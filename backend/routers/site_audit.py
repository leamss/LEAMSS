"""Phase 21 Slice 4 Sub-Slice A.1 — IT Site Audit Hub.

Runs lightweight static + live checks against the public surface and stores
a per-run report so the IT/Admin can monitor SEO/health regressions.

Checks:
  1. Meta tag completeness (title, description, OG, Twitter)
  2. JSON-LD validity (BreadcrumbList + FAQPage on Atlas, Organization on /start)
  3. H1/H2 hierarchy (exactly one H1, H2 nesting sane)
  4. Internal link health (sample of <a href="..."> resolves to 200)
  5. Image alt coverage (% of <img> tags with non-empty alt)

Rate limited: max 1 concurrent run per user · max 10 runs / day / workspace.
"""
import os
import re
import json
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.database import db
from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/site-audit", tags=["Site Audit"])

audits_col = db["site_audit_runs"]

# IT role gating — admin/admin_owner + IT-specific permissions.
_IT_VIEW = require_any_permission("it.view.all", "system.view.all", _legacy_role="admin")

ALLOWED_SCOPES = ("atlas", "start", "all")
DEFAULT_SAMPLE = 5
MAX_SAMPLE = 25
DAILY_RUN_CAP = 10
RUN_TTL_DAYS = 90

ATLAS_DIR = Path("/app/frontend/public/atlas")
PUBLIC_BASE = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:3000").rstrip("/")


class AuditRunRequest(BaseModel):
    scope: str = "all"
    sample_size: int = DEFAULT_SAMPLE


# ─────────────────────────── Helpers ────────────────────────────

def _collect_atlas_pages(limit: int) -> List[Path]:
    """Sample HTML files inside /app/frontend/public/atlas (SSG output)."""
    if not ATLAS_DIR.exists():
        return []
    files = list(ATLAS_DIR.rglob("*.html"))
    return files[:limit]


def _check_meta_tags(html: str) -> dict:
    """Returns {status, details: [..]}."""
    issues = []
    title = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if not title or not (title.group(1) or "").strip():
        issues.append("Missing or empty <title>")
    if not re.search(r'<meta[^>]+name=[\'"]description[\'"][^>]+content=[\'"][^\'"]+[\'"]', html, re.I):
        issues.append("Missing meta description")
    if not re.search(r'<meta[^>]+property=[\'"]og:title[\'"]', html, re.I):
        issues.append("Missing og:title")
    if not re.search(r'<meta[^>]+property=[\'"]og:description[\'"]', html, re.I):
        issues.append("Missing og:description")
    if not re.search(r'<meta[^>]+name=[\'"]twitter:card[\'"]', html, re.I):
        issues.append("Missing twitter:card")
    status = "pass" if not issues else ("warn" if len(issues) <= 2 else "fail")
    return {"status": status, "issues": issues}


def _check_jsonld(html: str, expect_types: List[str]) -> dict:
    """Validate JSON-LD blocks contain expected schema types."""
    blocks = re.findall(r'<script[^>]+type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', html, re.I | re.S)
    if not blocks:
        return {"status": "fail", "issues": ["No JSON-LD blocks found"], "found_types": []}
    found_types: List[str] = []
    parse_errors: List[str] = []
    for raw in blocks:
        try:
            data = json.loads(raw.strip())
            objs = data if isinstance(data, list) else [data]
            for obj in objs:
                if isinstance(obj, dict) and obj.get("@type"):
                    t = obj["@type"]
                    found_types.append(t if isinstance(t, str) else ",".join(t))
        except json.JSONDecodeError as e:
            parse_errors.append(f"JSON-LD parse error: {e.msg}")
    missing = [t for t in expect_types if not any(t.lower() in ft.lower() for ft in found_types)]
    issues = parse_errors + [f"Missing recommended schema: {m}" for m in missing]
    status = "pass" if not issues else ("warn" if not parse_errors and len(missing) <= 1 else "fail")
    return {"status": status, "issues": issues, "found_types": found_types}


def _check_h_hierarchy(html: str) -> dict:
    h1_count = len(re.findall(r"<h1\b", html, re.I))
    h2_count = len(re.findall(r"<h2\b", html, re.I))
    issues = []
    if h1_count == 0:
        issues.append("Missing <h1>")
    elif h1_count > 1:
        issues.append(f"Multiple H1s ({h1_count}) — should be exactly one")
    if h2_count == 0:
        issues.append("No <h2> sub-headings")
    status = "pass" if not issues else ("warn" if h1_count == 1 else "fail")
    return {"status": status, "issues": issues, "h1_count": h1_count, "h2_count": h2_count}


def _check_image_alt(html: str) -> dict:
    imgs = re.findall(r"<img\b[^>]*>", html, re.I)
    total = len(imgs)
    if total == 0:
        return {"status": "pass", "issues": [], "total_imgs": 0, "missing_alt": 0, "coverage_pct": 100}
    missing = sum(1 for tag in imgs if not re.search(r'\balt=[\'"][^\'"]+[\'"]', tag, re.I))
    pct = round((total - missing) / total * 100, 1)
    status = "pass" if pct >= 95 else ("warn" if pct >= 80 else "fail")
    issues = []
    if missing:
        issues.append(f"{missing}/{total} images missing non-empty alt text")
    return {"status": status, "issues": issues, "total_imgs": total, "missing_alt": missing, "coverage_pct": pct}


async def _check_internal_links(html: str, sample_size: int = 5) -> dict:
    """Sample internal anchors and probe HEAD/GET; <a href starting with /"""
    hrefs = re.findall(r'<a\b[^>]*href=[\'"](/[^\'"#]*)[\'"]', html, re.I)
    unique = []
    seen = set()
    for h in hrefs:
        if h not in seen and h not in ("/", ""):
            seen.add(h)
            unique.append(h)
    sample = unique[:sample_size]
    broken: List[dict] = []
    if not sample:
        return {"status": "pass", "issues": [], "checked": 0, "broken": []}
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
        for path in sample:
            try:
                r = await client.get(f"{PUBLIC_BASE}{path}")
                if r.status_code >= 400:
                    broken.append({"path": path, "status_code": r.status_code})
            except httpx.HTTPError as e:
                broken.append({"path": path, "status_code": -1, "error": str(e)[:120]})
    pct = (len(sample) - len(broken)) / max(len(sample), 1) * 100
    status = "pass" if not broken else ("warn" if pct >= 80 else "fail")
    return {
        "status": status,
        "issues": [f"{len(broken)}/{len(sample)} internal links failed"] if broken else [],
        "checked": len(sample),
        "broken": broken,
    }


# ─────────────────────────── Audit runner ────────────────────────────

async def _audit_one_page(html: str, page_url: str, expect_jsonld: List[str], sample_links: int) -> dict:
    return {
        "page_url": page_url,
        "meta_tags": _check_meta_tags(html),
        "json_ld": _check_jsonld(html, expect_jsonld),
        "h_hierarchy": _check_h_hierarchy(html),
        "image_alt": _check_image_alt(html),
        "internal_links": await _check_internal_links(html, sample_links),
    }


async def _run_audit_in_background(run_id: str, scope: str, sample_size: int) -> None:
    """Executes the audit and patches the run document with results."""
    try:
        pages: List[dict] = []  # collected results per-page
        sample_links = min(5, sample_size)

        # Atlas pages
        if scope in ("atlas", "all"):
            for fpath in _collect_atlas_pages(sample_size):
                try:
                    html = fpath.read_text(encoding="utf-8")[:200_000]
                    rel = "/" + str(fpath.relative_to(Path("/app/frontend/public"))).replace("\\", "/")
                    pages.append(await _audit_one_page(html, rel, ["BreadcrumbList", "FAQPage"], sample_links))
                except Exception as e:
                    logger.warning("Atlas page audit failed for %s: %s", fpath, e)

        # /start funnel (live fetch)
        if scope in ("start", "all"):
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    r = await client.get(f"{PUBLIC_BASE}/start")
                    if r.status_code == 200:
                        pages.append(await _audit_one_page(r.text[:200_000], "/start", ["Organization", "WebSite"], sample_links))
            except Exception as e:
                logger.warning("/start audit failed: %s", e)

        # Roll up summary
        summary = {"pass": 0, "warn": 0, "fail": 0}
        for p in pages:
            for k in ("meta_tags", "json_ld", "h_hierarchy", "image_alt", "internal_links"):
                summary[p[k]["status"]] += 1

        await audits_col.update_one(
            {"id": run_id},
            {"$set": {
                "status": "complete",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "pages_audited": len(pages),
                "summary": summary,
                "pages": pages,
            }},
        )
    except Exception as e:
        logger.exception("Site audit %s failed: %s", run_id, e)
        await audits_col.update_one(
            {"id": run_id},
            {"$set": {"status": "failed", "error": str(e)[:500], "finished_at": datetime.now(timezone.utc).isoformat()}},
        )


# ─────────────────────────── Endpoints ────────────────────────────

@router.post("/run")
async def kick_off_audit(req: AuditRunRequest, user: dict = Depends(_IT_VIEW)):
    if req.scope not in ALLOWED_SCOPES:
        raise HTTPException(status_code=400, detail=f"scope must be one of {ALLOWED_SCOPES}")
    sample_size = max(1, min(req.sample_size, MAX_SAMPLE))

    # Concurrency guard — single running audit per user
    in_flight = await audits_col.count_documents({"started_by": user["id"], "status": "running"})
    if in_flight > 0:
        raise HTTPException(status_code=409, detail="An audit is already running for your account — wait for it to finish")

    # Daily cap (workspace-wide)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    today_count = await audits_col.count_documents({"started_at": {"$gte": since.isoformat()}})
    if today_count >= DAILY_RUN_CAP:
        raise HTTPException(status_code=429, detail=f"Daily audit cap reached ({DAILY_RUN_CAP}/day). Try again tomorrow.")

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": run_id,
        "scope": req.scope,
        "sample_size": sample_size,
        "status": "running",
        "started_by": user["id"],
        "started_by_name": user.get("name"),
        "started_at": now.isoformat(),
        "expires_at": (now + timedelta(days=RUN_TTL_DAYS)).isoformat(),
    }
    await audits_col.insert_one(doc)

    # Fire-and-forget background task
    asyncio.create_task(_run_audit_in_background(run_id, req.scope, sample_size))
    return {"run_id": run_id, "status": "running", "scope": req.scope}


@router.get("/runs")
async def list_runs(limit: int = 25, user: dict = Depends(_IT_VIEW)):
    out = []
    async for r in audits_col.find({}, {"_id": 0, "pages": 0}).sort("started_at", -1).limit(min(limit, 100)):
        out.append(r)
    return out


@router.get("/runs/{run_id}")
async def run_detail(run_id: str, user: dict = Depends(_IT_VIEW)):
    r = await audits_col.find_one({"id": run_id}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    return r
