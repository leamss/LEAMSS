"""Phase 10.2 · IRCC Express Entry Streams Mapping for NOC 2021.

Official source: Immigration, Refugees and Citizenship Canada (IRCC)
  https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/

Maps every CA `occupation_master` record to:

A) Federal program eligibility (deterministic from TEER + Major Group):
   • FSWP (Federal Skilled Worker Program)   — TEER 0/1/2/3 eligible
   • CEC  (Canadian Experience Class)         — TEER 0/1/2/3 (requires Canadian exp)
   • FSTP (Federal Skilled Trades Program)    — Major Groups 72/73/82/83/92/93, TEER 2-3 only

B) Category-Based Selection (2026 official IRCC list — 10 categories):
   1.  french_language        — NOT NOC-specific (NCLC 7+ score); applies to all eligible NOCs
   2.  healthcare             — 37 specific NOCs (medicine, nursing, allied health, social services)
   3.  stem                   — 11 specific NOCs (engineering, cybersecurity, science managers)
   4.  trade                  — 25 specific NOCs (skilled trades, construction managers)
   5.  education              — 5 specific NOCs (teachers, ECEs, classroom assistants)
   6.  transport              — 4 specific NOCs (pilots, aircraft mechanics, auto techs)
   7.  physicians_ca_exp      — 3 NOCs, requires Canadian work experience
   8.  senior_managers_ca_exp — 4 NOCs (Senior Mgmt 00012-00015), requires Canadian work exp
   9.  researchers_ca_exp     — 2 NOCs (University profs, post-secondary assistants), requires CA exp
   10. military_recruits      — 3 NOCs (Canadian Armed Forces), requires offer + 10yr foreign mil svc

Note: Agriculture and agri-food was REMOVED from the 2026 list.

This module is DETERMINISTIC — no scraping, no AI, no network calls.
The category NOC lists are baked in from the official IRCC published tables (2026 edition).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

SOURCE_NAME = "ircc_ee_streams_2026"
SOURCE_URL = (
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/"
    "immigrate-canada/express-entry/rounds-invitations/category-based-selection.html"
)

# ─── A) Federal program eligibility rules ──────────────────────────────────
# TEER eligible for FSWP / CEC (both = TEER 0-3)
FSWP_CEC_ELIGIBLE_TEER: Set[int] = {0, 1, 2, 3}

# Federal Skilled Trades Program — skilled trades major groups (NOC 2021)
# Major Group 72 = Industrial, electrical and construction trades
# Major Group 73 = Maintenance and equipment operation trades
# Major Group 82 = Supervisors in natural resources, agriculture and related production
# Major Group 83 = Occupations in natural resources and related production
# Major Group 92 = Processing, manufacturing and utilities supervisors and central control ops
# Major Group 93 = Central control and process operators in processing, manufacturing and utilities
FSTP_MAJOR_GROUPS: Set[str] = {"72", "73", "82", "83", "92", "93"}
FSTP_ELIGIBLE_TEER: Set[int] = {2, 3}  # FSTP is for TEER 2-3 trades only

# ─── B) Category-Based Selection — 2026 official IRCC list ──────────────────

# Healthcare and social services (37 NOCs)
HEALTHCARE_NOCS: Set[str] = {
    # TEER 1
    "31100", "31101", "31102", "31103",  # Physicians, vets
    "31110", "31111", "31112",  # Dentists, optometrists, audiologists
    "31120", "31121",  # Pharmacists, dietitians
    "31200", "31201", "31202", "31203", "31209",  # Psychologists, chiro, PT, OT
    "31300", "31301", "31302", "31303",  # Nurses
    # TEER 2
    "32101", "32102", "32103", "32104", "32109",  # LPN, paramedics, respiratory
    "32111",  # Dental hygienists
    "32120", "32121", "32122", "32123", "32124", "32129",  # Med tech
    "32201",  # Massage therapists
    # TEER 3
    "33101", "33102", "33103",  # Med lab assist, nurse aides, pharmacy assist
    # Social services
    "41300", "41301",  # Social workers, counsellors
    "42201",  # Social and community service workers
}

# STEM occupations (11 NOCs)
STEM_NOCS: Set[str] = {
    "20011",  # Architecture and science managers (TEER 0)
    "21220",  # Cybersecurity specialists (TEER 1)
    "21300", "21301", "21310", "21321", "21331",  # Civil/Mech/Elec/Industrial/Geo eng (TEER 1)
    "22300", "22301", "22310",  # Eng technologists (TEER 2)
    "63100",  # Insurance agents and brokers (TEER 3) — yes, per official 2026 table
}

# Trade occupations (25 NOCs)
TRADE_NOCS: Set[str] = {
    "22303",  # Construction estimators (TEER 2)
    "70010", "70011",  # Construction managers (TEER 0)
    "72100", "72102", "72106",  # Machinists, sheet metal, welders (TEER 2)
    "72200", "72201",  # Electricians (TEER 2)
    "72300", "72302",  # Plumbers, gas fitters (TEER 2)
    "72310", "72311",  # Carpenters, cabinetmakers (TEER 2)
    "72320",  # Bricklayers (TEER 2)
    "72400", "72401", "72402", "72422",  # Construction millwrights/HVAC/elec mechanics (TEER 2)
    "72501",  # Water well drillers (TEER 2)
    "72999",  # Other technical trades (TEER 2)
    "73100", "73110", "73112", "73113",  # Concrete, roofers, painters, floor (TEER 3)
    "82021",  # Contractors and supervisors, oil and gas drilling (TEER 2)
    "63201",  # Butchers — retail and wholesale (TEER 3)
}

# Education occupations (5 NOCs)
EDUCATION_NOCS: Set[str] = {
    "41220", "41221",  # Secondary, elementary teachers (TEER 1)
    "42202", "42203",  # ECE, instructors persons with disabilities (TEER 2)
    "43100",  # Teacher assistants (TEER 3)
}

# Transport occupations (4 NOCs) — newly expanded 2026
TRANSPORT_NOCS: Set[str] = {
    "72404",  # Aircraft mechanics and aircraft inspectors (TEER 2)
    "72600",  # Air pilots, flight engineers, flying instructors (TEER 2)
    "22313",  # Aircraft instrument, electrical and avionics tech (TEER 2)
    "72410",  # Automotive service techs, truck/bus mechanics (TEER 2)
}

# Physicians with Canadian work experience (3 NOCs) — REQUIRES CANADIAN EXP
PHYSICIANS_CA_NOCS: Set[str] = {"31100", "31101", "31102"}

# Senior managers with Canadian work experience (4 NOCs) — REQUIRES CANADIAN EXP
SENIOR_MANAGERS_CA_NOCS: Set[str] = {"00012", "00013", "00014", "00015"}

# Researchers with Canadian work experience (2 NOCs) — REQUIRES CANADIAN EXP
RESEARCHERS_CA_NOCS: Set[str] = {"41200", "41201"}

# Skilled military recruits (3 NOCs) — REQUIRES CAF offer + 10yr foreign service
MILITARY_NOCS: Set[str] = {"40042", "42102", "43204"}


# ─── Category metadata for UI display ──────────────────────────────────────
CATEGORY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "french_language": {
        "id": "french_language",
        "label": "French-language proficiency",
        "icon": "🇫🇷",
        "requires_canadian_exp": False,
        "language_requirement": "NCLC 7+ in all 4 abilities",
        "noc_scope": "all_eligible",  # not NOC-specific
    },
    "healthcare": {
        "id": "healthcare",
        "label": "Healthcare and social services occupations",
        "icon": "🏥",
        "requires_canadian_exp": False,
        "noc_scope": "specific_list",
    },
    "stem": {
        "id": "stem",
        "label": "Science, Technology, Engineering and Math (STEM) occupations",
        "icon": "🔬",
        "requires_canadian_exp": False,
        "noc_scope": "specific_list",
    },
    "trade": {
        "id": "trade",
        "label": "Trade occupations",
        "icon": "🔧",
        "requires_canadian_exp": False,
        "noc_scope": "specific_list",
    },
    "education": {
        "id": "education",
        "label": "Education occupations",
        "icon": "📚",
        "requires_canadian_exp": False,
        "noc_scope": "specific_list",
    },
    "transport": {
        "id": "transport",
        "label": "Transport occupations",
        "icon": "✈️",
        "requires_canadian_exp": False,
        "noc_scope": "specific_list",
    },
    "physicians_ca_exp": {
        "id": "physicians_ca_exp",
        "label": "Physicians with Canadian work experience",
        "icon": "👨‍⚕️",
        "requires_canadian_exp": True,
        "noc_scope": "specific_list",
    },
    "senior_managers_ca_exp": {
        "id": "senior_managers_ca_exp",
        "label": "Senior managers with Canadian work experience",
        "icon": "💼",
        "requires_canadian_exp": True,
        "noc_scope": "specific_list",
    },
    "researchers_ca_exp": {
        "id": "researchers_ca_exp",
        "label": "Researchers with Canadian work experience",
        "icon": "🧪",
        "requires_canadian_exp": True,
        "noc_scope": "specific_list",
    },
    "military_recruits": {
        "id": "military_recruits",
        "label": "Skilled military recruits",
        "icon": "🪖",
        "requires_canadian_exp": False,
        "language_requirement": "Foreign military service 10+ years + CAF offer",
        "noc_scope": "specific_list",
    },
}

# Lookup tables for performance: NOC → list of category IDs
_CATEGORY_NOC_MAP: Dict[str, Set[str]] = {
    "healthcare": HEALTHCARE_NOCS,
    "stem": STEM_NOCS,
    "trade": TRADE_NOCS,
    "education": EDUCATION_NOCS,
    "transport": TRANSPORT_NOCS,
    "physicians_ca_exp": PHYSICIANS_CA_NOCS,
    "senior_managers_ca_exp": SENIOR_MANAGERS_CA_NOCS,
    "researchers_ca_exp": RESEARCHERS_CA_NOCS,
    "military_recruits": MILITARY_NOCS,
}


def classify(code: str, teer: int, noc_sets_override: Dict[str, Set[str]] = None) -> Dict[str, Any]:
    """Returns full EE eligibility payload for a single NOC code + TEER.

    Output schema:
      {
        "fswp_eligible": bool,
        "cec_eligible": bool,
        "fstp_eligible": bool,
        "categories": [list of category IDs the code is in],
        "category_details": [{...metadata...} for each category],
        "french_language_eligible": bool,
      }

    If `noc_sets_override` is supplied (Phase 11 admin overrides), it is used in
    place of the hardcoded `_CATEGORY_NOC_MAP`.
    """
    major_group = code[:2]

    # A) Federal programs
    fswp_eligible = teer in FSWP_CEC_ELIGIBLE_TEER
    cec_eligible = teer in FSWP_CEC_ELIGIBLE_TEER
    fstp_eligible = (
        major_group in FSTP_MAJOR_GROUPS
        and teer in FSTP_ELIGIBLE_TEER
    )

    noc_map = noc_sets_override if noc_sets_override is not None else _CATEGORY_NOC_MAP

    # B) Category-Based Selection — match against NOC lists
    matched_categories: List[str] = []
    for cat_id, noc_set in noc_map.items():
        if code in noc_set:
            matched_categories.append(cat_id)

    # French-language is available to any NOC that's at least FSWP or CEC eligible
    french_eligible = fswp_eligible or cec_eligible
    if french_eligible:
        matched_categories.insert(0, "french_language")

    return {
        "fswp_eligible": fswp_eligible,
        "cec_eligible": cec_eligible,
        "fstp_eligible": fstp_eligible,
        "categories": matched_categories,
        "category_details": [
            CATEGORY_REGISTRY[cat_id] for cat_id in matched_categories
        ],
        "french_language_eligible": french_eligible,
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "version": "2026-01",
    }


OVERRIDE_COLLECTION = "ircc_category_overrides"


async def _build_effective_noc_map(db) -> Dict[str, Set[str]]:
    """Phase 11 — merge hardcoded defaults with admin DB overrides.

    Each override doc shape:
      { category_id, added_nocs: [..], removed_nocs: [..], updated_at, updated_by }
    """
    effective: Dict[str, Set[str]] = {k: set(v) for k, v in _CATEGORY_NOC_MAP.items()}
    async for o in db[OVERRIDE_COLLECTION].find({}, {"_id": 0}):
        cat_id = o.get("category_id")
        if cat_id not in effective:
            continue
        added = set(o.get("added_nocs") or [])
        removed = set(o.get("removed_nocs") or [])
        effective[cat_id] = (effective[cat_id] | added) - removed
    return effective


async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Run the IRCC EE Streams classifier against `occupation_master` (CA only).

    Updates each CA record with an `ee_eligibility` block. Idempotent.

    Phase 11: respects admin overrides from `ircc_category_overrides` collection.
    """
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc)
    effective_map = await _build_effective_noc_map(db)
    overrides_used = sum(
        1 for cat_id in effective_map
        if effective_map[cat_id] != _CATEGORY_NOC_MAP.get(cat_id, set())
    )

    total = 0
    updated = 0
    skipped_unchanged = 0
    skipped_no_teer = 0
    category_counts: Dict[str, int] = {cat_id: 0 for cat_id in CATEGORY_REGISTRY}
    program_counts = {"fswp": 0, "cec": 0, "fstp": 0}

    async for d in coll.find({"country_code": "CA"}, {"_id": 0, "code": 1, "teer_category": 1, "ee_eligibility": 1}):
        total += 1
        code = d.get("code")
        teer = d.get("teer_category")
        if not code or teer is None:
            skipped_no_teer += 1
            continue

        new_ee = classify(code, teer, noc_sets_override=effective_map)
        existing_ee = d.get("ee_eligibility") or {}

        # Compare (ignoring meta source/version/timestamps)
        compare_fields = ["fswp_eligible", "cec_eligible", "fstp_eligible", "categories"]
        unchanged = all(existing_ee.get(f) == new_ee[f] for f in compare_fields)
        if unchanged and existing_ee.get("source") == SOURCE_NAME:
            skipped_unchanged += 1
        else:
            if not dry_run:
                await coll.update_one(
                    {"country_code": "CA", "code": code},
                    {"$set": {
                        "ee_eligibility": {**new_ee, "last_classified_at": now},
                        "updated_at": now,
                    }},
                )
            updated += 1

        # Stats roll-up
        if new_ee["fswp_eligible"]:
            program_counts["fswp"] += 1
        if new_ee["cec_eligible"]:
            program_counts["cec"] += 1
        if new_ee["fstp_eligible"]:
            program_counts["fstp"] += 1
        for cat_id in new_ee["categories"]:
            category_counts[cat_id] = category_counts.get(cat_id, 0) + 1

    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "dry_run": dry_run,
        "version": "2026-01",
        "total_ca_codes_processed": total,
        "overrides_applied_categories": overrides_used,
        "counts": {
            "updated": updated,
            "skipped_unchanged": skipped_unchanged,
            "skipped_no_teer": skipped_no_teer,
        },
        "federal_program_distribution": program_counts,
        "category_distribution": category_counts,
        "ran_at": now.isoformat(),
        "actor": actor,
    }
