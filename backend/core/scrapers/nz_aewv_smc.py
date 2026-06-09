"""Phase 12.1 — NZ AEWV + SMC eligibility classifier.

  • AEWV (Accredited Employer Work Visa): replaces ESSENTIAL SKILLS / TALENT /
    AEWV. Required for almost all temporary work in NZ. Based on:
      - Job's ANZSCO skill_level (1-3 = AEWV-eligible / 4-5 = AEWV-restricted)
      - Employer accreditation
      - Median wage threshold ($30.00/hr in 2026)

  • SMC (Skilled Migrant Category): NZ's 6-point system for residency.
    Each occupation gets a `smc_skill_points_base` from skill_level:
      Level 1 → 6 points (Recognized qualification + high skill)
      Level 2 → 5 points
      Level 3 → 4 points
      Level 4 → 3 points
      Level 5 → 2 points

    Other points come from work-experience, qualifications, age etc — those
    stay on the client calculator side. We only encode the OCCUPATION-derived
    base here.

This is a deterministic classifier — no scraping.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

SOURCE_NAME = "nz_aewv_smc_2026"
SOURCE_URL = "https://www.immigration.govt.nz/employ-migrants/employer-accreditation-and-the-accredited-employer-work-visa-aewv/"

# Median wage threshold for AEWV (NZD per hour) — 2026 update
AEWV_MEDIAN_WAGE_HOURLY = 30.00
SMC_PASS_MARK = 6  # 6-point pass mark (NZ 2024+ reform)

# Skill-level → base AEWV + SMC outputs
SKILL_LEVEL_TABLE: Dict[int, Dict[str, Any]] = {
    1: {
        "aewv_eligible": True,
        "smc_skill_points_base": 6,
        "occupational_band": "Highly Skilled",
        "wage_band_note": "Usually 2× median wage threshold",
    },
    2: {
        "aewv_eligible": True,
        "smc_skill_points_base": 5,
        "occupational_band": "Skilled (Tertiary)",
        "wage_band_note": "1.5× median wage threshold",
    },
    3: {
        "aewv_eligible": True,
        "smc_skill_points_base": 4,
        "occupational_band": "Skilled (Trade / Diploma)",
        "wage_band_note": "≥ Median wage threshold",
    },
    4: {
        "aewv_eligible": True,
        "smc_skill_points_base": 3,
        "occupational_band": "Semi-Skilled",
        "wage_band_note": "Sector-Agreement cap applies (Tourism / Hospitality / Care)",
    },
    5: {
        "aewv_eligible": False,
        "smc_skill_points_base": 2,
        "occupational_band": "Low-Skilled",
        "wage_band_note": "AEWV closed unless sector-agreement covers role",
    },
}


def classify(skill_level: int | None, green_tier: int | None) -> Dict[str, Any]:
    """Compute aewv_eligibility + smc_points block for one occupation."""
    sl = skill_level if skill_level in SKILL_LEVEL_TABLE else 5
    row = SKILL_LEVEL_TABLE[sl]
    # Green List Tier 1/2 occupations always pass SMC automatically
    auto_smc_pass = green_tier in (1, 2)

    return {
        "aewv_eligibility": {
            "eligible": row["aewv_eligible"],
            "occupational_band": row["occupational_band"],
            "median_wage_hourly_nzd": AEWV_MEDIAN_WAGE_HOURLY,
            "wage_band_note": row["wage_band_note"],
            "accredited_employer_required": True,
            "max_stay_years": 5 if sl in (1, 2, 3) else 3,
        },
        "smc_points_breakdown": {
            "skill_points_base": row["smc_skill_points_base"],
            "pass_mark": SMC_PASS_MARK,
            "occupation_passes_alone": row["smc_skill_points_base"] >= SMC_PASS_MARK or auto_smc_pass,
            "green_list_auto_pass": auto_smc_pass,
            "note": (
                "Green List occupation → SMC automatic 6 points." if auto_smc_pass
                else "Combine occupation points with age + qualification + work-experience."
            ),
        },
    }


async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Tag every NZ ANZSCO record with AEWV + SMC blocks."""
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc)

    total = 0
    updated = 0
    skipped_unchanged = 0
    aewv_eligible_count = 0
    smc_auto_pass_count = 0

    async for d in coll.find(
        {"country_code": "NZ"},
        {"_id": 0, "code": 1, "skill_level": 1, "nz_green_list_tier": 1,
         "aewv_eligibility": 1, "smc_points_breakdown": 1},
    ):
        total += 1
        code = d.get("code")
        if not code:
            continue
        new = classify(d.get("skill_level"), d.get("nz_green_list_tier"))
        if new["aewv_eligibility"]["eligible"]:
            aewv_eligible_count += 1
        if new["smc_points_breakdown"]["occupation_passes_alone"]:
            smc_auto_pass_count += 1

        existing_aewv = d.get("aewv_eligibility") or {}
        existing_smc = d.get("smc_points_breakdown") or {}
        unchanged = (
            existing_aewv.get("eligible") == new["aewv_eligibility"]["eligible"]
            and existing_aewv.get("occupational_band") == new["aewv_eligibility"]["occupational_band"]
            and existing_smc.get("skill_points_base") == new["smc_points_breakdown"]["skill_points_base"]
            and existing_smc.get("green_list_auto_pass") == new["smc_points_breakdown"]["green_list_auto_pass"]
        )
        if unchanged:
            skipped_unchanged += 1
            continue

        if not dry_run:
            await coll.update_one(
                {"country_code": "NZ", "code": code},
                {"$set": {
                    "aewv_eligibility": new["aewv_eligibility"],
                    "smc_points_breakdown": new["smc_points_breakdown"],
                    "updated_at": now,
                }},
            )
        updated += 1

    if not dry_run:
        await db["kb_settings"].replace_one(
            {"_id": "nz_aewv_smc"},
            {
                "_id": "nz_aewv_smc",
                "source": SOURCE_NAME,
                "version": "2026-Q1",
                "aewv_median_wage_hourly_nzd": AEWV_MEDIAN_WAGE_HOURLY,
                "smc_pass_mark": SMC_PASS_MARK,
                "skill_level_table": {str(k): v for k, v in SKILL_LEVEL_TABLE.items()},
                "updated_at": now,
            },
            upsert=True,
        )

    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "dry_run": dry_run,
        "version": "2026-Q1",
        "totals": {
            "nz_records_processed": total,
            "aewv_eligible_count": aewv_eligible_count,
            "smc_auto_pass_count": smc_auto_pass_count,
        },
        "counts": {
            "updated": updated,
            "skipped_unchanged": skipped_unchanged,
        },
        "ran_at": now.isoformat(),
        "actor": actor,
    }
