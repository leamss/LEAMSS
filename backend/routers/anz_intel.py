"""Phase 9 — ANZSCO Intelligence (Audit Layer).

READ-ONLY audit endpoints that show LEAMSS sales/admin team the exact
coverage gap between two existing collections:

  • `anzsco_4digit_master`  — 1,236 records from jobsandskills.gov.au
                              (ABS Feb 2026 ANZSCO catalogue, 4-digit groups)
  • `occupation_master`     — 6-digit migration-specific entries
                              (visa pathways, assessing authority, status)

Used by `/admin/anz-intel/audit` admin page to visualise which fields
are present/missing for each occupation, BEFORE we begin scraping/enrichment.

ZERO mutations — purely diagnostic.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/anz-intel", tags=["anz-intel"])

# Fields we expect to eventually have populated per occupation
TRACKED_FIELDS = [
    "anzsco_profile",          # salary / employment / demographics (from 4-digit)
    "tasks",                   # job tasks list
    "industries_ranked",       # top industries
    "state_distribution",      # state-wise employment %
    "assessing_authority",     # ACS / VETASSESS / EA etc
    "skill_assessment_details",# group classification (A/B/C/D/E/F for VETASSESS)
    "visa_pathways",           # 189/190/491/482/186 eligibility
    "state_territory_eligibility",  # NSW/VIC/etc nomination lists
    "skillselect_tier",        # SkillSelect Tier 1-4 (NEW — not yet populated)
    "latest_invitation_min_points",  # NEW — from Home Affairs invitation rounds
    "dama_inclusion",          # NEW — DAMA agreement membership
    "ila_inclusion",           # NEW — Industry Labour Agreement
    "classification_dual_code",# NEW — v1.3 ↔ v2022 mapping
]

ADMIN_ROLES = {"admin", "admin_owner"}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _has_value(doc: dict, field: str) -> bool:
    """Determine whether a tracked field is meaningfully populated."""
    v = doc.get(field)
    if v is None or v == "" or v == [] or v == {}:
        return False
    # For nested dicts/lists ensure they have content
    if isinstance(v, dict) and not any(v.values()):
        return False
    return True


@router.get("/audit-summary")
async def audit_summary(current_user: dict = Depends(get_current_user)):
    """High-level KB coverage summary — used for hero stats on audit page."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    # 4-digit parent collection
    total_4d = await db["anzsco_4digit_master"].count_documents({})

    # 6-digit child collection (occupation_master) — AU only
    total_6d_au = await db["occupation_master"].count_documents({"country_code": "AU"})
    verified_6d_au = await db["occupation_master"].count_documents(
        {"country_code": "AU", "status": "verified"}
    )
    draft_6d_au = await db["occupation_master"].count_documents(
        {"country_code": "AU", "status": "draft"}
    )

    # Count 4-digit codes that have AT LEAST ONE 6-digit child
    cursor = db["occupation_master"].aggregate([
        {"$match": {"country_code": "AU"}},
        {"$project": {"_id": 0, "code": 1}},
        {"$group": {"_id": {"$substr": ["$code", 0, 4]}}},
    ])
    parents_with_child = {row["_id"] async for row in cursor}

    # Per-field coverage on 6-digit AU records
    field_counts: Dict[str, int] = {f: 0 for f in TRACKED_FIELDS}
    proj = {"_id": 0, **{f: 1 for f in TRACKED_FIELDS}}
    async for d in db["occupation_master"].find({"country_code": "AU"}, proj):
        for f in TRACKED_FIELDS:
            if _has_value(d, f):
                field_counts[f] += 1

    return {
        "totals": {
            "anzsco_4digit_groups": total_4d,
            "occupation_master_au_total": total_6d_au,
            "occupation_master_au_verified": verified_6d_au,
            "occupation_master_au_draft": draft_6d_au,
            "4digit_groups_with_child": len(parents_with_child),
            "4digit_groups_without_child": total_4d - len(parents_with_child),
        },
        "field_coverage_au": [
            {
                "field": f,
                "label": _humanize(f),
                "count_present": field_counts[f],
                "count_missing": total_6d_au - field_counts[f],
                "pct_present": round((field_counts[f] / total_6d_au * 100), 1) if total_6d_au else 0,
                "source_hint": _source_hint(f),
            }
            for f in TRACKED_FIELDS
        ],
    }


