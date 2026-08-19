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

from core.resume_extractor import extract_text, extract_text_smart, parse_resume_with_ai

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
# Bulk enrichment runs across hundreds of clients — use the fast Haiku model for both
# resume parsing and ANZSCO matching (accurate enough for retrieve-then-rank, ~3x faster).
MATCH_MODEL = "claude-haiku-4-5-20251001"
BULK_PARSE_MODEL = "claude-haiku-4-5-20251001"

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# Many resume hosts (e.g. LiteSpeed on leamss.com) DROP connections under a concurrent
# burst from one IP ("Server disconnected without sending a response"). A single request
# works fine, so we throttle downloads to a small, polite concurrency across the whole batch.
_FETCH_SEM = asyncio.Semaphore(2)
# PDF/DOCX text extraction (pdfplumber/python-docx) is GIL-bound CPU work; even in a thread
# it contends with the event loop. Cap simultaneous extractions so the API stays responsive.
_EXTRACT_SEM = asyncio.Semaphore(2)


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


async def fetch_resume_text(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Download a resume from a public link and return (text, error).

    Retries transient network failures (many hosts, e.g. leamss.com, intermittently
    drop the connection under concurrent load — 'Server disconnected without response').
    """
    if not url:
        return None, "No resume link provided"
    fetch_url = _normalize_resume_url(url)
    transient = (
        httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError,
        httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout, httpx.WriteError,
    )
    last_err: Optional[str] = None
    for attempt in range(4):  # up to 4 tries with jittered backoff
        try:
            async with _FETCH_SEM:  # polite, throttled downloads (avoid host rate-limit drops)
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=httpx.Timeout(45.0, connect=15.0),
                    headers=_UA,
                    limits=httpx.Limits(max_connections=4, max_keepalive_connections=0),
                ) as client:
                    resp = await client.get(fetch_url)
                    resp.raise_for_status()
                    content = resp.content
                    ct = resp.headers.get("content-type", "")
                    cd = resp.headers.get("content-disposition", "")

                    # Google Drive interstitial (large files / virus-scan confirm page)
                    if "text/html" in ct.lower() and content[:2000].lower().find(b"<html") != -1:
                        token = re.search(rb'confirm=([0-9A-Za-z_-]+)', content)
                        gid = re.search(r"id=([A-Za-z0-9_-]+)", fetch_url)
                        if token and gid:
                            resp = await client.get(
                                f"https://drive.google.com/uc?export=download&confirm="
                                f"{token.group(1).decode()}&id={gid.group(1)}",
                            )
                            content = resp.content
                            ct = resp.headers.get("content-type", "")
                            cd = resp.headers.get("content-disposition", "")
                        if "text/html" in ct.lower():
                            return None, "Link opened an HTML page, not a file. Share it as 'Anyone with the link' (Viewer)."

            fname = _guess_filename(fetch_url, ct, cd)
            # Smart extraction: handles PDF/DOCX/TXT and OCRs scanned PDFs & image resumes.
            text, oerr = await extract_text_smart(fname, content)
            if oerr:
                return None, oerr
            return text, None
        except httpx.HTTPStatusError as e:
            return None, f"Download failed (HTTP {e.response.status_code}). Is the link public?"
        except ValueError as e:
            return None, str(e)
        except transient as e:  # noqa: PERF203 — retryable network failure
            last_err = f"{type(e).__name__}: {str(e) or 'connection dropped'}"
            if attempt < 3:
                await asyncio.sleep(0.8 * (attempt + 1) + random.uniform(0, 0.7))
                continue
            logger.warning(f"resume fetch failed after retries for {url}: {last_err}")
            return None, "Could not fetch resume (host dropped the connection after 4 tries). Check the link is publicly reachable."
        except Exception as e:  # noqa: BLE001
            logger.warning(f"resume fetch error for {url}: {e}")
            return None, f"Could not fetch resume: {type(e).__name__}"
    return None, last_err or "Could not fetch resume"


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
                    limits=httpx.Limits(max_connections=4, max_keepalive_connections=0),
                ) as client:
                    resp = await client.get(fetch_url)
                    resp.raise_for_status()
                    content = resp.content
                    ct = resp.headers.get("content-type", "")
                    cd = resp.headers.get("content-disposition", "")
                    if "text/html" in ct.lower() and content[:2000].lower().find(b"<html") != -1:
                        return None, None, "Link opened an HTML page, not a file (private/expired link?)."
            return content, _guess_filename(fetch_url, ct, cd), None
        except httpx.HTTPStatusError as e:
            return None, None, f"Download failed (HTTP {e.response.status_code}). Is the link public?"
        except transient as e:  # noqa: PERF203
            if attempt < 2:
                await asyncio.sleep(0.8 * (attempt + 1) + random.uniform(0, 0.7))
                continue
            return None, None, "Host dropped the connection after retries."
        except Exception as e:  # noqa: BLE001
            return None, None, f"Could not fetch resume: {type(e).__name__}"
    return None, None, "Could not fetch resume"


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
    """Retrieve-then-rank: shrink AU codes with $text, then let Claude pick the best."""
    if not EMERGENT_LLM_KEY:
        return {"_error": "EMERGENT_LLM_KEY not configured"}
    # Only pull the few fields we actually send to the LLM — avoids loading 120 full
    # occupation docs (with big tasks/description arrays) per row, which was blocking the loop.
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
        docs = [o async for o in db["occupation_master"].find(
            tq, tproj,
        ).sort([("score", {"$meta": "textScore"})]).limit(max_candidates)]
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
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except ImportError as e:  # pragma: no cover
        return {"_error": f"emergentintegrations missing: {e}"}
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"anzsco-{os.urandom(3).hex()}",
                       system_message=_MATCH_SYSTEM).with_model("anthropic", MATCH_MODEL)
        # emergentintegrations runs the BLOCKING litellm.completion() on the event loop.
        # Run it in a worker thread (own loop) so concurrent bulk jobs don't freeze the API.
        resp = await asyncio.to_thread(
            lambda: asyncio.run(chat.send_message(UserMessage(text=prompt)))
        )
        raw = (str(resp) if resp is not None else "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        i, j = raw.find("{"), raw.rfind("}")
        if i == -1 or j == -1:
            return {"_error": "AI returned non-JSON", "_raw": raw[:200]}
        parsed = json.loads(raw[i:j + 1])
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
