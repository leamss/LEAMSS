"""
Scheduler Router for LEAMSS Portal (MySQL)
Document expiry tracking and notifications
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime, timedelta
from core.database import get_db
from core.models import Document, Case, User, UserRole
from core.auth import get_current_user, require_role

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.get("/expiring-documents", response_model=List[dict])
async def get_expiring_documents(
    days: int = 30,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Get documents expiring within specified days"""
    today = datetime.utcnow().date()
    expiry_date = today + timedelta(days=days)
    
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.case).selectinload(Case.client))
        .where(Document.expiry_date.isnot(None))
        .where(Document.expiry_date <= expiry_date)
        .where(Document.expiry_date >= today)
        .order_by(Document.expiry_date)
    )
    documents = result.scalars().all()
    
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "document_type": doc.document_type,
            "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
            "days_until_expiry": (doc.expiry_date - today).days if doc.expiry_date else None,
            "case_id": doc.case_id,
            "case_number": doc.case.case_id if doc.case else None,
            "client_name": doc.case.client.name if doc.case and doc.case.client else None,
            "status": doc.status.value if doc.status else "unknown"
        }
        for doc in documents
    ]


@router.get("/expired-documents", response_model=List[dict])
async def get_expired_documents(
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Get already expired documents"""
    today = datetime.utcnow().date()
    
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.case).selectinload(Case.client))
        .where(Document.expiry_date.isnot(None))
        .where(Document.expiry_date < today)
        .order_by(Document.expiry_date.desc())
    )
    documents = result.scalars().all()
    
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "document_type": doc.document_type,
            "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
            "days_expired": (today - doc.expiry_date).days if doc.expiry_date else None,
            "case_id": doc.case_id,
            "case_number": doc.case.case_id if doc.case else None,
            "client_name": doc.case.client.name if doc.case and doc.case.client else None,
            "status": doc.status.value if doc.status else "unknown"
        }
        for doc in documents
    ]
