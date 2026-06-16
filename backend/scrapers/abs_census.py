"""Phase 19.2a-Lite — ABS Census 2021 Income by Occupation scraper.

Source: https://api.data.abs.gov.au/ (SDMX REST API)
Reachable: ✓ partial — dataflow listing returns 3.2 MB SDMX-ML XML (3000+ flows).

Status: SKELETON IMPL — recon confirms reachability, but the per-ANZSCO 6-digit
income data resides under a Census 2021 dataflow whose exact ID + dimension
schema requires deeper SDMX exploration than Phase 19.2a-Lite budgets allow.
The scraper:
1. Lists all dataflows and identifies Census21 income-related ones.
2. Records that into `knowledge_base` as a deferral marker.
3. Marks status = "skipped" with an explicit notes field.

Phase 19.2b will:
- Find the exact dataflow ID (likely `ABS,CENSUS21_T15A_TLF_INCOME,1.0.0` or similar)
- Build the SDMX dimension-key request (ANZSCO_6DIGIT × WEEKLY_PERSONAL_INCOME)
- Parse the SDMX-DataSet response into per-occupation salary distributions
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, List, Optional

from .base import BaseScraper, ScrapeRunResult, db

ABS_DATAFLOW_URL = "https://api.data.abs.gov.au/dataflow/ABS"


class ABSCensusScraper(BaseScraper):
    scraper_id = "abs_census"
    display_name = "ABS Census 2021 Income by Occupation"
    description = "AU salary distribution per ANZSCO 6-digit (SKELETON — dataflow ID discovery pending)"
    countries = ["AU"]
    source_url = ABS_DATAFLOW_URL
    is_global = True

    async def scrape(self, codes: Optional[List[str]] = None) -> ScrapeRunResult:
        result = ScrapeRunResult(
            scraper_id=self.scraper_id, started_at="", finished_at="",
            duration_ms=0, status="skipped",
        )
        r = await self.fetch(
            self.source_url,
            accept="application/vnd.sdmx.structure+xml;version=2.1",
        )
        if r is None or r.status_code != 200:
            result.status = "failed"
            result.notes = f"ABS API HTTP {r.status_code if r else 'ERR'}"
            return result
        xml = r.text
        # Best-effort parse: find census21 / income dataflows
        ids = re.findall(r'<structure:Dataflow\b[^>]*\bid="([^"]+)"', xml)
        income_candidates: List[str] = []
        for fid in ids:
            up = fid.upper()
            if ("INCOME" in up or "EARN" in up or "C21" in up or "CENSUS" in up) and "OCC" in up:
                income_candidates.append(fid)
        # Always also flag bare census21 flows for later eyeballing
        census21_candidates = [fid for fid in ids if "C21" in fid.upper()][:30]

        await self._upsert_kb({
            "source_id": "abs_census",
            "source_type": "labour_market",
            "title": "ABS Census 2021 Income by Occupation (deferred)",
            "url": self.source_url,
            "rules_summary": (
                "ABS SDMX API reachable from preview but per-ANZSCO 6-digit income dataflow "
                "ID discovery is deferred to Phase 19.2b. Once the correct dataflow is identified, "
                "this scraper will populate occupation_master.abs_data with weekly median + salary "
                "distribution per AU verified record."
            ),
            "countries": ["AU"],
            "_status": "deferred",
            "_income_candidates": income_candidates[:20],
            "_census21_candidates": census21_candidates,
            "_total_dataflows": len(ids),
        })
        result.notes = (
            f"ABS SDMX reachable. {len(ids)} dataflows listed. "
            f"Income+OCC candidates: {income_candidates[:5]!r}. "
            "Detailed dataflow-ID discovery deferred to Phase 19.2b."
        )
        result.status = "skipped"
        return result
