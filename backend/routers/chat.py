"""Chat Router — Real-time messaging between Client and Case Manager"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from core.database import (
    chat_messages_col, chat_conversations_col, cases_col, users_col
)
from core.auth import get_current_user
from core.services import log_activity, create_notification

router = APIRouter(prefix="/chat", tags=["Chat"])


class SendMessageRequest(BaseModel):
    conversation_id: str
    message: str


class StartConversationRequest(BaseModel):
    case_id: str
    subject: Optional[str] = ""


@router.get("/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Get all conversations for current user"""
    role = current_user["role"]
    uid = current_user["id"]

    if role == "client":
        cases = await cases_col.find({"client_id": uid}, {"_id": 0, "id": 1}).to_list(100)
        case_ids = [c["id"] for c in cases]
        query = {"case_id": {"$in": case_ids}}
    elif role == "case_manager":
        cases = await cases_col.find({"case_manager_id": uid}, {"_id": 0, "id": 1}).to_list(100)
        case_ids = [c["id"] for c in cases]
        query = {"case_id": {"$in": case_ids}}
    elif role == "admin":
        query = {}
    else:
        return []

    convos = await chat_conversations_col.find(query, {"_id": 0}).sort("updated_at", -1).to_list(100)

    for c in convos:
        if isinstance(c.get("created_at"), datetime):
            c["created_at"] = c["created_at"].isoformat()
        if isinstance(c.get("updated_at"), datetime):
            c["updated_at"] = c["updated_at"].isoformat()
        # Get unread count for current user
        unread = await chat_messages_col.count_documents({
            "conversation_id": c["id"],
            "sender_id": {"$ne": uid},
            "read": False
        })
        c["unread_count"] = unread

    return convos


@router.post("/conversations")
async def start_conversation(
    request: StartConversationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start a new conversation for a case"""
    case = await cases_col.find_one({"id": request.case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check if conversation already exists for this case
    existing = await chat_conversations_col.find_one(
        {"case_id": request.case_id}, {"_id": 0}
    )
    if existing:
        return existing

    # Get participant info
    client = await users_col.find_one({"id": case["client_id"]}, {"_id": 0, "id": 1, "name": 1})
    cm = None
    if case.get("case_manager_id"):
        cm = await users_col.find_one({"id": case["case_manager_id"]}, {"_id": 0, "id": 1, "name": 1})

    convo = {
        "id": str(uuid.uuid4()),
        "case_id": request.case_id,
        "case_display_id": case.get("case_id", ""),
        "subject": request.subject or f"Chat - {case.get('case_id', '')}",
        "client_id": case["client_id"],
        "client_name": client["name"] if client else "",
        "case_manager_id": case.get("case_manager_id", ""),
        "case_manager_name": cm["name"] if cm else "Unassigned",
        "product_name": case.get("product_name", ""),
        "last_message": "",
        "last_message_at": None,
        "message_count": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await chat_conversations_col.insert_one(convo)

    convo["created_at"] = convo["created_at"].isoformat()
    convo["updated_at"] = convo["updated_at"].isoformat()

    return convo


@router.get("/messages/{conversation_id}")
async def get_messages(
    conversation_id: str,
    limit: int = Query(50),
    before: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get messages for a conversation"""
    convo = await chat_conversations_col.find_one({"id": conversation_id}, {"_id": 0})
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Access check
    uid = current_user["id"]
    role = current_user["role"]
    if role not in ["admin"] and uid != convo.get("client_id") and uid != convo.get("case_manager_id"):
        raise HTTPException(status_code=403, detail="Access denied")

    query = {"conversation_id": conversation_id}
    if before:
        query["created_at"] = {"$lt": datetime.fromisoformat(before)}

    messages = await chat_messages_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    messages.reverse()

    # Mark as read
    await chat_messages_col.update_many(
        {"conversation_id": conversation_id, "sender_id": {"$ne": uid}, "read": False},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc)}}
    )

    for m in messages:
        if isinstance(m.get("created_at"), datetime):
            m["created_at"] = m["created_at"].isoformat()
        if isinstance(m.get("read_at"), datetime):
            m["read_at"] = m["read_at"].isoformat()

    return messages


@router.post("/messages")
async def send_message(
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message in a conversation"""
    convo = await chat_conversations_col.find_one({"id": request.conversation_id}, {"_id": 0})
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    uid = current_user["id"]
    role = current_user["role"]
    if role not in ["admin"] and uid != convo.get("client_id") and uid != convo.get("case_manager_id"):
        raise HTTPException(status_code=403, detail="Access denied")

    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": request.conversation_id,
        "sender_id": uid,
        "sender_name": current_user.get("name", ""),
        "sender_role": role,
        "message": request.message,
        "read": False,
        "created_at": datetime.now(timezone.utc),
    }
    await chat_messages_col.insert_one(msg)

    # Update conversation
    await chat_conversations_col.update_one(
        {"id": request.conversation_id},
        {"$set": {
            "last_message": request.message[:100],
            "last_message_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }, "$inc": {"message_count": 1}}
    )

    # Notify the other party
    recipient_id = convo["client_id"] if uid != convo["client_id"] else convo.get("case_manager_id")
    if recipient_id:
        await create_notification(
            recipient_id,
            f"New message from {current_user.get('name', '')}",
            request.message[:100],
            "chat",
            request.conversation_id
        )

    # Send email notification
    try:
        from core.email_service import send_ticket_update_email
        recipient = await users_col.find_one({"id": recipient_id}, {"_id": 0, "email": 1, "name": 1})
        if recipient:
            await send_ticket_update_email(
                recipient["email"], recipient["name"],
                convo.get("subject", "Chat"), request.message[:200]
            )
    except Exception:
        pass

    msg["created_at"] = msg["created_at"].isoformat()
    return msg


@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get total unread message count for current user"""
    uid = current_user["id"]
    role = current_user["role"]

    if role == "client":
        cases = await cases_col.find({"client_id": uid}, {"_id": 0, "id": 1}).to_list(100)
    elif role == "case_manager":
        cases = await cases_col.find({"case_manager_id": uid}, {"_id": 0, "id": 1}).to_list(100)
    elif role == "admin":
        return {"unread": 0}
    else:
        return {"unread": 0}

    case_ids = [c["id"] for c in cases]
    convos = await chat_conversations_col.find(
        {"case_id": {"$in": case_ids}}, {"_id": 0, "id": 1}
    ).to_list(100)
    convo_ids = [c["id"] for c in convos]

    if not convo_ids:
        return {"unread": 0}

    count = await chat_messages_col.count_documents({
        "conversation_id": {"$in": convo_ids},
        "sender_id": {"$ne": uid},
        "read": False
    })
    return {"unread": count}
