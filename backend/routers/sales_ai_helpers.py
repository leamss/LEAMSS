import json
import logging
import os
import re
import time as _time
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.ai_models import model_for
import httpx
from openai import AsyncOpenAI
router = APIRouter(prefix="/sales/ai", tags=["Smart Sales Helper - AI Helpers"])
logger = logging.getLogger(__name__)

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

_SHARED_HTTP_CLIENT = httpx.AsyncClient(
    verify=False,
    timeout=httpx.Timeout(45.0, connect=10.0),
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
)

_OCC_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_OCC_CACHE_TTL = 300.0  # 5 minutes


async def _get_available_codes(country_codes: Optional[List[str]]) -> List[Dict[str, Any]]:
    cache_key = ",".join(sorted(c.upper() for c in country_codes)) if country_codes else "ALL"
    now_t = _time.time()
    cached = _OCC_CACHE.get(cache_key)
    if cached and (now_t - cached[0]) < _OCC_CACHE_TTL:
        return cached[1]

    query: Dict[str, Any] = {"status": {"$ne": "superseded"}}
    if country_codes:
        query["country_code"] = {"$in": [c.upper() for c in country_codes]}

    available_codes: List[Dict[str, Any]] = []
    async for occ in db["occupation_master"].find(
        query,
        {
            "_id": 0,
            "country_code": 1,
            "code": 1,
            "title": 1,
            "hierarchy": 1,
            "assessing_authority": 1,
            "visa_pathways": 1,
            "alternative_titles": 1,
        },
    ):
        cc = (occ.get("country_code") or "AU").upper()
        code_str = str(occ.get("code") or "").strip()
        # Strictly require 6 digits for Australia (no 4-digit unit groups)
        if cc == "AU" and (len(code_str) != 6 or not code_str.isdigit()):
            continue

        aa = occ.get("assessing_authority") or {}
        hierarchy = occ.get("hierarchy") or {}
        pathway_lists = (occ.get("visa_pathways") or {}).get("pathway_lists") or []
        available_codes.append({
            "country_code": cc,
            "code": code_str,
            "title": occ.get("title"),
            "group": hierarchy.get("unit_group_name"),
            "assessing_body": aa.get("name"),
            "pathway": pathway_lists[0] if pathway_lists else None,
            "alternative_titles": occ.get("alternative_titles") or [],
        })

    _OCC_CACHE[cache_key] = (now_t, available_codes)
    return available_codes


from core.skills_assessment_engine import evaluate_skills_assessment, is_field_relevant_to_occupation
from core.anzsco_duties_knowledge import ANZSCO_UNIT_GROUP_DUTIES, lemmatize_token
from routers.au_classification_versions import (
    get_active_classification_versions,
    evaluate_occupation_classification_versions,
    DEFAULT_AU_CLASSIFICATIONS,
)

ROLE_SALES = {
    "admin", "admin_owner", "sales_executive", "sr_sales_executive",
    "sales_manager", "sales_head", "partner", "case_manager",
}


def _user_role(user: dict) -> str:
    return user.get("rbac_role") or user.get("role") or ""


def _can_access(user: dict) -> bool:
    return _user_role(user) in ROLE_SALES or "*" in (user.get("permissions") or [])


def _safe_json_loads(raw: str, fallback_codes: Optional[List[Dict[str, Any]]] = None) -> dict:
    """Robust multi-tier JSON parser for AI responses.
    Handles markdown fences, truncated JSON arrays, control chars, trailing commas,
    unescaped quotes, and falls back to regex extraction or heuristic pre-scored codes.
    """
    clean = (raw or "").strip()
    # Strip markdown fences
    clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean)
    clean = clean.strip()

    # Strategy 1: Direct load
    try:
        return json.loads(clean)
    except Exception:
        pass

    # Strategy 2: Remove non-whitespace control characters & trailing commas
    clean_sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", clean)
    clean_sanitized = re.sub(r",\s*([}\]])", r"\1", clean_sanitized)
    try:
        return json.loads(clean_sanitized)
    except Exception:
        pass

    # Strategy 3: Slice between first { and last }
    first = clean_sanitized.find("{")
    last = clean_sanitized.rfind("}")
    if first != -1 and last > first:
        sub = clean_sanitized[first:last + 1]
        try:
            return json.loads(sub)
        except Exception:
            pass
        # Try closing brackets if JSON was truncated mid-object or mid-array
        for tail in ['\n  ]\n}', '\n}', '"\n  ]\n}', '"}\n  ]\n}', '}\n  ]\n}', '"]}', ']}']:
            try:
                return json.loads(sub + tail)
            except Exception:
                pass
        last_obj = sub.rfind("},")
        if last_obj != -1:
            try:
                return json.loads(sub[:last_obj + 1] + "\n  ]\n}")
            except Exception:
                pass

    # Strategy 4: Bracket-matching to extract individual suggestion objects
    recovered_suggestions = []
    pos = 0
    while True:
        s_start = clean.find("{", pos)
        if s_start == -1:
            break
        depth = 0
        s_end = -1
        for i in range(s_start, len(clean)):
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
                if depth == 0:
                    s_end = i
                    break
        if s_end != -1:
            block = clean[s_start:s_end + 1]
            try:
                obj = json.loads(block)
                if isinstance(obj, dict):
                    if "suggestions" in obj and isinstance(obj["suggestions"], list):
                        return obj
                    if "code" in obj and "title" in obj:
                        recovered_suggestions.append(obj)
            except Exception:
                try:
                    cleaned_b = re.sub(r",\s*([}\]])", r"\1", block)
                    obj = json.loads(cleaned_b)
                    if isinstance(obj, dict) and "code" in obj and "title" in obj:
                        recovered_suggestions.append(obj)
                except Exception:
                    pass
            pos = s_end + 1
        else:
            pos = s_start + 1

    if recovered_suggestions:
        logger.info("Successfully recovered %d suggestions from partial JSON", len(recovered_suggestions))
        return {
            "suggestions": recovered_suggestions,
            "general_advice": "Suggestions recovered from AI response.",
            "_ai_status": "repaired",
        }

    # Strategy 5: Regex extraction for { "code": "...", "title": "..." } patterns
    pattern = re.compile(
        r'\{\s*"country_code"[\s\S]*?"code":\s*"(\d+)"[\s\S]*?"title":\s*"([^"]+)"[\s\S]*?\}'
    )
    for m in pattern.finditer(clean):
        try:
            item = json.loads(m.group(0))
            if item.get("code") and item.get("title"):
                recovered_suggestions.append(item)
        except Exception:
            pass

    if recovered_suggestions:
        return {
            "suggestions": recovered_suggestions,
            "general_advice": "Suggestions extracted from response text.",
            "_ai_status": "repaired",
        }

    # Strategy 6: Fallback to scored database codes if available
    if fallback_codes:
        logger.warning("All JSON parsing failed; falling back to %d pre-scored codes", len(fallback_codes))
        fallback_list = []
        for a in fallback_codes:
            fallback_list.append({
                "country_code": a.get("country_code", "AU"),
                "code": str(a.get("code", "")),
                "title": a.get("title", ""),
                "confidence": "medium",
                "reasoning": "Selected based on profile role and duties matching standard occupation keywords.",
                "considerations": "Please review assessing authority criteria and visa availability.",
                "assessing_body": a.get("assessing_body") or "",
                "pathway": a.get("pathway") or "",
            })
        return {
            "suggestions": fallback_list,
            "general_advice": "Recommended matches from occupation database based on profile description.",
            "_ai_status": "fallback",
        }

    raise ValueError("Could not parse JSON response from AI")


# ════════════════════════════════════════════════════════════════
# OCCUPATION SUGGESTER — natural-language → top 3-5 codes
# ════════════════════════════════════════════════════════════════
SUGGESTER_SYSTEM_PROMPT = """You are a senior Australian immigration and occupation-code assessment specialist.

A candidate's full professional profile will be provided, including:
- Detailed job descriptions and duty bullet points across their roles
- Current employer and company nature / business sector
- Qualifications (degrees, majors/fields of study, institutions)
- Years of professional experience and candidate age / DOB

Your task: from the AVAILABLE_CODES list provided, suggest the TOP 3-5 codes that
best match the candidate's ACTUAL DUTIES, ROLES & RESPONSIBILITIES, COMPANY NATURE, and
QUALIFICATIONS according to official assessing authority criteria (ACS, VETASSESS, TRA, Engineers Australia).

═══════════════════════════════════════════════════════════════════
ABSOLUTE RULES
═══════════════════════════════════════════════════════════════════

🔴 RULE 1 — Review the FULL RESUME & PROFILE. Do NOT just match superficial designation titles. Match on actual daily roles, responsibilities, and tasks performed.
🔴 RULE 2 — Validate COMPANY NATURE & INDUSTRY. The nature of the employer's business must align with the occupation's industry domain.
🔴 RULE 3 — Validate QUALIFICATIONS against ASSESSING AUTHORITY CRITERIA (e.g. ACS ICT major requirements, VETASSESS Group A/B degree relevance, TRA trade apprenticeship, Engineers Australia Washington Accord / CDR).
🔴 RULE 4 — Only suggest codes from the AVAILABLE_CODES list. Do NOT invent codes.
🔴 RULE 5 — Be honest about confidence: HIGH (strong duty, company, and qualification alignment), MEDIUM (related but adjacent), LOW (partial match).
🔴 RULE 6 — Clearly explain duty alignment, company nature alignment, and assessing body deduction rules in the reasoning.
🔴 RULE 7 — AUSTRALIA OCCUPATION CODES MUST BE EXACTLY 6 DIGITS: For country AU, suggest ONLY official 6-digit ANZSCO occupation codes (e.g. 261312, 261313, 221111). NEVER return 4-digit unit group codes (e.g. 2613 is a unit group, NOT a valid occupation code). Every AU code must be exactly 6 digits.
🔴 RULE 8 — EVALUATE DUAL CLASSIFICATION PATHWAYS: Identify whether the occupation qualifies for General Skilled Migration (ANZSCO 2013: Subclasses 189, 190, 491, 494) and/or Employer Sponsored (OSCA 2022 / CSOL: Subclasses 482, 186, 407, 485). Mention visa availability in considerations.
🔴 RULE 9 — ANALYSE ALL WORK EXPERIENCE (PAST AND CURRENT): Do NOT evaluate only the candidate's latest or current job title. Evaluate the candidate's ENTIRE employment chronology across all past and current roles. If the candidate has worked across multiple distinct relevant occupations throughout their career (e.g. 3 years as a Software Developer and 3 years as a DevOps Engineer/Systems Analyst, or Junior Accountant then Auditor), suggest the top matching occupation codes corresponding to their various qualified career stages so the consultant can choose the best migration pathway.
🔴 RULE 10 — NO LAZY DEFAULTING TO 221111 (ACCOUNTANT) OR 224713 (MANAGEMENT CONSULTANT): Base suggestions strictly on actual duties performed. If candidate is a Finance Manager, FP&A lead, or Corporate Finance leader, suggest 132211 (Finance Manager) or 222312 (Financial Investment Manager) — NEVER suggest Accountant (221111) unless their primary day-to-day duties were statutory bookkeeping, general ledgers, and tax compliance. NEVER suggest Management Consultant (224713) unless the candidate actually worked in consulting/advisory or business transformation.

═══════════════════════════════════════════════════════════════════
OUTPUT FORMAT — return ONLY this JSON, no markdown, no prose:
═══════════════════════════════════════════════════════════════════
{
  "suggestions": [
    {
      "country_code": "AU",
      "code": "261313",
      "title": "Software Engineer",
      "confidence": "high|medium|low",
      "reasoning": "Specific explanation synthesizing duty alignment, company nature, and assessing authority qualification match.",
      "considerations": "Exact assessing authority rules, deductions required, and documentation needed.",
      "assessing_body": "ACS",
      "pathway": "MLTSSL"
    }
  ],
  "general_advice": "1-2 sentences advising the consultant on assessing authority strategy and points maximization."
}
"""


class SuggestRequest(BaseModel):
    description: str = Field(..., min_length=15, max_length=4000, description="Free-text description or full resume text of the candidate's profession")
    country_codes: Optional[List[str]] = Field(None, description="Restrict to these countries (default: all)")
    max_suggestions: int = Field(5, ge=1, le=8)
    qualification: Optional[str] = Field(None, description="Highest qualification level (e.g. bachelor, master, diploma)")
    field_of_study: Optional[str] = Field(None, description="Field of study / degree major (e.g. Computer Science, Commerce)")
    years_experience_total: Optional[float] = Field(None, description="Total years of professional experience")
    profile: Optional[Dict[str, Any]] = Field(None, description="Full candidate profile if available")
    target_subclasses: Optional[List[str]] = Field(None, description="Optional target visa subclasses (e.g. ['189', '190', '482']) to prioritize")
    target_framework: Optional[str] = Field(None, description="Optional target classification framework: 'ANZSCO_2013', 'OSCA_2022', or 'ALL'")


def extract_subclasses_from_text(text: str) -> List[str]:
    """Extract Australian visa subclasses mentioned in text (e.g. 189, 190, 491, 494, 482, 186, 407, 485)."""
    if not text:
        return []
    valid_subclasses = {"189", "190", "491", "494", "482", "186", "407", "485", "191"}
    found = []
    matches = re.findall(r'(?:subclass|visa|sc)?\s*\b(189|190|491|494|482|186|407|485)\b', text, re.IGNORECASE)
    for m in matches:
        if m in valid_subclasses and m not in found:
            found.append(m)
    return found


