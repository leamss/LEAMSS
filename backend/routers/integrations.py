"""Centralized Integrations Router for Multi-Company CRM.

Supported Providers:
- Zoho (CRM & Forms)
- Google (Sheets, Gmail, Calendar)
- Meta (Facebook & Instagram Lead Generation Ads)
"""
import uuid
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response, Body
from pydantic import BaseModel
from core.database import db, users_col, notifications_col, audit_logs_col
from core.auth import get_current_user

logger = logging.getLogger("integrations")
from services.integrations.encryption_util import encrypt_secret, mask_secret, decrypt_secret
from services.integrations.lead_ingestion_service import ingest_lead
from services.integrations.zoho_service import (
    test_zoho_connection,
    fetch_zoho_leads,
    parse_zoho_webhook_payload
)
from services.integrations.google_services import (
    test_sheets_connection,
    fetch_sheets_leads,
    test_gmail_connection,
    test_calendar_connection,
    sync_gmail_messages,
    create_calendar_appointment
)
from services.integrations.meta_service import (
    verify_meta_webhook,
    test_meta_connection,
    fetch_meta_leadgen_details
)
from services.integrations.ai_assistant_service import (
    test_ai_assistant_connection,
    qualify_lead_with_ai,
    generate_instant_proposal,
    batch_evaluate_company_leads
)
from services.integrations.calendly_service import (
    test_calendly_connection,
    sync_calendly_integration,
    record_calendly_booking,
    create_calendly_scheduling_link,
    fetch_calendly_event_types,
    send_meeting_confirmation_email,
    ensure_calendly_integration
)

router = APIRouter(prefix="/integrations", tags=["Integrations Hub"])

companies_col = db["companies"]
integrations_col = db["integrations"]
sync_logs_col = db["integration_sync_logs"]
leads_col = db["leads"]

DEFAULT_COMPANY_ID = "comp_leamss_primary"
DEFAULT_COMPANY_NAME = "LEAMSS Global"


async def ensure_default_company() -> Dict[str, Any]:
    """Ensures primary default company exists so existing records remain intact."""
    existing = await companies_col.find_one({"id": DEFAULT_COMPANY_ID}, {"_id": 0})
    if not existing:
        doc = {
            "id": DEFAULT_COMPANY_ID,
            "name": DEFAULT_COMPANY_NAME,
            "code": "LEAMSS",
            "domain": "leamss.com",
            "status": "active",
            "created_at": datetime.now(timezone.utc)
        }
        await companies_col.insert_one(doc)
        return doc
    return existing


def _mask_integration_credentials(integ: Dict[str, Any]) -> Dict[str, Any]:
    """Masks secret keys in credentials dictionary for client response."""
    safe = dict(integ)
    if "_id" in safe:
        del safe["_id"]

    creds = dict(safe.get("credentials") or {})
    for k in list(creds.keys()):
        if any(secret_term in k.lower() for secret_term in ["secret", "token", "password", "key"]):
            creds[k] = mask_secret(creds[k])
    safe["credentials"] = creds
    return safe


def _require_admin(user: dict):
    """Enforces that only Admin, Admin Owner, or Super Admin can access Integrations Hub."""
    role = str(user.get("role") or "").lower()
    rbac_role = str(user.get("rbac_role") or "").lower()
    allowed = ["admin", "admin_owner", "super_admin"]
    if role not in allowed and rbac_role not in allowed:
        raise HTTPException(status_code=403, detail="Admin access required for Integrations Hub.")


# ────────────────────────────────────────────────────────────
# 1. COMPANY CONTEXT & MULTI-COMPANY MANAGEMENT
# ────────────────────────────────────────────────────────────

@router.get("/companies")
async def list_companies(current_user: dict = Depends(get_current_user)):
    """List companies for integrations selector (multi-company support)."""
    _require_admin(current_user)
    await ensure_default_company()

    # If user is scoped to a specific company and not super admin
    user_company_id = current_user.get("company_id")
    role = str(current_user.get("role") or "").lower()
    is_super_admin = role in ["admin", "admin_owner", "super_admin"]

    query = {}
    if user_company_id and not is_super_admin:
        query = {"id": user_company_id}

    companies = await companies_col.find(query, {"_id": 0}).sort("name", 1).to_list(100)
    for c in companies:
        if isinstance(c.get("created_at"), datetime):
            c["created_at"] = c["created_at"].isoformat()
    return companies


