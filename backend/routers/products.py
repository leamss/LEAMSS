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
    # Phase 4C — Success bonus field is `bonus_amount` (matches allocations_logic), fall back to `amount`
    max_bonus = sum(
        float((b.get("bonus_amount") if b.get("bonus_amount") is not None else b.get("amount", 0)) or 0)
        for b in (success_bonuses or [])
    )
    return {
        "expected_base_cost": round(base, 2),
        "expected_margin": round(margin, 2),
        "expected_margin_pct": round((margin / sp * 100), 2) if sp > 0 else 0,
        "max_bonus_payout": round(max_bonus, 2),
    }


@router.get("")
async def get_products(
    include_archived: bool = False,
    category: Optional[str] = None,
    country: Optional[str] = None,
    is_pre_assessment: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Phase 20.2 — extended with filters + archived exclusion by default."""
    q: Dict[str, Any] = {}
    if not include_archived:
        q["archived_at"] = None
    if category:
        q["$or"] = [{"category": category}, {"_category_v2": category}]
    if country:
        q["country"] = country
    if is_pre_assessment is not None:
        q["is_pre_assessment"] = bool(is_pre_assessment)
    products = await products_col.find(q, {"_id": 0}).to_list(200)
    for p in products:
        steps = await workflow_steps_col.find({"product_id": p["id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        p["workflow_steps"] = steps
        for k in ("created_at", "updated_at", "archived_at"):
            if isinstance(p.get(k), datetime):
                p[k] = p[k].isoformat()
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
        # Phase 20.2 — new fields
        "is_pre_assessment", "pre_assessment_fee_inr", "pre_assessment_fee_currency",
        "workflow_id", "workflow_steps_count",
        "visa_subclass", "assessing_body_code",
        "commissions_v2", "_category_v2",
    ]:
        if field in data:
            update[field] = data[field]

    # Phase 20.2 — validation rules
    if "assessing_body_code" in update and update["assessing_body_code"]:
        existing = await products_col.find_one({"id": product_id}, {"country": 1})
        country = (data.get("country") or (existing or {}).get("country") or "").upper()
        if country not in ("AU", "NZ", "AUSTRALIA", "NEW ZEALAND"):
            raise HTTPException(status_code=400,
                                detail=f"assessing_body_code only valid for AU/NZ products; got country={country}")
        aa = await db["assessing_authorities"].find_one(
            {"code": update["assessing_body_code"]}, {"_id": 0, "code": 1})
        if not aa:
            raise HTTPException(status_code=400,
                                detail=f"Unknown assessing_body_code: {update['assessing_body_code']}")

    if "workflow_id" in update and update["workflow_id"]:
        wf = await db["ai_workflow_templates"].find_one(
            {"id": update["workflow_id"], "verified": True}, {"_id": 0, "id": 1})
        if not wf:
            raise HTTPException(status_code=400,
                                detail=f"Unknown or unverified workflow_id: {update['workflow_id']}")

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


# ── Phase 20.2 — Soft-archive / restore / link workflow / commissions ─────────
class ArchiveRequest(BaseModel):
    reason: str = Field(..., min_length=2, max_length=300)


@router.post("/{product_id}/archive")
async def archive_product(product_id: str, req: ArchiveRequest,
                          current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = await products_col.find_one({"id": product_id}, {"id": 1, "name": 1, "archived_at": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    if p.get("archived_at"):
        return {"ok": True, "already_archived": True, "id": product_id}
    now = datetime.now(timezone.utc)
    await products_col.update_one({"id": product_id}, {"$set": {
        "archived_at": now, "archived_by": current_user.get("id"),
        "archived_by_email": current_user.get("email"),
        "archived_reason": req.reason,
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "archived", "product", product_id,
                       f"Archived '{p.get('name')}' · reason: {req.reason}")
    return {"ok": True, "id": product_id, "archived_at": now.isoformat()}


@router.post("/{product_id}/restore")
async def restore_product(product_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = await products_col.find_one({"id": product_id}, {"id": 1, "name": 1, "archived_at": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    if not p.get("archived_at"):
        return {"ok": True, "already_active": True, "id": product_id}
    await products_col.update_one({"id": product_id}, {"$set": {
        "archived_at": None, "archived_by": None,
        "archived_by_email": None, "archived_reason": None,
        "restored_at": datetime.now(timezone.utc),
        "restored_by": current_user.get("id"),
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "restored", "product", product_id,
                       f"Restored '{p.get('name')}'")
    return {"ok": True, "id": product_id}


class LinkWorkflowRequest(BaseModel):
    workflow_id: str
    steps_count: Optional[int] = None


@router.post("/{product_id}/link-workflow")
async def link_workflow(product_id: str, req: LinkWorkflowRequest,
                        current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    wf = await db["ai_workflow_templates"].find_one(
        {"id": req.workflow_id, "verified": True}, {"_id": 0})
    if not wf:
        raise HTTPException(status_code=400,
                            detail=f"Unknown or unverified workflow_id: {req.workflow_id}")
    steps = req.steps_count
    if steps is None:
        steps = len((wf.get("workflow_payload") or {}).get("steps") or [])
    await products_col.update_one({"id": product_id}, {"$set": {
        "workflow_id": req.workflow_id, "workflow_steps_count": steps,
        "updated_at": datetime.now(timezone.utc),
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "linked_workflow", "product", product_id,
                       f"Linked workflow {req.workflow_id} ({steps} steps)")
    return {"ok": True, "id": product_id, "workflow_id": req.workflow_id, "steps_count": steps}


@router.get("/{product_id}/commissions")
async def get_commissions(product_id: str, current_user: dict = Depends(get_current_user)):
    """Returns commissions_v2 filtered by caller's role.
    Sales user → only sales_user · Partner → only partner_internal/external · Admin → all.
    """
    p = await products_col.find_one({"id": product_id}, {"_id": 0, "id": 1, "name": 1, "commissions_v2": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    v2 = p.get("commissions_v2") or {}
    role = (current_user.get("rbac_role") or current_user.get("role") or "").lower()
    visible = {}
    if role in ("admin", "admin_owner", "super_admin") or "*" in (current_user.get("permissions") or []):
        visible = v2  # full view
    elif role in ("sales", "case_manager"):
        if "sales_user" in v2:
            visible["sales_user"] = v2["sales_user"]
    elif role == "partner":
        if "partner_internal" in v2:
            visible["partner_internal"] = v2["partner_internal"]
        if "partner_external" in v2:
            visible["partner_external"] = v2["partner_external"]
    return {"product_id": product_id, "name": p.get("name"), "commissions": visible,
            "role": role, "has_v2": bool(v2)}


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
                bonus = float((match.get("bonus_amount") if match.get("bonus_amount") is not None else match.get("amount", 0)) or 0)
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

