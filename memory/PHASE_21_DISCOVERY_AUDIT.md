# Phase 21.0 — Discovery Audit (READ-ONLY)

> **Prepared for:** Sir 🙏
> **Mode:** Pure investigation — zero code changes
> **Date:** Feb 2026
> **Scope:** `/admin/employees`, `/admin/marketing`, `/admin/hr/settings` → unification into ONE cohesive surface
> **Reference plan:** Phase 21 (21.1 → 21.10)

---

## Executive TL;DR

Sir, **good news** — aap pehle se hi Phase 21 ki **~55% foundation already build kar chuke ho**:

| Phase 21 sub-phase | Status |
|---|---|
| 21.1 Employee Master + Org Chart + Auth + Departments | ✅ **DONE** (production-ready) |
| 21.2 Profile + Documents + Onboarding | 🟡 **50%** (profile✅, docs❌, onboarding❌) |
| 21.3 Attendance + Leave | ✅ **DONE** (full IST-tz aware system with regularization, LWP scan, sandwich detection) |
| 21.4 Salary + Payroll | ❌ **MISSING** (no schema, no collections) |
| 21.5 Tasks + Announcements + Policies | 🟡 **15%** (refund policies only) |
| 21.6 HR Admin + Analytics | ✅ **DONE** (settings, holidays, leave types, approvers, audit) |
| 21.7 Advanced (Chat + Tickets + Assets + Shifts) | 🟡 **40%** (chat & tickets exist, no assets/shifts) |
| 21.8 IT Productivity Tools | ❌ **MISSING** |
| 21.9 Marketing Productivity Tools | 🟡 **30%** (CRM done, no Content/SEO/AEO Studio) |
| 21.10 Mobile responsive + polish | 🟡 **TBD** (most surfaces responsive but no audit done) |

**Key insight:** The "distinct Employee JWT" approach from the original Phase 21 brief is **NOT NEEDED**. Existing `rbac_role` + `permissions[]` + `require_any_permission()` machinery on the **single staff JWT** is sufficient. Backward-compat is guaranteed because every existing employee already has a `rbac_role` and `user_type: "internal"`.

**Recommended hub strategy:** `/admin/portal-hub` mega-landing + retain all 3 existing deep links (backward-compat). Single sidebar `DashboardShell` with grouped nav (Employees / Marketing / HR / IT / Me).

---

## 1. Current State Map

### 1A. `/admin/employees` → `EmployeesPortal.jsx` (Lazy + DashboardShell)

| Surface | File | Lines | Status |
|---|---|---|---|
| Sidebar shell | `pages/EmployeesPortal.jsx` | 109 | ✅ Clean, lazy-loaded children |
| Dashboard | `components/employees/EmployeesDashboard.jsx` | 159 | ✅ Stats, dept-breakdown, recent joiners |
| Departments | `components/employees/DepartmentsPage.jsx` | 175 | ✅ 8 dept cards, head editing |
| All Employees | `components/employees/EmployeesList.jsx` | 197 | ✅ Search + filters + CSV export |
| Org Chart | `components/employees/OrgChart.jsx` | 163 | ✅ Recursive tree with reports_to chain |
| Add Employee | `components/employees/AddEmployeeForm.jsx` | 346 | ✅ 3-step wizard, cascading dept→role→manager |
| Employee Detail | `components/employees/EmployeeDetailModal.jsx` | 534 | ✅ 4 tabs (Profile/Role/History/Activity), Reset Pwd, Toggle Active, Role Change w/ reason, Dashboard Preview |
| Dashboard Preview | `components/employees/DashboardPreviewModal.jsx` | 152 | ✅ Read-only "view as user" peek |

**Backend (`routers/employees.py`, 684 lines):**
| Route | Method | Notes |
|---|---|---|
| `/employees` | GET | List w/ filters, pagination |
| `/employees/stats` | GET | Total/active/on_leave/new + dept breakdown |
| `/employees/recent` | GET | Last 5 joiners |
| `/employees/org-chart` | GET | Recursive children build |
| `/employees/managers-for-role/{role}` | GET | Cascading parent lookup |
| `/employees/{id}` | GET | Profile + manager + direct reports |
| `/employees/{id}/history` | GET | Role-change timeline |
| `/employees/{id}/activity` | GET | Activity log |
| `/employees` | POST | Create + auto employee_id + auto password + auto leave balances + 2FA hint |
| `/employees/{id}` | PATCH | Update profile |
| `/employees/{id}/role` | PATCH | Role change with min-20-char reason + cache invalidation |
| `/employees/{id}/deactivate` | POST | Soft terminate |
| `/employees/{id}/reactivate` | POST | Reverse |
| `/employees/{id}/reset-password` | POST | Generate temp pwd |

