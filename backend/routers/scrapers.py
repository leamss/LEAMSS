"""Phase 19.2a-Lite — Scraper Hub admin endpoints.

Endpoints:
  GET  /api/scrapers/all-status   — admin only, list of all scrapers + last_run summary
  GET  /api/scrapers/{id}/status  — admin only, single scraper detail
  POST /api/scrapers/{id}/run     — admin only, kicks off scrape (optional codes payload)
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import get_current_user
from scrapers.abs_census import ABSCensusScraper
from scrapers.acs import ACSScraper
from scrapers.engineers_australia import EngineersAustraliaScraper
from scrapers.nzqa import NZQAScraper
from scrapers.vetassess import VETASSESSScraper
from scrapers.wes import WESScraper
from scrapers.base import db

router = APIRouter(prefix="/scrapers", tags=["scrapers"])

# Single source of truth — registry of all available scrapers
_SCRAPERS: Dict[str, Any] = {
    s.scraper_id: s for s in [
        ACSScraper(),
        VETASSESSScraper(),
        EngineersAustraliaScraper(),
        NZQAScraper(),
        WESScraper(),
        ABSCensusScraper(),
    ]
}


def _is_admin(user: Dict[str, Any]) -> bool:
    role = (user or {}).get("role", "")
    return role in ("admin", "super_admin")


def _require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def _meta(s) -> Dict[str, Any]:
    return {
        "scraper_id": s.scraper_id,
        "display_name": s.display_name,
        "description": s.description,
        "countries": s.countries,
        "source_url": s.source_url,
    }


async def _latest_run_for(scraper_id: str) -> Optional[Dict[str, Any]]:
    cursor = db()["audit_logs"].find(
        {"action": "scraper_run", "scraper_id": scraper_id}
    ).sort("created_at", -1).limit(1)
    async for row in cursor:
        row.pop("_id", None)
        if isinstance(row.get("created_at"), datetime):
            row["created_at"] = row["created_at"].isoformat()
        return row
    return None


@router.get("/all-status")
async def all_status(user: Dict[str, Any] = Depends(_require_admin)):
    out: List[Dict[str, Any]] = []
    for sid, s in _SCRAPERS.items():
        meta = _meta(s)
        latest = await _latest_run_for(sid)
        meta["latest_run"] = latest
        out.append(meta)
    return {"scrapers": out, "count": len(out)}


@router.get("/{scraper_id}/status")
async def one_status(scraper_id: str, user: Dict[str, Any] = Depends(_require_admin)):
    s = _SCRAPERS.get(scraper_id)
    if not s:
        raise HTTPException(404, "Unknown scraper")
    return {**_meta(s), "latest_run": await _latest_run_for(scraper_id)}


class RunRequest(BaseModel):
    codes: Optional[List[str]] = None


@router.post("/{scraper_id}/run")
async def run_scraper(
    scraper_id: str,
    req: Optional[RunRequest] = None,
    user: Dict[str, Any] = Depends(_require_admin),
):
    s = _SCRAPERS.get(scraper_id)
    if not s:
        raise HTTPException(404, "Unknown scraper")
    codes = req.codes if req else None
    result = await s.run(codes=codes)
    # Coerce dataclass-like into dict
    return {
        "scraper_id": result.scraper_id,
        "status": result.status,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "duration_ms": result.duration_ms,
        "records_attempted": result.records_attempted,
        "records_updated": result.records_updated,
        "records_skipped": result.records_skipped,
        "errors": result.errors,
        "notes": result.notes,
    }


def list_scraper_objects():
    """Used by APScheduler for the monthly nightly chain."""
    return list(_SCRAPERS.values())


@router.get("/scheduler-status")
async def scheduler_status(user: Dict[str, Any] = Depends(_require_admin)):
    """Phase 19.2c — Introspect APScheduler to verify monthly scraper crons.

    Returns list of registered job IDs + next-run timestamps so tests/ops can
    confirm the 5 scraper monthly crons are actually scheduled.
    """
    try:
        import server  # noqa: PLC0415
        sched = getattr(server, "_digest_scheduler", None)
        if sched is None:
            return {"running": False, "jobs": [], "scraper_jobs": []}
        jobs = []
        scraper_jobs = []
        for j in sched.get_jobs():
            row = {
                "id": j.id,
                "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
                "trigger": str(j.trigger),
            }
            jobs.append(row)
            if j.id.startswith("scraper_monthly_"):
                scraper_jobs.append(j.id)
        return {
            "running": sched.running,
            "jobs": jobs,
            "scraper_jobs": sorted(scraper_jobs),
            "scraper_job_count": len(scraper_jobs),
        }
    except Exception as e:  # noqa: BLE001
        return {"running": False, "error": str(e), "jobs": [], "scraper_jobs": []}
