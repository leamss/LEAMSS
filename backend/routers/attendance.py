"""Attendance Router — Phase 3

Tracks clock-in/out, late detection, monthly calendar, regularization,
and admin/manager rollup views.
"""
import uuid
from datetime import datetime, timezone, timedelta, date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.database import db, users_col
from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission

router = APIRouter(prefix="/attendance", tags=["Attendance"])

attendance_col = db["attendance_records"]
attendance_settings_col = db["attendance_settings"]
holidays_col = db["holidays"]
activity_log_col = db["activity_log"]


# ────────────────────────────────────────────────────────────
# Default settings
# ────────────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "key": "company",
    "office_start_time": "09:30",
    "office_end_time": "18:30",
    "working_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    "min_work_hours": 8.0,
    "half_day_threshold_hours": 4.0,
    "late_threshold_minutes": 15,
    "geo_fencing_enabled": False,
    "office_locations": [],
    "allow_wfh": True,
    "require_clock_out_reason": False,
}


async def get_settings():
    s = await attendance_settings_col.find_one({"key": "company"}, {"_id": 0})
    if not s:
        s = {**DEFAULT_SETTINGS, "created_at": datetime.now(timezone.utc)}
        await attendance_settings_col.insert_one(s.copy())
    return s


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _serialize(r: dict) -> dict:
    out = {k: v for k, v in r.items() if k != "_id"}
    for f in ("clock_in_time", "clock_out_time", "created_at", "updated_at",
              "regularization_approved_at"):
        if isinstance(out.get(f), datetime):
            out[f] = out[f].isoformat()
    return out


def _parse_hhmm(s: str) -> tuple:
    h, m = s.split(":")
    return int(h), int(m)


# ────────────────────────────────────────────────────────────
# Models
# ────────────────────────────────────────────────────────────
class ClockInBody(BaseModel):
    location: Optional[dict] = None  # {lat, lng, accuracy}
    notes: Optional[str] = None


class ClockOutBody(BaseModel):
    location: Optional[dict] = None
    notes: Optional[str] = None


class RegularizeBody(BaseModel):
    date: str  # YYYY-MM-DD
    reason: str
    suggested_clock_in: Optional[str] = None  # HH:MM
    suggested_clock_out: Optional[str] = None


class SettingsUpdate(BaseModel):
    office_start_time: Optional[str] = None
    office_end_time: Optional[str] = None
    working_days: Optional[list] = None
    min_work_hours: Optional[float] = None
    half_day_threshold_hours: Optional[float] = None
    late_threshold_minutes: Optional[int] = None
    geo_fencing_enabled: Optional[bool] = None
    allow_wfh: Optional[bool] = None


# ────────────────────────────────────────────────────────────
# Clock In / Out
# ────────────────────────────────────────────────────────────
@router.post("/clock-in")
async def clock_in(body: ClockInBody, current_user: dict = Depends(get_current_user)):
    if current_user.get("user_type") != "internal":
        raise HTTPException(status_code=403, detail="Only internal employees can clock in")

    today = _today_str()
    existing = await attendance_col.find_one({"user_id": current_user["id"], "date": today}, {"_id": 0})
    if existing and existing.get("clock_in_time"):
        raise HTTPException(status_code=400, detail="Already clocked in today")

    now = datetime.now(timezone.utc)
    settings = await get_settings()
    office_h, office_m = _parse_hhmm(settings["office_start_time"])
    office_start = now.replace(hour=office_h, minute=office_m, second=0, microsecond=0)
    late_threshold = timedelta(minutes=settings.get("late_threshold_minutes", 15))

    is_late = now > (office_start + late_threshold)
    late_by_minutes = max(0, int((now - office_start).total_seconds() / 60)) if is_late else 0

    record = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "date": today,
        "clock_in_time": now,
        "clock_out_time": None,
        "clock_in_location": body.location,
        "clock_in_notes": body.notes,
        "status": "present",
        "is_late": is_late,
        "late_by_minutes": late_by_minutes,
        "work_hours_total": 0.0,
        "created_at": now,
    }
    await attendance_col.replace_one(
        {"user_id": current_user["id"], "date": today},
        record,
        upsert=True,
    )

    return {
        "record_id": record["id"],
        "clock_in_time": now.isoformat(),
        "is_late": is_late,
        "late_by_minutes": late_by_minutes,
        "message": f"Clocked in at {now.strftime('%I:%M %p')}" + (f" ({late_by_minutes} min late)" if is_late else ""),
    }


