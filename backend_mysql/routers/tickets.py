"""
Tickets Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import os
import uuid
from core.database import get_db
from core.models import (
    Ticket, TicketMessage, TicketAttachment, TicketActivityLog, TicketTarget,
    User, UserRole, TicketStatus, TicketPriority, TicketCategory, Notification
)
from core.auth import get_current_user, require_role
from core.schemas import TicketCreate, TicketMessage as TicketMessageSchema, TicketStatusUpdate

router = APIRouter(prefix="/tickets", tags=["Tickets"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")


def serialize_ticket(ticket: Ticket, user_map: dict = None) -> dict:
    """Convert ticket model to dict"""
    user_map = user_map or {}
    
    created_by_user = user_map.get(ticket.created_by, {})
    resolved_by_user = user_map.get(ticket.resolved_by, {}) if ticket.resolved_by else {}
    
    return {
        "id": ticket.id,
        "case_id": ticket.case_id,
        "created_by": ticket.created_by,
        "created_by_name": created_by_user.get("name", "Unknown"),
        "created_by_role": created_by_user.get("role", "unknown"),
        "subject": ticket.subject,
        "category": ticket.category.value if ticket.category else "general",
        "priority": ticket.priority.value if ticket.priority else "medium",
        "description": ticket.description,
        "status": ticket.status.value if ticket.status else "open",
        "target_role": ticket.target_role,
        "target_user_ids": [t.user_id for t in ticket.targets] if ticket.targets else [],
        "resolution_note": ticket.resolution_note,
        "resolved_by": ticket.resolved_by,
        "resolved_by_name": resolved_by_user.get("name"),
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "messages": [
            {
                "id": msg.id,
                "user_id": msg.user_id,
                "user_name": user_map.get(msg.user_id, {}).get("name", "Unknown"),
                "user_role": user_map.get(msg.user_id, {}).get("role", "unknown"),
                "message": msg.message,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in sorted(ticket.messages, key=lambda m: m.created_at) if ticket.messages
        ],
        "attachments": [
            {
                "id": att.id,
                "filename": att.filename,
                "file_id": att.id,
                "file_size": att.file_size,
                "uploaded_by": att.uploaded_by,
                "uploaded_by_name": user_map.get(att.uploaded_by, {}).get("name", "Unknown"),
                "uploaded_at": att.uploaded_at.isoformat() if att.uploaded_at else None
            }
            for att in ticket.attachments if ticket.attachments
        ],
        "activity_log": [
            {
                "id": log.id,
                "action": log.action,
                "details": log.details,
                "user_id": log.user_id,
                "user_name": user_map.get(log.user_id, {}).get("name", "System"),
                "timestamp": log.created_at.isoformat() if log.created_at else None
            }
            for log in sorted(ticket.activity_log, key=lambda l: l.created_at) if ticket.activity_log
        ]
    }


async def get_user_map(db: AsyncSession, user_ids: List[str]) -> dict:
    """Get a map of user_id -> user info"""
    if not user_ids:
        return {}
    
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()
    
    return {
        u.id: {"name": u.name, "role": u.role.value}
        for u in users
    }


@router.get("/my-tickets", response_model=List[dict])
async def get_my_tickets(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tickets for current user"""
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    # Get tickets where user is creator or target
    result = await db.execute(
        select(Ticket)
        .options(
            selectinload(Ticket.messages),
            selectinload(Ticket.attachments),
            selectinload(Ticket.activity_log),
            selectinload(Ticket.targets)
        )
        .outerjoin(TicketTarget)
        .where(
            or_(
                Ticket.created_by == user_id,
                TicketTarget.user_id == user_id,
                Ticket.target_role == user_role
            )
        )
        .distinct()
        .order_by(Ticket.created_at.desc())
    )
    tickets = result.scalars().unique().all()
    
    # Get all user IDs
    user_ids = set()
    for t in tickets:
        user_ids.add(t.created_by)
        if t.resolved_by:
            user_ids.add(t.resolved_by)
        for msg in t.messages:
            user_ids.add(msg.user_id)
        for att in t.attachments:
            user_ids.add(att.uploaded_by)
        for log in t.activity_log:
            if log.user_id:
                user_ids.add(log.user_id)
    
    user_map = await get_user_map(db, list(user_ids))
    
    return [serialize_ticket(t, user_map) for t in tickets]


