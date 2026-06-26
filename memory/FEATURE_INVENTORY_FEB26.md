# LEAMSS Full Portal Feature Inventory — Feb 26, 2026

**Purpose:** Atomic inventory of every meaningful feature across the LEAMSS portal — backend + frontend — to power Phase 22 RBAC v2 (Capability Packs + Layer-2 per-feature overrides). Each feature becomes a togglable row in the admin Role & Capability Builder UI.

**Source scan:**
- Backend: 137 router modules in `/app/backend/routers/`, ~840+ endpoints
- Frontend: 144 page files + ~140 `<Route>` entries in `/app/frontend/src/App.js`
- Existing Hub: 6 GROUP_CARDS in `EmployeesPortal.jsx` (communication / employees / hr / marketing / it / me)

---

## 🎯 9 Capability Packs (Sir's confirmed list — updated Feb 26 with `ai_power_tools` as 9th pack)

| Pack ID | Display Name | Color Accent | Auto-granted to | Notes |
|---------|-------------|--------------|-----------------|-------|
| `baseline_employee` | Baseline Employee | leamss-teal | Every internal staff (cannot be revoked) | Personal workspace + comms |
| `marketing` | Marketing | leamss-orange | dept=Marketing | Marketing dept tools + Atlas content mgmt |
| `it` | IT | slate | dept=IT | Site audit, dev tracker, scrapers |
| `accounts` | Accounts | sky | dept=Accounts/Finance | Finance, payments, commission admin |
| `hr` | HR | leamss-red | dept=HR | People, payroll, leave/attendance policies |
| `operations` | Operations | emerald | dept=Operations / Sales / Case Mgmt | Sales + CM + cases + ops tools + Atlas + KB |
| `ai_power_tools` | AI Power Tools | leamss-orange (gradient) | _(none — admin assigns to selected users)_ | AI Workflow Builder + AI Proposal + AI Verify + Doc Extraction + Intelligence Engine. Sir's mental model: "Case Manager + Sales ko AI Workflow Builder do" |
| `manager_elevation` | Manager Elevation | leamss-teal (dark) | Anyone with direct reports | Approval-type actions overlay |
| `admin_elevation` | Admin Elevation | leamss-red (dark) | rbac_role=admin / admin_owner only | Super-overlay: RBAC, system, bulk ops |

---

## 📋 Feature Catalog (per category)

> Layer-2 overrides operate at the `feature_id` level. The admin UI's "Feature Catalog" lists every row below as a toggle.

### Category 1: Baseline Employee (15 features — auto-granted, not togglable)

| feature_id | Name | Description | Backend routes (key) | Frontend routes | Default packs |
|------------|------|-------------|----------------------|-----------------|---------------|
| `baseline.hub_home` | Hub Home Dashboard | Personal landing with KPI tiles + group chips | `GET /api/admin/portal-hub/stats` | `/admin/employees`, `/portal` | baseline_employee |
| `baseline.profile` | My Profile | View / edit own personal + bank + emergency | `GET /api/users/me`, `PATCH /api/employees/{me}` | `/portal/my-profile` | baseline_employee |
| `baseline.attendance` | My Attendance | Punch in/out, monthly calendar | `POST /api/attendance/punch`, `GET /api/attendance/me/...` | `/portal/attendance` | baseline_employee |
| `baseline.leaves` | My Leaves | Apply, balance, history | `POST /api/leaves`, `GET /api/leaves/me/...` | `/portal/leaves` | baseline_employee |
| `baseline.tasks` | My Tasks | Kanban of own assignments | `GET /api/tasks?mode=me` | `/portal/my-tasks` | baseline_employee |
| `baseline.payslips` | My Payslips | View own monthly + PDF | `GET /api/employees/me/payslips`, `GET /api/payslips/{id}/pdf` | `/portal/my-payslips` | baseline_employee |
| `baseline.documents` | My Documents | Own ID/edu/bank vault | `GET /api/employee-documents/me/...` | `/portal/my-documents` | baseline_employee |
| `baseline.assets` | My Assets | Laptop/phone/access cards | `GET /api/onboarding-assets/me` | `/portal/my-assets` | baseline_employee |
| `baseline.onboarding` | My Onboarding | Personal checklist + evidence | `GET /api/onboarding-assets/checklist` | `/portal/my-onboarding` | baseline_employee |
| `baseline.reimbursements` | My Reimbursements | Submit + track own claims | `POST /api/reimbursements`, `GET /api/reimbursements/me/...` | `/portal/my-reimbursements` | baseline_employee |
| `baseline.announcements` | Announcements Feed | Read company news | `GET /api/announcements-policies` | `/portal/announcements` | baseline_employee |
| `baseline.policies` | Policies | Read + acknowledge handbook | `GET /api/announcements-policies?type=policy` | `/portal/policies` | baseline_employee |
| `baseline.notifications` | Notifications | Inbox + SSE stream | `GET /api/notifications/...` | `/notifications` | baseline_employee |
| `baseline.chat` | Internal Chat | DMs + group threads | `/api/internal-chat/*` (11 endpoints) | `/portal/chat`, `/admin/chat` | baseline_employee |
| `baseline.tickets_raise` | Support Tickets (raise) | Submit own ticket, view own | `POST /api/support-tickets`, `GET /api/support-tickets?raised_by=me` | `/portal/tickets` | baseline_employee |

