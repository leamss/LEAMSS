# LEAMSS RBAC v2 — Capability Packs Architecture (Phase 22)

**Status:** Design approved by Sir on Feb 26, 2026. Build dispatched as single mega-sweep.

## Goals
1. **Replace single `rbac_role` field** with composable **capability_packs** (Layer 1) + **feature_overrides** (Layer 2)
2. **Backward compat**: every existing `RequirePermission` check continues to work; no API consumers break
3. **Zero permission regression**: migration script guarantees every existing user has ≥ their previous effective permissions
4. **Auditable**: every pack/override mutation writes to `rbac_audit_log`
5. **Discoverable**: admin UI exposes the full 140-feature catalog with search/filter for surgical control

## Layer model

```
LAYER 0: Permissions catalog (existing, untouched)
          permissions: 200+ keys like "pa.approve.l2", "hr.policy.update"

LAYER 1: Capability Packs (NEW — 9 packs)
          capability_packs[]: pack assignments. Each pack maps to feature_ids.

LAYER 2: Feature Overrides (NEW)
          feature_overrides: { granted: [feature_id], revoked: [feature_id] }

LAYER 3: Feature → Permission flattening (computed)
          For each effective feature, look up feature_catalog.backend_permissions
          ∪ all of these → user.permissions (cached on the user row + JWT)
```

## Data model

### `users` collection (additions only — NO field removals)
```python
{
  "id": "uuid",
  # ... existing fields unchanged: role, rbac_role, user_type, department, permissions, ui_modules, etc.

  # NEW Phase 22:
  "capability_packs": ["baseline_employee", "marketing", "manager_elevation"],
  "feature_overrides": {
      "granted": ["ai.workflow_builder"],
      "revoked": ["marketing.scorecards"]
  },
  "capability_packs_assigned_at": ISODate,
  "capability_packs_assigned_by": "user_id",
}
```

### `capability_packs` collection (new, system-seeded on startup)
```python
{
  "pack_id": "marketing",
  "name": "Marketing",
  "description": "Marketing dept tools + Atlas content mgmt",
  "color": "leamss-orange",
  "icon": "Megaphone",
  "feature_ids": ["marketing.dashboard", "marketing.content_studio", ...],
  "is_system": True,
  "is_baseline": False,             # baseline_employee=True; auto-granted, cannot be removed
  "is_admin_only": False,           # admin_elevation=True; only admin_owner can assign
  "sort_order": 2,
  "created_at": ISODate,
}
```

### `feature_catalog` collection (new, system-seeded on startup from FEATURE_INVENTORY doc)
```python
{
  "feature_id": "marketing.content_studio",
  "name": "AI Content Studio (Claude 4.5)",
  "description": "...",
  "category": "marketing",          # for UI grouping
  "backend_permissions": ["marketing.content.create", "marketing.content.view"],
  "ui_modules": ["marketing/content-studio"],
  "frontend_routes": ["/portal/marketing/content-studio", "/admin/marketing/content-studio"],
  "default_packs": ["marketing"],
  "is_baseline": False,
  "is_admin_only": False,
  "created_at": ISODate,
}
```

### `rbac_audit_log` collection (new)
```python
{
  "id": "uuid",
  "actor_id": "admin user id",
  "actor_name": "...",
  "target_user_id": "user whose capabilities changed",
  "target_user_name": "...",
  "action": "packs_changed" | "overrides_changed" | "template_applied" | "promoted" | "demoted",
  "before": { "capability_packs": [...], "feature_overrides": {...} },
  "after":  { "capability_packs": [...], "feature_overrides": {...} },
  "diff":   { "added_packs": [...], "removed_packs": [...], "added_features": [...], "removed_features": [...] },
  "reason": "Required field per Sir spec",
  "timestamp": ISODate,
}
```

