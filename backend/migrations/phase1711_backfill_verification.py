"""Phase 17.1.1 backfill — populate `verification.source` + `last_scraped_at`
on existing CA + NZ `occupation_master` records that lack them. Idempotent.

Called from server.py startup. Safe to re-run."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict

BACKFILL_DEFAULTS = {
    "CA": {
        "verification.source": "StatCan NOC 2021",
        "verification.auto_verified_by": "phase1711_backfill",
        "verification.method": "Phase 17.1.1 startup backfill — original seed lacked verification stamp",
        "last_scraped_by": "ca_initial_seed",
    },
    "NZ": {
        "verification.source": "INZ National Occupation List",
        "verification.auto_verified_by": "phase1711_backfill",
        "verification.method": "Phase 17.1.1 startup backfill — original seed lacked verification stamp",
        "last_scraped_by": "nz_initial_seed",
    },
}


async def run_backfill(db) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    result: Dict[str, Any] = {}
    coll = db["occupation_master"]
    for country, defaults in BACKFILL_DEFAULTS.items():
        # Match records that LACK either verification.source OR last_scraped_at
        q = {
            "country_code": country,
            "$or": [
                {"verification.source": {"$exists": False}},
                {"verification.source": None},
                {"verification.source": ""},
                {"last_scraped_at": {"$exists": False}},
            ],
        }
        n_missing = await coll.count_documents(q)
        if n_missing == 0:
            result[country] = {"backfilled": 0, "status": "already_clean"}
            continue
        # Build $set patch — use auto_verified_at = created_at OR now (fall back)
        patch = {**defaults, "verification.auto_verified_at": now,
                 "last_scraped_at": now, "updated_at": now}
        upd = await coll.update_many(q, {"$set": patch})
        result[country] = {"backfilled": int(upd.modified_count), "status": "done"}
    return result
