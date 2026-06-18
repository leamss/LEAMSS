"""Phase 19 — SEO/SSG generator.

Static Site Generation for all public /atlas/* pages. Renders Jinja2 templates
using the same data the existing /api/public-atlas/{cc}/{code} endpoint
returns, then writes files to ``/app/frontend/public/atlas/...`` so the CRA
dev-server (and any production nginx) serves them file-first.

Triggered by:
  • Admin-verify hook (synchronous, ~80ms per call)
  • APScheduler nightly job at 03:00 UTC (safety-net full sweep)
  • Manual admin endpoint POST /api/seo-ssg/regenerate-all
"""
from __future__ import annotations
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/seo-ssg", tags=["SEO SSG"])

# Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BACKEND_DIR / "templates"
FRONTEND_PUBLIC = Path("/app/frontend/public")
ATLAS_OUT = FRONTEND_PUBLIC / "atlas"

# Status memo (in-process — admin /status endpoint reads from here)
_status: Dict[str, Any] = {
    "last_full_sweep_at": None,
    "last_full_sweep_duration_ms": None,
    "file_count": None,
    "sitemap_url_count": None,
    "errors": [],
}


# ─────────────────────────────────────────────────────────────────────────────
# Jinja env
# ─────────────────────────────────────────────────────────────────────────────
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _public_base() -> str:
    return os.environ.get("LEAMSS_PUBLIC_BASE_URL", "https://www.leamss.com").rstrip("/")


def _country_meta(cc: str) -> Dict[str, str]:
    cc = (cc or "").upper()
    return {
        "AU": {"flag": "🇦🇺", "name": "Australia", "classification": "ANZSCO", "currency": "AUD"},
        "CA": {"flag": "🇨🇦", "name": "Canada", "classification": "NOC", "currency": "CAD"},
        "NZ": {"flag": "🇳🇿", "name": "New Zealand", "classification": "ANZSCO", "currency": "NZD"},
    }.get(cc, {"flag": "🌐", "name": cc, "classification": "Code", "currency": ""})


# Phase 19.1a — Country landmark hero images (Unsplash CDN, matches V2 React).
def _hero_image(cc: str) -> str:
    cc = (cc or "").upper()
    return {
        "AU": "https://images.unsplash.com/photo-1753275032483-d13bd056f4da?crop=entropy&cs=srgb&fm=jpg&w=1920&q=78&auto=format",
        "CA": "https://images.unsplash.com/photo-1517935706615-2717063c2225?crop=entropy&cs=srgb&fm=jpg&w=1920&q=78&auto=format",
        "NZ": "https://images.unsplash.com/photo-1677557769726-565a3034fa2c?crop=entropy&cs=srgb&fm=jpg&w=1920&q=78&auto=format",
    }.get(cc, "")


