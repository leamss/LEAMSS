"""CRM Sales Router — Deals, Payments, Campaigns, Reports, Performance, Automation, SLA & Audit Logs"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from core.database import db
from core.auth import get_current_user
from core.services import create_notification, log_activity

router = APIRouter(prefix="/crm", tags=["CRM Sales"])

crm_deals_col = db["crm_deals"]
crm_payments_col = db["crm_payments"]
crm_campaigns_col = db["crm_campaigns"]
crm_automation_rules_col = db["crm_automation_rules"]
crm_audit_logs_col = db["crm_audit_logs"]
crm_calls_col = db["crm_calls"]
crm_whatsapp_col = db["crm_whatsapp_messages"]
crm_emails_col = db["crm_emails"]
crm_tasks_col = db["crm_tasks"]
crm_meetings_col = db["crm_meetings"]
follow_ups_col = db["follow_ups"]
leads_col = db["leads"]
users_col = db["users"]
sales_col = db["sales"]
cases_col = db["cases"]
audit_logs_col = db["audit_logs"]


def _is_sales_person(user: dict) -> bool:
    sales_roles = [
        "partner", "external_partner",
        "sales_executive", "sr_sales_executive", "senior_sales_executive",
        "sales_rep", "sales_person", "sales"
    ]
    return user.get("role") in sales_roles or user.get("rbac_role") in sales_roles


def _is_manager_or_admin(user: dict) -> bool:
    role = user.get("role", "")
    rbac = user.get("rbac_role", "")
    return role in ["admin", "admin_owner", "sales_manager", "sales_head"] or rbac in ["admin_owner", "sales_manager", "sales_head", "admin"]


def _is_admin(user: dict) -> bool:
    role = user.get("role", "")
    rbac = user.get("rbac_role", "")
    return role in ["admin", "admin_owner", "super_admin"] or rbac in ["admin", "admin_owner", "super_admin"]


ROLE_LABELS = {
    "admin": "Admin / Director",
    "admin_owner": "Admin / Owner",
    "sales_head": "Sales Head (L4)",
    "sales_manager": "Sales Manager (L3)",
    "sr_sales_executive": "Senior Sales Executive (L2)",
    "senior_sales_executive": "Senior Sales Executive (L2)",
    "sales_executive": "Sales Executive (L1)",
    "sales_rep": "Sales Executive (L1)",
    "sales_person": "Sales Executive (L1)",
    "sales": "Sales Executive (L1)",
    "partner": "External Partner (L0)",
    "external_partner": "External Partner (L0)",
}

ROLE_DESCRIPTIONS = {
    "admin": "Full system management, client conversions, high-level deal approvals and sales oversight",
    "admin_owner": "Full system management, client conversions, high-level deal approvals and sales oversight",
    "sales_head": "All sales data, team management, dept targets, high discount approvals",
    "sales_manager": "Team PAs, leads, targets, medium discount approval, team follow-ups & performance",
    "sr_sales_executive": "Senior IC — leads, conversions, agreements, mentorship visibility",
    "senior_sales_executive": "Senior IC — leads, conversions, agreements, mentorship visibility",
    "sales_executive": "Internal sales — owns PAs, leads, targets, client conversions, attendance self",
    "partner": "External partner — owns PAs, assigned client leads, referral commissions",
    "external_partner": "External partner — owns PAs, assigned client leads, referral commissions",
}


# ────────────────────────────────────────────────────────────
# 1. ACTIONS WAITING FOR YOU (DASHBOARD WIDGET)
# ────────────────────────────────────────────────────────────

@router.get("/actions-waiting")
async def get_actions_waiting_for_you(current_user: dict = Depends(get_current_user)):
    """
    Get counts for the 8 'Actions Waiting for You' clickable cards:
    1. Calls Due
    2. Follow-ups Due
    3. WhatsApp Replies
    4. Emails Pending
    5. Payment Follow-ups
    6. Documents Pending
    7. Meetings Today
    8. Overdue Actions
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_end = (datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)).isoformat()

    user_match = {"assigned_to": current_user["id"]} if _is_sales_person(current_user) else {}

    # 1. Calls Due (today)
    calls_due_query = {"type": "Call", "status": "pending", "scheduled_at": {"$lte": today_end}}
    if user_match:
        calls_due_query.update(user_match)
    calls_due_count = await follow_ups_col.count_documents(calls_due_query)

    # 2. Follow-ups Due (today)
    fu_due_query = {"status": "pending", "scheduled_at": {"$gte": today_start, "$lte": today_end}}
    if user_match:
        fu_due_query.update(user_match)
    fu_due_count = await follow_ups_col.count_documents(fu_due_query)

    # 3. WhatsApp Replies (inbound unread)
    wa_match: Dict[str, Any] = {"direction": "inbound", "read": False}
    if _is_sales_person(current_user):
        wa_match["sales_person_id"] = current_user["id"]
    whatsapp_replies_count = await crm_whatsapp_col.count_documents(wa_match)

    # 4. Emails Pending
    email_match: Dict[str, Any] = {"status": {"$in": ["pending", "draft"]}}
    if _is_sales_person(current_user):
        email_match["sales_person_id"] = current_user["id"]
    emails_pending_count = await crm_emails_col.count_documents(email_match)

    # 5. Payment Follow-ups
    payment_fu_query = {"type": "Payment Follow-up", "status": "pending"}
    if user_match:
        payment_fu_query.update(user_match)
    payment_fu_count = await follow_ups_col.count_documents(payment_fu_query)

    # 6. Documents Pending (leads with stage in assessment/proposal or missing docs)
    doc_lead_query = {"stage": {"$in": ["assessment", "proposal", "proposal_sent", "payment_pending"]}}
    if _is_sales_person(current_user):
        doc_lead_query["assigned_to"] = current_user["id"]
    docs_pending_count = await leads_col.count_documents(doc_lead_query)

    # 7. Meetings Today
    meet_query = {"meeting_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "status": "scheduled"}
    if _is_sales_person(current_user):
        meet_query["sales_person_id"] = current_user["id"]
    meetings_today_count = await crm_meetings_col.count_documents(meet_query)

    # 8. Overdue Actions (overdue follow-ups + overdue tasks)
    overdue_fu_query = {"status": "pending", "scheduled_at": {"$lt": today_start}}
    if user_match:
        overdue_fu_query.update(user_match)
    overdue_fu_count = await follow_ups_col.count_documents(overdue_fu_query)

    overdue_task_query = {"status": "pending", "due_date": {"$lt": today_start}}
    if _is_sales_person(current_user):
        overdue_task_query["assigned_to"] = current_user["id"]
    overdue_tasks_count = await crm_tasks_col.count_documents(overdue_task_query)

    # 9. Leads Assigned Today
    today_dt_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    assigned_today_query: Dict[str, Any] = {
        "$or": [
            {"assigned_at": {"$gte": today_dt_start}},
            {"assigned_at": {"$gte": today_start}}
        ]
    }
    if user_match:
        assigned_today_query.update(user_match)
    assigned_today_count = await leads_col.count_documents(assigned_today_query)

    return {
        "calls_due": calls_due_count,
        "follow_ups_due": fu_due_count,
        "whatsapp_replies": whatsapp_replies_count,
        "emails_pending": emails_pending_count,
        "payment_followups": payment_fu_count,
        "documents_pending": docs_pending_count,
        "meetings_today": meetings_today_count,
        "overdue_actions": total_overdue,
        "assigned_today": assigned_today_count,
        "breakdown": {
            "overdue_followups": overdue_fu_count,
            "overdue_tasks": overdue_tasks_count
        }
    }


# ────────────────────────────────────────────────────────────
# 2. DEALS & PIPELINE MODULE
# ────────────────────────────────────────────────────────────

PIPELINE_STAGES = [
    {"key": "new", "label": "New", "probability": 10},
    {"key": "contacted", "label": "Contacted", "probability": 25},
    {"key": "qualified", "label": "Qualified", "probability": 40},
    {"key": "assessment", "label": "Assessment", "probability": 55},
    {"key": "proposal", "label": "Proposal", "probability": 70},
    {"key": "negotiation", "label": "Negotiation", "probability": 85},
    {"key": "payment_pending", "label": "Payment Pending", "probability": 90},
    {"key": "won", "label": "Won", "probability": 100},
    {"key": "lost", "label": "Lost", "probability": 0}
]

@router.post("/deals")
async def create_deal(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Create a new sales deal in the pipeline"""
    lead_id = data.get("lead_id")
    client_id = data.get("client_id")
    client_name = data.get("client_name", "")
    if lead_id and not client_name:
        lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1, "service_interested": 1, "country_of_interest": 1})
        if lead:
            client_name = lead.get("name", "")
            data.setdefault("service", lead.get("service_interested", "Immigration Consulting"))
            data.setdefault("country", lead.get("country_of_interest", "Canada"))

    stage = data.get("stage", "new")
    stage_match = next((s for s in PIPELINE_STAGES if s["key"] == stage), None)
    probability = data.get("probability", stage_match["probability"] if stage_match else 20)

    deal_doc = {
        "id": str(uuid.uuid4()),
        "deal_name": data.get("deal_name") or f"Deal - {client_name}",
        "lead_id": lead_id,
        "client_id": client_id,
        "client_name": client_name,
        "service": data.get("service", "Immigration Consulting"),
        "country": data.get("country", "Canada"),
        "deal_value": float(data.get("deal_value", 0)),
        "discount": float(data.get("discount", 0)),
        "final_amount": float(data.get("final_amount", data.get("deal_value", 0))),
        "probability": probability,
        "stage": stage,  # new, contacted, qualified, assessment, proposal, negotiation, payment_pending, won, lost
        "priority": data.get("priority", "medium"),
        "next_follow_up": data.get("next_follow_up"),
        "sales_person_id": data.get("sales_person_id") or current_user["id"],
        "sales_person_name": data.get("sales_person_name") or current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "closed_at": datetime.now(timezone.utc) if stage in ["won", "lost"] else None
    }
    await crm_deals_col.insert_one(deal_doc)

    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action="deal_created",
        entity_type="deal",
        entity_id=deal_doc["id"],
        details=f"Deal '{deal_doc['deal_name']}' created (Value: ₹{deal_doc['deal_value']}, Stage: {stage})"
    )

    return {"message": "Deal created successfully", "deal_id": deal_doc["id"]}


@router.get("/deals")
async def get_deals(
    stage: Optional[str] = Query(None),
    lead_id: Optional[str] = Query(None),
    sales_person_id: Optional[str] = Query(None),
    limit: int = Query(200),
    current_user: dict = Depends(get_current_user)
):
    """Get all deals with role filtering"""
    query: Dict[str, Any] = {}
    if stage:
        query["stage"] = stage
    if lead_id:
        query["lead_id"] = lead_id
    if _is_sales_person(current_user):
        query["sales_person_id"] = current_user["id"]
    elif sales_person_id and _is_manager_or_admin(current_user):
        query["sales_person_id"] = sales_person_id

    deals = await crm_deals_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    for d in deals:
        for f in ["created_at", "updated_at", "closed_at"]:
            if isinstance(d.get(f), datetime):
                d[f] = d[f].isoformat()
    return deals


@router.put("/deals/{deal_id}/stage")
async def update_deal_stage(deal_id: str, data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Move deal to another pipeline stage"""
    new_stage = data.get("stage")
    if not new_stage:
        raise HTTPException(status_code=400, detail="Stage is required")
    
    deal = await crm_deals_col.find_one({"id": deal_id}, {"_id": 0})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    stage_match = next((s for s in PIPELINE_STAGES if s["key"] == new_stage), None)
    updates: Dict[str, Any] = {
        "stage": new_stage,
        "updated_at": datetime.now(timezone.utc)
    }
    if stage_match:
        updates["probability"] = stage_match["probability"]
    if new_stage in ["won", "closed_won", "lost"]:
        updates["closed_at"] = datetime.now(timezone.utc)
    
    await crm_deals_col.update_one({"id": deal_id}, {"$set": updates})

    # If linked to lead, update lead stage as well
    if deal.get("lead_id"):
        lead_updates = {"stage": new_stage, "updated_at": datetime.now(timezone.utc)}
        if new_stage in ["won", "closed_won"]:
            lead_updates["converted"] = True
            lead_updates["converted_at"] = datetime.now(timezone.utc)
            lead_updates["closed_at"] = datetime.now(timezone.utc)
        await leads_col.update_one({"id": deal["lead_id"]}, {"$set": lead_updates})

    # Trigger real-time targets recalculation
    try:
        from core.targets_logic import recalc_targets_for_user
        rep_id = deal.get("sales_person_id") or current_user["id"]
        if rep_id:
            await recalc_targets_for_user(rep_id, notify=True)
    except Exception:
        pass

    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action=f"deal_stage_{new_stage}",
        entity_type="deal",
        entity_id=deal_id,
        details=f"Deal '{deal.get('deal_name')}' moved from {deal.get('stage')} to {new_stage}",
        old_value=deal.get("stage"),
        new_value=new_stage
    )

    try:
        from services.salesperson_activity_service import log_salesperson_activity
        lid = deal.get("lead_id")
        lead_info = await leads_col.find_one({"id": lid}, {"_id": 0, "name": 1, "phone": 1, "email": 1}) if lid else None
        c_name = (lead_info.get("name") if lead_info else None) or deal.get("client_name") or deal.get("deal_name") or "Deal"
        sp_name_val = current_user.get("name", "Sales Person")
        old_d_stage = str(deal.get("stage") or "None").replace("_", " ").title()
        new_d_stage = str(new_stage).replace("_", " ").title()
        await log_salesperson_activity(
            db=db,
            salesperson_id=current_user["id"],
            salesperson_name=sp_name_val,
            salesperson_email=current_user.get("email"),
            salesperson_role=current_user.get("rbac_role") or current_user.get("role"),
            activity_type="stage_change",
            client_id=lid or deal_id,
            client_name=c_name,
            client_phone=lead_info.get("phone") if lead_info else None,
            client_email=lead_info.get("email") if lead_info else None,
            title=f"Deal Stage: {old_d_stage} → {new_d_stage} - {c_name}",
            details=f"Deal moved from '{old_d_stage}' to '{new_d_stage}' by {sp_name_val}",
            metadata={
                "previous_stage": deal.get("stage"),
                "new_stage": new_stage,
                "old_stage": deal.get("stage"),
                "deal_id": deal_id,
                "lead_id": lid
            }
        )
    except Exception as e:
        logger.warning(f"Error logging deal stage change to salesperson activity: {e}")

    return {"message": f"Deal stage updated to {new_stage}"}


# ────────────────────────────────────────────────────────────
# 3. CRM PAYMENTS MODULE
# ────────────────────────────────────────────────────────────

@router.post("/payments")
async def record_crm_payment(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Record a sales payment against lead or deal"""
    lead_id = data.get("lead_id")
    deal_id = data.get("deal_id")
    client_id = data.get("client_id")
    
    package_price = float(data.get("package_price", 0))
    discount = float(data.get("discount", 0))
    final_amount = float(data.get("final_amount", package_price - discount))
    paid_amount = float(data.get("paid_amount", 0))
    pending_amount = max(0.0, final_amount - paid_amount)
    
    payment_status = "paid" if pending_amount == 0 and paid_amount > 0 else "partially_paid" if paid_amount > 0 else "pending"

    client_name = data.get("client_name", "")
    if lead_id and not client_name:
        lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1})
        if lead:
            client_name = lead.get("name", "")

    payment_doc = {
        "id": str(uuid.uuid4()),
        "receipt_number": f"RCP-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}",
        "lead_id": lead_id,
        "deal_id": deal_id,
        "client_id": client_id,
        "client_name": client_name,
        "sales_person_id": current_user["id"],
        "sales_person_name": current_user.get("name", ""),
        "package_name": data.get("package_name", "Standard Consulting Package"),
        "package_price": package_price,
        "discount": discount,
        "final_amount": final_amount,
        "paid_amount": paid_amount,
        "pending_amount": pending_amount,
        "payment_method": data.get("payment_method", "Bank Transfer"),  # Bank Transfer, UPI, Credit Card, Razorpay, Cash
        "transaction_id": data.get("transaction_id", f"TXN-{uuid.uuid4().hex[:8].upper()}"),
        "payment_date": data.get("payment_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "payment_status": payment_status,  # pending, partially_paid, paid, failed, refunded
        "notes": data.get("notes", ""),
        "created_at": datetime.now(timezone.utc)
    }
    await crm_payments_col.insert_one(payment_doc)

    # Sync with deal & lead
    if deal_id:
        await crm_deals_col.update_one({"id": deal_id}, {"$set": {
            "paid_amount": paid_amount,
            "pending_amount": pending_amount,
            "stage": "won" if payment_status == "paid" else "payment_pending",
            "updated_at": datetime.now(timezone.utc)
        }})
    if lead_id:
        await leads_col.update_one({"id": lead_id}, {"$set": {
            "stage": "payment_received" if payment_status == "paid" else "payment_pending",
            "payment_status": payment_status,
            "paid_amount": paid_amount,
            "pending_amount": pending_amount,
            "updated_at": datetime.now(timezone.utc)
        }})

    # Activity log
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action="payment_received",
        entity_type="payment",
        entity_id=payment_doc["id"],
        details=f"Payment of ₹{paid_amount} recorded for {client_name} (Status: {payment_status}, Txn: {payment_doc['transaction_id']})"
    )

    # Real-time target recalculation for payments/revenue
    try:
        from core.targets_logic import recalc_targets_for_user
        await recalc_targets_for_user(current_user["id"], notify=True)
    except Exception:
        pass

    # Automatic salesperson commission calculation
    try:
        from core.commission_logic import apply_commission_for_crm_payment
        await apply_commission_for_crm_payment(payment_doc)
    except Exception as _ce:
        pass

    return {"message": "Payment recorded successfully", "payment": payment_doc}


@router.get("/payments")
async def get_crm_payments(
    lead_id: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    limit: int = Query(100),
    current_user: dict = Depends(get_current_user)
):
    """List CRM payments with role filtering"""
    query: Dict[str, Any] = {}
    if lead_id:
        query["lead_id"] = lead_id
    if payment_status:
        query["payment_status"] = payment_status
    if _is_sales_person(current_user):
        query["sales_person_id"] = current_user["id"]

    payments = await crm_payments_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    for p in payments:
        if isinstance(p.get("created_at"), datetime):
            p["created_at"] = p["created_at"].isoformat()
    return payments


# ────────────────────────────────────────────────────────────
# 4. CAMPAIGN MANAGEMENT
# ────────────────────────────────────────────────────────────

@router.get("/campaigns")
async def get_campaigns(current_user: dict = Depends(get_current_user)):
    """List marketing campaigns with performance and ROI stats"""
    campaigns = await crm_campaigns_col.find({}, {"_id": 0}).sort("start_date", -1).to_list(100)
    
    # If no campaigns exist, seed default initial campaigns
    if not campaigns:
        defaults = [
            {
                "id": str(uuid.uuid4()),
                "name": "Independence Day Special Offer",
                "source": "Meta Ads",
                "budget": 50000,
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
                "status": "completed",
                "target_country": "Canada",
                "target_service": "PR Express Entry"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Navratri Festival Immigration Drive",
                "source": "Google Search",
                "budget": 75000,
                "start_date": "2026-09-01",
                "end_date": "2026-10-15",
                "status": "active",
                "target_country": "Australia",
                "target_service": "Skilled Migration"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Study Abroad Winter Intake 2026",
                "source": "Instagram / YouTube",
                "budget": 40000,
                "start_date": "2026-08-15",
                "end_date": "2026-11-30",
                "status": "active",
                "target_country": "UK",
                "target_service": "Student Visa"
            }
        ]
        for c in defaults:
            c["created_at"] = datetime.now(timezone.utc)
            await crm_campaigns_col.insert_one(c)
        campaigns = defaults

    # Enrich with live lead counts & conversions
    for c in campaigns:
        c_name = c["name"]
        total_leads = await leads_col.count_documents({"campaign": c_name})
        qualified = await leads_col.count_documents({"campaign": c_name, "stage": {"$in": ["qualified", "assessment", "proposal", "won", "converted"]}})
        converted = await leads_col.count_documents({"campaign": c_name, "stage": {"$in": ["won", "converted"]}})
        
        c["lead_count"] = total_leads
        c["qualified_leads"] = qualified
        c["converted_leads"] = converted
        c["conversion_rate"] = round((converted / total_leads * 100) if total_leads > 0 else 0.0, 1)
        c["revenue"] = converted * 65000  # estimated / actual revenue
        if isinstance(c.get("created_at"), datetime):
            c["created_at"] = c["created_at"].isoformat()

    return campaigns


@router.post("/campaigns")
async def create_campaign(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Create a new campaign (Admin/Manager)"""
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin or Manager access required")

    camp_doc = {
        "id": str(uuid.uuid4()),
        "name": data.get("name"),
        "source": data.get("source", "Google Ads"),
        "budget": float(data.get("budget", 0)),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "status": data.get("status", "active"),
        "target_country": data.get("target_country", "All"),
        "target_service": data.get("target_service", "All"),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }
    await crm_campaigns_col.insert_one(camp_doc)
    return {"message": "Campaign created", "campaign": camp_doc}


# ────────────────────────────────────────────────────────────
# 5. REPORTS & SALESPERSON PERFORMANCE
# ────────────────────────────────────────────────────────────

@router.get("/reports/performance")
async def get_sales_performance_report(
    sales_person_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed salesperson performance metrics:
    - Leads assigned
    - Leads contacted
    - Connected calls & duration
    - WhatsApp messages sent
    - Emails sent
    - Follow-ups completed & overdue
    - Deals won & lost
    - Total Revenue generated
    - Conversion Rate %
    """
    target_user_id = current_user["id"] if _is_sales_person(current_user) else (sales_person_id or current_user["id"])
    target_user = await users_col.find_one({"id": target_user_id}, {"_id": 0, "name": 1, "email": 1, "role": 1})

    # 1. Leads
    leads_assigned = await leads_col.count_documents({"assigned_to": target_user_id})
    leads_contacted = await leads_col.count_documents({"assigned_to": target_user_id, "last_contacted_at": {"$ne": None}})
    leads_qualified = await leads_col.count_documents({"assigned_to": target_user_id, "stage": {"$in": ["qualified", "assessment", "proposal", "won", "converted"]}})
    leads_won = await leads_col.count_documents({"assigned_to": target_user_id, "stage": {"$in": ["won", "converted"]}})
    leads_lost = await leads_col.count_documents({"assigned_to": target_user_id, "stage": {"$in": ["not_interested", "lost", "not_eligible"]}})

    # 2. Calls
    calls_total = await crm_calls_col.count_documents({"sales_person_id": target_user_id})
    calls_connected = await crm_calls_col.count_documents({"sales_person_id": target_user_id, "status": "connected"})
    call_duration_pipeline = [
        {"$match": {"sales_person_id": target_user_id}},
        {"$group": {"_id": None, "total_duration": {"$sum": "$duration_seconds"}}}
    ]
    duration_res = await crm_calls_col.aggregate(call_duration_pipeline).to_list(1)
    total_call_seconds = duration_res[0]["total_duration"] if duration_res else 0

    # 3. WhatsApp & Emails
    wa_count = await crm_whatsapp_col.count_documents({"sales_person_id": target_user_id, "direction": "outbound"})
    email_count = await crm_emails_col.count_documents({"sales_person_id": target_user_id})

    # 4. Follow-ups
    fu_completed = await follow_ups_col.count_documents({"assigned_to": target_user_id, "status": "completed"})
    now_utc = datetime.now(timezone.utc).isoformat()
    fu_overdue = await follow_ups_col.count_documents({"assigned_to": target_user_id, "status": "pending", "scheduled_at": {"$lt": now_utc}})

    # 5. Deals & Revenue
    deals_won = await crm_deals_col.count_documents({"sales_person_id": target_user_id, "stage": "won"})
    deals_lost = await crm_deals_col.count_documents({"sales_person_id": target_user_id, "stage": "lost"})
    
    rev_pipeline = [
        {"$match": {"sales_person_id": target_user_id, "payment_status": "paid"}},
        {"$group": {"_id": None, "total_revenue": {"$sum": "$paid_amount"}}}
    ]
    rev_res = await crm_payments_col.aggregate(rev_pipeline).to_list(1)
    total_revenue = rev_res[0]["total_revenue"] if rev_res else (deals_won * 50000.0)

    conversion_rate = round((leads_won / leads_assigned * 100) if leads_assigned > 0 else 0.0, 1)

    return {
        "sales_person_id": target_user_id,
        "sales_person_name": target_user.get("name", "Sales Executive") if target_user else "Sales Executive",
        "leads_assigned": leads_assigned,
        "leads_contacted": leads_contacted,
        "leads_qualified": leads_qualified,
        "connected_calls": calls_connected,
        "total_calls": calls_total,
        "total_call_duration_minutes": round(total_call_seconds / 60, 1),
        "whatsapp_messages_sent": wa_count,
        "emails_sent": email_count,
        "follow_ups_completed": fu_completed,
        "overdue_follow_ups": fu_overdue,
        "deals_won": deals_won or leads_won,
        "deals_lost": deals_lost or leads_lost,
        "total_revenue": total_revenue,
        "conversion_rate": conversion_rate
    }


# ────────────────────────────────────────────────────────────
# 6. AUTOMATION & SLA MANAGEMENT
# ────────────────────────────────────────────────────────────

@router.get("/automation/rules")
async def get_automation_rules(current_user: dict = Depends(get_current_user)):
    """Get automation and SLA routing rules"""
    rules = await crm_automation_rules_col.find({}, {"_id": 0}).to_list(50)
    if not rules:
        default_rules = [
            {
                "id": "rule_canada_auto_assign",
                "name": "Canada Leads Auto-Assignment",
                "condition": "Country = Canada",
                "action": "Assign to Canada Sales Team & Create Call Task",
                "enabled": True,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "id": "rule_sla_15min_contact",
                "name": "New Lead 15-Minute SLA",
                "condition": "New Lead uncontacted after 15 mins",
                "action": "Trigger Overdue Notification & Escalation to Sales Manager",
                "enabled": True,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "id": "rule_payment_handover_trigger",
                "name": "Full Payment Case Handover Trigger",
                "condition": "Payment Status = Paid (100%)",
                "action": "Auto-notify Admin and enable 1-Click Case Manager Handover",
                "enabled": True,
                "created_at": datetime.now(timezone.utc)
            }
        ]
        for r in default_rules:
            await crm_automation_rules_col.insert_one(r)
        rules = default_rules

    for r in rules:
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
    return rules


# ────────────────────────────────────────────────────────────
# 7. IMMUTABLE AUDIT LOGS
# ────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_crm_audit_logs(
    entity_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve immutable CRM audit trail"""
    query: Dict[str, Any] = {}
    if entity_id:
        query["entity_id"] = entity_id
    if action:
        query["action"] = action
    if _is_sales_person(current_user):
        query["user_id"] = current_user["id"]

    logs = await audit_logs_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    for l in logs:
        if isinstance(l.get("created_at"), datetime):
            l["created_at"] = l["created_at"].isoformat()
    return logs


# ────────────────────────────────────────────────────────────
# 8. ADMIN SALES PERSON OVERVIEW & COMPLETE WORK MONITORING
# ────────────────────────────────────────────────────────────

@router.get("/sales-reps/overview")
async def get_sales_reps_overview(
    salesperson_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Admin-level complete overview of all sales persons with their full performance metrics:
    - separated by internal salespersons and external salespersons / partners
    - total assigned clients (including existing clients, new leads, and block section assignments)
    - today's calls & total calls (with duration)
    - emails, WhatsApp, and total interactions
    - pending & completed follow-ups
    - meetings (scheduled & completed)
    - converted clients & lost clients
    - pending payments & revenue collected
    - overall conversion status & rate
    """
    # If not admin or manager, only include the salesperson themselves
    is_admin_mgr = _is_manager_or_admin(current_user)
    if not is_admin_mgr and not _is_sales_person(current_user):
        raise HTTPException(status_code=403, detail="Admin or Sales access required")

    # Fetch all sales users and admins (excluding client role / client user_type)
    sales_roles = [
        "admin", "admin_owner",
        "sales_head", "sales_manager", "sr_sales_executive", "senior_sales_executive",
        "sales_executive", "sales_person", "sales_agent", "sales_rep", "sales",
        "partner", "external_partner"
    ]
    sales_users = await users_col.find({
        "$and": [
            {"role": {"$ne": "client"}},
            {"user_type": {"$ne": "client"}},
            {
                "$or": [
                    {"role": {"$in": sales_roles}},
                    {"rbac_role": {"$in": sales_roles}},
                    {"department": "sales"},
                    {"role": "partner"},
                    {"user_type": "external"}
                ]
            }
        ]
    }, {"_id": 0, "password": 0}).to_list(200)

    # Also find any other user IDs that have leads assigned to them (excluding clients)
    assigned_ids = await leads_col.distinct("assigned_to")
    existing_ids = {u["id"] for u in sales_users if "id" in u}
    extra_ids = [aid for aid in assigned_ids if aid and aid not in existing_ids]

    if extra_ids:
        extra_users = await users_col.find({"id": {"$in": extra_ids}}, {"_id": 0, "password": 0}).to_list(100)
        sales_users.extend([u for u in extra_users if u.get("role") != "client" and u.get("user_type") != "client"])

    if not is_admin_mgr:
        uid_me = current_user.get("id")
        sales_users = [u for u in sales_users if u.get("id") == uid_me] or [current_user]

    # Date ranges for "today"
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_iso = today_start.isoformat()
    today_date_str = now.strftime("%Y-%m-%d")

    results = []

    for rep in sales_users:
        uid = rep.get("id")
        if not uid:
            continue

        uemail = rep.get("email")
        uname = rep.get("name")

        # Classification: External vs Internal
        is_external = (
            rep.get("user_type") == "external"
            or "partner" in str(rep.get("role", "")).lower()
            or "partner" in str(rep.get("rbac_role", "")).lower()
            or rep.get("is_external") is True
        )
        rep_type = "external" if is_external else "internal"

        # 1. Leads / Clients: include new leads, created by leads, manager assigned, partner assigned, existing converted clients, and block section assignments
        lead_or_conds = [
            {"assigned_to": uid},
            {"assigned_sales_rep_id": uid},
            {"sales_person_id": uid},
            {"created_by": uid},
            {"assigned_manager_id": uid},
            {"partner_id": uid},
            {"block_assigned_to": uid}
        ]
        if uemail:
            lead_or_conds.append({"assigned_to": uemail})
        if uname:
            lead_or_conds.append({"assigned_to_name": uname})
            lead_or_conds.append({"created_by_name": uname})

        assigned_leads = await leads_col.find({"$or": lead_or_conds}, {"_id": 0}).to_list(2000)
        lead_ids_set = {l.get("id") for l in assigned_leads if l.get("id")}

        # Existing clients from cases_col
        extra_cases = await cases_col.find({
            "$or": [{"assigned_to": uid}, {"sales_person_id": uid}, {"created_by": uid}]
        }, {"_id": 0}).to_list(500)
        unique_extra_cases = [c for c in extra_cases if c.get("lead_id") not in lead_ids_set and c.get("id") not in lead_ids_set]

        # Converted clients from users_col
        user_clients = await users_col.find({
            "role": "client",
            "$or": [{"assigned_sales_person_id": uid}, {"assigned_to": uid}]
        }, {"_id": 0, "password": 0}).to_list(500)
        unique_user_clients = [uc for uc in user_clients if uc.get("original_lead_id") not in lead_ids_set and uc.get("id") not in lead_ids_set]

        total_assigned = len(assigned_leads) + len(unique_extra_cases) + len(unique_user_clients)

        # Contacted leads (either last_contacted_at is set, or stage != 'new', or logged in calls/messages)
        contacted_leads = [l for l in assigned_leads if l.get("last_contacted_at") or l.get("stage") not in ["new", None]]
        total_contacted = len(contacted_leads) + len(unique_extra_cases)

        # 2. Calls
        rep_calls = await crm_calls_col.find({"$or": [{"sales_person_id": uid}, {"created_by": uid}]}, {"_id": 0}).to_list(2000)
        total_calls = len(rep_calls)
        
        today_calls = 0
        total_call_seconds = 0
        for c in rep_calls:
            dur = c.get("duration_seconds") or 0
            total_call_seconds += int(dur)
            c_time = c.get("created_at") or c.get("timestamp")
            if isinstance(c_time, datetime) and c_time >= today_start:
                today_calls += 1
            elif isinstance(c_time, str) and (c_time.startswith(today_date_str) or c_time >= today_start_iso):
                today_calls += 1

        # 3. WhatsApp Messages & Emails
        wa_count = await crm_whatsapp_col.count_documents({"$or": [{"sales_person_id": uid}, {"created_by": uid}]})
        email_count = await crm_emails_col.count_documents({"$or": [{"sales_person_id": uid}, {"created_by": uid}]})

        # 4. Follow-ups
        rep_followups = await follow_ups_col.find({"$or": [{"assigned_to": uid}, {"created_by": uid}]}, {"_id": 0}).to_list(1000)
        pending_followups = sum(1 for f in rep_followups if f.get("status") == "pending")
        completed_followups = sum(1 for f in rep_followups if f.get("status") == "completed")

        # 5. Meetings
        rep_meetings = await crm_meetings_col.find({"$or": [{"sales_person_id": uid}, {"created_by": uid}]}, {"_id": 0}).to_list(500)
        meetings_count = len(rep_meetings)

        # 6. Converted vs Lost Clients
        converted_clients = sum(1 for l in assigned_leads if l.get("stage") in ["won", "closed_won", "converted", "payment_received", "case_created"] or l.get("converted") is True) + len(unique_extra_cases) + len(unique_user_clients)
        lost_clients = sum(1 for l in assigned_leads if l.get("stage") in ["lost", "not_interested", "not_eligible", "archived", "closed_lost"])
        in_pipeline = max(0, total_assigned - (converted_clients + lost_clients))

        # 7. Payments & Revenue
        pending_payments_count = 0
        pending_payments_amount = 0.0
        collected_payments_amount = 0.0

        for l in assigned_leads:
            p_amt = float(l.get("pending_amount", 0) or 0)
            paid_amt = float(l.get("paid_amount", 0) or 0)
            if p_amt > 0 or l.get("payment_status") in ["pending", "partially_paid"]:
                pending_payments_count += 1
                pending_payments_amount += p_amt
            collected_payments_amount += paid_amt

        # Also aggregate from crm_payments_col
        recorded_payments = await crm_payments_col.find({"sales_person_id": uid}, {"_id": 0}).to_list(500)
        if recorded_payments:
            rec_collected = sum(float(p.get("paid_amount", 0) or 0) for p in recorded_payments if p.get("payment_status") in ["paid", "partially_paid"])
            if rec_collected > collected_payments_amount:
                collected_payments_amount = rec_collected

        # 8. Conversion Rate & Status
        conversion_rate = round((converted_clients / total_assigned * 100) if total_assigned > 0 else 0.0, 1)
        
        conversion_status = "Excellent" if conversion_rate >= 30 else "Good" if conversion_rate >= 15 else "Moderate" if conversion_rate >= 5 else "Needs Attention" if total_assigned > 0 else "New Rep"

        total_interactions = total_calls + wa_count + email_count + meetings_count

        # Latest activity
        last_activity = None
        for item_list in [rep_calls, rep_followups, rep_meetings]:
            for item in item_list:
                t = item.get("created_at") or item.get("timestamp") or item.get("updated_at")
                if t:
                    if isinstance(t, datetime):
                        t_iso = t.isoformat()
                    else:
                        t_iso = str(t)
                    if not last_activity or t_iso > last_activity:
                        last_activity = t_iso

        role_key = rep.get("rbac_role") or rep.get("role") or "sales_executive"
        role_label = ROLE_LABELS.get(role_key, role_key.replace("_", " ").title())
        role_desc = ROLE_DESCRIPTIONS.get(role_key, "Sales representative")
        designation = rep.get("designation") or role_label

        results.append({
            "id": uid,
            "name": rep.get("name") or rep.get("email", "Unknown"),
            "email": rep.get("email", ""),
            "role": role_key,
            "role_label": role_label,
            "designation": designation,
            "role_description": role_desc,
            "department": rep.get("department", "sales"),
            "mobile": rep.get("mobile", ""),
            "salesperson_type": rep_type,
            "is_external": is_external,
            "total_assigned_clients": total_assigned,
            "total_clients_contacted": total_contacted,
            "contact_rate": round((total_contacted / total_assigned * 100) if total_assigned > 0 else 0.0, 1),
            "today_calls": today_calls,
            "total_calls": total_calls,
            "total_call_duration_minutes": round(total_call_seconds / 60, 1),
            "whatsapp_messages": wa_count,
            "emails_count": email_count,
            "total_interactions": total_interactions,
            "pending_followups": pending_followups,
            "completed_followups": completed_followups,
            "meetings_count": meetings_count,
            "converted_clients": converted_clients,
            "lost_clients": lost_clients,
            "in_pipeline_clients": in_pipeline,
            "pending_payments_count": pending_payments_count,
            "pending_payments_amount": round(pending_payments_amount, 2),
            "collected_payments_amount": round(collected_payments_amount, 2),
            "conversion_rate": conversion_rate,
            "conversion_status": conversion_status,
            "last_activity": last_activity or rep.get("created_at")
        })

    # Sort by total assigned clients
    results.sort(key=lambda x: (x["total_assigned_clients"], x["today_calls"], x["converted_clients"]), reverse=True)

    internal_reps = [r for r in results if r["salesperson_type"] == "internal"]
    external_reps = [r for r in results if r["salesperson_type"] == "external"]

    # Summary metrics across whole team
    team_summary = {
        "total_sales_persons": len(results),
        "total_internal": len(internal_reps),
        "total_external": len(external_reps),
        "total_assigned_clients": sum(r["total_assigned_clients"] for r in results),
        "internal_assigned_clients": sum(r["total_assigned_clients"] for r in internal_reps),
        "external_assigned_clients": sum(r["total_assigned_clients"] for r in external_reps),
        "total_clients_contacted": sum(r["total_clients_contacted"] for r in results),
        "total_today_calls": sum(r["today_calls"] for r in results),
        "total_calls": sum(r["total_calls"] for r in results),
        "total_whatsapp_messages": sum(r["whatsapp_messages"] for r in results),
        "total_emails": sum(r["emails_count"] for r in results),
        "total_pending_followups": sum(r["pending_followups"] for r in results),
        "total_completed_followups": sum(r["completed_followups"] for r in results),
        "total_converted_clients": sum(r["converted_clients"] for r in results),
        "total_lost_clients": sum(r["lost_clients"] for r in results),
        "total_pending_payments_amount": sum(r["pending_payments_amount"] for r in results),
        "total_collected_payments_amount": sum(r["collected_payments_amount"] for r in results),
        "team_conversion_rate": round(
            (sum(r["converted_clients"] for r in results) / sum(r["total_assigned_clients"] for r in results) * 100)
            if sum(r["total_assigned_clients"] for r in results) > 0 else 0.0, 1
        )
    }

    filtered_sales_reps = results
    if salesperson_type and salesperson_type in ["internal", "external"]:
        filtered_sales_reps = [r for r in results if r["salesperson_type"] == salesperson_type]

    return {
        "team_summary": team_summary,
        "sales_reps": filtered_sales_reps
    }


@router.get("/sales-reps/{sales_person_id}/detail")
async def get_sales_rep_full_detail(
    sales_person_id: str,
    client_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Admin-level complete client-wise activity history and workflow drilldown for a specific Sales Person.
    Includes:
    - Sales person profile & overview metrics
    - Complete assigned clients list with client-specific stats and stages
    - Complete chronological timeline of all activities (calls with recordings, WhatsApp, emails, follow-ups, meetings, conversions)
    """
    if not _is_manager_or_admin(current_user) and current_user.get("id") != sales_person_id:
        raise HTTPException(status_code=403, detail="Admin, Manager, or Sales Person self-access required")

    rep_user = await users_col.find_one({"id": sales_person_id}, {"_id": 0, "password": 0})
    if not rep_user:
        raise HTTPException(status_code=404, detail="Sales person not found")

    is_external = (
        rep_user.get("user_type") == "external"
        or "partner" in str(rep_user.get("role", "")).lower()
        or "partner" in str(rep_user.get("rbac_role", "")).lower()
        or rep_user.get("is_external") is True
    )
    rep_type = "external" if is_external else "internal"

    # Fetch all leads assigned to this rep (including block section assignments, created_by, manager_assigned, partner_assigned, and existing clients)
    rep_lead_or = [
        {"assigned_to": sales_person_id},
        {"assigned_sales_rep_id": sales_person_id},
        {"sales_person_id": sales_person_id},
        {"created_by": sales_person_id},
        {"assigned_manager_id": sales_person_id},
        {"partner_id": sales_person_id},
        {"block_assigned_to": sales_person_id}
    ]
    if rep_user.get("email"):
        rep_lead_or.append({"assigned_to": rep_user.get("email")})
    if rep_user.get("name"):
        rep_lead_or.append({"assigned_to_name": rep_user.get("name")})
        rep_lead_or.append({"created_by_name": rep_user.get("name")})

    if client_id and isinstance(client_id, str):
        lead_query = {"$and": [{"id": client_id}, {"$or": rep_lead_or}]}
    else:
        lead_query = {"$or": rep_lead_or}

    assigned_leads = await leads_col.find(lead_query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    # Also include existing clients from cases_col if not already present
    lead_ids_set = {l.get("id") for l in assigned_leads if l.get("id")}
    case_query = {"$or": [{"assigned_to": sales_person_id}, {"sales_person_id": sales_person_id}, {"created_by": sales_person_id}]}
    if client_id and isinstance(client_id, str):
        case_query = {"$and": [{"$or": [{"id": client_id}, {"lead_id": client_id}]}, case_query]}
    extra_cases = await cases_col.find(case_query, {"_id": 0}).to_list(500)
    for c in extra_cases:
        cid = c.get("lead_id") or c.get("id")
        if cid not in lead_ids_set:
            assigned_leads.append({
                "id": cid,
                "name": c.get("client_name") or c.get("name") or "Existing Client",
                "email": c.get("client_email") or c.get("email") or "",
                "phone": c.get("client_phone") or c.get("phone") or "",
                "country_of_interest": c.get("country") or "Canada",
                "service_interested": c.get("service") or c.get("case_type") or "Immigration",
                "stage": c.get("status") or "converted",
                "status": c.get("status") or "converted",
                "converted": True,
                "source": "Existing Client",
                "lead_score": 90,
                "priority": "high",
                "created_at": c.get("created_at")
            })
            lead_ids_set.add(cid)

    # Also include clients directly from users_col assigned to this sales person
    user_clients_query = {
        "$and": [
            {
                "$or": [
                    {"role": "client"},
                    {"rbac_role": "client"},
                    {"user_type": "client"},
                    {"client_portal_status": "activated"}
                ]
            },
            {
                "$or": [
                    {"assigned_sales_person_id": sales_person_id},
                    {"assigned_sales_rep_id": sales_person_id},
                    {"sales_person_id": sales_person_id}
                ]
            }
        ]
    }
    if client_id and isinstance(client_id, str):
        user_clients_query["$and"].append({"$or": [{"id": client_id}, {"lead_id": client_id}]})
    extra_user_clients = await users_col.find(user_clients_query, {"_id": 0, "password": 0}).to_list(500)
    for uc in extra_user_clients:
        ucid = uc.get("lead_id") or uc.get("id")
        if ucid not in lead_ids_set:
            assigned_leads.append({
                "id": ucid,
                "name": uc.get("name") or uc.get("client_name") or "Converted Client",
                "email": uc.get("email") or "",
                "phone": uc.get("phone") or uc.get("mobile") or "",
                "country_of_interest": uc.get("country_of_interest") or uc.get("country") or "Canada",
                "service_interested": uc.get("service_interested") or "Immigration",
                "stage": "converted",
                "status": "converted",
                "converted": True,
                "source": uc.get("source") or "Converted Client",
                "lead_score": 100,
                "priority": "high",
                "created_at": uc.get("created_at")
            })
            lead_ids_set.add(ucid)

    # Lead ID mapping for quick lookup
    lead_map = {l["id"]: l for l in assigned_leads if "id" in l}

    # Fetch all client-wise activities for this sales person
    # 1. Calls
    call_query = {"$or": [{"sales_person_id": sales_person_id}, {"created_by": sales_person_id}]}
    if client_id and isinstance(client_id, str):
        call_query["lead_id"] = client_id
    raw_calls = await crm_calls_col.find(call_query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    # 2. WhatsApp
    wa_query = {"$or": [{"sales_person_id": sales_person_id}, {"created_by": sales_person_id}]}
    if client_id and isinstance(client_id, str):
        wa_query["lead_id"] = client_id
    raw_wa = await crm_whatsapp_col.find(wa_query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    # 3. Emails
    email_query = {"$or": [{"sales_person_id": sales_person_id}, {"created_by": sales_person_id}]}
    if client_id and isinstance(client_id, str):
        email_query["lead_id"] = client_id
    raw_emails = await crm_emails_col.find(email_query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    # 4. Follow-ups
    fu_query = {"$or": [{"assigned_to": sales_person_id}, {"created_by": sales_person_id}]}
    if client_id and isinstance(client_id, str):
        fu_query["lead_id"] = client_id
    raw_fu = await follow_ups_col.find(fu_query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    # 5. Meetings
    meet_query = {"$or": [{"sales_person_id": sales_person_id}, {"created_by": sales_person_id}]}
    if client_id and isinstance(client_id, str):
        meet_query["lead_id"] = client_id
    raw_meetings = await crm_meetings_col.find(meet_query, {"_id": 0}).sort("created_at", -1).to_list(500)

    # 6. Deals & Payments
    raw_deals = await crm_deals_col.find({"sales_person_id": sales_person_id}, {"_id": 0}).to_list(500)
    raw_payments = await crm_payments_col.find({"sales_person_id": sales_person_id}, {"_id": 0}).to_list(500)

    # Format clients with individual interaction metrics
    clients_list = []
    for l in assigned_leads:
        lid = l.get("id")
        c_calls = [c for c in raw_calls if c.get("lead_id") == lid]
        c_wa = [w for w in raw_wa if w.get("lead_id") == lid]
        c_emails = [e for e in raw_emails if e.get("lead_id") == lid]
        c_fu = [f for f in raw_fu if f.get("lead_id") == lid]

        for date_f in ["created_at", "updated_at", "last_contacted_at"]:
            if isinstance(l.get(date_f), datetime):
                l[date_f] = l[date_f].isoformat()

        source_val = l.get("source")
        tags_list = l.get("tags") or []
        if "general_enquiry" in tags_list or "mysql_general" in str(tags_list):
            source_val = "Website"
        elif "popup_enquiry" in tags_list or "mysql_popup" in str(tags_list):
            source_val = "Website Popup"
        elif not source_val:
            source_val = "Organic"

        clients_list.append({
            "id": lid,
            "name": l.get("name", "Unnamed Client"),
            "email": l.get("email", ""),
            "phone": l.get("phone", ""),
            "country_of_interest": l.get("country_of_interest", "Canada"),
            "service_interested": l.get("service_interested", "Consulting"),
            "stage": l.get("stage", "new"),
            "status": l.get("status") or l.get("stage", "new"),
            "converted": bool(l.get("converted") or l.get("stage") == "converted" or l.get("status") == "converted"),
            "lead_score": l.get("lead_score", 50),
            "priority": l.get("priority", "medium"),
            "source": source_val,
            "campaign": l.get("campaign", ""),
            "paid_amount": float(l.get("paid_amount", 0) or 0),
            "pending_amount": float(l.get("pending_amount", 0) or 0),
            "payment_status": l.get("payment_status", "pending"),
            "total_calls": len(c_calls),
            "total_messages": len(c_wa),
            "total_emails": len(c_emails),
            "total_followups": len(c_fu),
            "last_contacted_at": l.get("last_contacted_at"),
            "created_at": l.get("created_at")
        })

    # Build Unified Unified Activities Stream
    timeline_events = []

    # Add Calls
    for c in raw_calls:
        t = c.get("created_at") or c.get("timestamp") or datetime.now(timezone.utc)
        iso_t = t.isoformat() if isinstance(t, datetime) else str(t)
        lid = c.get("lead_id")
        client_name = c.get("client_name") or (lead_map.get(lid, {}).get("name") if lid else "Client")
        
        timeline_events.append({
            "id": c.get("id") or str(uuid.uuid4()),
            "type": "call",
            "title": f"Call ({c.get('direction', 'outgoing').capitalize()}) with {client_name}",
            "description": c.get("notes") or f"Call completed. Outcome: {c.get('outcome', 'Completed')}",
            "timestamp": iso_t,
            "lead_id": lid,
            "client_name": client_name,
            "direction": c.get("direction", "outgoing"),
            "duration_seconds": c.get("duration_seconds", 0),
            "outcome": c.get("outcome", "connected"),
            "recording_url": c.get("recording_url", ""),
            "notes": c.get("notes", "")
        })

    # Add WhatsApp
    for w in raw_wa:
        t = w.get("created_at") or datetime.now(timezone.utc)
        iso_t = t.isoformat() if isinstance(t, datetime) else str(t)
        lid = w.get("lead_id")
        client_name = w.get("client_name") or (lead_map.get(lid, {}).get("name") if lid else "Client")

        timeline_events.append({
            "id": w.get("id") or str(uuid.uuid4()),
            "type": "whatsapp",
            "title": f"WhatsApp ({w.get('direction', 'outbound').capitalize()}) - {client_name}",
            "description": w.get("text") or w.get("message") or w.get("content") or "WhatsApp message sent",
            "timestamp": iso_t,
            "lead_id": lid,
            "client_name": client_name,
            "direction": w.get("direction", "outbound"),
            "media_url": w.get("media_url")
        })

    # Add Emails
    for e in raw_emails:
        t = e.get("created_at") or e.get("sent_at") or datetime.now(timezone.utc)
        iso_t = t.isoformat() if isinstance(t, datetime) else str(t)
        lid = e.get("lead_id")
        client_name = e.get("client_name") or (lead_map.get(lid, {}).get("name") if lid else "Client")

        timeline_events.append({
            "id": e.get("id") or str(uuid.uuid4()),
            "type": "email",
            "title": f"Email: {e.get('subject', 'Consulting Follow-up')} to {client_name}",
            "description": e.get("body") or e.get("snippet") or "Email communication sent",
            "timestamp": iso_t,
            "lead_id": lid,
            "client_name": client_name,
            "status": e.get("status", "sent")
        })

    # Add Follow-ups
    for f in raw_fu:
        t = f.get("scheduled_at") or f.get("created_at") or datetime.now(timezone.utc)
        iso_t = t.isoformat() if isinstance(t, datetime) else str(t)
        lid = f.get("lead_id")
        client_name = f.get("client_name") or (lead_map.get(lid, {}).get("name") if lid else "Client")

        timeline_events.append({
            "id": f.get("id") or str(uuid.uuid4()),
            "type": "followup",
            "title": f"Follow-up: {f.get('type', 'General')} for {client_name}",
            "description": f.get("notes") or f"Scheduled follow-up (Status: {f.get('status', 'pending')})",
            "timestamp": iso_t,
            "lead_id": lid,
            "client_name": client_name,
            "status": f.get("status", "pending")
        })

    # Add Meetings
    for m in raw_meetings:
        t = m.get("meeting_date") or m.get("created_at") or datetime.now(timezone.utc)
        iso_t = t.isoformat() if isinstance(t, datetime) else str(t)
        lid = m.get("lead_id")
        client_name = m.get("client_name") or (lead_map.get(lid, {}).get("name") if lid else "Client")

        timeline_events.append({
            "id": m.get("id") or str(uuid.uuid4()),
            "type": "meeting",
            "title": f"Meeting: {m.get('title', 'Consultation')} with {client_name}",
            "description": m.get("notes") or f"Meeting scheduled ({m.get('time', '')})",
            "timestamp": iso_t,
            "lead_id": lid,
            "client_name": client_name,
            "status": m.get("status", "scheduled")
        })

    # Add Payments
    for p in raw_payments:
        t = p.get("created_at") or datetime.now(timezone.utc)
        iso_t = t.isoformat() if isinstance(t, datetime) else str(t)
        lid = p.get("lead_id")
        client_name = p.get("client_name") or (lead_map.get(lid, {}).get("name") if lid else "Client")

        timeline_events.append({
            "id": p.get("id") or str(uuid.uuid4()),
            "type": "payment",
            "title": f"Payment Received: ₹{p.get('paid_amount', 0):,} from {client_name}",
            "description": f"Receipt {p.get('receipt_number', '')} | Mode: {p.get('payment_method', 'Bank Transfer')} | Pending: ₹{p.get('pending_amount', 0):,}",
            "timestamp": iso_t,
            "lead_id": lid,
            "client_name": client_name,
            "amount": p.get("paid_amount", 0),
            "pending_amount": p.get("pending_amount", 0),
            "status": p.get("payment_status", "paid")
        })

    # Filter by activity_type if provided
    if activity_type and activity_type != "all":
        timeline_events = [e for e in timeline_events if e["type"] == activity_type]

    # Sort activities chronologically descending
    timeline_events.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)

    role_key = rep_user.get("rbac_role") or rep_user.get("role") or "sales_executive"
    role_label = ROLE_LABELS.get(role_key, role_key.replace("_", " ").title())
    role_desc = ROLE_DESCRIPTIONS.get(role_key, "Sales representative")
    designation = rep_user.get("designation") or role_label

    return {
        "sales_rep": {
            "id": rep_user.get("id"),
            "name": rep_user.get("name", "Sales Representative"),
            "email": rep_user.get("email", ""),
            "role": role_key,
            "role_label": role_label,
            "designation": designation,
            "role_description": role_desc,
            "department": rep_user.get("department", "sales"),
            "mobile": rep_user.get("mobile", ""),
            "salesperson_type": rep_type,
            "is_external": is_external
        },
        "stats": {
            "total_assigned": len(assigned_leads),
            "total_calls": len(raw_calls),
            "total_whatsapp": len(raw_wa),
            "total_emails": len(raw_emails),
            "total_followups": len(raw_fu),
            "total_meetings": len(raw_meetings),
            "total_payments": len(raw_payments)
        },
        "clients": clients_list,
        "activities": timeline_events
    }


# ────────────────────────────────────────────────────────────
# PIPELINE COCKPIT INTEGRATION ENDPOINTS FOR CRM
# ────────────────────────────────────────────────────────────

async def _resolve_crm_lead(lead_id: str) -> Optional[dict]:
    query_conditions = [{"id": lead_id}, {"unique_id": lead_id}, {"lead_number": lead_id}]
    from bson import ObjectId
    if ObjectId.is_valid(lead_id):
        query_conditions.append({"_id": ObjectId(lead_id)})
    return await leads_col.find_one({"$or": query_conditions})


@router.post("/leads/{lead_id}/mark-paid")
async def mark_crm_lead_paid(
    lead_id: str,
    payload: Optional[Dict[str, Any]] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Mark lead as paid in CRM, trigger automated state transition and resume request if needed."""
    if not _is_manager_or_admin(current_user) and not _is_sales_person(current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    from core.navratri_automation import mark_lead_paid_and_transition
    p = payload or {}
    payment_mode = p.get("payment_mode", "upi")
    payment_amount = float(p.get("payment_amount", 2427.0))
    razorpay_payment_id = p.get("razorpay_payment_id")
    razorpay_order_id = p.get("razorpay_order_id")
    trigger_auto_resume = p.get("trigger_auto_resume_request", True)

    try:
        res = await mark_lead_paid_and_transition(
            lead_id=lead_id,
            payment_mode=payment_mode,
            payment_amount=payment_amount,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            trigger_auto_resume_request=trigger_auto_resume
        )
        now = datetime.now(timezone.utc)
        activity_entry = {
            "id": str(uuid.uuid4()),
            "lead_id": lead_id,
            "activity_type": "payment_received",
            "type": "payment_received",
            "title": f"Payment Recorded (₹{payment_amount:,.0f})",
            "description": f"Payment of ₹{payment_amount:,.0f} marked as received via {payment_mode.upper()} by {current_user.get('name')}.",
            "amount": payment_amount,
            "user_id": current_user.get("id"),
            "user_name": current_user.get("name"),
            "timestamp": now.isoformat(),
            "created_at": now.isoformat(),
        }
        await leads_col.update_one(
            {"$or": [{"id": lead_id}, {"unique_id": lead_id}]},
            {"$push": {"timeline": activity_entry}}
        )
        await crm_audit_logs_col.insert_one(activity_entry)
        return {
            "success": True,
            **res,
            "message": f"Payment of ₹{payment_amount:,.0f} successfully recorded."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/leads/{lead_id}/send-payment-link")
async def send_crm_lead_payment_link(
    lead_id: str,
    payload: Optional[Dict[str, Any]] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Dispatches payment link via Email and WhatsApp to the lead and logs CRM activity."""
    from core.navratri_automation import send_navratri_payment_link
    lead = await _resolve_crm_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    p = payload or {}
    payment_url = p.get("payment_url")
    res = await send_navratri_payment_link(lead, payment_url_override=payment_url)
    
    now = datetime.now(timezone.utc)
    activity_entry = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "activity_type": "payment_link_sent",
        "type": "payment_link_sent",
        "title": "Payment Link Dispatched",
        "description": f"Payment link sent via Email ({'✓' if res.get('email_sent') else '✗'}) and WhatsApp ({'✓' if res.get('whatsapp_sent') else '✗'}) by {current_user.get('name')}.",
        "user_id": current_user.get("id"),
        "user_name": current_user.get("name"),
        "timestamp": now.isoformat(),
        "created_at": now.isoformat(),
    }
    await leads_col.update_one(
        {"$or": [{"id": lead_id}, {"unique_id": lead_id}]},
        {"$push": {"timeline": activity_entry}}
    )
    await crm_audit_logs_col.insert_one(activity_entry)
    return {
        "success": True,
        "result": res,
        "message": "Payment link sent successfully via Email and WhatsApp."
    }


@router.post("/leads/{lead_id}/send-resume-request")
async def send_crm_lead_resume_request(
    lead_id: str,
    request: Request,
    payload: Optional[Dict[str, Any]] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Dispatches secure resume upload request via Email and WhatsApp and logs CRM activity."""
    from core.navratri_automation import send_navratri_resume_request
    lead = await _resolve_crm_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    p = payload or {}
    sender_name = current_user.get("name") or "LEAMSS Migration Team"
    client_origin = p.get("base_url") or request.headers.get("origin") or request.headers.get("referer")
    if client_origin:
        client_origin = client_origin.rstrip("/")
        if "/sales" in client_origin or "/crm" in client_origin:
            from urllib.parse import urlparse
            parsed = urlparse(client_origin)
            client_origin = f"{parsed.scheme}://{parsed.netloc}"
    res = await send_navratri_resume_request(lead, sender_name=sender_name, custom_message=p.get("custom_message"), base_url=client_origin)
    
    now = datetime.now(timezone.utc)
    activity_entry = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "activity_type": "resume_request_sent",
        "type": "resume_request_sent",
        "title": "Resume Upload Request Dispatched",
        "description": f"Resume upload request dispatched via Email ({'✓' if res.get('email_sent') else '✗'}) and WhatsApp ({'✓' if res.get('whatsapp_sent') else '✗'}) by {sender_name}.",
        "user_id": current_user.get("id"),
        "user_name": sender_name,
        "timestamp": now.isoformat(),
        "created_at": now.isoformat(),
    }
    await leads_col.update_one(
        {"$or": [{"id": lead_id}, {"unique_id": lead_id}]},
        {"$push": {"timeline": activity_entry}}
    )
    await crm_audit_logs_col.insert_one(activity_entry)
    return {
        "success": True,
        "result": res,
        "message": "Resume upload request dispatched successfully via Email and WhatsApp."
    }


@router.get("/leads/{lead_id}/resume-status")
async def get_crm_lead_resume_status(
    lead_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Checks real-time resume status for a lead, including multi-record candidate synchronization."""
    import re
    from core.resume_service import attach_and_sync_resume
    from core.navratri_automation import has_lead_resume

    lead = await _resolve_crm_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    actual_lead_id = lead.get("id") or str(lead.get("_id"))

    # 1. Check if lead already has direct resume attached
    if has_lead_resume(lead) and lead.get("resume_file_id"):
        return {
            "success": True,
            "has_resume": True,
            "resume_file_id": lead.get("resume_file_id"),
            "resume_filename": lead.get("resume_filename") or "Candidate Resume",
            "resume_url": lead.get("resume_url") or f"/cockpit/resume/{lead.get('resume_file_id')}",
            "uploaded_at": lead.get("resume_uploaded_at"),
            "lead": {
                "id": actual_lead_id,
                "lead_number": lead.get("lead_number"),
                "resume_file_id": lead.get("resume_file_id"),
                "resume_filename": lead.get("resume_filename") or "Candidate Resume",
                "resume_url": lead.get("resume_url") or f"/cockpit/resume/{lead.get('resume_file_id')}",
                "resume_uploaded": True,
            }
        }

    # 2. Check if any duplicate lead record for this candidate has an attached resume
    client_name = (lead.get("name") or "").strip()
    client_email = (lead.get("email") or "").strip().lower()
    raw_phone = str(lead.get("phone") or lead.get("whatsapp_number") or lead.get("mobile") or "").strip()
    clean_digits = re.sub(r"[^\d]", "", raw_phone)
    phone_10 = clean_digits[-10:] if len(clean_digits) >= 10 else clean_digits if len(clean_digits) >= 7 else None

    search_conditions: List[Dict[str, Any]] = []
    if client_email and "@" in client_email:
        search_conditions.append({"email": {"$regex": f"^{re.escape(client_email)}$", "$options": "i"}})
    if phone_10:
        search_conditions.extend([
            {"phone": {"$regex": re.escape(phone_10)}},
            {"whatsapp_number": {"$regex": re.escape(phone_10)}},
            {"alternate_phone": {"$regex": re.escape(phone_10)}},
            {"mobile": {"$regex": re.escape(phone_10)}},
        ])
    if client_name and len(client_name) >= 4 and client_name.lower() not in ("applicant", "unknown", "lead", "client"):
        search_conditions.append({"name": {"$regex": f"^{re.escape(client_name)}$", "$options": "i"}})

    if search_conditions:
        cand_lead = await leads_col.find_one({
            "$and": [
                {"$or": search_conditions},
                {"$or": [
                    {"resume_file_id": {"$exists": True, "$ne": None, "$nin": ["", "null", "undefined"]}},
                    {"resume_url": {"$regex": r"/resume/|/cockpit/|/uploads/"}}
                ]}
            ]
        })
        if cand_lead and cand_lead.get("resume_file_id"):
            file_id = cand_lead["resume_file_id"]
            fn = cand_lead.get("resume_filename") or "Candidate Resume"
            await attach_and_sync_resume(
                lead_id=actual_lead_id,
                file_id_str=file_id,
                filename=fn,
                uploaded_by={"id": "auto_sync", "name": "Multi-Record Sync"}
            )
            return {
                "success": True,
                "has_resume": True,
                "resume_file_id": file_id,
                "resume_filename": fn,
                "resume_url": cand_lead.get("resume_url") or f"/cockpit/resume/{file_id}",
                "uploaded_at": cand_lead.get("resume_uploaded_at"),
                "lead": {
                    "id": actual_lead_id,
                    "lead_number": lead.get("lead_number"),
                    "resume_file_id": file_id,
                    "resume_filename": fn,
                    "resume_url": cand_lead.get("resume_url") or f"/cockpit/resume/{file_id}",
                    "resume_uploaded": True,
                }
            }

    return {
        "success": True,
        "has_resume": False,
        "resume_file_id": None,
        "resume_filename": None,
        "resume_url": None,
        "lead": {
            "id": actual_lead_id,
            "lead_number": lead.get("lead_number"),
            "resume_file_id": None,
            "resume_uploaded": False,
        }
    }


@router.post("/leads/{lead_id}/generate-assessment-report")
async def generate_crm_lead_assessment_report(
    lead_id: str,
    payload: Optional[Dict[str, Any]] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Generates immutable professional Assessment Report (PDF v2) from lead record."""
    import re
    import io
    from bson import ObjectId
    from routers.assessment_reports import _build_snapshot, REPORT_SNAPSHOTS, ASSESSMENTS
    from core.report_v2 import render_pdf_v2
    from motor.motor_asyncio import AsyncIOMotorGridFSBucket

    lead = await _resolve_crm_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Permission check
    if not _is_admin(current_user) and not _is_manager_or_admin(current_user):
        user_id = str(current_user.get("id") or "").strip()
        user_email = str(current_user.get("email") or "").strip().lower()
        lead_assignee = str(lead.get("assigned_to") or "").strip()
        lead_assignee_email = str(lead.get("assigned_to_email") or "").strip().lower()
        if user_id != lead_assignee and user_email != lead_assignee_email:
            raise HTTPException(status_code=403, detail="Access denied. You can only generate reports for assigned leads.")

    real_lead_id = lead.get("id") or str(lead.get("_id"))
    now = datetime.now(timezone.utc)

    # Validation: Resume must be uploaded before generating the assessment report
    has_resume = bool(
        lead.get("resume_file_id")
        or lead.get("resume_url")
        or lead.get("resume_path")
        or lead.get("resume_uploaded")
    )
    if not has_resume:
        from core.resume_service import get_resume_bytes_and_meta
        resume_doc = await get_resume_bytes_and_meta(real_lead_id)
        if not resume_doc:
            raise HTTPException(
                status_code=400,
                detail="Client resume is required before generating the Assessment Report. Please upload or attach the client resume first."
            )
    
    # Check if snapshot already exists and force_regenerate is False
    body = payload or {}
    force_regenerate = body.get("force_regenerate", False)
    existing_snap_id = lead.get("latest_report_snapshot_id") or lead.get("assessment_report_id")
    if existing_snap_id and not force_regenerate:
        existing_snap = await REPORT_SNAPSHOTS.find_one({"snapshot_id": existing_snap_id}, {"_id": 0})
        if existing_snap:
            return {
                "success": True,
                "snapshot_id": existing_snap_id,
                "pdf_url": f"/api/assessment-reports/{existing_snap_id}/pdf",
                "message": "Existing verified report retrieved."
            }

    # Generate assessment document
    target_country = (lead.get("country_of_interest") or lead.get("interested_country") or lead.get("country") or "AU").strip()
    if target_country.lower() in ("australia", "au"):
        cc = "AU"
    elif target_country.lower() in ("canada", "ca"):
        cc = "CA"
    elif target_country.lower() in ("united kingdom", "uk", "gb"):
        cc = "UK"
    elif target_country.lower() in ("new zealand", "nz"):
        cc = "NZ"
    elif target_country.lower() in ("united states", "usa", "us"):
        cc = "USA"
    else:
        cc = "AU"

    occ_title = lead.get("occupation") or lead.get("job_title") or lead.get("service_interested") or "Software and Applications Programmers"
    occ_code = lead.get("occupation_code") or lead.get("anzsco_code") or "261399"
    
    assessment_id = lead.get("assessment_id") or f"ASM-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    client_name = lead.get("name") or "Valued Client"
    client_email = lead.get("email") or ""
    client_phone = lead.get("phone") or ""

    resume_f_id = lead.get("resume_file_id")
    resume_fname = lead.get("resume_filename")
    resume_u = lead.get("resume_url")
    client_age = int(lead.get("age") or 29)
    client_qual = lead.get("latest_qualification") or lead.get("education") or "Bachelor's Degree"
    client_exp = float(lead.get("experience_years") or lead.get("work_experience") or 4.0)

    doc = {
        "id": assessment_id,
        "lead_id": real_lead_id,
        "client_name": client_name,
        "client_email": client_email,
        "client_phone": client_phone,
        "occupation_country": cc,
        "best_country_code": cc,
        "resume_file_id": resume_f_id,
        "resume_filename": resume_fname,
        "resume_url": resume_u,
        "resume_uploaded": True if (resume_f_id or resume_u) else False,
        "profile": {
            "client_name": client_name,
            "marital_status": lead.get("marital_status") or "single",
            "resume_file_id": resume_f_id,
            "resume_filename": resume_fname,
            "resume_url": resume_u,
            "primary_applicant": {
                "personal": {"age": client_age},
                "education": {"highest_qualification": client_qual},
                "professional": {
                    "current_profession": occ_title,
                    "designation": occ_title,
                    "years_experience_total": client_exp,
                    "years_experience_australia": 0.0,
                },
                "language": {
                    "scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}
                },
                "au_extras": {},
                "ca_extras": {},
                "nz_extras": {},
            },
        },
        "occupation": {
            "code": occ_code,
            "title": occ_title,
            "country_code": cc,
            "assessing_body": "ACS" if cc == "AU" else "VETASSESS",
            "pathway": "Skilled Migration",
        },
        "occupations": [
            {
                "code": occ_code,
                "title": occ_title,
                "country_code": cc,
                "assessing_body": "ACS" if cc == "AU" else "VETASSESS",
                "pathway": "Skilled Migration",
            }
        ],
        "profile_snapshot": {
            "name": client_name,
            "age": client_age,
            "education": client_qual,
            "experience_years": client_exp,
            "english_level": lead.get("english_level") or "Proficient (IELTS 7 / PTE 65+)",
            "primary_applicant": {
                "age": client_age,
                "education": client_qual,
                "experience_years": client_exp,
                "english_level": lead.get("english_level") or "Proficient",
            }
        },
        "results": [
            {
                "country_code": cc,
                "country": target_country,
                "visa_subclass": "189" if cc == "AU" else "Express Entry",
                "total": int(lead.get("score") or 75),
                "pass_mark": 65,
                "breakdown": {
                    "Age": 30,
                    "English": 10,
                    "Qualifications": 15,
                    "Work Experience": 10,
                    "Partner / Australian Study": 10
                },
                "recommendation": f"Skilled Migration Pathway — {target_country}",
            }
        ],
        "score": int(lead.get("score") or 75),
        "best_total": int(lead.get("score") or 75),
        "best_country_code": cc,
        "status": "verified",
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name"),
        "created_at": now,
        "updated_at": now,
    }
    await ASSESSMENTS.replace_one({"id": assessment_id}, doc, upsert=True)

    # Build report snapshot + render PDF
    snap_data = await _build_snapshot(doc, persona="client", mode="combined", include_unverified=False)
    snapshot_id = f"RPT-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    await REPORT_SNAPSHOTS.insert_one({
        "snapshot_id": snapshot_id,
        "assessment_id": assessment_id,
        "client_name": client_name,
        "persona": "client",
        "mode": "combined",
        "data": snap_data,
        "data_integrity_hash": snap_data.get("data_integrity_hash"),
        "generated_at": now,
        "generated_by": current_user["id"],
        "is_immutable": True,
    })
    snap_data["snapshot_id"] = snapshot_id
    pdf_bytes = render_pdf_v2(snap_data)

    gridfs = AsyncIOMotorGridFSBucket(db)
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", client_name)[:40]
    file_id = await gridfs.upload_from_stream(
        f"{safe_name}_{assessment_id}.pdf", io.BytesIO(pdf_bytes),
        metadata={"lead_id": real_lead_id, "snapshot_id": snapshot_id, "client_name": client_name},
    )

    await ASSESSMENTS.update_one(
        {"id": assessment_id},
        {"$set": {
            "snapshot_id": snapshot_id,
            "latest_report_snapshot_id": snapshot_id,
            "assessment_report_id": snapshot_id,
            "pdf_file_id": str(file_id),
            "updated_at": now,
        }}
    )

    lead_query = [{"id": real_lead_id}, {"unique_id": real_lead_id}]
    if ObjectId.is_valid(real_lead_id):
        lead_query.append({"_id": ObjectId(real_lead_id)})
    
    await leads_col.update_many(
        {"$or": lead_query},
        {"$set": {
            "report_generated": True,
            "report_status": "generated",
            "report_generated_at": now.isoformat(),
            "latest_report_snapshot_id": snapshot_id,
            "assessment_report_id": snapshot_id,
            "assessment_id": assessment_id,
            "pdf_file_id": str(file_id),
            "updated_at": now,
        }}
    )

    activity_entry = {
        "id": str(uuid.uuid4()),
        "lead_id": real_lead_id,
        "activity_type": "report_generated",
        "type": "report_generated",
        "title": "Assessment Report Generated",
        "description": f"Assessment Report (PDF v2) generated successfully (Snapshot: {snapshot_id}).",
        "snapshot_id": snapshot_id,
        "user_id": current_user.get("id"),
        "user_name": current_user.get("name"),
        "timestamp": now.isoformat(),
        "created_at": now.isoformat(),
    }
    await leads_col.update_one(
        {"$or": lead_query},
        {"$push": {"timeline": activity_entry}}
    )
    await crm_audit_logs_col.insert_one(activity_entry)

    return {
        "success": True,
        "snapshot_id": snapshot_id,
        "assessment_id": assessment_id,
        "pdf_url": f"/api/assessment-reports/{snapshot_id}/pdf",
        "message": f"Assessment Report generated successfully for {client_name}."
    }


@router.get("/partner-report")
async def get_crm_partner_report(
    partner_id: Optional[str] = Query(None),
    period: str = Query("lifetime"),
    current_user: dict = Depends(get_current_user)
):
    """Admin / Manager Partner Performance & Referral Report."""
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    from routers.sales import get_partner_report as _sales_partner_report
    return await _sales_partner_report(partner_id=partner_id, period=period, current_user=current_user)


@router.post("/leads/{lead_id}/check-razorpay-payment")
async def check_lead_razorpay_payment(
    lead_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Reconciles live Razorpay payments directly against a specific CRM lead via email and phone."""
    from services.razorpay_sync_service import reconcile_single_lead_payment
    res = await reconcile_single_lead_payment(lead_id)
    if not res.get("success") and res.get("error") == "Lead not found":
        raise HTTPException(status_code=404, detail="Lead not found")
    return res


@router.post("/payments/razorpay/sync")
async def sync_razorpay_payments_batch(
    count: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Fetches recent Razorpay payments directly from Razorpay API and links them to CRM leads."""
    from services.razorpay_sync_service import sync_all_recent_razorpay_payments
    res = await sync_all_recent_razorpay_payments(count=count)
    return res


