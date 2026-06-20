"""Phase 13 — Public Atlas Router (SEO + Lead Capture).

NO AUTHENTICATION — these endpoints are publicly accessible so Google can
crawl them and visitors can submit leads without signing up.

Endpoints:
  GET  /api/public-atlas/featured                 — homepage hero (top 12)
  GET  /api/public-atlas/{country}/list           — paginated browse
  GET  /api/public-atlas/{country}/{code}         — single occupation page
  GET  /api/public-atlas/sitemap.xml              — auto-generated sitemap
  POST /api/public-atlas/lead                     — capture lead from CTA form

All `public-atlas` responses include a `seo` block with title/meta_description/
og_image/json_ld for the frontend to inject into <head>.

Rate-limiting: simple in-memory throttle (5 leads/min per IP).
Honeypot: leads with a non-empty `_company_url` field are silently dropped.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Body, Request, Response
from pydantic import BaseModel, EmailStr, Field
from motor.motor_asyncio import AsyncIOMotorClient

# ─── DB ─────────────────────────────────────────────────────────────────────
_mongo_url = os.environ["MONGO_URL"]
_db_name = os.environ["DB_NAME"]
db = AsyncIOMotorClient(_mongo_url)[_db_name]

router = APIRouter(prefix="/public-atlas", tags=["public-atlas"])

# Pre-computed featured codes (most-searched / most-actionable per country).
# Picked from each country's atlas — overrideable later via kb_settings if needed.
FEATURED_CODES = [
    ("AU", "261313", "Software Engineer"),
    ("AU", "233211", "Civil Engineer"),
    ("AU", "254499", "Registered Nurses"),
    ("AU", "263111", "Computer Network Engineer"),
    ("CA", "21231",  "Software Engineers"),
    ("CA", "21321",  "Industrial and Manufacturing Engineers"),
    ("CA", "31301",  "Registered Nurses"),
    ("CA", "72310",  "Carpenters"),
    ("NZ", "261313", "Software Engineer"),
    ("NZ", "253111", "General Practitioner"),
    ("NZ", "341111", "Electrician (General)"),
    ("NZ", "233211", "Civil Engineer"),
]

# Base URL for canonical/og links — read from env so deployment swap is easy.
PUBLIC_SITE_URL = (
    os.environ.get("PUBLIC_SITE_URL")
    or os.environ.get("FRONTEND_URL")
    or ""
)


def _public_site_url() -> str:
    """Return the absolute base URL for SEO canonicals + OG images.

    Priority: PUBLIC_SITE_URL env > FRONTEND_URL env > fallback.
    """
    base = (PUBLIC_SITE_URL or "https://leamss.com").rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "https://" + base
    return base


# ─── Helpers ────────────────────────────────────────────────────────────────
def _safe_doc(d: Dict[str, Any]) -> Dict[str, Any]:
    """Strip MongoDB internals + verification metadata before exposing publicly."""
    d = dict(d)
    d.pop("_id", None)
    d.pop("verification", None)
    d.pop("created_by", None)
    d.pop("ai_draft", None)
    d.pop("_migration_version", None)
    return d


def _code_path_country(country: str) -> str:
    return (country or "").upper()


def _country_meta(code: str) -> Dict[str, str]:
    return {
        "AU": {"flag": "🇦🇺", "name": "Australia",   "classification": "ANZSCO"},
        "CA": {"flag": "🇨🇦", "name": "Canada",      "classification": "NOC 2021"},
        "NZ": {"flag": "🇳🇿", "name": "New Zealand", "classification": "ANZSCO 1.3"},
    }.get(code, {"flag": "", "name": code, "classification": "—"})


LOGO_IMG = "https://leamss.com/public/assets/web/images/logo.webp"


def _org_node() -> Dict[str, Any]:
    """Reusable schema.org Organization node for JSON-LD @graph."""
    return {
        "@type": "Organization",
        "@id": "https://www.leamss.com/#organization",
        "name": "Ladhani Education & Migration Services (OPC) Pvt. Ltd",
        "alternateName": "LEAMSS",
        "url": "https://www.leamss.com",
        "logo": LOGO_IMG,
        "foundingDate": "2014",
        "address": {"@type": "PostalAddress", "addressLocality": "Thane", "addressRegion": "Maharashtra", "addressCountry": "IN"},
        "contactPoint": {"@type": "ContactPoint", "telephone": "+91-77188-82427", "contactType": "customer service", "areaServed": "IN", "availableLanguage": ["en", "hi"]},
    }


def _build_occupation_faqs(country: str, doc: Dict[str, Any], cm: Dict[str, str]) -> List[Dict[str, str]]:
    """Deterministic, occupation-specific FAQ pairs — rendered on the page AND
    emitted as FAQPage JSON-LD so the page is eligible for Google rich results."""
    code = doc.get("code") or ""
    title = doc.get("title") or "this occupation"
    classification = cm["classification"]
    cname = cm["name"]
    body = (doc.get("assessing_authority") or {}).get("name")
    salary = (doc.get("anzsco_profile") or {}).get("median_salary_aud")
    faqs: List[Dict[str, str]] = []

    faqs.append({
        "q": f"How can I migrate to {cname} as a {title}?",
        "a": (
            f"{title} ({code}) is a verified {cname} occupation under {classification}. "
            f"You can migrate through skilled-migration visa pathways after a positive skills assessment"
            f"{f' from {body}' if body else ''}. LEAMSS offers a free eligibility check that maps your "
            f"age, education, English and experience to the best-fit visa pathway for {title}."
        ),
    })

    # Visa pathways (AU / NZ)
    vp = doc.get("visa_pathways") or {}
    eligible = [v.get("visa_subclass") for v in (vp.get("visa_eligibility") or []) if v.get("eligible")]
    if eligible:
        faqs.append({
            "q": f"Which visa subclasses can {title} ({code}) apply for?",
            "a": (
                f"Based on the latest {classification} rules, {title} ({code}) is eligible for the following "
                f"visa pathways: {', '.join(str(e) for e in eligible)}. Exact eligibility also depends on your "
                f"points score, state/territory nomination and English level — confirm with a LEAMSS expert."
            ),
        })

    # Assessing authority
    if body:
        full = (doc.get("assessing_authority") or {}).get("full_name")
        faqs.append({
            "q": f"What is the assessing authority for {title} in {cname}?",
            "a": (
                f"{title} ({code}) is assessed by {body}{f' ({full})' if full and full != body else ''}. "
                f"A positive skills assessment from this authority is required before lodging most skilled-migration "
                f"applications. LEAMSS guides you through the full documentation and RPL/CDR pathway where applicable."
            ),
        })

    # Express Entry (CA)
    ee = doc.get("ee_eligibility") or {}
    if ee:
        progs = []
        if ee.get("fswp_eligible"): progs.append("FSWP")
        if ee.get("cec_eligible"): progs.append("CEC")
        if ee.get("fstp_eligible"): progs.append("FSTP")
        faqs.append({
            "q": f"Is {title} ({code}) eligible for Canada Express Entry?",
            "a": (
                f"{title} (NOC {code}) is "
                + (f"eligible for {', '.join(progs)} under Express Entry." if progs
                   else "currently not eligible under the core Express Entry federal programs.")
                + " Your final outcome depends on your CRS score, language ability (CLB) and provincial nomination."
            ),
        })

    # Green List (NZ)
    tier = doc.get("nz_green_list_tier")
    if tier:
        faqs.append({
            "q": f"Is {title} on the New Zealand Green List?",
            "a": (
                f"Yes — {title} ({code}) is on the New Zealand Green List (Tier {tier}). "
                + ("Tier 1 offers a Straight to Residence pathway. " if str(tier) == "1"
                   else "Tier 2 offers a Work to Residence pathway after 24 months on the AEWV. ")
                + "This is a faster route than the standard SMC 6-point system."
            ),
        })

    # Salary (AU)
    if salary:
        cur = "AUD" if country == "AU" else "CAD" if country == "CA" else "NZD"
        faqs.append({
            "q": f"What salary can a {title} expect in {cname}?",
            "a": (
                f"The indicative median salary for {title} ({code}) in {cname} is around {cur} {salary:,}. "
                f"Actual pay varies by state/region, employer and years of experience."
            ),
        })

    # Brand trust FAQ (always)
    faqs.append({
        "q": "Does LEAMSS offer a refund guarantee?",
        "a": (
            "Yes. LEAMSS offers a written 100% refund guarantee on a negative skill assessment "
            "(excluding rejections caused by false information provided by the applicant). We are MARA-registered "
            "and have helped clients migrate since 2014."
        ),
    })

    return faqs[:6]


_CTA = "Check eligibility with LEAMSS."
_CTA_CORE = _CTA.rstrip(" .")  # "Check eligibility with LEAMSS" — for duplicate detection
_MAX_META_LEN = 165  # Phase 19.5 — hard cap per Sir's brief (SERP-safe)
_TARGET_META_LEN = 150  # ideal SERP-visible length
_MIN_META_LEN = 80     # Phase 19.5 — relaxed: country-specific minimums kick-in via padding

# Phase 19.5 — country-specific rotating CTAs. Picked deterministically by code parity
# so the page-to-page CTA varies subtly without breaking idempotency.
_CTA_POOL = {
    "AU": ["Free eligibility check.", "Free PR pathway guide.", "Get free assessment."],
    "CA": ["Check your CRS score free.", "Free Express Entry guide.", "Get free assessment."],
    "NZ": ["Get free assessment.", "Free Green List eligibility check.", "Free PR pathway guide."],
    "DEFAULT": ["Free eligibility check.", "Get free assessment."],
}


def _pick_cta(country: str, code: str) -> str:
    """Deterministic CTA selection per (country, code) — different occupations get
    different CTAs so SERP snippets stay fresh."""
    pool = _CTA_POOL.get(country) or _CTA_POOL["DEFAULT"]
    # Hash on code char-sum so the same code always picks the same CTA (idempotent).
    digest = sum(ord(c) for c in (code or "0"))
    return pool[digest % len(pool)]


def _ensure_cta_once(s: str) -> str:
    """Guarantee the string ends with exactly ONE trailing CTA.

    Strips any number of trailing CTA repeats (with or without final period)
    then appends a single canonical CTA. Idempotent.
    """
    s = (s or "").strip()
    # Strip trailing CTAs (with optional period / whitespace between repeats)
    while True:
        # Drop trailing whitespace + optional period
        trimmed = s.rstrip()
        if trimmed.endswith("."):
            trimmed = trimmed[:-1].rstrip()
        if trimmed.endswith(_CTA_CORE):
            s = trimmed[: -len(_CTA_CORE)].rstrip(" ,.;:")
            continue
        break
    if s and s[-1] not in ".!?":
        s += "."
    return (s + " " + _CTA).strip()


def _clean_sentence(parts: List[str]) -> str:
    """Join non-empty fragments into a clean sentence — strips empty parens,
    'None', doubled spaces, dangling commas / semicolons / repeated CTAs."""
    s = " ".join(p.strip() for p in parts if p and p.strip())
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    # Strip empty parens / brackets / "None"
    s = re.sub(r"\(\s*\)|\[\s*\]|\bNone\b", "", s)
    # Fix " ," / " ." / " ;" / " :" doubled punctuation
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r",\s*,+", ",", s)
    s = re.sub(r",\s*\.", ".", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Collapse any duplicated CTA (Phase 16.7.1 guard) — e.g. when two builders
    # both appended the CTA in chained calls.
    cta_escaped = re.escape(_CTA_CORE)
    s = re.sub(rf"({cta_escaped}\.?\s*){{2,}}", _CTA + " ", s).strip()
    # Ensure terminal full stop
    if s and s[-1] not in ".!?":
        s += "."
    return s


def _au_visa_subclasses(doc: Dict[str, Any]) -> List[str]:
    """Return ordered unique AU visa subclasses where eligible=True.
    Priority order: PR streams first (189 > 190 > 491 > 186 > 482), then others."""
    seen: List[str] = []
    for v in (doc.get("visa_pathways") or {}).get("visa_eligibility") or []:
        if not v.get("eligible"):
            continue
        sc = str(v.get("visa_subclass") or "").strip()
        if sc and sc not in seen:
            seen.append(sc)
    priority = ["189", "190", "491", "186", "482", "494", "485", "407", "489"]
    return sorted(seen, key=lambda x: priority.index(x) if x in priority else 99)


def _ca_ee_programs(ee: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    if ee.get("fswp_eligible"):
        out.append("FSWP")
    if ee.get("cec_eligible"):
        out.append("CEC")
    if ee.get("fstp_eligible"):
        out.append("FSTP")
    return out


# Friendly labels for IRCC category ids (fallback if `label` is absent).
_CA_CAT_LABELS = {
    "french_language": "French",
    "healthcare": "Healthcare",
    "stem": "STEM",
    "trade": "Trade",
    "education": "Education",
    "transport": "Transport",
    "physicians_ca": "Physicians",
    "senior_managers_ca": "Senior Managers",
    "researchers_ca": "Researchers",
    "military": "Military Recruits",
    "agriculture": "Agriculture",
}


def _ca_categories(ee: Dict[str, Any]) -> List[str]:
    """Return short category labels (max 2) from EE category_details / categories."""
    raw_details = ee.get("category_details") or []
    raw_ids = ee.get("categories") or []
    labels: List[str] = []
    if raw_details:
        for d in raw_details:
            cid = d.get("id")
            lbl = _CA_CAT_LABELS.get(cid) or (d.get("label") or "").split(" ")[0]
            if lbl and lbl not in labels:
                labels.append(lbl)
    else:
        for cid in raw_ids:
            lbl = _CA_CAT_LABELS.get(cid)
            if lbl and lbl not in labels:
                labels.append(lbl)
    return labels[:2]


def _format_salary_aud(value) -> str:
    """Phase 19.5 — format salary as 'AUD $131k' (round to nearest 1k)."""
    if not isinstance(value, (int, float)) or value <= 0:
        return ""
    k = round(value / 1000)
    return f"AUD ${k}k"


def _format_salary_cad(value) -> str:
    if not isinstance(value, (int, float)) or value <= 0:
        return ""
    k = round(value / 1000)
    return f"CAD ${k}k"


def _format_salary_nzd(value) -> str:
    if not isinstance(value, (int, float)) or value <= 0:
        return ""
    k = round(value / 1000)
    return f"NZD ${k}k"


def _build_au_meta(doc: Dict[str, Any], code: str, title: str, country_name: str) -> str:
    """Phase 19.5 — Data-rich AU description.

    Target: `ANZSCO 261313 Software Engineer — Visa 189/190/491 via ACS.
            Median AUD $132k, +27% growth by 2035. Free eligibility check.`
    """
    subs = _au_visa_subclasses(doc)[:3]
    aa = doc.get("assessing_authority") or {}
    body_short = (aa.get("short_name") or "").strip() or (aa.get("name") or "").strip()
    body_short = re.sub(r"\s+(Incorporated|Limited|Ltd\.?|Inc\.?|Pty\.?\s*Ltd)\.?$", "", body_short).split()[0] if body_short else ""

    # Salary — prefer Phase 19.4 ABS data, fall back to anzsco_profile.median_salary_aud
    abs_d = doc.get("abs_data") or {}
    salary_aud = abs_d.get("median_ft_annual_aud") or (doc.get("anzsco_profile") or {}).get("median_salary_aud")
    salary_str = _format_salary_aud(salary_aud)

    # Growth — Phase 19.4 JSA projection (10y growth pct)
    jsa = doc.get("jsa_data") or {}
    growth_pct = jsa.get("growth_pct_2025_to_2035")
    growth_str = ""
    if isinstance(growth_pct, (int, float)):
        sign = "+" if growth_pct >= 0 else ""
        growth_str = f"{sign}{growth_pct:.0f}% growth by 2035"

    # Pathway snippet
    if subs:
        sub_str = "/".join(subs)
        pathway = f"Visa {sub_str}"
    else:
        pathway = "Skilled migration pathway"

    # Authority via
    via = f" via {body_short}" if body_short else ""

    cta = _pick_cta("AU", code)
    head = f"ANZSCO {code} {title}"

    # Build candidate segments in priority order — earlier ones kept, later trimmed first
    # Segment 1: head + pathway via authority
    seg1 = f"{head} — {pathway}{via}."
    # Segment 2: salary + growth (combine if both present)
    if salary_str and growth_str:
        seg2 = f"Median {salary_str}, {growth_str}."
    elif salary_str:
        seg2 = f"Median {salary_str}."
    elif growth_str:
        seg2 = f"{growth_str.capitalize()}."
    else:
        seg2 = ""

    # Try full → trim growth → trim salary → trim authority
    for candidate in (
        f"{seg1} {seg2} {cta}".strip() if seg2 else f"{seg1} {cta}",
        # Without growth
        f"{head} — {pathway}{via}. Median {salary_str}. {cta}" if salary_str else None,
        # Without salary, with growth
        f"{head} — {pathway}{via}. {growth_str.capitalize()}. {cta}" if growth_str else None,
        # Without salary/growth (head + pathway + authority + CTA)
        f"{head} — {pathway}{via}. {cta}",
        # Compact: no authority
        f"{head} — {pathway}. {cta}",
    ):
        if candidate and len(candidate) <= _MAX_META_LEN:
            return _clean_sentence([candidate])

    # Final defensive trim
    s = f"{head} — {pathway}. {cta}"
    return s[:_MAX_META_LEN].rstrip(" ,.;:") + "."


def _build_ca_meta(doc: Dict[str, Any], code: str, title: str, country_name: str) -> str:
    """Phase 19.5 — Data-rich CA description.

    Target: `NOC 21231 Software Engineer — Express Entry FSW/CEC eligible.
            WES assessment. Median CAD $95k. Check your CRS score free.`

    Fallback ladder (drop in order: salary → category → body → trim title).
    EE clause is the TOP signal and kept until last.
    """
    teer = doc.get("teer_category")
    ee = doc.get("ee_eligibility") or {}
    progs = _ca_ee_programs(ee)
    cats = _ca_categories(ee)
    aa = doc.get("assessing_authority") or {}
    body_short = (aa.get("short_name") or aa.get("name") or "").strip()
    body_short = body_short.split()[0] if body_short else ""

    salary_cad = (doc.get("anzsco_profile") or {}).get("median_salary_cad") or (doc.get("salary") or {}).get("median")
    salary_str = _format_salary_cad(salary_cad)

    head = f"NOC {code} {title}"
    cta = _pick_cta("CA", code)

    # Pathway core clause — Express Entry is the top signal
    if progs:
        ee_short = "/".join(progs)  # e.g. FSWP/CEC
        ee_core = f"Express Entry {ee_short} eligible"
    else:
        ee_core = "Skilled migration pathway"

    ee_with_cats = ee_core + (f" + {'/'.join(cats)} category" if cats else "")
    body_clause = f"{body_short} assessment." if body_short else ""
    teer_clause = f"TEER {teer}" if teer is not None else ""

    candidates = [
        # 1. Full: head + EE + categories + body + salary + CTA
        " ".join(s for s in [f"{head} — {ee_with_cats}.", body_clause, f"Median {salary_str}." if salary_str else "", cta] if s),
        # 2. Drop salary
        " ".join(s for s in [f"{head} — {ee_with_cats}.", body_clause, cta] if s),
        # 3. Drop categories
        " ".join(s for s in [f"{head} — {ee_core}.", body_clause, f"Median {salary_str}." if salary_str else "", cta] if s),
        # 4. Drop categories + salary
        " ".join(s for s in [f"{head} — {ee_core}.", body_clause, cta] if s),
        # 5. Drop categories + body
        " ".join(s for s in [f"{head} — {ee_core}.", f"Median {salary_str}." if salary_str else "", cta] if s),
        # 6. Bare-minimum with EE clause
        f"{head} — {ee_core}. {cta}",
    ]
    for candidate in candidates:
        if candidate and len(candidate) <= _MAX_META_LEN:
            return _clean_sentence([candidate])

    # 7. Title too long even for minimal — trim title to fit
    cta_budget = len(f" — {ee_core}. {cta}") + len("NOC 99999 ")
    title_max = _MAX_META_LEN - cta_budget - 3
    short_title = (title[:title_max].rstrip(" -,;:") + "…") if len(title) > title_max else title
    return _clean_sentence([f"NOC {code} {short_title} — {ee_core}. {cta}"])


def _build_nz_meta(doc: Dict[str, Any], code: str, title: str, country_name: str) -> str:
    """Phase 19.5 — Data-rich NZ description.

    Target: `ANZSCO 261313 Software Engineer — NZ Green List Tier 1,
            Straight-to-Residence via NZQA. Median NZD $95k. Get free assessment.`
    """
    tier = doc.get("nz_green_list_tier")
    tier_str = str(tier) if tier is not None else ""
    aewv = (doc.get("aewv_eligibility") or {})
    aewv_ok = bool(aewv.get("eligible")) if isinstance(aewv, dict) else False
    smc = (doc.get("smc_points_breakdown") or {})
    smc_pts = smc.get("skill_points_base") if isinstance(smc, dict) else None
    aa = doc.get("assessing_authority") or {}
    body_short = (aa.get("short_name") or aa.get("name") or "").strip()
    body_short = body_short.split()[0] if body_short else ""

    # Salary — reserve hook for future NZ imports
    salary_nzd = (doc.get("anzsco_profile") or {}).get("median_salary_nzd") or (doc.get("salary") or {}).get("median")
    salary_str = _format_salary_nzd(salary_nzd)

    head = f"ANZSCO {code} {title}"
    cta = _pick_cta("NZ", code)

    # Green-List clause (top NZ signal)
    if tier_str == "1":
        pathway = "NZ Green List Tier 1, Straight-to-Residence"
    elif tier_str == "2":
        pathway = "NZ Green List Tier 2, Work-to-Residence on AEWV"
    elif aewv_ok:
        pathway = "AEWV-eligible skilled work pathway"
    else:
        pathway = "Skilled migration pathway"

    via = f" via {body_short}" if body_short else ""
    smc_clause = f"SMC {int(smc_pts)}-pt base." if isinstance(smc_pts, (int, float)) and smc_pts else ""

    for candidate in (
        # Full
        " ".join(s for s in [f"{head} — {pathway}{via}.", f"Median {salary_str}." if salary_str else "", cta] if s),
        # Without salary, with SMC
        " ".join(s for s in [f"{head} — {pathway}{via}.", smc_clause, cta] if s),
        # Without via
        f"{head} — {pathway}. Median {salary_str}. {cta}" if salary_str else f"{head} — {pathway}. {cta}",
        # Minimal
        f"{head} — {pathway}. {cta}",
    ):
        if candidate and len(candidate) <= _MAX_META_LEN:
            return _clean_sentence([candidate])

    return f"{head} — {pathway[:50]}. {cta}"[:_MAX_META_LEN]


def _build_meta_description(country: str, doc: Dict[str, Any], code: str, title: str, country_name: str) -> str:
    """Phase 19.5 — Data-rich, country-aware meta description for one occupation.

    Returns ≤165 chars woven from real `occupation_master` fields with a
    country-specific rotating CTA. Each builder applies its own length-aware
    fallback ladder; this wrapper only enforces the hard cap defensively.
    """
    if country == "AU":
        meta = _build_au_meta(doc, code, title, country_name)
    elif country == "CA":
        meta = _build_ca_meta(doc, code, title, country_name)
    elif country == "NZ":
        meta = _build_nz_meta(doc, code, title, country_name)
    else:
        cta = _pick_cta(country, code)
        meta = f"{title} ({code}) in {country_name} — skilled migration pathway and eligibility guide. {cta}"

    # Defensive hard-cap at 165 chars; cut at last word boundary if too long.
    if len(meta) > _MAX_META_LEN:
        cut = meta[: _MAX_META_LEN]
        last_space = cut.rfind(" ")
        if last_space > _MAX_META_LEN * 0.5:
            cut = cut[:last_space]
        meta = cut.rstrip(" ,.;:") + "."
    return meta


def _build_seo(country: str, doc: Dict[str, Any], faqs: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Build SEO meta + JSON-LD structured data for one occupation."""
    cm = _country_meta(country)
    code = doc.get("code") or ""
    title = doc.get("title") or "Occupation"
    # Use the country's official classification name (NOT the doc-stored version
    # which may include sync timestamps like "Legacy migration · 2026-05-22").
    classification = cm["classification"]
    salary_min = (doc.get("anzsco_profile") or {}).get("median_salary_aud")
    body = (doc.get("assessing_authority") or {}).get("name")
    description = (doc.get("description") or "").strip()[:400] or (
        f"Comprehensive guide to migrating to {cm['name']} as a {title} ({code}). "
        f"Visa pathways, eligibility, salary trends, and assessing-body requirements."
    )

    page_title = f"{title} ({code}) — {cm['name']} {classification} Migration Guide | LEAMSS"
    # Phase 16.7: data-driven country-aware meta description (replaces boilerplate).
    meta_desc = _build_meta_description(country, doc, code, title, cm["name"])

    # Occupation-specific keywords for long-tail organic search.
    kw = [
        title, code, f"{title} {cm['name']}", f"{cm['name']} PR",
        f"{classification} {code}", f"migrate to {cm['name']} as {title}",
        f"{title} visa pathway", f"{title} skill assessment",
        f"{title} {cm['name']} immigration",
    ]
    if body:
        kw.append(f"{body} skill assessment")
    if doc.get("nz_green_list_tier"):
        kw.append(f"{title} NZ Green List")
    if doc.get("ee_eligibility"):
        kw.append(f"NOC {code} Express Entry")
    kw += ["immigration consultant India", "MARA registered agent", "LEAMSS"]
    keywords = ", ".join(kw)

    # Build absolute URLs — required by Open Graph + Google's canonical spec.
    base = _public_site_url()
    canonical = f"{base}/atlas/{country.lower()}/{code}"
    og_image = LOGO_IMG

    # JSON-LD structured data — @graph with Occupation + BreadcrumbList + FAQPage + Organization
    occupation_node = {
        "@type": "Occupation",
        "@id": f"{canonical}#occupation",
        "name": title,
        "occupationLocation": {"@type": "Country", "name": cm["name"]},
        "occupationalCategory": code,
        "description": description,
        "estimatedSalary": (
            [{
                "@type": "MonetaryAmountDistribution",
                "name": "Median Salary",
                "currency": "AUD" if country == "AU" else "CAD" if country == "CA" else "NZD",
                "median": salary_min,
            }] if salary_min else []
        ),
    }
    breadcrumb_node = {
        "@type": "BreadcrumbList",
        "@id": f"{canonical}#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Atlas", "item": f"{base}/atlas"},
            {"@type": "ListItem", "position": 2, "name": cm["name"], "item": f"{base}/atlas/{country.lower()}"},
            {"@type": "ListItem", "position": 3, "name": f"{title} ({code})", "item": canonical},
        ],
    }
    graph: List[Dict[str, Any]] = [_org_node(), occupation_node, breadcrumb_node]
    if faqs:
        graph.append({
            "@type": "FAQPage",
            "@id": f"{canonical}#faq",
            "mainEntity": [
                {"@type": "Question", "name": f["q"],
                 "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                for f in faqs
            ],
        })
    json_ld = {"@context": "https://schema.org", "@graph": graph}

    return {
        "page_title": page_title,
        "meta_description": meta_desc,
        "keywords": keywords,
        "canonical_url": canonical,
        "og_title": page_title,
        "og_description": meta_desc,
        "og_image": og_image,
        "og_url": canonical,
        "json_ld": json_ld,
    }


def _shape_for_card(d: Dict[str, Any]) -> Dict[str, Any]:
    """Compact shape for list / featured cards (smaller payload)."""
    return {
        "country_code": d.get("country_code"),
        "code": d.get("code"),
        "title": d.get("title"),
        "skill_level": d.get("skill_level"),
        "teer_category": d.get("teer_category"),
        "nz_green_list_tier": d.get("nz_green_list_tier"),
        "hierarchy": (d.get("hierarchy") or {}).get("unit_group_name"),
        "verified": (d.get("status") or "") == "verified",
    }


# ─── Featured ───────────────────────────────────────────────────────────────
@router.get("/featured")
async def get_featured():
    """Return ~12 hero cards for the public /atlas landing page (no auth)."""
    items: List[Dict[str, Any]] = []
    for country, code, _ in FEATURED_CODES:
        d = await db["occupation_master"].find_one(
            {"country_code": country, "code": code},
            {"_id": 0},
        )
        if d:
            items.append(_shape_for_card(d))
    return {
        "items": items,
        "countries": [
            {"code": "AU", **_country_meta("AU"), "total": await db["occupation_master"].count_documents({"country_code": "AU", "status": "verified"})},
            {"code": "CA", **_country_meta("CA"), "total": await db["occupation_master"].count_documents({"country_code": "CA", "status": "verified"})},
            {"code": "NZ", **_country_meta("NZ"), "total": await db["occupation_master"].count_documents({"country_code": "NZ", "status": "verified"})},
        ],
        "seo": {
            "page_title": "Migration Atlas — Australia, Canada & New Zealand Occupation Guide | LEAMSS",
            "meta_description": "Free migration occupation atlas covering ANZSCO + NOC codes. Visa pathways, eligibility, salary trends for AU, CA, NZ. Verified by licensed migration experts.",
            "keywords": "migration atlas, ANZSCO occupation list, NOC code list, Australia occupation codes, Canada NOC 2021, New Zealand Green List, skilled occupation list, visa pathways AU CA NZ, immigration consultant India, LEAMSS",
            "canonical_url": f"{_public_site_url()}/atlas",
            "og_url": f"{_public_site_url()}/atlas",
            "og_image": LOGO_IMG,
            "json_ld": {
                "@context": "https://schema.org",
                "@graph": [
                    _org_node(),
                    {
                        "@type": "CollectionPage",
                        "name": "Migration Atlas — AU, CA, NZ Occupation Guide",
                        "url": f"{_public_site_url()}/atlas",
                        "isPartOf": {"@id": "https://www.leamss.com/#organization"},
                    },
                ],
            },
        },
    }




# ─── Phase 19.4d — AU State pages (must come before /{country}/{code} catch-all) ───
def _slug_to_state_code(slug: str) -> Optional[str]:
    """Resolve a URL slug to a state code (case-insensitive)."""
    return {
        "new-south-wales": "NSW", "nsw": "NSW",
        "victoria": "VIC", "vic": "VIC",
        "queensland": "QLD", "qld": "QLD",
        "south-australia": "SA", "sa": "SA",
        "western-australia": "WA", "wa": "WA",
        "tasmania": "TAS", "tas": "TAS",
        "northern-territory": "NT", "nt": "NT",
        "australian-capital-territory": "ACT", "act": "ACT",
    }.get((slug or "").lower())


@router.get("/AU/states")
async def list_au_states():
    """Summary list of 8 AU states — used by hub page Browse-by-State section."""
    items = []
    async for s in db["au_states_master"].find({}, {"_id": 0}).sort("state_code", 1):
        items.append({
            "state_code": s.get("state_code"),
            "state_name": s.get("state_name"),
            "slug": s.get("slug"),
            "capital_city": s.get("capital_city"),
            "population": s.get("population"),
            "tagline": s.get("tagline"),
            "immigration_friendly_score": s.get("immigration_friendly_score"),
            "monthly_ads": (s.get("vacancy_data") or {}).get("monthly_ads"),
            "primary_visa_subclasses": s.get("primary_visa_subclasses"),
        })
    return {"country": "AU", "items": items, "total": len(items)}


@router.get("/AU/state/{state_code_or_slug}")
async def get_au_state(state_code_or_slug: str):
    """Return full state page payload for SSR or React renderer."""
    raw = (state_code_or_slug or "").strip()
    code = raw.upper() if len(raw) <= 3 else _slug_to_state_code(raw)
    if not code:
        code = _slug_to_state_code(raw)
    if not code:
        raise HTTPException(404, "Unknown state code or slug")
    state = await db["au_states_master"].find_one({"state_code": code}, {"_id": 0})
    if not state:
        raise HTTPException(404, f"State {code} not seeded — admin run /api/admin/au-states/seed")
    return {"country": "AU", "state": state}


# ─── Country list ───────────────────────────────────────────────────────────
@router.get("/{country}/list")
async def list_country(
    country: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, max_length=80),
    verified_only: bool = Query(True),
):
    country = _code_path_country(country)
    if country not in {"AU", "CA", "NZ"}:
        raise HTTPException(404, "Unknown country")

    match: Dict[str, Any] = {"country_code": country}
    if verified_only:
        match["status"] = "verified"
    if search:
        # Escape regex special chars
        s = re.escape(search.strip())
        match["$or"] = [
            {"code": {"$regex": s, "$options": "i"}},
            {"title": {"$regex": s, "$options": "i"}},
        ]

    total = await db["occupation_master"].count_documents(match)
    proj = {"_id": 0, "code": 1, "title": 1, "country_code": 1, "skill_level": 1,
            "teer_category": 1, "nz_green_list_tier": 1, "hierarchy": 1, "status": 1}
    cursor = db["occupation_master"].find(match, proj).sort("code", 1).skip(offset).limit(limit)
    items = [_shape_for_card(d) async for d in cursor]

    cm = _country_meta(country)
    return {
        "country": country,
        "country_meta": cm,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
        "seo": {
            "page_title": f"{cm['name']} Occupation Atlas — Browse {total} Verified Codes | LEAMSS",
            "meta_description": (
                f"Browse {total} verified {cm['classification']} occupations for {cm['name']} migration. "
                f"Visa pathways, salary band, assessing authority for each code."
            ),
            "keywords": (
                f"{cm['name']} occupation list, {cm['classification']} codes, {cm['name']} skilled occupation list, "
                f"{cm['name']} PR visa, {cm['name']} migration, immigration consultant India, LEAMSS"
            ),
            "canonical_url": f"{_public_site_url()}/atlas/{country.lower()}",
            "og_url": f"{_public_site_url()}/atlas/{country.lower()}",
            "og_image": LOGO_IMG,
            "json_ld": {
                "@context": "https://schema.org",
                "@graph": [
                    _org_node(),
                    {
                        "@type": "BreadcrumbList",
                        "itemListElement": [
                            {"@type": "ListItem", "position": 1, "name": "Atlas", "item": f"{_public_site_url()}/atlas"},
                            {"@type": "ListItem", "position": 2, "name": cm["name"], "item": f"{_public_site_url()}/atlas/{country.lower()}"},
                        ],
                    },
                ],
            },
        },
    }


