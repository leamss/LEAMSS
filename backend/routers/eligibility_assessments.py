"""Phase 6.3 — Eligibility Assessments Router.

Runs the hybrid (Custom Rules + Claude AI) analysis on a saved client profile.

Endpoints:
  POST /api/eligibility/assessments/run       — Trigger fresh analysis
  GET  /api/eligibility/assessments/{id}      — Retrieve a single assessment
  GET  /api/eligibility/assessments/profile/{profile_id}  — Latest assessment for a profile
  POST /api/eligibility/assessments/{id}/re-run — Force re-analysis (bypass cache)
  GET  /api/eligibility/assessments/{id}/insights — Compact summary for embeds
  GET  /api/eligibility/assessments            — Paginated history

Caching: results stored in `eligibility_assessments`. Re-run within 24h returns
the cached row unless `force=True`.
"""
import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.eligibility_rules import analyze_country_rules
from core.eligibility_ai import claude_enrich

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eligibility/assessments", tags=["Phase 6.3 - Eligibility Assessments"])

assessments_col = db["eligibility_assessments"]
profiles_col = db["client_eligibility_profiles"]
countries_col = db["country_rules"]


ROLE_VIEWERS = {"admin", "admin_owner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "partner", "case_manager", "hr_manager"}
PARALLEL_TIMEOUT_PER_COUNTRY = 30  # seconds
CACHE_HOURS = 24


def _user_role(user: dict) -> str:
    return user.get("rbac_role") or user.get("role") or ""


def _can_access(user: dict) -> bool:
    return _user_role(user) in ROLE_VIEWERS or "*" in (user.get("permissions") or [])


def _strip(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


def _profile_hash(profile: Dict[str, Any], countries: List[str]) -> str:
    """Cache key: hash of the relevant profile fields + country set.
    Phase 6.7 — also include new structure fields (primary_applicant, spouse, marital_status)
    so edits to the spouse panel correctly invalidate the cache.
    """
    keep = {
        # Phase 6.7 canonical fields
        "marital_status": profile.get("marital_status"),
        "primary_applicant": profile.get("primary_applicant"),
        "spouse": profile.get("spouse"),
        "dependents": profile.get("dependents"),
        # Legacy projection (kept for legacy profiles still at schema_version 1)
        "basic_info": profile.get("basic_info"),
        "professional": profile.get("professional"),
        "education": profile.get("education"),
        "language_proficiency": profile.get("language_proficiency"),
        "family": profile.get("family"),
        "additional_factors": profile.get("additional_factors"),
        "countries": sorted(countries),
    }
    blob = json.dumps(keep, default=str, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


# ════════════════════════════════════════════════════════════════
# Request Models
# ════════════════════════════════════════════════════════════════
class RunRequest(BaseModel):
    profile_id: str
    mode: Optional[str] = None  # specific | top_3 | custom | top_5  (auto-uses profile.preferences if omitted)
    specific_country: Optional[str] = None
    custom_countries: List[str] = Field(default_factory=list)
    force: bool = False  # bypass cache


# ════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════
def _resolve_countries_to_analyze(
    profile: Dict[str, Any], mode: Optional[str], specific: Optional[str], custom: List[str]
) -> List[str]:
    """Returns list of country codes to analyze based on chosen mode."""
    prefs = profile.get("preferences") or {}
    chosen_mode = mode or prefs.get("search_mode") or "top_3"

    if chosen_mode == "specific":
        code = (specific or prefs.get("specific_country") or "").upper()
        if not code:
            raise HTTPException(status_code=400, detail="Specific mode requires a country code")
        return [code]
    if chosen_mode == "custom":
        codes = [c.upper() for c in (custom or prefs.get("custom_countries") or []) if c]
        if len(codes) < 2:
            raise HTTPException(status_code=400, detail="Custom mode requires at least 2 country codes")
        return codes[:5]  # hard-cap at 5
    if chosen_mode == "top_5":
        return ["AU", "CA", "NZ", "UK", "US"]
    # default top_3
    return ["AU", "CA", "NZ"]


async def _analyze_one_country(
    profile: Dict[str, Any], country_code: str, session_id: str
) -> Dict[str, Any]:
    """Runs Custom Rules + Claude enrichment for a single country.
    Returns a merged country result. Wrapped in timeout."""
    country = await countries_col.find_one({"country_code": country_code.upper()})
    if not country:
        return {
            "country_code": country_code.upper(),
            "country": country_code,
            "error": "Country not in knowledge base — admin needs to seed it",
            "overall_verdict": "unavailable",
        }
    if not country.get("is_active", True):
        return {
            "country_code": country_code.upper(),
            "country": country.get("country"),
            "country_flag": country.get("country_flag_emoji"),
            "error": "Country is currently disabled in admin settings",
            "overall_verdict": "unavailable",
        }

    # Pure rules first
    rules_out = analyze_country_rules(profile, country)

    # Then Claude enrichment (best-effort)
    try:
        enrichment = await asyncio.wait_for(
            claude_enrich(profile, country, rules_out, session_id=f"{session_id}-{country_code.upper()}"),
            timeout=PARALLEL_TIMEOUT_PER_COUNTRY,
        )
    except asyncio.TimeoutError:
        from core.eligibility_ai import _fallback_enrichment
        enrichment = _fallback_enrichment(rules_out, reason="ai_timeout")

    # Final merged shape
    return {
        **rules_out,
        "ai_enrichment": enrichment,
    }


def _rank_countries(country_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort countries by success_prediction.score desc; failed/unavailable last."""
    def sort_key(c: Dict[str, Any]) -> tuple:
        if c.get("error"):
            return (3, 0)
        sp = c.get("success_prediction") or {}
        verdict = c.get("overall_verdict", "ineligible")
        verdict_rank = {"eligible": 0, "marginal": 1, "ineligible": 2}.get(verdict, 3)
        return (verdict_rank, -1 * (sp.get("score") or 0))
    return sorted(country_results, key=sort_key)


# ════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════
@router.post("/run")
async def run_assessment(req: RunRequest, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    profile = await profiles_col.find_one({"id": req.profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Permission: same as profile access
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and profile.get("created_by") != current_user["id"] and profile.get("pa_partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorised to assess this profile")

    countries_to_analyze = _resolve_countries_to_analyze(profile, req.mode, req.specific_country, req.custom_countries)
    cache_key = _profile_hash(profile, countries_to_analyze)

    # Cache check
    if not req.force:
        cached = await assessments_col.find_one(
            {"profile_id": req.profile_id, "cache_key": cache_key, "created_at": {"$gt": datetime.now(timezone.utc) - timedelta(hours=CACHE_HOURS)}},
            sort=[("created_at", -1)],
        )
        if cached:
            return {**_strip(cached), "from_cache": True}

    # Parallel analysis
    session_id = f"elg-{req.profile_id}-{uuid.uuid4().hex[:6]}"
    started = datetime.now(timezone.utc)
    try:
        results = await asyncio.gather(
            *[_analyze_one_country(profile, cc, session_id) for cc in countries_to_analyze],
            return_exceptions=True,
        )
    except Exception as e:
        logger.error(f"Parallel analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Analysis engine failed")

    country_results: List[Dict[str, Any]] = []
    for cc, r in zip(countries_to_analyze, results):
        if isinstance(r, Exception):
            country_results.append({
                "country_code": cc.upper(),
                "country": cc,
                "error": f"Analysis failed: {type(r).__name__}",
                "overall_verdict": "unavailable",
            })
        else:
            country_results.append(r)

    ranked = _rank_countries(country_results)
    best_match = ranked[0] if ranked and not ranked[0].get("error") else None

    finished = datetime.now(timezone.utc)
    duration_seconds = (finished - started).total_seconds()

    assessment_id = f"AST-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    # Phase 6.7 — capture profile snapshots so the results UI can clearly separate
    # the PRIMARY APPLICANT analysis from SPOUSE INFORMATION without re-fetching.
    primary_applicant_snapshot = profile.get("primary_applicant") or {
        # Legacy fallback — synthesize from flat fields
        "personal": {
            "full_name": (profile.get("basic_info") or {}).get("full_name") or profile.get("name"),
            "age": (profile.get("basic_info") or {}).get("age"),
            "current_country": (profile.get("basic_info") or {}).get("current_country"),
        },
        "professional": profile.get("professional") or {},
        "education": profile.get("education") or {},
        "language": profile.get("language_proficiency") or {},
    }
    spouse_snapshot = profile.get("spouse")
    marital_status = profile.get("marital_status") or (profile.get("basic_info") or {}).get("marital_status") or "single"

    doc = {
        "id": assessment_id,
        "profile_id": req.profile_id,
        "profile_name": profile.get("name"),
        # Phase 6.7 snapshots (used by results UI to render the Spouse Info panel)
        "marital_status": marital_status,
        "primary_applicant_snapshot": primary_applicant_snapshot,
        "spouse_snapshot": spouse_snapshot,
        "cache_key": cache_key,
        "mode_used": req.mode or (profile.get("preferences") or {}).get("search_mode") or "top_3",
        "countries_analyzed": countries_to_analyze,
        "results": country_results,
        "ranked": ranked,
        "best_match": {
            "country_code": best_match.get("country_code") if best_match else None,
            "country": best_match.get("country") if best_match else None,
            "country_flag": best_match.get("country_flag") if best_match else None,
            "score": (best_match.get("success_prediction") or {}).get("score") if best_match else 0,
            "label": (best_match.get("success_prediction") or {}).get("label") if best_match else "low",
            "recommended_visa": best_match.get("recommended_visa") if best_match else None,
            "narrative": (best_match.get("ai_enrichment") or {}).get("narrative") if best_match else "",
        } if best_match else None,
        "duration_seconds": round(duration_seconds, 2),
        "created_at": started,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name"),
    }
    await assessments_col.insert_one(doc)

    # Update profile status → assessed + link assessment
    await profiles_col.update_one(
        {"id": req.profile_id},
        {"$set": {"status": "assessed", "assessment_id": assessment_id, "updated_at": finished}},
    )

    return {**_strip(doc), "from_cache": False}


@router.get("/{assessment_id}")
async def get_assessment(assessment_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    doc = await assessments_col.find_one({"id": assessment_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Assessment not found")
    # Permission: same as the profile
    profile = await profiles_col.find_one({"id": doc.get("profile_id")}, {"_id": 0, "created_by": 1, "pa_partner_id": 1, "pa_created_by_user_id": 1})
    role = _user_role(current_user)
    is_admin = role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])
    if not is_admin and (not profile or (profile.get("created_by") != current_user["id"] and profile.get("pa_partner_id") != current_user["id"])):
        raise HTTPException(status_code=403, detail="Not authorised")
    return _strip(doc)


@router.get("/profile/{profile_id}")
async def latest_for_profile(profile_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    doc = await assessments_col.find_one({"profile_id": profile_id}, sort=[("created_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="No assessment found for this profile")
    return _strip(doc)


@router.post("/{assessment_id}/re-run")
async def rerun_assessment(assessment_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    existing = await assessments_col.find_one({"id": assessment_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Assessment not found")
    req = RunRequest(profile_id=existing["profile_id"], mode=existing.get("mode_used"),
                     custom_countries=existing.get("countries_analyzed", []), force=True)
    return await run_assessment(req, current_user)


@router.get("/{assessment_id}/insights")
async def insights(assessment_id: str, current_user: dict = Depends(get_current_user)):
    """Compact view — used by PA detail page + dashboards."""
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    doc = await assessments_col.find_one({"id": assessment_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Assessment not found")
    best = doc.get("best_match") or {}
    return {
        "assessment_id": assessment_id,
        "profile_id": doc.get("profile_id"),
        "profile_name": doc.get("profile_name"),
        "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else doc.get("created_at"),
        "best_country": best.get("country"),
        "best_country_code": best.get("country_code"),
        "best_country_flag": best.get("country_flag"),
        "best_score": best.get("score"),
        "best_label": best.get("label"),
        "best_visa": (best.get("recommended_visa") or {}).get("name"),
        "best_narrative": best.get("narrative"),
        "countries_analyzed": doc.get("countries_analyzed", []),
    }


@router.get("")
async def list_assessments(
    profile_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    query: Dict[str, Any] = {}
    role = _user_role(current_user)
    if role not in ("admin", "admin_owner") and "*" not in (current_user.get("permissions") or []):
        query["created_by"] = current_user["id"]
    if profile_id:
        query["profile_id"] = profile_id

    items = []
    async for a in assessments_col.find(query).sort("created_at", -1).limit(limit):
        items.append({
            "id": a.get("id"),
            "profile_id": a.get("profile_id"),
            "profile_name": a.get("profile_name"),
            "mode_used": a.get("mode_used"),
            "countries_analyzed": a.get("countries_analyzed", []),
            "best_match": a.get("best_match"),
            "duration_seconds": a.get("duration_seconds"),
            "created_at": a.get("created_at"),
            "created_by_name": a.get("created_by_name"),
        })
        if isinstance(items[-1]["created_at"], datetime):
            items[-1]["created_at"] = items[-1]["created_at"].isoformat()
    return {"items": items, "count": len(items)}
