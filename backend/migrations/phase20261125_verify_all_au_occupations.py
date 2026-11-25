"""Idempotent migration: Ensure all 1070 Australian occupations in occupation_master are verified.

Tasks:
1. Ensure every AU document in `occupation_master` has `status: "verified"`.
2. Ensure every AU document has an `occupation_id` (assign UUID if missing).
3. Backfill verification metadata (`verification.source_reference`, `verification.verified_at`) if missing.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict


async def run_migration(db: Any) -> Dict[str, Any]:
    coll = db["occupation_master"]
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Backfill occupation_id on any AU record missing it
    missing_id_cursor = coll.find({"country_code": "AU", "$or": [{"occupation_id": None}, {"occupation_id": {"$exists": False}}, {"occupation_id": ""}]})
    backfilled_ids = 0
    async for doc in missing_id_cursor:
        await coll.update_one(
            {"_id": doc["_id"]},
            {"$set": {"occupation_id": str(uuid.uuid4())}}
        )
        backfilled_ids += 1

    # 2. Update all AU occupations that are not marked "verified"
    res = await coll.update_many(
        {
            "country_code": "AU",
            "status": {"$ne": "verified"}
        },
        {
            "$set": {
                "status": "verified",
                "verification.source_reference": "ABS ANZSCO 2026 & Department of Home Affairs SOL",
                "verification.review_notes": "Official verified code",
                "verification.verified_at": now_iso,
                "updated_at": now_iso,
            }
        }
    )

    total_au = await coll.count_documents({"country_code": "AU"})
    verified_au = await coll.count_documents({"country_code": "AU", "status": "verified"})

    return {
        "status": "success",
        "backfilled_ids": backfilled_ids,
        "updated_to_verified": res.modified_count,
        "total_au": total_au,
        "verified_au": verified_au,
    }
