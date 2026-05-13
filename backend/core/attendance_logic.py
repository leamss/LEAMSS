"""Attendance & Leave Business Logic Helpers.

All company policies are implemented here as pure functions
so they can be reused across routers and tested in isolation.

Policies:
- Late detection (10:10 AM cutoff)
- Late marks tracking (3 = -1 CL)
- Work hours compensation
- Sandwich leave detection (Fri+Mon, Sat+Mon, Fri+Sat+Mon)
- Monthly CL cap
- Max consecutive days (7)
- Long leave once-per-year (>5 days)
- LWP auto-marking
"""
import uuid
from datetime import datetime, timezone, timedelta, date, time
from typing import Optional, List, Tuple
from core.database import (
    attendance_settings_col, attendance_logs_col, leave_types_col,
    leave_balances_col, leave_requests_col, holidays_col,
    late_marks_tracker_col, leave_balance_history_col, lwp_records_col,
    users_col, notifications_col,
)

INDIA_TZ_OFFSET_HOURS = 5.5  # IST


# ────────────────────────────────────────────────────────
# Time / Date helpers
# ────────────────────────────────────────────────────────
def now_ist() -> datetime:
    """Current time in IST (timezone-aware UTC)."""
    return datetime.now(timezone.utc) + timedelta(hours=INDIA_TZ_OFFSET_HOURS)


def to_ist(dt: datetime) -> datetime:
    """Convert a UTC datetime to IST naive."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc) + timedelta(hours=INDIA_TZ_OFFSET_HOURS)


def today_ist_str() -> str:
    """Today's date in IST as YYYY-MM-DD."""
    return now_ist().strftime("%Y-%m-%d")


def year_month_str(d: Optional[date] = None) -> str:
    """Returns YYYY-MM for a given date (today by default)."""
    d = d or now_ist().date()
    return d.strftime("%Y-%m")


def parse_date(s: str) -> date:
    """Parse YYYY-MM-DD into a date object."""
    return datetime.strptime(s, "%Y-%m-%d").date()


def date_range(start: date, end: date) -> List[date]:
    """Inclusive list of dates between start and end."""
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


async def get_settings() -> dict:
    """Get global attendance settings (singleton). Falls back to in-code defaults."""
    s = await attendance_settings_col.find_one({"key": "global"}, {"_id": 0})
    if not s:
        # Should never happen if migration ran — fallback
        from migrations.attendance_leave_migration import DEFAULT_SETTINGS
        return DEFAULT_SETTINGS
    return s


async def get_holiday_dates(year: int) -> List[str]:
    """Return list of holiday date strings for a year."""
    out = []
    async for h in holidays_col.find({"year": year}, {"_id": 0, "date": 1}):
        out.append(h["date"])
    return out


async def is_holiday(d: date) -> bool:
    """Is the given date a public holiday?"""
    h = await holidays_col.find_one({"date": d.strftime("%Y-%m-%d")}, {"_id": 0, "id": 1})
    return h is not None


def is_weekly_off(d: date, weekly_off_days: List[int]) -> bool:
    """Is the given date a weekly-off (e.g., Sunday)?"""
    return d.weekday() in weekly_off_days


async def is_working_day(d: date, settings: Optional[dict] = None) -> bool:
    """True if it's a working day (not weekly off + not holiday)."""
    settings = settings or await get_settings()
    if is_weekly_off(d, settings.get("weekly_off_days", [6])):
        return False
    if await is_holiday(d):
        return False
    return True


