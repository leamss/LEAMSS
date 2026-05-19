"""Smart Sales Helper — Rule-based Document Checklist Generator.

Generates a document checklist for a Smart Sales Helper assessment based on:
  • Destination country (AU / CA / NZ / UK / USA / others)
  • Assessing body for occupation (ACS, EA, VETASSESS, WES, ICAS, NZQA, etc.)
  • Marital status (adds spouse docs when married/de_facto)
  • Visa subclass / pathway hints (e.g., AU 189 needs SkillSelect EOI; AU 190 needs state nomination)

Used by:
  GET /api/sales/assessments/{id}/checklist
  GET /api/sales/assessments/public/{token}      (sanitised summary)
"""
from typing import Dict, List, Any

# Country-level base template — these docs are always needed for a skilled migration application
_BASE_BY_COUNTRY: Dict[str, List[dict]] = {
    "AU": [
        {"name": "Passport (bio page + last page)", "category": "Identity", "required": True},
        {"name": "Passport-size photographs (Australian spec, 6 copies)", "category": "Identity", "required": True},
        {"name": "PTE / IELTS / TOEFL score (within 3 years)", "category": "English", "required": True},
        {"name": "All degree certificates + final transcripts", "category": "Education", "required": True},
        {"name": "Employment Reference Letters (with duties, salary, dates)", "category": "Work Experience", "required": True},
        {"name": "Form 16 / Salary Slips / Tax Returns (last 3 years)", "category": "Work Experience", "required": True},
        {"name": "Resume (current, ANZSCO-aligned)", "category": "Work Experience", "required": True},
        {"name": "PCC — Police Clearance Certificate (every country lived 12+ months)", "category": "Character", "required": True},
        {"name": "Medical Examination Report (BUPA Australia panel)", "category": "Medical", "required": False, "note": "After invite (ITA)"},
        {"name": "Birth Certificate", "category": "Identity", "required": True},
        {"name": "Form 80 — Personal Particulars", "category": "Forms", "required": True},
        {"name": "Form 1221 — Additional Personal Particulars", "category": "Forms", "required": False},
    ],
    "CA": [
        {"name": "Passport (all pages)", "category": "Identity", "required": True},
        {"name": "Passport-size photographs (Canadian visa spec)", "category": "Identity", "required": True},
        {"name": "IELTS General / CELPIP General (within 2 years)", "category": "English", "required": True},
        {"name": "ECA — Educational Credential Assessment (WES / ICAS / IQAS)", "category": "Education", "required": True},
        {"name": "All degree certificates + transcripts", "category": "Education", "required": True},
        {"name": "Reference letters (with NOC code, hours/week, duties)", "category": "Work Experience", "required": True},
        {"name": "Salary slips + Tax Returns (last 3 years)", "category": "Work Experience", "required": True},
        {"name": "Proof of funds — 6 months bank statement (CAD 13,757+ for single)", "category": "Funds", "required": True},
        {"name": "PCC — Police Clearance Certificate", "category": "Character", "required": True},
        {"name": "Medical Examination (panel physician)", "category": "Medical", "required": False, "note": "After ITA"},
        {"name": "Marriage Certificate (if applicable)", "category": "Family", "required": False},
        {"name": "Birth Certificate", "category": "Identity", "required": True},
    ],
    "NZ": [
        {"name": "Passport (bio page + recent visa pages)", "category": "Identity", "required": True},
        {"name": "Passport-size photographs", "category": "Identity", "required": True},
        {"name": "IELTS General (overall 6.5, no band < 6.0)", "category": "English", "required": True},
        {"name": "Degree certificates + NZQA assessment", "category": "Education", "required": True},
        {"name": "Employment reference letters (ANZSCO skill level)", "category": "Work Experience", "required": True},
        {"name": "Salary slips + IRD / Form 16 equivalents", "category": "Work Experience", "required": True},
        {"name": "Skill-matched Job Offer from NZ employer (for SMC)", "category": "Job Offer", "required": True, "note": "Required for SMC post-Sept-2023"},
        {"name": "Police Clearance Certificate", "category": "Character", "required": True},
        {"name": "Medical Examination (eMedical)", "category": "Medical", "required": False, "note": "After invite"},
        {"name": "Birth Certificate", "category": "Identity", "required": True},
    ],
    "UK": [
        {"name": "Passport", "category": "Identity", "required": True},
        {"name": "Certificate of Sponsorship (CoS) — issued by UK employer", "category": "Sponsorship", "required": True},
        {"name": "IELTS UKVI (CEFR B1 or above)", "category": "English", "required": True},
        {"name": "Degree certificate (or Ecctis assessment)", "category": "Education", "required": True},
        {"name": "Proof of Funds (£1,270 maintenance, 28 days)", "category": "Funds", "required": True},
        {"name": "TB Test Certificate (from approved clinic)", "category": "Medical", "required": False, "note": "If from listed country"},
        {"name": "Police Clearance Certificate", "category": "Character", "required": True},
        {"name": "Birth Certificate", "category": "Identity", "required": True},
    ],
    "USA": [
        {"name": "Passport (valid 6+ months beyond intended stay)", "category": "Identity", "required": True},
        {"name": "US visa photo (51mm × 51mm)", "category": "Identity", "required": True},
        {"name": "Educational documents (degree + transcripts)", "category": "Education", "required": True},
        {"name": "Experience letters (with duties + salary)", "category": "Work Experience", "required": True},
        {"name": "I-797 Approval Notice (after USCIS petition approval)", "category": "Petition", "required": False, "note": "After H1B selection"},
        {"name": "DS-160 confirmation page", "category": "Forms", "required": True, "note": "After USCIS approval"},
        {"name": "Pay stubs / W-2 / Tax returns (if previously in US)", "category": "Work Experience", "required": False},
    ],
    "DEFAULT": [
        {"name": "Passport (bio page)", "category": "Identity", "required": True},
        {"name": "Language proficiency test (IELTS/PTE/TOEFL)", "category": "English", "required": True},
        {"name": "All degree certificates + transcripts", "category": "Education", "required": True},
        {"name": "Work experience reference letters", "category": "Work Experience", "required": True},
        {"name": "Proof of funds (bank statement)", "category": "Funds", "required": True},
        {"name": "Police Clearance Certificate", "category": "Character", "required": True},
    ],
}


