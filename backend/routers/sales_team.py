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
targets_col = db["sales_targets"]


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


# ===================== PHASE 3 — MANAGER DASHBOARD =====================
def _parse_month(month_str: Optional[str]):
    """Returns (start_dt, end_dt, label) for YYYY-MM or current month if None."""
    now = _now()
    if month_str:
        try:
            y, m = map(int, month_str.split("-"))
        except Exception:
            raise HTTPException(status_code=400, detail="month must be YYYY-MM")
    else:
        y, m = now.year, now.month
    start = datetime(y, m, 1, tzinfo=timezone.utc)
    if m == 12:
        end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(y, m + 1, 1, tzinfo=timezone.utc)
    return start, end, f"{y:04d}-{m:02d}"


# Pipeline stages tracked in the team pipeline view (early → late funnel)
PIPELINE_STAGES = [
    "new", "partner_review", "approved", "proposal_sent",
    "proposal_paid", "awaiting_final_approval", "case_created",
]
# Revenue-realizing stages (a PA contributes to monthly revenue once it hits any of these)
CLOSED_STAGES = ["proposal_paid", "awaiting_final_approval", "case_created"]


async def _scope_reps(current_user: dict) -> List[dict]:
    """Returns the list of in-house employee users this manager / admin can see."""
    role = current_user.get("role")
    q = {"employment_type": "employee", "status": "active"}
    if role == "sales_manager":
        q["manager_id"] = current_user["id"]
    reps = await users_col.find(q, {"_id": 0, "password": 0}).to_list(500)
    return reps


@router.get("/manager-dashboard")
async def manager_dashboard(
    month: Optional[str] = Query(None, description="YYYY-MM, default current month"),
    current_user: dict = Depends(get_current_user),
):
    """Comprehensive Manager / Admin dashboard.
    Admin sees all in-house employees; sales_manager sees only `manager_id == self`.

    Returns: top stats + per-rep performance + pipeline by stage + pending approvals summary.
    """
    _manager_or_admin(current_user)
    start, end, month_label = _parse_month(month)
    cfg = await _get_tier_config()

    reps = await _scope_reps(current_user)
    rep_ids = [r["id"] for r in reps]

    # ─── Per-rep aggregation (closed revenue + deals this month) ───
    rep_perf = []
    team_revenue = 0.0
    team_deals = 0
    if rep_ids:
        agg = pa_col.aggregate([
            {"$match": {
                "partner_id": {"$in": rep_ids},
                "stage": {"$in": CLOSED_STAGES},
                "proposal_fee": {"$exists": True, "$ne": None},
                "updated_at": {"$gte": start, "$lt": end},
            }},
            {"$group": {"_id": "$partner_id", "revenue": {"$sum": "$proposal_fee"}, "deals": {"$sum": 1}}},
        ])
        rev_map = {doc["_id"]: doc async for doc in agg}

        # Fetch targets for the month
        target_docs = await targets_col.find(
            {"rep_id": {"$in": rep_ids}, "month": month_label}, {"_id": 0}
        ).to_list(500)
        target_map = {t["rep_id"]: t for t in target_docs}

        for r in reps:
            rdoc = rev_map.get(r["id"], {})
            revenue = float(rdoc.get("revenue", 0.0))
            deals = int(rdoc.get("deals", 0))
            tier = next((t for t in cfg["tiers"] if revenue >= t["min_revenue"] and (t.get("max_revenue") is None or revenue < t["max_revenue"])), cfg["tiers"][0])
            tgt = target_map.get(r["id"], {})
            target_rev = float(tgt.get("target_revenue", 0))
            target_deals = int(tgt.get("target_deals", 0))
            attainment_pct = round((revenue / target_rev) * 100, 1) if target_rev > 0 else None
            rep_perf.append({
                "id": r["id"],
                "name": r.get("name"),
                "email": r.get("email"),
                "manager_id": r.get("manager_id"),
                "revenue": revenue,
                "deal_count": deals,
                "tier_label": tier["label"],
                "tier_rate_pct": tier["rate_pct"],
                "projected_payout": round(revenue * tier["rate_pct"] / 100, 2),
                "target_revenue": target_rev,
                "target_deals": target_deals,
                "attainment_pct": attainment_pct,
            })
            team_revenue += revenue
            team_deals += deals

    rep_perf.sort(key=lambda r: r["revenue"], reverse=True)

    # ─── Pipeline by stage across all reps (live counts, not month-bound) ───
    pipeline_by_stage = []
    if rep_ids:
        stage_agg = pa_col.aggregate([
            {"$match": {"partner_id": {"$in": rep_ids}}},
            {"$group": {
                "_id": "$stage",
                "count": {"$sum": 1},
                "value": {"$sum": {"$ifNull": ["$proposal_fee", 0]}},
            }},
        ])
        stage_map = {doc["_id"]: doc async for doc in stage_agg}
        for s in PIPELINE_STAGES:
            d = stage_map.get(s, {})
            pipeline_by_stage.append({
                "stage": s,
                "count": int(d.get("count", 0)),
                "value": float(d.get("value", 0.0)),
            })

    # ─── Pending approvals (in scope) ───
    pending_q = {"status": "pending"}
    if current_user.get("role") == "sales_manager":
        # Manager sees only their team's requests + manager-level
        pending_q["requester_id"] = {"$in": rep_ids}
        pending_q["level_required"] = "manager"
    pending_count = await disc_col.count_documents(pending_q)
    pending_total_loss = 0.0
    async for d in disc_col.find(pending_q, {"_id": 0, "base_fee": 1, "final_amount": 1}):
        pending_total_loss += float(d.get("base_fee", 0)) - float(d.get("final_amount", 0))

    # ─── Team aggregate target ───
    team_target = sum(rp["target_revenue"] for rp in rep_perf)
    team_attainment = round((team_revenue / team_target) * 100, 1) if team_target > 0 else None

    # ─── Top performer & laggard ───
    top_performer = rep_perf[0] if rep_perf else None
    laggard = rep_perf[-1] if len(rep_perf) > 1 else None

    return {
        "month": month_label,
        "scope": "admin_all" if current_user.get("role") == "admin" else "manager_team",
        "stats": {
            "rep_count": len(reps),
            "team_revenue": team_revenue,
            "team_deals": team_deals,
            "team_target": team_target,
            "team_attainment_pct": team_attainment,
            "pending_approvals": pending_count,
            "pending_discount_value": round(pending_total_loss, 2),
        },
        "reps": rep_perf,
        "pipeline_by_stage": pipeline_by_stage,
        "top_performer": top_performer,
        "laggard": laggard,
        "config_version": cfg.get("version"),
    }


