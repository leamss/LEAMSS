"""Phase 4C.3 — Cost Allocations Router (per-PA breakdown)."""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.database import pre_assessments_col, users_col
from core.allocations_logic import (
    build_allocations_for_pa,
    get_allocations_for_pa,
    assign_vendor,
    set_allocation_status,
    apply_visa_approved_bonuses,
    apply_refund_clawback,
)

router = APIRouter(prefix="/pa", tags=["Phase 4C.3 - PA Cost Allocations"])


def _is_admin(u: dict) -> bool:
    return u.get("role") in ("admin", "admin_owner") or u.get("rbac_role") in ("admin", "admin_owner")


def _can_view_allocations(u: dict) -> bool:
    if _is_admin(u):
        return True
    perms = u.get("permissions") or []
    return any(p in perms for p in ["allocation.view.all", "allocation.view.team", "vendor.view.all", "pa.view.all"])


def _can_manage_allocations(u: dict) -> bool:
    if _is_admin(u):
        return True
    perms = u.get("permissions") or []
    return "allocation.assign.vendor" in perms or "allocation.approve" in perms


class AssignVendorRequest(BaseModel):
    vendor_id: str


class MarkPaidRequest(BaseModel):
    payment_reference: Optional[str] = None


def _clean(d):
    if not d:
        return d
    d.pop("_id", None)
    for k in ("created_at", "updated_at", "last_recalculated_at"):
        v = d.get(k)
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


@router.get("/{pa_id}/allocations")
async def get_allocations(pa_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_view_allocations(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="PA not found")
    doc = await get_allocations_for_pa(pa_id)
    if not doc:
        # Auto-build on first access if PA has reached case_created
        if pa.get("stage") == "case_created":
            doc = await build_allocations_for_pa(pa)
        else:
            return {"pa_id": pa_id, "has_allocations": False, "message": "Allocations are created when PA reaches case_created stage"}
    return {"pa_id": pa_id, "has_allocations": True, "allocations": _clean(doc)}


@router.post("/{pa_id}/allocations/recalculate")
async def recalc(pa_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="PA not found")
    doc = await build_allocations_for_pa(pa)
    if not doc:
        raise HTTPException(status_code=400, detail="No matching cost structure found for this PA's product")
    return {"ok": True, "allocations": _clean(doc)}


@router.post("/{pa_id}/allocations/{allocation_id}/assign-vendor")
async def assign(pa_id: str, allocation_id: str, req: AssignVendorRequest, current_user: dict = Depends(get_current_user)):
    if not _can_manage_allocations(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to assign vendors")
    try:
        doc = await assign_vendor(pa_id, allocation_id, req.vendor_id, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "allocations": _clean(doc)}


@router.post("/{pa_id}/allocations/{allocation_id}/approve")
async def approve(pa_id: str, allocation_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user) and "allocation.approve" not in (current_user.get("permissions") or []):
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        doc = await set_allocation_status(pa_id, allocation_id, "approved", current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "allocations": _clean(doc)}


@router.post("/{pa_id}/allocations/{allocation_id}/mark-paid")
async def mark_paid(pa_id: str, allocation_id: str, req: MarkPaidRequest, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user) and "allocation.mark-paid" not in (current_user.get("permissions") or []):
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        doc = await set_allocation_status(pa_id, allocation_id, "paid", current_user["id"], req.payment_reference)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "allocations": _clean(doc)}


@router.post("/{pa_id}/allocations/{allocation_id}/dispute")
async def dispute(pa_id: str, allocation_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    try:
        doc = await set_allocation_status(pa_id, allocation_id, "disputed", current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "allocations": _clean(doc)}


@router.post("/{pa_id}/allocations/visa-approved")
async def trigger_visa_approved(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Admin trigger when visa is granted — applies success bonuses to all matching allocations."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="PA not found")
    doc = await apply_visa_approved_bonuses(pa)
    if not doc:
        raise HTTPException(status_code=400, detail="No allocations to apply bonuses to")
    # Mark PA itself with visa_approved milestone (informational)
    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {"visa_approved": True, "visa_approved_at": datetime.utcnow()}})
    return {"ok": True, "allocations": _clean(doc)}


@router.post("/{pa_id}/allocations/refund-clawback")
async def trigger_refund_clawback(pa_id: str, recovery_rate: float = 0.5, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    if not (0 <= recovery_rate <= 1):
        raise HTTPException(status_code=400, detail="recovery_rate must be between 0 and 1")
    doc = await apply_refund_clawback(pa_id, recovery_rate)
    if not doc:
        raise HTTPException(status_code=404, detail="No allocations for this PA")
    return {"ok": True, "allocations": _clean(doc)}
