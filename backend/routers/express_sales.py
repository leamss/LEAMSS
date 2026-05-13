"""Phase 4B (Part 2) — Express Sales Router.

Endpoints:
  POST   /api/express/approve/{pa_id}            Admin approves
  POST   /api/express/reject/{pa_id}             Admin rejects
  GET    /api/express/pending                    Admin: queue
  GET    /api/express/my-usage                   Sales: own monthly count + limit
  GET    /api/express/settings                   Read settings
  PATCH  /api/express/settings                   Admin updates limits/flags
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.database import db, users_col, pre_assessments_col, notifications_col
from core.express_logic import (
    get_express_settings,
    update_express_settings,
    count_express_this_month,
    check_limit,
)

router = APIRouter(prefix="/express", tags=["Phase 4B - Express Sales"])


# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────
class ExpressApprovalRequest(BaseModel):
    remarks: Optional[str] = ""


class ExpressRejectRequest(BaseModel):
    remarks: str = Field(..., min_length=5, description="Reason for rejection (min 5 chars)")


class ExpressSettingsUpdate(BaseModel):
    express_sale_enabled: Optional[bool] = None
    express_monthly_limits: Optional[Dict[str, Optional[int]]] = None
    express_auto_approve_for_roles: Optional[list] = None
    express_max_value: Optional[float] = None
    express_min_justification_chars: Optional[int] = None


def _is_admin(u: dict) -> bool:
    return u.get("role") in ("admin", "admin_owner") or u.get("rbac_role") in ("admin", "admin_owner")


def _can_approve_express(u: dict) -> bool:
    """Admin or sales_head can approve. Permission pa.approve.express also acceptable."""
    if _is_admin(u):
        return True
    if u.get("rbac_role") in ("sales_head",):
        return True
    return "pa.approve.express" in (u.get("permissions") or [])


def _iso(dt):
    return dt.isoformat() if isinstance(dt, datetime) else dt


def _clean(d: dict) -> dict:
    if not d:
        return d
    d.pop("_id", None)
    for k in ("created_at", "updated_at", "express_sale_approved_at", "express_sale_requested_at", "final_approved_at"):
        v = d.get(k)
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


# ──────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────
@router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    s = await get_express_settings()
    s.pop("_id", None)
    if isinstance(s.get("updated_at"), datetime):
        s["updated_at"] = s["updated_at"].isoformat()
    if isinstance(s.get("created_at"), datetime):
        s["created_at"] = s["created_at"].isoformat()
    return s


@router.patch("/settings")
async def patch_settings(req: ExpressSettingsUpdate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    updates = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    s = await update_express_settings(updates, updated_by=current_user["id"])
    s.pop("_id", None)
    if isinstance(s.get("updated_at"), datetime):
        s["updated_at"] = s["updated_at"].isoformat()
    if isinstance(s.get("created_at"), datetime):
        s["created_at"] = s["created_at"].isoformat()
    return {"ok": True, "settings": s}


# ──────────────────────────────────────────────────────────────
# Sales person — own usage
# ──────────────────────────────────────────────────────────────
@router.get("/my-usage")
async def my_usage(current_user: dict = Depends(get_current_user)):
    allowed, used, limit, msg = await check_limit(current_user)
    return {
        "allowed": allowed,
        "used_this_month": used,
        "limit_per_month": limit,  # None = unlimited
        "remaining": (limit - used) if limit is not None else None,
        "message": msg,
        "month_label": datetime.now(timezone.utc).strftime("%b %Y"),
    }


# ──────────────────────────────────────────────────────────────
# Admin queue + approve/reject
# ──────────────────────────────────────────────────────────────
@router.get("/pending")
async def list_pending(
    sales_user_id: Optional[str] = None,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    if not _can_approve_express(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view Express approvals")
    q = {"sale_type": "express", "express_sale_approval_status": "pending"}
    if sales_user_id:
        q["created_by_user_id"] = sales_user_id
    if reason:
        q["express_sale_reason"] = reason

    cursor = pre_assessments_col.find(q, {"_id": 0}).sort("created_at", -1).limit(500)
    items = await cursor.to_list(length=500)
    return {"items": [_clean(i) for i in items], "count": len(items)}


@router.post("/approve/{pa_id}")
async def approve_express(pa_id: str, req: Optional[ExpressApprovalRequest] = None, current_user: dict = Depends(get_current_user)):
    if not _can_approve_express(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to approve Express")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if pa.get("sale_type") != "express":
        raise HTTPException(status_code=400, detail="Not an express sale")
    if pa.get("express_sale_approval_status") != "pending":
        raise HTTPException(status_code=400, detail=f"Already {pa.get('express_sale_approval_status')}")

    now = datetime.now(timezone.utc)
    remarks = (req.remarks if req else "") or ""
    # Stage transition: express_pending_approval → approved (skip to proposal stage)
    # 'approved' is an existing stage in the standard flow meaning "1st approval done — partner can send proposal"
    await pre_assessments_col.update_one(
        {"id": pa_id},
        {"$set": {
            "express_sale_approval_status": "approved",
            "express_sale_approved_by": current_user["id"],
            "express_sale_approved_by_name": current_user.get("name", ""),
            "express_sale_approved_at": now,
            "express_sale_approval_remarks": remarks,
            "stage": "approved",  # converges with standard flow's first-approval state
            "admin_decision": "approved",
            "admin_reviewed_by": current_user["id"],
            "admin_reviewed_at": now,
            "updated_at": now,
        }},
    )

    # Notify creator
    if pa.get("created_by_user_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["created_by_user_id"],
            "title": "✅ Express Sale Approved",
            "message": f"Your Express Sale for {pa.get('client_name')} has been approved. You can now generate the proposal.",
            "type": "express_approved",
            "read": False,
            "link": "/sales/dashboard",
            "metadata": {"pa_id": pa_id},
            "created_at": now,
        })

    return {"ok": True, "stage": "approved", "express_sale_approval_status": "approved"}


@router.post("/reject/{pa_id}")
async def reject_express(pa_id: str, req: ExpressRejectRequest, current_user: dict = Depends(get_current_user)):
    if not _can_approve_express(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to reject Express")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if pa.get("sale_type") != "express":
        raise HTTPException(status_code=400, detail="Not an express sale")
    if pa.get("express_sale_approval_status") != "pending":
        raise HTTPException(status_code=400, detail=f"Already {pa.get('express_sale_approval_status')}")

    now = datetime.now(timezone.utc)
    await pre_assessments_col.update_one(
        {"id": pa_id},
        {"$set": {
            "express_sale_approval_status": "rejected",
            "express_sale_approved_by": current_user["id"],
            "express_sale_approved_by_name": current_user.get("name", ""),
            "express_sale_approved_at": now,
            "express_sale_approval_remarks": req.remarks,
            "stage": "express_rejected",
            "admin_decision": "rejected",
            "admin_reason": req.remarks,
            "admin_reviewed_by": current_user["id"],
            "admin_reviewed_at": now,
            "updated_at": now,
        }},
    )

    # Notify creator
    if pa.get("created_by_user_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["created_by_user_id"],
            "title": "❌ Express Sale Rejected",
            "message": f"Your Express Sale for {pa.get('client_name')} was rejected. Reason: {req.remarks}",
            "type": "express_rejected",
            "read": False,
            "link": "/sales/dashboard",
            "metadata": {"pa_id": pa_id, "reason": req.remarks},
            "created_at": now,
        })

    return {"ok": True, "stage": "express_rejected", "express_sale_approval_status": "rejected"}


@router.get("/history")
async def history(
    status: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    """Admin history view of approved/rejected express sales."""
    if not _can_approve_express(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    q: Dict[str, Any] = {"sale_type": "express"}
    if status:
        q["express_sale_approval_status"] = status
    cursor = pre_assessments_col.find(q, {"_id": 0}).sort("express_sale_approved_at", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"items": [_clean(i) for i in items], "count": len(items)}
