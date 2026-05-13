# LEAMSS — Changelog

This file appends every completed phase/feature with dates and verification status.

---

## 📅 February 2026

### ✅ Phase 4B — Sales Targets Management (DELIVERED)
**Completed:** Feb 13, 2026
**Tests:** Backend 29/29 + Phase 4A regression 15/15 = **44/44 ALL PASS** (`/app/test_reports/iteration_97.json`)

#### Acceptance Criteria — 33/33 met
- **Admin/Manager workflows**: Create + edit (with required reason ≥5 chars) + soft-delete (admin, future-only) + bulk-apply template (override flag) + template CRUD with system-template lock
- **Sales Executive view**: `/sales/my-targets` with Monthly/Quarterly/History tabs, live progress cards (Revenue + PA Count), daily run-rate calculation, days remaining, color-coded by % (rose → yellow → blue → emerald → amber for exceeded)
- **Live dashboard widget**: `Monthly Target` on `/sales/dashboard` shows real-time ₹achievement / ₹target, %, days left, daily required pace (was placeholder)
- **Auto-recalc**: PA `case_created` triggers `recalc_targets_for_user(created_by_user_id)` with milestone notifications at 50/75/100/150%
- **Role isolation verified**: Partner/Case Manager/Client get null/redirect on `/sales/*` routes (RequirePermission guards). Sales Exec cannot set own target (403).
- **Past-period block**: Cannot create or edit targets whose period has ended (400)
- **Period uniqueness**: One target per user per period (409 on duplicate, can use override_existing in bulk)
- **3 seed templates**: Starter ₹3L/6 · Standard ₹5L/10 · Aggressive ₹8L/16 (all system-locked from edit/delete)

#### Files
**New (4):**
- `backend/core/targets_logic.py` — period bounds, achievement compute, status, milestone detection, tz-safe helpers
- `backend/routers/targets.py` — 18 endpoints (CRUD + bulk + view + recalc + analytics + templates)
- `backend/migrations/phase4b_targets_init.py` — idempotent: 5 indexes + 3 system templates seed
- `backend/tests/test_phase4b_targets.py` — 15 pytest cases
- `frontend/src/pages/MyTargets.jsx` — Sales exec progress UI
- `frontend/src/pages/admin/SalesTargetsAdmin.jsx` — Admin team grid + bulk-apply modal + edit modal
- `frontend/src/pages/admin/TargetTemplatesManager.jsx` — Template CRUD

**Modified:**
- `backend/core/database.py` — registered `sales_targets_col`, `target_templates_col`
- `backend/core/rbac/seed_data.py` — added 8 perms: `target.delete.any`, `target.history.{team,all}`, `target_template.{view,use,create,manage}.{all,any}`; updated 4 role permission lists
- `backend/server.py` — registered `targets_router` BEFORE `sales_router` (avoids `/sales/{id}` catch-all collision), boot-time migration hook
- `backend/routers/pre_assess_portal.py` — `admin_approve_final` now triggers `recalc_targets_for_user` after stage→case_created
- `frontend/src/components/sales/SalesWidgets.jsx` — `TargetWidget` now LIVE (calls `/api/sales/targets/my`)
- `frontend/src/pages/AdminDashboard.jsx` — new sidebar group "Sales Management" with Targets + Templates
- `frontend/src/App.js` — 3 new routes guarded by RequirePermission

#### Bug Fixed Post-Test-Agent Review
- **`days_remaining = 0` mid-period bug**: `_strip_id` converted MongoDB datetimes to ISO strings; `datetime.fromisoformat` returned naive datetimes which raised TypeError on comparison with tz-aware `now()`. The `except Exception` branch then defaulted to 0. **Fix**: coerce parsed datetimes to UTC-aware in `get_my_targets.enrich()` AND in `days_remaining_in_period()` itself. Verified: sexec sees `18 days left · Need ₹27.8K/day` correctly mid-May.



### ✅ Full Impersonation Restored — "View Dashboard As User" (Switch Button)
**Completed:** Feb 13, 2026
**Tests:** Backend curl (5 guard-rails) + Frontend E2E screenshot flow — ALL PASS

#### Why
User requested original full impersonation back (Option A) — the prior agent had downgraded `/api/auth/impersonate` to 410 GONE in favor of a read-only `dashboard-preview` modal. User found the preview modal too restrictive and wanted to actually navigate the impersonated user's portal.