### `rbac_role_templates` collection (new, admin-managed)
```python
{
  "template_id": "uuid",
  "name": "Marketing Manager",
  "description": "Standard combo for marketing line managers",
  "capability_packs": ["baseline_employee", "marketing", "manager_elevation"],
  "feature_overrides": { "granted": [], "revoked": [] },
  "created_by": "admin user id",
  "created_at": ISODate,
  "updated_at": ISODate,
}
```

## Capability service contract

`core/rbac/capability_service.py` exposes:

```python
class CapabilityService:

    @staticmethod
    async def compute_effective_features(user: dict) -> set[str]:
        """
        Returns the final set of feature_ids the user has access to:
        ∪(pack.feature_ids for pack in user.capability_packs)
        ∪ user.feature_overrides.granted
        − user.feature_overrides.revoked
        """

    @staticmethod
    async def compute_effective_permissions(user: dict) -> list[str]:
        """
        Maps effective_features → flat backend_permissions list.
        Persists onto user.permissions (cache for fast checks).
        Also recomputes user.ui_modules.
        """

    @staticmethod
    async def apply_packs(actor: dict, target_user_id: str, packs: list[str], reason: str) -> dict:
        """
        Mutates user.capability_packs, recomputes permissions, writes audit log,
        invalidates token (sets password_changed_at = now so user must re-login).
        Returns the new effective state for response.
        """

    @staticmethod
    async def apply_overrides(actor: dict, target_user_id: str,
                              granted: list[str], revoked: list[str], reason: str) -> dict:
        """Same pattern for Layer 2 overrides."""

    @staticmethod
    async def smart_default_packs_for_department(dept: str) -> list[str]:
        """
        Returns the recommended pack list when creating a user in a given dept.
        marketing → [baseline_employee, marketing]
        hr → [baseline_employee, hr]
        sales → [baseline_employee, operations]
        ...
        """
```

## RBAC v2 endpoints (`/api/rbac/*`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/rbac/packs` | any internal staff | List all 9 packs with their feature_ids |
| GET | `/api/rbac/feature-catalog` | any internal staff | Full 140-feature catalog (supports `?category=&search=`) |
| GET | `/api/rbac/users/{user_id}/effective-capabilities` | admin / admin_owner OR self | Compute live effective state |
| PATCH | `/api/rbac/users/{user_id}/capability-packs` | admin / admin_owner | Set Layer 1 packs (body: `{packs, reason}`) |
| PATCH | `/api/rbac/users/{user_id}/feature-overrides` | admin / admin_owner | Set Layer 2 overrides (body: `{granted, revoked, reason}`) |
| POST | `/api/rbac/users/{user_id}/promote` | admin / admin_owner | Add packs (body: `{add_packs, add_features, reason}`) |
| POST | `/api/rbac/users/{user_id}/demote` | admin / admin_owner | Remove packs (body: `{remove_packs, remove_features, reason}`) |
| GET | `/api/rbac/audit-log` | admin / admin_owner | Paginated log (`?target_user_id=&limit=&skip=`) |
| GET | `/api/rbac/templates` | admin / admin_owner | List role templates |
| POST | `/api/rbac/templates` | admin / admin_owner | Create template |
| PATCH | `/api/rbac/templates/{id}` | admin / admin_owner | Update template |
| DELETE | `/api/rbac/templates/{id}` | admin / admin_owner | Soft-delete template |
| POST | `/api/rbac/users/{user_id}/apply-template` | admin / admin_owner | Apply template (body: `{template_id, reason}`) |

## Migration plan

Script: `backend/scripts/migrate_rbac_v2.py` — idempotent, prod-gated, dry-run mode by default.

Per user:
- If `capability_packs` already set → SKIP (idempotent)
- Else derive packs from `(rbac_role, department, role)`:
  ```
  rbac_role=admin_owner  → ALL 9 packs (god-mode)
  rbac_role=admin        → [baseline, admin_elevation, manager_elevation, operations]
  legacy role=admin      → same as rbac_role=admin
  rbac_role=hr_head      → [baseline, hr, manager_elevation]
  rbac_role=hr           → [baseline, hr]
  rbac_role=marketing    → [baseline, marketing] + manager_elevation if is_manager
  rbac_role=it           → [baseline, it]
  rbac_role=accounts/finance → [baseline, accounts]
  rbac_role=case_manager → [baseline, operations]
  rbac_role=partner      → [baseline, operations]  (partners that are internal staff)
  rbac_role=staff/employee → [baseline] + dept-specific pack if dept matches
  no rbac_role + dept=marketing → [baseline, marketing]
  no rbac_role + no dept → [baseline]
  ```
