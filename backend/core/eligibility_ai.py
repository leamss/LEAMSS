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
  1. A candidate profile (JSON) — has `primary_applicant` (always) and `spouse` (only if marital_status is married/de_facto)
  2. Country immigration rules (JSON)
  3. A deterministic Custom Rules Engine output (points calc, occupation match, eligibility verdict)

═══════════════════════════════════════════════════════════════════
ABSOLUTE RULES — VIOLATING ANY OF THESE IS A CRITICAL FAILURE
═══════════════════════════════════════════════════════════════════

🔴 RULE 1 — ALWAYS analyse the PRIMARY APPLICANT only.
    - The visa recommendation, occupation match, points, and success probability MUST be for `profile.primary_applicant`.
    - NEVER analyse the spouse's career as if they were the applicant.
    - If spouse data is present, mention it ONLY as context for partner points (e.g., "spouse contributes +10 partner points") — do NOT recommend visas for the spouse.

🔴 RULE 2 — Match occupation codes (ANZSCO / NOC / NZ ANZSCO) using the PRIMARY APPLICANT'S CURRENT PROFESSION.
    - The CURRENT job/role (`primary_applicant.professional.current_profession` and `designation`) is the SINGLE source of truth for occupation matching.
    - IGNORE past education or degrees that are unrelated to the current job. Example: a candidate with a B.V.Sc Veterinary degree who is currently a Marketing Specialist MUST be matched as "225113 Marketing Specialist" (ANZSCO) — NOT a Veterinarian code.
    - If the rules engine matched a code based on stale/incorrect data (e.g., it picked Veterinarian because of the degree), CORRECT it in `occupation_code_reasoning` and propose the right code from the country's occupation_codes list.
    - Only if there is NO current profession data, you may fall back to most recent role in `work_history`.

🔴 RULE 3 — Education is contextual, not occupational.
    - A degree (Master's, Bachelor's, Veterinary, etc.) earns education POINTS — it does NOT determine the visa occupation.
    - Mention education only in `strengths`, `weaknesses`, or `personalised_advice` when relevant — never use it to override the occupation match.

🔴 RULE 4 — Spouse points are a BONUS only; never the headline.
    - When spouse contributes points (e.g., +10 for skill_assessment), include it in `strengths` as a single bullet (e.g., "Spouse adds +10 partner points via skill assessment").
    - Do NOT restate the spouse's full career analysis.
    - If spouse does NOT contribute (non_contributing / not_applicable), do not mention them in strengths.

🔴 RULE 5 — Respect the deterministic rules-engine.
    - If the engine says "ineligible", do NOT flip the verdict; suggest alternatives instead.
    - You may CORRECT a wrong occupation match, but do not change the points total or eligibility verdict.

═══════════════════════════════════════════════════════════════════
OUTPUT FORMAT — return ONLY this JSON object, no markdown, no prose:
═══════════════════════════════════════════════════════════════════
{
  "narrative": "2-3 sentence executive summary of the PRIMARY APPLICANT's prospects in this country (mention spouse contribution as a phrase only if it adds points)",
  "strengths": ["bullet 1", "bullet 2", ...],
  "weaknesses": ["bullet 1", "bullet 2", ...],
  "recommended_visa_reasoning": "Why the rule-engine's recommended visa is the right fit for the PRIMARY APPLICANT's CURRENT profession (or what's better)",
  "occupation_code_reasoning": "Why this code matches the PRIMARY APPLICANT's CURRENT profession (Marketing Specialist, Software Engineer, etc.). If the rules engine picked a wrong code based on education, name the corrected code from the country's occupation_codes list.",
  "skill_body_advice": "Advice on the recommended skill assessment body — what to prepare",
  "personalised_advice": ["Concrete next-step 1 for the primary applicant", "Concrete next-step 2", ...],
  "risk_factors": ["Risk 1 to flag with the client", "Risk 2", ...],
  "alternative_pathways_in_country": ["Pathway 1 if recommended visa fails", ...],
  "estimated_success_probability_text": "high|medium|low with a 1-sentence rationale that cross-checks the rules-engine label"
}

