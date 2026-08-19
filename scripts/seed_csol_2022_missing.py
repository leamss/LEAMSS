"""Seed the 79 missing CSOL (ANZSCO 2022) occupations into occupation_master (AU).

Data sources (all authoritative):
  - ABS ANZSCO 2022 structure (Table 5): code, title, skill level, hierarchy
  - CSOL (Migration (Specification of Occupations-Subclass 482 Visa) Instrument 2024, F2024L01620): list membership
  - Assessing authorities (Subclass 186 Instrument, F2024L01618): code -> assessing authority
  - anzsco_4digit_master: inherited description + typical tasks from 4-digit parent

Policy:
  - These are ANZSCO 2022 / CSOL (employer-sponsored) records: visas 482 / 186 / 494, list = CSOL.
  - GSM (189/190/491) uses ANZSCO 2013 + MLTSSL, so it is NOT asserted here (a note is stored).
  - Renumber cases (same occupation, new 2022 code vs existing 2013 code in DB): old code -> status 'superseded'.
"""
import asyncio, os, json, re
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
NOW = datetime.now(timezone.utc)
ISO = NOW.isoformat()

csol_missing = [x["code"] for x in json.load(open("/tmp/csol_missing.json"))["csol_missing"]]
code2auth = json.load(open("/tmp/code2auth.json"))
hier = json.load(open("/tmp/hier2022.json"))

AUTH_FULL = {
    "VETASSESS": "Vocational Education and Training Assessment Services",
    "TRA": "Trades Recognition Australia",
    "ACS": "Australian Computer Society",
    "EA": "Engineers Australia",
    "IML": "Institute of Managers and Leaders",
    "AITSL": "Australian Institute for Teaching and School Leadership",
    "MedBA": "Medical Board of Australia",
    "ANMAC": "Australian Nursing and Midwifery Accreditation Council",
    "SLAA": "State or Territory Legal Admission Authority",
    "AVBC": "Australasian Veterinary Boards Council",
    "APC": "Australian Physiotherapy Council",
    "PodBA": "Podiatry Board of Australia",
    "AASW": "Australian Association of Social Workers",
    "CAANZ, CPAA, IPA": "Chartered Accountants ANZ / CPA Australia / Institute of Public Accountants",
    "TRA, VETASSESS": "Trades Recognition Australia / VETASSESS",
    "EA, VETASSESS": "Engineers Australia / VETASSESS",
}

CSOL_VISAS = [
    {"visa_subclass": "482", "notes": "Skills in Demand (subclass 482) - Core Skills stream", "eligible": True, "list": "CSOL"},
    {"visa_subclass": "186", "notes": "Employer Nomination Scheme visa (subclass 186) - Direct Entry Pathway", "eligible": True, "list": "CSOL"},
    {"visa_subclass": "494", "notes": "Skilled Employer Sponsored Regional (provisional) (subclass 494) - Employer sponsored stream", "eligible": True, "list": "CSOL"},
]

GSM_NOTE = ("GSM points-tested visas (189/190/491) use ANZSCO 2013 (MLTSSL/STSOL) codes; "
            "verify GSM eligibility separately. This record covers employer-sponsored CSOL pathways (ANZSCO 2022).")


def norm_title(t):
    t = (t or "").lower()
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"[^a-z ]", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    # crude singularisation of last word
    words = t.split()
    if words and words[-1].endswith("s") and len(words[-1]) > 3:
        words[-1] = words[-1][:-1]
    return " ".join(words)


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    col = db["occupation_master"]
    four = db["anzsco_4digit_master"]

    inserted, skipped, superseded = [], [], []
    for code in csol_missing:
        if await col.find_one({"code": code, "country_code": "AU"}):
            skipped.append(code)
            continue
        h = hier.get(code, {})
        title = h.get("title") or ""
        unit = h.get("unit") or code[:4]
        # enrichment: description + tasks from 4-digit parent
        parent = await four.find_one({"code": unit})
        desc = (parent or {}).get("description") or ""
        tasks = (parent or {}).get("tasks") or []
        auth_short = code2auth.get(code, "")
        auth_full = AUTH_FULL.get(auth_short, auth_short)

        # renumber detection: same 4-digit unit, exact normalised title match
        superseded_note = None
        nt = norm_title(title)
        async for old in col.find({"country_code": "AU", "code": {"$regex": f"^{unit}"}, "status": {"$ne": "superseded"}},
                                  {"code": 1, "title": 1}):
            if old["code"] != code and norm_title(old.get("title")) == nt and nt:
                await col.update_one({"_id": old["_id"]},
                    {"$set": {"status": "superseded",
                              "superseded_by": code,
                              "superseded_reason": "ANZSCO 2013 -> 2022 renumber (CSOL uses new code)",
                              "superseded_at": ISO}})
                superseded.append(f"{old['code']} ({old.get('title')}) -> {code}")
                superseded_note = f"Replaces ANZSCO 2013 code {old['code']} ({old.get('title')})"
                break

        doc = {
            "occupation_id": f"AU-{code}",
            "code": code,
            "classification_type": "ANZSCO",
            "classification_version": "2022",
            "country_code": "AU",
            "title": title,
            "alternative_titles": [],
            "specialisations": [],
            "hierarchy": {"four_digit_parent": unit, "unit_group": unit, "unit_group_name": h.get("unit_name"),
                          "minor_group": h.get("minor"), "minor_group_name": h.get("minor_name"),
                          "sub_major_group": h.get("sub"), "major_group": h.get("major")},
            "description": desc,
            "typical_tasks": tasks,
            "tasks": tasks,
            "skill_level": h.get("skill_level") or "",
            "assessing_authority": {"short_name": auth_short, "name": auth_full, "url": ""},
            "skill_assessment_details": {},
            "visa_pathways": {"visa_eligibility": [dict(v) for v in CSOL_VISAS], "pathway_lists": ["CSOL"]},
            "state_territory_eligibility": [],
            "similar_codes": [],
            "status": "verified",
            "verification": {"is_verified": False, "verified_by": None, "verified_at": None},
            "source": "csol_2022_gap_seed",
            "compliance_note": GSM_NOTE + ((" " + superseded_note) if superseded_note else ""),
            "imported_at": ISO, "imported_by": "admin@leamss.com",
            "created_by": "admin@leamss.com", "created_at": ISO, "updated_at": ISO,
            "data_source": {
                "label": "ABS ANZSCO 2022 + CSOL (F2024L01620) + Assessing Authorities (F2024L01618)",
                "url": "https://www.legislation.gov.au/F2024L01620/latest",
                "reference_period": "2024-25 (CSOL, compilation Nov 2025)",
                "imported_at": ISO, "imported_by": "admin@leamss.com",
            },
            "classification_dual_code": {"2022": code},
            "pathway_list": "CSOL",
            "pathway_lists": ["CSOL"],
        }
        await col.insert_one(doc)
        inserted.append(f"{code} {title} [{auth_short}]")

    print(f"INSERTED: {len(inserted)}")
    for i in inserted:
        print("  +", i)
    print(f"\nSUPERSEDED (renumbers): {len(superseded)}")
    for s in superseded:
        print("  ~", s)
    print(f"\nSKIPPED (already present): {len(skipped)} -> {skipped}")

    total_au = await col.count_documents({"country_code": "AU", "status": {"$ne": "superseded"}})
    print(f"\nAU active occupations now: {total_au}")


if __name__ == "__main__":
    asyncio.run(main())
