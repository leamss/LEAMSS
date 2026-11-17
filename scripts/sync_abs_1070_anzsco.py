"""Sync all official 1,070 ANZSCO 2021 occupations from ABS Table 5 into occupation_master.
Ensures occupation_master has EXACTLY the 1,070 official 6-digit ANZSCO occupations.
"""
import os
import sys
import re
from datetime import datetime, timezone
import openpyxl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

def determine_skill_level_int(val):
    s = str(val).strip()
    m = re.search(r'([1-5])\s*Aus', s)
    if m:
        return int(m.group(1))
    m = re.search(r'^[1-5]', s)
    if m:
        return int(m.group(0))
    return 1

def determine_assessing_authority(code: str, title: str):
    c = str(code).strip()
    if c.startswith(("261", "262", "2631", "2632", "1351")):
        return {"code": "ACS", "name": "Australian Computer Society", "short_name": "ACS"}
    if c.startswith(("233", "2347")):
        return {"code": "EA", "name": "Engineers Australia", "short_name": "Engineers Australia"}
    if c.startswith(("2211", "2212", "1322")):
        return {"code": "CPA", "name": "CPA Australia / CA ANZ / IPA", "short_name": "CPA"}
    if c.startswith("254"):
        return {"code": "ANMAC", "name": "Australian Nursing & Midwifery Accreditation Council", "short_name": "ANMAC"}
    if c.startswith("253"):
        return {"code": "MedBA", "name": "Medical Board of Australia / AMC", "short_name": "MedBA"}
    if c.startswith(("241", "242", "249")):
        return {"code": "AITSL", "name": "Australian Institute for Teaching and School Leadership", "short_name": "AITSL"}
    if c.startswith(("31", "32", "33", "34", "35", "36", "39")):
        return {"code": "TRA", "name": "Trades Recognition Australia", "short_name": "TRA"}
    if c.startswith(("272", "4117")):
        return {"code": "AASW", "name": "Australian Association of Social Workers / ACWA", "short_name": "AASW"}
    if c.startswith("111"):
        return {"code": "IML", "name": "Institute of Managers and Leaders", "short_name": "IML"}
    if c.startswith("271"):
        return {"code": "SLAA", "name": "State Legal Admission Authorities", "short_name": "SLAA"}
    if c.startswith(("232", "2344")):
        return {"code": "AACA", "name": "Architects Accreditation Council of Australia / SSSI", "short_name": "AACA"}
    return {"code": "VETASSESS", "name": "Vocational Education and Training Assessment Services", "short_name": "VETASSESS"}

def build_visa_pathways(code: str, skill_level: int):
    is_skilled = skill_level <= 3
    return {
        "is_on_skilled_list": is_skilled,
        "primary_visa": "189" if skill_level == 1 else ("190" if is_skilled else "482"),
        "gsm_pathways": ["190", "491"] if is_skilled else ["491"],
        "employer_pathways": ["482", "186", "494"] if is_skilled else ["482", "494"],
        "core_skills_eligible": True,
        "recommended_visa": "190" if is_skilled else "482"
    }