- `feature_overrides = {granted: [], revoked: []}` (empty)
- Recompute `permissions` + `ui_modules` from new pack assignments — must ≥ current permissions

## Backward compatibility strategy
1. All existing `permissions` lookups continue to work — `compute_effective_permissions` writes the same `user.permissions` field
2. Legacy `rbac_role` / `role` fields **preserved** — derived from primary pack on user update (e.g. if a user has `[hr, manager_elevation]`, rbac_role = `hr_head`)
3. `require_permission()` / `require_any_permission()` unchanged
4. JWT payload unchanged (`build_token_payload` still emits `role`, `rbac_role`, `permissions`)
5. Force-logout already in place via `password_changed_at` — capability changes trigger this same mechanism

## Frontend UI scope (Sub-Slice 22.3)

Single component `RoleCapabilityBuilder.jsx` mounted in admin user-detail "Role & Permissions" tab:

```
┌─ LAYER 1: Quick Presets (9 chips) ───────────────┐
│ [✓ Baseline][✓ Marketing][ ] IT [ ] Accounts ... │
│ Toggle → cascades feature checkboxes              │
└───────────────────────────────────────────────────┘
┌─ LAYER 2: Feature Catalog ────────────────────────┐
│ 🔍 search... | Category [All ▼] | [✓] Show only granted │
│ Category accordions with feature checkboxes      │
│ Override badge on rows that differ from pack default │
└───────────────────────────────────────────────────┘
┌─ LAYER 3: Live Preview ───────────────────────────┐
│ Effective permissions: 47                         │
│ UI modules: 23                                    │
│ Changes from current: +3 features, -1 feature    │
└───────────────────────────────────────────────────┘
┌─ LAYER 4: Save ───────────────────────────────────┐
│ Reason: [_______________ ] (required)             │
│ [Cancel] [Save Changes →]                         │
└───────────────────────────────────────────────────┘
```

Plus secondary surfaces:
- **Role History** tab: `rbac_audit_log` for this target_user_id, sorted newest-first
- **Promote/Demote modals** on user detail card header
- **Role Templates** management page at `/admin/rbac/templates`
- **PayrollAdminHub** at `/admin/payroll` (bundled per Sir's Q5 = a)

## Test plan (`backend/tests/test_phase22_rbac_v2.py`)

| TC | Test |
|----|------|
| 1 | Pack seed idempotency |
| 2 | Feature catalog seed idempotency |
| 3 | `effective_features = ∪packs − revoked + granted` math |
| 4 | Override revoke beats pack grant |
| 5 | Override grant pulls in features outside packs |
| 6 | `apply_packs` writes audit log + diff |
| 7 | `apply_overrides` writes audit log |
| 8 | `apply_packs` triggers `password_changed_at` (force-logout) |
| 9 | Migration script idempotency (run twice, same result) |
| 10 | Migration guarantees ≥ old permissions for every user |
| 11 | `RequirePermission` legacy decorator still passes for migrated users |
| 12 | Non-admin cannot call `/api/rbac/users/*/capability-packs` |
| 13 | admin_owner can call all endpoints |
| 14 | `apply_template` flow |
| 15 | Promote/Demote endpoints diff correctly |
| 16 | Smart defaults: `compute_default_packs("marketing") == [baseline, marketing]` |
| 17 | Cannot revoke `baseline_employee` pack (system-protected) |
| 18 | Cannot assign `admin_elevation` unless actor is admin_owner |
| 19 | Reason field is required (400 if missing) |
| 20 | Effective-capabilities endpoint accessible by self + admin |
