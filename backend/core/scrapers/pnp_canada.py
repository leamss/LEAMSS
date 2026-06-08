"""Phase 10.3 · Canada Provincial Nominee Programs (PNP) Seed.

Covers all 11 PNPs (Quebec excluded — runs separate PEQ/PSTQ system):
  1. BC PNP    — British Columbia Provincial Nominee Program
  2. OINP      — Ontario Immigrant Nominee Program
  3. AAIP      — Alberta Advantage Immigration Program
  4. SINP      — Saskatchewan Immigrant Nominee Program
  5. MPNP      — Manitoba Provincial Nominee Program
  6. NBPNP     — New Brunswick Provincial Nominee Program
  7. NSNP      — Nova Scotia Nominee Program
  8. PEI PNP   — Prince Edward Island Provincial Nominee Program
  9. NLPNP     — Newfoundland & Labrador Provincial Nominee Program
  10. YNP      — Yukon Nominee Program
  11. NTNP     — Northwest Territories Nominee Program

This is a STATIC SEED — provincial sites are mostly JS-driven and publish lists
in PDFs that change weekly. Approach mirrors AU state_nominations.py:
  - Seed the core 2025-26 priority NOC lists per stream (verified at build time)
  - Admin extends via CSV Upload + AI Paste-Extract tools
  - Provincial draws / round cutoffs handled separately in Phase 10.4

Each occupation_master CA record gets a `pnp_eligibility[]` array showing
which provinces have streams targeting that NOC, with stream metadata.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

SOURCE_NAME = "ca_pnp_seed_2026"

# ─── PNP Registry — 11 PNPs with their primary streams + priority NOCs ──────

PNP_REGISTRY: Dict[str, Dict[str, Any]] = {
    "bc_pnp": {
        "id": "bc_pnp",
        "province_code": "BC",
        "name": "British Columbia Provincial Nominee Program",
        "official_url": "https://www.welcomebc.ca/immigrate-to-b-c/about-the-bc-provincial-nominee-program",
        "streams": [
            {"id": "bc_si_skilled", "name": "Skills Immigration — Skilled Worker", "express_entry_linked": False},
            {"id": "bc_si_healthcare", "name": "Skills Immigration — Healthcare Professional", "express_entry_linked": False},
            {"id": "bc_si_technology", "name": "Skills Immigration — Technology", "express_entry_linked": False},
            {"id": "bc_ee", "name": "Express Entry BC", "express_entry_linked": True},
            {"id": "bc_si_entry_level", "name": "Entry Level and Semi-Skilled", "express_entry_linked": False},
        ],
        # Technology stream — 36 NOCs (BC PNP 2026 program guide May 28, 2026)
        "priority_nocs": {
            "bc_si_technology": [
                "10030", "20012", "21100", "21210", "21211", "21220", "21221", "21222",
                "21223", "21230", "21231", "21232", "21233", "21234", "21300", "21301",
                "21310", "21311", "21320", "21399", "22110", "22220", "22221", "22222",
                "22310", "22312", "50011", "51111", "51112", "51120", "52119", "52112",
                "52113", "52120", "53111",
            ],
            "bc_si_healthcare": [
                "31100", "31101", "31102", "31103", "31110", "31111", "31112",
                "31120", "31121", "31200", "31201", "31202", "31203", "31300",
                "31301", "31302", "31303", "32101", "32102", "32103", "32109",
                "32111", "32120", "32121", "32122", "32129", "32200", "32201",
                "33101", "33102", "33103",
            ],
        },
    },
    "oinp": {
        "id": "oinp",
        "province_code": "ON",
        "name": "Ontario Immigrant Nominee Program",
        "official_url": "https://www.ontario.ca/page/ontario-immigrant-nominee-program",
        "streams": [
            {"id": "oinp_hcp", "name": "Human Capital Priorities (HCP)", "express_entry_linked": True},
            {"id": "oinp_skilled_trades", "name": "Skilled Trades Stream", "express_entry_linked": True},
            {"id": "oinp_french", "name": "French-Speaking Skilled Worker", "express_entry_linked": True},
            {"id": "oinp_in_demand", "name": "In-Demand Skills (TEER 4-5)", "express_entry_linked": False},
            {"id": "oinp_masters", "name": "Master's Graduate", "express_entry_linked": False},
            {"id": "oinp_phd", "name": "PhD Graduate", "express_entry_linked": False},
            {"id": "oinp_employer_job_offer", "name": "Employer Job Offer — Foreign Worker", "express_entry_linked": False},
        ],
        "priority_nocs": {
            "oinp_hcp": [
                # 6 core tech NOCs targeted by Ontario tech draws
                "21231", "21232", "21311", "21233", "21223", "20012",
                # Plus all FSWP/CEC eligible (TEER 0-3) qualify via the stream
            ],
            "oinp_in_demand": [
                # TEER 4-5 occupations per 2026 OINP update
                "75101",  # Shippers and receivers
                "73400",  # Production logistics workers
                "44101",  # Home support workers (housekeepers)
                "75200",  # Material handlers
                "75110",  # Construction trades helpers and labourers
                "75119",  # Other trades helpers and labourers
                "65310",  # Food and beverage servers (some categories)
            ],
        },
    },
    "aaip": {
        "id": "aaip",
        "province_code": "AB",
        "name": "Alberta Advantage Immigration Program",
        "official_url": "https://www.alberta.ca/aaip-application-streams",
        "streams": [
            {"id": "aaip_ee", "name": "Alberta Express Entry Stream", "express_entry_linked": True},
            {"id": "aaip_opportunity", "name": "Alberta Opportunity Stream", "express_entry_linked": False},
            {"id": "aaip_rural_renewal", "name": "Rural Renewal Stream", "express_entry_linked": False},
            {"id": "aaip_tourism_hospitality", "name": "Tourism and Hospitality Stream", "express_entry_linked": False},
            {"id": "aaip_self_employed_farmer", "name": "Self-Employed Farmer Stream", "express_entry_linked": False},
            {"id": "aaip_accelerated_tech", "name": "Accelerated Tech Pathway", "express_entry_linked": True},
        ],
        "priority_nocs": {
            "aaip_accelerated_tech": [
                "21100", "21210", "21211", "21220", "21221", "21222", "21223",
                "21230", "21231", "21232", "21233", "21234", "21311", "20012",
                "22220", "22221", "22222",
            ],
            "aaip_ee": [
                # 2026 known target sectors: construction, healthcare, tech, agriculture
                "21300", "21301", "21311",  # Construction-related engineers
                "31301", "31302", "32101",  # Nurses
                "70010", "70011",  # Construction managers
                "63200", "63201",  # Chefs, cooks (tourism)
                "85100", "85101",  # Agriculture workers
            ],
        },
    },
    "sinp": {
        "id": "sinp",
        "province_code": "SK",
        "name": "Saskatchewan Immigrant Nominee Program",
        "official_url": "https://www.saskatchewan.ca/residents/moving-to-saskatchewan/immigrating-to-saskatchewan/saskatchewan-immigrant-nominee-program",
        "streams": [
            {"id": "sinp_ee", "name": "Express Entry Stream", "express_entry_linked": True},
            {"id": "sinp_occupation_in_demand", "name": "Occupation In-Demand Sub-Category", "express_entry_linked": False},
            {"id": "sinp_employment_offer", "name": "Employment Offer", "express_entry_linked": False},
            {"id": "sinp_entrepreneur", "name": "Entrepreneur Stream", "express_entry_linked": False},
            {"id": "sinp_farm_owner", "name": "Farm Owner and Operator", "express_entry_linked": False},
        ],
        "priority_nocs": {
            "sinp_occupation_in_demand": [
                # SINP commonly-listed in-demand NOCs (2025-26)
                "31301", "31302", "32101",  # Nurses
                "21231", "21232",  # SW engineers/developers
                "72106", "72200", "72201", "72310", "72400",  # Trades
                "82021",  # Oil and gas supervisors (SK staple)
            ],
        },
    },
    "mpnp": {
        "id": "mpnp",
        "province_code": "MB",
        "name": "Manitoba Provincial Nominee Program",
        "official_url": "https://immigratemanitoba.com",
        "streams": [
            {"id": "mpnp_swm", "name": "Skilled Worker in Manitoba", "express_entry_linked": False},
            {"id": "mpnp_swo", "name": "Skilled Worker Overseas (Strategic Recruitment Initiative)", "express_entry_linked": False},
            {"id": "mpnp_ies", "name": "International Education Stream", "express_entry_linked": False},
            {"id": "mpnp_business", "name": "Business Investor Stream", "express_entry_linked": False},
        ],
        "priority_nocs": {
            "mpnp_swo": [
                # Manitoba 2025-26 in-demand sectors
                "31301", "31302",  # Nurses
                "21231", "21232",  # Tech
                "72106", "72200", "72310", "72400",  # Trades
                "63200", "63201",  # Chefs/cooks (Winnipeg hospitality)
                "73300",  # Truck drivers
            ],
        },
    },
    "nbpnp": {
        "id": "nbpnp",
        "province_code": "NB",
        "name": "New Brunswick Provincial Nominee Program",
        "official_url": "https://www.welcomenb.ca/content/wel-bien/en/immigrating_and_settling/immigration.html",
        "streams": [
            {"id": "nbpnp_ee", "name": "Express Entry Labour Market Stream", "express_entry_linked": True},
            {"id": "nbpnp_skilled_worker_offer", "name": "Skilled Worker with Employer Support", "express_entry_linked": False},
            {"id": "nbpnp_business", "name": "Entrepreneurial Stream", "express_entry_linked": False},
            {"id": "nbpnp_critical_workforce", "name": "Critical Worker Pilot", "express_entry_linked": False},
        ],
        "priority_nocs": {
            "nbpnp_ee": [
                # NB 2026 priority sectors: healthcare, IT, trades, hospitality
                "31301", "31302", "32101",
                "21231", "21232",
                "72106", "72200", "72310", "72400",
                "63200", "63201",
            ],
        },
    },
    "nsnp": {
        "id": "nsnp",
        "province_code": "NS",
        "name": "Nova Scotia Nominee Program",
        "official_url": "https://novascotiaimmigration.com/move-here/",
        "streams": [
            {"id": "nsnp_labour_market_priorities", "name": "Labour Market Priorities", "express_entry_linked": True},
            {"id": "nsnp_physician", "name": "Labour Market Priorities for Physicians", "express_entry_linked": True},
            {"id": "nsnp_critical_construction", "name": "Critical Construction Worker Pilot", "express_entry_linked": False},
            {"id": "nsnp_skilled_worker", "name": "Skilled Worker Stream", "express_entry_linked": False},
            {"id": "nsnp_entrepreneur", "name": "Entrepreneur Stream", "express_entry_linked": False},
        ],
        "priority_nocs": {
            "nsnp_physician": ["31100", "31101", "31102"],
            "nsnp_critical_construction": [
                "70010", "70011",
                "72100", "72102", "72106",
                "72200", "72201", "72300", "72310", "72311", "72320",
                "72400", "72401", "72402",
            ],
        },
    },
    "pei_pnp": {
        "id": "pei_pnp",
        "province_code": "PE",
        "name": "Prince Edward Island Provincial Nominee Program",
        "official_url": "https://www.princeedwardisland.ca/en/topic/office-of-immigration",
        "streams": [
            {"id": "pei_pnp_labour_impact", "name": "Labour Impact Category", "express_entry_linked": False},
            {"id": "pei_pnp_ee", "name": "PEI Express Entry Stream", "express_entry_linked": True},
            {"id": "pei_pnp_business", "name": "Business Impact (Work Permit + Entrepreneur)", "express_entry_linked": False},
        ],
        "priority_nocs": {
            "pei_pnp_ee": [
                # PEI 2025-26 invitations focus heavily on healthcare and trades
                "31301", "31302",
                "72106", "72200", "72310",
                "63200", "63201",
            ],
        },
    },
    "nlpnp": {
        "id": "nlpnp",
        "province_code": "NL",
        "name": "Newfoundland and Labrador Provincial Nominee Program",
        "official_url": "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/",
        "streams": [
            {"id": "nlpnp_ee_skilled", "name": "Express Entry Skilled Worker", "express_entry_linked": True},
            {"id": "nlpnp_skilled_worker", "name": "Skilled Worker (Employer Job Offer)", "express_entry_linked": False},
            {"id": "nlpnp_international_grad", "name": "International Graduate Stream", "express_entry_linked": False},
            {"id": "nlpnp_priority_skills", "name": "Priority Skills NL Stream", "express_entry_linked": False},
        ],
        "priority_nocs": {
            "nlpnp_priority_skills": [
                # NL 2025-26 focus: aquaculture, healthcare, marine
                "31301", "31302",
                "21231", "21232",
                "82031",  # Aquaculture managers
            ],
        },
    },
    "ynp": {
        "id": "ynp",
        "province_code": "YT",
        "name": "Yukon Nominee Program",
        "official_url": "https://yukon.ca/en/employment/permits-and-nominee-program/find-out-if-you-can-apply-yukon-nominee-program",
        "streams": [
            {"id": "ynp_ee", "name": "Express Entry — Yukon", "express_entry_linked": True},
            {"id": "ynp_skilled", "name": "Skilled Worker", "express_entry_linked": False},
            {"id": "ynp_critical_impact", "name": "Critical Impact Worker (TEER 4-5)", "express_entry_linked": False},
            {"id": "ynp_business", "name": "Business Nominee", "express_entry_linked": False},
        ],
        "priority_nocs": {
            "ynp_critical_impact": [
                # Yukon TEER 4-5 focus on services + retail + hospitality
                "65100",  # Cashiers
                "65310",  # Food and beverage servers
                "65329",  # Other food counter servers
                "75101",
            ],
        },
    },
    "ntnp": {
        "id": "ntnp",
        "province_code": "NT",
        "name": "Northwest Territories Nominee Program",
        "official_url": "https://www.immigratenwt.ca",
        "streams": [
            {"id": "ntnp_ee", "name": "Express Entry NWT", "express_entry_linked": True},
            {"id": "ntnp_skilled_worker", "name": "Skilled Worker (Employer-Driven)", "express_entry_linked": False},
            {"id": "ntnp_critical_impact", "name": "Critical Impact Worker (TEER 4-5)", "express_entry_linked": False},
            {"id": "ntnp_business", "name": "Business Stream", "express_entry_linked": False},
        ],
        "priority_nocs": {
            "ntnp_skilled_worker": [
                # NWT 2025-26 sectors: mining, healthcare, trades
                "31301", "31302",
                "82010",  # Mining managers
                "72106", "72200", "72310", "72400",
                "63200", "63201",
            ],
        },
    },
}


# ─── Apply to DB ────────────────────────────────────────────────────────────

async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Tag every CA `occupation_master` record with its `pnp_eligibility[]`.

    Output shape per occupation:
      pnp_eligibility: [
        {
          "province_code": "BC",
          "province_name": "British Columbia Provincial Nominee Program",
          "pnp_id": "bc_pnp",
          "streams": [
            {"id": "bc_si_technology", "name": "Skills Immigration — Technology", "ee_linked": false},
            ...
          ],
          "priority": true,  // currently in priority NOC list (recruiter signal)
          "official_url": "..."
        },
        ...
      ]
    """
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc)

    # Step 1: Build per-NOC index — which PNPs target this NOC and via which streams?
    per_noc: Dict[str, List[Dict[str, Any]]] = {}
    for pnp_id, pnp in PNP_REGISTRY.items():
        # Collect per-stream NOCs
        for stream_id, noc_list in (pnp.get("priority_nocs") or {}).items():
            stream_meta = next((s for s in pnp["streams"] if s["id"] == stream_id), None)
            if not stream_meta:
                continue
            for code in noc_list:
                per_noc.setdefault(code, [])
                # Find or create the PNP-level entry
                existing = next((e for e in per_noc[code] if e["pnp_id"] == pnp_id), None)
                if existing:
                    existing["streams"].append({
                        "id": stream_id,
                        "name": stream_meta["name"],
                        "ee_linked": stream_meta.get("express_entry_linked", False),
                    })
                else:
                    per_noc[code].append({
                        "pnp_id": pnp_id,
                        "province_code": pnp["province_code"],
                        "province_name": pnp["name"],
                        "official_url": pnp["official_url"],
                        "priority": True,
                        "streams": [{
                            "id": stream_id,
                            "name": stream_meta["name"],
                            "ee_linked": stream_meta.get("express_entry_linked", False),
                        }],
                    })

    # Step 2: Apply to each CA record
    updated = 0
    skipped_unchanged = 0
    untagged_codes_count = 0
    total = 0

    async for d in coll.find({"country_code": "CA"}, {"_id": 0, "code": 1, "pnp_eligibility": 1}):
        total += 1
        code = d.get("code")
        new_pnps = per_noc.get(code, [])
        existing_pnps = d.get("pnp_eligibility") or []

        # Idempotency check: serialize-compare
        if new_pnps == existing_pnps:
            skipped_unchanged += 1
        else:
            if not dry_run:
                await coll.update_one(
                    {"country_code": "CA", "code": code},
                    {"$set": {
                        "pnp_eligibility": new_pnps,
                        "pnp_eligibility_last_synced_at": now,
                        "updated_at": now,
                    }},
                )
            updated += 1

        if not new_pnps:
            untagged_codes_count += 1

    # Stats summary
    pnp_summary = {}
    for pnp_id, pnp in PNP_REGISTRY.items():
        all_nocs: Set[str] = set()
        for stream_nocs in (pnp.get("priority_nocs") or {}).values():
            all_nocs.update(stream_nocs)
        pnp_summary[pnp_id] = {
            "province_code": pnp["province_code"],
            "name": pnp["name"],
            "streams_count": len(pnp["streams"]),
            "priority_nocs_tagged": len(all_nocs),
        }

    return {
        "source": SOURCE_NAME,
        "dry_run": dry_run,
        "total_ca_codes_processed": total,
        "counts": {
            "updated": updated,
            "skipped_unchanged": skipped_unchanged,
            "untagged_codes": untagged_codes_count,
        },
        "total_pnps_registered": len(PNP_REGISTRY),
        "pnp_summary": pnp_summary,
        "ran_at": now.isoformat(),
        "actor": actor,
    }
