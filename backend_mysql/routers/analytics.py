"""
Analytics Router for LEAMSS Portal (MySQL)
Dashboard charts and trend data
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from typing import Optional, List
from datetime import datetime, timedelta
from core.database import get_db
from core.models import (
    Sale, SaleStatus, Case, CaseStatus, Ticket, TicketStatus,
    User, UserRole, Document, DocumentStatus
)
from core.auth import get_current_user, require_role

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/sales-trend", response_model=dict)
async def get_sales_trend(
    days: int = 30,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.partner])),
    db: AsyncSession = Depends(get_db)
):
    """Get sales trend over time"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(
        func.date(Sale.created_at).label("date"),
        func.count(Sale.id).label("count"),
        func.sum(Sale.fee_amount).label("total_fee"),
        func.sum(Sale.commission_amount).label("total_commission")
    ).where(Sale.created_at >= start_date)
    
    if current_user["role"] == "partner":
        query = query.where(Sale.partner_id == current_user["id"])
    
    query = query.group_by(func.date(Sale.created_at)).order_by(func.date(Sale.created_at))
    
    result = await db.execute(query)
    data = result.all()
    
    return {
        "labels": [str(row[0]) for row in data],
        "sales_count": [row[1] for row in data],
        "revenue": [float(row[2]) if row[2] else 0 for row in data],
        "commission": [float(row[3]) if row[3] else 0 for row in data],
        "period_days": days
    }


@router.get("/sales-by-status", response_model=dict)
async def get_sales_by_status(
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.partner])),
    db: AsyncSession = Depends(get_db)
):
    """Get sales breakdown by status"""
    query = select(
        Sale.status,
        func.count(Sale.id),
        func.sum(Sale.fee_amount)
    )
    
    if current_user["role"] == "partner":
        query = query.where(Sale.partner_id == current_user["id"])
    
    query = query.group_by(Sale.status)
    
    result = await db.execute(query)
    data = result.all()
    
    return {
        "labels": [row[0].value if row[0] else "unknown" for row in data],
        "counts": [row[1] for row in data],
        "amounts": [float(row[2]) if row[2] else 0 for row in data]
    }


@router.get("/cases-by-status", response_model=dict)
async def get_cases_by_status(
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Get cases breakdown by status"""
    query = select(
        Case.status,
        func.count(Case.id)
    )
    
    if current_user["role"] == "case_manager":
        query = query.where(Case.case_manager_id == current_user["id"])
    
    query = query.group_by(Case.status)
    
    result = await db.execute(query)
    data = result.all()
    
    return {
        "labels": [row[0].value if row[0] else "unknown" for row in data],
        "counts": [row[1] for row in data]
    }


@router.get("/tickets-by-priority", response_model=dict)
async def get_tickets_by_priority(
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Get tickets breakdown by priority"""
    query = select(
        Ticket.priority,
        func.count(Ticket.id)
    ).where(Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress]))
    
    query = query.group_by(Ticket.priority)
    
    result = await db.execute(query)
    data = result.all()
    
    return {
        "labels": [row[0].value if row[0] else "unknown" for row in data],
        "counts": [row[1] for row in data]
    }


