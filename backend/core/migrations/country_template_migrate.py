"""Phase 6.9.5 — Migrate existing AU/CA/NZ points_system from `country_rules`
into the new `country_templates` collection.

Idempotent. Sets status='draft' so admin verifies the calculator rules against
current official sources (especially CA CRS + NZ SMC which Sir flagged as
incorrect). The legacy points_system stays in country_rules untouched — calculator
will read templates first and fall back to legacy if no template exists.

Usage:
  python -m core.migrations.country_template_migrate --dry-run
  python -m core.migrations.country_template_migrate --commit
"""
import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.database import db  # noqa: E402

NOW = datetime.now(timezone.utc)
COUNTRY_TEMPLATES = db["country_templates"]
COUNTRY_RULES = db["country_rules"]


def _build_factor(name: str, points_range_dict: Dict[str, Any], factor_type: str = "select",
                  is_additional: bool = False, is_core: bool = True, display_order: int = 0,
                  notes: str = "") -> Dict[str, Any]:
    """Convert a {label → points} dict into a Factor doc with options[]."""
    options: List[Dict[str, Any]] = []
    if isinstance(points_range_dict, dict):
        for label, points in points_range_dict.items():
            options.append({
                "label": str(label).replace("_", " ").title(),
                "condition": str(label),
                "points": int(points) if isinstance(points, (int, float)) else 0,
            })
    return {
        "factor_id": str(uuid.uuid4()),
        "factor_name": name,
        "factor_type": factor_type,
        "options": options,
        "is_additional_factor": is_additional,
        "is_core": is_core,
        "display_order": display_order,
        "notes": notes,
    }


def _build_au_template(ps: Dict[str, Any], country: Dict[str, Any]) -> Dict[str, Any]:
    """Build AU template from the legacy points_system. Status=draft (admin verifies)."""
    factors = []
    order = 0
    for key in ["age", "english", "experience_overseas", "experience_australia", "education",
                "australian_education", "partner_skills", "state_nomination"]:
        ps_block = ps.get(key)
        if not ps_block:
            continue
        factors.append(_build_factor(
            name=key.replace("_", " ").title(),
            points_range_dict=ps_block,
            factor_type="select",
            is_additional=key in ("australian_education", "partner_skills", "state_nomination"),
            is_core=key in ("age", "english", "experience_overseas", "experience_australia", "education"),
            display_order=order,
            notes="Admin must verify against the official Department of Home Affairs Points Test (Schedule 6).",
        ))
        order += 1

    # Visa subclasses from country.visa_categories
    visa_subs = []
    for v in (country.get("visa_categories") or []):
        e = v.get("eligibility") or {}
        visa_subs.append({
            "subclass": v.get("code", ""),
            "name": v.get("name", ""),
            "min_points": e.get("points_minimum"),
            "processing_months": v.get("processing_time", ""),
        })

    return {
        "country_code": "AU",
        "country_name": "Australia",
        "flag": "🇦🇺",
        "is_active": True,
        "classification_system": "ANZSCO",
        "factors": factors,
        "pass_mark": 65,
        "visa_subclasses": visa_subs,
        "partner_rules": {
            "no_partner_or_australian_pr": 10,
            "skilled_partner": 10,
            "competent_english_partner": 5,
            "none": 0,
        },
        "notes": "Migrated from country_rules.points_system. Admin must verify factor points "
                 "against the current Department of Home Affairs Points Test (Schedule 6).",
        "status": "draft",
        "verification": {
            "verified_by": None, "verified_at": None,
            "source_reference": "Migrated · admin to verify against official Schedule 6", "review_notes": "",
        },
        "created_by": "system_migration",
        "created_at": NOW,
        "updated_at": NOW,
        "last_reviewed_at": None,
    }


def _build_ca_template(ps: Dict[str, Any], country: Dict[str, Any]) -> Dict[str, Any]:
    """Build CA CRS-style template. Sir flagged this as broken — status=draft for
    full admin rebuild against current IRCC CRS rules."""
    factors = []
    order = 0
    for key, block in ps.items():
        if not isinstance(block, dict):
            continue
        factors.append(_build_factor(
            name=key.replace("_", " ").title(),
            points_range_dict=block,
            factor_type="select",
            is_additional=key.startswith("additional_"),
            is_core=key.startswith("core_") or key.startswith("skill_"),
            display_order=order,
            notes="⚠️ Admin: rebuild this factor against current IRCC CRS rules. "
                  "Legacy mapping is incomplete.",
        ))
        order += 1
    visa_subs = []
    for v in (country.get("visa_categories") or []):
        e = v.get("eligibility") or {}
        visa_subs.append({
            "subclass": v.get("code", ""),
            "name": v.get("name", ""),
            "min_points": e.get("points_minimum"),
            "processing_months": v.get("processing_time", ""),
        })
    return {
        "country_code": "CA",
        "country_name": "Canada",
        "flag": "🇨🇦",
        "is_active": True,
        "classification_system": "NOC",
        "factors": factors,
        "pass_mark": 67,
        "visa_subclasses": visa_subs,
        "partner_rules": {
            "no_partner_or_australian_pr": 0,
            "skilled_partner": 0,
            "competent_english_partner": 0,
            "none": 0,
        },
        "notes": "⚠️ Sir flagged CA calculator as broken. Admin: rebuild factors against the "
                 "current IRCC Comprehensive Ranking System (CRS) rules + provincial nomination logic.",
        "status": "draft",
        "verification": {
            "verified_by": None, "verified_at": None,
            "source_reference": "Migrated · admin rebuild required (see notes)", "review_notes": "",
        },
        "created_by": "system_migration",
        "created_at": NOW,
        "updated_at": NOW,
        "last_reviewed_at": None,
    }


