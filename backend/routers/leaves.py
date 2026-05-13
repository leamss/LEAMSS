"""Leaves Router — Phase 3A

Endpoints:
- GET  /leaves/types
- GET  /leaves/my-balance
- GET  /leaves/balance/{user_id}
- POST /leaves/validate           — dry-run validation (for live preview)
- POST /leaves/apply              — submit leave request
- GET  /leaves/my-history
- POST /leaves/{id}/cancel
- GET  /leaves/inbox              — manager L1
- GET  /leaves/inbox-final        — final approver
- POST /leaves/{id}/decide        — approve/reject
- GET  /leaves/all                — HR/admin
- GET  /leaves/balance-history    — audit log
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission
from core.database import (
    leave_types_col, leave_balances_col, leave_requests_col,
    leave_balance_history_col, notifications_col,
)
from core.attendance_logic import (
    validate_leave_request, deduct_leave_balance, parse_date,
    resolve_approvers, now_ist,
)

router = APIRouter(prefix="/leaves", tags=["Leaves"])


class LeaveApply(BaseModel):
    leave_type_key: str
    from_date: str
    to_date: str
    reason: str = Field(min_length=10)
    handover_to_user_id: Optional[str] = None
    contact_during_leave: Optional[str] = None
    proof_url: Optional[str] = None
    accept_sandwich: bool = False


class LeaveValidate(BaseModel):
    leave_type_key: str
    from_date: str
    to_date: str


class LeaveDecide(BaseModel):
    decision: str
    note: Optional[str] = None


def _serialize_balance(b: dict) -> dict:
    out = {k: v for k, v in b.items() if k != "_id"}
    for f in ("created_at", "updated_at"):
        if isinstance(out.get(f), datetime):
            out[f] = out[f].isoformat()
    return out


def _serialize_request(r: dict) -> dict:
    out = {k: v for k, v in r.items() if k != "_id"}
    for f in ("created_at", "decided_at_l1", "decided_at_final", "cancelled_at", "applied_at"):
        if isinstance(out.get(f), datetime):
            out[f] = out[f].isoformat()
    return out


# ──────────────────────────────────────────────────────────────
# Leave types
# ──────────────────────────────────────────────────────────────
@router.get("/types")
async def list_leave_types(current_user: dict = Depends(get_current_user)):
    items = []
    async for lt in leave_types_col.find({"is_active": True}, {"_id": 0}).sort("sort_order", 1):
        items.append(lt)
    return items


# ──────────────────────────────────────────────────────────────
# My balance
# ──────────────────────────────────────────────────────────────
@router.get("/my-balance")
async def my_balance(
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    year = year or now_ist().year
    user_id = current_user["id"]

    types = []
    async for lt in leave_types_col.find({"is_active": True}, {"_id": 0}).sort("sort_order", 1):
        types.append(lt)

    balances = {}
    async for b in leave_balances_col.find({"user_id": user_id, "year": year}, {"_id": 0}):
        balances[b["leave_type_key"]] = b

    out = []
    for lt in types:
        b = balances.get(lt["key"])
        ym = now_ist().strftime("%Y-%m")
        used_this_month = (b.get("monthly_used", {}) if b else {}).get(ym, 0)
        out.append({
            "leave_type_key": lt["key"],
            "leave_type_name": lt["name"],
            "short_code": lt["short_code"],
            "color": lt["color"],
            "annual_quota": lt["annual_quota"],
            "monthly_cap": lt.get("monthly_cap", 0),
            "max_consecutive": lt.get("max_consecutive", 0),
            "opening_balance": (b or {}).get("opening_balance", 0),
            "used": (b or {}).get("used", 0),
            "available": (b or {}).get("available", lt["annual_quota"] if lt["key"] not in ("lwp", "comp_off") else 0),
            "carried_forward": (b or {}).get("carried_forward", 0),
            "used_this_month": used_this_month,
            "sort_order": lt.get("sort_order", 99),
        })
    return {"year": year, "balances": out}


@router.get("/balance/{user_id}")
async def get_user_balance(
    user_id: str,
    year: Optional[int] = None,
    current_user: dict = Depends(require_any_permission(
        "leave.view.team", "leave.view.dept", "leave.view.all"
    )),
):
    year = year or now_ist().year
    items = []
    async for b in leave_balances_col.find({"user_id": user_id, "year": year}, {"_id": 0}):
        items.append(_serialize_balance(b))
    return items


# ──────────────────────────────────────────────────────────────
# Validate (dry-run)
# ──────────────────────────────────────────────────────────────
@router.post("/validate")
async def validate_leave(
    payload: LeaveValidate,
    current_user: dict = Depends(get_current_user),
):
    result = await validate_leave_request(
        user_id=current_user["id"],
        leave_type_key=payload.leave_type_key,
        from_date_str=payload.from_date,
        to_date_str=payload.to_date,
    )
    return result


# ──────────────────────────────────────────────────────────────
# Apply
# ──────────────────────────────────────────────────────────────
@router.post("/apply")
async def apply_leave(
    payload: LeaveApply,
    current_user: dict = Depends(require_any_permission("leave.apply.own")),
):
    result = await validate_leave_request(
        user_id=current_user["id"],
        leave_type_key=payload.leave_type_key,
        from_date_str=payload.from_date,
        to_date_str=payload.to_date,
    )
    if not result["ok"]:
        raise HTTPException(status_code=400, detail={
            "errors": result["errors"],
            "warnings": result["warnings"],
            "days_breakdown": result.get("days_breakdown"),
        })

    if result["days_breakdown"]["is_sandwich"] and not payload.accept_sandwich:
        raise HTTPException(status_code=400, detail={
            "requires_acknowledgement": True,
            "warnings": result["warnings"],
            "days_breakdown": result["days_breakdown"],
            "message": "Sandwich leave detected. Re-submit with accept_sandwich=true to confirm.",
        })

    approvers = await resolve_approvers(current_user)
    if not approvers["l1_manager_id"]:
        raise HTTPException(status_code=400, detail="No manager assigned. Contact HR to set up reports_to.")

    skip_l1 = (current_user["id"] == approvers["l1_manager_id"])
    initial_status = "pending_final" if skip_l1 else "pending_l1"

    request_id = str(uuid.uuid4())
    req = {
        "id": request_id,
        "user_id": current_user["id"],
        "user_name": current_user.get("name"),
        "user_email": current_user.get("email"),
        "user_employee_id": current_user.get("employee_id"),
        "department": current_user.get("department"),
        "designation": current_user.get("designation"),
        "leave_type_key": payload.leave_type_key,
        "leave_type_name": result.get("leave_type_name"),
        "from_date": payload.from_date,
        "to_date": payload.to_date,
        "total_days": result["total_days"],
        "working_days": result["working_days"],
        "is_sandwich": result["days_breakdown"]["is_sandwich"],
        "weekend_included": result["days_breakdown"]["weekend_included"],
        "counted_dates": result["days_breakdown"]["counted_dates"],
        "reason": payload.reason,
        "handover_to_user_id": payload.handover_to_user_id,
        "contact_during_leave": payload.contact_during_leave,
        "proof_url": payload.proof_url,
        "manager_id": approvers["l1_manager_id"],
        "manager_name": approvers["l1_manager_name"],
        "final_approver_id": approvers["final_approver_id"],
        "final_approver_name": approvers["final_approver_name"],
        "status": initial_status,
        "warnings": result.get("warnings", []),
        "applied_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
    await leave_requests_col.insert_one(req)

    await leave_balance_history_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "date": datetime.now(timezone.utc),
        "leave_type_key": payload.leave_type_key,
        "change_type": "applied",
        "delta": 0,
        "balance_before": None,
        "balance_after": None,
        "reason": f"Leave applied: {payload.from_date} to {payload.to_date}",
        "request_id": request_id,
        "triggered_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    })

    target_id = approvers["final_approver_id"] if skip_l1 else approvers["l1_manager_id"]
    if target_id:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": target_id,
            "title": f"Leave request from {current_user.get('name')}",
            "message": f"{result.get('leave_type_name')} • {payload.from_date} to {payload.to_date} • {result['total_days']} day(s)",
            "type": "leave_request",
            "entity_id": request_id,
            "read": False,
            "created_at": datetime.now(timezone.utc),
        })

    return {
        "message": "Leave applied successfully",
        "request_id": request_id,
        "status": initial_status,
        "total_days": result["total_days"],
        "warnings": result.get("warnings", []),
    }


# ──────────────────────────────────────────────────────────────
# My history
# ──────────────────────────────────────────────────────────────
@router.get("/my-history")
async def my_history(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    q = {"user_id": current_user["id"]}
    if status:
        q["status"] = status
    items = []
    async for r in leave_requests_col.find(q, {"_id": 0}).sort("created_at", -1).limit(limit):
        items.append(_serialize_request(r))
    return items


# ──────────────────────────────────────────────────────────────
# Cancel
# ──────────────────────────────────────────────────────────────
@router.post("/{request_id}/cancel")
async def cancel_leave(
    request_id: str,
    current_user: dict = Depends(get_current_user),
):
    req = await leave_requests_col.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if req["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only cancel your own leave")
    if req["status"] not in ("pending_l1", "pending_final"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel — status is '{req['status']}'")

    await leave_requests_col.update_one(
        {"id": request_id},
        {"$set": {
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc),
            "cancelled_by": current_user["id"],
        }}
    )

    target_id = req.get("manager_id") if req["status"] == "pending_l1" else req.get("final_approver_id")
    if target_id:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": target_id,
            "title": "Leave request cancelled",
            "message": f"{current_user.get('name')} cancelled their leave request for {req['from_date']} to {req['to_date']}",
            "type": "leave_cancelled",
            "entity_id": request_id,
            "read": False,
            "created_at": datetime.now(timezone.utc),
        })

    return {"message": "Leave request cancelled"}


# ──────────────────────────────────────────────────────────────
# L1 manager inbox
# ──────────────────────────────────────────────────────────────
@router.get("/inbox")
async def manager_inbox(
    status: str = "pending_l1",
    current_user: dict = Depends(require_any_permission(
        "leave.approve.l1", "leave.approve.l2", "leave.view.dept", "leave.view.team"
    )),
):
    items = []
    async for r in leave_requests_col.find(
        {"manager_id": current_user["id"], "status": status}, {"_id": 0}
    ).sort("created_at", -1).limit(100):
        items.append(_serialize_request(r))
    return items


@router.get("/inbox-final")
async def final_inbox(
    status: str = "pending_final",
    current_user: dict = Depends(require_any_permission(
        "leave.approve.l2", "leave.approve.final", "leave.view.all"
    )),
):
    items = []
    async for r in leave_requests_col.find(
        {"final_approver_id": current_user["id"], "status": status}, {"_id": 0}
    ).sort("created_at", -1).limit(100):
        items.append(_serialize_request(r))
    return items


# ──────────────────────────────────────────────────────────────
# Decide
# ──────────────────────────────────────────────────────────────
@router.post("/{request_id}/decide")
async def decide_leave(
    request_id: str,
    payload: LeaveDecide,
    current_user: dict = Depends(require_any_permission(
        "leave.approve.l1", "leave.approve.l2", "leave.approve.final"
    )),
):
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")

    req = await leave_requests_col.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")

    user_id = current_user["id"]
    is_admin_override = current_user.get("rbac_role") in ("admin_owner", "hr_head")

    if req["status"] == "pending_l1":
        if req["manager_id"] != user_id and not is_admin_override:
            raise HTTPException(status_code=403, detail="Only the assigned L1 manager can decide")
        stage = "l1"
    elif req["status"] == "pending_final":
        if req["final_approver_id"] != user_id and not is_admin_override:
            raise HTTPException(status_code=403, detail="Only the final approver can decide")
        stage = "final"
    else:
        raise HTTPException(status_code=400, detail=f"Cannot decide — status is '{req['status']}'")

    now = datetime.now(timezone.utc)
    updates = {}

    if stage == "l1":
        updates["decided_at_l1"] = now
        updates["decided_by_l1"] = user_id
        updates["decided_by_l1_name"] = current_user.get("name")
        updates["decision_note_l1"] = payload.note

        if payload.decision == "rejected":
            updates["status"] = "rejected"
            updates["rejection_reason"] = payload.note or "Rejected by L1 manager"
        else:
            if req["manager_id"] == req["final_approver_id"]:
                updates["status"] = "approved"
                updates["decided_at_final"] = now
                updates["decided_by_final"] = user_id
                updates["decided_by_final_name"] = current_user.get("name")
            else:
                updates["status"] = "pending_final"

    else:  # final
        updates["decided_at_final"] = now
        updates["decided_by_final"] = user_id
        updates["decided_by_final_name"] = current_user.get("name")
        updates["decision_note_final"] = payload.note

        if payload.decision == "rejected":
            updates["status"] = "rejected"
            updates["rejection_reason"] = payload.note or "Rejected by final approver"
        else:
            updates["status"] = "approved"

    await leave_requests_col.update_one({"id": request_id}, {"$set": updates})

    if updates.get("status") == "approved":
        from_d = parse_date(req["from_date"])
        await deduct_leave_balance(
            user_id=req["user_id"],
            leave_type_key=req["leave_type_key"],
            year=from_d.year,
            days=req["total_days"],
            request_id=request_id,
            reason=f"Leave approved: {req['from_date']} to {req['to_date']}",
            triggered_by=user_id,
            month_key=req["from_date"][:7] if req["leave_type_key"] == "casual_leave" else None,
        )

    final_status = updates.get("status")
    if final_status == "pending_final":
        if req.get("final_approver_id"):
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": req["final_approver_id"],
                "title": "Leave request awaits your final approval",
                "message": f"{req.get('user_name')} • {req.get('leave_type_name')} • {req['from_date']} to {req['to_date']}",
                "type": "leave_request",
                "entity_id": request_id,
                "read": False,
                "created_at": now,
            })

    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": req["user_id"],
        "title": f"Leave request {final_status or payload.decision}",
        "message": f"Your {req.get('leave_type_name')} leave ({req['from_date']} to {req['to_date']}) is now '{final_status or payload.decision}'." +
                   (f" Note: {payload.note}" if payload.note else ""),
        "type": "leave_decision",
        "entity_id": request_id,
        "read": False,
        "created_at": now,
    })

    return {
        "message": f"Leave {payload.decision} at stage {stage}",
        "new_status": final_status,
    }


# ──────────────────────────────────────────────────────────────
# All leaves (HR/admin)
# ──────────────────────────────────────────────────────────────
@router.get("/all")
async def list_all_leaves(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    department: Optional[str] = None,
    leave_type_key: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    current_user: dict = Depends(require_any_permission(
        "leave.view.all", "leave.view.dept"
    )),
):
    q = {}
    if status:
        q["status"] = status
    if user_id:
        q["user_id"] = user_id
    if department:
        q["department"] = department
    if leave_type_key:
        q["leave_type_key"] = leave_type_key

    items = []
    async for r in leave_requests_col.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit):
        items.append(_serialize_request(r))
    total = await leave_requests_col.count_documents(q)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


# ──────────────────────────────────────────────────────────────
# Balance history
# ──────────────────────────────────────────────────────────────
@router.get("/balance-history/my")
async def my_balance_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    items = []
    async for h in leave_balance_history_col.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("date", -1).limit(limit):
        if isinstance(h.get("date"), datetime):
            h["date"] = h["date"].isoformat()
        if isinstance(h.get("created_at"), datetime):
            h["created_at"] = h["created_at"].isoformat()
        items.append(h)
    return items


@router.get("/balance-history/user/{user_id}")
async def user_balance_history(
    user_id: str,
    limit: int = 50,
    current_user: dict = Depends(require_any_permission(
        "leave.view.team", "leave.view.dept", "leave.view.all"
    )),
):
    items = []
    async for h in leave_balance_history_col.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("date", -1).limit(limit):
        if isinstance(h.get("date"), datetime):
            h["date"] = h["date"].isoformat()
        if isinstance(h.get("created_at"), datetime):
            h["created_at"] = h["created_at"].isoformat()
        items.append(h)
    return items
