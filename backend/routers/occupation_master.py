"""Phase 6.9.1 — Occupation Master CRUD endpoints (admin-controlled).

Single source of truth for occupation codes across all sales/partner tabs.

Endpoints:
  GET  /api/occupation-master              — list with filters (country, status, search)
  GET  /api/occupation-master/stats        — counts by status (feeds admin KB dashboard)
  GET  /api/occupation-master/{id}         — single + populated assessing-body details
  POST /api/occupation-master              — admin creates a new code manually
  PUT  /api/occupation-master/{id}         — admin updates a code (incl. status flip)
  DELETE /api/occupation-master/{id}       — admin soft-delete (status=superseded)
  POST /api/occupation-master/{id}/verify  — admin marks 'verified' with source_reference
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.kb_ai import draft_occupation, draft_skill_body, now_utc

router = APIRouter(prefix="/occupation-master", tags=["occupation-master"])

OCCUPATION_MASTER = db["occupation_master"]
SKILL_BODY_MASTER = db["skill_body_master"]

VALID_STATUSES = {"verified", "draft", "outdated", "superseded"}
ADMIN_ROLES = {"admin", "admin_owner"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _strip(doc: dict) -> dict:
    """Remove Mongo _id (BSON ObjectId is not JSON serialisable)."""
    if doc and "_id" in doc:
        doc.pop("_id", None)
    return doc


async def _require_admin(user: dict):
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────
class AssessingAuthority(BaseModel):
    body_id: Optional[str] = None
    name: Optional[str] = ""
    full_name: Optional[str] = ""
    website: Optional[str] = ""


class HierarchyModel(BaseModel):
    major_group: Optional[str] = ""
    sub_major_group: Optional[str] = ""
    minor_group: Optional[str] = ""
    unit_group: Optional[str] = ""
    unit_group_name: Optional[str] = ""


class OccupationCreate(BaseModel):
    code: str = Field(..., min_length=1)
    country_code: str = Field(..., min_length=2, max_length=3)
    title: str = Field(..., min_length=1)
    classification_type: str = "ANZSCO"
    classification_version: Optional[str] = ""
    alternative_titles: List[str] = []
    specialisations: List[str] = []
    hierarchy: Optional[HierarchyModel] = None
    description: Optional[str] = ""
    typical_tasks: List[str] = []
    skill_level: Optional[int] = None
    assessing_authority: Optional[AssessingAuthority] = None
    status: str = "draft"  # always draft on create


class OccupationUpdate(BaseModel):
    title: Optional[str] = None
    classification_type: Optional[str] = None
    classification_version: Optional[str] = None
    alternative_titles: Optional[List[str]] = None
    specialisations: Optional[List[str]] = None
    hierarchy: Optional[HierarchyModel] = None
    description: Optional[str] = None
    typical_tasks: Optional[List[str]] = None
    skill_level: Optional[int] = None
    assessing_authority: Optional[AssessingAuthority] = None
    skill_assessment_details: Optional[dict] = None
    visa_pathways: Optional[dict] = None
    state_territory_eligibility: Optional[list] = None
    status: Optional[str] = None
    linked_product_id: Optional[str] = None


class VerifyRequest(BaseModel):
    source_reference: str = Field(..., min_length=1)
    review_notes: Optional[str] = ""


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/occupation-master/stats — admin dashboard counts
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/stats")
async def stats(current_user: dict = Depends(get_current_user)):
    """Status / country breakdown for the admin Knowledge Base dashboard.

    Excludes superseded (soft-deleted) records from totals since they are
    not actionable. Phase 6.9.4 will surface them separately.
    """
    pipeline = [
        {"$match": {"status": {"$ne": "superseded"}}},
        {"$group": {"_id": {"country": "$country_code", "status": "$status"}, "count": {"$sum": 1}}},
    ]
    rows = await OCCUPATION_MASTER.aggregate(pipeline).to_list(500)
    total = await OCCUPATION_MASTER.count_documents({"status": {"$ne": "superseded"}})
    superseded_count = await OCCUPATION_MASTER.count_documents({"status": "superseded"})
    by_status = {"verified": 0, "draft": 0, "outdated": 0}
    by_country = {}
    for r in rows:
        k = r["_id"]
        st = k.get("status") or "draft"
        cc = k.get("country") or "?"
        by_status[st] = by_status.get(st, 0) + r["count"]
        by_country.setdefault(cc, {"verified": 0, "draft": 0, "outdated": 0})
        by_country[cc][st] = by_country[cc].get(st, 0) + r["count"]
    pending = by_status["draft"] + by_status["outdated"]
    return {
        "total": total,
        "by_status": by_status,
        "by_country": by_country,
        "pending_verification": pending,
        "pending_percent": round((pending / total) * 100, 1) if total else 0,
        "superseded_count": superseded_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/occupation-master — list with filters
# ─────────────────────────────────────────────────────────────────────────────
@router.get("")
async def list_occupations(
    country: Optional[str] = Query(None, description="Filter by country_code (AU/CA/NZ)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search title / code / alternative_titles"),
    body_id: Optional[str] = Query(None, description="Filter by assessing-body slug/id"),
    limit: int = Query(200, ge=1, le=500),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Admin sees everything (except superseded by default). Non-admin during
    transition also sees everything non-superseded (Phase 6.9.4 will enforce
    status filter once verification reaches threshold)."""
    q: dict = {}
    if country:
        q["country_code"] = country.upper()
    # Phase 17.1.2 — accept "all" / "any" / "*" as wildcards (no status filter).
    # Prevents the 400 papercut when callers pass a deliberate "show everything"
    # sentinel from a URL query param.
    _STATUS_WILDCARDS = {"all", "any", "*"}
    if status and status.strip().lower() not in _STATUS_WILDCARDS:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Use one of {VALID_STATUSES}")
        q["status"] = status
    elif not status:
        # Default (no param at all): hide superseded (soft-deleted) records.
        q["status"] = {"$ne": "superseded"}
    # else: wildcard passed → no status clause added → returns all statuses
    if body_id:
        q["assessing_authority.body_id"] = body_id
    if search:
        q["$or"] = [
            {"code": {"$regex": search, "$options": "i"}},
            {"title": {"$regex": search, "$options": "i"}},
            {"alternative_titles": {"$regex": search, "$options": "i"}},
        ]
    cursor = OCCUPATION_MASTER.find(q, {"_id": 0}).sort([("country_code", 1), ("code", 1)]).skip(skip).limit(limit)
    items = [_strip(d) async for d in cursor]
    total = await OCCUPATION_MASTER.count_documents(q)
    return {"items": items, "total": total, "limit": limit, "skip": skip}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/occupation-master/{id} — single + populated body details
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{occupation_id}")
async def get_occupation(occupation_id: str, current_user: dict = Depends(get_current_user)):
    doc = await _find_occupation(occupation_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Occupation not found")
    # Populate assessing-body full record if linked
    body_slug = (doc.get("assessing_authority") or {}).get("body_id")
    if body_slug:
        body = await SKILL_BODY_MASTER.find_one(
            {"country_code": doc["country_code"], "slug": body_slug},
            {"_id": 0},
        )
        if body:
            doc["assessing_authority_full"] = _strip(body)
    return _strip(doc)


# ─── Phase 17.1.3 — dual-lookup resolver ───────────────────────────────────
async def _find_occupation(identifier: str) -> Optional[dict]:
    """Find one record by `occupation_id` (UUID or slug like 'au-261313').

    Fallback: if the identifier looks like a country-prefixed slug
    `{cc}-{code}` (e.g. ``au-261313``), also try `(country_code, code)` —
    protects against records that still lack `occupation_id` after backfill
    OR future records seeded by external scripts.
    """
    doc = await OCCUPATION_MASTER.find_one({"occupation_id": identifier}, {"_id": 0})
    if doc:
        return doc
    # Slug fallback: "{cc}-{code}" → split and try (country_code, code)
    if isinstance(identifier, str) and "-" in identifier:
        cc, _, code = identifier.partition("-")
        if cc and code:
            doc = await OCCUPATION_MASTER.find_one(
                {"country_code": cc.upper(), "code": code},
                {"_id": 0},
            )
            if doc:
                return doc
    return None


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/occupation-master — admin creates a single code
# ─────────────────────────────────────────────────────────────────────────────
@router.post("")
async def create_occupation(req: OccupationCreate, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    # Uniqueness check
    existing = await OCCUPATION_MASTER.find_one(
        {"country_code": req.country_code.upper(), "code": req.code}, {"_id": 0}
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Code {req.code} already exists for {req.country_code}",
        )
    now = datetime.now(timezone.utc)
    doc = {
        "occupation_id": str(uuid.uuid4()),
        "code": req.code,
        "classification_type": req.classification_type or "ANZSCO",
        "classification_version": req.classification_version or "",
        "country_code": req.country_code.upper(),
        "title": req.title,
        "alternative_titles": req.alternative_titles,
        "specialisations": req.specialisations,
        "hierarchy": req.hierarchy.model_dump() if req.hierarchy else {},
        "description": req.description or "",
        "typical_tasks": req.typical_tasks,
        "skill_level": req.skill_level,
        "assessing_authority": req.assessing_authority.model_dump() if req.assessing_authority else {},
        "skill_assessment_details": {
            "requirements": "", "criteria_notes": "", "qualification_rules": "",
            "documents_required": [], "fee_native": None, "fee_currency": None,
            "processing_time": "",
        },
        "visa_pathways": {"pathway_lists": [], "visa_eligibility": [], "processing_times": {}},
        "state_territory_eligibility": [],
        "similar_codes": [],
        "status": "draft",  # always draft on create — admin verifies later
        "verification": {
            "verified_by": None, "verified_at": None,
            "source_reference": "", "review_notes": "",
        },
        "ai_draft": {
            "description": "", "typical_tasks": [],
            "generated_at": None, "generated_by_model": None, "is_stale": False,
        },
        "linked_product_id": None,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
        "last_reviewed_at": None,
    }
    await OCCUPATION_MASTER.insert_one(doc)
    return _strip({**doc})


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/occupation-master/{id} — admin updates
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/{occupation_id}")
async def update_occupation(occupation_id: str, req: OccupationUpdate, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    existing = await _find_occupation(occupation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Occupation not found")
    if req.status and req.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use one of {VALID_STATUSES}")

    # Resolve to the canonical id stored on the doc (handles slug → uuid fallback)
    real_id = existing.get("occupation_id") or occupation_id

    update_doc = req.model_dump(exclude_unset=True)
    if "hierarchy" in update_doc and update_doc["hierarchy"]:
        update_doc["hierarchy"] = update_doc["hierarchy"]
    if "assessing_authority" in update_doc and update_doc["assessing_authority"]:
        update_doc["assessing_authority"] = update_doc["assessing_authority"]
    update_doc["updated_at"] = datetime.now(timezone.utc)
    await OCCUPATION_MASTER.update_one({"occupation_id": real_id}, {"$set": update_doc})
    refreshed = await OCCUPATION_MASTER.find_one({"occupation_id": real_id}, {"_id": 0})
    return _strip(refreshed)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/occupation-master/{id}/verify — verify & publish
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{occupation_id}/verify")
async def verify_occupation(occupation_id: str, req: VerifyRequest, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    existing = await _find_occupation(occupation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = existing.get("occupation_id") or occupation_id
    now = datetime.now(timezone.utc)
    await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id},
        {"$set": {
            "status": "verified",
            "verification.verified_by": current_user["id"],
            "verification.verified_at": now,
            "verification.source_reference": req.source_reference,
            "verification.review_notes": req.review_notes or "",
            "last_reviewed_at": now,
            "updated_at": now,
        }},
    )
    refreshed = await OCCUPATION_MASTER.find_one({"occupation_id": real_id}, {"_id": 0})
    return _strip(refreshed)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/occupation-master/{id} — soft-delete (status=superseded)
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/{occupation_id}")
async def delete_occupation(occupation_id: str, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    existing = await _find_occupation(occupation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = existing.get("occupation_id") or occupation_id
    now = datetime.now(timezone.utc)
    await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id},
        {"$set": {"status": "superseded", "updated_at": now}},
    )
    return {"ok": True, "occupation_id": real_id, "status": "superseded"}


# ═════════════════════════════════════════════════════════════════════════════
# Skill Body Master — supporting endpoints for the same resource
# ═════════════════════════════════════════════════════════════════════════════
bodies_router = APIRouter(prefix="/skill-body-master", tags=["skill-body-master"])


@bodies_router.get("")
async def list_bodies(
    country: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    q: dict = {}
    if country:
        q["country_code"] = country.upper()
    if status:
        q["status"] = status
    if search:
        q["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
            {"slug": {"$regex": search, "$options": "i"}},
        ]
    cursor = SKILL_BODY_MASTER.find(q, {"_id": 0}).sort([("country_code", 1), ("name", 1)]).limit(200)
    items = [_strip(d) async for d in cursor]
    return {"items": items, "total": len(items)}


@bodies_router.get("/{body_id}")
async def get_body(body_id: str, current_user: dict = Depends(get_current_user)):
    doc = await SKILL_BODY_MASTER.find_one({"body_id": body_id}, {"_id": 0})
    if not doc:
        # Fall back to slug
        doc = await SKILL_BODY_MASTER.find_one({"slug": body_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Skill body not found")
    return _strip(doc)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6.9.3 — AI Draft endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{occupation_id}/ai-draft")
async def generate_occupation_ai_draft(occupation_id: str, current_user: dict = Depends(get_current_user)):
    """Admin clicks "🤖 Generate AI Draft" → calls Claude for baseline content
    (description / typical_tasks / qualification_rules). Result cached on the
    occupation's `ai_draft` block. Status remains 'draft' until admin verifies.
    """
    await _require_admin(current_user)
    occ = await _find_occupation(occupation_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = occ.get("occupation_id") or occupation_id
    aa = occ.get("assessing_authority") or {}
    pathway_lists = (occ.get("visa_pathways") or {}).get("pathway_lists") or []
    hierarchy = occ.get("hierarchy") or {}
    try:
        draft = await draft_occupation(
            code=occ.get("code", ""),
            title=occ.get("title", ""),
            country_code=occ.get("country_code", ""),
            assessing_body=aa.get("name"),
            pathway=pathway_lists[0] if pathway_lists else None,
            hierarchy_group=hierarchy.get("unit_group_name"),
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"AI draft failed: {e}") from e

    now = now_utc()
    ai_draft_block = {
        "description": draft.get("description", ""),
        "typical_tasks": draft.get("typical_tasks", []),
        "qualification_rules": draft.get("qualification_rules", ""),
        "ai_confidence_note": draft.get("ai_confidence_note", ""),
        "generated_at": now,
        "generated_by_model": "claude-sonnet-4-6",
        "generated_by": current_user["id"],
        "is_stale": False,
    }
    await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id},
        {"$set": {"ai_draft": ai_draft_block, "updated_at": now}},
    )
    return {"ok": True, "ai_draft": ai_draft_block}


@bodies_router.post("/{body_id_or_slug}/ai-draft")
async def generate_body_ai_draft(body_id_or_slug: str, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    body = await SKILL_BODY_MASTER.find_one({"body_id": body_id_or_slug})
    if not body:
        body = await SKILL_BODY_MASTER.find_one({"slug": body_id_or_slug})
    if not body:
        raise HTTPException(status_code=404, detail="Skill body not found")
    try:
        draft = await draft_skill_body(
            slug=body.get("slug", ""),
            name=body.get("name", ""),
            full_name=body.get("full_name", ""),
            country_code=body.get("country_code", ""),
            website=body.get("website"),
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"AI draft failed: {e}") from e

    now = now_utc()
    ai_draft_block = {
        "description": draft.get("description", ""),
        "role": draft.get("role", ""),
        "criteria": draft.get("general_criteria", {}),
        "ai_confidence_note": draft.get("ai_confidence_note", ""),
        "generated_at": now,
        "generated_by_model": "claude-sonnet-4-6",
        "generated_by": current_user["id"],
        "is_stale": False,
    }
    await SKILL_BODY_MASTER.update_one(
        {"body_id": body["body_id"]},
        {"$set": {"ai_draft": ai_draft_block, "updated_at": now}},
    )
    return {"ok": True, "ai_draft": ai_draft_block}
