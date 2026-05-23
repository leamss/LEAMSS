"""Phase 6.9.3 — Shared AI helpers for the Verified Knowledge Base.

Single integration point for Claude Sonnet 4.6 (via emergentintegrations).

Used by:
  • occupation_master.py        — Generate AI Draft for an occupation
  • skill_body_master endpoints — Generate AI Draft for an assessing body
  • country_templates.py        — Generate factor descriptions
  • Generic /api/kb/polish-text — "✨ Polish with AI" on any text field

PHILOSOPHY: AI drafts only. Admin verifies before publish.
"""
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"


def _strip_json_fences(s: str) -> str:
    """Remove ```json ... ``` fences a model may wrap output in."""
    s = s.strip()
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", s, re.DOTALL)
    if m:
        return m.group(1).strip()
    return s


async def _call_claude(system: str, user_text: str, session_prefix: str = "kb") -> str:
    """Single helper to send one user message to Claude via emergentintegrations.

    Returns raw text. Caller is responsible for JSON parsing if expected.
    """
    if not EMERGENT_LLM_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except ImportError as e:
        raise RuntimeError(f"emergentintegrations not installed: {e}") from e

    chat = (
        LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"{session_prefix}-{uuid.uuid4().hex[:8]}",
            system_message=system,
        )
        .with_model("anthropic", CLAUDE_MODEL)
    )
    response = await chat.send_message(UserMessage(text=user_text))
    return response if isinstance(response, str) else str(response)


