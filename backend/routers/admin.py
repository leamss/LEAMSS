"""
Admin management routes for LEAMSS Portal
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

from core.database import db
from core.auth import get_current_user, require_role, UserRole, create_access_token
from core.models import SystemSettings

router = APIRouter(tags=["Admin"])


@router.post("/impersonate/{user_id}")
async def impersonate_user(user_id: str, admin: dict = Depends(require_role([UserRole.ADMIN]))):
    """Impersonate a user (Admin only)"""
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create token for target user
    token = create_access_token({"sub": target_user["email"]})
    
    return {
        "token": token,
        "user": {
            "id": target_user["id"],
            "email": target_user["email"],
            "name": target_user["name"],
            "role": target_user["role"]
        },
        "admin_id": admin["id"],
        "admin_name": admin["name"]
    }


@router.get("/stats/dashboard")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """Get dashboard statistics based on user role"""
    stats = {}
    
    if user["role"] == UserRole.ADMIN:
        stats["total_users"] = await db.users.count_documents({})
        stats["total_cases"] = await db.cases.count_documents({})
        stats["active_cases"] = await db.cases.count_documents({"status": "active"})
        stats["pending_sales"] = await db.sales.count_documents({"status": "pending"})
        stats["total_products"] = await db.products.count_documents({})
        stats["open_tickets"] = await db.tickets.count_documents({"status": {"$in": ["open", "in_progress"]}})
        stats["pending_docs"] = await db.documents.count_documents({"status": "pending_review"})
        
    elif user["role"] == UserRole.CASE_MANAGER:
        stats["my_cases"] = await db.cases.count_documents({"case_manager_id": user["id"]})
        stats["active_cases"] = await db.cases.count_documents({"case_manager_id": user["id"], "status": "active"})
        stats["pending_docs"] = await db.documents.count_documents({"status": "pending_review"})
        stats["my_tickets"] = await db.tickets.count_documents({
            "$or": [{"created_by": user["id"]}, {"target_user_ids": user["id"]}]
        })
        
    elif user["role"] == UserRole.PARTNER:
        stats["my_sales"] = await db.sales.count_documents({"partner_id": user["id"]})
        stats["approved_sales"] = await db.sales.count_documents({"partner_id": user["id"], "status": "approved"})
        stats["pending_sales"] = await db.sales.count_documents({"partner_id": user["id"], "status": "pending"})
        stats["total_commission"] = 0
        sales = await db.sales.find({"partner_id": user["id"], "status": "approved"}).to_list(1000)
        stats["total_commission"] = sum(s.get("commission_amount", 0) for s in sales)
        
    elif user["role"] == UserRole.CLIENT:
        stats["my_cases"] = await db.cases.count_documents({"client_id": user["id"]})
        case = await db.cases.find_one({"client_id": user["id"]})
        if case:
            stats["current_step"] = case.get("current_step", "N/A")
            stats["case_status"] = case.get("status", "N/A")
            # Calculate progress
            steps = case.get("steps", [])
            completed = sum(1 for s in steps if s.get("status") == "completed")
            stats["progress"] = int((completed / len(steps)) * 100) if steps else 0
        stats["unread_notifications"] = await db.notifications.count_documents({"user_id": user["id"], "is_read": False})
    
    return stats


# ==================== Settings Endpoints ====================

@router.get("/settings")
async def get_system_settings(user: dict = Depends(get_current_user)):
    """Get system settings"""
    settings = await db.settings.find_one({"key": "global"})
    if not settings:
        # Return defaults
        return {"allow_case_manager_workflow_customization": False}
    
    return {
        "allow_case_manager_workflow_customization": settings.get("allow_case_manager_workflow_customization", False)
    }


@router.put("/settings")
async def update_system_settings(
    settings: SystemSettings,
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Update system settings (Admin only)"""
    await db.settings.update_one(
        {"key": "global"},
        {"$set": {
            "key": "global",
            "allow_case_manager_workflow_customization": settings.allow_case_manager_workflow_customization,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user["id"]
        }},
        upsert=True
    )
    return {"message": "Settings updated successfully"}
