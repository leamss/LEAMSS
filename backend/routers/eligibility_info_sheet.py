"""Phase 6.7 Part 2 — Client Self-Service Info Sheet workflow.

Allows admin/partner to send a public link to the client so they can self-fill
the basic Phase 6.7 fields. After submission, the profile lands in a "pending review"
queue where the partner approves before running the AI analysis.

Flow:
  1. Admin/Partner clicks "Send Info Sheet to Client" on a profile (or starts fresh)
     → POST /api/eligibility/info-sheet/generate-link/{profile_id?}
     → returns a public URL (/info-sheet/{token})
  2. Client opens the link (NO LOGIN)
     → GET /api/eligibility/info-sheet/public/{token} — sees a friendly form
     → POST /api/eligibility/info-sheet/public/{token}/submit — submits their data
  3. Profile saved with status='pending_review' + link marked consumed
  4. Partner/Admin sees it in pending queue → GET /api/eligibility/info-sheet/pending
  5. Partner reviews + approves → POST /api/eligibility/info-sheet/{profile_id}/approve
     → status='complete' → ready for AI assessment
"""
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/eligibility/info-sheet", tags=["Phase 6.7 - Info Sheet"])

profiles_col = db["client_eligibility_profiles"]
links_col = db["eligibility_info_sheet_links"]

