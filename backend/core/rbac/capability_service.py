"""Phase 22 — CapabilityService: compute / mutate / audit RBAC v2 capability assignments.

Layer 0: legacy permissions catalog (unchanged)
Layer 1: capability_packs[]  ← what THIS module manages
Layer 2: feature_overrides {granted[], revoked[]}  ← what THIS module manages
Effective features = ∪packs ∪ granted − revoked
Effective permissions = flatten(feature.backend_permissions for f in effective_features)
"""
import uuid
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from fastapi import HTTPException
from core.database import db
from core.rbac.capability_packs_data import (
    CAPABILITY_PACKS,
    FEATURE_CATALOG,
    DEPT_TO_PACKS,
    LEGACY_ROLE_TO_PACKS,
    features_by_pack,
    packs_to_feature_ids,
)

users_col = db["users"]
audit_col = db["rbac_audit_log"]
templates_col = db["rbac_role_templates"]

# Quick lookups
_PACKS_BY_ID = {p["pack_id"]: p for p in CAPABILITY_PACKS}
_FEATURES_BY_ID = {f["feature_id"]: f for f in FEATURE_CATALOG}


def _is_admin_user(actor: dict) -> bool:
    """Only admin_owner / admin can mutate RBAC. Legacy `role` also honoured."""
    rbac_role = actor.get("rbac_role") or actor.get("role")
    return rbac_role in ("admin_owner", "admin")


def _is_owner(actor: dict) -> bool:
    rbac_role = actor.get("rbac_role") or actor.get("role")
    return rbac_role == "admin_owner"


