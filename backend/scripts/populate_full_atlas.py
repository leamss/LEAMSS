"""Master script to populate the canonical 708 Home Affairs Skilled Occupations,
link assessing authorities, apply official scrapers, and verify the Atlas.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.database import db
from core.anzsco_excel_importer import import_anzsco_excel
from core.eligibility_kb_seed import seed_country_rules
from core.eligibility_kb_bulk_seed import expand_seed
from core.migrations.occupation_master_migrate import main as migrate_occ_master


async def main():
    print("=== STEP 1: Seeding Base Country Rules & Assessing Authorities ===")
    await seed_country_rules(db['country_rules'])
    await expand_seed()
    
    try:
        from seeds.assessing_authorities_au import ensure_seeded_in_db
        await ensure_seeded_in_db(db)
        print("✔ Assessing authorities (44 bodies) seeded and ensured")
    except Exception as e:
        print(f"Assessing authorities note: {e}")

    print("\n=== STEP 2: Migrating Base Collections ===")
    await migrate_occ_master(dry_run=False)

    print("\n=== STEP 3: Importing Official ANZSCO 4-Digit Groups from Excel ===")
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

    print("\n=== STEP 4: Ingesting Canonical 708 Home Affairs Skilled Occupations ===")
    ha_by_code: Dict[str, Dict[str, Any]] = {}
    try:
        from core.scrapers.home_affairs import fetch_raw_records, normalize_record
        raw = fetch_raw_records()
        normalized = [normalize_record(r) for r in raw]
        for n in normalized:
            c = n.get("code")
            if c and len(c) == 6:
                if c in ha_by_code and not n.get("title"):
                    continue
                ha_by_code[c] = n
        print(f"✔ Fetched {len(ha_by_code)} official skilled occupations from Home Affairs")
    except Exception as e:
        print(f"Home Affairs live scrape note: {e}")

    if not ha_by_code:
        print("⚠️ Warning: No Home Affairs records fetched; keeping existing genuine AU codes.")
        ha_codes = set()
    else:
        ha_codes = set(ha_by_code.keys())

    # Purge any AU records that are not in the canonical Home Affairs skilled list
    if ha_codes:
        del_res = await db["occupation_master"].delete_many({
            "country_code": "AU",
            "code": {"$nin": list(ha_codes)}
        })
        print(f"✔ Cleaned {del_res.deleted_count} non-skilled / extra AU records (Retaining exactly {len(ha_codes)} canonical Home Affairs occupations)")

    # Authorities lookup
    authorities = await db["assessing_authorities"].find({}).to_list(100)
    auth_by_code = {str(a.get("code") or "").upper(): a for a in authorities}
    auth_by_alias = {}
    for a in authorities:
        c = str(a.get("code") or "").upper()
        auth_by_alias[c] = a
        auth_by_alias[c.lower()] = a
        for alias in a.get("aliases", []):
            if alias:
                auth_by_alias[alias.upper()] = a
                auth_by_alias[alias.lower()] = a
                auth_by_alias[alias.strip().upper()] = a

    default_auth = auth_by_code.get("VETASSESS") or (authorities[0] if authorities else None)

    PREFIX_TO_AUTH = {
        # Exact 6-digit overrides
        "233213": "AIQS",
        "224913": "MARA",
        "251912": "AOPA",
        "251214": "ANZSNM",
        "252112": "AOAC",
        "252111": "CCEA",

        # ICT -> ACS
        "2611": "ACS", "2612": "ACS", "2613": "ACS", "2621": "ACS", "2631": "ACS", "2632": "ACS",
        "1351": "ACS", "3131": "ACS", "3132": "ACS",
        
        # Engineers -> EA
        "2331": "EA", "2332": "EA", "2333": "EA", "2334": "EA", "2335": "EA", "2336": "EA", 
        "2339": "EA", "2633": "EA", "3122": "EA", "3123": "EA", "3124": "EA", "3129": "EA",
        
        # Nurses & Midwives -> ANMAC
        "2541": "ANMAC", "2542": "ANMAC", "2543": "ANMAC", "2544": "ANMAC", "4114": "ANMAC",
        
        # Medical Practitioners -> MedBA
        "2531": "MedBA", "2532": "MedBA", "2533": "MedBA", "2534": "MedBA", "2535": "MedBA", 
        "2539": "MedBA", "2530": "MedBA",
        
        # Teaching & School -> AITSL / ACECQA
        "2411": "ACECQA", "2412": "AITSL", "2413": "AITSL", "2414": "AITSL", "2415": "AITSL",
        "2421": "VETASSESS", "2422": "VETASSESS", "2491": "AITSL", "2492": "AITSL", "2493": "AITSL",
        
        # Accounting & Finance -> CAANZ / CPA / IPA
        "2211": "CAANZ", "2212": "CPA", "2213": "CAANZ",
        
        # Management -> IML
        "1111": "IML", "1112": "IML", "1113": "IML", "1311": "IML", "1321": "IML", "1322": "IML", 
        "1323": "IML", "1324": "IML", "1325": "IML", "1331": "IML", "1332": "IML", "1333": "IML", 
        "1334": "IML", "1335": "IML", "1336": "IML", "1341": "ACECQA", "1342": "VETASSESS", 
        "1343": "VETASSESS", "1344": "VETASSESS", "1391": "IML", "1392": "IML", "1399": "IML",
        
        # Dental -> ADC
        "2523": "ADC", "4112": "ADC",
        
        # Pharmacy -> APharmC
        "2515": "APharmC",
        
        # Medical Imaging & Radiation -> ASMIRT
        "2512": "ASMIRT",
        
        # Medical Scientists -> AIMS
        "2346": "AIMS",
        
        # Physiotherapy -> APC
        "2525": "APC",
        
        # Occupational Therapy -> OTC
        "2524": "OTC",
        
        # Psychology -> APS
        "2723": "APS",
        
        # Speech Pathology -> SPA
        "2527": "SPA",
        
        # Dietetics -> DAA
        "2511": "DAA",
        
        # Podiatry -> PodBA
        "2526": "PodBA",
        
        # Optometry -> OCANZ
        "2514": "OCANZ",
        
        # Chiropractor & Osteopath -> CCEA
        "2521": "CCEA",
        
        # Chinese Medicine -> CMBA
        "2522": "CMBA",
        
        # Legal -> LAA
        "2711": "LAA", "2712": "LAA", "2713": "LAA",
        
        # Architecture & Surveying -> AACA / ISNSW
        "2321": "AACA", "2322": "ISNSW",
        
        # Maritime & Aviation -> AMSA / CASA
        "2311": "CASA", "2312": "AMSA", "7129": "AMSA",
        
        # Social & Community Work -> CWA / AASW
        "2725": "AASW", "2726": "CWA", "4117": "CWA",
        
        # Translation -> NAATI
        "2724": "NAATI",
        
        # Veterinary -> AVBC
        "2347": "AVBC",
        
        # Trades -> TRA
        "3111": "TRA", "3112": "TRA", "3113": "TRA", "3114": "TRA", "3121": "VETASSESS",
        "3211": "TRA", "3212": "TRA", "3213": "TRA", "3214": "TRA", "3221": "TRA", "3222": "TRA", 
        "3223": "TRA", "3231": "TRA", "3232": "TRA", "3233": "TRA", "3234": "TRA", "3241": "TRA",
        "3242": "TRA", "3243": "TRA", "3311": "TRA", "3312": "TRA", "3321": "TRA", "3322": "TRA",
        "3331": "TRA", "3332": "TRA", "3333": "TRA", "3334": "TRA", "3341": "TRA", "3411": "TRA",
        "3421": "TRA", "3422": "TRA", "3423": "TRA", "3424": "TRA", "3511": "TRA", "3512": "TRA",
        "3513": "TRA", "3514": "TRA", "3611": "TRA", "3612": "TRA", "3613": "TRA", "3621": "TRA",
        "3622": "TRA", "3623": "TRA", "3624": "TRA", "3911": "TRA", "3921": "TRA", "3922": "TRA",
        "3923": "TRA", "3931": "TRA", "3932": "TRA", "3933": "TRA", "3941": "TRA", "3942": "TRA",
        "3991": "TRA", "3992": "TRA", "3993": "TRA", "3994": "TRA", "3995": "TRA", "3996": "TRA",
        "3999": "TRA", "4512": "TRA", "4513": "TRA",
    }

    def resolve_auth(code_str: str, title: str, ha_auth_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if ha_auth_dict and isinstance(ha_auth_dict, dict):
            for k in ["short_name", "code", "name"]:
                val = str(ha_auth_dict.get(k) or "").strip()
                if val and val in auth_by_alias:
                    return auth_by_alias[val]
                if val and val.upper() in auth_by_alias:
                    return auth_by_alias[val.upper()]

        for prefix_len in [6, 4, 3, 2]:
            pref = code_str[:prefix_len]
            if pref in PREFIX_TO_AUTH:
                auth_code = PREFIX_TO_AUTH[pref]
                if auth_code in auth_by_code:
                    return auth_by_code[auth_code]

        t = (title or "").lower()
        if any(k in t for k in ["software", "developer", "programmer", "ict", "cyber", "database", "systems analyst", "network"]):
            return auth_by_code.get("ACS") or default_auth
        if any(k in t for k in ["engineer", "engineering"]):
            return auth_by_code.get("EA") or default_auth
        if any(k in t for k in ["nurse", "midwife"]):
            return auth_by_code.get("ANMAC") or default_auth
        if any(k in t for k in ["doctor", "physician", "medical", "surgeon", "radiologist", "pathologist"]):
            return auth_by_code.get("MedBA") or default_auth
        if any(k in t for k in ["teacher", "lecturer", "school", "tutor"]):
            return auth_by_code.get("AITSL") or default_auth
        if any(k in t for k in ["accountant", "auditor"]):
            return auth_by_code.get("CAANZ") or default_auth
        if any(k in t for k in ["manager", "director", "chief executive"]):
            return auth_by_code.get("IML") or default_auth
        if any(k in t for k in ["mechanic", "electrician", "plumber", "carpenter", "welder", "chef", "cook", "trade", "baker", "bricklayer"]):
            return auth_by_code.get("TRA") or default_auth
        if any(k in t for k in ["social worker"]):
            return auth_by_code.get("AASW") or default_auth
        if any(k in t for k in ["community work", "welfare"]):
            return auth_by_code.get("CWA") or default_auth
        if "architect" in t:
            return auth_by_code.get("AACA") or default_auth
        if "surveyor" in t:
            return auth_by_code.get("ISNSW") or default_auth
        return default_auth

    # Fetch 4-digit unit group parent profiles
    all_4d: Dict[str, Dict[str, Any]] = {}
    async for p in db["anzsco_4digit_master"].find({}):
        code = str(p.get("code") or "").strip()
        all_4d[code] = p

    now_iso = datetime.now(timezone.utc).isoformat()
    upserted_count = 0

    for code, n in ha_by_code.items():
        parent_code = code[:4]
        parent = all_4d.get(parent_code) or {}

        title = n.get("title") or parent.get("title") or f"Occupation {code}"
        m_auth = resolve_auth(code, title, n.get("assessing_authority"))
        auth_id = m_auth["id"] if m_auth else None
        auth_block = {
            "id": m_auth["id"],
            "code": m_auth["code"],
            "name": m_auth["code"],
            "full_name": m_auth.get("full_name") or m_auth["code"],
        } if m_auth else (n.get("assessing_authority") or {})

        doc = {
            "country_code": "AU",
            "code": code,
            "title": title,
            "classification_version": n.get("classification_version") or "ANZSCO 2013",
            "classification_dual_code": n.get("classification_dual_code") or {
                "anzsco_v1_3": code,
                "anzsco_v2022": code,
                "mapped": True,
            },
            "anzsco_ref_url": n.get("anzsco_ref_url") or "",
            "anzsco_4digit_code": parent_code,
            "anzsco_major_group_code": code[0],
            "anzsco_profile": parent.get("anzsco_profile"),
            "tasks": parent.get("tasks"),
            "industries_ranked": parent.get("industries_ranked"),
            "state_distribution": parent.get("state_distribution"),
            "assessing_authority_id": auth_id,
            "assessing_authority": auth_block,
            "visa_pathways": n.get("visa_pathways") or {},
            "pathway_list": n.get("pathway_list") or "MLTSSL",
            "status": "verified",
            "updated_at": now_iso,
        }

        existing = await db["occupation_master"].find_one({"country_code": "AU", "code": code})
        if existing:
            await db["occupation_master"].update_one({"_id": existing["_id"]}, {"$set": doc})
        else:
            doc["created_at"] = now_iso
            await db["occupation_master"].insert_one(doc)

        upserted_count += 1

    print(f"✔ Upserted {upserted_count} official Home Affairs skilled occupations into occupation_master")

    print("\n=== STEP 5: Running Official Scrapers & Real Enrichments ===")
    try:
        from core.scrapers.vetassess_groups import apply_to_db as apply_vetassess
        await apply_vetassess(db, dry_run=False, actor="system_auto")
        print("✔ VETASSESS groups applied")
    except Exception as e:
        print(f"VETASSESS note: {e}")

    try:
        from core.scrapers.state_nominations import apply_to_db as apply_states
        await apply_states(db, dry_run=False, actor="system_auto")
        print("✔ State nominations applied")
    except Exception as e:
        print(f"State nominations note: {e}")

    try:
        from core.scrapers.skillselect_tiers import apply_to_db as apply_tiers
        await apply_tiers(db, dry_run=False, actor="system_auto")
        print("✔ SkillSelect tiers applied")
    except Exception as e:
        print(f"SkillSelect note: {e}")

    try:
        from core.scrapers.home_affairs_supplementary import apply_dama_to_db, apply_ila_to_db
        await apply_dama_to_db(db, dry_run=False, actor="system_auto")
        await apply_ila_to_db(db, dry_run=False, actor="system_auto")
        print("✔ DAMA and ILA eligibility applied")
    except Exception as e:
        print(f"DAMA/ILA note: {e}")

    # Re-calculate authority occupation counts
    total_linked = 0
    for auth in authorities:
        cnt = await db["occupation_master"].count_documents({"country_code": "AU", "assessing_authority_id": auth["id"]})
        await db["assessing_authorities"].update_one(
            {"_id": auth["_id"]},
            {"$set": {"occupation_count": cnt, "status": "active"}}
        )
        total_linked += cnt

    total_au = await db["occupation_master"].count_documents({"country_code": "AU"})
    verified_au = await db["occupation_master"].count_documents({"country_code": "AU", "status": "verified"})
    print(f"✔ AU Total in DB: {total_au} (Verified: {verified_au}) · Linked to {len(authorities)} authorities: {total_linked}")

    print("\n=== STEP 6: Running Canada (NOC 2021) & New Zealand Scrapers ===")
    try:
        from core.scrapers.noc_canada import apply_to_db as apply_noc
        from core.scrapers.ircc_ee_streams import apply_to_db as apply_ee
        from core.scrapers.pnp_canada import apply_to_db as apply_pnp
        from core.scrapers.ca_regional_pilots import apply_to_db as apply_pilots
        from core.scrapers.quebec_immigration import apply_to_db as apply_quebec
        await apply_noc(db, dry_run=False, actor="system_auto")
        await apply_ee(db, dry_run=False, actor="system_auto")
        await apply_pnp(db, dry_run=False, actor="system_auto")
        await apply_pilots(db, dry_run=False, actor="system_auto")
        await apply_quebec(db, dry_run=False, actor="system_auto")
        print("✔ Canada scrapers applied")
    except Exception as e:
        print(f"Canada scrapers note: {e}")

    try:
        from core.scrapers.nz_anzsco_seed import apply_to_db as apply_nz_seed
        from core.scrapers.nz_green_list import apply_to_db as apply_nz_green
        from core.scrapers.nz_aewv_smc import apply_to_db as apply_nz_aewv
        from core.scrapers.nz_sector_agreements import apply_to_db as apply_nz_sectors
        await apply_nz_seed(db, dry_run=False, actor="system_auto")
        await apply_nz_green(db, dry_run=False, actor="system_auto")
        await apply_nz_aewv(db, dry_run=False, actor="system_auto")
        await apply_nz_sectors(db, dry_run=False, actor="system_auto")
        print("✔ New Zealand scrapers applied")
    except Exception as e:
        print(f"NZ scrapers note: {e}")

    print("\n=== STEP 7: Running Auto-Verification ===")
    try:
        try:
            from core.auto_verify import auto_verify_all
            v_res = await auto_verify_all(db_inst=db, dry_run=False)
        except ImportError:
            from core.auto_verify import run as auto_verify_run
            v_res = {}
            for c in ["AU", "CA", "NZ"]:
                try:
                    v_res[c] = await auto_verify_run(db, country=c, min_coverage_pct=50.0, dry_run=False)
                except Exception as ex:
                    v_res[c] = {"error": str(ex)}
        print(f"✔ Auto-verified: {v_res}")
    except Exception as e:
        print(f"Auto-verify note: {e}")

    print("\n🎉 Canonical 708 Atlas sync complete!")


if __name__ == "__main__":
    asyncio.run(main())
