"""CRM Activities Router — Follow-ups, Tasks, Meetings, and Timeline"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from core.database import db
from core.auth import get_current_user
from core.services import create_notification, log_activity
from core.meeting_service import generate_meeting_link, get_meeting_config, save_meeting_config

logger = logging.getLogger("crm_activities")

router = APIRouter(prefix="/crm", tags=["CRM Activities"])

follow_ups_col = db["follow_ups"]
crm_tasks_col = db["crm_tasks"]
crm_meetings_col = db["crm_meetings"]
crm_calls_col = db["crm_calls"]
crm_whatsapp_col = db["crm_whatsapp_messages"]
crm_emails_col = db["crm_emails"]
leads_col = db["leads"]
audit_logs_col = db["audit_logs"]


def _is_sales_person(user: dict) -> bool:
    return user.get("role") in ["partner", "sales_executive", "sr_sales_executive"] or user.get("rbac_role") in ["partner", "sales_executive", "sr_sales_executive"]


# ────────────────────────────────────────────────────────────
# 1. FOLLOW-UPS MANAGEMENT & REMINDERS
# ────────────────────────────────────────────────────────────

@router.post("/follow-ups")
async def create_crm_follow_up(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Create a follow-up with reminders and priority"""
    lead_id = data.get("lead_id")
    client_id = data.get("client_id")
    scheduled_at = data.get("scheduled_at")
    follow_up_type = data.get("type", "Call")  # Call, WhatsApp, Email, Meeting, Payment Follow-up
    priority = data.get("priority", "medium")  # low, medium, high, urgent
    notes = data.get("notes") or data.get("message", "")
    reminder_before = data.get("reminder_before", "30_mins")  # 30_mins, 1_hour, 1_day

    assigned_to = data.get("assigned_to") or current_user["id"]
    assigned_name = data.get("assigned_to_name") or current_user.get("name", "")

    lead_name = data.get("lead_name", "")
    lead_phone = data.get("lead_phone", "")
    if lead_id and not lead_name:
        lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1, "phone": 1})
        if lead:
            lead_name = lead.get("name", "")
            lead_phone = lead.get("phone", "")

    fu_doc = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "client_id": client_id,
        "lead_name": lead_name,
        "lead_phone": lead_phone,
        "type": follow_up_type,
        "priority": priority,
        "scheduled_at": scheduled_at,
        "notes": notes,
        "message": notes,
        "reminder_before": reminder_before,
        "status": "pending",  # pending, completed, overdue, rescheduled, cancelled
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_name,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc),
        "completed_at": None,
        "outcome": None
    }
    await follow_ups_col.insert_one(fu_doc)

    # Update next_follow_up on lead
    if lead_id and scheduled_at:
        await leads_col.update_one({"id": lead_id}, {"$set": {"next_follow_up": scheduled_at, "last_contacted_at": datetime.now(timezone.utc)}})

    # Activity log
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action="follow_up_created",
        entity_type="lead" if lead_id else "client",
        entity_id=lead_id or client_id,
        details=f"Follow-up scheduled ({follow_up_type}) on {scheduled_at}. Notes: {notes}"
    )

    # Record to Salesperson Activity Audit Log
    try:
        from services.salesperson_activity_service import log_salesperson_activity
        client_name_val = None
        if lead_id:
            ld = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1, "phone": 1, "email": 1})
            if ld:
                client_name_val = ld.get("name")
        await log_salesperson_activity(
            db=db,
            salesperson_id=current_user["id"],
            salesperson_name=current_user.get("name", "Sales Person"),
            salesperson_email=current_user.get("email"),
            salesperson_role=current_user.get("rbac_role") or current_user.get("role"),
            activity_type="follow_up",
            client_id=lead_id or client_id,
            client_name=client_name_val,
            title=f"Follow-up Scheduled ({follow_up_type})",
            details=f"Scheduled for {scheduled_at}. Notes: {notes or 'None'}",
            metadata={"follow_up_type": follow_up_type, "scheduled_at": scheduled_at, "priority": priority}
        )
    except Exception as e:
        logger.warning(f"Error logging follow-up creation to audit: {e}")

    return {"message": "Follow-up created successfully", "id": fu_doc["id"]}


@router.get("/follow-ups")
async def get_crm_follow_ups(
    status: Optional[str] = Query(None),  # pending, completed, overdue, today
    lead_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(100),
    current_user: dict = Depends(get_current_user)
):
    """List follow-ups with role filtering and status filters"""
    query: Dict[str, Any] = {}
    if lead_id:
        query["lead_id"] = lead_id
    if priority:
        query["priority"] = priority
    
    if _is_sales_person(current_user):
        query["$or"] = [{"assigned_to": current_user["id"]}, {"created_by": current_user["id"]}]
    
    now_utc = datetime.now(timezone.utc).isoformat()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_end = (datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)).isoformat()

    if status == "pending":
        query["status"] = "pending"
    elif status == "completed":
        query["status"] = "completed"
    elif status == "overdue":
        query["status"] = "pending"
        query["scheduled_at"] = {"$lt": now_utc}
    elif status == "today":
        query["status"] = "pending"
        query["scheduled_at"] = {"$gte": today_start, "$lte": today_end}

    follow_ups = await follow_ups_col.find(query, {"_id": 0}).sort("scheduled_at", 1).to_list(limit)
    for fu in follow_ups:
        for f in ["created_at", "completed_at"]:
            if isinstance(fu.get(f), datetime):
                fu[f] = fu[f].isoformat()
        # enrich lead info if missing
        if fu.get("lead_id") and not fu.get("lead_name"):
            lead = await leads_col.find_one({"id": fu["lead_id"]}, {"_id": 0, "name": 1, "phone": 1})
            if lead:
                fu["lead_name"] = lead.get("name", "Unknown")
                fu["lead_phone"] = lead.get("phone", "")
        # auto-flag overdue in response
        if fu.get("status") == "pending" and fu.get("scheduled_at") and fu["scheduled_at"] < now_utc:
            fu["is_overdue"] = True
        else:
            fu["is_overdue"] = False

    return follow_ups


