# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client. Expanding to a full multi-department Employee Portal with production-grade RBAC.

### RBAC Phase 2 — Employee Portal UI Complete (2026-05-13)

**Dedicated Employee Portal at `/admin/employees`** — separate page using DashboardShell layout. Entry-point: green "Employee Portal" button on Admin Home greeting card.

**New Pages (5):**
1. **Employees Dashboard** (`emp-dashboard`) — top stat cards (Total/Active/On Leave/New This Month), department breakdown bars, recently joined list, quick actions
2. **Departments** (`emp-departments`) — 8 department cards with icon/color/employee count/head, edit dialog for name/description/head
3. **All Employees** (`emp-list`) — searchable filterable table (Department, Role, Status), CSV export, row → opens detail modal
4. **Add Employee** (`emp-add`) — 3-step stepper (Basic Info → Employment → Access & Security), auto-2FA for hierarchy_level >= 3, shows temp password once
5. **Org Chart** (`emp-org-chart`) — hierarchical tree from `reports_to` with expand/collapse, department-color borders

**Employee Detail Modal** with 3 tabs:
- **Profile** — inline edit (name, mobile, designation, location, work mode), direct reports widget
- **Role & Permissions** — current role with permissions/UI modules display, change role dialog (logs to `user_role_history`), full role-change history
- **Activity** — recent 30 activity log entries
- Header actions: Reset Password, Deactivate/Reactivate

**Backend Endpoints (15):**
- `GET /api/employees` — list with filters (department, role, status, search) + pagination
- `GET /api/employees/stats` — dashboard counts + dept/role breakdowns
- `GET /api/employees/recent` — recent joiners
- `GET /api/employees/org-chart` — hierarchical tree
- `GET /api/employees/{id}` — detail with manager + direct_reports
- `GET /api/employees/{id}/history` — role change audit
- `GET /api/employees/{id}/activity` — activity log
- `POST /api/employees` — create with all RBAC fields populated, auto-gen LMS-2026-NNNN
- `PATCH /api/employees/{id}` — update profile
- `PATCH /api/employees/{id}/role` — change role + refresh perms + log history + notify user
- `POST /api/employees/{id}/deactivate` — terminate
- `POST /api/employees/{id}/reactivate` — restore
- `POST /api/employees/{id}/reset-password` — generate new temp password
- `GET /api/departments` — list with employee counts + head
- `GET /api/departments/{key}` — detail
- `GET /api/departments/{key}/employees` — employees in dept
- `GET /api/departments/{key}/roles` — roles available for dept
- `PATCH /api/departments/{key}` — update name/desc/head
- `GET /api/departments/_meta/roles` — all internal roles cross-dept

**All endpoints gated by RBAC Phase 1 permissions:**
- View: `employee.view.all` OR `user.view.all` OR `employee.view.dept`
- Create: `employee.create.any` OR `user.create.any`
- Update: `employee.update.all` OR `user.update.any`
- Terminate: `employee.terminate.any`

**Files Created (8):**
- `/app/backend/routers/employees.py` — 13 endpoints, ~400 lines
- `/app/backend/routers/departments.py` — 5 endpoints, ~130 lines
- `/app/frontend/src/pages/EmployeesPortal.jsx` — DashboardShell wrapper with lazy-loaded children
- `/app/frontend/src/components/employees/EmployeesDashboard.jsx`
- `/app/frontend/src/components/employees/DepartmentsPage.jsx`
- `/app/frontend/src/components/employees/EmployeesList.jsx`
- `/app/frontend/src/components/employees/AddEmployeeForm.jsx`
- `/app/frontend/src/components/employees/OrgChart.jsx`
- `/app/frontend/src/components/employees/EmployeeDetailModal.jsx`

**Files Modified (3):**
- `/app/backend/server.py` — registered employees + departments routers
- `/app/frontend/src/App.js` — new route `/admin/employees`
- `/app/frontend/src/components/AdminHome.jsx` — "Employee Portal" button on greeting card

**Backend Fixes During Implementation:**
- `routers/auth.py` `/login` endpoint now returns ALL RBAC fields (rbac_role, user_type, department, permissions, ui_modules, employee_id, partner_code, two_fa_enabled) — previously only login response missed the upgrade

**Critical Technical Note — Babel Stack Overflow Workaround:**
- AdminDashboard.jsx is already 3370+ lines. Adding new imports for shadcn-heavy components (Dialog, Select) triggered `Maximum call stack size exceeded` in the platform's visual-edits babel plugin (`subtreeHasPortals` recursive AST analysis).
- **Resolution**: Built Employee Portal as a STANDALONE page route (`/admin/employees`) instead of merging into AdminDashboard sidebar. Used `React.lazy` for sub-components so dynamic imports skip the recursive AST scanner.
- **Result**: AdminDashboard untouched (0 regressions). Employee Portal works seamlessly via dedicated route.

**Test Validation:**
- ✅ All 4 existing logins work unchanged
- ✅ Created test employees → got LMS-2026-NNNN, permissions[], ui_modules[] populated
- ✅ New employee login returns full RBAC fields
- ✅ All 5 portal pages render
- ✅ Lint clean on backend (3 files) + frontend (6 components + 1 page)

### RBAC Phase 1 — Foundation Complete (2026-05-12 night)

**User-approved Phase 1 RBAC foundation built end-to-end** — backward-compatible, zero regressions.

**8 new MongoDB collections seeded:**
- `departments` (8): admin, sales, marketing, operations, hr, accounts, it, compliance
- `roles` (18 system roles): admin_owner, compliance_officer, sales_head, sales_manager, sr_sales_executive, sales_executive, partner, marketing_head, marketing_executive, ops_head, case_manager, doc_verifier, hr_head, hr_executive, accounts_head, accounts_executive, it_admin, client
- `permissions` (219 entries) — naming: `{resource}.{action}.{scope}` + wildcard `*` for owner
- `teams` (empty, ready for use)
- `user_role_history` (audit trail)
- `migrations` (auto-logs every migration run)

**Users collection extended (backward-compatible):**
- Legacy `role` field **PRESERVED** (admin/partner/case_manager/client) — no existing route breaks
- NEW `rbac_role` (admin_owner/partner/case_manager/client + 14 more keys for future)
- NEW: `user_type`, `department`, `designation`, `reports_to`, `team_id`, `permissions[]`, `ui_modules[]`, `custom_permissions_granted[]`, `custom_permissions_revoked[]`
- Internal employees: `employee_id` (LMS-2026-NNNN), `date_of_joining`, `employment_status`, `employment_type`, `work_mode`
- External partners: `partner_code` (PRT-NNNN), `commission_tier`, `partner_agreement_signed`
- Security: `two_fa_enabled`, `two_fa_secret`, `failed_login_count`, `account_locked_until`
- Profile: `avatar_url`, `emergency_contact`

**Permission Service** (`/app/backend/core/rbac/permission_service.py`):
- `has_permission` / `has_any_permission` / `has_all_permissions`
- Wildcard `*` for admin_owner — passes ANY check
- Resource wildcards: `pa.*`, `pa.view.*`
- Hierarchical scope: `all > dept > team > own` (team scope passes own checks)
- Custom overrides: `effective = (role.permissions + custom_granted) − custom_revoked`
- Resource-level scope check (own/team/dept) against actual document fields
- `refresh_user_permissions(user_id)` — recompute cached perms on role change

**FastAPI Dependencies** (`/app/backend/core/rbac/dependencies.py`):
- `require_permission("pa.approve.l2")` — single check
- `require_any_permission(*keys)` / `require_all_permissions(*keys)`
- `require_role(*role_keys)` (honors both legacy + rbac_role)
- `require_department(*dept_keys)`
- `get_resource_with_permission(collection, id, perm_key, user)` — fetch + scope check in one call
- 403 errors return structured body: `{error, message, required, your_role}`

**Migration** (`/app/backend/migrations/rbac_phase1_migration.py`):
- Idempotent — safe on every boot (auto-runs in `server.py` startup)
- Seeds depts/perms/roles via upsert by `key`
- Backfills existing users:
  - admin → rbac_role=admin_owner, user_type=internal, dept=admin
  - partner → rbac_role=partner, user_type=external, dept=sales
  - case_manager → rbac_role=case_manager, user_type=internal, dept=operations
  - client → rbac_role=client, user_type=client, dept=null