STOP_WORDS = {
    "with", "and", "the", "for", "years", "year", "experience", "holds", "held",
    "master", "masters", "bachelor", "bachelors", "degree", "client", "current",
    "role", "roles", "work", "worked", "working", "job", "candidate", "profile",
    "overall", "total", "skills", "assessment", "level", "post", "have", "has",
    "from", "also", "been", "their", "this", "that", "these", "those", "under",
    "over", "into", "onto", "education", "qualified", "qualifications", "completed",
    "history", "details", "applicant", "primary", "full", "time", "general", "responsible",
    "duties", "including", "across", "various", "multiple", "using", "well"
}

SYNONYM_DOMAINS = {
    "business_management": {
        "roots": [
            "advisori", "consult", "transform", "govern", "benchmarking", "restructur",
            "framework", "organis", "corporat govern", "chang manag"
        ],
        "occ_codes": ["224713", "224712", "132411", "111211", "224999"],
    },
    "human_resources": {
        "roots": ["human resourc", "talent", "recruit", "onboard", "apprais", "workplace relat", "employe", "personnel", "remuner", "grievanc", "headhunt", "staffing"],
        "occ_codes": ["223111", "223112", "223113", "132311"],
    },
    "sales_business_dev": {
        "roots": ["b2b", "sale", "quotat", "tender", "prospect", "negotiat", "client relat", "pipelin", "territori", "quota", "account manag", "account execut"],
        "occ_codes": ["225411", "225412", "131112", "225211", "225212"],
    },
    "construction_management": {
        "roots": ["construct", "site manag", "subcontractor", "site supervis", "build", "defect", "handov", "boq", "site safeti", "contractor"],
        "occ_codes": ["133111", "133112", "312111", "312112"],
    },
    "supply_chain_logistics": {
        "roots": ["suppli chain", "logist", "procure", "warehous", "inventori", "distribut", "freight", "customs", "sourc", "carrier", "custom clearance"],
        "occ_codes": ["133611", "133612", "225211"],
    },
    "design_multimedia": {
        "roots": ["graphic", "illustrat", "ui", "ux", "figma", "photoshop", "wirefram", "visual", "animat", "brand ident", "layout", "creative", "design system"],
        "occ_codes": ["232411", "232412", "232413", "232414", "261211", "261212"],
    },
    "software_dev": {
        "roots": ["program", "code", "develop", "softwar", "api", "microservic", "backend", "frontend", "fullstack", "script", "comput", "algorithm", "architect", "datab", "sql", "git", "cloud", "aws", "docker", "deploy", "debug", "test", "optimis", "framework"],
        "occ_codes": ["261311", "261312", "261313", "261399", "261111", "261112", "262111", "262112", "262113"],
    },
    "culinary_hospitality": {
        "roots": ["cook", "chef", "culinari", "kitchen", "food", "menu", "platter", "salad", "appet", "dessert", "hygien", "haccp", "dish", "meal", "baker", "pastri", "restaur", "hotel", "cater", "garde", "hospital"],
        "occ_codes": ["351311", "351411", "351111", "351112", "351211", "141111", "141211", "141311"],
    },
    "legal_practice": {
        "roots": ["law", "legal", "solicitor", "advocate", "barrister", "litigat", "court", "counsel", "brief", "draft", "contract", "plead", "judg", "tribun", "conveyanc"],
        "occ_codes": ["271311", "271111", "271214", "271299", "599112", "599214"],
    },
    "clinical_biotech": {
        "roots": ["clinic", "trial", "biomarker", "biotech", "laboratori", "bioch", "pharmac", "protocol", "gcp", "fda", "regul", "specimen", "cell", "molecul", "genom"],
        "occ_codes": ["234599", "234511", "234513", "234514", "234518", "234611"],
    },
    "allied_health": {
        "roots": ["physio", "radiograph", "x-ray", "mri", "ultrasound", "sonograph", "musculoskelet", "rehabilit", "ergonom", "patholog", "occup therap"],
        "occ_codes": ["252511", "252411", "251211", "251212", "251214", "234611"],
    },
    "social_community": {
        "roots": ["social work", "welfar", "communiti", "counsel", "casework", "crisis", "disabil", "youth", "child protect"],
        "occ_codes": ["272511", "272613", "411711", "411712", "411713", "411714", "411715", "411716"],
    },
    "nursing_healthcare": {
        "roots": ["nurse", "nurs", "patient", "ward", "icu", "medic", "care", "dosag", "triage", "vitals", "clinic", "hospital", "health"],
        "occ_codes": ["254411", "254412", "254413", "254414", "254415", "254418", "254421", "254422", "254423", "254499"],
    },
    "accounting_finance": {
        "roots": ["account", "tax", "audit", "balanc", "ledger", "financ", "invoic", "reconcil", "budget", "asset", "profit", "cpa", "fiscal", "expens", "treasuri", "fp&a"],
        "occ_codes": ["221111", "221112", "221113", "222311", "222312", "132211"],
    },
    "civil_construction": {
        "roots": ["civil", "structur", "concret", "draw", "cad", "bim", "foundat", "drainag", "road", "infrastruct"],
        "occ_codes": ["233211", "233212", "233214", "233215", "312211", "312212"],
    },
    "mechanical_eng": {
        "roots": ["mechan", "hvac", "thermodynam", "pip", "pump", "engin", "machin", "robot", "fabric", "vehicl"],
        "occ_codes": ["233512", "233513", "312511", "312512"],
    },
    "electrical_eng": {
        "roots": ["electr", "power", "circuit", "voltag", "substat", "generat", "wiring", "transmiss", "cabl"],
        "occ_codes": ["233311", "312311", "341111"],
    },
    "teaching_education": {
        "roots": ["teach", "lesson", "student", "class", "curriculum", "pupil", "school", "educ", "pedagogi", "kindergarten", "preschool"],
        "occ_codes": ["241111", "241213", "241411", "242111"],
    },
    "actuarial_data_science": {
        "roots": ["actuari", "mathemat", "statist", "biostatist", "econometr", "quantit", "risk model", "probabl"],
        "occ_codes": ["224111", "224112", "224113"],
    },
}


ANZSCO_MAJOR_GROUP_KEYWORDS: Dict[str, Dict[str, Any]] = {
    "26": {
        "domain_name": "ICT & Software",
        "keywords": [
            "software", "developer", "programmer", "coding", "python", "java", "react", "django",
            "node", "javascript", "backend", "frontend", "fullstack", "devops", "cloud", "aws",
            "docker", "kubernetes", "database", "sql", "postgres", "api", "microservice",
            "microservices", "sysadmin", "cybersecurity", "network", "web application", "system analyst",
            "business analyst", "it consultant", "qa tester", "test automation"
        ],
        "unit_prefixes": ["2611", "2612", "2613", "2621", "2631", "2632", "2633"],
    },
    "2231": {
        "domain_name": "Human Resources & Talent Management",
        "keywords": [
            "human resources", "hr specialist", "hr adviser", "hr manager", "talent acquisition",
            "recruiter", "recruitment consultant", "onboarding", "workplace relations",
            "employee relations", "performance appraisal", "people and culture", "staffing",
            "remuneration", "payroll coordination", "grievance handling"
        ],
        "unit_prefixes": ["2231", "1323"],
    },
    "1311": {
        "domain_name": "Corporate Sales, B2B & Account Management",
        "keywords": [
            "account manager", "key account manager", "sales representative", "b2b sales",
            "sales manager", "sales director", "business development manager", "territory sales",
            "technical sales", "commercial tenders", "sales quota", "client relationship manager"
        ],
        "unit_prefixes": ["1311", "2254", "2252"],
    },
    "1331": {
        "domain_name": "Construction Management & Building",
        "keywords": [
            "construction manager", "construction project manager", "project builder",
            "site manager", "site supervisor", "building contractor", "subcontractor",
            "progress claims", "structural drawings", "construction site", "tender bid"
        ],
        "unit_prefixes": ["1331", "3121"],
    },
    "1336": {
        "domain_name": "Supply Chain & Logistics Management",
        "keywords": [
            "supply chain manager", "logistics manager", "procurement manager", "warehouse manager",
            "inventory management", "distribution manager", "freight forwarding", "customs clearance",
            "shipping logistics", "vendor management"
        ],
        "unit_prefixes": ["1336", "2252"],
    },
    "2324": {
        "domain_name": "Design & Multimedia",
        "keywords": [
            "graphic designer", "web designer", "ui designer", "ux designer", "ui/ux",
            "illustrator", "multimedia designer", "visual designer", "product designer",
            "figma", "photoshop", "wireframes", "design systems"
        ],
        "unit_prefixes": ["2324", "2612", "2323", "2325"],
    },
    "1322": {
        "domain_name": "Finance Management & Executive Leadership",
        "keywords": [
            "finance manager", "financial manager", "financial controller", "head of finance",
            "director of finance", "vp finance", "cfo", "chief financial officer", "treasurer",
            "financial planning and analysis", "fp&a", "p&l ownership", "pricing strategy",
            "capital allocation", "commercial finance", "finance partner"
        ],
        "unit_prefixes": ["1322", "1112", "2223"],
    },
    "2223": {
        "domain_name": "Financial Investment & Advisory",
        "keywords": [
            "financial analyst", "investment manager", "portfolio manager", "investment analyst",
            "due diligence", "financial modeling", "wealth manager", "equity research",
            "valuation", "market analysis", "forecasting", "asset allocation"
        ],
        "unit_prefixes": ["2223", "2221", "2222", "1322"],
    },
    "2247": {
        "domain_name": "Management & Strategy Consulting",
        "keywords": [
            "management consultant", "strategy consultant", "business consultant",
            "management consulting", "advisory consultant", "business transformation",
            "operating model restructuring", "change management"
        ],
        "unit_prefixes": ["2247"],
    },
    "2241": {
        "domain_name": "Actuarial, Mathematics & Statistics",
        "keywords": [
            "actuary", "actuarial", "mathematician", "statistician", "biostatistician",
            "econometrician", "quantitative analyst", "risk modeling", "statistical modeling"
        ],
        "unit_prefixes": ["2241"],
    },
    "2244": {
        "domain_name": "Policy & Intelligence Analysis",
        "keywords": [
            "policy analyst", "intelligence officer", "intelligence analyst", "policy officer",
            "public policy", "strategic policy", "defence intelligence"
        ],
        "unit_prefixes": ["2244"],
    },
    "2211": {
        "domain_name": "Accounting & Taxation",
        "keywords": [
            "accountant", "accounting", "balance sheet", "ledger", "reconciliation", "taxation",
            "tax return", "bas", "gst", "cpa", "financial statements", "bookkeeper",
            "general ledger", "statutory audit", "trial balance"
        ],
        "unit_prefixes": ["2211", "2212"],
    },
    "2332": {
        "domain_name": "Civil & Structural Engineering",
        "keywords": [
            "civil engineer", "structural engineer", "concrete", "structural design", "drainage",
            "stormwater", "autocad", "site inspection", "bridge", "road alignment", "geotechnical",
            "quantity surveyor", "earthworks", "construction site"
        ],
        "unit_prefixes": ["2332", "3122"],
    },
    "2335": {
        "domain_name": "Mechanical & Industrial Engineering",
        "keywords": [
            "mechanical engineer", "hvac", "thermodynamics", "piping", "pumps", "cad", "solidworks",
            "ansys", "stress analysis", "machinery", "fabrication", "industrial engineer", "plant engineer"
        ],
        "unit_prefixes": ["2335", "3125"],
    },
    "2333": {
        "domain_name": "Electrical & Electronics Engineering",
        "keywords": [
            "electrical engineer", "electronics engineer", "substation", "high voltage", "circuit design",
            "power distribution", "switchgear", "plc", "scada", "telecommunications"
        ],
        "unit_prefixes": ["2333", "2334", "3123"],
    },
    "2251": {
        "domain_name": "Marketing & Advertising",
        "keywords": [
            "marketing", "digital marketing", "seo", "google ads", "social media", "campaign",
            "lead generation", "content marketing", "copywriter", "advertising", "branding", "marketing specialist"
        ],
        "unit_prefixes": ["2251", "2253"],
    },
    "2544": {
        "domain_name": "Nursing & Midwifery",
        "keywords": [
            "registered nurse", "nursing", "patient care", "triage", "medication administration",
            "iv infusion", "wound care", "hospital ward", "icu", "clinical nurse", "midwife"
        ],
        "unit_prefixes": ["2544", "2541", "2542"],
    },
    "2525": {
        "domain_name": "Allied Health & Radiation",
        "keywords": [
            "physiotherapist", "radiographer", "medical radiation", "sonographer", "ultrasound",
            "occupational therapist", "musculoskeletal", "rehabilitation", "x-ray"
        ],
        "unit_prefixes": ["2525", "2524", "2512"],
    },
    "2345": {
        "domain_name": "Life Sciences & Medical Laboratory",
        "keywords": [
            "biotechnologist", "microbiologist", "biochemist", "life scientist", "clinical trial",
            "molecular biologist", "genetics", "medical laboratory scientist", "pathology"
        ],
        "unit_prefixes": ["2345", "2346", "2341"],
    },
    "2725": {
        "domain_name": "Social Work & Community Welfare",
        "keywords": [
            "social worker", "community worker", "welfare worker", "youth worker", "caseworker",
            "crisis counsellor", "child protection", "disabilities services officer"
        ],
        "unit_prefixes": ["2725", "2726", "4117"],
    },
    "3513": {
        "domain_name": "Chefs & Food Hospitality",
        "keywords": [
            "chef", "head chef", "sous chef", "cook", "kitchen", "menu planning", "food preparation",
            "culinary", "haccp", "pastry", "catering", "baker", "commis"
        ],
        "unit_prefixes": ["3513", "3514", "3511", "3512", "1411", "1412"],
    },
    "3312": {
        "domain_name": "Carpentry & Trades",
        "keywords": [
            "carpenter", "joiner", "framing", "formwork", "cabinetmaker", "plumber", "electrician",
            "motor mechanic", "welder", "fitter", "fabricator", "bricklayer", "tiler"
        ],
        "unit_prefixes": ["3312", "3341", "3411", "3223", "3212", "3232"],
    },
    "2411": {
        "domain_name": "Education & Teaching",
        "keywords": [
            "teacher", "secondary school teacher", "primary school teacher", "early childhood teacher",
            "kindergarten", "lesson plans", "curriculum", "pedagogy", "school teaching"
        ],
        "unit_prefixes": ["2411", "2412", "2414", "2421"],
    },
}