# Occupation-specific skill assessment docs (Australia)
_ASSESSING_BODY_DOCS: Dict[str, List[dict]] = {
    "ACS": [
        {"name": "ACS Skills Assessment Application + RPL Report (if applicable)", "category": "Skill Assessment", "required": True, "fee_native": "AUD 500 (Stage-6) / AUD 1,000-1,450 (RPL)"},
        {"name": "All employment evidence in ACS format", "category": "Skill Assessment", "required": True},
    ],
    "EA": [
        {"name": "Engineers Australia CDR (3 Career Episodes + CPD + Summary)", "category": "Skill Assessment", "required": True, "fee_native": "AUD 1,150 (standard) / AUD 1,800 (CDR fast-track)"},
        {"name": "Continuing Professional Development (CPD) record", "category": "Skill Assessment", "required": True},
    ],
    "VETASSESS": [
        {"name": "VETASSESS Skills Assessment Application", "category": "Skill Assessment", "required": True, "fee_native": "AUD 1,225 (standard) / AUD 2,710 (priority)"},
        {"name": "Detailed CV in VETASSESS format", "category": "Skill Assessment", "required": True},
    ],
    "WES": [
        {"name": "WES (World Education Services) ECA report", "category": "Education", "required": True, "fee_native": "CAD 320"},
        {"name": "Original transcripts sent directly from university to WES", "category": "Education", "required": True},
    ],
    "ICAS": [
        {"name": "ICAS — International Credential Assessment Service report", "category": "Education", "required": True, "fee_native": "CAD 220"},
    ],
    "IQAS": [
        {"name": "IQAS (Alberta) ECA report", "category": "Education", "required": True, "fee_native": "CAD 200"},
    ],
    "NZQA": [
        {"name": "NZQA International Qualifications Assessment", "category": "Education", "required": True, "fee_native": "NZD 866"},
    ],
}


