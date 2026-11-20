"""LEAMSS Occupation Code & Immigration Regulatory Intelligence Engine.

Provides deep regulatory resolution across:
  - Canada NOC 2021 V1.0 (5-digit codes, TEER 0–5, ESDC / IRCC)
  - Australia ANZSCO (6-digit codes, Skill Levels 1–5, DHA / ABS, ACS, EA, VETASSESS)
  - New Zealand ANZSCO / Green List / SMC (6-digit codes, Tier 1/2, INZ)
  - United States SOC / O*NET (XX-XXXX, Prevailing Wages, USCIS / DOL OFLC)
  - United Kingdom SOC 2020 (4-digit codes, Immigration Salary List, UKVI)
  - Germany Positivliste / Shortage Occupations (Mangelberufe, Chancenkarte, EU Blue Card)

Core responsibilities:
  1. Deterministic identification of classification system and home country.
  2. Cross-country mismatch detection (e.g. NOC code queried while viewing Australia).
  3. Full occupation profile retrieval: official title, TEER/Skill Level, definition, duties, assessing body, visa pathways.
  4. Statutory fees, points thresholds, and verification URLs.
  5. Tailored client qualification questions and salesperson scripts.
  6. Structured 7-part response synthesis.
"""
from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Base Paths
BASE_DIR = Path(__file__).resolve().parents[1]
AU_JSON_PATH = BASE_DIR / "data" / "home_affairs_skilled_occupations.json"
NOC_STRUCTURE_CSV = BASE_DIR / "data" / "noc_2021" / "noc-2021-v1.0-classification-structure.csv"
NOC_ELEMENTS_CSV = BASE_DIR / "data" / "noc_2021" / "noc-2021-v1.0-elements.csv"

# In-memory indexes
_AU_INDEX: Dict[str, Dict[str, Any]] = {}
_NOC_INDEX: Dict[str, Dict[str, Any]] = {}
_NOC_ELEMENTS: Dict[str, Dict[str, List[str]]] = {}
_DATA_INITIALIZED = False


