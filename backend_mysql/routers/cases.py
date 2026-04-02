"""
Cases Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, date
from core.database import get_db
from core.models import (
    Case, CaseStep, CaseStepRequirement, User, Product, Document,
    AdditionalDocRequest, UserRole, CaseStatus, StepStatus, DocumentStatus, Notification
)
from core.auth import get_current_user, require_role
from core.schemas import StepUpdate, AdditionalDocRequest as AdditionalDocRequestSchema

router = APIRouter(prefix="/cases", tags=["Cases"])


def serialize_case(case: Case) -> dict:
    """Convert case model to dict with all relations"""
    steps = []
    for step in sorted(case.steps, key=lambda s: s.step_order):
        step_dict = {
            "id": step.id,
            "step_name": step.step_name,
            "step_order": step.step_order,
            "status": step.status.value if step.status else "locked",
            "is_locked": step.is_locked,
            "notes": step.notes,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            "required_documents": [
                {
                    "id": req.id,
                    "doc_name": req.doc_name,
                    "description": req.description,
                    "is_mandatory": req.is_mandatory,
                    "has_expiry": req.has_expiry,
                    "expiry_date": req.expiry_date.isoformat() if req.expiry_date else None,
                    "validity_months": req.validity_months,
                    "doc_type": req.doc_type,
                    "status": req.status.value if req.status else "pending"
                }
                for req in step.requirements
            ]
        }
        steps.append(step_dict)
    
    additional_requests = [
        {
            "id": req.id,
            "step_order": req.step_order,
            "document_name": req.document_name,
            "description": req.description,
            "due_date": req.due_date.isoformat() if req.due_date else None,
            "expiry_date": req.expiry_date.isoformat() if req.expiry_date else None,
            "validity_months": req.validity_months,
            "doc_type": req.doc_type,
            "status": req.status.value if req.status else "pending"
        }
        for req in case.additional_doc_requests
    ]
    
    return {
        "id": case.id,
        "case_id": case.case_id,
        "client_id": case.client_id,
        "client_name": case.client.name if case.client else "Unknown",
        "client_email": case.client.email if case.client else "",
        "product_id": case.product_id,
        "product_name": case.product.name if case.product else "Unknown",
        "case_manager_id": case.case_manager_id,
        "case_manager_name": case.case_manager.name if case.case_manager else None,
        "partner_id": case.partner_id,
        "status": case.status.value if case.status else "active",
        "current_step": case.current_step,
        "current_step_order": case.current_step_order,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "steps": steps,
        "additional_doc_requests": additional_requests
    }


@router.get("", response_model=List[dict])
async def get_all_cases(
    status: str = None,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get all cases (Admin only)"""
    query = select(Case).options(
        selectinload(Case.client),
        selectinload(Case.case_manager),
        selectinload(Case.product),
        selectinload(Case.steps).selectinload(CaseStep.requirements),
        selectinload(Case.additional_doc_requests)
    )
    
    if status:
        query = query.where(Case.status == CaseStatus(status))
    
    result = await db.execute(query.order_by(Case.created_at.desc()))
    cases = result.scalars().all()
    
    return [serialize_case(c) for c in cases]