# Phase 19.1a — Per-country skill-level breakdown (for hub + country pages).
async def _skill_level_breakdown(cc: str) -> List[Dict[str, Any]]:
    cc = (cc or "").upper()
    pipeline = [
        {"$match": {"country_code": cc, "status": "verified", "skill_level": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$skill_level", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    out: List[Dict[str, Any]] = []
    async for row in db["occupation_master"].aggregate(pipeline):
        lvl = row.get("_id")
        cnt = row.get("count", 0)
        if lvl is None or cnt <= 0:
            continue
        try:
            lvl_int = int(lvl)
        except (TypeError, ValueError):
            continue
        out.append({"level": lvl_int, "count": cnt})
    return out


# Phase 19.1a — Visa pathway chips for occupation template.
def _build_visa_pathway_chips(occ: Dict[str, Any], recommended: Optional[str]) -> List[Dict[str, Any]]:
    chips: List[Dict[str, Any]] = []
    pw = (occ.get("visa_pathways") or {})
    for v in (pw.get("visa_eligibility") or []):
        sub = v.get("visa_subclass")
        if not sub:
            continue
        eligible = bool(v.get("eligible"))
        cls = "ineligible"
        if recommended and str(sub) == str(recommended):
            cls = "recommended"
        elif eligible:
            cls = "eligible"
        chips.append({"subclass": sub, "cls": cls, "notes": v.get("notes") or ""})
    return chips


def _pathway_list_pills(occ: Dict[str, Any]) -> List[str]:
    """Split `pathway_list` like 'MLTSSL;CSOL' into individual pills."""
    pls = (occ.get("visa_pathways") or {}).get("pathway_lists") or []
    out: List[str] = []
    if isinstance(pls, list):
        for entry in pls:
            for token in str(entry).replace(",", ";").split(";"):
                t = token.strip()
                if t and t not in out:
                    out.append(t)
    raw_pl = occ.get("pathway_list")
    if raw_pl:
        for token in str(raw_pl).replace(",", ";").split(";"):
            t = token.strip()
            if t and t not in out:
                out.append(t)
    return out


def _days_since(dt: Any) -> Optional[int]:
    if not dt:
        return None
    try:
        if isinstance(dt, str):
            t = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        else:
            t = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - t).days)
    except Exception:  # noqa: BLE001
        return None


def _verification_tone(days: Optional[int]) -> str:
    if days is None:
        return "slate"
    if days <= 30:
        return "emerald"
    if days <= 90:
        return "amber"
    return "rose"


# ─────────────────────────────────────────────────────────────────────────────
# Data loaders (mirror /api/public-atlas/{cc}/{code} but pure DB, no HTTP)
# ─────────────────────────────────────────────────────────────────────────────
async def _load_occupation_for_ssg(cc: str, code: str) -> Optional[Dict[str, Any]]:
    cc = (cc or "").upper()
    return await db["occupation_master"].find_one(
        {"country_code": cc, "code": str(code), "status": "verified"},
        {"_id": 0},
    )


def _build_occupation_jsonld(occ: Dict[str, Any], country: Dict[str, str], base_url: str, page_url: str) -> Dict[str, Any]:
    """Full Schema.org Occupation JSON-LD (Sir's default #3 — extended beyond Phase 16.6)."""
    aa = occ.get("assessing_authority") or {}
    cc = occ["country_code"]
    code = occ["code"]
    title = occ.get("title") or "Occupation"
    desc = occ.get("description") or ""
    typical_tasks = occ.get("typical_tasks") or []
    qual = occ.get("qualification_rules") or ""

    occupation_node: Dict[str, Any] = {
        "@type": "Occupation",
        "name": title,
        "occupationLocation": {"@type": "Country", "name": country["name"]},
        "description": (desc or f"{title} — {country['classification']} code {code}.")[:600],
        "estimatedSalary": {
            "@type": "MonetaryAmountDistribution",
            "name": "Indicative annual salary",
            "currency": country.get("currency", "AUD"),
        },
        "qualifications": qual[:1000] if qual else f"{country['classification']} skills assessment by {aa.get('name', 'designated authority')}",
        "responsibilities": ". ".join(t for t in typical_tasks[:8] if t) or f"Performs duties of {title}.",
        "url": page_url,
    }
    if aa.get("name"):
        occupation_node["skills"] = aa.get("name")

    breadcrumb = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{base_url}/"},
            {"@type": "ListItem", "position": 2, "name": "Migration Atlas", "item": f"{base_url}/atlas"},
            {"@type": "ListItem", "position": 3, "name": country["name"], "item": f"{base_url}/atlas/{cc.lower()}"},
            {"@type": "ListItem", "position": 4, "name": f"{title} ({code})", "item": page_url},
        ],
    }

    organization = {
        "@type": "Organization",
        "name": "LEAMSS",
        "alternateName": "Ladhani Education & Migration Services",
        "url": base_url,
        "logo": f"{base_url}/leamss-logo.png",
    }
    website = {
        "@type": "WebSite",
        "url": base_url,
        "name": "LEAMSS",
    }
    return {"@context": "https://schema.org", "@graph": [organization, website, occupation_node, breadcrumb]}


def _build_faqpage_jsonld(faqs: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    if not faqs:
        return None
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f.get("q") or f.get("question") or "", "acceptedAnswer": {"@type": "Answer", "text": f.get("a") or f.get("answer") or ""}}
            for f in faqs[:10] if (f.get("q") or f.get("question"))
        ],
    }


def _build_seo_dict(occ: Dict[str, Any], country: Dict[str, str], page_url: str) -> Dict[str, Any]:
    title_short = occ.get("title") or "Occupation"
    code = occ.get("code")
    desc = occ.get("description") or ""
    short_desc = (desc[:250] + "…") if len(desc) > 260 else desc
    if not short_desc:
        short_desc = f"{title_short} — {country['classification']} code {code} migration pathway to {country['name']}. Verified by LEAMSS — Ladhani Education & Migration Services."

    return {
        "page_title": f"{title_short} ({country['classification']} {code}) — {country['name']} Migration Pathway | LEAMSS",
        "meta_description": short_desc,
        "og_title": f"{title_short} — {country['name']} Migration Pathway",
        "og_description": short_desc,
        "canonical_url": page_url,
    }


def _generate_faqs(occ: Dict[str, Any], country: Dict[str, str]) -> List[Dict[str, str]]:
    """Reuses the Phase 16.6 FAQ generation pattern — kept simple inline so SSG
    has no runtime dependency on the public_atlas router."""
    code = occ["code"]
    title = occ.get("title") or "this occupation"
    aa = (occ.get("assessing_authority") or {}).get("name") or "the designated authority"
    rec_visa = ""
    rvs = occ.get("recommended_visa_subclass") or {}
    if isinstance(rvs, dict):
        rec_visa = rvs.get(country["name"][:2].upper(), "") or rvs.get(occ.get("country_code", "").upper(), "")
    pt = (occ.get("assessing_authority") or {}).get("processing_time_weeks")

    out: List[Dict[str, str]] = []
    out.append({"question": f"How long does {country['classification']} {code} assessment take?", "answer": f"{aa} typically processes {title} assessments in {pt or '8–16'} weeks once all documents are submitted."})
    out.append({"question": f"Which visa is recommended for {title} in {country['name']}?", "answer": (f"The recommended visa subclass for {title} in {country['name']} is {rec_visa}." if rec_visa else f"Multiple visa pathways are available depending on points score, age, and English ability.")})
    out.append({"question": f"What documents are required for {title}?", "answer": f"Identity proof, qualifications (degree + transcripts), employment evidence (references + payslips), English test, and {aa}-specific forms. LEAMSS provides a personalised checklist."})
    out.append({"question": f"Is {title} on the skilled occupation list?", "answer": f"{title} ({code}) is currently a verified occupation on the {country['name']} skilled migration atlas as of the date shown above."})
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Render
# ─────────────────────────────────────────────────────────────────────────────
async def render_occupation_html(country_code: str, code: str) -> Optional[str]:
    occ = await _load_occupation_for_ssg(country_code, code)
    if not occ:
        return None
    cc = country_code.upper()
    country = _country_meta(cc)
    base = _public_base()
    page_url = f"{base}/atlas/{cc.lower()}/{code}"
    seo = _build_seo_dict(occ, country, page_url)
    verified_at = (occ.get("verification") or {}).get("verified_at") or occ.get("last_reviewed_at")
    days = _days_since(verified_at)
    tone = _verification_tone(days)

    # Similar occupations (same anzsco_4digit_code if present)
    similar: List[Dict[str, Any]] = []
    grp = occ.get("anzsco_4digit_code") or occ.get("anzsco_major_group_code")
    if grp:
        async for s in db["occupation_master"].find(
            {"country_code": cc, "anzsco_4digit_code": grp, "status": "verified", "code": {"$ne": occ["code"]}},
            {"_id": 0, "code": 1, "title": 1},
        ).limit(6):
            similar.append(s)

    faqs = _generate_faqs(occ, country)
    jsonld = _build_occupation_jsonld(occ, country, base, page_url)
    faq_jsonld = _build_faqpage_jsonld(faqs)

    visa_pw = occ.get("visa_pathways") or {}
    eligible_visas = [v.get("visa_subclass") for v in (visa_pw.get("visa_eligibility") or []) if v.get("eligible") and v.get("visa_subclass")]
    rvs = occ.get("recommended_visa_subclass") or {}
    rec_visa = rvs.get(cc) if isinstance(rvs, dict) else None

    visa_pathway_chips = _build_visa_pathway_chips(occ, rec_visa)
    pathway_list_pills = _pathway_list_pills(occ)

    # Phase 19.4 — Top 5 SA4 regions with "Strong" rating (AU only, country-wide)
    strong_regions: List[Dict[str, Any]] = []
    if cc == "AU":
        async for r in db["regional_labour_market"].find(
            {"rating": "Strong"}, {"_id": 0}
        ).limit(5):
            strong_regions.append(r)

    tmpl = _env.get_template("atlas_occupation_ssr.html")
    return tmpl.render(
        occ=occ,
        country=country,
        country_code=cc,
        country_code_lower=cc.lower(),
        page_url=page_url,
        base_url=base,
        seo=seo,
        days_since_verified=days,
        verification_tone=tone,
        verified_at_human=(verified_at.strftime("%d %b %Y") if hasattr(verified_at, "strftime") else (str(verified_at)[:10] if verified_at else "")),
        similar=similar,
        faqs=faqs,
        jsonld=jsonld,
        faq_jsonld=faq_jsonld,
        eligible_visas=eligible_visas,
        recommended_visa=rec_visa,
        visa_pathway_chips=visa_pathway_chips,
        pathway_list_pills=pathway_list_pills,
        hero_image=_hero_image(cc),
        og_image=f"{base}/leamss-logo.png",
        now_iso=datetime.now(timezone.utc).isoformat(),
        strong_regions=strong_regions,
    )


