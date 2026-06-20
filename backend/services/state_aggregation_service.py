"""Phase 19.4d — AU State Aggregation Service.

Refreshes denormalized fields on ``au_states_master`` documents by pulling from:
  • vacancy_snapshots.by_state  → ads + monthly_change
  • occupation_master.state_distribution[state_code] → top occupations
  • industry_master (national; per-state distribution not yet captured)
  • regional_labour_market grouped by state → SA4 region list
  • state_nomination_lists (if uploaded, optional)

All writes are wrapped in a Phase 19.6 ``import_batches`` entry so admin can
revoke a bad refresh within 24h.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

STATE_RANKING_MAP = {  # used to scale rating string into sortable int
    "Strong": 4, "Average": 3, "Soft": 2, "Weak": 1, "Tight": 4,
}


async def refresh_state_data(db, state_code: str) -> Dict[str, Any]:
    """Re-aggregate denormalized fields for one state. Idempotent.

    Returns the updated subset of fields (for audit/visibility).
    """
    state_code = (state_code or "").upper()
    state = await db["au_states_master"].find_one({"state_code": state_code})
    if not state:
        return {"ok": False, "error": f"State {state_code} not seeded"}

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Vacancy snapshot
    vac = await db["vacancy_snapshots"].find_one({"is_latest": True}) \
        or await db["vacancy_snapshots"].find_one()
    vacancy_data: Optional[Dict[str, Any]] = None
    if vac and isinstance(vac.get("by_state"), dict):
        ads = vac["by_state"].get(state_code)
        if ads is not None:
            # State-level monthly change is rarely broken out — surface national
            # change as a contextual hint (admin can override later via UI).
            vacancy_data = {
                "monthly_ads": int(ads),
                "national_monthly_change_pct": vac.get("monthly_change_pct"),
                "period": vac.get("period") or vac.get("period_iso"),
                "source": vac.get("source"),
                "last_refreshed": now_iso,
            }

    # 2. Top occupations — scan AU occupation_master for those weighted highest
    # toward this state via `state_distribution` (pct) × national signal.
    top_occupations: List[Dict[str, Any]] = []
    occ_cursor = db["occupation_master"].find(
        {"country_code": "AU", "status": "verified",
         f"jsa_data.state_distribution.{state_code}": {"$gt": 0}},
        {"_id": 0, "code": 1, "title": 1, "jsa_data.state_distribution": 1,
         "abs_data.employment_estimate": 1},
    )
    candidates: List[Dict[str, Any]] = []
    async for o in occ_cursor:
        pct = ((o.get("jsa_data") or {}).get("state_distribution") or {}).get(state_code, 0)
        nat_emp = (o.get("abs_data") or {}).get("employment_estimate") or 0
        est = int(pct * nat_emp / 100) if nat_emp else int(pct * 1000)
        candidates.append({
            "anzsco_code": o.get("code"),
            "title": o.get("title"),
            "state_share_pct": pct,
            "vacancy_count_estimate": est,
        })
    # Fallback: when state_distribution missing, scan again without filter.
    if not candidates:
        async for o in db["occupation_master"].find(
            {"country_code": "AU", "status": "verified"},
            {"_id": 0, "code": 1, "title": 1, "state_distribution": 1,
             "abs_data.employment_estimate": 1},
        ).limit(200):
            pct = (o.get("state_distribution") or {}).get(state_code, 0)
            if not pct:
                continue
            nat_emp = (o.get("abs_data") or {}).get("employment_estimate") or 0
            est = int(pct * nat_emp / 100) if nat_emp else int(pct * 1000)
            candidates.append({
                "anzsco_code": o.get("code"),
                "title": o.get("title"),
                "state_share_pct": pct,
                "vacancy_count_estimate": est,
            })
    candidates.sort(key=lambda c: c["vacancy_count_estimate"], reverse=True)
    top_occupations = candidates[:10]

    # 3. Top industries — industry_master doesn't track per-state yet; surface
    # the national top 5 by `employed_count` with explicit "national" qualifier.
    # When per-state ANZSIC data is uploaded later, this section auto-upgrades.
    top_industries: List[Dict[str, Any]] = []
    ind_cursor = db["industry_master"].find(
        {}, {"_id": 0, "industry_name": 1, "anzsic_code": 1, "slug": 1,
             "employed_count": 1, "employed_by_state": 1}
    ).sort("employed_count", -1).limit(5)
    async for ind in ind_cursor:
        # Use per-state if uploaded; else fall back to national.
        by_state = ind.get("employed_by_state") or {}
        employed = by_state.get(state_code) if by_state else None
        top_industries.append({
            "industry_name": ind.get("industry_name"),
            "anzsic_code": ind.get("anzsic_code"),
            "slug": ind.get("slug"),
            "employed_count": employed or ind.get("employed_count"),
            "is_national": employed is None,
        })

    # 4. SA4 regions for this state — sorted by indicator strength
    sa4_regions: List[Dict[str, Any]] = []
    rlm_cursor = db["regional_labour_market"].find(
        {"state": state_code}, {"_id": 0, "sa4_code": 1, "sa4_name": 1, "rating": 1}
    )
    async for r in rlm_cursor:
        rating = r.get("rating") or "Average"
        sa4_regions.append({
            "sa4_code": r.get("sa4_code"),
            "region_name": r.get("sa4_name"),
            "strength_rating": rating,
            "rank_value": STATE_RANKING_MAP.get(rating, 3),
        })
    sa4_regions.sort(key=lambda x: x["rank_value"], reverse=True)
    sa4_regions = sa4_regions[:12]  # cap for layout

    # 5. State nomination lists (degrades gracefully if collection empty)
    sol_codes: Optional[List[str]] = None
    rol_codes: Optional[List[str]] = None
    state_nom_last_updated: Optional[str] = None
    nom = await db["state_nomination_lists"].find_one({"state_code": state_code})
    if nom:
        sol_codes = nom.get("sol_codes")
        rol_codes = nom.get("rol_codes")
        state_nom_last_updated = nom.get("updated_at") or nom.get("last_updated_at")

    # 6. Open audit batch (Phase 19.6 revocability)
    batch_id = str(uuid.uuid4())
    await db["import_batches"].insert_one({
        "id": batch_id,
        "batch_id": batch_id,
        "scope": f"au_state_aggregation:{state_code}",
        "target_collection": "au_states_master",
        "operation": "refresh",
        "started_at": now_iso,
        "status": "active",
        "writes_count": 1,
        "revocable_until": (datetime.now(timezone.utc).timestamp() + 86400),
        "actor": "state_aggregation_service",
    })

    # 7. Persist
    update_payload = {
        "vacancy_data": vacancy_data,
        "top_occupations": top_occupations,
        "top_industries": top_industries,
        "sa4_regions": sa4_regions,
        "sol_codes": sol_codes,
        "rol_codes": rol_codes,
        "state_nom_last_updated": state_nom_last_updated,
        "last_aggregated_at": now_iso,
        "last_updated_at": now_iso,
        "last_aggregation_batch_id": batch_id,
    }
    await db["au_states_master"].update_one(
        {"state_code": state_code}, {"$set": update_payload}
    )

    return {
        "ok": True,
        "state_code": state_code,
        "batch_id": batch_id,
        "counts": {
            "top_occupations": len(top_occupations),
            "top_industries": len(top_industries),
            "sa4_regions": len(sa4_regions),
            "has_vacancy_data": vacancy_data is not None,
            "has_nomination_lists": sol_codes is not None or rol_codes is not None,
        },
        **update_payload,
    }


async def refresh_all_states(db) -> List[Dict[str, Any]]:
    """Re-aggregate all 8 seeded states. Used by daily cron + manual sweep."""
    results: List[Dict[str, Any]] = []
    async for s in db["au_states_master"].find({}, {"_id": 0, "state_code": 1}):
        results.append(await refresh_state_data(db, s["state_code"]))
    return results