@router.get("/my-cases", response_model=List[dict])
async def get_my_cases(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cases for current user based on role"""
    query = select(Case).options(
        selectinload(Case.client),
        selectinload(Case.case_manager),
        selectinload(Case.product),
        selectinload(Case.steps).selectinload(CaseStep.requirements),
        selectinload(Case.additional_doc_requests)
    )
    
    if current_user["role"] == "client":
        query = query.where(Case.client_id == current_user["id"])
    elif current_user["role"] == "case_manager":
        query = query.where(Case.case_manager_id == current_user["id"])
    elif current_user["role"] == "partner":
        query = query.where(Case.partner_id == current_user["id"])
    
    result = await db.execute(query.order_by(Case.created_at.desc()))
    cases = result.scalars().all()
    
    return [serialize_case(c) for c in cases]


@router.get("/{case_id}", response_model=dict)
async def get_case(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get case by ID"""
    result = await db.execute(
        select(Case)
        .options(
            selectinload(Case.client),
            selectinload(Case.case_manager),
            selectinload(Case.product),
            selectinload(Case.steps).selectinload(CaseStep.requirements),
            selectinload(Case.additional_doc_requests)
        )
        .where(Case.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return serialize_case(case)


@router.put("/update-step", response_model=dict)
async def update_step_status(
    request: StepUpdate,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Update case step status"""
    result = await db.execute(
        select(Case)
        .options(selectinload(Case.steps), selectinload(Case.client))
        .where(Case.id == request.case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Find the step
    step = next((s for s in case.steps if s.step_name == request.step_name), None)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    # Update step status
    step.status = StepStatus(request.status)
    step.notes = request.notes
    
    if request.status == "in_progress" and not step.started_at:
        step.started_at = datetime.utcnow()
        step.is_locked = False
    elif request.status == "completed":
        step.completed_at = datetime.utcnow()
        step.approved_by = current_user["id"]
        step.approved_at = datetime.utcnow()
        
        # Unlock next step
        next_step = next((s for s in case.steps if s.step_order == step.step_order + 1), None)
        if next_step:
            next_step.is_locked = False
            next_step.status = StepStatus.pending
            case.current_step = next_step.step_name
            case.current_step_order = next_step.step_order
        else:
            # All steps completed
            case.status = CaseStatus.completed
            case.completed_at = datetime.utcnow()
    
    # Notify client
    notification = Notification(
        user_id=case.client_id,
        title=f"Step Updated: {step.step_name}",
        message=f"Your case step '{step.step_name}' has been updated to '{request.status}'",
        type="step_update",
        related_id=case.id
    )
    db.add(notification)
    
    await db.commit()
    
    return {"message": "Step updated successfully"}


@router.post("/request-document", response_model=dict)
async def request_additional_document(
    request: AdditionalDocRequestSchema,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Request additional document from client"""
    result = await db.execute(
        select(Case)
        .options(selectinload(Case.client))
        .where(Case.id == request.case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Parse dates
    due_date = None
    expiry_date = None
    if request.due_date:
        try:
            due_date = datetime.fromisoformat(request.due_date.replace('Z', '+00:00')).date()
        except:
            pass
    if request.expiry_date:
        try:
            expiry_date = datetime.fromisoformat(request.expiry_date.replace('Z', '+00:00')).date()
        except:
            pass
    
    doc_request = AdditionalDocRequest(
        case_id=case.id,
        step_order=request.step_order,
        document_name=request.document_name,
        description=request.description,
        due_date=due_date,
        expiry_date=expiry_date,
        validity_months=request.validity_months,
        doc_type=request.doc_type,
        status=DocumentStatus.pending,
        requested_by=current_user["id"]
    )
    
    db.add(doc_request)
    
    # Notify client
    notification = Notification(
        user_id=case.client_id,
        title="Document Requested",
        message=f"A new document '{request.document_name}' has been requested for your case",
        type="document_request",
        related_id=case.id
    )
    db.add(notification)
    
    await db.commit()
    
    return {"message": "Document requested successfully"}


@router.put("/{case_id}/assign-manager", response_model=dict)
async def assign_case_manager(
    case_id: str,
    case_manager_id: str,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Reassign case manager (Admin only)"""
    result = await db.execute(
        select(Case)
        .options(selectinload(Case.client))
        .where(Case.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Verify the manager exists and is a case_manager
    mgr_result = await db.execute(
        select(User).where(User.id == case_manager_id).where(User.role == UserRole.case_manager)
    )
    manager = mgr_result.scalar_one_or_none()
    
    if not manager:
        raise HTTPException(status_code=404, detail="Case manager not found")
    
    case.case_manager_id = case_manager_id
    
    # Notify the new case manager
    notification = Notification(
        user_id=case_manager_id,
        title="New Case Assigned",
        message=f"You have been assigned to case {case.case_id}",
        type="case_assigned",
        related_id=case.id
    )
    db.add(notification)
    
    await db.commit()
    
    return {"message": "Case manager reassigned successfully"}


@router.get("/stats/my-stats", response_model=dict)
async def get_case_manager_stats(
    current_user: dict = Depends(require_role([UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Get case manager statistics"""
    total_result = await db.execute(
        select(func.count(Case.id)).where(Case.case_manager_id == current_user["id"])
    )
    total = total_result.scalar()
    
    active_result = await db.execute(
        select(func.count(Case.id))
        .where(Case.case_manager_id == current_user["id"])
        .where(Case.status.in_([CaseStatus.active, CaseStatus.in_progress]))
    )
    active = active_result.scalar()
    
    completed_result = await db.execute(
        select(func.count(Case.id))
        .where(Case.case_manager_id == current_user["id"])
        .where(Case.status == CaseStatus.completed)
    )
    completed = completed_result.scalar()
    
    return {
        "my_cases": total,
        "active_cases": active,
        "completed_cases": completed
    }