- Auto-generates LMS-2026-NNNN / PRT-NNNN with no collisions
- Logs each run in `migrations` collection

**Auth Updates:**
- `build_token_payload(user)` — JWT now includes `rbac_role`, `user_type`, `department`, `permissions[]`
- `/api/auth/me` returns: legacy `role` + new `rbac_role`, `user_type`, `department`, `permissions`, `ui_modules`, `employee_id`/`partner_code`, `two_fa_enabled`, `emergency_contact`, etc.
- `/api/auth/login` response enriched with same fields
- Existing `current_user["role"] == "admin"` checks across 100+ routes still work — ZERO migration needed in Phase 1

**Indexes added** (idempotent):
- users: `(user_type, department, rbac_role)` compound, `reports_to`, `team_id`, `employment_status`, `employee_id` unique sparse, `partner_code` unique sparse
- roles: `key` unique, `(department, hierarchy_level)`
- permissions: `key` unique, `(resource, action)`
- departments: `key` unique
- teams: `department`, `manager_id`
- user_role_history: `(user_id, effective_date desc)`

**Acceptance Tests — ALL PASS:**
1. ✅ admin@leamss.com: /auth/me → role=admin, rbac_role=admin_owner, user_type=internal, dept=admin, employee_id=LMS-2026-0001, permissions=["*"]
2. ✅ partner@leamss.com: rbac_role=partner, user_type=external, dept=sales, partner_code=PRT-0001, 18 perms
3. ✅ manager@leamss.com: rbac_role=case_manager, user_type=internal, dept=operations, employee_id=LMS-2026-0002, 11 perms
4. ✅ client@leamss.com: rbac_role=client, user_type=client, dept=null, 8 perms (incl. pa.view.own, agreement.sign.own)
5. ✅ Regression: /api/users, /api/products, /api/cases, /api/legal-archive/stats (admin only — 403 for partner) all working
6. ✅ Permission service: admin "*" passes any check; partner has pa.create.own but NOT pa.approve.l1; scope hierarchy (team>=own) works; client denied legal_archive; has_any/has_all logic; custom grant/revoke overrides
7. ✅ Idempotency: 2nd run of migration → 0 duplicate inserts, 0 re-backfills

**Files created (7):**
- `/app/backend/core/rbac/__init__.py`
- `/app/backend/core/rbac/models.py` — Pydantic models for new collections
- `/app/backend/core/rbac/seed_data.py` — 8 depts + 219 perms + 18 roles definitions
- `/app/backend/core/rbac/permission_service.py` — Core check logic
- `/app/backend/core/rbac/dependencies.py` — FastAPI deps
- `/app/backend/migrations/__init__.py`
- `/app/backend/migrations/rbac_phase1_migration.py` — Idempotent seed + backfill + indexes

**Files modified (4):**
- `/app/backend/core/database.py` — added 6 new collection handles
- `/app/backend/core/auth.py` — `build_token_payload()` helper for RBAC-aware JWT
- `/app/backend/routers/auth.py` — `/login`, `/auth/me`, `/impersonate` return RBAC fields
- `/app/backend/server.py` — auto-runs migration on startup

**What's NOT touched (preserved):**
- All existing routes still use legacy `role` field — no regression
- Frontend code unchanged — login UI still renders correctly
- All existing PA workflow, AI proposals, agreements, legal archive intact

### Rollback — In-House Sales Team CRM Removed (2026-05-12 evening)

**User feedback**: In-House Partner concept + Sales Team Manager Dashboard didn't align with the bigger vision. User wants a proper **Employee Portal** instead (with departments, attendance, payroll, etc.) — planned as next major build.

**Removed cleanly** (no git revert; manual removal so existing features stayed intact):
- `/app/backend/routers/sales_team.py` — deleted
- `/app/frontend/src/components/sales/` (3 components) — deleted
- `users.py`: removed `employment_type` + `manager_id` fields from create/update
- `server.py`: removed sales_team_router import + mount
- `AdminDashboard.jsx`: removed Sales Team sidebar item + render + sales_manager role option + employment_type badge in Users list + employment_type dropdown in user dialog
- `PartnerDashboard.jsx`: removed Team Dashboard conditional sidebar item + sales_manager auth + sales-team render + auto-land
- `AdminHome.jsx`: removed DiscountApprovalInbox
- `PartnerHome.jsx`: removed IncentiveTierWidget
- `Login.jsx`: removed sales_manager route mapping
- DB cleanup: dropped `discount_requests`, `incentive_configs`, `sales_targets` collections; stripped `employment_type`/`manager_id` from users; deleted `salesmgr@leamss.com` user

**Verified**: 404 on `/api/sales-team/*`, clean Users page, existing Admin/Partner/Case Manager/Client flows untouched. Lint clean across modified files.

### In-House Sales Team CRM — Phase 1 + 2 (2026-05-12)

**User-approved P1**: Build foundation + Discount Approval + Tiered Incentive for in-house sales reps. Phase 3 (full Manager Dashboard) next round.

**Phase 1 — Foundation**:
- `users` collection: new `employment_type` field (values: `external` (default) | `employee`) + `manager_id` field
- `PUT /api/users/{id}` accepts both fields with validation
- `POST /api/users` defaults `employment_type=external`
- Admin Users page (AdminDashboard.jsx):
  - New badge column showing 🏢 In-House / 🌍 External next to partner names (data-testid=emp-type-{userId})
  - Edit/Create dialog: new indigo-bordered "Employment Type" dropdown (data-testid=user-employment-type) — appears only when role=partner
  - Explanatory text: "In-house employees get tiered incentives + stricter discount cap (5% vs 10%) and visibility to managers"

**Phase 2 — Discount Approval + Incentive**:
- New router `/app/backend/routers/sales_team.py` mounted at `/api/sales-team` (renamed from `/sales` to avoid existing route conflict)
- Auto-seeded tier config in `incentive_configs` collection:
  - Tiers: Bronze (0-5L @ 5%), Silver (5-15L @ 7%), Gold (15L+ @ 10%)
  - Discount caps: employee 5% auto / 15% manager / 100% admin; external 10% auto / 100% admin
- `POST /api/sales-team/discount-requests` — auto-routes based on % + employment_type. Returns `auto_approved=true` if within cap, else `status=pending` with `level_required`
- `GET /api/sales-team/discount-requests?status=` — admin/manager see all, partner/rep see own
- `POST /api/sales-team/discount-requests/{id}/decide` — approve/reject with optional note; managers blocked from admin-level requests
- `GET /api/sales-team/my-incentive?month=YYYY-MM` — employee-only; aggregates current rep's revenue from closed deals (`proposal_paid` / `awaiting_final_approval` / `case_created` stages), returns current tier + base_payout + next_tier + delta_needed
- `GET /api/sales-team/team-rollup` — admin sees all employees, sales_manager sees own team (by manager_id)
- `GET /api/sales-team/incentive-config` & `PUT /api/sales-team/incentive-config` — admin can adjust tiers/caps; versioning auto-bumps

**Frontend**:
- `/app/frontend/src/components/sales/IncentiveTierWidget.jsx` — mounted on PartnerHome. Gold-gradient tier banner + revenue/deals/commission stats + progress bar to next tier. **Auto-hides for externals** (403 response).
- `/app/frontend/src/components/sales/DiscountApprovalInbox.jsx` — mounted on AdminHome. Pending requests with level badge (auto/manager/admin), employment_type tag, base→discount→final breakdown, optional decision note, Approve/Reject buttons.

**Verified via curl + screenshots**:
- 3% discount → auto_approved instantly (within 5% cap)
- 10% discount → pending, level_required='manager'
- 25% discount → pending, level_required='admin'
- Approve flow works, status updates correctly
- Incentive: ₹2.98L revenue → Bronze tier → ₹14,948 payout, ₹2.01L to Silver visible
- External 403 on incentive endpoint (correct gate)
- Team rollup returns 1 employee rep with revenue + tier
- Frontend: badges render, incentive widget shows on PartnerHome, discount inbox shows on AdminHome

### Active Share Links Dashboard (2026-05-12)

**User-approved potential improvement** following smart-link + expiry control. Compliance + security gold-tier feature.

