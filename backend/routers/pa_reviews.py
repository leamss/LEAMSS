"""Phase 20.5 — Admin Pre-Assessment Review Queue.

Backs the admin workflow where Pre-Assessments are submitted with documents
and need human admin review before progressing to Proposal stage.

Statuses: pending | approved | rejected | refunded | closed

Reject actions:
  - request_more_docs (returns PA to client for more uploads)
  - close_case (archives the case, no refund)
  - refund (initiates refund flow + closes case)

All writes register Phase 19.6 revocable batches + audit-logged.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/pa-reviews", tags=["Phase 20.5 PA Review Queue"])

REVIEWS_COLL = "pre_assessment_reviews"
PA_COLL = "pre_assessments"
INFO_SHEETS_COLL = "information_sheets"

ADMIN_ROLES = {"admin", "admin_owner", "super_admin", "case_manager", "case_manager_lead"}
REVIEW_STATUSES = {"pending", "approved", "rejected", "refunded", "closed"}
REJECTION_ACTIONS = {"request_more_docs", "close_case", "refund"}


def _is_admin(u: Dict[str, Any]) -> bool:
    role = (u.get("rbac_role") or u.get("role") or "").lower()
    return role in ADMIN_ROLES or "*" in (u.get("permissions") or [])


async def ensure_review_record(db_, pa: Dict[str, Any]) -> Dict[str, Any]:
    """Idempotent: create or fetch the review record for a PA when it enters under_review.

    Called from PA `submit-documents` endpoint and on-demand by admin listing.
    """
    existing = await db_[REVIEWS_COLL].find_one({"pa_id": pa["id"]})
    if existing:
        return existing
    # Find linked info sheet
    sheet = await db_[INFO_SHEETS_COLL].find_one({
        "$or": [
            {"entity_type": "client", "entity_id": pa.get("client_user_id") or pa.get("client_id")},
            {"entity_type": "case", "entity_id": pa.get("id")},
            {"case_id": pa.get("case_id")},
        ],
    })
    now = datetime.now(timezone.utc)
    record = {
        "id": str(uuid.uuid4()), "pa_id": pa["id"],
        "client_id": pa.get("client_user_id") or pa.get("client_id"),
        "client_name": pa.get("client_name"),
        "client_email": pa.get("client_email"),
        "product_id": pa.get("product_id"),
        "country": pa.get("country"), "service_type": pa.get("service_type"),
        "pre_assessment_fee": pa.get("pre_assessment_fee"),
        "info_sheet_id": sheet["id"] if sheet else None,
        "submitted_at": pa.get("submitted_at") or now,
        "submitted_by": pa.get("partner_id"),
        "status": "pending",
        "reviewed_by": None, "reviewed_at": None,
        "review_notes": None,
        "rejection_action": None, "refund_amount_inr": None,
        "audit_trail": [{"action": "created", "by": "system",
                         "at": now.isoformat(), "pa_id": pa["id"]}],
        "created_at": now, "updated_at": now,
    }
    await db_[REVIEWS_COLL].insert_one(record)
    return record


# ── Pydantic ──────────────────────────────────────────────────────────────────
class ApproveRequest(BaseModel):
    notes: str = Field(default="", max_length=2000)


class RejectRequest(BaseModel):
    action: str = Field(..., pattern=r"^(request_more_docs|close_case|refund)$")
    reason: str = Field(..., min_length=10, max_length=2000)
    refund_amount_inr: Optional[int] = Field(None, ge=0, le=1_000_000)


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("")
async def list_reviews(
    status: str = "pending", limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    if status not in REVIEW_STATUSES and status != "all":
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    q: Dict[str, Any] = {} if status == "all" else {"status": status}
    # Auto-ingest any PAs in `under_review` that don't have a record yet
    async for pa in db[PA_COLL].find({"stage": "under_review"}):
        await ensure_review_record(db, pa)
    rows: List[Dict[str, Any]] = []
    async for r in db[REVIEWS_COLL].find(q, {"_id": 0}).sort("submitted_at", -1).limit(limit):
        for k, v in list(r.items()):
            if isinstance(v, datetime):
                r[k] = v.isoformat()
        rows.append(r)
    return {"reviews": rows, "count": len(rows), "status_filter": status}


@router.get("/{review_id}")
async def get_review(
    review_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    rec = await db[REVIEWS_COLL].find_one({"id": review_id}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Review not found")
    for k, v in list(rec.items()):
        if isinstance(v, datetime):
            rec[k] = v.isoformat()
    pa = await db[PA_COLL].find_one({"id": rec["pa_id"]}, {"_id": 0})
    if pa:
        for k, v in list(pa.items()):
            if isinstance(v, datetime):
                pa[k] = v.isoformat()
    sheet = None
    if rec.get("info_sheet_id"):
        sheet = await db[INFO_SHEETS_COLL].find_one({"id": rec["info_sheet_id"]}, {"_id": 0})
        if sheet:
            for k, v in list(sheet.items()):
                if isinstance(v, datetime):
                    sheet[k] = v.isoformat()
    return {"review": rec, "pa": pa, "info_sheet": sheet}


@router.post("/{review_id}/approve")
async def approve_review(
    review_id: str, payload: ApproveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    rec = await db[REVIEWS_COLL].find_one({"id": review_id})
    if not rec:
        raise HTTPException(status_code=404, detail="Review not found")
    if rec["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve from status: {rec['status']}")

    user_id = str(current_user.get("id") or "admin")
    user_name = current_user.get("name") or current_user.get("email")
    now = datetime.now(timezone.utc)

    body = f"approve_{review_id}_{user_id}".encode()
    batch = await ibs.open_batch(
        db, ingestion_path="phase_20.5_pa_review.approve",
        endpoint=f"POST /api/admin/pa-reviews/{review_id}/approve",
        uploaded_by=user_id, uploaded_by_name=user_name,
        file_name=f"approve_{review_id}", file_hash=ibs.file_sha256(body),
        file_size_bytes=len(body), target_collection=REVIEWS_COLL,
    )

    audit_entry = {"action": "approved", "by": user_id, "by_name": user_name,
                   "at": now.isoformat(), "notes": payload.notes}
    await db[REVIEWS_COLL].update_one(
        {"id": review_id},
        {"$set": {"status": "approved", "reviewed_by": user_id,
                  "reviewed_at": now, "review_notes": payload.notes,
                  "updated_at": now},
         "$push": {"audit_trail": audit_entry}},
    )
    # Update PA stage → admin_approved (unlocks proposal flow)
    await db[PA_COLL].update_one(
        {"id": rec["pa_id"]},
        {"$set": {"stage": "admin_approved",
                  "admin_approved_at": now,
                  "admin_approved_by": user_id,
                  "updated_at": now}},
    )
    ibs.record_update(batch, review_id, {"id": review_id}, rec)
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(db, action="pa_review.approve", user_id=user_id,
                     user_name=user_name, severity="info",
                     summary={"review_id": review_id, "pa_id": rec["pa_id"],
                              "batch_id": batch["batch_id"]})
    return {"ok": True, "review_id": review_id, "status": "approved",
            "pa_id": rec["pa_id"], "next_stage": "admin_approved",
            "batch_id": batch["batch_id"], "revocable": True}


@router.post("/{review_id}/reject")
async def reject_review(
    review_id: str, payload: RejectRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    rec = await db[REVIEWS_COLL].find_one({"id": review_id})
    if not rec:
        raise HTTPException(status_code=404, detail="Review not found")
    if rec["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot reject from status: {rec['status']}")

    user_id = str(current_user.get("id") or "admin")
    user_name = current_user.get("name") or current_user.get("email")
    now = datetime.now(timezone.utc)

    # Map action → final status
    new_status_map = {
        "request_more_docs": "rejected",
        "close_case": "closed",
        "refund": "refunded",
    }
    new_status = new_status_map[payload.action]
    pa_new_stage = {
        "request_more_docs": "payment_received",  # back to docs upload
        "close_case": "admin_rejected",
        "refund": "refunded",
    }[payload.action]

    body = f"reject_{review_id}_{payload.action}".encode()
    batch = await ibs.open_batch(
        db, ingestion_path=f"phase_20.5_pa_review.{payload.action}",
        endpoint=f"POST /api/admin/pa-reviews/{review_id}/reject",
        uploaded_by=user_id, uploaded_by_name=user_name,
        file_name=f"reject_{review_id}", file_hash=ibs.file_sha256(body),
        file_size_bytes=len(body), target_collection=REVIEWS_COLL,
    )

    refund_amount = None
    if payload.action == "refund":
        refund_amount = payload.refund_amount_inr or rec.get("pre_assessment_fee") or 0

    audit_entry = {
        "action": f"reject_{payload.action}", "by": user_id, "by_name": user_name,
        "at": now.isoformat(), "reason": payload.reason,
        "refund_amount_inr": refund_amount,
    }
    await db[REVIEWS_COLL].update_one(
        {"id": review_id},
        {"$set": {"status": new_status, "reviewed_by": user_id,
                  "reviewed_at": now, "review_notes": payload.reason,
                  "rejection_action": payload.action,
                  "refund_amount_inr": refund_amount, "updated_at": now},
         "$push": {"audit_trail": audit_entry}},
    )
    await db[PA_COLL].update_one(
        {"id": rec["pa_id"]},
        {"$set": {"stage": pa_new_stage,
                  "admin_rejected_at": now if payload.action != "request_more_docs" else None,
                  "admin_rejected_by": user_id if payload.action != "request_more_docs" else None,
                  "admin_rejected_reason": payload.reason,
                  "refund_amount_inr": refund_amount,
                  "updated_at": now}},
    )
    ibs.record_update(batch, review_id, {"id": review_id}, rec)
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(
        db, action=f"pa_review.{payload.action}",
        user_id=user_id, user_name=user_name,
        severity="warn" if payload.action == "refund" else "info",
        summary={"review_id": review_id, "pa_id": rec["pa_id"],
                 "action": payload.action, "reason": payload.reason,
                 "refund_amount": refund_amount, "batch_id": batch["batch_id"]},
    )
    return {"ok": True, "review_id": review_id, "status": new_status,
            "pa_id": rec["pa_id"], "next_pa_stage": pa_new_stage,
            "refund_amount_inr": refund_amount, "batch_id": batch["batch_id"],
            "revocable": True}
