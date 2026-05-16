"""Phase 6.3 — Claude AI Enrichment for Eligibility Analysis.

Wraps the Custom Rules output with Claude Sonnet 4.6 reasoning:
  • Validates / cross-checks rule calculations
  • Adds personalised advice + risk factors
  • Identifies edge cases the rules missed
  • Generates "Why this country?" narrative

Falls back gracefully to rules-only if Claude API fails.
Cached per (profile_id, country_code) for 24h to control cost.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

CLAUDE_MODEL = "claude-sonnet-4-6"  # cost-efficient for structured analysis
CLAUDE_TIMEOUT_SECONDS = 25


SYSTEM_PROMPT = """You are an expert immigration consultant analysing a candidate profile.

You will receive:
  1. A candidate profile (JSON)
  2. Country immigration rules (JSON)
  3. A deterministic Custom Rules Engine output (points calc, occupation match, eligibility verdict)

Your job is to ENRICH the rules output, NOT recalculate it. Return ONLY a JSON object with these keys:

{
  "narrative": "2-3 sentence executive summary of this candidate's prospects in this country",
  "strengths": ["bullet 1", "bullet 2", ...],
  "weaknesses": ["bullet 1", "bullet 2", ...],
  "recommended_visa_reasoning": "Why the rule-engine's recommended visa is the right fit (or what's better)",
  "occupation_code_reasoning": "Why the matched occupation code fits (or suggest a better one if rules missed it)",
  "skill_body_advice": "Advice on the recommended skill assessment body — what to prepare",
  "personalised_advice": ["Concrete next-step 1", "Concrete next-step 2", ...],
  "risk_factors": ["Risk 1 to flag with the client", "Risk 2", ...],
  "alternative_pathways_in_country": ["Pathway 1 if recommended visa fails", ...],
  "estimated_success_probability_text": "high|medium|low with a 1-sentence rationale that cross-checks the rules-engine label"
}

CRITICAL RULES:
- Be REALISTIC and EVIDENCE-BASED — do not over-promise.
- If the rules engine says "ineligible", do NOT contradict it; instead suggest alternatives.
- Keep each bullet ≤ 25 words.
- Output MUST be valid JSON, no markdown, no commentary outside the JSON.
"""


def _build_user_prompt(profile: Dict[str, Any], country: Dict[str, Any], rules_output: Dict[str, Any]) -> str:
    """Strip country to essentials to reduce token cost."""
    country_slim = {
        "country": country.get("country"),
        "country_code": country.get("country_code"),
        "visa_categories_summary": [
            {"code": v.get("code"), "name": v.get("name"), "type": v.get("type"),
             "pathway_type": v.get("pathway_type"), "min_points": (v.get("eligibility") or {}).get("points_minimum"),
             "is_active": v.get("is_active", True)}
            for v in (country.get("visa_categories") or [])[:8]
        ],
        "skill_bodies_summary": [
            {"name": b.get("name"), "full_name": b.get("full_name"),
             "occupations_count": len(b.get("assesses_occupations") or [])}
            for b in (country.get("skill_assessment_bodies") or [])[:8]
        ],
    }
    return (
        "## CANDIDATE PROFILE\n```json\n"
        + json.dumps(profile, default=str, ensure_ascii=False)
        + "\n```\n\n## COUNTRY RULES (summary)\n```json\n"
        + json.dumps(country_slim, default=str, ensure_ascii=False)
        + "\n```\n\n## CUSTOM RULES ENGINE OUTPUT\n```json\n"
        + json.dumps(rules_output, default=str, ensure_ascii=False)
        + "\n```\n\nReturn the enrichment JSON now."
    )


async def claude_enrich(
    profile: Dict[str, Any],
    country: Dict[str, Any],
    rules_output: Dict[str, Any],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Claude for enrichment. On any failure, return a fallback structure
    derived from the rules output so the UI never breaks.
    """
    if not EMERGENT_LLM_KEY:
        logger.warning("EMERGENT_LLM_KEY missing — skipping Claude enrichment")
        return _fallback_enrichment(rules_output, reason="ai_disabled")

    try:
        # Local import to keep the rest of the app usable if the lib is missing
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except ImportError as e:
        logger.error(f"emergentintegrations not installed: {e}")
        return _fallback_enrichment(rules_output, reason="ai_lib_missing")

    sid = session_id or f"elg-{country.get('country_code', 'XX')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    user_prompt = _build_user_prompt(profile, country, rules_output)

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=sid,
            system_message=SYSTEM_PROMPT,
        ).with_model("anthropic", CLAUDE_MODEL)
        response = await chat.send_message(UserMessage(text=user_prompt))
        raw = (str(response) if response is not None else "").strip()
        # Sometimes models wrap in ```json blocks despite instruction
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        # Find first { and last } to be robust
        first = raw.find("{")
        last = raw.rfind("}")
        if first == -1 or last == -1:
            raise ValueError("Claude returned non-JSON response")
        parsed = json.loads(raw[first:last + 1])
        parsed["_ai_status"] = "ok"
        parsed["_ai_model"] = CLAUDE_MODEL
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Claude JSON parse failed: {e}")
        return _fallback_enrichment(rules_output, reason=f"ai_parse_error:{e}")
    except Exception as e:
        err_text = str(e)
        if "budget" in err_text.lower() or "Budget has been exceeded" in err_text:
            reason = f"ai_budget_exhausted: {err_text[:100]}"
        else:
            reason = f"ai_call_error:{type(e).__name__}: {err_text[:80]}"
        logger.error(f"Claude call failed: {e}")
        return _fallback_enrichment(rules_output, reason=reason)


def _fallback_enrichment(rules: Dict[str, Any], reason: str = "ai_unavailable") -> Dict[str, Any]:
    """Synthesize an enrichment shape from rules output so UI is always renderable."""
    success = rules.get("success_prediction") or {}
    rec = rules.get("recommended_visa") or {}
    occ = (rules.get("occupation") or {}).get("primary") or {}
    body = rules.get("skill_body") or {}

    return {
        "narrative": (
            f"{rules.get('country')} — {success.get('label','unknown')} probability. "
            f"Recommended visa: {rec.get('name') or 'none yet'}. "
            f"Points: {(rules.get('points') or {}).get('total', 0)}."
        ),
        "strengths": list(success.get("factors_positive") or []),
        "weaknesses": list(success.get("factors_negative") or []),
        "recommended_visa_reasoning": f"Visa selected by deterministic rules (verdict: {rec.get('verdict','—')}).",
        "occupation_code_reasoning": (
            f"Code {occ.get('code')} ({occ.get('title')}) matched at "
            f"{int((occ.get('confidence') or 0) * 100)}% confidence on profile tokens."
            if occ else "No occupation code matched — manual review recommended."
        ),
        "skill_body_advice": (
            f"Use {body.get('name')} — fee ~₹{body.get('assessment_fee_inr', 0):,}, "
            f"processing {body.get('processing_time_weeks', '?')} weeks."
            if body else "Skill body could not be auto-identified."
        ),
        "personalised_advice": [
            "Complete a competent-level English test if not done",
            "Gather employment reference letters for all roles",
            "Prepare bachelor degree + transcripts for skill assessment",
        ],
        "risk_factors": [r for r in (rec.get("warnings") or [])] or ["Verify all hard requirements before fee payment"],
        "alternative_pathways_in_country": [],
        "estimated_success_probability_text": (
            f"{success.get('label','medium')} — based on deterministic rules-engine score "
            f"{success.get('score',0)}/100."
        ),
        "_ai_status": "fallback",
        "_ai_fallback_reason": reason,
    }
