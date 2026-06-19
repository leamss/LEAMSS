"""Phase 19.7.1 — CA Data Quality Auto-Fix.

Fixes mislabel/corruption in CA `occupation_master.assessing_authority`:
- 513 records with empty short_name/name/url (but correct body_url=wes.org) → backfill WES
- 1 record (CA 21231 Software engineers and designers) — corrupted with AU "ACS" leak
- 1 record (wes.com URL) — fix to canonical WES URL
- Leaves MCC record untouched (legitimate Canadian medical body)

Registers as Phase 19.6 `import_batch` (24h revocable).
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from motor.motor_asyncio import AsyncIOMotorClient

from services import import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


WES_FIX = {
    "short_name": "WES",
    "name": "World Education Services",
    "url": "https://www.wes.org/ca/",
}


async def main() -> None:
    mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = mongo[os.environ["DB_NAME"]]

    # Open revocable batch
    fake_file = b"phase_19.7.1_ca_data_quality_fix"
    batch = await ibs.open_batch(
        db,
        ingestion_path="phase_19.7.1_ca_authority_fix",
        endpoint="cli: migrations/m20260619_ca_authority_fix.py",
        uploaded_by="system",
        uploaded_by_name="Phase 19.7.1 CA Fix",
        file_name="phase_19.7.1_ca_data_quality_fix",
        file_hash=ibs.file_sha256(fake_file),
        file_size_bytes=len(fake_file),
        target_collection="occupation_master",
    )
    logger.info("Migration batch opened: %s", batch["batch_id"])

    counts = {"empty_backfilled": 0, "acs_corruption_fixed": 0, "wes_com_fixed": 0,
              "mcc_skipped": 0, "no_change": 0, "total_ca": 0}

    cursor = db["occupation_master"].find({"country_code": "CA"})
    async for occ in cursor:
        counts["total_ca"] += 1
        aa = occ.get("assessing_authority") or {}
        occ_id = occ.get("occupation_id") or occ.get("code")
        short = (aa.get("short_name") or "").strip()
        name = (aa.get("name") or "").strip()
        url = (aa.get("url") or "").strip()

        # Skip MCC — legit Canadian body for medical occupations
        if name == "MCC":
            counts["mcc_skipped"] += 1
            continue

        # Determine action
        change_reason = None
        if not short and not name and not url:
            change_reason = "empty_backfill"
        elif "acs.org.au" in url.lower() or short == "ACS" or name == "ACS":
            change_reason = "acs_corruption_fix"
        elif "wes.com" in url.lower():
            change_reason = "wes_com_url_normalised"
        elif short == "WES" and name == "World Education Services":
            counts["no_change"] += 1
            continue
        else:
            counts["no_change"] += 1
            continue

        # Build new assessing_authority preserving all other fields
        new_aa = dict(aa)
        new_aa.update(WES_FIX)
        new_aa["_phase_19_7_1_fix"] = {
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "reason": change_reason,
            "old_short_name": short or None,
            "old_name": name or None,
            "old_url": url or None,
        }

        # Capture pre-state for revoke
        pre_state = {k: v for k, v in occ.items() if k != "_id"}

        # Apply
        await db["occupation_master"].update_one(
            {"occupation_id": occ_id},
            {"$set": {"assessing_authority": new_aa}},
        )
        ibs.record_update(batch, occ_id,
                          {"country_code": "CA", "occupation_id": occ_id},
                          pre_state)
        if change_reason == "empty_backfill":
            counts["empty_backfilled"] += 1
        elif change_reason == "acs_corruption_fix":
            counts["acs_corruption_fixed"] += 1
            logger.info("ACS corruption fixed on occ %s (%s)", occ_id, occ.get("title"))
        elif change_reason == "wes_com_url_normalised":
            counts["wes_com_fixed"] += 1

    total_updated = counts["empty_backfilled"] + counts["acs_corruption_fixed"] + counts["wes_com_fixed"]

    # Close batch
    await ibs.close_batch(db, batch, total_rows=counts["total_ca"], status="committed")

    # Audit
    await log_action(
        db, action="ca_data_quality_fix.phase_19_7_1",
        user_id="system", user_name="Phase 19.7.1 CA Fix",
        severity="info",
        summary={"batch_id": batch["batch_id"], **counts, "total_updated": total_updated},
    )

    print("\n" + "="*70)
    print("PHASE 19.7.1 CA DATA QUALITY FIX COMPLETE")
    print("="*70)
    print(f"Batch ID (revocable 24h): {batch['batch_id']}")
    print(f"Total CA records       : {counts['total_ca']}")
    print(f"  ✅ Empty backfilled  : {counts['empty_backfilled']}")
    print(f"  🔧 ACS corruption fix: {counts['acs_corruption_fixed']}")
    print(f"  🔗 wes.com normalised: {counts['wes_com_fixed']}")
    print(f"  ⏭️  MCC skipped (legit): {counts['mcc_skipped']}")
    print(f"  ⏭️  No change needed : {counts['no_change']}")
    print(f"  Total updated        : {total_updated}")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