@router.put("/follow-ups/{fu_id}/status")
async def update_follow_up_status(
    fu_id: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Complete, reschedule, or cancel a follow-up"""
    new_status = data.get("status", "completed")
    outcome = data.get("outcome", "")
    rescheduled_at = data.get("rescheduled_at")

    fu = await follow_ups_col.find_one({"id": fu_id}, {"_id": 0})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    updates: Dict[str, Any] = {"status": new_status, "outcome": outcome}
    if new_status == "completed":
        updates["completed_at"] = datetime.now(timezone.utc)
        updates["completed_by"] = current_user["id"]
    elif new_status == "rescheduled" and rescheduled_at:
        updates["scheduled_at"] = rescheduled_at
        updates["status"] = "pending"
        updates["rescheduled_count"] = fu.get("rescheduled_count", 0) + 1

    await follow_ups_col.update_one({"id": fu_id}, {"$set": updates})

    # Trigger real-time targets recalculation for follow-up completion
    try:
        from core.targets_logic import recalc_targets_for_user
        target_rep = fu.get("assigned_to") or current_user["id"]
        if target_rep:
            await recalc_targets_for_user(target_rep, notify=True)
        if current_user["id"] != target_rep:
            await recalc_targets_for_user(current_user["id"], notify=False)
    except Exception:
        pass

    # Activity log
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action=f"follow_up_{new_status}",
        entity_type="lead" if fu.get("lead_id") else "client",
        entity_id=fu.get("lead_id") or fu.get("client_id"),
        details=f"Follow-up marked {new_status}. Outcome: {outcome}"
    )

    # Record to Salesperson Activity Audit Log
    try:
        from services.salesperson_activity_service import log_salesperson_activity
        client_name_val = fu.get("lead_name") or fu.get("client_name")
        if not client_name_val and fu.get("lead_id"):
            ld = await leads_col.find_one({"id": fu.get("lead_id")}, {"_id": 0, "name": 1})
            if ld:
                client_name_val = ld.get("name")
        await log_salesperson_activity(
            db=db,
            salesperson_id=current_user["id"],
            salesperson_name=current_user.get("name", "Sales Person"),
            salesperson_email=current_user.get("email"),
            salesperson_role=current_user.get("rbac_role") or current_user.get("role"),
            activity_type="follow_up",
            client_id=fu.get("lead_id") or fu.get("client_id"),
            client_name=client_name_val,
            title=f"Follow-up Marked {new_status.title()}",
            details=f"Outcome: {outcome or 'None'}. Type: {fu.get('type', 'Call')}",
            metadata={"status": new_status, "outcome": outcome, "fu_id": fu_id}
        )
    except Exception as e:
        logger.warning(f"Error logging follow-up update to audit: {e}")

    return {"message": f"Follow-up updated to {new_status}"}


# ────────────────────────────────────────────────────────────
# 2. TASK MANAGEMENT
# ────────────────────────────────────────────────────────────

@router.post("/tasks")
async def create_crm_task(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Create a task for Sales Person or Team"""
    lead_id = data.get("lead_id")
    client_id = data.get("client_id")
    title = data.get("title") or data.get("task_name", "Untitled Task")
    description = data.get("description", "")
    priority = data.get("priority", "medium")
    due_date = data.get("due_date")
    assigned_to = data.get("assigned_to") or current_user["id"]
    assigned_to_name = data.get("assigned_to_name") or current_user.get("name", "")

    task_doc = {
        "id": str(uuid.uuid4()),
        "title": title,
        "task_name": title,
        "description": description,
        "priority": priority,
        "due_date": due_date,
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_to_name,
        "lead_id": lead_id,
        "client_id": client_id,
        "status": "pending",  # pending, in_progress, completed, cancelled
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc),
        "completed_at": None
    }
    await crm_tasks_col.insert_one(task_doc)

    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action="task_created",
        entity_type="lead" if lead_id else "client",
        entity_id=lead_id or client_id,
        details=f"Task '{title}' created (Priority: {priority}, Due: {due_date})"
    )

    return {"message": "Task created successfully", "id": task_doc["id"]}


@router.get("/tasks")
async def get_crm_tasks(
    lead_id: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100),
    current_user: dict = Depends(get_current_user)
):
    """Get CRM tasks with role filtering"""
    query: Dict[str, Any] = {}
    if lead_id:
        query["lead_id"] = lead_id
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status
    
    if _is_sales_person(current_user):
        query["assigned_to"] = current_user["id"]

    tasks = await crm_tasks_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    for t in tasks:
        for f in ["created_at", "completed_at"]:
            if isinstance(t.get(f), datetime):
                t[f] = t[f].isoformat()
    return tasks


