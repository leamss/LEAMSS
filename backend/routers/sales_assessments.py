"""Smart Sales Helper — Phase 6 v2 Part 3: Save Assessment + Create-PA Bridge.

Endpoints:
  POST   /api/sales/assessments              — save a completed assessment
  GET    /api/sales/assessments              — list (mine, scoped by role)
  GET    /api/sales/assessments/{id}         — fetch single
  POST   /api/sales/assessments/{id}/create-pa — 1-click bridge to PA workflow
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.sales_calculator import calculate

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
