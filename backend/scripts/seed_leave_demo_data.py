"""Phase 21 Slice 3 Backlog B.2 — Leave demo seed.

Inserts ~24 approved leave_requests across ~8 active employees and 3 leave types
(sick / casual / earned) over the last 90 days so that
/portal/hr-analytics' "Leave Patterns" Recharts BarChart renders visible bars
instead of the empty-state placeholder.

Design:
- Idempotent — uses deterministic IDs (`seed-leave-{employee_id}-{type}-{day_offset}`).
  Safe to run multiple times; rerun just upserts.
- Production-safe — refuses to run when ENV=production unless `--confirm` is passed.

Run:
    cd /app/backend
    python scripts/seed_leave_demo_data.py
    # or, on prod with explicit override:
    python scripts/seed_leave_demo_data.py --confirm
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Make backend root importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from core.database import db  # noqa: E402

DEFAULT_LEAVE_TYPES = [
    {"key": "sick", "name": "Sick Leave", "max_days_per_year": 12, "is_paid": True, "is_active": True, "sort_order": 1},
    {"key": "casual", "name": "Casual Leave", "max_days_per_year": 10, "is_paid": True, "is_active": True, "sort_order": 2},
    {"key": "earned", "name": "Earned Leave", "max_days_per_year": 21, "is_paid": True, "is_active": True, "sort_order": 3},
]

# Spread over last 90 days; each tuple = (employee_index, leave_type_key, day_offset_from_today, total_days)
DEMO_PATTERN = [
    (0, "sick", -5, 1), (0, "casual", -32, 2),
    (1, "sick", -12, 1), (1, "earned", -45, 3),
    (2, "casual", -18, 1), (2, "earned", -60, 5),
    (3, "sick", -8, 2), (3, "casual", -25, 1), (3, "earned", -50, 4),
    (4, "sick", -20, 1), (4, "earned", -70, 3),
    (5, "casual", -6, 1), (5, "sick", -40, 2),
    (6, "earned", -15, 2), (6, "casual", -55, 1),
    (7, "sick", -3, 1), (7, "casual", -28, 2), (7, "earned", -65, 4),
    (0, "earned", -75, 2),
    (1, "casual", -10, 1),
    (2, "sick", -2, 1),
    (4, "casual", -38, 2),
    (6, "sick", -22, 1),
    (5, "earned", -80, 3),
]


def _is_prod() -> bool:
    env = (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "").lower()
    return env in ("production", "prod")


async def _ensure_leave_types() -> None:
    """Upsert the 3 base leave types if missing."""
    existing = {t["key"] async for t in db["leave_types"].find({}, {"_id": 0, "key": 1})}
    for lt in DEFAULT_LEAVE_TYPES:
        if lt["key"] not in existing:
            await db["leave_types"].insert_one({**lt, "created_at": datetime.now(timezone.utc)})
            print(f"  + Inserted leave_type '{lt['key']}'")
        else:
            print(f"  · leave_type '{lt['key']}' already exists — skipping")


async def _pick_employees(limit: int) -> list[dict]:
    """Pick up to `limit` active employees (any with an id + name)."""
    employees: list[dict] = []
    async for u in db["users"].find(
        {"id": {"$exists": True}, "name": {"$exists": True}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "employee_id": 1, "department": 1, "designation": 1, "rbac_role": 1, "role": 1},
    ).limit(limit):
        employees.append(u)
    return employees


async def _upsert_leave(emp: dict, type_key: str, day_offset: int, total_days: int) -> bool:
    """Returns True if newly inserted, False if already existed."""
    now = datetime.now(timezone.utc)
    from_dt = (now + timedelta(days=day_offset)).date()
    to_dt = (from_dt + timedelta(days=total_days - 1))
    leave_id = f"seed-leave-{emp['id']}-{type_key}-{day_offset}"

    type_doc = await db["leave_types"].find_one({"key": type_key}, {"_id": 0, "name": 1})
    type_name = (type_doc or {}).get("name") or type_key.title()

    existing = await db["leave_requests"].find_one({"id": leave_id}, {"_id": 0, "id": 1})
    payload = {
        "id": leave_id,
        "user_id": emp["id"],
        "user_name": emp.get("name"),
        "user_email": emp.get("email"),
        "user_employee_id": emp.get("employee_id"),
        "department": emp.get("department") or "operations",
        "designation": emp.get("designation"),
        "leave_type_key": type_key,
        "leave_type_name": type_name,
        "from_date": from_dt.isoformat(),
        "to_date": to_dt.isoformat(),
        "total_days": total_days,
        "working_days": total_days,
        "num_days": total_days,  # HR Analytics leave-patterns aggregates by this exact field name
        "is_sandwich": False,
        "weekend_included": False,
        "counted_dates": [(from_dt + timedelta(days=i)).isoformat() for i in range(total_days)],
        "reason": f"Demo seed — {type_name.lower()} leave",
        "handover_to_user_id": None,
        "contact_during_leave": None,
        "proof_url": None,
        "manager_id": None,
        "manager_name": None,
        "final_approver_id": None,
        "final_approver_name": None,
        "status": "approved",  # critical: HR analytics aggregates only approved
        "warnings": [],
        "applied_at": now + timedelta(days=day_offset - 2),
        "approved_at": now + timedelta(days=day_offset - 1),
        "created_at": now + timedelta(days=day_offset - 2),
        "_seed_source": "seed_leave_demo_data.py",
    }
    await db["leave_requests"].update_one({"id": leave_id}, {"$set": payload}, upsert=True)
    return existing is None


async def main(force_prod: bool) -> int:
    if _is_prod() and not force_prod:
        print("[seed_leave_demo_data] ENV=production detected. Refusing to seed without --confirm.")
        return 2

    print("[seed_leave_demo_data] Ensuring leave_types exist…")
    await _ensure_leave_types()

    print("[seed_leave_demo_data] Picking employees…")
    employees = await _pick_employees(8)
    if not employees:
        print("  ! No employees found in users collection. Aborting (run user seed first).")
        return 1
    print(f"  · Picked {len(employees)} employees: {[e.get('name') for e in employees]}")

    inserted = 0
    skipped = 0
    for emp_idx, type_key, day_offset, total_days in DEMO_PATTERN:
        if emp_idx >= len(employees):
            continue  # gracefully skip patterns beyond pool size
        was_new = await _upsert_leave(employees[emp_idx], type_key, day_offset, total_days)
        if was_new:
            inserted += 1
        else:
            skipped += 1

    print(f"\n[seed_leave_demo_data] Done. Inserted {inserted} new approved leave records; {skipped} already existed.")
    total = await db["leave_requests"].count_documents({"status": "approved", "_seed_source": "seed_leave_demo_data.py"})
    print(f"[seed_leave_demo_data] Total seed approved leaves now in DB: {total}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed approved leave records for HR Analytics demo.")
    parser.add_argument("--confirm", action="store_true", help="Override production-safety guard.")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.confirm)))
