"""Phase 17.1.3 — backfill `occupation_id` on AU records.

The Phase 16.7 `seed_au_from_home_affairs.py` script never set the
`occupation_id` field, leaving all 708 AU records without it. The admin Edit
page sends `item.occupation_id` to action endpoints (Generate AI / Verify /
Save Draft / Polish) — when undefined, every action fails with HTTP 404
"Occupation not found".

Convention (matches existing CA records): `au-{code}` slug, lower-case.
Idempotent: skips records that already have a non-empty `occupation_id`.

Wired into server.py startup."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict


async def run_backfill_occupation_id(db) -> Dict[str, Any]:
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc).isoformat()
    patched = 0
    skipped = 0

    cur = coll.find(
        {
            "$or": [
                {"occupation_id": {"$exists": False}},
                {"occupation_id": None},
                {"occupation_id": ""},
            ]
        },
        {"_id": 0, "country_code": 1, "code": 1},
    )
    async for d in cur:
        cc = (d.get("country_code") or "").lower().strip()
        code = (d.get("code") or "").strip()
        if not cc or not code:
            skipped += 1
            continue
        new_oid = f"{cc}-{code}"
        await coll.update_one(
            {"country_code": d["country_code"], "code": d["code"]},
            {"$set": {"occupation_id": new_oid, "updated_at": now}},
        )
        patched += 1

    return {"patched": patched, "skipped": skipped, "status": "ok"}
