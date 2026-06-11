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
# Phase 18.2 — full rewire to read from `occupation_master` directly so all
# admin-verified fields (qualification_rules, assessing_authority,
# required_documents, similar_codes_override, recommended_visa_subclass,
# sample_cases, custom_sections, verification_history) surface to sales.
# Legacy `country_rules` is now used only for: country name + visa catalogue
# metadata (subclass name / points / fee / age limit). Falls back to the
# legacy shape only when an occupation isn't yet in `occupation_master`.
# ════════════════════════════════════════════════════════════════
@router.get("/{country_code}/{code}")
async def get_occupation_detail(
    country_code: str,
    code: str,
    include_legacy: bool = Query(False, description="Also return the old legacy-shaped payload under `_legacy` for debugging."),
    current_user: dict = Depends(get_current_user),
):
    from datetime import datetime, timezone

    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    cc = country_code.upper()
    country = await country_rules_col.find_one({"country_code": cc}, {"_id": 0})
    name_map = await _country_names()
    country_name = (country or {}).get("country") or name_map.get(cc) or cc

    occ_master = await occupation_master_col.find_one(
        {"country_code": cc, "code": str(code), "status": {"$ne": "superseded"}},
        {"_id": 0},
    )
    # Graceful fallback: if occupation_master misses this code, return the legacy
    # shape so older codes don't 404 the page.
    if not occ_master:
        if not country:
            raise HTTPException(status_code=404, detail=f"Country '{country_code}' not in knowledge base")
        legacy = await _fetch_legacy_shaped_occupation(country_code, code)
        if not legacy:
            raise HTTPException(status_code=404, detail=f"Occupation code '{code}' not found in {country_code}")
        # Return a minimal compatible response shape with empty new sections
        return _build_minimal_legacy_response(legacy, country, country_name)

    # ─── Local helpers (closure-scoped) ───────────────────────────────────
    aa = occ_master.get("assessing_authority") or {}
    hierarchy = occ_master.get("hierarchy") or {}
    visa_pathways_raw = occ_master.get("visa_pathways") or {}
    pathway_lists = visa_pathways_raw.get("pathway_lists") or []
    primary_pathway = pathway_lists[0] if pathway_lists else None
    state_demand = {
        s.get("state"): s.get("demand")
        for s in (occ_master.get("state_territory_eligibility") or [])
        if s.get("state")
    }
    rvs = occ_master.get("recommended_visa_subclass") or {}
    recommended_subclass = rvs.get(cc) or ""

    # ─── overview ────────────────────────────────────────────────────────
    tasks = occ_master.get("typical_tasks") or []
    if not tasks:
        tasks = _default_tasks(occ_master.get("title", ""))
    overview = {
        "code": occ_master.get("code"),
        "title": occ_master.get("title"),
        "country_code": cc,
        "country_name": country_name,
        "group": hierarchy.get("unit_group_name"),
        "group_code": hierarchy.get("unit_group"),
        "skill_level": occ_master.get("skill_level"),
        "pathway": primary_pathway,
        "alternative_titles": occ_master.get("alternative_titles") or [],
        "description": occ_master.get("description") or "",
        "typical_tasks": tasks,
        "qualification_rules": occ_master.get("qualification_rules") or "",
        "custom_sections": occ_master.get("custom_sections") or [],
        "state_demand": state_demand,
        "in_demand": _is_in_demand(state_demand),
        "salary_range": (occ_master.get("skill_assessment_details") or {}).get("salary_range"),
    }

    # ─── skill_assessment — direct from occupation_master.assessing_authority ──
    skill_assessment = {
        "body_name": aa.get("name") or "",
        "body_short": aa.get("short_name") or aa.get("name") or "",
        "body_url": aa.get("url") or aa.get("website") or "",
        "processing_time_weeks": aa.get("processing_time_weeks"),
        "fee_native": aa.get("fee_native"),
        "fee_currency": aa.get("fee_currency") or "",
        "contact_details": aa.get("contact_details") or "",
        "rules_summary": aa.get("rules_summary") or "",
        "has_data": bool(aa.get("name")),
    }

    # ─── visa_pathways — merge occ_master eligibility flags w/ country catalogue ──
    elig_index = {
        (v.get("visa_subclass") or v.get("subclass") or v.get("code") or "").strip(): v
        for v in (visa_pathways_raw.get("visa_eligibility") or [])
    }
    visa_catalogue = {
        (v.get("code") or v.get("subclass") or "").strip(): v
        for v in ((country or {}).get("visa_categories") or [])
    }
    # Union of subclasses present in either source
    all_subclasses = list({*elig_index.keys(), *visa_catalogue.keys()})
    all_subclasses = [s for s in all_subclasses if s]

    visa_pathways = []
    for sub in all_subclasses:
        e = elig_index.get(sub) or {}
        cat = visa_catalogue.get(sub) or {}
        cat_elig = cat.get("eligibility") or {}
        cat_cost = cat.get("cost") or {}
        # eligible = either marker says true; if occ_master is missing this sub, treat as legacy-implied
        is_eligible = e.get("eligible") if "eligible" in e else (sub in elig_index)
        if not (is_eligible or sub in elig_index or sub in visa_catalogue):
            continue
        visa_pathways.append({
            "subclass": sub,
            "name": e.get("visa_name") or cat.get("name") or sub,
            "eligible": bool(is_eligible),
            "pathway_type": e.get("pathway_type") or cat.get("pathway_type") or "",
            "is_recommended": bool(recommended_subclass) and sub == recommended_subclass,
            "points_minimum": e.get("points_minimum") if e.get("points_minimum") is not None else cat_elig.get("points_minimum"),
            "age_limit": e.get("age_limit") or cat_elig.get("age_max") or cat_elig.get("age_limit"),
            "experience_required": e.get("experience_required") or cat_elig.get("experience_minimum_years") or "",
            "english_minimum": cat_elig.get("english_minimum"),
            "fee_native": cat_cost.get("government_fee_native"),
            "fee_inr": cat_cost.get("government_fee_inr"),
            "processing_time_months": cat.get("processing_time_months"),
        })
    # Sort: recommended first → eligible → subclass alphabetical
    visa_pathways.sort(key=lambda x: (
        0 if x.get("is_recommended") else 1,
        0 if x.get("eligible") else 1,
        (x.get("subclass") or "").lower(),
    ))

    # ─── documents — filter by country_override ──────────────────────────
    doc_items: List[Dict[str, Any]] = []
    by_category: Dict[str, int] = {}
    for d in occ_master.get("required_documents") or []:
        co = d.get("country_override")
        if co and co.upper() != cc:
            continue  # skip docs scoped to a different country
        doc_items.append(d)
        cat = d.get("category") or "Other"
        by_category[cat] = by_category.get(cat, 0) + 1
    documents = {
        "items": doc_items,
        "total": len(doc_items),
        "by_category": by_category,
        "filtered_by_country": True,
    }
    # Back-compat alias for legacy frontend (until Tab 4 rewire ships)
    document_checklist = {
        "code": occ_master.get("code"),
        "title": occ_master.get("title"),
        "country": cc,
        "categories": [{"name": k, "docs": [d for d in doc_items if (d.get("category") or "Other") == k]} for k in by_category],
        "total_docs": len(doc_items),
    }

    # ─── similar — override priority → auto top-up to 8 ──────────────────
    similar: List[Dict[str, Any]] = []
    seen_slugs: Set[str] = set()
    own_slug = f"{cc.lower()}-{occ_master.get('code')}"
    seen_slugs.add(own_slug)

    overrides = occ_master.get("similar_codes_override") or []
    for slug in overrides:
        slug = (slug or "").strip().lower()
        if not slug or slug in seen_slugs:
            continue
        sub_cc, _, sub_code = slug.partition("-")
        if not (sub_cc and sub_code):
            continue
        pinned = await occupation_master_col.find_one(
            {"country_code": sub_cc.upper(), "code": sub_code, "status": {"$ne": "superseded"}},
            {"_id": 0, "code": 1, "title": 1, "country_code": 1, "assessing_authority": 1, "hierarchy": 1, "visa_pathways": 1, "skill_level": 1},
        )
        if not pinned:
            continue
        p_aa = pinned.get("assessing_authority") or {}
        p_hier = pinned.get("hierarchy") or {}
        p_pathway = ((pinned.get("visa_pathways") or {}).get("pathway_lists") or [None])[0]
        similar.append({
            "country_code": pinned.get("country_code"),
            "code": pinned.get("code"),
            "title": pinned.get("title"),
            "group": p_hier.get("unit_group_name"),
            "pathway": p_pathway,
            "assessing_body": p_aa.get("name"),
            "skill_level": pinned.get("skill_level"),
            "is_override": True,
            "similarity_score": 100,
        })
        seen_slugs.add(slug)
        if len(similar) >= 8:
            break

    auto_slots = 8 - len(similar)
    if auto_slots > 0:
        own_group = hierarchy.get("unit_group")
        own_body = aa.get("name")
        async for o in occupation_master_col.find(
            {"country_code": cc, "code": {"$ne": occ_master.get("code")}, "status": {"$ne": "superseded"}},
            {"_id": 0, "code": 1, "title": 1, "country_code": 1, "assessing_authority": 1, "hierarchy": 1, "visa_pathways": 1, "skill_level": 1},
        ):
            o_slug = f"{(o.get('country_code') or '').lower()}-{o.get('code')}"
            if o_slug in seen_slugs:
                continue
            o_aa = o.get("assessing_authority") or {}
            o_hier = o.get("hierarchy") or {}
            o_pathway = ((o.get("visa_pathways") or {}).get("pathway_lists") or [None])[0]
            score = 0
            if own_group and o_hier.get("unit_group") == own_group:
                score += 50
            if own_body and o_aa.get("name") == own_body:
                score += 30
            if primary_pathway and o_pathway == primary_pathway:
                score += 20
            if score > 0:
                similar.append({
                    "country_code": o.get("country_code"),
                    "code": o.get("code"),
                    "title": o.get("title"),
                    "group": o_hier.get("unit_group_name"),
                    "pathway": o_pathway,
                    "assessing_body": o_aa.get("name"),
                    "skill_level": o.get("skill_level"),
                    "is_override": False,
                    "similarity_score": score,
                })
                seen_slugs.add(o_slug)
        # Sort the auto portion by score desc and cap at 8 total
        overrides_pinned = [s for s in similar if s.get("is_override")]
        auto_only = sorted([s for s in similar if not s.get("is_override")], key=lambda x: -x.get("similarity_score", 0))
        similar = (overrides_pinned + auto_only)[:8]

    # ─── sample_cases ────────────────────────────────────────────────────
    sample_cases = occ_master.get("sample_cases") or []

    # ─── verification_meta ───────────────────────────────────────────────
    ver = occ_master.get("verification") or {}
    verified_at_raw = ver.get("verified_at")
    verified_at_iso = None
    days_since = None
    if verified_at_raw:
        if hasattr(verified_at_raw, "isoformat"):
            verified_at_dt = verified_at_raw
        else:
            try:
                verified_at_dt = datetime.fromisoformat(str(verified_at_raw).replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001
                verified_at_dt = None
        if verified_at_dt:
            if verified_at_dt.tzinfo is None:
                verified_at_dt = verified_at_dt.replace(tzinfo=timezone.utc)
            verified_at_iso = verified_at_dt.isoformat()
            days_since = (datetime.now(timezone.utc) - verified_at_dt).days
    verification_meta = {
        "is_verified": bool(ver.get("is_verified")) or occ_master.get("status") == "verified",
        "verified_at": verified_at_iso,
        "verified_by_name": ver.get("verified_by_name") or ver.get("verified_by") or "",
        "source_reference": ver.get("source_reference") or "",
        "verification_count": len(occ_master.get("verification_history") or []),
        "days_since_verified": days_since,
    }

    response: Dict[str, Any] = {
        "country_code": cc,
        "country": country_name,
        "overview": overview,
        "skill_assessment": skill_assessment,
        "visa_pathways": visa_pathways,
        "documents": documents,
        "document_checklist": document_checklist,  # back-compat alias
        "similar": similar,
        "similar_codes": similar,                  # back-compat alias
        "sample_cases": sample_cases,
        "verification_meta": verification_meta,
    }

    if include_legacy:
        try:
            legacy_doc = await _fetch_legacy_shaped_occupation(country_code, code)
            response["_legacy"] = legacy_doc
        except Exception:  # noqa: BLE001
            response["_legacy"] = None

    return response


def _build_minimal_legacy_response(legacy: Dict[str, Any], country: Dict[str, Any], country_name: str) -> Dict[str, Any]:
    """Phase 18.2 — when occupation_master is missing this code, return a minimal
    new-shape response built from the legacy adapter so the page still renders
    without errors."""
    return {
        "country_code": (country or {}).get("country_code") or "",
        "country": country_name,
        "overview": {
            "code": legacy.get("code"),
            "title": legacy.get("title"),
            "country_code": (country or {}).get("country_code") or "",
            "country_name": country_name,
            "group": legacy.get("group"),
            "group_code": legacy.get("group_code"),
            "skill_level": legacy.get("skill_level"),
            "pathway": legacy.get("pathway"),
            "alternative_titles": legacy.get("alternative_titles") or [],
            "description": legacy.get("description") or "",
            "typical_tasks": legacy.get("typical_tasks") or _default_tasks(legacy.get("title", "")),
            "qualification_rules": "",
            "custom_sections": [],
            "state_demand": legacy.get("state_demand") or {},
            "in_demand": _is_in_demand(legacy.get("state_demand") or {}),
            "salary_range": legacy.get("salary_range"),
        },
        "skill_assessment": {
            "body_name": legacy.get("assessing_body") or "",
            "body_short": legacy.get("assessing_body") or "",
            "body_url": "", "processing_time_weeks": None, "fee_native": None,
            "fee_currency": "", "contact_details": "", "rules_summary": "",
            "has_data": bool(legacy.get("assessing_body")),
        },
        "visa_pathways": [],
        "documents": {"items": [], "total": 0, "by_category": {}, "filtered_by_country": True},
        "document_checklist": {"categories": [], "total_docs": 0},
        "similar": [],
        "similar_codes": [],
        "sample_cases": [],
        "verification_meta": {"is_verified": False, "verified_at": None, "verified_by_name": "",
                              "source_reference": "", "verification_count": 0, "days_since_verified": None},
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
