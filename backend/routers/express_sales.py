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
    express_user_limit_overrides: Optional[Dict[str, Optional[int]]] = None
    express_auto_approve_for_roles: Optional[list] = None
    express_max_value: Optional[float] = None
    express_min_justification_chars: Optional[int] = None


class UserLimitOverrideRequest(BaseModel):
    user_id: str
    # -1 = unlimited, 0 = blocked, >0 = custom monthly limit, None = remove override (use role default)
    limit: Optional[int] = None


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
# Per-user limit override management (Admin)
# ──────────────────────────────────────────────────────────────
@router.put("/settings/user-limit")
async def set_user_limit(req: UserLimitOverrideRequest, current_user: dict = Depends(get_current_user)):
    """Set / update / remove a per-user express sale monthly limit override.

    `limit` semantics:
      -  None  → remove override (user falls back to role-based limit)
      -  -1    → unlimited (no cap)
      -   0    → blocked (cannot create any express sale)
      -  N>0   → custom monthly cap
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    target = await users_col.find_one({"id": req.user_id}, {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    settings = await get_express_settings()
    overrides = dict(settings.get("express_user_limit_overrides") or {})

    if req.limit is None:
        overrides.pop(req.user_id, None)
        action = "removed"
    else:
        try:
            lim = int(req.limit)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="limit must be an integer (-1, 0, or > 0)")
        if lim < -1:
            raise HTTPException(status_code=400, detail="limit must be -1 (unlimited), 0 (block), or > 0")
        overrides[req.user_id] = lim
        action = "set"

    await update_express_settings(
        {"express_user_limit_overrides": overrides},
        updated_by=current_user["id"],
    )
    return {
        "ok": True,
        "action": action,
        "user": target,
        "limit": req.limit,
        "overrides": overrides,
    }


@router.get("/settings/user-overrides")
async def list_user_overrides(current_user: dict = Depends(get_current_user)):
    """List every user that currently has a per-user override, hydrated with name+email+role."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    settings = await get_express_settings()
    overrides = settings.get("express_user_limit_overrides") or {}
    if not overrides:
        return {"items": [], "count": 0}

    user_ids = list(overrides.keys())
    cursor = users_col.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1, "rbac_role": 1})
    users_map = {u["id"]: u async for u in cursor}

    items = []
    for uid, lim in overrides.items():
        u = users_map.get(uid, {"id": uid, "name": "(deleted user)", "email": "—"})
        # Compute current month usage for context
        used = await count_express_this_month(uid)
        items.append({
            **u,
            "user_id": uid,
            "limit": lim,
            "limit_label": (
                "Unlimited" if lim in (-1, None) else
                "Blocked" if lim == 0 else f"{lim}/month"
            ),
            "used_this_month": used,
        })
    items.sort(key=lambda x: (x.get("name") or "").lower())
    return {"items": items, "count": len(items)}


@router.get("/settings/searchable-users")
async def searchable_users(
    q: Optional[str] = None,
    limit: int = 25,
    current_user: dict = Depends(get_current_user),
):
    """List users eligible for express-sale overrides (sales roles + partners + admins).
    Used by the admin Express Settings page when adding a new override.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    eligible_roles = [
        "partner", "sales_executive", "sr_sales_executive",
        "sales_manager", "sales_head", "admin", "admin_owner",
    ]
    query: Dict[str, Any] = {
        "$or": [
            {"role": {"$in": eligible_roles}},
            {"rbac_role": {"$in": eligible_roles}},
        ]
    }
    if q:
        q_str = q.strip()
        if q_str:
            query = {
                "$and": [
                    query,
                    {"$or": [
                        {"name": {"$regex": q_str, "$options": "i"}},
                        {"email": {"$regex": q_str, "$options": "i"}},
                    ]},
                ]
            }
    cursor = users_col.find(query, {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1, "rbac_role": 1}).limit(min(limit, 100))
    items = await cursor.to_list(length=limit)
    return {"items": items, "count": len(items)}


# ──────────────────────────────────────────────────────────────
# Sales person — own usage
# ──────────────────────────────────────────────────────────────
@router.get("/my-usage")
async def my_usage(current_user: dict = Depends(get_current_user)):
    allowed, used, limit, msg = await check_limit(current_user)
    # Surface whether the limit comes from a per-user override
    settings = await get_express_settings()
    overrides = settings.get("express_user_limit_overrides") or {}
    has_override = current_user["id"] in overrides
    return {
        "allowed": allowed,
        "used_this_month": used,
        "limit_per_month": limit,  # None = unlimited
        "remaining": (limit - used) if limit is not None else None,
        "message": msg,
        "month_label": datetime.now(timezone.utc).strftime("%b %Y"),
        "limit_source": "admin_override" if has_override else "role_default",
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