#### Backend Changes
- **`POST /api/auth/impersonate/{user_id}`** — restored to fully working endpoint (was returning 410 GONE)
  - Admin-only gate (legacy `role == 'admin'` + `rbac_role in (admin_owner, admin)`)
  - 400 if admin tries to impersonate self
  - 400 if target is inactive
  - 404 if user not found
  - Issues a JWT for target using `build_token_payload(target)` (same flow as `/login`)
  - Returns target's full user payload + `impersonated_by` metadata
  - Every switch logged to `audit_logs` with `action='impersonate_user'`, `admin_email`, `target_email`, `target_role`

#### Frontend Changes
- **`AdminDashboard.jsx`** — `Switch` button (`[data-testid^="switch-user-"]`) at line 2424 now wired to `handleImpersonate(usr)` (was `setPreviewUserId(usr.id)`)
- **`handleImpersonate`** — expanded route map to support all sales roles (`/sales/dashboard`) + fallback to `/portal/welcome`. Added error-recovery to restore admin token if switch fails mid-way.
- **`DashboardShell.jsx > AdminReturnBanner`** — yellow banner enhanced:
  - Shows `🔄 Impersonating [target name]` with role badge
  - Shows `(Logged in as Admin: [admin name])` for clarity
  - Button text: `Exit Impersonation` (was `Return to Admin`)
  - `data-testid="impersonating-label"` for the target-name span
- Existing read-only `DashboardPreviewModal` still mounted (kept for `EmployeeDetailModal` usage)

#### Verified
- ✅ Partner → impersonate → 403
- ✅ Self-impersonate → 400 "Cannot impersonate yourself"
- ✅ Anonymous → 403
- ✅ Bad user id → 404
- ✅ Audit log entry written
- ✅ Frontend E2E: Admin → Users tab → Switch on Case Manager → land on `/case-manager` → yellow banner shows "Impersonating Case Manager" → Exit → back to `/admin`, banner gone



### ✅ Phase 4A — Sales Workflow Inheritance (COMPLETE — 15/15 backend tests passed)
**Completed:** Feb 13, 2026
**Tests:** 15/15 backend tests passed via testing_agent_v3_fork (`/app/test_reports/iteration_96.json`)
**Test file:** `/app/backend/tests/test_phase4a_sales_workflow.py`

#### 🎯 Design Principle — DRY
Sales executives are treated as "internal partners" — they use the EXACT SAME PA workflow components as external partners. NO duplication.

#### Backend Changes
- **NEW**: `core/attendance_logic`-style helper module: `_assert_pa_owner()` at top of `pre_assessment.py` for centralized ownership enforcement
- **NEW**: Module-level constants `PA_CREATOR_ROLES`, `OWN_SCOPED_ROLES`
- **CRITICAL FIX**: Applied ownership check to `GET /api/pre-assessment/{pa_id}` (was previously unrestricted — pre-existing bug exposed by Phase 4A)
- `POST /api/pre-assessment/create` now accepts `lead_source` + `lead_source_detail` (10 options) and stores `created_by_role`, `created_by_user_id`, `created_by_user_type`
- 14 ownership checks across 7 routers updated from `role == "partner"` to `role in (partner|sales_executive|sr_sales_executive)`
- Sales executive `partner_id = user.id` strategy → all existing scope queries work transparently

#### Migration (Phase 4A)
- `migrations/phase4a_pa_backfill.py` — Idempotent. Backfills `created_by_user_id`, `created_by_role`, `created_by_user_type` on existing PAs.
- 15 existing PAs backfilled on first boot.

#### Frontend Changes
- **NEW**: `/sales/dashboard` route (RequirePermission: pa.create.own || pa.view.own)
- **NEW**: `pages/SalesDashboard.jsx` — thin wrapper rendering `<PartnerDashboard mode="sales" />`
- **NEW**: `components/sales/SalesWidgets.jsx` — 4 placeholder widgets (Target/Commission/Rank/Followups) with "Coming in Phase 4X" badges
- **NEW**: `pages/ComingSoon.jsx` — friendly placeholder for unbuilt features
- **MODIFIED**: `pages/PartnerDashboard.jsx` — accepts `mode` prop (default "partner"); allows sales roles when mode="sales"; injects `<SalesWidgetsRow>` above PartnerHome
- **MODIFIED**: `pages/Login.jsx` — smart redirect for 4 sales roles → `/sales/dashboard`
- **MODIFIED**: `components/pa/PaCreateForm.jsx` — Lead Source dropdown (10 options) at TOP of form, optional but recommended
- **MODIFIED**: `components/PreAssessmentPipeline.jsx` — form state includes `lead_source` + `lead_source_detail`