@router.post("/clock-out")
async def clock_out(body: ClockOutBody, current_user: dict = Depends(get_current_user)):
    today = _today_str()
    record = await attendance_col.find_one({"user_id": current_user["id"], "date": today}, {"_id": 0})
    if not record or not record.get("clock_in_time"):
        raise HTTPException(status_code=400, detail="You haven't clocked in today")
    if record.get("clock_out_time"):
        raise HTTPException(status_code=400, detail="Already clocked out today")

    now = datetime.now(timezone.utc)
    clock_in = record["clock_in_time"]
    if isinstance(clock_in, str):
        clock_in = datetime.fromisoformat(clock_in.replace("Z", "+00:00"))
    if clock_in.tzinfo is None:
        clock_in = clock_in.replace(tzinfo=timezone.utc)

    work_hours = round((now - clock_in).total_seconds() / 3600, 2)

    settings = await get_settings()
    half_day_threshold = settings.get("half_day_threshold_hours", 4)
    status = "half_day" if work_hours < half_day_threshold else "present"

    await attendance_col.update_one(
        {"user_id": current_user["id"], "date": today},
        {"$set": {
            "clock_out_time": now,
            "clock_out_location": body.location,
            "clock_out_notes": body.notes,
            "work_hours_total": work_hours,
            "status": status,
            "updated_at": now,
        }}
    )
    return {
        "clock_out_time": now.isoformat(),
        "work_hours_total": work_hours,
        "was_late": record.get("is_late", False),
        "status": status,
        "message": f"Clocked out — {work_hours}h worked today",
    }


@router.get("/today")
async def attendance_today(current_user: dict = Depends(get_current_user)):
    today = _today_str()
    record = await attendance_col.find_one({"user_id": current_user["id"], "date": today}, {"_id": 0})
    settings = await get_settings()
    if not record:
        return {"clocked_in": False, "clocked_out": False, "settings": settings}
    return {
        "clocked_in": bool(record.get("clock_in_time")),
        "clocked_out": bool(record.get("clock_out_time")),
        "record": _serialize(record),
        "settings": settings,
    }


# ────────────────────────────────────────────────────────────
# Monthly view
# ────────────────────────────────────────────────────────────
async def _build_month_view(user_id: str, month: str):
    """Returns dict of date → record for the given user/month."""
    cursor = attendance_col.find(
        {"user_id": user_id, "date": {"$regex": f"^{month}-"}},
        {"_id": 0},
    )
    records = {}
    async for r in cursor:
        records[r["date"]] = _serialize(r)
    return records


@router.get("/my")
async def my_attendance(
    month: Optional[str] = Query(None, description="YYYY-MM"),
    current_user: dict = Depends(get_current_user),
):
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    records = await _build_month_view(current_user["id"], month)

    # Holidays for context
    holidays = {}
    async for h in holidays_col.find({"date": {"$regex": f"^{month}-"}}, {"_id": 0}):
        holidays[h["date"]] = h.get("name", "Holiday")

    # Stats
    total_present = sum(1 for r in records.values() if r.get("status") == "present")
    total_half = sum(1 for r in records.values() if r.get("status") == "half_day")
    total_leave = sum(1 for r in records.values() if r.get("status") == "leave")
    total_hours = sum(r.get("work_hours_total", 0) for r in records.values())
    days_with_hours = sum(1 for r in records.values() if r.get("work_hours_total", 0) > 0)
    avg_hours = round(total_hours / days_with_hours, 2) if days_with_hours else 0

    return {
        "month": month,
        "records": records,
        "holidays": holidays,
        "stats": {
            "total_present": total_present,
            "total_half_day": total_half,
            "total_leave": total_leave,
            "total_hours": round(total_hours, 2),
            "avg_hours": avg_hours,
            "late_count": sum(1 for r in records.values() if r.get("is_late")),
        },
    }


