"""CRM Website Leads Router — Live Website Enquiry Capture, Auto-Classification (PR/TR/General/Other) & Country Drilldown"""
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from core.database import db
from core.auth import get_current_user
from core.services import create_notification, log_activity

router = APIRouter(prefix="/crm/website-leads", tags=["CRM Website Leads"])

leads_col = db["leads"]
users_col = db["users"]

COUNTRY_NAME_MAP = {
    "AU": "Australia",
    "CA": "Canada",
    "UK": "United Kingdom",
    "GB": "United Kingdom",
    "US": "United States",
    "USA": "United States",
    "NZ": "New Zealand",
    "DE": "Germany",
    "IE": "Ireland",
    "SG": "Singapore",
    "AE": "UAE",
    "EUROPEAN COUNTRIES": "European Countries",
    "EUROPE": "European Countries",
    "GLOBAL / OTHER": "Other",
    "GLOBAL": "Other",
    "OTHER": "Other",
}

CATEGORY_PR = "PR"
CATEGORY_TR = "TR"
CATEGORY_WORK = "Work"
CATEGORY_STUDY = "Study"
CATEGORY_TOURIST = "Tourist"
CATEGORY_FAMILY = "Family"
CATEGORY_GENERAL = "General"
CATEGORY_OTHER = "Other"
CATEGORY_ATLAS = "Atlas"

ALL_CATEGORIES = [
    CATEGORY_PR,
    CATEGORY_TR,
    CATEGORY_WORK,
    CATEGORY_STUDY,
    CATEGORY_TOURIST,
    CATEGORY_FAMILY,
    CATEGORY_GENERAL,
    CATEGORY_ATLAS
]

CATEGORY_METADATA = {
    CATEGORY_PR: {
        "code": CATEGORY_PR,
        "label": "PR (Permanent Residency)",
        "description": "Permanent residence pathways including Australia Subclass 189/190/491, Canada Express Entry (FSWP/CEC/PNP), and NZ SMC / Green List Tier 1.",
        "badge_color": "emerald"
    },
    CATEGORY_TR: {
        "code": CATEGORY_TR,
        "label": "TR (Temporary Residency)",
        "description": "Temporary residence, work permits, student visas, TSS Subclass 482/485, AEWV, and visitor visas.",
        "badge_color": "indigo"
    },
    CATEGORY_WORK: {
        "code": CATEGORY_WORK,
        "label": "Work",
        "description": "Employer-sponsored work visas, TSS Subclass 482/186/400, UK Skilled Worker, Canada LMIA & Work Permits, AEWV, and H-1B.",
        "badge_color": "blue"
    },
    CATEGORY_STUDY: {
        "code": CATEGORY_STUDY,
        "label": "Study",
        "description": "Student visas, Subclass 500, UK Student Visa, Canada Study Permit, SDS, and university/college admissions.",
        "badge_color": "purple"
    },
    CATEGORY_TOURIST: {
        "code": CATEGORY_TOURIST,
        "label": "Tourist",
        "description": "Tourist and visitor visas, Subclass 600, UK Standard Visitor, US B1/B2, and tourist travel permits.",
        "badge_color": "teal"
    },
    CATEGORY_FAMILY: {
        "code": CATEGORY_FAMILY,
        "label": "Family",
        "description": "Partner & spouse visas (Subclass 309/100, 820/801), UK Family Visa, child & parent sponsorship, and super visas.",
        "badge_color": "rose"
    },
    CATEGORY_GENERAL: {
        "code": CATEGORY_GENERAL,
        "label": "General",
        "description": "Eligibility assessments, skill assessments, point calculator inquiries, and comprehensive migration evaluations.",
        "badge_color": "amber"
    },
    CATEGORY_ATLAS: {
        "code": CATEGORY_ATLAS,
        "label": "Atlas",
        "description": "Migration Atlas occupation pathway enquiries (ANZSCO/NOC consultations) and free immigration points calculator / assessment submissions.",
        "badge_color": "cyan"
    }
}

WEBSITE_LEAD_CONDITIONS = [
    {"source": {"$in": ["Website", "website", "public_atlas", "public_landing", "landing_page", "website_enquiry", "eligibility_pre_score", "eligibility_quiz", "atlas", "state_landing", "shared_fee_estimate", "Website (Popup)", "Website Popup"]}},
    {"source": {"$regex": "website", "$options": "i"}},
    {"source": {"$regex": "state_landing", "$options": "i"}},
    {"website_page_url": {"$exists": True, "$ne": ""}},
    {"atlas_code": {"$exists": True, "$ne": ""}},
    {"tags": {"$in": ["public_atlas", "atlas", "website", "website_enquiry", "fee-estimate-viewer", "popup_enquiry", "general_enquiry"]}}
]


def _is_admin(user: dict) -> bool:
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in ["admin", "admin_owner", "super_admin"] or rbac in ["admin", "admin_owner", "super_admin"]


def _is_manager_or_admin(user: dict) -> bool:
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in ["admin", "admin_owner", "super_admin", "sales_manager", "sales_head"] or rbac in ["admin_owner", "sales_manager", "sales_head", "admin", "super_admin"]


def normalize_country(raw_country: Any, page_url: str = "", atlas_code: str = "") -> str:
    """Normalizes country input into standard full name (e.g. Australia, Canada, UK, USA, New Zealand, European Countries, Other)."""
    if raw_country:
        c_clean = str(raw_country).strip().upper()
        if c_clean in ("GLOBAL / OTHER", "GLOBAL", "OTHER"):
            return "Other"
        if c_clean in COUNTRY_NAME_MAP:
            return COUNTRY_NAME_MAP[c_clean]
        c_title = str(raw_country).strip().title()
        if c_title in ("Global / Other", "Global", "Other"):
            return "Other"
        for k, v in COUNTRY_NAME_MAP.items():
            if c_title.lower() == v.lower():
                return v
        if str(raw_country).strip():
            rc = str(raw_country).strip()
            if rc.lower() in ("global / other", "global", "other"):
                return "Other"
            return rc

    url_lower = str(page_url or "").lower()
    if "/au" in url_lower or "australia" in url_lower:
        return "Australia"
    if "/ca" in url_lower or "canada" in url_lower:
        return "Canada"
    if "/uk" in url_lower or "united-kingdom" in url_lower:
        return "United Kingdom"
    if "/us" in url_lower or "usa" in url_lower or "united-states" in url_lower:
        return "United States"
    if "/nz" in url_lower or "new-zealand" in url_lower:
        return "New Zealand"

    return "Other"


PR_KEYWORDS = [
    "pr", "permanent", "189", "190", "491", "186", "express entry", "fswp", "cec", "fstp",
    "pnp", "oinp", "bcpnp", "ainp", "sinp", "smc", "skilled migrant", "green list tier 1",
    "green list tier 2", "green list", "straight to residence", "work to residence",
    "skilled migrant category", "permanent residency", "skilled independent",
    "skilled nominated", "skilled regional", "subclass 189", "subclass 190", "subclass 491",
    "subclass 186", "subclass 820", "subclass 801", "subclass 309", "subclass 100",
    "partner visa onshore", "partner visa offshore",
    "eb1", "eb-1", "eb2", "eb-2", "eb3", "eb-3", "eb4", "eb-4", "eb5", "eb-5", "green card",
    "spousal sponsorship", "child sponsorship", "dependent child", "parents and grandparents",
    "pgp", "startup visa", "start-up visa", "self-employed", "provincial entrepreneur",
    "f2a", "f2b", "f3", "ir1", "cr1", "ir2", "ir5", "global talent", "858", "ilr", "settlement",
    "pr australia", "pr canada"
]

TR_KEYWORDS = [
    "tr", "temporary", "482", "485", "aewv", "work permit", "work visa", "working holiday",
    "skilled worker", "health and care worker", "health care worker", "worker",
    "student", "study", "visitor", "tourist", "subclass 482", "subclass 485", "408", "476",
    "500", "600", "subclass 400", "subclass 462", "open work permit", "lmia", "graduate",
    "post graduate", "under graduate", "study abroad", "tourist visa", "pswv", "post study work visa",
    "fee paying student", "exchange student", "accredited employer", "transit visa",
    "o1", "o-1", "h1b", "h-1b", "h2b", "h-2b", "l1", "l-1", "f1", "f-1", "m1", "m-1",
    "j1", "j-1", "b1", "b2", "b1/b2", "p1", "p2", "p3", "k1", "k3", "super visa", "sds", "non-sds",
    "business visitor", "family visit", "closed work permit", "employer specific",
    "subclass 309", "subclass 820", "tr australia", "tr canada"
]

WORK_KEYWORDS = [
    "work", "work permit", "work visa", "working holiday", "skilled worker", "health and care worker",
    "health care worker", "health & care", "senior or specialist worker", "scale-up", "expansion worker",
    "482", "subclass 482", "tss", "186", "subclass 186", "ens", "400", "subclass 400",
    "494", "subclass 494", "407", "subclass 407", "408", "subclass 408", "462", "subclass 462",
    "417", "subclass 417", "aewv", "accredited employer", "lmia", "open work permit",
    "closed work permit", "employer specific", "pgwp", "post graduation work permit",
    "h1b", "h-1b", "h2b", "h-2b", "l1", "l-1", "o1", "o-1", "p1", "p2", "p3",
    "job offer", "employer sponsored", "employer nomination", "work to residence",
    "work visa australia", "work permit canada"
]

STUDY_KEYWORDS = [
    "student", "study", "study abroad", "student visa", "study permit",
    "500", "subclass 500", "590", "subclass 590",
    "uk student visa", "child student visa", "under graduate", "post graduate",
    "undergraduate", "postgraduate", "pswv", "post study work visa", "post study",
    "fee paying student", "exchange student", "pathway student", "sds", "non-sds",
    "f1", "f-1", "m1", "m-1", "j1", "j-1", "higher education",
    "study in australia", "study in canada", "study in uk", "study in new zealand"
]

TOURIST_KEYWORDS = [
    "tourist", "visitor", "tourist visa", "visitor visa", "visit", "tourism",
    "600", "subclass 600", "601", "subclass 601", "651", "subclass 651", "771", "subclass 771",
    "eta", "evisitor", "standard visitor", "general visitor",
    "b1", "b2", "b1/b2", "b-1", "b-2", "business visitor", "transit", "transit visa",
    "vacation", "holiday visa", "nzeta",
    "tourist visa australia", "tourist visa canada", "visitor visa australia"
]

FAMILY_KEYWORDS = [
    "family", "partner", "spouse", "spousal", "marriage", "fiancé", "fiance",
    "309", "subclass 309", "100", "subclass 100", "820", "subclass 820", "801", "subclass 801",
    "300", "subclass 300", "prospective marriage", "parent visa", "contributory parent",
    "143", "173", "804", "864", "870", "sponsored parent",
    "101", "102", "445", "802", "child visa", "dependent child", "child sponsorship",
    "uk family visa", "spouse / partner / child", "spousal sponsorship",
    "parents and grandparents", "pgp", "super visa", "family visit",
    "k1", "k-1", "k3", "k-3", "f2a", "f2b", "f3", "f4", "ir1", "cr1", "ir2", "ir5"
]

GENERAL_KEYWORDS = [
    "general", "assessment", "skill assessment", "eligibility", "calculator", "points",
    "score", "consultation", "advisory", "pre-assessment", "evaluation", "profile", "advice",
    "pre_score"
]

ATLAS_KEYWORDS = [
    "atlas", "migration atlas", "public_atlas", "points calculator", "point calculator",
    "eligibility calculator", "eligibility quiz", "anzsco", "noc", "pathway in 60 seconds",
    "pre_score", "eligibility_pre_score"
]


def is_atlas_lead(doc: Dict[str, Any]) -> bool:
    """Checks if a lead originated from the Migration Atlas pages or the Points Calculator (/start)."""
    if not doc:
        return False

    explicit = str(doc.get("lead_category") or doc.get("category") or "").strip().upper()
    if explicit == "ATLAS":
        return True

    src = str(doc.get("source") or "").strip().lower()
    if src in ("public_atlas", "atlas", "eligibility_quiz", "eligibility_pre_score"):
        return True

    if doc.get("atlas_code") or doc.get("atlas_title"):
        return True

    tags = doc.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if any("atlas" in str(t).lower() or "calculator" in str(t).lower() or "elig" in str(t).lower() for t in tags):
        return True

    page_url = str(doc.get("website_page_url") or doc.get("page_url") or "").lower()
    if "/atlas/" in page_url:
        return True

    page_title = str(doc.get("website_page_title") or doc.get("page_title") or "").lower()
    if "migration atlas" in page_title or "points calculator" in page_title or "point calculator" in page_title:
        return True

    msg = str(doc.get("message") or doc.get("msg") or "").lower()
    if "migration atlas" in msg or "points calculator" in msg or "anzsco" in msg:
        return True

    # If enquired_for matches a specific subclass in PAGE_METADATA_MAP, do not hijack it to Atlas
    enq_lower = str(doc.get("enquired_for") or "").strip().lower()
    enq_clean = re.sub(r'[\s\-_]+', ' ', enq_lower).strip()
    is_specific_subclass = bool(PAGE_METADATA_MAP.get(enq_lower) or PAGE_METADATA_MAP.get(enq_clean))

    if not is_specific_subclass:
        if "/start" in page_url or "/calculator" in page_url or "pathway in 60 seconds" in page_title:
            return True

    text_corpus = _extract_lead_text_corpus(doc)
    if _matches_any(text_corpus, ["public_atlas", "migration atlas", "points calculator", "point calculator"]):
        return True

    return False


def _matches_any(text: str, keywords: list) -> bool:
    for kw in keywords:
        if len(kw) <= 4 or " " not in kw:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                return True
        elif kw in text:
            return True
    return False


def _extract_lead_text_corpus(doc: Dict[str, Any]) -> str:
    # Important: do NOT include doc["work_experience"] or doc["total_work_experience"]
    # as that's applicant's experience length (e.g. "5 Years"), not visa purpose.
    return " ".join([
        str(doc.get("service_interested") or ""),
        str(doc.get("service_type") or ""),
        str(doc.get("services") or ""),
        str(doc.get("enquired_for") or ""),
        str(doc.get("visa_type") or ""),
        str(doc.get("visa_pathway") or ""),
        str(doc.get("interested_program") or ""),
        str(doc.get("atlas_title") or ""),
        str(doc.get("website_page_title") or ""),
        str(doc.get("website_page_url") or ""),
        str(doc.get("message") or ""),
        str(doc.get("msg") or ""),
        str(doc.get("tag") or ""),
        str(doc.get("tags") or "")
    ]).lower()


def classify_lead_category(doc: Dict[str, Any]) -> str:
    """
    Classifies lead into PR, TR, Work, Study, Tourist, Family, General, or Atlas using:
    - explicitly stored lead_category
    - service_interested / service_type / services
    - visa_type / interested_program
    - atlas_title / message / msg / website_page_title / website_page_url / enquired_for
    """
    explicit = str(doc.get("lead_category") or doc.get("category") or "").strip().upper()
    if explicit == "ATLAS":
        return CATEGORY_ATLAS
    if is_atlas_lead(doc):
        return CATEGORY_ATLAS
    if explicit in (CATEGORY_PR, CATEGORY_TR, "GENERAL", "OTHER"):
        return CATEGORY_GENERAL if explicit in ("GENERAL", "OTHER") else explicit
    if explicit in (CATEGORY_WORK.upper(), CATEGORY_STUDY.upper(), CATEGORY_TOURIST.upper(), CATEGORY_FAMILY.upper()):
        if explicit == CATEGORY_WORK.upper():
            return CATEGORY_WORK
        if explicit == CATEGORY_STUDY.upper():
            return CATEGORY_STUDY
        if explicit == CATEGORY_TOURIST.upper():
            return CATEGORY_TOURIST
        if explicit == CATEGORY_FAMILY.upper():
            return CATEGORY_FAMILY

    text_corpus = _extract_lead_text_corpus(doc)

    if is_atlas_lead(doc):
        return CATEGORY_ATLAS
    if _matches_any(text_corpus, PR_KEYWORDS):
        return CATEGORY_PR
    if _matches_any(text_corpus, TR_KEYWORDS):
        return CATEGORY_TR
    if _matches_any(text_corpus, GENERAL_KEYWORDS):
        return CATEGORY_GENERAL

    return CATEGORY_GENERAL


