"""WhatsApp Marketing & Live Chat Inbox Router.

Provides multi-thread WhatsApp conversation management, live chat box messaging,
Admin assignment of conversations to partners/agents, internal notes, canned responses,
and Meta Webhook handling for incoming client messages.
"""
from __future__ import annotations

import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel

from core.auth import get_current_user
from core.database import db
from core.whatsapp_service import (
    normalize_phone_number,
    get_whatsapp_config,
    send_whatsapp_text,
    send_whatsapp_template,
)

logger = logging.getLogger("whatsapp_chat")

router = APIRouter(prefix="/whatsapp-chat", tags=["whatsapp-chat"])

CONVERSATIONS = db["whatsapp_conversations"]
MESSAGES = db["whatsapp_messages"]
USERS = db["users"]
TEMPLATES = db["whatsapp_templates"]
ASSESSMENTS = db["sales_assessments"]

ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}
ALLOWED_ROLES = {
    "admin", "admin_owner", "super_admin", "partner", "sales_executive",
    "sr_sales_executive", "sales_manager", "sales_head", "case_manager",
}


def _clean_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    return doc


def _has_access(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role") or ""
    return role in ALLOWED_ROLES or "*" in (user.get("permissions") or [])


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role") or ""
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


# ── Pydantic Request Models ───────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    text: str
    template_id: Optional[str] = None
    media_url: Optional[str] = None
    media_filename: Optional[str] = None


class AssignChatRequest(BaseModel):
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str  # "open", "in_progress", "qualified", "closed"


class AddNoteRequest(BaseModel):
    text: str


class CreateConversationRequest(BaseModel):
    phone: str
    client_name: Optional[str] = "Client"
    client_email: Optional[str] = None
    assessment_id: Optional[str] = None
    initial_message: Optional[str] = None


class SimulateInboundRequest(BaseModel):
    phone: str
    client_name: Optional[str] = "Applicant"
    text: str


# ── Helper to record message & upsert conversation ───────────────────────────

async def record_chat_message(
    phone: str,
    text: str,
    direction: str = "outbound",  # "inbound" | "outbound"
    sender_type: str = "staff",   # "client" | "staff" | "system"
    sender_id: Optional[str] = None,
    sender_name: Optional[str] = None,
    client_name: Optional[str] = None,
    client_email: Optional[str] = None,
    assessment_id: Optional[str] = None,
    status: str = "sent",
    media_url: Optional[str] = None,
    media_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to save a message and update/create the parent conversation thread."""
    clean_phone = normalize_phone_number(phone)
    if not clean_phone:
        raise ValueError("Invalid phone number")

    now = datetime.now(timezone.utc)

    # 1. Find or create conversation
    conv = await CONVERSATIONS.find_one({"phone": clean_phone})
    if not conv:
        # Check if we can infer client name or assessment from sales_assessments
        ass_doc = None
        if not client_name or not assessment_id:
            ass_doc = await ASSESSMENTS.find_one({
                "$or": [
                    {"client_phone": clean_phone},
                    {"whatsapp_to": clean_phone},
                    {"phone": clean_phone},
                ]
            })
            if ass_doc:
                client_name = client_name or ass_doc.get("client_name") or "Applicant"
                client_email = client_email or ass_doc.get("client_email") or ass_doc.get("email")
                assessment_id = assessment_id or ass_doc.get("id")

        conv_id = str(uuid.uuid4())
        conv = {
            "id": conv_id,
            "phone": clean_phone,
            "client_name": client_name or "Applicant",
            "client_email": client_email,
            "assessment_id": assessment_id,
            "assigned_to": None,
            "assigned_to_name": None,
            "assigned_by": None,
            "assigned_at": None,
            "status": "open",
            "last_message": text,
            "last_message_at": now,
            "last_message_direction": direction,
            "unread_count": 1 if direction == "inbound" else 0,
            "tags": [],
            "notes": [],
            "created_at": now,
            "updated_at": now,
        }
        await CONVERSATIONS.insert_one(conv)
    else:
        conv_id = conv["id"]
        update_set: Dict[str, Any] = {
            "last_message": text,
            "last_message_at": now,
            "last_message_direction": direction,
            "updated_at": now,
        }
        if client_name and conv.get("client_name") in (None, "", "Applicant", "Client"):
            update_set["client_name"] = client_name
        if client_email and not conv.get("client_email"):
            update_set["client_email"] = client_email
        if assessment_id and not conv.get("assessment_id"):
            update_set["assessment_id"] = assessment_id

        update_ops: Dict[str, Any] = {"$set": update_set}
        if direction == "inbound":
            update_ops["$inc"] = {"unread_count": 1}

        await CONVERSATIONS.update_one({"id": conv_id}, update_ops)

    # 2. Insert message
    msg_id = str(uuid.uuid4())
    msg_doc = {
        "id": msg_id,
        "conversation_id": conv_id,
        "phone": clean_phone,
        "direction": direction,
        "sender_type": sender_type,
        "sender_id": sender_id,
        "sender_name": sender_name or ("Client" if direction == "inbound" else "LEAMSS Team"),
        "body": text,
        "media_url": media_url,
        "media_filename": media_filename,
        "status": status,
        "created_at": now,
    }
    await MESSAGES.insert_one(msg_doc)

    return msg_doc


# ── Conversation Management Endpoints ────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(
    search: Optional[str] = None,
    assigned_to: Optional[str] = None,
    status: Optional[str] = None,
    tab: Optional[str] = "all",  # "all", "mine", "unassigned"
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    """List WhatsApp conversations with flexible search, tab, and assignment filters."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to access WhatsApp Inbox")

    user_id = current_user.get("id")
    user_role = current_user.get("rbac_role") or current_user.get("role") or ""
    is_admin = _is_admin(current_user)

    query: Dict[str, Any] = {}

    # Tab logic
    if tab == "mine":
        query["assigned_to"] = user_id
    elif tab == "unassigned":
        query["$or"] = [{"assigned_to": None}, {"assigned_to": ""}, {"assigned_to": {"$exists": False}}]
    elif not is_admin and user_role in ("partner", "sales_executive"):
        if assigned_to:
            query["assigned_to"] = assigned_to
        else:
            query["$or"] = [
                {"assigned_to": user_id},
                {"assigned_to": None},
                {"assigned_to": ""},
                {"assigned_to": {"$exists": False}},
            ]
    else:
        if assigned_to == "unassigned":
            query["$or"] = [{"assigned_to": None}, {"assigned_to": ""}, {"assigned_to": {"$exists": False}}]
        elif assigned_to and assigned_to != "all":
            query["assigned_to"] = assigned_to

    # Status filter
    if status and status != "all":
        query["status"] = status

    # Text Search filter
    if search and search.strip():
        term = re.escape(search.strip())
        rgx = {"$regex": term, "$options": "i"}
        search_filter = {"$or": [{"client_name": rgx}, {"phone": rgx}, {"last_message": rgx}, {"client_email": rgx}]}
        if "$or" in query:
            query = {"$and": [query, search_filter]}
        else:
            query.update(search_filter)

    cursor = CONVERSATIONS.find(query).sort("last_message_at", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        items.append(_clean_doc(doc))

    # Calculate global counters
    total_all = await CONVERSATIONS.count_documents({})
    total_open = await CONVERSATIONS.count_documents({"status": "open"})
    total_unassigned = await CONVERSATIONS.count_documents({
        "$or": [{"assigned_to": None}, {"assigned_to": ""}, {"assigned_to": {"$exists": False}}]
    })
    total_mine = await CONVERSATIONS.count_documents({"assigned_to": user_id}) if user_id else 0

    return {
        "conversations": items,
        "count": len(items),
        "stats": {
            "total_all": total_all,
            "total_open": total_open,
            "total_unassigned": total_unassigned,
            "total_mine": total_mine,
        },
    }


@router.get("/conversations/{conv_id}")
async def get_conversation(
    conv_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve full details for a single WhatsApp conversation."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    conv = await CONVERSATIONS.find_one({"id": conv_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv_clean = _clean_doc(conv)

    # Attach linked assessment details if available
    assessment_data = None
    if conv.get("assessment_id"):
        ass = await ASSESSMENTS.find_one({"id": conv["assessment_id"]})
        if ass:
            assessment_data = {
                "id": ass.get("id"),
                "client_name": ass.get("client_name"),
                "best_country_code": ass.get("best_country_code"),
                "best_total": ass.get("best_total"),
                "occupation": ass.get("occupation"),
                "status": ass.get("status"),
                "share_token": ass.get("share_token"),
            }
    elif conv.get("phone"):
        ass = await ASSESSMENTS.find_one({
            "$or": [{"client_phone": conv["phone"]}, {"whatsapp_to": conv["phone"]}, {"phone": conv["phone"]}]
        })
        if ass:
            assessment_data = {
                "id": ass.get("id"),
                "client_name": ass.get("client_name"),
                "best_country_code": ass.get("best_country_code"),
                "best_total": ass.get("best_total"),
                "occupation": ass.get("occupation"),
                "status": ass.get("status"),
                "share_token": ass.get("share_token"),
            }

    conv_clean["linked_assessment"] = assessment_data
    return conv_clean


@router.get("/conversations/{conv_id}/messages")
async def get_conversation_messages(
    conv_id: str,
    limit: int = 150,
    current_user: dict = Depends(get_current_user),
):
    """Fetch message history for a conversation and clear unread count."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    conv = await CONVERSATIONS.find_one({"id": conv_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Reset unread counter since staff is viewing the thread
    await CONVERSATIONS.update_one({"id": conv_id}, {"$set": {"unread_count": 0}})

    cursor = MESSAGES.find({"conversation_id": conv_id}).sort("created_at", 1).limit(limit)
    messages = []
    async for m in cursor:
        messages.append(_clean_doc(m))

    return {
        "conversation_id": conv_id,
        "messages": messages,
    }


@router.post("/conversations/{conv_id}/send")
async def send_chat_message(
    conv_id: str,
    req: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """Send an outbound WhatsApp message in this conversation and log to thread."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    conv = await CONVERSATIONS.find_one({"id": conv_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    phone = conv.get("phone")
    if not phone:
        raise HTTPException(status_code=400, detail="Conversation has no valid phone number")

    text_to_send = req.text.strip()
    if not text_to_send:
        raise HTTPException(status_code=400, detail="Message text cannot be empty")

    sender_name = current_user.get("name") or current_user.get("email") or "Staff"
    sender_id = current_user.get("id")

    # Check WhatsApp API configuration
    cfg = await get_whatsapp_config()
    send_status = "sent"
    api_error = None

    if cfg.get("is_configured"):
        try:
            await send_whatsapp_text(to_phone=phone, text=text_to_send)
            send_status = "sent"
        except Exception as exc:
            logger.warning("Live WhatsApp send encountered error: %s (recording message to chat thread)", exc)
            api_error = str(exc)
            send_status = "failed"
    else:
        send_status = "simulated"

    # Save to database
    msg = await record_chat_message(
        phone=phone,
        text=text_to_send,
        direction="outbound",
        sender_type="staff",
        sender_id=sender_id,
        sender_name=sender_name,
        client_name=conv.get("client_name"),
        client_email=conv.get("client_email"),
        assessment_id=conv.get("assessment_id"),
        status=send_status,
        media_url=req.media_url,
        media_filename=req.media_filename,
    )

    return {
        "success": send_status in ("sent", "simulated"),
        "message": _clean_doc(msg),
        "api_error": api_error,
        "is_simulated": send_status == "simulated",
    }


@router.post("/conversations/{conv_id}/assign")
async def assign_conversation(
    conv_id: str,
    req: AssignChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Admin or Team Lead assigns a conversation to a specific partner/agent."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    conv = await CONVERSATIONS.find_one({"id": conv_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    assigned_by_name = current_user.get("name") or current_user.get("email") or "Admin"
    now = datetime.now(timezone.utc)

    assigned_to = req.user_id
    assigned_to_name = req.user_name

    # If user_id provided without name, lookup in DB
    if assigned_to and not assigned_to_name:
        target_user = await USERS.find_one({"id": assigned_to})
        if target_user:
            assigned_to_name = target_user.get("name") or target_user.get("email")

    await CONVERSATIONS.update_one(
        {"id": conv_id},
        {
            "$set": {
                "assigned_to": assigned_to,
                "assigned_to_name": assigned_to_name if assigned_to else None,
                "assigned_by": assigned_by_name if assigned_to else None,
                "assigned_at": now if assigned_to else None,
                "updated_at": now,
            }
        },
    )

    # Add audit note
    action_text = f"Assigned to {assigned_to_name} by {assigned_by_name}" if assigned_to else f"Unassigned by {assigned_by_name}"
    note_id = str(uuid.uuid4())
    note_doc = {
        "id": note_id,
        "author_name": assigned_by_name,
        "text": f"📋 [System Note] {action_text}",
        "created_at": now.isoformat(),
    }
    await CONVERSATIONS.update_one({"id": conv_id}, {"$push": {"notes": note_doc}})

    return {
        "success": True,
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_to_name,
        "note": note_doc,
    }


@router.post("/conversations/{conv_id}/status")
async def update_conversation_status(
    conv_id: str,
    req: UpdateStatusRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update conversation status: open, in_progress, qualified, closed."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    valid_statuses = {"open", "in_progress", "qualified", "closed"}
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    now = datetime.now(timezone.utc)
    res = await CONVERSATIONS.update_one(
        {"id": conv_id},
        {"$set": {"status": req.status, "updated_at": now}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"success": True, "status": req.status}


@router.post("/conversations/{conv_id}/notes")
async def add_internal_note(
    conv_id: str,
    req: AddNoteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a private staff/partner internal note to a WhatsApp conversation."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Note text cannot be empty")

    author = current_user.get("name") or current_user.get("email") or "Staff"
    now = datetime.now(timezone.utc)
    note_id = str(uuid.uuid4())

    note_doc = {
        "id": note_id,
        "author_name": author,
        "author_id": current_user.get("id"),
        "text": req.text.strip(),
        "created_at": now.isoformat(),
    }

    res = await CONVERSATIONS.update_one(
        {"id": conv_id},
        {"$push": {"notes": note_doc}, "$set": {"updated_at": now}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"success": True, "note": note_doc}


@router.post("/conversations/create-or-get")
async def create_or_get_conversation(
    req: CreateConversationRequest,
    current_user: dict = Depends(get_current_user),
):
    """Find existing or start a new WhatsApp conversation thread for a phone number."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    clean_phone = normalize_phone_number(req.phone)
    if not clean_phone:
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    conv = await CONVERSATIONS.find_one({"phone": clean_phone})
    if conv:
        return {"conversation": _clean_doc(conv), "is_new": False}

    now = datetime.now(timezone.utc)
    conv_id = str(uuid.uuid4())
    conv = {
        "id": conv_id,
        "phone": clean_phone,
        "client_name": req.client_name or "Applicant",
        "client_email": req.client_email,
        "assessment_id": req.assessment_id,
        "assigned_to": current_user.get("id") if not _is_admin(current_user) else None,
        "assigned_to_name": current_user.get("name") if not _is_admin(current_user) else None,
        "assigned_by": current_user.get("name") if not _is_admin(current_user) else None,
        "assigned_at": now if not _is_admin(current_user) else None,
        "status": "open",
        "last_message": req.initial_message or "Conversation started",
        "last_message_at": now,
        "last_message_direction": "outbound",
        "unread_count": 0,
        "tags": [],
        "notes": [],
        "created_at": now,
        "updated_at": now,
    }
    await CONVERSATIONS.insert_one(conv)

    if req.initial_message:
        await record_chat_message(
            phone=clean_phone,
            text=req.initial_message,
            direction="outbound",
            sender_type="staff",
            sender_id=current_user.get("id"),
            sender_name=current_user.get("name"),
            client_name=req.client_name,
            client_email=req.client_email,
            assessment_id=req.assessment_id,
            status="sent",
        )

    return {"conversation": _clean_doc(conv), "is_new": True}


# ── Metadata & Directory Endpoints ───────────────────────────────────────────

@router.get("/assignable-users")
async def list_assignable_users(current_user: dict = Depends(get_current_user)):
    """List staff and partners eligible to be assigned WhatsApp conversations."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    cursor = USERS.find(
        {
            "$or": [
                {"role": {"$in": ["admin", "admin_owner", "partner", "sales_executive", "case_manager"]}},
                {"rbac_role": {"$in": ["admin", "admin_owner", "partner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "case_manager"]}},
            ]
        },
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1, "rbac_role": 1, "status": 1}
    )
    users = []
    async for u in cursor:
        users.append(u)

    return {"users": users}


@router.get("/canned-templates")
async def list_canned_templates(current_user: dict = Depends(get_current_user)):
    """Fetch saved templates from whatsapp_templates collection for one-click chat insertion."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    cursor = TEMPLATES.find({}).sort("name", 1)
    templates = []
    async for doc in cursor:
        templates.append(_clean_doc(doc))
    return {"templates": templates}


# ── Meta Cloud API Webhook Handling ──────────────────────────────────────────

@router.get("/webhook")
async def meta_webhook_verify(
    request: Request,
):
    """Meta Webhook Challenge Verification (GET)."""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    expected_token = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN") or "leamss_whatsapp_verify_token_2026"

    if mode == "subscribe" and token == expected_token:
        logger.info("Meta WhatsApp Webhook successfully verified!")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Meta WhatsApp Webhook verification failed. Received token: %s", token)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/webhook")
async def meta_webhook_receive(request: Request):
    """Meta Webhook Inbound Event Receiver (POST)."""
    try:
        body = await request.json()
    except Exception:
        return {"status": "ignored_non_json"}

    logger.info("WhatsApp Webhook payload received: %s", body)

    entries = body.get("entry") or []
    for entry in entries:
        changes = entry.get("changes") or []
        for change in changes:
            value = change.get("value") or {}
            messages = value.get("messages") or []
            contacts = value.get("contacts") or []

            name_map = {}
            for c in contacts:
                wa_id = c.get("wa_id")
                profile_name = (c.get("profile") or {}).get("name")
                if wa_id and profile_name:
                    name_map[wa_id] = profile_name

            for msg in messages:
                from_phone = msg.get("from")
                msg_type = msg.get("type")
                msg_text = ""
                media_url = None
                media_filename = None

                if msg_type == "text":
                    msg_text = (msg.get("text") or {}).get("body", "")
                elif msg_type == "button":
                    msg_text = (msg.get("button") or {}).get("text", "")
                elif msg_type == "interactive":
                    interactive = msg.get("interactive") or {}
                    btn_reply = interactive.get("button_reply") or {}
                    list_reply = interactive.get("list_reply") or {}
                    msg_text = btn_reply.get("title") or list_reply.get("title") or "Interactive Response"
                elif msg_type in ("image", "document", "audio", "video"):
                    doc_obj = msg.get(msg_type) or {}
                    msg_text = doc_obj.get("caption") or f"[{msg_type.capitalize()} Attachment]"
                    media_filename = doc_obj.get("filename")

                if from_phone and msg_text:
                    client_name = name_map.get(from_phone) or "WhatsApp User"
                    try:
                        await record_chat_message(
                            phone=from_phone,
                            text=msg_text,
                            direction="inbound",
                            sender_type="client",
                            sender_name=client_name,
                            client_name=client_name,
                            status="received",
                            media_url=media_url,
                            media_filename=media_filename,
                        )
                    except Exception as e:
                        logger.error("Error recording inbound WhatsApp message: %s", e)

            # Handle status delivery receipts (sent, delivered, read)
            statuses = value.get("statuses") or []
            for st in statuses:
                st_id = st.get("id")
                st_status = st.get("status")
                if st_id and st_status:
                    await MESSAGES.update_many(
                        {"meta_message_id": st_id},
                        {"$set": {"status": st_status}}
                    )

    return {"status": "processed"}


# ── Inbound Testing Simulator ────────────────────────────────────────────────

@router.post("/simulate-inbound")
async def simulate_inbound_message(
    req: SimulateInboundRequest,
    current_user: dict = Depends(get_current_user),
):
    """Test Tool: Simulate an incoming WhatsApp reply from a client for testing."""
    if not _has_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    clean_phone = normalize_phone_number(req.phone)
    if not clean_phone:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    msg = await record_chat_message(
        phone=clean_phone,
        text=text,
        direction="inbound",
        sender_type="client",
        sender_name=req.client_name or "Applicant",
        client_name=req.client_name,
        status="received",
    )

    return {
        "success": True,
        "simulated": True,
        "message": _clean_doc(msg),
    }
