import os
import re
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Query, Body, UploadFile, File, Form, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from core.database import db
from core.auth import get_current_user
from core.services import create_notification, log_activity
from core.mail_dispatch import dispatch_email, get_email_credentials, test_smtp_connection
from core.whatsapp_service import (
    get_whatsapp_config,
    verify_meta_signature,
    normalize_phone_number,
    send_whatsapp_text,
    send_whatsapp_template,
    send_whatsapp_media,
    download_and_store_meta_media,
    test_whatsapp_connection,
)

logger = logging.getLogger("crm_communication")

router = APIRouter(prefix="/crm", tags=["CRM Communication"])

crm_calls_col = db["crm_calls"]
crm_whatsapp_col = db["crm_whatsapp_messages"]
crm_emails_col = db["crm_emails"]
crm_templates_col = db["crm_templates"]
leads_col = db["leads"]
clients_col = db["users"]
cases_col = db["cases"]
audit_logs_col = db["audit_logs"]
follow_ups_col = db["follow_ups"]

RECORDINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "call_recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True)

ATTACHMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "email_attachments")
os.makedirs(ATTACHMENTS_DIR, exist_ok=True)


# Helper for role check
def _is_admin(user: dict) -> bool:
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in ["admin", "admin_owner", "super_admin"] or rbac in ["admin", "admin_owner", "super_admin"]


def _is_sales_person(user: dict) -> bool:
    sales_roles = [
        "partner", "external_partner", "external_salesperson",
        "sales_executive", "sr_sales_executive", "senior_sales_executive",
        "sales_rep", "sales_person", "sales", "internal_salesperson", "sales_consultant",
        "sales_manager", "sales_head", "sales_agent"
    ]
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in sales_roles or rbac in sales_roles


def _is_manager_or_admin(user: dict) -> bool:
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in ["admin", "admin_owner", "super_admin", "sales_manager", "sales_head"] or rbac in ["admin_owner", "sales_manager", "sales_head", "admin", "super_admin"]


# ────────────────────────────────────────────────────────────
# 1. CALLING MODULE & RECORDING STORAGE
# ────────────────────────────────────────────────────────────

@router.post("/calls/recordings/upload")
async def upload_call_recording(
    file: Optional[UploadFile] = File(None),
    audio_base64: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload and securely store audio recording file for a call (both incoming and outgoing)"""
    file_id = str(uuid.uuid4())
    ext = "webm"
    saved_filename = f"rec_{file_id}.{ext}"

    if file:
        orig_name = file.filename or ""
        if "." in orig_name:
            ext = orig_name.rsplit(".", 1)[-1].lower()
            saved_filename = f"rec_{file_id}.{ext}"
        target_path = os.path.join(RECORDINGS_DIR, saved_filename)
        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)
        file_size = len(content)
    elif audio_base64:
        # If passed as data URL or base64
        if "base64," in audio_base64:
            header, base64_str = audio_base64.split("base64,", 1)
            if "audio/mp3" in header or "audio/mpeg" in header:
                ext = "mp3"
            elif "audio/wav" in header:
                ext = "wav"
            elif "audio/webm" in header:
                ext = "webm"
            saved_filename = f"rec_{file_id}.{ext}"
        else:
            base64_str = audio_base64
        
        target_path = os.path.join(RECORDINGS_DIR, saved_filename)
        content = base64.b64decode(base64_str)
        with open(target_path, "wb") as f:
            f.write(content)
        file_size = len(content)
    else:
        raise HTTPException(status_code=400, detail="No audio file or base64 data provided")

    recording_url = f"/api/crm/calls/recordings/{saved_filename}"
    return {
        "success": True,
        "filename": saved_filename,
        "recording_url": recording_url,
        "file_size": file_size
    }


@router.get("/calls/recordings/{filename}")
async def get_call_recording(filename: str):
    """Stream or download call audio recording with proper audio MIME type"""
    # Sanitize filename to prevent directory traversal
    clean_filename = os.path.basename(filename)
    file_path = os.path.join(RECORDINGS_DIR, clean_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Recording not found")

    media_type = "audio/webm"
    if clean_filename.endswith(".mp3"):
        media_type = "audio/mpeg"
    elif clean_filename.endswith(".wav"):
        media_type = "audio/wav"
    elif clean_filename.endswith(".ogg") or clean_filename.endswith(".opus"):
        media_type = "audio/ogg"

    return FileResponse(file_path, media_type=media_type, headers={"Accept-Ranges": "bytes"})


@router.post("/calls")
async def log_call(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Log a phone call (Incoming or Outgoing) with lead or client and attach call recording"""
    lead_id = data.get("lead_id")
    client_id = data.get("client_id")
    
    # Verify access if sales person
    if _is_sales_person(current_user) and lead_id:
        lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "assigned_to": 1, "name": 1, "phone": 1})
        if lead and lead.get("assigned_to") and lead["assigned_to"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can only log calls for your assigned leads")
    
    lead_name = data.get("lead_name", "")
    lead_phone = data.get("lead_phone", "")
    if lead_id and not lead_name:
        lead_doc = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1, "phone": 1})
        if lead_doc:
            lead_name = lead_doc.get("name", "")
            lead_phone = lead_doc.get("phone", "")

    direction = data.get("direction", "outgoing")  # outgoing or incoming
    status = data.get("status", "connected")  # connected, not_connected, missed, busy, rejected
    duration_s = int(data.get("duration_seconds", 0))

    call_doc = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "client_id": client_id,
        "lead_name": lead_name,
        "lead_phone": lead_phone,
        "sales_person_id": current_user["id"],
        "sales_person_name": current_user.get("name", ""),
        "direction": direction,
        "start_time": data.get("start_time", datetime.now(timezone.utc).isoformat()),
        "end_time": data.get("end_time"),
        "duration_seconds": duration_s,
        "status": status,
        "outcome": data.get("outcome", "follow_up_required"),  # interested, follow_up_required, not_interested, call_back, wrong_number, no_response, converted, payment_discussion
        "notes": data.get("notes", ""),
        "recording_url": data.get("recording_url", ""),
        "transcript": data.get("transcript", ""),
        "ai_summary": data.get("ai_summary", ""),
        "ai_sentiment": data.get("ai_sentiment", "Neutral"),  # Positive, Neutral, Negative
        "next_best_action": data.get("next_best_action", ""),
        "created_at": datetime.now(timezone.utc),
    }
    await crm_calls_col.insert_one(call_doc)

    # Automatically process structured AI summary & genuine transcription status
    try:
        from core.call_intelligence_service import process_call_intelligence
        intel_doc = await process_call_intelligence(call_doc["id"])
        if intel_doc:
            call_doc.update(intel_doc)
    except Exception as e:
        logger.warning(f"Auto call intelligence processing skipped: {e}")

    # Update lead's last contacted timestamp & increment score if connected
    if lead_id:
        update_fields = {"last_contacted_at": datetime.now(timezone.utc)}
        if call_doc["status"] == "connected":
            update_fields["last_connected_at"] = datetime.now(timezone.utc)
        await leads_col.update_one({"id": lead_id}, {"$set": update_fields, "$inc": {"call_count": 1}})
    
    # Log to unified activity
    mins = duration_s // 60
    secs = duration_s % 60
    dur_str = f"{mins:02d}:{secs:02d}"
    rec_info = " [Recording Attached]" if call_doc.get("recording_url") else ""
    await log_activity(
        user_id=current_user["id"],
        user_name=current_user.get("name", "Sales Person"),
        action="call_logged",
        entity_type="lead" if lead_id else "client",
        entity_id=lead_id or client_id,
        details=f"{direction.title()} Call ({call_doc['status']} - {call_doc['outcome']}) - Duration: {dur_str}. Notes: {call_doc['notes']}{rec_info}"
    )

    return {
        "message": "Call logged successfully",
        "call_id": call_doc["id"],
        "recording_url": call_doc.get("recording_url"),
        "ai_summary": call_doc.get("ai_summary", ""),
        "ai_summary_structured": call_doc.get("ai_summary_structured"),
        "transcription_status": call_doc.get("transcription_status", "unavailable"),
    }


@router.get("/calls")
async def get_calls(
    lead_id: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    sales_person_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    limit: int = Query(100),
    current_user: dict = Depends(get_current_user)
):
    """Get calls list with role filtering, date ranges, and full text search."""
    query: Dict[str, Any] = {}
    if lead_id:
        query["lead_id"] = lead_id
    if client_id:
        query["client_id"] = client_id
    if status and status != "all":
        query["status"] = status
    if direction and direction != "all":
        query["direction"] = direction

    # Search filter across client name, phone, advisor name, notes, summary, and transcript
    if search and search.strip():
        s_regex = {"$regex": re.escape(search.strip()), "$options": "i"}
        search_or = [
            {"lead_name": s_regex},
            {"client_name": s_regex},
            {"lead_phone": s_regex},
            {"client_phone": s_regex},
            {"sales_person_name": s_regex},
            {"notes": s_regex},
            {"transcript": s_regex},
            {"ai_summary": s_regex},
            {"ai_summary_structured.main_discussion": s_regex},
        ]
        if query:
            query = {"$and": [query, {"$or": search_or}]}
        else:
            query = {"$or": search_or}

    # Date range filters (from_date / to_date)
    if from_date or to_date:
        date_q = {}
        if from_date:
            try:
                date_q["$gte"] = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                pass
        if to_date:
            try:
                date_q["$lte"] = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            except Exception:
                pass
        if date_q:
            if "$and" in query:
                query["$and"].append({"created_at": date_q})
            elif query:
                query = {"$and": [query, {"created_at": date_q}]}
            else:
                query["created_at"] = date_q
    
    # RBAC Enforcement: Non-admin sales reps only see their assigned leads or own calls
    if not _is_admin(current_user):
        uid = str(current_user.get("id") or "").strip()
        uemail = str(current_user.get("email") or "").strip().lower()
        uname = str(current_user.get("name") or "").strip()
        lead_assign_criteria = []
        if uid:
            lead_assign_criteria.extend([
                {"assigned_to": uid},
                {"assigned_sales_rep_id": uid},
                {"sales_person_id": uid},
                {"block_assigned_to": uid},
                {"created_by": uid}
            ])
        if uemail:
            lead_assign_criteria.extend([
                {"assigned_to": uemail},
                {"assigned_to_email": uemail}
            ])
        if uname:
            lead_assign_criteria.append({"assigned_to_name": uname})
            lead_assign_criteria.append({"assigned_to_name": {"$regex": f"^{re.escape(uname)}$", "$options": "i"}})

        assigned_leads = await leads_col.find(
            {"$or": lead_assign_criteria},
            {"id": 1}
        ).to_list(1000)
        assigned_lead_ids = [l["id"] for l in assigned_leads if l.get("id")]

        call_scope = [{"sales_person_id": uid}]
        if assigned_lead_ids:
            call_scope.append({"lead_id": {"$in": assigned_lead_ids}})

        if "$and" in query:
            query["$and"].append({"$or": call_scope})
        elif query:
            query = {"$and": [query, {"$or": call_scope}]}
        else:
            query = {"$or": call_scope}
    elif sales_person_id and sales_person_id != "all" and _is_manager_or_admin(current_user):
        if "$and" in query:
            query["$and"].append({"sales_person_id": sales_person_id})
        elif query:
            query = {"$and": [query, {"sales_person_id": sales_person_id}]}
        else:
            query["sales_person_id"] = sales_person_id
    
    limit_val = int(limit.default if hasattr(limit, 'default') else (limit or 100))
    calls = await crm_calls_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit_val)
    for c in calls:
        if isinstance(c.get("created_at"), datetime):
            c["created_at"] = c["created_at"].isoformat()
        if not c.get("transcription_status"):
            c["transcription_status"] = "completed" if (c.get("transcript") or "").strip() else "unavailable"
    return calls


@router.get("/calls/{call_id}")
async def get_single_call(call_id: str, current_user: dict = Depends(get_current_user)):
    """Get single call record by ID with full AI summary and conversation transcript."""
    query_conditions = [{"id": call_id}]
    try:
        from bson import ObjectId
        query_conditions.append({"_id": ObjectId(call_id)})
    except Exception:
        pass

    call = await crm_calls_col.find_one({"$or": query_conditions})
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")

    if not _is_admin(current_user):
        uid = current_user.get("id")
        if call.get("sales_person_id") != uid:
            lead = await leads_col.find_one({"id": call.get("lead_id")}, {"assigned_to": 1})
            if not lead or lead.get("assigned_to") != uid:
                raise HTTPException(status_code=403, detail="Access denied to this call record")

    if "_id" in call:
        call["_id"] = str(call["_id"])
    if "id" not in call:
        call["id"] = call_id
    if isinstance(call.get("created_at"), datetime):
        call["created_at"] = call["created_at"].isoformat()
    return call


@router.post("/calls/{call_id}/ai-summary")
async def generate_call_ai_summary(call_id: str, current_user: dict = Depends(get_current_user)):
    """Generate or refresh structured AI call summary (Main Discussion, Client Requirements, Concerns, Next Steps)"""
    query_conditions = [{"id": call_id}]
    try:
        from bson import ObjectId
        query_conditions.append({"_id": ObjectId(call_id)})
    except Exception:
        pass

    call = await crm_calls_col.find_one({"$or": query_conditions})
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")

    resolved_call_id = call.get("id") or str(call.get("_id") or call_id)
    updated_call = None
    try:
        from core.call_intelligence_service import process_call_intelligence
        updated_call = await process_call_intelligence(resolved_call_id)
    except Exception as e:
        logger.warning(f"Error during AI summary generation for {resolved_call_id}: {e}")

    if not updated_call:
        from core.call_intelligence_service import _heuristic_summary_extraction
        heuristic = _heuristic_summary_extraction(call)
        concerns = heuristic.get("concerns_objections", [])
        next_steps = heuristic.get("next_steps", ["Follow up with client"])
        updated_call = {
            **call,
            "ai_summary": heuristic.get("executive_summary", ""),
            "ai_summary_structured": {
                **heuristic,
                "concerns": concerns,
                "concerns_objections": concerns,
                "next_steps": next_steps,
            },
            "ai_sentiment": heuristic.get("sentiment", "Neutral"),
            "next_best_action": next_steps[0] if next_steps else "Follow up with client",
            "transcription_status": "completed" if (call.get("transcript") or "").strip() else "unavailable",
            "transcription_status_reason": "Full conversation transcript uploaded" if (call.get("transcript") or "").strip() else "Audio stream not transcribed / No dialogue transcript was attached.",
        }

    return {
        "success": True,
        "id": resolved_call_id,
        "call_id": resolved_call_id,
        "ai_summary": updated_call.get("ai_summary", ""),
        "ai_summary_structured": updated_call.get("ai_summary_structured", {}),
        "ai_sentiment": updated_call.get("ai_sentiment", "Neutral"),
        "next_best_action": updated_call.get("next_best_action", "Follow up with client"),
        "transcription_status": updated_call.get("transcription_status", "unavailable"),
        "transcription_status_reason": updated_call.get("transcription_status_reason", ""),
    }


