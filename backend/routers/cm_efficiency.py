"""Phase 11: Case Manager Efficiency Router
- 11A: Smart Workload View
- 11B: Client Communication Hub
- 11C: Batch Case Operations
"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from core.database import (
    db, cases_col, case_steps_col, users_col, documents_col,
    notifications_col, audit_logs_col, tickets_col
)
from core.auth import get_current_user
from core.services import log_activity

router = APIRouter(prefix="/cm-tools", tags=["CM Efficiency"])

cm_messages_col = db["cm_client_messages"]


# ===================== 11A: SMART WORKLOAD VIEW =====================

@router.get("/workload")
async def get_smart_workload(current_user: dict = Depends(get_current_user)):
    """Get smart workload data for case manager"""
    if current_user["role"] not in ["case_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Case Manager or Admin only")

    cm_id = current_user["id"]
    if current_user["role"] == "admin":
        cm_id = None  # Admin sees all

    query = {"case_manager_id": cm_id} if cm_id else {}
    my_cases = await cases_col.find(query, {"_id": 0}).to_list(500)

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # Categorize cases
    urgent_cases = []
    overdue_cases = []
    due_today = []
    upcoming_cases = []
    on_track = []

    for c in my_cases:
        if c.get("status") not in ["active", "in_progress"]:
            continue

        case_id = c.get("id", "")
        # Get steps for this case
        steps = await case_steps_col.find(
            {"case_id": case_id, "status": {"$in": ["pending", "in_progress"]}}, {"_id": 0}
        ).to_list(50)

        has_overdue = False
        has_due_today = False
        nearest_deadline = None

        for step in steps:
            deadline = step.get("deadline")
            if deadline:
                if isinstance(deadline, str):
                    deadline_date = deadline[:10]
                elif isinstance(deadline, datetime):
                    deadline_date = deadline.strftime("%Y-%m-%d")
                else:
                    continue

                if deadline_date < today_str:
                    has_overdue = True
                elif deadline_date == today_str:
                    has_due_today = True

                if nearest_deadline is None or deadline_date < nearest_deadline:
                    nearest_deadline = deadline_date

        # Pending docs count
        pending_docs = await documents_col.count_documents({
            "case_id": case_id,
            "status": {"$in": ["pending", "uploaded", "pending_review"]}
        })

        case_info = {
            "id": c["id"],
            "case_id": c.get("case_id", ""),
            "client_name": c.get("client_name", ""),
            "product_name": c.get("product_name", ""),
            "status": c.get("status", ""),
            "current_step": c.get("current_step", ""),
            "current_step_order": c.get("current_step_order", 0),
            "total_steps": len(await case_steps_col.find({"case_id": case_id}, {"_id": 0}).to_list(50)),
            "pending_docs": pending_docs,
            "nearest_deadline": nearest_deadline,
            "created_at": c.get("created_at").isoformat() if isinstance(c.get("created_at"), datetime) else str(c.get("created_at", "")),
        }

        if has_overdue:
            case_info["priority"] = "overdue"
            overdue_cases.append(case_info)
        elif has_due_today:
            case_info["priority"] = "due_today"
            due_today.append(case_info)
        elif pending_docs > 0:
            case_info["priority"] = "action_needed"
            urgent_cases.append(case_info)
        elif nearest_deadline and nearest_deadline <= (now + timedelta(days=7)).strftime("%Y-%m-%d"):
            case_info["priority"] = "upcoming"
            upcoming_cases.append(case_info)
        else:
            case_info["priority"] = "on_track"
            on_track.append(case_info)

    # Workload score (0-100)
    total_active = len(overdue_cases) + len(due_today) + len(urgent_cases) + len(upcoming_cases) + len(on_track)
    overdue_weight = len(overdue_cases) * 3
    due_today_weight = len(due_today) * 2
    urgent_weight = len(urgent_cases) * 1.5
    workload_score = min(100, round((overdue_weight + due_today_weight + urgent_weight + total_active) / max(1, total_active) * 20))

    return {
        "overdue": overdue_cases,
        "due_today": due_today,
        "action_needed": urgent_cases,
        "upcoming": upcoming_cases,
        "on_track": on_track,
        "summary": {
            "total_active": total_active,
            "overdue_count": len(overdue_cases),
            "due_today_count": len(due_today),
            "action_needed_count": len(urgent_cases),
            "upcoming_count": len(upcoming_cases),
            "on_track_count": len(on_track),
            "workload_score": workload_score,
        }
    }


# ===================== 11B: CLIENT COMMUNICATION HUB =====================

class SendMessage(BaseModel):
    case_id: str
    client_id: str
    message: str
    message_type: str = "text"  # text, update, reminder, document_request


@router.get("/communications/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get unread message count for case manager"""
    if current_user["role"] not in ["case_manager", "admin"]:
        return {"count": 0}

    # Get all cases for this CM
    cm_cases = await cases_col.find(
        {"case_manager_id": current_user["id"]}, {"_id": 0, "id": 1}
    ).to_list(500)
    case_ids = [c["id"] for c in cm_cases]

    if not case_ids:
        return {"count": 0}

    count = await cm_messages_col.count_documents({
        "case_id": {"$in": case_ids},
        "sender_role": {"$ne": "case_manager"},
        "read": False
    })
    return {"count": count}


