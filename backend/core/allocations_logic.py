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
    db, pre_assessments_col, users_col, notifications_col, cases_col, sales_col,
)

cost_structures_col = db["product_cost_structures"]
allocations_col = db["pa_cost_allocations"]
vendors_col = db["vendors"]


# ──────────────────────────────────────────────────────────────
# Matching
# ──────────────────────────────────────────────────────────────
async def find_matching_structure(pa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Look up the best matching active cost-config (Phase 4C unified products).

    Priority:
      1. Unified product (products collection) where cost_allocations exists — by:
         a) product_id → product
         b) product_name (case-insensitive)
         c) country + visa_type (case-insensitive)
      2. Legacy product_cost_structures collection (back-compat).
      3. None — caller skips allocations.

    The returned dict is normalized to the shape the rest of allocations_logic
    expects: {product_name, country, visa_type, service_price, cost_allocations, success_bonuses}.
    """
    # ── 1. Unified products lookup ──
    pid = pa.get("product_id")
    if pid:
        prod = await db["products"].find_one({"id": pid, "cost_allocations": {"$exists": True, "$ne": []}}, {"_id": 0})
        if prod:
            return _product_to_structure(prod)

    pname = pa.get("product_name") or pa.get("service_type")
    if pname:
        import re
        prod = await db["products"].find_one(
            {"name": {"$regex": f"^{re.escape(str(pname))}$", "$options": "i"},
             "cost_allocations": {"$exists": True, "$ne": []}},
            {"_id": 0},
        )
        if prod:
            return _product_to_structure(prod)

    country = pa.get("country")
    visa = pa.get("service_type")
    if country and visa:
        import re
        prod = await db["products"].find_one(
            {"country": country, "visa_type": {"$regex": f"^{re.escape(str(visa))}$", "$options": "i"},
            "cost_allocations": {"$exists": True, "$ne": []}},
            {"_id": 0},
        )
        if prod:
            return _product_to_structure(prod)

    # ── 2. Legacy product_cost_structures fallback ──
    if pid:
        prod = await db["products"].find_one({"id": pid}, {"_id": 0, "name": 1})
        if prod and prod.get("name"):
            s = await cost_structures_col.find_one(
                {"product_name": prod["name"], "is_active": True, "deleted_at": None},
                {"_id": 0},
            )
            if s:
                return s

    if pname:
        s = await cost_structures_col.find_one(
            {"product_name": {"$regex": f"^{pname}$", "$options": "i"}, "is_active": True, "deleted_at": None},
            {"_id": 0},
        )
        if s:
            return s

    if country and visa:
        s = await cost_structures_col.find_one(
            {"country": country, "visa_type": {"$regex": f"^{visa}$", "$options": "i"}, "is_active": True, "deleted_at": None},
            {"_id": 0},
        )
        if s:
            return s

    # ── 3. Default fallback if no structure found ──
    # Ensure every PA has standard allocations (Sales Commission & Case Manager)
    std_price = float(pa.get("proposal_net_agreement_value") or pa.get("proposal_fee") or pa.get("proposal_base_fee") or 0)
    return {
        "id": f"default_{str(pa.get('country') or 'global').lower()}",
        "product_id": pa.get("product_id"),
        "product_name": pa.get("product_name") or pa.get("service_type") or "Standard Service",
        "country": pa.get("country") or "",
        "visa_type": pa.get("service_type") or "",
        "service_price": std_price,
        "cost_allocations": [
            {
                "allocation_id": str(uuid.uuid4()),
                "vendor_category": "sales_commission",
                "payment_type": "percentage",
                "amount": 10.0,
                "rate": 10.0,
                "label": "Sales Commission (10%)",
                "is_active": True,
                "is_optional": False,
                "auto_assign": True,
            },
            {
                "allocation_id": str(uuid.uuid4()),
                "vendor_category": "case_manager",
                "payment_type": "flat",
                "amount": 10000.0,
                "rate": None,
                "label": "Case Manager Fee",
                "is_active": True,
                "is_optional": False,
                "auto_assign": True,
            },
        ],
        "success_bonuses": [],
        "default_currency": "INR",
        "is_active": True,
        "source": "auto_default",
    }


def _product_to_structure(prod: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a unified product doc to the cost-structure shape used downstream."""
    return {
        "id": prod.get("id"),
        "product_id": prod.get("id"),
        "product_name": prod.get("name"),
        "country": prod.get("country") or "",
        "visa_type": prod.get("visa_type") or "",
        "service_price": float(prod.get("service_price") or prod.get("base_fee") or 0),
        "cost_allocations": prod.get("cost_allocations") or [],
        "success_bonuses": prod.get("success_bonuses") or [],
        "default_currency": (prod.get("cost_structure_meta") or {}).get("default_currency", "INR"),
        "is_active": prod.get("status", "active") == "active",
        "source": "unified_product",
    }


