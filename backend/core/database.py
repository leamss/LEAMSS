"""MongoDB Database Connection"""
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "leamss_portal")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_col = db["users"]
products_col = db["products"]
workflow_steps_col = db["workflow_steps"]
sales_col = db["sales"]
sale_documents_col = db["sale_documents"]
cases_col = db["cases"]
case_steps_col = db["case_steps"]
documents_col = db["documents"]
additional_doc_requests_col = db["additional_doc_requests"]
tickets_col = db["tickets"]
ticket_messages_col = db["ticket_messages"]
notifications_col = db["notifications"]
audit_logs_col = db["audit_logs"]
settings_col = db["settings"]
information_sheets_col = db["information_sheets"]
payment_transactions_col = db["payment_transactions"]
refunds_col = db["refunds"]
partner_product_commissions_col = db["partner_product_commissions"]
chat_messages_col = db["chat_messages"]
chat_conversations_col = db["chat_conversations"]
surveys_col = db["surveys"]
knowledge_base_col = db["knowledge_base"]
case_transfers_col = db["case_transfers"]
appointments_col = db["appointments"]
case_notes_col = db["case_notes"]
canned_responses_col = db["canned_responses"]
referrals_col = db["referrals"]
greetings_col = db["greetings"]
pre_assessments_col = db["pre_assessments"]
pre_assessment_docs_col = db["pre_assessment_documents"]
case_deadlines_col = db["case_deadlines"]
intake_forms_col = db["intake_forms"]

# RBAC Phase 1 — new collections
departments_col = db["departments"]
roles_col = db["roles"]
permissions_col = db["permissions"]
teams_col = db["teams"]
user_role_history_col = db["user_role_history"]
migrations_col = db["migrations"]

# RBAC Phase 3 — Attendance & Leave Management
attendance_settings_col = db["attendance_settings"]
attendance_logs_col = db["attendance_logs"]
leave_types_col = db["leave_types"]
leave_balances_col = db["leave_balances"]
leave_requests_col = db["leave_requests"]
holidays_col = db["holidays"]
late_marks_tracker_col = db["late_marks_tracker"]
leave_balance_history_col = db["leave_balance_history"]
lwp_records_col = db["lwp_records"]
attendance_regularizations_col = db["attendance_regularizations"]

# Phase 4B — Sales Targets Management
sales_targets_col = db["sales_targets"]
target_templates_col = db["target_templates"]

# Phase 4C — Vendor Master & Commission
vendor_categories_col = db["vendor_categories"]
vendors_col = db["vendors"]
cost_structures_col = db["product_cost_structures"]


async def init_db():
    """Create indexes"""
    await users_col.create_index("email", unique=True)
    await sales_col.create_index("partner_id")
    await sales_col.create_index("status")
    await sales_col.create_index("collection_deadline")
    await cases_col.create_index("client_id")
    await cases_col.create_index("case_manager_id")
    await cases_col.create_index("case_id", unique=True)
    await documents_col.create_index("case_id")
    await tickets_col.create_index("created_by")
    await tickets_col.create_index("assigned_to")
    await audit_logs_col.create_index("created_at")
    await notifications_col.create_index("user_id")
    await information_sheets_col.create_index("case_id", unique=True)
    await refunds_col.create_index("sale_id")
    await chat_messages_col.create_index([("conversation_id", 1), ("created_at", 1)])
    await chat_conversations_col.create_index("case_id")
    await surveys_col.create_index("case_id")
    await knowledge_base_col.create_index("category")
    await case_transfers_col.create_index("case_id")
    await appointments_col.create_index([("user_id", 1), ("date", 1)])
    await case_notes_col.create_index("case_id")
    await canned_responses_col.create_index("user_id")
    await referrals_col.create_index("referrer_id")
    await greetings_col.create_index("user_id")
    await pre_assessments_col.create_index("partner_id")
    await pre_assessments_col.create_index("stage")
    await pre_assessments_col.create_index([("partner_id", 1), ("stage", 1)])
    await pre_assessments_col.create_index("updated_at")
    await pre_assessments_col.create_index("client_user_id")
    await pre_assessments_col.create_index("client_email")
    await pre_assessments_col.create_index("case_id")
    # Heavy-read collections touched on every PA expand
    await pre_assessment_docs_col.create_index("pre_assessment_id")
    await db["proposal_consent_emails"].create_index("pre_assessment_id")
    await db["pa_invoices"].create_index("pre_assessment_id")
    await db["pa_nudges"].create_index([("pre_assessment_id", 1), ("sent_at", -1)])
    await db["pa_signatures"].create_index("pre_assessment_id")
    await db["case_milestones"].create_index("case_id")
    await db["case_milestones"].create_index([("case_id", 1), ("status", 1)])
    await db["activity_log"].create_index([("user_id", 1), ("created_at", -1)])
    await db["activity_log"].create_index([("entity_id", 1), ("created_at", -1)])
    await notifications_col.create_index([("user_id", 1), ("read", 1), ("created_at", -1)])
    await case_deadlines_col.create_index("case_id")
    await case_deadlines_col.create_index("due_date")
    await db["partner_product_commissions"].create_index(
        [("partner_id", 1), ("product_id", 1)], unique=True
    )
    print("Database indexes created")
