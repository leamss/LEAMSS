"""Phase 21 Slice 4 Sub-Slice C — Past-SLA demo seed.

Inserts 2 backdated support_tickets with `sla_target_at` in the past so the
TicketsHub UI's red "Past SLA" highlight + `stats.past_sla > 0` KPI tile
actually render on the live preview.

Idempotent — uses deterministic IDs (`seed-past-sla-{i}`). Safe to rerun.
Production-safe — refuses to run when ENV=production unless `--confirm`.

Run:
    cd /app/backend
    python scripts/seed_past_sla_demo.py
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from core.database import db  # noqa: E402

DEMO_TICKETS = [
    {
        "_seed_idx": 1,
        "title": "[DEMO past-SLA] Laptop stuck on Windows update — blocker",
        "description": "Demo seed — backdated 7 days to exercise Past SLA red highlight CSS path.",
        "department": "it",
        "priority": "P0",
        "tags": ["demo", "past-sla"],
        "days_old": 7,
    },
    {
        "_seed_idx": 2,
        "title": "[DEMO past-SLA] Marketing campaign asset stuck in review",
        "description": "Demo seed — backdated 4 days to exercise Past SLA red highlight CSS path.",
        "department": "marketing",
        "priority": "P1",
        "tags": ["demo", "past-sla"],
        "days_old": 4,
    },
]

SLA_HOURS = {"P0": 4, "P1": 8, "P2": 24, "P3": 72}


def _is_prod() -> bool:
    env = (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "").lower()
    return env in ("production", "prod")


async def _pick_admin_user() -> dict | None:
    """Pick the first admin user as raised_by (for realistic audit log)."""
    for role_match in ({"rbac_role": "admin_owner"}, {"role": "admin"}, {}):
        u = await db["users"].find_one(role_match, {"_id": 0, "id": 1, "name": 1, "email": 1})
        if u:
            return u
    return None


async def _next_ticket_number_seed(seed_idx: int) -> str:
    """Stable seeded ticket number — uses deterministic prefix to stay idempotent."""
    return f"TKT-SEED-PSLA-{seed_idx:02d}"


async def _upsert_past_sla_ticket(spec: dict, admin: dict) -> bool:
    now = datetime.now(timezone.utc)
    days_old = spec["days_old"]
    created_at = now - timedelta(days=days_old)
    sla_target_at = created_at + timedelta(hours=SLA_HOURS[spec["priority"]])
    # By construction sla_target_at < now (e.g. created 7d ago + 4h SLA → 6.83d in past)

    seed_id = f"seed-past-sla-{spec['_seed_idx']}"
    ticket_number = await _next_ticket_number_seed(spec["_seed_idx"])

    existing = await db["support_tickets"].find_one({"id": seed_id}, {"_id": 0, "id": 1})

    payload = {
        "id": seed_id,
        "ticket_number": ticket_number,
        "title": spec["title"],
        "description": spec["description"],
        "department": spec["department"],
        "category": None,
        "raised_by_id": admin["id"],
        "raised_by_name": admin.get("name") or "Admin User",
        "priority": spec["priority"],
        "status": "open",  # must be in (open / in_progress / waiting) for past_sla counter
        "assignee_id": None,
        "assignee_name": None,
        "tags": spec["tags"],
        "attachments": [],
        "comments": [],
        "audit_log": [{
            "action": "created",
            "actor_id": admin["id"],
            "actor_name": admin.get("name") or "Admin User",
            "timestamp": created_at.isoformat(),
        }],
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat(),
        "resolved_at": None,
        "sla_target_at": sla_target_at.isoformat(),
        "satisfaction_rating": None,
        "linked_dev_item_id": None,
        "_seed_source": "seed_past_sla_demo.py",
    }
    await db["support_tickets"].update_one({"id": seed_id}, {"$set": payload}, upsert=True)
    return existing is None


async def main(force_prod: bool) -> int:
    if _is_prod() and not force_prod:
        print("[seed_past_sla_demo] ENV=production detected. Refusing to seed without --confirm.")
        return 2

    print("[seed_past_sla_demo] Looking for an admin user to attribute tickets to…")
    admin = await _pick_admin_user()
    if not admin:
        print("  ! No user found. Aborting (need at least 1 user in DB).")
        return 1
    print(f"  · Using: {admin.get('name')} ({admin.get('email')})")

    inserted = 0
    updated = 0
    for spec in DEMO_TICKETS:
        was_new = await _upsert_past_sla_ticket(spec, admin)
        if was_new:
            inserted += 1
            print(f"  + Inserted past-SLA ticket #{spec['_seed_idx']} — {spec['title'][:60]}…")
        else:
            updated += 1
            print(f"  · Refreshed past-SLA ticket #{spec['_seed_idx']} (already existed)")

    total = await db["support_tickets"].count_documents({"_seed_source": "seed_past_sla_demo.py"})
    print(f"\n[seed_past_sla_demo] Done. Inserted {inserted}; refreshed {updated}. Total seed tickets now: {total}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed past-SLA support tickets for mobile demo.")
    parser.add_argument("--confirm", action="store_true", help="Override production-safety guard.")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.confirm)))
