"""Marketing Router — Referral System & Promo Codes"""
from fastapi import APIRouter, HTTPException, Depends, Query
from core.database import db
from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission
from core.services import create_notification, log_activity
import uuid, random, string
from datetime import datetime, timezone

router = APIRouter(prefix="/marketing", tags=["Marketing"])

referrals_col = db["referrals"]
promo_codes_col = db["promo_codes"]


# ============ REFERRAL SYSTEM ============

@router.get("/referral/my-code")
async def get_my_referral_code(current_user: dict = Depends(get_current_user)):
    """Get or generate a referral code for the current user"""
    existing = await referrals_col.find_one(
        {"referrer_id": current_user["id"], "type": "code"}, {"_id": 0}
    )
    if existing:
        # Count referrals
        count = await referrals_col.count_documents(
            {"referral_code": existing["code"], "type": "usage"}
        )
        return {"code": existing["code"], "referral_count": count}
    
    # Generate unique code
    prefix = current_user["name"].split()[0].upper()[:4] if current_user.get("name") else "REF"
    code = f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
    
    await referrals_col.insert_one({
        "id": str(uuid.uuid4()),
        "referrer_id": current_user["id"],
        "referrer_name": current_user.get("name", ""),
        "code": code,
        "type": "code",
        "created_at": datetime.now(timezone.utc)
    })
    return {"code": code, "referral_count": 0}


@router.post("/referral/redeem")
async def redeem_referral(data: dict, current_user: dict = Depends(get_current_user)):
    """Redeem a referral code"""
    code = data.get("code", "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Referral code required")
    
    referral = await referrals_col.find_one({"code": code, "type": "code"}, {"_id": 0})
    if not referral:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    if referral["referrer_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot use your own referral code")
    
    # Check if already used
    existing = await referrals_col.find_one({
        "referral_code": code, "redeemed_by": current_user["id"], "type": "usage"
    })
    if existing:
        raise HTTPException(status_code=400, detail="You have already redeemed this code")
    
    await referrals_col.insert_one({
        "id": str(uuid.uuid4()),
        "referral_code": code,
        "referrer_id": referral["referrer_id"],
        "redeemed_by": current_user["id"],
        "redeemed_by_name": current_user.get("name", ""),
        "type": "usage",
        "created_at": datetime.now(timezone.utc)
    })
    
    await create_notification(referral["referrer_id"], "Referral Used!",
        f"{current_user.get('name', 'Someone')} used your referral code!",
        "referral_used", current_user["id"])
    
    return {"message": "Referral code applied successfully!"}


@router.get("/referral/stats")
async def referral_stats(
    current_user: dict = Depends(
        require_any_permission("marketing.view.all", "content.view.all", _legacy_role="admin")
    ),
):
    """Get referral statistics for admin / marketing head."""
    total_codes = await referrals_col.count_documents({"type": "code"})
    total_uses = await referrals_col.count_documents({"type": "usage"})
    
    # Top referrers
    pipeline = [
        {"$match": {"type": "usage"}},
        {"$group": {"_id": "$referrer_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_referrers = []
    async for item in referrals_col.aggregate(pipeline):
        from core.database import users_col
        user = await users_col.find_one({"id": item["_id"]}, {"_id": 0, "password": 0})
        top_referrers.append({
            "name": user["name"] if user else "Unknown",
            "count": item["count"]
        })
    
    return {"total_codes": total_codes, "total_uses": total_uses, "top_referrers": top_referrers}


# ============ PROMO CODES ============

@router.post("/promo")
async def create_promo(
    data: dict,
    current_user: dict = Depends(
        require_any_permission("marketing.update.all", "promo.manage.all", _legacy_role="admin")
    ),
):
    """Create a promo code"""
    code = data.get("code", "").strip().upper()
    if not code or len(code) < 3:
        raise HTTPException(status_code=400, detail="Promo code must be at least 3 characters")
    
    existing = await promo_codes_col.find_one({"code": code})
    if existing:
        raise HTTPException(status_code=400, detail="Promo code already exists")
    
    promo = {
        "id": str(uuid.uuid4()),
        "code": code,
        "discount_type": data.get("discount_type", "percentage"),
        "discount_value": data.get("discount_value", 10),
        "max_uses": data.get("max_uses", 100),
        "current_uses": 0,
        "valid_from": data.get("valid_from"),
        "valid_until": data.get("valid_until"),
        "applicable_products": data.get("applicable_products", []),
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }
    await promo_codes_col.insert_one(promo)
    await log_activity(current_user["id"], current_user["name"], "created", "promo_code", promo["id"],
        f"Created promo code: {code}")
    return {"id": promo["id"], "message": f"Promo code {code} created"}


@router.get("/promos")
async def get_promos(
    current_user: dict = Depends(
        require_any_permission("marketing.view.all", "promo.manage.all", "content.view.all", _legacy_role="admin")
    ),
):
    """Get all promo codes"""
    promos = await promo_codes_col.find({}, {"_id": 0}).to_list(500)
    for p in promos:
        if isinstance(p.get("created_at"), datetime):
            p["created_at"] = p["created_at"].isoformat()
    return promos


@router.post("/promo/validate")
async def validate_promo(data: dict, current_user: dict = Depends(get_current_user)):
    """Validate a promo code"""
    code = data.get("code", "").strip().upper()
    promo = await promo_codes_col.find_one({"code": code, "is_active": True}, {"_id": 0})
    if not promo:
        raise HTTPException(status_code=404, detail="Invalid or expired promo code")
    if promo["current_uses"] >= promo["max_uses"]:
        raise HTTPException(status_code=400, detail="Promo code usage limit reached")
    
    return {
        "valid": True,
        "code": promo["code"],
        "discount_type": promo["discount_type"],
        "discount_value": promo["discount_value"]
    }


@router.delete("/promo/{promo_id}")
async def delete_promo(
    promo_id: str,
    current_user: dict = Depends(
        require_any_permission("marketing.update.all", "promo.manage.all", _legacy_role="admin")
    ),
):
    """Deactivate a promo code"""
    await promo_codes_col.update_one({"id": promo_id}, {"$set": {"is_active": False}})
    return {"message": "Promo code deactivated"}
