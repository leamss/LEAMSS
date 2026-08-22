"""Phase 6.10 Part 2 — Professional Assessment Report Engine.

Distinct from `reports.py` (which serves sales analytics). This module owns the
client-facing branded Assessment Report PDFs generated from frozen snapshots.

Route prefix: /api/assessment-reports

Endpoints:
  POST   /generate                   — create immutable snapshot + return metadata
  GET    /                           — list reports (admin sees all, sales own)
  GET    /{snapshot_id}              — metadata
  GET    /{snapshot_id}/pdf          — stream the branded PDF
  POST   /{snapshot_id}/share        — create / refresh a public share token
  DELETE /{snapshot_id}/share        — revoke (admin / owner)
  POST   /{snapshot_id}/email        — mocked email send (logs to DB)
  GET    /public/{share_token}       — public metadata (no auth)
  GET    /public/{share_token}/pdf   — public PDF stream (no auth)
"""
import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.report_renderer import now_human, render_pdf as render_pdf_v1
from core.report_v2 import render_pdf_v2
from routers.eoi_backlog import build_eoi_for_occupation, eoi_pool_total
from core.sales_calculator import calculate_with_rules

# Phase 8 — premium HTML→PDF renderer is the default.
# Set USE_REPORT_V2=false in env to fall back to the legacy ReportLab engine.
import os as _os
_USE_V2 = _os.environ.get("USE_REPORT_V2", "true").lower() != "false"
render_pdf = render_pdf_v2 if _USE_V2 else render_pdf_v1

router = APIRouter(prefix="/assessment-reports", tags=["assessment-reports"])

REPORT_SNAPSHOTS = db["report_snapshots"]
REPORT_SHARES = db["report_shares"]
REPORT_EMAILS = db["report_emails"]
ASSESSMENTS = db["sales_assessments"]
OCCUPATION_MASTER = db["occupation_master"]
COUNTRY_TEMPLATES = db["country_templates"]
COUNTRY_GUIDES = db["country_guides"]
ANZSCO_4DIGIT_MASTER = db["anzsco_4digit_master"]
PROTECTION_POLICIES = db["protection_policies"]
SKILL_BODY_MASTER = db["skill_body_master"]
ADMIN_ROLES = {"admin", "admin_owner"}

# Built-in LEAMSS Protection Policy (Sir's USP) — used as the guaranteed fallback so
# the "100% Refund Guarantee" section prints on EVERY report even when no verified
# policy is seeded in the DB (e.g. a fresh install). Mirrors the admin seed content.
DEFAULT_PROTECTION_POLICY = {
    "policy_id": "POL-LEAMSS-DEFAULT",
    "title": "🛡️ LEAMSS Protection Policy — 100% Refund Guarantee",
    "policy_type": "negative_outcome_refund",
    "description_markdown": (
        "LEAMSS is India's first migration consultancy to introduce a 100% Protection "
        "Policy that safeguards your entire investment. If your skill assessment is negative "
        "or your visa is rejected due to factors we have committed to verify upfront, we refund "
        "your professional fees + government fees without question. This policy is part of our "
        "promise of complete transparency, honesty and emotional accountability to every client."
    ),
    "refund_terms": {
        "covers": ["professional_fees", "government_fees", "body_fees"],
        "excludes": ["english_test_fees", "medical_test_fees", "police_clearance_fees"],
        "claim_within_days": 90,
    },
    "applicable_countries": ["AU", "CA", "NZ", "UK", "USA"],
    "applicable_visa_types": ["*"],
    "version": "1.0",
    "is_default_leamss": True,
    "status": "verified",
}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _strip(d: dict) -> dict:
    if d and "_id" in d:
        d.pop("_id", None)
    return d


def _hash(payload: Any) -> str:
    s = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


