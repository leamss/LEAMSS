"""RBAC Seed Data — Departments, Permissions, Roles

This module defines the static catalog that gets seeded into MongoDB.
All entries are marked is_system=True so they cannot be deleted via admin UI.
"""

# ────────────────────────────────────────────────────────────
# 8 DEPARTMENTS
# ────────────────────────────────────────────────────────────
DEPARTMENTS = [
    {"key": "admin", "name": "Administration", "icon": "Shield", "color": "#7c3aed",
     "description": "Owners, founders, compliance officers"},
    {"key": "sales", "name": "Sales", "icon": "TrendingUp", "color": "#16a34a",
     "description": "Sales executives, managers, and external partners"},
    {"key": "marketing", "name": "Marketing", "icon": "Megaphone", "color": "#ea580c",
     "description": "Campaigns, content, brand"},
    {"key": "operations", "name": "Operations", "icon": "Briefcase", "color": "#0891b2",
     "description": "Case managers, doc verifiers, ops execution"},
    {"key": "hr", "name": "Human Resources", "icon": "Users", "color": "#db2777",
     "description": "People, attendance, leave, payroll"},
    {"key": "accounts", "name": "Accounts & Finance", "icon": "Receipt", "color": "#0d9488",
     "description": "Invoices, refunds, GST, vendor mgmt"},
    {"key": "it", "name": "IT & Systems", "icon": "Server", "color": "#475569",
     "description": "Access mgmt, system config, support"},
    {"key": "compliance", "name": "Compliance & Legal", "icon": "ScrollText", "color": "#b91c1c",
     "description": "Audit, legal archive, regulatory"},
]


# ────────────────────────────────────────────────────────────
# PERMISSION CATALOG (~150 permissions)
# Format: (key, resource, action, scope, display_name, category, risk_level, requires_2fa, audit_required)
# ────────────────────────────────────────────────────────────
def _p(resource, action, scope, display, category, risk="low", twofa=False, audit=False):
    return {
        "key": f"{resource}.{action}.{scope}",
        "resource": resource,
        "action": action,
        "scope": scope,
        "display_name": display,
        "description": f"{action.title()} {resource} ({scope} scope)",
        "category": category,
        "risk_level": risk,
        "requires_2fa": twofa,
        "audit_log_required": audit,
    }