@router.put("/tasks/{task_id}")
async def update_crm_task(task_id: str, data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Update task details or mark complete"""
    updates = {k: v for k, v in data.items() if k not in ["_id", "id"]}
    if updates.get("status") == "completed":
        updates["completed_at"] = datetime.now(timezone.utc)
    
    await crm_tasks_col.update_one({"id": task_id}, {"$set": updates})
    return {"message": "Task updated successfully"}


# ────────────────────────────────────────────────────────────
# 3. MEETING MANAGEMENT (GOOGLE MEET & ZOOM INTEGRATION)
# ────────────────────────────────────────────────────────────

@router.post("/meetings/generate-link")
async def generate_meeting_link_endpoint(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Generate a real Google Meet or Zoom link on demand"""
    platform = data.get("meeting_type") or data.get("platform", "Google Meet")
    topic = data.get("title", "Consultation Meeting")
    meeting_date = data.get("meeting_date")
    meeting_time = data.get("meeting_time")
    duration = int(data.get("duration_minutes", 30))
    res = await generate_meeting_link(platform=platform, topic=topic, meeting_date=meeting_date, meeting_time=meeting_time, duration_minutes=duration)
    return res


@router.get("/meetings/config")
async def get_meetings_config_endpoint(current_user: dict = Depends(get_current_user)):
    """Retrieve Zoom & Google Meet configuration settings"""
    return await get_meeting_config()


@router.post("/meetings/config")
async def save_meetings_config_endpoint(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Update Zoom & Google Meet API credentials"""
    return await save_meeting_config(data)


@router.post("/meetings")
async def schedule_meeting(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Schedule meeting (Google Meet, Zoom, Office, Phone) with real link generation & history logging"""
    lead_id = data.get("lead_id")
    client_id = data.get("client_id")
    title = data.get("title", "Consultation Meeting")
    meeting_type = data.get("meeting_type", "Google Meet")  # Google Meet, Zoom, Office Meeting, Phone Meeting
    meeting_date = data.get("meeting_date")  # YYYY-MM-DD
    meeting_time = data.get("meeting_time")  # HH:MM
    duration_minutes = int(data.get("duration_minutes", 30))
    meeting_link = data.get("meeting_link", "")
    meeting_password = data.get("meeting_password", "")
    location = data.get("location", "")
    notes = data.get("notes", "")

    # Resolve contact info if not provided
    contact_name = data.get("contact_name", "")
    contact_phone = data.get("contact_phone", "")
    contact_email = data.get("contact_email", "")

    if lead_id and not (contact_name and contact_phone and contact_email):
        lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1, "phone": 1, "email": 1, "whatsapp_number": 1})
        if lead:
            if not contact_name:
                contact_name = lead.get("name", "")
            if not contact_phone:
                contact_phone = lead.get("whatsapp_number") or lead.get("phone", "")
            if not contact_email:
                contact_email = lead.get("email", "")

    # Auto-generate link if not supplied
    if not meeting_link:
        gen = await generate_meeting_link(platform=meeting_type, topic=title, meeting_date=meeting_date, meeting_time=meeting_time, duration_minutes=duration_minutes)
        meeting_link = gen.get("meeting_link", "")
        if not meeting_password:
            meeting_password = gen.get("password", "")

    sales_person_name = data.get("sales_person_name") or current_user.get("name", "Sales Person")

    meeting_doc = {
        "id": str(uuid.uuid4()),
        "title": title,
        "lead_id": lead_id,
        "client_id": client_id,
        "contact_name": contact_name,
        "contact_phone": contact_phone,
        "contact_email": contact_email,
        "sales_person_id": current_user["id"],
        "sales_person_name": sales_person_name,
        "meeting_type": meeting_type,
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "duration_minutes": duration_minutes,
        "meeting_link": meeting_link,
        "meeting_password": meeting_password,
        "location": location,
        "notes": notes,
        "status": "scheduled",  # scheduled, completed, cancelled, rescheduled
        "reminders_sent": [],
        "recap": data.get("recap"),
        "created_at": datetime.now(timezone.utc)
    }
    await crm_meetings_col.insert_one(meeting_doc)

    dur_text = f" ({duration_minutes} mins)" if duration_minutes else ""
    await log_activity(
        user_id=current_user["id"],
        user_name=sales_person_name,
        action="meeting_scheduled",
        entity_type="lead" if lead_id else "client",
        entity_id=lead_id or client_id,
        details=f"Meeting '{title}' scheduled via {meeting_type} on {meeting_date} at {meeting_time}{dur_text} with {contact_name or 'Client'}. Link: {meeting_link}"
    )

    if lead_id:
        await leads_col.update_one({"id": lead_id}, {"$set": {"last_contacted_at": datetime.now(timezone.utc), "has_booking": True}})

    # Trigger booking confirmation email to client if requested
    send_email_to_client = data.get("send_client_email", True)
    if send_email_to_client and contact_email and "@" in contact_email:
        from services.integrations.calendly_service import send_meeting_confirmation_email
        try:
            await send_meeting_confirmation_email(
                to_email=contact_email,
                client_name=contact_name,
                consultant_name=sales_person_name,
                meeting_title=title,
                meeting_date=meeting_date,
                meeting_time=meeting_time,
                duration_minutes=duration_minutes,
                meeting_link=meeting_link,
                platform=meeting_type
            )
        except Exception as e:
            logger.warning(f"Could not dispatch meeting confirmation email: {e}")

    return {
        "message": "Meeting scheduled successfully",
        "id": meeting_doc["id"],
        "meeting_link": meeting_link,
        "meeting_password": meeting_password,
        "status": "scheduled"
    }


@router.get("/meetings")
async def get_meetings(
    lead_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(200),
    current_user: dict = Depends(get_current_user)
):
    """Get meetings with role filtering, status filters (scheduled, upcoming, completed, cancelled, rescheduled), and date sorting"""
    query: Dict[str, Any] = {}
    if lead_id:
        query["lead_id"] = lead_id

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if status and status != "all":
        if status == "upcoming":
            query["status"] = "scheduled"
            query["meeting_date"] = {"$gte": today_str}
        else:
            query["status"] = status

    if _is_sales_person(current_user):
        query["sales_person_id"] = current_user["id"]

    meetings = await crm_meetings_col.find(query, {"_id": 0}).sort("meeting_date", -1).to_list(limit)
    for m in meetings:
        if isinstance(m.get("created_at"), datetime):
            m["created_at"] = m["created_at"].isoformat()
    return meetings


