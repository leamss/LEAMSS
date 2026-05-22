"""Phase 6.9.1 — Occupation Master + Skill Body Master migration script.

Foundation for the Verified Knowledge Base. Migrates the embedded
`occupation_codes[]` + `skill_assessment_bodies[]` arrays from `country_rules`
into two flat collections:

  • occupation_master       — single source of truth for codes
  • skill_body_master       — single source of truth for assessing bodies

Idempotent. Dry-run first, then commit. Original `country_rules` untouched.

Usage:
  python -m core.migrations.occupation_master_migrate --dry-run
  python -m core.migrations.occupation_master_migrate --commit
"""
import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# Allow running this file directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.database import db  # noqa: E402


OCCUPATION_MASTER = db["occupation_master"]
SKILL_BODY_MASTER = db["skill_body_master"]
COUNTRY_RULES = db["country_rules"]

NOW = datetime.now(timezone.utc)
MIGRATION_VERSION = "Legacy migration · 2026-05-22"
MIGRATION_USER = "system_migration"


# ─────────────────────────────────────────────────────────────────────────────
# Mapping helpers
# ─────────────────────────────────────────────────────────────────────────────
def _slugify(name: str) -> str:
    return (name or "").lower().replace(" ", "_").replace("-", "_").strip("_") or "unknown"


def _build_skill_body_doc(body: Dict[str, Any], country_code: str) -> Dict[str, Any]:
    """Transform a legacy skill_assessment_bodies[i] dict into a skill_body_master doc."""
    slug = body.get("body_id") or _slugify(body.get("name", ""))
    return {
        "body_id": str(uuid.uuid4()),
        "slug": slug,
        "name": body.get("name") or "",
        "full_name": body.get("full_name") or "",
        "country_code": country_code,
        "website": body.get("website") or "",
        "description": "",  # 6.9.3 admin fills via AI Draft
        "role": "",
        "contact_info": body.get("contact_info") or {"email": "", "phone": "", "address": ""},
        "assesses_occupations": list(body.get("assesses_occupations") or []),
        "assessment_criteria": {
            "general": body.get("criteria_general") or {
                "minimum_education": "",
                "relevant_work_experience": "",
                "english_required": "",
                "registration_required": "",
            },
            "occupation_specific": [],  # 6.9.3 fills
        },
        "fees": {
            "standard": _build_fee_block(body.get("fee_native"), body.get("assessment_fee_inr"), "standard"),
            "rpl": _build_fee_block(body.get("fee_native"), None, "rpl"),
            "priority": _build_fee_block(body.get("fee_native"), None, "priority"),
            "additional_charges": [],
        },
        "processing": {
            "standard_weeks": body.get("processing_time_weeks"),
            "priority_weeks": None,
            "rpl_weeks": None,
        },
        "documents_required": [
            {"name": d, "required": True, "notes": ""} for d in (body.get("documents_required") or [])
        ],
        "status": "draft",
        "verification": {
            "verified_by": None,
            "verified_at": None,
            "source_reference": "Migrated from country_rules.skill_assessment_bodies",
            "review_notes": "",
        },
        "ai_draft": {
            "description": "",
            "role": "",
            "criteria": {},
            "generated_at": None,
            "generated_by_model": None,
            "is_stale": False,
        },
        "linked_product_id": None,
        "created_by": MIGRATION_USER,
        "created_at": NOW,
        "updated_at": NOW,
        "last_reviewed_at": None,
        "_migration_version": MIGRATION_VERSION,
    }


def _build_fee_block(fee_native: Dict[str, Any] | None, inr_equiv: int | None, key: str) -> Dict[str, Any]:
    fee_native = fee_native or {}
    amount = fee_native.get(key) or fee_native.get("standard")
    return {
        "native_currency": fee_native.get("currency") or "",
        "native_amount": amount if key in fee_native else None,
        "label": fee_native.get("label", "") if key == "standard" else "",
        "inr_equivalent": inr_equiv if key == "standard" else None,
    }


