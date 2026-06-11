"""Phase 18.3 — Feedback / Verification-Request flow.

Sales / case-manager users can flag an occupation that has incomplete data
(typically: missing `assessing_authority`, missing visa pathways, stale
verification, or a typo). Admin picks the request up from the Verification
Hub.

Collection: `feedback_requests`
Indexes (created on startup):
  - (status, requested_at desc)        — admin's open queue
  - (occupation_id, status)            — per-occupation history
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db, audit_logs_col

router = APIRouter(prefix="/feedback-requests", tags=["feedback-requests"])

FEEDBACK = db["feedback_requests"]
OCCUPATION_MASTER = db["occupation_master"]

VALID_REQUEST_TYPES = {"verification_request", "data_correction", "missing_data"}
VALID_REQUESTED_FIELDS = {
    "general", "assessing_authority", "visa_pathways", "required_documents",
    "qualification_rules", "sample_cases", "description", "typical_tasks",
}
VALID_STATUSES = {"open", "in_progress", "resolved", "rejected"}
# Phase 18.3 — guard regression: never let a resolved/rejected entry walk
# back to open via PATCH (would corrupt the admin queue history).
_TRANSITIONS = {
    "open": {"in_progress", "resolved", "rejected"},
    "in_progress": {"resolved", "rejected", "open"},  # admin may re-open if requester pings
    "resolved": set(),
    "rejected": set(),
}
ADMIN_ROLES = {"admin", "admin_owner"}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


async def _write_audit(user: dict, action: str, entity_id: str, extra=None):
    try:
        await audit_logs_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user.get("id"),
            "user_email": user.get("email"),
            "action": action,
            "entity_type": "feedback_request",
            "entity_id": entity_id,
            "extra": extra or {},
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:  # noqa: BLE001
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────
class FeedbackCreate(BaseModel):
    occupation_id: str = Field(..., min_length=1)
    request_type: str = "verification_request"
    requested_field: str = "general"
    message: Optional[str] = Field("", max_length=2000)


class FeedbackPatch(BaseModel):
    status: Optional[str] = None
    resolution_notes: Optional[str] = Field(None, max_length=2000)


def _strip(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc.pop("_id", None)
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# POST /feedback-requests — any authenticated user can file a request
# ─────────────────────────────────────────────────────────────────────────────
@router.post("")
async def create_feedback(req: FeedbackCreate, current_user: dict = Depends(get_current_user)):
    if req.request_type not in VALID_REQUEST_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid request_type. Use one of {sorted(VALID_REQUEST_TYPES)}")
    if req.requested_field not in VALID_REQUESTED_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid requested_field. Use one of {sorted(VALID_REQUESTED_FIELDS)}")

    # Resolve occupation context (canonical slug + title) for the admin queue.
    occ = await OCCUPATION_MASTER.find_one({"occupation_id": req.occupation_id}, {"_id": 0})
    if not occ and "-" in req.occupation_id:
        cc, _, code = req.occupation_id.partition("-")
        occ = await OCCUPATION_MASTER.find_one({"country_code": cc.upper(), "code": code}, {"_id": 0})
    if not occ:
        raise HTTPException(status_code=404, detail=f"Occupation '{req.occupation_id}' not found")

    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        "request_type": req.request_type,
        "occupation_id": occ.get("occupation_id") or req.occupation_id,
        "country_code": occ.get("country_code"),
        "code": occ.get("code"),
        "occupation_title": occ.get("title") or "",
        "requested_field": req.requested_field,
        "message": (req.message or "").strip(),
        "requested_by": current_user.get("id"),
        "requested_by_name": current_user.get("name") or current_user.get("email") or "user",
        "requested_by_role": current_user.get("rbac_role") or current_user.get("role") or "user",
        "requested_at": now,
        "status": "open",
        "resolved_by": None,
        "resolved_at": None,
        "resolution_notes": None,
    }
    await FEEDBACK.insert_one(doc)
    await _write_audit(current_user, "create_feedback_request", doc["id"],
                       extra={"occupation_id": doc["occupation_id"], "requested_field": doc["requested_field"]})
    return _strip({**doc})


# ─────────────────────────────────────────────────────────────────────────────
# GET /feedback-requests — admin queue
# ─────────────────────────────────────────────────────────────────────────────
@router.get("")
async def list_feedback(
    status: Optional[str] = Query(None),
    occupation_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    q: dict = {}
    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Use one of {sorted(VALID_STATUSES)}")
        q["status"] = status
    if occupation_id:
        q["occupation_id"] = occupation_id
    skip = (page - 1) * page_size
    cursor = FEEDBACK.find(q, {"_id": 0}).sort([("requested_at", -1)]).skip(skip).limit(page_size)
    items = [d async for d in cursor]
    total = await FEEDBACK.count_documents(q)
    open_count = await FEEDBACK.count_documents({"status": "open"})
    in_progress_count = await FEEDBACK.count_documents({"status": "in_progress"})
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "counts": {
            "open": open_count,
            "in_progress": in_progress_count,
            "all_pending": open_count + in_progress_count,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /feedback-requests/{id} — admin updates status / resolution notes
# ─────────────────────────────────────────────────────────────────────────────
@router.patch("/{feedback_id}")
async def patch_feedback(feedback_id: str, req: FeedbackPatch, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await FEEDBACK.find_one({"id": feedback_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Feedback request not found")
    set_payload: dict = {}
    if req.status is not None:
        if req.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Use one of {sorted(VALID_STATUSES)}")
        cur = existing.get("status") or "open"
        if req.status != cur and req.status not in _TRANSITIONS.get(cur, set()):
            raise HTTPException(status_code=400, detail=f"Illegal status transition: {cur} → {req.status}")
        set_payload["status"] = req.status
        if req.status in ("resolved", "rejected"):
            set_payload["resolved_by"] = current_user.get("id")
            set_payload["resolved_at"] = datetime.now(timezone.utc)
    if req.resolution_notes is not None:
        set_payload["resolution_notes"] = req.resolution_notes.strip()
    if not set_payload:
        raise HTTPException(status_code=400, detail="Nothing to update")
    await FEEDBACK.update_one({"id": feedback_id}, {"$set": set_payload})
    await _write_audit(current_user, "patch_feedback_request", feedback_id, extra=set_payload)
    refreshed = await FEEDBACK.find_one({"id": feedback_id}, {"_id": 0})
    return _strip(refreshed)


# ─────────────────────────────────────────────────────────────────────────────
# Startup-time index creation (idempotent)
# ─────────────────────────────────────────────────────────────────────────────
async def ensure_indexes():
    try:
        await FEEDBACK.create_index([("status", 1), ("requested_at", -1)], name="status_requested_at")
        await FEEDBACK.create_index([("occupation_id", 1), ("status", 1)], name="occupation_status")
    except Exception:  # noqa: BLE001
        pass
