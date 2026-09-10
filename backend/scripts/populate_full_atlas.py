"""Reset AU Atlas database back to original clean state:
1. Clean out all dummy / extra AU records
2. Ingest original official 708 Home Affairs Skilled Occupations
3. Apply standard official scrapers (VETASSESS, State nominations, SkillSelect, DAMA, ILA)
4. Seed original 44 Assessing Authorities and update counts
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.database import db
from core.scrapers.home_affairs import fetch_raw_records, normalize_record
from seeds.assessing_authorities_au import ensure_seeded_in_db


async def main():
    print("=== 1. Resetting AU occupation_master to clean state ===")
    del_res = await db["occupation_master"].delete_many({"country_code": "AU"})
    print(f"✔ Cleared {del_res.deleted_count} AU records from occupation_master")

    print("\n=== 2. Ingesting original 708 Home Affairs Skilled Occupations ===")
    raw = fetch_raw_records()
    normalized = [normalize_record(r) for r in raw]
    
    by_code: dict[str, dict] = {}
    for n in normalized:
        c = n.get("code")
        if not c or len(c) != 6:
            continue
        if c in by_code and not n.get("title"):
            continue
        by_code[c] = n
    
    print(f"  Total unique Home Affairs codes: {len(by_code)}")
    
    now = datetime.now(timezone.utc).isoformat()
    to_insert = []
    for code, n in by_code.items():
        doc = {
            "country_code": "AU",
            "code": code,
            "title": n.get("title") or "",
            "classification_version": n.get("classification_version") or "ANZSCO 2013",
            "classification_dual_code": n.get("classification_dual_code") or {},
            "anzsco_ref_url": n.get("anzsco_ref_url") or "",
            "visa_pathways": n.get("visa_pathways") or {},
            "pathway_list": n.get("pathway_list") or "",
            "assessing_authority": n.get("assessing_authority") or {},
            "status": "verified",
            "verification": {
                "source": "home_affairs_skilled_occupation_list",
                "auto_verified_at": now,
                "auto_verified_by": "reset_to_original.py",
                "method": "Home Affairs live scrape — official Australian Government source",
            },
            "created_at": now,
            "updated_at": now,
            "last_scraped_at": now,
            "last_scraped_by": "home_affairs_skilled_occupation_list",
        }
        if len(code) == 6 and code.isdigit():
            doc["anzsco_4digit_code"] = code[:4]
            doc["anzsco_major_group_code"] = code[0]
        to_insert.append(doc)

    if to_insert:
        await db["occupation_master"].insert_many(to_insert, ordered=False)
        print(f"✔ Inserted {len(to_insert)} canonical Home Affairs occupations")

    print("\n=== 3. Running official scrapers ===")
    try:
        from core.scrapers.vetassess_groups import apply_to_db as apply_vetassess
        await apply_vetassess(db, dry_run=False, actor="system_reset")
        print("✔ VETASSESS groups applied")
    except Exception as e:
        print(f"VETASSESS note: {e}")

    try:
        from core.scrapers.state_nominations import apply_to_db as apply_states
        await apply_states(db, dry_run=False, actor="system_reset")
        print("✔ State nominations applied")
    except Exception as e:
        print(f"State nominations note: {e}")

    try:
        from core.scrapers.skillselect_tiers import apply_to_db as apply_tiers
        await apply_tiers(db, dry_run=False, actor="system_reset")
        print("✔ SkillSelect tiers applied")
    except Exception as e:
        print(f"SkillSelect note: {e}")

    try:
        from core.scrapers.home_affairs_supplementary import apply_dama_to_db, apply_ila_to_db
        await apply_dama_to_db(db, dry_run=False, actor="system_reset")
        await apply_ila_to_db(db, dry_run=False, actor="system_reset")
        print("✔ DAMA and ILA eligibility applied")
    except Exception as e:
        print(f"DAMA/ILA note: {e}")

    print("\n=== 4. Seeding Assessing Authorities (44 bodies) & Linking ===")
    await ensure_seeded_in_db(db)
    
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

    async for occ in db["occupation_master"].find({"country_code": "AU"}):
        aa = occ.get("assessing_authority") or {}
        m_auth = None
        if isinstance(aa, dict):
            for k in ["short_name", "code", "name"]:
                val = str(aa.get(k) or "").strip()
                if val and val in auth_by_alias:
                    m_auth = auth_by_alias[val]
                    break
                if val and val.upper() in auth_by_alias:
                    m_auth = auth_by_alias[val.upper()]
                    break
        if m_auth:
            await db["occupation_master"].update_one(
                {"_id": occ["_id"]},
                {"$set": {
                    "assessing_authority_id": m_auth["id"],
                    "assessing_authority": {
                        "id": m_auth["id"],
                        "code": m_auth["code"],
                        "name": m_auth["code"],
                        "full_name": m_auth.get("full_name") or m_auth["code"],
                    }
                }}
            )

    # Update counts on authorities
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
    print(f"✔ Original AU Reset complete: Total={total_au}, Verified={verified_au}, Total Linked to Authorities={total_linked}")


if __name__ == "__main__":
    asyncio.run(main())
