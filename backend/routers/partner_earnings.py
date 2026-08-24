"""Partner Earnings Router — read-only earnings breakdown for Partners & Sales Reps.

Aggregates sales commission allocations from pa_cost_allocations (and direct sales)
where the partner/rep is the recipient. Provides lifetime totals, pending, approved,
paid amounts, and client-wise detail records.
"""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/partner-earnings", tags=["Partner Earnings"])

allocations_col = db["pa_cost_allocations"]
pre_assessments_col = db["pre_assessments"]
sales_col = db["sales"]


def _is_partner_or_sales(u: dict) -> bool:
    role = u.get("role") or u.get("rbac_role") or ""
    return role in ("partner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "admin", "admin_owner")


def _iso(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


@router.get("/my")
async def my_partner_earnings(period: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Returns summary + line items for the current Partner's commission allocations."""
    if not _is_partner_or_sales(current_user):
        raise HTTPException(status_code=403, detail="Partner or Sales role required")

    uid = current_user["id"]
    
    # 1. Find all PAs belonging to this partner
    partner_pas = await pre_assessments_col.find(
        {"$or": [{"partner_id": uid}, {"created_by_user_id": uid}]},
        {"_id": 0, "id": 1, "pa_number": 1, "client_name": 1}
    ).to_list(500)
    partner_pa_ids = {p["id"] for p in partner_pas if p.get("id")}
    pa_info_map = {p["id"]: p for p in partner_pas if p.get("id")}

    # 2. Query allocations_col for docs matching this partner
    alloc_cursor = allocations_col.find({
        "$or": [
            {"allocations.vendor_id": uid},
            {"pa_id": {"$in": list(partner_pa_ids)}},
        ]
    }, {"_id": 0})

    line_items = []
    seen_keys = set()
    totals = {"pending": 0.0, "approved": 0.0, "paid": 0.0, "disputed": 0.0}

    async for doc in alloc_cursor:
        pa_id = doc.get("pa_id")
        pa_fallback = pa_info_map.get(pa_id, {})
        client_name = doc.get("client_name") or pa_fallback.get("client_name") or "Valued Client"
        pa_number = doc.get("pa_number") or pa_fallback.get("pa_number") or ""

        for a in (doc.get("allocations") or []):
            # Check if this allocation is for the partner (sales_commission or explicit vendor_id)
            is_match = (
                a.get("vendor_id") == uid or
                (a.get("vendor_category") == "sales_commission" and pa_id in partner_pa_ids)
            )
            if not is_match:
                continue

            alloc_id = a.get("allocation_id") or f"{pa_id}_{a.get('vendor_category')}"
            if alloc_id in seen_keys:
                continue
            seen_keys.add(alloc_id)

            amount = float(a.get("total_amount") or 0)
            status = a.get("status") or "pending"
            if status in totals:
                totals[status] += amount

            line_items.append({
                "pa_id": pa_id,
                "pa_number": pa_number,
                "client_name": client_name,
                "label": a.get("label") or "Sales Commission",
                "vendor_category": a.get("vendor_category", "sales_commission"),
                "amount": amount,
                "status": status,
                "paid_at": _iso(a.get("paid_at")),
                "approved_at": _iso(a.get("approved_at")),
                "payment_reference": a.get("payment_reference"),
                "last_recalculated_at": _iso(doc.get("last_recalculated_at")),
                "source": "cost_allocation",
            })

    # 3. Also include any approved direct sales from sales_col (if not duplicate)
    sales_cursor = sales_col.find({
        "$or": [{"partner_id": uid}, {"created_by_user_id": uid}, {"sales_rep_id": uid}],
        "status": {"$in": ["approved", "pending", "paid"]}
    }, {"_id": 0})

    async for s in sales_cursor:
        sale_key = f"sale_{s.get('id')}"
        if sale_key in seen_keys:
            continue
        seen_keys.add(sale_key)

        comm_amount = float(s.get("commission_amount") or 0)
        status = s.get("payment_status") or s.get("status") or "pending"
        if status == "approved":
            status = "approved"
        elif status == "paid":
            status = "paid"
        else:
            status = "pending"

        if status in totals:
            totals[status] += comm_amount

        line_items.append({
            "pa_id": s.get("id"),
            "pa_number": s.get("invoice_number") or s.get("id"),
            "client_name": s.get("client_name") or "Valued Client",
            "label": f"Direct Sale ({s.get('product_name') or 'Service'})",
            "vendor_category": "sales_commission",
            "amount": comm_amount,
            "status": status,
            "paid_at": _iso(s.get("paid_at")),
            "approved_at": _iso(s.get("approved_at")),
            "payment_reference": s.get("payment_reference"),
            "last_recalculated_at": _iso(s.get("created_at")),
            "source": "direct_sale",
        })

    # Period filter if provided
    if period:
        def _in_period(item):
            ref = item.get("paid_at") or item.get("approved_at") or item.get("last_recalculated_at") or ""
            return isinstance(ref, str) and ref.startswith(period)
        line_items = [li for li in line_items if _in_period(li)]
        totals = {"pending": 0.0, "approved": 0.0, "paid": 0.0, "disputed": 0.0}
        for li in line_items:
            s = li["status"]
            if s in totals:
                totals[s] += li["amount"]

    line_items.sort(key=lambda x: x.get("last_recalculated_at") or "", reverse=True)
    total = round(sum(totals.values()), 2)

    return {
        "user_id": uid,
        "period": period,
        "totals": {k: round(v, 2) for k, v in totals.items()},
        "lifetime_total": total,
        "deal_count": len({li["pa_id"] for li in line_items}),
        "line_items": line_items,
    }