ROLE_VIEWERS = {"admin", "admin_owner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "partner", "case_manager", "hr_manager"}


def _user_role(user: dict) -> str:
    return user.get("rbac_role") or user.get("role") or ""


def _can_access(user: dict) -> bool:
    return _user_role(user) in ROLE_VIEWERS or "*" in (user.get("permissions") or [])


def _strip(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


class GenerateLinkRequest(BaseModel):
    profile_id: Optional[str] = None  # If supplied, send the info-sheet for an existing draft
    client_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    client_phone: Optional[str] = None
    expires_in_days: int = 14  # default 2-week expiry


class InfoSheetSubmission(BaseModel):
    """Minimal client-friendly schema — full version is in eligibility_profiles."""
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    current_country: Optional[str] = None
    current_city: Optional[str] = None
    marital_status: Optional[str] = None  # single | married | de_facto | etc

    # Professional
    current_profession: Optional[str] = None
    designation: Optional[str] = None
    years_experience_total: Optional[float] = 0
    employer_name: Optional[str] = None
    industry: Optional[str] = None

    # Education
    highest_qualification: Optional[str] = None
    field_of_study: Optional[str] = None
    year_completed: Optional[int] = None

    # Language
    language_test_taken: Optional[bool] = False
    language_overall_score: Optional[float] = None

    # Spouse (only if married/de_facto)
    spouse_full_name: Optional[str] = None
    spouse_age: Optional[int] = None
    spouse_profession: Optional[str] = None
    spouse_education: Optional[str] = None
    spouse_english_overall: Optional[float] = None
    spouse_on_visa: Optional[bool] = True

    # Preferences
    preferred_countries: List[str] = Field(default_factory=list)
    timeline_months: Optional[int] = 12


# ══════════════════════════════════════════════════════════════
# 1. Generate a public link (admin/partner)
# ══════════════════════════════════════════════════════════════
@router.post("/generate-link")
async def generate_info_sheet_link(req: GenerateLinkRequest, request: Request, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=max(1, min(req.expires_in_days, 90)))

    profile_id = req.profile_id
    if profile_id:
        existing = await profiles_col.find_one({"id": profile_id}, {"_id": 0, "id": 1})
        if not existing:
            raise HTTPException(status_code=404, detail="Profile not found")
    else:
        # Create a stub draft profile to anchor the link to
        profile_id = f"ELG-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        await profiles_col.insert_one({
            "id": profile_id,
            "name": req.client_name or "Awaiting Client",
            "email": req.client_email,
            "phone": req.client_phone,
            "marital_status": None,
            "schema_version": 2,
            "primary_applicant": {},
            "spouse": None,
            "dependents": [],
            "status": "awaiting_info_sheet",
            "info_sheet_invited_by": current_user["id"],
            "info_sheet_invited_at": now,
            "created_by": current_user["id"],
            "created_by_name": current_user.get("name"),
            "created_at": now,
            "updated_at": now,
        })

    doc = {
        "token": token,
        "profile_id": profile_id,
        "expires_at": expires_at,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name"),
        "created_at": now,
        "used": False,
        "used_at": None,
        "used_ip": None,
        "used_ua": None,
        "client_name_hint": req.client_name,
        "client_email_hint": req.client_email,
    }
    await links_col.insert_one(doc)

    # Build public URL — prefer FRONTEND_URL env (set via deployment), fallback to base_url
    import os as _os
    base = _os.environ.get("FRONTEND_URL") or _os.environ.get("REACT_APP_BACKEND_URL")
    if not base:
        base = str(request.base_url).rstrip("/")
    base = base.rstrip("/")
    # If base accidentally has /api suffix, strip it
    if base.endswith("/api"):
        base = base[:-4]
    public_url = f"{base}/info-sheet/{token}"

    return {
        "ok": True,
        "token": token,
        "profile_id": profile_id,
        "public_url": public_url,
        "expires_at": expires_at.isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# 2. Client opens the public link (NO AUTH)
# ══════════════════════════════════════════════════════════════
@router.get("/public/{token}")
async def public_get_link(token: str):
    link = await links_col.find_one({"token": token}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    if link.get("used"):
        raise HTTPException(status_code=410, detail="This link has already been submitted")
    expires = link.get("expires_at")
    if expires:
        if isinstance(expires, str):
            try:
                expires = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            except ValueError:
                expires = None
        # Normalize tz: Mongo stores as naive UTC; compare apples to apples
        if isinstance(expires, datetime):
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                raise HTTPException(status_code=410, detail="This link has expired")

    profile = await profiles_col.find_one({"id": link["profile_id"]}, {"_id": 0, "name": 1, "email": 1, "phone": 1, "info_sheet_invited_by": 1, "info_sheet_invited_at": 1})
    invited_by = ""
    if profile and profile.get("info_sheet_invited_by"):
        inviter = await db["users"].find_one({"id": profile["info_sheet_invited_by"]}, {"_id": 0, "name": 1})
        if inviter:
            invited_by = inviter.get("name") or ""

    return {
        "ok": True,
        "token": token,
        "expires_at": link.get("expires_at").isoformat() if isinstance(link.get("expires_at"), datetime) else link.get("expires_at"),
        "prefill": {
            "full_name": (profile or {}).get("name") if (profile or {}).get("name") != "Awaiting Client" else "",
            "email": (profile or {}).get("email") or link.get("client_email_hint"),
            "phone": (profile or {}).get("phone"),
        },
        "invited_by": invited_by,
    }


# ══════════════════════════════════════════════════════════════
# 3. Client submits the info sheet (NO AUTH)
# ══════════════════════════════════════════════════════════════
@router.post("/public/{token}/submit")
async def public_submit(token: str, payload: InfoSheetSubmission, request: Request):
    link = await links_col.find_one({"token": token})
    if not link:
        raise HTTPException(status_code=404, detail="Invalid link")
    if link.get("used"):
        raise HTTPException(status_code=410, detail="Already submitted")
    expires = link.get("expires_at")
    if expires:
        if isinstance(expires, datetime) and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if isinstance(expires, datetime) and expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Link has expired")

    now = datetime.now(timezone.utc)
    # Map client-friendly fields → Phase 6.7 nested structure
    primary_applicant = {
        "personal": {
            "full_name": payload.full_name,
            "date_of_birth": payload.date_of_birth,
            "nationality": payload.nationality,
            "current_country": payload.current_country,
            "current_city": payload.current_city,
        },
        "professional": {
            "current_profession": payload.current_profession,
            "designation": payload.designation,
            "years_experience_total": payload.years_experience_total or 0,
            "employer_name": payload.employer_name,
            "industry": payload.industry,
        },
        "education": {
            "highest_qualification": payload.highest_qualification,
            "field_of_study": payload.field_of_study,
            "year_completed": payload.year_completed,
        },
        "language": {
            "primary_test": "IELTS",
            "test_completed": bool(payload.language_test_taken),
            "scores": {"overall": payload.language_overall_score} if payload.language_overall_score else {},
        },
    }
    spouse_block = None
    if payload.marital_status in ("married", "de_facto") and (payload.spouse_full_name or payload.spouse_profession):
        spouse_block = {
            "is_applicant_on_visa": bool(payload.spouse_on_visa),
            "contribution_type": "not_applicable",  # admin/partner will set this during review
            "is_australian_pr_or_citizen": False,
            "personal": {"full_name": payload.spouse_full_name, "age": payload.spouse_age},
            "professional": {"current_profession": payload.spouse_profession} if payload.spouse_profession else {},
            "education": {"highest_qualification": payload.spouse_education} if payload.spouse_education else {},
            "language": {"primary_test": "IELTS", "scores": {"overall": payload.spouse_english_overall}} if payload.spouse_english_overall else {},
        }

    update = {
        "name": payload.full_name,
        "email": payload.email,
        "phone": payload.phone,
        "marital_status": payload.marital_status or "single",
        "primary_applicant": primary_applicant,
        "spouse": spouse_block,
        "preferences": {
            "preferred_countries": payload.preferred_countries or [],
            "timeline_months": payload.timeline_months or 12,
            "search_mode": "top_3",
        },
        "schema_version": 2,
        "status": "pending_review",
        "info_sheet_submitted_at": now,
        "info_sheet_submitted_ip": (request.client.host if request.client else None),
        "info_sheet_submitted_ua": request.headers.get("user-agent", "")[:200],
        "updated_at": now,
    }
    await profiles_col.update_one({"id": link["profile_id"]}, {"$set": update})
    await links_col.update_one({"token": token}, {"$set": {
        "used": True,
        "used_at": now,
        "used_ip": (request.client.host if request.client else None),
        "used_ua": request.headers.get("user-agent", "")[:200],
    }})

    # Notify the inviter via notifications collection
    inviter_id = (await profiles_col.find_one({"id": link["profile_id"]}, {"_id": 0, "info_sheet_invited_by": 1}) or {}).get("info_sheet_invited_by")
    if inviter_id:
        await db["notifications"].insert_one({
            "id": str(uuid.uuid4()),
            "user_id": inviter_id,
            "type": "info_sheet_submitted",
            "title": "Client Info Sheet Submitted",
            "message": f"{payload.full_name} has submitted the eligibility info sheet — pending your review.",
            "link": f"/eligibility/profile/{link['profile_id']}",
            "read": False,
            "created_at": now,
        })

    return {"ok": True, "profile_id": link["profile_id"], "status": "pending_review"}


# ══════════════════════════════════════════════════════════════
# 4. Pending review queue (admin/partner)
# ══════════════════════════════════════════════════════════════
@router.get("/pending")
async def list_pending_reviews(current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])

    query: Dict[str, Any] = {"status": {"$in": ["pending_review", "awaiting_info_sheet"]}}
    if not is_admin:
        query["info_sheet_invited_by"] = current_user["id"]

    items: List[Dict[str, Any]] = []
    async for p in profiles_col.find(query).sort("updated_at", -1).limit(100):
        items.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "email": p.get("email"),
            "phone": p.get("phone"),
            "status": p.get("status"),
            "marital_status": p.get("marital_status"),
            "current_profession": ((p.get("primary_applicant") or {}).get("professional") or {}).get("current_profession"),
            "invited_by": p.get("info_sheet_invited_by"),
            "invited_at": (p.get("info_sheet_invited_at").isoformat() if isinstance(p.get("info_sheet_invited_at"), datetime) else p.get("info_sheet_invited_at")),
            "submitted_at": (p.get("info_sheet_submitted_at").isoformat() if isinstance(p.get("info_sheet_submitted_at"), datetime) else p.get("info_sheet_submitted_at")),
            "updated_at": p.get("updated_at").isoformat() if isinstance(p.get("updated_at"), datetime) else p.get("updated_at"),
        })
    return {"items": items, "count": len(items)}