# ─── Targets CRUD ─────────────────────────────────────────────────────────────
class TargetUpsert(BaseModel):
    rep_id: str
    month: str  # YYYY-MM
    target_revenue: float
    target_deals: Optional[int] = 0


@router.post("/targets")
async def upsert_target(body: TargetUpsert, current_user: dict = Depends(get_current_user)):
    """Set / update a monthly target for an in-house employee.
    Admin: anyone. Sales-manager: only their direct reports.
    """
    _manager_or_admin(current_user)
    rep = await users_col.find_one({"id": body.rep_id}, {"_id": 0, "id": 1, "name": 1, "email": 1, "employment_type": 1, "manager_id": 1})
    if not rep:
        raise HTTPException(status_code=404, detail="Rep not found")
    if rep.get("employment_type") != "employee":
        raise HTTPException(status_code=400, detail="Targets only apply to in-house employees")
    if current_user.get("role") == "sales_manager" and rep.get("manager_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only set targets for your direct reports")

    if body.target_revenue < 0 or (body.target_deals or 0) < 0:
        raise HTTPException(status_code=400, detail="Target must be non-negative")

    # Validate month
    _parse_month(body.month)  # raises if bad format

    now = _now()
    existing = await targets_col.find_one({"rep_id": body.rep_id, "month": body.month}, {"_id": 0, "id": 1})
    if existing:
        await targets_col.update_one(
            {"id": existing["id"]},
            {"$set": {
                "target_revenue": body.target_revenue,
                "target_deals": int(body.target_deals or 0),
                "updated_at": now,
                "updated_by": current_user["id"],
                "updated_by_name": current_user.get("name") or current_user.get("email"),
            }},
        )
        return {"ok": True, "id": existing["id"], "action": "updated"}

    rec = {
        "id": str(uuid.uuid4()),
        "rep_id": body.rep_id,
        "rep_name": rep.get("name"),
        "month": body.month,
        "target_revenue": body.target_revenue,
        "target_deals": int(body.target_deals or 0),
        "set_by": current_user["id"],
        "set_by_name": current_user.get("name") or current_user.get("email"),
        "created_at": now,
        "updated_at": now,
    }
    await targets_col.insert_one(rec)
    return {"ok": True, "id": rec["id"], "action": "created"}


@router.get("/targets")
async def list_targets(
    month: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    _manager_or_admin(current_user)
    _, _, month_label = _parse_month(month)
    reps = await _scope_reps(current_user)
    rep_ids = [r["id"] for r in reps]
    items = []
    if rep_ids:
        cursor = targets_col.find(
            {"rep_id": {"$in": rep_ids}, "month": month_label}, {"_id": 0}
        )
        async for t in cursor:
            for k in ("created_at", "updated_at"):
                if isinstance(t.get(k), datetime):
                    t[k] = t[k].isoformat()
            items.append(t)
    return {"month": month_label, "count": len(items), "items": items}


# ─── Assign rep to a sales-manager ────────────────────────────────────────────
class AssignManagerBody(BaseModel):
    manager_id: Optional[str] = None  # null to detach


@router.post("/reps/{rep_id}/assign-manager")
async def assign_manager(rep_id: str, body: AssignManagerBody, current_user: dict = Depends(get_current_user)):
    """Admin assigns a `manager_id` to a rep (or detaches it with null)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    rep = await users_col.find_one({"id": rep_id}, {"_id": 0, "id": 1, "name": 1, "employment_type": 1})
    if not rep:
        raise HTTPException(status_code=404, detail="Rep not found")
    if rep.get("employment_type") != "employee":
        raise HTTPException(status_code=400, detail="Only in-house employees can be assigned to a manager")
    if body.manager_id:
        mgr = await users_col.find_one({"id": body.manager_id}, {"_id": 0, "id": 1, "role": 1, "name": 1})
        if not mgr:
            raise HTTPException(status_code=404, detail="Manager not found")
        if mgr.get("role") not in ("sales_manager", "admin"):
            raise HTTPException(status_code=400, detail="Selected user is not a sales_manager / admin")
    await users_col.update_one({"id": rep_id}, {"$set": {"manager_id": body.manager_id, "updated_at": _now()}})
    return {"ok": True, "rep_id": rep_id, "manager_id": body.manager_id}


@router.get("/managers")
async def list_managers(current_user: dict = Depends(get_current_user)):
    """List available sales managers (admin sees all; sales_manager sees self)."""
    _manager_or_admin(current_user)
    q = {"role": "sales_manager", "status": "active"}
    if current_user.get("role") == "sales_manager":
        q["id"] = current_user["id"]
    items = await users_col.find(q, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(200)
    return {"count": len(items), "items": items}
