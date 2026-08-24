"""Seed the 148 non-CSOL real ANZSCO 2022 occupations as basic REFERENCE skeletons
so no valid occupation code is ever 'missing'. These are not on any skilled list, so
no visa pathways / assessing authority are asserted (status='imported_skeleton').
"""
import asyncio, os, json
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
ISO = datetime.now(timezone.utc).isoformat()

missing_real = json.load(open("/tmp/missing_real.json"))["missing_real"]
csol_codes = {x["code"] for x in json.load(open("/tmp/csol_missing.json"))["csol_missing"]}
hier = json.load(open("/tmp/hier2022.json"))

reference = [r for r in missing_real if r["code"] not in csol_codes]
print("Reference (non-CSOL) to seed:", len(reference))


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    col = db["occupation_master"]
    four = db["anzsco_4digit_master"]
    inserted, skipped = 0, 0
    no_desc = []
    for r in reference:
        code = r["code"]
        if await col.find_one({"code": code, "country_code": "AU"}):
            skipped += 1
            continue
        h = hier.get(code, {})
        unit = h.get("unit") or code[:4]
        parent = await four.find_one({"code": unit})
        desc = (parent or {}).get("description") or ""
        tasks = (parent or {}).get("tasks") or []
        if not desc:
            no_desc.append(f"{code} {h.get('title')}")
        doc = {
            "occupation_id": f"AU-{code}",
            "code": code,
            "classification_type": "ANZSCO",
            "classification_version": "2022",
            "country_code": "AU",
            "title": h.get("title") or r.get("title") or "",
            "alternative_titles": [],
            "specialisations": [],
            "hierarchy": {"four_digit_parent": unit, "unit_group": unit, "unit_group_name": h.get("unit_name"),
                          "minor_group": h.get("minor"), "minor_group_name": h.get("minor_name"),
                          "sub_major_group": h.get("sub"), "major_group": h.get("major")},
            "description": desc,
            "typical_tasks": tasks,
            "tasks": tasks,
            "skill_level": h.get("skill_level") or "",
            "assessing_authority": {"short_name": "", "name": "", "url": ""},
            "skill_assessment_details": {},
            "visa_pathways": {"visa_eligibility": [], "pathway_lists": []},
            "state_territory_eligibility": [],
            "similar_codes": [],
            "status": "imported_skeleton",
            "verification": {"is_verified": False, "verified_by": None, "verified_at": None},
            "source": "anzsco_2022_reference_seed",
            "compliance_note": "Reference occupation (ANZSCO 2022). Not on the CSOL or MLTSSL — no standard skilled-migration pathway. Verify any list membership before advising.",
            "imported_at": ISO, "imported_by": "admin@leamss.com",
            "created_by": "admin@leamss.com", "created_at": ISO, "updated_at": ISO,
            "data_source": {"label": "ABS ANZSCO 2022 (Table 5)",
                            "url": "https://www.abs.gov.au/statistics/classifications/anzsco-australian-and-new-zealand-standard-classification-occupations/2022",
                            "reference_period": "2022", "imported_at": ISO, "imported_by": "admin@leamss.com"},
            "classification_dual_code": {"2022": code},
            "pathway_list": "",
            "pathway_lists": [],
        }
        await col.insert_one(doc)
        inserted += 1
    print(f"INSERTED reference skeletons: {inserted} | SKIPPED (already present): {skipped}")
    print(f"Records with empty description (new unit groups): {len(no_desc)}")
    for n in no_desc:
        print("   ", n)
    total = await col.count_documents({"country_code": "AU", "status": {"$ne": "superseded"}})
    print(f"AU active occupations now: {total}")


if __name__ == "__main__":
    asyncio.run(main())
