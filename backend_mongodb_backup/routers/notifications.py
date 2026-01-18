"""
Notification routes for LEAMSS Portal
Handles REST API, SSE, and Push notifications
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import List
from bson import ObjectId
import asyncio
import json

from core.database import db
from core.auth import get_current_user, require_role, UserRole, get_user_from_token
from core.config import PUSH_ENABLED, VAPID_PUBLIC_KEY
from core.models import NotificationResponse, PushSubscription
from services.notification_service import ws_manager, sse_manager

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(user: dict = Depends(get_current_user)):
    """Get all notifications for current user"""
    notifications = await db.notifications.find(
        {"user_id": user["id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return [NotificationResponse(**n) for n in notifications]


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    """Mark a notification as read"""
    await db.notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"is_read": True}}
    )
    return {"message": "Notification marked as read"}


@router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str, user: dict = Depends(get_current_user)):
    """Delete a notification"""
    result = await db.notifications.delete_one(
        {"id": notification_id, "user_id": user["id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}


@router.get("/notifications/stream")
async def notification_stream(token: str):
    """Server-Sent Events endpoint for real-time notifications"""
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = user["id"]
    queue = sse_manager.connect(user_id)
    
    async def event_generator():
        try:
            # Send initial connection confirmation
            yield f"data: {json.dumps({'type': 'connected', 'user_id': user_id})}\n\n"
            
            while True:
                try:
                    # Wait for notification with timeout for keep-alive
                    notification = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(notification)}\n\n"
                except asyncio.TimeoutError:
                    # Send keep-alive ping every 30 seconds
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.disconnect(user_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==================== Push Notification Endpoints ====================

@router.get("/push/vapid-public-key")
async def get_vapid_public_key():
    """Get VAPID public key for push subscription"""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"publicKey": VAPID_PUBLIC_KEY}


@router.post("/push/subscribe")
async def subscribe_push(subscription: PushSubscription, user: dict = Depends(get_current_user)):
    """Subscribe to push notifications"""
    if not PUSH_ENABLED:
        raise HTTPException(status_code=503, detail="Push notifications not available")
    
    # Check if subscription already exists
    existing = await db.push_subscriptions.find_one({
        "user_id": user["id"],
        "endpoint": subscription.endpoint
    })
    
    if existing:
        # Update existing subscription
        await db.push_subscriptions.update_one(
            {"_id": existing["_id"]},
            {"$set": {"keys": subscription.keys, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"message": "Subscription updated", "id": existing["id"]}
    
    # Create new subscription
    sub_doc = {
        "id": str(ObjectId()),
        "user_id": user["id"],
        "endpoint": subscription.endpoint,
        "keys": subscription.keys,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.push_subscriptions.insert_one(sub_doc)
    
    return {"message": "Subscribed to push notifications", "id": sub_doc["id"]}


@router.delete("/push/unsubscribe")
async def unsubscribe_push(endpoint: str, user: dict = Depends(get_current_user)):
    """Unsubscribe from push notifications"""
    result = await db.push_subscriptions.delete_one({
        "user_id": user["id"],
        "endpoint": endpoint
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"message": "Unsubscribed from push notifications"}


@router.get("/push/subscriptions")
async def get_push_subscriptions(user: dict = Depends(get_current_user)):
    """Get user's push subscriptions"""
    subs = await db.push_subscriptions.find(
        {"user_id": user["id"]}, 
        {"_id": 0, "keys": 0}
    ).to_list(100)
    return subs