async def render_country_index_html(country_code: str) -> str:
    cc = country_code.upper()
    country = _country_meta(cc)
    base = _public_base()
    page_url = f"{base}/atlas/{cc.lower()}"

    top: List[Dict[str, Any]] = []
    async for o in db["occupation_master"].find(
        {"country_code": cc, "status": "verified"},
        {"_id": 0, "code": 1, "title": 1, "assessing_authority": 1,
         "recommended_visa_subclass": 1, "anzsco_major_group_code": 1,
         "skill_level": 1, "teer_category": 1,
         "abs_data": 1, "jsa_data": 1},
    ).sort("code", 1).limit(50):
        # Flatten recommended_visa to a single string for the template
        rvs = o.get("recommended_visa_subclass") or {}
        if isinstance(rvs, dict):
            o["recommended_visa"] = rvs.get(cc) or ""
        else:
            o["recommended_visa"] = ""
        # Phase 19.3 — surface assessing-authority fee + proc time on cards
        aa = o.get("assessing_authority") or {}
        o["aa_fee"] = aa.get("fee_native")
        o["aa_currency"] = aa.get("fee_currency")
        o["aa_proc_weeks"] = aa.get("processing_time_weeks")
        # Phase 19.4 — surface salary + growth on country index cards
        abs_d = o.get("abs_data") or {}
        jsa_d = o.get("jsa_data") or {}
        annual = abs_d.get("median_ft_annual_aud")
        if annual:
            o["salary_chip"] = f"${round(annual / 1000)}k/yr"
        else:
            o["salary_chip"] = None
        o["growth_chip"] = jsa_d.get("future_growth") if jsa_d.get("future_growth") not in (None, "Unknown") else None
        top.append(o)
    total = await db["occupation_master"].count_documents({"country_code": cc, "status": "verified"})
    skill_breakdown = await _skill_level_breakdown(cc)

    tmpl = _env.get_template("atlas_country_ssr.html")
    return tmpl.render(
        country=country, country_code=cc, country_code_lower=cc.lower(),
        page_url=page_url, base_url=base, top=top, total=total,
        skill_level_breakdown=skill_breakdown,
        hero_image=_hero_image(cc),
        og_image=f"{base}/leamss-logo.png",
        now_iso=datetime.now(timezone.utc).isoformat(),
    )


