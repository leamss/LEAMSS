"""Seed ANZSCO 324111 Panelbeater (AU) into occupation_master.
Mirrors the TRA-assessed MLTSSL;CSOL schema used by 341111 (Electricians General).
"""
import asyncio, os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

NOW = datetime.now(timezone.utc)
ISO = NOW.isoformat()

TASKS = [
    "Examines damaged vehicles and estimates the extent and cost of repairs.",
    "Removes dents from vehicle panels and bodies using hammers, jacks and other hand and power tools.",
    "Repairs damaged vehicle body work by cutting out, removing and replacing damaged panels and sections.",
    "Fills depressions in bodywork with body solder and filler, and files, grinds and sands surfaces.",
    "Fits and adjusts new parts and panels, and aligns vehicle chassis and body frames.",
    "Removes rust and treats and prepares surfaces prior to painting.",
    "Uses welding and brazing equipment to join and repair metal sections.",
]

DOC = {
    "occupation_id": "AU-324111",
    "code": "324111",
    "classification_type": "ANZSCO",
    "classification_version": "1.3",
    "country_code": "AU",
    "title": "Panelbeater",
    "alternative_titles": ["Collision Repairer"],
    "specialisations": [],
    "hierarchy": {"four_digit_parent": "3241"},
    "description": (
        "Panelbeaters repair damage to vehicle bodies and body components made of metal, "
        "plastic or fibreglass, and reform and refinish damaged panels and body sections."
    ),
    "typical_tasks": TASKS,
    "skill_level": "3",
    "assessing_authority": {
        "short_name": "TRA",
        "name": "Trades Recognition Australia",
        "url": "",
    },
    "skill_assessment_details": {
        "qualification_required": "Trade-equivalent qualification (per AQF, e.g. AUR32120 Certificate III in Automotive Body Repair Technology)",
        "experience_required": "Post-qualification employment in the trade",
        "pre_qual_experience_allowed": "case-by-case",
    },
    "visa_pathways": {
        "visa_eligibility": [
            {"visa_subclass": "189", "notes": "Skilled Independent  (subclass 189) - Points-Tested", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "190", "notes": "Skilled Nominated   (subclass 190)", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "407", "notes": "Training visa (subclass 407)", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "485", "notes": "Temporary Graduate (subclass 485)", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "489", "notes": "Skilled Regional (Provisional) visa (subclass 489) - Family sponsored", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "489", "notes": "Skilled Regional (Provisional) visa (subclass 489) - State or Territory nominated", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "494", "notes": "Skilled Employer Sponsored Regional (provisional) (subclass 494) - Employer sponsored stream", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "491", "notes": "Skilled Work Regional (provisional) visa (subclass 491) State or Territory nominated", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "491", "notes": "Skilled Work Regional (provisional) visa (subclass 491) Family Sponsored", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "482", "notes": "Skills in Demand (subclass 482) - Core Skills stream", "eligible": True, "list": "MLTSSL;CSOL"},
            {"visa_subclass": "186", "notes": "Employer Nomination Scheme visa (subclass 186) - Direct Entry Pathway", "eligible": True, "list": "MLTSSL;CSOL"},
        ],
        "pathway_lists": ["MLTSSL;CSOL"],
    },
    "state_territory_eligibility": [],
    "similar_codes": [],
    "status": "verified",
    "verification": {"is_verified": False, "verified_by": None, "verified_at": None},
    "source": "manual_seed_324111",
    "imported_at": ISO,
    "imported_by": "admin@leamss.com",
    "created_by": "admin@leamss.com",
    "created_at": ISO,
    "updated_at": ISO,
    "anzsco_profile": {
        "employed_count": None,
        "part_time_share_pct": None,
        "female_share_pct": None,
        "median_weekly_earnings_aud": None,
        "median_age": None,
        "annual_employment_growth": None,
        "full_time_share_pct": None,
        "avg_full_time_hours_per_week": None,
        "median_full_time_weekly_aud": None,
        "median_full_time_hourly_aud": None,
    },
    "tasks": TASKS,
    "industries_ranked": ["Other Services", "Manufacturing", "Retail Trade"],
    "state_distribution": {},
    "education_distribution": {},
    "data_source": {
        "label": "ABS ANZSCO 2022 - Unit Group 3241 Panelbeaters",
        "url": "https://www.abs.gov.au/statistics/classifications/anzsco-australian-and-new-zealand-standard-classification-occupations/2022/browse-classification/3/32/324/3241",
        "reference_period": "2022",
        "imported_at": ISO,
        "imported_by": "admin@leamss.com",
    },
    "anzsco_ref_url": "https://www.abs.gov.au/statistics/classifications/anzsco-australian-and-new-zealand-standard-classification-occupations/2022/browse-classification/3/32/324/3241",
    "classification_dual_code": {"2013": "324111", "2022": "324111"},
    "pathway_list": "MLTSSL;CSOL",
    "skillselect_tier": "tier_2",
    "skillselect_tier_reason": "core_skills_occupation_list",
}


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    existing = await db["occupation_master"].find_one({"code": "324111", "country_code": "AU"})
    if existing:
        print("ALREADY EXISTS - skipping insert")
        return
    res = await db["occupation_master"].insert_one(DOC)
    print("Inserted 324111 Panelbeater with _id:", res.inserted_id)
    check = await db["occupation_master"].find_one({"code": "324111", "country_code": "AU"})
    print("Verify:", check["code"], check["title"], "| authority:", check["assessing_authority"]["short_name"], "| pathway:", check["pathway_list"])


if __name__ == "__main__":
    asyncio.run(main())