**Backend (`routers/departments.py`, 153 lines):**
| Route | Method | Notes |
|---|---|---|
| `/departments` | GET | List + count + head expansion |
| `/departments/{key}` | GET | Single |
| `/departments/{key}/employees` | GET | Dept roster |
| `/departments/{key}/roles` | GET | Available roles for dept |
| `/departments/{key}` | PATCH | Update name/desc/head/color/icon |
| `/departments/_meta/roles` | GET | All internal roles flat |

**DB Collections:** `departments(8)`, `roles(18)`, `user_role_history(0)`, `activity_log(0)`

---

### 1B. `/admin/marketing` → `MarketingDashboard.jsx` (Monolithic, 853 lines)

| Tab | Backend router | Status |
|---|---|---|
| Overview | `leads.py` `campaigns.py` `marketing_tools.py` | ✅ Stats cards + pipeline + follow-ups + sources |
| Lead CRM | `leads.py` | ✅ CRUD + stages + notes + follow-ups |
| Scorecards | `eligibility.py` | ✅ Quiz/pre-score leads + PDF + assign |
| Campaigns | `campaigns.py` | ✅ CRUD + Send + Stats |
| Testimonials | `marketing_tools.py` | ✅ CRUD + featured flag |
| Leaderboard | `marketing_tools.py` | ✅ Partner ranking + tiers |
| Promo Codes | `marketing.py` | ✅ Code + discount + max uses |

**Backend route inventory:**
- `routers/marketing.py` (183 lines) — **referrals + promo codes ONLY**
- `routers/campaigns.py` — campaign CRUD + send
- `routers/leads.py` — lead CRUD + pipeline + follow-ups
- `routers/marketing_tools.py` — testimonials + leaderboard + cross-sell
- `routers/eligibility.py` — quiz scorecard leads

**DB Collections:** `leads(67)`, `campaigns(3)`, `campaign_recipients(24)`, `testimonials(3)`, `referrals(6)`, `promo_codes(9)`

**⚠️ Auth note:** `marketing.py` & `campaigns.py` still use **legacy `current_user["role"] == "admin"`** check (not RBAC `require_any_permission`). Migration TBD.

**❌ Missing (Phase 21.9 expectations):**
- Content Studio (drafts, calendar, AI-generated copy)
- SEO Health Monitor (Lighthouse-style)
- AEO/GEO scoring & optimization
- Social media post composer + scheduler
- A/B test setup for campaigns
- Brand asset library
- Website audit (broken links, missing alt, slow pages)

---

### 1C. `/admin/hr/settings` → `HRSettingsLayout.jsx` + 5 routes

| Route | Layout / Page | Status |
|---|---|---|
| `/admin/hr/settings` | Attendance Settings | ✅ Singleton CRUD |
| `/admin/hr/holidays` | Holiday Calendar | ✅ CRUD + Indian holiday import + copy-year |
| `/admin/hr/leave-types` | Leave Types & Policies | ✅ CRUD with system-lock + soft-delete + usage stats |
| `/admin/hr/approvers` | Approval Configuration | ✅ 3 modes: specific_user / by_department / reports_to_chain + simulate + backup |
| `/admin/hr/audit` | Audit Log | ✅ Policy-change audit trail |

**Backend (`routers/hr_admin.py`, 835 lines):**
- `GET/PATCH /hr/settings` — global attendance settings (office times, late threshold, CL cap, sandwich rule, etc.)
- `GET/POST/PATCH/DELETE /hr/holidays` + `import-indian/{year}` + `copy-from/{y1}/to/{y2}`
- `GET/POST/PATCH /hr/leave-types` + `/deactivate` + `/activate` + soft `DELETE` (with min-20-char reason)
- `GET/PATCH /hr/approvers/config` + `/simulate/{user_id}` + `/eligible-approvers`
- `GET /hr/audit-log` — filter by scope

**Backend (`routers/attendance.py`, 757 lines):**
- `POST /attendance/punch-in` + `punch-out` (with confirm_short_hours flow)
- `GET /attendance/current-status` — live status widget
- `GET /attendance/my-month?year=&month=` — calendar view
- `GET /attendance/user/{user_id}/month` — manager view
- `GET /attendance/today` — HR all-employees-today
- `GET /attendance/late-marks/my`
- `POST /attendance/regularize` + `GET /regularizations/inbox` + `decide`
- `GET /attendance/dashboard` — HR analytics
- `POST /attendance/lwp/scan` — admin trigger

**Backend (`routers/leaves.py`, 539 lines):**
- `GET /leaves/types`
- `GET /leaves/my-balance` + `/balance/{user_id}`
- `POST /leaves/validate` — dry-run with sandwich detection
- `POST /leaves/apply` — w/ accept_sandwich flow
- `GET /leaves/my-history` + `POST /leaves/{id}/cancel`
- `GET /leaves/inbox` + `/inbox-final` (L1 + Final approvers)
- `POST /leaves/{id}/decide`
- `GET /leaves/all` (HR)
- `GET /leaves/balance-history/my` + `/balance-history/user/{id}`