@router.get("/team")
async def team_attendance(
    month: Optional[str] = Query(None),
    current_user: dict = Depends(require_any_permission("attendance.view.team", "attendance.view.dept", "attendance.view.all")),
):
    """Team attendance — current user's direct reports."""
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    reports = []
    async for u in users_col.find(
        {"reports_to": current_user["id"], "user_type": "internal", "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "designation": 1, "department": 1, "employee_id": 1, "avatar_url": 1},
    ):
        records = await _build_month_view(u["id"], month)
        u["attendance"] = records
        reports.append(u)
    return {"month": month, "team": reports, "total": len(reports)}


@router.get("/all")
async def all_attendance(
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    department: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(require_any_permission("attendance.view.all", "attendance.export.all")),
):
    """HR/Admin master view — all employees for a single date."""
    target_date = date or _today_str()

    # Get all internal employees
    user_query = {"user_type": "internal", "status": "active"}
    if department:
        user_query["department"] = department
    employees = {}
    async for u in users_col.find(user_query, {"_id": 0, "id": 1, "name": 1, "department": 1, "designation": 1, "employee_id": 1}):
        employees[u["id"]] = u

    # Get their attendance for that date
    records = {}
    async for r in attendance_col.find({"date": target_date, "user_id": {"$in": list(employees.keys())}}, {"_id": 0}):
        records[r["user_id"]] = _serialize(r)

    rows = []
    for uid, emp in employees.items():
        rec = records.get(uid)
        row = {**emp, "attendance": rec, "status_label": rec.get("status") if rec else "absent"}
        if status and row["status_label"] != status:
            continue
        rows.append(row)

    # Totals
    counts = {"present": 0, "half_day": 0, "leave": 0, "absent": 0, "late": 0}
    for r in rows:
        st = r["status_label"]
        if st in counts:
            counts[st] += 1
        if r.get("attendance", {}) and r["attendance"].get("is_late"):
            counts["late"] += 1

    return {"date": target_date, "rows": rows, "totals": counts, "total_employees": len(rows)}


# ────────────────────────────────────────────────────────────
# Regularization
# ────────────────────────────────────────────────────────────
@router.post("/regularize")
async def request_regularize(body: RegularizeBody, current_user: dict = Depends(get_current_user)):
    if current_user.get("user_type") != "internal":
        raise HTTPException(status_code=403, detail="Only internal employees")

    now = datetime.now(timezone.utc)
    existing = await attendance_col.find_one({"user_id": current_user["id"], "date": body.date}, {"_id": 0})
    record = existing or {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "date": body.date,
        "created_at": now,
    }
    record.update({
        "is_regularization": True,
        "regularization_reason": body.reason,
        "regularization_status": "pending",
        "regularization_requested_at": now,
        "regularization_suggested_in": body.suggested_clock_in,
        "regularization_suggested_out": body.suggested_clock_out,
        "updated_at": now,
    })
    if existing:
        await attendance_col.update_one({"user_id": current_user["id"], "date": body.date}, {"$set": record})
    else:
        await attendance_col.insert_one(record)

    # Notify manager
    if current_user.get("reports_to"):
        await db["notifications"].insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user["reports_to"],
            "title": "Attendance Regularization Request",
            "message": f"{current_user.get('name')} requests regularization for {body.date}",
            "type": "regularization_request",
            "read": False,
            "created_at": now,
        })
    return {"message": "Regularization requested. Awaiting manager approval.", "record_id": record["id"]}


@router.post("/regularize/{user_id}/{date}/approve")
async def approve_regularize(
    user_id: str, date: str,
    current_user: dict = Depends(require_any_permission("attendance.update.team", "attendance.update.all")),
):
    record = await attendance_col.find_one({"user_id": user_id, "date": date}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="No request found")

    now = datetime.now(timezone.utc)
    # Apply suggested times if provided
    updates = {
        "regularization_status": "approved",
        "regularization_approved_by": current_user["id"],
        "regularization_approved_at": now,
        "status": "present",
    }
    if record.get("regularization_suggested_in"):
        h, m = _parse_hhmm(record["regularization_suggested_in"])
        d_parts = date.split("-")
        updates["clock_in_time"] = datetime(int(d_parts[0]), int(d_parts[1]), int(d_parts[2]), h, m, tzinfo=timezone.utc)
    if record.get("regularization_suggested_out"):
        h, m = _parse_hhmm(record["regularization_suggested_out"])
        d_parts = date.split("-")
        updates["clock_out_time"] = datetime(int(d_parts[0]), int(d_parts[1]), int(d_parts[2]), h, m, tzinfo=timezone.utc)
        if "clock_in_time" in updates:
            updates["work_hours_total"] = round((updates["clock_out_time"] - updates["clock_in_time"]).total_seconds() / 3600, 2)
    await attendance_col.update_one({"user_id": user_id, "date": date}, {"$set": updates})

    await db["notifications"].insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": "Attendance Regularized",
        "message": f"Your regularization for {date} has been approved",
        "type": "regularization_approved",
        "read": False,
        "created_at": now,
    })
    return {"message": "Regularization approved"}


# ────────────────────────────────────────────────────────────
# Settings
# ────────────────────────────────────────────────────────────
@router.get("/settings")
async def get_attendance_settings(current_user: dict = Depends(get_current_user)):
    return await get_settings()


@router.patch("/settings")
async def update_attendance_settings(
    body: SettingsUpdate,
    current_user: dict = Depends(require_any_permission("system.update.any", "attendance.update.all")),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"message": "No changes"}
    updates["updated_at"] = datetime.now(timezone.utc)
    updates["updated_by"] = current_user["id"]
    await attendance_settings_col.update_one({"key": "company"}, {"$set": updates}, upsert=True)
    return {"message": "Settings updated", "fields": list(updates.keys())}
