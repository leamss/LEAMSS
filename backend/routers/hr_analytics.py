"""Phase 21 Slice 3 Day 2 — HR Analytics Dashboard Backend.

Read-only aggregations across employees, leaves, attendance, onboarding for the HR analytics surface.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from core.database import db, users_col
from core.auth import get_current_user

router = APIRouter(prefix="/hr-analytics", tags=["HR Analytics"])

leave_requests_col = db["leave_requests"]
attendance_logs_col = db["attendance_logs"]
late_marks_col = db["late_marks_tracker"]
onb_workflows_col = db["onboarding_workflows"]


def _is_hr_or_admin(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    rbac = (user.get("rbac_role") or "").lower()
    if role == "admin" or "*" in (user.get("permissions") or []):
        return True
    return any(k in rbac for k in ["hr", "admin", "owner", "head"])


def _gate(user: dict):
    if not _is_hr_or_admin(user):
        raise HTTPException(status_code=403, detail="HR/admin only")


@router.get("/headcount")
async def headcount(department: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    _gate(current_user)
    q: dict = {"user_type": "internal"}
    if department:
        q["department"] = department
    total = await users_col.count_documents(q)
    active = await users_col.count_documents({**q, "employment_status": "active"})
    on_leave = await users_col.count_documents({**q, "employment_status": "on_leave"})
    terminated = await users_col.count_documents({**q, "employment_status": "terminated"})
    return {
        "total": total,
        "active": active,
        "on_leave": on_leave,
        "terminated": terminated,
    }


@router.get("/department-breakdown")
async def department_breakdown(current_user: dict = Depends(get_current_user)):
    _gate(current_user)
    pipeline = [
        {"$match": {"user_type": "internal"}},
        {"$group": {
            "_id": "$department",
            "total": {"$sum": 1},
            "active": {"$sum": {"$cond": [{"$eq": ["$employment_status", "active"]}, 1, 0]}},
        }},
        {"$sort": {"total": -1}},
    ]
    rows = []
    async for r in users_col.aggregate(pipeline):
        rows.append({
            "department": r["_id"] or "Unassigned",
            "total": r["total"],
            "active": r["active"],
        })
    return rows


@router.get("/attrition")
async def attrition(days: int = 365, current_user: dict = Depends(get_current_user)):
    _gate(current_user)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    terminated = await users_col.count_documents({
        "user_type": "internal",
        "employment_status": "terminated",
        "terminated_at": {"$gte": since},
    })
    total = await users_col.count_documents({"user_type": "internal"})
    rate_pct = round(100 * terminated / max(total, 1), 2)
    return {
        "period_days": days,
        "terminated_count": terminated,
        "total_workforce": total,
        "attrition_rate_pct": rate_pct,
    }


@router.get("/leave-patterns")
async def leave_patterns(days: int = 365, current_user: dict = Depends(get_current_user)):
    _gate(current_user)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}, "status": "approved"}},
        {"$group": {
            "_id": "$leave_type_key",
            "count": {"$sum": 1},
            "total_days": {"$sum": "$num_days"},
        }},
        {"$sort": {"count": -1}},
    ]
    rows = []
    async for r in leave_requests_col.aggregate(pipeline):
        rows.append({
            "leave_type": r["_id"],
            "request_count": r["count"],
            "total_days": r.get("total_days") or 0,
        })
    return rows


@router.get("/attendance-summary")
async def attendance_summary(days: int = 30, current_user: dict = Depends(get_current_user)):
    _gate(current_user)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    total_logs = await attendance_logs_col.count_documents({"date": {"$gte": since}})
    late_marks = await late_marks_col.count_documents({"date": {"$gte": since}})
    pipeline = [
        {"$match": {"date": {"$gte": since}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
        }},
    ]
    by_status = {}
    async for r in attendance_logs_col.aggregate(pipeline):
        by_status[r["_id"] or "unknown"] = r["count"]
    return {
        "period_days": days,
        "total_attendance_logs": total_logs,
        "late_marks_count": late_marks,
        "by_status": by_status,
    }


@router.get("/onboarding-completion-rate")
async def onboarding_completion_rate(days: int = 90, current_user: dict = Depends(get_current_user)):
    _gate(current_user)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    total = await onb_workflows_col.count_documents({"started_at": {"$gte": since}})
    completed = await onb_workflows_col.count_documents({
        "started_at": {"$gte": since},
        "status": "completed",
    })
    in_progress = await onb_workflows_col.count_documents({
        "started_at": {"$gte": since},
        "status": "in_progress",
    })
    rate_pct = round(100 * completed / max(total, 1), 2) if total else 0
    return {
        "period_days": days,
        "total_started": total,
        "completed": completed,
        "in_progress": in_progress,
        "completion_rate_pct": rate_pct,
    }


@router.get("/overview")
async def hr_analytics_overview(current_user: dict = Depends(get_current_user)):
    """One-call payload for the dashboard top tiles + headline charts."""
    _gate(current_user)
    hc = await headcount(current_user=current_user)
    attr = await attrition(current_user=current_user)
    att = await attendance_summary(current_user=current_user)
    onb = await onboarding_completion_rate(current_user=current_user)
    dept = await department_breakdown(current_user=current_user)
    leaves = await leave_patterns(current_user=current_user)
    return {
        "headcount": hc,
        "attrition": attr,
        "attendance": att,
        "onboarding": onb,
        "departments": dept,
        "leaves": leaves,
    }
