"""Notification & Activity Log Service — injects events into business logic"""
import uuid
from datetime import datetime, timezone
from core.database import notifications_col, audit_logs_col, users_col


async def create_notification(user_id: str, title: str, message: str, 
                               notification_type: str, related_id: str = None):
    """Create a notification for a specific user"""
    notif = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "related_id": related_id,
        "read": False,
        "is_read": False,
        "created_at": datetime.now(timezone.utc)
    }
    await notifications_col.insert_one(notif)
    return notif


async def notify_role(role: str, title: str, message: str,
                      notification_type: str, related_id: str = None, exclude_user_id: str = None):
    """Notify all users with a specific role"""
    query = {"role": role, "status": "active"}
    if exclude_user_id:
        query["id"] = {"$ne": exclude_user_id}
    users = await users_col.find(query, {"_id": 0, "id": 1}).to_list(500)
    for u in users:
        await create_notification(u["id"], title, message, notification_type, related_id)


async def notify_users(user_ids: list, title: str, message: str,
                       notification_type: str, related_id: str = None):
    """Notify a list of specific users"""
    for uid in user_ids:
        await create_notification(uid, title, message, notification_type, related_id)


async def log_activity(user_id: str, user_name: str, action: str,
                       entity_type: str, entity_id: str = None, details: str = None):
    """Log an activity/audit event"""
    log = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_name": user_name,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
        "created_at": datetime.now(timezone.utc)
    }
    await audit_logs_col.insert_one(log)
    return log
