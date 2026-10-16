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

PRIMARY_MODEL = ("perplexity", "sonar-pro")
FALLBACK_MODEL = ("perplexity", "sonar")

# Quality bar
MIN_STEPS = 5
MIN_DOCS_PER_STEP = 3
MAX_QUALITY_RETRIES = 2


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


# ── Core AI call: Perplexity fast primary (sonar) + deep fallback (sonar-pro) ──
async def call_ai_with_fallback(
    prompt: str,
    system_msg: str = "",
    session_prefix: str = "workflow",
    primary_timeout: float = 35.0,
    fallback_timeout: float = 50.0,
    perplexity_timeout: float = 60.0,
) -> Tuple[str, str]:
    """Call Perplexity Sonar (fast primary, ~10-15s) with automatic fallback to Sonar Pro.

    Returns: (response_text, model_used_label)
    Raises: RuntimeError if all attempts fail.
    """
    from core.perplexity_client import call_perplexity
    try:
        res, model = await call_perplexity(
            prompt=prompt,
            system_msg=system_msg,
            model="sonar",
            max_tokens=3500,
            temperature=0.2,
            timeout=primary_timeout,
        )
        return res, model
    except Exception as e:
        logger.warning(f"Fast primary AI call (sonar) failed: {e} — trying sonar-pro fallback")
        try:
            res, model = await call_perplexity(
                prompt=prompt,
                system_msg=system_msg,
                model="sonar-pro",
                max_tokens=4000,
                temperature=0.2,
                timeout=fallback_timeout,
            )
            return res, model
        except Exception as e2:
            logger.error(f"Fallback AI call (sonar-pro) failed: {e2}")
            raise RuntimeError(f"All AI providers failed: {e2}") from e2


# ── JSON extraction (handles markdown-wrapped responses & citations) ──────────
def parse_json_response(text: str) -> Dict[str, Any]:
    """Extract first valid JSON block from response text.

    Handles direct JSON, markdown-wrapped JSON, and JSON followed by Perplexity citations/sources.
    """
    if not text:
        raise ValueError("Empty AI response")
    trimmed = text.strip()
    # Try direct parse
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        pass
    # Strip markdown fence
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Locate first '{' and use JSONDecoder().raw_decode
    start = text.find("{")
    if start != -1:
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text[start:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    # Best-effort greedy regex
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
