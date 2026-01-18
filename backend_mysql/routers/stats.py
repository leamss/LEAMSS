"""
Stats Router for LEAMSS Portal (MySQL)
Dashboard statistics and reports
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta
from core.database import get_db
from core.models import (
    Sale, User, Product, Case, Ticket, Document, 
    UserRole, SaleStatus, CaseStatus, TicketStatus, DocumentStatus
)
from core.auth import get_current_user, require_role

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/dashboard", response_model=dict)
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
        .where(Case.status.in_([CaseStatus.active, CaseStatus.in_progress]))
    )
    active_cases = active_cases_result.scalar()
    
    # Total sales
    sales_result = await db.execute(select(func.count(Sale.id)))
    total_sales = sales_result.scalar()
    
    # Pending sales
    pending_sales_result = await db.execute(
        select(func.count(Sale.id)).where(Sale.status == SaleStatus.pending)
    )
    pending_sales = pending_sales_result.scalar()
    
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
    
    # Open tickets
    open_tickets_result = await db.execute(
        select(func.count(Ticket.id))
        .where(Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress]))
    )
    open_tickets = open_tickets_result.scalar()
    
    return {
        "total_users": sum(users_by_role.values()),
        "users_by_role": users_by_role,
        "total_cases": total_cases,
        "active_cases": active_cases,
        "total_sales": total_sales,
        "pending_sales": pending_sales,
        "total_revenue": total_revenue,
        "total_commission": total_commission,
        "open_tickets": open_tickets
    }


@router.get("/partner-dashboard", response_model=dict)
async def get_partner_dashboard_stats(
    current_user: dict = Depends(require_role([UserRole.partner])),
    db: AsyncSession = Depends(get_db)
):
    """Get partner dashboard statistics"""
    partner_id = current_user["id"]
    
    # Total sales
    total_result = await db.execute(
        select(func.count(Sale.id)).where(Sale.partner_id == partner_id)
    )
    total_sales = total_result.scalar()
    
    # Approved sales
    approved_result = await db.execute(
        select(func.count(Sale.id))
        .where(Sale.partner_id == partner_id)
        .where(Sale.status == SaleStatus.approved)
    )
    approved_sales = approved_result.scalar()
    
    # Pending sales
    pending_result = await db.execute(
        select(func.count(Sale.id))
        .where(Sale.partner_id == partner_id)
        .where(Sale.status == SaleStatus.pending)
    )
    pending_sales = pending_result.scalar()
    
    # Total commission
    commission_result = await db.execute(
        select(func.sum(Sale.commission_amount))
        .where(Sale.partner_id == partner_id)
        .where(Sale.status == SaleStatus.approved)
    )
    total_commission = commission_result.scalar() or 0
    
    # Active cases
    cases_result = await db.execute(
        select(func.count(Case.id))
        .where(Case.partner_id == partner_id)
        .where(Case.status.in_([CaseStatus.active, CaseStatus.in_progress]))
    )
    active_cases = cases_result.scalar()
    
    return {
        "total_sales": total_sales,
        "approved_sales": approved_sales,
        "pending_sales": pending_sales,
        "total_commission": total_commission,
        "active_cases": active_cases
    }


@router.get("/case-manager-dashboard", response_model=dict)
async def get_case_manager_dashboard_stats(
    current_user: dict = Depends(require_role([UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Get case manager dashboard statistics"""
    manager_id = current_user["id"]
    
    # Total cases
    total_result = await db.execute(
        select(func.count(Case.id)).where(Case.case_manager_id == manager_id)
    )
    total_cases = total_result.scalar()
    
    # Active cases
    active_result = await db.execute(
        select(func.count(Case.id))
        .where(Case.case_manager_id == manager_id)
        .where(Case.status.in_([CaseStatus.active, CaseStatus.in_progress]))
    )
    active_cases = active_result.scalar()
    
    # Completed cases
    completed_result = await db.execute(
        select(func.count(Case.id))
        .where(Case.case_manager_id == manager_id)
        .where(Case.status == CaseStatus.completed)
    )
    completed_cases = completed_result.scalar()
    
    # Pending document reviews
    pending_reviews_result = await db.execute(
        select(func.count(Document.id))
        .join(Case, Document.case_id == Case.id)
        .where(Case.case_manager_id == manager_id)
        .where(Document.status == DocumentStatus.pending_review)
    )
    pending_reviews = pending_reviews_result.scalar()
    
    return {
        "total_cases": total_cases,
        "active_cases": active_cases,
        "completed_cases": completed_cases,
        "pending_reviews": pending_reviews
    }


@router.get("/client-dashboard", response_model=dict)
async def get_client_dashboard_stats(
    current_user: dict = Depends(require_role([UserRole.client])),
    db: AsyncSession = Depends(get_db)
):
    """Get client dashboard statistics"""
    client_id = current_user["id"]
    
    # Total cases
    total_result = await db.execute(
        select(func.count(Case.id)).where(Case.client_id == client_id)
    )
    total_cases = total_result.scalar()
    
    # Active cases
    active_result = await db.execute(
        select(func.count(Case.id))
        .where(Case.client_id == client_id)
        .where(Case.status.in_([CaseStatus.active, CaseStatus.in_progress]))
    )
    active_cases = active_result.scalar()
    
    # Pending documents
    pending_docs_result = await db.execute(
        select(func.count(Document.id))
        .join(Case, Document.case_id == Case.id)
        .where(Case.client_id == client_id)
        .where(Document.status == DocumentStatus.pending_review)
    )
    pending_docs = pending_docs_result.scalar()
    
    return {
        "total_cases": total_cases,
        "active_cases": active_cases,
        "pending_documents": pending_docs
    }