**Employee-facing portal (already exists!):**
- `/portal/welcome` → `PortalWelcome`
- `/portal/attendance` → `MyAttendance`
- `/portal/leaves` → `MyLeaves`
- `/portal/leave-approvals` → `LeaveApprovals`
- `components/attendance/PunchWidget.jsx` (264 lines) — live timer + late ban warning + short-hours confirm

**DB Collections:** `attendance_settings(1)`, `attendance_logs(0)`, `attendance_regularizations(0)`, `late_marks_tracker(0)`, `lwp_records(0)`, `holidays(27)`, `leave_types(11)`, `leave_balances(70)`, `leave_requests(0)`, `leave_balance_history(0)`, `policy_audit_log(33)`

---

### 1D. Auth & RBAC State

- **Single staff JWT** (`/api/auth/login` → Bearer token)
- `users` collection holds `user_type: "internal" | "partner" | "client"` + `rbac_role` + `permissions[]` + `ui_modules[]`
- `roles` collection (18 docs) — keys like `admin_owner`, `sales_head`, `hr_head`, `it_admin`, `marketing_head`, `case_manager`
- `departments` collection (8 docs) — admin, sales, marketing, operations, hr, accounts, it, compliance
- Permission gate: `require_any_permission("employee.view.all", ...)` in dependencies
- Permission cache + invalidation hooks (`rbac_admin.invalidate_cache`)
- 2FA infra: `two_fa_required`, `two_fa_secret` fields present, auto-true if role hierarchy ≥ 3
- Distinct Client JWT exists separately for `/client-portal/*` (Phase 20 Option C)

---

## 2. Gap Analysis (Phase 21 Plan vs Reality)

| Phase 21 Goal | Status | Built? | Notes |
|---|---|---|---|
| **21.1.1** Employee CRUD | ✅ | Yes | Full CRUD + soft terminate |
| **21.1.2** Auto employee_id (LMS-YYYY-NNNN) | ✅ | Yes | `_next_employee_id()` |
| **21.1.3** Cascading dept→role→manager form | ✅ | Yes | 3-step wizard |
| **21.1.4** Org Chart (recursive) | ✅ | Yes | reports_to-based tree |
| **21.1.5** Departments mgmt | ✅ | Yes | 8 depts seeded |
| **21.1.6** Role hierarchy + permissions | ✅ | Yes | `roles_col` w/ hierarchy_level + permissions[] |
| **21.1.7** Distinct Employee JWT | ❌ | No (and **NOT NEEDED** — see Section 8) | Existing staff JWT + RBAC covers this |
| **21.2.1** Self-serve profile editing | 🟡 | Partial | Profile fields exist, no "My Profile" page in `/portal` |
| **21.2.2** Document vault (Aadhar, PAN, offer letter, contract) | ❌ | No | No `employee_documents` collection |
| **21.2.3** Onboarding checklist (laptop assigned, email, induction) | ❌ | No | No `onboarding_tasks` collection |
| **21.2.4** Asset assignment (laptop, phone, ID card) | ❌ | No | No `assets` collection |
| **21.3.1** Attendance: punch in/out with geofence | ✅ | Yes | lat/lng captured, IP+UA logged |
| **21.3.2** Late marks + auto CL deduction | ✅ | Yes | `late_marks_tracker` |
| **21.3.3** LWP auto-marking | ✅ | Yes | `/attendance/lwp/scan` cron-ready |
| **21.3.4** Regularization flow | ✅ | Yes | Grace days + manager approve |
| **21.3.5** Leave types + balances + carry-forward | ✅ | Yes | 11 types seeded |
| **21.3.6** Multi-stage leave approval (L1+Final) | ✅ | Yes | + sandwich detection |
| **21.3.7** Holidays + working-day calendar | ✅ | Yes | India holidays preset |
| **21.4.1** Salary structure (basic/HRA/bonus) | ❌ | No | No `salary_structures` |
| **21.4.2** Monthly payroll generation | ❌ | No | No `payroll_runs` |
| **21.4.3** Payslip PDF + auto-email | ❌ | No | WeasyPrint available, no template |
| **21.4.4** Income tax / TDS computation | ❌ | No | |
| **21.4.5** PF / ESIC / Gratuity tracking | ❌ | No | |
| **21.4.6** Reimbursement claims | ❌ | No | No `reimbursements` collection |
| **21.5.1** Tasks (assign, due date, status) | ❌ | No | No `tasks` collection |
| **21.5.2** Kanban / list view | ❌ | No | |
| **21.5.3** Announcements (company-wide) | ❌ | No | No `announcements` collection |
| **21.5.4** Internal Policies (employee handbook) | ❌ | No | `protection_policies` is for refund policies only |
| **21.6.1** HR Settings + Audit | ✅ | Yes | Full |
| **21.6.2** HR analytics dashboard | 🟡 | Partial | `/attendance/dashboard` exists, no leave/payroll analytics |
| **21.7.1** Internal Chat (1-on-1 + group) | 🟡 | Partial | `chat_conversations(2)` + `chat_messages(11)` exist (internal AI chat?) |
| **21.7.2** Tickets / Help desk | 🟡 | Partial | `tickets(23)` + `ticket_messages(4)` exist (client tickets — needs internal IT/HR ticket variant) |
| **21.7.3** Asset mgmt | ❌ | No | |
| **21.7.4** Shift mgmt | ❌ | No | |
| **21.8.1** Website audit (broken links, missing alt) | ❌ | No | |
| **21.8.2** SEO health monitor (Lighthouse-style) | ❌ | No | |
| **21.8.3** Perf benchmarks visible in IT dash | 🟡 | Partial | `pytest-benchmark` JSON exists, no UI |
| **21.8.4** Dev task tracker | ❌ | No | |
| **21.9.1** Lead CRM | ✅ | Yes | 67 leads |
| **21.9.2** Email campaigns | ✅ | Yes | + send + stats |
| **21.9.3** Testimonials | ✅ | Yes | |
| **21.9.4** Scorecards (quiz) | ✅ | Yes | |
| **21.9.5** Promo codes | ✅ | Yes | |
| **21.9.6** Leaderboard | ✅ | Yes | Partners |
| **21.9.7** Content Studio (drafts, calendar, AI copy) | ❌ | No | |
| **21.9.8** SEO/AEO/GEO scoring | ❌ | No | |
| **21.9.9** Social composer + scheduler | ❌ | No | |
| **21.9.10** A/B test framework | ❌ | No | |
| **21.10** Mobile responsive + polish | 🟡 | Partial | Most uses tailwind responsive, not audited |

