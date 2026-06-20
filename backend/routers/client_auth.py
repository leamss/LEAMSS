"""Step 2 W1 — Client Authentication.

Separate JWT session for clients (distinct from staff `/api/auth/login`).
Uses bcrypt hash stored on client_mini_portals. Plain `temp_password` field
remains for sales-rep display + first-time login; on first login it's auto-
hashed into `password_hash` for subsequent attempts.

Endpoints:
  POST   /api/client-auth/login              {email, password} → client JWT
  POST   /api/client-auth/logout             204 (client invalidates locally)
  POST   /api/client-auth/forgot-password    {email} → reset token logged (email preview)
  POST   /api/client-auth/reset-password     {token, new_password}
  POST   /api/client-auth/change-password    {current, new}  — requires client JWT
  GET    /api/client-auth/me                 — current client info

JWT claim: {user_type: "client", client_id: uuid, email, name}
"""
from __future__ import annotations

import logging
import os
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from core.auth import (JWT_SECRET, get_password_hash, validate_password_strength,
                        verify_password)
from core.database import db
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/client-auth", tags=["Step 2 Client Auth"])
_security = HTTPBearer(auto_error=False)

PORTAL_COLL = "client_mini_portals"
RESET_COLL = "client_password_resets"
LOGIN_AUDIT_COLL = "client_login_audit"


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class ClientLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=80)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# ── JWT helpers ───────────────────────────────────────────────────────────────
def _make_client_token(portal: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": portal["client_id"],
        "user_type": "client",
        "client_id": portal["client_id"],
        "email": portal.get("client_email"),
        "name": portal.get("client_name"),
        "portal_id": portal.get("id"),
        "iat": int(now.timestamp()),
        "exp": now + timedelta(hours=12),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def get_current_client(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(401, "Client authentication required")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired — please login again")
    except jwt.DecodeError:
        raise HTTPException(401, "Invalid client token")
    if payload.get("user_type") != "client":
        raise HTTPException(403, "Not a client token (staff tokens cannot use this scope)")
    client_id = payload.get("client_id") or payload.get("sub")
    portal = await db[PORTAL_COLL].find_one({"client_id": client_id})
    if not portal:
        raise HTTPException(401, "Client portal no longer exists")
    if portal.get("locked"):
        raise HTTPException(403, "Account locked — please contact LEAMSS")
    portal.pop("_id", None)
    return {**payload, "portal": portal}


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/login")
async def client_login(body: ClientLoginIn, request: Request):
    email = body.email.lower()
    portal = await db[PORTAL_COLL].find_one({"client_email": email})
    ip = request.client.host if request.client else "unknown"

    async def _audit(status: str, portal_id: Optional[str] = None):
        await db[LOGIN_AUDIT_COLL].insert_one({
            "email": email, "ip": ip, "status": status,
            "portal_id": portal_id, "ua": request.headers.get("user-agent", ""),
            "at": datetime.now(timezone.utc),
        })

    if not portal:
        await _audit("unknown_email")
        raise HTTPException(401, "Invalid email or password")
    if portal.get("locked"):
        await _audit("locked", portal.get("id"))
        raise HTTPException(403, "Your account is locked. Please contact LEAMSS.")

    pwd_hash = portal.get("password_hash")
    temp_pwd = portal.get("temp_password")

    ok = False
    if pwd_hash:
        try:
            ok = verify_password(body.password, pwd_hash)
        except Exception:
            ok = False
    if not ok and temp_pwd and body.password == temp_pwd:
        # First-time login with temp password — auto-hash for next time
        ok = True
        await db[PORTAL_COLL].update_one(
            {"id": portal["id"]},
            {"$set": {"password_hash": get_password_hash(body.password),
                      "last_login_at": datetime.now(timezone.utc)}},
        )

    if not ok:
        await _audit("bad_password", portal.get("id"))
        raise HTTPException(401, "Invalid email or password")

    await db[PORTAL_COLL].update_one(
        {"id": portal["id"]},
        {"$set": {"last_login_at": datetime.now(timezone.utc),
                  "last_login_ip": ip}},
    )
    await _audit("ok", portal.get("id"))
    token = _make_client_token(portal)
    return {
        "ok": True,
        "token": token,
        "client": {
            "client_id": portal["client_id"],
            "name": portal.get("client_name"),
            "email": portal.get("client_email"),
            "product_id": portal.get("product_id"),
            "must_change_password": bool(portal.get("password_must_change")),
        },
    }


@router.post("/logout")
async def client_logout(client: Dict[str, Any] = Depends(get_current_client)):
    # JWT is stateless; client discards token. We log it for audit purposes.
    await log_action(db, action="client.logout", user_id=client["client_id"],
                     severity="info", summary={"portal_id": client.get("portal_id")})
    return {"ok": True}


@router.post("/forgot-password")
async def client_forgot_password(body: ForgotIn, request: Request):
    """Always returns 200 to prevent email enumeration. Token is logged."""
    portal = await db[PORTAL_COLL].find_one({"client_email": body.email.lower()})
    if portal:
        token = secrets.token_urlsafe(32)
        await db[RESET_COLL].insert_one({
            "token": token,
            "client_id": portal["client_id"],
            "email": portal["client_email"],
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
            "used": False,
            "ip": request.client.host if request.client else "unknown",
        })
        # Email preview (Resend API key pending)
        public_base = os.environ.get("PUBLIC_SITE_URL", "https://app.leamss.com")
        reset_link = f"{public_base}/client-portal/reset?token={token}"
        logger.info(f"[Step2 ClientAuth] Password reset link for {body.email}: {reset_link}")
    return {"ok": True, "message": "If an account exists, a reset link has been sent."}


@router.post("/reset-password")
async def client_reset_password(body: ResetIn):
    ok, msg = validate_password_strength(body.new_password)
    if not ok:
        raise HTTPException(400, msg)

    reset = await db[RESET_COLL].find_one({"token": body.token, "used": False})
    if not reset:
        raise HTTPException(400, "Invalid or already-used token")
    exp = reset.get("expires_at")
    if isinstance(exp, datetime):
        exp_aware = exp.replace(tzinfo=timezone.utc) if exp.tzinfo is None else exp
        if exp_aware < datetime.now(timezone.utc):
            raise HTTPException(400, "Reset token expired")

    await db[PORTAL_COLL].update_one(
        {"client_id": reset["client_id"]},
        {"$set": {"password_hash": get_password_hash(body.new_password),
                  "password_must_change": False,
                  "password_reset_at": datetime.now(timezone.utc),
                  "password_reset_via": "self_service_token"}},
    )
    await db[RESET_COLL].update_one(
        {"token": body.token}, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}}
    )
    await log_action(db, action="client.password_reset",
                     user_id=reset["client_id"], severity="info",
                     summary={"via": "self_service_token"})
    return {"ok": True, "message": "Password updated. Please login with your new password."}


