"""Phase 19.2a-Lite — BaseScraper

Shared retry / rate-limit / cache / UA / audit-log infrastructure for every
LEAMSS scraper. Concrete scrapers subclass this and implement ``scrape(codes)``
or, for site-wide scrapers like VETASSESS / ACS, ``scrape_global()`` to populate
the full set of occupations in one HTTP call.

Hard rules (enforced here, not optional):
* User-Agent must start with ``LEAMSS-Scraper/`` (test_10 in 19.2a checks this).
* Minimum 1.0s sleep between consecutive same-host requests.
* Failures are written into the ``client_errors`` collection (Phase 18.6).
* Every ``run()`` writes one row into ``audit_logs`` with status + counts.
* 24-hour in-memory LRU cache keyed by ``(method, url, params)``.
"""
from __future__ import annotations
import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
_log = logging.getLogger("leamss.scrapers")

USER_AGENT = "LEAMSS-Scraper/1.0 (+https://leamss.com/about)"
MIN_SLEEP_SECONDS = 1.0
CACHE_TTL_HOURS = 24
HTTP_TIMEOUT = 25.0

_mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
_db = _mongo[os.environ["DB_NAME"]]

# In-memory LRU-ish cache: {hash: (expires_at, body, status, headers)}
_cache: Dict[str, tuple] = {}
_last_host_fetch: Dict[str, float] = {}


def _cache_key(method: str, url: str, params: Optional[Dict[str, Any]] = None) -> str:
    seed = f"{method.upper()}|{url}|{sorted((params or {}).items())}"
    return hashlib.sha256(seed.encode()).hexdigest()


def _host(url: str) -> str:
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except Exception:  # noqa: BLE001
        return url


async def _polite_sleep(url: str) -> None:
    host = _host(url)
    last = _last_host_fetch.get(host, 0.0)
    delta = time.time() - last
    if delta < MIN_SLEEP_SECONDS:
        await asyncio.sleep(MIN_SLEEP_SECONDS - delta)
    _last_host_fetch[host] = time.time()


@dataclass
class ScrapeRunResult:
    scraper_id: str
    started_at: str
    finished_at: str
    duration_ms: int
    status: str  # "success" | "partial" | "failed" | "skipped"
    records_attempted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    notes: str = ""


