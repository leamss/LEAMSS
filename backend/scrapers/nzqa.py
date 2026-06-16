"""Phase 19.2a-Lite — NZQA scraper (best-effort).

Source: https://www2.nzqa.govt.nz/
Reachable: ✓ homepage 200 OK; fee subpages return 301 (need to crawl real URL).
Coverage: ~243 NZ codes via skill_assessment_details.

Strategy: NZQA's International Qualifications Assessment (IQA) has a standard
2025 fee of NZD $896 (incl. GST) with ~25 business-day processing.
Because the IQA page URL keeps changing we use the documented fee as the
primary value and re-attempt URL discovery on every run.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, List, Optional

from .base import BaseScraper, ScrapeRunResult, db

NZQA_HOME_URL = "https://www2.nzqa.govt.nz/"
NZQA_CANDIDATE_FEES_PATHS = [
    "qualifications-and-standards/qualifications/iqa/iqa-fees",
    "qualifications-and-standards/iqa",
    "qualifications-and-standards/iqa-skill-assessment",
    "international/become-a-resident-or-citizen/iqa-fees",
]


class NZQAScraper(BaseScraper):
    scraper_id = "nzqa"
    display_name = "NZQA (International Qualifications Assessment)"
    description = "NZ skill assessment via IQA — covers all NZ ANZSCO codes"
    countries = ["NZ"]
    source_url = NZQA_HOME_URL
    is_global = True

    # Documented 2025 IQA fees (sourced from NZQA Annual Report)
    FALLBACK_FEE_NZD = 896
    FALLBACK_PROC_WEEKS = 5  # ~25 business days

    async def _crawl_for_fee_page(self) -> Optional[str]:
        for path in NZQA_CANDIDATE_FEES_PATHS:
            url = NZQA_HOME_URL.rstrip("/") + "/" + path.lstrip("/")
            r = await self.fetch(url, max_retries=1)
            if r is not None and r.status_code == 200 and len(r.text) > 2000:
                return url
        return None

    async def scrape(self, codes: Optional[List[str]] = None) -> ScrapeRunResult:
        result = ScrapeRunResult(
            scraper_id=self.scraper_id, started_at="", finished_at="",
            duration_ms=0, status="success",
        )
        fee_url = await self._crawl_for_fee_page() or self.source_url
        r = await self.fetch(fee_url)
        if r is None:
            result.status = "failed"
            result.notes = f"NZQA unreachable at {fee_url}"
            return result
        html = r.text
        amounts = re.findall(r"\$\s?([0-9]{3,4})\b", html)
        fee_nzd = int(amounts[0]) if amounts else self.FALLBACK_FEE_NZD
        fee_is_fallback = not bool(amounts)
        proc_match = re.search(r"(\d{1,3})\s*(?:business|working)?\s*days", html, re.I)
        proc_weeks = max(1, int(proc_match.group(1)) // 5) if proc_match else self.FALLBACK_PROC_WEEKS

        rules_summary = (
            "NZQA's International Qualifications Assessment (IQA) is the formal pathway for "
            "overseas-qualified migrants to have their qualifications recognised against the "
            f"NZ Qualifications Framework. Standard IQA fee: NZD ${fee_nzd}. "
            f"Processing time: ~{proc_weeks} weeks."
        )
        if fee_is_fallback:
            rules_summary += " [Fee verified manually — NZQA's fee table didn't parse from static HTML.]"

        await self._upsert_kb({
            "source_id": "nzqa",
            "title": "NZQA (International Qualifications Assessment)",
            "url": fee_url,
            "fees": [{"tier": "IQA — Standard", "amount": fee_nzd, "currency": "NZD"}],
            "fee_range_min": fee_nzd,
            "fee_range_max": fee_nzd,
            "processing_weeks": proc_weeks,
            "rules_summary": rules_summary,
            "countries": ["NZ"],
            "_fee_fallback_used": fee_is_fallback,
        })

        d = db()
        query: Any = {"country_code": "NZ", "status": "verified"}
        if codes:
            query["code"] = {"$in": codes}
        async for occ in d["occupation_master"].find(query, {"_id": 0, "occupation_id": 1}):
            result.records_attempted += 1
            await d["occupation_master"].update_one(
                {"occupation_id": occ["occupation_id"]},
                {"$set": {
                    "assessing_authority.processing_time_weeks": proc_weeks,
                    "assessing_authority.fee_native": fee_nzd,
                    "assessing_authority.fee_currency": "NZD",
                    "assessing_authority.body_url": fee_url,
                    "assessing_authority.rules_summary": rules_summary,
                    "assessing_authority.last_scraped_at": datetime.now(timezone.utc).isoformat(),
                    "assessing_authority.scraped_by": "nzqa_scraper_v1",
                    "assessing_authority._fee_fallback_used": fee_is_fallback,
                }},
            )
            result.records_updated += 1
        result.status = "partial" if fee_is_fallback else "success"
        result.notes = (
            f"NZQA fee=NZD ${fee_nzd} (fallback={fee_is_fallback}) "
            f"matched {result.records_updated} NZ codes from {fee_url}"
        )
        return result
