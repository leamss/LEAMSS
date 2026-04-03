"""Tickets Router"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import tickets_col, ticket_messages_col, users_col, notifications_col
from core.auth import get_current_user
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/tickets", tags=["Tickets"])


class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "medium"
    category: str = "general"


class TicketReply(BaseModel):
    message: str


@router.get("")
async def get_tickets(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] not in ["admin", "case_manager"]:
        query["created_by"] = current_user["id"]
    
    tickets = await tickets_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    for t in tickets:
        creator = await users_col.find_one({"id": t.get("created_by")}, {"_id": 0, "password": 0})
        t["creator_name"] = creator["name"] if creator else "Unknown"
        msgs = await ticket_messages_col.count_documents({"ticket_id": t["id"]})
        t["message_count"] = msgs
        for f in ["created_at", "updated_at", "closed_at"]:
            if isinstance(t.get(f), datetime):
                t[f] = t[f].isoformat()
    return tickets


@router.get("/all")
async def get_all_tickets(current_user: dict = Depends(get_current_user)):
    """Get all tickets - admin endpoint"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")
    
    tickets = await tickets_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for t in tickets:
        creator = await users_col.find_one({"id": t.get("created_by")}, {"_id": 0, "password": 0})
        t["creator_name"] = creator["name"] if creator else "Unknown"
        t["creator_role"] = creator["role"] if creator else "unknown"
        msgs = await ticket_messages_col.count_documents({"ticket_id": t["id"]})
        t["message_count"] = msgs
        for f in ["created_at", "updated_at", "closed_at"]:
            if isinstance(t.get(f), datetime):
                t[f] = t[f].isoformat()
    return tickets


@router.get("/stats")
async def get_ticket_stats(current_user: dict = Depends(get_current_user)):
    """Get ticket statistics"""
    total = await tickets_col.count_documents({})
    open_count = await tickets_col.count_documents({"status": "open"})
    in_progress = await tickets_col.count_documents({"status": "in_progress"})
    resolved = await tickets_col.count_documents({"status": "resolved"})
    closed = await tickets_col.count_documents({"status": "closed"})
    
    high_priority = await tickets_col.count_documents({"priority": "high", "status": {"$ne": "closed"}})
    
    return {
        "total": total,
        "open": open_count,
        "in_progress": in_progress,
        "resolved": resolved,
        "closed": closed,
        "high_priority": high_priority
    }


@router.post("")
async def create_ticket(data: dict, current_user: dict = Depends(get_current_user)):
    target_user_ids = data.get("target_user_ids", [])
    assigned_to = data.get("assigned_to", None)
    assigned_role = data.get("assigned_role", None)
    
    # Auto-routing: if client creates ticket with no targets, auto-route by category
    if not target_user_ids and not assigned_to and current_user["role"] == "client":
        category = data.get("category", "general")
        if category in ["document", "payment"]:
            # Route to case managers
            assigned_role = "case_manager"
            cms = await users_col.find({"role": "case_manager", "status": "active"}, {"_id": 0}).to_list(10)
            target_user_ids = [cm["id"] for cm in cms]
        else:
            # Route to admin
            assigned_role = "admin"
            admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0}).to_list(10)
            target_user_ids = [a["id"] for a in admins]
    
    ticket = {
        "id": str(uuid.uuid4()), "subject": data.get("subject", ""),
        "description": data.get("description", ""), "priority": data.get("priority", "medium"),
        "category": data.get("category", "general"), "status": "open",
        "created_by": current_user["id"],
        "target_user_ids": target_user_ids,
        "assigned_to": assigned_to,
        "assigned_role": assigned_role,
        "case_id": data.get("case_id"),
        "created_at": datetime.now(timezone.utc)
    }
    await tickets_col.insert_one(ticket)
    
    # Create notifications for assigned targets
    for uid in target_user_ids:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": uid,
            "title": f"New Ticket: {ticket['subject']}",
            "message": f"A new {ticket['priority']} priority ticket has been assigned to you.",
            "type": "ticket", "read": False,
            "reference_id": ticket["id"], "reference_type": "ticket",
            "created_at": datetime.now(timezone.utc)
        })
    
    return {"id": ticket["id"], "message": "Ticket created"}


@router.put("/{ticket_id}/assign")
async def assign_ticket(ticket_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Reassign a ticket to a different user or role"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")
    
    ticket = await tickets_col.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    update_fields = {"updated_at": datetime.now(timezone.utc)}
    
    if "assigned_to" in data:
        update_fields["assigned_to"] = data["assigned_to"]
        # Add to target_user_ids if not already there
        target_ids = ticket.get("target_user_ids", [])
        if data["assigned_to"] not in target_ids:
            target_ids.append(data["assigned_to"])
            update_fields["target_user_ids"] = target_ids
        
        # Notify the assigned user
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": data["assigned_to"],
            "title": f"Ticket Assigned: {ticket['subject']}",
            "message": f"A ticket has been assigned to you by {current_user.get('name', 'Admin')}.",
            "type": "ticket", "read": False,
            "reference_id": ticket_id, "reference_type": "ticket",
            "created_at": datetime.now(timezone.utc)
        })
    
    if "assigned_role" in data:
        update_fields["assigned_role"] = data["assigned_role"]
    
    await tickets_col.update_one({"id": ticket_id}, {"$set": update_fields})
    return {"message": "Ticket reassigned successfully"}


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)):
    ticket = await tickets_col.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    creator = await users_col.find_one({"id": ticket.get("created_by")}, {"_id": 0, "password": 0})
    ticket["creator_name"] = creator["name"] if creator else "Unknown"
    
    messages = await ticket_messages_col.find({"ticket_id": ticket_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    for m in messages:
        sender = await users_col.find_one({"id": m.get("sender_id")}, {"_id": 0, "password": 0})
        m["sender_name"] = sender["name"] if sender else "Unknown"
        if isinstance(m.get("created_at"), datetime):
            m["created_at"] = m["created_at"].isoformat()
    
    ticket["messages"] = messages
    for f in ["created_at", "updated_at"]:
        if isinstance(ticket.get(f), datetime):
            ticket[f] = ticket[f].isoformat()
    return ticket


@router.post("/{ticket_id}/reply")
async def reply_ticket(ticket_id: str, data: TicketReply, current_user: dict = Depends(get_current_user)):
    ticket = await tickets_col.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    msg = {
        "id": str(uuid.uuid4()), "ticket_id": ticket_id,
        "sender_id": current_user["id"], "message": data.message,
        "created_at": datetime.now(timezone.utc)
    }
    await ticket_messages_col.insert_one(msg)
    await tickets_col.update_one({"id": ticket_id}, {"$set": {"updated_at": datetime.now(timezone.utc)}})
    return {"message": "Reply sent"}


@router.put("/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    new_status = data.get("status", "")
    closure_comment = data.get("closure_comment", data.get("resolution_note", ""))
    
    # Require closure comment when resolving or closing
    if new_status in ["resolved", "closed"]:
        if not closure_comment or len(closure_comment.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Closure comment is required (minimum 10 characters) when resolving or closing a ticket"
            )
    
    update_fields = {"status": new_status, "updated_at": datetime.now(timezone.utc)}
    if closure_comment:
        update_fields["closure_comment"] = closure_comment.strip()
        update_fields["closed_by"] = current_user["id"]
        update_fields["closed_at"] = datetime.now(timezone.utc)
    
    await tickets_col.update_one({"id": ticket_id}, {"$set": update_fields})
    return {"message": "Ticket status updated"}