@router.get("/monthly-revenue", response_model=dict)
async def get_monthly_revenue(
    year: Optional[int] = None,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get monthly revenue for the year"""
    if not year:
        year = datetime.utcnow().year
    
    result = await db.execute(
        select(
            extract('month', Sale.approved_at).label("month"),
            func.sum(Sale.fee_amount).label("revenue"),
            func.sum(Sale.commission_amount).label("commission")
        )
        .where(Sale.status == SaleStatus.approved)
        .where(extract('year', Sale.approved_at) == year)
        .group_by(extract('month', Sale.approved_at))
        .order_by(extract('month', Sale.approved_at))
    )
    data = result.all()
    
    # Fill in missing months
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    revenue_by_month = {int(row[0]): float(row[1]) if row[1] else 0 for row in data}
    commission_by_month = {int(row[0]): float(row[2]) if row[2] else 0 for row in data}
    
    return {
        "labels": months,
        "revenue": [revenue_by_month.get(i+1, 0) for i in range(12)],
        "commission": [commission_by_month.get(i+1, 0) for i in range(12)],
        "year": year
    }


@router.get("/top-products", response_model=List[dict])
async def get_top_products(
    limit: int = 5,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get top selling products"""
    from core.models import Product
    
    result = await db.execute(
        select(
            Product.id,
            Product.name,
            func.count(Sale.id).label("sales_count"),
            func.sum(Sale.fee_amount).label("total_revenue")
        )
        .join(Sale, Product.id == Sale.product_id)
        .where(Sale.status == SaleStatus.approved)
        .group_by(Product.id, Product.name)
        .order_by(func.count(Sale.id).desc())
        .limit(limit)
    )
    data = result.all()
    
    return [
        {
            "id": row[0],
            "name": row[1],
            "sales_count": row[2],
            "total_revenue": float(row[3]) if row[3] else 0
        }
        for row in data
    ]


@router.get("/top-partners", response_model=List[dict])
async def get_top_partners(
    limit: int = 5,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get top performing partners"""
    result = await db.execute(
        select(
            User.id,
            User.name,
            User.email,
            func.count(Sale.id).label("sales_count"),
            func.sum(Sale.fee_amount).label("total_revenue"),
            func.sum(Sale.commission_amount).label("total_commission")
        )
        .join(Sale, User.id == Sale.partner_id)
        .where(User.role == UserRole.partner)
        .where(Sale.status == SaleStatus.approved)
        .group_by(User.id, User.name, User.email)
        .order_by(func.sum(Sale.fee_amount).desc())
        .limit(limit)
    )
    data = result.all()
    
    return [
        {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "sales_count": row[3],
            "total_revenue": float(row[4]) if row[4] else 0,
            "total_commission": float(row[5]) if row[5] else 0
        }
        for row in data
    ]


@router.get("/document-status", response_model=dict)
async def get_document_status_breakdown(
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Get document status breakdown"""
    query = select(
        Document.status,
        func.count(Document.id)
    )
    
    if current_user["role"] == "case_manager":
        query = query.join(Case, Document.case_id == Case.id).where(
            Case.case_manager_id == current_user["id"]
        )
    
    query = query.group_by(Document.status)
    
    result = await db.execute(query)
    data = result.all()
    
    return {
        "labels": [row[0].value if row[0] else "unknown" for row in data],
        "counts": [row[1] for row in data]
    }


@router.get("/case-completion-rate", response_model=dict)
async def get_case_completion_rate(
    days: int = 90,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get case completion statistics"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total cases created in period
    total_result = await db.execute(
        select(func.count(Case.id))
        .where(Case.created_at >= start_date)
    )
    total_cases = total_result.scalar() or 0
    
    # Completed cases
    completed_result = await db.execute(
        select(func.count(Case.id))
        .where(Case.created_at >= start_date)
        .where(Case.status == CaseStatus.completed)
    )
    completed_cases = completed_result.scalar() or 0
    
    # Average completion time (for completed cases)
    avg_time_result = await db.execute(
        select(func.avg(func.datediff(Case.completed_at, Case.created_at)))
        .where(Case.status == CaseStatus.completed)
        .where(Case.completed_at.isnot(None))
    )
    avg_days = avg_time_result.scalar()
    
    return {
        "total_cases": total_cases,
        "completed_cases": completed_cases,
        "completion_rate": round(completed_cases / total_cases * 100, 1) if total_cases > 0 else 0,
        "average_completion_days": round(float(avg_days), 1) if avg_days else None,
        "period_days": days
    }


@router.get("/user-activity", response_model=List[dict])
async def get_user_activity_summary(
    days: int = 7,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get user activity summary"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get users with their activity counts
    result = await db.execute(
        select(User)
        .where(User.status == "active")
        .order_by(User.role)
    )
    users = result.scalars().all()
    
    activity_data = []
    for user in users:
        # Count tickets created
        tickets_result = await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.created_by == user.id)
            .where(Ticket.created_at >= start_date)
        )
        tickets_count = tickets_result.scalar() or 0
        
        # Count sales (for partners)
        sales_count = 0
        if user.role == UserRole.partner:
            sales_result = await db.execute(
                select(func.count(Sale.id))
                .where(Sale.partner_id == user.id)
                .where(Sale.created_at >= start_date)
            )
            sales_count = sales_result.scalar() or 0
        
        activity_data.append({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role.value,
            "tickets_created": tickets_count,
            "sales_created": sales_count
        })
    
    return activity_data
