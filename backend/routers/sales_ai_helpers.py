"""Smart Sales Helper — Phase 6 v2 Part 3: AI Helpers (Resume Parser + Occupation Suggester).

LLM-only suggestions, never auto-decisions. Sales person reviews and selects.

Endpoints:
  POST /api/sales/ai/suggest-occupation — free-text description → top 3-5 code suggestions
  (Resume parser already lives at /api/eligibility/profiles/resume-extract — reused.)
"""
import json
import logging
import os
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.ai_models import model_for

router = APIRouter(prefix="/sales/ai", tags=["Smart Sales Helper - AI Helpers"])
logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
# Phase 9.3 — Haiku 4.5 for high-frequency, low-stakes typeahead suggestions
CLAUDE_MODEL = model_for("occupation_suggester")

ROLE_SALES = {
    "admin", "admin_owner", "sales_executive", "sr_sales_executive",
    "sales_manager", "sales_head", "partner", "case_manager",
}


def _user_role(user: dict) -> str:
    return user.get("rbac_role") or user.get("role") or ""


def _can_access(user: dict) -> bool:
    return _user_role(user) in ROLE_SALES or "*" in (user.get("permissions") or [])


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
async def suggest_occupation(req: SuggestRequest, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")

    # Build the available_codes list from occupation_master (Phase 6.9.1 — Single Source of Truth)
    query: Dict[str, Any] = {"status": {"$ne": "superseded"}}
    if req.country_codes:
        query["country_code"] = {"$in": [c.upper() for c in req.country_codes]}
    available_codes: List[Dict[str, Any]] = []
    async for occ in db["occupation_master"].find(query, {"_id": 0}):
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

    if not available_codes:
        raise HTTPException(status_code=400, detail="No occupation codes loaded in the knowledge base")

    # Slim payload — only essentials
    available_slim = [
        {
            "country_code": a["country_code"],
            "code": a["code"],
            "title": a["title"],
            "group": a["group"],
            "assessing_body": a.get("assessing_body"),
            "pathway": a.get("pathway"),
            "alt": a.get("alternative_titles")[:3],
        } for a in available_codes
    ]

    user_prompt = (
        "## CANDIDATE DESCRIPTION (sales consultant's words)\n"
        + req.description.strip()
        + "\n\n## AVAILABLE_CODES (only suggest from this list)\n```json\n"
        + json.dumps(available_slim, ensure_ascii=False)
        + f"\n```\n\nSuggest the top {req.max_suggestions} codes. Return JSON only."
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"emergentintegrations not installed: {e}")

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"suggest-{current_user.get('id','anon')[:8]}",
            system_message=SUGGESTER_SYSTEM_PROMPT,
        ).with_model("anthropic", CLAUDE_MODEL)
        response = await chat.send_message(UserMessage(text=user_prompt))
        raw = (str(response) if response is not None else "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        first = raw.find("{")
        last = raw.rfind("}")
        if first == -1 or last == -1:
            raise HTTPException(status_code=502, detail=f"AI returned non-JSON: {raw[:200]}")
        parsed = json.loads(raw[first:last + 1])
        # Cross-check that suggested codes actually exist in available_codes
        valid_set = {(a["country_code"], a["code"]) for a in available_codes}
        for s in parsed.get("suggestions", []):
            cc = s.get("country_code", "").upper()
            code = str(s.get("code", ""))
            s["country_code"] = cc
            s["_verified"] = (cc, code) in valid_set
        parsed["_ai_status"] = "ok"
        parsed["_ai_model"] = CLAUDE_MODEL
        return parsed
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned malformed JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Occupation suggester error: {e}")
        raise HTTPException(status_code=502, detail=f"AI call failed: {type(e).__name__}: {str(e)[:150]}")



# ════════════════════════════════════════════════════════════════
# Phase 10.3 — ATLAS AUTO-SUGGEST (free-text → NOC + PNP + EE intel)
# ════════════════════════════════════════════════════════════════
ATLAS_AUTO_SUGGEST_SYSTEM_PROMPT = """You are a Canadian immigration NOC matching expert.

A sales rep will describe a candidate in plain English, optionally with a province
preference. Your task: from the CA_NOC_LIST, return the TOP 3-5 NOC codes that
best match the candidate's CURRENT occupation.

ABSOLUTE RULES
🔴 RULE 1 — Match on the candidate's CURRENT job duties, NOT their degree.
🔴 RULE 2 — Only suggest codes from CA_NOC_LIST. Do NOT invent codes.
🔴 RULE 3 — If a destination province is mentioned, prefer NOCs that province targets.
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
      "destination_province_match": true|false
    }
  ],
  "tip": "1-sentence sales advice"
}
"""


class AtlasAutoSuggestRequest(BaseModel):
    description: str = Field(..., min_length=15, max_length=2000)
    province_code: Optional[str] = Field(None, description="Optional: BC/ON/AB/SK/MB/NB/NS/PE/NL/YT/NT")
    max_suggestions: int = Field(5, ge=1, le=8)


@router.post("/atlas-auto-suggest")
async def atlas_auto_suggest(req: AtlasAutoSuggestRequest, current_user: dict = Depends(get_current_user)):
    """Phase 10.3 — Canada Atlas Auto-Suggest.

    Free-text → top NOC matches enriched with TEER + IRCC EE eligibility + PNP
    eligibility. Optimised for Canada with the 2026 IRCC/PNP intel baked in.

    Hybrid LLM router: routes to Haiku 4.5 (fast, cheap) via `atlas_auto_suggest`.
    """
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")

    # Slim list of CA NOCs only (cap to ~300 to keep prompt tight)
    available: List[Dict[str, Any]] = []
    async for occ in db["occupation_master"].find(
        {"country_code": "CA", "status": {"$ne": "superseded"}},
        {"_id": 0, "code": 1, "title": 1, "teer_category": 1, "alternative_titles": 1, "pnp_eligibility": 1, "hierarchy": 1},
    ):
        # If province_code given, prefer codes targeted by that province
        prov_match = False
        if req.province_code:
            for p in (occ.get("pnp_eligibility") or []):
                if (p.get("province_code") or "").upper() == req.province_code.upper():
                    prov_match = True
                    break
        major_group = (occ.get("hierarchy") or {}).get("major_group", {})
        available.append({
            "code": occ.get("code"),
            "title": occ.get("title"),
            "teer": occ.get("teer_category"),
            "major_group": major_group.get("title") if isinstance(major_group, dict) else None,
            "alt": (occ.get("alternative_titles") or [])[:5],
            "_prov_match": prov_match,
        })

    if not available:
        raise HTTPException(status_code=400, detail="No CA NOC codes in occupation_master")

    # Strip the helper flag before sending to LLM
    available_slim = [{k: v for k, v in a.items() if not k.startswith("_")} for a in available]

    user_prompt = (
        f"## CANDIDATE DESCRIPTION\n{req.description.strip()}\n\n"
        + (f"## DESTINATION PROVINCE PREFERENCE\n{req.province_code.upper()}\n\n" if req.province_code else "")
        + "## CA_NOC_LIST\n```json\n"
        + json.dumps(available_slim, ensure_ascii=False)
        + f"\n```\n\nSuggest the top {req.max_suggestions} NOCs. Return JSON only."
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"emergentintegrations not installed: {e}")

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"atlas-suggest-{current_user.get('id','anon')[:8]}",
            system_message=ATLAS_AUTO_SUGGEST_SYSTEM_PROMPT,
        ).with_model("anthropic", model_for("atlas_auto_suggest"))
        response = await chat.send_message(UserMessage(text=user_prompt))
        raw = (str(response) if response is not None else "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        first = raw.find("{")
        last = raw.rfind("}")
        if first == -1 or last == -1:
            raise HTTPException(status_code=502, detail=f"AI returned non-JSON: {raw[:200]}")
        parsed = json.loads(raw[first:last + 1])

        # Enrich each suggestion with full Atlas data (EE + PNP eligibility)
        valid_codes = {a["code"] for a in available}
        enriched: List[Dict[str, Any]] = []
        for s in parsed.get("suggestions", []):
            code = str(s.get("code", ""))
            if code not in valid_codes:
                continue
            full = await db["occupation_master"].find_one(
                {"country_code": "CA", "code": code},
                {"_id": 0, "code": 1, "title": 1, "teer_category": 1, "teer_label": 1,
                 "ee_eligibility": 1, "pnp_eligibility": 1, "hierarchy": 1},
            )
            if full:
                # If province_code given, filter PNP eligibility to that province first
                pnps = full.get("pnp_eligibility") or []
                if req.province_code:
                    pc = req.province_code.upper()
                    pnps_sorted = sorted(pnps, key=lambda p: 0 if p.get("province_code") == pc else 1)
                else:
                    pnps_sorted = pnps
                enriched.append({
                    **s,
                    "atlas": {
                        "teer_category": full.get("teer_category"),
                        "teer_label": full.get("teer_label"),
                        "ee_eligibility": full.get("ee_eligibility") or {},
                        "pnp_eligibility": pnps_sorted,
                        "major_group": (full.get("hierarchy") or {}).get("major_group", {}),
                    },
                })

        return {
            "suggestions": enriched,
            "tip": parsed.get("tip", ""),
            "_ai_model": model_for("atlas_auto_suggest"),
            "_total_candidates_considered": len(available),
            "_province_filter": req.province_code,
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned malformed JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Atlas auto-suggest error: {e}")
        raise HTTPException(status_code=502, detail=f"AI call failed: {type(e).__name__}: {str(e)[:150]}")
