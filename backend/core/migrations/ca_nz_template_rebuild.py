"""Phase 6.10.1 — Rebuild CA & NZ country templates with proper modern structure.

Canada — Comprehensive Ranking System (CRS) full structure:
  • Core / Human Capital (age, education, language, Canadian work exp)
  • Spouse factors
  • Skill Transferability factors (combinations)
  • Additional points (PNP, job offer, French, sibling)

New Zealand — Skilled Migrant Category (SMC) 6-points system (effective Oct 2023):
  • Qualifications OR Income-from-employment OR Registration → 3-6 points
  • Plus NZ work experience bonus

CRITICAL:
  • Templates set to status='draft' — admin must verify exact point values
  • Existing CA / NZ template (if present) is overwritten with the new structure
  • Australia template is NOT touched (already validated factor set)
  • Idempotent — multiple runs are safe

Usage:
  python -m core.migrations.ca_nz_template_rebuild --dry-run
  python -m core.migrations.ca_nz_template_rebuild --commit
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


def _factor(name: str, factor_type: str, options: List[Dict[str, Any]],
            is_additional: bool = False, is_core: bool = True, display_order: int = 0,
            notes: str = "") -> Dict[str, Any]:
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


def _opt(label: str, points: int, condition: str = "") -> Dict[str, Any]:
    return {"label": label, "condition": condition or label.lower().replace(" ", "_"), "points": points}


# ─────────────────────────────────────────────────────────────────────────────
# CANADA — Comprehensive Ranking System (CRS)
# ─────────────────────────────────────────────────────────────────────────────
def build_canada_template() -> Dict[str, Any]:
    """Single applicant CRS (max 600 for human capital, plus additional up to 600).

    Source-ref placeholder values — admin must verify against current IRCC CRS tool
    https://www.canada.ca/en/immigration-refugees-citizenship/services/come-canada-tool-immigration-express-entry.html
    """
    factors: List[Dict[str, Any]] = []
    order = 0

    # CORE / HUMAN CAPITAL
    factors.append(_factor(
        "Age", "select", [
            _opt("17 or less", 0), _opt("18", 90), _opt("19", 95),
            _opt("20-29", 100), _opt("30", 95), _opt("31", 90),
            _opt("32", 85), _opt("33", 80), _opt("34", 75),
            _opt("35", 70), _opt("36", 65), _opt("37", 60),
            _opt("38", 55), _opt("39", 50), _opt("40", 45),
            _opt("41", 35), _opt("42", 25), _opt("43", 15),
            _opt("44", 5), _opt("45 or more", 0),
        ],
        is_core=True, display_order=order,
        notes="Max 100 (single applicant) / 110 (with spouse). Admin verify vs IRCC CRS tool.",
    )); order += 1

    factors.append(_factor(
        "Level of Education", "select", [
            _opt("Less than secondary", 0),
            _opt("Secondary diploma (high school)", 30),
            _opt("One-year post-secondary credential", 90),
            _opt("Two-year post-secondary credential", 98),
            _opt("Bachelor's (3+ years)", 120),
            _opt("Two or more post-secondary credentials (one being 3+ years)", 128),
            _opt("Master's / professional degree", 135),
            _opt("Doctoral (PhD)", 150),
        ],
        is_core=True, display_order=order,
        notes="Max 150 (single applicant). Admin verify ECA equivalencies.",
    )); order += 1

    factors.append(_factor(
        "First Official Language (English/French)", "select", [
            _opt("CLB 4 or 5 (per ability)", 6),
            _opt("CLB 6 (per ability)", 9),
            _opt("CLB 7 (per ability)", 17),
            _opt("CLB 8 (per ability)", 23),
            _opt("CLB 9 (per ability)", 31),
            _opt("CLB 10+ (per ability)", 34),
        ],
        is_core=True, display_order=order,
        notes="Points per ability (Listen/Read/Write/Speak) — max 34 each ability. "
              "Total max 136. Admin must verify CLB → IELTS/CELPIP/TEF mapping.",
    )); order += 1

    factors.append(_factor(
        "Second Official Language", "select", [
            _opt("CLB 4 or less", 0),
            _opt("CLB 5-6 (per ability)", 1),
            _opt("CLB 7-8 (per ability)", 3),
            _opt("CLB 9+ (per ability)", 6),
        ],
        is_core=True, display_order=order,
        notes="Max 24. Admin verify mapping.",
    )); order += 1

    factors.append(_factor(
        "Canadian Work Experience", "select", [
            _opt("None or less than 1 year", 0),
            _opt("1 year", 40),
            _opt("2 years", 53),
            _opt("3 years", 64),
            _opt("4 years", 72),
            _opt("5 or more years", 80),
        ],
        is_core=True, display_order=order,
        notes="Max 80 (single applicant). TEER 0, 1, 2 or 3 NOC jobs only.",
    )); order += 1

    # SPOUSE FACTORS
    factors.append(_factor(
        "Spouse — Level of Education", "select", [
            _opt("Less than secondary", 0),
            _opt("Secondary", 2),
            _opt("Post-secondary 1 year", 6),
            _opt("Post-secondary 2 years", 7),
            _opt("Bachelor's", 8),
            _opt("Two credentials (one 3+ years)", 9),
            _opt("Master's / Professional", 10),
            _opt("Doctoral", 10),
        ],
        is_additional=False, is_core=False, display_order=order,
        notes="Max 10. Applies only when spouse is also coming to Canada.",
    )); order += 1

    factors.append(_factor(
        "Spouse — First Language", "select", [
            _opt("CLB 4 or less", 0),
            _opt("CLB 5-6 (per ability)", 1),
            _opt("CLB 7-8 (per ability)", 3),
            _opt("CLB 9+ (per ability)", 5),
        ],
        is_core=False, display_order=order,
        notes="Max 20 (5 per ability).",
    )); order += 1

    factors.append(_factor(
        "Spouse — Canadian Work Experience", "select", [
            _opt("None", 0),
            _opt("1 year", 5),
            _opt("2 years", 7),
            _opt("3 years", 8),
            _opt("4 years", 9),
            _opt("5+ years", 10),
        ],
        is_core=False, display_order=order,
    )); order += 1

    # SKILL TRANSFERABILITY (max 100)
    factors.append(_factor(
        "Skill Transferability — Education + Language", "select", [
            _opt("Bachelor's + CLB 7", 13),
            _opt("Bachelor's + CLB 9+", 25),
            _opt("Two credentials + CLB 7", 25),
            _opt("Two credentials + CLB 9+", 50),
        ],
        is_core=False, display_order=order,
        notes="Max 50.",
    )); order += 1

    factors.append(_factor(
        "Skill Transferability — Foreign Work Experience + Language", "select", [
            _opt("1-2 yrs foreign + CLB 7", 13),
            _opt("1-2 yrs foreign + CLB 9+", 25),
            _opt("3+ yrs foreign + CLB 7", 25),
            _opt("3+ yrs foreign + CLB 9+", 50),
        ],
        is_core=False, display_order=order,
        notes="Max 50.",
    )); order += 1

    # ADDITIONAL POINTS (max 600)
    factors.append(_factor(
        "Provincial Nomination (PNP)", "boolean", [
            _opt("No", 0), _opt("Yes", 600),
        ],
        is_additional=True, display_order=order,
        notes="+600 points — Express Entry game-changer.",
    )); order += 1

    factors.append(_factor(
        "Arranged Employment — Job Offer (NOC 00)", "boolean", [
            _opt("No", 0), _opt("Yes (senior management)", 200),
        ],
        is_additional=True, display_order=order,
    )); order += 1

    factors.append(_factor(
        "Arranged Employment — Job Offer (NOC 0/A/B)", "boolean", [
            _opt("No", 0), _opt("Yes", 50),
        ],
        is_additional=True, display_order=order,
    )); order += 1

    factors.append(_factor(
        "Canadian Post-Secondary Education", "select", [
            _opt("None", 0),
            _opt("1-2 years credential", 15),
            _opt("3+ years credential / Master's / Doctoral", 30),
        ],
        is_additional=True, display_order=order,
    )); order += 1

    factors.append(_factor(
        "French Language Skills", "select", [
            _opt("No French (or below CLB 7)", 0),
            _opt("French NCLC 7+ AND English ≤ CLB 4", 25),
            _opt("French NCLC 7+ AND English ≥ CLB 5", 50),
        ],
        is_additional=True, display_order=order,
        notes="Bilingual bonus.",
    )); order += 1

    factors.append(_factor(
        "Sibling in Canada (Citizen / PR)", "boolean", [
            _opt("No", 0), _opt("Yes", 15),
        ],
        is_additional=True, display_order=order,
    )); order += 1

    visa_subclasses = [
        {"subclass": "express_entry", "name": "Express Entry (FSWP / CEC / FSTP)",
         "min_points": 67, "processing_months": "6 months from ITA"},
        {"subclass": "pnp", "name": "Provincial Nomination Program",
         "min_points": None, "processing_months": "6-18 months"},
        {"subclass": "ee_atlantic", "name": "Atlantic Immigration Program (via EE)",
         "min_points": None, "processing_months": "6 months"},
    ]

    return {
        "country_code": "CA",
        "country_name": "Canada",
        "flag": "🇨🇦",
        "is_active": True,
        "classification_system": "NOC",
        "factors": factors,
        "pass_mark": 67,
        "visa_subclasses": visa_subclasses,
        "partner_rules": {
            "no_partner_or_australian_pr": 0,
            "skilled_partner": 0,
            "competent_english_partner": 0,
            "none": 0,
        },
        "notes": "Phase 6.10.1 rebuild — full CRS structure (Core + Spouse + Skill Transferability + "
                 "Additional). Admin must verify exact point values against the official IRCC CRS tool "
                 "(https://www.canada.ca/.../come-canada-tool-immigration-express-entry.html) before "
                 "marking 'verified'. Calculator continues using legacy values until this template is verified.",
        "status": "draft",
        "verification": {
            "verified_by": None, "verified_at": None,
            "source_reference": "Phase 6.10.1 rebuild — IRCC CRS structure",
            "review_notes": "",
        },
        "created_by": "system_migration_6_10_1",
        "created_at": NOW,
        "updated_at": NOW,
        "last_reviewed_at": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NEW ZEALAND — SMC 6-points system (effective Oct 2023)
# ─────────────────────────────────────────────────────────────────────────────
def build_nz_template() -> Dict[str, Any]:
    """Current NZ Skilled Migrant Category 6-points threshold system.

    Pass mark = 6 points total. Choose ONE qualification path then add bonuses.
    Source: https://www.immigration.govt.nz/new-zealand-visas/visas/visa/skilled-migrant-category-resident-visa
    """
    factors: List[Dict[str, Any]] = []
    order = 0

    # Path A: Qualifications
    factors.append(_factor(
        "Qualifications (Path A)", "select", [
            _opt("No NZQF Level 4+ qualification", 0),
            _opt("NZQF Level 4 or 5 — Diploma", 3),
            _opt("NZQF Level 6 — Diploma", 4),
            _opt("NZQF Level 7 — Bachelor's", 5),
            _opt("NZQF Level 8 — Bachelor's Honours / Postgrad Diploma", 5),
            _opt("NZQF Level 9 — Master's degree", 5),
            _opt("NZQF Level 10 — Doctoral (PhD)", 6),
        ],
        is_core=True, display_order=order,
        notes="Pick ONE of the three paths (Qualifications OR Income OR Registration). "
              "Admin must verify NZQF equivalency for foreign qualifications.",
    )); order += 1

    # Path B: Income from skilled employment
    factors.append(_factor(
        "Income from Skilled Employment (Path B)", "select", [
            _opt("Below 1.5x median wage", 0),
            _opt("1.5x median wage (~NZD $66/hr)", 3),
            _opt("2x median wage", 4),
            _opt("3x median wage", 5),
            _opt("4x median wage or higher", 6),
        ],
        is_core=True, display_order=order,
        notes="Alternative path to Qualifications. Admin verify current NZ median wage threshold.",
    )); order += 1

    # Path C: Occupational registration
    factors.append(_factor(
        "Occupational Registration (Path C)", "select", [
            _opt("No registration", 0),
            _opt("Registration + 2 years skilled exp in NZ", 3),
            _opt("Registration + 4 years skilled exp in NZ", 4),
            _opt("Registration + 6 years skilled exp in NZ", 5),
            _opt("Registration requiring 6+ years (e.g., doctor)", 6),
        ],
        is_core=True, display_order=order,
        notes="For registered professions (doctors, engineers, lawyers, teachers, etc.).",
    )); order += 1

    # Bonus — NZ skilled work experience (added to any path, cap at 6 total)
    factors.append(_factor(
        "NZ Skilled Work Experience (bonus)", "select", [
            _opt("Less than 1 year", 0),
            _opt("1 year skilled NZ work", 1),
            _opt("2 years skilled NZ work", 2),
            _opt("3+ years skilled NZ work", 3),
        ],
        is_additional=True, display_order=order,
        notes="Bonus points added to the primary path. Total capped at 6 points overall.",
    )); order += 1

    visa_subclasses = [
        {"subclass": "smc", "name": "Skilled Migrant Category Resident Visa",
         "min_points": 6, "processing_months": "9-15 months"},
        {"subclass": "saw", "name": "Skilled Accredited Employer Work Visa (AEWV)",
         "min_points": None, "processing_months": "2-4 months"},
        {"subclass": "green_list", "name": "Straight to Residence (Green List Tier 1)",
         "min_points": None, "processing_months": "3-6 months"},
        {"subclass": "green_list_work", "name": "Work to Residence (Green List Tier 2)",
         "min_points": None, "processing_months": "6-9 months"},
    ]

    return {
        "country_code": "NZ",
        "country_name": "New Zealand",
        "flag": "🇳🇿",
        "is_active": True,
        "classification_system": "ANZSCO",
        "factors": factors,
        "pass_mark": 6,
        "visa_subclasses": visa_subclasses,
        "partner_rules": {
            "no_partner_or_australian_pr": 0,
            "skilled_partner": 0,
            "competent_english_partner": 0,
            "none": 0,
        },
        "notes": "Phase 6.10.1 rebuild — current NZ Skilled Migrant Category 6-points threshold "
                 "system (effective Oct 9, 2023). Single applicant qualifies via ONE of three paths "
                 "(Qualifications / Income / Registration), plus optional NZ work experience bonus. "
                 "Admin must verify current median wage thresholds + NZQF equivalencies against "
                 "https://www.immigration.govt.nz/ before marking 'verified'. Calculator uses legacy "
                 "values until this template is verified.",
        "status": "draft",
        "verification": {
            "verified_by": None, "verified_at": None,
            "source_reference": "Phase 6.10.1 rebuild — SMC 6-points (Oct 2023)",
            "review_notes": "",
        },
        "created_by": "system_migration_6_10_1",
        "created_at": NOW,
        "updated_at": NOW,
        "last_reviewed_at": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────
async def main(dry_run: bool):
    new_ca = build_canada_template()
    new_nz = build_nz_template()

    existing_ca = await COUNTRY_TEMPLATES.find_one({"country_code": "CA"})
    existing_nz = await COUNTRY_TEMPLATES.find_one({"country_code": "NZ"})

    print("\n" + "=" * 70)
    print(" Phase 6.10.1 — CA & NZ Rebuild", "(DRY RUN)" if dry_run else "(COMMIT)")
    print("=" * 70)
    print(f" Canada template:")
    print(f"   {'Replacing' if existing_ca else 'Inserting'} — {len(new_ca['factors'])} factors, pass_mark {new_ca['pass_mark']}")
    print(f"   Status: draft (admin must verify against IRCC CRS tool)")
    print(f"   Subclasses: {len(new_ca['visa_subclasses'])}")
    print(f" New Zealand template:")
    print(f"   {'Replacing' if existing_nz else 'Inserting'} — {len(new_nz['factors'])} factors, pass_mark {new_nz['pass_mark']}")
    print(f"   Status: draft (admin must verify against immigration.govt.nz)")
    print(f"   Subclasses: {len(new_nz['visa_subclasses'])}")
    print("=" * 70)
    if dry_run:
        print(" Dry run only — nothing written.")
        return

    # Overwrite existing CA and NZ templates with the new structure
    if existing_ca:
        await COUNTRY_TEMPLATES.delete_one({"country_code": "CA"})
    if existing_nz:
        await COUNTRY_TEMPLATES.delete_one({"country_code": "NZ"})
    await COUNTRY_TEMPLATES.insert_many([new_ca, new_nz])
    print(" Committed CA + NZ templates (draft).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not (args.dry_run or args.commit):
        parser.error("Specify --dry-run OR --commit")
    asyncio.run(main(dry_run=args.dry_run))
