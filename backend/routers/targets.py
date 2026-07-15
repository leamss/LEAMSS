"""Phase 4B — Sales Targets Router.

Endpoints:
  Admin/Manager:
    POST   /api/sales/targets                       Create target
    PATCH  /api/sales/targets/{id}                  Update (with reason)
    DELETE /api/sales/targets/{id}                  Soft-delete (admin only)
    POST   /api/sales/targets/bulk-set              Apply template to many users
    POST   /api/sales/targets/from-template         Single user from template

  Viewing:
    GET    /api/sales/targets/my                    Own current targets
    GET    /api/sales/targets/my/history            Own last 12 months
    GET    /api/sales/targets/user/{user_id}        Specific user (scoped)
    GET    /api/sales/targets/team                  Team members (manager+)
    GET    /api/sales/targets/department            Dept-wide (sales_head)

  Auto-calc:
    POST   /api/sales/targets/recalculate           All active (admin)
    POST   /api/sales/targets/{id}/recalculate      Single target

  Analytics:
    GET    /api/sales/targets/leaderboard           Top performers
    GET    /api/sales/targets/forecast/{user_id}    Run-rate projection
    GET    /api/sales/targets/insights/{user_id}    Daily pace + recommendations

  Templates:
    GET    /api/sales/target-templates
    POST   /api/sales/target-templates
    PATCH  /api/sales/target-templates/{id}
    DELETE /api/sales/target-templates/{id}
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.database import db, users_col
from core.targets_logic import (
    sales_targets_col,
    target_templates_col,
    get_period_bounds,
    compute_achievement,
    compute_status,
    recalc_target,
    recalc_all_active,
    days_remaining_in_period,
    format_period_label,
    _aware,
)

router = APIRouter(prefix="/sales", tags=["Phase 4B - Sales Targets"])

# Roles that can RECEIVE targets (be the user_id on a target)
ASSIGNABLE_ROLES = {"sales_executive", "sr_sales_executive", "sales_manager"}
# Roles that can SET / VIEW team targets
MANAGER_ROLES = {"sales_manager"}
HEAD_ROLES = {"sales_head"}
ADMIN_ROLES = {"admin", "admin_owner"}


# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────
class TargetCreateRequest(BaseModel):
    user_id: str
    period_type: str  # "monthly" | "quarterly"
    period_year: int
    period_month: Optional[int] = None
    period_quarter: Optional[int] = None
    revenue: float = Field(..., ge=0)
    pa_count: int = Field(..., ge=0)
    notes: Optional[str] = ""


class TargetUpdateRequest(BaseModel):
    revenue: Optional[float] = Field(None, ge=0)
    pa_count: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    reason: str  # required for audit


class BulkSetRequest(BaseModel):
    template_id: str
    user_ids: List[str]
    period_type: str
    period_year: int
    period_month: Optional[int] = None
    period_quarter: Optional[int] = None
    override_existing: bool = False


class FromTemplateRequest(BaseModel):
    template_id: str
    user_id: str
    period_type: str
    period_year: int
    period_month: Optional[int] = None
    period_quarter: Optional[int] = None


class TemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    applicable_roles: List[str] = ["sales_executive"]
    period_type: str = "monthly"
    revenue: float = Field(..., ge=0)
    pa_count: int = Field(..., ge=0)


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    applicable_roles: Optional[List[str]] = None
    period_type: Optional[str] = None
    revenue: Optional[float] = Field(None, ge=0)
    pa_count: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


# ──────────────────────────────────────────────────────────────
# Authorization helpers
# ──────────────────────────────────────────────────────────────
def _is_admin(user: dict) -> bool:
    return user.get("role") in ADMIN_ROLES or user.get("rbac_role") in ADMIN_ROLES


def _is_head(user: dict) -> bool:
    return user.get("rbac_role") in HEAD_ROLES


def _is_manager(user: dict) -> bool:
    return user.get("rbac_role") in MANAGER_ROLES


def _can_set_for_user(setter: dict, target_user: dict) -> bool:
    """Admin/sales_head can set for anyone. Manager can set only for own team (reports_to)."""
    if _is_admin(setter) or _is_head(setter):
        return True
    if _is_manager(setter):
        return target_user.get("reports_to") == setter.get("id")
    return False


def _can_view_user_target(viewer: dict, target_user: dict) -> bool:
    if _is_admin(viewer) or _is_head(viewer):
        return True
    if viewer.get("id") == target_user.get("id"):
        return True
    if _is_manager(viewer):
        return target_user.get("reports_to") == viewer.get("id")
    return False


def _strip_id(d: dict) -> dict:
    if d:
        d.pop("_id", None)
        for k in ("period_start", "period_end", "set_at", "last_updated_at", "last_recalc_at", "created_at", "updated_at"):
            v = d.get(k)
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        # Recurse into history entries
        for entry in (d.get("history") or []):
            for k in ("at",):
                v = entry.get(k)
                if isinstance(v, datetime):
                    entry[k] = v.isoformat()
    return d


# ──────────────────────────────────────────────────────────────
# CREATE / UPDATE / DELETE
# ──────────────────────────────────────────────────────────────
@router.post("/targets")
async def create_target(req: TargetCreateRequest, current_user: dict = Depends(get_current_user)):
    # Validate target user
    target_user = await users_col.find_one({"id": req.user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.get("rbac_role") not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail=f"User role '{target_user.get('rbac_role')}' is not eligible for sales targets")

    # Permission
    if not _can_set_for_user(current_user, target_user):
        raise HTTPException(status_code=403, detail="You cannot set targets for this user")

    # Period bounds
    try:
        start, end = get_period_bounds(req.period_type, req.period_year, req.period_month, req.period_quarter)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    now = datetime.now(timezone.utc)
    # Block past periods (entire period already ended)
    if end <= now:
        raise HTTPException(status_code=400, detail="Cannot set targets for periods that have already ended")

    # Uniqueness check
    unique_q = {
        "user_id": req.user_id,
        "period_type": req.period_type,
        "period_year": req.period_year,
        "period_month": req.period_month,
        "period_quarter": req.period_quarter,
        "deleted_at": None,
    }
    existing = await sales_targets_col.find_one(unique_q, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=409, detail="A target for this user + period already exists. Use PATCH to update.")

    target = {
        "id": str(uuid.uuid4()),
        "user_id": req.user_id,
        "user_role": target_user.get("rbac_role"),
        "user_name": target_user.get("name"),
        "user_email": target_user.get("email"),
        "period_type": req.period_type,
        "period_year": req.period_year,
        "period_month": req.period_month,
        "period_quarter": req.period_quarter,
        "period_start": start,
        "period_end": end,
        "targets": {"revenue": float(req.revenue), "pa_count": int(req.pa_count)},
        "achievement": {"revenue": 0.0, "pa_count": 0, "revenue_percentage": 0, "pa_count_percentage": 0, "overall_percentage": 0},
        "status": "active",
        "set_by": current_user["id"],
        "set_by_name": current_user.get("name"),
        "set_at": now,
        "last_updated_at": now,
        "last_updated_by": current_user["id"],
        "notes": req.notes or "",
        "history": [{
            "action": "created",
            "by": current_user["id"],
            "by_name": current_user.get("name"),
            "at": now,
            "new_values": {"revenue": float(req.revenue), "pa_count": int(req.pa_count)},
            "reason": "Initial creation",
        }],
        "deleted_at": None,
    }
    await sales_targets_col.insert_one(target)
    target.pop("_id", None)

    # Immediately compute achievement (handles back-set with existing PAs)
    updated = await recalc_target(target["id"], notify=False)
    return {"ok": True, "target": _strip_id(updated or target)}


@router.patch("/targets/{target_id}")
async def update_target(target_id: str, req: TargetUpdateRequest, current_user: dict = Depends(get_current_user)):
    if len((req.reason or "").strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason must be at least 5 characters")

    target = await sales_targets_col.find_one({"id": target_id, "deleted_at": None}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    target_user = await users_col.find_one({"id": target["user_id"]}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    if not _can_set_for_user(current_user, target_user):
        raise HTTPException(status_code=403, detail="You cannot modify targets for this user")

    # Block past targets (period ended + not exceeded)
    if _aware(target["period_end"]) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Cannot modify a target whose period has ended")

    now = datetime.now(timezone.utc)
    update_fields = {"last_updated_at": now, "last_updated_by": current_user["id"]}
    old_values = {"revenue": target["targets"].get("revenue"), "pa_count": target["targets"].get("pa_count"), "notes": target.get("notes")}
    new_values = {}

    if req.revenue is not None:
        update_fields["targets.revenue"] = float(req.revenue)
        new_values["revenue"] = float(req.revenue)
    if req.pa_count is not None:
        update_fields["targets.pa_count"] = int(req.pa_count)
        new_values["pa_count"] = int(req.pa_count)
    if req.notes is not None:
        update_fields["notes"] = req.notes
        new_values["notes"] = req.notes

    if not new_values:
        return {"ok": True, "no_change": True}

    history_entry = {
        "action": "updated",
        "by": current_user["id"],
        "by_name": current_user.get("name"),
        "at": now,
        "old_values": old_values,
        "new_values": new_values,
        "reason": req.reason,
    }

    await sales_targets_col.update_one(
        {"id": target_id},
        {"$set": update_fields, "$push": {"history": history_entry}},
    )
    updated = await recalc_target(target_id, notify=False)
    return {"ok": True, "target": _strip_id(updated)}


@router.delete("/targets/{target_id}")
async def delete_target(target_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only — soft-delete is restricted")

    target = await sales_targets_col.find_one({"id": target_id, "deleted_at": None}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if _aware(target["period_start"]) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Cannot delete a target whose period has already started")

    now = datetime.now(timezone.utc)
    await sales_targets_col.update_one(
        {"id": target_id},
        {
            "$set": {"deleted_at": now, "deleted_by": current_user["id"]},
            "$push": {"history": {
                "action": "deleted",
                "by": current_user["id"],
                "by_name": current_user.get("name"),
                "at": now,
                "reason": "Admin soft-delete",
            }},
        },
    )
    return {"ok": True, "deleted": True}


# ──────────────────────────────────────────────────────────────
# BULK + TEMPLATE APPLY
# ──────────────────────────────────────────────────────────────
async def _resolve_template(template_id: str) -> dict:
    tpl = await target_templates_col.find_one({"id": template_id, "is_active": True}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found or inactive")
    return tpl


@router.post("/targets/bulk-set")
async def bulk_set_targets(req: BulkSetRequest, current_user: dict = Depends(get_current_user)):
    if not (_is_admin(current_user) or _is_head(current_user) or _is_manager(current_user)):
        raise HTTPException(status_code=403, detail="Only sales managers and above can bulk-set targets")

    tpl = await _resolve_template(req.template_id)
    try:
        start, end = get_period_bounds(req.period_type, req.period_year, req.period_month, req.period_quarter)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if end <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Cannot set targets for past periods")

    results = {"created": [], "skipped": [], "failed": []}
    for uid in req.user_ids:
        target_user = await users_col.find_one({"id": uid}, {"_id": 0})
        if not target_user or target_user.get("rbac_role") not in ASSIGNABLE_ROLES:
            results["failed"].append({"user_id": uid, "reason": "Invalid user / role"})
            continue
        if not _can_set_for_user(current_user, target_user):
            results["failed"].append({"user_id": uid, "reason": "Not authorized for this user"})
            continue
        existing = await sales_targets_col.find_one({
            "user_id": uid,
            "period_type": req.period_type,
            "period_year": req.period_year,
            "period_month": req.period_month,
            "period_quarter": req.period_quarter,
            "deleted_at": None,
        }, {"_id": 0, "id": 1})
        if existing and not req.override_existing:
            results["skipped"].append({"user_id": uid, "reason": "Target already exists"})
            continue

        now = datetime.now(timezone.utc)
        history_entry = {
            "action": "created" if not existing else "replaced",
            "by": current_user["id"],
            "by_name": current_user.get("name"),
            "at": now,
            "new_values": {"revenue": float(tpl["revenue"]), "pa_count": int(tpl["pa_count"])},
            "reason": f"Bulk-apply template '{tpl['name']}'",
        }
        if existing:
            await sales_targets_col.update_one(
                {"id": existing["id"]},
                {
                    "$set": {
                        "targets.revenue": float(tpl["revenue"]),
                        "targets.pa_count": int(tpl["pa_count"]),
                        "last_updated_at": now,
                        "last_updated_by": current_user["id"],
                    },
                    "$push": {"history": history_entry},
                },
            )
            await recalc_target(existing["id"], notify=False)
            results["created"].append({"user_id": uid, "target_id": existing["id"], "replaced": True})
        else:
            new_t = {
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "user_role": target_user.get("rbac_role"),
                "user_name": target_user.get("name"),
                "user_email": target_user.get("email"),
                "period_type": req.period_type,
                "period_year": req.period_year,
                "period_month": req.period_month,
                "period_quarter": req.period_quarter,
                "period_start": start,
                "period_end": end,
                "targets": {"revenue": float(tpl["revenue"]), "pa_count": int(tpl["pa_count"])},
                "achievement": {"revenue": 0.0, "pa_count": 0, "revenue_percentage": 0, "pa_count_percentage": 0, "overall_percentage": 0},
                "status": "active",
                "set_by": current_user["id"],
                "set_by_name": current_user.get("name"),
                "set_at": now,
                "last_updated_at": now,
                "last_updated_by": current_user["id"],
                "notes": f"From template: {tpl['name']}",
                "template_id": tpl["id"],
                "history": [history_entry],
                "deleted_at": None,
            }
            await sales_targets_col.insert_one(new_t)
            await recalc_target(new_t["id"], notify=False)
            results["created"].append({"user_id": uid, "target_id": new_t["id"], "replaced": False})

    return {"ok": True, "summary": {
        "created": len(results["created"]),
        "skipped": len(results["skipped"]),
        "failed": len(results["failed"]),
    }, "results": results}


@router.post("/targets/from-template")
async def target_from_template(req: FromTemplateRequest, current_user: dict = Depends(get_current_user)):
    body = BulkSetRequest(
        template_id=req.template_id,
        user_ids=[req.user_id],
        period_type=req.period_type,
        period_year=req.period_year,
        period_month=req.period_month,
        period_quarter=req.period_quarter,
        override_existing=False,
    )
    return await bulk_set_targets(body, current_user)


# ──────────────────────────────────────────────────────────────
# VIEW endpoints
# ──────────────────────────────────────────────────────────────
@router.get("/targets/my")
async def get_my_targets(current_user: dict = Depends(get_current_user)):
    """Returns current month + current quarter target for the logged-in user."""
    now = datetime.now(timezone.utc)
    month_target = await sales_targets_col.find_one(
        {
            "user_id": current_user["id"],
            "period_type": "monthly",
            "period_year": now.year,
            "period_month": now.month,
            "deleted_at": None,
        },
        {"_id": 0},
    )
    quarter = (now.month - 1) // 3 + 1
    quarter_target = await sales_targets_col.find_one(
        {
            "user_id": current_user["id"],
            "period_type": "quarterly",
            "period_year": now.year,
            "period_quarter": quarter,
            "deleted_at": None,
        },
        {"_id": 0},
    )

    # Refresh both before returning (cheap — single user)
    if month_target:
        month_target = await recalc_target(month_target["id"], notify=False) or month_target
    if quarter_target:
        quarter_target = await recalc_target(quarter_target["id"], notify=False) or quarter_target

    def enrich(t):
        if not t:
            return None
        t = _strip_id(t)
        # days_remaining calc needs ISO -> datetime; parsed datetime is naive when stored from Mongo,
        # so coerce to UTC-aware before comparing against now() which is aware.
        try:
            end_dt = datetime.fromisoformat(t["period_end"])
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            start_dt = datetime.fromisoformat(t["period_start"])
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            t["days_remaining"] = days_remaining_in_period(end_dt)
            total_days = (end_dt - start_dt).days
            t["total_days"] = total_days
            t["days_elapsed"] = max(0, total_days - t["days_remaining"])
        except Exception:
            t["days_remaining"] = 0
            t["total_days"] = 0
            t["days_elapsed"] = 0
        t["period_label"] = format_period_label(t)
        return t

    return {
        "monthly": enrich(month_target),
        "quarterly": enrich(quarter_target),
    }


@router.get("/targets/my/history")
async def get_my_history(months: int = 12, current_user: dict = Depends(get_current_user)):
    """Returns last N months of monthly targets for the logged-in user."""
    cursor = sales_targets_col.find(
        {
            "user_id": current_user["id"],
            "period_type": "monthly",
            "deleted_at": None,
        },
        {"_id": 0},
    ).sort("period_start", -1).limit(months)
    items = [_strip_id(t) for t in await cursor.to_list(length=months)]
    return {"history": items, "count": len(items)}


@router.get("/targets/user/{user_id}")
async def get_user_target(user_id: str, current_user: dict = Depends(get_current_user)):
    target_user = await users_col.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _can_view_user_target(current_user, target_user):
        raise HTTPException(status_code=403, detail="Not authorized to view this user's targets")
    now = datetime.now(timezone.utc)
    quarter = (now.month - 1) // 3 + 1
    monthly = await sales_targets_col.find_one(
        {"user_id": user_id, "period_type": "monthly", "period_year": now.year, "period_month": now.month, "deleted_at": None},
        {"_id": 0},
    )
    quarterly = await sales_targets_col.find_one(
        {"user_id": user_id, "period_type": "quarterly", "period_year": now.year, "period_quarter": quarter, "deleted_at": None},
        {"_id": 0},
    )
    return {"user": {"id": target_user["id"], "name": target_user["name"], "role": target_user.get("rbac_role")},
            "monthly": _strip_id(monthly) if monthly else None,
            "quarterly": _strip_id(quarterly) if quarterly else None}


@router.get("/targets/team")
async def get_team_targets(
    period_type: str = "monthly",
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    if not (_is_manager(current_user) or _is_head(current_user) or _is_admin(current_user)):
        raise HTTPException(status_code=403, detail="Sales manager or higher only")

    now = datetime.now(timezone.utc)
    year = year or now.year
    if period_type == "monthly":
        month = month or now.month
    else:
        quarter = quarter or ((now.month - 1) // 3 + 1)

    # Resolve team member ids
    if _is_admin(current_user) or _is_head(current_user):
        users = await users_col.find({"rbac_role": {"$in": list(ASSIGNABLE_ROLES)}, "status": "active"}, {"_id": 0}).to_list(500)
    else:
        users = await users_col.find({"reports_to": current_user["id"], "status": "active"}, {"_id": 0}).to_list(500)

    out = []
    for u in users:
        q = {"user_id": u["id"], "period_type": period_type, "period_year": year, "deleted_at": None}
        if period_type == "monthly":
            q["period_month"] = month
        else:
            q["period_quarter"] = quarter
        t = await sales_targets_col.find_one(q, {"_id": 0})
        if t:
            t = await recalc_target(t["id"], notify=False) or t
        out.append({
            "user": {"id": u["id"], "name": u.get("name"), "email": u.get("email"), "rbac_role": u.get("rbac_role"), "reports_to": u.get("reports_to")},
            "target": _strip_id(t) if t else None,
        })
    return {"period_type": period_type, "period_year": year, "period_month": month, "period_quarter": quarter, "members": out}


@router.get("/targets/department")
async def get_department_targets(
    period_type: str = "monthly",
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    if not (_is_head(current_user) or _is_admin(current_user)):
        raise HTTPException(status_code=403, detail="Sales head or admin only")
    # Reuses team logic — admin/head see entire sales dept
    return await get_team_targets(period_type, year, month, quarter, current_user)


# ──────────────────────────────────────────────────────────────
# RECALC endpoints (manual triggers)
# ──────────────────────────────────────────────────────────────
@router.post("/targets/recalculate")
async def recalc_all(current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    return await recalc_all_active(notify=False)


@router.post("/targets/{target_id}/recalculate")
async def recalc_one(target_id: str, current_user: dict = Depends(get_current_user)):
    target = await sales_targets_col.find_one({"id": target_id, "deleted_at": None}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    target_user = await users_col.find_one({"id": target["user_id"]}, {"_id": 0})
    if not target_user or not _can_view_user_target(current_user, target_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = await recalc_target(target_id, notify=True)
    return {"ok": True, "target": _strip_id(updated)}


# ──────────────────────────────────────────────────────────────
# Analytics
# ──────────────────────────────────────────────────────────────
@router.get("/targets/leaderboard")
async def leaderboard(
    period_type: str = "monthly",
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    allowed_viewer_roles = ("sales_executive", "sr_sales_executive")
    if not (_is_manager(current_user) or _is_head(current_user) or _is_admin(current_user)
            or current_user.get("role") in allowed_viewer_roles):
        raise HTTPException(status_code=403, detail="Sales team members only")
    now = datetime.now(timezone.utc)
    q = {
        "period_type": period_type,
        "period_year": now.year,
        "deleted_at": None,
    }
    if period_type == "monthly":
        q["period_month"] = now.month
    else:
        q["period_quarter"] = (now.month - 1) // 3 + 1

    # Manager scope: only own team
    if _is_manager(current_user) and not _is_admin(current_user):
        team_ids = [u["id"] async for u in users_col.find({"reports_to": current_user["id"]}, {"_id": 0, "id": 1})]
        q["user_id"] = {"$in": team_ids}

    cursor = sales_targets_col.find(q, {"_id": 0}).limit(500)
    items = await cursor.to_list(length=500)
    for t in items:
        await recalc_target(t["id"], notify=False)
        t["achievement"] = (await sales_targets_col.find_one({"id": t["id"]}, {"_id": 0, "achievement": 1}) or {}).get("achievement") or t.get("achievement")
    items.sort(key=lambda t: (t.get("achievement") or {}).get("overall_percentage", 0), reverse=True)
    return {"period_type": period_type, "top": [_strip_id(t) for t in items[:limit]], "bottom": [_strip_id(t) for t in items[-min(3, len(items)):][::-1]]}


@router.get("/targets/forecast/{user_id}")
async def forecast_user(user_id: str, current_user: dict = Depends(get_current_user)):
    target_user = await users_col.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _can_view_user_target(current_user, target_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    now = datetime.now(timezone.utc)
    t = await sales_targets_col.find_one({
        "user_id": user_id, "period_type": "monthly",
        "period_year": now.year, "period_month": now.month,
        "deleted_at": None,
    }, {"_id": 0})
    if not t:
        return {"has_target": False}
    t = await recalc_target(t["id"], notify=False) or t
    ach = t["achievement"]
    period_start = _aware(t["period_start"])
    period_end = _aware(t["period_end"])
    total_days = max(1, (period_end - period_start).days)
    days_elapsed = max(1, (now - period_start).days)
    days_remaining = max(0, (period_end - now).days)
    run_rate_rev = ach["revenue"] / days_elapsed if days_elapsed > 0 else 0
    run_rate_pa = ach["pa_count"] / days_elapsed if days_elapsed > 0 else 0
    projected_rev = run_rate_rev * total_days
    projected_pa = run_rate_pa * total_days
    rev_target = t["targets"]["revenue"]
    pa_target = t["targets"]["pa_count"]
    rev_gap = max(0, rev_target - ach["revenue"])
    pa_gap = max(0, pa_target - ach["pa_count"])
    daily_required_rev = rev_gap / days_remaining if days_remaining > 0 else float('inf')
    daily_required_pa = pa_gap / days_remaining if days_remaining > 0 else float('inf')
    return {
        "has_target": True,
        "target_id": t["id"],
        "current_achievement": ach,
        "projected": {
            "revenue": round(projected_rev, 2),
            "pa_count": round(projected_pa, 2),
            "revenue_percentage": round((projected_rev / rev_target * 100) if rev_target > 0 else 0, 2),
            "pa_count_percentage": round((projected_pa / pa_target * 100) if pa_target > 0 else 0, 2),
        },
        "daily_required": {
            "revenue": round(daily_required_rev, 2) if daily_required_rev != float('inf') else None,
            "pa_count": round(daily_required_pa, 2) if daily_required_pa != float('inf') else None,
        },
        "days_remaining": days_remaining,
        "days_elapsed": days_elapsed,
    }


@router.get("/targets/insights/{user_id}")
async def insights_user(user_id: str, current_user: dict = Depends(get_current_user)):
    forecast = await forecast_user(user_id, current_user)
    if not forecast.get("has_target"):
        return {"has_target": False}
    proj_pct = forecast["projected"]["revenue_percentage"]
    if proj_pct >= 110:
        verdict = "ahead"
        message = "Excellent pace! You're on track to exceed your target."
    elif proj_pct >= 95:
        verdict = "on_track"
        message = "Solid pace — you'll hit your target if you maintain this rhythm."
    elif proj_pct >= 70:
        verdict = "needs_push"
        message = "You need to step up — increase daily activity to recover ground."
    else:
        verdict = "behind"
        message = "Significantly behind. Consider escalating to your manager for support."
    return {**forecast, "verdict": verdict, "message": message}


# ──────────────────────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────────────────────
@router.get("/target-templates")
async def list_templates(current_user: dict = Depends(get_current_user)):
    items = await target_templates_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    for it in items:
        if isinstance(it.get("created_at"), datetime):
            it["created_at"] = it["created_at"].isoformat()
    return {"templates": items}


@router.post("/target-templates")
async def create_template(req: TemplateCreateRequest, current_user: dict = Depends(get_current_user)):
    if not (_is_admin(current_user) or _is_head(current_user)):
        raise HTTPException(status_code=403, detail="Admin or sales_head only")
    tpl = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "description": req.description or "",
        "applicable_roles": req.applicable_roles,
        "period_type": req.period_type,
        "revenue": float(req.revenue),
        "pa_count": int(req.pa_count),
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    await target_templates_col.insert_one(tpl)
    tpl.pop("_id", None)
    tpl["created_at"] = tpl["created_at"].isoformat()
    return {"ok": True, "template": tpl}


@router.patch("/target-templates/{template_id}")
async def update_template(template_id: str, req: TemplateUpdateRequest, current_user: dict = Depends(get_current_user)):
    if not (_is_admin(current_user) or _is_head(current_user)):
        raise HTTPException(status_code=403, detail="Admin or sales_head only")
    update = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    if not update:
        return {"ok": True, "no_change": True}
    res = await target_templates_col.update_one({"id": template_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}


@router.delete("/target-templates/{template_id}")
async def delete_template(template_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    res = await target_templates_col.update_one({"id": template_id}, {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True, "deactivated": True}