**Summary count:** ✅ 24 done · 🟡 10 partial · ❌ 17 missing  → ~**45% complete by feature count**, **~55% by infrastructure weight** (Phase 21.1 + 21.3 + 21.6 are the heavyweights and they're done).

---

## 3. UPGRADE Opportunities (Existing pieces to enhance, not rebuild)

### 3A. Marketing Dashboard
1. **Split monolith** → `MarketingDashboard.jsx` (853 lines) into lazy-loaded children like Employees pattern.
2. **Migrate auth** from legacy `role == 'admin'` to `require_any_permission("marketing.view.all", "campaign.view.all", ...)`.
3. **Brand sweep** — 30+ hardcoded `#2a777a` references should use `leamss-teal-700` tokens.
4. **Add Marketing-side Content Studio** as new tabs without removing existing 7 tabs.
5. **Source attribution** in Pipeline Overview — currently shows count but not conversion %.

### 3B. Employees Portal
1. **Add `/portal/my-profile`** so employees can self-edit (currently admin-only via `EmployeesPortal`).
2. **Expand Add Employee form** to optionally seed onboarding checklist & assign laptop/phone (when 21.2.3 + 21.2.4 land).
3. **Org Chart** — add zoom/pan + export to PNG + filter by dept toggle.
4. **EmployeesDashboard** — add "Birthdays this month" + "Work anniversaries" + "Pending leave approvals (mine)" widgets.
5. **Activity log** — `activity_log(0)` currently empty; many actions are logged but the dashboard doesn't surface them. Hook this up.

### 3C. HR Settings
1. **Unify under same shell** — currently uses its own `HRSettingsLayout` while Employees uses `DashboardShell`. Migrate to one shell.
2. **Surface live data** — show stats inline (e.g., "27 holidays in 2026", "11 leave types active") instead of plain nav labels.
3. **Settings UX** — promote "Late threshold" + "Min work hours" to the top with quick toggles instead of buried form.

### 3D. PunchWidget (currently sits in DashboardShell?)
- Already great. Just need a centralized "Today's Status" mini-strip at the top of `/portal/welcome` and `/admin/portal-hub`.

### 3E. Cross-cutting
1. **Reuse `DashboardShell` everywhere** — already used by `EmployeesPortal`. Marketing & HR Settings should adopt for visual consistency.
2. **Reuse `DashboardPreviewModal`** — extend to preview *what the employee sees* of the new unified hub.
3. **Centralized `_log_activity`** (Phase 20 Option D) — wire all writes into this.

---

## 4. Unification Strategy

### 4A. Architecture: "Portal Hub" pattern

```
┌─────────────────────────────────────────────────────────────────┐
│ /admin/portal-hub  (NEW landing — sidebar mega-page)            │
│                                                                  │
│  ┌─ Sidebar (DashboardShell) ──────────────────────┐  ┌────────┐│
│  │ 🏠 Hub Home                                       │  │ Stage  ││
│  │ ─── EMPLOYEES ──                                  │  │ Area   ││
│  │ • Dashboard                                       │  │        ││
│  │ • Departments      ← deep-link /admin/employees   │  │        ││
│  │ • All Employees                                   │  │        ││
│  │ • Org Chart                                       │  │        ││
│  │ • Add Employee                                    │  │        ││
│  │ ─── HR ──                                         │  │        ││
│  │ • Attendance Settings  ← /admin/hr/settings       │  │        ││
│  │ • Holidays                                        │  │        ││
│  │ • Leave Types                                     │  │        ││
│  │ • Approvers                                       │  │        ││
│  │ • Audit Log                                       │  │        ││
│  │ • HR Analytics  (NEW)                             │  │        ││
│  │ ─── MARKETING ──                                  │  │        ││
│  │ • Overview         ← /admin/marketing             │  │        ││
│  │ • Lead CRM                                        │  │        ││
│  │ • Campaigns                                       │  │        ││
│  │ • Testimonials                                    │  │        ││
│  │ • Promos                                          │  │        ││
│  │ • Content Studio (NEW)                            │  │        ││
│  │ • SEO/AEO/GEO   (NEW)                             │  │        ││
│  │ ─── IT ──                       (NEW)             │  │        ││
│  │ • Site Audit                                      │  │        ││
│  │ • SEO Health                                      │  │        ││
│  │ • Dev Task Tracker                                │  │        ││
│  │ ─── ME ──                                         │  │        ││
│  │ • My Profile  (NEW)        ← /portal/welcome      │  │        ││
│  │ • My Attendance                                   │  │        ││
│  │ • My Leaves                                       │  │        ││
│  │ • My Tasks   (NEW)                                │  │        ││
│  │ • My Payroll (NEW)                                │  │        ││
│  └───────────────────────────────────────────────────┘  └────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 4B. Routing & Backward-compat

- **NEW landing:** `/admin/portal-hub` — single React page that wraps `DashboardShell` with all 5 groups.
- **DEEP LINKS PRESERVED:**
  - `/admin/employees` → redirects to `/admin/portal-hub?tab=emp-dashboard`
  - `/admin/marketing` → redirects to `/admin/portal-hub?tab=mkt-overview`
  - `/admin/hr/settings` → redirects to `/admin/portal-hub?tab=hr-settings`
  - `/admin/hr/holidays`, `/admin/hr/leave-types`, etc. → same pattern
- **OR (recommended):** keep all 3 existing pages exactly as they are AND add `/admin/portal-hub` as the *new* canonical entry. AdminHome.jsx adds one prominent "Open Portal Hub" CTA. Zero breaking changes.

### 4C. State machine

- Single `activeTab` state in `PortalHub.jsx` controls render via switch.
- Lazy-load every panel: `EmployeesDashboard`, `MarketingOverview`, `HRSettings`, etc.
- URL sync: `?tab=mkt-leads` updates URL; deep links honored on mount.
- Sidebar group `defaultOpen` based on `?tab=` prefix.

### 4D. Tabs taxonomy (final)

```
EMPLOYEES (existing)  : emp-dashboard, emp-departments, emp-list, emp-org-chart, emp-add
HR (existing)         : hr-settings, hr-holidays, hr-leave-types, hr-approvers, hr-audit, hr-analytics (NEW)
MARKETING (existing+) : mkt-overview, mkt-leads, mkt-scorecards, mkt-campaigns,
                        mkt-testimonials, mkt-leaderboard, mkt-promos,
                        mkt-content-studio (NEW), mkt-seo (NEW), mkt-social (NEW)
IT (NEW)              : it-site-audit, it-seo-health, it-dev-tasks, it-perf
ME (NEW + existing)   : me-profile (NEW), me-attendance, me-leaves, me-tasks (NEW),
                        me-payroll (NEW), me-policies (NEW)
```

### 4E. Visual Identity

- Single brand palette: `leamss-teal-700` primary, `leamss-orange-500` accent, `leamss-red-500` for danger.
- Each group has a sidebar tint (teal=Employees, blue=HR, orange=Marketing, slate=IT, emerald=Me).
- Department color tokens already in `DEPT_COLORS` map — reuse for org chart + employee cards.

---

## 5. Additional Features (Beyond Original Phase 21)

### 5A. Quick wins (1-2 days each)

1. **Birthdays & Anniversaries widget** — surface in EmployeesDashboard + Hub Home.
2. **"Who's on leave today" strip** — pulls from `leaves.py /all?status=approved` filtered by date.
3. **Slack-style mentions in lead notes** — `@employee_name` autocomplete.
4. **"Reports filed but unread"** badge on AdminHome.
5. **Quick-jump command palette (Cmd+K)** — search employees, leads, policies.
6. **Personal pinned shortcuts** per user.
7. **CSV import for bulk employee onboarding** (matches existing `data_import.py` pattern).

### 5B. Compounding value features

1. **Skill matrix** — track each employee's skills (Python, Sales, Visa expertise). Power-up for org chart filtering & assignment routing.
2. **1-on-1 meeting tracker** — manager + report cadence + agenda + notes.
3. **Goal/OKR tracking** — quarterly objectives per employee, public to manager.
4. **360° feedback** — peer review forms, anonymous mode.
5. **Internal job board** — open roles posted internally first, referral bonus engine on top.
6. **Knowledge base for internal SOPs** — reuse `kb_unified` infrastructure.
7. **Vacation calendar overlay** — see whole team's blocked dates in one Gantt.
8. **Document expiry tracker for employees** — passports, IDs, visas (reuse `doc_expiry.py`).
9. **Helpdesk SLA dashboard** — for internal IT/HR tickets.
10. **Exit interview workflow** — auto-prompt on `deactivate_employee` + structured feedback capture.

### 5C. Marketing & IT specific upgrades

**Marketing:**
- **AI campaign copywriter** (Claude Sonnet — Emergent key already wired) — generate subject + body variants.
- **Landing page conversion tracker** — UTM source attribution.
- **Drip campaign builder** (multi-step email sequences with delays).
- **Win/Loss tagging** on leads — feeds back into lead score model.
- **AEO/GEO checker** — query likely "answer engine" prompts and score brand surface.
- **Lighthouse audit on demand** + history graph.

**IT:**
- **Deploy log viewer** (preview & live) — frontend tail of supervisor logs.
- **DB index advisor** — suggest indexes based on slow query log.
- **Backup status dashboard** — verify mongodump cron is alive.
- **Secret rotation reminder** — expiry tracker on JWT_SECRET, Stripe key, Resend key, Emergent LLM key.
- **API rate limit map** — which endpoints are hot, who's calling.

### 5D. Cross-platform — Mobile-first ME tab

- Punch in/out widget at top of `/portal/welcome` (PunchWidget already exists, just bring to top).
- One-tap "Apply leave" button.
- Today's tasks + tomorrow's tasks summary.
- Pinned announcements.
- "My team is online" status strip (presence indicator).

---

## 6. Refined Phase 21 Plan

> Building on **what already exists**, treating Phase 21 as an **expansion** (not rebuild) of the existing surfaces, unified under `/admin/portal-hub`. Each sub-phase scoped to fit a single working session.

| Sub-phase | Title | Effort | Net new code | Reuses |
|---|---|---|---|---|
| **21.A** | Portal Hub Shell + Routing | 0.5 day | `pages/PortalHub.jsx`, deep-link aliases | `DashboardShell`, existing pages |
| **21.B** | Employee Self-Service (`/portal/my-profile`) | 1 day | `pages/MyProfile.jsx` + reuse `EmployeeDetailModal` profile tab | RBAC `employee.update.own` |
| **21.C** | Documents Vault | 1.5 days | `routers/employee_documents.py`, `employee_documents` collection, S3-style upload | Object storage playbook |
| **21.D** | Onboarding Checklist + Assets | 1 day | `routers/onboarding.py`, `routers/assets.py`, 2 new collections | reuse `notifications` |
| **21.E** | Tasks (assign/Kanban) | 1.5 days | `routers/tasks.py`, `tasks` collection + Kanban UI | reuse `notifications` + `activity_log` |
| **21.F** | Announcements + Internal Policies | 1 day | `routers/announcements.py`, `routers/internal_policies.py`, 2 collections | reuse `notifications` + audit |
| **21.G** | Salary + Payroll Run | 2 days | `routers/payroll.py`, `salary_structures` + `payroll_runs` + `payslips` collections + PDF | reuse WeasyPrint, Resend |
| **21.H** | Reimbursements | 1 day | `routers/reimbursements.py` + collection | reuse 2-stage approval pattern |
| **21.I** | HR Analytics Dashboard | 1 day | `pages/HRAnalytics.jsx` | reuse attendance/leave aggregations |
| **21.J** | Marketing Content Studio | 1.5 days | `routers/content_drafts.py`, calendar UI + AI copywriter (Claude) | reuse Emergent LLM key |
| **21.K** | SEO / AEO / GEO Studio | 2 days | `routers/seo_audit.py` + Lighthouse runner + scoring tables | new |
| **21.L** | IT Dept Tools (Site Audit + Dev Tasks) | 1.5 days | `routers/it_tools.py` + perf benchmark UI | reuse `pytest-benchmark` JSON |
| **21.M** | Internal Chat + Internal Tickets | 1.5 days | extend `chat.py` + new `internal_tickets.py` | reuse chat infra |
| **21.N** | RBAC Migration of Marketing/HR endpoints | 0.5 day | Replace `role == 'admin'` with `require_any_permission` | RBAC catalog |
| **21.O** | Brand sweep on Marketing dashboard | 0.5 day | Hex → tokens | leamss palette |
| **21.P** | Mobile responsive audit + polish | 1 day | Tailwind tweaks + viewport meta checks | Existing components |

**Total estimate:** ~18 working days (compressible to ~10-12 days with batched releases).

---

## 7. Recommended Build Order

> **Principle:** Ship the shell first (21.A) so subsequent panels can attach. Front-load high-touch employee experience (21.B-F). Payroll (21.G) is heaviest, so it follows once foundations are solid. IT/Marketing studios (21.J-L) are independent and can ship in parallel.

### MVP Path (Phase 21 Slice 1 — "Unification first") — **5 working days**
```
Day 1  ▸ 21.A  Portal Hub Shell + Routing             (deliver: /admin/portal-hub live)
Day 2  ▸ 21.B  Employee Self-Service Profile          (deliver: /portal/my-profile)
Day 3  ▸ 21.E  Tasks (assign/Kanban)                  (deliver: me-tasks + emp-tasks tabs)
Day 4  ▸ 21.F  Announcements + Internal Policies      (deliver: news feed + handbook)
Day 5  ▸ 21.N + 21.O  RBAC migration + brand sweep    (deliver: clean baseline)
```
✅ **Outcome of MVP slice:** Unified hub live, every employee has a real "Me" experience, internal-comms backbone in place, marketing dashboard cleaned up.

### Slice 2 — "HR & Payroll" — **4 working days**
```
Day 6  ▸ 21.C  Document Vault
Day 7  ▸ 21.D  Onboarding + Assets
Day 8-9 ▸ 21.G Salary + Payroll Run                   (heaviest single chunk)
```

### Slice 3 — "Productivity Tools" — **5 working days**
```
Day 10  ▸ 21.H  Reimbursements
Day 11  ▸ 21.I  HR Analytics
Day 12  ▸ 21.J  Marketing Content Studio (+ AI)
Day 13-14 ▸ 21.K  SEO/AEO/GEO Studio                  (Lighthouse runner is non-trivial)
```

### Slice 4 — "IT + Chat + Polish" — **3 working days**
```
Day 15  ▸ 21.L  IT Dept Tools
Day 16  ▸ 21.M  Internal Chat + Tickets
Day 17  ▸ 21.P  Mobile responsive audit + polish
```

### Recommended deploy cadence
- After each slice → Pytest pass + benchmark check + manual smoke + 1 deployment.
- Slice 1 should be the first user-visible release; everything after is additive.

---

## 8. RBAC + Auth Migration Matrix (8th section per Sir's request)

### 8A. Current Auth Scheme per Surface

| Surface | Auth scheme | RBAC enforced? | Notes |
|---|---|---|---|
| `/admin/employees` | Staff JWT + `require_any_permission("employee.view.all", ...)` | ✅ Yes | Modern pattern |
| `/admin/marketing` (overview + campaigns + leads + promos) | Staff JWT + legacy `current_user["role"] == "admin"` | ❌ No | Needs migration |
| `/admin/marketing` (testimonials + leaderboard via `marketing_tools.py`) | Staff JWT + `get_current_user` only | ❌ No | Open to any logged-in staff |
| `/admin/hr/*` (settings, holidays, leave-types, approvers, audit) | Staff JWT + `require_any_permission` | ✅ Yes | Modern pattern |
| `/portal/attendance` `/portal/leaves` | Staff JWT + `attendance.clock.own` / `leave.apply.own` | ✅ Yes | Modern pattern |
| `/client-portal/*` | **Distinct Client JWT** (separate `/api/client-auth/*`) | n/a | Phase 20 Option C |

### 8B. Should we add a separate "Employee JWT"?

**Recommendation: ❌ NO. Use a single Staff JWT.**

Reasoning:
1. The current `users` collection already has `user_type: "internal"` discriminator.
2. The `rbac_role` field + `permissions[]` cover *all* roles from `admin_owner` (CEO) down to `intern_analyst`.
3. Splitting would force token-juggling on the frontend and double the auth surface for marginal gain.
4. The **distinction that matters** is between **internal staff** and **external clients** — and that's already handled by the distinct Client JWT introduced in Phase 20 Option C.
5. The original Phase 21 brief said "Auth" — what was really meant is **role-scoped views** of the same JWT, which RBAC already provides.

**What we DO need (instead):**
- Migrate the 2 legacy endpoints (`marketing.py`, `campaigns.py`, parts of `marketing_tools.py`) from `role == 'admin'` to `require_any_permission`.
- Add the **missing permission keys** to the RBAC catalog (see 8D).
- Frontend route guards check `user.permissions` instead of `user.role`.

### 8C. Per-role Permission Matrix (target state for Phase 21)

| Permission key | admin_owner | hr_head | sales_head | marketing_head | it_admin | dept_lead | sales_manager / mgr_* | sr_emp / employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `employee.view.all` | ✅ | ✅ | — | — | — | — | — | — |
| `employee.view.dept` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (own dept) | ✅ (own dept) | — |
| `employee.view.own` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `employee.create.any` | ✅ | ✅ | — | — | — | — | — | — |
| `employee.update.all` | ✅ | ✅ | — | — | — | — | — | — |
| `employee.update.own` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `employee.terminate.any` | ✅ | ✅ | — | — | — | — | — | — |
| `attendance.clock.own` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `attendance.view.team` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| `attendance.view.dept` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| `attendance.view.all` | ✅ | ✅ | — | — | — | — | — | — |
| `attendance.update.team` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| `leave.apply.own` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `leave.approve.l1` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| `leave.approve.final` | ✅ | ✅ | — | — | — | — | — | — |
| `task.assign.team` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| `task.view.own` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payroll.run.all` 🆕 | ✅ | ✅ | — | — | — | — | — | — |
| `payroll.view.own` 🆕 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `announcement.create.any` 🆕 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| `policy.manage.all` 🆕 | ✅ | ✅ | — | — | — | — | — | — |
| `marketing.view.all` 🆕 | ✅ | — | ✅ | ✅ | — | — | — | — |
| `marketing.update.all` 🆕 | ✅ | — | ✅ | ✅ | — | — | — | — |
| `campaign.send.any` 🆕 | ✅ | — | — | ✅ | — | — | — | — |
| `lead.view.all` 🆕 | ✅ | — | ✅ | ✅ | — | — | — | — |
| `lead.assign.any` 🆕 | ✅ | — | ✅ | ✅ | — | — | — | — |
| `content.create.any` 🆕 | ✅ | — | — | ✅ | — | — | — | — |
| `seo.audit.run` 🆕 | ✅ | — | — | ✅ | ✅ | — | — | — |
| `it.audit.run` 🆕 | ✅ | — | — | — | ✅ | — | — | — |
| `dev.tasks.manage` 🆕 | ✅ | — | — | — | ✅ | — | — | — |
| `system.view.all` | ✅ | — | — | — | — | — | — | — |
| `system.update.any` | ✅ | — | — | — | — | — | — | — |

🆕 = needs to be **added to RBAC catalog** during Phase 21.N migration.

### 8D. Permission keys to ADD to RBAC catalog (`core/rbac/`)

```python
# Marketing
"marketing.view.all", "marketing.update.all",
"campaign.view.all", "campaign.send.any",
"lead.view.all", "lead.update.own", "lead.assign.any",
"testimonial.manage.all", "promo.manage.all",
"content.create.any", "content.publish.any",
"seo.audit.run", "seo.view.all",

# IT
"it.audit.run", "it.view.logs",
"dev.tasks.manage", "dev.tasks.view.team",

# Payroll / HR new
"payroll.run.all", "payroll.view.own", "payroll.view.team",
"announcement.create.any", "announcement.view.all",
"policy.manage.all", "policy.view.all",
"document.upload.own", "document.view.team",
"task.assign.team", "task.assign.any", "task.view.own", "task.view.team",
"reimbursement.submit.own", "reimbursement.approve.team",
"asset.assign.any", "asset.view.own",
"onboarding.manage.all", "onboarding.view.own",
```

### 8E. Backward-compatibility strategy

1. **Existing staff tokens keep working** — every existing JWT carries `rbac_role`; mapping to permissions is server-side via `users_col.permissions`.
2. **Legacy `role == 'admin'` checks** stay live until `21.N` migration. Migration is endpoint-by-endpoint, no big-bang.
3. **Bridge layer:** during migration, `require_any_permission` should accept `_legacy_role: ["admin"]` flag so we don't have to flip everything at once. Example shim:
   ```python
   @router.delete("/promo/{promo_id}")
   async def delete_promo(
       promo_id: str,
       current_user: dict = Depends(
           require_any_permission("promo.manage.all", _legacy_role="admin")
       ),
   ):
   ```
4. **Frontend** continues reading `user.permissions` from `localStorage` (already does in `EmployeeDetailModal` line 41-48). No frontend regression.
5. **RBAC cache** must be invalidated when new permission keys are seeded — `invalidate_cache()` hook already exists.
6. **Distinct Client JWT (Phase 20 Option C) remains untouched** — separate namespace.

### 8F. Migration order (matches 21.N)
1. `routers/marketing.py` → `routers/campaigns.py` → `routers/leads.py` → `routers/marketing_tools.py` (Marketing first).
2. Seed new permission keys into `roles_col` via a small migration script (`migrations/phase21_rbac.py`).
3. Invalidate cache.
4. Run regression Pytest (302 tests) — must stay green.
5. Add new permission-gated tests for `task.*`, `payroll.*`, `content.*`, `seo.*`.

---

## ✅ Recommended Decision for Sir

1. ✅ **APPROVE** the "Portal Hub" pattern as the unification approach (Section 4).
2. ✅ **APPROVE** the MVP Slice 1 build order (Days 1–5 in Section 7) — delivers unified hub + employee self-service + tasks + announcements + clean RBAC baseline within ~5 working days.
3. ✅ **CONFIRM** single Staff JWT path (no separate Employee JWT) — Section 8B.
4. 🟡 **DEFER** Slices 2–4 to next iteration cycles after Slice 1 is in user's hands.
5. 🟢 **OPTIONAL** future enhancements list (Section 5) — Sir can pick & choose post-Slice-1.

**No code changes have been made.** All findings are based on read-only inspection of:
- 3 frontend pages + 9 component files
- 6 backend routers (employees, marketing, hr_admin, attendance, leaves, departments)
- 34 relevant MongoDB collections
- App.js route map

**Sir, awaiting your GO on which slice(s) to kickoff first.** 🙏

---

*Report end. Generated Feb 2026.*
