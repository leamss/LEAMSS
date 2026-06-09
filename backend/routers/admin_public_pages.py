"""Phase 15 — Public Pages Manager (admin + public read).

Admin endpoints (require admin auth):
  GET    /admin-public-pages/urls?country=&search=&limit=&offset=  — paginated URL list with lead counts
  POST   /admin-public-pages/qr                                    — generate QR code PNG for any URL
  GET    /admin-public-pages/analytics?days=30                     — per-URL lead conversion analytics
  GET    /admin-public-pages/top-pages?limit=10&days=30            — top performing URLs by lead count

Editable content (admin write + public read):
  GET    /admin-public-pages/content/{section}        (admin)
  PUT    /admin-public-pages/content/{section}        (admin)
  GET    /public-pages/content/{section}              (public — frontend uses this)

Sections supported: hero, featured_codes, testimonials, faqs, trust_strip
Persisted to `public_content` collection (one document per section).
"""
from __future__ import annotations

import os
import io
import base64
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Response
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

from core.auth import get_current_user

# ─── DB ─────────────────────────────────────────────────────────────────────
_mongo_url = os.environ["MONGO_URL"]
_db_name = os.environ["DB_NAME"]
db = AsyncIOMotorClient(_mongo_url)[_db_name]

router = APIRouter(prefix="/admin-public-pages", tags=["public-pages-manager"])
public_router = APIRouter(prefix="/public-pages", tags=["public-pages-read"])

CONTENT_COLLECTION = "public_content"
ALLOWED_SECTIONS = {"hero", "featured_codes", "testimonials", "faqs", "trust_strip"}


def _is_admin(user: dict) -> bool:
    return (user or {}).get("role") == "admin"


def _public_site_url() -> str:
    base = (os.environ.get("PUBLIC_SITE_URL") or os.environ.get("FRONTEND_URL") or "https://leamss.com").rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "https://" + base
    return base


# ─── Default seed content (used if section doc not yet in DB) ──────────────
DEFAULTS = {
    "hero": {
        "eyebrow": "100% Refund Guarantee · MARA Registered",
        "title_line1": "Find your migration",
        "title_line2": "pathway",
        "title_line3_accent": "in 60 seconds.",
        "subtitle": "Free AI eligibility check across 80+ visa categories for Australia, Canada & New Zealand. No login. No spam. Just an honest scorecard.",
        "cta_primary": "Start AI Eligibility Quiz",
        "cta_secondary": "Browse Migration Atlas",
        "rating": "4.9 / 5",
        "rating_subtitle": "from 500+ Google reviews",
    },
    "featured_codes": [
        {"country_code": "AU", "code": "261313", "title": "Software Engineer"},
        {"country_code": "AU", "code": "233211", "title": "Civil Engineer"},
        {"country_code": "AU", "code": "254499", "title": "Registered Nurses"},
        {"country_code": "AU", "code": "263111", "title": "Computer Network Engineer"},
        {"country_code": "CA", "code": "21231",  "title": "Software Engineers"},
        {"country_code": "CA", "code": "21321",  "title": "Industrial Engineers"},
        {"country_code": "CA", "code": "31301",  "title": "Registered Nurses"},
        {"country_code": "CA", "code": "72310",  "title": "Carpenters"},
        {"country_code": "NZ", "code": "261313", "title": "Software Engineer"},
        {"country_code": "NZ", "code": "253111", "title": "General Practitioner"},
        {"country_code": "NZ", "code": "341111", "title": "Electrician (General)"},
        {"country_code": "NZ", "code": "233211", "title": "Civil Engineer"},
    ],
    "testimonials": [
        {"name": "Sophia Chowdhury", "city": "Mumbai → Sydney", "text": "I am so grateful to Leamss for helping me navigate my Australian PR journey. Their expertise and support made a huge difference.", "stars": 5},
        {"name": "Varsha Bhatia", "city": "Pune → Toronto", "text": "Extremely happy with the services. Team was supportive, professional, highly responsive. Patiently addressed all queries.", "stars": 5},
        {"name": "Krishna KV", "city": "Bangalore → Brisbane", "text": "Practical, supportive and expert in analyzing profiles for ideal destination. Strongly recommend for anyone exploring migration.", "stars": 5},
        {"name": "Gurleen Kaur", "city": "Delhi → Auckland", "text": "A wonderful team to work with. Worth trusting. Professional, lucid. They have marked their words and made this journey wonderful.", "stars": 5},
    ],
    "faqs": [
        {"q": "What is ANZSCO and why does my occupation code matter?",
         "a": "ANZSCO (Australian and New Zealand Standard Classification of Occupations) is the official code used by Department of Home Affairs Australia and Immigration NZ. Your 6-digit code (e.g., 261313 Software Engineer) decides which visa subclasses you can apply for, which state nominates, and what salary you can expect."},
        {"q": "How are CRS points calculated for Canada Express Entry?",
         "a": "CRS (Comprehensive Ranking System) scores you out of 1200 points based on age, education, official language ability (CLB), work experience, adaptability, and additional factors. You need at least 67 points on the FSWP eligibility scoresheet to enter the pool, then your CRS determines whether you get an Invitation to Apply (ITA)."},
        {"q": "What's the difference between NZ SMC and Green List?",
         "a": "SMC (Skilled Migrant Category) is NZ's standard 6-point system for residency. Green List occupations (Tier 1 = Straight to Residence, Tier 2 = Work-to-Residence after 24 months on AEWV) bypass the regular SMC scoring and offer faster, simpler pathways for high-demand roles."},
        {"q": "Is the 100% Refund Guarantee real? What's the catch?",
         "a": "Yes — we offer a written refund policy if your skill assessment is negative or your visa is rejected due to LEAMSS-attributable error. The only exclusion: rejections due to false information you provided (which is a legal disqualifier anyway). Full policy: leamss.com/privacy-policy."},
        {"q": "How long does the whole PR process take from start to finish?",
         "a": "Typical timelines: Australia 189/190 (12-18 months end-to-end), Canada Express Entry (6-12 months), NZ Green List Tier 1 (3-6 months), NZ SMC (12-18 months). LEAMSS provides a fixed-timeline guarantee on Express Entry profiles."},
        {"q": "Can I migrate without an English test (IELTS/PTE)?",
         "a": "No major skilled visa pathway allows skipping the English test. Minimum requirements: Australia (IELTS 6.0 each band or equivalent PTE), Canada (CLB 7), New Zealand (IELTS 6.5). However, LEAMSS offers PTE/IELTS coaching as part of our PR package."},
    ],
    "trust_strip": [
        {"num": "80+",  "label": "Visa Categories"},
        {"num": "80k+", "label": "Visas Processed"},
        {"num": "80+",  "label": "LEAMSS Experts"},
        {"num": "4.9★", "label": "Google Reviews"},
        {"num": "100%", "label": "Refund on Negative Assessment"},
        {"num": "12+",  "label": "Years of Trust"},
    ],
}


