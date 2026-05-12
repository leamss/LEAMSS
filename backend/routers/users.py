"""Users Router"""
from fastapi import APIRouter, HTTPException, Depends
from core.database import users_col, audit_logs_col
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
        "commission_rate_history": [],
        "employment_type": data.get("employment_type", "external"),
        "manager_id": data.get("manager_id"),
        "created_at": datetime.now(timezone.utc)
    }
    await users_col.insert_one(user)
    return {"id": user["id"], "message": "User created"}


@router.put("/{user_id}")
async def update_user(user_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    user = await users_col.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update = {}
    for field in ["name", "email", "mobile", "role", "status", "employment_type", "manager_id"]:
        if field in data:
            update[field] = data[field]
    
    # Validate employment_type
    if "employment_type" in update and update["employment_type"] not in ("employee", "external"):
        raise HTTPException(status_code=400, detail="employment_type must be 'employee' or 'external'")
    
    # Track commission rate changes with effective date
    if "commission_rate" in data and data["commission_rate"] != user.get("commission_rate"):
        old_rate = user.get("commission_rate", 0)
        new_rate = data["commission_rate"]
        effective_date = data.get("commission_effective_date", datetime.now(timezone.utc).isoformat())
        
        history_entry = {
            "old_rate": old_rate,
            "new_rate": new_rate,
            "effective_from": effective_date,
            "changed_at": datetime.now(timezone.utc).isoformat(),
            "changed_by": current_user["id"]
        }
        
        update["commission_rate"] = new_rate
        
        await users_col.update_one({"id": user_id}, {
            "$set": update,
            "$push": {"commission_rate_history": history_entry}
        })
        
        await audit_logs_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": current_user["id"],
            "action": "commission_rate_changed", "entity_type": "user",
            "entity_id": user_id, "new_value": {
                "old_rate": old_rate, "new_rate": new_rate,
                "effective_from": effective_date, "user_name": user.get("name")
            }, "created_at": datetime.now(timezone.utc)
        })
        
        return {"message": f"User updated. Commission rate changed from {old_rate}% to {new_rate}% (effective {effective_date})"}
    
    if update:
        await users_col.update_one({"id": user_id}, {"$set": update})
    return {"message": "User updated"}


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await users_col.update_one({"id": user_id}, {"$set": {"status": "inactive"}})
    return {"message": "User deactivated"}


@router.put("/{user_id}/reset-password")
async def reset_password(user_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Admin reset user password"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    user = await users_col.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_password = data.get("new_password")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    hashed = get_password_hash(new_password)
    await users_col.update_one({"id": user_id}, {"$set": {"password": hashed}})
    
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "password_reset", "entity_type": "user",
        "entity_id": user_id, "new_value": {"user_name": user.get("name"), "user_email": user.get("email")},
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"message": f"Password reset for {user['name']} ({user['email']})"}