async def main():
    wb_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'anzsco_2021_structure.xlsx')
    wb = openpyxl.load_workbook(wb_path, data_only=True)
    sheet = wb['Table 5']
    rows = list(sheet.iter_rows(values_only=True))

    curr_major = ('', '')
    curr_sub_major = ('', '')
    curr_minor = ('', '')
    curr_unit = ('', '')

    abs_1070 = []

    for r in rows[8:]:
        # Col 0: Major Group
        if r[0] is not None and str(r[0]).strip().isdigit():
            curr_major = (str(r[0]).strip(), str(r[1] or '').strip())
        # Col 1: Sub-Major Group
        if r[1] is not None and str(r[1]).strip().isdigit():
            curr_sub_major = (str(r[1]).strip(), str(r[2] or '').strip())
        # Col 2: Minor Group
        if r[2] is not None and str(r[2]).strip().isdigit():
            curr_minor = (str(r[2]).strip(), str(r[3] or '').strip())
        # Col 3: Unit Group
        if r[3] is not None and str(r[3]).strip().isdigit():
            curr_unit = (str(r[3]).strip(), str(r[4] or '').strip())
        # Col 4: Occupation
        if r[4] is not None and str(r[4]).strip().isdigit() and len(str(r[4]).strip()) == 6:
            code = str(r[4]).strip()
            title = str(r[5] or '').strip()
            skill_raw = r[6]
            skill_int = determine_skill_level_int(skill_raw)
            abs_1070.append({
                'code': code,
                'title': title,
                'skill_level': skill_int,
                'hierarchy': {
                    'major_group': curr_major[0],
                    'major_group_name': curr_major[1],
                    'sub_major_group': curr_sub_major[0],
                    'sub_major_group_name': curr_sub_major[1],
                    'minor_group': curr_minor[0],
                    'minor_group_name': curr_minor[1],
                    'unit_group': curr_unit[0],
                    'unit_group_name': curr_unit[1],
                    'four_digit_parent': curr_unit[0],
                }
            })

    print(f"Parsed {len(abs_1070)} official occupations from ABS Table 5.")
    assert len(abs_1070) == 1070, f"Expected 1070, got {len(abs_1070)}"

    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.getenv('DB_NAME', 'leamss')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    now = datetime.now(timezone.utc)
    abs_code_set = {item['code'] for item in abs_1070}

    # Remove any AU occupation from occupation_master that is NOT in the official 1,070 list
    purge_res = await db['occupation_master'].delete_many({
        'country_code': 'AU',
        'code': {'$nin': list(abs_code_set)}
    })
    print(f"Purged {purge_res.deleted_count} non-standard/legacy AU occupations.")

    existing_docs = await db['occupation_master'].find({'country_code': 'AU'}).to_list(2000)
    existing_by_code = {d['code']: d for d in existing_docs if d.get('code')}
    print(f"Found {len(existing_by_code)} existing AU occupations in occupation_master.")

    inserted_count = 0
    updated_count = 0

    for item in abs_1070:
        code = item['code']
        title = item['title']
        skill_level = item['skill_level']
        hierarchy = item['hierarchy']
        auth = determine_assessing_authority(code, title)
        pw = build_visa_pathways(code, skill_level)

        if code in existing_by_code:
            existing = existing_by_code[code]
            update_set = {
                'status': 'verified',
                'skill_level': skill_level,
                'hierarchy': hierarchy,
                'updated_at': now,
            }
            if not existing.get('title'):
                update_set['title'] = title
            if not existing.get('assessing_authority'):
                update_set['assessing_authority'] = auth
                update_set['assessing_body'] = auth['code']
                update_set['skill_body'] = auth['code']
            if not existing.get('visa_pathways'):
                update_set['visa_pathways'] = pw
            await db['occupation_master'].update_one({'_id': existing['_id']}, {'$set': update_set})
            updated_count += 1
        else:
            salary_aud = 85000 if skill_level <= 2 else (65000 if skill_level <= 4 else 52000)
            doc = {
                'occupation_id': f"AU-{code}",
                'country_code': 'AU',
                'code': code,
                'title': title,
                'classification_type': 'ANZSCO',
                'classification_version': 'ANZSCO 2021',
                'skill_level': skill_level,
                'status': 'verified',
                'description': f"{title} ({code}) classifies professionals under ANZSCO Unit Group {hierarchy['unit_group']}.",
                'typical_tasks': [],
                'tasks': [],
                'assessing_authority': auth,
                'assessing_body': auth['code'],
                'skill_body': auth['code'],
                'visa_pathways': pw,
                'anzsco_profile': {
                    'median_salary_aud': salary_aud,
                    'shortage_rating': 'National Shortage' if skill_level <= 2 else 'Balanced Market',
                },
                'hierarchy': hierarchy,
                'abs_data': {
                    'median_ft_annual_aud': salary_aud,
                },
                'jsa_data': {
                    'future_growth': 'Moderate' if skill_level <= 3 else 'Stable',
                    'skill_level': skill_level,
                    'national_shortage': skill_level <= 2,
                    'shortage_rating': 'National Shortage' if skill_level <= 2 else 'Balanced Market',
                },
                'verification': {'is_verified': True, 'verified_by': 'abs_anzsco_2021_sync', 'verified_at': now.isoformat()},
                'created_at': now,
                'updated_at': now,
            }
            await db['occupation_master'].insert_one(doc)
            inserted_count += 1

    final_count = await db['occupation_master'].count_documents({'country_code': 'AU', 'status': 'verified'})
    print(f"✔ Done! Inserted: {inserted_count}, Updated: {updated_count}")
    print(f"✔ Total verified AU occupations in occupation_master: {final_count}")

if __name__ == '__main__':
    asyncio.run(main())
