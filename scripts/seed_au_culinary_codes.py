#!/usr/bin/env python3
"""Seed missing AU culinary / food-trade ANZSCO codes into occupation_master.

WHY: The AU occupation_master was missing the core culinary trades (Chef 351311,
Cook 351411, Butcher 351211), so AU chef/cook resumes returned no exact code.
Bakers (351111) and Pastrycooks (351112) already exist. This script idempotently
UPSERTS the missing codes with accurate ANZSCO + Home Affairs SOL data, marked
status=verified so they surface on the public Atlas and the AI suggester.

Data verified (Jun 2026): assessing authority = TRA (Trades Recognition Australia).
  • Chef 351311 — Skill Level 2 — MLTSSL → 189/190/491/482/186 eligible
  • Cook 351411 — Skill Level 3 — STSOL+CSOL → 190/491/482/186 (NOT 189)
  • Butcher or Smallgoods Maker 351211 — Skill Level 3 — STSOL+CSOL → 190/491/482/186

NOTE: State/territory nomination lists change frequently — left empty here for the
admin to confirm per current state programs before giving client advice.

USAGE:
  python /app/scripts/seed_au_culinary_codes.py
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")

TRA = {"body_id": "tra", "name": "TRA", "full_name": "Trades Recognition Australia", "website": "https://www.tradesrecognitionaustralia.gov.au"}


def _visa_eligibility(list_name: str, s189: bool):
    return [
        {"visa_subclass": "189", "eligible": s189, "list": list_name, "notes": "" if s189 else "Not eligible — occupation not on MLTSSL"},
        {"visa_subclass": "190", "eligible": True, "list": list_name, "notes": ""},
        {"visa_subclass": "491", "eligible": True, "list": list_name, "notes": ""},
        {"visa_subclass": "482", "eligible": True, "list": list_name, "notes": "Skills in Demand (Core Skills stream)"},
        {"visa_subclass": "186", "eligible": True, "list": list_name, "notes": "ENS Direct Entry"},
        {"visa_subclass": "187", "eligible": False, "list": list_name, "notes": ""},
        {"visa_subclass": "485", "eligible": False, "list": list_name, "notes": ""},
    ]


CODES = [
    {
        "code": "351311",
        "title": "Chef",
        "alternative_titles": ["Head Chef", "Executive Chef", "Sous Chef", "Chef de Partie",
                                "Demi Chef de Partie", "Commis Chef", "Pastry Chef", "Garde Manger"],
        "skill_level": 2,
        "unit_group": "3513",
        "unit_group_name": "Chefs",
        "pathway_lists": ["MLTSSL"],
        "visa_eligibility": _visa_eligibility("MLTSSL", s189=True),
        "description": ("Chefs plan and organise the preparation and cooking of food in dining and "
                        "catering establishments. They design menus, control kitchen operations, and "
                        "supervise cooks and other kitchen staff."),
        "typical_tasks": [
            "Planning menus and estimating food and labour costs",
            "Ordering and purchasing food supplies",
            "Monitoring quality of dishes at all stages of preparation and presentation",
            "Discussing food preparation issues with managers, dietitians and kitchen staff",
            "Demonstrating techniques and advising on cooking procedures",
            "Preparing, seasoning and cooking food, and portioning and plating meals",
            "Explaining and enforcing hygiene and food-safety regulations",
            "Selecting, training and supervising kitchen staff",
        ],
    },
    {
        "code": "351411",
        "title": "Cook",
        "alternative_titles": ["Commercial Cook", "Line Cook", "Grill Cook", "Breakfast Cook"],
        "skill_level": 3,
        "unit_group": "3514",
        "unit_group_name": "Cooks",
        "pathway_lists": ["STSOL", "CSOL"],
        "visa_eligibility": _visa_eligibility("STSOL", s189=False),
        "description": ("Cooks prepare, season and cook soups, meats, vegetables, desserts and other "
                        "foodstuffs in dining and catering establishments."),
        "typical_tasks": [
            "Examining foodstuffs to ensure quality",
            "Regulating temperatures of ovens, grills and other cooking equipment",
            "Preparing and cooking food by baking, roasting, grilling, frying and steaming",
            "Seasoning food during cooking",
            "Portioning food, placing it on plates, and adding gravies, sauces and garnishes",
            "Storing food in temperature-controlled conditions",
            "Washing, peeling, cutting and deboning foodstuffs before cooking",
        ],
    },
    {
        "code": "351211",
        "title": "Butcher or Smallgoods Maker",
        "alternative_titles": ["Butcher", "Smallgoods Maker", "Slaughterer"],
        "skill_level": 3,
        "unit_group": "3512",
        "unit_group_name": "Butchers and Smallgoods Makers",
        "pathway_lists": ["STSOL", "CSOL"],
        "visa_eligibility": _visa_eligibility("STSOL", s189=False),
        "description": ("Butchers or Smallgoods Makers select, cut, bone, trim and prepare standard cuts "
                        "of meat and smallgoods for sale, and may serve customers."),
        "typical_tasks": [
            "Cutting, boning, trimming and preparing standard cuts of meat",
            "Curing and preserving meat and making smallgoods such as sausages",
            "Grinding meat and preparing mince and portion-controlled cuts",
            "Cleaning and maintaining equipment and work areas to hygiene standards",
            "Advising and serving customers, and weighing and pricing products",
        ],
    },
]


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    col = db["occupation_master"]
    now = datetime.now(timezone.utc)
    inserted, updated = 0, 0
    for c in CODES:
        doc = {
            "code": c["code"],
            "classification_type": "ANZSCO",
            "classification_version": "Curated culinary seed · 2026-06",
            "country_code": "AU",
            "title": c["title"],
            "alternative_titles": c["alternative_titles"],
            "specialisations": [],
            "hierarchy": {
                "major_group": "3", "sub_major_group": "35", "minor_group": "351",
                "unit_group": c["unit_group"], "unit_group_name": c["unit_group_name"],
            },
            "description": c["description"],
            "typical_tasks": c["typical_tasks"],
            "skill_level": c["skill_level"],
            "assessing_authority": TRA,
            "skill_assessment_details": {
                "requirements": "Recognised qualification in commercial cookery/relevant trade plus post-qualification work experience; or Job Ready Program for Australian-trained applicants.",
                "criteria_notes": "", "qualification_rules": "", "documents_required": [],
                "fee_native": None, "fee_currency": None, "processing_time": "",
            },
            "visa_pathways": {
                "pathway_lists": c["pathway_lists"],
                "visa_eligibility": c["visa_eligibility"],
                "processing_times": {},
            },
            "state_territory_eligibility": [],
            "similar_codes": [x["code"] for x in CODES if x["code"] != c["code"]],
            "status": "verified",
            "verification": {
                "verified_by": "system-seed",
                "verified_at": now,
                "source_reference": "ANZSCO + Home Affairs Skilled Occupation List (verified Jun 2026)",
                "review_notes": "Seeded culinary trade. Confirm current SOL + state/territory nomination before client advice.",
            },
            "ai_draft": {"description": c["description"], "typical_tasks": c["typical_tasks"]},
            "updated_at": now,
        }
        existing = await col.find_one({"country_code": "AU", "code": c["code"]}, {"_id": 1})
        if existing:
            await col.update_one({"country_code": "AU", "code": c["code"]}, {"$set": doc})
            updated += 1
            print(f"  ↻ updated AU {c['code']} {c['title']}")
        else:
            doc["occupation_id"] = str(uuid.uuid4())
            doc["created_at"] = now
            await col.insert_one(doc)
            inserted += 1
            print(f"  + inserted AU {c['code']} {c['title']}")
    print(f"\n✅ Done — inserted {inserted}, updated {updated}. (idempotent, safe to re-run)")


if __name__ == "__main__":
    asyncio.run(main())
