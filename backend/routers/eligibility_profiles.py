"""Phase 6.2 — Smart Profile Form (Client Eligibility Profiles).

Collects detailed client profile data feeding the AI Eligibility Engine (Phase 6.3).
A profile can be:
  - Draft (in-progress wizard)
  - Complete (ready for assessment)
  - Assessed (already analysed; assessment_id linked)

Profiles can be pre-filled from an existing PA, duplicated, and linked back to a PA.
"""
import uuid
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/eligibility/profiles", tags=["Phase 6.2 - Eligibility Profiles"])

profiles_col = db["client_eligibility_profiles"]
pa_col = db["pre_assessments"]
users_col = db["users"]


ROLE_VIEWERS = {"admin", "admin_owner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "partner", "case_manager", "hr_manager"}


def _user_role(user: dict) -> str:
    return user.get("rbac_role") or user.get("role") or ""


def _can_access(user: dict) -> bool:
    return _user_role(user) in ROLE_VIEWERS or "*" in (user.get("permissions") or [])


def _can_see_profile(user: dict, profile: dict) -> bool:
    """Admin sees all; everyone else sees only what they created or PA they own."""
    role = _user_role(user)
    if role in ("admin", "admin_owner") or "*" in (user.get("permissions") or []):
        return True
    if profile.get("created_by") == user["id"]:
        return True
    # If linked to a PA owned by the user
    pa_id = profile.get("pa_id")
    if pa_id and (profile.get("pa_partner_id") == user["id"] or profile.get("pa_created_by_user_id") == user["id"]):
        return True
    return False


def _strip(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    for k, v in list(doc.items()):
        if isinstance(v, (datetime, date)):
            doc[k] = v.isoformat()
    return doc


# ══════════════════════════════════════════════════════════════
# Profile Section Models
# ══════════════════════════════════════════════════════════════
class BasicInfo(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None  # ISO YYYY-MM-DD
    age: Optional[int] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    dependents_count: Optional[int] = 0
    current_country: Optional[str] = None
    current_city: Optional[str] = None
    nationality: Optional[str] = None


class Professional(BaseModel):
    current_profession: Optional[str] = None
    designation: Optional[str] = None
    years_experience_total: Optional[float] = 0
    years_in_current_role: Optional[float] = 0
    industry: Optional[str] = None
    employer_name: Optional[str] = None
    salary_inr_per_annum: Optional[float] = None
    has_managerial_experience: Optional[bool] = False


class Education(BaseModel):
    highest_qualification: Optional[str] = None  # diploma | bachelor | master | doctorate | trade
    field_of_study: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None
    year_completed: Optional[int] = None
    additional_qualifications: List[Dict[str, Any]] = Field(default_factory=list)


class LanguageProficiency(BaseModel):
    primary_test: Optional[str] = None  # IELTS | PTE | TOEFL | none
    test_completed: Optional[bool] = False
    test_date: Optional[str] = None
    scores: Dict[str, Optional[float]] = Field(default_factory=dict)
    target_score: Optional[str] = None


class Family(BaseModel):
    spouse_present: Optional[bool] = False
    spouse_education: Optional[str] = None
    spouse_profession: Optional[str] = None
    spouse_language: Optional[str] = None
    children_count: Optional[int] = 0
    children_ages: List[int] = Field(default_factory=list)


class Finances(BaseModel):
    annual_household_income: Optional[float] = None
    savings_inr: Optional[float] = None
    budget_for_immigration_inr: Optional[float] = None
    able_to_show_funds: Optional[bool] = False


class Preferences(BaseModel):
    timeline_months: Optional[int] = 12
    preferred_countries: List[str] = Field(default_factory=list)
    avoiding_countries: List[str] = Field(default_factory=list)
    family_relocation: Optional[bool] = True
    priority: Optional[str] = None  # speed | cost | quality_of_life
    # Phase 6.2 — search mode selected during wizard
    search_mode: Optional[str] = None  # specific | top_3 | custom | top_5
    specific_country: Optional[str] = None
    custom_countries: List[str] = Field(default_factory=list)


class WorkHistoryEntry(BaseModel):
    employer: Optional[str] = None
    designation: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    country: Optional[str] = None
    duties: Optional[str] = None
    can_provide_reference: Optional[bool] = True


class AdditionalFactors(BaseModel):
    has_relative_in_target_country: Optional[bool] = False
    relative_relationship: Optional[str] = None
    has_job_offer: Optional[bool] = False
    state_preference: Optional[str] = None
    medical_concerns: Optional[str] = None
    criminal_record: Optional[bool] = False


class ProfileCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    pa_id: Optional[str] = None  # Pre-link to a PA at creation
    basic_info: Optional[BasicInfo] = None
    professional: Optional[Professional] = None
    education: Optional[Education] = None
    language_proficiency: Optional[LanguageProficiency] = None
    family: Optional[Family] = None
    finances: Optional[Finances] = None
    preferences: Optional[Preferences] = None
    work_history: List[WorkHistoryEntry] = Field(default_factory=list)
    additional_factors: Optional[AdditionalFactors] = None
    status: str = "draft"  # draft | complete | assessed


class ProfilePatch(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    basic_info: Optional[BasicInfo] = None
    professional: Optional[Professional] = None
    education: Optional[Education] = None
    language_proficiency: Optional[LanguageProficiency] = None
    family: Optional[Family] = None
    finances: Optional[Finances] = None
    preferences: Optional[Preferences] = None
    work_history: Optional[List[WorkHistoryEntry]] = None
    additional_factors: Optional[AdditionalFactors] = None
    status: Optional[str] = None


def _compute_age(dob: Optional[str]) -> Optional[int]:
    if not dob:
        return None
    try:
        d = datetime.fromisoformat(dob).date()
        today = date.today()
        return today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    except (ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════
@router.post("")
async def create_profile(req: ProfileCreate, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    now = datetime.now(timezone.utc)
    profile_id = f"ELG-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    payload = req.model_dump()
    # Compute age from DOB if missing
    if payload.get("basic_info") and not payload["basic_info"].get("age"):
        computed_age = _compute_age(payload["basic_info"].get("date_of_birth"))
        if computed_age is not None:
            payload["basic_info"]["age"] = computed_age

    # PA linkage — capture metadata for permission checks
    pa_meta = {}
    if payload.get("pa_id"):
        pa = await pa_col.find_one({"id": payload["pa_id"]}, {"_id": 0, "id": 1, "partner_id": 1, "created_by_user_id": 1, "client_name": 1, "pa_number": 1, "country": 1, "service_type": 1})
        if pa:
            pa_meta = {
                "pa_partner_id": pa.get("partner_id"),
                "pa_created_by_user_id": pa.get("created_by_user_id"),
                "pa_client_name": pa.get("client_name"),
                "pa_number": pa.get("pa_number"),
            }
        else:
            raise HTTPException(status_code=404, detail="Linked PA not found")

    doc = {
        "id": profile_id,
        **payload,
        **pa_meta,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name"),
        "created_at": now,
        "updated_at": now,
        "assessment_id": None,
    }
    await profiles_col.insert_one(doc)
    return _strip(doc)


@router.get("")
async def list_profiles(
    status: Optional[str] = None,
    pa_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    query: Dict[str, Any] = {}
    role = _user_role(current_user)
    if role not in ("admin", "admin_owner") and "*" not in (current_user.get("permissions") or []):
        query["$or"] = [
            {"created_by": current_user["id"]},
            {"pa_partner_id": current_user["id"]},
            {"pa_created_by_user_id": current_user["id"]},
        ]
    if status:
        query["status"] = status
    if pa_id:
        query["pa_id"] = pa_id
    if search:
        regex = {"$regex": search, "$options": "i"}
        query.setdefault("$or", []).extend([{"name": regex}, {"email": regex}, {"phone": regex}])

    items = []
    async for p in profiles_col.find(query).sort("updated_at", -1).limit(limit):
        items.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "email": p.get("email"),
            "phone": p.get("phone"),
            "status": p.get("status"),
            "search_mode": (p.get("preferences") or {}).get("search_mode"),
            "current_profession": (p.get("professional") or {}).get("current_profession"),
            "current_country": (p.get("basic_info") or {}).get("current_country"),
            "age": (p.get("basic_info") or {}).get("age"),
            "pa_id": p.get("pa_id"),
            "pa_number": p.get("pa_number"),
            "assessment_id": p.get("assessment_id"),
            "created_by": p.get("created_by"),
            "created_by_name": p.get("created_by_name"),
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"),
        })
        for k in ("created_at", "updated_at"):
            if isinstance(items[-1][k], datetime):
                items[-1][k] = items[-1][k].isoformat()
    return {"items": items, "count": len(items)}


@router.get("/{profile_id}")
async def get_profile(profile_id: str, current_user: dict = Depends(get_current_user)):
    doc = await profiles_col.find_one({"id": profile_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not _can_see_profile(current_user, doc):
        raise HTTPException(status_code=403, detail="Not authorised to view this profile")
    return _strip(doc)


@router.patch("/{profile_id}")
async def patch_profile(profile_id: str, req: ProfilePatch, current_user: dict = Depends(get_current_user)):
    existing = await profiles_col.find_one({"id": profile_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not _can_see_profile(current_user, existing):
        raise HTTPException(status_code=403, detail="Not authorised")

    updates = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    # Section-level merge (preserve untouched fields within a section)
    SECTIONS = {"basic_info", "professional", "education", "language_proficiency", "family", "finances", "preferences", "additional_factors"}
    merged_updates: Dict[str, Any] = {}
    for k, v in updates.items():
        if k in SECTIONS and isinstance(v, dict):
            current = existing.get(k) or {}
            merged_updates[k] = {**current, **v}
        else:
            merged_updates[k] = v

    # Recompute age if DOB changed
    if "basic_info" in merged_updates and isinstance(merged_updates["basic_info"], dict):
        dob = merged_updates["basic_info"].get("date_of_birth")
        if dob and not merged_updates["basic_info"].get("age"):
            ca = _compute_age(dob)
            if ca:
                merged_updates["basic_info"]["age"] = ca

    merged_updates["updated_at"] = datetime.now(timezone.utc)
    await profiles_col.update_one({"id": profile_id}, {"$set": merged_updates})
    doc = await profiles_col.find_one({"id": profile_id})
    return _strip(doc)


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str, current_user: dict = Depends(get_current_user)):
    existing = await profiles_col.find_one({"id": profile_id}, {"_id": 0, "created_by": 1})
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found")
    role = _user_role(current_user)
    if role not in ("admin", "admin_owner") and existing.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the creator or an admin can delete this profile")
    await profiles_col.delete_one({"id": profile_id})
    return {"ok": True}


@router.post("/{profile_id}/duplicate")
async def duplicate_profile(profile_id: str, current_user: dict = Depends(get_current_user)):
    src = await profiles_col.find_one({"id": profile_id})
    if not src:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not _can_see_profile(current_user, src):
        raise HTTPException(status_code=403, detail="Not authorised")
    now = datetime.now(timezone.utc)
    new_id = f"ELG-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    src.pop("_id", None)
    src["id"] = new_id
    src["name"] = f"{src.get('name', 'Profile')} (Copy)"
    src["status"] = "draft"
    src["assessment_id"] = None
    src["pa_id"] = None
    src["pa_partner_id"] = None
    src["pa_created_by_user_id"] = None
    src["pa_client_name"] = None
    src["pa_number"] = None
    src["created_at"] = now
    src["updated_at"] = now
    src["created_by"] = current_user["id"]
    src["created_by_name"] = current_user.get("name")
    await profiles_col.insert_one(src)
    return _strip(src)


@router.post("/{profile_id}/link-to-pa")
async def link_to_pa(profile_id: str, pa_id: str, current_user: dict = Depends(get_current_user)):
    profile = await profiles_col.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not _can_see_profile(current_user, profile):
        raise HTTPException(status_code=403, detail="Not authorised")
    pa = await pa_col.find_one({"id": pa_id}, {"_id": 0, "partner_id": 1, "created_by_user_id": 1, "client_name": 1, "pa_number": 1})
    if not pa:
        raise HTTPException(status_code=404, detail="PA not found")
    update = {
        "pa_id": pa_id,
        "pa_partner_id": pa.get("partner_id"),
        "pa_created_by_user_id": pa.get("created_by_user_id"),
        "pa_client_name": pa.get("client_name"),
        "pa_number": pa.get("pa_number"),
        "updated_at": datetime.now(timezone.utc),
    }
    await profiles_col.update_one({"id": profile_id}, {"$set": update})
    return {"ok": True, "pa_id": pa_id, "pa_number": pa.get("pa_number")}


@router.post("/{profile_id}/unlink-pa")
async def unlink_pa(profile_id: str, current_user: dict = Depends(get_current_user)):
    profile = await profiles_col.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not _can_see_profile(current_user, profile):
        raise HTTPException(status_code=403, detail="Not authorised")
    await profiles_col.update_one({"id": profile_id}, {
        "$set": {"pa_id": None, "pa_partner_id": None, "pa_created_by_user_id": None,
                 "pa_client_name": None, "pa_number": None,
                 "updated_at": datetime.now(timezone.utc)}
    })
    return {"ok": True}


@router.post("/prefill-from-pa/{pa_id}")
async def prefill_from_pa(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Pre-fills a new draft profile using data from an existing PA.
    Returns the pre-populated payload — frontend can use it as a starting point in the wizard
    BEFORE creating the profile (so user can review and edit first).
    """
    pa = await pa_col.find_one({"id": pa_id})
    if not pa:
        raise HTTPException(status_code=404, detail="PA not found")
    # Ownership / role check
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and pa.get("partner_id") != current_user["id"] and pa.get("created_by_user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorised to access this PA")

    prefill = {
        "name": pa.get("client_name") or "",
        "email": pa.get("client_email") or None,
        "phone": pa.get("client_mobile") or None,
        "pa_id": pa_id,
        "basic_info": {
            "full_name": pa.get("client_name"),
            "current_country": "India",  # default — user can override
        },
        "preferences": {
            "preferred_countries": [pa.get("country")] if pa.get("country") else [],
            "search_mode": "specific" if pa.get("country") else "top_3",
            "specific_country": _country_to_code(pa.get("country")),
        },
        "professional": {},
    }
    return prefill


def _country_to_code(country: Optional[str]) -> Optional[str]:
    mapping = {
        "australia": "AU", "canada": "CA", "new zealand": "NZ",
        "united kingdom": "UK", "uk": "UK", "usa": "US", "united states": "US",
        "germany": "DE",
    }
    if not country:
        return None
    return mapping.get(country.strip().lower())


@router.get("/stats/me")
async def my_stats(current_user: dict = Depends(get_current_user)):
    """Quick stats for the calling user — used by dashboards."""
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    query: Dict[str, Any] = {"created_by": current_user["id"]}
    total = await profiles_col.count_documents(query)
    drafts = await profiles_col.count_documents({**query, "status": "draft"})
    complete = await profiles_col.count_documents({**query, "status": "complete"})
    assessed = await profiles_col.count_documents({**query, "status": "assessed"})
    return {
        "total": total,
        "draft": drafts,
        "complete": complete,
        "assessed": assessed,
    }