### Category 2: Marketing (12 features)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `marketing.dashboard` | Marketing Dashboard | `/api/marketing/*` (7 ep) | `/admin/marketing` | marketing |
| `marketing.content_studio` | AI Content Studio (Claude 4.5) | `/api/content-studio/*` (15 ep) | `/portal/marketing/content-studio` · `/admin/marketing/content-studio` | marketing |
| `marketing.seo_tools` | SEO Tools Hub | `/api/marketing-tools/*` (SEO subset) | `/portal/marketing/seo` · `/admin/marketing/seo` | marketing |
| `marketing.aeo_tools` | AEO Tools Hub | `/api/marketing-tools/*` (AEO subset) | `/portal/marketing/aeo` · `/admin/marketing/aeo` | marketing |
| `marketing.geo_tools` | GEO Tools Hub (LLM citation) | `/api/marketing-tools/*` (GEO subset) | `/portal/marketing/geo` · `/admin/marketing/geo` | marketing |
| `marketing.leads_crm` | Lead CRM | `/api/leads/*` (10 ep) | `/admin/marketing` (Leads tab) | marketing |
| `marketing.campaigns` | Email Campaigns / Drip | `/api/campaigns/*` (7 ep) | `/admin/marketing` (Campaigns tab) | marketing |
| `marketing.promo_codes` | Promo Codes & Coupons | `/api/coupons/*` (7 ep) | `/admin/coupons` | marketing, accounts |
| `marketing.scorecards` | Eligibility Scorecards (Leads) | `/api/surveys/*` (3 ep) | `/admin/marketing` (Scorecards) | marketing |
| `marketing.referrals` | Referral Program | `/api/referrals/*` (4 ep) | `/admin/marketing` (Referrals) | marketing |
| `marketing.brand_guide` | Brand Guide Editor | (static) | `/admin/brand-guide` | marketing |
| `marketing.public_pages_manager` | Public Pages Manager | `/api/admin/public-pages/*` (7 ep) | `/admin/public-pages` | marketing |

### Category 3: Sales & CRM (15 features — under Operations pack per Sir)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `sales.dashboard` | Sales Dashboard | `/api/sales/*` (12 ep) | `/sales/dashboard` | operations |
| `sales.smart_sales_helper` | Smart Sales Helper | `/api/sales-ai-helpers/*` (2 ep) | (inline in sales wizard) | operations |
| `sales.my_targets` | My Sales Targets | `/api/targets/me/*` | `/sales/my-targets` | operations |
| `sales.team_targets` | Team Targets (Admin) | `/api/targets/*` (19 ep) | `/admin/sales/targets` | manager_elevation |
| `sales.target_templates` | Target Templates | `/api/targets/templates/*` | `/admin/sales/target-templates` | admin_elevation |
| `sales.express_approvals` | Express Sales Approvals | `/api/express-sales/*` (10 ep) | `/admin/sales/express-approvals` | operations, manager_elevation |
| `sales.express_settings` | Express Settings | `/api/express-sales/settings/*` | `/admin/sales/express-settings` | admin_elevation |
| `sales.client_assessment` | Client Assessment Wizard | `/api/sales-assessments/*` (15 ep) | `/sales/client-assessment` | operations |
| `sales.my_assessments` | My Assessments | `/api/sales-assessments/me/*` | `/sales/my-assessments` | operations |
| `sales.calculator` | Eligibility Calculator | `/api/sales-calculator/*` (2 ep), `/api/fee-calculator/*` (20 ep) | `/sales/calculator`, `/calculator` | operations |
| `sales.occupations_search` | Occupation Search | `/api/sales-occupations/*` (5 ep) | `/sales/occupations` | operations |
| `sales.occupations_compare` | Occupation Compare | `/api/sales-compare/*` (4 ep) | `/sales/occupations/compare`, `/sales/compare` | operations |
| `sales.visa_compare` | Visa Compare | `/api/visa-compare/*` (4 ep) | `/visa-compare`, `/start#compare` | operations |
| `sales.proposal_builder` | Proposal Builder | `/api/proposals/*` + `/api/proposal-docs/*` (12 ep) | `/sales/proposal-builder` | operations |
| `sales.wizard_v2` | Sales Wizard v2 | `/api/sales-wizard-v2/*` (4 ep) | `/sales/wizard` (steps 1-7) | operations |

### Category 4: Commission & Revenue (10 features)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `commission.my_commission` | My Commission | `/api/cm-earnings/*`, `/api/partner-commissions/me/*` | `/sales/my-commission` | operations |
| `commission.dashboard_admin` | Commission Dashboard (Admin) | `/api/sales-commission/*` (11 ep) | `/admin/sales/commissions` | accounts, manager_elevation |
| `commission.slabs_manager` | Commission Slabs Manager | `/api/sales-commission/slabs/*` | `/admin/sales/commission-slabs` | admin_elevation |
| `commission.analytics` | Commission Analytics | `/api/sales-commission/analytics/*` | (CommissionAnalytics page) | accounts, manager_elevation |
| `commission.payouts_queue` | Payout Queue | `/api/payouts/*` (7 ep) | `/admin/payouts` | accounts |
| `commission.partner_commissions` | Partner Commissions | `/api/partner-commissions/*` (5 ep) · `/api/partner-analytics/*` (4 ep) | (PartnerDashboard) | accounts, manager_elevation |
| `revenue.forecasting` | Revenue Forecasting | `/api/analytics/forecasting/*` | (RevenueForecasting page) | accounts |
| `revenue.country_product_analytics` | Country/Product Analytics | `/api/analytics/country-product/*` | (CountryProductAnalytics page) | accounts, marketing |
| `revenue.refunds` | Refunds Management | `/api/refunds/*` (5 ep) | (FinanceDashboard) | accounts |
| `revenue.payment_history` | Payment History | `/api/payment-history/*` (6 ep), `/api/payments/*` (6 ep) | (FinanceDashboard) | accounts |

