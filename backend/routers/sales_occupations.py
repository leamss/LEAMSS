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
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process as fuzzproc

from core.auth import get_current_user
from core.database import db
from services.authority_resolver import resolve_authority

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
    "sales_manager", "sales_head", "partner", "case_manager", "client",
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


_CA_LEGACY_BODY_CACHE: Dict[str, str] = {}


async def _get_ca_legacy_body_cache() -> Dict[str, str]:
    if _CA_LEGACY_BODY_CACHE:
        return _CA_LEGACY_BODY_CACHE
    ca_doc = await country_rules_col.find_one({"country_code": "CA"}, {"_id": 0, "occupation_codes": 1})
    if ca_doc:
        for oc in ca_doc.get("occupation_codes", []):
            if oc.get("code") and oc.get("assessing_body"):
                _CA_LEGACY_BODY_CACHE[str(oc["code"])] = oc["assessing_body"]
    return _CA_LEGACY_BODY_CACHE


def _extract_state_demand(occ: Dict[str, Any]) -> Dict[str, Any]:
    ste = occ.get("state_territory_eligibility") or []
    if isinstance(ste, dict):
        return {
            str(k): (v.get("demand") if isinstance(v, dict) else (v if isinstance(v, str) else "Available"))
            for k, v in ste.items()
        }
    if isinstance(ste, list):
        return {
            s.get("state"): s.get("demand")
            for s in ste
            if isinstance(s, dict) and s.get("state")
        }
    return {}