@router.get("/communications/{case_id}")
async def get_communications(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get all communications for a case (CM, Admin, or Client who owns the case)"""
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Access check: CM/Admin or the client who owns the case
    if current_user["role"] not in ["case_manager", "admin"]:
        if current_user["id"] != case.get("client_id"):
            raise HTTPException(status_code=403, detail="Access denied")

    messages = await cm_messages_col.find(
        {"case_id": case_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(500)

    for m in messages:
        if isinstance(m.get("created_at"), datetime):
            m["created_at"] = m["created_at"].isoformat()

    client = await users_col.find_one({"id": case.get("client_id")}, {"_id": 0, "name": 1, "email": 1})

    return {
        "messages": messages,
        "case_id": case.get("case_id", ""),
        "client_name": client["name"] if client else case.get("client_name", ""),
        "client_email": client["email"] if client else "",
    }


@router.post("/communications/send")
async def send_message(data: SendMessage, current_user: dict = Depends(get_current_user)):
    """Send a message to client from case manager"""
    if current_user["role"] not in ["case_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Case Manager or Admin only")

    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    msg = {
        "id": str(uuid.uuid4()),
        "case_id": data.case_id,
        "client_id": data.client_id,
        "sender_id": current_user["id"],
        "sender_name": current_user.get("name", ""),
        "sender_role": current_user["role"],
        "message": data.message.strip(),
        "message_type": data.message_type,
        "read": False,
        "created_at": datetime.now(timezone.utc),
    }
    await cm_messages_col.insert_one(msg)
    msg.pop("_id", None)
    msg["created_at"] = msg["created_at"].isoformat()

    # Notify client
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": data.client_id,
        "title": f"Message from {current_user.get('name', 'Case Manager')}",
        "message": data.message[:100] + ("..." if len(data.message) > 100 else ""),
        "type": "cm_message",
        "read": False,
        "link": "/client",
        "created_at": datetime.now(timezone.utc),
    })

    return {"message": "Message sent", "data": msg}


@router.post("/communications/reply")
async def client_reply(data: SendMessage, current_user: dict = Depends(get_current_user)):
    """Client replies to case manager"""
    msg = {
        "id": str(uuid.uuid4()),
        "case_id": data.case_id,
        "client_id": data.client_id,
        "sender_id": current_user["id"],
        "sender_name": current_user.get("name", ""),
        "sender_role": current_user["role"],
        "message": data.message.strip(),
        "message_type": data.message_type,
        "read": False,
        "created_at": datetime.now(timezone.utc),
    }
    await cm_messages_col.insert_one(msg)
    msg.pop("_id", None)
    msg["created_at"] = msg["created_at"].isoformat()

    # Notify case manager
    case = await cases_col.find_one({"id": data.case_id}, {"_id": 0, "case_manager_id": 1})
    if case and case.get("case_manager_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": case["case_manager_id"],
            "title": f"Reply from {current_user.get('name', 'Client')}",
            "message": data.message[:100],
            "type": "client_reply",
            "read": False,
            "created_at": datetime.now(timezone.utc),
        })

    return {"message": "Reply sent", "data": msg}


@router.put("/communications/{case_id}/mark-read")
async def mark_messages_read(case_id: str, current_user: dict = Depends(get_current_user)):
    """Mark all messages in a case as read"""
    await cm_messages_col.update_many(
        {"case_id": case_id, "read": False, "sender_id": {"$ne": current_user["id"]}},
        {"$set": {"read": True}}
    )


@router.get("/client-messages")
async def get_client_messages(current_user: dict = Depends(get_current_user)):
    """Get all case-based conversations for a client"""
    # Get client's cases
    my_cases = await cases_col.find(
        {"client_id": current_user["id"]}, {"_id": 0}
    ).to_list(50)

    conversations = []
    for case in my_cases:
        case_id = case["id"]
        # Get last message
        last_msg = await cm_messages_col.find(
            {"case_id": case_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(1)

        unread = await cm_messages_col.count_documents({
            "case_id": case_id,
            "sender_id": {"$ne": current_user["id"]},
            "read": False
        })

        cm = await users_col.find_one({"id": case.get("case_manager_id")}, {"_id": 0, "name": 1})

        conversations.append({
            "case_id": case_id,
            "case_display_id": case.get("case_id", ""),
            "product_name": case.get("product_name", ""),
            "case_manager_name": cm["name"] if cm else "Unassigned",
            "last_message": last_msg[0]["message"][:80] if last_msg else "",
            "last_message_at": last_msg[0]["created_at"].isoformat() if last_msg and isinstance(last_msg[0].get("created_at"), datetime) else "",
            "unread_count": unread,
            "has_messages": len(last_msg) > 0,
        })

    return sorted(conversations, key=lambda x: x.get("last_message_at", ""), reverse=True)


class ClientSendMessage(BaseModel):
    case_id: str
    message: str


@router.post("/client-messages/send")
async def client_send_message(data: ClientSendMessage, current_user: dict = Depends(get_current_user)):
    """Client sends a message to their case manager"""
    case = await cases_col.find_one({"id": data.case_id, "client_id": current_user["id"]}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or not yours")

    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    msg = {
        "id": str(uuid.uuid4()),
        "case_id": data.case_id,
        "client_id": current_user["id"],
        "sender_id": current_user["id"],
        "sender_name": current_user.get("name", ""),
        "sender_role": "client",
        "message": data.message.strip(),
        "message_type": "text",
        "read": False,
        "created_at": datetime.now(timezone.utc),
    }
    await cm_messages_col.insert_one(msg)
    msg.pop("_id", None)
    msg["created_at"] = msg["created_at"].isoformat()

    # Notify case manager
    if case.get("case_manager_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": case["case_manager_id"],
            "title": f"Message from {current_user.get('name', 'Client')}",
            "message": data.message[:100],
            "type": "client_message",
            "read": False,
            "created_at": datetime.now(timezone.utc),
        })

    return {"message": "Message sent", "data": msg}


    return {"message": "Messages marked as read"}


# ===================== 11C: BATCH CASE OPERATIONS =====================

class BatchStatusUpdate(BaseModel):
    case_ids: List[str]
    action: str  # "add_note", "change_status", "send_notification"
    value: str = ""
    notes: str = ""


@router.post("/batch-operations")
async def batch_case_operation(data: BatchStatusUpdate, current_user: dict = Depends(get_current_user)):
    """Perform batch operations on multiple cases"""
    if current_user["role"] not in ["case_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Case Manager or Admin only")

    if not data.case_ids:
        raise HTTPException(status_code=400, detail="No cases selected")

    results = {"success": 0, "failed": 0, "errors": []}

    for case_id in data.case_ids:
        try:
            case = await cases_col.find_one({"id": case_id}, {"_id": 0})
            if not case:
                results["failed"] += 1
                results["errors"].append(f"Case {case_id} not found")
                continue

            if data.action == "add_note":
                if not data.notes.strip():
                    results["failed"] += 1
                    results["errors"].append("Note cannot be empty")
                    continue
                from core.database import case_notes_col
                await case_notes_col.insert_one({
                    "id": str(uuid.uuid4()),
                    "case_id": case_id,
                    "user_id": current_user["id"],
                    "user_name": current_user.get("name", ""),
                    "content": data.notes.strip(),
                    "type": "batch_note",
                    "created_at": datetime.now(timezone.utc),
                })
                results["success"] += 1

            elif data.action == "change_status":
                if data.value not in ["active", "on_hold", "completed"]:
                    results["failed"] += 1
                    results["errors"].append(f"Invalid status: {data.value}")
                    continue
                update_data = {"status": data.value}
                if data.value == "completed":
                    update_data["completed_at"] = datetime.now(timezone.utc)
                await cases_col.update_one({"id": case_id}, {"$set": update_data})
                await log_activity(current_user["id"], current_user.get("name", ""),
                                   f"batch_status_{data.value}", "case", case_id,
                                   f"Status changed to {data.value} (batch)")
                results["success"] += 1

            elif data.action == "send_notification":
                if not data.notes.strip():
                    results["failed"] += 1
                    results["errors"].append("Notification message cannot be empty")
                    continue
                client_id = case.get("client_id")
                if client_id:
                    await notifications_col.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": client_id,
                        "title": "Case Update from Your Manager",
                        "message": data.notes.strip(),
                        "type": "batch_notification",
                        "read": False,
                        "created_at": datetime.now(timezone.utc),
                    })
                results["success"] += 1

            elif data.action == "request_documents":
                client_id = case.get("client_id")
                if client_id and data.notes.strip():
                    await notifications_col.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": client_id,
                        "title": "Document Request",
                        "message": f"Your case manager has requested: {data.notes.strip()}",
                        "type": "document_request",
                        "read": False,
                        "created_at": datetime.now(timezone.utc),
                    })
                    # Also add as a CM message
                    await cm_messages_col.insert_one({
                        "id": str(uuid.uuid4()),
                        "case_id": case_id,
                        "client_id": client_id,
                        "sender_id": current_user["id"],
                        "sender_name": current_user.get("name", ""),
                        "sender_role": "case_manager",
                        "message": f"Document Request: {data.notes.strip()}",
                        "message_type": "document_request",
                        "read": False,
                        "created_at": datetime.now(timezone.utc),
                    })
                results["success"] += 1

            else:
                results["failed"] += 1
                results["errors"].append(f"Unknown action: {data.action}")

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(str(e))

    # Log batch operation
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "action": f"batch_{data.action}",
        "entity_type": "case",
        "entity_id": ",".join(data.case_ids[:5]),
        "new_value": {
            "action": data.action,
            "cases_count": len(data.case_ids),
            "success": results["success"],
            "failed": results["failed"],
        },
        "created_at": datetime.now(timezone.utc),
    })

    return {
        "message": f"Batch operation completed: {results['success']} success, {results['failed']} failed",
        **results
    }


@router.get("/my-cases-summary")
async def get_my_cases_summary(current_user: dict = Depends(get_current_user)):
    """Get a quick summary of all cases for batch selection"""
    if current_user["role"] not in ["case_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Case Manager or Admin only")

    query = {"case_manager_id": current_user["id"]} if current_user["role"] == "case_manager" else {}
    my_cases = await cases_col.find(
        {**query, "status": {"$in": ["active", "in_progress"]}}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)

    result = []
    for c in my_cases:
        result.append({
            "id": c["id"],
            "case_id": c.get("case_id", ""),
            "client_name": c.get("client_name", ""),
            "client_id": c.get("client_id", ""),
            "product_name": c.get("product_name", ""),
            "status": c.get("status", ""),
            "current_step": c.get("current_step", ""),
        })

    return result
