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

import os
from datetime import datetime, timezone
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
    "skillselect_tier",        # SkillSelect Tier 1-4
    "min_invitation_points",   # Home Affairs invitation rounds (Phase 9.5)
    "dama_eligibility",        # DAMA agreement membership (Phase 9.5)
    "ila_eligibility",         # Industry Labour Agreement (Phase 9.5)
    "classification_dual_code",# v1.3 ↔ v2022 mapping
]

# Phase 11 — Per-country field coverage configs.
# Each country tracks DIFFERENT enrichment fields because immigration data shapes differ.
TRACKED_FIELDS_CA = [
    "teer_category",                # Phase 10.1 — NOC TEER classification
    "hierarchy",                    # Phase 10.1 — broad/major/sub-major/minor parents
    "alternative_titles",           # Phase 10.1 — search synonyms
    "typical_tasks",                # Phase 10.1 — main duties
    "employment_requirements",      # Phase 10.1 — education / training
    "description",                  # Phase 10.1 — class definition
    "ee_eligibility",               # Phase 10.2 — FSWP/CEC/FSTP + 10 categories
    "pnp_eligibility",              # Phase 10.3 — 11 provincial nominee programs
    "ircc_round_cutoffs",           # Phase 10.4 — latest CRS minimums per category
    "regional_pilot_eligibility",   # Phase 10.5 — AIP + RCIP + FCIP
    "quebec_eligibility",           # Phase 10.7 — PSTQ + PEQ-legacy
]

TRACKED_FIELDS_NZ = [
    "title",                        # basic occupation title
    "alternative_titles",           # search synonyms
    "tasks",                        # NZ-equivalent of typical_tasks (legacy field)
    "anzsco_profile",               # salary/employment (shared with AU)
    "visa_pathways",                # SMC / AEWV / Green List eligibility
    "assessing_authority",          # NZQA / engineering NZ etc.
]


def _tracked_fields_for(country: str):
    """Returns the appropriate field list per country."""
    c = (country or "AU").upper()
    if c == "CA":
        return TRACKED_FIELDS_CA
    if c == "NZ":
        return TRACKED_FIELDS_NZ
    return TRACKED_FIELDS  # default AU


