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
    users_col, db,
)

router = APIRouter(prefix="/hr", tags=["HR Admin"])

# Lightweight audit collection (created lazily)
policy_audit_col = db["policy_audit_log"]


async def _log_audit(actor_id: str, actor_name: str, scope: str, action: str, before: dict, after: dict, note: str = ""):
    """Append a policy-change audit row."""
    try:
        await policy_audit_col.insert_one({
            "id": str(uuid.uuid4()),
            "actor_id": actor_id,
            "actor_name": actor_name,
            "scope": scope,
            "action": action,
            "before": before,
            "after": after,
            "note": note,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:
        pass


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

    # Snapshot before
    before_doc = await attendance_settings_col.find_one({"key": "global"}, {"_id": 0})
    before_snap = {k: before_doc.get(k) for k in updates.keys()} if before_doc else {}

    updates["updated_at"] = datetime.now(timezone.utc)
    updates["updated_by"] = current_user["id"]
    updates["updated_by_name"] = current_user.get("name")
    await attendance_settings_col.update_one({"key": "global"}, {"$set": updates})

    await _log_audit(
        actor_id=current_user["id"],
        actor_name=current_user.get("name"),
        scope="attendance_settings",
        action="update",
        before=before_snap,
        after={k: v for k, v in updates.items() if k not in ("updated_at", "updated_by", "updated_by_name")},
    )
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
    await _log_audit(
        actor_id=current_user["id"], actor_name=current_user.get("name"),
        scope=f"holiday:{payload.date}", action="create", before={},
        after={"name": payload.name, "type": payload.type},
    )
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
    before = await holidays_col.find_one({"id": holiday_id}, {"_id": 0})
    if not before:
        raise HTTPException(status_code=404, detail="Holiday not found")
    updates["updated_at"] = datetime.now(timezone.utc)
    await holidays_col.update_one({"id": holiday_id}, {"$set": updates})
    await _log_audit(
        actor_id=current_user["id"], actor_name=current_user.get("name"),
        scope=f"holiday:{before.get('date')}", action="update",
        before={k: before.get(k) for k in updates.keys() if k != "updated_at"},
        after={k: v for k, v in updates.items() if k != "updated_at"},
    )
    return {"message": "Holiday updated"}


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
    holiday_id: str,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "attendance.update.all"
    )),
):
    before = await holidays_col.find_one({"id": holiday_id}, {"_id": 0})
    r = await holidays_col.delete_one({"id": holiday_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Holiday not found")
    await _log_audit(
        actor_id=current_user["id"], actor_name=current_user.get("name"),
        scope=f"holiday:{(before or {}).get('date')}", action="delete",
        before={"name": (before or {}).get("name")}, after={},
    )
    return {"message": "Holiday deleted"}


@router.post("/holidays/import-indian/{year}")
async def import_indian_holidays(
    year: int,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "attendance.update.all"
    )),
):
    """One-click import of standard 11 India national holidays for the given year."""
    from migrations.attendance_leave_migration import DEFAULT_HOLIDAYS_2026
    if year < 2024 or year > 2030:
        raise HTTPException(status_code=400, detail="Year out of supported range")
    inserted = 0
    skipped = 0
    for h in DEFAULT_HOLIDAYS_2026:
        # Re-map the date to the requested year — preserves month/day
        new_date = f"{year}-{h['date'][5:]}"
        existing = await holidays_col.find_one({"date": new_date}, {"_id": 0, "id": 1})
        if existing:
            skipped += 1
            continue
        await holidays_col.insert_one({
            "id": str(uuid.uuid4()),
            "date": new_date,
            "year": year,
            "name": h["name"],
            "type": h.get("type", "public"),
            "is_optional": False,
            "applicable_locations": ["all"],
            "created_at": datetime.now(timezone.utc),
            "created_by": current_user["id"],
        })
        inserted += 1
    await _log_audit(
        actor_id=current_user["id"], actor_name=current_user.get("name"),
        scope="holidays", action="bulk_import", before={"year": year},
        after={"inserted": inserted, "skipped": skipped},
    )
    return {"message": "Indian holidays imported", "inserted": inserted, "skipped": skipped}


@router.post("/holidays/copy-from/{from_year}/to/{to_year}")
async def copy_holidays_from_year(
    from_year: int,
    to_year: int,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "attendance.update.all"
    )),
):
    """Copy all holidays from from_year to to_year (preserves month/day)."""
    inserted = 0
    skipped = 0
    async for h in holidays_col.find({"year": from_year}, {"_id": 0}):
        new_date = f"{to_year}-{h['date'][5:]}"
        existing = await holidays_col.find_one({"date": new_date}, {"_id": 0, "id": 1})
        if existing:
            skipped += 1
            continue
        await holidays_col.insert_one({
            "id": str(uuid.uuid4()),
            "date": new_date,
            "year": to_year,
            "name": h["name"],
            "type": h.get("type", "public"),
            "is_optional": h.get("is_optional", False),
            "applicable_locations": h.get("applicable_locations", ["all"]),
            "created_at": datetime.now(timezone.utc),
            "created_by": current_user["id"],
        })
        inserted += 1
    return {"message": "Holidays copied", "inserted": inserted, "skipped": skipped}


