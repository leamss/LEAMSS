"""Client Greetings Router — Auto birthday/anniversary/festival greetings"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from core.database import greetings_col, users_col, notifications_col
from core.auth import get_current_user
from core.services import create_notification

router = APIRouter(prefix="/greetings", tags=["Greetings"])

FESTIVAL_TEMPLATES = [
    {"name": "Diwali", "message": "Wishing you a very Happy Diwali! May this festival of lights bring prosperity to your immigration journey."},
    {"name": "Christmas", "message": "Merry Christmas! Wishing you joy and happiness this holiday season."},
    {"name": "New Year", "message": "Happy New Year! May this year bring success to your immigration plans."},
    {"name": "Eid", "message": "Eid Mubarak! Wishing you peace and blessings."},
    {"name": "Holi", "message": "Happy Holi! May your life be filled with colors of joy and success."},
    {"name": "Thanksgiving", "message": "Happy Thanksgiving! We're thankful for your trust in LEAMSS."},
    {"name": "Independence Day", "message": "Happy Independence Day! Celebrating freedom and new beginnings."},
]


class GreetingCreate(BaseModel):
    type: str  # birthday, anniversary, festival, custom
    template_name: str = ""
    custom_message: str = ""
    target_user_ids: List[str] = []
    send_to_all_clients: bool = False


@router.get("/templates")
async def get_templates(current_user: dict = Depends(get_current_user)):
    """Get available greeting templates"""
    return FESTIVAL_TEMPLATES


@router.post("/send")
async def send_greeting(request: GreetingCreate, current_user: dict = Depends(get_current_user)):
    """Send greeting to clients (admin/CM only)"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Determine message
    if request.custom_message:
        message = request.custom_message
    elif request.template_name:
        tpl = next((t for t in FESTIVAL_TEMPLATES if t["name"] == request.template_name), None)
        message = tpl["message"] if tpl else f"Happy {request.template_name}!"
    else:
        message = "Warm greetings from LEAMSS Immigration!"
    
    # Determine targets
    if request.send_to_all_clients:
        clients = await users_col.find({"role": "client", "status": "active"}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
        target_ids = [c["id"] for c in clients]
    else:
        target_ids = request.target_user_ids
    
    sent = 0
    greeting_id = str(uuid.uuid4())
    for uid in target_ids:
        await create_notification(uid, f"{request.type.title()} Greeting", message, "greeting", greeting_id)
        sent += 1
    
    # Log greeting
    greeting = {
        "id": greeting_id, "type": request.type,
        "template_name": request.template_name, "message": message,
        "sent_by": current_user["id"], "sent_by_name": current_user["name"],
        "recipients": sent, "target_ids": target_ids[:50],
        "created_at": datetime.now(timezone.utc)
    }
    await greetings_col.insert_one(greeting)
    greeting.pop("_id", None)
    greeting["created_at"] = greeting["created_at"].isoformat()
    return {"message": f"Greeting sent to {sent} clients", "greeting_id": greeting_id, "sent": sent}


@router.get("/history")
async def greeting_history(current_user: dict = Depends(get_current_user)):
    """Get greeting history"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    greetings = await greetings_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for g in greetings:
        if isinstance(g.get("created_at"), datetime):
            g["created_at"] = g["created_at"].isoformat()
    return greetings