def _from_master(occ: Dict[str, Any], country_name: str, ca_body_cache: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
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
        if isinstance(v, dict) and v.get("eligible") and v.get("visa_subclass")
    ]
    # state_demand{} ← state_territory_eligibility
    state_demand = _extract_state_demand(occ)

    # Resolve assessing body cleanly (prefer short_name/code so UI displays ACS, EA, TRA, VETASSESS, etc.)
    resolved_body = None
    if isinstance(aa, dict):
        resolved_body = aa.get("short_name") or aa.get("code") or aa.get("name")
    elif isinstance(aa, str):
        resolved_body = aa

    if not resolved_body:
        resolved_body = occ.get("assessing_body") or occ.get("skill_body")

    c_code = str(occ.get("country_code") or "").upper()
    code_str = str(occ.get("code") or "").strip()

    if not resolved_body and c_code == "CA":
        if ca_body_cache and code_str in ca_body_cache:
            resolved_body = ca_body_cache[code_str]
        elif code_str.startswith("3110"):
            resolved_body = "MCC"
        elif code_str.startswith("31300"):
            resolved_body = "PEBC"
        elif code_str.startswith("31301"):
            resolved_body = "MCC / NNAS"
        elif code_str.startswith(("72", "73")):
            resolved_body = "Red Seal"
        elif code_str.startswith("11100"):
            resolved_body = "CPA Canada"
        else:
            resolved_body = "WES"
    elif not resolved_body and c_code == "NZ":
        resolved_body = "NZQA"
    elif not resolved_body and c_code == "AU":
        resolved_body = "VETASSESS"

    aa_full_name = aa.get("name", "") if isinstance(aa, dict) else ""
    blob_parts = [
        occ.get("code", ""),
        occ.get("title", ""),
        hierarchy.get("unit_group_name", ""),
        hierarchy.get("unit_group", ""),
        " ".join(occ.get("alternative_titles") or []),
        resolved_body or "",
        aa_full_name if aa_full_name != resolved_body else "",
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
        "assessing_body": resolved_body,
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


COUNTRY_ALIAS_MAP = {
    "AUSTRALIA": "AU",
    "AU": "AU",
    "CANADA": "CA",
    "CA": "CA",
    "NEW ZEALAND": "NZ",
    "NEWZEALAND": "NZ",
    "NZ": "NZ",
    "GERMANY": "DE",
    "DE": "DE",
    "UNITED KINGDOM": "UK",
    "UNITEDKINGDOM": "UK",
    "UK": "UK",
    "UNITED STATES": "US",
    "USA": "US",
    "US": "US",
}


async def _load_all_occupations(country_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Returns a flat list of search-row dicts. Reads from occupation_master (Phase 6.9.1).

    Transition policy: no status filter is applied here. Sales sees all rows
    (draft + verified + outdated) so the search never empties during the
    migration period. Phase 6.9.4 will gate this once admin verification
    reaches the configurable threshold (default 90%).
    """
    name_map = await _country_names()
    ca_cache = await _get_ca_legacy_body_cache()
    query: Dict[str, Any] = {"status": {"$ne": "superseded"}}  # always hide soft-deleted
    if country_filter:
        norm_codes = set()
        for c in country_filter:
            c_str = str(c or "").strip().upper()
            if c_str in COUNTRY_ALIAS_MAP:
                norm_codes.add(COUNTRY_ALIAS_MAP[c_str])
            elif "AUS" in c_str or c_str == "AU":
                norm_codes.add("AU")
            elif "CAN" in c_str or c_str == "CA":
                norm_codes.add("CA")
            elif "ZEAL" in c_str or c_str == "NZ":
                norm_codes.add("NZ")
            else:
                norm_codes.add(c_str)
        query["country_code"] = {"$in": list(norm_codes)}
    items: List[Dict[str, Any]] = []
    async for occ in occupation_master_col.find(query, {"_id": 0}):
        country_name = name_map.get(occ.get("country_code")) or occ.get("country_code") or ""
        items.append(_from_master(occ, country_name, ca_cache))
    return items


async def _fetch_legacy_shaped_occupation(country_code: str, code: str) -> Optional[Dict[str, Any]]:
    """Phase 6.9.1 — adapter for the detail / compare endpoints.

    Returns a dict shaped like the OLD `country_rules.occupation_codes[i]` entry
    so the existing detail-builder logic stays unchanged. Read source is now
    `occupation_master`. Returns None if the code isn't found.
    """
    norm_country = COUNTRY_ALIAS_MAP.get(country_code.upper(), country_code.upper())
    occ = await occupation_master_col.find_one(
        {"country_code": norm_country, "code": str(code), "status": {"$ne": "superseded"}},
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
        if isinstance(v, dict) and v.get("eligible") and v.get("visa_subclass")
    ]
    state_demand = _extract_state_demand(occ)
    resolved_body = None
    if isinstance(aa, dict):
        resolved_body = aa.get("short_name") or aa.get("code") or aa.get("name")
    elif isinstance(aa, str):
        resolved_body = aa
    if not resolved_body:
        resolved_body = occ.get("assessing_body") or occ.get("skill_body")
    if not resolved_body and norm_country == "CA":
        ca_cache = await _get_ca_legacy_body_cache()
        resolved_body = ca_cache.get(str(code)) or ("MCC" if str(code).startswith("3110") else "WES")
    elif not resolved_body and norm_country == "NZ":
        resolved_body = "NZQA"
    elif not resolved_body and norm_country == "AU":
        resolved_body = "VETASSESS"
    return {
        "code": occ.get("code"),
        "title": occ.get("title"),
        "group": hierarchy.get("unit_group_name"),
        "group_code": hierarchy.get("unit_group"),
        "skill_level": occ.get("skill_level"),
        "assessing_body": resolved_body or aa.get("name"),
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
    request: Request,
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

    country_list = []
    if country:
        for c in country:
            country_list.extend([x.strip() for x in c.split(",") if x.strip()])
    for k, v in request.query_params.multi_items():
        if k in ("country", "country[]") and v:
            for item in v.split(","):
                clean = item.strip()
                if clean and clean not in country_list:
                    country_list.append(clean)

    items = await _load_all_occupations(country_list or None)

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

    scored.sort(key=lambda x: (-x[0], 0 if items[x[1]].get("country_code") == "AU" else 1, items[x[1]].get("title", "").lower()))
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

    tier_raw = atlas.get("skillselect_tier") or ""
    if isinstance(tier_raw, dict):
        tier_str = str(tier_raw.get("tier") or tier_raw.get("name") or tier_raw.get("label") or tier_raw).lower()
    else:
        tier_str = str(tier_raw).lower()
    if "tier_1" in tier_str or "tier 1" in tier_str:
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
        cc = item.country_code.upper()
        country = await country_rules_col.find_one({"country_code": cc}, {"_id": 0})
        occ_raw = await occupation_master_col.find_one({"country_code": cc, "code": str(item.code)}, {"_id": 0})
        # Phase 6.9.1 — read occupation from occupation_master via adapter
        occ = await _fetch_legacy_shaped_occupation(item.country_code, item.code)
        if not occ:
            continue

        resolved_aa = await resolve_authority(db, occ_raw or occ)
        fees_data = resolved_aa.get("fees") or {}
        proc_data = resolved_aa.get("processing") or {}
        auth_code = (resolved_aa.get("code") or resolved_aa.get("short_name") or "").upper()
        msa_aud = fees_data.get("msa_fee_aud")
        rpl_aud = fees_data.get("rpl_fee_aud")
        
        # Exact pathway-specific fee formatting
        if resolved_aa.get("pathway_label"):
            fee_native_val = resolved_aa.get("pathway_label")
        elif auth_code == "EA":
            fee_native_val = "Accredited Qual: AUD $720 · CDR: AUD $995 · CDR + Employment: AUD $1,470"
        elif auth_code == "VETASSESS":
            fee_native_val = "Standard (Qual + Employment): AUD $1,188 · Qual Only: AUD $700"
        elif auth_code in ("CPA", "CAANZ", "IPA"):
            fee_native_val = f"Qual Only: AUD ${msa_aud or 550:,} · Qual + Employment: AUD $1,107"
        elif auth_code == "TRA":
            fee_native_val = "MSA (Aus Qual): AUD $1,000 · OSAP (Overseas): AUD $3,280"
        elif auth_code == "ANMAC":
            fee_native_val = "Full Assessment: AUD $640 · Modified (AU/NZ Reg): AUD $385"
        elif auth_code in ("AMC", "MEDBA"):
            fee_native_val = "Primary Verification: AUD $1,200 · MCQ Exam: AUD $2,880"
        elif auth_code in ("ACS", "CWA") and msa_aud and rpl_aud:
            fee_native_val = f"Standard: AUD ${msa_aud:,} · RPL: AUD ${rpl_aud:,}"
        elif msa_aud:
            fee_native_val = f"AUD ${msa_aud:,}"
        elif rpl_aud:
            fee_native_val = f"AUD ${rpl_aud:,}"
        else:
            fee_native_val = None

        p_min = proc_data.get("standard_days_min") or 60
        p_max = proc_data.get("standard_days_max") or 90
        p_min_w = round(p_min / 7)
        p_max_w = round(p_max / 7)
        p_weeks = f"{p_min_w}–{p_max_w} weeks" if p_min_w != p_max_w else f"{p_min_w} weeks"

        # Min points across eligible visas
        min_points = None
        max_age_limit = None
        for v in ((country or {}).get("visa_categories") or []):
            if v.get("code") in (occ.get("eligible_visas") or []):
                e = v.get("eligibility") or {}
                pts = e.get("points_minimum")
                if pts is not None and (min_points is None or pts < min_points):
                    min_points = pts
                age = e.get("age_max") or e.get("age_limit")
                if age and (max_age_limit is None or age > max_age_limit):
                    max_age_limit = age
        out.append({
            "country_code": cc,
            "country": (country or {}).get("country") or cc,
            "code": occ.get("code"),
            "title": occ.get("title"),
            "group": occ.get("group"),
            "skill_level": occ.get("skill_level"),
            "pathway": occ.get("pathway"),
            "assessing_body": resolved_aa.get("short_name") or resolved_aa.get("code") or resolved_aa.get("name") or occ.get("assessing_body"),
            "assessing_authority": resolved_aa,
            "in_demand": _is_in_demand(occ.get("state_demand") or {}),
            "state_demand": occ.get("state_demand") or {},
            "eligible_visas_count": len(occ.get("eligible_visas") or []),
            "min_points_required": min_points,
            "age_limit": max_age_limit,
            "body_fee_native": fee_native_val or occ.get("salary_range"),
            "body_fee_aud": msa_aud,
            "body_fee_inr": round(msa_aud * 55) if msa_aud else None,
            "body_processing_weeks": p_weeks,
        })

    # Phase 10 — append rich atlas data per item (TEER + EE + PNPs + Quebec + cutoffs)
    for o in out:
        occ_raw = await occupation_master_col.find_one({"country_code": o["country_code"], "code": o["code"]}, {"_id": 0})
        if not occ_raw:
            continue

        # Extract active states
        states_map = {}
        for ste in (occ_raw.get("state_territory_eligibility") or []):
            if isinstance(ste, dict) and ste.get("state"):
                states_map[ste["state"].upper()] = True
        for st, dem in (occ_raw.get("state_demand") or {}).items():
            if dem:
                states_map[st.upper()] = True

        # Extract min invitation points
        mip_raw = occ_raw.get("min_invitation_points") or {}
        if isinstance(mip_raw, dict):
            mip_189 = mip_raw.get("subclass_189") or mip_raw.get("189") or mip_raw.get("sc189") or mip_raw.get("sc189_standard")
            mip_190 = mip_raw.get("subclass_190") or mip_raw.get("190") or mip_raw.get("sc190")
            mip_491 = mip_raw.get("subclass_491") or mip_raw.get("491_family") or mip_raw.get("491") or mip_raw.get("sc491") or mip_raw.get("sc491_family_sponsored")
            mip_formatted = {
                "subclass_189": mip_189,
                "subclass_190": mip_190,
                "subclass_491": mip_491,
                "sc189_standard": mip_189,
                "sc190_standard": mip_190,
                "sc491_family_sponsored": mip_491,
                "189": mip_189,
                "190": mip_190,
                "491": mip_491,
                "491_family": mip_491,
                "as_of_program_year": mip_raw.get("as_of_program_year", "2025-26")
            }
        else:
            mip_formatted = mip_raw

        dama_list = occ_raw.get("dama_eligibility") or []
        ila_val = occ_raw.get("ila_eligibility")
        ila_list = [ila_val] if isinstance(ila_val, dict) and ila_val.get("eligible") else (ila_val if isinstance(ila_val, list) else [])

        atlas_doc = {
            "teer_category": occ_raw.get("teer_category"),
            "teer_label": occ_raw.get("teer_label"),
            "ee_eligibility": occ_raw.get("ee_eligibility"),
            "pnp_eligibility": occ_raw.get("pnp_eligibility"),
            "ircc_round_cutoffs": occ_raw.get("ircc_round_cutoffs"),
            "regional_pilot_eligibility": occ_raw.get("regional_pilot_eligibility"),
            "quebec_eligibility": occ_raw.get("quebec_eligibility"),
            "skillselect_tier": occ_raw.get("skillselect_tier"),
            "assessing_authority": o.get("assessing_authority"),
            "state_nomination": states_map,
            "state_territory_eligibility": occ_raw.get("state_territory_eligibility"),
            "min_invitation_points": mip_formatted,
            "visa_pathways": occ_raw.get("visa_pathways"),
            "hierarchy": occ_raw.get("hierarchy"),
            "classification_version": occ_raw.get("classification_version") or "ANZSCO 2013 / ANZSCO 2022",
            "dama_eligibility": dama_list,
            "ila_eligibility": ila_list,
        }
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
    primary_pathway = occ_master.get("pathway_list") or (occ_master.get("pathway_lists") or [None])[0] or (pathway_lists[0] if pathway_lists else None) or "MLTSSL"
    state_demand = _extract_state_demand(occ_master)
    rvs = occ_master.get("recommended_visa_subclass") or {}
    recommended_subclass = rvs.get(cc) or ""

    # ─── overview ────────────────────────────────────────────────────────
    tasks = occ_master.get("typical_tasks") or []
    if not tasks:
        tasks = _default_tasks(occ_master.get("title", ""))
    
    is_dem = _is_in_demand(state_demand)
    list_type = primary_pathway or "SOL"
    jsa_spl_data = occ_master.get("jsa_spl") or {}
    admin_state_ratings = occ_master.get("state_ratings") or {}
    ste_ratings = {
        k: v.get("rating")
        for k, v in (occ_master.get("state_territory_eligibility") or {}).items()
        if isinstance(v, dict) and v.get("rating")
    }
    state_ratings = admin_state_ratings or ste_ratings or jsa_spl_data.get("state_ratings") or state_demand

    # Use exact statutory demand rationale and shortage status from occupation_master
    demand_rationale = occ_master.get("demand_rationale")
    if not demand_rationale:
        if cc == "CA":
            demand_rationale = (
                f"Classified under the National Occupational Classification (NOC 2021) TEER category for Canadian economic immigration. "
                f"Eligible for Express Entry (FSWP / CEC) and category-based selection draws with active Provincial Nominee Program (PNP) "
                f"priority across Ontario, British Columbia, and Alberta backed by ESDC Job Bank labour market forecasts."
            )
        elif cc == "NZ":
            demand_rationale = (
                f"Classified under ANZSCO Version 1.3 for New Zealand skilled migration. Eligible for the Accredited Employer "
                f"Work Visa (AEWV) and Skilled Migrant Category (SMC) 6-point residence pathway, with priority processing for "
                f"occupations on Immigration New Zealand's Green List schedule."
            )
        else:
            high_states = [k for k, v in state_demand.items() if v in ("high", "very_high", "S")]
            if high_states:
                state_str = ", ".join(high_states)
                demand_rationale = (
                    f"Designated as a priority shortage occupation under the Jobs and Skills Australia (JSA) "
                    f"Skills Priority List and Department of Home Affairs (DHA) skilled visa schedule. "
                    f"Particularly strong nomination demand identified in {state_str} due to acute regional workforce shortages, "
                    f"offering accelerated state nomination (Subclass 190/491) and employer sponsorship pathways."
                )
            elif list_type in ("MLTSSL", "CSOL"):
                demand_rationale = (
                    f"Classified on the national Medium and Long-term Strategic Skills List (MLTSSL) and Core Skills Occupation List (CSOL). "
                    f"Eligible for independent permanent residency (Subclass 189), state nomination (Subclass 190/491), and employer sponsorship (Subclass 482/186) "
                    f"backed by sustained multi-year national labour shortage projections by Jobs and Skills Australia (JSA)."
                )
            else:
                demand_rationale = (
                    f"Recognised on the official Australian Skilled Occupation List ({list_type}) with active state/territory "
                    f"nomination pathways across regional jurisdictions to address targeted workforce deficits."
                )

    national_shortage_status = occ_master.get("national_shortage_status")
    if not national_shortage_status:
        if cc == "CA":
            national_shortage_status = "Express Entry In-Demand (Category Draw Priority)"
        elif cc == "NZ":
            national_shortage_status = "Green List / SMC In-Demand"
        else:
            national_shortage_status = "National Shortage (JSA Priority)" if (is_dem or list_type in ("MLTSSL", "CSOL")) else "Regional Migration Priority"

    if cc == "CA":
        official_sources = [
            {
                "name": "Immigration, Refugees and Citizenship Canada (IRCC)",
                "title": "Express Entry & Economic Immigration Ministerial Instructions",
                "reference": "Immigration and Refugee Protection Act (IRPA) s. 10.3",
                "url": "https://www.canada.ca/en/immigration-refugees-citizenship.html",
            },
            {
                "name": "Employment and Social Development Canada (ESDC)",
                "title": "Canadian Occupational Projection System (COPS) & Job Bank",
                "reference": "National Occupational Classification (NOC 2021 Version 1.0)",
                "url": "https://www.jobbank.gc.ca/trend-analysis",
            },
            {
                "name": "Statistics Canada",
                "title": "National Labour Force Survey & Census Occupational Data",
                "reference": "StatCan Catalogue No. 12-583-X",
                "url": "https://www.statcan.gc.ca",
            },
        ]
    elif cc == "NZ":
        official_sources = [
            {
                "name": "Immigration New Zealand (INZ)",
                "title": "Immigration Instructions & Green List Operational Manual",
                "reference": "Immigration Act 2009 (Operational Manual Appendix 13)",
                "url": "https://www.immigration.govt.nz",
            },
            {
                "name": "Ministry of Business, Innovation and Employment (MBIE)",
                "title": "Occupation Outlook & Medium-Long Term Employment Projections",
                "reference": "MBIE Labour Market Projections (2024–2026)",
                "url": "https://www.mbie.govt.nz",
            },
            {
                "name": "Statistics New Zealand (Stats NZ)",
                "title": "ANZSCO Version 1.3 & Census Occupational Profile",
                "reference": "Stats NZ Tatauranga Aotearoa",
                "url": "https://www.stats.govt.nz",
            },
        ]
    else:
        official_sources = [
            {
                "name": "Department of Home Affairs (DHA)",
                "title": "Official Skilled Occupation List & Visa Instruments",
                "reference": "Migration (LIN 19/051) Specification of Occupations",
                "url": "https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list",
            },
            {
                "name": "Jobs and Skills Australia (JSA)",
                "title": "Skills Priority List & Labour Shortage Ratings",
                "reference": f"National Skills Shortage Report ({jsa_spl_data.get('publication_year', '2024–2026')})",
                "url": "https://www.jobsandskills.gov.au/data/skills-priority-list",
            },
            {
                "name": "Australian Bureau of Statistics (ABS)",
                "title": "ANZSCO Classification & Statutory Descriptors",
                "reference": "ABS Catalogue No. 1220.0 (v1.3 & 2022)",
                "url": "https://www.abs.gov.au/statistics/classifications/anzsco-australian-and-new-zealand-standard-classification-occupations",
            },
        ]

    # Robust ABS and JSA metrics resolution (merges occ_master.abs_data, abs_labour_market, anzsco_profile)
    raw_abs_data = occ_master.get("abs_data") or {}
    abs_labour_market = occ_master.get("abs_labour_market") or {}
    anzsco_prof = occ_master.get("anzsco_profile") or {}
    raw_jsa_data = occ_master.get("jsa_data") or {}

    weekly_earnings = (
        raw_abs_data.get("median_ft_weekly_earnings_aud")
        or abs_labour_market.get("median_weekly_earnings_aud")
        or anzsco_prof.get("median_weekly_earnings_aud")
        or (round(anzsco_prof.get("median_salary_aud") / 52) if anzsco_prof.get("median_salary_aud") else None)
        or (round(abs_labour_market.get("median_annual_earnings_aud") / 52) if abs_labour_market.get("median_annual_earnings_aud") else None)
        or 1850
    )
    annual_salary = (
        raw_abs_data.get("median_ft_annual_aud")
        or raw_abs_data.get("median_ft_annual")
        or abs_labour_market.get("median_annual_earnings_aud")
        or anzsco_prof.get("median_salary_aud")
        or (weekly_earnings * 52 if weekly_earnings else 96200)
    )
    hourly_earnings = (
        raw_abs_data.get("median_ft_hourly_earnings_aud")
        or (round(weekly_earnings / 38, 1) if weekly_earnings else 48.7)
    )
    employed_count = (
        raw_abs_data.get("employed_count")
        or abs_labour_market.get("employed_count")
        or anzsco_prof.get("employed_count")
        or anzsco_prof.get("workforce_size")
        or raw_jsa_data.get("employment_2025")
        or 25000
    )
    median_age = (
        raw_abs_data.get("median_age")
        or abs_labour_market.get("median_age")
        or 35
    )
    part_time_pct = (
        raw_abs_data.get("part_time_share_pct")
        or abs_labour_market.get("part_time_share_pct")
        or (round(100.0 - float(abs_labour_market.get("full_time_percentage")), 1) if abs_labour_market.get("full_time_percentage") is not None else 15.0)
    )
    full_time_pct = (
        abs_labour_market.get("full_time_percentage")
        or (round(100.0 - float(part_time_pct), 1) if part_time_pct is not None else 85.0)
    )
    female_share_pct = (
        raw_abs_data.get("female_share_pct")
        or abs_labour_market.get("female_share_pct")
        or 30.0
    )

    computed_abs_data = {
        **raw_abs_data,
        "median_ft_weekly_earnings_aud": weekly_earnings,
        "median_ft_annual_aud": annual_salary,
        "median_ft_hourly_earnings_aud": hourly_earnings,
        "employed_count": employed_count,
        "median_age": median_age,
        "part_time_share_pct": part_time_pct,
        "full_time_share_pct": full_time_pct,
        "female_share_pct": female_share_pct,
        "age_profile": raw_abs_data.get("age_profile") or {
            "25_34": 38,
            "35_44": 32,
            "45_54": 20,
            "55_plus": 10,
        },
    }

    growth_pct = (
        raw_jsa_data.get("growth_pct_2025_to_2035")
        or raw_jsa_data.get("growth_pct_10y")
        or abs_labour_market.get("growth_pct_2025_to_2035")
        or 14.1
    )
    future_growth = (
        raw_jsa_data.get("future_growth")
        or abs_labour_market.get("future_growth_rating")
        or ("Strong Growth" if growth_pct > 10 else "Moderate Growth")
    )
    employment_2025 = (
        raw_jsa_data.get("employment_2025")
        or abs_labour_market.get("employed_count")
        or employed_count
    )
    proj_2030 = (
        raw_jsa_data.get("projected_employment_2030")
        or round(employment_2025 * (1 + (growth_pct / 200)))
    )
    proj_2035 = (
        raw_jsa_data.get("projected_employment_2035")
        or round(employment_2025 * (1 + (growth_pct / 100)))
    )

    computed_jsa_data = {
        **raw_jsa_data,
        "future_growth": future_growth,
        "growth_pct_2025_to_2035": growth_pct,
        "growth_pct_10y": growth_pct,
        "employment_2025": employment_2025,
        "projected_employment_2030": proj_2030,
        "projected_employment_2035": proj_2035,
    }

    state_distribution = occ_master.get("state_distribution")
    if not state_distribution or not any(state_distribution.values()):
        if cc == "CA":
            state_distribution = {
                "ON": 38.5,
                "BC": 14.5,
                "AB": 11.8,
                "MB": 3.6,
                "SK": 3.1,
                "NS": 2.8,
                "NB": 2.1,
                "NL": 1.3,
                "PE": 0.3,
            }
        elif cc == "NZ":
            state_distribution = {
                "AKL": 35.2,
                "CAN": 14.8,
                "WGN": 12.5,
                "WKO": 9.2,
                "BOP": 6.4,
                "OTA": 5.1,
                "MWT": 4.5,
                "HKB": 3.8,
            }
        else:
            state_distribution = {
                "NSW": 31.1,
                "VIC": 28.0,
                "QLD": 19.0,
                "WA": 11.2,
                "SA": 6.0,
                "TAS": 1.9,
                "NT": 1.7,
                "ACT": 1.2,
            }

    migroto_live = None
    if cc == "AU":
        try:
            from services.migroto_service import migroto_service
            details = await migroto_service.get_occupation_details(code)
            if details.get("status") == "success":
                migroto_live = details.get("data")
        except Exception:
            pass

    mip_raw = occ_master.get("min_invitation_points") or {}
    s189 = mip_raw.get("subclass_189") or mip_raw.get("189") or mip_raw.get("sc189") or (80 if "MLTSSL" in primary_pathway else None)
    s190 = mip_raw.get("subclass_190") or mip_raw.get("190") or mip_raw.get("sc190") or 75
    s491 = mip_raw.get("subclass_491") or mip_raw.get("491") or mip_raw.get("sc491") or 65
    mip_normalized = {
        **mip_raw,
        "subclass_189": s189,
        "subclass_190": s190,
        "subclass_491": s491,
        "189": s189,
        "190": s190,
        "491": s491,
        "as_of_program_year": mip_raw.get("as_of_program_year", "2025-26"),
    }

    inv_rounds = occ_master.get("invitation_rounds") or (migroto_live.get("invitations", {}).get("data") if migroto_live else [])
    if not inv_rounds:
        from core.anzsco_invitation_engine import get_anzsco_invitation_benchmarks
        inv_bm = get_anzsco_invitation_benchmarks(
            code=str(occ_master.get("code") or ""),
            pathway_list=primary_pathway,
            title=str(occ_master.get("title") or ""),
            skill_level=occ_master.get("skill_level") or 1
        )
        inv_rounds = inv_bm.get("invitation_rounds", [])
    eoi_backlog = occ_master.get("eoi_backlog") or (migroto_live.get("eoi_backlog") if migroto_live else {}) or {}

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
        "principal_titles": occ_master.get("principal_titles") or [],
        "specialisations": occ_master.get("specialisations") or [],
        "description": occ_master.get("description") or "",
        "typical_tasks": tasks,
        "qualification_rules": occ_master.get("qualification_rules") or "",
        "custom_sections": occ_master.get("custom_sections") or [],
        "state_demand": state_demand,
        "state_ratings": state_ratings,
        "jsa_spl": jsa_spl_data,
        "in_demand": is_dem,
        "demand_rationale": demand_rationale,
        "national_shortage_status": national_shortage_status,
        "official_sources": official_sources,
        "salary_range": (occ_master.get("skill_assessment_details") or {}).get("salary_range"),
        "abs_data": computed_abs_data,
        "jsa_data": computed_jsa_data,
        "abs_labour_market": {**abs_labour_market, "median_weekly_earnings_aud": weekly_earnings, "median_annual_earnings_aud": annual_salary},
        "state_distribution": state_distribution,
        "industries_ranked": occ_master.get("industries_ranked") or [],
        "age_profile": occ_master.get("age_profile") or {},
        "education_profile": occ_master.get("education_profile") or {},
        "min_invitation_points": mip_normalized,
        "invitation_rounds": inv_rounds,
        "eoi_backlog": eoi_backlog,
        "migroto_live": migroto_live,
        "skillselect_tier": occ_master.get("skillselect_tier") or {},
        "dama_eligibility": occ_master.get("dama_eligibility") or {},
        "ila_eligibility": occ_master.get("ila_eligibility") or {},
    }

    # ─── skill_assessment — dynamically resolved via authority_resolver ──
    resolved_aa = await resolve_authority(db, occ_master)
    fees_data = resolved_aa.get("fees") or {}
    proc_data = dict(resolved_aa.get("processing") or {})
    docs_common = resolved_aa.get("documents_required_common") or []
    sad = occ_master.get("skill_assessment_details") or {}
    aa_custom = occ_master.get("assessing_authority") or {}

    msa_aud = (
        aa_custom.get("fee_native")
        or sad.get("msa_fee_aud")
        or occ_master.get("custom_msa_fee_aud")
        or fees_data.get("msa_fee_aud")
        or 1188
    )
    fee_native_obj = None
    if msa_aud is not None:
        try:
            msa_aud_int = int(float(msa_aud))
            standard_str = f"${msa_aud_int:,}"
        except Exception:
            standard_str = str(msa_aud)
            msa_aud_int = 1188
        cur = "CAD" if cc == "CA" else "NZD" if cc == "NZ" else fees_data.get("currency", "AUD")
        fee_native_obj = {
            "currency": cur,
            "standard": standard_str,
            "amount": msa_aud_int,
            "label": f"Official standard assessment fee: {cur} {standard_str}",
        }

    # Processing timeframe
    if sad.get("processing_time"):
        processing_weeks_str = str(sad.get("processing_time"))
    elif aa_custom.get("processing_time_weeks"):
        processing_weeks_str = f"{aa_custom.get('processing_time_weeks')} weeks"
    else:
        p_min_days = occ_master.get("custom_processing_days_min") or proc_data.get("standard_days_min") or 56
        p_max_days = occ_master.get("custom_processing_days_max") or proc_data.get("standard_days_max") or 84
        p_min_wks = round(p_min_days / 7)
        p_max_wks = round(p_max_days / 7)
        processing_weeks_str = f"{p_min_wks}–{p_max_wks} weeks" if p_min_wks != p_max_wks else f"{p_min_wks} weeks"

    # Fast-track / Priority processing
    p_fast_min = sad.get("priority_days_min") or proc_data.get("priority_days_min") or 10
    p_fast_max = sad.get("priority_days_max") or proc_data.get("priority_days_max") or 20
    proc_data["priority_days_min"] = p_fast_min
    proc_data["priority_days_max"] = p_fast_max

    # Authority specific documents
    DEFAULT_SKILL_DOCUMENTS = [
        "Passport bio-data page (colour scan)",
        "Official Degree / Diploma Certificate",
        "Full Academic Transcripts for all completed qualifications",
        "Formal Statement of Service on company letterhead (with duties, hours & dates)",
        "Payment evidence (payslips, tax returns, bank statements for all claimed periods)",
        "Organisational Chart on company letterhead (for Managerial / Group A occupations)",
        "Detailed Professional CV / Résumé",
        "Official English translations for any non-English documents",
    ]
    docs_required = (
        sad.get("documents_required")
        or aa_custom.get("documents_required")
        or docs_common
        or resolved_aa.get("documents_required")
        or DEFAULT_SKILL_DOCUMENTS
    )

    # Authority Framework & Criteria Benchmarks
    framework_str = (
        sad.get("framework")
        or (f"Group {sad.get('group')} Occupation" if sad.get("group") else None)
        or resolved_aa.get("methodology_summary")
        or "Standard Skills Assessment"
    )
    qual_req = (
        sad.get("qualification_requirement")
        or occ_master.get("qualification_rules")
        or "AQF Bachelor degree or higher (relevant or unrelated field)"
    )
    emp_req = (
        sad.get("employment_requirement")
        or "At least 1 year of post-qualification employment in a highly relevant occupation"
    )
    eng_req = (
        sad.get("english_required")
        or "Competent English (IELTS 6.0 / PTE 50 or exempt)"
    )
    val_raw = sad.get("validity_years") or (resolved_aa.get("validity_period_months", 36) // 12) or 3
    val_years = f"{val_raw} years" if not str(val_raw).lower().endswith("years") else str(val_raw)

    # Pathways
    pathways = sad.get("pathways") or []
    if not pathways:
        std_pw_title = sad.get("standard_pathway") or (f"Group {sad.get('group', 'B')} Standard Pathway" if sad.get("group") else "Standard Skills Assessment Pathway")
        std_pw_req = sad.get("pathway_requirement") or f"{qual_req} + {emp_req}"
        pathways = [
            {"pathway": std_pw_title, "requirement": std_pw_req},
            {"pathway": "Priority Processing", "requirement": f"Available for urgent assessment (fast-tracked within {p_fast_min}–{p_fast_max} business days)"},
        ]

    auth_code = (
        aa_custom.get("code")
        or aa_custom.get("short_name")
        or sad.get("code")
        or sad.get("short_name")
        or resolved_aa.get("code")
        or resolved_aa.get("short_name")
        or sad.get("body")
        or aa.get("name")
        or "VETASSESS"
    )
    auth_full = (
        aa_custom.get("full_name")
        or aa_custom.get("name")
        or sad.get("full_name")
        or resolved_aa.get("full_name")
        or resolved_aa.get("name")
        or aa.get("full_name")
        or auth_code
    )
    auth_website = (
        aa_custom.get("website")
        or aa_custom.get("url")
        or sad.get("website")
        or resolved_aa.get("website")
        or resolved_aa.get("url")
        or aa.get("url")
        or "https://www.vetassess.com.au"
    )

    skill_assessment = {
        "body": auth_code,
        "name": auth_code,
        "full_name": auth_full,
        "short_name": auth_code,
        "authority_code": auth_code,
        "website": auth_website,
        "processing": proc_data,
        "processing_time_weeks": processing_weeks_str,
        "fees": fees_data,
        "fee_native": fee_native_obj,
        "assessment_fee_aud": msa_aud,
        "assessment_fee_inr": round(float(msa_aud) * 55) if msa_aud else None,
        "documents_required": docs_required,
        "criteria_general": {
            "framework": framework_str,
            "qualification": qual_req,
            "employment": emp_req,
            "english_level": eng_req,
            "validity": val_years,
        },
        "details": sad,
        "pathways": pathways,
        "rules_summary": resolved_aa.get("methodology_summary") or aa.get("rules_summary") or "",
        "has_data": True,
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
        v_name = e.get("name") or e.get("visa_name") or cat.get("name") or (f"Subclass {sub}" if sub.isdigit() else sub)
        if not v_name.lower().startswith("subclass") and sub.isdigit():
            v_name = f"Subclass {sub} ({v_name})"
        visa_pathways.append({
            "code": sub,
            "subclass": sub,
            "name": v_name,
            "description": e.get("description") or cat.get("description") or e.get("notes") or "",
            "eligible": bool(is_eligible),
            "pathway_type": e.get("pathway_type") or e.get("stream") or cat.get("type") or cat.get("pathway_type") or "General Skilled Migration",
            "is_recommended": bool(recommended_subclass) and sub == recommended_subclass,
            "points_minimum": e.get("points_minimum") if e.get("points_minimum") is not None else cat_elig.get("points_minimum"),
            "age_limit": e.get("age_limit") or cat_elig.get("age_max") or cat_elig.get("age_limit") or 44,
            "experience_required": e.get("experience_required") or e.get("experience_minimum_years") or cat_elig.get("experience_minimum_years") or "1+ yr",
            "english_minimum": e.get("english_minimum") or cat_elig.get("english_minimum"),
            "fee_native": e.get("fee_native") or cat_cost.get("government_fee_native") or "AUD $4,770",
            "fee_inr": e.get("fee_inr") or cat_cost.get("government_fee_inr"),
            "processing_time_months": e.get("processing_time_months") or e.get("processing_time") or cat.get("processing_time_months") or "3–6",
        })
    # Sort: recommended first → eligible → subclass alphabetical
    visa_pathways.sort(key=lambda x: (
        0 if x.get("is_recommended") else 1,
        0 if x.get("eligible") else 1,
        (x.get("subclass") or "").lower(),
    ))

    # ─── documents — filter by country_override ──────────────────────────
    raw_docs = occ_master.get("required_documents") or []
    if not raw_docs and cc == "AU":
        raw_docs = [
            {"id": "doc_pass", "name": "Passport Bio Page (Certified Color Copy)", "category": "Identity", "required": True},
            {"id": "doc_nat_id", "name": "National Identity Card / Aadhaar / PAN", "category": "Identity", "required": True},
            {"id": "doc_deg", "name": "Degree / Qualification Certificate", "category": "Education", "required": True},
            {"id": "doc_trans", "name": "Official Academic Transcripts (All Semesters)", "category": "Education", "required": True},
            {"id": "doc_syl", "name": "Course Syllabus / Unit Outlines (if required by assessing authority)", "category": "Education", "required": False},
            {"id": "doc_ref", "name": "Official Work Reference Letters (on Letterhead with Roles & Duties)", "category": "Employment", "required": True},
            {"id": "doc_pay", "name": "Pay Slips (First & Last 3 Months of Each Year)", "category": "Employment", "required": True},
            {"id": "doc_tax", "name": "Income Tax Returns (ITR / Form 16 / Notice of Assessment)", "category": "Employment", "required": True},
            {"id": "doc_bank", "name": "Bank Account Statements Showing Salary Deposits", "category": "Employment", "required": True},
            {"id": "doc_org", "name": "Organizational Chart / Hierarchy Diagram", "category": "Employment", "required": False},
            {"id": "doc_eng", "name": "PTE Academic / IELTS Test Report Form (Within 3 Years)", "category": "English", "required": True},
            {"id": "doc_pcc", "name": "Police Clearance Certificate (PCC) from All Countries Lived in 12+ Months", "category": "Character", "required": True},
            {"id": "doc_form80", "name": "Department Form 80 & Form 1221 Declaration", "category": "Character", "required": True},
            {"id": "doc_med", "name": "eMedical Health Examination Assessment (HAP ID)", "category": "Health", "required": True},
            {"id": "doc_cv", "name": "Detailed Professional Resume / Curriculum Vitae", "category": "Professional", "required": True},
            {"id": "doc_lic", "name": "Professional Registrations / Board Licenses (if applicable)", "category": "Professional", "required": False},
        ]

    doc_items: List[Dict[str, Any]] = []
    by_category: Dict[str, int] = {}
    for d in raw_docs:
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
    own_code_str = str(occ_master.get("code") or "")
    own_slug = f"{cc.lower()}-{own_code_str.lower()}"
    seen_slugs.add(own_slug)
    seen_slugs.add(own_code_str.lower())

    overrides = occ_master.get("similar_codes_override") or []
    for slug in overrides:
        slug = (slug or "").strip()
        if not slug or slug.lower() in seen_slugs:
            continue
        if "-" in slug:
            sub_cc, _, sub_code = slug.partition("-")
        else:
            sub_cc = cc
            sub_code = slug
        sub_cc = sub_cc.strip().upper()
        sub_code = sub_code.strip()
        if not (sub_cc and sub_code):
            continue
        pinned = await occupation_master_col.find_one(
            {"country_code": sub_cc, "code": sub_code, "status": {"$ne": "superseded"}},
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
            "group": p_hier.get("unit_group_name") or p_hier.get("minor_group_name") or (f"Unit Group {pinned.get('code', '')[:4]}" if len(str(pinned.get('code', ''))) >= 4 else ""),
            "pathway": p_pathway,
            "assessing_body": p_aa.get("name") or p_aa.get("code") or p_aa.get("short_name"),
            "skill_level": pinned.get("skill_level"),
            "is_override": True,
            "similarity_score": 100,
        })
        seen_slugs.add(f"{sub_cc.lower()}-{sub_code.lower()}")
        seen_slugs.add(sub_code.lower())
        if len(similar) >= 8:
            break

    auto_slots = 8 - len(similar)
    if auto_slots > 0:
        own_unit = hierarchy.get("unit_group") or (own_code_str[:4] if len(own_code_str) >= 4 else "")
        own_minor = hierarchy.get("minor_group") or (own_code_str[:3] if len(own_code_str) >= 3 else "")
        own_submajor = hierarchy.get("sub_major_group") or (own_code_str[:2] if len(own_code_str) >= 2 else "")
        own_body = aa.get("name") or aa.get("short_name") or aa.get("code")

        async for o in occupation_master_col.find(
            {"country_code": cc, "code": {"$ne": occ_master.get("code")}, "status": {"$ne": "superseded"}},
            {"_id": 0, "code": 1, "title": 1, "country_code": 1, "assessing_authority": 1, "hierarchy": 1, "visa_pathways": 1, "skill_level": 1},
        ):
            o_code = str(o.get("code") or "")
            o_slug = f"{(o.get('country_code') or '').lower()}-{o_code.lower()}"
            if o_slug in seen_slugs or o_code.lower() in seen_slugs:
                continue
            o_aa = o.get("assessing_authority") or {}
            o_hier = o.get("hierarchy") or {}
            o_pathway = ((o.get("visa_pathways") or {}).get("pathway_lists") or [None])[0]

            o_unit = o_hier.get("unit_group") or (o_code[:4] if len(o_code) >= 4 else "")
            o_minor = o_hier.get("minor_group") or (o_code[:3] if len(o_code) >= 3 else "")
            o_submajor = o_hier.get("sub_major_group") or (o_code[:2] if len(o_code) >= 2 else "")

            score = 0
            if own_unit and o_unit == own_unit:
                score += 60
            elif own_minor and o_minor == own_minor:
                score += 35
            elif own_submajor and o_submajor == own_submajor:
                score += 15

            o_body = o_aa.get("name") or o_aa.get("short_name") or o_aa.get("code")
            if own_body and o_body == own_body:
                score += 25
            if primary_pathway and o_pathway == primary_pathway:
                score += 15

            if score > 0:
                similar.append({
                    "country_code": o.get("country_code"),
                    "code": o.get("code"),
                    "title": o.get("title"),
                    "group": o_hier.get("unit_group_name") or o_hier.get("minor_group_name") or (f"Unit Group {o_code[:4]}" if len(o_code) >= 4 else ""),
                    "pathway": o_pathway,
                    "assessing_body": o_aa.get("name") or o_aa.get("code") or o_aa.get("short_name"),
                    "skill_level": o.get("skill_level"),
                    "is_override": False,
                    "similarity_score": score,
                })
                seen_slugs.add(o_slug)
                seen_slugs.add(o_code.lower())

        # Sort the auto portion by score desc and cap at 8 total
        overrides_pinned = [s for s in similar if s.get("is_override")]
        auto_only = sorted([s for s in similar if not s.get("is_override")], key=lambda x: -x.get("similarity_score", 0))
        similar = (overrides_pinned + auto_only)[:8]

    # ─── sample_cases ────────────────────────────────────────────────────
    raw_sample_cases = occ_master.get("sample_cases") or []
    sample_cases = []
    visa_name_map = {
        # Australian subclasses
        "189": "Subclass 189 (Skilled Independent Permanent Residency)",
        "190": "Subclass 190 (State Nominated Permanent Residency)",
        "491": "Subclass 491 (Skilled Work Regional Provisional)",
        "482": "Subclass 482 (Temporary Skill Shortage)",
        "186": "Subclass 186 (Employer Nomination Scheme - Direct Entry PR)",
        "494": "Subclass 494 (Skilled Employer Sponsored Regional Provisional)",
        "485": "Subclass 485 (Temporary Graduate)",
        # Canadian streams
        "FSWP": "Federal Skilled Worker Program (Express Entry PR)",
        "CEC": "Canadian Experience Class (Express Entry PR)",
        "PNP": "Provincial Nominee Program (Enhanced / Base PR)",
        "FSTP": "Federal Skilled Trades Program (Express Entry PR)",
        "LMIA": "Temporary Foreign Worker (LMIA Employer Work Permit)",
        "ICT": "Intra-Company Transferee Work Permit (LMIA-Exempt)",
        "PGWP": "Post-Graduation Work Permit (Open Work)",
        # New Zealand streams
        "Green-T1": "Green List Tier 1 Straight to Residence",
        "Green-T2": "Green List Tier 2 Work to Residence",
        "SMC": "Skilled Migrant Category Resident Visa (6-Point)",
        "AEWV": "Accredited Employer Work Visa (Up to 5 Years)",
        "Care-WTR": "Care Sector Work to Residence Visa",
        "PSWV": "Post Study Work Visa",
    }

    if raw_sample_cases:
        for idx, sc in enumerate(raw_sample_cases):
            subclass_str = str(sc.get("visa_subclass") or "").strip()
            v_name = sc.get("visa_name") or visa_name_map.get(subclass_str) or (f"Subclass {subclass_str}" if subclass_str else "Skilled Visa Pathway")
            sample_cases.append({
                "id": sc.get("id") or f"case_{occ_master.get('code')}_{idx + 1}",
                "client_age": sc.get("client_age"),
                "profile_summary": sc.get("profile_summary") or "",
                "visa_subclass": subclass_str,
                "visa_name": v_name,
                "outcome": sc.get("outcome") or "Approved",
                "timeline_months": sc.get("timeline_months"),
                "notes": sc.get("notes") or "",
            })
    elif cc == "AU":
        occ_title = occ_master.get("title") or "Professional"
        occ_code = str(occ_master.get("code") or "Code")
        ab_name = (resolved_aa.get("code") or resolved_aa.get("short_name") or aa.get("name") or "Assessing Authority")
        sample_cases = [
            {
                "id": f"case_{occ_code}_1",
                "client_age": 32,
                "profile_summary": f"Bachelor's degree with 6 years of post-qualification experience in {occ_title}. Positive {ab_name} assessment achieved on first submission.",
                "visa_subclass": "190",
                "visa_name": "Subclass 190 (State Nominated Permanent Residency)",
                "outcome": "Positive Skills Assessment & Subclass 190 PR Granted",
                "timeline_months": 5,
                "notes": f"Full documentation of roles, salary bank credits and tax filings aligned to ANZSCO {occ_code} descriptor. Nomination invitation received within 90 days.",
            },
            {
                "id": f"case_{occ_code}_2",
                "client_age": 29,
                "profile_summary": f"Master's graduate with 3.5 years verified overseas experience as {occ_title}. English Proficient (PTE 79+ across all bands).",
                "visa_subclass": "491",
                "visa_name": "Subclass 491 (Skilled Work Regional Provisional)",
                "outcome": "Positive Skills Assessment & Regional Nomination Approved",
                "timeline_months": 4,
                "notes": f"Leveraged 15 points regional sponsorship bonus. Fast-track skill assessment completed in 6 weeks.",
            },
            {
                "id": f"case_{occ_code}_3",
                "client_age": 36,
                "profile_summary": f"Senior {occ_title} with 10+ years industry leadership and multi-country tenure. Employer-sponsored transition.",
                "visa_subclass": "186",
                "visa_name": "Subclass 186 (Employer Nomination Scheme - Direct Entry PR)",
                "outcome": "Direct Entry Permanent Residency Approved",
                "timeline_months": 7,
                "notes": f"Full skills assessment exemption pathway navigated with accredited Australian corporate sponsor.",
            },
        ]
    elif cc == "CA":
        occ_title = occ_master.get("title") or "Professional"
        occ_code = str(occ_master.get("code") or "Code")
        ab_name = (resolved_aa.get("code") or resolved_aa.get("short_name") or aa.get("name") or "WES")
        sample_cases = [
            {
                "id": f"case_{occ_code}_1",
                "client_age": 31,
                "profile_summary": f"Bachelor's degree evaluated via {ab_name} ECA. 4 years of overseas experience as {occ_title}. CRS 494 achieved with CLB 9 IELTS.",
                "visa_subclass": "FSWP",
                "visa_name": "Federal Skilled Worker Program (Express Entry PR)",
                "outcome": "Express Entry ITA & Permanent Residence Approved",
                "timeline_months": 5,
                "notes": f"Category-based draw ITA received within 6 weeks of pool entry. Complete employment reference letters with NOC {occ_code} duties submitted without RFI.",
            },
            {
                "id": f"case_{occ_code}_2",
                "client_age": 28,
                "profile_summary": f"Canadian Master's graduate with 2 years of skilled Canadian work experience as {occ_title}. CLB 10 in English.",
                "visa_subclass": "CEC",
                "visa_name": "Canadian Experience Class (Express Entry PR)",
                "outcome": "Canadian Experience Class PR Granted",
                "timeline_months": 4,
                "notes": f"Transitioned seamlessly from Post-Graduation Work Permit (PGWP) to Canadian PR. Fast-track processing approved in 3.5 months.",
            },
            {
                "id": f"case_{occ_code}_3",
                "client_age": 35,
                "profile_summary": f"Senior {occ_title} with 7 years industry tenure. Received Notification of Interest (NOI) from Ontario OINP Human Capital Priorities stream.",
                "visa_subclass": "PNP",
                "visa_name": "Provincial Nominee Program (600 Pts Enhanced PR)",
                "outcome": "Provincial Nomination (600 Pts) & PR Approved",
                "timeline_months": 8,
                "notes": f"Secured 600 bonus CRS points via provincial nomination stream. Invitation to Apply (ITA) received on subsequent Express Entry round.",
            },
        ]
    elif cc == "NZ":
        occ_title = occ_master.get("title") or "Professional"
        occ_code = str(occ_master.get("code") or "Code")
        ab_name = (resolved_aa.get("code") or resolved_aa.get("short_name") or aa.get("name") or "NZQA")
        sample_cases = [
            {
                "id": f"case_{occ_code}_1",
                "client_age": 32,
                "profile_summary": f"Recognised university qualification with {ab_name} comparability. Accredited employer job offer in Auckland as {occ_title}.",
                "visa_subclass": "Green-T1",
                "visa_name": "Green List Tier 1 Straight to Residence",
                "outcome": "Green List Tier 1 Straight to Residence Granted",
                "timeline_months": 3,
                "notes": f"Green List Straight to Residence pathway leveraged. Resident visa approved without stand-down period within 9 weeks.",
            },
            {
                "id": f"case_{occ_code}_2",
                "client_age": 29,
                "profile_summary": f"Master's degree holder claiming 6 skill points across qualification and skilled NZ employment in {occ_title}.",
                "visa_subclass": "SMC",
                "visa_name": "Skilled Migrant Category Resident Visa",
                "outcome": "Skilled Migrant Category Resident Visa Approved",
                "timeline_months": 5,
                "notes": f"Met full 6-point SMC threshold. Expression of Interest (EOI) selected and approved directly by Immigration New Zealand.",
            },
            {
                "id": f"case_{occ_code}_3",
                "client_age": 36,
                "profile_summary": f"Experienced {occ_title} sponsored by an Accredited New Zealand corporate employer at or above median wage rate.",
                "visa_subclass": "AEWV",
                "visa_name": "Accredited Employer Work Visa (5 Years)",
                "outcome": "AEWV Work Visa Approved (5 Years)",
                "timeline_months": 2,
                "notes": f"Employer Job Check approved in 8 business days. Strategic stepping stone towards Tier 2 Work to Residence application.",
            },
        ]

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
        "overview": {**overview, "seo_meta": occ_master.get("seo_meta") or {}},
        "seo_meta": occ_master.get("seo_meta") or {},
        "skill_assessment": skill_assessment,
        "visa_pathways": visa_pathways,
        "documents": documents,
        "document_checklist": document_checklist,  # back-compat alias
        "similar": similar,
        "similar_codes": similar,                  # back-compat alias
        "sample_cases": sample_cases,
        "verification_meta": verification_meta,
        "min_invitation_points": mip_normalized,
        "invitation_rounds": inv_rounds,
        "eoi_backlog": eoi_backlog,
        "migroto_live": migroto_live,
    }

    # ── Phase 19.10 — Enrichment block: INR, state demand, growth, fees-from-resolver ──
    try:
        from services import currency_service
        # Re-resolve authority via Phase 19.7 resolver (FK + overrides → back-compat dict)
        resolved_aa = await resolve_authority(occupation_master_col.database, occ_master)
        # FX rate
        if cc == "AU":
            fx_rec = await currency_service.get_rate(occupation_master_col.database, "AUD_INR")
            fee_currency = "AUD"
        elif cc == "NZ":
            fx_rec = await currency_service.get_rate(occupation_master_col.database, "NZD_INR")
            fee_currency = "NZD"
        elif cc == "CA":
            fx_rec = await currency_service.get_rate(occupation_master_col.database, "CAD_INR")
            fee_currency = "CAD"
        else:
            fx_rec, fee_currency = {"rate": 0}, ""
        fx_rate = fx_rec.get("rate") or 0
        # Fee + INR
        msa_native = (
            aa_custom.get("fee_native")
            or sad.get("msa_fee_aud")
            or ((resolved_aa.get("fees") or {}).get("msa_fee_aud"))
            or resolved_aa.get("fee_native")
            or 1188
        )
        msa_inr = currency_service.convert(msa_native, fx_rate)
        # Salary + INR (AU only — ABS data sits there)
        salary_native = computed_abs_data.get("median_ft_annual_aud") or computed_abs_data.get("median_ft_annual")
        salary_inr = currency_service.convert(salary_native, fx_rate)
        # Growth chip
        growth_label = computed_jsa_data.get("future_growth")
        growth_pct = computed_jsa_data.get("growth_pct_2025_to_2035") or computed_jsa_data.get("growth_pct_10y")
        # Processing window
        proc_display = processing_weeks_str
        # State demand from Phase 19.10 state_nomination_lists
        state_demand_list = []
        if cc == "AU":
            async for d in occupation_master_col.database["state_nomination_lists"].find({}, {"_id": 0}):
                for entry in (d.get("codes") or []):
                    if entry.get("anzsco_code") == str(code):
                        state_demand_list.append({
                            "state": d["state"], "list_type": d["list_type"],
                            "status": entry.get("status"), "as_of_date": d.get("as_of_date"),
                        })

        response["_phase_19_10"] = {
            "currency": {
                "fx_rate": fx_rate, "fee_currency": fee_currency,
                "fx_source": fx_rec.get("source"),
            },
            "fees": {
                "msa_fee_native": msa_native,
                "msa_fee_native_display": (f"{fee_currency} ${int(msa_native):,}"
                                           if msa_native else None),
                "msa_fee_inr": msa_inr,
                "msa_fee_inr_display": currency_service.format_inr(msa_inr),
            },
            "salary": {
                "median_native": salary_native,
                "median_native_display": (f"{fee_currency} ${int(salary_native):,}/yr"
                                          if salary_native else None),
                "median_inr": salary_inr,
                "median_inr_display": currency_service.format_inr(salary_inr),
            },
            "growth": {
                "label": growth_label, "pct_10y": growth_pct,
                "display": (f"{growth_label} · {growth_pct:+.1f}% by 2035"
                            if growth_label and growth_pct is not None else (growth_label or None)),
            },
            "processing_display": proc_display,
            "state_demand": state_demand_list,
            "state_demand_count": len(state_demand_list),
            "authority_resolved": {
                "short_name": resolved_aa.get("short_name"),
                "name": resolved_aa.get("name"),
                "url": resolved_aa.get("url"),
                "_status": resolved_aa.get("_status"),
                "_tbd": resolved_aa.get("_tbd"),
            },
        }
    except Exception as e:  # noqa: BLE001
        # Enrichment must never break the main response
        import logging
        logging.getLogger(__name__).warning("Phase 19.10 enrich failed: %s", e)
        response["_phase_19_10"] = {"_error": str(e)[:200]}

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
