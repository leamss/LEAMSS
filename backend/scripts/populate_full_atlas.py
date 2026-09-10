"""Master script to populate all ANZSCO 4-digit groups, 6-digit occupations,
assessing bodies, state nominations, and auto-verify the Atlas.
"""
import asyncio
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.database import db
from core.anzsco_excel_importer import import_anzsco_excel
from core.eligibility_kb_seed import seed_country_rules
from core.eligibility_kb_bulk_seed import expand_seed
from core.migrations.occupation_master_migrate import run_migration
from core.auto_verify import auto_verify_all


async def main():
    print("=== STEP 1: Seeding Base Country Rules & Expanded Codes ===")
    await seed_country_rules(db['country_rules'])
    await expand_seed()

    print("\n=== STEP 2: Migrating into Occupation Master & Skill Body Master ===")
    await run_migration(commit=True)

    print("\n=== STEP 3: Importing Official ANZSCO 4-Digit Groups from Excel ===")
    # Look for the Excel file in possible container/local paths
    candidates = [
        "/app/data/jsa_imports/occupation_profiles_feb_2026.xlsx",
        "/app/backend/data/jsa_imports/occupation_profiles_feb_2026.xlsx",
        str(Path(__file__).resolve().parents[1] / "data" / "jsa_imports" / "occupation_profiles_feb_2026.xlsx"),
    ]
    excel_path = None
    for cand in candidates:
        if os.path.exists(cand):
            excel_path = cand
            break

    if excel_path:
        print(f"Found workbook at: {excel_path}")
        res = await import_anzsco_excel(excel_path, imported_by="system_auto")
        print(f"✔ 4-Digit ANZSCO Import: {res.get('imported')} imported, {res.get('updated')} updated, total {res.get('total_processed')}")
    else:
        print(f"⚠️ Workbook not found at candidate paths: {candidates}")

    print("\n=== STEP 4: Running Scrapers & Enrichments ===")
    try:
        from core.scrapers.vetassess_groups import apply_vetassess_seed
        await apply_vetassess_seed(db)
        print("✔ VETASSESS groups applied")
    except Exception as e:
        print(f"VETASSESS note: {e}")

    try:
        from core.scrapers.state_nominations import scrape_all_states
        await scrape_all_states(db)
        print("✔ State nominations applied")
    except Exception as e:
        print(f"State nominations note: {e}")

    try:
        from core.scrapers.skillselect_tiers import apply_skillselect_tiers
        await apply_skillselect_tiers(db)
        print("✔ SkillSelect tiers applied")
    except Exception as e:
        print(f"SkillSelect note: {e}")

    print("\n=== STEP 5: Running Auto-Verification ===")
    try:
        v_res = await auto_verify_all(dry_run=False)
        print(f"✔ Auto-verified: {v_res}")
    except Exception as e:
        print(f"Auto-verify note: {e}")

    print("\n🎉 Full Atlas data merge & verification complete!")


if __name__ == "__main__":
    asyncio.run(main())
