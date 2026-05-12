"""RBAC (Role-Based Access Control) Module — Phase 1 Foundation

Provides:
- Pydantic models for departments, roles, permissions, teams, role history
- Seed data: 8 departments, ~150 permissions, 16 system roles
- PermissionService: hierarchical scope checks, wildcards, custom overrides
- FastAPI dependencies: require_permission, require_any_permission, etc.
"""