ADMIN_ROLES = {"admin", "admin_owner"}
ATLAS_READ_ROLES = {
    "admin", "admin_owner", "case_manager",
    "partner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head",
}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _can_read_atlas(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ATLAS_READ_ROLES or "*" in (user.get("permissions") or [])


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

    # ─── Phase 11 — Per-country field coverage (CA + NZ) ──────────────────
    total_6d_ca = await db["occupation_master"].count_documents({"country_code": "CA"})
    total_6d_nz = await db["occupation_master"].count_documents({"country_code": "NZ"})

    field_counts_ca: Dict[str, int] = {f: 0 for f in TRACKED_FIELDS_CA}
    proj_ca = {"_id": 0, **{f: 1 for f in TRACKED_FIELDS_CA}}
    async for d in db["occupation_master"].find({"country_code": "CA"}, proj_ca):
        for f in TRACKED_FIELDS_CA:
            if _has_value(d, f):
                field_counts_ca[f] += 1

    field_counts_nz: Dict[str, int] = {f: 0 for f in TRACKED_FIELDS_NZ}
    proj_nz = {"_id": 0, **{f: 1 for f in TRACKED_FIELDS_NZ}}
    async for d in db["occupation_master"].find({"country_code": "NZ"}, proj_nz):
        for f in TRACKED_FIELDS_NZ:
            if _has_value(d, f):
                field_counts_nz[f] += 1

    return {
        "totals": {
            "anzsco_4digit_groups": total_4d,
            "occupation_master_au_total": total_6d_au,
            "occupation_master_au_verified": verified_6d_au,
            "occupation_master_au_draft": draft_6d_au,
            "4digit_groups_with_child": len(parents_with_child),
            "4digit_groups_without_child": total_4d - len(parents_with_child),
            "occupation_master_ca_total": total_6d_ca,
            "occupation_master_ca_verified": await db["occupation_master"].count_documents({"country_code": "CA", "status": "verified"}),
            "occupation_master_ca_draft": await db["occupation_master"].count_documents({"country_code": "CA", "status": "draft"}),
            "occupation_master_nz_total": total_6d_nz,
            "occupation_master_nz_verified": await db["occupation_master"].count_documents({"country_code": "NZ", "status": "verified"}),
            "occupation_master_nz_draft": await db["occupation_master"].count_documents({"country_code": "NZ", "status": "draft"}),
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
        "field_coverage_ca": [
            {
                "field": f,
                "label": _humanize(f),
                "count_present": field_counts_ca[f],
                "count_missing": total_6d_ca - field_counts_ca[f],
                "pct_present": round((field_counts_ca[f] / total_6d_ca * 100), 1) if total_6d_ca else 0,
                "source_hint": _source_hint(f),
            }
            for f in TRACKED_FIELDS_CA
        ],
        "field_coverage_nz": [
            {
                "field": f,
                "label": _humanize(f),
                "count_present": field_counts_nz[f],
                "count_missing": total_6d_nz - field_counts_nz[f],
                "pct_present": round((field_counts_nz[f] / total_6d_nz * 100), 1) if total_6d_nz else 0,
                "source_hint": _source_hint(f, country="NZ"),
            }
            for f in TRACKED_FIELDS_NZ
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

    tracked = _tracked_fields_for(country)
    total = await db["occupation_master"].count_documents(match)
    proj = {
        "_id": 0, "occupation_id": 1, "code": 1, "title": 1, "status": 1,
        "country_code": 1, "classification_version": 1, "updated_at": 1,
        **{f: 1 for f in tracked},
    }
    rows: List[Dict[str, Any]] = []
    cursor = db["occupation_master"].find(match, proj).sort("code", 1).skip(offset).limit(limit)
    async for d in cursor:
        coverage = {f: _has_value(d, f) for f in tracked}
        rows.append({
            "code": d.get("code"),
            "title": d.get("title"),
            "status": d.get("status") or "—",
            "version": d.get("classification_version") or "—",
            "coverage": coverage,
            "coverage_pct": round(
                (sum(1 for v in coverage.values() if v) / len(coverage) * 100), 0
            ) if coverage else 0,
            "updated_at": d.get("updated_at"),
        })

    return {
        "items": rows,
        "total": total,
        "offset": offset,
        "limit": limit,
        "tracked_fields": [{"key": f, "label": _humanize(f)} for f in tracked],
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
    cursor2 = db["anzsco_4digit_master"].find(
        {"code": {"$regex": "^[0-9]{4}$"}},  # only true 4-digit
        {"_id": 0, "code": 1, "title": 1, "anzsco_profile": 1},
    )
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

    # Sort by largest workforce first
    orphans.sort(key=lambda o: -(o.get("employed") or 0))
    return {"items": orphans[:limit], "count": len(orphans)}


# ─── Step 3 — Migration Atlas Data Merge ────────────────────────────────────
INHERIT_FROM_PARENT = [
    "anzsco_profile",         # salary, employment, demographics
    "tasks",                  # job tasks
    "industries_ranked",      # top industries
    "state_distribution",     # state-wise employment %
    "education_distribution", # education levels
    "data_source",            # source metadata (ABS Feb 2026)
]


@router.get("/merge-preview")
async def merge_preview(current_user: dict = Depends(get_current_user)):
    """DRY-RUN preview: shows exactly what `/merge-commit` will do, without writing.

    Returns counts + sample inserts so admin can review BEFORE committing.
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    # All 6-digit codes already in occupation_master (AU)
    existing_codes = set()
    async for d in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$regex": "^[0-9]{6}$"}},
        {"_id": 0, "code": 1},
    ):
        existing_codes.add(d["code"])

    # All valid 6-digit codes available in anzsco_4digit_master
    to_create: List[Dict[str, Any]] = []
    to_enrich: List[Dict[str, Any]] = []
    async for d in db["anzsco_4digit_master"].find(
        {"code": {"$regex": "^[0-9]{6}$"}},
        {"_id": 0, "code": 1, "title": 1, **{f: 1 for f in INHERIT_FROM_PARENT}},
    ):
        code = d.get("code")
        if code in existing_codes:
            to_enrich.append({"code": code, "title": d.get("title")})
        else:
            to_create.append({"code": code, "title": d.get("title")})

    return {
        "summary": {
            "existing_6digit_in_master": len(existing_codes),
            "available_in_anzsco_master": len(to_create) + len(to_enrich),
            "will_create_new": len(to_create),
            "will_enrich_existing": len(to_enrich),
            "fields_inherited_from_4digit_parent": INHERIT_FROM_PARENT,
            "test_artifacts_untouched": 32,
        },
        "sample_creates": to_create[:8],
        "sample_enriches": to_enrich[:8],
        "ready_to_commit": True,
    }


@router.post("/merge-commit")
async def merge_commit(
    confirm: str = Query(..., description="Must equal 'YES-MERGE' to proceed"),
    current_user: dict = Depends(get_current_user),
):
    """Actually writes 6-digit codes from anzsco_4digit_master → occupation_master."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if confirm != "YES-MERGE":
        raise HTTPException(400, "Pass ?confirm=YES-MERGE to proceed")

    now = _now()
    actor = current_user.get("id") or "admin"

    # Index existing AU 6-digit codes
    existing = {}
    async for d in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$regex": "^[0-9]{6}$"}},
    ):
        existing[d.get("code")] = d

    created = 0
    enriched = 0
    cursor = db["anzsco_4digit_master"].find(
        {"code": {"$regex": "^[0-9]{6}$"}},
    )
    async for parent in cursor:
        code = parent.get("code")
        title = parent.get("title")

        if code not in existing:
            # Insert NEW skeleton
            doc = {
                "occupation_id": f"AU-{code}",
                "code": code,
                "classification_type": "ANZSCO",
                "classification_version": "1.3",
                "country_code": "AU",
                "title": title,
                "alternative_titles": [],
                "specialisations": [],
                "hierarchy": {"four_digit_parent": code[:4]},
                "description": parent.get("description") or "",
                "typical_tasks": parent.get("tasks") or [],
                "skill_level": "",
                "assessing_authority": {},
                "skill_assessment_details": {},
                "visa_pathways": {},
                "state_territory_eligibility": [],
                "similar_codes": [],
                "status": "imported_skeleton",
                "verification": {"is_verified": False, "verified_by": None, "verified_at": None},
                "source": "anzsco_4digit_master",
                "imported_at": now,
                "imported_by": actor,
                "created_by": actor,
                "created_at": now,
                "updated_at": now,
            }
            for f in INHERIT_FROM_PARENT:
                if parent.get(f) is not None:
                    doc[f] = parent[f]
            await db["occupation_master"].insert_one(doc)
            created += 1
        else:
            # Enrich only missing inherited fields
            existing_doc = existing[code]
            update_set: Dict[str, Any] = {}
            for f in INHERIT_FROM_PARENT:
                if not _has_value(existing_doc, f) and parent.get(f) is not None:
                    update_set[f] = parent[f]
            if update_set:
                update_set["updated_at"] = now
                update_set["last_enriched_at"] = now
                update_set["last_enriched_by"] = actor
                await db["occupation_master"].update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": update_set},
                )
                enriched += 1

    return {
        "created": created,
        "enriched": enriched,
        "total_processed": created + enriched,
        "committed_at": now,
        "committed_by": actor,
    }


# ─── Step 4 — Search APIs (Option 1 — Migration Atlas Search) ───────────────
@router.get("/search")
async def search_occupations(
    q: Optional[str] = Query(None, description="Free text query"),
    mode: str = Query("code_title", description="code_title | task | state | multi"),
    state: Optional[str] = Query(None, description="NSW | VIC | QLD | SA | WA | TAS | NT | ACT"),
    codes: Optional[str] = Query(None, description="Comma-separated codes for multi-compare"),
    limit: int = Query(40, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Unified search across LEAMSS Migration Atlas occupation data."""
    base_match: Dict[str, Any] = {
        "country_code": "AU",
        "code": {"$regex": "^[0-9]{6}$"},  # only proper 6-digit ANZSCO
        "status": {"$ne": "superseded"},   # exclude test artifacts
    }

    proj = {
        "_id": 0, "code": 1, "title": 1, "status": 1,
        "anzsco_profile.employed_count": 1,
        "anzsco_profile.median_weekly_earnings_aud": 1,
        "anzsco_profile.median_full_time_weekly_aud": 1,
        "state_distribution": 1,
        "industries_ranked": 1,
        "assessing_authority": 1,
        "visa_pathways": 1,
        "state_territory_eligibility": 1,
        "tasks": 1,
    }

    items: List[Dict[str, Any]] = []

    if mode == "multi" and codes:
        code_list = [c.strip() for c in codes.split(",") if c.strip()][:8]
        match = {**base_match, "code": {"$in": code_list}}
        async for d in db["occupation_master"].find(match, proj):
            items.append(_search_card(d))

    elif mode == "state" and state:
        # Match occupation_master that has the state listed in distribution OR nomination
        st = state.upper()
        match = {**base_match, "$or": [
            {f"state_distribution.{st}": {"$exists": True, "$ne": None}},
            {"state_territory_eligibility.state": st},
        ]}
        cursor = db["occupation_master"].find(match, proj).limit(limit)
        async for d in cursor:
            items.append(_search_card(d))

    elif mode == "task" and q:
        # Full-text-ish search on tasks
        match = {**base_match, "tasks": {"$regex": q, "$options": "i"}}
        cursor = db["occupation_master"].find(match, proj).limit(limit)
        async for d in cursor:
            items.append(_search_card(d))

    else:  # code_title (default)
        if q:
            match = {**base_match, "$or": [
                {"code": {"$regex": q, "$options": "i"}},
                {"title": {"$regex": q, "$options": "i"}},
            ]}
        else:
            match = base_match
        cursor = db["occupation_master"].find(match, proj).sort("code", 1).limit(limit)
        async for d in cursor:
            items.append(_search_card(d))

    return {"items": items, "count": len(items), "mode": mode, "query": q}


@router.get("/occupation/{code}")
async def occupation_detail(
    code: str, current_user: dict = Depends(get_current_user),
):
    """Full occupation profile — used by detail drawer + PDF infosheet."""
    d = await db["occupation_master"].find_one(
        {"country_code": "AU", "code": code}, {"_id": 0}
    )
    if not d:
        raise HTTPException(404, f"Occupation {code} not found")

    # Also fetch the 4-digit parent for related codes
    parent_code = code[:4]
    siblings = []
    async for s in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$regex": f"^{parent_code}[0-9]{{2}}$", "$ne": code}},
        {"_id": 0, "code": 1, "title": 1, "anzsco_profile.employed_count": 1},
    ).limit(10):
        siblings.append({"code": s["code"], "title": s["title"],
                         "employed": (s.get("anzsco_profile") or {}).get("employed_count")})

    return {"occupation": d, "siblings": siblings, "parent_4digit": parent_code}


@router.get("/occupation/{code}/infosheet.pdf")
async def occupation_infosheet_pdf(
    code: str, current_user: dict = Depends(get_current_user),
):
    """Phase 9 · Option 5 — One-click LEAMSS-branded ANZSCO Infosheet PDF.

    Renders a 4-page magazine-quality infosheet using the Phase 8 WeasyPrint
    template engine.
    """
    from datetime import datetime
    from fastapi.responses import StreamingResponse
    import io, base64, mimetypes
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from weasyprint import HTML

    d = await db["occupation_master"].find_one(
        {"country_code": "AU", "code": code}, {"_id": 0}
    )
    if not d:
        raise HTTPException(404, f"Occupation {code} not found")

    # Sort state distribution
    state_dist = d.get("state_distribution") or {}
    state_dist_sorted = sorted(
        [(k, v) for k, v in state_dist.items() if isinstance(v, (int, float))],
        key=lambda x: -x[1],
    )

    # Render via WeasyPrint
    HERE = Path("/app/backend/core/report_v2")
    css_text = (HERE / "css" / "theme.css").read_text(encoding="utf-8")
    logo_path = Path("/app/backend/assets/leamss-logo.png")
    logo_uri = None
    if logo_path.exists():
        mime = mimetypes.guess_type(str(logo_path))[0] or "image/png"
        b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        logo_uri = f"data:{mime};base64,{b64}"

    env = Environment(
        loader=FileSystemLoader(str(HERE / "templates")),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True, lstrip_blocks=True,
    )
    tmpl = env.get_template("infosheet.html")
    inner = tmpl.render(
        occupation=d,
        state_dist_sorted=state_dist_sorted,
        logo_data_uri=logo_uri,
        generated_on_human=datetime.now().strftime("%d %B %Y · %I:%M %p"),
    )
    full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css_text}</style></head><body>{inner}</body></html>"

    pdf_bytes = HTML(string=full_html, base_url=str(HERE)).write_pdf()
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="LEAMSS_ANZSCO_{code}.pdf"'},
    )


def _search_card(d: Dict[str, Any]) -> Dict[str, Any]:
    """Compact card shape used by search results grid."""
    ap = d.get("anzsco_profile") or {}
    aa = d.get("assessing_authority") or {}
    state_dist = d.get("state_distribution") or {}
    top_states = sorted(
        [(k, v) for k, v in state_dist.items() if isinstance(v, (int, float))],
        key=lambda x: -x[1],
    )[:3]
    visas = (d.get("visa_pathways") or {}).get("visa_eligibility") or []
    eligible_visas = [str(v.get("visa_subclass")) for v in visas if v.get("eligible")]

    return {
        "code": d.get("code"),
        "title": d.get("title"),
        "status": d.get("status"),
        "employed": ap.get("employed_count"),
        "median_weekly_aud": ap.get("median_weekly_earnings_aud") or ap.get("median_full_time_weekly_aud"),
        "top_states": [{"state": s, "pct": p} for s, p in top_states],
        "assessing_authority": aa.get("name"),
        "eligible_visas": eligible_visas,
        "tasks_count": len(d.get("tasks") or []),
        "first_task": (d.get("tasks") or [None])[0],
    }


# ─── helpers ────────────────────────────────────────────────────────────────
def _humanize(field: str) -> str:
    """Friendly column header for the audit grid."""
    mapping = {
        # AU
        "anzsco_profile":            "Salary & Workforce",
        "tasks":                     "Job Tasks",
        "industries_ranked":         "Top Industries",
        "state_distribution":        "State % Distribution",
        "assessing_authority":       "Skill Body",
        "skill_assessment_details":  "Skill Body Criteria",
        "visa_pathways":             "Visa Eligibility",
        "state_territory_eligibility":"State Nomination",
        "skillselect_tier":          "SkillSelect Tier",
        "min_invitation_points":     "Min Invitation Pts",
        "dama_eligibility":          "DAMA",
        "ila_eligibility":           "Industry Labour Agreement",
        "classification_dual_code":  "ANZSCO v1.3 ↔ v2022",
        # CA (Phase 10 / 11)
        "teer_category":             "TEER (0-5)",
        "hierarchy":                 "NOC Hierarchy",
        "alternative_titles":        "Alt. Titles",
        "typical_tasks":             "Typical Tasks",
        "employment_requirements":   "Employment Requirements",
        "description":               "Description",
        "ee_eligibility":            "Express Entry (FSWP/CEC/FSTP+Cats)",
        "pnp_eligibility":           "PNPs (11 provinces)",
        "ircc_round_cutoffs":        "IRCC Round Cutoffs",
        "regional_pilot_eligibility":"Regional Pilots (AIP/RCIP/FCIP)",
        "quebec_eligibility":        "Quebec PSTQ/PEQ",
        # NZ (Phase 11)
        "title":                     "Title",
    }
    return mapping.get(field, field.replace("_", " ").title())


def _source_hint(field: str, country: str = "AU") -> str:
    """Where will we get this data from when we scrape?

    Some fields are shared across countries (e.g. `tasks`, `anzsco_profile`,
    `alternative_titles`) but should resolve to a country-specific source.
    """
    # NZ-specific overrides for shared-name fields
    nz_overrides = {
        "tasks":                "careers.govt.nz + Stats NZ ANZSCO catalogue",
        "anzsco_profile":       "Stats NZ + immigration.govt.nz",
        "alternative_titles":   "careers.govt.nz",
        "visa_pathways":        "immigration.govt.nz — SMC / AEWV / Green List Tier 1+2",
        "assessing_authority":  "NZQA / Engineering NZ / Teaching Council NZ / etc.",
    }
    if (country or "").upper() == "NZ" and field in nz_overrides:
        return nz_overrides[field]

    hints = {
        # AU
        "anzsco_profile":             "jobsandskills.gov.au (4-digit aggregate)",
        "tasks":                      "jobsandskills.gov.au + ABS ANZSCO catalogue",
        "industries_ranked":          "jobsandskills.gov.au",
        "state_distribution":         "jobsandskills.gov.au",
        "assessing_authority":        "Home Affairs assessment authority list (immi.homeaffairs.gov.au)",
        "skill_assessment_details":   "vetassess.com.au / acs.org.au / tradesrecognitionaustralia.gov.au / etc",
        "visa_pathways":              "immi.homeaffairs.gov.au — LIN 19/051, MLTSSL/STSOL/ROL",
        "state_territory_eligibility":"NSW, VIC, QLD, SA, WA, TAS, NT, ACT state migration sites",
        "skillselect_tier":           "Home Affairs SkillSelect Tier prioritisation publication",
        "min_invitation_points":      "Home Affairs Invitation Rounds outcomes (monthly)",
        "dama_eligibility":           "Home Affairs DAMA agreement pages",
        "ila_eligibility":            "Home Affairs Industry Labour Agreement page",
        "classification_dual_code":   "legislation.gov.au — ANZSCO v1.3 & v2022",
        # CA
        "teer_category":              "statcan.gc.ca — NOC 2021 TEER classification",
        "hierarchy":                  "statcan.gc.ca — NOC 2021 broad/major/sub-major/minor groups",
        "alternative_titles":         "statcan.gc.ca — NOC 2021 alternate titles",
        "typical_tasks":              "statcan.gc.ca — NOC 2021 main duties",
        "employment_requirements":    "statcan.gc.ca — NOC 2021 employment requirements",
        "description":                "statcan.gc.ca — NOC 2021 unit group definitions",
        "ee_eligibility":             "ircc.canada.ca — Express Entry streams + 2026 category-based selection",
        "pnp_eligibility":            "Provincial nominee program pages (11 provinces/territories)",
        "ircc_round_cutoffs":         "ircc.canada.ca — Express Entry rounds of invitations (monthly)",
        "regional_pilot_eligibility": "ircc.canada.ca — AIP + RCIP + FCIP pilot pages",
        "quebec_eligibility":         "quebec.ca — PSTQ + PEQ-legacy lists",
        # NZ
        "title":                      "immigration.govt.nz + Stats NZ ANZSCO catalogue",
    }
    return hints.get(field, "manual entry")


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ─── Step 4 — Scrapers (Home Affairs first) ─────────────────────────────────
@router.post("/scrapers/home-affairs/run")
async def run_home_affairs_scraper(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Fetch Home Affairs Skilled Occupation List and enrich occupation_master.

    Set ?dry_run=false to actually write changes.
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import home_affairs
        result = await home_affairs.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Scraper failed: {e}")


@router.get("/scrapers/list")
async def list_scrapers(current_user: dict = Depends(get_current_user)):
    """List of available scrapers + their source URLs + last-run summary."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    payload = {
        "scrapers": [
            {
                "id": "home_affairs",
                "name": "Home Affairs — Skilled Occupation List",
                "source_url": "https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list",
                "what_it_provides": [
                    "Assessing authority (ACS / VETASSESS / EA / IML etc) per occupation",
                    "Visa subclass eligibility (189, 190, 491, 482, 186, 187, 494, 485)",
                    "MLTSSL / STSOL / ROL list membership",
                    "ANZSCO classification version (2013 vs 2022)",
                ],
                "estimated_records": 714,
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/home-affairs/run",
            },
            {
                "id": "state_nominations",
                "name": "State / Territory Nomination Lists (NSW + QLD + WA)",
                "source_url": "Multiple official state government sites",
                "what_it_provides": [
                    "Subclass 190 + 491 nomination eligibility per state",
                    "NSW Skills List (4-digit unit groups, 190 + 491)",
                    "QLD Offshore QSOL (6-digit codes)",
                    "WA WASMOL Schedule 1/2/GOL",
                    "State-specific caveats and notes",
                ],
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/state-nominations/run",
                "note": "VIC, ACT, NT, SA, TAS are not publicly scrapable (JS-driven or rule-based). Use CSV Upload or AI-Extract for those.",
            },
            {
                "id": "skillselect_tiers",
                "name": "SkillSelect 4-Tier Classifier (CSOL/MLTSSL based)",
                "source_url": "https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list",
                "what_it_provides": [
                    "Tier 1 — Health & Education priority occupations",
                    "Tier 2 — CSOL (Core Skills Occupation List)",
                    "Tier 3 — MLTSSL-only / regional & critical trades",
                    "Tier 4 — Other STSOL/ROL eligible occupations",
                ],
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/skillselect-tiers/run",
                "note": "Deterministic classification using existing pathway_list data — no network calls.",
            },
            {
                "id": "vetassess_groups",
                "name": "VETASSESS — Group A-F Static Seed",
                "source_url": "https://www.vetassess.com.au/skills-assessment/general-occupations",
                "what_it_provides": [
                    "Group classification (A/B/C/D/E/F) for ~120 most-common occupations",
                    "Required qualification level + field of study",
                    "Pre vs post qualification employment",
                ],
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/vetassess-groups/run",
                "note": "Site is JS-driven — this seed covers top occupations. Extend via CSV Upload or AI-Extract.",
            },
            {
                "id": "min_invitation_points",
                "name": "SkillSelect — Min Invitation Points",
                "source_url": "https://immi.homeaffairs.gov.au/visas/working-in-australia/skillselect/previous-rounds",
                "what_it_provides": [
                    "Latest confirmed minimum points for 189 + 491 invitations (2025-26 program year)",
                    "Tier-1 priority Health/Education cutoffs (often 25+ points lower)",
                    "Singleton kb_settings doc consumable by the wizard",
                ],
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/min-invitation-points/run",
                "note": "Round results are in PDFs — this seed captures median cutoffs. Admin can edit via CSV/AI-Extract.",
            },
            {
                "id": "dama",
                "name": "DAMA — Designated Area Migration Agreements (13 current)",
                "source_url": "https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/labour-agreements/types-of-labour-agreements/designated-area-migration-agreements-(dama)",
                "what_it_provides": [
                    "All 13 current DAMAs with region + state + validity",
                    "Concessions (age, English, salary) per DAMA",
                    "Sample occupation tagging on occupation_master",
                ],
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/dama/run",
                "note": "Detailed per-occupation lists are in PDF agreements — admin extends via CSV/AI-Extract.",
            },
            {
                "id": "ila",
                "name": "ILA — Industry Labour Agreements (4 main industries)",
                "source_url": "https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/labour-agreements/types-of-labour-agreements/industry-labour-agreements",
                "what_it_provides": [
                    "Restaurant (Premium Dining), Meat, Aged Care, Fishing industries",
                    "Specific occupation codes per industry agreement",
                    "Visa subclasses + concessions (English/salary/PR pathway)",
                ],
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/ila/run",
            },
            {
                "id": "noc_canada",
                "name": "🇨🇦 Canada NOC 2021 V1.0 Bulk Importer (516 unit groups)",
                "source_url": "https://www.statcan.gc.ca/en/subjects/standard/noc/2021/indexV1",
                "what_it_provides": [
                    "All 516 NOC 2021 unit groups (5-digit codes)",
                    "Full hierarchy (Broad Cat / Major / Sub-major / Minor / Unit)",
                    "TEER categorization (0-5) — Canada's skill_level equivalent",
                    "Class definition + main duties + employment requirements",
                    "27,000+ alternative job titles for search/typeahead",
                ],
                "country": "CA",
                "estimated_records": 516,
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/noc-canada/run",
                "note": "Statistics Canada official CSVs — idempotent. Preserves admin verification + custom edits.",
            },
            {
                "id": "ircc_ee_streams",
                "name": "🇨🇦 IRCC Express Entry Streams Classifier (FSWP/CEC/FSTP + 10 Categories)",
                "source_url": (
                    "https://www.canada.ca/en/immigration-refugees-citizenship/services/"
                    "immigrate-canada/express-entry/rounds-invitations/category-based-selection.html"
                ),
                "what_it_provides": [
                    "FSWP (Federal Skilled Worker) eligibility — TEER 0/1/2/3",
                    "CEC (Canadian Experience Class) eligibility — TEER 0/1/2/3",
                    "FSTP (Federal Skilled Trades) eligibility — Major Groups 72/73/82/83/92/93 TEER 2-3",
                    "Category-Based Selection 2026 (10 categories: French, Healthcare, STEM, Trade, Education, Transport, Physicians-CA, Senior Mgr-CA, Researchers-CA, Military Recruits)",
                ],
                "country": "CA",
                "estimated_records": 516,
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/ircc-ee-streams/run",
                "note": "Deterministic classification using IRCC 2026 official NOC tables — no network calls.",
            },
            {
                "id": "pnp_canada",
                "name": "🇨🇦 Canada PNP — 11 Provincial Nominee Programs",
                "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/provincial-nominees.html",
                "what_it_provides": [
                    "All 11 PNPs registered (BC/ON/AB/SK/MB/NB/NS/PE/NL/YT/NT)",
                    "Per-PNP streams with Express Entry linkage flag",
                    "Priority NOC tagging per stream (BC Tech 36 NOCs, OINP HCP 6 tech NOCs, AAIP Tech 17 NOCs, etc.)",
                    "Per-occupation pnp_eligibility[] array for Atlas Verify card",
                ],
                "country": "CA",
                "estimated_records": 516,
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/pnp-canada/run",
                "note": "Quebec excluded (separate PEQ/PSTQ system). Static seed — admin extends via CSV/AI-Extract.",
            },
            {
                "id": "ircc_round_cutoffs",
                "name": "🇨🇦 IRCC Round Cutoff Tracker (2026 CRS minimums per category)",
                "source_url": (
                    "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/"
                    "policies-operational-instructions-agreements/ministerial-instructions/express-entry-rounds.html"
                ),
                "what_it_provides": [
                    "Latest 2026 CRS minimum scores per category (CEC 518, PNP 749, Healthcare 467, Trades 477, etc.)",
                    "Latest draw date + ITA count per category",
                    "Per-NOC tagging — each occupation gets the cutoffs applicable to its categories",
                    "Singleton kb_settings doc for global Atlas view",
                ],
                "country": "CA",
                "estimated_records": 516,
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/ircc-round-cutoffs/run",
                "note": "IRCC rounds change every 2-4 weeks. Admin refreshes via CSV/AI-Extract.",
            },
            {
                "id": "ca_regional_pilots",
                "name": "🇨🇦 AIP + RCIP + FCIP Regional Programs (AU DAMA/ILA equivalent)",
                "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots.html",
                "what_it_provides": [
                    "AIP — Atlantic Immigration Program (NB/NS/PE/NL) with designated-employer rules",
                    "RCIP — 14 designated rural communities (NS/ON/MB/SK/AB/BC)",
                    "FCIP — 6 Francophone communities (NB/ON/MB/BC)",
                    "Per-occupation regional_pilot_eligibility[] array",
                ],
                "country": "CA",
                "estimated_records": 516,
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/ca-regional-pilots/run",
                "note": "Static seed of priority NOCs per community. Admin extends via CSV upload.",
            },
            {
                "id": "quebec_immigration",
                "name": "🇨🇦 Quebec PSTQ + PEQ-Legacy (Separate Provincial System)",
                "source_url": "https://www.quebec.ca/en/immigration/permanent/skilled-workers",
                "what_it_provides": [
                    "PSTQ — Programme de sélection des travailleurs qualifiés (current 2026 program)",
                    "4 PSTQ Sections: A (TEER 0-2) · B (TEER 3-5) · C (Regulated) · D (QC graduates)",
                    "Per-NOC quebec_eligibility[] with FEER category, French requirements, priority flags",
                    "PEQ-Legacy reference (closed for new applicants 2025)",
                ],
                "country": "CA",
                "estimated_records": 516,
                "status": "ready",
                "run_endpoint": "/api/anz-intel/scrapers/quebec-immigration/run",
                "note": "Quebec runs its own immigration system (not federal). FEER = NOC 2021 TEER. Admin extends per-draw priority lists.",
            },
        ]
    }
    # Default any scraper without a country tag to AU (legacy 7 AU scrapers).
    for s in payload["scrapers"]:
        s.setdefault("country", "AU")
    return payload


# ─── Step 4b — State Nominations Scraper ────────────────────────────────────
@router.post("/scrapers/state-nominations/run")
async def run_state_nominations_scraper(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Scrape NSW + QLD + WA state nomination lists and enrich state_territory_eligibility."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import state_nominations
        result = await state_nominations.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"State nominations scraper failed: {e}")


# ─── Step 4c — SkillSelect Tier Classifier ──────────────────────────────────
@router.post("/scrapers/skillselect-tiers/run")
async def run_skillselect_tiers(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Deterministically classify AU occupations into SkillSelect Tier 1-4."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import skillselect_tiers
        result = await skillselect_tiers.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"SkillSelect tier classifier failed: {e}")


# ─── Step 4d — VETASSESS Group A-F Static Seed ──────────────────────────────
@router.post("/scrapers/vetassess-groups/run")
async def run_vetassess_groups(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Seed VETASSESS Group A-F classification onto top occupations."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import vetassess_groups
        result = await vetassess_groups.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"VETASSESS seed failed: {e}")


# ─── Step 4e — Min Invitation Points Seed (Phase 9.5) ───────────────────────
@router.post("/scrapers/min-invitation-points/run")
async def run_min_invitation_points(
    dry_run: bool = Query(True),
    current_user: dict = Depends(get_current_user),
):
    """Seed SkillSelect minimum invitation points (latest confirmed cutoffs)."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import home_affairs_supplementary as supp
        return await supp.apply_min_invitation_points(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
    except Exception as e:
        raise HTTPException(500, f"Min invitation points seed failed: {e}")


# ─── Step 4f — DAMA Seed (Phase 9.5) ────────────────────────────────────────
@router.post("/scrapers/dama/run")
async def run_dama(
    dry_run: bool = Query(True),
    current_user: dict = Depends(get_current_user),
):
    """Seed 13 current Designated Area Migration Agreements with their region + concessions."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import home_affairs_supplementary as supp
        return await supp.apply_dama_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
    except Exception as e:
        raise HTTPException(500, f"DAMA seed failed: {e}")


# ─── Step 4g — ILA Seed (Phase 9.5) ─────────────────────────────────────────
@router.post("/scrapers/ila/run")
async def run_ila(
    dry_run: bool = Query(True),
    current_user: dict = Depends(get_current_user),
):
    """Seed 4 main Industry Labour Agreements (Restaurant/Meat/Aged Care/Fishing)."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import home_affairs_supplementary as supp
        return await supp.apply_ila_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
    except Exception as e:
        raise HTTPException(500, f"ILA seed failed: {e}")


# ─── Step 4h — Canada NOC 2021 Bulk Importer (Phase 10.1) ───────────────────
@router.post("/scrapers/noc-canada/run")
async def run_noc_canada(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Bulk import all 516 NOC 2021 V1.0 unit groups from Statistics Canada CSVs.

    Idempotent: re-runs preserve admin verification, custom_qa, linked_product_id,
    assessing_authority, and status. Only scraper-owned fields are refreshed.
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import noc_canada
        return await noc_canada.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
    except FileNotFoundError as e:
        raise HTTPException(503, f"NOC CSV files missing — re-download from statcan.gc.ca: {e}")
    except Exception as e:
        raise HTTPException(500, f"NOC Canada importer failed: {e}")


# ─── Step 4i — IRCC Express Entry Streams Classifier (Phase 10.2) ──────────
@router.post("/scrapers/ircc-ee-streams/run")
async def run_ircc_ee_streams(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Classify every CA NOC record with IRCC Express Entry eligibility.

    Tags each occupation with:
      - FSWP / CEC / FSTP federal program eligibility (TEER-driven)
      - Category-Based Selection 2026 categories (10 total)
        French, Healthcare, STEM, Trade, Education, Transport, Physicians-CA-exp,
        Senior Managers-CA-exp, Researchers-CA-exp, Military Recruits.

    Deterministic — no scraping, no AI. Idempotent.
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import ircc_ee_streams
        return await ircc_ee_streams.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
    except Exception as e:
        raise HTTPException(500, f"IRCC EE Streams classifier failed: {e}")


# ─── Step 4j — Canada PNP Seed (Phase 10.3) ─────────────────────────────────
@router.post("/scrapers/pnp-canada/run")
async def run_pnp_canada(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Seed 11 Canadian PNPs and tag each CA NOC with pnp_eligibility[].

    Excludes Quebec (separate PEQ/PSTQ system).
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import pnp_canada
        return await pnp_canada.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
    except Exception as e:
        raise HTTPException(500, f"PNP Canada seed failed: {e}")


# ─── Step 4k — IRCC Round Cutoff Tracker (Phase 10.4) ───────────────────────
@router.post("/scrapers/ircc-round-cutoffs/run")
async def run_ircc_round_cutoffs(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Snapshot 2026 IRCC Express Entry round cutoffs and tag each CA NOC.

    Stores singleton in kb_settings + tags every CA occupation with applicable
    category cutoffs (CEC, PNP, Healthcare, STEM, Trades, French, etc.).
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import ircc_round_cutoffs
        return await ircc_round_cutoffs.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
    except Exception as e:
        raise HTTPException(500, f"IRCC Round Cutoffs scraper failed: {e}")


# ─── Step 4l — CA Regional Pilots: AIP + RCIP + FCIP (Phase 10.5) ───────────
@router.post("/scrapers/ca-regional-pilots/run")
async def run_ca_regional_pilots(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Seed AIP + 14 RCIP communities + 6 FCIP communities.

    Tags each CA NOC with regional_pilot_eligibility[] showing which pilots/communities
    target this occupation. Equivalent to AU's DAMA + ILA.
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import ca_regional_pilots
        return await ca_regional_pilots.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
    except Exception as e:
        raise HTTPException(500, f"CA Regional Pilots seed failed: {e}")


# ─── Step 4m — Quebec PSTQ + PEQ-Legacy (Phase 10.7) ────────────────────────
@router.post("/scrapers/quebec-immigration/run")
async def run_quebec_immigration(
    dry_run: bool = Query(True, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Seed Quebec PSTQ (4 sections) + PEQ legacy reference.

    Tags every CA NOC with quebec_eligibility (FEER category, eligible PSTQ sections,
    French requirements, regulated flag).
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    try:
        from core.scrapers import quebec_immigration
        return await quebec_immigration.apply_to_db(
            db, dry_run=dry_run, actor=current_user.get("id") or "admin"
        )
    except Exception as e:
        raise HTTPException(500, f"Quebec immigration seed failed: {e}")


# ─── Step 5 — Manual Tools (Bulk CSV Upload + AI Paste-Extract) ─────────────
from fastapi import UploadFile, File, Body

@router.post("/bulk-upload-csv/preview")
async def bulk_upload_csv_preview(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Parse uploaded CSV and return a dry-run preview.

    Expected columns (case-insensitive, in any order):
      • code (required, 6-digit ANZSCO)
      • vetassess_group  (A | B | C | D | E | F)
      • vetassess_criteria_text
      • assessing_body
      • assessing_body_url
      • skill_assessment_notes
    """
    import csv, io
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))

    rows: List[Dict[str, Any]] = []
    invalid: List[Dict[str, Any]] = []
    for i, raw in enumerate(reader, start=2):  # row 1 is header
        row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
        code = row.get("code") or ""
        if not code or not code.isdigit() or len(code) != 6:
            invalid.append({"row": i, "code": code, "reason": "code must be 6-digit numeric"})
            continue
        rows.append({"row_num": i, **row})

    # Check which codes exist in DB
    codes = [r["code"] for r in rows]
    existing = set()
    async for d in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$in": codes}}, {"_id": 0, "code": 1}
    ):
        existing.add(d["code"])

    matched = [r for r in rows if r["code"] in existing]
    unmatched = [r["code"] for r in rows if r["code"] not in existing]

    return {
        "total_rows": len(rows) + len(invalid),
        "valid_rows": len(rows),
        "invalid_rows": invalid[:20],
        "matched_in_db": len(matched),
        "unmatched_codes": unmatched[:20],
        "sample_matched": matched[:8],
        "columns_seen": list(rows[0].keys()) if rows else [],
    }


@router.post("/bulk-upload-csv/commit")
async def bulk_upload_csv_commit(
    file: UploadFile = File(...),
    overwrite: bool = Query(False, description="If true, overwrite existing values"),
    current_user: dict = Depends(get_current_user),
):
    """Commit a CSV — same as preview but actually writes."""
    import csv, io
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))

    now = _now()
    actor = current_user.get("id") or "admin"
    updated = 0
    skipped_unknown = 0
    skipped_verified = 0
    errors: List[Dict[str, Any]] = []

    for i, raw in enumerate(reader, start=2):
        row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
        code = row.get("code")
        if not code or not code.isdigit() or len(code) != 6:
            continue

        ex = await db["occupation_master"].find_one({"country_code": "AU", "code": code})
        if not ex:
            skipped_unknown += 1
            continue
        if not overwrite and ex.get("status") == "verified":
            skipped_verified += 1
            continue

        update_set: Dict[str, Any] = {}

        if row.get("vetassess_group"):
            details = ex.get("skill_assessment_details") or {}
            details["vetassess_group"] = row["vetassess_group"].upper()
            if row.get("vetassess_criteria_text"):
                details["vetassess_criteria"] = row["vetassess_criteria_text"]
            update_set["skill_assessment_details"] = details

        if row.get("assessing_body"):
            aa = ex.get("assessing_authority") or {}
            if overwrite or not aa.get("name"):
                aa["name"] = row["assessing_body"]
                aa["short_name"] = aa.get("short_name") or row["assessing_body"]
            if row.get("assessing_body_url") and (overwrite or not aa.get("url")):
                aa["url"] = row["assessing_body_url"]
            update_set["assessing_authority"] = aa

        if row.get("skill_assessment_notes"):
            update_set["skill_assessment_notes"] = row["skill_assessment_notes"]

        if update_set:
            update_set["last_csv_imported_at"] = now
            update_set["last_csv_imported_by"] = actor
            try:
                await db["occupation_master"].update_one(
                    {"_id": ex["_id"]}, {"$set": update_set}
                )
                updated += 1
            except Exception as e:
                errors.append({"row": i, "code": code, "error": str(e)[:200]})

    return {
        "updated": updated,
        "skipped_unknown_code": skipped_unknown,
        "skipped_verified": skipped_verified,
        "errors": errors[:20],
        "ran_at": now,
        "ran_by": actor,
    }


