"""Phase 4C.4 — Sales Commission Slab Engine.

Concept:
  Sales executives earn commission based on tiered slabs evaluated on their
  current-period revenue achievement. When a PA reaches `case_created`, an
  entry is auto-created against the rep at the CURRENT slab rate. At month-end
  (or on-demand), entries can be RECONCILED — re-evaluating slab tier based on
  final achieved revenue.

Slab example:
  Bronze:  ₹0      ─ ₹5,00,000      @ 5%
  Silver:  ₹5L     ─ ₹15,00,000     @ 7%
  Gold:    ₹15L+                     @ 10%

DB collections:
  - sales_commission_slabs:   { id, key, name, min_revenue, max_revenue, rate_pct, is_active }
  - sales_commission_entries: { id, user_id, pa_id, period, revenue, rate_pct,
                                slab_name, commission_amount, status, applied_at, ...}
  - sales_commission_config:  single-doc config (currency, reconciliation_day, etc.)

Status flow: pending → approved → paid  (or → reversed on refund)
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.database import db, users_col

slabs_col = db["sales_commission_slabs"]
entries_col = db["sales_commission_entries"]
config_col = db["sales_commission_config"]


SALES_ROLES = {"sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "partner"}


def _period_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return d.strftime("%Y-%m")


def _is_sales_user(user: Dict[str, Any]) -> bool:
    if not user:
        return False
    # If explicitly deactivated from commission, exclude
    if user.get("is_commission_active") is False:
        return False
    rbac = user.get("rbac_role") or ""
    role = user.get("role") or ""
    all_sales_roles = SALES_ROLES | {"sales", "sales_rep", "sales_person", "internal_salesperson"}
    return rbac in all_sales_roles or role in all_sales_roles


# ──────────────────────────────────────────────────────────────
# Default seed
# ──────────────────────────────────────────────────────────────
DEFAULT_SLABS = [
    {"key": "bronze", "name": "Bronze", "min_revenue": 0,        "max_revenue": 500000,  "rate_pct": 5.0,  "color": "amber"},
    {"key": "silver", "name": "Silver", "min_revenue": 500000,   "max_revenue": 1500000, "rate_pct": 7.0,  "color": "slate"},
    {"key": "gold",   "name": "Gold",   "min_revenue": 1500000,  "max_revenue": None,    "rate_pct": 10.0, "color": "yellow"},
]


async def ensure_default_slabs() -> int:
    """Seed default slabs only if collection is empty. Returns count seeded."""
    count = await slabs_col.count_documents({})
    if count > 0:
        return 0
    now = datetime.now(timezone.utc)
    for s in DEFAULT_SLABS:
        await slabs_col.insert_one({
            "id": str(uuid.uuid4()),
            **s,
            "is_active": True,
            "is_system": True,
            "created_at": now,
        })
    # Seed config
    await config_col.update_one(
        {"key": "main"},
        {"$setOnInsert": {
            "key": "main",
            "currency": "INR",
            "reconciliation_day": 5,  # 5th of next month
            "auto_reconcile": False,
            "created_at": now,
        }},
        upsert=True,
    )
    return len(DEFAULT_SLABS)


# ──────────────────────────────────────────────────────────────
# Slab matching
# ──────────────────────────────────────────────────────────────
async def get_active_slabs() -> List[Dict[str, Any]]:
    items = await slabs_col.find({"is_active": True}, {"_id": 0}).sort("min_revenue", 1).to_list(50)
    return items


def _match_slab(achieved: float, slabs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Returns the highest slab whose min_revenue ≤ achieved AND (max_revenue is None OR achieved < max)."""
    matched = None
    for s in slabs:
        mn = float(s.get("min_revenue") or 0)
        mx = s.get("max_revenue")
        if achieved >= mn and (mx is None or achieved < float(mx)):
            matched = s
    if matched:
        return matched
    # If nothing matched (achieved < first slab min), use first slab
    return slabs[0] if slabs else None