PERMISSIONS = [
    # ───── Wildcard ─────
    {"key": "*", "resource": "*", "action": "*", "scope": "all",
     "display_name": "All Permissions (Owner)", "description": "Full system access",
     "category": "system", "risk_level": "critical", "requires_2fa": True, "audit_log_required": True},

    # ───── Pre-Assessment (PA) ─────
    _p("pa", "view", "own", "View Own PAs", "pa"),
    _p("pa", "view", "team", "View Team PAs", "pa"),
    _p("pa", "view", "dept", "View Dept PAs", "pa"),
    _p("pa", "view", "all", "View All PAs", "pa", "medium"),
    _p("pa", "create", "own", "Create PA", "pa"),
    _p("pa", "update", "own", "Update Own PA", "pa"),
    _p("pa", "update", "team", "Update Team PA", "pa", "medium"),
    _p("pa", "update", "all", "Update Any PA", "pa", "high", audit=True),
    _p("pa", "delete", "own", "Delete Own PA", "pa", "medium", audit=True),
    _p("pa", "delete", "all", "Delete Any PA", "pa", "high", twofa=True, audit=True),
    _p("pa", "approve", "l1", "1st Approval", "pa", "high", audit=True),
    _p("pa", "approve", "l2", "2nd Approval (Activate Case)", "pa", "critical", twofa=True, audit=True),
    _p("pa", "approve", "final", "Final Approval", "pa", "critical", twofa=True, audit=True),
    _p("pa", "assign", "team", "Assign PA Within Team", "pa", "medium"),
    _p("pa", "assign", "all", "Assign Any PA", "pa", "high"),
    _p("pa", "share", "own", "Share Own PA Link", "pa"),
    _p("pa", "share", "all", "Share Any PA Link", "pa", "medium"),
    _p("pa", "review", "team", "Review Team PA", "pa"),
    _p("pa", "review", "all", "Review Any PA", "pa", "medium"),

    # ───── Case ─────
    _p("case", "view", "own", "View Own Cases", "case"),
    _p("case", "view", "team", "View Team Cases", "case"),
    _p("case", "view", "dept", "View Dept Cases", "case"),
    _p("case", "view", "all", "View All Cases", "case", "medium"),
    _p("case", "create", "any", "Create Case", "case", "high", audit=True),
    _p("case", "update", "own", "Update Own Case", "case"),
    _p("case", "update", "team", "Update Team Case", "case", "medium"),
    _p("case", "update", "all", "Update Any Case", "case", "high", audit=True),
    _p("case", "assign", "any", "Assign Case Manager", "case", "high", audit=True),
    _p("case", "terminate", "any", "Terminate Case", "case", "critical", twofa=True, audit=True),
    _p("case", "finalize", "any", "Finalize Case", "case", "high", audit=True),

    # ───── Lead ─────
    _p("lead", "view", "own", "View Own Leads", "lead"),
    _p("lead", "view", "team", "View Team Leads", "lead"),
    _p("lead", "view", "pool", "View Lead Pool", "lead"),
    _p("lead", "view", "all", "View All Leads", "lead", "medium"),
    _p("lead", "create", "any", "Create Lead", "lead"),
    _p("lead", "update", "own", "Update Own Lead", "lead"),
    _p("lead", "update", "team", "Update Team Lead", "lead", "medium"),
    _p("lead", "claim", "pool", "Claim Lead from Pool", "lead"),
    _p("lead", "assign", "any", "Assign Lead to Rep", "lead", "medium"),
    _p("lead", "delete", "any", "Delete Lead", "lead", "medium", audit=True),

    # ───── Invoice ─────
    _p("invoice", "view", "own", "View Own Invoices", "invoice"),
    _p("invoice", "view", "team", "View Team Invoices", "invoice"),
    _p("invoice", "view", "all", "View All Invoices", "invoice", "medium"),
    _p("invoice", "generate", "own", "Generate Own Invoice", "invoice"),
    _p("invoice", "generate", "any", "Generate Any Invoice", "invoice", "medium"),
    _p("invoice", "send", "own", "Send Own Invoice", "invoice"),
    _p("invoice", "send", "any", "Send Any Invoice", "invoice", "medium", audit=True),
    _p("invoice", "update", "any", "Edit Invoice", "invoice", "high", audit=True),
    _p("invoice", "delete", "any", "Delete Invoice", "invoice", "critical", twofa=True, audit=True),

    # ───── Employee ─────
    _p("employee", "view", "own", "View Own Profile", "employee"),
    _p("employee", "view", "team", "View Team Profiles", "employee"),
    _p("employee", "view", "dept", "View Dept Profiles", "employee"),
    _p("employee", "view", "all", "View All Employees", "employee", "medium"),
    _p("employee", "create", "any", "Create Employee", "employee", "high", audit=True),
    _p("employee", "update", "own", "Update Own Profile", "employee"),
    _p("employee", "update", "team", "Update Team Employee", "employee", "medium"),
    _p("employee", "update", "dept", "Update Dept Employee", "employee", "high"),
    _p("employee", "update", "all", "Update Any Employee", "employee", "high", audit=True),
    _p("employee", "delete", "any", "Delete Employee", "employee", "critical", twofa=True, audit=True),
    _p("employee", "terminate", "any", "Terminate Employee", "employee", "critical", twofa=True, audit=True),

    # ───── Attendance ─────
    _p("attendance", "view", "own", "View Own Attendance", "attendance"),
    _p("attendance", "view", "team", "View Team Attendance", "attendance"),
    _p("attendance", "view", "dept", "View Dept Attendance", "attendance"),
    _p("attendance", "view", "all", "View All Attendance", "attendance", "medium"),
    _p("attendance", "clock", "own", "Clock In/Out", "attendance"),
    _p("attendance", "update", "team", "Edit Team Attendance", "attendance", "medium", audit=True),
    _p("attendance", "update", "all", "Edit Any Attendance", "attendance", "high", audit=True),
    _p("attendance", "export", "all", "Export Attendance", "attendance", "medium"),

    # ───── Leave ─────
    _p("leave", "view", "own", "View Own Leave", "leave"),
    _p("leave", "view", "team", "View Team Leave", "leave"),
    _p("leave", "view", "dept", "View Dept Leave", "leave"),
    _p("leave", "view", "all", "View All Leave", "leave"),
    _p("leave", "apply", "own", "Apply for Leave", "leave"),
    _p("leave", "approve", "l1", "Leave Approval L1", "leave", "medium"),
    _p("leave", "approve", "l2", "Leave Approval L2", "leave", "medium"),
    _p("leave", "approve", "final", "Final Leave Approval", "leave", "high", audit=True),

    # ───── Commission ─────
    _p("commission", "view", "own", "View Own Commission", "commission"),
    _p("commission", "view", "team", "View Team Commission", "commission"),
    _p("commission", "view", "all", "View All Commissions", "commission", "medium"),
    _p("commission", "payout", "any", "Pay Out Commission", "commission", "critical", twofa=True, audit=True),
    _p("commission", "update", "any", "Adjust Commission", "commission", "high", audit=True),

    # ───── Campaign ─────
    _p("campaign", "view", "own", "View Own Campaigns", "campaign"),
    _p("campaign", "view", "all", "View All Campaigns", "campaign"),
    _p("campaign", "create", "any", "Create Campaign", "campaign"),
    _p("campaign", "update", "own", "Update Own Campaign", "campaign"),
    _p("campaign", "update", "all", "Update Any Campaign", "campaign", "medium"),
    _p("campaign", "delete", "any", "Delete Campaign", "campaign", "medium", audit=True),

    # ───── Content ─────
    _p("content", "view", "all", "View Content Library", "content"),
    _p("content", "create", "any", "Create Content", "content"),
    _p("content", "update", "any", "Update Content", "content"),
    _p("content", "delete", "any", "Delete Content", "content", "medium", audit=True),

    # ───── Email Campaign ─────
    _p("email_campaign", "view", "own", "View Own Emails", "email_campaign"),
    _p("email_campaign", "view", "all", "View All Emails", "email_campaign"),
    _p("email_campaign", "create", "any", "Draft Email Campaign", "email_campaign"),
    _p("email_campaign", "send", "any", "Send Email Campaign", "email_campaign", "high", audit=True),

    # ───── Client ─────
    _p("client", "view", "own", "View Own Clients", "client"),
    _p("client", "view", "team", "View Team Clients", "client"),
    _p("client", "view", "all", "View All Clients", "client", "medium"),

    # ───── Proposal ─────
    _p("proposal", "view", "own", "View Own Proposals", "proposal"),
    _p("proposal", "view", "all", "View All Proposals", "proposal", "medium"),
    _p("proposal", "generate", "own", "Generate Own Proposal", "proposal"),
    _p("proposal", "generate", "any", "Generate Any Proposal", "proposal", "medium"),
    _p("proposal", "send", "own", "Send Own Proposal", "proposal"),
    _p("proposal", "send", "any", "Send Any Proposal", "proposal", "medium", audit=True),

    # ───── Agreement ─────
    _p("agreement", "view", "own", "View Own Agreement", "agreement"),
    _p("agreement", "view", "all", "View All Agreements", "agreement", "medium"),
    _p("agreement", "generate", "own", "Generate Own Agreement", "agreement"),
    _p("agreement", "generate", "any", "Generate Any Agreement", "agreement", "medium"),
    _p("agreement", "sign", "own", "Sign Own Agreement", "agreement", "medium", audit=True),

    # ───── Agreement Templates ─────
    _p("agreement_template", "view", "all", "View Templates", "agreement_template"),
    _p("agreement_template", "create", "any", "Create Template", "agreement_template", "high", audit=True),
    _p("agreement_template", "update", "any", "Update Template", "agreement_template", "high", audit=True),
    _p("agreement_template", "delete", "any", "Delete Template", "agreement_template", "critical", twofa=True, audit=True),

    # ───── Doc Verification ─────
    _p("doc_verification", "view", "all", "View Doc Verification Queue", "doc_verification"),
    _p("doc_verification", "do", "any", "Verify Documents", "doc_verification", "medium", audit=True),
    _p("doc_verification", "review", "any", "Review Verified Docs", "doc_verification", "medium"),

    # ───── Legal Archive ─────
    _p("legal_archive", "view", "all", "View Legal Archive", "legal_archive", "high", audit=True),
    _p("legal_archive", "export", "all", "Export Legal Archive", "legal_archive", "critical", twofa=True, audit=True),

    # ───── Audit Log ─────
    _p("audit_log", "view", "own", "View Own Audit Log", "audit"),
    _p("audit_log", "view", "all", "View All Audit Logs", "audit", "high"),
    _p("audit_log", "export", "all", "Export Audit Logs", "audit", "critical", twofa=True, audit=True),

    # ───── Activity Log ─────
    _p("activity_log", "view", "own", "View Own Activity", "audit"),
    _p("activity_log", "view", "team", "View Team Activity", "audit"),
    _p("activity_log", "view", "all", "View All Activity", "audit", "medium"),

    # ───── Compliance Report ─────
    _p("compliance_report", "view", "all", "View Compliance Reports", "compliance"),
    _p("compliance_report", "generate", "any", "Generate Compliance Report", "compliance", "high", audit=True),
    _p("compliance_report", "export", "all", "Export Compliance Report", "compliance", "critical", twofa=True, audit=True),

    # ───── Team ─────
    _p("team", "view", "own", "View Own Team", "team"),
    _p("team", "view", "dept", "View Dept Teams", "team"),
    _p("team", "view", "all", "View All Teams", "team"),
    _p("team", "create", "any", "Create Team", "team", "medium"),
    _p("team", "update", "own", "Manage Own Team", "team"),
    _p("team", "update", "dept", "Manage Dept Teams", "team", "medium"),
    _p("team", "update", "all", "Manage Any Team", "team", "high"),
    _p("team", "delete", "any", "Delete Team", "team", "high", audit=True),

    # ───── Target ─────
    _p("target", "view", "own", "View Own Targets", "target"),
    _p("target", "view", "team", "View Team Targets", "target"),
    _p("target", "view", "dept", "View Dept Targets", "target"),
    _p("target", "view", "all", "View All Targets", "target"),
    _p("target", "create", "any", "Set Targets", "target", "medium"),
    _p("target", "update", "team", "Update Team Targets", "target", "medium"),
    _p("target", "update", "all", "Update Any Target", "target", "high"),

    # ───── Incentive ─────
    _p("incentive", "view", "own", "View Own Incentive", "incentive"),
    _p("incentive", "view", "team", "View Team Incentive", "incentive"),
    _p("incentive", "view", "all", "View All Incentives", "incentive", "medium"),
    _p("incentive", "update", "any", "Configure Incentives", "incentive", "high", audit=True),
    _p("incentive", "payout", "any", "Pay Out Incentive", "incentive", "critical", twofa=True, audit=True),

    # ───── Discount ─────
    _p("discount", "view", "own", "View Own Discounts", "discount"),
    _p("discount", "view", "all", "View All Discounts", "discount"),
    _p("discount", "apply", "own", "Apply Discount", "discount"),
    _p("discount", "approve", "low", "Approve Low Discount (≤10%)", "discount", "medium"),
    _p("discount", "approve", "medium", "Approve Medium Discount (≤25%)", "discount", "high", audit=True),
    _p("discount", "approve", "high", "Approve High Discount", "discount", "critical", twofa=True, audit=True),

    # ───── Refund ─────
    _p("refund", "view", "own", "View Own Refunds", "refund"),
    _p("refund", "view", "all", "View All Refunds", "refund", "medium"),
    _p("refund", "create", "any", "Initiate Refund", "refund", "high", audit=True),
    _p("refund", "approve", "any", "Approve Refund", "refund", "critical", twofa=True, audit=True),

    # ───── GST / Vendor / Expense ─────
    _p("gst", "view", "all", "View GST Records", "finance", "medium"),
    _p("gst", "file", "any", "File GST Return", "finance", "critical", twofa=True, audit=True),

    _p("vendor", "view", "all", "View Vendors", "finance"),
    _p("vendor", "create", "any", "Add Vendor", "finance", "medium", audit=True),
    _p("vendor", "update", "any", "Edit Vendor", "finance", "medium"),
    _p("vendor", "delete", "any", "Remove Vendor", "finance", "high", audit=True),

    _p("expense", "view", "own", "View Own Expenses", "finance"),
    _p("expense", "view", "team", "View Team Expenses", "finance"),
    _p("expense", "view", "all", "View All Expenses", "finance"),
    _p("expense", "create", "own", "File Expense", "finance"),
    _p("expense", "approve", "low", "Approve Low Expense (<₹10k)", "finance"),
    _p("expense", "approve", "medium", "Approve Medium Expense", "finance", "medium"),
    _p("expense", "approve", "high", "Approve High Expense", "finance", "high", audit=True),

    # ───── Salary / Onboarding / Offboarding / Performance / Training ─────
    _p("salary_structure", "view", "own", "View Own Salary", "hr", "medium"),
    _p("salary_structure", "view", "team", "View Team Salary", "hr", "high"),
    _p("salary_structure", "view", "all", "View All Salaries", "hr", "high", audit=True),
    _p("salary_structure", "update", "any", "Update Salary Structure", "hr", "critical", twofa=True, audit=True),

    _p("onboarding", "view", "all", "View Onboarding Queue", "hr"),
    _p("onboarding", "do", "any", "Onboard Employee", "hr", "medium", audit=True),

    _p("offboarding", "view", "all", "View Offboarding Queue", "hr"),
    _p("offboarding", "do", "any", "Offboard Employee", "hr", "high", audit=True),

    _p("performance_review", "view", "own", "View Own Review", "hr"),
    _p("performance_review", "view", "team", "View Team Reviews", "hr", "medium"),
    _p("performance_review", "view", "all", "View All Reviews", "hr", "high"),
    _p("performance_review", "do", "team", "Conduct Team Review", "hr", "medium"),
    _p("performance_review", "do", "any", "Conduct Any Review", "hr", "high"),

    _p("training", "view", "own", "View Own Training", "hr"),
    _p("training", "view", "all", "View All Trainings", "hr"),
    _p("training", "assign", "any", "Assign Training", "hr", "medium"),
    _p("training", "update", "any", "Manage Training", "hr"),

    # ───── Public Page / User / System / API Key / Backup / Asset ─────
    _p("public_page", "view", "all", "View Public Pages", "system"),
    _p("public_page", "update", "any", "Edit Public Pages", "system", "medium", audit=True),

    _p("user", "view", "all", "View All Users", "user", "medium"),
    _p("user", "create", "any", "Create User", "user", "high", audit=True),
    _p("user", "update", "any", "Update User", "user", "high", audit=True),
    _p("user", "delete", "any", "Delete User", "user", "critical", twofa=True, audit=True),

    _p("system", "view", "all", "View System Config", "system", "medium"),
    _p("system", "update", "any", "Update System Config", "system", "critical", twofa=True, audit=True),

    _p("api_key", "view", "all", "View API Keys", "system", "high"),
    _p("api_key", "create", "any", "Create API Key", "system", "critical", twofa=True, audit=True),
    _p("api_key", "rotate", "any", "Rotate API Key", "system", "critical", twofa=True, audit=True),
    _p("api_key", "delete", "any", "Delete API Key", "system", "critical", twofa=True, audit=True),

    _p("backup", "view", "all", "View Backups", "system", "high"),
    _p("backup", "create", "any", "Create Backup", "system", "high", audit=True),

    _p("asset", "view", "all", "View Assets", "asset"),
    _p("asset", "create", "any", "Add Asset", "asset"),
    _p("asset", "update", "any", "Update Asset", "asset"),
    _p("asset", "delete", "any", "Delete Asset", "asset", "medium", audit=True),
    _p("asset", "assign", "any", "Assign Asset", "asset"),

    # ───── Support Ticket / Security Log / Call Log ─────
    _p("support_ticket", "view", "own", "View Own Tickets", "support"),
    _p("support_ticket", "view", "team", "View Team Tickets", "support"),
    _p("support_ticket", "view", "all", "View All Tickets", "support"),
    _p("support_ticket", "create", "any", "Create Ticket", "support"),
    _p("support_ticket", "resolve", "any", "Resolve Ticket", "support"),

    _p("security_log", "view", "all", "View Security Logs", "system", "high", audit=True),

    _p("call_log", "view", "own", "View Own Calls", "sales"),
    _p("call_log", "view", "team", "View Team Calls", "sales"),
    _p("call_log", "view", "all", "View All Calls", "sales", "medium"),
    _p("call_log", "create", "own", "Log Call", "sales"),

    # ───── Self-service (all internal employees) ─────
    _p("profile", "view", "own", "View Own Profile", "self"),
    _p("profile", "update", "own", "Update Own Profile", "self"),
]