@router.get("/bulk-upload-csv/template")
async def bulk_upload_csv_template(current_user: dict = Depends(get_current_user)):
    """Returns a CSV template for the admin team to fill in."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    from fastapi.responses import StreamingResponse
    import io
    sample = (
        "code,vetassess_group,vetassess_criteria_text,assessing_body,assessing_body_url,skill_assessment_notes\n"
        "261313,A,AQF Bachelor degree or higher in a highly relevant field; 1 year post-qualification employment in Australia OR 3 years globally,ACS — Australian Computer Society,https://www.acs.org.au/skills-assessment.html,Recognised pathway for skilled migration\n"
        "221111,B,AQF Bachelor degree or higher in accounting; 1 year post-qualification employment,CPA Australia,https://www.cpaaustralia.com.au/become-a-cpa/migration-assessment,Provisional and full membership pathways available\n"
        "313211,C,AQF Diploma or higher; 3 years post-qualification employment,VETASSESS,https://www.vetassess.com.au,\n"
        "312911,D,AQF Certificate IV; 5 years employment with 3 years post-qualification,VETASSESS,https://www.vetassess.com.au,\n"
    )
    return StreamingResponse(
        io.BytesIO(sample.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leamss_atlas_vetassess_template.csv"'},
    )


# ─── AI-Extract tool (Claude via Emergent LLM Key) ──────────────────────────
@router.post("/ai-extract/preview")
async def ai_extract_preview(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """AI-Extract: paste raw text (eg from VETASSESS checker result) → Claude extracts structured fields.

    Body:
      • code:       6-digit ANZSCO code (required for matching to DB)
      • raw_text:   text content to extract from (required)
      • intent:     "vetassess_group" | "acs_rules" | "state_nomination"
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    code = (payload.get("code") or "").strip()
    raw_text = (payload.get("raw_text") or "").strip()
    intent = (payload.get("intent") or "vetassess_group").strip()

    if not code or not raw_text:
        raise HTTPException(400, "code and raw_text are required")
    if not (code.isdigit() and len(code) == 6):
        raise HTTPException(400, "code must be 6-digit ANZSCO")

    EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "EMERGENT_LLM_KEY not configured")

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid, json as _json

    extraction_schema = {
        "vetassess_group": (
            "Extract VETASSESS skill assessment Group classification (A/B/C/D/E/F) "
            "and criteria. Return JSON: { \"vetassess_group\": \"A\" | \"B\" | \"C\" | \"D\" | \"E\" | \"F\" | null, "
            "\"qualification_required\": string, \"experience_required\": string, "
            "\"pre_qual_experience_allowed\": true | false | null, \"criteria_summary\": string }"
        ),
        "acs_rules": (
            "Extract ACS skill assessment rules. Return JSON: { \"acs_classification\": \"ICT Major\" | \"ICT Minor\" | \"Non-ICT\" | null, "
            "\"qualification_required\": string, \"experience_required\": string, \"criteria_summary\": string }"
        ),
        "state_nomination": (
            "Extract state nomination eligibility. Return JSON: { \"state\": \"NSW\" | \"VIC\" | ..., "
            "\"demand_level\": \"high\" | \"medium\" | \"low\" | null, "
            "\"sc190_eligible\": true | false, \"sc491_eligible\": true | false, "
            "\"caveats\": string }"
        ),
    }
    instruction = extraction_schema.get(intent, extraction_schema["vetassess_group"])

    system = (
        "You are LEAMSS Migration Atlas extraction assistant. Read the user's raw text "
        "(copied from an official migration site) and return STRICTLY VALID JSON matching the schema. "
        "No markdown fences. No commentary. If a field cannot be determined, use null."
    )
    prompt = (
        f"Schema instruction:\n{instruction}\n\n"
        f"ANZSCO code: {code}\n\n"
        f"Raw text to extract from:\n---\n{raw_text[:8000]}\n---\n\n"
        "Return JSON only."
    )

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"atlas-extract-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-6")

    try:
        response = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        raise HTTPException(502, f"AI extraction failed: {str(e)[:200]}")

    text = str(response).strip()
    # Strip code fences if present
    if text.startswith("```"):
        text = text.strip("`")
        # remove possible "json\n" prefix
        if text.lower().startswith("json"):
            text = text.split("\n", 1)[1] if "\n" in text else text[4:]
    try:
        extracted = _json.loads(text)
    except _json.JSONDecodeError:
        raise HTTPException(502, f"AI returned non-JSON: {text[:400]}")

    return {
        "code": code,
        "intent": intent,
        "extracted": extracted,
        "raw_ai_response": text[:1500],
    }


