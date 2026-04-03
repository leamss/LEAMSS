"""Settings Router"""
from fastapi import APIRouter, HTTPException, Depends
from core.database import settings_col
from core.auth import get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
async def get_settings(current_user: dict = Depends(get_current_user)):
    settings = await settings_col.find_one({"key": "global"}, {"_id": 0})
    return settings or {
        "company_name": "LEAMSS Immigration Services",
        "default_commission_rate": 10,
        "allow_partner_registration": True,
        "require_document_verification": True,
        "auto_assign_case_manager": False,
        "allow_case_manager_workflow_customization": False,
        "base_currency": "USD",
        "exchange_rate_usd_to_inr": 83.50,
        "show_dual_currency": True
    }


@router.put("")
async def update_settings(data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    data["key"] = "global"
    data["updated_at"] = datetime.now(timezone.utc)
    await settings_col.update_one({"key": "global"}, {"$set": data}, upsert=True)
    return {"message": "Settings updated"}


@router.get("/exchange-rate")
async def get_exchange_rate(current_user: dict = Depends(get_current_user)):
    """Get current USD to INR exchange rate"""
    settings = await settings_col.find_one({"key": "global"}, {"_id": 0})
    rate = settings.get("exchange_rate_usd_to_inr", 83.50) if settings else 83.50
    return {
        "base_currency": "USD",
        "target_currency": "INR",
        "rate": rate,
        "show_dual_currency": settings.get("show_dual_currency", True) if settings else True
    }
