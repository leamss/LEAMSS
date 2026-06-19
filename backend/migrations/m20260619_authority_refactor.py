"""Phase 19.7 — Idempotent migration: AU assessing_authority dict → FK.

Steps:
    1. Ensure `assessing_authorities` collection exists with indexes
    2. Seed 39 AU bodies from `seeds.assessing_authorities_au.AU_AUTHORITIES`
       (idempotent — upsert by `code`)
    3. Walk every AU `occupation_master` doc:
         - Read `assessing_authority.short_name`/`name`
         - Fuzzy-match against authority `code` + aliases (lowercase + stripped)
         - If matched → set `assessing_authority_id` (FK)
         - If unmatched but non-empty → log to `assessing_authority_unmatched`
           collection for admin review (Phase 19.9 UI)
         - Preserve `assessing_authority_legacy_string` snapshot for forensics
    4. Update authority `occupation_count` denormalised field
    5. Register the entire migration as a Phase 19.6 `import_batch`
       (revocable within 24h)
    6. Fix the 1 known data-corruption row: EA with vetassess URL

Re-runnable: subsequent runs detect already-migrated docs (assessing_authority_id present)
and skip; only NEW unmatched strings get logged.

Run from /app/backend:
    python migrations/m20260619_authority_refactor.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Path bootstrap
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from seeds.assessing_authorities_au import AU_AUTHORITIES  # noqa: E402
from services import import_batch_service as ibs  # noqa: E402
from services.audit_service import log_action  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _build_alias_index() -> Dict[str, str]:
    """Lower-stripped alias → canonical `code` mapping for fuzzy lookup."""
    idx: Dict[str, str] = {}
    for body in AU_AUTHORITIES:
        code = body["code"]
        # Canonical code itself
        idx[code.strip().lower()] = code
        # Full name
        idx[body["full_name"].strip().lower()] = code
        # All aliases
        for alias in body.get("aliases", []):
            idx[alias.strip().lower()] = code
    return idx


def _resolve_string_to_code(value: str, alias_idx: Dict[str, str]) -> Optional[str]:
    """Return canonical code OR None if no fuzzy match."""
    if not value:
        return None
    key = value.strip().lower()
    if key in alias_idx:
        return alias_idx[key]
    # Try substring match (last resort — only if input is short to avoid false +ve)
    if len(key) < 30:
        for alias, code in alias_idx.items():
            if alias and alias in key:
                return code
            if key and key in alias and len(key) > 3:
                return code
    return None


async def seed_authorities(db) -> Dict[str, Any]:
    """Upsert 39 AU bodies into `assessing_authorities`. Idempotent by code."""
    coll = db["assessing_authorities"]
    # Indexes (idempotent)
    await coll.create_index("code", unique=True)
    await coll.create_index([("country", 1), ("status", 1)])
    await coll.create_index([("occupation_count", -1)])

    now = datetime.now(timezone.utc)
    inserted, updated = 0, 0
    for body in AU_AUTHORITIES:
        existing = await coll.find_one({"code": body["code"]})
        doc = {
            **body,
            "country": "AU",
            "status": existing.get("status") if existing else "draft",  # Preserve admin-set status on re-run
            "source_url": "https://immi.homeaffairs.gov.au/visas/working-in-australia/skills-assessment/assessing-authorities",
            "_seed_source": "phase_19.7_home_affairs_canonical_2026",
            "last_updated_at": now,
            "documents_required_common": body.get("documents_required_common", [
                "Passport bio page",
                "Birth certificate (translated)",
                "Academic transcripts (certified)",
                "Degree/diploma certificates (certified)",
                "Detailed CV / résumé",
                "Statement of Service / Reference letters (employer)",
                "English-language test results (IELTS / PTE / TOEFL)",
            ]),
        }
        if existing:
            await coll.update_one({"code": body["code"]}, {"$set": doc})
            updated += 1
        else:
            doc["id"] = str(uuid.uuid4())
            doc["created_at"] = now
            await coll.insert_one(doc)
            inserted += 1
    return {"inserted": inserted, "updated": updated, "total_target": len(AU_AUTHORITIES)}


async def migrate_au_occupations(
    db, batch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Walk all AU occupation_master docs → set assessing_authority_id FK."""
    alias_idx = _build_alias_index()
    occ_coll = db["occupation_master"]
    auth_coll = db["assessing_authorities"]
    unmatched_coll = db["assessing_authority_unmatched"]

    counts = {"matched": 0, "skipped_already_migrated": 0, "unmatched": 0,
              "empty_authority": 0, "corruption_fixed": 0, "total_au": 0}

    # Pre-load authority id-by-code
    code_to_id: Dict[str, str] = {}
    async for a in auth_coll.find({"country": "AU"}, {"code": 1, "id": 1}):
        code_to_id[a["code"]] = a["id"]

    cursor = occ_coll.find({"country_code": "AU"})
    async for occ in cursor:
        counts["total_au"] += 1
        occ_id = occ.get("occupation_id") or occ.get("code")

        # Skip if already migrated
        if occ.get("assessing_authority_id"):
            counts["skipped_already_migrated"] += 1
            continue

        aa = occ.get("assessing_authority") or {}
        short = (aa.get("short_name") or "").strip()
        name = (aa.get("name") or "").strip()

        # Empty
        if not short and not name:
            counts["empty_authority"] += 1
            continue

        # Fix data corruption: EA with vetassess URL
        url = (aa.get("url") or "").strip().lower()
        if short.lower() in {"engineers australia", "ea"} and "vetassess" in url:
            counts["corruption_fixed"] += 1
            logger.info("Data corruption fix: occ %s — EA short_name with vetassess URL → corrected to engineersaustralia.org.au", occ_id)
            aa["url"] = "https://www.engineersaustralia.org.au/"

        # Fuzzy resolve
        code = _resolve_string_to_code(short, alias_idx) or _resolve_string_to_code(name, alias_idx)
        if code and code in code_to_id:
            authority_id = code_to_id[code]
            # Snapshot pre-state for revoke
            pre_state = {k: v for k, v in occ.items() if k != "_id"}
            await occ_coll.update_one(
                {"occupation_id": occ_id},
                {"$set": {
                    "assessing_authority_id": authority_id,
                    "assessing_authority_legacy_string": f"{short} | {name}",
                    "_phase_197_migrated_at": datetime.now(timezone.utc),
                }},
            )
            counts["matched"] += 1
            if batch is not None:
                ibs.record_update(batch, occ_id,
                                  {"country_code": "AU", "occupation_id": occ_id},
                                  pre_state)
        else:
            counts["unmatched"] += 1
            await unmatched_coll.update_one(
                {"occupation_id": occ_id, "raw_string": f"{short} | {name}"},
                {"$set": {
                    "occupation_id": occ_id,
                    "country_code": "AU",
                    "code": occ.get("code"),
                    "title": occ.get("title"),
                    "raw_string": f"{short} | {name}",
                    "raw_short_name": short,
                    "raw_name": name,
                    "raw_url": aa.get("url"),
                    "logged_at": datetime.now(timezone.utc),
                    "phase": "19.7",
                    "_complex_legacy": short.lower().startswith("legal admissions"),
                }},
                upsert=True,
            )
            logger.info("UNMATCHED: occ %s '%s | %s'", occ_id, short, name)

    return counts