def _build_nz_template(ps: Dict[str, Any], country: Dict[str, Any]) -> Dict[str, Any]:
    """Build NZ SMC template. Sir flagged the legacy points as OUTDATED."""
    factors = []
    order = 0
    for key, block in ps.items():
        if not isinstance(block, dict):
            continue
        factors.append(_build_factor(
            name=key.replace("_", " ").title(),
            points_range_dict=block,
            factor_type="select",
            display_order=order,
            notes="⚠️ Legacy NZ points system was captured incorrectly. Admin: update to "
                  "the current Skilled Migrant Category (6-points-system, 2022+) rules.",
        ))
        order += 1
    # Add NZ-current 6-point system as a placeholder (admin to verify)
    if not factors:
        factors.append(_build_factor(
            name="Skilled Employment",
            points_range_dict={"3_points": 3, "4_points": 4, "5_points": 5, "6_points": 6},
            display_order=0,
            notes="⚠️ NZ 6-point system placeholder. Admin must verify against current SMC rules.",
        ))
    visa_subs = []
    for v in (country.get("visa_categories") or []):
        e = v.get("eligibility") or {}
        visa_subs.append({
            "subclass": v.get("code", ""),
            "name": v.get("name", ""),
            "min_points": e.get("points_minimum"),
            "processing_months": v.get("processing_time", ""),
        })
    return {
        "country_code": "NZ",
        "country_name": "New Zealand",
        "flag": "🇳🇿",
        "is_active": True,
        "classification_system": "ANZSCO",
        "factors": factors,
        "pass_mark": 6,
        "visa_subclasses": visa_subs,
        "partner_rules": {"no_partner_or_australian_pr": 0, "skilled_partner": 0,
                          "competent_english_partner": 0, "none": 0},
        "notes": "⚠️ Sir flagged NZ legacy points as outdated. Admin: update to current "
                 "Skilled Migrant Category 6-points-system (effective Oct 2023).",
        "status": "draft",
        "verification": {
            "verified_by": None, "verified_at": None,
            "source_reference": "Migrated · admin must update to current NZ SMC rules", "review_notes": "",
        },
        "created_by": "system_migration",
        "created_at": NOW,
        "updated_at": NOW,
        "last_reviewed_at": None,
    }


BUILDERS = {"AU": _build_au_template, "CA": _build_ca_template, "NZ": _build_nz_template}


async def collect_plan():
    planned = []
    summary = {"countries": [], "templates_new": 0, "templates_skip": 0, "warnings": []}
    async for country in COUNTRY_RULES.find({}, {"_id": 0}):
        cc = country.get("country_code")
        if not cc:
            continue
        builder = BUILDERS.get(cc)
        if not builder:
            summary["warnings"].append(f"No builder for country {cc}, skipped")
            continue
        existing = await COUNTRY_TEMPLATES.find_one({"country_code": cc})
        if existing:
            summary["templates_skip"] += 1
            summary["countries"].append(f"{cc} (exists, skip)")
            continue
        ps = country.get("points_system") or {}
        doc = builder(ps, country)
        planned.append(doc)
        summary["templates_new"] += 1
        summary["countries"].append(f"{cc} ({len(doc['factors'])} factors)")
    return planned, summary


async def ensure_indexes():
    await COUNTRY_TEMPLATES.create_index([("country_code", 1)], unique=True, name="country_code_unique")
    await COUNTRY_TEMPLATES.create_index([("status", 1)], name="status_lookup")


async def main(dry_run: bool):
    await ensure_indexes()
    planned, summary = await collect_plan()
    print("\n" + "═" * 70)
    print(" Phase 6.9.5 — Country Template Migration", "(DRY RUN)" if dry_run else "(COMMIT)")
    print("═" * 70)
    print(f" Templates to insert: {summary['templates_new']} new, {summary['templates_skip']} already-exists (skipped)")
    for c in summary["countries"]:
        print(f"   · {c}")
    if summary["warnings"]:
        print(f" ⚠️  Warnings ({len(summary['warnings'])}):")
        for w in summary["warnings"]:
            print(f"   · {w}")
    print(f" Status default      : 'draft' (admin must verify factor values against official sources)")
    print(f" CA + NZ flagged in notes for full admin rebuild (Sir's directive).")
    print("═" * 70)
    if dry_run:
        print(" Dry run only — nothing written.")
        return
    if planned:
        await COUNTRY_TEMPLATES.insert_many(planned, ordered=False)
    print(f" ✓ COMMITTED {len(planned)} templates")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not (args.dry_run or args.commit):
        parser.error("Specify --dry-run OR --commit")
    asyncio.run(main(dry_run=args.dry_run))
