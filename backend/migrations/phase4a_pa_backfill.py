"""Phase 4A — Backfill created_by_user_id on existing pre_assessments.

Idempotent: only touches PAs that don't already have the field.
Sets:
  - created_by_user_id = partner_id (the original creator)
  - created_by_role = "partner" (assumes existing PAs were partner-created)
  - created_by_user_type = "external"

For PAs created by admin directly, we look up the admin's user_type as "internal".
"""
import uuid
from datetime import datetime, timezone
from core.database import db, pre_assessments_col, users_col, migrations_col

MIGRATION_KEY = "phase4a_pa_created_by_v1"


async def run_migration() -> dict:
    started_at = datetime.now(timezone.utc)
    backfilled = 0
    skipped = 0

    # Cache user info for performance
    user_role_cache = {}

    async for pa in pre_assessments_col.find(
        {"created_by_user_id": {"$exists": False}},
        {"_id": 0, "id": 1, "partner_id": 1},
    ):
        partner_id = pa.get("partner_id")
        if not partner_id:
            skipped += 1
            continue

        # Lookup creator (role + user_type)
        if partner_id not in user_role_cache:
            u = await users_col.find_one(
                {"id": partner_id},
                {"_id": 0, "role": 1, "user_type": 1},
            )
            user_role_cache[partner_id] = {
                "role": (u or {}).get("role", "partner"),
                "user_type": (u or {}).get("user_type", "external"),
            }
        cached = user_role_cache[partner_id]

        await pre_assessments_col.update_one(
            {"id": pa["id"]},
            {"$set": {
                "created_by_user_id": partner_id,
                "created_by_role": cached["role"],
                "created_by_user_type": cached["user_type"],
            }},
        )
        backfilled += 1

    report = {
        "key": MIGRATION_KEY,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "backfilled": backfilled,
        "skipped": skipped,
        "status": "completed",
    }
    try:
        await migrations_col.insert_one({
            "id": str(uuid.uuid4()),
            **report,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:
        pass
    return report