#### RBAC Permission Updates
- `sales_executive` role now has 28 permissions (all 18 partner perms + 10 sales/self-service)
- Added missing: `agreement.view.own`, `agreement.generate.own`, `invoice.view.own`

#### Verified
- ✅ Partner workflow EXACTLY unchanged (regression: 4/4 manual tests + screenshot)
- ✅ Sales exec can do everything partner can (parity: 11/11 verified)
- ✅ Cross-role scope isolation (sexec → partner PA = 403; partner → sexec PA = 403)
- ✅ Admin bypass preserved
- ✅ Phase 3A/3B + RBAC regression all passing

---

## 📅 February 2026

### ✅ Phase 3B — HR Admin Settings UI (COMPLETE — backend 100% tested)
**Completed:** Feb 13, 2026 (same day as 3A)
**Tests:** 42/42 backend tests passed via testing_agent_v3_fork (`/app/test_reports/iteration_93.json`)
  - 19 Phase 3B new tests
  - 23 Phase 3A regression tests (all still pass)

#### Backend
- Renamed router prefix: `/api/hr-admin/*` → `/api/hr/*`
- New endpoints in `routers/hr_admin.py`:
  - `POST /api/hr/leave-types` — create custom leave type (key uniqueness enforced)
  - `DELETE /api/hr/leave-types/{key}` — delete (blocks system types)
  - `POST /api/hr/holidays/import-indian/{year}` — bulk seed 9 India holidays
  - `POST /api/hr/holidays/copy-from/{from_year}/to/{to_year}` — clone year's holidays
  - `GET/PATCH /api/hr/approvers/config` — get/update approval workflow
  - `GET /api/hr/approvers/simulate/{user_id}` — visual chain simulator
  - `GET /api/hr/audit-log` — policy change audit trail
- New `policy_audit_log` MongoDB collection (lazy-created)
- All PATCH endpoints now log before/after to audit + use `exclude_unset` to support clearing nullable fields

#### Frontend — 5 New Admin Pages
- `/admin/hr/settings` — `AttendanceSettings.jsx` — 5 collapsible sections, live previews, save state
- `/admin/hr/holidays` — `HolidayManager.jsx` — List + Calendar views, bulk import/copy, CSV export
- `/admin/hr/leave-types` — `LeaveTypesManager.jsx` — 7-card grid + custom type creator + audit panel
- `/admin/hr/approvers` — `ApproverConfig.jsx` — 5 sections + **visual chain simulator** (Applicant → L1 → Final)
- `/admin/hr/audit` — `HRAuditLog.jsx` — Scope filter, expandable before/after diff

#### Shared Components
- `components/hr/HRSettingsLayout.jsx` — sidebar nav + breadcrumb wrapper for all 5 pages

#### Sidebar Integration
- AdminDashboard sidebar has new "HR Settings" group with 5 entries
- All routes wrapped in `RequirePermission` with appropriate perm gates
- Sales executive (non-admin) is properly blocked (403 redirect)

