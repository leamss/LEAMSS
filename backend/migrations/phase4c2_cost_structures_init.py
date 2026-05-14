"""Phase 4C.2 — Seed 5 default cost structures + indexes."""
import uuid
from datetime import datetime, timezone
from core.database import db

cost_structures_col = db["product_cost_structures"]


def _alloc(category, payment_type, amount, label, optional=False, base="service_price"):
    return {
        "allocation_id": str(uuid.uuid4()),
        "vendor_category": category,
        "payment_type": payment_type,
        "amount": amount,
        "base": base,
        "label": label,
        "is_active": True,
        "is_optional": optional,
        "conditions": None,
        "auto_assign": True,
    }


def _bonus(category, amount, label, milestone="visa_approved"):
    return {"milestone": milestone, "vendor_category": category, "bonus_amount": amount, "label": label}


DEFAULT_STRUCTURES = [
    {
        "key": "canada_pr_express",
        "product_name": "Canada PR Express Entry",
        "country": "Canada", "visa_type": "PR",
        "service_price": 100000, "government_fees": 40000,
        "cost_allocations": [
            _alloc("sales_commission", "percentage", 5,  "Sales Commission (5%)"),
            _alloc("case_manager",     "flat",       10000, "Case Manager Fee"),
            _alloc("tutor",            "flat",       15000, "IELTS Coaching", optional=True),
            _alloc("lawyer",           "flat",       8000,  "Legal Review", optional=True),
        ],
        "success_bonuses": [
            _bonus("case_manager",     5000, "Visa Grant Bonus"),
            _bonus("sales_commission", 2000, "Sales Success Bonus"),
        ],
    },
    {
        "key": "australia_pr_skilled",
        "product_name": "Australia PR Skilled Worker",
        "country": "Australia", "visa_type": "PR",
        "service_price": 80000, "government_fees": 35000,
        "cost_allocations": [
            _alloc("sales_commission", "percentage", 5,     "Sales Commission (5%)"),
            _alloc("case_manager",     "flat",       8000,  "Case Manager Fee"),
            _alloc("tutor",            "flat",       15000, "PTE Coaching", optional=True),
        ],
        "success_bonuses": [
            _bonus("case_manager",     4000, "Visa Grant Bonus"),
            _bonus("sales_commission", 2000, "Sales Success Bonus"),
        ],
    },
    {
        "key": "usa_h1b",
        "product_name": "USA H1B",
        "country": "USA", "visa_type": "H1B",
        "service_price": 150000, "government_fees": 60000,
        "cost_allocations": [
            _alloc("sales_commission", "percentage", 5,     "Sales Commission (5%)"),
            _alloc("case_manager",     "flat",       15000, "Case Manager Fee"),
            _alloc("lawyer",           "flat",       15000, "Mandatory Legal Filing"),  # not optional for H1B
        ],
        "success_bonuses": [
            _bonus("case_manager",     7500, "Visa Grant Bonus"),
            _bonus("sales_commission", 3000, "Sales Success Bonus"),
            _bonus("lawyer",           5000, "Lawyer Success Bonus"),
        ],
    },
    {
        "key": "uk_skilled_worker",
        "product_name": "UK Skilled Worker",
        "country": "UK", "visa_type": "Skilled Worker",
        "service_price": 90000, "government_fees": 45000,
        "cost_allocations": [
            _alloc("sales_commission", "percentage", 5,     "Sales Commission (5%)"),
            _alloc("case_manager",     "flat",       10000, "Case Manager Fee"),
            _alloc("tutor",            "flat",       12000, "IELTS Coaching", optional=True),
        ],
        "success_bonuses": [
            _bonus("case_manager",     5000, "Visa Grant Bonus"),
            _bonus("sales_commission", 2000, "Sales Success Bonus"),
        ],
    },
    {
        "key": "student_visa_canada",
        "product_name": "Student Visa - Canada",
        "country": "Canada", "visa_type": "Student",
        "service_price": 50000, "government_fees": 12000,
        "cost_allocations": [
            _alloc("sales_commission", "percentage", 5,     "Sales Commission (5%)"),
            _alloc("case_manager",     "flat",       7000,  "Case Manager Fee"),
            _alloc("tutor",            "flat",       15000, "IELTS Coaching", optional=True),
        ],
        "success_bonuses": [
            _bonus("case_manager",     3000, "Visa Grant Bonus"),
            _bonus("sales_commission", 1500, "Sales Success Bonus"),
        ],
    },
]


def _compute(struct: dict) -> dict:
    sp = float(struct["service_price"])
    total_required = 0.0
    for a in struct["cost_allocations"]:
        if a.get("is_optional"):
            continue
        amount = float(a["amount"])
        if a["payment_type"] == "percentage":
            total_required += sp * amount / 100
        else:
            total_required += amount
    margin = round(sp - total_required, 2)
    return {
        "total_costs_typical": round(total_required, 2),
        "expected_margin": margin,
        "expected_margin_percentage": round((margin / sp * 100), 2) if sp > 0 else 0,
    }


async def run_migration() -> dict:
    started_at = datetime.now(timezone.utc)
    await cost_structures_col.create_index("key", unique=True, sparse=True)
    await cost_structures_col.create_index([("is_active", 1), ("country", 1)])
    await cost_structures_col.create_index([("product_name", 1)])

    seeded, skipped = 0, 0
    for s in DEFAULT_STRUCTURES:
        existing = await cost_structures_col.find_one({"key": s["key"]}, {"_id": 0, "key": 1})
        if existing:
            skipped += 1
            continue
        doc = {
            "id": str(uuid.uuid4()),
            **s,
            "computed": _compute(s),
            "is_active": True,
            "is_system": True,
            "effective_from": started_at,
            "effective_until": None,
            "deleted_at": None,
            "created_at": started_at,
            "created_by": "system",
            "updated_at": started_at,
        }
        await cost_structures_col.insert_one(doc)
        seeded += 1
    return {
        "key": "phase4c2_cost_structures_v1",
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "structures_seeded": seeded,
        "structures_skipped": skipped,
        "status": "completed",
    }