# ══════════════════════════════════════════════════════════════
# 5. Approve a pending review (admin/partner)
# ══════════════════════════════════════════════════════════════
class ApproveRequest(BaseModel):
    note: Optional[str] = None
    spouse_contribution_type: Optional[str] = None  # if admin/partner sets it during review


@router.post("/{profile_id}/approve")
async def approve_pending(profile_id: str, req: ApproveRequest, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    profile = await profiles_col.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and profile.get("info_sheet_invited_by") != current_user["id"] and profile.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the inviter or an admin can approve this")
    if profile.get("status") not in ("pending_review", "awaiting_info_sheet"):
        raise HTTPException(status_code=400, detail=f"Profile is at status '{profile.get('status')}' — not pending review")

    update = {
        "status": "complete",
        "info_sheet_reviewed_at": datetime.now(timezone.utc),
        "info_sheet_reviewed_by": current_user["id"],
        "info_sheet_review_note": req.note,
        "updated_at": datetime.now(timezone.utc),
    }
    if req.spouse_contribution_type and profile.get("spouse"):
        spouse = dict(profile["spouse"])
        spouse["contribution_type"] = req.spouse_contribution_type
        update["spouse"] = spouse
    await profiles_col.update_one({"id": profile_id}, {"$set": update})
    return {"ok": True, "profile_id": profile_id, "status": "complete"}


# ══════════════════════════════════════════════════════════════
# 6. Revoke / regenerate link (admin/partner)
# ══════════════════════════════════════════════════════════════
@router.post("/revoke/{token}")
async def revoke_link(token: str, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    link = await links_col.find_one({"token": token})
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and link.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the issuer or an admin can revoke")
    await links_col.update_one({"token": token}, {"$set": {
        "revoked": True,
        "revoked_at": datetime.now(timezone.utc),
        "revoked_by": current_user["id"],
    }})
    return {"ok": True}
