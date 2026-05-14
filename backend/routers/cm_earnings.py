"""Phase 4C.5 — Case Manager Earnings (read-only widget).

CM users see their earnings from allocations where they are assigned as
`case_manager`. Pure read-only — no workflow changes to CM portal.
"""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/cm-earnings", tags=["Phase 4C.5 - CM Earnings"])

allocations_col = db["pa_cost_allocations"]


def _is_cm(u: dict) -> bool:
    return u.get("role") == "case_manager" or u.get("rbac_role") == "case_manager"


def _iso(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


@router.get("/my")
async def my_earnings(period: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Returns summary + line items for the current CM's allocations.

    period: optional 'YYYY-MM' filter on the allocation's last_recalculated_at.
    """
    if not _is_cm(current_user):
        raise HTTPException(status_code=403, detail="Case manager role required")

    uid = current_user["id"]
    # Aggregate all allocation docs where ANY allocation has vendor_id == this CM and category == case_manager
    cursor = allocations_col.find({
        "allocations": {"$elemMatch": {"vendor_category": "case_manager", "vendor_id": uid}}
    }, {"_id": 0})

    line_items = []
    totals = {"pending": 0.0, "approved": 0.0, "paid": 0.0, "disputed": 0.0}
    async for doc in cursor:
        for a in (doc.get("allocations") or []):
            if a.get("vendor_category") != "case_manager":
                continue
            if a.get("vendor_id") != uid:
                continue
            amount = float(a.get("total_amount") or 0)
            status = a.get("status") or "pending"
            if status in totals:
                totals[status] += amount
            line_items.append({
                "pa_id": doc.get("pa_id"),
                "pa_number": doc.get("pa_number"),
                "client_name": doc.get("client_name"),
                "label": a.get("label"),
                "amount": amount,
                "status": status,
                "paid_at": _iso(a.get("paid_at")),
                "approved_at": _iso(a.get("approved_at")),
                "payment_reference": a.get("payment_reference"),
                "last_recalculated_at": _iso(doc.get("last_recalculated_at")),
            })

    # Filter by period (YYYY-MM) using paid_at if available, else last_recalculated_at
    if period:
        def _in_period(item):
            ref = item.get("paid_at") or item.get("last_recalculated_at") or ""
            return isinstance(ref, str) and ref.startswith(period)
        line_items = [li for li in line_items if _in_period(li)]
        # Recompute totals based on filtered list
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
