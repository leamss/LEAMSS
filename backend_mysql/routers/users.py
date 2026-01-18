"""
Users Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from core.database import get_db
from core.models import User, UserRole, UserStatus
from core.auth import get_current_user, require_role, get_password_hash
from core.schemas import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[dict])
async def get_users(
    role: str = None,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get all users (Admin only)"""
    query = select(User)
    
    if role:
        query = query.where(User.role == UserRole(role))
    
    result = await db.execute(query.order_by(User.created_at.desc()))
    users = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role.value,
            "mobile": u.mobile,
            "status": u.status.value,
            "commission_rate": u.commission_rate,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]


@router.get("/by-role/{role}", response_model=List[dict])
async def get_users_by_role(
    role: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get users by role"""
    result = await db.execute(
        select(User)
        .where(User.role == UserRole(role))
        .where(User.status == UserStatus.active)
    )
    users = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role.value
        }
        for u in users
    ]


@router.get("/ticket-recipients", response_model=List[dict])
async def get_ticket_recipients(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get potential ticket recipients based on current user's role"""
    user_role = current_user["role"]
    
    # Define which roles can receive tickets from which roles
    if user_role == "admin":
        target_roles = [UserRole.admin, UserRole.case_manager, UserRole.partner, UserRole.client]
    elif user_role == "case_manager":
        target_roles = [UserRole.admin, UserRole.case_manager, UserRole.client]
    elif user_role == "partner":
        target_roles = [UserRole.admin, UserRole.case_manager]
    else:  # client
        target_roles = [UserRole.admin, UserRole.case_manager]
    
    result = await db.execute(
        select(User)
        .where(User.role.in_(target_roles))
        .where(User.status == UserStatus.active)
        .where(User.id != current_user["id"])
    )
    users = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role.value
        }
        for u in users
    ]


@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "mobile": user.mobile,
        "status": user.status.value,
        "commission_rate": user.commission_rate,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


@router.post("", response_model=dict)
async def create_user(
    request: UserCreate,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user (Admin only)"""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = User(
        email=request.email,
        password=get_password_hash(request.password),
        name=request.name,
        role=UserRole(request.role),
        mobile=request.mobile,
        status=UserStatus.active,
        commission_rate=request.commission_rate or 0.0
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "mobile": user.mobile,
        "status": user.status.value,
        "commission_rate": user.commission_rate,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


@router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    request: UserUpdate,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Update a user (Admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if request.name is not None:
        user.name = request.name
    if request.mobile is not None:
        user.mobile = request.mobile
    if request.status is not None:
        user.status = UserStatus(request.status)
    if request.commission_rate is not None:
        user.commission_rate = request.commission_rate
    
    await db.commit()
    await db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "mobile": user.mobile,
        "status": user.status.value,
        "commission_rate": user.commission_rate,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (Admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}