# ────────────────────────────────────────────────────────
# Punch logic
# ────────────────────────────────────────────────────────
def compute_late_status(punch_in_time: datetime, settings: dict) -> Tuple[bool, int]:
    """Given an IST punch-in datetime, return (is_late, late_by_minutes).

    Late = punched in after (office_start_time + late_threshold_minutes).
    """
    office_start_h, office_start_m = map(int, settings["office_start_time"].split(":"))
    grace_min = int(settings.get("late_threshold_minutes", 10))
    cutoff = punch_in_time.replace(
        hour=office_start_h, minute=office_start_m, second=0, microsecond=0
    ) + timedelta(minutes=grace_min)
    # Reference for "on-time": exact office_start
    on_time = punch_in_time.replace(
        hour=office_start_h, minute=office_start_m, second=0, microsecond=0
    )
    if punch_in_time <= cutoff:
        return False, 0
    diff = punch_in_time - on_time
    return True, int(diff.total_seconds() // 60)


def compute_expected_clock_out(punch_in_time: datetime, settings: dict) -> datetime:
    """Punch-in + min_work_hours."""
    hrs = float(settings.get("min_work_hours", 9))
    return punch_in_time + timedelta(hours=hrs)


# ────────────────────────────────────────────────────────
# Late marks & auto CL deduction
# ────────────────────────────────────────────────────────
async def record_late_mark(user_id: str, punch_date: str, late_by_min: int) -> dict:
    """Increment late_marks counter for user-month and apply -1 CL when threshold hit.

    Returns dict with: count_after, deduction_applied (bool)
    """
    settings = await get_settings()
    threshold = int(settings.get("late_marks_for_leave_deduction", 3))
    ym = punch_date[:7]  # YYYY-MM

    existing = await late_marks_tracker_col.find_one(
        {"user_id": user_id, "year_month": ym}, {"_id": 0}
    )
    if not existing:
        new_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "year_month": ym,
            "late_marks_count": 1,
            "deductions_applied": 0,
            "late_dates": [punch_date],
            "last_late_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
        }
        await late_marks_tracker_col.insert_one(new_doc)
        count_after = 1
        deductions_before = 0
    else:
        # Avoid double counting if same date already recorded
        if punch_date in existing.get("late_dates", []):
            return {
                "count_after": existing["late_marks_count"],
                "deduction_applied": False,
                "already_counted": True,
            }
        count_after = existing["late_marks_count"] + 1
        deductions_before = existing.get("deductions_applied", 0)
        await late_marks_tracker_col.update_one(
            {"user_id": user_id, "year_month": ym},
            {
                "$inc": {"late_marks_count": 1},
                "$push": {"late_dates": punch_date},
                "$set": {"last_late_at": datetime.now(timezone.utc)},
            },
        )

    # Apply CL deduction every Nth late mark
    deduction_applied = False
    if count_after // threshold > deductions_before:
        await _apply_auto_cl_deduction(user_id, ym, count_after, late_by_min)
        await late_marks_tracker_col.update_one(
            {"user_id": user_id, "year_month": ym},
            {"$inc": {"deductions_applied": 1},
             "$set": {"last_deduction_at": datetime.now(timezone.utc)}},
        )
        deduction_applied = True

    return {
        "count_after": count_after,
        "deduction_applied": deduction_applied,
        "threshold": threshold,
    }


async def _apply_auto_cl_deduction(user_id: str, year_month: str, late_count: int, late_by_min: int):
    """Deduct 1 day from casual_leave balance + log + notify."""
    year = int(year_month[:4])
    bal = await leave_balances_col.find_one(
        {"user_id": user_id, "leave_type_key": "casual_leave", "year": year},
        {"_id": 0},
    )
    if not bal:
        return  # no balance doc

    before = float(bal.get("available", 0))
    after = max(0, before - 1)
    await leave_balances_col.update_one(
        {"id": bal["id"]},
        {"$set": {"available": after, "updated_at": datetime.now(timezone.utc)},
         "$inc": {"used": 1}},
    )

    # Audit log
    await leave_balance_history_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "date": datetime.now(timezone.utc),
        "leave_type_key": "casual_leave",
        "change_type": "auto_deducted_late",
        "delta": -1,
        "balance_before": before,
        "balance_after": after,
        "reason": f"Auto-deducted 1 CL — {late_count} late marks in {year_month}",
        "triggered_by": "system",
        "created_at": datetime.now(timezone.utc),
    })

    # Notify
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": "1 Casual Leave Auto-Deducted",
        "message": f"You hit {late_count} late marks this month ({year_month}). 1 CL has been deducted from your balance.",
        "type": "leave_deduction",
        "read": False,
        "created_at": datetime.now(timezone.utc),
    })


