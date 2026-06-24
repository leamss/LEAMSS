"""Portal Hub Router — Phase 21.A

Provides aggregated stats for the unified Portal Hub landing.
Used by /admin/portal-hub to show counts in sidebar groups.
"""
import time
from typing import Dict
from fastapi import APIRouter, Depends

from core.auth import get_current_user
from core.database import (
    users_col, leave_requests_col,
    db,
)

router = APIRouter(prefix="/admin/portal-hub", tags=["Portal Hub"])

# Simple in-process cache (60s TTL)
_cache: Dict[str, dict] = {}
_CACHE_TTL_SEC = 60


def _cache_get(key: str):
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > _CACHE_TTL_SEC:
        _cache.pop(key, None)
        return None
    return entry["data"]


def _cache_set(key: str, data: dict):
    _cache[key] = {"data": data, "ts": time.time()}


@router.get("/stats")
async def portal_hub_stats(current_user: dict = Depends(get_current_user)):
    """Aggregated counts for sidebar groups.

    Returns:
        {
            "employees": {"active": N, "on_leave": N, "total": N},
            "hr": {"pending_leaves": N, "pending_regularizations": N, "policies": N},
            "marketing": {"active_campaigns": N, "draft_campaigns": N, "leads": N},
            "it": {"open_incidents": N},
            "me": {"my_tasks": N, "my_pending_leaves": N}
        }
    """
    cache_key = f"stats:{current_user['id']}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # Employees group
    active_employees = await users_col.count_documents({
        "user_type": "internal", "employment_status": "active"
    })
    on_leave_employees = await users_col.count_documents({
        "user_type": "internal", "employment_status": "on_leave"
    })
    total_employees = await users_col.count_documents({"user_type": "internal"})

    # HR group
    pending_leaves = await leave_requests_col.count_documents({
        "status": {"$in": ["pending_l1", "pending_final"]}
    })
    pending_regs = await db["attendance_regularizations"].count_documents({"status": "pending"})
    policies_count = await db["internal_policies"].count_documents({"status": "active"})

    # Marketing group
    campaigns_col = db["campaigns"]
    active_campaigns = await campaigns_col.count_documents({"status": {"$in": ["scheduled", "sending"]}})
    draft_campaigns = await campaigns_col.count_documents({"status": "draft"})
    leads_count = await db["leads"].count_documents({"stage": {"$nin": ["won", "lost"]}})

    # IT group (placeholder for Slice 4)
    open_incidents = 0

    # Me group
    my_tasks = await db["employee_tasks"].count_documents({
        "assignee_id": current_user["id"],
        "status": {"$in": ["todo", "in_progress", "review"]},
        "archived": {"$ne": True},
    })
    my_pending_leaves = await leave_requests_col.count_documents({
        "user_id": current_user["id"],
        "status": {"$in": ["pending_l1", "pending_final"]}
    })
    my_unread_announcements = await db["announcements"].count_documents({
        "$nor": [{"read_receipts.user_id": current_user["id"]}],
    })

    result = {
        "employees": {
            "active": active_employees,
            "on_leave": on_leave_employees,
            "total": total_employees,
        },
        "hr": {
            "pending_leaves": pending_leaves,
            "pending_regularizations": pending_regs,
            "active_policies": policies_count,
        },
        "marketing": {
            "active_campaigns": active_campaigns,
            "draft_campaigns": draft_campaigns,
            "open_leads": leads_count,
        },
        "it": {
            "open_incidents": open_incidents,
        },
        "me": {
            "my_tasks": my_tasks,
            "my_pending_leaves": my_pending_leaves,
            "unread_announcements": my_unread_announcements,
        },
    }
    _cache_set(cache_key, result)
    return result