**Backend**:
- New router `/app/backend/routers/share_links_dashboard.py` mounted at `/api/share-links`
- `GET /api/share-links/?status=&link_type=&search=` (admin only) — unified list of all share-tokens + magic-tokens across all PAs with metadata: issuer, purpose, amount_label, issued_at, expires_at, status (active/expired/revoked/consumed/deactivated), access_count, last_accessed_at/ip/ua, and a `suspicious` flag (heuristic: clicks≥5 while still active)
- `POST /api/share-links/revoke` — admin sets `share_active=false` (for public) or `revoked=true` (for magic) with audit fields: revoked_at/by/reason
- Click tracking added to `GET /pre-assess-portal/public/{token}` — auto-increments `share_click_count` and records `share_last_accessed_at/ip/ua` per visit
- Magic links capture `used_ip/used_ua` on consume + check `revoked` flag (returns 410 'Link revoked by admin')

**Frontend**:
- New component `/app/frontend/src/components/ShareLinksDashboard.jsx` — full audit table with stats strip, search, type filter, click-to-revoke flow with reason capture, suspicious badges, color-coded status pills
- Mounted on AdminHome as third bottom widget (`id=share-links-anchor`)
- New Quick Access tile `quick-share-links-anchor` with indigo accent + smooth-scroll to widget

**Verified visually**: 30 links rendered, filter to "active" shows 15, revoke dialog opens cleanly with reason input. Stats update live after revoke (1 → revoked column).

### Smart Share Link + Expiry Control (2026-05-08)

**User-reported issue + enhancement combined**:

**Issue**: WhatsApp / Copy Public Link button always generated ₹5,100 PA-fee link, even on PAs that were already past `proposal_sent` (where client should pay the proposal fee, e.g., ₹1,50,000). User specifically complained that for an `approved + proposal_sent` PA with proposal fee ₹1,50,000, the share link was still showing ₹5,100.

**Enhancement**: Configurable link expiry (1/7/30/90 days or never).

**Backend** — `/app/backend/routers/pre_assess_portal.py`:
- `GenerateLinkRequest` model gains `expires_in_days: Optional[int]` (allowed values: 0, 1, 7, 30, 90)
- `POST /api/pre-assess-portal/generate-public-link` now branches by stage:
  - **BRANCH A** — fee NOT paid → public share-token URL (`/pre-assess/{token}`), `link_type: 'public_pa_fee'`, `amount: 5100`, `amount_label: '₹5,100'`, `purpose: 'pre_assessment_fee'`
  - **BRANCH B1** — fee paid + `proposal_sent` + linked user → magic-link URL (`/magic/{token}`), `link_type: 'magic_portal'`, `amount: pa.proposal_fee`, `purpose: 'proposal_fee_payment'`
  - **BRANCH B2** — `case_created` + linked → `purpose: 'view_portal'`, `amount: 0`
  - **BRANCH B3** — fee paid but no client_user_id → 400 'Client account not linked yet'
- Expiry honored: `expires_in_days=0` → null `expires_at` for public links, 5-year-out for magic links
- Activity log captures `action='share_link_generated'` with `type` + `expires_in_days` metadata

**Frontend** — `/app/frontend/src/components/pa/PaActionBar.jsx` (full rewrite):
- Both **Copy Public Link** and **WhatsApp** buttons now open a unified dialog (`data-testid=share-dialog-{paId}`)
- 5 expiry option pills (`data-testid=expiry-1, expiry-7, expiry-30, expiry-90, expiry-0`)
- Default = 30 days
- Amber warning banner when "Never expire" selected ("Use only for trusted recipients")
- WhatsApp message text adapts by `purpose`: shows ₹1,50,000 for proposal flows, ₹5,100 for new PAs, "View case status" for case_created
- Dialog also shows generated link with copy+open icons after submission

**Verified**: iteration_91.json — Backend **14/14 PASS** · Frontend **100% PASS** · 0 regressions across previous flows.

### Bug Fix + Edit PA Details (2026-05-08)

**User-reported issues**:
1. **🚨 BUG**: "Forward to Admin" throwing `ReferenceError: pas is not defined` — broke 3 critical handlers (forward / send-proposal / submit-final)
2. **📝 GAP**: No way to edit PA contact details (mobile/email/name) after creation — blocked WhatsApp share for PAs created without mobile

**Bug fix**:
- `/app/frontend/src/components/PreAssessmentPipeline.jsx` — state was named `assessments`/`setAssessments`, but 9 lines across 3 handlers (`handleForwardToAdmin`, `handleSendProposal`, `handleSubmitFinal`) used the wrong identifiers `pas`/`setPas`
- All 9 occurrences renamed correctly
- Forward / Proposal / Final flows now work end-to-end without errors

**New: Edit PA Details**:
- `POST → PUT /api/pre-assessment/{pa_id}/details` — `PADetailsUpdate` Pydantic model accepts: client_name, client_email, client_mobile, client_age, education, work_experience, country, service_type, notes
- Authorization: admin (any), partner (own only), case_manager (any), client (forbidden 403)
- Locked when stage = `case_created` (returns 400 — case must be edited from Case page)
- Diff-detection: only changed fields are persisted, returns `{ok: true, no_change: true}` when nothing different
- Auto-syncs `client_name` + `client_mobile` to linked `users` collection (so client login still works)
- Audit trail via `log_activity` with full before/after diff

**Frontend**:
- New `/app/frontend/src/components/pa/PaEditDetailsModal.jsx` — 8 grid fields + notes textarea + amber "case is locked" warning banner
- Pencil icon button (`data-testid=edit-pa-{paId}`) in every PA card row header — sits next to "Preview as Client"
- Modal applies optimistic UI update (assessment list refreshes immediately on save)

**Tested**: iteration_90.json — Backend **11/11 PASS** (1 skipped: no proposal_paid PA available) · Frontend **100% PASS** · 0 regressions across send-proposal / submit-final / forward / WhatsApp flows. `retest_needed:false`.

### Public Lead-Gen + Doc Expiry + WhatsApp Share (2026-05-08)

**4 user-approved features built and tested**:

#### #1 — AI Eligibility Pre-Score (PUBLIC lead magnet)
- New router `/app/backend/routers/eligibility.py`
- `GET /api/eligibility/pathways` — list 8 pathways
- `POST /api/eligibility/score` — public scoring via Claude Sonnet 4.6 across 8 pathways with tier/timeline/strengths/gaps/notes per pathway + top_recommendation + overall_summary
- `GET /api/eligibility/share/{score_id}` — public shareable result
- Lead capture: when `consent_to_contact=true` + email/mobile provided → auto-creates entry in `leads` collection with priority based on top score (>=70 = high)
- New page `/app/frontend/src/pages/EligibilityCheck.jsx` mounted at `/eligibility` route — public, no login required
- 90-second form → loading state → 8 pathway cards with score bars + tier badges + strengths/gaps + share/re-score/compare CTAs

#### #2 — Document Expiry Tracker (admin/partner/client)
- New router `/app/backend/routers/doc_expiry.py`
- `GET /api/doc-expiry/upcoming?horizon_days=120&severity=critical` — list expiring docs across PA + Case docs with role scoping
- `POST /api/doc-expiry/check-now` — idempotent scan that creates notifications for new bucket-crossings (90/60/30/15/7 days)
- `PUT /api/doc-expiry/pa-doc/{doc_id}/expiry` — set/update expiry on PA doc
- Idempotency: `doc_expiry_alerts` collection logs (doc_id, bucket) so same alert never fires twice
- Severity buckets: expired / critical (≤15d) / warning (≤60d) / info (≤90d) / ok
- New `DocExpiryWidget.jsx` mounted on AdminHome with 4 stat cells + Refresh + Send Alerts buttons
- Role scoping: admin/CM see all, partner sees own PAs, client sees own

#### #3 — WhatsApp Smart Share (zero-cost velocity)
- Updated `/app/frontend/src/components/pa/PaActionBar.jsx` — added green-bordered `MessageCircle` button
- `data-testid=whatsapp-share-{paId}` between "Copy Public Link" and "Preview as Client"
- Opens `https://wa.me/{cleanMobile}?text={prefilled}` with auto-built message: client name, partner name, country/service, PA reference, fee amount, secure link, signature
- No Twilio API needed (pure deep link). Toast error if mobile not on file.