#### Acceptance Criteria — All Verified ✅
1. ✅ Admin sees HR Settings sidebar group
2. ✅ Sales Executive blocked from /admin/hr/* (403)
3. ✅ Office timings update reflects in next punch
4. ✅ Custom holiday added → visible in employee calendar
5. ✅ CL annual quota edit → reflects in user balances
6. ✅ Final approver change → next leave routes to new approver
7. ✅ Audit log captures all policy changes with timestamps
8. ✅ Approval chain simulator works (visual flow)
9. ✅ All Phase 3A functionality intact (regression: 23/23 passed)
10. ✅ All 4 default logins still work

---

## 📅 February 2026

### ✅ Phase 3A — Attendance & Leave Management (COMPLETE — backend 100% tested)
**Completed:** Feb 13, 2026
**Tests:** 23/23 backend tests passed via testing_agent_v3_fork (`/app/test_reports/iteration_92.json`)
**Test file:** `/app/backend/tests/test_phase3a_attendance_leaves.py`

#### Company Policies Implemented (configurable via /api/hr-admin/settings)
- 🕙 Office hours: 10:00 — 19:00 IST (9 hours)
- ⚠️ Late after 10 min grace (post 10:10 AM = late)
- 🚨 3 late marks/month → 1 CL auto-deducted (`record_late_mark` in attendance_logic.py)
- 📅 Monthly CL cap: 1/month (counts approved + pending)
- 🥪 Sandwich leave (Fri-Mon = 4 days incl. weekend; Sat-Mon = 3 days)
- 📏 Max 7 consecutive days leave
- 🚫 Long leave (>5 days) once per year
- ❌ No approval = LWP (auto-marked after working day with no punch + no leave)
- ⏱ Regularization grace: 3 days

#### 7 Leave Types Seeded
| Type | Quota | Monthly Cap | Max Consecutive |
|------|-------|-------------|-----------------|
| Casual Leave (CL) | 12/yr | **1/month** | 1 day |
| Sick Leave (SL) | 12/yr | — | 7 days |
| Earned Leave (EL) | 24/yr | — | 7 days |
| Comp-off | earned | — | 3 days |
| LWP | unlimited | — | — |
| Maternity | 180 days | — | 180 |
| Paternity | 5 days | — | 5 |

#### Backend (3 new routers + 1 migration + 1 logic module)
- `routers/attendance.py` — punch-in/out, current-status, my-month, today, late-marks, regularization, LWP scan, dashboard
- `routers/leaves.py` — types, my-balance, validate, apply, my-history, inbox, inbox-final, decide, all, balance-history
- `routers/hr_admin.py` — settings GET/PATCH, holidays CRUD, leave-types PATCH, approver-config
- `core/attendance_logic.py` — All business logic (sandwich detection, late marks, validation, balance deduction, approver resolution, LWP marking)
- `migrations/attendance_leave_migration.py` — Seeds defaults + backfills

#### New DB Collections
- `attendance_settings` (singleton with company policies)
- `attendance_logs` (one per user per day)
- `leave_types` (7 types)
- `leave_balances` (per user/type/year — with monthly_used breakdown)
- `leave_requests` (with L1 + Final approver IDs)
- `holidays` (year-indexed)
- `late_marks_tracker` (per user per month)
- `leave_balance_history` (audit log)
- `lwp_records` (auto-marked absences)
- `attendance_regularizations` (employee disputes)

#### Frontend
- `components/attendance/PunchWidget.jsx` — punch in/out with GPS, late banner, hours progress, late marks indicator
- `pages/MyAttendance.jsx` — calendar view with color-coded statuses, late marks card, regularization modal
- `pages/MyLeaves.jsx` — balance cards, apply modal with live validation (sandwich detection in UI), history with cancel
- `pages/LeaveApprovals.jsx` — L1 / Final inbox with one-click approve/reject
- PortalWelcome — punch widget mounted at top for internal employees

#### RBAC Updates
- New permissions auto-granted to every internal role (Phase 1 migration auto-merges):
  - `attendance.clock.own`, `attendance.view.own`
  - `leave.apply.own`, `leave.view.own`
  - `profile.view.own`, `profile.update.own`
- `SELF_SERVICE_PERMISSIONS` constant in `core/rbac/seed_data.py`

#### Two-Stage Approval Workflow Verified
- Sales Exec → L1 Manager (reports_to) → Final Approver (admin or dept head, configurable)
- If user IS the L1 approver (dept head), L1 stage is skipped
- If L1 approver IS the final approver, single approval suffices
- All decisions audited, notifications sent at each stage

---

## 📅 January 2026

### ✅ Phase 2 — Employee Portal Foundation + RBAC
**Completed:** Jan 2026

- 18 RBAC roles across 8 departments
- 219 permissions across 11 resources
- Dynamic role-based dashboard (PortalWelcome) with `ui_modules`
- Employee CRUD, Department/Org Chart, View Dashboard As (read-only preview)
- Password reset / Force-change-on-first-login / Forgot password flow
- User role history audit trail

### ✅ Phase 2.2 — Frontend Route Guard
**Completed:** Jan 2026 (verification pending in this fork; bug-fix scope completed)
- `RequirePermission.jsx` wrapper for sensitive routes
- Applied to `/admin/employees`
- Admin-only action buttons hidden conditionally in EmployeeDetailModal

---

## 📅 Pre-Jan 2026 (Phases A — D)

### ✅ Phase A-D — Core CRM (5-step funnel)
- Pre-Assessment forms with public share links
- Admin Approval workflow + Proposal Generation (AI - Claude)
- Consent & Payment (mocked Stripe)
- Case Manager assignment + Client mini-portal
- AI Eligibility Pre-score, Visa Pathway comparison
- Legal Archive with SHA-256 integrity chain
- Agreement Template Engine, Document Expiry Tracker
- WhatsApp Smart Share (mocked Twilio)
