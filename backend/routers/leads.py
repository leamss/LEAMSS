"""Leads & Complete CRM Pipeline Router"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, UploadFile, File, Form, Request
from core.database import db, users_col, cases_col, sales_col
from core.auth import get_current_user, get_current_user_optional, get_password_hash
from core.services import log_activity, create_notification
from datetime import datetime, timezone, timedelta, date
import uuid
import re
import csv
import io
import json
import logging
from urllib.parse import unquote
import openpyxl
from typing import Optional, List, Dict, Any, Set, Union

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])
leads_col = db["leads"]
follow_ups_col = db["follow_ups"]
crm_deals_col = db["crm_deals"]
crm_calls_col = db["crm_calls"]
crm_whatsapp_col = db["crm_whatsapp_messages"]
crm_emails_col = db["crm_emails"]
crm_tasks_col = db["crm_tasks"]
crm_meetings_col = db["crm_meetings"]
crm_payments_col = db["crm_payments"]
audit_logs_col = db["audit_logs"]


SALESPERSON_ROLES = [
    "partner", "external_partner", "external_salesperson",
    "sales_executive", "sr_sales_executive", "senior_sales_executive",
    "sales_rep", "sales_person", "sales", "internal_salesperson", "sales_consultant"
]


def _is_admin(user: dict) -> bool:
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in ["admin", "admin_owner", "super_admin"] or rbac in ["admin", "admin_owner", "super_admin"]


def _is_sales_person(user: dict) -> bool:
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in SALESPERSON_ROLES or rbac in SALESPERSON_ROLES


def _is_manager_or_admin(user: dict) -> bool:
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in ["admin", "admin_owner", "super_admin", "sales_manager", "sales_head"] or rbac in ["admin_owner", "sales_manager", "sales_head", "admin", "super_admin"]


async def _next_lead_number():
    """Generate a sequential lead number like LD006672."""
    count = await leads_col.count_documents({})
    return f"LD{(count + 6620):06d}"


def calculate_lead_score(lead: dict) -> tuple:
    """Calculate numerical score (0-100) and category (HOT, WARM, COLD)."""
    score = 20  # base
    # Source
    src = str(lead.get("source", "")).lower()
    if any(k in src for k in ["referral", "google", "website", "direct"]):
        score += 20
    elif any(k in src for k in ["facebook", "instagram", "ads"]):
        score += 15
    else:
        score += 10
    
    # Completeness
    if lead.get("email") and lead.get("phone"):
        score += 10
    if lead.get("occupation") or lead.get("latest_qualification"):
        score += 10
    if lead.get("country_of_interest") or lead.get("interested_country"):
        score += 10
    if lead.get("budget") and str(lead.get("budget")) not in ["", "0"]:
        score += 15
    
    # Engagement
    calls = int(lead.get("call_count", 0))
    if calls > 0:
        score += min(15, calls * 5)
    
    score = min(100, score)
    category = "HOT" if score >= 70 else "WARM" if score >= 40 else "COLD"
    return score, category


async def process_capture_lead(
    data: dict,
    uploaded_file: Optional[UploadFile] = None,
    current_user: Optional[dict] = None
) -> dict:
    from services.spam_filter import is_spam_or_fake_lead
    if is_spam_or_fake_lead(data):
        raise HTTPException(status_code=400, detail="Submission rejected: Spam or invalid entry detected.")

    lead_number = data.get("lead_number") or await _next_lead_number()
    score, category = calculate_lead_score(data)
    now = datetime.now(timezone.utc)

    # ── Auto-Capture & Persist Resume Attachment ──
    resume_fid = None
    resume_fname = None
    resume_download_url = None

    if uploaded_file and uploaded_file.filename:
        file_bytes = await uploaded_file.read()
        if file_bytes:
            from core.resume_service import save_resume_to_gridfs
            resume_fname = uploaded_file.filename
            resume_fid, resume_download_url = await save_resume_to_gridfs(
                filename=resume_fname,
                file_bytes=file_bytes,
                content_type=uploaded_file.content_type,
                metadata={
                    "source": "website_form_upload",
                    "uploaded_at": now.isoformat(),
                }
            )

    raw_resume_url = (
        data.get("resume_url")
        or data.get("resume_path")
        or data.get("resume_link")
        or data.get("resume")
        or data.get("file_url")
        or ""
    )
    if not resume_fid and raw_resume_url:
        resume_download_url = str(raw_resume_url).strip()
        resume_fname = data.get("resume_filename") or unquote(resume_download_url.split("/")[-1].split("?")[0]) or "resume.pdf"
        from core.resume_service import fetch_resume_from_external_or_path, save_resume_to_gridfs
        try:
            res_fetched = await fetch_resume_from_external_or_path(resume_download_url)
            if res_fetched:
                raw_bytes, fname, ctype = res_fetched
                resume_fname = fname
                resume_fid, resume_download_url = await save_resume_to_gridfs(
                    filename=fname,
                    file_bytes=raw_bytes,
                    content_type=ctype,
                    metadata={"source": "website_form_url_auto_cached", "original_url": raw_resume_url}
                )
        except Exception as e:
            logger.warning(f"Failed to auto-cache resume from {raw_resume_url}: {e}")

    raw_assigned_to = data.get("assigned_to")
    if raw_assigned_to in ["unassigned", "none", "", None]:
        assigned_to = None
        assigned_name = None
    else:
        assigned_to = str(raw_assigned_to).strip()
        assigned_name = data.get("assigned_to_name", "")

    country = data.get("country_of_interest") or data.get("interested_country") or data.get("country", "")
    service = data.get("service_interested") or data.get("service_type") or data.get("services", "")

    created_by = None
    created_by_name = None
    created_by_role = None
    partner_id = None
    partner_name = None

    if current_user:
        created_by = current_user.get("id")
        created_by_name = current_user.get("name", "User")
        created_by_role = current_user.get("role")

        # If created by Partner
        if current_user.get("role") == "partner" or current_user.get("rbac_role") == "partner":
            partner_id = current_user.get("id")
            partner_name = current_user.get("name", "Partner")
            if not assigned_to:
                assigned_to = current_user.get("id")
                assigned_name = current_user.get("name", "Partner")

        # If created by Sales Executive / Specialist / Manager / Admin
        elif _is_sales_person(current_user) or _is_manager_or_admin(current_user):
            if not assigned_to:
                assigned_to = current_user.get("id")
                assigned_name = current_user.get("name", "Sales Representative")

    # If assigned_to was passed as ID, resolve its name
    if assigned_to and not assigned_name:
        u = await users_col.find_one({"id": assigned_to}, {"_id": 0, "name": 1})
        if u:
            assigned_name = u.get("name", "")

    # Public landing page or website enquiry: keep unassigned until Admin assigns
    if not assigned_to and not current_user:
        assigned_to = None
        assigned_name = "Unassigned"

    from services.lead_source_tracker import detect_lead_source
    canonical_source, original_source, source_details = detect_lead_source(
        data,
        default_source="Direct Entry" if current_user else "Website"
    )
    page_title = str(data.get("website_page_title") or data.get("page_title") or "").strip()
    page_url = str(data.get("website_page_url") or data.get("page_url") or "").strip()
    if (not page_title or not page_url or page_url in ("https://leamss.com", "https://leamss.com/")) and not current_user:
        from routers.crm_website_leads import resolve_page_details
        res_title, res_url, _ = resolve_page_details(data)
        if not page_title or "Migrate Abroad from India" in page_title or page_title == "LEAMSS Official Website Enquiry":
            page_title = res_title
        if not page_url or page_url in ("https://leamss.com", "https://leamss.com/"):
            page_url = res_url

    lead_cat = str(data.get("lead_category") or data.get("category") or "").strip()
    if not lead_cat:
        from routers.crm_website_leads import classify_lead_category
        lead_cat = classify_lead_category({
            **data,
            "service_interested": service,
            "message": data.get("message") or data.get("msg", "")
        })

    lead = {
        "id": str(uuid.uuid4()),
        "lead_number": lead_number,
        "name": str(data.get("name", "")).strip(),
        "email": str(data.get("email", "")).strip(),
        "phone": str(data.get("phone", "")).strip(),
        "alternate_phone": str(data.get("alternate_phone", "")).strip(),
        "whatsapp_number": str(data.get("whatsapp_number") or data.get("phone", "")).strip(),
        "address": str(data.get("address", "")).strip(),
        "city": str(data.get("city", "")).strip(),
        "country": str(data.get("country") or data.get("country_of_interest") or "").strip(),
        "service_interested": service,
        "service_type": service,
        "services": service,
        "country_of_interest": country,
        "interested_country": country,
        "interested_program": str(data.get("interested_program", "")).strip(),
        "visa_type": str(data.get("visa_type", "")).strip(),
        "visa_pathway": str(data.get("visa_pathway") or service or "").strip(),
        "lead_category": lead_cat,
        "website_page_title": page_title,
        "website_page_url": page_url,
        "budget": str(data.get("budget", "")).strip(),
        "message": str(data.get("message") or data.get("msg") or "").strip(),
        "enquired_for": str(data.get("enquired_for") or "").strip(),
        "source": canonical_source,
        "original_source": original_source,
        "source_details": source_details,
        "subsource": data.get("subsource", ""),
        "campaign": data.get("campaign", data.get("utm_campaign", "Manual Direct" if current_user else "Organic")),
        "utm_source": source_details.get("utm_source") or data.get("utm_source", ""),
        "utm_medium": source_details.get("utm_medium") or data.get("utm_medium", ""),
        "utm_campaign": source_details.get("utm_campaign") or data.get("utm_campaign", ""),
        "stage": data.get("stage", "new"),
        "status": data.get("status", data.get("stage", "new")),
        "priority": data.get("priority", "medium"),
        "lead_score": score,
        "score_category": category,
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_name,
        "assigned_at": now if assigned_to else None,
        "assigned_by": (current_user.get("id") if current_user else None) if assigned_to else None,
        "assigned_by_name": (current_user.get("name", "Admin") if current_user else None) if assigned_to else None,
        "assigned_manager_id": data.get("assigned_manager_id"),
        "created_by": created_by,
        "created_by_name": created_by_name,
        "created_by_role": created_by_role,
        "partner_id": partner_id,
        "partner_name": partner_name,
        "date_of_birth": str(data.get("date_of_birth", "")).strip(),
        "occupation": str(data.get("occupation") or data.get("job_title") or data.get("designation") or "").strip(),
        "total_work_experience": str(data.get("total_work_experience") or data.get("experience") or data.get("work_experience") or data.get("work_exp") or "").strip(),
        "work_experience": str(data.get("work_experience") or data.get("total_work_experience") or data.get("work_exp") or "").strip(),
        "work_exp": str(data.get("work_exp") or "").strip(),
        "backlogs": str(data.get("backlogs", "")).strip(),
        "lead_type": str(data.get("lead_type", "")).strip(),
        "latest_qualification": str(data.get("latest_qualification") or data.get("qualification") or data.get("education") or "").strip(),
        "qualification": str(data.get("qualification") or data.get("latest_qualification") or data.get("education") or "").strip(),
        "university": str(data.get("university", "")).strip(),
        "course": str(data.get("course", "")).strip(),
        "atlas_code": str(data.get("atlas_code") or "").strip() or None,
        "atlas_title": str(data.get("atlas_title") or "").strip() or None,
        "tags": list(set(list(data.get("tags") or []) + (["atlas", "public_atlas"] if (lead_cat == "Atlas" or data.get("atlas_code") or data.get("atlas_title")) else []))),
        "notes": data.get("notes", []),
        "call_count": 0,
        "created_at": now,
        "updated_at": now,
        "last_contacted_at": None,
        "next_follow_up": data.get("next_follow_up"),
        "converted": False,
        "converted_sale_id": None,
        "converted_client_id": None,
        "company_id": data.get("company_id") or "comp_leamss_primary",
        "resume_file_id": resume_fid,
        "resume_filename": resume_fname if (resume_fid or resume_download_url) else None,
        "resume_url": resume_download_url,
        "resume_path": resume_download_url,
        "resume_uploaded": bool(resume_fid or resume_download_url),
        "resume_uploaded_at": now if (resume_fid or resume_download_url) else None,
    }
    await leads_col.insert_one(lead)

    # Sync to connected Google Sheets in real-time
    try:
        from services.integrations.google_services import sync_lead_to_connected_sheets
        await sync_lead_to_connected_sheets(lead)
    except Exception:
        pass

    # If resume was attached, cascade sync
    if resume_fid:
        try:
            from core.resume_service import attach_and_sync_resume
            await attach_and_sync_resume(
                lead_id=lead["id"],
                file_id_str=resume_fid,
                filename=resume_fname or "resume.pdf",
                uploaded_by={"id": "website_form", "name": lead.get("name") or "Website Visitor"}
            )
        except Exception:
            pass

    if "_id" in lead:
        lead["_id"] = str(lead["_id"])
    return lead


@router.post("/capture")
async def capture_lead(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Create a lead — handles JSON, Form, and Multipart file uploads (resume attachments) from landing pages, website forms, or authenticated users."""
    if isinstance(request, dict):
        return await process_capture_lead(data=request, current_user=current_user)

    content_type = request.headers.get("content-type", "")
    uploaded_file: Optional[UploadFile] = None
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            data = {}
    else:
        form = await request.form()
        data = {}
        for k, v in form.items():
            if hasattr(v, "filename") and hasattr(v, "read"):
                uploaded_file = v
            else:
                data[k] = v
        for file_key in ("resume", "file", "cv", "resume_file", "attachment"):
            fv = form.get(file_key)
            if hasattr(fv, "filename") and hasattr(fv, "read") and fv.filename:
                uploaded_file = fv
                break

    return await process_capture_lead(data=data, uploaded_file=uploaded_file, current_user=current_user)

    # Initial activity
    creator_user_name = created_by_name or data.get("creator_name") or "System / Landing Page"
    creator_user_id = created_by or data.get("creator_id") or "system"
    await log_activity(
        user_id=creator_user_id,
        user_name=creator_user_name,
        action="lead_created",
        entity_type="lead",
        entity_id=lead["id"],
        details=f"Lead {lead['name']} ({lead_number}) created from {lead['source']} (Score: {score} - {category})"
    )

    if assigned_to and assigned_to != created_by:
        await create_notification(
            user_id=assigned_to,
            title="New Lead Assigned",
            message=f"You have been assigned lead: {lead['name']} ({lead['phone']})",
            notification_type="lead_assigned",
            related_id=lead["id"]
        )

    return {"message": "Lead saved successfully.", "lead_id": lead["id"], "lead_number": lead_number, "lead": {k: v for k, v in lead.items() if k != "_id"}}


