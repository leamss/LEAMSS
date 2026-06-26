"""Phase 22 — Canonical RBAC v2 capability pack + feature catalog data.

Single source of truth. Both the boot-time seeder (`seed_capability_packs.py`)
and the API endpoints (`routers/rbac_v2.py`) read from these constants.

Mirrors `/app/memory/FEATURE_INVENTORY_FEB26.md` — 9 packs · 140 features · 14 categories.
"""
from typing import List, Dict, Any

# ════════════════════════════════════════════════════════════════════
# 9 Capability Packs
# ════════════════════════════════════════════════════════════════════

CAPABILITY_PACKS: List[Dict[str, Any]] = [
    {
        "pack_id": "baseline_employee",
        "name": "Baseline Employee",
        "description": "Personal workspace + comms. Auto-granted to every internal staff. Cannot be revoked.",
        "color": "leamss-teal",
        "icon": "User",
        "sort_order": 1,
        "is_baseline": True,
        "is_admin_only": False,
        "is_system": True,
    },
    {
        "pack_id": "marketing",
        "name": "Marketing",
        "description": "Marketing dashboard, content studio, SEO/AEO/GEO tools, campaigns, public pages.",
        "color": "leamss-orange",
        "icon": "Megaphone",
        "sort_order": 2,
        "is_baseline": False,
        "is_admin_only": False,
        "is_system": True,
    },
    {
        "pack_id": "it",
        "name": "IT",
        "description": "Site audit, dev tracker, scrapers, data import, client errors.",
        "color": "slate",
        "icon": "Server",
        "sort_order": 3,
        "is_baseline": False,
        "is_admin_only": False,
        "is_system": True,
    },
    {
        "pack_id": "accounts",
        "name": "Accounts / Finance",
        "description": "Finance dashboard, products, payments, refunds, payouts, commissions admin.",
        "color": "sky",
        "icon": "Wallet",
        "sort_order": 4,
        "is_baseline": False,
        "is_admin_only": False,
        "is_system": True,
    },
    {
        "pack_id": "hr",
        "name": "HR",
        "description": "People, payroll, leave/attendance policies, holidays, audit.",
        "color": "leamss-red",
        "icon": "ShieldCheck",
        "sort_order": 5,
        "is_baseline": False,
        "is_admin_only": False,
        "is_system": True,
    },
    {
        "pack_id": "operations",
        "name": "Operations",
        "description": "Sales + Case Mgmt + Atlas + Knowledge Base + ops tools. Default for Sales / Case Manager / Operations dept.",
        "color": "emerald",
        "icon": "Network",
        "sort_order": 6,
        "is_baseline": False,
        "is_admin_only": False,
        "is_system": True,
    },
    {
        "pack_id": "ai_power_tools",
        "name": "AI Power Tools",
        "description": "AI Workflow Builder, AI Proposal, AI Verification, Doc Extraction, Intelligence Engine. Admin selectively assigns.",
        "color": "leamss-orange",
        "icon": "Sparkles",
        "sort_order": 7,
        "is_baseline": False,
        "is_admin_only": False,
        "is_system": True,
    },
    {
        "pack_id": "manager_elevation",
        "name": "Manager Elevation",
        "description": "Approval-type actions overlay. Assign to anyone with direct reports.",
        "color": "leamss-teal",
        "icon": "UsersRound",
        "sort_order": 8,
        "is_baseline": False,
        "is_admin_only": False,
        "is_system": True,
    },
    {
        "pack_id": "admin_elevation",
        "name": "Admin Elevation",
        "description": "Super-overlay: RBAC mgmt, system settings, bulk ops, audit log. Only admin_owner can assign.",
        "color": "leamss-red",
        "icon": "ShieldCheck",
        "sort_order": 9,
        "is_baseline": False,
        "is_admin_only": True,
        "is_system": True,
    },
]


