"""HR Admin Router — Phase 3A

Endpoints for HR/Admin only:
- GET/PATCH /hr-admin/settings        — attendance_settings (singleton)
- GET/POST/PATCH/DELETE /hr-admin/holidays
- GET/POST/PATCH /hr-admin/leave-types
- GET /hr-admin/approver-config
- POST /hr-admin/approver-config      — set final approver / dept heads
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission
from core.database import (
    attendance_settings_col, holidays_col, leave_types_col,
    users_col,
)

router = APIRouter(prefix="/hr-admin", tags=["HR Admin"])


class SettingsUpdate(BaseModel):
    office_start_time: Optional[str] = None
    office_end_time: Optional[str] = None
    min_work_hours: Optional[float] = None
    late_threshold_minutes: Optional[int] = None
    late_marks_for_leave_deduction: Optional[int] = None
    enforce_work_hours_compensation: Optional[bool] = None
    enforce_sandwich_leave: Optional[bool] = None
    enforce_monthly_cl_limit: Optional[bool] = None
    monthly_cl_limit: Optional[int] = None
    max_consecutive_leave_days: Optional[int] = None
    max_long_leaves_per_year: Optional[int] = None
    long_leave_threshold_days: Optional[int] = None
    auto_mark_lwp_for_unapproved_absence: Optional[bool] = None
    regularization_grace_days: Optional[int] = None
    working_days: Optional[List[int]] = None
    weekly_off_days: Optional[List[int]] = None
    final_approver_logic: Optional[str] = None
    final_approver_user_id: Optional[str] = None
    final_approvers_by_department: Optional[dict] = None
    backup_approver_user_id: Optional[str] = None


class HolidayCreate(BaseModel):
    date: str  # YYYY-MM-DD
    name: str
    type: str = "public"
    is_optional: bool = False
    applicable_locations: List[str] = ["all"]


class HolidayUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    is_optional: Optional[bool] = None
    applicable_locations: Optional[List[str]] = None


class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = None
    annual_quota: Optional[int] = None
    monthly_cap: Optional[int] = None
    max_consecutive: Optional[int] = None
    carry_forward: Optional[bool] = None
    carry_forward_cap: Optional[int] = None
    min_notice_days: Optional[int] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


# ──────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────
@router.get("/settings")
async def get_settings_doc(
    current_user: dict = Depends(require_any_permission(
        "system.view.all", "attendance.view.all"
    )),
):
    s = await attendance_settings_col.find_one({"key": "global"}, {"_id": 0})
    if not s:
        raise HTTPException(status_code=404, detail="Settings not initialized")
    if isinstance(s.get("created_at"), datetime):
        s["created_at"] = s["created_at"].isoformat()
    if isinstance(s.get("updated_at"), datetime):
        s["updated_at"] = s["updated_at"].isoformat()
    return s


@router.patch("/settings")
async def update_settings(
    payload: SettingsUpdate,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "attendance.update.all"
    )),
):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"message": "No changes"}

    # Validate final_approver_user_id if specified
    if "final_approver_user_id" in updates and updates["final_approver_user_id"]:
        existing_u = await users_col.find_one(
            {"id": updates["final_approver_user_id"], "status": "active"},
            {"_id": 0, "id": 1, "name": 1},
        )
        if not existing_u:
            raise HTTPException(status_code=400, detail="final_approver_user_id is not an active user")

    updates["updated_at"] = datetime.now(timezone.utc)
    updates["updated_by"] = current_user["id"]
    await attendance_settings_col.update_one({"key": "global"}, {"$set": updates})
    return {"message": "Settings updated", "fields": list(updates.keys())}


# ──────────────────────────────────────────────────────────────
# Holidays
# ──────────────────────────────────────────────────────────────
@router.get("/holidays")
async def list_holidays(
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    q = {}
    if year:
        q["year"] = year
    items = []
    async for h in holidays_col.find(q, {"_id": 0}).sort("date", 1):
        if isinstance(h.get("created_at"), datetime):
            h["created_at"] = h["created_at"].isoformat()
        items.append(h)
    return items


@router.post("/holidays")
async def create_holiday(
    payload: HolidayCreate,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "attendance.update.all"
    )),
):
    try:
        dt = datetime.strptime(payload.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)")
    existing = await holidays_col.find_one({"date": payload.date}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=400, detail="Holiday already exists on this date")
    doc = {
        "id": str(uuid.uuid4()),
        "date": payload.date,
        "year": dt.year,
        "name": payload.name,
        "type": payload.type,
        "is_optional": payload.is_optional,
        "applicable_locations": payload.applicable_locations,
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user["id"],
    }
    await holidays_col.insert_one(doc)
    return {"message": "Holiday created", "id": doc["id"]}


@router.patch("/holidays/{holiday_id}")
async def update_holiday(
    holiday_id: str,
    payload: HolidayUpdate,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "attendance.update.all"
    )),
):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"message": "No changes"}
    updates["updated_at"] = datetime.now(timezone.utc)
    r = await holidays_col.update_one({"id": holiday_id}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Holiday not found")
    return {"message": "Holiday updated"}


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
    holiday_id: str,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "attendance.update.all"
    )),
):
    r = await holidays_col.delete_one({"id": holiday_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Holiday not found")
    return {"message": "Holiday deleted"}


# ──────────────────────────────────────────────────────────────
# Leave types
# ──────────────────────────────────────────────────────────────
@router.patch("/leave-types/{key}")
async def update_leave_type(
    key: str,
    payload: LeaveTypeUpdate,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "leave.approve.final"
    )),
):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"message": "No changes"}
    updates["updated_at"] = datetime.now(timezone.utc)
    r = await leave_types_col.update_one({"key": key}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Leave type not found")
    return {"message": "Leave type updated"}


# ──────────────────────────────────────────────────────────────
# Approver config
# ──────────────────────────────────────────────────────────────
@router.get("/approver-config")
async def get_approver_config(
    current_user: dict = Depends(require_any_permission(
        "system.view.all", "leave.view.all", "attendance.view.all"
    )),
):
    s = await attendance_settings_col.find_one({"key": "global"}, {"_id": 0})
    if not s:
        raise HTTPException(status_code=404, detail="Settings not initialized")

    out = {
        "final_approver_logic": s.get("final_approver_logic"),
        "final_approver_user_id": s.get("final_approver_user_id"),
        "final_approver_user": None,
        "final_approvers_by_department": s.get("final_approvers_by_department", {}),
        "backup_approver_user_id": s.get("backup_approver_user_id"),
        "backup_approver_user": None,
    }

    if s.get("final_approver_user_id"):
        u = await users_col.find_one(
            {"id": s["final_approver_user_id"]},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "rbac_role": 1, "designation": 1},
        )
        out["final_approver_user"] = u

    if s.get("backup_approver_user_id"):
        u = await users_col.find_one(
            {"id": s["backup_approver_user_id"]},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "rbac_role": 1, "designation": 1},
        )
        out["backup_approver_user"] = u

    return out


@router.get("/eligible-approvers")
async def list_eligible_approvers(
    current_user: dict = Depends(require_any_permission(
        "system.view.all", "leave.view.all"
    )),
):
    """Active internal users who can be set as approvers (Heads, Admin)."""
    items = []
    async for u in users_col.find(
        {
            "user_type": "internal",
            "status": "active",
            "rbac_role": {"$in": [
                "admin_owner", "sales_head", "marketing_head",
                "ops_head", "hr_head", "accounts_head",
                "it_admin", "compliance_officer",
            ]},
        },
        {"_id": 0, "id": 1, "name": 1, "email": 1, "rbac_role": 1,
         "department": 1, "designation": 1, "employee_id": 1, "avatar_url": 1},
    ).sort("name", 1):
        items.append(u)
    return items
