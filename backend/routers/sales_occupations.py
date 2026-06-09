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

# Phase 6.9.1 — Single Source of Truth migration.
# Reads now come from `occupation_master` instead of `country_rules.occupation_codes`.
# `country_rules` is still used for: country-level display name + visa_categories list
# (those move into the new schema in Phase 6.9.5 Country Template, not now).
country_rules_col = db["country_rules"]
occupation_master_col = db["occupation_master"]
skill_body_master_col = db["skill_body_master"]

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
_COUNTRY_NAME_CACHE: Dict[str, str] = {}


async def _country_names() -> Dict[str, str]:
    """Cache map of country_code → human-readable country name (for UI labels)."""
    if _COUNTRY_NAME_CACHE:
        return _COUNTRY_NAME_CACHE
    async for c in country_rules_col.find({}, {"_id": 0, "country_code": 1, "country": 1}):
        if c.get("country_code"):
            _COUNTRY_NAME_CACHE[c["country_code"]] = c.get("country") or c["country_code"]
    return _COUNTRY_NAME_CACHE


def _from_master(occ: Dict[str, Any], country_name: str) -> Dict[str, Any]:
    """Phase 6.9.1 — adapter: map occupation_master document → legacy search-row shape.

    Output shape is intentionally identical to the pre-migration `country_rules.occupation_codes[i]`
    rows so every downstream endpoint (search/typeahead/detail/compare/filters) continues to work
    unchanged. The only producer that needed touching was `_load_all_occupations` itself.
    """
    aa = occ.get("assessing_authority") or {}
    hierarchy = occ.get("hierarchy") or {}
    visa_pathways = occ.get("visa_pathways") or {}
    pathway_lists = visa_pathways.get("pathway_lists") or []
    # eligible_visas[] ← visa_pathways.visa_eligibility[] where eligible=true
    eligible_visas = [
        v.get("visa_subclass")
        for v in (visa_pathways.get("visa_eligibility") or [])
        if v.get("eligible") and v.get("visa_subclass")
    ]
    # state_demand{} ← state_territory_eligibility[]
    state_demand = {
        s.get("state"): s.get("demand")
        for s in (occ.get("state_territory_eligibility") or [])
        if s.get("state")
    }
    blob_parts = [
        occ.get("code", ""),
        occ.get("title", ""),
        hierarchy.get("unit_group_name", ""),
        hierarchy.get("unit_group", ""),
        " ".join(occ.get("alternative_titles") or []),
        aa.get("name", ""),
        pathway_lists[0] if pathway_lists else "",
    ]
    return {
        "country_code": occ.get("country_code"),
        "country": country_name,
        "code": occ.get("code"),
        "title": occ.get("title"),
        "group": hierarchy.get("unit_group_name"),
        "group_code": hierarchy.get("unit_group"),
        "skill_level": occ.get("skill_level"),
        "assessing_body": aa.get("name"),
        "pathway": pathway_lists[0] if pathway_lists else None,
        "eligible_visas": eligible_visas,
        "alternative_titles": occ.get("alternative_titles") or [],
        "state_demand": state_demand,
        "in_demand": _is_in_demand(state_demand),
        # New 6.9.1 fields surfaced (UI may use them later)
        "status": occ.get("status"),
        "classification_type": occ.get("classification_type"),
        "_search_blob": " ".join(p for p in blob_parts if p).lower(),
    }


