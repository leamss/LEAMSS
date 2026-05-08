"""Visa Pathway Comparison — public side-by-side comparison + admin editor.

Public can compare any 2-4 pathways: fees, timelines, eligibility, post-arrival.
Admin can edit pathway data (fees change yearly).

Default seed = 8 popular pathways with current 2026 data.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.database import db
from routers.auth import get_current_user

router = APIRouter(prefix="/visa-compare", tags=["Visa Pathway Comparison"])
pathways_col = db["visa_pathways"]


def _admin_only(u):
    if u.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


# ----------- Seed data (real 2026 ballpark numbers) -----------
SEEDS = [
    {
        "slug": "canada_express_entry",
        "name": "Canada · Express Entry (FSW)",
        "country": "Canada",
        "category": "Permanent Residence",
        "min_age": 18, "max_age": 47,
        "min_education": "Bachelor's Degree",
        "min_work_exp_years": 1,
        "language_required": "IELTS General 6.0 (CLB 7) min",
        "min_funds_inr": 1300000,
        "govt_fee_inr": 110000,
        "leamss_fee_inr": 200000,
        "timeline_months": "8-14",
        "key_benefits": [
            "Permanent Residence from Day 1",
            "Universal healthcare for family",
            "Access to public education",
            "Path to Canadian citizenship in 3 years",
        ],
        "key_drawbacks": [
            "CRS cutoff fluctuates (currently ~480)",
            "Cold winters in many provinces",
        ],
        "post_arrival_jobs": "Strong demand: IT, healthcare, skilled trades, finance",
        "rank": 1,
    },
    {
        "slug": "australia_189",
        "name": "Australia · Subclass 189 (Skilled Independent)",
        "country": "Australia",
        "category": "Permanent Residence",
        "min_age": 18, "max_age": 44,
        "min_education": "Bachelor's Degree",
        "min_work_exp_years": 3,
        "language_required": "IELTS Academic 6.0 / PTE 50 min",
        "min_funds_inr": 1500000,
        "govt_fee_inr": 230000,
        "leamss_fee_inr": 250000,
        "timeline_months": "10-18",
        "key_benefits": [
            "PR with full work rights anywhere in Australia",
            "Medicare healthcare access",
            "Citizenship path in 4 years",
            "Strong AUD currency, high salaries",
        ],
        "key_drawbacks": [
            "Skills assessment required (₹40-80K extra)",
            "Points race — minimum 65 needed (avg invitation 75+)",
        ],
        "post_arrival_jobs": "Hot sectors: nursing, software, accounting, civil engineering",
        "rank": 2,
    },
    {
        "slug": "australia_190",
        "name": "Australia · Subclass 190 (State Nominated)",
        "country": "Australia",
        "category": "Permanent Residence",
        "min_age": 18, "max_age": 44,
        "min_education": "Bachelor's Degree",
        "min_work_exp_years": 3,
        "language_required": "IELTS Academic 6.0 / PTE 50 min",
        "min_funds_inr": 1500000,
        "govt_fee_inr": 230000,
        "leamss_fee_inr": 250000,
        "timeline_months": "8-15",
        "key_benefits": [
            "PR with state nomination boost (+5 points)",
            "Faster than 189 in many cases",
            "All standard PR benefits",
        ],
        "key_drawbacks": [
            "Must commit to nominated state for 2 years",
            "State occupation lists vary",
        ],
        "post_arrival_jobs": "Varies by state — Tasmania/SA generous, NSW/VIC selective",
        "rank": 3,
    },
    {
        "slug": "uk_skilled_worker",
        "name": "UK · Skilled Worker Visa",
        "country": "United Kingdom",
        "category": "Work Visa (5-year route to PR)",
        "min_age": 18, "max_age": 65,
        "min_education": "Job-specific (often Bachelor's)",
        "min_work_exp_years": 0,
        "language_required": "IELTS UKVI 4.0 (B1) min",
        "min_funds_inr": 105000,
        "govt_fee_inr": 200000,
        "leamss_fee_inr": 175000,
        "timeline_months": "2-4 (after job offer)",
        "key_benefits": [
            "Fastest pathway if you have UK job offer",
            "Bring spouse + children",
            "Indefinite Leave to Remain after 5 years",
            "NHS access",
        ],
        "key_drawbacks": [
            "Must have UK employer sponsorship (Tier 2 license)",
            "Salary threshold £38,700+ (raised 2024)",
            "IHS surcharge ~£2,500/yr per family",
        ],
        "post_arrival_jobs": "Already employed at sponsor; switching jobs = new sponsor",
        "rank": 4,
    },
    {
        "slug": "germany_eu_blue_card",
        "name": "Germany · EU Blue Card",
        "country": "Germany",
        "category": "Work Visa (33-month PR path)",
        "min_age": 18, "max_age": 60,
        "min_education": "Bachelor's Degree (recognized)",
        "min_work_exp_years": 0,
        "language_required": "B1 German preferred (English OK with offer)",
        "min_funds_inr": 80000,
        "govt_fee_inr": 12000,
        "leamss_fee_inr": 150000,
        "timeline_months": "3-6 (after job offer)",
        "key_benefits": [
            "PR in 33 months (21 with B1 German)",
            "EU mobility — work in 27 countries",
            "Free education + healthcare",
            "Strong Euro currency",
        ],
        "key_drawbacks": [
            "Must have German employer offer",
            "Salary threshold €43,800+/yr",
            "Bureaucratic paperwork",
        ],
        "post_arrival_jobs": "IT, engineering, healthcare in massive shortage",
        "rank": 5,
    },
    {
        "slug": "usa_eb2_niw",
        "name": "USA · EB2-NIW (National Interest Waiver)",
        "country": "United States",
        "category": "Permanent Residence (Green Card)",
        "min_age": 25, "max_age": 60,
        "min_education": "Master's Degree or Bachelor's + 5yr exp",
        "min_work_exp_years": 5,
        "language_required": "Strong English (no formal test)",
        "min_funds_inr": 400000,
        "govt_fee_inr": 60000,
        "leamss_fee_inr": 600000,
        "timeline_months": "18-36 (priority date dependent)",
        "key_benefits": [
            "Self-petition (no employer needed)",
            "US Green Card directly",
            "Best for researchers, doctors, entrepreneurs",
            "Spouse gets EAD work permit",
        ],
        "key_drawbacks": [
            "India backlog 6-10 years for green card issuance",
            "Strong evidence portfolio required (publications, awards)",
            "High legal fees ($8-15K typical)",
        ],
        "post_arrival_jobs": "Any employer, any state — full flexibility",
        "rank": 6,
    },
    {
        "slug": "new_zealand_swv",
        "name": "New Zealand · Skilled Migrant Category",
        "country": "New Zealand",
        "category": "Permanent Residence",
        "min_age": 18, "max_age": 55,
        "min_education": "Bachelor's Degree",
        "min_work_exp_years": 3,
        "language_required": "IELTS 6.5 (General/Academic)",
        "min_funds_inr": 800000,
        "govt_fee_inr": 240000,
        "leamss_fee_inr": 220000,
        "timeline_months": "12-18",
        "key_benefits": [
            "PR with all rights, includes citizenship in 5 years",
            "Beautiful country, work-life balance",
            "Healthcare + education for family",
        ],
        "key_drawbacks": [
            "Smaller job market than AU/CA",
            "EOI invitation needed (points-based)",
            "Higher cost of living in Auckland",
        ],
        "post_arrival_jobs": "Construction, healthcare, IT, dairy industry",
        "rank": 7,
    },
    {
        "slug": "canada_pnp",
        "name": "Canada · Provincial Nominee Program (PNP)",
        "country": "Canada",
        "category": "Permanent Residence",
        "min_age": 18, "max_age": 50,
        "min_education": "Diploma+ depending on province",
        "min_work_exp_years": 1,
        "language_required": "IELTS General 5.0+ (varies by province)",
        "min_funds_inr": 1100000,
        "govt_fee_inr": 145000,
        "leamss_fee_inr": 220000,
        "timeline_months": "12-20",
        "key_benefits": [
            "Lower CRS / language requirements than Express Entry",
            "+600 CRS points bonus once nominated",
            "Specific province targeting (Saskatchewan, Manitoba, NB easiest)",
        ],
        "key_drawbacks": [
            "Must commit to province for ≥2 years",
            "Slower than Express Entry",
            "Some streams need job offer or work experience in province",
        ],
        "post_arrival_jobs": "Province-dependent; in-demand trades, healthcare, IT",
        "rank": 8,
    },
]


# ----------- Public endpoints -----------

@router.get("/pathways")
async def list_pathways(country: Optional[str] = None):
    """Public — list all active pathways. Optional ?country=Canada filter."""
    # Auto-seed on first call if empty
    count = await pathways_col.count_documents({})
    if count == 0:
        for s in SEEDS:
            await pathways_col.insert_one({
                **s, "id": str(uuid.uuid4()), "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })

    q = {"is_active": True}
    if country:
        q["country"] = country
    items = await pathways_col.find(q, {"_id": 0}).sort("rank", 1).to_list(50)
    for it in items:
        for k in ("created_at", "updated_at"):
            if hasattr(it.get(k), "isoformat"):
                it[k] = it[k].isoformat()
    return {"count": len(items), "pathways": items}


@router.get("/compare")
async def compare(slugs: str = Query(..., description="Comma-separated, 2-4 pathway slugs")):
    """Public — fetch full data for selected pathways for side-by-side render."""
    parts = [s.strip() for s in slugs.split(",") if s.strip()]
    if len(parts) < 2 or len(parts) > 4:
        raise HTTPException(status_code=400, detail="Provide 2-4 pathway slugs")
    items = await pathways_col.find({"slug": {"$in": parts}, "is_active": True}, {"_id": 0}).to_list(10)
    if len(items) < 2:
        raise HTTPException(status_code=404, detail="Not enough valid pathways found")
    for it in items:
        for k in ("created_at", "updated_at"):
            if hasattr(it.get(k), "isoformat"):
                it[k] = it[k].isoformat()
    # Order matches user-provided slug order
    items.sort(key=lambda x: parts.index(x["slug"]) if x["slug"] in parts else 99)
    return {"count": len(items), "pathways": items}


# ----------- Admin endpoints -----------

class PathwayUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    min_education: Optional[str] = None
    min_work_exp_years: Optional[float] = None
    language_required: Optional[str] = None
    min_funds_inr: Optional[float] = None
    govt_fee_inr: Optional[float] = None
    leamss_fee_inr: Optional[float] = None
    timeline_months: Optional[str] = None
    key_benefits: Optional[List[str]] = None
    key_drawbacks: Optional[List[str]] = None
    post_arrival_jobs: Optional[str] = None
    rank: Optional[int] = None
    is_active: Optional[bool] = None


@router.put("/pathways/{slug}")
async def update_pathway(slug: str, body: PathwayUpdate, current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    upd = {k: v for k, v in body.dict().items() if v is not None}
    if not upd:
        raise HTTPException(status_code=400, detail="No fields to update")
    upd["updated_at"] = datetime.now(timezone.utc)
    res = await pathways_col.update_one({"slug": slug}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pathway not found")
    item = await pathways_col.find_one({"slug": slug}, {"_id": 0})
    if hasattr(item.get("updated_at"), "isoformat"):
        item["updated_at"] = item["updated_at"].isoformat()
    return {"ok": True, "pathway": item}


@router.post("/reseed")
async def reseed_pathways(current_user: dict = Depends(get_current_user)):
    """Admin — wipe and re-insert default seed (yearly fee refresh utility)."""
    _admin_only(current_user)
    await pathways_col.delete_many({})
    for s in SEEDS:
        await pathways_col.insert_one({
            **s, "id": str(uuid.uuid4()), "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
    return {"ok": True, "inserted": len(SEEDS)}
