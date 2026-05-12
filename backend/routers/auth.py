"""Auth Router"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from core.database import users_col, audit_logs_col
from core.auth import verify_password, get_password_hash, create_access_token, get_current_user, build_token_payload
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
    # Build RBAC-aware response while preserving legacy fields for backward compat
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "mobile": current_user.get("mobile", ""),
        "status": current_user.get("status"),
        "avatar_url": current_user.get("avatar_url"),

        # Legacy + RBAC role fields
        "role": current_user.get("role"),                          # legacy preserved
        "rbac_role": current_user.get("rbac_role"),                # new RBAC key
        "user_type": current_user.get("user_type"),
        "department": current_user.get("department"),
        "designation": current_user.get("designation"),
        "permissions": current_user.get("permissions", []),
        "ui_modules": current_user.get("ui_modules", []),

        # Internal employee fields (if applicable)
        "employee_id": current_user.get("employee_id"),
        "date_of_joining": current_user.get("date_of_joining").isoformat() if isinstance(current_user.get("date_of_joining"), datetime) else current_user.get("date_of_joining"),
        "employment_status": current_user.get("employment_status"),
        "employment_type": current_user.get("employment_type"),
        "work_mode": current_user.get("work_mode"),

        # External partner fields (if applicable)
        "partner_code": current_user.get("partner_code"),
        "commission_tier": current_user.get("commission_tier"),
        "commission_rate": current_user.get("commission_rate"),

        # Security
        "two_fa_enabled": current_user.get("two_fa_enabled", False),

        # Profile
        "emergency_contact": current_user.get("emergency_contact"),
        "reports_to": current_user.get("reports_to"),
        "team_id": current_user.get("team_id"),

        "created_at": current_user.get("created_at").isoformat() if isinstance(current_user.get("created_at"), datetime) else current_user.get("created_at"),
    }


@router.post("/impersonate/{user_id}")
async def impersonate_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    target = await users_col.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    token = create_access_token(build_token_payload(target))
    
    return {
        "token": token,
        "user": {
            "id": target["id"], "email": target["email"], "name": target["name"],
            "role": target["role"], "mobile": target.get("mobile", ""),
            "status": target["status"],
            "rbac_role": target.get("rbac_role"),
            "user_type": target.get("user_type"),
            "department": target.get("department"),
            "permissions": target.get("permissions", []),
            "ui_modules": target.get("ui_modules", []),
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



@router.put("/update-profile")
async def update_profile(data: dict, current_user: dict = Depends(get_current_user)):
    """Update current user profile info"""
    allowed = {"name", "mobile", "preferred_language", "notification_preferences"}
    updates = {k: v for k, v in data.items() if k in allowed and v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    updates["updated_at"] = datetime.now(timezone.utc)
    await users_col.update_one({"id": current_user["id"]}, {"$set": updates})
    await _log(current_user["id"], "update_profile", "user", current_user["id"], updates)
    updated = await users_col.find_one({"id": current_user["id"]}, {"_id": 0, "password": 0})
    return {"message": "Profile updated", "user": updated}


@router.get("/notifications-preferences")
async def get_notification_prefs(current_user: dict = Depends(get_current_user)):
    user = await users_col.find_one({"id": current_user["id"]}, {"_id": 0})
    return user.get("notification_preferences", {
        "email": True, "sms": False, "in_app": True,
        "case_updates": True, "payment_reminders": True,
        "document_requests": True, "marketing": False
    })
