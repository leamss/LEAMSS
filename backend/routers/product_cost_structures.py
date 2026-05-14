"""Phase 4C.2 — Product Cost Structures Router.

Endpoints:
  GET    /api/products/cost-structures
  GET    /api/products/cost-structures/{id}
  POST   /api/products/cost-structures
  PATCH  /api/products/cost-structures/{id}
  DELETE /api/products/cost-structures/{id}            (soft)
  POST   /api/products/cost-structures/{id}/preview    (test calculator)
  POST   /api/products/cost-structures/{id}/clone
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/products/cost-structures", tags=["Phase 4C - Product Cost Structures"])

cost_structures_col = db["product_cost_structures"]
vendor_categories_col = db["vendor_categories"]


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def _is_admin(u: dict) -> bool:
    return u.get("role") in ("admin", "admin_owner") or u.get("rbac_role") in ("admin", "admin_owner")


def _can_view(u: dict) -> bool:
    if _is_admin(u):
        return True
    perms = u.get("permissions") or []
    return any(p in perms for p in ["product_cost.view.all", "product_cost.manage.any", "vendor.view.all"])


def _can_manage(u: dict) -> bool:
    if _is_admin(u):
        return True
    return "product_cost.manage.any" in (u.get("permissions") or [])


def _clean(d: dict) -> dict:
    if not d:
        return d
    d.pop("_id", None)
    for k in ("created_at", "updated_at", "effective_from", "effective_until", "deleted_at"):
        v = d.get(k)
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def _calculate_allocation(allocation: dict, service_price: float) -> float:
    """Returns the rupee amount for a single allocation."""
    if not allocation.get("is_active", True):
        return 0.0
    base_amount = float(service_price)
    if allocation.get("base") == "net_revenue":
        # Net = service_price minus all flat costs (simplification: use service_price for now)
        base_amount = float(service_price)
    payment_type = allocation.get("payment_type", "flat")
    amount = float(allocation.get("amount", 0) or 0)
    if payment_type == "percentage":
        return round(base_amount * amount / 100, 2)
    # flat / per_document / hourly → treat amount as direct rupee value
    return round(amount, 2)


def _compute_summary(struct: dict) -> dict:
    """Recomputes total_costs_typical, expected_margin, expected_margin_percentage."""
    sp = float(struct.get("service_price") or 0)
    total_costs = 0.0
    for a in struct.get("cost_allocations") or []:
        if a.get("is_optional"):
            continue  # exclude optional from "typical" estimate
        total_costs += _calculate_allocation(a, sp)
    margin = round(sp - total_costs, 2)
    margin_pct = round((margin / sp * 100), 2) if sp > 0 else 0
    return {
        "total_costs_typical": round(total_costs, 2),
        "expected_margin": margin,
        "expected_margin_percentage": margin_pct,
    }


# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────
class AllocationModel(BaseModel):
    allocation_id: Optional[str] = None
    vendor_category: str  # FK key in vendor_categories
    payment_type: str = "flat"  # flat | percentage | per_document | hourly
    amount: float = 0
    base: str = "service_price"  # service_price | net_revenue
    label: Optional[str] = None
    is_active: bool = True
    is_optional: bool = False
    conditions: Optional[Dict[str, Any]] = None
    auto_assign: bool = True


class SuccessBonusModel(BaseModel):
    milestone: str = "visa_approved"
    vendor_category: str
    bonus_amount: float = 0
    label: Optional[str] = None


class CostStructureCreate(BaseModel):
    product_name: str
    country: Optional[str] = ""
    visa_type: Optional[str] = ""
    service_price: float = Field(..., ge=0)
    government_fees: float = 0
    cost_allocations: List[AllocationModel] = []
    success_bonuses: List[SuccessBonusModel] = []
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class CostStructureUpdate(BaseModel):
    product_name: Optional[str] = None
    country: Optional[str] = None
    visa_type: Optional[str] = None
    service_price: Optional[float] = Field(None, ge=0)
    government_fees: Optional[float] = None
    cost_allocations: Optional[List[AllocationModel]] = None
    success_bonuses: Optional[List[SuccessBonusModel]] = None
    is_active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class PreviewRequest(BaseModel):
    service_price: Optional[float] = None  # Override; defaults to structure's service_price
    include_optional: bool = True
    include_bonuses: bool = True


# ──────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────
async def _validate_allocations(allocations: List[Dict[str, Any]]):
    """Ensure every vendor_category exists + active."""
    keys = {a["vendor_category"] for a in allocations}
    if not keys:
        return
    cursor = vendor_categories_col.find({"key": {"$in": list(keys)}, "is_active": True}, {"_id": 0, "key": 1})
    found = {c["key"] async for c in cursor}
    missing = keys - found
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown or inactive vendor categories: {sorted(missing)}")


# ══════════════════════════════════════════════════════════════
# LIST / GET / CREATE / UPDATE / DELETE
# ══════════════════════════════════════════════════════════════
@router.get("")
async def list_structures(current_user: dict = Depends(get_current_user)):
    if not _can_view(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    items = await cost_structures_col.find({"deleted_at": None}, {"_id": 0}).sort("product_name", 1).to_list(500)
    return {"structures": [_clean(i) for i in items], "count": len(items)}


@router.get("/{struct_id}")
async def get_structure(struct_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_view(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    s = await cost_structures_col.find_one({"id": struct_id}, {"_id": 0})
    if not s:
        raise HTTPException(status_code=404, detail="Cost structure not found")
    return _clean(s)


@router.post("")
async def create_structure(req: CostStructureCreate, current_user: dict = Depends(get_current_user)):
    if not _can_manage(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    allocations = [a.model_dump() for a in req.cost_allocations]
    for a in allocations:
        if not a.get("allocation_id"):
            a["allocation_id"] = str(uuid.uuid4())
    await _validate_allocations(allocations)

    bonuses = [b.model_dump() for b in req.success_bonuses]
    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        "product_name": req.product_name.strip(),
        "country": req.country or "",
        "visa_type": req.visa_type or "",
        "service_price": float(req.service_price),
        "government_fees": float(req.government_fees or 0),
        "cost_allocations": allocations,
        "success_bonuses": bonuses,
        "is_active": True,
        "effective_from": req.effective_from or now,
        "effective_until": req.effective_until,
        "is_system": False,
        "deleted_at": None,
        "created_at": now,
        "created_by": current_user["id"],
        "updated_at": now,
    }
    doc["computed"] = _compute_summary(doc)
    await cost_structures_col.insert_one(doc)
    return {"ok": True, "structure": _clean(doc)}


@router.patch("/{struct_id}")
async def update_structure(struct_id: str, req: CostStructureUpdate, current_user: dict = Depends(get_current_user)):
    if not _can_manage(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await cost_structures_col.find_one({"id": struct_id, "deleted_at": None}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Cost structure not found")

    update: Dict[str, Any] = {}
    body = req.model_dump(exclude_unset=True)
    if "cost_allocations" in body:
        allocations = body["cost_allocations"]
        for a in allocations:
            if not a.get("allocation_id"):
                a["allocation_id"] = str(uuid.uuid4())
        await _validate_allocations(allocations)
        update["cost_allocations"] = allocations
    for k in ("product_name", "country", "visa_type", "service_price", "government_fees", "success_bonuses", "is_active", "effective_from", "effective_until"):
        if k in body and body[k] is not None:
            update[k] = body[k]
    if not update:
        return {"ok": True, "no_change": True}

    # Recompute summary
    merged = {**existing, **update}
    update["computed"] = _compute_summary(merged)
    update["updated_at"] = datetime.now(timezone.utc)
    update["updated_by"] = current_user["id"]
    await cost_structures_col.update_one({"id": struct_id}, {"$set": update})
    return {"ok": True}


@router.delete("/{struct_id}")
async def delete_structure(struct_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_manage(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    res = await cost_structures_col.update_one(
        {"id": struct_id, "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc), "deleted_by": current_user["id"], "is_active": False}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cost structure not found")
    return {"ok": True, "deleted": True}


# ══════════════════════════════════════════════════════════════
# PREVIEW (test calculator)
# ══════════════════════════════════════════════════════════════
@router.post("/{struct_id}/preview")
async def preview_structure(struct_id: str, req: PreviewRequest, current_user: dict = Depends(get_current_user)):
    """Returns per-allocation breakdown for a given service_price (or structure default)."""
    if not _can_view(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    s = await cost_structures_col.find_one({"id": struct_id, "deleted_at": None}, {"_id": 0})
    if not s:
        raise HTTPException(status_code=404, detail="Cost structure not found")

    sp = float(req.service_price if req.service_price is not None else s["service_price"])
    breakdown = []
    total_required = 0.0
    total_optional = 0.0
    for a in s.get("cost_allocations") or []:
        amt = _calculate_allocation(a, sp)
        entry = {
            "allocation_id": a.get("allocation_id"),
            "vendor_category": a["vendor_category"],
            "label": a.get("label") or a["vendor_category"],
            "payment_type": a.get("payment_type"),
            "amount_input": a.get("amount"),
            "calculated_amount": amt,
            "is_optional": a.get("is_optional", False),
        }
        breakdown.append(entry)
        if a.get("is_optional"):
            total_optional += amt
        else:
            total_required += amt

    bonuses = []
    bonus_total = 0.0
    if req.include_bonuses:
        for b in s.get("success_bonuses") or []:
            bonuses.append(b)
            bonus_total += float(b.get("bonus_amount") or 0)

    total_costs = total_required + (total_optional if req.include_optional else 0)
    margin = round(sp - total_costs, 2)
    margin_pct = round((margin / sp * 100), 2) if sp > 0 else 0

    return {
        "service_price": sp,
        "government_fees_passthrough": float(s.get("government_fees") or 0),
        "breakdown": breakdown,
        "totals": {
            "required_costs": round(total_required, 2),
            "optional_costs": round(total_optional, 2),
            "total_costs": round(total_costs, 2),
            "bonus_potential": round(bonus_total, 2),
            "margin": margin,
            "margin_percentage": margin_pct,
        },
        "bonuses": bonuses,
    }


@router.post("/{struct_id}/clone")
async def clone_structure(struct_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_manage(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    src = await cost_structures_col.find_one({"id": struct_id, "deleted_at": None}, {"_id": 0})
    if not src:
        raise HTTPException(status_code=404, detail="Source structure not found")
    now = datetime.now(timezone.utc)
    new = dict(src)
    new["id"] = str(uuid.uuid4())
    new["product_name"] = f"{src['product_name']} (Copy)"
    new["is_system"] = False
    new["created_at"] = now
    new["updated_at"] = now
    new["created_by"] = current_user["id"]
    # Drop the unique 'key' to avoid index collision; new clone is custom (no system key)
    new.pop("key", None)
    # Regenerate allocation_ids so they're unique to the new structure
    for a in new.get("cost_allocations") or []:
        a["allocation_id"] = str(uuid.uuid4())
    await cost_structures_col.insert_one(new)
    return {"ok": True, "structure": _clean(new)}
