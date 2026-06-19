"""Phase 20.4 M3 — Resume AI extraction service (Claude Sonnet 4.5).

Strict JSON extractor for uploaded resume text. Uses Emergent Universal Key.

Output schema (validated):
{
  "extracted_qualifications": [{degree, field_of_study, awarding_body, institute,
                                start_date, end_date, study_mode, confidence}],
  "extracted_employment": [{job_title, business_name, address,
                            start_date, end_date, working_hours_per_week,
                            is_current, confidence}],
  "summary": {skills: [...], total_years_experience: float, certifications: [...]},
  "confidence_score": 0..1,
  "model_used": "claude-sonnet-4-5-20250929",
  "extracted_at": iso
}
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
PRIMARY_MODEL = ("anthropic", "claude-sonnet-4-5-20250929")
FALLBACK_MODEL = ("anthropic", "claude-haiku-4-5-20251001")
MAX_TOKENS_PER_EXTRACT = 1500

SYSTEM_PROMPT = """You are a strict resume/CV parser. Extract structured data ONLY.
Return valid JSON. No prose. No markdown. No preamble.
If a field is missing, use null. If a section is empty, use [].
Date format: YYYY-MM-DD (or null). Today's date is for context only — do not invent past dates."""


EXTRACTION_PROMPT_TEMPLATE = """Parse this resume text and extract structured data.

Return EXACTLY this JSON shape (no extra fields, no markdown):
{{
  "extracted_qualifications": [
    {{
      "degree": "string (e.g., Bachelor of Engineering)",
      "field_of_study": "string",
      "awarding_body": "string (university name)",
      "institute": "string (campus or college if separate)",
      "start_date": "YYYY-MM-DD or null",
      "end_date": "YYYY-MM-DD or null",
      "study_mode": "Full Time | Part Time | Distance | null",
      "confidence": 0.0-1.0
    }}
  ],
  "extracted_employment": [
    {{
      "job_title": "string",
      "business_name": "string (company)",
      "address": "string or null",
      "start_date": "YYYY-MM-DD or null",
      "end_date": "YYYY-MM-DD or null (null if current job)",
      "working_hours_per_week": "integer or null",
      "is_current": true|false,
      "confidence": 0.0-1.0
    }}
  ],
  "summary": {{
    "skills": ["string", ...],
    "total_years_experience": float,
    "certifications": ["string", ...]
  }},
  "confidence_score": 0.0-1.0
}}

RESUME TEXT:
---
{resume_text}
---

Return ONLY the JSON object."""


def parse_json_response(text: str) -> Dict[str, Any]:
    """Strict JSON extraction with markdown fence stripping."""
    if not text:
        raise ValueError("Empty AI response")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse JSON: {e}") from e
    raise ValueError("No JSON object found in response")


def validate_extraction(data: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce to canonical shape + safe defaults. Drops invalid entries."""
    out: Dict[str, Any] = {
        "extracted_qualifications": [],
        "extracted_employment": [],
        "summary": {"skills": [], "total_years_experience": 0.0, "certifications": []},
        "confidence_score": float(data.get("confidence_score") or 0.0),
    }
    for q in (data.get("extracted_qualifications") or []):
        if not isinstance(q, dict) or not q.get("degree"):
            continue
        out["extracted_qualifications"].append({
            "degree": str(q.get("degree") or ""),
            "field_of_study": q.get("field_of_study"),
            "awarding_body": q.get("awarding_body"),
            "institute": q.get("institute"),
            "start_date": q.get("start_date"),
            "end_date": q.get("end_date"),
            "study_mode": q.get("study_mode"),
            "confidence": float(q.get("confidence") or 0.5),
        })
    for e in (data.get("extracted_employment") or []):
        if not isinstance(e, dict) or not e.get("job_title"):
            continue
        out["extracted_employment"].append({
            "job_title": str(e.get("job_title") or ""),
            "business_name": e.get("business_name"),
            "address": e.get("address"),
            "start_date": e.get("start_date"),
            "end_date": e.get("end_date"),
            "working_hours_per_week": e.get("working_hours_per_week"),
            "is_current": bool(e.get("is_current")),
            "confidence": float(e.get("confidence") or 0.5),
        })
    summ = data.get("summary") or {}
    if isinstance(summ, dict):
        out["summary"]["skills"] = [str(s) for s in (summ.get("skills") or []) if s][:30]
        try:
            out["summary"]["total_years_experience"] = float(summ.get("total_years_experience") or 0)
        except (TypeError, ValueError):
            out["summary"]["total_years_experience"] = 0.0
        out["summary"]["certifications"] = [str(c) for c in (summ.get("certifications") or []) if c][:20]
    return out


async def extract_resume(resume_text: str) -> Dict[str, Any]:
    """Call Claude Sonnet 4.5 to extract structured data from resume text.

    Falls back to Haiku 4.5 silently on Sonnet failure.
    Returns the validated extraction payload + model_used + extracted_at.
    """
    if not EMERGENT_LLM_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY not set in env")
    if not resume_text or len(resume_text.strip()) < 50:
        raise ValueError("Resume text too short (< 50 chars) — cannot extract")
    # Trim to safe length (≈20k chars max — model limit)
    resume_text = resume_text[:20000]

    from emergentintegrations.llm.chat import LlmChat, UserMessage

    session_id = f"resume-{uuid.uuid4().hex[:8]}"
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(resume_text=resume_text)
    last_err: Exception | None = None

    for provider, model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=session_id,
                system_message=SYSTEM_PROMPT,
            ).with_model(provider, model).with_params(max_tokens=MAX_TOKENS_PER_EXTRACT)
            raw = await chat.send_message(UserMessage(text=prompt))
            data = parse_json_response(raw)
            validated = validate_extraction(data)
            validated["model_used"] = f"{provider}/{model}"
            validated["extracted_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(
                "Resume extracted via %s — quals=%d, employment=%d, confidence=%.2f",
                model, len(validated["extracted_qualifications"]),
                len(validated["extracted_employment"]),
                validated["confidence_score"],
            )
            return validated
        except Exception as e:  # noqa: BLE001
            logger.warning("Resume extraction failed via %s: %s — trying next model", model, e)
            last_err = e
            continue

    raise RuntimeError(f"All AI providers failed for resume extraction: {last_err}")


def extract_text_from_pdf_or_docx(content: bytes, filename: str) -> str:
    """Extract plain text from a PDF or DOCX byte stream."""
    name_lower = (filename or "").lower()
    if name_lower.endswith(".pdf"):
        try:
            import pdfplumber
            import io
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                parts = [p.extract_text() or "" for p in pdf.pages]
                return "\n".join(parts).strip()
        except Exception as e:  # noqa: BLE001
            logger.error("PDF text extraction failed: %s", e)
            raise ValueError(f"Could not extract PDF text: {e}") from e
    if name_lower.endswith((".docx", ".doc")):
        try:
            from docx import Document
            import io
            doc = Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:  # noqa: BLE001
            logger.error("DOCX text extraction failed: %s", e)
            raise ValueError(f"Could not extract DOCX text: {e}") from e
    if name_lower.endswith(".txt"):
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return content.decode("latin-1", errors="ignore")
    raise ValueError(f"Unsupported resume file type: {filename}. Use PDF, DOCX, or TXT.")