### Category 5: HR — People, Payroll & Policies (16 features)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `hr.analytics` | HR Analytics Dashboard | `/api/hr-analytics/*` (7 ep) | `/admin/hr/analytics`, `/portal/hr-analytics` | hr, manager_elevation |
| `hr.attendance_settings` | Attendance Settings | `/api/hr-admin/attendance-settings/*` | `/admin/hr/settings` | hr |
| `hr.holiday_calendar` | Holiday Calendar Manager | `/api/hr-admin/holidays/*` | `/admin/hr/holidays` | hr |
| `hr.leave_types` | Leave Types Manager | `/api/hr-admin/leave-types/*` | `/admin/hr/leave-types` | hr |
| `hr.approver_config` | Approver Configuration | `/api/hr-admin/approvers/*` | `/admin/hr/approvers` | hr |
| `hr.audit_log` | HR Audit Log | `/api/hr-admin/audit/*` | `/admin/hr/audit` | hr, admin_elevation |
| `hr.reimbursements_approve` | Approve Reimbursements (HR + Finance merge to payslip) | `/api/reimbursements/*` (8 ep) | `/admin/reimbursements/pending`, `/admin/reimbursements/all` | hr, manager_elevation |
| `hr.payroll_admin` | Payroll Admin (generate, approve, mark-paid) | `/api/payslips/*`, `/api/payroll/*` (11 ep) | (NEEDS PayrollAdminHub.jsx — UI gap) | hr, accounts |
| `hr.salary_structures` | Salary Structures CRUD | `/api/employees/{id}/salary-structure/*` | (NEEDS UI — UI gap) | hr, accounts |
| `hr.employee_directory` | All Employees Directory | `/api/employees/*` (19 ep) | `/admin/employees` (All tab) | hr, manager_elevation |
| `hr.org_chart` | Org Chart | `/api/employees/org-chart` | `/admin/employees` (Org tab) | hr |
| `hr.departments_admin` | Departments Manager | `/api/departments/*` (6 ep) | `/admin/employees` (Departments tab) | hr |
| `hr.add_employee` | Add Employee Wizard | `POST /api/employees`, `POST /api/users` | `/admin/employees` (Add tab) | hr |
| `hr.employee_documents` | Employee Documents (manage all) | `/api/employee-documents/*` (8 ep) | (inline in employee detail) | hr |
| `hr.publish_announcements` | Publish Announcements | `/api/announcements-policies/announcements/*` | `/admin/announcements` | hr |
| `hr.publish_policies` | Publish Policies | `/api/announcements-policies/policies/*` | `/admin/policies` | hr |

### Category 6: Manager Elevation (overlay — 8 features)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `manager.approve_leaves` | Approve Leaves (L1 / Final) | `/api/leaves/approvals/*` (subset of 13) | `/portal/leave-approvals` | manager_elevation |
| `manager.approve_reimbursements` | Approve Reimbursements (direct reports) | `/api/reimbursements/team/*` | `/admin/reimbursements/pending` | manager_elevation |
| `manager.team_tasks` | Team Tasks view | `/api/tasks?mode=team` | `/admin/employee-tasks` | manager_elevation |
| `manager.team_attendance` | Team Attendance view | `/api/attendance/team/*` | (TeamAttendance — exists in admin/employees) | manager_elevation |
| `manager.cm_performance` | CM Performance | `/api/cm-efficiency/*` (10 ep) | `/cm-performance` (CMPerformance.jsx) | manager_elevation, operations |
| `manager.team_commission_view` | Team Commission View | `/api/sales-commission/team/*` | (commission dashboard, team filter) | manager_elevation |
| `manager.team_targets_view` | Team Targets View | `/api/targets/team/*` | (SalesTargetsAdmin team filter) | manager_elevation |
| `manager.protection_policies_view` | Protection Policies View | `/api/protection-policies/*` (10 ep, read) | `/admin/protection-policies` | manager_elevation, admin_elevation |

### Category 7: Operations / Case Management (15 features)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `ops.cases_list` | Cases (all + unassigned) | `/api/cases/*` (21 ep) | (within AdminDashboard cases tab) | operations |
| `ops.case_notes_tags` | Case Notes & Tags | `/api/case-notes/*` (6 ep) | (CaseNotesAndTags.jsx) | operations |
| `ops.case_timeline` | Case Timeline | `/api/timeline/*` (1 ep) | (CaseTimeline.jsx) | operations |
| `ops.case_transfer` | Case Transfer | `/api/cases/{id}/transfer` | (CaseTransfer.jsx) | operations, manager_elevation |
| `ops.cm_dashboard` | Case Manager Dashboard | `/api/cm-efficiency/*` | `/case-manager` | operations |
| `ops.allocations` | Allocations Manager | `/api/pa-allocations/*` (8 ep) | `/admin/allocations` | operations, manager_elevation |
| `ops.pa_reviews` | PA Reviews Queue | `/api/pa-reviews/*` (4 ep) | `/admin/pa-reviews` | operations |
| `ops.pre_assess_portal` | Pre-Assessment Portal | `/api/pre-assess-portal/*` (20 ep), `/api/pre-assessment/*` (18 ep) | (PreAssessmentPayment) | operations |
| `ops.deadlines` | Deadlines Tracker | `/api/deadlines/*` (5 ep) | (within case detail) | operations |
| `ops.sla_tracker` | SLA Tracker | `/api/share-links-dashboard/*` (7 ep) | (SLATracker.jsx) | operations, manager_elevation |
| `ops.appointments` | Appointments | `/api/appointments/*` (4 ep) | (Appointments.jsx) | operations |
| `ops.canned_responses` | Canned Responses | `/api/canned-responses/*` (5 ep) | (CannedResponses.jsx) | operations |
| `ops.client_greetings` | Client Greetings | `/api/greetings/*` (3 ep) | (ClientGreetings.jsx) | operations |
| `ops.mini_portals_admin` | Mini Portals Admin | `/api/mini-portal/*` (5 ep) | `/admin/mini-portals` | operations |
| `ops.feedback_requests` | Feedback Requests | `/api/feedback-requests/*` (4 ep) | (within client experience) | operations |

### Category 8: Accounts / Finance (8 features)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `accounts.finance_dashboard` | Finance Dashboard | (aggregator of payments + refunds + payouts) | `/admin/finance` | accounts |
| `accounts.products_manager` | Products Manager | `/api/products/*` (14 ep) | `/admin/products` | accounts |
| `accounts.cost_structures` | Product Cost Structures | `/api/product-cost-structures/*` (7 ep) | `/admin/products/cost-structures` | accounts |
| `accounts.products_bulk_import` | Products Bulk Import | `/api/products-bulk-import/*` (3 ep) | (within ProductsManager) | accounts, admin_elevation |
| `accounts.fee_policies` | Pre-Assessment Fee Policies | `/api/pre-assessment-fee-policies/*` (8 ep) | `/admin/fee-policies` | accounts |
| `accounts.upsell_bundles` | Upsell Bundles | `/api/upsell-bundles/*` (5 ep) | (within ProductsManager) | accounts |
| `accounts.vendors_manager` | Vendors Manager | `/api/vendors/*` (11 ep) | `/admin/vendors` | accounts, operations |
| `accounts.vendor_categories` | Vendor Categories | `/api/vendors/categories/*` | `/admin/vendors/categories` | accounts |

### Category 9: IT (6 features)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `it.site_audit` | Site Audit Hub | `/api/site-audit/*` (3 ep) | `/portal/it/site-audit` · `/admin/it/site-audit` | it |
| `it.dev_tracker` | Dev Tracker (Kanban) | `/api/dev-tracker/*` (6 ep) | `/portal/it/dev-tracker` · `/admin/it/dev-tracker` | it |
| `it.scrapers_hub` | Scraper Hub | `/api/scrapers/*` (4 ep) | `/admin/scrapers` | it |
| `it.data_import_hub` | Data Import Hub | `/api/data-import/*` (7 ep), `/api/import-batches/*` (5 ep) | `/admin/data-import` | it, admin_elevation |
| `it.client_errors` | Client Errors Dashboard | `/api/client-errors/*` (9 ep) | `/admin/client-errors` | it |
| `it.verify_hub` | Verification Hub | `/api/ai-verification/*` (2 ep), `/api/enrichment/*` (3 ep) | `/admin/verify-hub` | it |