def get_lead_categories(doc: Dict[str, Any]) -> Set[str]:
    """
    Returns all categories a lead belongs to:
    (PR, TR, Work, Study, Tourist, Family, General, Atlas)
    """
    categories: Set[str] = set()
    explicit = str(doc.get("lead_category") or doc.get("category") or "").strip().upper()

    if explicit in (CATEGORY_PR.upper(), "PR"):
        categories.add(CATEGORY_PR)
    elif explicit in (CATEGORY_TR.upper(), "TR"):
        categories.add(CATEGORY_TR)
    elif explicit in (CATEGORY_WORK.upper(), "WORK"):
        categories.add(CATEGORY_WORK)
    elif explicit in (CATEGORY_STUDY.upper(), "STUDY"):
        categories.add(CATEGORY_STUDY)
    elif explicit in (CATEGORY_TOURIST.upper(), "TOURIST"):
        categories.add(CATEGORY_TOURIST)
    elif explicit in (CATEGORY_FAMILY.upper(), "FAMILY"):
        categories.add(CATEGORY_FAMILY)
    elif explicit in (CATEGORY_ATLAS.upper(), "ATLAS"):
        categories.add(CATEGORY_ATLAS)
    elif explicit in ("GENERAL", CATEGORY_GENERAL.upper(), "OTHER"):
        categories.add(CATEGORY_GENERAL)

    text_corpus = _extract_lead_text_corpus(doc)

    if _matches_any(text_corpus, PR_KEYWORDS):
        categories.add(CATEGORY_PR)
    if _matches_any(text_corpus, TR_KEYWORDS):
        categories.add(CATEGORY_TR)
    if _matches_any(text_corpus, WORK_KEYWORDS):
        categories.add(CATEGORY_WORK)
    if _matches_any(text_corpus, STUDY_KEYWORDS):
        categories.add(CATEGORY_STUDY)
    if _matches_any(text_corpus, TOURIST_KEYWORDS):
        categories.add(CATEGORY_TOURIST)
    if _matches_any(text_corpus, FAMILY_KEYWORDS):
        categories.add(CATEGORY_FAMILY)
    if _matches_any(text_corpus, GENERAL_KEYWORDS):
        categories.add(CATEGORY_GENERAL)
    if is_atlas_lead(doc):
        categories.add(CATEGORY_ATLAS)

    # Check PAGE_METADATA_MAP for matched category
    enq_lower = str(doc.get("enquired_for") or "").strip().lower()
    enq_clean = re.sub(r'[\s\-_]+', ' ', enq_lower).strip()
    matched_entry = PAGE_METADATA_MAP.get(enq_lower) or PAGE_METADATA_MAP.get(enq_clean)
    if not matched_entry and doc.get("website_page_url"):
        url_clean = str(doc.get("website_page_url")).rstrip("/").lower()
        for k, v in PAGE_METADATA_MAP.items():
            if v[1].rstrip("/").lower() == url_clean:
                matched_entry = v
                break
    if matched_entry and len(matched_entry) >= 4:
        meta_cat = matched_entry[3]
        if meta_cat:
            categories.add(meta_cat)

    if not categories:
        categories.add(CATEGORY_GENERAL)

    return categories


def lead_matches_category(doc: Dict[str, Any], target_category: str) -> bool:
    """Checks if a lead matches the given category filter."""
    if not target_category or target_category.strip().upper() == "ALL":
        return True
    target = target_category.strip().upper()
    cats = {c.upper() for c in get_lead_categories(doc)}
    return target in cats


PAGE_METADATA_MAP = {
    # --- UK SPECIFIC SUBCLASS PAGES ---
    "uk skilled worker visa": (
        "UK Skilled Worker Visa for Indians 2026 | Requirements, Fees & Process",
        "https://leamss.com/uk/visa/uk-skilled-worker-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk-skilled-worker-visa": (
        "UK Skilled Worker Visa for Indians 2026 | Requirements, Fees & Process",
        "https://leamss.com/uk/visa/uk-skilled-worker-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk health and care worker": (
        "UK Health and Care Worker Visa for Indians 2025 | NHS Visa Guide",
        "https://leamss.com/uk/visa/uk-health-care-worker-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk-health-care-worker-visa": (
        "UK Health and Care Worker Visa for Indians 2025 | NHS Visa Guide",
        "https://leamss.com/uk/visa/uk-health-care-worker-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk health & care worker visa": (
        "UK Health and Care Worker Visa for Indians 2025 | NHS Visa Guide",
        "https://leamss.com/uk/visa/uk-health-care-worker-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk student visa": (
        "UK Student Visa 2026 | Requirements, Fees & Process",
        "https://leamss.com/uk/visa/uk-student-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk-student-visa": (
        "UK Student Visa 2026 | Requirements, Fees & Process",
        "https://leamss.com/uk/visa/uk-student-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk family visa (spouse / partner / child)": (
        "UK Family Visa for Indians 2026 | Spouse, Partner & Child Visa Guide",
        "https://leamss.com/uk/visa/uk-family-visa-spouse-partner-child",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk-family-visa-spouse-partner-child": (
        "UK Family Visa for Indians 2026 | Spouse, Partner & Child Visa Guide",
        "https://leamss.com/uk/visa/uk-family-visa-spouse-partner-child",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk family visa": (
        "UK Family Visa for Indians 2026 | Spouse, Partner & Child Visa Guide",
        "https://leamss.com/uk/visa/uk-family-visa-spouse-partner-child",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk global talent visa": (
        "UK Global Talent Visa 2026 | Leaders in Tech, Arts & Research",
        "https://leamss.com/uk/visa/uk-global-talent-visa",
        "United Kingdom",
        CATEGORY_PR,
    ),
    "uk-global-talent-visa": (
        "UK Global Talent Visa 2026 | Leaders in Tech, Arts & Research",
        "https://leamss.com/uk/visa/uk-global-talent-visa",
        "United Kingdom",
        CATEGORY_PR,
    ),
    "uk standard visitor visa": (
        "UK Standard Visitor Visa for Indians 2026 | Requirements & Fees",
        "https://leamss.com/uk/visa/uk-standard-visitor-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk-standard-visitor-visa": (
        "UK Standard Visitor Visa for Indians 2026 | Requirements & Fees",
        "https://leamss.com/uk/visa/uk-standard-visitor-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk indefinite leave to remain and british citizenship": (
        "UK ILR and British Citizenship for Indians 2025 | Settlement Guide",
        "https://leamss.com/uk/visa/uk-ilr-british-citizenship",
        "United Kingdom",
        CATEGORY_PR,
    ),
    "uk-ilr-british-citizenship": (
        "UK ILR and British Citizenship for Indians 2025 | Settlement Guide",
        "https://leamss.com/uk/visa/uk-ilr-british-citizenship",
        "United Kingdom",
        CATEGORY_PR,
    ),
    "uk ilr": (
        "UK ILR and British Citizenship for Indians 2025 | Settlement Guide",
        "https://leamss.com/uk/visa/uk-ilr-british-citizenship",
        "United Kingdom",
        CATEGORY_PR,
    ),

    # --- UK MAIN LANDING PAGE ---
    "uk visa": (
        "UK Visa for Indians 2026 | Complete Immigration Guide",
        "https://leamss.com/uk-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "uk-visa": (
        "UK Visa for Indians 2026 | Complete Immigration Guide",
        "https://leamss.com/uk-visa",
        "United Kingdom",
        CATEGORY_TR,
    ),

    # --- NEW ZEALAND SPECIFIC SUBCLASS PAGES ---
    "nz post study work visa": (
        "New Zealand Post Study Work Visa 2026 | PSWV Requirements & Process",
        "https://leamss.com/nz/visa/post-study-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "post study work visa": (
        "New Zealand Post Study Work Visa 2026 | PSWV Requirements & Process",
        "https://leamss.com/nz/visa/post-study-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "post-study-work-visa": (
        "New Zealand Post Study Work Visa 2026 | PSWV Requirements & Process",
        "https://leamss.com/nz/visa/post-study-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz-post-study-work-visa": (
        "New Zealand Post Study Work Visa 2026 | PSWV Requirements & Process",
        "https://leamss.com/nz/visa/post-study-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "new zealand post study work visa": (
        "New Zealand Post Study Work Visa 2026 | PSWV Requirements & Process",
        "https://leamss.com/nz/visa/post-study-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "pswv": (
        "New Zealand Post Study Work Visa 2026 | PSWV Requirements & Process",
        "https://leamss.com/nz/visa/post-study-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz pswv": (
        "New Zealand Post Study Work Visa 2026 | PSWV Requirements & Process",
        "https://leamss.com/nz/visa/post-study-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),

    "nz accredited employer work visa": (
        "New Zealand AEWV Work Visa 2026 | Requirements, Fees & Application Process",
        "https://leamss.com/nz/visa/accredited-employer-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "accredited employer work visa": (
        "New Zealand AEWV Work Visa 2026 | Requirements, Fees & Application Process",
        "https://leamss.com/nz/visa/accredited-employer-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "accredited-employer-work-visa": (
        "New Zealand AEWV Work Visa 2026 | Requirements, Fees & Application Process",
        "https://leamss.com/nz/visa/accredited-employer-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz-accredited-employer-work-visa": (
        "New Zealand AEWV Work Visa 2026 | Requirements, Fees & Application Process",
        "https://leamss.com/nz/visa/accredited-employer-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "new zealand accredited employer work visa": (
        "New Zealand AEWV Work Visa 2026 | Requirements, Fees & Application Process",
        "https://leamss.com/nz/visa/accredited-employer-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "aewv": (
        "New Zealand AEWV Work Visa 2026 | Requirements, Fees & Application Process",
        "https://leamss.com/nz/visa/accredited-employer-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz aewv": (
        "New Zealand AEWV Work Visa 2026 | Requirements, Fees & Application Process",
        "https://leamss.com/nz/visa/accredited-employer-work-visa",
        "New Zealand",
        CATEGORY_TR,
    ),

    "nz skilled migrant category resident visa": (
        "New Zealand Skilled Migrant Visa 2026 | NZ PR Guide",
        "https://leamss.com/nz/visa/skilled-migrant-category-resident-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "skilled migrant category resident visa": (
        "New Zealand Skilled Migrant Visa 2026 | NZ PR Guide",
        "https://leamss.com/nz/visa/skilled-migrant-category-resident-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "skilled-migrant-category-resident-visa": (
        "New Zealand Skilled Migrant Visa 2026 | NZ PR Guide",
        "https://leamss.com/nz/visa/skilled-migrant-category-resident-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "nz-skilled-migrant-category-resident-visa": (
        "New Zealand Skilled Migrant Visa 2026 | NZ PR Guide",
        "https://leamss.com/nz/visa/skilled-migrant-category-resident-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "new zealand skilled migrant category resident visa": (
        "New Zealand Skilled Migrant Visa 2026 | NZ PR Guide",
        "https://leamss.com/nz/visa/skilled-migrant-category-resident-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "nz smc": (
        "New Zealand Skilled Migrant Visa 2026 | NZ PR Guide",
        "https://leamss.com/nz/visa/skilled-migrant-category-resident-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "nz skilled migrant": (
        "New Zealand Skilled Migrant Visa 2026 | NZ PR Guide",
        "https://leamss.com/nz/visa/skilled-migrant-category-resident-visa",
        "New Zealand",
        CATEGORY_PR,
    ),

    "nz straight to residence visa": (
        "NZ Straight to Residence Visa 2026 | Green List PR",
        "https://leamss.com/nz/visa/straight-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "straight to residence visa": (
        "NZ Straight to Residence Visa 2026 | Green List PR",
        "https://leamss.com/nz/visa/straight-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "straight-to-residence-visa": (
        "NZ Straight to Residence Visa 2026 | Green List PR",
        "https://leamss.com/nz/visa/straight-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "nz-straight-to-residence-visa": (
        "NZ Straight to Residence Visa 2026 | Green List PR",
        "https://leamss.com/nz/visa/straight-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "new zealand straight to residence visa": (
        "NZ Straight to Residence Visa 2026 | Green List PR",
        "https://leamss.com/nz/visa/straight-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),

    "nz work to residence visa": (
        "New Zealand Work to Residence Visa 2026 Guide",
        "https://leamss.com/nz/visa/work-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "work to residence visa": (
        "New Zealand Work to Residence Visa 2026 Guide",
        "https://leamss.com/nz/visa/work-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "work-to-residence-visa": (
        "New Zealand Work to Residence Visa 2026 Guide",
        "https://leamss.com/nz/visa/work-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "nz-work-to-residence-visa": (
        "New Zealand Work to Residence Visa 2026 Guide",
        "https://leamss.com/nz/visa/work-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),
    "new zealand work to residence visa": (
        "New Zealand Work to Residence Visa 2026 Guide",
        "https://leamss.com/nz/visa/work-to-residence-visa",
        "New Zealand",
        CATEGORY_PR,
    ),

    "nz student visa": (
        "New Zealand Student Visa 2026 | Fees, Requirements & Study Visa Process",
        "https://leamss.com/nz/visa/fee-paying-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz fee paying student visa": (
        "New Zealand Student Visa 2026 | Fees, Requirements & Study Visa Process",
        "https://leamss.com/nz/visa/fee-paying-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "fee paying student visa": (
        "New Zealand Student Visa 2026 | Fees, Requirements & Study Visa Process",
        "https://leamss.com/nz/visa/fee-paying-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "fee-paying-student-visa": (
        "New Zealand Student Visa 2026 | Fees, Requirements & Study Visa Process",
        "https://leamss.com/nz/visa/fee-paying-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz-fee-paying-student-visa": (
        "New Zealand Student Visa 2026 | Fees, Requirements & Study Visa Process",
        "https://leamss.com/nz/visa/fee-paying-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "new zealand student visa": (
        "New Zealand Student Visa 2026 | Fees, Requirements & Study Visa Process",
        "https://leamss.com/nz/visa/fee-paying-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),

    "nz exchange student visa": (
        "New Zealand Exchange Student Visa 2026 | Fees, Requirements & How to Apply",
        "https://leamss.com/nz/visa/exchange-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "exchange student visa": (
        "New Zealand Exchange Student Visa 2026 | Fees, Requirements & How to Apply",
        "https://leamss.com/nz/visa/exchange-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "exchange-student-visa": (
        "New Zealand Exchange Student Visa 2026 | Fees, Requirements & How to Apply",
        "https://leamss.com/nz/visa/exchange-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz-exchange-student-visa": (
        "New Zealand Exchange Student Visa 2026 | Fees, Requirements & How to Apply",
        "https://leamss.com/nz/visa/exchange-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "new zealand exchange student visa": (
        "New Zealand Exchange Student Visa 2026 | Fees, Requirements & How to Apply",
        "https://leamss.com/nz/visa/exchange-student-visa",
        "New Zealand",
        CATEGORY_TR,
    ),

    "nz partner of a new zealand resident visa": (
        "New Zealand Family Visa 2026 | Partner & Parent Guide",
        "https://leamss.com/nz/visa/family-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "partner of a new zealand resident visa": (
        "New Zealand Family Visa 2026 | Partner & Parent Guide",
        "https://leamss.com/nz/visa/family-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz family visa": (
        "New Zealand Family Visa 2026 | Partner & Parent Guide",
        "https://leamss.com/nz/visa/family-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "family visa": (
        "New Zealand Family Visa 2026 | Partner & Parent Guide",
        "https://leamss.com/nz/visa/family-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz-family-visa": (
        "New Zealand Family Visa 2026 | Partner & Parent Guide",
        "https://leamss.com/nz/visa/family-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "new zealand family visa": (
        "New Zealand Family Visa 2026 | Partner & Parent Guide",
        "https://leamss.com/nz/visa/family-visa",
        "New Zealand",
        CATEGORY_TR,
    ),

    "nz business visitor visa": (
        "New Zealand Business Visitor Visa 2026 | Requirements, Fees & Apply Online",
        "https://leamss.com/nz/visa/business-visitor-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "business visitor visa": (
        "New Zealand Business Visitor Visa 2026 | Requirements, Fees & Apply Online",
        "https://leamss.com/nz/visa/business-visitor-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "business-visitor-visa": (
        "New Zealand Business Visitor Visa 2026 | Requirements, Fees & Apply Online",
        "https://leamss.com/nz/visa/business-visitor-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz-business-visitor-visa": (
        "New Zealand Business Visitor Visa 2026 | Requirements, Fees & Apply Online",
        "https://leamss.com/nz/visa/business-visitor-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "new zealand business visitor visa": (
        "New Zealand Business Visitor Visa 2026 | Requirements, Fees & Apply Online",
        "https://leamss.com/nz/visa/business-visitor-visa",
        "New Zealand",
        CATEGORY_TR,
    ),

    "nz visitor visa (general)": (
        "New Zealand Visitor Visa 2026 | Requirements, Fees & Application Guide",
        "https://leamss.com/nz/visa/visitor-visa-general",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz visitor visa": (
        "New Zealand Visitor Visa 2026 | Requirements, Fees & Application Guide",
        "https://leamss.com/nz/visa/visitor-visa-general",
        "New Zealand",
        CATEGORY_TR,
    ),
    "visitor visa general": (
        "New Zealand Visitor Visa 2026 | Requirements, Fees & Application Guide",
        "https://leamss.com/nz/visa/visitor-visa-general",
        "New Zealand",
        CATEGORY_TR,
    ),
    "visitor-visa-general": (
        "New Zealand Visitor Visa 2026 | Requirements, Fees & Application Guide",
        "https://leamss.com/nz/visa/visitor-visa-general",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz-visitor-visa-general": (
        "New Zealand Visitor Visa 2026 | Requirements, Fees & Application Guide",
        "https://leamss.com/nz/visa/visitor-visa-general",
        "New Zealand",
        CATEGORY_TR,
    ),
    "new zealand visitor visa": (
        "New Zealand Visitor Visa 2026 | Requirements, Fees & Application Guide",
        "https://leamss.com/nz/visa/visitor-visa-general",
        "New Zealand",
        CATEGORY_TR,
    ),

    "nz transit visa": (
        "New Zealand Transit Visa for Indians 2025 | Requirements, Fee NZD 235 & Apply",
        "https://leamss.com/nz/visa/transit-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "transit visa": (
        "New Zealand Transit Visa for Indians 2025 | Requirements, Fee NZD 235 & Apply",
        "https://leamss.com/nz/visa/transit-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "transit-visa": (
        "New Zealand Transit Visa for Indians 2025 | Requirements, Fee NZD 235 & Apply",
        "https://leamss.com/nz/visa/transit-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "nz-transit-visa": (
        "New Zealand Transit Visa for Indians 2025 | Requirements, Fee NZD 235 & Apply",
        "https://leamss.com/nz/visa/transit-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "new zealand transit visa": (
        "New Zealand Transit Visa for Indians 2025 | Requirements, Fee NZD 235 & Apply",
        "https://leamss.com/nz/visa/transit-visa",
        "New Zealand",
        CATEGORY_TR,
    ),

    # --- NEW ZEALAND MAIN VISA LANDING PAGE ---
    "nz visa": (
        "New Zealand Visa Guide 2026 | PR, Work, Student & Visitor Visa Options",
        "https://leamss.com/newzealand-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "newzealand-visa": (
        "New Zealand Visa Guide 2026 | PR, Work, Student & Visitor Visa Options",
        "https://leamss.com/newzealand-visa",
        "New Zealand",
        CATEGORY_TR,
    ),
    "newzealand visa": (
        "New Zealand Visa Guide 2026 | PR, Work, Student & Visitor Visa Options",
        "https://leamss.com/newzealand-visa",
        "New Zealand",
        CATEGORY_TR,
    ),

    # --- AUSTRALIA SPECIFIC SUBCLASS PAGES ---
    # 1. Subclass 189
    "skilled independent visa subclass 189 australia": (
        "Skilled Independent Visa Subclass 189 Australia 2026 | Points & Guide",
        "https://leamss.com/australia/visa/skilled-independent-visa-subclass-189-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Independent Visa Subclass 189",
    ),
    "skilled-independent-visa-subclass-189-australia": (
        "Skilled Independent Visa Subclass 189 Australia 2026 | Points & Guide",
        "https://leamss.com/australia/visa/skilled-independent-visa-subclass-189-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Independent Visa Subclass 189",
    ),
    "subclass 189": (
        "Skilled Independent Visa Subclass 189 Australia 2026 | Points & Guide",
        "https://leamss.com/australia/visa/skilled-independent-visa-subclass-189-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Independent Visa Subclass 189",
    ),
    "subclass 189 australia": (
        "Skilled Independent Visa Subclass 189 Australia 2026 | Points & Guide",
        "https://leamss.com/australia/visa/skilled-independent-visa-subclass-189-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Independent Visa Subclass 189",
    ),
    "189 visa": (
        "Skilled Independent Visa Subclass 189 Australia 2026 | Points & Guide",
        "https://leamss.com/australia/visa/skilled-independent-visa-subclass-189-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Independent Visa Subclass 189",
    ),

    # 2. Subclass 190
    "skilled nominated visa subclass 190 australia": (
        "Skilled Nominated Visa Subclass 190 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/skilled-nominated-visa-subclass-190-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Nominated Visa Subclass 190",
    ),
    "skilled-nominated-visa-subclass-190-australia": (
        "Skilled Nominated Visa Subclass 190 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/skilled-nominated-visa-subclass-190-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Nominated Visa Subclass 190",
    ),
    "australia skilled nominated visa": (
        "Skilled Nominated Visa Subclass 190 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/skilled-nominated-visa-subclass-190-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Nominated Visa Subclass 190",
    ),
    "subclass 190": (
        "Skilled Nominated Visa Subclass 190 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/skilled-nominated-visa-subclass-190-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Nominated Visa Subclass 190",
    ),
    "subclass 190 australia": (
        "Skilled Nominated Visa Subclass 190 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/skilled-nominated-visa-subclass-190-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Nominated Visa Subclass 190",
    ),
    "190 visa": (
        "Skilled Nominated Visa Subclass 190 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/skilled-nominated-visa-subclass-190-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Nominated Visa Subclass 190",
    ),

    # 3. Subclass 491
    "skilled work regional visa subclass 491 australia": (
        "Skilled Work Regional Visa Subclass 491 Australia 2026 | Guide",
        "https://leamss.com/australia/visa/skilled-work-regional-visa-subclass-491-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Work Regional Visa Subclass 491",
    ),
    "skilled-work-regional-visa-subclass-491-australia": (
        "Skilled Work Regional Visa Subclass 491 Australia 2026 | Guide",
        "https://leamss.com/australia/visa/skilled-work-regional-visa-subclass-491-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Work Regional Visa Subclass 491",
    ),
    "subclass 491": (
        "Skilled Work Regional Visa Subclass 491 Australia 2026 | Guide",
        "https://leamss.com/australia/visa/skilled-work-regional-visa-subclass-491-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Work Regional Visa Subclass 491",
    ),
    "subclass 491 australia": (
        "Skilled Work Regional Visa Subclass 491 Australia 2026 | Guide",
        "https://leamss.com/australia/visa/skilled-work-regional-visa-subclass-491-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Work Regional Visa Subclass 491",
    ),
    "491 visa": (
        "Skilled Work Regional Visa Subclass 491 Australia 2026 | Guide",
        "https://leamss.com/australia/visa/skilled-work-regional-visa-subclass-491-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Skilled Work Regional Visa Subclass 491",
    ),

    # 4. Subclass 186
    "subclass 186 employer nomination scheme visa australia": (
        "Employer Nomination Scheme Visa Subclass 186 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/subclass-186-employer-nomination-scheme-visa-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Employer Nomination Scheme Visa Subclass 186",
    ),
    "subclass-186-employer-nomination-scheme-visa-australia": (
        "Employer Nomination Scheme Visa Subclass 186 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/subclass-186-employer-nomination-scheme-visa-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Employer Nomination Scheme Visa Subclass 186",
    ),
    "subclass 186": (
        "Employer Nomination Scheme Visa Subclass 186 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/subclass-186-employer-nomination-scheme-visa-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Employer Nomination Scheme Visa Subclass 186",
    ),
    "186 visa": (
        "Employer Nomination Scheme Visa Subclass 186 Australia 2026 | PR Guide",
        "https://leamss.com/australia/visa/subclass-186-employer-nomination-scheme-visa-australia",
        "Australia",
        CATEGORY_PR,
        "Australia Employer Nomination Scheme Visa Subclass 186",
    ),

    # 5. Subclass 482
    "australia subclass 482 skills in demand visa": (
        "Australia Subclass 482 Skills in Demand Visa 2026 | Requirements & Guide",
        "https://leamss.com/australia/visa/australia-subclass-482-skills-in-demand-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Skills in Demand Visa Subclass 482",
    ),
    "australia-subclass-482-skills-in-demand-visa": (
        "Australia Subclass 482 Skills in Demand Visa 2026 | Requirements & Guide",
        "https://leamss.com/australia/visa/australia-subclass-482-skills-in-demand-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Skills in Demand Visa Subclass 482",
    ),
    "subclass 482": (
        "Australia Subclass 482 Skills in Demand Visa 2026 | Requirements & Guide",
        "https://leamss.com/australia/visa/australia-subclass-482-skills-in-demand-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Skills in Demand Visa Subclass 482",
    ),
    "482 visa": (
        "Australia Subclass 482 Skills in Demand Visa 2026 | Requirements & Guide",
        "https://leamss.com/australia/visa/australia-subclass-482-skills-in-demand-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Skills in Demand Visa Subclass 482",
    ),

    # 6. Subclass 485
    "subclass 485 temporary graduate visa": (
        "Temporary Graduate Visa Subclass 485 Australia 2026 | Guide",
        "https://leamss.com/australia/visa/subclass-485-temporary-graduate-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Temporary Graduate Visa Subclass 485",
    ),
    "subclass-485-temporary-graduate-visa": (
        "Temporary Graduate Visa Subclass 485 Australia 2026 | Guide",
        "https://leamss.com/australia/visa/subclass-485-temporary-graduate-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Temporary Graduate Visa Subclass 485",
    ),
    "subclass 485": (
        "Temporary Graduate Visa Subclass 485 Australia 2026 | Guide",
        "https://leamss.com/australia/visa/subclass-485-temporary-graduate-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Temporary Graduate Visa Subclass 485",
    ),
    "485 visa": (
        "Temporary Graduate Visa Subclass 485 Australia 2026 | Guide",
        "https://leamss.com/australia/visa/subclass-485-temporary-graduate-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Temporary Graduate Visa Subclass 485",
    ),

    # 7. Subclass 500
    "australia student visa subclass 500": (
        "Australia Student Visa Subclass 500 2026 | Fees, Requirements & Process",
        "https://leamss.com/australia/visa/australia-student-visa-subclass-500",
        "Australia",
        CATEGORY_TR,
        "Australia Student Visa Subclass 500",
    ),
    "australia-student-visa-subclass-500": (
        "Australia Student Visa Subclass 500 2026 | Fees, Requirements & Process",
        "https://leamss.com/australia/visa/australia-student-visa-subclass-500",
        "Australia",
        CATEGORY_TR,
        "Australia Student Visa Subclass 500",
    ),
    "subclass 500": (
        "Australia Student Visa Subclass 500 2026 | Fees, Requirements & Process",
        "https://leamss.com/australia/visa/australia-student-visa-subclass-500",
        "Australia",
        CATEGORY_TR,
        "Australia Student Visa Subclass 500",
    ),
    "500 visa": (
        "Australia Student Visa Subclass 500 2026 | Fees, Requirements & Process",
        "https://leamss.com/australia/visa/australia-student-visa-subclass-500",
        "Australia",
        CATEGORY_TR,
        "Australia Student Visa Subclass 500",
    ),

    # 8. Subclass 600
    "australia visitor visa subclass 600": (
        "Australia Visitor Visa Subclass 600 2026 | Tourist Stream Requirements",
        "https://leamss.com/australia/visa/australia-visitor-visa-subclass-600",
        "Australia",
        CATEGORY_TR,
        "Australia Visitor Visa Subclass 600",
    ),
    "australia-visitor-visa-subclass-600": (
        "Australia Visitor Visa Subclass 600 2026 | Tourist Stream Requirements",
        "https://leamss.com/australia/visa/australia-visitor-visa-subclass-600",
        "Australia",
        CATEGORY_TR,
        "Australia Visitor Visa Subclass 600",
    ),
    "subclass 600": (
        "Australia Visitor Visa Subclass 600 2026 | Tourist Stream Requirements",
        "https://leamss.com/australia/visa/australia-visitor-visa-subclass-600",
        "Australia",
        CATEGORY_TR,
        "Australia Visitor Visa Subclass 600",
    ),
    "600 visa": (
        "Australia Visitor Visa Subclass 600 2026 | Tourist Stream Requirements",
        "https://leamss.com/australia/visa/australia-visitor-visa-subclass-600",
        "Australia",
        CATEGORY_TR,
        "Australia Visitor Visa Subclass 600",
    ),

    # 9. Subclass 400
    "australia-subclass-400-visa": (
        "Australia 400 Work Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-400-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Short Stay Specialist Visa Subclass 400",
    ),
    "australia subclass 400 visa": (
        "Australia 400 Work Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-400-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Short Stay Specialist Visa Subclass 400",
    ),
    "australia temporary work visa": (
        "Australia 400 Work Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-400-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Short Stay Specialist Visa Subclass 400",
    ),
    "subclass 400": (
        "Australia 400 Work Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-400-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Short Stay Specialist Visa Subclass 400",
    ),
    "subclass 400 temporary work short stay specialist visa": (
        "Australia 400 Work Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-400-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Short Stay Specialist Visa Subclass 400",
    ),
    "subclass-400-temporary-work-short-stay-specialist-visa": (
        "Australia 400 Work Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-400-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Short Stay Specialist Visa Subclass 400",
    ),
    "400 visa": (
        "Australia 400 Work Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-400-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Short Stay Specialist Visa Subclass 400",
    ),

    # 10. Subclass 462
    "australia-subclass-462-work-and-holiday-visa": (
        "Australia 462 Work and Holiday Visa India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-462-work-and-holiday-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Work and Holiday Visa Subclass 462",
    ),
    "australia subclass 462 work and holiday visa": (
        "Australia 462 Work and Holiday Visa India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-462-work-and-holiday-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Work and Holiday Visa Subclass 462",
    ),
    "australia work and holiday visa": (
        "Australia 462 Work and Holiday Visa India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-462-work-and-holiday-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Work and Holiday Visa Subclass 462",
    ),
    "subclass 462": (
        "Australia 462 Work and Holiday Visa India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-462-work-and-holiday-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Work and Holiday Visa Subclass 462",
    ),
    "subclass 462 work and holiday visa australia": (
        "Australia 462 Work and Holiday Visa India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-462-work-and-holiday-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Work and Holiday Visa Subclass 462",
    ),
    "subclass-462-work-and-holiday-visa-australia": (
        "Australia 462 Work and Holiday Visa India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-462-work-and-holiday-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Work and Holiday Visa Subclass 462",
    ),
    "462 visa": (
        "Australia 462 Work and Holiday Visa India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-462-work-and-holiday-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Work and Holiday Visa Subclass 462",
    ),

    # 11. Subclass 820 (Onshore Temporary)
    "australia-subclass-820-partner-visa-onshore": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "australia subclass 820 partner visa onshore": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "australia partner (temporary) visa": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "australia partner temporary visa": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "partner (temporary) visa": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "partner temporary visa": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "subclass 820": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "subclass 820 visa": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "subclass 820 partner visa": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "820 visa": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "subclass-820-801-partner-visa-onshore-australia": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),
    "subclass 820 801 partner visa onshore australia": (
        "Australia 820 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-820-partner-visa-onshore",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 820",
    ),

    # 12. Subclass 801 (Onshore Permanent)
    "australia-subclass-801-partner-visa-onshore": (
        "Australia 801 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-801-partner-visa-onshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 801",
    ),
    "australia subclass 801 partner visa onshore": (
        "Australia 801 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-801-partner-visa-onshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 801",
    ),
    "australia partner (permanent) visa": (
        "Australia 801 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-801-partner-visa-onshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 801",
    ),
    "australia partner permanent visa": (
        "Australia 801 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-801-partner-visa-onshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 801",
    ),
    "partner (permanent) visa": (
        "Australia 801 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-801-partner-visa-onshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 801",
    ),
    "subclass 801": (
        "Australia 801 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-801-partner-visa-onshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 801",
    ),
    "subclass 801 visa": (
        "Australia 801 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-801-partner-visa-onshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 801",
    ),
    "subclass 801 partner visa": (
        "Australia 801 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-801-partner-visa-onshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 801",
    ),
    "801 visa": (
        "Australia 801 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-subclass-801-partner-visa-onshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 801",
    ),

    # 13. Subclass 309 (Offshore Provisional)
    "partner-visa-subclass-309-offshore-provisional": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),
    "partner visa subclass 309 offshore provisional": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),
    "australia partner visa (provisional) (offshore)": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),
    "australia partner visa provisional offshore": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),
    "australia partner visa (provisional)": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),
    "partner visa (provisional) (offshore)": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),
    "subclass 309": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),
    "subclass 309 visa": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),
    "subclass 309 partner visa": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),
    "309 visa": (
        "Australia 309 Provisional Partner Visa India | LEAMSS",
        "https://leamss.com/australia/visa/partner-visa-subclass-309-offshore-provisional",
        "Australia",
        CATEGORY_TR,
        "Australia Partner Visa Subclass 309",
    ),

    # 14. Subclass 100 (Offshore Permanent)
    "australia-partner-visa-subclass-100-offshore": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "australia partner visa subclass 100 offshore": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "australia partner visa (permanent)": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "australia partner visa permanent": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "partner visa (permanent)": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "partner visa permanent": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "subclass 100": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "subclass 100 visa": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "subclass 100 partner visa": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "100 visa": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "subclass-309-100-partner-visa-offshore-australia": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),
    "subclass 309 100 partner visa offshore australia": (
        "Australia 100 Partner Visa from India | LEAMSS",
        "https://leamss.com/australia/visa/australia-partner-visa-subclass-100-offshore",
        "Australia",
        CATEGORY_PR,
        "Australia Partner Visa Subclass 100",
    ),

    # 13. Australia General Landing Pages
    "australia pr": (
        "Australia PR from India: 189, 190 & 491 Visa Guide",
        "https://leamss.com/immigration/permanent-residency/australia",
        "Australia",
        CATEGORY_PR,
        "Australia PR",
    ),
    "australia-pr": (
        "Australia PR from India: 189, 190 & 491 Visa Guide",
        "https://leamss.com/immigration/permanent-residency/australia",
        "Australia",
        CATEGORY_PR,
        "Australia PR",
    ),
    "australia tr": (
        "Australia Temporary Visas: 482, 500, 600 & 485 Compared",
        "https://leamss.com/immigration/temporary-residency/australia",
        "Australia",
        CATEGORY_TR,
        "Australia TR",
    ),
    "australia-tr": (
        "Australia Temporary Visas: 482, 500, 600 & 485 Compared",
        "https://leamss.com/immigration/temporary-residency/australia",
        "Australia",
        CATEGORY_TR,
        "Australia TR",
    ),
    "australia visa": (
        "Australia Visa for Indians 2026 | Complete Immigration Guide",
        "https://leamss.com/australia-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Visa Guide",
    ),
    "australia-visa": (
        "Australia Visa for Indians 2026 | Complete Immigration Guide",
        "https://leamss.com/australia-visa",
        "Australia",
        CATEGORY_TR,
        "Australia Visa Guide",
    ),

    # --- CANADA SPECIFIC SUBCLASS PAGES ---
    # 1. Canada Express Entry
    "canada express entry system": (
        "Canada Express Entry 2026 | CRS Points, Requirements & Process",
        "https://leamss.com/canada/visa/canada-express-entry-system",
        "Canada",
        CATEGORY_PR,
        "Canada Express Entry System",
    ),
    "australia express entry system": (
        "Canada Express Entry 2026 | CRS Points, Requirements & Process",
        "https://leamss.com/canada/visa/canada-express-entry-system",
        "Canada",
        CATEGORY_PR,
        "Canada Express Entry System",
    ),
    "canada-express-entry-system": (
        "Canada Express Entry 2026 | CRS Points, Requirements & Process",
        "https://leamss.com/canada/visa/canada-express-entry-system",
        "Canada",
        CATEGORY_PR,
        "Canada Express Entry System",
    ),
    "express entry system": (
        "Canada Express Entry 2026 | CRS Points, Requirements & Process",
        "https://leamss.com/canada/visa/canada-express-entry-system",
        "Canada",
        CATEGORY_PR,
        "Canada Express Entry System",
    ),

    # 2. Canada FSWP
    "canada federal skilled worker program": (
        "Canada Federal Skilled Worker Program 2026 | FSWP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-worker-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Worker Program (FSWP)",
    ),
    "australia federal skilled worker program (fswp)": (
        "Canada Federal Skilled Worker Program 2026 | FSWP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-worker-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Worker Program (FSWP)",
    ),
    "australia federal skilled worker program": (
        "Canada Federal Skilled Worker Program 2026 | FSWP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-worker-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Worker Program (FSWP)",
    ),
    "canada-federal-skilled-worker-program": (
        "Canada Federal Skilled Worker Program 2026 | FSWP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-worker-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Worker Program (FSWP)",
    ),
    "fswp": (
        "Canada Federal Skilled Worker Program 2026 | FSWP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-worker-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Worker Program (FSWP)",
    ),

    # 3. Canada FSTP
    "canada federal skilled trades program": (
        "Canada Federal Skilled Trades Program 2026 | FSTP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-trades-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Trades Program (FSTP)",
    ),
    "australia federal skilled trades program (fstp)": (
        "Canada Federal Skilled Trades Program 2026 | FSTP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-trades-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Trades Program (FSTP)",
    ),
    "australia federal skilled trades program": (
        "Canada Federal Skilled Trades Program 2026 | FSTP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-trades-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Trades Program (FSTP)",
    ),
    "canada-federal-skilled-trades-program": (
        "Canada Federal Skilled Trades Program 2026 | FSTP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-trades-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Trades Program (FSTP)",
    ),
    "fstp": (
        "Canada Federal Skilled Trades Program 2026 | FSTP Guide",
        "https://leamss.com/canada/visa/canada-federal-skilled-trades-program",
        "Canada",
        CATEGORY_PR,
        "Canada Federal Skilled Trades Program (FSTP)",
    ),

    # 4. Canada CEC
    "canada canadian experience class": (
        "Canadian Experience Class 2026 | CEC Requirements & Process",
        "https://leamss.com/canada/visa/canada-canadian-experience-class",
        "Canada",
        CATEGORY_PR,
        "Canada Canadian Experience Class (CEC)",
    ),
    "australia canadian experience class (cec)": (
        "Canadian Experience Class 2026 | CEC Requirements & Process",
        "https://leamss.com/canada/visa/canada-canadian-experience-class",
        "Canada",
        CATEGORY_PR,
        "Canada Canadian Experience Class (CEC)",
    ),
    "australia canadian experience class": (
        "Canadian Experience Class 2026 | CEC Requirements & Process",
        "https://leamss.com/canada/visa/canada-canadian-experience-class",
        "Canada",
        CATEGORY_PR,
        "Canada Canadian Experience Class (CEC)",
    ),
    "canada-canadian-experience-class": (
        "Canadian Experience Class 2026 | CEC Requirements & Process",
        "https://leamss.com/canada/visa/canada-canadian-experience-class",
        "Canada",
        CATEGORY_PR,
        "Canada Canadian Experience Class (CEC)",
    ),
    "cec": (
        "Canadian Experience Class 2026 | CEC Requirements & Process",
        "https://leamss.com/canada/visa/canada-canadian-experience-class",
        "Canada",
        CATEGORY_PR,
        "Canada Canadian Experience Class (CEC)",
    ),
    "canadian experience class": (
        "Canadian Experience Class 2026 | CEC Requirements & Process",
        "https://leamss.com/canada/visa/canada-canadian-experience-class",
        "Canada",
        CATEGORY_PR,
        "Canada Canadian Experience Class (CEC)",
    ),

    # 5. Canada OINP
    "ontario immigrant nominee program": (
        "Ontario Immigrant Nominee Program 2026 | OINP Streams & CRS",
        "https://leamss.com/canada/visa/ontario-immigrant-nominee-program",
        "Canada",
        CATEGORY_PR,
        "Ontario Immigrant Nominee Program (OINP)",
    ),
    "australia ontario immigrant nominee program (oinp)": (
        "Ontario Immigrant Nominee Program 2026 | OINP Streams & CRS",
        "https://leamss.com/canada/visa/ontario-immigrant-nominee-program",
        "Canada",
        CATEGORY_PR,
        "Ontario Immigrant Nominee Program (OINP)",
    ),
    "australia ontario immigrant nominee program": (
        "Ontario Immigrant Nominee Program 2026 | OINP Streams & CRS",
        "https://leamss.com/canada/visa/ontario-immigrant-nominee-program",
        "Canada",
        CATEGORY_PR,
        "Ontario Immigrant Nominee Program (OINP)",
    ),
    "ontario-immigrant-nominee-program": (
        "Ontario Immigrant Nominee Program 2026 | OINP Streams & CRS",
        "https://leamss.com/canada/visa/ontario-immigrant-nominee-program",
        "Canada",
        CATEGORY_PR,
        "Ontario Immigrant Nominee Program (OINP)",
    ),
    "oinp": (
        "Ontario Immigrant Nominee Program 2026 | OINP Streams & CRS",
        "https://leamss.com/canada/visa/ontario-immigrant-nominee-program",
        "Canada",
        CATEGORY_PR,
        "Ontario Immigrant Nominee Program (OINP)",
    ),

    # 6. Canada Open Work Permit
    "canada open work permit": (
        "Canada Open Work Permit 2026 | Eligibility, Fees & Processing Time",
        "https://leamss.com/canada/visa/canada-open-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Open Work Permit",
    ),
    "australia open work permit": (
        "Canada Open Work Permit 2026 | Eligibility, Fees & Processing Time",
        "https://leamss.com/canada/visa/canada-open-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Open Work Permit",
    ),
    "canada-open-work-permit": (
        "Canada Open Work Permit 2026 | Eligibility, Fees & Processing Time",
        "https://leamss.com/canada/visa/canada-open-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Open Work Permit",
    ),
    "open work permit": (
        "Canada Open Work Permit 2026 | Eligibility, Fees & Processing Time",
        "https://leamss.com/canada/visa/canada-open-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Open Work Permit",
    ),

    # 7. Canada Employer Specific Work Permit
    "canada employer specific work permit": (
        "Employer-Specific Work Permit Canada 2026 | Closed Work Permit Guide",
        "https://leamss.com/canada/visa/canada-employer-specific-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Employer-Specific Work Permit",
    ),
    "australia employer-specific work permit": (
        "Employer-Specific Work Permit Canada 2026 | Closed Work Permit Guide",
        "https://leamss.com/canada/visa/canada-employer-specific-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Employer-Specific Work Permit",
    ),
    "australia employer specific work permit": (
        "Employer-Specific Work Permit Canada 2026 | Closed Work Permit Guide",
        "https://leamss.com/canada/visa/canada-employer-specific-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Employer-Specific Work Permit",
    ),
    "canada-employer-specific-work-permit": (
        "Employer-Specific Work Permit Canada 2026 | Closed Work Permit Guide",
        "https://leamss.com/canada/visa/canada-employer-specific-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Employer-Specific Work Permit",
    ),
    "employer-specific work permit": (
        "Employer-Specific Work Permit Canada 2026 | Closed Work Permit Guide",
        "https://leamss.com/canada/visa/canada-employer-specific-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Employer-Specific Work Permit",
    ),
    "closed work permit": (
        "Employer-Specific Work Permit Canada 2026 | Closed Work Permit Guide",
        "https://leamss.com/canada/visa/canada-employer-specific-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Employer-Specific Work Permit",
    ),

    # 8. Canada PGWP
    "canada post graduation work permit": (
        "Post-Graduation Work Permit Canada 2026 | PGWP Rules & Application",
        "https://leamss.com/canada/visa/canada-post-graduation-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Post-Graduation Work Permit (PGWP)",
    ),
    "australia post-graduation work permit (pgwp)": (
        "Post-Graduation Work Permit Canada 2026 | PGWP Rules & Application",
        "https://leamss.com/canada/visa/canada-post-graduation-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Post-Graduation Work Permit (PGWP)",
    ),
    "australia post graduation work permit": (
        "Post-Graduation Work Permit Canada 2026 | PGWP Rules & Application",
        "https://leamss.com/canada/visa/canada-post-graduation-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Post-Graduation Work Permit (PGWP)",
    ),
    "canada-post-graduation-work-permit": (
        "Post-Graduation Work Permit Canada 2026 | PGWP Rules & Application",
        "https://leamss.com/canada/visa/canada-post-graduation-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Post-Graduation Work Permit (PGWP)",
    ),
    "pgwp": (
        "Post-Graduation Work Permit Canada 2026 | PGWP Rules & Application",
        "https://leamss.com/canada/visa/canada-post-graduation-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Post-Graduation Work Permit (PGWP)",
    ),
    "canada pgwp": (
        "Post-Graduation Work Permit Canada 2026 | PGWP Rules & Application",
        "https://leamss.com/canada/visa/canada-post-graduation-work-permit",
        "Canada",
        CATEGORY_TR,
        "Canada Post-Graduation Work Permit (PGWP)",
    ),

    # 9. Canada SDS Study Permit
    "canada fast track study permit sds": (
        "Student Direct Stream Canada 2026 | SDS Study Permit for Indians",
        "https://leamss.com/canada/visa/canada-fast-track-study-permit-sds",
        "Canada",
        CATEGORY_TR,
        "Canada Student Direct Stream (SDS)",
    ),
    "canada-fast-track-study-permit-sds": (
        "Student Direct Stream Canada 2026 | SDS Study Permit for Indians",
        "https://leamss.com/canada/visa/canada-fast-track-study-permit-sds",
        "Canada",
        CATEGORY_TR,
        "Canada Student Direct Stream (SDS)",
    ),
    "sds": (
        "Student Direct Stream Canada 2026 | SDS Study Permit for Indians",
        "https://leamss.com/canada/visa/canada-fast-track-study-permit-sds",
        "Canada",
        CATEGORY_TR,
        "Canada Student Direct Stream (SDS)",
    ),

    # 10. Canada Non-SDS Study Permit
    "canada regular study permit non sds": (
        "Canada Study Permit 2026 | Non-SDS Student Visa Requirements",
        "https://leamss.com/canada/visa/canada-regular-study-permit-non-sds",
        "Canada",
        CATEGORY_TR,
        "Canada Regular Study Permit (Non-SDS)",
    ),
    "canada-regular-study-permit-non-sds": (
        "Canada Study Permit 2026 | Non-SDS Student Visa Requirements",
        "https://leamss.com/canada/visa/canada-regular-study-permit-non-sds",
        "Canada",
        CATEGORY_TR,
        "Canada Regular Study Permit (Non-SDS)",
    ),
    "non-sds": (
        "Canada Study Permit 2026 | Non-SDS Student Visa Requirements",
        "https://leamss.com/canada/visa/canada-regular-study-permit-non-sds",
        "Canada",
        CATEGORY_TR,
        "Canada Regular Study Permit (Non-SDS)",
    ),

    # 11. Canada Business Visitor
    "canada business visitor visa": (
        "Canada Business Visitor Visa 2026 | Requirements & Application Process",
        "https://leamss.com/canada/visa/canada-business-visitor-visa",
        "Canada",
        CATEGORY_TR,
        "Canada Business Visitor Visa",
    ),
    "canada-business-visitor-visa": (
        "Canada Business Visitor Visa 2026 | Requirements & Application Process",
        "https://leamss.com/canada/visa/canada-business-visitor-visa",
        "Canada",
        CATEGORY_TR,
        "Canada Business Visitor Visa",
    ),

    # 12. Canada Super Visa
    "canada super visa for parents grandparents": (
        "Canada Super Visa for Parents & Grandparents 2026 | Guide & Insurance",
        "https://leamss.com/canada/visa/canada-super-visa-for-parents-grandparents",
        "Canada",
        CATEGORY_TR,
        "Canada Super Visa for Parents & Grandparents",
    ),
    "canada-super-visa-for-parents-grandparents": (
        "Canada Super Visa for Parents & Grandparents 2026 | Guide & Insurance",
        "https://leamss.com/canada/visa/canada-super-visa-for-parents-grandparents",
        "Canada",
        CATEGORY_TR,
        "Canada Super Visa for Parents & Grandparents",
    ),
    "super visa": (
        "Canada Super Visa for Parents & Grandparents 2026 | Guide & Insurance",
        "https://leamss.com/canada/visa/canada-super-visa-for-parents-grandparents",
        "Canada",
        CATEGORY_TR,
        "Canada Super Visa for Parents & Grandparents",
    ),

    # 13. Canada Spousal Sponsorship
    "canada spousal sponsorship": (
        "Canada Spousal Sponsorship 2026 | Sponsor Spouse or Partner Guide",
        "https://leamss.com/canada/visa/canada-spousal-sponsorship",
        "Canada",
        CATEGORY_PR,
        "Canada Spousal Sponsorship",
    ),
    "canada-spousal-sponsorship": (
        "Canada Spousal Sponsorship 2026 | Sponsor Spouse or Partner Guide",
        "https://leamss.com/canada/visa/canada-spousal-sponsorship",
        "Canada",
        CATEGORY_PR,
        "Canada Spousal Sponsorship",
    ),

    # 14. Canada Dependent Child Sponsorship
    "canada dependent child sponsorship": (
        "Dependent Child Sponsorship Canada 2026 | Requirements & Process",
        "https://leamss.com/canada/visa/canada-dependent-child-sponsorship",
        "Canada",
        CATEGORY_PR,
        "Canada Dependent Child Sponsorship",
    ),
    "canada-dependent-child-sponsorship": (
        "Dependent Child Sponsorship Canada 2026 | Requirements & Process",
        "https://leamss.com/canada/visa/canada-dependent-child-sponsorship",
        "Canada",
        CATEGORY_PR,
        "Canada Dependent Child Sponsorship",
    ),

    # 15. Canada PGP
    "canada parents and grandparents program": (
        "Parents and Grandparents Program Canada 2026 | PGP PR Sponsorship",
        "https://leamss.com/canada/visa/canada-parents-and-grandparents-program",
        "Canada",
        CATEGORY_PR,
        "Canada Parents & Grandparents Program (PGP)",
    ),
    "canada-parents-and-grandparents-program": (
        "Parents and Grandparents Program Canada 2026 | PGP PR Sponsorship",
        "https://leamss.com/canada/visa/canada-parents-and-grandparents-program",
        "Canada",
        CATEGORY_PR,
        "Canada Parents & Grandparents Program (PGP)",
    ),
    "pgp": (
        "Parents and Grandparents Program Canada 2026 | PGP PR Sponsorship",
        "https://leamss.com/canada/visa/canada-parents-and-grandparents-program",
        "Canada",
        CATEGORY_PR,
        "Canada Parents & Grandparents Program (PGP)",
    ),

    # 16. Canada Start-up Visa
    "canada startup visa program": (
        "Canada Start-up Visa Program 2026 | Requirements, Designated Entities & PR",
        "https://leamss.com/canada/visa/canada-startup-visa-program",
        "Canada",
        CATEGORY_PR,
        "Canada Start-up Visa Program",
    ),
    "canada-startup-visa-program": (
        "Canada Start-up Visa Program 2026 | Requirements, Designated Entities & PR",
        "https://leamss.com/canada/visa/canada-startup-visa-program",
        "Canada",
        CATEGORY_PR,
        "Canada Start-up Visa Program",
    ),
    "startup visa": (
        "Canada Start-up Visa Program 2026 | Requirements, Designated Entities & PR",
        "https://leamss.com/canada/visa/canada-startup-visa-program",
        "Canada",
        CATEGORY_PR,
        "Canada Start-up Visa Program",
    ),

    # 17. Canada Self-Employed
    "canada self employed persons program": (
        "Self-Employed Persons Program Canada 2026 | Cultural & Athletic PR",
        "https://leamss.com/canada/visa/canada-self-employed-persons-program",
        "Canada",
        CATEGORY_PR,
        "Canada Self-Employed Persons Program",
    ),
    "canada-self-employed-persons-program": (
        "Self-Employed Persons Program Canada 2026 | Cultural & Athletic PR",
        "https://leamss.com/canada/visa/canada-self-employed-persons-program",
        "Canada",
        CATEGORY_PR,
        "Canada Self-Employed Persons Program",
    ),

    # 18. Canada Provincial Entrepreneur
    "canada provincial entrepreneur programs": (
        "Provincial Entrepreneur Programs Canada 2026 | PNP Business PR",
        "https://leamss.com/canada/visa/canada-provincial-entrepreneur-programs",
        "Canada",
        CATEGORY_PR,
        "Canada Provincial Entrepreneur Programs",
    ),
    "canada-provincial-entrepreneur-programs": (
        "Provincial Entrepreneur Programs Canada 2026 | PNP Business PR",
        "https://leamss.com/canada/visa/canada-provincial-entrepreneur-programs",
        "Canada",
        CATEGORY_PR,
        "Canada Provincial Entrepreneur Programs",
    ),

    # 19. Canada Family Visit Visa
    "canada family visit visa": (
        "Canada Family Visit Visa 2026 | Requirements, Documents & Apply",
        "https://leamss.com/canada/visa/canada-family-visit-visa",
        "Canada",
        CATEGORY_TR,
        "Canada Family Visit Visa",
    ),
    "canada-family-visit-visa": (
        "Canada Family Visit Visa 2026 | Requirements, Documents & Apply",
        "https://leamss.com/canada/visa/canada-family-visit-visa",
        "Canada",
        CATEGORY_TR,
        "Canada Family Visit Visa",
    ),

    # 20. Canada Transit Visa
    "canada transit visa": (
        "Canada Transit Visa for Indians 2026 | Requirements & Free Online Application",
        "https://leamss.com/canada/visa/canada-transit-visa",
        "Canada",
        CATEGORY_TR,
        "Canada Transit Visa",
    ),
    "canada-transit-visa": (
        "Canada Transit Visa for Indians 2026 | Requirements & Free Online Application",
        "https://leamss.com/canada/visa/canada-transit-visa",
        "Canada",
        CATEGORY_TR,
        "Canada Transit Visa",
    ),

    # 21. Canada Landing Page
    "canada visa": (
        "Canada Visa for Indians 2026 | Complete Immigration Guide",
        "https://leamss.com/canada-visa",
        "Canada",
        CATEGORY_TR,
        "Canada Visa Guide",
    ),
    "canada-visa": (
        "Canada Visa for Indians 2026 | Complete Immigration Guide",
        "https://leamss.com/canada-visa",
        "Canada",
        CATEGORY_TR,
        "Canada Visa Guide",
    ),
    "canada pr": (
        "Canada PR from India: Express Entry, PNP & CRS Guide.",
        "https://leamss.com/immigration/permanent-residency/canada",
        "Canada",
        CATEGORY_PR,
        "Canada PR",
    ),
    "canada-pr": (
        "Canada PR from India: Express Entry, PNP & CRS Guide.",
        "https://leamss.com/immigration/permanent-residency/canada",
        "Canada",
        CATEGORY_PR,
        "Canada PR",
    ),
    "canada express entry": (
        "Canada PR from India: Express Entry, PNP & CRS Guide.",
        "https://leamss.com/immigration/permanent-residency/canada",
        "Canada",
        CATEGORY_PR,
        "Canada PR",
    ),
    "express entry": (
        "Canada PR from India: Express Entry, PNP & CRS Guide.",
        "https://leamss.com/immigration/permanent-residency/canada",
        "Canada",
        CATEGORY_PR,
        "Canada PR",
    ),
    "canada pnp": (
        "Canada PR from India: Express Entry, PNP & CRS Guide.",
        "https://leamss.com/immigration/permanent-residency/canada",
        "Canada",
        CATEGORY_PR,
        "Canada PR",
    ),
    "pnp": (
        "Canada PR from India: Express Entry, PNP & CRS Guide.",
        "https://leamss.com/immigration/permanent-residency/canada",
        "Canada",
        CATEGORY_PR,
        "Canada PR",
    ),
    "canada tr": (
        "Canada Temporary Resident Visa: Work, Study, Visit",
        "https://leamss.com/immigration/temporary-residency/canada",
        "Canada",
        CATEGORY_TR,
        "Canada TR",
    ),
    "canada-tr": (
        "Canada Temporary Resident Visa: Work, Study, Visit",
        "https://leamss.com/immigration/temporary-residency/canada",
        "Canada",
        CATEGORY_TR,
        "Canada TR",
    ),
    "canada work permit": (
        "Canada Temporary Resident Visa: Work, Study, Visit",
        "https://leamss.com/immigration/temporary-residency/canada",
        "Canada",
        CATEGORY_TR,
        "Canada TR",
    ),
    "canada visitor visa": (
        "Canada Temporary Resident Visa: Work, Study, Visit",
        "https://leamss.com/immigration/temporary-residency/canada",
        "Canada",
        CATEGORY_TR,
        "Canada TR",
    ),
    "canada tourist visa": (
        "Canada Temporary Resident Visa: Work, Study, Visit",
        "https://leamss.com/immigration/temporary-residency/canada",
        "Canada",
        CATEGORY_TR,
        "Canada TR",
    ),

    # --- USA SPECIFIC SUBCLASS PAGES ---
    # 1. USA O1 Visa
    "usa o1 extraordinary ability visa": (
        "USA O1 Extraordinary Ability Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-o1-extraordinary-ability-visa",
        "United States",
        CATEGORY_TR,
        "USA O1 Extraordinary Ability Visa",
    ),
    "usa o1 extraordinary ability": (
        "USA O1 Extraordinary Ability Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-o1-extraordinary-ability-visa",
        "United States",
        CATEGORY_TR,
        "USA O1 Extraordinary Ability Visa",
    ),
    "australia o1 extraordinary ability": (
        "USA O1 Extraordinary Ability Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-o1-extraordinary-ability-visa",
        "United States",
        CATEGORY_TR,
        "USA O1 Extraordinary Ability Visa",
    ),
    "o1 extraordinary ability": (
        "USA O1 Extraordinary Ability Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-o1-extraordinary-ability-visa",
        "United States",
        CATEGORY_TR,
        "USA O1 Extraordinary Ability Visa",
    ),
    "o1 extraordinary ability visa": (
        "USA O1 Extraordinary Ability Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-o1-extraordinary-ability-visa",
        "United States",
        CATEGORY_TR,
        "USA O1 Extraordinary Ability Visa",
    ),
    "usa-o1-extraordinary-ability-visa": (
        "USA O1 Extraordinary Ability Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-o1-extraordinary-ability-visa",
        "United States",
        CATEGORY_TR,
        "USA O1 Extraordinary Ability Visa",
    ),
    "o1-extraordinary-ability-visa": (
        "USA O1 Extraordinary Ability Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-o1-extraordinary-ability-visa",
        "United States",
        CATEGORY_TR,
        "USA O1 Extraordinary Ability Visa",
    ),
    "o1 visa": (
        "USA O1 Extraordinary Ability Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-o1-extraordinary-ability-visa",
        "United States",
        CATEGORY_TR,
        "USA O1 Extraordinary Ability Visa",
    ),
    "o1": (
        "USA O1 Extraordinary Ability Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-o1-extraordinary-ability-visa",
        "United States",
        CATEGORY_TR,
        "USA O1 Extraordinary Ability Visa",
    ),

    # 2. USA EB1 Visa
    "usa eb1 priority workers green card visa": (
        "USA EB1 Priority Workers Green Card for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb1-priority-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB1 Priority Workers Green Card",
    ),
    "usa eb1 priority workers": (
        "USA EB1 Priority Workers Green Card for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb1-priority-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB1 Priority Workers Green Card",
    ),
    "australia eb1 priority workers": (
        "USA EB1 Priority Workers Green Card for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb1-priority-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB1 Priority Workers Green Card",
    ),
    "eb1 priority workers": (
        "USA EB1 Priority Workers Green Card for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb1-priority-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB1 Priority Workers Green Card",
    ),
    "usa-eb1-priority-workers-visa": (
        "USA EB1 Priority Workers Green Card for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb1-priority-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB1 Priority Workers Green Card",
    ),
    "eb1 visa": (
        "USA EB1 Priority Workers Green Card for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb1-priority-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB1 Priority Workers Green Card",
    ),
    "eb1": (
        "USA EB1 Priority Workers Green Card for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb1-priority-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB1 Priority Workers Green Card",
    ),
    "eb-1": (
        "USA EB1 Priority Workers Green Card for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb1-priority-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB1 Priority Workers Green Card",
    ),

    # 3. USA EB2 Visa
    "usa eb-2 green card visa": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),
    "usa eb2 advanced degree professionals exceptional ability visa": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),
    "australia eb-2 advanced degree professionals & exceptional ability": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),
    "australia eb2 advanced degree professionals & exceptional ability": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),
    "eb-2 advanced degree professionals & exceptional ability": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),
    "eb2 advanced degree professionals": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),
    "usa-eb2-advanced-degree-professionals-exceptional-ability-visa": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),
    "eb-2 visa": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),
    "eb2 visa": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),
    "eb2": (
        "USA EB-2 Green Card Visa for Indians 2026 | Advanced Degree Professionals",
        "https://leamss.com/usa/visa/usa-eb2-advanced-degree-professionals-exceptional-ability-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-2 Green Card Visa",
    ),

    # 4. USA EB3 Visa
    "usa eb-3 green card visa": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),
    "usa eb3 skilled workers professionals unskilled workers visa": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),
    "australia eb-3 skilled workers, professionals & other workers visa": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),
    "australia eb3 skilled workers professionals other workers visa": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),
    "eb-3 skilled workers": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),
    "eb3 skilled workers": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),
    "usa-eb3-skilled-workers-professionals-unskilled-workers-visa": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),
    "eb-3 visa": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),
    "eb3 visa": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),
    "eb3": (
        "USA EB-3 Green Card Visa for Indians 2026 | Skilled Workers & Professionals",
        "https://leamss.com/usa/visa/usa-eb3-skilled-workers-professionals-unskilled-workers-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-3 Green Card Visa",
    ),

    # 5. USA EB4 Visa
    "usa eb-4 special immigrants visa": (
        "USA EB-4 Special Immigrants Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb4-special-immigrants-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-4 Special Immigrants Visa",
    ),
    "usa eb4 special immigrants visa": (
        "USA EB-4 Special Immigrants Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb4-special-immigrants-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-4 Special Immigrants Visa",
    ),
    "australia eb-4 special immigrants visa": (
        "USA EB-4 Special Immigrants Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb4-special-immigrants-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-4 Special Immigrants Visa",
    ),
    "australia eb4 special immigrants visa": (
        "USA EB-4 Special Immigrants Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb4-special-immigrants-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-4 Special Immigrants Visa",
    ),
    "eb-4 special immigrants visa": (
        "USA EB-4 Special Immigrants Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb4-special-immigrants-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-4 Special Immigrants Visa",
    ),
    "usa-eb4-special-immigrants-visa": (
        "USA EB-4 Special Immigrants Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb4-special-immigrants-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-4 Special Immigrants Visa",
    ),
    "eb-4 visa": (
        "USA EB-4 Special Immigrants Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb4-special-immigrants-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-4 Special Immigrants Visa",
    ),
    "eb4 visa": (
        "USA EB-4 Special Immigrants Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb4-special-immigrants-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-4 Special Immigrants Visa",
    ),
    "eb4": (
        "USA EB-4 Special Immigrants Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-eb4-special-immigrants-visa",
        "United States",
        CATEGORY_PR,
        "USA EB-4 Special Immigrants Visa",
    ),

    # 6. USA EB5 Visa
    "usa eb-5 immigrant investor program": (
        "EB-5 Immigrant Investor Program USA – Investment Green Card Visa Guide",
        "https://leamss.com/usa/visa/eb-5-immigrant-investor-program",
        "United States",
        CATEGORY_PR,
        "USA EB-5 Immigrant Investor Program",
    ),
    "usa eb5 immigrant investor program": (
        "EB-5 Immigrant Investor Program USA – Investment Green Card Visa Guide",
        "https://leamss.com/usa/visa/eb-5-immigrant-investor-program",
        "United States",
        CATEGORY_PR,
        "USA EB-5 Immigrant Investor Program",
    ),
    "australia eb-5 immigrant investor program": (
        "EB-5 Immigrant Investor Program USA – Investment Green Card Visa Guide",
        "https://leamss.com/usa/visa/eb-5-immigrant-investor-program",
        "United States",
        CATEGORY_PR,
        "USA EB-5 Immigrant Investor Program",
    ),
    "australia eb5 immigrant investor program": (
        "EB-5 Immigrant Investor Program USA – Investment Green Card Visa Guide",
        "https://leamss.com/usa/visa/eb-5-immigrant-investor-program",
        "United States",
        CATEGORY_PR,
        "USA EB-5 Immigrant Investor Program",
    ),
    "eb-5 immigrant investor program": (
        "EB-5 Immigrant Investor Program USA – Investment Green Card Visa Guide",
        "https://leamss.com/usa/visa/eb-5-immigrant-investor-program",
        "United States",
        CATEGORY_PR,
        "USA EB-5 Immigrant Investor Program",
    ),
    "eb-5-immigrant-investor-program": (
        "EB-5 Immigrant Investor Program USA – Investment Green Card Visa Guide",
        "https://leamss.com/usa/visa/eb-5-immigrant-investor-program",
        "United States",
        CATEGORY_PR,
        "USA EB-5 Immigrant Investor Program",
    ),
    "eb-5 visa": (
        "EB-5 Immigrant Investor Program USA – Investment Green Card Visa Guide",
        "https://leamss.com/usa/visa/eb-5-immigrant-investor-program",
        "United States",
        CATEGORY_PR,
        "USA EB-5 Immigrant Investor Program",
    ),
    "eb5 visa": (
        "EB-5 Immigrant Investor Program USA – Investment Green Card Visa Guide",
        "https://leamss.com/usa/visa/eb-5-immigrant-investor-program",
        "United States",
        CATEGORY_PR,
        "USA EB-5 Immigrant Investor Program",
    ),
    "eb5": (
        "EB-5 Immigrant Investor Program USA – Investment Green Card Visa Guide",
        "https://leamss.com/usa/visa/eb-5-immigrant-investor-program",
        "United States",
        CATEGORY_PR,
        "USA EB-5 Immigrant Investor Program",
    ),

    # 7. USA H1B Visa
    "usa h1b work visa": (
        "USA H1B Work Visa for Indians 2026 | Skilled Worker Visa USA",
        "https://leamss.com/usa/visa/usa-h1b-specialty-occupation-work-visa",
        "United States",
        CATEGORY_TR,
        "USA H1B Work Visa",
    ),
    "usa h1b specialty occupation work visa": (
        "USA H1B Work Visa for Indians 2026 | Skilled Worker Visa USA",
        "https://leamss.com/usa/visa/usa-h1b-specialty-occupation-work-visa",
        "United States",
        CATEGORY_TR,
        "USA H1B Work Visa",
    ),
    "australia h1b specialty occupation visa": (
        "USA H1B Work Visa for Indians 2026 | Skilled Worker Visa USA",
        "https://leamss.com/usa/visa/usa-h1b-specialty-occupation-work-visa",
        "United States",
        CATEGORY_TR,
        "USA H1B Work Visa",
    ),
    "h1b specialty occupation visa": (
        "USA H1B Work Visa for Indians 2026 | Skilled Worker Visa USA",
        "https://leamss.com/usa/visa/usa-h1b-specialty-occupation-work-visa",
        "United States",
        CATEGORY_TR,
        "USA H1B Work Visa",
    ),
    "usa-h1b-specialty-occupation-work-visa": (
        "USA H1B Work Visa for Indians 2026 | Skilled Worker Visa USA",
        "https://leamss.com/usa/visa/usa-h1b-specialty-occupation-work-visa",
        "United States",
        CATEGORY_TR,
        "USA H1B Work Visa",
    ),
    "h1b work visa": (
        "USA H1B Work Visa for Indians 2026 | Skilled Worker Visa USA",
        "https://leamss.com/usa/visa/usa-h1b-specialty-occupation-work-visa",
        "United States",
        CATEGORY_TR,
        "USA H1B Work Visa",
    ),
    "h1b visa": (
        "USA H1B Work Visa for Indians 2026 | Skilled Worker Visa USA",
        "https://leamss.com/usa/visa/usa-h1b-specialty-occupation-work-visa",
        "United States",
        CATEGORY_TR,
        "USA H1B Work Visa",
    ),
    "h1b": (
        "USA H1B Work Visa for Indians 2026 | Skilled Worker Visa USA",
        "https://leamss.com/usa/visa/usa-h1b-specialty-occupation-work-visa",
        "United States",
        CATEGORY_TR,
        "USA H1B Work Visa",
    ),
    "h-1b": (
        "USA H1B Work Visa for Indians 2026 | Skilled Worker Visa USA",
        "https://leamss.com/usa/visa/usa-h1b-specialty-occupation-work-visa",
        "United States",
        CATEGORY_TR,
        "USA H1B Work Visa",
    ),

    # 8. USA H-2B Visa
    "usa h-2b temporary workers visa": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),
    "usa h2b temporary workers visa": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),
    "australia h-2b temporary non-agricultural worker": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),
    "australia h2b temporary non-agricultural worker": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),
    "h-2b temporary non-agricultural worker": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),
    "usa-h2b-temporary-workers-visa": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),
    "h-2b visa": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),
    "h2b visa": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),
    "h-2b": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),
    "h2b": (
        "H-2B Temporary Non-Agricultural Worker – USA Visa | LEAMS",
        "https://leamss.com/usa/visa/usa-h2b-temporary-workers-visa",
        "United States",
        CATEGORY_TR,
        "USA H-2B Temporary Non-Agricultural Worker Visa",
    ),

    # 9. USA L1 Visa
    "usa l1 intracompany transferee visa": (
        "USA L1 Intracompany Transferee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-l1-intracompany-transferee-visa",
        "United States",
        CATEGORY_TR,
        "USA L1 Intracompany Transferee Visa",
    ),
    "usa l1 visa": (
        "USA L1 Intracompany Transferee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-l1-intracompany-transferee-visa",
        "United States",
        CATEGORY_TR,
        "USA L1 Intracompany Transferee Visa",
    ),
    "australia l1 intracompany transferee": (
        "USA L1 Intracompany Transferee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-l1-intracompany-transferee-visa",
        "United States",
        CATEGORY_TR,
        "USA L1 Intracompany Transferee Visa",
    ),
    "l1 intracompany transferee": (
        "USA L1 Intracompany Transferee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-l1-intracompany-transferee-visa",
        "United States",
        CATEGORY_TR,
        "USA L1 Intracompany Transferee Visa",
    ),
    "usa-l1-intracompany-transferee-visa": (
        "USA L1 Intracompany Transferee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-l1-intracompany-transferee-visa",
        "United States",
        CATEGORY_TR,
        "USA L1 Intracompany Transferee Visa",
    ),
    "l1 visa": (
        "USA L1 Intracompany Transferee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-l1-intracompany-transferee-visa",
        "United States",
        CATEGORY_TR,
        "USA L1 Intracompany Transferee Visa",
    ),
    "l-1 visa": (
        "USA L1 Intracompany Transferee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-l1-intracompany-transferee-visa",
        "United States",
        CATEGORY_TR,
        "USA L1 Intracompany Transferee Visa",
    ),
    "l1": (
        "USA L1 Intracompany Transferee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-l1-intracompany-transferee-visa",
        "United States",
        CATEGORY_TR,
        "USA L1 Intracompany Transferee Visa",
    ),
    "l-1": (
        "USA L1 Intracompany Transferee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-l1-intracompany-transferee-visa",
        "United States",
        CATEGORY_TR,
        "USA L1 Intracompany Transferee Visa",
    ),

    # 10. USA F1 Visa
    "usa f1 student visa": (
        "USA F1 Student Visa for Indians 2026 | Study in America",
        "https://leamss.com/usa/visa/usa-f1-student-visa",
        "United States",
        CATEGORY_TR,
        "USA F1 Student Visa",
    ),
    "australia f1 academic student": (
        "USA F1 Student Visa for Indians 2026 | Study in America",
        "https://leamss.com/usa/visa/usa-f1-student-visa",
        "United States",
        CATEGORY_TR,
        "USA F1 Student Visa",
    ),
    "f1 academic student": (
        "USA F1 Student Visa for Indians 2026 | Study in America",
        "https://leamss.com/usa/visa/usa-f1-student-visa",
        "United States",
        CATEGORY_TR,
        "USA F1 Student Visa",
    ),
    "usa-f1-student-visa": (
        "USA F1 Student Visa for Indians 2026 | Study in America",
        "https://leamss.com/usa/visa/usa-f1-student-visa",
        "United States",
        CATEGORY_TR,
        "USA F1 Student Visa",
    ),
    "f1 student visa": (
        "USA F1 Student Visa for Indians 2026 | Study in America",
        "https://leamss.com/usa/visa/usa-f1-student-visa",
        "United States",
        CATEGORY_TR,
        "USA F1 Student Visa",
    ),
    "f1 visa": (
        "USA F1 Student Visa for Indians 2026 | Study in America",
        "https://leamss.com/usa/visa/usa-f1-student-visa",
        "United States",
        CATEGORY_TR,
        "USA F1 Student Visa",
    ),
    "f-1 visa": (
        "USA F1 Student Visa for Indians 2026 | Study in America",
        "https://leamss.com/usa/visa/usa-f1-student-visa",
        "United States",
        CATEGORY_TR,
        "USA F1 Student Visa",
    ),
    "f1": (
        "USA F1 Student Visa for Indians 2026 | Study in America",
        "https://leamss.com/usa/visa/usa-f1-student-visa",
        "United States",
        CATEGORY_TR,
        "USA F1 Student Visa",
    ),
    "f-1": (
        "USA F1 Student Visa for Indians 2026 | Study in America",
        "https://leamss.com/usa/visa/usa-f1-student-visa",
        "United States",
        CATEGORY_TR,
        "USA F1 Student Visa",
    ),

    # 11. USA M1 Visa
    "usa m1 vocational student visa": (
        "USA M1 Vocational Student Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-m1-vocational-student-visa",
        "United States",
        CATEGORY_TR,
        "USA M1 Vocational Student Visa",
    ),
    "australia m1 vocational student": (
        "USA M1 Vocational Student Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-m1-vocational-student-visa",
        "United States",
        CATEGORY_TR,
        "USA M1 Vocational Student Visa",
    ),
    "m1 vocational student": (
        "USA M1 Vocational Student Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-m1-vocational-student-visa",
        "United States",
        CATEGORY_TR,
        "USA M1 Vocational Student Visa",
    ),
    "usa-m1-vocational-student-visa": (
        "USA M1 Vocational Student Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-m1-vocational-student-visa",
        "United States",
        CATEGORY_TR,
        "USA M1 Vocational Student Visa",
    ),
    "m1 visa": (
        "USA M1 Vocational Student Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-m1-vocational-student-visa",
        "United States",
        CATEGORY_TR,
        "USA M1 Vocational Student Visa",
    ),
    "m-1 visa": (
        "USA M1 Vocational Student Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-m1-vocational-student-visa",
        "United States",
        CATEGORY_TR,
        "USA M1 Vocational Student Visa",
    ),
    "m1": (
        "USA M1 Vocational Student Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-m1-vocational-student-visa",
        "United States",
        CATEGORY_TR,
        "USA M1 Vocational Student Visa",
    ),

    # 12. USA J1 Visa
    "usa j-1 intern & trainee visa": (
        "USA J-1 Intern & Trainee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-j1-interns-trainees-visa",
        "United States",
        CATEGORY_TR,
        "USA J-1 Intern & Trainee Visa",
    ),
    "usa j1 interns trainees visa": (
        "USA J-1 Intern & Trainee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-j1-interns-trainees-visa",
        "United States",
        CATEGORY_TR,
        "USA J-1 Intern & Trainee Visa",
    ),
    "australia j-1 exchange visitor visa (interns & trainees)": (
        "USA J-1 Intern & Trainee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-j1-interns-trainees-visa",
        "United States",
        CATEGORY_TR,
        "USA J-1 Intern & Trainee Visa",
    ),
    "australia j1 exchange visitor visa (interns & trainees)": (
        "USA J-1 Intern & Trainee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-j1-interns-trainees-visa",
        "United States",
        CATEGORY_TR,
        "USA J-1 Intern & Trainee Visa",
    ),
    "j-1 exchange visitor visa (interns & trainees)": (
        "USA J-1 Intern & Trainee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-j1-interns-trainees-visa",
        "United States",
        CATEGORY_TR,
        "USA J-1 Intern & Trainee Visa",
    ),
    "usa-j1-interns-trainees-visa": (
        "USA J-1 Intern & Trainee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-j1-interns-trainees-visa",
        "United States",
        CATEGORY_TR,
        "USA J-1 Intern & Trainee Visa",
    ),
    "j-1 visa": (
        "USA J-1 Intern & Trainee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-j1-interns-trainees-visa",
        "United States",
        CATEGORY_TR,
        "USA J-1 Intern & Trainee Visa",
    ),
    "j1 visa": (
        "USA J-1 Intern & Trainee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-j1-interns-trainees-visa",
        "United States",
        CATEGORY_TR,
        "USA J-1 Intern & Trainee Visa",
    ),
    "j1": (
        "USA J-1 Intern & Trainee Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-j1-interns-trainees-visa",
        "United States",
        CATEGORY_TR,
        "USA J-1 Intern & Trainee Visa",
    ),

    # 13. USA B1/B2 Visa
    "usa b1/b2 tourist & business visa": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),
    "usa b1 b2 tourist business visa": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),
    "australia b1/b2 visitor": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),
    "australia b1 b2 visitor": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),
    "b1/b2 visitor": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),
    "usa-b1-b2-tourist-business-visa": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),
    "b1/b2 visa": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),
    "b1 b2 visa": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),
    "b1 visa": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),
    "b2 visa": (
        "USA B1/B2 Tourist & Business Visa for Indians 2026",
        "https://leamss.com/usa/visa/usa-b1-b2-tourist-business-visa",
        "United States",
        CATEGORY_TR,
        "USA B1/B2 Tourist & Business Visa",
    ),

    # 14. USA P1 Visa
    "p1 visa usa": (
        "P-1 Visa USA: Internationally Recognized Athletes & Entertainers",
        "https://leamss.com/usa/visa/p1-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA P-1 Athlete & Entertainer Visa",
    ),
    "p-1 visa usa": (
        "P-1 Visa USA: Internationally Recognized Athletes & Entertainers",
        "https://leamss.com/usa/visa/p1-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA P-1 Athlete & Entertainer Visa",
    ),
    "p1-visa-usa": (
        "P-1 Visa USA: Internationally Recognized Athletes & Entertainers",
        "https://leamss.com/usa/visa/p1-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA P-1 Athlete & Entertainer Visa",
    ),

    # 15. USA P2 Visa
    "p2 visa usa": (
        "P-2 Visa USA | Reciprocal Exchange Artists & Entertainers",
        "https://leamss.com/usa/visa/p2-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA P-2 Artist & Entertainer Visa",
    ),
    "p-2 visa usa": (
        "P-2 Visa USA | Reciprocal Exchange Artists & Entertainers",
        "https://leamss.com/usa/visa/p2-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA P-2 Artist & Entertainer Visa",
    ),
    "p2-visa-usa": (
        "P-2 Visa USA | Reciprocal Exchange Artists & Entertainers",
        "https://leamss.com/usa/visa/p2-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA P-2 Artist & Entertainer Visa",
    ),

    # 16. USA P3 Visa
    "p3 visa usa": (
        "P-3 Visa USA | Culturally Unique Artists & Entertainers",
        "https://leamss.com/usa/visa/p3-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA P-3 Culturally Unique Artist Visa",
    ),
    "p-3 visa usa": (
        "P-3 Visa USA | Culturally Unique Artists & Entertainers",
        "https://leamss.com/usa/visa/p3-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA P-3 Culturally Unique Artist Visa",
    ),
    "p3-visa-usa": (
        "P-3 Visa USA | Culturally Unique Artists & Entertainers",
        "https://leamss.com/usa/visa/p3-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA P-3 Culturally Unique Artist Visa",
    ),

    # 17. USA F2A Visa
    "f2a family visa usa": (
        "F2A Family Visa USA | Spouses and Children of Permanent Residents",
        "https://leamss.com/usa/visa/f2a-family-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA F2A Family Visa",
    ),
    "f2a-family-visa-usa": (
        "F2A Family Visa USA | Spouses and Children of Permanent Residents",
        "https://leamss.com/usa/visa/f2a-family-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA F2A Family Visa",
    ),

    # 18. USA F2B Visa
    "f2b family visa usa": (
        "F2B Family Visa USA | Unmarried Sons and Daughters of PR",
        "https://leamss.com/usa/visa/f2b-family-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA F2B Family Visa",
    ),
    "f2b-family-visa-usa": (
        "F2B Family Visa USA | Unmarried Sons and Daughters of PR",
        "https://leamss.com/usa/visa/f2b-family-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA F2B Family Visa",
    ),

    # 19. USA F3 Visa
    "f3 family visa usa": (
        "F3 Family Visa USA | Married Sons and Daughters of US Citizens",
        "https://leamss.com/usa/visa/f3-family-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA F3 Family Visa",
    ),
    "f3-family-visa-usa": (
        "F3 Family Visa USA | Married Sons and Daughters of US Citizens",
        "https://leamss.com/usa/visa/f3-family-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA F3 Family Visa",
    ),

    # 20. USA IR1 / CR1 Visa
    "ir1 cr1 spouse visa usa": (
        "IR1 / CR1 Spouse Visa USA | Green Card for Spouse of US Citizen",
        "https://leamss.com/usa/visa/ir1-cr1-spouse-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA IR1 / CR1 Spouse Visa",
    ),
    "ir1-cr1-spouse-visa-usa": (
        "IR1 / CR1 Spouse Visa USA | Green Card for Spouse of US Citizen",
        "https://leamss.com/usa/visa/ir1-cr1-spouse-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA IR1 / CR1 Spouse Visa",
    ),

    # 21. USA IR2 Visa
    "ir2 child immigrant visa usa": (
        "IR2 Child Immigrant Visa USA | Green Card for Children of US Citizens",
        "https://leamss.com/usa/visa/ir2-child-immigrant-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA IR2 Child Immigrant Visa",
    ),
    "ir2-child-immigrant-visa-usa": (
        "IR2 Child Immigrant Visa USA | Green Card for Children of US Citizens",
        "https://leamss.com/usa/visa/ir2-child-immigrant-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA IR2 Child Immigrant Visa",
    ),

    # 22. USA IR5 Visa
    "ir5 parent visa usa": (
        "IR5 Parent Visa USA | Green Card for Parents of US Citizens",
        "https://leamss.com/usa/visa/ir5-parent-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA IR5 Parent Visa",
    ),
    "ir5-parent-visa-usa": (
        "IR5 Parent Visa USA | Green Card for Parents of US Citizens",
        "https://leamss.com/usa/visa/ir5-parent-visa-usa",
        "United States",
        CATEGORY_PR,
        "USA IR5 Parent Visa",
    ),

    # 23. USA K1 Visa
    "k1 fiance visa usa": (
        "K1 Fiance Visa USA | Fiance Visa for US Citizens",
        "https://leamss.com/usa/visa/k1-fiance-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA K1 Fiance Visa",
    ),
    "k1-fiance-visa-usa": (
        "K1 Fiance Visa USA | Fiance Visa for US Citizens",
        "https://leamss.com/usa/visa/k1-fiance-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA K1 Fiance Visa",
    ),

    # 24. USA K3 Visa
    "k3 spouse visa usa": (
        "K3 Spouse Visa USA | Nonimmigrant Visa for Spouse of US Citizen",
        "https://leamss.com/usa/visa/k3-spouse-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA K3 Spouse Visa",
    ),
    "k3-spouse-visa-usa": (
        "K3 Spouse Visa USA | Nonimmigrant Visa for Spouse of US Citizen",
        "https://leamss.com/usa/visa/k3-spouse-visa-usa",
        "United States",
        CATEGORY_TR,
        "USA K3 Spouse Visa",
    ),

    # 25. USA Landing Page
    "usa visa": (
        "Study in USA 2026 | University & F1 Visa Guide | LEAMSS Mumbai",
        "https://leamss.com/usa-visa",
        "United States",
        CATEGORY_TR,
        "USA Visa Guide",
    ),
    "usa-visa": (
        "Study in USA 2026 | University & F1 Visa Guide | LEAMSS Mumbai",
        "https://leamss.com/usa-visa",
        "United States",
        CATEGORY_TR,
        "USA Visa Guide",
    ),
    "us visa": (
        "Study in USA 2026 | University & F1 Visa Guide | LEAMSS Mumbai",
        "https://leamss.com/usa-visa",
        "United States",
        CATEGORY_TR,
        "USA Visa Guide",
    ),

    # --- MIGRATE GENERAL PAGE ---
    "migrate": (
        "Migrate Abroad from India: Visa Options by Country",
        "https://leamss.com/migrate",
        None,
        CATEGORY_PR,
    ),

    # --- SERVICES PAGE ---
    "our services": (
        "Immigration & Visa Services in Thane | ₹2,100 Consultation",
        "https://leamss.com/Our-Services",
        None,
        CATEGORY_GENERAL,
    ),
    "our-services": (
        "Immigration & Visa Services in Thane | ₹2,100 Consultation",
        "https://leamss.com/Our-Services",
        None,
        CATEGORY_GENERAL,
    ),

    # --- PROTECTION POLICY PAGE ---
    "protection policy": (
        "LEAMSS Protection Policy: Australia PR Fee Refund Terms",
        "https://leamss.com/protection-policy",
        "Australia",
        CATEGORY_PR,
    ),
    "protection-policy": (
        "LEAMSS Protection Policy: Australia PR Fee Refund Terms",
        "https://leamss.com/protection-policy",
        "Australia",
        CATEGORY_PR,
    ),

    # --- STUDY ABROAD SPECIFIC COUNTRY PAGES ---
    "uk": (
        "Study in UK from India: Fees, Universities & Visa",
        "https://leamss.com/study-abroad/study-in-uk",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "study in uk": (
        "Study in UK from India: Fees, Universities & Visa",
        "https://leamss.com/study-abroad/study-in-uk",
        "United Kingdom",
        CATEGORY_TR,
    ),
    "australia": (
        "Study in Australia from India: Universities, Fees & Visa",
        "https://leamss.com/study-abroad/study-in-australia",
        "Australia",
        CATEGORY_TR,
    ),
    "study in australia": (
        "Study in Australia from India: Universities, Fees & Visa",
        "https://leamss.com/study-abroad/study-in-australia",
        "Australia",
        CATEGORY_TR,
    ),
    "canada": (
        "Study in Canada for Indian Students: Study Permit & PGWP",
        "https://leamss.com/study-abroad/study-in-canada",
        "Canada",
        CATEGORY_TR,
    ),
    "study in canada": (
        "Study in Canada for Indian Students: Study Permit & PGWP",
        "https://leamss.com/study-abroad/study-in-canada",
        "Canada",
        CATEGORY_TR,
    ),
    "usa": (
        "Study in USA from India: Universities, Costs & Visa",
        "https://leamss.com/study-abroad/study-in-usa",
        "United States",
        CATEGORY_TR,
    ),
    "study in usa": (
        "Study in USA from India: Universities, Costs & Visa",
        "https://leamss.com/study-abroad/study-in-usa",
        "United States",
        CATEGORY_TR,
    ),
    "new zeland": (
        "Study in New Zealand for Indian Students | LEAMSS",
        "https://leamss.com/study-abroad/study-in-new-zealand",
        "New Zealand",
        CATEGORY_TR,
    ),
    "new zealand": (
        "Study in New Zealand for Indian Students | LEAMSS",
        "https://leamss.com/study-abroad/study-in-new-zealand",
        "New Zealand",
        CATEGORY_TR,
    ),
    "study in new zealand": (
        "Study in New Zealand for Indian Students | LEAMSS",
        "https://leamss.com/study-abroad/study-in-new-zealand",
        "New Zealand",
        CATEGORY_TR,
    ),
    "european contries": (
        "Study in Europe for Indian Students: Germany, France & More",
        "https://leamss.com/study-abroad/study-in-european-countries",
        "European Countries",
        CATEGORY_TR,
    ),
    "european countries": (
        "Study in Europe for Indian Students: Germany, France & More",
        "https://leamss.com/study-abroad/study-in-european-countries",
        "European Countries",
        CATEGORY_TR,
    ),
    "study in european countries": (
        "Study in Europe for Indian Students: Germany, France & More",
        "https://leamss.com/study-abroad/study-in-european-countries",
        "European Countries",
        CATEGORY_TR,
    ),
    "study abroad": (
        "Study Abroad Consultants in Thane & Mumbai | LEAMSS",
        "https://leamss.com/study-abroad",
        None,
        CATEGORY_TR,
    ),
    "study-abroad": (
        "Study Abroad Consultants in Thane & Mumbai | LEAMSS",
        "https://leamss.com/study-abroad",
        None,
        CATEGORY_TR,
    ),

    # --- WEBSITE CONSULTATION POPUP ---
    "website popup": (
        "LEAMSS Official Website – Consultation Popup",
        "https://leamss.com",
        None,
        CATEGORY_GENERAL,
    ),
}