# ─── Module 1: URL Browser + QR ─────────────────────────────────────────────
@router.get("/urls")
async def list_public_urls(
    country: Optional[str] = Query(None, regex="^(AU|CA|NZ|all)$"),
    search: Optional[str] = Query(None, max_length=80),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Return paginated list of all public URLs with lead counts."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    base = _public_site_url()
    rows: List[Dict[str, Any]] = []

    # Static URLs
    if not search:
        for path, title, tag in [
            ("/start", "Mega Landing Page", "landing"),
            ("/atlas", "Atlas Hub", "hub"),
            ("/atlas/au", "Australia Atlas", "country"),
            ("/atlas/ca", "Canada Atlas", "country"),
            ("/atlas/nz", "New Zealand Atlas", "country"),
        ]:
            if country and country != "all" and tag == "country" and country.lower() not in path:
                continue
            rows.append({
                "url": f"{base}{path}",
                "path": path,
                "title": title,
                "country_code": path.split("/")[-1].upper() if tag == "country" else None,
                "code": None,
                "kind": tag,
            })

    # Occupation URLs (verified only)
    match: Dict[str, Any] = {"status": "verified"}
    if country and country != "all":
        match["country_code"] = country
    if search:
        import re
        s = re.escape(search.strip())
        match["$or"] = [{"code": {"$regex": s, "$options": "i"}}, {"title": {"$regex": s, "$options": "i"}}]

    total = await db["occupation_master"].count_documents(match) + (len(rows) if not search else 0)

    cursor = db["occupation_master"].find(
        match,
        {"_id": 0, "code": 1, "title": 1, "country_code": 1},
    ).sort([("country_code", 1), ("code", 1)]).skip(max(0, offset - (len(rows) if not search else 0))).limit(limit - len(rows))

    async for d in cursor:
        c = d["country_code"]
        rows.append({
            "url": f"{base}/atlas/{c.lower()}/{d['code']}",
            "path": f"/atlas/{c.lower()}/{d['code']}",
            "title": d["title"],
            "country_code": c,
            "code": d["code"],
            "kind": "occupation",
        })

    # Lead counts per URL (last 30 days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    leads_by_code: Dict[str, int] = {}
    leads_by_kind: Dict[str, int] = {"landing": 0, "hub": 0, "country": 0, "occupation": 0}
    async for lead in db["leads"].find(
        {"source": "public_atlas", "created_at": {"$gte": cutoff}},
        {"_id": 0, "atlas_code": 1, "country_of_interest": 1},
    ):
        ac = lead.get("atlas_code") or ""
        if ac == "mega-landing":
            leads_by_kind["landing"] += 1
        elif ac:
            leads_by_code[ac] = leads_by_code.get(ac, 0) + 1

    # Annotate rows
    for r in rows:
        if r["kind"] == "occupation" and r.get("code"):
            r["leads_30d"] = leads_by_code.get(r["code"], 0)
        elif r["kind"] == "landing":
            r["leads_30d"] = leads_by_kind["landing"]
        else:
            r["leads_30d"] = 0

    return {"total": total, "offset": offset, "limit": limit, "items": rows, "site_url": base}


@router.post("/qr")
async def generate_qr_code(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Generate a QR code PNG (base64) for a URL.

    Body: { url: "https://..." }
    Returns: { data_url: "data:image/png;base64,..." }
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    url = (payload.get("url") or "").strip()
    if not url:
        raise HTTPException(400, "url is required")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "url must be absolute (http:// or https://)")
    if len(url) > 800:
        raise HTTPException(400, "url too long")

    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"url": url, "data_url": f"data:image/png;base64,{b64}"}


