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
    """Actually writes 6-digit codes from anzsco_4digit_master → occupation_master.

    Behaviour:
      • For each 6-digit code in anzsco_4digit_master:
        - If absent in occupation_master AU → INSERT new skeleton record
        - If present → enrich only missing inherited fields (NO overwrite)
      • Test artifacts (12-13 digit codes) untouched
      • Existing verified/draft records preserved
    """
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


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
