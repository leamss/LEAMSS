"""
Authentication routes for LEAMSS Portal
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from bson import ObjectId

from core.database import db
from core.auth import pwd_context, create_access_token, UserRole
from core.models import UserCreate, UserResponse, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    """Register a new user"""
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_doc = {
        "id": str(ObjectId()),
        "email": user.email,
        "name": user.name,
        "mobile": user.mobile,
        "role": user.role,
        "password_hash": pwd_context.hash(user.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    return UserResponse(**user_doc)


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Login and get access token"""
    user = await db.users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Handle both old 'password' and new 'password_hash' field names
    password_field = user.get("password_hash") or user.get("password")
    if not password_field or not pwd_context.verify(credentials.password, password_field):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user["email"]})
    user_response = UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        mobile=user.get("mobile"),
        created_at=user["created_at"]
    )
    return LoginResponse(token=token, user=user_response)
