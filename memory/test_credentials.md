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

## Step 2 Client Portal (Jun 20, 2026)

Client Portal uses a **separate JWT** at `/api/client-auth/login` (NOT `/api/auth/login`).
Token stored under `localStorage["client_token"]`. JWT claim `user_type: "client"`.
**Staff tokens get 403** on `/api/client-portal/*` endpoints.

Existing client portal records use the seeded `temp_password` on the
`client_mini_portals` doc (12-char random alphanumeric). On first login it auto-
hashes into `password_hash` for subsequent attempts.

Test flow: query `c.client_mini_portals.find_one({"client_email":"client@leamss.com"})`
to retrieve current `temp_password` for that record, then call:

```
POST /api/client-auth/login  {"email": "<email>", "password": "<temp_password>"}
```

Login page URL: `/client-portal/login` · Dashboard: `/client-portal/dashboard`.

To seed a fresh demo client for screenshots:
```python
c.client_mini_portals.insert_one({"id":"...","client_id":"demo_cid",
  "client_email":"demo@example.com","temp_password":"DemoPwd1234",
  "client_name":"Demo","status":"active","locked":False,
  "info_sheet_id":"...","temp_password":"...",...})
```

| Khushii Singh (auto from vendor) | khushiii@leamss.com | Welcome@aYnfWufa | case_manager | internal | — | (must change on first login) |
## Phase 3A — Attendance & Leave Test Accounts (May 2026)

| Role            | Email                  | Password   | rbac_role        | reports_to        | employee_id    |
|-----------------|------------------------|------------|------------------|-------------------|----------------|
| Sales Manager   | smgr-test@leamss.com   | Pass@1234  | sales_manager    | (admin fallback)  | LMS-2026-0007  |
| Sales Executive | sexec-test@leamss.com  | Pass@1234  | sales_executive  | Sales Manager     | LMS-2026-0008  |

These test accounts demonstrate the full leave approval workflow:
- Sales Exec applies for leave → L1 = Sales Manager, Final = Admin (fallback)
- Sales Manager applies → L1 = Admin, Final = Admin (skip L1)

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
- Phase 3A: Every internal employee role auto-gets `attendance.clock.own`, `attendance.view.own`, `leave.apply.own`, `leave.view.own` permissions via self-service permission merge.

## Phase 3A — Company Policies (configurable via /api/hr-admin/settings)

- Office hours: 10:00 — 19:00 (9 hours)
- Late threshold: 10 min grace (after 10:10 = late)
- 3 late marks/month = 1 CL auto-deducted
- Monthly CL cap: 1 per month
- Max consecutive leave: 7 days
- Long leave (>5 days): once per year
- Sandwich leave (Fri+Mon): weekend counted
- No approval = LWP (regularize within 3 days)


## Login Verification (Jun 10, 2026 — Phase 16.7 environment restore)

After a container restore, `.env` files for both backend + frontend were missing
and had to be recreated. Login itself was never broken — only the **frontend
service** was in BACKOFF (missing `node_modules` → `craco: not found`). After
`yarn install` it compiles cleanly and login works end-to-end.

**Login endpoint:** `POST /api/auth/login` · Content-Type: `application/json`

**Verified sample curl (works on local + preview URL):**

```bash
curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@leamss.com","password":"Admin@123"}'
# → HTTP 200, returns {"token":"eyJ...","user":{...}}

# Token is accepted on a protected endpoint:
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@leamss.com","password":"Admin@123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s http://localhost:8001/api/auth/me -H "Authorization: Bearer $TOKEN"
# → HTTP 200, returns admin profile
```

**Idempotent re-seed status:** Auto-seed runs on every backend boot
(`migrations`, `[RBAC]`, `[Attendance]`, `[Phase4A/B/C…]` lines visible in
`/var/log/supervisor/backend.out.log`). User docs are NOT overwritten on
re-boot — bcrypt hashes stored in the `password` field (NOT `hashed_password`).
Verified `$2b$12$…` bcrypt prefix with length 60.

**Frontend login page:** `<REACT_APP_BACKEND_URL>/login` — once frontend is
RUNNING, browser → preview URL → login form sends to `/api/auth/login`.