@router.post("/calls/{call_id}/transcript")
async def update_call_transcript(
    call_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Save or attach complete call transcript, and re-generate AI summary immediately."""
    query_conditions = [{"id": call_id}]
    try:
        from bson import ObjectId
        query_conditions.append({"_id": ObjectId(call_id)})
    except Exception:
        pass

    call = await crm_calls_col.find_one({"$or": query_conditions})

    # If call record not found directly, check if call_id is a lead_id or if lead_id was provided
    if not call:
        lead_id = payload.get("lead_id") or call_id
        lead_lookup = [{"id": lead_id}]
        try:
            from bson import ObjectId
            lead_lookup.append({"_id": ObjectId(lead_id)})
        except Exception:
            pass
        lead = await leads_col.find_one({"$or": lead_lookup})
        if lead:
            resolved_lead_id = lead.get("id") or str(lead.get("_id"))
            # Find latest call for this lead or create a new call record
            call = await crm_calls_col.find_one({"lead_id": resolved_lead_id}, sort=[("created_at", -1)])
            if not call:
                new_call_id = str(uuid.uuid4())
                call = {
                    "id": new_call_id,
                    "lead_id": resolved_lead_id,
                    "lead_name": lead.get("name", "Client"),
                    "lead_phone": lead.get("phone", ""),
                    "sales_person_id": current_user.get("id"),
                    "sales_person_name": current_user.get("name", "LEAMSS Consultant"),
                    "direction": "outgoing",
                    "duration_seconds": 0,
                    "status": "connected",
                    "outcome": "interested",
                    "notes": payload.get("notes") or "Call transcript attached via CRM",
                    "transcript": str(payload.get("transcript") or "").strip(),
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                await crm_calls_col.insert_one(call)
                call_id = new_call_id

    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")

    resolved_call_id = call.get("id") or str(call.get("_id") or call_id)
    transcript = str(payload.get("transcript") or "").strip()
    notes = str(payload.get("notes") or "").strip()

    updates: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
    if transcript:
        updates["transcript"] = transcript
        updates["transcription_status"] = "completed"
        updates["transcription_status_reason"] = "Full conversation transcript uploaded"
    if notes:
        updates["notes"] = notes

    update_query = {"$or": [{"id": resolved_call_id}]}
    try:
        from bson import ObjectId
        update_query["$or"].append({"_id": ObjectId(resolved_call_id)})
    except Exception:
        pass

    await crm_calls_col.update_one(update_query, {"$set": updates})

    # AI Intelligence processing with bulletproof fallback
    updated_call = None
    try:
        from core.call_intelligence_service import process_call_intelligence
        updated_call = await process_call_intelligence(resolved_call_id)
    except Exception as e:
        logger.warning(f"Error during AI intelligence processing for call {resolved_call_id}: {e}")

    if not updated_call:
        from core.call_intelligence_service import _heuristic_summary_extraction
        merged_doc = {**call, **updates}
        heuristic = _heuristic_summary_extraction(merged_doc)
        concerns = heuristic.get("concerns_objections", [])
        next_steps = heuristic.get("next_steps", ["Follow up with client"])
        updated_call = {
            **merged_doc,
            "transcription_status": "completed" if transcript else "unavailable",
            "transcription_status_reason": "Full conversation transcript uploaded" if transcript else "Audio stream not transcribed / No dialogue transcript was attached.",
            "ai_summary": heuristic.get("executive_summary", ""),
            "ai_summary_structured": {
                **heuristic,
                "concerns": concerns,
                "concerns_objections": concerns,
                "next_steps": next_steps,
            },
            "ai_sentiment": heuristic.get("sentiment", "Neutral"),
            "next_best_action": next_steps[0] if next_steps else "Follow up with client",
        }

    return {
        "success": True,
        "message": "Call transcript saved and intelligence refreshed successfully",
        "id": resolved_call_id,
        "call_id": resolved_call_id,
        "transcript": transcript or call.get("transcript", ""),
        "transcription_status": updated_call.get("transcription_status") if updated_call else "completed",
        "transcription_status_reason": updated_call.get("transcription_status_reason") if updated_call else "Full conversation transcript uploaded",
        "ai_summary": updated_call.get("ai_summary") if updated_call else "",
        "ai_summary_structured": updated_call.get("ai_summary_structured") if updated_call else {},
        "ai_sentiment": updated_call.get("ai_sentiment") if updated_call else "Neutral",
        "next_best_action": updated_call.get("next_best_action") if updated_call else "Follow up with client",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


# ────────────────────────────────────────────────────────────
# 2. WHATSAPP MODULE
# ────────────────────────────────────────────────────────────

@router.get("/whatsapp/inbox")
async def get_whatsapp_inbox(
    tab: str = Query("all"),  # all, unread, replied, waiting_for_reply
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get WhatsApp conversations inbox organized by lead/client thread"""
    match_query: Dict[str, Any] = {}
    if not _is_admin(current_user):
        uid = str(current_user.get("id") or "").strip()
        uemail = str(current_user.get("email") or "").strip().lower()
        uname = str(current_user.get("name") or "").strip()
        lead_assign_criteria = []
        if uid:
            lead_assign_criteria.extend([
                {"assigned_to": uid},
                {"assigned_sales_rep_id": uid},
                {"sales_person_id": uid},
                {"block_assigned_to": uid},
                {"created_by": uid}
            ])
        if uemail:
            lead_assign_criteria.extend([
                {"assigned_to": uemail},
                {"assigned_to_email": uemail}
            ])
        if uname:
            lead_assign_criteria.append({"assigned_to_name": uname})
            lead_assign_criteria.append({"assigned_to_name": {"$regex": f"^{re.escape(uname)}$", "$options": "i"}})

        assigned_leads = await leads_col.find(
            {"$or": lead_assign_criteria},
            {"id": 1, "phone": 1, "whatsapp_number": 1}
        ).to_list(1000)
        assigned_lead_ids = [l["id"] for l in assigned_leads if l.get("id")]
        assigned_phones = [l.get("phone") for l in assigned_leads if l.get("phone")] + [l.get("whatsapp_number") for l in assigned_leads if l.get("whatsapp_number")]

        wa_or = [{"sales_person_id": uid}]
        if assigned_lead_ids:
            wa_or.append({"lead_id": {"$in": assigned_lead_ids}})
        if assigned_phones:
            wa_or.append({"phone": {"$in": assigned_phones}})

        match_query = {"$or": wa_or}
    
    pipeline = [
        {"$match": match_query} if match_query else {"$match": {}},
        {"$sort": {"created_at": -1}},
        {
            "$group": {
                "_id": {"$ifNull": ["$lead_id", "$client_id"]},
                "last_message": {"$first": "$$ROOT"},
                "unread_count": {
                    "$sum": {"$cond": [{"$and": [{"$eq": ["$direction", "inbound"]}, {"$eq": ["$read", False]}]}, 1, 0]}
                },
                "total_messages": {"$sum": 1}
            }
        },
        {"$sort": {"last_message.created_at": -1}},
        {"$limit": 100}
    ]
    
    threads_raw = await crm_whatsapp_col.aggregate(pipeline).to_list(100)
    results = []
    
    for t in threads_raw:
        last_msg = t["last_message"]
        lead_id = last_msg.get("lead_id")
        lead_info = None
        if lead_id:
            lead_info = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1, "phone": 1, "whatsapp_number": 1, "stage": 1, "assigned_to": 1})
        
        direction = last_msg.get("direction", "outbound")
        # determine status: waiting_for_reply (last is outbound), replied (last is inbound & answered), unread
        thread_status = "unread" if t["unread_count"] > 0 else "waiting_for_reply" if direction == "outbound" else "replied"
        
        if tab == "unread" and t["unread_count"] == 0:
            continue
        if tab == "waiting_for_reply" and direction != "outbound":
            continue
        if tab == "replied" and direction != "inbound":
            continue
        
        contact_name = (lead_info.get("name") if lead_info else None) or last_msg.get("contact_name") or last_msg.get("phone", "WhatsApp Contact")
        contact_phone = (lead_info.get("whatsapp_number") or lead_info.get("phone") if lead_info else None) or last_msg.get("phone", "")

        if search:
            s = search.lower()
            if s not in contact_name.lower() and s not in contact_phone.lower():
                continue

        results.append({
            "thread_id": t["_id"],
            "lead_id": lead_id,
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "lead_stage": lead_info.get("stage", "new") if lead_info else "",
            "unread_count": t["unread_count"],
            "thread_status": thread_status,
            "last_message_text": last_msg.get("text", ""),
            "last_message_time": last_msg.get("created_at").isoformat() if isinstance(last_msg.get("created_at"), datetime) else str(last_msg.get("created_at")),
            "last_direction": direction
        })

    return results


@router.get("/whatsapp/thread/{entity_id}")
async def get_whatsapp_thread(entity_id: str, current_user: dict = Depends(get_current_user)):
    """Get all WhatsApp messages in a conversation thread"""
    query = {"$or": [{"lead_id": entity_id}, {"client_id": entity_id}, {"phone": entity_id}]}
    if _is_sales_person(current_user):
        # Lead check
        lead = await leads_col.find_one({"id": entity_id}, {"_id": 0, "assigned_to": 1})
        if lead and lead.get("assigned_to") and lead["assigned_to"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to view messages for this lead")

    messages = await crm_whatsapp_col.find(query).sort("created_at", 1).to_list(200)
    for m in messages:
        if "_id" in m:
            if not m.get("id"):
                m["id"] = str(m["_id"])
            del m["_id"]
        for dt_key in ["created_at", "confirmed_at", "status_updated_at"]:
            if isinstance(m.get(dt_key), datetime):
                m[dt_key] = m[dt_key].isoformat()
    
    # Mark inbound as read
    await crm_whatsapp_col.update_many(
        {"$or": [{"lead_id": entity_id}, {"client_id": entity_id}], "direction": "inbound", "read": False},
        {"$set": {"read": True}}
    )
    return messages


@router.get("/whatsapp/webhook")
async def verify_whatsapp_webhook(
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """Meta Webhook verification handshake."""
    cfg = await get_whatsapp_config()
    expected_token = cfg.get("verify_token") or "leamss_wa_verify_token_2026"
    
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Meta WhatsApp webhook challenge successfully verified.")
        return PlainTextResponse(content=hub_challenge or "", status_code=200)
    
    logger.warning("WhatsApp webhook verification failed: Token mismatch or invalid mode.")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/whatsapp/webhook")
async def process_whatsapp_webhook(request: Request):
    """Meta Webhook event processor for incoming messages, media, and delivery statuses."""
    raw_body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256")
    cfg = await get_whatsapp_config()

    # Validate HMAC signature if app_secret is set
    if not verify_meta_signature(raw_body, sig_header, cfg.get("app_secret", "")):
        logger.error("Meta Webhook signature validation failed!")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored_non_json"}

    now = datetime.now(timezone.utc)

    # Process all entries and changes
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
            val = change.get("value", {})
            
            # 1. STATUS UPDATES (sent, delivered, read, failed)
            for status_obj in val.get("statuses", []):
                wamid = status_obj.get("id")
                new_status = status_obj.get("status")  # sent, delivered, read, failed
                
                if wamid and new_status:
                    update_fields: Dict[str, Any] = {"status": new_status, "status_updated_at": now}
                    if new_status == "read":
                        update_fields["read"] = True
                    if new_status == "failed":
                        errors = status_obj.get("errors", [])
                        err_msg = errors[0].get("message") if errors else "Failed delivery"
                        update_fields["error_message"] = err_msg

                    await crm_whatsapp_col.update_many(
                        {"meta_message_id": wamid},
                        {"$set": update_fields}
                    )
                    logger.info("WhatsApp status updated: %s -> %s", wamid, new_status)

            # 2. INCOMING CLIENT MESSAGES
            messages = val.get("messages", [])
            contacts = val.get("contacts", [])
            sender_profile_name = ""
            if contacts and len(contacts) > 0:
                sender_profile_name = contacts[0].get("profile", {}).get("name", "")

            for msg in messages:
                wamid = msg.get("id")
                if not wamid:
                    continue

                # De-duplication check (Meta webhooks may retry)
                existing = await crm_whatsapp_col.find_one({"meta_message_id": wamid})
                if existing:
                    continue

                sender_phone = normalize_phone_number(msg.get("from"))
                if not sender_phone:
                    continue

                last10 = sender_phone[-10:] if len(sender_phone) >= 10 else sender_phone
                
                # Match Lead or Client
                lead = await leads_col.find_one({
                    "$or": [
                        {"phone": {"$regex": last10}},
                        {"whatsapp_number": {"$regex": last10}}
                    ]
                })

                lead_id = None
                client_id = None
                contact_name = sender_profile_name or "WhatsApp Client"
                sales_person_id = None
                sales_person_name = "LEAMSS Consultant"

                if lead:
                    lead_id = lead["id"]
                    contact_name = lead.get("name") or contact_name
                    sales_person_id = lead.get("assigned_to")
                    sales_person_name = lead.get("assigned_to_name") or "LEAMSS Consultant"
                else:
                    # Check users/clients collection
                    client = await clients_col.find_one({
                        "$or": [
                            {"phone": {"$regex": last10}},
                            {"whatsapp_number": {"$regex": last10}}
                        ]
                    })
                    if client:
                        client_id = client.get("id") or str(client.get("_id"))
                        contact_name = client.get("name") or contact_name
                    else:
                        # Auto-provision new lead in "New" stage
                        lead_id = str(uuid.uuid4())
                        new_lead_doc = {
                            "id": lead_id,
                            "name": contact_name,
                            "phone": sender_phone,
                            "whatsapp_number": sender_phone,
                            "source": "WhatsApp Inbound",
                            "stage": "New",
                            "assigned_to": None,
                            "assigned_to_name": "Unassigned",
                            "created_at": now,
                            "last_contacted_at": now,
                            "last_inbound_at": now
                        }
                        await leads_col.insert_one(new_lead_doc)

                msg_type = msg.get("type", "text")
                text_content = ""
                media_meta = None
                media_filename = ""
                media_mime = None
                media_res = None

                if msg_type == "text":
                    text_content = msg.get("text", {}).get("body", "")
                elif msg_type in ["image", "document", "audio", "video"]:
                    media_meta = msg.get(msg_type, {})
                    media_id = media_meta.get("id")
                    media_filename = media_meta.get("filename", "")
                    text_content = media_meta.get("caption") or f"[{msg_type.capitalize()} Attachment]"
                    
                    # Download & store in GridFS
                    if media_id and cfg.get("access_token"):
                        media_res = await download_and_store_meta_media(media_id, cfg["access_token"])
                elif msg_type == "button":
                    text_content = msg.get("button", {}).get("text", "")
                elif msg_type == "interactive":
                    interactive_obj = msg.get("interactive", {})
                    if "button_reply" in interactive_obj:
                        text_content = interactive_obj["button_reply"].get("title", "")
                    elif "list_reply" in interactive_obj:
                        text_content = interactive_obj["list_reply"].get("title", "")
                else:
                    text_content = f"[{msg_type.capitalize()} message received]"

                msg_doc = {
                    "id": str(uuid.uuid4()),
                    "meta_message_id": wamid,
                    "lead_id": lead_id,
                    "client_id": client_id,
                    "phone": sender_phone,
                    "contact_name": contact_name,
                    "sales_person_id": sales_person_id,
                    "sales_person_name": sales_person_name,
                    "direction": "inbound",
                    "type": msg_type,
                    "text": text_content,
                    "media_id": media_res.get("file_id") if media_res else None,
                    "media_url": media_res.get("local_url") if media_res else None,
                    "media_mime": media_res.get("mime_type") if media_res else media_mime,
                    "media_filename": media_filename or (media_res.get("filename") if media_res else None),
                    "status": "received",
                    "read": False,
                    "created_at": now
                }
                await crm_whatsapp_col.insert_one(msg_doc)

                # Log activity in client timeline
                await log_activity(
                    user_id=sales_person_id or "system",
                    user_name=sales_person_name,
                    action="whatsapp_received",
                    entity_type="lead" if lead_id else "client",
                    entity_id=lead_id or client_id,
                    details=f"Inbound WhatsApp from {contact_name} ({sender_phone}): {text_content[:60]}..."
                )

                # Update lead timestamps
                if lead_id:
                    await leads_col.update_one(
                        {"id": lead_id},
                        {"$set": {
                            "last_contacted_at": now,
                            "last_inbound_at": now,
                            "whatsapp_last_message": text_content[:100],
                            "whatsapp_last_message_at": now
                        }}
                    )

                logger.info("Processed inbound WhatsApp message from %s (lead=%s)", sender_phone, lead_id)

    return {"status": "ok"}


@router.get("/whatsapp/media/{file_id}")
async def get_whatsapp_media(file_id: str):
    """Stream WhatsApp media stored in MongoDB GridFS."""
    from motor.motor_asyncio import AsyncIOMotorGridFSBucket
    from bson import ObjectId

    try:
        gridfs = AsyncIOMotorGridFSBucket(db, bucket_name="whatsapp_media")
        grid_out = await gridfs.open_download_stream(ObjectId(file_id))
        mime_type = grid_out.metadata.get("mime_type", "application/octet-stream") if grid_out.metadata else "application/octet-stream"

        async def stream_generator():
            while True:
                chunk = await grid_out.readchunk()
                if not chunk:
                    break
                yield chunk

        return StreamingResponse(stream_generator(), media_type=mime_type)
    except Exception as e:
        logger.error(f"Error streaming WhatsApp media {file_id}: {e}")
        raise HTTPException(status_code=404, detail="Media file not found")


@router.post("/whatsapp/media/upload")
async def upload_whatsapp_media(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload outbound media (image, document, audio) to GridFS for WhatsApp dispatch."""
    from motor.motor_asyncio import AsyncIOMotorGridFSBucket
    try:
        content = await file.read()
        mime_type = file.content_type or "application/octet-stream"
        filename = file.filename or "media_upload"

        media_type = "document"
        if mime_type.startswith("image/"):
            media_type = "image"
        elif mime_type.startswith("audio/"):
            media_type = "audio"
        elif mime_type.startswith("video/"):
            media_type = "video"

        gridfs = AsyncIOMotorGridFSBucket(db, bucket_name="whatsapp_media")
        grid_in = gridfs.open_upload_stream(
            filename=filename,
            metadata={"mime_type": mime_type, "uploader_id": current_user.get("id"), "media_type": media_type}
        )
        await grid_in.write(content)
        await grid_in.close()

        file_id = str(grid_in._id)
        media_url = f"/api/crm/whatsapp/media/{file_id}"
        return {
            "file_id": file_id,
            "media_url": media_url,
            "media_type": media_type,
            "filename": filename,
            "size": len(content),
            "mime_type": mime_type
        }
    except Exception as e:
        logger.error(f"Error uploading WhatsApp media: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload media: {e}")


@router.get("/whatsapp/session-status/{lead_id}")
async def get_whatsapp_session_status(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Calculate Meta 24-hour service window status for a lead."""
    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "last_inbound_at": 1, "name": 1, "phone": 1})
    if not lead:
        return {"is_session_active": False, "remaining_seconds": 0, "reason": "lead_not_found"}

    last_inbound = lead.get("last_inbound_at")
    if not last_inbound:
        # Check last inbound in crm_whatsapp_col
        last_msg = await crm_whatsapp_col.find_one(
            {"lead_id": lead_id, "direction": "inbound"},
            sort=[("created_at", -1)]
        )
        if last_msg:
            last_inbound = last_msg.get("created_at")

    if not last_inbound:
        return {
            "is_session_active": False,
            "remaining_seconds": 0,
            "last_inbound_at": None,
            "reason": "no_prior_inbound"
        }

    if isinstance(last_inbound, str):
        try:
            last_inbound = datetime.fromisoformat(last_inbound.replace("Z", "+00:00"))
        except Exception:
            last_inbound = None

    if not last_inbound:
        return {"is_session_active": False, "remaining_seconds": 0}

    now = datetime.now(timezone.utc)
    if last_inbound.tzinfo is None:
        last_inbound = last_inbound.replace(tzinfo=timezone.utc)

    elapsed_seconds = (now - last_inbound).total_seconds()
    is_active = elapsed_seconds < 86400  # 24 hours
    remaining = max(0, int(86400 - elapsed_seconds))

    return {
        "is_session_active": is_active,
        "remaining_seconds": remaining,
        "remaining_hours": round(remaining / 3600, 1),
        "last_inbound_at": last_inbound.isoformat()
    }


@router.get("/whatsapp/config")
async def get_whatsapp_admin_config(current_user: dict = Depends(get_current_user)):
    """Get WhatsApp Cloud API configuration for admin settings."""
    cfg = await get_whatsapp_config()
    token = cfg.get("access_token", "")
    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 12 else token
    return {
        "phone_number_id": cfg.get("phone_number_id", ""),
        "waba_id": cfg.get("waba_id", ""),
        "access_token": masked_token,
        "is_token_set": bool(token),
        "app_secret": "***" if cfg.get("app_secret") else "",
        "is_app_secret_set": bool(cfg.get("app_secret")),
        "verify_token": cfg.get("verify_token", "leamss_wa_verify_token_2026"),
        "sender_display": cfg.get("sender_display", "+91 77383 52427 (LEAMSS Official)"),
        "is_configured": cfg.get("is_configured", False)
    }


@router.put("/whatsapp/config")
async def update_whatsapp_admin_config(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Update WhatsApp Cloud API settings in email_settings collection."""
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin permissions required")

    updates = {}
    if "phone_number_id" in data:
        updates["whatsapp_phone_number_id"] = str(data["phone_number_id"]).strip()
    if "waba_id" in data:
        updates["whatsapp_waba_id"] = str(data["waba_id"]).strip()
    if "access_token" in data and data["access_token"] and not str(data["access_token"]).startswith("***"):
        updates["whatsapp_access_token"] = str(data["access_token"]).strip()
    if "app_secret" in data and data["app_secret"] and not str(data["app_secret"]).startswith("***"):
        updates["whatsapp_app_secret"] = str(data["app_secret"]).strip()
    if "verify_token" in data:
        updates["whatsapp_verify_token"] = str(data["verify_token"]).strip()
    if "sender_display" in data:
        updates["whatsapp_sender_display"] = str(data["sender_display"]).strip()

    if updates:
        await db["email_settings"].update_one({"id": "global"}, {"$set": updates}, upsert=True)

    return {"message": "WhatsApp Cloud API configuration updated successfully"}


@router.post("/whatsapp/config/test")
async def test_whatsapp_admin_connection(current_user: dict = Depends(get_current_user)):
    """Test live Meta WhatsApp Cloud API connection."""
    res = await test_whatsapp_connection()
    return res


@router.post("/whatsapp/send")
async def send_whatsapp_message(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Send WhatsApp message, template, or media via Meta Cloud API"""
    lead_id = data.get("lead_id")
    client_id = data.get("client_id")
    phone = data.get("phone", "")
    text = data.get("text", "")
    template_name = data.get("template_name")
    template_components = data.get("template_components")
    media_url = data.get("media_url")
    media_type = data.get("media_type")  # image, document, audio, video
    media_filename = data.get("media_filename", "")

    mode = data.get("mode", "web")
    contact_name = data.get("contact_name", "")
    if lead_id and not contact_name:
        lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1, "phone": 1, "whatsapp_number": 1})
        if lead:
            contact_name = lead.get("name", "")
            if not phone:
                phone = lead.get("whatsapp_number") or lead.get("phone", "")
    if client_id and not contact_name:
        client = await clients_col.find_one({"id": client_id}, {"_id": 0, "name": 1, "phone": 1, "whatsapp_number": 1})
        if client:
            contact_name = client.get("name", "")
            if not phone:
                phone = client.get("whatsapp_number") or client.get("phone", "")

    # Normalize phone
    clean_phone = normalize_phone_number(phone)
    if clean_phone:
        phone = clean_phone

    sales_person_name = data.get("sales_person_name") or current_user.get("name") or "Sales Person"

    meta_delivered = False
    meta_message_id = None
    meta_err = None

    # Only attempt Meta Cloud API if explicitly requested (mode == "direct")
    if mode == "direct":
        try:
            cfg = await get_whatsapp_config()
            if cfg.get("is_configured"):
                if template_name:
                    meta_res = await send_whatsapp_template(to_phone=phone, template_name=template_name, components=template_components)
                    meta_message_id = meta_res.get("meta_message_id")
                    meta_delivered = True
                elif media_url and media_type:
                    meta_res = await send_whatsapp_media(to_phone=phone, media_type=media_type, media_url=media_url, caption=text, filename=media_filename)
                    meta_message_id = meta_res.get("meta_message_id")
                    meta_delivered = True
                elif text:
                    meta_res = await send_whatsapp_text(to_phone=phone, text=text)
                    meta_message_id = meta_res.get("meta_message_id")
                    meta_delivered = True
        except Exception as e:
            meta_err = str(e)
            logger.warning(f"Meta WhatsApp Cloud API dispatch error: {e}")

    # Determine status & channel
    is_confirmed = data.get("confirmed") is True or data.get("status") == "sent"
    if meta_delivered:
        msg_status = "delivered"
        channel = "meta_cloud_api"
    elif mode in ["web", "app"]:
        msg_status = "sent" if is_confirmed else "pending_confirmation"
        channel = "whatsapp_web" if mode == "web" else "whatsapp_app"
    elif mode == "direct":
        msg_status = "sent" if is_confirmed else "failed"
        channel = "whatsapp_direct"
    else:
        msg_status = "logged"
        channel = "crm_internal"

    msg_doc = {
        "id": str(uuid.uuid4()),
        "meta_message_id": meta_message_id,
        "lead_id": lead_id,
        "client_id": client_id,
        "phone": phone,
        "contact_name": contact_name,
        "sales_person_id": current_user["id"],
        "sales_person_name": sales_person_name,
        "direction": "outbound",
        "text": text,
        "template_name": template_name,
        "media_url": media_url,
        "media_type": media_type,
        "media_filename": media_filename,
        "status": msg_status,
        "channel": channel,
        "error_message": meta_err,
        "read": True,
        "created_at": datetime.now(timezone.utc)
    }
    await crm_whatsapp_col.insert_one(msg_doc)

    # Always log to activity timeline & salesperson audit log regardless of status (sent, failed, pending)
    tpl_label = f" [Template: {template_name}]" if template_name else ""
    status_tag = "Sent" if msg_status in ["sent", "delivered"] else ("Failed" if msg_status == "failed" else "Pending")

    if msg_status in ["sent", "delivered"]:
        act_action = "whatsapp_sent"
        act_details = f"WhatsApp sent to {contact_name} ({phone}) by {sales_person_name}{tpl_label}: {text[:75]}..."
    elif msg_status == "failed":
        act_action = "whatsapp_failed"
        act_details = f"WhatsApp attempt failed to {contact_name} ({phone}) by {sales_person_name}{tpl_label}: {text[:75]}... [Reason: {meta_err or 'Failed'}]"
    else:
        act_action = "whatsapp_pending"
        act_details = f"WhatsApp initiated via Web (Pending Confirmation) to {contact_name} ({phone}) by {sales_person_name}{tpl_label}: {text[:75]}..."

    await log_activity(
        user_id=current_user["id"],
        user_name=sales_person_name,
        action=act_action,
        entity_type="lead" if lead_id else "client",
        entity_id=lead_id or client_id,
        details=act_details
    )

    if lead_id:
        await leads_col.update_one({"id": lead_id}, {"$set": {"last_contacted_at": datetime.now(timezone.utc)}})
    if client_id:
        await clients_col.update_one({"id": client_id}, {"$set": {"last_contacted_at": datetime.now(timezone.utc)}})

    # Record to Salesperson Activity Audit Log
    try:
        from services.salesperson_activity_service import log_salesperson_activity
        await log_salesperson_activity(
            db=db,
            salesperson_id=current_user["id"],
            salesperson_name=sales_person_name,
            salesperson_email=current_user.get("email"),
            salesperson_role=current_user.get("rbac_role") or current_user.get("role"),
            activity_type="whatsapp",
            client_id=lead_id or client_id,
            client_name=contact_name,
            client_phone=phone,
            title=f"WhatsApp Message to {contact_name}",
            details=f"{text[:120]}... [Template: {template_name}]" if template_name else text[:140],
            metadata={
                "status": msg_status,
                "message_status": msg_status,
                "channel": channel,
                "mode": mode,
                "template": template_name,
                "message_id": msg_doc["id"],
                "client_name": contact_name,
                "salesperson_name": sales_person_name,
                "error_message": meta_err if msg_status == "failed" else None
            }
        )
    except Exception as e:
        logger.warning(f"Error logging whatsapp to salesperson audit: {e}")

    if mode == "direct" and meta_err and not meta_delivered:
        raise HTTPException(status_code=400, detail=meta_err)

    return {
        "message": "WhatsApp Web opened; pending delivery confirmation" if msg_status == "pending_confirmation" else "WhatsApp message recorded in CRM",
        "id": msg_doc["id"],
        "meta_message_id": meta_message_id,
        "status": msg_status,
        "channel": channel,
        "phone": phone,
        "contact_name": contact_name,
        "template_name": template_name,
        "delivered": meta_delivered,
    }


