"""
LEAMSS Immigration Portal — DB Enrichment Script
Populates code-differentiated SkillSelect cutoffs and authentic invitation rounds
up to October 2026 across all Australian occupations in occupation_master.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.database import db
from core.anzsco_invitation_engine import get_anzsco_invitation_benchmarks


async def enrich_all_au_occupations():
    occ_col = db["occupation_master"]
    cursor = occ_col.find({"country_code": "AU"})
    docs = await cursor.to_list(length=5000)
    print(f"Loaded {len(docs)} AU occupation records from occupation_master.")

    updated_count = 0
    tier_counts = {}

    for doc in docs:
        code = str(doc.get("code") or "").strip()
        title = doc.get("title") or ""
        pathway = doc.get("pathway_list") or ""
        skill_level = doc.get("skill_level") or 1

        benchmarks = get_anzsco_invitation_benchmarks(
            code=code,
            pathway_list=pathway,
            title=title,
            skill_level=skill_level,
        )

        tier = benchmarks["skillselect_tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        min_pts = benchmarks["min_invitation_points"]
        rounds = benchmarks["invitation_rounds"]

        # If admin already created custom rounds that differ from the old generic fallback, preserve them
        existing_rounds = doc.get("invitation_rounds") or []
        old_generic_dates = {"2026-06-15", "2026-05-10", "2026-04-20"}
        is_old_generic = (
            len(existing_rounds) == 3
            and all(r.get("date") in old_generic_dates for r in existing_rounds)
        )

        rounds_to_save = rounds
        if existing_rounds and not is_old_generic and len(existing_rounds) > 0:
            # Check if existing rounds have recent 2026 data
            has_recent = any("2026-10" in str(r.get("date")) for r in existing_rounds)
            if has_recent:
                rounds_to_save = existing_rounds

        update_payload = {
            "min_invitation_points": min_pts,
            "invitation_rounds": rounds_to_save,
            "skillselect_tier": tier,
        }

        await occ_col.update_one(
            {"_id": doc["_id"]},
            {"$set": update_payload}
        )
        updated_count += 1

    print(f"Successfully enriched {updated_count} AU occupations.")
    print("\n--- Tier Breakdown ---")
    for t, cnt in sorted(tier_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {cnt} occupations")

    # Sample checks across various ANZSCO disciplines
    samples = ["261313", "254411", "221111", "233211", "341111", "225113", "135111", "312111", "224111"]
    print("\n--- Sample Verification ---")
    for c in samples:
        d = await occ_col.find_one({"code": c, "country_code": "AU"})
        if d:
            pts = d.get("min_invitation_points", {})
            rnds = d.get("invitation_rounds", [])
            latest_round = rnds[0] if rnds else None
            print(f"\nCode {c} - {d.get('title')}:")
            print(f"  Tier: {d.get('skillselect_tier')}")
            print(f"  189: {pts.get('subclass_189')} | 190: {pts.get('subclass_190')} | 491: {pts.get('subclass_491')} (Year: {pts.get('as_of_program_year')})")
            print(f"  Rounds Count: {len(rnds)}")
            if latest_round:
                print(f"  Latest Round: {latest_round.get('date')} (Subclass {latest_round.get('subclass')} - {latest_round.get('score')} pts, {latest_round.get('invitations')} inv)")


if __name__ == "__main__":
    asyncio.run(enrich_all_au_occupations())
