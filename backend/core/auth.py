"""Authentication utilities"""
import os
import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.database import users_col

JWT_SECRET = os.environ.get("JWT_SECRET", "leamss-portal-secret-key-2024-secure")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_hours: int = 24) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def build_token_payload(user: dict) -> dict:
    """Compact JWT payload including RBAC fields for fast permission checks."""
    return {
        "sub": user["id"],
        "role": user.get("role"),                              # legacy — preserved
        "rbac_role": user.get("rbac_role") or user.get("role"), # new RBAC key
        "user_type": user.get("user_type"),
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
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(allowed_roles: list):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in [r.value if hasattr(r, 'value') else r for r in allowed_roles] and current_user["role"] not in [str(r) for r in allowed_roles]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker
