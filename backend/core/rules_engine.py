"""Phase 9.6 — Admin-configurable Rule-Based Scoring Engine.

The calculator (`core.sales_calculator`) currently uses HARD-CODED scoring tables
that match the official 2025-26 program-year rules. This engine allows admins
to override those tables via a `kb_settings` document per country — so rule
changes published by Home Affairs / IRCC / INZ can be reflected without code
deploys.

Architecture:
  • Each country has ONE rules document in `kb_settings`:
      _id = "calculator_rules_au" | "calculator_rules_ca" | "calculator_rules_nz"
  • If no override exists, the engine returns the hardcoded defaults
  • Admins can GET / PUT / RESET via /api/admin/calculator-rules/{country}
  • The calculator itself remains stable — it will gradually opt-in to reading
    via `load_rules(country)` instead of touching hardcoded constants directly.

NOTE: This iteration ships the STORAGE + ADMIN UI. Actual calculator wiring
(reading from DB instead of constants) is a follow-up — current calculator
behavior is preserved 100%.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ─── Hardcoded defaults — mirror current `core.sales_calculator` tables ──────
# These ARE the official 2025-26 rules; admins should edit only when a new
# program year publishes updated points.

DEFAULTS_AU: Dict[str, Any] = {
    "country": "AU",
    "version": "2025-26",
    "tables": {
        "age": {
            "type": "bands",
            "rule": "Single applicants 25-32 get 30 pts; 33-39 = 25; 40-44 = 15; 45+ = 0",
            "bands": [
                {"min": 18, "max": 24, "points": 25},
                {"min": 25, "max": 32, "points": 30},
                {"min": 33, "max": 39, "points": 25},
                {"min": 40, "max": 44, "points": 15},
                {"min": 45, "max": 99, "points": 0},
            ],
        },
        "english": {
            "type": "tiered",
            "rule": "Superior (IELTS 8+) = 20 pts · Proficient (7+) = 10 · Competent (6+) = 0",
            "tiers": {"superior": 20, "proficient": 10, "competent": 0, "below_competent": 0},
        },
        "education": {
            "type": "categorical",
            "rule": "PhD/Doctorate = 20 pts · Master/Bachelor = 15 · Diploma/Trade = 10",
            "categories": {
                "doctorate": 20, "phd": 20,
                "master": 15, "bachelor": 15,
                "diploma": 10, "trade": 10, "certificate_iv": 10,
                "other": 0,
            },
        },
        "overseas_experience": {
            "type": "bands",
            "rule": "8+ yrs = 15 pts · 5-7 yrs = 10 · 3-4 yrs = 5 · <3 yrs = 0",
            "bands": [
                {"min": 0, "max": 2, "points": 0},
                {"min": 3, "max": 4, "points": 5},
                {"min": 5, "max": 7, "points": 10},
                {"min": 8, "max": 99, "points": 15},
            ],
        },
        "australia_experience": {
            "type": "bands",
            "rule": "8+ yrs = 20 pts · 5-7 yrs = 15 · 3-4 yrs = 10 · 1-2 yrs = 5 · <1 yr = 0",
            "bands": [
                {"min": 0, "max": 0, "points": 0},
                {"min": 1, "max": 2, "points": 5},
                {"min": 3, "max": 4, "points": 10},
                {"min": 5, "max": 7, "points": 15},
                {"min": 8, "max": 99, "points": 20},
            ],
        },
        "partner_skills": {
            "type": "categorical",
            "rule": "Single OR partner-is-AU-PR = 10 · Skilled partner = 10 · Partner competent English = 5 · Else 0",
            "categories": {
                "single_or_pr_partner": 10,
                "skilled_partner": 10,
                "competent_english_only": 5,
                "non_contributing": 0,
            },
        },
        "bonuses": {
            "type": "named",
            "rule": "Various +5/+10 bonuses applied additively if criteria met",
            "items": {
                "naati_accredited": 5,
                "professional_year_completed": 5,
                "specialist_education_stem_au": 10,
                "australian_study_2_years": 5,
                "regional_study_au": 5,
            },
        },
        "state_nomination": {
            "type": "by_subclass",
            "rule": "Subclass 190 nomination = +5 · Subclass 491 = +15 · Subclass 189 = 0",
            "by_subclass": {"189": 0, "190": 5, "491": 15},
        },
    },
}

DEFAULTS_CA: Dict[str, Any] = {
    "country": "CA",
    "version": "Express Entry 2025-26",
    "tables": {
        "age": {
            "type": "bands",
            "rule": "Single max 110 at age 20-29 · Decreases each year after",
            "bands": [
                {"min": 17, "max": 17, "points": 0},
                {"min": 18, "max": 19, "points": 90},
                {"min": 20, "max": 29, "points": 110},
                {"min": 30, "max": 39, "points": 95},
                {"min": 40, "max": 44, "points": 50},
                {"min": 45, "max": 99, "points": 0},
            ],
        },
        "language": {
            "type": "tiered",
            "rule": "CLB level mapped to points · CLB 10+ Single = 136 max",
            "tiers": {"clb_4": 0, "clb_5": 12, "clb_6": 18, "clb_7": 22, "clb_8": 24, "clb_9": 27, "clb_10": 32},
        },
        "education": {
            "type": "categorical",
            "rule": "PhD = 140 · Master = 135 · Bachelor = 120 · Trade = 90",
            "categories": {"phd": 140, "doctorate": 140, "master": 135, "bachelor": 120, "diploma": 98, "trade": 90, "other": 0},
        },
        "additional": {
            "type": "named",
            "rule": "Provincial Nomination = 600 · French CLB 7 = 50 · Sibling in Canada = 15 · Job offer NOC 00 = 200",
            "items": {
                "provincial_nomination": 600,
                "french_clb_7": 50,
                "sibling_in_canada": 15,
                "job_offer_noc_00": 200,
                "job_offer_noc_0_a_b": 50,
                "canadian_education_3plus_years": 30,
                "canadian_education_1_2_years": 15,
            },
        },
    },
}

DEFAULTS_NZ: Dict[str, Any] = {
    "country": "NZ",
    "version": "Skilled Migrant Category 2025-26",
    "tables": {
        "qualification": {
            "type": "categorical",
            "rule": "PhD/Doctorate = 70 · Master = 70 · Bachelor + Hons = 50 · Bachelor = 40",
            "categories": {"phd": 70, "doctorate": 70, "master": 70, "bachelor_hons": 50, "bachelor": 40, "diploma": 30, "other": 0},
        },
        "skilled_employment_years": {
            "type": "bands",
            "rule": "10+ yrs = 50 pts · 3 yrs = 30 · 1 yr = 10",
            "bands": [
                {"min": 0, "max": 0, "points": 0},
                {"min": 1, "max": 2, "points": 10},
                {"min": 3, "max": 5, "points": 30},
                {"min": 6, "max": 9, "points": 40},
                {"min": 10, "max": 99, "points": 50},
            ],
        },
        "extras": {
            "type": "named",
            "rule": "Job offer +30 · Partner skilled = +20",
            "items": {
                "nz_job_offer": 30,
                "nz_skilled_employment_current": 50,
                "regional_employment_nz": 30,
                "partner_skilled_master": 20,
            },
        },
    },
}


_DEFAULTS_BY_COUNTRY = {"AU": DEFAULTS_AU, "CA": DEFAULTS_CA, "NZ": DEFAULTS_NZ}


# ─── Loader ──────────────────────────────────────────────────────────────────
async def load_rules(db, country: str) -> Dict[str, Any]:
    """Returns the active rule set for the country — DB override if present,
    else hardcoded defaults."""
    country_u = (country or "").upper()
    if country_u not in _DEFAULTS_BY_COUNTRY:
        raise ValueError(f"Unsupported country: {country_u}")

    override = await db["kb_settings"].find_one({"_id": f"calculator_rules_{country_u.lower()}"})
    if override and override.get("tables"):
        return {
            "country": country_u,
            "version": override.get("version") or _DEFAULTS_BY_COUNTRY[country_u]["version"],
            "tables": override["tables"],
            "source": "db_override",
            "updated_at": override.get("updated_at"),
            "updated_by": override.get("updated_by"),
        }
    return {**_DEFAULTS_BY_COUNTRY[country_u], "source": "hardcoded_defaults"}


async def save_rules(db, country: str, tables: Dict[str, Any], version: Optional[str], actor: str) -> Dict[str, Any]:
    """Persist an admin-edited rule set. Returns the saved document."""
    country_u = (country or "").upper()
    if country_u not in _DEFAULTS_BY_COUNTRY:
        raise ValueError(f"Unsupported country: {country_u}")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "_id": f"calculator_rules_{country_u.lower()}",
        "country": country_u,
        "version": version or _DEFAULTS_BY_COUNTRY[country_u]["version"],
        "tables": tables,
        "updated_at": now,
        "updated_by": actor,
    }
    await db["kb_settings"].update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
    return {**doc, "source": "db_override"}


async def reset_rules(db, country: str, actor: str) -> Dict[str, Any]:
    """Delete the override doc — calculator goes back to hardcoded defaults."""
    country_u = (country or "").upper()
    if country_u not in _DEFAULTS_BY_COUNTRY:
        raise ValueError(f"Unsupported country: {country_u}")
    await db["kb_settings"].delete_one({"_id": f"calculator_rules_{country_u.lower()}"})
    return {**_DEFAULTS_BY_COUNTRY[country_u], "source": "hardcoded_defaults",
            "reset_at": datetime.now(timezone.utc).isoformat(), "reset_by": actor}


def supported_countries() -> list:
    return list(_DEFAULTS_BY_COUNTRY.keys())