# ════════════════════════════════════════════════════════════════════
# 140 Features — atomic catalog
# Format: (feature_id, name, category, default_packs, backend_perms, frontend_routes)
# ════════════════════════════════════════════════════════════════════

def _feat(fid: str, name: str, category: str, packs: List[str],
          perms: List[str] = None, routes: List[str] = None,
          description: str = "") -> Dict[str, Any]:
    return {
        "feature_id": fid,
        "name": name,
        "description": description or name,
        "category": category,
        "default_packs": packs,
        "backend_permissions": perms or [],
        "frontend_routes": routes or [],
        "is_baseline": "baseline_employee" in packs,
        "is_admin_only": packs == ["admin_elevation"],
        "is_system": True,
    }


FEATURE_CATALOG: List[Dict[str, Any]] = [
    # ───── Category 1: Baseline Employee (15) ─────
    _feat("baseline.hub_home", "Hub Home Dashboard", "baseline", ["baseline_employee"], [], ["/admin/employees", "/portal"]),
    _feat("baseline.profile", "My Profile", "baseline", ["baseline_employee"], [], ["/portal/my-profile"]),
    _feat("baseline.attendance", "My Attendance", "baseline", ["baseline_employee"], ["attendance.view.own"], ["/portal/attendance"]),
    _feat("baseline.leaves", "My Leaves", "baseline", ["baseline_employee"], ["leave.view.own", "leave.create.own"], ["/portal/leaves"]),
    _feat("baseline.tasks", "My Tasks", "baseline", ["baseline_employee"], ["task.view.own"], ["/portal/my-tasks"]),
    _feat("baseline.payslips", "My Payslips", "baseline", ["baseline_employee"], ["payslip.view.own"], ["/portal/my-payslips"]),
    _feat("baseline.documents", "My Documents", "baseline", ["baseline_employee"], [], ["/portal/my-documents"]),
    _feat("baseline.assets", "My Assets", "baseline", ["baseline_employee"], [], ["/portal/my-assets"]),
    _feat("baseline.onboarding", "My Onboarding", "baseline", ["baseline_employee"], [], ["/portal/my-onboarding"]),
    _feat("baseline.reimbursements", "My Reimbursements", "baseline", ["baseline_employee"], ["reimbursement.create.own", "reimbursement.view.own"], ["/portal/my-reimbursements"]),
    _feat("baseline.announcements", "Announcements Feed", "baseline", ["baseline_employee"], [], ["/portal/announcements"]),
    _feat("baseline.policies", "Policies", "baseline", ["baseline_employee"], [], ["/portal/policies"]),
    _feat("baseline.notifications", "Notifications", "baseline", ["baseline_employee"], [], ["/notifications"]),
    _feat("baseline.chat", "Internal Chat", "baseline", ["baseline_employee"], [], ["/portal/chat", "/admin/chat"]),
    _feat("baseline.tickets_raise", "Support Tickets (raise own)", "baseline", ["baseline_employee"], [], ["/portal/tickets"]),

    # ───── Category 2: Marketing (12) ─────
    _feat("marketing.dashboard", "Marketing Dashboard", "marketing", ["marketing"], ["marketing.view.all"], ["/admin/marketing"]),
    _feat("marketing.content_studio", "AI Content Studio (Claude 4.5)", "marketing", ["marketing"], ["marketing.content.create"], ["/portal/marketing/content-studio", "/admin/marketing/content-studio"]),
    _feat("marketing.seo_tools", "SEO Tools Hub", "marketing", ["marketing"], ["marketing.view.all"], ["/portal/marketing/seo", "/admin/marketing/seo"]),
    _feat("marketing.aeo_tools", "AEO Tools Hub", "marketing", ["marketing"], ["marketing.view.all"], ["/portal/marketing/aeo", "/admin/marketing/aeo"]),
    _feat("marketing.geo_tools", "GEO Tools Hub", "marketing", ["marketing"], ["marketing.view.all"], ["/portal/marketing/geo", "/admin/marketing/geo"]),
    _feat("marketing.leads_crm", "Lead CRM", "marketing", ["marketing"], ["marketing.view.all"], []),
    _feat("marketing.campaigns", "Email Campaigns", "marketing", ["marketing"], ["marketing.view.all"], []),
    _feat("marketing.promo_codes", "Promo Codes & Coupons", "marketing", ["marketing", "accounts"], ["coupon.view.all"], ["/admin/coupons"]),
    _feat("marketing.scorecards", "Eligibility Scorecards", "marketing", ["marketing"], [], []),
    _feat("marketing.referrals", "Referral Program", "marketing", ["marketing"], [], []),
    _feat("marketing.brand_guide", "Brand Guide Editor", "marketing", ["marketing"], [], ["/admin/brand-guide"]),
    _feat("marketing.public_pages_manager", "Public Pages Manager", "marketing", ["marketing"], [], ["/admin/public-pages"]),

    # ───── Category 3: Sales & CRM (15) ─────
    _feat("sales.dashboard", "Sales Dashboard", "sales", ["operations"], ["sales.view.own"], ["/sales/dashboard"]),
    _feat("sales.smart_sales_helper", "Smart Sales Helper", "sales", ["operations"], [], []),
    _feat("sales.my_targets", "My Sales Targets", "sales", ["operations"], [], ["/sales/my-targets"]),
    _feat("sales.team_targets", "Team Targets (Admin)", "sales", ["manager_elevation"], ["sales.view.all"], ["/admin/sales/targets"]),
    _feat("sales.target_templates", "Target Templates", "sales", ["admin_elevation"], [], ["/admin/sales/target-templates"]),
    _feat("sales.express_approvals", "Express Sales Approvals", "sales", ["operations", "manager_elevation"], [], ["/admin/sales/express-approvals"]),
    _feat("sales.express_settings", "Express Settings", "sales", ["admin_elevation"], [], ["/admin/sales/express-settings"]),
    _feat("sales.client_assessment", "Client Assessment Wizard", "sales", ["operations"], [], ["/sales/client-assessment"]),
    _feat("sales.my_assessments", "My Assessments", "sales", ["operations"], [], ["/sales/my-assessments"]),
    _feat("sales.calculator", "Eligibility Calculator", "sales", ["operations"], [], ["/sales/calculator", "/calculator"]),
    _feat("sales.occupations_search", "Occupation Search", "sales", ["operations"], [], ["/sales/occupations"]),
    _feat("sales.occupations_compare", "Occupation Compare", "sales", ["operations"], [], ["/sales/occupations/compare"]),
    _feat("sales.visa_compare", "Visa Compare", "sales", ["operations"], [], ["/visa-compare"]),
    _feat("sales.proposal_builder", "Proposal Builder", "sales", ["operations"], [], ["/sales/proposal-builder"]),
    _feat("sales.wizard_v2", "Sales Wizard v2", "sales", ["operations"], [], []),

    # ───── Category 4: Commission & Revenue (10) ─────
    _feat("commission.my_commission", "My Commission", "commission_revenue", ["operations"], [], ["/sales/my-commission"]),
    _feat("commission.dashboard_admin", "Commission Dashboard (Admin)", "commission_revenue", ["accounts", "manager_elevation"], ["commission.view.all"], ["/admin/sales/commissions"]),
    _feat("commission.slabs_manager", "Commission Slabs Manager", "commission_revenue", ["admin_elevation"], [], ["/admin/sales/commission-slabs"]),
    _feat("commission.analytics", "Commission Analytics", "commission_revenue", ["accounts", "manager_elevation"], [], []),
    _feat("commission.payouts_queue", "Payout Queue", "commission_revenue", ["accounts"], [], ["/admin/payouts"]),
    _feat("commission.partner_commissions", "Partner Commissions", "commission_revenue", ["accounts", "manager_elevation"], [], []),
    _feat("revenue.forecasting", "Revenue Forecasting", "commission_revenue", ["accounts"], [], []),
    _feat("revenue.country_product_analytics", "Country / Product Analytics", "commission_revenue", ["accounts", "marketing"], [], []),
    _feat("revenue.refunds", "Refunds Management", "commission_revenue", ["accounts"], [], []),
    _feat("revenue.payment_history", "Payment History", "commission_revenue", ["accounts"], [], []),

    # ───── Category 5: HR (16) ─────
    _feat("hr.analytics", "HR Analytics Dashboard", "hr", ["hr", "manager_elevation"], ["hr.view.all"], ["/admin/hr/analytics", "/portal/hr-analytics"]),
    _feat("hr.attendance_settings", "Attendance Settings", "hr", ["hr"], ["hr.policy.update"], ["/admin/hr/settings"]),
    _feat("hr.holiday_calendar", "Holiday Calendar", "hr", ["hr"], ["hr.policy.update"], ["/admin/hr/holidays"]),
    _feat("hr.leave_types", "Leave Types Manager", "hr", ["hr"], ["hr.policy.update"], ["/admin/hr/leave-types"]),
    _feat("hr.approver_config", "Approver Configuration", "hr", ["hr"], ["hr.policy.update"], ["/admin/hr/approvers"]),
    _feat("hr.audit_log", "HR Audit Log", "hr", ["hr", "admin_elevation"], ["hr.view.all"], ["/admin/hr/audit"]),
    _feat("hr.reimbursements_approve", "Approve Reimbursements", "hr", ["hr", "manager_elevation"], ["reimbursement.approve"], ["/admin/reimbursements/pending", "/admin/reimbursements/all"]),
    _feat("hr.payroll_admin", "Payroll Admin (generate · approve · pay)", "hr", ["hr", "accounts"], ["payroll.manage"], ["/admin/payroll"]),
    _feat("hr.salary_structures", "Salary Structures CRUD", "hr", ["hr", "accounts"], ["payroll.manage"], ["/admin/payroll"]),
    _feat("hr.employee_directory", "All Employees Directory", "hr", ["hr", "manager_elevation"], ["employee.view.all"], ["/admin/employees"]),
    _feat("hr.org_chart", "Org Chart", "hr", ["hr"], ["employee.view.all"], []),
    _feat("hr.departments_admin", "Departments Manager", "hr", ["hr"], [], []),
    _feat("hr.add_employee", "Add Employee Wizard", "hr", ["hr"], ["employee.create.any"], []),
    _feat("hr.employee_documents", "Employee Documents (manage)", "hr", ["hr"], [], []),
    _feat("hr.publish_announcements", "Publish Announcements", "hr", ["hr"], [], ["/admin/announcements"]),
    _feat("hr.publish_policies", "Publish Policies", "hr", ["hr"], [], ["/admin/policies"]),

    # ───── Category 6: Manager Elevation overlay (8) ─────
    _feat("manager.approve_leaves", "Approve Leaves", "manager", ["manager_elevation"], ["leave.approve.l1", "leave.approve.final"], ["/portal/leave-approvals"]),
    _feat("manager.approve_reimbursements", "Approve Reimbursements (team)", "manager", ["manager_elevation"], ["reimbursement.approve"], ["/admin/reimbursements/pending"]),
    _feat("manager.team_tasks", "Team Tasks", "manager", ["manager_elevation"], ["task.view.team"], ["/admin/employee-tasks"]),
    _feat("manager.team_attendance", "Team Attendance", "manager", ["manager_elevation"], ["attendance.view.team"], []),
    _feat("manager.cm_performance", "CM Performance", "manager", ["manager_elevation", "operations"], [], []),
    _feat("manager.team_commission_view", "Team Commission View", "manager", ["manager_elevation"], [], []),
    _feat("manager.team_targets_view", "Team Targets View", "manager", ["manager_elevation"], [], []),
    _feat("manager.protection_policies_view", "Protection Policies (view)", "manager", ["manager_elevation", "admin_elevation"], [], ["/admin/protection-policies"]),

    # ───── Category 7: Operations / Case Management (15) ─────
    _feat("ops.cases_list", "Cases (all + unassigned)", "operations", ["operations"], ["case.view.all"], []),
    _feat("ops.case_notes_tags", "Case Notes & Tags", "operations", ["operations"], [], []),
    _feat("ops.case_timeline", "Case Timeline", "operations", ["operations"], [], []),
    _feat("ops.case_transfer", "Case Transfer", "operations", ["operations", "manager_elevation"], [], []),
    _feat("ops.cm_dashboard", "Case Manager Dashboard", "operations", ["operations"], [], ["/case-manager"]),
    _feat("ops.allocations", "Allocations Manager", "operations", ["operations", "manager_elevation"], [], ["/admin/allocations"]),
    _feat("ops.pa_reviews", "PA Reviews Queue", "operations", ["operations"], ["pa.approve.l1", "pa.approve.l2"], ["/admin/pa-reviews"]),
    _feat("ops.pre_assess_portal", "Pre-Assessment Portal", "operations", ["operations"], [], []),
    _feat("ops.deadlines", "Deadlines Tracker", "operations", ["operations"], [], []),
    _feat("ops.sla_tracker", "SLA Tracker", "operations", ["operations", "manager_elevation"], [], []),
    _feat("ops.appointments", "Appointments", "operations", ["operations"], [], []),
    _feat("ops.canned_responses", "Canned Responses", "operations", ["operations"], [], []),
    _feat("ops.client_greetings", "Client Greetings", "operations", ["operations"], [], []),
    _feat("ops.mini_portals_admin", "Mini Portals Admin", "operations", ["operations"], [], ["/admin/mini-portals"]),
    _feat("ops.feedback_requests", "Feedback Requests", "operations", ["operations"], [], []),

    # ───── Category 8: Accounts / Finance (8) ─────
    _feat("accounts.finance_dashboard", "Finance Dashboard", "accounts", ["accounts"], [], ["/admin/finance"]),
    _feat("accounts.products_manager", "Products Manager", "accounts", ["accounts"], ["product.view.all"], ["/admin/products"]),
    _feat("accounts.cost_structures", "Product Cost Structures", "accounts", ["accounts"], [], ["/admin/products/cost-structures"]),
    _feat("accounts.products_bulk_import", "Products Bulk Import", "accounts", ["accounts", "admin_elevation"], [], []),
    _feat("accounts.fee_policies", "Pre-Assessment Fee Policies", "accounts", ["accounts"], [], ["/admin/fee-policies"]),
    _feat("accounts.upsell_bundles", "Upsell Bundles", "accounts", ["accounts"], [], []),
    _feat("accounts.vendors_manager", "Vendors Manager", "accounts", ["accounts", "operations"], [], ["/admin/vendors"]),
    _feat("accounts.vendor_categories", "Vendor Categories", "accounts", ["accounts"], [], ["/admin/vendors/categories"]),

    # ───── Category 9: IT (6) ─────
    _feat("it.site_audit", "Site Audit Hub", "it", ["it"], [], ["/portal/it/site-audit", "/admin/it/site-audit"]),
    _feat("it.dev_tracker", "Dev Tracker (Kanban)", "it", ["it"], [], ["/portal/it/dev-tracker", "/admin/it/dev-tracker"]),
    _feat("it.scrapers_hub", "Scraper Hub", "it", ["it"], [], ["/admin/scrapers"]),
    _feat("it.data_import_hub", "Data Import Hub", "it", ["it", "admin_elevation"], [], ["/admin/data-import"]),
    _feat("it.client_errors", "Client Errors Dashboard", "it", ["it"], [], ["/admin/client-errors"]),
    _feat("it.verify_hub", "Verification Hub", "it", ["it"], [], ["/admin/verify-hub"]),

    # ───── Category 10: Atlas / Migration Intel (8) ─────
    _feat("atlas.search", "Atlas Search (admin)", "atlas", ["operations", "marketing"], [], ["/admin/atlas/search"]),
    _feat("atlas.country_guides_admin", "Country Guides Admin", "atlas", ["marketing"], [], ["/admin/country-guides"]),
    _feat("atlas.occupation_master_admin", "Occupation Master Admin", "atlas", ["operations", "marketing"], [], ["/admin/kb/occupation-master"]),
    _feat("atlas.authorities_admin", "Assessing Authorities Admin", "atlas", ["operations"], [], ["/admin/authorities"]),
    _feat("atlas.anz_intel_audit", "ANZ Intel Audit", "atlas", ["operations"], [], ["/admin/anz-intel/audit"]),
    _feat("atlas.visa_pathways_editor", "Visa Pathways Editor", "atlas", ["operations"], [], ["/admin/visa-pathways"]),
    _feat("atlas.calculator_rules", "Calculator Rules Editor", "atlas", ["operations", "accounts"], [], ["/admin/calculator-rules"]),
    _feat("atlas.country_templates", "Country Templates", "atlas", ["marketing"], [], []),

    # ───── Category 11: Knowledge Base & Eligibility (8) ─────
    _feat("kb.eligibility_kb", "Eligibility Knowledge Base", "knowledge_base", ["operations"], [], ["/admin/eligibility/knowledge-base"]),
    _feat("kb.kb_unified", "Unified Knowledge Base", "knowledge_base", ["operations"], [], []),
    _feat("kb.eligibility_scoring", "Eligibility Scoring Rules", "knowledge_base", ["operations"], [], ["/admin/eligibility-scoring"]),
    _feat("kb.eligibility_profiles", "Eligibility Profiles", "knowledge_base", ["operations"], [], ["/eligibility/profiles"]),
    _feat("kb.pre_assessment", "Pre-Assessment Reports", "knowledge_base", ["operations"], [], []),
    _feat("kb.info_sheets", "Info Sheets Manager", "knowledge_base", ["operations"], [], []),
    _feat("kb.legal_archive", "Legal Archive", "knowledge_base", ["operations", "admin_elevation"], [], []),
    _feat("kb.knowledge_base_legacy", "Knowledge Base (legacy)", "knowledge_base", ["operations"], [], ["/admin/knowledge-base"]),

    # ───── Category 12: AI Power Tools (7) ─────
    _feat("ai.workflow_builder", "AI Workflow Builder (Claude)", "ai", ["ai_power_tools"], [], ["/admin/ai-workflow"]),
    _feat("ai.workflows_legacy", "Workflow Builder (legacy)", "ai", ["ai_power_tools"], [], ["/admin/workflows"]),
    _feat("ai.ai_intelligence", "AI Intelligence", "ai", ["ai_power_tools"], [], []),
    _feat("ai.ai_proposal", "AI Proposal Generator", "ai", ["ai_power_tools"], [], []),
    _feat("ai.ai_verification", "AI Verification", "ai", ["ai_power_tools"], [], []),
    _feat("ai.doc_extraction", "Document Extraction (OCR)", "ai", ["ai_power_tools"], [], []),
    _feat("ai.intelligence_engine", "Intelligence Engine", "ai", ["ai_power_tools"], [], ["/admin/audit-insights"]),

    # ───── Category 13: System & Admin Elevation (10) ─────
    _feat("admin.dashboard", "Admin Dashboard", "admin_system", ["admin_elevation"], [], ["/admin"]),
    _feat("admin.user_management", "User Management (CRUD)", "admin_system", ["admin_elevation"], ["user.view.all", "user.create.any", "user.update.any"], []),
    _feat("admin.rbac_packs_management", "RBAC Capability Packs Management", "admin_system", ["admin_elevation"], ["system.update.any"], []),
    _feat("admin.rbac_audit_log", "RBAC Audit Log", "admin_system", ["admin_elevation"], [], []),
    _feat("admin.activity_log", "Activity Log", "admin_system", ["admin_elevation"], [], ["/admin/activity"]),
    _feat("admin.analytics_dashboard", "Analytics Dashboard", "admin_system", ["admin_elevation", "accounts"], [], ["/admin/analytics", "/admin/funnel-dashboard"]),
    _feat("admin.cockpit", "Cockpit (Real-time KPIs)", "admin_system", ["admin_elevation"], [], ["/admin/cockpit"]),
    _feat("admin.bulk_operations", "Bulk Operations", "admin_system", ["admin_elevation"], [], []),
    _feat("admin.protection_policies_admin", "Protection Policies Admin", "admin_system", ["admin_elevation"], [], ["/admin/protection-policies"]),
    _feat("admin.system_settings", "System Settings", "admin_system", ["admin_elevation"], ["system.update.any"], []),

    # ───── Category 14: Communication (non-baseline triage) (2) ─────
    _feat("comms.tickets_triage", "Tickets Triage (all depts)", "communication", ["hr", "it", "manager_elevation", "admin_elevation"], [], ["/admin/tickets"]),
    _feat("comms.chat_admin_groups", "Chat — Admin Group Management", "communication", ["admin_elevation"], [], []),
]


