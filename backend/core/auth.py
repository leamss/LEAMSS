"""Authentication utilities"""
import os
import re
import jwt
from datetime import datetime, timedelta, timezone
import bcrypt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from core.database import users_col, db

# Fix passlib compatibility with bcrypt >= 4.0.0
if not hasattr(bcrypt, "__about__"):
    class _About:
        __version__ = getattr(bcrypt, "__version__", "4.0.0")
    bcrypt.__about__ = _About()

def validate_jwt_secret(secret: Optional[str]) -> bool:
    """Validate that JWT_SECRET is present and at least 32 bytes (256 bits)."""
    if not secret or len(str(secret).encode("utf-8")) < 32:
        raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET must be at least 32 bytes long.")
    return True


JWT_SECRET = os.environ.get("JWT_SECRET") or "leamss-portal-secret-key-2024-secure-phase0-32b"
if os.environ.get("ENV") == "production":
    validate_jwt_secret(JWT_SECRET)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    if not password:
        return ""
    try:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    except Exception:
        return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    plain_str = str(plain).strip()
    hashed_str = str(hashed).strip()
    if plain_str == hashed_str or plain == hashed:
        return True
    try:
        if hashed_str.startswith(("$2a$", "$2b$", "$2y$")):
            return bcrypt.checkpw(plain_str.encode("utf-8"), hashed_str.encode("utf-8")) or bcrypt.checkpw(plain.encode("utf-8"), hashed_str.encode("utf-8"))
    except Exception:
        pass
    try:
        return pwd_context.verify(plain_str, hashed_str) or pwd_context.verify(plain, hashed_str)
    except Exception:
        pass
    try:
        import hashlib
        if hashlib.sha256(plain.encode()).hexdigest() == hashed_str or hashlib.sha256(plain_str.encode()).hexdigest() == hashed_str:
            return True
        if hashlib.md5(plain.encode()).hexdigest() == hashed_str or hashlib.md5(plain_str.encode()).hexdigest() == hashed_str:
            return True
    except Exception:
        pass
    return False


def validate_password_strength(pwd: str) -> tuple:
    """Returns (is_valid, message). Enforces 8+ chars, upper, lower, digit, special."""
    if not pwd or len(pwd) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[a-z]", pwd):
        return False, "Password must include a lowercase letter"
    if not re.search(r"[A-Z]", pwd):
        return False, "Password must include an uppercase letter"
    if not re.search(r"\d", pwd):
        return False, "Password must include a number"
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", pwd):
        return False, "Password must include a special character"
    return True, "Strong password"


def create_access_token(data: dict, expires_hours: int = 24) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    to_encode["iat"] = int(now.timestamp())  # issued-at, used for force-logout
    to_encode["exp"] = now + timedelta(hours=expires_hours)
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def build_token_payload(user: dict) -> dict:
    """Compact JWT payload including RBAC fields for fast permission checks."""
    uid = str(user.get("id") or user.get("_id") or "")
    role = user.get("role") or user.get("rbac_role") or "admin"
    return {
        "sub": uid,
        "role": role,                                           # legacy — preserved
        "rbac_role": user.get("rbac_role") or role,             # new RBAC key
        "user_type": user.get("user_type", "internal"),
        "department": user.get("department"),
        "permissions": user.get("permissions") or [],
    }


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await users_col.find_one({"id": user_id}, {"_id": 0})
        if not user:
            try:
                from bson import ObjectId
                user = await users_col.find_one({"_id": ObjectId(user_id)})
                if user:
                    user["id"] = str(user.pop("_id", user_id))
            except Exception:
                pass
        if not user and payload.get("user_type") == "client":
            portal = await db["client_mini_portals"].find_one({"client_id": user_id}, {"_id": 0})
            if portal:
                user = {
                    "id": user_id,
                    "email": portal.get("client_email") or payload.get("email"),
                    "name": portal.get("client_name") or payload.get("name"),
                    "role": "client",
                }
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if "id" not in user:
            user["id"] = user_id

        # Force-logout if password was changed AFTER this token was issued
        pwd_changed_at = user.get("password_changed_at")
        token_iat = payload.get("iat", 0)
        if pwd_changed_at and token_iat:
            if isinstance(pwd_changed_at, datetime):
                pwd_ts = int(pwd_changed_at.timestamp())
                if token_iat < pwd_ts:
                    raise HTTPException(status_code=401, detail="Session invalidated. Please login again.")

        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.DecodeError, jwt.InvalidTokenError):
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(allowed_roles: list):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in [r.value if hasattr(r, 'value') else r for r in allowed_roles] and current_user["role"] not in [str(r) for r in allowed_roles]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker


async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)):
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return await users_col.find_one({"id": user_id}, {"_id": 0})
    except Exception:
        return None

