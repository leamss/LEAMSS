"""
Notification service for LEAMSS Portal
Handles real-time notifications via WebSocket, SSE, and Push
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from bson import ObjectId
from fastapi import WebSocket

from core.database import db
from core.config import PUSH_ENABLED, VAPID_PRIVATE_KEY, VAPID_CLAIMS_EMAIL

# Import push notification library if available
if PUSH_ENABLED:
    from pywebpush import webpush, WebPushException


# ==================== WebSocket Connection Manager ====================

class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logging.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logging.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user"""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logging.error(f"Error sending WebSocket message: {e}")
                    disconnected.append(connection)
            for conn in disconnected:
                self.disconnect(conn, user_id)
    
    async def broadcast(self, message: dict):
        """Send a message to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)


# ==================== SSE Connection Manager ====================

class SSEConnectionManager:
    """Manages SSE connections for real-time notifications (works through HTTP ingress)"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[asyncio.Queue]] = {}
    
    def connect(self, user_id: str) -> asyncio.Queue:
        """Create a new queue for a user's SSE connection"""
        queue = asyncio.Queue()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(queue)
        logging.info(f"SSE connected for user {user_id}")
        return queue
    
    def disconnect(self, user_id: str, queue: asyncio.Queue):
        """Remove a queue when SSE connection closes"""
        if user_id in self.active_connections:
            if queue in self.active_connections[user_id]:
                self.active_connections[user_id].remove(queue)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logging.info(f"SSE disconnected for user {user_id}")
    
    async def send_notification(self, user_id: str, notification: dict):
        """Send notification to a specific user via SSE"""
        if user_id in self.active_connections:
            for queue in self.active_connections[user_id]:
                try:
                    await queue.put(notification)
                except Exception as e:
                    logging.error(f"Error sending SSE notification: {e}")


# Global instances
ws_manager = ConnectionManager()
sse_manager = SSEConnectionManager()


# ==================== Push Notification Functions ====================

async def send_push_notification(user_id: str, title: str, body: str, url: str = None):
    """Send push notification to all subscribed devices for a user"""
    if not PUSH_ENABLED or not VAPID_PRIVATE_KEY:
        return
    
    try:
        subscriptions = await db.push_subscriptions.find({"user_id": user_id}).to_list(100)
        
        for sub in subscriptions:
            try:
                payload = json.dumps({
                    "title": title,
                    "body": body,
                    "icon": "/logo192.png",
                    "badge": "/logo192.png",
                    "url": url or "/",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                webpush(
                    subscription_info={
                        "endpoint": sub["endpoint"],
                        "keys": sub["keys"]
                    },
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"}
                )
            except WebPushException as e:
                logging.error(f"Push notification failed: {e}")
                if e.response and e.response.status_code in [404, 410]:
                    await db.push_subscriptions.delete_one({"_id": sub["_id"]})
            except Exception as e:
                logging.error(f"Push notification error: {e}")
    except Exception as e:
        logging.error(f"Failed to send push notifications: {e}")


# ==================== Main Notification Function ====================

async def create_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str,
    related_id: Optional[str] = None
):
    """
    Create a notification and send via all channels:
    - Store in database
    - Send via WebSocket
    - Send via SSE
    - Send via Push notification
    """
    notification = {
        "id": str(ObjectId()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "related_id": related_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    notification_payload = {
        "type": "notification",
        "data": {
            "id": notification["id"],
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "related_id": related_id,
            "created_at": notification["created_at"]
        }
    }
    
    # Send via WebSocket
    try:
        await ws_manager.send_personal_message(notification_payload, user_id)
    except Exception as e:
        logging.error(f"Failed to send WebSocket notification: {e}")
    
    # Send via SSE
    try:
        await sse_manager.send_notification(user_id, notification_payload)
    except Exception as e:
        logging.error(f"Failed to send SSE notification: {e}")
    
    # Send via Push
    try:
        await send_push_notification(user_id, title, message, f"/?notification={notification['id']}")
    except Exception as e:
        logging.error(f"Failed to send push notification: {e}")