# ─── Single occupation ──────────────────────────────────────────────────────
@router.get("/{country}/{code}")
async def get_single_occupation(country: str, code: str):
    country = _code_path_country(country)
    if country not in {"AU", "CA", "NZ"}:
        raise HTTPException(404, "Unknown country")
    # Sanity on code format
    if not re.match(r"^\d{5,6}$", code):
        raise HTTPException(400, "Invalid code format")

    d = await db["occupation_master"].find_one(
        {"country_code": country, "code": code, "status": "verified"},
        {"_id": 0},
    )
    if not d:
        raise HTTPException(404, "Occupation not found or not yet verified")

    # Phase 19.7 — resolve assessing_authority via FK + overrides (back-compat shape)
    from services.authority_resolver import resolve_authority
    d["assessing_authority"] = await resolve_authority(db, d)

    cm = _country_meta(country)
    safe = _safe_doc(d)
    faqs = _build_occupation_faqs(country, d, cm)

    # Similar codes — same minor_group (3 chars) or major_group (1-2 chars)
    same_minor = (d.get("hierarchy") or {}).get("minor_group") or code[:3]
    similar_cursor = db["occupation_master"].find(
        {
            "country_code": country, "status": "verified",
            "code": {"$ne": code},
            "$or": [
                {"hierarchy.minor_group": same_minor},
                {"code": {"$regex": f"^{code[:2]}"}},
            ],
        },
        {"_id": 0, "code": 1, "title": 1, "country_code": 1, "skill_level": 1,
         "teer_category": 1, "nz_green_list_tier": 1, "hierarchy": 1, "status": 1},
    ).limit(6)
    similar = [_shape_for_card(s) async for s in similar_cursor]

    # Cross-country: same code in other countries
    cross_country = []
    for other in [c for c in ["AU", "CA", "NZ"] if c != country]:
        match_code = code if other != "CA" else code[:5]  # CA NOCs are 5-digit
        other_doc = await db["occupation_master"].find_one(
            {"country_code": other, "code": match_code, "status": "verified"},
            {"_id": 0, "code": 1, "title": 1, "country_code": 1},
        )
        if other_doc:
            cross_country.append({
                "country_code": other,
                "code": other_doc["code"],
                "title": other_doc["title"],
                **_country_meta(other),
            })

    return {
        "country": country,
        "country_meta": cm,
        "occupation": safe,
        "similar": similar,
        "cross_country": cross_country,
        "faqs": faqs,
        "seo": _build_seo(country, d, faqs),
    }


