"""Appointments Router — Scheduling"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import appointments_col, cases_col, users_col
from core.auth import get_current_user
from core.services import create_notification, log_activity

router = APIRouter(prefix="/appointments", tags=["Appointments"])


class AppointmentCreate(BaseModel):
    case_id: Optional[str] = None
    title: str
    description: str = ""
    date: str
    time: str
    duration_minutes: int = 30
    attendee_id: Optional[str] = None


@router.post("")
async def create_appointment(request: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    """Create an appointment"""
    appt = {
        "id": str(uuid.uuid4()), "case_id": request.case_id,
        "title": request.title, "description": request.description,
        "date": request.date, "time": request.time,
        "duration_minutes": request.duration_minutes,
        "created_by": current_user["id"], "created_by_name": current_user["name"],
        "attendee_id": request.attendee_id, "status": "scheduled",
        "created_at": datetime.now(timezone.utc)
    }
    if request.attendee_id:
        attendee = await users_col.find_one({"id": request.attendee_id}, {"_id": 0, "name": 1})
        appt["attendee_name"] = attendee["name"] if attendee else ""
        await create_notification(request.attendee_id, "New Appointment", f"{request.title} on {request.date} at {request.time}", "appointment", appt["id"])
    await appointments_col.insert_one(appt)
    appt.pop("_id", None)
    appt["created_at"] = appt["created_at"].isoformat()
    await log_activity(current_user["id"], current_user["name"], "create_appointment", "appointment", appt["id"], {"title": request.title})
    return appt


@router.get("")
async def list_appointments(current_user: dict = Depends(get_current_user)):
    """List appointments for current user"""
    query = {"$or": [{"created_by": current_user["id"]}, {"attendee_id": current_user["id"]}]}
    if current_user["role"] == "admin":
        query = {}
    appts = await appointments_col.find(query, {"_id": 0}).sort("date", -1).to_list(100)
    for a in appts:
        if isinstance(a.get("created_at"), datetime):
            a["created_at"] = a["created_at"].isoformat()
    return appts


@router.put("/{appt_id}/cancel")
async def cancel_appointment(appt_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel appointment"""
    appt = await appointments_col.find_one({"id": appt_id}, {"_id": 0})
    if not appt:
        raise HTTPException(status_code=404, detail="Not found")
    await appointments_col.update_one({"id": appt_id}, {"$set": {"status": "cancelled"}})
    if appt.get("attendee_id"):
        await create_notification(appt["attendee_id"], "Appointment Cancelled", f"{appt['title']} has been cancelled", "appointment", appt_id)
    return {"message": "Cancelled"}


@router.put("/{appt_id}/complete")
async def complete_appointment(appt_id: str, current_user: dict = Depends(get_current_user)):
    """Mark appointment as completed"""
    await appointments_col.update_one({"id": appt_id}, {"$set": {"status": "completed"}})
    return {"message": "Completed"}
