"""Phase 4C.3 — Auto-Allocation Engine.

Pure logic + persistence:
  - Match a PA to a product_cost_structure (by product_id → product_name → country+visa_type)
  - Calculate per-allocation rupee amounts from total revenue
  - Auto-assign known vendors (sales person, case manager)
  - Mark others as unassigned
  - Apply success bonuses on visa_approved milestone
  - 50% clawback on refund/cancellation

Triggered from:
  - PA admin_approve_final  (stage → case_created)
  - sales.approve_sale       (direct-sale revenue path)
  - vendor assignment        (admin manually assigns tutor/lawyer)
  - visa_approved milestone  (applies bonuses)
  - refund / cancellation    (clawback)
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from core.database import (
    db, pre_assessments_col, users_col, notifications_col,
)

cost_structures_col = db["product_cost_structures"]
allocations_col = db["pa_cost_allocations"]
vendors_col = db["vendors"]


# ──────────────────────────────────────────────────────────────
# Matching
# ──────────────────────────────────────────────────────────────
async def find_matching_structure(pa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Look up the best matching active cost structure for a PA.
    Strategy:
      1. By product_id (if PA links to product)
      2. By exact product_name match
      3. By country + visa_type loose match
      4. Return None → caller skips allocations
    """
    pid = pa.get("product_id")
    if pid:
        prod = await db["products"].find_one({"id": pid}, {"_id": 0, "name": 1})
        if prod and prod.get("name"):
            s = await cost_structures_col.find_one(
                {"product_name": prod["name"], "is_active": True, "deleted_at": None},
                {"_id": 0},
            )
            if s:
                return s

    pname = pa.get("product_name") or pa.get("service_type")
    if pname:
        s = await cost_structures_col.find_one(
            {"product_name": {"$regex": f"^{pname}$", "$options": "i"}, "is_active": True, "deleted_at": None},
            {"_id": 0},
        )
        if s:
            return s

    country = pa.get("country")
    visa = pa.get("service_type")
    if country and visa:
        s = await cost_structures_col.find_one(
            {"country": country, "visa_type": {"$regex": f"^{visa}$", "$options": "i"}, "is_active": True, "deleted_at": None},
            {"_id": 0},
        )
        if s:
            return s
    return None


# ──────────────────────────────────────────────────────────────
# Calculation
# ──────────────────────────────────────────────────────────────
def _calc_allocation(rate_or_amount: float, payment_type: str, revenue: float) -> float:
    if payment_type == "percentage":
        return round(float(revenue) * float(rate_or_amount) / 100, 2)
    return round(float(rate_or_amount), 2)


async def _auto_assign_vendor(category: str, pa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Returns {vendor_id, vendor_name, vendor_type} or None."""
    # sales_commission → PA creator
    if category == "sales_commission":
        uid = pa.get("created_by_user_id") or pa.get("partner_id")
        if uid:
            u = await users_col.find_one({"id": uid}, {"_id": 0, "id": 1, "name": 1, "user_type": 1})
            if u:
                return {"vendor_id": u["id"], "vendor_name": u.get("name"), "vendor_type": u.get("user_type", "internal")}

    # case_manager → PA's assigned case manager
    if category == "case_manager":
        cm_id = pa.get("case_manager_id") or pa.get("assigned_case_manager_id")
        if cm_id:
            u = await users_col.find_one({"id": cm_id}, {"_id": 0, "id": 1, "name": 1, "user_type": 1})
            if u:
                return {"vendor_id": u["id"], "vendor_name": u.get("name"), "vendor_type": "internal"}

    # For external categories, leave unassigned (admin manually assigns)
    return None


def _compute_summary(allocations: List[Dict[str, Any]], total_revenue: float) -> Dict[str, Any]:
    allocated = sum(float(a.get("total_amount") or 0) for a in allocations if not a.get("is_optional") or a.get("vendor_id"))
    paid = sum(float(a.get("total_amount") or 0) for a in allocations if a.get("status") == "paid")
    pending = sum(float(a.get("total_amount") or 0) for a in allocations if a.get("status") in ("pending", "approved", "unassigned"))
    margin = max(0, total_revenue - allocated)
    return {
        "total_allocated": round(allocated, 2),
        "total_paid": round(paid, 2),
        "total_pending": round(pending, 2),
        "company_margin": round(margin, 2),
        "company_margin_percentage": round((margin / total_revenue * 100), 2) if total_revenue > 0 else 0,
    }


# ──────────────────────────────────────────────────────────────
# Build / Upsert allocations doc
# ──────────────────────────────────────────────────────────────
async def build_allocations_for_pa(pa: Dict[str, Any], revenue: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Idempotent: rebuilds allocation breakdown for a PA based on its current cost structure.
    Preserves existing assignment + status flags (vendor_id, status, paid_at, …) when allocation_id matches.
    """
    structure = await find_matching_structure(pa)
    if not structure:
        return None

    total_revenue = float(revenue if revenue is not None else (pa.get("proposal_fee") or pa.get("final_amount") or structure.get("service_price") or 0))

    existing = await allocations_col.find_one({"pa_id": pa["id"]}, {"_id": 0})
    existing_map: Dict[str, Dict[str, Any]] = {}
    if existing:
        for a in existing.get("allocations") or []:
            # Index by vendor_category since structure allocation_ids may regenerate
            existing_map[a["vendor_category"]] = a

    new_allocations: List[Dict[str, Any]] = []
    for spec in structure.get("cost_allocations") or []:
        if not spec.get("is_active", True):
            continue
        calc = _calc_allocation(spec.get("amount", 0), spec.get("payment_type", "flat"), total_revenue)

        # Preserve existing assignment/status if present
        prev = existing_map.get(spec["vendor_category"]) or {}
        assignment = {
            "vendor_id": prev.get("vendor_id"),
            "vendor_name": prev.get("vendor_name"),
            "vendor_type": prev.get("vendor_type"),
        }
        if not assignment["vendor_id"]:
            # Try auto-assign on first run
            auto = await _auto_assign_vendor(spec["vendor_category"], pa)
            if auto:
                assignment = auto

        bonus_amount = float(prev.get("bonus_amount") or 0)
        total_amount = round(calc + bonus_amount, 2)
        status = prev.get("status")
        if not status:
            status = "unassigned" if not assignment.get("vendor_id") else "pending"

        new_allocations.append({
            "allocation_id": spec.get("allocation_id") or str(uuid.uuid4()),
            "vendor_category": spec["vendor_category"],
            "label": spec.get("label") or spec["vendor_category"],
            "payment_type": spec.get("payment_type", "flat"),
            "base_amount": float(spec.get("amount", 0)),
            "rate": float(spec.get("amount", 0)) if spec.get("payment_type") == "percentage" else None,
            "calculated_amount": calc,
            "bonus_amount": bonus_amount,
            "total_amount": total_amount,
            "is_optional": bool(spec.get("is_optional", False)),
            **assignment,
            "status": status,
            "assigned_at": prev.get("assigned_at"),
            "approved_at": prev.get("approved_at"),
            "paid_at": prev.get("paid_at"),
            "payment_reference": prev.get("payment_reference"),
            "notes": prev.get("notes") or "",
        })

    now = datetime.now(timezone.utc)
    summary = _compute_summary(new_allocations, total_revenue)

    doc = {
        "pa_id": pa["id"],
        "pa_number": pa.get("pa_number"),
        "client_name": pa.get("client_name"),
        "product_id": pa.get("product_id"),
        "cost_structure_id": structure["id"],
        "cost_structure_name": structure["product_name"],
        "total_revenue": round(total_revenue, 2),
        "allocations": new_allocations,
        "summary": summary,
        "milestones": existing.get("milestones") if existing else {"visa_approved": False, "refunded": False},
        "last_recalculated_at": now,
        "updated_at": now,
    }
    if existing:
        await allocations_col.update_one({"pa_id": pa["id"]}, {"$set": doc})
        doc["_id"] = existing.get("_id")
    else:
        doc["id"] = str(uuid.uuid4())
        doc["created_at"] = now
        await allocations_col.insert_one(doc)

    doc.pop("_id", None)
    return doc


async def get_allocations_for_pa(pa_id: str) -> Optional[Dict[str, Any]]:
    doc = await allocations_col.find_one({"pa_id": pa_id}, {"_id": 0})
    return doc


# ──────────────────────────────────────────────────────────────
# Milestones: visa_approved bonus / refund clawback
# ──────────────────────────────────────────────────────────────
async def apply_visa_approved_bonuses(pa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the linked cost structure, add success_bonuses to matching allocations."""
    doc = await allocations_col.find_one({"pa_id": pa["id"]}, {"_id": 0})
    if not doc:
        return None
    if (doc.get("milestones") or {}).get("visa_approved"):
        return doc  # already applied

    struct = await cost_structures_col.find_one({"id": doc["cost_structure_id"]}, {"_id": 0, "success_bonuses": 1})
    bonuses = (struct or {}).get("success_bonuses") or []

    by_cat: Dict[str, float] = {}
    for b in bonuses:
        if b.get("milestone") == "visa_approved":
            by_cat[b["vendor_category"]] = by_cat.get(b["vendor_category"], 0) + float(b.get("bonus_amount") or 0)

    updated = []
    for a in doc["allocations"]:
        bonus = by_cat.get(a["vendor_category"], 0)
        if bonus > 0:
            a["bonus_amount"] = round(float(a.get("bonus_amount") or 0) + bonus, 2)
            a["total_amount"] = round(float(a["calculated_amount"]) + a["bonus_amount"], 2)
        updated.append(a)

    doc["allocations"] = updated
    doc["summary"] = _compute_summary(updated, doc["total_revenue"])
    doc["milestones"] = {**(doc.get("milestones") or {}), "visa_approved": True, "visa_approved_at": datetime.now(timezone.utc).isoformat()}
    doc["updated_at"] = datetime.now(timezone.utc)
    await allocations_col.update_one({"pa_id": pa["id"]}, {"$set": doc})
    return doc


async def apply_refund_clawback(pa_id: str, recovery_rate: float = 0.5) -> Optional[Dict[str, Any]]:
    """Default 50% clawback per approved spec. Reduces total_amount on all allocations except those already 'paid'."""
    doc = await allocations_col.find_one({"pa_id": pa_id}, {"_id": 0})
    if not doc:
        return None
    if (doc.get("milestones") or {}).get("refunded"):
        return doc

    updated = []
    for a in doc["allocations"]:
        if a.get("status") == "paid":
            # Cannot claw back already-paid; admin marks dispute manually
            updated.append(a)
            continue
        a["calculated_amount"] = round(float(a["calculated_amount"]) * (1 - recovery_rate), 2)
        a["bonus_amount"] = round(float(a.get("bonus_amount") or 0) * (1 - recovery_rate), 2)
        a["total_amount"] = round(a["calculated_amount"] + a["bonus_amount"], 2)
        a["clawback_applied"] = True
        updated.append(a)

    doc["allocations"] = updated
    doc["summary"] = _compute_summary(updated, doc["total_revenue"])
    doc["milestones"] = {**(doc.get("milestones") or {}), "refunded": True, "refunded_at": datetime.now(timezone.utc).isoformat(), "clawback_rate": recovery_rate}
    doc["updated_at"] = datetime.now(timezone.utc)
    await allocations_col.update_one({"pa_id": pa_id}, {"$set": doc})
    return doc


# ──────────────────────────────────────────────────────────────
# Manual operations
# ──────────────────────────────────────────────────────────────
async def assign_vendor(pa_id: str, allocation_id: str, vendor_id: str, current_user_id: str) -> Dict[str, Any]:
    doc = await allocations_col.find_one({"pa_id": pa_id}, {"_id": 0})
    if not doc:
        raise ValueError("No allocations for this PA")
    vendor = await vendors_col.find_one({"id": vendor_id, "status": "active"}, {"_id": 0, "id": 1, "name": 1, "vendor_type": 1, "user_id": 1})
    if not vendor:
        raise ValueError("Vendor not found or inactive")

    found = False
    for a in doc["allocations"]:
        if a["allocation_id"] == allocation_id:
            a["vendor_id"] = vendor.get("user_id") or vendor["id"]
            a["vendor_name"] = vendor["name"]
            a["vendor_type"] = vendor.get("vendor_type", "external")
            a["vendor_master_id"] = vendor["id"]
            a["assigned_at"] = datetime.now(timezone.utc).isoformat()
            a["status"] = "pending"
            found = True
            break
    if not found:
        raise ValueError("Allocation not found")

    doc["summary"] = _compute_summary(doc["allocations"], doc["total_revenue"])
    doc["updated_at"] = datetime.now(timezone.utc)
    await allocations_col.update_one({"pa_id": pa_id}, {"$set": doc})

    # Notify vendor (if linked to a user_id)
    target_user_id = vendor.get("user_id")
    if target_user_id:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": target_user_id,
            "title": f"New Assignment — {doc.get('client_name')}",
            "message": f"You've been assigned as {a['label']} on case {doc.get('pa_number')} (₹{a['total_amount']:.0f})",
            "type": "vendor_assignment",
            "read": False,
            "link": "/vendor/dashboard",
            "metadata": {"pa_id": pa_id, "allocation_id": allocation_id},
            "created_at": datetime.now(timezone.utc),
        })
    return doc


async def set_allocation_status(pa_id: str, allocation_id: str, status: str, by_user_id: str, payment_ref: Optional[str] = None) -> Dict[str, Any]:
    """status in: approved | paid | disputed"""
    if status not in ("approved", "paid", "disputed"):
        raise ValueError(f"Invalid status: {status}")
    doc = await allocations_col.find_one({"pa_id": pa_id}, {"_id": 0})
    if not doc:
        raise ValueError("No allocations for this PA")
    now = datetime.now(timezone.utc)
    found = False
    for a in doc["allocations"]:
        if a["allocation_id"] == allocation_id:
            if not a.get("vendor_id") and status != "disputed":
                raise ValueError("Cannot approve/pay an unassigned allocation")
            a["status"] = status
            if status == "approved":
                a["approved_at"] = now.isoformat()
                a["approved_by"] = by_user_id
            if status == "paid":
                a["paid_at"] = now.isoformat()
                a["paid_by"] = by_user_id
                a["payment_reference"] = payment_ref
            found = True
            break
    if not found:
        raise ValueError("Allocation not found")
    doc["summary"] = _compute_summary(doc["allocations"], doc["total_revenue"])
    doc["updated_at"] = now
    await allocations_col.update_one({"pa_id": pa_id}, {"$set": doc})
    return doc