# ─── Module 2: Editable Content ─────────────────────────────────────────────
class ContentEnvelope(BaseModel):
    section: str
    data: Any
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


def _validate_section_data(section: str, data: Any) -> None:
    """Type-check the inbound data before persisting."""
    if section == "hero":
        if not isinstance(data, dict):
            raise HTTPException(400, "hero must be an object")
        required = {"title_line1", "title_line2", "title_line3_accent", "subtitle", "cta_primary", "cta_secondary"}
        missing = required - set(data.keys())
        if missing:
            raise HTTPException(400, f"hero missing fields: {sorted(missing)}")
    elif section == "featured_codes":
        if not isinstance(data, list) or not (1 <= len(data) <= 24):
            raise HTTPException(400, "featured_codes must be 1-24 items")
        for it in data:
            if not isinstance(it, dict) or "country_code" not in it or "code" not in it or "title" not in it:
                raise HTTPException(400, "Each featured code needs country_code + code + title")
    elif section == "testimonials":
        if not isinstance(data, list) or len(data) > 24:
            raise HTTPException(400, "testimonials max 24 items")
        for it in data:
            if not isinstance(it, dict):
                raise HTTPException(400, "Each testimonial must be an object")
            if not it.get("name") or not it.get("text"):
                raise HTTPException(400, "Each testimonial needs name + text")
    elif section == "faqs":
        if not isinstance(data, list) or len(data) > 30:
            raise HTTPException(400, "faqs max 30 items")
        for it in data:
            if not isinstance(it, dict) or not it.get("q") or not it.get("a"):
                raise HTTPException(400, "Each FAQ needs q + a")
    elif section == "trust_strip":
        if not isinstance(data, list) or len(data) > 12:
            raise HTTPException(400, "trust_strip max 12 items")
        for it in data:
            if not isinstance(it, dict) or not it.get("num") or not it.get("label"):
                raise HTTPException(400, "Each trust item needs num + label")


@router.get("/content/{section}")
async def get_content_admin(section: str, current_user: dict = Depends(get_current_user)):
    """Admin read of a single content section."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if section not in ALLOWED_SECTIONS:
        raise HTTPException(400, f"Unknown section: {section}")
    return await _get_section(section)


@router.put("/content/{section}")
async def put_content_admin(
    section: str,
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Admin save / update a content section."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if section not in ALLOWED_SECTIONS:
        raise HTTPException(400, f"Unknown section: {section}")
    data = payload.get("data")
    if data is None:
        raise HTTPException(400, "Body must include 'data'")
    _validate_section_data(section, data)

    now = datetime.now(timezone.utc).isoformat()
    actor = current_user.get("email") or current_user.get("id") or "admin"
    await db[CONTENT_COLLECTION].update_one(
        {"_id": section},
        {"$set": {"_id": section, "data": data, "updated_at": now, "updated_by": actor}},
        upsert=True,
    )
    return {"ok": True, "section": section, "updated_at": now, "updated_by": actor}


@router.post("/content/{section}/reset")
async def reset_content_admin(section: str, current_user: dict = Depends(get_current_user)):
    """Reset a section back to the hardcoded defaults."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if section not in ALLOWED_SECTIONS:
        raise HTTPException(400, f"Unknown section: {section}")
    res = await db[CONTENT_COLLECTION].delete_one({"_id": section})
    return {"ok": True, "section": section, "deleted": res.deleted_count}