# ──────────────────────────────────────────────────────────────
# Leave types
# ──────────────────────────────────────────────────────────────
class LeaveTypeCreate(BaseModel):
    key: str = Field(min_length=3, max_length=40, pattern=r"^[a-z][a-z0-9_]+$")
    name: str = Field(min_length=2, max_length=80)
    short_code: str = Field(min_length=1, max_length=8)
    annual_quota: int = Field(default=0, ge=0)
    monthly_cap: int = Field(default=0, ge=0)
    max_consecutive: int = Field(default=7, ge=1, le=365)
    carry_forward: bool = False
    carry_forward_cap: int = Field(default=0, ge=0)
    requires_proof_after_days: int = Field(default=0, ge=0)
    min_notice_days: int = Field(default=0, ge=0)
    color: str = "#6b7280"
    applicable_to: List[str] = ["all"]


@router.get("/leave-types")
async def list_leave_types(current_user: dict = Depends(get_current_user)):
    items = []
    async for lt in leave_types_col.find({}, {"_id": 0}).sort("sort_order", 1):
        if isinstance(lt.get("created_at"), datetime):
            lt["created_at"] = lt["created_at"].isoformat()
        items.append(lt)
    return items


@router.post("/leave-types")
async def create_leave_type(
    payload: LeaveTypeCreate,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "leave.approve.final"
    )),
):
    existing = await leave_types_col.find_one({"key": payload.key}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=400, detail=f"Leave type '{payload.key}' already exists")

    last = await leave_types_col.find_one({}, {"_id": 0, "sort_order": 1}, sort=[("sort_order", -1)])
    sort_order = (last.get("sort_order", 0) + 1) if last else 1

    doc = {
        "id": str(uuid.uuid4()),
        **payload.model_dump(),
        "is_active": True,
        "is_system": False,
        "sort_order": sort_order,
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user["id"],
    }
    await leave_types_col.insert_one(doc)
    await _log_audit(
        actor_id=current_user["id"], actor_name=current_user.get("name"),
        scope="leave_type", action="create", before={}, after=payload.model_dump(),
    )
    return {"message": "Leave type created", "id": doc["id"], "key": doc["key"]}


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
    before_doc = await leave_types_col.find_one({"key": key}, {"_id": 0})
    if not before_doc:
        raise HTTPException(status_code=404, detail="Leave type not found")
    before_snap = {k: before_doc.get(k) for k in updates.keys()}
    updates["updated_at"] = datetime.now(timezone.utc)
    await leave_types_col.update_one({"key": key}, {"$set": updates})
    await _log_audit(
        actor_id=current_user["id"], actor_name=current_user.get("name"),
        scope=f"leave_type:{key}", action="update", before=before_snap,
        after={k: v for k, v in updates.items() if k != "updated_at"},
    )
    return {"message": "Leave type updated"}


@router.delete("/leave-types/{key}")
async def delete_leave_type(
    key: str,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "leave.approve.final"
    )),
):
    lt = await leave_types_col.find_one({"key": key}, {"_id": 0})
    if not lt:
        raise HTTPException(status_code=404, detail="Leave type not found")
    if lt.get("is_system"):
        raise HTTPException(status_code=400, detail="System leave types cannot be deleted; mark inactive instead")
    await leave_types_col.delete_one({"key": key})
    await _log_audit(
        actor_id=current_user["id"], actor_name=current_user.get("name"),
        scope=f"leave_type:{key}", action="delete", before={"name": lt.get("name")}, after={},
    )
    return {"message": "Leave type deleted"}


# ──────────────────────────────────────────────────────────────
# Approver config
# ──────────────────────────────────────────────────────────────
class ApproverConfigUpdate(BaseModel):
    final_approver_logic: Optional[str] = None  # specific_user | by_department | reports_to_chain
    final_approver_user_id: Optional[str] = None
    final_approvers_by_department: Optional[dict] = None
    backup_approver_user_id: Optional[str] = None
    # Optional advanced rules (stored under settings dict)
    allow_skip_l1_emergency: Optional[bool] = None
    allow_manager_self_approve: Optional[bool] = None
    auto_approve_l1_after_days: Optional[int] = None
    auto_approve_final_after_days: Optional[int] = None
    escalate_after_days: Optional[int] = None
    long_leave_requires_dept_head: Optional[bool] = None
    lwp_requires_admin: Optional[bool] = None


