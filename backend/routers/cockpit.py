"""Phase 7.5 — Pipeline Cockpit Router.

Single-pane API that unifies LEAMSS pipeline records across collections:

  • leads               → `leads`
  • assessments         → `sales_assessments` (no linked PA yet)
  • pre-assessments     → `pre_assessments` in early stages
  • proposals           → `pre_assessments` in proposal_sent
  • cases               → `pre_assessments` in proposal_paid / case_created
  • closed              → `pre_assessments` in rejected / refunded

Endpoints:
  GET /api/cockpit/funnel  — live counts per stage
  GET /api/cockpit/cards   — paginated card list with filters
  GET /api/cockpit/brief   — AI Brief stats for sidebar
  GET /api/cockpit/card/{type}/{id} — drill-in detail
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from core.auth import get_current_user
from core.database import db
from core.navratri_automation import (
    NAVRATRI_QUERY,
    is_lead_navratri,
    get_navratri_category,
    is_lead_paid,
    has_lead_resume,
    get_resume_upload_url,
    get_payment_url,
    send_navratri_resume_request,
    send_navratri_payment_link,
    mark_lead_paid_and_transition,
)

router = APIRouter(prefix="/cockpit", tags=["Cockpit"])

@router.get("/resume/{file_id}")
async def get_cockpit_resume(file_id: str):
    """Stream resume file from GridFS."""
    try:
        oid = ObjectId(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file ID")

    gridfs = AsyncIOMotorGridFSBucket(db, bucket_name="bulk_resumes")
    try:
        grid_out = await gridfs.open_download_stream(oid)
    except Exception:
        raise HTTPException(status_code=404, detail="Resume file not found")

    filename = grid_out.filename or "resume.pdf"
    content_type = (grid_out.metadata or {}).get("contentType") or "application/pdf"
    if filename.lower().endswith(".pdf"):
        content_type = "application/pdf"
    elif filename.lower().endswith(".docx"):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif filename.lower().endswith(".doc"):
        content_type = "application/msword"
    elif filename.lower().endswith(".png"):
        content_type = "image/png"
    elif filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
        content_type = "image/jpeg"

    async def iter_chunks():
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield chunk

    return StreamingResponse(
        iter_chunks(),
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(grid_out.length),
        },
    )


# ─── Stage taxonomy ──────────────────────────────────────────────────────────
STAGE_KEYS = ["leads", "assessments", "pa", "proposals", "cases", "closed", "navratri"]

PA_STAGE_GROUPS = {
    "pa": {"new", "payment_pending", "payment_received", "documents_submitted",
           "under_review", "approved", "express_pending_approval"},
    "proposals": {"proposal_sent"},
    "cases": {"proposal_paid", "awaiting_final_approval", "case_created"},
    "closed": {"rejected", "refunded", "express_rejected"},
}

# Maps PA stage → next-action label + urgency
PA_NEXT_ACTION = {
    "new":                       ("Send Payment Link", "high"),
    "payment_pending":           ("Awaiting PA Fee Payment", "medium"),
    "payment_received":          ("Submit Documents", "high"),
    "documents_submitted":       ("Awaiting Admin Review", "medium"),
    "under_review":              ("Admin Reviewing", "low"),
    "approved":                  ("Send Sales Proposal", "high"),
    "proposal_sent":             ("Awaiting Main Fee Payment", "medium"),
    "proposal_paid":             ("Create Case", "high"),
    "awaiting_final_approval":   ("Final Approval Pending", "medium"),
    "case_created":              ("Case Active — Documentation", "low"),
    "rejected":                  ("Refund Initiated", "low"),
    "refunded":                  ("Closed — Refunded", "low"),
    "express_pending_approval":  ("Express PA Awaiting Approval", "high"),
    "express_rejected":          ("Express Rejected", "low"),
}

LIFECYCLE_FROM_PA_STAGE = {
    "new": 3, "payment_pending": 3, "express_pending_approval": 3,
    "payment_received": 4, "documents_submitted": 4, "under_review": 4,
    "approved": 4, "rejected": 4, "refunded": 4, "refund_initiated": 4,
    "express_rejected": 4, "proposal_sent": 4,
    "proposal_paid": 5, "awaiting_final_approval": 5,
    "case_created": 6,
}


# ─── Permissions ─────────────────────────────────────────────────────────────
def _is_admin(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    return role in ("admin", "admin_owner", "case_manager") or "*" in (user.get("permissions") or [])


def _own_query(user: dict) -> Dict[str, Any]:
    """Returns the ownership filter for non-admin users."""
    if _is_admin(user):
        return {}
    return {"created_by": user["id"]}


def _own_pa_query(user: dict) -> Dict[str, Any]:
    """Ownership filter for PAs (uses partner_id field)."""
    if _is_admin(user):
        return {}
    return {"partner_id": user["id"]}


def _own_lead_query(user: dict) -> Dict[str, Any]:
    if _is_admin(user):
        return {}
    return {"$or": [
        {"assigned_to": user["id"]},
        {"partner_id": user["id"]},
        {"assigned_to": None},
        {"assigned_to": ""},
        {"assigned_to": "Unassigned"},
        {"assigned_to": {"$exists": False}},
        {"source": {"$regex": "website|navratri|landing", "$options": "i"}}
    ]}


# ─── Card builders (per source) ──────────────────────────────────────────────
def _humanize_ago(dt: Optional[datetime]) -> str:
    if not dt:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:        return "just now"
    if secs < 3600:      return f"{secs // 60} min ago"
    if secs < 86400:     return f"{secs // 3600} hr ago"
    if secs < 604800:    return f"{secs // 86400} day{'s' if secs // 86400 > 1 else ''} ago"
    return dt.strftime("%d %b %Y")


def _build_lead_card(d: Dict[str, Any], gen_leads: Optional[set] = None, gen_emails: Optional[set] = None, batch_map: Optional[dict] = None) -> Dict[str, Any]:
    """Normalize a `leads` doc into a cockpit card."""
    country = d.get("country_of_interest") or ""
    unique_id = d.get("unique_id") or ""
    service = d.get("service_interested") or "New enquiry"
    score_label = f"{unique_id} · {service}" if unique_id else service
    
    lid = str(d.get("id") or "").strip()
    lemail = str(d.get("email") or "").strip().lower()

    is_nav = is_lead_navratri(d)
    nav_category = get_navratri_category(d)
    is_paid = is_lead_paid(d)

    # STRICT RULE: Unpaid leads can NEVER have a generated report or batch
    if is_paid:
        batch_id = d.get("bulk_batch_id") or (batch_map.get(lid) if batch_map and lid else None) or (batch_map.get(lemail) if batch_map and lemail and "@" in lemail else None)
        has_report = bool(
            d.get("report_generated") is True
            or d.get("report_status") in ("generated", "completed")
            or bool(d.get("assessment_report_id"))
            or bool(d.get("latest_report_snapshot_id"))
            or bool(batch_id)
            or (lid and gen_leads and lid in gen_leads)
            or (lemail and "@" in lemail and gen_emails and lemail in gen_emails)
        )
    else:
        batch_id = None
        has_report = False

    resume_fid = d.get("resume_file_id") if (d.get("resume_file_id") and is_valid_resume_path(d.get("resume_file_id"))) else None
    has_resume = has_lead_resume(d)
    resume_fname = None
    resume_link = ""
    if has_resume:
        raw_name = d.get("resume_filename")
        if raw_name and is_valid_resume_path(raw_name):
            resume_fname = str(raw_name).strip()
        else:
            raw_url = str(d.get("resume_url") or d.get("resume_path") or d.get("resume_link") or "")
            fn = raw_url.replace("\\", "/").split("/")[-1].strip()
            resume_fname = fn if (fn and is_valid_resume_path(fn)) else "Uploaded_Resume.pdf"
        resume_link = f"/cockpit/resume/{resume_fid}" if resume_fid else (d.get("resume_url") or d.get("resume_path") or d.get("resume_link") or "")

    upload_url = get_resume_upload_url(d)
    pay_url = get_payment_url(d)

    # Contextual next action
    if is_nav:
        if is_paid and has_resume:
            next_action = "Create Pre-Assessment" if has_report else "Bulk Pre-Assessment (Ready)"
        elif is_paid and not has_resume:
            next_action = "Request Resume (Email + WA)"
        else:
            next_action = "Send Payment Link (Email + WA)"
    else:
        next_action = "Create Pre-Assessment" if has_report else "Start Eligibility Wizard"

    return {
        "id": d.get("id"),
        "type": "lead",
        "name": d.get("name") or "Unnamed Lead",
        "email": d.get("email") or "",
        "phone": d.get("phone") or "",
        "unique_id": unique_id,
        "stage": "leads",
        "countries": [country] if country else [],
        "score": None,
        "score_label": score_label,
        "qualification": d.get("latest_qualification") or "",
        "experience": d.get("total_work_experience") or "",
        "payment_status": d.get("payment_status") or ("success" if is_paid else "pending"),
        "payment_amount": d.get("payment_amount"),
        "is_paid": is_paid,
        "is_navratri": is_nav,
        "navratri_category": nav_category,
        "resume_upload_url": upload_url,
        "payment_link": pay_url,
        "last_resume_request_sent_at": d.get("last_resume_request_sent_at"),
        "last_payment_link_sent_at": d.get("last_payment_link_sent_at"),
        "has_resume": has_resume,
        "resume_file_id": resume_fid,
        "resume_filename": resume_fname,
        "resume_url": resume_link,
        "report_generated": has_report,
        "report_status": "generated" if has_report else (d.get("report_status") or "pending"),
        "report_generated_at": d.get("report_generated_at") if is_paid else None,
        "assessment_report_id": (d.get("assessment_report_id") or d.get("latest_report_snapshot_id")) if is_paid else None,
        "bulk_batch_id": batch_id,
        "bulk_row_id": d.get("bulk_row_id") if is_paid else None,
        "lifecycle": 2 if has_report else (1 if (is_paid and has_resume) else (1 if is_paid else 0)),
        "next_action": next_action,
        "urgency": d.get("priority") or ("high" if not has_report and is_paid else "medium"),
        "owner": {
            "id": d.get("assigned_to"),
            "name": d.get("assigned_to_name") if d.get("assigned_to") else "Unassigned",
        },
        "partner": {
            "id": d.get("partner_id"),
            "name": d.get("partner_name") if d.get("partner_id") else "Unassigned",
        },
        "case_manager": {
            "id": d.get("case_manager_id"),
            "name": d.get("case_manager_name") if d.get("case_manager_id") else "Unassigned",
        },
        "created_at": d.get("created_at"),
        "created_at_human": _humanize_ago(d.get("created_at")),
        "updated_at": d.get("created_at") or d.get("updated_at"),
        "updated_at_human": _humanize_ago(d.get("created_at") or d.get("updated_at")),
        "source": d.get("source") or "website",
    }


def _build_assessment_card(d: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a `sales_assessments` (no PA yet) doc into a cockpit card."""
    best_cc = d.get("best_country_code") or ""
    best_total = d.get("best_total")
    has_report = bool(d.get("latest_report_snapshot_id"))
    next_action = "Generate Report" if not has_report else "Create Pre-Assessment"

    snap = d.get("profile_snapshot") or {}
    pri = snap.get("primary_applicant") or {}
    raw_fid = d.get("resume_file_id") or snap.get("resume_file_id") or pri.get("resume_file_id")
    resume_fid = raw_fid if (raw_fid and is_valid_resume_path(raw_fid)) else None
    raw_res = d.get("resume_url") or snap.get("resume_url") or d.get("resume_link")
    has_resume = bool(resume_fid or (raw_res and is_valid_resume_path(raw_res)))
    resume_fname = None
    resume_link = ""
    if has_resume:
        raw_name = d.get("resume_filename") or snap.get("resume_filename") or pri.get("resume_filename")
        if raw_name and is_valid_resume_path(raw_name):
            resume_fname = str(raw_name).strip()
        else:
            fn = str(raw_res or "").replace("\\", "/").split("/")[-1].strip()
            resume_fname = fn if (fn and is_valid_resume_path(fn)) else "Uploaded_Resume.pdf"
        resume_link = f"/cockpit/resume/{resume_fid}" if resume_fid else str(raw_res or "")

    return {
        "id": d.get("id"),
        "type": "assessment",
        "name": d.get("client_name") or "Untitled",
        "email": d.get("client_email") or (d.get("profile") or {}).get("email") or "",
        "phone": d.get("client_phone") or (d.get("profile") or {}).get("phone") or "",
        "stage": "assessments",
        "countries": [best_cc] if best_cc else [],
        "score": best_total,
        "score_label": (
            f"{best_cc} {best_total} pts" if best_cc and best_total is not None
            else "Calculating…"
        ),
        "has_resume": has_resume,
        "resume_file_id": resume_fid,
        "resume_filename": resume_fname,
        "resume_url": resume_link,
        "report_generated": has_report,
        "report_status": "generated" if has_report else "pending",
        "bulk_batch_id": d.get("bulk_batch_id"),
        "assessment_report_id": d.get("latest_report_snapshot_id"),
        "lifecycle": 2 if has_report else (1 if best_total is not None else 0),
        "next_action": next_action,
        "urgency": "high" if not has_report else "medium",
        "owner": {
            "id": d.get("created_by"),
            "name": d.get("created_by_name") or "—",
        },
        "updated_at": d.get("updated_at") or d.get("created_at"),
        "updated_at_human": _humanize_ago(d.get("updated_at") or d.get("created_at")),
    }