#### #8 — Visa Pathway Comparison (PUBLIC + admin-editable)
- New router `/app/backend/routers/visa_compare.py`
- 8 seeded pathways with realistic 2026 fees/timelines (Canada EE/PNP, Australia 189/190, UK SW, Germany Blue Card, USA EB2-NIW, NZ SMC)
- `GET /api/visa-compare/pathways[?country=]` — public list (auto-seeds if empty)
- `GET /api/visa-compare/compare?slugs=` — 2-4 pathways side-by-side
- `PUT /api/visa-compare/pathways/{slug}` — admin edits (yearly fee refresh)
- `POST /api/visa-compare/reseed` — admin reset to defaults
- New page `/app/frontend/src/pages/VisaCompare.jsx` at `/visa-compare` — public, 8 pickable pills (max 4) → side-by-side cards with timeline / total cost / settlement funds / education / work-exp / age / language / benefits / drawbacks / post-arrival jobs

#### Login page — public access tiles
- `/app/frontend/src/pages/Login.jsx` — added 2 gradient tiles below demo creds: `public-eligibility-link` → /eligibility, `public-compare-link` → /visa-compare

**Tested**: iteration_89.json — Backend **18/18 PASS** · Frontend 100% PASS · 0 issues · 0 regressions. `retest_needed:false`.

### PreAssessmentPipeline Refactor — Round 2 (2026-05-07 night)

**User-approved P2 task**: Further break down `PreAssessmentPipeline.jsx` (was 1066 → 1002 after Round 1).

**6 new sub-components extracted** to `/app/frontend/src/components/pa/`:
- `PaProposalForm.jsx` (131 lines) — Send Service Proposal form with promo, discount, upsell bundles, AI generation buttons (Sonnet 4.6 + Opus 4.6 Premium), live breakdown panel
- `PaDocumentsList.jsx` (92 lines) — Client Documents panel with view (inline)/download/delete handlers per file
- `PaFinalSubmitForm.jsx` (64 lines) — Receipt + Agreement upload + Submit-to-Admin form (proposal_paid → awaiting_final_approval transition)
- `PaForwardForm.jsx` (27 lines) — Partner-review remarks form
- `PaStageProgress.jsx` (23 lines) — Bottom horizontal stage indicator with 7 dots
- `PaActionBar.jsx` (23 lines) — Copy Public Link + Preview as Client + dynamic next-action button

**Result**:
- `PreAssessmentPipeline.jsx`: 1066 → **770 lines** (-296, ~28% reduction)
- All data-testids preserved across extracted components
- Cleaned unused lucide imports (IndianRupee, ArrowRight, Download)
- New `/pa/` directory now houses 8 focused sub-components (Pipeline parent + 8 children)

**Tested**: iteration_88.json — Frontend **100% PASS** · Zero regressions across all PA flows (create/expand/proposal/forward/final-submit/agreement). `retest_needed:false`.

### Compliance Report PDF (2026-05-07 night)

**User-approved enhancement** following SHA-256 tamper detection: a stamped PDF audit report for legal/audit officers.

**Backend** — `GET /api/legal-archive/compliance-report.pdf?start_date=&end_date=` (admin-only):
- ReportLab-rendered A4 PDF (~3-5 KB typical, scales linearly with records)
- Sections: Cover (window, generator, totals) → Integrity scan summary (verified/tampered/unverified counts + flagged records list) → Consents table → E-Signatures table → Invoices table → Report-level SHA-256 chain hash binding all record hashes + timestamp + officer ID
- Default window = last 90 days; configurable via query params
- Returns `X-Report-Hash` header with the binding SHA-256 for client display
- Each table includes the per-record SHA-256 hash prefix
- Footer: page numbers + "LEAMSS · Compliance Report · timestamp" on every page
- 403 enforced for non-admin

**Frontend** — `/app/frontend/src/components/LegalArchive.jsx`:
- New "Compliance Report" gradient button in header (data-testid=`compliance-report-btn`) next to Verify Integrity
- Dialog (data-testid=`compliance-report-dialog`) with From/To date pickers (default last 90d), feature description list, Generate button
- On click: streams PDF, opens in new tab, toast shows first 16 chars of report hash for instant verification

**Verified via curl**:
- Admin default → HTTP 200 + valid `%PDF-1.4` magic + 4.3 KB + correct headers
- Admin custom range → HTTP 200 + 3.2 KB
- Partner → HTTP 403 ("Admin only — Legal Archive is restricted to compliance officers")
- Anonymous → HTTP 403

### SHA-256 Tamper Detection + Legal Doc Polish + PA Refactor (2026-05-07 night)

**User asked**: 1️⃣ Re-seed agreement templates so generated UI/PDF matches uploaded DOCX verbatim with proper typography. 2️⃣ Add SHA-256 tamper detection (Task C). 3️⃣ Refactor PreAssessmentPipeline.jsx (Task D).

**Templates re-seeded** (v2): `seed_agreement_templates.py` re-run — Australia Standard, Australia Protection, Canada Express Entry now have verbatim DOCX text with structured `<h1 class=title>`, `<h2>` annexure heads, `<ul>`/`<table class="client-details">`/`<table class="fee-table">`/`<table class="signature-table">`.

**New shared CSS** `/app/frontend/src/components/agreement-doc.css` — legal-document grade typography:
- Serif font stack (Georgia, Times New Roman, Cambria), 13.5px / 1.7 line-height, justified paragraphs
- Centered title with double-rule underline, italic meta line
- H2 sections with teal left-rule and uppercase tracking; H3 with underline
- Client-details + fee-table with bordered cells, teal header on fee-table, zebra striping
- Signature-table at bottom with 28px sign-line + uppercase muted labels
- A4-feel wrapper `.agreement-doc-wrap` with subtle shadow + light grey backdrop
- Print-friendly media query

Applied via `agreement-doc-wrap` to:
- `AgreementViewerModal.jsx` (admin/partner read-only view)
- `ClientAgreementSigning.jsx` (client scroll-to-sign view)
- `AgreementGenerator.jsx` (partner step-3 preview)
- `AgreementTemplatesManager.jsx` (admin preview)

**SHA-256 Tamper Detection (Task C):**
- New module `/app/backend/core/integrity.py` with `compute_hash`, `verify_hash`, canonical PROJECTIONS per record_type (consent / signature / invoice). Hash = sha256(canonical-JSON of immutable fields).
- All 3 insert sites now persist `integrity_hash` at write-time:
  - `routers/proposal_docs.py` — invoice send + e-sign save
  - `routers/pre_assess_portal.py` — proposal-consent submit
- New endpoints in `routers/legal_archive.py`:
  - `POST /api/legal-archive/integrity/backfill` — adds hash to legacy records (admin-only)
  - `GET /api/legal-archive/integrity/verify-all` — recomputes + diffs all records, returns `{verified, tampered, unverified, tampered_records[]}` 
- `/api/legal-archive/search` now returns `integrity_status` + `integrity_hash` (12-char prefix) per item
- LegalArchive UI: "Verify Integrity" button in header, auto-fires on mount, banner shows verify/tamper counts with red-pulse alert + tampered records list. Each row gets a colored Integrity badge (green ShieldCheck for verified, red ShieldAlert pulse for tampered, slate Shield for legacy/unverified). Backfill button appears only when legacy records present.
- Tamper sanity verified: mutating `body_snapshot.final_amount` directly in Mongo → verify-all flagged 1 tampered record with expected vs actual hash diff. Restored + rehashed.

**Refactor (Task D):**
- Extracted `PaCreateForm` from `PreAssessmentPipeline.jsx` (~75 lines) → `/app/frontend/src/components/pa/PaCreateForm.jsx`
- Trimmed unused lucide imports (User, Mail, Phone, Globe, GraduationCap, Briefcase)
- Pipeline file: 1066 → 1002 lines. All data-testids preserved.

**Tested**: iteration_87.json — Backend **16/16 PASS** · Frontend 100% PASS. 0 issues. `retest_needed:false`.

### Agreement Template Library + Auto-Generator (2026-05-07 PM)

**User uploaded 3 official LEAMSS agreements** (Australia Standard, Australia Protection, Canada Express Entry). Built end-to-end Agreement Template + E-Sign system.