def resolve_page_details(doc: Dict[str, Any]) -> tuple[str, str, str]:
    """Resolves (website_page_title, website_page_url, visa_pathway) for a lead."""
    base_site = "https://leamss.com"

    page_url = str(doc.get("website_page_url") or doc.get("page_url") or "").strip()
    page_title = str(doc.get("website_page_title") or doc.get("page_title") or "").strip()
    enquired_for = str(doc.get("enquired_for") or "").strip()
    enq_raw = enquired_for.lower()
    enq_clean = re.sub(r'[\s\-_]+', ' ', enq_raw).strip()
    doc_corpus = f"{enq_raw} {str(doc.get('name') or '').lower()} {str(doc.get('message') or doc.get('msg') or '').lower()} {str(doc.get('service_interested') or doc.get('services') or '').lower()}"
    atlas_code = str(doc.get("atlas_code") or "").strip()
    atlas_title = str(doc.get("atlas_title") or "").strip()
    coi = str(doc.get("country_of_interest") or "au").lower()
    interested_state = str(doc.get("interested_state") or "").lower()

    # --- SPECIAL HANDLING FOR MIGRATION ATLAS & POINTS CALCULATOR LEADS ---
    if is_atlas_lead(doc):
        # 1. Try to extract occupation code and title if missing
        if not atlas_code and "/atlas/" in page_url:
            m_code = re.search(r'/atlas/(?:au|ca|nz|uk|us)/([0-9a-zA-Z\-_]+)', page_url, re.IGNORECASE)
            if m_code:
                atlas_code = m_code.group(1).strip("/")
        if not atlas_title and doc.get("message"):
            m_msg = re.search(r'Interested in:\s*([^()]+?)(?:\s*\(([0-9a-zA-Z\-_]+)\))?', str(doc.get("message")))
            if m_msg:
                atlas_title = m_msg.group(1).strip()
                if not atlas_code and m_msg.group(2):
                    atlas_code = m_msg.group(2).strip()

        # 2. Determine Page URL
        if page_url.startswith("http://") or page_url.startswith("https://"):
            clean_url = page_url
        elif page_url.startswith("/"):
            clean_url = f"{base_site}{page_url}"
        elif atlas_code and atlas_code != "mega-landing":
            clean_url = f"{base_site}/atlas/{coi}/{atlas_code}"
        elif interested_state:
            clean_url = f"{base_site}/atlas/au/state/{interested_state}"
        else:
            clean_url = f"{base_site}/start"

        # 3. Determine Page Title
        if page_title and page_title not in ("LEAMSS Official Website", "Migration Atlas", "– LEAMSS", "LEAMSS", "LEAMSS Official Page"):
            clean_title = page_title
        elif atlas_code == "mega-landing":
            clean_title = "Find Your Migration Pathway in 60 Seconds - LEAMSS"
        elif atlas_title and atlas_code:
            clean_title = f"{atlas_title} ({atlas_code}) - Migration Atlas | LEAMSS"
        elif atlas_title:
            clean_title = f"{atlas_title} - Migration Atlas | LEAMSS"
        elif atlas_code:
            clean_title = f"Occupation {atlas_code} - Migration Atlas | LEAMSS"
        elif interested_state:
            clean_title = f"{interested_state.upper()} State Nomination Guide & Opportunities"
        elif "/start" in clean_url or doc.get("source") in ("eligibility_quiz", "eligibility_pre_score"):
            clean_title = "Free Immigration Points Calculator - LEAMSS"
        else:
            clean_title = "Migration Atlas - LEAMSS"

        # 4. Determine Visa Pathway / Enquiry For
        if atlas_title and atlas_code and atlas_code != "mega-landing":
            clean_pathway = f"{atlas_title} ({atlas_code})"
        elif atlas_title:
            clean_pathway = atlas_title
        elif "/start" in clean_url or doc.get("source") in ("eligibility_quiz", "eligibility_pre_score"):
            clean_pathway = "Immigration Points Calculator"
        else:
            clean_pathway = str(doc.get("service_interested") or doc.get("visa_pathway") or "Migration Atlas Consultation").strip()

        return clean_title, clean_url, clean_pathway

    # 1. Match from enquired_for if present in PAGE_METADATA_MAP
    mapped_title = None
    mapped_url = None
    matched_entry = PAGE_METADATA_MAP.get(enq_raw) or PAGE_METADATA_MAP.get(enq_clean)
    if matched_entry:
        mapped_title = matched_entry[0]
        mapped_url = matched_entry[1]
    else:
        # Check without prefixes like 'nz ', 'uk ', 'australia ', 'canada ', 'new zealand ', 'usa ', 'us '
        for prefix in ("nz ", "uk ", "australia ", "canada ", "new zealand ", "usa ", "us "):
            if enq_raw.startswith(prefix):
                stripped = enq_raw[len(prefix):].strip()
                if stripped in PAGE_METADATA_MAP:
                    mapped_title, mapped_url = PAGE_METADATA_MAP[stripped][:2]
                    matched_entry = PAGE_METADATA_MAP[stripped]
                    break
            elif enq_clean.startswith(prefix):
                stripped = enq_clean[len(prefix):].strip()
                if stripped in PAGE_METADATA_MAP:
                    mapped_title, mapped_url = PAGE_METADATA_MAP[stripped][:2]
                    matched_entry = PAGE_METADATA_MAP[stripped]
                    break

    # 2. Check if page_url matches any URL in PAGE_METADATA_MAP
    if not mapped_url and page_url:
        page_url_clean = page_url.rstrip("/").lower()
        for k, v in PAGE_METADATA_MAP.items():
            if v[1].rstrip("/").lower() == page_url_clean:
                mapped_title, mapped_url = v[0], v[1]
                matched_entry = v
                break

    # 3. Smart Keyword Fallback if still not matched and enq_raw is specific
    if not mapped_url and enq_raw and enq_raw not in ("website popup", "general enquiry", "website enquiry", "migrate"):
        # Check USA visa keywords
        if any(kw in enq_raw for kw in ("o1", "o-1", "extraordinary ability")):
            matched_entry = PAGE_METADATA_MAP.get("usa o1 extraordinary ability visa")
        elif any(kw in enq_raw for kw in ("eb1", "eb-1", "priority workers")):
            matched_entry = PAGE_METADATA_MAP.get("usa eb1 priority workers green card visa")
        elif any(kw in enq_raw for kw in ("eb2", "eb-2", "advanced degree")):
            matched_entry = PAGE_METADATA_MAP.get("usa eb-2 green card visa")
        elif any(kw in enq_raw for kw in ("eb3", "eb-3")):
            matched_entry = PAGE_METADATA_MAP.get("usa eb-3 green card visa")
        elif any(kw in enq_raw for kw in ("eb4", "eb-4", "special immigrant")):
            matched_entry = PAGE_METADATA_MAP.get("usa eb-4 special immigrants visa")
        elif any(kw in enq_raw for kw in ("eb5", "eb-5", "immigrant investor")):
            matched_entry = PAGE_METADATA_MAP.get("usa eb-5 immigrant investor program")
        elif any(kw in enq_raw for kw in ("h1b", "h-1b")):
            matched_entry = PAGE_METADATA_MAP.get("usa h1b work visa")
        elif any(kw in enq_raw for kw in ("h2b", "h-2b")):
            matched_entry = PAGE_METADATA_MAP.get("usa h-2b temporary workers visa")
        elif any(kw in enq_raw for kw in ("l1", "l-1", "intracompany")):
            matched_entry = PAGE_METADATA_MAP.get("usa l1 intracompany transferee visa")
        elif any(kw in enq_raw for kw in ("f1", "f-1")):
            matched_entry = PAGE_METADATA_MAP.get("usa f1 student visa")
        elif any(kw in enq_raw for kw in ("m1", "m-1", "vocational")):
            matched_entry = PAGE_METADATA_MAP.get("usa m1 vocational student visa")
        elif any(kw in enq_raw for kw in ("j1", "j-1")):
            matched_entry = PAGE_METADATA_MAP.get("usa j-1 intern & trainee visa")
        elif any(kw in enq_raw for kw in ("b1", "b2", "b1/b2")):
            matched_entry = PAGE_METADATA_MAP.get("usa b1/b2 tourist & business visa")
        # Check Canada keywords
        elif "express entry" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("canada express entry system")
        elif "fswp" in enq_raw or "federal skilled worker" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("canada federal skilled worker program")
        elif "fstp" in enq_raw or "federal skilled trades" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("canada federal skilled trades program")
        elif "cec" in enq_raw or "canadian experience" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("canada canadian experience class")
        elif "oinp" in enq_raw or "ontario" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("ontario immigrant nominee program")
        # Check Australia keywords
        elif "100" in doc_corpus or ("partner" in enq_raw and "permanent" in enq_raw and "801" not in doc_corpus):
            matched_entry = PAGE_METADATA_MAP.get("australia-partner-visa-subclass-100-offshore")
        elif "801" in doc_corpus or ("partner" in enq_raw and "permanent" in enq_raw and "801" in doc_corpus):
            matched_entry = PAGE_METADATA_MAP.get("australia-subclass-801-partner-visa-onshore")
        elif "820" in doc_corpus or ("partner" in enq_raw and "temporary" in enq_raw and "309" not in doc_corpus):
            matched_entry = PAGE_METADATA_MAP.get("australia-subclass-820-partner-visa-onshore")
        elif "309" in doc_corpus or ("partner" in enq_raw and "provisional" in enq_raw):
            matched_entry = PAGE_METADATA_MAP.get("partner-visa-subclass-309-offshore-provisional")
        elif "400" in doc_corpus or "temporary work" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("australia-subclass-400-visa")
        elif "462" in doc_corpus or "work and holiday" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("australia-subclass-462-work-and-holiday-visa")
        elif "189" in enq_raw or "skilled independent" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("skilled independent visa subclass 189 australia")
        elif "190" in enq_raw or "skilled nominated" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("skilled nominated visa subclass 190 australia")
        elif "491" in enq_raw or "skilled work regional" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("skilled work regional visa subclass 491 australia")
        elif "186" in enq_raw or "employer nomination" in enq_raw or "ens" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("subclass 186 employer nomination scheme visa australia")
        elif "482" in enq_raw or "skills in demand" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("australia subclass 482 skills in demand visa")
        elif "485" in enq_raw or "temporary graduate" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("subclass 485 temporary graduate visa")
        elif "500" in enq_raw or "student visa" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("australia student visa subclass 500")
        elif "600" in enq_raw or "visitor visa" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("australia visitor visa subclass 600")
        # Check New Zealand keywords
        elif "pswv" in enq_raw or "post study work" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("nz post study work visa")
        elif "aewv" in enq_raw or "accredited employer" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("nz accredited employer work visa")
        elif "smc" in enq_raw or "skilled migrant" in enq_raw:
            matched_entry = PAGE_METADATA_MAP.get("nz skilled migrant category resident visa")

        if matched_entry:
            mapped_title, mapped_url = matched_entry[:2]

    # 4. Only if still not matched AND enq_raw is genuinely generic, check services
    if not mapped_url and (not enq_raw or enq_raw in ("migrate", "website popup", "general enquiry", "website enquiry")):
        srv_lower = str(doc.get("services") or doc.get("service_interested") or "").lower()
        if "pr australia" in srv_lower:
            matched_entry = PAGE_METADATA_MAP["australia pr"]
            mapped_title, mapped_url = matched_entry[:2]
        elif "pr canada" in srv_lower:
            matched_entry = PAGE_METADATA_MAP["canada pr"]
            mapped_title, mapped_url = matched_entry[:2]
        elif "tr australia" in srv_lower:
            matched_entry = PAGE_METADATA_MAP["australia tr"]
            mapped_title, mapped_url = matched_entry[:2]
        elif "tr canada" in srv_lower:
            matched_entry = PAGE_METADATA_MAP["canada tr"]
            mapped_title, mapped_url = matched_entry[:2]
        elif "study abroad" in srv_lower:
            matched_entry = PAGE_METADATA_MAP["study abroad"]
            mapped_title, mapped_url = matched_entry[:2]
        elif enq_raw and enq_raw not in ("website popup", "general enquiry", "website enquiry"):
            # Safe slug or canonical landing page fallback (prevent generating 404 slugs like /nz-...)
            if enq_raw.startswith("nz ") or "new zealand" in enq_raw:
                mapped_title = "New Zealand Visa Guide 2026 | PR, Work, Student & Visitor Visa Options"
                mapped_url = "https://leamss.com/newzealand-visa"
            elif enq_raw.startswith("uk ") or "united kingdom" in enq_raw:
                mapped_title = "UK Visa for Indians 2026 | Complete Immigration Guide"
                mapped_url = "https://leamss.com/uk-visa"
            elif "australia" in enq_raw:
                mapped_title = "Australia PR from India: 189, 190 & 491 Visa Guide"
                mapped_url = "https://leamss.com/immigration/permanent-residency/australia"
            elif "canada" in enq_raw:
                mapped_title = "Canada PR from India: Express Entry, PNP & CRS Guide."
                mapped_url = "https://leamss.com/immigration/permanent-residency/canada"
            elif "usa" in enq_raw or "united states" in enq_raw:
                mapped_title = "Study in USA 2026 | University & F1 Visa Guide | LEAMSS Mumbai"
                mapped_url = "https://leamss.com/usa-visa"
            else:
                slug = re.sub(r'[^a-z0-9]+', '-', enq_raw).strip('-')
                mapped_title = f"{doc.get('enquired_for')} – LEAMSS"
                mapped_url = f"{base_site}/{slug}"

    # 4. If mapped_url is found, evaluate whether existing page_url should be replaced
    if mapped_url:
        is_stale_or_generic = (
            not page_url
            or page_url in (base_site, f"{base_site}/", f"{base_site}/migrate", f"{base_site}/uk-visa", f"{base_site}/start")
            or page_url.startswith(f"{base_site}/nz-")
            or page_url.startswith(f"{base_site}/uk-")
            or "– leamss" in page_title.lower()
            or matched_entry is not None
            or enq_raw in PAGE_METADATA_MAP
            or enq_clean in PAGE_METADATA_MAP
        )
        if is_stale_or_generic:
            page_url = mapped_url
            page_title = mapped_title
    elif not page_url:
        if atlas_code == "mega-landing":
            page_url = f"{base_site}/start"
        elif atlas_code:
            page_url = f"{base_site}/atlas/{coi}/{atlas_code}"
        elif interested_state:
            page_url = f"{base_site}/atlas/au/state/{interested_state}"
        elif doc.get("source") == "eligibility_pre_score":
            page_url = f"{base_site}/start#quiz"
        else:
            page_url = f"{base_site}/start"

    # 5. Evaluate page_title
    if mapped_title:
        if (
            not page_title
            or "– leamss" in page_title.lower()
            or page_title in (
                "LEAMSS Official Website",
                "LEAMSS Official Website Enquiry",
                "Find Your Migration Pathway in 60 Seconds - LEAMSS"
            )
            or ("Migrate Abroad from India" in page_title and enq_raw != "migrate")
            or ("Complete Immigration Guide" in page_title and enq_raw not in ("uk visa", "uk-visa"))
            or matched_entry is not None
            or enq_raw in PAGE_METADATA_MAP
            or enq_clean in PAGE_METADATA_MAP
        ):
            page_title = mapped_title
    elif not page_title:
        if atlas_title and atlas_code and atlas_code != "mega-landing":
            page_title = f"{atlas_title} ({atlas_code}) - Migration Atlas"
        elif interested_state:
            page_title = f"{interested_state.upper()} State Nomination Guide & Opportunities"
        elif atlas_code == "mega-landing" or "/start" in page_url:
            page_title = "Find Your Migration Pathway in 60 Seconds - LEAMSS"
        elif "/calculator" in page_url or doc.get("source") == "eligibility_pre_score":
            page_title = "Free AI Visa Eligibility Assessment & Points Calculator"
        elif "/countries" in page_url:
            page_title = "Country Migration & Visa Pathways Guide"
        else:
            page_title = "LEAMSS Official Website"

    clean_pathway = None
    if matched_entry and len(matched_entry) >= 5 and matched_entry[4]:
        clean_pathway = matched_entry[4]

    visa_pathway = str(
        clean_pathway or
        doc.get("visa_pathway") or
        doc.get("service_interested") or
        doc.get("service_type") or
        doc.get("top_pathway_name") or
        doc.get("atlas_title") or
        doc.get("enquired_for") or
        "Skilled Migration Assessment"
    ).strip()

    return page_title, page_url, visa_pathway


