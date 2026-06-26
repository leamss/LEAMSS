# LEAMSS — "Coming Soon" Audit (Feb 26, 2026 hotfix)

Sir ne 2 critical regressions raise kiye the. Iss audit me **HAR "coming soon" / "future phase" reference** ko enumerate kiya hai aur action document ki hai.

## Source grep
```
$ grep -rnE "Coming soon|coming-soon|future phase|TODO|placeholder" /app/frontend/src/pages/ /app/frontend/src/components/
```

## Findings + Action

| # | Location | Old behaviour | Action taken | Feature actually built? |
|---|----------|---------------|--------------|--------------------------|
| 1 | `/app/frontend/src/pages/PortalWelcome.jsx:163` | `toast.info("🚧 ... coming soon in a future phase")` whenever a UI module card was clicked that wasn't explicitly routed | **WIRED** — expanded `routes` mapping from 6 → **31 module routes** covering all built Phase 21+22 features (Tasks, Onboarding, Payroll, Tickets, Chat, Site Audit, Dev Tracker, Content Studio, HR Analytics, Sales Dashboard, CM Dashboard, etc.). Fallback toast Hinglish-friendly: `"Ye module abhi roadmap me hai — agle phase me aayega"` | YES — modules now point to real `/portal/*` routes |
| 2 | `/app/frontend/src/pages/PortalWelcome.jsx:230` | My Tasks StatCard: `value="—" hint="Coming soon"` | **FIXED** — fetches live `/api/tasks?mode=me`, displays unfinished count (`status != done/completed`), clickable → `/portal/my-tasks` | YES — Tasks shipped in Phase 21 Slice 1 |
| 3 | `/app/frontend/src/pages/PortalWelcome.jsx:232` | This Month Attendance StatCard: `value="—" hint="Phase 3"` | **FIXED** — relabeled "Attendance" with value=`View`, hint=`Punch & monthly`, clickable → `/portal/attendance` | YES — Attendance shipped in Phase 21 Slice 1 |
| 4 | `/app/frontend/src/pages/PortalWelcome.jsx:189` | Profile header button: `toast.info("🚧 Profile editor coming soon")` | **FIXED** — `onClick={() => navigate('/portal/my-profile')}` | YES — Profile tab in MyWorkspace exists |
| 5 | `/app/frontend/src/pages/PortalWelcome.jsx:192` | Password header button: `toast.info("🚧 Change password coming in next phase")` | **FIXED** — `onClick={() => navigate('/portal/my-profile?tab=security')}` (security tab includes password change form) | YES — pwd-change endpoint live |
| 6 | `/app/frontend/src/pages/ComingSoon.jsx` | Standalone "Coming Soon" page | **KEPT AS-IS** — used by `/sales/coming-soon` route for genuinely-unbuilt sales sub-features (leaderboard etc.). Acceptable. | Sales leaderboard genuinely not built |
| 7 | `/app/frontend/src/components/sales/SalesWidgets.jsx:231` | Navigate to `/sales/coming-soon?feature=leaderboard` | **KEPT AS-IS** — Sales Leaderboard genuinely roadmap | Genuinely Phase 23 |

## Genuinely-unbuilt features (kept "coming soon" with explicit roadmap chip)

These are NOT yet built. Toast message now reads `"agle phase me aayega"` in Hinglish:
- `performance_cycles` (Performance Reviews) → Phase 23
- `offboarding` → Phase 23
- `training_mgmt` (Training & Development) → Phase 23
- `pa_pipeline_team`, `pa_pipeline_all` → Phase 23 (only `pa_pipeline_own` mapped)
- `team_targets`, `team_incentives`, `team_commissions` (specific team-level views — backend exists but no dedicated UI) → Phase 23
- `discount_inbox` (Discount approval queue) → Phase 23
- `call_log`, `call_logs` (Call log feature) → Phase 23
- `lead_analytics` → Phase 23 (separate from marketing dashboard)
- `doc_verification_queue`, `ocr_review`, `cm_workload` (Operations sub-features) → Phase 23
- `email_drafts` → Phase 23
- `accounts: invoices_all, invoices_process, refunds, gst, vendors, expenses, revenue_pnl` → already wired or Phase 23 (Finance Dashboard exists at `/admin/finance`)
- `user_access`, `system_config`, `api_keys`, `backups` (IT admin) → Phase 23
- `legal_archive`, `compliance_reports` (Compliance) → Phase 23