@router.get("/{ticket_id}", response_model=dict)
async def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get ticket by ID"""
    result = await db.execute(
        select(Ticket)
        .options(
            selectinload(Ticket.messages),
            selectinload(Ticket.attachments),
            selectinload(Ticket.activity_log),
            selectinload(Ticket.targets)
        )
        .where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get user map
    user_ids = {ticket.created_by}
    if ticket.resolved_by:
        user_ids.add(ticket.resolved_by)
    for msg in ticket.messages:
        user_ids.add(msg.user_id)
    for att in ticket.attachments:
        user_ids.add(att.uploaded_by)
    for log in ticket.activity_log:
        if log.user_id:
            user_ids.add(log.user_id)
    
    user_map = await get_user_map(db, list(user_ids))
    
    return serialize_ticket(ticket, user_map)


@router.post("", response_model=dict)
async def create_ticket(
    request: TicketCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new ticket"""
    ticket = Ticket(
        case_id=request.case_id,
        created_by=current_user["id"],
        subject=request.subject,
        category=TicketCategory(request.category) if request.category else TicketCategory.general,
        priority=TicketPriority(request.priority) if request.priority else TicketPriority.medium,
        description=request.description,
        status=TicketStatus.open,
        target_role=request.target_role
    )
    
    db.add(ticket)
    await db.flush()
    
    # Add target users
    if request.target_user_ids:
        for user_id in request.target_user_ids:
            target = TicketTarget(ticket_id=ticket.id, user_id=user_id)
            db.add(target)
            
            # Notify target user
            notification = Notification(
                user_id=user_id,
                title="New Ticket Assigned",
                message=f"You have been assigned to ticket: {request.subject}",
                type="ticket_assigned",
                related_id=ticket.id
            )
            db.add(notification)
    
    # Add activity log
    activity = TicketActivityLog(
        ticket_id=ticket.id,
        user_id=current_user["id"],
        action="created",
        details=f"Ticket created: {request.subject}"
    )
    db.add(activity)
    
    await db.commit()
    
    return {"id": ticket.id, "message": "Ticket created successfully"}


@router.post("/{ticket_id}/message", response_model=dict)
async def add_message(
    ticket_id: str,
    request: TicketMessageSchema,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add message to ticket"""
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.targets))
        .where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    message = TicketMessage(
        ticket_id=ticket_id,
        user_id=current_user["id"],
        message=request.message
    )
    db.add(message)
    
    # Activity log
    activity = TicketActivityLog(
        ticket_id=ticket_id,
        user_id=current_user["id"],
        action="message_added",
        details=f"Message added by {current_user['name']}"
    )
    db.add(activity)
    
    # Notify other participants
    notify_ids = {ticket.created_by}
    for target in ticket.targets:
        notify_ids.add(target.user_id)
    notify_ids.discard(current_user["id"])
    
    for user_id in notify_ids:
        notification = Notification(
            user_id=user_id,
            title="New Message on Ticket",
            message=f"New message on ticket: {ticket.subject}",
            type="ticket_message",
            related_id=ticket.id
        )
        db.add(notification)
    
    await db.commit()
    
    return {"message": "Message added successfully"}


@router.put("/{ticket_id}/status", response_model=dict)
async def update_ticket_status(
    ticket_id: str,
    request: TicketStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update ticket status"""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    old_status = ticket.status.value if ticket.status else "open"
    ticket.status = TicketStatus(request.status)
    
    if request.status in ["resolved", "closed"]:
        ticket.resolved_by = current_user["id"]
        ticket.resolved_at = datetime.utcnow()
        ticket.resolution_note = request.resolution_note
    
    # Activity log
    activity = TicketActivityLog(
        ticket_id=ticket_id,
        user_id=current_user["id"],
        action="status_changed",
        details=f"Status changed from {old_status} to {request.status}"
    )
    db.add(activity)
    
    # Notify creator
    if ticket.created_by != current_user["id"]:
        notification = Notification(
            user_id=ticket.created_by,
            title=f"Ticket {request.status.capitalize()}",
            message=f"Your ticket '{ticket.subject}' has been {request.status}",
            type=f"ticket_{request.status}",
            related_id=ticket.id
        )
        db.add(notification)
    
    await db.commit()
    
    return {"message": f"Ticket status updated to {request.status}"}


@router.post("/{ticket_id}/attachment", response_model=dict)
async def upload_attachment(
    ticket_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload attachment to ticket"""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Save file
    file_ext = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_dir = os.path.join(UPLOAD_DIR, "tickets", ticket_id)
    os.makedirs(file_dir, exist_ok=True)
    file_path = os.path.join(file_dir, file_name)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    attachment = TicketAttachment(
        ticket_id=ticket_id,
        uploaded_by=current_user["id"],
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        content_type=file.content_type
    )
    db.add(attachment)
    
    # Activity log
    activity = TicketActivityLog(
        ticket_id=ticket_id,
        user_id=current_user["id"],
        action="attachment_added",
        details=f"Attachment '{file.filename}' uploaded"
    )
    db.add(activity)
    
    await db.commit()
    
    return {"id": attachment.id, "message": "Attachment uploaded successfully"}


@router.get("/stats", response_model=dict)
async def get_ticket_stats(
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get ticket statistics (Admin only)"""
    total_result = await db.execute(select(func.count(Ticket.id)))
    total = total_result.scalar()
    
    open_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.open)
    )
    open_count = open_result.scalar()
    
    high_priority_result = await db.execute(
        select(func.count(Ticket.id))
        .where(Ticket.priority.in_([TicketPriority.high, TicketPriority.urgent]))
        .where(Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress]))
    )
    high_priority = high_priority_result.scalar()
    
    return {
        "total": total,
        "open": open_count,
        "high_priority": high_priority
    }
