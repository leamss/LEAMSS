"""Bulk Pre-Assessment pipeline (Australia PR · 189 / 190 / 491).

Two-phase system:
  PHASE A  Upload Excel → validate → background-generate DRAFT assessments + reports
  PHASE B  Review dashboard: per-client edit (code / english / spouse / cost / EOI) + regenerate
  EXPORT   ZIP of all PDFs + summary Excel

Points are computed deterministically via core.sales_calculator (100% accurate given inputs).
Defaults (editable per client in Phase B): English 8/8/8/8/8 superior, AU extras none,
total experience treated as overseas, married clients default to competent-English spouse (+5 partner points).
"""
from __future__ import annotations

import asyncio
import io
import os
import re
import time
import uuid
import zipfile
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from core.auth import get_current_user
from core.database import db
from core.sales_calculator import calculate_with_rules
from routers.assessment_reports import _build_snapshot, REPORT_SNAPSHOTS, _skill_body_fee
from routers.sales_wizard_v2 import _kb_cost_defaults, _leamss_service_packages
from core.report_v2 import render_pdf_v2
from core.bulk_ai_enrich import fetch_resume_text, match_anzsco, build_description, BULK_PARSE_MODEL
from core.resume_extractor import parse_resume_with_ai, extract_text_smart
from core.report_email import build_report_email, build_not_eligible_email, build_resume_request_email
from core.eligibility import classify_eligibility, bucket_for_row, manual_verdict
from core.bulk_ai_enrich import fetch_resume_bytes
from core.gmail_dwd import (
    send as gmail_send, is_configured as gmail_is_configured,
    default_sender as gmail_default_sender, remaining_budget as gmail_remaining,
    sa_client_id as gmail_sa_client_id, sa_client_email as gmail_sa_client_email,
    delegated_domain as gmail_domain,
)

router = APIRouter(prefix="/bulk-assessments", tags=["bulk-assessments"])

BATCHES = db["bulk_batches"]
ROWS = db["bulk_rows"]
ASSESSMENTS = db["sales_assessments"]
OCCUPATION_MASTER = db["occupation_master"]
SKILL_BODY_MASTER = db["skill_body_master"]
FEE_OVERRIDES = db["skill_assessment_fee_overrides"]  # admin-saved authority fees (grows over time)
MAIL_SENDERS = db["mail_senders"]  # consultant mailboxes (separate list, domain-wide delegation)
_gridfs = AsyncIOMotorGridFSBucket(db, bucket_name="bulk_pdfs")
_resume_gridfs = AsyncIOMotorGridFSBucket(db, bucket_name="bulk_resumes")

ADMIN_ROLES = {"admin", "admin_owner"}
DEFAULT_ENGLISH = {"overall": 8, "listening": 8, "reading": 8, "writing": 8, "speaking": 8}

# Canonical assessing-authority key aliases (occupation_master uses full legal names /
# varying body_ids; we fold them into one stable key per authority).
_AUTH_KEY_ALIASES = {
    "cpa_australia": "cpa", "cpa_au": "cpa", "cpaaustralia": "cpa", "cpaaustralialtd": "cpa",
    "caanz": "cpa",
    "trades_tra": "tra", "tradesrecognitionaustralia": "tra",
    "aitsl_0a45": "aitsl", "australianinstituteforteachingandschoolleadershiplimited": "aitsl",
    "engineersaustralia": "ea", "theinstitutionofengineersaustralia": "ea",
    "australiancomputersociety": "acs", "australiancomputersocietyincorporated": "acs",
    "vocationaleducationandtrainingassessmentservices": "vetassess",
    "australiannursingmidwiferyaccreditationcouncillimited": "anmac",
    "australianhealthpractitionerregulationagency": "ahpra",
    "medicalboardofaustralia": "ahpra",
    "instituteofmanagersandleadersnational": "aim",
}


def _can(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or []) or role in (
        "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "partner",
    )


# ─────────────────────────────────────────────────────────────
# Column mapping + normalisers
# ─────────────────────────────────────────────────────────────
def _norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).strip().lower())


COLUMN_ALIASES = {
    "name":        ["name", "clientname", "fullname", "applicantname"],
    "email":       ["email", "emailid", "emailaddress"],
    "phone":       ["mobilenumber", "mobile", "phone", "contact", "phonenumber", "contactnumber"],
    "dob":         ["dateofbirth", "dob", "birthdate", "birthday"],
    "qualification": ["qualification", "highestqualification", "education", "degree"],
    "experience":  ["workexperiencetotal", "workexperience", "totalexperience", "experience",
                    "yearsofexperience", "totalworkexperience", "experienceyears"],
    "gender":      ["gender", "sex"],
    "marital_status": ["maritalstatus", "marital"],
    "resume_link": ["resumelink", "resume", "cv", "cvlink", "resumeurl"],
    "anzsco_code": ["anzscocode", "anzsco", "occupationcode", "code", "skillcode"],
    "occupation_title": ["occupation", "occupationtitle", "jobtitle", "profession"],
    "enquiry_date": ["date", "enquirydate", "leaddate", "registrationdate"],
    # optional english overrides
    "eng_overall": ["ieltsoverall", "englishoverall", "pteoverall", "overall"],
    "eng_listening": ["ieltslistening", "listening"],
    "eng_reading": ["ieltsreading", "reading"],
    "eng_writing": ["ieltswriting", "writing"],
    "eng_speaking": ["ieltsspeaking", "speaking"],
}


def _map_columns(cols: List[str]) -> Dict[str, str]:
    norm_map = {_norm(c): c for c in cols}
    out: Dict[str, str] = {}
    for key, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            if a in norm_map:
                out[key] = norm_map[a]
                break
    return out