## Issue 2 — "Change Role" dialog (separate fix)
- **Location:** `/app/frontend/src/components/employees/EmployeeDetailModal.jsx:273-275`
- **Old behaviour:** Click "Change Role" → opens legacy single-dropdown dialog (`Select new role...`) with 20-char min reason
- **Fix:** Button now `navigate(\`/admin/rbac?user_id=${user.id}\`)` + relabeled **"Manage Roles & Capabilities"** + leamss-teal accent. Old dialog code (lines 383-399) remains as dead code (never triggered) — can be removed in next cleanup sweep.
- **Result:** Admin opens employee detail → "Role" tab → click "Manage Roles & Capabilities" → lands directly on the new 4-layer RoleCapabilityBuilder with user pre-selected via `?user_id=...` query param

## Issue 3 — Payroll mark-paid missing fields (carryover from tester WARN)
- **Location:** `/app/backend/routers/payroll.py:557-572`
- **Old behaviour:** Set only `paid_on` (legacy field, no `_at`/`_by`)
- **Fix:** Set `paid_at` (ISO string), `paid_on` (kept for backward-compat), `paid_by` (current user id), `paid_by_name`, plus enriched audit_log entry with actor_name and payment_reference
- **Result:** `GET /api/payslips/{id}` after mark-paid now returns populated `paid_at`, `paid_by`, `paid_by_name`, `payment_reference` fields

## v2 — Deeper Regressions Found During Hotfix Validation (Feb 26 evening)

While taking validation screenshots, two additional regressions surfaced from the Phase 22 RBAC v2 migration. Both fixed in the same session.

### Issue 4 — `ui_modules` format change broke ALL tile clicks (P0)
- **Location:** `/app/frontend/src/pages/PortalWelcome.jsx`
- **Root cause:** Phase 22 RBAC v2 migration silently switched `ui_modules` from legacy snake_case keys (e.g., `hr_dashboard`) to full URL paths (e.g., `/admin/hr/audit`). `PortalWelcome.jsx`'s `handleModuleClick` `routes` map and `MODULE_META` label dictionary were both keyed by snake_case, so:
  - Every "Your Access" tile click fell through to fallback toast "Ye module abhi roadmap me hai" (the EXACT bug Sir reported)
  - Tile labels rendered ugly raw URL strings like `/Admin/Activity` instead of friendly labels
- **Fix:**
  - `handleModuleClick`: added early return — if `moduleKey.startsWith('/')`, `navigate(moduleKey)` directly
  - Label derivation: if `m.startsWith('/')`, derive label from last path segment, replace `-`/`_` with space, Title Case (e.g., `/admin/ai-workflow` → "Ai Workflow")
  - Both legacy snake_case AND new URL-path ui_modules are supported (forward + backward compat)

### Issue 5 — `EmployeeDetailModal.jsx` Modal navigate is not defined (P0 runtime error)
- **Location:** `/app/frontend/src/components/employees/EmployeeDetailModal.jsx:276`
- **Root cause:** Previous hotfix attempt wired the "Manage Roles & Capabilities" button to `navigate('/admin/rbac?user_id=...')` but forgot to import `useNavigate` from `react-router-dom`. Runtime threw `navigate is not defined` immediately on click.
- **Fix:**
  - Added `import { useNavigate } from 'react-router-dom'`
  - Added `const navigate = useNavigate();` at the top of the component
- **Verified:** Click now navigates cleanly to `/admin/rbac?user_id=<user_id>` and the `RoleCapabilityBuilder` renders with 9 packs + 140 features.

## Final Status (v2)

| Issue | Status |
|-------|--------|
| 1. PortalWelcome "Coming soon" StatCards | ✅ FIXED (live data) |
| 2. PortalWelcome routes mapping | ✅ FIXED (31 routes + URL-path autoroute) |
| 3. Profile/Password header buttons | ✅ FIXED |
| 4. ChangeRole legacy dialog → RoleCapabilityBuilder | ✅ FIXED (button + nav import) |
| 5. Payroll mark-paid missing paid_at/paid_by | ✅ FIXED + verified via curl |
| 6. RBAC v2 ui_modules URL-path label + click | ✅ FIXED (dual format support) |
| 7. EmployeeDetailModal `navigate is not defined` | ✅ FIXED |

All P0 items GREEN. Ready for `e1_tester` full e2e.