# ════════════════════════════════════════════════════════════════════
# Smart defaults: dept → pack list mapping
# ════════════════════════════════════════════════════════════════════

DEPT_TO_PACKS: Dict[str, List[str]] = {
    "marketing": ["baseline_employee", "marketing"],
    "it": ["baseline_employee", "it"],
    "accounts": ["baseline_employee", "accounts"],
    "finance": ["baseline_employee", "accounts"],
    "hr": ["baseline_employee", "hr"],
    "operations": ["baseline_employee", "operations"],
    "sales": ["baseline_employee", "operations"],
    "case_management": ["baseline_employee", "operations"],
    "admin": ["baseline_employee", "admin_elevation", "manager_elevation", "operations"],
}


# ════════════════════════════════════════════════════════════════════
# Legacy role → pack mapping for migration
# ════════════════════════════════════════════════════════════════════

LEGACY_ROLE_TO_PACKS: Dict[str, List[str]] = {
    "admin_owner": [p["pack_id"] for p in CAPABILITY_PACKS],  # ALL 9 packs — god-mode
    "admin": ["baseline_employee", "admin_elevation", "manager_elevation", "operations"],
    "hr_head": ["baseline_employee", "hr", "manager_elevation"],
    "hr": ["baseline_employee", "hr"],
    "marketing_head": ["baseline_employee", "marketing", "manager_elevation"],
    "marketing": ["baseline_employee", "marketing"],
    "it_head": ["baseline_employee", "it", "manager_elevation"],
    "it": ["baseline_employee", "it"],
    "accounts_head": ["baseline_employee", "accounts", "manager_elevation"],
    "accounts": ["baseline_employee", "accounts"],
    "finance": ["baseline_employee", "accounts"],
    "operations_head": ["baseline_employee", "operations", "manager_elevation"],
    "operations": ["baseline_employee", "operations"],
    "case_manager": ["baseline_employee", "operations"],
    "case_manager_lead": ["baseline_employee", "operations", "manager_elevation"],
    "sales": ["baseline_employee", "operations"],
    "sales_manager": ["baseline_employee", "operations", "manager_elevation"],
    "partner": ["baseline_employee", "operations"],
    "staff": ["baseline_employee"],
    "employee": ["baseline_employee"],
}


def features_by_pack(pack_id: str) -> List[str]:
    """All feature_ids whose default_packs include this pack."""
    return [f["feature_id"] for f in FEATURE_CATALOG if pack_id in f["default_packs"]]


def packs_to_feature_ids(packs: List[str]) -> set:
    """Compute ∪(features) for given pack list."""
    out: set = set()
    for p in packs or []:
        out.update(features_by_pack(p))
    return out