@router.post("/change-password")
async def client_change_password(
    body: ChangePasswordIn,
    client: Dict[str, Any] = Depends(get_current_client),
):
    portal = client["portal"]
    pwd_hash = portal.get("password_hash")
    temp = portal.get("temp_password")

    ok = False
    if pwd_hash:
        try: ok = verify_password(body.current_password, pwd_hash)
        except Exception: ok = False
    if not ok and temp and body.current_password == temp:
        ok = True
    if not ok:
        raise HTTPException(400, "Current password is incorrect")

    valid, msg = validate_password_strength(body.new_password)
    if not valid:
        raise HTTPException(400, msg)

    await db[PORTAL_COLL].update_one(
        {"id": portal["id"]},
        {"$set": {"password_hash": get_password_hash(body.new_password),
                  "password_must_change": False,
                  "password_changed_at": datetime.now(timezone.utc),
                  "password_changed_by": "client_self"}},
    )
    await log_action(db, action="client.password_change",
                     user_id=client["client_id"], severity="info",
                     summary={"via": "self_service"})
    return {"ok": True, "message": "Password updated successfully."}


@router.get("/me")
async def client_me(client: Dict[str, Any] = Depends(get_current_client)):
    p = client["portal"]
    return {
        "client_id": p["client_id"],
        "name": p.get("client_name"),
        "email": p.get("client_email"),
        "phone": p.get("client_phone"),
        "product_id": p.get("product_id"),
        "info_sheet_id": p.get("info_sheet_id"),
        "status": p.get("status"),
        "locked": bool(p.get("locked")),
        "must_change_password": bool(p.get("password_must_change")),
        "created_at": p.get("created_at").isoformat() if isinstance(p.get("created_at"), datetime) else p.get("created_at"),
        "last_login_at": p.get("last_login_at").isoformat() if isinstance(p.get("last_login_at"), datetime) else p.get("last_login_at"),
    }
