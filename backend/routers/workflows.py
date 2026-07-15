"""Workflow Builder Router — custom workflow templates"""
from fastapi import APIRouter, HTTPException, Depends
from core.database import products_col, workflow_steps_col
from core.auth import get_current_user
from core.services import log_activity
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/workflows", tags=["Workflow Builder"])


@router.get("/{product_id}")
async def get_workflow(product_id: str, current_user: dict = Depends(get_current_user)):
    """Get workflow steps for a product"""
    steps = await workflow_steps_col.find(
        {"product_id": product_id}, {"_id": 0}
    ).sort("step_order", 1).to_list(100)
    product = await products_col.find_one({"id": product_id}, {"_id": 0})
    # Normalize field names
    for s in steps:
        s["name"] = s.get("step_name") or s.get("name", "")
        s["order"] = s.get("step_order") or s.get("order", 0)
    return {
        "product_id": product_id,
        "product_name": product.get("name", "") if product else "",
        "steps": steps
    }


@router.put("/{product_id}")
async def update_workflow(product_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Update entire workflow for a product (drag-and-drop reorder, add/remove steps)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    product = await products_col.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    steps = data.get("steps", [])
    
    # Delete existing steps
    await workflow_steps_col.delete_many({"product_id": product_id})
    
    # Insert new steps in order
    for idx, step in enumerate(steps):
        step_doc = {
            "id": step.get("id", str(uuid.uuid4())),
            "product_id": product_id,
            "step_name": step.get("name") or step.get("step_name", f"Step {idx + 1}"),
            "name": step.get("name") or step.get("step_name", f"Step {idx + 1}"),
            "step_order": idx + 1,
            "order": idx + 1,
            "description": step.get("description", ""),
            "duration_days": step.get("duration_days", 7),
            "required_documents": step.get("required_documents", []),
            "sections": step.get("sections", []),
            "is_active": step.get("is_active", True),
            "created_at": datetime.now(timezone.utc)
        }
        await workflow_steps_col.insert_one(step_doc)
    
    await log_activity(current_user["id"], current_user["name"], "updated_workflow", "product", product_id,
        f"Updated workflow for {product.get('name', '')} — {len(steps)} steps")
    
    return {"message": f"Workflow updated with {len(steps)} steps"}


@router.post("/{product_id}/step")
async def add_step(product_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Add a new step to an existing workflow"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Get current max order
    last_step = await workflow_steps_col.find_one(
        {"product_id": product_id}, sort=[("order", -1)]
    )
    next_order = (last_step.get("order", 0) + 1) if last_step else 1
    
    step_doc = {
        "id": str(uuid.uuid4()),
        "product_id": product_id,
        "name": data.get("name", f"Step {next_order}"),
        "description": data.get("description", ""),
        "order": next_order,
        "required_documents": data.get("required_documents", []),
        "sections": [],
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    await workflow_steps_col.insert_one(step_doc)
    
    return {"id": step_doc["id"], "message": "Step added"}


@router.delete("/{product_id}/step/{step_id}")
async def delete_step(product_id: str, step_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a workflow step"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await workflow_steps_col.delete_one({"id": step_id, "product_id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Step not found")
    
    # Reorder remaining steps
    remaining = await workflow_steps_col.find(
        {"product_id": product_id}, {"_id": 0}
    ).sort("order", 1).to_list(100)
    for idx, step in enumerate(remaining):
        await workflow_steps_col.update_one({"id": step["id"]}, {"$set": {"order": idx + 1}})
    
    return {"message": "Step deleted and workflow reordered"}
