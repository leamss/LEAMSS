# LEAMSS Test Credentials

These accounts are seeded automatically on first boot and backfilled with RBAC fields by the Phase 1 migration.

## Active Login Credentials

| Role        | Email                  | Password     | rbac_role      | user_type | department | employee_id / partner_code |
|-------------|------------------------|--------------|----------------|-----------|------------|----------------------------|
| Admin       | admin@leamss.com       | Admin@123    | admin_owner    | internal  | admin      | LMS-2026-0001              |
| Case Mgr    | manager@leamss.com     | Manager@123  | case_manager   | internal  | operations | LMS-2026-0002              |
| Partner     | partner@leamss.com     | Partner@123  | partner        | external  | sales      | PRT-0001                   |
| Client      | client@leamss.com      | Client@123   | client         | client    | —          | —                          |
| Client 2    | client2@leamss.com     | Client@123   | client         | client    | —          | —                          |

## Additional Test Users (Pre-existing)

| Email                  | Legacy Role   | rbac_role      |
|------------------------|---------------|----------------|
| sales@leamss.com       | sales_manager | sales_manager  |
| tanvi@leamss.com       | case_manager  | case_manager   |
| jyoti@leamss.com       | admin         | admin_owner    |
| minal@leamss.com       | client        | client         |
| pgmodel29@gmail.com    | partner       | partner        |

## Notes
- Both legacy `role` and new `rbac_role` are populated. Existing routes that use `current_user["role"]` keep working.
- `/api/auth/me` returns BOTH fields plus `user_type`, `department`, `permissions`, `ui_modules`, etc.
- Migration runs idempotently on every backend startup — no manual setup needed.