### Category 10: Atlas / Migration Intelligence (8 features)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `atlas.search` | Atlas Search (admin internal) | `/api/atlas/*`, `/api/public-atlas/*` (7 ep) | `/admin/atlas/search` | operations, marketing |
| `atlas.country_guides_admin` | Country Guides Admin | `/api/country-guides/*` (10 ep) | `/admin/country-guides` | marketing |
| `atlas.occupation_master_admin` | Occupation Master Admin | `/api/occupation-master/*` (15 ep), `/api/occupation-master-import/*` (2 ep) | `/admin/kb/occupation-master` | operations, marketing |
| `atlas.authorities_admin` | Assessing Authorities Admin | `/api/assessing-authorities/*` (5 ep), `/api/assessing-authorities-write/*` (8 ep) | `/admin/authorities` | operations |
| `atlas.anz_intel_audit` | ANZ Intel Audit | `/api/anz-intel/*` (46 ep) | `/admin/anz-intel/audit` | operations |
| `atlas.visa_pathways_editor` | Visa Pathways Editor | `/api/state-nominations/*` (5 ep) + intel | `/admin/visa-pathways` | operations |
| `atlas.calculator_rules` | Calculator Rules Editor | `/api/fee-calculator/rules/*` | `/admin/calculator-rules` | operations, accounts |
| `atlas.country_templates` | Country Templates | `/api/country-templates/*` (6 ep) | (within country guides) | marketing |

### Category 11: Knowledge Base & Eligibility (8 features)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `kb.eligibility_kb` | Eligibility Knowledge Base | `/api/eligibility-kb/*` (16 ep) | `/admin/eligibility/knowledge-base` | operations |
| `kb.kb_unified` | Unified Knowledge Base | `/api/kb-unified/*` (10 ep), `/api/kb-settings/*` (4 ep) | (KnowledgeBase.jsx) | operations |
| `kb.eligibility_scoring` | Eligibility Scoring Rules | `/api/eligibility/*` (10 ep), `/api/eligibility-profiles/*` (13 ep) | `/admin/eligibility-scoring` | operations |
| `kb.eligibility_profiles` | Eligibility Profiles | `/api/eligibility-profiles/*` | `/eligibility/profiles` · `/eligibility/new-assessment` | operations |
| `kb.pre_assessment` | Pre-Assessment Reports | `/api/assessment-reports/*` (10 ep), `/api/pre-assessment-report-v2/*` (2 ep) | (PublicAssessmentReport, PublicReportView) | operations |
| `kb.info_sheets` | Info Sheets Manager | `/api/info-sheets/*` (12 ep), `/api/eligibility-info-sheet/*` (6 ep) | `/admin/info-sheets/:entityType/:entityId` | operations |
| `kb.legal_archive` | Legal Archive | `/api/legal-archive/*` (7 ep) | (within KB) | operations, admin_elevation |
| `kb.knowledge_base_legacy` | Knowledge Base (legacy) | `/api/knowledge-base/*` (6 ep) | `/admin/knowledge-base` | operations |

### Category 12: AI / Power Tools (assigned via `ai_power_tools` pack — Sir's 9th pack confirmed)

> Sir's directive: "Case Manager + Sales ko AI Workflow Builder do" — these features now live in a dedicated `ai_power_tools` pack which admin explicitly toggles per user. Default-granted to **no one**; admin selectively assigns.

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `ai.workflow_builder` | AI Workflow Builder (Claude) | `/api/ai-workflow-builder/*` (7 ep) | `/admin/ai-workflow` | ai_power_tools |
| `ai.workflows_legacy` | Workflow Builder (legacy) | `/api/workflows/*` (4 ep) | `/admin/workflows` | ai_power_tools |
| `ai.ai_intelligence` | AI Intelligence | `/api/ai-intelligence/*` (9 ep) | (inline in dashboards) | ai_power_tools |
| `ai.ai_proposal` | AI Proposal Generator | `/api/ai-proposal/*` (1 ep) | (inline in proposal builder) | ai_power_tools |
| `ai.ai_verification` | AI Verification | `/api/ai-verification/*` (2 ep) | (within VerificationHub) | ai_power_tools |
| `ai.doc_extraction` | Document Extraction (OCR) | `/api/doc-extraction/*` (9 ep) | (inline in document upload) | ai_power_tools |
| `ai.intelligence_engine` | Intelligence Engine | `/api/intelligence/*` (4 ep), `/api/audit-insights/*` (2 ep) | `/admin/audit-insights` | ai_power_tools |