async def render_atlas_hub_html() -> str:
    base = _public_base()
    page_url = f"{base}/atlas"

    countries = []
    for cc in ("AU", "CA", "NZ"):
        n = await db["occupation_master"].count_documents({"country_code": cc, "status": "verified"})
        meta = _country_meta(cc)
        skill_breakdown = await _skill_level_breakdown(cc)
        countries.append({
            "code": cc, "code_lower": cc.lower(),
            "name": meta["name"], "flag": meta["flag"],
            "classification": meta["classification"], "count": n,
            "skill_level_breakdown": skill_breakdown,
            "hero_image": _hero_image(cc),
        })

    tmpl = _env.get_template("atlas_hub_ssr.html")
    return tmpl.render(
        countries=countries, page_url=page_url, base_url=base,
        og_image=f"{base}/leamss-logo.png",
        now_iso=datetime.now(timezone.utc).isoformat(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# File writers
# ─────────────────────────────────────────────────────────────────────────────
def _write_file(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


async def regenerate_one(country_code: str, code: str) -> Optional[str]:
    cc = country_code.upper()
    html = await render_occupation_html(cc, str(code))
    if not html:
        return None
    target = ATLAS_OUT / cc.lower() / str(code) / "index.html"
    _write_file(target, html)
    return str(target)


async def regenerate_country_index(country_code: str) -> str:
    cc = country_code.upper()
    html = await render_country_index_html(cc)
    target = ATLAS_OUT / cc.lower() / "index.html"
    _write_file(target, html)
    return str(target)


async def regenerate_atlas_hub() -> str:
    html = await render_atlas_hub_html()
    target = ATLAS_OUT / "index.html"
    _write_file(target, html)
    return str(target)


async def prune_unverified_files() -> Dict[str, Any]:
    """Walk written files; delete any that no longer have a verified record."""
    if not ATLAS_OUT.exists():
        return {"deleted": 0}
    verified_codes: set = set()
    async for d in db["occupation_master"].find({"status": "verified"}, {"_id": 0, "country_code": 1, "code": 1}):
        verified_codes.add((str(d.get("country_code", "")).lower(), str(d.get("code", ""))))
    deleted = 0
    for cc_dir in ATLAS_OUT.iterdir():
        if not cc_dir.is_dir():
            continue
        if cc_dir.name in ("index.html",):
            continue
        for code_dir in cc_dir.iterdir():
            if not code_dir.is_dir():
                continue
            if (cc_dir.name, code_dir.name) not in verified_codes:
                try:
                    shutil.rmtree(code_dir)
                    deleted += 1
                except Exception:  # noqa: BLE001
                    pass
    return {"deleted": deleted}


async def regenerate_sitemap() -> Dict[str, Any]:
    base = _public_base()
    urls: List[Dict[str, Any]] = []
    urls.append({"loc": f"{base}/", "priority": "1.0", "changefreq": "weekly"})
    urls.append({"loc": f"{base}/start", "priority": "1.0", "changefreq": "weekly"})
    urls.append({"loc": f"{base}/atlas", "priority": "0.9", "changefreq": "weekly"})
    for cc in ("AU", "CA", "NZ"):
        urls.append({"loc": f"{base}/atlas/{cc.lower()}", "priority": "0.8", "changefreq": "weekly"})

    async for d in db["occupation_master"].find(
        {"status": "verified"},
        {"_id": 0, "country_code": 1, "code": 1, "updated_at": 1},
    ).sort("country_code", 1):
        cc = (d.get("country_code") or "").lower()
        code = d.get("code")
        if not cc or not code:
            continue
        lastmod = d.get("updated_at")
        if hasattr(lastmod, "strftime"):
            lastmod_str = lastmod.strftime("%Y-%m-%d")
        else:
            lastmod_str = (str(lastmod)[:10] if lastmod else None)
        u: Dict[str, Any] = {"loc": f"{base}/atlas/{cc}/{code}", "priority": "0.7", "changefreq": "weekly"}
        if lastmod_str:
            u["lastmod"] = lastmod_str
        urls.append(u)

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        line = f'  <url><loc>{u["loc"]}</loc>'
        if "lastmod" in u:
            line += f"<lastmod>{u['lastmod']}</lastmod>"
        line += f"<changefreq>{u['changefreq']}</changefreq><priority>{u['priority']}</priority></url>"
        xml_lines.append(line)
    xml_lines.append("</urlset>")
    xml = "\n".join(xml_lines)
    _write_file(FRONTEND_PUBLIC / "sitemap.xml", xml)
    return {"url_count": len(urls), "path": str(FRONTEND_PUBLIC / "sitemap.xml")}


async def regenerate_all() -> Dict[str, Any]:
    start = datetime.now(timezone.utc)
    written = 0
    errors: List[Dict[str, Any]] = []
    # 1. Hub
    try:
        await regenerate_atlas_hub()
    except Exception as e:  # noqa: BLE001
        errors.append({"path": "/atlas", "error": str(e)[:200]})
    # 2. Country indexes
    for cc in ("AU", "CA", "NZ"):
        try:
            await regenerate_country_index(cc)
        except Exception as e:  # noqa: BLE001
            errors.append({"path": f"/atlas/{cc}", "error": str(e)[:200]})
    # 3. All verified occupations
    async for d in db["occupation_master"].find(
        {"status": "verified"},
        {"_id": 0, "country_code": 1, "code": 1},
    ):
        try:
            cc = d.get("country_code")
            code = d.get("code")
            if not cc or not code:
                continue
            r = await regenerate_one(cc, str(code))
            if r:
                written += 1
        except Exception as e:  # noqa: BLE001
            errors.append({"path": f"/atlas/{d.get('country_code')}/{d.get('code')}", "error": str(e)[:200]})
    # 4. Sitemap
    sitemap = await regenerate_sitemap()
    # 5. Prune (don't fail full sweep on prune errors)
    try:
        await prune_unverified_files()
    except Exception:  # noqa: BLE001
        pass
    end = datetime.now(timezone.utc)
    duration_ms = int((end - start).total_seconds() * 1000)
    _status["last_full_sweep_at"] = end.isoformat()
    _status["last_full_sweep_duration_ms"] = duration_ms
    _status["file_count"] = written + 4  # +hub +3 country
    _status["sitemap_url_count"] = sitemap["url_count"]
    _status["errors"] = errors[:20]
    return {
        "started_at": start.isoformat(),
        "finished_at": end.isoformat(),
        "duration_ms": duration_ms,
        "occupations_written": written,
        "country_indexes_written": 3,
        "hub_written": 1,
        "sitemap": sitemap,
        "errors": errors[:20],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Admin endpoints
# ─────────────────────────────────────────────────────────────────────────────
def _is_admin(user: dict) -> bool:
    role = (user.get("rbac_role") or user.get("role") or "").lower()
    return role in {"admin", "admin_owner"}


class RegenOneBody(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=4)
    code: str = Field(..., min_length=1, max_length=20)


@router.post("/regenerate-all")
async def admin_regen_all(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    return await regenerate_all()


@router.post("/regenerate-one")
async def admin_regen_one(body: RegenOneBody, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    path = await regenerate_one(body.country_code, body.code)
    if not path:
        raise HTTPException(status_code=404, detail="Occupation not found or not verified")
    return {"path": path, "ok": True}


@router.post("/prune")
async def admin_prune(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    return await prune_unverified_files()


@router.get("/status")
async def admin_status(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    return dict(_status)


# ─────────────────────────────────────────────────────────────────────────────
# Best-effort hook called from the admin /verify endpoint
# ─────────────────────────────────────────────────────────────────────────────
async def on_verified_hook(country_code: str, code: str) -> None:
    """Synchronous-safe regen call from the verify endpoint. Swallows errors
    (must not block verify). Reports failures to ``client_errors`` for ops.
    """
    try:
        await regenerate_one(country_code, code)
        # country index is cheap; rebuild it too so the country page lists this freshly-verified record
        await regenerate_country_index(country_code)
        # sitemap is also rebuilt (cheap, keeps lastmod tied to verify timestamp)
        await regenerate_sitemap()
    except Exception as e:  # noqa: BLE001
        try:
            await db["client_errors"].insert_one({
                "id": f"ssg-{country_code}-{code}-{datetime.now(timezone.utc).timestamp()}",
                "user_id": "ssg-hook",
                "user_role": "system",
                "user_email": "system",
                "message": f"SSG regen failed for {country_code}/{code}: {str(e)[:200]}",
                "stack": "",
                "componentStack": "",
                "route": f"/atlas/{country_code}/{code}",
                "scope": "ssg",
                "user_agent": "ssg/hook",
                "received_at": datetime.now(timezone.utc),
                "occurrence_count": 1,
                "resolved": False,
                "is_synthetic": False,
            })
        except Exception:  # noqa: BLE001
            pass