# ─────────────────────────────────────────────────────────────────────────────
# 6.9.3 — AI Draft for an Occupation
# ─────────────────────────────────────────────────────────────────────────────
async def draft_occupation(
    code: str,
    title: str,
    country_code: str,
    assessing_body: Optional[str] = None,
    pathway: Optional[str] = None,
    hierarchy_group: Optional[str] = None,
) -> Dict[str, Any]:
    """Draft `description` + `typical_tasks` + `qualification_rules` for an occupation.

    STRICT rules baked into the prompt:
      • Never invent fees, deadlines, or numeric thresholds
      • Tasks must be generic and verifiable against ABS/NOC/ANZSCO
      • Output JSON only
    """
    system = (
        "You are an immigration knowledge base drafting assistant for an Australian/Canadian/"
        "New Zealand migration consultancy. Draft factual baseline content for the "
        "ADMIN to verify against official sources (ABS/ANZSCO, ESDC/NOC, ANZSCO/StatsNZ). "
        "STRICT RULES:\n"
        "  1. Never invent fees, processing times, deadlines, or specific monetary amounts.\n"
        "  2. Never claim a code IS or IS NOT on a specific list (MLTSSL/STSOL/etc.) unless explicitly told.\n"
        "  3. Keep tone professional, concise, suitable for a sales agent + client report.\n"
        "  4. Return ONLY valid JSON. No prose, no markdown fences."
    )

    user_prompt = (
        f"Draft baseline content for this occupation code. Output JSON only.\n\n"
        f"Country: {country_code}\n"
        f"Code: {code}\n"
        f"Title: {title}\n"
        f"Assessing Body (provided): {assessing_body or 'unknown'}\n"
        f"Pathway list (provided): {pathway or 'unknown'}\n"
        f"Occupation group: {hierarchy_group or 'unknown'}\n\n"
        f"Required JSON shape:\n"
        f"{{\n"
        f'  "description": "2-3 sentence professional role summary, 60-180 words.",\n'
        f'  "typical_tasks": ["task 1", "task 2", ...10 short bullets, each <120 chars],\n'
        f'  "qualification_rules": "1-2 paragraph note on typical education + experience requirements (no specific fees).",\n'
        f'  "ai_confidence_note": "One line on what an admin should specifically verify against official sources."\n'
        f"}}"
    )

    raw = await _call_claude(system, user_prompt, session_prefix="occ-draft")
    raw = _strip_json_fences(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("AI returned non-JSON for occupation draft, retrying once")
        # Retry once with stricter prompt
        raw2 = await _call_claude(
            system + "\nIMPORTANT: Your last response was not valid JSON. Return ONLY raw JSON.",
            user_prompt,
            session_prefix="occ-draft-retry",
        )
        raw2 = _strip_json_fences(raw2)
        data = json.loads(raw2)

    # Validate shape
    data.setdefault("description", "")
    data.setdefault("typical_tasks", [])
    data.setdefault("qualification_rules", "")
    data.setdefault("ai_confidence_note", "Admin must verify against official source.")
    if isinstance(data["typical_tasks"], str):
        data["typical_tasks"] = [data["typical_tasks"]]
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 6.9.3 — AI Draft for a Skill Assessment Body
# ─────────────────────────────────────────────────────────────────────────────
async def draft_skill_body(
    slug: str,
    name: str,
    full_name: str,
    country_code: str,
    website: Optional[str] = None,
) -> Dict[str, Any]:
    system = (
        "You are an immigration knowledge base drafting assistant. Draft factual baseline "
        "content about an official skill-assessment authority (e.g., ACS, VETASSESS, WES, NZQA). "
        "STRICT RULES:\n"
        "  1. Never invent fees or processing times — leave those for admin to fill from official source.\n"
        "  2. Describe the body's role, the kinds of occupations they assess, the general criteria.\n"
        "  3. Return ONLY valid JSON. No prose, no markdown fences."
    )
    user_prompt = (
        f"Draft baseline content for this skill assessment body.\n\n"
        f"Country: {country_code}\n"
        f"Short name: {name}\n"
        f"Full name: {full_name}\n"
        f"Website: {website or 'unknown'}\n\n"
        f"Required JSON shape:\n"
        f"{{\n"
        f'  "description": "2-3 sentence about the body, 50-150 words.",\n'
        f'  "role": "Single line: what they assess and for which visa pathways.",\n'
        f'  "general_criteria": {{\n'
        f'    "minimum_education": "...",\n'
        f'    "relevant_work_experience": "...",\n'
        f'    "english_required": "...",\n'
        f'    "registration_required": "..."\n'
        f"  }},\n"
        f'  "ai_confidence_note": "What admin should verify (fees, exact requirements)."\n'
        f"}}"
    )
    raw = await _call_claude(system, user_prompt, session_prefix="body-draft")
    raw = _strip_json_fences(raw)
    data = json.loads(raw)
    data.setdefault("description", "")
    data.setdefault("role", "")
    data.setdefault("general_criteria", {})
    data.setdefault("ai_confidence_note", "Admin must verify against official source.")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 6.9.3 — "✨ Polish with AI" — improve writing without changing facts
# ─────────────────────────────────────────────────────────────────────────────
async def polish_text(text: str, field_label: Optional[str] = None, context: Optional[str] = None) -> str:
    if not text or not text.strip():
        return text
    system = (
        "You are a professional editor for an immigration knowledge base. "
        "Improve writing quality without changing FACTS, NUMBERS, NAMES, or TECHNICAL CONTENT.\n\n"
        "STRICT RULES:\n"
        "  1. Keep every factual claim, number, date, name, URL identical.\n"
        "  2. Improve grammar, clarity, professional tone, and flow.\n"
        "  3. Do NOT add new information. Do NOT remove existing information.\n"
        "  4. Match the original length (within ±20%).\n"
        "  5. Return ONLY the polished text. No commentary, no markdown, no quotes around it."
    )
    prompt_parts = []
    if field_label:
        prompt_parts.append(f"Field: {field_label}")
    if context:
        prompt_parts.append(f"Context: {context}")
    prompt_parts.append(f"\nOriginal text:\n---\n{text}\n---\n\nPolished text:")
    polished = await _call_claude(system, "\n".join(prompt_parts), session_prefix="polish")
    polished = polished.strip()
    # Strip wrapping quotes/fences if any
    polished = _strip_json_fences(polished)
    if polished.startswith('"') and polished.endswith('"'):
        polished = polished[1:-1]
    return polished


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
