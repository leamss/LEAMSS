"""Products Router — Phase 4C Unified.

A unified product carries both workflow-builder fields AND cost-structure fields
(country, visa_type, service_price, cost_allocations, success_bonuses, computed margin).
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from core.database import products_col, workflow_steps_col, db
from core.auth import get_current_user
from core.services import log_activity
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/products", tags=["Products"])


def _compute_margin(service_price: float, cost_allocations: list, success_bonuses: list) -> dict:
    sp = float(service_price or 0)
    base = 0.0
    for a in (cost_allocations or []):
        if a.get("is_optional"):
            continue
        # Percentage and flat both store the value in `amount` (rate is a fallback alias)
        val = float(a.get("rate") if a.get("rate") is not None else a.get("amount", 0) or 0)
        if a.get("payment_type") == "percentage":
            base += sp * val / 100.0
        else:
            base += val
    margin = sp - base
    return {
        "expected_base_cost": round(base, 2),
        "expected_margin": round(margin, 2),
        "expected_margin_pct": round((margin / sp * 100), 2) if sp > 0 else 0,
        "max_bonus_payout": round(sum(float(b.get("amount", 0) or 0) for b in (success_bonuses or [])), 2),
    }


@router.get("")
async def get_products(current_user: dict = Depends(get_current_user)):
    products = await products_col.find({}, {"_id": 0}).to_list(100)
    for p in products:
        steps = await workflow_steps_col.find({"product_id": p["id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        p["workflow_steps"] = steps
        if isinstance(p.get("created_at"), datetime):
            p["created_at"] = p["created_at"].isoformat()
        if isinstance(p.get("updated_at"), datetime):
            p["updated_at"] = p["updated_at"].isoformat()
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
    sp = float(data.get("service_price") or data.get("base_fee") or 0)
    cost_allocations = data.get("cost_allocations") or []
    success_bonuses = data.get("success_bonuses") or []
    product = {
        "id": str(uuid.uuid4()),
        "name": data["name"],
        "description": data.get("description", ""),
        "category": data.get("category", "immigration"),
        "country": data.get("country") or "",
        "visa_type": data.get("visa_type") or "",
        "base_fee": sp,
        "service_price": sp,
        "commission_rate": data.get("commission_rate", 0),
        "commission_type": data.get("commission_type", "percentage"),
        "cost_allocations": cost_allocations,
        "success_bonuses": success_bonuses,
        "computed": _compute_margin(sp, cost_allocations, success_bonuses),
        "status": "active",
        "created_at": datetime.now(timezone.utc),
    }
    await products_col.insert_one(product)
    for step_data in data.get("workflow_steps", []):
        step = {
            "id": str(uuid.uuid4()), "product_id": product["id"],
            "step_name": step_data["step_name"],
            "step_order": step_data["step_order"],
            "description": step_data.get("description", ""),
            "duration_days": step_data.get("duration_days", 7),
            "required_documents": step_data.get("required_documents", []),
        }
        await workflow_steps_col.insert_one(step)
    await log_activity(current_user["id"], current_user["name"], "created", "product", product["id"],
                       f"Created product: {data['name']}")
    return {"id": product["id"], "message": "Product created"}


@router.put("/{product_id}")
async def update_product(product_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    update: Dict[str, Any] = {}
    for field in [
        "name", "description", "category", "status",
        "country", "visa_type",
        "commission_type", "commission_rate", "commission_tiers", "commission_effective_from",
        "cost_allocations", "success_bonuses", "cost_structure_meta",
    ]:
        if field in data:
            update[field] = data[field]
    # base_fee / service_price are mirrored
    if "service_price" in data:
        update["service_price"] = float(data["service_price"] or 0)
        update["base_fee"] = update["service_price"]
    elif "base_fee" in data:
        update["base_fee"] = float(data["base_fee"] or 0)
        update["service_price"] = update["base_fee"]
    elif "fee" in data:
        update["base_fee"] = float(data["fee"] or 0)
        update["service_price"] = update["base_fee"]

    if update:
        # Recompute margin if pricing-related fields changed
        if any(k in update for k in ("service_price", "base_fee", "cost_allocations", "success_bonuses")):
            current = await products_col.find_one({"id": product_id}, {"_id": 0})
            if current:
                merged = {**current, **update}
                update["computed"] = _compute_margin(
                    merged.get("service_price") or merged.get("base_fee") or 0,
                    merged.get("cost_allocations") or [],
                    merged.get("success_bonuses") or [],
                )
        update["updated_at"] = datetime.now(timezone.utc)
        await products_col.update_one({"id": product_id}, {"$set": update})
    await log_activity(current_user["id"], current_user["name"], "updated", "product", product_id,
                       f"Updated product fields: {', '.join(k for k in update.keys() if k != 'updated_at')}")
    return {"message": "Product updated", "computed": update.get("computed")}


@router.delete("/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await products_col.delete_one({"id": product_id})
    await workflow_steps_col.delete_many({"product_id": product_id})
    await log_activity(current_user["id"], current_user["name"], "deleted", "product", product_id,
                       "Deleted product and workflow steps")
    return {"message": "Product deleted"}


# ──────────────────────────────────────────────────────────────
# Phase 4C — Cost preview / calculator on a Product
# ──────────────────────────────────────────────────────────────
class PreviewRequest(BaseModel):
    service_price: Optional[float] = None
    visa_approved: bool = False


@router.post("/{product_id}/preview")
async def preview_cost(product_id: str, req: PreviewRequest, current_user: dict = Depends(get_current_user)):
    """Compute allocations + margin breakdown for a hypothetical sale on this product."""
    p = await products_col.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    sp = float(req.service_price if req.service_price is not None else (p.get("service_price") or p.get("base_fee") or 0))
    cost_allocations = p.get("cost_allocations") or []
    success_bonuses = p.get("success_bonuses") or []

    rows = []
    for a in cost_allocations:
        val = float(a.get("rate") if a.get("rate") is not None else a.get("amount", 0) or 0)
        if a.get("payment_type") == "percentage":
            base = sp * val / 100.0
        else:
            base = val
        bonus = 0.0
        if req.visa_approved:
            match = next((b for b in success_bonuses if b.get("vendor_category") == a.get("vendor_category")), None)
            if match:
                bonus = float(match.get("amount", 0) or 0)
        rows.append({
            "label": a.get("label"),
            "vendor_category": a.get("vendor_category"),
            "payment_type": a.get("payment_type"),
            "base_amount": round(base, 2),
            "bonus_amount": round(bonus, 2),
            "total_amount": round(base + bonus, 2),
            "is_optional": a.get("is_optional", False),
        })

    total_cost = sum(r["total_amount"] for r in rows if not r["is_optional"])
    margin = sp - total_cost
    return {
        "service_price": sp,
        "rows": rows,
        "total_cost": round(total_cost, 2),
        "margin": round(margin, 2),
        "margin_pct": round((margin / sp * 100), 2) if sp > 0 else 0,
        "visa_approved_applied": req.visa_approved,
    }


# ──────────────────────────────────────────────────────────────
# Workflow Step CRUD (unchanged — kept for AI Workflow Builder)
# ──────────────────────────────────────────────────────────────
@router.post("/{product_id}/workflow-step")
async def create_workflow_step(product_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    import re
    escaped_name = re.escape(data['step_name'].strip())
    existing = await workflow_steps_col.find_one({
        "product_id": product_id,
        "step_name": {"$regex": f"^{escaped_name}$", "$options": "i"}
    })
    if existing:
        raise HTTPException(status_code=400, detail=f"A workflow step named '{data['step_name']}' already exists for this product")
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

