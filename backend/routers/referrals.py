"""Referral Program Router"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import referrals_col, users_col
from core.auth import get_current_user
from core.services import create_notification, log_activity

router = APIRouter(prefix="/referrals", tags=["Referrals"])


class ReferralCreate(BaseModel):
    referred_name: str
    referred_email: str
    referred_phone: str = ""
    service_interested: str = ""
    notes: str = ""


@router.post("")
async def create_referral(request: ReferralCreate, current_user: dict = Depends(get_current_user)):
    """Client submits a referral"""
    existing = await referrals_col.find_one({"referred_email": request.referred_email, "referrer_id": current_user["id"]}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="You have already referred this person")
    referral = {
        "id": str(uuid.uuid4()),
        "referrer_id": current_user["id"], "referrer_name": current_user["name"],
        "referrer_email": current_user.get("email", ""),
        "referred_name": request.referred_name, "referred_email": request.referred_email,
        "referred_phone": request.referred_phone,
        "service_interested": request.service_interested,
        "notes": request.notes,
        "status": "pending",  # pending, contacted, converted, expired
        "reward_status": "pending",  # pending, eligible, claimed
        "created_at": datetime.now(timezone.utc)
    }
    await referrals_col.insert_one(referral)
    referral.pop("_id", None)
    referral["created_at"] = referral["created_at"].isoformat()
    # Notify admin
    admins = await users_col.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(10)
    for a in admins:
        await create_notification(a["id"], "New Referral", f"{current_user['name']} referred {request.referred_name}", "referral", referral["id"])
    await log_activity(current_user["id"], current_user["name"], "create_referral", "referral", referral["id"], {"referred": request.referred_name})
    return referral


@router.get("")
async def list_referrals(current_user: dict = Depends(get_current_user)):
    """List referrals"""
    if current_user["role"] == "admin":
        query = {}
    else:
        query = {"referrer_id": current_user["id"]}
    refs = await referrals_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    for r in refs:
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
    return refs


@router.put("/{referral_id}/status")
async def update_referral_status(referral_id: str, status: str, current_user: dict = Depends(get_current_user)):
    """Admin updates referral status"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if status not in ["pending", "contacted", "converted", "expired"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    ref = await referrals_col.find_one({"id": referral_id}, {"_id": 0})
    if not ref:
        raise HTTPException(status_code=404, detail="Not found")
    update = {"status": status}
    if status == "converted":
        update["reward_status"] = "eligible"
        await create_notification(ref["referrer_id"], "Referral Converted!", f"Your referral {ref['referred_name']} has been converted. Reward is now eligible!", "referral", referral_id)
    await referrals_col.update_one({"id": referral_id}, {"$set": update})
    return {"message": f"Status updated to {status}"}


@router.get("/stats")
async def referral_stats(current_user: dict = Depends(get_current_user)):
    """Get referral program statistics"""
    if current_user["role"] == "admin":
        query = {}
    else:
        query = {"referrer_id": current_user["id"]}
    refs = await referrals_col.find(query, {"_id": 0}).to_list(1000)
    total = len(refs)
    by_status = {}
    for r in refs:
        s = r.get("status", "pending")
        by_status[s] = by_status.get(s, 0) + 1
    converted = by_status.get("converted", 0)
    return {
        "total": total, "by_status": by_status,
        "conversion_rate": round(converted / total * 100) if total > 0 else 0,
        "converted": converted
    }
