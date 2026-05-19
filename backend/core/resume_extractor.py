"""Phase 6.7 Part 2 — Resume Upload + AI Extraction.

Extracts structured candidate profile fields from a resume (PDF or DOCX) using:
  1. Text extraction via pdfplumber / python-docx
  2. Claude AI (Sonnet 4.6) for structured JSON extraction

Output schema matches the Phase 6.7 ProfileCreate model so it can be used to
prefill the wizard directly.
"""
import io
import json
import logging
import os
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

MAX_TEXT_CHARS = 24_000  # safe Claude input budget


EXTRACTION_PROMPT = """You are a resume-parsing assistant for an immigration consultancy.

Extract the candidate's profile from the resume text below. Return ONLY a JSON object
matching this exact schema (omit fields if not found — do NOT invent data):

{
  "name": "Full name of the candidate",
  "email": "email if present",
  "phone": "phone with country code if present",
  "marital_status": "single | married | de_facto | separated | divorced | widowed (if mentioned)",
  "primary_applicant": {
    "personal": {
      "full_name": "...",
      "date_of_birth": "YYYY-MM-DD if found",
      "age": null,
      "gender": "male | female | other (if found)",
      "nationality": "if found",
      "current_country": "country candidate currently lives in",
      "current_city": "city candidate currently lives in"
    },
    "professional": {
      "current_profession": "MOST RECENT job role (e.g., 'Marketing Specialist', 'Software Engineer')",
      "designation": "Most recent designation/title",
      "years_experience_total": 0.0,
      "years_in_current_role": 0.0,
      "industry": "Industry sector",
      "employer_name": "Current employer",
      "salary_inr_per_annum": null,
      "has_managerial_experience": false
    },
    "education": {
      "highest_qualification": "doctorate | master | bachelor | diploma | trade | high_school",
      "field_of_study": "Field of study (e.g., 'Computer Science')",
      "institution": "Last/highest institution",
      "country": "Country of highest qualification",
      "year_completed": null
    },
    "language": {
      "primary_test": "IELTS | PTE | TOEFL | none",
      "test_completed": false,
      "test_date": null,
      "scores": {}
    },
    "work_history": [
      {"employer": "...", "designation": "...", "start_date": "YYYY-MM", "end_date": "YYYY-MM or null", "country": "...", "duties": "1-2 line summary"}
    ]
  },
  "_extraction_notes": ["any caveats, ambiguities, or fields that need user review"]
}

CRITICAL RULES:
- The MOST RECENT job (top of work history) = `current_profession` and `designation`.
- `years_experience_total` = sum of years across all professional roles (not student/intern).
- `highest_qualification` MUST be one of: doctorate | master | bachelor | diploma | trade | high_school. Map common synonyms (PhD→doctorate, M.Tech/MBA/M.S→master, B.Tech/B.E/B.S→bachelor).
- DO NOT confuse education field with current profession. e.g., A B.V.Sc graduate currently working as Marketing Specialist → `current_profession='Marketing Specialist'`, `field_of_study='Veterinary Science'`.
- If language test is mentioned (IELTS/PTE/TOEFL), set `test_completed=true` and include scores. Otherwise default to `primary_test='IELTS', test_completed=false, scores={}`.
- For unclear fields, leave them null/empty and add a note in `_extraction_notes`.
- Output MUST be valid JSON. NO markdown, NO commentary outside the JSON.
"""


def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract plain text from a PDF resume."""
    import pdfplumber

    text_parts = []
    page_count = 0
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                text_parts.append(t)
    text = "\n\n".join(text_parts)
    return text, {"page_count": page_count, "char_count": len(text)}


def extract_text_from_docx(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract plain text from a DOCX resume."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    parts = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    # Also pull table cells
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                if cell.text and cell.text.strip():
                    parts.append(cell.text.strip())
    text = "\n".join(parts)
    return text, {"paragraph_count": len(doc.paragraphs), "char_count": len(text)}


def extract_text(filename: str, file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Dispatch by file extension."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if name.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    if name.endswith(".txt"):
        try:
            t = file_bytes.decode("utf-8", errors="replace")
        except Exception:
            t = file_bytes.decode("latin-1", errors="replace")
        return t, {"char_count": len(t)}
    raise ValueError(f"Unsupported file type — only .pdf, .docx, .txt allowed (got '{name}')")


async def parse_resume_with_ai(resume_text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Send resume text to Claude AI for structured extraction.
    Returns the parsed JSON (Phase 6.7 ProfileCreate shape) or a fallback empty shell.
    """
    if not EMERGENT_LLM_KEY:
        return {"_error": "EMERGENT_LLM_KEY not configured"}
    if not resume_text or len(resume_text.strip()) < 50:
        return {"_error": "Resume text is too short to extract anything meaningful"}

    # Trim to safe budget
    text = resume_text[:MAX_TEXT_CHARS]

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except ImportError as e:
        return {"_error": f"emergentintegrations missing: {e}"}

    sid = session_id or f"resume-{os.urandom(4).hex()}"
    user_prompt = (
        "## RESUME TEXT\n```\n"
        + text
        + "\n```\n\nReturn the extracted JSON now."
    )

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=sid,
            system_message=EXTRACTION_PROMPT,
        ).with_model("anthropic", CLAUDE_MODEL)
        response = await chat.send_message(UserMessage(text=user_prompt))
        raw = (str(response) if response is not None else "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        first = raw.find("{")
        last = raw.rfind("}")
        if first == -1 or last == -1:
            return {"_error": "AI returned non-JSON response", "_raw": raw[:300]}
        parsed = json.loads(raw[first:last + 1])
        parsed["_ai_status"] = "ok"
        parsed["_ai_model"] = CLAUDE_MODEL
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"Resume parse JSON error: {e}")
        return {"_error": f"AI returned malformed JSON: {e}"}
    except Exception as e:
        logger.error(f"Resume parse AI call error: {e}")
        return {"_error": f"AI call failed: {type(e).__name__}: {str(e)[:120]}"}
