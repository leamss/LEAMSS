"""Attendance Router — Phase 3A

Endpoints:
- POST /attendance/punch-in
- POST /attendance/punch-out
- GET  /attendance/current-status
- GET  /attendance/my-month?year=&month=
- GET  /attendance/today (HR/admin — all employees today)
- GET  /attendance/late-marks/my
- POST /attendance/regularize
- GET  /attendance/regularizations/inbox  (manager)
- POST /attendance/regularizations/{id}/decide
- GET  /attendance/dashboard (HR — dept stats)
"""
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission
from core.database import (
    attendance_logs_col, users_col, notifications_col, holidays_col,
    attendance_regularizations_col, lwp_records_col,
    late_marks_tracker_col, leave_requests_col,
)
from core.attendance_logic import (
    now_ist, today_ist_str,
    get_settings, compute_late_status, compute_expected_clock_out,
    record_late_mark, get_late_marks_count, is_working_day,
    has_approved_leave_on, mark_lwp_for_date, parse_date,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


class PunchInRequest(BaseModel):
    work_mode: str = Field(default="office")  # office | wfh | field
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_label: Optional[str] = None
    notes: Optional[str] = None


class PunchOutRequest(BaseModel):
    notes: Optional[str] = None
    confirm_short_hours: bool = False


class RegularizeRequest(BaseModel):
    date: str  # YYYY-MM-DD
    reason: str = Field(min_length=10)
    request_type: str = Field(default="missed_punch")
    correct_punch_in: Optional[str] = None
    correct_punch_out: Optional[str] = None


class RegularizationDecide(BaseModel):
    decision: str
    note: Optional[str] = None


def _strip_log(log: dict) -> dict:
    return {
        k: v for k, v in log.items()
        if k not in ("_id", "created_at", "updated_at",
                     "punch_in_user_agent", "punch_out_user_agent",
                     "punch_in_ip", "punch_out_ip")
    }


# ──────────────────────────────────────────────────────────────
# Punch IN
# ──────────────────────────────────────────────────────────────
@router.post("/punch-in")
async def punch_in(
    payload: PunchInRequest,
    request: Request,
    current_user: dict = Depends(require_any_permission("attendance.clock.own")),
):
    user_id = current_user["id"]
    settings = await get_settings()
    now_local = now_ist()
    today_str = now_local.strftime("%Y-%m-%d")

    existing = await attendance_logs_col.find_one(
        {"user_id": user_id, "date": today_str}, {"_id": 0}
    )
    if existing and existing.get("punch_in_at"):
        if not existing.get("punch_out_at"):
            return {
                "message": "Already punched in",
                "already_punched": True,
                "log": _strip_log(existing),
            }
        raise HTTPException(status_code=400, detail="You've already completed today's attendance")

    is_late, late_min = compute_late_status(now_local, settings)
    expected_out = compute_expected_clock_out(now_local, settings)

    log_id = str(uuid.uuid4())
    log = {
        "id": log_id,
        "user_id": user_id,
        "user_name": current_user.get("name"),
        "department": current_user.get("department"),
        "date": today_str,
        "year_month": today_str[:7],
        "punch_in_at": now_local.isoformat(),
        "punch_in_ip": request.client.host if request.client else None,
        "punch_in_user_agent": request.headers.get("user-agent", "")[:300],
        "punch_in_lat": payload.latitude,
        "punch_in_lng": payload.longitude,
        "punch_in_location": payload.location_label,
        "work_mode": payload.work_mode,
        "notes_in": payload.notes,
        "is_late": is_late,
        "late_by_minutes": late_min,
        "expected_clock_out_at": expected_out.isoformat() if is_late else None,
        "punch_out_at": None,
        "total_minutes": None,
        "status": "in_progress",
        "is_holiday": not (await is_working_day(parse_date(today_str), settings)),
        "created_at": datetime.now(timezone.utc),
    }
    await attendance_logs_col.insert_one(log)

    late_result = None
    if is_late:
        late_result = await record_late_mark(user_id, today_str, late_min)

    return {
        "message": "Punched in successfully",
        "log": _strip_log(log),
        "is_late": is_late,
        "late_by_minutes": late_min,
        "expected_clock_out_at": expected_out.isoformat() if is_late else None,
        "late_marks_this_month": late_result,
    }


# ──────────────────────────────────────────────────────────────
# Punch OUT
# ──────────────────────────────────────────────────────────────
@router.post("/punch-out")
async def punch_out(
    payload: PunchOutRequest,
    request: Request,
    current_user: dict = Depends(require_any_permission("attendance.clock.own")),
):
    user_id = current_user["id"]
    settings = await get_settings()
    now_local = now_ist()
    today_str = now_local.strftime("%Y-%m-%d")

    log = await attendance_logs_col.find_one(
        {"user_id": user_id, "date": today_str}, {"_id": 0}
    )
    if not log:
        raise HTTPException(status_code=400, detail="No punch-in found for today")
    if log.get("punch_out_at"):
        raise HTTPException(status_code=400, detail="Already punched out")

    punch_in_at = datetime.fromisoformat(log["punch_in_at"])
    total_minutes = int((now_local - punch_in_at).total_seconds() // 60)
    min_required = int(float(settings.get("min_work_hours", 9)) * 60)
    short_hours = total_minutes < min_required

    if short_hours and not payload.confirm_short_hours:
        shortfall = min_required - total_minutes
        return {
            "requires_confirmation": True,
            "short_hours": True,
            "shortfall_minutes": shortfall,
            "total_minutes": total_minutes,
            "min_required_minutes": min_required,
            "message": f"⚠️ You'll be short by {shortfall} minutes ({shortfall // 60}h {shortfall % 60}m). Manager approval may be required.",
        }

    status = "short_hours" if short_hours else "complete"

    await attendance_logs_col.update_one(
        {"id": log["id"]},
        {"$set": {
            "punch_out_at": now_local.isoformat(),
            "punch_out_ip": request.client.host if request.client else None,
            "punch_out_user_agent": request.headers.get("user-agent", "")[:300],
            "notes_out": payload.notes,
            "total_minutes": total_minutes,
            "short_hours": short_hours,
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }}
    )

    return {
        "message": "Punched out successfully",
        "total_minutes": total_minutes,
        "total_hours_str": f"{total_minutes // 60}h {total_minutes % 60}m",
        "short_hours": short_hours,
        "status": status,
    }


# ──────────────────────────────────────────────────────────────
# Current status
# ──────────────────────────────────────────────────────────────
@router.get("/current-status")
async def current_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    now_local = now_ist()
    today_str = now_local.strftime("%Y-%m-%d")
    settings = await get_settings()

    log = await attendance_logs_col.find_one(
        {"user_id": user_id, "date": today_str}, {"_id": 0}
    )
    late_marks = await get_late_marks_count(user_id)
    threshold = int(settings.get("late_marks_for_leave_deduction", 3))

    if not log:
        return {
            "status": "not_punched",
            "today": today_str,
            "now_ist": now_local.isoformat(),
            "office_start_time": settings["office_start_time"],
            "office_end_time": settings["office_end_time"],
            "min_work_hours": settings["min_work_hours"],
            "late_threshold_minutes": settings["late_threshold_minutes"],
            "late_marks": late_marks,
            "late_threshold": threshold,
        }

    if log.get("punch_out_at"):
        return {
            "status": "completed",
            "today": today_str,
            "log": _strip_log(log),
            "late_marks": late_marks,
            "late_threshold": threshold,
        }

    punch_in_at = datetime.fromisoformat(log["punch_in_at"])
    elapsed = int((now_local - punch_in_at).total_seconds() // 60)
    min_required = int(float(settings.get("min_work_hours", 9)) * 60)
    expected_out = compute_expected_clock_out(punch_in_at, settings)

    return {
        "status": "in_progress",
        "today": today_str,
        "now_ist": now_local.isoformat(),
        "log": _strip_log(log),
        "elapsed_minutes": elapsed,
        "min_required_minutes": min_required,
        "remaining_minutes": max(0, min_required - elapsed),
        "expected_clock_out_at": expected_out.isoformat(),
        "late_marks": late_marks,
        "late_threshold": threshold,
    }


# ──────────────────────────────────────────────────────────────
# My month — calendar view
# ──────────────────────────────────────────────────────────────
async def _get_month_data(user_id: str, year: int, month: int):
    import calendar
    ym = f"{year:04d}-{month:02d}"
    settings = await get_settings()
    weekly_off = settings.get("weekly_off_days", [6])

    logs_by_date = {}
    async for log in attendance_logs_col.find(
        {"user_id": user_id, "year_month": ym}, {"_id": 0}
    ):
        logs_by_date[log["date"]] = log

    holidays = {}
    async for h in holidays_col.find({"year": year}, {"_id": 0}):
        if h["date"].startswith(ym):
            holidays[h["date"]] = h

    leaves_by_date = {}
    async for lr in leave_requests_col.find({
        "user_id": user_id,
        "status": {"$in": ["approved", "pending_l1", "pending_final"]},
    }, {"_id": 0}):
        try:
            from_d = parse_date(lr["from_date"])
            to_d = parse_date(lr["to_date"])
            d = from_d
            while d <= to_d:
                if d.strftime("%Y-%m") == ym:
                    leaves_by_date[d.strftime("%Y-%m-%d")] = lr
                d = d + timedelta(days=1)
        except Exception:
            continue

    lwp_dates = set()
    async for lw in lwp_records_col.find(
        {"user_id": user_id, "date": {"$regex": f"^{ym}"}}, {"_id": 0, "date": 1}
    ):
        lwp_dates.add(lw["date"])

    _, days_in_month = calendar.monthrange(year, month)

    days = []
    counters = {
        "present": 0, "absent": 0, "late": 0, "half_day": 0, "leave": 0,
        "holiday": 0, "weekly_off": 0, "lwp": 0, "future": 0,
        "total_hours": 0,
    }

    today = now_ist().date()
    for dnum in range(1, days_in_month + 1):
        d = date(year, month, dnum)
        date_str = d.strftime("%Y-%m-%d")
        is_future = d > today
        is_wo = d.weekday() in weekly_off
        is_h = date_str in holidays
        log = logs_by_date.get(date_str)
        leave = leaves_by_date.get(date_str)
        is_lwp = date_str in lwp_dates

        day = {
            "date": date_str,
            "day_of_month": dnum,
            "day_of_week": d.weekday(),
            "is_future": is_future,
            "is_weekly_off": is_wo,
            "is_holiday": is_h,
            "holiday_name": holidays[date_str]["name"] if is_h else None,
            "is_lwp": is_lwp,
        }

        if is_future:
            day["status"] = "future"
            counters["future"] += 1
        elif is_lwp:
            day["status"] = "lwp"
            counters["lwp"] += 1
        elif leave:
            day["status"] = "leave"
            day["leave_type"] = leave.get("leave_type_key")
            day["leave_status"] = leave.get("status")
            counters["leave"] += 1
        elif is_h:
            day["status"] = "holiday"
            counters["holiday"] += 1
        elif is_wo:
            day["status"] = "weekly_off"
            counters["weekly_off"] += 1
        elif log:
            if log.get("is_late"):
                day["status"] = "late"
                counters["late"] += 1
                counters["present"] += 1
            else:
                day["status"] = "present"
                counters["present"] += 1
            day["punch_in"] = log.get("punch_in_at", "")[11:16] if log.get("punch_in_at") else None
            day["punch_out"] = log.get("punch_out_at", "")[11:16] if log.get("punch_out_at") else None
            day["total_minutes"] = log.get("total_minutes")
            day["late_by_minutes"] = log.get("late_by_minutes", 0)
            day["work_mode"] = log.get("work_mode")
            if log.get("total_minutes"):
                counters["total_hours"] += log["total_minutes"] / 60
        else:
            day["status"] = "absent"
            counters["absent"] += 1

        days.append(day)

    counters["total_hours"] = round(counters["total_hours"], 1)
    late_marks = await get_late_marks_count(user_id, ym)

    return {
        "year": year,
        "month": month,
        "year_month": ym,
        "days": days,
        "counters": counters,
        "late_marks": late_marks,
        "settings": {
            "office_start_time": settings["office_start_time"],
            "office_end_time": settings["office_end_time"],
            "min_work_hours": settings["min_work_hours"],
            "late_threshold_minutes": settings["late_threshold_minutes"],
            "late_marks_for_leave_deduction": settings["late_marks_for_leave_deduction"],
        },
    }


@router.get("/my-month")
async def my_month(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    current_user: dict = Depends(get_current_user),
):
    return await _get_month_data(current_user["id"], year, month)


@router.get("/user/{user_id}/month")
async def user_month(
    user_id: str,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    current_user: dict = Depends(require_any_permission(
        "attendance.view.team", "attendance.view.dept", "attendance.view.all"
    )),
):
    return await _get_month_data(user_id, year, month)


# ──────────────────────────────────────────────────────────────
# Today's attendance (HR/admin)
# ──────────────────────────────────────────────────────────────
@router.get("/today")
async def today_attendance(
    department: Optional[str] = None,
    current_user: dict = Depends(require_any_permission(
        "attendance.view.team", "attendance.view.dept", "attendance.view.all"
    )),
):
    today_str = today_ist_str()
    user_query = {"user_type": "internal", "status": "active"}
    if department:
        user_query["department"] = department

    employees = []
    async for u in users_col.find(user_query, {
        "_id": 0, "id": 1, "name": 1, "email": 1, "department": 1,
        "rbac_role": 1, "designation": 1, "employee_id": 1, "avatar_url": 1,
    }):
        employees.append(u)

    user_ids = [u["id"] for u in employees]
    logs = {}
    async for log in attendance_logs_col.find(
        {"user_id": {"$in": user_ids}, "date": today_str}, {"_id": 0}
    ):
        logs[log["user_id"]] = log

    on_leave = set()
    async for lr in leave_requests_col.find({
        "user_id": {"$in": user_ids},
        "status": "approved",
        "from_date": {"$lte": today_str},
        "to_date": {"$gte": today_str},
    }, {"_id": 0, "user_id": 1}):
        on_leave.add(lr["user_id"])

    out = []
    counts = {"present": 0, "late": 0, "absent": 0, "leave": 0, "wfh": 0}
    for e in employees:
        log = logs.get(e["id"])
        if e["id"] in on_leave:
            status = "leave"
            counts["leave"] += 1
        elif log:
            if log.get("is_late"):
                status = "late"
                counts["late"] += 1
            else:
                status = "present"
                counts["present"] += 1
            if log.get("work_mode") == "wfh":
                counts["wfh"] += 1
        else:
            status = "absent"
            counts["absent"] += 1
        out.append({
            **e,
            "status": status,
            "punch_in": (log.get("punch_in_at", "")[11:16] if log and log.get("punch_in_at") else None),
            "punch_out": (log.get("punch_out_at", "")[11:16] if log and log.get("punch_out_at") else None),
            "late_by_minutes": log.get("late_by_minutes", 0) if log else 0,
            "work_mode": log.get("work_mode") if log else None,
        })

    return {
        "date": today_str,
        "total_employees": len(employees),
        "counts": counts,
        "employees": out,
    }


# ──────────────────────────────────────────────────────────────
# My late marks
# ──────────────────────────────────────────────────────────────
@router.get("/late-marks/my")
async def my_late_marks(
    year_month: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    settings = await get_settings()
    data = await get_late_marks_count(current_user["id"], year_month)
    data["threshold"] = int(settings.get("late_marks_for_leave_deduction", 3))
    return data


# ──────────────────────────────────────────────────────────────
# Regularization
# ──────────────────────────────────────────────────────────────
@router.post("/regularize")
async def regularize_attendance(
    payload: RegularizeRequest,
    current_user: dict = Depends(get_current_user),
):
    settings = await get_settings()
    grace_days = int(settings.get("regularization_grace_days", 3))
    try:
        d = parse_date(payload.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)")

    today = now_ist().date()
    if d > today:
        raise HTTPException(status_code=400, detail="Cannot regularize future date")
    if (today - d).days > grace_days:
        raise HTTPException(
            status_code=400,
            detail=f"Regularization window expired ({grace_days} days). Contact HR for manual fix."
        )

    from core.attendance_logic import resolve_approvers
    approvers = await resolve_approvers(current_user)

    req = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_name": current_user.get("name"),
        "department": current_user.get("department"),
        "date": payload.date,
        "reason": payload.reason,
        "request_type": payload.request_type,
        "correct_punch_in": payload.correct_punch_in,
        "correct_punch_out": payload.correct_punch_out,
        "manager_id": approvers["l1_manager_id"],
        "manager_name": approvers["l1_manager_name"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }
    await attendance_regularizations_col.insert_one(req)

    if approvers["l1_manager_id"]:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": approvers["l1_manager_id"],
            "title": "Attendance regularization request",
            "message": f"{current_user.get('name')} requested regularization for {payload.date}.",
            "type": "regularization",
            "entity_id": req["id"],
            "read": False,
            "created_at": datetime.now(timezone.utc),
        })

    return {"message": "Regularization submitted", "request_id": req["id"]}


@router.get("/regularizations/inbox")
async def regularizations_inbox(
    status: str = "pending",
    current_user: dict = Depends(require_any_permission(
        "leave.approve.l1", "attendance.update.team", "attendance.update.all"
    )),
):
    items = []
    async for r in attendance_regularizations_col.find(
        {"manager_id": current_user["id"], "status": status},
        {"_id": 0},
    ).sort("created_at", -1).limit(100):
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
        items.append(r)
    return items


@router.get("/regularizations/my")
async def my_regularizations(current_user: dict = Depends(get_current_user)):
    items = []
    async for r in attendance_regularizations_col.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("created_at", -1).limit(50):
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
        items.append(r)
    return items


@router.post("/regularizations/{reg_id}/decide")
async def decide_regularization(
    reg_id: str,
    payload: RegularizationDecide,
    current_user: dict = Depends(require_any_permission(
        "leave.approve.l1", "attendance.update.team", "attendance.update.all"
    )),
):
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")

    reg = await attendance_regularizations_col.find_one({"id": reg_id}, {"_id": 0})
    if not reg:
        raise HTTPException(status_code=404, detail="Regularization not found")
    if reg["manager_id"] != current_user["id"] and current_user.get("rbac_role") not in ("admin_owner", "hr_head"):
        raise HTTPException(status_code=403, detail="Only the assigned manager can decide")
    if reg["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Already {reg['status']}")

    await attendance_regularizations_col.update_one(
        {"id": reg_id},
        {"$set": {
            "status": payload.decision,
            "decided_by": current_user["id"],
            "decided_by_name": current_user.get("name"),
            "decision_note": payload.note,
            "decided_at": datetime.now(timezone.utc),
        }}
    )

    if payload.decision == "approved":
        d = parse_date(reg["date"])
        date_str = reg["date"]
        if reg["request_type"] in ("missed_punch", "wrong_time"):
            settings = await get_settings()
            office_start_h, office_start_m = map(int, settings["office_start_time"].split(":"))
            office_end_h, office_end_m = map(int, settings["office_end_time"].split(":"))
            pin = reg.get("correct_punch_in") or f"{office_start_h:02d}:{office_start_m:02d}"
            pout = reg.get("correct_punch_out") or f"{office_end_h:02d}:{office_end_m:02d}"
            punch_in = datetime(d.year, d.month, d.day, *map(int, pin.split(":")))
            punch_out = datetime(d.year, d.month, d.day, *map(int, pout.split(":")))
            total_min = int((punch_out - punch_in).total_seconds() // 60)

            await attendance_logs_col.update_one(
                {"user_id": reg["user_id"], "date": date_str},
                {
                    "$set": {
                        "user_id": reg["user_id"],
                        "user_name": reg.get("user_name"),
                        "department": reg.get("department"),
                        "date": date_str,
                        "year_month": date_str[:7],
                        "punch_in_at": punch_in.isoformat(),
                        "punch_out_at": punch_out.isoformat(),
                        "total_minutes": total_min,
                        "is_late": False,
                        "late_by_minutes": 0,
                        "status": "regularized",
                        "regularized_by": current_user["id"],
                        "regularization_id": reg_id,
                        "updated_at": datetime.now(timezone.utc),
                    },
                    "$setOnInsert": {
                        "id": str(uuid.uuid4()),
                        "created_at": datetime.now(timezone.utc),
                    },
                },
                upsert=True,
            )

        if reg["request_type"] == "lwp_dispute":
            await lwp_records_col.update_one(
                {"user_id": reg["user_id"], "date": date_str},
                {"$set": {"regularization_status": "approved", "regularization_id": reg_id}},
            )

    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": reg["user_id"],
        "title": f"Regularization {payload.decision}",
        "message": f"Your regularization for {reg['date']} was {payload.decision}." +
                   (f" Note: {payload.note}" if payload.note else ""),
        "type": "regularization_decision",
        "read": False,
        "created_at": datetime.now(timezone.utc),
    })

    return {"message": f"Regularization {payload.decision}"}


# ──────────────────────────────────────────────────────────────
# HR dashboard
# ──────────────────────────────────────────────────────────────
@router.get("/dashboard")
async def attendance_dashboard(
    current_user: dict = Depends(require_any_permission(
        "attendance.view.all", "attendance.view.dept"
    )),
):
    today_str = today_ist_str()
    ym = today_str[:7]
    today_data = await today_attendance(current_user=current_user)
    counts = today_data["counts"]

    total_late_marks = 0
    total_deductions = 0
    async for lm in late_marks_tracker_col.find({"year_month": ym}, {"_id": 0}):
        total_late_marks += lm.get("late_marks_count", 0)
        total_deductions += lm.get("deductions_applied", 0)

    total_lwp = await lwp_records_col.count_documents({
        "date": {"$regex": f"^{ym}"},
    })

    pending_leaves = await leave_requests_col.count_documents({"status": {"$in": ["pending_l1", "pending_final"]}})

    return {
        "today": today_str,
        "year_month": ym,
        "today_counts": counts,
        "total_late_marks_this_month": total_late_marks,
        "total_cl_auto_deducted_this_month": total_deductions,
        "total_lwp_this_month": total_lwp,
        "pending_leave_requests": pending_leaves,
        "total_employees": today_data["total_employees"],
    }


# ──────────────────────────────────────────────────────────────
# LWP scan (admin trigger)
# ──────────────────────────────────────────────────────────────
@router.post("/lwp/scan")
async def scan_for_lwp(
    target_date: Optional[str] = None,
    current_user: dict = Depends(require_any_permission(
        "attendance.update.all", "leave.approve.final"
    )),
):
    settings = await get_settings()
    if not settings.get("auto_mark_lwp_for_unapproved_absence", True):
        return {"message": "LWP auto-marking is disabled in settings"}

    yesterday = now_ist().date() - timedelta(days=1)
    d = parse_date(target_date) if target_date else yesterday

    if not await is_working_day(d, settings):
        return {"message": f"{d.isoformat()} is not a working day (holiday or weekly off)", "scanned": 0}

    scanned = 0
    marked = 0
    async for u in users_col.find(
        {"user_type": "internal", "status": "active"},
        {"_id": 0, "id": 1, "name": 1},
    ):
        scanned += 1
        from core.attendance_logic import has_punched_on
        if await has_punched_on(u["id"], d):
            continue
        if await has_approved_leave_on(u["id"], d):
            continue
        applied = await mark_lwp_for_date(u["id"], d, reason="no_approval")
        if applied:
            marked += 1

    return {"date": d.isoformat(), "scanned": scanned, "marked_lwp": marked}