class CapabilityService:

    # ──────────────────────── Compute ────────────────────────

    @staticmethod
    def compute_effective_features(user: dict) -> set:
        packs = user.get("capability_packs") or []
        # Always include baseline_employee for staff with any pack assignment
        if packs and "baseline_employee" not in packs:
            packs = ["baseline_employee", *packs]
        base = packs_to_feature_ids(packs)
        overrides = user.get("feature_overrides") or {}
        granted = set(overrides.get("granted") or [])
        revoked = set(overrides.get("revoked") or [])
        return (base | granted) - revoked

    @staticmethod
    def compute_effective_permissions(user: dict) -> List[str]:
        features = CapabilityService.compute_effective_features(user)
        perms: set = set()
        ui_modules: set = set()
        for fid in features:
            f = _FEATURES_BY_ID.get(fid)
            if not f:
                continue
            for p in f.get("backend_permissions") or []:
                perms.add(p)
            for r in f.get("frontend_routes") or []:
                ui_modules.add(r)
        return sorted(perms), sorted(ui_modules)

    @staticmethod
    async def get_effective_state(user_id: str) -> Dict[str, Any]:
        user = await users_col.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        features = sorted(CapabilityService.compute_effective_features(user))
        perms, ui_modules = CapabilityService.compute_effective_permissions(user)
        return {
            "user_id": user_id,
            "capability_packs": user.get("capability_packs") or [],
            "feature_overrides": user.get("feature_overrides") or {"granted": [], "revoked": []},
            "effective_features": features,
            "effective_permissions": perms,
            "effective_ui_modules": ui_modules,
            "totals": {
                "packs": len(user.get("capability_packs") or []),
                "features": len(features),
                "permissions": len(perms),
                "ui_modules": len(ui_modules),
            },
        }

    # ──────────────────────── Smart defaults ────────────────────────

    @staticmethod
    def smart_default_packs(dept: str = None, legacy_role: str = None) -> List[str]:
        if legacy_role and legacy_role in LEGACY_ROLE_TO_PACKS:
            return LEGACY_ROLE_TO_PACKS[legacy_role]
        if dept and dept.lower() in DEPT_TO_PACKS:
            return DEPT_TO_PACKS[dept.lower()]
        return ["baseline_employee"]

    # ──────────────────────── Validation ────────────────────────

    @staticmethod
    def _validate_packs(packs: List[str], actor: dict):
        unknown = [p for p in packs if p not in _PACKS_BY_ID]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown packs: {unknown}")
        if "admin_elevation" in packs and not _is_owner(actor):
            raise HTTPException(status_code=403, detail="Only admin_owner can assign admin_elevation pack")

    @staticmethod
    def _validate_features(feature_ids: List[str]):
        unknown = [f for f in feature_ids if f not in _FEATURES_BY_ID]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown feature_ids: {unknown}")

    # ──────────────────────── Mutations + audit ────────────────────────

    @staticmethod
    async def _write_audit(actor: dict, target_user: dict, action: str,
                           before: dict, after: dict, reason: str):
        now = datetime.now(timezone.utc)
        before_packs = set(before.get("capability_packs") or [])
        after_packs = set(after.get("capability_packs") or [])
        before_features = CapabilityService.compute_effective_features(before)
        after_features = CapabilityService.compute_effective_features(after)
        entry = {
            "id": str(uuid.uuid4()),
            "actor_id": actor.get("id"),
            "actor_name": actor.get("name") or actor.get("email") or "Admin",
            "target_user_id": target_user.get("id"),
            "target_user_name": target_user.get("name") or target_user.get("email") or "User",
            "action": action,
            "before": {
                "capability_packs": list(before_packs),
                "feature_overrides": before.get("feature_overrides") or {"granted": [], "revoked": []},
            },
            "after": {
                "capability_packs": list(after_packs),
                "feature_overrides": after.get("feature_overrides") or {"granted": [], "revoked": []},
            },
            "diff": {
                "added_packs": sorted(after_packs - before_packs),
                "removed_packs": sorted(before_packs - after_packs),
                "added_features": sorted(after_features - before_features),
                "removed_features": sorted(before_features - after_features),
            },
            "reason": reason,
            "timestamp": now.isoformat(),
        }
        await audit_col.insert_one(entry)
        return entry

    @staticmethod
    async def _persist_and_force_logout(user_id: str, packs: List[str],
                                        overrides: dict, actor_id: str):
        """Persist new packs + overrides + recomputed permissions/ui_modules.
        Also bump password_changed_at to invalidate any active JWT (force re-login).
        """
        user = await users_col.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user["capability_packs"] = packs
        user["feature_overrides"] = overrides
        perms, ui_modules = CapabilityService.compute_effective_permissions(user)
        now = datetime.now(timezone.utc)
        await users_col.update_one(
            {"id": user_id},
            {"$set": {
                "capability_packs": packs,
                "feature_overrides": overrides,
                "permissions": perms,
                "ui_modules": ui_modules,
                "capability_packs_assigned_at": now,
                "capability_packs_assigned_by": actor_id,
                "password_changed_at": now,  # invalidates existing JWT
            }},
        )

    @staticmethod
    async def apply_packs(actor: dict, target_user_id: str,
                          packs: List[str], reason: str) -> Dict[str, Any]:
        if not _is_admin_user(actor):
            raise HTTPException(status_code=403, detail="Only admin / admin_owner can change capability packs")
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="reason is required")
        CapabilityService._validate_packs(packs, actor)
        # Ensure baseline_employee always present
        if "baseline_employee" not in packs:
            packs = ["baseline_employee", *packs]
        # Dedup
        packs = sorted(set(packs), key=lambda p: _PACKS_BY_ID[p].get("sort_order", 99))

        before = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        if not before:
            raise HTTPException(status_code=404, detail="Target user not found")
        # Keep existing overrides as-is
        existing_overrides = before.get("feature_overrides") or {"granted": [], "revoked": []}
        await CapabilityService._persist_and_force_logout(
            target_user_id, packs, existing_overrides, actor.get("id")
        )
        after = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        await CapabilityService._write_audit(actor, before, "packs_changed", before, after, reason)
        return await CapabilityService.get_effective_state(target_user_id)

    @staticmethod
    async def apply_overrides(actor: dict, target_user_id: str,
                              granted: List[str], revoked: List[str],
                              reason: str) -> Dict[str, Any]:
        if not _is_admin_user(actor):
            raise HTTPException(status_code=403, detail="Only admin / admin_owner can change feature overrides")
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="reason is required")
        CapabilityService._validate_features((granted or []) + (revoked or []))

        before = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        if not before:
            raise HTTPException(status_code=404, detail="Target user not found")
        packs = before.get("capability_packs") or ["baseline_employee"]
        new_overrides = {
            "granted": sorted(set(granted or [])),
            "revoked": sorted(set(revoked or [])),
        }
        await CapabilityService._persist_and_force_logout(
            target_user_id, packs, new_overrides, actor.get("id")
        )
        after = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        await CapabilityService._write_audit(actor, before, "overrides_changed", before, after, reason)
        return await CapabilityService.get_effective_state(target_user_id)

    @staticmethod
    async def promote(actor: dict, target_user_id: str,
                      add_packs: List[str], add_features: List[str], reason: str) -> Dict[str, Any]:
        if not _is_admin_user(actor):
            raise HTTPException(status_code=403, detail="Only admin / admin_owner can promote users")
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="reason is required")
        before = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        if not before:
            raise HTTPException(status_code=404, detail="Target user not found")

        current_packs = set(before.get("capability_packs") or [])
        current_overrides = before.get("feature_overrides") or {"granted": [], "revoked": []}
        new_packs = sorted(current_packs | set(add_packs or []),
                           key=lambda p: _PACKS_BY_ID.get(p, {}).get("sort_order", 99))
        new_overrides = {
            "granted": sorted(set((current_overrides.get("granted") or []) + (add_features or []))),
            "revoked": current_overrides.get("revoked") or [],
        }
        CapabilityService._validate_packs(new_packs, actor)
        CapabilityService._validate_features(new_overrides["granted"] + new_overrides["revoked"])
        await CapabilityService._persist_and_force_logout(
            target_user_id, new_packs, new_overrides, actor.get("id")
        )
        after = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        await CapabilityService._write_audit(actor, before, "promoted", before, after, reason)
        return await CapabilityService.get_effective_state(target_user_id)

    @staticmethod
    async def demote(actor: dict, target_user_id: str,
                     remove_packs: List[str], remove_features: List[str], reason: str) -> Dict[str, Any]:
        if not _is_admin_user(actor):
            raise HTTPException(status_code=403, detail="Only admin / admin_owner can demote users")
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="reason is required")
        before = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        if not before:
            raise HTTPException(status_code=404, detail="Target user not found")

        current_packs = set(before.get("capability_packs") or [])
        current_overrides = before.get("feature_overrides") or {"granted": [], "revoked": []}
        # baseline_employee is sticky — can never be removed
        new_packs_set = current_packs - set(remove_packs or [])
        new_packs_set.add("baseline_employee")
        new_packs = sorted(new_packs_set, key=lambda p: _PACKS_BY_ID.get(p, {}).get("sort_order", 99))
        new_overrides = {
            "granted": [f for f in (current_overrides.get("granted") or []) if f not in (remove_features or [])],
            "revoked": sorted(set((current_overrides.get("revoked") or []) + (remove_features or []))),
        }
        await CapabilityService._persist_and_force_logout(
            target_user_id, new_packs, new_overrides, actor.get("id")
        )
        after = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        await CapabilityService._write_audit(actor, before, "demoted", before, after, reason)
        return await CapabilityService.get_effective_state(target_user_id)

    @staticmethod
    async def apply_template(actor: dict, target_user_id: str,
                             template_id: str, reason: str) -> Dict[str, Any]:
        if not _is_admin_user(actor):
            raise HTTPException(status_code=403, detail="Only admin / admin_owner can apply templates")
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="reason is required")
        tpl = await templates_col.find_one({"id": template_id, "is_active": True}, {"_id": 0})
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
        before = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        if not before:
            raise HTTPException(status_code=404, detail="Target user not found")

        new_packs = sorted(
            set(tpl.get("capability_packs") or ["baseline_employee"]) | {"baseline_employee"},
            key=lambda p: _PACKS_BY_ID.get(p, {}).get("sort_order", 99),
        )
        new_overrides = tpl.get("feature_overrides") or {"granted": [], "revoked": []}
        CapabilityService._validate_packs(new_packs, actor)
        await CapabilityService._persist_and_force_logout(
            target_user_id, new_packs, new_overrides, actor.get("id")
        )
        after = await users_col.find_one({"id": target_user_id}, {"_id": 0})
        full_reason = f"Template applied: {tpl.get('name')} — {reason}"
        await CapabilityService._write_audit(actor, before, "template_applied", before, after, full_reason)
        return await CapabilityService.get_effective_state(target_user_id)


def is_admin_actor(user: dict) -> bool:
    return _is_admin_user(user)
