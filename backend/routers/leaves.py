"""Leaves Router — Phase 3

Implements:
- Leave types catalog (5 pre-seeded)
- Per-user leave balances (auto-init for current year)
- Apply leave with validation (overlap, balance, notice)
- L1 (manager) + Final (HR) approval workflow
- Holiday calendar
"""
import uuid
from datetime import datetime, timezone, timedelta, date as date_type
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.database import db, users_col
from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission

router = APIRouter(prefix="/leaves", tags=["Leaves"])

leave_types_col = db["leave_types"]
leave_balances_col = db["leave_balances"]
leave_applications_col = db["leave_applications"]
holidays_col = db["holidays"]
attendance_col = db["attendance_records"]
notifications_col = db["notifications"]


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────
def _today() -> date_type:
    return datetime.now(timezone.utc).date()


def _parse_date(s: str) -> date_type:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _serialize(d: dict) -> dict:
    out = {k: v for k, v in d.items() if k != "_id"}
    for f in ("from_date", "to_date", "applied_at", "l1_approved_at", "hr_approved_at",
              "cancelled_at", "modified_at", "created_at", "updated_at", "effective_date"):
        if isinstance(out.get(f), datetime):
            out[f] = out[f].isoformat()
    return out


async def _calc_working_days(from_d: date_type, to_d: date_type, half_day: bool = False) -> float:
    """Count days excluding weekends + holidays."""
    if half_day and from_d == to_d:
        return 0.5
    # Get holidays in range
    holiday_dates = set()
    cursor = holidays_col.find(
        {"date": {"$gte": from_d.isoformat(), "$lte": to_d.isoformat()}},
        {"_id": 0, "date": 1},
    )
    async for h in cursor:
        holiday_dates.add(h["date"])

    count = 0
    d = from_d
    while d <= to_d:
        if d.weekday() < 6 and d.isoformat() not in holiday_dates:  # Mon-Sat work
            count += 1
        d = d + timedelta(days=1)
    return float(count)


async def _ensure_balance(user_id: str, year: int):
    """Create balance entries for all leave types if missing."""
    async for lt in leave_types_col.find({}, {"_id": 0}):
        existing = await leave_balances_col.find_one(
            {"user_id": user_id, "year": year, "leave_type_key": lt["key"]},
            {"_id": 0},
        )
        if not existing:
            await leave_balances_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "year": year,
                "leave_type_key": lt["key"],
                "total_quota": lt.get("annual_quota") or 0,
                "used": 0.0,
                "pending": 0.0,
                "carried_forward": 0.0,
                "accrued": 0.0,
                "last_updated": datetime.now(timezone.utc),
            })


async def _check_overlap(user_id: str, from_d: date_type, to_d: date_type, exclude_id: str = None) -> bool:
    """Check if user has overlapping leave."""
    query = {
        "user_id": user_id,
        "status": {"$in": ["pending_l1", "pending_hr", "approved"]},
        "from_date": {"$lte": to_d.isoformat()},
        "to_date": {"$gte": from_d.isoformat()},
    }
    if exclude_id:
        query["id"] = {"$ne": exclude_id}
    overlap = await leave_applications_col.find_one(query, {"_id": 0})
    return overlap is not None


# ────────────────────────────────────────────────────────────
# Models
# ────────────────────────────────────────────────────────────
class ApplyLeaveBody(BaseModel):
    leave_type_key: str
    from_date: str  # YYYY-MM-DD
    to_date: str
    is_half_day: bool = False
    half_day_session: Optional[str] = None  # first_half | second_half
    reason: str = Field(min_length=10)
    proof_document_url: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    task_handover_to: Optional[str] = None
    task_handover_notes: Optional[str] = None


class ApprovalBody(BaseModel):
    remarks: Optional[str] = None


class RejectBody(BaseModel):
    reason: str = Field(min_length=5)


# ────────────────────────────────────────────────────────────
# Leave Types
# ────────────────────────────────────────────────────────────
@router.get("/types")
async def list_leave_types(current_user: dict = Depends(get_current_user)):
    items = []
    async for lt in leave_types_col.find({}, {"_id": 0}).sort("name", 1):
        items.append(lt)
    return items