@router.get("/audit-rows")
async def audit_rows(
    country: str = Query("AU"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    only_status: Optional[str] = Query(None, description="verified|draft|all"),
    search: Optional[str] = Query(None, description="Search by code or title"),
    current_user: dict = Depends(get_current_user),
):
    """Detailed per-occupation audit table — used as the main heatmap grid."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    match: Dict[str, Any] = {"country_code": country}
    if only_status and only_status != "all":
        match["status"] = only_status
    if search:
        match["$or"] = [
            {"code": {"$regex": search, "$options": "i"}},
            {"title": {"$regex": search, "$options": "i"}},
        ]

    total = await db["occupation_master"].count_documents(match)
    proj = {
        "_id": 0, "occupation_id": 1, "code": 1, "title": 1, "status": 1,
        "country_code": 1, "classification_version": 1, "updated_at": 1,
        **{f: 1 for f in TRACKED_FIELDS},
    }
    rows: List[Dict[str, Any]] = []
    cursor = db["occupation_master"].find(match, proj).sort("code", 1).skip(offset).limit(limit)
    async for d in cursor:
        coverage = {f: _has_value(d, f) for f in TRACKED_FIELDS}
        rows.append({
            "code": d.get("code"),
            "title": d.get("title"),
            "status": d.get("status") or "—",
            "version": d.get("classification_version") or "—",
            "coverage": coverage,
            "coverage_pct": round(
                (sum(1 for v in coverage.values() if v) / len(coverage) * 100), 0
            ),
            "updated_at": d.get("updated_at"),
        })

    return {
        "items": rows,
        "total": total,
        "offset": offset,
        "limit": limit,
        "tracked_fields": [{"key": f, "label": _humanize(f)} for f in TRACKED_FIELDS],
    }


@router.get("/orphans-4digit")
async def orphans_4digit(
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    """4-digit ANZSCO groups that have NO 6-digit child in occupation_master."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    # Get all 4-digit parent codes that have children
    cursor = db["occupation_master"].aggregate([
        {"$match": {"country_code": "AU"}},
        {"$project": {"parent": {"$substr": ["$code", 0, 4]}}},
        {"$group": {"_id": "$parent"}},
    ])
    parents_with_child = {row["_id"] async for row in cursor}

    # Find 4-digit groups NOT in this set
    orphans = []
    cursor2 = db["anzsco_4digit_master"].find({}, {"_id": 0, "code": 1, "title": 1, "anzsco_profile": 1})
    async for d in cursor2:
        if d.get("code") not in parents_with_child:
            ap = d.get("anzsco_profile") or {}
            orphans.append({
                "code": d.get("code"),
                "title": d.get("title"),
                "employed": ap.get("employed_count"),
                "median_weekly_aud": ap.get("median_weekly_earnings_aud"),
            })
            if len(orphans) >= limit:
                break

    # Sort by largest workforce first (these are highest-value to enrich)
    orphans.sort(key=lambda o: -(o.get("employed") or 0))
    return {"items": orphans[:limit], "count": len(orphans)}


# ─── helpers ────────────────────────────────────────────────────────────────
def _humanize(field: str) -> str:
    """Friendly column header for the audit grid."""
    mapping = {
        "anzsco_profile":            "Salary & Workforce",
        "tasks":                     "Job Tasks",
        "industries_ranked":         "Top Industries",
        "state_distribution":        "State % Distribution",
        "assessing_authority":       "Skill Body",
        "skill_assessment_details":  "Skill Body Criteria",
        "visa_pathways":             "Visa Eligibility",
        "state_territory_eligibility":"State Nomination",
        "skillselect_tier":          "SkillSelect Tier",
        "latest_invitation_min_points":"Min Invitation Pts",
        "dama_inclusion":            "DAMA",
        "ila_inclusion":             "Industry Labour Agreement",
        "classification_dual_code":  "ANZSCO v1.3 ↔ v2022",
    }
    return mapping.get(field, field.replace("_", " ").title())


def _source_hint(field: str) -> str:
    """Where will we get this data from when we scrape?"""
    hints = {
        "anzsco_profile":             "jobsandskills.gov.au (4-digit aggregate)",
        "tasks":                      "jobsandskills.gov.au + ABS ANZSCO catalogue",
        "industries_ranked":          "jobsandskills.gov.au",
        "state_distribution":         "jobsandskills.gov.au",
        "assessing_authority":        "Home Affairs assessment authority list (immi.homeaffairs.gov.au)",
        "skill_assessment_details":   "vetassess.com.au / acs.org.au / tradesrecognitionaustralia.gov.au / etc",
        "visa_pathways":              "immi.homeaffairs.gov.au — LIN 19/051, MLTSSL/STSOL/ROL",
        "state_territory_eligibility":"NSW, VIC, QLD, SA, WA, TAS, NT, ACT state migration sites",
        "skillselect_tier":           "Home Affairs SkillSelect Tier prioritisation publication",
        "latest_invitation_min_points":"Home Affairs Invitation Rounds outcomes (monthly)",
        "dama_inclusion":             "Home Affairs DAMA agreement pages",
        "ila_inclusion":              "Home Affairs Industry Labour Agreement page",
        "classification_dual_code":   "legislation.gov.au — ANZSCO v1.3 & v2022",
    }
    return hints.get(field, "manual entry")