# ─── Sitemap.xml ────────────────────────────────────────────────────────────
@router.get("/sitemap.xml")
async def sitemap_xml(response: Response):
    """Return XML sitemap with all verified occupation URLs."""
    base = _public_site_url()
    urls: List[str] = [f"{base}/atlas", f"{base}/atlas/au", f"{base}/atlas/ca", f"{base}/atlas/nz"]
    async for d in db["occupation_master"].find(
        {"status": "verified"},
        {"_id": 0, "code": 1, "country_code": 1},
    ):
        urls.append(f"{base}/atlas/{(d['country_code'] or '').lower()}/{d['code']}")

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml_lines.append(f"  <url><loc>{u}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>")
    xml_lines.append("</urlset>")
    xml = "\n".join(xml_lines)
    return Response(content=xml, media_type="application/xml")




# ─── Lead Capture (rate-limited + honeypot) ─────────────────────────────────
_IP_WINDOW_SECONDS = 60
_IP_MAX_REQUESTS = 15  # generous threshold; bots get blocked, real shared office IPs don't
_ip_log: Dict[str, deque] = {}


def _rate_limit(ip: str) -> bool:
    """Returns True if allowed, False if rate-limited."""
    now = time.time()
    q = _ip_log.setdefault(ip, deque())
    while q and now - q[0] > _IP_WINDOW_SECONDS:
        q.popleft()
    if len(q) >= _IP_MAX_REQUESTS:
        return False
    q.append(now)
    return True


class PublicLeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=24)
    country_of_interest: Optional[str] = None       # AU | CA | NZ
    atlas_code: Optional[str] = None
    atlas_title: Optional[str] = None
    message: Optional[str] = Field(default=None, max_length=600)
    # Honeypot — bots will fill this; humans won't see it.
    company_url: Optional[str] = Field(default=None, max_length=300)


@router.post("/lead")
async def submit_lead(request: Request, body: PublicLeadCreate = Body(...)):
    # Honeypot — if bot fills hidden field, silently 200 without writing.
    if body.company_url:
        return {"ok": True, "lead_id": "honeypot_dropped"}

    # Rate limit per IP
    ip = request.client.host if request.client else "unknown"
    if not _rate_limit(ip):
        raise HTTPException(429, "Too many requests. Please wait a minute before trying again.")

    now = datetime.now(timezone.utc)
    lead_id = str(uuid.uuid4())

    # Service inferred from country_of_interest
    coi = (body.country_of_interest or "").upper()
    service_map = {"AU": "Australia PR", "CA": "Canada PR", "NZ": "New Zealand PR"}
    service = service_map.get(coi, "Migration Eligibility Check")

    msg_parts = []
    if body.atlas_code and body.atlas_title:
        msg_parts.append(f"Interested in: {body.atlas_title} ({body.atlas_code})")
    if body.message:
        msg_parts.append(body.message.strip())

    doc = {
        "id": lead_id,
        "name": body.name.strip(),
        "email": body.email.lower(),
        "phone": body.phone.strip(),
        "service_interested": service,
        "country_of_interest": coi,
        "message": " · ".join(msg_parts),
        "source": "public_atlas",
        "atlas_code": body.atlas_code,
        "atlas_title": body.atlas_title,
        "utm_source": "", "utm_medium": "", "utm_campaign": "",
        "stage": "new",
        "assigned_to": None,
        "priority": "medium",
        "tags": ["public_atlas", f"atlas_{coi.lower()}"] if coi else ["public_atlas"],
        "notes": [],
        "ip_address": ip,
        "created_at": now,
        "updated_at": now,
        "last_contacted_at": None,
        "converted": False,
        "converted_sale_id": None,
    }
    await db["leads"].insert_one(doc)
    return {
        "ok": True,
        "lead_id": lead_id,
        "message": "Thank you! Our migration expert will contact you within 24 hours.",
    }
