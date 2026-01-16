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
    
    print("Creating demo products...")
    products = [
        {
            "id": str(ObjectId()),
            "name": "Australia PR - Skilled Route 189/190",
            "description": "Skilled independent visa for Australia permanent residency",
            "fee": 5000.00,
            "commission_rate": 15.0,
            "workflow_steps": [
                {"step_name": "Onboarding & KYC", "step_order": 1, "description": "Initial client verification"},
                {"step_name": "Skills Assessment", "step_order": 2, "description": "Professional skills evaluation"},
                {"step_name": "EOI Submission", "step_order": 3, "description": "Expression of Interest filing"},
                {"step_name": "ITA Received", "step_order": 4, "description": "Invitation to Apply"},
                {"step_name": "Visa Documents", "step_order": 5, "description": "Final document preparation"},
                {"step_name": "Visa Lodged", "step_order": 6, "description": "Application submitted"},
                {"step_name": "Decision", "step_order": 7, "description": "Final visa decision"}
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(ObjectId()),
            "name": "Canada Express Entry",
            "description": "Federal skilled worker program for Canada",
            "fee": 4500.00,
            "commission_rate": 12.0,
            "workflow_steps": [
                {"step_name": "Profile Creation", "step_order": 1, "description": "Express Entry profile"},
                {"step_name": "Document Collection", "step_order": 2, "description": "Gather required documents"},
                {"step_name": "ITA Response", "step_order": 3, "description": "Respond to invitation"},
                {"step_name": "Medical & Police", "step_order": 4, "description": "Medical and police clearance"},
                {"step_name": "PR Application", "step_order": 5, "description": "Submit PR application"}
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(ObjectId()),
            "name": "UK Skilled Worker Visa",
            "description": "Tier 2 skilled worker visa for UK",
            "fee": 3500.00,
            "commission_rate": 10.0,
            "workflow_steps": [
                {"step_name": "Job Offer Verification", "step_order": 1, "description": "Verify sponsorship"},
                {"step_name": "Document Preparation", "step_order": 2, "description": "Prepare visa documents"},
                {"step_name": "Application Submission", "step_order": 3, "description": "Submit visa application"},
                {"step_name": "Biometrics", "step_order": 4, "description": "Biometric appointment"}
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
    for step in product["workflow_steps"]:
        case_steps.append({
            "step_name": step["step_name"],
            "step_order": step["step_order"],
            "status": "pending" if step["step_order"] > 1 else "in_progress",
            "notes": ""
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
        "steps": case_steps,
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
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