@router.get("/")
async def get_leads(
    stage: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    campaign: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    score_category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    report_status: Optional[str] = Query(None),
    limit: int = Query(200),
    current_user: dict = Depends(get_current_user)
):
    """Get all leads with role-based restriction and multi-criteria filters"""
    and_conditions = [
        {
            "is_spam": {"$ne": True},
            "source": {"$ne": "Sample Leads"},
            "email": {"$not": {"$regex": "@example\\.com$|merepost\\.com|myxa\\.cc", "$options": "i"}},
            "name": {"$not": {"$regex": "scam\\s*service|myxa\\.cc|<a\\s+href|\\[url=", "$options": "i"}}
        }
    ]
    
    st = stage or status
    if st and st != "all":
        and_conditions.append({"$or": [{"stage": st}, {"status": st}]})
    if source and source != "all":
        s_clean = source.strip()
        if s_clean.lower() == "unknown":
            and_conditions.append({
                "$or": [
                    {"source": "Unknown"},
                    {"source": None},
                    {"source": ""},
                    {"source": {"$exists": False}}
                ]
            })
        elif s_clean.lower() in ["google sheets", "google_sheets"]:
            and_conditions.append({"$or": [{"source": "Google Sheets"}, {"source": "Google_sheets"}]})
        elif s_clean.lower() in ["facebook ads", "facebook"]:
            and_conditions.append({"$or": [{"source": "Facebook Ads"}, {"source": "Facebook"}]})
        elif s_clean.lower() in ["website", "website popup"]:
            and_conditions.append({"$or": [{"source": "Website"}, {"source": "Website Popup"}, {"source": "website"}]})
        elif s_clean.lower() in ["zoho", "zoho crm"]:
            and_conditions.append({"$or": [{"source": "Zoho"}, {"source": "Zoho CRM"}]})
        elif s_clean.lower() in ["calendly", "calendly bookings"]:
            cal_meeting_leads = await crm_meetings_col.distinct("lead_id", {"source": "calendly", "lead_id": {"$ne": None}})
            cal_meeting_emails = await crm_meetings_col.distinct("contact_email", {"source": "calendly", "contact_email": {"$ne": ""}})
            or_clauses = [
                {"source": {"$regex": "^calendly$", "$options": "i"}},
                {"has_booking": True},
                {"tags": "calendly"}
            ]
            if cal_meeting_leads:
                or_clauses.append({"id": {"$in": cal_meeting_leads}})
            if cal_meeting_emails:
                or_clauses.append({"email": {"$in": cal_meeting_emails}})
            and_conditions.append({"$or": or_clauses})
        else:
            and_conditions.append({"source": {"$regex": f"^{re.escape(s_clean)}$", "$options": "i"}})
    if campaign and campaign != "all":
        and_conditions.append({"campaign": campaign})
    if country and country != "all":
        and_conditions.append({"$or": [{"country_of_interest": country}, {"interested_country": country}, {"country": country}]})
    if score_category and score_category != "all":
        and_conditions.append({"score_category": score_category})
    if priority and priority != "all":
        and_conditions.append({"priority": priority})

    # Role check: ONLY Admin can view all leads and filter by assigned_to;
    # Non-admins (Salespersons, Sales Executives, Partners, Sales Staff) can ONLY view leads assigned to them.
    if _is_admin(current_user):
        if assigned_to and assigned_to != "all":
            if assigned_to.lower() == "unassigned":
                and_conditions.append({
                    "$or": [
                        {"assigned_to": None},
                        {"assigned_to": ""},
                        {"assigned_to": "unassigned"},
                        {"assigned_to": {"$exists": False}}
                    ]
                })
            else:
                and_conditions.append({
                    "$or": [
                        {"assigned_to": assigned_to},
                        {"assigned_sales_rep_id": assigned_to},
                        {"assigned_sales_person_id": assigned_to},
                        {"assigned_to_name": {"$regex": f"^{re.escape(assigned_to)}$", "$options": "i"}},
                        {"assigned_sales_person_name": {"$regex": f"^{re.escape(assigned_to)}$", "$options": "i"}},
                        {"assigned_to_email": assigned_to.lower()}
                    ]
                })
    else:
        user_id = str(current_user.get("id") or "").strip()
        user_email = str(current_user.get("email") or "").strip().lower()
        user_name = str(current_user.get("name") or "").strip()
        user_first = user_name.split()[0] if user_name else ""
        assigned_or = []
        if user_id:
            assigned_or.append({"assigned_to": user_id})
            assigned_or.append({"assigned_sales_rep_id": user_id})
            assigned_or.append({"assigned_sales_person_id": user_id})
            assigned_or.append({"sales_person_id": user_id})
            assigned_or.append({"created_by": user_id})
            assigned_or.append({"partner_id": user_id})
            assigned_or.append({"block_assigned_to": user_id})
        if user_email:
            assigned_or.append({"assigned_to": user_email})
            assigned_or.append({"assigned_to_email": user_email})
            assigned_or.append({"assigned_to": {"$regex": f"^{re.escape(user_email)}$", "$options": "i"}})
            assigned_or.append({"assigned_to_email": {"$regex": f"^{re.escape(user_email)}$", "$options": "i"}})
        if user_name:
            assigned_or.append({"assigned_to": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
            assigned_or.append({"assigned_to_name": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
            assigned_or.append({"assigned_sales_person_name": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
            assigned_or.append({"created_by_name": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
        if user_first and len(user_first) >= 3:
            assigned_or.append({"assigned_to": {"$regex": f"^{re.escape(user_first)}$", "$options": "i"}})
            assigned_or.append({"assigned_to_name": {"$regex": f"^{re.escape(user_first)}$", "$options": "i"}})
            assigned_or.append({"assigned_sales_person_name": {"$regex": f"^{re.escape(user_first)}$", "$options": "i"}})
        and_conditions.append({"$or": assigned_or if assigned_or else [{"assigned_to": "__none__"}]})

    if search:
        s_regex = {"$regex": search, "$options": "i"}
        and_conditions.append({
            "$or": [
                {"name": s_regex},
                {"email": s_regex},
                {"phone": s_regex},
                {"lead_number": s_regex},
                {"whatsapp_number": s_regex},
                {"city": s_regex},
                {"service_interested": s_regex},
                {"occupation": s_regex}
            ]
        })

    query = {"$and": and_conditions} if and_conditions else {}
    leads = await leads_col.find(query, {"_id": 0}).sort([("lead_number", -1), ("updated_at", -1), ("created_at", -1)]).to_list(limit)
    
    from core.navratri_automation import is_lead_paid, has_lead_resume
    enriched_leads = []
    for lead in leads:
        paid = is_lead_paid(lead)
        resume = has_lead_resume(lead)
        lead["is_paid"] = paid
        lead["has_resume"] = resume
        if paid and not lead.get("payment_status"):
            lead["payment_status"] = "paid"
        elif not paid and not lead.get("payment_status"):
            lead["payment_status"] = "unpaid"

        if not lead.get("payment_amount"):
            lead["payment_amount"] = lead.get("amount") or 2427.0
        if "amount_paid" not in lead or lead.get("amount_paid") is None:
            lead["amount_paid"] = lead["payment_amount"] if paid else 0.0
        
        has_report = bool(
            lead.get("report_generated") is True
            or lead.get("report_status") in ("generated", "completed")
            or lead.get("latest_report_snapshot_id")
            or lead.get("assessment_report_id")
        )
        lead["report_generated"] = has_report
        lead["report_status"] = "generated" if has_report else (lead.get("report_status") or "pending")
        if has_report and not lead.get("assessment_report_id"):
            lead["assessment_report_id"] = lead.get("latest_report_snapshot_id")

        for field in ["created_at", "updated_at", "last_contacted_at", "assigned_at", "converted_at"]:
            if isinstance(lead.get(field), datetime):
                lead[field] = lead[field].isoformat()

        # Route external leamss.com resumes through proxy to prevent X-Frame-Options iframe blocking
        r_url = lead.get("resume_url") or lead.get("resume_path") or ""
        if r_url and "leamss.com" in r_url and "api.leamss.com" not in r_url:
            from urllib.parse import quote
            lead["resume_url"] = f"/api/cockpit/resume-proxy?url={quote(r_url, safe='')}"

        # Guarantee newest leads (LD006997+) have freshest timestamp so all frontend versions sort them to top
        lead_num_int = 0
        ln_str = str(lead.get("lead_number") or "")
        m_ln = re.search(r"\d+", ln_str)
        if m_ln:
            lead_num_int = int(m_ln.group(0))
        if lead_num_int >= 6997:
            lead["updated_at"] = datetime.now(timezone.utc).isoformat()
            lead["created_at"] = lead.get("created_at") or lead["updated_at"]

        # Apply payment / report filtering if requested
        if payment_status:
            p_val = payment_status.strip().lower()
            if p_val == "paid" and not paid:
                continue
            elif p_val == "unpaid" and (paid or lead.get("payment_status") == "failed"):
                continue
            elif p_val == "failed" and lead.get("payment_status") != "failed":
                continue
            elif p_val == "partially_paid" and lead.get("payment_status") != "partially_paid":
                continue

        if report_status == "generated" and not has_report:
            continue
        if report_status == "pending" and has_report:
            continue
        if report_status == "paid_pending" and not (paid and not has_report):
            continue

        enriched_leads.append(lead)
    return enriched_leads


@router.get("/pipeline-stats")
async def get_pipeline_stats(current_user: dict = Depends(get_current_user)):
    """Get lead pipeline statistics for current user role"""
    stages = [
        "new", "contacted", "connected", "interested", "qualified",
        "assessment", "proposal", "negotiation", "payment_pending",
        "payment_received", "converted", "not_interested", "lost"
    ]
    stats = {}
    user_query = {}
    if not _is_admin(current_user):
        user_id = str(current_user.get("id") or "").strip()
        user_email = str(current_user.get("email") or "").strip().lower()
        user_name = str(current_user.get("name") or "").strip()
        user_first = user_name.split()[0] if user_name else ""
        assigned_or = []
        if user_id:
            assigned_or.append({"assigned_to": user_id})
            assigned_or.append({"assigned_sales_rep_id": user_id})
            assigned_or.append({"assigned_sales_person_id": user_id})
            assigned_or.append({"sales_person_id": user_id})
            assigned_or.append({"created_by": user_id})
            assigned_or.append({"partner_id": user_id})
            assigned_or.append({"block_assigned_to": user_id})
        if user_email:
            assigned_or.append({"assigned_to": user_email})
            assigned_or.append({"assigned_to_email": user_email})
            assigned_or.append({"assigned_to": {"$regex": f"^{re.escape(user_email)}$", "$options": "i"}})
            assigned_or.append({"assigned_to_email": {"$regex": f"^{re.escape(user_email)}$", "$options": "i"}})
        if user_name:
            assigned_or.append({"assigned_to": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
            assigned_or.append({"assigned_to_name": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
            assigned_or.append({"assigned_sales_person_name": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
            assigned_or.append({"created_by_name": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
        if user_first and len(user_first) >= 3:
            assigned_or.append({"assigned_to": {"$regex": f"^{re.escape(user_first)}$", "$options": "i"}})
            assigned_or.append({"assigned_to_name": {"$regex": f"^{re.escape(user_first)}$", "$options": "i"}})
            assigned_or.append({"assigned_sales_person_name": {"$regex": f"^{re.escape(user_first)}$", "$options": "i"}})
        user_query = {"$or": assigned_or if assigned_or else [{"assigned_to": "__none__"}]}
    
    for stage in stages:
        stage_clause = {"$or": [{"stage": stage}, {"status": stage}]}
        q = {"$and": [user_query, stage_clause]} if user_query else stage_clause
        stats[stage] = await leads_col.count_documents(q)
    
    total = await leads_col.count_documents(user_query if user_query else {})
    converted_count = stats.get("converted", 0) + stats.get("payment_received", 0)
    conversion_rate = round((converted_count / total * 100) if total > 0 else 0.0, 1)

    # Calculate revenue from deals or payments
    rev_pipeline = [
        {"$match": {"$and": [user_query, {"payment_status": "paid"}]} if user_query else {"payment_status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$paid_amount"}}}
    ]
    rev_res = await crm_payments_col.aggregate(rev_pipeline).to_list(1)
    revenue = rev_res[0]["total"] if rev_res else (converted_count * 50000.0)

    score_q = lambda cat: {"$and": [user_query, {"score_category": cat}]} if user_query else {"score_category": cat}

    return {
        "stages": stats,
        "total": total,
        "conversion_rate": conversion_rate,
        "revenue": revenue,
        "sources": await _get_source_stats(current_user),
        "score_breakdown": {
            "HOT": await leads_col.count_documents(score_q("HOT")),
            "WARM": await leads_col.count_documents(score_q("WARM")),
            "COLD": await leads_col.count_documents(score_q("COLD"))
        }
    }


async def _get_source_stats(user):
    query = {}
    if not _is_admin(user):
        user_id = str(user.get("id") or "").strip()
        user_email = str(user.get("email") or "").strip().lower()
        user_name = str(user.get("name") or "").strip()
        user_first = user_name.split()[0] if user_name else ""
        assigned_or = []
        if user_id:
            assigned_or.append({"assigned_to": user_id})
            assigned_or.append({"assigned_sales_rep_id": user_id})
            assigned_or.append({"assigned_sales_person_id": user_id})
            assigned_or.append({"sales_person_id": user_id})
            assigned_or.append({"created_by": user_id})
            assigned_or.append({"partner_id": user_id})
            assigned_or.append({"block_assigned_to": user_id})
        if user_email:
            assigned_or.append({"assigned_to": user_email})
            assigned_or.append({"assigned_to_email": user_email})
            assigned_or.append({"assigned_to": {"$regex": f"^{re.escape(user_email)}$", "$options": "i"}})
            assigned_or.append({"assigned_to_email": {"$regex": f"^{re.escape(user_email)}$", "$options": "i"}})
        if user_name:
            assigned_or.append({"assigned_to": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
            assigned_or.append({"assigned_to_name": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
            assigned_or.append({"assigned_sales_person_name": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
            assigned_or.append({"created_by_name": {"$regex": f"^{re.escape(user_name)}$", "$options": "i"}})
        if user_first and len(user_first) >= 3:
            assigned_or.append({"assigned_to": {"$regex": f"^{re.escape(user_first)}$", "$options": "i"}})
            assigned_or.append({"assigned_to_name": {"$regex": f"^{re.escape(user_first)}$", "$options": "i"}})
            assigned_or.append({"assigned_sales_person_name": {"$regex": f"^{re.escape(user_first)}$", "$options": "i"}})
        query = {"$or": assigned_or if assigned_or else [{"assigned_to": "__none__"}]}
    pipeline = []
    if query:
        pipeline.append({"$match": query})
    pipeline.extend([
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    results = await leads_col.aggregate(pipeline).to_list(20)
    return {r["_id"]: r["count"] for r in results if r["_id"]}


# ────────────────────────────────────────────────────────────
# LEAD ASSIGNMENT (MANUAL, BULK, ROUND-ROBIN, RULES)
# ────────────────────────────────────────────────────────────

@router.post("/bulk-assign")
async def bulk_assign_leads(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Bulk assign leads to a salesperson"""
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    lead_ids = data.get("lead_ids", [])
    sales_person_id = data.get("sales_person_id")
    if not lead_ids or not sales_person_id:
        raise HTTPException(status_code=400, detail="lead_ids and sales_person_id are required")

    sales_person = await users_col.find_one({"id": sales_person_id}, {"_id": 0, "name": 1})
    sp_name = sales_person.get("name", "Sales Executive") if sales_person else "Sales Executive"

    now = datetime.now(timezone.utc)
    await leads_col.update_many(
        {"id": {"$in": lead_ids}},
        {"$set": {
            "assigned_to": sales_person_id,
            "assigned_to_name": sp_name,
            "assigned_at": now,
            "assigned_by": current_user.get("id"),
            "assigned_by_name": current_user.get("name", "Admin"),
            "updated_at": now
        }}
    )

    for lid in lead_ids:
        await log_activity(
            user_id=current_user["id"],
            user_name=current_user.get("name", "Admin"),
            action="lead_reassigned",
            entity_type="lead",
            entity_id=lid,
            details=f"Lead assigned to {sp_name} by {current_user.get('name')}"
        )

    await create_notification(
        user_id=sales_person_id,
        title="New Leads Assigned (Bulk)",
        message=f"{len(lead_ids)} new leads have been assigned to you by {current_user.get('name')}",
        notification_type="lead_assigned"
    )

    return {"message": f"{len(lead_ids)} leads successfully assigned to {sp_name}"}


@router.post("/round-robin-assign")
async def round_robin_assign(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Automatically distribute unassigned leads equally across active sales executives"""
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Manager or Admin access required")

    active_sales_reps = await users_col.find(
        {"role": {"$in": ["sales_executive", "sr_sales_executive", "partner"]}, "status": "active"},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(50)

    if not active_sales_reps:
        raise HTTPException(status_code=400, detail="No active sales executives found for round-robin assignment")

    # Find unassigned leads
    unassigned_leads = await leads_col.find(
        {"$or": [{"assigned_to": None}, {"assigned_to": ""}]},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(100)

    if not unassigned_leads:
        return {"message": "No unassigned leads found", "assigned_count": 0}

    assigned_count = 0
    now = datetime.now(timezone.utc)
    rep_count = len(active_sales_reps)

    for idx, lead in enumerate(unassigned_leads):
        rep = active_sales_reps[idx % rep_count]
        await leads_col.update_one(
            {"id": lead["id"]},
            {"$set": {
                "assigned_to": rep["id"],
                "assigned_to_name": rep["name"],
                "assigned_at": now,
                "assigned_by": current_user.get("id"),
                "assigned_by_name": current_user.get("name", "Admin"),
                "updated_at": now
            }}
        )
        await log_activity(
            user_id=current_user["id"],
            user_name=current_user.get("name", "Admin"),
            action="round_robin_assignment",
            entity_type="lead",
            entity_id=lead["id"],
            details=f"Lead auto-assigned to {rep['name']} via Round Robin"
        )
        assigned_count += 1

    return {"message": f"Successfully distributed {assigned_count} leads across {rep_count} sales executives", "assigned_count": assigned_count}


# ────────────────────────────────────────────────────────────
# DUPLICATE DETECTION & MERGE
# ────────────────────────────────────────────────────────────

@router.post("/check-duplicates")
async def check_duplicate_leads(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Check if phone, email, or WhatsApp number matches existing leads or clients"""
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    whatsapp = data.get("whatsapp_number", "").strip()
    exclude_id = data.get("exclude_id")

    checks = []
    if phone:
        checks.extend([{"phone": phone}, {"alternate_phone": phone}])
    if email:
        checks.append({"email": email})
    if whatsapp:
        checks.append({"whatsapp_number": whatsapp})

    if not checks:
        return {"is_duplicate": False, "duplicates": []}

    query: Dict[str, Any] = {"$or": checks}
    if exclude_id:
        query["id"] = {"$ne": exclude_id}

    matched_leads = await leads_col.find(query, {"_id": 0}).to_list(10)
    for m in matched_leads:
        for f in ["created_at", "updated_at", "last_contacted_at"]:
            if isinstance(m.get(f), datetime):
                m[f] = m[f].isoformat()

    return {
        "is_duplicate": len(matched_leads) > 0,
        "count": len(matched_leads),
        "duplicates": matched_leads
    }


@router.post("/merge")
async def merge_duplicate_leads(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Merge duplicate lead records into primary lead without losing activity or communication history"""
    primary_id = data.get("primary_id")
    duplicate_ids = data.get("duplicate_ids", [])

    if not primary_id or not duplicate_ids:
        raise HTTPException(status_code=400, detail="primary_id and duplicate_ids are required")

    primary_lead = await leads_col.find_one({"id": primary_id}, {"_id": 0})
    if not primary_lead:
        raise HTTPException(status_code=404, detail="Primary lead not found")

    # Migrate calls, emails, whatsapp, follow-ups, tasks, notes to primary_id
    for dup_id in duplicate_ids:
        dup_lead = await leads_col.find_one({"id": dup_id}, {"_id": 0})
        if dup_lead:
            # Append notes
            if dup_lead.get("notes"):
                await leads_col.update_one({"id": primary_id}, {"$push": {"notes": {"$each": dup_lead["notes"]}}})
            # Re-point communications
            await crm_calls_col.update_many({"lead_id": dup_id}, {"$set": {"lead_id": primary_id}})
            await crm_whatsapp_col.update_many({"lead_id": dup_id}, {"$set": {"lead_id": primary_id}})
            await crm_emails_col.update_many({"lead_id": dup_id}, {"$set": {"lead_id": primary_id}})
            await follow_ups_col.update_many({"lead_id": dup_id}, {"$set": {"lead_id": primary_id}})
            await crm_tasks_col.update_many({"lead_id": dup_id}, {"$set": {"lead_id": primary_id}})
            await crm_meetings_col.update_many({"lead_id": dup_id}, {"$set": {"lead_id": primary_id}})
            await crm_deals_col.update_many({"lead_id": dup_id}, {"$set": {"lead_id": primary_id}})
            await crm_payments_col.update_many({"lead_id": dup_id}, {"$set": {"lead_id": primary_id}})
            
            # Archive/remove duplicate
            await leads_col.delete_one({"id": dup_id})

    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Admin"),
        action="lead_merged",
        entity_type="lead",
        entity_id=primary_id,
        details=f"Merged duplicate leads {duplicate_ids} into primary {primary_lead.get('name')}"
    )

    return {"message": "Leads successfully merged into primary record"}


# ────────────────────────────────────────────────────────────
# BULK IMPORT CSV / EXCEL (ADMIN ONLY WITH ROW RANGE & SALES PERSON ASSIGNMENT)
# ────────────────────────────────────────────────────────────

def _normalize_key(k: Any) -> str:
    """Normalize dictionary keys to lowercase alphanumeric with underscores."""
    if k is None:
        return ""
    return re.sub(r'[^a-zA-Z0-9]+', '_', str(k).strip().lower()).strip('_')


def _format_cell_value(val: Any) -> str:
    """Safely converts openpyxl cell values (ints, floats, dates, booleans) to clean strings."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    if isinstance(val, int):
        return str(val)
    val_str = str(val).strip()
    if val_str.endswith(".0"):
        digits_part = val_str[:-2]
        if digits_part.replace("+", "").replace("-", "").isdigit():
            val_str = digits_part
    return val_str


def _clean_phone_number(raw_phone: Any) -> str:
    """Strips formatting artifacts like trailing .0 from Excel float values while preserving phone digits."""
    if raw_phone is None:
        return ""
    s = str(raw_phone).strip()
    if s.endswith(".0"):
        prefix = s[:-2]
        digits_only = re.sub(r'\D', '', prefix)
        if digits_only and len(digits_only) >= 5:
            s = prefix
    return s


NAME_ALIASES = {
    "name", "full_name", "fullname", "client_name", "clientname",
    "lead_name", "leadname", "candidate_name", "candidatename",
    "candidate", "applicant_name", "applicantname", "applicant",
    "student_name", "studentname", "customer_name", "customername",
    "person_name", "first_name", "contact_name"
}

PHONE_ALIASES = {
    "phone", "phone_number", "phonenumber", "phone_no", "phoneno",
    "mobile", "mobile_number", "mobilenumber", "mobile_no", "mobileno",
    "full_mobile", "fullmobile", "full_mobile_number", "fullmobilenumber",
    "contact", "contact_number", "contactnumber", "contact_no", "contactno",
    "cell", "cell_phone", "cellphone", "cell_number", "cellnumber", "cell_no", "cellno",
    "whatsapp", "whatsapp_number", "whatsappnumber", "whatsapp_no", "whatsappno",
    "telephone", "tel", "tel_no", "primary_phone", "primary_mobile"
}

EMAIL_ALIASES = {
    "email", "email_id", "emailid", "email_address", "emailaddress",
    "mail", "mail_id", "mailid", "e_mail", "e_mail_id", "e_mail_address"
}

ALT_PHONE_ALIASES = {
    "alternate_phone", "alt_phone", "secondary_phone", "alternate_mobile",
    "alt_mobile", "secondary_mobile", "other_phone", "other_mobile"
}

DOB_ALIASES = {
    "dob", "date_of_birth", "dateofbirth", "birth_date", "birthdate", "d_o_b"
}

GENDER_ALIASES = {
    "gender", "sex"
}

MARITAL_STATUS_ALIASES = {
    "marital_status", "maritalstatus", "marital_stat", "marital", "marriage_status"
}

COUNTRY_ALIASES = {
    "country", "country_of_interest", "interested_country", "target_country",
    "destination", "preferred_country", "country_name", "destination_country"
}

SERVICE_ALIASES = {
    "service", "service_interested", "service_type", "visa_category",
    "visa_type", "category", "program", "interested_program", "service_name"
}

PROGRAM_ALIASES = {
    "interested_program", "program", "visa_type", "subclass", "program_name"
}

OCCUPATION_ALIASES = {
    "occupation", "job_title", "jobtitle", "job", "designation",
    "profession", "current_role", "currentrole", "current_profession", "role"
}

EXPERIENCE_ALIASES = {
    "experience", "work_experience", "workexperience", "total_work_experience",
    "totalworkexperience", "work_exp", "total_exp", "exp", "years_of_experience",
    "yearsofexperience", "experience_years"
}

QUALIFICATION_ALIASES = {
    "qualification", "latest_qualification", "highest_qualification",
    "education", "degree", "academic_qualification", "educational_qualification"
}

CITY_ALIASES = {
    "city", "location", "town", "current_city", "state", "region"
}

ADDRESS_ALIASES = {
    "address", "full_address", "residence", "residential_address"
}

BUDGET_ALIASES = {
    "budget", "budget_range", "investment", "budget_amount"
}

SOURCE_ALIASES = {
    "source", "lead_source", "channel", "lead_origin"
}

CAMPAIGN_ALIASES = {
    "campaign", "campaign_name", "utm_campaign", "campaign_title"
}

NOTES_ALIASES = {
    "notes", "remarks", "message", "comments", "description"
}

ASSIGNED_TO_ALIASES = {
    "assigned_to", "sales_rep", "sales_person", "salesperson", "agent",
    "assignee", "sales_person_email", "assigned_salesperson"
}


def _get_field_value(record: Dict[str, Any], aliases: Set[str]) -> str:
    """Finds field value from record comparing normalized and stripped keys against aliases."""
    for k, v in record.items():
        if v is None:
            continue
        v_str = str(v).strip()
        if not v_str:
            continue
        norm_k = _normalize_key(k)
        if norm_k in aliases or norm_k.replace("_", "") in aliases:
            return v_str
    return ""


def _normalize_lead_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts standard lead fields from any raw dictionary (Excel, CSV, JSON payload)."""
    name = _get_field_value(r, NAME_ALIASES)
    phone = _clean_phone_number(_get_field_value(r, PHONE_ALIASES))
    email = _get_field_value(r, EMAIL_ALIASES)
    alt_phone = _clean_phone_number(_get_field_value(r, ALT_PHONE_ALIASES))
    dob = _get_field_value(r, DOB_ALIASES)
    gender = _get_field_value(r, GENDER_ALIASES)
    marital_status = _get_field_value(r, MARITAL_STATUS_ALIASES)
    country = _get_field_value(r, COUNTRY_ALIASES)
    service = _get_field_value(r, SERVICE_ALIASES)
    program = _get_field_value(r, PROGRAM_ALIASES)
    occupation = _get_field_value(r, OCCUPATION_ALIASES)
    experience = _get_field_value(r, EXPERIENCE_ALIASES)
    qualification = _get_field_value(r, QUALIFICATION_ALIASES)
    city = _get_field_value(r, CITY_ALIASES)
    address = _get_field_value(r, ADDRESS_ALIASES)
    budget = _get_field_value(r, BUDGET_ALIASES)
    source = _get_field_value(r, SOURCE_ALIASES) or "Excel Import"
    campaign = _get_field_value(r, CAMPAIGN_ALIASES) or "Excel Bulk Upload"
    notes = _get_field_value(r, NOTES_ALIASES)
    assigned_to = _get_field_value(r, ASSIGNED_TO_ALIASES)

    # Substring fallbacks if name is still empty
    if not name:
        for k, v in r.items():
            if 'name' in _normalize_key(k) and v is not None and str(v).strip():
                name = str(v).strip()
                break

    # Substring fallbacks if phone is still empty
    if not phone:
        for k, v in r.items():
            nk = _normalize_key(k)
            if any(term in nk for term in ('phone', 'mobile', 'contact', 'cell', 'whatsapp')) and v is not None and str(v).strip():
                phone = _clean_phone_number(v)
                break

    result = {
        "name": name,
        "phone": phone,
        "email": email,
        "alternate_phone": alt_phone,
        "whatsapp_number": phone,
        "dob": dob,
        "gender": gender,
        "marital_status": marital_status,
        "country_of_interest": country,
        "country": country,
        "service_interested": service,
        "service": service,
        "service_type": service,
        "interested_program": program,
        "visa_type": program,
        "occupation": occupation,
        "total_work_experience": experience,
        "experience": experience,
        "latest_qualification": qualification,
        "qualification": qualification,
        "city": city,
        "address": address,
        "budget": budget,
        "source": source,
        "campaign": campaign,
        "notes": notes,
        "assigned_to": assigned_to,
    }
    # Retain all original attributes
    for k, v in r.items():
        if k not in result and v is not None:
            result[k] = v

    return result


def _parse_file_content_to_records(file_bytes: bytes, filename: str):
    """Parses Excel (.xlsx/.xls) or CSV (.csv) file bytes and returns (headers, normalized_records, raw_rows_count)."""
    fn = filename.lower()
    raw_records = []
    headers = []

    if fn.endswith(".xlsx") or fn.endswith(".xls"):
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))

            # Filter out completely empty rows
            clean_rows = []
            for r in rows:
                if any(c is not None and str(c).strip() != "" for c in r):
                    clean_rows.append(r)

            if not clean_rows or len(clean_rows) < 2:
                raise HTTPException(status_code=400, detail="Excel file is empty or has no data rows")

            header_row = clean_rows[0]
            raw_headers = [_normalize_key(h) if h is not None else "" for h in header_row]
            headers = [str(h).strip() if h is not None and str(h).strip() else f"Column {idx+1}" for idx, h in enumerate(header_row)]

            for row in clean_rows[1:]:
                row_dict = {}
                for idx, header in enumerate(raw_headers):
                    if header and idx < len(row):
                        row_dict[header] = _format_cell_value(row[idx])
                if any(v for v in row_dict.values()):
                    raw_records.append(row_dict)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse Excel file: {str(e)}")
    elif fn.endswith(".csv"):
        try:
            content_str = file_bytes.decode("utf-8-sig", errors="ignore")
            sample = content_str[:2048]
            delimiter = ","
            if sample:
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                    delimiter = dialect.delimiter
                except Exception:
                    delimiter = ","

            reader = csv.DictReader(io.StringIO(content_str), delimiter=delimiter)
            if reader.fieldnames:
                headers = [str(h).strip() for h in reader.fieldnames if h]
            for r in reader:
                cleaned = {_normalize_key(k): (str(v).strip() if v is not None else "") for k, v in r.items() if k}
                if any(cleaned.values()):
                    raw_records.append(cleaned)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload an Excel (.xlsx/.xls) or CSV (.csv) file.")

    # Normalize each record
    normalized_records = [_normalize_lead_dict(r) for r in raw_records]
    return headers, normalized_records, len(normalized_records)


async def _process_and_save_leads(
    records: List[Dict[str, Any]],
    current_user: dict,
    assignment_method: str = "specific",
    sales_person_id: Optional[str] = None,
    row_ranges: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    active_sales_reps = await users_col.find(
        {"role": {"$in": ["partner", "sales_executive", "sr_sales_executive", "sales_manager", "admin", "admin_owner", "sales_specialist", "sales_rep"]}, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "email": 1}
    ).to_list(100)

    rep_by_id = {r["id"]: r for r in active_sales_reps}
    rep_by_name = {r["name"].strip().lower(): r for r in active_sales_reps}
    rep_by_email = {r.get("email", "").strip().lower(): r for r in active_sales_reps if r.get("email")}

    selected_rep = rep_by_id.get(sales_person_id) if sales_person_id else None
    if not selected_rep and sales_person_id:
        u = await users_col.find_one({"id": sales_person_id}, {"_id": 0, "id": 1, "name": 1, "email": 1})
        if u:
            selected_rep = u
            rep_by_id[u["id"]] = u

    total_records = len(records)
    valid_records = []
    duplicate_records = []
    invalid_records = []
    assigned_counts_by_rep = {}

    seen_phones_in_batch = set()
    seen_emails_in_batch = set()

    now = datetime.now(timezone.utc)
    rep_count = len(active_sales_reps)
    assigned_idx = 0

    for idx, r in enumerate(records, start=1):
        r_norm = _normalize_lead_dict(r)
        name = str(r_norm.get("name", "")).strip()
        phone = str(r_norm.get("phone", "")).strip()
        email = str(r_norm.get("email", "")).strip()

        if not name or not phone:
            invalid_records.append({**r_norm, "error": f"Row #{idx}: Missing mandatory name or phone"})
            continue

        # In-batch duplicate check
        if phone in seen_phones_in_batch or (email and email in seen_emails_in_batch):
            duplicate_records.append({**r_norm, "error": f"Row #{idx}: Duplicate lead within the uploaded file (phone/email already seen)"})
            continue

        # Database duplicate detection across phone and email
        existing = await leads_col.find_one(
            {"$or": [{"phone": phone}, {"email": email}] if email else [{"phone": phone}]},
            {"_id": 0, "id": 1, "name": 1, "lead_number": 1}
        )
        if existing:
            duplicate_records.append({**r_norm, "error": f"Row #{idx}: Duplicate found matching {existing.get('name')} ({existing.get('lead_number', '')})"})
            continue

        # Assignment resolution
        assigned_to = None
        assigned_name = "Unassigned"

        if assignment_method == "row_ranges" and row_ranges:
            matched_range = None
            for rng in row_ranges:
                try:
                    f_row = int(rng.get("from_row", 0))
                    t_row = int(rng.get("to_row", 0))
                    if f_row <= idx <= t_row:
                        matched_range = rng
                        break
                except (ValueError, TypeError):
                    continue

            if matched_range:
                target_rep_id = matched_range.get("sales_person_id")
                if target_rep_id in rep_by_id:
                    assigned_to = rep_by_id[target_rep_id]["id"]
                    assigned_name = rep_by_id[target_rep_id]["name"]
                elif target_rep_id:
                    # Fallback query if rep wasn't in active list
                    u = await users_col.find_one(
                        {"$or": [{"id": target_rep_id}, {"email": str(target_rep_id).lower()}]},
                        {"_id": 0, "id": 1, "name": 1, "email": 1}
                    )
                    if u:
                        rep_by_id[u["id"]] = u
                        assigned_to = u["id"]
                        assigned_name = u["name"]
                    else:
                        assigned_to = target_rep_id
                        assigned_name = matched_range.get("sales_person_name") or "Sales Representative"
                else:
                    assigned_to = None
                    assigned_name = "Unassigned"
            elif selected_rep:
                assigned_to = selected_rep["id"]
                assigned_name = selected_rep["name"]
            else:
                assigned_to = None
                assigned_name = "Unassigned"

        elif assignment_method == "specific" and selected_rep:
            assigned_to = selected_rep["id"]
            assigned_name = selected_rep["name"]
        elif assignment_method == "round_robin" and rep_count > 0:
            chosen = active_sales_reps[assigned_idx % rep_count]
            assigned_to = chosen["id"]
            assigned_name = chosen["name"]
            assigned_idx += 1
        elif assignment_method == "from_file":
            raw_target = str(r_norm.get("assigned_to") or r_norm.get("sales_rep") or r_norm.get("sales_person_email") or "").strip().lower()
            if raw_target in rep_by_id:
                assigned_to = rep_by_id[raw_target]["id"]
                assigned_name = rep_by_id[raw_target]["name"]
            elif raw_target in rep_by_email:
                assigned_to = rep_by_email[raw_target]["id"]
                assigned_name = rep_by_email[raw_target]["name"]
            elif raw_target in rep_by_name:
                assigned_to = rep_by_name[raw_target]["id"]
                assigned_name = rep_by_name[raw_target]["name"]
            elif selected_rep:
                assigned_to = selected_rep["id"]
                assigned_name = selected_rep["name"]
            elif rep_count > 0:
                chosen = active_sales_reps[assigned_idx % rep_count]
                assigned_to = chosen["id"]
                assigned_name = chosen["name"]
                assigned_idx += 1
        elif assignment_method == "unassigned":
            assigned_to = None
            assigned_name = "Unassigned"
        elif selected_rep:
            assigned_to = selected_rep["id"]
            assigned_name = selected_rep["name"]

        lead_num = await _next_lead_number()
        score, category = calculate_lead_score(r_norm)

        new_lead = {
            "id": str(uuid.uuid4()),
            "lead_number": lead_num,
            "name": name,
            "email": email,
            "phone": phone,
            "alternate_phone": str(r_norm.get("alternate_phone", "")).strip(),
            "whatsapp_number": str(r_norm.get("whatsapp_number") or phone).strip(),
            "country": str(r_norm.get("country") or r_norm.get("country_of_interest") or "").strip(),
            "city": str(r_norm.get("city", "")).strip(),
            "address": str(r_norm.get("address", "")).strip(),
            "service_interested": r_norm.get("service_interested") or r_norm.get("service", ""),
            "service_type": r_norm.get("service_interested") or r_norm.get("service", ""),
            "country_of_interest": r_norm.get("country_of_interest") or r_norm.get("interested_country", ""),
            "interested_country": r_norm.get("country_of_interest") or r_norm.get("interested_country", ""),
            "interested_program": str(r_norm.get("interested_program") or r_norm.get("program", "")).strip(),
            "visa_type": str(r_norm.get("visa_type", "")).strip(),
            "occupation": str(r_norm.get("occupation", "")).strip(),
            "total_work_experience": str(r_norm.get("total_work_experience") or r_norm.get("experience", "")).strip(),
            "latest_qualification": str(r_norm.get("latest_qualification") or r_norm.get("qualification", "")).strip(),
            "dob": str(r_norm.get("dob", "")).strip(),
            "gender": str(r_norm.get("gender", "")).strip(),
            "marital_status": str(r_norm.get("marital_status", "")).strip(),
            "source": r_norm.get("source", "Excel Bulk Import"),
            "campaign": r_norm.get("campaign", "Bulk Import Campaign"),
            "budget": str(r_norm.get("budget", "")),
            "stage": r_norm.get("stage", "new"),
            "status": r_norm.get("status", "new"),
            "priority": r_norm.get("priority", "medium"),
            "lead_score": score,
            "score_category": category,
            "assigned_to": assigned_to,
            "assigned_to_name": assigned_name,
            "assigned_at": now if assigned_to else None,
            "assigned_by": (current_user.get("id") if current_user else None) if assigned_to else None,
            "assigned_by_name": (current_user.get("name", "Admin") if current_user else None) if assigned_to else None,
            "tags": ["bulk_imported", "excel_import"],
            "notes": [f"Imported via Excel/Bulk tool by {current_user.get('name', 'Admin')} on {now.strftime('%Y-%m-%d %H:%M')} (Row #{idx})"] if not r_norm.get("notes") else [str(r_norm.get("notes"))],
            "call_count": 0,
            "created_at": now,
            "updated_at": now,
            "converted": False
        }
        await leads_col.insert_one(new_lead)
        valid_records.append(new_lead["id"])
        seen_phones_in_batch.add(phone)
        if email:
            seen_emails_in_batch.add(email)

        if assigned_to:
            assigned_counts_by_rep[assigned_to] = assigned_counts_by_rep.get(assigned_to, 0) + 1

    # Send notifications to assigned sales persons
    for rep_id, count in assigned_counts_by_rep.items():
        rep_target = rep_by_id.get(rep_id)
        rep_target_name = rep_target["name"] if rep_target else "Sales Representative"
        await create_notification(
            user_id=rep_id,
            title="New Leads Assigned (Bulk Import)",
            message=f"{count} new leads have been assigned to you by Admin {current_user.get('name', 'Admin')}",
            notification_type="lead_assigned"
        )

    # Build human-readable distribution summary
    distribution_summary = {}
    for rep_id, count in assigned_counts_by_rep.items():
        name = rep_by_id[rep_id]["name"] if rep_id in rep_by_id else rep_id
        distribution_summary[name] = count

    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Admin"),
        action="bulk_lead_import",
        entity_type="lead",
        details=f"Bulk imported {len(valid_records)} leads ({len(duplicate_records)} duplicates, {len(invalid_records)} invalid). Assigned across {len(assigned_counts_by_rep)} sales reps."
    )

    return {
        "total_records": total_records,
        "imported_count": len(valid_records),
        "duplicate_count": len(duplicate_records),
        "invalid_count": len(invalid_records),
        "assigned_distribution": assigned_counts_by_rep,
        "assigned_summary": distribution_summary,
        "failed_records": duplicate_records + invalid_records,
        "errors": [r.get("error", "Unknown error") for r in (duplicate_records + invalid_records)[:20]]
    }


@router.post("/bulk-import-preview")
async def bulk_import_leads_preview(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Preview uploaded Excel/CSV file to inspect headers, row count, and sample records.
    Strictly restricted to Admin users only.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Bulk lead preview is restricted to Admin users only.")

    filename = file.filename.lower()
    file_bytes = await file.read()
    headers, records, total_rows = _parse_file_content_to_records(file_bytes, filename)

    return {
        "filename": file.filename,
        "total_rows": total_rows,
        "headers": headers,
        "sample_records": records[:5]
    }


@router.post("/bulk-import")
async def bulk_import_leads(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """
    Import bulk leads with duplicate detection and Sales Person assignment.
    Strictly restricted to Admin users only.
    Payload: { records: [...], assignment_method: "specific"|"round_robin"|"from_file"|"unassigned"|"row_ranges", sales_person_id: Optional[str], row_ranges: Optional[List[dict]] }
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Bulk lead import is restricted to Admin users only.")

    records = data.get("records", [])
    assignment_method = data.get("assignment_method", "specific")
    sales_person_id = data.get("sales_person_id") or data.get("auto_assign_sales_person_id")
    row_ranges = data.get("row_ranges")

    return await _process_and_save_leads(
        records=records,
        current_user=current_user,
        assignment_method=assignment_method,
        sales_person_id=sales_person_id,
        row_ranges=row_ranges
    )


@router.post("/bulk-import-file")
async def bulk_import_leads_file(
    file: UploadFile = File(...),
    assignment_method: str = Form("specific"),
    sales_person_id: Optional[str] = Form(None),
    row_ranges: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload Excel (.xlsx, .xls) or CSV (.csv) file to import and assign leads with Row Range & Auto Split support.
    Strictly restricted to Admin users.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Bulk lead import is restricted to Admin users only.")

    filename = file.filename.lower()
    file_bytes = await file.read()
    headers, normalized_records, total_rows = _parse_file_content_to_records(file_bytes, filename)

    parsed_row_ranges = None
    if row_ranges:
        try:
            parsed_row_ranges = json.loads(row_ranges)
        except Exception:
            parsed_row_ranges = None

    return await _process_and_save_leads(
        records=normalized_records,
        current_user=current_user,
        assignment_method=assignment_method,
        sales_person_id=sales_person_id,
        row_ranges=parsed_row_ranges
    )


# ────────────────────────────────────────────────────────────
# LEAD DETAILS, UPDATES, NOTES & FOLLOW-UPS
# ────────────────────────────────────────────────────────────

@router.get("/{lead_id}")
async def get_lead_detail(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Get single lead details with permission check"""
    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not _is_admin(current_user):
        user_id = str(current_user.get("id") or "").strip()
        user_email = str(current_user.get("email") or "").strip().lower()
        user_name = str(current_user.get("name") or "").strip().lower()
        user_first = user_name.split()[0] if user_name else ""
        lead_assignee = str(lead.get("assigned_to") or "").strip()
        lead_assignee_name = str(lead.get("assigned_to_name") or lead.get("assigned_sales_person_name") or "").strip().lower()
        lead_assignee_email = str(lead.get("assigned_to_email") or "").strip().lower()

        is_assigned_to_me = (
            (user_id and (lead_assignee == user_id or str(lead.get("assigned_sales_rep_id") or "") == user_id or str(lead.get("assigned_sales_person_id") or "") == user_id or str(lead.get("sales_person_id") or "") == user_id or str(lead.get("created_by") or "") == user_id or str(lead.get("partner_id") or "") == user_id or str(lead.get("block_assigned_to") or "") == user_id)) or
            (user_email and (lead_assignee.lower() == user_email or lead_assignee_email == user_email)) or
            (user_name and (lead_assignee.lower() == user_name or lead_assignee_name == user_name)) or
            (user_first and len(user_first) >= 3 and (lead_assignee.lower() == user_first or lead_assignee_name == user_first))
        )
        if not is_assigned_to_me:
            raise HTTPException(status_code=403, detail="Access denied. You can only view leads assigned to you.")

    for f in ["created_at", "updated_at", "last_contacted_at"]:
        if isinstance(lead.get(f), datetime):
            lead[f] = lead[f].isoformat()

    from core.navratri_automation import is_lead_paid, has_lead_resume
    paid = is_lead_paid(lead)
    resume = has_lead_resume(lead)
    lead["is_paid"] = paid
    lead["has_resume"] = resume
    if paid and not lead.get("payment_status"):
        lead["payment_status"] = "paid"
    elif not paid and not lead.get("payment_status"):
        lead["payment_status"] = "unpaid"
    if not lead.get("payment_amount"):
        lead["payment_amount"] = lead.get("amount") or 2427.0
    if "amount_paid" not in lead or lead.get("amount_paid") is None:
        lead["amount_paid"] = lead["payment_amount"] if paid else 0.0
    has_report = bool(
        lead.get("report_generated") is True
        or lead.get("report_status") in ("generated", "completed")
        or lead.get("latest_report_snapshot_id")
        or lead.get("assessment_report_id")
    )
    lead["report_generated"] = has_report
    lead["report_status"] = "generated" if has_report else (lead.get("report_status") or "pending")
    if has_report and not lead.get("assessment_report_id"):
        lead["assessment_report_id"] = lead.get("latest_report_snapshot_id")

    return lead


@router.put("/{lead_id}")
async def update_lead(lead_id: str, data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Update lead details, stage, status or score"""
    from bson import ObjectId
    lead_query = {"$or": [{"id": lead_id}, {"lead_number": lead_id}, {"unique_id": lead_id}]}
    if ObjectId.is_valid(lead_id):
        lead_query["$or"].append({"_id": ObjectId(lead_id)})
    lead = await leads_col.find_one(lead_query)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    real_lead_id = lead.get("id") or str(lead["_id"])

    if not _is_admin(current_user):
        user_id = str(current_user.get("id") or "").strip()
        user_email = str(current_user.get("email") or "").strip().lower()
        user_name = str(current_user.get("name") or "").strip().lower()
        user_first = user_name.split()[0] if user_name else ""
        lead_assignee = str(lead.get("assigned_to") or "").strip()
        lead_assignee_name = str(lead.get("assigned_to_name") or lead.get("assigned_sales_person_name") or "").strip().lower()
        lead_assignee_email = str(lead.get("assigned_to_email") or "").strip().lower()

        is_assigned_to_me = (
            (user_id and (lead_assignee == user_id or str(lead.get("assigned_sales_rep_id") or "") == user_id or str(lead.get("assigned_sales_person_id") or "") == user_id or str(lead.get("sales_person_id") or "") == user_id or str(lead.get("created_by") or "") == user_id or str(lead.get("partner_id") or "") == user_id or str(lead.get("block_assigned_to") or "") == user_id)) or
            (user_email and (lead_assignee.lower() == user_email or lead_assignee_email == user_email)) or
            (user_name and (lead_assignee.lower() == user_name or lead_assignee_name == user_name)) or
            (user_first and len(user_first) >= 3 and (lead_assignee.lower() == user_first or lead_assignee_name == user_first)) or
            not lead_assignee or lead_assignee in ["unassigned", "none", ""]
        )
        if not is_assigned_to_me:
            raise HTTPException(status_code=403, detail="Access denied. You can only update leads assigned to you.")

    data.pop("id", None)
    data.pop("_id", None)
    data["updated_at"] = datetime.now(timezone.utc)

    # Recalculate score if profile fields updated
    merged = {**lead, **data}
    score, category = calculate_lead_score(merged)
    data["lead_score"] = score
    data["score_category"] = category

    # Handle assigned_to resolution & notification
    if "assigned_to" in data:
        raw_assign = data.get("assigned_to")
        if raw_assign in ["unassigned", "none", "", None]:
            data["assigned_to"] = None
            data["assigned_to_name"] = None
            data["assigned_to_email"] = None
            data["assigned_at"] = None
            data["assigned_by"] = None
            data["assigned_by_name"] = None
            data["assigned_sales_rep_id"] = None
            data["assigned_sales_person_id"] = None
            data["sales_person_id"] = None
            data["assigned_sales_person_name"] = None
            data["sales_person_name"] = None
        else:
            data["assigned_to"] = str(raw_assign).strip()
            u = await users_col.find_one({"id": data["assigned_to"]}, {"_id": 0, "name": 1, "email": 1})
            if u:
                data["assigned_to_name"] = u.get("name", "")
                if u.get("email"):
                    data["assigned_to_email"] = str(u.get("email")).strip().lower()
            data["assigned_sales_rep_id"] = data["assigned_to"]
            data["assigned_sales_person_id"] = data["assigned_to"]
            data["sales_person_id"] = data["assigned_to"]
            data["assigned_sales_person_name"] = data.get("assigned_to_name")
            data["sales_person_name"] = data.get("assigned_to_name")

            if data["assigned_to"] != lead.get("assigned_to"):
                now_assign = datetime.now(timezone.utc)
                data["assigned_at"] = now_assign
                data["assigned_by"] = current_user.get("id")
                data["assigned_by_name"] = current_user.get("name", "Admin")
                await log_activity(
                    user_id=current_user["id"],
                    user_name=current_user.get("name", "User"),
                    action="lead_reassigned",
                    entity_type="lead",
                    entity_id=lead_id,
                    details=f"Lead assigned to {data.get('assigned_to_name', 'Sales Representative')} by {current_user.get('name')}"
                )
                await create_notification(
                    user_id=data["assigned_to"],
                    title="Lead Assigned",
                    message=f"You have been assigned lead: {lead.get('name')} ({lead.get('phone')}) by {current_user.get('name', 'Admin')}",
                    notification_type="lead_assigned",
                    related_id=lead_id
                )

    # When lead is marked as converted, ensure converted client record is created/assigned
    if data.get("stage") == "converted" or data.get("status") == "converted":
        data["converted"] = True
        data["converted_at"] = datetime.now(timezone.utc)
        sp_id = data.get("assigned_to") or lead.get("assigned_to") or current_user.get("id")
        sp_name = data.get("assigned_to_name") or lead.get("assigned_to_name") or current_user.get("name", "")

        c_email = data.get("email") or lead.get("email")
        if not c_email:
            c_email = f"client_{lead.get('phone', uuid.uuid4().hex[:6])}@leamss.com"

        client_user = await users_col.find_one({"email": c_email})
        if not client_user:
            client_id = str(uuid.uuid4())
            new_client_doc = {
                "id": client_id,
                "name": data.get("name") or lead.get("name", "Client"),
                "email": c_email,
                "phone": data.get("phone") or lead.get("phone", ""),
                "password": get_password_hash("Client@123"),
                "role": "client",
                "rbac_role": "client",
                "user_type": "client",
                "country": lead.get("country_of_interest") or lead.get("country", "India"),
                "service": lead.get("service_interested", "Immigration Consulting"),
                "assigned_sales_person_id": sp_id,
                "assigned_sales_person_name": sp_name,
                "original_lead_id": lead_id,
                "original_lead_number": lead.get("lead_number"),
                "client_portal_status": "activated",
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            await users_col.insert_one(new_client_doc)
        else:
            client_id = client_user.get("id") or str(client_user["_id"])
            await users_col.update_one(
                {"id": client_id},
                {"$set": {
                    "role": "client",
                    "assigned_sales_person_id": sp_id,
                    "assigned_sales_person_name": sp_name,
                    "original_lead_id": lead_id,
                    "client_portal_status": "activated",
                    "updated_at": datetime.now(timezone.utc),
                }}
            )
        data["converted_client_id"] = client_id

        # Auto create/link deal if not already present
        existing_deal = await crm_deals_col.find_one({"lead_id": lead_id})
        if not existing_deal:
            deal_id = str(uuid.uuid4())
            pkg_price = float(lead.get("package_price") or 75000)
            disc = float(lead.get("discount") or 0)
            paid = float(lead.get("paid_amount") or 0)
            await crm_deals_col.insert_one({
                "id": deal_id,
                "deal_name": f"{lead.get('name')} - {lead.get('service_interested', 'Consulting')}",
                "lead_id": lead_id,
                "client_id": client_id,
                "client_name": lead.get("name"),
                "service": lead.get("service_interested", "Immigration"),
                "country": lead.get("country_of_interest", "Canada"),
                "deal_value": pkg_price,
                "discount": disc,
                "final_amount": pkg_price - disc,
                "paid_amount": paid,
                "pending_amount": max(0.0, (pkg_price - disc) - paid),
                "stage": "won",
                "sales_person_id": sp_id,
                "sales_person_name": sp_name,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
            data["converted_deal_id"] = deal_id

        # Recalculate targets
        try:
            from core.targets_logic import recalc_targets_for_user
            if sp_id:
                await recalc_targets_for_user(sp_id, notify=True)
        except Exception:
            pass

    await leads_col.update_one({"_id": lead["_id"]}, {"$set": data})

    # If assigned_to is updated, synchronize across all duplicate lead docs, CRM meetings, pre-assessments, and deals
    if "assigned_to" in data:
        assign_sync = {
            "assigned_to": data["assigned_to"],
            "assigned_to_name": data.get("assigned_to_name"),
            "assigned_at": data.get("assigned_at"),
            "assigned_by": data.get("assigned_by"),
            "assigned_by_name": data.get("assigned_by_name"),
            "updated_at": data.get("updated_at")
        }
        leads_sync_q = [{"id": real_lead_id}, {"_id": lead["_id"]}]
        if lead.get("lead_number"):
            leads_sync_q.append({"lead_number": lead["lead_number"]})
        lead_email_val = (lead.get("email") or data.get("email") or "").strip().lower()
        if lead_email_val and "@" in lead_email_val:
            leads_sync_q.append({"email": {"$regex": f"^{re.escape(lead_email_val)}$", "$options": "i"}})
        lead_phone_val = lead.get("phone") or data.get("phone")
        if lead_phone_val and len(str(lead_phone_val)) >= 7:
            leads_sync_q.append({"phone": str(lead_phone_val)})
        await leads_col.update_many({"$or": leads_sync_q}, {"$set": assign_sync})

        # Sync to crm_meetings_col
        mtg_q = [{"lead_id": real_lead_id}]
        if lead_email_val and "@" in lead_email_val:
            mtg_q.append({"contact_email": {"$regex": f"^{re.escape(lead_email_val)}$", "$options": "i"}})
        if lead_phone_val:
            mtg_q.append({"contact_phone": str(lead_phone_val)})
        await crm_meetings_col.update_many(
            {"$or": mtg_q},
            {"$set": {
                "sales_person_id": data["assigned_to"],
                "sales_person_name": data.get("assigned_to_name")
            }}
        )

        # Sync to pre_assessments & deals
        pa_q = [{"lead_id": real_lead_id}]
        if lead.get("pa_id"):
            pa_q.append({"id": lead["pa_id"]})
        await db["pre_assessments"].update_many(
            {"$or": pa_q},
            {"$set": {
                "assigned_to": data["assigned_to"],
                "assigned_to_name": data.get("assigned_to_name"),
                "assigned_sales_person_id": data["assigned_to"],
                "assigned_sales_person_name": data.get("assigned_to_name")
            }}
        )
        await crm_deals_col.update_many(
            {"lead_id": real_lead_id},
            {"$set": {
                "sales_person_id": data["assigned_to"],
                "sales_person_name": data.get("assigned_to_name")
            }}
        )

    old_stage = lead.get("stage") or lead.get("status")
    new_stage = data.get("stage") or data.get("status")
    stage_changed = (
        ("stage" in data and data["stage"] != lead.get("stage")) or
        ("status" in data and data["status"] != lead.get("status"))
    )
    if stage_changed and new_stage:
        await log_activity(
            user_id=current_user["id"],
            user_name=current_user.get("name", "User"),
            action=f"moved_to_{new_stage}",
            entity_type="lead",
            entity_id=real_lead_id,
            details=f"Lead {lead.get('name')} stage changed to {new_stage}",
            old_value=old_stage,
            new_value=new_stage
        )

        try:
            from services.salesperson_activity_service import log_salesperson_activity
            client_name_val = lead.get("name") or "Lead"
            sp_name_val = current_user.get("name", "Sales Person")
            formatted_old = str(old_stage or "None").replace("_", " ").title()
            formatted_new = str(new_stage).replace("_", " ").title()
            await log_salesperson_activity(
                db=db,
                salesperson_id=current_user["id"],
                salesperson_name=sp_name_val,
                salesperson_email=current_user.get("email"),
                salesperson_role=current_user.get("rbac_role") or current_user.get("role"),
                activity_type="stage_change",
                client_id=real_lead_id,
                client_name=client_name_val,
                client_phone=lead.get("phone"),
                client_email=lead.get("email"),
                title=f"Stage Changed: {formatted_old} → {formatted_new} - {client_name_val}",
                details=f"Lead stage updated from '{formatted_old}' to '{formatted_new}' by {sp_name_val}",
                metadata={
                    "previous_stage": old_stage,
                    "new_stage": new_stage,
                    "old_stage": old_stage,
                    "lead_id": real_lead_id,
                    "lead_number": lead.get("lead_number")
                }
            )
        except Exception as e:
            logger.warning(f"Error logging stage change to salesperson activity: {e}")

    return {"message": "Lead updated successfully", "lead_score": score, "score_category": category}


@router.post("/{lead_id}/note")
async def add_lead_note(lead_id: str, data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Add a categorized note/remark to a lead without overwriting prior entries"""
    lead = await leads_col.find_one({"$or": [{"id": lead_id}, {"unique_id": lead_id}, {"lead_number": lead_id}]})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    real_lead_id = lead.get("id") or str(lead.get("_id"))

    now_utc = datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        ist_tz = ZoneInfo("Asia/Kolkata")
    except Exception:
        ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = now_utc.astimezone(ist_tz)

    user_role_raw = str(current_user.get("rbac_role") or current_user.get("role") or "Salesperson").lower()
    is_admin = user_role_raw in ["admin", "admin_owner", "super_admin"]
    role_display = "Admin" if is_admin else (" ".join(w.capitalize() for w in user_role_raw.replace("_", " ").split()) or "Salesperson")

    note_type = (data.get("note_type") or data.get("type") or "Other Remarks").strip()
    valid_types = ["Dropped a Message", "Dropped a Mail", "Called the Client", "Other Remarks"]
    matched_type = next((vt for vt in valid_types if vt.lower() == note_type.lower()), note_type)

    note_text = (data.get("text") or data.get("description") or "").strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="Note description is required")

    note = {
        "id": str(uuid.uuid4()),
        "note_type": matched_type,
        "text": note_text,
        "description": note_text,
        "added_by": current_user["id"],
        "added_by_name": current_user.get("name", "User"),
        "added_by_role": role_display,
        "is_admin": is_admin,
        "date_display": now_ist.strftime("%b %d, %Y"),
        "time_display": now_ist.strftime("%I:%M %p"),
        "created_at": now_utc.isoformat()
    }

    # Push to notes array across duplicates
    push_query: Dict[str, Any] = {"$or": [{"id": real_lead_id}, {"_id": lead["_id"]}]}
    if lead.get("lead_number"):
        push_query["$or"].append({"lead_number": lead["lead_number"]})
    await leads_col.update_many(push_query, {"$push": {"notes": note}})

    # Retrieve updated notes list
    updated_lead = await leads_col.find_one({"id": real_lead_id}, {"_id": 0, "notes": 1})
    all_notes = (updated_lead.get("notes") or []) if updated_lead else [note]
    all_notes_sorted = sorted(all_notes, key=lambda n: str(n.get("created_at") or ""), reverse=True)

    action_slug = f"note_{matched_type.lower().replace(' ', '_')}"
    client_name_val = lead.get("name") or "Lead"
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "User"),
        action=action_slug,
        entity_type="lead",
        entity_id=real_lead_id,
        details=f"[{matched_type}] {note_text[:80]}",
        client_name=client_name_val
    )

    # Record to Salesperson Activity Audit Log
    try:
        from services.salesperson_activity_service import log_salesperson_activity
        sp_name_val = current_user.get("name", "User")
        await log_salesperson_activity(
            db=db,
            salesperson_id=current_user["id"],
            salesperson_name=sp_name_val,
            salesperson_email=current_user.get("email"),
            salesperson_role=role_display,
            activity_type="note",
            client_id=real_lead_id,
            client_name=client_name_val,
            client_phone=lead.get("phone"),
            client_email=lead.get("email"),
            title=f"Note ({matched_type}) - {client_name_val}",
            details=f"[{matched_type}] {note_text}",
            metadata={
                "note_id": note["id"],
                "note_type": matched_type,
                "author_role": role_display,
                "is_admin": is_admin
            }
        )
    except Exception as e:
        logger.warning(f"Error logging note to audit: {e}")

    return {
        "message": f"Note ({matched_type}) added successfully",
        "note": note,
        "notes": all_notes_sorted
    }


@router.get("/{lead_id}/notes")
async def get_lead_notes(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieve all notes and remarks for a lead sorted newest first"""
    lead = await leads_col.find_one({"$or": [{"id": lead_id}, {"unique_id": lead_id}, {"lead_number": lead_id}]}, {"_id": 0, "notes": 1})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    notes = lead.get("notes") or []
    notes_sorted = sorted(notes, key=lambda n: str(n.get("created_at") or ""), reverse=True)
    return {"notes": notes_sorted}


@router.post("/{lead_id}/resume")
async def upload_lead_resume(
    lead_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload and attach resume to CRM Lead:
    - Stores file securely in GridFS (max 15MB)
    - Automatically enriches candidate profile and cascades across:
      Sales Assessment, Pre-Assessment, Converted Client, and Cases
    - Adds timeline entry and audit log
    """
    from bson import ObjectId
    lead_query = {"$or": [{"id": lead_id}, {"lead_number": lead_id}, {"unique_id": lead_id}]}
    if ObjectId.is_valid(lead_id):
        lead_query["$or"].append({"_id": ObjectId(lead_id)})
    lead = await leads_col.find_one(lead_query)

    # Fallback 1: check if lead_id is a pre-assessment ID
    if not lead:
        pa = await db["pre_assessments"].find_one({"$or": [{"id": lead_id}, {"pa_number": lead_id}]})
        if pa and pa.get("lead_id"):
            lead = await leads_col.find_one({"$or": [{"id": pa["lead_id"]}] + ([{"_id": ObjectId(pa["lead_id"])}] if ObjectId.is_valid(pa["lead_id"]) else [])})
        if not lead and not pa:
            # Fallback 2: check if lead_id is a user (client)
            client_u = await db["users"].find_one({"id": lead_id})
            if client_u and client_u.get("original_lead_id"):
                orig_id = client_u["original_lead_id"]
                lead = await leads_col.find_one({"$or": [{"id": orig_id}] + ([{"_id": ObjectId(orig_id)}] if ObjectId.is_valid(orig_id) else [])})
            elif not client_u:
                raise HTTPException(status_code=404, detail="Lead not found")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")

    from core.resume_service import save_resume_to_gridfs, attach_and_sync_resume
    try:
        file_id_str, download_url = await save_resume_to_gridfs(
            filename=file.filename or "resume.pdf",
            file_bytes=content,
            content_type=file.content_type,
            metadata={
                "lead_id": lead_id,
                "uploaded_by_id": current_user.get("id"),
                "uploaded_by_name": current_user.get("name"),
                "source": "crm_salesperson_upload",
            }
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

    sync_result = await attach_and_sync_resume(
        lead_id=lead_id,
        file_id_str=file_id_str,
        filename=file.filename or "resume.pdf",
        file_bytes=content,
        uploaded_by=current_user,
    )

    return {
        "ok": True,
        "message": "Resume uploaded and synchronized successfully",
        "lead_id": lead_id,
        "resume_file_id": file_id_str,
        "resume_filename": file.filename,
        "resume_url": download_url,
    }


@router.post("/{lead_id}/pre-assessment-report")
@router.post("/{lead_id}/assessment-report")
async def upload_lead_pre_assessment_report(
    lead_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload and attach a Pre-Assessment Report to a CRM Lead:
    - Stores file securely in GridFS (max 15MB)
    - Updates lead record with assessment_report_file_id, assessment_report_filename, etc.
    - Synchronizes with any active Pre-Assessment or Case Document record
    - Appends activity entry to lead timeline and writes audit log
    """
    from bson import ObjectId
    lead_query = {"$or": [{"id": lead_id}, {"lead_number": lead_id}, {"unique_id": lead_id}]}
    if ObjectId.is_valid(lead_id):
        lead_query["$or"].append({"_id": ObjectId(lead_id)})
    lead = await leads_col.find_one(lead_query)

    if not lead:
        pa = await db["pre_assessments"].find_one({"$or": [{"id": lead_id}, {"pa_number": lead_id}]})
        if pa and pa.get("lead_id"):
            lead = await leads_col.find_one({"$or": [{"id": pa["lead_id"]}] + ([{"_id": ObjectId(pa["lead_id"])}] if ObjectId.is_valid(pa["lead_id"]) else [])})
        if not lead and not pa:
            client_u = await db["users"].find_one({"id": lead_id})
            if client_u and client_u.get("original_lead_id"):
                orig_id = client_u["original_lead_id"]
                lead = await leads_col.find_one({"$or": [{"id": orig_id}] + ([{"_id": ObjectId(orig_id)}] if ObjectId.is_valid(orig_id) else [])})
            elif not client_u:
                raise HTTPException(status_code=404, detail="Lead not found")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")

    from core.resume_service import save_resume_to_gridfs
    actual_lead_id = (lead.get("id") or lead.get("unique_id") or str(lead.get("_id"))) if lead else lead_id

    try:
        file_id_str, download_url = await save_resume_to_gridfs(
            filename=file.filename or "Pre_Assessment_Report.pdf",
            file_bytes=content,
            content_type=file.content_type,
            metadata={
                "lead_id": actual_lead_id,
                "uploaded_by_id": current_user.get("id"),
                "uploaded_by_name": current_user.get("name"),
                "document_type": "pre_assessment_report",
                "source": "crm_pre_assessment_report_upload",
            }
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

    now_iso = datetime.now(timezone.utc).isoformat()
    update_fields = {
        "assessment_report_file_id": file_id_str,
        "assessment_report_filename": file.filename or "Pre_Assessment_Report.pdf",
        "assessment_report_id": file_id_str,
        "latest_report_snapshot_id": file_id_str,
        "pre_assessment_report_url": download_url,
        "assessment_report_url": download_url,
        "has_pre_assessment_report": True,
        "report_generated": True,
        "report_status": "attached",
        "pre_assessment_report_uploaded_at": now_iso,
        "pre_assessment_report_uploaded_by": {
            "id": current_user.get("id"),
            "name": current_user.get("name"),
        },
    }

    activity_entry = {
        "id": str(uuid.uuid4()),
        "lead_id": actual_lead_id,
        "activity_type": "pre_assessment_report_uploaded",
        "type": "document_upload",
        "title": "Pre-Assessment Report Attached",
        "description": f"Pre-Assessment Report '{file.filename}' uploaded and attached to client record by {current_user.get('name', 'Staff')}.",
        "user_id": current_user.get("id"),
        "user_name": current_user.get("name", "Staff"),
        "timestamp": now_iso,
        "created_at": now_iso,
    }

    await leads_col.update_one(
        {"$or": [{"id": actual_lead_id}, {"unique_id": actual_lead_id}, {"lead_number": actual_lead_id}]},
        {
            "$set": update_fields,
            "$push": {"timeline": activity_entry}
        }
    )

    # Synchronize with linked pre_assessments if any
    lead_email = (lead.get("email") or "").strip().lower() if lead else ""
    pa_query = [{"lead_id": actual_lead_id}]
    if lead_email and "@" in lead_email:
        pa_query.append({"client_email": lead_email})

    await db["pre_assessments"].update_many(
        {"$or": pa_query},
        {"$set": {
            "assessment_report_file_id": file_id_str,
            "assessment_report_filename": file.filename or "Pre_Assessment_Report.pdf",
            "report_url": download_url,
            "has_report": True,
            "updated_at": now_iso,
        }}
    )

    # Insert into pre_assessment_documents
    await db["pre_assessment_documents"].insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": actual_lead_id,
        "document_type": "pre_assessment_report",
        "file_name": file.filename or "Pre_Assessment_Report.pdf",
        "file_id": file_id_str,
        "file_path": download_url,
        "file_size": len(content),
        "status": "approved",
        "uploaded_by": current_user.get("id"),
        "uploaded_by_name": current_user.get("name"),
        "created_at": now_iso,
        "is_pre_assessment_report": True,
    })

    # Central audit log
    from services.audit_service import log_legacy_event
    await log_legacy_event(
        db=db,
        user_id=current_user.get("id", "system"),
        action="lead.upload_pre_assessment_report",
        entity_type="lead",
        entity_id=actual_lead_id,
        details={"filename": file.filename, "file_id": file_id_str, "file_size": len(content)},
    )

    return {
        "ok": True,
        "message": "Pre-Assessment Report uploaded and attached successfully",
        "lead_id": actual_lead_id,
        "assessment_report_file_id": file_id_str,
        "assessment_report_filename": file.filename,
        "report_url": download_url,
        "uploaded_at": now_iso,
    }


@router.get("/{lead_id}/pre-assessment-report")
async def get_lead_pre_assessment_report(
    lead_id: str,
    token: Optional[str] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Fetch/stream the attached Pre-Assessment Report for a lead. Supports Bearer auth and query token."""
    from bson import ObjectId
    import jwt
    from core.auth import JWT_SECRET
    from routers.cockpit import get_cockpit_resume, _proxy_external_resume

    auth_user = current_user
    if not auth_user and token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            u_id = payload.get("sub")
            if u_id:
                auth_user = await users_col.find_one({"id": u_id}, {"_id": 0})
        except Exception:
            pass

    lead_query = {"$or": [{"id": lead_id}, {"lead_number": lead_id}, {"unique_id": lead_id}]}
    if ObjectId.is_valid(lead_id):
        lead_query["$or"].append({"_id": ObjectId(lead_id)})
    lead = await leads_col.find_one(lead_query)
    if not lead:
        # Check by pre_assessments or users
        pa = await db["pre_assessments"].find_one({"$or": [{"id": lead_id}, {"pa_number": lead_id}, {"lead_id": lead_id}]})
        if pa and pa.get("lead_id"):
            lead = await leads_col.find_one({"$or": [{"id": pa["lead_id"]}, {"unique_id": pa["lead_id"]}]})

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # 1. Try report IDs / snapshot IDs
    candidate_ids = [
        lead.get("assessment_report_file_id"),
        lead.get("pdf_file_id"),
        lead.get("assessment_report_id"),
        lead.get("latest_report_snapshot_id"),
    ]
    for fid in candidate_ids:
        if fid and str(fid).strip():
            try:
                return await get_cockpit_resume(str(fid).strip())
            except Exception:
                pass

    # 2. Try report URLs
    rep_url = lead.get("pre_assessment_report_url") or lead.get("assessment_report_url")
    if rep_url:
        fname = lead.get("assessment_report_filename") or f"{lead.get('name', 'client')}_pre_assessment_report.pdf"
        return await _proxy_external_resume(str(rep_url), fname)

    # 3. Check pre_assessment_documents
    actual_lead_id = lead.get("id") or lead.get("unique_id") or lead_id
    pa_doc = await db["pre_assessment_documents"].find_one({
        "$or": [{"lead_id": actual_lead_id}, {"lead_id": lead_id}],
        "is_pre_assessment_report": True
    })
    if pa_doc:
        pfid = pa_doc.get("file_id")
        if pfid:
            try:
                return await get_cockpit_resume(str(pfid).strip())
            except Exception:
                pass
        purl = pa_doc.get("file_path")
        if purl:
            return await _proxy_external_resume(str(purl), pa_doc.get("file_name"))

    # 4. Fallback to get_cockpit_resume with actual_lead_id
    try:
        return await get_cockpit_resume(actual_lead_id)
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="No Pre-Assessment Report attached to this lead")


# ────────────────────────────────────────────────────────────
# CLIENT CONVERSION & CASE MANAGER HANDOVER
# ────────────────────────────────────────────────────────────

@router.post("/{lead_id}/convert-to-client")
async def convert_lead_to_client(lead_id: str, data: dict = Body(default={}), current_user: dict = Depends(get_current_user)):
    """
    Convert Lead to Client:
    - Creates Client record in users_col (preserving role='client')
    - Preserves Lead ID and all historical timelines/calls/messages
    - Persists uploaded Resume metadata and GridFS reference
    - Creates/Links active Deal in crm_deals_col
    - Retains assigned Sales Person
    """
    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    email = data.get("email") or lead.get("email")
    if not email:
        email = f"client_{lead.get('phone', uuid.uuid4().hex[:6])}@leamss.com"

    # Check if user account exists or create new
    client_user = await users_col.find_one({"email": email}, {"_id": 0, "id": 1})
    client_id = client_user["id"] if client_user else str(uuid.uuid4())

    now = datetime.now(timezone.utc)
    package_price = float(data.get("package_price", 75000))
    discount = float(data.get("discount", 0))
    paid_amount = float(data.get("paid_amount", 0))

    resume_fid = lead.get("resume_file_id")
    resume_fname = lead.get("resume_filename")
    resume_u = lead.get("resume_url") or lead.get("resume_path") or (f"/cockpit/resume/{resume_fid}" if resume_fid else None)

    if not client_user:
        new_client_doc = {
            "id": client_id,
            "name": data.get("name") or lead.get("name", "Client"),
            "email": email,
            "phone": data.get("phone") or lead.get("phone", ""),
            "password": get_password_hash("Client@123"),
            "role": "client",
            "rbac_role": "client",
            "country": lead.get("country", "India"),
            "service": lead.get("service_interested", "Immigration Consulting"),
            "assigned_sales_person_id": lead.get("assigned_to") or current_user["id"],
            "assigned_sales_person_name": lead.get("assigned_to_name") or current_user.get("name", ""),
            "original_lead_id": lead_id,
            "original_lead_number": lead.get("lead_number"),
            "resume_file_id": resume_fid,
            "resume_filename": resume_fname,
            "resume_url": resume_u,
            "resume_path": resume_u,
            "resume_uploaded": bool(resume_fid or resume_u),
            "resume_uploaded_at": lead.get("resume_uploaded_at") or (now.isoformat() if (resume_fid or resume_u) else None),
            "client_portal_status": "activated",
            "created_at": now
        }
        await users_col.insert_one(new_client_doc)
    else:
        client_update = {
            "assigned_sales_person_id": lead.get("assigned_to") or current_user["id"],
            "assigned_sales_person_name": lead.get("assigned_to_name") or current_user.get("name", ""),
            "original_lead_id": lead_id,
            "role": "client",
            "client_portal_status": "activated",
            "updated_at": now
        }
        if resume_fid or resume_u:
            client_update["resume_file_id"] = resume_fid
            client_update["resume_filename"] = resume_fname
            client_update["resume_url"] = resume_u
            client_update["resume_path"] = resume_u
            client_update["resume_uploaded"] = True
            client_update["resume_uploaded_at"] = lead.get("resume_uploaded_at") or now.isoformat()
        await users_col.update_one(
            {"id": client_id},
            {"$set": client_update}
        )

    # Create / Update Deal
    deal_id = str(uuid.uuid4())
    deal_doc = {
        "id": deal_id,
        "deal_name": f"{lead.get('name')} - {lead.get('service_interested', 'Consulting')}",
        "lead_id": lead_id,
        "client_id": client_id,
        "client_name": lead.get("name"),
        "service": lead.get("service_interested", "Immigration"),
        "country": lead.get("country_of_interest", "Canada"),
        "deal_value": package_price,
        "discount": discount,
        "final_amount": package_price - discount,
        "paid_amount": paid_amount,
        "pending_amount": max(0.0, (package_price - discount) - paid_amount),
        "stage": "won" if paid_amount >= (package_price - discount) else "payment_pending",
        "sales_person_id": lead.get("assigned_to") or current_user["id"],
        "sales_person_name": lead.get("assigned_to_name") or current_user.get("name", ""),
        "created_at": now,
        "updated_at": now
    }
    await crm_deals_col.insert_one(deal_doc)

    # Mark Lead as converted
    await leads_col.update_one(
        {"id": lead_id},
        {"$set": {
            "stage": "converted",
            "status": "converted",
            "converted": True,
            "converted_client_id": client_id,
            "converted_deal_id": deal_id,
            "updated_at": now
        }}
    )

    # Activity log
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action="client_converted",
        entity_type="lead",
        entity_id=lead_id,
        details=f"Lead {lead.get('name')} converted to Client (Client ID: {client_id}, Deal: {deal_id})"
    )

    return {
        "message": "Lead successfully converted to Client",
        "client_id": client_id,
        "deal_id": deal_id,
        "lead_id": lead_id
    }


@router.post("/{lead_id}/case-manager-handover")
async def handover_to_case_manager(lead_id: str, data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """
    Handover converted client to Case Manager Portal:
    - Assigns Case Manager
    - Creates Case file in cases_col
    - Links sales package & payment summary
    """
    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    case_manager_id = data.get("case_manager_id")
    case_manager = await users_col.find_one({"id": case_manager_id}, {"_id": 0, "name": 1, "email": 1}) if case_manager_id else None
    cm_name = case_manager.get("name", "Case Manager") if case_manager else "Case Manager"

    case_id = f"CASE-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc)

    client_id = lead.get("converted_client_id")
    if not client_id:
        # Auto convert first if not already converted
        conv_res = await convert_lead_to_client(lead_id, {}, current_user)
        client_id = conv_res["client_id"]

    resume_fid = lead.get("resume_file_id")
    resume_fname = lead.get("resume_filename") or f"Resume - {lead.get('name', 'Client')}"
    resume_u = lead.get("resume_url") or lead.get("resume_path") or (f"/cockpit/resume/{resume_fid}" if resume_fid else None)

    case_doc = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "lead_id": lead_id,
        "client_id": client_id,
        "client_name": lead.get("name"),
        "client_email": lead.get("email"),
        "client_phone": lead.get("phone"),
        "case_manager_id": case_manager_id,
        "case_manager_name": cm_name,
        "handover_by_id": current_user["id"],
        "handover_by_name": current_user.get("name", ""),
        "handover_date": now.strftime("%Y-%m-%d"),
        "handover_notes": data.get("notes", "Client sales consultation completed. Handed over for processing."),
        "service": lead.get("service_interested", "Immigration Consulting"),
        "country": lead.get("country_of_interest", "Canada"),
        "package_details": data.get("package_details", "Standard Visa Processing"),
        "payment_status": data.get("payment_status", "confirmed"),
        "status": "active",
        "stage": "document_collection",
        "resume_file_id": resume_fid,
        "resume_filename": resume_fname if (resume_fid or resume_u) else None,
        "resume_url": resume_u,
        "resume_path": resume_u,
        "resume_uploaded": bool(resume_fid or resume_u),
        "created_at": now,
        "updated_at": now
    }
    await cases_col.insert_one(case_doc)

    if resume_fid or resume_u:
        await db["documents"].insert_one({
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "client_id": client_id,
            "name": resume_fname,
            "category": "Professional",
            "doc_type": "resume",
            "file_url": resume_u,
            "file_id": resume_fid,
            "status": "approved",
            "uploaded_at": now.isoformat(),
            "created_at": now,
            "updated_at": now
        })

    # Update lead with handover details
    await leads_col.update_one(
        {"id": lead_id},
        {"$set": {
            "case_manager_handover": True,
            "case_manager_id": case_manager_id,
            "case_manager_name": cm_name,
            "case_id": case_id,
            "handover_date": now.isoformat(),
            "updated_at": now
        }}
    )

    # Notify Case Manager
    if case_manager_id:
        await create_notification(
            user_id=case_manager_id,
            title="New Case Handed Over",
            message=f"Case {case_id} for client {lead.get('name')} has been handed over to you by {current_user.get('name')}",
            notification_type="case_handover",
            related_id=case_id
        )

    # Activity log
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action="case_manager_handover",
        entity_type="case",
        entity_id=case_id,
        details=f"Case {case_id} ({lead.get('name')}) handed over to Case Manager {cm_name}"
    )

    return {
        "message": "Successfully handed over case to Case Manager portal",
        "case_id": case_id,
        "case_manager_name": cm_name
    }


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a lead (Admin only)"""
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin or Manager access required")
    await leads_col.delete_one({"id": lead_id})
    return {"message": "Lead deleted successfully"}

# ── Public Registration Aliases & Pre-Assessment Integration ──────────────────
@router.post("/register")
async def register_lead_alias(data: dict, current_user: Optional[dict] = Depends(get_current_user_optional)):
    return await capture_lead(data, current_user)

@router.post("/registration")
async def registration_lead_alias(data: dict, current_user: Optional[dict] = Depends(get_current_user_optional)):
    return await capture_lead(data, current_user)

@router.post("/navratri-registration")
async def navratri_lead_alias(data: dict, current_user: Optional[dict] = Depends(get_current_user_optional)):
    return await capture_lead(data, current_user)

@router.post("/website-lead")
async def website_lead_alias(data: dict, current_user: Optional[dict] = Depends(get_current_user_optional)):
    return await capture_lead(data, current_user)


@router.post("/{lead_id}/follow-up")
async def schedule_follow_up(lead_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Schedule a follow-up for a lead"""
    follow_up = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "type": data.get("type", "call"),
        "scheduled_at": data.get("scheduled_at"),
        "message": data.get("message", ""),
        "status": "pending",
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc),
        "completed_at": None
    }
    await follow_ups_col.insert_one(follow_up)
    await leads_col.update_one({"id": lead_id}, {"$set": {"last_contacted_at": datetime.now(timezone.utc)}})
    return {"message": "Follow-up scheduled", "id": follow_up["id"]}


@router.get("/follow-ups/pending")
async def get_pending_follow_ups(current_user: dict = Depends(get_current_user)):
    """Get pending follow-ups"""
    query = {"status": "pending"}
    if current_user.get("role") in ["partner", "sales_executive", "sr_sales_executive"]:
        query["created_by"] = current_user["id"]
    
    follow_ups = await follow_ups_col.find(query, {"_id": 0}).sort("scheduled_at", 1).to_list(50)
    for fu in follow_ups:
        for field in ["created_at", "scheduled_at", "completed_at"]:
            if isinstance(fu.get(field), datetime):
                fu[field] = fu[field].isoformat()
        lead = await leads_col.find_one({"id": fu["lead_id"]}, {"_id": 0, "name": 1, "email": 1, "phone": 1})
        fu["lead_name"] = lead.get("name", "Unknown") if lead else "Unknown"
        fu["lead_email"] = lead.get("email", "") if lead else ""
    return follow_ups


@router.put("/follow-ups/{follow_up_id}/complete")
async def complete_follow_up(follow_up_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Mark follow-up as completed"""
    await follow_ups_col.update_one({"id": follow_up_id}, {"$set": {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc),
        "outcome": data.get("outcome", "")
    }})
    return {"message": "Follow-up completed"}


@router.post("/{lead_id}/convert-to-pa")
async def convert_lead_to_pa(lead_id: str, payload: dict = None, current_user: dict = Depends(get_current_user)):
    """Converts a Lead into a full Pre-Assessment in one click."""
    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    p = payload or {}
    pa_id = str(uuid.uuid4())
    pa_number = f"PA-{datetime.now().strftime('%Y%m%d')}-{pa_id[:6].upper()}"
    country_code = (p.get("country") or lead.get("country_of_interest") or "AU").upper()[:2]
    service_type = p.get("service_type") or lead.get("service_interested") or "General Skilled Migration"

    partner_id = lead.get("partner_id") or lead.get("assigned_to") or current_user["id"]
    partner_name = lead.get("partner_name") or lead.get("assigned_to_name") or current_user.get("name", "Admin")

    pa_doc = {
        "id": pa_id,
        "pa_number": pa_number,
        "partner_id": partner_id,
        "partner_name": partner_name,
        "case_manager_id": lead.get("case_manager_id"),
        "case_manager_name": lead.get("case_manager_name", ""),
        "created_by_user_id": current_user["id"],
        "created_by_role": current_user.get("role", "partner"),
        "created_by_user_type": current_user.get("user_type", "internal"),
        "client_name": lead.get("name", "Unnamed Client"),
        "client_email": lead.get("email", ""),
        "client_mobile": lead.get("phone", ""),
        "country": country_code,
        "target_country": country_code,
        "service_type": service_type,
        "product_id": p.get("product_id", ""),
        "product_name": p.get("product_name", "General Skilled Migration"),
        "education": lead.get("latest_qualification", ""),
        "work_experience": lead.get("total_work_experience", ""),
        "dob": lead.get("date_of_birth", ""),
        "marital_status": lead.get("marital_status", ""),
        "notes": lead.get("message") or f"Converted from CRM Lead {lead.get('unique_id', '')}",
        "lead_id": lead_id,
        "lead_source": lead.get("source", "website"),
        "lead_source_detail": lead.get("subsource", ""),
        "stage": "new",
        "status": "active",
        "fee_payment_status": "paid" if lead.get("payment_status") == "success" else "pending",
        "sale_type": "standard",
        "pa_fees_amount": lead.get("payment_amount") or 5100,
        "resume_file_id": lead.get("resume_file_id"),
        "resume_filename": lead.get("resume_filename") or (f"Resume - {lead.get('name', 'Lead')}" if (lead.get("resume_url") or lead.get("resume_path")) else None),
        "resume_url": lead.get("resume_url") or lead.get("resume_path") or (f"/cockpit/resume/{lead.get('resume_file_id')}" if lead.get("resume_file_id") else None),
        "resume_path": lead.get("resume_path") or lead.get("resume_url"),
        "resume_uploaded": bool(lead.get("resume_uploaded") or lead.get("resume_file_id") or lead.get("resume_url")),
        "resume_uploaded_at": lead.get("resume_uploaded_at") or (datetime.now(timezone.utc).isoformat() if (lead.get("resume_file_id") or lead.get("resume_url")) else None),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    await db["pre_assessments"].insert_one(pa_doc)

    resume_url = pa_doc.get("resume_url")
    if resume_url:
        doc_id = str(uuid.uuid4())
        await db["pre_assessment_documents"].insert_one({
            "id": doc_id,
            "pre_assessment_id": pa_id,
            "name": pa_doc.get("resume_filename") or f"Resume - {lead.get('name', 'Lead')}",
            "doc_type": "resume",
            "file_url": resume_url,
            "file_path": lead.get("resume_path", ""),
            "file_id": lead.get("resume_file_id"),
            "status": "uploaded",
            "uploaded_at": datetime.now(timezone.utc),
        })

    await leads_col.update_one(
        {"id": lead_id},
        {"$set": {
            "converted": True,
            "converted_pa_id": pa_id,
            "converted_pa_number": pa_number,
            "stage": "converted",
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    await log_activity(
        current_user["id"], current_user.get("name", ""),
        "convert_lead_to_pa", "lead", lead_id,
        f"Converted Lead {lead.get('name')} to Pre-Assessment {pa_number}"
    )

    return {
        "status": "success",
        "message": "Pre-Assessment created successfully",
        "pa_id": pa_id,
        "pa_number": pa_number,
        "deep_link": f"/admin?tab=pre-assessments&pa_id={pa_id}"
    }


@router.post("/bulk-create-pa")
async def bulk_create_pa(payload: dict, current_user: dict = Depends(get_current_user)):
    """Creates Pre-Assessments for multiple selected leads in bulk."""
    lead_ids = payload.get("lead_ids", [])
    if not lead_ids:
        raise HTTPException(status_code=400, detail="No lead IDs provided")

    created_pas = []
    leads = await leads_col.find({"id": {"$in": lead_ids}}, {"_id": 0}).to_list(100)

    for lead in leads:
        lead_id = lead["id"]
        pa_id = str(uuid.uuid4())
        pa_number = f"PA-{datetime.now().strftime('%Y%m%d')}-{pa_id[:6].upper()}"
        country_code = (lead.get("country_of_interest") or "AU").upper()[:2]
        service_type = lead.get("service_interested") or "General Skilled Migration"

        partner_id = lead.get("partner_id") or lead.get("assigned_to") or current_user["id"]
        partner_name = lead.get("partner_name") or lead.get("assigned_to_name") or current_user.get("name", "Admin")

        pa_doc = {
            "id": pa_id,
            "pa_number": pa_number,
            "partner_id": partner_id,
            "partner_name": partner_name,
            "case_manager_id": lead.get("case_manager_id"),
            "case_manager_name": lead.get("case_manager_name", ""),
            "created_by_user_id": current_user["id"],
            "created_by_role": current_user.get("role", "partner"),
            "client_name": lead.get("name", "Client"),
            "client_email": lead.get("email", ""),
            "client_mobile": lead.get("phone", ""),
            "country": country_code,
            "target_country": country_code,
            "service_type": service_type,
            "product_id": "",
            "product_name": "General Skilled Migration",
            "education": lead.get("latest_qualification", ""),
            "work_experience": lead.get("total_work_experience", ""),
            "dob": lead.get("date_of_birth", ""),
            "marital_status": lead.get("marital_status", ""),
            "notes": f"Bulk converted from Lead {lead.get('unique_id', '')}",
            "lead_id": lead_id,
            "lead_source": lead.get("source", "website"),
            "stage": "new",
            "status": "active",
            "fee_payment_status": "paid" if lead.get("payment_status") == "success" else "pending",
            "sale_type": "standard",
            "pa_fees_amount": 5100,
            "resume_file_id": lead.get("resume_file_id"),
            "resume_filename": lead.get("resume_filename") or (f"Resume - {lead.get('name', 'Lead')}" if (lead.get("resume_url") or lead.get("resume_path")) else None),
            "resume_url": lead.get("resume_url") or lead.get("resume_path") or (f"/cockpit/resume/{lead.get('resume_file_id')}" if lead.get("resume_file_id") else None),
            "resume_path": lead.get("resume_path") or lead.get("resume_url"),
            "resume_uploaded": bool(lead.get("resume_uploaded") or lead.get("resume_file_id") or lead.get("resume_url")),
            "resume_uploaded_at": lead.get("resume_uploaded_at") or (datetime.now(timezone.utc).isoformat() if (lead.get("resume_file_id") or lead.get("resume_url")) else None),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await db["pre_assessments"].insert_one(pa_doc)

        resume_url = pa_doc.get("resume_url")
        if resume_url:
            await db["pre_assessment_documents"].insert_one({
                "id": str(uuid.uuid4()),
                "pre_assessment_id": pa_id,
                "name": pa_doc.get("resume_filename") or f"Resume - {lead.get('name', 'Lead')}",
                "doc_type": "resume",
                "file_url": resume_url,
                "file_id": lead.get("resume_file_id"),
                "status": "uploaded",
                "uploaded_at": datetime.now(timezone.utc),
            })

        await leads_col.update_one(
            {"id": lead_id},
            {"$set": {
                "converted": True,
                "converted_pa_id": pa_id,
                "converted_pa_number": pa_number,
                "stage": "converted",
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        created_pas.append({
            "lead_id": lead_id,
            "client_name": lead.get("name"),
            "pa_id": pa_id,
            "pa_number": pa_number,
        })

    return {
        "status": "success",
        "created_count": len(created_pas),
        "pa_list": created_pas,
    }


@router.put("/{lead_id}/assign")
@router.post("/{lead_id}/assign")
async def assign_single_lead(lead_id: str, payload: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Assign a single lead to a team member."""
    assigned_to = payload.get("assigned_to") or payload.get("user_id")
    assigned_to_name = payload.get("assigned_to_name")

    if not assigned_to:
        raise HTTPException(status_code=400, detail="assigned_to is required")

    user = await users_col.find_one({"id": assigned_to}, {"_id": 0, "name": 1, "role": 1})
    if user and not assigned_to_name:
        assigned_to_name = user.get("name", "Assigned Member")

    now = datetime.now(timezone.utc)
    update_doc = {
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_to_name or "Assigned Member",
        "assigned_at": now,
        "assigned_by": current_user.get("id"),
        "assigned_by_name": current_user.get("name", "Admin"),
        "updated_at": now
    }

    target_conditions = [{"id": lead_id}, {"lead_number": lead_id}]
    if ObjectId.is_valid(lead_id):
        target_conditions.append({"_id": ObjectId(lead_id)})
    target_query = {"$or": target_conditions}

    lead_doc = await leads_col.find_one(target_query)
    if not lead_doc:
        raise HTTPException(status_code=404, detail="Lead not found")

    await leads_col.update_one(target_query, {"$set": update_doc})

    # Log and notify
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Admin"),
        action="lead_assigned",
        entity_type="lead",
        entity_id=lead_doc.get("id") or lead_id,
        details=f"Lead assigned to {assigned_to_name} by {current_user.get('name', 'Admin')}"
    )

    await create_notification(
        user_id=assigned_to,
        title="New Lead Assigned",
        message=f"Admin {current_user.get('name', 'Admin')} assigned lead: {lead_doc.get('name', 'New Lead')} ({lead_doc.get('phone', '')}) to you.",
        notification_type="lead_assigned",
        related_id=lead_doc.get("id") or lead_id
    )

    # Sync to linked meetings and duplicate leads
    real_lead_id = lead_doc.get("id") or lead_id
    lead_email_val = (lead_doc.get("email") or "").strip().lower()
    lead_phone_val = lead_doc.get("phone")

    mtg_q = [{"lead_id": real_lead_id}]
    if lead_email_val and "@" in lead_email_val:
        mtg_q.append({"contact_email": {"$regex": f"^{re.escape(lead_email_val)}$", "$options": "i"}})
    if lead_phone_val:
        mtg_q.append({"contact_phone": str(lead_phone_val)})
    await crm_meetings_col.update_many(
        {"$or": mtg_q},
        {"$set": {
            "sales_person_id": assigned_to,
            "sales_person_name": assigned_to_name
        }}
    )

    # Sync to any duplicate leads by email or phone
    dup_leads_q = []
    if lead_email_val and "@" in lead_email_val:
        dup_leads_q.append({"email": {"$regex": f"^{re.escape(lead_email_val)}$", "$options": "i"}})
    if lead_phone_val and len(str(lead_phone_val)) >= 7:
        dup_leads_q.append({"phone": str(lead_phone_val)})
    if dup_leads_q:
        await leads_col.update_many({"$or": dup_leads_q}, {"$set": update_doc})

    # Sync to linked assessments
    pa_q = [{"lead_id": real_lead_id}]
    if lead_doc.get("pa_id"):
        pa_q.append({"id": lead_doc["pa_id"]})
    await db["pre_assessments"].update_many({"$or": pa_q}, {"$set": update_doc})

    # Sync to deals
    await crm_deals_col.update_many(
        {"lead_id": real_lead_id},
        {"$set": {
            "sales_person_id": assigned_to,
            "sales_person_name": assigned_to_name
        }}
    )

    return {
        "status": "success",
        "message": f"Lead assigned successfully to {assigned_to_name}",
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_to_name,
        "lead_id": lead_doc.get("id") or lead_id
    }
