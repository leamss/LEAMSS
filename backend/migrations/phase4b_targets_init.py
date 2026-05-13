"""Phase 4B — Targets Init Migration.

Idempotent. Safe on every boot.
  1. Creates indexes on sales_targets + target_templates
  2. Seeds 3 default templates (Starter / Standard / Aggressive)
"""
import uuid
from datetime import datetime, timezone
from core.database import db, migrations_col

MIGRATION_KEY = "phase4b_targets_init_v1"
sales_targets_col = db["sales_targets"]
target_templates_col = db["target_templates"]


DEFAULT_TEMPLATES = [
    {
        "key": "sales_exec_starter_monthly",
        "name": "Sales Executive — Starter Monthly",
        "description": "Entry-level monthly target for new hires (probation / first 90 days)",
        "applicable_roles": ["sales_executive"],
        "period_type": "monthly",
        "revenue": 300000,   # ₹3 Lakh
        "pa_count": 6,
    },
    {
        "key": "sales_exec_standard_monthly",
        "name": "Sales Executive — Standard Monthly",
        "description": "Standard monthly target for trained executives",
        "applicable_roles": ["sales_executive", "sr_sales_executive"],
        "period_type": "monthly",
        "revenue": 500000,   # ₹5 Lakh
        "pa_count": 10,
    },
    {
        "key": "sales_exec_aggressive_monthly",
        "name": "Sales Executive — Aggressive Monthly",
        "description": "High-stretch target for top performers / season pushes",
        "applicable_roles": ["sales_executive", "sr_sales_executive", "sales_manager"],
        "period_type": "monthly",
        "revenue": 800000,   # ₹8 Lakh
        "pa_count": 16,
    },
]


async def run_migration() -> dict:
    started_at = datetime.now(timezone.utc)

    # ─── Indexes ─────────────────────────────────────────────
    # Unique compound: one target per user per period
    # Note: MongoDB partial filter only supports equality/$gt/$lt, not $exists:false
    # so we use deleted_at: null (we store explicit null on creation; soft-delete writes a datetime).
    await sales_targets_col.create_index(
        [
            ("user_id", 1),
            ("period_type", 1),
            ("period_year", 1),
            ("period_month", 1),
            ("period_quarter", 1),
        ],
        unique=True,
        partialFilterExpression={"deleted_at": None},
        name="sales_targets_unique_period",
    )
    await sales_targets_col.create_index([("set_by", 1), ("set_at", -1)])
    await sales_targets_col.create_index([("period_start", 1), ("period_end", 1)])
    await sales_targets_col.create_index([("status", 1), ("period_end", 1)])
    await sales_targets_col.create_index("user_id")

    await target_templates_col.create_index("key", unique=True, sparse=True)
    await target_templates_col.create_index([("is_active", 1), ("period_type", 1)])

    # ─── Seed templates (upsert by key) ──────────────────────
    seeded = 0
    skipped = 0
    for tpl in DEFAULT_TEMPLATES:
        existing = await target_templates_col.find_one({"key": tpl["key"]}, {"_id": 0, "id": 1})
        if existing:
            skipped += 1
            continue
        doc = {
            "id": str(uuid.uuid4()),
            "key": tpl["key"],
            "name": tpl["name"],
            "description": tpl["description"],
            "applicable_roles": tpl["applicable_roles"],
            "period_type": tpl["period_type"],
            "revenue": tpl["revenue"],
            "pa_count": tpl["pa_count"],
            "is_active": True,
            "is_system": True,
            "created_by": "system",
            "created_at": datetime.now(timezone.utc),
        }
        await target_templates_col.insert_one(doc)
        seeded += 1

    report = {
        "key": MIGRATION_KEY,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "templates_seeded": seeded,
        "templates_skipped": skipped,
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
