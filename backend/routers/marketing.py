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
    
    is_active = data.get("is_active", data.get("active", True))
    if is_active is None:
        is_active = True
    
    promo = {
        "id": str(uuid.uuid4()),
        "code": code,
        "discount_type": data.get("discount_type", "percentage"),
        "discount_value": data.get("discount_value", 10),
        "max_uses": data.get("max_uses", 100),
        "current_uses": 0,
        "used_count": 0,
        "valid_from": data.get("valid_from"),
        "valid_until": data.get("valid_until"),
        "applicable_products": data.get("applicable_products", []),
        "is_active": bool(is_active),
        "active": bool(is_active),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }
    await promo_codes_col.insert_one(promo)
    await log_activity(current_user["id"], current_user["name"], "created", "promo_code", promo["id"],
        f"Created promo code: {code}")
    return {"id": promo["id"], "message": f"Promo code {code} created"}


@router.get("/promos")
async def get_promos(current_user: dict = Depends(get_current_user)):
    """Get all promo codes (available to Admin, Partners, and authenticated users)"""
    promos = await promo_codes_col.find({}, {"_id": 0}).to_list(500)
    for p in promos:
        c_uses = int(p.get("current_uses") if p.get("current_uses") is not None else (p.get("used_count") or 0))
        m_uses = int(p.get("max_uses") or 100)
        is_limit_reached = m_uses > 0 and c_uses >= m_uses
        is_explicitly_inactive = p.get("status") == "inactive"
        
        # If under limit, it's active unless explicitly marked inactive by admin
        is_effective_active = not is_limit_reached and not is_explicitly_inactive
        p["is_limit_reached"] = is_limit_reached
        p["is_active"] = is_effective_active
        p["active"] = is_effective_active
        p["status"] = "limit_reached" if is_limit_reached else ("active" if is_effective_active else "inactive")
        p["used_count"] = c_uses
        p["current_uses"] = c_uses
        if isinstance(p.get("created_at"), datetime):
            p["created_at"] = p["created_at"].isoformat()
    return promos


def _calc_promo_discount(promo: dict, amount: float):
    discount_type = promo.get("discount_type", "percentage")
    discount_val = float(promo.get("discount_value", 0))
    if discount_type == "percentage":
        discount_amount = round(amount * (discount_val / 100.0), 2)
    else:
        discount_amount = round(min(amount, discount_val), 2)
    final_amount = max(0.0, round(amount - discount_amount, 2))
    return discount_amount, final_amount


@router.post("/promo/validate")
async def validate_promo(data: dict, current_user: dict = Depends(get_current_user)):
    """Validate a promo code and calculate live discount for an amount"""
    code = data.get("code", "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Please enter a promo code")
    promo = await promo_codes_col.find_one({"code": code}, {"_id": 0})
    if not promo:
        raise HTTPException(status_code=404, detail=f"Promo code '{code}' is invalid or expired")
    
    current_uses = int(promo.get("current_uses") if promo.get("current_uses") is not None else (promo.get("used_count") or 0))
    max_uses = int(promo.get("max_uses") or 100)
    if max_uses > 0 and current_uses >= max_uses:
        raise HTTPException(status_code=400, detail=f"Promo code '{code}' usage limit reached ({current_uses}/{max_uses})")
    
    if promo.get("status") == "inactive":
        raise HTTPException(status_code=400, detail=f"Promo code '{code}' is inactive")
    
    amount = float(data.get("amount", 0) or 0)
    discount_amount, final_amount = _calc_promo_discount(promo, amount) if amount > 0 else (0.0, 0.0)

    return {
        "valid": True,
        "code": promo["code"],
        "discount_type": promo["discount_type"],
        "discount_value": promo["discount_value"],
        "original_amount": amount,
        "discount_amount": discount_amount,
        "final_amount": final_amount,
        "message": f"{promo['discount_value']}% OFF applied" if promo['discount_type'] == 'percentage' else f"Flat ₹{promo['discount_value']} OFF applied"
    }


