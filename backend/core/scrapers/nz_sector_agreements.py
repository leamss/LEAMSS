"""Phase 12.1 — NZ Sector Agreements (Construction / Care / Transport / Tourism).

Sector Agreements grant relaxed AEWV rules (e.g., below median wage) for
labour-shortage industries. Replaces the older "RSE / Hospitality / Care Workforce"
schemes.

Currently active 2026:
  • Construction & Infrastructure (CISA)
  • Care Workforce
  • Transport (HGV drivers + bus operators)
  • Tourism & Hospitality (sub-cap wage roles)
  • Meat Processing
  • Seasonal Snow & Adventure Tourism

DETERMINISTIC — no scraping. Static lists curated from immigration.govt.nz.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

SOURCE_NAME = "nz_sector_agreements_2026"
SOURCE_URL = "https://www.immigration.govt.nz/employ-migrants/sector-agreements"

# ─── Sector → ANZSCO codes mapping ──────────────────────────────────────────
SECTOR_AGREEMENTS: Dict[str, Dict[str, Any]] = {
    "construction_cisa": {
        "name": "Construction & Infrastructure (CISA)",
        "concessions": "Sub-median wage allowed, accelerated processing, 3-year visas.",
        "occupations": {
            "331111", "331112", "331211", "331212", "331213",  # Bricklayers, Carpenters
            "332211",  # Painter
            "333111", "333211", "333212", "333411",  # Plasterer, Tiler, Glazier
            "334111", "334112", "334113", "334114", "334115",  # Plumber, Gasfitter, Drainlayer
            "341111", "341112", "341113",  # Electrician
            "712111", "721211", "721212", "721213", "721214", "721215", "721216",  # Plant operators
            "322311", "322312", "322313",  # Welder / Metal Fabricator
            "323211", "323212", "323213",  # Fitter
        },
    },
    "care_workforce": {
        "name": "Care Workforce (Aged & Disability Care)",
        "concessions": "Wage threshold $28.25/hr (sub-median), enhanced family reunion.",
        "occupations": {
            "423111", "423211", "423311", "423312", "423313",  # Care assistants
            "254412", "254416", "254417", "254418",  # RN Aged Care, Disability
            "411411", "411412",  # Welfare Support Workers
            "134214", "134299",  # Welfare Centre Manager
        },
    },
    "transport": {
        "name": "Transport (HGV Drivers + Bus Operators)",
        "concessions": "Below-median wage allowed for HGV class 4-5 drivers.",
        "occupations": {
            "721211", "721212", "721213", "721214", "721215", "721216",  # Heavy plant operators
            "323111", "323112", "323113",  # Aircraft maintenance engineers
        },
    },
    "tourism_hospitality": {
        "name": "Tourism & Hospitality (Sub-Cap Wage)",
        "concessions": "Chefs + Cafe/Restaurant Managers + adventure tourism roles allowed sub-median.",
        "occupations": {
            "141111",  # Cafe or Restaurant Manager
            "141311",  # Hotel/Motel Manager
            "351311",  # Chef
            "351411",  # Cook
            "351111", "351112",  # Baker, Pastrycook
            "351211",  # Butcher
        },
    },
    "meat_processing": {
        "name": "Meat Processing",
        "concessions": "Boners, Slaughterers, Process Workers — annual quota system.",
        "occupations": {
            "351211",  # Butcher / Smallgoods Maker
        },
    },
    "seasonal_snow_adventure": {
        "name": "Seasonal Snow & Adventure Tourism",
        "concessions": "Short-term seasonal visas, accelerated processing.",
        "occupations": {
            "141311",  # Hotel/Motel Manager
            "149311",  # Conference and Event Organiser
        },
    },
}


def classify(code: str) -> Dict[str, Any]:
    """Return sector agreement eligibility for one ANZSCO code."""
    eligible: List[Dict[str, str]] = []
    for sec_id, sec in SECTOR_AGREEMENTS.items():
        if code in sec["occupations"]:
            eligible.append({
                "sector_id": sec_id,
                "name": sec["name"],
                "concessions": sec["concessions"],
            })
    return {
        "sector_agreement_eligibility": eligible,
        "is_sector_agreement_role": bool(eligible),
        "sector_count": len(eligible),
    }


async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc)

    total = 0
    updated = 0
    skipped_unchanged = 0
    sector_count_dist: Dict[str, int] = {sid: 0 for sid in SECTOR_AGREEMENTS}
    tagged_codes = 0

    async for d in coll.find(
        {"country_code": "NZ"},
        {"_id": 0, "code": 1, "sector_agreement_eligibility": 1},
    ):
        total += 1
        code = d.get("code")
        if not code:
            continue
        new = classify(code)
        if new["is_sector_agreement_role"]:
            tagged_codes += 1
        for s in new["sector_agreement_eligibility"]:
            sector_count_dist[s["sector_id"]] = sector_count_dist.get(s["sector_id"], 0) + 1

        existing = d.get("sector_agreement_eligibility") or []
        existing_ids = sorted([s.get("sector_id") for s in existing])
        new_ids = sorted([s["sector_id"] for s in new["sector_agreement_eligibility"]])
        if existing_ids == new_ids:
            skipped_unchanged += 1
            continue

        if not dry_run:
            await coll.update_one(
                {"country_code": "NZ", "code": code},
                {"$set": {
                    "sector_agreement_eligibility": new["sector_agreement_eligibility"],
                    "updated_at": now,
                }},
            )
        updated += 1

    if not dry_run:
        await db["kb_settings"].replace_one(
            {"_id": "nz_sector_agreements"},
            {
                "_id": "nz_sector_agreements",
                "source": SOURCE_NAME,
                "version": "2026-Q1",
                "agreements": {sid: {"name": sec["name"], "concessions": sec["concessions"], "code_count": len(sec["occupations"])} for sid, sec in SECTOR_AGREEMENTS.items()},
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
            "tagged_codes": tagged_codes,
            "sector_distribution": sector_count_dist,
        },
        "counts": {
            "updated": updated,
            "skipped_unchanged": skipped_unchanged,
        },
        "ran_at": now.isoformat(),
        "actor": actor,
    }
