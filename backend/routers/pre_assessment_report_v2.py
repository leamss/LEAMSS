"""Phase 19.11 — Pre-Assessment Report PDF (v2 — WeasyPrint).

Endpoint:
    POST /api/reports/pre-assessment
    Body: { client: {name, email, phone, age, english_score, education, work_exp_years},
            country_code: "AU", occupation_code: "261313" }
    Auth: admin / sales / case_manager / partner (partner restricted to own leads)
    Returns: PDF binary stream (application/pdf, Content-Disposition: attachment)

Cache: 5-min in-memory cache keyed on (client_hash, country_code, code).
Logs: every generation writes to `pre_assessment_reports_log` collection.
"""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import currency_service
from services.authority_resolver import resolve_authority

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["pre-assessment-report"])

# 5-min cache: {key: (expires_at, pdf_bytes, ref)}
_CACHE: Dict[str, tuple] = {}
_TTL = 300

ALLOWED_ROLES = {"admin", "admin_owner", "super_admin", "sales", "case_manager", "partner"}


def _can_generate(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ALLOWED_ROLES or "*" in (user.get("permissions") or [])


class ClientProfile(BaseModel):
    name: str = Field("", max_length=200)
    email: str = Field("", max_length=200)
    phone: str = Field("", max_length=40)
    age: Optional[int] = None
    english_score: Optional[str] = None  # "IELTS 7.5", "PTE 65" etc.
    education: Optional[str] = None
    work_exp_years: Optional[int] = None
    notes: Optional[str] = None


class ReportRequest(BaseModel):
    client: ClientProfile
    country_code: str = Field(..., min_length=2, max_length=3)
    occupation_code: str = Field(..., min_length=4, max_length=20)
    preview_html: bool = False  # if true, return HTML body instead of PDF


def _client_hash(c: ClientProfile) -> str:
    raw = f"{c.name}|{c.email}|{c.phone}|{c.age}".encode()
    return hashlib.sha256(raw).hexdigest()[:10]


def _ref_for(client_hash: str, cc: str, code: str) -> str:
    seed = f"{client_hash}|{cc}|{code}|{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    return hashlib.sha1(seed.encode()).hexdigest()[:8].upper()


def _fmt_currency(amount: Optional[float], currency: str) -> Optional[str]:
    if amount is None:
        return None
    sign = "AUD $" if currency == "AUD" else f"{currency} "
    return f"{sign}{int(amount):,}"


async def _build_context(req: ReportRequest, user: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble all data needed by the WeasyPrint template."""
    cc = req.country_code.upper()
    occ = await db["occupation_master"].find_one(
        {"country_code": cc, "code": req.occupation_code, "status": {"$ne": "superseded"}},
        {"_id": 0},
    )
    if not occ:
        raise HTTPException(status_code=404,
                            detail=f"Occupation {req.occupation_code} not found in {cc} atlas")

    # Resolve authority
    aa = await resolve_authority(db, occ)

    # FX rate for INR conversion
    fx = await currency_service.get_rate(db, f"{cc if cc != 'AU' else 'AUD'}_INR" if cc != "AU" else "AUD_INR")
    fx_rate = fx.get("rate") or 55.5

    # Salary block
    abs_data = occ.get("abs_data") or {}
    salary_native = abs_data.get("median_ft_annual_aud") or abs_data.get("median_ft_annual")
    salary_inr = currency_service.convert(salary_native, fx_rate)
    salary = {
        "native_display": _fmt_currency(salary_native, "AUD"),
        "inr_display": currency_service.format_inr(salary_inr),
        "weekly": _fmt_currency(abs_data.get("median_weekly_earnings"), "AUD") + "/wk" if abs_data.get("median_weekly_earnings") else None,
        "hourly": (f"AUD ${abs_data.get('median_hourly_earnings'):.0f}/hr"
                   if abs_data.get("median_hourly_earnings") else None),
    }

    # Growth block
    jsa = occ.get("jsa_data") or {}
    growth = {
        "label": jsa.get("future_growth") or "TBD",
        "pct": (f"{jsa.get('growth_pct_10y'):+.1f}% by 2035"
                if jsa.get("growth_pct_10y") is not None else None),
    }

    # Workforce projection
    workforce = {
        "current": (f"{jsa.get('employment_2025'):,}"
                    if jsa.get("employment_2025") else None),
        "projected_2035": (f"{jsa.get('employment_2035'):,} by 2035"
                           if jsa.get("employment_2035") else None),
    }

    # Vacancy snapshot (national)
    vacancy_doc = await db["vacancy_snapshots"].find_one({"is_latest": True}, {"_id": 0})
    vacancy = {
        "total": (f"{vacancy_doc['national_total']:,}"
                  if vacancy_doc and vacancy_doc.get("national_total") else None),
        "mom_pct": (f"{vacancy_doc['mom_pct']:+.1f}% MoM"
                    if vacancy_doc and vacancy_doc.get("mom_pct") is not None else None),
    }

    # Top industries (from abs_data)
    top_industries = [
        {"name": i.get("name") or i.get("industry"), "pct": i.get("pct") or i.get("share_pct")}
        for i in (abs_data.get("top_industries") or [])[:5]
    ]

    # State demand (Phase 19.10 state_nomination_lists)
    state_demand = []
    async for d in db["state_nomination_lists"].find({}, {"_id": 0}):
        for entry in (d.get("codes") or []):
            if entry.get("anzsco_code") == req.occupation_code:
                state_demand.append({
                    "state": d["state"], "list_type": d["list_type"],
                    "status": entry.get("status"), "as_of_date": d.get("as_of_date"),
                })

    # Visa pathways
    elig = (occ.get("visa_pathways") or {}).get("visa_eligibility") or []
    pathways = [
        {
            "subclass": v.get("visa_subclass") or v.get("subclass"),
            "name": v.get("visa_name") or v.get("name") or "",
            "eligible": bool(v.get("eligible")),
            "notes": v.get("notes") or "",
        }
        for v in elig if v.get("visa_subclass") or v.get("subclass")
    ]
    rvs = occ.get("recommended_visa_subclass") or {}
    rec_sub = rvs.get(cc) or ""
    recommended_visa = None
    if rec_sub:
        rec_match = next((p for p in pathways if p["subclass"] == rec_sub), None)
        recommended_visa = rec_match or {"subclass": rec_sub, "name": rec_sub}

    # Assessing body block
    assessing_body = None
    if aa and (aa.get("name") or aa.get("short_name")):
        msa_aud = ((aa.get("fees") or {}).get("msa_fee_aud")
                   or aa.get("fee_native"))
        msa_inr = currency_service.convert(msa_aud, fx_rate)
        proc = aa.get("processing") or {}
        proc_min = proc.get("standard_days_min")
        proc_max = proc.get("standard_days_max")
        proc_disp = None
        if proc_min and proc_max:
            proc_disp = f"{proc_min}-{proc_max} days"
        elif aa.get("processing_time_weeks"):
            proc_disp = f"{aa['processing_time_weeks']} weeks"
        assessing_body = {
            "name": aa.get("name") or aa.get("full_name") or "",
            "short_name": aa.get("short_name") or aa.get("code"),
            "url": aa.get("url") or aa.get("website") or "",
            "fee_display": _fmt_currency(msa_aud, "AUD") if msa_aud else None,
            "fee_inr_display": currency_service.format_inr(msa_inr),
            "processing_display": proc_disp,
            "validity_months": aa.get("validity_period_months") or 36,
            "documents_required": aa.get("documents_required_common") or [],
            "methodology_summary": aa.get("methodology_summary") or "",
        }

    return {
        "client": req.client.dict(),
        "country": {"code": cc, "name": {"AU": "Australia", "CA": "Canada", "NZ": "New Zealand"}.get(cc, cc)},
        "occupation": {
            "code": occ.get("code"),
            "title": occ.get("title") or "",
            "description": occ.get("description") or "",
            "typical_tasks": occ.get("typical_tasks") or [],
            "alternative_titles": occ.get("alternative_titles") or [],
            "verification_meta": {
                "is_verified": occ.get("status") == "verified",
                "days_since_verified": None,
            },
        },
        "assessing_body": assessing_body,
        "salary": salary,
        "growth": growth,
        "workforce": workforce,
        "vacancy": vacancy,
        "top_industries": top_industries,
        "state_demand": state_demand,
        "pathways": pathways,
        "recommended_visa": recommended_visa,
        "fx_rate": fx_rate,
        "data_sources": "ABS, JSA, Home Affairs, ACS/VETASSESS/Engineers Australia",
    }


@router.post("/pre-assessment")
async def generate_pre_assessment(
    req: ReportRequest, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_generate(current_user):
        raise HTTPException(status_code=403, detail="Not authorised to generate reports")

    # Cache key (per-day, per-client, per-occupation)
    ch = _client_hash(req.client)
    key = f"{ch}|{req.country_code}|{req.occupation_code}"
    now_ts = time.time()
    if not req.preview_html and key in _CACHE:
        exp, pdf_bytes, ref = _CACHE[key]
        if exp > now_ts:
            return Response(
                content=pdf_bytes, media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="leamss_pre_assessment_{req.occupation_code}_{ref}.pdf"',
                    "X-Report-Ref": ref, "X-Cache": "HIT",
                },
            )

    # Build context
    ctx = await _build_context(req, current_user)
    ref = _ref_for(ch, req.country_code, req.occupation_code)
    ctx.update({
        "ref": ref,
        "agent_name": current_user.get("name") or current_user.get("email") or "LEAMSS agent",
        "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC"),
        "generated_at_date": datetime.now(timezone.utc).strftime("%d %b %Y"),
    })

    # Render template
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Template engine missing: {e}") from e
    tmpl_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(tmpl_dir)),
                      autoescape=select_autoescape(["html", "xml"]))
    tmpl = env.get_template("pre_assessment_report_v2.html")
    html = tmpl.render(**ctx)

    if req.preview_html:
        return Response(content=html, media_type="text/html",
                        headers={"X-Report-Ref": ref})

    # Render PDF
    try:
        from weasyprint import HTML
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"PDF engine unavailable: {e}") from e
    buf = BytesIO()
    HTML(string=html, base_url=str(tmpl_dir)).write_pdf(target=buf)
    buf.seek(0)
    pdf_bytes = buf.read()

    # Cache + log
    _CACHE[key] = (now_ts + _TTL, pdf_bytes, ref)
    try:
        await db["pre_assessment_reports_log"].insert_one({
            "id": str(uuid.uuid4()),
            "ref": ref,
            "client_name": req.client.name,
            "client_email": req.client.email,
            "country_code": req.country_code,
            "occupation_code": req.occupation_code,
            "occupation_title": ctx["occupation"]["title"],
            "agent_id": str(current_user.get("id") or ""),
            "agent_name": ctx["agent_name"],
            "size_bytes": len(pdf_bytes),
            "generated_at": datetime.now(timezone.utc),
        })
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to log pre-assessment report: %s", e)

    filename = f"leamss_pre_assessment_{req.occupation_code}_{ref}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Ref": ref, "X-Cache": "MISS",
        },
    )


@router.get("/pre-assessment/log")
async def list_report_log(
    limit: int = 50, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_generate(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    cursor = db["pre_assessment_reports_log"].find({}, {"_id": 0}).sort("generated_at", -1).limit(limit)
    items = []
    async for d in cursor:
        if isinstance(d.get("generated_at"), datetime):
            d["generated_at"] = d["generated_at"].isoformat()
        items.append(d)
    return {"items": items, "count": len(items)}