def _norm_qualification(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s or s == "nan":
        return None

    # Clean punctuation for token checks
    clean = re.sub(r"[\.\-\/\_]", "", s)
    tokens = set(re.findall(r"[a-z0-9\+]+", s)) | set(re.findall(r"[a-z0-9\+]+", clean))

    # Doctorate
    doc_tokens = {"phd", "doctorate", "doctoral", "dphil"}
    if tokens & doc_tokens or "ph.d" in s or "doctor of philosophy" in s or "doctorate" in s:
        return "doctorate"

    # Master / Post-grad
    master_tokens = {
        "master", "masters", "mtech", "msc", "me", "mba", "mca", "mcom", "ma", "ms",
        "postgrad", "postgraduate", "pg", "pgdm", "pgdca", "pgd", "mpharm", "mpt", "march",
        "llm", "med", "msw", "mdes", "ca", "icwa", "cma", "cfa"
    }
    if tokens & master_tokens or "master" in s or "post graduate" in s or "post-graduate" in s:
        return "master"

    # Bachelor / Undergrad / Professional degrees
    bachelor_tokens = {
        "bachelor", "bachelors", "btech", "be", "bsc", "bs", "bcom", "bca", "ba",
        "bba", "bms", "bhm", "bpharm", "bds", "mbbs", "bpt", "barch", "llb",
        "bed", "bams", "bhms", "bsw", "bdes", "bvsc", "undergrad", "undergraduate",
        "degree", "graduate", "graduation", "ug"
    }
    if tokens & bachelor_tokens or "bachelor" in s or "engineering" in s or "under graduate" in s:
        return "bachelor"

    # Diploma / Nursing diplomas (GNM / ANM)
    diploma_tokens = {"diploma", "polytechnic", "gnm", "anm", "dpharm", "ded"}
    if tokens & diploma_tokens or "diploma" in s or "general nursing" in s:
        return "diploma"

    # Trade / Certificate
    trade_tokens = {"trade", "iti", "certificate", "cert", "apprenticeship", "vocational"}
    if tokens & trade_tokens or "trade" in s or "certificate" in s:
        return "trade"

    # High school
    hs_tokens = {"12th", "10th", "hsc", "ssc", "intermediate", "secondary", "highschool"}
    if tokens & hs_tokens or "high school" in s or "higher secondary" in s or "+2" in s:
        return "high_school"

    return None


def _norm_marital(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if any(k in s for k in ("married", "de facto", "defacto", "de-facto", "spouse")):
        return "married"
    return "single"


def _parse_dob_to_age(raw: Any) -> Optional[int]:
    if raw is None or str(raw).strip() in ("", "nan"):
        return None
    dob = None
    if isinstance(raw, datetime):
        dob = raw.date()
    elif isinstance(raw, date):
        dob = raw
    else:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d %b %Y", "%d %B %Y", "%d.%m.%Y"):
            try:
                dob = datetime.strptime(str(raw).strip()[:19], fmt).date()
                break
            except ValueError:
                continue
        if dob is None:
            try:
                dob = pd.to_datetime(str(raw), dayfirst=True).date()
            except Exception:
                return None
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 0 or age > 100:
        return None
    return age


def _to_float(v: Any) -> Optional[float]:
    try:
        f = float(str(v).strip())
        return f
    except (ValueError, TypeError):
        return None


async def _parse_and_validate_row(rowmap: Dict[str, str], r: pd.Series) -> Dict[str, Any]:
    def g(key):
        col = rowmap.get(key)
        if not col:
            return None
        v = r.get(col)
        if pd.isna(v):
            return None
        return v

    errors: List[str] = []          # hard errors (block the row)
    recoverable: List[str] = []     # blanks the AI can fill from a resume
    name = str(g("name") or "").strip()
    if not name:
        errors.append("Missing client name")

    age = _parse_dob_to_age(g("dob"))
    if age is None:
        recoverable.append("Date of Birth")
    # Age 45+ is NOT a hard error — the client still gets a clear Not-Eligible (age) report.

    resume_link = str(g("resume_link") or "").strip() or None

    raw_q = str(g("qualification") or "").strip()
    qualification = _norm_qualification(g("qualification"))
    if qualification is None:
        if raw_q and not resume_link:
            errors.append(f"Unrecognised qualification: '{raw_q}'")
        else:
            recoverable.append("Qualification")  # AI will normalise it from the resume

    experience = _to_float(g("experience"))
    if experience is None:
        recoverable.append("Work experience")

    code = str(g("anzsco_code") or "").strip()
    code = re.sub(r"\.0$", "", code)  # excel float codes
    occ_title = None
    occ_country = "AU"
    if code:
        occ = await OCCUPATION_MASTER.find_one(
            {"country_code": "AU", "code": code}, {"_id": 0, "title": 1, "assessing_authority": 1},
        )
        if not occ:
            errors.append(f"ANZSCO code {code} not found in Occupation Master (AU)")
        else:
            occ_title = occ.get("title")
    else:
        recoverable.append("ANZSCO code")

    eng = dict(DEFAULT_ENGLISH)
    for band in ("overall", "listening", "reading", "writing", "speaking"):
        v = _to_float(g(f"eng_{band}"))
        if v is not None:
            eng[band] = v

    parsed = {
        "name": name,
        "email": str(g("email") or "").strip() or None,
        "phone": str(g("phone") or "").strip() or None,
        "age": age,
        "qualification": qualification,
        "qualification_raw": raw_q or None,
        "experience_total": experience,
        "experience_au": 0,
        "gender": str(g("gender") or "").strip() or None,
        "marital_status": _norm_marital(g("marital_status")),
        "resume_link": resume_link,
        "anzsco_code": code or None,
        "anzsco_source": "manual" if code else None,
        "occupation_title": occ_title,
        "occupation_country": occ_country,
        "english": eng,
        "enquiry_date": str(g("enquiry_date") or "").strip() or None,
    }
    # Status: hard errors block. Blank fields are AI-recoverable if a Resume Link exists,
    # otherwise they become hard errors.
    if errors:
        status = "error"
    elif recoverable:
        if resume_link:
            status = "needs_ai"
        else:
            status = "error"
            errors = [f"Missing {r} (no Resume Link to auto-detect)" for r in recoverable]
    else:
        status = "valid"
    return {"parsed": parsed, "errors": errors, "status": status}


def _revalidate_row(p: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Recompute a row's status/errors after AI enrichment filled fields."""
    errors: List[str] = []
    if not p.get("name"):
        errors.append("Missing client name")
    age = p.get("age")
    if age is None:
        errors.append("Missing/invalid Date of Birth")
    # Age 45+ is NOT a hard error — a Not-Eligible (age) report is still produced.
    if not p.get("qualification"):
        errors.append("Unrecognised / missing qualification")
    if p.get("experience_total") is None:
        errors.append("Missing/invalid work experience (years)")
    if not p.get("anzsco_code"):
        return ("needs_ai" if p.get("resume_link") else "error",
                errors + ["Could not determine ANZSCO code from resume"])
    return ("error" if errors else "valid", errors)


def _spouse_from_partner_skill(skill: Optional[str]) -> Optional[Dict[str, Any]]:
    """Map the per-client Partner Skills dropdown to a spouse block the calculator understands.
    A migrating partner must set is_applicant_on_visa=True, else the calculator treats the
    applicant as single (+10). Only relevant when marital status is married/de_facto."""
    COMPETENT = {"scores": {"overall": 7, "listening": 7, "reading": 7, "writing": 7, "speaking": 7}}
    if skill == "pr_citizen":
        return {"is_australian_pr_or_citizen": True}
    if skill == "skilled":
        return {"is_applicant_on_visa": True, "contribution_type": "skill_assessment",
                "personal": {"age": 30}, "language": COMPETENT}
    if skill == "english_only":
        return {"is_applicant_on_visa": True, "contribution_type": "english_only", "language": COMPETENT}
    # 'none' / not skilled → migrating partner, not contributing → 0 points
    return {"is_applicant_on_visa": True, "contribution_type": "non_contributing"}


def _profile_from_parsed(p: Dict[str, Any]) -> Dict[str, Any]:
    extras = p.get("au_extras") or {}
    # Partner points: honour the per-client override. Default for married/de_facto clients
    # (when no override is set) = migrating spouse with competent English → +5 partner points.
    spouse_override = p.get("spouse_override")
    if spouse_override is None and p.get("marital_status") in ("married", "de_facto"):
        spouse_override = _spouse_from_partner_skill("english_only")
    return {
        "client_name": p["name"],
        "marital_status": p["marital_status"],
        "primary_applicant": {
            "personal": {"age": p["age"]},
            "professional": {
                "current_profession": p.get("occupation_title"),
                "designation": p.get("occupation_title"),
                "years_experience_total": p["experience_total"],
                "years_experience_australia": p.get("experience_au", 0),
            },
            "education": {"highest_qualification": p["qualification"]},
            "language": {"scores": p["english"]},
            "au_extras": {
                "australian_study_2_years": bool(extras.get("australian_study_2_years")),
                "specialist_education_stem_au": bool(extras.get("specialist_education_stem_au")),
                "professional_year_completed": bool(extras.get("professional_year_completed")),
                "naati_accredited": bool(extras.get("naati_accredited")),
                "regional_study_au": bool(extras.get("regional_study_au")),
                "state_nominated": bool(p.get("state_nominated")),
                "state_code": p.get("state_code"),
            },
        },
        "spouse": spouse_override,
    }


# ─────────────────────────────────────────────────────────────
# Template
# ─────────────────────────────────────────────────────────────
@router.get("/template")
async def download_template(current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    headers = ["Name", "Email", "Mobile Number", "Date of Birth", "Qualification",
               "Work Experience - Total", "Gender", "Marital Status", "ANZSCO Code",
               "Resume Link", "Date"]
    example = ["John Doe", "john@example.com", "9876543210", "15/06/1994",
               "Bachelor of Engineering", "8", "Male", "Single", "261313",
               "https://drive.google.com/...", "01/06/2026"]
    example2 = ["Priya Sharma (AI will detect from resume)", "priya@example.com", "9812300000",
                "", "", "", "Female", "Married", "",
                "https://drive.google.com/file/d/FILEID/view?usp=sharing", "01/06/2026"]
    df = pd.DataFrame([example, example2], columns=headers)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Clients")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="bulk_preassessment_template.xlsx"'},
    )


# ─────────────────────────────────────────────────────────────
# Upload + Validate  → creates a batch (nothing generated yet)
# ─────────────────────────────────────────────────────────────
@router.post("/validate")
async def validate_upload(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    raw = await file.read()
    try:
        if (file.filename or "").lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw))
        else:
            df = pd.read_excel(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    df = df.dropna(how="all")
    if df.empty:
        raise HTTPException(status_code=400, detail="File has no data rows")

    rowmap = _map_columns(list(df.columns))
    # Only Name is strictly required at the column level. ANZSCO can be derived from a Resume
    # Link, and blank age/qualification/experience are AI-recoverable when a resume is present.
    required = {"name"}
    missing_cols = required - set(rowmap.keys())
    if "anzsco_code" not in rowmap and "resume_link" not in rowmap:
        missing_cols = set(missing_cols) | {"ANZSCO Code OR Resume Link"}
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {sorted(missing_cols)}. Found: {list(df.columns)}",
        )

    batch_id = f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc)
    row_docs = []
    valid = 0
    needs_ai = 0
    for idx, (_, r) in enumerate(df.iterrows()):
        res = await _parse_and_validate_row(rowmap, r)
        if res["status"] == "valid":
            valid += 1
        elif res["status"] == "needs_ai":
            needs_ai += 1
        row_docs.append({
            "id": str(uuid.uuid4()),
            "batch_id": batch_id,
            "row_index": idx + 1,
            "parsed": res["parsed"],
            "errors": res["errors"],
            "status": res["status"],  # valid | error | needs_ai | generated | failed
            "assessment_id": None,
            "snapshot_id": None,
            "pdf_file_id": None,
            "points": None,
            "created_at": now,
        })
    if row_docs:
        await ROWS.insert_many(row_docs)

    batch = {
        "id": batch_id,
        "name": file.filename or batch_id,
        "status": "ready",  # ready | enriching | generating | done
        "total": len(row_docs),
        "valid": valid,
        "invalid": len(row_docs) - valid - needs_ai,
        "needs_ai": needs_ai,
        "generated": 0,
        "failed": 0,
        "show_eoi_backlog": True,  # per user's choice for these bulk reports
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name") or current_user.get("email"),
        "created_at": now,
    }
    await BATCHES.insert_one(batch)

    preview = [
        {"row_index": d["row_index"], "name": d["parsed"]["name"], "code": d["parsed"]["anzsco_code"],
         "age": d["parsed"]["age"], "qualification": d["parsed"]["qualification"],
         "status": d["status"], "errors": d["errors"]}
        for d in row_docs[:50]
    ]
    return {"batch_id": batch_id, "total": len(row_docs), "valid": valid,
            "needs_ai": needs_ai, "invalid": len(row_docs) - valid - needs_ai, "preview": preview}


# ─────────────────────────────────────────────────────────────
# AI enrich: Resume Link → ANZSCO code (+ fill missing fields)
# ─────────────────────────────────────────────────────────────
def _fill_missing_from_profile(p: Dict[str, Any], profile: Dict[str, Any]) -> List[str]:
    """Fill only the BLANK Excel fields from the AI-parsed resume. Returns filled field names."""
    filled: List[str] = []
    pa = profile.get("primary_applicant") or {}
    prof = pa.get("professional") or {}
    edu = pa.get("education") or {}
    personal = pa.get("personal") or {}
    lang = pa.get("language") or {}

    if p.get("experience_total") is None:
        yr = _to_float(prof.get("years_experience_total"))
        if yr:
            p["experience_total"] = yr
            filled.append("experience")
    if not p.get("qualification"):
        q = _norm_qualification(edu.get("highest_qualification"))
        if q:
            p["qualification"] = q
            p["qualification_raw"] = edu.get("highest_qualification")
            filled.append("qualification")
    if p.get("age") is None:
        age = personal.get("age")
        if not age and personal.get("date_of_birth"):
            age = _parse_dob_to_age(personal.get("date_of_birth"))
        try:
            if age and 0 < int(age) < 100:
                p["age"] = int(age)
                filled.append("age")
        except (ValueError, TypeError):
            pass
    if not p.get("email") and profile.get("email"):
        p["email"] = profile["email"]; filled.append("email")
    if not p.get("phone") and profile.get("phone"):
        p["phone"] = profile["phone"]; filled.append("phone")
    if not p.get("gender") and personal.get("gender"):
        p["gender"] = personal["gender"]; filled.append("gender")
    scores = lang.get("scores") or {}
    if scores and lang.get("test_completed"):
        eng = dict(p.get("english") or {})
        for band in ("overall", "listening", "reading", "writing", "speaking"):
            v = _to_float(scores.get(band))
            if v is not None:
                eng[band] = v
        p["english"] = eng
        filled.append("english")
    return filled


async def _enrich_from_text(p: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Given a client profile dict + extracted resume text, run AI parse + ANZSCO match and
    populate the profile. Shared by bulk enrichment, manual upload and suggest-codes."""
    profile = await parse_resume_with_ai(text, model=BULK_PARSE_MODEL)
    if profile.get("_error"):
        return {"status": "needs_ai", "parsed": p, "ai_error": profile["_error"]}
    filled = _fill_missing_from_profile(p, profile)
    desc = build_description(profile) or text[:1500]
    match = await match_anzsco(db, desc)
    if match.get("_error"):
        return {"status": "needs_ai", "parsed": p, "ai_error": match["_error"]}
    best = match.get("best") or {}
    code = best.get("code")
    if not code:
        p["ai_alternatives"] = match.get("alternatives") or []
        return {"status": "needs_ai", "parsed": p,
                "ai_error": "AI could not match a suitable ANZSCO code from this resume"}
    occ = await OCCUPATION_MASTER.find_one({"country_code": "AU", "code": code}, {"_id": 0, "title": 1})
    p["anzsco_code"] = code
    p["occupation_title"] = (occ or {}).get("title") or best.get("title")
    p["anzsco_source"] = "ai"
    p["ai_confidence"] = best.get("confidence")
    p["ai_reasoning"] = best.get("reasoning")
    p["ai_alternatives"] = match.get("alternatives") or []
    p["ai_enriched"] = True
    p["ai_filled_fields"] = filled
    status, errors = _revalidate_row(p)
    return {"status": status, "parsed": p, "errors": errors,
            "ai_error": None if status == "valid" else "; ".join(errors)}


async def _enrich_one(row: Dict[str, Any]) -> Dict[str, Any]:
    p = dict(row["parsed"])
    text, err = await fetch_resume_text(p.get("resume_link"))
    if err:
        return {"status": "needs_ai", "parsed": p, "ai_error": err}
    return await _enrich_from_text(p, text)


async def _run_ai_enrich(batch_id: str, user: Dict[str, Any] | None = None):
    rows = await ROWS.find({"batch_id": batch_id, "status": "needs_ai"}, {"_id": 0}).to_list(100000)
    if not rows:
        await BATCHES.update_one({"id": batch_id}, {"$set": {"status": "ready", "ai_heartbeat": None}})
        return
    # Own the batch state so this run is self-describing (survives restarts / manual resume)
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "status": "enriching", "ai_total": len(rows), "ai_done": 0,
        "ai_heartbeat": datetime.now(timezone.utc).isoformat(),
    }})
    # LLM concurrency for enrichment. Blocking LLM/PDF work is offloaded to threads, so the
    # event loop stays responsive; kept at 6 for good throughput without over-subscribing.
    sem = asyncio.Semaphore(6)
    done = 0

    async def worker(row):
        nonlocal done
        async with sem:
            try:
                # Hard per-row cap so a slow/hanging LLM call can never freeze the batch
                res = await asyncio.wait_for(_enrich_one(row), timeout=120)
            except asyncio.TimeoutError:
                res = {"status": "needs_ai", "parsed": row["parsed"],
                       "ai_error": "AI timed out on this resume (>120s) — try again or set the code manually"}
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                res = {"status": "needs_ai", "parsed": row["parsed"],
                       "ai_error": f"{type(e).__name__}: {str(e)[:100]}"}
        await ROWS.update_one({"id": row["id"]}, {"$set": {
            "status": res["status"], "parsed": res["parsed"],
            "errors": res.get("errors", row.get("errors", [])), "ai_error": res.get("ai_error"),
        }})
        done += 1
        # Heartbeat + progress so a stalled/dead run can be detected and resumed
        upd = {"ai_done": done, "ai_heartbeat": datetime.now(timezone.utc).isoformat()}
        # Keep the header stat cards (valid / needs_ai / invalid) roughly live during the run
        if done % 10 == 0:
            upd["valid"] = await ROWS.count_documents({"batch_id": batch_id, "status": "valid"})
            upd["needs_ai"] = await ROWS.count_documents({"batch_id": batch_id, "status": "needs_ai"})
            upd["invalid"] = await ROWS.count_documents({"batch_id": batch_id, "status": "error"})
        await BATCHES.update_one({"id": batch_id}, {"$set": upd})

    try:
        await asyncio.gather(*[worker(r) for r in rows])
    except asyncio.CancelledError:
        # Backend is shutting down (reload/restart). Leave status='enriching' so the
        # startup hook resumes this batch — do NOT mark it 'ready' prematurely.
        raise
    # Normal completion only
    valid = await ROWS.count_documents({"batch_id": batch_id, "status": "valid"})
    still = await ROWS.count_documents({"batch_id": batch_id, "status": "needs_ai"})
    err = await ROWS.count_documents({"batch_id": batch_id, "status": "error"})
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "status": "ready", "valid": valid, "needs_ai": still, "invalid": err,
        "ai_heartbeat": None,
    }})


def _enrich_is_stale(batch: Dict[str, Any], max_idle_seconds: int = 90) -> bool:
    """A batch marked 'enriching' whose heartbeat is old = its background task died
    (e.g. a backend restart). Such a run is safe to resume."""
    hb = batch.get("ai_heartbeat")
    if not hb:
        return True
    try:
        last = datetime.fromisoformat(hb)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return True
    return (datetime.now(timezone.utc) - last).total_seconds() > max_idle_seconds


async def resume_stuck_enrichments():
    """On startup, re-launch AI enrichment for any batch left mid-run by a restart."""
    stuck = await BATCHES.find({"status": "enriching"}, {"id": 1, "_id": 0}).to_list(1000)
    for b in stuck:
        try:
            asyncio.create_task(_run_ai_enrich(b["id"]))
        except Exception as e:  # noqa: BLE001
            print(f"[bulk] could not resume enrichment for {b.get('id')}: {e}")
    if stuck:
        print(f"[bulk] resuming AI enrichment for {len(stuck)} batch(es) after restart")


@router.post("/{batch_id}/ai-enrich")
async def ai_enrich(batch_id: str, current_user: dict = Depends(get_current_user)):
    """Kick off (or resume) AI resume→ANZSCO detection for all rows with a Resume Link but no code."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    batch = await BATCHES.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.get("status") == "generating":
        raise HTTPException(status_code=400, detail="Batch is generating reports")
    if batch.get("status") == "enriching" and not _enrich_is_stale(batch):
        raise HTTPException(status_code=400, detail="AI detection is already running")
    # status is 'enriching' but stale (task died on a restart) → safe to resume
    pending = await ROWS.count_documents({"batch_id": batch_id, "status": "needs_ai"})
    if pending == 0:
        raise HTTPException(status_code=400, detail="No rows need AI ANZSCO detection")
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "status": "enriching", "ai_done": 0, "ai_total": pending,
        "ai_heartbeat": datetime.now(timezone.utc).isoformat(),
    }})
    resuming = batch.get("status") == "enriching"
    asyncio.create_task(_run_ai_enrich(batch_id))
    return {"ok": True, "enriching": pending, "resumed": resuming}



