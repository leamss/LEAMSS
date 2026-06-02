"""Phase 9 — Migration Atlas Scrapers (Foundation).

Source-by-source enrichment modules for occupation_master.

Each scraper is responsible for ONE official source and writes its data into
the occupation_master collection while respecting:
  • Existing verified records (no overwrite)
  • Dry-run preview before commit
  • Audit fields: `source`, `last_scraped_at`, `last_scraped_by`
"""
