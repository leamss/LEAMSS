"""One-shot script to delete all test pre-assessments, cases, sales, documents, and activity.
Preserves: users (admin/partner/cm/client), products, workflows, fee_database, promo_codes, upsell_bundles.
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

COLLECTIONS_TO_CLEAR = [
    "pre_assessments",
    "pre_assessment_documents",
    "pre_assess_activity",
    "sales",
    "cases",
    "case_steps",
    "documents",
    "additional_documents",
    "magic_links",
    "notifications",
    "commissions",
    "payments",
    "proposals",
    "messages",
    "tickets",
    "ticket_messages",
    "case_transfers",
    "activity_logs",
    "refunds",
    "intake_form_submissions",
    "survey_responses",
    "client_profiles",
    "case_timeline",
    "deadlines",
]


async def main():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    totals = {}
    for name in COLLECTIONS_TO_CLEAR:
        col = db[name]
        count = await col.count_documents({})
        if count > 0:
            result = await col.delete_many({})
            totals[name] = result.deleted_count

    # Also delete auto-created client users (retain only seeded admins + fixed test accounts)
    users_col = db["users"]
    keep_emails = [
        "admin@leamss.com", "partner@leamss.com", "manager@leamss.com",
        "client@leamss.com", "tanvi@leamss.com",
    ]
    deleted_clients = await users_col.delete_many({
        "role": "client",
        "email": {"$nin": keep_emails},
    })
    totals["users(auto-clients)"] = deleted_clients.deleted_count

    # Delete any partner-created test partners (keep only seeded)
    deleted_partners = await users_col.delete_many({
        "role": "partner",
        "email": {"$nin": keep_emails},
    })
    totals["users(test-partners)"] = deleted_partners.deleted_count

    print("=== CLEANUP SUMMARY ===")
    for k, v in totals.items():
        print(f"  {k}: {v} deleted")
    print(f"\nTotal collections cleared: {len(totals)}")

    # Verification
    remaining_users = await users_col.count_documents({})
    print(f"\n✅ Remaining users (seeded accounts): {remaining_users}")
    pa_remaining = await db["pre_assessments"].count_documents({})
    cases_remaining = await db["cases"].count_documents({})
    sales_remaining = await db["sales"].count_documents({})
    print(f"✅ Pre-assessments: {pa_remaining}, Cases: {cases_remaining}, Sales: {sales_remaining}")


if __name__ == "__main__":
    asyncio.run(main())
