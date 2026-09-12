"""Seed script to populate sample/existing website registrations from navratri_registrations."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.website_sync import upsert_website_lead

SAMPLE_REGISTRATIONS = [
    {
        "id": 31,
        "unique_id": "NN242731",
        "full_name": "Pooja Prakash Ghatkar",
        "email": "pgmodel29@gmail.com",
        "mobile": "+919423391355",
        "country_code": "91",
        "mobile_number": "9423391355",
        "dob": "1995-09-09",
        "qualification": "CS",
        "experience": "2 years",
        "gender": "Female",
        "marital_status": "Single",
        "resume_path": "uploads/resumes/1789021243_SRI GODA TURLAPATI CV.pdf",
        "agree": 1,
        "payment_status": "success",
        "payment_mode": "upi",
        "payment_amount": 1.00,
        "razorpay_payment_id": "pay_TaE0YLf6KnSyTI",
        "razorpay_order_id": "order_TaE00jSZjFgla2",
        "paid_at": "2026-09-10 11:21:29",
        "reference": "Facebook",
        "sales_person_name": "rohit",
        "created_at": "2026-09-10 11:20:41",
        "updated_at": "2026-09-10 11:21:29"
    },
    {
        "id": 32,
        "unique_id": "NN242732",
        "full_name": "Jyoti Pandey",
        "email": "jyoti@leamss.com",
        "mobile": "+917900152427",
        "country_code": "91",
        "mobile_number": "7900152427",
        "dob": "1989-07-11",
        "qualification": "BSc CS",
        "experience": "9",
        "gender": "Female",
        "marital_status": "Single",
        "resume_path": "uploads/resumes/1789021243_SRI GODA TURLAPATI CV.pdf",
        "agree": 1,
        "payment_status": "failed",
        "payment_mode": "card",
        "payment_amount": 1.00,
        "razorpay_payment_id": "pay_TaEXnmAc9AQITT",
        "razorpay_order_id": "order_TaEWVxug8DLnay",
        "reference": "Sales Call",
        "sales_person_name": "rohit",
        "created_at": "2026-09-10 11:50:43",
        "updated_at": "2026-09-10 11:53:24"
    },
    {
        "id": 33,
        "unique_id": "NN242733",
        "full_name": "Pranali Patkar",
        "email": "tech@leamss.com",
        "mobile": "+917900152427",
        "country_code": "91",
        "mobile_number": "7900152427",
        "dob": "1994-05-14",
        "qualification": "BSc CS",
        "experience": "9",
        "gender": "Female",
        "marital_status": "Single",
        "resume_path": "uploads/resumes/1789029951_Rohit_Sai_Chakravarthy_CV.pdf",
        "agree": 1,
        "payment_status": "pending",
        "reference": "Facebook",
        "created_at": "2026-09-10 14:15:54",
        "updated_at": "2026-09-10 14:15:54"
    }
]


async def seed():
    print(f"Seeding {len(SAMPLE_REGISTRATIONS)} Navratri registrations into CRM...")
    for reg in SAMPLE_REGISTRATIONS:
        lead, is_new = await upsert_website_lead(reg)
        action = "Created new" if is_new else "Updated existing"
        print(f"  {action} lead: {lead.get('name')} ({lead.get('unique_id')}) - Stage: {lead.get('stage')}")
    print("Done seeding website leads.")


if __name__ == "__main__":
    asyncio.run(seed())
