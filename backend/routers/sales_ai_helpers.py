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
        aa = occ.get("assessing_authority") or {}
        hierarchy = occ.get("hierarchy") or {}
        pathway_lists = (occ.get("visa_pathways") or {}).get("pathway_lists") or []
        available_codes.append({
            "country_code": occ.get("country_code"),
            "code": occ.get("code"),
            "title": occ.get("title"),
            "group": hierarchy.get("unit_group_name"),
            "assessing_body": aa.get("name"),
            "pathway": pathway_lists[0] if pathway_lists else None,
            "alternative_titles": occ.get("alternative_titles") or [],
        })

    _OCC_CACHE[cache_key] = (now_t, available_codes)
    return available_codes


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
SUGGESTER_SYSTEM_PROMPT = """You are an immigration occupation-code expert.

A sales consultant will describe a candidate's profession in plain English.
Your task: from the AVAILABLE_CODES list provided, suggest the TOP 3-5 codes that
best match the candidate's CURRENT job and duties.

═══════════════════════════════════════════════════════════════════
ABSOLUTE RULES
═══════════════════════════════════════════════════════════════════

🔴 RULE 1 — Suggest, DO NOT decide. The sales consultant verifies and picks.
🔴 RULE 2 — Match based on the candidate's CURRENT job, duties and industry.
   IGNORE education unless the current job is clearly NEW (e.g., degree unrelated
   to current work).
🔴 RULE 3 — Only suggest codes from the AVAILABLE_CODES list. Do NOT invent codes.
🔴 RULE 4 — Be honest about confidence: HIGH (clear duty/title match),
   MEDIUM (related but adjacent), LOW (loose match).
🔴 RULE 5 — When relevant, mention concerns or considerations the consultant should
   discuss with the client (e.g., "this code requires 2 years post-qualification work
   experience", "VETASSESS Skills Assessment can take 10-12 weeks").

═══════════════════════════════════════════════════════════════════
OUTPUT FORMAT — return ONLY this JSON, no markdown, no prose:
═══════════════════════════════════════════════════════════════════
{
  "suggestions": [
    {
      "country_code": "AU|CA|NZ",
      "code": "225113",
      "title": "Marketing Specialist",
      "confidence": "high|medium|low",
      "reasoning": "Specific 2-3 sentence explanation of why this code matches.",
      "considerations": "Any caveats, processing time concerns, or things to verify with the client.",
      "assessing_body": "VETASSESS",
      "pathway": "STSOL"
    }
  ],
  "general_advice": "1-2 sentences advising the consultant on which to prioritise and why."
}
"""


class SuggestRequest(BaseModel):
    description: str = Field(..., min_length=20, max_length=2000, description="Free-text description of the candidate's profession")
    country_codes: Optional[List[str]] = Field(None, description="Restrict to these countries (default: all)")
    max_suggestions: int = Field(5, ge=1, le=8)


@router.post("/suggest-occupation")
async def suggest_occupation(
    req: SuggestRequest,
    current_user: dict = Depends(get_current_user)
):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")

    api_key = (os.getenv("PERPLEXITY_API_KEY") or PERPLEXITY_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="PERPLEXITY_API_KEY not configured"
        )

    # Build the available occupation list from fast in-memory cache
    available_codes = await _get_available_codes(req.country_codes)

    if not available_codes:
        raise HTTPException(
            status_code=400,
            detail="No occupation codes loaded in the knowledge base",
        )

    import re
    desc_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', req.description.lower()))

    def _score_occ(a: dict) -> int:
        title_lower = (a.get("title") or "").lower()
        group_lower = (a.get("group") or "").lower()
        alts = [str(x).lower() for x in (a.get("alternative_titles") or [])]
        code = str(a.get("code") or "")

        score = 0
        for w in desc_words:
            if w in title_lower:
                score += 15
            elif any(w in alt for alt in alts):
                score += 10
            elif w in group_lower:
                score += 5
            elif w == code:
                score += 25
        return score

    # Sort available codes by relevance score
    scored_codes = sorted(available_codes, key=_score_occ, reverse=True)
    top_codes = scored_codes[:45] if len(scored_codes) > 45 else scored_codes

    available_slim = [
        {
            "country_code": a["country_code"],
            "code": a["code"],
            "title": a["title"],
            "group": a["group"],
            "assessing_body": a.get("assessing_body"),
            "pathway": a.get("pathway"),
            "alt": a.get("alternative_titles")[:2],
        }
        for a in top_codes
    ]

    user_prompt = (
        "## CANDIDATE DESCRIPTION (sales consultant's words)\n"
        + req.description.strip()
        + "\n\n## AVAILABLE_CODES (only suggest from this list)\n```json\n"
        + json.dumps(available_slim, ensure_ascii=False)
        + f"\n```\n\nSuggest the top {req.max_suggestions} codes. Return JSON only."
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

        # Verify returned codes exist
        valid_set = {
            (a["country_code"], str(a["code"]))
            for a in available_codes
        }

        for s in parsed.get("suggestions", []):
            cc = s.get("country_code", "").upper()
            code = str(s.get("code", ""))
            s["country_code"] = cc
            s["_verified"] = (cc, code) in valid_set

        parsed.setdefault("_ai_status", "ok")
        parsed["_ai_model"] = "sonar-pro"

        return parsed

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Perplexity suggestion error: %s", e)
        # Safe fallback: return top scored codes from database so the consultant is never blocked
        fallback_suggestions = []
        for a in top_codes[:req.max_suggestions]:
            fallback_suggestions.append({
                "country_code": a.get("country_code", "AU"),
                "code": str(a.get("code", "")),
                "title": a.get("title", ""),
                "confidence": "medium",
                "reasoning": "Selected by keyword relevance matching based on candidate profile description.",
                "considerations": "Please review assessing authority criteria and visa availability.",
                "assessing_body": a.get("assessing_body") or "",
                "pathway": a.get("pathway") or "",
                "_verified": True,
            })
        return {
            "suggestions": fallback_suggestions,
            "general_advice": "Recommended matches from occupation database based on profile description.",
            "_ai_status": "fallback",
            "_ai_model": "knowledge-base-heuristic"
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
                score += 15
            elif any(w in alt for alt in alts):
                score += 10
            elif w == code_str:
                score += 25
        if a.get("_region_match"):
            score += 8
        return score

    scored_available = sorted(available, key=_score_atlas, reverse=True)
    top_available = scored_available[:50]

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

