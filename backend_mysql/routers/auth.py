"""
Authentication Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.models import User, UserRole, UserStatus
from core.auth import verify_password, get_password_hash, create_access_token, get_current_user
from core.schemas import LoginRequest, LoginResponse, UserCreate, UserResponse
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and get JWT token"""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )
    
    token = create_access_token({"sub": user.id, "role": user.role.value})
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "mobile": user.mobile,
            "status": user.status.value,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    }


@router.post("/register", response_model=UserResponse)
async def register(request: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user (typically for clients)"""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=request.email,
        password=get_password_hash(request.password),
        name=request.name,
        role=UserRole(request.role) if request.role in [r.value for r in UserRole] else UserRole.client,
        mobile=request.mobile,
        status=UserStatus.active,
        commission_rate=request.commission_rate or 0.0
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        mobile=user.mobile,
        status=user.status.value,
        commission_rate=user.commission_rate,
        created_at=user.created_at
    )


@router.get("/me", response_model=dict)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current logged-in user info"""
    return current_user


@router.post("/impersonate/{user_id}")
async def impersonate_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin impersonation - switch to another user's account"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user.status != UserStatus.active:
        raise HTTPException(status_code=400, detail="User account is not active")
    
    token = create_access_token({"sub": target_user.id, "role": target_user.role.value})
    
    return {
        "token": token,
        "user": {
            "id": target_user.id,
            "email": target_user.email,
            "name": target_user.name,
            "role": target_user.role.value,
            "mobile": target_user.mobile,
            "status": target_user.status.value,
            "created_at": target_user.created_at.isoformat() if target_user.created_at else None
        }
    }


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    result = await db.execute(select(User).where(User.id == current_user["id"]))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    
    user.password = get_password_hash(new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}