# ─────────────────────────────────────────────────────────────
# Generate (background)
# ─────────────────────────────────────────────────────────────
# ── Assessing-authority canonical key + fee resolution ───────────────
def _canon_auth_key(auth: Any) -> str:
    """Fold an assessing_authority (dict or string) into one stable key."""
    if isinstance(auth, dict):
        bid = auth.get("body_id") or auth.get("slug")
        k = _norm(bid) if bid else _norm(auth.get("short_name") or auth.get("name") or auth.get("full_name") or "")
    else:
        k = _norm(auth or "")
    return _AUTH_KEY_ALIASES.get(k, k) or "unknown"


def _auth_display_name(auth: Any) -> str:
    if isinstance(auth, dict):
        return (auth.get("full_name") or auth.get("name") or auth.get("short_name")
                or auth.get("body_id") or "Assessing Authority")
    return str(auth or "Assessing Authority")


def _fee_from_std(std: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not std:
        return None
    inr = std.get("inr_equivalent")
    if inr:
        return {"amount": float(inr), "currency": "INR"}
    nat = std.get("native_amount")
    if nat:
        return {"amount": float(nat), "currency": std.get("native_currency") or "AUD"}
    return None


def _fee_components_of(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalise a fee-master / skill-body doc into a clean list of fee components."""
    comps = doc.get("components")
    if comps:
        return [{"label": c.get("label") or "Skill Assessment Fee",
                 "amount": float(c["amount"]), "currency": c.get("currency") or "INR"}
                for c in comps if c.get("amount") not in (None, "")]
    if doc.get("amount") not in (None, ""):  # legacy single-amount docs
        return [{"label": "Skill Assessment Fee", "amount": float(doc["amount"]),
                 "currency": doc.get("currency") or "INR"}]
    return []


_FEE_MAP_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0}


async def _fee_master_map(force: bool = False) -> Dict[str, Dict[str, Any]]:
    """canon_key -> {authority_name, components:[{label,amount,currency}], source}.
    Base defaults derived from skill_body_master (single component), overlaid by the
    admin Fee Master (skill_assessment_fee_overrides — supports multiple components)."""
    now = time.time()
    cached = _FEE_MAP_CACHE.get("data")
    if not force and cached is not None and now - _FEE_MAP_CACHE["ts"] < 3:
        return cached
    m: Dict[str, Dict[str, Any]] = {}
    async for doc in SKILL_BODY_MASTER.find({}, {"_id": 0, "name": 1, "slug": 1, "full_name": 1, "fees": 1}):
        fee = _fee_from_std((doc.get("fees") or {}).get("standard") or {})
        if not fee:
            continue
        comp = [{"label": "Skill Assessment Fee", "amount": fee["amount"], "currency": fee["currency"]}]
        name = doc.get("full_name") or doc.get("name") or doc.get("slug")
        for token in (doc.get("slug"), doc.get("name"), doc.get("full_name")):
            if token:
                k = _AUTH_KEY_ALIASES.get(_norm(token), _norm(token))
                m.setdefault(k, {"authority_name": name, "components": comp, "source": "skill_body"})
    async for doc in FEE_OVERRIDES.find({}, {"_id": 0}):
        k = doc.get("key")
        if not k:
            continue
        comps = _fee_components_of(doc)
        if comps:
            m[k] = {"authority_name": doc.get("authority_name") or (m.get(k) or {}).get("authority_name") or k,
                    "components": comps, "source": "fee_master"}
    _FEE_MAP_CACHE["data"] = m
    _FEE_MAP_CACHE["ts"] = now
    return m


async def _authority_catalog() -> List[Dict[str, Any]]:
    """Every distinct assessing authority present in occupation_master (AU) + occupation counts."""
    pipe = [
        {"$match": {"country_code": "AU"}},
        {"$group": {"_id": "$assessing_authority", "n": {"$sum": 1}}},
    ]
    agg: Dict[str, Dict[str, Any]] = {}
    async for r in OCCUPATION_MASTER.aggregate(pipe):
        auth = r["_id"]
        if not auth:
            continue  # occupations with no assessing authority — covered by the batch fallback fee
        key = _canon_auth_key(auth)
        name = _auth_display_name(auth)
        if key == "unknown":
            continue
        if key not in agg:
            agg[key] = {"key": key, "authority_name": name, "occupation_count": 0}
        agg[key]["occupation_count"] += r["n"]
        if len(name) > len(agg[key]["authority_name"]):
            agg[key]["authority_name"] = name
    return sorted(agg.values(), key=lambda x: -x["occupation_count"])


async def _resolve_skill_lines(anzsco_code: Optional[str], batch_defaults: Optional[Dict[str, Any]],
                               fee_map: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Skill Assessment line(s) for one occupation — multi-component aware.
    Priority: per-batch override → Fee Master components → batch fallback fee → 0."""
    batch_defaults = batch_defaults or {}
    if fee_map is None:
        fee_map = await _fee_master_map()
    name, key = "Assessing Authority", "unknown"
    if anzsco_code:
        occ = await OCCUPATION_MASTER.find_one(
            {"country_code": "AU", "code": anzsco_code}, {"_id": 0, "assessing_authority": 1},
        )
        auth = (occ or {}).get("assessing_authority")
        if auth:
            key, name = _canon_auth_key(auth), _auth_display_name(auth)

    comps: List[Dict[str, Any]] = []
    disp = name
    override = (batch_defaults.get("skill_fees") or {}).get(key)
    if override:
        comps = _fee_components_of(override)
        disp = override.get("authority_name") or name
    if not comps:
        fm = fee_map.get(key) or {}
        comps = fm.get("components") or []
        disp = fm.get("authority_name") or name

    def _line(suffix, amount, ccy):
        return {"category": "Skill Assessment",
                "label": f"{disp} — {suffix}", "amount": amount, "currency": ccy,
                "is_estimated": True, "is_editable": True}

    if comps:
        multi = len(comps) > 1
        return [_line(c["label"] if multi else "Skill Assessment", c["amount"], c.get("currency", "INR"))
                for c in comps]
    fb = batch_defaults.get("fallback_skill_fee") or {}
    if fb.get("amount") not in (None, ""):
        return [_line("Skill Assessment", float(fb["amount"]), fb.get("currency") or "INR")]
    return [_line("Skill Assessment", 0, "INR")]


async def _bulk_common_items(visa_subclass: str = "189") -> List[Dict[str, Any]]:
    """Non-occupation-specific cost lines: govt visa, English, LEAMSS fee, protection, medical, PCC.
    (Skill Assessment is intentionally excluded — it is resolved per occupation.)"""
    items = await _kb_cost_defaults("AU", visa_subclass, None)
    VISA_FEE_AUD = 4640  # DHA indicative principal-applicant charge (189/190/491), editable
    gov = next((it for it in items if it.get("category") == "Government Fees"), None)
    if gov is None:
        items.insert(0, {"category": "Government Fees",
                         "label": f"Visa Application Fee — Subclass {visa_subclass}",
                         "amount": VISA_FEE_AUD, "currency": "AUD",
                         "is_estimated": True, "is_editable": True})
    elif not gov.get("amount"):
        gov["amount"] = VISA_FEE_AUD
        gov["currency"] = gov.get("currency") or "AUD"
    items.append({"category": "Medical Tests", "label": "Health Examination (BUPA panel)",
                  "amount": 7000, "currency": "INR", "is_estimated": True, "is_editable": True})
    items.append({"category": "Police Clearance", "label": "PCC (per applicant)",
                  "amount": 1500, "currency": "INR", "is_estimated": True, "is_editable": True})
    return items


def _totals(items: List[Dict[str, Any]]) -> Dict[str, float]:
    tbc: Dict[str, float] = {}
    for it in items:
        cur = it.get("currency", "INR")
        tbc[cur] = tbc.get(cur, 0) + (it.get("amount") or 0)
    return tbc


async def _patch_override_skill_fee(cost_override: Dict[str, Any], anzsco_code: Optional[str],
                                    batch_defaults: Dict[str, Any],
                                    fee_map: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Refresh ONLY the Skill Assessment line(s) inside an individually-edited client's cost
    override (preserving all their other manual edits), now multi-component aware."""
    ce = {**(cost_override or {})}
    items = [dict(it) for it in (ce.get("items") or []) if it.get("category") != "Skill Assessment"]
    items.extend(await _resolve_skill_lines(anzsco_code, batch_defaults, fee_map))
    ce["items"] = items
    ce["total_by_currency"] = _totals(items)
    return ce


async def _build_bulk_cost_estimator(anzsco_code: Optional[str], visa_subclass: str,
                                     batch_defaults: Optional[Dict[str, Any]] = None,
                                     fee_map: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Cost estimator for a bulk report.

    Skill Assessment fee(s) come from the admin Fee Master per the occupation's assessing
    authority (multi-component aware, e.g. TRA = Document Evidence + Technical + Practical),
    with the batch fallback fee covering any authority not yet set. Common items + LEAMSS
    packages come from the batch defaults when set, else from verified KB defaults.
    """
    if fee_map is None:
        fee_map = await _fee_master_map()

    if batch_defaults:
        items = [dict(it) for it in (batch_defaults.get("common_items") or [])]
        items.extend(await _resolve_skill_lines(anzsco_code, batch_defaults, fee_map))
        packages = [dict(p) for p in (batch_defaults.get("service_packages") or _leamss_service_packages("AU"))]
        return {
            "currency": "INR",
            "items": items,
            "service_packages": packages,
            "total_by_currency": _totals(items),
            "notes": batch_defaults.get("notes") or "Batch default costs & packages applied.",
        }

    items = await _bulk_common_items(visa_subclass)
    items.extend(await _resolve_skill_lines(anzsco_code, None, fee_map))
    return {
        "currency": "INR",
        "items": items,
        "service_packages": _leamss_service_packages("AU"),
        "total_by_currency": _totals(items),
        "notes": "Auto-filled from Fee Master + verified KB defaults — edit per client if needed.",
    }


async def _compose_bulk_cost_estimator(row: Dict[str, Any], batch: Dict[str, Any],
                                       anzsco_code: Optional[str], visa_subclass: str,
                                       fee_map: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Final cost estimator for a client's report.

    ALWAYS starts from the batch-wide base (common items like Government/English/Medical/PCC
    + skill lines + service packages) so batch-level costs are never lost — even for clients
    that were individually edited. Any per-client `cost_override` is then LAYERED on top:
      • edits to a common line (matched by category+label) win
      • per-client Skill Assessment lines (if the override has any) win over resolved ones
      • extra custom lines the consultant added are appended
      • per-client service-package edits win
    """
    base = await _build_bulk_cost_estimator(anzsco_code, visa_subclass, batch.get("cost_defaults"), fee_map)
    override = row.get("cost_override")
    if not override:
        return base

    base_items = [dict(it) for it in (base.get("items") or [])]
    non_skill_base = [it for it in base_items if it.get("category") != "Skill Assessment"]
    skill_base = [it for it in base_items if it.get("category") == "Skill Assessment"]
    index = {(it.get("category"), (it.get("label") or "").strip()): it for it in non_skill_base}

    ov_items = override.get("items") or []
    ov_skill = [dict(it) for it in ov_items if it.get("category") == "Skill Assessment"]
    extras: List[Dict[str, Any]] = []
    for ov in ov_items:
        if ov.get("category") == "Skill Assessment":
            continue
        key = (ov.get("category"), (ov.get("label") or "").strip())
        if key in index:
            index[key]["amount"] = ov.get("amount")
            index[key]["currency"] = ov.get("currency") or index[key].get("currency")
        else:
            extras.append(dict(ov))

    skill_lines = ov_skill if ov_skill else skill_base
    items = non_skill_base + skill_lines + extras
    ov_pkgs = override.get("service_packages")
    packages = ov_pkgs if ov_pkgs else base.get("service_packages")
    return {
        "currency": "INR",
        "items": items,
        "service_packages": packages,
        "total_by_currency": _totals(items),
        "notes": override.get("notes") or base.get("notes"),
    }


async def _generate_row(row: Dict[str, Any], batch: Dict[str, Any], user: Dict[str, Any]) -> bool:
    p = row["parsed"]
    profile = _profile_from_parsed(p)

    # Points for all 3 subclasses (shown in the all-pathways table + summary)
    r189 = await calculate_with_rules(db, profile, "AU", "189")
    base = int(r189.get("total") or 0)
    points = {"189": base, "190": base + 5, "491": base + 15}

    # ONE representative country target = least-restrictive subclass they qualify for
    # (prevents the Country section repeating once per subclass). Falls back to 491.
    best_sc = next((sc for sc in ("189", "190", "491") if points[sc] >= 65), "491")
    best_result = await calculate_with_rules(db, profile, "AU", best_sc)
    targets = [{"country": "AU", "visa_subclass": best_sc}]
    results = [best_result]
    best = best_result

    # Eligibility verdict — a consultant's MANUAL override wins over the auto classification.
    manual = row.get("manual_eligibility")
    if manual and manual.get("kind") in ("improvable", "ineligible"):
        eligibility = manual_verdict(manual.get("kind"), manual.get("reason"), p, points)
    else:
        eligibility = classify_eligibility(p, points)

    # Cost estimator: batch-wide base (common + skill + packages) with any per-client override layered on top.
    cost_estimator = await _compose_bulk_cost_estimator(
        row, batch, p.get("anzsco_code"), best_sc, batch.get("_fee_map"),
    )

    now = datetime.now(timezone.utc)
    assessment_id = row.get("assessment_id") or f"SAH-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    # Alternate ANZSCO pathways for the report's comparison page (primary + up to 2 alternates).
    # Prefer consultant-curated codes; else fall back to the AI's suggested alternatives.
    additional_occupations: List[Dict[str, Any]] = []
    seen_codes = {str(p.get("anzsco_code") or "")}
    alt_source = p.get("report_alt_codes")
    if alt_source is None:
        alt_source = p.get("ai_alternatives") or []
    for alt in alt_source:
        acode = str((alt or {}).get("code") or "").strip()
        if not acode or acode in seen_codes:
            continue
        occ_alt = await OCCUPATION_MASTER.find_one(
            {"country_code": "AU", "code": acode}, {"_id": 0, "title": 1})
        if occ_alt:
            additional_occupations.append({
                "country_code": "AU", "code": acode,
                "title": occ_alt.get("title") or alt.get("title"), "assessing_body": None,
            })
            seen_codes.add(acode)
        if len(additional_occupations) >= 2:
            break

    doc = {
        "id": assessment_id,
        "client_name": p["name"],
        "client_email": p.get("email"),
        "client_phone": p.get("phone"),
        "profile_snapshot": profile,
        "occupation": {
            "country_code": "AU", "code": p["anzsco_code"], "title": p.get("occupation_title"),
            "assessing_body": None, "pathway": None,
        } if p.get("anzsco_code") else None,
        "additional_occupations": additional_occupations,
        "ai_occupation_match": ({
            "source": "resume",
            "confidence": p.get("ai_confidence"),
            "reviewed": bool(p.get("ai_reviewed")),
        } if p.get("anzsco_source") == "ai" else None),
        "show_eoi_backlog": bool(batch.get("show_eoi_backlog")) and not bool(p.get("hide_eoi")),
        "cost_estimator": cost_estimator,
        "targets": targets,
        "results": results,
        "best_country_code": "AU",
        "best_total": best.get("total") if best else None,
        "resume_link": p.get("resume_link"),
        "gender": p.get("gender"),
        "source_batch_id": batch["id"],
        "created_by": user["id"],
        "created_by_name": user.get("name"),
        "created_at": now,
        "updated_at": now,
    }
    await ASSESSMENTS.replace_one({"id": assessment_id}, doc, upsert=True)

    # Build report snapshot + render PDF
    snap_data = await _build_snapshot(doc, persona="client", mode="combined", include_unverified=False)
    snapshot_id = f"RPT-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    await REPORT_SNAPSHOTS.insert_one({
        "snapshot_id": snapshot_id, "assessment_id": assessment_id, "client_name": p["name"],
        "persona": "client", "mode": "combined", "data": snap_data,
        "data_integrity_hash": snap_data.get("data_integrity_hash"),
        "generated_at": now, "generated_by": user["id"], "is_immutable": True,
    })
    snap_data["snapshot_id"] = snapshot_id
    snap_data["eligibility_verdict"] = eligibility
    pdf_bytes = render_pdf_v2(snap_data)

    # Store PDF in GridFS (replace any previous for this row)
    if row.get("pdf_file_id"):
        try:
            await _gridfs.delete(ObjectId(row["pdf_file_id"]))
        except Exception:
            pass
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", p["name"])[:40]
    file_id = await _gridfs.upload_from_stream(
        f"{safe}_{assessment_id}.pdf", io.BytesIO(pdf_bytes),
        metadata={"batch_id": batch["id"], "row_id": row["id"], "client_name": p["name"]},
    )

    await ROWS.update_one({"id": row["id"]}, {"$set": {
        "status": "generated", "assessment_id": assessment_id, "snapshot_id": snapshot_id,
        "pdf_file_id": str(file_id), "points": points, "cost_estimator": cost_estimator,
        "eligibility": eligibility, "generated_at": now,
    }})
    return True


async def _run_batch(batch_id: str, user: Dict[str, Any]):
    batch = await BATCHES.find_one({"id": batch_id})
    if not batch:
        return
    await BATCHES.update_one({"id": batch_id}, {"$set": {"status": "generating", "generated": 0, "failed": 0}})
    batch["_fee_map"] = await _fee_master_map(force=True)  # load Fee Master once for the whole run
    # Re-validate previously-errored rows — rules may have relaxed (e.g. age 45+ is no longer a hard
    # block; it now produces a Not-Eligible report instead). Rows that recover become generatable.
    err_rows = await ROWS.find({"batch_id": batch_id, "status": "error"}, {"_id": 0}).to_list(100000)
    for er in err_rows:
        st, errs = _revalidate_row(er.get("parsed") or {})
        if st != "error":
            await ROWS.update_one({"id": er["id"]}, {"$set": {"status": st, "errors": errs}})
    generated = 0
    failed = 0
    cursor = ROWS.find({"batch_id": batch_id, "status": {"$in": ["valid", "generated", "failed"]}})
    rows = await cursor.to_list(length=100000)
    for row in rows:
        if row["status"] == "error":
            continue
        try:
            await _generate_row(row, batch, user)
            generated += 1
        except Exception as e:
            failed += 1
            await ROWS.update_one({"id": row["id"]}, {"$set": {"status": "failed", "gen_error": str(e)[:300]}})
        await BATCHES.update_one({"id": batch_id}, {"$set": {"generated": generated, "failed": failed}})
    await BATCHES.update_one({"id": batch_id}, {"$set": {"status": "done", "generated": generated, "failed": failed,
                                                         "completed_at": datetime.now(timezone.utc)}})


@router.patch("/{batch_id}/settings")
async def update_batch_settings(
    batch_id: str,
    show_eoi_backlog: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    batch = await BATCHES.find_one({"id": batch_id}, {"_id": 0})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    updates = {}
    if show_eoi_backlog is not None:
        updates["show_eoi_backlog"] = show_eoi_backlog
    if updates:
        await BATCHES.update_one({"id": batch_id}, {"$set": updates})
    b = await BATCHES.find_one({"id": batch_id}, {"_id": 0})
    return {"ok": True, "batch": b}


# ─────────────────────────────────────────────────────────────
# Batch-wide cost & package defaults ("Set Batch Defaults")
# ─────────────────────────────────────────────────────────────
class CostDefaultsRequest(BaseModel):
    common_items: List[Dict[str, Any]] = []
    service_packages: List[Dict[str, Any]] = []
    skill_fees: Dict[str, Dict[str, Any]] = {}      # canon_key -> {authority_name, amount, currency}
    fallback_skill_fee: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    save_to_master: bool = True
    regenerate: bool = True


@router.get("/{batch_id}/cost-defaults-template")
async def cost_defaults_template(batch_id: str, current_user: dict = Depends(get_current_user)):
    """Seed for the "Set Batch Defaults" modal: common cost lines, LEAMSS packages, and the
    DISTINCT assessing authorities present in THIS batch (with known fees pre-filled)."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    batch = await BATCHES.find_one({"id": batch_id}, {"_id": 0})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    existing = batch.get("cost_defaults") or {}
    base_items = existing.get("common_items") or await _bulk_common_items("189")
    packages = existing.get("service_packages") or _leamss_service_packages("AU")

    rows = await ROWS.find({"batch_id": batch_id}, {"_id": 0, "parsed": 1}).to_list(100000)
    codes = {(r.get("parsed") or {}).get("anzsco_code") for r in rows if (r.get("parsed") or {}).get("anzsco_code")}
    code_to_auth: Dict[str, Any] = {}
    for code in codes:
        occ = await OCCUPATION_MASTER.find_one(
            {"country_code": "AU", "code": code}, {"_id": 0, "assessing_authority": 1},
        )
        code_to_auth[code] = (occ or {}).get("assessing_authority")

    fee_map = await _fee_master_map()
    saved_fees = existing.get("skill_fees") or {}
    auth_map: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        code = (r.get("parsed") or {}).get("anzsco_code")
        auth = code_to_auth.get(code)
        key = _canon_auth_key(auth) if auth else "unknown"
        name = _auth_display_name(auth) if auth else "Unknown / Not set"
        if key not in auth_map:
            fm = fee_map.get(key)
            comps = (saved_fees.get(key) or {}).get("components") or (fm or {}).get("components") or []
            auth_map[key] = {
                "key": key,
                "authority_name": (saved_fees.get(key) or {}).get("authority_name") or (fm or {}).get("authority_name") or name,
                "count": 0,
                "components": comps,
                "total_by_currency": _totals(comps),
                "matched": bool(comps),
            }
        auth_map[key]["count"] += 1
    authorities = sorted(auth_map.values(), key=lambda x: -x["count"])

    return {
        "common_items": base_items,
        "service_packages": packages,
        "authorities": authorities,
        "fallback_skill_fee": existing.get("fallback_skill_fee") or {"amount": None, "currency": "INR"},
        "notes": existing.get("notes") or "",
        "has_defaults": bool(existing),
        "total_clients": len(rows),
    }


@router.put("/{batch_id}/cost-defaults")
async def set_cost_defaults(batch_id: str, req: CostDefaultsRequest,
                            current_user: dict = Depends(get_current_user)):
    """Save batch-wide cost + package defaults, optionally persist filled fees to the master,
    patch the Skill Assessment line on individually-edited clients, and regenerate."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    batch = await BATCHES.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.get("status") == "generating":
        raise HTTPException(status_code=400, detail="Batch is already generating")

    cost_defaults = {
        "common_items": req.common_items,
        "service_packages": req.service_packages,
        "skill_fees": req.skill_fees or {},
        "fallback_skill_fee": req.fallback_skill_fee or {"amount": None, "currency": "INR"},
        "notes": req.notes or "",
        "set_at": datetime.now(timezone.utc),
    }
    await BATCHES.update_one({"id": batch_id}, {"$set": {"cost_defaults": cost_defaults}})

    # Grow the Fee Master for any authority the consultant filled here (multi-component aware).
    if req.save_to_master:
        for key, entry in (req.skill_fees or {}).items():
            if key in (None, "", "unknown"):
                continue
            comps = _fee_components_of(entry or {})
            if not comps:
                continue
            await FEE_OVERRIDES.update_one({"key": key}, {"$set": {
                "key": key,
                "authority_name": (entry or {}).get("authority_name"),
                "components": comps,
                "updated_at": datetime.now(timezone.utc),
                "updated_by": current_user.get("id"),
            }, "$unset": {"amount": "", "currency": ""}}, upsert=True)
    fee_map = await _fee_master_map(force=True)

    # Individually-edited clients: refresh ONLY their Skill Assessment line(s), keep the rest.
    edited = await ROWS.find(
        {"batch_id": batch_id, "cost_override": {"$exists": True, "$ne": None}}, {"_id": 0},
    ).to_list(100000)
    for r in edited:
        patched = await _patch_override_skill_fee(
            r["cost_override"], (r.get("parsed") or {}).get("anzsco_code"), cost_defaults, fee_map,
        )
        await ROWS.update_one({"id": r["id"]}, {"$set": {"cost_override": patched}})

    regenerating = False
    if req.regenerate:
        valid = await ROWS.count_documents(
            {"batch_id": batch_id, "status": {"$in": ["valid", "generated", "failed"]}},
        )
        if valid > 0:
            await BATCHES.update_one({"id": batch_id}, {"$set": {"status": "generating", "generated": 0, "failed": 0}})
            user = {"id": current_user["id"], "name": current_user.get("name") or current_user.get("email")}
            asyncio.create_task(_run_batch(batch_id, user))
            regenerating = True

    return {"ok": True, "edited_patched": len(edited), "regenerating": regenerating,
            "fees_saved_to_master": req.save_to_master}



@router.post("/{batch_id}/generate")
async def start_generate(batch_id: str, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    batch = await BATCHES.find_one({"id": batch_id}, {"_id": 0})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.get("status") == "generating":
        raise HTTPException(status_code=400, detail="Batch is already generating")
    valid = await ROWS.count_documents({"batch_id": batch_id, "status": {"$in": ["valid", "generated", "failed"]}})
    if valid == 0:
        raise HTTPException(status_code=400, detail="No valid rows to generate")
    user = {"id": current_user["id"], "name": current_user.get("name") or current_user.get("email")}
    asyncio.create_task(_run_batch(batch_id, user))
    return {"ok": True, "batch_id": batch_id, "queued": valid}


# ─────────────────────────────────────────────────────────────
# Status / list / rows
# ─────────────────────────────────────────────────────────────
@router.get("")
async def list_batches(current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    items = await BATCHES.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return {"batches": items}


@router.get("/email-config")
async def email_config(current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    configured = gmail_is_configured()
    senders = await MAIL_SENDERS.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    return {
        "configured": configured,
        "method": "domain_wide_delegation",
        "default_sender": gmail_default_sender(),
        "domain": gmail_domain(),
        "sa_client_id": gmail_sa_client_id(),
        "sa_client_email": gmail_sa_client_email(),
        "scope": "https://www.googleapis.com/auth/gmail.send",
        "remaining_today": (await gmail_remaining()) if configured else 0,
        "senders": senders,
    }


class MailSenderRequest(BaseModel):
    name: str
    email: str
    active: bool = True


@router.get("/mail-senders")
async def list_mail_senders(current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    return await MAIL_SENDERS.find({}, {"_id": 0}).sort("name", 1).to_list(1000)


@router.post("/mail-senders")
async def add_mail_sender(req: MailSenderRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    email = (req.email or "").strip().lower()
    name = (req.name or "").strip()
    if "@" not in email or not name:
        raise HTTPException(status_code=400, detail="A valid name and email are required.")
    if await MAIL_SENDERS.find_one({"email": email}):
        raise HTTPException(status_code=400, detail=f"{email} is already in the mailbox list.")
    dom = gmail_domain()
    domain_ok = (not dom) or email.endswith("@" + dom)
    doc = {
        "id": str(uuid.uuid4()), "name": name, "email": email, "active": bool(req.active),
        "domain_ok": domain_ok, "created_at": datetime.now(timezone.utc), "created_by": current_user.get("email"),
    }
    await MAIL_SENDERS.insert_one(dict(doc))
    doc.pop("_id", None)
    return {"ok": True, "sender": {k: v for k, v in doc.items() if k != "created_at"}, "domain_warning": (not domain_ok)}


@router.patch("/mail-senders/{sender_id}")
async def update_mail_sender(sender_id: str, req: dict, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    updates = {}
    if "name" in req and req["name"]:
        updates["name"] = str(req["name"]).strip()
    if "active" in req:
        updates["active"] = bool(req["active"])
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update.")
    res = await MAIL_SENDERS.update_one({"id": sender_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Mailbox not found.")
    return {"ok": True}


@router.delete("/mail-senders/{sender_id}")
async def delete_mail_sender(sender_id: str, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    await MAIL_SENDERS.delete_one({"id": sender_id})
    return {"ok": True}


@router.get("/{batch_id}")
async def get_batch(batch_id: str, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    batch = await BATCHES.find_one({"id": batch_id}, {"_id": 0})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    rows = await ROWS.find({"batch_id": batch_id}, {"_id": 0}).sort("row_index", 1).to_list(100000)
    return {"batch": batch, "rows": rows}


# ─────────────────────────────────────────────────────────────
# Phase B — per-row edit + regenerate
# ─────────────────────────────────────────────────────────────
class RowEditRequest(BaseModel):
    anzsco_code: Optional[str] = None
    age: Optional[int] = None
    qualification: Optional[str] = None
    experience_total: Optional[float] = None
    experience_au: Optional[float] = None
    marital_status: Optional[str] = None
    english: Optional[Dict[str, float]] = None
    state_nominated: Optional[bool] = None
    spouse: Optional[Dict[str, Any]] = None
    partner_skill: Optional[str] = None  # dropdown: pr_citizen | skilled | english_only | none
    au_extras: Optional[Dict[str, Any]] = None  # study/STEM/PY/NAATI/regional bonus toggles
    show_eoi_backlog: Optional[bool] = None
    mark_reviewed: Optional[bool] = None  # confirm an AI-suggested ANZSCO
    report_alt_codes: Optional[List[str]] = None  # alternate ANZSCO pathways to show on the report
    hide_eoi: Optional[bool] = None  # per-client: hide EOI backlog tables on THIS client's report
    consultant_email: Optional[str] = None  # mailbox this client's report is emailed FROM ("" clears)
    cost_estimator: Optional[Dict[str, Any]] = None  # per-client cost + LEAMSS packages override


@router.patch("/row/{row_id}")
async def edit_row(row_id: str, req: RowEditRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    row = await ROWS.find_one({"id": row_id})
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    batch = await BATCHES.find_one({"id": row["batch_id"]})
    p = dict(row["parsed"])

    # Apply edits
    if req.anzsco_code is not None:
        code = re.sub(r"\.0$", "", str(req.anzsco_code).strip())
        occ = await OCCUPATION_MASTER.find_one({"country_code": "AU", "code": code}, {"_id": 0, "title": 1})
        if not occ:
            raise HTTPException(status_code=400, detail=f"ANZSCO {code} not in Occupation Master (AU)")
        p["anzsco_code"] = code
        p["occupation_title"] = occ.get("title")
        p["ai_reviewed"] = True  # consultant explicitly set/confirmed the code
    if req.age is not None:
        p["age"] = req.age
    if req.qualification is not None:
        p["qualification"] = req.qualification
    if req.experience_total is not None:
        p["experience_total"] = req.experience_total
    if req.experience_au is not None:
        p["experience_au"] = req.experience_au
    if req.marital_status is not None:
        p["marital_status"] = req.marital_status
    if req.english is not None:
        p["english"] = {**p.get("english", DEFAULT_ENGLISH), **req.english}
    if req.state_nominated is not None:
        p["state_nominated"] = req.state_nominated
    if req.au_extras is not None:
        p["au_extras"] = {**(p.get("au_extras") or {}), **req.au_extras}
    if req.partner_skill is not None:
        p["partner_skill"] = req.partner_skill
        p["spouse_override"] = _spouse_from_partner_skill(req.partner_skill)
    elif req.spouse is not None:
        p["spouse_override"] = req.spouse
    if req.mark_reviewed:
        p["ai_reviewed"] = True

    # Consultant-curated alternate ANZSCO pathways for the report comparison page (max 2)
    if req.report_alt_codes is not None:
        alts: List[Dict[str, Any]] = []
        primary = str(p.get("anzsco_code") or "")
        for ac in req.report_alt_codes[:2]:
            ac = re.sub(r"\.0$", "", str(ac).strip())
            if not ac or ac == primary or any(a["code"] == ac for a in alts):
                continue
            oc = await OCCUPATION_MASTER.find_one({"country_code": "AU", "code": ac}, {"_id": 0, "title": 1})
            if oc:
                alts.append({"code": ac, "title": oc.get("title")})
        p["report_alt_codes"] = alts

    if req.hide_eoi is not None:
        p["hide_eoi"] = bool(req.hide_eoi)

    if req.consultant_email is not None:
        ce = req.consultant_email.strip().lower() or None
        cn = None
        if ce:
            s = await MAIL_SENDERS.find_one({"email": ce})
            cn = (s or {}).get("name")
        p["consultant_email"] = ce
        p["consultant_name"] = cn

    await ROWS.update_one({"id": row_id}, {"$set": {"parsed": p, "status": "valid", "errors": []}})
    if req.cost_estimator is not None:
        await ROWS.update_one({"id": row_id}, {"$set": {"cost_override": req.cost_estimator}})
    if req.show_eoi_backlog is not None:
        await BATCHES.update_one({"id": row["batch_id"]}, {"$set": {"show_eoi_backlog": req.show_eoi_backlog}})
        batch = await BATCHES.find_one({"id": row["batch_id"]})

    row = await ROWS.find_one({"id": row_id})
    user = {"id": current_user["id"], "name": current_user.get("name") or current_user.get("email")}
    try:
        await _generate_row(row, batch, user)
    except Exception as e:
        await ROWS.update_one({"id": row_id}, {"$set": {"status": "failed", "gen_error": str(e)[:300]}})
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {e}")
    updated = await ROWS.find_one({"id": row_id}, {"_id": 0})
    return {"ok": True, "row": updated}


@router.post("/{batch_id}/row/{row_id}/confirm-ai")
async def confirm_ai_row(batch_id: str, row_id: str, current_user: dict = Depends(get_current_user)):
    """Mark an AI-suggested ANZSCO as reviewed/confirmed (no code change, no regeneration)."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    row = await ROWS.find_one({"id": row_id, "batch_id": batch_id})
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    p = dict(row["parsed"])
    p["ai_reviewed"] = True
    await ROWS.update_one({"id": row_id}, {"$set": {"parsed": p}})
    return {"ok": True, "row_id": row_id, "reviewed": True}


@router.post("/{batch_id}/confirm-all-ai")
async def confirm_all_ai(batch_id: str, current_user: dict = Depends(get_current_user)):
    """Mark ALL pending AI-suggested ANZSCO rows in the batch as reviewed/confirmed in one go."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not await BATCHES.find_one({"id": batch_id}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Batch not found")
    res = await ROWS.update_many(
        {"batch_id": batch_id, "parsed.anzsco_source": "ai", "parsed.ai_reviewed": {"$ne": True}},
        {"$set": {"parsed.ai_reviewed": True}},
    )
    return {"ok": True, "reviewed": res.modified_count}


# ─────────────────────────────────────────────────────────────
# Manual resume upload + serve + AI code suggestions (per client)
# ─────────────────────────────────────────────────────────────
@router.post("/row/{row_id}/upload-resume")
async def upload_resume(row_id: str, file: UploadFile = File(...),
                        current_user: dict = Depends(get_current_user)):
    """Upload a resume file for one client (for private/scanned/missing links), extract text
    (with OCR fallback), auto-detect ANZSCO + fill missing fields, and store the file so it
    can be re-viewed. Does NOT auto-generate the report (consultant reviews then saves)."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    row = await ROWS.find_one({"id": row_id})
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 15 MB)")

    # Replace any previously uploaded resume for this row
    p = dict(row["parsed"])
    if p.get("resume_file_id"):
        try:
            await _resume_gridfs.delete(ObjectId(p["resume_file_id"]))
        except Exception:
            pass
    file_id = await _resume_gridfs.upload_from_stream(
        file.filename or f"resume-{row_id}",
        io.BytesIO(content),
        metadata={"contentType": file.content_type or "application/octet-stream", "row_id": row_id},
    )
    p["resume_file_id"] = str(file_id)
    p["resume_filename"] = file.filename
    p["resume_uploaded"] = True

    text, err = await extract_text_smart(file.filename or "upload.pdf", content)
    if err or not text:
        await ROWS.update_one({"id": row_id}, {"$set": {"parsed": p, "status": "needs_ai",
                                                         "ai_error": err or "Could not read the uploaded file"}})
        updated = await ROWS.find_one({"id": row_id}, {"_id": 0})
        return {"ok": False, "error": err or "Could not read the uploaded file", "row": updated}

    res = await _enrich_from_text(p, text)
    await ROWS.update_one({"id": row_id}, {"$set": {
        "status": res["status"], "parsed": res["parsed"],
        "errors": res.get("errors", []), "ai_error": res.get("ai_error"),
    }})
    updated = await ROWS.find_one({"id": row_id}, {"_id": 0})
    return {"ok": res["status"] == "valid", "row": updated,
            "detected_code": res["parsed"].get("anzsco_code"),
            "alternatives": res["parsed"].get("ai_alternatives") or [],
            "ai_error": res.get("ai_error")}


@router.get("/row/{row_id}/resume-file")
async def get_resume_file(row_id: str, current_user: dict = Depends(get_current_user)):
    """Stream a manually-uploaded resume back for viewing."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    row = await ROWS.find_one({"id": row_id})
    if not row or not (row.get("parsed") or {}).get("resume_file_id"):
        raise HTTPException(status_code=404, detail="No uploaded resume for this client")
    p = row["parsed"]
    stream = await _resume_gridfs.open_download_stream(ObjectId(p["resume_file_id"]))
    data = await stream.read()
    ct = (stream.metadata or {}).get("contentType") or "application/octet-stream"
    return StreamingResponse(io.BytesIO(data), media_type=ct, headers={
        "Content-Disposition": f'inline; filename="{p.get("resume_filename") or "resume"}"',
    })


class SuggestCodesRequest(BaseModel):
    query: Optional[str] = None  # free-text job title / description; else uses stored resume


@router.post("/row/{row_id}/suggest-codes")
async def suggest_codes(row_id: str, req: SuggestCodesRequest,
                        current_user: dict = Depends(get_current_user)):
    """Return the best ANZSCO match + alternative codes for a client — from a typed job title,
    or (if none given) by reading the client's resume. Powers the manual code helper."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    row = await ROWS.find_one({"id": row_id})
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    p = row.get("parsed") or {}

    desc = (req.query or "").strip()
    source = "query"
    if not desc:
        # Read the resume: uploaded file first, else the link
        text = None
        if p.get("resume_file_id"):
            try:
                stream = await _resume_gridfs.open_download_stream(ObjectId(p["resume_file_id"]))
                data = await stream.read()
                text, _ = await extract_text_smart(p.get("resume_filename") or "resume.pdf", data)
            except Exception:
                text = None
        if not text and p.get("resume_link"):
            text, _ = await fetch_resume_text(p.get("resume_link"))
        if not text:
            raise HTTPException(status_code=400, detail="No job title given and no readable resume to analyse")
        profile = await parse_resume_with_ai(text, model=BULK_PARSE_MODEL)
        desc = build_description(profile) if not profile.get("_error") else text[:1500]
        source = "resume"

    match = await match_anzsco(db, desc)
    if match.get("_error"):
        raise HTTPException(status_code=400, detail=match["_error"])
    best = match.get("best") or {}
    alts = match.get("alternatives") or []
    # Enrich each suggestion with the official title from Occupation Master
    async def _title(code):
        if not code:
            return None
        o = await OCCUPATION_MASTER.find_one({"country_code": "AU", "code": str(code)}, {"_id": 0, "title": 1})
        return (o or {}).get("title")
    suggestions = []
    for s in ([best] + alts):
        c = s.get("code")
        if not c:
            continue
        suggestions.append({"code": str(c), "title": s.get("title") or await _title(c),
                            "confidence": s.get("confidence"), "reasoning": s.get("reasoning")})
    return {"ok": True, "source": source, "suggestions": suggestions}



# ─────────────────────────────────────────────────────────────
# Email reports to clients — from the consultant's own Gmail (rohit@leamss.com)
# ─────────────────────────────────────────────────────────────
async def _read_pdf_bytes(file_id: str) -> bytes:
    buf = io.BytesIO()
    await _gridfs.download_to_stream(ObjectId(file_id), buf)
    return buf.getvalue()


def _report_filename(name: str, assessment_id: Optional[str]) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", name or "Client")[:40]
    return f"{safe}_PreAssessment{('_' + assessment_id) if assessment_id else ''}.pdf"


async def _email_context(row: Dict[str, Any], settings: Dict[str, Any], upload_url: Optional[str] = None) -> Dict[str, Any]:
    """Placeholder context for user-authored email templates."""
    p = row.get("parsed") or {}
    ev = row.get("eligibility") or classify_eligibility(p, row.get("points") or {})
    sender_name = (p.get("consultant_name") or "").strip() or "Ladhani Education & Migration Services"
    return {
        "client_name": " ".join((p.get("name") or "Applicant").split()),
        "occupation": p.get("occupation_title") or "",
        "code": p.get("anzsco_code") or "",
        "points": ev.get("best_points") or 0,
        "best_subclass": ev.get("best_subclass") or "",
        "pass_mark": ev.get("pass_mark") or 65,
        "reasons": ev.get("reasons") or [],
        "improvements": ev.get("improvements") or [],
        "alternatives": ev.get("alternatives") or [],
        "upload_link": upload_url or "",
        "consultant_name": sender_name,
        "calendly_link": settings.get("calendly_link") or "",
        "offer_badge": settings.get("offer_badge") or "",
        "offer_price": settings.get("offer_price") or "",
        "offer_regular_fee": settings.get("offer_regular_fee") or "",
        "offer_savings": settings.get("offer_savings") or "",
        "offer_valid_till": settings.get("offer_valid_till") or "",
        "payment_link": settings.get("payment_link") or "",
        "upi_id": settings.get("upi_id") or "",
        "company": "LEAMSS",
        "phone": settings.get("contact_phone") or "+91 77188 82427",
        "email": settings.get("contact_email") or "info@leamss.com",
        "website": settings.get("website") or "www.leamss.com",
    }


async def _load_template(template_id: Optional[str], category: Optional[str]) -> Optional[Dict[str, Any]]:
    """Explicit template by id → else the category default (is_default) → else None (built-in fallback)."""
    coll = db["email_templates"]
    if template_id:
        t = await coll.find_one({"id": template_id})
        if t:
            t.pop("_id", None)
            return t
    if category:
        t = await coll.find_one({"category": category, "is_default": True})
        if t:
            t.pop("_id", None)
            return t
    return None


async def _send_row_with_template(row: Dict[str, Any], to: str, template: Dict[str, Any],
                                  bcc_self: bool, upload_url: Optional[str] = None) -> Dict[str, Any]:
    from routers.email_settings import get_settings
    from core.report_email import render_custom_email
    s = await get_settings()
    p = row.get("parsed") or {}
    sender_email = (p.get("consultant_email") or gmail_default_sender() or "").strip().lower()
    sender_name = (p.get("consultant_name") or "").strip() or "Ladhani Education & Migration Services"
    ctx = await _email_context(row, s, upload_url=upload_url)
    subject, html, plain = render_custom_email(template, ctx, sender_name=sender_name, settings=s)
    attachments: List[Dict[str, Any]] = []
    if template.get("attach_report") and row.get("pdf_file_id"):
        attachments.append({
            "bytes": await _read_pdf_bytes(row["pdf_file_id"]),
            "filename": _report_filename(p.get("name"), row.get("assessment_id")),
            "maintype": "application", "subtype": "pdf",
        })
    await gmail_send(sender_email=sender_email, sender_name=sender_name, recipient=to,
                     subject=subject, html=html, plain=plain, attachments=attachments,
                     bcc=(sender_email if bcc_self else None))
    return {"sender_email": sender_email, "template": template.get("name")}


async def _send_row_auto(row: Dict[str, Any], to: str, bcc_self: bool,
                         template_id: Optional[str] = None) -> Dict[str, Any]:
    """Unified per-row sender. Picks the right email for the client's bucket, honouring a chosen
    template (or the category default), else falling back to the built-in default builders."""
    bucket = bucket_for_row(row)
    category = {"eligible": "eligible", "improvable": "not_eligible",
                "ineligible": "not_eligible", "needs_resume": "resume"}.get(bucket, "eligible")
    upload_url = None
    if bucket == "needs_resume":
        token = row.get("resume_token")
        if not token:
            token = uuid.uuid4().hex
            await ROWS.update_one({"id": row["id"]}, {"$set": {"resume_token": token}})
        upload_url = _resume_upload_url(token)

    template = await _load_template(template_id, category)
    if template:
        meta = await _send_row_with_template(row, to, template, bcc_self, upload_url=upload_url)
        meta["kind"] = bucket
        return meta
    # Built-in fallbacks
    if bucket == "needs_resume":
        meta = await _email_resume_request_row(row, to, bcc_self)
    elif bucket in ("improvable", "ineligible"):
        meta = await _email_not_eligible_row(row, to, bcc_self)
    else:
        meta = await _email_one_row(row, to, bcc_self)
    meta["kind"] = bucket
    return meta




async def _email_one_row(row: Dict[str, Any], to: str, bcc_self: bool) -> Dict[str, Any]:
    from routers.email_settings import get_settings, read_asset_bytes
    s = await get_settings()
    p = row.get("parsed") or {}
    sender_email = (p.get("consultant_email") or gmail_default_sender() or "").strip().lower()
    sender_name = (p.get("consultant_name") or "").strip() or "Ladhani Education & Migration Services"
    subject, html, plain = build_report_email(
        s, client_name=p.get("name") or "Applicant",
        occupation=p.get("occupation_title"), code=p.get("anzsco_code"),
        points=row.get("points") or {}, sender_name=sender_name,
        backend_url=os.environ.get("PUBLIC_BASE_URL", ""),
    )
    attachments: List[Dict[str, Any]] = []
    if s.get("attach_report", True) and row.get("pdf_file_id"):
        attachments.append({
            "bytes": await _read_pdf_bytes(row["pdf_file_id"]),
            "filename": _report_filename(p.get("name"), row.get("assessment_id")),
            "maintype": "application", "subtype": "pdf",
        })
    if s.get("attach_sla") and s.get("sla_file_id"):
        sla = await read_asset_bytes(s["sla_file_id"])
        if sla:
            attachments.append({"bytes": sla, "filename": s.get("sla_filename") or "LEAMSS-Service-Level-Agreement.pdf",
                                "maintype": "application", "subtype": "pdf"})
    if s.get("qr_file_id"):
        qr = await read_asset_bytes(s["qr_file_id"])
        if qr:
            attachments.append({"bytes": qr, "filename": "LEAMSS-Payment-QR.png", "maintype": "image", "subtype": "png"})
    resume_attached = False
    resume_error = None
    if s.get("attach_resume"):
        if p.get("resume_link"):
            rb, rfname, rerr = await fetch_resume_bytes(p["resume_link"])
            if rb:
                ext = os.path.splitext(rfname or "")[1].lower() or ".pdf"
                subtype = {".pdf": "pdf", ".docx": "vnd.openxmlformats-officedocument.wordprocessingml.document",
                           ".doc": "msword", ".txt": "plain"}.get(ext, "octet-stream")
                maintype = "text" if ext == ".txt" else "application"
                cname = (p.get("name") or "Client").replace(" ", "_")
                attachments.append({"bytes": rb, "filename": f"{cname}_Resume{ext}", "maintype": maintype, "subtype": subtype})
                resume_attached = True
            else:
                resume_error = rerr or "Could not fetch resume"
        else:
            resume_error = "No resume link on file"
    await gmail_send(
        sender_email=sender_email, sender_name=sender_name, recipient=to,
        subject=subject, html=html, plain=plain, attachments=attachments,
        bcc=(sender_email if bcc_self else None),
    )
    return {"resume_attached": resume_attached, "resume_error": resume_error, "sender_email": sender_email}


class RowEmailRequest(BaseModel):
    email_override: Optional[str] = None
    bcc_self: bool = True
    template_id: Optional[str] = None


_EMAIL_NOT_CONFIGURED = ("Gmail is not configured. Add the service-account key (GMAIL_SA_JSON_B64) in "
                         "backend/.env and complete the Google Admin console domain-wide delegation.")


@router.post("/row/{row_id}/email")
async def email_row(row_id: str, req: RowEmailRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not gmail_is_configured():
        raise HTTPException(status_code=503, detail=_EMAIL_NOT_CONFIGURED)
    row = await ROWS.find_one({"id": row_id})
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    p = row.get("parsed") or {}
    to = (req.email_override or p.get("email") or "").strip()
    if not to or "@" not in to:
        raise HTTPException(status_code=400, detail="This client has no valid email address. Add one and try again.")
    bucket = bucket_for_row(row)
    # Eligible / Not-Eligible need a generated report to attach; resume-request does not.
    if bucket != "needs_resume" and not row.get("pdf_file_id"):
        raise HTTPException(status_code=400, detail="No generated report to email — generate the report first.")
    now = datetime.now(timezone.utc)
    try:
        meta = await _send_row_auto(row, to, req.bcc_self, template_id=req.template_id)
    except RuntimeError as e:
        await ROWS.update_one({"id": row_id}, {"$set": {"email_status": "failed", "email_error": str(e)[:400], "email_attempted_at": now}})
        raise HTTPException(status_code=503, detail=str(e))
    await ROWS.update_one({"id": row_id}, {"$set": {
        "email_status": "sent", "email_to": to, "email_sent_at": now, "email_error": None,
        "email_kind": meta.get("kind"), "email_from": meta.get("sender_email"),
        "email_resume_attached": meta.get("resume_attached"), "email_resume_error": meta.get("resume_error"),
    }})
    return {"ok": True, "sent_to": to, "kind": meta.get("kind"), "template": meta.get("template"),
            "resume_attached": meta.get("resume_attached"), "resume_error": meta.get("resume_error")}


class RowEligibilityRequest(BaseModel):
    kind: str  # 'auto' | 'improvable' | 'ineligible'
    reason: Optional[str] = None


@router.post("/row/{row_id}/set-eligibility")
async def set_row_eligibility(row_id: str, req: RowEligibilityRequest, current_user: dict = Depends(get_current_user)):
    """Manually override a client's eligibility verdict and regenerate their report."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    row = await ROWS.find_one({"id": row_id})
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    kind = (req.kind or "auto").strip()
    if kind == "auto":
        await ROWS.update_one({"id": row_id}, {"$unset": {"manual_eligibility": ""}})
    elif kind in ("improvable", "ineligible"):
        await ROWS.update_one({"id": row_id}, {"$set": {"manual_eligibility": {
            "kind": kind, "reason": (req.reason or "").strip(),
            "set_by": current_user.get("email"), "set_at": datetime.now(timezone.utc).isoformat(),
        }}})
    else:
        raise HTTPException(status_code=400, detail="Invalid eligibility kind")

    # Regenerate the report PDF so it reflects the new verdict (needs generatable data).
    row = await ROWS.find_one({"id": row_id})
    regenerated = False
    if row.get("status") in ("generated", "valid") and (row.get("parsed") or {}).get("anzsco_code"):
        batch = await BATCHES.find_one({"id": row["batch_id"]})
        if batch:
            user = {"id": current_user["id"], "name": current_user.get("name") or current_user.get("email")}
            try:
                regenerated = bool(await _generate_row(row, batch, user))
            except Exception as e:  # noqa: BLE001
                await ROWS.update_one({"id": row_id}, {"$set": {"gen_error": str(e)[:300]}})
    updated = await ROWS.find_one({"id": row_id}, {"_id": 0})
    return {"ok": True, "regenerated": regenerated, "eligibility": updated.get("eligibility"),
            "bucket": bucket_for_row(updated)}


async def _run_email_all(batch_id: str, bcc_self: bool):
    rows = await ROWS.find({"batch_id": batch_id, "status": "generated"}, {"_id": 0}).sort("row_index", 1).to_list(100000)
    done = 0
    failed = 0
    skipped = 0
    for row in rows:
        p = row.get("parsed") or {}
        to = (p.get("email") or "").strip()
        if not row.get("pdf_file_id") or not to or "@" not in to:
            skipped += 1
            continue
        now = datetime.now(timezone.utc)
        try:
            meta = await _email_one_row(row, to, bcc_self)
            await ROWS.update_one({"id": row["id"]}, {"$set": {
                "email_status": "sent", "email_to": to, "email_sent_at": now, "email_error": None,
                "email_resume_attached": meta.get("resume_attached"), "email_resume_error": meta.get("resume_error"),
                "email_from": meta.get("sender_email"),
            }})
            done += 1
        except Exception as e:  # noqa: BLE001
            await ROWS.update_one({"id": row["id"]}, {"$set": {"email_status": "failed", "email_error": str(e)[:400], "email_attempted_at": now}})
            failed += 1
        await BATCHES.update_one({"id": batch_id}, {"$set": {"email_done": done, "email_failed": failed}})
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "email_status": "done", "email_done": done, "email_failed": failed,
        "email_skipped": skipped, "email_completed_at": datetime.now(timezone.utc),
    }})


class EmailAllRequest(BaseModel):
    bcc_self: bool = True


@router.post("/{batch_id}/email-all")
async def email_all(batch_id: str, req: EmailAllRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not gmail_is_configured():
        raise HTTPException(status_code=503, detail=_EMAIL_NOT_CONFIGURED)
    batch = await BATCHES.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.get("email_status") == "sending":
        raise HTTPException(status_code=400, detail="Emails are already being sent for this batch.")
    rows = await ROWS.find({"batch_id": batch_id, "status": "generated"}, {"_id": 0, "pdf_file_id": 1, "parsed.email": 1}).to_list(100000)
    sendable = [r for r in rows if r.get("pdf_file_id") and ((r.get("parsed") or {}).get("email") or "").strip() and "@" in ((r.get("parsed") or {}).get("email") or "")]
    if not sendable:
        raise HTTPException(status_code=400, detail="No generated reports with a valid client email to send.")
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "email_status": "sending", "email_total": len(sendable), "email_done": 0,
        "email_failed": 0, "email_skipped": 0, "email_started_at": datetime.now(timezone.utc),
    }})
    asyncio.create_task(_run_email_all(batch_id, req.bcc_self))
    return {"ok": True, "queued": len(sendable)}


def _resume_upload_url(token: str) -> str:
    base = (os.environ.get("FRONTEND_URL") or os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")
    return f"{base}/upload-resume/{token}"


async def _email_not_eligible_row(row: Dict[str, Any], to: str, bcc_self: bool) -> Dict[str, Any]:
    from routers.email_settings import get_settings
    s = await get_settings()
    p = row.get("parsed") or {}
    sender_email = (p.get("consultant_email") or gmail_default_sender() or "").strip().lower()
    sender_name = (p.get("consultant_name") or "").strip() or "Ladhani Education & Migration Services"
    verdict = row.get("eligibility") or classify_eligibility(p, row.get("points") or {})
    subject, html, plain = build_not_eligible_email(
        s, client_name=p.get("name") or "Applicant", verdict=verdict,
        occupation=p.get("occupation_title"), code=p.get("anzsco_code"),
        sender_name=sender_name, backend_url=os.environ.get("PUBLIC_BASE_URL", ""),
    )
    attachments: List[Dict[str, Any]] = []
    if row.get("pdf_file_id"):
        attachments.append({
            "bytes": await _read_pdf_bytes(row["pdf_file_id"]),
            "filename": _report_filename(p.get("name"), row.get("assessment_id")),
            "maintype": "application", "subtype": "pdf",
        })
    await gmail_send(sender_email=sender_email, sender_name=sender_name, recipient=to,
                     subject=subject, html=html, plain=plain, attachments=attachments,
                     bcc=(sender_email if bcc_self else None))
    return {"sender_email": sender_email, "verdict": verdict.get("verdict")}


async def _email_resume_request_row(row: Dict[str, Any], to: str, bcc_self: bool) -> Dict[str, Any]:
    from routers.email_settings import get_settings
    s = await get_settings()
    p = row.get("parsed") or {}
    sender_email = (p.get("consultant_email") or gmail_default_sender() or "").strip().lower()
    sender_name = (p.get("consultant_name") or "").strip() or "Ladhani Education & Migration Services"
    token = row.get("resume_token")
    if not token:
        token = uuid.uuid4().hex
        await ROWS.update_one({"id": row["id"]}, {"$set": {"resume_token": token}})
    url = _resume_upload_url(token)
    subject, html, plain = build_resume_request_email(
        s, client_name=p.get("name") or "Applicant", upload_url=url, sender_name=sender_name)
    await gmail_send(sender_email=sender_email, sender_name=sender_name, recipient=to,
                     subject=subject, html=html, plain=plain, attachments=[],
                     bcc=(sender_email if bcc_self else None))
    return {"sender_email": sender_email, "upload_url": url}


def _has_email(row: Dict[str, Any]) -> Optional[str]:
    to = ((row.get("parsed") or {}).get("email") or "").strip()
    return to if (to and "@" in to) else None


async def _run_email_category(batch_id: str, kind: str, bcc_self: bool, template_id: Optional[str] = None):
    """Background sender for 'not_eligible' or 'resume_request' categories."""
    if kind == "not_eligible":
        rows = await ROWS.find({"batch_id": batch_id, "status": "generated"}, {"_id": 0}).sort("row_index", 1).to_list(100000)
        rows = [r for r in rows if bucket_for_row(r) in ("improvable", "ineligible")]
    else:  # resume_request
        rows = await ROWS.find({"batch_id": batch_id, "status": {"$in": ["needs_ai", "error"]}}, {"_id": 0}).sort("row_index", 1).to_list(100000)
    done = failed = skipped = 0
    for row in rows:
        to = _has_email(row)
        if not to or (kind == "not_eligible" and not row.get("pdf_file_id")):
            skipped += 1
            continue
        now = datetime.now(timezone.utc)
        try:
            meta = await _send_row_auto(row, to, bcc_self, template_id=template_id)
            await ROWS.update_one({"id": row["id"]}, {"$set": {
                "email_status": "sent", "email_to": to, "email_sent_at": now, "email_error": None,
                "email_kind": kind, "email_from": meta.get("sender_email"),
            }})
            done += 1
        except Exception as e:  # noqa: BLE001
            await ROWS.update_one({"id": row["id"]}, {"$set": {"email_status": "failed", "email_error": str(e)[:400], "email_attempted_at": now}})
            failed += 1
        await BATCHES.update_one({"id": batch_id}, {"$set": {"email_done": done, "email_failed": failed}})
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "email_status": "done", "email_done": done, "email_failed": failed,
        "email_skipped": skipped, "email_completed_at": datetime.now(timezone.utc),
    }})


class CategoryEmailRequest(BaseModel):
    bcc_self: bool = True
    template_id: Optional[str] = None


@router.get("/{batch_id}/eligibility-summary")
async def eligibility_summary(batch_id: str, current_user: dict = Depends(get_current_user)):
    """Bucket counts for the batch: eligible / improvable / ineligible / needs_resume (+ emailable counts)."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    rows = await ROWS.find({"batch_id": batch_id},
                           {"_id": 0, "status": 1, "eligibility": 1, "parsed.email": 1, "pdf_file_id": 1}).to_list(100000)
    buckets = {"eligible": 0, "improvable": 0, "ineligible": 0, "needs_resume": 0}
    emailable = {"eligible": 0, "improvable": 0, "ineligible": 0, "needs_resume": 0}
    for r in rows:
        b = bucket_for_row(r)
        buckets[b] = buckets.get(b, 0) + 1
        if _has_email(r):
            if b == "needs_resume" or r.get("pdf_file_id"):
                emailable[b] = emailable.get(b, 0) + 1
    return {"buckets": buckets, "emailable": emailable, "total": len(rows)}


@router.post("/{batch_id}/email-not-eligible")
async def email_not_eligible(batch_id: str, req: CategoryEmailRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not gmail_is_configured():
        raise HTTPException(status_code=503, detail=_EMAIL_NOT_CONFIGURED)
    batch = await BATCHES.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.get("email_status") == "sending":
        raise HTTPException(status_code=400, detail="Emails are already being sent for this batch.")
    rows = await ROWS.find({"batch_id": batch_id, "status": "generated"}, {"_id": 0}).to_list(100000)
    sendable = [r for r in rows if bucket_for_row(r) in ("improvable", "ineligible") and _has_email(r) and r.get("pdf_file_id")]
    if not sendable:
        raise HTTPException(status_code=400, detail="No Not-Eligible clients with a generated report and valid email to send.")
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "email_status": "sending", "email_total": len(sendable), "email_done": 0,
        "email_failed": 0, "email_skipped": 0, "email_started_at": datetime.now(timezone.utc),
    }})
    asyncio.create_task(_run_email_category(batch_id, "not_eligible", req.bcc_self, req.template_id))
    return {"ok": True, "queued": len(sendable)}


@router.post("/{batch_id}/email-resume-request")
async def email_resume_request(batch_id: str, req: CategoryEmailRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not gmail_is_configured():
        raise HTTPException(status_code=503, detail=_EMAIL_NOT_CONFIGURED)
    batch = await BATCHES.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.get("email_status") == "sending":
        raise HTTPException(status_code=400, detail="Emails are already being sent for this batch.")
    rows = await ROWS.find({"batch_id": batch_id, "status": {"$in": ["needs_ai", "error"]}}, {"_id": 0}).to_list(100000)
    sendable = [r for r in rows if _has_email(r)]
    if not sendable:
        raise HTTPException(status_code=400, detail="No resume-pending clients with a valid email to send.")
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "email_status": "sending", "email_total": len(sendable), "email_done": 0,
        "email_failed": 0, "email_skipped": 0, "email_started_at": datetime.now(timezone.utc),
    }})
    asyncio.create_task(_run_email_category(batch_id, "resume_request", req.bcc_self, req.template_id))
    return {"ok": True, "queued": len(sendable)}


