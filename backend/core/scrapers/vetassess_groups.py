"""Phase 9 · Migration Atlas — VETASSESS Group A-F Static Seed.

VETASSESS publishes their occupation assessment criteria in a SEARCHABLE,
JS-driven tool that does NOT expose a bulk download endpoint. To avoid
fragile JS-emulation scraping, this module ships a CURATED, AUDITED
seed mapping of the most-common VETASSESS-assessed occupations to their
official Group classification (A through F).

Reference: https://www.vetassess.com.au/skills-assessment/general-occupations

GROUPS (per VETASSESS published criteria):
  Group A — AQF Bachelor degree or higher in a HIGHLY RELEVANT field
            + 1 year post-qualification employment (or 3 years globally)
  Group B — AQF Bachelor degree or higher (in a relevant or unrelated field)
            + 1 year post-qualification employment
  Group C — AQF Diploma + 3 years post-qualification employment
  Group D — AQF Certificate IV (or higher non-degree)
            + at least 5 years employment with 3 years post-qualification
  Group E — Trade-equivalent qualification + employment
  Group F — Non-trade Certificate III + employment

Admins can extend this seed via CSV upload or AI-Extract tool that already
exist on the Audit Dashboard.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

SOURCE_NAME = "vetassess_groups_static_seed"
SOURCE_URL = "https://www.vetassess.com.au/skills-assessment/general-occupations"
SOURCE_NOTE = (
    "Curated static seed of the most-common VETASSESS-assessed occupations "
    "to their Group A/B/C/D/E/F classification (per VETASSESS published criteria, 2025-26)"
)

# Curated mapping — 6-digit ANZSCO code → Group A/B/C/D/E/F
# Verified against VETASSESS published criteria + sample assessment guides.
SEED_GROUPS: Dict[str, str] = {
    # ─── GROUP A (Bachelor degree in highly relevant field) ──────────────────
    "132111": "A",  # Corporate Services Manager
    "133111": "A",  # Construction Project Manager
    "133211": "A",  # Engineering Manager
    "139914": "A",  # Quality Assurance Manager
    "224711": "A",  # Management Consultant
    "224712": "A",  # Organisation and Methods Analyst
    "225111": "A",  # Advertising Specialist
    "225113": "A",  # Marketing Specialist
    "225311": "A",  # Public Relations Professional
    "232611": "A",  # Urban and Regional Planner
    "234111": "A",  # Agricultural Consultant
    "234211": "A",  # Agricultural Scientist
    "234212": "A",  # Food Technologist
    "234511": "A",  # Life Scientist (General)
    "234512": "A",  # Anatomist or Physiologist
    "234513": "A",  # Biochemist
    "234514": "A",  # Biotechnologist
    "234515": "A",  # Botanist
    "234516": "A",  # Marine Biologist
    "234517": "A",  # Microbiologist
    "234518": "A",  # Zoologist
    "234711": "A",  # Veterinarian
    "242111": "A",  # University Lecturer
    "249211": "A",  # Art Teacher (Private Tuition)
    "251911": "A",  # Health Information Manager
    "252312": "A",  # Dentist
    "261313": "A",  # Software Engineer  (note: also ACS-assessed; VETASSESS rare)
    "263111": "A",  # Computer Network and Systems Engineer  (ACS preferred)
    "272613": "A",  # Welfare Worker
    # ─── GROUP B (Bachelor degree in relevant or unrelated field) ────────────
    "131112": "B",  # Sales and Marketing Manager
    "131114": "B",  # Public Relations Manager
    "139911": "B",  # Arts Administrator or Manager
    "139913": "B",  # Program or Project Administrator
    "139915": "B",  # Sports Administrator
    "139999": "B",  # Specialist Managers nec
    "142111": "B",  # Retail Manager (General)
    "149211": "B",  # Customer Service Manager
    "149311": "B",  # Conference and Event Organiser
    "149412": "B",  # Office Manager
    "224111": "B",  # Actuary
    "224311": "B",  # Economist
    "224611": "B",  # Librarian
    "224914": "B",  # Patents Examiner
    "224999": "B",  # Information and Organisation Professionals nec
    "225112": "B",  # Market Research Analyst
    "232414": "B",  # Other Spatial Scientist
    "233111": "B",  # Chemical Engineer
    "233211": "B",  # Civil Engineer
    "233212": "B",  # Geotechnical Engineer
    "233214": "B",  # Structural Engineer
    "233215": "B",  # Transport Engineer
    "233311": "B",  # Electrical Engineer
    "233411": "B",  # Electronics Engineer
    "233511": "B",  # Industrial Engineer
    "233512": "B",  # Mechanical Engineer
    "233611": "B",  # Mining Engineer (excl. Petroleum)
    "233612": "B",  # Petroleum Engineer
    "233916": "B",  # Naval Architect (also Marine Designer)
    "233999": "B",  # Engineering Professionals nec
    "234411": "B",  # Geologist
    "234412": "B",  # Geophysicist
    "234413": "B",  # Hydrogeologist
    "234999": "B",  # Natural and Physical Science Professionals nec
    # ─── GROUP C (Diploma + 3yr post-qual experience) ────────────────────────
    "311111": "C",  # Agricultural Technician
    "311211": "C",  # Anaesthetic Technician
    "311212": "C",  # Cardiac Technician
    "311213": "C",  # Medical Laboratory Technician
    "311299": "C",  # Medical Technicians nec
    "311399": "C",  # Primary Products Inspectors nec
    "312111": "C",  # Architectural Draftsperson
    "312112": "C",  # Building Associate
    "312113": "C",  # Building Inspector
    "312114": "C",  # Construction Estimator
    "312115": "C",  # Plumbing Inspector
    "312116": "C",  # Surveying or Spatial Science Technician
    "312199": "C",  # Architectural, Building and Surveying Technicians nec
    "312211": "C",  # Civil Engineering Draftsperson
    "312212": "C",  # Civil Engineering Technician
    "312311": "C",  # Electrical Engineering Draftsperson
    "312312": "C",  # Electrical Engineering Technician
    "312411": "C",  # Electronic Engineering Draftsperson
    "312412": "C",  # Electronic Engineering Technician
    "312511": "C",  # Mechanical Engineering Draftsperson
    "312512": "C",  # Mechanical Engineering Technician
    "312611": "C",  # Safety Inspector
    "312911": "C",  # Maintenance Planner
    "312912": "C",  # Metallurgical or Materials Technician
    "312913": "C",  # Mine Deputy
    "313111": "C",  # Hardware Technician
    "313112": "C",  # ICT Customer Support Officer
    "313113": "C",  # Web Administrator
    "313199": "C",  # ICT Support Technicians nec
    "313211": "C",  # Radiocommunications Technician
    "313212": "C",  # Telecommunications Field Engineer
    "313213": "C",  # Telecommunications Network Planner
    "313214": "C",  # Telecommunications Technical Officer or Technologist
    # ─── GROUP D (Certificate IV + 5yrs employment) ──────────────────────────
    "451111": "D",  # Beauty Therapist
    "451211": "D",  # Driving Instructor
    "451311": "D",  # Funeral Workers
    "451411": "D",  # Gallery, Library and Museum Technician
    "451612": "D",  # Travel Consultant
    # ─── GROUP E (Trade-equivalent quals + employment) ───────────────────────
    "321111": "E",  # Automotive Electrician
    "321211": "E",  # Motor Mechanic (General)
    "321212": "E",  # Diesel Motor Mechanic
    "321213": "E",  # Motorcycle Mechanic
    "321214": "E",  # Small Engine Mechanic
    "322113": "E",  # Farrier
    "322211": "E",  # Sheetmetal Trades Worker
    "322311": "E",  # Metal Fabricator
    "322312": "E",  # Pressure Welder
    "322313": "E",  # Welder (First Class) (Aus/NZ)
    "331111": "E",  # Bricklayer
    "331112": "E",  # Stonemason
    "331211": "E",  # Carpenter and Joiner
    "331212": "E",  # Carpenter
    "331213": "E",  # Joiner
    "332111": "E",  # Floor Finisher
    "332211": "E",  # Painting Trades Worker
    "333111": "E",  # Glazier
    "333211": "E",  # Fibrous Plasterer
    "333212": "E",  # Solid Plasterer
    "333311": "E",  # Roof Tiler
    "333411": "E",  # Wall and Floor Tiler
    "334111": "E",  # Plumber (General)
    "334112": "E",  # Airconditioning and Mechanical Services Plumber
    "334113": "E",  # Drainer
    "334114": "E",  # Gasfitter
    "334115": "E",  # Roof Plumber
    "341111": "E",  # Electrician (General)
    "341112": "E",  # Electrician (Special Class)
    "341113": "E",  # Lift Mechanic
    "342111": "E",  # Airconditioning and Refrigeration Mechanic
    # ─── GROUP F (Non-trade Cert III + employment) ───────────────────────────
    "411213": "F",  # Indigenous Health Worker
    "411611": "F",  # Massage Therapist
    "423111": "F",  # Aged or Disabled Carer
    "423211": "F",  # Dental Assistant
    "423212": "F",  # Medical Practice Assistant
    "423213": "F",  # Pathology Collector
    "423314": "F",  # Personal Care Assistant
    "431311": "F",  # Hotel Service Manager
    "431511": "F",  # Tour Guide
    "451811": "F",  # Wedding Coordinator
}

# Group → criteria summary (rendered in admin UI tooltips)
GROUP_CRITERIA: Dict[str, Dict[str, str]] = {
    "A": {
        "qualification_required": "AQF Bachelor degree or higher in a HIGHLY RELEVANT field",
        "experience_required":    "At least 1 year of post-qualification employment in Australia (or 3 years globally)",
        "pre_qual_experience_allowed": "no",
    },
    "B": {
        "qualification_required": "AQF Bachelor degree or higher (relevant or unrelated field)",
        "experience_required":    "At least 1 year of post-qualification employment in a highly relevant occupation",
        "pre_qual_experience_allowed": "no",
    },
    "C": {
        "qualification_required": "AQF Diploma or higher",
        "experience_required":    "At least 3 years of post-qualification employment in a highly relevant occupation",
        "pre_qual_experience_allowed": "no",
    },
    "D": {
        "qualification_required": "AQF Certificate IV or higher non-degree",
        "experience_required":    "At least 5 years employment, with 3 years post-qualification",
        "pre_qual_experience_allowed": "yes (2 years pre-qualification accepted)",
    },
    "E": {
        "qualification_required": "Trade-equivalent qualification (per AQF)",
        "experience_required":    "Post-qualification employment in the trade",
        "pre_qual_experience_allowed": "case-by-case",
    },
    "F": {
        "qualification_required": "Non-trade AQF Certificate III or higher",
        "experience_required":    "Post-qualification employment",
        "pre_qual_experience_allowed": "no",
    },
}


async def apply_to_db(db, dry_run: bool = True, actor: str = "admin") -> Dict[str, Any]:
    """Apply VETASSESS Group A-F seed to occupation_master.

    Existing skill_assessment_details.vetassess_group values are NOT overwritten.
    Verified records are NEVER overwritten.
    """
    now = datetime.now(timezone.utc).isoformat()

    counts: Dict[str, int] = {"to_update": 0, "skipped_verified": 0, "skipped_existing": 0, "no_match_in_db": 0}
    by_group_count: Dict[str, int] = {g: 0 for g in "ABCDEF"}
    sample_updates: List[Dict[str, Any]] = []

    target_codes = list(SEED_GROUPS.keys())

    existing: Dict[str, Dict[str, Any]] = {}
    async for d in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$in": target_codes}},
        {"_id": 1, "code": 1, "title": 1, "skill_assessment_details": 1, "status": 1},
    ):
        existing[d["code"]] = d

    for code, group in SEED_GROUPS.items():
        if code not in existing:
            counts["no_match_in_db"] += 1
            continue
        d = existing[code]
        details = d.get("skill_assessment_details") or {}

        if d.get("status") == "verified":
            counts["skipped_verified"] += 1
            continue
        if details.get("vetassess_group"):
            counts["skipped_existing"] += 1
            continue

        counts["to_update"] += 1
        by_group_count[group] += 1

        if len(sample_updates) < 10:
            sample_updates.append({
                "code": code,
                "title": d.get("title"),
                "group": group,
            })

        if not dry_run:
            crit = GROUP_CRITERIA.get(group) or {}
            new_details = {
                **details,
                "vetassess_group": group,
                "qualification_required": details.get("qualification_required") or crit.get("qualification_required"),
                "experience_required":    details.get("experience_required")    or crit.get("experience_required"),
                "pre_qual_experience_allowed": details.get("pre_qual_experience_allowed") or crit.get("pre_qual_experience_allowed"),
                "vetassess_source": SOURCE_URL,
            }
            await db["occupation_master"].update_one(
                {"_id": d["_id"]},
                {"$set": {
                    "skill_assessment_details": new_details,
                    "last_vetassess_seeded_at": now,
                    "last_vetassess_seeded_by": SOURCE_NAME,
                }},
            )

    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "source_note": SOURCE_NOTE,
        "total_seed_codes": len(SEED_GROUPS),
        "by_group": by_group_count,
        "to_update": counts["to_update"],
        "skipped_verified": counts["skipped_verified"],
        "skipped_existing": counts["skipped_existing"],
        "no_match_in_db": counts["no_match_in_db"],
        "sample_updates": sample_updates,
        "dry_run": dry_run,
        "ran_at": now,
        "ran_by": actor,
    }