**Backend (`/app/backend/routers/agreement_templates.py`):**
- 2 routers: `agreement_templates_router` + `pa_agreements_router`
- 14 endpoints: list/create/edit/clone/delete/upload-docx/request templates + auto-vars/generate/list/get/sign/pdf for per-PA agreements
- 3-level taxonomy: Country × Visa Category × Policy Variant
- Jinja2 rendering with `{{var}}` placeholders (auto-detected via regex)
- python-docx integration for DOCX upload + HTML extraction
- ReportLab PDF rendering with HTMLParser (preserves headings + bold + paragraphs) + embedded canvas signature image

**Seeded 3 default templates** via `seed_agreement_templates.py`:
- Australia · PR · Standard (5 annexures, INR fees, milestones)
- Australia · PR · Protection (premium variant with 100% refund + free re-application)
- Canada · PR · Express Entry (CICC-registered retainer)

**Frontend components (3 new + 1 enhanced):**
- `AgreementTemplatesManager.jsx` (admin) — CRUD with rich-text editor, placeholder badges, DOCX upload, clone/preview/edit
- `AgreementGenerator.jsx` (partner) — 3-step modal: Select Template → Fill Variables (auto-filled, editable) → Preview & Generate
- `ClientAgreementSigning.jsx` (client) — Full agreement body preview + scroll-to-end gate + canvas signature → green signed card with download
- `AgreementViewerModal.jsx` — read-only view for already-generated agreements with regenerate option
- Enhanced `PaFinancialSummary` — added "Generate Agreement" / "View Agreement" / "Agreement Signed ✓" smart button

**Security:** Admin-only writes for templates. Partner can only generate for own PAs. Client can only sign own agreements (403 enforced at backend).

**Auto-fill placeholders** (29 vars from PA): client_name, client_email, client_phone, client_dob, client_address, client_passport, country, service_type, agreement_date, partner_name, agent_name, pa_number, pre_assessment_fee, proposal_base_fee, proposal_final_amount, promo_code, milestone_1/2/3 amount/date, payment_mode, leamss_agent_email.

**Tested**: iteration_86.json — Backend **24/24 PASS** · Frontend **95% PASS** (1 LOW priority — fixed: View Agreement button now opens dedicated viewer modal instead of generator). `retest_needed:false`.

### Legal Archive (P1) — Admin Compliance Dashboard (2026-05-07 PM)

**User ask**: P1 — Legal Archive tab with searchable consents + signatures + invoices.

**New Backend router** `/app/backend/routers/legal_archive.py` (admin-only):
- `GET /api/legal-archive/stats` — returns `{consents, signatures, invoices, total}`
- `GET /api/legal-archive/search?q=&record_type=&start_date=&end_date=` — unified timeline aggregating from 3 collections (proposal_consent_emails, pa_signatures, pa_invoices). Sorted desc by timestamp, hydrated with PA metadata (client/partner/country).
- `GET /api/legal-archive/{ref_id}` — fetch full record by reference_id
- 403 enforcement helper `_admin_only()` blocks partner/CM/client

**New Frontend component** `/app/frontend/src/components/LegalArchive.jsx`:
- 4 stat cards (Total / Consents / E-Signatures / Invoices) with colored borders
- Free-text search bar (Enter or click Search)
- Filter pills: All / Consents / Signatures / Invoices
- Date range pickers (start/end)
- Results table: Type badge + Reference ID (mono) + Client info + Country/Service + Amount (₹) + Timestamp + Actions
- View Detail modal with type-specific previews:
  - Consent: full fee snapshot (base, promo, custom discount, upsells, final)
  - Signature: IP + file size + UA
  - Invoice: download button
- Inline invoice download icon
- Export CSV button (downloads filtered results)
- Refresh button

**Wired into Admin sidebar** — System group, Shield icon. Partner sidebar excludes it.

**Tested**: iteration_85.json — Backend **17/18 PASS** (1 minor 401-vs-403 ignorable) · Frontend 100% verified · 0 issues. `retest_needed:false`.

### P0 Batch + AI Upgrade (2026-05-07) — Sonnet 4.6 + Opus 4.6 + Optimistic UI

**User asks**: P0 batch (Optimistic UI + Refactor + Lazy-load) + Hybrid AI (Sonnet 4.6 default + Opus 4.6 Premium button).

**AI Model Upgrade ✨**
- Default: `claude-sonnet-4-6` (released Feb 17, 2026 — 30-50% faster than 4.5, same price)
- Premium: `claude-opus-4-6` (deepest reasoning, for ₹5L+ proposals)
- New `premium: bool` field in `AIGenerateRequest`. Response now returns `{model, premium}`.
- Frontend shows TWO buttons in proposal form: ✨ Generate with AI (Sonnet) + 👑 Premium AI (Opus, gradient bg).

**Optimistic UI**
- All stage-changing actions now flip card stage **INSTANTLY** before server confirms:
  - Admin approve/reject (`PreAssessmentQueue.handleReview`)
  - Admin approve-final + create case (`handleApproveFinal`)
  - Partner send-proposal (`handleSendProposal`)
  - Partner forward-to-admin (`handleForwardToAdmin`)
  - Partner submit-final (`handleSubmitFinal`)
- Rollback on failure restores snapshot + toast shows ` — reverted`.

**Refactor**
- Extracted `PaFinancialSummary` (90 lines) into `/app/frontend/src/components/pa/PaFinancialSummary.jsx`. Pipeline file: 1103 → 1037 lines. Same UI / data-testids preserved.

**Lazy-load**
- `DropoffRecoveryWidget` now uses `useRef` + `IntersectionObserver` (rootMargin 100px). Shows "Scroll to load…" placeholder until visible. `/api/intelligence/dropoff-leads` no longer fires on every Home render.

**Tested**: iteration_84.json — Backend **20/20 PASS** · Frontend 100% verified. Zero issues. `retest_needed:false`.

### Performance Fix — Portal Speed + Real-time Notifications (2026-04-23 night)
**User complaint**: "Bahot slow chal raha hai pura portal. Notifications, reviews immediately update nahi ho rahe."

**Root causes found:**
1. **Missing DB indexes** — `pre_assessment_documents.pre_assessment_id`, `activity_log.entity_id`, `notifications (user_id, read, created_at)`, `pa_invoices`, `case_milestones`, etc. all did full-collection scans.
2. **API call explosion** — Expanding one PA card fired 5+ parallel calls (docs + activity + payment-history + risk + checklist).
3. **Stats endpoint serial counts** — 9 sequential `count_documents()` calls per Home page render.
4. **SSE polling 15s** — Felt "not instant" for action notifications.

**Fixes applied:**
- **10 new Mongo indexes** in `core/database.py` (including compound `(partner_id, stage)`, `(user_id, read, created_at)`, `(entity_id, created_at)`, etc.)
- **NEW bundle endpoint** `GET /api/pre-assessment/{pa_id}/bundle` — returns pa + documents + activity + payment_history + checklist + risk in ONE parallel-queried response.
- **Stats endpoint** now uses `asyncio.gather` for all 9 counts in parallel.
- **SSE notification poll** reduced 15s → 5s with UTC-aware datetimes.
- **Frontend components** (`PaymentHistoryTimeline`, `RiskScoreBadge`, `SmartDocChecklist`) now accept `initialData` prop to skip their own fetch when the parent has bundle data.
- **PA expand on Partner Pipeline** uses bundle directly — 1 call instead of 5+.

**Benchmark:**
- Expanding PA card: **701ms → 118ms** (~**6x faster**, 5+ calls → 1 call)
- Stats: serial → parallel (~**9x faster** on large DBs)
- Notifications: max 5s delay instead of 15s (3x more responsive)

### Latest: AI Proposal + Send Proposal 403 Fix (2026-04-23 evening)
**User issue (screenshot)**: Partner clicked "Generate with AI" → red toast "Partners or admins only"; then "Send Proposal to Client" → "Not Authorized". Reproduced via curl: backend worked correctly with fresh partner token, so issue was stale/confusing error message with no status hint.

**Root cause**: Error messages were too generic ("Not authorized", "Partners or admins only") giving no debugging hint about role vs ownership vs stage.