# Pathway-specific add-ons (e.g., AU 190 = state nomination, AU 189 = SkillSelect EOI)
_PATHWAY_DOCS: Dict[str, List[dict]] = {
    "AU_189": [
        {"name": "SkillSelect EOI (Expression of Interest) submission", "category": "Application", "required": True},
        {"name": "Invitation to Apply (ITA) email", "category": "Application", "required": False, "note": "After EOI selection"},
    ],
    "AU_190": [
        {"name": "State Nomination Application (e.g., NSW/VIC/QLD)", "category": "State Nomination", "required": True},
        {"name": "Commitment letter to live in nominated state for 2 years", "category": "State Nomination", "required": True},
    ],
    "AU_491": [
        {"name": "Regional state/territory nomination OR eligible family sponsor", "category": "Regional Nomination", "required": True},
        {"name": "Commitment to regional residence (3 years)", "category": "Regional Nomination", "required": True},
    ],
    "CA_EE": [
        {"name": "Express Entry Profile (online IRCC)", "category": "Application", "required": True},
        {"name": "Comprehensive Ranking System (CRS) score breakdown", "category": "Application", "required": True},
    ],
}


# Spouse-specific docs (added when marital_status in {married, de_facto})
_SPOUSE_DOCS: List[dict] = [
    {"name": "Spouse Passport (bio page)", "category": "Spouse", "required": True},
    {"name": "Marriage Certificate (Hindu Marriage Act / civil)", "category": "Spouse", "required": True},
    {"name": "Marriage photographs (5-10 copies)", "category": "Spouse", "required": True},
    {"name": "Joint bank account / joint utility bills (proof of relationship)", "category": "Spouse", "required": False},
    {"name": "Spouse IELTS / PTE score (for partner points)", "category": "Spouse", "required": False, "note": "For partner points (+5 or +10)"},
    {"name": "Spouse degree certificate + transcripts", "category": "Spouse", "required": False},
    {"name": "Spouse skill assessment (if claiming +10 partner points)", "category": "Spouse", "required": False},
]


def build_checklist(
    country_code: str,
    occupation: dict | None = None,
    marital_status: str | None = None,
    targets: list[dict] | None = None,
) -> dict:
    """Build a deterministic document checklist from an assessment snapshot.

    Returns:
        {
            "template_key": "AU",
            "country_code": "AU",
            "items": [{name, category, required, note?, fee_native?}, ...],
            "categories": ["Identity", "English", ...],
            "stats": {"total": N, "required": M, "categories": K},
        }
    """
    country_code = (country_code or "").upper()
    items: List[dict] = []

    # 1) Base country template
    base = _BASE_BY_COUNTRY.get(country_code, _BASE_BY_COUNTRY["DEFAULT"])
    items.extend([dict(it) for it in base])

    # 2) Occupation-specific skill assessment docs
    if occupation and occupation.get("assessing_body"):
        body = (occupation.get("assessing_body") or "").upper()
        for k, docs in _ASSESSING_BODY_DOCS.items():
            if k in body:
                items.extend([dict(it) for it in docs])
                break

    # 3) Pathway-specific docs (only for AU + CA right now)
    if targets:
        seen_paths = set()
        for t in targets:
            c = (t.get("country") or "").upper()
            sub = str(t.get("visa_subclass") or "").strip()
            path_key = None
            if c == "AU" and sub in ("189", "190", "491"):
                path_key = f"AU_{sub}"
            elif c == "CA":
                path_key = "CA_EE"
            if path_key and path_key not in seen_paths:
                items.extend([dict(it) for it in _PATHWAY_DOCS.get(path_key, [])])
                seen_paths.add(path_key)

    # 4) Spouse docs if married
    if marital_status in ("married", "de_facto"):
        items.extend([dict(it) for it in _SPOUSE_DOCS])

    # Stats
    required = sum(1 for it in items if it.get("required"))
    cats = sorted({it["category"] for it in items})

    return {
        "template_key": country_code,
        "country_code": country_code,
        "items": items,
        "categories": cats,
        "stats": {
            "total": len(items),
            "required": required,
            "optional": len(items) - required,
            "categories": len(cats),
        },
    }
