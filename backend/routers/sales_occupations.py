"""Smart Sales Helper — Phase 6 v2 Part 1: Smart Occupation Search.

Deterministic rule-based occupation search across AU/CA/NZ knowledge base.
Uses rapidfuzz for typo-tolerant matching.

Endpoints:
  GET  /api/sales/occupations/search         — query + filters → ranked list
  GET  /api/sales/occupations/typeahead      — fast top-5 suggestions for autocomplete
  GET  /api/sales/occupations/{country}/{code} — detail with 6 tab payloads
  POST /api/sales/occupations/compare        — multi-code side-by-side
  GET  /api/sales/occupations/filters/meta   — distinct filter values (pathways/industries/skill_bodies)
"""
from typing import Optional, List, Dict, Any, Set
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process as fuzzproc

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/sales/occupations", tags=["Smart Sales Helper"])

country_rules_col = db["country_rules"]

ROLE_SALES = {
    "admin", "admin_owner", "sales_executive", "sr_sales_executive",
    "sales_manager", "sales_head", "partner", "case_manager",
}


def _user_role(user: dict) -> str:
    return user.get("rbac_role") or user.get("role") or ""


def _can_access(user: dict) -> bool:
    return _user_role(user) in ROLE_SALES or "*" in (user.get("permissions") or [])


