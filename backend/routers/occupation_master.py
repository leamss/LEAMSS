"""Phase 6.9.1 / 18.1 — Occupation Master CRUD endpoints (admin-controlled).

Single source of truth for occupation codes across all sales/partner tabs.

Endpoints:
  GET    /api/occupation-master                       — list with filters
  GET    /api/occupation-master/stats                 — counts by status
  GET    /api/occupation-master/{id}                  — single + populated body
  POST   /api/occupation-master                       — admin creates a new code
  PUT    /api/occupation-master/{id}                  — admin updates (incl. all expanded fields)
  DELETE /api/occupation-master/{id}                  — admin soft-delete
  POST   /api/occupation-master/{id}/verify           — verify+publish with snapshot history
  POST   /api/occupation-master/{id}/copy-from-ai     — Phase 18.1: lift ai_draft.* to top-level
  POST   /api/occupation-master/{id}/sample-cases     — Phase 18.1: add sample case (assigns UUID)
  PATCH  /api/occupation-master/{id}/sample-cases/{case_id}    — update sample case by UUID
  DELETE /api/occupation-master/{id}/sample-cases/{case_id}    — remove sample case by UUID
  POST   /api/occupation-master/{id}/custom-sections           — add custom section (assigns UUID)
  PATCH  /api/occupation-master/{id}/custom-sections/{sec_id}  — update custom section
  DELETE /api/occupation-master/{id}/custom-sections/{sec_id}  — remove custom section
"""
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from core.auth import get_current_user
from core.database import db, audit_logs_col
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
    # Phase 18.1 — richer admin-curated body info
    url: Optional[str] = ""
    processing_time_weeks: Optional[int] = None
    fee_native: Optional[float] = None
    fee_currency: Optional[str] = ""
    contact_details: Optional[str] = ""
    rules_summary: Optional[str] = ""


class HierarchyModel(BaseModel):
    major_group: Optional[str] = ""
    sub_major_group: Optional[str] = ""
    minor_group: Optional[str] = ""
    unit_group: Optional[str] = ""
    unit_group_name: Optional[str] = ""


class RequiredDocument(BaseModel):
    """Phase 18.1 — admin-curated document checklist item."""
    id: Optional[str] = None  # backend assigns UUID if missing
    name: str
    category: str = "Other"
    required: bool = True
    country_override: Optional[str] = None  # None = applies to all countries


# Phase 18.3 — outcome enum enforced
VALID_SAMPLE_CASE_OUTCOMES = {"Approved", "Refused", "Withdrawn", "Pending"}


class SampleCase(BaseModel):
    """Phase 18.1 / 18.3 — anonymised client success story (lenient bulk shape).

    The model itself stays lenient so bulk PUT (`/occupation-master/{id}`) can
    replace the whole array without per-row blow-ups. The dedicated POST/PATCH
    `/sample-cases` endpoints validate strictly via `SampleCaseStrict`.
    """
    id: Optional[str] = None
    client_age: Optional[int] = Field(None, ge=18, le=70)
    profile_summary: Optional[str] = Field("", max_length=500)
    visa_subclass: Optional[str] = Field("", max_length=40)
    outcome: Optional[str] = Field("", max_length=40)
    timeline_months: Optional[int] = Field(None, ge=0, le=48)
    notes: Optional[str] = Field("", max_length=1000)


_URL_RE = re.compile(r"^https?://[^\s<>\"']+$", re.IGNORECASE)


class CustomSection(BaseModel):
    """Phase 18.1 / 18.3 — free-form section (lenient bulk shape)."""
    id: Optional[str] = None
    title: Optional[str] = Field("", max_length=80)
    body_markdown: Optional[str] = Field("", max_length=5000)
    source_url: Optional[str] = Field("", max_length=500)


