"""FastAPI Dependencies for RBAC permission/role checks.

Usage:
    @router.get("/admin-only")
    async def my_route(user = Depends(require_permission("pa.approve.l2"))):
        ...
"""
from fastapi import Depends, HTTPException
from typing import Optional
from core.auth import get_current_user
from core.rbac.permission_service import PermissionService
from core.database import db


def _deny(permission_key: str, user: dict, message: Optional[str] = None):
    raise HTTPException(
        status_code=403,
        detail={
            "error": "permission_denied",
            "message": message or f"You don't have permission: {permission_key}",
            "required": permission_key,
            "your_role": user.get("rbac_role") or user.get("role"),
        },
    )


def require_permission(permission_key: str):
    """Single permission check."""
    async def checker(current_user: dict = Depends(get_current_user)):
        if not PermissionService.has_permission(current_user, permission_key):
            _deny(permission_key, current_user)
        return current_user
    return checker


def require_any_permission(*permission_keys: str, _legacy_role: Optional[str] = None):
    """User must have at least ONE of the listed permissions.

    Phase 21.N Backward-compat shim:
        If `_legacy_role` is passed (e.g. "admin"), users with that legacy `role` value
        are also allowed through — this lets us migrate `if current_user["role"] == "admin"`
        checks one endpoint at a time without big-bang flag flips.

    Examples:
        require_any_permission("marketing.view.all")               # strict
        require_any_permission("marketing.view.all", _legacy_role="admin")  # transitional
    """
    async def checker(current_user: dict = Depends(get_current_user)):
        if _legacy_role and current_user.get("role") == _legacy_role:
            return current_user
        if not PermissionService.has_any_permission(current_user, list(permission_keys)):
            _deny(" | ".join(permission_keys), current_user,
                  message=f"Requires any of: {', '.join(permission_keys)}")
        return current_user
    return checker


def require_all_permissions(*permission_keys: str):
    """User must have ALL of the listed permissions."""
    async def checker(current_user: dict = Depends(get_current_user)):
        if not PermissionService.has_all_permissions(current_user, list(permission_keys)):
            _deny(" & ".join(permission_keys), current_user,
                  message=f"Requires all of: {', '.join(permission_keys)}")
        return current_user
    return checker


def require_role(*role_keys: str):
    """Restrict by exact role key. Honors both legacy 'role' and new 'rbac_role'."""
    async def checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("rbac_role") or current_user.get("role")
        legacy_role = current_user.get("role")
        if user_role not in role_keys and legacy_role not in role_keys:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "role_denied",
                    "message": f"Role '{user_role}' not allowed",
                    "required_roles": list(role_keys),
                    "your_role": user_role,
                },
            )
        return current_user
    return checker


def require_department(*dept_keys: str):
    """Restrict by department membership."""
    async def checker(current_user: dict = Depends(get_current_user)):
        user_dept = current_user.get("department")
        if user_dept not in dept_keys:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "department_denied",
                    "message": f"Department '{user_dept}' not allowed",
                    "required_departments": list(dept_keys),
                    "your_department": user_dept,
                },
            )
        return current_user
    return checker


async def get_resource_with_permission(
    collection_name: str,
    resource_id: str,
    permission_key: str,
    user: dict,
    id_field: str = "id",
):
    """Fetch resource AND verify scoped access in one call.

    Example:
        pa = await get_resource_with_permission(
            "pre_assessments", pa_id, "pa.view.own", user
        )
    """
    col = db[collection_name]
    resource = await col.find_one({id_field: resource_id}, {"_id": 0})
    if not resource:
        raise HTTPException(status_code=404, detail=f"{collection_name} not found")

    if not PermissionService.has_permission(user, permission_key):
        _deny(permission_key, user)

    # Verify scope on the resource
    parts = permission_key.split(".")
    scope = parts[2] if len(parts) >= 3 else "any"
    if scope not in ("all", "any"):
        ok = await PermissionService.check_resource_scope(user, resource, scope)
        if not ok:
            _deny(permission_key, user,
                  message=f"Resource scope mismatch — you can only access {scope}-scoped resources")

    return resource
