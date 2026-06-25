"""Phase 21 Slice 3 Day 1 — Reimbursement Claims.

Employee submits → manager approves → HR approves → eligible for next payroll run.
"""
import uuid
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.database import db, users_col
from core.auth import get_current_user

router = APIRouter(prefix="/reimbursements", tags=["Reimbursements"])

reimb_col = db["reimbursement_claims"]
activity_col = db["activity_log"]

# Phase 21 Slice 3 Backlog B.1 — bill file storage
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/backend/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BILL_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BILL_ALLOWED_MIME = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}

VALID_CATEGORIES = {
    "travel", "food", "office_supplies", "client_entertainment",
    "phone", "internet", "medical", "other",
}


def _is_manager(user: dict) -> bool:
    rbac = (user.get("rbac_role") or "").lower()
    return any(k in rbac for k in ["manager", "lead", "head"])


def _is_hr_or_admin(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    rbac = (user.get("rbac_role") or "").lower()
    if role == "admin" or "*" in (user.get("permissions") or []):
        return True
    return any(k in rbac for k in ["hr", "admin", "owner"])


def _serialize(d: dict) -> dict:
    out = dict(d)
    out.pop("_id", None)
    for k in ("created_at", "updated_at", "claim_date", "expense_date",
              "manager_approved_at", "hr_approved_at"):
        if isinstance(out.get(k), datetime):
            out[k] = out[k].isoformat()
    return out


class ReimbCreate(BaseModel):
    category: str
    amount_inr: int
    vendor_name: Optional[str] = ""
    description: str
    expense_date: str  # YYYY-MM-DD
    bills: List[dict] = Field(default_factory=list)  # [{file_url, file_name, mime_type}]


class ReimbAction(BaseModel):
    notes: Optional[str] = ""
    reason: Optional[str] = ""


@router.post("")
async def submit_reimbursement(payload: ReimbCreate, current_user: dict = Depends(get_current_user)):
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Allowed: {sorted(VALID_CATEGORIES)}")
    if payload.amount_inr <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if not payload.description.strip():
        raise HTTPException(status_code=400, detail="Description required")

    claim = {
        "id": str(uuid.uuid4()),
        "employee_id": current_user["id"],
        "employee_name": current_user.get("name"),
        "claim_date": datetime.now(timezone.utc).date().isoformat(),
        "expense_date": payload.expense_date,
        "category": payload.category,
        "amount_inr": payload.amount_inr,
        "currency": "INR",
        "vendor_name": payload.vendor_name or "",
        "description": payload.description.strip(),
        "bills": payload.bills or [],
        "status": "submitted",
        "manager_id": None,
        "manager_approved_at": None,
        "manager_notes": None,
        "hr_id": None,
        "hr_approved_at": None,
        "hr_notes": None,
        "rejected_by": None,
        "rejected_reason": None,
        "reimbursed_in_payslip_period": None,
        "payslip_id": None,
        "audit_log": [{
            "action": "submitted",
            "actor_id": current_user["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await reimb_col.insert_one(claim)
    return _serialize(claim)


@router.get("")
async def list_reimbursements(
    for_view: str = "me",  # me | team | all
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    q: dict = {}
    if for_view == "me":
        q["employee_id"] = current_user["id"]
    elif for_view == "team":
        if not _is_manager(current_user) and not _is_hr_or_admin(current_user):
            raise HTTPException(status_code=403, detail="Managers only")
        # Team = direct reports
        report_ids = []
        async for u in users_col.find({"reports_to": current_user["id"]}, {"_id": 0, "id": 1}):
            report_ids.append(u["id"])
        q["employee_id"] = {"$in": report_ids}
    elif for_view == "all":
        if not _is_hr_or_admin(current_user):
            raise HTTPException(status_code=403, detail="HR/admin only")
    if status:
        q["status"] = status
    items = []
    async for c in reimb_col.find(q, {"_id": 0}).sort("created_at", -1):
        items.append(_serialize(c))
    return items


@router.patch("/{claim_id}/manager-approve")
async def manager_approve(claim_id: str, payload: ReimbAction, current_user: dict = Depends(get_current_user)):
    if not (_is_manager(current_user) or _is_hr_or_admin(current_user)):
        raise HTTPException(status_code=403, detail="Managers/HR only")
    c = await reimb_col.find_one({"id": claim_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    if c.get("status") != "submitted":
        raise HTTPException(status_code=400, detail=f"Cannot approve from status '{c.get('status')}'")
    await reimb_col.update_one(
        {"id": claim_id},
        {"$set": {
            "status": "manager_approved",
            "manager_id": current_user["id"],
            "manager_approved_at": datetime.now(timezone.utc),
            "manager_notes": payload.notes or "",
            "updated_at": datetime.now(timezone.utc),
        }, "$push": {"audit_log": {
            "action": "manager_approved",
            "actor_id": current_user["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }}},
    )
    return {"message": "Manager approved"}


@router.patch("/{claim_id}/hr-approve")
async def hr_approve(claim_id: str, payload: ReimbAction, current_user: dict = Depends(get_current_user)):
    if not _is_hr_or_admin(current_user):
        raise HTTPException(status_code=403, detail="HR/admin only")
    c = await reimb_col.find_one({"id": claim_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    if c.get("status") not in ("manager_approved", "submitted"):
        raise HTTPException(status_code=400, detail="HR can only approve manager-approved or submitted claims")
    await reimb_col.update_one(
        {"id": claim_id},
        {"$set": {
            "status": "hr_approved",
            "hr_id": current_user["id"],
            "hr_approved_at": datetime.now(timezone.utc),
            "hr_notes": payload.notes or "",
            "updated_at": datetime.now(timezone.utc),
        }, "$push": {"audit_log": {
            "action": "hr_approved",
            "actor_id": current_user["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }}},
    )
    return {"message": "HR approved — will merge into next payslip"}


@router.patch("/{claim_id}/reject")
async def reject_claim(claim_id: str, payload: ReimbAction, current_user: dict = Depends(get_current_user)):
    if not (_is_manager(current_user) or _is_hr_or_admin(current_user)):
        raise HTTPException(status_code=403, detail="Managers/HR only")
    if not (payload.reason or "").strip():
        raise HTTPException(status_code=400, detail="Rejection reason required")
    c = await reimb_col.find_one({"id": claim_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    if c.get("status") in ("reimbursed", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot reject from status '{c.get('status')}'")
    await reimb_col.update_one(
        {"id": claim_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user["id"],
            "rejected_reason": payload.reason.strip(),
            "updated_at": datetime.now(timezone.utc),
        }, "$push": {"audit_log": {
            "action": "rejected",
            "actor_id": current_user["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": payload.reason.strip(),
        }}},
    )
    return {"message": "Rejected"}


@router.get("/{claim_id}/audit-trail")
async def claim_audit_trail(claim_id: str, current_user: dict = Depends(get_current_user)):
    c = await reimb_col.find_one({"id": claim_id}, {"_id": 0, "audit_log": 1, "employee_id": 1})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    if c["employee_id"] != current_user["id"] and not (_is_manager(current_user) or _is_hr_or_admin(current_user)):
        raise HTTPException(status_code=403, detail="No access")
    return c.get("audit_log", [])


# ─────────────────────────────────────────────────────────────────────────────
# Phase 21 Slice 3 Backlog B.1 — Bill file upload / download
# ─────────────────────────────────────────────────────────────────────────────

def _claim_or_404_with_access(claim: dict, current_user: dict) -> None:
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim["employee_id"] != current_user["id"] and not (_is_manager(current_user) or _is_hr_or_admin(current_user)):
        raise HTTPException(status_code=403, detail="No access")


@router.post("/{claim_id}/bill")
async def upload_bill(
    claim_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Multipart bill upload — PDF/JPG/PNG up to 5MB. Owner or HR/admin only."""
    c = await reimb_col.find_one({"id": claim_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    # Only the claim owner may attach a bill (HR/managers approve, not attach)
    if c["employee_id"] != current_user["id"] and not _is_hr_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Only the claim owner or HR/admin can attach bills")
    if c.get("status") in ("reimbursed", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot attach bill to '{c.get('status')}' claim")

    mime = (file.content_type or "").lower()
    if mime not in BILL_ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{mime}'. Allowed: PDF, JPG, PNG")
    content = await file.read()
    if len(content) > BILL_MAX_BYTES:
        raise HTTPException(status_code=400, detail=f"File too large ({len(content)} bytes). Max 5 MB")
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    bill_id = str(uuid.uuid4())
    ext = BILL_ALLOWED_MIME[mime]
    storage_path = UPLOAD_DIR / f"reimb_{bill_id}{ext}"
    storage_path.write_bytes(content)
    safe_name = (file.filename or f"bill{ext}").replace("/", "_")[:255]

    bill_entry = {
        "bill_id": bill_id,
        "file_name": safe_name,
        "mime_type": mime,
        "size_bytes": len(content),
        "stored_path": str(storage_path),
        "uploaded_by": current_user["id"],
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    await reimb_col.update_one(
        {"id": claim_id},
        {
            "$push": {
                "bills": bill_entry,
                "audit_log": {
                    "action": "bill_attached",
                    "actor_id": current_user["id"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "bill_id": bill_id,
                    "file_name": safe_name,
                },
            },
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    return {"bill_id": bill_id, "file_name": safe_name, "size_bytes": len(content), "mime_type": mime}


@router.get("/{claim_id}/bill/{bill_id}")
async def download_bill(claim_id: str, bill_id: str, current_user: dict = Depends(get_current_user)):
    """Download attached bill — owner or any manager/HR/admin."""
    c = await reimb_col.find_one({"id": claim_id}, {"_id": 0})
    _claim_or_404_with_access(c, current_user)
    bill = next((b for b in (c.get("bills") or []) if b.get("bill_id") == bill_id), None)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    path = Path(bill.get("stored_path", ""))
    if not path.exists():
        raise HTTPException(status_code=410, detail="File missing from storage")
    return FileResponse(
        path=str(path),
        media_type=bill.get("mime_type") or "application/octet-stream",
        filename=bill.get("file_name") or path.name,
    )
