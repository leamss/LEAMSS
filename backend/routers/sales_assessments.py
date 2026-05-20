"""Smart Sales Helper — Phase 6 v2 Part 3: Save Assessment + Create-PA Bridge.

Endpoints:
  POST   /api/sales/assessments              — save a completed assessment
  GET    /api/sales/assessments              — list (mine, scoped by role)
  GET    /api/sales/assessments/{id}         — fetch single
  POST   /api/sales/assessments/{id}/create-pa — 1-click bridge to PA workflow

  Phase 6.5 (May 19, 2026) — Checklist + Public Share:
  GET    /api/sales/assessments/{id}/checklist          — rule-based doc checklist
  POST   /api/sales/assessments/{id}/share              — generate public share token
  POST   /api/sales/assessments/{id}/share/revoke       — revoke share token
  GET    /api/sales/assessments/public/{token}          — public read-only view (no auth)
"""
import os
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.sales_calculator import calculate
from core.sales_checklist import build_checklist
from core.share_audit import record_share_event

router = APIRouter(prefix="/sales/assessments", tags=["Smart Sales Helper - Assessments"])

assessments_col = db["sales_assessments"]
pre_assessments_col = db["pre_assessments"]

ROLE_SALES = {
    "admin", "admin_owner", "sales_executive", "sr_sales_executive",
    "sales_manager", "sales_head", "partner", "case_manager",
}


def _user_role(user: dict) -> str:
    return user.get("rbac_role") or user.get("role") or ""


def _can_access(user: dict) -> bool:
    return _user_role(user) in ROLE_SALES or "*" in (user.get("permissions") or [])