# ────────────────────────────────────────────────────────────
# Balances
# ────────────────────────────────────────────────────────────
@router.get("/balance")
async def my_balance(current_user: dict = Depends(get_current_user)):
    year = _today().year
    await _ensure_balance(current_user["id"], year)
    balances = []
    types_by_key = {}
    async for lt in leave_types_col.find({}, {"_id": 0}):
        types_by_key[lt["key"]] = lt
    async for b in leave_balances_col.find({"user_id": current_user["id"], "year": year}, {"_id": 0}):
        lt = types_by_key.get(b["leave_type_key"], {})
        total = b.get("total_quota", 0) + b.get("carried_forward", 0) + b.get("accrued", 0)
        used = b.get("used", 0)
        pending = b.get("pending", 0)
        available = max(0, total - used - pending)
        balances.append({
            **b,
            "available": available,
            "total": total,
            "leave_type_name": lt.get("name"),
            "short_code": lt.get("short_code"),
            "color": lt.get("color"),
            "last_updated": b["last_updated"].isoformat() if isinstance(b.get("last_updated"), datetime) else b.get("last_updated"),
        })
    return balances


# ────────────────────────────────────────────────────────────
# Apply / Cancel
# ────────────────────────────────────────────────────────────
@router.post("/apply")
async def apply_leave(body: ApplyLeaveBody, current_user: dict = Depends(get_current_user)):
    if current_user.get("user_type") != "internal":
        raise HTTPException(status_code=403, detail="Only internal employees can apply for leave")

    # Validate leave type
    lt = await leave_types_col.find_one({"key": body.leave_type_key}, {"_id": 0})
    if not lt:
        raise HTTPException(status_code=400, detail="Invalid leave type")

    from_d = _parse_date(body.from_date)
    to_d = _parse_date(body.to_date)
    if to_d < from_d:
        raise HTTPException(status_code=400, detail="to_date must be >= from_date")

    # Min notice check
    notice_days = lt.get("min_notice_days", 0)
    today = _today()
    if notice_days > 0 and (from_d - today).days < notice_days and body.leave_type_key != "sick_leave":
        raise HTTPException(status_code=400, detail=f"Requires {notice_days} day(s) advance notice")

    # Past date check (allow sick leave for past)
    if from_d < today and body.leave_type_key not in ("sick_leave", "loss_of_pay"):
        raise HTTPException(status_code=400, detail="Cannot apply for past dates")

    # Working days
    days = await _calc_working_days(from_d, to_d, body.is_half_day)
    if days == 0:
        raise HTTPException(status_code=400, detail="No working days in selected range (all weekends/holidays)")

    # Max consecutive check
    max_consec = lt.get("max_consecutive_days")
    if max_consec and days > max_consec:
        raise HTTPException(status_code=400, detail=f"Max {max_consec} consecutive days allowed")

    # Overlap check
    if await _check_overlap(current_user["id"], from_d, to_d):
        raise HTTPException(status_code=400, detail="Overlapping leave application exists")

    # Balance check
    year = from_d.year
    await _ensure_balance(current_user["id"], year)
    balance = await leave_balances_col.find_one(
        {"user_id": current_user["id"], "year": year, "leave_type_key": body.leave_type_key},
        {"_id": 0},
    )
    if body.leave_type_key != "loss_of_pay":
        total = balance.get("total_quota", 0) + balance.get("carried_forward", 0) + balance.get("accrued", 0)
        available = total - balance.get("used", 0) - balance.get("pending", 0)
        if days > available:
            raise HTTPException(status_code=400, detail=f"Insufficient balance. Available: {available} days")

    now = datetime.now(timezone.utc)
    app_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_name": current_user.get("name"),
        "user_department": current_user.get("department"),
        "leave_type_key": body.leave_type_key,
        "leave_type_name": lt.get("name"),
        "leave_type_color": lt.get("color"),
        "from_date": body.from_date,
        "to_date": body.to_date,
        "days_count": days,
        "is_half_day": body.is_half_day,
        "half_day_session": body.half_day_session,
        "reason": body.reason,
        "proof_document_url": body.proof_document_url,
        "contact_phone": body.contact_phone or current_user.get("mobile"),
        "contact_email": body.contact_email or current_user.get("email"),
        "task_handover_to": body.task_handover_to,
        "task_handover_notes": body.task_handover_notes,
        "status": "pending_l1",
        "l1_approver_id": current_user.get("reports_to"),
        "hr_approver_id": None,
        "applied_at": now,
        "created_at": now,
    }
    # If no reports_to, skip L1 and go directly to HR
    if not current_user.get("reports_to"):
        app_doc["status"] = "pending_hr"

    await leave_applications_col.insert_one(app_doc)

    # Lock balance (move from available → pending)
    await leave_balances_col.update_one(
        {"user_id": current_user["id"], "year": year, "leave_type_key": body.leave_type_key},
        {"$inc": {"pending": days}},
    )

    # Notify
    notify_target = current_user.get("reports_to")
    if not notify_target:
        # Notify HR head/exec
        hr_user = await users_col.find_one({"rbac_role": {"$in": ["hr_head", "hr_executive", "admin_owner"]}, "status": "active"}, {"_id": 0, "id": 1})
        if hr_user:
            notify_target = hr_user["id"]
    if notify_target:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": notify_target,
            "title": "Leave Application Pending",
            "message": f"{current_user.get('name')} applied for {days} day(s) of {lt.get('name')}",
            "type": "leave_pending",
            "read": False,
            "link": "/leaves/approvals",
            "created_at": now,
        })

    return {"id": app_doc["id"], "status": app_doc["status"], "days_count": days, "message": "Leave applied successfully"}