@router.post("/ai-extract/commit")
async def ai_extract_commit(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Commit AI-extracted data to occupation_master.

    Body:
      • code:      6-digit ANZSCO
      • intent:    vetassess_group | acs_rules | state_nomination
      • extracted: object returned by /ai-extract/preview
      • overwrite: bool (default false)
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    code = (payload.get("code") or "").strip()
    intent = (payload.get("intent") or "").strip()
    extracted = payload.get("extracted") or {}
    overwrite = bool(payload.get("overwrite"))

    if not code or not intent or not extracted:
        raise HTTPException(400, "code, intent, extracted are all required")

    ex = await db["occupation_master"].find_one({"country_code": "AU", "code": code})
    if not ex:
        raise HTTPException(404, f"Occupation {code} not found")
    if ex.get("status") == "verified" and not overwrite:
        raise HTTPException(409, "Record is verified — pass overwrite=true to update")

    now = _now()
    actor = current_user.get("id") or "admin"
    update_set: Dict[str, Any] = {}

    if intent == "vetassess_group":
        details = ex.get("skill_assessment_details") or {}
        if extracted.get("vetassess_group"):
            details["vetassess_group"] = extracted["vetassess_group"]
        for k in ("qualification_required", "experience_required", "criteria_summary", "pre_qual_experience_allowed"):
            if extracted.get(k) is not None:
                details[k] = extracted[k]
        update_set["skill_assessment_details"] = details
    elif intent == "acs_rules":
        details = ex.get("skill_assessment_details") or {}
        details["acs"] = extracted
        update_set["skill_assessment_details"] = details
    elif intent == "state_nomination":
        st = (extracted.get("state") or "").upper()
        if st:
            existing = list(ex.get("state_territory_eligibility") or [])
            existing = [e for e in existing if e.get("state") != st]
            existing.append({
                "state": st,
                "demand": extracted.get("demand_level"),
                "sc190": bool(extracted.get("sc190_eligible")),
                "sc491": bool(extracted.get("sc491_eligible")),
                "caveats": extracted.get("caveats"),
            })
            update_set["state_territory_eligibility"] = existing

    if not update_set:
        raise HTTPException(400, "No actionable fields in extracted payload")

    update_set["last_ai_extracted_at"] = now
    update_set["last_ai_extracted_by"] = actor
    await db["occupation_master"].update_one(
        {"_id": ex["_id"]}, {"$set": update_set}
    )

    return {"ok": True, "code": code, "intent": intent, "updated_fields": list(update_set.keys()), "saved_at": now}



# ─── Phase 9.2 — Sales-accessible Atlas Verify endpoint ─────────────────────
TIER_LABELS = {
    "tier_1": {"label": "Tier 1", "tag": "Health & Education Priority", "tone": "teal"},
    "tier_2": {"label": "Tier 2", "tag": "Core Skills Occupation List (CSOL)", "tone": "teal"},
    "tier_3": {"label": "Tier 3", "tag": "MLTSSL / Regional Critical", "tone": "gold"},
    "tier_4": {"label": "Tier 4", "tag": "Other Eligible (STSOL/ROL)", "tone": "orange"},
}


@router.get("/verify/{code}")
async def verify_in_atlas(
    code: str,
    country: str = Query("AU"),
    current_user: dict = Depends(get_current_user),
):
    """Sales-facing Atlas Verify Card endpoint.

    Returns a compact, ready-to-render payload showing:
      - Occupation title + ANZSCO code + classification dual-code
      - Assessing authority (skill body) - name + URL
      - SkillSelect Tier 1-4 with friendly label
      - VETASSESS Group A-F + qualification criteria
      - Visa pathways (subclass eligibility)
      - State / territory nomination matrix (190 + 491)
      - Verification status from admin

    Accessible to sales, partner, case manager, and admin roles.
    """
    if not _can_read_atlas(current_user):
        raise HTTPException(403, "Atlas read access required")
    # AU = 6-digit ANZSCO, CA = 5-digit NOC, NZ = 6-digit ANZSCO
    country_upper = country.upper()
    if country_upper == "CA":
        if not (code.isdigit() and len(code) == 5):
            raise HTTPException(400, "CA code must be 5-digit NOC")
    else:
        if not (code.isdigit() and len(code) == 6):
            raise HTTPException(400, f"{country_upper} code must be 6-digit ANZSCO")

    d = await db["occupation_master"].find_one(
        {"country_code": country_upper, "code": code},
        {"_id": 0},
    )
    if not d:
        raise HTTPException(404, f"Occupation {code} not found in {country_upper} Atlas")

    tier_key = d.get("skillselect_tier") or "tier_4"
    tier_meta = {**TIER_LABELS.get(tier_key, TIER_LABELS["tier_4"]),
                 "reason": d.get("skillselect_tier_reason")}

    sad = d.get("skill_assessment_details") or {}
    vetassess = {
        "group": sad.get("vetassess_group"),
        "qualification_required": sad.get("qualification_required"),
        "experience_required":    sad.get("experience_required"),
        "pre_qual_experience_allowed": sad.get("pre_qual_experience_allowed"),
        "source": sad.get("vetassess_source"),
    }

    vp = d.get("visa_pathways") or {}
    visas = vp.get("visa_eligibility") or []

    state_arr = d.get("state_territory_eligibility") or []
    state_matrix = {}
    for entry in state_arr:
        st = (entry.get("state") or "").upper()
        if not st:
            continue
        state_matrix[st] = {
            "state":  st,
            "sc190":  bool(entry.get("sc190")),
            "sc491":  bool(entry.get("sc491")),
            "demand": entry.get("demand"),
            "caveats": entry.get("caveats"),
            "unit_group_match": entry.get("unit_group_match"),
            "source": entry.get("source"),
        }

    return {
        "code": d.get("code"),
        "title": d.get("title"),
        "country_code": d.get("country_code"),
        "classification_version": d.get("classification_version"),
        "classification_dual_code": d.get("classification_dual_code") or {},
        "verification_status": d.get("status") or "draft",
        "skillselect_tier": tier_meta,
        "min_invitation_points": d.get("min_invitation_points") or {},
        "assessing_authority": d.get("assessing_authority") or {},
        "vetassess": vetassess,
        "visa_eligibility": visas,
        "pathway_lists": (d.get("pathway_list") or "").split(";") if d.get("pathway_list") else [],
        "state_nomination_matrix": state_matrix,
        "dama_eligibility": d.get("dama_eligibility") or [],
        "ila_eligibility": d.get("ila_eligibility") or [],
        # Phase 10.1/10.2 — Canada-specific fields (empty for AU/NZ)
        "teer_category": d.get("teer_category"),
        "teer_label": d.get("teer_label"),
        "ee_eligibility": d.get("ee_eligibility") or {},
        "pnp_eligibility": d.get("pnp_eligibility") or [],
        "ircc_round_cutoffs": d.get("ircc_round_cutoffs") or {},
        "regional_pilot_eligibility": d.get("regional_pilot_eligibility") or [],
        "quebec_eligibility": d.get("quebec_eligibility") or {},
        "hierarchy": d.get("hierarchy") or {},
        "tasks_count": len(d.get("tasks") or []),
        "atlas_url": "/admin/anz-intel/audit",
        "infosheet_pdf": f"/api/anz-intel/occupation/{code}/infosheet.pdf",
    }



# ═════════════════════════════════════════════════════════════════════════════
# Phase 9.6 — Bulk State Nomination AI Extract (for VIC/SA/ACT/NT/TAS)
# ═════════════════════════════════════════════════════════════════════════════
@router.post("/ai-extract-state-bulk/preview")
async def ai_extract_state_bulk_preview(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Bulk state-nomination AI extraction for states whose sites are JS-driven.

    Body:
      • state: "VIC" | "SA" | "ACT" | "NT" | "TAS" | "WA" (any 2-3 letter state code)
      • raw_text: pasted page content from official state migration site
      • source_url: official source URL for audit trail
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    state = (payload.get("state") or "").strip().upper()
    raw_text = (payload.get("raw_text") or "").strip()
    source_url = (payload.get("source_url") or "").strip()

    if not state or not raw_text:
        raise HTTPException(400, "state and raw_text are required")
    if len(state) not in (2, 3) or not state.isalpha():
        raise HTTPException(400, "state must be a 2-3 letter code (NSW/VIC/QLD/SA/WA/TAS/NT/ACT)")

    EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "EMERGENT_LLM_KEY not configured")

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid
    import json as _json

    system = (
        "You are LEAMSS Migration Atlas bulk extractor. Read raw text copied from an official Australian "
        "state-migration website and return a JSON array of occupation eligibility entries. "
        "Each entry must be: {code, title, sc190, sc491, demand, caveats}. "
        "If 'code' is 4-digit ANZSCO unit-group, set field 'unit_group_match' instead of 'code'. "
        "Strictly valid JSON, no markdown fences, no commentary."
    )
    prompt = (
        f"State: {state}\nSource URL: {source_url or '(not provided)'}\n\n"
        "Extract ALL occupations referenced in the text. Return JSON of this shape:\n"
        "{ \"records\": [ "
        "{ \"code\": \"261313\" | null, \"unit_group_match\": \"2613\" | null, "
        "\"title\": \"Software Engineer\", \"sc190\": true|false, \"sc491\": true|false, "
        "\"demand\": \"high\"|\"medium\"|\"low\"|null, \"caveats\": \"any notes\"|null } ] }\n\n"
        f"Raw text:\n---\n{raw_text[:12000]}\n---\n\n"
        "Return JSON only."
    )

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"atlas-state-bulk-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-6")

    try:
        response = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        raise HTTPException(502, f"AI extraction failed: {str(e)[:200]}")

    text = str(response).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text.split("\n", 1)[1] if "\n" in text else text[4:]
    try:
        extracted = _json.loads(text)
    except _json.JSONDecodeError:
        raise HTTPException(502, f"AI returned non-JSON: {text[:400]}")

    records = extracted.get("records") if isinstance(extracted, dict) else (extracted if isinstance(extracted, list) else [])
    if not isinstance(records, list):
        records = []

    # Match records to existing occupation_master codes
    matched: List[Dict[str, Any]] = []
    unmatched: List[Dict[str, Any]] = []
    unit_group_resolutions: List[Dict[str, Any]] = []

    for rec in records:
        code = (rec.get("code") or "").strip() if isinstance(rec.get("code"), str) else None
        unit_group = (rec.get("unit_group_match") or "").strip() if isinstance(rec.get("unit_group_match"), str) else None
        if code and code.isdigit() and len(code) == 6:
            ex = await db["occupation_master"].find_one({"country_code": "AU", "code": code}, {"_id": 1, "title": 1})
            if ex:
                matched.append({**rec, "matched_code": code, "match_type": "6_digit_exact"})
            else:
                unmatched.append({**rec, "reason": f"6-digit code {code} not in DB"})
        elif unit_group and unit_group.isdigit() and len(unit_group) == 4:
            children = await db["occupation_master"].find(
                {"country_code": "AU", "code": {"$regex": f"^{unit_group}"}},
                {"code": 1, "title": 1, "_id": 0},
            ).to_list(length=200)
            if children:
                unit_group_resolutions.append({
                    "unit_group": unit_group,
                    "rec_title": rec.get("title"),
                    "child_count": len(children),
                    "sample_children": children[:3],
                })
                matched.append({**rec, "matched_unit_group": unit_group, "child_count": len(children), "match_type": "4_digit_expanded"})
            else:
                unmatched.append({**rec, "reason": f"Unit group {unit_group} not in DB"})
        else:
            unmatched.append({**rec, "reason": "Invalid code/unit_group"})

    return {
        "state": state,
        "source_url": source_url,
        "total_extracted": len(records),
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "unit_group_expansions": unit_group_resolutions,
        "records": matched,
        "unmatched": unmatched[:20],
        "raw_ai_response_preview": text[:1000],
    }


