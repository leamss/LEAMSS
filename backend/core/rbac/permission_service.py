"""Permission Service — central authority for RBAC permission checks.

Handles:
- Wildcard (*) for admin owners
- Effective permissions = role.permissions + custom_granted - custom_revoked
- Hierarchical scope: all > dept > team > own
- Resource-level scope checks (own/team/dept/all)
"""
from typing import Optional, List
from core.database import db

roles_col = db["roles"]
users_col = db["users"]

# Hierarchy: a user with a wider scope automatically passes narrower scopes
_SCOPE_HIERARCHY = {"all": 4, "dept": 3, "team": 2, "own": 1, "any": 4, "pool": 2}


def _effective_permissions(user: dict) -> List[str]:
    """Return final permission list applying custom grants/revocations."""
    base = set(user.get("permissions") or [])
    granted = set(user.get("custom_permissions_granted") or [])
    revoked = set(user.get("custom_permissions_revoked") or [])
    return list((base | granted) - revoked)


def _parse_key(key: str):
    """Split 'pa.view.own' → ('pa', 'view', 'own'). Returns None for wildcard."""
    if key == "*" or "." not in key:
        return None
    parts = key.split(".")
    if len(parts) < 3:
        return (parts[0], parts[1] if len(parts) > 1 else None, None)
    return (parts[0], parts[1], parts[2])


class PermissionService:
    """Synchronous permission checks. Resource-level scope check is async."""

    # ───────────── Core checks ─────────────
    @staticmethod
    def has_permission(user: dict, permission_key: str) -> bool:
        """Check if user has a specific permission key, considering wildcards & scope hierarchy."""
        if not user:
            return False

        effective = _effective_permissions(user)

        # 1) Owner wildcard
        if "*" in effective:
            return True

        # 2) Exact match
        if permission_key in effective:
            return True

        # 3) Resource-level wildcard (e.g. "pa.*")
        parsed = _parse_key(permission_key)
        if not parsed:
            return False
        resource, action, scope = parsed
        if f"{resource}.*" in effective:
            return True
        if f"{resource}.{action}.*" in effective:
            return True

        # 4) Scope hierarchy — wider scope passes narrower
        required_level = _SCOPE_HIERARCHY.get(scope, 1)
        for ep in effective:
            ep_parsed = _parse_key(ep)
            if not ep_parsed:
                continue
            ep_resource, ep_action, ep_scope = ep_parsed
            if ep_resource != resource or ep_action != action:
                continue
            ep_level = _SCOPE_HIERARCHY.get(ep_scope, 0)
            if ep_level >= required_level:
                return True
        return False

    @staticmethod
    def has_any_permission(user: dict, permission_keys: List[str]) -> bool:
        return any(PermissionService.has_permission(user, k) for k in permission_keys)

    @staticmethod
    def has_all_permissions(user: dict, permission_keys: List[str]) -> bool:
        return all(PermissionService.has_permission(user, k) for k in permission_keys)

    # ───────────── Resource-level scope check ─────────────
    @staticmethod
    async def check_resource_scope(user: dict, resource: dict, scope: str) -> bool:
        """Verify the user's scope rights over a specific resource document.

        scope='own'  → resource owner fields match user.id
        scope='team' → resource creator is in same team_id
        scope='dept' → resource creator is in same department
        scope='all'  → always pass
        """
        if scope in ("all", "any"):
            return True

        user_id = user.get("id")
        if scope == "own":
            owner_fields = ("created_by", "owner_id", "partner_id", "assigned_to",
                            "user_id", "client_user_id", "case_manager_id")
            for f in owner_fields:
                if resource.get(f) == user_id:
                    return True
            return False

        # Get owner of resource to check team/dept membership
        owner_id = (resource.get("created_by") or resource.get("partner_id")
                    or resource.get("assigned_to") or resource.get("user_id"))
        if not owner_id:
            return False

        owner = await users_col.find_one({"id": owner_id}, {"_id": 0})
        if not owner:
            return False

        if scope == "team":
            return bool(user.get("team_id")) and user.get("team_id") == owner.get("team_id")
        if scope == "dept":
            return bool(user.get("department")) and user.get("department") == owner.get("department")
        return False

    # ───────────── Cache management ─────────────
    @staticmethod
    async def refresh_user_permissions(user_id: str) -> Optional[List[str]]:
        """Recompute cached permissions on a user from their role's catalog."""
        user = await users_col.find_one({"id": user_id}, {"_id": 0})
        if not user:
            return None

        role_key = user.get("rbac_role") or user.get("role")
        if not role_key:
            return None

        role = await roles_col.find_one({"key": role_key}, {"_id": 0})
        if not role:
            return None

        perms = role.get("permissions", [])
        ui_modules = role.get("ui_modules", [])
        await users_col.update_one(
            {"id": user_id},
            {"$set": {"permissions": perms, "ui_modules": ui_modules}},
        )
        return perms

    @staticmethod
    async def get_user_modules(user: dict) -> List[str]:
        """Return UI modules the user has access to."""
        cached = user.get("ui_modules")
        if cached is not None:
            return cached
        role_key = user.get("rbac_role") or user.get("role")
        if not role_key:
            return []
        role = await roles_col.find_one({"key": role_key}, {"_id": 0})
        return role.get("ui_modules", []) if role else []