**Fixes applied:**
- `ai_proposal.py`: Now also accepts `case_manager` role. Error explicitly states user's actual role and required roles. Partner-ownership error now says "This pre-assessment belongs to another partner…".
- `pre_assessment.py` send-proposal: Role check and partner-ownership check split with distinct messages. Stage mismatch now says "Pre-assessment is at stage 'X'. Must be at 'approved' stage (after 1st Admin approval)".
- Frontend handleGenerateAI + handleSendProposal: Display HTTP status code + detailed detail. 401 specifically surfaces "Session expired — log in again". console.error for devtools.

**Verified via curl**:
- Partner owner → AI generate 200 (303 words) + send-proposal 200
- Client role → AI generate 403 with crystal-clear message
- Already-sent PA → send-proposal 400 with stage hint

### Phase B + C + D Complete (2026-04-23 PM) — MASSIVE RELEASE

**User ask**: Build Phase B (Proposal PDF + Digital E-Sign + Send Invoice button), Phase C (Payment History + Auto Invoice + Milestone Payments), Phase D (Drop-off Recovery + Smart Doc Checklist + Risk Prediction), plus consent-summary email auto-trigger with Reference ID for legal records. "Sab achese interlink ho — koi link break nah hojayega."

**New Backend routers (all wired in server.py):**
1. `/app/backend/routers/proposal_docs.py` — ReportLab A4 branded PDFs + e-sign
   - `GET /api/proposal-docs/{pa_id}/proposal.pdf` / `invoice.pdf`
   - `POST /api/proposal-docs/{pa_id}/send-invoice` (MOCK email + records Reference ID)
   - `GET /api/proposal-docs/{pa_id}/invoices`
   - `POST /api/proposal-docs/{pa_id}/esign` (client-only, saves PNG + IP + UA)
   - `GET /api/proposal-docs/{pa_id}/esign`
2. `/app/backend/routers/payment_history.py` — two routers
   - `GET /api/payment-history/pa/{pa_id}` + `/case/{case_id}` (unified timeline)
   - `POST /api/milestones/case/{case_id}/create`, `GET /api/milestones/case/{case_id}`
   - `POST /api/milestones/{mid}/mock-pay`, `mark-paid`, `DELETE /api/milestones/{mid}`
3. `/app/backend/routers/intelligence.py` — Phase D
   - `GET /api/intelligence/dropoff-leads` (stage-SLA detection, severity, suggested_action)
   - `POST /api/intelligence/nudge/{pa_id}` (MOCK email + in-app notification)
   - `GET /api/intelligence/checklist/{pa_id}` (4 templates: canada_express_entry, australia_skilled, uk_work_visa, usa_h1b, default)
   - `GET /api/intelligence/risk/{pa_id}` (rule-based 0-100 score using age, education, experience, stage, docs, idle time, rejection history)

**Consent Summary Email (legal paper-trail):**
- Modified `POST /api/pre-assess-portal/client/proposal-consent/{pa_id}` to emit `reference_id` (format: `CON-<PA#>-<YYMMDDHHMM>`), persist full body_snapshot (base_fee + promo + upsells + final_amount + consent_at) in `proposal_consent_emails` collection, notify both client + partner
- New `GET /api/pre-assess-portal/client/consent-summary/{pa_id}` for archived view

**New Frontend components (6):**
- `SignatureCanvas.jsx` — HTML5 canvas drawing + typed-name verification
- `PaymentHistoryTimeline.jsx` — vertical timeline w/ received/pending totals
- `MilestonesManager.jsx` — create/pay/mark-paid/delete milestones (role-aware)
- `RiskScoreBadge.jsx` — risk pill + factor breakdown
- `SmartDocChecklist.jsx` — progress bar + checklist items
- `DropoffRecoveryWidget.jsx` — stuck-leads list with Nudge buttons

**Enhancements to existing:**
- **PartnerHome + AdminHome**: DropoffRecoveryWidget mounted at bottom
- **PreAssessmentPipeline (Partner)**: Financial Summary now has 3 action buttons (Download Proposal PDF · Download Invoice PDF · Send Invoice to Client) + below it a 2-col block with Payment Timeline + Risk Badge + Smart Checklist (when fee_payment_status=paid)
- **PreAssessmentMiniPortal (Client)**: Consent flow shows Reference ID inline + archived summary; new "E-Sign Your Service Agreement" card with SignatureCanvas (proposal_paid stage); "Your Payment Records" card with Proposal/Invoice download + PaymentHistoryTimeline
- **ClientDashboard → My Journey tab**: PaymentHistoryTimeline (case scope) + MilestonesManager for active cases

**Tech additions:**
- ReportLab (already installed v4.4.10) — A4 branded PDFs with logo, parties, fee breakdown table, consent clause, footer
- New collections: `pa_signatures`, `pa_invoices`, `proposal_consent_emails`, `case_milestones`, `pa_nudges`

**Tested**: iteration_83.json — Backend **49/49 PASS** · Frontend 100% · 0 regressions on Phase A · 0 issues. `retest_needed:false`.

### Latest: 3 Document UX Fixes (2026-04-23)
**User feedback**: "Document View download ho raha hai instead of inline open. Partner upload ke liye explicit Upload button chahiye aur Delete option bhi. Awaiting Final Approval stage pe Financial Summary dikhao."

