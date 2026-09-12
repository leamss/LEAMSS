"""Leads & CRM Pipeline Router"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from core.database import db
from core.auth import get_current_user
from core.services import log_activity, create_notification
from core.website_sync import upsert_website_lead
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/leads", tags=["leads"])
leads_col = db["leads"]
follow_ups_col = db["follow_ups"]
users_col = db["users"]


async def _next_lead_number():
    """Generate a human-friendly sequential lead number like LD006672."""
    count = await leads_col.count_documents({})
    return f"LD{(count + 6620):06d}"


@router.post("/capture")
async def capture_lead(request_or_data: Request | dict | None = None):
    """Create or update a lead — public website registration, landing page, Laravel, or authenticated."""
    if isinstance(request_or_data, Request):
        try:
            data = await request_or_data.json()
        except Exception:
            form = await request_or_data.form()
            data = dict(form)
    elif isinstance(request_or_data, dict):
        data = request_or_data
    else:
        data = {}

    if not data:
        raise HTTPException(status_code=400, detail="No lead registration payload provided")

    lead_doc, is_new = await upsert_website_lead(data)
    return {
        "status": "success",
        "message": "Lead saved successfully.",
        "action": "created" if is_new else "updated",
        "lead_id": lead_doc.get("id"),
        "lead_number": lead_doc.get("lead_number"),
        "unique_id": lead_doc.get("unique_id"),
        "payment_status": lead_doc.get("payment_status"),
    }


@router.post("/register")
async def register_lead_alias(request: Request):
    return await capture_lead(request)


@router.post("/registration")
async def registration_lead_alias(request: Request):
    return await capture_lead(request)


@router.post("/navratri-registration")
async def navratri_lead_alias(request: Request):
    return await capture_lead(request)


@router.post("/website-lead")
async def website_lead_alias(request: Request):
    return await capture_lead(request)


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


@router.post("/{lead_id}/convert-to-pa")
async def convert_lead_to_pa(lead_id: str, payload: dict = None, current_user: dict = Depends(get_current_user)):
    """Converts a Lead into a full Pre-Assessment in one click."""
    if current_user["role"] not in ["admin", "partner", "case_manager", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head"]:
        raise HTTPException(status_code=403, detail="Not authorized to convert leads to Pre-Assessment")

    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    p = payload or {}
    pa_id = str(uuid.uuid4())
    pa_number = f"PA-{datetime.now().strftime('%Y%m%d')}-{pa_id[:6].upper()}"
    country_code = (p.get("country") or lead.get("country_of_interest") or "AU").upper()[:2]
    service_type = p.get("service_type") or lead.get("service_interested") or "General Skilled Migration"

    partner_id = lead.get("partner_id") or lead.get("assigned_to") or current_user["id"]
    partner_name = lead.get("partner_name") or lead.get("assigned_to_name") or current_user.get("name", "Admin")

    pa_doc = {
        "id": pa_id,
        "pa_number": pa_number,
        "partner_id": partner_id,
        "partner_name": partner_name,
        "case_manager_id": lead.get("case_manager_id"),
        "case_manager_name": lead.get("case_manager_name", ""),
        "created_by_user_id": current_user["id"],
        "created_by_role": current_user.get("role", "partner"),
        "created_by_user_type": current_user.get("user_type", "internal"),
        "client_name": lead.get("name", "Unnamed Client"),
        "client_email": lead.get("email", ""),
        "client_mobile": lead.get("phone", ""),
        "country": country_code,
        "target_country": country_code,
        "service_type": service_type,
        "product_id": p.get("product_id", ""),
        "product_name": p.get("product_name", "General Skilled Migration"),
        "education": lead.get("latest_qualification", ""),
        "work_experience": lead.get("total_work_experience", ""),
        "dob": lead.get("date_of_birth", ""),
        "marital_status": lead.get("marital_status", ""),
        "notes": lead.get("message") or f"Converted from CRM Lead {lead.get('unique_id', '')}",
        "lead_id": lead_id,
        "lead_source": lead.get("source", "website"),
        "lead_source_detail": lead.get("subsource", ""),
        "stage": "new",
        "status": "active",
        "fee_payment_status": "paid" if lead.get("payment_status") == "success" else "pending",
        "sale_type": "standard",
        "pa_fees_amount": lead.get("payment_amount") or 5100,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    await db["pre_assessments"].insert_one(pa_doc)

    # Link resume document if available
    resume_url = lead.get("resume_url") or lead.get("resume_path")
    if resume_url:
        doc_id = str(uuid.uuid4())
        await db["pre_assessment_documents"].insert_one({
            "id": doc_id,
            "pre_assessment_id": pa_id,
            "name": f"Resume - {lead.get('name', 'Lead')}",
            "doc_type": "resume",
            "file_url": resume_url,
            "file_path": lead.get("resume_path", ""),
            "status": "uploaded",
            "uploaded_at": datetime.now(timezone.utc),
        })

    # Mark lead as converted
    await leads_col.update_one(
        {"id": lead_id},
        {"$set": {
            "converted": True,
            "converted_pa_id": pa_id,
            "converted_pa_number": pa_number,
            "stage": "converted",
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    await log_activity(
        current_user["id"], current_user.get("name", ""),
        "convert_lead_to_pa", "lead", lead_id,
        f"Converted Lead {lead.get('name')} to Pre-Assessment {pa_number}"
    )

    return {
        "status": "success",
        "message": "Pre-Assessment created successfully",
        "pa_id": pa_id,
        "pa_number": pa_number,
        "deep_link": f"/admin?tab=pre-assessments&pa_id={pa_id}"
    }


@router.post("/bulk-create-pa")
async def bulk_create_pa(payload: dict, current_user: dict = Depends(get_current_user)):
    """Creates Pre-Assessments for multiple selected leads in bulk."""
    if current_user["role"] not in ["admin", "partner", "case_manager", "sales_executive", "sr_sales_executive", "sales_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    lead_ids = payload.get("lead_ids", [])
    if not lead_ids:
        raise HTTPException(status_code=400, detail="No lead IDs provided")

    created_pas = []
    leads = await leads_col.find({"id": {"$in": lead_ids}}, {"_id": 0}).to_list(100)

    for lead in leads:
        lead_id = lead["id"]
        pa_id = str(uuid.uuid4())
        pa_number = f"PA-{datetime.now().strftime('%Y%m%d')}-{pa_id[:6].upper()}"
        country_code = (lead.get("country_of_interest") or "AU").upper()[:2]
        service_type = lead.get("service_interested") or "General Skilled Migration"

        partner_id = lead.get("partner_id") or lead.get("assigned_to") or current_user["id"]
        partner_name = lead.get("partner_name") or lead.get("assigned_to_name") or current_user.get("name", "Admin")

        pa_doc = {
            "id": pa_id,
            "pa_number": pa_number,
            "partner_id": partner_id,
            "partner_name": partner_name,
            "case_manager_id": lead.get("case_manager_id"),
            "case_manager_name": lead.get("case_manager_name", ""),
            "created_by_user_id": current_user["id"],
            "created_by_role": current_user.get("role", "partner"),
            "client_name": lead.get("name", "Client"),
            "client_email": lead.get("email", ""),
            "client_mobile": lead.get("phone", ""),
            "country": country_code,
            "target_country": country_code,
            "service_type": service_type,
            "product_id": "",
            "product_name": "General Skilled Migration",
            "education": lead.get("latest_qualification", ""),
            "work_experience": lead.get("total_work_experience", ""),
            "dob": lead.get("date_of_birth", ""),
            "marital_status": lead.get("marital_status", ""),
            "notes": f"Bulk converted from Lead {lead.get('unique_id', '')}",
            "lead_id": lead_id,
            "lead_source": lead.get("source", "website"),
            "stage": "new",
            "status": "active",
            "fee_payment_status": "paid" if lead.get("payment_status") == "success" else "pending",
            "sale_type": "standard",
            "pa_fees_amount": 5100,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await db["pre_assessments"].insert_one(pa_doc)

        resume_url = lead.get("resume_url") or lead.get("resume_path")
        if resume_url:
            await db["pre_assessment_documents"].insert_one({
                "id": str(uuid.uuid4()),
                "pre_assessment_id": pa_id,
                "name": f"Resume - {lead.get('name', 'Lead')}",
                "doc_type": "resume",
                "file_url": resume_url,
                "status": "uploaded",
                "uploaded_at": datetime.now(timezone.utc),
            })

        await leads_col.update_one(
            {"id": lead_id},
            {"$set": {
                "converted": True,
                "converted_pa_id": pa_id,
                "converted_pa_number": pa_number,
                "stage": "converted",
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        created_pas.append({
            "lead_id": lead_id,
            "client_name": lead.get("name"),
            "pa_id": pa_id,
            "pa_number": pa_number,
        })

    return {
        "status": "success",
        "created_count": len(created_pas),
        "pa_list": created_pas,
    }


@router.post("/bulk-assign")
async def bulk_assign_leads(payload: dict, current_user: dict = Depends(get_current_user)):
    """Assign multiple leads to a team member (Partner, Case Manager, or Sales Agent)."""
    if current_user["role"] not in ["admin", "case_manager", "sales_manager", "sales_head", "partner"]:
        raise HTTPException(status_code=403, detail="Admin or manager access required for bulk assignment")

    lead_ids = payload.get("lead_ids", [])
    assigned_to = payload.get("assigned_to") or payload.get("user_id")
    assigned_to_name = payload.get("assigned_to_name")
    assignment_type = payload.get("assignment_type", "agent")  # "agent" | "partner" | "case_manager"

    if not lead_ids or not assigned_to:
        raise HTTPException(status_code=400, detail="lead_ids and assigned_to are required")

    user = await users_col.find_one({"id": assigned_to}, {"_id": 0, "name": 1, "role": 1})
    if user:
        if not assigned_to_name:
            assigned_to_name = user.get("name", "Assigned Member")
        user_role = user.get("role", "")
    else:
        user_role = ""

    update_doc = {
        "updated_at": datetime.now(timezone.utc)
    }

    if assignment_type == "partner" or user_role == "partner":
        update_doc["partner_id"] = assigned_to
        update_doc["partner_name"] = assigned_to_name
        update_doc["assigned_to"] = assigned_to
        update_doc["assigned_to_name"] = assigned_to_name
    elif assignment_type == "case_manager" or user_role == "case_manager":
        update_doc["case_manager_id"] = assigned_to
        update_doc["case_manager_name"] = assigned_to_name
        update_doc["assigned_to"] = assigned_to
        update_doc["assigned_to_name"] = assigned_to_name
    else:
        update_doc["assigned_to"] = assigned_to
        update_doc["assigned_to_name"] = assigned_to_name

    result = await leads_col.update_many(
        {"id": {"$in": lead_ids}},
        {"$set": update_doc}
    )

    return {
        "status": "success",
        "updated_count": result.modified_count,
        "assigned_to_name": assigned_to_name,
        "assignment_type": assignment_type,
    }


@router.put("/{lead_id}/assign")
async def assign_single_lead(lead_id: str, payload: dict, current_user: dict = Depends(get_current_user)):
    """Assign a single lead to a team member (Partner, Case Manager, or Sales Agent)."""
    assigned_to = payload.get("assigned_to") or payload.get("user_id")
    assigned_to_name = payload.get("assigned_to_name")
    assignment_type = payload.get("assignment_type", "agent")  # "agent" | "partner" | "case_manager"

    if not assigned_to:
        raise HTTPException(status_code=400, detail="assigned_to is required")

    user = await users_col.find_one({"id": assigned_to}, {"_id": 0, "name": 1, "role": 1})
    if user:
        if not assigned_to_name:
            assigned_to_name = user.get("name", "Assigned Member")
        user_role = user.get("role", "")
    else:
        user_role = ""

    update_doc = {
        "updated_at": datetime.now(timezone.utc)
    }

    if assignment_type == "partner" or user_role == "partner":
        update_doc["partner_id"] = assigned_to
        update_doc["partner_name"] = assigned_to_name
        update_doc["assigned_to"] = assigned_to
        update_doc["assigned_to_name"] = assigned_to_name
    elif assignment_type == "case_manager" or user_role == "case_manager":
        update_doc["case_manager_id"] = assigned_to
        update_doc["case_manager_name"] = assigned_to_name
        update_doc["assigned_to"] = assigned_to
        update_doc["assigned_to_name"] = assigned_to_name
    else:
        update_doc["assigned_to"] = assigned_to
        update_doc["assigned_to_name"] = assigned_to_name

    await leads_col.update_one(
        {"id": lead_id},
        {"$set": update_doc}
    )

    return {
        "status": "success",
        "message": "Lead assigned successfully",
        "assigned_to_name": assigned_to_name,
        "assignment_type": assignment_type,
        "lead_id": lead_id
    }


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a lead"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await leads_col.delete_one({"id": lead_id})
    return {"message": "Lead deleted"}