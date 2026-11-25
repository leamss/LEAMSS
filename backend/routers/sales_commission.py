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
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.database import db, users_col
from core.commission_logic import (
    slabs_col, entries_col, get_user_summary, _period_key,
    ensure_default_slabs, _is_sales_user, get_active_slabs,
    _match_slab, SALES_ROLES,
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


class SalespersonConfigUpdate(BaseModel):
    commission_mode: Optional[Literal["slab", "flat"]] = Field(None, description="slab (tiered) or flat (individual rate)")
    commission_rate: Optional[float] = Field(None, ge=0, le=100, description="Individual flat rate %")
    is_commission_active: Optional[bool] = Field(None, description="Enable or disable commission eligibility")
    reason: Optional[str] = Field(None, max_length=500, description="Audit reason for changes")



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
# Admin: Salesperson Rate & Rules Management
# ══════════════════════════════════════════════════════════════
@router.get("/salespersons")
async def list_salespersons(
    period: Optional[str] = Query(None, description="YYYY-MM"),
    current_user: dict = Depends(get_current_user),
):
    """List all salespersons (even those with 0 sales) with their rate rules and period metrics. Admin only."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    period = period or _period_key()
    all_sales_roles = list(SALES_ROLES | {"sales", "sales_rep", "sales_person", "internal_salesperson"})

    users = await users_col.find(
        {"$or": [
            {"role": {"$in": all_sales_roles}},
            {"rbac_role": {"$in": all_sales_roles}},
        ]},
        {"_id": 0, "password": 0, "password_hash": 0, "hashed_password": 0}
    ).sort("name", 1).to_list(1000)

    user_ids = [u["id"] for u in users if u.get("id")]
    pipeline = [
        {"$match": {"user_id": {"$in": user_ids}, "period": period, "status": {"$ne": "reversed"}}},
        {"$group": {
            "_id": "$user_id",
            "total_revenue": {"$sum": "$revenue"},
            "total_commission": {"$sum": "$commission_amount"},
            "paid": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, "$commission_amount", 0]}},
            "approved": {"$sum": {"$cond": [{"$eq": ["$status", "approved"]}, "$commission_amount", 0]}},
            "pending": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, "$commission_amount", 0]}},
            "deal_count": {"$sum": 1},
        }},
    ]
    stats_cursor = entries_col.aggregate(pipeline)
    stats_map = {row["_id"]: row async for row in stats_cursor}

    slabs = await get_active_slabs()

    salespersons = []
    for u in users:
        uid = u["id"]
        st = stats_map.get(uid, {})
        rev = float(st.get("total_revenue") or 0)
        matched_slab = _match_slab(rev, slabs) if slabs else None

        comm_mode = u.get("commission_mode", "slab")
        indiv_rate = float(u.get("commission_rate") or 0)

        effective_rate = indiv_rate if comm_mode == "flat" else (float(matched_slab["rate_pct"]) if matched_slab else 0.0)

        salespersons.append({
            "id": uid,
            "name": u.get("name") or "Unnamed",
            "email": u.get("email"),
            "role": u.get("role"),
            "rbac_role": u.get("rbac_role"),
            "status": u.get("status", "active"),
            "commission_mode": comm_mode,
            "commission_rate": indiv_rate,
            "is_commission_active": u.get("is_commission_active", True),
            "commission_rate_history": u.get("commission_rate_history", []),
            "current_slab": _clean(matched_slab) if matched_slab else None,
            "effective_rate_pct": effective_rate,
            "rule_display": f"Individual Rate ({indiv_rate}%)" if comm_mode == "flat" else f"Tiered Slab: {matched_slab.get('name', 'None') if matched_slab else 'Bronze'} ({effective_rate}%)",
            "total_revenue": round(rev, 2),
            "total_commission": round(float(st.get("total_commission") or 0), 2),
            "paid": round(float(st.get("paid") or 0), 2),
            "approved": round(float(st.get("approved") or 0), 2),
            "pending": round(float(st.get("pending") or 0), 2),
            "deal_count": int(st.get("deal_count") or 0),
        })

    return {
        "period": period,
        "salespersons": salespersons,
        "count": len(salespersons),
    }


@router.put("/salespersons/{user_id}/config")
async def update_salesperson_commission_config(
    user_id: str,
    req: SalespersonConfigUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Admin endpoint to configure a salesperson's commission mode, flat rate, and active status."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    user = await users_col.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update: dict = {}
    history_entry = {
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "changed_by": current_user["id"],
        "reason": req.reason or "Admin rate adjustment",
        "previous_mode": user.get("commission_mode", "slab"),
        "previous_rate": user.get("commission_rate", 0.0),
        "previous_active": user.get("is_commission_active", True),
    }

    if req.commission_mode is not None:
        update["commission_mode"] = req.commission_mode
        history_entry["new_mode"] = req.commission_mode

    if req.commission_rate is not None:
        update["commission_rate"] = req.commission_rate
        history_entry["new_rate"] = req.commission_rate

    if req.is_commission_active is not None:
        update["is_commission_active"] = req.is_commission_active
        history_entry["new_active"] = req.is_commission_active

    if not update:
        return {"ok": True, "no_change": True}

    update["updated_at"] = datetime.now(timezone.utc)

    await users_col.update_one(
        {"id": user_id},
        {
            "$set": update,
            "$push": {"commission_rate_history": history_entry}
        }
    )

    # Insert into audit log
    audit_logs_col = db["audit_logs"]
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "action": "salesperson_commission_config_updated",
        "entity_type": "user",
        "entity_id": user_id,
        "details": history_entry,
        "created_at": datetime.now(timezone.utc),
    })

    return {"ok": True, "message": "Salesperson commission configuration updated", "config": update}


# ══════════════════════════════════════════════════════════════
# Approve / Mark Paid / Reverse
# ══════════════════════════════════════════════════════════════
class MarkPaidReq(BaseModel):
    payment_reference: Optional[str] = None


@router.post("/entries/{entry_id}/approve")
async def approve_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    existing = await entries_col.find_one({"id": entry_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Maker-checker validation
    if existing.get("user_id") == current_user["id"]:
        raise HTTPException(status_code=403, detail="Maker-checker violation: You cannot approve your own commission payout.")

    if existing.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Entry is not in pending state")

    now = datetime.now(timezone.utc)
    res = await entries_col.find_one_and_update(
        {"id": entry_id, "status": "pending"},
        {"$set": {"status": "approved", "approved_at": now, "approved_by": current_user["id"]}},
        return_document=True,
        projection={"_id": 0},
    )

    # Audit log
    audit_logs_col = db["audit_logs"]
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "action": "commission_entry_approved",
        "entity_type": "sales_commission_entry",
        "entity_id": entry_id,
        "details": {"commission_amount": existing.get("commission_amount"), "recipient_id": existing.get("user_id")},
        "created_at": now,
    })

    return {"ok": True, "entry": _clean(res)}


@router.post("/entries/{entry_id}/mark-paid")
async def mark_paid(entry_id: str, req: MarkPaidReq, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    existing = await entries_col.find_one({"id": entry_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Maker-checker validation
    if existing.get("user_id") == current_user["id"]:
        raise HTTPException(status_code=403, detail="Maker-checker violation: You cannot pay your own commission payout.")

    if existing.get("status") not in ("pending", "approved"):
        raise HTTPException(status_code=400, detail="Entry must be pending or approved to mark as paid")

    now = datetime.now(timezone.utc)
    res = await entries_col.find_one_and_update(
        {"id": entry_id, "status": {"$in": ["pending", "approved"]}},
        {"$set": {
            "status": "paid",
            "paid_at": now,
            "paid_by": current_user["id"],
            "payment_reference": req.payment_reference or ""
        }},
        return_document=True,
        projection={"_id": 0},
    )

    # Audit log
    audit_logs_col = db["audit_logs"]
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "action": "commission_entry_paid",
        "entity_type": "sales_commission_entry",
        "entity_id": entry_id,
        "details": {
            "commission_amount": existing.get("commission_amount"),
            "payment_reference": req.payment_reference,
            "recipient_id": existing.get("user_id")
        },
        "created_at": now,
    })

    return {"ok": True, "entry": _clean(res)}


@router.post("/entries/{entry_id}/reverse")
async def reverse_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    existing = await entries_col.find_one({"id": entry_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found")

    if existing.get("status") == "reversed":
        raise HTTPException(status_code=400, detail="Entry is already reversed")

    now = datetime.now(timezone.utc)
    res = await entries_col.find_one_and_update(
        {"id": entry_id, "status": {"$ne": "reversed"}},
        {"$set": {"status": "reversed", "reversed_at": now, "reversed_by": current_user["id"]}},
        return_document=True,
        projection={"_id": 0},
    )

    # Audit log
    audit_logs_col = db["audit_logs"]
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "action": "commission_entry_reversed",
        "entity_type": "sales_commission_entry",
        "entity_id": entry_id,
        "details": {"commission_amount": existing.get("commission_amount"), "recipient_id": existing.get("user_id")},
        "created_at": now,
    })

    return {"ok": True, "entry": _clean(res)}

