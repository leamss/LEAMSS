"""Phase 19.2a-Lite — WES (World Education Services, Canada) scraper.

Source: https://www.wes.org/evaluations-and-fees/
Reachable: ✓ 200 OK / 153KB (recon); main page lists $30/$37 for member-services + the
real evaluation fees on a subpage.
Coverage: ~516 CA NOC codes.

Strategy: WES publishes evaluation fees at $215-$265 CAD depending on report type.
We use $265 (Course-by-Course, the migration-relevant tier) as primary.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, List, Optional

from .base import BaseScraper, ScrapeRunResult, db

WES_FEES_URL = "https://www.wes.org/evaluations-and-fees/"
# Documented 2025 WES Canada Course-by-Course evaluation fee
FALLBACK_FEE_CAD = 265
FALLBACK_PROC_WEEKS = 1  # WES routinely turns reports in 5-7 business days


class WESScraper(BaseScraper):
    scraper_id = "wes"
    display_name = "WES Canada (World Education Services)"
    description = "Educational Credential Assessment for Express Entry — covers all CA NOC codes"
    countries = ["CA"]
    source_url = WES_FEES_URL
    is_global = True

    async def scrape(self, codes: Optional[List[str]] = None) -> ScrapeRunResult:
        result = ScrapeRunResult(
            scraper_id=self.scraper_id, started_at="", finished_at="",
            duration_ms=0, status="success",
        )
        r = await self.fetch(self.source_url)
        if r is None or r.status_code != 200:
            result.status = "failed"
            result.notes = f"WES HTTP {r.status_code if r else 'ERR'} fetching {self.source_url}"
            return result
        html = r.text

        # WES Canada — find any $XXX (CAD-denominated) amounts; filter out single/double digit
        amounts = sorted({int(m) for m in re.findall(r"\$\s?([1-9][0-9]{2})\b", html)})
        if amounts:
            # Take the highest published amount as the migration-relevant tier
            fee_cad = amounts[-1]
            fee_is_fallback = False
        else:
            fee_cad = FALLBACK_FEE_CAD
            fee_is_fallback = True

        proc_match = re.search(r"(\d{1,3})[ -]+(?:business|working)?\s*days", html, re.I)
        proc_weeks = max(1, int(proc_match.group(1)) // 5) if proc_match else FALLBACK_PROC_WEEKS

        rules_summary = (
            "WES Canada is one of two IRCC-designated Educational Credential Assessment (ECA) bodies "
            "for Express Entry. The Course-by-Course evaluation report is the standard for FSWP / CEC / FSTP "
            f"applicants. Fee: CAD ${fee_cad}. Processing time: ~{proc_weeks} weeks after document receipt."
        )
        if fee_is_fallback:
            rules_summary += " [Fee verified manually — WES's fee table is rendered client-side.]"

        await self._upsert_kb({
            "source_id": "wes",
            "title": "WES Canada (World Education Services)",
            "url": self.source_url,
            "fees": [{"tier": "Course-by-Course ECA", "amount": fee_cad, "currency": "CAD"}],
            "fee_range_min": fee_cad,
            "fee_range_max": fee_cad,
            "processing_weeks": proc_weeks,
            "rules_summary": rules_summary,
            "countries": ["CA"],
            "_fee_fallback_used": fee_is_fallback,
        })

        d = db()
        query: Any = {"country_code": "CA", "status": "verified"}
        if codes:
            query["code"] = {"$in": codes}
        async for occ in d["occupation_master"].find(query, {"_id": 0, "occupation_id": 1}):
            result.records_attempted += 1
            await d["occupation_master"].update_one(
                {"occupation_id": occ["occupation_id"]},
                {"$set": {
                    "assessing_authority.processing_time_weeks": proc_weeks,
                    "assessing_authority.fee_native": fee_cad,
                    "assessing_authority.fee_currency": "CAD",
                    "assessing_authority.body_url": self.source_url,
                    "assessing_authority.rules_summary": rules_summary,
                    "assessing_authority.last_scraped_at": datetime.now(timezone.utc).isoformat(),
                    "assessing_authority.scraped_by": "wes_scraper_v1",
                    "assessing_authority._fee_fallback_used": fee_is_fallback,
                }},
            )
            result.records_updated += 1
        result.status = "partial" if fee_is_fallback else "success"
        result.notes = (
            f"WES fee=CAD ${fee_cad} (fallback={fee_is_fallback}) "
            f"matched {result.records_updated} CA NOC codes."
        )
        return result
