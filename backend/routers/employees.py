"""Employees Router — Phase 2 Employee Portal

Provides CRUD + role mgmt + org chart for internal employees.
Permissions are gated via the RBAC Phase 1 catalog.
"""
import uuid
import secrets
import string
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from core.database import db, users_col
from core.auth import get_current_user, get_password_hash
from core.rbac.dependencies import require_any_permission
from core.rbac.permission_service import PermissionService

router = APIRouter(prefix="/employees", tags=["Employees"])

departments_col = db["departments"]
roles_col = db["roles"]
teams_col = db["teams"]
user_role_history_col = db["user_role_history"]
activity_log_col = db["activity_log"]
notifications_col = db["notifications"]


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────
async def _next_employee_id() -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"LMS-{year}-"
    nums = []
    async for u in users_col.find({"employee_id": {"$regex": f"^{prefix}"}}, {"_id": 0, "employee_id": 1}):
        try:
            nums.append(int(u["employee_id"].split("-")[-1]))
        except (ValueError, IndexError):
            continue
    return f"{prefix}{(max(nums) + 1 if nums else 1):04d}"


def _gen_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _serialize_user(u: dict) -> dict:
    """Strip password + serialize datetimes."""
    out = {k: v for k, v in u.items() if k not in ("password", "_id")}
    for f in ("created_at", "date_of_joining", "date_of_leaving", "last_password_change", "account_locked_until"):
        if isinstance(out.get(f), datetime):
            out[f] = out[f].isoformat()
    return out


async def _log_role_change(user_id: str, changed_from: Optional[str], changed_to: str, changed_by: str, reason: Optional[str] = None):
    await user_role_history_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "changed_from": changed_from,
        "changed_to": changed_to,
        "changed_by": changed_by,
        "reason": reason,
        "effective_date": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    })


# ────────────────────────────────────────────────────────────
# Models
# ────────────────────────────────────────────────────────────
class EmployeeCreate(BaseModel):
    # Basic
    name: str = Field(min_length=2)
    email: EmailStr
    mobile: Optional[str] = ""
    date_of_birth: Optional[str] = None
    # Employment
    department: str
    role: str  # rbac_role key
    designation: Optional[str] = None
    reports_to: Optional[str] = None
    team_id: Optional[str] = None
    date_of_joining: Optional[str] = None
    employment_type: str = "full_time"
    work_mode: str = "onsite"
    work_location: Optional[str] = None
    # Access
    password: Optional[str] = None  # auto-gen if absent
    send_welcome_email: bool = True
    require_2fa: Optional[bool] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    designation: Optional[str] = None
    reports_to: Optional[str] = None
    team_id: Optional[str] = None
    department: Optional[str] = None
    work_location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    emergency_contact: Optional[dict] = None
    avatar_url: Optional[str] = None


class RoleChange(BaseModel):
    new_role: str
    reason: Optional[str] = None


# ────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────
@router.get("")
async def list_employees(
    department: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(require_any_permission("employee.view.all", "user.view.all")),
):
    """List internal employees with filters."""
    query = {"user_type": "internal"}
    if department:
        query["department"] = department
    if role:
        query["rbac_role"] = role
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"employee_id": {"$regex": search, "$options": "i"}},
        ]
    cursor = users_col.find(query, {"_id": 0, "password": 0}).skip(skip).limit(limit).sort("created_at", -1)
    items = [_serialize_user(u) async for u in cursor]
    total = await users_col.count_documents(query)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/stats")