def _build_occupation_doc(
    occ: Dict[str, Any],
    country_code: str,
    skill_body_lookup: Dict[str, Dict[str, Any]],
    visa_categories: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Transform a legacy occupation_codes[i] dict into an occupation_master doc."""
    code = str(occ.get("code") or "")
    body_name = occ.get("assessing_body") or ""
    body_meta = skill_body_lookup.get(body_name.upper(), {})

    # Build visa_eligibility[] from eligible_visas[]
    eligible_codes = set(str(v) for v in (occ.get("eligible_visas") or []))
    visa_eligibility = []
    for vc in visa_categories:
        sub = str(vc.get("code", ""))
        if sub:
            visa_eligibility.append({
                "visa_subclass": sub,
                "eligible": sub in eligible_codes,
                "list": occ.get("pathway") or "",
                "notes": "",
            })

    # Build state_territory_eligibility[] from state_demand{}
    state_demand = occ.get("state_demand") or {}
    state_terr_elig = [
        {
            "state": st,
            "stream": "Skilled",
            "demand": dem,
            "sc190": dem in ("very_high", "high", "medium"),
            "sc491": dem in ("very_high", "high", "medium"),
        }
        for st, dem in state_demand.items()
    ]

    return {
        "occupation_id": str(uuid.uuid4()),
        "code": code,
        "classification_type": "ANZSCO",
        "classification_version": MIGRATION_VERSION,
        "country_code": country_code,
        "title": occ.get("title") or "",
        "alternative_titles": list(occ.get("alternative_titles") or []),
        "specialisations": [],
        "hierarchy": {
            "major_group": "",
            "sub_major_group": "",
            "minor_group": "",
            "unit_group": str(occ.get("group_code") or ""),
            "unit_group_name": occ.get("group") or "",
        },
        "description": "",  # 6.9.2/6.9.3 admin fills
        "typical_tasks": [],
        "skill_level": occ.get("skill_level"),
        "assessing_authority": {
            "body_id": body_meta.get("slug") or _slugify(body_name),
            "name": body_name,
            "full_name": body_meta.get("full_name") or "",
            "website": body_meta.get("website") or "",
        },
        "skill_assessment_details": {
            "requirements": "",
            "criteria_notes": "",
            "qualification_rules": "",
            "documents_required": [],
            "fee_native": body_meta.get("fee_native") or None,
            "fee_currency": (body_meta.get("fee_native") or {}).get("currency"),
            "processing_time": (
                f"{body_meta.get('processing_time_weeks')} weeks"
                if body_meta.get("processing_time_weeks")
                else ""
            ),
        },
        "visa_pathways": {
            "pathway_lists": [occ.get("pathway")] if occ.get("pathway") else [],
            "visa_eligibility": visa_eligibility,
            "processing_times": {},
        },
        "state_territory_eligibility": state_terr_elig,
        "similar_codes": [],
        "status": "draft",  # Sir's directive: incomplete data ≠ verified
        "verification": {
            "verified_by": None,
            "verified_at": None,
            "source_reference": "Migrated from country_rules.occupation_codes",
            "review_notes": "",
        },
        "ai_draft": {
            "description": "",
            "typical_tasks": [],
            "generated_at": None,
            "generated_by_model": None,
            "is_stale": False,
        },
        "linked_product_id": None,
        "created_by": MIGRATION_USER,
        "created_at": NOW,
        "updated_at": NOW,
        "last_reviewed_at": None,
        "_migration_version": MIGRATION_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Migration driver
# ─────────────────────────────────────────────────────────────────────────────
async def collect_plan() -> Tuple[List[Dict], List[Dict], Dict[str, Any]]:
    """Walk country_rules, build new docs, compute idempotent diff vs existing master collections.

    Returns: (occupations_to_upsert, bodies_to_upsert, summary_stats)
    """
    occupations: List[Dict[str, Any]] = []
    bodies: List[Dict[str, Any]] = []
    summary = {"countries": [], "occupations_new": 0, "occupations_skip": 0,
               "bodies_new": 0, "bodies_skip": 0, "warnings": []}

    async for country in COUNTRY_RULES.find({}, {"_id": 0}):
        cc = country.get("country_code")
        if not cc:
            continue
        summary["countries"].append(cc)
        visa_categories = country.get("visa_categories") or []

        # Skill bodies first
        skill_body_lookup: Dict[str, Dict[str, Any]] = {}
        for body in (country.get("skill_assessment_bodies") or []):
            name_upper = (body.get("name") or "").upper()
            skill_body_lookup[name_upper] = body  # for occupation cross-ref
            slug = body.get("body_id") or _slugify(body.get("name", ""))
            existing = await SKILL_BODY_MASTER.find_one({"country_code": cc, "slug": slug}, {"_id": 0})
            if existing:
                summary["bodies_skip"] += 1
                continue
            bodies.append(_build_skill_body_doc(body, cc))
            summary["bodies_new"] += 1

        # Occupations — dedupe within country by code (keep FIRST occurrence,
        # log duplicate so admin can fix source data later)
        seen_codes_this_country: Dict[str, str] = {}  # code → first title seen
        for occ in (country.get("occupation_codes") or []):
            code = str(occ.get("code") or "")
            if not code:
                summary["warnings"].append(f"{cc}: occupation with no code, skipped")
                continue
            if code in seen_codes_this_country:
                summary["warnings"].append(
                    f"{cc}: duplicate code '{code}' in source — kept first "
                    f"('{seen_codes_this_country[code]}'), dropped duplicate "
                    f"('{occ.get('title')}'). Admin should re-add with correct code."
                )
                summary["occupations_dropped_dup"] = summary.get("occupations_dropped_dup", 0) + 1
                continue
            seen_codes_this_country[code] = occ.get("title") or "?"
            existing = await OCCUPATION_MASTER.find_one({"country_code": cc, "code": code}, {"_id": 0})
            if existing:
                summary["occupations_skip"] += 1
                continue
            occupations.append(_build_occupation_doc(occ, cc, skill_body_lookup, visa_categories))
            summary["occupations_new"] += 1

    summary["occupations_total_new"] = len(occupations)
    summary["bodies_total_new"] = len(bodies)
    return occupations, bodies, summary


async def ensure_indexes() -> None:
    await OCCUPATION_MASTER.create_index([("country_code", 1), ("code", 1)], unique=True, name="country_code_unique")
    await OCCUPATION_MASTER.create_index([("country_code", 1), ("status", 1)], name="country_status")
    await OCCUPATION_MASTER.create_index([("code", 1)], name="code_lookup")
    await OCCUPATION_MASTER.create_index([("assessing_authority.body_id", 1)], name="body_lookup")
    await OCCUPATION_MASTER.create_index([("title", "text"), ("alternative_titles", "text")], name="text_search")

    await SKILL_BODY_MASTER.create_index([("country_code", 1), ("slug", 1)], unique=True, name="country_slug_unique")
    await SKILL_BODY_MASTER.create_index([("country_code", 1), ("status", 1)], name="country_status")
    await SKILL_BODY_MASTER.create_index([("name", "text"), ("full_name", "text")], name="text_search")


async def commit_plan(occupations: List[Dict], bodies: List[Dict]) -> Dict[str, int]:
    if bodies:
        await SKILL_BODY_MASTER.insert_many(bodies, ordered=False)
    if occupations:
        await OCCUPATION_MASTER.insert_many(occupations, ordered=False)
    # Mark country_rules as migrated (audit trail)
    await COUNTRY_RULES.update_many({}, {"$set": {"meta.migrated_to_occupation_master_at": NOW,
                                                   "meta.migration_version": MIGRATION_VERSION}})
    return {"occupations_inserted": len(occupations), "bodies_inserted": len(bodies)}


async def main(dry_run: bool, verbose: bool = False) -> None:
    await ensure_indexes()
    occupations, bodies, summary = await collect_plan()

    print("\n" + "═" * 70)
    print(" Phase 6.9.1 — Migration Plan (DRY RUN)" if dry_run else " Phase 6.9.1 — Migration Plan (COMMIT)")
    print("═" * 70)
    print(f" Source collection : country_rules ({len(summary['countries'])} countries: {summary['countries']})")
    print(f" Target collections: occupation_master, skill_body_master")
    print(f"")
    print(f" Occupations to insert : {summary['occupations_new']} new, {summary['occupations_skip']} already-exists (skipped)")
    print(f" Skill bodies to insert: {summary['bodies_new']} new, {summary['bodies_skip']} already-exists (skipped)")

    # Per-country breakdown
    by_country = {}
    for occ in occupations:
        by_country.setdefault(occ["country_code"], []).append(occ)
    if by_country:
        print(f"")
        print(f" Per-country breakdown:")
        for cc, occs in sorted(by_country.items()):
            print(f"   {cc}: {len(occs)} occupations  ({occs[0]['title'][:40]}, ...)")

    if summary["warnings"]:
        print(f"")
        print(f" ⚠️  Warnings ({len(summary['warnings'])}):")
        for w in summary["warnings"][:10]:
            print(f"   • {w}")

    print(f"")
    print(f" Default values applied:")
    print(f"   • status                    = 'draft'  (Sir's directive — incomplete data)")
    print(f"   • classification_type       = 'ANZSCO'")
    print(f"   • classification_version    = '{MIGRATION_VERSION}'")
    print(f"   • description / typical_tasks = empty (admin fills via AI Draft in 6.9.3)")
    print(f"   • linked_product_id         = null  (6.9.5 will populate)")

    if verbose and occupations:
        print(f"")
        print(f" Sample document (first occupation):")
        sample = occupations[0]
        for k in ["occupation_id", "code", "country_code", "title", "classification_type",
                  "status", "skill_level", "assessing_authority", "linked_product_id"]:
            v = sample.get(k)
            if isinstance(v, dict):
                v = {kk: vv for kk, vv in v.items() if kk in ("body_id", "name", "full_name")}
            print(f"   {k}: {v}")

    print("═" * 70)

    if dry_run:
        print(" Dry run only — nothing written. Re-run with --commit to apply.")
        return

    result = await commit_plan(occupations, bodies)
    print(f" ✓ COMMITTED: {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if not (args.dry_run or args.commit):
        parser.error("Specify --dry-run OR --commit")
    asyncio.run(main(dry_run=args.dry_run, verbose=args.verbose))
