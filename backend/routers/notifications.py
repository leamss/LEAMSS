"""Notifications Router"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from core.database import notifications_col
from core.auth import get_current_user
from datetime import datetime, timezone
import asyncio
import json
import jwt
import os

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


@router.get("/stream")
async def notification_stream(token: str = Query(...)):
    """SSE endpoint for real-time notifications"""
    try:
        payload = jwt.decode(token, os.environ.get("JWT_SECRET", "leamss-portal-secret-key-2024-secure"), algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            return StreamingResponse(iter([]), status_code=401)
    except Exception:
        return StreamingResponse(iter([]), status_code=401)

    async def event_generator():
        yield f"data: {json.dumps({'type': 'connected', 'user_id': user_id})}\n\n"
        last_check = datetime.now(timezone.utc)
        while True:
            await asyncio.sleep(5)  # Poll every 5s for near-real-time delivery
            try:
                new_notifs = await notifications_col.find(
                    {"user_id": user_id, "read": False, "created_at": {"$gt": last_check}},
                    {"_id": 0}
                ).to_list(20)
                last_check = datetime.now(timezone.utc)
                for n in new_notifs:
                    if isinstance(n.get("created_at"), datetime):
                        n["created_at"] = n["created_at"].isoformat()
                    yield f"data: {json.dumps({'type': 'notification', **n})}\n\n"
                if not new_notifs:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
            except asyncio.CancelledError:
                break
            except Exception:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )
