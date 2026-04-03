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


async def init_db():
    """Create indexes"""
    await users_col.create_index("email", unique=True)
    await sales_col.create_index("partner_id")
    await sales_col.create_index("status")
    await cases_col.create_index("client_id")
    await cases_col.create_index("case_manager_id")
    await cases_col.create_index("case_id", unique=True)
    await documents_col.create_index("case_id")
    await tickets_col.create_index("created_by")
    await audit_logs_col.create_index("created_at")
    await notifications_col.create_index("user_id")
    await information_sheets_col.create_index("case_id", unique=True)
    print("Database indexes created")
