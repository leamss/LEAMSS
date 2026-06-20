"""Auth Router"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
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
    # X3: delegate to centralised audit_service.log_legacy_event
    from services.audit_service import log_legacy_event
    from core.database import db as _db
    await log_legacy_event(_db, user_id, action, entity_type, entity_id, details)


@router.post("/login")
async def login(request: LoginRequest):
    user = await users_col.find_one({"email": request.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get("status") != "active":
        raise HTTPException(status_code=401, detail="Account is inactive")
    
    token = create_access_token(build_token_payload(user))
    
    await _log(user["id"], "login", "user", user["id"], {"role": user["role"], "email": user["email"]})
    
    return {
        "token": token,
        "user": {
            "id": user["id"], "email": user["email"], "name": user["name"],
            "role": user["role"], "mobile": user.get("mobile", ""),
            "status": user["status"],
            "rbac_role": user.get("rbac_role"),
            "user_type": user.get("user_type"),
            "department": user.get("department"),
            "permissions": user.get("permissions", []),
            "ui_modules": user.get("ui_modules", []),
            "employee_id": user.get("employee_id"),
            "partner_code": user.get("partner_code"),
            "two_fa_enabled": user.get("two_fa_enabled", False),
            "must_change_password_on_next_login": user.get("must_change_password_on_next_login", False),
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
    """Admin-only — issues a JWT for the target user so the admin can view their dashboard.
    The frontend stashes the admin's original token in localStorage as `admin_token` and
    shows a yellow banner with a 'Return to Admin' button (handled by AdminReturnBanner).
    Every switch is logged to audit_logs for compliance.
    """
    # Admin-only gate (legacy role check + rbac_role fallback)
    is_admin = current_user.get("role") == "admin" or current_user.get("rbac_role") in ("admin_owner", "admin")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Only admin can impersonate other users")

    # Block self-impersonation (no-op)
    if user_id == current_user.get("id"):
        raise HTTPException(status_code=400, detail="Cannot impersonate yourself")

    target = await users_col.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.get("status") != "active":
        raise HTTPException(status_code=400, detail="Cannot impersonate an inactive user")

    # Issue JWT for target user (same flow as /login)
    token = create_access_token(build_token_payload(target))

    # Audit log — captures admin id + target id for compliance
    await _log(
        current_user["id"],
        "impersonate_user",
        "user",
        target["id"],
        {
            "admin_email": current_user.get("email"),
            "target_email": target.get("email"),
            "target_role": target.get("role"),
            "target_rbac_role": target.get("rbac_role"),
        },
    )

    return {
        "token": token,
        "user": {
            "id": target["id"], "email": target["email"], "name": target["name"],
            "role": target["role"], "mobile": target.get("mobile", ""),
            "status": target.get("status"),
            "rbac_role": target.get("rbac_role"),
            "user_type": target.get("user_type"),
            "department": target.get("department"),
            "permissions": target.get("permissions", []),
            "ui_modules": target.get("ui_modules", []),
            "employee_id": target.get("employee_id"),
            "partner_code": target.get("partner_code"),
            "two_fa_enabled": target.get("two_fa_enabled", False),
        },
        "impersonated_by": {
            "id": current_user["id"],
            "email": current_user.get("email"),
            "name": current_user.get("name"),
        },
    }


@router.post("/change-password")
async def change_password(data: dict, current_user: dict = Depends(get_current_user)):
    """User-initiated password change. Validates strength, enforces force-logout on other sessions."""
    if not verify_password(data.get("current_password", ""), current_user.get("password", "")):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    new_pwd = data.get("new_password", "")
    confirm = data.get("confirm_password", "")
    if new_pwd != confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Strength validation
    from core.auth import validate_password_strength
    ok, msg = validate_password_strength(new_pwd)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    # Reject if same as current
    if verify_password(new_pwd, current_user.get("password", "")):
        raise HTTPException(status_code=400, detail="New password must differ from current")

    # Reject if matches last 3 (password history)
    history = current_user.get("password_history", [])
    for old_hash in history[-3:]:
        if verify_password(new_pwd, old_hash):
            raise HTTPException(status_code=400, detail="Cannot reuse any of your last 3 passwords")

    new_hash = get_password_hash(new_pwd)
    new_history = (history + [current_user.get("password")])[-3:]

    await users_col.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "password": new_hash,
            "password_changed_at": datetime.now(timezone.utc),
            "must_change_password_on_next_login": False,
            "password_history": new_history,
            "last_password_change": datetime.now(timezone.utc),
        }}
    )
    await _log(current_user["id"], "password_changed_self", "user", current_user["id"], {})
    return {"message": "Password changed successfully. Other sessions have been logged out."}


@router.post("/forgot-password")
async def forgot_password(data: dict):
    """Public — request a reset link. Always returns success (no email enumeration)."""
    import uuid
    from core.database import db
    magic_col = db["magic_links"]

    email = (data.get("email") or "").strip().lower()
    if not email:
        return {"message": "If an account exists, reset instructions sent."}

    user = await users_col.find_one({"email": email}, {"_id": 0, "id": 1, "name": 1, "email": 1})
    if user:
        token = str(uuid.uuid4())
        await magic_col.insert_one({
            "id": str(uuid.uuid4()),
            "token": token,
            "user_id": user["id"],
            "purpose": "password_reset",
            "used": False,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=72),
            "created_at": datetime.now(timezone.utc),
        })
        # ACTIVATE EMAIL WHEN RESEND LIVE
        reset_url = f"/reset-password?token={token}"
        print(f"[PASSWORD RESET LINK for {email}] → {reset_url} (Resend MOCKED — share manually for now)")
        await _log(user["id"], "password_reset_requested", "user", user["id"], {"email": email})

    return {"message": "If an account exists, reset instructions sent."}


@router.post("/reset-password-with-token")
async def reset_password_with_token(data: dict):
    """Public — set new password using a valid reset token."""
    from core.database import db
    magic_col = db["magic_links"]

    token = data.get("token", "")
    new_pwd = data.get("new_password", "")
    confirm = data.get("confirm_password", "")
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
    if new_pwd != confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    from core.auth import validate_password_strength
    ok, msg = validate_password_strength(new_pwd)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    link = await magic_col.find_one({"token": token, "purpose": "password_reset"}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if link.get("used"):
        raise HTTPException(status_code=400, detail="This reset link has already been used")
    expires_at = link.get("expires_at")
    if expires_at and isinstance(expires_at, datetime):
        if datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at:
            raise HTTPException(status_code=400, detail="This reset link has expired")

    user = await users_col.find_one({"id": link["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    new_hash = get_password_hash(new_pwd)
    history = user.get("password_history", [])
    new_history = (history + [user.get("password")])[-3:]

    await users_col.update_one(
        {"id": user["id"]},
        {"$set": {
            "password": new_hash,
            "password_changed_at": datetime.now(timezone.utc),
            "must_change_password_on_next_login": False,
            "password_history": new_history,
            "last_password_change": datetime.now(timezone.utc),
        }}
    )
    await magic_col.update_one({"token": token}, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}})
    await _log(user["id"], "password_reset_via_token", "user", user["id"], {})
    return {"message": "Password reset successful. Please login with your new password."}



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
