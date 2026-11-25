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
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Response, Query

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
ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}


# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────
class TargetCreateRequest(BaseModel):
    user_id: str
    period_type: str  # "daily" | "weekly" | "monthly" | "quarterly"
    period_year: int
    period_month: Optional[int] = None
    period_quarter: Optional[int] = None
    period_week: Optional[int] = None
    period_date: Optional[str] = None  # YYYY-MM-DD for daily
    revenue: float = Field(0.0, ge=0)
    pa_count: int = Field(0, ge=0)
    leads: Optional[int] = Field(0, ge=0)
    calls: Optional[int] = Field(0, ge=0)
    follow_ups: Optional[int] = Field(0, ge=0)
    conversions: Optional[int] = Field(0, ge=0)
    notes: Optional[str] = ""


class TargetUpdateRequest(BaseModel):
    revenue: Optional[float] = Field(None, ge=0)
    pa_count: Optional[int] = Field(None, ge=0)
    leads: Optional[int] = Field(None, ge=0)
    calls: Optional[int] = Field(None, ge=0)
    follow_ups: Optional[int] = Field(None, ge=0)
    conversions: Optional[int] = Field(None, ge=0)
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
    r = str(user.get("role", "")).lower()
    rr = str(user.get("rbac_role", "")).lower()
    return r in ADMIN_ROLES or rr in ADMIN_ROLES or "admin" in r or "admin" in rr


def _is_head(user: dict) -> bool:
    return user.get("rbac_role") in HEAD_ROLES or user.get("role") in HEAD_ROLES


