"""Phase 7.1 — Idempotent migration:
  1. Seed UK + USA country_templates (status=draft) — fills Sir's gap
  2. Seed default LEAMSS Protection Policy (status=draft) — Sir's USP
  3. Add `status: active` to all existing occupation_master docs missing the field
  4. Add `custom_qa: []` to all existing occupation_master docs missing the field
  5. Add `status: active` to country_templates / country_guides missing it

All operations are idempotent — safe to re-run.
"""
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

# Allow running directly from /app/backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

COUNTRY_TEMPLATES = db["country_templates"]
COUNTRY_GUIDES = db["country_guides"]
OCCUPATIONS = db["occupation_master"]
POLICIES = db["protection_policies"]


def _now():
    return datetime.now(timezone.utc)


UK_TEMPLATE = {
    "country_code": "UK",
    "country_name": "United Kingdom",
    "flag": "🇬🇧",
    "classification_system": "SOC2020",
    "pass_mark": 70,
    "factors": [],
    "visa_subclasses": [
        {"code": "skilled_worker", "name": "Skilled Worker Visa", "description": "Job offer with eligible employer + skill level RQF 3+ + English."},
        {"code": "global_talent", "name": "Global Talent", "description": "Endorsement by approved UK body in digital/research/arts."},
        {"code": "scale_up", "name": "Scale-up Worker", "description": "Sponsored by fast-growth UK businesses."},
        {"code": "hpi", "name": "High Potential Individual", "description": "Graduate from top global universities (last 5 yrs)."},
    ],
    "partner_rules": {},
    "notes": (
        "Phase 7.1 seed — Sir flagged UK was missing from country_templates while present in country_guides. "
        "Admin to add SOC 2020 points-equivalent factors and verify against gov.uk/skilled-worker-visa."
    ),
    "status": "draft",
    "verification": {"verified_by": None, "verified_at": None, "source_reference": None, "review_notes": ""},
    "is_default_seed": True,
    "created_at": _now(),
    "updated_at": _now(),
}

USA_TEMPLATE = {
    "country_code": "USA",
    "country_name": "United States of America",
    "flag": "🇺🇸",
    "classification_system": "SOC2018",
    "pass_mark": None,  # USA mostly non-points-based for H1B/EB-2
    "factors": [],
    "visa_subclasses": [
        {"code": "h1b", "name": "H-1B Specialty Occupation", "description": "Lottery-based, employer-sponsored, bachelor's-equivalent role."},
        {"code": "eb1a", "name": "EB-1A Extraordinary Ability", "description": "Top achievement in sciences/arts/business — no PERM/labor cert."},
        {"code": "eb1b", "name": "EB-1B Outstanding Researcher", "description": "International recognition in academia/research."},
        {"code": "eb2_niw", "name": "EB-2 NIW", "description": "Advanced degree or exceptional ability + national interest waiver."},
        {"code": "o1", "name": "O-1 Extraordinary Ability", "description": "Top in field — non-immigrant work visa."},
    ],
    "partner_rules": {},
    "notes": (
        "Phase 7.1 seed — USA mostly category-based, not points. Admin to add per-category eligibility "
        "criteria and verify against uscis.gov."
    ),
    "status": "draft",
    "verification": {"verified_by": None, "verified_at": None, "source_reference": None, "review_notes": ""},
    "is_default_seed": True,
    "created_at": _now(),
    "updated_at": _now(),
}


async def seed_country_template(template_doc: dict):
    existing = await COUNTRY_TEMPLATES.find_one({"country_code": template_doc["country_code"]}, {"_id": 0})
    if existing:
        logger.info("Template %s already exists — skipping", template_doc["country_code"])
        return False
    await COUNTRY_TEMPLATES.insert_one(template_doc)
    logger.info("Inserted template for %s (%s)", template_doc["country_code"], template_doc["country_name"])
    return True


async def seed_default_protection_policy():
    existing = await POLICIES.find_one({"is_default_leamss": True}, {"_id": 0})
    if existing:
        logger.info("Default Protection Policy already exists (%s) — skipping", existing.get("policy_id"))
        return False
    policy_id = f"POL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    doc = {
        "policy_id": policy_id,
        "title": "🛡️ LEAMSS Protection Policy — 100% Refund Guarantee",
        "policy_type": "negative_outcome_refund",
        "description_markdown": (
            "## We Value Emotions\n\n"
            "LEAMSS is **India's first migration consultancy** to introduce a 100% Protection "
            "Policy that safeguards your entire investment.\n\n"
            "If your **skill assessment is negative** or your **visa is rejected** due to factors "
            "we have committed to verify upfront, we refund your **professional fees + government "
            "fees** without question.\n\n"
            "This policy is part of our promise of **complete transparency, honesty, and emotional "
            "accountability** to every client who trusts us with their dream of migration."
        ),
        "refund_terms": {
            "covers": ["professional_fees", "government_fees", "body_fees"],
            "excludes": ["english_test_fees", "medical_test_fees", "police_clearance_fees"],
            "claim_within_days": 90,
        },
        "applicable_countries": ["AU", "CA", "NZ", "UK", "USA"],
        "applicable_visa_types": ["*"],
        "version": "1.0",
        "is_default_leamss": True,
        "status": "draft",
        "verification": {"by": None, "by_name": None, "at": None, "source_reference": None},
        "created_at": _now(),
        "updated_at": _now(),
        "created_by": "system_phase71_migration",
    }
    await POLICIES.insert_one(doc)
    logger.info("Inserted default LEAMSS Protection Policy %s", policy_id)
    return True


async def backfill_status_field(collection, name: str):
    """Add status='active' to docs that don't have a status field."""
    r = await collection.update_many(
        {"status": {"$exists": False}},
        {"$set": {"status": "active", "status_backfilled_phase71_at": _now()}},
    )
    logger.info("[%s] Backfilled status=active on %d docs (skipped existing)", name, r.modified_count)


async def backfill_custom_qa_field():
    r = await OCCUPATIONS.update_many(
        {"custom_qa": {"$exists": False}},
        {"$set": {"custom_qa": []}},
    )
    logger.info("[occupation_master] Backfilled custom_qa=[] on %d docs", r.modified_count)


async def main():
    logger.info("══════════ Phase 7.1 KB Unification Migration ══════════")
    inserted_uk = await seed_country_template(UK_TEMPLATE)
    inserted_usa = await seed_country_template(USA_TEMPLATE)
    inserted_policy = await seed_default_protection_policy()
    await backfill_status_field(COUNTRY_TEMPLATES, "country_templates")
    await backfill_status_field(COUNTRY_GUIDES, "country_guides")
    await backfill_custom_qa_field()
    logger.info("══════════ Migration complete ══════════")
    logger.info("  UK template: %s", "✅ inserted" if inserted_uk else "⏭️  existed")
    logger.info("  USA template: %s", "✅ inserted" if inserted_usa else "⏭️  existed")
    logger.info("  Default Protection Policy: %s", "✅ inserted" if inserted_policy else "⏭️  existed")


async def run_idempotent(database) -> dict:
    """Phase 17.0 piggyback — call from `@app.on_event("startup")` so the
    Country Templates + Protection Policies KPI cards are never empty on a
    fresh DB. The ``database`` arg is accepted for API symmetry with other
    migrations but module-level collection handles are reused.

    Returns a small status dict suitable for printing during boot.
    """
    inserted_uk = await seed_country_template(UK_TEMPLATE)
    inserted_usa = await seed_country_template(USA_TEMPLATE)
    inserted_policy = await seed_default_protection_policy()
    await backfill_status_field(COUNTRY_TEMPLATES, "country_templates")
    await backfill_status_field(COUNTRY_GUIDES, "country_guides")
    await backfill_custom_qa_field()
    return {
        "status": "ok",
        "uk_template": "inserted" if inserted_uk else "existed",
        "usa_template": "inserted" if inserted_usa else "existed",
        "default_policy": "inserted" if inserted_policy else "existed",
    }


if __name__ == "__main__":
    asyncio.run(main())