def _build_pa_card(d: Dict[str, Any], stage_group: str) -> Dict[str, Any]:
    """Normalize a `pre_assessments` doc into a cockpit card."""
    pa_stage = d.get("stage") or "new"
    countries = [(d.get("target_country") or "").upper()] if d.get("target_country") else []
    next_action, urgency = PA_NEXT_ACTION.get(pa_stage, ("Review", "medium"))

    snap = d.get("profile_snapshot") or {}
    pri = snap.get("primary_applicant") or {}
    raw_fid = d.get("resume_file_id") or snap.get("resume_file_id") or pri.get("resume_file_id")
    resume_fid = raw_fid if (raw_fid and is_valid_resume_path(raw_fid)) else None
    raw_res = d.get("resume_url") or snap.get("resume_url")
    has_resume = bool(resume_fid or (raw_res and is_valid_resume_path(raw_res)))
    resume_fname = None
    resume_link = ""
    if has_resume:
        raw_name = d.get("resume_filename") or snap.get("resume_filename") or pri.get("resume_filename")
        if raw_name and is_valid_resume_path(raw_name):
            resume_fname = str(raw_name).strip()
        else:
            fn = str(raw_res or "").replace("\\", "/").split("/")[-1].strip()
            resume_fname = fn if (fn and is_valid_resume_path(fn)) else "Uploaded_Resume.pdf"
        resume_link = f"/cockpit/resume/{resume_fid}" if resume_fid else str(raw_res or "")

    return {
        "id": d.get("id"),
        "type": "pa",
        "name": d.get("client_name") or "Untitled",
        "email": d.get("client_email") or "",
        "phone": d.get("client_phone") or "",
        "stage": stage_group,
        "countries": countries,
        "score": d.get("eligibility_score"),
        "score_label": (
            f"{d.get('pa_number') or d.get('id', '')[:8]} · {pa_stage.replace('_', ' ').title()}"
        ),
        "has_resume": has_resume,
        "resume_file_id": resume_fid,
        "resume_filename": resume_fname,
        "resume_url": resume_link,
        "lifecycle": LIFECYCLE_FROM_PA_STAGE.get(pa_stage, 3),
        "next_action": next_action,
        "urgency": urgency,
        "owner": {
            "id": d.get("partner_id"),
            "name": d.get("partner_name") or "—",
        },
        "updated_at": d.get("updated_at") or d.get("created_at"),
        "updated_at_human": _humanize_ago(d.get("updated_at") or d.get("created_at")),
        "pa_stage": pa_stage,
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────
@router.get("/funnel")
async def get_funnel(current_user: dict = Depends(get_current_user)):
    """Live counts per stage. Respects ownership scoping."""
    leads_q = _own_lead_query(current_user) | {"stage": {"$ne": "converted"}}
    sa_q    = _own_query(current_user) | {"linked_pa_id": {"$in": [None, ""]}}
    pa_q    = _own_pa_query(current_user)
    
    if _is_admin(current_user):
        nav_q = NAVRATRI_QUERY
    else:
        nav_q = {"$and": [_own_lead_query(current_user), NAVRATRI_QUERY]}

    leads_n = await db["leads"].count_documents(leads_q)
    assessments_n = await db["sales_assessments"].count_documents(sa_q)
    navratri_n = await db["leads"].count_documents(nav_q)

    pa_counts = {k: 0 for k in ("pa", "proposals", "cases", "closed")}
    cursor = db["pre_assessments"].find(pa_q, {"_id": 0, "stage": 1})
    async for row in cursor:
        st = row.get("stage")
        for group, members in PA_STAGE_GROUPS.items():
            if st in members:
                pa_counts[group] += 1
                break

    return {
        "leads": leads_n,
        "assessments": assessments_n,
        "pa": pa_counts["pa"],
        "proposals": pa_counts["proposals"],
        "cases": pa_counts["cases"],
        "closed": pa_counts["closed"],
        "navratri": navratri_n,
        "total_active": leads_n + assessments_n + pa_counts["pa"] + pa_counts["proposals"] + pa_counts["cases"],
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/cards")
async def get_cards(
    stage: Optional[str] = Query(None, description="leads|assessments|pa|proposals|cases|closed|navratri|all"),
    owner: Optional[str] = Query(None, description="me|all|<user_id>"),
    filter: Optional[str] = Query(None, description="paid_report_pending|with_resume|without_resume|all"),
    navratri_status: Optional[str] = Query(None, description="paid_resume_received|paid_resume_pending|unpaid|all"),
    has_resume: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("recent", description="recent|oldest|paid_first|score_desc|score_asc"),
    limit: int = Query(500, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    """Unified card list across leads, assessments, and PAs."""
    cards: List[Dict[str, Any]] = []
    is_admin = _is_admin(current_user)

    # Owner override
    if owner == "me":
        own_filter_lead = {"$or": [{"assigned_to": current_user["id"]}, {"partner_id": current_user["id"]}]}
        own_filter_sa   = {"created_by":  current_user["id"]}
        own_filter_pa   = {"partner_id":  current_user["id"]}
    elif not is_admin and owner != "all":
        own_filter_lead = {"$or": [
            {"assigned_to": current_user["id"]},
            {"partner_id": current_user["id"]},
            {"assigned_to": None},
            {"assigned_to": ""},
            {"assigned_to": "Unassigned"},
            {"assigned_to": {"$exists": False}},
            {"source": {"$regex": "website|navratri|landing", "$options": "i"}}
        ]}
        own_filter_sa   = {"created_by":  current_user["id"]}
        own_filter_pa   = {"partner_id":  current_user["id"]}
    elif owner and owner not in ("all", "me"):
        own_filter_lead = {"$or": [{"assigned_to": owner}, {"partner_id": owner}]}
        own_filter_sa   = {"created_by":  owner}
        own_filter_pa   = {"partner_id":  owner}
    else:
        own_filter_lead = own_filter_sa = own_filter_pa = {}

    text_re = {"$regex": search, "$options": "i"} if search else None

    want_all = (not stage) or stage == "all"
    is_navratri_stage = stage == "navratri"

    # Collect all IDs/emails of generated reports across bulk_assessment_rows and sales_assessments
    gen_leads_set: set = set()
    gen_emails_set: set = set()
    gen_batch_map: dict = {}
    async for r in db["bulk_assessment_rows"].find(
        {"$or": [{"status": "generated"}, {"snapshot_id": {"$exists": True, "$ne": None}}]},
        {"lead_id": 1, "parsed.email": 1, "batch_id": 1}
    ):
        bid = r.get("batch_id")
        lid = r.get("lead_id")
        em = (r.get("parsed") or {}).get("email") if isinstance(r.get("parsed"), dict) else r.get("email")
        if lid:
            lid_str = str(lid).strip()
            gen_leads_set.add(lid_str)
            if bid: gen_batch_map[lid_str] = bid
        if em and "@" in str(em):
            em_str = str(em).strip().lower()
            gen_emails_set.add(em_str)
            if bid: gen_batch_map[em_str] = bid

    async for a in db["sales_assessments"].find(
        {"$or": [{"latest_report_snapshot_id": {"$exists": True, "$ne": None}}, {"report_snapshot_ids": {"$exists": True, "$ne": []}}]},
        {"lead_id": 1, "client_email": 1, "bulk_batch_id": 1}
    ):
        bid = a.get("bulk_batch_id")
        if a.get("lead_id"):
            lid_str = str(a["lead_id"]).strip()
            gen_leads_set.add(lid_str)
            if bid: gen_batch_map[lid_str] = bid
        if a.get("client_email") and str(a["client_email"]).strip():
            em_str = str(a["client_email"]).strip().lower()
            gen_emails_set.add(em_str)
            if bid: gen_batch_map[em_str] = bid

    # 1) Navratri Offer Leads (Full unfiltered list for campaign)
    if is_navratri_stage:
        q = NAVRATRI_QUERY.copy()
        if owner == "me" and own_filter_lead:
            q = {"$and": [own_filter_lead, NAVRATRI_QUERY]}
        elif owner and owner not in ("all", "me") and own_filter_lead:
            q = {"$and": [own_filter_lead, NAVRATRI_QUERY]}
        if text_re:
            q = {"$and": [q, {"$or": [{"name": text_re}, {"email": text_re}, {"phone": text_re}, {"unique_id": text_re}]}]}
        async for d in db["leads"].find(q, {"_id": 0}).sort("created_at", -1).limit(limit):
            cards.append(_build_lead_card(d, gen_leads_set, gen_emails_set, gen_batch_map))

    # 2) Standard Leads (when in 'all' or 'leads')
    elif want_all or stage == "leads":
        q = own_filter_lead | {"stage": {"$ne": "converted"}}
        if text_re:
            q["$or"] = [{"name": text_re}, {"email": text_re}, {"phone": text_re}]
        async for d in db["leads"].find(q, {"_id": 0}).sort("updated_at", -1).limit(limit):
            cards.append(_build_lead_card(d, gen_leads_set, gen_emails_set, gen_batch_map))

    # 3) Sales assessments (no PA yet)
    if (want_all or stage == "assessments") and not is_navratri_stage:
        q = own_filter_sa | {"linked_pa_id": {"$in": [None, ""]}}
        if text_re:
            q["client_name"] = text_re
        proj = {
            "_id": 0, "id": 1, "client_name": 1, "client_email": 1, "client_phone": 1,
            "best_country_code": 1, "best_total": 1,
            "latest_report_snapshot_id": 1, "created_at": 1, "updated_at": 1,
            "created_by": 1, "created_by_name": 1,
            "resume_file_id": 1, "resume_filename": 1, "resume_url": 1, "resume_link": 1,
            "profile_snapshot": 1, "profile": 1,
        }
        async for d in db["sales_assessments"].find(q, proj).sort("updated_at", -1).limit(limit):
            cards.append(_build_assessment_card(d))

    # 4) Pre-assessments (grouped by stage)
    pa_stage_filter: Optional[Dict[str, Any]] = None
    if want_all and not is_navratri_stage:
        pa_stage_filter = {}
    elif stage in PA_STAGE_GROUPS and not is_navratri_stage:
        pa_stage_filter = {"stage": {"$in": list(PA_STAGE_GROUPS[stage])}}

    if pa_stage_filter is not None and not is_navratri_stage:
        q = own_filter_pa | pa_stage_filter
        if text_re:
            q["client_name"] = text_re
        proj = {
            "_id": 0, "id": 1, "pa_number": 1, "client_name": 1, "client_email": 1, "client_phone": 1,
            "stage": 1, "target_country": 1, "eligibility_score": 1, "created_at": 1, "updated_at": 1,
            "partner_id": 1, "partner_name": 1,
            "resume_file_id": 1, "resume_filename": 1, "resume_url": 1,
            "profile_snapshot": 1,
        }
        async for d in db["pre_assessments"].find(q, proj).sort("updated_at", -1).limit(limit):
            st = d.get("stage")
            for group, members in PA_STAGE_GROUPS.items():
                if st in members:
                    cards.append(_build_pa_card(d, group))
                    break

    # Navratri status filter
    if navratri_status and is_navratri_stage:
        if navratri_status == "paid_resume_received":
            cards = [c for c in cards if c.get("navratri_category") == "paid_resume_received"]
        elif navratri_status == "paid_resume_pending":
            cards = [c for c in cards if c.get("navratri_category") == "paid_resume_pending"]
        elif navratri_status == "unpaid":
            cards = [c for c in cards if c.get("navratri_category") in ("unpaid", "unpaid_with_resume", "unpaid_without_resume")]
        elif navratri_status == "unpaid_with_resume":
            cards = [c for c in cards if c.get("navratri_category") == "unpaid_with_resume"]
        elif navratri_status == "unpaid_without_resume":
            cards = [c for c in cards if c.get("navratri_category") == "unpaid_without_resume"]

    # Filter
    if filter == "paid_report_pending":
        cards = [
            c for c in cards
            if (c.get("payment_status") in ("success", "paid", "completed", "captured") or (c.get("payment_amount") or 0) > 0)
            and not c.get("report_generated")
        ]

    if has_resume is True or filter == "with_resume":
        cards = [c for c in cards if c.get("has_resume")]
    elif has_resume is False or filter == "without_resume":
        cards = [c for c in cards if not c.get("has_resume")]


    # Sort
    def _sort_key_recent(c):
        u = c.get("created_at") or c.get("updated_at")
        if isinstance(u, str):
            try: u = datetime.fromisoformat(u.replace("Z", "+00:00"))
            except ValueError: u = None
        dt_val = u or datetime.min.replace(tzinfo=timezone.utc)
        
        # Extract numeric registration sequence from unique_id (e.g. NN2427111 -> 2427111)
        uid = str(c.get("unique_id") or "")
        digits = "".join(ch for ch in uid if ch.isdigit())
        num_part = int(digits) if digits else 0
        return (dt_val, num_part)

    if sort == "paid_first":
        cards.sort(key=lambda c: (
            1 if c.get("payment_status") in ("success", "paid", "completed", "captured") or (c.get("payment_amount") or 0) > 0 else 0,
            _sort_key_recent(c)
        ), reverse=True)
    elif sort == "oldest":
        cards.sort(key=_sort_key_recent)
    elif sort == "score_desc":
        cards.sort(key=lambda c: c.get("score") or -1, reverse=True)
    elif sort == "score_asc":
        cards.sort(key=lambda c: c.get("score") or 999999)
    else:  # recent (default)
        cards.sort(key=_sort_key_recent, reverse=True)

    cards = cards[:limit]

    # Stringify datetime fields for JSON
    for c in cards:
        if isinstance(c.get("updated_at"), datetime):
            c["updated_at"] = c["updated_at"].isoformat()
        if isinstance(c.get("created_at"), datetime):
            c["created_at"] = c["created_at"].isoformat()

    return {"items": cards, "count": len(cards), "as_of": datetime.now(timezone.utc).isoformat()}


@router.get("/brief")
async def get_ai_brief(current_user: dict = Depends(get_current_user)):
    """AI Brief panel — actionable stats for the right sidebar."""
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=48)

    leads_q = _own_lead_query(current_user) | {
        "stage": {"$ne": "converted"},
        "$or": [{"last_contacted_at": None}, {"last_contacted_at": {"$lt": stale_cutoff}}],
    }
    stale_leads_n = await db["leads"].count_documents(leads_q)

    pa_q = _own_pa_query(current_user) | {"stage": "payment_pending"}
    payment_pending_n = await db["pre_assessments"].count_documents(pa_q)

    pa_q2 = _own_pa_query(current_user) | {"stage": "proposal_sent"}
    proposals_pending_n = await db["pre_assessments"].count_documents(pa_q2)

    verify_q = {"status": {"$in": ["draft", "unverified"]}}
    pending_verify_n = await db["country_templates"].count_documents(verify_q)

    insights = []
    if stale_leads_n:
        insights.append({
            "icon": "alert",
            "title": f"{stale_leads_n} leads not contacted in 48 hours",
            "cta_label": "Open Pre-Assessments",
            "cta_link": "/admin?tab=pre-assessments",
            "urgency": "high",
        })
    if payment_pending_n:
        insights.append({
            "icon": "clock",
            "title": f"{payment_pending_n} PA fee window closing soon",
            "cta_label": "Send Reminder",
            "cta_link": "/admin?tab=pre-assessments",
            "urgency": "medium",
        })
    if proposals_pending_n:
        insights.append({
            "icon": "mail",
            "title": f"{proposals_pending_n} proposals awaiting client decision",
            "cta_label": "Follow Up",
            "cta_link": "/admin?tab=pre-assessments",
            "urgency": "medium",
        })
    if pending_verify_n:
        insights.append({
            "icon": "shield",
            "title": f"{pending_verify_n} KB items awaiting verification",
            "cta_label": "Verify Hub",
            "cta_link": "/admin/verify-hub",
            "urgency": "low",
        })

    return {
        "insights": insights,
        "counts": {
            "stale_leads": stale_leads_n,
            "payment_pending": payment_pending_n,
            "proposals_pending": proposals_pending_n,
            "pending_verify": pending_verify_n,
        },
        "as_of": now.isoformat(),
    }


@router.get("/card/{kind}/{ref_id}")
async def get_card_detail(
    kind: str, ref_id: str, current_user: dict = Depends(get_current_user)
):
    """Drill-in detail for a single card."""
    if kind == "lead":
        d = await db["leads"].find_one({"id": ref_id}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="Lead not found")
        if not _is_admin(current_user) and d.get("assigned_to") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your lead")

        # Resolve bulk_batch_id and report generation if not on doc
        if not d.get("bulk_batch_id") or not d.get("report_generated"):
            row_match = await db["bulk_assessment_rows"].find_one(
                {"$or": [
                    {"lead_id": d.get("id")},
                    {"parsed.email": {"$regex": f"^{re.escape(str(d.get('email') or '').strip())}$", "$options": "i"}} if d.get("email") else {"_id": None},
                ]},
                {"batch_id": 1, "status": 1, "snapshot_id": 1}
            )
            if row_match:
                if row_match.get("batch_id"):
                    d["bulk_batch_id"] = row_match["batch_id"]
                if row_match.get("status") == "generated" or row_match.get("snapshot_id"):
                    d["report_generated"] = True
                    d["report_status"] = "generated"

        # Format string date fields
        for f in ("created_at", "updated_at", "paid_at", "last_contacted_at"):
            if isinstance(d.get(f), datetime):
                d[f] = d[f].isoformat()
        return {
            "kind": "lead",
            "record": d,
            "deep_link": f"/sales/client-assessment?lead_id={d.get('id')}",
            "lifecycle": [{"key": "lead_captured", "label": "Lead Captured",
                          "completed": True, "timestamp": d.get("created_at")}],
        }


    if kind == "assessment":
        d = await db["sales_assessments"].find_one({"id": ref_id}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="Assessment not found")
        if not _is_admin(current_user) and d.get("created_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your assessment")
        for f in ("created_at", "updated_at"):
            if isinstance(d.get(f), datetime):
                d[f] = d[f].isoformat()
        
        snap = d.get("profile_snapshot") or {}
        pri = snap.get("primary_applicant") or {}
        resume_fid = d.get("resume_file_id") or snap.get("resume_file_id") or pri.get("resume_file_id")
        has_resume = bool(resume_fid or d.get("resume_url") or snap.get("resume_url") or d.get("resume_link"))
        resume_fname = (
            d.get("resume_filename")
            or snap.get("resume_filename")
            or pri.get("resume_filename")
            or ("Resume.pdf" if has_resume else None)
        )
        resume_link = f"/cockpit/resume/{resume_fid}" if resume_fid else (d.get("resume_url") or snap.get("resume_url") or d.get("resume_link") or "")

        return {
            "kind": "assessment",
            "record": d,
            "record_id": d.get("id"),
            "name": d.get("client_name"),
            "email": d.get("client_email") or (d.get("profile") or {}).get("email") or "",
            "phone": d.get("client_phone") or (d.get("profile") or {}).get("phone") or "",
            "best_country": d.get("best_country_code"),
            "best_total": d.get("best_total"),
            "latest_report_id": d.get("latest_report_snapshot_id"),
            "results_count": len(d.get("results") or []),
            "deep_link": f"/sales/client-assessment?id={d.get('id')}",
            "has_resume": has_resume,
            "resume_file_id": resume_fid,
            "resume_filename": resume_fname,
            "resume_url": resume_link,
        }

    if kind == "pa":
        d = await db["pre_assessments"].find_one({"id": ref_id}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="Pre-Assessment not found")
        if not _is_admin(current_user) and d.get("partner_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your pre-assessment")
        for f in ("created_at", "updated_at"):
            if isinstance(d.get(f), datetime):
                d[f] = d[f].isoformat()

        snap = d.get("profile_snapshot") or {}
        pri = snap.get("primary_applicant") or {}
        resume_fid = d.get("resume_file_id") or snap.get("resume_file_id") or pri.get("resume_file_id")
        has_resume = bool(resume_fid or d.get("resume_url") or snap.get("resume_url"))
        resume_fname = (
            d.get("resume_filename")
            or snap.get("resume_filename")
            or pri.get("resume_filename")
            or ("Resume.pdf" if has_resume else None)
        )
        resume_link = f"/cockpit/resume/{resume_fid}" if resume_fid else (d.get("resume_url") or snap.get("resume_url") or "")

        return {
            "kind": "pa",
            "record": d,
            "record_id": d.get("id"),
            "pa_number": d.get("pa_number"),
            "name": d.get("client_name"),
            "email": d.get("client_email") or "",
            "phone": d.get("client_phone") or "",
            "stage": d.get("stage"),
            "deep_link": "/admin?tab=pre-assessments",
            "has_resume": has_resume,
            "resume_file_id": resume_fid,
            "resume_filename": resume_fname,
            "resume_url": resume_link,
        }

    raise HTTPException(status_code=400, detail=f"Unknown kind: {kind}")


# ─── Navratri Campaign Automation Endpoints ─────────────────────────────────

@router.post("/navratri/send-resume-request")
async def api_send_navratri_resume_request(
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    """Dispatches secure resume upload link via Email and WhatsApp to specified lead(s)."""
    lead_ids = payload.get("lead_ids") or []
    if isinstance(payload.get("lead_id"), str):
        lead_ids = [payload["lead_id"]]
    
    if not lead_ids:
        raise HTTPException(status_code=400, detail="No lead_ids specified.")

    sender_name = current_user.get("name") or "LEAMSS Migration Team"
    leads = await db["leads"].find({"id": {"$in": lead_ids}}).to_list(len(lead_ids))
    
    results = []
    for l in leads:
        res = await send_navratri_resume_request(l, sender_name=sender_name)
        results.append(res)

    sent_count = sum(1 for r in results if r.get("email_sent") or r.get("whatsapp_sent"))
    return {
        "ok": True,
        "total_requested": len(lead_ids),
        "dispatched_count": sent_count,
        "results": results,
    }


@router.post("/navratri/send-payment-link")
async def api_send_navratri_payment_link(
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    """Dispatches Navratri Special Offer payment link via Email and WhatsApp to specified lead(s)."""
    lead_ids = payload.get("lead_ids") or []
    if isinstance(payload.get("lead_id"), str):
        lead_ids = [payload["lead_id"]]
    payment_url = payload.get("payment_url")

    if not lead_ids:
        raise HTTPException(status_code=400, detail="No lead_ids specified.")

    leads = await db["leads"].find({"id": {"$in": lead_ids}}).to_list(len(lead_ids))
    
    results = []
    for l in leads:
        res = await send_navratri_payment_link(l, payment_url_override=payment_url)
        results.append(res)

    sent_count = sum(1 for r in results if r.get("email_sent") or r.get("whatsapp_sent"))
    return {
        "ok": True,
        "total_requested": len(lead_ids),
        "dispatched_count": sent_count,
        "results": results,
    }


@router.post("/navratri/mark-paid")
async def api_mark_navratri_lead_paid(
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    """Manually marks a Navratri lead as Paid and transitions them to Paid list.
    
    If resume is already present, status becomes 'paid_resume_received' (Ready for bulk assessment).
    If resume is missing, status becomes 'paid_resume_pending' and auto-dispatches resume upload link.
    """
    lead_id = payload.get("lead_id")
    if not lead_id:
        raise HTTPException(status_code=400, detail="lead_id is required.")

    payment_mode = payload.get("payment_mode", "upi")
    payment_amount = payload.get("payment_amount", 1.0)
    trigger_auto_resume = payload.get("trigger_auto_resume_request", True)

    try:
        res = await mark_lead_paid_and_transition(
            lead_id=lead_id,
            payment_mode=payment_mode,
            payment_amount=payment_amount,
            trigger_auto_resume_request=trigger_auto_resume,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/navratri/bulk-process-pre-assessment")
async def api_bulk_process_navratri(
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    """Enqueues all selected or all 'Paid · Resume Received' Navratri leads whose reports are pending into Bulk Pre-Assessment batch for Report Generation."""
    from routers.bulk_assessments import create_batch_from_leads
    lead_ids = payload.get("lead_ids") or []
    
    # If no specific IDs provided, get all Navratri paid leads with resume whose report is pending
    if not lead_ids:
        q = NAVRATRI_QUERY | {
            "$or": [
                {"payment_status": {"$in": ["success", "paid", "completed", "captured"]}},
                {"payment_amount": {"$gt": 0}},
                {"stage": "payment_done"}
            ],
            "$and": [
                {"$or": [
                    {"resume_file_id": {"$exists": True, "$ne": None, "$ne": ""}},
                    {"resume_url": {"$exists": True, "$ne": None, "$ne": ""}},
                    {"resume_path": {"$exists": True, "$ne": None, "$ne": ""}},
                    {"resume_uploaded": True}
                ]},
                {"report_generated": {"$ne": True}},
                {"report_status": {"$nin": ["generated", "completed"]}},
                {"latest_report_snapshot_id": {"$in": [None, ""]}},
                {"assessment_report_id": {"$in": [None, ""]}},
                {"bulk_batch_id": {"$in": [None, ""]}}
            ]
        }
        cursor = db["leads"].find(q, {"id": 1}).limit(500)
        async for row in cursor:
            if row.get("id"):
                lead_ids.append(row["id"])

    if not lead_ids:
        raise HTTPException(status_code=404, detail="No Paid Navratri leads with resumes found pending report generation.")

    batch_res = await create_batch_from_leads(
        payload={
            "lead_ids": lead_ids,
            "paid_only": True,
            "report_pending_only": payload.get("report_pending_only", True),
            "batch_name": f"Navratri Offer Paid Batch ({datetime.now(timezone.utc).strftime('%d %b %Y %H:%M')})",
        },
        current_user=current_user,
    )
    return {
        "ok": True,
        "leads_queued_count": batch_res.get("total", len(lead_ids)),
        "batch_id": batch_res.get("batch_id"),
        "batch_info": batch_res,
    }


