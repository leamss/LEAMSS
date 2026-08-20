"""Smart Sales Helper — Phase 6 v2 Part 3: AI Helpers (Resume Parser + Occupation Suggester).

LLM-only suggestions, never auto-decisions. Sales person reviews and selects.

Endpoints:
  POST /api/sales/ai/suggest-occupation — free-text description → top 3-5 code suggestions
  (Resume parser already lives at /api/eligibility/profiles/resume-extract — reused.)
"""
import json
import logging
import os
import re
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

    # Smart Pre-Filtering: Rank and select top 35 most relevant candidates
    # Reduces prompt from 150KB (40k tokens) to 3KB (500 tokens) -> 10x faster response time!
    desc_clean = req.description.strip().lower()
    desc_tokens = set(re.findall(r'\b[a-z]{3,}\b', desc_clean))

    def _score_candidate(a: dict) -> int:
        score = 0
        t_low = (a.get("title") or "").lower()
        g_low = (a.get("group") or "").lower()
        alts = [x.lower() for x in (a.get("alt") or [])]

        if t_low and t_low in desc_clean:
            score += 60
        for alt_title in alts:
            if alt_title and alt_title in desc_clean:
                score += 50
        for tok in re.findall(r'\b[a-z]{3,}\b', t_low):
            if tok in desc_tokens:
                score += 15
        for tok in re.findall(r'\b[a-z]{3,}\b', g_low):
            if tok in desc_tokens:
                score += 5
        return score

    scored_candidates = sorted(available_slim, key=_score_candidate, reverse=True)
    # Take top 20 candidates (or all if fewer) for ultra-fast < 2.5s generation
    top_candidates = scored_candidates[:20] if len(scored_candidates) > 20 else scored_candidates

    user_prompt = (
        "## CANDIDATE DESCRIPTION\n"
        + req.description.strip()
        + "\n\n## CANDIDATES LIST\n```json\n"
        + json.dumps(top_candidates, ensure_ascii=False)
        + f"\n```\n\nSuggest the top {req.max_suggestions} matching codes. Return concise JSON only with code, title, confidence, reasoning, assessing_body, pathway."
    )

    client = AsyncOpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
        http_client=httpx.AsyncClient(verify=False, timeout=60)
    )

    try:
        response = await client.chat.completions.create(
            model="sonar",
            messages=[
                {"role": "system", "content": "You are an Australian immigration assistant. Return concise JSON only."},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=600,
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
        parsed["_ai_model"] = "sonar"

        return parsed
    
    except Exception as e:
      import traceback

      traceback.print_exc()

      logger.exception("Perplexity Error")

      raise HTTPException(
        status_code=500,
        detail=str(e)
    )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Occupation suggester error: {e}")

        raise HTTPException(
            status_code=502,
            detail=f"AI call failed: {type(e).__name__}: {str(e)[:150]}",
        )
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
      "destination_region_match": true|false
    }
  ],
  "tip": "1-sentence sales advice"
}
"""


class AtlasAutoSuggestRequest(BaseModel):
    description: str = Field(..., min_length=15, max_length=2000)
    country_code: str = Field("CA", description="AU / CA / NZ — the destination country")
    region_code: Optional[str] = Field(None, description="Optional state/province: NSW/VIC/BC/ON/etc")
    max_suggestions: int = Field(5, ge=1, le=8)


@router.post("/atlas-auto-suggest")
async def atlas_auto_suggest(req: AtlasAutoSuggestRequest, current_user: dict = Depends(get_current_user)):
    """Phase 10.3 → 10.7 — Multi-country Atlas Auto-Suggest.

    Free-text → top occupation matches enriched with country-specific Atlas data.
    Works across AU (ANZSCO 6-digit), CA (NOC 5-digit), NZ (ANZSCO 6-digit).

    Hybrid LLM router: routes to Haiku 4.5 (fast, cheap) via `atlas_auto_suggest`.
    """
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not PERPLEXITY_API_KEY:
        raise HTTPException(
        status_code=500,
        detail="PERPLEXITY_API_KEY not configured"
    )

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

    # Slim list — cap to ~600 codes per country to keep prompt size reasonable
    available: List[Dict[str, Any]] = []
    async for occ in db["occupation_master"].find(
        {"country_code": country, "status": {"$ne": "superseded"}},
        {"_id": 0, "code": 1, "title": 1, "teer_category": 1, "skill_level": 1,
         "alternative_titles": 1, "hierarchy": 1, priority_match_key: 1, "state_nomination": 1},
    ):
        # If region_code given, prefer codes targeted by that region
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
            "code": occ.get("code"),
            "title": occ.get("title"),
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

    available_slim = [{k: v for k, v in a.items() if not k.startswith("_")} for a in available]

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

    # try:
    #     from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    # except ImportError as e:
    #     raise HTTPException(status_code=500, detail=f"emergentintegrations not installed: {e}")

    try:
        # chat = LlmChat(
        #     api_key=EMERGENT_LLM_KEY,
        #     session_id=f"atlas-suggest-{country.lower()}-{current_user.get('id','anon')[:8]}",
        #     system_message=ATLAS_AUTO_SUGGEST_SYSTEM_PROMPT,
        # ).with_model("anthropic", model_for("atlas_auto_suggest"))
        # response = await chat.send_message(UserMessage(text=user_prompt))
        # raw = (str(response) if response is not None else "").strip()
        # if raw.startswith("```"):
        #     raw = raw.strip("`").lstrip("json").strip()
        client = AsyncOpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai",
            http_client=httpx.AsyncClient(verify=False, timeout=60)
        )

        try:
            response = await client.chat.completions.create(
                model="sonar",
                messages=[
                    {
                        "role": "system",
                        "content": ATLAS_AUTO_SUGGEST_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.2,
                max_tokens=1800,
            )

            raw = response.choices[0].message.content.strip()
            print("=" * 100)
            print(raw)
            print("=" * 100)
            print("Length:", len(raw))
            print("Ends with }:", raw.endswith("}"))

            if raw.startswith("```"):
                raw = raw.strip("`").lstrip("json").strip()

            first = raw.find("{")
            last = raw.rfind("}")

            if first == -1 or last == -1:
                raise HTTPException(
                    status_code=502,
                    detail=f"AI returned non-JSON: {raw[:200]}"
                )

            parsed = json.loads(raw[first:last + 1])

            # Cross-check that suggested codes actually exist
            valid_codes = {a["code"] for a in available}

            for s in parsed.get("suggestions", []):
                code = str(s.get("code", ""))
                s["_verified"] = code in valid_codes

            parsed["_ai_status"] = "ok"
            parsed["_ai_model"] = "sonar"

            # DON'T return here
            # Continue to the Atlas enrichment section below
          

           

        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=502,
                detail=f"AI returned malformed JSON: {e}"
            )

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Occupation suggester error: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"AI call failed: {type(e).__name__}: {str(e)[:150]}"
            )
        first = raw.find("{")
        last = raw.rfind("}")
        if first == -1 or last == -1:
            raise HTTPException(status_code=502, detail=f"AI returned non-JSON: {raw[:200]}")
        parsed = json.loads(raw[first:last + 1])

        # Enrich each suggestion with full country-specific Atlas data
        valid_codes = {a["code"] for a in available}
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

            # Build country-flavoured atlas payload
            atlas: Dict[str, Any] = {
                "country_code": country,
                "skill_level_or_teer": full.get("teer_category") if country == "CA" else full.get("skill_level"),
                "major_group": (full.get("hierarchy") or {}).get("major_group", {}),
                "classification": classification_label,
            }
            if country == "CA":
                atlas["teer_category"] = full.get("teer_category")
                atlas["teer_label"] = full.get("teer_label")
                atlas["ee_eligibility"] = full.get("ee_eligibility") or {}
                # Sort PNPs by region preference
                pnps = full.get("pnp_eligibility") or []
                if req.region_code:
                    rc = req.region_code.upper()
                    pnps = sorted(pnps, key=lambda p: 0 if (p.get("province_code") or "").upper() == rc else 1)
                atlas["pnp_eligibility"] = pnps
                atlas["ircc_round_cutoffs"] = full.get("ircc_round_cutoffs") or {}
                atlas["regional_pilot_eligibility"] = full.get("regional_pilot_eligibility") or []
                atlas["quebec_eligibility"] = full.get("quebec_eligibility") or {}
            elif country == "AU":
                atlas["assessing_authority"] = full.get("assessing_authority") or {}
                atlas["skillselect_tier"] = full.get("skillselect_tier")
                atlas["state_nomination"] = full.get("state_nomination") or {}
                atlas["visa_pathways"] = full.get("visa_pathways") or []
                atlas["min_invitation_points"] = full.get("min_invitation_points") or {}
            else:  # NZ
                atlas["assessing_authority"] = full.get("assessing_authority") or {}
                atlas["visa_pathways"] = full.get("visa_pathways") or []

            enriched.append({**s, "atlas": atlas})

        return {
            "suggestions": enriched,
            "tip": parsed.get("tip", ""),
            "_ai_model": model_for("atlas_auto_suggest"),
            "_total_candidates_considered": len(available),
            "_country": country,
            "_region_filter": req.region_code,
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned malformed JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Atlas auto-suggest error: {e}")
        raise HTTPException(status_code=502, detail=f"AI call failed: {type(e).__name__}: {str(e)[:150]}")
