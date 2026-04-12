"""LEAMSS Portal - FastAPI Backend with MongoDB"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from core.database import init_db

from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.products import router as products_router
from routers.sales import router as sales_router
from routers.cases import router as cases_router
from routers.documents import router as documents_router
from routers.tickets import router as tickets_router
from routers.notifications import router as notifications_router
from routers.stats import router as stats_router
from routers.activity import router as activity_router
from routers.analytics import router as analytics_router
from routers.search import router as search_router
from routers.reports import router as reports_router
from routers.settings import router as settings_router
from routers.refunds import router as refunds_router
from routers.partner_commissions import router as partner_commissions_router
from routers.pdf_reports import router as pdf_reports_router
from routers.ai_verification import router as ai_router
from routers.workflows import router as workflows_router
from routers.marketing import router as marketing_router
from routers.leads import router as leads_router
from routers.campaigns import router as campaigns_router
from routers.marketing_tools import router as marketing_tools_router
from routers.payments import router as payments_router
from routers.reminders import router as reminders_router
from routers.ai_intelligence import router as ai_intel_router
from routers.ai_workflow_builder import router as ai_workflow_router
from routers.chat import router as chat_router
from routers.surveys import router as surveys_router
from routers.knowledge_base import router as kb_router
from routers.appointments import router as appointments_router
from routers.timeline import router as timeline_router
from routers.case_notes import router as case_notes_router
from routers.canned_responses import router as canned_responses_router
from routers.referrals import router as referrals_router
from routers.greetings import router as greetings_router
from routers.pre_assessment import router as pre_assessment_router
from routers.partner_analytics import router as partner_analytics_router

app = FastAPI(title="LEAMSS Portal API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()
    
    # Auto-seed if database is empty
    from core.database import users_col
    count = await users_col.count_documents({})
    if count == 0:
        print("Database empty, seeding...")
        await seed_database()
        print("Database seeded successfully!")


async def seed_database():
    """Seed the database with initial data"""
    from core.database import users_col, products_col, workflow_steps_col, sales_col, cases_col, case_steps_col, tickets_col, ticket_messages_col
    from core.auth import get_password_hash
    import uuid
    from datetime import datetime, timezone
    
    # Create users
    users = [
        {"id": str(uuid.uuid4()), "email": "admin@leamss.com", "password": get_password_hash("Admin@123"),
         "name": "Admin User", "role": "admin", "mobile": "+1-555-0001", "status": "active", "commission_rate": 0.0, "created_at": datetime.now(timezone.utc)},
        {"id": str(uuid.uuid4()), "email": "manager@leamss.com", "password": get_password_hash("Manager@123"),
         "name": "Case Manager", "role": "case_manager", "mobile": "+1-555-0002", "status": "active", "commission_rate": 0.0, "created_at": datetime.now(timezone.utc)},
        {"id": str(uuid.uuid4()), "email": "partner@leamss.com", "password": get_password_hash("Partner@123"),
         "name": "Partner User", "role": "partner", "mobile": "+1-555-0003", "status": "active", "commission_rate": 10.0, "created_at": datetime.now(timezone.utc)},
        {"id": str(uuid.uuid4()), "email": "client@leamss.com", "password": get_password_hash("Client@123"),
         "name": "Jane Smith", "role": "client", "mobile": "+1-555-0004", "status": "active", "commission_rate": 0.0, "created_at": datetime.now(timezone.utc)},
        {"id": str(uuid.uuid4()), "email": "client2@leamss.com", "password": get_password_hash("Client@123"),
         "name": "Bob Johnson", "role": "client", "mobile": "+1-555-0005", "status": "active", "commission_rate": 0.0, "created_at": datetime.now(timezone.utc)},
    ]
    await users_col.insert_many(users)
    
    admin, manager, partner, client1, client2 = users
    
    # Create products
    products_data = [
        {"name": "Canada PR", "description": "Permanent Residence in Canada", "category": "immigration", "base_fee": 50000},
        {"name": "Student Visa", "description": "Student Visa Processing", "category": "visa", "base_fee": 25000},
        {"name": "Work Permit", "description": "Work Permit Application", "category": "work", "base_fee": 35000},
    ]
    
    steps_data = [
        [
            {"step_name": "Profile Creation", "step_order": 1, "description": "Create client profile", "duration_days": 3, "required_documents": [{"doc_name": "Passport", "is_mandatory": True}, {"doc_name": "Photo", "is_mandatory": True}]},
            {"step_name": "Document Collection", "step_order": 2, "description": "Collect all documents", "duration_days": 14, "required_documents": [{"doc_name": "Education Certs", "is_mandatory": True}, {"doc_name": "Work Experience", "is_mandatory": True}]},
            {"step_name": "IELTS Preparation", "step_order": 3, "description": "Language test preparation", "duration_days": 30, "required_documents": [{"doc_name": "IELTS Score Card", "is_mandatory": True}]},
            {"step_name": "Application Filing", "step_order": 4, "description": "File the application", "duration_days": 7, "required_documents": []},
            {"step_name": "Biometrics", "step_order": 5, "description": "Biometrics appointment", "duration_days": 14, "required_documents": [{"doc_name": "Biometrics Receipt", "is_mandatory": True}]},
            {"step_name": "Medical Exam", "step_order": 6, "description": "Medical examination", "duration_days": 14, "required_documents": [{"doc_name": "Medical Report", "is_mandatory": True}]},
            {"step_name": "Background Check", "step_order": 7, "description": "PCC and background", "duration_days": 30, "required_documents": [{"doc_name": "PCC", "is_mandatory": True}]},
            {"step_name": "Final Review", "step_order": 8, "description": "Final review and decision", "duration_days": 60, "required_documents": []},
        ],
        [
            {"step_name": "Profile Creation", "step_order": 1, "description": "Create student profile", "duration_days": 3, "required_documents": [{"doc_name": "Passport", "is_mandatory": True}]},
            {"step_name": "University Selection", "step_order": 2, "description": "Select universities", "duration_days": 7, "required_documents": [{"doc_name": "Transcripts", "is_mandatory": True}]},
            {"step_name": "Application", "step_order": 3, "description": "Submit applications", "duration_days": 14, "required_documents": [{"doc_name": "SOP", "is_mandatory": True}]},
            {"step_name": "Visa Filing", "step_order": 4, "description": "File visa application", "duration_days": 14, "required_documents": [{"doc_name": "Offer Letter", "is_mandatory": True}]},
        ],
        [
            {"step_name": "Profile Creation", "step_order": 1, "description": "Create work profile", "duration_days": 3, "required_documents": [{"doc_name": "Passport", "is_mandatory": True}]},
            {"step_name": "LMIA Processing", "step_order": 2, "description": "Labour market assessment", "duration_days": 30, "required_documents": [{"doc_name": "Job Offer", "is_mandatory": True}]},
            {"step_name": "Work Permit Filing", "step_order": 3, "description": "File work permit", "duration_days": 14, "required_documents": []},
        ],
    ]
    
    for i, pdata in enumerate(products_data):
        product = {
            "id": str(uuid.uuid4()), **pdata,
            "status": "active", "created_at": datetime.now(timezone.utc)
        }
        await products_col.insert_one(product)
        
        for step in steps_data[i]:
            ws = {"id": str(uuid.uuid4()), "product_id": product["id"], **step}
            await workflow_steps_col.insert_one(ws)
        
        products_data[i]["_product"] = product
    
    # Create sales
    sale1 = {
        "id": str(uuid.uuid4()), "partner_id": partner["id"],
        "client_name": "Jane Smith", "client_email": "client@leamss.com",
        "client_mobile": "+1-555-0004", "product_id": products_data[0]["_product"]["id"],
        "fee_amount": 150000, "amount_received": 75000,
        "payment_method": "bank_transfer", "payment_reference": "TXN-001",
        "commission_rate": 10.0, "commission_amount": 15000,
        "agreement_signed": True, "status": "approved",
        "approved_by": admin["id"], "approved_at": datetime.now(timezone.utc),
        "payment_status": "partial", "created_at": datetime.now(timezone.utc)
    }
    
    sale2 = {
        "id": str(uuid.uuid4()), "partner_id": partner["id"],
        "client_name": "Bob Johnson", "client_email": "client2@leamss.com",
        "client_mobile": "+1-555-0005", "product_id": products_data[1]["_product"]["id"],
        "fee_amount": 75000, "amount_received": 0,
        "payment_method": "cash", "payment_reference": "",
        "commission_rate": 10.0, "commission_amount": 0,
        "agreement_signed": True, "status": "pending",
        "payment_status": "pending", "created_at": datetime.now(timezone.utc)
    }
    await sales_col.insert_many([sale1, sale2])
    
    # Create case for approved sale
    case = {
        "id": str(uuid.uuid4()), "case_id": "LEAMSS-2024-0001",
        "sale_id": sale1["id"], "client_id": client1["id"],
        "product_id": products_data[0]["_product"]["id"],
        "case_manager_id": manager["id"], "partner_id": partner["id"],
        "status": "active", "current_step": "Profile Creation",
        "current_step_order": 1, "created_at": datetime.now(timezone.utc)
    }
    await cases_col.insert_one(case)
    
    # Create case steps
    for step in steps_data[0]:
        cs = {
            "id": str(uuid.uuid4()), "case_id": case["id"],
            "step_name": step["step_name"], "step_order": step["step_order"],
            "status": "pending", "description": step.get("description", ""),
            "required_documents": step.get("required_documents", []),
            "created_at": datetime.now(timezone.utc)
        }
        await case_steps_col.insert_one(cs)
    
    # Create ticket
    ticket = {
        "id": str(uuid.uuid4()), "subject": "Need help with documents",
        "description": "I need guidance on which documents to upload for step 2",
        "priority": "medium", "category": "general", "status": "open",
        "created_by": client1["id"], "created_at": datetime.now(timezone.utc)
    }
    await tickets_col.insert_one(ticket)
    
    await ticket_messages_col.insert_one({
        "id": str(uuid.uuid4()), "ticket_id": ticket["id"],
        "sender_id": client1["id"],
        "message": "Could you please let me know the list of required documents for Document Collection step?",
        "created_at": datetime.now(timezone.utc)
    })
    
    print(f"Seeded: 5 users, 3 products, 2 sales, 1 case, 1 ticket")
    print(f"  Admin: admin@leamss.com / Admin@123")
    print(f"  Manager: manager@leamss.com / Manager@123")
    print(f"  Partner: partner@leamss.com / Partner@123")
    print(f"  Client: client@leamss.com / Client@123")


# Include all routers
for r in [auth_router, users_router, products_router, sales_router, cases_router,
          documents_router, tickets_router, notifications_router, stats_router,
          activity_router, analytics_router, search_router, reports_router, settings_router,
          refunds_router, partner_commissions_router, pdf_reports_router, ai_router,
          workflows_router, marketing_router, leads_router, campaigns_router, marketing_tools_router,
          payments_router, reminders_router, ai_intel_router, ai_workflow_router, chat_router,
          surveys_router, kb_router, appointments_router,
          timeline_router, case_notes_router, canned_responses_router,
          referrals_router, greetings_router, pre_assessment_router,
          partner_analytics_router]:
    app.include_router(r, prefix="/api")


@app.get("/api/health")
async def health():
    from core.database import client as mongo_client
    try:
        await mongo_client.admin.command("ping")
        return {"status": "healthy", "database": "connected", "service": "LEAMSS Portal API v3.0 (MongoDB)"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    import os
    from core.database import db
    payment_transactions_col = db["payment_transactions"]
    
    try:
        body = await request.body()
        stripe_signature = request.headers.get("Stripe-Signature", "")
        
        api_key = os.environ.get("STRIPE_API_KEY")
        if not api_key:
            return {"status": "error", "message": "Stripe not configured"}
        
        from emergentintegrations.payments.stripe.checkout import StripeCheckout
        stripe_checkout = StripeCheckout(api_key=api_key, webhook_url="")
        webhook_response = await stripe_checkout.handle_webhook(body, stripe_signature)
        
        if webhook_response and webhook_response.payment_status == "paid":
            session_id = webhook_response.session_id
            transaction = await payment_transactions_col.find_one({"session_id": session_id, "processed": {"$ne": True}}, {"_id": 0})
            if transaction:
                from routers.payments import _process_successful_payment
                await payment_transactions_col.update_one({"session_id": session_id}, {"$set": {"status": "complete", "payment_status": "paid"}})
                await _process_successful_payment(transaction["sale_id"], transaction["amount"], session_id)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/quick-actions")
async def quick_actions():
    """Quick actions endpoint for frontend"""
    from core.database import sales_col, cases_col, tickets_col
    
    pending_sales = await sales_col.count_documents({"status": "pending"})
    active_cases = await cases_col.count_documents({"status": "active"})
    open_tickets = await tickets_col.count_documents({"status": "open"})
    
    actions = []
    if pending_sales > 0:
        actions.append({
            "type": "pending_sales",
            "title": f"{pending_sales} Pending Sales",
            "description": "Sales awaiting approval",
            "action": "Review Sales"
        })
    if open_tickets > 0:
        actions.append({
            "type": "open_tickets",
            "title": f"{open_tickets} Open Tickets",
            "description": "Support tickets need attention",
            "action": "View Tickets"
        })
    
    return actions


@app.get("/api/scheduler/expiring-documents")
async def get_expiring_documents():
    """Get documents expiring soon"""
    from core.database import documents_col
    from datetime import datetime, timedelta, timezone
    
    # Get documents expiring in next 30 days
    thirty_days = datetime.now(timezone.utc) + timedelta(days=30)
    
    # For now return empty list as we don't have expiry tracking yet
    return {"documents": [], "count": 0}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
