"""Phase 4C.7 — Approval + Payout Workflow.

Admin tools to bulk-process allocation payouts AND export NEFT-ready CSV.

Endpoints:
  GET    /api/payouts/queue?status=&vendor_id=&from=&to=     (admin)
  POST   /api/payouts/bulk-approve                            (admin)
  POST   /api/payouts/bulk-mark-paid                          (admin)
  GET    /api/payouts/neft-csv?status=approved&from=&to=      (admin — CSV download)
  GET    /api/payouts/stats                                    (admin — payout summary)
"""
import io
import csv
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/payouts", tags=["Phase 4C.7 - Payouts"])

allocations_col = db["pa_cost_allocations"]
vendors_col = db["vendors"]
users_col = db["users"]


def _is_admin(u: dict) -> bool:
    return u.get("role") in ("admin", "admin_owner") or u.get("rbac_role") in ("admin", "admin_owner")


def _iso(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


async def _flatten_queue(filter_status: Optional[str], vendor_id: Optional[str], from_d: Optional[str], to_d: Optional[str]):
    """Iterate all pa_cost_allocations docs and emit flat rows."""
    rows = []
    cursor = allocations_col.find({}, {"_id": 0})
    async for doc in cursor:
        for a in (doc.get("allocations") or []):
            st = a.get("status") or "pending"
            if filter_status and st != filter_status:
                continue
            if vendor_id and a.get("vendor_id") != vendor_id and a.get("vendor_master_id") != vendor_id:
                continue
            rec_date = a.get("paid_at") or a.get("approved_at") or a.get("assigned_at") or doc.get("last_recalculated_at")
            rec_date_iso = _iso(rec_date) if rec_date else None
            if from_d and rec_date_iso and rec_date_iso < from_d:
                continue
            if to_d and rec_date_iso and rec_date_iso > to_d + "T23:59:59":
                continue
            rows.append({
                "pa_id": doc.get("pa_id"),
                "pa_number": doc.get("pa_number"),
                "allocation_id": a.get("allocation_id"),
                "client_name": doc.get("client_name"),
                "label": a.get("label"),
                "vendor_category": a.get("vendor_category"),
                "vendor_id": a.get("vendor_id"),
                "vendor_master_id": a.get("vendor_master_id"),
                "vendor_name": a.get("vendor_name"),
                "vendor_type": a.get("vendor_type"),
                "amount": float(a.get("total_amount") or 0),
                "calculated_amount": float(a.get("calculated_amount") or 0),
                "bonus_amount": float(a.get("bonus_amount") or 0),
                "status": st,
                "assigned_at": _iso(a.get("assigned_at")),
                "approved_at": _iso(a.get("approved_at")),
                "paid_at": _iso(a.get("paid_at")),
                "payment_reference": a.get("payment_reference"),
            })
    rows.sort(key=lambda r: r.get("approved_at") or r.get("assigned_at") or "", reverse=True)
    return rows


@router.get("/queue")
async def queue(
    status: Optional[str] = Query(None),
    vendor_id: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    to_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    rows = await _flatten_queue(status, vendor_id, from_date, to_date)
    totals = {"pending": 0.0, "approved": 0.0, "paid": 0.0, "disputed": 0.0}
    for r in rows:
        if r["status"] in totals:
            totals[r["status"]] += r["amount"]
    return {
        "rows": rows,
        "count": len(rows),
        "totals": {k: round(v, 2) for k, v in totals.items()},
    }


@router.get("/stats")
async def stats(current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    rows = await _flatten_queue(None, None, None, None)
    totals = {"pending": 0.0, "approved": 0.0, "paid": 0.0, "disputed": 0.0, "unassigned": 0.0}
    counts = {"pending": 0, "approved": 0, "paid": 0, "disputed": 0, "unassigned": 0}
    for r in rows:
        st = r["status"]
        if st in totals:
            totals[st] += r["amount"]
            counts[st] += 1
    return {
        "totals": {k: round(v, 2) for k, v in totals.items()},
        "counts": counts,
        "ready_to_pay": round(totals["approved"], 2),
        "outstanding": round(totals["approved"] + totals["pending"], 2),
    }


class BulkActionRequest(BaseModel):
    items: List[dict]  # [{"pa_id": "...", "allocation_id": "..."}]
    payment_reference: Optional[str] = None


@router.post("/bulk-approve")
async def bulk_approve(req: BulkActionRequest, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    now = datetime.now(timezone.utc)
    ok, fail = 0, 0
    errors = []
    for item in req.items:
        pa_id = item.get("pa_id")
        alloc_id = item.get("allocation_id")
        if not pa_id or not alloc_id:
            fail += 1
            errors.append("missing pa_id/allocation_id")
            continue
        res = await allocations_col.update_one(
            {"pa_id": pa_id, "allocations": {"$elemMatch": {"allocation_id": alloc_id, "status": "pending", "vendor_id": {"$ne": None}}}},
            {"$set": {
                "allocations.$.status": "approved",
                "allocations.$.approved_at": now,
                "allocations.$.approved_by": current_user["id"],
                "updated_at": now,
            }}
        )
        if res.modified_count > 0:
            ok += 1
        else:
            fail += 1
            errors.append(f"{pa_id}/{alloc_id}: not in pending state or unassigned")
    return {"ok": True, "approved": ok, "failed": fail, "errors": errors[:20]}


@router.post("/bulk-mark-paid")
async def bulk_mark_paid(req: BulkActionRequest, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    now = datetime.now(timezone.utc)
    ok, fail = 0, 0
    errors = []
    ref = req.payment_reference or f"BATCH-{now.strftime('%Y%m%d-%H%M%S')}"
    for item in req.items:
        pa_id = item.get("pa_id")
        alloc_id = item.get("allocation_id")
        if not pa_id or not alloc_id:
            fail += 1
            errors.append("missing pa_id/allocation_id")
            continue
        res = await allocations_col.update_one(
            {"pa_id": pa_id, "allocations": {"$elemMatch": {"allocation_id": alloc_id, "status": {"$in": ["pending", "approved"]}, "vendor_id": {"$ne": None}}}},
            {"$set": {
                "allocations.$.status": "paid",
                "allocations.$.paid_at": now,
                "allocations.$.paid_by": current_user["id"],
                "allocations.$.payment_reference": ref,
                "updated_at": now,
            }}
        )
        if res.modified_count > 0:
            ok += 1
        else:
            fail += 1
            errors.append(f"{pa_id}/{alloc_id}: not approvable")
    return {"ok": True, "paid": ok, "failed": fail, "payment_reference": ref, "errors": errors[:20]}


# ──────────────────────────────────────────────────────────────
# NEFT CSV Export
# ──────────────────────────────────────────────────────────────
@router.get("/neft-csv")
async def neft_csv(
    status: str = Query("approved", description="approved | pending | paid"),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Generates NEFT-ready CSV with vendor banking details."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    rows = await _flatten_queue(status, None, from_date, to_date)

    # Hydrate vendor bank details
    vendor_master_ids = list({r["vendor_master_id"] for r in rows if r.get("vendor_master_id")})
    user_ids = list({r["vendor_id"] for r in rows if r.get("vendor_id") and not r.get("vendor_master_id")})

    vmap: dict = {}
    if vendor_master_ids:
        async for v in vendors_col.find({"id": {"$in": vendor_master_ids}}, {"_id": 0}):
            vmap[v["id"]] = v
    # For internal users (CMs, sales reps) — pull from users.bank_details if available
    umap: dict = {}
    if user_ids:
        async for u in users_col.find({"id": {"$in": user_ids}}, {"_id": 0}):
            umap[u["id"]] = u

    # Build CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "S.No", "Beneficiary Name", "Account Number", "IFSC", "Bank Name",
        "Amount (INR)", "PAN", "PA Number", "Client", "Vendor Code",
        "Vendor Type", "Allocation Label", "Status",
        "Approved At", "Payment Reference",
    ])

    for i, r in enumerate(rows, start=1):
        vendor = vmap.get(r.get("vendor_master_id"))
        bank = (vendor or {}).get("bank_details") or {}
        if not bank and r.get("vendor_id"):
            user = umap.get(r["vendor_id"])
            if user:
                bank = user.get("bank_details") or {}
        writer.writerow([
            i,
            (vendor.get("name") if vendor else r.get("vendor_name")) or "",
            bank.get("account_number") or "",
            bank.get("ifsc") or "",
            bank.get("bank_name") or "",
            f"{r['amount']:.2f}",
            (vendor or {}).get("pan_number") or "",
            r.get("pa_number") or "",
            r.get("client_name") or "",
            (vendor or {}).get("vendor_code") or "",
            r.get("vendor_type") or "",
            r.get("label") or "",
            r.get("status") or "",
            r.get("approved_at") or "",
            r.get("payment_reference") or "",
        ])

    buf.seek(0)
    filename = f"NEFT_payouts_{status}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)
