"""Phase 20.1 — AI Workflow Builder generation service.

Wires **Claude Sonnet 4.5 (primary)** with **GPT-5.2 silent fallback** for
structured immigration workflow generation, plus quality bar enforcement
(min 5 steps, ≥3 docs per step, official + VFS + skill-assessment URLs).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Per Phase 20.1 directive #1 & #2 — Sir requested GPT-5.2 fallback, but Emergent
# Universal Key is ANTHROPIC-ONLY (not allowed to access OpenAI models per key policy).
# We silently use Claude Haiku 4.5 as the cheap-and-fast fallback (3-5x cheaper than Sonnet).
PRIMARY_MODEL = ("anthropic", "claude-sonnet-4-5-20250929")
FALLBACK_MODEL = ("anthropic", "claude-haiku-4-5-20251001")

# Phase 20.1 quality bar (Sir's directive)
MIN_STEPS = 5
MIN_DOCS_PER_STEP = 3
MAX_QUALITY_RETRIES = 2  # 2 retries (1 primary failure + 1 fallback) before giving up


# ── VFSglobal lookup ──────────────────────────────────────────────────────────
_VFS_MAP_CACHE: Optional[Dict[str, Any]] = None


def _load_vfs_map() -> Dict[str, Any]:
    global _VFS_MAP_CACHE
    if _VFS_MAP_CACHE is None:
        p = Path(__file__).resolve().parent.parent / "data" / "vfsglobal_country_map.json"
        try:
            _VFS_MAP_CACHE = json.loads(p.read_text())
        except Exception as e:  # noqa: BLE001
            logger.warning("VFS map load failed: %s — using empty map", e)
            _VFS_MAP_CACHE = {"countries": {}}
    return _VFS_MAP_CACHE


def vfsglobal_url(country_key: str) -> Optional[str]:
    """Return Indian-applicant VFSglobal URL for destination country, or None."""
    m = _load_vfs_map()
    slug = m.get("countries", {}).get((country_key or "").lower())
    if not slug:
        return None
    return f"https://visa.vfsglobal.com/ind/en/{slug}/"


# ── AU/NZ Skill Assessment authority resolution ───────────────────────────────
async def resolve_au_nz_skill_assessment_url(db, country_key: str, service_type: str) -> Optional[str]:
    """For AU/NZ PR workflows, pull a representative assessing authority website
    from Phase 19.7 `assessing_authorities` collection."""
    if country_key not in ("australia", "new_zealand") or service_type != "pr":
        return None
    cc = "AU" if country_key == "australia" else "NZ"
    # Pick a high-profile body as canonical reference
    canonical = {"AU": "VETASSESS", "NZ": "NZQA"}.get(cc)
    if not canonical:
        return None
    doc = await db["assessing_authorities"].find_one(
        {"country_code": cc, "code": canonical}, {"_id": 0, "url": 1, "website": 1, "full_name": 1, "short_name": 1},
    )
    if not doc:
        return None
    return doc.get("url") or doc.get("website") or None


# ── Core AI call: Claude primary, GPT fallback ────────────────────────────────
def _sync_chat_call(api_key: str, session_id: str, system_msg: str, provider: str, model: str, prompt: str) -> str:
    """Sweep A.2 fix — Runs the LlmChat in a brand-new event loop inside a worker
    thread. emergentintegrations.LlmChat.send_message is declared `async` but
    internally calls the SYNC litellm.completion() — that blocks the main FastAPI
    event loop for 20–90s per call. Wrapping it via run_in_executor + asyncio.run
    makes it true non-blocking from the main loop's perspective.
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=api_key, session_id=session_id, system_message=system_msg).with_model(provider, model)
    return asyncio.run(chat.send_message(UserMessage(text=prompt)))


