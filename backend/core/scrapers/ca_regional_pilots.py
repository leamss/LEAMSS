"""Phase 10.5 · Atlantic Immigration Program (AIP) + Rural & Francophone Pilots seed.

Equivalent to AU's DAMA + ILA (regional/special-route programs).

Three programs covered:

1. **AIP (Atlantic Immigration Program)** — federal, employer-driven for the 4 Atlantic provinces
   (NB, NS, PEI, NL). Requires a job offer from a provincially designated employer.
   - TEER 0-3 → 1-yr job offer, CLB 5
   - TEER 4   → permanent job offer, CLB 4
   - Excluded sectors vary per province (e.g., NB excludes accommodation/food svc in 2026)
   Official: https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/atlantic-immigration/

2. **RCIP (Rural Community Immigration Pilot)** — replaces the older RNIP.
   - 14 designated rural communities across NS, ON, MB, SK, AB, BC.
   - Each community publishes its own priority sectors + NOC list.
   Official: https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration.html

3. **FCIP (Francophone Community Immigration Pilot)** — for French-speaking candidates.
   - 6 designated communities (NB, ON, MB, BC); Sudbury & Timmins are in BOTH RCIP & FCIP.
   - Requires NCLC 5+ French.
   Official: https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/franco-immigration.html

Static seed approach (admin extends via CSV / AI tools — same pattern as DAMA).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

SOURCE_NAME = "ca_regional_pilots_2026"

# ─── AIP — Atlantic Immigration Program (4 provinces) ───────────────────────
AIP_PROGRAM: Dict[str, Any] = {
    "id": "aip",
    "name": "Atlantic Immigration Program",
    "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/atlantic-immigration/",
    "provinces": ["NB", "NS", "PE", "NL"],
    "valid_until": "ongoing",
    "concessions": {
        "language_clb_teer_0_3": 5,
        "language_clb_teer_4": 4,
        "experience_hours_required": 1560,  # 1 year @ 30h/week
        "experience_within_years": 5,
        "spouse_can_get_open_wp": True,
        "no_lmia_required": True,
    },
    "noc_eligibility": {
        # TEER 0-3 (skilled) — broad eligibility per IRCC
        "teer_0_3_eligible": True,
        "teer_4_eligible": True,  # with permanent job offer
        # Healthcare-specific bridging rules
        "healthcare_bridge_nocs": [
            # Work exp in 31301 (RN) or 31201 (LPN) can count toward:
            "33102",  # Nurse aides, orderlies and patient service associates
            "44101",  # Home support workers
        ],
    },
    # Priority NOCs commonly targeted by AIP designated employers (across 4 provinces)
    "priority_nocs": [
        # Healthcare (always priority)
        "31301", "31302", "31201", "32101", "33102", "44101",
        # Education
        "41220", "41221", "42202",
        # Trades / Construction (priority since 2025 housing initiatives)
        "70010", "72100", "72106", "72200", "72300", "72310", "72400",
        # IT (NS + NB tech corridor)
        "21231", "21232", "21311",
        # Hospitality (only some Atlantic provinces — NB excluded accommodation+food in 2026)
        # NOT including these here to be conservative
    ],
    "province_specific_notes": {
        "NB": "Accommodation/food services excluded for 2026. Healthcare, Education, Trades preferred.",
        "NS": "Designated employer list updated April 1, 2026.",
        "PE": "Strong demand in fish processing + hospitality.",
        "NL": "Aquaculture + Marine sector priority.",
    },
}

# ─── RCIP — Rural Community Immigration Pilot (14 communities) ──────────────
RCIP_COMMUNITIES: List[Dict[str, Any]] = [
    {
        "id": "rcip_pictou_county", "name": "Pictou County, NS", "province_code": "NS",
        "url": "https://pictoucountypartnership.com/rcip/",
        "priority_sectors": ["healthcare", "manufacturing", "construction"],
        "priority_nocs_subset": ["31301", "31302", "33102", "72100", "72106", "72310"],
    },
    {
        "id": "rcip_north_bay", "name": "North Bay and Area, ON", "province_code": "ON",
        "url": "https://nbrcip.ca/",
        "priority_sectors": ["healthcare", "trades", "education"],
        "priority_nocs_subset": ["31301", "32101", "72200", "72310", "41220"],
    },
    {
        "id": "rcip_sudbury", "name": "Sudbury, ON", "province_code": "ON",
        "url": "https://investsudbury.ca/why-sudbury/newcomers/rcipfcip/",
        "priority_sectors": ["mining", "healthcare", "trades", "technology"],
        "priority_nocs_subset": ["82010", "31301", "21231", "72200", "72400"],
        "also_fcip": True,
    },
    {
        "id": "rcip_timmins", "name": "Timmins, ON", "province_code": "ON",
        "url": "https://timminsedc.com/immigration/",
        "priority_sectors": ["mining", "construction", "healthcare"],
        "priority_nocs_subset": ["82010", "72100", "72310", "31301", "31302"],
        "also_fcip": True,
    },
    {
        "id": "rcip_sault_ste_marie", "name": "Sault Ste. Marie, ON", "province_code": "ON",
        "url": "https://welcometossm.com/rcip/",
        "priority_sectors": ["healthcare", "trades", "manufacturing"],
        "priority_nocs_subset": ["31301", "31302", "72100", "72310", "72400"],
    },
    {
        "id": "rcip_thunder_bay", "name": "Thunder Bay, ON", "province_code": "ON",
        "url": "https://gotothunderbay.ca/why-thunder-bay/immigration/",
        "priority_sectors": ["healthcare", "trades", "transport"],
        "priority_nocs_subset": ["31301", "32101", "72200", "72310", "72404", "72410"],
    },
    {
        "id": "rcip_steinbach", "name": "Steinbach, MB", "province_code": "MB",
        "url": "https://steinbachedc.com/rcip/",
        "priority_sectors": ["manufacturing", "agriculture", "healthcare"],
        "priority_nocs_subset": ["72100", "72106", "85100", "31301"],
    },
    {
        "id": "rcip_altona_rhineland", "name": "Altona/Rhineland, MB", "province_code": "MB",
        "url": "https://ared-rpga.com/immigration/rcip/",
        "priority_sectors": ["agriculture", "manufacturing"],
        "priority_nocs_subset": ["85100", "85101", "72100", "72106"],
    },
    {
        "id": "rcip_brandon", "name": "Brandon, MB", "province_code": "MB",
        "url": "https://economicdevelopmentbrandon.com/rcip/rcip",
        "priority_sectors": ["healthcare", "agriculture", "trades"],
        "priority_nocs_subset": ["31301", "31302", "85100", "72310"],
    },
    {
        "id": "rcip_moose_jaw", "name": "Moose Jaw, SK", "province_code": "SK",
        "url": "https://rcip.mjchamber.com/",
        "priority_sectors": ["healthcare", "trades", "transport"],
        "priority_nocs_subset": ["31301", "72200", "72310", "73300"],
    },
    {
        "id": "rcip_claresholm", "name": "Claresholm, AB", "province_code": "AB",
        "url": "https://claresholm-rcip.ca/",
        "priority_sectors": ["agriculture", "healthcare", "hospitality"],
        "priority_nocs_subset": ["85100", "31301", "63200"],
    },
    {
        "id": "rcip_west_kootenay", "name": "West Kootenay, BC", "province_code": "BC",
        "url": "https://wk-rnip.ca/",
        "priority_sectors": ["healthcare", "trades", "tourism", "manufacturing"],
        "priority_nocs_subset": ["31301", "32101", "72200", "72310", "63200"],
    },
    {
        "id": "rcip_north_okanagan_shuswap", "name": "North Okanagan Shuswap, BC", "province_code": "BC",
        "url": "https://rcipnorthokanaganshuswap.com/",
        "priority_sectors": ["agriculture", "tourism", "healthcare", "trades"],
        "priority_nocs_subset": ["85100", "63200", "31301", "72310"],
    },
    {
        "id": "rcip_peace_liard", "name": "Peace Liard, BC", "province_code": "BC",
        "url": "https://www.nebcimmigration.ca/",
        "priority_sectors": ["oil_and_gas", "healthcare", "trades", "agriculture"],
        "priority_nocs_subset": ["82021", "31301", "72200", "72310", "72400", "85100"],
    },
]

# ─── FCIP — Francophone Community Immigration Pilot (6 communities) ─────────
FCIP_COMMUNITIES: List[Dict[str, Any]] = [
    {
        "id": "fcip_acadian_peninsula", "name": "Acadian Peninsula, NB", "province_code": "NB",
        "url": "https://inspirepeninsuleacadienne.ca/programme-pilote-immigration-communautes-francophones/",
        "priority_sectors": ["fisheries", "healthcare", "manufacturing"],
        "priority_nocs_subset": ["31301", "31302", "85120", "82031"],
        "language": "French (NCLC 5+)",
    },
    {
        "id": "fcip_sudbury", "name": "Sudbury, ON", "province_code": "ON",
        "url": "https://investsudbury.ca/why-sudbury/newcomers/rcipfcip/",
        "priority_sectors": ["mining", "healthcare", "education"],
        "priority_nocs_subset": ["82010", "31301", "41220", "41221"],
        "language": "French (NCLC 5+)",
        "also_rcip": True,
    },
    {
        "id": "fcip_timmins", "name": "Timmins, ON", "province_code": "ON",
        "url": "https://timminsedc.com/immigration/",
        "priority_sectors": ["mining", "healthcare", "trades"],
        "priority_nocs_subset": ["82010", "31301", "72200", "72310"],
        "language": "French (NCLC 5+)",
        "also_rcip": True,
    },
    {
        "id": "fcip_superior_east", "name": "Superior East Region, ON", "province_code": "ON",
        "url": "https://superioreastcfdc.ca/superioreastcfdc.ca/index.php/en-ca/fcip",
        "priority_sectors": ["forestry", "healthcare", "trades"],
        "priority_nocs_subset": ["85100", "31301", "72310"],
        "language": "French (NCLC 5+)",
    },
    {
        "id": "fcip_st_pierre_jolys", "name": "St. Pierre Jolys, MB", "province_code": "MB",
        "url": "https://villagestpierrejolys.ca/p/francophone-communities-immigration-pilot-program",
        "priority_sectors": ["agriculture", "manufacturing", "healthcare"],
        "priority_nocs_subset": ["85100", "72100", "31301"],
        "language": "French (NCLC 5+)",
    },
    {
        "id": "fcip_kelowna", "name": "Kelowna, BC", "province_code": "BC",
        "url": "https://www.sdecb.com/en/pilot-program/",
        "priority_sectors": ["healthcare", "trades", "tourism", "technology"],
        "priority_nocs_subset": ["31301", "32101", "72200", "72310", "21231", "63200"],
        "language": "French (NCLC 5+)",
    },
]


async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Tag CA NOCs with regional_pilot_eligibility[] array."""
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc)

    # Build per-NOC index
    per_noc: Dict[str, List[Dict[str, Any]]] = {}

    # AIP applies to all listed priority NOCs across 4 Atlantic provinces
    for noc in AIP_PROGRAM["priority_nocs"]:
        per_noc.setdefault(noc, []).append({
            "pilot": "aip",
            "program_name": AIP_PROGRAM["name"],
            "provinces": AIP_PROGRAM["provinces"],
            "language_clb": 5,
            "url": AIP_PROGRAM["official_url"],
        })

    # RCIP — per community
    for c in RCIP_COMMUNITIES:
        for noc in c["priority_nocs_subset"]:
            per_noc.setdefault(noc, []).append({
                "pilot": "rcip",
                "community_id": c["id"],
                "community_name": c["name"],
                "province_code": c["province_code"],
                "priority_sectors": c["priority_sectors"],
                "language_clb": 4,  # RCIP min CLB 4 for TEER 4-5
                "url": c["url"],
                "also_fcip": c.get("also_fcip", False),
            })

    # FCIP — per community
    for c in FCIP_COMMUNITIES:
        for noc in c["priority_nocs_subset"]:
            per_noc.setdefault(noc, []).append({
                "pilot": "fcip",
                "community_id": c["id"],
                "community_name": c["name"],
                "province_code": c["province_code"],
                "priority_sectors": c["priority_sectors"],
                "language_nclc": 5,  # FCIP requires French NCLC 5+
                "url": c["url"],
                "also_rcip": c.get("also_rcip", False),
            })

    # Apply to DB
    total = 0
    updated = 0
    skipped_unchanged = 0

    async for d in coll.find({"country_code": "CA"}, {"_id": 0, "code": 1, "regional_pilot_eligibility": 1}):
        total += 1
        code = d.get("code")
        new_pilots = per_noc.get(code, [])
        existing = d.get("regional_pilot_eligibility") or []
        if new_pilots == existing:
            skipped_unchanged += 1
            continue
        if not dry_run:
            await coll.update_one(
                {"country_code": "CA", "code": code},
                {"$set": {
                    "regional_pilot_eligibility": new_pilots,
                    "regional_pilot_last_synced_at": now,
                    "updated_at": now,
                }},
            )
        updated += 1

    # Also store program metadata as singleton in kb_settings
    if not dry_run:
        await db["kb_settings"].replace_one(
            {"_id": "ca_regional_pilots"},
            {
                "_id": "ca_regional_pilots",
                "source": SOURCE_NAME,
                "version": "2026-H1",
                "aip": AIP_PROGRAM,
                "rcip_communities": RCIP_COMMUNITIES,
                "fcip_communities": FCIP_COMMUNITIES,
                "updated_at": now,
            },
            upsert=True,
        )

    return {
        "source": SOURCE_NAME,
        "dry_run": dry_run,
        "version": "2026-H1",
        "totals": {
            "aip_priority_nocs": len(AIP_PROGRAM["priority_nocs"]),
            "rcip_communities": len(RCIP_COMMUNITIES),
            "fcip_communities": len(FCIP_COMMUNITIES),
            "ca_codes_tagged": sum(1 for v in per_noc.values() if v),
        },
        "counts": {
            "total_ca_processed": total,
            "updated": updated,
            "skipped_unchanged": skipped_unchanged,
        },
        "ran_at": now.isoformat(),
        "actor": actor,
    }
