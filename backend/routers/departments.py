"""Departments Router — Phase 2 Employee Portal"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from core.database import db, users_col
from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission

router = APIRouter(prefix="/departments", tags=["Departments"])

departments_col = db["departments"]
roles_col = db["roles"]


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    head_user_id: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


@router.get("")
async def list_departments(current_user: dict = Depends(get_current_user)):
    """List all departments with employee counts."""
    departments = []
    async for d in departments_col.find({}, {"_id": 0}).sort("name", 1):
        # Count employees in this department
        count = await users_col.count_documents({
            "user_type": "internal",
            "department": d["key"],
            "employment_status": "active",
        })
        # Get head info
        head = None
        if d.get("head_user_id"):
            h = await users_col.find_one(
                {"id": d["head_user_id"]},
                {"_id": 0, "id": 1, "name": 1, "designation": 1, "email": 1, "avatar_url": 1}
            )
            if h:
                head = h

        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()

        departments.append({**d, "employee_count": count, "head": head})

    return departments


@router.get("/{dept_key}")
async def get_department(dept_key: str, current_user: dict = Depends(get_current_user)):
    d = await departments_col.find_one({"key": dept_key}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Department not found")
    if isinstance(d.get("created_at"), datetime):
        d["created_at"] = d["created_at"].isoformat()

    count = await users_col.count_documents({
        "user_type": "internal",
        "department": dept_key,
        "employment_status": "active",
    })
    head = None
    if d.get("head_user_id"):
        h = await users_col.find_one(
            {"id": d["head_user_id"]},
            {"_id": 0, "id": 1, "name": 1, "designation": 1, "email": 1, "avatar_url": 1}
        )
        if h:
            head = h
    return {**d, "employee_count": count, "head": head}


@router.get("/{dept_key}/employees")
async def list_dept_employees(
    dept_key: str,
    current_user: dict = Depends(require_any_permission("employee.view.all", "user.view.all", "employee.view.dept")),
):
    items = []
    async for u in users_col.find(
        {"user_type": "internal", "department": dept_key},
        {"_id": 0, "password": 0},
    ).sort("name", 1):
        for f in ("created_at", "date_of_joining"):
            if isinstance(u.get(f), datetime):
                u[f] = u[f].isoformat()
        items.append(u)
    return items


@router.get("/{dept_key}/roles")
async def list_dept_roles(dept_key: str, current_user: dict = Depends(get_current_user)):
    """All roles available for this department (used in Add Employee form)."""
    items = []
    async for r in roles_col.find(
        {"department": dept_key, "is_active": True},
        {"_id": 0}
    ).sort("hierarchy_level", -1):
        for f in ("created_at", "updated_at"):
            if isinstance(r.get(f), datetime):
                r[f] = r[f].isoformat()
        items.append(r)
    return items


@router.patch("/{dept_key}")
async def update_department(
    dept_key: str,
    payload: DepartmentUpdate,
    current_user: dict = Depends(require_any_permission("employee.update.all", "user.update.any", "system.update.any")),
):
    d = await departments_col.find_one({"key": dept_key}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Department not found")

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"message": "No changes"}

    # Validate head_user_id exists
    if "head_user_id" in updates and updates["head_user_id"]:
        head = await users_col.find_one({"id": updates["head_user_id"]}, {"_id": 0, "id": 1})
        if not head:
            raise HTTPException(status_code=400, detail="Head user not found")

    updates["updated_at"] = datetime.now(timezone.utc)
    await departments_col.update_one({"key": dept_key}, {"$set": updates})
    return {"message": "Department updated", "updated_fields": list(updates.keys())}


@router.get("/_meta/roles")
async def list_all_internal_roles(current_user: dict = Depends(get_current_user)):
    """Cross-department lookup of all internal roles (used in form when no dept selected)."""
    items = []
    async for r in roles_col.find(
        {"user_type": "internal", "is_active": True},
        {"_id": 0, "key": 1, "name": 1, "department": 1, "hierarchy_level": 1, "description": 1}
    ).sort([("department", 1), ("hierarchy_level", -1)]):
        items.append(r)
    return items