def _is_manager(user: dict) -> bool:
    return user.get("rbac_role") in MANAGER_ROLES or user.get("role") in MANAGER_ROLES


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
        if "period_type" in d:
            d["period_label"] = format_period_label(d)
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
        start, end = get_period_bounds(
            req.period_type,
            req.period_year,
            req.period_month,
            req.period_quarter,
            req.period_week,
            req.period_date,
        )
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
        "deleted_at": None,
    }
    if req.period_type == "daily":
        unique_q["period_date"] = req.period_date
    elif req.period_type == "weekly":
        unique_q["period_week"] = req.period_week
    elif req.period_type == "monthly":
        unique_q["period_month"] = req.period_month
    elif req.period_type == "quarterly":
        unique_q["period_quarter"] = req.period_quarter

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
        "period_week": req.period_week,
        "period_date": req.period_date,
        "period_start": start,
        "period_end": end,
        "targets": {
            "revenue": float(req.revenue or 0),
            "pa_count": int(req.pa_count or 0),
            "leads": int(req.leads or 0),
            "calls": int(req.calls or 0),
            "follow_ups": int(req.follow_ups or 0),
            "conversions": int(req.conversions or 0),
        },
        "achievement": {
            "revenue": 0.0,
            "pa_count": 0,
            "leads": 0,
            "calls": 0,
            "follow_ups": 0,
            "conversions": 0,
            "revenue_percentage": 0,
            "pa_count_percentage": 0,
            "leads_percentage": 0,
            "calls_percentage": 0,
            "follow_ups_percentage": 0,
            "conversions_percentage": 0,
            "overall_percentage": 0,
            "pending": {
                "leads": int(req.leads or 0),
                "calls": int(req.calls or 0),
                "follow_ups": int(req.follow_ups or 0),
                "conversions": int(req.conversions or 0),
                "revenue": float(req.revenue or 0),
                "pa_count": int(req.pa_count or 0),
            },
        },
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
            "new_values": {
                "revenue": float(req.revenue or 0),
                "pa_count": int(req.pa_count or 0),
                "leads": int(req.leads or 0),
                "calls": int(req.calls or 0),
                "follow_ups": int(req.follow_ups or 0),
                "conversions": int(req.conversions or 0),
            },
            "reason": "Initial creation",
        }],
        "deleted_at": None,
    }
    await sales_targets_col.insert_one(target)
    target.pop("_id", None)

    # Immediately compute achievement (handles back-set with existing activity/PAs)
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
    old_values = {
        "revenue": target["targets"].get("revenue"),
        "pa_count": target["targets"].get("pa_count"),
        "leads": target["targets"].get("leads"),
        "calls": target["targets"].get("calls"),
        "follow_ups": target["targets"].get("follow_ups"),
        "conversions": target["targets"].get("conversions"),
        "notes": target.get("notes"),
    }
    new_values = {}

    if req.revenue is not None:
        update_fields["targets.revenue"] = float(req.revenue)
        new_values["revenue"] = float(req.revenue)
    if req.pa_count is not None:
        update_fields["targets.pa_count"] = int(req.pa_count)
        new_values["pa_count"] = int(req.pa_count)
    if req.leads is not None:
        update_fields["targets.leads"] = int(req.leads)
        new_values["leads"] = int(req.leads)
    if req.calls is not None:
        update_fields["targets.calls"] = int(req.calls)
        new_values["calls"] = int(req.calls)
    if req.follow_ups is not None:
        update_fields["targets.follow_ups"] = int(req.follow_ups)
        new_values["follow_ups"] = int(req.follow_ups)
    if req.conversions is not None:
        update_fields["targets.conversions"] = int(req.conversions)
        new_values["conversions"] = int(req.conversions)
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
    """Returns current daily, weekly, monthly, and quarterly targets for the logged-in user."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    iso_y, iso_w, _ = now.isocalendar()
    quarter = (now.month - 1) // 3 + 1

    daily_target = await sales_targets_col.find_one(
        {
            "user_id": current_user["id"],
            "period_type": "daily",
            "period_date": today_str,
            "deleted_at": None,
        },
        {"_id": 0},
    )
    weekly_target = await sales_targets_col.find_one(
        {
            "user_id": current_user["id"],
            "period_type": "weekly",
            "period_year": iso_y,
            "period_week": iso_w,
            "deleted_at": None,
        },
        {"_id": 0},
    )
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

    yearly_target = await sales_targets_col.find_one(
        {
            "user_id": current_user["id"],
            "period_type": "yearly",
            "period_year": now.year,
            "deleted_at": None,
        },
        {"_id": 0},
    )

    # Refresh all before returning (cheap — single user)
    if daily_target:
        daily_target = await recalc_target(daily_target["id"], notify=False) or daily_target
    if weekly_target:
        weekly_target = await recalc_target(weekly_target["id"], notify=False) or weekly_target
    if month_target:
        month_target = await recalc_target(month_target["id"], notify=False) or month_target
    if quarter_target:
        quarter_target = await recalc_target(quarter_target["id"], notify=False) or quarter_target
    if yearly_target:
        yearly_target = await recalc_target(yearly_target["id"], notify=False) or yearly_target
    else:
        # Synthesize real-time Year-to-Date (YTD) performance for current year
        start_y, end_y = get_period_bounds("yearly", now.year)
        ytd_pseudo = {
            "id": f"ytd-{current_user['id']}-{now.year}",
            "user_id": current_user["id"],
            "period_type": "yearly",
            "period_year": now.year,
            "period_start": start_y,
            "period_end": end_y,
            "targets": {
                "revenue": float((month_target.get("targets", {}).get("revenue") if month_target else 0) or 0) * 12,
                "pa_count": int((month_target.get("targets", {}).get("pa_count") if month_target else 0) or 0) * 12,
                "leads": int((month_target.get("targets", {}).get("leads") if month_target else 0) or 0) * 12,
                "calls": int((month_target.get("targets", {}).get("calls") if month_target else 0) or 0) * 12,
                "follow_ups": int((month_target.get("targets", {}).get("follow_ups") if month_target else 0) or 0) * 12,
                "conversions": int((month_target.get("targets", {}).get("conversions") if month_target else 0) or 0) * 12,
            },
            "status": "active",
        }
        ytd_ach = await compute_achievement(ytd_pseudo)
        ytd_pseudo["achievement"] = ytd_ach
        ytd_pseudo["status"] = compute_status(ytd_pseudo, ytd_ach)
        yearly_target = ytd_pseudo

    def enrich(t):
        if not t:
            return None
        t = _strip_id(t)
        try:
            end_dt = datetime.fromisoformat(t["period_end"])
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            start_dt = datetime.fromisoformat(t["period_start"])
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            t["days_remaining"] = days_remaining_in_period(end_dt)
            total_days = max(1, (end_dt - start_dt).days)
            t["total_days"] = total_days
            t["days_elapsed"] = max(0, total_days - t["days_remaining"])
            t["is_active"] = (start_dt <= now < end_dt)
        except Exception:
            t["days_remaining"] = 0
            t["total_days"] = 0
            t["days_elapsed"] = 0
            t["is_active"] = False
        t["period_label"] = format_period_label(t)
        return t

    return {
        "daily": enrich(daily_target),
        "weekly": enrich(weekly_target),
        "monthly": enrich(month_target),
        "quarterly": enrich(quarter_target),
        "yearly": enrich(yearly_target),
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
    today_str = now.strftime("%Y-%m-%d")
    iso_y, iso_w, _ = now.isocalendar()
    quarter = (now.month - 1) // 3 + 1

    daily = await sales_targets_col.find_one(
        {"user_id": user_id, "period_type": "daily", "period_date": today_str, "deleted_at": None},
        {"_id": 0},
    )
    weekly = await sales_targets_col.find_one(
        {"user_id": user_id, "period_type": "weekly", "period_year": iso_y, "period_week": iso_w, "deleted_at": None},
        {"_id": 0},
    )
    monthly = await sales_targets_col.find_one(
        {"user_id": user_id, "period_type": "monthly", "period_year": now.year, "period_month": now.month, "deleted_at": None},
        {"_id": 0},
    )
    quarterly = await sales_targets_col.find_one(
        {"user_id": user_id, "period_type": "quarterly", "period_year": now.year, "period_quarter": quarter, "deleted_at": None},
        {"_id": 0},
    )
    return {
        "user": {"id": target_user["id"], "name": target_user["name"], "role": target_user.get("rbac_role")},
        "daily": _strip_id(daily) if daily else None,
        "weekly": _strip_id(weekly) if weekly else None,
        "monthly": _strip_id(monthly) if monthly else None,
        "quarterly": _strip_id(quarterly) if quarterly else None,
    }


@router.get("/targets/team")
async def get_team_targets(
    period_type: str = "monthly",
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    week: Optional[int] = None,
    date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    if not (_is_manager(current_user) or _is_head(current_user) or _is_admin(current_user)):
        raise HTTPException(status_code=403, detail="Sales manager or higher only")

    now = datetime.now(timezone.utc)
    year = year or now.year
    if period_type == "daily":
        date = date or now.strftime("%Y-%m-%d")
    elif period_type == "weekly":
        iso_y, iso_w, _ = now.isocalendar()
        year = year or iso_y
        week = week or iso_w
    elif period_type == "monthly":
        month = month or now.month
    else:
        quarter = quarter or ((now.month - 1) // 3 + 1)

    # Resolve team member ids
    if _is_admin(current_user) or _is_head(current_user):
        users = await users_col.find({
            "$or": [
                {"rbac_role": {"$in": list(ASSIGNABLE_ROLES)}},
                {"role": {"$in": list(ASSIGNABLE_ROLES)}}
            ],
            "status": "active"
        }, {"_id": 0}).to_list(500)
    else:
        users = await users_col.find({"reports_to": current_user["id"], "status": "active"}, {"_id": 0}).to_list(500)

    out = []
    for u in users:
        q = {"user_id": u["id"], "period_type": period_type, "period_year": year, "deleted_at": None}
        if period_type == "daily":
            q["period_date"] = date
        elif period_type == "weekly":
            q["period_week"] = week
        elif period_type == "monthly":
            q["period_month"] = month
        else:
            q["period_quarter"] = quarter

        t = await sales_targets_col.find_one(q, {"_id": 0})
        if t:
            t = await recalc_target(t["id"], notify=False) or t
        out.append({
            "user": {"id": u["id"], "name": u.get("name"), "email": u.get("email"), "rbac_role": u.get("rbac_role") or u.get("role") or "sales_executive", "reports_to": u.get("reports_to")},
            "target": _strip_id(t) if t else None,
        })
    return {
        "period_type": period_type,
        "period_year": year,
        "period_month": month,
        "period_quarter": quarter,
        "period_week": week,
        "period_date": date,
        "members": out,
    }


@router.get("/targets/reports")
async def get_targets_reports(
    salesperson_id: Optional[str] = None,
    period_type: Optional[str] = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: Optional[str] = "json",
    current_user: dict = Depends(get_current_user),
):
    """Generates salesperson target vs actual performance report with filters and summary totals."""
    is_admin = _is_admin(current_user)
    is_head = _is_head(current_user)
    is_mgr = _is_manager(current_user)

    # Scoping
    if not (is_admin or is_head or is_mgr):
        target_uids = [current_user["id"]]
    elif is_mgr and not (is_admin or is_head):
        team_uids = [u["id"] async for u in users_col.find({"reports_to": current_user["id"]}, {"_id": 0, "id": 1})]
        team_uids.append(current_user["id"])
        if salesperson_id and salesperson_id not in ("all", ""):
            if salesperson_id not in team_uids:
                raise HTTPException(status_code=403, detail="Not authorized to view reports for this salesperson")
            target_uids = [salesperson_id]
        else:
            target_uids = team_uids
    else:
        if salesperson_id and salesperson_id not in ("all", ""):
            target_uids = [salesperson_id]
        else:
            target_uids = None

    q = {"deleted_at": None}
    if target_uids is not None:
        q["user_id"] = {"$in": target_uids} if len(target_uids) > 1 else target_uids[0]

    if period_type and period_type != "all":
        q["period_type"] = period_type

    if start_date:
        try:
            s_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            q["period_start"] = {"$gte": s_dt}
        except Exception:
            pass
    if end_date:
        try:
            e_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            q["period_end"] = {"$lte": e_dt}
        except Exception:
            pass

    cursor = sales_targets_col.find(q, {"_id": 0}).sort("period_start", -1).limit(1000)
    raw_targets = await cursor.to_list(1000)

    rows = []
    tot_targets = {"leads": 0, "calls": 0, "follow_ups": 0, "conversions": 0, "revenue": 0.0, "pa_count": 0}
    tot_actuals = {"leads": 0, "calls": 0, "follow_ups": 0, "conversions": 0, "revenue": 0.0, "pa_count": 0}
    tot_pending = {"leads": 0, "calls": 0, "follow_ups": 0, "conversions": 0, "revenue": 0.0, "pa_count": 0}
    status_counts = {"active": 0, "completed": 0, "exceeded": 0, "missed": 0}

    for t in raw_targets:
        t = await recalc_target(t["id"], notify=False) or t
        t = _strip_id(t)
        t["period_label"] = format_period_label(t)
        rows.append(t)

        st = t.get("status", "active")
        status_counts[st] = status_counts.get(st, 0) + 1

        tg = t.get("targets", {})
        ach = t.get("achievement", {})
        pnd = ach.get("pending", {})

        for m in ["leads", "calls", "follow_ups", "conversions", "pa_count"]:
            tot_targets[m] += int(tg.get(m, 0) or 0)
            tot_actuals[m] += int(ach.get(m, 0) or 0)
            tot_pending[m] += int(pnd.get(m, 0) or 0)
        tot_targets["revenue"] += float(tg.get("revenue", 0) or 0)
        tot_actuals["revenue"] += float(ach.get("revenue", 0) or 0)
        tot_pending["revenue"] += float(pnd.get("revenue", 0) or 0)

    tot_targets["revenue"] = round(tot_targets["revenue"], 2)
    tot_actuals["revenue"] = round(tot_actuals["revenue"], 2)
    tot_pending["revenue"] = round(tot_pending["revenue"], 2)

    summary_pcts = []
    for m in ["leads", "calls", "follow_ups", "conversions", "pa_count"]:
        if tot_targets[m] > 0:
            summary_pcts.append(round((tot_actuals[m] / tot_targets[m] * 100), 2))
    if tot_targets["revenue"] > 0:
        summary_pcts.append(round((tot_actuals["revenue"] / tot_targets["revenue"] * 100), 2))

    overall_avg_pct = round(sum(summary_pcts) / len(summary_pcts), 2) if summary_pcts else 0.0

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Target ID", "Salesperson Name", "Email", "Role", "Period Type", "Period",
            "Leads Target", "Leads Actual", "Leads Pending", "Leads Achievement %",
            "Calls Target", "Calls Actual", "Calls Pending", "Calls Achievement %",
            "Follow-ups Target", "Follow-ups Actual", "Follow-ups Pending", "Follow-ups Achievement %",
            "Conversions Target", "Conversions Actual", "Conversions Pending", "Conversions Achievement %",
            "Revenue Target (₹)", "Revenue Actual (₹)", "Revenue Pending (₹)", "Revenue Achievement %",
            "Overall Achievement %", "Status"
        ])
        for r in rows:
            tg = r.get("targets", {})
            ach = r.get("achievement", {})
            pnd = ach.get("pending", {})
            writer.writerow([
                r.get("id"),
                r.get("user_name"),
                r.get("user_email"),
                r.get("user_role"),
                r.get("period_type"),
                r.get("period_label"),
                tg.get("leads", 0), ach.get("leads", 0), pnd.get("leads", 0), f"{ach.get('leads_percentage', 0)}%",
                tg.get("calls", 0), ach.get("calls", 0), pnd.get("calls", 0), f"{ach.get('calls_percentage', 0)}%",
                tg.get("follow_ups", 0), ach.get("follow_ups", 0), pnd.get("follow_ups", 0), f"{ach.get('follow_ups_percentage', 0)}%",
                tg.get("conversions", 0), ach.get("conversions", 0), pnd.get("conversions", 0), f"{ach.get('conversions_percentage', 0)}%",
                tg.get("revenue", 0), ach.get("revenue", 0), pnd.get("revenue", 0), f"{ach.get('revenue_percentage', 0)}%",
                f"{ach.get('overall_percentage', 0)}%",
                r.get("status"),
            ])
        csv_data = output.getvalue()
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=sales_target_reports_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"},
        )

    return {
        "summary": {
            "total_targets_count": len(rows),
            "status_counts": status_counts,
            "targets": tot_targets,
            "actuals": tot_actuals,
            "pending": tot_pending,
            "overall_achievement_percentage": overall_avg_pct,
        },
        "rows": rows,
    }


@router.get("/targets/department")
async def get_department_targets(
    period_type: str = "monthly",
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    week: Optional[int] = None,
    date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    if not (_is_head(current_user) or _is_admin(current_user) or _is_manager(current_user)):
        raise HTTPException(status_code=403, detail="Sales manager or higher only")
    # Reuses team logic — admin/head see entire sales dept
    return await get_team_targets(
        period_type=period_type,
        year=year,
        month=month,
        quarter=quarter,
        week=week,
        date=date,
        current_user=current_user,
    )


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