# ──────────────────────────────────────────────────────────────
# Calculation
# ──────────────────────────────────────────────────────────────
def _calc_allocation(rate_or_amount: float, payment_type: str, revenue: float) -> float:
    if payment_type == "percentage":
        return round(float(revenue) * float(rate_or_amount) / 100, 2)
    return round(float(rate_or_amount), 2)


async def _auto_assign_vendor(category: str, pa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Returns {vendor_id, vendor_name, vendor_type} or None."""
    cat = (category or "").lower().strip()
    # sales_commission / sales / partner / internal_partner / external_partner → PA creator / partner
    if cat in ("sales_commission", "sales", "partner", "partner_commission", "internal_partner", "external_partner"):
        uid = pa.get("partner_id") or pa.get("created_by_user_id") or pa.get("sales_rep_id")
        if not uid and pa.get("id"):
            sale = await sales_col.find_one({"pre_assessment_id": pa["id"]}, {"_id": 0, "partner_id": 1})
            if sale:
                uid = sale.get("partner_id")
        if uid:
            u = await users_col.find_one({"id": uid}, {"_id": 0, "id": 1, "name": 1, "user_type": 1, "role": 1, "partner_type": 1, "is_internal": 1})
            if u:
                is_int = (u.get("role") != "partner" or u.get("user_type") == "internal" or u.get("partner_type") == "internal" or u.get("is_internal") is True)
                if cat == "internal_partner" and not is_int:
                    return None
                if cat == "external_partner" and is_int:
                    return None
                vtype = "internal" if is_int else "external"
                return {"vendor_id": u["id"], "vendor_name": u.get("name"), "vendor_type": vtype}

    # case_manager / cm → PA's assigned case manager or linked case manager
    if cat in ("case_manager", "cm"):
        cm_id = pa.get("case_manager_id") or pa.get("assigned_case_manager_id")
        if not cm_id and pa.get("id"):
            linked = await cases_col.find_one(
                {"$or": [{"pre_assessment_id": pa["id"]}, {"pa_id": pa["id"]}, {"id": pa.get("case_id")}]},
                {"_id": 0, "case_manager_id": 1, "case_manager_name": 1}
            )
            if linked:
                cm_id = linked.get("case_manager_id")
        if not cm_id:
            cm_user = await users_col.find_one({"$or": [{"role": "case_manager"}, {"rbac_role": "case_manager"}], "status": "active"}, {"_id": 0, "id": 1, "name": 1})
            if cm_user:
                cm_id = cm_user["id"]
        if cm_id:
            u = await users_col.find_one({"id": cm_id}, {"_id": 0, "id": 1, "name": 1, "user_type": 1, "role": 1})
            if u:
                return {"vendor_id": u["id"], "vendor_name": u.get("name"), "vendor_type": "internal"}

    # For external categories, leave unassigned (admin manually assigns)
    return None


def _compute_summary(allocations: List[Dict[str, Any]], total_revenue: float, amount_received: float = 0.0) -> Dict[str, Any]:
    allocated = sum(float(a.get("total_amount") or 0) for a in allocations if not a.get("is_optional") or a.get("vendor_id"))
    full_allocated = sum(float(a.get("full_amount") or a.get("total_amount") or 0) for a in allocations if not a.get("is_optional") or a.get("vendor_id"))
    paid = sum(float(a.get("total_amount") or 0) for a in allocations if a.get("status") == "paid")
    pending = sum(float(a.get("total_amount") or 0) for a in allocations if a.get("status") in ("pending", "approved", "unassigned"))
    margin = max(0, total_revenue - full_allocated)
    return {
        "total_allocated": round(allocated, 2),
        "full_total_allocated": round(full_allocated, 2),
        "total_paid": round(paid, 2),
        "total_pending": round(pending, 2),
        "amount_received": round(amount_received, 2),
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

    # Overall payment candidate (proposal_total_fee, proposal_fee, final_amount, etc.)
    revenue_candidate = (
        pa.get("proposal_total_fee") or 
        pa.get("proposal_fee") or 
        pa.get("final_amount") or 
        pa.get("final_fee") or 
        pa.get("total_amount") or
        pa.get("proposal_base_fee") or
        pa.get("proposal_discounted_total") or
        pa.get("proposal_net_agreement_value") or 
        pa.get("net_agreement_value")
    )
    if not revenue_candidate and pa.get("id"):
        sale = await sales_col.find_one(
            {"$or": [{"pre_assessment_id": pa["id"]}, {"id": pa.get("sale_id")}]},
            {"_id": 0, "total_amount": 1, "fee_amount": 1, "amount_received": 1, "paid_amount": 1, "net_agreement_value": 1}
        )
        if sale:
            revenue_candidate = sale.get("total_amount") or sale.get("fee_amount") or sale.get("paid_amount") or sale.get("amount_received") or sale.get("net_agreement_value")
    if not revenue_candidate and structure:
        revenue_candidate = structure.get("service_price") or structure.get("base_fee") or 0

    total_revenue = float(revenue if revenue is not None else (revenue_candidate or 0))

    # Actual client payment received for this proposal
    paid_amount = float(pa.get("proposal_amount_paid") or pa.get("amount_received") or 0)
    if paid_amount <= 0 and pa.get("id"):
        sale_for_paid = await sales_col.find_one(
            {"$or": [{"pre_assessment_id": pa["id"]}, {"id": pa.get("sale_id")}]},
            {"_id": 0, "amount_received": 1, "paid_amount": 1}
        )
        if sale_for_paid:
            paid_amount = float(sale_for_paid.get("amount_received") or sale_for_paid.get("paid_amount") or 0)
    if paid_amount <= 0 and pa.get("stage") in ("proposal_paid", "case_created"):
        paid_amount = total_revenue

    payment_ratio = min(1.0, round(paid_amount / total_revenue, 4)) if total_revenue > 0 else 1.0

    existing = await allocations_col.find_one({"pa_id": pa["id"]}, {"_id": 0})
    existing_map: Dict[str, Dict[str, Any]] = {}
    if existing:
        for a in existing.get("allocations") or []:
            # Index by vendor_category since structure allocation_ids may regenerate
            existing_map[a["vendor_category"]] = a

    new_allocations: List[Dict[str, Any]] = []
    sales_comm_rate_resolved = 0.0

    for spec in structure.get("cost_allocations") or []:
        if not spec.get("is_active", True):
            continue
        
        cat = str(spec.get("vendor_category") or "").strip().lower()
        ptype = spec.get("payment_type", "flat")
        if ptype == "percentage":
            raw_rate = spec.get("rate") if (spec.get("rate") is not None and str(spec.get("rate")) != "") else spec.get("amount", 0)
        else:
            raw_rate = spec.get("amount") if (spec.get("amount") is not None and str(spec.get("amount")) != "") else spec.get("rate", 0)
        
        try:
            raw_rate = float(raw_rate or 0)
        except (ValueError, TypeError):
            raw_rate = 0.0

        # Automatic calculation for sales/partner commission if rate not explicitly > 0
        if cat in ("sales_commission", "sales", "partner", "partner_commission", "internal_partner", "external_partner"):
            if raw_rate <= 0:
                partner_id = pa.get("partner_id") or pa.get("created_by_user_id") or pa.get("sales_rep_id")
                # 1. Custom partner-product commission
                if partner_id and pa.get("product_id"):
                    custom = await db["partner_product_commissions"].find_one(
                        {"partner_id": partner_id, "product_id": pa.get("product_id")}, {"_id": 0, "commission_rate": 1}
                    )
                    if custom and float(custom.get("commission_rate") or 0) > 0:
                        raw_rate = float(custom["commission_rate"])
                # 2. Product-level commission rate
                if raw_rate <= 0 and pa.get("product_id"):
                    p_doc = await db["products"].find_one({"id": pa.get("product_id")}, {"_id": 0, "commission_rate": 1})
                    if p_doc and float(p_doc.get("commission_rate") or 0) > 0:
                        raw_rate = float(p_doc["commission_rate"])
                # 3. Partner user profile rate
                if raw_rate <= 0 and partner_id:
                    part_user = await users_col.find_one({"id": partner_id}, {"_id": 0, "commission_rate": 1, "commission_mode": 1})
                    if part_user and part_user.get("commission_mode") == "flat" and part_user.get("commission_rate") is not None:
                        raw_rate = float(part_user.get("commission_rate") or 0)
                    elif part_user and float(part_user.get("commission_rate") or 0) > 0:
                        raw_rate = float(part_user["commission_rate"])
                # 4. Commission slab rate based on revenue
                if raw_rate <= 0:
                    try:
                        from core.commission_logic import get_active_slabs, _match_slab
                        slabs = await get_active_slabs()
                        slab = _match_slab(total_revenue, slabs)
                        if slab and float(slab.get("rate_pct") or 0) > 0:
                            raw_rate = float(slab["rate_pct"])
                    except Exception:
                        pass
                # 5. Default partner commission rate (10.0%)
                if raw_rate <= 0:
                    raw_rate = 10.0
                ptype = "percentage"
            sales_comm_rate_resolved = raw_rate

        # Automatic calculation for case manager if amount not explicitly > 0
        elif cat in ("case_manager", "cm"):
            if raw_rate <= 0:
                country = str(pa.get("country") or structure.get("country") or "").lower()
                if "aus" in country:
                    raw_rate = 8000.0
                elif "usa" in country or "us" == country:
                    raw_rate = 15000.0
                elif "uk" in country:
                    raw_rate = 10000.0
                elif "can" in country:
                    raw_rate = 10000.0
                else:
                    raw_rate = 10000.0
                ptype = "flat"

        # Proportional calculation based on client payment received
        full_calc = _calc_allocation(raw_rate, ptype, total_revenue)
        if paid_amount >= total_revenue or total_revenue <= 0:
            calc = full_calc
        elif paid_amount > 0:
            if ptype == "percentage":
                calc = _calc_allocation(raw_rate, "percentage", paid_amount)
            else:
                calc = round(full_calc * payment_ratio, 2)
        else:
            calc = 0.0

        # Preserve existing assignment/status if present, otherwise auto-assign
        vcat = spec.get("vendor_category")
        prev = existing_map.get(vcat) or existing_map.get(cat) or {}
        if not prev:
            if cat in ("sales_commission", "sales", "partner", "partner_commission"):
                for k in ("sales_commission", "sales", "partner", "partner_commission"):
                    if k in existing_map:
                        prev = existing_map[k]
                        break
            elif cat in ("case_manager", "cm"):
                for k in ("case_manager", "cm"):
                    if k in existing_map:
                        prev = existing_map[k]
                        break

        assignment = {
            "vendor_id": prev.get("vendor_id"),
            "vendor_name": prev.get("vendor_name"),
            "vendor_type": prev.get("vendor_type"),
        }
        if not assignment["vendor_id"]:
            # Try auto-assign on first run or when newly assigned
            auto = await _auto_assign_vendor(spec["vendor_category"], pa)
            if auto:
                assignment = auto

        bonus_amount = float(prev.get("bonus_amount") or 0)
        total_amount = round(calc + bonus_amount, 2)
        full_total_amount = round(full_calc + bonus_amount, 2)
        status = prev.get("status")
        if not status or status == "unassigned":
            status = "unassigned" if not assignment.get("vendor_id") else "pending"

        # Label fallback
        label = spec.get("label") or vcat
        if label.lower() in ("sales", "sales_commission", "sales commission"):
            rate_str = f" ({raw_rate:g}%)" if ptype == "percentage" and raw_rate > 0 else ""
            label = f"Sales Commission{rate_str}"
        elif label.lower() in ("cm", "case_manager", "case manager"):
            label = "Case Manager Fee"

        new_allocations.append({
            "allocation_id": spec.get("allocation_id") or str(uuid.uuid4()),
            "vendor_category": vcat,
            "label": label,
            "payment_type": ptype,
            "base_amount": raw_rate,
            "rate": raw_rate if ptype == "percentage" else None,
            "full_amount": full_total_amount,
            "calculated_amount": calc,
            "bonus_amount": bonus_amount,
            "total_amount": total_amount,
            "amount_received": round(paid_amount, 2),
            "paid_ratio": round(payment_ratio * 100, 1),
            "is_optional": bool(spec.get("is_optional", False)),
            **assignment,
            "status": status,
            "assigned_at": prev.get("assigned_at"),
            "approved_at": prev.get("approved_at"),
            "paid_at": prev.get("paid_at"),
            "payment_reference": prev.get("payment_reference"),
            "notes": prev.get("notes") or "",
        })

    # Ensure sales_commission is present if missing from structure
    has_sales = any(str(a.get("vendor_category") or "").lower() in (
        "sales_commission", "sales", "partner", "partner_commission",
        "internal_partner", "external_partner", "internal_salesperson", "external_salesperson"
    ) for a in new_allocations)
    if not has_sales:
        partner_id = pa.get("partner_id") or pa.get("created_by_user_id") or pa.get("sales_rep_id")
        raw_rate = 10.0
        if partner_id:
            part_user = await users_col.find_one({"id": partner_id}, {"_id": 0, "commission_rate": 1, "commission_mode": 1})
            if part_user and part_user.get("commission_rate") is not None and str(part_user.get("commission_rate")).strip() != "":
                raw_rate = float(part_user["commission_rate"])
        full_calc = _calc_allocation(raw_rate, "percentage", total_revenue)
        if paid_amount >= total_revenue or total_revenue <= 0:
            calc = full_calc
        elif paid_amount > 0:
            calc = _calc_allocation(raw_rate, "percentage", paid_amount)
        else:
            calc = 0.0
        auto = await _auto_assign_vendor("sales_commission", pa)
        new_allocations.insert(0, {
            "allocation_id": str(uuid.uuid4()),
            "vendor_category": "sales_commission",
            "label": f"Sales Commission ({raw_rate:g}%)",
            "payment_type": "percentage",
            "base_amount": raw_rate,
            "rate": raw_rate,
            "full_amount": full_calc,
            "calculated_amount": calc,
            "bonus_amount": 0.0,
            "total_amount": calc,
            "amount_received": round(paid_amount, 2),
            "paid_ratio": round(payment_ratio * 100, 1),
            "is_optional": False,
            **(auto or {"vendor_id": None, "vendor_name": None, "vendor_type": None}),
            "status": "pending" if auto and auto.get("vendor_id") else "unassigned",
            "assigned_at": None, "approved_at": None, "paid_at": None,
            "payment_reference": None, "notes": "",
        })
        sales_comm_rate_resolved = raw_rate

    now = datetime.now(timezone.utc)
    summary = _compute_summary(new_allocations, total_revenue, paid_amount)

    doc = {
        "pa_id": pa["id"],
        "pa_number": pa.get("pa_number"),
        "client_name": pa.get("client_name"),
        "product_id": pa.get("product_id"),
        "cost_structure_id": structure["id"],
        "cost_structure_name": structure["product_name"],
        "total_revenue": round(total_revenue, 2),
        "amount_received": round(paid_amount, 2),
        "payment_ratio": round(payment_ratio * 100, 1),
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

    # Synchronize linked sale commission in sales_col
    try:
        sale_id = pa.get("sale_id")
        if not sale_id and pa.get("id"):
            sale_doc = await sales_col.find_one(
                {"$or": [{"pre_assessment_id": pa["id"]}, {"id": pa.get("sale_id")}]},
                {"_id": 0, "id": 1}
            )
            if sale_doc:
                sale_id = sale_doc.get("id")
        if sale_id:
            sale_doc = await sales_col.find_one({"id": sale_id}, {"_id": 0})
            if sale_doc:
                effective_rate = sales_comm_rate_resolved
                if effective_rate <= 0:
                    effective_rate = float(sale_doc.get("commission_rate") or 10.0)
                received = float(sale_doc.get("amount_received") or pa.get("proposal_amount_paid") or pa.get("amount_received") or 0)
                comm_amt = round(received * (effective_rate / 100), 2)
                await sales_col.update_one(
                    {"id": sale_id},
                    {"$set": {
                        "commission_rate": effective_rate,
                        "commission_amount": comm_amt,
                        "net_agreement_value": pa.get("proposal_net_agreement_value") or sale_doc.get("net_agreement_value") or total_revenue,
                    }}
                )
    except Exception:
        pass

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
