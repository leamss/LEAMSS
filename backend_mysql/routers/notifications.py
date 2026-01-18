"""
Notifications Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List
from datetime import datetime
import asyncio
import json
from core.database import get_db
from core.models import Notification, PushSubscription, UserRole
from core.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[dict])
async def get_notifications(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all notifications for current user"""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user["id"])
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifications = result.scalars().all()
    
    return [
        {
            "id": n.id,
            "user_id": n.user_id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "related_id": n.related_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notifications
    ]


@router.get("/unread", response_model=List[dict])
async def get_unread_notifications(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get unread notifications for current user"""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user["id"])
        .where(Notification.is_read == False)
        .order_by(Notification.created_at.desc())
        .limit(20)
    )
    notifications = result.scalars().all()
    
    return [
        {
            "id": n.id,
            "user_id": n.user_id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "related_id": n.related_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notifications
    ]


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read"""
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.user_id == current_user["id"])
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Notification marked as read"}


@router.put("/read-all")
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read"""
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user["id"])
        .where(Notification.is_read == False)
        .values(is_read=True, read_at=datetime.utcnow())
    )
    
    await db.commit()
    
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a notification"""
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.user_id == current_user["id"])
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    await db.delete(notification)
    await db.commit()
    
    return {"message": "Notification deleted"}


@router.delete("/delete-all")
async def delete_all_notifications(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete all notifications for current user"""
    await db.execute(
        delete(Notification).where(Notification.user_id == current_user["id"])
    )
    
    await db.commit()
    
    return {"message": "All notifications deleted"}


@router.get("/stream")
async def notification_stream(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Server-sent events stream for real-time notifications"""
    async def event_generator():
        yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to notification stream'})}\n\n"
        
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            # Get unread count
            async with db.begin():
                result = await db.execute(
                    select(Notification)
                    .where(Notification.user_id == current_user["id"])
                    .where(Notification.is_read == False)
                )
                unread = result.scalars().all()
                
                if unread:
                    latest = unread[0]
                    yield f"data: {json.dumps({'type': 'notification', 'count': len(unread), 'latest': {'id': latest.id, 'title': latest.title, 'message': latest.message}})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
