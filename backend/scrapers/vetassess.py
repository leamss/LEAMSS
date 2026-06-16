"""Phase 19.2a-Lite — VETASSESS scraper.

Source: https://www.vetassess.com.au/skills-assessment-for-migration/professional-occupations/skills-assessment-fees-for-professional-occupations
Reachable: ✓ confirmed in recon (200 OK, 86KB page with 10 tables, 15+ fee values)
Coverage: ~360 AU codes (broadest assessing body)
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseScraper, ScrapeRunResult, db

VETASSESS_FEES_URL = (
    "https://www.vetassess.com.au/skills-assessment-for-migration/"
    "professional-occupations/skills-assessment-fees-for-professional-occupations"
)
# VETASSESS covers a wide range — most non-IT, non-engineering, non-trade occupations.
# Heuristic: any AU verified record whose assessing_authority.name contains
# "VETASSESS" (case-insensitive) is in scope.
VETASSESS_BODY_NAME_PATTERN = re.compile(r"VETASSESS", re.I)


class VETASSESSScraper(BaseScraper):
    scraper_id = "vetassess"
    display_name = "VETASSESS"
    description = "Skills assessment for ~360 professional ANZSCO occupations"
    countries = ["AU"]
    source_url = VETASSESS_FEES_URL
    is_global = True

    async def scrape(self, codes: Optional[List[str]] = None) -> ScrapeRunResult:
        result = ScrapeRunResult(
            scraper_id=self.scraper_id, started_at="", finished_at="",
            duration_ms=0, status="success",
        )
        r = await self.fetch(self.source_url)
        if r is None or r.status_code != 200:
            result.status = "failed"
            result.notes = f"HTTP {r.status_code if r else 'ERR'} fetching {self.source_url}"
            return result
        html = r.text

        amounts = sorted(set(re.findall(r"\$\s?([0-9]{2,4}(?:\.[0-9]{2})?)", html)), key=lambda s: float(s))
        if not amounts:
            result.status = "partial"
            result.notes = "VETASSESS page reachable but no $-prefixed amounts parsed"
            result.errors.append({"type": "ParseError", "message": "no $ amounts found"})
        # Heuristic: VETASSESS Application — Skills Assessment ~ AUD 1190.20 (Full)
        # We pick the highest tier as primary (Full skills assessment).
        primary_fee = float(amounts[-1]) if amounts else None
        proc_match = re.search(r"(\d{1,3})\s*(?:working|business)?\s*(?:days|weeks)", html, re.I)
        proc_weeks: Optional[int] = None
        if proc_match:
            n = int(proc_match.group(1))
            unit = proc_match.group(0).lower()
            proc_weeks = n if "week" in unit else max(1, n // 5)  # business days → weeks
        rules_summary = (
            "VETASSESS is the largest skills assessing authority for general professional ANZSCO "
            "occupations. Full skills assessment fee approximately "
            f"AUD ${primary_fee:.2f} (varies by pathway). "
            + (f"Standard processing time: ~{proc_weeks} weeks." if proc_weeks else
               "Processing time varies by occupation and document quality.")
        )

        await self._upsert_kb({
            "source_id": "vetassess",
            "title": "VETASSESS",
            "url": self.source_url,
            "fees": [{"tier": "Full skills assessment", "amount": primary_fee, "currency": "AUD"}],
            "fee_range_min": float(amounts[0]) if amounts else None,
            "fee_range_max": float(amounts[-1]) if amounts else None,
            "fee_amounts_observed": amounts[:30],
            "processing_weeks": proc_weeks,
            "rules_summary": rules_summary,
            "countries": ["AU"],
        })

        d = db()
        query: Dict[str, Any] = {
            "country_code": "AU", "status": "verified",
            "assessing_authority.name": VETASSESS_BODY_NAME_PATTERN,
        }
        if codes:
            query["code"] = {"$in": codes}
        async for occ in d["occupation_master"].find(query, {"_id": 0, "occupation_id": 1}):
            result.records_attempted += 1
            update_doc: Dict[str, Any] = {
                "assessing_authority.fee_native": primary_fee,
                "assessing_authority.fee_currency": "AUD",
                "assessing_authority.body_url": self.source_url,
                "assessing_authority.rules_summary": rules_summary,
                "assessing_authority.last_scraped_at": datetime.now(timezone.utc).isoformat(),
                "assessing_authority.scraped_by": "vetassess_scraper_v1",
            }
            if proc_weeks is not None:
                update_doc["assessing_authority.processing_time_weeks"] = proc_weeks
            await d["occupation_master"].update_one(
                {"occupation_id": occ["occupation_id"]},
                {"$set": update_doc},
            )
            result.records_updated += 1
        result.notes = (
            f"VETASSESS amounts={amounts[:5]}... primary=${primary_fee} "
            f"proc={proc_weeks}w matched {result.records_updated}."
        )
        return result