async def employees_stats(current_user: dict = Depends(require_any_permission("employee.view.all", "user.view.all"))):
    """Top-line employee stats for dashboard."""
    base = {"user_type": "internal"}
    total = await users_col.count_documents(base)
    active = await users_col.count_documents({**base, "employment_status": "active"})
    on_leave = await users_col.count_documents({**base, "employment_status": "on_leave"})
    terminated = await users_col.count_documents({**base, "employment_status": {"$in": ["terminated", "resigned"]}})

    # New this month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = await users_col.count_documents({**base, "date_of_joining": {"$gte": month_start}})

    # Department breakdown
    pipeline = [
        {"$match": base},
        {"$group": {"_id": "$department", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    dept_breakdown = []
    async for d in users_col.aggregate(pipeline):
        dept_breakdown.append({"department": d["_id"], "count": d["count"]})

    # Role breakdown
    pipeline_role = [
        {"$match": base},
        {"$group": {"_id": "$rbac_role", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    role_breakdown = []
    async for r in users_col.aggregate(pipeline_role):
        role_breakdown.append({"role": r["_id"], "count": r["count"]})

    return {
        "total": total,
        "active": active,
        "on_leave": on_leave,
        "terminated": terminated,
        "new_this_month": new_this_month,
        "department_breakdown": dept_breakdown,
        "role_breakdown": role_breakdown,
    }


@router.get("/recent")
async def recent_joiners(
    limit: int = 5,
    current_user: dict = Depends(require_any_permission("employee.view.all", "user.view.all")),
):
    cursor = users_col.find(
        {"user_type": "internal", "employment_status": "active"},
        {"_id": 0, "password": 0},
    ).sort("date_of_joining", -1).limit(limit)
    return [_serialize_user(u) async for u in cursor]


@router.get("/org-chart")
async def org_chart(
    current_user: dict = Depends(require_any_permission("employee.view.all", "user.view.all", "team.view.all")),
):
    """Build hierarchical org chart from reports_to relationships."""
    users = []
    async for u in users_col.find({"user_type": "internal"}, {"_id": 0, "password": 0}):
        users.append({
            "id": u["id"],
            "name": u.get("name"),
            "email": u.get("email"),
            "employee_id": u.get("employee_id"),
            "designation": u.get("designation"),
            "department": u.get("department"),
            "rbac_role": u.get("rbac_role"),
            "avatar_url": u.get("avatar_url"),
            "reports_to": u.get("reports_to"),
            "employment_status": u.get("employment_status"),
            "children": [],
        })

    by_id = {u["id"]: u for u in users}
    roots = []
    for u in users:
        parent_id = u.get("reports_to")
        if parent_id and parent_id in by_id:
            by_id[parent_id]["children"].append(u)
        else:
            roots.append(u)

    return {"roots": roots, "total": len(users)}


@router.get("/managers-for-role/{role_key}")
async def managers_for_role(
    role_key: str,
    current_user: dict = Depends(require_any_permission("employee.view.all", "user.view.all")),
):
    """Return active users whose role can be reports_to for the given role.

    Logic: Look up role.reports_to_roles array, find active users whose
    rbac_role is in that list. Used in cascading Add Employee form.
    """
    role = await roles_col.find_one({"key": role_key}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_key}' not found")

    parent_roles = role.get("reports_to_roles", [])
    if not parent_roles:
        # Top-level role — no manager needed
        return []

    items = []
    async for u in users_col.find(
        {
            "rbac_role": {"$in": parent_roles},
            "status": "active",
            "user_type": "internal",
        },
        {"_id": 0, "id": 1, "name": 1, "designation": 1, "email": 1, "rbac_role": 1, "department": 1, "avatar_url": 1},
    ).sort("name", 1):
        items.append(u)
    return items


@router.get("/{employee_id}")
async def get_employee(
    employee_id: str,
    current_user: dict = Depends(require_any_permission("employee.view.all", "user.view.all", "employee.view.own")),
):
    user = await users_col.find_one({"id": employee_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Manager + team info
    manager = None
    if user.get("reports_to"):
        m = await users_col.find_one({"id": user["reports_to"]}, {"_id": 0, "id": 1, "name": 1, "designation": 1, "email": 1, "avatar_url": 1})
        if m:
            manager = m

    # Direct reports
    reports = []
    async for r in users_col.find({"reports_to": employee_id}, {"_id": 0, "id": 1, "name": 1, "designation": 1, "rbac_role": 1, "avatar_url": 1, "employment_status": 1}):
        reports.append(r)

    return {
        **_serialize_user(user),
        "manager": manager,
        "direct_reports": reports,
    }


@router.get("/{employee_id}/history")
async def employee_role_history(
    employee_id: str,
    current_user: dict = Depends(require_any_permission("employee.view.all", "user.view.all")),
):
    items = []
    async for h in user_role_history_col.find({"user_id": employee_id}, {"_id": 0}).sort("effective_date", -1).limit(50):
        if isinstance(h.get("effective_date"), datetime):
            h["effective_date"] = h["effective_date"].isoformat()
        if isinstance(h.get("created_at"), datetime):
            h["created_at"] = h["created_at"].isoformat()
        items.append(h)
    return items


@router.get("/{employee_id}/activity")
async def employee_activity(
    employee_id: str,
    limit: int = 50,
    current_user: dict = Depends(require_any_permission("employee.view.all", "user.view.all", "activity_log.view.all")),
):
    items = []
    async for a in activity_log_col.find({"user_id": employee_id}, {"_id": 0}).sort("created_at", -1).limit(limit):
        if isinstance(a.get("created_at"), datetime):
            a["created_at"] = a["created_at"].isoformat()
        items.append(a)
    return items


@router.post("")
async def create_employee(
    payload: EmployeeCreate,
    current_user: dict = Depends(require_any_permission("employee.create.any", "user.create.any")),
):
    # Validate department + role exist
    dept = await departments_col.find_one({"key": payload.department}, {"_id": 0})
    if not dept:
        raise HTTPException(status_code=400, detail=f"Department '{payload.department}' not found")

    role_doc = await roles_col.find_one({"key": payload.role}, {"_id": 0})
    if not role_doc:
        raise HTTPException(status_code=400, detail=f"Role '{payload.role}' not found")

    if role_doc.get("user_type") not in ("internal", None):
        raise HTTPException(status_code=400, detail=f"Role '{payload.role}' is not an internal employee role")

    # Email uniqueness
    if await users_col.find_one({"email": payload.email}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=400, detail="Email already exists")

    # Build legacy 'role' for backward compat
    legacy_role_map = {
        "admin_owner": "admin",
        "case_manager": "case_manager",
    }
    legacy_role = legacy_role_map.get(payload.role, payload.role)

    password = payload.password or _gen_password()
    emp_id = await _next_employee_id()

    # 2FA: auto-true if hierarchy_level >= 3 OR explicitly requested
    auto_2fa = (role_doc.get("hierarchy_level", 0) >= 3)
    require_2fa = payload.require_2fa if payload.require_2fa is not None else auto_2fa

    now = datetime.now(timezone.utc)
    doj = now
    if payload.date_of_joining:
        try:
            doj = datetime.fromisoformat(payload.date_of_joining.replace("Z", "+00:00"))
        except Exception:
            pass

    user = {
        "id": str(uuid.uuid4()),
        "email": payload.email,
        "password": get_password_hash(password),
        "name": payload.name,
        "mobile": payload.mobile or "",
        "role": legacy_role,                # legacy preserved
        "rbac_role": payload.role,          # new RBAC key
        "user_type": "internal",
        "department": payload.department,
        "designation": payload.designation,
        "reports_to": payload.reports_to,
        "team_id": payload.team_id,
        "employee_id": emp_id,
        "date_of_joining": doj,
        "employment_status": "active",
        "employment_type": payload.employment_type,
        "work_mode": payload.work_mode,
        "work_location": payload.work_location,
        "status": "active",
        "commission_rate": 0.0,
        "permissions": role_doc.get("permissions", []),
        "ui_modules": role_doc.get("ui_modules", []),
        "custom_permissions_granted": [],
        "custom_permissions_revoked": [],
        "two_fa_enabled": False,
        "two_fa_required": require_2fa,
        "two_fa_secret": None,
        "failed_login_count": 0,
        "created_at": now,
        "created_by": current_user["id"],
    }
    if payload.date_of_birth:
        user["date_of_birth"] = payload.date_of_birth

    await users_col.insert_one(user)
    await _log_role_change(user["id"], None, payload.role, current_user["id"], "Initial role assignment")

    # Activity log
    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "employee",
        "entity_id": user["id"],
        "action": "employee_created",
        "details": {"name": payload.name, "email": payload.email, "role": payload.role, "department": payload.department},
        "created_at": now,
    })

    # MOCK welcome email (Resend integration pending)
    welcome_email_sent = False
    if payload.send_welcome_email:
        welcome_email_sent = True  # mocked

    return {
        "id": user["id"],
        "employee_id": emp_id,
        "email": payload.email,
        "temporary_password": password,  # show once for admin to share
        "welcome_email_sent": welcome_email_sent,
        "require_2fa": require_2fa,
        "message": f"Employee {payload.name} created successfully",
    }


@router.patch("/{employee_id}")
async def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    current_user: dict = Depends(require_any_permission("employee.update.all", "user.update.any")),
):
    user = await users_col.find_one({"id": employee_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"message": "No changes"}

    # Validate department if being changed
    if "department" in updates:
        dept = await departments_col.find_one({"key": updates["department"]}, {"_id": 0})
        if not dept:
            raise HTTPException(status_code=400, detail=f"Department '{updates['department']}' not found")

    updates["updated_at"] = datetime.now(timezone.utc)
    await users_col.update_one({"id": employee_id}, {"$set": updates})

    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "employee",
        "entity_id": employee_id,
        "action": "employee_updated",
        "details": updates,
        "created_at": datetime.now(timezone.utc),
    })

    return {"message": "Updated", "updated_fields": list(updates.keys())}


@router.patch("/{employee_id}/role")
async def change_role(
    employee_id: str,
    payload: RoleChange,
    current_user: dict = Depends(require_any_permission("employee.update.all", "user.update.any")),
):
    user = await users_col.find_one({"id": employee_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")

    role_doc = await roles_col.find_one({"key": payload.new_role}, {"_id": 0})
    if not role_doc:
        raise HTTPException(status_code=400, detail=f"Role '{payload.new_role}' not found")

    old_role = user.get("rbac_role")
    if old_role == payload.new_role:
        return {"message": "No change — role is already set"}

    # Update user with new role + refresh cached permissions
    legacy_role_map = {"admin_owner": "admin", "case_manager": "case_manager"}
    legacy_role = legacy_role_map.get(payload.new_role, payload.new_role)

    await users_col.update_one(
        {"id": employee_id},
        {"$set": {
            "rbac_role": payload.new_role,
            "role": legacy_role,
            "department": role_doc.get("department") or user.get("department"),
            "permissions": role_doc.get("permissions", []),
            "ui_modules": role_doc.get("ui_modules", []),
            "updated_at": datetime.now(timezone.utc),
        }}
    )

    await _log_role_change(employee_id, old_role, payload.new_role, current_user["id"], payload.reason)

    # Invalidate RBAC cache (user counts in /roles/{key} would be stale)
    try:
        from routers.rbac_admin import invalidate_cache
        invalidate_cache()
    except Exception:
        pass

    # Notify the employee
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": employee_id,
        "title": "Your role was updated",
        "message": f"Your role has been changed to {role_doc.get('name')}. Please log out and log in again to refresh your access.",
        "type": "role_change",
        "read": False,
        "created_at": datetime.now(timezone.utc),
    })

    return {"message": "Role changed", "from": old_role, "to": payload.new_role}


@router.post("/{employee_id}/deactivate")
async def deactivate_employee(
    employee_id: str,
    reason: str = Query(""),
    current_user: dict = Depends(require_any_permission("employee.terminate.any", "employee.update.all", "user.delete.any")),
):
    user = await users_col.find_one({"id": employee_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    await users_col.update_one(
        {"id": employee_id},
        {"$set": {
            "status": "inactive",
            "employment_status": "terminated",
            "date_of_leaving": datetime.now(timezone.utc),
            "deactivation_reason": reason,
        }}
    )
    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "employee",
        "entity_id": employee_id,
        "action": "employee_deactivated",
        "details": {"reason": reason},
        "created_at": datetime.now(timezone.utc),
    })
    return {"message": "Employee deactivated"}


@router.post("/{employee_id}/reactivate")
async def reactivate_employee(
    employee_id: str,
    current_user: dict = Depends(require_any_permission("employee.update.all", "user.update.any")),
):
    user = await users_col.find_one({"id": employee_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    await users_col.update_one(
        {"id": employee_id},
        {"$set": {
            "status": "active",
            "employment_status": "active",
            "date_of_leaving": None,
            "deactivation_reason": None,
        }}
    )
    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "employee",
        "entity_id": employee_id,
        "action": "employee_reactivated",
        "details": {},
        "created_at": datetime.now(timezone.utc),
    })
    return {"message": "Employee reactivated"}


@router.post("/{employee_id}/reset-password")
async def reset_employee_password(
    employee_id: str,
    current_user: dict = Depends(require_any_permission("employee.update.all", "user.update.any")),
):
    user = await users_col.find_one({"id": employee_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    new_pwd = _gen_password()
    await users_col.update_one(
        {"id": employee_id},
        {"$set": {
            "password": get_password_hash(new_pwd),
            "last_password_change": datetime.now(timezone.utc),
        }}
    )
    return {"message": "Password reset", "temporary_password": new_pwd}
