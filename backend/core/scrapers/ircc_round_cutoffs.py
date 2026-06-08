"""Phase 10.4 · IRCC Express Entry Round Cutoff Tracker (2026 program year).

Official source: Immigration, Refugees and Citizenship Canada (IRCC)
  https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/
    policies-operational-instructions-agreements/ministerial-instructions/
    express-entry-rounds.html

This module is the Canada-side equivalent of AU's `min_invitation_points` scraper.
It tracks the latest published Comprehensive Ranking System (CRS) cutoff for
each round category so the Atlas Verify card + Sales Wizard can show
"You need X CRS points to be invited" per category.

Two storage locations:
  1. Singleton `kb_settings` doc with `_id="ircc_round_cutoffs"` — latest snapshot
  2. Per-occupation `occupation_master.ircc_round_cutoffs` block — copies the
     relevant category cutoffs for that NOC (e.g., a Software engineer sees
     General/PNP/CEC cutoffs; a Family physician also sees Healthcare + Physicians)

Round cutoffs change frequently (every 2-4 weeks). Admin extends/refreshes via
the CSV Upload + AI Paste-Extract tools — same pattern as AU.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

SOURCE_NAME = "ircc_round_cutoffs_2026"
SOURCE_URL = (
    "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/"
    "policies-operational-instructions-agreements/ministerial-instructions/"
    "express-entry-rounds.html"
)

# Latest confirmed cutoffs (Feb-Apr 2026 program year — sample window).
# Each entry: category → most recent draw CRS minimum + draw date + ITAs issued.
ROUND_CUTOFFS_2026: Dict[str, Dict[str, Any]] = {
    "general": {
        "label": "General all-program round",
        "latest_crs_min": None,  # No general all-program round held in 2026 H1
        "latest_draw_date": None,
        "ita_count_latest": None,
        "notes": "All-program rounds have been paused; IRCC running PNP + category-specific draws only.",
    },
    "cec": {
        "label": "Canadian Experience Class (CEC) only",
        "latest_crs_min": 518,
        "latest_draw_date": "2026-04-09",
        "ita_count_latest": 6500,
        "notes": "2026 CEC cutoffs ranged 507-518. CEC requires 1+ year Canadian work experience.",
    },
    "pnp": {
        "label": "Provincial Nominee Program (PNP)",
        "latest_crs_min": 749,
        "latest_draw_date": "2026-04-02",
        "ita_count_latest": 825,
        "notes": "PNP nominees get +600 CRS boost — cutoff includes this. 2026 PNP-only draws ran 710-805.",
    },
    "french_language": {
        "label": "French-language proficiency",
        "latest_crs_min": 409,
        "latest_draw_date": "2026-03-26",
        "ita_count_latest": 3500,
        "notes": "2026 French draws: 393-419. Required: NCLC 7+ in all 4 abilities.",
    },
    "healthcare": {
        "label": "Healthcare and social services occupations",
        "latest_crs_min": 467,
        "latest_draw_date": "2026-02-20",
        "ita_count_latest": 5500,
        "notes": "Single occupation in last 3 years (12+ months full-time). 37 eligible NOCs.",
    },
    "stem": {
        "label": "STEM occupations",
        "latest_crs_min": 491,  # Last confirmed 2025 STEM draw
        "latest_draw_date": "2025-12-04",
        "ita_count_latest": 3000,
        "notes": "Last STEM-specific draw in late 2025. 2026 STEM draws expected but not yet held in window.",
    },
    "trade": {
        "label": "Trade occupations",
        "latest_crs_min": 477,
        "latest_draw_date": "2026-04-02",
        "ita_count_latest": 2400,
        "notes": "2026 trade draw cutoff. 25 eligible NOCs.",
    },
    "education": {
        "label": "Education occupations",
        "latest_crs_min": 479,  # Last confirmed (late 2025)
        "latest_draw_date": "2025-11-15",
        "ita_count_latest": 1800,
        "notes": "Education category added late 2025. 5 eligible NOCs.",
    },
    "transport": {
        "label": "Transport occupations",
        "latest_crs_min": 435,  # 2025 introductory cutoff
        "latest_draw_date": "2025-08-26",
        "ita_count_latest": 1500,
        "notes": "Transport draws targeted at pilots, aircraft mechs, auto techs.",
    },
    "physicians_ca_exp": {
        "label": "Physicians with Canadian work experience",
        "latest_crs_min": 169,
        "latest_draw_date": "2026-02-19",
        "ita_count_latest": 400,
        "notes": "Lowest cutoff among all categories — very low CRS bar but requires CA work exp.",
    },
    "senior_managers_ca_exp": {
        "label": "Senior managers with Canadian work experience",
        "latest_crs_min": 429,
        "latest_draw_date": "2026-03-05",
        "ita_count_latest": 200,
        "notes": "Requires CA work experience in NOCs 00012-00015.",
    },
    "researchers_ca_exp": {
        "label": "Researchers with Canadian work experience",
        "latest_crs_min": None,
        "latest_draw_date": None,
        "ita_count_latest": None,
        "notes": "No 2026 dedicated draw yet — newer category established 2026.",
    },
    "military_recruits": {
        "label": "Skilled military recruits",
        "latest_crs_min": None,
        "latest_draw_date": None,
        "ita_count_latest": None,
        "notes": "New 2026 category — first draws expected later in the program year.",
    },
}

# Category → mapping function: which categories apply to which NOC?
# This mirrors Phase 10.2's ircc_ee_streams categories.
def _categories_applicable_to(code: str, teer: int, ee_categories: List[str]) -> List[str]:
    """Returns the list of round-cutoff category IDs that apply to a given NOC."""
    applicable: List[str] = []
    # Federal programs (these are always applicable if TEER 0-3)
    if teer in {0, 1, 2, 3}:
        applicable.append("general")
        applicable.append("cec")
        applicable.append("pnp")
    # Category-Based: copy from Phase 10.2's ee_categories
    for c in ee_categories or []:
        if c in ROUND_CUTOFFS_2026:
            applicable.append(c)
    return applicable


async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Snapshot the 2026 round cutoffs to kb_settings + tag each CA NOC with applicable cutoffs."""
    now = datetime.now(timezone.utc)
    coll = db["occupation_master"]

    # Step 1 — write/refresh the kb_settings singleton
    settings_doc = {
        "_id": "ircc_round_cutoffs",
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "version": "2026-H1",
        "cutoffs": ROUND_CUTOFFS_2026,
        "updated_at": now,
        "updated_by": actor,
    }
    if not dry_run:
        await db["kb_settings"].replace_one(
            {"_id": "ircc_round_cutoffs"}, settings_doc, upsert=True
        )

    # Step 2 — tag each CA NOC with the categories applicable + the cutoff values
    total = 0
    updated = 0
    skipped_unchanged = 0

    async for d in coll.find(
        {"country_code": "CA"},
        {"_id": 0, "code": 1, "teer_category": 1, "ee_eligibility": 1, "ircc_round_cutoffs": 1},
    ):
        total += 1
        code = d.get("code")
        teer = d.get("teer_category")
        if not code or teer is None:
            continue
        ee_categories = (d.get("ee_eligibility") or {}).get("categories") or []
        applicable_ids = _categories_applicable_to(code, teer, ee_categories)

        # Build the per-NOC cutoff block (copy only applicable categories)
        new_block = {
            "applicable_categories": applicable_ids,
            "cutoffs_by_category": {
                cid: {
                    "label": ROUND_CUTOFFS_2026[cid]["label"],
                    "latest_crs_min": ROUND_CUTOFFS_2026[cid]["latest_crs_min"],
                    "latest_draw_date": ROUND_CUTOFFS_2026[cid]["latest_draw_date"],
                }
                for cid in applicable_ids if cid in ROUND_CUTOFFS_2026
            },
            "version": "2026-H1",
        }
        existing_block = d.get("ircc_round_cutoffs") or {}

        if existing_block.get("applicable_categories") == new_block["applicable_categories"] \
                and existing_block.get("cutoffs_by_category") == new_block["cutoffs_by_category"]:
            skipped_unchanged += 1
            continue

        if not dry_run:
            await coll.update_one(
                {"country_code": "CA", "code": code},
                {"$set": {
                    "ircc_round_cutoffs": {**new_block, "last_synced_at": now},
                    "updated_at": now,
                }},
            )
        updated += 1

    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "dry_run": dry_run,
        "version": "2026-H1",
        "total_categories": len(ROUND_CUTOFFS_2026),
        "categories_with_active_cutoff": sum(
            1 for v in ROUND_CUTOFFS_2026.values() if v["latest_crs_min"] is not None
        ),
        "total_ca_codes_processed": total,
        "counts": {"updated": updated, "skipped_unchanged": skipped_unchanged},
        "settings_doc_id": "ircc_round_cutoffs",
        "ran_at": now.isoformat(),
        "actor": actor,
    }
