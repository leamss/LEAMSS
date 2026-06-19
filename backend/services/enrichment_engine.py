"""Phase 19.8 — Bulk Enrichment Engine.

Cross-pollinates uploaded JSA data + 4-digit ANZSCO master → 6-digit occupation_master.
Priority hierarchy (highest wins):
    1. _verified_by:admin_id    (admin-locked — never overwrite without force=true)
    2. scraped from official    (Phase 19.2/19.3 scrapers: ACS, VETASSESS, EA, NZQA, WES)
    3. uploaded official        (Phase 19.4: JSA Excel/PDF/CSV)
    4. AI-generated drafts      (Phase 16/17 LLM helpers)
    5. seed placeholder         (Phase 19.7 home affairs canonical)

Enrichment targets for AU occupations:
    • description, typical_tasks    ← from anzsco_4digit_master parent (where empty)
    • anzsco_profile_from_4digit    ← parent's employment + earnings + demographics
    • industries_ranked, state_distribution, age_profile, education_distribution
    • osl_listed, osl_state_shortages   ← from "OSL 2025 (OSCA 6).csv"
    • assessing_authority_id        ← fuzzy match against existing FK only (TBD bucket — mostly public service, won't resolve)

Output: a delta-per-occupation describing what would change, including full provenance.
Registers as Phase 19.6 `import_batch` (revocable 24h).
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from services import import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)

# Field priority — admin verification wins over everything
PROVENANCE_PRIORITY = {
    "admin_verified": 100,
    "scraped_official": 80,
    "uploaded_official": 60,
    "ai_generated": 40,
    "seed_placeholder": 20,
}

ENRICHABLE_FIELDS = {
    "description": "uploaded_official",
    "typical_tasks": "uploaded_official",
    "anzsco_profile_from_4digit": "uploaded_official",
    "industries_ranked": "uploaded_official",
    "state_distribution": "uploaded_official",
    "age_profile": "uploaded_official",
    "education_distribution": "uploaded_official",
    "osl_listed": "uploaded_official",
    "osl_state_shortages": "uploaded_official",
    "osl_national_rating": "uploaded_official",
}


def _is_empty(value: Any) -> bool:
    """Treat None / '' / [] / {} as empty."""
    if value is None:
        return True
    if isinstance(value, (str, list, dict)) and len(value) == 0:
        return True
    return False


def _load_osl_csv(path: str) -> Dict[str, Dict[str, Any]]:
    """Parse the OSL 2025 CSV into a code → state-shortage map.

    Returns: {anzsco_code: {national_rating, state_ratings:{NSW,VIC,QLD,...}}}
    """
    out: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(path):
        logger.warning("OSL CSV not found: %s", path)
        return out
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = str(row.get("Code") or "").strip()
            if not code:
                continue
            national = (row.get("National Shortage Rating") or "").strip()
            state_keys = [
                ("NSW", "New South Wales Shortage Rating"),
                ("VIC", "Victoria Shortage Rating"),
                ("QLD", "Queensland Shortage Rating"),
                ("SA",  "South Australia Shortage Rating"),
                ("WA",  "Western Australia Shortage Rating"),
                ("TAS", "Tasmania Shortage Rating"),
                ("ACT", "Australian Capital Territory Shortage Rating"),
                ("NT",  "Northern Territory Shortage Rating"),
            ]
            state_ratings = {}
            for short, col in state_keys:
                v = (row.get(col) or "").strip()
                if v:
                    state_ratings[short] = v
            out[code] = {
                "national": national,
                "state_ratings": state_ratings,
                "listed": national.lower() not in {"", "no shortage", "no data"},
            }
    return out


async def _find_4digit_parent(db: AsyncIOMotorDatabase, code_6: str) -> Optional[Dict[str, Any]]:
    """Resolve the 4-digit ANZSCO parent for a 6-digit code."""
    if len(code_6) < 4:
        return None
    code_4 = code_6[:4]
    return await db["anzsco_4digit_master"].find_one({"code": code_4}, {"_id": 0})


async def compute_enrichment_delta(
    db: AsyncIOMotorDatabase,
    occ: Dict[str, Any],
    osl_lookup: Dict[str, Dict[str, Any]],
    force: bool = False,
) -> Dict[str, Any]:
    """Compute what would change for a single occupation.

    Returns a dict {field: {old, new, source, source_file}} describing the delta.
    Empty dict = no changes proposed.
    """
    delta: Dict[str, Any] = {}
    code = occ.get("code") or ""
    code_str = str(code)

    # Source 1: 4-digit parent inheritance
    parent = await _find_4digit_parent(db, code_str)
    if parent:
        inherit_fields = [
            ("description", parent.get("description")),
            ("typical_tasks", parent.get("tasks")),
            ("industries_ranked", parent.get("industries_ranked")),
            ("state_distribution", parent.get("state_distribution")),
            ("age_profile", parent.get("age_profile")),
            ("education_distribution", parent.get("education_distribution")),
        ]
        for field, parent_value in inherit_fields:
            if parent_value and (_is_empty(occ.get(field)) or force):
                current_verified = occ.get(f"_{field}_verified_by")
                if current_verified and not force:
                    continue  # admin-locked
                delta[field] = {
                    "old": occ.get(field),
                    "new": parent_value,
                    "source": "uploaded_official",
                    "source_file": "anzsco_4digit_master (occupation_profiles_feb_2026.xlsx)",
                    "source_provenance": parent.get("data_source", {}),
                }

        # Set anzsco_profile_from_4digit (always informational copy of parent's profile)
        parent_profile = parent.get("anzsco_profile")
        if parent_profile and (_is_empty(occ.get("anzsco_profile_from_4digit")) or force):
            delta["anzsco_profile_from_4digit"] = {
                "old": occ.get("anzsco_profile_from_4digit"),
                "new": parent_profile,
                "source": "uploaded_official",
                "source_file": "anzsco_4digit_master",
            }

    # Source 2: OSL CSV (only for AU)
    if occ.get("country_code") == "AU":
        osl_entry = osl_lookup.get(code_str)
        if osl_entry:
            if _is_empty(occ.get("osl_listed")) or occ.get("osl_listed") != osl_entry["listed"]:
                delta["osl_listed"] = {
                    "old": occ.get("osl_listed"),
                    "new": osl_entry["listed"],
                    "source": "uploaded_official",
                    "source_file": "OSL 2025 (OSCA 6).csv",
                }
            if _is_empty(occ.get("osl_state_shortages")) or force:
                delta["osl_state_shortages"] = {
                    "old": occ.get("osl_state_shortages"),
                    "new": osl_entry["state_ratings"],
                    "source": "uploaded_official",
                    "source_file": "OSL 2025 (OSCA 6).csv",
                }
            if _is_empty(occ.get("osl_national_rating")) or force:
                delta["osl_national_rating"] = {
                    "old": occ.get("osl_national_rating"),
                    "new": osl_entry["national"],
                    "source": "uploaded_official",
                    "source_file": "OSL 2025 (OSCA 6).csv",
                }

    return delta


async def run_enrichment(
    db: AsyncIOMotorDatabase,
    country_code: str = "AU",
    force: bool = False,
    dry_run: bool = False,
    user_id: str = "system",
    user_name: str = "Phase 19.8 Enrichment Engine",
    osl_csv_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Run enrichment across all occupations for a given country.

    Args:
        country_code: AU / NZ / CA (Phase 19.8 ships AU only)
        force: bypass admin-verified field locks (extra-audit)
        dry_run: compute deltas but do NOT write to DB
        osl_csv_path: optional override for OSL CSV path (default: auto-detect)

    Returns: summary dict with per-field stats + delta sample.
    """
    # Resolve OSL CSV path
    if osl_csv_path is None:
        osl_file = await db["import_files"].find_one({"filename": "OSL 2025 (OSCA 6).csv"})
        osl_csv_path = osl_file.get("stored_path") if osl_file else None
    osl_lookup = _load_osl_csv(osl_csv_path) if osl_csv_path else {}
    logger.info("OSL lookup loaded: %d codes", len(osl_lookup))

    # Open revocable batch (unless dry_run)
    batch = None
    if not dry_run:
        fake_file = f"phase_19.8_enrichment_{country_code}".encode()
        batch = await ibs.open_batch(
            db,
            ingestion_path=f"phase_19.8_bulk_enrichment.{country_code}",
            endpoint="POST /api/enrichment/run",
            uploaded_by=user_id, uploaded_by_name=user_name,
            file_name=f"phase_19.8_enrichment_{country_code}",
            file_hash=ibs.file_sha256(fake_file),
            file_size_bytes=len(fake_file),
            target_collection="occupation_master",
        )
        logger.info("Enrichment batch opened: %s", batch["batch_id"])

    counts: Dict[str, int] = {
        "total_occupations": 0,
        "occupations_with_changes": 0,
        "fields_enriched": 0,
        "field_breakdown": {},
    }
    field_breakdown: Dict[str, int] = {}
    sample_deltas: List[Dict[str, Any]] = []
    osl_resolutions = {"listed_true": 0, "listed_false": 0, "not_in_csv": 0}

    cursor = db["occupation_master"].find({"country_code": country_code})
    async for occ in cursor:
        counts["total_occupations"] += 1
        delta = await compute_enrichment_delta(db, occ, osl_lookup, force=force)
        if not delta:
            continue
        counts["occupations_with_changes"] += 1
        counts["fields_enriched"] += len(delta)
        for field in delta:
            field_breakdown[field] = field_breakdown.get(field, 0) + 1

        # OSL stats
        if "osl_listed" in delta:
            if delta["osl_listed"]["new"]:
                osl_resolutions["listed_true"] += 1
            else:
                osl_resolutions["listed_false"] += 1

        # Apply if not dry-run
        if not dry_run and batch:
            occ_id = occ.get("occupation_id") or occ.get("code")
            pre_state = {k: v for k, v in occ.items() if k != "_id"}
            update_doc: Dict[str, Any] = {}
            for field, change in delta.items():
                update_doc[field] = change["new"]
                update_doc[f"_{field}_provenance"] = {
                    "source": change["source"],
                    "source_file": change.get("source_file"),
                    "set_at": datetime.now(timezone.utc),
                    "set_by": user_id,
                }
            update_doc["_phase_19_8_enriched_at"] = datetime.now(timezone.utc)
            await db["occupation_master"].update_one(
                {"occupation_id": occ_id}, {"$set": update_doc},
            )
            ibs.record_update(
                batch, occ_id,
                {"country_code": country_code, "occupation_id": occ_id},
                pre_state,
            )

        if len(sample_deltas) < 5:
            sample_deltas.append({
                "code": occ.get("code"), "title": occ.get("title"),
                "fields_changed": list(delta.keys()),
            })

    counts["field_breakdown"] = field_breakdown
    counts["osl_resolutions"] = osl_resolutions
    counts["dry_run"] = dry_run
    counts["force"] = force
    counts["country_code"] = country_code

    # Track which AU codes had OSL but no occupation in DB
    if osl_lookup:
        all_au_codes = {str(o.get("code")) for o in
                        await db["occupation_master"].find({"country_code": "AU"}, {"code": 1, "_id": 0}).to_list(2000)}
        osl_codes = set(osl_lookup.keys())
        counts["osl_codes_total"] = len(osl_codes)
        counts["osl_codes_matched_in_db"] = len(osl_codes & all_au_codes)
        counts["osl_codes_unmatched"] = len(osl_codes - all_au_codes)

    # Close batch
    if batch:
        await ibs.close_batch(db, batch, total_rows=counts["total_occupations"], status="committed")
        counts["batch_id"] = batch["batch_id"]

    # Audit
    await log_action(
        db, action=f"enrichment.phase_19_8.{country_code}",
        user_id=user_id, user_name=user_name,
        severity="info",
        summary={**counts, "sample_deltas": sample_deltas},
    )

    counts["sample_deltas"] = sample_deltas
    return counts


async def compute_coverage(db: AsyncIOMotorDatabase, country_code: str = "AU") -> Dict[str, Any]:
    """Compute per-field coverage % across all occupations of a country."""
    total = await db["occupation_master"].count_documents({"country_code": country_code})
    if total == 0:
        return {"country_code": country_code, "total": 0, "per_field": {}}

    fields_to_check = [
        "description", "typical_tasks", "industries_ranked",
        "state_distribution", "age_profile", "education_distribution",
        "osl_listed", "osl_state_shortages", "osl_national_rating",
        "assessing_authority_id", "abs_data", "jsa_data",
        "anzsco_profile_from_4digit",
    ]
    per_field: Dict[str, Dict[str, Any]] = {}
    for field in fields_to_check:
        # Count non-empty
        # Use multi-condition: field exists + not None/empty
        filled = await db["occupation_master"].count_documents({
            "country_code": country_code,
            field: {"$exists": True, "$nin": [None, "", [], {}]},
        })
        per_field[field] = {"filled": filled, "pct": round(filled * 100 / total, 1)}
    return {"country_code": country_code, "total": total, "per_field": per_field}
