"""One-stop script to seed skill levels, import all JSA data, and regenerate SSG files.

Usage (inside backend docker container or on server):
    python scripts/enrich_jsa_and_ssg.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import shutil
from pathlib import Path

# Add backend directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from motor.motor_asyncio import AsyncIOMotorClient
from seeds.au_states import SEED_STATES
from services.state_aggregation_service import refresh_all_states
from parsers.jsa import occupation_profiles, employment_projections, sa4_ratings, industry_data
from services.jsa_importer import (
    commit_occupation_profiles,
    commit_employment_projections,
    commit_sa4_ratings,
    commit_industry_data,
)
from routers.seo_ssg import regenerate_all


def get_anzsco_skill_level(code: str) -> int:
    code = str(code).strip()
    if not code:
        return 1

    major = code[0]
    submajor = code[:2] if len(code) >= 2 else code
    unit = code[:4] if len(code) >= 4 else code

    # Major 2: Professionals -> all Skill Level 1
    if major == '2':
        return 1

    # Major 1: Managers
    if major == '1':
        if submajor in ('11', '13'):
            if unit == '1331' and code.startswith('133112'):
                return 2
            return 1
        if submajor == '12':  # Farmers
            if unit in ('1211', '1212', '1214'):
                return 1
            if unit == '1213':
                if code.startswith(('121311', '121316')):
                    return 2
                return 1
            return 1
        if submajor == '14':  # Hospitality, Retail and Service Managers
            return 2
        return 1

    # Major 3: Technicians and Trades
    if major == '3':
        if submajor == '31':  # Engineering, ICT and Science Technicians
            return 2
        return 3

    # Major 4: Community and Personal Service Workers
    if major == '4':
        if unit in ('4111', '4112', '4113', '4114', '4117', '4412', '4413'):
            return 2
        if unit in ('4115', '4116', '4511', '4512', '4521', '4522', '4523', '4524'):
            return 3
        return 4

    # Major 5: Clerical and Administrative Workers
    if major == '5':
        if unit in ('5111', '5112'):
            return 2
        if unit in ('5121', '5122'):
            return 3
        return 4

    # Major 6: Sales Workers
    if major == '6':
        if unit in ('6111', '6112'):
            return 3
        return 4

    # Major 7: Machinery Operators and Drivers
    if major == '7':
        return 4

    # Major 8: Labourers
    if major == '8':
        return 5

    return 1


async def main():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://127.0.0.1:27017")
    db_name = os.environ.get("DB_NAME", "leamss")
    print(f"Connecting to MongoDB at {mongo_url} [{db_name}]...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # 1. Seed Skill Levels
    print("\n--- 1. Seeding ANZSCO Skill Levels ---")
    cursor = db["occupation_master"].find({"country_code": "AU"})
    count_lvl = 0
    async for doc in cursor:
        lvl = get_anzsco_skill_level(doc.get("code"))
        await db["occupation_master"].update_one(
            {"_id": doc["_id"]},
            {"$set": {"skill_level": lvl}}
        )
        count_lvl += 1
    print(f"Updated {count_lvl} AU occupations with ANZSCO skill level.")

    # 2. Seed AU States
    print("\n--- 2. Seeding AU States Master ---")
    states_seeded = 0
    for seed in SEED_STATES:
        existing = await db["au_states_master"].find_one({"state_code": seed["state_code"]})
        if not existing:
            await db["au_states_master"].insert_one(dict(seed))
            states_seeded += 1
        else:
            await db["au_states_master"].update_one(
                {"state_code": seed["state_code"]},
                {"$set": seed}
            )
    print(f"AU States seeded/updated ({len(SEED_STATES)} states).")

    # 3. Import JSA Excel Datasets
    jsa_dir = BACKEND_DIR / "data" / "jsa_imports"
    if jsa_dir.exists():
        print("\n--- 3. Importing JSA Datasets from backend/data/jsa_imports/ ---")
        
        # 3a. Occupation Profiles (ABS earnings, demographics, top industries, education)
        occ_file = jsa_dir / "occupation_profiles_feb_2026.xlsx"
        if occ_file.exists():
            print(f"Parsing {occ_file.name}...")
            parsed = list(occupation_profiles.parse_workbook(str(occ_file)))
            res = await commit_occupation_profiles(db, parsed)
            print("Occupation profiles committed:", res)
        
        # 3b. Employment Projections (2025-2035 growth, future demand)
        proj_file = jsa_dir / "employment_projections_may_2025_2035.xlsx"
        if proj_file.exists():
            print(f"Parsing {proj_file.name}...")
            parsed = list(employment_projections.parse_workbook(str(proj_file)))
            res = await commit_employment_projections(db, parsed)
            print("Employment projections committed:", res)

        # 3c. Labour market ratings by SA4
        sa4_file = jsa_dir / "labour_market_ratings_by_sa4.xlsx"
        if sa4_file.exists():
            print(f"Parsing {sa4_file.name}...")
            parsed = list(sa4_ratings.parse_workbook(str(sa4_file)))
            res = await commit_sa4_ratings(db, parsed)
            print("SA4 ratings committed:", res)

        # 3d. Industry Data (ANZSIC 19 industries)
        ind_file = jsa_dir / "industry_data_feb_2026.xlsx"
        if ind_file.exists():
            print(f"Parsing {ind_file.name}...")
            parsed = list(industry_data.parse_workbook(str(ind_file)))
            res = await commit_industry_data(db, parsed)
            print("Industry data committed:", res)

    # 4. Refresh State Aggregations
    print("\n--- 4. Refreshing State Aggregations ---")
    try:
        agg_res = await refresh_all_states(db)
        print("State aggregation refreshed:", agg_res)
    except Exception as e:
        print("State aggregation warning:", e)

    # 5. Regenerate SSG Files
    print("\n--- 5. Regenerating Static Site (SSG) Files ---")
    try:
        ssg_res = await regenerate_all()
        print("SSG Regeneration completed:", ssg_res)
    except Exception as e:
        print("SSG Regeneration error:", e)

    # 6. Synchronize frontend/public/atlas into frontend/build/atlas
    print("\n--- 6. Syncing frontend/public/atlas to frontend/build/atlas ---")
    pub_atlas = PROJECT_ROOT / "frontend" / "public" / "atlas"
    bld_atlas = PROJECT_ROOT / "frontend" / "build" / "atlas"
    if pub_atlas.exists():
        bld_atlas.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(pub_atlas), str(bld_atlas), dirs_exist_ok=True)
        print("Successfully synchronized frontend/public/atlas -> frontend/build/atlas")

    print("\n=== ALL JSA ENRICHMENT & SSG GENERATION COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())
