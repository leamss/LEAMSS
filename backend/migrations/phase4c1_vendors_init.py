"""Phase 4C.1 — Vendor Categories Seed + Indexes.

Idempotent: re-running is safe. Seeds the 9 default categories and creates indexes.
"""
import uuid
from datetime import datetime, timezone
from core.database import db

vendor_categories_col = db["vendor_categories"]
vendors_col = db["vendors"]

DEFAULT_CATEGORIES = [
    {"key": "sales_commission",  "name": "Sales Commission",        "description": "Internal sales person commission per closed PA", "icon": "TrendingUp",  "color": "indigo",   "default_payment_type": "percentage",   "is_internal": True,  "linked_role": "sales_executive"},
    {"key": "case_manager",      "name": "Case Manager",            "description": "Internal case manager flat fee per case",         "icon": "UserCog",     "color": "emerald",  "default_payment_type": "flat",         "is_internal": True,  "linked_role": "case_manager"},
    {"key": "tutor",             "name": "Tutor (IELTS/PTE/TOEFL)", "description": "External coach for English language tests",       "icon": "GraduationCap","color": "blue",    "default_payment_type": "flat",         "is_internal": False, "linked_role": None},
    {"key": "lawyer",            "name": "Lawyer",                  "description": "External legal review for visa/case",             "icon": "Scale",       "color": "slate",    "default_payment_type": "flat",         "is_internal": False, "linked_role": None},
    {"key": "translator",        "name": "Translator",              "description": "Per-document language translation",                "icon": "Languages",   "color": "amber",    "default_payment_type": "per_document", "is_internal": False, "linked_role": None},
    {"key": "consultant",        "name": "Consultant",              "description": "Country-specific expert consultation",             "icon": "Briefcase",   "color": "purple",   "default_payment_type": "hourly",       "is_internal": False, "linked_role": None},
    {"key": "medical_examiner",  "name": "Medical Examiner",        "description": "Approved medical exam centre",                     "icon": "Stethoscope", "color": "rose",     "default_payment_type": "flat",         "is_internal": False, "linked_role": None},
    {"key": "courier",           "name": "Courier",                 "description": "Document courier / shipping partner",              "icon": "Package",     "color": "orange",   "default_payment_type": "flat",         "is_internal": False, "linked_role": None},
    {"key": "other",             "name": "Other",                   "description": "Miscellaneous external vendor",                    "icon": "MoreHorizontal","color": "neutral","default_payment_type": "flat",         "is_internal": False, "linked_role": None},
]


async def run_migration() -> dict:
    started_at = datetime.now(timezone.utc)

    # Indexes
    await vendor_categories_col.create_index("key", unique=True)
    await vendor_categories_col.create_index([("is_active", 1), ("name", 1)])
    await vendors_col.create_index("vendor_code", unique=True)
    await vendors_col.create_index("email", unique=True)
    await vendors_col.create_index([("category", 1), ("status", 1)])
    await vendors_col.create_index([("vendor_type", 1), ("status", 1)])
    await vendors_col.create_index([("user_id", 1)], sparse=True)

    # Seed
    seeded, skipped = 0, 0
    for cat in DEFAULT_CATEGORIES:
        existing = await vendor_categories_col.find_one({"key": cat["key"]}, {"_id": 0, "key": 1})
        if existing:
            skipped += 1
            continue
        doc = {
            "id": str(uuid.uuid4()),
            **cat,
            "is_active": True,
            "is_system": True,
            "created_by": "system",
            "created_at": started_at,
        }
        await vendor_categories_col.insert_one(doc)
        seeded += 1

    return {
        "key": "phase4c1_vendors_init_v1",
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "categories_seeded": seeded,
        "categories_skipped": skipped,
        "status": "completed",
    }