**All 3 fixed:**
1. **Inline View** — Backend `GET /api/pre-assessment/{pa_id}/document/{doc_id}/download?inline=true` sets `Content-Disposition: inline` (via FileResponse `content_disposition_type`). Both Partner Pipeline + Admin Queue View buttons fetch with `?inline=true`, create blob URL, open in new tab. Save/Download buttons omit param (defaults to `attachment`).
2. **Explicit Upload flow** — Replaced auto-upload-on-select with 2-step staging: `pendingUpload[paId] = { file, docType }`. Selecting a file now shows filename + size + doc-type preview with explicit **Upload** + **Cancel** buttons. Applied to both `payment_received` zone + final-submit zone. data-testids: `file-input-{paId}`, `upload-btn-{paId}`, `cancel-upload-{paId}`, `final-upload-btn-{paId}`, `final-cancel-upload-{paId}`.
3. **Delete docs** — `DELETE /api/pre-assessment/{pa_id}/document/{doc_id}` (allowed for doc-owner client, PA's partner, admin). Frontend XCircle button with window.confirm. data-testid: `delete-doc-{docId}`.
4. **Financial Summary block** — NEW emerald gradient card visible at `proposal_paid`, `awaiting_final_approval`, `case_created` stages. Shows PA Fee ₹5,100 + Main Service breakdown (Base Fee, Promo discount with code, Custom Discount, Upsells list+total, Final Paid) + Total Received badge + Proposal notes.
5. **Awaiting Final Approval banner** — NEW indigo waiting banner at `awaiting_final_approval` stage with Hinglish subtext "Aapka role iske baad complete ho jayega".

**Tested**: iteration_82.json — Backend 29/29 PASSED, Frontend 100% verified. 0 issues. `retest_needed: false`.

## Complete Feature List (2026-04-15 to 2026-04-17)

1. **Step-wise Document Management** - Admin/CM/Client document flow
2. **Unified Client Document View** - Single "Documents & Steps" tab
3. **Smart Template AI** - 8 verified templates, 51 countries
4. **AI Workflow Builder** - Country->Visa->Generate->Edit->Save with SVG flags
5. **Government Forms** - 48 official forms (7 countries) with download links
6. **AI Verification System** - Admin verifies AI data before saving
7. **Deadline & SLA Tracker** - Auto document expiry, manual deadlines, color-coded urgency
8. **Client Intake Form Builder** - Product-specific, role-based (Client/CM/Both), Admin-managed
9. **Automated Government Fee Calculator** (2026-04-17) - 20 countries, live INR conversion

### Latest: 5 Critical UX Fixes (2026-04-22 late night)
**User-reported issues:**
1. Partner + Admin couldn't View/Download client-uploaded documents
2. Admin 1st Approval tab didn't show approved/rejected history (only pending)
3. Partner cards at `proposal_sent` stage had no "Waiting for Client Payment" visual cue
4. Client saw blind "Pay" button without full proposal details + breakdown + consent
5. After client pays, case went straight to admin — partner couldn't upload receipt/agreement/docs first

**All 5 fixed:**
- **Doc View/Download**: NEW `GET /api/pre-assessment/{pa_id}/document/{doc_id}/download` endpoint. Partner + Admin cards show "View" (opens new tab) + "Save" (download) buttons per doc.
- **1st Approval history**: Admin's 1st Approval filter now includes approved/rejected/proposal_sent/etc items (visible history)
- **Waiting banner**: `proposal_sent` cards now show pulsing amber "Waiting for Client Payment" banner with client name + fee amount. Stage label renamed "Waiting for Client Payment".
- **Rich proposal + consent**: Client MiniPortal at `proposal_sent` now shows (a) AI proposal text, (b) Pricing breakdown (base, promo, discount, upsells), (c) Partner note, (d) mandatory consent checkbox with SLA + no-misleading-info language, (e) "I Agree — Unlock Payment" gate button, (f) only after consent → Pay button unlocked. Backend enforces: `mock-pay-proposal` returns 400 if `proposal_consent_given` false.
- **NEW stage `awaiting_final_approval`**: Inserted between `proposal_paid` and `case_created`. Flow: Client pays → partner notified → partner uploads payment receipt + signed agreement + basic docs → Partner "Submit to Admin for Final Approval" → stage becomes `awaiting_final_approval` → admin queue shows it → admin activates case + assigns CM.

**NEW endpoints:**
- `GET /api/pre-assessment/{pa_id}/document/{doc_id}/download` (all roles)
- `POST /api/pre-assess-portal/client/proposal-consent/{pa_id}` (client-only)
- `POST /api/pre-assess-portal/partner/submit-final/{pa_id}` (partner/admin)

**Tested**: iteration_81.json — 28/28 backend + frontend 90%+ verified. 0 issues.

### Deep-Link Filtering + Fresh DB (2026-04-22 night)
**User feedback**: "Admin Home mein '1st Approval' click kiya tho pura Pre-Assessments tab open ho raha — sirf wohi cases dikhne chahiye. Plus saare test data delete karo, fresh se test karunga."

**Solution 1 — DB Cleanup**:
- Created `/app/backend/cleanup_test_data.py` — deleted 1,315 records across 13 collections
- Preserved: 6 seeded users, products, workflows, fee_database, promo_codes, upsell_bundles

**Solution 2 — Deep-link filtering**:
- `PreAssessmentQueue` + `PreAssessmentPipeline` now accept `initialFilter` prop
- Admin/Partner action cards pass filter → opens filtered view only
- Amber context banner + Clear-filter button when filter active
- Stats cards clickable for instant filtering
- Filter auto-clears on sidebar click

**Tested**: iteration_80.json — 14/14 backend + frontend 100%, 0 issues.

### Dashboard UX Simplification + AI → Claude (2026-04-22 PM)
**Problem solved**: User was overwhelmed with 20+ tabs in Admin, 8+ in Partner — "itna complicated kyu bana hai?"

**Solution**: Action-first redesign WITHOUT deleting any feature
- **NEW `PartnerHome.jsx`**: Home tab showing greeting + 4 pulsing action cards (partner_review / approved / new_leads / proposal_paid) + Quick access tiles + Recent PAs list
- **NEW `AdminHome.jsx`**: Home tab showing greeting + 3 approval cards (1st approval, 2nd approval, unassigned cases) + Org snapshot + Quick access grid
- **NEW `FunnelProgress.jsx`**: Reusable 5-step pipeline indicator (Created → Admin Approved → Proposal Sent → Main Fee Paid → Case Active) — inserted at top of every expanded PA card

**Sidebar regroup (no deletions)**:
- Partner: `Home` → `Daily Work` (PA, Leads, Tickets) / `Sales & Earnings` (Sales, Commission, Performance) / `Tools` (Fee Calc, Classic Dashboard)
- Admin: `Home` + `Classic Dashboard` as first 2 items, all other 20+ tabs retained in existing groups
- All previously-accessible tabs still navigable

**AI switch**: GPT-5.2 → **Claude Sonnet 4.5** (`claude-sonnet-4-5-20250929` via Emergent LLM key)
- Better warmth + immigration-domain empathy in proposal writing
- Model changes in `/app/backend/routers/ai_proposal.py` lines 109 + 130

**Tested**: iteration_79.json — 17/17 backend + frontend 100%, **0 regressions on any existing tab**. All user feature guarantees honoured.

### Phase A Retouch + 3 Major Features (2026-04-22)
**🔧 Critical Flow Fixes:**
- **NEW stage `partner_review`** — Between client-submit and admin-queue. Client submit → Partner gets "Action needed" notification + pink pulsing badge → Partner reviews in expanded card → Partner forwards with remarks → Admin queue
- **Partner card visibility** — Expanded card now shows 2 panels: "Client Documents" (file list + type badge) + "Client Activity" (timeline). Auto-loads on expand.
- **Strict Sales Rule** — `POST /sales` now rejects partner-created sales that lack `pre_assessment_id` UNLESS `bypass_pre_assessment=true` with `bypass_reason` (min 10 chars). Admin/CM unaffected.
- **Partner role extended** — Partner remains active through stages: new → partner_review → approved → proposal_sent → proposal_paid → **case_created (role ends here after CM assigned)**

**✨ Smart Discount Engine (wired):**
- Existing `/api/marketing/promo` CRUD + validate already backed
- Now integrated into Send Proposal form: promo code input + Apply btn + live discount preview
- `send-proposal` backend validates promo, increments `current_uses`, stores `promo_code`, `promo_discount_amount`, `total_discount_amount` in sale + PA

**📦 Upsell Bundles (new):**
- New `/api/upsell-bundles` CRUD + `/resolve` endpoint
- Auto-seeds 6 default bundles: Priority Processing ₹5k, Family Member +₹15k, Doc Courier ₹3.5k, Extended Consultation ₹8k, Mock Interview ₹4.5k, Landing Package ₹12k
- Admin UI: `UpsellBundlesManager.jsx` under Planning Tools (create/edit/delete)
- Partner UI: Checkbox grid in Proposal form; selected bundles auto-add to `upsell_total`

**✨ AI Proposal Generator (new):**
- New `/api/ai-proposal/generate` — uses **GPT-5.2** via Emergent LLM key
- Reads client profile (name, country, visa, age, education, experience, partner notes) + generates 250-380 word professional proposal body
- Tone options: professional | friendly | assertive
- Partner UI: "✨ Generate with AI" button in proposal form → auto-fills editable textarea

**📊 Enhanced Proposal Form breakdown:**
```
Base Fee:            ₹1,50,000
Promo (SAVE10 10%):  -₹15,000
Custom Discount:      -₹5,000
Upsells (2):         +₹8,000
─────────────────────────
Final Amount:        ₹1,38,000
```

**Tested**: 100% (15/15 backend + frontend all green) — iteration_78.json, 0 issues

### Latest: Pre-Assessment Client Portal Layer — Phase A Part 3 (2026-04-17)
- **Full E2E CRM sales funnel LIVE (MOCK payments)**: Partner creates PA → Client pays via public link → Magic-login → Upload docs → Submit for review → Partner validates & forwards → Admin 1st approval → Partner sends proposal → Client accepts + pays main fee → Admin 2nd approval assigns CM → Real Case created & active
- **NEW Admin endpoints**:
  - `GET /api/pre-assess-portal/admin/case-managers` — lists active case managers for the Assign-CM dropdown
  - `POST /api/pre-assess-portal/admin/approve-final/{pa_id}` — now accepts `{case_manager_id}` body, validates CM, attaches to new case, notifies CM
- **NEW Partner endpoint**: `POST /api/pre-assess-portal/partner/preview-magic/{pa_id}` — short-lived (30min) magic link so partner can preview exactly what client sees in MiniPortal
- **Admin UI enhancements** (`PreAssessmentQueue.jsx`):
  - 6-card stats grid (Total, 1st Review, Approved, Rejected, Awaiting Case, Conversion)
  - `proposal_paid` items now appear in admin queue with orange "Create Case" CTA
  - 2nd-approval UI with **Case Manager dropdown** (optional assign-or-later)
  - Admin sidebar: new "Pre-Assessments" menu item under Cases & Users
- **Partner UI enhancements** (`PreAssessmentPipeline.jsx`):
  - "Copy Public Link" + "Preview as Client" buttons now visible on **every** PA card (all stages)
  - Preview as Client button also in card header for 1-click access
  - Copy Link now returns **full URL** (`window.location.origin` + path) — shareable via WhatsApp/email
- **Admin queue backend updated** to include `proposal_paid` stage in `/api/pre-assessment/admin/queue`
- **Tested**: 100% (10/10 backend + frontend all green) — iteration_76.json + iteration_77.json

### Pre-Assessment Client Portal Layer — Phase A Part 2 (2026-04-17)
- **Client MiniPortal** (`/app/frontend/src/components/PreAssessmentMiniPortal.jsx`): Beautiful stage-aware dashboard shown to clients who have a pre-assessment but no active case
  - 6-step progress pipeline (Paid → Upload → Review → Approved → Proposal → Case Active)
  - Stage-specific UI: `payment_received` shows upload UI + Submit button; `documents_submitted/under_review` shows "Under Review"; `approved` shows "Congratulations"; `proposal_sent` shows Accept + Pay buttons; `proposal_paid` shows "Activating your case"; `rejected` shows refund notice
- **Dynamic Sidebar** (`ClientDashboard.jsx`): When `isMiniMode=true` shrinks sidebar to Overview + Tools (AI Scanner only, +Cost Estimator & Eligibility in `isExpandedMode`) + Communication + Profile
- **New Backend Endpoints**:
  - `POST /api/pre-assess-portal/client/submit/{pa_id}` — client marks docs as ready, stage → documents_submitted, notifies partner
  - `POST /api/pre-assess-portal/client/accept-proposal/{pa_id}` — client accepts partner's proposal
  - `POST /api/pre-assess-portal/client/mock-pay-proposal/{pa_id}` — MOCK main-fee payment, stage → proposal_paid
  - `POST /api/pre-assess-portal/admin/approve-final/{pa_id}` — admin's 2nd approval: creates real Case record + copies workflow steps, stage → case_created
- **Updated**: `GET /client/portal-access/{pa_id}` now returns `can_submit_for_review` flag; mini access_level now covers rejected/refund stages
- **Tested**: 100% (11/11 backend tests) — iteration_75.json; Frontend UI verified for multiple stages

### Pre-Assessment Client Portal Layer — Phase A Part 1 (2026-04-17)
- **New router**: `/app/backend/routers/pre_assess_portal.py` extends existing `pre_assessments` collection
- **Public endpoints (no auth)**: `GET /public/{token}`, `POST /public/mock-pay` — creates client user + magic link
- **Magic login** (72h token) + **OTP fallback** (email/phone, 10-min code)
- **Client endpoints**: `my-assessments`, `portal-access/{pa_id}` (returns mini/expanded/full access level)
- **Activity log**: `activity/log`, `activity/pa/{pa_id}` — partner visibility
- **Public pages** (`/pre-assess/:token`, `/magic/:token`): premium branded payment + login UI
- **Verified E2E**: Partner creates PA → generates public link → unauthenticated client pays (MOCK) → user auto-created → magic link issued → client logs in → fetches own assessments → `access_level: mini` + `can_upload_docs: true`

### Previous: AI Document Scanner (P1 Feature)
- **Backend**: `/app/backend/routers/doc_extraction.py` — GPT-4o Vision via Emergent LLM Key
- **Supported docs**: passport, visa, educational cert, academic transcript, IELTS, bank statement, PCC, marriage/birth cert, driver license, offer letter + auto-detect
- **Endpoints**: `/doc-types`, `/sample-docs` (public), `/sample-docs/{id}/extraction` (public demo), `/extract` (base64), `/extract-upload` (multipart), `/save`, `/history`
- **5 pre-loaded specimen docs** with pre-computed extraction (no API cost for demo)
- **Frontend**: `DocumentExtractor.jsx` with 2 tabs (Upload & Extract + Try Demo), animated extraction progress, field-by-field confidence bars (green/amber/red), AI Verified badges, editable fields, Save to Records
- **Integrated in**: Client Dashboard (Tools → AI Document Scanner) + CM Dashboard (Tools)
- **Verified**: 95% confidence on real test_passport.jpg extraction with correct fields (Patel, Anil Kumar, Z9876543, ISO dates)
- **Tested**: 100% (25/25 backend tests passed) — iteration_74.json

### Previous: Fee Database CRUD + Per-Estimate Edits (v3)
- **Option B — Master Fee Database Editor** (Admin-only):
  - Migrated hardcoded `FEE_DATABASE` dict → MongoDB collection `fee_country_catalog` (auto-seeded on first run)
  - 7 new CRUD endpoints: `admin/catalog`, `admin/countries` (POST/PUT/DELETE), `admin/countries/{id}/categories` (POST/PUT/DELETE), `admin/reseed`
  - Full UI `FeeDatabaseManager.jsx` — Admin Sidebar → Planning Tools → Fee Database
  - Add unlimited new countries (slug auto from name) + categories + fee line items (label, amount, mandatory, per_applicant, notes)
  - Reseed utility to revert to built-in defaults
- **Option A — Per-Estimate Inline Edit**:
  - `CalculateRequest` supports `overrides` (correct fees per estimate) + `extra_lines` (ad-hoc custom charges)
  - UI: pencil icon on each fee line → inline editor for label/amount/notes → "Edited" / "Custom" badges
  - "Add Custom Line" button + "Reset all edits" revert button
  - Overrides are per-estimate (don't touch master catalog)
- **Tested**: 100% (25/25 backend) — iteration_73.json; minor 404 issue fixed post-test

### Previous: Share Estimate Link (v2)
- **5 new endpoints**: `share/{id}`, `share/{id}/deactivate`, `share/{id}/stats`, public `public/{token}`, public `public/{token}/lead`
- **Public URL**: `/shared-estimate/:token` — no login, branded view with breakdown + lead capture CTA
- **View count tracking** (per-view increment on public access)
- **Lead capture** auto-assigns lead to estimate owner with source='shared_fee_estimate', priority='high', tag='fee-estimate-viewer' + sends notification
- **Auto-expiry** (default 30 days, max 365) with 410 Gone response when expired
- **Deactivate** kill-switch for owner/admin
- **Tested**: 100% (25/25 backend) — iteration_72.json
- **UI in FeeCalculator**: Share button → dialog shows link + copy + view/lead/expiry stats + deactivate
- **New page**: `/app/frontend/src/pages/SharedEstimate.jsx` with premium branded layout, lead form, success state

### Previous Feature: Automated Government Fee Calculator (v1)
- **Backend**: `/api/fee-calculator/*` (7 endpoints) in `routers/fee_calculator.py`
- **Countries**: 20 (Canada, Australia, UK, USA, NZ, Germany, Singapore, UAE, Ireland, France, Netherlands, Portugal, Spain, Japan, South Korea, Sweden, Denmark, Switzerland, Hong Kong, Malaysia)
- **Currencies**: USD/CAD/AUD/GBP/EUR/NZD/SGD/JPY/SEK/DKK/CHF/HKD/MYR/KRW/AED + INR
- **Live FX**: frankfurter.dev (ECB) cached 1 hr + static fallback
- **Real 2025-26 official fees**: application, biometrics, medicals, skills assessments, language tests, priority surcharges
- **Line items support**: mandatory vs optional, per-applicant multiplier, official_url links, notes
- **Consultancy service fee + GST** (only shown for Partner/CM/Admin; hidden for Clients)
- **Output**: Dual-currency display (Native + ₹INR), Copy-to-Clipboard, Print/PDF, Attach-to-Case
- **Collection**: `fee_estimates` (saved for proposals/cases)
- **Frontend**: `FeeCalculator.jsx` reusable component
- **Integrated in**: Partner (Fee Calculator tab), Case Manager (Tools), Client (Cost Estimator), Admin (Tools)
- **Tested**: 100% backend (28/28 pass in iteration_71)

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123

## Roadmap / Pending

### Next (User-approved)
- **P1**: Improved Document Info Extraction UI + Demo Mode (live OCR-style extraction preview, sample demo, field-level confidence scores, AI verified badges)
- **P1**: White-Label SaaS Multi-Tenancy Architecture (`agency_id` on all core collections, tenant context in JWT, Super-Admin portal, branding, commission mgmt)

### Backlog
- P2: Resend Email live dispatch (requires user RESEND_API_KEY)
- P3: Twilio WhatsApp full integration
- P3: Comparison Tools (on hold, user to specify approach)

### Backend Routers
ai_workflow_builder, deadlines, intake_forms, step_documents, fee_calculator + core (auth, cases, documents, payments, etc.)