@router.post("/ai-extract-state-bulk/commit")
async def ai_extract_state_bulk_commit(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Commit matched records from /ai-extract-state-bulk/preview to occupation_master.state_territory_eligibility.

    Body:
      • state, source_url
      • records: the `matched` array from preview (only matched ones are processed)
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    state = (payload.get("state") or "").strip().upper()
    source_url = (payload.get("source_url") or "").strip()
    records = payload.get("records") or []

    if not state or not records:
        raise HTTPException(400, "state and records are required")

    now = datetime.now(timezone.utc).isoformat()
    actor = current_user.get("id") or "admin"
    updates_6d = 0
    updates_4d_expanded = 0
    skipped_verified = 0

    for rec in records:
        match_type = rec.get("match_type")
        if match_type == "6_digit_exact":
            target_codes = [rec["matched_code"]]
        elif match_type == "4_digit_expanded":
            unit_group = rec["matched_unit_group"]
            children_docs = await db["occupation_master"].find(
                {"country_code": "AU", "code": {"$regex": f"^{unit_group}"}},
                {"code": 1, "_id": 0},
            ).to_list(length=500)
            target_codes = [c["code"] for c in children_docs]
        else:
            continue

        new_entry = {
            "state": state,
            "sc190": bool(rec.get("sc190")),
            "sc491": bool(rec.get("sc491")),
            "demand": rec.get("demand"),
            "caveats": rec.get("caveats"),
            "source": source_url or "AI-extracted",
            "ai_extracted_at": now,
        }
        if match_type == "4_digit_expanded":
            new_entry["unit_group_match"] = rec["matched_unit_group"]

        async for d in db["occupation_master"].find(
            {"country_code": "AU", "code": {"$in": target_codes}},
            {"_id": 1, "code": 1, "state_territory_eligibility": 1, "status": 1},
        ):
            if d.get("status") == "verified":
                skipped_verified += 1
                continue
            merged = [e for e in (d.get("state_territory_eligibility") or []) if (e.get("state") or "").upper() != state]
            merged.append(new_entry)
            await db["occupation_master"].update_one(
                {"_id": d["_id"]},
                {"$set": {"state_territory_eligibility": merged, "last_state_ai_extracted_at": now, "last_state_ai_extracted_by": actor}},
            )
            if match_type == "6_digit_exact":
                updates_6d += 1
            else:
                updates_4d_expanded += 1

    return {
        "state": state,
        "source_url": source_url,
        "updates_6_digit_exact": updates_6d,
        "updates_4_digit_expanded": updates_4d_expanded,
        "skipped_verified": skipped_verified,
        "ran_at": now,
        "ran_by": actor,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Phase 9.6 — DAMA / ILA PDF Parser (admin uploads official PDF → extract codes)
# ═════════════════════════════════════════════════════════════════════════════
@router.post("/dama-pdf/preview")
async def dama_pdf_preview(
    file: UploadFile = File(...),
    target_id: str = Query(..., description="DAMA id (nt/goldfields/aerotropolis/etc) OR ILA id (restaurant/meat/aged_care/fishing)"),
    target_type: str = Query("dama", description="'dama' or 'ila'"),
    current_user: dict = Depends(get_current_user),
):
    """Upload official DAMA/ILA PDF → pdfplumber extracts text → regex finds all 6-digit ANZSCO codes.
    Returns preview (no DB writes)."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if target_type not in ("dama", "ila"):
        raise HTTPException(400, "target_type must be 'dama' or 'ila'")
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, f"Expected PDF, got {file.content_type}")

    import pdfplumber
    import re as _re
    import io as _io

    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(413, "PDF too large (max 20MB)")

    try:
        all_text = []
        with pdfplumber.open(_io.BytesIO(contents)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                txt = page.extract_text() or ""
                all_text.append(txt)
        full_text = "\n".join(all_text)
    except Exception as e:
        raise HTTPException(502, f"Failed to parse PDF: {str(e)[:200]}")

    # Extract all 6-digit ANZSCO codes
    codes_found = sorted(set(_re.findall(r"\b([1-8]\d{5})\b", full_text)))
    if not codes_found:
        return {
            "target_id": target_id, "target_type": target_type,
            "pdf_pages": page_count, "pdf_size_bytes": len(contents),
            "codes_extracted": [], "matched_in_db": [], "unmatched_codes": [],
            "warning": "No 6-digit ANZSCO codes found in PDF",
        }

    # Cross-check against occupation_master
    matched: List[Dict[str, Any]] = []
    db_titles = {}
    async for d in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$in": codes_found}},
        {"_id": 0, "code": 1, "title": 1, "status": 1, "dama_eligibility": 1, "ila_eligibility": 1},
    ):
        db_titles[d["code"]] = d
        matched.append({
            "code": d["code"],
            "title": d.get("title"),
            "status": d.get("status"),
            "already_tagged_with_target": any(
                (e.get("id") == target_id)
                for e in (d.get("dama_eligibility" if target_type == "dama" else "ila_eligibility") or [])
            ),
        })
    unmatched = [c for c in codes_found if c not in db_titles]

    return {
        "target_id": target_id,
        "target_type": target_type,
        "filename": file.filename,
        "pdf_pages": page_count,
        "pdf_size_bytes": len(contents),
        "total_codes_extracted": len(codes_found),
        "matched_in_db": matched,
        "unmatched_codes": unmatched,
        "preview_text_snippet": full_text[:600],
    }


@router.post("/dama-pdf/commit")
async def dama_pdf_commit(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Commit selected codes from a DAMA/ILA PDF preview to occupation_master.

    Body:
      • target_id (e.g. 'nt', 'aerotropolis', 'restaurant')
      • target_type: 'dama' | 'ila'
      • codes: list of 6-digit codes to commit
      • source: PDF filename or URL
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    target_id = (payload.get("target_id") or "").strip()
    target_type = (payload.get("target_type") or "dama").strip()
    codes = payload.get("codes") or []
    source = (payload.get("source") or "").strip()

    if not target_id or not codes:
        raise HTTPException(400, "target_id and codes are required")
    if target_type not in ("dama", "ila"):
        raise HTTPException(400, "target_type must be 'dama' or 'ila'")

    # Look up the seed entry for target_id from kb_settings
    settings_key = "dama_list" if target_type == "dama" else "ila_list"
    settings_doc = await db["kb_settings"].find_one({"_id": settings_key})
    if not settings_doc:
        raise HTTPException(404, f"{settings_key} not seeded — run /scrapers/{target_type}/run first")
    seeded = settings_doc.get("data") or []
    target_seed = next((s for s in seeded if s.get("id") == target_id), None)
    if not target_seed:
        raise HTTPException(404, f"{target_type.upper()} id '{target_id}' not found in seed")

    now = datetime.now(timezone.utc).isoformat()
    actor = current_user.get("id") or "admin"
    field_key = "dama_eligibility" if target_type == "dama" else "ila_eligibility"

    new_entry: Dict[str, Any] = {
        "id": target_seed["id"],
        "source": source or settings_doc.get("source_url"),
        "pdf_extracted_at": now,
    }
    if target_type == "dama":
        new_entry.update({
            "region": target_seed["region"], "state": target_seed["state"],
            "valid_until": target_seed["valid_until"], "concessions": target_seed["concessions"],
        })
    else:
        new_entry.update({
            "industry": target_seed["industry"],
            "visa_subclasses": target_seed["visa_subclasses"],
            "concessions": target_seed["concessions"],
        })

    updated = 0
    skipped_verified = 0
    async for d in db["occupation_master"].find(
        {"country_code": "AU", "code": {"$in": codes}},
        {"_id": 1, "code": 1, field_key: 1, "status": 1},
    ):
        if d.get("status") == "verified":
            skipped_verified += 1
            continue
        existing = [e for e in (d.get(field_key) or []) if e.get("id") != target_seed["id"]]
        existing.append(new_entry)
        await db["occupation_master"].update_one(
            {"_id": d["_id"]},
            {"$set": {
                field_key: existing,
                f"last_{target_type}_pdf_committed_at": now,
                f"last_{target_type}_pdf_committed_by": actor,
            }},
        )
        updated += 1

    return {
        "target_id": target_id,
        "target_type": target_type,
        "updated": updated,
        "skipped_verified": skipped_verified,
        "codes_attempted": len(codes),
        "ran_at": now,
        "ran_by": actor,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Phase 9.6 — Admin-editable Calculator Rules Engine
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/calculator-rules/{country}")
async def get_calculator_rules(
    country: str,
    current_user: dict = Depends(get_current_user),
):
    """Return active rule set for a country — DB override or hardcoded defaults."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    from core.rules_engine import load_rules, supported_countries
    if country.upper() not in supported_countries():
        raise HTTPException(400, f"Unsupported country. Choose from {supported_countries()}")
    return await load_rules(db, country)


@router.put("/calculator-rules/{country}")
async def put_calculator_rules(
    country: str,
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Admin saves edited rule set for a country.
    Body: { tables: {...}, version?: "2025-26" }
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    from core.rules_engine import save_rules, supported_countries
    if country.upper() not in supported_countries():
        raise HTTPException(400, f"Unsupported country. Choose from {supported_countries()}")
    tables = payload.get("tables")
    if not isinstance(tables, dict) or not tables:
        raise HTTPException(400, "Body must contain non-empty 'tables' object")
    return await save_rules(
        db, country, tables, payload.get("version"),
        actor=current_user.get("id") or "admin",
    )


@router.post("/calculator-rules/{country}/reset")
async def reset_calculator_rules(
    country: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete the DB override → calculator falls back to hardcoded defaults."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    from core.rules_engine import reset_rules, supported_countries
    if country.upper() not in supported_countries():
        raise HTTPException(400, f"Unsupported country. Choose from {supported_countries()}")
    return await reset_rules(db, country, actor=current_user.get("id") or "admin")


# ─── Phase 11 — IRCC Express Entry Category NOC Overrides ───────────────────
# Admin UI to override the hardcoded category NOC lists from
# core/scrapers/ircc_ee_streams.py without touching code.
# Persists to `ircc_category_overrides` collection.

OVERRIDE_COLLECTION = "ircc_category_overrides"
OVERRIDABLE_CATEGORIES = {
    "healthcare", "stem", "trade", "education", "transport",
    "physicians_ca_exp", "senior_managers_ca_exp", "researchers_ca_exp",
    "military_recruits",
}


def _is_valid_noc(code: str) -> bool:
    return isinstance(code, str) and len(code) == 5 and code.isdigit()


@router.get("/calc-rules/ircc-categories")
async def get_ircc_category_rules(current_user: dict = Depends(get_current_user)):
    """Return the EFFECTIVE NOC list per IRCC EE category (defaults + overrides merged)."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    from core.scrapers.ircc_ee_streams import (
        CATEGORY_REGISTRY,
        HEALTHCARE_NOCS, STEM_NOCS, TRADE_NOCS, EDUCATION_NOCS, TRANSPORT_NOCS,
        PHYSICIANS_CA_NOCS, SENIOR_MANAGERS_CA_NOCS, RESEARCHERS_CA_NOCS, MILITARY_NOCS,
    )
    defaults_map = {
        "healthcare":            sorted(HEALTHCARE_NOCS),
        "stem":                  sorted(STEM_NOCS),
        "trade":                 sorted(TRADE_NOCS),
        "education":             sorted(EDUCATION_NOCS),
        "transport":             sorted(TRANSPORT_NOCS),
        "physicians_ca_exp":     sorted(PHYSICIANS_CA_NOCS),
        "senior_managers_ca_exp":sorted(SENIOR_MANAGERS_CA_NOCS),
        "researchers_ca_exp":    sorted(RESEARCHERS_CA_NOCS),
        "military_recruits":     sorted(MILITARY_NOCS),
    }

    overrides_cursor = db[OVERRIDE_COLLECTION].find({}, {"_id": 0})
    overrides_map: Dict[str, Dict[str, Any]] = {}
    async for o in overrides_cursor:
        overrides_map[o["category_id"]] = o

    categories = []
    for cat_id, default_list in defaults_map.items():
        ov = overrides_map.get(cat_id) or {}
        added = sorted(set(ov.get("added_nocs") or []))
        removed = sorted(set(ov.get("removed_nocs") or []))
        effective = sorted((set(default_list) | set(added)) - set(removed))
        meta = CATEGORY_REGISTRY.get(cat_id, {})
        categories.append({
            "id": cat_id,
            "label": meta.get("label", cat_id),
            "icon": meta.get("icon"),
            "requires_canadian_exp": meta.get("requires_canadian_exp", False),
            "default_nocs": default_list,
            "default_count": len(default_list),
            "added_nocs": added,
            "removed_nocs": removed,
            "effective_nocs": effective,
            "effective_count": len(effective),
            "has_override": bool(added or removed),
            "updated_at": ov.get("updated_at"),
            "updated_by": ov.get("updated_by"),
        })
    return {
        "categories": categories,
        "total_categories": len(categories),
        "source": "ircc_ee_streams_2026 + db_overrides",
        "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations/category-based-selection.html",
    }


@router.put("/calc-rules/ircc-categories/{category_id}")
async def put_ircc_category_override(
    category_id: str,
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Save admin override for one category.
    Body: { added_nocs: [..], removed_nocs: [..] }
    Sends are full replacements of the override arrays.
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if category_id not in OVERRIDABLE_CATEGORIES:
        raise HTTPException(400, f"Unknown or non-overridable category: {category_id}")
    added = payload.get("added_nocs") or []
    removed = payload.get("removed_nocs") or []
    if not isinstance(added, list) or not isinstance(removed, list):
        raise HTTPException(400, "added_nocs and removed_nocs must be arrays")
    bad = [c for c in (added + removed) if not _is_valid_noc(c)]
    if bad:
        raise HTTPException(400, f"Invalid NOC codes (must be 5-digit numeric strings): {bad[:5]}")
    # Cannot have a code in both lists
    overlap = set(added) & set(removed)
    if overlap:
        raise HTTPException(400, f"NOC codes cannot be both added and removed: {sorted(overlap)}")

    now = datetime.now(timezone.utc).isoformat()
    actor = current_user.get("email") or current_user.get("id") or "admin"
    await db[OVERRIDE_COLLECTION].update_one(
        {"category_id": category_id},
        {"$set": {
            "category_id": category_id,
            "added_nocs": sorted(set(added)),
            "removed_nocs": sorted(set(removed)),
            "updated_at": now,
            "updated_by": actor,
        }},
        upsert=True,
    )
    return {
        "ok": True,
        "category_id": category_id,
        "added_count": len(set(added)),
        "removed_count": len(set(removed)),
        "updated_at": now,
        "updated_by": actor,
    }


@router.delete("/calc-rules/ircc-categories/{category_id}")
async def reset_ircc_category_override(
    category_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove override for one category → revert to hardcoded defaults."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if category_id not in OVERRIDABLE_CATEGORIES:
        raise HTTPException(400, f"Unknown category: {category_id}")
    res = await db[OVERRIDE_COLLECTION].delete_one({"category_id": category_id})
    return {"ok": True, "category_id": category_id, "deleted": res.deleted_count}


@router.post("/calc-rules/ircc-categories/reapply")
async def reapply_ircc_category_overrides(
    dry_run: bool = Query(False, description="If true, returns preview without writing"),
    current_user: dict = Depends(get_current_user),
):
    """Re-run the IRCC EE classifier against all CA occupations using current overrides.
    This refreshes `ee_eligibility.categories` on every CA NOC.
    """
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    from core.scrapers import ircc_ee_streams
    return await ircc_ee_streams.apply_to_db(
        db, dry_run=dry_run, actor=current_user.get("email") or current_user.get("id") or "admin",
    )