def _project_website_lead(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Projects raw database lead document into standardized Website Lead shape."""
    page_title, page_url, visa_pathway = resolve_page_details(doc)
    cat = classify_lead_category(doc)
    norm_country = normalize_country(doc.get("country") or doc.get("country_of_interest"), page_url, doc.get("atlas_code"))
    clean_enq = None

    if not is_atlas_lead(doc):
        enq_lower = str(doc.get("enquired_for") or "").strip().lower()
        enq_clean = re.sub(r'[\s\-_]+', ' ', enq_lower).strip()
        matched_entry = PAGE_METADATA_MAP.get(enq_lower) or PAGE_METADATA_MAP.get(enq_clean)
        if not matched_entry and page_url:
            page_url_clean = page_url.rstrip("/").lower()
            for k, v in PAGE_METADATA_MAP.items():
                if v[1].rstrip("/").lower() == page_url_clean:
                    matched_entry = v
                    break

        if matched_entry and len(matched_entry) >= 4:
            meta_country = matched_entry[2]
            meta_cat = matched_entry[3]
            if len(matched_entry) >= 5 and matched_entry[4]:
                clean_enq = matched_entry[4]
                visa_pathway = clean_enq

            if meta_country:
                # Subclass destination country overrides applicant's nationality/generic country
                if not norm_country or norm_country in ("Other", "Global / Other", "Global", "India") or enq_lower not in ("migrate", "website popup", "general enquiry", "website enquiry"):
                    norm_country = meta_country
            if meta_cat and (not cat or cat in (CATEGORY_GENERAL, "Other", CATEGORY_OTHER)):
                cat = meta_cat
            elif meta_cat and enq_lower not in ("migrate", "website popup", "general enquiry", "website enquiry"):
                cat = meta_cat

    assigned_to = doc.get("assigned_to")
    assigned_name = doc.get("assigned_to_name")
    if not assigned_to or assigned_to in ("none", "unassigned"):
        assigned_to = None
        assigned_name = "Unassigned"

    created_at = doc.get("created_at")
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or "")

    resume_fid = doc.get("resume_file_id")
    resume_u = doc.get("resume_url") or doc.get("resume_path") or (f"/cockpit/resume/{resume_fid}" if resume_fid else None)

    return {
        "id": doc.get("id") or str(doc.get("_id", "")),
        "lead_number": doc.get("lead_number", ""),
        "name": doc.get("name", "Unknown Client"),
        "email": doc.get("email", ""),
        "phone": doc.get("phone") or doc.get("mobile", ""),
        "alternate_phone": doc.get("alternate_phone", ""),
        "whatsapp_number": doc.get("whatsapp_number") or doc.get("phone", ""),
        "country": norm_country,
        "country_raw": doc.get("country") or doc.get("country_of_interest", ""),
        "qualification": doc.get("qualification") or doc.get("latest_qualification") or doc.get("highest_qualification") or doc.get("education") or "",
        "latest_qualification": doc.get("latest_qualification") or doc.get("qualification") or doc.get("highest_qualification") or doc.get("education") or "",
        "work_experience": doc.get("work_experience") or doc.get("total_work_experience") or doc.get("work_exp") or doc.get("experience_years") or "",
        "total_work_experience": doc.get("total_work_experience") or doc.get("work_experience") or doc.get("work_exp") or doc.get("experience_years") or "",
        "resume_file_id": resume_fid,
        "resume_filename": doc.get("resume_filename"),
        "resume_url": resume_u,
        "resume_uploaded": bool(doc.get("resume_uploaded") or resume_fid or resume_u),
        "category": cat,
        "categories": sorted(list(get_lead_categories(doc))),
        "category_meta": CATEGORY_METADATA.get(cat, CATEGORY_METADATA.get(CATEGORY_GENERAL, {})),
        "visa_pathway": clean_enq or visa_pathway,
        "service_interested": doc.get("service_interested") or doc.get("services") or clean_enq or visa_pathway,
        "enquired_for": clean_enq or doc.get("enquired_for") or visa_pathway,
        "website_page_title": page_title,
        "website_page_url": page_url,
        "enquiry_date": created_at_str,
        "created_at": created_at_str,
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_name or "Unassigned",
        "is_unassigned": assigned_to is None,
        "source": doc.get("source", "Website"),
        "message": doc.get("message") or doc.get("msg") or "",
        "notes": doc.get("notes", []),
        "lead_score": doc.get("lead_score", 50),
        "score_category": doc.get("score_category", "WARM"),
        "stage": doc.get("stage", "new"),
        "status": doc.get("status", "new"),
    }


@router.post("/capture")
async def capture_crm_website_lead(request: Request):
    """
    Dedicated public ingestion endpoint for enquiries from Laravel website forms (e.g. submitgeneralenquiry).
    Accepts full website form payload (JSON or multipart/form-data with resume file), automatically classifies category, normalizes country, and records unassigned lead.
    """
    from routers.leads import capture_lead
    return await capture_lead(request=request, current_user=None)


@router.get("/overview")
async def get_website_leads_overview(current_user: dict = Depends(get_current_user)):
    """
    Returns aggregated stats for Website Leads (Admin only):
    - total website leads
    - total unassigned leads
    - breakdown by Categories (PR, TR, Work, Study, Tourist, Family, General)
    - under each Category, breakdown by Country (Australia, Canada, UK, USA, etc.)
    - all_countries_list across all enquiries
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Only administrators can access website leads.")

    leads_cursor = leads_col.find(
        {"$or": WEBSITE_LEAD_CONDITIONS},
        {"_id": 0}
    ).sort("created_at", -1)

    all_raw_leads = await leads_cursor.to_list(2000)

    total_count = len(all_raw_leads)
    unassigned_count = 0

    category_buckets: Dict[str, Dict[str, Any]] = {
        cat: {
            **CATEGORY_METADATA[cat],
            "count": 0,
            "unassigned_count": 0,
            "countries": {}
        }
        for cat in ALL_CATEGORIES
    }

    all_countries: Dict[str, Dict[str, Any]] = {}

    for raw in all_raw_leads:
        proj = _project_website_lead(raw)
        country = proj["country"]
        is_unassigned = proj["is_unassigned"]

        if is_unassigned:
            unassigned_count += 1

        if country not in all_countries:
            all_countries[country] = {"country": country, "count": 0, "unassigned_count": 0}
        all_countries[country]["count"] += 1
        if is_unassigned:
            all_countries[country]["unassigned_count"] += 1

        matched_cats = get_lead_categories(raw)
        if proj.get("category"):
            matched_cats.add(proj["category"])

        for cat in matched_cats:
            if cat in category_buckets:
                bucket = category_buckets[cat]
                bucket["count"] += 1
                if is_unassigned:
                    bucket["unassigned_count"] += 1

                country_dict = bucket["countries"]
                if country not in country_dict:
                    country_dict[country] = {"country": country, "count": 0, "unassigned_count": 0}
                country_dict[country]["count"] += 1
                if is_unassigned:
                    country_dict[country]["unassigned_count"] += 1

    # Format countries dict into sorted list
    for cat, b in category_buckets.items():
        sorted_countries = sorted(b["countries"].values(), key=lambda x: x["count"], reverse=True)
        b["countries_list"] = sorted_countries

    all_countries_list = sorted(all_countries.values(), key=lambda x: x["count"], reverse=True)

    return {
        "total_website_leads": total_count,
        "unassigned_count": unassigned_count,
        "categories": category_buckets,
        "all_countries_list": all_countries_list,
    }


@router.get("/list")
async def list_website_leads(
    category: Optional[str] = Query("all", description="PR, TR, Work, Study, Tourist, Family, General, Other, or all"),
    country: Optional[str] = Query("all", description="Target country or all"),
    assignment: Optional[str] = Query("all", description="all, unassigned, or assigned"),
    search: Optional[str] = Query(None, description="Search term across name, phone, email, pathway, url"),
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns filtered Website Leads with complete client details, contact information,
    category, country, exact website page title, page URL, and enquiry date.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Only administrators can access website leads.")

    leads_cursor = leads_col.find(
        {"$or": WEBSITE_LEAD_CONDITIONS},
        {"_id": 0}
    ).sort("created_at", -1)

    all_raw_leads = await leads_cursor.to_list(2000)
    filtered = []

    cat_filter = (category if isinstance(category, str) else "all").strip().upper()
    country_filter = (country if isinstance(country, str) else "all").strip().lower()
    assign_filter = (assignment if isinstance(assignment, str) else "all").strip().lower()
    search_term = (search if isinstance(search, str) else "").strip().lower()

    for raw in all_raw_leads:
        proj = _project_website_lead(raw)

        # 1. Category Filter
        if cat_filter != "ALL":
            lead_cats = {c.upper() for c in get_lead_categories(raw)}
            if proj.get("category"):
                lead_cats.add(proj["category"].upper())
            if cat_filter not in lead_cats:
                continue

        # 2. Country Filter
        if country_filter != "all":
            lead_c = proj["country"].lower()
            if country_filter in ("other", "global / other", "global"):
                if lead_c not in ("other", "global / other", "global"):
                    continue
            elif lead_c != country_filter:
                continue

        # 3. Assignment Filter
        if assign_filter == "unassigned" and not proj["is_unassigned"]:
            continue
        if assign_filter == "assigned" and proj["is_unassigned"]:
            continue

        # 4. Search Filter
        if search_term:
            searchable_str = " ".join([
                proj["name"],
                proj["email"],
                proj["phone"],
                proj["country"],
                proj["visa_pathway"],
                proj["website_page_title"],
                proj["website_page_url"],
                proj["message"],
            ]).lower()
            if search_term not in searchable_str:
                continue

        filtered.append(proj)

    limit_val = limit if isinstance(limit, int) else 50
    offset_val = offset if isinstance(offset, int) else 0
    total_filtered = len(filtered)
    paged = filtered[offset_val: offset_val + limit_val]

    return {
        "total": total_filtered,
        "offset": offset_val,
        "limit": limit_val,
        "category": cat_filter,
        "country": country_filter,
        "assignment": assign_filter,
        "leads": paged
    }


@router.post("/{lead_id}/assign")
async def assign_website_lead(
    lead_id: str,
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Admin assigns a website lead to a Sales Person.
    Updates assigned_to, sends notification to sales rep, and logs audit activity.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Only administrators can assign website leads.")

    sales_person_id = (payload.get("sales_person_id") or "").strip()
    if not sales_person_id:
        raise HTTPException(status_code=400, detail="sales_person_id is required")

    sales_rep = await users_col.find_one({"id": sales_person_id}, {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1})
    if not sales_rep:
        raise HTTPException(status_code=404, detail="Selected Sales Person not found")

    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "id": 1, "name": 1, "phone": 1, "email": 1, "lead_number": 1})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    now = datetime.now(timezone.utc)

    await leads_col.update_one(
        {"id": lead_id},
        {"$set": {
            "assigned_to": sales_rep["id"],
            "assigned_to_name": sales_rep["name"],
            "assigned_at": now,
            "assigned_by": current_user.get("id"),
            "assigned_by_name": current_user.get("name", "Admin"),
            "updated_at": now,
        }}
    )

    await create_notification(
        user_id=sales_rep["id"],
        title="Website Lead Assigned",
        message=f"Admin {current_user.get('name', 'Admin')} assigned website enquiry: {lead.get('name')} ({lead.get('phone')}) to you.",
        notification_type="lead_assigned",
        related_id=lead_id
    )

    await log_activity(
        user_id=current_user.get("id", "admin"),
        user_name=current_user.get("name", "Admin"),
        action="website_lead_assigned",
        entity_type="lead",
        entity_id=lead_id,
        details=f"Assigned website lead {lead.get('name')} to {sales_rep['name']} ({sales_rep['id']})"
    )

    return {
        "success": True,
        "message": f"Lead '{lead.get('name')}' successfully assigned to {sales_rep['name']}.",
        "lead_id": lead_id,
        "assigned_to": sales_rep["id"],
        "assigned_to_name": sales_rep["name"]
    }


@router.post("/bulk-assign")
async def bulk_assign_website_leads(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Admin assigns multiple website leads to a Sales Person in a single operation.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Only administrators can assign website leads.")

    lead_ids = payload.get("lead_ids") or []
    sales_person_id = (payload.get("sales_person_id") or "").strip()

    if not lead_ids or not isinstance(lead_ids, list):
        raise HTTPException(status_code=400, detail="lead_ids array is required")
    if not sales_person_id:
        raise HTTPException(status_code=400, detail="sales_person_id is required")

    sales_rep = await users_col.find_one({"id": sales_person_id}, {"_id": 0, "id": 1, "name": 1, "email": 1})
    if not sales_rep:
        raise HTTPException(status_code=404, detail="Selected Sales Person not found")

    now = datetime.now(timezone.utc)

    result = await leads_col.update_many(
        {"id": {"$in": lead_ids}},
        {"$set": {
            "assigned_to": sales_rep["id"],
            "assigned_to_name": sales_rep["name"],
            "assigned_at": now,
            "assigned_by": current_user.get("id"),
            "assigned_by_name": current_user.get("name", "Admin"),
            "updated_at": now,
        }}
    )

    await create_notification(
        user_id=sales_rep["id"],
        title="Multiple Website Leads Assigned",
        message=f"{result.modified_count} website leads assigned to you by Admin {current_user.get('name', 'Admin')}",
        notification_type="lead_assigned"
    )

    await log_activity(
        user_id=current_user.get("id", "admin"),
        user_name=current_user.get("name", "Admin"),
        action="bulk_website_leads_assigned",
        entity_type="lead",
        details=f"Assigned {result.modified_count} website leads to {sales_rep['name']}"
    )

    return {
        "success": True,
        "assigned_count": result.modified_count,
        "sales_person_id": sales_rep["id"],
        "sales_person_name": sales_rep["name"],
        "message": f"Successfully assigned {result.modified_count} leads to {sales_rep['name']}."
    }


@router.delete("/{lead_id}")
async def delete_website_lead(
    lead_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Admin deletes a website enquiry.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only administrators can delete website leads")

    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "id": 1, "name": 1})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    await leads_col.delete_one({"id": lead_id})

    await log_activity(
        user_id=current_user.get("id", "admin"),
        user_name=current_user.get("name", "Admin"),
        action="website_lead_deleted",
        entity_type="lead",
        entity_id=lead_id,
        details=f"Deleted website enquiry for {lead.get('name', 'Unknown')}"
    )

    return {
        "success": True,
        "message": f"Enquiry for '{lead.get('name')}' successfully deleted."
    }


@router.post("/sync-mysql")
async def sync_mysql_endpoint(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Connects to cPanel MySQL database (e.g. hosldwuh_staging) and syncs
    all general_enquiries and popup_enquiries directly into CRM.
    """
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Only administrators can trigger MySQL synchronization")

    host = str(payload.get("host") or "").strip()
    user = str(payload.get("user") or "").strip()
    password = str(payload.get("password") or "").strip()
    database = str(payload.get("database") or "hosldwuh_staging").strip()
    port = int(payload.get("port") or 3306)

    if not host or not user or not password:
        raise HTTPException(status_code=400, detail="host, user, and password are required")

    try:
        from services.website_mysql_sync import sync_from_mysql_connection
        result = await sync_from_mysql_connection(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync with MySQL: {str(e)}")


@router.post("/import-rows")
async def import_enquiry_rows_endpoint(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Imports enquiry rows exported from phpMyAdmin (JSON array or list of objects).
    Accepts table_type: 'general_enquiries' or 'popup_enquiries'.
    """
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Only administrators can import enquiry rows")

    rows = payload.get("rows")
    table_type = str(payload.get("table_type") or "general_enquiries").strip()

    if not rows or not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="rows must be a non-empty array of enquiry records")

    try:
        from services.website_mysql_sync import import_enquiry_rows_batch
        result = await import_enquiry_rows_batch(rows=rows, table_type=table_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import rows: {str(e)}")


@router.post("/sync-url")
async def sync_url_endpoint(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetches leads from a JSON export endpoint on live website (e.g. https://leamss.com/api/crm-website-leads-export)
    and syncs them into the CRM.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    url = str(payload.get("url") or "https://leamss.com/api/crm-website-leads-export").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    import httpx
    try:
        headers = {"User-Agent": "curl/8.7.1", "Accept": "*/*"}
        async with httpx.AsyncClient(timeout=30.0, verify=False, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Website returned status {resp.status_code}")
            data = resp.json()

        from services.website_mysql_sync import import_enquiry_rows_batch
        gen_rows = data.get("general") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        pop_rows = data.get("popups", []) if isinstance(data, dict) else []
        atlas_rows = (data.get("atlas") or data.get("atlas_leads") or []) if isinstance(data, dict) else []
        # Also fetch live Atlas leads from app.leamss.com if syncing main website
        if "leamss.com" in url and "public-atlas" not in url:
            try:
                async with httpx.AsyncClient(timeout=10.0, verify=False, headers=headers) as c2:
                    r2 = await c2.get("https://app.leamss.com/api/public-atlas/export-recent")
                    if r2.status_code == 200:
                        d2 = r2.json()
                        live_atlas = d2.get("atlas", []) if isinstance(d2, dict) else []
                        if live_atlas:
                            gen_rows = (gen_rows or []) + live_atlas
            except Exception:
                pass

        gen_res = await import_enquiry_rows_batch(gen_rows, "general_enquiries") if gen_rows else {"new_leads_inserted": 0}
        pop_res = await import_enquiry_rows_batch(pop_rows, "popup_enquiries") if pop_rows else {"new_leads_inserted": 0}

        # Also sync consultation registrations from connected Google Sheets
        sheet_inserted = 0
        sheet_updated = 0
        try:
            from services.integrations.google_services import fetch_sheets_leads
            from services.integrations.lead_ingestion_service import ingest_lead
            integrations = await db["integrations"].find({"provider": "google_sheets", "status": "connected"}).to_list(10)
            for integ in integrations:
                creds = integ.get("credentials") or {}
                company_id = integ.get("company_id") or "comp_leamss_primary"
                sheet_leads = await fetch_sheets_leads(creds, max_rows=50)
                for sl in sheet_leads:
                    try:
                        res = await ingest_lead(company_id, integ.get("id"), "google_sheets", sl)
                        if res.get("status") == "created":
                            sheet_inserted += 1
                        elif res.get("status") == "updated":
                            sheet_updated += 1
                    except Exception:
                        pass
        except Exception:
            pass

        total = gen_res["new_leads_inserted"] + pop_res["new_leads_inserted"] + sheet_inserted
        return {
            "success": True,
            "general_inserted": gen_res["new_leads_inserted"],
            "popup_inserted": pop_res["new_leads_inserted"],
            "consultation_inserted": sheet_inserted,
            "consultation_updated": sheet_updated,
            "total_new_leads": total,
            "message": f"Successfully synced {total} new leads and updated {sheet_updated} consultation payments from Google Sheets."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch leads from website: {str(e)}")


@router.post("/sync-now")
async def sync_now_endpoint(
    payload: Optional[Dict[str, Any]] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Instant one-click sync for live website enquiries into CRM."""
    body = payload or {}
    return await sync_url_endpoint(payload=body, current_user=current_user)




