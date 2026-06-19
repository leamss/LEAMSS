"""Phase 20.6 — VFSglobal URL health verifier.

Reads `backend/data/vfsglobal_country_map.json`, pings every non-null URL using
httpx async client with 10s timeout + follow redirects, categorises results.

Run: cd /app/backend && python3 scripts/verify_vfsglobal_urls.py
Output: /app/memory/seeds/vfsglobal_url_health.json
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "vfsglobal_country_map.json"
OUT_PATH = Path("/app/memory/seeds/vfsglobal_url_health.json")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

SEMAPHORE_LIMIT = 10
TIMEOUT_SECONDS = 10
USER_AGENT = "LEAMSS-Phase20.6-URLChecker/1.0"


def build_url(slug: str) -> str:
    return f"https://visa.vfsglobal.com/ind/en/{slug}/"


def alternate_url(slug: str) -> List[str]:
    """Alternative URL patterns to try if primary fails."""
    return [
        f"https://visa.vfsglobal.com/in/en/{slug}/",     # alt pattern 1
        f"https://www.vfsglobal.com/in/en/{slug}/",      # alt pattern 2
    ]


async def check_one(client: httpx.AsyncClient, country: str, slug: str, sem: asyncio.Semaphore) -> Dict[str, Any]:
    async with sem:
        primary = build_url(slug)
        result = {
            "country": country, "slug": slug,
            "primary_url": primary,
            "status_code": None, "final_url": None,
            "category": "unknown", "elapsed_ms": None,
            "tried_alternates": [],
        }
        urls_to_try = [primary] + alternate_url(slug)
        for url in urls_to_try:
            start = time.time()
            try:
                r = await client.get(url, follow_redirects=True, timeout=TIMEOUT_SECONDS,
                                     headers={"User-Agent": USER_AGENT})
                result["elapsed_ms"] = int((time.time() - start) * 1000)
                result["status_code"] = r.status_code
                result["final_url"] = str(r.url)
                if r.status_code == 200:
                    if str(r.url) != url:
                        result["category"] = "redirect_ok"
                    else:
                        result["category"] = "healthy"
                    if url != primary:
                        result["working_url"] = url
                    return result
                elif r.status_code == 404:
                    result["category"] = "404_dead"
                    if url != primary:
                        result["tried_alternates"].append({"url": url, "status": 404})
                        continue
                elif r.status_code >= 500:
                    result["category"] = "5xx_server_error"
                elif r.status_code in (403, 429):
                    # CDN/firewall — counts as "live but blocked"
                    result["category"] = "blocked_or_rate_limited"
                    return result
                else:
                    result["category"] = f"http_{r.status_code}"
                # Continue to next alternate
                if url != primary:
                    result["tried_alternates"].append({"url": url, "status": r.status_code})
            except httpx.TimeoutException:
                result["category"] = "timeout"
                result["elapsed_ms"] = int((time.time() - start) * 1000)
                if url != primary:
                    result["tried_alternates"].append({"url": url, "status": "timeout"})
            except Exception as e:  # noqa: BLE001
                result["category"] = f"error:{type(e).__name__}"
                result["error"] = str(e)[:120]
                if url != primary:
                    result["tried_alternates"].append({"url": url, "status": str(e)[:60]})
        return result


async def main():
    map_data = json.loads(MAP_PATH.read_text())
    countries = map_data["countries"]
    targets = [(c, s) for c, s in countries.items() if s]
    null_count = sum(1 for s in countries.values() if not s)
    print(f"Loaded {len(countries)} countries · {len(targets)} have VFS slug · {null_count} marked null")

    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    async with httpx.AsyncClient(verify=False) as client:
        results = await asyncio.gather(*[
            check_one(client, c, s, sem) for c, s in targets
        ])

    # Categorise
    by_cat: Dict[str, List[str]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r["country"])

    summary = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "map_file": str(MAP_PATH),
        "total_with_slug": len(targets),
        "total_null_slug": null_count,
        "categories": {k: sorted(v) for k, v in by_cat.items()},
        "counts_by_category": {k: len(v) for k, v in by_cat.items()},
        "results": results,
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2))
    print(f"\n=== VFS URL Health Report ===")
    for cat, names in sorted(by_cat.items()):
        print(f"  {cat:25s} ({len(names):2d}) : {', '.join(names[:6])}{' ...' if len(names) > 6 else ''}")
    print(f"\nReport saved → {OUT_PATH}")
    return summary


if __name__ == "__main__":
    asyncio.run(main())