OTHER RULES:
- Be REALISTIC and EVIDENCE-BASED — do not over-promise.
- Keep each bullet ≤ 25 words.
- Output MUST be valid JSON, no markdown, no commentary outside the JSON.
"""


def _build_user_prompt(profile: Dict[str, Any], country: Dict[str, Any], rules_output: Dict[str, Any]) -> str:
    """Strip country to essentials to reduce token cost.
    Also explicitly surface the PRIMARY APPLICANT's CURRENT PROFESSION so Claude
    cannot miss it (Phase 6.7 bug fix — was matching codes based on education).
    """
    primary = profile.get("primary_applicant") or {}
    primary_personal = primary.get("personal") or {}
    primary_prof = primary.get("professional") or {}
    primary_edu = primary.get("education") or {}
    # Legacy fallbacks
    legacy_prof = profile.get("professional") or {}
    legacy_edu = profile.get("education") or {}
    legacy_bi = profile.get("basic_info") or {}

    profile_focus = {
        "MARITAL_STATUS": profile.get("marital_status") or legacy_bi.get("marital_status"),
        "PRIMARY_APPLICANT": {
            "name": primary_personal.get("full_name") or profile.get("name"),
            "age": primary_personal.get("age") or legacy_bi.get("age"),
            "CURRENT_PROFESSION": primary_prof.get("current_profession") or legacy_prof.get("current_profession"),
            "CURRENT_DESIGNATION": primary_prof.get("designation") or legacy_prof.get("designation"),
            "CURRENT_INDUSTRY": primary_prof.get("industry") or legacy_prof.get("industry"),
            "years_experience_total": primary_prof.get("years_experience_total") or legacy_prof.get("years_experience_total"),
            "highest_qualification": primary_edu.get("highest_qualification") or legacy_edu.get("highest_qualification"),
            "field_of_study": primary_edu.get("field_of_study") or legacy_edu.get("field_of_study"),
            "language_scores": (primary.get("language") or profile.get("language_proficiency") or {}).get("scores"),
            "work_history": primary.get("work_history") or profile.get("work_history") or [],
        },
        "SPOUSE_CONTRIBUTION_ONLY": _spouse_context(profile),
        "additional_factors": profile.get("additional_factors") or {},
        "finances": profile.get("finances") or {},
        "preferences": profile.get("preferences") or {},
    }

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
        # Phase 6.7 — list of occupation codes for Claude to choose the right match
        "occupation_codes_available": [
            {"code": o.get("code"), "title": o.get("title"), "group": o.get("group"),
             "assessing_body": o.get("assessing_body"), "pathway": o.get("pathway"),
             "eligible_visas": o.get("eligible_visas") or []}
            for o in (country.get("occupation_codes") or [])[:60]
        ],
    }
    return (
        "## PROFILE FOCUS (Primary applicant is the ONLY visa applicant being analysed)\n```json\n"
        + json.dumps(profile_focus, default=str, ensure_ascii=False, indent=2)
        + "\n```\n\n## COUNTRY RULES (summary)\n```json\n"
        + json.dumps(country_slim, default=str, ensure_ascii=False)
        + "\n```\n\n## CUSTOM RULES ENGINE OUTPUT\n```json\n"
        + json.dumps(rules_output, default=str, ensure_ascii=False)
        + "\n```\n\n"
        + "REMINDER: Match occupation codes using the PRIMARY APPLICANT's CURRENT_PROFESSION. "
        + "Ignore any past education/degree (e.g., a Veterinary degree) if the current profession is different (e.g., Marketing). "
        + "Spouse data is ONLY relevant for partner points — never recommend visas for the spouse.\n\n"
        + "Return the enrichment JSON now."
    )


def _spouse_context(profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a minimal spouse context block ONLY when the spouse contributes to points
    (skill_assessment / english_only / australian_pr_citizen). Otherwise return None
    so Claude doesn't get distracted by irrelevant spouse data.
    """
    spouse = profile.get("spouse") or {}
    fam = profile.get("family") or {}
    contribution = spouse.get("contribution_type") or fam.get("spouse_contribution_type") or "not_applicable"
    if contribution in ("not_applicable", "non_contributing", ""):
        return None
    return {
        "contribution_type": contribution,
        "is_australian_pr_or_citizen": spouse.get("is_australian_pr_or_citizen") or fam.get("spouse_is_australian_pr_or_citizen") or False,
        "is_applicant_on_visa": spouse.get("is_applicant_on_visa") if spouse else fam.get("spouse_is_applicant_on_visa"),
        "spouse_age": (spouse.get("personal") or {}).get("age"),
        "spouse_english_overall": ((spouse.get("language") or {}).get("scores") or {}).get("overall"),
        "spouse_current_profession": (spouse.get("professional") or {}).get("current_profession") or fam.get("spouse_profession"),
        "_note": "This is ONLY for partner-points context. Do NOT recommend visas for the spouse.",
    }


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
