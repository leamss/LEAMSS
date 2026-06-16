"""Phase 19.2a-Lite + 19.2c — VETASSESS scraper.

Source: https://www.vetassess.com.au/skills-assessment-for-migration/professional-occupations/skills-assessment-fees-for-professional-occupations
Reachable: ✓ confirmed in recon (200 OK, 86KB page with 10 tables, 15+ fee values)
Coverage: 19.2a captured 0 records (assessing_authority.name=="VETASSESS" literal didn't match);
19.2c switches to a "catch-all for non-ICT, non-engineering AU verified records that don't
already have a fee" mapping — yields ~580 records.
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
# Codes covered by OTHER bodies — exclude from VETASSESS catch-all
OTHER_BODY_PREFIXES = ("261", "262", "263", "233", "234")  # ACS + EA


class VETASSESSScraper(BaseScraper):
    scraper_id = "vetassess"
    display_name = "VETASSESS"
    description = "Skills assessment for ~580 professional ANZSCO occupations (catch-all body)"
    countries = ["AU"]
    source_url = VETASSESS_FEES_URL
    is_global = True

    # Documented standard VETASSESS Full Skills Assessment fee + ~12 week processing
    DOCUMENTED_FEE_AUD = 1205.60
    DOCUMENTED_PROC_WEEKS = 12

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

        amounts = sorted({float(m) for m in re.findall(r"\$\s?([0-9]{2,4}(?:\.[0-9]{2})?)", html)})
        primary_fee = amounts[-1] if amounts else self.DOCUMENTED_FEE_AUD
        data_quality = "live_scraped" if amounts else "fallback_published_rate"
        proc_match = re.search(r"(\d{1,3})\s*weeks", html, re.I)
        proc_weeks = int(proc_match.group(1)) if proc_match else self.DOCUMENTED_PROC_WEEKS

        rules_summary = (
            "VETASSESS is the largest skills assessing authority for general professional ANZSCO "
            "occupations. Full skills assessment fee: "
            f"AUD ${primary_fee:.2f}. Standard processing time: ~{proc_weeks} weeks. "
            "VETASSESS is the default assessing body for occupations not covered by ACS (IT), "
            "Engineers Australia (engineering) or specialist bodies (medical/legal/trades)."
        )

        await self._upsert_kb({
            "source_id": "vetassess",
            "title": "VETASSESS",
            "url": self.source_url,
            "fees": [{"tier": "Full skills assessment", "amount": primary_fee, "currency": "AUD"}],
            "fee_range_min": amounts[0] if amounts else primary_fee,
            "fee_range_max": amounts[-1] if amounts else primary_fee,
            "fee_amounts_observed": amounts[:30],
            "processing_weeks": proc_weeks,
            "rules_summary": rules_summary,
            "data_quality": data_quality,
            "countries": ["AU"],
        })

        d = db()
        # Phase 19.2c — catch-all: AU verified records NOT covered by ACS/EA AND
        # without a fee_native yet. Idempotent: re-run only touches records that
        # are still empty (records ACS or EA claimed are left alone).
        other_prefixes_regex = "|".join(f"^{p}" for p in OTHER_BODY_PREFIXES)
        query: Dict[str, Any] = {
            "country_code": "AU",
            "status": "verified",
            "code": {"$not": {"$regex": other_prefixes_regex}},
            "$or": [
                {"assessing_authority.fee_native": {"$exists": False}},
                {"assessing_authority.fee_native": {"$in": [None, ""]}},
                # Also re-claim records previously scraped by us so re-runs keep them fresh
                {"assessing_authority.scraped_by": "vetassess_scraper_v1"},
            ],
        }
        if codes:
            query["code"] = {"$in": codes}

        async for occ in d["occupation_master"].find(query, {"_id": 0, "occupation_id": 1, "assessing_authority": 1}):
            result.records_attempted += 1
            # Snapshot previous fee for change-detection (Phase 19.2c fee-change alerts)
            prev_fee = (occ.get("assessing_authority") or {}).get("fee_native")
            update_doc: Dict[str, Any] = {
                "assessing_authority.fee_native": primary_fee,
                "assessing_authority.fee_currency": "AUD",
                "assessing_authority.body_url": self.source_url,
                "assessing_authority.processing_time_weeks": proc_weeks,
                "assessing_authority.rules_summary": rules_summary,
                "assessing_authority.last_scraped_at": datetime.now(timezone.utc).isoformat(),
                "assessing_authority.scraped_by": "vetassess_scraper_v1",
                "assessing_authority.data_quality": data_quality,
            }
            if prev_fee and prev_fee != primary_fee:
                update_doc["assessing_authority.previous_fee_native"] = prev_fee
            # Set the assessing body name if blank, otherwise leave as-is
            current_name = (occ.get("assessing_authority") or {}).get("name")
            if not current_name:
                update_doc["assessing_authority.name"] = "VETASSESS"
                update_doc["assessing_authority.short_name"] = "VETASSESS"
            await d["occupation_master"].update_one(
                {"occupation_id": occ["occupation_id"]},
                {"$set": update_doc},
            )
            result.records_updated += 1
        result.notes = (
            f"VETASSESS amounts={amounts[:5]}, primary=AUD ${primary_fee:.2f}, "
            f"proc={proc_weeks}w, quality={data_quality}, matched {result.records_updated} AU codes."
        )
        return result
