"""Phase 4C.4 — Sales Commission Slab Router.

Endpoints:
  GET    /api/sales-commission/slabs                  (admin/sales-head)
  POST   /api/sales-commission/slabs                  (admin)
  PATCH  /api/sales-commission/slabs/{id}             (admin)
  DELETE /api/sales-commission/slabs/{id}             (admin)
  POST   /api/sales-commission/slabs/seed             (admin — re-seed defaults)
  GET    /api/sales-commission/my                     (sales rep)
  GET    /api/sales-commission/all?period=YYYY-MM     (admin)
  GET    /api/sales-commission/leaderboard?period=    (admin/sales-head)
  POST   /api/sales-commission/entries/{id}/approve   (admin)
  POST   /api/sales-commission/entries/{id}/mark-paid (admin)
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.database import db, users_col
from core.commission_logic import (
    slabs_col, entries_col, get_user_summary, _period_key,
    ensure_default_slabs, _is_sales_user,
)

router = APIRouter(prefix="/sales-commission", tags=["Phase 4C.4 - Sales Commission"])


def _is_admin(u: dict) -> bool:
    return u.get("role") in ("admin", "admin_owner") or u.get("rbac_role") in ("admin", "admin_owner")


def _can_view_all(u: dict) -> bool:
    if _is_admin(u):
        return True
    perms = u.get("permissions") or []
    return "commission.view.all" in perms or "commission.view.team" in perms


def _clean(d: dict) -> dict:
    if not d:
        return d
    d.pop("_id", None)
    for k in ("created_at", "updated_at", "applied_at", "approved_at", "paid_at", "reversed_at"):
        v = d.get(k)
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────
class SlabCreate(BaseModel):
    key: str = Field(..., pattern=r"^[a-z_]+$", max_length=40)
    name: str
    min_revenue: float = Field(..., ge=0)
    max_revenue: Optional[float] = None  # None = unbounded
    rate_pct: float = Field(..., ge=0, le=100)
    color: Optional[str] = "slate"


class SlabUpdate(BaseModel):
    name: Optional[str] = None
    min_revenue: Optional[float] = Field(None, ge=0)
    max_revenue: Optional[float] = None
    rate_pct: Optional[float] = Field(None, ge=0, le=100)
    color: Optional[str] = None
    is_active: Optional[bool] = None


# ══════════════════════════════════════════════════════════════
# SLABS — CRUD
# ══════════════════════════════════════════════════════════════
@router.get("/slabs")
async def list_slabs(current_user: dict = Depends(get_current_user)):
    if not (_is_admin(current_user) or _is_sales_user(current_user) or _can_view_all(current_user)):
        raise HTTPException(status_code=403, detail="Not authorized")
    # Auto-seed if empty
    await ensure_default_slabs()
    items = await slabs_col.find({}, {"_id": 0}).sort("min_revenue", 1).to_list(50)
    return {"slabs": [_clean(i) for i in items], "count": len(items)}


@router.post("/slabs")
async def create_slab(req: SlabCreate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    if await slabs_col.find_one({"key": req.key}, {"_id": 0, "key": 1}):
        raise HTTPException(status_code=409, detail=f"Slab key '{req.key}' already exists")
    if req.max_revenue is not None and req.max_revenue <= req.min_revenue:
        raise HTTPException(status_code=400, detail="max_revenue must be greater than min_revenue")
    doc = {
        "id": str(uuid.uuid4()),
        **req.model_dump(),
        "is_active": True,
        "is_system": False,
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user["id"],
    }
    await slabs_col.insert_one(doc)
    return {"ok": True, "slab": _clean(doc)}


@router.patch("/slabs/{slab_id}")
async def update_slab(slab_id: str, req: SlabUpdate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await slabs_col.find_one({"id": slab_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Slab not found")
    update = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None or k in ("max_revenue",)}
    if not update:
        return {"ok": True, "no_change": True}
    merged = {**existing, **update}
    if merged.get("max_revenue") is not None and float(merged["max_revenue"]) <= float(merged.get("min_revenue") or 0):
        raise HTTPException(status_code=400, detail="max_revenue must be greater than min_revenue")
    update["updated_at"] = datetime.now(timezone.utc)
    await slabs_col.update_one({"id": slab_id}, {"$set": update})
    return {"ok": True}


@router.delete("/slabs/{slab_id}")
async def delete_slab(slab_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await slabs_col.find_one({"id": slab_id}, {"_id": 0, "is_system": 1})
    if not existing:
        raise HTTPException(status_code=404, detail="Slab not found")
    if existing.get("is_system"):
        raise HTTPException(status_code=400, detail="System slabs cannot be deleted. Deactivate instead.")
    await slabs_col.delete_one({"id": slab_id})
    return {"ok": True}


@router.post("/slabs/seed")
async def reseed_slabs(current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    count = await ensure_default_slabs()
    return {"ok": True, "seeded": count, "note": "Defaults only seeded when collection is empty"}


# ══════════════════════════════════════════════════════════════
# Self-service: My Commission
# ══════════════════════════════════════════════════════════════
@router.get("/my")
async def my_commission(
    period: Optional[str] = Query(None, description="YYYY-MM (defaults to current month)"),
    current_user: dict = Depends(get_current_user),
):
    if not _is_sales_user(current_user):
        raise HTTPException(status_code=403, detail="Sales role required")
    period = period or _period_key()
    summary = await get_user_summary(current_user["id"], period)
    # Sanitize entries
    summary["entries"] = [_clean(e) for e in summary["entries"]]
    if summary.get("current_slab"):
        summary["current_slab"] = _clean(summary["current_slab"])
    if summary.get("next_slab"):
        summary["next_slab"] = _clean(summary["next_slab"])
    return summary


# ══════════════════════════════════════════════════════════════
# Admin: All / Leaderboard
# ══════════════════════════════════════════════════════════════
@router.get("/all")
async def all_entries(
    period: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    if not _can_view_all(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    period = period or _period_key()
    qry: dict = {"period": period}
    if status:
        qry["status"] = status
    if user_id:
        qry["user_id"] = user_id
    items = await entries_col.find(qry, {"_id": 0}).sort("applied_at", -1).to_list(2000)
    total_commission = sum(float(e.get("commission_amount") or 0) for e in items if e.get("status") != "reversed")
    total_revenue = sum(float(e.get("revenue") or 0) for e in items if e.get("status") != "reversed")
    return {
        "period": period,
        "entries": [_clean(i) for i in items],
        "count": len(items),
        "total_revenue": round(total_revenue, 2),
        "total_commission": round(total_commission, 2),
    }


@router.get("/leaderboard")
async def leaderboard(period: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if not _can_view_all(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    period = period or _period_key()
    pipeline = [
        {"$match": {"period": period, "status": {"$ne": "reversed"}}},
        {"$group": {
            "_id": "$user_id",
            "user_name": {"$first": "$user_name"},
            "user_email": {"$first": "$user_email"},
            "total_revenue": {"$sum": "$revenue"},
            "total_commission": {"$sum": "$commission_amount"},
            "deal_count": {"$sum": 1},
        }},
        {"$sort": {"total_revenue": -1}},
        {"$limit": 50},
    ]
    rows = await entries_col.aggregate(pipeline).to_list(50)
    leaderboard = []
    for r in rows:
        leaderboard.append({
            "user_id": r["_id"],
            "user_name": r.get("user_name"),
            "user_email": r.get("user_email"),
            "deal_count": r.get("deal_count"),
            "total_revenue": round(float(r.get("total_revenue") or 0), 2),
            "total_commission": round(float(r.get("total_commission") or 0), 2),
        })
    return {"period": period, "leaderboard": leaderboard, "count": len(leaderboard)}


# ══════════════════════════════════════════════════════════════
# Approve / Mark Paid / Reverse
# ══════════════════════════════════════════════════════════════
class MarkPaidReq(BaseModel):
    payment_reference: Optional[str] = None


@router.post("/entries/{entry_id}/approve")
async def approve_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    res = await entries_col.find_one_and_update(
        {"id": entry_id, "status": {"$in": ["pending"]}},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc), "approved_by": current_user["id"]}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Entry not found or not in pending state")
    return {"ok": True, "entry": _clean(res)}


@router.post("/entries/{entry_id}/mark-paid")
async def mark_paid(entry_id: str, req: MarkPaidReq, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    res = await entries_col.find_one_and_update(
        {"id": entry_id, "status": {"$in": ["pending", "approved"]}},
        {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc), "paid_by": current_user["id"], "payment_reference": req.payment_reference}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Entry not found or not approvable")
    return {"ok": True, "entry": _clean(res)}


@router.post("/entries/{entry_id}/reverse")
async def reverse_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    res = await entries_col.find_one_and_update(
        {"id": entry_id, "status": {"$nin": ["reversed"]}},
        {"$set": {"status": "reversed", "reversed_at": datetime.now(timezone.utc), "reversed_by": current_user["id"]}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"ok": True, "entry": _clean(res)}
