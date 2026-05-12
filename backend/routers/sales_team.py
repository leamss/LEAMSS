"""In-House Sales Team CRM.

Endpoints for:
  • Discount approval workflow — partner requests >5% discount, manager/admin approves
  • Tiered incentive calculator — monthly revenue → commission tier with bonuses/penalties
  • Sales team rollup (admin/manager view)

Behavior gating: 'employment_type' on users
  • external (default for legacy partners)  — current behavior, no extras
  • employee (in-house sales rep)            — tiered incentive, stricter discount cap

Manager linkage: users.manager_id → another user's id (typically a sales_manager role)
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.database import db
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sales-team", tags=["In-House Sales Team"])

users_col = db["users"]
pa_col = db["pre_assessments"]
sales_col = db["sales"]
disc_col = db["discount_requests"]
incentive_cfg_col = db["incentive_configs"]


# ===================== HELPERS =====================
def _now():
    return datetime.now(timezone.utc)


def _employee_only(u):
    if u.get("employment_type") != "employee":
        raise HTTPException(status_code=403, detail="In-house employees only")


def _manager_or_admin(u):
    if u.get("role") == "admin":
        return
    if u.get("role") == "sales_manager":
        return
    raise HTTPException(status_code=403, detail="Manager or admin only")


# ===================== DEFAULT INCENTIVE TIER CONFIG =====================
DEFAULT_TIER_CONFIG = {
    "id": "default",
    "version": 1,
    "tiers": [
        {"min_revenue": 0, "max_revenue": 500000, "rate_pct": 5.0, "label": "Bronze"},
        {"min_revenue": 500000, "max_revenue": 1500000, "rate_pct": 7.0, "label": "Silver"},
        {"min_revenue": 1500000, "max_revenue": None, "rate_pct": 10.0, "label": "Gold"},
    ],
    "penalties": [
        {"trigger": "discount_above_pct", "threshold": 10, "rate_delta_pct": -1.0, "label": "−1% if any deal had discount >10%"},
        {"trigger": "sla_breach_count", "threshold": 1, "rate_delta_pct": -2.0, "label": "−2% per SLA breach (lead untouched 48h)"},
    ],
    "bonuses": [
        {"trigger": "zero_refunds_quarter", "threshold": 0, "rate_delta_pct": 0.5, "label": "+0.5% if zero refunds last quarter"},
        {"trigger": "rep_of_month_flat_inr", "amount": 5000, "label": "₹5,000 flat for Rep of the Month"},
    ],
    "discount_caps": {
        "employee_auto_pct": 5.0,        # employees: <=5% auto-approved
        "employee_manager_pct": 15.0,     # 5-15% needs manager approval
        "employee_admin_pct": 100.0,      # >15% needs admin
        "external_auto_pct": 10.0,        # externals: <=10% auto-approved
        "external_admin_pct": 100.0,      # >10% needs admin
    },
    "updated_at": None,
}


async def _get_tier_config():
    cfg = await incentive_cfg_col.find_one({"id": "default"}, {"_id": 0})
    if not cfg:
        seed = dict(DEFAULT_TIER_CONFIG)
        seed["updated_at"] = _now()
        await incentive_cfg_col.insert_one(seed)
        cfg = seed
    return cfg


# ===================== DISCOUNT APPROVAL =====================
class DiscountRequestCreate(BaseModel):
    pa_id: str
    discount_type: Literal["percentage", "flat"] = "percentage"
    discount_value: float
    base_fee: float
    reason: Optional[str] = None


@router.post("/discount-requests")
async def create_discount_request(body: DiscountRequestCreate, current_user: dict = Depends(get_current_user)):
    """Partner / sales-rep submits a discount request.
    Backend determines required approval level based on discount % + employment_type:
      - within auto cap → auto-approved instantly
      - within manager cap → routed to manager (sales_manager / admin)
      - beyond manager cap → admin only
    """
    if current_user.get("role") not in ("partner", "sales_rep", "admin", "sales_manager"):
        raise HTTPException(status_code=403, detail="Sales role required")

    pa = await pa_col.find_one({"id": body.pa_id}, {"_id": 0, "id": 1, "partner_id": 1, "client_name": 1, "pa_number": 1, "country": 1})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if current_user.get("role") == "partner" and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your PA")

    if body.discount_value <= 0:
        raise HTTPException(status_code=400, detail="Discount must be positive")
    if body.base_fee <= 0:
        raise HTTPException(status_code=400, detail="Base fee must be positive")

    # Compute % discount
    pct = body.discount_value if body.discount_type == "percentage" else (body.discount_value / body.base_fee) * 100
    final_amount = body.base_fee * (1 - pct / 100) if body.discount_type == "percentage" else (body.base_fee - body.discount_value)

    cfg = await _get_tier_config()
    caps = cfg["discount_caps"]
    is_employee = current_user.get("employment_type") == "employee"

    if is_employee:
        if pct <= caps["employee_auto_pct"]:
            level = "auto"
            status = "approved"
        elif pct <= caps["employee_manager_pct"]:
            level = "manager"
            status = "pending"
        else:
            level = "admin"
            status = "pending"
    else:
        if pct <= caps["external_auto_pct"]:
            level = "auto"
            status = "approved"
        else:
            level = "admin"
            status = "pending"

    rec = {
        "id": str(uuid.uuid4()),
        "pa_id": body.pa_id,
        "pa_number": pa.get("pa_number"),
        "client_name": pa.get("client_name"),
        "requester_id": current_user["id"],
        "requester_name": current_user.get("name") or current_user.get("email"),
        "requester_employment_type": current_user.get("employment_type", "external"),
        "discount_type": body.discount_type,
        "discount_value": body.discount_value,
        "discount_pct": round(pct, 2),
        "base_fee": body.base_fee,
        "final_amount": round(final_amount, 2),
        "reason": body.reason,
        "level_required": level,
        "status": status,
        "created_at": _now(),
        "decided_by": current_user["id"] if status == "approved" else None,
        "decided_at": _now() if status == "approved" else None,
        "decision_note": "Auto-approved (within cap)" if status == "approved" else None,
    }
    await disc_col.insert_one(rec)

    return {
        "id": rec["id"], "status": status, "level_required": level,
        "discount_pct": rec["discount_pct"], "final_amount": rec["final_amount"],
        "auto_approved": status == "approved",
    }


@router.get("/discount-requests")
async def list_discount_requests(
    status: Optional[str] = Query(None, description="pending | approved | rejected"),
    mine_only: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    """List discount requests:
      • admin / sales_manager → all pending in their scope
      • partner / sales_rep    → only own requests (mine_only ignored, always own)
    """
    role = current_user.get("role")
    q = {}
    if status:
        q["status"] = status

    if role in ("partner", "sales_rep") or mine_only:
        q["requester_id"] = current_user["id"]
    # admin/sales_manager: all

    items = await disc_col.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    for it in items:
        for k in ("created_at", "decided_at"):
            if isinstance(it.get(k), datetime):
                it[k] = it[k].isoformat()

    stats = {"pending": 0, "approved": 0, "rejected": 0}
    for it in items:
        stats[it["status"]] = stats.get(it["status"], 0) + 1

    return {"count": len(items), "stats": stats, "items": items}


class DecisionBody(BaseModel):
    decision: Literal["approve", "reject"]
    note: Optional[str] = None


@router.post("/discount-requests/{req_id}/decide")
async def decide_discount(req_id: str, body: DecisionBody, current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role not in ("admin", "sales_manager"):
        raise HTTPException(status_code=403, detail="Manager or admin only")

    rec = await disc_col.find_one({"id": req_id}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Request not found")
    if rec["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Already {rec['status']}")

    # Manager can only decide on level_required='manager'; admin on anything
    if role == "sales_manager" and rec["level_required"] == "admin":
        raise HTTPException(status_code=403, detail="Admin approval required for this discount level")

    new_status = "approved" if body.decision == "approve" else "rejected"
    await disc_col.update_one({"id": req_id}, {"$set": {
        "status": new_status,
        "decided_by": current_user["id"],
        "decided_by_name": current_user.get("name") or current_user.get("email"),
        "decided_at": _now(),
        "decision_note": body.note,
    }})
    return {"ok": True, "status": new_status, "id": req_id}


# ===================== INCENTIVE TIER CALCULATOR =====================
@router.get("/incentive-config")
async def get_config(current_user: dict = Depends(get_current_user)):
    """Anyone authenticated can view (transparency); only admin can edit."""
    cfg = await _get_tier_config()
    if isinstance(cfg.get("updated_at"), datetime):
        cfg["updated_at"] = cfg["updated_at"].isoformat()
    return cfg


@router.put("/incentive-config")
async def update_config(body: dict, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    allowed = {k: body[k] for k in ("tiers", "penalties", "bonuses", "discount_caps") if k in body}
    if not allowed:
        raise HTTPException(status_code=400, detail="No editable fields supplied")
    allowed["updated_at"] = _now()
    allowed["version"] = (await _get_tier_config()).get("version", 1) + 1
    await incentive_cfg_col.update_one({"id": "default"}, {"$set": allowed}, upsert=True)
    return {"ok": True, "version": allowed["version"]}


@router.get("/my-incentive")
async def my_incentive(
    month: Optional[str] = Query(None, description="YYYY-MM, default current month"),
    current_user: dict = Depends(get_current_user),
):
    """Calculate current rep's incentive for the given month."""
    if current_user.get("employment_type") != "employee":
        raise HTTPException(status_code=403, detail="In-house employees only — externals use flat commission_rate")

    cfg = await _get_tier_config()
    now = _now()
    if month:
        try:
            y, m = map(int, month.split("-"))
            start = datetime(y, m, 1, tzinfo=timezone.utc)
            if m == 12:
                end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
            else:
                end = datetime(y, m + 1, 1, tzinfo=timezone.utc)
        except Exception:
            raise HTTPException(status_code=400, detail="month must be YYYY-MM")
    else:
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        end = now

    # Sum closed-won revenue for this rep this month
    pipeline = [
        {"$match": {
            "partner_id": current_user["id"],
            "stage": {"$in": ["proposal_paid", "awaiting_final_approval", "case_created"]},
            "proposal_fee": {"$exists": True, "$ne": None},
            "updated_at": {"$gte": start, "$lt": end},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$proposal_fee"}, "count": {"$sum": 1}}},
    ]
    res = await pa_col.aggregate(pipeline).to_list(1)
    revenue = float(res[0]["total"]) if res else 0.0
    deal_count = int(res[0]["count"]) if res else 0

    # Determine tier
    tier = None
    for t in cfg["tiers"]:
        max_r = t.get("max_revenue")
        if revenue >= t["min_revenue"] and (max_r is None or revenue < max_r):
            tier = t
            break
    tier = tier or cfg["tiers"][0]

    base_payout = revenue * tier["rate_pct"] / 100

    # Next tier preview
    next_tier = None
    delta_needed = None
    for t in cfg["tiers"]:
        if t["min_revenue"] > revenue:
            next_tier = t
            delta_needed = t["min_revenue"] - revenue
            break

    return {
        "month": f"{start.year:04d}-{start.month:02d}",
        "revenue": revenue,
        "deal_count": deal_count,
        "current_tier": tier,
        "base_payout": round(base_payout, 2),
        "next_tier": next_tier,
        "revenue_to_next_tier": delta_needed,
        "config_version": cfg.get("version"),
    }


# ===================== TEAM ROLLUP (basic Phase 2 — full dashboard Phase 3) =====================
@router.get("/team-rollup")
async def team_rollup(current_user: dict = Depends(get_current_user)):
    """Manager / admin: summary of their team (manager_id = me) for the current month."""
    _manager_or_admin(current_user)

    q = {"employment_type": "employee", "status": "active"}
    if current_user.get("role") == "sales_manager":
        q["manager_id"] = current_user["id"]

    cfg = await _get_tier_config()
    now = _now()
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    reps = []
    async for u in users_col.find(q, {"_id": 0, "password": 0}):
        pipeline = [
            {"$match": {
                "partner_id": u["id"],
                "stage": {"$in": ["proposal_paid", "awaiting_final_approval", "case_created"]},
                "proposal_fee": {"$exists": True, "$ne": None},
                "updated_at": {"$gte": start, "$lt": now},
            }},
            {"$group": {"_id": None, "total": {"$sum": "$proposal_fee"}, "count": {"$sum": 1}}},
        ]
        res = await pa_col.aggregate(pipeline).to_list(1)
        revenue = float(res[0]["total"]) if res else 0.0
        deal_count = int(res[0]["count"]) if res else 0

        tier = next((t for t in cfg["tiers"] if revenue >= t["min_revenue"] and (t.get("max_revenue") is None or revenue < t["max_revenue"])), cfg["tiers"][0])
        reps.append({
            "id": u["id"], "name": u.get("name"), "email": u.get("email"),
            "revenue": revenue, "deal_count": deal_count,
            "tier_label": tier["label"], "tier_rate_pct": tier["rate_pct"],
            "projected_payout": round(revenue * tier["rate_pct"] / 100, 2),
        })

    reps.sort(key=lambda r: r["revenue"], reverse=True)
    team_total = sum(r["revenue"] for r in reps)
    return {
        "month": f"{start.year:04d}-{start.month:02d}",
        "rep_count": len(reps),
        "team_revenue": team_total,
        "reps": reps,
    }