### Category 13: System & Admin Elevation (10 features — admin_owner / admin only)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `admin.dashboard` | Admin Dashboard | `/api/admin/*`, `/api/stats/*` (5 ep) | `/admin` | admin_elevation |
| `admin.user_management` | User Management (CRUD + invite) | `/api/users/*` (6 ep), `/api/admin-users/*` (2 ep), `/api/auth/*` (9 ep) | `/admin/employees` (with Users tab) | admin_elevation |
| `admin.rbac_packs_management` | RBAC Capability Packs Management | `/api/rbac/packs/*`, `/api/rbac/feature-catalog/*` (NEW Phase 22) | `/admin/employees` (Role & Capability Builder tab) | admin_elevation |
| `admin.rbac_audit_log` | RBAC Audit Log | `/api/rbac/audit/*` (NEW Phase 22), `/api/rbac-admin/*` (4 ep) | (within user detail) | admin_elevation |
| `admin.activity_log` | Activity Log | `/api/activity/*` (6 ep) | `/admin/activity` | admin_elevation |
| `admin.analytics_dashboard` | Analytics Dashboard | `/api/analytics/*` (13 ep), `/api/funnel-metrics/*` (1 ep) | `/admin/analytics`, `/admin/funnel-dashboard` | admin_elevation, accounts |
| `admin.cockpit` | Cockpit (real-time KPIs) | `/api/cockpit/*` (4 ep) | `/admin/cockpit`, `/admin/cockpit-mockup` | admin_elevation |
| `admin.bulk_operations` | Bulk Operations | `/api/admin-superpowers/*` (9 ep) | (BulkOperations.jsx) | admin_elevation |
| `admin.protection_policies_admin` | Protection Policies (manage) | `/api/protection-policies/*` (10 ep) | `/admin/protection-policies` | admin_elevation |
| `admin.system_settings` | System Settings (rates, notifications) | `/api/settings/*` (3 ep), `/api/notification-channels/*` (7 ep), `/api/email-digest/*` (4 ep), `/api/currency/*` (3 ep) | (within admin) | admin_elevation |

### Category 14: Communication (Tickets — non-baseline subset)

| feature_id | Name | Backend | Frontend | Default packs |
|------------|------|---------|----------|---------------|
| `comms.tickets_triage` | Tickets Triage (all departments, assign, internal notes) | `/api/support-tickets/*` (9 ep — admin views + assign + internal-notes) | `/portal/tickets`, `/admin/tickets` (admin view) | hr, it, manager_elevation, admin_elevation |
| `comms.chat_admin_groups` | Chat — Admin Group Management | `/api/internal-chat/groups/*` | (within ChatHub) | admin_elevation |

---

## 📊 Inventory Totals

| Category | # Features |
|----------|-----------|
| 1. Baseline Employee | 15 |
| 2. Marketing | 12 |
| 3. Sales & CRM | 15 |
| 4. Commission & Revenue | 10 |
| 5. HR — People, Payroll & Policies | 16 |
| 6. Manager Elevation (overlay) | 8 |
| 7. Operations / Case Management | 15 |
| 8. Accounts / Finance | 8 |
| 9. IT | 6 |
| 10. Atlas / Migration Intelligence | 8 |
| 11. Knowledge Base & Eligibility | 8 |
| 12. AI / Power Tools | 7 |
| 13. System & Admin Elevation | 10 |
| 14. Communication (non-baseline) | 2 |
| **GRAND TOTAL** | **140 features** |

---

## 🎁 Pack-to-Features Mapping (Layer 1 quick presets)

```
baseline_employee = [ALL 15 baseline.* features]
marketing         = [ALL 12 marketing.* features]
                  + revenue.country_product_analytics
sales/operations  = [ALL 15 sales.* + ALL 15 ops.* + commission.my_commission
                  + ALL 8 atlas.* + ALL 8 kb.*]
                  → labeled "Operations" pack (covers Sales + Case Mgmt + Atlas + KB per Sir's direction)
it                = [ALL 6 it.*]
accounts          = [ALL 8 accounts.* + ALL 10 commission.* + ALL revenue.*
                  + marketing.promo_codes + atlas.calculator_rules]
hr                = [ALL 16 hr.* + manager.approve_reimbursements]
manager_elevation = [ALL 8 manager.* + hr.analytics + sales.team_targets
                  + sales.express_approvals + commission.team_view + ops.case_transfer
                  + ops.allocations + ops.sla_tracker + comms.tickets_triage]
admin_elevation   = [ALL 10 admin.* + sales.express_settings + sales.target_templates
                  + hr.audit_log + kb.legal_archive + commission.slabs_manager
                  + comms.chat_admin_groups + it.data_import_hub]
ai_power_tools (override-only, no default pack) = [ai.workflow_builder, ai.ai_intelligence,
                  ai.ai_proposal, ai.ai_verification, ai.doc_extraction,
                  ai.intelligence_engine, ai.workflows_legacy]
```

