"""RBAC Admin Router — exposes roles, permissions catalog as REST endpoints.

Wraps the Phase 1 seeded data (departments, roles, permissions) for use by
the admin UI (Employee form, role pickers, permission matrix viewer).

Includes simple in-memory TTL cache for hot reads.
"""
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from core.database import db, users_col
from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission

router = APIRouter(tags=["RBAC Admin"])

roles_col = db["roles"]
departments_col = db["departments"]
permissions_col = db["permissions"]


# ────────────────────────────────────────────────────────────
# Simple in-memory TTL cache (cleared on any role/dept update)
# ────────────────────────────────────────────────────────────
_CACHE: dict = {}
_TTL = {"roles": 300, "departments": 300, "permissions": 600}  # seconds


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry["t"] > _TTL.get(key.split(":", 1)[0], 300):
        _CACHE.pop(key, None)
        return None
    return entry["v"]


def _cache_set(key: str, value):
    _CACHE[key] = {"t": time.time(), "v": value}


def invalidate_cache(prefix: str = None):
    """Drop all cache entries (or those with a prefix)."""
    if prefix is None:
        _CACHE.clear()
    else:
        for k in list(_CACHE.keys()):
            if k.startswith(prefix):
                _CACHE.pop(k, None)


def _serialize_role(r: dict) -> dict:
    out = {k: v for k, v in r.items() if k != "_id"}
    for f in ("created_at", "updated_at"):
        if isinstance(out.get(f), datetime):
            out[f] = out[f].isoformat()
    return out


def _serialize_permission(p: dict) -> dict:
    out = {k: v for k, v in p.items() if k != "_id"}
    if isinstance(out.get("created_at"), datetime):
        out["created_at"] = out["created_at"].isoformat()
    return out


# ════════════════════════════════════════════════════════════
# ROLES ENDPOINTS
# ════════════════════════════════════════════════════════════
@router.get("/roles")
async def list_roles(
    department: Optional[str] = None,
    user_type: Optional[str] = None,
    is_system: Optional[bool] = None,
    hide_admin: bool = True,
    current_user: dict = Depends(require_any_permission("user.view.all", "employee.view.all", "system.update.any")),
):
    """List all active roles. Filters: department, user_type, is_system, hide_admin.

    Sorted by hierarchy_level descending (heads first).
    """
    cache_key = f"roles:{department}:{user_type}:{is_system}:{hide_admin}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    query = {"is_active": True}
    if department:
        query["department"] = department
    if user_type:
        query["user_type"] = user_type
    if is_system is not None:
        query["is_system"] = is_system
    if hide_admin:
        query["key"] = {"$ne": "admin_owner"}

    items = []
    async for r in roles_col.find(query, {"_id": 0}).sort([("hierarchy_level", -1), ("name", 1)]):
        items.append(_serialize_role(r))

    _cache_set(cache_key, items)
    return items


@router.get("/roles/by-department/{department_key}")
async def roles_by_department(
    department_key: str,
    current_user: dict = Depends(require_any_permission("user.view.all", "employee.view.all", "system.update.any")),
):
    """Roles filtered by department — used in cascading dropdowns."""
    cache_key = f"roles:dept:{department_key}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Verify dept exists
    dept = await departments_col.find_one({"key": department_key}, {"_id": 0, "key": 1})
    if not dept:
        raise HTTPException(status_code=404, detail=f"Department '{department_key}' not found")

    items = []
    async for r in roles_col.find(
        {"department": department_key, "is_active": True, "key": {"$ne": "admin_owner"}},
        {"_id": 0},
    ).sort("hierarchy_level", -1):
        items.append(_serialize_role(r))

    _cache_set(cache_key, items)
    return items


@router.get("/roles/{role_key}")
async def get_role(
    role_key: str,
    current_user: dict = Depends(require_any_permission("user.view.all", "employee.view.all", "system.update.any")),
):
    """Full role detail with user count + permissions grouped by category."""
    role = await roles_col.find_one({"key": role_key}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_key}' not found")

    # Live user count in this role
    user_count = await users_col.count_documents({"rbac_role": role_key, "status": "active"})

    # Group permissions by category
    perm_keys = role.get("permissions", [])
    grouped: dict = {}
    if perm_keys:
        # Wildcard handling
        if perm_keys == ["*"]:
            grouped["wildcard"] = [{"key": "*", "display_name": "All Permissions (Owner)"}]
        else:
            async for p in permissions_col.find({"key": {"$in": perm_keys}}, {"_id": 0}):
                cat = p.get("category", "other")
                grouped.setdefault(cat, []).append({
                    "key": p["key"],
                    "display_name": p.get("display_name", p["key"]),
                    "risk_level": p.get("risk_level", "low"),
                    "requires_2fa": p.get("requires_2fa", False),
                })
            # Sort each group
            for cat in grouped:
                grouped[cat].sort(key=lambda x: x["key"])

    return {
        **_serialize_role(role),
        "user_count": user_count,
        "permissions_grouped": grouped,
        "total_permissions": len(perm_keys),
        "total_ui_modules": len(role.get("ui_modules", [])),
    }


# ════════════════════════════════════════════════════════════
# PERMISSIONS ENDPOINTS
# ════════════════════════════════════════════════════════════
@router.get("/permissions")
async def list_permissions(
    resource: Optional[str] = None,
    risk_level: Optional[str] = None,
    grouped: bool = Query(True, description="Return permissions grouped by category"),
    current_user: dict = Depends(require_any_permission("system.update.any", "user.view.all")),
):
    """List all permissions in the catalog. Admin-only by default."""
    cache_key = f"permissions:{resource}:{risk_level}:{grouped}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    query = {}
    if resource:
        query["resource"] = resource
    if risk_level:
        query["risk_level"] = risk_level

    items = []
    async for p in permissions_col.find(query, {"_id": 0}).sort([("category", 1), ("key", 1)]):
        items.append(_serialize_permission(p))

    if grouped:
        groups: dict = {}
        for p in items:
            cat = p.get("category", "other")
            groups.setdefault(cat, []).append(p)
        result = {"grouped": groups, "total": len(items)}
    else:
        result = {"items": items, "total": len(items)}

    _cache_set(cache_key, result)
    return result