class BaseScraper:
    """Subclasses must set ``scraper_id``, ``display_name``, ``countries``."""

    scraper_id: str = ""
    display_name: str = ""
    description: str = ""
    countries: List[str] = []
    source_url: str = ""
    # If True, the scraper writes one common payload to many occupation_master
    # records via per-row condition; if False, the scraper expects a list of
    # explicit ``codes`` to process.
    is_global: bool = False

    # ─────────────────────────────────────────────────────────────────────
    # HTTP helper (used by all subclasses)
    # ─────────────────────────────────────────────────────────────────────
    async def fetch(self, url: str, *, method: str = "GET",
                    params: Optional[Dict[str, Any]] = None,
                    headers: Optional[Dict[str, str]] = None,
                    accept: str = "text/html,application/xhtml+xml,application/xml",
                    use_cache: bool = True,
                    max_retries: int = 3) -> Optional[httpx.Response]:
        key = _cache_key(method, url, params)
        if use_cache and key in _cache:
            expires_at, body, status, hdrs = _cache[key]
            if expires_at > datetime.now(timezone.utc):
                _log.info(f"[{self.scraper_id}] CACHE hit {url[:80]}")
                # Strip content-encoding headers — body is already decoded
                clean_hdrs = {k: v for k, v in hdrs.items() if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")}
                req = httpx.Request(method, url)
                return httpx.Response(status, content=body, headers=clean_hdrs, request=req)
        await _polite_sleep(url)
        merged = {
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Language": "en-IN,en;q=0.9",
        }
        if headers:
            merged.update(headers)
        backoff = 1.0
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
                    r = await client.request(method, url, params=params, headers=merged)
                if r.status_code < 500:
                    if use_cache and r.status_code == 200:
                        # Cache the already-decoded text bytes, not raw
                        _cache[key] = (
                            datetime.now(timezone.utc) + timedelta(hours=CACHE_TTL_HOURS),
                            r.text.encode("utf-8"),
                            r.status_code,
                            dict(r.headers),
                        )
                    return r
                _log.warning(f"[{self.scraper_id}] HTTP {r.status_code} {url} (try {attempt+1}/{max_retries})")
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                _log.warning(f"[{self.scraper_id}] NET {type(e).__name__} {url} (try {attempt+1}/{max_retries}): {e}")
            await asyncio.sleep(backoff)
            backoff *= 2
        return None

    # ─────────────────────────────────────────────────────────────────────
    # Subclasses override one of these
    # ─────────────────────────────────────────────────────────────────────
    async def scrape(self, codes: Optional[List[str]] = None) -> ScrapeRunResult:
        raise NotImplementedError

    # ─────────────────────────────────────────────────────────────────────
    # Status / KB write helpers (shared)
    # ─────────────────────────────────────────────────────────────────────
    async def _write_audit(self, result: ScrapeRunResult) -> None:
        try:
            await _db["audit_logs"].insert_one({
                "action": "scraper_run",
                "scraper_id": self.scraper_id,
                "status": result.status,
                "records_attempted": result.records_attempted,
                "records_updated": result.records_updated,
                "records_skipped": result.records_skipped,
                "error_count": len(result.errors),
                "duration_ms": result.duration_ms,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
                "notes": result.notes,
                "created_at": datetime.now(timezone.utc),
            })
        except Exception as e:  # noqa: BLE001
            _log.error(f"audit write fail: {e}")
        if result.status in ("failed", "partial"):
            try:
                await _db["client_errors"].insert_one({
                    "message": f"Scraper {self.scraper_id} status={result.status}",
                    "route": f"/scrapers/{self.scraper_id}",
                    "occurrence_count": 1,
                    "resolved": False,
                    "is_synthetic": False,
                    "received_at": datetime.now(timezone.utc),
                    "details": {"errors": result.errors[:5], "notes": result.notes},
                })
            except Exception as e:  # noqa: BLE001
                _log.error(f"client_errors write fail: {e}")

    async def _upsert_kb(self, payload: Dict[str, Any]) -> None:
        """Write/update knowledge_base entry. payload must include source_id."""
        sid = payload.get("source_id")
        if not sid:
            return
        payload.setdefault("source_type", "assessing_authority")
        payload["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            await _db["knowledge_base"].update_one(
                {"source_id": sid},
                {"$set": payload},
                upsert=True,
            )
        except Exception as e:  # noqa: BLE001
            _log.error(f"KB upsert fail: {e}")

    # ─────────────────────────────────────────────────────────────────────
    # Orchestration: timing + audit + error capture
    # ─────────────────────────────────────────────────────────────────────
    async def run(self, codes: Optional[List[str]] = None) -> ScrapeRunResult:
        started = datetime.now(timezone.utc)
        t0 = time.time()
        try:
            result = await self.scrape(codes=codes)
            if not isinstance(result, ScrapeRunResult):  # defensive
                result = ScrapeRunResult(
                    scraper_id=self.scraper_id, started_at=started.isoformat(),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=int((time.time() - t0) * 1000), status="failed",
                    notes="scrape() returned non-ScrapeRunResult"
                )
        except Exception as e:  # noqa: BLE001
            _log.exception(f"[{self.scraper_id}] hard crash")
            result = ScrapeRunResult(
                scraper_id=self.scraper_id, started_at=started.isoformat(),
                finished_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=int((time.time() - t0) * 1000), status="failed",
                errors=[{"type": type(e).__name__, "message": str(e)[:200]}],
                notes=f"exception: {type(e).__name__}",
            )
        result.scraper_id = self.scraper_id
        result.started_at = started.isoformat()
        result.finished_at = datetime.now(timezone.utc).isoformat()
        result.duration_ms = int((time.time() - t0) * 1000)
        await self._write_audit(result)
        return result


def db():
    return _db
