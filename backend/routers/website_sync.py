"""Website Sync Router.

Exposes endpoints for:
1. Live Webhook ingestion from `https://leamss.com/navratri-offers` (instant real-time lead capture)
2. Direct MySQL database sync against `hosldwuh_staging` table `navratri_registrations`
3. Bulk JSON payload importer
4. Sync health and status
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks

from core.auth import get_current_user
from core.database import db
from core.website_sync import upsert_website_lead, sync_from_mysql_database

from core.navratri_automation import (
    is_lead_paid,
    has_lead_resume,
    send_navratri_resume_request,
    send_navratri_payment_link,
)

router = APIRouter(prefix="/leads", tags=["Website Lead Sync"])
leads_col = db["leads"]


@router.post("/navratri-webhook")
async def navratri_lead_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    is_sync: Optional[bool] = Query(False),
    notify: Optional[bool] = Query(None),
):
    """Public webhook receiver for https://leamss.com/navratri-offers form submissions.
    
    Can be called directly by PHP/Laravel on leamss.com when a lead registers or makes a payment.
    Accepts raw JSON or form-encoded payloads.
    """
    try:
        data = await request.json()
    except Exception:
        form_data = await request.form()
        data = dict(form_data)

    if not data:
        raise HTTPException(status_code=400, detail="No registration data provided in payload")

    # Check if this request is a sync/batch operation (do NOT send automated messages for mass syncs)
    sync_flag = (
        is_sync is True
        or data.get("is_sync") in (True, "true", "1", 1)
        or data.get("sync") in (True, "true", "1", 1)
        or data.get("is_bulk") in (True, "true", "1", 1)
        or data.get("notify") in (False, "false", "0", 0)
        or (notify is False)
    )

    # Upsert the lead into MongoDB
    lead_doc, is_new = await upsert_website_lead(data)

    # Only send automated Email/WhatsApp notifications if NOT a bulk/historical sync
    if not sync_flag:
        if is_lead_paid(lead_doc):
            # Paid lead: if resume is missing and hasn't been requested in the last 24 hours
            if not has_lead_resume(lead_doc) and not lead_doc.get("last_resume_request_sent_at"):
                background_tasks.add_task(send_navratri_resume_request, lead_doc)
        else:
            # Unpaid lead: only auto-send payment link if fresh new registration and hasn't been sent
            if is_new and not lead_doc.get("last_payment_link_sent_at"):
                background_tasks.add_task(send_navratri_payment_link, lead_doc)

    return {
        "status": "success",
        "action": "created" if is_new else "updated",
        "lead_id": lead_doc.get("id"),
        "lead_number": lead_doc.get("lead_number"),
        "unique_id": lead_doc.get("unique_id"),
        "payment_status": lead_doc.get("payment_status"),
        "has_resume": has_lead_resume(lead_doc),
        "received_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/sync-mysql")
async def sync_mysql_endpoint(
    payload: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
):
    """Admin endpoint to trigger a direct sync from MySQL `hosldwuh_staging` table `navratri_registrations`."""
    if current_user.get("role") not in ("admin", "admin_owner", "case_manager", "partner"):
        raise HTTPException(status_code=403, detail="Admin authorization required to trigger database sync")

    p = payload or {}
    try:
        result = await sync_from_mysql_database(
            host=p.get("host"),
            port=p.get("port"),
            user=p.get("user"),
            password=p.get("password"),
            database=p.get("database"),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database sync failed: {str(e)}")


@router.post("/bulk-import-navratri")
async def bulk_import_navratri(
    records: List[Dict[str, Any]],
    current_user: dict = Depends(get_current_user),
):
    """Bulk import or update raw records exported from phpMyAdmin / MySQL table."""
    if current_user.get("role") not in ("admin", "admin_owner", "case_manager", "partner"):
        raise HTTPException(status_code=403, detail="Admin authorization required")

    created = 0
    updated = 0
    for r in records:
        _, is_new = await upsert_website_lead(r)
        if is_new:
            created += 1
        else:
            updated += 1

    return {
        "status": "success",
        "total_processed": len(records),
        "created": created,
        "updated": updated,
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/website-sync-summary")
async def get_website_sync_summary(current_user: dict = Depends(get_current_user)):
    """Returns overview of website-generated leads and payment breakdown."""
    total_navratri = await leads_col.count_documents({"source": "Navratri Offer (leamss.com)"})
    paid_navratri = await leads_col.count_documents({
        "source": "Navratri Offer (leamss.com)",
        "payment_status": "success"
    })
    pending_navratri = await leads_col.count_documents({
        "source": "Navratri Offer (leamss.com)",
        "payment_status": "pending"
    })
    failed_navratri = await leads_col.count_documents({
        "source": "Navratri Offer (leamss.com)",
        "payment_status": "failed"
    })

    recent_leads = await leads_col.find(
        {"source": "Navratri Offer (leamss.com)"},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)

    for l in recent_leads:
        for f in ("created_at", "updated_at", "paid_at", "last_contacted_at"):
            if isinstance(l.get(f), datetime):
                l[f] = l[f].isoformat()

    return {
        "total_registrations": total_navratri,
        "paid_count": paid_navratri,
        "pending_count": pending_navratri,
        "failed_count": failed_navratri,
        "recent_registrations": recent_leads,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
