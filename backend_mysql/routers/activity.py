"""
Activity Log Router for LEAMSS Portal (MySQL)
Audit trail and activity tracking
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta
from core.database import get_db
from core.models import AuditLog, User, UserRole
from core.auth import get_current_user, require_role
from pydantic import BaseModel

router = APIRouter(prefix="/activity", tags=["Activity Log"])


class ActivityLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    user_name: Optional[str]
    user_email: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[str]
    old_value: Optional[dict]
    new_value: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


async def log_activity(
    db: AsyncSession,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str = None,
    old_value: dict = None,
    new_value: dict = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Helper function to log activity"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(log)
    await db.commit()
    return log


@router.get("/logs", response_model=List[dict])
async def get_activity_logs(
    entity_type: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get activity logs with filtering (Admin only)"""
    query = select(AuditLog).order_by(desc(AuditLog.created_at))
    
    # Apply filters
    filters = []
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if action:
        filters.append(AuditLog.action.contains(action))
    if start_date:
        filters.append(AuditLog.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        filters.append(AuditLog.created_at <= datetime.fromisoformat(end_date))
    
    if filters:
        query = query.where(and_(*filters))
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Get user names
    user_ids = set(log.user_id for log in logs if log.user_id)
    user_map = {}
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        for user in users_result.scalars().all():
            user_map[user.id] = {"name": user.name, "email": user.email}
    
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": user_map.get(log.user_id, {}).get("name"),
            "user_email": user_map.get(log.user_id, {}).get("email"),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]


@router.get("/stats", response_model=dict)
async def get_activity_stats(
    days: int = 7,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get activity statistics for dashboard"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total activities
    total_result = await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.created_at >= start_date)
    )
    total_activities = total_result.scalar()
    
    # Activities by type
    by_type_result = await db.execute(
        select(AuditLog.entity_type, func.count(AuditLog.id))
        .where(AuditLog.created_at >= start_date)
        .group_by(AuditLog.entity_type)
    )
    activities_by_type = {row[0]: row[1] for row in by_type_result.all()}
    
    # Activities by action
    by_action_result = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .where(AuditLog.created_at >= start_date)
        .group_by(AuditLog.action)
        .order_by(desc(func.count(AuditLog.id)))
        .limit(10)
    )
    top_actions = [{"action": row[0], "count": row[1]} for row in by_action_result.all()]
    
    # Most active users
    by_user_result = await db.execute(
        select(AuditLog.user_id, func.count(AuditLog.id))
        .where(AuditLog.created_at >= start_date)
        .where(AuditLog.user_id.isnot(None))
        .group_by(AuditLog.user_id)
        .order_by(desc(func.count(AuditLog.id)))
        .limit(5)
    )
    user_activities = by_user_result.all()
    
    # Get user names for most active
    user_ids = [row[0] for row in user_activities]
    user_map = {}
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        for user in users_result.scalars().all():
            user_map[user.id] = user.name
    
    most_active_users = [
        {"user_id": row[0], "user_name": user_map.get(row[0], "Unknown"), "count": row[1]}
        for row in user_activities
    ]
    
    # Daily activity trend
    daily_result = await db.execute(
        select(
            func.date(AuditLog.created_at).label("date"),
            func.count(AuditLog.id)
        )
        .where(AuditLog.created_at >= start_date)
        .group_by(func.date(AuditLog.created_at))
        .order_by(func.date(AuditLog.created_at))
    )
    daily_trend = [
        {"date": str(row[0]), "count": row[1]}
        for row in daily_result.all()
    ]
    
    return {
        "total_activities": total_activities,
        "activities_by_type": activities_by_type,
        "top_actions": top_actions,
        "most_active_users": most_active_users,
        "daily_trend": daily_trend,
        "period_days": days
    }


@router.get("/entity/{entity_type}/{entity_id}", response_model=List[dict])
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activity history for a specific entity"""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type)
        .where(AuditLog.entity_id == entity_id)
        .order_by(desc(AuditLog.created_at))
        .limit(100)
    )
    logs = result.scalars().all()
    
    # Get user names
    user_ids = set(log.user_id for log in logs if log.user_id)
    user_map = {}
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        for user in users_result.scalars().all():
            user_map[user.id] = user.name
    
    return [
        {
            "id": log.id,
            "user_name": user_map.get(log.user_id, "System"),
            "action": log.action,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]