# ──────────────────────────────────────────────────────────────
# Aggregate achieved revenue for a user this period
# ──────────────────────────────────────────────────────────────
async def get_period_revenue(user_id: str, period: Optional[str] = None) -> float:
    """Sum of `revenue` across this user's existing entries in the period."""
    period = period or _period_key()
    pipeline = [
        {"$match": {"user_id": user_id, "period": period, "status": {"$ne": "reversed"}}},
        {"$group": {"_id": None, "total": {"$sum": "$revenue"}}},
    ]
    cursor = entries_col.aggregate(pipeline)
    rows = await cursor.to_list(1)
    return float(rows[0]["total"]) if rows else 0.0


def _resolve_rate(user: Dict[str, Any], achieved_after: float, slabs: List[Dict[str, Any]]):
    """Determines rate, slab name, and mode based on individual user config vs global slabs."""
    comm_mode = user.get("commission_mode", "slab")
    custom_rate = user.get("commission_rate")
    
    # If user has individual flat rate configured
    if comm_mode == "flat" and custom_rate is not None and float(custom_rate) > 0:
        rate = float(custom_rate)
        return {
            "rate_mode": "flat",
            "rate_pct": rate,
            "slab_key": "individual_flat",
            "slab_name": f"Individual Rate ({rate}%)",
            "matched_slab": None,
        }
    
    # Otherwise use tiered slabs
    slab = _match_slab(achieved_after, slabs)
    if slab:
        return {
            "rate_mode": "slab",
            "rate_pct": float(slab["rate_pct"]),
            "slab_key": slab.get("key"),
            "slab_name": slab.get("name"),
            "matched_slab": slab,
        }
    return None


