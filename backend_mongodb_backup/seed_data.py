import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timezone
from bson import ObjectId
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_database():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("Clearing existing data...")
    await db.users.delete_many({})
    await db.products.delete_many({})
    await db.sales.delete_many({})
    await db.cases.delete_many({})
    await db.documents.delete_many({})
    await db.notifications.delete_many({})
    await db.tickets.delete_many({})
    
    print("Creating demo users...")
    users = [
        {
            "id": str(ObjectId()),
            "email": "admin@leamss.com",
            "name": "Admin User",
            "role": "admin",
            "mobile": "+1234567890",
            "password": pwd_context.hash("Admin@123"),
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(ObjectId()),
            "email": "manager@leamss.com",
            "name": "Case Manager",
            "role": "case_manager",
            "mobile": "+1234567891",
            "password": pwd_context.hash("Manager@123"),
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(ObjectId()),
            "email": "partner@leamss.com",
            "name": "Partner User",
            "role": "partner",
            "mobile": "+1234567892",
            "password": pwd_context.hash("Partner@123"),
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(ObjectId()),
            "email": "client@leamss.com",
            "name": "Client User",
            "role": "client",
            "mobile": "+1234567893",
            "password": pwd_context.hash("Client@123"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.users.insert_many(users)
    print(f"Created {len(users)} demo users")
    
    print("Creating demo products with detailed workflows...")
    products = [
        {
            "id": str(ObjectId()),
            "name": "Australia PR - Skilled Route 189/190",
            "description": "Skilled independent visa for Australia permanent residency",
            "fee": 5000.00,
            "commission_rate": 15.0,
            "workflow_steps": [
                {
                    "step_name": "Registration",
                    "step_order": 1,
                    "description": "Initial registration and client onboarding",
                    "duration_days": 15,
                    "required_documents": [
                        {"doc_name": "Passport Copy", "description": "Valid passport with minimum 6 months validity", "is_mandatory": True},
                        {"doc_name": "Photo", "description": "Recent passport-sized photograph", "is_mandatory": True},
                        {"doc_name": "Resume/CV", "description": "Detailed work experience", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "Document Collection",
                    "step_order": 2,
                    "description": "Collect all required documents for assessment",
                    "duration_days": 7,
                    "required_documents": [
                        {"doc_name": "Educational Certificates", "description": "All degree certificates and transcripts", "is_mandatory": True},
                        {"doc_name": "Work Experience Letters", "description": "Employment letters from all employers", "is_mandatory": True},
                        {"doc_name": "Salary Slips", "description": "Last 6 months salary slips", "is_mandatory": True},
                        {"doc_name": "Bank Statements", "description": "6 months bank statements", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "Skills Assessment",
                    "step_order": 3,
                    "description": "Professional skills evaluation by assessing authority",
                    "duration_days": 45,
                    "required_documents": [
                        {"doc_name": "Skills Assessment Application", "description": "Completed application form", "is_mandatory": True},
                        {"doc_name": "Reference Letters", "description": "Professional reference letters", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "EOI Submission",
                    "step_order": 4,
                    "description": "Expression of Interest filing",
                    "duration_days": 15,
                    "required_documents": [
                        {"doc_name": "Skills Assessment Letter", "description": "Approved skills assessment", "is_mandatory": True},
                        {"doc_name": "IELTS/PTE Scorecard", "description": "English language test results", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "ITA Received",
                    "step_order": 5,
                    "description": "Invitation to Apply received",
                    "duration_days": 60,
                    "required_documents": []
                },
                {
                    "step_name": "Visa Documents",
                    "step_order": 6,
                    "description": "Final document preparation for visa application",
                    "duration_days": 30,
                    "required_documents": [
                        {"doc_name": "Police Clearance Certificate", "description": "PCC from all countries lived for 12+ months", "is_mandatory": True},
                        {"doc_name": "Medical Certificate", "description": "Health examination results", "is_mandatory": True},
                        {"doc_name": "Form 80", "description": "Character assessment form", "is_mandatory": True},
                        {"doc_name": "Marriage Certificate", "description": "If applicable", "is_mandatory": False}
                    ]
                },
                {
                    "step_name": "Visa Lodged",
                    "step_order": 7,
                    "description": "Visa application submitted to DHA",
                    "duration_days": 20,
                    "required_documents": [
                        {"doc_name": "Payment Receipt", "description": "Visa application fee payment", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "Decision",
                    "step_order": 8,
                    "description": "Final visa decision",
                    "duration_days": 90,
                    "required_documents": []
                }
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(ObjectId()),
            "name": "Canada Study Visa",
            "description": "Study permit for Canadian universities",
            "fee": 3500.00,
            "commission_rate": 12.0,
            "workflow_steps": [
                {
                    "step_name": "Registration",
                    "step_order": 1,
                    "description": "Student registration and intake",
                    "duration_days": 15,
                    "required_documents": [
                        {"doc_name": "Passport", "description": "Valid passport", "is_mandatory": True},
                        {"doc_name": "Academic Transcripts", "description": "All previous education records", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "Document Collection",
                    "step_order": 2,
                    "description": "Gather application documents",
                    "duration_days": 7,
                    "required_documents": [
                        {"doc_name": "SOP", "description": "Statement of Purpose", "is_mandatory": True},
                        {"doc_name": "Financial Documents", "description": "Proof of funds", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "University Application",
                    "step_order": 3,
                    "description": "Apply to Canadian universities",
                    "duration_days": 30,
                    "required_documents": [
                        {"doc_name": "Application Form", "description": "Completed university application", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "Offer Letter",
                    "step_order": 4,
                    "description": "Receive university offer letter",
                    "duration_days": 45,
                    "required_documents": []
                },
                {
                    "step_name": "GIC & Fees",
                    "step_order": 5,
                    "description": "GIC account and fee payment",
                    "duration_days": 15,
                    "required_documents": [
                        {"doc_name": "GIC Certificate", "description": "Guaranteed Investment Certificate", "is_mandatory": True},
                        {"doc_name": "Fee Payment Receipt", "description": "Tuition fee payment proof", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "Medical & Biometrics",
                    "step_order": 6,
                    "description": "Medical exam and biometrics",
                    "duration_days": 20,
                    "required_documents": [
                        {"doc_name": "Medical Report", "description": "Approved medical examination", "is_mandatory": True},
                        {"doc_name": "Biometrics Receipt", "description": "Biometrics submission proof", "is_mandatory": True}
                    ]
                },
                {
                    "step_name": "Visa Application",
                    "step_order": 7,
                    "description": "Submit study permit application",
                    "duration_days": 30,
                    "required_documents": [
                        {"doc_name": "Visa Application Form", "description": "IMM forms completed", "is_mandatory": True}
                    ]
                }
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.products.insert_many(products)
    print(f"Created {len(products)} demo products")
    
    print("Creating demo sale and case...")
    partner = next(u for u in users if u["role"] == "partner")
    case_manager = next(u for u in users if u["role"] == "case_manager")
    client = next(u for u in users if u["role"] == "client")
    product = products[0]
    
    sale_id = str(ObjectId())
    sale = {
        "id": sale_id,
        "partner_id": partner["id"],
        "partner_name": partner["name"],
        "client_name": client["name"],
        "client_email": client["email"],
        "client_mobile": client["mobile"],
        "product_id": product["id"],
        "product_name": product["name"],
        "fee_amount": product["fee"],
        "amount_received": product["fee"],
        "payment_method": "bank_transfer",
        "payment_reference": "TXN123456",
        "status": "approved",
        "commission_rate": product["commission_rate"],
        "commission_amount": product["fee"] * (product["commission_rate"] / 100),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents": []
    }
    
    await db.sales.insert_one(sale)
    print("Created demo sale")
    
    case_steps = []
    for idx, step in enumerate(product["workflow_steps"]):
        case_steps.append({
            "step_name": step["step_name"],
            "step_order": step["step_order"],
            "status": "in_progress" if idx == 0 else "locked",
            "notes": "",
            "uploaded_documents": [],
            "required_documents": step["required_documents"],
            "approved_by": None,
            "approved_at": None,
            "is_locked": False if idx == 0 else True
        })
    
    case = {
        "id": str(ObjectId()),
        "case_id": f"CASE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(ObjectId())[:6].upper()}",
        "client_id": client["id"],
        "client_name": client["name"],
        "client_email": client["email"],
        "product_id": product["id"],
        "product_name": product["name"],
        "case_manager_id": case_manager["id"],
        "case_manager_name": case_manager["name"],
        "partner_id": partner["id"],
        "partner_name": partner["name"],
        "sale_id": sale_id,
        "status": "active",
        "current_step": case_steps[0]["step_name"],
        "current_step_order": 1,
        "steps": case_steps,
        "additional_doc_requests": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.cases.insert_one(case)
    print("Created demo case")
    
    print("\n✅ Database seeded successfully!")
    print("\n📧 Demo Login Credentials:")
    print("Admin: admin@leamss.com / Admin@123")
    print("Case Manager: manager@leamss.com / Manager@123")
    print("Partner: partner@leamss.com / Partner@123")
    print("Client: client@leamss.com / Client@123")

if __name__ == "__main__":
    asyncio.run(seed_database())
