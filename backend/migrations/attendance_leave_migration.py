"""Phase 3A — Attendance & Leave Management Migration.

Seeds:
- 1 attendance_settings document (singleton with company policies)
- 7 leave types (CL, SL, EL, Comp-off, LWP, Maternity, Paternity)
- Default holidays for current year (India national holidays)

Backfills:
- leave_balances for every active internal employee (current year)

Creates indexes for fast queries on:
- attendance_logs (user_id + date)
- leave_requests (user_id, status)
- leave_balances (user_id + year)
- holidays (date)

Idempotent — safe on every boot.
"""
import uuid
from datetime import datetime, timezone, date
from core.database import (
    db, users_col,
    attendance_settings_col, attendance_logs_col,
    leave_types_col, leave_balances_col, leave_requests_col,
    holidays_col, late_marks_tracker_col,
    leave_balance_history_col, lwp_records_col,
    attendance_regularizations_col, migrations_col,
)

MIGRATION_KEY = "attendance_leave_phase3a_v1"


# ────────────────────────────────────────────────────────
# Company Policy Defaults
# ────────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "key": "global",
    "office_start_time": "10:00",
    "office_end_time": "19:00",
    "min_work_hours": 9,
    "late_threshold_minutes": 10,  # grace period — punch after 10:10 = late
    "late_marks_for_leave_deduction": 3,
    "enforce_work_hours_compensation": True,
    "enforce_sandwich_leave": True,
    "enforce_monthly_cl_limit": True,
    "monthly_cl_limit": 1,
    "max_consecutive_leave_days": 7,
    "max_long_leaves_per_year": 1,  # long = > 5 days
    "long_leave_threshold_days": 5,
    "auto_mark_lwp_for_unapproved_absence": True,
    "regularization_grace_days": 3,
    "working_days": [0, 1, 2, 3, 4, 5],  # Mon=0 ... Sun=6. Sat included, Sun off
    "weekly_off_days": [6],  # Sunday only
    "final_approver_logic": "specific_user",  # or "by_department"
    "final_approver_user_id": None,  # admin sets via HR settings UI
    "final_approvers_by_department": {},
    "backup_approver_user_id": None,
    "is_system": True,
}


LEAVE_TYPES = [
    {
        "key": "casual_leave",
        "name": "Casual Leave",
        "short_code": "CL",
        "annual_quota": 12,
        "monthly_cap": 1,  # ⭐ company rule
        "max_consecutive": 1,
        "carry_forward": False,
        "carry_forward_cap": 0,
        "requires_proof_after_days": 0,
        "min_notice_days": 0,
        "color": "#3b82f6",
        "applicable_to": ["all"],  # all internal employees
        "is_system": True,
        "sort_order": 1,
    },
    {
        "key": "sick_leave",
        "name": "Sick Leave",
        "short_code": "SL",
        "annual_quota": 12,
        "monthly_cap": 0,  # no cap
        "max_consecutive": 7,
        "carry_forward": False,
        "carry_forward_cap": 0,
        "requires_proof_after_days": 2,
        "min_notice_days": 0,
        "color": "#ef4444",
        "applicable_to": ["all"],
        "is_system": True,
        "sort_order": 2,
    },
    {
        "key": "earned_leave",
        "name": "Earned Leave",
        "short_code": "EL",
        "annual_quota": 24,
        "monthly_cap": 0,
        "max_consecutive": 7,
        "carry_forward": True,
        "carry_forward_cap": 30,
        "requires_proof_after_days": 0,
        "min_notice_days": 7,
        "color": "#10b981",
        "applicable_to": ["all"],
        "is_system": True,
        "sort_order": 3,
    },
    {
        "key": "comp_off",
        "name": "Compensatory Off",
        "short_code": "Comp",
        "annual_quota": 0,  # earned by working on holidays/weekends
        "monthly_cap": 0,
        "max_consecutive": 3,
        "carry_forward": False,
        "carry_forward_cap": 0,
        "requires_proof_after_days": 0,
        "min_notice_days": 0,
        "color": "#a855f7",
        "applicable_to": ["all"],
        "is_system": True,
        "sort_order": 4,
    },
    {
        "key": "lwp",
        "name": "Loss of Pay",
        "short_code": "LWP",
        "annual_quota": 0,  # auto-applied
        "monthly_cap": 0,
        "max_consecutive": 365,
        "carry_forward": False,
        "carry_forward_cap": 0,
        "requires_proof_after_days": 0,
        "min_notice_days": 0,
        "color": "#737373",
        "applicable_to": ["all"],
        "is_system": True,
        "sort_order": 5,
    },
    {
        "key": "maternity_leave",
        "name": "Maternity Leave",
        "short_code": "ML",
        "annual_quota": 180,
        "monthly_cap": 0,
        "max_consecutive": 180,
        "carry_forward": False,
        "carry_forward_cap": 0,
        "requires_proof_after_days": 0,
        "min_notice_days": 14,
        "color": "#ec4899",
        "applicable_to": ["female"],
        "is_system": True,
        "sort_order": 6,
    },
    {
        "key": "paternity_leave",
        "name": "Paternity Leave",
        "short_code": "PL",
        "annual_quota": 5,
        "monthly_cap": 0,
        "max_consecutive": 5,
        "carry_forward": False,
        "carry_forward_cap": 0,
        "requires_proof_after_days": 0,
        "min_notice_days": 7,
        "color": "#06b6d4",
        "applicable_to": ["male"],
        "is_system": True,
        "sort_order": 7,
    },
]


