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
    rbac = user.get("rbac_role")
    if rbac in SALES_ROLES:
        return True
    return user.get("role") == "partner"


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
    """Sum of `revenue` across this user's existing entries in the period (BEFORE the current PA)."""
    period = period or _period_key()
    pipeline = [
        {"$match": {"user_id": user_id, "period": period, "status": {"$ne": "reversed"}}},
        {"$group": {"_id": None, "total": {"$sum": "$revenue"}}},
    ]
    cursor = entries_col.aggregate(pipeline)
    rows = await cursor.to_list(1)
    return float(rows[0]["total"]) if rows else 0.0


# ──────────────────────────────────────────────────────────────
# Apply commission on a PA reaching case_created
# ──────────────────────────────────────────────────────────────
async def apply_commission_for_pa(pa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Idempotent — returns the created/existing entry or None if not applicable."""
    creator_id = pa.get("created_by_user_id") or pa.get("partner_id")
    if not creator_id:
        return None

    user = await users_col.find_one({"id": creator_id}, {"_id": 0, "id": 1, "name": 1, "role": 1, "rbac_role": 1, "email": 1})
    if not user or not _is_sales_user(user):
        return None

    # Idempotency: skip if entry already exists for this PA
    existing = await entries_col.find_one({"pa_id": pa["id"]}, {"_id": 0})
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
    slab = _match_slab(achieved_after, slabs)
    if not slab:
        return None

    rate = float(slab["rate_pct"])
    commission = round(revenue * rate / 100, 2)
    now = datetime.now(timezone.utc)

    entry = {
        "id": str(uuid.uuid4()),
        "user_id": creator_id,
        "user_name": user.get("name"),
        "user_email": user.get("email"),
        "pa_id": pa["id"],
        "pa_number": pa.get("pa_number"),
        "client_name": pa.get("client_name"),
        "country": pa.get("country"),
        "service_type": pa.get("service_type"),
        "period": period,
        "revenue": revenue,
        "achieved_before": round(achieved_before, 2),
        "achieved_after": round(achieved_after, 2),
        "slab_key": slab.get("key"),
        "slab_name": slab.get("name"),
        "rate_pct": rate,
        "commission_amount": commission,
        "status": "pending",   # pending → approved → paid (or reversed)
        "applied_at": now,
        "created_at": now,
    }
    await entries_col.insert_one(entry)
    entry.pop("_id", None)
    return entry


async def reverse_commission_for_pa(pa_id: str, reason: str = "refund") -> Optional[Dict[str, Any]]:
    """Mark existing commission entry as reversed (e.g., on refund)."""
    res = await entries_col.find_one_and_update(
        {"pa_id": pa_id, "status": {"$nin": ["reversed"]}},
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
        "deal_count": len(entries),
        "total_revenue": round(revenue, 2),
        "total_commission": round(commission, 2),
        "paid": round(paid, 2),
        "approved": round(approved, 2),
        "pending": round(pending, 2),
        "current_slab": current_slab,
        "next_slab": next_slab,
        "gap_to_next_slab": round(gap_to_next, 2) if gap_to_next is not None else None,
        "entries": entries,
    }
