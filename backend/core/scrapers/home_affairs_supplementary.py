"""Phase 9.5 — Home Affairs Supplementary Data Scrapers (DAMA + ILA + Min Invitation Points).

Three data sources from Home Affairs that don't expose scrapable HTML
(content is in PDFs or behind JS):

  1. SkillSelect — Min Invitation Points per visa subclass
     Source: https://immi.homeaffairs.gov.au/visas/working-in-australia/skillselect/previous-rounds
     Approach: Static seed of latest confirmed cutoffs (admin can edit via CSV/AI-Extract)

  2. DAMA — Designated Area Migration Agreements (13 current agreements)
     Source: https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/
             labour-agreements/types-of-labour-agreements/designated-area-migration-agreements-(dama)
     Approach: Curated seed of 13 current DAMAs + their region + concessions
              (occupation-level breakdown is in PDF — admin extends via tools)

  3. ILA — Industry Labour Agreements (4 main industries)
     Source: https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/
             labour-agreements/types-of-labour-agreements/industry-labour-agreements
     Approach: Curated seed of 4 industries (Restaurant, Meat, Aged Care, Fishing)
              with their specific occupation codes + visa subclass

All three are deterministic (no live scraping). Re-running is idempotent.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

# ─── 1. SkillSelect Min Invitation Points (latest confirmed cutoffs) ─────────
SOURCE_INV = "https://immi.homeaffairs.gov.au/visas/working-in-australia/skillselect/previous-rounds"

# Latest confirmed minimum points required to receive an invitation per subclass
# (figures fluctuate per round; admins should update via CSV/AI-Extract tools).
# These represent the MEDIAN cutoff across the 2025-26 program year.
MIN_INVITATION_POINTS: Dict[str, Dict[str, Any]] = {
    "189": {
        "min_points": 90,
        "round_type": "General Skilled Independent",
        "as_of_program_year": "2025-26",
        "notes": "Cutoff varies by ANZSCO occupation ceiling — Health/Education roles "
                 "often invited at lower scores. This is the median across all occupations.",
    },
    "491_family": {
        "min_points": 65,
        "round_type": "Family-sponsored Regional",
        "as_of_program_year": "2025-26",
        "notes": "State-nominated 491 has separate state-driven cutoffs (see state_territory_eligibility).",
    },
    "189_priority_health": {
        "min_points": 65,
        "round_type": "Priority Health/Education stream",
        "as_of_program_year": "2025-26",
        "notes": "Tier-1 priority occupations (Healthcare/Teaching) — see skillselect_tier.",
    },
}


# ─── 2. DAMA (13 current Designated Area Migration Agreements) ───────────────
SOURCE_DAMA = ("https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/"
               "labour-agreements/types-of-labour-agreements/designated-area-migration-agreements-(dama)")

DAMA_LIST: List[Dict[str, Any]] = [
    {
        "id": "nt", "region": "Northern Territory (NT)",
        "state": "NT", "valid_until": "2030-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0", "Salary below TSMIT"],
        "sample_occupations_anzsco": ["141999", "351411", "321211", "411211", "411712"],
    },
    {
        "id": "goldfields", "region": "Goldfields, WA",
        "state": "WA", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0", "Salary below TSMIT"],
        "sample_occupations_anzsco": ["351411", "321211", "232511", "611111"],
    },
    {
        "id": "fnq", "region": "Far North Queensland",
        "state": "QLD", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0"],
        "sample_occupations_anzsco": ["351411", "451612", "411712", "234212"],
    },
    {
        "id": "east_kimberley", "region": "East Kimberley, WA",
        "state": "WA", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0"],
        "sample_occupations_anzsco": ["351411", "411213"],
    },
    {
        "id": "pilbara", "region": "Pilbara, WA",
        "state": "WA", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0", "Salary below TSMIT"],
        "sample_occupations_anzsco": ["233111", "311111", "411712"],
    },
    {
        "id": "sw_wa", "region": "South West, WA",
        "state": "WA", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0"],
        "sample_occupations_anzsco": ["351411", "232511", "411712"],
    },
    {
        "id": "orana_nsw", "region": "Orana, NSW",
        "state": "NSW", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0"],
        "sample_occupations_anzsco": ["351411", "411712", "232511"],
    },
    {
        "id": "adelaide_tech", "region": "Adelaide City Technology and Innovation Advancement DAMA",
        "state": "SA", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "Technology focus"],
        "sample_occupations_anzsco": ["261313", "261312", "261311", "263111", "263112"],
    },
    {
        "id": "sa_regional", "region": "South Australia Regional DAMA",
        "state": "SA", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0"],
        "sample_occupations_anzsco": ["351411", "232511", "411712"],
    },
    {
        "id": "townsville", "region": "Townsville, QLD",
        "state": "QLD", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0"],
        "sample_occupations_anzsco": ["351411", "411712", "232511"],
    },
    {
        "id": "hobart_city", "region": "Hobart City Deal DAMA",
        "state": "TAS", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "Specific city occupations"],
        "sample_occupations_anzsco": ["351411", "411712", "232511"],
    },
    {
        "id": "great_south_coast", "region": "Great South Coast, VIC",
        "state": "VIC", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "English IELTS 5.0"],
        "sample_occupations_anzsco": ["351411", "411712", "232511"],
    },
    {
        "id": "aerotropolis", "region": "Western Sydney Aerotropolis DAMA",
        "state": "NSW", "valid_until": "2028-06-30",
        "concessions": ["Age up to 55", "Aerospace/Tech focus"],
        "sample_occupations_anzsco": ["233911", "233912", "261313", "263111"],
    },
]


# ─── 3. ILA (4 main Industry Labour Agreements with specific occupations) ────
SOURCE_ILA = ("https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/"
              "labour-agreements/types-of-labour-agreements/industry-labour-agreements")

ILA_LIST: List[Dict[str, Any]] = [
    {
        "id": "restaurant",
        "industry": "Restaurant (Premium Dining) Industry",
        "visa_subclasses": ["482", "186"],
        "concessions": ["Permanent residency pathway", "English concession"],
        "occupations_anzsco": [
            {"code": "351311", "title": "Chef"},
            {"code": "351411", "title": "Cook"},
            {"code": "141111", "title": "Café or Restaurant Manager"},
            {"code": "431511", "title": "Trade Waiter"},
        ],
    },
    {
        "id": "meat",
        "industry": "Meat Industry",
        "visa_subclasses": ["482", "186"],
        "concessions": ["English IELTS 4.5 (vs 5.0)", "Salary 10% below TSMIT permitted"],
        "occupations_anzsco": [
            {"code": "831212", "title": "Skilled Meat Worker"},
            {"code": "831211", "title": "Meat Boner and Slicer"},
        ],
    },
    {
        "id": "aged_care",
        "industry": "Aged Care Industry",
        "visa_subclasses": ["482", "186", "494"],
        "concessions": ["PR pathway after 2 years", "English IELTS 5.0", "Union MoU required"],
        "occupations_anzsco": [
            {"code": "423312", "title": "Nursing Support Worker"},
            {"code": "423313", "title": "Personal Care Assistant"},
            {"code": "423111", "title": "Aged or Disabled Carer"},
        ],
    },
    {
        "id": "fishing",
        "industry": "Fishing Industry",
        "visa_subclasses": ["482", "186"],
        "concessions": ["Age up to 50", "English IELTS 4.5"],
        "occupations_anzsco": [
            {"code": "899211", "title": "Deck Hand"},
            {"code": "831213", "title": "Fishing Hand"},
            {"code": "231213", "title": "Ship's Master"},
            {"code": "231211", "title": "Ship's Engineer"},
            {"code": "231212", "title": "Ship's Officer"},
            {"code": "831515", "title": "Seafood Process Worker"},
        ],
    },
]


# ═════════════════════════════════════════════════════════════════════════════
# APPLIERS
# ═════════════════════════════════════════════════════════════════════════════
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def apply_min_invitation_points(db, dry_run: bool = True, actor: str = "admin") -> Dict[str, Any]:
    """Stores SkillSelect min-invitation cutoffs in a dedicated singleton document
    (kb_settings collection) so the wizard can display them, plus applies the
    per-occupation Tier-1 priority cutoff where applicable."""
    now = _now()
    counts = {"settings_doc_upserted": 0, "tier_1_codes_tagged": 0, "skipped_verified": 0}

    if not dry_run:
        await db["kb_settings"].update_one(
            {"_id": "min_invitation_points"},
            {"$set": {
                "_id": "min_invitation_points",
                "data": MIN_INVITATION_POINTS,
                "source_url": SOURCE_INV,
                "updated_at": now,
                "updated_by": actor,
            }},
            upsert=True,
        )
        counts["settings_doc_upserted"] = 1

    # Tier 1 priority cutoff applied to occupation_master records flagged tier_1
    tier1_priority = MIN_INVITATION_POINTS["189_priority_health"]["min_points"]
    standard_cutoff = MIN_INVITATION_POINTS["189"]["min_points"]
    samples: List[Dict[str, Any]] = []

    async for d in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$regex": "^[0-9]{6}$"}, "skillselect_tier": {"$in": ["tier_1", "tier_2"]}},
        {"_id": 1, "code": 1, "title": 1, "skillselect_tier": 1, "status": 1, "min_invitation_points": 1},
    ):
        if d.get("status") == "verified":
            counts["skipped_verified"] += 1
            continue
        cutoff = tier1_priority if d["skillselect_tier"] == "tier_1" else standard_cutoff
        new_val = {
            "189": cutoff,
            "491_family": MIN_INVITATION_POINTS["491_family"]["min_points"],
            "as_of_program_year": "2025-26",
            "source_url": SOURCE_INV,
        }
        if d.get("min_invitation_points") == new_val:
            continue
        counts["tier_1_codes_tagged"] += 1
        if len(samples) < 8:
            samples.append({"code": d["code"], "title": d["title"], "tier": d["skillselect_tier"], "min_189": cutoff})
        if not dry_run:
            await db["occupation_master"].update_one(
                {"_id": d["_id"]},
                {"$set": {
                    "min_invitation_points": new_val,
                    "last_min_invitation_seeded_at": now,
                }},
            )

    return {
        "source": "min_invitation_points_seed",
        "source_url": SOURCE_INV,
        "global_cutoffs": MIN_INVITATION_POINTS,
        "counts": counts,
        "sample_updates": samples,
        "dry_run": dry_run,
        "ran_at": now,
        "ran_by": actor,
    }


async def apply_dama_to_db(db, dry_run: bool = True, actor: str = "admin") -> Dict[str, Any]:
    """Apply DAMA eligibility info onto sample occupations + store full list in kb_settings."""
    now = _now()
    counts = {"settings_doc_upserted": 0, "occupations_tagged": 0, "skipped_verified": 0, "no_match_in_db": 0}
    sample_by_dama: Dict[str, List[str]] = {}

    if not dry_run:
        await db["kb_settings"].update_one(
            {"_id": "dama_list"},
            {"$set": {
                "_id": "dama_list", "data": DAMA_LIST,
                "source_url": SOURCE_DAMA, "updated_at": now, "updated_by": actor,
            }},
            upsert=True,
        )
        counts["settings_doc_upserted"] = 1

    # Build code → list-of-DAMAs mapping
    code_to_damas: Dict[str, List[Dict[str, Any]]] = {}
    for dama in DAMA_LIST:
        entry = {
            "id": dama["id"], "region": dama["region"], "state": dama["state"],
            "valid_until": dama["valid_until"], "concessions": dama["concessions"],
            "source": SOURCE_DAMA,
        }
        for code in dama["sample_occupations_anzsco"]:
            code_to_damas.setdefault(code, []).append(entry)
            sample_by_dama.setdefault(dama["id"], []).append(code)

    target_codes = list(code_to_damas.keys())
    if not target_codes:
        return {"source": "dama_seed", "counts": counts, "dry_run": dry_run, "ran_at": now, "ran_by": actor}

    found_codes: set = set()
    async for d in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$in": target_codes}},
        {"_id": 1, "code": 1, "title": 1, "dama_eligibility": 1, "status": 1},
    ):
        found_codes.add(d["code"])
        if d.get("status") == "verified":
            counts["skipped_verified"] += 1
            continue
        new_arr = code_to_damas[d["code"]]
        if (d.get("dama_eligibility") or []) == new_arr:
            continue
        counts["occupations_tagged"] += 1
        if not dry_run:
            await db["occupation_master"].update_one(
                {"_id": d["_id"]},
                {"$set": {
                    "dama_eligibility": new_arr,
                    "last_dama_seeded_at": now,
                }},
            )

    counts["no_match_in_db"] = len(set(target_codes) - found_codes)

    return {
        "source": "dama_seed",
        "source_url": SOURCE_DAMA,
        "total_damas": len(DAMA_LIST),
        "damas": [{"id": d["id"], "region": d["region"], "state": d["state"], "valid_until": d["valid_until"]} for d in DAMA_LIST],
        "counts": counts,
        "sample_codes_by_dama": {k: v[:5] for k, v in sample_by_dama.items()},
        "dry_run": dry_run,
        "ran_at": now,
        "ran_by": actor,
    }


async def apply_ila_to_db(db, dry_run: bool = True, actor: str = "admin") -> Dict[str, Any]:
    """Apply Industry Labour Agreement eligibility onto specific occupations."""
    now = _now()
    counts = {"settings_doc_upserted": 0, "occupations_tagged": 0, "skipped_verified": 0, "no_match_in_db": 0}
    sample_by_ila: Dict[str, List[str]] = {}

    if not dry_run:
        await db["kb_settings"].update_one(
            {"_id": "ila_list"},
            {"$set": {
                "_id": "ila_list", "data": ILA_LIST,
                "source_url": SOURCE_ILA, "updated_at": now, "updated_by": actor,
            }},
            upsert=True,
        )
        counts["settings_doc_upserted"] = 1

    code_to_ilas: Dict[str, List[Dict[str, Any]]] = {}
    for ila in ILA_LIST:
        entry = {
            "id": ila["id"], "industry": ila["industry"],
            "visa_subclasses": ila["visa_subclasses"],
            "concessions": ila["concessions"], "source": SOURCE_ILA,
        }
        for occ in ila["occupations_anzsco"]:
            code_to_ilas.setdefault(occ["code"], []).append(entry)
            sample_by_ila.setdefault(ila["id"], []).append(occ["code"])

    target_codes = list(code_to_ilas.keys())
    if not target_codes:
        return {"source": "ila_seed", "counts": counts, "dry_run": dry_run, "ran_at": now, "ran_by": actor}

    found_codes: set = set()
    async for d in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$in": target_codes}},
        {"_id": 1, "code": 1, "title": 1, "ila_eligibility": 1, "status": 1},
    ):
        found_codes.add(d["code"])
        if d.get("status") == "verified":
            counts["skipped_verified"] += 1
            continue
        new_arr = code_to_ilas[d["code"]]
        if (d.get("ila_eligibility") or []) == new_arr:
            continue
        counts["occupations_tagged"] += 1
        if not dry_run:
            await db["occupation_master"].update_one(
                {"_id": d["_id"]},
                {"$set": {
                    "ila_eligibility": new_arr,
                    "last_ila_seeded_at": now,
                }},
            )

    counts["no_match_in_db"] = len(set(target_codes) - found_codes)

    return {
        "source": "ila_seed",
        "source_url": SOURCE_ILA,
        "total_ilas": len(ILA_LIST),
        "ilas": [{"id": i["id"], "industry": i["industry"], "occupations_count": len(i["occupations_anzsco"])} for i in ILA_LIST],
        "counts": counts,
        "sample_codes_by_ila": {k: v[:5] for k, v in sample_by_ila.items()},
        "dry_run": dry_run,
        "ran_at": now,
        "ran_by": actor,
    }
