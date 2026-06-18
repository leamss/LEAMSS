"""Phase 19.4b — ABS Census 2021 Income by Occupation — FORMALLY CLOSED (Jun 2026).

⚠️ HONEST DEFERRAL — DO NOT REVIVE WITHOUT REASON:

After exhaustive Phase 19.4b reconnaissance of all 1,223 public ABS dataflows on
`https://api.data.abs.gov.au/dataflow/ABS`, the per-ANZSCO 6-digit income crosstab
(OCCP × INCP / OCCP × MEDIAN_PERSONAL_INCOME) is **NOT exposed** in the public
SDMX REST API. The Census 2021 GCP (General Community Profile) tables exist only
sliced by GEOGRAPHY (CED / LGA / POA / SA2 / SAL / SED / SUA / UCL), not by
occupation. The OCCP × INCP crosstab is available **only via ABS TableBuilder
Pro**, which requires a separate registered-user authentication flow.

**Why this scraper is no longer needed:** the Phase 19.4 JSA Occupation Profiles
direct-upload pipeline already delivers the same data (median weekly earnings +
median FT annual + employed count per 4-digit ANZSCO, sourced from ABS Census
2021 with proper attribution). 96% of AU verified records (703/729) carry
`abs_data.median_ft_annual_aud` populated via JSA upload. Re-scraping the ABS
API would duplicate this without adding precision.

Status today: `redundant_data_via_jsa_upload`. APScheduler cron entry for this
scraper is DISABLED (`server.py`). Code retained as future-reference scaffolding
if/when ABS opens the OCCP×INCP API or if we obtain TableBuilder Pro credentials.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, List, Optional

from .base import BaseScraper, ScrapeRunResult, db

ABS_DATAFLOW_URL = "https://api.data.abs.gov.au/dataflow/ABS"


class ABSCensusScraper(BaseScraper):
    scraper_id = "abs_census"
    display_name = "ABS Census 2021 Income by Occupation (CLOSED — data via JSA upload)"
    description = "Phase 19.4b CLOSED. ABS public SDMX API does not expose ANZSCO×INCOME crosstab. Same data is delivered by the Phase 19.4 JSA Occupation Profiles upload pipeline."
    countries = ["AU"]
    source_url = ABS_DATAFLOW_URL
    is_global = True

    async def scrape(self, codes: Optional[List[str]] = None) -> ScrapeRunResult:
        """Formal close-out: writes the redundancy marker once and skips."""
        result = ScrapeRunResult(
            scraper_id=self.scraper_id, started_at="", finished_at="",
            duration_ms=0, status="skipped",
        )
        await self._upsert_kb({
            "source_id": "abs_census",
            "source_type": "labour_market",
            "title": "ABS Census 2021 Income by Occupation (CLOSED — data via JSA upload)",
            "url": self.source_url,
            "rules_summary": (
                "FORMALLY CLOSED (Phase 19.4b). ABS public SDMX API does not expose "
                "OCCP × INCP crosstab — the per-ANZSCO income data is delivered via "
                "the Phase 19.4 JSA Occupation Profiles upload pipeline instead "
                "(703/729 AU records already populated). No live-scrape needed."
            ),
            "countries": ["AU"],
            "_status": "redundant_data_via_jsa_upload",
            "_closed_at": datetime.now(timezone.utc).isoformat(),
            "_replacement_path": "POST /api/data-import/upload (file_type=occupation_profiles)",
        })
        result.notes = (
            "Phase 19.4b CLOSED — ABS public SDMX API has no ANZSCO×INCOME crosstab. "
            "Replacement path: Phase 19.4 JSA Occupation Profiles upload pipeline."
        )
        result.status = "skipped"
        return result