# ════════════════════════════════════════════════════════════════
# Helpers — flatten all occupations across countries into a search index
# ════════════════════════════════════════════════════════════════
async def _load_all_occupations(country_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Returns a flat list of {country_code, ...occupation_fields, _search_blob}.
    Cached per-request; cheap enough for ~90 codes.
    """
    query: Dict[str, Any] = {}
    if country_filter:
        query["country_code"] = {"$in": [c.upper() for c in country_filter]}
    items: List[Dict[str, Any]] = []
    async for c in country_rules_col.find(query, {"_id": 0, "country_code": 1, "country": 1, "occupation_codes": 1}):
        country_code = c.get("country_code")
        country_name = c.get("country")
        for occ in (c.get("occupation_codes") or []):
            blob_parts = [
                occ.get("code", ""),
                occ.get("title", ""),
                occ.get("group", ""),
                occ.get("group_code", ""),
                " ".join(occ.get("alternative_titles") or []),
                occ.get("assessing_body", ""),
                occ.get("pathway", ""),
            ]
            items.append({
                "country_code": country_code,
                "country": country_name,
                "code": occ.get("code"),
                "title": occ.get("title"),
                "group": occ.get("group"),
                "group_code": occ.get("group_code"),
                "skill_level": occ.get("skill_level"),
                "assessing_body": occ.get("assessing_body"),
                "pathway": occ.get("pathway"),
                "eligible_visas": occ.get("eligible_visas") or [],
                "alternative_titles": occ.get("alternative_titles") or [],
                "state_demand": occ.get("state_demand") or {},
                "in_demand": _is_in_demand(occ.get("state_demand") or {}),
                "_search_blob": " ".join(p for p in blob_parts if p).lower(),
            })
    return items


def _is_in_demand(state_demand: Dict[str, str]) -> bool:
    """An occupation is 'in demand' if ANY state shows high or very_high."""
    if not state_demand:
        return False
    vals = {str(v or "").lower() for v in state_demand.values()}
    return bool(vals & {"high", "very_high", "very high"})


# ════════════════════════════════════════════════════════════════
# 1. SEARCH — main endpoint
# ════════════════════════════════════════════════════════════════
@router.get("/search")
async def search_occupations(
    q: Optional[str] = Query(None, description="Search query (fuzzy, typo-tolerant)"),
    country: Optional[List[str]] = Query(None, description="Country codes: AU, CA, NZ"),
    skill_level: Optional[int] = Query(None, ge=1, le=5),
    pathway: Optional[str] = Query(None, description="MLTSSL, STSOL, ROL, NOC TEER 0/1, SMC, etc."),
    in_demand: Optional[bool] = Query(None),
    industry: Optional[str] = Query(None),
    skill_body: Optional[str] = Query(None),
    state_code: Optional[str] = Query(None, description="Filter by state showing high demand (e.g., NSW, VIC, ON)"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Fuzzy search across code + title + alternative_titles + group + skill_body + pathway.
    Returns ranked list with confidence scores (0-100).
    """
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    items = await _load_all_occupations(country)

    # Apply structural filters first (fast)
    if skill_level is not None:
        items = [i for i in items if i.get("skill_level") == skill_level]
    if pathway:
        items = [i for i in items if (i.get("pathway") or "").upper() == pathway.upper()]
    if in_demand is not None:
        items = [i for i in items if i.get("in_demand") == in_demand]
    if industry:
        ind_l = industry.lower()
        items = [i for i in items if ind_l in (i.get("_search_blob") or "")]
    if skill_body:
        items = [i for i in items if (i.get("assessing_body") or "").upper() == skill_body.upper()]
    if state_code:
        sc = state_code.upper()
        items = [i for i in items if str((i.get("state_demand") or {}).get(sc) or "").lower() in ("high", "very_high", "very high")]

    # If no query, return all (sorted by in_demand + title)
    if not q or not q.strip():
        items.sort(key=lambda i: (not i.get("in_demand"), (i.get("title") or "").lower()))
        return {
            "items": [_strip_blob(i) | {"confidence": None} for i in items[:limit]],
            "count": len(items),
            "query": None,
        }

    # Fuzzy search via rapidfuzz
    query_l = q.strip().lower()
    scored = []
    for idx, item in enumerate(items):
        code = item.get("code") or ""
        title = (item.get("title") or "").lower()
        alts = [(a or "").lower() for a in (item.get("alternative_titles") or [])]
        group = (item.get("group") or "").lower()
        # Score against most-meaningful fields, take MAX
        blob_score = fuzz.WRatio(query_l, item["_search_blob"])
        title_score = fuzz.WRatio(query_l, title) if title else 0
        partial_title = fuzz.partial_ratio(query_l, title) if title else 0
        alt_score = max([fuzz.WRatio(query_l, a) for a in alts] or [0])
        group_score = fuzz.partial_ratio(query_l, group) if group else 0
        score = max(blob_score, title_score, partial_title, alt_score, group_score)
        # Boost: exact code match
        if query_l == code:
            score = 100
        # Boost: code starts with query
        elif code.startswith(query_l):
            score = max(score, 95)
        # Boost: title contains query as substring
        elif query_l in title:
            score = max(score, 90)
        # Boost: alt-title contains query
        elif any(query_l in a for a in alts):
            score = max(score, 85)
        scored.append((score, idx))

    scored.sort(key=lambda x: (-x[0], items[x[1]].get("title", "").lower()))
    # Threshold lowered to 50 for typo tolerance
    filtered = [(s, idx) for s, idx in scored if s >= 50]

    results = []
    for score, idx in filtered[:limit]:
        item = _strip_blob(items[idx])
        item["confidence"] = round(score)
        results.append(item)

    return {"items": results, "count": len(results), "query": q}


def _strip_blob(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if not k.startswith("_")}


# ════════════════════════════════════════════════════════════════
# 2. TYPEAHEAD — fast top-5 for autocomplete
# ════════════════════════════════════════════════════════════════
@router.get("/typeahead")
async def typeahead(
    q: str = Query(..., min_length=2),
    country: Optional[List[str]] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    items = await _load_all_occupations(country)
    query_l = q.strip().lower()
    blobs = [i["_search_blob"] for i in items]
    scored = []
    for idx, blob in enumerate(blobs):
        code = items[idx].get("code") or ""
        title = (items[idx].get("title") or "").lower()
        s = fuzz.WRatio(query_l, blob)
        if query_l == code: s = 100
        elif code.startswith(query_l): s = max(s, 95)
        elif query_l in title: s = max(s, 88)
        scored.append((s, idx))
    scored.sort(key=lambda x: -x[0])
    out = []
    for score, idx in scored[:5]:
        if score < 55:
            break
        i = items[idx]
        out.append({
            "country_code": i["country_code"],
            "code": i["code"],
            "title": i["title"],
            "assessing_body": i.get("assessing_body"),
            "pathway": i.get("pathway"),
            "score": round(score),
        })
    return {"items": out}


# ════════════════════════════════════════════════════════════════
# 5. FILTER META — distinct filter values for UI dropdowns
# (MUST be declared BEFORE /{country_code}/{code} so route resolves correctly)
# ════════════════════════════════════════════════════════════════
@router.get("/filters/meta")
async def filter_meta(current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    items = await _load_all_occupations(None)
    pathways: Set[str] = set()
    skill_bodies: Set[str] = set()
    industries: Set[str] = set()
    states_per_country: Dict[str, Set[str]] = {}
    for i in items:
        if i.get("pathway"):
            pathways.add(i["pathway"])
        if i.get("assessing_body"):
            skill_bodies.add(i["assessing_body"])
        for st in (i.get("state_demand") or {}).keys():
            states_per_country.setdefault(i["country_code"], set()).add(st)
        if i.get("group"):
            industries.add(i["group"])
    return {
        "countries": [
            {"code": "AU", "name": "Australia", "flag": "🇦🇺"},
            {"code": "CA", "name": "Canada", "flag": "🇨🇦"},
            {"code": "NZ", "name": "New Zealand", "flag": "🇳🇿"},
        ],
        "pathways": sorted(pathways),
        "skill_bodies": sorted(skill_bodies),
        "industries": sorted(industries)[:50],
        "skill_levels": [1, 2, 3, 4, 5],
        "states_by_country": {k: sorted(v) for k, v in states_per_country.items()},
    }


# ════════════════════════════════════════════════════════════════
# 6. COMPARE — side-by-side (POST, declared before dynamic GET path)
# ════════════════════════════════════════════════════════════════
class CompareItem(BaseModel):
    country_code: str
    code: str


class CompareRequest(BaseModel):
    items: List[CompareItem] = Field(..., min_length=2, max_length=4)


@router.post("/compare")
async def compare_occupations(req: CompareRequest, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    out = []
    for item in req.items:
        country = await country_rules_col.find_one({"country_code": item.country_code.upper()}, {"_id": 0})
        if not country:
            continue
        occ = next((o for o in (country.get("occupation_codes") or []) if str(o.get("code")) == str(item.code)), None)
        if not occ:
            continue
        body = None
        for b in (country.get("skill_assessment_bodies") or []):
            if str(occ.get("code")) in (b.get("assesses_occupations") or []):
                body = b
                break
        # Min points across eligible visas
        min_points = None
        max_age_limit = None
        for v in (country.get("visa_categories") or []):
            if v.get("code") in (occ.get("eligible_visas") or []):
                e = v.get("eligibility") or {}
                pts = e.get("points_minimum")
                if pts is not None and (min_points is None or pts < min_points):
                    min_points = pts
                age = e.get("age_max") or e.get("age_limit")
                if age and (max_age_limit is None or age > max_age_limit):
                    max_age_limit = age
        out.append({
            "country_code": item.country_code.upper(),
            "country": country.get("country"),
            "code": occ.get("code"),
            "title": occ.get("title"),
            "group": occ.get("group"),
            "skill_level": occ.get("skill_level"),
            "pathway": occ.get("pathway"),
            "assessing_body": occ.get("assessing_body"),
            "in_demand": _is_in_demand(occ.get("state_demand") or {}),
            "state_demand": occ.get("state_demand") or {},
            "eligible_visas_count": len(occ.get("eligible_visas") or []),
            "min_points_required": min_points,
            "age_limit": max_age_limit,
            "body_fee_native": (body or {}).get("fee_native"),
            "body_processing_weeks": (body or {}).get("processing_time_weeks"),
        })
    return {"items": out, "count": len(out)}


# ════════════════════════════════════════════════════════════════
# 7. DETAIL — full code info with 6 tabs (DYNAMIC path — keep LAST)
# ════════════════════════════════════════════════════════════════
@router.get("/{country_code}/{code}")
async def get_occupation_detail(
    country_code: str,
    code: str,
    current_user: dict = Depends(get_current_user),
):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    country = await country_rules_col.find_one({"country_code": country_code.upper()}, {"_id": 0})
    if not country:
        raise HTTPException(status_code=404, detail=f"Country '{country_code}' not in knowledge base")

    occupations = country.get("occupation_codes") or []
    occ = next((o for o in occupations if str(o.get("code")) == str(code)), None)
    if not occ:
        raise HTTPException(status_code=404, detail=f"Occupation code '{code}' not found in {country_code}")

    # Tab 1: Overview
    overview = {
        "code": occ.get("code"),
        "title": occ.get("title"),
        "group": occ.get("group"),
        "group_code": occ.get("group_code"),
        "skill_level": occ.get("skill_level"),
        "pathway": occ.get("pathway"),
        "alternative_titles": occ.get("alternative_titles") or [],
        "state_demand": occ.get("state_demand") or {},
        "in_demand": _is_in_demand(occ.get("state_demand") or {}),
        "typical_tasks": occ.get("typical_tasks") or _default_tasks(occ.get("title", "")),
        "salary_range": occ.get("salary_range"),
    }

    # Tab 2: Skill Assessment Body
    skill_body = None
    body_name = occ.get("assessing_body")
    if body_name:
        for b in (country.get("skill_assessment_bodies") or []):
            if (b.get("name") or "").upper() == body_name.upper() and str(occ.get("code")) in (b.get("assesses_occupations") or []):
                skill_body = {
                    "body_id": b.get("body_id"),
                    "name": b.get("name"),
                    "full_name": b.get("full_name"),
                    "website": b.get("website"),
                    "fee_native": b.get("fee_native"),
                    "assessment_fee_inr": b.get("assessment_fee_inr"),
                    "processing_time_weeks": b.get("processing_time_weeks"),
                    "documents_required": b.get("documents_required") or [],
                    "criteria_general": b.get("criteria_general") or {},
                    "contact_info": b.get("contact_info") or {},
                }
                break
        # Fallback: pick the first body that assesses this code (in case of name mismatch)
        if not skill_body:
            for b in (country.get("skill_assessment_bodies") or []):
                if str(occ.get("code")) in (b.get("assesses_occupations") or []):
                    skill_body = {
                        "body_id": b.get("body_id"),
                        "name": b.get("name"),
                        "full_name": b.get("full_name"),
                        "website": b.get("website"),
                        "fee_native": b.get("fee_native"),
                        "assessment_fee_inr": b.get("assessment_fee_inr"),
                        "processing_time_weeks": b.get("processing_time_weeks"),
                        "documents_required": b.get("documents_required") or [],
                        "criteria_general": b.get("criteria_general") or {},
                    }
                    break

    # Tab 3: Visa Pathways — all visas accepting this code
    eligible_visa_codes = set(occ.get("eligible_visas") or [])
    visa_pathways = []
    for v in (country.get("visa_categories") or []):
        if v.get("code") in eligible_visa_codes or _visa_accepts_pathway(v, occ.get("pathway")):
            elig = v.get("eligibility") or {}
            visa_pathways.append({
                "code": v.get("code"),
                "name": v.get("name"),
                "type": v.get("type"),
                "pathway_type": v.get("pathway_type"),
                "age_limit": elig.get("age_max") or elig.get("age_limit"),
                "points_minimum": elig.get("points_minimum"),
                "english_minimum": elig.get("english_minimum"),
                "experience_minimum_years": elig.get("experience_minimum_years"),
                "fee_inr": (v.get("cost") or {}).get("government_fee_inr"),
                "fee_native": (v.get("cost") or {}).get("government_fee_native"),
                "processing_time_months": v.get("processing_time_months"),
                "is_active": v.get("is_active", True),
                "description": v.get("description"),
            })

    # Tab 4: Document Checklist (rule-based, no AI)
    docs_checklist = _build_doc_checklist(occ, country, skill_body)

    # Tab 5: Similar Codes (same group + skill_body)
    similar = []
    for o in occupations:
        if o.get("code") == occ.get("code"):
            continue
        score = 0
        if o.get("group_code") == occ.get("group_code"):
            score += 50
        if o.get("assessing_body") == occ.get("assessing_body"):
            score += 30
        if o.get("pathway") == occ.get("pathway"):
            score += 20
        if score > 0:
            similar.append({
                "code": o.get("code"),
                "title": o.get("title"),
                "group": o.get("group"),
                "pathway": o.get("pathway"),
                "assessing_body": o.get("assessing_body"),
                "skill_level": o.get("skill_level"),
                "similarity_score": score,
            })
    similar.sort(key=lambda x: -x["similarity_score"])
    similar = similar[:8]

    return {
        "country_code": country.get("country_code"),
        "country": country.get("country"),
        "overview": overview,
        "skill_assessment": skill_body,
        "visa_pathways": visa_pathways,
        "document_checklist": docs_checklist,
        "similar_codes": similar,
        "sample_cases": [],  # Placeholder for future
    }


def _visa_accepts_pathway(visa: Dict[str, Any], pathway: Optional[str]) -> bool:
    if not pathway:
        return False
    vp = (visa.get("pathway_type") or "").upper()
    return vp == pathway.upper()


def _default_tasks(title: str) -> List[str]:
    """Generate generic task placeholders when seed doesn't have typical_tasks.
    Better seed data will replace these in the future.
    """
    t = (title or "").lower()
    if "manager" in t:
        return [
            "Lead and supervise a team of professionals",
            "Develop and implement strategic plans",
            "Manage budgets, resources and operational performance",
            "Liaise with stakeholders and senior leadership",
        ]
    if "engineer" in t or "developer" in t:
        return [
            "Design, develop and maintain technical solutions",
            "Collaborate with cross-functional teams on requirements",
            "Conduct code reviews and ensure quality standards",
            "Document architectures, technical specs and processes",
        ]
    if "specialist" in t or "analyst" in t:
        return [
            "Analyse data, trends and best practices in the domain",
            "Develop recommendations and execute initiatives",
            "Produce reports and presentations for stakeholders",
            "Stay current with industry standards and regulations",
        ]
    return [
        f"Perform core duties of a {title}",
        "Follow industry standards and best practices",
        "Maintain professional records and documentation",
        "Engage in continuous professional development",
    ]


def _build_doc_checklist(occ: Dict[str, Any], country: Dict[str, Any], skill_body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Rule-based document checklist for skill assessment + visa application."""
    common = [
        {"name": "Valid passport (bio page)", "required": True, "category": "identity"},
        {"name": "Passport-sized photographs", "required": True, "category": "identity"},
        {"name": "Birth certificate", "required": True, "category": "identity"},
        {"name": "Police clearance certificate", "required": True, "category": "character"},
        {"name": "Medical examination report", "required": True, "category": "health"},
        {"name": "English language test results (IELTS/PTE/TOEFL)", "required": True, "category": "english"},
        {"name": "Resume / CV (chronological)", "required": True, "category": "professional"},
    ]
    body_docs = []
    if skill_body and skill_body.get("documents_required"):
        body_docs = [{"name": d, "required": True, "category": "skill_assessment", "body": skill_body.get("name")} for d in skill_body["documents_required"]]
    education_docs = [
        {"name": "Degree certificate(s)", "required": True, "category": "education"},
        {"name": "Academic transcripts (all years)", "required": True, "category": "education"},
        {"name": "Equivalency certificate (if relevant)", "required": False, "category": "education"},
    ]
    employment_docs = [
        {"name": "Employment reference letters on company letterhead", "required": True, "category": "employment"},
        {"name": "Detailed role & responsibilities document", "required": True, "category": "employment"},
        {"name": "Payslips (recent 6 months)", "required": True, "category": "employment"},
        {"name": "Bank statements showing salary credit", "required": True, "category": "employment"},
        {"name": "Tax returns / Form 16 (if applicable)", "required": True, "category": "employment"},
        {"name": "PF / EPF statements", "required": False, "category": "employment"},
    ]
    return {
        "code": occ.get("code"),
        "title": occ.get("title"),
        "country": country.get("country_code"),
        "assessing_body": (skill_body or {}).get("name"),
        "categories": [
            {"name": "Identity & Personal", "docs": [d for d in common if d["category"] == "identity"]},
            {"name": "Education", "docs": education_docs},
            {"name": "Employment", "docs": employment_docs},
            {"name": "Skill Assessment", "docs": body_docs},
            {"name": "Character & Health", "docs": [d for d in common if d["category"] in ("character", "health")]},
            {"name": "English Proficiency", "docs": [d for d in common if d["category"] == "english"]},
            {"name": "Professional", "docs": [d for d in common if d["category"] == "professional"]},
        ],
        "total_docs": len(common) + len(education_docs) + len(employment_docs) + len(body_docs),
    }


# ════════════════════════════════════════════════════════════════
# (compare + filter_meta moved above the dynamic /{country_code}/{code} route)
# ════════════════════════════════════════════════════════════════