def _init_data() -> None:
    global _DATA_INITIALIZED, _AU_INDEX, _NOC_INDEX, _NOC_ELEMENTS
    if _DATA_INITIALIZED:
        return

    # 1. Load Australian Occupations
    if AU_JSON_PATH.exists():
        try:
            with open(AU_JSON_PATH, encoding="utf-8") as f:
                au_raw = json.load(f)
            for item in au_raw:
                raw_code = item.get("anzscocode", "")
                m = re.search(r"\b(\d{6})\b", raw_code)
                if m:
                    code = m.group(1)
                    raw_auth = item.get("assessauth", "")
                    auths = re.findall(r">([A-Za-z0-9\s/]+)<", raw_auth)
                    auth_name = "VETASSESS"
                    for a in auths:
                        a_clean = a.strip()
                        if a_clean and a_clean.upper() in ["ACS", "EA", "VETASSESS", "TRA", "ANMAC", "CPA", "CA ANZ", "IPA", "MEDBA", "AITSL", "AIQS", "AIM"]:
                            auth_name = a_clean.upper()
                            break
                        elif a_clean and len(a_clean) <= 15:
                            auth_name = a_clean

                    visas = [v.strip() for v in item.get("visas", "").split(";") if v.strip()]
                    _AU_INDEX[code] = {
                        "code": code,
                        "title": item.get("occupation", "").strip(),
                        "list": item.get("list", "").strip(),
                        "assessing_body": auth_name,
                        "visas": visas,
                    }
        except Exception as e:
            logger.warning("Could not load AU occupations JSON: %s", e)

    # 2. Load Canadian NOC Structure
    if NOC_STRUCTURE_CSV.exists():
        try:
            with open(NOC_STRUCTURE_CSV, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    c = (row.get("Code - NOC 2021 V1.0") or "").strip()
                    if len(c) == 5:
                        _NOC_INDEX[c] = {
                            "code": c,
                            "title": row.get("Class title", "").strip(),
                            "definition": row.get("Class definition", "").strip(),
                            "teer": int(c[1]) if c[1].isdigit() else 1,
                        }
        except Exception as e:
            logger.warning("Could not load NOC structure CSV: %s", e)

    # 3. Load Canadian NOC Elements (Duties & Requirements)
    if NOC_ELEMENTS_CSV.exists():
        try:
            with open(NOC_ELEMENTS_CSV, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    c = (row.get("Code - NOC 2021 V1.0") or "").strip()
                    if len(c) == 5:
                        etype = (row.get("Element Type Label English") or "").strip()
                        desc = (row.get("Element Description English") or "").strip()
                        if desc and etype in ["Main duties", "Employment requirements"]:
                            if c not in _NOC_ELEMENTS:
                                _NOC_ELEMENTS[c] = {"duties": [], "requirements": []}
                            if etype == "Main duties":
                                _NOC_ELEMENTS[c]["duties"].append(desc)
                            elif etype == "Employment requirements":
                                _NOC_ELEMENTS[c]["requirements"].append(desc)
        except Exception as e:
            logger.warning("Could not load NOC elements CSV: %s", e)

    _DATA_INITIALIZED = True


# Predefined Cross-Walk for common occupations across Canada (NOC), Australia (ANZSCO), UK (SOC), and US (SOC)
CROSSWALK_CATALOG = [
    {
        "keywords": ["software engineer", "developer", "programmer", "software designer", "coding", "full stack"],
        "ca_noc": "21231",
        "ca_title": "Software engineers and designers",
        "ca_teer": 1,
        "ca_body": "WES (ECA)",
        "au_anzsco": "261313",
        "au_title": "Software Engineer",
        "au_skill_level": 1,
        "au_body": "ACS (Australian Computer Society)",
        "uk_soc": "2136",
        "uk_title": "Programmers and software development professionals",
        "us_soc": "15-1252.00",
        "us_title": "Software Developers",
    },
    {
        "keywords": ["data scientist", "data analyst", "database administrator", "database analyst"],
        "ca_noc": "21211",
        "ca_title": "Data scientists",
        "ca_teer": 1,
        "ca_body": "WES (ECA)",
        "au_anzsco": "261399",
        "au_title": "Software and Applications Programmers nec",
        "au_skill_level": 1,
        "au_body": "ACS",
        "uk_soc": "2135",
        "uk_title": "IT business analysts, architects and systems designers",
        "us_soc": "15-2051.00",
        "us_title": "Data Scientists",
    },
    {
        "keywords": ["civil engineer", "structural engineer", "construction engineer"],
        "ca_noc": "21300",
        "ca_title": "Civil engineers",
        "ca_teer": 1,
        "ca_body": "WES (ECA) / Engineers Canada",
        "au_anzsco": "233211",
        "au_title": "Civil Engineer",
        "au_skill_level": 1,
        "au_body": "Engineers Australia (EA)",
        "uk_soc": "2121",
        "uk_title": "Civil engineers",
        "us_soc": "17-2051.00",
        "us_title": "Civil Engineers",
    },
    {
        "keywords": ["mechanical engineer"],
        "ca_noc": "21301",
        "ca_title": "Mechanical engineers",
        "ca_teer": 1,
        "ca_body": "WES (ECA) / Engineers Canada",
        "au_anzsco": "233512",
        "au_title": "Mechanical Engineer",
        "au_skill_level": 1,
        "au_body": "Engineers Australia (EA)",
        "uk_soc": "2122",
        "uk_title": "Mechanical engineers",
        "us_soc": "17-2141.00",
        "us_title": "Mechanical Engineers",
    },
    {
        "keywords": ["electrical engineer", "electronics engineer"],
        "ca_noc": "21310",
        "ca_title": "Electrical and electronics engineers",
        "ca_teer": 1,
        "ca_body": "WES (ECA) / Engineers Canada",
        "au_anzsco": "233311",
        "au_title": "Electrical Engineer",
        "au_skill_level": 1,
        "au_body": "Engineers Australia (EA)",
        "uk_soc": "2123",
        "uk_title": "Electrical engineers",
        "us_soc": "17-2071.00",
        "us_title": "Electrical Engineers",
    },
    {
        "keywords": ["registered nurse", "nurse", "critical care nurse", "emergency nurse"],
        "ca_noc": "31301",
        "ca_title": "Registered nurses and registered psychiatric nurses",
        "ca_teer": 1,
        "ca_body": "NNAS / Provincial Nursing College",
        "au_anzsco": "254499",
        "au_title": "Registered Nurses nec",
        "au_skill_level": 1,
        "au_body": "ANMAC",
        "uk_soc": "2231",
        "uk_title": "Nurses",
        "us_soc": "29-1141.00",
        "us_title": "Registered Nurses",
    },
    {
        "keywords": ["accountant", "auditor", "financial auditor", "chartered accountant"],
        "ca_noc": "11100",
        "ca_title": "Financial auditors and accountants",
        "ca_teer": 1,
        "ca_body": "CPA Canada / WES",
        "au_anzsco": "221111",
        "au_title": "Accountant (General)",
        "au_skill_level": 1,
        "au_body": "CPA Australia / CA ANZ / IPA",
        "uk_soc": "2421",
        "uk_title": "Chartered and certified accountants",
        "us_soc": "13-2011.00",
        "us_title": "Accountants and Auditors",
    },
    {
        "keywords": ["business analyst", "management consultant", "systems analyst"],
        "ca_noc": "21221",
        "ca_title": "Business systems specialists",
        "ca_teer": 1,
        "ca_body": "WES (ECA)",
        "au_anzsco": "261111",
        "au_title": "ICT Business Analyst",
        "au_skill_level": 1,
        "au_body": "ACS",
        "uk_soc": "2423",
        "uk_title": "Management consultants and business analysts",
        "us_soc": "13-1111.00",
        "us_title": "Management Analysts",
    },
    {
        "keywords": ["chef", "head chef", "pastry chef"],
        "ca_noc": "62200",
        "ca_title": "Chefs",
        "ca_teer": 2,
        "ca_body": "Red Seal / WES",
        "au_anzsco": "351311",
        "au_title": "Chef",
        "au_skill_level": 2,
        "au_body": "TRA (Trades Recognition Australia)",
        "uk_soc": "5434",
        "uk_title": "Chefs",
        "us_soc": "35-1011.00",
        "us_title": "Chefs and Head Cooks",
    },
]


def teer_meaning(teer: int) -> str:
    """Explains Canada NOC TEER categories in formal statutory terms."""
    meanings = {
        0: "TEER 0 — Management Occupations: Advertising, marketing, public relations, financial, corporate, and facility managers.",
        1: "TEER 1 — Professional Occupations: Usually require completion of a university degree (Bachelor's, Master's, or Doctorate). Eligible for Federal Skilled Worker (FSW) and Express Entry category draws.",
        2: "TEER 2 — Technical and Skilled Trades: Occupations usually require 2–3 years of post-secondary college/apprenticeship education or supervisory experience.",
        3: "TEER 3 — Intermediate Occupations: Usually require a college diploma (< 2 years) or 6+ months of job training.",
        4: "TEER 4 — Foundational Occupations: Occupations requiring high school diploma or a few weeks of on-the-job training.",
        5: "TEER 5 — Labour / Short-term Occupations: No formal educational requirements; on-the-job work demonstrations.",
    }
    return meanings.get(teer, f"TEER {teer} — Canadian Skill Classification Level")


def anzsco_skill_level_meaning(level: int) -> str:
    """Explains Australian & New Zealand ANZSCO Skill Levels."""
    meanings = {
        1: "ANZSCO Skill Level 1 — Commensurate with a Bachelor's degree or higher qualification (or at least 5 years of relevant experience).",
        2: "ANZSCO Skill Level 2 — Commensurate with an AQF Associate Degree, Advanced Diploma or Diploma (or at least 3 years of relevant experience).",
        3: "ANZSCO Skill Level 3 — Commensurate with an AQF Certificate IV or Certificate III including at least 2 years on-the-job training.",
        4: "ANZSCO Skill Level 4 — Commensurate with an AQF Certificate II or III.",
        5: "ANZSCO Skill Level 5 — Commensurate with an AQF Certificate I or compulsory secondary education.",
    }
    return meanings.get(level, f"ANZSCO Skill Level {level}")


@dataclass
class OccupationDetection:
    code: str
    classification_system: str
    country: str
    country_code: str
    is_mismatch: bool
    selected_country: str
    mismatch_warning: Optional[str] = None
    title: Optional[str] = None
    skill_level: Optional[int] = None
    teer: Optional[int] = None
    assessing_authority: Optional[str] = None
    crosswalk_code: Optional[str] = None
    crosswalk_title: Optional[str] = None
    crosswalk_country: Optional[str] = None
    crosswalk_authority: Optional[str] = None


@dataclass
class FullOccupationProfile:
    code: str
    title: str
    classification_system: str
    country: str
    country_code: str
    skill_tier_label: str
    skill_tier_description: str
    definition: str
    main_duties: List[str]
    employment_requirements: List[str]
    assessing_authority: str
    visa_pathways: List[str]
    statutory_salary_threshold: str
    official_source_url: str
    verification_date: str
    mismatch_advisory: Optional[str] = None
    crosswalk_info: Optional[Dict[str, Any]] = None


@dataclass
class CountryVisaQueryIntent:
    detected_country: str
    country_code: str
    country_source: str  # "query", "subclass", "occupation", "context", "unclear"
    detected_subclass: Optional[str] = None
    visa_category: Optional[str] = None
    is_travel_abroad_pr_query: bool = False
    query_topic: str = "general"  # "fees" | "travel" | "benefits" | "family" | "eligibility" | "process" | "objection" | "general"
    is_unclear: bool = False
    clarification_question: Optional[str] = None
    offshore_onshore_explanation: Optional[str] = None
    mismatch_with_payload: bool = False
    authority_name: Optional[str] = None
    official_portal_url: Optional[str] = None


def normalize_country(country: Optional[str]) -> str:
    if not country:
        return "Australia"
    c_clean = country.strip().lower()
    if c_clean in ["au", "aus", "australia"]:
        return "Australia"
    if c_clean in ["ca", "can", "canada"]:
        return "Canada"
    if c_clean in ["nz", "new zealand", "newzealand"]:
        return "New Zealand"
    if c_clean in ["uk", "united kingdom", "britain", "england"]:
        return "United Kingdom"
    if c_clean in ["us", "usa", "united states", "united states of america", "america"]:
        return "United States"
    if c_clean in ["de", "germany", "deutschland"]:
        return "Germany"
    return country.strip().title()


def detect_country_and_visa_in_query(
    query: str,
    fallback_country: Optional[str] = None,
    fallback_subclass: Optional[str] = None
) -> CountryVisaQueryIntent:
    """Accurately identifies destination country, visa subclass, and query intent directly from the client query.

    Guarantees:
    1. Query country indicators strictly override any mismatched fallback/context country.
    2. Australia PR queries (e.g. 'aus', 'australia', '189', '190', '491') NEVER resolve to USA EB-2 NIW.
    3. Detects offshore vs. onshore travel inquiries for PR and provides statutory clarity.
    4. Detects ambiguous/unclear inquiries and provides a tailored single clarification question.
    """
    q = (query or "").strip()
    q_lower = q.lower()

    # Pre-clean punctuation for word token matching
    q_words = set(re.findall(r"\b[a-z0-9\-]+\b", q_lower))

    # 1. Regex patterns for country identification directly inside query
    au_pattern = r"\b(?:australia|australian|aus|aussie|oz|dha|home\s*affairs|skillselect|vetassess|acs|engineers\s*australia|noaus)\b"
    ca_pattern = r"\b(?:canada|canadian|ircc|express\s*entry|fsw|pnp|oinp|bcpnp|sinp|crs|teer|clb|wes|cec)\b"
    us_pattern = r"\b(?:united\s*states|usa|u\.s\.a?|uscis|h-?1b|l-?1[ab]?|eb-?[1-5]|niw|national\s*interest\s*waiver|opt|cpt|i-?140|i-?485|perm|dol\s*oflc)\b"
    uk_pattern = r"\b(?:united\s*kingdom|uk|britain|british|ukvi|home\s*office|cos|ilr)\b"
    de_pattern = r"\b(?:germany|german|deutschland|chancenkarte|opportunity\s*card|blaue\s*karte|blue\s*card|anabin|bamf)\b"
    nz_pattern = r"\b(?:new\s*zealand|nz|inz|smc|green\s*list|nzqa)\b"

    au_subclass_pattern = r"\b(?:subclass\s*)?(189|190|491|482|186|500|600|820|801)\b"

    country = None
    country_source = None
    subclass = None
    category = "skilled_migration"

    # Step A: Country Detection from Query
    if re.search(au_pattern, q_lower):
        country = "Australia"
        country_source = "query"
    elif re.search(ca_pattern, q_lower):
        country = "Canada"
        country_source = "query"
    elif re.search(us_pattern, q_lower):
        country = "United States"
        country_source = "query"
    elif re.search(de_pattern, q_lower):
        country = "Germany"
        country_source = "query"
    elif re.search(uk_pattern, q_lower):
        country = "United Kingdom"
        country_source = "query"
    elif re.search(nz_pattern, q_lower):
        country = "New Zealand"
        country_source = "query"

    # Step B: Check Australian subclasses if country not yet set
    if not country:
        m_au = re.search(au_subclass_pattern, q_lower)
        if m_au:
            country = "Australia"
            country_source = "subclass"
            subclass = m_au.group(1)

    # Step C: Subclass Extraction based on Country
    if country == "Australia":
        m_sub = re.search(au_subclass_pattern, q_lower)
        if m_sub:
            subclass = m_sub.group(1)
        elif "491" in q_lower:
            subclass = "491"
        elif "190" in q_lower:
            subclass = "190"
        elif "189" in q_lower:
            subclass = "189"
        elif "pr" in q_lower or "permanent" in q_lower or "skilled" in q_lower or "travel" in q_lower:
            subclass = "189/190/491 (GSM PR)"
        else:
            subclass = "189/190/491 (General Skilled Migration)"
    elif country == "Canada":
        if "fsw" in q_lower: subclass = "FSW"
        elif "pnp" in q_lower: subclass = "PNP"
        elif "study" in q_lower: subclass = "Study Permit"; category = "student"
        elif "visitor" in q_lower: subclass = "Visitor Visa"; category = "visitor"
        elif "express entry" in q_lower or "pr" in q_lower: subclass = "Express Entry (FSW)"
        else: subclass = "Express Entry (FSW)"
    elif country == "United States":
        if "h-1b" in q_lower or "h1b" in q_lower: subclass = "H-1B"; category = "work"
        elif "l-1" in q_lower or "l1" in q_lower: subclass = "L-1"; category = "work"
        elif "eb-1" in q_lower or "eb1" in q_lower: subclass = "EB-1"; category = "pr"
        elif "eb-2" in q_lower or "eb2" in q_lower or "niw" in q_lower: subclass = "EB-2"; category = "pr"
        elif "b-1" in q_lower or "b-2" in q_lower or "visitor" in q_lower: subclass = "B-1/B-2"; category = "visitor"
        else: subclass = "EB-2 / EB-3 (Employment-Based PR)"
    elif country == "Germany":
        if "chancen" in q_lower or "opportunity" in q_lower: subclass = "Chancenkarte"; category = "work"
        elif "blue card" in q_lower or "blaue" in q_lower: subclass = "EU Blue Card"; category = "work"
        else: subclass = "Chancenkarte"

    # Step D: Fallback Resolution if no country was in query
    is_unclear = False
    clarification_q = None
    mismatch_with_payload = False

    if not country:
        norm_fallback = normalize_country(fallback_country) if fallback_country else None
        # Check if query is generic without country (e.g., 'can i get pr without job offer')
        is_generic_pr = any(k in q_lower for k in ["pr", "permanent residency", "permanent resident", "points", "job offer", "eligibility"])
        if is_generic_pr and (not norm_fallback or norm_fallback in ["Other", "Selected Destination"]):
            is_unclear = True
            country = "Australia"  # default display comparison
            country_source = "unclear"
            subclass = "189/190 vs Canada Express Entry"
            clarification_q = (
                "Could you clarify which destination country you are targeting — Australia (Subclass 189/190) "
                "or Canada (Express Entry)? Both offer direct permanent residency pathways without an employer job offer."
            )
        elif norm_fallback:
            country = norm_fallback
            country_source = "context"
            subclass = fallback_subclass or ("189" if country == "Australia" else "FSW" if country == "Canada" else "EB-2" if country == "United States" else "")
        else:
            is_unclear = True
            country = "Australia"
            country_source = "unclear"
            subclass = "189/190/491"
            clarification_q = (
                "Which destination country are you inquiring about (e.g. Australia, Canada, or United States)?"
            )
    else:
        if fallback_country and normalize_country(fallback_country) != country:
            mismatch_with_payload = True

    # Step E: Travel Abroad / Offshore vs Onshore Query Intent Detection
    travel_pattern = (
        r"\b(?:travel\s*(?:to\s*other|abroad|outside)|offshore|onshore|leave\s*(?:home|india|country)|"
        r"why\s*(?:i\s*)?want\s*to\s*travel|why\s*(?:do\s*i\s*)?need\s*to\s*travel|apply\s*from\s*(?:india|home)|"
        r"outside\s*(?:australia|canada|us|country))\b"
    )
    is_travel = bool(re.search(travel_pattern, q_lower))

    offshore_explanation = None
    if is_travel:
        if country == "Australia":
            offshore_explanation = (
                "Under official Department of Home Affairs (DHA) regulations for Australia General Skilled Migration "
                "(Subclass 189, 190, 491), you DO NOT need to travel abroad or travel to Australia to apply. "
                "The entire application process — Skills Assessment (VETASSESS/ACS/EA), English exam (IELTS/PTE), "
                "SkillSelect Expression of Interest (EOI), State Nomination, and DHA visa lodgement — is completed "
                "100% offshore from your home country. You only travel to Australia after your permanent residency visa "
                "is formally granted by DHA to make your initial entry."
            )
        elif country == "Canada":
            offshore_explanation = (
                "Under official IRCC regulations, Express Entry (FSW/PNP) is a 100% offshore process. "
                "You do not need to travel to Canada during the application. You only travel after receiving your "
                "Confirmation of Permanent Residence (COPR) and immigrant visa sticker."
            )
        elif country == "United States":
            offshore_explanation = (
                "Under USCIS and Department of State regulations, foreign nationals living abroad may file Form I-140 "
                "under EB-2 NIW without traveling to the U.S. Once the I-140 petition is approved and a visa number is available, "
                "immigrant visa processing takes place at the local U.S. Embassy/Consulate (Consular Processing)."
            )

    # Step F: Query Topic Classification (Strict Question-Based Relevance)
    fee_pattern = (
        r"\b(?:fee|fees|cost|costs|price|pricing|charge|charges|expense|expenses|"
        r"how\s*much|gst|inr|aud|cad|usd|euro|retainer|payment|milestone|milestones|commercials|refund|refunds|"
        r"package|packages|tier|tiers|commission|commissions|incentive|incentives|payout|payouts)\b"
    )
    family_pattern = (
        r"\b(?:family|spouse|partner|wife|husband|child|children|kid|kids|dependent|dependents|"
        r"son|daughter|include\s+(?:my\s+)?(?:family|spouse|wife|husband|child|children)|"
        r"add\s+(?:my\s+)?(?:family|spouse|wife|husband|child|children)|"
        r"de\s*facto|marriage|married|baby|babies|member\s*of\s*the\s*family\s*unit|mofu)\b"
    )
    travel_focus_pattern = (
        r"\b(?:travel|traveling|travelling|abroad|outside|offshore|onshore|leave\s*(?:home|india|country)|"
        r"why\s*(?:i\s*)?want\s*to\s*travel|why\s*(?:do\s*i\s*)?need\s*to\s*travel|apply\s*from\s*(?:india|home)|"
        r"outside\s*(?:australia|canada|us|country)|flight|relocate|relocation)\b"
    )
    benefits_pattern = (
        r"\b(?:benefit|benefits|advantage|advantages|perk|perks|why\s*(?:should\s*i\s*)?(?:choose|pick|opt|prefer|apply|migrate|go|target)|"
        r"why\s*(?:australia|canada|germany|nz|pr|permanent)|what\s*(?:are|is)\s*(?:the\s*)?benefits?|rights|citizenship|medicare|healthcare|social\s*security)\b"
    )
    eligibility_pattern = (
        r"\b(?:eligible|eligibility|qualify|qualifies|qualification|criteria|points|score|pass\s*mark|benchmark|requirements?|minimum\s*points|age\s*limit|job\s*offer)\b"
    )
    process_pattern = (
        r"\b(?:process|processing|procedure|step|steps|timeline|duration|how\s*long|how\s*to\s*apply|time\s*taken|stages|phases|roadmap|how\s*much\s*time)\b"
    )
    objection_pattern = (
        r"\b(?:guarantee|promise|rejection|refusal|risk|chance|chances|success\s*rate|fake)\b"
    )

    if re.search(objection_pattern, q_lower):
        topic = "objection"
    elif re.search(family_pattern, q_lower) and not re.search(fee_pattern, q_lower):
        topic = "family"
    elif re.search(fee_pattern, q_lower):
        topic = "fees"
    elif is_travel or re.search(travel_focus_pattern, q_lower):
        topic = "travel"
    elif re.search(family_pattern, q_lower):
        topic = "family"
    elif re.search(benefits_pattern, q_lower):
        topic = "benefits"
    elif re.search(eligibility_pattern, q_lower):
        topic = "eligibility"
    elif re.search(process_pattern, q_lower):
        topic = "process"
    else:
        topic = "general"

    # Authority and portal mapping
    cc_map = {
        "Australia": ("AU", "Department of Home Affairs (DHA)", "https://immi.homeaffairs.gov.au"),
        "Canada": ("CA", "Immigration, Refugees and Citizenship Canada (IRCC)", "https://www.canada.ca/en/immigration-refugees-citizenship.html"),
        "United States": ("US", "U.S. Citizenship and Immigration Services (USCIS) / Department of State", "https://www.uscis.gov"),
        "United Kingdom": ("GB", "UK Visas and Immigration (UKVI) / Home Office", "https://www.gov.uk/government/organisations/uk-visas-and-immigration"),
        "Germany": ("DE", "Federal Foreign Office (Auswärtiges Amt) / BAMF", "https://www.auswaertiges-amt.de"),
        "New Zealand": ("NZ", "Immigration New Zealand (INZ)", "https://www.immigration.govt.nz"),
    }
    cc, auth, portal = cc_map.get(country, ("AU", f"{country} Immigration Authority", "https://immi.homeaffairs.gov.au"))

    return CountryVisaQueryIntent(
        detected_country=country,
        country_code=cc,
        country_source=country_source,
        detected_subclass=subclass,
        visa_category=category,
        is_travel_abroad_pr_query=is_travel,
        query_topic=topic,
        is_unclear=is_unclear,
        clarification_question=clarification_q,
        offshore_onshore_explanation=offshore_explanation,
        mismatch_with_payload=mismatch_with_payload,
        authority_name=auth,
        official_portal_url=portal,
    )


def detect_occupation_in_query(query: str, selected_country: Optional[str] = None) -> Optional[OccupationDetection]:
    """Detects occupation codes and systems (NOC, ANZSCO, NZSCO, SOC, UK SOC) in query text."""
    _init_data()
    q = (query or "").strip()
    norm_sel = normalize_country(selected_country)

    # 1. Check for explicit NOC mentions or 5-digit Canadian NOC codes
    # Examples: "NOC 21231", "NOC21231", "NOC code 21232", "TEER 1 21231"
    noc_match = re.search(r"\bNOC\s*(?:2021\s*|2016\s*|code\s*)?(\d{5})\b", q, re.IGNORECASE)
    if not noc_match:
        # Check standalone 5-digit number if user mentions teer or canada or if code matches our NOC database
        five_digit_match = re.search(r"\b(\d{5})\b", q)
        if five_digit_match:
            c = five_digit_match.group(1)
            if "noc" in q.lower() or "teer" in q.lower() or "canada" in q.lower() or "express entry" in q.lower() or c in _NOC_INDEX:
                noc_match = five_digit_match

    if noc_match:
        code = noc_match.group(1)
        teer = int(code[1]) if code[1].isdigit() else 1
        noc_data = _NOC_INDEX.get(code, {})
        title = noc_data.get("title") or "Canadian Skilled Professional"
        is_mismatch = (norm_sel != "Canada")
        mismatch_warn = None
        cw_code, cw_title, cw_auth = None, None, None

        if is_mismatch:
            mismatch_warn = (
                f"⚠️ Country & System Clarification: The requested code NOC {code} ({title}) belongs to the "
                f"Canadian National Occupational Classification (NOC 2021 V1.0 - TEER {teer}) system administered by IRCC & ESDC, "
                f"not {norm_sel}."
            )
            # Find crosswalk to selected country
            for cw in CROSSWALK_CATALOG:
                if cw["ca_noc"] == code or code.startswith(cw["ca_noc"][:4]):
                    if norm_sel == "Australia":
                        cw_code = cw["au_anzsco"]
                        cw_title = cw["au_title"]
                        cw_auth = cw["au_body"]
                    elif norm_sel == "United Kingdom":
                        cw_code = cw["uk_soc"]
                        cw_title = cw["uk_title"]
                        cw_auth = "UKVI / Home Office"
                    elif norm_sel == "United States":
                        cw_code = cw["us_soc"]
                        cw_title = cw["us_title"]
                        cw_auth = "USCIS / DOL OFLC"
                    break

        return OccupationDetection(
            code=code,
            classification_system="Canada National Occupational Classification (NOC 2021 V1.0)",
            country="Canada",
            country_code="CA",
            is_mismatch=is_mismatch,
            selected_country=norm_sel,
            mismatch_warning=mismatch_warn,
            title=title,
            teer=teer,
            assessing_authority="WES / CES / ICAS (ECA Credential Evaluation)",
            crosswalk_code=cw_code,
            crosswalk_title=cw_title,
            crosswalk_country=norm_sel if is_mismatch else None,
            crosswalk_authority=cw_auth,
        )

    # 2. Check for explicit ANZSCO mentions or 6-digit Australian/NZ codes
    anzsco_match = re.search(r"\bANZSCO\s*(?:code\s*)?(\d{6})\b", q, re.IGNORECASE)
    if not anzsco_match:
        six_digit_match = re.search(r"\b(\d{6})\b", q)
        if six_digit_match:
            c = six_digit_match.group(1)
            if "anzsco" in q.lower() or "acs" in q.lower() or "vetassess" in q.lower() or "engineers australia" in q.lower() or c in _AU_INDEX:
                anzsco_match = six_digit_match

    if anzsco_match:
        code = anzsco_match.group(1)
        # Determine whether query explicitly targets NZ or Australia
        is_nz = (norm_sel == "New Zealand" or bool(re.search(r"\b(?:nz|new\s*zealand|green\s*list)\b", q, re.IGNORECASE)))
        target_country = "New Zealand" if is_nz else "Australia"
        target_cc = "NZ" if is_nz else "AU"
        sys_name = "New Zealand Standard Classification (ANZSCO / Green List)" if is_nz else "Australian and New Zealand Standard Classification of Occupations (ANZSCO)"
        au_data = _AU_INDEX.get(code, {})
        title = au_data.get("title") or "Skilled Professional"
        auth = "NZQA" if is_nz else au_data.get("assessing_body", "VETASSESS / ACS / EA")

        is_mismatch = (norm_sel not in [target_country, "Australia", "New Zealand"] if not is_nz else norm_sel != "New Zealand")
        mismatch_warn = None
        cw_code, cw_title, cw_auth = None, None, None

        if is_mismatch:
            mismatch_warn = (
                f"⚠️ Country & System Clarification: The requested code ANZSCO {code} ({title}) belongs to the "
                f"{target_country} immigration framework ({sys_name}), not {norm_sel}."
            )
            for cw in CROSSWALK_CATALOG:
                if cw["au_anzsco"] == code:
                    if norm_sel == "Canada":
                        cw_code = cw["ca_noc"]
                        cw_title = cw["ca_title"]
                        cw_auth = cw["ca_body"]
                    elif norm_sel == "United Kingdom":
                        cw_code = cw["uk_soc"]
                        cw_title = cw["uk_title"]
                        cw_auth = "UKVI / Home Office"
                    elif norm_sel == "United States":
                        cw_code = cw["us_soc"]
                        cw_title = cw["us_title"]
                        cw_auth = "USCIS / DOL OFLC"
                    break

        # Calculate Skill level (Major group 1-3 = Level 1/2/3)
        skill_lvl = 1 if code.startswith(("1", "2")) else (2 if code.startswith("3") else 3)

        return OccupationDetection(
            code=code,
            classification_system=sys_name,
            country=target_country,
            country_code=target_cc,
            is_mismatch=is_mismatch,
            selected_country=norm_sel,
            mismatch_warning=mismatch_warn,
            title=title,
            skill_level=skill_lvl,
            assessing_authority=auth,
            crosswalk_code=cw_code,
            crosswalk_title=cw_title,
            crosswalk_country=norm_sel if is_mismatch else None,
            crosswalk_authority=cw_auth,
        )

    # 3. Check for US SOC / O*NET pattern: XX-XXXX or XX-XXXX.XX
    us_soc_match = re.search(r"\b(?:SOC|O\*?NET)?\s*(\d{2}-\d{4}(?:\.\d{2})?)\b", q, re.IGNORECASE)
    if us_soc_match:
        code = us_soc_match.group(1)
        is_mismatch = (norm_sel != "United States")
        title = "Specialty Occupation Professional"
        cw_code, cw_title, cw_auth = None, None, None

        for cw in CROSSWALK_CATALOG:
            if cw["us_soc"].startswith(code[:7]):
                title = cw["us_title"]
                if norm_sel == "Australia":
                    cw_code = cw["au_anzsco"]
                    cw_title = cw["au_title"]
                    cw_auth = cw["au_body"]
                elif norm_sel == "Canada":
                    cw_code = cw["ca_noc"]
                    cw_title = cw["ca_title"]
                    cw_auth = cw["ca_body"]
                break

        mismatch_warn = None
        if is_mismatch:
            mismatch_warn = (
                f"⚠️ Country & System Clarification: The code SOC {code} ({title}) belongs to the "
                f"United States Standard Occupational Classification (SOC / O*NET) system administered by the US Department of Labor & USCIS, "
                f"not {norm_sel}."
            )

        return OccupationDetection(
            code=code,
            classification_system="US Standard Occupational Classification (SOC / O*NET)",
            country="United States",
            country_code="US",
            is_mismatch=is_mismatch,
            selected_country=norm_sel,
            mismatch_warning=mismatch_warn,
            title=title,
            assessing_authority="USCIS / US Department of Labor (DOL OFLC)",
            crosswalk_code=cw_code,
            crosswalk_title=cw_title,
            crosswalk_country=norm_sel if is_mismatch else None,
            crosswalk_authority=cw_auth,
        )

    # 4. Check for UK SOC 2020 pattern: UK SOC XXXX or 4-digit code in UK query
    uk_soc_match = re.search(r"\b(?:UK\s*SOC|SOC\s*2020)\s*(\d{4})\b", q, re.IGNORECASE)
    if not uk_soc_match and (norm_sel == "United Kingdom" or "uk" in q.lower() or "skilled worker" in q.lower()):
        four_digit = re.search(r"\b(\d{4})\b", q)
        if four_digit:
            uk_soc_match = four_digit

    if uk_soc_match:
        code = uk_soc_match.group(1)
        is_mismatch = (norm_sel != "United Kingdom")
        title = "UK Skilled Worker Occupation"
        cw_code, cw_title, cw_auth = None, None, None

        for cw in CROSSWALK_CATALOG:
            if cw["uk_soc"] == code:
                title = cw["uk_title"]
                if norm_sel == "Australia":
                    cw_code = cw["au_anzsco"]
                    cw_title = cw["au_title"]
                    cw_auth = cw["au_body"]
                elif norm_sel == "Canada":
                    cw_code = cw["ca_noc"]
                    cw_title = cw["ca_title"]
                    cw_auth = cw["ca_body"]
                break

        mismatch_warn = None
        if is_mismatch:
            mismatch_warn = (
                f"⚠️ Country & System Clarification: The code UK SOC {code} ({title}) belongs to the "
                f"United Kingdom Standard Occupational Classification (SOC 2020) system administered by the Home Office / UKVI, "
                f"not {norm_sel}."
            )

        return OccupationDetection(
            code=code,
            classification_system="UK Standard Occupational Classification (SOC 2020)",
            country="United Kingdom",
            country_code="UK",
            is_mismatch=is_mismatch,
            selected_country=norm_sel,
            mismatch_warning=mismatch_warn,
            title=title,
            assessing_authority="Home Office / UKVI Sponsor Licence Verification",
            crosswalk_code=cw_code,
            crosswalk_title=cw_title,
            crosswalk_country=norm_sel if is_mismatch else None,
            crosswalk_authority=cw_auth,
        )

    # 5. Check keyword-based occupation matching from catalog if no raw code was typed
    q_low = q.lower()
    for cw in CROSSWALK_CATALOG:
        if any(kw in q_low for kw in cw["keywords"]):
            # Match directly to the selected country!
            if norm_sel == "Canada":
                c = cw["ca_noc"]
                return OccupationDetection(
                    code=c,
                    classification_system="Canada National Occupational Classification (NOC 2021 V1.0)",
                    country="Canada",
                    country_code="CA",
                    is_mismatch=False,
                    selected_country=norm_sel,
                    title=cw["ca_title"],
                    teer=cw["ca_teer"],
                    assessing_authority=cw["ca_body"],
                )
            elif norm_sel in ["Australia", "New Zealand"]:
                is_nz = (norm_sel == "New Zealand")
                c = cw["au_anzsco"]
                return OccupationDetection(
                    code=c,
                    classification_system="New Zealand Standard Classification (ANZSCO)" if is_nz else "Australian ANZSCO (ABS / DHA)",
                    country="New Zealand" if is_nz else "Australia",
                    country_code="NZ" if is_nz else "AU",
                    is_mismatch=False,
                    selected_country=norm_sel,
                    title=cw["au_title"],
                    skill_level=cw["au_skill_level"],
                    assessing_authority="NZQA" if is_nz else cw["au_body"],
                )
            elif norm_sel == "United Kingdom":
                c = cw["uk_soc"]
                return OccupationDetection(
                    code=c,
                    classification_system="UK Standard Occupational Classification (SOC 2020)",
                    country="United Kingdom",
                    country_code="UK",
                    is_mismatch=False,
                    selected_country=norm_sel,
                    title=cw["uk_title"],
                    assessing_authority="Home Office / UKVI",
                )
            elif norm_sel == "United States":
                c = cw["us_soc"]
                return OccupationDetection(
                    code=c,
                    classification_system="US Standard Occupational Classification (SOC / O*NET)",
                    country="United States",
                    country_code="US",
                    is_mismatch=False,
                    selected_country=norm_sel,
                    title=cw["us_title"],
                    assessing_authority="USCIS / DOL OFLC",
                )

    return None


def get_full_occupation_profile(det: OccupationDetection) -> FullOccupationProfile:
    """Builds a comprehensive, rich occupation profile with duties, requirements, assessing authority, and fees."""
    _init_data()

    if det.country_code == "CA":
        # Canadian NOC
        noc_data = _NOC_INDEX.get(det.code, {})
        elems = _NOC_ELEMENTS.get(det.code, {})
        title = det.title or noc_data.get("title") or "Canadian Skilled Professional"
        definition = noc_data.get("definition") or (
            f"{title} operate in professional, scientific and technical environments. "
            f"Under Statistics Canada and IRCC regulations, they research, develop, analyze, and oversee specialized technical implementations."
        )
        duties = elems.get("duties", [])
        if not duties:
            duties = [
                f"Analyze client specifications, business objectives, and regulatory standards to draft comprehensive technical workflows.",
                f"Lead the design, configuration, implementation, and integration of enterprise systems and specialized protocols.",
                f"Conduct systematic unit tests, security verifications, quality assurance, and compliance diagnostics.",
                f"Document technical specifications, standard operating procedures, and architectural documentation for regulatory oversight.",
                f"Mentor associate technical staff, coordinate with cross-functional stakeholders, and troubleshoot escalated operational anomalies.",
            ]
        else:
            # Clean first item if introductory
            if duties and "duties:" in duties[0].lower():
                duties = duties[1:]

        reqs = elems.get("requirements", [])
        if not reqs:
            reqs = [
                "A recognized Bachelor's or Master's degree in a directly relevant discipline is mandatory for TEER 1 classification.",
                "Minimum 12 to 36 months of verified, continuous post-qualification skilled employment.",
                "Educational Credential Assessment (ECA) report from an IRCC-designated body (e.g. WES, ICAS, CES) validating Canadian equivalency.",
                "Language proficiency benchmark meeting Canadian Language Benchmark (CLB) 7.0 minimum for Express Entry streams.",
            ]

        teer = det.teer if det.teer is not None else int(det.code[1]) if len(det.code) >= 2 and det.code[1].isdigit() else 1
        teer_desc = teer_meaning(teer)

        pathways = [
            "Express Entry — Federal Skilled Worker Program (FSWP, 67-point grid)",
            "Express Entry — Canadian Experience Class (CEC, minimum 1 yr Canadian skilled work)",
            "Express Entry — Category-Based Selection (STEM / Healthcare / Trades draws)",
            "Provincial Nominee Programs (PNP: Ontario OINP Tech, BC PNP Tech, Alberta AAIP)",
        ]

        salary_info = "CAD $85,000 – $135,000 / year (Statutory Median: CAD $48.50/hr). Express Entry requires settlement funds of CAD $14,690 (single applicant) unless on an LMIA-backed job offer."
        source_url = f"https://noc.esdc.gc.ca/Structure/NocDetails?objectid={det.code}"

        return FullOccupationProfile(
            code=det.code,
            title=title,
            classification_system=det.classification_system,
            country="Canada",
            country_code="CA",
            skill_tier_label=f"TEER {teer}",
            skill_tier_description=teer_desc,
            definition=definition,
            main_duties=duties[:6],
            employment_requirements=reqs[:4],
            assessing_authority="WES / CES / ICAS (ECA Credential Evaluation)",
            visa_pathways=pathways,
            statutory_salary_threshold=salary_info,
            official_source_url=source_url,
            verification_date="Current 2024–2025 IRCC Ministerial Instructions & NOC 2021 V1.0 Gazette",
            mismatch_advisory=det.mismatch_warning,
            crosswalk_info={
                "code": det.crosswalk_code,
                "title": det.crosswalk_title,
                "country": det.crosswalk_country,
                "authority": det.crosswalk_authority,
            } if det.crosswalk_code else None,
        )

    elif det.country_code == "AU":
        # Australian ANZSCO
        au_data = _AU_INDEX.get(det.code, {})
        title = det.title or au_data.get("title") or "Skilled Professional"
        auth = det.assessing_authority or au_data.get("assessing_body") or "ACS / VETASSESS / Engineers Australia"
        list_type = au_data.get("list") or "MLTSSL (Medium and Long-term Strategic Skills List)"

        skill_lvl = det.skill_level or 1
        skill_desc = anzsco_skill_level_meaning(skill_lvl)

        duties = [
            f"Analyze user requirements, produce technical design models, and document functional system blueprints.",
            f"Write, test, debug, and optimize robust software code and high-performance system architectures.",
            f"Oversee end-to-end integration, performance profiling, and compliance testing against enterprise standards.",
            f"Maintain technical release governance, change registers, and operational escalation procedures.",
            f"Liaise with systems analysts, engineering peers, and senior business executives to ensure project deliverables.",
        ]

        reqs = [
            f"Bachelor's degree or higher qualification in a closely related field assessed by {auth}.",
            f"Post-qualification work experience (typically 2 to 4 years deducted by {auth} to meet the Australian suitability criteria).",
            "Competent English (IELTS 6.0 each) mandatory; Proficient (IELTS 7.0 / PTE 65) or Superior (IELTS 8.0 / PTE 79) recommended for points.",
            "Valid positive Skills Assessment outcome letter issued by the designated assessing authority.",
        ]

        raw_visas = au_data.get("visas") or [
            "189 - Skilled Independent (Points-Tested PR)",
            "190 - Skilled Nominated (State PR, +5 pts)",
            "491 - Skilled Work Regional (Provisional, +15 pts)",
            "482 - Skills in Demand / TSS (Employer Sponsored)",
            "186 - Employer Nomination Scheme (Direct Entry PR)",
        ]

        salary_info = "Temporary Skilled Migration Income Threshold (TSMIT): AUD $73,150 / year minimum. Market rate for Skill Level 1: AUD $95,000 – $145,000 / year."
        source_url = f"https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list"

        return FullOccupationProfile(
            code=det.code,
            title=title,
            classification_system=det.classification_system,
            country="Australia",
            country_code="AU",
            skill_tier_label=f"ANZSCO Skill Level {skill_lvl} ({list_type})",
            skill_tier_description=skill_desc,
            definition=f"{title} under ANZSCO {det.code} plans, designs, builds, and maintains high-integrity software applications and technical platforms for Australian enterprises.",
            main_duties=duties,
            employment_requirements=reqs,
            assessing_authority=auth,
            visa_pathways=raw_visas[:5],
            statutory_salary_threshold=salary_info,
            official_source_url=source_url,
            verification_date="Current 2024–2025 Migration Regulations (Legislative Instrument LIN 19/051 & TSMIT Indexation)",
            mismatch_advisory=det.mismatch_warning,
            crosswalk_info={
                "code": det.crosswalk_code,
                "title": det.crosswalk_title,
                "country": det.crosswalk_country,
                "authority": det.crosswalk_authority,
            } if det.crosswalk_code else None,
        )

    elif det.country_code == "NZ":
        # New Zealand ANZSCO / Green List
        title = det.title or "New Zealand Skilled Migrant"
        return FullOccupationProfile(
            code=det.code,
            title=title,
            classification_system=det.classification_system,
            country="New Zealand",
            country_code="NZ",
            skill_tier_label="Green List Tier 1 / SMC 6-Point System",
            skill_tier_description="Eligible under INZ Green List (Straight to Residence Pathway) or the 6-point Skilled Migrant Category (SMC).",
            definition=f"{title} (ANZSCO {det.code}) delivers critical technical capabilities meeting Immigration New Zealand workforce shortage criteria.",
            main_duties=[
                "Establish architectural designs, technical requirements, and functional specifications.",
                "Implement scalable technology solutions adhering to New Zealand regulatory and privacy standards.",
                "Ensure continuous quality assurance, system performance, and automated regression diagnostics.",
                "Collaborate with multi-disciplinary stakeholders to deliver enterprise business transformation.",
            ],
            employment_requirements=[
                "Recognized Bachelor's Degree (Level 7) or Master's (Level 8) on the New Zealand Qualifications Framework (NZQF) or evaluated by NZQA.",
                "Job offer or current employment with an INZ Accredited Employer.",
                "Remuneration meeting or exceeding the NZ Median Wage threshold.",
            ],
            assessing_authority="NZQA (International Qualifications Assessment) / IPENZ / Professional Registration",
            visa_pathways=[
                "Straight to Residence Visa (Green List Tier 1)",
                "Work to Residence Visa (Green List Tier 2, after 24 months)",
                "Skilled Migrant Category Resident Visa (SMC 6-point system)",
                "Accredited Employer Work Visa (AEWV)",
            ],
            statutory_salary_threshold="NZD $31.61 / hour (or 1.5x / 2x median wage for SMC points tiers). Green List roles require minimum NZD $61.69/hr or accredited employer contract.",
            official_source_url="https://www.immigration.govt.nz/new-zealand-visas/preparing-a-visa-application/working-in-nz/qualifications-for-work/green-list-occupations",
            verification_date="Current 2024–2025 Immigration New Zealand Operational Manual",
            mismatch_advisory=det.mismatch_warning,
            crosswalk_info={
                "code": det.crosswalk_code,
                "title": det.crosswalk_title,
                "country": det.crosswalk_country,
                "authority": det.crosswalk_authority,
            } if det.crosswalk_code else None,
        )

    elif det.country_code == "UK":
        # United Kingdom SOC 2020
        title = det.title or "UK Skilled Worker"
        return FullOccupationProfile(
            code=det.code,
            title=title,
            classification_system="UK Standard Occupational Classification (SOC 2020)",
            country="United Kingdom",
            country_code="UK",
            skill_tier_label="RQF Level 3+ (A-Level / Degree Equivalent)",
            skill_tier_description="Eligible for UK Skilled Worker visa sponsorship under Home Office Points-Based Immigration System.",
            definition=f"{title} (UK SOC {det.code}) performs high-level technical development and analysis under the UK Points-Based Immigration System.",
            main_duties=[
                "Interpret business requirements and architect technical systems aligned with UK data security and governance.",
                "Develop, maintain, and upgrade production software applications and cloud environments.",
                "Conduct automated testing, peer reviews, and performance diagnostics.",
                "Manage incident resolution, change management, and technical documentation.",
            ],
            employment_requirements=[
                "Valid Certificate of Sponsorship (CoS) from a licensed UK Home Office sponsor.",
                "Salary meeting the UK general threshold of £38,700/year or the occupation's going rate (whichever is higher).",
                "English language proficiency at CEFR B1 level (reading, writing, speaking, and listening).",
            ],
            assessing_authority="UKVI / Licensed Home Office A-Rated Sponsor Employer",
            visa_pathways=[
                "Skilled Worker Visa (5-year route to Indefinite Leave to Remain - ILR)",
                "Global Talent Visa (for leaders and promising talent in Tech Nation endorsement)",
                "Senior or Specialist Worker Visa (Global Business Mobility)",
            ],
            statutory_salary_threshold="General threshold £38,700 / year (or Immigration Salary List rate of £30,960 minimum). Plus Immigration Health Surcharge (IHS) of £1,035/year.",
            official_source_url="https://www.gov.uk/government/publications/skilled-worker-visa-immigration-salary-list",
            verification_date="Current UK Statement of Changes in Immigration Rules (HC 590)",
            mismatch_advisory=det.mismatch_warning,
            crosswalk_info={
                "code": det.crosswalk_code,
                "title": det.crosswalk_title,
                "country": det.crosswalk_country,
                "authority": det.crosswalk_authority,
            } if det.crosswalk_code else None,
        )

    elif det.country_code == "US":
        # United States SOC / O*NET
        title = det.title or "US Specialty Occupation Professional"
        return FullOccupationProfile(
            code=det.code,
            title=title,
            classification_system="US Standard Occupational Classification (SOC / O*NET)",
            country="United States",
            country_code="US",
            skill_tier_label="Specialty Occupation (US Bachelor's Degree Equivalent)",
            skill_tier_description="Requires theoretical and practical application of a body of highly specialized knowledge requiring a US Bachelor's degree or higher.",
            definition=f"{title} (SOC {det.code}) executes advanced engineering, system architecture, and specialized technology implementations under USCIS and DOL regulations.",
            main_duties=[
                "Formulate comprehensive software specifications and system architecture designs.",
                "Program, engineer, and deploy high-concurrency enterprise services.",
                "Evaluate algorithms, network protocols, and data structures for maximum efficiency.",
                "Produce technical reports, security audit matrices, and release protocols.",
            ],
            employment_requirements=[
                "At least a US Bachelor's degree (or 4-year foreign equivalent evaluated by an accredited evaluation agency).",
                "Certified Labor Condition Application (LCA Form ETA-9035) from the Department of Labor demonstrating prevailing wage compliance.",
                "Petition approval on Form I-129 (for H-1B/L-1) or Form I-140 (for EB-2 / EB-3).",
            ],
            assessing_authority="USCIS / US Department of Labor (DOL OFLC)",
            visa_pathways=[
                "H-1B Specialty Occupation Visa (Cap-subject lottery or Cap-exempt)",
                "EB-2 National Interest Waiver (NIW, self-petition PR route)",
                "EB-1B / EB-1A Extraordinary Ability / Outstanding Researcher",
                "L-1A / L-1B Intracompany Transferee Executive or Specialized Knowledge",
            ],
            statutory_salary_threshold="Must meet or exceed the DOL OFLC Prevailing Wage Level (Level 1–4 depending on seniority and metropolitan statistical area).",
            official_source_url="https://www.onetonline.org/",
            verification_date="Current USCIS Policy Manual & DOL OFLC Prevailing Wage Data",
            mismatch_advisory=det.mismatch_warning,
            crosswalk_info={
                "code": det.crosswalk_code,
                "title": det.crosswalk_title,
                "country": det.crosswalk_country,
                "authority": det.crosswalk_authority,
            } if det.crosswalk_code else None,
        )

    # Fallback generic profile
    return FullOccupationProfile(
        code=det.code,
        title=det.title or "Skilled Professional",
        classification_system=det.classification_system,
        country=det.country,
        country_code=det.country_code,
        skill_tier_label="Skilled Professional",
        skill_tier_description="Standard skilled immigration qualification.",
        definition=f"Professional operating under official statutory guidelines for {det.country}.",
        main_duties=[
            "Design and execute professional activities in accordance with regulatory frameworks.",
            "Maintain technical documentation and client records.",
            "Coordinate cross-functional implementations.",
        ],
        employment_requirements=[
            "Formal degree or diploma equivalency.",
            "Minimum 3 years verifiable professional experience.",
            "Language proficiency benchmark.",
        ],
        assessing_authority=det.assessing_authority or "Designated Authority",
        visa_pathways=["Permanent Residency Skilled Migration", "Work Visa Pathway"],
        statutory_salary_threshold="Subject to national median wage benchmarks.",
        official_source_url="https://leamss.com/atlas/",
        verification_date="Current Statutory Gazette",
        mismatch_advisory=det.mismatch_warning,
    )


def generate_sales_qualification_questions(profile: Optional[FullOccupationProfile], country: str) -> List[str]:
    """Generates 5 sharp qualification questions for the sales consultant to ask prospect on call."""
    c_norm = normalize_country(country)
    code_text = f" ({profile.code} - {profile.title})" if profile else ""

    if c_norm == "Canada":
        return [
            f"1. **Formal Degree Assessment:** Do you hold a full-time 4-year Bachelor's degree or Master's, and have you obtained an Educational Credential Assessment (ECA) through WES or ICAS for Canadian equivalency?",
            f"2. **Work Experience Continuity:** Do you have at least 3 years of continuous, paid full-time post-graduation experience that directly matches the primary duties of NOC {profile.code if profile else 'your target occupation'}?",
            f"3. **Language Band (IELTS / CELPIP / PTE Core):** Have you taken an official language test, and can you achieve Canadian Language Benchmark (CLB) 7 or 8 (equivalent to IELTS 6.0–7.5 in all bands)?",
            f"4. **Age Bracket:** What is your exact date of birth? (Applicants between 20–29 secure the maximum 110 CRS points for age in Express Entry).",
            f"5. **Settlement Liquidity:** Do you have unencumbered, liquid settlement funds meeting the IRCC statutory requirement of CAD $14,690 (single) or CAD $18,288 (couple) in your bank account?",
        ]
    elif c_norm in ["Australia", "New Zealand"]:
        auth = profile.assessing_authority if profile else "ACS / Engineers Australia / VETASSESS"
        return [
            f"1. **Degree & Skills Assessment Alignment:** Is your primary qualification directly relevant to {profile.title if profile else 'your nominated occupation'}, and do you have syllabus transcripts ready for your {auth} skills assessment?",
            f"2. **Verifiable Post-Qualification Tenure:** Can you supply formal experience letters on company letterhead detailing your duties, official salary bank statements, and tax returns (Form 16 / ITR) covering at least 3 to 8 years?",
            f"3. **English Proficiency Benchmark:** Are you prepared to target Proficient English (PTE 65+ / IELTS 7.0 for 10 extra points) or Superior English (PTE 79+ / IELTS 8.0 for 20 extra points)?",
            f"4. **Points Grid Score:** Based on age (optimal: 25–32 years for 30 points), education (15 pts), and experience (10–15 pts), does your current profile achieve at least the 65-point benchmark?",
            f"5. **State Nomination Flexibility:** Are you open to lodging Expressions of Interest (EOI) across state nomination (Subclass 190, +5 points) and regional sponsorship (Subclass 491, +15 points) streams to maximize invitation chances?",
        ]
    elif c_norm == "Germany":
        return [
            f"1. **Qualification Recognition:** Is your university degree recognized in the German Anabin database as 'H+' or evaluated as equivalent to a German higher education degree by ZAB?",
            f"2. **Chancenkarte 6-Point Threshold:** Do you meet the 6-point requirement for the Opportunity Card through recognized education (4 pts), 5+ years experience in a shortage profession (3 pts), and age <35 (2 pts)?",
            f"3. **German / English Proficiency:** Do you have certified German language proficiency at CEFR A2/B1 level (Goethe/telc) or English C1 level?",
            f"4. **Blocked Account Liquidity:** Are you prepared to establish a statutory German Blocked Account (Sperrkonto) of approximately €1,027/month (€12,324/year) to demonstrate self-sufficiency?",
            f"5. **Blue Card Job Offer Feasibility:** Do you hold or are you actively interviewing for a contract meeting the German EU Blue Card threshold of €41,041.80 (STEM shortage) or €45,300 (general)?",
        ]
    elif c_norm == "United Kingdom":
        return [
            f"1. **Job Offer & Sponsor Licence:** Has a UK employer with an active Home Office A-Rated Sponsor Licence extended a formal Certificate of Sponsorship (CoS)?",
            f"2. **Salary Level Compliance:** Does the contracted remuneration meet or exceed the statutory threshold of £38,700/year (or £30,960 if on the Immigration Salary List)?",
            f"3. **English Language Requirement:** Can you prove English proficiency at CEFR B1 level via a SELT test (IELTS for UKVI) or a UK-equivalent degree taught in English with Ecctis certification?",
            f"4. **Skill Level Verification:** Does the job role correspond to RQF Level 3 or higher under UK SOC 2020?",
            f"5. **Immigration Health Surcharge Preparedness:** Are you prepared for the statutory UKVI visa application fees and the Immigration Health Surcharge of £1,035 per applicant per year?",
        ]
    elif c_norm == "United States":
        return [
            f"1. **Degree Equivalence:** Do you possess a 4-year US Bachelor's degree or foreign equivalent in a field directly specialized to the position?",
            f"2. **H-1B Employer Petition:** Does your prospective employer have the corporate standing to file an LCA with the DOL and an I-129 petition with USCIS?",
            f"3. **Prevailing Wage Compliance:** Does the proposed salary satisfy the DOL OFLC prevailing wage level for the specific metropolitan statistical area?",
            f"4. **EB-2 NIW National Importance:** For EB-2 NIW self-petitioners: Can you establish substantial merit and national importance for your proposed endeavor in the United States?",
            f"5. **Timing & Visa Cap:** Are you filing under the annual H-1B cap lottery in March or qualifies under cap-exempt non-profit / academic institutions?",
        ]

    return [
        "1. What is your highest level of formal educational qualification?",
        "2. How many years of verifiable, continuous post-qualification employment experience do you have?",
        "3. Have you taken an authorized English language proficiency test (IELTS/PTE)?",
        "4. What is your age, and is your passport valid for at least 12 months?",
        "5. Do you have unencumbered funds to satisfy government settlement benchmarks?",
    ]


def get_statutory_fees_and_commercials(country: str, visa_subclass: Optional[str] = None) -> Dict[str, Any]:
    """Returns official statutory government fees and standard LEAMSS commercials."""
    c_norm = normalize_country(country)

    if c_norm == "Canada":
        return {
            "gov_fee_foreign": "CAD $1,525",
            "gov_fee_breakdown": "CAD $950 (Processing fee) + CAD $575 (Right of Permanent Residence Fee - RPRF). Biometrics: CAD $85.",
            "gov_fee_inr_approx": "₹95,000 – ₹1,05,000",
            "leamss_retainer_inr": "₹1,25,000 (+ 18% GST)",
            "leamss_milestones": "40% Onboarding & File Review ➔ 30% ECA & Profile Lodgement ➔ 30% ITA Submission",
            "statutory_benchmark": "67 Points minimum for Federal Skilled Worker (FSW) Grid.",
            "settlement_funds": "CAD $14,690 (Single Applicant) / CAD $18,288 (Family of 2)",
            "official_portal": "https://www.canada.ca/en/immigration-refugees-citizenship.html",
        }
    elif c_norm == "Australia":
        return {
            "gov_fee_foreign": "AUD $4,770",
            "gov_fee_breakdown": "AUD $4,770 (Primary applicant). Secondary adult applicant (18+): AUD $2,385. Dependent child: AUD $1,195.",
            "gov_fee_inr_approx": "₹2,65,000 – ₹2,75,000",
            "leamss_retainer_inr": "₹1,35,000 (+ 18% GST)",
            "leamss_milestones": "40% Onboarding & Skills Assessment ➔ 30% State Nomination / EOI Lodgement ➔ 30% Visa Lodgement",
            "statutory_benchmark": "65 Points statutory pass mark on General Skilled Migration (GSM) grid.",
            "settlement_funds": "AUD $30,000 – $40,000 recommended for state nomination applications.",
            "official_portal": "https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list",
        }
    elif c_norm == "New Zealand":
        return {
            "gov_fee_foreign": "NZD $4,290",
            "gov_fee_breakdown": "NZD $4,290 (Skilled Migrant Category Resident Visa application fee & immigration levy).",
            "gov_fee_inr_approx": "₹2,20,000 – ₹2,30,000",
            "leamss_retainer_inr": "₹1,20,000 (+ 18% GST)",
            "leamss_milestones": "40% Onboarding & NZQA Assessment ➔ 30% Expression of Interest ➔ 30% ITA Resident Lodgement",
            "statutory_benchmark": "6 Points required under the new SMC points framework or Green List Tier 1 straight to residence.",
            "settlement_funds": "Median wage of NZD $31.61/hour contract required.",
            "official_portal": "https://www.immigration.govt.nz/new-zealand-visas/preparing-a-visa-application/working-in-nz/qualifications-for-work/green-list-occupations",
        }
    elif c_norm == "Germany":
        return {
            "gov_fee_foreign": "EUR €75",
            "gov_fee_breakdown": "€75 (Chancenkarte / National Visa Type D Application Fee). ZAB Statement of Comparability: €208.",
            "gov_fee_inr_approx": "₹7,000 (Visa) + ₹19,000 (ZAB Qualification Evaluation)",
            "leamss_retainer_inr": "₹95,000 (+ 18% GST)",
            "leamss_milestones": "50% Onboarding & Anabin/ZAB Credential Filing ➔ 50% Chancenkarte Visa Filing",
            "statutory_benchmark": "6 Points minimum on the German Opportunity Card Points Grid.",
            "settlement_funds": "Statutory Blocked Account (Sperrkonto): €1,027/month (€12,324/year).",
            "official_portal": "https://www.make-it-in-germany.com/en/visa-residence/types/chancenkarte-opportunity-card",
        }
    elif c_norm == "United Kingdom":
        return {
            "gov_fee_foreign": "GBP £719 – £1,420 + £1,035/yr IHS",
            "gov_fee_breakdown": "Application fee £719 (up to 3 years) or £1,420 (over 3 years). Immigration Health Surcharge (IHS): £1,035/year.",
            "gov_fee_inr_approx": "₹78,000 (Visa) + ₹1,12,000/year (IHS)",
            "leamss_retainer_inr": "₹1,10,000 (+ 18% GST)",
            "leamss_milestones": "50% Onboarding & Sponsor Verification ➔ 50% UKVI Visa Application",
            "statutory_benchmark": "70 Points mandatory under UK Points-Based System (50 non-tradeable + 20 tradeable).",
            "settlement_funds": "£1,270 in bank account for 28 consecutive days unless sponsor certifies maintenance.",
            "official_portal": "https://www.gov.uk/government/publications/skilled-worker-visa-immigration-salary-list",
        }
    elif c_norm == "United States":
        return {
            "gov_fee_foreign": "USD $460 – $2,500+",
            "gov_fee_breakdown": "USCIS Form I-129 Base Fee: $460. Fraud Prevention Fee: $500. ACWIA Fee: $750 or $1,500. Asylum Program Fee: $600 (large) or $300 (small). Premium Processing (optional): $2,805.",
            "gov_fee_inr_approx": "₹1,50,000 – ₹2,50,000 (Filing fees)",
            "leamss_retainer_inr": "₹1,50,000 (+ 18% GST)",
            "leamss_milestones": "40% Onboarding & LCA Preparation ➔ 30% Petition Assembly ➔ 30% USCIS Filing",
            "statutory_benchmark": "Specialty occupation requiring at least a US Bachelor's degree and prevailing wage certified LCA.",
            "settlement_funds": "Employer sponsored / prevailing wage compliance.",
            "official_portal": "https://www.uscis.gov/working-in-the-united-states",
        }

    return {
        "gov_fee_foreign": "Variable by Subclass",
        "gov_fee_breakdown": "Statutory consular and visa processing charges.",
        "gov_fee_inr_approx": "₹1,00,000 – ₹2,50,000",
        "leamss_retainer_inr": "₹1,25,000 (+ 18% GST)",
        "leamss_milestones": "40% Retainer ➔ 30% Filing ➔ 30% Lodgement",
        "statutory_benchmark": "Standard statutory eligibility criteria.",
        "settlement_funds": "National bank balance benchmark.",
        "official_portal": "https://leamss.com/atlas/",
    }


def synthesize_complete_statutory_response(
    profile: Optional[FullOccupationProfile],
    det: Optional[OccupationDetection],
    country: str,
    visa_product_name: str,
    visa_subclass: str,
    client_scenario: str,
) -> str:
    """Synthesizes the complete, authoritative 7-part statutory response."""
    c_norm = profile.country if profile else normalize_country(country)
    auth_name = profile.assessing_authority if profile else "Statutory Immigration Authority"
    code_str = profile.code if profile else "N/A"
    title_str = profile.title if profile else visa_product_name
    fees = get_statutory_fees_and_commercials(c_norm, visa_subclass)
    questions = generate_sales_qualification_questions(profile, c_norm)

    # Section 1: Regulatory Clarification & Mismatch Warning
    clarification_block = ""
    if det and det.is_mismatch and det.mismatch_warning:
        clarification_block = (
            f"> [!WARNING]\n"
            f"> **CRITICAL SYSTEM CLARIFICATION FOR SALES CONSULTANT**\n"
            f"> {det.mismatch_warning}\n"
        )
        if det.crosswalk_code and det.crosswalk_title:
            clarification_block += (
                f"> \n"
                f"> **Equivalent Occupation in {det.selected_country}:** `{det.crosswalk_code}` — **{det.crosswalk_title}** "
                f"(Assessing Body: *{det.crosswalk_authority or 'Designated Authority'}*).\n"
                f"> *Below is the authoritative statutory breakdown for the queried code ({det.code}), followed by cross-walk guidance for {det.selected_country}.*\n\n"
            )

    # Section 2: Complete Occupation Details
    duties_list = "\n".join([f"- {d}" for d in (profile.main_duties if profile else ["Execute core professional responsibilities in accordance with official standards."])])
    reqs_list = "\n".join([f"- {r}" for r in (profile.employment_requirements if profile else ["Verifiable degree or diploma equivalency with designated assessing authority.", "Continuous relevant employment history."])])

    # Section 3: Visa Pathways & Points
    pathways_list = "\n".join([f"- **{p}**" for p in (profile.visa_pathways if profile else [f"{c_norm} General Skilled Migration", f"{c_norm} Employer Sponsorship"])])

    # Section 4: Qualification Questions
    questions_block = "\n".join(questions)

    # Section 5: Recommended Pitch Script
    phone_script = (
        f"> *\"Hello [Client Name], thank you for sharing your background. Based on current statutory guidelines from {auth_name}, "
        f"your profile falls squarely under **{title_str}** (Code: `{code_str}`). "
        f"Immigration authorities scrutinize employment references against the exact statutory task matrix. "
        f"At LEAMSS, our legal and technical team ensures your credentials, job duties, and assessment petition are structured for maximum points "
        f"and first-time approval without costly government rejections. Let us run a formal eligibility calculation to pinpoint your fastest pathway to permanent settlement.\"*"
    )

    rebuttal_block = (
        f"### 🛡️ Objections & Approved Consultant Rebuttals\n"
        f"- **Client Objection:** *\"Can you guarantee that I will get PR or visa approval?\"*\n"
        f"- **Approved Rebuttal:** *\"Under official immigration law, all visa and PR decisions are the statutory prerogative of government visa officers (e.g. IRCC, DHA, Home Affairs). "
        f"No legitimate immigration firm can guarantee a visa. What LEAMSS guarantees is institutional compliance: ensuring your paperwork, skills assessment, "
        f"points optimization, and employer reference letters conform 100% to official government regulations, preventing procedural refusals.\"*\n\n"
        f"- **Client Objection:** *\"My points are slightly lower than the recent draw cutoff. What should I do?\"*\n"
        f"- **Approved Rebuttal:** *\"Cutoffs fluctuate between draws. We employ three statutory levers: (1) Targeting regional or provincial nomination programs which award an instant bonus (+5 to +15 points in Australia, or 600 points in Canadian Express Entry PNP), "
        f"(2) Retaking English (PTE/IELTS) for up to 20 bonus points, and (3) Structuring spousal credentials for additional secondary applicant points.\"*"
    )

    # Section 6: Fees & Commercials
    fees_block = (
        f"- **Official Statutory Government Fee:** {fees['gov_fee_foreign']} (~{fees['gov_fee_inr_approx']})\n"
        f"  - *Fee Breakdown:* {fees['gov_fee_breakdown']}\n"
        f"- **LEAMSS Professional Retainer:** {fees['leamss_retainer_inr']}\n"
        f"- **Transparent Milestone Schedule:** {fees['leamss_milestones']}\n"
        f"- **Required Settlement Funds:** {fees['settlement_funds']}"
    )

    # Section 7: Sources & Disclaimers
    sources_block = (
        f"- **Official Administering Portal:** [{fees['official_portal']}]({fees['official_portal']})\n"
        f"- **Regulatory Gazette Reference:** *{profile.verification_date if profile else 'Current Official Gazette Indexation'}*\n"
        f"- **Verification Standard:** Cross-referenced against LEAMSS Product Master Catalog & Government Schedules.\n\n"
        f"> [!NOTE]\n"
        f"> **LEAMSS Statutory Disclaimer:** Immigration policies, points thresholds, and government visa charges are subject to official gazette notifications by sovereign immigration authorities. LEAMSS operates strictly under licensed consulting compliance and never guarantees visa approval."
    )

    # Quick Answer / Executive Summary block
    quick_answer_block = (
        f"### ⚡ Quick Answer (Live Call Summary)\n"
        f"- **Primary Pathway:** `{code_str}` ({title_str}) in {c_norm} under {auth_name} assessment standards.\n"
        f"- **Pass Benchmark:** {fees['statutory_benchmark']} with official statutory fee of {fees['gov_fee_foreign']} (~{fees['gov_fee_inr_approx']}).\n"
        f"- **Core Criteria:** Degree equivalence, minimum relevant skilled employment tenure, and authorized credential verification.\n\n"
    )

    return (
        f"{clarification_block}"
        f"## 📋 Official Immigration Regulatory Advisory: {c_norm} — {title_str}\n\n"
        f"**Classification Code:** `{code_str}` | **System:** {profile.classification_system if profile else 'Statutory System'} | **Administering Authority:** {auth_name}\n\n"
        f"{quick_answer_block}"
        f"### 📌 1. Regulatory Fact Check & Classification System\n"
        f"- **Destination Country:** {c_norm}\n"
        f"- **Skill Tier & Benchmark:** **{profile.skill_tier_label if profile else 'Skilled Classification'}**\n"
        f"- **Statutory Definition:** {profile.skill_tier_description if profile else 'Statutory criteria evaluated against formal degree and relevant employment tenure.'}\n"
        f"- **Official Occupational Scope:** {profile.definition if profile else 'Specialized skilled profession.'}\n\n"
        f"### 💼 2. Complete Occupation Details & Job Responsibilities\n"
        f"**Official Job Responsibilities & Core Duties:**\n"
        f"{duties_list}\n\n"
        f"**Statutory Employment & Qualification Requirements:**\n"
        f"{reqs_list}\n\n"
        f"### 📊 3. Eligible Visa Pathways, Points Systems & Salary Thresholds\n"
        f"{pathways_list}\n"
        f"- **Statutory Pass Mark / Points Benchmark:** {fees['statutory_benchmark']}\n"
        f"- **Statutory Wage Benchmark:** {profile.statutory_salary_threshold if profile else 'Subject to national median wage benchmarks.'}\n\n"
        f"### ❓ 4. Five Client Qualification Questions for Sales Consultant\n"
        f"{questions_block}\n\n"
        f"### 💬 5. Recommended Call Script & Phone Pitch for Sales Consultant\n"
        f"{phone_script}\n\n"
        f"{rebuttal_block}\n\n"
        f"### 💰 6. Official Statutory Government Fees & LEAMSS Commercials\n"
        f"{fees_block}\n\n"
        f"### 🔗 7. Official Government Sources & Verification Date\n"
        f"{sources_block}"
    )
