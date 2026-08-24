"""Bulk Pre-Assessment — AI resume enrichment.

For rows where the consultant left the ANZSCO code blank but provided a public
"Resume Link" (Google Drive / Dropbox / direct file URL), we:
  1. Fetch the resume file from the link (handles Drive/Dropbox share URLs).
  2. Extract text (pdfplumber / python-docx) and AI-parse the profile.
  3. Match the candidate's current occupation to the best AU ANZSCO code
     (Mongo $text retrieve-then-rank + Claude), with a confidence + alternatives.

The picked code is flagged as AI-suggested (review pending) so the consultant keeps
final control in the per-client edit dialog.
"""
import asyncio
import json
import logging
import os
import random
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from openai import AsyncOpenAI

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# Many resume hosts (e.g. LiteSpeed on leamss.com) DROP connections under a concurrent
# burst from one IP ("Server disconnected without sending a response"). A single request
# works fine, so we throttle downloads to a small, polite concurrency across the whole batch.
_FETCH_SEM = asyncio.Semaphore(4)
# PDF/DOCX text extraction (pdfplumber/python-docx) is GIL-bound CPU work; even in a thread
# it contends with the event loop. Cap simultaneous extractions so the API stays responsive.
_EXTRACT_SEM = asyncio.Semaphore(4)


# ── Resume link → text ────────────────────────────────────────────
def _normalize_resume_url(url: str) -> str:
    u = (url or "").strip()
    # Google Drive share links → direct download
    m = re.search(r"drive\.google\.com/file/d/([A-Za-z0-9_-]+)", u)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"drive\.google\.com/open\?id=([A-Za-z0-9_-]+)", u)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    if "drive.google.com" in u:
        m = re.search(r"[?&]id=([A-Za-z0-9_-]+)", u)
        if m:
            return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    # Dropbox → force direct download
    if "dropbox.com" in u:
        if "dl=0" in u:
            return u.replace("dl=0", "dl=1")
        if "dl=1" not in u:
            return u + ("&dl=1" if "?" in u else "?dl=1")
    return u


def _guess_filename(url: str, content_type: str, content_disposition: str) -> str:
    if content_disposition:
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', content_disposition)
        if m:
            return m.group(1)
    path = url.split("?")[0]
    if path.lower().endswith((".pdf", ".docx", ".doc", ".txt")):
        return path.rsplit("/", 1)[-1]
    ct = (content_type or "").lower()
    if "pdf" in ct:
        return "resume.pdf"
    if "word" in ct or "officedocument" in ct:
        return "resume.docx"
    if "text/plain" in ct:
        return "resume.txt"
    return "resume.pdf"


def _extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    from core.resume_extractor import extract_text
    try:
        text, _ = extract_text(filename, file_bytes)
        return text or ""
    except Exception as e:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""


async def fetch_resume_bytes(url: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """Download a resume file from a public link → (bytes, filename, error).

    Used to attach the client's original resume to their report email.
    """
    if not url:
        return None, None, "No resume link provided"
    fetch_url = _normalize_resume_url(url)
    transient = (
        httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError,
        httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout, httpx.WriteError,
    )
    for attempt in range(3):
        try:
            async with _FETCH_SEM:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=httpx.Timeout(45.0, connect=15.0),
                    headers=_UA,
                    verify=False,
                    limits=httpx.Limits(max_connections=4, max_keepalive_connections=0),
                ) as client:
                    resp = await client.get(fetch_url)
                    resp.raise_for_status()
                    content = resp.content
                    ct = resp.headers.get("content-type", "")
                    cd = resp.headers.get("content-disposition", "")
                    if "text/html" in ct.lower() and content[:2000].lower().find(b"<html") != -1:
                        return None, None, "Link opened an HTML page, not a direct file (private/expired link?)."
            return content, _guess_filename(fetch_url, ct, cd), None
        except httpx.HTTPStatusError as e:
            return None, None, f"Download failed (HTTP {e.response.status_code}). Is the link public?"
        except transient as e:
            if attempt < 2:
                await asyncio.sleep(0.8 * (attempt + 1) + random.uniform(0, 0.7))
                continue
            return None, None, "Host dropped the connection after retries."
        except Exception as e:
            return None, None, f"Could not fetch resume: {type(e).__name__}"
    return None, None, "Could not fetch resume"


