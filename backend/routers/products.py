"""
Product and workflow management routes for LEAMSS Portal
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from typing import List
from bson import ObjectId

from core.database import db
from core.auth import get_current_user, require_role, UserRole
from core.models import ProductCreate, ProductUpdate, ProductResponse, WorkflowStepCreate

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
async def get_products(user: dict = Depends(get_current_user)):
    """Get all products"""
    products = await db.products.find({}, {"_id": 0}).to_list(100)
    return [ProductResponse(**p) for p in products]


@router.post("", response_model=ProductResponse)
async def create_product(product: ProductCreate, user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Create a new product (Admin only)"""
    product_doc = {
        "id": str(ObjectId()),
        "name": product.name,
        "description": product.description,
        "fee": product.fee,
        "commission_rate": product.commission_rate,
        "commission_type": product.commission_type,
        "commission_tiers": product.commission_tiers or [],
        "commission_history": [],
        "workflow_steps": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.products.insert_one(product_doc)
    return ProductResponse(**product_doc)


@router.post("/workflow-step")
async def add_workflow_step(step: WorkflowStepCreate, user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Add a workflow step to a product (Admin only)"""
    product = await db.products.find_one({"id": step.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    step_doc = {
        "step_name": step.step_name,
        "step_order": step.step_order,
        "description": step.description,
        "duration_days": step.duration_days,
        "required_documents": [doc.model_dump() for doc in step.required_documents]
    }
    
    await db.products.update_one(
        {"id": step.product_id},
        {"$push": {"workflow_steps": step_doc}}
    )
    return {"message": "Workflow step added successfully"}


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, product: ProductUpdate, user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Update a product (Admin only)"""
    existing = await db.products.find_one({"id": product_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = {}
    if product.name is not None:
        update_data["name"] = product.name
    if product.description is not None:
        update_data["description"] = product.description
    if product.fee is not None:
        update_data["fee"] = product.fee
    
    # Handle commission changes with history
    commission_changed = False
    if product.commission_rate is not None or product.commission_type is not None or product.commission_tiers is not None:
        commission_changed = True
        
        # Archive old commission in history
        history_entry = {
            "previous_rate": existing.get("commission_rate"),
            "previous_type": existing.get("commission_type"),
            "previous_tiers": existing.get("commission_tiers", []),
            "new_rate": product.commission_rate if product.commission_rate is not None else existing.get("commission_rate"),
            "new_type": product.commission_type if product.commission_type is not None else existing.get("commission_type"),
            "new_tiers": product.commission_tiers if product.commission_tiers is not None else existing.get("commission_tiers", []),
            "effective_from": product.commission_effective_from or datetime.now(timezone.utc).isoformat(),
            "changed_at": datetime.now(timezone.utc).isoformat(),
            "changed_by": user["id"],
            "changed_by_name": user["name"]
        }
        
        if product.commission_rate is not None:
            update_data["commission_rate"] = product.commission_rate
        if product.commission_type is not None:
            update_data["commission_type"] = product.commission_type
        if product.commission_tiers is not None:
            update_data["commission_tiers"] = product.commission_tiers
    
    if update_data:
        if commission_changed:
            await db.products.update_one(
                {"id": product_id},
                {
                    "$set": update_data,
                    "$push": {"commission_history": history_entry}
                }
            )
        else:
            await db.products.update_one({"id": product_id}, {"$set": update_data})
    
    updated = await db.products.find_one({"id": product_id}, {"_id": 0})
    return ProductResponse(**updated)


@router.delete("/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Delete a product (Admin only)"""
    await db.products.delete_one({"id": product_id})
    return {"message": "Product deleted successfully"}


@router.put("/{product_id}/workflow-step/{step_order}")
async def update_workflow_step(
    product_id: str, 
    step_order: int, 
    step: WorkflowStepCreate, 
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Update a workflow step (Admin only)"""
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    workflow_steps = product.get("workflow_steps", [])
    step_index = next((i for i, s in enumerate(workflow_steps) if s.get("step_order") == step_order), None)
    
    if step_index is None:
        raise HTTPException(status_code=404, detail="Workflow step not found")
    
    step_doc = {
        "step_name": step.step_name,
        "step_order": step.step_order,
        "description": step.description,
        "duration_days": step.duration_days,
        "required_documents": [doc.model_dump() for doc in step.required_documents]
    }
    
    workflow_steps[step_index] = step_doc
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"workflow_steps": workflow_steps}}
    )
    
    return {"message": "Workflow step updated successfully"}


@router.delete("/{product_id}/workflow-step/{step_order}")
async def delete_workflow_step(product_id: str, step_order: int, user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Delete a workflow step (Admin only)"""
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.products.update_one(
        {"id": product_id},
        {"$pull": {"workflow_steps": {"step_order": step_order}}}
    )
    return {"message": "Workflow step deleted successfully"}
