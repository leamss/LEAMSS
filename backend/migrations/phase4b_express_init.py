"""Phase 4B (Part 2) — Express Sales Init Migration.

Idempotent:
  - Creates sales_settings doc with default limits + cap
  - Creates indexes on pre_assessments for express queries

Stage constants are documented but no schema change needed (mongo is schema-less).
"""
from datetime import datetime, timezone
from core.database import db
from core.express_logic import DEFAULT_EXPRESS_SETTINGS

sales_settings_col = db["sales_settings"]
pre_assessments_col = db["pre_assessments"]


async def run_migration() -> dict:
    started_at = datetime.now(timezone.utc)

    # ─── Settings seed ────────────────────────────────────
    seeded = 0
    existing = await sales_settings_col.find_one({"key": "express_sales"}, {"_id": 0, "key": 1})
    if not existing:
        await sales_settings_col.insert_one(dict(DEFAULT_EXPRESS_SETTINGS, created_at=started_at))
        seeded = 1

    # ─── Indexes ──────────────────────────────────────────
    await pre_assessments_col.create_index([("sale_type", 1), ("express_sale_approval_status", 1)])
    await pre_assessments_col.create_index([("created_by_user_id", 1), ("sale_type", 1), ("created_at", -1)])

    return {
        "key": "phase4b_express_init_v1",
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "settings_seeded": seeded,
        "status": "completed",
    }