@router.patch("/{leave_id}/cancel")
async def cancel_leave(leave_id: str, current_user: dict = Depends(get_current_user)):
    app = await leave_applications_col.find_one({"id": leave_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="Leave not found")
    if app["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Can only cancel own leaves")
    if app["status"] not in ("pending_l1", "pending_hr"):
        raise HTTPException(status_code=400, detail="Only pending leaves can be cancelled")

    now = datetime.now(timezone.utc)
    await leave_applications_col.update_one(
        {"id": leave_id},
        {"$set": {"status": "cancelled", "cancelled_at": now}}
    )
    # Release balance
    await leave_balances_col.update_one(
        {"user_id": app["user_id"], "year": _parse_date(app["from_date"]).year, "leave_type_key": app["leave_type_key"]},
        {"$inc": {"pending": -app["days_count"]}},
    )
    return {"message": "Leave cancelled"}


# ────────────────────────────────────────────────────────────
# My / List
# ────────────────────────────────────────────────────────────
@router.get("/my")
async def my_leaves(
    status: Optional[str] = None,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    query = {"user_id": current_user["id"]}
    if status:
        query["status"] = status
    if year:
        query["from_date"] = {"$regex": f"^{year}-"}
    items = []
    async for a in leave_applications_col.find(query, {"_id": 0}).sort("applied_at", -1):
        items.append(_serialize(a))
    return items


@router.get("/all")
async def all_leaves(
    status: Optional[str] = None,
    department: Optional[str] = None,
    leave_type_key: Optional[str] = None,
    current_user: dict = Depends(require_any_permission("leave.view.all", "leave.approve.final")),
):
    query = {}
    if status:
        query["status"] = status
    if department:
        query["user_department"] = department
    if leave_type_key:
        query["leave_type_key"] = leave_type_key
    items = []
    async for a in leave_applications_col.find(query, {"_id": 0}).sort("applied_at", -1).limit(200):
        items.append(_serialize(a))
    return items


@router.get("/pending/l1")
async def pending_l1(current_user: dict = Depends(get_current_user)):
    """Leaves where current user is the L1 approver (reports_to)."""
    items = []
    async for a in leave_applications_col.find(
        {"l1_approver_id": current_user["id"], "status": "pending_l1"},
        {"_id": 0},
    ).sort("applied_at", -1):
        items.append(_serialize(a))
    return items


@router.get("/pending/hr")
async def pending_hr(current_user: dict = Depends(require_any_permission("leave.approve.final", "leave.approve.l2"))):
    items = []
    async for a in leave_applications_col.find(
        {"status": "pending_hr"},
        {"_id": 0},
    ).sort("applied_at", -1):
        items.append(_serialize(a))
    return items


# ────────────────────────────────────────────────────────────
# Approve / Reject
# ────────────────────────────────────────────────────────────
@router.post("/{leave_id}/approve-l1")
async def approve_l1(leave_id: str, body: ApprovalBody, current_user: dict = Depends(require_any_permission("leave.approve.l1"))):
    app = await leave_applications_col.find_one({"id": leave_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="Leave not found")
    if app["status"] != "pending_l1":
        raise HTTPException(status_code=400, detail=f"Cannot approve — current status: {app['status']}")
    if app["l1_approver_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You are not the L1 approver for this leave")

    now = datetime.now(timezone.utc)
    await leave_applications_col.update_one(
        {"id": leave_id},
        {"$set": {
            "status": "pending_hr",
            "l1_approved_at": now,
            "l1_remarks": body.remarks,
            "l1_approver_name": current_user.get("name"),
        }}
    )

    # Notify HR
    hr_user = await users_col.find_one({"rbac_role": {"$in": ["hr_head", "hr_executive", "admin_owner"]}, "status": "active"}, {"_id": 0, "id": 1})
    if hr_user:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": hr_user["id"],
            "title": "Leave Pending HR Approval",
            "message": f"{app.get('user_name')}'s leave approved by manager, needs HR review",
            "type": "leave_pending_hr",
            "read": False,
            "link": "/leaves/approvals",
            "created_at": now,
        })
    # Notify applicant
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": app["user_id"],
        "title": "Leave Approved by Manager",
        "message": f"Awaiting final HR approval for your {app.get('leave_type_name')} from {app['from_date']}",
        "type": "leave_l1_approved",
        "read": False,
        "created_at": now,
    })
    return {"message": "Approved at L1, forwarded to HR"}