async def get_late_marks_count(user_id: str, year_month: Optional[str] = None) -> dict:
    """Returns {count, deductions, dates}."""
    ym = year_month or year_month_str()
    doc = await late_marks_tracker_col.find_one(
        {"user_id": user_id, "year_month": ym}, {"_id": 0}
    )
    if not doc:
        return {"count": 0, "deductions": 0, "dates": [], "year_month": ym}
    return {
        "count": doc.get("late_marks_count", 0),
        "deductions": doc.get("deductions_applied", 0),
        "dates": doc.get("late_dates", []),
        "year_month": ym,
    }


# ────────────────────────────────────────────────────────
# Sandwich leave detection
# ────────────────────────────────────────────────────────
async def expand_sandwich_dates(from_date: date, to_date: date, settings: dict) -> dict:
    """Detect if the leave range qualifies as a 'sandwich leave' and expand
    weekend days to be counted.

    Policy: if a leave touches Friday and the following Monday (with Sat/Sun
    in between as non-working), OR Sat+Mon, then the weekend IS counted as
    part of the leave (4 days for Fri-Mon, 3 days for Sat-Mon).

    Returns:
        {
          is_sandwich: bool,
          counted_dates: [date, ...]   # all dates that consume balance
          working_dates: [date, ...]   # subset that are actual working days
          weekend_included: int,
          original_dates: [date, ...]
        }
    """
    if not settings.get("enforce_sandwich_leave", True):
        all_d = date_range(from_date, to_date)
        working = [d for d in all_d if await is_working_day(d, settings)]
        return {
            "is_sandwich": False,
            "counted_dates": working,
            "working_dates": working,
            "weekend_included": 0,
            "original_dates": all_d,
        }

    original = date_range(from_date, to_date)
    is_sandwich = False
    extra_weekend = []
    weekend_in_range = 0

    # Case 1: range is Fri → Mon (4 days: Fri, Sat, Sun, Mon)
    if from_date.weekday() == 4 and to_date.weekday() == 0 and (to_date - from_date).days == 3:
        is_sandwich = True
        weekend_in_range = 2

    # Case 2: range is Sat → Mon (3 days: Sat, Sun, Mon)
    elif from_date.weekday() == 5 and to_date.weekday() == 0 and (to_date - from_date).days == 2:
        is_sandwich = True
        weekend_in_range = 2  # Sun (weekly off) + Sat technically a working day in policy

    # Case 3: user submits Fri-only OR Mon-only — sandwich detection for separate days
    # would require cross-request checks; we handle Fri-Mon and Sat-Mon as the primary
    # detection. Other patterns (e.g., Thu-Mon) naturally count all days as continuous.

    # Case 4: range starts with Fri, has explicit weekend skip (user submitted Fri AND Mon
    # in same range but somehow excluded weekend — not possible in from-to, but kept for safety):
    range_set = set(original)
    for d in original:
        if d.weekday() == 4:  # Friday
            mon = d + timedelta(days=3)
            sat = d + timedelta(days=1)
            sun = d + timedelta(days=2)
            if mon in range_set and (sat not in range_set or sun not in range_set):
                is_sandwich = True
                if sat not in range_set:
                    extra_weekend.append(sat)
                if sun not in range_set:
                    extra_weekend.append(sun)

    counted = sorted(set(original) | set(extra_weekend))
    working_dates = [d for d in counted if await is_working_day(d, settings)]

    return {
        "is_sandwich": is_sandwich,
        "counted_dates": counted,
        "working_dates": working_dates,
        "weekend_included": len(extra_weekend) + (weekend_in_range if is_sandwich and not extra_weekend else 0),
        "original_dates": original,
    }