# India national holidays (2026) — admin can edit
DEFAULT_HOLIDAYS_2026 = [
    {"date": "2026-01-01", "name": "New Year's Day", "type": "public"},
    {"date": "2026-01-26", "name": "Republic Day", "type": "public"},
    {"date": "2026-03-03", "name": "Holi", "type": "public"},
    {"date": "2026-04-14", "name": "Ambedkar Jayanti", "type": "public"},
    {"date": "2026-05-01", "name": "Labour Day", "type": "public"},
    {"date": "2026-08-15", "name": "Independence Day", "type": "public"},
    {"date": "2026-10-02", "name": "Gandhi Jayanti", "type": "public"},
    {"date": "2026-10-20", "name": "Diwali", "type": "public"},
    {"date": "2026-12-25", "name": "Christmas", "type": "public"},
]


# ────────────────────────────────────────────────────────
# Seed helpers
# ────────────────────────────────────────────────────────
async def _seed_settings():
    now = datetime.now(timezone.utc)
    existing = await attendance_settings_col.find_one({"key": "global"}, {"_id": 0})
    if existing:
        return {"action": "skipped_existing"}
    doc = {"id": str(uuid.uuid4()), **DEFAULT_SETTINGS, "created_at": now, "updated_at": now}
    await attendance_settings_col.insert_one(doc)
    return {"action": "seeded"}


async def _seed_leave_types():
    seeded, updated = 0, 0
    now = datetime.now(timezone.utc)
    for lt in LEAVE_TYPES:
        existing = await leave_types_col.find_one({"key": lt["key"]}, {"_id": 0})
        if existing:
            await leave_types_col.update_one({"key": lt["key"]}, {"$set": {**lt, "updated_at": now}})
            updated += 1
        else:
            doc = {"id": str(uuid.uuid4()), **lt, "is_active": True, "created_at": now}
            await leave_types_col.insert_one(doc)
            seeded += 1
    return {"seeded": seeded, "updated": updated, "total": len(LEAVE_TYPES)}


async def _seed_holidays():
    seeded = 0
    now = datetime.now(timezone.utc)
    for h in DEFAULT_HOLIDAYS_2026:
        existing = await holidays_col.find_one({"date": h["date"]}, {"_id": 0})
        if not existing:
            await holidays_col.insert_one({
                "id": str(uuid.uuid4()),
                **h,
                "year": int(h["date"][:4]),
                "is_optional": False,
                "applicable_locations": ["all"],
                "created_at": now,
                "created_by": "system",
            })
            seeded += 1
    return {"seeded": seeded, "total": len(DEFAULT_HOLIDAYS_2026)}


