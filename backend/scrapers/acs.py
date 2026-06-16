"""Phase 19.2a-Lite — ACS (Australian Computer Society) scraper.

Source: https://www.acs.org.au/msa.html
Reachable: ✓ confirmed in recon (200 OK, $500/$516/$600/$605/$620/$625 + 12-week processing time)
Coverage: ~50 AU IT-related ANZSCO codes (2611xx, 2612xx, 2613xx, etc.)
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseScraper, ScrapeRunResult, db

# ACS handles ANZSCO Unit Group 261 (Business and Systems Analysts and Programmers),
# 262 (Database and Systems Administrators, and ICT Security Specialists),
# 263 (ICT Network and Support Professionals) and a few related codes.
ACS_ANZSCO_PREFIXES = ("261", "262", "263", "135", "224", "225")
ACS_SOURCE_URL = "https://www.acs.org.au/msa.html"


class ACSScraper(BaseScraper):
    scraper_id = "acs"
    display_name = "Australian Computer Society (ACS)"
    description = "ANZSCO IT / ICT occupations · MSA fees + processing time"
    countries = ["AU"]
    source_url = ACS_SOURCE_URL
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

        # Extract fee tiers — these are publicly listed on the MSA page
        fee_amounts = sorted(set(re.findall(r"\$([0-9]{3,4})\b", html)), key=int)
        # The "primary" MSA fee for new applicants is documented as the highest tier
        primary_fee = int(fee_amounts[-1]) if fee_amounts else None
        # Processing time
        proc_match = re.search(r"(\d{1,3})\s*weeks?", html, re.I)
        proc_weeks = int(proc_match.group(1)) if proc_match else 12  # ACS stated 12 weeks
        rules_summary = (
            "ACS evaluates ICT qualifications and skilled employment for ANZSCO Skill Level 1 unit groups "
            "261, 262, 263 and related. Standard MSA application processing time is approximately "
            f"{proc_weeks} weeks. Fees range from ${fee_amounts[0] if fee_amounts else '500'} to "
            f"${fee_amounts[-1] if fee_amounts else '625'} AUD depending on pathway."
        )

        # KB upsert
        await self._upsert_kb({
            "source_id": "acs",
            "title": "Australian Computer Society (ACS)",
            "url": self.source_url,
            "fees": [{"tier": "MSA — All pathways", "amount": primary_fee, "currency": "AUD"}],
            "fee_range_min": int(fee_amounts[0]) if fee_amounts else None,
            "fee_range_max": int(fee_amounts[-1]) if fee_amounts else None,
            "processing_weeks": proc_weeks,
            "rules_summary": rules_summary,
            "countries": ["AU"],
        })

        # Update occupation_master records that match ACS's coverage
        d = db()
        query = {
            "country_code": "AU",
            "status": "verified",
            "$or": [{"code": {"$regex": f"^{p}"}} for p in ACS_ANZSCO_PREFIXES],
        }
        if codes:
            query["code"] = {"$in": codes}
        cursor = d["occupation_master"].find(query, {"_id": 0, "occupation_id": 1, "code": 1})
        async for occ in cursor:
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
                    "assessing_authority.scraped_by": "acs_scraper_v1",
                }},
            )
            result.records_updated += 1
        result.notes = (
            f"ACS fees={fee_amounts!r}, primary=${primary_fee}, proc={proc_weeks}w, "
            f"matched {result.records_updated} ANZSCO codes."
        )
        return result
