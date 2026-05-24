"""Phase 6.10 Part 3 — Country Guides (Admin-managed Knowledge Base + Public-facing).

Each country has a single rich guide document with:
  • Hero (title, subtitle, hero image_url)
  • Sections (ordered, markdown body)
  • FAQ items (question + answer)
  • Status: draft → verified (admin re-verifies after every edit)
  • AI Draft block (cached output from Claude Sonnet 4.6, admin reviews/copies)

Endpoints (under /api/country-guides):
  GET    /                            — admin lists all guides (status filter)
  GET    /public                      — public lists VERIFIED guides for SEO
  GET    /public/{code}               — public read-only single guide
  GET    /{code}                      — admin gets full guide (drafts allowed)
  POST   /                            — admin create (draft, idempotent on country_code)
  PUT    /{code}                      — admin edit (auto-flips to draft)
  POST   /{code}/ai-draft             — generate Claude draft, cached on doc
  POST   /{code}/verify               — admin verifies with source_reference
  POST   /seed-defaults               — admin one-click seed AU/CA/NZ/UK/USA shells
  DELETE /{code}                      — soft-delete (status=archived)
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.kb_ai import _call_claude, _strip_json_fences, now_utc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/country-guides", tags=["country-guides"])

GUIDES = db["country_guides"]

ADMIN_ROLES = {"admin", "admin_owner"}

# Curated 5-country base set (must always exist as guides)
DEFAULT_COUNTRIES = [
    {"code": "AU", "name": "Australia", "flag": "🇦🇺", "tagline": "Skilled Migration to the Land Down Under"},
    {"code": "CA", "name": "Canada", "flag": "🇨🇦", "tagline": "Permanent Residency through Express Entry & PNP"},
    {"code": "NZ", "name": "New Zealand", "flag": "🇳🇿", "tagline": "Skilled Migrant Category to Aotearoa"},
    {"code": "UK", "name": "United Kingdom", "flag": "🇬🇧", "tagline": "Skilled Worker & Global Talent Routes"},
    {"code": "USA", "name": "United States", "flag": "🇺🇸", "tagline": "H1B, EB-2 NIW & Green Card Pathways"},
]

DEFAULT_SECTION_KEYS = [
    {"key": "overview", "title": "Country Overview"},
    {"key": "pr_pathways", "title": "PR Pathways"},
    {"key": "eligibility", "title": "Eligibility Snapshot"},
    {"key": "fees", "title": "Fees & Costs"},
    {"key": "timeline", "title": "Processing Timeline"},
    {"key": "pros_cons", "title": "Pros & Cons"},
    {"key": "settlement", "title": "Settlement & Life After PR"},
]


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _strip(d: dict) -> dict:
    if d and "_id" in d:
        d.pop("_id", None)
    return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class SectionModel(BaseModel):
    key: str
    title: str
    body_markdown: str = ""


class FAQItem(BaseModel):
    question: str
    answer: str


class HeroModel(BaseModel):
    title: str = ""
    subtitle: str = ""
    image_url: Optional[str] = None


class GuideUpdate(BaseModel):
    hero: Optional[HeroModel] = None
    sections: Optional[List[SectionModel]] = None
    faq: Optional[List[FAQItem]] = None


class GuideCreate(BaseModel):
    country_code: str
    name: str
    flag: str = ""
    tagline: str = ""


class VerifyRequest(BaseModel):
    source_reference: str = Field(..., min_length=5, description="Official URL or source the admin verified against.")


# ─────────────────────────────────────────────────────────────────────────────
# Seed defaults
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_guide_if_missing(country: Dict[str, Any]) -> Dict[str, Any]:
    existing = await GUIDES.find_one({"country_code": country["code"]}, {"_id": 0})
    if existing:
        return existing
    now = now_utc()
    doc = {
        "country_code": country["code"],
        "name": country["name"],
        "flag": country["flag"],
        "tagline": country["tagline"],
        "hero": {
            "title": f"{country['flag']} {country['name']}",
            "subtitle": country["tagline"],
            "image_url": None,
        },
        "sections": [
            {"key": s["key"], "title": s["title"], "body_markdown": ""}
            for s in DEFAULT_SECTION_KEYS
        ],
        "faq": [],
        "status": "draft",
        "verification": {"by": None, "by_name": None, "at": None, "source_reference": None},
        "ai_draft": {"generated_at": None, "model": None, "sections": {}, "faq": []},
        "created_at": now,
        "updated_at": now,
    }
    await GUIDES.insert_one(doc)
    return _strip(doc)


@router.post("/seed-defaults")
async def seed_defaults(current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    created = 0
    skipped = 0
    for c in DEFAULT_COUNTRIES:
        existing = await GUIDES.find_one({"country_code": c["code"]}, {"_id": 0})
        if existing:
            skipped += 1
            continue
        await _seed_guide_if_missing(c)
        created += 1
    return {"ok": True, "created": created, "skipped_existing": skipped, "total": len(DEFAULT_COUNTRIES)}


# ─────────────────────────────────────────────────────────────────────────────
# Admin list / detail
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/")
async def list_guides(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    q: Dict[str, Any] = {}
    if status:
        q["status"] = status
    docs = await GUIDES.find(q, {"_id": 0}).sort("country_code", 1).to_list(50)
    # Auto-seed defaults on first ever call so admin has a starting set
    if not docs:
        for c in DEFAULT_COUNTRIES:
            await _seed_guide_if_missing(c)
        docs = await GUIDES.find(q, {"_id": 0}).sort("country_code", 1).to_list(50)
    return {"items": docs, "count": len(docs)}


@router.get("/public")
async def list_public_guides():
    """Public list of VERIFIED guides — used for SEO landing / homepage links."""
    docs = await GUIDES.find(
        {"status": "verified"},
        {"_id": 0, "country_code": 1, "name": 1, "flag": 1, "tagline": 1, "hero": 1, "updated_at": 1},
    ).sort("country_code", 1).to_list(50)
    return {"items": docs, "count": len(docs)}


@router.get("/public/{code}")
async def get_public_guide(code: str):
    """Public single-guide. Only verified guides are exposed publicly.

    Returns 404 for draft / archived guides to avoid leaking unverified content.
    """
    doc = await GUIDES.find_one({"country_code": code.upper(), "status": "verified"}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Guide not found or not yet published")
    # Strip admin-only fields
    doc.pop("ai_draft", None)
    return doc


@router.get("/{code}")
async def get_guide(code: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    doc = await GUIDES.find_one({"country_code": code.upper()}, {"_id": 0})
    if not doc:
        # Auto-seed if it's one of our defaults
        default = next((c for c in DEFAULT_COUNTRIES if c["code"] == code.upper()), None)
        if not default:
            raise HTTPException(404, "Guide not found")
        doc = await _seed_guide_if_missing(default)
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# Admin write
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/")
async def create_guide(payload: GuideCreate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    code = payload.country_code.upper()
    existing = await GUIDES.find_one({"country_code": code}, {"_id": 0})
    if existing:
        raise HTTPException(409, f"Guide for {code} already exists")
    doc = await _seed_guide_if_missing({
        "code": code, "name": payload.name, "flag": payload.flag, "tagline": payload.tagline,
    })
    return doc


@router.put("/{code}")
async def update_guide(code: str, payload: GuideUpdate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    code = code.upper()
    existing = await GUIDES.find_one({"country_code": code}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Guide not found")
    update: Dict[str, Any] = {"updated_at": now_utc()}
    if payload.hero is not None:
        update["hero"] = payload.hero.model_dump()
    if payload.sections is not None:
        update["sections"] = [s.model_dump() for s in payload.sections]
    if payload.faq is not None:
        update["faq"] = [f.model_dump() for f in payload.faq]
    # Any edit reverts status to draft (admin must re-verify)
    update["status"] = "draft"
    update["verification"] = {"by": None, "by_name": None, "at": None, "source_reference": None}
    await GUIDES.update_one({"country_code": code}, {"$set": update})
    doc = await GUIDES.find_one({"country_code": code}, {"_id": 0})
    return doc


@router.post("/{code}/verify")
async def verify_guide(code: str, req: VerifyRequest, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    code = code.upper()
    existing = await GUIDES.find_one({"country_code": code}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Guide not found")
    await GUIDES.update_one(
        {"country_code": code},
        {"$set": {
            "status": "verified",
            "verification": {
                "by": current_user.get("id"),
                "by_name": current_user.get("name") or current_user.get("email"),
                "at": now_utc(),
                "source_reference": req.source_reference,
            },
            "updated_at": now_utc(),
        }},
    )
    doc = await GUIDES.find_one({"country_code": code}, {"_id": 0})
    return doc


@router.delete("/{code}")
async def archive_guide(code: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    code = code.upper()
    r = await GUIDES.update_one({"country_code": code}, {"$set": {"status": "archived", "updated_at": now_utc()}})
    if r.matched_count == 0:
        raise HTTPException(404, "Guide not found")
    return {"ok": True, "archived": code}


# ─────────────────────────────────────────────────────────────────────────────
# AI Draft
# ─────────────────────────────────────────────────────────────────────────────
import json as _json


async def _draft_country_guide(country_name: str, country_code: str) -> Dict[str, Any]:
    """Generate AI baseline for sections + FAQ. Strict no-invented-numbers rules."""
    system = (
        "You are an immigration knowledge-base drafting assistant for a migration consultancy. "
        "Draft factual baseline content about a country's immigration landscape for an ADMIN to verify "
        "against official sources (Home Affairs AU, IRCC CA, INZ NZ, UK Home Office, USCIS US). "
        "STRICT RULES:\n"
        "  1. Never invent specific government fees, exact thresholds, or recent policy dates.\n"
        "  2. Never claim a program 'has been cancelled' or 'is open' without acknowledging it as 'subject to current policy'.\n"
        "  3. Keep tone professional, concise, suitable for an HNI consultation deck.\n"
        "  4. Return ONLY valid JSON. No prose, no markdown fences."
    )
    user_prompt = (
        f"Draft baseline immigration guide content for {country_name} ({country_code}). Output JSON only.\n\n"
        f"Required JSON shape:\n"
        f"{{\n"
        f'  "hero_subtitle": "Short hero subline (~12-18 words) capturing the migration value prop.",\n'
        f'  "sections": {{\n'
        f'    "overview": "2-3 paragraphs (200-350 words) on the country\'s migration landscape, who it is for, demand outlook.",\n'
        f'    "pr_pathways": "Markdown list of major PR pathways with 1-2 line description each. Examples: skilled, employer-sponsored, family, business.",\n'
        f'    "eligibility": "2-3 paragraphs (150-250 words) on broad eligibility levers — age, English, education, work experience, points-based note.",\n'
        f'    "fees": "Markdown note on approximate cost categories (gov fees, body fees, settlement funds, professional fees). NEVER quote precise figures — say \'admin to update from official source\'.",\n'
        f'    "timeline": "Approximate stages and rough duration ranges. No exact dates.",\n'
        f'    "pros_cons": "Markdown ## Pros and ## Cons headings each with 3-5 bullets.",\n'
        f'    "settlement": "1-2 paragraphs on life after PR — citizenship pathway, healthcare, schooling, common cities."\n'
        f'  }},\n'
        f'  "faq": [\n'
        f'    {{"question": "Q1", "answer": "A1 (1-2 sentences)"}},\n'
        f'    ...8 short Q&A pairs spanning eligibility, fees, timeline, family, work-rights, citizenship.\n'
        f'  ],\n'
        f'  "admin_verify_note": "One line guidance on what an admin must specifically verify against official sources."\n'
        f"}}"
    )
    raw = await _call_claude(system, user_prompt, session_prefix="country-guide-draft")
    raw = _strip_json_fences(raw)
    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError:
        raw2 = await _call_claude(
            system + "\nIMPORTANT: Your last response was not valid JSON. Return ONLY raw JSON.",
            user_prompt,
            session_prefix="country-guide-retry",
        )
        data = _json.loads(_strip_json_fences(raw2))
    data.setdefault("hero_subtitle", "")
    data.setdefault("sections", {})
    data.setdefault("faq", [])
    data.setdefault("admin_verify_note", "Admin must verify all specific numbers against the official source.")
    return data


@router.post("/{code}/ai-draft")
async def generate_ai_draft(code: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    code = code.upper()
    doc = await GUIDES.find_one({"country_code": code}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Guide not found")
    try:
        data = await _draft_country_guide(doc["name"], code)
    except Exception as e:
        logger.exception("AI draft failed for country guide %s", code)
        raise HTTPException(500, f"AI draft failed: {e}")
    ai_draft = {
        "generated_at": now_utc(),
        "model": "claude-sonnet-4-6",
        "hero_subtitle": data.get("hero_subtitle"),
        "sections": data.get("sections", {}),
        "faq": data.get("faq", []),
        "admin_verify_note": data.get("admin_verify_note"),
    }
    await GUIDES.update_one(
        {"country_code": code},
        {"$set": {"ai_draft": ai_draft, "updated_at": now_utc()}},
    )
    return {"ok": True, "ai_draft": ai_draft}