# Phase 18.3 — strict sub-CRUD payloads for POST /sample-cases & POST /custom-sections
class SampleCaseStrict(BaseModel):
    id: Optional[str] = None
    client_age: Optional[int] = Field(None, ge=18, le=70)
    profile_summary: Optional[str] = Field("", max_length=500)
    visa_subclass: Optional[str] = Field("", max_length=40)
    outcome: str = Field(..., min_length=1)
    timeline_months: Optional[int] = Field(None, ge=0, le=48)
    notes: Optional[str] = Field("", max_length=1000)

    @field_validator("outcome")
    @classmethod
    def _outcome_enum(cls, v: str) -> str:
        if v not in VALID_SAMPLE_CASE_OUTCOMES:
            raise ValueError(f"outcome must be one of {sorted(VALID_SAMPLE_CASE_OUTCOMES)}")
        return v


class CustomSectionStrict(BaseModel):
    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=80)
    body_markdown: Optional[str] = Field("", max_length=5000)
    source_url: Optional[str] = Field("", max_length=500)

    @field_validator("source_url")
    @classmethod
    def _source_url_format(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if not _URL_RE.match(v.strip()):
            raise ValueError("source_url must be a valid http(s) URL")
        return v.strip()


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
    # Phase 18.1 — workspace expansion fields
    qualification_rules: Optional[str] = None
    required_documents: Optional[List[RequiredDocument]] = None
    similar_codes_override: Optional[List[str]] = None
    recommended_visa_subclass: Optional[Dict[str, str]] = None  # MERGE per-country
    sample_cases: Optional[List[SampleCase]] = None
    custom_sections: Optional[List[CustomSection]] = None


class VerifyRequest(BaseModel):
    """Phase 18.1 — /verify accepts both legacy (source_reference + review_notes
    only) and the new full payload that includes all editable fields. Snapshots
    the pre-change state into `verification_history[]` before applying changes."""
    source_reference: str = Field(..., min_length=1)
    review_notes: Optional[str] = ""
    # Optional full editable payload (any subset)
    title: Optional[str] = None
    description: Optional[str] = None
    typical_tasks: Optional[List[str]] = None
    qualification_rules: Optional[str] = None
    alternative_titles: Optional[List[str]] = None
    assessing_authority: Optional[AssessingAuthority] = None
    required_documents: Optional[List[RequiredDocument]] = None
    similar_codes_override: Optional[List[str]] = None
    recommended_visa_subclass: Optional[Dict[str, str]] = None
    sample_cases: Optional[List[SampleCase]] = None
    custom_sections: Optional[List[CustomSection]] = None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 18.1 helpers — UUID stamping + merge semantics
# ─────────────────────────────────────────────────────────────────────────────
_SNAPSHOT_FIELDS = (
    "title", "description", "typical_tasks", "qualification_rules",
    "alternative_titles", "assessing_authority", "required_documents",
    "similar_codes_override", "recommended_visa_subclass",
    "sample_cases", "custom_sections",
)


def _ensure_ids(items: Optional[List[dict]]) -> List[dict]:
    """Stamp a UUID on any list item missing an `id` field. Returns new list."""
    out: List[dict] = []
    for it in items or []:
        if isinstance(it, dict):
            if not it.get("id"):
                it = {**it, "id": str(uuid.uuid4())}
            out.append(it)
    return out


def _snapshot(doc: dict) -> dict:
    """Capture current top-level editable fields for verification_history entry."""
    return {k: doc.get(k) for k in _SNAPSHOT_FIELDS if k in doc}


async def _write_audit(user: dict, action: str, occupation_id: str, extra: Optional[dict] = None):
    """Append a row to `audit_logs` for any verify/copy/sub-CRUD action."""
    log_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user.get("id"),
        "user_email": user.get("email"),
        "action": action,
        "entity_type": "occupation_master",
        "entity_id": occupation_id,
        "created_at": datetime.now(timezone.utc),
    }
    if extra:
        log_doc["extra"] = extra
    try:
        await audit_logs_col.insert_one(log_doc)
    except Exception:  # noqa: BLE001 — never block an admin action on audit failure
        pass


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/occupation-master/stats — admin dashboard counts
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/stats")
async def stats(current_user: dict = Depends(get_current_user)):
    pipeline = [
        {"$match": {"status": {"$ne": "superseded"}}},
        {"$group": {"_id": {"country": "$country_code", "status": "$status"}, "count": {"$sum": 1}}},
    ]
    rows = await OCCUPATION_MASTER.aggregate(pipeline).to_list(500)
    total = await OCCUPATION_MASTER.count_documents({"status": {"$ne": "superseded"}})
    superseded_count = await OCCUPATION_MASTER.count_documents({"status": "superseded"})
    by_status = {"verified": 0, "draft": 0, "outdated": 0}
    by_country: Dict[str, Dict[str, int]] = {}
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
    country: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    body_id: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    q: dict = {}
    if country:
        q["country_code"] = country.upper()
    _STATUS_WILDCARDS = {"all", "any", "*"}
    if status and status.strip().lower() not in _STATUS_WILDCARDS:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Use one of {VALID_STATUSES}")
        q["status"] = status
    elif not status:
        q["status"] = {"$ne": "superseded"}
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
    body_slug = (doc.get("assessing_authority") or {}).get("body_id")
    if body_slug:
        body = await SKILL_BODY_MASTER.find_one(
            {"country_code": doc["country_code"], "slug": body_slug}, {"_id": 0},
        )
        if body:
            doc["assessing_authority_full"] = _strip(body)
    return _strip(doc)


# ─── Dual-lookup resolver (Phase 17.1.3) ─────────────────────────────────────
async def _find_occupation(identifier: str) -> Optional[dict]:
    doc = await OCCUPATION_MASTER.find_one({"occupation_id": identifier}, {"_id": 0})
    if doc:
        return doc
    if isinstance(identifier, str) and "-" in identifier:
        cc, _, code = identifier.partition("-")
        if cc and code:
            doc = await OCCUPATION_MASTER.find_one(
                {"country_code": cc.upper(), "code": code}, {"_id": 0},
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
    existing = await OCCUPATION_MASTER.find_one(
        {"country_code": req.country_code.upper(), "code": req.code}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Code {req.code} already exists for {req.country_code}")
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
        # Phase 18.1 — new workspace fields default-empty
        "qualification_rules": "",
        "required_documents": [],
        "similar_codes_override": [],
        "recommended_visa_subclass": {},
        "sample_cases": [],
        "custom_sections": [],
        "verification_history": [],
        "status": "draft",
        "verification": {
            "verified_by": None, "verified_at": None, "is_verified": False,
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
    real_id = existing.get("occupation_id") or occupation_id

    update_doc = req.model_dump(exclude_unset=True)
    update_set: Dict[str, Any] = {}

    # Phase 18.1 — stamp UUIDs on sub-doc items
    if "required_documents" in update_doc and update_doc["required_documents"] is not None:
        update_set["required_documents"] = _ensure_ids(update_doc.pop("required_documents"))
    if "sample_cases" in update_doc and update_doc["sample_cases"] is not None:
        update_set["sample_cases"] = _ensure_ids(update_doc.pop("sample_cases"))
    if "custom_sections" in update_doc and update_doc["custom_sections"] is not None:
        update_set["custom_sections"] = _ensure_ids(update_doc.pop("custom_sections"))

    # Phase 18.1 — recommended_visa_subclass uses MERGE semantics per-country.
    rvs = update_doc.pop("recommended_visa_subclass", None)
    if rvs is not None and isinstance(rvs, dict):
        for cc, subclass in rvs.items():
            update_set[f"recommended_visa_subclass.{cc.upper()}"] = subclass

    # Remaining fields → straight $set
    for k, v in update_doc.items():
        update_set[k] = v

    update_set["updated_at"] = datetime.now(timezone.utc)
    await OCCUPATION_MASTER.update_one({"occupation_id": real_id}, {"$set": update_set})
    refreshed = await OCCUPATION_MASTER.find_one({"occupation_id": real_id}, {"_id": 0})
    return _strip(refreshed)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/occupation-master/{id}/verify — verify, snapshot, persist
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{occupation_id}/verify")
async def verify_occupation(occupation_id: str, req: VerifyRequest, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    existing = await _find_occupation(occupation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = existing.get("occupation_id") or occupation_id
    now = datetime.now(timezone.utc)

    # 1. Snapshot current top-level state into history (immutable, append-only).
    history_entry = {
        "verified_by": current_user.get("id"),
        "verified_by_name": current_user.get("name") or current_user.get("email") or "admin",
        "verified_at": now.isoformat(),
        "source_reference": req.source_reference,
        "review_notes": req.review_notes or "",
        "snapshot": _snapshot(existing),
    }

    # 2. Build $set payload — apply any editable fields from the payload.
    update_set: Dict[str, Any] = {
        "status": "verified",
        "verification.verified_by": current_user["id"],
        "verification.verified_by_name": current_user.get("name") or current_user.get("email") or "admin",
        "verification.verified_at": now,
        "verification.source_reference": req.source_reference,
        "verification.review_notes": req.review_notes or "",
        "verification.is_verified": True,
        "last_reviewed_at": now,
        "updated_at": now,
    }
    body = req.model_dump(exclude_unset=True)
    for key in ("source_reference", "review_notes"):
        body.pop(key, None)

    if "required_documents" in body and body["required_documents"] is not None:
        update_set["required_documents"] = _ensure_ids(body.pop("required_documents"))
    if "sample_cases" in body and body["sample_cases"] is not None:
        update_set["sample_cases"] = _ensure_ids(body.pop("sample_cases"))
    if "custom_sections" in body and body["custom_sections"] is not None:
        update_set["custom_sections"] = _ensure_ids(body.pop("custom_sections"))

    rvs = body.pop("recommended_visa_subclass", None)
    if rvs is not None and isinstance(rvs, dict):
        for cc, subclass in rvs.items():
            update_set[f"recommended_visa_subclass.{cc.upper()}"] = subclass

    for k, v in body.items():
        update_set[k] = v

    await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id},
        {"$set": update_set, "$push": {"verification_history": history_entry}},
    )

    await _write_audit(
        current_user, "verify_occupation", real_id,
        extra={"source_reference": req.source_reference},
    )

    refreshed = await OCCUPATION_MASTER.find_one({"occupation_id": real_id}, {"_id": 0})
    return _strip(refreshed)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/occupation-master/{id}/copy-from-ai — Phase 18.1
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{occupation_id}/copy-from-ai")
async def copy_from_ai(occupation_id: str, current_user: dict = Depends(get_current_user)):
    """Bulk-copy ai_draft.{description, typical_tasks, qualification_rules}
    into the top-level editable fields. Does NOT auto-verify; status remains
    whatever it was. Used by the "Copy All from AI" button in Admin Edit."""
    await _require_admin(current_user)
    occ = await _find_occupation(occupation_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = occ.get("occupation_id") or occupation_id
    ai = occ.get("ai_draft") or {}
    if not (ai.get("description") or ai.get("typical_tasks") or ai.get("qualification_rules")):
        raise HTTPException(status_code=400, detail="No ai_draft content to copy — generate first")
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {"updated_at": now}
    if ai.get("description"):
        payload["description"] = ai["description"]
    if ai.get("typical_tasks"):
        payload["typical_tasks"] = ai["typical_tasks"]
    if ai.get("qualification_rules"):
        payload["qualification_rules"] = ai["qualification_rules"]
    await OCCUPATION_MASTER.update_one({"occupation_id": real_id}, {"$set": payload})
    await _write_audit(current_user, "copy_from_ai", real_id, extra={"fields": list(payload.keys())})
    refreshed = await OCCUPATION_MASTER.find_one({"occupation_id": real_id}, {"_id": 0})
    return _strip(refreshed)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 18.1 — Sample Cases sub-CRUD
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{occupation_id}/sample-cases")
async def add_sample_case(occupation_id: str, req: SampleCaseStrict, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    occ = await _find_occupation(occupation_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = occ.get("occupation_id") or occupation_id
    now = datetime.now(timezone.utc)
    case = req.model_dump()
    case["id"] = case.get("id") or str(uuid.uuid4())
    case["created_at"] = now.isoformat()
    case["created_by"] = current_user["id"]
    await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id},
        {"$push": {"sample_cases": case}, "$set": {"updated_at": now}},
    )
    await _write_audit(current_user, "add_sample_case", real_id, extra={"case_id": case["id"]})
    return {"ok": True, "sample_case": case}


@router.patch("/{occupation_id}/sample-cases/{case_id}")
async def update_sample_case(occupation_id: str, case_id: str, req: SampleCase, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    occ = await _find_occupation(occupation_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = occ.get("occupation_id") or occupation_id
    fields = req.model_dump(exclude_unset=True)
    fields.pop("id", None)
    set_payload = {f"sample_cases.$.{k}": v for k, v in fields.items()}
    set_payload["updated_at"] = datetime.now(timezone.utc)
    res = await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id, "sample_cases.id": case_id},
        {"$set": set_payload},
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Sample case not found")
    refreshed = await OCCUPATION_MASTER.find_one({"occupation_id": real_id}, {"_id": 0})
    case = next((c for c in (refreshed.get("sample_cases") or []) if c.get("id") == case_id), None)
    await _write_audit(current_user, "update_sample_case", real_id, extra={"case_id": case_id})
    return {"ok": True, "sample_case": case}


@router.delete("/{occupation_id}/sample-cases/{case_id}")
async def delete_sample_case(occupation_id: str, case_id: str, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    occ = await _find_occupation(occupation_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = occ.get("occupation_id") or occupation_id
    res = await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id},
        {"$pull": {"sample_cases": {"id": case_id}}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    if not res.modified_count:
        raise HTTPException(status_code=404, detail="Sample case not found")
    await _write_audit(current_user, "delete_sample_case", real_id, extra={"case_id": case_id})
    return {"ok": True, "case_id": case_id}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 18.1 — Custom Sections sub-CRUD
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{occupation_id}/custom-sections")
async def add_custom_section(occupation_id: str, req: CustomSectionStrict, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    occ = await _find_occupation(occupation_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = occ.get("occupation_id") or occupation_id
    now = datetime.now(timezone.utc)
    section = req.model_dump()
    section["id"] = section.get("id") or str(uuid.uuid4())
    section["created_at"] = now.isoformat()
    section["created_by"] = current_user["id"]
    await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id},
        {"$push": {"custom_sections": section}, "$set": {"updated_at": now}},
    )
    await _write_audit(current_user, "add_custom_section", real_id, extra={"section_id": section["id"]})
    return {"ok": True, "custom_section": section}


@router.patch("/{occupation_id}/custom-sections/{section_id}")
async def update_custom_section(occupation_id: str, section_id: str, req: CustomSection, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    occ = await _find_occupation(occupation_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = occ.get("occupation_id") or occupation_id
    fields = req.model_dump(exclude_unset=True)
    fields.pop("id", None)
    set_payload = {f"custom_sections.$.{k}": v for k, v in fields.items()}
    set_payload["updated_at"] = datetime.now(timezone.utc)
    res = await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id, "custom_sections.id": section_id},
        {"$set": set_payload},
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Custom section not found")
    refreshed = await OCCUPATION_MASTER.find_one({"occupation_id": real_id}, {"_id": 0})
    section = next((s for s in (refreshed.get("custom_sections") or []) if s.get("id") == section_id), None)
    await _write_audit(current_user, "update_custom_section", real_id, extra={"section_id": section_id})
    return {"ok": True, "custom_section": section}


@router.delete("/{occupation_id}/custom-sections/{section_id}")
async def delete_custom_section(occupation_id: str, section_id: str, current_user: dict = Depends(get_current_user)):
    await _require_admin(current_user)
    occ = await _find_occupation(occupation_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occupation not found")
    real_id = occ.get("occupation_id") or occupation_id
    res = await OCCUPATION_MASTER.update_one(
        {"occupation_id": real_id},
        {"$pull": {"custom_sections": {"id": section_id}}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    if not res.modified_count:
        raise HTTPException(status_code=404, detail="Custom section not found")
    await _write_audit(current_user, "delete_custom_section", real_id, extra={"section_id": section_id})
    return {"ok": True, "section_id": section_id}


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
        doc = await SKILL_BODY_MASTER.find_one({"slug": body_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Skill body not found")
    return _strip(doc)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6.9.3 — AI Draft endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{occupation_id}/ai-draft")
async def generate_occupation_ai_draft(occupation_id: str, current_user: dict = Depends(get_current_user)):
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