@router.post("/whatsapp/call-log")
async def log_whatsapp_call(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Log an outgoing/incoming WhatsApp call in CRM"""
    lead_id = data.get("lead_id")
    client_id = data.get("client_id")
    phone = data.get("phone", "")
    duration_seconds = int(data.get("duration_seconds", 0) or 0)
    outcome = data.get("outcome", "connected")
    direction = data.get("direction", "outgoing")
    contact_name = data.get("contact_name", "")

    if lead_id and not contact_name:
        lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1, "phone": 1, "whatsapp_number": 1})
        if lead:
            contact_name = lead.get("name", "")
            if not phone:
                phone = lead.get("whatsapp_number") or lead.get("phone", "")

    sales_person_name = data.get("sales_person_name") or current_user.get("name") or "Sales Person"
    notes = data.get("notes") or f"WhatsApp call with {contact_name or 'Client'} ({phone})"

    # 1. Save in crm_calls_col with channel='whatsapp'
    call_doc = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "client_id": client_id,
        "lead_phone": phone,
        "lead_name": contact_name,
        "sales_person_id": current_user["id"],
        "sales_person_name": sales_person_name,
        "direction": direction,
        "channel": "whatsapp",
        "duration_seconds": duration_seconds,
        "status": "connected",
        "outcome": outcome,
        "notes": notes,
        "created_at": datetime.now(timezone.utc)
    }
    await crm_calls_col.insert_one(call_doc)

    # 2. Save in crm_whatsapp_col as call event
    msg_doc = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "client_id": client_id,
        "phone": phone,
        "contact_name": contact_name,
        "sales_person_id": current_user["id"],
        "sales_person_name": sales_person_name,
        "direction": direction,
        "type": "call",
        "text": f"📞 WhatsApp Call ({direction.capitalize()}): {notes}",
        "status": "completed",
        "read": True,
        "created_at": datetime.now(timezone.utc)
    }
    await crm_whatsapp_col.insert_one(msg_doc)

    # 3. Log activity
    await log_activity(
        user_id=current_user["id"],
        user_name=sales_person_name,
        action="whatsapp_call",
        entity_type="lead" if lead_id else "client",
        entity_id=lead_id or client_id,
        details=f"WhatsApp Call ({direction}) to {contact_name} ({phone}) by {sales_person_name}: {notes}"
    )

    # 4. Update last_contacted_at on lead
    if lead_id:
        await leads_col.update_one({"id": lead_id}, {"$set": {"last_contacted_at": datetime.now(timezone.utc)}})

    return {"message": "WhatsApp call logged", "call_id": call_doc["id"], "msg_id": msg_doc["id"]}


@router.post("/whatsapp/templates")
async def create_or_get_templates(data: Optional[dict] = None, current_user: dict = Depends(get_current_user)):
    """Get standard WhatsApp templates or create custom template"""
    default_templates = [
        {
            "id": "wa_tpl_intro",
            "name": "🌟 Welcome & Call Request",
            "category": "Lead Follow-up",
            "body": "Hello {{name}}, thank you for your interest in LEAMSS Immigration Consulting. I am {{sales_person}}, your dedicated Immigration Advisor. When would be a good time for a quick 5-minute call regarding your {{country}} {{service}} profile?"
        },
        {
            "id": "wa_tpl_assessment",
            "name": "📋 Free Assessment Ready",
            "category": "Assessment",
            "body": "Hi {{name}}, this is {{sales_person}} from LEAMSS. Great news! We have reviewed your profile for {{country}} immigration. Would you like me to share your eligibility report or discuss your next steps over a quick call?"
        },
        {
            "id": "wa_tpl_followup",
            "name": "⏰ Quick Check-in Follow-up",
            "category": "Follow-up",
            "body": "Hi {{name}}, {{sales_person}} here from LEAMSS following up on our previous conversation regarding your {{country}} visa application. Do you have any questions I can help clarify today?"
        },
        {
            "id": "wa_tpl_documents",
            "name": "📄 Document Checklist & Submission",
            "category": "Documents",
            "body": "Hello {{name}}, this is {{sales_person}} from LEAMSS. To evaluate your points and proceed with your {{country}} file, please share your updated CV/Resume and latest education degree. Let me know if you need assistance!"
        },
        {
            "id": "wa_tpl_payment_reminder",
            "name": "💳 Retainer & Agreement Next Steps",
            "category": "Closing",
            "body": "Dear {{name}}, this is {{sales_person}} from LEAMSS. Your customized immigration retainer proposal is ready. Please confirm when we can connect to finalize the onboarding process."
        }
    ]
    
    if data and data.get("name") and data.get("body"):
        custom_tpl = {
            "id": str(uuid.uuid4()),
            "name": data["name"],
            "category": data.get("category", "Custom"),
            "body": data["body"],
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc)
        }
        await crm_templates_col.insert_one(custom_tpl)
        return {"message": "Template created", "template": custom_tpl}
    
    custom_saved = await crm_templates_col.find({"type": "whatsapp"}, {"_id": 0}).to_list(50)
    return {"templates": default_templates + custom_saved}


# ────────────────────────────────────────────────────────────
# 3. EMAIL MODULE (REAL DELIVERY + ADMIN TEMPLATES + INBOUND THREADING)
# ────────────────────────────────────────────────────────────

email_templates_col = db["email_templates"]


def _user_query(current_user: dict) -> dict:
    uid = str(current_user.get("id") or "").strip()
    uemail = str(current_user.get("email") or "").strip().lower()
    parts = []
    if uid:
        parts.append({"id": uid})
        parts.append({"email": uid.lower()})
        try:
            from bson import ObjectId
            if ObjectId.is_valid(uid):
                parts.append({"_id": ObjectId(uid)})
        except Exception:
            pass
    if uemail:
        parts.append({"email": uemail})
        parts.append({"mailbox_settings.smtp_user": uemail})
        parts.append({"mailbox_settings.sender_email": uemail})
    return {"$or": parts} if parts else {"id": "__invalid__"}


@router.get("/emails/service-status")
async def get_email_service_status(current_user: dict = Depends(get_current_user)):
    """Check active email delivery credentials status (SMTP / Resend) with personal mailbox status."""
    creds = await get_email_credentials(user_id=current_user.get("id"), sender_email=current_user.get("email"))

    # Also check user's personal mailbox doc
    user_doc = await db["users"].find_one(_user_query(current_user), {"mailbox_settings": 1, "email": 1, "name": 1})
    m_settings = (user_doc or {}).get("mailbox_settings") or {}
    has_personal = bool(m_settings.get("smtp_pass"))

    return {
        "has_smtp": creds["has_smtp"],
        "smtp_host": creds["smtp_host"] if creds["has_smtp"] else None,
        "smtp_user": creds["smtp_user"] if creds["has_smtp"] else None,
        "has_resend": creds["has_resend"],
        "sender_email": creds["sender_email"],
        "sender_name": creds["sender_name"],
        "active_provider": creds.get("provider", "none"),
        "is_personal": creds.get("is_personal", False),
        "personal_mailbox": {
            "has_mailbox": has_personal,
            "smtp_host": m_settings.get("smtp_host", "smtp.gmail.com"),
            "smtp_port": m_settings.get("smtp_port", 587),
            "smtp_user": m_settings.get("smtp_user") or current_user.get("email"),
            "sender_name": m_settings.get("sender_name") or current_user.get("name"),
            "sender_email": m_settings.get("sender_email") or current_user.get("email"),
            "last_tested_at": m_settings.get("last_tested_at"),
            "last_test_status": m_settings.get("last_test_status"),
        }
    }


@router.get("/emails/my-mailbox")
async def get_my_mailbox(current_user: dict = Depends(get_current_user)):
    """Get the current sales person's personal mailbox settings."""
    user_doc = await db["users"].find_one(_user_query(current_user), {"_id": 0, "mailbox_settings": 1, "email": 1, "name": 1})
    m = (user_doc or {}).get("mailbox_settings") or {}
    has_pass = bool(m.get("smtp_pass"))
    return {
        "email": current_user.get("email", ""),
        "name": current_user.get("name", ""),
        "smtp_host": m.get("smtp_host", "smtp.gmail.com"),
        "smtp_port": int(m.get("smtp_port", 587)),
        "smtp_user": m.get("smtp_user") or current_user.get("email", ""),
        "sender_name": m.get("sender_name") or current_user.get("name", ""),
        "sender_email": m.get("sender_email") or current_user.get("email", ""),
        "has_password": has_pass,
        "masked_password": "••••••••••••" if has_pass else "",
        "is_configured": has_pass and bool(m.get("smtp_user") or current_user.get("email")),
        "last_tested_at": m.get("last_tested_at"),
        "last_test_status": m.get("last_test_status"),
        "last_test_message": m.get("last_test_message"),
    }


@router.put("/emails/my-mailbox")
async def update_my_mailbox(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Update current sales person's personal mailbox settings."""
    smtp_host = (data.get("smtp_host") or "smtp.gmail.com").strip()
    smtp_port = int(data.get("smtp_port") or 587)
    smtp_user = (data.get("smtp_user") or current_user.get("email", "")).strip()
    sender_name = (data.get("sender_name") or current_user.get("name", "")).strip()
    sender_email = (data.get("sender_email") or smtp_user or current_user.get("email", "")).strip()
    smtp_pass = (data.get("smtp_pass") or "").replace(" ", "").strip()

    user_doc = await db["users"].find_one(_user_query(current_user), {"mailbox_settings": 1})
    curr_m = (user_doc or {}).get("mailbox_settings") or {}
    effective_pass = smtp_pass if smtp_pass else curr_m.get("smtp_pass", "")

    new_settings = {
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_pass": effective_pass,
        "sender_name": sender_name,
        "sender_email": sender_email,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_tested_at": curr_m.get("last_tested_at"),
        "last_test_status": curr_m.get("last_test_status"),
        "last_test_message": curr_m.get("last_test_message"),
    }

    await db["users"].update_many(
        _user_query(current_user),
        {"$set": {"mailbox_settings": new_settings}}
    )

    return {
        "success": True,
        "message": f"Personal mailbox for {sender_email} saved successfully",
        "mailbox": {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_user": smtp_user,
            "sender_name": sender_name,
            "sender_email": sender_email,
            "has_password": bool(effective_pass),
            "is_configured": bool(effective_pass and smtp_user),
        }
    }


@router.post("/emails/my-mailbox/test")
async def test_my_mailbox(data: Optional[dict] = Body(None), current_user: dict = Depends(get_current_user)):
    """Test personal SMTP connection and authentication."""
    data = data or {}
    user_doc = await db["users"].find_one(_user_query(current_user), {"mailbox_settings": 1})
    curr_m = (user_doc or {}).get("mailbox_settings") or {}

    smtp_host = (data.get("smtp_host") or curr_m.get("smtp_host") or "smtp.gmail.com").strip()
    smtp_port = int(data.get("smtp_port") or curr_m.get("smtp_port") or 587)
    smtp_user = (data.get("smtp_user") or curr_m.get("smtp_user") or current_user.get("email", "")).strip()
    smtp_pass = (data.get("smtp_pass") or curr_m.get("smtp_pass") or "").replace(" ", "").strip()

    if not smtp_user:
        raise HTTPException(status_code=400, detail="Mailbox username/email is required")
    if not smtp_pass:
        raise HTTPException(status_code=400, detail="Mailbox password or App Password is required")

    test_res = await test_smtp_connection(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_pass=smtp_pass
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    status_str = "success" if test_res.get("success") else "failed"
    await db["users"].update_many(
        _user_query(current_user),
        {"$set": {
            "mailbox_settings.last_tested_at": now_iso,
            "mailbox_settings.last_test_status": status_str,
            "mailbox_settings.last_test_message": test_res.get("message") or test_res.get("error"),
        }}
    )

    return test_res


@router.get("/emails/templates")
async def get_crm_email_templates(current_user: dict = Depends(get_current_user)):
    """Get active email templates created and managed by Admin"""
    docs = await email_templates_col.find({}, {"_id": 0}).sort("created_at", 1).to_list(200)
    
    # If empty, return standard starters
    if not docs:
        docs = [
            {
                "id": "tpl_welcome_consultation",
                "name": "Welcome Consultation & Assessment",
                "category": "eligible",
                "subject": "Your Immigration Consultation with LEAMSS — Next Steps",
                "body": (
                    "Dear {{name}},\n\n"
                    "Thank you for consulting with LEAMSS Immigration Services. Based on our discussion, "
                    "we have evaluated your profile for {{country}} immigration.\n\n"
                    "We are pleased to share that your qualifications and experience align with active migration pathways. "
                    "Please review the attached program roadmap and next steps.\n\n"
                    "Best regards,\n{{sales_person}}\nLEAMSS Immigration"
                ),
                "is_default": True
            },
            {
                "id": "tpl_proposal_shared",
                "name": "Official Proposal & Service Agreement",
                "category": "proposal",
                "subject": "Official Immigration Service Proposal — {{name}}",
                "body": (
                    "Dear {{name}},\n\n"
                    "We are pleased to present the official service proposal for your {{visa_type}} application with LEAMSS.\n\n"
                    "Please review the fee structure, milestones and terms. Once you confirm your enrollment, "
                    "your dedicated Case Manager will be assigned immediately.\n\n"
                    "Warm regards,\n{{sales_person}}"
                ),
                "is_default": False
            },
            {
                "id": "tpl_payment_acknowledgment",
                "name": "Payment Receipt & Portal Onboarding",
                "category": "onboarding",
                "subject": "Payment Received — Welcome to LEAMSS Client Portal",
                "body": (
                    "Dear {{name}},\n\n"
                    "We have successfully received your enrollment fee. Your Client Portal account has been activated, "
                    "and your case documentation process is now underway.\n\n"
                    "You may log in to upload required certificates and track your stage-by-stage progress.\n\n"
                    "Best regards,\nLEAMSS Client Operations"
                ),
                "is_default": False
            },
            {
                "id": "tpl_warm_followup",
                "name": "Warm Follow-Up & Consultation Booking",
                "category": "follow_up",
                "subject": "Following up on your immigration inquiry — {{name}}",
                "body": (
                    "Hi {{name}},\n\n"
                    "I wanted to quickly check in regarding our conversation on your immigration plans for {{country}}.\n\n"
                    "Do you have any questions regarding the documentation requirements or timeline? "
                    "I would be glad to arrange a 10-minute follow-up call.\n\n"
                    "Warm regards,\n{{sales_person}}"
                ),
                "is_default": False
            }
        ]
    return docs


@router.post("/emails/attachments/upload")
async def upload_email_attachment(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload an attachment or inline image for email composer"""
    file_id = str(uuid.uuid4())
    orig_name = file.filename or "attachment"
    ext = ""
    if "." in orig_name:
        ext = "." + orig_name.rsplit(".", 1)[-1].lower()

    clean_prefix = re.sub(r"[^a-zA-Z0-9_\-]", "_", orig_name.rsplit(".", 1)[0]) if "." in orig_name else "attachment"
    saved_filename = f"{clean_prefix}_{file_id[:8]}{ext}"
    target_path = os.path.join(ATTACHMENTS_DIR, saved_filename)

    content = await file.read()
    with open(target_path, "wb") as f:
        f.write(content)
    file_size = len(content)

    content_type = file.content_type or "application/octet-stream"
    if not content_type or content_type == "application/octet-stream":
        if ext in [".jpg", ".jpeg"]:
            content_type = "image/jpeg"
        elif ext == ".png":
            content_type = "image/png"
        elif ext == ".gif":
            content_type = "image/gif"
        elif ext == ".webp":
            content_type = "image/webp"
        elif ext == ".pdf":
            content_type = "application/pdf"
        elif ext in [".doc", ".docx"]:
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    attachment_url = f"/api/crm/emails/attachments/{saved_filename}"
    return {
        "success": True,
        "id": file_id,
        "filename": orig_name,
        "saved_filename": saved_filename,
        "content_type": content_type,
        "file_size": file_size,
        "size": file_size,
        "url": attachment_url,
        "file_path": target_path
    }


@router.get("/emails/attachments/{filename}")
async def get_email_attachment(filename: str):
    """Download or view an uploaded email attachment / inline photo"""
    clean_filename = os.path.basename(filename)
    file_path = os.path.join(ATTACHMENTS_DIR, clean_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Attachment not found")

    ext = clean_filename.rsplit(".", 1)[-1].lower() if "." in clean_filename else ""
    media_type = "application/octet-stream"
    if ext in ["jpg", "jpeg"]:
        media_type = "image/jpeg"
    elif ext == "png":
        media_type = "image/png"
    elif ext == "gif":
        media_type = "image/gif"
    elif ext == "webp":
        media_type = "image/webp"
    elif ext == ".pdf":
        media_type = "application/pdf"
    elif ext in ["doc", "docx"]:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(file_path, media_type=media_type, filename=clean_filename, headers={"Accept-Ranges": "bytes"})


LEAMSS_LOGO_BASE64 = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEMAAAAqCAYAAADoMebhAAAGZ0lEQVR42u2Z228cVx3HP2dmdvbq3fXu2vH9gu0m7"
    "o049ClIVRLErUICqaTiueo7Qn3oI+EP4AWpj4WCBAi1FEjbB2hJQ6tSalqSUDmJG9vUju3E68vu7HpnZ+dyDg+7Ns49aY3iwhxpNKszZ3+/mc"
    "/8Lt+jEUopRTgA0EIEIYwQRggjhBHCCGHsPRhKAgrXdanVavA5lS7GZ+agFEJolByf9cUFBIpoLE5XVxeGYfwfRYZSCCFoXJxEvfsyPesfMzI6"
    "RrlcYm5uDgCpFEopFDQPdXt7N12wY04FQdOelLsegbuSJkahF/+151HLM1CvsK+7lyAImg6EQAiBgOYhbmNIiJsv2DEndL1pT9PuYOzeh9iNvY"
    "lyatQvTlJ2PPR0DidZIOo36BoewWp4+EGzpkil0IRGPpVsRg0gpcTQNFAKWVnHi8QwEynEjnqkqiUcM0E8EmX2l7/CMgw6Mhk6Jg4S6+luparY"
    "G5EhIzHMBw/zmsrxw8kLZJMJOnv7QeisWBbP/OznrFgVKnWHX//tfZxGA4D6O69w8hc/+U8KXfqQD3/wNc7Ozzc5AO7J5/njj56mEvhUXnqZ0l"
    "/eofDNbzA1+QH27NwNaXT/u4kQGGaUvAG9uXYyhU6kGQMh6M3lSJgmD/b2MNLZwXcOTWyHd3VxBue9k1yuOQghcEYfQ9N0Fk7/vlUffD6e/oiN"
    "SIpssg1nfp726UsMtGc5/Oz3ob/vhjTaMzpD7iiYtM6eH6AJwcxKkTemztOXaydmmtRXl9mYeIKDnXn++d4pUAqnbpM+8hTGuTcp+pLN4hJuZh"
    "+JqIkLZL/3FM7sHJeOfh1m58gNDW4X8T0ruoQQqNZZE01Alzc2WLEq22uK02dIxeOMPvAQ62//FlcIDKeKefAow1GNC5Nvs1bdpLdviMBzm5ES"
    "j9Pz+u8QSrJw+AjlU6dBCFSrWO8pGLqmYehNkxFdx6rXATB1nSPjB3ji0UdwA0nDqVPTInRm00Qef5Kuq9NMr1sk4wn8tjxjj3+LK7/5Mat6go"
    "58B34gMQD7zT+TzucZPf0GbcefpPzCi034e02OK6BUsylWqri+z1KpzKtnzhFIxVK5zFq1Sjoe49Wpi5z700tYRIhlOhCDj3Agl2bqDy+wWatS"
    "Xpwh8uVvk9pYJJ7vRLPLuOUiMggoOQ5//emLOLNzBNkM5qGD27535WWeOHHixGdOCyCQko2aTXcmTdSIML+2TjoRJxk1SZgmmXiMjc0aq5bFw0"
    "EZM5Eivq8fo2ETS2XItKWJoIgEHvGBcRL7H6O/uxdlrVHoG0Hv6If946x3FLgy+Xcyw0P0PfN007+m7R2d8b8ydnXzsNVJtFYBBRDSxz3/LprQ"
    "0HrHCMqraIEHkShaog3QUNU1lNARutEsvG4dFUs2a4HQ0DoHERGzpdZVc14phK7ffxhbim8rqLZa2zUQtub1CJrvIq1VRDKDjiK4OgvxNNLZRO"
    "R6wDChUUUFLngumAnkxjIimgSvjmjvBsNs2rxFSuy8l+t/323r/dRpstPJ9VDuVGiFUrcWSjuuqZYcF0K7wee9+v2vdBPP87Btu6kYnToLC5eb"
    "GychCIKAcqlEsVikUqlc8z/brmHb9VboCyzLouG6VCoVFpeWcRrutpr0PA+rUm1Fl4ZlldkolbYfWkqJ53nbfgGKxRU2SmUAarUam5ubeJ5HqV"
    "Tibt+3ca+RcGV5iY+mzrMw/wlzs/+iUqnxwP4RPM9HCJ3xA2OcPXcWu9ag0NlJJtNG4LucvzBNd1c3MvAZ/sIoqytLpLJ5gobNKydf56vHjgGC"
    "RCLKpdlZ0m1ZkokYETPKww+Nc+qtt0gkkuRyOeq2jRGJoJSkXLb47vHj/OOD95n75DKpVIqhoSEEijNnzpJKZXjuuWfvKl3uuWbkcjl0TZDNtj"
    "PxpXa6O7u4cnWZaCxOW6qN/oE+hCbwvQC7XieTyVCv2xw71ouuaTQch6GhYXq6O2h4kn2FHJlcgbXiCnbdZWxsjPZCgUwqTa22ST5fYGCgj4ly"
    "Gd2IMDw4yNraGr7v03AbSKXwXJdHvzjBkaNfYWZmllg0ilWxOHRognQ6e00d+Vy0VikDpATD0O/bPXwqGFLK2+9L7mhSbOtGIQRSSvRWm7yZ7Z"
    "t1iOuv36rTAWh3KcpC0RV+KghhhDBCGCGMEEYII4QRwghhhDBCGHts/Bu7BAcrX+c6QwAAAABJRU5ErkJggg=="
)


@router.get("/emails/logo")
async def get_crm_email_logo():
    """Serves the official LEAMSS email logo image directly"""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(backend_dir, "assets", "leamss-logo.png")
    if os.path.isfile(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    return Response(content=b"", media_type="image/png", status_code=404)


@router.get("/emails/signature")
async def get_user_signature(current_user: dict = Depends(get_current_user)):
    """Get the current user's email signature or default generated signature"""
    user_id = current_user.get("id")
    user_email = current_user.get("email")

    # Look up user document in db["users"] first, fallback to clients_col
    user_doc = None
    if user_id or user_email:
        user_doc = await db["users"].find_one({"$or": [{"id": user_id}, {"email": user_email}]})
        if not user_doc:
            user_doc = await clients_col.find_one({"$or": [{"id": user_id}, {"email": user_email}]})
    user_doc = user_doc or {}

    saved_sig = user_doc.get("signature") or (user_doc.get("mailbox_settings") or {}).get("signature")
    if saved_sig and str(saved_sig).strip():
        # Ensure it has the bounded signature container and working logo
        cleaned_sig = str(saved_sig).strip()
        # Upgrade any legacy or broken logo link to official HTTPS logo
        if "https://www.leamss.com/leamss-logo.png" in cleaned_sig or "leamss.com/leamss-logo.png" in cleaned_sig:
            cleaned_sig = cleaned_sig.replace("https://www.leamss.com/leamss-logo.png", "https://leamss.com/public/assets/web/images/logo.png")
            cleaned_sig = cleaned_sig.replace("http://www.leamss.com/leamss-logo.png", "https://leamss.com/public/assets/web/images/logo.png")
        if 'onerror="this.style.display=\'none\'"' in cleaned_sig:
            cleaned_sig = cleaned_sig.replace('onerror="this.style.display=\'none\'"', '')
        if 'data-signature-block="true"' not in cleaned_sig and 'class="leamss-signature-block"' not in cleaned_sig:
            cleaned_sig = f'<div class="leamss-signature-block" data-signature-block="true">{cleaned_sig}</div>'
        return {"signature": cleaned_sig, "is_custom": True}

    name = (user_doc.get("name") or current_user.get("name") or "Immigration Consultant").strip()
    designation = (user_doc.get("designation") or user_doc.get("role_title") or user_doc.get("rbac_role_label") or "").strip()
    if not designation:
        role_str = str(current_user.get("role", "")).lower()
        if "admin" in role_str:
            designation = "Director & Principal Consultant"
        elif "sr" in role_str:
            designation = "Senior Immigration Consultant"
        elif "pooja" in name.lower():
            designation = "Marketing & Technical Specialist"
        else:
            designation = "Immigration & Visa Advisor"

    email_val = (user_doc.get("email") or current_user.get("email") or "advisor@leamss.com").strip()
    mobile_val = (user_doc.get("mobile") or user_doc.get("phone") or ("7400403105" if "pooja" in name.lower() else "+91 98765 43210")).strip()
    has_personal_mb = bool((user_doc.get("mailbox_settings") or {}).get("smtp_pass"))
    gw_info = (
        f"Gateway info: Delivered directly from personal mailbox ({email_val})"
        if has_personal_mb
        else f"Gateway info: Delivered via company gateway ({email_val})"
    )

    # Match the official corporate signature shown in LEAMSS CRM with reliable embedded logo
    default_html = (
        f'<div class="leamss-signature-block" data-signature-block="true" style="margin-top: 16px; font-family: Arial, Helvetica, sans-serif; color: #1e293b;">'
        f'  <p style="margin: 0 0 10px 0; font-size: 13px; color: #334155; line-height: 1.4;">Warm Regards,<br/><strong>{name}</strong></p>'
        f'  <table cellpadding="0" cellspacing="0" border="0" style="border-top: 1px solid #cbd5e1; padding-top: 10px; width: 100%; max-width: 520px; font-size: 12px; line-height: 1.5;">'
        f'    <tr>'
        f'      <td style="vertical-align: top; padding-right: 14px; width: 64px;">'
        f'        <img src="https://leamss.com/public/assets/web/images/logo.png" alt="LEAMSS" style="height: 38px; width: auto; max-width: 90px; display: block; object-fit: contain;" />'
        f'      </td>'
        f'      <td style="vertical-align: top;">'
        f'        <div style="font-size: 11px; color: #0284c7; font-weight: bold;"><a href="https://www.leamss.com" target="_blank" style="color: #0284c7; text-decoration: none;">www.leamss.com</a></div>'
        f'        <div style="font-size: 12px; font-weight: bold; color: #0f172a; margin-top: 2px;">Ladhani Education <span style="color: #f97316;">And Migration</span> <span style="color: #ef4444;">Services Pvt Ltd.</span></div>'
        f'        <div style="font-size: 10px; color: #64748b; font-weight: 500;">CIN-U85500MH2024OPC420610</div>'
        f'        <div style="font-size: 12px; font-weight: 600; color: #1e293b; margin-top: 4px;">{designation} - {name}</div>'
        f'        <div style="font-size: 11px; color: #475569;">Contact- <a href="tel:{mobile_val}" style="color: #475569; text-decoration: none; font-weight: 500;">{mobile_val}</a></div>'
        f'        <div style="font-size: 11px; color: #4f46e5; margin-top: 5px;">'
        f'          <a href="https://www.leamss.com" target="_blank" style="color: #4f46e5; text-decoration: underline;">LEAMSS website</a> | '
        f'          <a href="https://www.linkedin.com/company/leamss" target="_blank" style="color: #4f46e5; text-decoration: underline;">LinkedIn</a> | '
        f'          <a href="https://www.instagram.com/leamss_official" target="_blank" style="color: #4f46e5; text-decoration: underline;">Instagram</a> | '
        f'          <a href="https://www.facebook.com/leamssofficial" target="_blank" style="color: #4f46e5; text-decoration: underline;">Facebook</a>'
        f'        </div>'
        f'        <div style="font-size: 10px; color: #94a3b8; margin-top: 8px; font-style: italic; border-top: 1px dashed #e2e8f0; padding-top: 4px;">'
        f'          {gw_info}'
        f'        </div>'
        f'      </td>'
        f'    </tr>'
        f'  </table>'
        f'</div>'
    )
    return {"signature": default_html, "is_custom": False}


@router.put("/emails/signature")
async def save_user_signature(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Save custom rich HTML signature for current user as their permanent default signature"""
    sig = (data.get("signature") or "").strip()
    user_id = current_user.get("id")
    user_email = current_user.get("email")

    if sig and 'data-signature-block="true"' not in sig and 'class="leamss-signature-block"' not in sig:
        sig = f'<div class="leamss-signature-block" data-signature-block="true">{sig}</div>'

    now_iso = datetime.now(timezone.utc).isoformat()
    # Persist in users collection (both top-level and in mailbox_settings)
    await db["users"].update_many(
        {"$or": [{"id": user_id}, {"email": user_email}]},
        {"$set": {"signature": sig, "mailbox_settings.signature": sig, "signature_updated_at": now_iso}}
    )
    # Also update clients collection if matching
    await clients_col.update_many(
        {"$or": [{"id": user_id}, {"email": user_email}]},
        {"$set": {"signature": sig, "signature_updated_at": now_iso}}
    )
    return {"success": True, "message": "Email signature saved as default", "signature": sig, "is_custom": True}


@router.get("/whatsapp/message/{message_id}")
async def get_whatsapp_message_detail(message_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch complete WhatsApp message verification and audit status details."""
    msg = await crm_whatsapp_col.find_one({"id": message_id})
    if not msg:
        try:
            from bson import ObjectId
            if ObjectId.is_valid(message_id):
                msg = await crm_whatsapp_col.find_one({"_id": ObjectId(message_id)})
        except Exception:
            pass
    if not msg:
        raise HTTPException(status_code=404, detail="WhatsApp message not found")

    if "_id" in msg:
        if not msg.get("id"):
            msg["id"] = str(msg["_id"])
        del msg["_id"]

    for dt_field in ["created_at", "confirmed_at", "status_updated_at"]:
        if isinstance(msg.get(dt_field), datetime):
            msg[dt_field] = msg[dt_field].isoformat()

    # Check if recorded in salesperson activity logs
    audit_log = await db["salesperson_activity_logs"].find_one({
        "$or": [
            {"metadata.message_id": msg.get("id")},
            {"id": msg.get("id")}
        ]
    }, {"_id": 0})
    if audit_log and isinstance(audit_log.get("created_at"), datetime):
        audit_log["created_at"] = audit_log["created_at"].isoformat()

    return {
        "success": True,
        "message": msg,
        "audit_logged": bool(audit_log),
        "audit_log": audit_log
    }


@router.post("/whatsapp/confirm-status")
async def confirm_whatsapp_status(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Confirm whether a WhatsApp Web message was successfully sent or failed.
    
    If confirmed sent ('sent'), records the activity in salesperson_activity_logs
    with salesperson_name, client_name, message_status='sent', date & exact time in Asia/Kolkata.
    If marked as failed/cancelled, ensures it is NEVER in salesperson_activity_logs.
    """
    msg_id = data.get("id") or data.get("message_id")
    status = (data.get("status") or "sent").lower().strip()
    error_message = data.get("error_message")

    if not msg_id:
        raise HTTPException(status_code=400, detail="Message ID is required")

    msg = await crm_whatsapp_col.find_one({"id": msg_id})
    if not msg:
        try:
            from bson import ObjectId
            if ObjectId.is_valid(msg_id):
                msg = await crm_whatsapp_col.find_one({"_id": ObjectId(msg_id)})
        except Exception:
            pass
    if not msg:
        raise HTTPException(status_code=404, detail="WhatsApp message not found")

    canonical_id = msg.get("id") or str(msg.get("_id", msg_id))
    filter_query = {"id": msg["id"]} if msg.get("id") else {"_id": msg["_id"]}

    now = datetime.now(timezone.utc)
    lead_id = msg.get("lead_id") or data.get("lead_id")
    client_id = msg.get("client_id") or data.get("client_id")
    contact_name = msg.get("contact_name") or data.get("contact_name") or "Client"
    phone = msg.get("phone") or data.get("phone", "")
    text = msg.get("text") or data.get("text", "")
    template_name = msg.get("template_name")
    sales_person_name = msg.get("sales_person_name") or current_user.get("name") or "Sales Person"

    if status in ["sent", "delivered"]:
        await crm_whatsapp_col.update_one(
            filter_query,
            {"$set": {
                "id": canonical_id,
                "status": "sent",
                "status_updated_at": now,
                "confirmed_at": now,
                "error_message": None
            }}
        )

        tpl_label = f" [Template: {template_name}]" if template_name else ""
        await log_activity(
            user_id=current_user["id"],
            user_name=sales_person_name,
            action="whatsapp_sent",
            entity_type="lead" if lead_id else "client",
            entity_id=lead_id or client_id,
            details=f"WhatsApp Web sent to {contact_name} ({phone}) by {sales_person_name}{tpl_label}: {text[:75]}..."
        )

        if lead_id:
            await leads_col.update_one({"id": lead_id}, {"$set": {"last_contacted_at": now}})
        if client_id:
            await clients_col.update_one({"id": client_id}, {"$set": {"last_contacted_at": now}})

        try:
            from services.salesperson_activity_service import log_salesperson_activity
            # Update existing log if found, otherwise insert
            updated = await db["salesperson_activity_logs"].update_one(
                {"$or": [{"metadata.message_id": canonical_id}, {"metadata.message_id": msg_id}, {"id": canonical_id}]},
                {"$set": {
                    "title": f"WhatsApp Message to {contact_name}",
                    "details": f"{text[:120]}... [Template: {template_name}]" if template_name else text[:140],
                    "message_status": "sent",
                    "metadata.status": "sent",
                    "metadata.message_status": "sent",
                    "metadata.confirmed_at": now.isoformat(),
                    "metadata.error_message": None,
                }}
            )
            if updated.matched_count == 0:
                await log_salesperson_activity(
                    db=db,
                    salesperson_id=current_user["id"],
                    salesperson_name=sales_person_name,
                    salesperson_email=current_user.get("email"),
                    salesperson_role=current_user.get("rbac_role") or current_user.get("role"),
                    activity_type="whatsapp",
                    client_id=lead_id or client_id,
                    client_name=contact_name,
                    client_phone=phone,
                    title=f"WhatsApp Message to {contact_name}",
                    details=f"{text[:120]}... [Template: {template_name}]" if template_name else text[:140],
                    metadata={
                        "status": "sent",
                        "message_status": "sent",
                        "channel": "whatsapp_web",
                        "client_name": contact_name,
                        "salesperson_name": sales_person_name,
                        "message_id": canonical_id,
                        "template": template_name,
                        "confirmed_at": now.isoformat()
                    }
                )
        except Exception as e:
            logger.warning(f"Error logging confirmed whatsapp to audit: {e}")

        return {"success": True, "status": "sent", "id": canonical_id, "message": "WhatsApp message confirmed sent & logged in Audit Log"}
    else:
        # Mark as failed or cancelled
        fail_reason = error_message or "Send cancelled or failed in WhatsApp Web"
        await crm_whatsapp_col.update_one(
            filter_query,
            {"$set": {
                "id": canonical_id,
                "status": "failed",
                "status_updated_at": now,
                "error_message": fail_reason
            }}
        )

        tpl_label = f" [Template: {template_name}]" if template_name else ""
        await log_activity(
            user_id=current_user["id"],
            user_name=sales_person_name,
            action="whatsapp_failed",
            entity_type="lead" if lead_id else "client",
            entity_id=lead_id or client_id,
            details=f"WhatsApp to {contact_name} ({phone}) marked as failed by {sales_person_name}{tpl_label}: {fail_reason}"
        )

        # Update or record in salesperson_activity_logs (NEVER delete or hide failed messages)
        try:
            from services.salesperson_activity_service import log_salesperson_activity
            updated = await db["salesperson_activity_logs"].update_one(
                {"$or": [{"metadata.message_id": canonical_id}, {"metadata.message_id": msg_id}, {"id": canonical_id}]},
                {"$set": {
                    "title": f"WhatsApp Message to {contact_name} (Failed)",
                    "details": f"{text[:120]}... [Failed: {fail_reason}]",
                    "message_status": "failed",
                    "metadata.status": "failed",
                    "metadata.message_status": "failed",
                    "metadata.error_message": fail_reason,
                    "metadata.failed_at": now.isoformat()
                }}
            )
            if updated.matched_count == 0:
                await log_salesperson_activity(
                    db=db,
                    salesperson_id=current_user["id"],
                    salesperson_name=sales_person_name,
                    salesperson_email=current_user.get("email"),
                    salesperson_role=current_user.get("rbac_role") or current_user.get("role"),
                    activity_type="whatsapp",
                    client_id=lead_id or client_id,
                    client_name=contact_name,
                    client_phone=phone,
                    title=f"WhatsApp Message to {contact_name} (Failed)",
                    details=f"{text[:120]}... [Failed: {fail_reason}]",
                    metadata={
                        "status": "failed",
                        "message_status": "failed",
                        "channel": "whatsapp_web",
                        "client_name": contact_name,
                        "salesperson_name": sales_person_name,
                        "message_id": canonical_id,
                        "template": template_name,
                        "error_message": fail_reason,
                        "failed_at": now.isoformat()
                    }
                )
        except Exception as e:
            logger.warning(f"Error recording failed whatsapp in audit: {e}")

        return {"success": True, "status": "failed", "id": canonical_id, "message": "WhatsApp message marked as failed & recorded in Audit Log"}



@router.post("/emails/send")
async def send_crm_email(data: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Compose and send email from CRM to lead or client with real delivery through SMTP/Resend"""
    lead_id = data.get("lead_id")
    client_id = data.get("client_id")
    to_email = (data.get("to_email") or "").strip()
    subject = (data.get("subject") or "").strip()
    body_html = data.get("body_html") or data.get("body") or ""
    attachments = data.get("attachments", [])
    template_id = data.get("template_id")
    thread_id = data.get("thread_id")
    
    contact_name = data.get("contact_name", "")
    if lead_id and not to_email:
        lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "name": 1, "email": 1})
        if lead:
            to_email = (lead.get("email") or "").strip()
            contact_name = contact_name or lead.get("name", "")

    if client_id and not to_email:
        client = await clients_col.find_one({"id": client_id}, {"_id": 0, "name": 1, "email": 1})
        if client:
            to_email = (client.get("email") or "").strip()
            contact_name = contact_name or client.get("name", "")
            
    if not to_email or "@" not in to_email:
        raise HTTPException(status_code=400, detail="A valid recipient email address is required")

    # Auto-link lead or client if not explicitly passed
    if not lead_id and not client_id and to_email:
        escaped_to = re.escape(to_email.strip())
        matched_lead = await leads_col.find_one({"email": {"$regex": f"^{escaped_to}$", "$options": "i"}})
        if matched_lead:
            lead_id = matched_lead.get("id")
            contact_name = contact_name or matched_lead.get("name", "")
        else:
            matched_client = await clients_col.find_one({"email": {"$regex": f"^{escaped_to}$", "$options": "i"}})
            if matched_client:
                client_id = matched_client.get("id") or str(matched_client.get("_id"))
                contact_name = contact_name or matched_client.get("name", "")

    if not subject:
        raise HTTPException(status_code=400, detail="Email subject is required")

    email_id = str(uuid.uuid4())
    effective_thread_id = thread_id
    if not effective_thread_id:
        match_query = {}
        if lead_id:
            match_query["lead_id"] = lead_id
        elif client_id:
            match_query["client_id"] = client_id
        elif to_email:
            match_query["$or"] = [{"to_email": to_email}, {"from_email": to_email}]
        
        if match_query:
            existing = await crm_emails_col.find_one(match_query, sort=[("created_at", -1)])
            if existing and existing.get("thread_id"):
                norm_sub = re.sub(r"^(?:re|fwd?|wa)\s*:\s*", "", subject, flags=re.IGNORECASE).strip().lower()
                exist_sub = re.sub(r"^(?:re|fwd?|wa)\s*:\s*", "", existing.get("subject", ""), flags=re.IGNORECASE).strip().lower()
                if norm_sub == exist_sub:
                    effective_thread_id = existing.get("thread_id")

    if not effective_thread_id:
        effective_thread_id = email_id

    # Lookup parent message_id for In-Reply-To header
    in_reply_to = data.get("in_reply_to")
    if not in_reply_to and effective_thread_id != email_id:
        latest = await crm_emails_col.find_one({"thread_id": effective_thread_id}, sort=[("created_at", -1)])
        if latest and latest.get("message_id"):
            in_reply_to = latest.get("message_id")

    message_id = f"<crm_{email_id}@{to_email.split('@')[-1]}>"
    sender_name = current_user.get("name") or "LEAMSS Immigration Advisor"
    sender_email = current_user.get("email")

    # Format plain text and HTML
    html_content = body_html
    is_rich_html = bool(re.search(r"<(p|div|table|ul|ol|h[1-6]|span|blockquote|br|hr|img|a|strong|b|em|i)\b", html_content, re.IGNORECASE))
    if not is_rich_html:
        # Wrap plain text in clean HTML styling
        paras = "".join(f"<p style='margin:0 0 12px; line-height: 1.6;'>{p}</p>" for p in html_content.split("\n\n") if p.strip())
        html_content = (
            f"<div style='font-family: Arial, sans-serif; font-size: 14px; color: #1e293b; max-width: 650px;'>"
            f"{paras}"
            f"<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;' />"
            f"<p style='font-size: 12px; color: #64748b;'>Sent by {sender_name} · LEAMSS Immigration Services</p>"
            f"</div>"
        )
    else:
        # Ensure no duplicate signatures in outbound email
        if "leamss-signature-block" in html_content:
            sig_matches = list(re.finditer(r'<div[^>]*class=["\'][^"\']*leamss-signature-block[^"\']*["\'][^>]*>.*?</div>\s*</div>', html_content, re.DOTALL | re.IGNORECASE))
            if len(sig_matches) > 1:
                # Keep only the last signature block
                for m in reversed(sig_matches[:-1]):
                    html_content = html_content[:m.start()] + html_content[m.end():]

    # Save default signature on first use if not already saved or explicitly requested
    save_as_default = bool(data.get("save_as_default_signature", False))
    user_id = current_user.get("id")
    user_email = current_user.get("email")
    if ("leamss-signature-block" in html_content or save_as_default) and (user_id or user_email):
        existing_u = await db["users"].find_one({"$or": [{"id": user_id}, {"email": user_email}]}, {"signature": 1})
        if save_as_default or not (existing_u or {}).get("signature"):
            sig_match = re.search(r'(<div[^>]*class=["\'][^"\']*leamss-signature-block[^"\']*["\'][^>]*>.*?</div>\s*</div>)', html_content, re.DOTALL | re.IGNORECASE)
            extracted_sig = sig_match.group(1) if sig_match else (data.get("signature") or "")
            if extracted_sig:
                now_iso = datetime.now(timezone.utc).isoformat()
                await db["users"].update_many(
                    {"$or": [{"id": user_id}, {"email": user_email}]},
                    {"$set": {"signature": extracted_sig, "mailbox_settings.signature": extracted_sig, "signature_updated_at": now_iso}}
                )

    # Resolve local attachment file paths if saved_filename is present
    for att in (attachments or []):
        if not att.get("file_path") and att.get("saved_filename"):
            cand = os.path.join(ATTACHMENTS_DIR, os.path.basename(att["saved_filename"]))
            if os.path.exists(cand):
                att["file_path"] = cand

    # Auto-attach candidate resume if requested or when forwarding candidate details
    attach_resume_flag = data.get("attach_resume")
    resume_fid = data.get("resume_file_id")
    should_attach_resume = (
        attach_resume_flag is True
        or (attach_resume_flag is not False and any(k in subject.lower() for k in ("forward", "profile", "candidate", "resume", "cv")))
    )
    if should_attach_resume and not resume_fid:
        if lead_id:
            ld = await leads_col.find_one({"id": lead_id}, {"_id": 0, "resume_file_id": 1, "resume_filename": 1})
            if ld and ld.get("resume_file_id"):
                resume_fid = ld["resume_file_id"]
        elif client_id:
            cl = await clients_col.find_one({"id": client_id}, {"_id": 0, "resume_file_id": 1, "resume_filename": 1})
            if cl and cl.get("resume_file_id"):
                resume_fid = cl["resume_file_id"]

    if resume_fid:
        already_attached = any(att.get("file_id") == str(resume_fid) for att in (attachments or []))
        if not already_attached:
            from core.resume_service import get_resume_bytes_and_meta
            res_meta = await get_resume_bytes_and_meta(resume_fid)
            if res_meta:
                if attachments is None:
                    attachments = []
                attachments.append({
                    "filename": res_meta["filename"],
                    "bytes": res_meta["bytes"],
                    "content_type": res_meta["content_type"],
                    "file_id": res_meta["file_id"],
                })

    # Notification, CC, and BCC options
    notify_by_email = bool(data.get("notify_by_email", False))
    cc = (data.get("cc") or data.get("cc_email") or "").strip() or None
    bcc = (data.get("bcc") or data.get("bcc_email") or "").strip() or None

    # Dispatch via active email service (personal SMTP / company gateway / Resend)
    dispatch_res = await dispatch_email(
        to_email=to_email,
        subject=subject,
        body_html=html_content,
        user_id=current_user["id"],
        sender_name=sender_name,
        sender_email=sender_email,
        cc=cc,
        bcc=bcc,
        notify_by_email=notify_by_email,
        message_id=message_id,
        in_reply_to=in_reply_to,
        attachments=attachments
    )

    now_utc = datetime.now(timezone.utc)
    email_doc = {
        "id": email_id,
        "lead_id": lead_id,
        "client_id": client_id,
        "thread_id": effective_thread_id,
        "in_reply_to": in_reply_to,
        "message_id": dispatch_res.get("message_id") or message_id,
        "direction": "outbound",
        "to_email": to_email,
        "contact_name": contact_name,
        "from_email": sender_email,
        "requested_from_email": sender_email,
        "is_personal_mailbox": True,
        "reply_to": dispatch_res.get("reply_to") or f"{sender_name} <{sender_email}>",
        "cc": cc,
        "bcc": bcc,
        "notify_by_email": notify_by_email,
        "sales_person_id": current_user["id"],
        "sales_person_name": sender_name,
        "subject": subject,
        "body_html": html_content,
        "raw_text": body_html,
        "attachments": attachments,
        "template_id": template_id,
        "status": dispatch_res.get("status", "sent"),  # delivered, failed, pending_configuration
        "delivery_provider": dispatch_res.get("provider"),
        "delivery_info": dispatch_res.get("info"),
        "delivery_error": dispatch_res.get("error"),
        "opened_at": None,
        "sent_at": now_utc,
        "created_at": now_utc
    }
    await crm_emails_col.insert_one(email_doc)

    # Propagate latest notify_by_email preference to this thread
    if effective_thread_id:
        await crm_emails_col.update_many(
            {"thread_id": effective_thread_id},
            {"$set": {"notify_by_email": notify_by_email}}
        )

    # Activity log
    await log_activity(
        user_id=current_user["id"],
        user_name=sender_name,
        action="email_sent",
        entity_type="lead" if lead_id else "client",
        entity_id=lead_id or client_id,
        details=f"Email '{subject}' sent to {to_email} ({dispatch_res.get('status')})"
    )

    return {
        "success": True,
        "message": "Email sent and logged successfully",
        "id": email_doc["id"],
        "thread_id": effective_thread_id,
        "notify_by_email": notify_by_email,
        "reply_to": dispatch_res.get("reply_to"),
        "cc": cc,
        "status": dispatch_res.get("status"),
        "delivery_info": dispatch_res.get("info"),
        "delivery_error": dispatch_res.get("error"),
        "fallback": bool(dispatch_res.get("fallback"))
    }


@router.post("/emails/inbound")
async def receive_inbound_email(payload: dict = Body(...)):
    """Capture incoming email reply from client or webhook provider into client history"""
    from_email = (payload.get("from_email") or payload.get("from") or payload.get("sender") or "").strip().lower()
    to_email = (payload.get("to_email") or payload.get("to") or payload.get("recipient") or "").strip().lower()
    subject = (payload.get("subject") or "Re: Communication").strip()
    body_html = payload.get("body_html") or payload.get("html") or payload.get("text") or payload.get("body") or ""
    in_reply_to = payload.get("in_reply_to") or payload.get("In-Reply-To")
    thread_id = payload.get("thread_id")
    lead_id = payload.get("lead_id")
    client_id = payload.get("client_id")

    if not from_email:
        raise HTTPException(status_code=400, detail="Sender email (from_email) is required")

    contact_name = payload.get("contact_name") or ""
    # Try finding matching lead/client
    if not lead_id and not client_id:
        escaped_email = re.escape(from_email)
        lead = await leads_col.find_one({"email": {"$regex": f"^{escaped_email}$", "$options": "i"}})
        if lead:
            lead_id = lead.get("id")
            contact_name = contact_name or lead.get("name", "")
        else:
            client = await clients_col.find_one({"email": {"$regex": f"^{escaped_email}$", "$options": "i"}})
            if client:
                client_id = client.get("id") or str(client.get("_id"))
                contact_name = contact_name or client.get("name", "")

    # If thread_id not provided, match with existing thread for this client
    if not thread_id and (lead_id or client_id or from_email):
        last_email = await crm_emails_col.find_one(
            {"$or": [{"lead_id": lead_id}, {"client_id": client_id}, {"to_email": from_email}]},
            sort=[("created_at", -1)]
        )
        if last_email:
            thread_id = last_email.get("thread_id") or last_email.get("id")

    # Determine notify_by_email preference for this thread
    notify_by_email = bool(payload.get("notify_by_email", False))
    effective_tid = thread_id or (last_email.get("thread_id") if last_email else None)
    if effective_tid and not notify_by_email:
        parent_e = await crm_emails_col.find_one(
            {"thread_id": effective_tid, "notify_by_email": {"$exists": True}},
            sort=[("created_at", -1)]
        )
        if parent_e:
            notify_by_email = bool(parent_e.get("notify_by_email", False))

    # Determine assigned sales rep
    assigned_sp_id = None
    assigned_sp_name = None
    assigned_sp_email = None
    assigned_sp_role = None

    if lead_id:
        l_doc = await leads_col.find_one({"id": lead_id}, {"assigned_to": 1, "sales_person_id": 1, "assigned_to_name": 1})
        if l_doc:
            assigned_sp_id = l_doc.get("assigned_to") or l_doc.get("sales_person_id")
            assigned_sp_name = l_doc.get("assigned_to_name")

    if not assigned_sp_id and to_email:
        rep_u = await db["users"].find_one({"email": to_email})
        if rep_u:
            assigned_sp_id = rep_u.get("id")
            assigned_sp_name = rep_u.get("name")
            assigned_sp_email = rep_u.get("email")
            assigned_sp_role = rep_u.get("rbac_role") or rep_u.get("role")
    elif assigned_sp_id:
        rep_u = await db["users"].find_one({"id": assigned_sp_id})
        if rep_u:
            assigned_sp_name = assigned_sp_name or rep_u.get("name")
            assigned_sp_email = rep_u.get("email")
            assigned_sp_role = rep_u.get("rbac_role") or rep_u.get("role")

    now_utc = datetime.now(timezone.utc)
    inbound_doc = {
        "id": str(uuid.uuid4()),
        "message_id": payload.get("message_id") or f"<inbound_{uuid.uuid4().hex}@client>",
        "thread_id": thread_id or str(uuid.uuid4()),
        "in_reply_to": in_reply_to,
        "lead_id": lead_id,
        "client_id": client_id,
        "sales_person_id": assigned_sp_id,
        "sales_person_name": assigned_sp_name,
        "direction": "inbound",
        "status": "received",
        "from_email": from_email,
        "to_email": to_email or "advisor@leamss.com",
        "contact_name": contact_name or from_email,
        "subject": subject,
        "body_html": body_html,
        "notify_by_email": notify_by_email,
        "read": False,
        "created_at": now_utc
    }
    await crm_emails_col.insert_one(inbound_doc)

    # Activity log
    if lead_id or client_id:
        await log_activity(
            user_id="system",
            user_name=contact_name or from_email,
            action="email_reply_received",
            entity_type="lead" if lead_id else "client",
            entity_id=lead_id or client_id,
            details=f"Received email reply from {contact_name or from_email}: {subject}"
        )
        if assigned_sp_id:
            try:
                from services.salesperson_activity_service import log_salesperson_activity
                await log_salesperson_activity(
                    db=db,
                    salesperson_id=assigned_sp_id,
                    salesperson_name=assigned_sp_name or "Salesperson",
                    salesperson_email=assigned_sp_email or to_email,
                    salesperson_role=assigned_sp_role or "sales_executive",
                    activity_type="email",
                    client_id=lead_id or client_id,
                    client_name=contact_name or from_email,
                    client_email=from_email,
                    title=f"Email (Received): {subject} - {contact_name or from_email}",
                    details=f"Received email reply from {contact_name or from_email}: {subject}",
                    metadata={
                        "subject": subject,
                        "direction": "received",
                        "status": "received",
                        "from_email": from_email,
                        "to_email": to_email or assigned_sp_email
                    }
                )
            except Exception as e_act:
                logger.debug(f"Could not log inbound email to salesperson audit: {e_act}")

    # Inbound notification for assigned sales rep
    if lead_id:
        l_doc = await leads_col.find_one({"id": lead_id}, {"assigned_to": 1})
        if l_doc and l_doc.get("assigned_to"):
            await create_notification(
                user_id=l_doc["assigned_to"],
                title="New Client Email Reply",
                message=f"{contact_name or from_email} replied: '{subject}'",
                type="email_reply",
                link="/my-crm"
            )
            # If 'Notify me by email' was explicitly enabled for this thread, deliver copy to sales rep's Gmail
            if notify_by_email:
                try:
                    rep_user = await db["users"].find_one({"id": l_doc["assigned_to"]})
                    if rep_user and rep_user.get("email"):
                        await dispatch_email(
                            to_email=rep_user["email"],
                            subject=f"[CRM Reply] {subject}",
                            body_html=(
                                f"<p><strong>Client {contact_name or from_email} replied:</strong></p>"
                                f"<div style='background:#f8fafc;border-left:4px solid #6366f1;padding:12px;margin:12px 0;'>"
                                f"{body_html}"
                                f"</div>"
                                f"<p style='font-size:11px;color:#64748b;'>Delivered to your email because 'Notify me by email' was enabled in CRM.</p>"
                            ),
                            sender_name="LEAMSS CRM",
                            sender_email="info@leamss.com",
                            notify_by_email=True,
                        )
                except Exception as n_err:
                    logger.debug("Could not dispatch notification email to sales rep: %s", n_err)

    return {
        "success": True,
        "message": "Inbound email logged successfully",
        "id": inbound_doc["id"],
        "thread_id": inbound_doc["thread_id"],
        "notify_by_email": notify_by_email
    }


@router.post("/emails/simulate-reply")
async def simulate_client_reply(payload: dict = Body(...), current_user: dict = Depends(get_current_user)):
    """Simulate an incoming email reply from client for live verification and demo"""
    email_id = payload.get("email_id")
    lead_id = payload.get("lead_id")
    client_id = payload.get("client_id")
    reply_subject = payload.get("reply_subject")
    reply_body = payload.get("reply_body") or (
        "Thank you for the detailed information. I have reviewed the requirements "
        "and I am interested in proceeding. Could we schedule a call tomorrow afternoon?"
    )

    target_email = None
    if email_id:
        target_email = await crm_emails_col.find_one({"id": email_id})
    elif lead_id:
        target_email = await crm_emails_col.find_one({"lead_id": lead_id}, sort=[("created_at", -1)])
    elif client_id:
        target_email = await crm_emails_col.find_one({"client_id": client_id}, sort=[("created_at", -1)])

    lead_doc = None
    target_lid = lead_id or (target_email.get("lead_id") if target_email else None)
    if target_lid:
        lead_doc = await leads_col.find_one({"id": target_lid})

    from_email = (target_email.get("to_email") if target_email else None) or (lead_doc.get("email") if lead_doc else None) or "client@example.com"
    contact_name = (target_email.get("contact_name") if target_email else None) or (lead_doc.get("name") if lead_doc else None) or "Client"
    thread_id = (target_email.get("thread_id") if target_email else None) or (target_email.get("id") if target_email else None) or str(uuid.uuid4())
    subj = reply_subject or (f"Re: {target_email.get('subject', 'Consultation')}" if target_email else "Re: Inquiry regarding Australian PR")

    now_utc = datetime.now(timezone.utc)
    target_notify = bool(target_email.get("notify_by_email", False)) if target_email else False
    sim_sp_id = (target_email.get("sales_person_id") if target_email else None) or (lead_doc.get("assigned_to") if lead_doc else None) or current_user.get("id")
    sim_sp_name = (target_email.get("sales_person_name") if target_email else None) or current_user.get("name") or "Salesperson"
    sim_sp_email = current_user.get("email") or "advisor@leamss.com"

    inbound_doc = {
        "id": str(uuid.uuid4()),
        "message_id": f"<sim_{uuid.uuid4().hex}@client>",
        "thread_id": thread_id,
        "in_reply_to": target_email.get("message_id") if target_email else None,
        "lead_id": target_lid,
        "client_id": client_id or (target_email.get("client_id") if target_email else None),
        "sales_person_id": sim_sp_id,
        "sales_person_name": sim_sp_name,
        "direction": "inbound",
        "status": "received",
        "from_email": from_email,
        "to_email": current_user.get("email", "advisor@leamss.com"),
        "contact_name": contact_name,
        "subject": subj,
        "body_html": f"<p style='font-family: Arial, sans-serif; font-size: 14px; color: #1e293b;'>{reply_body}</p>",
        "raw_text": reply_body,
        "notify_by_email": target_notify,
        "read": False,
        "created_at": now_utc
    }
    await crm_emails_col.insert_one(inbound_doc)

    # Activity log
    await log_activity(
        user_id=current_user["id"],
        user_name=contact_name,
        action="email_reply_received",
        entity_type="lead" if target_lid else "client",
        entity_id=target_lid or inbound_doc.get("client_id"),
        details=f"Received email reply from {contact_name} ({from_email}): {subj}"
    )

    try:
        from services.salesperson_activity_service import log_salesperson_activity
        await log_salesperson_activity(
            db=db,
            salesperson_id=sim_sp_id,
            salesperson_name=sim_sp_name,
            salesperson_email=sim_sp_email,
            salesperson_role=current_user.get("rbac_role") or current_user.get("role") or "sales_executive",
            activity_type="email",
            client_id=target_lid or inbound_doc.get("client_id"),
            client_name=contact_name,
            client_email=from_email,
            title=f"Email (Received): {subj} - {contact_name}",
            details=f"Received email reply from {contact_name} ({from_email}): {subj}",
            metadata={
                "subject": subj,
                "direction": "received",
                "status": "received",
                "from_email": from_email,
                "to_email": sim_sp_email
            }
        )
    except Exception as e_act:
        logger.debug(f"Could not log simulated email reply to salesperson audit: {e_act}")

    clean_reply = {k: v for k, v in inbound_doc.items() if k != "_id"}
    clean_reply["created_at"] = now_utc.isoformat()
    return {"success": True, "message": "Simulated reply captured", "reply": clean_reply}


@router.post("/emails/sync")
async def trigger_email_sync(
    payload: Optional[dict] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger bidirectional mailbox synchronization (INBOX + Sent Mail)."""
    from core.mail_sync import sync_user_mailbox

    payload = payload or {}
    contact_email = payload.get("contact_email")
    lead_id = payload.get("lead_id")
    client_id = payload.get("client_id")

    if not contact_email and lead_id:
        lead = await leads_col.find_one({"id": lead_id}, {"email": 1})
        if lead:
            contact_email = lead.get("email")

    if not contact_email and client_id:
        client = await clients_col.find_one({"id": client_id}, {"email": 1})
        if client:
            contact_email = client.get("email")

    res = await sync_user_mailbox(
        user_id=current_user["id"],
        target_contact_email=contact_email,
        limit=40
    )
    return res


@router.get("/emails")
async def get_crm_emails(
    lead_id: Optional[str] = None,
    client_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    sales_person_id: Optional[str] = None,
    sort: str = "desc",
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get emails sent/received for a lead, client, conversation thread, or role-scoped list"""
    query: Dict[str, Any] = {}
    if thread_id:
        query["thread_id"] = thread_id
    elif lead_id:
        lead = await leads_col.find_one({"id": lead_id}, {"email": 1})
        lead_email = (lead.get("email") or "").strip().lower() if lead else ""
        if lead_email:
            escaped_e = re.escape(lead_email)
            query["$or"] = [
                {"lead_id": lead_id},
                {"to_email": {"$regex": f"^{escaped_e}$", "$options": "i"}},
                {"from_email": {"$regex": f"^{escaped_e}$", "$options": "i"}},
            ]
        else:
            query["lead_id"] = lead_id
    elif client_id:
        client = await clients_col.find_one({"id": client_id}, {"email": 1})
        c_email = (client.get("email") or "").strip().lower() if client else ""
        if c_email:
            escaped_e = re.escape(c_email)
            query["$or"] = [
                {"client_id": client_id},
                {"to_email": {"$regex": f"^{escaped_e}$", "$options": "i"}},
                {"from_email": {"$regex": f"^{escaped_e}$", "$options": "i"}},
            ]
        else:
            query["client_id"] = client_id

    # Role-based scoping: Non-admin sales persons can ONLY see emails for their assigned clients/leads
    if not _is_admin(current_user):
        uid = str(current_user.get("id") or "").strip()
        uemail = str(current_user.get("email") or "").strip().lower()
        uname = str(current_user.get("name") or "").strip()

        lead_assign_criteria = []
        if uid:
            lead_assign_criteria.extend([
                {"assigned_to": uid},
                {"assigned_sales_rep_id": uid},
                {"sales_person_id": uid},
                {"block_assigned_to": uid},
                {"created_by": uid}
            ])
        if uemail:
            lead_assign_criteria.extend([
                {"assigned_to": uemail},
                {"assigned_to_email": uemail}
            ])
        if uname:
            lead_assign_criteria.append({"assigned_to_name": uname})
            lead_assign_criteria.append({"assigned_to_name": {"$regex": f"^{re.escape(uname)}$", "$options": "i"}})

        assigned_leads = await leads_col.find(
            {"$or": lead_assign_criteria},
            {"id": 1, "email": 1, "name": 1}
        ).to_list(1000)

        assigned_lead_ids = [l["id"] for l in assigned_leads if l.get("id")]
        assigned_lead_emails = [
            (l["email"]).strip().lower() for l in assigned_leads if l.get("email")
        ]

        assigned_cases = await cases_col.find(
            {"$or": [
                {"assigned_to": uid},
                {"case_manager_id": uid},
                {"sales_person_id": uid},
                {"created_by": uid}
            ]},
            {"id": 1, "client_id": 1, "client_email": 1, "email": 1}
        ).to_list(500)
        assigned_client_ids = [c["id"] for c in assigned_cases if c.get("id")] + [
            c["client_id"] for c in assigned_cases if c.get("client_id")
        ]
        assigned_client_emails = [
            (c.get("client_email") or c.get("email") or "").strip().lower()
            for c in assigned_cases
            if (c.get("client_email") or c.get("email"))
        ]

        salesperson_scope = []
        if assigned_lead_ids:
            salesperson_scope.append({"lead_id": {"$in": assigned_lead_ids}})
        if assigned_client_ids:
            salesperson_scope.append({"client_id": {"$in": assigned_client_ids}})

        all_scoped_emails = set([e for e in assigned_lead_emails + assigned_client_emails if e])
        for ce in all_scoped_emails:
            escaped_ce = re.escape(ce)
            salesperson_scope.append({"to_email": {"$regex": f"^{escaped_ce}$", "$options": "i"}})
            salesperson_scope.append({"from_email": {"$regex": f"^{escaped_ce}$", "$options": "i"}})

        if not salesperson_scope:
            # Salesperson has no assigned leads/clients - must see zero emails
            query = {"id": "__no_assigned_clients__"}
        elif query:
            query = {"$and": [query, {"$or": salesperson_scope}]}
        else:
            query = {"$or": salesperson_scope}

    elif sales_person_id and _is_manager_or_admin(current_user):
        sp_filter = {"$or": [{"sales_person_id": sales_person_id}, {"created_by": sales_person_id}]}
        if query:
            query = {"$and": [query, sp_filter]}
        else:
            query = sp_filter

    sort_dir = 1 if (sort or "").lower() == "asc" else -1
    emails = await crm_emails_col.find(query, {"_id": 0}).sort("created_at", sort_dir).to_list(limit)
    for e in emails:
        if isinstance(e.get("created_at"), datetime):
            e["created_at"] = e["created_at"].isoformat()
        if isinstance(e.get("sent_at"), datetime):
            e["sent_at"] = e["sent_at"].isoformat()
        # Outbound emails sent by sales staff must always show the salesperson's email ID
        if e.get("direction") != "inbound":
            req_from = e.get("requested_from_email")
            if req_from:
                e["from_email"] = req_from
            elif e.get("from_email") == "info@leamss.com" and e.get("sales_person_name") and e.get("sales_person_name").lower() != "system":
                # Fallback to salesperson email or consultant address
                if e.get("sales_person_id"):
                    sp_doc = await db["users"].find_one({"id": e["sales_person_id"]}, {"email": 1})
                    if sp_doc and sp_doc.get("email"):
                        e["from_email"] = sp_doc["email"]
    return emails


# ────────────────────────────────────────────────────────────
# 6. AI SALES COMMUNICATION ASSISTANT (WHATSAPP, EMAIL, CALL COPILOT)
# ────────────────────────────────────────────────────────────

class CrmAiSuggestReplyRequest(BaseModel):
    channel: str = Field(..., description="'whatsapp', 'email', or 'live_call'")
    client_message: str = Field(..., description="Inbound text, client email inquiry, or call question")
    lead_id: Optional[str] = None
    target_country: Optional[str] = None
    service_interested: Optional[str] = None
    intent_type: Optional[str] = "auto_reply"
    lead_context: Optional[Dict[str, Any]] = None

    class Config:
        extra = "ignore"


@router.post("/ai/suggest-reply")
async def crm_ai_suggest_reply(
    payload: CrmAiSuggestReplyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generates channel-specific sales communication responses (WhatsApp, Email, Live Call) grounded in Product Master."""
    from services.crm_ai_communication_service import generate_communication_reply

    res = await generate_communication_reply(
        channel=payload.channel,
        client_message=payload.client_message,
        lead_id=payload.lead_id,
        target_country=payload.target_country,
        service_interested=payload.service_interested,
        intent_type=payload.intent_type or "auto_reply",
        lead_context=payload.lead_context,
    )
    return res

