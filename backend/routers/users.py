"""Users Router"""
from fastapi import APIRouter, HTTPException, Depends
from core.database import users_col
from core.auth import get_current_user, get_password_hash
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("")
async def get_users(role: str = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if role:
        query["role"] = role
    users = await users_col.find(query, {"_id": 0, "password": 0}).to_list(500)
    for u in users:
        if isinstance(u.get("created_at"), datetime):
            u["created_at"] = u["created_at"].isoformat()
    return users


@router.get("/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    user = await users_col.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if isinstance(user.get("created_at"), datetime):
        user["created_at"] = user["created_at"].isoformat()
    return user


@router.post("")
async def create_user(data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    existing = await users_col.find_one({"email": data["email"]})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user = {
        "id": str(uuid.uuid4()), "email": data["email"],
        "password": get_password_hash(data.get("password", "User@123")),
        "name": data["name"], "role": data.get("role", "client"),
        "mobile": data.get("mobile", ""), "status": "active",
        "commission_rate": data.get("commission_rate", 0.0),
        "created_at": datetime.now(timezone.utc)
    }
    await users_col.insert_one(user)
    return {"id": user["id"], "message": "User created"}


@router.put("/{user_id}")
async def update_user(user_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    update = {}
    for field in ["name", "email", "mobile", "role", "status", "commission_rate"]:
        if field in data:
            update[field] = data[field]
    
    if update:
        await users_col.update_one({"id": user_id}, {"$set": update})
    return {"message": "User updated"}


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await users_col.update_one({"id": user_id}, {"$set": {"status": "inactive"}})
    return {"message": "User deactivated"}