# ────────────────────────────────────────────────────────
# Leave application validation
# ────────────────────────────────────────────────────────
async def validate_leave_request(
    user_id: str,
    leave_type_key: str,
    from_date_str: str,
    to_date_str: str,
    settings: Optional[dict] = None,
) -> dict:
    """Run ALL policy checks. Returns:
    {
      ok: bool,
      errors: [str, ...],
      warnings: [str, ...],
      days_breakdown: { ...sandwich result },
      total_days: float,
      working_days: int,
    }

    Caller can choose to proceed even with warnings (e.g., sandwich detected).
    Errors are blocking.
    """
    settings = settings or await get_settings()
    errors = []
    warnings = []

    try:
        from_d = parse_date(from_date_str)
        to_d = parse_date(to_date_str)
    except ValueError:
        return {"ok": False, "errors": ["Invalid date format (use YYYY-MM-DD)"], "warnings": []}

    if to_d < from_d:
        return {"ok": False, "errors": ["End date is before start date"], "warnings": []}

    # Leave type lookup
    lt = await leave_types_col.find_one({"key": leave_type_key, "is_active": True}, {"_id": 0})
    if not lt:
        return {"ok": False, "errors": [f"Leave type '{leave_type_key}' not found"], "warnings": []}

    # Sandwich detection + days breakdown
    days_breakdown = await expand_sandwich_dates(from_d, to_d, settings)
    counted = days_breakdown["counted_dates"]
    working = days_breakdown["working_dates"]
    total_counted = len(counted)

    if days_breakdown["is_sandwich"]:
        warnings.append(
            f"⚠️ Sandwich Leave detected. Total {total_counted} days will be deducted "
            f"(working: {len(working)}, weekend: {days_breakdown['weekend_included']})"
        )

    if total_counted == 0:
        errors.append("No working days in the selected range")
        return {"ok": False, "errors": errors, "warnings": warnings,
                "days_breakdown": days_breakdown, "total_days": 0, "working_days": 0}

    # Max consecutive days check
    max_consec_company = int(settings.get("max_consecutive_leave_days", 7))
    max_consec_type = int(lt.get("max_consecutive", 365))
    max_consec = min(max_consec_company, max_consec_type)
    if total_counted > max_consec:
        errors.append(
            f"❌ Maximum {max_consec} consecutive days allowed for {lt['name']}. "
            f"You're applying for {total_counted} days."
        )

    # Long leave (>threshold) once-per-year check
    long_threshold = int(settings.get("long_leave_threshold_days", 5))
    max_long_per_yr = int(settings.get("max_long_leaves_per_year", 1))
    if total_counted > long_threshold:
        year = from_d.year
        existing_long = await leave_requests_col.count_documents({
            "user_id": user_id,
            "status": {"$in": ["approved", "approved_l1"]},
            "total_days": {"$gt": long_threshold},
            "from_date": {
                "$gte": f"{year}-01-01",
                "$lte": f"{year}-12-31",
            },
            "leave_type_key": {"$ne": "maternity_leave"},  # maternity exempt
        })
        if existing_long >= max_long_per_yr:
            errors.append(
                f"❌ You've already used your one long leave (>{long_threshold} days) "
                f"for {year}. Max {max_long_per_yr} per year."
            )

    # Monthly CL cap (counts approved + pending in same month)
    if leave_type_key == "casual_leave" and settings.get("enforce_monthly_cl_limit", True):
        monthly_cap = int(lt.get("monthly_cap", 1))
        if monthly_cap > 0:
            month_key = from_d.strftime("%Y-%m")
            bal = await leave_balances_col.find_one(
                {"user_id": user_id, "leave_type_key": "casual_leave", "year": from_d.year},
                {"_id": 0, "monthly_used": 1},
            )
            approved_this_month = (bal.get("monthly_used", {}) if bal else {}).get(month_key, 0)
            # Also count pending requests for the same month
            month_start = f"{month_key}-01"
            month_end = f"{month_key}-31"
            pending_this_month = await leave_requests_col.count_documents({
                "user_id": user_id,
                "leave_type_key": "casual_leave",
                "status": {"$in": ["pending_l1", "pending_final"]},
                "from_date": {"$gte": month_start, "$lte": month_end},
            })
            total_used_or_pending = approved_this_month + pending_this_month
            if total_used_or_pending + total_counted > monthly_cap:
                errors.append(
                    f"❌ Monthly Casual Leave limit exceeded. "
                    f"{monthly_cap} CL/month allowed. "
                    f"{approved_this_month} approved, {pending_this_month} pending in {month_key}."
                )

    # Min notice days check (for EL, Paternity, etc.)
    min_notice = int(lt.get("min_notice_days", 0))
    if min_notice > 0:
        today = now_ist().date()
        notice_diff = (from_d - today).days
        if notice_diff < min_notice:
            warnings.append(
                f"⚠️ Minimum {min_notice} days notice required for {lt['name']}. "
                f"You're applying with {notice_diff} days notice."
            )

    # Balance check
    if leave_type_key != "lwp":
        bal = await leave_balances_col.find_one(
            {"user_id": user_id, "leave_type_key": leave_type_key, "year": from_d.year},
            {"_id": 0, "available": 1},
        )
        available = float(bal.get("available", 0)) if bal else 0
        # For comp_off, allow if user has earned
        if available < total_counted and leave_type_key != "comp_off":
            errors.append(
                f"❌ Insufficient {lt['name']} balance. Available: {available}, requested: {total_counted}"
            )
        elif available < total_counted and leave_type_key == "comp_off":
            errors.append(
                f"❌ Insufficient Comp-off balance. Available: {available}, requested: {total_counted}"
            )

    # Date in past (allow for SL within last 2 days)
    today = now_ist().date()
    if from_d < today:
        if leave_type_key == "sick_leave":
            days_late = (today - from_d).days
            if days_late > 2:
                warnings.append(f"⚠️ Backdated Sick Leave ({days_late} days ago). Manager approval may require proof.")
        else:
            errors.append(f"❌ Cannot apply leave for past dates ({from_date_str})")

    # Overlapping pending/approved leave check
    overlap = await leave_requests_col.find_one({
        "user_id": user_id,
        "status": {"$in": ["pending_l1", "pending_final", "approved_l1", "approved"]},
        "$or": [
            {"from_date": {"$lte": to_date_str}, "to_date": {"$gte": from_date_str}},
        ],
    }, {"_id": 0, "id": 1})
    if overlap:
        errors.append(f"❌ Overlapping leave request exists (ID: {overlap['id'][:8]})")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "days_breakdown": {
            "is_sandwich": days_breakdown["is_sandwich"],
            "counted_dates": [d.isoformat() for d in days_breakdown["counted_dates"]],
            "working_dates": [d.isoformat() for d in days_breakdown["working_dates"]],
            "weekend_included": days_breakdown["weekend_included"],
            "original_dates": [d.isoformat() for d in days_breakdown["original_dates"]],
        },
        "total_days": total_counted,
        "working_days": len(working),
        "leave_type_name": lt["name"],
    }


