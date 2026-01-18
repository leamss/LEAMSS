"""
Reports Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime, timedelta
from core.database import get_db
from core.models import Sale, User, Product, Case, UserRole, SaleStatus
from core.auth import get_current_user, require_role

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/sales", response_model=List[dict])
async def get_sales_report(
    period: str = "all",
    start_date: str = None,
    end_date: str = None,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get sales report (Admin only)"""
    query = select(Sale).options(
        selectinload(Sale.partner),
        selectinload(Sale.product)
    )
    
    # Apply period filter
    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.where(Sale.created_at >= start)
    elif period == "week":
        start = now - timedelta(days=7)
        query = query.where(Sale.created_at >= start)
    elif period == "month":
        start = now - timedelta(days=30)
        query = query.where(Sale.created_at >= start)
    elif period == "quarter":
        start = now - timedelta(days=90)
        query = query.where(Sale.created_at >= start)
    elif period == "year":
        start = now - timedelta(days=365)
        query = query.where(Sale.created_at >= start)
    elif start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            query = query.where(and_(Sale.created_at >= start, Sale.created_at <= end))
        except:
            pass
    
    result = await db.execute(query.order_by(Sale.created_at.desc()))
    sales = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "partner_name": s.partner.name if s.partner else "Unknown",
            "client_name": s.client_name,
            "product_name": s.product.name if s.product else "Unknown",
            "fee_amount": s.fee_amount,
            "amount_received": s.amount_received,
            "status": s.status.value if s.status else "pending",
            "commission_amount": s.commission_amount,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in sales
    ]


@router.get("/commission", response_model=List[dict])
async def get_commission_report(
    period: str = "all",
    start_date: str = None,
    end_date: str = None,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.partner])),
    db: AsyncSession = Depends(get_db)
):
    """Get commission report"""
    query = select(Sale).options(
        selectinload(Sale.partner),
        selectinload(Sale.product)
    ).where(Sale.status == SaleStatus.approved)
    
    # If partner, only show their commissions
    if current_user["role"] == "partner":
        query = query.where(Sale.partner_id == current_user["id"])
    
    # Apply date filters
    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.where(Sale.created_at >= start)
    elif period == "week":
        start = now - timedelta(days=7)
        query = query.where(Sale.created_at >= start)
    elif period == "month":
        start = now - timedelta(days=30)
        query = query.where(Sale.created_at >= start)
    elif period == "quarter":
        start = now - timedelta(days=90)
        query = query.where(Sale.created_at >= start)
    elif period == "year":
        start = now - timedelta(days=365)
        query = query.where(Sale.created_at >= start)
    elif start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            query = query.where(and_(Sale.created_at >= start, Sale.created_at <= end))
        except:
            pass
    
    result = await db.execute(query.order_by(Sale.created_at.desc()))
    sales = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "partner_id": s.partner_id,
            "partner_name": s.partner.name if s.partner else "Unknown",
            "client_name": s.client_name,
            "product_name": s.product.name if s.product else "Unknown",
            "fee_amount": s.fee_amount,
            "commission_rate": s.commission_rate,
            "commission_amount": s.commission_amount,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "approved_at": s.approved_at.isoformat() if s.approved_at else None
        }
        for s in sales
    ]


@router.get("/dashboard-stats", response_model=dict)
async def get_dashboard_stats(
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics (Admin only)"""
    # Total users by role
    users_result = await db.execute(
        select(User.role, func.count(User.id))
        .group_by(User.role)
    )
    users_by_role = {row[0].value: row[1] for row in users_result.all()}
    
    # Total cases
    cases_result = await db.execute(select(func.count(Case.id)))
    total_cases = cases_result.scalar()
    
    # Active cases
    active_cases_result = await db.execute(
        select(func.count(Case.id))
        .where(Case.status.in_(["active", "in_progress"]))
    )
    active_cases = active_cases_result.scalar()
    
    # Total sales
    sales_result = await db.execute(select(func.count(Sale.id)))
    total_sales = sales_result.scalar()
    
    # Total revenue
    revenue_result = await db.execute(
        select(func.sum(Sale.fee_amount))
        .where(Sale.status == SaleStatus.approved)
    )
    total_revenue = revenue_result.scalar() or 0
    
    # Total commission
    commission_result = await db.execute(
        select(func.sum(Sale.commission_amount))
        .where(Sale.status == SaleStatus.approved)
    )
    total_commission = commission_result.scalar() or 0
    
    return {
        "total_users": sum(users_by_role.values()),
        "users_by_role": users_by_role,
        "total_cases": total_cases,
        "active_cases": active_cases,
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_commission": total_commission
    }



@router.get("/partner-commissions", response_model=List[dict])
async def get_partner_commissions(
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get commission summary by partner (Admin only)"""
    result = await db.execute(
        select(
            User.id,
            User.name,
            User.email,
            func.count(Sale.id).label("total_sales"),
            func.sum(Sale.fee_amount).label("total_revenue"),
            func.sum(Sale.commission_amount).label("total_commission")
        )
        .join(Sale, User.id == Sale.partner_id)
        .where(User.role == UserRole.partner)
        .where(Sale.status == SaleStatus.approved)
        .group_by(User.id, User.name, User.email)
        .order_by(func.sum(Sale.commission_amount).desc())
    )
    partners = result.all()
    
    return [
        {
            "partner_id": p.id,
            "partner_name": p.name,
            "partner_email": p.email,
            "total_sales": p.total_sales,
            "total_revenue": float(p.total_revenue) if p.total_revenue else 0,
            "total_commission": float(p.total_commission) if p.total_commission else 0
        }
        for p in partners
    ]
