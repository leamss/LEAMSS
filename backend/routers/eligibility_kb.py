"""Phase 6.1 — Eligibility Knowledge Base Router.

Comprehensive country immigration rules, visa categories, skill assessment bodies,
occupation codes, points systems, and document templates.

Separate from the existing /api/eligibility/score lead-magnet (Phase 4D) — that one
is a quick public scorer; THIS is the deep configurable knowledge base used by:
  • Sub-Module 6.2 (Smart Profile Form)
  • Sub-Module 6.3 (AI Analysis Engine)
  • Sub-Module 6.5 (Checklist Integration)
"""
import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.eligibility_kb_seed import seed_country_rules

router = APIRouter(prefix="/eligibility/kb", tags=["Phase 6.1 - Eligibility Knowledge Base"])

countries_col = db["country_rules"]


# ──────────────────────────────────────────────────────────────
# Permissions / Roles
# ──────────────────────────────────────────────────────────────
ADMIN_ROLES = {"admin", "admin_owner"}
VIEWER_ROLES = ADMIN_ROLES | {"sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "partner", "case_manager", "hr_manager"}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _is_viewer(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    if role in VIEWER_ROLES:
        return True
    perms = set(user.get("permissions") or [])
    return "*" in perms or "eligibility_data.view" in perms


def _strip(doc: dict) -> dict:
    """Remove MongoDB _id and serialize datetimes for response."""
    if not doc:
        return doc
    doc.pop("_id", None)
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    # Serialise nested meta
    if isinstance(doc.get("meta"), dict):
        for k, v in list(doc["meta"].items()):
            if isinstance(v, datetime):
                doc["meta"][k] = v.isoformat()
    return doc


# Seed on first import
import asyncio
_seed_done = False
async def _ensure_seeded():
    global _seed_done
    if _seed_done:
        return
    try:
        n = await seed_country_rules(countries_col)
        if n > 0:
            print(f"[eligibility_kb] Seeded {n} countries on startup")
    except Exception as e:
        print(f"[eligibility_kb] Seed failed: {e}")
    _seed_done = True


# ══════════════════════════════════════════════════════════════
# Pydantic Models
# ══════════════════════════════════════════════════════════════
class CountryCreate(BaseModel):
    country: str
    country_code: str = Field(..., min_length=2, max_length=3)
    country_flag_emoji: Optional[str] = None
    is_active: bool = True
    priority: int = 99


class CountryPatch(BaseModel):
    country: Optional[str] = None
    country_flag_emoji: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    points_system: Optional[Dict[str, Any]] = None
    document_templates: Optional[Dict[str, Any]] = None


class VisaCategoryUpsert(BaseModel):
    visa_id: Optional[str] = None  # generated if absent
    code: str
    name: str
    type: str
    description: Optional[str] = ""
    eligibility: Dict[str, Any] = Field(default_factory=dict)
    processing_time: Dict[str, Any] = Field(default_factory=dict)
    cost: Dict[str, Any] = Field(default_factory=dict)
    required_skill_assessment: bool = False
    pathway_type: Optional[str] = None
    success_factors: List[str] = Field(default_factory=list)
    is_active: bool = True


class SkillBodyUpsert(BaseModel):
    body_id: Optional[str] = None
    name: str
    full_name: Optional[str] = None
    website: Optional[str] = None
    assesses_occupations: List[str] = Field(default_factory=list)
    criteria_general: Dict[str, Any] = Field(default_factory=dict)
    documents_required: List[str] = Field(default_factory=list)
    assessment_fee_inr: Optional[float] = None
    processing_time_weeks: Optional[int] = None
    contact_info: Dict[str, Any] = Field(default_factory=dict)


class OccupationUpsert(BaseModel):
    code: str
    title: str
    group: Optional[str] = None
    group_code: Optional[str] = None
    skill_level: Optional[int] = None
    assessing_body: Optional[str] = None
    pathway: Optional[str] = None
    alternative_titles: List[str] = Field(default_factory=list)
    eligible_visas: List[str] = Field(default_factory=list)
    state_demand: Dict[str, str] = Field(default_factory=dict)
    description: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# Country CRUD
# ══════════════════════════════════════════════════════════════
@router.get("/countries")
async def list_countries(current_user: dict = Depends(get_current_user)):
    """List all countries (active and inactive) for admin view; non-admins see only active."""
    await _ensure_seeded()
    if not _is_viewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    is_admin = _is_admin(current_user)
    query = {} if is_admin else {"is_active": True}
    items = []
    async for c in countries_col.find(query).sort("priority", 1):
        # Return summary fields only for list view (full doc on /countries/{code})
        items.append({
            "country": c.get("country"),
            "country_code": c.get("country_code"),
            "country_flag_emoji": c.get("country_flag_emoji"),
            "is_active": c.get("is_active", True),
            "priority": c.get("priority", 99),
            "visa_count": len(c.get("visa_categories") or []),
            "skill_body_count": len(c.get("skill_assessment_bodies") or []),
            "occupation_count": len(c.get("occupation_codes") or []),
            "last_updated": (c.get("meta") or {}).get("last_updated"),
        })
        # Serialize datetime in last_updated
        if isinstance(items[-1]["last_updated"], datetime):
            items[-1]["last_updated"] = items[-1]["last_updated"].isoformat()
    return {"items": items, "count": len(items)}


@router.get("/countries/{country_code}")
async def get_country(country_code: str, current_user: dict = Depends(get_current_user)):
    await _ensure_seeded()
    if not _is_viewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    code = country_code.upper()
    doc = await countries_col.find_one({"country_code": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Country not found")
    return _strip(doc)


@router.post("/countries")
async def create_country(req: CountryCreate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = req.country_code.upper()
    if await countries_col.find_one({"country_code": code}, {"_id": 1}):
        raise HTTPException(status_code=409, detail=f"Country {code} already exists")
    now = datetime.now(timezone.utc)
    doc = {
        **req.model_dump(),
        "country_code": code,
        "visa_categories": [],
        "skill_assessment_bodies": [],
        "occupation_codes": [],
        "points_system": {},
        "document_templates": {"common_identity": [], "skill_assessment_specific": {}, "visa_specific": {}, "occupation_specific": {}},
        "meta": {"last_updated": now, "data_source": "manual", "next_review_date": now.replace(year=now.year + 1)},
        "created_at": now,
        "updated_at": now,
        "created_by": current_user["id"],
    }
    await countries_col.insert_one(doc)
    return _strip(doc)


@router.patch("/countries/{country_code}")
async def patch_country(country_code: str, req: CountryPatch, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = country_code.upper()
    updates = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    now = datetime.now(timezone.utc)
    updates["updated_at"] = now
    updates["meta.last_updated"] = now
    r = await countries_col.update_one({"country_code": code}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Country not found")
    doc = await countries_col.find_one({"country_code": code})
    return _strip(doc)


@router.delete("/countries/{country_code}")
async def delete_country(country_code: str, current_user: dict = Depends(get_current_user)):
    """Soft-delete by setting is_active=False (preserves history)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = country_code.upper()
    r = await countries_col.update_one(
        {"country_code": code},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Country not found")
    return {"ok": True}


# ══════════════════════════════════════════════════════════════
# Visa Categories
# ══════════════════════════════════════════════════════════════
@router.post("/countries/{country_code}/visas")
async def add_or_update_visa(country_code: str, req: VisaCategoryUpsert, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = country_code.upper()
    visa = req.model_dump()
    if not visa.get("visa_id"):
        visa["visa_id"] = f"{code.lower()}_{visa['code'].lower().replace('-', '_').replace(' ', '_')}_{uuid.uuid4().hex[:6]}"

    country = await countries_col.find_one({"country_code": code}, {"visa_categories": 1})
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    existing = [v for v in (country.get("visa_categories") or []) if v.get("visa_id") == visa["visa_id"] or v.get("code") == visa["code"]]
    if existing:
        # Update in-place
        await countries_col.update_one(
            {"country_code": code, "visa_categories.visa_id": existing[0]["visa_id"]},
            {"$set": {"visa_categories.$": {**existing[0], **visa}, "updated_at": datetime.now(timezone.utc)}}
        )
    else:
        await countries_col.update_one(
            {"country_code": code},
            {"$push": {"visa_categories": visa}, "$set": {"updated_at": datetime.now(timezone.utc)}}
        )
    return {"ok": True, "visa_id": visa["visa_id"]}


@router.delete("/countries/{country_code}/visas/{visa_id}")
async def delete_visa(country_code: str, visa_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = country_code.upper()
    r = await countries_col.update_one(
        {"country_code": code},
        {"$pull": {"visa_categories": {"visa_id": visa_id}}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="Visa not found")
    return {"ok": True}


# ══════════════════════════════════════════════════════════════
# Skill Assessment Bodies
# ══════════════════════════════════════════════════════════════
@router.post("/countries/{country_code}/skill-bodies")
async def add_or_update_skill_body(country_code: str, req: SkillBodyUpsert, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = country_code.upper()
    body = req.model_dump()
    if not body.get("body_id"):
        body["body_id"] = body["name"].lower().replace(" ", "_") + "_" + uuid.uuid4().hex[:4]

    country = await countries_col.find_one({"country_code": code}, {"skill_assessment_bodies": 1})
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    existing = [b for b in (country.get("skill_assessment_bodies") or []) if b.get("body_id") == body["body_id"] or b.get("name") == body["name"]]
    if existing:
        await countries_col.update_one(
            {"country_code": code, "skill_assessment_bodies.body_id": existing[0]["body_id"]},
            {"$set": {"skill_assessment_bodies.$": {**existing[0], **body}, "updated_at": datetime.now(timezone.utc)}}
        )
    else:
        await countries_col.update_one(
            {"country_code": code},
            {"$push": {"skill_assessment_bodies": body}, "$set": {"updated_at": datetime.now(timezone.utc)}}
        )
    return {"ok": True, "body_id": body["body_id"]}


@router.delete("/countries/{country_code}/skill-bodies/{body_id}")
async def delete_skill_body(country_code: str, body_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = country_code.upper()
    r = await countries_col.update_one(
        {"country_code": code},
        {"$pull": {"skill_assessment_bodies": {"body_id": body_id}}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="Skill body not found")
    return {"ok": True}


# ══════════════════════════════════════════════════════════════
# Occupation Codes
# ══════════════════════════════════════════════════════════════
@router.post("/countries/{country_code}/occupations")
async def add_or_update_occupation(country_code: str, req: OccupationUpsert, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = country_code.upper()
    occ = req.model_dump()

    country = await countries_col.find_one({"country_code": code}, {"occupation_codes": 1})
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    existing = [o for o in (country.get("occupation_codes") or []) if o.get("code") == occ["code"]]
    if existing:
        await countries_col.update_one(
            {"country_code": code, "occupation_codes.code": occ["code"]},
            {"$set": {"occupation_codes.$": {**existing[0], **occ}, "updated_at": datetime.now(timezone.utc)}}
        )
    else:
        await countries_col.update_one(
            {"country_code": code},
            {"$push": {"occupation_codes": occ}, "$set": {"updated_at": datetime.now(timezone.utc)}}
        )
    return {"ok": True, "code": occ["code"]}


@router.delete("/countries/{country_code}/occupations/{occ_code}")
async def delete_occupation(country_code: str, occ_code: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = country_code.upper()
    r = await countries_col.update_one(
        {"country_code": code},
        {"$pull": {"occupation_codes": {"code": occ_code}}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="Occupation not found")
    return {"ok": True}


# ══════════════════════════════════════════════════════════════
# Bulk Import (CSV)
# ══════════════════════════════════════════════════════════════
@router.post("/countries/{country_code}/bulk-import-occupations")
async def bulk_import_occupations(
    country_code: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """CSV columns: code,title,group,group_code,skill_level,assessing_body,pathway,eligible_visas,alternative_titles,state_demand_NSW,state_demand_VIC,etc.
    Eligible_visas + alternative_titles: pipe-separated (|). State demand columns optional.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    code = country_code.upper()
    country = await countries_col.find_one({"country_code": code}, {"occupation_codes": 1})
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV too large (max 2MB)")

    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        decoded = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames or "code" not in reader.fieldnames or "title" not in reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must have at least 'code' and 'title' columns")

    inserted = 0
    updated = 0
    errors: List[str] = []
    existing_codes = {o.get("code") for o in (country.get("occupation_codes") or [])}

    new_occs: List[Dict[str, Any]] = []
    update_occs: List[Dict[str, Any]] = []
    for row_no, row in enumerate(reader, start=2):
        try:
            occ_code = (row.get("code") or "").strip()
            title = (row.get("title") or "").strip()
            if not occ_code or not title:
                errors.append(f"Row {row_no}: missing code/title — skipped")
                continue
            occ = {
                "code": occ_code,
                "title": title,
                "group": (row.get("group") or "").strip() or None,
                "group_code": (row.get("group_code") or "").strip() or None,
                "skill_level": int(row["skill_level"]) if row.get("skill_level", "").strip().isdigit() else None,
                "assessing_body": (row.get("assessing_body") or "").strip() or None,
                "pathway": (row.get("pathway") or "").strip() or None,
                "alternative_titles": [t.strip() for t in (row.get("alternative_titles") or "").split("|") if t.strip()],
                "eligible_visas": [v.strip() for v in (row.get("eligible_visas") or "").split("|") if v.strip()],
                "state_demand": {k.replace("state_demand_", ""): v.strip() for k, v in row.items() if k.startswith("state_demand_") and v and v.strip()},
            }
            if occ_code in existing_codes:
                update_occs.append(occ)
                updated += 1
            else:
                new_occs.append(occ)
                inserted += 1
        except (ValueError, KeyError) as e:
            errors.append(f"Row {row_no}: {e}")

    now = datetime.now(timezone.utc)
    if new_occs:
        await countries_col.update_one(
            {"country_code": code},
            {"$push": {"occupation_codes": {"$each": new_occs}}, "$set": {"updated_at": now}}
        )
    for occ in update_occs:
        await countries_col.update_one(
            {"country_code": code, "occupation_codes.code": occ["code"]},
            {"$set": {"occupation_codes.$": occ, "updated_at": now}}
        )

    return {"ok": True, "inserted": inserted, "updated": updated, "errors": errors[:20], "total_errors": len(errors)}


# ══════════════════════════════════════════════════════════════
# Search (cross-country)
# ══════════════════════════════════════════════════════════════
@router.get("/occupations/search")
async def search_occupations(
    q: str = Query(..., min_length=2),
    country_code: Optional[str] = None,
    limit: int = 25,
    current_user: dict = Depends(get_current_user),
):
    if not _is_viewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    query: Dict[str, Any] = {"is_active": True}
    if country_code:
        query["country_code"] = country_code.upper()

    results: List[Dict[str, Any]] = []
    async for c in countries_col.find(query, {"country": 1, "country_code": 1, "country_flag_emoji": 1, "occupation_codes": 1, "_id": 0}):
        q_low = q.lower()
        for occ in (c.get("occupation_codes") or []):
            if (q_low in (occ.get("code") or "").lower()
                or q_low in (occ.get("title") or "").lower()
                or any(q_low in t.lower() for t in (occ.get("alternative_titles") or []))):
                results.append({
                    **occ,
                    "country": c["country"],
                    "country_code": c["country_code"],
                    "country_flag_emoji": c.get("country_flag_emoji"),
                })
                if len(results) >= limit:
                    return {"items": results, "count": len(results)}
    return {"items": results, "count": len(results)}


@router.get("/skill-bodies/search")
async def search_skill_bodies(
    q: str = Query(..., min_length=2),
    country_code: Optional[str] = None,
    limit: int = 25,
    current_user: dict = Depends(get_current_user),
):
    if not _is_viewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    query: Dict[str, Any] = {"is_active": True}
    if country_code:
        query["country_code"] = country_code.upper()

    results: List[Dict[str, Any]] = []
    async for c in countries_col.find(query, {"country": 1, "country_code": 1, "country_flag_emoji": 1, "skill_assessment_bodies": 1, "_id": 0}):
        q_low = q.lower()
        for body in (c.get("skill_assessment_bodies") or []):
            if (q_low in (body.get("name") or "").lower()
                or q_low in (body.get("full_name") or "").lower()):
                results.append({**body, "country": c["country"], "country_code": c["country_code"], "country_flag_emoji": c.get("country_flag_emoji")})
                if len(results) >= limit:
                    return {"items": results, "count": len(results)}
    return {"items": results, "count": len(results)}


# ══════════════════════════════════════════════════════════════
# Re-seed (admin utility — useful after manual deletion)
# ══════════════════════════════════════════════════════════════
@router.post("/seed/run")
async def trigger_seed(current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    global _seed_done
    _seed_done = False  # Force re-check
    n = await seed_country_rules(countries_col)
    return {"ok": True, "inserted": n, "message": f"Seeded {n} new countries (existing data preserved)"}


# ══════════════════════════════════════════════════════════════
# Stats (for admin dashboard)
# ══════════════════════════════════════════════════════════════
@router.get("/stats")
async def kb_stats(current_user: dict = Depends(get_current_user)):
    if not _is_viewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    total_countries = 0
    active_countries = 0
    total_visas = 0
    total_bodies = 0
    total_occupations = 0
    async for c in countries_col.find({}, {"is_active": 1, "visa_categories": 1, "skill_assessment_bodies": 1, "occupation_codes": 1}):
        total_countries += 1
        if c.get("is_active"):
            active_countries += 1
        total_visas += len(c.get("visa_categories") or [])
        total_bodies += len(c.get("skill_assessment_bodies") or [])
        total_occupations += len(c.get("occupation_codes") or [])
    return {
        "total_countries": total_countries,
        "active_countries": active_countries,
        "total_visa_categories": total_visas,
        "total_skill_bodies": total_bodies,
        "total_occupations": total_occupations,
    }