# ────────────────────────────────────────────────────────
# Balance deduction on approval
# ────────────────────────────────────────────────────────
async def deduct_leave_balance(
    user_id: str, leave_type_key: str, year: int, days: float,
    request_id: str, reason: str, triggered_by: str,
    month_key: Optional[str] = None,
):
    """Deduct from balance + update monthly_used + audit log."""
    bal = await leave_balances_col.find_one(
        {"user_id": user_id, "leave_type_key": leave_type_key, "year": year},
        {"_id": 0},
    )
    if not bal:
        # Create on-the-fly for LWP
        bal = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "year": year,
            "leave_type_key": leave_type_key,
            "opening_balance": 0,
            "earned": 0,
            "used": 0,
            "available": 0,
            "monthly_used": {},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await leave_balances_col.insert_one(bal)

    before = float(bal.get("available", 0))
    after = before - days  # can go negative for LWP

    monthly_used = bal.get("monthly_used", {}) or {}
    if month_key:
        monthly_used[month_key] = monthly_used.get(month_key, 0) + days

    await leave_balances_col.update_one(
        {"id": bal["id"]},
        {
            "$set": {
                "available": after,
                "monthly_used": monthly_used,
                "updated_at": datetime.now(timezone.utc),
            },
            "$inc": {"used": days},
        },
    )

    # Audit
    await leave_balance_history_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "date": datetime.now(timezone.utc),
        "leave_type_key": leave_type_key,
        "change_type": "approved" if leave_type_key != "lwp" else "lwp",
        "delta": -days,
        "balance_before": before,
        "balance_after": after,
        "reason": reason,
        "request_id": request_id,
        "triggered_by": triggered_by,
        "created_at": datetime.now(timezone.utc),
    })