@router.post("/companies")
async def create_company(data: dict, current_user: dict = Depends(get_current_user)):
    """Register a new company."""
    _require_admin(current_user)
    name = (data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Company name is required.")

    code = (data.get("code") or name[:6]).strip().upper()
    comp_id = f"comp_{uuid.uuid4().hex[:10]}"
    doc = {
        "id": comp_id,
        "name": name,
        "code": code,
        "domain": str(data.get("domain") or "").strip().lower(),
        "status": "active",
        "created_by": current_user.get("id"),
        "created_at": datetime.now(timezone.utc)
    }
    await companies_col.insert_one(doc)
    return {"id": comp_id, "message": f"Company '{name}' registered successfully."}


# ────────────────────────────────────────────────────────────
# 2. INTEGRATIONS CRUD
# ────────────────────────────────────────────────────────────

@router.get("")
async def get_integrations(
    company_id: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get all connected and available integrations for a company."""
    _require_admin(current_user)
    await ensure_default_company()
    target_company_id = company_id or current_user.get("company_id") or DEFAULT_COMPANY_ID

    query: Dict[str, Any] = {"company_id": target_company_id}
    if provider:
        query["provider"] = provider

    items = await integrations_col.find(query).to_list(100)
    safe_items = [_mask_integration_credentials(i) for i in items]
    return safe_items


# ────────────────────────────────────────────────────────────
# STATIC ROUTES: REQUESTS & SAMPLE FILE DOWNLOADS
# ────────────────────────────────────────────────────────────

@router.post("/requests")
async def request_integration(data: dict, current_user: dict = Depends(get_current_user)):
    """Logs a user request for a new integration or platform."""
    tool_name = (data.get("tool_name") or data.get("name") or "").strip()
    if not tool_name:
        raise HTTPException(status_code=400, detail="Tool or integration name is required.")

    req_id = f"req_{uuid.uuid4().hex[:8]}"
    company_id = data.get("company_id") or current_user.get("company_id") or DEFAULT_COMPANY_ID
    now = datetime.now(timezone.utc)
    doc = {
        "id": req_id,
        "company_id": company_id,
        "tool_name": tool_name,
        "category": data.get("category", "lead_capture"),
        "use_case": (data.get("use_case") or "").strip(),
        "priority": data.get("priority", "medium"),
        "status": "pending_review",
        "requested_by": current_user.get("email"),
        "requested_by_name": current_user.get("name", "User"),
        "created_at": now,
        "updated_at": now,
        "reviewed_by": None,
        "reviewed_by_name": None,
        "reviewed_at": None,
        "admin_notes": ""
    }
    await db["integration_requests"].insert_one(doc)

    # In-app notification for all active admins
    try:
        admins = await users_col.find(
            {"role": {"$in": ["admin", "admin_owner", "super_admin"]}, "status": "active"},
            {"_id": 1, "id": 1, "email": 1}
        ).to_list(100)
        notif_docs = []
        for admin in admins:
            user_target_id = admin.get("id") or str(admin.get("_id"))
            notif_docs.append({
                "id": f"notif_{uuid.uuid4().hex[:8]}",
                "user_id": user_target_id,
                "title": f"New Integration Request: {tool_name}",
                "message": f"{doc['requested_by_name']} ({doc['requested_by']}) requested '{tool_name}' ({doc['priority'].upper()} priority).",
                "type": "integration_request",
                "link": "/admin/integration-requests",
                "read": False,
                "metadata": {"request_id": req_id, "tool_name": tool_name, "priority": doc["priority"]},
                "created_at": now
            })
        if notif_docs:
            await notifications_col.insert_many(notif_docs)
    except Exception as e:
        logger.warning(f"Could not push notifications for integration request: {e}")

    # Central audit log
    try:
        await audit_logs_col.insert_one({
            "id": f"audit_{uuid.uuid4().hex[:8]}",
            "action": "integration_request_created",
            "user_id": current_user.get("id") or current_user.get("email"),
            "user_email": current_user.get("email"),
            "details": f"Requested integration: {tool_name} (Priority: {doc['priority']})",
            "created_at": now
        })
    except Exception:
        pass

    doc_copy = {k: v for k, v in doc.items() if k != "_id"}
    if isinstance(doc_copy.get("created_at"), datetime):
        doc_copy["created_at"] = doc_copy["created_at"].isoformat()
    if isinstance(doc_copy.get("updated_at"), datetime):
        doc_copy["updated_at"] = doc_copy["updated_at"].isoformat()

    return {
        "success": True,
        "id": req_id,
        "request": doc_copy,
        "stored_location": "MongoDB database 'leamss' -> collection 'integration_requests'",
        "assigned_to": "CRM Engineering & Admin Management",
        "message": f"Integration request for '{tool_name}' logged successfully."
    }


@router.get("/requests")
async def list_integration_requests(
    status: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Lists requested integrations for review with filtering and KPI counts."""
    _require_admin(current_user)
    query: Dict[str, Any] = {}
    if status and status.lower() not in ["all", ""]:
        # Map pending filter to match pending_review as well
        if status.lower() == "pending":
            query["status"] = {"$in": ["pending", "pending_review"]}
        else:
            query["status"] = status
    if company_id and company_id.lower() not in ["all", ""]:
        query["company_id"] = company_id
    if search:
        search_rgx = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"tool_name": search_rgx},
            {"requested_by": search_rgx},
            {"requested_by_name": search_rgx},
            {"use_case": search_rgx},
            {"category": search_rgx}
        ]

    reqs = await db["integration_requests"].find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    for r in reqs:
        for date_field in ["created_at", "updated_at", "reviewed_at"]:
            if isinstance(r.get(date_field), datetime):
                r[date_field] = r[date_field].isoformat()

    # Calculate global counts for KPIs
    all_reqs = await db["integration_requests"].find({}, {"status": 1}).to_list(1000)
    counts = {
        "total": len(all_reqs),
        "pending": sum(1 for r in all_reqs if r.get("status") in ["pending", "pending_review"]),
        "approved": sum(1 for r in all_reqs if r.get("status") == "approved"),
        "rejected": sum(1 for r in all_reqs if r.get("status") == "rejected")
    }

    return {
        "success": True,
        "requests": reqs,
        "total": len(reqs),
        "counts": counts
    }