@router.get("/approvers/config")
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
        "allow_skip_l1_emergency": s.get("allow_skip_l1_emergency", False),
        "allow_manager_self_approve": s.get("allow_manager_self_approve", False),
        "auto_approve_l1_after_days": s.get("auto_approve_l1_after_days", 0),
        "auto_approve_final_after_days": s.get("auto_approve_final_after_days", 0),
        "escalate_after_days": s.get("escalate_after_days", 3),
        "long_leave_requires_dept_head": s.get("long_leave_requires_dept_head", False),
        "lwp_requires_admin": s.get("lwp_requires_admin", False),
    }

    if s.get("final_approver_user_id"):
        u = await users_col.find_one(
            {"id": s["final_approver_user_id"]},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "rbac_role": 1, "designation": 1, "department": 1},
        )
        out["final_approver_user"] = u

    if s.get("backup_approver_user_id"):
        u = await users_col.find_one(
            {"id": s["backup_approver_user_id"]},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "rbac_role": 1, "designation": 1, "department": 1},
        )
        out["backup_approver_user"] = u

    # Expand dept-wise approver objects
    expanded = {}
    for dept_key, user_id in (s.get("final_approvers_by_department") or {}).items():
        if user_id:
            u = await users_col.find_one(
                {"id": user_id},
                {"_id": 0, "id": 1, "name": 1, "designation": 1},
            )
            expanded[dept_key] = u
    out["final_approvers_by_department_expanded"] = expanded

    return out


@router.patch("/approvers/config")
async def update_approver_config(
    payload: ApproverConfigUpdate,
    current_user: dict = Depends(require_any_permission(
        "system.update.any", "attendance.update.all"
    )),
):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"message": "No changes"}

    # Validate user IDs
    for field in ("final_approver_user_id", "backup_approver_user_id"):
        if updates.get(field):
            u = await users_col.find_one({"id": updates[field], "status": "active"}, {"_id": 0, "id": 1})
            if not u:
                raise HTTPException(status_code=400, detail=f"{field} is not an active user")

    if "final_approvers_by_department" in updates:
        for dept, uid in (updates["final_approvers_by_department"] or {}).items():
            if uid:
                u = await users_col.find_one({"id": uid, "status": "active"}, {"_id": 0, "id": 1})
                if not u:
                    raise HTTPException(status_code=400, detail=f"Dept '{dept}' approver is not an active user")

    before_doc = await attendance_settings_col.find_one({"key": "global"}, {"_id": 0})
    before_snap = {k: (before_doc or {}).get(k) for k in updates.keys()}

    updates["updated_at"] = datetime.now(timezone.utc)
    updates["updated_by"] = current_user["id"]
    await attendance_settings_col.update_one({"key": "global"}, {"$set": updates})

    await _log_audit(
        actor_id=current_user["id"], actor_name=current_user.get("name"),
        scope="approver_config", action="update", before=before_snap,
        after={k: v for k, v in updates.items() if k not in ("updated_at", "updated_by")},
    )
    return {"message": "Approver config updated", "fields": list(updates.keys())}


@router.get("/approvers/simulate/{user_id}")
async def simulate_approval_chain(
    user_id: str,
    current_user: dict = Depends(require_any_permission(
        "system.view.all", "leave.view.all"
    )),
):
    """Simulate the approval chain for any user — useful for HR to verify config."""
    user = await users_col.find_one(
        {"id": user_id},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "department": 1, "rbac_role": 1,
         "designation": 1, "reports_to": 1, "user_type": 1},
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from core.attendance_logic import resolve_approvers
    chain = await resolve_approvers(user)

    return {
        "applicant": user,
        "l1_manager": {
            "user_id": chain["l1_manager_id"],
            "name": chain["l1_manager_name"],
        } if chain["l1_manager_id"] else None,
        "final_approver": {
            "user_id": chain["final_approver_id"],
            "name": chain["final_approver_name"],
        } if chain["final_approver_id"] else None,
        "skips_l1": user["id"] == chain["l1_manager_id"],
        "single_stage": chain["l1_manager_id"] == chain["final_approver_id"],
    }


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
                "sales_manager", "operations_manager",
            ]},
        },
        {"_id": 0, "id": 1, "name": 1, "email": 1, "rbac_role": 1,
         "department": 1, "designation": 1, "employee_id": 1, "avatar_url": 1},
    ).sort("name", 1):
        items.append(u)
    return items


# ──────────────────────────────────────────────────────────────
# Audit Log
# ──────────────────────────────────────────────────────────────
@router.get("/audit-log")
async def list_audit_log(
    scope: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(require_any_permission(
        "system.view.all", "leave.view.all", "attendance.view.all"
    )),
):
    q = {}
    if scope:
        q["scope"] = scope
    items = []
    async for a in policy_audit_col.find(q, {"_id": 0}).sort("created_at", -1).limit(limit):
        if isinstance(a.get("created_at"), datetime):
            a["created_at"] = a["created_at"].isoformat()
        items.append(a)
    return items
