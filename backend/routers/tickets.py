"""
Ticket/Support system routes for LEAMSS Portal
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
import io

from core.database import db, fs
from core.auth import get_current_user, require_role, UserRole
from core.models import TicketCreate, TicketResponse, TicketMessage, TicketStatusUpdate
from services.notification_service import create_notification

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def add_activity_log(activity_log: list, action: str, user: dict, details: str = None) -> list:
    """Add an entry to the activity log"""
    activity_log.append({
        "action": action,
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user["role"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details
    })
    return activity_log


@router.get("/stats")
async def get_ticket_stats(user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Get ticket statistics (Admin only)"""
    total = await db.tickets.count_documents({})
    open_tickets = await db.tickets.count_documents({"status": "open"})
    in_progress = await db.tickets.count_documents({"status": "in_progress"})
    resolved = await db.tickets.count_documents({"status": "resolved"})
    closed = await db.tickets.count_documents({"status": "closed"})
    
    # Get counts by priority
    high_priority = await db.tickets.count_documents({"priority": "high", "status": {"$nin": ["resolved", "closed"]}})
    
    # Get counts by category
    categories = await db.tickets.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    return {
        "total": total,
        "open": open_tickets,
        "in_progress": in_progress,
        "resolved": resolved,
        "closed": closed,
        "high_priority": high_priority,
        "by_category": {c["_id"]: c["count"] for c in categories}
    }


@router.get("/all", response_model=List[TicketResponse])
async def get_all_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    user: dict = Depends(require_role([UserRole.ADMIN, UserRole.CASE_MANAGER]))
):
    """Get all tickets with optional filters"""
    query = {}
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    if category:
        query["category"] = category
    
    # Case managers only see tickets assigned to them or created by them
    if user["role"] == UserRole.CASE_MANAGER:
        query["$or"] = [
            {"created_by": user["id"]},
            {"target_user_ids": user["id"]}
        ]
    
    tickets = await db.tickets.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [TicketResponse(**t) for t in tickets]


@router.get("/my-tickets", response_model=List[TicketResponse])
async def get_my_tickets(user: dict = Depends(get_current_user)):
    """Get tickets for current user"""
    query = {
        "$or": [
            {"created_by": user["id"]},
            {"target_user_ids": user["id"]}
        ]
    }
    tickets = await db.tickets.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [TicketResponse(**t) for t in tickets]


@router.get("/{ticket_id}")
async def get_ticket_details(ticket_id: str, user: dict = Depends(get_current_user)):
    """Get ticket details"""
    ticket = await db.tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access
    can_access = (
        user["role"] == UserRole.ADMIN or
        ticket["created_by"] == user["id"] or
        user["id"] in ticket.get("target_user_ids", [])
    )
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return TicketResponse(**ticket)


