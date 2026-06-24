"""Email Campaign Manager Router"""
from fastapi import APIRouter, HTTPException, Depends, Query
from core.database import db
from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
campaigns_col = db["campaigns"]
campaign_recipients_col = db["campaign_recipients"]
users_col = db["users"]

# Phase 21.N — RBAC migration
# All write/admin endpoints require campaign or marketing permission.
# Legacy `role == 'admin'` is honoured via _legacy_role shim during transition.
_CAMP_VIEW = require_any_permission("campaign.view.all", "marketing.view.all", "content.view.all", _legacy_role="admin")
_CAMP_WRITE = require_any_permission("campaign.send.any", "marketing.update.all", "content.create.any", _legacy_role="admin")


@router.post("/")
async def create_campaign(data: dict, current_user: dict = Depends(_CAMP_WRITE)):
    """Create a new email campaign"""
    campaign = {
        "id": str(uuid.uuid4()),
        "name": data.get("name", ""),
        "subject": data.get("subject", ""),
        "body": data.get("body", ""),
        "target_audience": data.get("target_audience", "all"),
        "target_roles": data.get("target_roles", []),
        "target_tags": data.get("target_tags", []),
        "status": "draft",
        "sent_count": 0,
        "opened_count": 0,
        "clicked_count": 0,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
        "sent_at": None,
        "scheduled_at": data.get("scheduled_at")
    }
    await campaigns_col.insert_one(campaign)
    return {"message": "Campaign created", "id": campaign["id"]}


@router.get("/")
async def get_campaigns(current_user: dict = Depends(_CAMP_VIEW)):
    """Get all campaigns"""
    campaigns = await campaigns_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for c in campaigns:
        for field in ["created_at", "sent_at", "scheduled_at"]:
            if isinstance(c.get(field), datetime):
                c[field] = c[field].isoformat()
    return campaigns


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, current_user: dict = Depends(_CAMP_VIEW)):
    """Get campaign details"""
    campaign = await campaigns_col.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    for field in ["created_at", "sent_at", "scheduled_at"]:
        if isinstance(campaign.get(field), datetime):
            campaign[field] = campaign[field].isoformat()
    
    recipients = await campaign_recipients_col.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(500)
    campaign["recipients"] = recipients
    return campaign


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: str, data: dict, current_user: dict = Depends(_CAMP_WRITE)):
    """Update campaign"""
    data.pop("id", None)
    data.pop("_id", None)
    await campaigns_col.update_one({"id": campaign_id}, {"$set": data})
    return {"message": "Campaign updated"}


@router.post("/{campaign_id}/send")
async def send_campaign(campaign_id: str, current_user: dict = Depends(_CAMP_WRITE)):
    """Send campaign to target audience (mocked — logs to DB)"""
    campaign = await campaigns_col.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Determine recipients based on target audience
    query = {"status": "active"}
    if campaign.get("target_audience") == "clients":
        query["role"] = "client"
    elif campaign.get("target_audience") == "partners":
        query["role"] = "partner"
    elif campaign.get("target_audience") == "leads":
        leads_col = db["leads"]
        leads = await leads_col.find({}, {"_id": 0, "email": 1, "name": 1}).to_list(500)
        sent_count = 0
        for lead in leads:
            if lead.get("email"):
                await campaign_recipients_col.insert_one({
                    "id": str(uuid.uuid4()),
                    "campaign_id": campaign_id,
                    "email": lead["email"],
                    "name": lead.get("name", ""),
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc)
                })
                sent_count += 1
        
        await campaigns_col.update_one({"id": campaign_id}, {"$set": {
            "status": "sent", "sent_count": sent_count, "sent_at": datetime.now(timezone.utc)
        }})
        return {"message": f"Campaign sent to {sent_count} leads"}
    
    if campaign.get("target_roles"):
        query["role"] = {"$in": campaign["target_roles"]}
    
    users = await users_col.find(query, {"_id": 0, "email": 1, "name": 1, "id": 1}).to_list(500)
    
    sent_count = 0
    for user in users:
        await campaign_recipients_col.insert_one({
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "user_id": user.get("id"),
            "email": user["email"],
            "name": user.get("name", ""),
            "status": "sent",
            "sent_at": datetime.now(timezone.utc)
        })
        sent_count += 1
        print(f"[CAMPAIGN MOCK] Sent to {user['email']}: {campaign['subject']}")
    
    await campaigns_col.update_one({"id": campaign_id}, {"$set": {
        "status": "sent",
        "sent_count": sent_count,
        "sent_at": datetime.now(timezone.utc)
    }})
    
    return {"message": f"Campaign sent to {sent_count} recipients"}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, current_user: dict = Depends(_CAMP_WRITE)):
    """Delete a campaign"""

@router.get("/stats/overview")
async def campaign_stats(current_user: dict = Depends(_CAMP_VIEW)):
    """Get overall campaign statistics"""
    total = await campaigns_col.count_documents({})
    sent = await campaigns_col.count_documents({"status": "sent"})
    total_recipients = await campaign_recipients_col.count_documents({})
    
    return {
        "total_campaigns": total,
        "sent_campaigns": sent,
        "draft_campaigns": total - sent,
        "total_recipients": total_recipients
    }
