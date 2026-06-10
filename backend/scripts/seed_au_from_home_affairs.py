"""One-time seeder: create base AU occupation_master records from Home Affairs
Skilled Occupation List (live scrape). Idempotent — only inserts codes missing
from DB. After this, home_affairs.py re-run enriches the same records (because
they already exist with country_code='AU').

Run from /app/backend:
    python scripts/seed_au_from_home_affairs.py
"""
from __future__ import annotations
import asyncio
import os
import sys
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from motor.motor_asyncio import AsyncIOMotorClient
from core.scrapers.home_affairs import fetch_raw_records, normalize_record


async def main() -> None:
    mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = mongo[os.environ["DB_NAME"]]
    coll = db["occupation_master"]

    print("→ Fetching Home Affairs live data ...")
    raw = fetch_raw_records()
    print(f"  fetched {len(raw)} raw records")

    normalized = [normalize_record(r) for r in raw]
    # dedupe by code, prefer entries with title
    by_code: dict[str, dict] = {}
    for n in normalized:
        c = n.get("code")
        if not c:
            continue
        if c in by_code and not n.get("title"):
            continue
        by_code[c] = n
    print(f"  unique codes: {len(by_code)}")

    # Existing
    existing = {d["code"] async for d in coll.find({"country_code": "AU"}, {"code": 1})}
    print(f"  already in DB: {len(existing)}")

    to_insert = []
    now = datetime.now(timezone.utc).isoformat()
    for code, n in by_code.items():
        if code in existing:
            continue
        # Derive 4-digit unit-group + skill_level (4-digit code = unit group, 1st digit ≈ major)
        doc = {
            "country_code": "AU",
            "code": code,
            "title": n.get("title") or "",
            "classification_version": n.get("classification_version") or "ANZSCO 2013",
            "classification_dual_code": n.get("classification_dual_code") or {},
            "anzsco_ref_url": n.get("anzsco_ref_url") or "",
            "visa_pathways": n.get("visa_pathways") or {},
            "pathway_list": n.get("pathway_list") or "",
            "assessing_authority": n.get("assessing_authority") or {},
            "status": "verified",  # Sourced from official Home Affairs gazette
            "verification": {
                "source": "home_affairs_skilled_occupation_list",
                "auto_verified_at": now,
                "auto_verified_by": "seed_au_from_home_affairs.py",
                "method": "Home Affairs live scrape — official Australian Government source",
            },
            "created_at": now,
            "updated_at": now,
            "last_scraped_at": now,
            "last_scraped_by": "home_affairs_skilled_occupation_list",
        }
        # Derive a default 4-digit parent code (anzsco_4digit_code) for breadcrumb
        if len(code) == 6 and code.isdigit():
            doc["anzsco_4digit_code"] = code[:4]
            doc["anzsco_major_group_code"] = code[0]
        to_insert.append(doc)

    print(f"  to insert: {len(to_insert)}")
    if not to_insert:
        print("✔ Nothing to insert; DB already in sync")
        return

    # Use batched insert_many for speed
    batch = 500
    for i in range(0, len(to_insert), batch):
        chunk = to_insert[i : i + batch]
        await coll.insert_many(chunk, ordered=False)
        print(f"  inserted {min(i + batch, len(to_insert))}/{len(to_insert)}")

    total = await coll.count_documents({"country_code": "AU"})
    verified = await coll.count_documents({"country_code": "AU", "status": "verified"})
    print(f"✔ Done. AU total={total} · verified={verified}")


if __name__ == "__main__":
    asyncio.run(main())