@router.post("", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate, user: dict = Depends(get_current_user)):
    """Create a new support ticket"""
    ticket_doc = {
        "id": str(ObjectId()),
        "case_id": ticket.case_id,
        "created_by": user["id"],
        "created_by_name": user["name"],
        "created_by_role": user["role"],
        "subject": ticket.subject,
        "category": ticket.category,
        "priority": ticket.priority,
        "description": ticket.description,
        "status": "open",
        "messages": [],
        "target_user_ids": ticket.target_user_ids or [],
        "target_role": ticket.target_role,
        "activity_log": [],
        "attachments": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add activity log entry
    ticket_doc["activity_log"] = add_activity_log([], "created", user, f"Ticket created: {ticket.subject}")
    
    # If no specific targets, notify based on role
    if not ticket.target_user_ids and not ticket.target_role:
        if user["role"] == UserRole.CLIENT:
            # Get case manager for the client's case
            if ticket.case_id:
                case = await db.cases.find_one({"id": ticket.case_id})
                if case:
                    ticket_doc["target_user_ids"] = [case["case_manager_id"]]
            else:
                # Notify all admins
                admins = await db.users.find({"role": UserRole.ADMIN}).to_list(100)
                ticket_doc["target_user_ids"] = [a["id"] for a in admins]
        elif user["role"] in [UserRole.CASE_MANAGER, UserRole.PARTNER]:
            # Notify all admins
            admins = await db.users.find({"role": UserRole.ADMIN}).to_list(100)
            ticket_doc["target_user_ids"] = [a["id"] for a in admins]
    
    await db.tickets.insert_one(ticket_doc)
    
    # Notify target users
    for target_id in ticket_doc["target_user_ids"]:
        await create_notification(
            target_id,
            f"New Ticket: {ticket.subject}",
            f"A new {ticket.priority} priority ticket has been created by {user['name']}",
            "ticket_created",
            ticket_doc["id"]
        )
    
    return TicketResponse(**ticket_doc)


@router.put("/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str, 
    status_update: TicketStatusUpdate, 
    user: dict = Depends(get_current_user)
):
    """Update ticket status"""
    ticket = await db.tickets.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access
    can_update = (
        user["role"] == UserRole.ADMIN or
        ticket["created_by"] == user["id"] or
        user["id"] in ticket.get("target_user_ids", [])
    )
    if not can_update:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = {"status": status_update.status}
    
    # Require resolution note for resolved/closed status
    if status_update.status in ["resolved", "closed"]:
        if not status_update.resolution_note:
            raise HTTPException(
                status_code=400, 
                detail="Resolution note is required when resolving or closing a ticket"
            )
        update_data["resolution_note"] = status_update.resolution_note
        update_data["resolved_by"] = user["id"]
        update_data["resolved_by_name"] = user["name"]
        update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()
    
    # Add activity log
    activity_log = ticket.get("activity_log", [])
    details = f"Status changed to {status_update.status}"
    if status_update.resolution_note:
        details += f". Resolution: {status_update.resolution_note}"
    activity_log = add_activity_log(activity_log, "status_changed", user, details)
    update_data["activity_log"] = activity_log
    
    await db.tickets.update_one({"id": ticket_id}, {"$set": update_data})
    
    # Notify relevant users
    users_to_notify = set(ticket.get("target_user_ids", []))
    users_to_notify.add(ticket["created_by"])
    users_to_notify.discard(user["id"])  # Don't notify the user who made the change
    
    for notify_id in users_to_notify:
        await create_notification(
            notify_id,
            f"Ticket Updated: {ticket['subject']}",
            f"Status changed to {status_update.status} by {user['name']}",
            "ticket_status_update",
            ticket_id
        )
    
    return {"message": f"Ticket status updated to {status_update.status}"}


@router.post("/{ticket_id}/message")
async def add_ticket_message(
    ticket_id: str, 
    message: TicketMessage, 
    background_tasks: BackgroundTasks, 
    user: dict = Depends(get_current_user)
):
    """Add a message to a ticket"""
    ticket = await db.tickets.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access
    can_access = (
        user["role"] == UserRole.ADMIN or
        ticket["created_by"] == user["id"] or
        user["id"] in ticket.get("target_user_ids", [])
    )
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    message_doc = {
        "id": str(ObjectId()),
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user["role"],
        "message": message.message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add activity log
    activity_log = ticket.get("activity_log", [])
    activity_log = add_activity_log(activity_log, "message_added", user, "Added a message")
    
    await db.tickets.update_one(
        {"id": ticket_id},
        {
            "$push": {"messages": message_doc},
            "$set": {"activity_log": activity_log}
        }
    )
    
    # Notify relevant users
    users_to_notify = set(ticket.get("target_user_ids", []))
    users_to_notify.add(ticket["created_by"])
    users_to_notify.discard(user["id"])
    
    for notify_id in users_to_notify:
        await create_notification(
            notify_id,
            f"New Message: {ticket['subject']}",
            f"{user['name']} added a message to the ticket",
            "ticket_message",
            ticket_id
        )
    
    return {"message": "Message added successfully", "message_id": message_doc["id"]}


@router.post("/{ticket_id}/attachment")
async def upload_ticket_attachment(
    ticket_id: str,
    file: UploadFile = File(...),
    description: str = Form(None),
    user: dict = Depends(get_current_user)
):
    """Upload an attachment to a ticket"""
    ticket = await db.tickets.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access
    can_access = (
        user["role"] == UserRole.ADMIN or
        ticket["created_by"] == user["id"] or
        user["id"] in ticket.get("target_user_ids", [])
    )
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Upload file to GridFS
    content = await file.read()
    file_id = await fs.upload_from_stream(
        file.filename,
        io.BytesIO(content),
        metadata={
            "content_type": file.content_type,
            "ticket_id": ticket_id,
            "uploaded_by": user["id"]
        }
    )
    
    attachment_doc = {
        "id": str(ObjectId()),
        "file_id": str(file_id),
        "filename": file.filename,
        "content_type": file.content_type,
        "file_size": len(content),
        "description": description,
        "uploaded_by": user["id"],
        "uploaded_by_name": user["name"],
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add activity log
    activity_log = ticket.get("activity_log", [])
    activity_log = add_activity_log(activity_log, "attachment_added", user, f"Attached file: {file.filename}")
    
    await db.tickets.update_one(
        {"id": ticket_id},
        {
            "$push": {"attachments": attachment_doc},
            "$set": {"activity_log": activity_log}
        }
    )
    
    return {"message": "Attachment uploaded", "attachment_id": attachment_doc["id"]}


@router.get("/{ticket_id}/attachment/{file_id}")
async def download_ticket_attachment(
    ticket_id: str,
    file_id: str,
    user: dict = Depends(get_current_user)
):
    """Download a ticket attachment"""
    ticket = await db.tickets.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access
    can_access = (
        user["role"] == UserRole.ADMIN or
        ticket["created_by"] == user["id"] or
        user["id"] in ticket.get("target_user_ids", [])
    )
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        grid_out = await fs.open_download_stream(ObjectId(file_id))
        content = await grid_out.read()
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=grid_out.metadata.get("content_type", "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename={grid_out.filename}"}
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
