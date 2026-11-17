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
from pprint import pformat
import re

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


# Phase 19.4c — Industry Data + Vacancy Snapshots
INDUSTRY_COLLECTION = "industry_master"
VACANCY_COLLECTION = "vacancy_snapshots"


async def ensure_industry_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[INDUSTRY_COLLECTION].create_index([("slug", 1)], unique=True)
    await db[INDUSTRY_COLLECTION].create_index([("anzsic_code", 1)])
    await db[VACANCY_COLLECTION].create_index([("period", 1)], unique=True)
    await db[VACANCY_COLLECTION].create_index([("is_latest", 1)])


async def commit_industry_data(
    db: AsyncIOMotorDatabase, parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Upsert industries into `industry_master` collection (idempotent by industry_name)."""
    import uuid
    parsed_list = list(parsed)
    if not parsed_list:
        return {"parsed_records": 0, "industries_upserted": 0}
    await ensure_industry_indexes(db)
    ops: List[UpdateOne] = []
    for rec in parsed_list:
        ops.append(UpdateOne(
            {"industry_name": rec["industry_name"]},
            {"$set": rec, "$setOnInsert": {"id": str(uuid.uuid4())}},
            upsert=True,
        ))
    result = await db[INDUSTRY_COLLECTION].bulk_write(ops, ordered=False)
    return {
        "parsed_records": len(parsed_list),
        "industries_upserted": result.upserted_count,
        "industries_modified": result.modified_count,
    }


# Phase 19.10 — State Nomination Lists
STATE_NOM_COLLECTION = "state_nomination_lists"


async def ensure_state_nom_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[STATE_NOM_COLLECTION].create_index(
        [("state", 1), ("list_type", 1)], unique=True,
    )
async def commit_atlas_industries(
    db: AsyncIOMotorDatabase,
    parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Upsert Atlas Industry documents into industry_master.
    One Atlas workbook = one industry document.
    """
    import uuid

    parsed_list = list(parsed)

    if not parsed_list:
        return {
            "parsed_records": 0,
            "industries_upserted": 0,
        }

    await ensure_industry_indexes(db)

    ops = []

    for rec in parsed_list:
        ops.append(
            UpdateOne(
                {
                    "anzsic_code": rec["anzsic_code"]
                },
                {
                    "$set": rec,
                    "$setOnInsert": {
                        "id": str(uuid.uuid4())
                    }
                },
                upsert=True,
            )
        )

    result = await db[INDUSTRY_COLLECTION].bulk_write(
        ops,
        ordered=False,
    )

    return {
        "parsed_records": len(parsed_list),
        "industries_upserted": result.upserted_count,
        "industries_modified": result.modified_count,
    }


async def commit_state_nominations(
    db: AsyncIOMotorDatabase, parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Idempotent upsert: one doc per (state, list_type)."""
    import uuid
    parsed_list = list(parsed)
    if not parsed_list:
        return {"parsed_records": 0, "lists_upserted": 0, "codes_indexed": 0}
    await ensure_state_nom_indexes(db)
    ops: List[UpdateOne] = []
    total_codes = 0
    for env in parsed_list:
        total_codes += len(env.get("codes") or [])
        ops.append(UpdateOne(
            {"state": env["state"], "list_type": env["list_type"]},
            {"$set": {**env, "uploaded_at": datetime.now(timezone.utc)},
             "$setOnInsert": {"id": str(uuid.uuid4())}},
            upsert=True,
        ))
    result = await db[STATE_NOM_COLLECTION].bulk_write(ops, ordered=False)
    return {
        "parsed_records": len(parsed_list),
        "lists_upserted": result.upserted_count,
        "lists_modified": result.modified_count,
        "codes_indexed": total_codes,
    }


async def commit_vacancy_report(
    db: AsyncIOMotorDatabase, parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Upsert vacancy snapshot. Flips `is_latest=False` on prior snapshots,
    sets `is_latest=True` on the newly-imported one (idempotent by period)."""
    import uuid
    parsed_list = list(parsed)
    if not parsed_list:
        return {"parsed_records": 0, "snapshots_upserted": 0}
    await ensure_industry_indexes(db)
    rec = parsed_list[0]  # one snapshot per file

    # Mark all existing as non-latest first
    await db[VACANCY_COLLECTION].update_many({"is_latest": True}, {"$set": {"is_latest": False}})

    # Upsert current as latest
    result = await db[VACANCY_COLLECTION].update_one(
        {"period": rec["period"]},
        {"$set": {**rec, "is_latest": True}, "$setOnInsert": {"id": str(uuid.uuid4())}},
        upsert=True,
    )
    return {
        "parsed_records": len(parsed_list),
        "period": rec["period"],
        "snapshots_upserted": 1 if result.upserted_id else 0,
        "snapshots_modified": result.modified_count,
    }


def detect_file_type(sheet_names: List[str], first_sheet_data: List[Any], filename: str = "") -> str:
    """Heuristic file-type detector based on sheet names / titles / filename."""
    joined = " ".join(sheet_names).lower()
    fname = (filename or "").lower()
    first_rows_text = " ".join(str(c or "").lower() for row in first_sheet_data for c in row)

    # 1. Canada NOC Elements
    if (
        "element type label english" in first_rows_text
        or "element description english" in first_rows_text
        or ("noc" in fname and "elements" in fname)
    ):
        return "noc_canada_elements"

    # 2. Canada NOC Structure
    if (
        ("code - noc" in first_rows_text and "hierarchical structure" in first_rows_text)
        or ("class title" in first_rows_text and "class definition" in first_rows_text)
        or ("noc" in fname and ("structure" in fname or "classification" in fname))
        or ("hierarchical structure" in joined and "noc" in joined)
    ):
        return "noc_canada_structure"

    # 3. New Zealand ANZSCO / Green list
    if (
        "green list" in first_rows_text
        or "green list" in fname
        or "green_list" in fname
        or "aewv" in first_rows_text
        or "nz_anzsco" in fname
        or "anzsco_2021_structure" in fname
        or ("table 5" in joined and "australian and new zealand" in first_rows_text and "nz" in fname)
    ):
        return "nz_anzsco_seed"

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
    sheet_set = {s.lower().strip() for s in sheet_names}

    if (
        "quarterly time series" in sheet_set
       and "top 10 occupations" in sheet_set
       and "industry subdivisions" in sheet_set
     ):
       return "atlas_industries"
    if (
     "contents" in sheet_set
     and "monthly time series" in sheet_set
     and "quarterly time series" in sheet_set
     and "employer recruitment insights" in sheet_set
     and "top 10s" in sheet_set
     and "demographic data" in sheet_set
     and "main fields of education" in sheet_set
     and "shortage ratings" in sheet_set
     and "projected employment" in sheet_set
     and "occupational mobility" in sheet_set
    ):
     return "atlas_occupation_workbook"
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

# async def commit_atlas_occupation_workbook(
#     db,
#     parsed,
# ):
#     print("=" * 80)
#     print("TYPE:", type(parsed))
#     print("VALUE:", parsed)
#     print("=" * 80)
#     meta = parsed.get("metadata", {})

#     code = str(meta.get("Source URL", "")).split("/")[-2].split("-")[0]

#     result = await db["occupation_master"].update_many(
#         {
#             "country_code": "AU",
#             "code": {"$regex": f"^{code}"},
#         },
#         {
#             "$set": {
#                 "atlas_data.metadata": meta,
#             }
#         },
#     )

#     return {
#         "occupation_group": code,
#         "updated": result.modified_count,
#     }
async def commit_atlas_occupation_workbook(db, parsed):

    if not parsed:
        return {
            "updated": 0
        }

    workbook = parsed[0]

    metadata = workbook.get("metadata", {})

    source_url = metadata.get("Source URL", "")

    match = re.search(r"/occupation/(\d{4})", source_url)

    if not match:
        return {
            "error": "Unable to extract ANZSCO code",
            "source_url": source_url
        }

    code4 = match.group(1)

    filter_query = {
        "country_code": "AU",
        "code": {
            "$regex": f"^{code4}"
        }
    }

    update_data = {
        "$set": {
            "atlas_workbook": workbook,
            "atlas_workbook_source": "JSA Atlas Occupation Workbook",
"atlas_workbook_source_url": "https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles",
            "atlas_workbook_imported_at": datetime.now(timezone.utc)
        }
    }

    count = await db["occupation_master"].count_documents(filter_query)

    result = await db["occupation_master"].update_many(
        filter_query,
        update_data
    )

    return {
        "code4": code4,
        "matched": result.matched_count,
        "modified": result.modified_count,
        "count_before_update": count
    }


async def commit_noc_canada_structure(
    db: AsyncIOMotorDatabase, parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Upsert Canada NOC unit groups, run enrichers, and auto-verify CA."""
    from core.scrapers import noc_canada, ircc_ee_streams, pnp_canada, ca_regional_pilots, quebec_immigration, ircc_round_cutoffs
    from core import auto_verify

    parsed_list = list(parsed)
    noc_res = await noc_canada.apply_to_db(db, dry_run=False, actor="admin_data_import")

    # Run CA enrichers
    await ircc_ee_streams.apply_to_db(db, dry_run=False)
    await pnp_canada.apply_to_db(db, dry_run=False)
    await ca_regional_pilots.apply_to_db(db, dry_run=False)
    await quebec_immigration.apply_to_db(db, dry_run=False)
    await ircc_round_cutoffs.apply_to_db(db, dry_run=False)

    verify_res = await auto_verify.run(db, "CA", dry_run=False, actor="admin_data_import")

    return {
        "source": "noc_canada_structure",
        "parsed_rows": len(parsed_list),
        "noc_result": noc_res.get("counts", {}),
        "verified_count": verify_res.get("verified_count", 0),
        "already_verified": verify_res.get("already_verified_count", 0),
    }


async def commit_noc_canada_elements(
    db: AsyncIOMotorDatabase, parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Group elements and patch occupation_master for CA, then auto-verify."""
    from collections import defaultdict
    from core import auto_verify
    from pymongo import UpdateOne

    ELEMENT_TYPE_MAP = {
        "All examples": "alternative_titles",
        "Illustrative example(s)": "illustrative_titles",
        "Main duties": "typical_tasks",
        "Employment requirements": "employment_requirements",
        "Exclusion(s)": "exclusions",
        "Inclusion(s)": "inclusions",
        "Additional information": "additional_info",
    }

    parsed_list = list(parsed)
    bucket: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for r in parsed_list:
        code = str(r.get("code") or "").strip()
        etype = str(r.get("element_type") or "").strip()
        desc = str(r.get("description") or "").strip()
        field = ELEMENT_TYPE_MAP.get(etype)
        if field and desc and code:
            bucket[code][field].append(desc)

    ops = []
    now = datetime.now(timezone.utc)
    for code, fields in bucket.items():
        patch: Dict[str, Any] = {"updated_at": now}
        if "typical_tasks" in fields:
            patch["typical_tasks"] = [t.strip() for t in fields["typical_tasks"] if t.strip()][:25]
        if "employment_requirements" in fields:
            patch["employment_requirements"] = " ".join(fields["employment_requirements"]).strip() or None
        if "alternative_titles" in fields or "illustrative_titles" in fields:
            alt_pool = []
            for src in ("alternative_titles", "illustrative_titles"):
                for t in fields.get(src, []):
                    t = t.strip()
                    if t and t not in alt_pool:
                        alt_pool.append(t)
            patch["alternative_titles"] = alt_pool[:30]
        if "exclusions" in fields:
            patch["exclusions"] = fields["exclusions"][:10]
        if "inclusions" in fields:
            patch["inclusions"] = fields["inclusions"][:10]
        if "additional_info" in fields:
            patch["additional_info"] = fields["additional_info"][:5]

        ops.append(UpdateOne(
            {"country_code": "CA", "code": code},
            {"$set": patch}
        ))

    modified = 0
    if ops:
        res = await db["occupation_master"].bulk_write(ops, ordered=False)
        modified = res.modified_count

    verify_res = await auto_verify.run(db, "CA", dry_run=False, actor="admin_data_import")

    return {
        "source": "noc_canada_elements",
        "parsed_rows": len(parsed_list),
        "codes_updated": len(ops),
        "occupations_modified": modified,
        "verified_count": verify_res.get("verified_count", 0),
    }


async def commit_nz_anzsco_seed(
    db: AsyncIOMotorDatabase, parsed: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Seed NZ occupations, run NZ enrichers, and auto-verify NZ."""
    from core.scrapers import nz_anzsco_seed, nz_green_list, nz_aewv_smc, nz_sector_agreements
    from core import auto_verify

    parsed_list = list(parsed)
    seed_res = await nz_anzsco_seed.apply_to_db(db, dry_run=False, actor="admin_data_import")

    # Run NZ enrichers
    await nz_green_list.apply_to_db(db, dry_run=False)
    await nz_aewv_smc.apply_to_db(db, dry_run=False)
    await nz_sector_agreements.apply_to_db(db, dry_run=False)

    verify_res = await auto_verify.run(db, "NZ", dry_run=False, actor="admin_data_import")

    return {
        "source": "nz_anzsco_seed",
        "parsed_rows": len(parsed_list),
        "seed_result": seed_res.get("counts", {}),
        "verified_count": verify_res.get("verified_count", 0),
        "already_verified": verify_res.get("already_verified_count", 0),
    }