async def _skill_body_fee(body_token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Look up a skill-assessing body's standard fee from skill_body_master.

    Matches on name / short_name / slug (skill_body_master has no `code` field).
    Returns {currency, amount, inr} or None when not found.
    """
    if not body_token:
        return None
    tok = str(body_token).strip()
    if not tok:
        return None
    doc = await SKILL_BODY_MASTER.find_one({
        "$or": [
            {"name": {"$regex": f"^{re.escape(tok)}$", "$options": "i"}},
            {"slug": tok.lower()},
            {"slug": tok.lower().replace(" ", "_")},
            {"full_name": {"$regex": re.escape(tok), "$options": "i"}},
        ]
    }, {"_id": 0, "name": 1, "full_name": 1, "fees": 1})
    if not doc:
        return None
    std = (doc.get("fees") or {}).get("standard") or {}
    return {
        "authority_name": doc.get("full_name") or doc.get("name"),
        "currency": std.get("native_currency"),
        "amount": std.get("native_amount"),
        "inr": std.get("inr_equivalent"),
    }


async def _build_occupation_comparison(
    assessment: Dict[str, Any], results: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Build a side-by-side comparison of the primary + additional occupations.

    Each item carries: code, title, assessing authority, skill-assessment fee,
    eligible visa pathways, min invitation points, and the client's points score
    (profile-driven, so shared per country) + eligibility vs the pass mark.
    Only returned when 2+ occupations are selected.
    """
    occ_list: List[Dict[str, Any]] = []
    primary = assessment.get("occupation")
    if primary and primary.get("code"):
        occ_list.append({**primary, "is_primary": True})
    for ao in (assessment.get("additional_occupations") or []):
        if ao and ao.get("code"):
            occ_list.append({**ao, "is_primary": False})

    if len(occ_list) < 2:
        return None

    items: List[Dict[str, Any]] = []
    for occ in occ_list:
        cc = (occ.get("country_code") or "").upper()
        code = occ.get("code")
        full = await OCCUPATION_MASTER.find_one(
            {"country_code": cc, "code": code}, {"_id": 0},
        ) or {}

        auth = full.get("assessing_authority") or {}
        auth_name = (auth.get("name") or auth.get("short_name")) if isinstance(auth, dict) else (auth or None)
        body_token = occ.get("assessing_body") or (
            (auth.get("name") or auth.get("short_name") or auth.get("body_id")) if isinstance(auth, dict) else None
        )
        fee = await _skill_body_fee(body_token)

        # Eligible visa subclasses
        vp = full.get("visa_pathways") or {}
        subclasses = []
        for ve in (vp.get("visa_eligibility") or []):
            if ve.get("eligible") and ve.get("visa_subclass"):
                subclasses.append(str(ve["visa_subclass"]))
        subclasses = sorted(set(subclasses))

        # Min invitation points (AU): show the standard subclass 189 cutoff if present
        mip = full.get("min_invitation_points") or {}
        min_points = mip.get("189") if isinstance(mip, dict) else mip

        # Client points for this occupation's country (profile-driven)
        res = next((r for r in results if (r.get("country_code") or "").upper() == cc), None)
        points = res.get("total") if res else None
        pass_mark = res.get("pass_mark") if res else None
        if pass_mark is None and cc:
            tmpl = await COUNTRY_TEMPLATES.find_one({"country_code": cc}, {"_id": 0, "pass_mark": 1})
            pass_mark = (tmpl or {}).get("pass_mark")
        eligible = None
        if points is not None and pass_mark is not None:
            eligible = points >= pass_mark

        # EOI pool (subclass 189 SUBMITTED) — AU only
        eoi_189 = None
        if cc == "AU":
            eoi_189 = await eoi_pool_total(code, "189")

        items.append({
            "is_primary": occ.get("is_primary", False),
            "country_code": cc,
            "code": code,
            "title": occ.get("title") or full.get("title"),
            "assessing_body": body_token,
            "assessing_authority_name": auth_name,
            "skill_assessment_fee": fee,
            "visa_subclasses": subclasses,
            "pathway": occ.get("pathway"),
            "min_invitation_points": min_points,
            "skillselect_tier": full.get("skillselect_tier"),
            "points": points,
            "pass_mark": pass_mark,
            "eligible": eligible,
            "eoi_189": eoi_189,
        })

    return {"occupations": items}


def _occupation_open_map(occ_doc: Dict[str, Any]) -> Dict[str, Optional[bool]]:
    """From an occupation_master doc, which GSM subclasses accept this occupation."""
    out: Dict[str, Optional[bool]] = {"189": None, "190": None, "491": None}
    vp = (occ_doc or {}).get("visa_pathways") or {}
    for ve in (vp.get("visa_eligibility") or []):
        sc = str(ve.get("visa_subclass") or "")
        if sc in out:
            out[sc] = bool(ve.get("eligible"))
    return out


async def _build_au_subclass_points(
    assessment: Dict[str, Any], results: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Points for ALL three AU GSM subclasses (189 / 190 / 491), regardless of which
    subclass was selected, plus whether the primary occupation is open for each.

    190 = base + 5 (state nomination), 491 = base + 15 (regional/family nomination).
    These nomination points are shown as potential (they require an invitation).
    """
    targets = assessment.get("targets") or []
    primary_occ = assessment.get("occupation") or {}
    au_relevant = (
        (primary_occ.get("country_code") or "").upper() == "AU"
        or any((t.get("country") or "").upper() == "AU" for t in targets)
    )
    if not au_relevant:
        return None

    profile = assessment.get("profile_snapshot") or {}
    try:
        base = await calculate_with_rules(db, profile, "AU", "189")
    except Exception:
        return None
    total_189 = int(base.get("total") or 0)
    ve = base.get("visa_eligibility") or {}
    pass_mark = (ve.get("189") or {}).get("min_required") or 65

    open_map = {"189": None, "190": None, "491": None}
    occ_code = primary_occ.get("code")
    occ_title = primary_occ.get("title")
    if occ_code and (primary_occ.get("country_code") or "").upper() == "AU":
        occ_doc = await OCCUPATION_MASTER.find_one(
            {"country_code": "AU", "code": occ_code}, {"_id": 0, "visa_pathways": 1, "title": 1},
        )
        if occ_doc:
            open_map = _occupation_open_map(occ_doc)
            occ_title = occ_title or occ_doc.get("title")

    state_nominated = bool(((profile.get("primary_applicant") or {}).get("au_extras") or {}).get("state_nominated"))

    rows = [
        {"subclass": "189", "label": "Skilled Independent", "points": total_189,
         "nomination": 0, "requires_nomination": False,
         "meets_pass": total_189 >= pass_mark, "occupation_open": open_map.get("189")},
        {"subclass": "190", "label": "Skilled Nominated (State)", "points": total_189 + 5,
         "nomination": 5, "requires_nomination": True,
         "meets_pass": (total_189 + 5) >= pass_mark, "occupation_open": open_map.get("190")},
        {"subclass": "491", "label": "Skilled Work Regional", "points": total_189 + 15,
         "nomination": 15, "requires_nomination": True,
         "meets_pass": (total_189 + 15) >= pass_mark, "occupation_open": open_map.get("491")},
    ]
    return {
        "pass_mark": pass_mark,
        "occupation_code": occ_code,
        "occupation_title": occ_title,
        "state_nominated": state_nominated,
        "base_points": total_189,
        "rows": rows,
    }


async def _build_snapshot(
    assessment: Dict[str, Any], *,
    persona: str = "client", mode: str = "combined",
    include_unverified: bool = False,
) -> Dict[str, Any]:
    warnings: List[str] = []
    countries_data: List[Dict[str, Any]] = []
    country_guides_data: List[Dict[str, Any]] = []
    results = assessment.get("results") or []
    targets = assessment.get("targets") or []

    for tgt in targets:
        cc = (tgt.get("country") or "").upper()
        result = next((r for r in results if (r.get("country_code") or "").upper() == cc), None)
        if not result:
            continue

        template = await COUNTRY_TEMPLATES.find_one({"country_code": cc}, {"_id": 0})
        if template and template.get("status") != "verified" and not include_unverified:
            warnings.append(
                f"Country template for {cc} is '{template.get('status')}' — admin verification pending."
            )
        country_name = (template or {}).get("country_name") or cc
        flag = (template or {}).get("flag") or ""
        pass_mark = (template or {}).get("pass_mark") or result.get("pass_mark")

        # Phase 6.10.3 fix — pull verified visa_subclasses[] so PDF Notes column populates
        visa_subclasses_meta: Dict[str, Dict[str, Any]] = {}
        for vs in (template or {}).get("visa_subclasses") or []:
            code = vs.get("code") or vs.get("subclass")
            if code:
                visa_subclasses_meta[str(code)] = vs

        occ_doc: Optional[Dict[str, Any]] = None
        occ_block = assessment.get("occupation") or {}
        if occ_block and (occ_block.get("country_code") or "").upper() == cc:
            full = await OCCUPATION_MASTER.find_one(
                {"country_code": cc, "code": occ_block.get("code")}, {"_id": 0}
            )
            if full:
                if full.get("status") != "verified" and not include_unverified:
                    warnings.append(
                        f"Occupation {cc} · {full.get('code')} ({full.get('title')}) is "
                        f"'{full.get('status')}' — verify before sending to clients."
                    )
                occ_doc = full
            else:
                occ_doc = occ_block

        countries_data.append({
            "country_code": cc,
            "country_name": country_name,
            "flag": flag,
            "pass_mark": pass_mark,
            "visa_subclass": result.get("visa_subclass"),
            "total": result.get("total"),
            "breakdown": result.get("breakdown") or {},
            "visa_eligibility": result.get("visa_eligibility") or {},
            "visa_subclasses_meta": visa_subclasses_meta,
            "recommendation": result.get("recommendation"),
            "template_status": (template or {}).get("status") or "none",
            "template_fees": (template or {}).get("fees") or {},
            "occupation": ({**occ_doc, "ai_matched": assessment.get("ai_occupation_match")}
                           if occ_doc else occ_doc),
        })

        # Phase 6.10.3 fix — pull verified Country Guide for Section 5
        guide = await COUNTRY_GUIDES.find_one({"country_code": cc}, {"_id": 0})
        if guide:
            if guide.get("status") == "verified" or include_unverified:
                country_guides_data.append({
                    "country_code": cc,
                    "country_name": country_name or guide.get("name"),
                    "flag": flag or guide.get("flag"),
                    "status": guide.get("status"),
                    "hero": guide.get("hero") or {},
                    "sections": guide.get("sections") or [],
                    "faq": guide.get("faq") or [],
                })
            elif guide.get("status") != "verified":
                warnings.append(
                    f"Country guide for {cc} is '{guide.get('status')}' — verify it under "
                    f"/admin/country-guides to publish in this report."
                )

    best = max(countries_data, key=lambda c: (c.get("total") or 0)) if countries_data else None

    # ────────────────────────────────────────────────────────────────────
    # Phase 7.3 — Inject KB-driven data into the snapshot
    # ────────────────────────────────────────────────────────────────────
    # 1) ANZSCO 4-digit profile (from Feb 2026 ABS Excel)
    anzsco_profile = None
    occ_block = assessment.get("occupation") or {}
    occ_code = occ_block.get("code") or ""
    if occ_code and len(occ_code) >= 4:
        parent_code = occ_code[:4]
        anzsco_profile = await ANZSCO_4DIGIT_MASTER.find_one(
            {"code": parent_code}, {"_id": 0},
        )

    # 2) Cost Estimator (from sales_assessments.cost_estimator)
    from routers.sales_wizard_v2 import DEFAULT_PACKAGES
    cost_estimator = assessment.get("cost_estimator")
    if not cost_estimator:
        cost_estimator = {
            "currency": "INR",
            "items": [],
            "packages": DEFAULT_PACKAGES,
            "service_packages": DEFAULT_PACKAGES,
            "total_by_currency": {"INR": 0},
            "notes": "",
        }
    else:
        pkgs = cost_estimator.get("service_packages") or cost_estimator.get("packages")
        if not pkgs:
            pkgs = DEFAULT_PACKAGES
        for p in pkgs:
            fee = float(p.get("professional_fee") or 0)
            disc = float(p.get("discount") or 0)
            gst = float(p.get("gst") or 0)
            calc_total = max(0, fee - disc + gst)
            p["total_payable"] = float(p.get("total") if p.get("total") is not None else (p.get("total_payable") if p.get("total_payable") is not None else calc_total))
            p["total"] = p["total_payable"]
            if "show" in p:
                p["show_in_report"] = bool(p["show"])
            else:
                p.setdefault("show_in_report", True)
        cost_estimator["packages"] = pkgs
        cost_estimator["service_packages"] = pkgs


    # 2b) Occupation side-by-side comparison (primary + additional codes)
    occupation_comparison = await _build_occupation_comparison(assessment, results)

    # 2b-ii) Points across all AU subclasses (189/190/491) + occupation open per subclass
    au_subclass_points = await _build_au_subclass_points(assessment, results)

    # 2c) EOI Backlog (SkillSelect pool) for the primary AU occupation + each alternate
    # pathway — only when the consultant has opted to show it for this client.
    eoi_backlog = None
    eoi_backlog_alts: List[Dict[str, Any]] = []
    primary_occ = assessment.get("occupation") or {}
    if assessment.get("show_eoi_backlog") and (primary_occ.get("country_code") or "").upper() == "AU":
        au_res = next((r for r in results if (r.get("country_code") or "").upper() == "AU"), None)
        client_points = au_res.get("total") if au_res else None
        if primary_occ.get("code"):
            eoi_backlog = await build_eoi_for_occupation(primary_occ["code"], client_points)
        primary_code = str(primary_occ.get("code") or "")
        seen_alt = {primary_code}
        for ao in (assessment.get("additional_occupations") or []):
            acode = str((ao or {}).get("code") or "")
            if not acode or acode in seen_alt or (ao.get("country_code") or "").upper() != "AU":
                continue
            seen_alt.add(acode)
            alt_eoi = await build_eoi_for_occupation(acode, client_points)
            if alt_eoi and (alt_eoi.get("unified") or {}).get("rows"):
                eoi_backlog_alts.append(alt_eoi)

    # 3) Protection Policy (default verified LEAMSS policy)
    protection_policy = await PROTECTION_POLICIES.find_one(
        {"is_default_leamss": True, "status": "verified"}, {"_id": 0},
    )
    if not protection_policy:
        # Fallback: any verified policy (so PDF still shows USP)
        protection_policy = await PROTECTION_POLICIES.find_one(
            {"status": "verified"}, {"_id": 0},
        )
    if not protection_policy:
        # Guaranteed fallback — the Protection Policy (Sir's USP) must print on EVERY
        # report, independent of the cost/investment breakdown or DB seed state.
        protection_policy = dict(DEFAULT_PROTECTION_POLICY)

    snap_data = {
        "assessment_id": assessment.get("id"),
        "persona": persona,
        "mode": mode,
        "render_tier": "full",
        "client": {
            "name": assessment.get("client_name"),
            "email": assessment.get("client_email"),
            "phone": assessment.get("client_phone"),
        },
        "profile_snapshot": assessment.get("profile_snapshot") or {},
        "countries": countries_data,
        "country_guides": country_guides_data,
        "best_country": best,
        # Phase 7.3 — new snapshot fields
        "anzsco_profile": anzsco_profile,
        "cost_estimator": cost_estimator,
        "occupation_comparison": occupation_comparison,
        "au_subclass_points": au_subclass_points,
        "eoi_backlog": eoi_backlog,
        "eoi_backlog_alts": eoi_backlog_alts,
        "protection_policy": protection_policy,
        "warnings": warnings,
        "generated_at_iso": datetime.now(timezone.utc).isoformat(),
        "generated_on_human": now_human(),
    }
    snap_data["data_integrity_hash"] = _hash(snap_data)
    return snap_data


# ─────────────────────────────────────────────────────────────────────────────
# Generate
# ─────────────────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    assessment_id: str
    persona: str = "client"
    mode: str = "combined"
    target_country: Optional[str] = None
    include_unverified: bool = Field(False)


@router.post("/generate")
async def generate_report(req: GenerateRequest, current_user: dict = Depends(get_current_user)):
    a = await ASSESSMENTS.find_one({"id": req.assessment_id})
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not _is_admin(current_user) and a.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")

    if req.mode == "single":
        if not req.target_country:
            raise HTTPException(status_code=400, detail="target_country required for mode='single'")
        cc = req.target_country.upper()
        a = dict(a)
        a["targets"] = [t for t in (a.get("targets") or []) if (t.get("country") or "").upper() == cc]
        a["results"] = [r for r in (a.get("results") or []) if (r.get("country_code") or "").upper() == cc]
        if not a["targets"]:
            raise HTTPException(status_code=400, detail=f"Assessment has no target for {cc}")

    snap_data = await _build_snapshot(
        a, persona=req.persona, mode=req.mode, include_unverified=req.include_unverified,
    )

    snapshot_id = f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "snapshot_id": snapshot_id,
        "assessment_id": a.get("id"),
        "client_name": a.get("client_name"),
        "persona": req.persona,
        "mode": req.mode,
        "render_tier": "full",
        "include_unverified": req.include_unverified,
        "data": snap_data,
        "warnings": snap_data.get("warnings") or [],
        "data_integrity_hash": snap_data["data_integrity_hash"],
        "generated_at": datetime.now(timezone.utc),
        "generated_by": current_user["id"],
        "generated_by_name": current_user.get("name") or current_user.get("email"),
        "is_immutable": True,
    }
    await REPORT_SNAPSHOTS.insert_one(doc)
    await ASSESSMENTS.update_one(
        {"id": a.get("id")},
        {"$push": {"report_snapshot_ids": snapshot_id},
         "$set": {"latest_report_snapshot_id": snapshot_id,
                  "latest_report_generated_at": datetime.now(timezone.utc)}},
    )
    return _strip(doc)


# ─────────────────────────────────────────────────────────────────────────────
# List + Get
# ─────────────────────────────────────────────────────────────────────────────
@router.get("")
async def list_reports(
    assessment_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    current_user: dict = Depends(get_current_user),
):
    q: Dict[str, Any] = {}
    if assessment_id:
        q["assessment_id"] = assessment_id
    if not _is_admin(current_user):
        q["generated_by"] = current_user["id"]
    items = []
    async for d in REPORT_SNAPSHOTS.find(q, {"_id": 0, "data": 0}).sort("generated_at", -1).limit(limit):
        items.append(_strip(d))
    return {"items": items, "count": len(items)}


@router.get("/{snapshot_id}")
async def get_report(snapshot_id: str, current_user: dict = Depends(get_current_user)):
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    return _strip(d)


@router.get("/{snapshot_id}/pdf")
async def stream_pdf(
    snapshot_id: str,
    tier: str = "full",
    current_user: dict = Depends(get_current_user),
):
    """Phase 7.3 — tier-aware PDF stream.

    tier values:
      - teaser   — public read before PA payment (5-6 pages, cover + summary + protection + CTA)
      - full     — after PA paid (everything: code deep-dive, costs, guide)
      - proposal — after main fees paid (full + proposal-letter cover)
    Admins and the snapshot owner can request any tier. Tier is recorded on the snapshot
    via /upgrade-tier (internal logic, no Stripe).
    """
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    snap_data = d.get("data") or {}
    snap_data["snapshot_id"] = d.get("snapshot_id")
    snap_data["render_tier"] = tier if tier in ("teaser", "full", "proposal") else "full"
    pdf_bytes = render_pdf(snap_data)
    filename = f"LEAMSS_Report_{(d.get('client_name') or 'client').replace(' ', '_')}_{snapshot_id}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


class UpgradeTierRequest(BaseModel):
    tier: str = Field(..., description="full | proposal")
    payment_ref: Optional[str] = Field(None, description="Internal payment reference / PA id / receipt no.")


@router.post("/{snapshot_id}/upgrade-tier")
async def upgrade_tier(
    snapshot_id: str,
    req: UpgradeTierRequest,
    current_user: dict = Depends(get_current_user),
):
    """Phase 7.3 — Internal-logic tier upgrade. No Stripe (Sir's directive).

    Admin or owner can flip a snapshot's gating tier. Typically called when the
    Pre-Assessment fee or main fee is marked paid in the admin console.
    """
    if req.tier not in ("teaser", "full", "proposal"):
        raise HTTPException(400, "tier must be one of: teaser, full, proposal")
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    await REPORT_SNAPSHOTS.update_one(
        {"snapshot_id": snapshot_id},
        {"$set": {
            "render_tier": req.tier,
            "tier_upgraded_at": datetime.now(timezone.utc),
            "tier_upgraded_by": current_user.get("id"),
            "tier_payment_ref": req.payment_ref,
        }},
    )
    return {"ok": True, "snapshot_id": snapshot_id, "tier": req.tier}


# ─────────────────────────────────────────────────────────────────────────────
# Share — public read-only magic links
# ─────────────────────────────────────────────────────────────────────────────
class ShareRequest(BaseModel):
    expires_in_days: int = Field(30, ge=1, le=365)


@router.post("/{snapshot_id}/share")
async def share_report(snapshot_id: str, req: ShareRequest, current_user: dict = Depends(get_current_user)):
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    share_doc = {
        "share_token": token,
        "snapshot_id": snapshot_id,
        "assessment_id": d.get("assessment_id"),
        "client_name": d.get("client_name"),
        "created_by": current_user["id"],
        "created_at": now,
        "expires_at": now + timedelta(days=req.expires_in_days),
        "access_count": 0,
        "last_accessed_at": None,
        "revoked": False,
    }
    await REPORT_SHARES.insert_one(share_doc)
    return _strip(share_doc)


@router.delete("/{snapshot_id}/share")
async def revoke_share(snapshot_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id})
        if not d or d.get("generated_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Admin or owner only")
    r = await REPORT_SHARES.update_many(
        {"snapshot_id": snapshot_id, "revoked": False},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc),
                  "revoked_by": current_user["id"]}},
    )
    return {"ok": True, "revoked_count": r.modified_count}


def _expired(share: dict) -> bool:
    exp = share.get("expires_at")
    if not exp:
        return False
    # Mongo returns naive datetimes — make tz-aware for safe comparison
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp < datetime.now(timezone.utc)


@router.get("/public/{share_token}")
async def public_report_meta(share_token: str):
    share = await REPORT_SHARES.find_one({"share_token": share_token}, {"_id": 0})
    if not share:
        raise HTTPException(status_code=404, detail="Invalid share link")
    if share.get("revoked"):
        raise HTTPException(status_code=410, detail="Share link has been revoked")
    if _expired(share):
        raise HTTPException(status_code=410, detail="Share link expired")
    await REPORT_SHARES.update_one(
        {"share_token": share_token},
        {"$inc": {"access_count": 1}, "$set": {"last_accessed_at": datetime.now(timezone.utc)}},
    )
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": share["snapshot_id"]}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "snapshot_id": d.get("snapshot_id"),
        "client_name": d.get("client_name"),
        "generated_at": d.get("generated_at"),
        "persona": d.get("persona"),
        "integrity_hash": d.get("data_integrity_hash"),
        "countries_count": len((d.get("data") or {}).get("countries") or []),
        "best_country": (d.get("data") or {}).get("best_country"),
        "pdf_url": f"/api/assessment-reports/public/{share_token}/pdf",
        "company": "Ladhani Education & Migration Services Pvt. Ltd.",
        "tagline": "We Value Emotions",
    }


@router.get("/public/{share_token}/pdf")
async def public_pdf(share_token: str):
    share = await REPORT_SHARES.find_one({"share_token": share_token})
    if not share:
        raise HTTPException(status_code=404, detail="Invalid share link")
    if share.get("revoked"):
        raise HTTPException(status_code=410, detail="Share link has been revoked")
    if _expired(share):
        raise HTTPException(status_code=410, detail="Share link expired")
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": share["snapshot_id"]})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    snap_data = d.get("data") or {}
    snap_data["snapshot_id"] = d.get("snapshot_id")
    # Public link respects snapshot tier or defaults to full
    snap_data["render_tier"] = d.get("render_tier") or "full"
    pdf_bytes = render_pdf(snap_data)
    filename = f"LEAMSS_Report_{(d.get('client_name') or 'client').replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


class EmailRequest(BaseModel):
    to_email: str
    subject: Optional[str] = "Your LEAMSS Assessment Report"
    body: Optional[str] = None


@router.post("/{snapshot_id}/email")
async def email_report(snapshot_id: str, req: EmailRequest, current_user: dict = Depends(get_current_user)):
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    log = {
        "snapshot_id": snapshot_id,
        "to_email": req.to_email,
        "subject": req.subject,
        "body": req.body,
        "sent_by": current_user["id"],
        "sent_at": datetime.now(timezone.utc),
        "status": "mocked",
    }
    await REPORT_EMAILS.insert_one(log)
    return {"ok": True, "status": "mocked", "to_email": req.to_email,
            "note": "Email is MOCKED. Provide RESEND_API_KEY to enable live dispatch."}
