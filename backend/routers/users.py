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
