"""Auth Router"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from core.database import users_col, audit_logs_col
from core.auth import verify_password, get_password_hash, create_access_token, get_current_user
import uuid

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "client"
    mobile: str = ""


async def _log(user_id, action, entity_type, entity_id=None, details=None):
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "action": action,
        "entity_type": entity_type, "entity_id": entity_id,
        "new_value": details, "created_at": datetime.now(timezone.utc)
    })


@router.post("/login")
async def login(request: LoginRequest):
    user = await users_col.find_one({"email": request.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get("status") != "active":
        raise HTTPException(status_code=401, detail="Account is inactive")
    
    token = create_access_token({"sub": user["id"], "role": user["role"]})
    
    await _log(user["id"], "login", "user", user["id"], {"role": user["role"], "email": user["email"]})
    
    return {
        "token": token,
        "user": {
            "id": user["id"], "email": user["email"], "name": user["name"],
            "role": user["role"], "mobile": user.get("mobile", ""),
            "status": user["status"],
            "created_at": user.get("created_at", "").isoformat() if isinstance(user.get("created_at"), datetime) else str(user.get("created_at", ""))
        }
    }


@router.post("/register")
async def register(request: RegisterRequest):
    existing = await users_col.find_one({"email": request.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = {
        "id": str(uuid.uuid4()), "email": request.email,
        "password": get_password_hash(request.password),
        "name": request.name, "role": request.role,
        "mobile": request.mobile, "status": "active",
        "commission_rate": 0.0,
        "created_at": datetime.now(timezone.utc)
    }
    await users_col.insert_one(user)
    
    token = create_access_token({"sub": user["id"], "role": user["role"]})
    return {
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"], "status": "active"}
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/impersonate/{user_id}")
async def impersonate_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    target = await users_col.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    token = create_access_token({"sub": target["id"], "role": target["role"]})
    
    return {
        "token": token,
        "user": {
            "id": target["id"], "email": target["email"], "name": target["name"],
            "role": target["role"], "mobile": target.get("mobile", ""),
            "status": target["status"],
            "created_at": target.get("created_at", "").isoformat() if isinstance(target.get("created_at"), datetime) else str(target.get("created_at", ""))
        }
    }


@router.post("/change-password")
async def change_password(data: dict, current_user: dict = Depends(get_current_user)):
    if not verify_password(data.get("current_password", ""), current_user.get("password", "")):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    
    await users_col.update_one(
        {"id": current_user["id"]},
        {"$set": {"password": get_password_hash(data["new_password"])}}
    )
    return {"message": "Password changed successfully"}