def extract_profession_from_text(text: str) -> str:
    """Intelligently extract the candidate's current profession / designation from description or resume text."""
    if not text:
        return ""

    known_titles = [
        r"(?:senior\s+|lead\s+|principal\s+|junior\s+)?(?:software\s+developer|software\s+engineer|developer\s+programmer|web\s+developer|full\s*stack\s+developer|frontend\s+developer|backend\s+developer|devops\s+engineer|data\s+scientist|data\s+analyst|systems\s+analyst|database\s+administrator|network\s+engineer|cyber\s+security\s+specialist|cloud\s+engineer|ict\s+business\s+analyst)",
        r"(?:civil|structural|mechanical|electrical|electronics|chemical|biomedical|industrial|telecommunications)\s+engineer",
        r"(?:construction\s+manager|construction\s+project\s+manager|project\s+builder|site\s+manager)",
        r"(?:supply\s+chain\s+manager|logistics\s+manager|procurement\s+manager|warehouse\s+manager)",
        r"(?:human\s+resources\s+specialist|human\s+resources\s+adviser|hr\s+manager|recruitment\s+consultant|talent\s+acquisition\s+specialist)",
        r"(?:key\s+account\s+manager|account\s+manager|technical\s+sales\s+representative|sales\s+and\s+marketing\s+manager|business\s+development\s+manager)",
        r"(?:graphic\s+designer|web\s+designer|ui/ux\s+designer|ui\s+designer|ux\s+designer|illustrator|multimedia\s+designer)",
        r"(?:general\s+|taxation\s+|management\s+)?accountant|internal\s+auditor|external\s+auditor|financial\s+analyst|finance\s+manager",
        r"(?:registered\s+nurse|nurse|physiotherapist|occupational\s+therapist|medical\s+laboratory\s+scientist|pharmacist|general\s+practitioner|radiographer|sonographer)",
        r"(?:social\s+worker|community\s+worker|welfare\s+worker|youth\s+worker)",
        r"(?:head\s+chef|sous\s+chef|chef|cook|pastry\s+cook|baker|carpenter|plumber|electrician|motor\s+mechanic|welder|fitter)",
        r"(?:digital\s+marketing\s+specialist|marketing\s+specialist|advertising\s+specialist|public\s+relations\s+professional)",
        r"(?:early\s+childhood\s+teacher|primary\s+school\s+teacher|secondary\s+school\s+teacher|university\s+lecturer)",
    ]
    for kt in known_titles:
        m = re.search(r'\b(' + kt + r')\b', text, re.IGNORECASE)
        if m:
            return m.group(1).strip().title()

    m = re.search(r'(?:current\s+)?(?:designation|role|profession|job\s+title|title|position)[\s:]+([A-Za-z\s/&-]+?)(?=[,\.\n\(\)]|$)', text, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        if len(val) >= 3 and len(val) <= 50 and not any(w in val.lower() for w in ["completed", "bachelor", "master", "years", "experience"]):
            return val.title()

    m = re.search(r'(?:working|worked|work|experience|employed|serving)\s+(?:as|in\s+the\s+role\s+of)\s+(?:an?|the)?\s*([A-Za-z\s/&-]+?)(?=[,\.\n\(\)]|\s+for|\s+with|\s+at|\s+in\s+[A-Z]|\s+having|\s+handling|\s+designing|\s+developing|\s+creating|$)', text, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        if len(val) >= 3 and len(val) <= 50 and not any(w in val.lower() for w in ["completed", "bachelor", "master", "years"]):
            return val.title()

    first_line = text.strip().splitlines()[0]
    if len(first_line) < 45 and not any(c in first_line for c in ["@", "http", "{", "}", ".", ","]):
        return first_line.strip().title()
    return ""


def extract_all_professions_from_text(text: str) -> List[str]:
    """Extract ALL job titles and designations found across the candidate's work history and resume text."""
    if not text:
        return []

    found = []
    known_titles = [
        r"(?:senior\s+|lead\s+|principal\s+|junior\s+|associate\s+)?(?:software\s+developer|software\s+engineer|developer\s+programmer|web\s+developer|full\s*stack\s+developer|frontend\s+developer|backend\s+developer|devops\s+engineer|data\s+scientist|data\s+analyst|systems\s+analyst|database\s+administrator|network\s+engineer|cyber\s+security\s+specialist|cloud\s+engineer|cloud\s+architect|solutions\s+architect|ict\s+business\s+analyst|qa\s+engineer|test\s+automation\s+engineer)",
        r"(?:civil|structural|mechanical|electrical|electronics|chemical|biomedical|industrial|telecommunications)\s+engineer",
        r"(?:construction\s+manager|construction\s+project\s+manager|project\s+builder|site\s+manager)",
        r"(?:supply\s+chain\s+manager|logistics\s+manager|procurement\s+manager|warehouse\s+manager)",
        r"(?:human\s+resources\s+specialist|human\s+resources\s+adviser|hr\s+manager|recruitment\s+consultant|talent\s+acquisition\s+specialist)",
        r"(?:key\s+account\s+manager|account\s+manager|technical\s+sales\s+representative|sales\s+and\s+marketing\s+manager|business\s+development\s+manager)",
        r"(?:graphic\s+designer|web\s+designer|ui/ux\s+designer|ui\s+designer|ux\s+designer|illustrator|multimedia\s+designer)",
        r"(?:general\s+|taxation\s+|management\s+)?accountant|internal\s+auditor|external\s+auditor|financial\s+analyst|finance\s+manager",
        r"(?:registered\s+nurse|nurse|physiotherapist|occupational\s+therapist|medical\s+laboratory\s+scientist|pharmacist|general\s+practitioner|radiographer|sonographer)",
        r"(?:social\s+worker|community\s+worker|welfare\s+worker|youth\s+worker)",
        r"(?:head\s+chef|sous\s+chef|chef|cook|pastry\s+cook|baker|carpenter|plumber|electrician|motor\s+mechanic|welder|fitter)",
        r"(?:digital\s+marketing\s+specialist|marketing\s+specialist|advertising\s+specialist|public\s+relations\s+professional)",
        r"(?:early\s+childhood\s+teacher|primary\s+school\s+teacher|secondary\s+school\s+teacher|university\s+lecturer)",
    ]

    for kt in known_titles:
        for m in re.finditer(r'\b(' + kt + r')\b', text, re.IGNORECASE):
            t = m.group(1).strip().title()
            if t not in found:
                found.append(t)

    for m in re.finditer(r'(?:designation|role|profession|job\s+title|title|position)[\s:]+([A-Za-z\s/&-]+?)(?=[,\.\n\(\)]|$)', text, re.IGNORECASE):
        val = m.group(1).strip().title()
        if len(val) >= 3 and len(val) <= 50 and not any(w in val.lower() for w in ["completed", "bachelor", "master", "years", "experience"]):
            if val not in found:
                found.append(val)

    for m in re.finditer(r'(?:working|worked|work|experience|employed|serving)\s+(?:as|in\s+the\s+role\s+of)\s+(?:an?|the)?\s*([A-Za-z\s/&-]+?)(?=[,\.\n\(\)]|\s+for|\s+with|\s+at|\s+in\s+[A-Z]|\s+having|\s+handling|\s+designing|\s+developing|\s+creating|$)', text, re.IGNORECASE):
        val = m.group(1).strip().title() if m else ""
        if val and len(val) >= 3 and len(val) <= 50 and not any(w in val.lower() for w in ["completed", "bachelor", "master", "years"]):
            if val not in found:
                found.append(val)

    return found

    for kt in known_titles:
        for m in re.finditer(r'\b(' + kt + r')\b', text, re.IGNORECASE):
            t = m.group(1).strip().title()
            if t not in found:
                found.append(t)

    for m in re.finditer(r'(?:designation|role|profession|job\s+title|title|position)[\s:]+([A-Za-z\s/&-]+?)(?=[,\.\n\(\)]|$)', text, re.IGNORECASE):
        val = m.group(1).strip().title()
        if len(val) >= 3 and len(val) <= 50 and not any(w in val.lower() for w in ["completed", "bachelor", "master", "years", "experience"]):
            if val not in found:
                found.append(val)

    for m in re.finditer(r'(?:working|worked|work|experience|employed|serving)\s+(?:as|in\s+the\s+role\s+of)\s+(?:an?|the)?\s*([A-Za-z\s/&-]+?)(?=[,\.\n\(\)]|\s+for|\s+with|\s+at|\s+in\s+[A-Z]|\s+having|\s+handling|\s+designing|\s+developing|\s+creating|$)', text, re.IGNORECASE):
        val = m.group(1).strip().title() if m else ""
        if val and len(val) >= 3 and len(val) <= 50 and not any(w in val.lower() for w in ["completed", "bachelor", "master", "years"]):
            if val not in found:
                found.append(val)

    return found


def extract_experience_years_from_text(text: str) -> Optional[float]:
    """Extract years of experience from description text if present."""
    if not text:
        return None
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)(?:\s+of)?\s*(?:work\s+|professional\s+)?experience', text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def title_tokens_overlap(cand_title: str, occ_title: str, alt_titles: list) -> float:
    """Calculate token overlap between candidate designation and official occupation title."""
    seniority = {"senior", "junior", "lead", "principal", "associate", "head", "chief", "assistant", "staff", "executive", "general", "nec", "specialist", "officer", "professional"}
    cand_tokens = {lemmatize_token(w) for w in re.findall(r'\b[a-zA-Z]{3,}\b', (cand_title or "").lower()) if w not in seniority and w not in STOP_WORDS}
    occ_tokens = {lemmatize_token(w) for w in re.findall(r'\b[a-zA-Z]{3,}\b', (occ_title or "").lower()) if w not in seniority and w not in STOP_WORDS}
    if not cand_tokens or not occ_tokens:
        return 0.0

    common = cand_tokens.intersection(occ_tokens)
    if common:
        return len(common) / min(len(cand_tokens), len(occ_tokens))

    for alt in (alt_titles or []):
        alt_tokens = {lemmatize_token(w) for w in re.findall(r'\b[a-zA-Z]{3,}\b', str(alt).lower()) if w not in seniority and w not in STOP_WORDS}
        alt_common = cand_tokens.intersection(alt_tokens)
        if alt_common:
            return len(alt_common) / min(len(cand_tokens), len(alt_tokens))

    return 0.0


def _stem(word: str) -> str:
    return lemmatize_token(word)


def calculate_duty_alignment(cand_duties_text: str, occ_tasks: list, occ_code: str) -> tuple:
    """Calculate semantic duty alignment against official ABS ANZSCO tasks."""
    code_str = str(occ_code or "").strip()
    unit_prefix = code_str[:4]

    # Combine occupation tasks with official ABS ANZSCO unit group tasks
    combined_tasks = list(occ_tasks or [])
    unit_tasks = ANZSCO_UNIT_GROUP_DUTIES.get(unit_prefix, [])
    for ut in unit_tasks:
        if ut not in combined_tasks:
            combined_tasks.append(ut)

    if not combined_tasks:
        return 0.0, [], 0

    cand_words = {_stem(w) for w in re.findall(r'\b[a-zA-Z]{3,}\b', cand_duties_text.lower()) if w not in STOP_WORDS}
    matched_tasks = []
    generic_verbs = {"manag", "admin", "operat", "organis", "plan", "servic", "direct", "coordinat"}

    for task in combined_tasks:
        task_words = {_stem(w) for w in re.findall(r'\b[a-zA-Z]{3,}\b', task.lower()) if w not in STOP_WORDS}
        common = cand_words.intersection(task_words)
        meaningful_common = [c for c in common if c not in generic_verbs]
        if len(common) >= 2 and len(meaningful_common) >= 1:
            matched_tasks.append((task, list(common)))
        elif len(common) >= 1 and any(c in [
            "program", "code", "design", "test", "architect", "cook", "menu", "court",
            "law", "develop", "api", "haccp", "audit", "tax", "nurse", "welder", "mechanic",
            "teach", "culinari", "pastri", "conveyanc", "plead", "litigat", "microservic",
            "docker", "kubernetes", "database", "postgres", "sql", "cloud", "aws", "azure"
        ] for c in common):
            matched_tasks.append((task, list(common)))

    pct = (len(matched_tasks) / len(combined_tasks) * 100.0) if combined_tasks else 0.0

    domain_boost = 0
    for dom_name, dom_info in SYNONYM_DOMAINS.items():
        if code_str in dom_info["occ_codes"]:
            dom_matches = [r for r in dom_info["roots"] if any(w.startswith(r) for w in cand_words)]
            domain_boost = len(dom_matches)

    return round(pct, 1), matched_tasks, domain_boost


def calculate_company_alignment(cand_company_nature: str, industries: list) -> tuple:
    """Check alignment between candidate's employer business sector and occupation industry."""
    if not cand_company_nature or not industries:
        return False, None, "Company sector neutral"

    cn_lower = cand_company_nature.lower()
    for ind in industries:
        ind_lower = ind.lower()
        if any(k in cn_lower for k in ["hospitality", "hotel", "food", "restaurant", "catering"]) and ("accommodation" in ind_lower or "food" in ind_lower):
            return True, ind, f"Employer sector '{cand_company_nature}' aligns with '{ind}'"
        elif any(k in cn_lower for k in ["information technology", "software", "it services"]) and ("professional" in ind_lower or "information" in ind_lower or "financial" in ind_lower):
            return True, ind, f"Employer sector '{cand_company_nature}' aligns with '{ind}'"
        elif any(k in cn_lower for k in ["healthcare", "pharma", "pharmaceutical", "clinical", "medical"]) and ("health" in ind_lower or "social" in ind_lower or "professional" in ind_lower):
            return True, ind, f"Employer sector '{cand_company_nature}' aligns with '{ind}'"
        elif re.search(r'\bhospital\b', cn_lower) and ("health" in ind_lower or "social" in ind_lower):
            return True, ind, f"Hospital sector aligns with '{ind}'"
        elif any(k in cn_lower for k in ["bank", "finance", "financial"]) and ("financial" in ind_lower or "insurance" in ind_lower):
            return True, ind, f"Banking & finance sector aligns with '{ind}'"
        elif any(k in cn_lower for k in ["legal", "law"]) and ("professional" in ind_lower or "public" in ind_lower):
            return True, ind, f"Legal practice aligns with '{ind}'"
        elif any(k in cn_lower for k in ["construct", "infrastructure", "engineering"]) and "construction" in ind_lower:
            return True, ind, f"Engineering & construction aligns with '{ind}'"

    return False, industries[0] if industries else None, f"Sector '{cand_company_nature}' outside primary industries"


def calculate_age_gsm_points(age: int) -> tuple:
    """Calculate GSM age points and description."""
    if 18 <= age <= 24:
        return 25, f"Age {age} secures 25 GSM points (18-24 age bracket)."
    if 25 <= age <= 32:
        return 30, f"Age {age} secures maximum 30 GSM points (25-32 age bracket)."
    if 33 <= age <= 39:
        return 25, f"Age {age} secures 25 GSM points (33-39 age bracket)."
    if 40 <= age <= 44:
        return 15, f"Age {age} secures 15 GSM points (40-44 age bracket)."
    return 0, f"Age {age} is outside the GSM skilled points threshold (45+)."


def _enrich_suggestion_skills(
    s: dict,
    occ_doc: dict,
    candidate_profile: dict,
    cand_duties_text: str = "",
    cand_company_nature: str = "",
    cand_employer: str = "",
    cand_age: int = 30,
    classification_cfg: Optional[Dict[str, Any]] = None,
) -> None:
    """Evaluate and attach skills assessment rules, deductions, duty alignment, and company fit."""
    eval_occ = {**occ_doc, **s}
    eval_res = evaluate_skills_assessment(eval_occ, candidate_profile)

    auth_code = eval_res.get("authority_code") or s.get("assessing_body") or "AUTHORITY"
    auth_name = eval_res.get("authority_name") or s.get("assessing_body") or auth_code
    deducted = float(eval_res.get("deducted_years") or 0.0)
    claimable_yrs = float(eval_res.get("points_claimable_years") or 0.0)
    claimable_pts = int(eval_res.get("points_claimable_points") or 0)
    outcome = eval_res.get("assessment_outcome") or "Likely Positive Assessment"
    is_pos = bool(eval_res.get("is_positive", True))
    rpl = bool(eval_res.get("rpl_required"))
    cdr = (auth_code == "EA" and is_pos)

    # Qualification Relevance Check
    cand_field = candidate_profile.get("field_of_study") or ""
    is_field_rel, field_reason = is_field_relevant_to_occupation(cand_field, occ_doc)

    # Duty Alignment
    occ_tasks = occ_doc.get("tasks") or occ_doc.get("typical_tasks") or []
    duty_pct, matched_tasks, _boost = calculate_duty_alignment(cand_duties_text, occ_tasks, str(s.get("code", "")))
    matched_task_texts = [m[0] for m in matched_tasks]

    # Company Alignment across all historical and current employers
    industries = occ_doc.get("industries_ranked") or []
    is_comp_matched, matched_ind, comp_summary = calculate_company_alignment(cand_company_nature, industries)
    best_comp_name = cand_employer
    best_comp_nature = cand_company_nature

    if not is_comp_matched:
        for w in (candidate_profile.get("primary_applicant", {}).get("work_history") or []):
            w_emp = (w.get("employer") or w.get("employer_name") or "").strip()
            w_nat = (w.get("company_nature") or w.get("nature_of_company") or "").strip()
            if w_nat:
                c_matched, c_ind, c_sum = calculate_company_alignment(w_nat, industries)
                if c_matched:
                    is_comp_matched = True
                    matched_ind = c_ind
                    comp_summary = c_sum
                    best_comp_name = w_emp or cand_employer
                    best_comp_nature = w_nat
                    break

    # Age Points
    age_pts, age_summary = calculate_age_gsm_points(cand_age)

    # Confidence rating
    if (is_pos and (duty_pct >= 20.0 or is_field_rel)) or (duty_pct >= 35.0):
        s["confidence"] = "high"
    elif is_pos or duty_pct >= 15.0:
        s["confidence"] = "medium"
    else:
        s["confidence"] = "low"

    s["assessing_body"] = auth_name
    s["duty_alignment"] = {
        "match_percentage": duty_pct,
        "matched_tasks_count": len(matched_tasks),
        "total_tasks_count": len(occ_tasks),
        "matched_tasks": matched_task_texts[:4],
        "summary": (
            f"{duty_pct:.1f}% core duty alignment with official ABS ANZSCO tasks ({len(matched_tasks)}/{len(occ_tasks)} tasks matched)."
            if occ_tasks else "Duty alignment evaluated against unit group standards."
        ),
    }

    s["company_alignment"] = {
        "employer_name": best_comp_name,
        "company_nature": best_comp_nature,
        "matched_industry": matched_ind,
        "is_matched": is_comp_matched,
        "summary": comp_summary,
    }

    s["age_evaluation"] = {
        "age": cand_age,
        "gsm_age_points": age_pts,
        "summary": age_summary,
    }

    conditions_summary = (
        f"Requires {deducted:.1f} yr(s) qualifying deduction. "
        + ("2 ACS RPL Project Reports mandatory. " if rpl else "")
        + ("Competency Demonstration Report (CDR with 3 Career Episodes) required for non-Washington Accord degrees. " if cdr else "")
        + f"Remaining {claimable_yrs:.1f} yrs can claim {claimable_pts} migration points for GSM."
        if is_pos else
        f"Assessment Outcome: {outcome}. {eval_res.get('justification', '')}"
    )

    deduction_summary = (
        (f"-{deducted:.1f} yrs deduction ({'RPL Non-ICT' if rpl else 'Qualifying Requirement'}) → {claimable_yrs:.1f} yrs claimable ({claimable_pts} pts)"
        if deducted > 0 else
        f"0.0 yrs deduction → {claimable_yrs:.1f} yrs claimable ({claimable_pts} pts)")
        if is_pos else
        f"Ineligible: {outcome}"
    )

    s["skills_assessment"] = {
        "authority_code": auth_code,
        "authority_name": auth_name,
        "pathway_name": eval_res.get("pathway_name") or f"{auth_code} Skills Assessment",
        "assessment_outcome": outcome,
        "is_positive": is_pos,
        "rpl_required": rpl,
        "cdr_required": cdr,
        "qualification_bucket": eval_res.get("qualification_bucket") or eval_res.get("vetassess_group"),
        "total_experience_years": eval_res.get("total_experience_years", 0.0),
        "deducted_years": deducted,
        "points_claimable_years": claimable_yrs,
        "points_claimable_points": claimable_pts,
        "points_description": eval_res.get("points_description", ""),
        "deemed_skilled_summary": eval_res.get("deemed_skilled_summary", ""),
        "justification": eval_res.get("justification", ""),
        "deduction_summary": deduction_summary,
        "conditions_summary": conditions_summary,
        "required_documents": eval_res.get("required_documents", []),
        "risk_warnings": eval_res.get("risk_warnings", []),
        "screening_checklist_notes": eval_res.get("screening_checklist_notes", ""),
    }

    # Identify which specific candidate role(s) this occupation aligns with
    cand_titles_to_check = []
    if candidate_profile.get("primary_applicant", {}).get("professional", {}).get("current_profession"):
        cand_titles_to_check.append(candidate_profile["primary_applicant"]["professional"]["current_profession"])
    for w in (candidate_profile.get("primary_applicant", {}).get("work_history") or []):
        t = (w.get("designation") or w.get("job_title") or w.get("title") or "").strip()
        if t and t not in cand_titles_to_check:
            cand_titles_to_check.append(t)

    matched_roles = [
        t for t in cand_titles_to_check
        if title_tokens_overlap(t, (occ_doc.get("title") or "").lower(), occ_doc.get("alternative_titles") or []) >= 0.35
        or (occ_doc.get("title") or "").lower() in t.lower()
        or t.lower() in (occ_doc.get("title") or "").lower()
    ]
    role_prefix = f"Matches candidate's career role as {', '.join(matched_roles[:2])}. " if matched_roles else ""

    # Synthesize rich reasoning
    if duty_pct >= 20.0:
        duty_phrase = f"Duties align strongly with official ABS ANZSCO unit group tasks ({duty_pct:.1f}% match across {len(matched_tasks)} core tasks)."
    elif is_field_rel:
        duty_phrase = f"Qualifications and professional profile match {occ_doc.get('group') or s.get('title')} ({field_reason})."
    else:
        duty_phrase = f"Matches occupational profile in {occ_doc.get('group') or s.get('title')}."

    comp_phrase = f" Employer '{best_comp_name}' ({best_comp_nature}) aligns with {matched_ind or 'industry standards'}." if is_comp_matched and best_comp_name else ""
    qual_phrase = f" Qualifications assessed by {auth_name} ({eval_res.get('qualification_bucket') or 'Relevant Qualification'})."
    
    s["reasoning"] = f"{role_prefix}{duty_phrase}{comp_phrase}{qual_phrase}"
    if not is_pos:
        s["considerations"] = f"Assessment Outcome: {outcome}. {eval_res.get('justification', '')}"
    else:
        s["considerations"] = (
            f"Skills assessment by {auth_name}: -{deducted:.1f} qualifying years deducted, leaving {claimable_yrs:.1f} claimable years (+{claimable_pts} GSM points)."
            + (" RPL pathway required for non-ICT degree." if rpl else "")
            + (" CDR with 3 career episodes required." if cdr else "")
        )

    # Attach dual-framework classification version & subclass details for Australia
    cc = (s.get("country_code") or occ_doc.get("country_code") or "AU").upper()
    if cc == "AU":
        cfg_to_use = classification_cfg or DEFAULT_AU_CLASSIFICATIONS
        cv = evaluate_occupation_classification_versions(eval_occ, cfg_to_use)
        s["classification_versions"] = cv

        anz_sc = cv.get("anzsco_2013", {}).get("active_subclasses") or []
        osca_sc = cv.get("osca_2022", {}).get("active_subclasses") or []

        active_subclasses = []
        for sc in anz_sc:
            if sc not in active_subclasses:
                active_subclasses.append(sc)
        for sc in osca_sc:
            if sc not in active_subclasses:
                active_subclasses.append(sc)
        s["eligible_visas"] = active_subclasses

        has_gsm = len(anz_sc) > 0
        has_emp = len(osca_sc) > 0
        framework_label = (
            "ANZSCO 2013 (GSM) & OSCA 2022 (Employer)" if (has_gsm and has_emp)
            else ("ANZSCO 2013 (GSM Points-Tested)" if has_gsm
            else ("OSCA 2022 (Employer / Core Skills)" if has_emp
            else "No Active Subclasses"))
        )

        s["subclass_summary"] = {
            "has_gsm_pathway": has_gsm,
            "has_employer_pathway": has_emp,
            "anzsco_2013_subclasses": anz_sc,
            "osca_2022_subclasses": osca_sc,
            "all_active_subclasses": active_subclasses,
            "framework_label": framework_label,
            "subclasses_count": len(active_subclasses),
        }

        v_parts = []
        if anz_sc:
            v_parts.append(f"ANZSCO 2013 GSM: Subclasses {', '.join(anz_sc)}")
        if osca_sc:
            v_parts.append(f"OSCA 2022 Employer/Core Skills: Subclasses {', '.join(osca_sc)}")
        if v_parts:
            s["considerations"] = (s.get("considerations") or "") + f" [Pathways: {' | '.join(v_parts)}]"

        subclass_phrase = f" Eligible for Subclasses {', '.join(active_subclasses)} ({framework_label})." if active_subclasses else " No active subclasses configured."
        s["reasoning"] = f"{s['reasoning']}{subclass_phrase}"


@router.post("/suggest-occupation")
async def suggest_occupation(
    req: SuggestRequest,
    current_user: dict = Depends(get_current_user)
):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    api_key = (os.getenv("PERPLEXITY_API_KEY") or os.getenv("OPENAI_API_KEY") or PERPLEXITY_API_KEY or "").strip()
    classification_cfg = await get_active_classification_versions()

    # 1. Extract candidate profile and full work history details
    prof_dict = req.profile or {}
    pri_app = prof_dict.get("primary_applicant") or {}
    personal = pri_app.get("personal") or {}
    professional = pri_app.get("professional") or {}
    education = pri_app.get("education") or {}
    work_hist = pri_app.get("work_history") or prof_dict.get("work_history") or []

    # If work history is not pre-structured, parse multiple position blocks from the description text
    if not work_hist and req.description:
        try:
            from core.resume_extractor import parse_work_experience_blocks
            extracted_blocks = parse_work_experience_blocks(req.description)
            if extracted_blocks:
                work_hist = extracted_blocks
        except Exception as e:
            logger.warning("Failed to parse work experience blocks from description: %s", e)

    cand_prof = (
        professional.get("current_profession")
        or pri_app.get("current_profession")
        or professional.get("designation")
        or prof_dict.get("current_profession")
        or prof_dict.get("profession")
        or prof_dict.get("designation")
        or ""
    ).strip()

    if not cand_prof and work_hist:
        cand_prof = (work_hist[0].get("designation") or work_hist[0].get("title") or "").strip()
    if not cand_prof and req.description:
        cand_prof = extract_profession_from_text(req.description)

    cand_employer = (
        professional.get("employer_name")
        or (work_hist[0].get("employer") if work_hist else "")
        or ""
    ).strip()

    cand_company_nature = (
        professional.get("employer_nature")
        or (work_hist[0].get("company_nature") if work_hist else "")
        or professional.get("industry")
        or ""
    ).strip()

    if not cand_company_nature and cand_employer:
        from core.resume_extractor import infer_company_nature
        cand_company_nature = infer_company_nature(cand_employer, req.description or "")

    cand_qual = (
        req.qualification
        or education.get("highest_qualification")
        or pri_app.get("highest_qualification")
        or prof_dict.get("qualification")
        or "bachelor"
    )

    cand_field = (
        req.field_of_study
        or education.get("field_of_study")
        or pri_app.get("field_of_study")
        or prof_dict.get("field_of_study")
        or ""
    )

    cand_exp = (
        req.years_experience_total
        if req.years_experience_total is not None
        else professional.get("years_experience_total")
        or pri_app.get("years_experience_total")
        or prof_dict.get("years_experience_total")
    )
    if cand_exp is None or cand_exp == 0.0:
        extracted_exp = extract_experience_years_from_text(req.description or "")
        if extracted_exp is not None:
            cand_exp = extracted_exp
        else:
            cand_exp = 0.0

    # Ensure total experience reflects candidate's entire career across all past & present positions
    wh_years_sum = sum(float(w.get("years") or 0.0) for w in work_hist)
    if wh_years_sum > cand_exp:
        cand_exp = wh_years_sum

    cand_age = int(personal.get("age") or pri_app.get("age") or prof_dict.get("age") or 30)

    # Collect comprehensive duty text from all work history and description
    duties_parts = []
    if req.description:
        duties_parts.append(req.description)
    if prof_dict.get("roles_and_responsibilities"):
        duties_parts.append(str(prof_dict["roles_and_responsibilities"]))
    for b in (prof_dict.get("duty_bullets") or []):
        duties_parts.append(str(b))
    for w in work_hist:
        desig = w.get("designation") or w.get("job_title") or w.get("title") or ""
        emp = w.get("employer") or w.get("employer_name") or ""
        nat = w.get("company_nature") or w.get("nature_of_company") or ""
        if desig:
            duties_parts.append(f"Position: {desig} at {emp} ({nat})")
        if w.get("duties"):
            duties_parts.append(str(w["duties"]))
        if w.get("duty_bullets"):
            duties_parts.extend([str(b) for b in w["duty_bullets"]])
        if w.get("responsibilities"):
            duties_parts.append(str(w["responsibilities"]))
        if w.get("tasks"):
            duties_parts.append(str(w["tasks"]))
        if w.get("description"):
            duties_parts.append(str(w["description"]))
        if w.get("technologies"):
            duties_parts.append(str(w["technologies"]))
    if cand_prof:
        duties_parts.append(cand_prof)
    if cand_field:
        duties_parts.append(cand_field)

    cand_duties_text = " ".join(duties_parts).strip()

    candidate_profile = {
        "qualification": cand_qual,
        "field_of_study": cand_field,
        "years_experience_total": cand_exp,
        "primary_applicant": {
            "personal": {"age": cand_age, "full_name": personal.get("full_name") or pri_app.get("name") or ""},
            "education": {
                "highest_qualification": cand_qual,
                "field_of_study": cand_field,
            },
            "professional": {
                "current_profession": cand_prof,
                "employer_name": cand_employer,
                "employer_nature": cand_company_nature,
                "years_experience_total": cand_exp,
            },
            "work_history": work_hist,
        },
    }

    # 2. Build the available occupation list from database
    query: Dict[str, Any] = {"status": {"$ne": "superseded"}}
    if req.country_codes:
        query["country_code"] = {
            "$in": [c.upper() for c in req.country_codes]
        }

    available_codes: List[Dict[str, Any]] = []
    occ_doc_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

    async for occ in db["occupation_master"].find(query, {"_id": 0}):
        aa = occ.get("assessing_authority") or {}
        hierarchy = occ.get("hierarchy") or {}
        pathway_lists = (
            occ.get("visa_pathways") or {}
        ).get("pathway_lists") or []
        cc = (occ.get("country_code") or "AU").upper()
        code_str = str(occ.get("code", "")).strip()

        # Strictly require 6 digits for Australia (never 4-digit unit groups)
        if cc == "AU" and (len(code_str) != 6 or not code_str.isdigit()):
            continue

        item = {
            "country_code": cc,
            "code": code_str,
            "title": occ.get("title"),
            "group": hierarchy.get("unit_group_name"),
            "assessing_body": aa.get("name"),
            "pathway": pathway_lists[0] if pathway_lists else None,
            "alternative_titles": occ.get("alternative_titles") or [],
            "vetassess_group": occ.get("vetassess_group"),
            "is_trade_occupation": occ.get("is_trade_occupation"),
            "vetassess_approved_rto": occ.get("vetassess_approved_rto"),
            "is_licensed_trade": occ.get("is_licensed_trade"),
            "acs_category": occ.get("acs_category"),
            "tasks": occ.get("tasks") or [],
            "typical_tasks": occ.get("typical_tasks") or [],
            "industries_ranked": occ.get("industries_ranked") or [],
        }
        available_codes.append(item)
        occ_doc_map[(cc, code_str)] = occ

    if not available_codes:
        raise HTTPException(
            status_code=400,
            detail="No occupation codes loaded in the knowledge base",
        )

    cand_words = {_stem(w) for w in re.findall(r'\b[a-zA-Z]{3,}\b', (cand_duties_text + " " + cand_prof + " " + cand_company_nature).lower()) if w not in STOP_WORDS}
    prof_lower = cand_prof.lower()
    field_lower = cand_field.lower()
    comp_nature_lower = cand_company_nature.lower()

    # Collect all historical and current job titles across the candidate's career
    cand_work_titles = []
    if prof_lower:
        cand_work_titles.append(prof_lower)
    for w in work_hist:
        desig = (w.get("designation") or w.get("title") or w.get("job_title") or "").strip().lower()
        if desig and desig not in cand_work_titles:
            cand_work_titles.append(desig)

    # Extract all job titles and designations found across the entire description / resume text
    all_extracted_professions = extract_all_professions_from_text(req.description or "")
    for ep in all_extracted_professions:
        ep_lower = ep.lower().strip()
        if ep_lower and ep_lower not in cand_work_titles:
            cand_work_titles.append(ep_lower)

    # Detect active major groups based on full career chronology, work titles, and duties
    desc_for_detection = (cand_duties_text + " " + " ".join(cand_work_titles) + " " + cand_company_nature).lower()
    active_unit_prefixes = set()
    has_strong_group = False
    for grp_key, grp_data in ANZSCO_MAJOR_GROUP_KEYWORDS.items():
        matches = sum(
            1 for kw in grp_data["keywords"]
            if kw in desc_for_detection or any(w.startswith(kw[:4]) for w in cand_words)
        )
        if matches >= 2:
            active_unit_prefixes.update(grp_data["unit_prefixes"])
            if matches >= 3:
                has_strong_group = True

    # Extract target subclasses and target framework if requested or mentioned in candidate description
    active_target_subclasses = list(req.target_subclasses or [])
    if not active_target_subclasses and req.description:
        active_target_subclasses = extract_subclasses_from_text(req.description)

    target_framework = (req.target_framework or "").strip().upper()
    if not target_framework and req.description:
        desc_l = req.description.lower()
        if "osca" in desc_l or "employer" in desc_l or "csol" in desc_l or "tss" in desc_l:
            target_framework = "OSCA_2022"
        elif "anzsco" in desc_l or "gsm" in desc_l or "points-tested" in desc_l:
            target_framework = "ANZSCO_2013"

    # Pre-evaluate dual classification versions and active subclasses for all AU occupations
    occ_cv_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    cfg_to_use = classification_cfg or DEFAULT_AU_CLASSIFICATIONS
    for item in available_codes:
        cc_val = item["country_code"]
        c_code_val = item["code"]
        if cc_val == "AU":
            full_doc_val = occ_doc_map.get((cc_val, c_code_val)) or item
            cv_val = evaluate_occupation_classification_versions(full_doc_val, cfg_to_use)
            occ_cv_map[(cc_val, c_code_val)] = cv_val

    # 3. Multi-factor intelligent scoring function based primarily on work experience and subclass eligibility
    def _score_occ(a: dict) -> int:
        code = str(a.get("code") or "")
        code_prefix = code[:4]
        title_lower = (a.get("title") or "").lower()
        group_lower = (a.get("group") or "").lower()
        alts = [str(x).lower() for x in (a.get("alternative_titles") or [])]
        industries = a.get("industries_ranked") or []
        cc = (a.get("country_code") or "AU").upper()

        score = 50
        if cc == "AU":
            score += 30

        # --- FACTOR 1: TITLE & WORK EXPERIENCE TOKEN OVERLAP ACROSS ALL CAREER ROLES ---
        t_overlap = max(
            (title_tokens_overlap(t, title_lower, alts) for t in cand_work_titles),
            default=0.0
        )
        has_direct_work_title = (
            t_overlap >= 0.4
            or any(title_lower == t or title_lower in t or t in title_lower or any(alt and (alt == t or alt in t or t in alt) for alt in alts) for t in cand_work_titles)
        )

        # Tenure bonus for specific role match in candidate work history
        role_tenure_bonus = 0
        for w in work_hist:
            w_title = (w.get("designation") or w.get("title") or w.get("job_title") or "").strip().lower()
            if not w_title:
                continue
            w_alts = alts
            w_over = title_tokens_overlap(w_title, title_lower, w_alts)
            if w_over >= 0.4 or title_lower in w_title or w_title in title_lower or any(alt and (alt in w_title or w_title in alt) for alt in w_alts):
                yrs = float(w.get("years") or 0.0)
                bonus = min(int(yrs * 50), 200)
                if bonus > role_tenure_bonus:
                    role_tenure_bonus = bonus

        if has_direct_work_title:
            score += 650 + role_tenure_bonus
        elif t_overlap > 0:
            score += int(t_overlap * 400)
        elif group_lower and any(group_lower in t or t in group_lower for t in cand_work_titles):
            score += 150

        # --- MAJOR OCCUPATIONAL GROUP ALIGNMENT ---
        if code_prefix in active_unit_prefixes:
            score += 1200
        elif has_strong_group and not any(code_prefix.startswith(p[:2]) for p in active_unit_prefixes) and not has_direct_work_title:
            # Harsh penalty for cross-domain bleed (e.g. sports or management consulting for software developers)
            score -= 2000

        unit_tasks = ANZSCO_UNIT_GROUP_DUTIES.get(code_prefix, [])
        all_tasks = list(a.get("tasks") or a.get("typical_tasks") or [])
        for ut in unit_tasks:
            if ut not in all_tasks:
                all_tasks.append(ut)

        # --- FACTOR 2: DUTY & RESPONSIBILITIES MATCH AGAINST OFFICIAL ABS ANZSCO TASKS ---
        matched_tasks = []
        generic_verbs = {"manag", "admin", "operat", "organis", "plan", "servic", "direct", "coordinat"}
        for task in all_tasks:
            task_words = {_stem(w) for w in re.findall(r'\b[a-zA-Z]{3,}\b', task.lower()) if w not in STOP_WORDS}
            common = cand_words.intersection(task_words)
            meaningful_common = [c for c in common if c not in generic_verbs]
            if len(common) >= 2 and len(meaningful_common) >= 1:
                matched_tasks.append(task)
            elif len(common) >= 1 and any(c in [
                "program", "code", "design", "test", "architect", "cook", "menu", "court",
                "law", "develop", "api", "haccp", "audit", "tax", "nurse", "welder", "mechanic",
                "teach", "culinari", "pastri", "conveyanc", "plead", "litigat", "microservic",
                "docker", "kubernetes", "database", "postgres", "sql", "cloud", "aws", "azure"
            ] for c in common):
                matched_tasks.append(task)

        duty_pct = (len(matched_tasks) / len(all_tasks) * 100.0) if all_tasks else 0.0
        if duty_pct >= 35.0:
            score += 600
        elif duty_pct >= 20.0:
            score += 400
        elif duty_pct >= 10.0:
            score += 200
        score += len(matched_tasks) * 60

        # Domain roots boost
        for dom_name, dom_info in SYNONYM_DOMAINS.items():
            if code in dom_info["occ_codes"]:
                dom_matches = [r for r in dom_info["roots"] if any(w.startswith(r) for w in cand_words)]
                if dom_matches:
                    score += len(dom_matches) * 50

        # Specific software engineer / developer boost
        cand_p_lower = prof_lower + " " + " ".join(cand_work_titles)
        if any(k in cand_p_lower for k in ["developer", "programmer", "software engineer"]):
            if "developer" in title_lower or "programmer" in title_lower:
                score += 400
            if "software" in title_lower:
                score += 400
            if any(k in cand_duties_text.lower() for k in ["backend", "api", "microservice", "django", "python", "database"]):
                if code in ["261312", "261313", "261399"]:
                    score += 500

        # Exact code match in description
        if code and code in cand_duties_text.lower():
            score += 400

        # --- SPECIFIC ROLE PRECEDENCE BASED ON WORK EXPERIENCE ---
        # 1. Finance Leadership & FP&A vs Statutory Bookkeeping Accountants
        has_fin_mgr = any(any(k in t for k in ["finance manager", "financial manager", "director of finance", "head of finance", "vp finance", "cfo", "treasurer", "financial controller", "financial planning", "fp&a", "pricing strategy", "finance partner"]) for t in cand_work_titles) or "finance manager" in cand_p_lower
        has_fin_analyst = any(any(k in t for k in ["financial analyst", "investment analyst", "portfolio manager", "due diligence", "investment manager", "finance partner", "equity research", "financial modeling"]) for t in cand_work_titles)
        non_acc_sales_titles = {"account manager", "key account manager", "national account manager", "account executive", "technical account manager", "client account manager"}
        is_sales_acc_title = any(any(sat in t for sat in non_acc_sales_titles) for t in cand_work_titles)
        has_explicit_accountant = any(any(k in t for k in ["accountant", "bookkeeper", "tax accountant", "accounts officer", "accounts payable", "accounts receivable"]) for t in cand_work_titles) and not is_sales_acc_title

        if has_fin_mgr:
            if code == "132211":  # Finance Manager
                score += 900
            if code in ["222312", "222311"]:  # Financial Investment Manager / Adviser
                score += 650
            if code == "221111" and not has_explicit_accountant:
                score -= 2200
        elif has_fin_analyst:
            if code in ["222312", "222311"]:  # Financial Investment Manager / Adviser
                score += 850
            if code == "132211":
                score += 600
            if code == "221111" and not has_explicit_accountant:
                score -= 1600

        if has_explicit_accountant:
            if code in ["221111", "221112", "221113"]:
                score += 650

        # 2. Human Resources & Talent Acquisition
        has_hr_kw = any(
            any(k in t for k in ["human resource", "hr ", "talent acquisition", "recruitment", "recruiter", "people and culture", "workplace relations", "personnel", "onboarding", "employee relations", "staffing", "payroll coordination"])
            for t in cand_work_titles
        ) or any(k in field_lower for k in ["human resource", "hr", "personnel", "talent management", "industrial relations", "workplace relations"])
        if has_hr_kw:
            if code in ["223111", "223112", "223113"]:
                score += 850
            if code == "132311" and any(any(m in t for m in ["manager", "lead", "director", "head of"]) for t in cand_work_titles):
                score += 900

        # 3. Corporate B2B Sales, Technical Sales & Key Account Management
        has_sales_b2b_kw = any(
            any(k in t for k in ["sales", "account manager", "key account", "business development", "b2b", "sales representative", "client relationship manager", "territory manager", "sales executive", "sales engineer"])
            for t in cand_work_titles
        )
        if has_sales_b2b_kw:
            if code in ["225411", "225412", "225211", "225212"]:
                score += 800
            if code == "131112" and any(any(m in t for m in ["manager", "lead", "director", "head of"]) for t in cand_work_titles):
                score += 850

        # 4. Construction Project Management & Building
        has_construction_kw = any(
            any(k in t for k in ["construction manager", "construction project manager", "project builder", "site manager", "site supervisor", "builder", "construction site", "building contractor", "clerk of works"])
            for t in cand_work_titles
        ) or (any(k in cand_work_titles for k in ["project manager", "site engineer"]) and any(k in comp_nature_lower for k in ["construction", "building", "infrastructure"]))
        if has_construction_kw:
            if code in ["133111", "133112"]:
                score += 900

        # 5. Supply Chain & Logistics Management
        has_supply_chain_kw = any(
            any(k in t for k in ["supply chain", "logistics", "procurement", "inventory manager", "warehouse manager", "distribution manager", "freight manager", "import export"])
            for t in cand_work_titles
        )
        if has_supply_chain_kw:
            if code in ["133611", "133612"]:
                score += 900

        # 6. Graphic, Web & UI/UX Design
        has_designer_kw = any(
            any(k in t for k in ["graphic designer", "web designer", "ui/ux", "ui designer", "ux designer", "illustrator", "visual designer", "multimedia designer", "product designer"])
            for t in cand_work_titles
        ) or any(k in field_lower for k in ["graphic design", "visual communication", "multimedia", "digital design", "ui/ux"])
        if has_designer_kw:
            if code in ["232411", "232414", "261211", "261212", "232413"]:
                score += 850

        # 7. Social Work & Community Welfare
        has_social_work_kw = any(
            any(k in t for k in ["social worker", "caseworker", "community worker", "welfare worker", "youth worker", "crisis counsellor", "child protection"])
            for t in cand_work_titles
        ) or any(k in field_lower for k in ["social work", "welfare", "community development", "counselling"])
        if has_social_work_kw:
            if code in ["272511", "272613", "411711", "411716", "411713"]:
                score += 850

        # 8. Allied Health & Medical Radiation
        has_physio_kw = any(any(k in t for k in ["physiotherapist", "physical therapist", "physio"]) for t in cand_work_titles) or "physiotherapy" in field_lower
        if has_physio_kw and code == "252511":
            score += 950

        has_radiog_kw = any(any(k in t for k in ["radiographer", "medical radiation", "x-ray technician", "sonographer", "ultrasound technician"]) for t in cand_work_titles) or any(k in field_lower for k in ["radiography", "medical radiation", "sonography"])
        if has_radiog_kw and code in ["251211", "251212", "251214"]:
            score += 950

        has_ot_kw = any(any(k in t for k in ["occupational therapist", "occupational therapy"]) for t in cand_work_titles) or "occupational therapy" in field_lower
        if has_ot_kw and code == "252411":
            score += 950

        # 9. Life Sciences & Pathology Laboratory
        has_biotech_kw = any(any(k in t for k in ["biotechnologist", "microbiologist", "biochemist", "life scientist", "clinical trial", "genomic", "molecular biologist"]) for t in cand_work_titles) or any(k in field_lower for k in ["biotechnology", "microbiology", "biochemistry", "molecular biology", "genetics"])
        if has_biotech_kw and code in ["234514", "234517", "234513", "234511", "234599"]:
            score += 900

        has_med_lab_kw = any(any(k in t for k in ["medical laboratory scientist", "medical lab scientist", "pathology scientist", "clinical laboratory"]) for t in cand_work_titles) or any(k in field_lower for k in ["medical laboratory science", "pathology", "clinical laboratory"])
        if has_med_lab_kw and code == "234611":
            score += 950

        # --- FACTOR 3: QUALIFICATION VS WORK EXPERIENCE PRECEDENCE ---
        eval_doc = occ_doc_map.get((cc, code)) or a
        is_field_rel, field_reason = is_field_relevant_to_occupation(cand_field, eval_doc)
        has_exp_match = (
            has_direct_work_title
            or duty_pct >= 15.0
            or len(matched_tasks) >= 2
            or (code_prefix in active_unit_prefixes)
        )

        if is_field_rel:
            score += 200
        else:
            if has_exp_match:
                # Actual work experience in the occupation takes precedence over non-related college degree
                score += 350
            else:
                # Cross-discipline mismatch without relevant work experience
                if (
                    code.startswith("233") or code.startswith("312") or code.startswith("2633")
                    or code.startswith("25") or code.startswith("411")
                    or code.startswith("241")
                    or (code.startswith("3") and not code.startswith("313"))
                    or code.startswith("2211") or code.startswith("2212")
                    or code.startswith("271")
                    or code.startswith("1")
                ):
                    score -= 2500

        # --- FACTOR 4: ASSESSING AUTHORITY BODY EVALUATION (NON-DESTRUCTIVE) ---
        try:
            sa = evaluate_skills_assessment(eval_doc, candidate_profile)
        except Exception as sa_err:
            logger.warning("Skills assessment evaluation failed for %s: %s", code, sa_err)
            sa = {"is_positive": False, "deducted_years": 0.0, "points_claimable_years": 0.0}

        if sa.get("is_positive"):
            score += 200
            deducted = float(sa.get("deducted_years") or 0.0)
            claimable_yrs = float(sa.get("points_claimable_years") or 0.0)
            if deducted <= 1.0:
                score += 100
            elif deducted <= 2.0:
                score += 60
            elif deducted <= 3.0:
                score += 30
            if claimable_yrs >= 4.0:
                score += 80
            elif claimable_yrs >= 2.0:
                score += 40
        else:
            # Minor adjustment for experience shortfall so genuine occupation is NOT purged
            score -= 80

        # --- FACTOR 5: COMPANY NATURE & INDUSTRY MATCH ---
        for ind in industries:
            ind_lower = ind.lower()
            if any(k in comp_nature_lower for k in ["hospitality", "hotel", "food", "restaurant", "catering"]) and ("accommodation" in ind_lower or "food" in ind_lower):
                score += 140
                break
            elif any(k in comp_nature_lower for k in ["information technology", "software", "it services"]) and ("professional" in ind_lower or "information" in ind_lower or "financial" in ind_lower):
                score += 140
                break
            elif any(k in comp_nature_lower for k in ["healthcare", "pharma", "pharmaceutical", "clinical", "medical"]) and ("health" in ind_lower or "social" in ind_lower or "professional" in ind_lower):
                score += 140
                break
            elif re.search(r'\bhospital\b', comp_nature_lower) and ("health" in ind_lower or "social" in ind_lower):
                score += 140
                break
            elif any(k in comp_nature_lower for k in ["bank", "finance", "financial"]) and ("financial" in ind_lower or "insurance" in ind_lower):
                score += 140
                break
            elif any(k in comp_nature_lower for k in ["legal", "law"]) and ("professional" in ind_lower or "public" in ind_lower):
                score += 140
                break
            elif any(k in comp_nature_lower for k in ["construct", "infrastructure", "engineering"]) and "construction" in ind_lower:
                score += 140
                break
            elif any(k in comp_nature_lower for k in ["corporate", "commercial", "business", "consulting"]) and ("professional" in ind_lower or "administrative" in ind_lower):
                score += 140
                break

        # --- FACTOR 6: STRICT CROSS-DOMAIN NEGATIVE GUARDS ---
        has_mgr_kw = any(any(k in t for k in ["manager", "director", "head of", "chief", "lead", "general manager", "executive"]) for t in cand_work_titles) or "business" in field_lower or "management" in field_lower or "mba" in field_lower
        if not has_mgr_kw and (code.startswith("111") or code.startswith("131") or code.startswith("132") or code.startswith("133") or code == "141999"):
            score -= 3000

        # Specialized facility managers require specific domain experience
        has_childcare_kw = any(any(k in t for k in ["childcare", "child care", "early childhood", "preschool", "daycare", "kindergarten"]) for t in cand_work_titles) or any(k in field_lower for k in ["childhood", "early learning"])
        if not has_childcare_kw and code.startswith("1341"):
            score -= 3000

        has_health_admin_kw = any(any(k in t for k in ["health service", "hospital", "clinical service", "aged care manager", "health manager"]) for t in cand_work_titles) or any(k in comp_nature_lower for k in ["hospital", "health", "aged care"])
        if not has_health_admin_kw and code.startswith("1342"):
            score -= 3000

        has_hotel_kw = any(any(k in t for k in ["hotel", "motel", "resort", "accommodation", "lodging"]) for t in cand_work_titles) or any(k in comp_nature_lower for k in ["hotel", "motel", "resort", "accommodation"])
        if not has_hotel_kw and (code.startswith("1413") or code == "141999"):
            score -= 3000

        has_restaurant_kw = any(any(k in t for k in ["restaurant", "cafe", "bistro", "catering", "food service"]) for t in cand_work_titles) or any(k in comp_nature_lower for k in ["restaurant", "cafe", "hospitality"])
        if not has_restaurant_kw and (code.startswith("1411") or code.startswith("1412")):
            score -= 3000

        # Actuary, Mathematician, Statistician (2241)
        has_actuarial_kw = any(
            any(k in t for k in ["actuary", "actuarial", "mathematician", "statistician", "biostatistician", "quantitative analyst", "risk modeling"])
            for t in cand_work_titles
        ) or any(k in field_lower for k in ["actuarial", "statistics", "mathematics", "quantitative"])
        if not has_actuarial_kw and code.startswith("2241"):
            score -= 3000

        # Policy & Intelligence Analysts (2244)
        has_policy_intel_kw = any(
            any(k in t for k in ["policy analyst", "intelligence officer", "intelligence analyst", "policy officer", "strategic policy", "asio", "defence intelligence", "policy adviser"])
            for t in cand_work_titles
        ) or any(k in field_lower for k in ["public policy", "international relations", "criminology", "intelligence"])
        if not has_policy_intel_kw and code.startswith("2244"):
            score -= 3000

        # Economist (2243)
        has_econ_kw = any(
            any(k in t for k in ["economist", "economic analyst", "econometrician", "macroeconomic", "microeconomic"])
            for t in cand_work_titles
        ) or "economics" in field_lower or "econometrics" in field_lower
        if not has_econ_kw and code.startswith("2243"):
            score -= 3000

        has_eng_kw = any(any(k in t for k in ["engineer", "mechanical", "civil", "electrical", "chemical", "mechatronic"]) for t in cand_work_titles) or any(k in field_lower for k in ["engineer", "mechanical", "civil", "electrical", "chemical", "mechatronic"])
        if not has_eng_kw and (code.startswith("233") or code.startswith("312") or code.startswith("2633")):
            score -= 3000

        has_health_kw = any(any(k in t for k in ["nurse", "nursing", "midwife", "doctor", "physician", "medical", "mbbs", "dentist", "pharmacy", "physiotherapist", "radiographer", "occupational therapist"]) for t in cand_work_titles) or any(k in field_lower or k in comp_nature_lower for k in ["nurse", "nursing", "midwife", "doctor", "physician", "medical", "mbbs", "dentist", "pharmacy", "physiotherapy", "radiography"])
        if not has_health_kw and (code.startswith("25") or code.startswith("411")):
            score -= 3000

        has_teach_kw = any(any(k in t for k in ["teacher", "teaching", "b.ed", "m.ed", "school teacher", "lecturer"]) for t in cand_work_titles) or any(k in field_lower for k in ["teacher", "teaching", "b.ed", "m.ed", "school teacher", "lecturer"])
        if not has_teach_kw and code.startswith("241"):
            score -= 3000

        trade_roots = ["carpenter", "plumber", "electrician", "chef", "cook", "baker", "pastry", "mechanic", "welder", "fitter", "machinist", "mason", "joiner", "glazier", "plaster", "tiler", "hairdress", "butcher", "culinary", "hospitality", "hotel", "commis", "garde manger"]
        has_trade_kw = any(any(k in t for k in trade_roots) for t in cand_work_titles) or any(k in field_lower or k in comp_nature_lower for k in trade_roots) or any(k in cand_duties_text.lower() for k in ["chef", "cook", "culinary", "commis", "garde manger", "kitchen", "haccp", "welder", "carpenter", "mechanic"])
        if not has_trade_kw and (code.startswith("3") and not code.startswith("313")):
            score -= 3000

        # Strict Accounting Guard (2211, 2212)
        has_acc_kw = (
            any(re.search(r'\b(accountant|accounting|auditor|audit|taxation|tax|bookkeeper|cpa|chartered accountant)\b', t, re.I) for t in cand_work_titles)
            or any(re.search(r'\b(accounting|taxation|audit|chartered accountancy)\b', f, re.I) for f in [field_lower])
        ) and not (is_sales_acc_title and not any("accountant" in t or "auditor" in t for t in cand_work_titles))
        if not has_acc_kw and (code.startswith("2211") or code.startswith("2212")):
            score -= 3000

        # Strict Management Consulting Guard (2247)
        has_consulting_kw = any(
            any(k in t for k in [
                "management consultant", "strategy consultant", "business consultant", "management consulting",
                "advisory consultant", "business transformation", "operating model", "transformation consultant",
                "organisation analyst", "process consultant", "mckinsey", "bcg", "bain"
            ]) for t in cand_work_titles
        ) or (
            any(k in comp_nature_lower for k in ["management consulting", "strategy consulting", "business advisory"])
            and comp_nature_lower != "professional & commercial services"
        )
        if not has_consulting_kw and code.startswith("2247"):
            score -= 3000

        # Strict guard for pure Accountant (221111): only suggest if candidate actually worked in accounting roles
        if code == "221111" and not has_explicit_accountant and not (duty_pct >= 25.0 and is_field_rel):
            score -= 2500

        has_law_kw = any(any(k in t for k in ["law", "legal", "solicitor", "barrister", "advocate"]) for t in cand_work_titles) or any(k in field_lower for k in ["law", "legal", "solicitor", "barrister", "advocate"])
        if not has_law_kw and code.startswith("271"):
            score -= 3000

        has_art_kw = any(any(k in t for k in ["actor", "dancer", "entertainer", "singer", "artist"]) for t in cand_work_titles)
        if not has_art_kw and code.startswith("211"):
            score -= 3000

        # Prune complete mismatches (zero duty match AND unrelated field AND no work title match)
        if duty_pct == 0.0 and not is_field_rel and not has_direct_work_title and not has_exp_match:
            score -= 3000

        # --- FACTOR 7: DUAL CLASSIFICATION (ANZSCO 2013 vs OSCA 2022) & SUBCLASS ELIGIBILITY ---
        if cc == "AU":
            cv = occ_cv_map.get((cc, code)) or {}
            anz_subclasses = cv.get("anzsco_2013", {}).get("active_subclasses") or []
            osca_subclasses = cv.get("osca_2022", {}).get("active_subclasses") or []
            all_active_for_occ = set(anz_subclasses + osca_subclasses)

            # Heavy penalty if occupation has NO active eligible subclasses under configured frameworks
            if not all_active_for_occ:
                score -= 2500
            else:
                score += 150  # Base eligibility boost for having active Australian visa subclasses

                # ANZSCO 2013 Points-Tested GSM Subclass Boost
                if anz_subclasses:
                    score += 200
                    if "189" in anz_subclasses:
                        score += 120  # Independent Permanent Residence
                    if "190" in anz_subclasses:
                        score += 90   # State Nominated Permanent Residence
                    if "491" in anz_subclasses:
                        score += 70   # Regional Provisional

                # OSCA 2022 Core Skills & Employer Sponsored Subclass Boost
                if osca_subclasses:
                    score += 160
                    if "186" in osca_subclasses:
                        score += 110  # Employer Nomination Scheme Permanent Residence
                    if "482" in osca_subclasses:
                        score += 90   # Skills in Demand / TSS 4-year work visa

                # Specific target subclasses requested or extracted from description
                if active_target_subclasses:
                    matched_targets = set(active_target_subclasses).intersection(all_active_for_occ)
                    if matched_targets:
                        score += 500 + len(matched_targets) * 60
                    else:
                        score -= 400

                # Specific target framework requested or extracted from description
                if target_framework == "ANZSCO_2013":
                    if anz_subclasses:
                        score += 350
                    else:
                        score -= 350
                elif target_framework == "OSCA_2022":
                    if osca_subclasses:
                        score += 350
                    else:
                        score -= 350

        return score

    # Sort available codes by multi-factor score
    scored_codes = sorted(available_codes, key=_score_occ, reverse=True)
    # Prune non-viable negative-scoring codes
    viable_codes = [a for a in scored_codes if _score_occ(a) > 0]
    top_codes = viable_codes[:35] if viable_codes else scored_codes[:req.max_suggestions]

    # 4. If no external API key, return rich semantic AI suggestions directly
    if not api_key:
        top = top_codes[:req.max_suggestions]
        suggestions = []
        for occ in top:
            score = _score_occ(occ)
            conf = "high" if score >= 400 else ("medium" if score >= 200 else "low")
            title = occ.get("title", "")
            group = occ.get("group") or title
            body = occ.get("assessing_body") or "Designated Assessing Authority"
            path = occ.get("pathway") or "Core Skills / GSM"
            cc = occ.get("country_code", "AU")
            code_str = str(occ.get("code", ""))
            occ_full = occ_doc_map.get((cc.upper(), code_str)) or occ

            s_item = {
                "country_code": cc,
                "code": code_str,
                "title": title,
                "confidence": conf,
                "assessing_body": body,
                "pathway": path,
                "_verified": True,
            }
            _enrich_suggestion_skills(
                s_item,
                occ_full,
                candidate_profile,
                cand_duties_text=cand_duties_text,
                cand_company_nature=cand_company_nature,
                cand_employer=cand_employer,
                cand_age=cand_age,
                classification_cfg=classification_cfg,
            )
            suggestions.append(s_item)

        return {
            "suggestions": suggestions,
            "general_advice": "Prioritise codes where duties directly align with ABS tasks and assessing authority qualifying deductions maximize claimable GSM points.",
            "_ai_status": "ok",
            "_ai_model": "deep-duty-ai-matcher",
        }

    # 5. External LLM (Perplexity / Claude) path with rich context
    available_slim = []
    for a in top_codes:
        cc_upper = a["country_code"].upper()
        c_str = str(a["code"])
        eval_doc = occ_doc_map.get((cc_upper, c_str)) or a
        try:
            sa = evaluate_skills_assessment(eval_doc, candidate_profile)
        except Exception:
            sa = {}

        cv = occ_cv_map.get((cc_upper, c_str)) or {}
        anz_sc = cv.get("anzsco_2013", {}).get("active_subclasses") or []
        osca_sc = cv.get("osca_2022", {}).get("active_subclasses") or []
        all_active_sc = list(dict.fromkeys(anz_sc + osca_sc))

        available_slim.append({
            "country_code": a["country_code"],
            "code": c_str,
            "title": a["title"],
            "group": a["group"],
            "assessing_body": a.get("assessing_body"),
            "pathway": a.get("pathway"),
            "assessment_outcome": sa.get("assessment_outcome"),
            "is_positive": sa.get("is_positive"),
            "deducted_years": sa.get("deducted_years"),
            "claimable_years": sa.get("points_claimable_years"),
            "anzsco_2013_subclasses": anz_sc,
            "osca_2022_subclasses": osca_sc,
            "eligible_subclasses": all_active_sc,
            "tasks": (a.get("tasks") or a.get("typical_tasks") or [])[:4],
        })

    work_chronology_lines = []
    for idx, w in enumerate(work_hist, 1):
        desig = w.get("designation") or w.get("job_title") or w.get("title") or "Professional"
        emp = w.get("employer") or w.get("employer_name") or "Company"
        nat = w.get("company_nature") or w.get("nature_of_company") or cand_company_nature or "Commercial"
        dates = w.get("dates") or f"{w.get('start_date', '')} - {w.get('end_date', 'Present')}"
        yrs = w.get("years") or 0.0
        d_text = w.get("duties") or "; ".join(w.get("duty_bullets") or []) or "Standard duties"
        work_chronology_lines.append(
            f"Position {idx}: {desig} at {emp} (Sector: {nat}) | Dates: {dates} ({yrs} yrs)\n"
            f"  Core Duties & Tasks: {d_text}"
        )
    work_chronology_text = "\n\n".join(work_chronology_lines) if work_chronology_lines else cand_duties_text

    candidate_context = f"""
## CANDIDATE PROFESSIONAL SUMMARY
- Designation / Current Profession: {cand_prof}
- Current Employer: {cand_employer}
- Employer Business Sector / Industry: {cand_company_nature}
- Highest Qualification: {cand_qual} (Field of Study: {cand_field})
- Total Professional Experience: {cand_exp} years
- Candidate Age: {cand_age}

## CANDIDATE WORK EXPERIENCE CHRONOLOGY & ACTUAL JOB DUTIES
{work_chronology_text}

## FULL CANDIDATE PROFILE & DUTIES CONTEXT
{cand_duties_text}
"""

    user_prompt = (
        candidate_context
        + "\n\n## AVAILABLE_CODES (only suggest from this list)\n```json\n"
        + json.dumps(available_slim, ensure_ascii=False)
        + f"\n```\n\nCRITICAL INSTRUCTIONS:\n"
        + "1. ANALYSE CANDIDATE'S ENTIRE CAREER CHRONOLOGY ACROSS ALL PAST AND CURRENT ROLES. Do NOT evaluate only the current/latest job title. If the candidate worked across multiple distinct positions or specializations in their career (e.g. Software Developer, Systems Analyst, DevOps Engineer, Accountant, Auditor), suggest matching 6-digit occupation codes corresponding to their various qualified career stages so the immigration consultant can evaluate every viable pathway.\n"
        + "2. Base occupation code recommendations primarily on their ACTUAL WORK EXPERIENCE (real job titles, duties, tasks, tools, and responsibilities across all positions held).\n"
        + "3. Verify the assessing authority outcome is POSITIVE with minimum qualifying deductions.\n"
        + "4. FOR AUSTRALIA (AU): ALL SUGGESTED CODES MUST BE EXACTLY 6 DIGITS (e.g. 261312, 261313). 4-digit unit groups (e.g. 2613) are strictly forbidden.\n"
        + "5. SUBCLASS & FRAMEWORK VERIFICATION (ANZSCO 2013 vs OSCA 2022): For every suggested code, inspect 'anzsco_2013_subclasses' (Points-tested GSM: Subclasses 189, 190, 491, 494) and 'osca_2022_subclasses' (Employer/Core Skills: Subclasses 482, 186, 407, 485). Suggest codes that have verified active subclasses matching the candidate's pathway. Explicitly state in the reasoning and considerations which specific subclasses and framework the code qualifies for.\n"
        + "6. DO NOT DEFAULT TO 221111 (Accountant General) OR 224713 (Management Consultant). Match the candidate's SPECIFIC career path. If candidate is a Finance Manager, FP&A lead, or Corporate Finance leader: suggest 132211 (Finance Manager) or 222312 (Financial Investment Manager) — NOT Accountant (221111). Only suggest Management Consultant (224713) if the candidate actually worked in consulting, advisory, or business transformation.\n"
        + f"Suggest the TOP {req.max_suggestions} codes where duties best match their actual responsibilities across their career and the assessing authority outcome is POSITIVE. Return JSON only."
    )

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai",
        http_client=_SHARED_HTTP_CLIENT
    )

    try:
        response = await client.chat.completions.create(
            model="sonar-pro",
            temperature=0.1,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SUGGESTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw = response.choices[0].message.content or ""
        logger.info("Perplexity suggest-occupation response received (length=%d)", len(raw))
        parsed = _safe_json_loads(raw, fallback_codes=top_codes[:req.max_suggestions])

        valid_set = {
            (a["country_code"], str(a["code"]))
            for a in available_codes
        }

        filtered_suggestions = []
        for s in parsed.get("suggestions", []):
            cc = s.get("country_code", "AU").upper()
            code_str = str(s.get("code", "")).strip()

            # Strictly enforce 6-digit codes for Australia (no 4-digit unit groups)
            if cc == "AU" and len(code_str) != 6:
                if len(code_str) == 4 and code_str.isdigit():
                    # Resolve 4-digit unit group to the best 6-digit code in available_codes
                    matching_6 = [a for a in top_codes if str(a.get("code", "")).startswith(code_str) and len(str(a.get("code", ""))) == 6]
                    if matching_6:
                        code_str = str(matching_6[0]["code"])
                        s["code"] = code_str
                        s["title"] = matching_6[0].get("title") or s.get("title")
                    else:
                        continue
                else:
                    continue

            s["country_code"] = cc
            s["code"] = code_str
            s["_verified"] = (cc, code_str) in valid_set
            occ_full = occ_doc_map.get((cc, code_str)) or {
                "country_code": cc,
                "code": code_str,
                "title": s.get("title", ""),
                "assessing_body": s.get("assessing_body"),
            }
            _enrich_suggestion_skills(
                s,
                occ_full,
                candidate_profile,
                cand_duties_text=cand_duties_text,
                cand_company_nature=cand_company_nature,
                cand_employer=cand_employer,
                cand_age=cand_age,
                classification_cfg=classification_cfg,
            )
            filtered_suggestions.append(s)

        parsed["suggestions"] = filtered_suggestions
        parsed.setdefault("_ai_status", "ok")
        parsed["_ai_model"] = "sonar-pro"
        return parsed

    except Exception as e:
        logger.warning("Perplexity API call failed (%s) — falling back to deep duty AI matcher", e)
        top = top_codes[:req.max_suggestions]
        suggestions = []
        for occ in top:
            score = _score_occ(occ)
            conf = "high" if score >= 400 else ("medium" if score >= 200 else "low")
            title = occ.get("title", "")
            group = occ.get("group") or title
            body = occ.get("assessing_body") or "Designated Assessing Authority"
            path = occ.get("pathway") or "Core Skills / GSM"
            cc = occ.get("country_code", "AU")
            code_str = str(occ.get("code", ""))
            occ_full = occ_doc_map.get((cc.upper(), code_str)) or occ

            s_item = {
                "country_code": cc,
                "code": code_str,
                "title": title,
                "confidence": conf,
                "assessing_body": body,
                "pathway": path,
                "_verified": True,
            }
            _enrich_suggestion_skills(
                s_item,
                occ_full,
                candidate_profile,
                cand_duties_text=cand_duties_text,
                cand_company_nature=cand_company_nature,
                cand_employer=cand_employer,
                cand_age=cand_age,
                classification_cfg=classification_cfg,
            )
            suggestions.append(s_item)

        return {
            "suggestions": suggestions,
            "general_advice": "Prioritise codes where duties directly align with ABS tasks and assessing authority qualifying deductions maximize claimable GSM points.",
            "_ai_status": "ok",
            "_ai_model": "deep-duty-ai-matcher",
        }


# ════════════════════════════════════════════════════════════════
# Phase 10.3 — ATLAS AUTO-SUGGEST (free-text → NOC + PNP + EE intel)
# ════════════════════════════════════════════════════════════════
ATLAS_AUTO_SUGGEST_SYSTEM_PROMPT = """You are an immigration occupation matching expert.

A sales rep will describe a candidate in plain English, optionally with a destination
country and/or sub-region (province/state). Your task: from the OCCUPATION_LIST, return
the TOP 3-5 occupation codes that best match the candidate's CURRENT occupation.

ABSOLUTE RULES
🔴 RULE 1 — Match on the candidate's CURRENT job duties, NOT their degree.
🔴 RULE 2 — Only suggest codes from OCCUPATION_LIST. Do NOT invent codes.
🔴 RULE 3 — If a destination sub-region (province/state) is mentioned, prefer codes
            that region targets.
🔴 RULE 4 — Confidence: HIGH (clear duty match), MEDIUM (related), LOW (loose).
🔴 RULE 5 — Output ONLY JSON, no prose, no markdown.

OUTPUT FORMAT
{
  "suggestions": [
    {
      "code": "21231",
      "title": "Software engineers and designers",
      "confidence": "high|medium|low",
      "reasoning": "2-3 sentence match explanation",
      "destination_region_match": true
    }
  ],
  "tip": "1-sentence sales advice"
}
"""


class AtlasAutoSuggestRequest(BaseModel):
    description: str = Field(..., min_length=15, max_length=2000)
    country_code: str = Field("CA", description="AU / CA / NZ destination country")
    region_code: Optional[str] = Field(None, description="Optional state/province: NSW/VIC/BC/ON/etc")
    max_suggestions: int = Field(5, ge=1, le=8)


@router.post("/atlas-auto-suggest")
async def atlas_auto_suggest(req: AtlasAutoSuggestRequest, current_user: dict = Depends(get_current_user)):
    """Phase 10.3 - Multi-country Atlas Auto-Suggest.

    Free-text to top occupation matches enriched with country-specific Atlas data.
    Works across AU (ANZSCO 6-digit), CA (NOC 5-digit), NZ (ANZSCO 6-digit).
    """
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    api_key = (os.getenv("PERPLEXITY_API_KEY") or PERPLEXITY_API_KEY or "").strip()
    country = (req.country_code or "CA").upper()
    if country not in {"AU", "CA", "NZ"}:
        raise HTTPException(status_code=400, detail=f"Unsupported country: {country}")

    # Country-specific priority field used for region-match enrichment
    if country == "AU":
        priority_match_key = "state_nomination"
    elif country == "CA":
        priority_match_key = "pnp_eligibility"
    else:  # NZ
        priority_match_key = "regional_skill_shortage"

    # Slim list — cap to top relevant codes for prompt size
    available: List[Dict[str, Any]] = []
    async for occ in db["occupation_master"].find(
        {"country_code": country, "status": {"$ne": "superseded"}},
        {"_id": 0, "code": 1, "title": 1, "teer_category": 1, "skill_level": 1,
         "alternative_titles": 1, "hierarchy": 1, priority_match_key: 1, "state_nomination": 1},
    ):
        region_match = False
        if req.region_code:
            rc = req.region_code.upper()
            if country == "CA":
                for p in (occ.get("pnp_eligibility") or []):
                    if (p.get("province_code") or "").upper() == rc:
                        region_match = True
                        break
            elif country == "AU":
                state_doc = occ.get("state_nomination") or {}
                if rc in state_doc and state_doc.get(rc):
                    region_match = True
        major_group = (occ.get("hierarchy") or {}).get("major_group", {}) if isinstance(occ.get("hierarchy"), dict) else {}
        available.append({
            "code": str(occ.get("code", "")),
            "title": occ.get("title", ""),
            "skill_level_or_teer": occ.get("teer_category") if country == "CA" else occ.get("skill_level"),
            "major_group": major_group.get("title") if isinstance(major_group, dict) else None,
            "alt": (occ.get("alternative_titles") or [])[:5],
            "_region_match": region_match,
        })

    if not available:
        raise HTTPException(
            status_code=400,
            detail=f"No {country} occupation codes available in Atlas yet.",
        )

    # Score available codes by keywords
    desc_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', req.description.lower()))
    def _score_atlas(a: dict) -> int:
        score = 0
        t_low = (a.get("title") or "").lower()
        alts = [str(x).lower() for x in (a.get("alt") or [])]
        code_str = a.get("code") or ""
        for w in desc_words:
            if w in t_low:
                score += 25
            elif any(w in alt for alt in alts):
                score += 15
            elif w == code_str:
                score += 35
        for dom_name, dom_info in SYNONYM_DOMAINS.items():
            if code_str in dom_info["occ_codes"]:
                dom_matches = [r for r in dom_info["roots"] if any(w.startswith(r) for w in desc_words)]
                if dom_matches:
                    score += len(dom_matches) * 15
        if a.get("_region_match"):
            score += 8
        return score

    scored_available = sorted(available, key=_score_atlas, reverse=True)
    positive_scored = [a for a in scored_available if _score_atlas(a) > 0]
    top_available = positive_scored[:50] if positive_scored else scored_available[:50]

    available_slim = [{k: v for k, v in a.items() if not k.startswith("_")} for a in top_available]

    classification_label = "NOC 2021" if country == "CA" else "ANZSCO"
    region_hint = ""
    if req.region_code:
        region_label = "PROVINCE" if country == "CA" else "STATE"
        region_hint = f"## DESTINATION {region_label} PREFERENCE\n{req.region_code.upper()}\n\n"

    user_prompt = (
        f"## DESTINATION COUNTRY\n{country} (classification: {classification_label})\n\n"
        f"## CANDIDATE DESCRIPTION\n{req.description.strip()}\n\n"
        f"{region_hint}"
        + "## OCCUPATION_LIST\n```json\n"
        + json.dumps(available_slim, ensure_ascii=False)
        + f"\n```\n\nSuggest the top {req.max_suggestions} occupation codes. Return JSON only."
    )

    parsed = None
    if api_key:
        try:
            client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.perplexity.ai",
                http_client=_SHARED_HTTP_CLIENT
            )
            response = await client.chat.completions.create(
                model="sonar-pro",
                temperature=0.1,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": ATLAS_AUTO_SUGGEST_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content or ""
            parsed = _safe_json_loads(raw, fallback_codes=top_available[:req.max_suggestions])
        except Exception as e:
            logger.warning("Atlas auto-suggest Perplexity call failed, using heuristic: %s", e)

    if not parsed or not parsed.get("suggestions"):
        fallback_suggestions = []
        for a in top_available[:req.max_suggestions]:
            fallback_suggestions.append({
                "code": a["code"],
                "title": a["title"],
                "confidence": "high" if a.get("_region_match") else "medium",
                "reasoning": f"Closest match based on candidate profile and skills for {country}.",
                "destination_region_match": bool(a.get("_region_match")),
            })
        parsed = {
            "suggestions": fallback_suggestions,
            "tip": f"Review immigration criteria and assessing authorities for {country}.",
            "_ai_status": "fallback",
        }

    # Enrich each suggestion with full country-specific Atlas data
    valid_codes = {str(a["code"]) for a in available}
    enriched: List[Dict[str, Any]] = []
    for s in parsed.get("suggestions", []):
        code = str(s.get("code", ""))
        if code not in valid_codes:
            continue
        full = await db["occupation_master"].find_one(
            {"country_code": country, "code": code},
            {"_id": 0, "code": 1, "title": 1, "teer_category": 1, "teer_label": 1,
             "skill_level": 1, "ee_eligibility": 1, "pnp_eligibility": 1,
             "quebec_eligibility": 1, "ircc_round_cutoffs": 1, "regional_pilot_eligibility": 1,
             "state_nomination": 1, "visa_pathways": 1, "skillselect_tier": 1,
             "hierarchy": 1, "assessing_authority": 1, "min_invitation_points": 1},
        )
        if not full:
            continue
        s["atlas"] = full
        enriched.append(s)

    # If enrichment left 0 items (e.g. invalid codes returned), enrich top_available
    if not enriched:
        for a in top_available[:req.max_suggestions]:
            full = await db["occupation_master"].find_one(
                {"country_code": country, "code": a["code"]},
                {"_id": 0}
            )
            enriched.append({
                "code": a["code"],
                "title": a["title"],
                "confidence": "medium",
                "reasoning": "Keyword match with candidate duties.",
                "destination_region_match": bool(a.get("_region_match")),
                "atlas": full or {},
            })

    return {
        "suggestions": enriched,
        "tip": parsed.get("tip") or "Consult client on their preferred destination and verify processing times.",
        "_total_candidates_considered": len(available),
        "_ai_model": parsed.get("_ai_model", "sonar-pro"),
        "_ai_status": parsed.get("_ai_status", "ok"),
    }
