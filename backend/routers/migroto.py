"""Migroto Australian Skilled Migration Intelligence Router.

Integrates real-time ANZSCO data, visa invitation history, EOI backlog,
state nomination programs, and points distribution into LEAMSS Portal.
All endpoints are additive and do not alter existing functionality.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.auth import get_current_user
from services.migroto_service import migroto_service

router = APIRouter(prefix="/migroto", tags=["Migroto Skilled Migration"])

ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}
STAFF_ROLES = {"admin", "admin_owner", "super_admin", "sales", "case_manager", "partner"}


def _can_read(user: Dict[str, Any]) -> bool:
    role = (user or {}).get("role", "") or (user or {}).get("rbac_role", "")
    return role in STAFF_ROLES or "*" in (user.get("permissions") or [])


def _can_write(user: Dict[str, Any]) -> bool:
    role = (user or {}).get("role", "") or (user or {}).get("rbac_role", "")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


class BatchSyncRequest(BaseModel):
    codes: List[str]


@router.get("/status")
async def get_migroto_status(user: Dict[str, Any] = Depends(get_current_user)):
    """Check connectivity to Migroto API, API key validity, and cached status."""
    if not _can_read(user):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Run a quick check with filter endpoint
    filters = await migroto_service.get_occupation_filters()
    has_key = bool(migroto_service._get_api_key())
    is_connected = filters.get("status") == "success"

    return {
        "ok": is_connected,
        "configured": has_key,
        "scraper_id": migroto_service.scraper_id,
        "base_url": migroto_service.base_url,
        "states_available": len(filters.get("data", {}).get("states", [])),
        "subclasses": [s.get("subclass_number") for s in filters.get("data", {}).get("subclasses", [])],
        "cached": filters.get("cached", False),
    }


@router.get("/search")
async def search_occupations(
    query: str = Query(..., min_length=1, description="Occupation name or ANZSCO code"),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Full-text search over Australian skilled migration occupations by name or ANZSCO code."""
    if not _can_read(user):
        raise HTTPException(status_code=403, detail="Forbidden")

    return await migroto_service.search_occupations(query)


@router.get("/filters")
async def get_filters(
    refresh: bool = False,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieve Australian states, visa subclasses, financial year ranges, and EOI backlog dates."""
    if not _can_read(user):
        raise HTTPException(status_code=403, detail="Forbidden")

    return await migroto_service.get_occupation_filters(use_cache=not refresh)


@router.get("/occupation/{code}")
async def get_occupation_details(
    code: str,
    occupation_id: Optional[str] = Query(None),
    inv_subclass: Optional[str] = Query(None),
    eoi_subclass: Optional[str] = Query(None),
    trend_year_range: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieve comprehensive migration data for a single occupation identified by its ANZSCO code.

    Includes visa subclass eligibility, invitation history, EOI backlog, state nomination programs, and points distribution.
    """
    if not _can_read(user):
        raise HTTPException(status_code=403, detail="Forbidden")

    return await migroto_service.get_occupation_details(
        code=code,
        occupation_id=occupation_id,
        inv_subclass=inv_subclass,
        eoi_subclass=eoi_subclass,
        trend_year_range=trend_year_range,
    )


@router.post("/verify/{code}")
async def verify_occupation(
    code: str,
    title: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Verification Hub: Verifies an ANZSCO code against the official Migroto registry."""
    if not _can_read(user):
        raise HTTPException(status_code=403, detail="Forbidden")

    return await migroto_service.verify_anzsco_code(code=code, expected_title=title)


@router.post("/sync/{code}")
async def sync_occupation(
    code: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Admin only: Enriches LEAMSS occupation_master with live Migroto migration intelligence."""
    if not _can_write(user):
        raise HTTPException(status_code=403, detail="Admin role required")

    res = await migroto_service.enrich_occupation_master(code=code, force_refresh=True)
    if res.get("status") == "success":
        try:
            from routers.seo_ssg import regenerate_one
            await regenerate_one("AU", code)
        except Exception as e:
            pass
    return res


@router.post("/batch-sync")
async def batch_sync_occupations(
    req: BatchSyncRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Admin only: Enriches a list of occupation codes with live Migroto intelligence."""
    if not _can_write(user):
        raise HTTPException(status_code=403, detail="Admin role required")

    results = []
    for code in req.codes[:50]:  # Limit batch to 50
        res = await migroto_service.enrich_occupation_master(code)
        results.append(res)

    return {
        "status": "success",
        "total_requested": len(req.codes),
        "synced": sum(1 for r in results if r.get("status") == "success"),
        "results": results,
    }


@router.get("/audit")
async def audit_coverage(user: Dict[str, Any] = Depends(get_current_user)):
    """Atlas Coverage Audit: Audits LEAMSS Australian occupations against Migroto official registry."""
    if not _can_read(user):
        raise HTTPException(status_code=403, detail="Forbidden")

    return await migroto_service.audit_atlas_migroto_coverage()