@router.post("/promo/public-validate")
async def public_validate_promo(data: dict):
    """Public validation endpoint for unauthenticated clients on public payment links"""
    code = data.get("code", "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Please enter a promo code")
    promo = await promo_codes_col.find_one({"code": code}, {"_id": 0})
    if not promo:
        raise HTTPException(status_code=404, detail=f"Promo code '{code}' is invalid or expired")
    
    current_uses = int(promo.get("current_uses") if promo.get("current_uses") is not None else (promo.get("used_count") or 0))
    max_uses = int(promo.get("max_uses") or 100)
    if max_uses > 0 and current_uses >= max_uses:
        raise HTTPException(status_code=400, detail=f"Promo code '{code}' usage limit reached ({current_uses}/{max_uses})")
    
    if promo.get("status") == "inactive":
        raise HTTPException(status_code=400, detail=f"Promo code '{code}' is inactive")
    
    amount = float(data.get("amount", 0) or 0)
    discount_amount, final_amount = _calc_promo_discount(promo, amount) if amount > 0 else (0.0, 0.0)

    return {
        "valid": True,
        "code": promo["code"],
        "discount_type": promo["discount_type"],
        "discount_value": promo["discount_value"],
        "original_amount": amount,
        "discount_amount": discount_amount,
        "final_amount": final_amount,
        "message": f"{promo['discount_value']}% OFF applied" if promo['discount_type'] == 'percentage' else f"Flat ₹{promo['discount_value']} OFF applied"
    }


@router.put("/promo/{promo_id}")
async def update_promo(
    promo_id: str,
    data: dict,
    current_user: dict = Depends(
        require_any_permission("marketing.update.all", "promo.manage.all", _legacy_role="admin")
    ),
):
    """Update promo code details (code, discount, max_uses, is_active, validity, etc.)"""
    existing = await promo_codes_col.find_one({"$or": [{"id": promo_id}, {"code": promo_id.upper()}]})
    if not existing:
        raise HTTPException(status_code=404, detail="Promo code not found")
    
    code = data.get("code", existing.get("code", "")).strip().upper()
    if not code or len(code) < 3:
        raise HTTPException(status_code=400, detail="Promo code must be at least 3 characters")
    
    # Check if another promo code with this new code name exists
    if code != existing.get("code", "").upper():
        duplicate = await promo_codes_col.find_one({"code": code, "id": {"$ne": existing.get("id")}})
        if duplicate:
            raise HTTPException(status_code=400, detail=f"Promo code '{code}' already exists")
    
    max_uses = int(data.get("max_uses", existing.get("max_uses", 100)) or 100)
    current_uses = int(existing.get("current_uses") if existing.get("current_uses") is not None else (existing.get("used_count") or 0))
    is_limit_reached = max_uses > 0 and current_uses >= max_uses

    raw_active = data.get("is_active", data.get("active"))
    if raw_active is None:
        is_active = not is_limit_reached
    else:
        is_active = bool(raw_active)

    status = "limit_reached" if is_limit_reached else ("active" if is_active else "inactive")

    update_fields = {
        "code": code,
        "discount_type": data.get("discount_type", existing.get("discount_type", "percentage")),
        "discount_value": float(data.get("discount_value", existing.get("discount_value", 10))),
        "max_uses": max_uses,
        "valid_from": data.get("valid_from", existing.get("valid_from")),
        "valid_until": data.get("valid_until", existing.get("valid_until")),
        "applicable_products": data.get("applicable_products", existing.get("applicable_products", [])),
        "notes": data.get("notes", existing.get("notes", "")),
        "is_active": bool(is_active and not is_limit_reached),
        "active": bool(is_active and not is_limit_reached),
        "status": status,
        "updated_at": datetime.now(timezone.utc),
        "updated_by": current_user["id"],
    }
    
    await promo_codes_col.update_one({"id": existing["id"]}, {"$set": update_fields})
    await log_activity(current_user["id"], current_user.get("name", "Admin"), "updated", "promo_code", existing["id"],
        f"Updated promo code: {code} (discount: {update_fields['discount_value']}, max_uses: {max_uses}, status: {status})")
    
    return {"id": existing["id"], "message": f"Promo code {code} updated successfully"}


@router.delete("/promo/{promo_id}")
async def delete_promo(
    promo_id: str,
    current_user: dict = Depends(
        require_any_permission("marketing.update.all", "promo.manage.all", _legacy_role="admin")
    ),
):
    """Deactivate a promo code"""
    await promo_codes_col.update_one({"id": promo_id}, {"$set": {"is_active": False, "active": False}})
    return {"message": "Promo code deactivated"}
