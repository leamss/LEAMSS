"""Phase 19.4 — JSA Importer Service.

Takes parsed records from the 3 JSA parsers and commits them to MongoDB with:
  * 4-digit → 6-digit ANZSCO parent-fallback (each 6-digit code under a 4-digit
    parent inherits the parent's `abs_data` / `jsa_data` with `_parent_inherited: True`)
  * Idempotent upsert (re-running an import doesn't dupe — keyed by ANZSCO code)
  * Source attribution on every field
  * Audit logging
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne

logger = logging.getLogger(__name__)

REGIONAL_COLLECTION = "regional_labour_market"


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Phase 19.4 — index `regional_labour_market` for fast region queries."""
    coll = db[REGIONAL_COLLECTION]
    await coll.create_index([("state", 1), ("rating", 1)])
    await coll.create_index([("sa4_code", 1)], unique=True)


async def commit_occupation_profiles(
    db: AsyncIOMotorDatabase, parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Upsert ABS data onto AU occupation_master records using 4→6 fallback."""
    parsed_list = list(parsed)
    n_parsed = len(parsed_list)
    code_map = {r["anzsco_4digit"]: r for r in parsed_list}

    updated = 0
    skipped_no_match = 0
    ops: List[UpdateOne] = []

    async for occ in db["occupation_master"].find(
        {"country_code": "AU"}, {"occupation_id": 1, "code": 1}
    ):
        code = str(occ.get("code") or "")
        if len(code) < 4:
            skipped_no_match += 1
            continue
        parent4 = code[:4]
        rec = code_map.get(parent4)
        if not rec:
            skipped_no_match += 1
            continue
        abs_data = dict(rec["abs_data"])
        abs_data["_parent_inherited"] = (len(code) > 4)
        abs_data["_anzsco_4digit_source"] = parent4
        ops.append(UpdateOne(
            {"occupation_id": occ["occupation_id"]},
            {"$set": {"abs_data": abs_data}},
        ))

    if ops:
        result = await db["occupation_master"].bulk_write(ops, ordered=False)
        updated = result.modified_count + result.upserted_count

    return {
        "parsed_4digit_records": n_parsed,
        "occupations_updated": updated,
        "occupations_skipped_no_4digit_match": skipped_no_match,
    }


async def commit_employment_projections(
    db: AsyncIOMotorDatabase, parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Upsert jsa_data (employment projections) onto AU occupation_master records."""
    parsed_list = list(parsed)
    n_parsed = len(parsed_list)
    code_map = {r["anzsco_4digit"]: r for r in parsed_list}

    updated = 0
    skipped_no_match = 0
    ops: List[UpdateOne] = []

    async for occ in db["occupation_master"].find(
        {"country_code": "AU"}, {"occupation_id": 1, "code": 1}
    ):
        code = str(occ.get("code") or "")
        if len(code) < 4:
            skipped_no_match += 1
            continue
        parent4 = code[:4]
        rec = code_map.get(parent4)
        if not rec:
            skipped_no_match += 1
            continue
        jsa_data = dict(rec["jsa_data"])
        jsa_data["_parent_inherited"] = (len(code) > 4)
        jsa_data["_anzsco_4digit_source"] = parent4
        ops.append(UpdateOne(
            {"occupation_id": occ["occupation_id"]},
            {"$set": {"jsa_data": jsa_data}},
        ))

    if ops:
        result = await db["occupation_master"].bulk_write(ops, ordered=False)
        updated = result.modified_count + result.upserted_count

    return {
        "parsed_4digit_records": n_parsed,
        "occupations_updated": updated,
        "occupations_skipped_no_4digit_match": skipped_no_match,
    }


async def commit_sa4_ratings(
    db: AsyncIOMotorDatabase, parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Upsert SA4 region records into `regional_labour_market` collection."""
    parsed_list = list(parsed)
    n_parsed = len(parsed_list)
    if not parsed_list:
        return {"parsed_records": 0, "regions_upserted": 0}

    await ensure_indexes(db)

    ops: List[UpdateOne] = []
    for rec in parsed_list:
        # Drop the random `id` for keying; let upsert handle existing docs by sa4_code.
        doc = {k: v for k, v in rec.items() if k != "id"}
        ops.append(UpdateOne(
            {"sa4_code": doc["sa4_code"]},
            {"$set": doc, "$setOnInsert": {"id": rec["id"]}},
            upsert=True,
        ))

    result = await db[REGIONAL_COLLECTION].bulk_write(ops, ordered=False)
    return {
        "parsed_records": n_parsed,
        "regions_upserted": result.upserted_count,
        "regions_modified": result.modified_count,
    }


def detect_file_type(sheet_names: List[str], first_sheet_data: List[Any]) -> str:
    """Heuristic file-type detector based on sheet names / titles."""
    joined = " ".join(sheet_names).lower()
    if "table_9" in joined and "table_8" in joined and "table_1" in joined:
        return "occupation_profiles"
    if any("employment projections" in (str(c) or "").lower() for row in first_sheet_data for c in row):
        return "employment_projections"
    if any("regional labour market" in (str(c) or "").lower() or "rlmi" in (str(c) or "").lower() for row in first_sheet_data for c in row):
        return "sa4_ratings"
    if "table_6 occupation unit group" in joined:
        return "employment_projections"
    if any("march 20" in s.lower() for s in sheet_names):
        return "sa4_ratings"
    if any("industry data" in (str(c) or "").lower() for row in first_sheet_data for c in row):
        return "industry_data"
    return "unknown"


async def audit_log(
    db: AsyncIOMotorDatabase, user_id: str, action: str, summary: Dict[str, Any]
) -> None:
    """Phase 19.4 — write to audit_logs collection."""
    try:
        await db["audit_logs"].insert_one({
            "user_id": user_id,
            "action": action,
            "summary": summary,
            "at": datetime.now(timezone.utc),
        })
    except Exception as e:  # noqa: BLE001
        logger.warning("audit log write failed: %s", e)
