"""Leads & CRM Pipeline Router"""
from fastapi import APIRouter, HTTPException, Depends, Query
from core.database import db
from core.auth import get_current_user
from core.services import log_activity, create_notification
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/leads", tags=["leads"])
leads_col = db["leads"]
follow_ups_col = db["follow_ups"]


async def _next_lead_number():
    """Generate a human-friendly sequential lead number like LD006672."""
    count = await leads_col.count_documents({})
    return f"LD{(count + 6620):06d}"


@router.post("/capture")
async def capture_lead(data: dict):
    """Create a lead — public (landing page) or authenticated (Add Lead form) use both hit this."""
    lead_number = data.get("lead_number") or await _next_lead_number()
    lead = {
        "id": str(uuid.uuid4()),
        "lead_number": lead_number,
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "alternate_phone": data.get("alternate_phone", ""),
        "address": data.get("address", ""),
        "city": data.get("city", ""),
        "service_interested": data.get("service_interested", ""),
        "country_of_interest": data.get("country_of_interest", ""),
        "message": data.get("message", ""),
        "source": data.get("source", "website"),
        "subsource": data.get("subsource", ""),
        "utm_source": data.get("utm_source", ""),
        "utm_medium": data.get("utm_medium", ""),
        "utm_campaign": data.get("utm_campaign", ""),
        "stage": data.get("stage", "new"),
        "assigned_to": data.get("assigned_to"),
        "assigned_to_name": data.get("assigned_to_name", ""),
        "priority": data.get("priority", "medium"),
        "date_of_birth": data.get("date_of_birth", ""),
        "occupation": data.get("occupation", ""),
        "total_work_experience": data.get("total_work_experience", ""),
        "backlogs": data.get("backlogs", ""),
        "lead_type": data.get("lead_type", ""),
        "latest_qualification": data.get("latest_qualification", ""),
        "university": data.get("university", ""),
        "course": data.get("course", ""),
        "tags": [],
        "notes": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_contacted_at": None,
        "converted": False,
        "converted_sale_id": None
    }
    await leads_col.insert_one(lead)
    return {"message": "Lead saved successfully.", "lead_id": lead["id"], "lead_number": lead_number}