---

## 🔑 Pre-RBAC v2 Gaps Identified

These are surfaces with backend ready but **no UI** today — call them out so Sir knows where post-22 polish is needed:

| Gap | Status |
|-----|--------|
| `hr.payroll_admin` UI (Payroll Hub for bulk generate / approve / mark-paid) | Backend ✅ · UI ❌ (deferred — earlier Sir held the dedicated PayrollHub) |
| `hr.salary_structures` UI (assign/edit/history) | Backend ✅ · UI ❌ |
| `admin.rbac_packs_management` UI | Backend will be built in 22.2; UI in 22.3 |
| `admin.rbac_audit_log` UI | Backend will be built in 22.2; UI in 22.3 |

Sir, these are pure UI gaps. RBAC v2 unlocks the visibility/permission layer; the actual UI build is a future story.

---

## 🛡️ Default Role → Pack Migration Plan (Phase 22.2)

| Legacy `role` value (existing in DB) | New `capability_packs` | Notes |
|----------------|----------------------|-------|
| `admin_owner` | `[baseline_employee, admin_elevation, manager_elevation, hr, accounts, operations, marketing, it]` | Super-pack overlay (acts as god-mode) |
| `admin` | `[baseline_employee, admin_elevation, manager_elevation, operations]` | Slightly lighter than owner |
| `case_manager` | `[baseline_employee, operations]` | + manager_elevation if `is_manager=true` in DB |
| `partner` | `[baseline_employee, operations]` | (partner uses separate auth — staff side only if internal staff) |
| `staff` (generic) | `[baseline_employee]` | Plus dept-specific pack inferred from `department` field |
| `employee` | `[baseline_employee]` | Same as staff |
| `hr` | `[baseline_employee, hr]` + `manager_elevation` if manager | — |
| `marketing` | `[baseline_employee, marketing]` | — |
| `it` | `[baseline_employee, it]` | — |
| `accounts` / `finance` | `[baseline_employee, accounts]` | — |
| `sales` | `[baseline_employee, operations]` | Sales rides Operations pack per Sir |

**Guarantee:** Every user post-migration has ≥ their current effective permissions. Zero permission regression.

---

## ✅ Sir-Validation Checkpoint (PAUSE here for Sir GO)

Sir 🙏, **140 features across 14 categories** mapped. Sub-Slice 22.0 complete. Please review:

1. **Coverage adequate?** — Anything user-visible that I missed? (Client portal, Vendor portal, Partner portal are intentionally **excluded** since they have separate auth + are not staff-side RBAC scope.)
2. **Pack assignments sane?** — Are the 8-pack default mappings (esp. `hr.payroll_admin` under `[hr, accounts]`, `commission.*` under `accounts`, AI tools as override-only) aligned with your mental model?
3. **AI tools — override-only OR add to admin_elevation default?** — Currently zero default pack; only via override. Should `admin_elevation` auto-include them?
4. **Atlas / KB rolled under Operations** — OK? Or split into separate pack?

After your GO, I'll proceed to:
- **22.2** — Backend: capability_packs collection, feature_catalog seed, effective-capabilities computation, audit log, migration script, pytest
- **22.3** — Frontend: Role & Capability Builder UI (3-layer: pack chips → catalog grid → live preview → reason+save)
- **22.4** — User-creation smart defaults + Promote/Demote modals + Templates + Bulk-import CSV columns

Hinglish me reply karenge Sir? 🚀