async def _reminder_template(template_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    coll = db["email_templates"]
    if template_id:
        t = await coll.find_one({"id": template_id})
        if t:
            t.pop("_id", None)
            return t
    t = await coll.find_one({"name": "Reminder — Report Sent (Warm Follow-up)"})
    if not t:
        t = await coll.find_one({"category": "eligible", "name": {"$regex": "reminder", "$options": "i"}})
    if t:
        t.pop("_id", None)
    return t


def _reminder_sendable(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Eligible clients who were already sent their report and can receive a follow-up reminder."""
    return [r for r in rows if r.get("status") == "generated" and r.get("email_status") == "sent"
            and bucket_for_row(r) == "eligible" and r.get("pdf_file_id") and _has_email(r)]


async def _run_email_reminder(batch_id: str, bcc_self: bool, template_id: Optional[str] = None):
    tpl = await _reminder_template(template_id)
    rows = await ROWS.find({"batch_id": batch_id, "status": "generated", "email_status": "sent"},
                           {"_id": 0}).sort("row_index", 1).to_list(100000)
    rows = _reminder_sendable(rows)
    done = failed = 0
    for row in rows:
        to = _has_email(row)
        now = datetime.now(timezone.utc)
        try:
            if tpl:
                meta = await _send_row_with_template(row, to, tpl, bcc_self)
            else:
                meta = await _email_one_row(row, to, bcc_self)
            await ROWS.update_one({"id": row["id"]}, {"$set": {
                "reminder_status": "sent", "reminder_sent_at": now, "reminder_error": None,
                "reminder_from": meta.get("sender_email"),
            }})
            done += 1
        except Exception as e:  # noqa: BLE001
            await ROWS.update_one({"id": row["id"]}, {"$set": {"reminder_status": "failed", "reminder_error": str(e)[:400]}})
            failed += 1
        await BATCHES.update_one({"id": batch_id}, {"$set": {"email_done": done, "email_failed": failed}})
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "email_status": "done", "email_done": done, "email_failed": failed,
        "email_completed_at": datetime.now(timezone.utc),
    }})


@router.post("/{batch_id}/email-reminder")
async def email_reminder(batch_id: str, req: CategoryEmailRequest, current_user: dict = Depends(get_current_user)):
    """Send a follow-up reminder (with the offer) to every client who was already sent their positive report."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not gmail_is_configured():
        raise HTTPException(status_code=503, detail=_EMAIL_NOT_CONFIGURED)
    batch = await BATCHES.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.get("email_status") == "sending":
        raise HTTPException(status_code=400, detail="Emails are already being sent for this batch.")
    rows = await ROWS.find({"batch_id": batch_id, "status": "generated", "email_status": "sent"}, {"_id": 0}).to_list(100000)
    sendable = _reminder_sendable(rows)
    if not sendable:
        raise HTTPException(status_code=400, detail="No report-sent eligible clients found to remind. Send the reports first.")
    await BATCHES.update_one({"id": batch_id}, {"$set": {
        "email_status": "sending", "email_total": len(sendable), "email_done": 0,
        "email_failed": 0, "email_skipped": 0, "email_started_at": datetime.now(timezone.utc),
    }})
    asyncio.create_task(_run_email_reminder(batch_id, req.bcc_self, req.template_id))
    return {"ok": True, "queued": len(sendable)}


@router.get("/{batch_id}/email-preview")
async def email_preview(batch_id: str, current_user: dict = Depends(get_current_user)):
    """Pre-send confirm: how many will send, how many missing email, per-consultant split, resume coverage."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    from routers.email_settings import get_settings
    s = await get_settings()
    rows = await ROWS.find({"batch_id": batch_id, "status": "generated"},
                           {"_id": 0, "parsed.email": 1, "parsed.name": 1, "parsed.consultant_email": 1,
                            "parsed.consultant_name": 1, "parsed.resume_link": 1, "pdf_file_id": 1}).to_list(100000)
    sendable, missing = [], []
    by_consultant: Dict[str, Dict[str, Any]] = {}
    with_resume = 0
    default_sender = gmail_default_sender()
    for r in rows:
        p = r.get("parsed") or {}
        email = (p.get("email") or "").strip()
        if not r.get("pdf_file_id") or not email or "@" not in email:
            missing.append(p.get("name") or "(unnamed)")
            continue
        sendable.append(r)
        ce = (p.get("consultant_email") or default_sender or "").lower()
        cname = p.get("consultant_name") or ("Default" if ce == default_sender else ce)
        b = by_consultant.setdefault(ce, {"email": ce, "name": cname, "count": 0})
        b["count"] += 1
        if p.get("resume_link"):
            with_resume += 1
    return {
        "configured": gmail_is_configured(),
        "total_generated": len(rows),
        "sendable": len(sendable),
        "missing_email": len(missing),
        "missing_sample": missing[:15],
        "by_consultant": sorted(by_consultant.values(), key=lambda x: -x["count"]),
        "with_resume": with_resume,
        "without_resume": len(sendable) - with_resume,
        "attach_resume": bool(s.get("attach_resume")),
        "attach_sla": bool(s.get("attach_sla") and s.get("sla_file_id")),
        "attach_qr": bool(s.get("qr_file_id")),
        "offer_enabled": bool(s.get("offer_enabled", True)),
        "default_sender": default_sender,
    }


@router.get("/{batch_id}/email-summary")
async def email_summary(batch_id: str, current_user: dict = Depends(get_current_user)):
    """Post-send report: sent / failed / skipped / resume-missing, with per-consultant counts."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    batch = await BATCHES.find_one({"id": batch_id}, {"_id": 0})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    rows = await ROWS.find({"batch_id": batch_id, "status": "generated"},
                           {"_id": 0, "parsed.name": 1, "parsed.email": 1, "email_status": 1, "email_to": 1,
                            "email_error": 1, "email_from": 1, "email_resume_attached": 1,
                            "email_resume_error": 1, "email_sent_at": 1}).to_list(100000)
    sent, failed, skipped, resume_missing = [], [], [], []
    by_consultant: Dict[str, int] = {}
    for r in rows:
        p = r.get("parsed") or {}
        name = p.get("name") or "(unnamed)"
        es = r.get("email_status")
        if es == "sent":
            sent.append({"name": name, "email": r.get("email_to"), "from": r.get("email_from")})
            fr = r.get("email_from") or "default"
            by_consultant[fr] = by_consultant.get(fr, 0) + 1
            if r.get("email_resume_attached") is False:
                resume_missing.append({"name": name, "reason": r.get("email_resume_error") or "No resume"})
        elif es == "failed":
            failed.append({"name": name, "email": p.get("email"), "error": r.get("email_error") or "Send failed"})
        else:
            email = (p.get("email") or "").strip()
            if not email or "@" not in email:
                skipped.append({"name": name, "reason": "No email address"})
    return {
        "email_status": batch.get("email_status"),
        "started_at": batch.get("email_started_at"),
        "completed_at": batch.get("email_completed_at"),
        "totals": {"sent": len(sent), "failed": len(failed), "skipped": len(skipped),
                   "resume_missing": len(resume_missing)},
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "resume_missing": resume_missing,
        "by_consultant": [{"from": k, "count": v} for k, v in sorted(by_consultant.items(), key=lambda x: -x[1])],
    }


class AssignConsultantRequest(BaseModel):
    consultant_email: Optional[str] = None  # None / "" clears the assignment
    row_ids: Optional[List[str]] = None     # None → all rows in the batch


@router.post("/{batch_id}/assign-consultant")
async def assign_consultant(batch_id: str, req: AssignConsultantRequest, current_user: dict = Depends(get_current_user)):
    """Assign (or clear) the consultant mailbox that a client's report is sent FROM."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not await BATCHES.find_one({"id": batch_id}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Batch not found")
    email = (req.consultant_email or "").strip().lower() or None
    name = None
    if email:
        s = await MAIL_SENDERS.find_one({"email": email})
        if not s:
            raise HTTPException(status_code=400, detail=f"{email} is not in the mailbox list. Add it under Mail Accounts first.")
        name = s.get("name")
    q: Dict[str, Any] = {"batch_id": batch_id}
    if req.row_ids:
        q["id"] = {"$in": req.row_ids}
    res = await ROWS.update_many(q, {"$set": {"parsed.consultant_email": email, "parsed.consultant_name": name}})
    return {"ok": True, "updated": res.modified_count, "consultant_email": email, "consultant_name": name}


# ─────────────────────────────────────────────────────────────
# Export — ZIP of PDFs + summary Excel
# ─────────────────────────────────────────────────────────────
@router.get("/{batch_id}/export")
async def export_batch(batch_id: str, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    batch = await BATCHES.find_one({"id": batch_id}, {"_id": 0})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    rows = await ROWS.find({"batch_id": batch_id, "status": "generated"}, {"_id": 0}).sort("row_index", 1).to_list(100000)
    if not rows:
        raise HTTPException(status_code=400, detail="No generated reports to export")

    # Summary sheet
    summary_rows = []
    for r in rows:
        p = r["parsed"]; pts = r.get("points") or {}
        summary_rows.append({
            "Name": p["name"], "Email": p.get("email"), "Age": p.get("age"),
            "ANZSCO": p.get("anzsco_code"), "Occupation": p.get("occupation_title"),
            "Points 189": pts.get("189"), "Points 190": pts.get("190"), "Points 491": pts.get("491"),
            "Eligible (65+)": "Yes" if (pts.get("491") or 0) >= 65 else "No",
            "Assessment ID": r.get("assessment_id"),
        })
    sbuf = io.BytesIO()
    with pd.ExcelWriter(sbuf, engine="openpyxl") as w:
        pd.DataFrame(summary_rows).to_excel(w, index=False, sheet_name="Summary")
    sbuf.seek(0)

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("00_Summary.xlsx", sbuf.read())
        used = set()
        for r in rows:
            if not r.get("pdf_file_id"):
                continue
            try:
                stream = await _gridfs.open_download_stream(ObjectId(r["pdf_file_id"]))
                data = await stream.read()
            except Exception:
                continue
            base = re.sub(r"[^A-Za-z0-9_-]", "_", r["parsed"]["name"])[:40] or "client"
            fname = f"{base}_{r.get('assessment_id')}.pdf"
            n = 1
            while fname in used:
                fname = f"{base}_{r.get('assessment_id')}_{n}.pdf"; n += 1
            used.add(fname)
            zf.writestr(fname, data)
    zbuf.seek(0)
    return StreamingResponse(
        zbuf, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{batch_id}_reports.zip"'},
    )


@router.get("/row/{row_id}/pdf")
async def row_pdf(row_id: str, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    row = await ROWS.find_one({"id": row_id})
    if not row or not row.get("pdf_file_id"):
        raise HTTPException(status_code=404, detail="No PDF for this row")
    stream = await _gridfs.open_download_stream(ObjectId(row["pdf_file_id"]))
    data = await stream.read()
    base = re.sub(r"[^A-Za-z0-9_-]", "_", row["parsed"]["name"])[:40] or "client"
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'inline; filename="{base}.pdf"'})