async def fetch_resume_text(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Download a resume from a public link and extract text → (text, error)."""
    file_bytes, filename, err = await fetch_resume_bytes(url)
    if err or not file_bytes:
        return None, err or "Could not fetch resume"
    try:
        async with _EXTRACT_SEM:
            text = await asyncio.to_thread(_extract_text_from_bytes, file_bytes, filename or "resume.pdf")
            if not text.strip():
                return None, "Resume document was empty or unreadable"
            return text[:20000], None
    except Exception as e:
        return None, f"Text extraction failed: {e}"


# ── Occupation text → best ANZSCO code ────────────────────────────
_MATCH_SYSTEM = """You are an Australian immigration ANZSCO occupation-code expert.

Given a candidate's profile (from their resume) and a list of AVAILABLE_CODES,
pick the SINGLE best-matching ANZSCO code for their CURRENT occupation, plus up to
3 alternatives. Match on the candidate's most recent job title + duties + industry.
Ignore education unless the current job is clearly a new field.

Only choose codes from AVAILABLE_CODES — never invent a code.

Return ONLY this JSON (no markdown):
{
  "best": {"code": "261313", "title": "Software Engineer", "confidence": "high|medium|low", "reasoning": "1-2 sentences"},
  "alternatives": [{"code": "261312", "title": "Developer Programmer", "confidence": "medium"}]
}
If nothing fits, return {"best": null, "alternatives": []}.
"""


async def match_anzsco(db, description: str, max_candidates: int = 120) -> Dict[str, Any]:
    """Retrieve-then-rank: shrink AU codes with $text, then let AI pick the best."""
    api_key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        return {"_error": "PERPLEXITY_API_KEY not configured"}

    # Only pull the few fields we actually send to the LLM
    proj = {
        "_id": 0, "code": 1, "title": 1,
        "hierarchy.unit_group_name": 1, "assessing_authority.name": 1, "alternative_titles": 1,
    }
    query = {"country_code": "AU", "status": {"$ne": "superseded"}}
    docs: List[Dict[str, Any]] = []
    if (description or "").strip():
        tq = dict(query)
        tq["$text"] = {"$search": description}
        tproj = dict(proj)
        tproj["score"] = {"$meta": "textScore"}
        try:
            docs = [o async for o in db["occupation_master"].find(
                tq, tproj,
            ).sort([("score", {"$meta": "textScore"})]).limit(max_candidates)]
        except Exception:
            docs = []
    if not docs:
        docs = [o async for o in db["occupation_master"].find(query, proj).limit(max_candidates)]
    if not docs:
        return {"_error": "No AU occupation codes in knowledge base"}

    available = [{
        "code": o.get("code"),
        "title": o.get("title"),
        "group": (o.get("hierarchy") or {}).get("unit_group_name"),
        "assessing_body": (o.get("assessing_authority") or {}).get("name"),
        "alt": (o.get("alternative_titles") or [])[:3],
    } for o in docs]
    valid_codes = {a["code"] for a in available}

    prompt = (
        "## CANDIDATE PROFILE (from resume)\n" + (description or "")[:4000]
        + "\n\n## AVAILABLE_CODES (choose only from these)\n```json\n"
        + json.dumps(available, ensure_ascii=False)
        + "\n```\n\nReturn the best code + alternatives as JSON."
    )

    try:
        _http = httpx.AsyncClient(verify=False, timeout=60)
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai",
            http_client=_http,
        )
        response = None
        for attempt in range(5):
            try:
                response = await client.chat.completions.create(
                    model=AI_MATCH_MODEL,
                    temperature=0.1,
                    max_tokens=1500,
                    messages=[
                        {"role": "system", "content": _MATCH_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                )
                break
            except Exception as re_err:
                err_str = str(re_err).lower()
                if ("429" in err_str or "rate limit" in err_str) and attempt < 4:
                    wait_sec = 2.0 * (attempt + 1) + 0.5
                    logger.warning(f"Perplexity rate limited on match_anzsco, retrying in {wait_sec:.1f}s...")
                    await asyncio.sleep(wait_sec)
                    continue
                raise

        if not response:
            return {"_error": "No response from AI"}

        raw = response.choices[0].message.content or ""
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw.strip(), flags=re.IGNORECASE)
            raw = re.sub(r"```$", "", raw.strip())
        i, j = raw.find("{"), raw.rfind("}")
        if i == -1 or j == -1:
            return {"_error": "AI returned non-JSON", "_raw": raw[:200]}
        json_str = raw[i:j + 1]
        json_str = re.sub(r"[\x00-\x1F\x7F]", "", json_str)
        json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)
        parsed = json.loads(json_str)
        best = parsed.get("best") or None
        if best and best.get("code") not in valid_codes:
            best = None  # hallucinated code — drop
        alts = [a for a in (parsed.get("alternatives") or []) if a.get("code") in valid_codes][:3]
        return {"best": best, "alternatives": alts}
    except json.JSONDecodeError as e:
        return {"_error": f"AI malformed JSON: {e}"}
    except Exception as e:  # noqa: BLE001
        logger.error(f"match_anzsco error: {e}")
        return {"_error": f"AI call failed: {type(e).__name__}"}


def build_description(profile: Dict[str, Any]) -> str:
    """Turn an AI-parsed resume profile into a compact occupation description."""
    pa = profile.get("primary_applicant") or {}
    prof = pa.get("professional") or {}
    parts: List[str] = []
    for k in ("current_profession", "designation", "industry", "employer_name"):
        v = prof.get(k)
        if v:
            parts.append(str(v))
    for w in (pa.get("work_history") or [])[:2]:
        if w.get("designation"):
            parts.append(str(w["designation"]))
        if w.get("duties"):
            parts.append(str(w["duties"]))
    edu = pa.get("education") or {}
    if edu.get("field_of_study"):
        parts.append("Studied " + str(edu["field_of_study"]))
    return " · ".join(parts).strip()