# ────────────────────────────────────────────────────────
# Approver resolution
# ────────────────────────────────────────────────────────
async def resolve_approvers(user: dict) -> dict:
    """Determine L1 manager + Final approver for a user based on settings.

    Returns: {l1_manager_id, l1_manager_name, final_approver_id, final_approver_name}
    """
    settings = await get_settings()
    out = {
        "l1_manager_id": None,
        "l1_manager_name": None,
        "final_approver_id": None,
        "final_approver_name": None,
    }

    # L1 = direct reports_to
    if user.get("reports_to"):
        mgr = await users_col.find_one({"id": user["reports_to"]}, {"_id": 0, "id": 1, "name": 1, "email": 1})
        if mgr:
            out["l1_manager_id"] = mgr["id"]
            out["l1_manager_name"] = mgr.get("name")

    # Final approver
    logic = settings.get("final_approver_logic", "specific_user")
    if logic == "by_department":
        dept_map = settings.get("final_approvers_by_department", {})
        approver_id = dept_map.get(user.get("department"))
    else:
        approver_id = settings.get("final_approver_user_id")

    # Fallback: admin_owner
    if not approver_id:
        admin = await users_col.find_one(
            {"rbac_role": "admin_owner", "status": "active"},
            {"_id": 0, "id": 1, "name": 1},
        )
        if admin:
            approver_id = admin["id"]
            out["final_approver_name"] = admin.get("name")
    else:
        approver = await users_col.find_one({"id": approver_id}, {"_id": 0, "id": 1, "name": 1})
        if approver:
            out["final_approver_name"] = approver.get("name")

    out["final_approver_id"] = approver_id

    # If no L1 (user is at top), final is L1
    if not out["l1_manager_id"] and out["final_approver_id"]:
        out["l1_manager_id"] = out["final_approver_id"]
        out["l1_manager_name"] = out["final_approver_name"]

    return out


# ────────────────────────────────────────────────────────
# LWP auto-marking
# ────────────────────────────────────────────────────────
async def mark_lwp_for_date(user_id: str, d: date, reason: str = "no_approval") -> bool:
    """Idempotent — creates an LWP record + deducts. Returns True if newly applied."""
    date_str = d.strftime("%Y-%m-%d")
    existing = await lwp_records_col.find_one(
        {"user_id": user_id, "date": date_str}, {"_id": 0, "id": 1}
    )
    if existing:
        return False

    await lwp_records_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "date": date_str,
        "reason": reason,
        "regularization_status": "pending",
        "created_at": datetime.now(timezone.utc),
    })

    # Deduct as LWP (negative balance allowed)
    await deduct_leave_balance(
        user_id=user_id,
        leave_type_key="lwp",
        year=d.year,
        days=1,
        request_id=f"auto-lwp-{date_str}",
        reason=f"Auto-LWP for unapproved absence on {date_str}",
        triggered_by="system",
        month_key=date_str[:7],
    )

    # Notify
    settings = await get_settings()
    grace = int(settings.get("regularization_grace_days", 3))
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": "Marked as LWP",
        "message": f"{date_str} marked as Loss of Pay (LWP) due to no approved leave. "
                   f"You can regularize within {grace} days with a valid reason.",
        "type": "lwp_marked",
        "read": False,
        "created_at": datetime.now(timezone.utc),
    })
    return True


async def has_approved_leave_on(user_id: str, d: date) -> bool:
    """Check if user has any approved leave covering date d."""
    date_str = d.strftime("%Y-%m-%d")
    found = await leave_requests_col.find_one({
        "user_id": user_id,
        "status": "approved",
        "from_date": {"$lte": date_str},
        "to_date": {"$gte": date_str},
    }, {"_id": 0, "id": 1})
    return found is not None


async def has_punched_on(user_id: str, d: date) -> bool:
    """Check if user has an attendance log on date d."""
    date_str = d.strftime("%Y-%m-%d")
    found = await attendance_logs_col.find_one(
        {"user_id": user_id, "date": date_str}, {"_id": 0, "id": 1}
    )
    return found is not None