async def _load_all_occupations(country_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Returns a flat list of search-row dicts. Reads from occupation_master (Phase 6.9.1).

    Transition policy: no status filter is applied here. Sales sees all rows
    (draft + verified + outdated) so the search never empties during the
    migration period. Phase 6.9.4 will gate this once admin verification
    reaches the configurable threshold (default 90%).
    """
    name_map = await _country_names()
    query: Dict[str, Any] = {"status": {"$ne": "superseded"}}  # always hide soft-deleted
    if country_filter:
        query["country_code"] = {"$in": [c.upper() for c in country_filter]}
    items: List[Dict[str, Any]] = []
    async for occ in occupation_master_col.find(query, {"_id": 0}):
        country_name = name_map.get(occ.get("country_code")) or occ.get("country_code") or ""
        items.append(_from_master(occ, country_name))
    return items


async def _fetch_legacy_shaped_occupation(country_code: str, code: str) -> Optional[Dict[str, Any]]:
    """Phase 6.9.1 — adapter for the detail / compare endpoints.

    Returns a dict shaped like the OLD `country_rules.occupation_codes[i]` entry
    so the existing detail-builder logic stays unchanged. Read source is now
    `occupation_master`. Returns None if the code isn't found.
    """
    occ = await occupation_master_col.find_one(
        {"country_code": country_code.upper(), "code": str(code), "status": {"$ne": "superseded"}},
        {"_id": 0},
    )
    if not occ:
        return None
    aa = occ.get("assessing_authority") or {}
    hierarchy = occ.get("hierarchy") or {}
    visa_pathways = occ.get("visa_pathways") or {}
    pathway_lists = visa_pathways.get("pathway_lists") or []
    eligible_visas = [
        v.get("visa_subclass")
        for v in (visa_pathways.get("visa_eligibility") or [])
        if v.get("eligible") and v.get("visa_subclass")
    ]
    state_demand = {
        s.get("state"): s.get("demand")
        for s in (occ.get("state_territory_eligibility") or [])
        if s.get("state")
    }
    return {
        "code": occ.get("code"),
        "title": occ.get("title"),
        "group": hierarchy.get("unit_group_name"),
        "group_code": hierarchy.get("unit_group"),
        "skill_level": occ.get("skill_level"),
        "assessing_body": aa.get("name"),
        "pathway": pathway_lists[0] if pathway_lists else None,
        "alternative_titles": occ.get("alternative_titles") or [],
        "eligible_visas": eligible_visas,
        "state_demand": state_demand,
        "typical_tasks": occ.get("typical_tasks") or [],
        "salary_range": (occ.get("skill_assessment_details") or {}).get("salary_range"),
        # Surface new 6.9.1 fields for UI that wants them
        "status": occ.get("status"),
        "classification_type": occ.get("classification_type"),
        "classification_version": occ.get("classification_version"),
        "description": occ.get("description"),
    }


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
    items: List[CompareItem] = Field(..., min_length=2, max_length=5)


def _compute_best_fit_score(item: dict) -> int:
    """Higher = better-fit candidate. Used for ranking + green-highlight in UI.

    Scoring rubric (transparent, country-agnostic):
      • In-demand              → +20
      • Min points required low → +(100 - min_points/2) cap +50
      • Lower age_limit penalty → +(age_limit - 30) cap +15
      • Atlas data present     → +5 each (TEER label, EE eligibility, PNP/state count)
      • PNPs/States count      → +(count * 3) cap +30
      • Federal program eligibility (CA) → +10 per (FSWP/CEC/FSTP)
      • SkillSelect Tier 1     → +15 (AU)
      • Round cutoffs available → +5
      • Regional pilots / DAMA / ILA → +(count * 2) cap +15
      • Quebec eligible (CA)   → +10 (extra optionality)
    """
    score = 0
    if item.get("in_demand"):
        score += 20
    if (mp := item.get("min_points_required")) is not None:
        score += max(0, min(50, 100 - int(mp) // 2))
    if (al := item.get("age_limit")) is not None:
        score += max(0, min(15, int(al) - 30))

    atlas = item.get("atlas") or {}
    if atlas.get("teer_label"):
        score += 5
    ee = atlas.get("ee_eligibility") or {}
    for k in ("fswp_eligible", "cec_eligible", "fstp_eligible"):
        if ee.get(k):
            score += 10
    pnps = atlas.get("pnp_eligibility") or []
    score += min(30, len(pnps) * 3)
    states = atlas.get("state_nomination") or {}
    score += min(30, sum(1 for v in states.values() if v) * 3)

    tier = (atlas.get("skillselect_tier") or "").lower()
    if "tier_1" in tier or "tier 1" in tier:
        score += 15

    if atlas.get("ircc_round_cutoffs"):
        score += 5

    regional = atlas.get("regional_pilot_eligibility") or []
    score += min(15, len(regional) * 2)
    dama = atlas.get("dama_eligibility") or []
    ila = atlas.get("ila_eligibility") or []
    score += min(15, (len(dama) + len(ila)) * 2)

    qc = atlas.get("quebec_eligibility") or {}
    if qc.get("eligible"):
        score += 10
        # Priority section gives extra bonus
        if any(s.get("priority") for s in (qc.get("sections") or [])):
            score += 5

    return score


@router.post("/compare")
async def compare_occupations(req: CompareRequest, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    out = []
    for item in req.items:
        country = await country_rules_col.find_one({"country_code": item.country_code.upper()}, {"_id": 0})
        if not country:
            continue
        # Phase 6.9.1 — read occupation from occupation_master via adapter
        occ = await _fetch_legacy_shaped_occupation(item.country_code, item.code)
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

    # Phase 10 — append rich atlas data per item (TEER + EE + PNPs + Quebec + cutoffs)
    for o in out:
        atlas_doc = await occupation_master_col.find_one(
            {"country_code": o["country_code"], "code": o["code"]},
            {
                "_id": 0,
                "teer_category": 1, "teer_label": 1,
                "ee_eligibility": 1, "pnp_eligibility": 1,
                "ircc_round_cutoffs": 1, "regional_pilot_eligibility": 1,
                "quebec_eligibility": 1,
                "skillselect_tier": 1, "assessing_authority": 1,
                "state_nomination": 1, "min_invitation_points": 1,
                "visa_pathways": 1, "hierarchy": 1, "classification_version": 1,
                "dama_eligibility": 1, "ila_eligibility": 1,
            },
        )
        if atlas_doc:
            o["atlas"] = atlas_doc

    # Phase 10 — compute best-fit score for green highlight
    for o in out:
        o["best_fit_score"] = _compute_best_fit_score(o)

    # Mark the highest-scoring item as best_fit=True
    if out:
        max_score = max(o["best_fit_score"] for o in out)
        for o in out:
            o["best_fit"] = (o["best_fit_score"] == max_score and max_score > 0)

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

    # Phase 6.9.1 — occupation read from occupation_master via adapter
    occ = await _fetch_legacy_shaped_occupation(country_code, code)
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

    # Tab 5: Similar Codes (same group + skill_body) — Phase 6.9.1: query master directly
    similar = []
    similar_query = {
        "country_code": country_code.upper(),
        "code": {"$ne": occ.get("code")},
        "status": {"$ne": "superseded"},
    }
    async for o in occupation_master_col.find(similar_query, {"_id": 0}):
        o_aa = o.get("assessing_authority") or {}
        o_hier = o.get("hierarchy") or {}
        o_pathway = ((o.get("visa_pathways") or {}).get("pathway_lists") or [None])[0]
        score = 0
        if o_hier.get("unit_group") == occ.get("group_code"):
            score += 50
        if o_aa.get("name") == occ.get("assessing_body"):
            score += 30
        if o_pathway == occ.get("pathway"):
            score += 20
        if score > 0:
            similar.append({
                "code": o.get("code"),
                "title": o.get("title"),
                "group": o_hier.get("unit_group_name"),
                "pathway": o_pathway,
                "assessing_body": o_aa.get("name"),
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
