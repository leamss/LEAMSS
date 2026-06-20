"""Phase 19.4d — AU States Master Seed.

Seeds 8 canonical AU states into `au_states_master` with hardcoded population,
capital, tagline, immigration_friendly_score, primary visa subclasses.
Idempotent — safe to re-run. Aggregated data (vacancy, top occupations, etc.)
is populated lazily by ``services/state_aggregation_service.refresh_state_data()``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

# 8 AU states/territories with canonical SEO + LEAMSS pitch data.
SEED_STATES: List[Dict[str, Any]] = [
    {
        "state_code": "NSW",
        "state_name": "New South Wales",
        "slug": "new-south-wales",
        "capital_city": "Sydney",
        "population": 8_200_000,
        "area_sq_km": 800_641,
        "tagline": "Australia's Largest Economy — Tech, Finance, Healthcare Hub",
        "immigration_friendly_score": 8.0,
        "primary_visa_subclasses": ["190", "491", "189"],
        "cost_of_living_index": 105,
        "lifestyle_highlights": ["World-class Sydney harbour", "Top-ranked universities", "Diverse Indian community"],
    },
    {
        "state_code": "VIC",
        "state_name": "Victoria",
        "slug": "victoria",
        "capital_city": "Melbourne",
        "population": 6_700_000,
        "area_sq_km": 227_416,
        "tagline": "Cultural Capital, Strong Skilled Migration Lists",
        "immigration_friendly_score": 8.0,
        "primary_visa_subclasses": ["190", "491"],
        "cost_of_living_index": 100,
        "lifestyle_highlights": ["#1 liveable city ranking", "Best coffee culture", "Strong public transport"],
    },
    {
        "state_code": "QLD",
        "state_name": "Queensland",
        "slug": "queensland",
        "capital_city": "Brisbane",
        "population": 5_500_000,
        "area_sq_km": 1_852_642,
        "tagline": "Sunshine State, Booming Construction + Healthcare",
        "immigration_friendly_score": 7.0,
        "primary_visa_subclasses": ["190", "491", "188"],
        "cost_of_living_index": 92,
        "lifestyle_highlights": ["Year-round sunshine", "Brisbane 2032 Olympics boom", "Gold Coast lifestyle"],
    },
    {
        "state_code": "SA",
        "state_name": "South Australia",
        "slug": "south-australia",
        "capital_city": "Adelaide",
        "population": 1_800_000,
        "area_sq_km": 1_044_353,
        "tagline": "Affordable Living, Generous Regional Nomination",
        "immigration_friendly_score": 9.0,
        "primary_visa_subclasses": ["190", "491", "494"],
        "cost_of_living_index": 85,
        "lifestyle_highlights": ["Most affordable capital", "Designated regional area — extra 5 points", "Wine country"],
    },
    {
        "state_code": "WA",
        "state_name": "Western Australia",
        "slug": "western-australia",
        "capital_city": "Perth",
        "population": 2_700_000,
        "area_sq_km": 2_527_013,
        "tagline": "Mining + Resources Boom, Higher Wages",
        "immigration_friendly_score": 7.0,
        "primary_visa_subclasses": ["190", "491", "494"],
        "cost_of_living_index": 95,
        "lifestyle_highlights": ["Highest median wages", "Mining/LNG opportunities", "Pristine beaches"],
    },
    {
        "state_code": "TAS",
        "state_name": "Tasmania",
        "slug": "tasmania",
        "capital_city": "Hobart",
        "population": 570_000,
        "area_sq_km": 68_401,
        "tagline": "Regional Designation — Lower Threshold for 491",
        "immigration_friendly_score": 9.5,
        "primary_visa_subclasses": ["491", "190", "494"],
        "cost_of_living_index": 88,
        "lifestyle_highlights": ["Entire state designated regional", "Pure air + clean food", "Small-town community feel"],
    },
    {
        "state_code": "NT",
        "state_name": "Northern Territory",
        "slug": "northern-territory",
        "capital_city": "Darwin",
        "population": 250_000,
        "area_sq_km": 1_419_630,
        "tagline": "Regional Designation, Multiple Nomination Streams",
        "immigration_friendly_score": 9.5,
        "primary_visa_subclasses": ["491", "190", "494"],
        "cost_of_living_index": 102,
        "lifestyle_highlights": ["Designated regional area", "Lower nomination thresholds", "Strong defence + mining"],
    },
    {
        "state_code": "ACT",
        "state_name": "Australian Capital Territory",
        "slug": "australian-capital-territory",
        "capital_city": "Canberra",
        "population": 460_000,
        "area_sq_km": 2_358,
        "tagline": "Government Hub, Strong PR Pathway",
        "immigration_friendly_score": 8.5,
        "primary_visa_subclasses": ["190", "491"],
        "cost_of_living_index": 103,
        "lifestyle_highlights": ["High average income", "Government-job heavy", "Cleanest air of any capital"],
    },
]


async def seed_au_states(db) -> Dict[str, Any]:
    """Idempotent insert of 8 AU states. Returns counts of created vs skipped.

    Note: Marks each as ``status='draft'`` until admin verifies via existing
    Authority/Policy pattern. Aggregated data fields left empty for
    ``state_aggregation_service.refresh_state_data()`` to fill.
    """
    created: List[str] = []
    skipped: List[str] = []
    now = datetime.now(timezone.utc).isoformat()
    for seed in SEED_STATES:
        existing = await db["au_states_master"].find_one({"state_code": seed["state_code"]})
        if existing:
            skipped.append(seed["state_code"])
            continue
        doc = {
            "id": str(uuid.uuid4()),
            **seed,
            "country_code": "AU",
            "has_state_nomination": True,
            "vacancy_data": None,           # filled by aggregator
            "top_occupations": [],           # filled by aggregator
            "top_industries": [],            # filled by aggregator
            "sa4_regions": [],               # filled by aggregator
            "sol_codes": None,               # depends on state_nomination_lists uploads
            "rol_codes": None,
            "priority_skills_list": None,
            "state_nom_last_updated": None,
            "status": "draft",
            "created_at": now,
            "last_updated_at": now,
            "last_aggregated_at": None,
        }
        await db["au_states_master"].insert_one(doc)
        created.append(seed["state_code"])
    # Indexes (idempotent)
    await db["au_states_master"].create_index("state_code", unique=True)
    await db["au_states_master"].create_index("slug", unique=True)
    return {"created": created, "skipped": skipped, "total": 8}
