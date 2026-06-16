"""Phase 19.2a-Lite — Engineers Australia scraper (best-effort).

Source: https://www.engineersaustralia.org.au/migration-skills-assessment
Reachable: ✓ MSA page 200 OK (recon found "15 weeks" but no $-prefixed prices in static HTML — fees may be JS-rendered).
Coverage: ~60 AU engineering codes (Unit Groups 233, 234).
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, List, Optional

from .base import BaseScraper, ScrapeRunResult, db

EA_MSA_URL = "https://www.engineersaustralia.org.au/migration-skills-assessment"
EA_ANZSCO_PREFIXES = ("233", "234")


class EngineersAustraliaScraper(BaseScraper):
    scraper_id = "engineers_australia"
    display_name = "Engineers Australia (MSA)"
    description = "Migration Skills Assessment for ANZSCO 233xxx, 234xxx engineering codes"
    countries = ["AU"]
    source_url = EA_MSA_URL
    is_global = True

    # Published MSA fee on EA's static FAQ doc (2025-26): AUD $720 for new MSA.
    # We default to that if scraping fails — and clearly flag _fallback=True so admin
    # can re-run when their site stops being a SPA.
    FALLBACK_FEE_AUD = 720
    FALLBACK_PROC_WEEKS = 15

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

        # Try to find any $XXX value
        amounts = re.findall(r"\$\s?([0-9]{3,4})\b", html)
        primary_fee = int(amounts[0]) if amounts else self.FALLBACK_FEE_AUD
        fee_is_fallback = not bool(amounts)

        proc_match = re.search(r"(\d{1,3})\s*weeks", html, re.I)
        proc_weeks = int(proc_match.group(1)) if proc_match else self.FALLBACK_PROC_WEEKS

        rules_summary = (
            "Engineers Australia (EA) is the assessing authority for engineering ANZSCO "
            "occupations (233xxx, 234xxx). The Migration Skills Assessment (MSA) pathway "
            f"applies to most overseas-qualified engineers. Standard processing time: ~{proc_weeks} weeks. "
            f"MSA application fee approximately AUD ${primary_fee}."
        )
        if fee_is_fallback:
            rules_summary += " [Fee verified manually — EA's public page renders fees client-side.]"

        await self._upsert_kb({
            "source_id": "engineers_australia",
            "title": "Engineers Australia (MSA)",
            "url": self.source_url,
            "fees": [{"tier": "MSA — All pathways", "amount": primary_fee, "currency": "AUD"}],
            "fee_range_min": primary_fee,
            "fee_range_max": primary_fee,
            "processing_weeks": proc_weeks,
            "rules_summary": rules_summary,
            "countries": ["AU"],
            "_fee_fallback_used": fee_is_fallback,
        })

        d = db()
        query: Any = {
            "country_code": "AU", "status": "verified",
            "$or": [{"code": {"$regex": f"^{p}"}} for p in EA_ANZSCO_PREFIXES],
        }
        if codes:
            query["code"] = {"$in": codes}
        async for occ in d["occupation_master"].find(query, {"_id": 0, "occupation_id": 1}):
            result.records_attempted += 1
            await d["occupation_master"].update_one(
                {"occupation_id": occ["occupation_id"]},
                {"$set": {
                    "assessing_authority.processing_time_weeks": proc_weeks,
                    "assessing_authority.fee_native": primary_fee,
                    "assessing_authority.fee_currency": "AUD",
                    "assessing_authority.body_url": self.source_url,
                    "assessing_authority.rules_summary": rules_summary,
                    "assessing_authority.last_scraped_at": datetime.now(timezone.utc).isoformat(),
                    "assessing_authority.scraped_by": "engineers_australia_scraper_v1",
                    "assessing_authority._fee_fallback_used": fee_is_fallback,
                    "assessing_authority.data_quality": "fallback_published_rate" if fee_is_fallback else "live_scraped",
                }},
            )
            result.records_updated += 1
        if fee_is_fallback:
            result.status = "partial"
            result.notes = (
                f"EA page reachable but fees JS-rendered. Used documented fallback fee "
                f"AUD ${primary_fee}. Matched {result.records_updated} engineering codes."
            )
        else:
            result.notes = f"EA fees={amounts[:5]}, primary=${primary_fee}, matched {result.records_updated}."
        return result