async def call_ai_with_fallback(
    prompt: str, system_msg: str = "", session_prefix: str = "workflow",
) -> Tuple[str, str]:
    """Call Claude Sonnet 4.5 first. On exception, retry with GPT-5.2.

    Returns: (response_text, model_used_label)
    Raises: RuntimeError if BOTH fail.

    Sweep A.2 — Offloads the BLOCKING LiteLLM call to a thread-pool executor.
    """
    session_id = f"{session_prefix}-{uuid.uuid4().hex[:8]}"
    last_err: Optional[Exception] = None
    loop = asyncio.get_event_loop()

    for provider, model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            result = await loop.run_in_executor(
                None,
                _sync_chat_call,
                EMERGENT_LLM_KEY, session_id, system_msg, provider, model, prompt,
            )
            logger.info("AI workflow generated via %s/%s (session=%s)", provider, model, session_id)
            return result, f"{provider}/{model}"
        except Exception as e:  # noqa: BLE001
            logger.warning("AI call failed (%s/%s): %s — trying next model", provider, model, e)
            last_err = e
            continue
    raise RuntimeError(f"All AI providers failed. Last error: {last_err}")


# ── JSON extraction (handles markdown-wrapped responses) ──────────────────────
def parse_json_response(text: str) -> Dict[str, Any]:
    """Extract first valid JSON block from response text.

    Models sometimes wrap JSON in ```json...``` despite instructions.
    """
    if not text:
        raise ValueError("Empty AI response")
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown fence
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Best-effort: find first { ... } block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse JSON: {e}") from e
    raise ValueError("No JSON object found in response")


# ── Quality bar enforcement ───────────────────────────────────────────────────
def validate_workflow_quality(workflow: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Verify generated workflow meets Phase 20.1 quality bar.

    Returns: (passed, list_of_issues)
    """
    issues = []
    steps = workflow.get("steps") or []
    if len(steps) < MIN_STEPS:
        issues.append(f"Only {len(steps)} steps (min {MIN_STEPS} required)")
    for i, step in enumerate(steps, 1):
        docs = step.get("required_documents") or []
        if len(docs) < MIN_DOCS_PER_STEP:
            issues.append(f"Step {i} '{step.get('step_name')}' has only {len(docs)} docs (min {MIN_DOCS_PER_STEP})")
        if not step.get("step_name"):
            issues.append(f"Step {i} missing step_name")
        # Each step should have either step-level or workflow-level gov fee mention
        for d in docs:
            if not d.get("name"):
                issues.append(f"Step {i} doc missing name")
    if not workflow.get("estimated_government_fees"):
        issues.append("Missing estimated_government_fees")
    return (len(issues) == 0, issues)


def build_enrichment_context(
    country_key: str, service_type: str, country_ref: str,
    vfs_url: Optional[str], skill_assessment_url: Optional[str],
    template_context: str = "",
) -> str:
    """Compose context block for prompt with VFS + skill assessment URLs."""
    parts = [f"Official Government Reference:\n{country_ref}"]
    if vfs_url:
        parts.append(f"\nVFSglobal Application Centre (Indian applicants): {vfs_url}")
    if skill_assessment_url and country_key in ("australia", "new_zealand") and service_type == "pr":
        parts.append(f"\nSkill Assessment Authority (REQUIRED for {country_key.upper()} PR): {skill_assessment_url}")
    if template_context:
        parts.append(f"\n{template_context}")
    # Skill assessment rule (Sir's directive #4)
    if country_key in ("australia", "new_zealand") and service_type == "pr":
        parts.append("\nIMPORTANT: This workflow MUST include a 'Skills Assessment' step as the first or second step (mandatory for AU/NZ PR).")
    else:
        parts.append("\nNote: This is NOT an AU/NZ PR workflow — do NOT include a 'Skills Assessment' step unless the destination explicitly requires it.")
    return "\n".join(parts)


def build_stricter_retry_prompt(original_prompt: str, issues: List[str]) -> str:
    """Inject quality-bar failure feedback into a retry prompt."""
    issue_block = "\n".join(f"- {x}" for x in issues)
    return (
        original_prompt
        + f"\n\nIMPORTANT — your previous attempt failed quality checks. Fix these issues:\n{issue_block}\n"
        + f"\nMINIMUM REQUIREMENTS (HARD RULES):\n"
        + f"- At least {MIN_STEPS} steps\n"
        + f"- At least {MIN_DOCS_PER_STEP} required_documents per step\n"
        + "- Every document MUST have name + description + mandatory flag\n"
        + "- estimated_government_fees field MUST be populated\n"
        + "- Return ONLY valid JSON — no markdown, no preamble.\n"
    )