async def _get_section(section: str) -> Dict[str, Any]:
    """Internal helper — returns persisted section or falls back to defaults."""
    doc = await db[CONTENT_COLLECTION].find_one({"_id": section}, {"_id": 0})
    if doc and "data" in doc:
        return {
            "section": section,
            "data": doc["data"],
            "is_default": False,
            "updated_at": doc.get("updated_at"),
            "updated_by": doc.get("updated_by"),
        }
    return {
        "section": section,
        "data": DEFAULTS.get(section),
        "is_default": True,
        "updated_at": None,
        "updated_by": None,
    }


# ─── Public read (used by /start + /atlas pages) ───────────────────────────
@public_router.get("/content/{section}")
async def get_content_public(section: str):
    """No-auth read of a content section. Used by frontend public pages."""
    if section not in ALLOWED_SECTIONS:
        raise HTTPException(400, f"Unknown section: {section}")
    return await _get_section(section)


@public_router.get("/content")
async def get_all_content_public():
    """Fetch all sections in one call (used by /start landing page)."""
    out = {}
    for section in ALLOWED_SECTIONS:
        out[section] = (await _get_section(section))["data"]
    return out


# ─── Module 3: Analytics ────────────────────────────────────────────────────
@router.get("/analytics")
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Per-URL conversion data + daily trend for the last `days` days."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total leads in window
    total_leads = await db["leads"].count_documents({"source": "public_atlas", "created_at": {"$gte": cutoff}})

    # Top occupation codes
    pipeline = [
        {"$match": {"source": "public_atlas", "created_at": {"$gte": cutoff}, "atlas_code": {"$ne": None}}},
        {"$group": {"_id": {"code": "$atlas_code", "title": "$atlas_title"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 50},
    ]
    top_codes: List[Dict[str, Any]] = []
    async for doc in db["leads"].aggregate(pipeline):
        top_codes.append({
            "atlas_code": doc["_id"].get("code"),
            "atlas_title": doc["_id"].get("title"),
            "leads": doc["count"],
        })

    # Country distribution
    country_pipeline = [
        {"$match": {"source": "public_atlas", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$country_of_interest", "count": {"$sum": 1}}},
    ]
    country_dist: Dict[str, int] = {}
    async for doc in db["leads"].aggregate(country_pipeline):
        country_dist[doc["_id"] or "unknown"] = doc["count"]

    # Daily trend
    trend_pipeline = [
        {"$match": {"source": "public_atlas", "created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    daily_trend: List[Dict[str, Any]] = []
    async for doc in db["leads"].aggregate(trend_pipeline):
        daily_trend.append({"date": doc["_id"], "leads": doc["count"]})

    return {
        "days": days,
        "total_leads": total_leads,
        "top_codes": top_codes,
        "country_distribution": country_dist,
        "daily_trend": daily_trend,
    }


@router.get("/top-pages")
async def get_top_pages(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Quick view of top-performing public pages by lead conversion."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"source": "public_atlas", "created_at": {"$gte": cutoff}, "atlas_code": {"$ne": None}}},
        {"$group": {
            "_id": {"code": "$atlas_code", "title": "$atlas_title", "country": "$country_of_interest"},
            "leads": {"$sum": 1},
            "last_lead_at": {"$max": "$created_at"},
        }},
        {"$sort": {"leads": -1}},
        {"$limit": limit},
    ]
    base = _public_site_url()
    pages: List[Dict[str, Any]] = []
    async for doc in db["leads"].aggregate(pipeline):
        c = (doc["_id"].get("country") or "").lower() or "au"
        code = doc["_id"].get("code") or ""
        pages.append({
            "atlas_code": code,
            "atlas_title": doc["_id"].get("title"),
            "country": doc["_id"].get("country"),
            "leads": doc["leads"],
            "url": f"{base}/atlas/{c}/{code}" if code and code != "mega-landing" else f"{base}/start",
            "last_lead_at": doc["last_lead_at"].isoformat() if doc["last_lead_at"] else None,
        })
    return {"days": days, "pages": pages}