@router.get("/")
async def get_leads(
    stage: str = Query(None),
    assigned_to: str = Query(None),
    source: str = Query(None),
    limit: int = Query(100),
    current_user: dict = Depends(get_current_user)
):
    """Get all leads (admin/partner)"""
    if current_user["role"] not in ["admin", "partner", "case_manager", "sales_executive", "sr_sales_executive"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = {}
    if stage:
        query["stage"] = stage
    if assigned_to:
        query["assigned_to"] = assigned_to
    if source:
        query["source"] = source
    if current_user["role"] in ["partner", "sales_executive", "sr_sales_executive"]:
        query["assigned_to"] = current_user["id"]
    
    leads = await leads_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    for lead in leads:
        for field in ["created_at", "updated_at", "last_contacted_at"]:
            if isinstance(lead.get(field), datetime):
                lead[field] = lead[field].isoformat()
    return leads


@router.get("/pipeline-stats")
async def get_pipeline_stats(current_user: dict = Depends(get_current_user)):
    """Get lead pipeline statistics"""
    if current_user["role"] not in ["admin", "partner", "case_manager", "sales_executive", "sr_sales_executive"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    stages = ["new", "contacted", "not_connected", "payment_done", "prospect", "not_interested", "converted"]
    stats = {}
    for stage in stages:
        query = {"stage": stage}
        if current_user["role"] in ["partner", "sales_executive", "sr_sales_executive"]:
            query["assigned_to"] = current_user["id"]
        stats[stage] = await leads_col.count_documents(query)
    
    total = sum(stats.values())
    conversion_rate = round((stats.get("converted", 0) / total * 100) if total > 0 else 0, 1)
    
    return {
        "stages": stats,
        "total": total,
        "conversion_rate": conversion_rate,
        "sources": await _get_source_stats(current_user)
    }


async def _get_source_stats(user):
    query = {}
    if user["role"] in ["partner", "sales_executive", "sr_sales_executive"]:
        query["assigned_to"] = user["id"]
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    results = await leads_col.aggregate(pipeline).to_list(20)
    return {r["_id"]: r["count"] for r in results if r["_id"]}


@router.put("/{lead_id}")
async def update_lead(lead_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Update lead details or move through pipeline"""
    if current_user["role"] not in ["admin", "partner", "case_manager", "sales_executive", "sr_sales_executive"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    data.pop("id", None)
    data.pop("_id", None)
    data["updated_at"] = datetime.now(timezone.utc)
    
    await leads_col.update_one({"id": lead_id}, {"$set": data})
    
    if "stage" in data and data["stage"] != lead.get("stage"):
        await log_activity(current_user["id"], current_user["name"], 
            f"moved_to_{data['stage']}", "lead", lead_id,
            f"Lead {lead.get('name')} moved to {data['stage']}")
    
    return {"message": "Lead updated"}


@router.post("/{lead_id}/note")
async def add_note(lead_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Add a note to a lead"""
    note = {
        "id": str(uuid.uuid4()),
        "text": data.get("text", ""),
        "added_by": current_user["id"],
        "added_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await leads_col.update_one({"id": lead_id}, {"$push": {"notes": note}})
    return {"message": "Note added"}


@router.post("/{lead_id}/follow-up")
async def schedule_follow_up(lead_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Schedule a follow-up for a lead"""
    follow_up = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "type": data.get("type", "call"),
        "scheduled_at": data.get("scheduled_at"),
        "message": data.get("message", ""),
        "status": "pending",
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc),
        "completed_at": None
    }
    await follow_ups_col.insert_one(follow_up)
    
    await leads_col.update_one({"id": lead_id}, {"$set": {"last_contacted_at": datetime.now(timezone.utc)}})
    
    return {"message": "Follow-up scheduled", "id": follow_up["id"]}


@router.get("/follow-ups/pending")
async def get_pending_follow_ups(current_user: dict = Depends(get_current_user)):
    """Get pending follow-ups"""
    query = {"status": "pending"}
    if current_user["role"] in ["partner", "sales_executive", "sr_sales_executive"]:
        query["created_by"] = current_user["id"]
    
    follow_ups = await follow_ups_col.find(query, {"_id": 0}).sort("scheduled_at", 1).to_list(50)
    for fu in follow_ups:
        for field in ["created_at", "scheduled_at", "completed_at"]:
            if isinstance(fu.get(field), datetime):
                fu[field] = fu[field].isoformat()
        lead = await leads_col.find_one({"id": fu["lead_id"]}, {"_id": 0, "name": 1, "email": 1, "phone": 1})
        fu["lead_name"] = lead.get("name", "Unknown") if lead else "Unknown"
        fu["lead_email"] = lead.get("email", "") if lead else ""
    return follow_ups


@router.put("/follow-ups/{follow_up_id}/complete")
async def complete_follow_up(follow_up_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Mark follow-up as completed"""
    await follow_ups_col.update_one({"id": follow_up_id}, {"$set": {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc),
        "outcome": data.get("outcome", "")
    }})
    return {"message": "Follow-up completed"}


@router.post("/{lead_id}/convert")
async def convert_lead(lead_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Convert a lead to a sale"""
    if current_user["role"] not in ["admin", "partner", "sales_executive", "sr_sales_executive"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await leads_col.update_one({"id": lead_id}, {"$set": {
        "stage": "converted",
        "converted": True,
        "converted_sale_id": data.get("sale_id"),
        "updated_at": datetime.now(timezone.utc)
    }})
    return {"message": "Lead converted to sale"}


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a lead"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await leads_col.delete_one({"id": lead_id})
    return {"message": "Lead deleted"}