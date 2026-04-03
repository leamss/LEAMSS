"""Products Router"""
from fastapi import APIRouter, HTTPException, Depends
from core.database import products_col, workflow_steps_col
from core.auth import get_current_user
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("")
async def get_products(current_user: dict = Depends(get_current_user)):
    products = await products_col.find({}, {"_id": 0}).to_list(100)
    for p in products:
        steps = await workflow_steps_col.find({"product_id": p["id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        p["workflow_steps"] = steps
        if isinstance(p.get("created_at"), datetime):
            p["created_at"] = p["created_at"].isoformat()
    return products


@router.get("/{product_id}")
async def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    product = await products_col.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    steps = await workflow_steps_col.find({"product_id": product_id}, {"_id": 0}).sort("step_order", 1).to_list(100)
    product["workflow_steps"] = steps
    return product


@router.post("")
async def create_product(data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    product = {
        "id": str(uuid.uuid4()), "name": data["name"],
        "description": data.get("description", ""),
        "category": data.get("category", "immigration"),
        "base_fee": data.get("base_fee", 0),
        "status": "active", "created_at": datetime.now(timezone.utc)
    }
    await products_col.insert_one(product)
    
    for step_data in data.get("workflow_steps", []):
        step = {
            "id": str(uuid.uuid4()), "product_id": product["id"],
            "step_name": step_data["step_name"],
            "step_order": step_data["step_order"],
            "description": step_data.get("description", ""),
            "duration_days": step_data.get("duration_days", 7),
            "required_documents": step_data.get("required_documents", [])
        }
        await workflow_steps_col.insert_one(step)
    
    return {"id": product["id"], "message": "Product created"}


@router.put("/{product_id}")
async def update_product(product_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    update = {}
    for field in ["name", "description", "category", "base_fee", "status"]:
        if field in data:
            update[field] = data[field]
    
    if update:
        await products_col.update_one({"id": product_id}, {"$set": update})
    return {"message": "Product updated"}


@router.delete("/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await products_col.delete_one({"id": product_id})
    await workflow_steps_col.delete_many({"product_id": product_id})
    return {"message": "Product deleted"}


@router.post("/{product_id}/workflow-step")
async def create_workflow_step(product_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Prevent duplicate step names for same product
    existing = await workflow_steps_col.find_one({
        "product_id": product_id,
        "step_name": {"$regex": f"^{data['step_name'].strip()}$", "$options": "i"}
    })
    if existing:
        raise HTTPException(status_code=400, detail=f"A workflow step named '{data['step_name']}' already exists for this product")
    
    # Prevent duplicate step_order
    order_exists = await workflow_steps_col.find_one({
        "product_id": product_id,
        "step_order": data["step_order"]
    })
    if order_exists:
        raise HTTPException(status_code=400, detail=f"Step order {data['step_order']} already exists for this product")
    
    step = {
        "id": str(uuid.uuid4()), "product_id": product_id,
        "step_name": data["step_name"].strip(), "step_order": data["step_order"],
        "description": data.get("description", ""),
        "duration_days": data.get("duration_days", 7),
        "required_documents": data.get("required_documents", [])
    }
    await workflow_steps_col.insert_one(step)
    return {"message": "Workflow step created"}


@router.put("/{product_id}/workflow-step/{step_order}")
async def update_workflow_step(product_id: str, step_order: int, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    update = {}
    for field in ["step_name", "step_order", "description", "duration_days", "required_documents"]:
        if field in data:
            update[field] = data[field]
    
    await workflow_steps_col.update_one(
        {"product_id": product_id, "step_order": step_order},
        {"$set": update}
    )
    return {"message": "Workflow step updated"}


@router.delete("/{product_id}/workflow-step/{step_order}")
async def delete_workflow_step(product_id: str, step_order: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await workflow_steps_col.delete_one({"product_id": product_id, "step_order": step_order})
    return {"message": "Workflow step deleted"}