# ────────────────────────────────────────────────────────────
# Common UI modules for all internal employees
# ────────────────────────────────────────────────────────────
SELF_SERVICE_MODULES = ["attendance_self", "leave_self", "profile_self", "notifications", "my_tasks"]

# Self-service permissions auto-granted to every internal role (Phase 3A)
SELF_SERVICE_PERMISSIONS = [
    "attendance.clock.own",
    "attendance.view.own",
    "leave.apply.own",
    "leave.view.own",
    "profile.view.own",
    "profile.update.own",
]


# ────────────────────────────────────────────────────────────
# 16 SYSTEM ROLES
# ────────────────────────────────────────────────────────────
ROLES = [
    # ════════ ADMIN DEPT ════════
    {
        "key": "admin_owner",
        "name": "Admin Owner",
        "user_type": "internal",
        "department": "admin",
        "hierarchy_level": 6,
        "description": "Full system access (wildcard). Founders / owners.",
        "permissions": ["*"],
        "ui_modules": ["everything"],
        "reports_to_roles": [],
        "can_manage_roles": ["*"],
    },
    {
        "key": "compliance_officer",
        "name": "Compliance Officer",
        "user_type": "internal",
        "department": "compliance",
        "hierarchy_level": 4,
        "description": "Legal archive, audit logs, compliance reports access",
        "permissions": [
            "legal_archive.view.all", "legal_archive.export.all",
            "audit_log.view.all", "audit_log.export.all",
            "activity_log.view.all",
            "compliance_report.view.all", "compliance_report.generate.any", "compliance_report.export.all",
            "pa.view.all", "case.view.all",
            "agreement.view.all", "doc_verification.view.all",
            "profile.view.own", "profile.update.own",
        ],
        "ui_modules": ["legal_archive", "audit_log", "compliance_reports", "activity_log"] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["admin_owner"],
        "can_manage_roles": [],
    },

    # ════════ SALES DEPT ════════
    {
        "key": "sales_head",
        "name": "Sales Head",
        "user_type": "internal",
        "department": "sales",
        "hierarchy_level": 4,
        "description": "All sales data, team mgmt, dept targets, high discount approval",
        "permissions": [
            "pa.view.all", "pa.update.all", "pa.assign.all", "pa.review.all",
            "lead.view.all", "lead.assign.any", "lead.create.any", "lead.update.team",
            "client.view.all",
            "proposal.view.all", "proposal.generate.any", "proposal.send.any",
            "commission.view.all", "commission.update.any",
            "team.view.all", "team.create.any", "team.update.dept", "team.update.all",
            "target.view.all", "target.create.any", "target.update.team", "target.update.all",
            "incentive.view.all", "incentive.update.any",
            "discount.view.all", "discount.approve.low", "discount.approve.medium", "discount.approve.high",
            "call_log.view.all",
            "employee.view.dept",
            "leave.view.dept", "leave.approve.l2",
            "attendance.view.dept",
            "activity_log.view.team",
        ],
        "ui_modules": [
            "sales_dashboard", "pa_pipeline_all", "lead_pool", "team_targets",
            "team_incentives", "team_commissions", "discount_inbox",
            "call_logs", "sales_analytics", "team_management",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["admin_owner"],
        "can_manage_roles": ["sales_manager", "sr_sales_executive", "sales_executive"],
    },
    {
        "key": "sales_manager",
        "name": "Sales Manager",
        "user_type": "internal",
        "department": "sales",
        "hierarchy_level": 3,
        "description": "Team PAs, leads, targets, medium discount approval, leave approval L1",
        "permissions": [
            "pa.view.team", "pa.update.team", "pa.assign.team", "pa.review.team", "pa.create.own", "pa.update.own", "pa.view.own",
            "lead.view.team", "lead.assign.any", "lead.create.any", "lead.update.team", "lead.view.pool", "lead.claim.pool",
            "client.view.team",
            "proposal.view.own", "proposal.generate.own", "proposal.send.own",
            "commission.view.team", "commission.view.own",
            "team.view.own", "team.update.own",
            "target.view.team", "target.update.team",
            "incentive.view.team", "incentive.view.own",
            "discount.apply.own", "discount.approve.low", "discount.approve.medium",
            "call_log.view.team", "call_log.create.own",
            "employee.view.team",
            "leave.view.team", "leave.approve.l1",
            "attendance.view.team",
            "activity_log.view.team",
        ],
        "ui_modules": [
            "sales_dashboard", "pa_pipeline_team", "lead_pool", "my_targets",
            "team_targets", "discount_inbox", "call_logs", "team_management",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["sales_head"],
        "can_manage_roles": ["sr_sales_executive", "sales_executive"],
    },
    {
        "key": "sr_sales_executive",
        "name": "Senior Sales Executive",
        "user_type": "internal",
        "department": "sales",
        "hierarchy_level": 2,
        "description": "Senior IC — same permissions as sales_executive plus mentorship visibility",
        "permissions": [
            "pa.view.own", "pa.create.own", "pa.update.own", "pa.share.own", "pa.delete.own",
            "lead.view.own", "lead.view.pool", "lead.claim.pool", "lead.create.any", "lead.update.own",
            "client.view.own",
            "proposal.view.own", "proposal.generate.own", "proposal.send.own",
            "commission.view.own", "target.view.own", "incentive.view.own",
            "discount.apply.own",
            "call_log.view.own", "call_log.create.own",
        ],
        "ui_modules": [
            "sales_dashboard", "pa_pipeline_own", "lead_pool", "my_targets",
            "my_incentives", "my_commissions", "call_log", "leaderboard",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["sales_manager"],
        "can_manage_roles": [],
    },
    {
        "key": "sales_executive",
        "name": "Sales Executive",
        "user_type": "internal",
        "department": "sales",
        "hierarchy_level": 1,
        "description": "Own PAs, lead pool claim, targets, incentives, attendance self",
        "permissions": [
            "pa.view.own", "pa.create.own", "pa.update.own", "pa.share.own",
            "lead.view.own", "lead.view.pool", "lead.claim.pool", "lead.create.any", "lead.update.own",
            "client.view.own",
            "proposal.view.own", "proposal.generate.own", "proposal.send.own",
            "commission.view.own", "target.view.own", "incentive.view.own",
            "discount.apply.own",
            "call_log.view.own", "call_log.create.own",
        ],
        "ui_modules": [
            "sales_dashboard", "pa_pipeline_own", "lead_pool", "my_targets",
            "my_incentives", "my_commissions", "call_log", "leaderboard",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["sales_manager"],
        "can_manage_roles": [],
    },
    {
        "key": "partner",
        "name": "External Partner",
        "user_type": "external",
        "department": "sales",
        "hierarchy_level": 0,
        "description": "External partner — own PAs, own commission, no team views",
        "permissions": [
            "pa.view.own", "pa.create.own", "pa.update.own", "pa.share.own",
            "lead.view.own", "lead.create.any", "lead.update.own",
            "client.view.own",
            "proposal.view.own", "proposal.generate.own", "proposal.send.own",
            "agreement.view.own", "agreement.generate.own",
            "invoice.view.own",
            "commission.view.own",
            "discount.apply.own",
            "profile.view.own", "profile.update.own",
        ],
        "ui_modules": [
            "partner_home", "pa_pipeline_own", "my_clients", "my_commissions",
            "agreement_view", "fee_calculator",
        ],
        "reports_to_roles": ["sales_head"],
        "can_manage_roles": [],
    },

    # ════════ MARKETING DEPT ════════
    {
        "key": "marketing_head",
        "name": "Marketing Head",
        "user_type": "internal",
        "department": "marketing",
        "hierarchy_level": 4,
        "description": "All campaigns, budgets, marketing analytics",
        "permissions": [
            "campaign.view.all", "campaign.create.any", "campaign.update.all", "campaign.delete.any",
            "content.view.all", "content.create.any", "content.update.any", "content.delete.any",
            "email_campaign.view.all", "email_campaign.create.any", "email_campaign.send.any",
            "public_page.view.all", "public_page.update.any",
            "lead.view.all", "lead.assign.any",
            "employee.view.dept", "leave.view.dept", "leave.approve.l2", "attendance.view.dept",
            "team.view.dept", "team.update.dept",
            "target.view.dept",
        ],
        "ui_modules": [
            "marketing_dashboard", "campaigns_all", "content_library",
            "email_campaigns_all", "public_pages", "lead_analytics", "team_management",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["admin_owner"],
        "can_manage_roles": ["marketing_executive"],
    },
    {
        "key": "marketing_executive",
        "name": "Marketing Executive",
        "user_type": "internal",
        "department": "marketing",
        "hierarchy_level": 1,
        "description": "Own campaigns, content calendar, email marketing drafts",
        "permissions": [
            "campaign.view.own", "campaign.create.any", "campaign.update.own",
            "content.view.all", "content.create.any", "content.update.any",
            "email_campaign.view.own", "email_campaign.create.any",
            "public_page.view.all",
            "lead.view.team",
        ],
        "ui_modules": [
            "marketing_dashboard", "my_campaigns", "content_calendar",
            "email_drafts", "public_pages_view",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["marketing_head"],
        "can_manage_roles": [],
    },

    # ════════ OPERATIONS DEPT ════════
    {
        "key": "ops_head",
        "name": "Operations Head",
        "user_type": "internal",
        "department": "operations",
        "hierarchy_level": 4,
        "description": "All cases, PA L2 approval, CM workload, doc verification oversight",
        "permissions": [
            "pa.view.all", "pa.update.all", "pa.review.all", "pa.approve.l2", "pa.approve.final", "pa.assign.all",
            "case.view.all", "case.create.any", "case.update.all", "case.assign.any", "case.finalize.any",
            "client.view.all",
            "doc_verification.view.all", "doc_verification.do.any", "doc_verification.review.any",
            "agreement.view.all", "agreement.generate.any",
            "team.view.dept", "team.create.any", "team.update.dept",
            "target.view.dept",
            "employee.view.dept",
            "leave.view.dept", "leave.approve.l2",
            "attendance.view.dept",
            "activity_log.view.all",
        ],
        "ui_modules": [
            "ops_dashboard", "pa_l2_approval", "cases_all", "doc_verification_queue",
            "cm_workload", "team_management",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["admin_owner"],
        "can_manage_roles": ["case_manager", "doc_verifier"],
    },
    {
        "key": "case_manager",
        "name": "Case Manager",
        "user_type": "internal",
        "department": "operations",
        "hierarchy_level": 1,
        "description": "Only assigned cases (preserves existing behavior)",
        "permissions": [
            "case.view.own", "case.update.own", "case.finalize.any",
            "pa.view.own", "pa.review.team",
            "client.view.own",
            "agreement.view.own",
            "doc_verification.view.all", "doc_verification.do.any",
            "support_ticket.view.team", "support_ticket.resolve.any",
        ],
        "ui_modules": [
            "cm_dashboard", "my_cases", "doc_verification_queue",
            "support_tickets",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["ops_head"],
        "can_manage_roles": [],
    },
    {
        "key": "doc_verifier",
        "name": "Document Verifier",
        "user_type": "internal",
        "department": "operations",
        "hierarchy_level": 1,
        "description": "Uploaded docs verification queue + AI OCR review",
        "permissions": [
            "doc_verification.view.all", "doc_verification.do.any", "doc_verification.review.any",
            "pa.view.all",
            "case.view.all",
        ],
        "ui_modules": ["doc_verification_queue", "ocr_review"] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["ops_head"],
        "can_manage_roles": [],
    },

    # ════════ HR DEPT ════════
    {
        "key": "hr_head",
        "name": "HR Head",
        "user_type": "internal",
        "department": "hr",
        "hierarchy_level": 4,
        "description": "Full employee CRUD, all attendance/leave, payroll oversight, performance, training",
        "permissions": [
            "employee.view.all", "employee.create.any", "employee.update.all", "employee.delete.any", "employee.terminate.any",
            "attendance.view.all", "attendance.update.all", "attendance.export.all",
            "leave.view.all", "leave.approve.l1", "leave.approve.l2", "leave.approve.final",
            "salary_structure.view.all", "salary_structure.update.any",
            "onboarding.view.all", "onboarding.do.any",
            "offboarding.view.all", "offboarding.do.any",
            "performance_review.view.all", "performance_review.do.any",
            "training.view.all", "training.assign.any", "training.update.any",
            "team.view.all",
            "user.view.all", "user.update.any",
        ],
        "ui_modules": [
            "hr_dashboard", "employee_directory", "attendance_admin",
            "leave_admin", "payroll", "onboarding", "offboarding",
            "performance_cycles", "training_mgmt",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["admin_owner"],
        "can_manage_roles": ["hr_executive"],
    },
    {
        "key": "hr_executive",
        "name": "HR Executive",
        "user_type": "internal",
        "department": "hr",
        "hierarchy_level": 1,
        "description": "Employee view, attendance view, leave approval L1, onboarding execute, training assign",
        "permissions": [
            "employee.view.all", "employee.update.own",
            "attendance.view.all",
            "leave.view.all", "leave.approve.l1",
            "onboarding.view.all", "onboarding.do.any",
            "training.view.all", "training.assign.any",
            "team.view.all",
        ],
        "ui_modules": [
            "hr_dashboard", "employee_directory", "attendance_view",
            "leave_approvals", "onboarding", "training_mgmt",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["hr_head"],
        "can_manage_roles": [],
    },

    # ════════ ACCOUNTS DEPT ════════
    {
        "key": "accounts_head",
        "name": "Accounts Head",
        "user_type": "internal",
        "department": "accounts",
        "hierarchy_level": 4,
        "description": "Revenue, all invoices, refunds, commissions, GST, P&L, expense approval high",
        "permissions": [
            "invoice.view.all", "invoice.generate.any", "invoice.send.any", "invoice.update.any", "invoice.delete.any",
            "refund.view.all", "refund.create.any", "refund.approve.any",
            "commission.view.all", "commission.payout.any", "commission.update.any",
            "incentive.view.all", "incentive.payout.any",
            "gst.view.all", "gst.file.any",
            "vendor.view.all", "vendor.create.any", "vendor.update.any", "vendor.delete.any",
            "expense.view.all", "expense.approve.low", "expense.approve.medium", "expense.approve.high",
            "employee.view.dept",
            "leave.view.dept", "leave.approve.l2", "attendance.view.dept",
            "team.view.dept",
        ],
        "ui_modules": [
            "accounts_dashboard", "invoices_all", "refunds", "commissions",
            "gst", "vendors", "expenses", "revenue_pnl",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["admin_owner"],
        "can_manage_roles": ["accounts_executive"],
    },
    {
        "key": "accounts_executive",
        "name": "Accounts Executive",
        "user_type": "internal",
        "department": "accounts",
        "hierarchy_level": 1,
        "description": "Invoice processing, expense approval low, commission view, GST view, vendors",
        "permissions": [
            "invoice.view.all", "invoice.generate.any", "invoice.send.any",
            "commission.view.all",
            "gst.view.all",
            "vendor.view.all", "vendor.update.any",
            "expense.view.team", "expense.create.own", "expense.approve.low",
        ],
        "ui_modules": [
            "accounts_dashboard", "invoices_process", "commissions_view",
            "gst_view", "vendors_view", "expenses_view",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["accounts_head"],
        "can_manage_roles": [],
    },

    # ════════ IT DEPT ════════
    {
        "key": "it_admin",
        "name": "IT Admin",
        "user_type": "internal",
        "department": "it",
        "hierarchy_level": 3,
        "description": "User access mgmt, system config, API keys, asset mgmt, support tickets, security logs",
        "permissions": [
            "user.view.all", "user.create.any", "user.update.any",
            "system.view.all", "system.update.any",
            "api_key.view.all", "api_key.create.any", "api_key.rotate.any", "api_key.delete.any",
            "backup.view.all", "backup.create.any",
            "asset.view.all", "asset.create.any", "asset.update.any", "asset.delete.any", "asset.assign.any",
            "support_ticket.view.all", "support_ticket.resolve.any",
            "security_log.view.all",
            "audit_log.view.all",
            "employee.view.all",
        ],
        "ui_modules": [
            "it_dashboard", "user_access", "system_config", "api_keys",
            "backups", "assets", "support_tickets_admin", "security_logs",
        ] + SELF_SERVICE_MODULES,
        "reports_to_roles": ["admin_owner"],
        "can_manage_roles": [],
    },

    # ════════ CLIENT (Preserve Existing) ════════
    {
        "key": "client",
        "name": "Client",
        "user_type": "client",
        "department": None,
        "hierarchy_level": 0,
        "description": "End user — own PAs only, sign agreements, pay fees",
        "permissions": [
            "pa.view.own",
            "agreement.view.own", "agreement.sign.own",
            "invoice.view.own",
            "support_ticket.view.own", "support_ticket.create.any",
            "profile.view.own", "profile.update.own",
        ],
        "ui_modules": [
            "client_dashboard", "my_pa", "my_agreement", "my_invoices",
            "my_documents", "support_tickets",
        ],
        "reports_to_roles": [],
        "can_manage_roles": [],
    },
]
