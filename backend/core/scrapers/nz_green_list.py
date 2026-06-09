"""Phase 12.1 — NZ Green List Tier 1 (Straight to Residence) + Tier 2 (Work to Residence).

The Green List is Immigration NZ's published list of high-priority occupations
that bypass the regular SMC 6-point system:

  • Tier 1 (Straight to Residence) — ~85 occupations; apply for residence
    immediately if you have a qualifying job offer.
  • Tier 2 (Work to Residence) — ~22 occupations; work in role for 24 months
    on an AEWV before applying for residence.

Replaces the older LTSSL (Long Term Skill Shortage List) and RSSL (Regional Skill
Shortage List) which were retired in 2022.

This is a DETERMINISTIC classifier (no scraping, no network calls).
List sourced verbatim from immigration.govt.nz official 2026 Green List pages.

Outputs per occupation_master record:
  • nz_green_list_tier: 1 | 2 | null
  • nz_residence_pathway: "straight_to_residence" | "work_to_residence_24mo" | null
  • visa_pathways.visa_eligibility[Green-T1].eligible: bool
  • visa_pathways.visa_eligibility[Green-T2].eligible: bool
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

SOURCE_NAME = "nz_green_list_2026"
SOURCE_URL = "https://www.immigration.govt.nz/work/requirements-for-work-visas/green-list-occupations-qualifications-and-skills/green-list-roles-jobs-we-need-people-for-in-new-zealand/"

# ─── Tier 1 — Straight to Residence (Apr 2026 official list) ────────────────
GREEN_LIST_TIER_1: Set[str] = {
    # Construction & Engineering
    "133111",  # Construction Project Manager
    "133211",  # Engineering Manager
    "232112",  # Landscape Architect
    "232111",  # Architect
    "232212",  # Surveyor
    "232611",  # Urban and Regional Planner
    "233111",  # Chemical Engineer
    "233112",  # Materials Engineer
    "233211",  # Civil Engineer
    "233212",  # Geotechnical Engineer
    "233213",  # Quantity Surveyor
    "233214",  # Structural Engineer
    "233215",  # Transport Engineer
    "233311",  # Electrical Engineer
    "233411",  # Electronics Engineer
    "233511",  # Industrial Engineer
    "233512",  # Mechanical Engineer
    "233513",  # Production or Plant Engineer
    "233611",  # Mining Engineer (excl Petroleum)
    "233612",  # Petroleum Engineer
    "233911",  # Aeronautical Engineer
    "233912",  # Agricultural Engineer
    "233913",  # Biomedical Engineer
    "233915",  # Environmental Engineer
    "233916",  # Naval Architect
    "312211",  # Civil Engineering Technician

    # ICT
    "261111",  # ICT Business Analyst
    "261112",  # Systems Analyst
    "261311",  # Analyst Programmer
    "261312",  # Developer Programmer
    "261313",  # Software Engineer
    "261314",  # Software Tester
    "262111",  # Database Administrator
    "262112",  # ICT Security Specialist
    "262113",  # Systems Administrator
    "263111",  # Computer Network and Systems Engineer
    "263113",  # Network Analyst
    "263211",  # ICT Quality Assurance Engineer
    "263212",  # ICT Support Engineer
    "263213",  # ICT Systems Test Engineer

    # Health — Doctors & Specialists
    "253111",  # General Practitioner
    "253112",  # Resident Medical Officer
    "253211",  # Anaesthetist
    "253311",  # Specialist Physician
    "253312",  # Cardiologist
    "253313",  # Clinical Haematologist
    "253314",  # Medical Oncologist
    "253315",  # Endocrinologist
    "253316",  # Gastroenterologist
    "253317",  # Intensive Care Specialist
    "253318",  # Neurologist
    "253321",  # Paediatrician
    "253322",  # Renal Medicine Specialist
    "253323",  # Rheumatologist
    "253324",  # Thoracic Medicine Specialist
    "253399",  # Specialist Physicians nec
    "253411",  # Psychiatrist
    "253511",  # Surgeon (General)
    "253512",  # Cardiothoracic Surgeon
    "253513",  # Neurosurgeon
    "253514",  # Orthopaedic Surgeon
    "253515",  # Otorhinolaryngologist
    "253516",  # Paediatric Surgeon
    "253517",  # Plastic and Reconstructive Surgeon
    "253518",  # Urologist
    "253521",  # Vascular Surgeon
    "253911",  # Dermatologist
    "253912",  # Emergency Medicine Specialist
    "253913",  # Obstetrician and Gynaecologist
    "253914",  # Ophthalmologist
    "253915",  # Pathologist
    "253916",  # Diagnostic and Interventional Radiologist
    "253917",  # Radiation Oncologist
    "253999",  # Medical Practitioners nec

    # Health — Allied
    "251211",  # Medical Diagnostic Radiographer
    "251212",  # Medical Radiation Therapist
    "251213",  # Nuclear Medicine Technologist
    "251214",  # Sonographer
    "251411",  # Optometrist
    "251911",  # Health Promotion Officer
    "252213",  # Occupational Therapist (alt code)
    "252411",  # Occupational Therapist
    "252511",  # Physiotherapist
    "252611",  # Podiatrist
    "252711",  # Audiologist
    "252712",  # Speech Pathologist / Therapist
    "254111",  # Midwife
    "254411",  # Nurse Practitioner

    # Education
    "134311",  # School Principal
    "241111",  # Early Childhood Teacher
    "241511",  # Special Needs Teacher
}

# ─── Tier 2 — Work to Residence (24 months) ─────────────────────────────────
GREEN_LIST_TIER_2: Set[str] = {
    # Trades & Technical
    "321211",  # Motor Mechanic (General)
    "321212",  # Diesel Motor Mechanic
    "323111",  # Aircraft Maintenance Engineer (Avionics)
    "323112",  # Aircraft Maintenance Engineer (Mechanical)
    "323113",  # Aircraft Maintenance Engineer (Structures)
    "334111",  # Plumber (General)
    "334113",  # Drainlayer
    "334114",  # Gasfitter
    "341111",  # Electrician (General)
    "341112",  # Electrician (Special Class)
    "342111",  # Airconditioning and Refrigeration Mechanic
    "342414",  # Telecommunications Technician
    # Health Allied
    "254412",  # Registered Nurse (Aged Care)
    "254413",  # Registered Nurse (Child and Family Health)
    "254414",  # Registered Nurse (Community Health)
    "254415",  # Registered Nurse (Critical Care and Emergency)
    "254418",  # Registered Nurse (Medical)
    "254422",  # Registered Nurse (Mental Health)
    "254423",  # Registered Nurse (Perioperative)
    "254424",  # Registered Nurse (Surgical)
    "254499",  # Registered Nurses nec
    # Education
    "241213",  # Primary School Teacher
    "241411",  # Secondary School Teacher
}


def classify(code: str) -> Dict[str, Any]:
    """Return Green List classification for a single ANZSCO code."""
    if code in GREEN_LIST_TIER_1:
        return {
            "nz_green_list_tier": 1,
            "nz_residence_pathway": "straight_to_residence",
            "pathway_notes": (
                "Eligible for the Straight to Residence Visa — apply for residence "
                "directly with a qualifying job offer + meeting wage/qualification rules."
            ),
        }
    if code in GREEN_LIST_TIER_2:
        return {
            "nz_green_list_tier": 2,
            "nz_residence_pathway": "work_to_residence_24mo",
            "pathway_notes": (
                "Eligible for the Work to Residence pathway — apply for residence "
                "after working in the role for 24 months on an AEWV."
            ),
        }
    return {
        "nz_green_list_tier": None,
        "nz_residence_pathway": None,
        "pathway_notes": (
            "Not on the Green List. Pathway to residence via the SMC 6-point system "
            "or AEWV + future SMC application."
        ),
    }


def _update_visa_pathways(existing_visa_pathways: Dict[str, Any], tier: int | None) -> Dict[str, Any]:
    """Flip Green-T1 / Green-T2 booleans in the visa_eligibility[] array."""
    vp = dict(existing_visa_pathways or {})
    rows = list(vp.get("visa_eligibility") or [])
    if not rows:
        rows = [
            {"visa_subclass": "SMC",      "eligible": False, "list": "Federal", "notes": ""},
            {"visa_subclass": "Green-T1", "eligible": False, "list": "Federal", "notes": ""},
            {"visa_subclass": "Green-T2", "eligible": False, "list": "Federal", "notes": ""},
            {"visa_subclass": "AEWV",     "eligible": False, "list": "Federal", "notes": ""},
        ]
    by_sub = {r.get("visa_subclass"): r for r in rows}

    if "Green-T1" not in by_sub:
        rows.append({"visa_subclass": "Green-T1", "eligible": False, "list": "Federal", "notes": ""})
        by_sub["Green-T1"] = rows[-1]
    if "Green-T2" not in by_sub:
        rows.append({"visa_subclass": "Green-T2", "eligible": False, "list": "Federal", "notes": ""})
        by_sub["Green-T2"] = rows[-1]

    by_sub["Green-T1"]["eligible"] = (tier == 1)
    by_sub["Green-T2"]["eligible"] = (tier == 2)
    vp["visa_eligibility"] = rows
    if "pathway_lists" not in vp:
        vp["pathway_lists"] = ["Federal"]
    return vp


async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Tag every NZ ANZSCO record with Green List tier + residence pathway."""
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc)

    total = 0
    updated = 0
    skipped_unchanged = 0
    tier1_count = 0
    tier2_count = 0
    nontier_count = 0

    async for d in coll.find(
        {"country_code": "NZ"},
        {"_id": 0, "code": 1, "nz_green_list_tier": 1, "nz_residence_pathway": 1, "visa_pathways": 1},
    ):
        total += 1
        code = d.get("code")
        if not code:
            continue

        new = classify(code)
        tier = new["nz_green_list_tier"]
        if tier == 1:
            tier1_count += 1
        elif tier == 2:
            tier2_count += 1
        else:
            nontier_count += 1

        existing_tier = d.get("nz_green_list_tier")
        existing_pathway = d.get("nz_residence_pathway")
        existing_vp = d.get("visa_pathways") or {}
        existing_t1 = next((r.get("eligible") for r in (existing_vp.get("visa_eligibility") or []) if r.get("visa_subclass") == "Green-T1"), None)
        existing_t2 = next((r.get("eligible") for r in (existing_vp.get("visa_eligibility") or []) if r.get("visa_subclass") == "Green-T2"), None)

        already_synced = (
            existing_tier == tier
            and existing_pathway == new["nz_residence_pathway"]
            and existing_t1 == (tier == 1)
            and existing_t2 == (tier == 2)
        )
        if already_synced:
            skipped_unchanged += 1
            continue

        new_vp = _update_visa_pathways(existing_vp, tier)

        if not dry_run:
            await coll.update_one(
                {"country_code": "NZ", "code": code},
                {"$set": {
                    "nz_green_list_tier": tier,
                    "nz_residence_pathway": new["nz_residence_pathway"],
                    "nz_pathway_notes": new["pathway_notes"],
                    "visa_pathways": new_vp,
                    "updated_at": now,
                }},
            )
        updated += 1

    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "dry_run": dry_run,
        "version": "2026-Q1",
        "totals": {
            "nz_records_processed": total,
            "tier_1_count": tier1_count,
            "tier_2_count": tier2_count,
            "non_tier_count": nontier_count,
        },
        "counts": {
            "updated": updated,
            "skipped_unchanged": skipped_unchanged,
        },
        "ran_at": now.isoformat(),
        "actor": actor,
        "legacy_note": (
            "LTSSL (Long Term Skill Shortage List) and RSSL (Regional Skill Shortage List) "
            "were retired in 2022 — replaced by Green List Tier 2 and AEWV occupation tagging."
        ),
    }