# ──────────────────────────────────────────────────────────────
# Apply commission on a PA reaching case_created
# ──────────────────────────────────────────────────────────────
async def apply_commission_for_pa(pa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Idempotent — returns the created/existing entry or None if not applicable."""
    creator_id = pa.get("created_by_user_id") or pa.get("partner_id")
    if not creator_id:
        return None

    user = await users_col.find_one(
        {"id": creator_id},
        {"_id": 0, "id": 1, "name": 1, "role": 1, "rbac_role": 1, "email": 1, "commission_mode": 1, "commission_rate": 1, "is_commission_active": 1}
    )
    if not user or not _is_sales_user(user):
        return None

    # Idempotency: skip if entry already exists for this PA
    existing = await entries_col.find_one({"$or": [{"pa_id": pa["id"]}, {"source_type": "pa", "source_id": pa["id"]}]}, {"_id": 0})
    if existing:
        return existing

    revenue = float(pa.get("proposal_fee") or pa.get("final_amount") or 0)
    if revenue <= 0:
        return None

    period = _period_key()
    achieved_before = await get_period_revenue(creator_id, period)
    achieved_after = achieved_before + revenue

    slabs = await get_active_slabs()
    if not slabs:
        await ensure_default_slabs()
        slabs = await get_active_slabs()

    resolved = _resolve_rate(user, achieved_after, slabs)
    if not resolved:
        return None

    rate = resolved["rate_pct"]
    commission = round(revenue * rate / 100, 2)
    now = datetime.now(timezone.utc)

    entry = {
        "id": str(uuid.uuid4()),
        "user_id": creator_id,
        "user_name": user.get("name"),
        "user_email": user.get("email"),
        "source_type": "pa",
        "source_id": pa["id"],
        "pa_id": pa["id"],
        "pa_number": pa.get("pa_number"),
        "client_name": pa.get("client_name"),
        "country": pa.get("country"),
        "service_type": pa.get("service_type"),
        "period": period,
        "revenue": revenue,
        "achieved_before": round(achieved_before, 2),
        "achieved_after": round(achieved_after, 2),
        "rate_mode": resolved["rate_mode"],
        "slab_key": resolved["slab_key"],
        "slab_name": resolved["slab_name"],
        "rate_pct": rate,
        "commission_amount": commission,
        "formula": f"₹{revenue:,.2f} × {rate}% = ₹{commission:,.2f}",
        "status": "pending",   # pending → approved → paid (or reversed)
        "applied_at": now,
        "created_at": now,
    }
    await entries_col.insert_one(entry)
    entry.pop("_id", None)
    return entry


# ──────────────────────────────────────────────────────────────
# Apply commission on CRM payments
# ──────────────────────────────────────────────────────────────
async def apply_commission_for_crm_payment(payment_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Automatically calculate commission when a verified CRM payment is recorded.
    
    Idempotent: skips if entry already exists for this payment_id / receipt_number.
    """
    if not payment_doc or payment_doc.get("payment_status") not in ("paid", "partially_paid"):
        return None

    payment_id = payment_doc.get("id")
    if not payment_id:
        return None

    # Idempotency check
    existing = await entries_col.find_one(
        {"$or": [
            {"source_type": "crm_payment", "source_id": payment_id},
            {"crm_payment_id": payment_id},
        ]},
        {"_id": 0}
    )
    if existing:
        return existing

    rep_id = payment_doc.get("sales_person_id")
    if not rep_id:
        return None

    user = await users_col.find_one(
        {"id": rep_id},
        {"_id": 0, "id": 1, "name": 1, "role": 1, "rbac_role": 1, "email": 1, "commission_mode": 1, "commission_rate": 1, "is_commission_active": 1}
    )
    if not user or not _is_sales_user(user):
        return None

    revenue = float(payment_doc.get("paid_amount") or 0)
    if revenue <= 0:
        return None

    period = _period_key()
    achieved_before = await get_period_revenue(rep_id, period)
    achieved_after = achieved_before + revenue

    slabs = await get_active_slabs()
    if not slabs:
        await ensure_default_slabs()
        slabs = await get_active_slabs()

    product_id = payment_doc.get("product_id")
    if not product_id and payment_doc.get("deal_id"):
        deal = await db["crm_deals"].find_one({"id": payment_doc["deal_id"]}, {"_id": 0, "product_id": 1})
        if deal:
            product_id = deal.get("product_id")

    product_alloc = None
    if product_id:
        prod = await db["products"].find_one({"id": product_id}, {"_id": 0, "cost_allocations": 1})
        if prod:
            allocs = prod.get("cost_allocations") or []
            role = (user.get("rbac_role") or user.get("role") or "").lower()
            user_type = (user.get("user_type") or "").lower()
            is_int_p = user_type == "internal" or user.get("partner_type") == "internal" or user.get("is_internal") is True
            is_external = (
                user_type == "external"
                or "partner" in role
                or user.get("is_external") is True
            )
            if is_external and (is_int_p or user_type == "internal"):
                is_external = False

            if not is_external:
                product_alloc = next((a for a in allocs if a.get("vendor_category") in ("internal_partner", "internal_salesperson", "sales_commission", "salesperson", "sales_user")), None)
            else:
                product_alloc = next((a for a in allocs if a.get("vendor_category") in ("external_partner", "external_salesperson", "partner_external", "partner_commission")), None)

    if product_alloc:
        ptype = product_alloc.get("payment_type", "percentage")
        val = float(product_alloc.get("rate") if (product_alloc.get("rate") is not None and str(product_alloc.get("rate")) != "") else (product_alloc.get("amount", 0) or 0))
        if ptype == "percentage":
            rate = val
            commission = round(revenue * rate / 100, 2)
            resolved = {
                "rate_mode": "product_allocation",
                "rate_pct": rate,
                "slab_key": "product_commission",
                "slab_name": f"Product Rate ({rate}%)",
            }
            formula = f"₹{revenue:,.2f} × {rate}% = ₹{commission:,.2f}"
        else:
            commission = round(val, 2)
            rate = 0.0
            resolved = {
                "rate_mode": "flat_product_allocation",
                "rate_pct": rate,
                "slab_key": "product_commission_flat",
                "slab_name": f"Product Flat (₹{val:,.2f})",
            }
            formula = f"Flat ₹{commission:,.2f}"
    else:
        resolved = _resolve_rate(user, achieved_after, slabs)
        if not resolved:
            return None
        rate = resolved["rate_pct"]
        commission = round(revenue * rate / 100, 2)
        formula = f"₹{revenue:,.2f} × {rate}% = ₹{commission:,.2f}"
    now = datetime.now(timezone.utc)

    entry = {
        "id": str(uuid.uuid4()),
        "user_id": rep_id,
        "user_name": user.get("name") or payment_doc.get("sales_person_name"),
        "user_email": user.get("email"),
        "source_type": "crm_payment",
        "source_id": payment_id,
        "crm_payment_id": payment_id,
        "receipt_number": payment_doc.get("receipt_number"),
        "transaction_id": payment_doc.get("transaction_id"),
        "deal_id": payment_doc.get("deal_id"),
        "lead_id": payment_doc.get("lead_id"),
        "client_name": payment_doc.get("client_name"),
        "period": period,
        "revenue": revenue,
        "achieved_before": round(achieved_before, 2),
        "achieved_after": round(achieved_after, 2),
        "rate_mode": resolved["rate_mode"],
        "slab_key": resolved["slab_key"],
        "slab_name": resolved["slab_name"],
        "rate_pct": rate,
        "commission_amount": commission,
        "formula": f"₹{revenue:,.2f} × {rate}% = ₹{commission:,.2f}",
        "status": "pending",
        "applied_at": now,
        "created_at": now,
    }
    await entries_col.insert_one(entry)
    entry.pop("_id", None)
    return entry


# ──────────────────────────────────────────────────────────────
# Apply commission for direct sale payment
# ──────────────────────────────────────────────────────────────
async def apply_commission_for_direct_sale(sale: Dict[str, Any], payment_entry: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Idempotently records commission for direct sales payments."""
    rep_id = sale.get("partner_id")
    if not rep_id:
        return None

    user = await users_col.find_one(
        {"id": rep_id},
        {"_id": 0, "id": 1, "name": 1, "role": 1, "rbac_role": 1, "email": 1, "commission_mode": 1, "commission_rate": 1, "is_commission_active": 1}
    )
    if not user or not _is_sales_user(user):
        return None

    # Determine eligible revenue
    if payment_entry and payment_entry.get("amount"):
        revenue = float(payment_entry.get("amount") or 0)
        source_id = f"{sale['id']}_{payment_entry.get('receipt_number') or payment_entry.get('date') or uuid.uuid4().hex[:6]}"
    else:
        revenue = float(sale.get("amount_received") or 0)
        source_id = f"{sale['id']}_approved"

    if revenue <= 0:
        return None

    existing = await entries_col.find_one({"source_type": "direct_sale", "source_id": source_id}, {"_id": 0})
    if existing:
        return existing

    period = _period_key()
    achieved_before = await get_period_revenue(rep_id, period)
    achieved_after = achieved_before + revenue

    slabs = await get_active_slabs()
    if not slabs:
        await ensure_default_slabs()
        slabs = await get_active_slabs()

    if not payment_entry and sale.get("commission_amount") is not None and str(sale.get("commission_source", "")).startswith("product_allocation"):
        commission = float(sale["commission_amount"])
        rate = float(sale.get("commission_rate") or 0)
        ptype = sale.get("commission_type", "percentage")
        resolved = {
            "rate_mode": "product_allocation",
            "rate_pct": rate,
            "slab_key": "product_allocation",
            "slab_name": "Product Commission",
        }
        formula = f"₹{revenue:,.2f} × {rate}% = ₹{commission:,.2f}" if ptype == "percentage" else f"Flat ₹{commission:,.2f}"
    else:
        resolved = _resolve_rate(user, achieved_after, slabs)
        if not resolved:
            return None
        rate = resolved["rate_pct"]
        commission = round(revenue * rate / 100, 2)
        formula = f"₹{revenue:,.2f} × {rate}% = ₹{commission:,.2f}"
    now = datetime.now(timezone.utc)

    entry = {
        "id": str(uuid.uuid4()),
        "user_id": rep_id,
        "user_name": user.get("name"),
        "user_email": user.get("email"),
        "source_type": "direct_sale",
        "source_id": source_id,
        "sale_id": sale["id"],
        "client_name": sale.get("client_name"),
        "service_type": sale.get("service_type") or sale.get("product_name"),
        "period": period,
        "revenue": revenue,
        "achieved_before": round(achieved_before, 2),
        "achieved_after": round(achieved_after, 2),
        "rate_mode": resolved["rate_mode"],
        "slab_key": resolved["slab_key"],
        "slab_name": resolved["slab_name"],
        "rate_pct": rate,
        "commission_amount": commission,
        "formula": f"₹{revenue:,.2f} × {rate}% = ₹{commission:,.2f}",
        "status": "pending",
        "applied_at": now,
        "created_at": now,
    }
    await entries_col.insert_one(entry)
    entry.pop("_id", None)
    return entry


async def reverse_commission_for_pa(pa_id: str, reason: str = "refund") -> Optional[Dict[str, Any]]:
    """Mark existing commission entry as reversed (e.g., on refund)."""
    res = await entries_col.find_one_and_update(
        {"$or": [{"pa_id": pa_id}, {"source_id": pa_id}], "status": {"$nin": ["reversed"]}},
        {"$set": {"status": "reversed", "reversed_at": datetime.now(timezone.utc), "reverse_reason": reason}},
        return_document=True,
        projection={"_id": 0},
    )
    return res


# ──────────────────────────────────────────────────────────────
# Summary helpers
# ──────────────────────────────────────────────────────────────
async def get_user_summary(user_id: str, period: Optional[str] = None) -> Dict[str, Any]:
    period = period or _period_key()
    cursor = entries_col.find({"user_id": user_id, "period": period, "status": {"$ne": "reversed"}}, {"_id": 0}).sort("applied_at", -1)
    entries = await cursor.to_list(500)
    revenue = sum(float(e.get("revenue") or 0) for e in entries)
    commission = sum(float(e.get("commission_amount") or 0) for e in entries)
    paid = sum(float(e.get("commission_amount") or 0) for e in entries if e.get("status") == "paid")
    approved = sum(float(e.get("commission_amount") or 0) for e in entries if e.get("status") == "approved")
    pending = sum(float(e.get("commission_amount") or 0) for e in entries if e.get("status") == "pending")

    user = await users_col.find_one(
        {"id": user_id},
        {"_id": 0, "name": 1, "email": 1, "role": 1, "rbac_role": 1, "commission_mode": 1, "commission_rate": 1, "is_commission_active": 1}
    ) or {}

    comm_mode = user.get("commission_mode", "slab")
    custom_rate = user.get("commission_rate")

    slabs = await get_active_slabs()
    current_slab = _match_slab(revenue, slabs)
    # Find next slab
    next_slab = None
    if current_slab:
        for s in slabs:
            if float(s.get("min_revenue") or 0) > float(current_slab.get("min_revenue") or 0):
                next_slab = s
                break
    gap_to_next = None
    if next_slab:
        gap_to_next = max(0, float(next_slab["min_revenue"]) - revenue)

    return {
        "period": period,
        "user_id": user_id,
        "user_name": user.get("name"),
        "user_email": user.get("email"),
        "commission_mode": comm_mode,
        "individual_rate": float(custom_rate) if (custom_rate is not None and comm_mode == "flat") else None,
        "is_commission_active": user.get("is_commission_active", True),
        "deal_count": len(entries),
        "total_revenue": round(revenue, 2),
        "total_commission": round(commission, 2),
        "total_earned": round(commission, 2),
        "paid": round(paid, 2),
        "approved": round(approved, 2),
        "pending": round(pending, 2),
        "current_slab": current_slab,
        "next_slab": next_slab,
        "gap_to_next_slab": round(gap_to_next, 2) if gap_to_next is not None else None,
        "entries": entries,
    }