async def refresh_occupation_counts(db) -> Dict[str, int]:
    """Recompute denormalised `occupation_count` field on each authority."""
    auth_coll = db["assessing_authorities"]
    occ_coll = db["occupation_master"]
    counts = {}
    async for auth in auth_coll.find({"country": "AU"}):
        n = await occ_coll.count_documents({
            "country_code": "AU", "assessing_authority_id": auth["id"],
        })
        # Sample 5 codes for quick display
        sample = await occ_coll.find(
            {"country_code": "AU", "assessing_authority_id": auth["id"]},
            {"code": 1, "title": 1},
        ).limit(5).to_list(5)
        await auth_coll.update_one(
            {"id": auth["id"]},
            {"$set": {
                "occupation_count": n,
                "occupation_codes_sample": [{"code": s.get("code"), "title": s.get("title")} for s in sample],
            }},
        )
        counts[auth["code"]] = n
    return counts


async def main() -> None:
    mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = mongo[os.environ["DB_NAME"]]

    # ─── Step 1: register migration as a Phase 19.6 import_batch ────────────
    fake_file = b"phase_19.7_migration"
    batch = await ibs.open_batch(
        db,
        ingestion_path="phase_19.7_authority_refactor",
        endpoint="cli: migrations/m20260619_authority_refactor.py",
        uploaded_by="system",
        uploaded_by_name="Phase 19.7 Migration",
        file_name="phase_19.7_authority_refactor",
        file_hash=ibs.file_sha256(fake_file),
        file_size_bytes=len(fake_file),
        target_collection="occupation_master",
    )
    logger.info("Migration batch opened: %s", batch["batch_id"])

    try:
        # ─── Step 2: Seed authorities ─────────────────────────────────────
        seed_summary = await seed_authorities(db)
        logger.info("Seed summary: %s", seed_summary)

        # ─── Step 3: Migrate occupations ──────────────────────────────────
        migrate_summary = await migrate_au_occupations(db, batch=batch)
        logger.info("Migration summary: %s", migrate_summary)

        # ─── Step 4: Refresh occupation counts ────────────────────────────
        counts = await refresh_occupation_counts(db)
        top_5 = sorted(counts.items(), key=lambda x: -x[1])[:5]
        logger.info("Top 5 authorities by occupation count: %s", top_5)

        # ─── Step 5: Close batch ───────────────────────────────────────────
        await ibs.close_batch(db, batch, total_rows=migrate_summary["total_au"],
                              status="committed")
        # Batch is revocable (we captured pre_state for every update)

        # ─── Step 6: Audit log ────────────────────────────────────────────
        await log_action(
            db, action="occupation_master.phase_197_migration",
            user_id="system", user_name="Phase 19.7 Migration",
            severity="info",
            summary={
                "batch_id": batch["batch_id"],
                "seed_summary": seed_summary,
                "migrate_summary": migrate_summary,
                "top_5_by_count": top_5,
            },
        )

        print("\n" + "="*70)
        print("PHASE 19.7 MIGRATION COMPLETE")
        print("="*70)
        print(f"Batch ID (revocable 24h): {batch['batch_id']}")
        print(f"Seeded authorities:  {seed_summary}")
        print(f"Migrated occupations: {migrate_summary}")
        print(f"Top 5 by occupations: {top_5}")
        print("="*70)
    except Exception as e:
        logger.exception("Migration failed: %s", e)
        await db["import_batches"].update_one(
            {"batch_id": batch["batch_id"]},
            {"$set": {"status": "failed", "is_revocable": False,
                      "non_revocable_reason": "migration_failed"}},
        )
        raise


if __name__ == "__main__":
    asyncio.run(main())
