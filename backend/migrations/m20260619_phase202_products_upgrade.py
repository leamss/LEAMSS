"""Phase 20.2 — Products Master upgrade migration.

Adds new fields to existing products + soft-archives TEST_ rows.

Idempotent. Re-runnable. Backup snapshot saved BEFORE migration.

Run: cd /app/backend && python3 migrations/m20260619_phase202_products_upgrade.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient

# Load .env
env_path = Path("/app/backend/.env")
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


BACKUP_DIR = Path("/app/memory/snapshots")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

VALID_CATEGORIES = {
    "skilled_migration", "pr", "work", "study",
    "tourist", "visitor", "investment", "business",
    "dependent", "parent", "child", "exam_voucher",
    "coaching", "service_addon", "uncategorized",
    # legacy/back-compat
    "immigration", "visa", "test",
}

LEGACY_CATEGORY_MAP = {
    "immigration": "pr",  # most legacy "immigration" products are PR pathways
    "visa": "uncategorized",
    "test": "uncategorized",
}

NEW_FIELD_DEFAULTS = {
    "is_pre_assessment": False,
    "pre_assessment_fee_inr": None,
    "pre_assessment_fee_currency": "INR",
    "workflow_id": None,
    "workflow_steps_count": 0,
    "visa_subclass": None,
    "assessing_body_code": None,
    "commissions_v2": None,
    "archived_at": None,
    "archived_by": None,
    "archived_reason": None,
}


async def snapshot_products(db) -> Path:
    products = await db["products"].find({}, {"_id": 0}).to_list(1000)
    # Convert datetimes for JSON
    for p in products:
        for k, v in list(p.items()):
            if isinstance(v, datetime):
                p[k] = v.isoformat()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = BACKUP_DIR / f"pre_phase202_products_{ts}.json"
    payload = json.dumps(products, indent=2, default=str)
    out_path.write_text(payload)
    md5 = hashlib.md5(payload.encode()).hexdigest()
    print(f"Snapshot: {out_path} · {len(products)} products · md5={md5}")
    return out_path


async def add_new_fields(db) -> dict:
    """Add new Phase 20.2 fields to every product. Idempotent."""
    count = 0
    skipped = 0
    async for p in db["products"].find({}, {"id": 1, "name": 1, "category": 1}):
        sets = {}
        for k, v in NEW_FIELD_DEFAULTS.items():
            if k not in p:
                sets[k] = v
        # Migrate legacy category if not already in valid enum
        cur_cat = p.get("category") or "uncategorized"
        if cur_cat in LEGACY_CATEGORY_MAP and "_category_v2" not in p:
            sets["_category_v2"] = LEGACY_CATEGORY_MAP[cur_cat]
            sets["_category_v1"] = cur_cat  # preserve original
        if sets:
            await db["products"].update_one({"id": p["id"]}, {"$set": sets})
            count += 1
        else:
            skipped += 1
    return {"upgraded": count, "skipped": skipped}


async def soft_archive_test_products(db) -> dict:
    """Soft-archive any product with 'TEST_' in name or category=='test'."""
    test_query = {
        "$or": [
            {"name": {"$regex": "TEST_", "$options": "i"}},
            {"name": {"$regex": "^Test", "$options": "i"}},
            {"category": "test"},
        ],
        "archived_at": None,
    }
    cursor = db["products"].find(test_query, {"id": 1, "name": 1})
    targets = [(p["id"], p["name"]) async for p in cursor]
    now = datetime.now(timezone.utc)
    for pid, _ in targets:
        await db["products"].update_one(
            {"id": pid},
            {"$set": {
                "archived_at": now,
                "archived_by": "system_migration",
                "archived_by_email": "admin@leamss.com",
                "archived_reason": "Phase 20.2 audit cleanup",
            }},
        )
    return {"archived_count": len(targets), "names": [n for _, n in targets]}


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print("=== Phase 20.2 Products Upgrade Migration ===")
    backup_path = await snapshot_products(db)

    print("\n[1/2] Adding new fields…")
    field_result = await add_new_fields(db)
    print(f"  upgraded: {field_result['upgraded']} · already-current: {field_result['skipped']}")

    print("\n[2/2] Soft-archiving TEST_ products…")
    archive_result = await soft_archive_test_products(db)
    print(f"  archived: {archive_result['archived_count']}")
    for n in archive_result["names"]:
        print(f"    - {n}")

    # Final tally
    total = await db["products"].count_documents({})
    archived = await db["products"].count_documents({"archived_at": {"$ne": None}})
    active = total - archived
    print(f"\n=== FINAL ===")
    print(f"  Total products: {total}")
    print(f"  Active        : {active}")
    print(f"  Archived      : {archived}")
    print(f"  Backup        : {backup_path}")

    client.close()
    return {"backup_path": str(backup_path), **field_result, **archive_result}


if __name__ == "__main__":
    asyncio.run(main())
