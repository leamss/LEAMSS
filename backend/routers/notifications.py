"""Notifications Router"""
from fastapi import APIRouter, Depends
from core.database import notifications_col
from core.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    notifs = await notifications_col.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    for n in notifs:
        if isinstance(n.get("created_at"), datetime):
            n["created_at"] = n["created_at"].isoformat()
    return notifs


@router.put("/{notification_id}/read")
async def mark_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    await notifications_col.update_one({"id": notification_id}, {"$set": {"read": True}})
    return {"message": "Marked as read"}


@router.put("/mark-all-read")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    await notifications_col.update_many(
        {"user_id": current_user["id"], "read": False},
        {"$set": {"read": True}}
    )
    return {"message": "All marked as read"}
