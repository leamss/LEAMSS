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
import httpx
from openai import AsyncOpenAI
router = APIRouter(prefix="/sales/ai", tags=["Smart Sales Helper - AI Helpers"])
logger = logging.getLogger(__name__)

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
# Phase 9.3 — Haiku 4.5 for high-frequency, low-stakes typeahead suggestions
# CLAUDE_MODEL = model_for("occupation_suggester")


ROLE_SALES = {
    "admin", "admin_owner", "sales_executive", "sr_sales_executive",
    "sales_manager", "sales_head", "partner", "case_manager",
}


def _user_role(user: dict) -> str:
    return user.get("rbac_role") or user.get("role") or ""


def _can_access(user: dict) -> bool:
    return _user_role(user) in ROLE_SALES or "*" in (user.get("permissions") or [])


def _safe_json_loads(raw: str) -> dict:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.strip("`").lstrip("json").strip()
    first = clean.find("{")
    last = clean.rfind("}")
    if first == -1:
        raise ValueError(f"No JSON object found in AI response")
    sub = clean[first:last + 1]
    try:
        return json.loads(sub)
    except Exception:
        pass
    for tail in ['\n  ]\n}', '\n}', '"\n  ]\n}', '"}\n  ]\n}', '}\n  ]\n}']:
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
    return json.loads(sub)


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

    if not PERPLEXITY_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="PERPLEXITY_API_KEY not configured"
        )

    # Build the available occupation list
    query: Dict[str, Any] = {"status": {"$ne": "superseded"}}

    if req.country_codes:
        query["country_code"] = {
            "$in": [c.upper() for c in req.country_codes]
        }

    available_codes: List[Dict[str, Any]] = []

    async for occ in db["occupation_master"].find(query, {"_id": 0}):
        aa = occ.get("assessing_authority") or {}
        hierarchy = occ.get("hierarchy") or {}
        pathway_lists = (
            occ.get("visa_pathways") or {}
        ).get("pathway_lists") or []

        available_codes.append(
            {
                "country_code": occ.get("country_code"),
                "code": occ.get("code"),
                "title": occ.get("title"),
                "group": hierarchy.get("unit_group_name"),
                "assessing_body": aa.get("name"),
                "pathway": pathway_lists[0] if pathway_lists else None,
                "alternative_titles": occ.get("alternative_titles") or [],
            }
        )

    if not available_codes:
        raise HTTPException(
            status_code=400,
            detail="No occupation codes loaded in the knowledge base",
        )

    available_slim = [
        {
            "country_code": a["country_code"],
            "code": a["code"],
            "title": a["title"],
            "group": a["group"],
            "assessing_body": a.get("assessing_body"),
            "pathway": a.get("pathway"),
            "alt": a.get("alternative_titles")[:3],
        }
        for a in available_codes
    ]

    user_prompt = (
        "## CANDIDATE DESCRIPTION (sales consultant's words)\n"
        + req.description.strip()
        + "\n\n## AVAILABLE_CODES (only suggest from this list)\n```json\n"
        + json.dumps(available_slim, ensure_ascii=False)
        + f"\n```\n\nSuggest the top {req.max_suggestions} codes. Return JSON only."
    )

    client = AsyncOpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
        http_client=httpx.AsyncClient(verify=False, timeout=60)
    )

    try:
        print("Before API call")
        response = await client.chat.completions.create(
    model="sonar-reasoning-pro",
    messages=[
        {"role": "system", "content": SUGGESTER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0,
)

        raw = response.choices[0].message.content.strip()
        print("=" * 100)
        print(repr(raw))
        print("=" * 100)

        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()

        try:
            parsed = json.loads(raw)

        except json.JSONDecodeError:
            first = raw.find("{")
            last = raw.rfind("}")

            if first == -1 or last == -1:
                raise HTTPException(
                    status_code=502,
                    detail=f"AI returned non-JSON:\n{raw}",
                )

            parsed = json.loads(raw[first:last + 1])

        # Verify returned codes exist
        valid_set = {
            (a["country_code"], a["code"])
            for a in available_codes
        }

        for s in parsed.get("suggestions", []):
            cc = s.get("country_code", "").upper()
            code = str(s.get("code", ""))

            s["country_code"] = cc
            s["_verified"] = (cc, code) in valid_set

        parsed["_ai_status"] = "ok"
        parsed["_ai_model"] = "sonar-reasoning-pro"

        return parsed
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.exception("Perplexity Error")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
