"""
User management routes for LEAMSS Portal
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from core.database import db
from core.auth import get_current_user, require_role, UserRole, pwd_context
from core.models import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
async def get_all_users(user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Get all users (Admin only)"""
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]


@router.get("/case-managers")
async def get_case_managers(user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Get all case managers for assignment"""
    managers = await db.users.find(
        {"role": UserRole.CASE_MANAGER}, 
        {"_id": 0, "password_hash": 0}
    ).to_list(100)
    return managers


@router.put("/{user_id}")
async def update_user(user_id: str, update_data: dict, user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Update user details (Admin only)"""
    # Don't allow password update through this endpoint
    update_data.pop("password_hash", None)
    update_data.pop("password", None)
    
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    return {"message": "User updated successfully"}


@router.delete("/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Delete a user (Admin only)"""
    await db.users.delete_one({"id": user_id})
    return {"message": "User deleted successfully"}


@router.get("/ticket-recipients")
async def get_ticket_recipients(user: dict = Depends(get_current_user)):
    """Get available ticket recipients based on user role"""
    current_role = user["role"]
    recipients = []
    
    if current_role == UserRole.ADMIN:
        # Admin can send to anyone
        all_users = await db.users.find(
            {"id": {"$ne": user["id"]}}, 
            {"_id": 0, "id": 1, "name": 1, "role": 1, "email": 1}
        ).to_list(500)
        recipients = all_users
        
    elif current_role == UserRole.CASE_MANAGER:
        # Case Manager can send to their clients and admins
        cases = await db.cases.find(
            {"case_manager_id": user["id"]},
            {"_id": 0, "client_id": 1, "client_name": 1}
        ).to_list(100)
        
        # Get unique clients
        seen_ids = set()
        for case in cases:
            if case["client_id"] not in seen_ids:
                seen_ids.add(case["client_id"])
                recipients.append({
                    "id": case["client_id"],
                    "name": case["client_name"],
                    "role": "client"
                })
        
        # Add admins
        admins = await db.users.find(
            {"role": UserRole.ADMIN},
            {"_id": 0, "id": 1, "name": 1, "role": 1}
        ).to_list(100)
        recipients.extend(admins)
        
    elif current_role == UserRole.CLIENT:
        # Client can send to their case manager and admins
        cases = await db.cases.find(
            {"client_id": user["id"]},
            {"_id": 0, "case_manager_id": 1, "case_manager_name": 1}
        ).to_list(10)
        
        seen_ids = set()
        for case in cases:
            if case["case_manager_id"] not in seen_ids:
                seen_ids.add(case["case_manager_id"])
                recipients.append({
                    "id": case["case_manager_id"],
                    "name": case["case_manager_name"],
                    "role": "case_manager"
                })
        
        # Add admins
        admins = await db.users.find(
            {"role": UserRole.ADMIN},
            {"_id": 0, "id": 1, "name": 1, "role": 1}
        ).to_list(100)
        recipients.extend(admins)
        
    elif current_role == UserRole.PARTNER:
        # Partner can only send to admins
        admins = await db.users.find(
            {"role": UserRole.ADMIN},
            {"_id": 0, "id": 1, "name": 1, "role": 1}
        ).to_list(100)
        recipients = admins
    
    return recipients
