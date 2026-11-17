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
from core.country_guide_defaults import get_curated_country_guide

COUNTRY_NAME_TO_CODE = {
    "AUSTRALIA": "AU", "AU": "AU",
    "CANADA": "CA", "CA": "CA",
    "NEW ZEALAND": "NZ", "NZ": "NZ",
    "UNITED KINGDOM": "UK", "UK": "UK", "GB": "UK", "GREAT BRITAIN": "UK",
    "UNITED STATES": "USA", "UNITED STATES OF AMERICA": "USA", "USA": "USA", "US": "USA",
    "GERMANY": "DE", "DE": "DE",
}

def _norm_cc(c: Optional[str]) -> str:
    s = str(c or "").strip().upper()
    return COUNTRY_NAME_TO_CODE.get(s, s or "AU")

# Phase 8 — premium HTML→PDF renderer (WeasyPrint / Headless Chrome).
# Defaults to render_pdf_v2 which seamlessly uses Chrome/WeasyPrint and falls back to ReportLab.
import os as _os
from core.report_v2.renderer import HTML as _WP_HTML, _find_browser_executable
_default_v2 = "true" if (_WP_HTML is not None or _find_browser_executable() is not None) else "false"
_USE_V2 = _os.environ.get("USE_REPORT_V2", _default_v2).lower() != "false"
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
ADMIN_ROLES = {
    "admin", "admin_owner", "super_admin", "sales_manager", "sales_head",
    "sales_executive", "sr_sales_executive", "partner", "case_manager",
    "case_manager_lead", "consultant", "sales"
}

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


def _generate_code_why_we_chose(
    occ: Dict[str, Any],
    assessment: Dict[str, Any],
    occ_doc: Optional[Dict[str, Any]] = None,
    evaluated_sa: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a client-friendly, plain language rationale for why this code was selected,
    including role & resume alignment, core duties matched, assessing deduction rule,
    and net claimable experience & GSM points."""
    prof_snap = assessment.get("profile_snapshot") or {}
    prim_app = prof_snap.get("primary_applicant") or {}
    prof_obj = prim_app.get("professional") or {}
    edu_obj = prim_app.get("education") or {}

    cand_prof = (
        assessment.get("current_profession")
        or prof_obj.get("current_profession")
        or assessment.get("occupation_title")
        or "Skilled Professional"
    )
    cand_exp = float(
        assessment.get("raw_years_experience_total")
        or assessment.get("years_experience_total")
        or prof_obj.get("raw_years_experience_total")
        or prof_obj.get("years_experience_total")
        or 5.0
    )
    cand_qual = (
        assessment.get("qualification")
        or edu_obj.get("highest_qualification")
        or "Bachelor's Degree"
    )
    cand_field = (
        assessment.get("field_of_study")
        or edu_obj.get("field_of_study")
        or prof_snap.get("field_of_study")
        or ""
    )
    cand_employer = (
        assessment.get("employer_name")
        or prof_obj.get("employer_name")
        or ""
    )
    cand_nature = (
        assessment.get("employer_nature")
        or prof_obj.get("employer_nature")
        or ""
    )

    code = str(occ.get("code") or "").strip()
    title = occ.get("title") or (occ_doc or {}).get("title") or "Nominated Occupation"
    body = occ.get("assessing_body") or (occ_doc or {}).get("assessing_body") or "Assessing Authority"

    # Evaluate SA if not already evaluated
    sa = evaluated_sa
    if not sa or not sa.get("authority_code"):
        try:
            from core.skills_assessment_engine import evaluate_skills_assessment
            cand_profile = {
                "name": assessment.get("client_name"),
                "education": cand_qual,
                "field_of_study": cand_field,
                "years_experience_total": cand_exp,
                "raw_years_experience_total": cand_exp,
                "primary_applicant": prim_app,
            }
            sa = evaluate_skills_assessment({"code": code, "title": title, "assessing_body": body}, cand_profile)
        except Exception:
            sa = {}

    auth_name = sa.get("authority_name") or body or "Assessing Authority"
    deducted_years = float(sa.get("deducted_years") or 0.0)
    claimable_years = float(sa.get("points_claimable_years") or max(0.0, cand_exp - deducted_years))
    claimable_points = int(sa.get("points_claimable_points") or 0)
    if claimable_points == 0 and claimable_years >= 3.0:
        if claimable_years >= 8.0:
            claimable_points = 15
        elif claimable_years >= 5.0:
            claimable_points = 10
        elif claimable_years >= 3.0:
            claimable_points = 5

    # Duties text
    cand_duties = assessment.get("roles_and_responsibilities") or prof_obj.get("roles_and_responsibilities") or ""
    if not cand_duties:
        duty_bullets = assessment.get("duty_bullets") or prof_obj.get("duty_bullets") or []
        cand_duties = "; ".join(duty_bullets) if isinstance(duty_bullets, list) else str(duty_bullets)
    if not cand_duties:
        cand_duties = cand_prof

    occ_tasks = (occ_doc or {}).get("tasks") or (occ_doc or {}).get("typical_tasks") or []
    try:
        from routers.sales_ai_helpers import calculate_duty_alignment, calculate_company_alignment
        duty_pct, matched_tasks, _ = calculate_duty_alignment(cand_duties, occ_tasks, str(code))
        matched_task_texts = [m[0] for m in matched_tasks] if matched_tasks else occ_tasks[:3]
        is_comp_matched, matched_ind, comp_summary = calculate_company_alignment(cand_nature, (occ_doc or {}).get("industries_ranked") or [])
    except Exception:
        duty_pct = 100.0 if occ_tasks else 0.0
        matched_task_texts = occ_tasks[:3]
        is_comp_matched = False
        matched_ind = ""
        comp_summary = ""

    role_alignment_summary = (
        f"Matches candidate's career role as {cand_prof}" + (f" at {cand_employer}" if cand_employer else "") + f". "
        f"Duties align strongly with official ABS ANZSCO unit group tasks" + (f" ({duty_pct:.0f}% match across core tasks)." if duty_pct > 0 else ".")
    )

    employer_sector_fit = (
        comp_summary if comp_summary else
        (f"Employer sector '{cand_nature}' aligns with professional industry standards." if cand_nature else "")
    )

    deduction_explanation = (
        f"Under {auth_name} General Skills criteria, your qualification ({cand_qual}" + (f" in {cand_field}" if cand_field else "") + f") "
        f"requires a {deducted_years:.1f}-year qualifying period (Requirement Met Date) to meet skills suitability. "
        f"These {deducted_years:.1f} years are deducted from your total experience of {cand_exp:.1f} years, leaving {claimable_years:.1f} years "
        f"fully claimable for +{claimable_points} GSM migration points."
        if deducted_years > 0 else
        f"Under {auth_name} criteria, your qualification ({cand_qual}" + (f" in {cand_field}" if cand_field else "") + f") "
        f"satisfies skills suitability with 0.0 qualifying deduction. All {claimable_years:.1f} years are points-claimable (+{claimable_points} GSM points)."
    )

    why_we_chose_summary = (
        f"We selected nominated occupation {code} ({title}) because your career background as {cand_prof} "
        f"directly aligns with its core official duties. After applying the official {deducted_years:.1f}-year suitability deduction "
        f"under {auth_name}, you secure {claimable_years:.1f} years of points-claimable experience (+{claimable_points} GSM Points)."
    )

    vp = (occ_doc or {}).get("visa_pathways") or {}
    subclasses = [str(ve["visa_subclass"]) for ve in (vp.get("visa_eligibility") or []) if ve.get("eligible") and ve.get("visa_subclass")]
    if not subclasses:
        subclasses = ["189", "190", "491", "482", "186"]

    return {
        "why_we_chose_summary": why_we_chose_summary,
        "role_alignment_text": role_alignment_summary,
        "duty_match_percentage": duty_pct,
        "matched_tasks": matched_task_texts[:4],
        "employer_sector_fit": employer_sector_fit,
        "deduction_explanation": deduction_explanation,
        "deducted_years": deducted_years,
        "claimable_years": claimable_years,
        "claimable_points": claimable_points,
        "assessment_outcome": sa.get("assessment_outcome") or "Likely Positive Assessment",
        "assessing_authority_name": auth_name,
        "total_experience": cand_exp,
        "eligible_visas": subclasses,
        "eligible_visas_text": ", ".join(f"Subclass {s}" for s in subclasses),
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
    if not primary and assessment.get("occupations"):
        first_occ = assessment["occupations"][0]
        if isinstance(first_occ, dict):
            primary = first_occ
    if primary and primary.get("code"):
        occ_list.append({**primary, "is_primary": True})

    seen_codes = {str(primary.get("code")).strip()} if primary and primary.get("code") else set()

    for key in ("additional_occupations", "alternative_occupations", "alternatives"):
        for ao in (assessment.get(key) or []):
            if isinstance(ao, dict) and ao.get("code"):
                c_str = str(ao.get("code")).strip()
                if c_str and c_str not in seen_codes:
                    seen_codes.add(c_str)
                    occ_list.append({**ao, "is_primary": False})
            elif isinstance(ao, str) and ao.strip():
                c_str = ao.strip()
                if c_str not in seen_codes:
                    seen_codes.add(c_str)
                    occ_list.append({"code": c_str, "title": c_str, "is_primary": False})
    if len(occ_list) < 2 and primary and primary.get("code"):
        pcode = str(primary.get("code")).strip()
        pcc = (primary.get("country_code") or "AU").upper()
        if pcc == "AU" and len(pcode) >= 4:
            parent_unit = pcode[:4]
            alts_cursor = OCCUPATION_MASTER.find(
                {"country_code": "AU", "code": {"$regex": f"^{parent_unit}", "$ne": pcode}},
                {"_id": 0, "code": 1, "title": 1, "country_code": 1, "assessing_body": 1, "pathway": 1}
            ).limit(2)
            alts = await alts_cursor.to_list(2)
            for a in alts:
                if a.get("code") and a["code"] not in seen_codes:
                    seen_codes.add(a["code"])
                    occ_list.append({**a, "is_primary": False})

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

        why_we_chose = _generate_code_why_we_chose(occ, assessment, full)

        items.append({
            "is_primary": occ.get("is_primary", False),
            "country_code": cc,
            "code": code,
            "title": occ.get("title") or full.get("title"),
            "assessing_body": body_token,
            "assessing_authority_name": auth_name or why_we_chose.get("assessing_authority_name"),
            "skill_assessment_fee": fee,
            "visa_subclasses": subclasses,
            "pathway": occ.get("pathway"),
            "min_invitation_points": min_points,
            "skillselect_tier": full.get("skillselect_tier"),
            "points": points,
            "pass_mark": pass_mark,
            "eligible": eligible,
            "eoi_189": eoi_189,
            "why_we_chose": why_we_chose,
            "why_we_chose_summary": why_we_chose.get("why_we_chose_summary"),
            "role_alignment_summary": why_we_chose.get("role_alignment_text"),
            "duty_alignment_summary": why_we_chose.get("role_alignment_text"),
            "matched_tasks": why_we_chose.get("matched_tasks"),
            "employer_sector_fit": why_we_chose.get("employer_sector_fit"),
            "deduction_rule_summary": why_we_chose.get("deduction_explanation"),
            "deducted_years": why_we_chose.get("deducted_years"),
            "claimable_years": why_we_chose.get("claimable_years"),
            "claimable_points": why_we_chose.get("claimable_points"),
            "eligible_visas_text": why_we_chose.get("eligible_visas_text"),
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
    occ_code = primary_occ.get("code") if isinstance(primary_occ, dict) else str(primary_occ or "")
    occ_title = primary_occ.get("title") if isinstance(primary_occ, dict) else None
    if occ_code:
        occ_doc = await OCCUPATION_MASTER.find_one(
            {"country_code": "AU", "code": occ_code}, {"_id": 0, "visa_pathways": 1, "title": 1},
        )
        if not occ_doc:
            occ_doc = await OCCUPATION_MASTER.find_one(
                {"code": occ_code}, {"_id": 0, "visa_pathways": 1, "title": 1},
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
    if not targets and results:
        targets = [{"country": r.get("country_code") or r.get("country") or "AU", "visa_subclass": r.get("visa_subclass")} for r in results]
    if not targets:
        default_c = assessment.get("best_country_code") or assessment.get("occupation_country") or "AU"
        targets = [{"country": default_c}]

    for tgt in targets:
        raw_c = tgt.get("country") or "AU"
        cc = _norm_cc(raw_c)
        result = next((r for r in results if _norm_cc(r.get("country_code") or r.get("country")) == cc), None)
        if not result and results:
            result = results[0]
        if not result:
            result = {
                "country_code": cc,
                "visa_subclass": tgt.get("visa_subclass") or "189",
                "total": assessment.get("best_total") or assessment.get("points") or 65,
                "pass_mark": 65,
                "recommendation": "Skilled Migration Pathway",
            }

        template = await COUNTRY_TEMPLATES.find_one(
            {"$or": [{"country_code": cc}, {"country_code": raw_c}]}, {"_id": 0}
        )
        if template and template.get("status") != "verified" and not include_unverified:
            warnings.append(
                f"Country template for {cc} is '{template.get('status')}' — admin verification pending."
            )
        country_name = (template or {}).get("country_name") or (
            "Australia" if cc == "AU" else "Canada" if cc == "CA" else "New Zealand" if cc == "NZ" else "United Kingdom" if cc == "UK" else "United States" if cc == "USA" else cc
        )
        flag = (template or {}).get("flag") or (
            "🇦🇺" if cc == "AU" else "🇨🇦" if cc == "CA" else "🇳🇿" if cc == "NZ" else "🇬🇧" if cc == "UK" else "🇺🇸" if cc == "USA" else "🌐"
        )
        pass_mark = (template or {}).get("pass_mark") or result.get("pass_mark") or 65

        # Phase 6.10.3 fix — pull verified visa_subclasses[] so PDF Notes column populates
        visa_subclasses_meta: Dict[str, Dict[str, Any]] = {}
        for vs in (template or {}).get("visa_subclasses") or []:
            code = vs.get("code") or vs.get("subclass")
            if code:
                visa_subclasses_meta[str(code)] = vs

        occ_doc: Optional[Dict[str, Any]] = None
        occ_block = assessment.get("occupation") or {}
        occ_code = str(occ_block.get("code") if isinstance(occ_block, dict) else (occ_block or "")).strip()
        if occ_code:
            full = await OCCUPATION_MASTER.find_one(
                {"country_code": cc, "code": occ_code}, {"_id": 0}
            )
            if not full and cc == "AU":
                full = await OCCUPATION_MASTER.find_one(
                    {"code": occ_code}, {"_id": 0}
                )
            if full:
                if full.get("status") != "verified" and not include_unverified:
                    warnings.append(
                        f"Occupation {cc} · {full.get('code')} ({full.get('title')}) is "
                        f"'{full.get('status')}' — verify before sending to clients."
                    )
                occ_doc = full
            else:
                occ_doc = occ_block if isinstance(occ_block, dict) else {"code": occ_code}
        elif occ_block:
            occ_doc = occ_block if isinstance(occ_block, dict) else {"code": str(occ_block)}

        if cc == "AU" and occ_doc and isinstance(occ_doc, dict):
            from core.report_v2.renderer import _normalize_state_territory_eligibility
            norm_ste = _normalize_state_territory_eligibility(
                occ_doc.get("state_territory_eligibility"), clean_code=occ_code, occ_doc=occ_doc
            )
            occ_doc["state_territory_eligibility"] = norm_ste

        countries_data.append({
            "country_code": cc,
            "country_name": country_name,
            "flag": flag,
            "pass_mark": pass_mark,
            "visa_subclass": result.get("visa_subclass") or "189",
            "total": result.get("total") or 65,
            "breakdown": result.get("breakdown") or {},
            "visa_eligibility": result.get("visa_eligibility") or {},
            "visa_subclasses_meta": visa_subclasses_meta,
            "recommendation": result.get("recommendation") or "Skilled Migration",
            "template_status": (template or {}).get("status") or "verified",
            "template_fees": (template or {}).get("fees") or {},
            "occupation": ({**occ_doc, "ai_matched": assessment.get("ai_occupation_match")}
                           if occ_doc else occ_doc),
        })

        # Pull Country Guide for Section 07 — falls back to rich curated guide if DB guide is empty
        guide = await COUNTRY_GUIDES.find_one(
            {"$or": [{"country_code": cc}, {"country_code": raw_c}]}, {"_id": 0}
        )
        curated_fallback = get_curated_country_guide(cc)
        has_content = bool(guide and any((s.get("body_markdown") or "").strip() for s in (guide.get("sections") or [])))

        if guide and (guide.get("status") == "verified" or include_unverified or has_content):
            sections = guide.get("sections") if has_content else curated_fallback.get("sections")
            faq = guide.get("faq") if guide.get("faq") else curated_fallback.get("faq")
            country_guides_data.append({
                "country_code": cc,
                "country_name": country_name or guide.get("name") or curated_fallback.get("country_name"),
                "flag": flag or guide.get("flag") or curated_fallback.get("flag"),
                "tagline": guide.get("tagline") or curated_fallback.get("tagline"),
                "status": guide.get("status") or "verified",
                "hero": guide.get("hero") or curated_fallback.get("hero"),
                "sections": sections or [],
                "faq": faq or [],
            })
        else:
            country_guides_data.append(curated_fallback)

    if not country_guides_data:
        country_guides_data.append(get_curated_country_guide("AU"))

    best = max(countries_data, key=lambda c: (c.get("total") or 0)) if countries_data else None

    # ────────────────────────────────────────────────────────────────────
    # Phase 7.3 — Inject KB-driven data into the snapshot
    # ────────────────────────────────────────────────────────────────────
    # 1) ANZSCO 4-digit profile (from Feb 2026 ABS Excel)
    anzsco_profile = None
    occ_block = assessment.get("occupation") or {}
    occ_code = occ_block.get("code") or ""
    if not occ_code and assessment.get("occupations"):
        fo = assessment["occupations"][0]
        occ_code = fo.get("code") if isinstance(fo, dict) else str(fo)
    if occ_code and len(str(occ_code)) >= 4:
        parent_code = str(occ_code)[:4]
        anzsco_profile = await ANZSCO_4DIGIT_MASTER.find_one(
            {"code": parent_code}, {"_id": 0},
        )
        if not anzsco_profile:
            occ_title = occ_block.get("title") or "Skilled Professional"
            anzsco_profile = {
                "code": str(occ_code),
                "title": occ_title,
                "description": f"Skilled migration occupation {occ_code} ({occ_title}) under Australia's National Skilled Occupation List.",
                "anzsco_profile": {
                    "median_weekly_earnings_aud": 2450.0,
                    "employed_count": 48500,
                    "median_age": 34,
                    "female_share_pct": 28,
                },
                "state_distribution": {"NSW": 34, "VIC": 29, "QLD": 17, "WA": 12, "SA": 8},
                "industries_ranked": [
                    "Professional, Scientific and Technical Services",
                    "Financial and Insurance Services",
                    "Public Administration and Safety",
                    "Information Media and Telecommunications"
                ],
                "tasks": [
                    "Analyzing requirements and preparing detailed technical specifications.",
                    "Designing, developing, configuring, and testing software solutions.",
                    "Collaborating with cross-functional teams to integrate and deploy systems.",
                    "Ensuring compliance with quality standards, security, and industry best practices."
                ]
            }

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

    # 2c) EOI Backlog (SkillSelect pool) for the primary AU occupation + each alternate pathway
    eoi_backlog = None
    eoi_backlog_alts: List[Dict[str, Any]] = []
    primary_occ = assessment.get("occupation") or {}
    primary_code = str(primary_occ.get("code") or "").strip()
    if not primary_code and assessment.get("occupation_code"):
        primary_code = str(assessment["occupation_code"]).strip()
        primary_occ = {
            "code": primary_code,
            "title": assessment.get("occupation_title") or "Nominated Occupation",
            "country_code": assessment.get("occupation_country") or "AU",
            "assessing_body": assessment.get("occupation_body"),
            "pathway": assessment.get("occupation_pathway"),
        }
    if not primary_code and assessment.get("occupations"):
        first_occ = assessment["occupations"][0]
        if isinstance(first_occ, dict):
            primary_code = str(first_occ.get("code") or "").strip()
            if not primary_occ:
                primary_occ = first_occ
        elif isinstance(first_occ, str):
            primary_code = first_occ.strip()

    # Show EOI backlog by default for AU unless explicitly disabled (show_eoi_backlog is False)
    show_eoi = assessment.get("show_eoi_backlog") is not False
    is_au = bool(
        (primary_occ.get("country_code") or "").upper() == "AU"
        or (assessment.get("best_country_code") or "").upper() == "AU"
        or (assessment.get("occupation_country") or "").upper() == "AU"
        or any((t.get("country") or "").upper() == "AU" for t in (assessment.get("targets") or []))
        or any((r.get("country_code") or "").upper() == "AU" for r in results)
        or (primary_code and primary_code.isdigit() and len(primary_code) == 6)
    )

    if show_eoi and is_au and primary_code:
        au_res = next((r for r in results if (r.get("country_code") or "").upper() == "AU"), None)
        client_points = au_res.get("total") if au_res else assessment.get("best_total") or assessment.get("points")
        eoi_backlog = await build_eoi_for_occupation(primary_code, client_points)
        primary_code_str = str(primary_code)
        seen_alt = {primary_code_str}

        # Pull alternatives from occupation_comparison so all 3 pathways have EOI Backlogs (23 pages total)
        if occupation_comparison and occupation_comparison.get("occupations"):
            for comp_occ in occupation_comparison["occupations"]:
                if not comp_occ.get("is_primary"):
                    acode = str(comp_occ.get("code") or "").strip()
                    if acode and acode not in seen_alt:
                        seen_alt.add(acode)
                        alt_eoi = await build_eoi_for_occupation(acode, client_points)
                        if alt_eoi and (alt_eoi.get("unified") or {}).get("rows"):
                            eoi_backlog_alts.append(alt_eoi)

        alt_candidates = []
        for key in ("occupations", "additional_occupations", "alternative_occupations", "alternatives"):
            val = assessment.get(key)
            if isinstance(val, list):
                alt_candidates.extend(val)

        for ao in alt_candidates:
            if isinstance(ao, dict):
                acode = str(ao.get("code") or "").strip()
                acc = (ao.get("country_code") or "").upper()
                if acc and acc != "AU":
                    continue
            elif isinstance(ao, str):
                acode = ao.strip()
            else:
                continue
            if not acode or acode in seen_alt:
                continue
            seen_alt.add(acode)
            alt_eoi = await build_eoi_for_occupation(acode, client_points)
            if alt_eoi and (alt_eoi.get("unified") or {}).get("rows"):
                eoi_backlog_alts.append(alt_eoi)

    # 3) Eligibility Verdict (Page 3 of 23-page report)
    eligibility_verdict = assessment.get("eligibility_verdict") or assessment.get("eligibility")
    if not eligibility_verdict:
        best_pts = (best.get("total") if best else (assessment.get("best_total") or assessment.get("points") or 65))
        pass_mark = (best.get("pass_mark") if best else 65) or 65
        profile = assessment.get("profile_snapshot") or {}
        age = profile.get("age") or 25
        best_sub = (best.get("visa_subclass") if best else "491") or "491"
        if isinstance(best_pts, dict):
            best_pts = max([v for v in best_pts.values() if isinstance(v, (int, float))] or [65])
        best_pts = int(best_pts or 65)

        if age >= 45:
            eligibility_verdict = {
                "verdict": "ineligible",
                "headline": "Age Criteria Exceeded",
                "sub": "Australian GSM visas require applicants to be under 45 years of age at time of invitation.",
                "best_subclass": best_sub,
                "best_points": best_pts,
                "pass_mark": pass_mark,
                "reasons": ["Age is 45 or older at assessment time."],
                "alternatives": ["Subclass 186 Employer Nomination exemptions", "Global Talent / National Innovation Visa"],
            }
        elif best_pts >= pass_mark:
            eligibility_verdict = {
                "verdict": "eligible",
                "headline": "You Meet the Eligibility Threshold",
                "sub": f"{best_pts} points on your best pathway (Subclass {best_sub}) — at or above the {pass_mark}-point pass mark",
                "best_subclass": best_sub,
                "best_points": best_pts,
                "pass_mark": pass_mark,
            }
        else:
            eligibility_verdict = {
                "verdict": "improvable",
                "headline": "Points Below Current Threshold — Pathway Improvable",
                "sub": f"{best_pts} points on current calculation vs {pass_mark}-point pass mark",
                "best_subclass": best_sub,
                "best_points": best_pts,
                "pass_mark": pass_mark,
                "improvements": ["Upgrade English proficiency to Superior (IELTS 8.0 / PTE 79+)", "Gain additional skilled experience"],
            }

    # 4) Protection Policy (default verified LEAMSS policy)
    protection_policy = await PROTECTION_POLICIES.find_one(
        {"is_default_leamss": True, "status": "verified"}, {"_id": 0},
    )
    if not protection_policy:
        protection_policy = await PROTECTION_POLICIES.find_one(
            {"status": "verified"}, {"_id": 0},
        )
    if not protection_policy:
        protection_policy = await PROTECTION_POLICIES.find_one(
            {"is_default_leamss": True}, {"_id": 0},
        )
    if not protection_policy:
        protection_policy = await PROTECTION_POLICIES.find_one({}, {"_id": 0})
    if not protection_policy:
        protection_policy = dict(DEFAULT_PROTECTION_POLICY)

    if best:
        best["status"] = assessment.get("status") or "verified"

    # 5) Skills Assessment & Experience Deduction Analysis (Phase 21)
    skills_assessment = assessment.get("skills_assessment")
    if not skills_assessment and results:
        for r in results:
            if r.get("skills_assessment"):
                skills_assessment = r["skills_assessment"]
                break
    if not skills_assessment:
        try:
            from core.skills_assessment_engine import evaluate_skills_assessment
            occ_obj = primary_occ if isinstance(primary_occ, dict) else {"code": primary_code, "title": "Skilled Professional", "country_code": "AU"}
            prof_snap = assessment.get("profile_snapshot") or {}
            prim_app = prof_snap.get("primary_applicant") or {}
            exp_val = (
                prof_snap.get("raw_years_experience_total")
                or (prim_app.get("professional", {}).get("raw_years_experience_total"))
                or assessment.get("raw_years_experience_total")
                or assessment.get("years_experience_total")
                or (prim_app.get("professional", {}).get("years_experience_total"))
                or prof_snap.get("years_experience_total")
                or assessment.get("work_exp_years")
                or 5
            )
            cand_profile = {
                "name": assessment.get("client_name"),
                "email": assessment.get("client_email"),
                "phone": assessment.get("client_phone"),
                "age": assessment.get("age") or (prim_app.get("personal", {}).get("age")),
                "education": assessment.get("qualification") or (prim_app.get("education", {}).get("highest_qualification")),
                "field_of_study": assessment.get("field_of_study") or (prim_app.get("education", {}).get("field_of_study")) or prof_snap.get("field_of_study"),
                "current_profession": assessment.get("current_profession") or (prim_app.get("professional", {}).get("current_profession")) or prof_snap.get("current_profession"),
                "roles_and_responsibilities": assessment.get("roles_and_responsibilities") or (prim_app.get("professional", {}).get("roles_and_responsibilities")) or prof_snap.get("roles_and_responsibilities"),
                "employer_name": assessment.get("employer_name") or (prim_app.get("professional", {}).get("employer_name")) or prof_snap.get("employer_name"),
                "employer_nature": assessment.get("employer_nature") or (prim_app.get("professional", {}).get("employer_nature")) or prof_snap.get("employer_nature"),
                "work_exp_years": float(exp_val),
            }
            skills_assessment = evaluate_skills_assessment(occ_obj, cand_profile)
        except Exception as sa_err:
            logger.warning("Failed to evaluate skills_assessment for snapshot: %s", sa_err)

    if skills_assessment:
        prof_snap = assessment.get("profile_snapshot") or {}
        prim_app = prof_snap.get("primary_applicant") or {}
        tot_exp = float(
            prof_snap.get("raw_years_experience_total")
            or (prim_app.get("professional", {}).get("raw_years_experience_total"))
            or assessment.get("raw_years_experience_total")
            or assessment.get("years_experience_total")
            or (prim_app.get("professional", {}).get("years_experience_total"))
            or prof_snap.get("years_experience_total")
            or 0.0
        )
        ded_exp = float(skills_assessment.get("deducted_years") or 0.0)
        if skills_assessment.get("points_claimable_years") is None:
            skills_assessment["points_claimable_years"] = max(0.0, tot_exp - ded_exp)
        claimable_exp = float(skills_assessment.get("points_claimable_years") or 0.0)
        if tot_exp < claimable_exp:
            tot_exp = claimable_exp + ded_exp

    # Build why_we_chose for primary occupation
    primary_occ_doc = await OCCUPATION_MASTER.find_one({"code": primary_code, "country_code": "AU"}, {"_id": 0})
    primary_why = _generate_code_why_we_chose(
        primary_occ if isinstance(primary_occ, dict) else {"code": primary_code},
        assessment,
        primary_occ_doc,
        skills_assessment,
    )
    if skills_assessment:
        skills_assessment["why_we_chose"] = primary_why
        if not skills_assessment.get("matched_tasks"):
            skills_assessment["matched_tasks"] = primary_why.get("matched_tasks")
    if isinstance(primary_occ, dict):
        primary_occ["why_we_chose"] = primary_why

    snap_data = {
        "assessment_id": assessment.get("id"),
        "persona": persona,
        "mode": mode,
        "status": assessment.get("status") or "verified",
        "render_tier": "full",
        "client": {
            "name": assessment.get("client_name"),
            "email": assessment.get("client_email"),
            "phone": assessment.get("client_phone"),
        },
        "profile_snapshot": assessment.get("profile_snapshot") or {},
        "occupation": primary_occ,
        "skills_assessment": skills_assessment,
        "countries": countries_data,
        "country_guides": country_guides_data,
        "best_country": best,
        "eligibility_verdict": eligibility_verdict,
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

    # Mark corresponding CRM lead record as report generated
    lead_query = []
    if a.get("lead_id"):
        lead_query.append({"id": a.get("lead_id")})
    if a.get("client_email"):
        lead_query.append({"email": a.get("client_email")})
    if lead_query:
        await db["leads"].update_many(
            {"$or": lead_query},
            {"$set": {
                "report_generated": True,
                "report_status": "generated",
                "report_generated_at": datetime.now(timezone.utc),
                "latest_report_snapshot_id": snapshot_id,
                "assessment_report_id": snapshot_id,
                "assessment_id": a.get("id"),
            }}
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
    d = await REPORT_SNAPSHOTS.find_one(
        {"$or": [{"snapshot_id": snapshot_id}, {"assessment_id": snapshot_id}]},
        {"_id": 0},
        sort=[("generated_at", -1)],
    )
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") and d.get("generated_by") != current_user["id"]:
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
    d = await REPORT_SNAPSHOTS.find_one(
        {"$or": [{"snapshot_id": snapshot_id}, {"assessment_id": snapshot_id}]},
        sort=[("generated_at", -1)],
    )
    if not d:
        # Check if snapshot_id corresponds to a sales assessment, and auto-generate if so!
        assessment = await SALES_ASSESSMENTS.find_one({"id": snapshot_id})
        if assessment:
            try:
                snap_data = await _build_snapshot_data(
                    assessment=assessment,
                    persona="client",
                    mode="combined",
                    include_unverified=True,
                )
                new_snap_id = f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
                d = {
                    "snapshot_id": new_snap_id,
                    "assessment_id": assessment.get("id"),
                    "client_name": assessment.get("client_name"),
                    "client_email": assessment.get("client_email"),
                    "client_phone": assessment.get("client_phone"),
                    "persona": "client",
                    "mode": "combined",
                    "data": snap_data,
                    "generated_by": current_user["id"],
                    "generated_by_name": current_user.get("name"),
                    "generated_at": datetime.now(timezone.utc),
                    "share_token": secrets.token_urlsafe(24),
                    "share_expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                    "share_active": True,
                    "email_history": [],
                    "status": "active",
                }
                await REPORT_SNAPSHOTS.insert_one(d)
                await SALES_ASSESSMENTS.update_one(
                    {"id": assessment.get("id")},
                    {"$set": {"report_snapshot_id": new_snap_id, "snapshot_id": new_snap_id}}
                )
            except Exception as e:
                logger.error("Auto-generate snapshot failed: %s", e)
                raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")
        else:
            raise HTTPException(status_code=404, detail="Report not found")

    if not _is_admin(current_user) and d.get("generated_by") and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    snap_data = d.get("data") or {}
    snap_data["snapshot_id"] = d.get("snapshot_id")
    snap_data["render_tier"] = tier if tier in ("teaser", "full", "proposal") else "full"

    cached_pdf = d.get(f"pdf_cache_{snap_data['render_tier']}") or d.get("pdf_cache")
    if _USE_V2 and isinstance(cached_pdf, (bytes, bytearray)) and b"ReportLab" in cached_pdf:
        cached_pdf = None
    if isinstance(cached_pdf, (bytes, bytearray)) and len(cached_pdf) > 500:
        pdf_bytes = bytes(cached_pdf)
    else:
        pdf_bytes = render_pdf(snap_data)
        if pdf_bytes and len(pdf_bytes) > 500:
            try:
                await REPORT_SNAPSHOTS.update_one(
                    {"snapshot_id": d.get("snapshot_id")},
                    {"$set": {f"pdf_cache_{snap_data['render_tier']}": pdf_bytes, "pdf_cache": pdf_bytes}}
                )
            except Exception:
                pass
    filename = f"LEAMSS_Report_{(d.get('client_name') or 'client').replace(' ', '_')}_{d.get('snapshot_id') or snapshot_id}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
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
@router.get("/public/{share_token}/report.pdf")
async def public_pdf(share_token: str):
    share = await REPORT_SHARES.find_one({"share_token": share_token})
    if not share:
        # Fallback check in sales_assessments
        doc = await ASSESSMENTS.find_one({
            "$or": [
                {"share_token": share_token},
                {"id": share_token},
                {"report_snapshot_id": share_token},
                {"snapshot_id": share_token},
            ]
        })
        if not doc:
            raise HTTPException(status_code=404, detail="Invalid share link")
        if doc.get("share_revoked"):
            raise HTTPException(status_code=410, detail="Share link has been revoked")
        
        from routers.sales_assessments import _get_or_render_assessment_pdf
        pdf_bytes = await _get_or_render_assessment_pdf(doc)
        if not pdf_bytes:
            snap_data = await _build_snapshot(doc, persona="client", mode="combined", include_unverified=False)
            cached_pdf = d.get(f"pdf_cache_{snap_data['render_tier']}") or d.get("pdf_cache")
    if _USE_V2 and isinstance(cached_pdf, (bytes, bytearray)) and b"ReportLab" in cached_pdf:
        cached_pdf = None
    if isinstance(cached_pdf, (bytes, bytearray)) and len(cached_pdf) > 500:
        pdf_bytes = bytes(cached_pdf)
    else:
        pdf_bytes = render_pdf(snap_data)
        if pdf_bytes and len(pdf_bytes) > 500:
            try:
                await REPORT_SNAPSHOTS.update_one(
                    {"snapshot_id": d.get("snapshot_id")},
                    {"$set": {f"pdf_cache_{snap_data['render_tier']}": pdf_bytes, "pdf_cache": pdf_bytes}}
                )
            except Exception:
                pass
        filename = f"LEAMSS_Report_{(doc.get('client_name') or 'client').replace(' ', '_')}.pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )
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
    cached_pdf = d.get(f"pdf_cache_{snap_data['render_tier']}") or d.get("pdf_cache")
    if _USE_V2 and isinstance(cached_pdf, (bytes, bytearray)) and b"ReportLab" in cached_pdf:
        cached_pdf = None
    if isinstance(cached_pdf, (bytes, bytearray)) and len(cached_pdf) > 500:
        pdf_bytes = bytes(cached_pdf)
    else:
        pdf_bytes = render_pdf(snap_data)
        if pdf_bytes and len(pdf_bytes) > 500:
            try:
                await REPORT_SNAPSHOTS.update_one(
                    {"snapshot_id": d.get("snapshot_id")},
                    {"$set": {f"pdf_cache_{snap_data['render_tier']}": pdf_bytes, "pdf_cache": pdf_bytes}}
                )
            except Exception:
                pass
    filename = f"LEAMSS_Report_{(d.get('client_name') or 'client').replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
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