async def _backfill_leave_balances():
    """Create yearly leave balance docs for active internal employees."""
    year = datetime.now(timezone.utc).year
    leave_types = []
    async for lt in leave_types_col.find({"is_active": True, "applicable_to": {"$in": ["all"]}}, {"_id": 0}):
        leave_types.append(lt)

    backfilled = 0
    skipped = 0
    async for user in users_col.find(
        {"user_type": "internal", "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "gender": 1}
    ):
        for lt in leave_types:
            # Skip if balance doc already exists
            existing = await leave_balances_col.find_one(
                {"user_id": user["id"], "leave_type_key": lt["key"], "year": year},
                {"_id": 0, "id": 1}
            )
            if existing:
                skipped += 1
                continue
            # LWP / comp_off start at 0 — they're earned/auto
            opening = lt["annual_quota"] if lt["key"] not in ("lwp", "comp_off") else 0
            await leave_balances_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "year": year,
                "leave_type_key": lt["key"],
                "opening_balance": opening,
                "earned": 0,
                "used": 0,
                "carried_forward": 0,
                "available": opening,
                "monthly_used": {},  # {"2026-05": 1} - for monthly cap tracking
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
            backfilled += 1
    return {"backfilled": backfilled, "skipped": skipped}


async def _create_indexes():
    # attendance_settings
    await attendance_settings_col.create_index("key", unique=True, name="att_settings_key_unique")

    # attendance_logs — query by user+date or date-range
    await attendance_logs_col.create_index([("user_id", 1), ("date", -1)], name="att_logs_user_date")
    await attendance_logs_col.create_index("date", name="att_logs_date")
    await attendance_logs_col.create_index([("user_id", 1), ("year_month", 1)], name="att_logs_user_ym")

    # leave_types
    await leave_types_col.create_index("key", unique=True, name="leave_type_key_unique")

    # leave_balances
    await leave_balances_col.create_index(
        [("user_id", 1), ("leave_type_key", 1), ("year", 1)],
        unique=True, name="leave_balance_unique",
    )

    # leave_requests
    await leave_requests_col.create_index([("user_id", 1), ("status", 1)], name="leave_req_user_status")
    await leave_requests_col.create_index([("manager_id", 1), ("status", 1)], name="leave_req_mgr_status")
    await leave_requests_col.create_index([("final_approver_id", 1), ("status", 1)], name="leave_req_final_status")
    await leave_requests_col.create_index("from_date", name="leave_req_from")

    # holidays
    await holidays_col.create_index("date", unique=True, name="holiday_date_unique")
    await holidays_col.create_index("year", name="holiday_year")

    # late_marks_tracker
    await late_marks_tracker_col.create_index(
        [("user_id", 1), ("year_month", 1)],
        unique=True, name="late_marks_user_ym",
    )

    # leave_balance_history
    await leave_balance_history_col.create_index([("user_id", 1), ("date", -1)], name="lbh_user_date")

    # lwp_records
    await lwp_records_col.create_index([("user_id", 1), ("date", -1)], name="lwp_user_date")
    await lwp_records_col.create_index([("user_id", 1), ("date", 1)], unique=True, name="lwp_user_date_unique")

    # attendance_regularizations
    await attendance_regularizations_col.create_index([("user_id", 1), ("status", 1)], name="att_reg_user_status")
    await attendance_regularizations_col.create_index([("manager_id", 1), ("status", 1)], name="att_reg_mgr_status")

    return True


# ────────────────────────────────────────────────────────
# Main entry
# ────────────────────────────────────────────────────────
async def run_migration() -> dict:
    started_at = datetime.now(timezone.utc)
    report = {
        "key": MIGRATION_KEY,
        "started_at": started_at.isoformat(),
        "settings": None,
        "leave_types": None,
        "holidays": None,
        "balances_backfill": None,
        "indexes_created": False,
        "status": "running",
    }
    try:
        report["settings"] = await _seed_settings()
        report["leave_types"] = await _seed_leave_types()
        report["holidays"] = await _seed_holidays()
        await _create_indexes()
        report["indexes_created"] = True
        report["balances_backfill"] = await _backfill_leave_balances()
        report["status"] = "completed"
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        report["status"] = "failed"
        report["error"] = str(e)

    try:
        await migrations_col.insert_one({
            "id": str(uuid.uuid4()),
            **report,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:
        pass

    return report