@router.post("/meetings/{meeting_id}/reschedule")
async def reschedule_meeting_endpoint(
    meeting_id: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Reschedule an existing meeting directly from CRM.
    Mandatory reason field required.
    Saves reschedule history for audit, syncs lead records, and dispatches notification email.
    """
    meeting = await crm_meetings_col.find_one({"id": meeting_id})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Permission check: Salesperson can only reschedule their assigned meetings
    if _is_sales_person(current_user) and meeting.get("sales_person_id") and meeting.get("sales_person_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only reschedule meetings assigned to you")

    new_date = str(data.get("meeting_date") or "").strip()
    new_time = str(data.get("meeting_time") or "").strip()
    reason = str(data.get("reason") or "").strip()
    notes = str(data.get("notes") or "").strip()
    duration_minutes = int(data.get("duration_minutes") or meeting.get("duration_minutes") or 30)
    notify_client = bool(data.get("notify_client", True))

    if not new_date:
        raise HTTPException(status_code=400, detail="New meeting date is required")
    if not new_time:
        raise HTTPException(status_code=400, detail="New meeting time is required")
    if not reason:
        raise HTTPException(status_code=400, detail="Reason for rescheduling is strictly mandatory")

    now = datetime.now(timezone.utc)
    old_date = meeting.get("meeting_date", "")
    old_time = meeting.get("meeting_time", "")

    # Look up linked lead record to access full client profile
    lead_id = meeting.get("lead_id")
    target_lead = None
    if lead_id:
        target_lead = await leads_col.find_one({"id": lead_id})
    if not target_lead and meeting.get("contact_email"):
        target_lead = await leads_col.find_one({"email": meeting["contact_email"].strip().lower()})

    client_name = meeting.get("contact_name") or (target_lead.get("name") if target_lead else "Client")
    client_email = meeting.get("contact_email") or (target_lead.get("email") if target_lead else "")
    client_phone = meeting.get("contact_phone") or (target_lead.get("phone") if target_lead else "")

    updates: Dict[str, Any] = {
        "meeting_date": new_date,
        "meeting_time": new_time,
        "duration_minutes": duration_minutes,
        "status": "rescheduled",
        "reschedule_reason": reason,
        "updated_at": now,
        "reminders_sent": []
    }
    if notes:
        updates["notes"] = f"{meeting.get('notes', '')}\n[Rescheduled]: {reason} ({notes})".strip()

    # Synchronize with Calendly API v2 if this is a Calendly booking
    is_calendly = bool(meeting.get("calendly_event_id") or str(meeting.get("meeting_type") or "").lower() == "calendly")
    if is_calendly:
        try:
            from services.integrations.calendly_service import reschedule_calendly_event_via_api
            cal_res = await reschedule_calendly_event_via_api(
                company_id=meeting.get("company_id") or "comp_leamss_primary",
                old_event_id=meeting.get("calendly_event_id") or "",
                new_date=new_date,
                new_time=new_time,
                reason=reason,
                client_name=client_name,
                client_email=client_email,
                client_phone=client_phone,
                duration_minutes=duration_minutes,
                invitee_id=meeting.get("calendly_invitee_id") or "",
                reschedule_url=meeting.get("reschedule_url") or ""
            )
            calendly_sync_status = "failed"
            if cal_res and cal_res.get("success"):
                if cal_res.get("new_event_id"):
                    updates["calendly_event_id"] = cal_res["new_event_id"]
                if cal_res.get("new_invitee_id"):
                    updates["calendly_invitee_id"] = cal_res["new_invitee_id"]
                if cal_res.get("meeting_link"):
                    updates["meeting_link"] = cal_res["meeting_link"]
                if cal_res.get("cancel_url"):
                    updates["cancel_url"] = cal_res["cancel_url"]
                if cal_res.get("reschedule_url"):
                    updates["reschedule_url"] = cal_res["reschedule_url"]
                calendly_sync_status = "synced"
            elif cal_res and not cal_res.get("success"):
                err_detail = cal_res.get("error", "Calendly rejected this time slot")
                raise HTTPException(status_code=400, detail=f"Calendly Synchronization Error: {err_detail}")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Calendly API reschedule warning: {e}")
            calendly_sync_status = "error"
    else:
        calendly_sync_status = "n/a"

    hist_entry = {
        "id": str(uuid.uuid4()),
        "rescheduled_at": now.isoformat(),
        "rescheduled_by": current_user["id"],
        "rescheduled_by_name": current_user.get("name") or "Sales Consultant",
        "old_date": old_date,
        "old_time": old_time,
        "new_date": new_date,
        "new_time": new_time,
        "duration_minutes": duration_minutes,
        "reason": reason,
        "notes": notes,
        "calendly_synced": (calendly_sync_status == "synced"),
        "calendly_status": calendly_sync_status
    }

    await crm_meetings_col.update_one(
        {"id": meeting_id},
        {
            "$set": updates,
            "$push": {"reschedule_history": hist_entry}
        }
    )

    # Synchronize Lead Document if linked
    lead_sync_query: Dict[str, Any] = {"$or": []}
    if target_lead:
        lead_sync_query["$or"].append({"id": target_lead["id"]})
    elif lead_id:
        lead_sync_query["$or"].append({"id": lead_id})
    if meeting.get("contact_email"):
        lead_sync_query["$or"].append({"email": meeting["contact_email"].strip().lower()})

    lead_note_text = (
        f"Meeting '{meeting.get('title')}' rescheduled from {old_date} {old_time} "
        f"to {new_date} at {new_time} by {current_user.get('name', 'Consultant')}.\n"
        f"Reason: {reason}"
    )
    if notes:
        lead_note_text += f"\nNotes: {notes}"

    lead_note_entry = {
        "id": str(uuid.uuid4()),
        "text": lead_note_text,
        "author": current_user.get("name", "Sales Consultant"),
        "created_at": now.isoformat()
    }

    if lead_sync_query["$or"]:
        await leads_col.update_many(
            lead_sync_query,
            {
                "$set": {
                    "updated_at": now,
                    "last_contacted_at": now,
                    "calendly_booking.date": new_date,
                    "calendly_booking.time": new_time,
                    "calendly_booking.meeting_link": updates.get("meeting_link") or meeting.get("meeting_link", ""),
                    "booking_details.date": new_date,
                    "booking_details.time": new_time,
                    "booking_details.meeting_link": updates.get("meeting_link") or meeting.get("meeting_link", ""),
                    "booking_details.status": "rescheduled",
                    "booking_details.reschedule_reason": reason
                },
                "$push": {"notes": lead_note_entry}
            }
        )

    # Send client reschedule email if enabled
    email_dispatched = False
    effective_client_email = client_email or meeting.get("contact_email")
    if notify_client and effective_client_email and "@" in effective_client_email:
        try:
            from services.integrations.calendly_service import send_meeting_rescheduled_email
            email_dispatched = await send_meeting_rescheduled_email(
                to_email=effective_client_email,
                client_name=client_name,
                consultant_name=meeting.get("sales_person_name") or current_user.get("name") or "LEAMSS Consultant",
                meeting_title=meeting.get("title") or "Immigration Consultation",
                new_date=new_date,
                new_time=new_time,
                duration_minutes=duration_minutes,
                meeting_link=updates.get("meeting_link") or meeting.get("meeting_link") or "",
                reason=reason,
                old_date=old_date,
                old_time=old_time,
                platform=meeting.get("meeting_type") or "Google Meet",
                reschedule_link=updates.get("reschedule_url") or meeting.get("reschedule_url")
            )
        except Exception:
            pass

    # Audit log
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action="meeting_rescheduled",
        entity_type="lead" if lead_id else "meeting",
        entity_id=lead_id or meeting_id,
        details=f"Meeting rescheduled to {new_date} at {new_time}. Reason: {reason}"
    )

    updated_meeting = await crm_meetings_col.find_one({"id": meeting_id}, {"_id": 0})
    if isinstance(updated_meeting.get("created_at"), datetime):
        updated_meeting["created_at"] = updated_meeting["created_at"].isoformat()
    if isinstance(updated_meeting.get("updated_at"), datetime):
        updated_meeting["updated_at"] = updated_meeting["updated_at"].isoformat()

    return {
        "success": True,
        "message": f"Meeting rescheduled to {new_date} at {new_time}",
        "email_dispatched": email_dispatched,
        "meeting": updated_meeting
    }


@router.post("/meetings/{meeting_id}/recap")
async def save_meeting_recap(
    meeting_id: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Save or update meeting recap, notes, transcripts, recording URL, and action items"""
    meeting = await crm_meetings_col.find_one({"id": meeting_id})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participants = data.get("participants")
    if not participants:
        participants = [p for p in [meeting.get("contact_name"), meeting.get("sales_person_name")] if p]

    recap_doc = {
        "summary": data.get("summary") or data.get("recap") or "",
        "action_items": data.get("action_items") or [],
        "transcripts": data.get("transcripts") or "",
        "recording_url": data.get("recording_url") or "",
        "participants": participants,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"],
        "updated_by_name": current_user.get("name", "")
    }

    await crm_meetings_col.update_one(
        {"id": meeting_id},
        {"$set": {"recap": recap_doc, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Meeting recap saved successfully", "recap": recap_doc}


@router.post("/meetings/{meeting_id}/sync-recap")
async def sync_meeting_recap_endpoint(
    meeting_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Syncs meeting recaps & transcripts from Calendly API if available"""
    meeting = await crm_meetings_col.find_one({"id": meeting_id})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    event_id = meeting.get("calendly_event_id")
    if not event_id:
        return {"success": False, "message": "No Calendly event ID associated with this meeting", "recap": meeting.get("recap")}

    from services.integrations.calendly_service import sync_meeting_recaps_and_notes
    recap_res = await sync_meeting_recaps_and_notes("comp_leamss_primary", event_id)
    if recap_res:
        existing_recap = meeting.get("recap") or {}
        merged_recap = {
            **existing_recap,
            "summary": recap_res.get("summary") or existing_recap.get("summary", ""),
            "transcripts": recap_res.get("transcript") or existing_recap.get("transcripts", ""),
            "synced_at": datetime.now(timezone.utc).isoformat()
        }
        await crm_meetings_col.update_one({"id": meeting_id}, {"$set": {"recap": merged_recap, "updated_at": datetime.now(timezone.utc)}})
        return {"success": True, "message": "Recap synchronized from Calendly", "recap": merged_recap}
    return {"success": True, "message": "No external recap available yet; existing recap retained", "recap": meeting.get("recap")}


@router.put("/meetings/{meeting_id}")
async def update_meeting_details(
    meeting_id: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Update meeting link, date, time, title, or notes"""
    meeting = await crm_meetings_col.find_one({"id": meeting_id})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    allowed_fields = [
        "title", "meeting_type", "meeting_date", "meeting_time",
        "duration_minutes", "meeting_link", "meeting_password", "notes", "status"
    ]
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    updates["updated_at"] = datetime.now(timezone.utc)

    await crm_meetings_col.update_one({"id": meeting_id}, {"$set": updates})
    return {"message": "Meeting updated successfully", "meeting_id": meeting_id}


@router.put("/meetings/{meeting_id}/status")
async def update_meeting_status(
    meeting_id: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Update meeting status (completed, cancelled, no_show, scheduled)"""
    new_status = data.get("status", "completed")
    outcome = data.get("outcome", "")
    notes = data.get("notes", "")

    meeting = await crm_meetings_col.find_one({"id": meeting_id})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    update_fields: Dict[str, Any] = {"status": new_status, "updated_at": datetime.now(timezone.utc)}
    if outcome:
        update_fields["outcome"] = outcome
    if notes:
        update_fields["completion_notes"] = notes

    await crm_meetings_col.update_one({"id": meeting_id}, {"$set": update_fields})

    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action=f"meeting_{new_status}",
        entity_type="lead" if meeting.get("lead_id") else "client",
        entity_id=meeting.get("lead_id") or meeting.get("client_id"),
        details=f"Meeting '{meeting.get('title')}' status updated to {new_status.upper()}"
    )
    return {"message": f"Meeting marked as {new_status}"}


@router.delete("/meetings/{meeting_id}")
async def cancel_or_delete_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel and delete meeting record"""
    meeting = await crm_meetings_col.find_one({"id": meeting_id})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    await crm_meetings_col.delete_one({"id": meeting_id})
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action="meeting_cancelled",
        entity_type="lead" if meeting.get("lead_id") else "client",
        entity_id=meeting.get("lead_id") or meeting.get("client_id"),
        details=f"Meeting '{meeting.get('title')}' cancelled and removed from CRM schedule"
    )
    return {"message": "Meeting deleted successfully"}


# Additional collections for 360 timeline
crm_deals_col = db["crm_deals"]
crm_payments_col = db["crm_payments"]
payments_col = db["payments"]
case_notes_col = db["case_notes"]


# ────────────────────────────────────────────────────────────
# 4. UNIFIED 360 ACTIVITY TIMELINE
# ────────────────────────────────────────────────────────────

@router.get("/timeline/{entity_type}/{entity_id}")
async def get_unified_activity_timeline(
    entity_type: str,  # lead or client
    entity_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive chronological activity timeline combining:
    - Lead Creation & Initial Ingestion
    - Audit logs & Status/Stage changes & Assignments
    - Calls logged (Incoming & Outgoing with Duration, Notes & Audio Recordings)
    - WhatsApp messages (Incoming & Outgoing)
    - Emails sent/received
    - Follow-ups created/completed/rescheduled
    - Tasks created/completed
    - Meetings scheduled
    - Deals created & updated
    - Payments received
    - Notes added
    - Conversion & Handover events
    """
    events = []
    
    # 0. Lead Profile baseline creation event
    lead_doc = await leads_col.find_one({"id": entity_id}, {"_id": 0})
    if lead_doc:
        created_at = lead_doc.get("created_at")
        ts = created_at.isoformat() if isinstance(created_at, datetime) else (str(created_at) if created_at else None)
        if ts:
            events.append({
                "id": f"creation-{entity_id}",
                "type": "lead_created",
                "action": "lead_created",
                "title": "Lead Created / Ingested",
                "description": f"Lead '{lead_doc.get('name')}' captured via {lead_doc.get('source', 'System')} ({lead_doc.get('campaign', 'Direct')}) for {lead_doc.get('service_interested', 'Immigration Consulting')}",
                "user_name": lead_doc.get("assigned_name") or "System Ingestion",
                "extra": {
                    "source": lead_doc.get("source"),
                    "campaign": lead_doc.get("campaign"),
                    "budget": lead_doc.get("budget"),
                    "service": lead_doc.get("service_interested"),
                    "country": lead_doc.get("country_of_interest") or lead_doc.get("interested_country")
                },
                "timestamp": ts
            })

    # 1. Audit / Activity logs
    audit_logs = await audit_logs_col.find(
        {"$or": [{"entity_id": entity_id}, {"case_id": entity_id}, {"lead_id": entity_id}]},
        {"_id": 0}
    ).to_list(150)
    for al in audit_logs:
        dt = al.get("created_at") or al.get("timestamp")
        act = al.get("action", "activity")
        act_lower = str(act).lower()
        is_stage = any(w in act_lower for w in ["stage", "status", "moved_to"])
        action_type = "stage_change" if is_stage else "audit_log"
        if is_stage and al.get("new_value"):
            old_v = str(al.get("old_value") or "").replace("_", " ").title()
            new_v = str(al.get("new_value") or "").replace("_", " ").title()
            title = f"Stage Changed: {old_v} ➔ {new_v}" if old_v else f"Stage Changed to {new_v}"
        else:
            title = act.replace("_", " ").title()

        events.append({
            "id": al.get("id") or str(uuid.uuid4()),
            "type": action_type,
            "action": act,
            "title": title,
            "description": al.get("details") or f"{al.get('user_name', 'User')} performed {act}",
            "user_name": al.get("user_name", "System"),
            "old_value": al.get("old_value"),
            "new_value": al.get("new_value"),
            "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
        })

    # 2. Calls (Incoming & Outgoing with audio recordings)
    call_query_or = [{"lead_id": entity_id}, {"client_id": entity_id}]
    if lead_doc:
        import re
        for fld in ["phone", "mobile", "whatsapp"]:
            val = lead_doc.get(fld)
            if val:
                digits = re.sub(r"\D", "", str(val))
                if len(digits) >= 6:
                    norm = digits[-10:] if len(digits) >= 10 else digits
                    pattern_str = r"\D*".join(re.escape(d) for d in norm) + r"\D*$"
                    rx = re.compile(pattern_str)
                    call_query_or.append({"lead_phone": rx})
                    call_query_or.append({"client_phone": rx})

    calls = await crm_calls_col.find({"$or": call_query_or}, {"_id": 0}).to_list(100)
    for c in calls:
        dt = c.get("created_at") or c.get("start_time")
        direction = c.get("direction", "outgoing")
        direction_badge = "Incoming Call" if direction == "incoming" else "Outgoing Call"
        duration_s = int(c.get("duration_seconds") or 0)
        mins = duration_s // 60
        secs = duration_s % 60
        dur_str = f"{mins:02d}:{secs:02d}"
        
        events.append({
            "id": c.get("id") or str(uuid.uuid4()),
            "type": "call",
            "action": f"call_{direction}",
            "title": f"{direction_badge} ({c.get('status', 'connected').title()})",
            "description": f"Duration: {dur_str} • Outcome: {c.get('outcome', '').replace('_', ' ').title()} • Notes: {c.get('notes') or 'No notes provided'}",
            "user_name": c.get("sales_person_name", "Sales Person"),
            "extra": {
                "recording_url": c.get("recording_url"),
                "duration_seconds": duration_s,
                "duration_formatted": dur_str,
                "direction": direction,
                "status": c.get("status", "connected"),
                "outcome": c.get("outcome", ""),
                "notes": c.get("notes", ""),
                "phone": c.get("lead_phone") or c.get("phone", ""),
                "ai_summary": c.get("ai_summary", "")
            },
            "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
        })

    # 3. WhatsApp messages & calls
    wa_query_or = [{"lead_id": entity_id}, {"client_id": entity_id}]
    if lead_doc:
        import re
        for fld in ["phone", "mobile", "whatsapp", "whatsapp_number", "alternate_phone"]:
            val = lead_doc.get(fld)
            if val:
                digits = re.sub(r"\D", "", str(val))
                if len(digits) >= 6:
                    norm = digits[-10:] if len(digits) >= 10 else digits
                    pattern_str = r"\D*".join(re.escape(d) for d in norm) + r"\D*$"
                    rx = re.compile(pattern_str)
                    wa_query_or.append({"phone": rx})

    wa_msgs = await crm_whatsapp_col.find({"$or": wa_query_or}, {"_id": 0}).to_list(150)
    for w in wa_msgs:
        dt = w.get("created_at")
        direction = w.get("direction", "outbound")
        is_call = w.get("type") == "call" or "call" in str(w.get("action", "")).lower()
        tpl_name = w.get("template_name")
        tpl_badge = f" [Template: {tpl_name}]" if tpl_name else ""

        w_status = (w.get("status") or "sent").lower()
        if is_call:
            direction_label = f"WhatsApp Call ({direction.capitalize()})"
            act_type = "whatsapp_call"
        elif w_status == "failed":
            direction_label = f"WhatsApp Message (Failed){tpl_badge}"
            act_type = "whatsapp_failed"
        elif w_status in ["pending", "pending_confirmation"]:
            direction_label = f"WhatsApp Message (Pending Confirmation){tpl_badge}"
            act_type = "whatsapp_pending"
        elif direction == "outbound":
            direction_label = f"Sent WhatsApp (Web){tpl_badge}"
            act_type = "whatsapp_sent"
        else:
            direction_label = f"Received WhatsApp{tpl_badge}"
            act_type = "whatsapp_received"

        events.append({
            "id": w.get("id") or str(uuid.uuid4()),
            "type": "whatsapp",
            "action": act_type,
            "title": direction_label,
            "description": w.get("text") or w.get("message", ""),
            "user_name": w.get("sales_person_name") or ("Prospect" if direction == "inbound" else "WhatsApp"),
            "extra": {
                "direction": direction,
                "phone": w.get("phone", ""),
                "is_call": is_call,
                "template_name": tpl_name,
                "status": w_status,
                "channel": w.get("channel", "whatsapp_web"),
                "error_message": w.get("error_message"),
                "salesperson_name": w.get("sales_person_name")
            },
            "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
        })

    # 4. Emails
    email_query_or = [{"lead_id": entity_id}, {"client_id": entity_id}]
    if lead_doc and lead_doc.get("email"):
        em = str(lead_doc.get("email")).strip().lower()
        if em:
            esc_em = re.escape(em)
            email_query_or.append({"to_email": {"$regex": f"^{esc_em}$", "$options": "i"}})
            email_query_or.append({"from_email": {"$regex": f"^{esc_em}$", "$options": "i"}})
    emails = await crm_emails_col.find({"$or": email_query_or}, {"_id": 0}).to_list(100)
    for e in emails:
        dt = e.get("created_at")
        events.append({
            "id": e.get("id") or str(uuid.uuid4()),
            "type": "email",
            "action": "email_sent",
            "title": f"Email: {e.get('subject', 'No Subject')}",
            "description": f"To: {e.get('to_email')} — Status: {e.get('status', 'Sent')}",
            "user_name": e.get("sales_person_name", "Sales Person"),
            "extra": {
                "to_email": e.get("to_email"),
                "subject": e.get("subject"),
                "body": e.get("body_html") or e.get("body_text") or e.get("body", "")
            },
            "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
        })

    # 5. Follow-ups
    follow_ups = await follow_ups_col.find({"$or": [{"lead_id": entity_id}, {"client_id": entity_id}]}, {"_id": 0}).to_list(100)
    for fu in follow_ups:
        dt = fu.get("created_at")
        events.append({
            "id": fu.get("id") or str(uuid.uuid4()),
            "type": "follow_up",
            "action": f"follow_up_{fu.get('status')}",
            "title": f"Follow-up ({fu.get('type', 'Call')}) - {fu.get('status', 'pending').upper()}",
            "description": f"Scheduled: {fu.get('scheduled_at')}. Notes: {fu.get('notes') or fu.get('message', '')}",
            "user_name": fu.get("created_by_name") or fu.get("assigned_to_name", "Consultant"),
            "extra": {
                "type": fu.get("type"),
                "priority": fu.get("priority"),
                "scheduled_at": fu.get("scheduled_at"),
                "status": fu.get("status"),
                "outcome": fu.get("outcome")
            },
            "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
        })

    # 6. Meetings
    meeting_query_or = [{"lead_id": entity_id}, {"client_id": entity_id}]
    if lead_doc:
        for fld in ["phone", "mobile", "whatsapp"]:
            val = lead_doc.get(fld)
            if val:
                meeting_query_or.append({"contact_phone": str(val).strip()})
        if lead_doc.get("email"):
            meeting_query_or.append({"contact_email": str(lead_doc.get("email")).strip()})
    meetings = await crm_meetings_col.find({"$or": meeting_query_or}, {"_id": 0}).to_list(100)
    for m in meetings:
        dt = m.get("created_at") or m.get("meeting_date")
        mt_lower = str(m.get("meeting_type")).lower()
        if mt_lower in ["google_meet", "google meet"]:
            platform_label = "Google Meet"
        elif mt_lower == "zoom":
            platform_label = "Zoom"
        elif mt_lower == "calendly":
            platform_label = "Calendly"
        else:
            platform_label = str(m.get("meeting_type", "Meeting")).title()
        events.append({
            "id": m.get("id") or str(uuid.uuid4()),
            "type": "meeting",
            "action": "meeting_scheduled",
            "title": f"Meeting: {m.get('title', 'Consultation')} ({platform_label})",
            "description": f"Date: {m.get('meeting_date')} at {m.get('meeting_time')} ({m.get('duration_minutes', 30)}m) • Link: {m.get('meeting_link') or 'N/A'}. Notes: {m.get('notes', '')}",
            "user_name": m.get("sales_person_name", "Sales Person"),
            "extra": {
                "meeting_id": m.get("id"),
                "title": m.get("title", "Consultation"),
                "meeting_type": m.get("meeting_type", "google_meet"),
                "meeting_date": m.get("meeting_date"),
                "meeting_time": m.get("meeting_time"),
                "duration_minutes": m.get("duration_minutes", 30),
                "meeting_link": m.get("meeting_link"),
                "meeting_password": m.get("meeting_password"),
                "contact_name": m.get("contact_name"),
                "contact_phone": m.get("contact_phone"),
                "contact_email": m.get("contact_email"),
                "notes": m.get("notes", ""),
                "status": m.get("status", "scheduled")
            },
            "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
        })

    # 7. Deals & Proposals
    deals = await crm_deals_col.find({"$or": [{"lead_id": entity_id}, {"client_id": entity_id}]}, {"_id": 0}).to_list(50)
    for d in deals:
        dt = d.get("created_at")
        events.append({
            "id": d.get("id") or str(uuid.uuid4()),
            "type": "deal",
            "action": "deal_created",
            "title": f"Deal: {d.get('deal_name', 'Visa Package')} (₹{d.get('deal_value', 0):,})",
            "description": f"Service: {d.get('service')} • Stage: {d.get('stage', 'proposal').title()} • Priority: {d.get('priority', 'high').upper()}",
            "user_name": d.get("sales_person_name", "Sales Person"),
            "extra": {
                "deal_value": d.get("deal_value"),
                "service": d.get("service"),
                "stage": d.get("stage")
            },
            "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
        })

    # 8. Payments
    payments = await crm_payments_col.find({"$or": [{"lead_id": entity_id}, {"client_id": entity_id}]}, {"_id": 0}).to_list(50)
    if not payments:
        payments = await payments_col.find({"$or": [{"lead_id": entity_id}, {"client_id": entity_id}, {"user_id": entity_id}]}, {"_id": 0}).to_list(50)
    for p in payments:
        dt = p.get("created_at")
        paid_amt = p.get("paid_amount") or p.get("amount", 0)
        events.append({
            "id": p.get("id") or str(uuid.uuid4()),
            "type": "payment",
            "action": "payment_received",
            "title": f"Payment Received: ₹{paid_amt:,}",
            "description": f"Package: {p.get('package_name', 'Processing Package')} • Method: {p.get('payment_method', 'Bank Transfer')} • Status: {p.get('status', 'Completed')}",
            "user_name": p.get("sales_person_name", "Sales Person"),
            "extra": {
                "paid_amount": paid_amt,
                "package_price": p.get("package_price"),
                "payment_method": p.get("payment_method"),
                "notes": p.get("notes", "")
            },
            "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
        })

    # 9. Case Notes / General Notes
    notes = await case_notes_col.find({"$or": [{"lead_id": entity_id}, {"case_id": entity_id}, {"client_id": entity_id}]}, {"_id": 0}).to_list(50)
    for n in notes:
        dt = n.get("created_at")
        events.append({
            "id": n.get("id") or str(uuid.uuid4()),
            "type": "note",
            "action": "note_added",
            "title": f"Note: {n.get('category', 'General Note').title()}",
            "description": n.get("note") or n.get("content") or n.get("text", ""),
            "user_name": n.get("created_by_name") or n.get("author_name", "Consultant"),
            "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
        })

    # 9b. Lead Notes / Client Remarks
    if lead_doc and lead_doc.get("notes"):
        for ln in lead_doc.get("notes", []):
            dt = ln.get("created_at")
            note_type = ln.get("note_type") or ln.get("type") or "Other Remarks"
            role_badge = ln.get("added_by_role") or ("Admin" if ln.get("is_admin") else "Salesperson")
            events.append({
                "id": ln.get("id") or str(uuid.uuid4()),
                "type": "note",
                "action": "client_remark",
                "title": f"Remark: {note_type}",
                "description": ln.get("text") or ln.get("description", ""),
                "user_name": f"{ln.get('added_by_name', 'Consultant')} ({role_badge})",
                "extra": {
                    "note_type": note_type,
                    "author_name": ln.get("added_by_name"),
                    "author_role": role_badge,
                    "is_admin": ln.get("is_admin", False),
                    "date_display": ln.get("date_display"),
                    "time_display": ln.get("time_display")
                },
                "timestamp": dt.isoformat() if isinstance(dt, datetime) else str(dt)
            })

    # Deduplicate events by id / action + timestamp
    seen = set()
    unique_events = []
    for ev in events:
        key = (ev.get("type"), ev.get("title"), ev.get("timestamp"))
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)

    # Sort descending by timestamp (newest first)
    unique_events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    return unique_events
