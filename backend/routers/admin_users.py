"""Admin Users Router — admin-only operations on user accounts.

Provides:
- Dashboard preview (read-only "view as user")
- Enhanced password reset with multiple delivery modes
"""
import uuid
import secrets
import string
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal

from core.database import db, users_col
from core.auth import get_password_hash, validate_password_strength
from core.rbac.dependencies import require_any_permission

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])

activity_log_col = db["activity_log"]
notifications_col = db["notifications"]
magic_links_col = db["magic_links"]
roles_col = db["roles"]
departments_col = db["departments"]


def _gen_password(length: int = 12) -> str:
    """Generate a strong password matching strength rules."""
    while True:
        pwd = "".join(secrets.choice(string.ascii_letters + string.digits + "!@#$%&*") for _ in range(length))
        ok, _ = validate_password_strength(pwd)
        if ok:
            return pwd


# ────────────────────────────────────────────────────────────
# Models
# ────────────────────────────────────────────────────────────
class ResetPasswordRequest(BaseModel):
    delivery: Literal["show_once", "email", "magic_link"] = "show_once"
    reason: str  # required, min 10 chars


# ────────────────────────────────────────────────────────────
# Dashboard Preview (read-only "View Dashboard As User")
# ────────────────────────────────────────────────────────────
@router.get("/{user_id}/dashboard-preview")
async def dashboard_preview(
    user_id: str,
    current_user: dict = Depends(require_any_permission("system.update.any", "employee.view.all", "user.view.all")),
):
    """Returns the target user's dashboard configuration for a read-only preview.

    NO session token issued. NO auth changes. Pure data peek.
    Every preview action is logged for audit.
    """
    target = await users_col.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Resolve role doc for name/description
    role_doc = None
    if target.get("rbac_role"):
        role_doc = await roles_col.find_one({"key": target["rbac_role"]}, {"_id": 0})

    # Resolve dept for theming hint
    dept_doc = None
    if target.get("department"):
        dept_doc = await departments_col.find_one({"key": target["department"]}, {"_id": 0})

    # Real unread notification count for that user
    unread = await db["notifications"].count_documents({"user_id": user_id, "read": False})

    # Mocked module stats — different per user_type for context
    mock_stats = {
        "my_tasks": "—",
        "unread_notifications": unread,
        "attendance_this_month": "—",
        "modules_count": len(target.get("ui_modules", [])),
    }

    # Log the preview action for audit
    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "user",
        "entity_id": user_id,
        "action": "viewed_dashboard_as_user",
        "details": {"target_email": target.get("email"), "target_role": target.get("rbac_role")},
        "created_at": datetime.now(timezone.utc),
    })

    # Strip datetime fields
    if isinstance(target.get("created_at"), datetime):
        target["created_at"] = target["created_at"].isoformat()
    if isinstance(target.get("date_of_joining"), datetime):
        target["date_of_joining"] = target["date_of_joining"].isoformat()

    return {
        "preview_mode": True,
        "viewing_as": {
            "id": target["id"],
            "name": target.get("name"),
            "email": target.get("email"),
            "employee_id": target.get("employee_id"),
            "partner_code": target.get("partner_code"),
            "designation": target.get("designation"),
            "department": target.get("department"),
            "rbac_role": target.get("rbac_role"),
            "user_type": target.get("user_type"),
            "avatar_url": target.get("avatar_url"),
            "employment_status": target.get("employment_status"),
        },
        "ui_modules": target.get("ui_modules", []),
        "permissions": target.get("permissions", []),
        "role_info": {
            "name": role_doc.get("name") if role_doc else target.get("rbac_role"),
            "description": role_doc.get("description") if role_doc else "",
            "hierarchy_level": role_doc.get("hierarchy_level") if role_doc else 0,
        },
        "department_info": {
            "name": dept_doc.get("name") if dept_doc else target.get("department"),
            "color": dept_doc.get("color") if dept_doc else "#475569",
            "icon": dept_doc.get("icon") if dept_doc else "Building2",
        },
        "stats": mock_stats,
        "previewed_by": {
            "id": current_user["id"],
            "name": current_user.get("name"),
        },
        "previewed_at": datetime.now(timezone.utc).isoformat(),
    }


# ────────────────────────────────────────────────────────────
# Enhanced password reset (admin-initiated)
# ────────────────────────────────────────────────────────────
@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    payload: ResetPasswordRequest,
    current_user: dict = Depends(require_any_permission("user.update.any", "employee.update.all", "system.update.any")),
):
    """Admin-initiated password reset with delivery options.

    delivery:
      - show_once: generate password, return once, admin shares manually
      - email: send via Resend (MOCKED — logs to console for now)
      - magic_link: create 72h reset link, return URL for admin to share

    Sets must_change_password_on_next_login = True on the user.
    """
    if not payload.reason or len(payload.reason.strip()) < 10:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 10 characters)")

    target = await users_col.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    response = {
        "delivery": payload.delivery,
        "reason": payload.reason,
        "must_change_on_next_login": True,
    }

    now = datetime.now(timezone.utc)

    if payload.delivery == "show_once":
        new_pwd = _gen_password()
        new_hash = get_password_hash(new_pwd)
        history = target.get("password_history", [])
        new_history = (history + [target.get("password")])[-3:]

        await users_col.update_one(
            {"id": user_id},
            {"$set": {
                "password": new_hash,
                "password_changed_at": now,
                "must_change_password_on_next_login": True,
                "password_history": new_history,
                "last_password_change": now,
            }}
        )
        response["temporary_password"] = new_pwd
        response["message"] = "Password reset. Share with user via secure channel."

    elif payload.delivery == "email":
        new_pwd = _gen_password()
        new_hash = get_password_hash(new_pwd)
        history = target.get("password_history", [])
        new_history = (history + [target.get("password")])[-3:]

        await users_col.update_one(
            {"id": user_id},
            {"$set": {
                "password": new_hash,
                "password_changed_at": now,
                "must_change_password_on_next_login": True,
                "password_history": new_history,
                "last_password_change": now,
            }}
        )
        # ACTIVATE EMAIL WHEN RESEND LIVE
        print(f"[ADMIN PASSWORD RESET via email to {target['email']}] → temp_pwd={new_pwd} (Resend MOCKED)")
        response["email_sent"] = True
        response["message"] = "Password reset email queued (MOCKED — Resend not live)."
        # Also include for visibility while mocked
        response["temporary_password"] = new_pwd

    elif payload.delivery == "magic_link":
        token = str(uuid.uuid4())
        await magic_links_col.insert_one({
            "id": str(uuid.uuid4()),
            "token": token,
            "user_id": user_id,
            "purpose": "password_reset",
            "used": False,
            "expires_at": now + timedelta(hours=72),
            "created_at": now,
            "created_by": current_user["id"],
        })
        # NOTE: don't change password yet; user sets new one via the reset page
        await users_col.update_one(
            {"id": user_id},
            {"$set": {"must_change_password_on_next_login": True}}
        )
        response["reset_url"] = f"/reset-password?token={token}"
        response["expires_in_hours"] = 72
        response["message"] = "Magic link generated. Share the URL with the user."

    # Notify the user
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": "Your password was reset by admin",
        "message": f"Reason: {payload.reason}. Please login with new credentials and update your password.",
        "type": "password_reset",
        "read": False,
        "created_at": now,
    })

    # Audit log
    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "user",
        "entity_id": user_id,
        "action": "password_reset_by_admin",
        "details": {
            "target_email": target.get("email"),
            "delivery": payload.delivery,
            "reason": payload.reason,
        },
        "created_at": now,
    })

    return response