@router.post("/{leave_id}/approve-final")
async def approve_final(leave_id: str, body: ApprovalBody, current_user: dict = Depends(require_any_permission("leave.approve.final"))):
    app = await leave_applications_col.find_one({"id": leave_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="Leave not found")
    if app["status"] not in ("pending_hr", "pending_l1"):
        raise HTTPException(status_code=400, detail=f"Cannot approve — current status: {app['status']}")

    now = datetime.now(timezone.utc)
    await leave_applications_col.update_one(
        {"id": leave_id},
        {"$set": {
            "status": "approved",
            "hr_approved_at": now,
            "hr_approver_id": current_user["id"],
            "hr_approver_name": current_user.get("name"),
            "hr_remarks": body.remarks,
        }}
    )

    # Move balance: pending → used
    await leave_balances_col.update_one(
        {"user_id": app["user_id"], "year": _parse_date(app["from_date"]).year, "leave_type_key": app["leave_type_key"]},
        {"$inc": {"pending": -app["days_count"], "used": app["days_count"]}},
    )

    # Mark dates in attendance as "leave"
    from_d = _parse_date(app["from_date"])
    to_d = _parse_date(app["to_date"])
    d = from_d
    while d <= to_d:
        await attendance_col.update_one(
            {"user_id": app["user_id"], "date": d.isoformat()},
            {"$set": {"status": "leave", "leave_type": app["leave_type_key"]}},
            upsert=True,
        )
        d = d + timedelta(days=1)

    # Notify applicant
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": app["user_id"],
        "title": "Leave Approved ✓",
        "message": f"Your {app.get('leave_type_name')} from {app['from_date']} to {app['to_date']} is approved",
        "type": "leave_approved",
        "read": False,
        "created_at": now,
    })
    return {"message": "Leave fully approved"}


@router.post("/{leave_id}/reject")
async def reject_leave(leave_id: str, body: RejectBody, current_user: dict = Depends(require_any_permission("leave.approve.l1", "leave.approve.final"))):
    app = await leave_applications_col.find_one({"id": leave_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="Leave not found")
    if app["status"] not in ("pending_l1", "pending_hr"):
        raise HTTPException(status_code=400, detail=f"Cannot reject — current status: {app['status']}")

    now = datetime.now(timezone.utc)
    await leave_applications_col.update_one(
        {"id": leave_id},
        {"$set": {
            "status": "rejected",
            "rejection_reason": body.reason,
            "rejected_by": current_user["id"],
            "rejected_at": now,
        }}
    )

    # Release balance
    await leave_balances_col.update_one(
        {"user_id": app["user_id"], "year": _parse_date(app["from_date"]).year, "leave_type_key": app["leave_type_key"]},
        {"$inc": {"pending": -app["days_count"]}},
    )

    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": app["user_id"],
        "title": "Leave Rejected",
        "message": f"Your leave request from {app['from_date']} was rejected. Reason: {body.reason}",
        "type": "leave_rejected",
        "read": False,
        "created_at": now,
    })
    return {"message": "Leave rejected"}


# ────────────────────────────────────────────────────────────
# Holidays
# ────────────────────────────────────────────────────────────
@router.get("/holidays")
async def list_holidays(year: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    year = year or _today().year
    items = []
    async for h in holidays_col.find({"date": {"$regex": f"^{year}-"}}, {"_id": 0}).sort("date", 1):
        items.append(h)
    return items