def _strip(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


class TargetCalc(BaseModel):
    country: str
    visa_subclass: Optional[str] = None


class SaveAssessmentRequest(BaseModel):
    client_name: str
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    profile: Dict[str, Any]
    occupation: Optional[Dict[str, Any]] = None  # { country_code, code, title, assessing_body, pathway }
    targets: List[TargetCalc] = Field(..., min_length=1)
    final_notes: Optional[str] = None


@router.post("")
async def save_assessment(req: SaveAssessmentRequest, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    now = datetime.now(timezone.utc)
    assessment_id = f"SAH-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    # Run the calculator for each target to capture the snapshot
    results = []
    for t in req.targets:
        r = calculate(req.profile, t.country, t.visa_subclass)
        results.append(r)

    # Pick best target by points (or by recommendation language if scoring metric differs)
    best = max(results, key=lambda r: r.get("total", 0)) if results else None

    doc = {
        "id": assessment_id,
        "client_name": req.client_name,
        "client_email": req.client_email,
        "client_phone": req.client_phone,
        "profile_snapshot": req.profile,
        "occupation": req.occupation,
        "targets": [t.model_dump() for t in req.targets],
        "results": results,
        "best_country_code": best.get("country_code") if best else None,
        "best_total": best.get("total") if best else None,
        "best_recommendation": best.get("recommendation") if best else None,
        "final_notes": req.final_notes,
        "linked_pa_id": None,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name"),
        "created_at": now,
        "updated_at": now,
    }
    await assessments_col.insert_one(doc)
    return _strip(doc)


@router.get("")
async def list_assessments(
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    query: Dict[str, Any] = {} if is_admin else {"created_by": current_user["id"]}
    if search:
        query["client_name"] = {"$regex": search, "$options": "i"}
    items = []
    async for d in assessments_col.find(query, {"_id": 0, "profile_snapshot": 0, "results": 0}).sort("created_at", -1).limit(limit):
        items.append(_strip(d))
    return {"items": items, "count": len(items)}


@router.get("/{assessment_id}")
async def get_assessment(assessment_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    d = await assessments_col.find_one({"id": assessment_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Assessment not found")
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and d.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    return _strip(d)


@router.delete("/{assessment_id}")
async def delete_assessment(assessment_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    d = await assessments_col.find_one({"id": assessment_id})
    if not d:
        raise HTTPException(status_code=404, detail="Assessment not found")
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and d.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    await assessments_col.delete_one({"id": assessment_id})
    return {"ok": True}


# ════════════════════════════════════════════════════════════════
# 1-click bridge → Pre-Assessment workflow
# ════════════════════════════════════════════════════════════════
class CreatePARequest(BaseModel):
    target_country_code: Optional[str] = None  # Default: best from assessment
    target_visa_subclass: Optional[str] = None
    pa_title: Optional[str] = None
    lead_source: str = "smart_sales_helper"


@router.post("/{assessment_id}/create-pa")
async def create_pa_from_assessment(assessment_id: str, req: CreatePARequest, current_user: dict = Depends(get_current_user)):
    """Create a Pre-Assessment from a saved Smart Sales Helper assessment.
    Pre-fills client name + email + phone + occupation + country + visa from the assessment.
    """
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    a = await assessments_col.find_one({"id": assessment_id})
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if a.get("linked_pa_id"):
        return {"ok": True, "pa_id": a["linked_pa_id"], "already_linked": True}

    country = req.target_country_code or a.get("best_country_code") or "AU"
    occupation = a.get("occupation") or {}
    pa_id = f"PA-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc)
    pa_doc = {
        "id": pa_id,
        "title": req.pa_title or f"Assessment for {a.get('client_name')}",
        "client_name": a.get("client_name"),
        "client_email": a.get("client_email"),
        "client_phone": a.get("client_phone"),
        "destination_country": country,
        "visa_subclass": req.target_visa_subclass,
        "occupation_code": occupation.get("code"),
        "occupation_title": occupation.get("title"),
        "skill_assessment_body": occupation.get("assessing_body"),
        "pathway": occupation.get("pathway"),
        "source_smart_sales_assessment_id": assessment_id,
        "lead_source": req.lead_source,
        "status": "draft",
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name"),
        "created_at": now,
        "updated_at": now,
    }
    await pre_assessments_col.insert_one(pa_doc)
    await assessments_col.update_one({"id": assessment_id}, {"$set": {"linked_pa_id": pa_id, "updated_at": now}})
    return {"ok": True, "pa_id": pa_id, "already_linked": False}


# ════════════════════════════════════════════════════════════════
# Phase 6.5 — Document Checklist (rule-based, deterministic)
# ════════════════════════════════════════════════════════════════
@router.get("/{assessment_id}/checklist")
async def assessment_checklist(assessment_id: str, current_user: dict = Depends(get_current_user)):
    """Return a rule-based document checklist for the assessment.

    Driven by: best_country_code + occupation.assessing_body + targets[].visa_subclass + marital_status.
    """
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    a = await assessments_col.find_one({"id": assessment_id}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and a.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")

    profile = a.get("profile_snapshot") or {}
    marital = profile.get("marital_status")
    checklist = build_checklist(
        country_code=a.get("best_country_code") or "",
        occupation=a.get("occupation"),
        marital_status=marital,
        targets=a.get("targets") or [],
    )
    checklist["assessment_id"] = assessment_id
    checklist["client_name"] = a.get("client_name")
    return checklist


# ════════════════════════════════════════════════════════════════
# Phase 6.5 — Public Share Link (Save & Share Report)
# ════════════════════════════════════════════════════════════════
EXPIRY_DAYS_ALLOWED = {0, 1, 7, 30, 90}


class ShareRequest(BaseModel):
    expires_in_days: int = Field(30, ge=0, le=90)


@router.post("/{assessment_id}/share")
async def create_share_link(assessment_id: str, req: ShareRequest, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if req.expires_in_days not in EXPIRY_DAYS_ALLOWED:
        raise HTTPException(status_code=422, detail=f"expires_in_days must be one of {sorted(EXPIRY_DAYS_ALLOWED)}")
    a = await assessments_col.find_one({"id": assessment_id})
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and a.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")

    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(24)
    expires_at = None if req.expires_in_days == 0 else now + timedelta(days=req.expires_in_days)
    share_doc = {
        "share_token": token,
        "share_active": True,
        "share_revoked": False,
        "share_issued_at": now,
        "share_issued_by": current_user["id"],
        "share_expires_at": expires_at,
        "share_click_count": 0,
        "share_last_accessed_at": None,
        "share_last_accessed_ip": None,
        "share_last_accessed_ua": None,
        "updated_at": now,
    }
    await assessments_col.update_one({"id": assessment_id}, {"$set": share_doc})

    # Audit log
    await record_share_event(
        event_type="share_generated",
        share_type="sales_report",
        share_token=token,
        reference_id=assessment_id,
        reference_kind="sales_assessment",
        client_name=a.get("client_name"),
        client_email=a.get("client_email"),
        actor_id=current_user.get("id"),
        actor_email=current_user.get("email"),
        actor_role=role,
        details={"expires_in_days": req.expires_in_days, "expires_at": expires_at.isoformat() if expires_at else None},
    )

    frontend_base = (os.environ.get("FRONTEND_URL") or os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
    return {
        "ok": True,
        "token": token,
        "public_url": f"{frontend_base}/sales/report/{token}",
        "expires_at": expires_at.isoformat() if expires_at else None,
        "expires_in_days": req.expires_in_days,
    }


@router.post("/{assessment_id}/share/revoke")
async def revoke_share_link(assessment_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    a = await assessments_col.find_one({"id": assessment_id})
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and a.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    if not a.get("share_token"):
        raise HTTPException(status_code=400, detail="No share link to revoke")
    now = datetime.now(timezone.utc)
    await assessments_col.update_one(
        {"id": assessment_id},
        {"$set": {"share_active": False, "share_revoked": True, "share_revoked_at": now, "updated_at": now}},
    )
    # Audit log
    await record_share_event(
        event_type="share_revoked",
        share_type="sales_report",
        share_token=a.get("share_token"),
        reference_id=assessment_id,
        reference_kind="sales_assessment",
        client_name=a.get("client_name"),
        client_email=a.get("client_email"),
        actor_id=current_user.get("id"),
        actor_email=current_user.get("email"),
        actor_role=role,
        details={"source": "assessment_page"},
    )
    return {"ok": True}


def _sanitise_public(a: dict) -> dict:
    """Strip internal/PII fields from a public share view."""
    profile = a.get("profile_snapshot") or {}
    primary = (profile.get("primary_applicant") or {})
    # Best-effort client display (mask email/phone)
    name = a.get("client_name") or "Applicant"
    return {
        "id": a.get("id"),
        "client_name": name,
        "best_country_code": a.get("best_country_code"),
        "best_total": a.get("best_total"),
        "best_recommendation": a.get("best_recommendation"),
        "occupation": a.get("occupation"),
        "targets": a.get("targets") or [],
        "results": a.get("results") or [],
        "marital_status": profile.get("marital_status"),
        "highlights": {
            "age": (primary.get("personal") or {}).get("age"),
            "qualification": (primary.get("education") or {}).get("highest_qualification"),
            "ielts_overall": ((primary.get("language") or {}).get("scores") or {}).get("overall"),
            "experience_years": (primary.get("professional") or {}).get("years_experience_total"),
            "current_profession": (primary.get("professional") or {}).get("current_profession"),
        },
        "created_at": a.get("created_at").isoformat() if isinstance(a.get("created_at"), datetime) else a.get("created_at"),
        "prepared_by": a.get("created_by_name"),
    }


@router.get("/public/{token}")
async def public_share_view(token: str, request: Request):
    """No-auth public read-only view of the assessment by share token."""
    a = await assessments_col.find_one({"share_token": token})
    # Capture request context up-front so we can log denied attempts too
    req_ip = request.client.host if request.client else None
    req_ua = request.headers.get("user-agent", "")[:240]

    async def _log_denied(reason: str, doc: dict | None):
        """Audit-log a denied access attempt (scraping signal). Best-effort."""
        try:
            await record_share_event(
                event_type="share_access_denied",
                share_type="sales_report",
                share_token=token,
                reference_id=(doc or {}).get("id"),
                reference_kind="sales_assessment",
                client_name=(doc or {}).get("client_name"),
                client_email=(doc or {}).get("client_email"),
                actor_role="anonymous",
                ip_address=req_ip,
                user_agent=req_ua,
                details={"reason": reason},
            )
        except Exception:
            pass

    if not a:
        # Don't log for completely-unknown tokens (random-scanner noise)
        raise HTTPException(status_code=404, detail="Link not found")
    if a.get("share_revoked"):
        await _log_denied("revoked", a)
        raise HTTPException(status_code=410, detail="Link revoked by issuer")
    if not a.get("share_active"):
        await _log_denied("inactive", a)
        raise HTTPException(status_code=410, detail="Link no longer active")
    expires_at = a.get("share_expires_at")
    if expires_at:
        if isinstance(expires_at, datetime):
            exp_dt = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        else:
            try:
                exp_dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            except Exception:
                exp_dt = None
        if exp_dt and datetime.now(timezone.utc) > exp_dt:
            await _log_denied("expired", a)
            raise HTTPException(status_code=410, detail="Link expired")
    # Track access
    now = datetime.now(timezone.utc)
    ip = req_ip
    ua = req_ua
    await assessments_col.update_one(
        {"share_token": token},
        {
            "$inc": {"share_click_count": 1},
            "$set": {"share_last_accessed_at": now, "share_last_accessed_ip": ip, "share_last_accessed_ua": ua},
        },
    )
    # Resolve IP geo (best-effort, cached). None for private/local IPs.
    geo = None
    try:
        from core.ip_geo import lookup_ip
        geo = await lookup_ip(ip)
    except Exception:
        pass
    # Audit log (best-effort — public access)
    try:
        await record_share_event(
            event_type="share_accessed",
            share_type="sales_report",
            share_token=token,
            reference_id=a.get("id"),
            reference_kind="sales_assessment",
            client_name=a.get("client_name"),
            client_email=a.get("client_email"),
            actor_role="anonymous",
            ip_address=ip,
            user_agent=ua,
            details={"click_count": (a.get("share_click_count") or 0) + 1, "geo": geo},
        )
    except Exception:
        pass  # Never block public access if audit insert fails
    # Include checklist summary
    profile = a.get("profile_snapshot") or {}
    checklist = build_checklist(
        country_code=a.get("best_country_code") or "",
        occupation=a.get("occupation"),
        marital_status=profile.get("marital_status"),
        targets=a.get("targets") or [],
    )
    payload = _sanitise_public(a)
    payload["checklist"] = checklist
    payload["expires_at"] = expires_at.isoformat() if isinstance(expires_at, datetime) else expires_at
    return payload