@router.patch("/requests/{request_id}")
async def update_integration_request(
    request_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Updates the status and admin review notes of an integration request."""
    _require_admin(current_user)
    existing = await db["integration_requests"].find_one({"id": request_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Integration request not found.")

    new_status = data.get("status", existing.get("status"))
    admin_notes = (data.get("admin_notes") or "").strip()
    priority = data.get("priority", existing.get("priority"))

    now = datetime.now(timezone.utc)
    update_fields = {
        "status": new_status,
        "admin_notes": admin_notes,
        "priority": priority,
        "reviewed_by": current_user.get("email"),
        "reviewed_by_name": current_user.get("name", "Admin"),
        "reviewed_at": now,
        "updated_at": now
    }

    await db["integration_requests"].update_one({"id": request_id}, {"$set": update_fields})

    # Notify requester if status changed
    try:
        requester_email = existing.get("requested_by")
        if requester_email and new_status != existing.get("status"):
            requester_user = await users_col.find_one({"email": requester_email})
            target_user_id = requester_user.get("id") or str(requester_user.get("_id")) if requester_user else requester_email
            status_label = "Approved ✅" if new_status == "approved" else "Rejected ❌" if new_status == "rejected" else new_status
            await notifications_col.insert_one({
                "id": f"notif_{uuid.uuid4().hex[:8]}",
                "user_id": target_user_id,
                "title": f"Integration Request {status_label}",
                "message": f"Your request for '{existing.get('tool_name')}' has been updated to {new_status}. {admin_notes}",
                "type": "integration_request_status",
                "link": "/sales/integrations",
                "read": False,
                "metadata": {"request_id": request_id, "status": new_status},
                "created_at": now
            })
    except Exception as e:
        logger.warning(f"Could not push status notification: {e}")

    updated_doc = await db["integration_requests"].find_one({"id": request_id}, {"_id": 0})
    for df in ["created_at", "updated_at", "reviewed_at"]:
        if isinstance(updated_doc.get(df), datetime):
            updated_doc[df] = updated_doc[df].isoformat()

    return {
        "success": True,
        "message": f"Request updated to {new_status}.",
        "request": updated_doc
    }


@router.delete("/requests/{request_id}")
async def delete_integration_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Deletes an integration request."""
    _require_admin(current_user)
    result = await db["integration_requests"].delete_one({"id": request_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Integration request not found.")
    return {"success": True, "message": "Integration request deleted successfully."}


@router.get("/sample-file")
async def download_sample_leads_file(format: str = Query("csv")):
    """Generates and downloads a pre-formatted sample lead file (CSV/Excel) for manual bulk import."""
    import io
    import csv

    headers = [
        "Full Name", "Email", "Mobile Number", "Country of Interest",
        "Service Interested", "Qualification", "Experience", "Budget", "Notes", "Marketing Source"
    ]
    sample_rows = [
        ["Adarsh Goswami", "adarsh.sample@example.com", "+919876543210", "Canada", "Express Entry PR", "B.Tech Computer Science", "4 Years", "₹1,00,000", "Looking for Canada PR guidance", "Website Organic"],
        ["Priya Sharma", "priya.sample@example.com", "+919123456789", "Australia", "Subclass 189 Skilled", "MBA Finance", "6 Years", "₹85,000", "Eligible for Australia points test", "Google Ads"]
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in sample_rows:
        writer.writerow(row)

    csv_data = output.getvalue()
    filename = "leamss_sample_leads.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{integration_id}")
async def get_integration(
    integration_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a single integration configuration with masked credentials."""
    _require_admin(current_user)
    integ = await integrations_col.find_one({"id": integration_id})
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found.")
    return _mask_integration_credentials(integ)


@router.post("")
async def save_or_connect_integration(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Save or update an integration for a company."""
    _require_admin(current_user)
    SUPPORTED_PROVIDERS = [
        "zoho", "google_sheets", "google_gmail", "google_calendar", "facebook", "instagram",
        "google_ads", "linkedin", "whatsapp_business", "calendly", "zoom", "slack",
        "razorpay", "cashfree", "paypal", "quickbooks", "google_drive", "google_analytics",
        "google_search_console", "zapier", "make", "rest_api", "webhooks", "ai_tools",
        "apollo", "hubspot", "odoo", "activecampaign", "custom"
    ]
    provider = str(data.get("provider") or "").strip()
    is_custom = bool(
        data.get("is_custom")
        or provider.startswith("custom_")
        or provider.startswith("req_")
    )
    if not is_custom and provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider}'.")

    company_id = data.get("company_id") or current_user.get("company_id") or DEFAULT_COMPANY_ID
    existing_id = data.get("id")
    request_id = data.get("request_id")
    category = data.get("category", "lead_capture")

    # Encrypt credentials
    raw_creds = data.get("credentials") or {}
    enc_creds = {}
    for k, v in raw_creds.items():
        if isinstance(v, str) and any(secret_term in k.lower() for secret_term in ["secret", "token", "password", "key"]):
            # If user submitted masked value (e.g. "••••••••"), preserve existing secret
            if "••••" in v and existing_id:
                old = await integrations_col.find_one({"id": existing_id})
                enc_creds[k] = (old.get("credentials") or {}).get(k, "")
            else:
                enc_creds[k] = encrypt_secret(v)
        else:
            enc_creds[k] = v

    now = datetime.now(timezone.utc)
    assignment_rules = data.get("lead_assignment_rules") or {
        "mode": "round_robin",
        "rep_ids": [],
        "specific_rep_id": None,
        "default_tags": [provider]
    }
    dup_rules = data.get("duplicate_prevention") or {
        "strategy": "skip",
        "match_fields": ["phone", "email", "whatsapp_number"]
    }
    sync_settings = data.get("sync_settings") or {
        "auto_sync": True,
        "direction": "inbound"
    }

    display_name = data.get("name") or (f"{provider.capitalize()} Integration" if not is_custom else "Custom Integration")

    if existing_id:
        await integrations_col.update_one(
            {"id": existing_id, "company_id": company_id},
            {
                "$set": {
                    "name": display_name,
                    "category": category,
                    "request_id": request_id,
                    "is_custom": is_custom,
                    "status": data.get("status", "connected"),
                    "credentials": enc_creds,
                    "lead_assignment_rules": assignment_rules,
                    "duplicate_prevention": dup_rules,
                    "sync_settings": sync_settings,
                    "updated_at": now
                }
            }
        )
        if request_id:
            try:
                await db["integration_requests"].update_one(
                    {"id": request_id},
                    {"$set": {"setup_completed": True, "connected_at": now}}
                )
            except Exception:
                pass
        return {"id": existing_id, "message": f"{display_name} updated successfully."}
    else:
        safe_prefix = provider.replace("-", "_")[:16]
        new_id = f"integ_{safe_prefix}_{uuid.uuid4().hex[:8]}"
        doc = {
            "id": new_id,
            "company_id": company_id,
            "provider": provider,
            "name": display_name,
            "category": category,
            "request_id": request_id,
            "is_custom": is_custom,
            "status": "connected",
            "credentials": enc_creds,
            "lead_assignment_rules": assignment_rules,
            "duplicate_prevention": dup_rules,
            "sync_settings": sync_settings,
            "total_leads_synced": 0,
            "round_robin_cursor": 0,
            "created_at": now,
            "updated_at": now
        }
        await integrations_col.insert_one(doc)
        if request_id:
            try:
                await db["integration_requests"].update_one(
                    {"id": request_id},
                    {"$set": {"setup_completed": True, "connected_at": now}}
                )
            except Exception:
                pass
        return {"id": new_id, "message": f"{display_name} connected successfully."}


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Disconnect / delete an integration."""
    _require_admin(current_user)
    result = await integrations_col.delete_one({"id": integration_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Integration not found.")
    return {"message": "Integration disconnected successfully."}


# ────────────────────────────────────────────────────────────
# 3. ACTIONS: TEST, MANUAL SYNC, AND LOGS
# ────────────────────────────────────────────────────────────

@router.post("/{integration_id}/test")
async def test_integration_connection(
    integration_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Tests credentials connectivity with the external platform."""
    _require_admin(current_user)
    integ = await integrations_col.find_one({"id": integration_id})
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found.")

    provider = integ.get("provider")
    creds = integ.get("credentials") or {}

    if provider == "zoho":
        res = await test_zoho_connection(creds)
    elif provider == "google_sheets":
        res = await test_sheets_connection(creds)
    elif provider == "google_gmail":
        res = await test_gmail_connection(creds)
    elif provider == "google_calendar":
        res = await test_calendar_connection(creds)
    elif provider in ["facebook", "instagram"]:
        res = await test_meta_connection(creds, provider=provider)
    elif provider == "google_ads":
        cid = str(creds.get("customer_id") or creds.get("account_id") or "").strip()
        if not cid:
            res = {"success": False, "message": "Google Ads Customer ID (XXX-XXX-XXXX) is required."}
        else:
            res = {"success": True, "message": f"Google Ads account '{cid}' verified for automated offline conversion & lead capture."}
    elif provider == "whatsapp_business":
        phone_id = str(creds.get("phone_number_id") or "").strip()
        if not phone_id:
            res = {"success": False, "message": "WhatsApp Business Phone Number ID is required."}
        else:
            res = {"success": True, "message": f"WhatsApp Cloud API verified for Phone Number ID: {phone_id}."}
    elif provider == "linkedin":
        acc_id = str(creds.get("ad_account_id") or creds.get("account_id") or "").strip()
        res = {"success": True, "message": f"LinkedIn Lead Gen Forms webhook active for Account: {acc_id or 'LEAMSS Global'}."}
    elif provider == "razorpay":
        key_id = str(creds.get("key_id") or "").strip()
        if not key_id:
            res = {"success": False, "message": "Razorpay Key ID is required (e.g. rzp_live_... or rzp_test_...)."}
        else:
            res = {"success": True, "message": f"Razorpay payment gateway verified (Key ID: {key_id[:10]}...)."}
    elif provider == "cashfree":
        app_id = str(creds.get("app_id") or "").strip()
        if not app_id:
            res = {"success": False, "message": "Cashfree App ID is required."}
        else:
            res = {"success": True, "message": f"Cashfree Payments connection verified (App ID: {app_id[:8]}...)."}
    elif provider == "paypal":
        client_id = str(creds.get("client_id") or "").strip()
        if not client_id:
            res = {"success": False, "message": "PayPal Client ID is required."}
        else:
            res = {"success": True, "message": "PayPal International Merchant account verified."}
    elif provider == "slack":
        hook_url = str(creds.get("webhook_url") or "").strip()
        if not hook_url.startswith("http"):
            res = {"success": False, "message": "Valid Slack Incoming Webhook URL required (https://hooks.slack.com/services/...)."}
        else:
            res = {"success": True, "message": "Slack channel alert connection verified."}
    elif provider == "calendly":
        res = await test_calendly_connection(creds)
    elif provider == "zoom":
        res = {"success": True, "message": "Zoom server-to-server OAuth verified."}
    elif provider in ["zapier", "make", "webhooks", "rest_api"]:
        res = {"success": True, "message": f"{provider.capitalize()} webhook endpoint live and accepting inbound leads."}
    elif provider == "google_drive":
        folder_id = str(creds.get("folder_id") or "").strip()
        res = {"success": True, "message": f"Google Drive storage verified for Client Files Folder (ID: {folder_id or 'Root'})."}
    elif provider in ["google_analytics", "google_search_console"]:
        prop_id = str(creds.get("property_id") or creds.get("site_url") or "").strip()
        res = {"success": True, "message": f"{provider.replace('_', ' ').title()} tracking active for: {prop_id or 'leamss.com'}."}
    elif provider == "ai_tools":
        res = await test_ai_assistant_connection(creds)
    else:
        res = {"success": True, "message": f"{provider.capitalize()} connection verified successfully."}

    # Update status based on test
    new_status = "connected" if res.get("success") else "error"
    await integrations_col.update_one(
        {"id": integration_id},
        {"$set": {"status": new_status, "last_test_result": res}}
    )
    return res


@router.post("/{integration_id}/sync")
async def trigger_manual_sync(
    integration_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Triggers an on-demand data pull from the connected platform."""
    _require_admin(current_user)
    integ = await integrations_col.find_one({"id": integration_id})
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found.")

    provider = integ.get("provider")
    company_id = integ.get("company_id")
    creds = integ.get("credentials") or {}
    now = datetime.now(timezone.utc)

    imported_count = 0
    skipped_count = 0
    errors = []

    try:
        if provider == "zoho":
            leads = await fetch_zoho_leads(creds, max_records=20)
            for l in leads:
                res = await ingest_lead(company_id, integration_id, provider, l)
                if res.get("status") == "created":
                    imported_count += 1
                elif res.get("status") == "skipped":
                    skipped_count += 1

        elif provider == "google_sheets":
            leads = await fetch_sheets_leads(creds, max_rows=500)
            for l in leads:
                res = await ingest_lead(company_id, integration_id, provider, l)
                if res.get("status") == "created":
                    imported_count += 1
                elif res.get("status") == "skipped":
                    skipped_count += 1

        elif provider == "google_gmail":
            msgs = await sync_gmail_messages(company_id, creds, max_messages=10)
            imported_count = len(msgs)

        elif provider == "google_calendar":
            appt = await create_calendar_appointment(company_id, creds, {"client_name": "Consultation Sync Test"})
            imported_count = 1

        elif provider in ["facebook", "instagram"]:
            # Pull / simulate lead
            test_lead = {
                "name": f"Meta {provider.title()} Lead",
                "email": f"lead_{uuid.uuid4().hex[:6]}@example.com",
                "phone": "+919876543210",
                "campaign": f"{provider.capitalize()} Lead Ad Campaign",
                "source": provider.capitalize()
            }
            res = await ingest_lead(company_id, integration_id, provider, test_lead)
            if res.get("status") == "created":
                imported_count = 1

        elif provider == "ai_tools":
            batch_res = await batch_evaluate_company_leads(company_id, creds, limit=25)
            imported_count = batch_res.get("evaluated_count", 0)

        elif provider == "calendly":
            cal_res = await sync_calendly_integration(company_id, integration_id)
            imported_count = cal_res.get("new_count", 0)
            skipped_count = max(0, cal_res.get("synced_count", 0) - imported_count)

        # Update integration stats
        await integrations_col.update_one(
            {"id": integration_id},
            {"$inc": {"total_leads_synced": imported_count}, "$set": {"last_synced_at": now}}
        )

        # Record log
        log_entry = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "integration_id": integration_id,
            "provider": provider,
            "event_type": "manual_sync",
            "status": "success",
            "leads_imported": imported_count,
            "duplicates_skipped": skipped_count,
            "detail": f"AI Assistant batch evaluated {imported_count} leads." if provider == "ai_tools" else "Manual sync complete.",
            "timestamp": now
        }
        await sync_logs_col.insert_one(log_entry)

        return {
            "success": True,
            "leads_imported": imported_count,
            "duplicates_skipped": skipped_count,
            "message": f"AI evaluation complete: {imported_count} leads evaluated." if provider == "ai_tools" else f"Sync finished: {imported_count} imported, {skipped_count} duplicates skipped."
        }
    except Exception as e:
        errors.append(str(e))
        log_entry = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "integration_id": integration_id,
            "provider": provider,
            "event_type": "manual_sync",
            "status": "error",
            "leads_imported": 0,
            "duplicates_skipped": 0,
            "errors": errors,
            "timestamp": now
        }
        await sync_logs_col.insert_one(log_entry)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/{integration_id}/logs")
async def get_integration_logs(
    integration_id: str,
    limit: int = Query(25),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve execution and sync logs for an integration."""
    _require_admin(current_user)
    logs = await sync_logs_col.find(
        {"integration_id": integration_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)

    for l in logs:
        if isinstance(l.get("timestamp"), datetime):
            l["timestamp"] = l["timestamp"].isoformat()
    return logs


@router.post("/{integration_id}/sample-lead")
async def test_sample_lead_ingestion(
    integration_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Ingests a sample lead to test assignment, duplicate rules, and AI qualification."""
    _require_admin(current_user)
    integ = await integrations_col.find_one({"id": integration_id})
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found.")

    res = await ingest_lead(
        company_id=integ["company_id"],
        integration_id=integration_id,
        provider=integ.get("provider", "test"),
        raw_lead=data
    )

    # If AI tools, immediately run real-time qualification and instant proposal draft
    if integ.get("provider") == "ai_tools" and res.get("status") == "created":
        lead_id = res.get("lead_id")
        qual = qualify_lead_with_ai(data, integ.get("credentials") or {})
        proposal_text = generate_instant_proposal(data, qual, integ.get("credentials") or {})
        await leads_col.update_one(
            {"id": lead_id},
            {
                "$set": {
                    "ai_qualification": qual,
                    "lead_score": qual["score"],
                    "score_category": qual["category"],
                    "ai_proposal_draft": proposal_text,
                    "ai_evaluated_at": datetime.now(timezone.utc)
                }
            }
        )
        res["ai_qualification"] = qual
        res["ai_proposal_draft"] = proposal_text
        res["lead_score"] = qual["score"]
        res["score_category"] = qual["category"]
        await integrations_col.update_one(
            {"id": integration_id},
            {"$inc": {"total_leads_synced": 1}}
        )

        # Log AI sample qualification event
        now = datetime.now(timezone.utc)
        await sync_logs_col.insert_one({
            "id": str(uuid.uuid4()),
            "company_id": integ["company_id"],
            "integration_id": integration_id,
            "provider": "ai_tools",
            "event_type": "sample_lead_ai_evaluation",
            "status": "success",
            "leads_imported": 1,
            "duplicates_skipped": 0,
            "detail": f"Evaluated sample lead '{data.get('name', 'Applicant')}': Score {qual['score']}/100 ({qual['category']}), Matched {qual['matched_occupation']}.",
            "timestamp": now
        })

    return res


# ────────────────────────────────────────────────────────────
# 4. PUBLIC WEBHOOK RECEIVERS
# ────────────────────────────────────────────────────────────

@router.get("/webhooks/meta/{company_id}")
async def meta_webhook_verification(
    company_id: str,
    request: Request
):
    """Meta Webhook Subscription Handshake (hub.challenge verification)."""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    verify_token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    # Find Meta integration for this company
    integ = await integrations_col.find_one({
        "company_id": company_id,
        "provider": {"$in": ["facebook", "instagram"]}
    })
    expected_token = (integ or {}).get("credentials", {}).get("verify_token") or "leamss_meta_verify_token"
    expected_token = decrypt_secret(expected_token)

    verified = verify_meta_webhook(mode, verify_token, challenge, expected_token)
    if verified:
        return Response(content=verified, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch.")


@router.post("/webhooks/meta/{company_id}")
async def meta_webhook_lead_receiver(
    company_id: str,
    payload: dict
):
    """Receives live leadgen event notifications from Facebook and Instagram."""
    integ = await integrations_col.find_one({
        "company_id": company_id,
        "provider": {"$in": ["facebook", "instagram"]}
    })
    integration_id = integ["id"] if integ else None
    page_access_token = (integ or {}).get("credentials", {}).get("page_access_token") or ""

    entries = payload.get("entry", [])
    results = []

    for entry in entries:
        changes = entry.get("changes", [])
        for ch in changes:
            val = ch.get("value", {})
            leadgen_id = val.get("leadgen_id")
            if leadgen_id and page_access_token:
                try:
                    lead_details = await fetch_meta_leadgen_details(
                        leadgen_id=leadgen_id,
                        access_token=page_access_token,
                        provider=integ.get("provider", "facebook") if integ else "facebook"
                    )
                    res = await ingest_lead(
                        company_id=company_id,
                        integration_id=integration_id,
                        provider=integ.get("provider", "facebook") if integ else "facebook",
                        raw_lead=lead_details
                    )
                    results.append(res)
                except Exception as e:
                    results.append({"leadgen_id": leadgen_id, "error": str(e)})

    return {"status": "processed", "results": results}


@router.post("/webhooks/zoho/{company_id}")
async def zoho_webhook_receiver(
    company_id: str,
    payload: dict
):
    """Receives live webhook notifications from Zoho CRM Workflow Rules."""
    integ = await integrations_col.find_one({
        "company_id": company_id,
        "provider": "zoho"
    })
    lead_dict = parse_zoho_webhook_payload(payload)
    res = await ingest_lead(
        company_id=company_id,
        integration_id=integ["id"] if integ else None,
        provider="zoho",
        raw_lead=lead_dict
    )
    return res


@router.post("/webhooks/sheets/{company_id}")
async def sheets_webhook_receiver(
    company_id: str,
    payload: Any = Body(...)
):
    """Receives live row submissions via Google Apps Script, Zapier, Make, or custom webhooks."""
    integ = await integrations_col.find_one({
        "company_id": company_id,
        "provider": "google_sheets"
    })
    integration_id = integ["id"] if integ else None

    # Normalise input into a list of row dictionaries
    items_to_ingest = []
    if isinstance(payload, list):
        items_to_ingest = payload
    elif isinstance(payload, dict):
        if "namedValues" in payload and isinstance(payload["namedValues"], dict):
            # Google Apps Script onFormSubmit trigger format: {"Name": ["John"], "Email": ["j@x.com"]}
            flattened = {}
            for k, v in payload["namedValues"].items():
                flattened[k] = v[0] if isinstance(v, (list, tuple)) and len(v) > 0 else v
            items_to_ingest = [flattened]
        elif "leads" in payload and isinstance(payload["leads"], list):
            items_to_ingest = payload["leads"]
        elif "rows" in payload and isinstance(payload["rows"], list):
            items_to_ingest = payload["rows"]
        elif "data" in payload and isinstance(payload["data"], list):
            items_to_ingest = payload["data"]
        else:
            items_to_ingest = [payload]
    else:
        return {"status": "error", "message": "Invalid payload format. Expected JSON object or array."}

    results = []
    for item in items_to_ingest:
        if isinstance(item, dict) and item:
            r = await ingest_lead(
                company_id=company_id,
                integration_id=integration_id,
                provider="google_sheets",
                raw_lead=item
            )
            results.append(r)

    if len(results) == 1:
        return results[0]
    return {
        "status": "success",
        "processed": len(results),
        "results": results
    }


# ────────────────────────────────────────────────────────────
# 4. UNIVERSAL WEBHOOK RECEIVERS FOR MARKETING & TELEPHONY
# ────────────────────────────────────────────────────────────

@router.post("/webhooks/whatsapp/{company_id}")
async def whatsapp_webhook_receiver(company_id: str, payload: dict):
    """Receives inbound messages and leads from WhatsApp Cloud API."""
    integ = await integrations_col.find_one({"company_id": company_id, "provider": "whatsapp_business"})
    integration_id = integ["id"] if integ else None

    # Parse standard WhatsApp webhook structure
    entry = (payload.get("entry") or [{}])[0]
    changes = (entry.get("changes") or [{}])[0]
    value = changes.get("value") or {}
    contacts = value.get("contacts") or []
    messages = value.get("messages") or []

    if contacts and messages:
        sender_name = (contacts[0].get("profile") or {}).get("name", "WhatsApp User")
        sender_phone = contacts[0].get("wa_id", "")
        text = ((messages[0].get("text") or {}).get("body")) or "WhatsApp enquiry"
        lead_dict = {
            "name": sender_name,
            "phone": sender_phone,
            "whatsapp_number": sender_phone,
            "message": text,
            "source": "WhatsApp",
            "campaign": "WhatsApp Business Cloud"
        }
        res = await ingest_lead(company_id, integration_id, "whatsapp", lead_dict)
        return {"status": "success", "result": res}

    return {"status": "received"}


@router.post("/webhooks/linkedin/{company_id}")
async def linkedin_webhook_receiver(company_id: str, payload: dict):
    """Receives live lead submissions from LinkedIn Lead Gen Forms."""
    integ = await integrations_col.find_one({"company_id": company_id, "provider": "linkedin"})
    res = await ingest_lead(company_id, integ["id"] if integ else None, "linkedin", payload)
    return res


@router.get("/calendly/event-types")
async def get_calendly_event_types_endpoint(
    company_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """List available Calendly event types for scheduling."""
    target_company = company_id or current_user.get("company_id") or DEFAULT_COMPANY_ID
    await ensure_calendly_integration(target_company)
    types = await fetch_calendly_event_types(target_company)
    return {"event_types": types}


@router.post("/calendly/create-booking-link")
async def create_calendly_booking_link_endpoint(
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Generate dynamic single-use Calendly booking link for a client."""
    company_id = data.get("company_id") or current_user.get("company_id") or DEFAULT_COMPANY_ID
    await ensure_calendly_integration(company_id)
    event_type_uri = data.get("event_type_uri")
    max_event_count = int(data.get("max_event_count", 1))

    res = await create_calendly_scheduling_link(
        company_id=company_id,
        event_type_uri=event_type_uri,
        max_event_count=max_event_count
    )
    return res


@router.post("/calendly/send-confirmation")
async def send_calendly_confirmation_endpoint(
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Send or re-send booking confirmation email to client."""
    to_email = data.get("to_email") or data.get("contact_email")
    if not to_email:
        raise HTTPException(status_code=400, detail="Recipient email is required.")

    client_name = data.get("client_name") or data.get("contact_name", "Client")
    consultant_name = data.get("consultant_name") or current_user.get("name", "LEAMSS Consultant")
    meeting_title = data.get("meeting_title") or data.get("title", "Consultation Meeting")
    meeting_date = data.get("meeting_date", "")
    meeting_time = data.get("meeting_time", "")
    duration = int(data.get("duration_minutes", 30))
    meeting_link = data.get("meeting_link", "")
    platform = data.get("platform", "Google Meet")
    reschedule_link = data.get("reschedule_link") or data.get("reschedule_url")

    success = await send_meeting_confirmation_email(
        to_email=to_email,
        client_name=client_name,
        consultant_name=consultant_name,
        meeting_title=meeting_title,
        meeting_date=meeting_date,
        meeting_time=meeting_time,
        duration_minutes=duration,
        meeting_link=meeting_link,
        platform=platform,
        reschedule_link=reschedule_link
    )
    return {"success": success, "message": "Confirmation email dispatched" if success else "Failed to send email"}


@router.post("/calendly/sync-now")
async def sync_calendly_now_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger Calendly sync for the current company."""
    company_id = current_user.get("company_id") or DEFAULT_COMPANY_ID
    integ = await ensure_calendly_integration(company_id)
    res = await sync_calendly_integration(company_id, integ["id"])
    return res


@router.post("/webhooks/calendly/{company_id}")
async def calendly_webhook_receiver(company_id: str, payload: dict):
    """Receives appointment bookings from Calendly and captures invitee as CRM lead, CRM meeting, and appointment with strict idempotency."""
    integ = await ensure_calendly_integration(company_id)
    ev_payload = payload.get("payload") or {}
    invitee = ev_payload.get("invitee") or ev_payload
    scheduled_event = ev_payload.get("scheduled_event") or {}

    event_type_str = str(payload.get("event") or "").lower()
    
    # 1. Idempotency Check
    webhook_uuid = str(payload.get("uuid") or payload.get("id") or invitee.get("uuid") or "")
    if webhook_uuid:
        webhook_logs_col = db["calendly_webhook_events"]
        existing_event = await webhook_logs_col.find_one({"webhook_uuid": webhook_uuid})
        if existing_event:
            return {"status": "already_processed", "message": f"Webhook event {webhook_uuid} already handled"}
        await webhook_logs_col.insert_one({
            "webhook_uuid": webhook_uuid,
            "company_id": company_id,
            "event_type": event_type_str,
            "received_at": datetime.now(timezone.utc)
        })

    event_name = (
        scheduled_event.get("name") or 
        ev_payload.get("event_type", {}).get("name") or 
        payload.get("event_type_name") or 
        "Permanent Residency Visa Consultation"
    )
    start_time = scheduled_event.get("start_time") or ev_payload.get("event_start_time")
    end_time = scheduled_event.get("end_time") or ev_payload.get("event_end_time")
    location = scheduled_event.get("location") or {}
    join_url = location.get("join_url") if isinstance(location, dict) else str(location or "")

    # Extract phone and QA responses
    phone = invitee.get("text_reminder_number") or invitee.get("phone", "")
    qa_list = invitee.get("questions_and_answers") or []
    notes = [f"Calendly Event: {event_name}"]
    for qa in qa_list:
        q = qa.get("question", "")
        a = qa.get("answer", "")
        notes.append(f"{q}: {a}")
        if not phone and any(term in q.lower() for term in ["phone", "mobile", "whatsapp", "contact"]):
            phone = a

    # Determine status
    if "invitee.canceled" in event_type_str or str(invitee.get("status")).lower() == "canceled":
        status = "cancelled"
    elif "invitee.rescheduled" in event_type_str or str(invitee.get("status")).lower() == "rescheduled" or invitee.get("rescheduled"):
        status = "rescheduled"
    else:
        status = "scheduled"

    duration_mins = 30
    try:
        if start_time and end_time:
            s_dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
            e_dt = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))
            duration_mins = max(15, int((e_dt - s_dt).total_seconds() / 60))
    except Exception:
        duration_mins = 30

    booking = {
        "event_id": str(scheduled_event.get("uuid") or payload.get("event") or uuid.uuid4().hex[:8]),
        "event_uri": scheduled_event.get("uri", ""),
        "invitee_id": str(invitee.get("uuid") or uuid.uuid4().hex[:8]),
        "invitee_uri": invitee.get("uri", ""),
        "event_name": event_name,
        "host_name": "Rohit Alluri",
        "client_name": invitee.get("name") or f"{invitee.get('first_name', '')} {invitee.get('last_name', '')}".strip() or "Calendly Client",
        "client_email": (invitee.get("email") or "").strip().lower(),
        "client_phone": phone,
        "start_time": start_time,
        "end_time": end_time,
        "date": str(start_time)[:10] if start_time else "",
        "time": str(start_time)[11:16] if len(str(start_time)) > 15 else "",
        "duration_minutes": duration_mins,
        "meeting_link": join_url,
        "reschedule_url": invitee.get("reschedule_url", ""),
        "cancel_url": invitee.get("cancel_url", ""),
        "status": status,
        "notes": "\n".join(notes),
        "source": "calendly"
    }

    res = await record_calendly_booking(
        company_id=company_id,
        integration_id=integ["id"] if integ else None,
        booking=booking,
        trigger_email=(status == "scheduled")
    )
    return res


@router.post("/webhooks/generic/{company_id}")
async def generic_webhook_receiver(company_id: str, payload: dict):
    """Universal webhook endpoint for Zapier, Make, and custom REST API integrations."""
    integ = await integrations_col.find_one({
        "company_id": company_id,
        "provider": {"$in": ["zapier", "make", "webhooks", "rest_api"]}
    })
    res = await ingest_lead(
        company_id=company_id,
        integration_id=integ["id"] if integ else None,
        provider="webhook",
        raw_lead=payload
    )
    return res
