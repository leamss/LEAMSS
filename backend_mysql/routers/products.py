"""
Products Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List
from datetime import date
from core.database import get_db
from core.models import (
    Product, WorkflowStep, DocumentRequirement, CommissionTier, 
    CommissionHistory, UserRole, CommissionType
)
from core.auth import get_current_user, require_role
from core.schemas import ProductCreate, ProductUpdate, WorkflowStepCreate

router = APIRouter(prefix="/products", tags=["Products"])


def serialize_product(product: Product) -> dict:
    """Convert product model to dict with all relations"""
    workflow_steps = []
    for step in sorted(product.workflow_steps, key=lambda s: s.step_order):
        step_dict = {
            "id": step.id,
            "step_name": step.step_name,
            "step_order": step.step_order,
            "description": step.description,
            "duration_days": step.duration_days,
            "required_documents": [
                {
                    "id": doc.id,
                    "doc_name": doc.doc_name,
                    "description": doc.description,
                    "is_mandatory": doc.is_mandatory,
                    "has_expiry": doc.has_expiry,
                    "validity_months": doc.validity_months,
                    "doc_type": doc.doc_type
                }
                for doc in step.document_requirements
            ]
        }
        workflow_steps.append(step_dict)
    
    commission_tiers = [
        {
            "id": tier.id,
            "min_sales": tier.min_sales,
            "max_sales": tier.max_sales,
            "commission_rate": tier.commission_rate
        }
        for tier in product.commission_tiers
    ]
    
    commission_history = [
        {
            "id": h.id,
            "commission_rate": h.commission_rate,
            "commission_type": h.commission_type.value,
            "effective_from": h.effective_from.isoformat() if h.effective_from else None,
            "created_at": h.created_at.isoformat() if h.created_at else None
        }
        for h in product.commission_history
    ]
    
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "fee": product.fee,
        "commission_rate": product.commission_rate,
        "commission_type": product.commission_type.value if product.commission_type else "fixed",
        "commission_effective_from": product.commission_effective_from.isoformat() if product.commission_effective_from else None,
        "status": product.status,
        "workflow_steps": workflow_steps,
        "commission_tiers": commission_tiers,
        "commission_history": commission_history,
        "created_at": product.created_at.isoformat() if product.created_at else None
    }


@router.get("", response_model=List[dict])
async def get_products(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all products with workflow steps"""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.workflow_steps).selectinload(WorkflowStep.document_requirements),
            selectinload(Product.commission_tiers),
            selectinload(Product.commission_history)
        )
        .where(Product.status == "active")
        .order_by(Product.name)
    )
    products = result.scalars().all()
    
    return [serialize_product(p) for p in products]


@router.get("/{product_id}", response_model=dict)
async def get_product(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get product by ID"""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.workflow_steps).selectinload(WorkflowStep.document_requirements),
            selectinload(Product.commission_tiers),
            selectinload(Product.commission_history)
        )
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return serialize_product(product)


@router.post("", response_model=dict)
async def create_product(
    request: ProductCreate,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new product (Admin only)"""
    product = Product(
        name=request.name,
        description=request.description,
        fee=request.fee,
        commission_rate=request.commission_rate,
        commission_type=CommissionType(request.commission_type) if request.commission_type else CommissionType.fixed,
        status="active"
    )
    
    db.add(product)
    await db.flush()
    
    # Add commission tiers if tiered
    if request.commission_type == "tiered" and request.commission_tiers:
        for tier in request.commission_tiers:
            ct = CommissionTier(
                product_id=product.id,
                min_sales=tier.get("min_sales", 0),
                max_sales=tier.get("max_sales"),
                commission_rate=tier.get("commission_rate", 0)
            )
            db.add(ct)
    
    # Add commission history
    history = CommissionHistory(
        product_id=product.id,
        commission_rate=request.commission_rate,
        commission_type=CommissionType(request.commission_type) if request.commission_type else CommissionType.fixed,
        effective_from=date.today(),
        created_by=current_user["id"]
    )
    db.add(history)
    
    await db.commit()
    
    # Reload with relations
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.workflow_steps).selectinload(WorkflowStep.document_requirements),
            selectinload(Product.commission_tiers),
            selectinload(Product.commission_history)
        )
        .where(Product.id == product.id)
    )
    product = result.scalar_one()
    
    return serialize_product(product)


@router.put("/{product_id}", response_model=dict)
async def update_product(
    product_id: str,
    request: ProductUpdate,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Update a product (Admin only)"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    commission_changed = False
    
    if request.name is not None:
        product.name = request.name
    if request.description is not None:
        product.description = request.description
    if request.fee is not None:
        product.fee = request.fee
    if request.commission_rate is not None and request.commission_rate != product.commission_rate:
        product.commission_rate = request.commission_rate
        commission_changed = True
    if request.commission_type is not None:
        product.commission_type = CommissionType(request.commission_type)
        commission_changed = True
    
    # Update commission tiers if provided
    if request.commission_tiers is not None:
        # Delete old tiers
        await db.execute(delete(CommissionTier).where(CommissionTier.product_id == product_id))
        
        # Add new tiers
        for tier in request.commission_tiers:
            ct = CommissionTier(
                product_id=product.id,
                min_sales=tier.get("min_sales", 0),
                max_sales=tier.get("max_sales"),
                commission_rate=tier.get("commission_rate", 0)
            )
            db.add(ct)
    
    # Add to commission history if changed
    if commission_changed:
        history = CommissionHistory(
            product_id=product.id,
            commission_rate=product.commission_rate,
            commission_type=product.commission_type,
            effective_from=date.today(),
            created_by=current_user["id"]
        )
        db.add(history)
    
    await db.commit()
    
    # Reload with relations
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.workflow_steps).selectinload(WorkflowStep.document_requirements),
            selectinload(Product.commission_tiers),
            selectinload(Product.commission_history)
        )
        .where(Product.id == product.id)
    )
    product = result.scalar_one()
    
    return serialize_product(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Delete a product (Admin only)"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Soft delete - just mark as inactive
    product.status = "inactive"
    await db.commit()
    
    return {"message": "Product deleted successfully"}


@router.post("/{product_id}/workflow-step", response_model=dict)
async def add_workflow_step(
    product_id: str,
    request: WorkflowStepCreate,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Add workflow step to product (Admin only)"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    step = WorkflowStep(
        product_id=product_id,
        step_name=request.step_name,
        step_order=request.step_order,
        description=request.description,
        duration_days=request.duration_days
    )
    
    db.add(step)
    await db.flush()
    
    # Add document requirements
    for doc in request.required_documents:
        doc_req = DocumentRequirement(
            workflow_step_id=step.id,
            doc_name=doc.doc_name,
            description=doc.description,
            is_mandatory=doc.is_mandatory,
            has_expiry=doc.has_expiry,
            validity_months=doc.validity_months,
            doc_type=doc.doc_type
        )
        db.add(doc_req)
    
    await db.commit()
    
    return {"message": "Workflow step added successfully", "step_id": step.id}


@router.delete("/{product_id}/workflow-step/{step_order}")
async def delete_workflow_step(
    product_id: str,
    step_order: int,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Delete workflow step (Admin only)"""
    result = await db.execute(
        select(WorkflowStep)
        .where(WorkflowStep.product_id == product_id)
        .where(WorkflowStep.step_order == step_order)
    )
    step = result.scalar_one_or_none()
    
    if not step:
        raise HTTPException(status_code=404, detail="Workflow step not found")
    
    await db.delete(step)
    await db.commit()
    
    return {"message": "Workflow step deleted successfully"}
