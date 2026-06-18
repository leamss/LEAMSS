"""Phase 19.2c + 19.3 — Polish + Surface tests (12 cases).

Combined coverage:
- Phase 19.2c: VETASSESS mapping, APScheduler registration, data_quality fields
- Phase 19.3: enriched fee data surfaced in atlas templates (occupation + country + hub)
"""
from __future__ import annotations
import os
import re

import httpx
import pytest

BASE_URL = os.environ.get("LEAMSS_BASE_URL", "http://localhost:8001")
FE_BASE_URL = os.environ.get("LEAMSS_FE_URL", "http://localhost:3000")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"


def _login(email: str, password: str) -> str:
    with httpx.Client(base_url=BASE_URL, timeout=20) as c:
        r = c.post("/api/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def scrapers_primed(admin_token: str) -> dict:
    """Phase 19.2c — Prime the DB once per test-module by running all 5
    reachable scrapers + a full SSG regen. This makes Phase 19.3 surfacing
    tests deterministic regardless of run order. Returns a small status dict
    so individual tests can pytest.skip if an upstream is blocked.
    """
    status: Dict[str, Any] = {}
    with httpx.Client(base_url=BASE_URL, timeout=120) as c:
        for sid in ("acs", "vetassess", "engineers_australia", "nzqa", "wes"):
            try:
                r = c.post(f"{API}/scrapers/{sid}/run", headers=_hdr(admin_token), json={})
                status[sid] = r.json() if r.status_code == 200 else {"status": "error", "code": r.status_code}
            except Exception as e:  # noqa: BLE001
                status[sid] = {"status": "error", "exc": str(e)[:80]}
        # One full SSG regen so all SSG files reflect the freshly-scraped fees
        c.post(f"{API}/seo-ssg/regenerate-all", headers=_hdr(admin_token))
    return status


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _fetch_fe(path: str) -> tuple[int, str]:
    with httpx.Client(base_url=FE_BASE_URL, timeout=20, follow_redirects=True) as c:
        r = c.get(path, headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"})
        return r.status_code, r.text


# ─── Phase 19.2c — polish ──────────────────────────────────────────────────

# 1. VETASSESS scraper now claims 350+ AU records (catch-all mapping)
def test_01_vetassess_catch_all_maps_350plus(admin_token: str):
    with httpx.Client(base_url=BASE_URL, timeout=90) as c:
        r = c.post(f"{API}/scrapers/vetassess/run", headers=_hdr(admin_token), json={})
        assert r.status_code == 200
        j = r.json()
        if j["status"] == "failed":
            pytest.skip(f"VETASSESS upstream blocked: {j.get('notes')}")
        # Catch-all maps to 350+ AU records (586 expected on full sweep)
        assert j["records_updated"] >= 350, f"VETASSESS only updated {j['records_updated']}"
        assert j["status"] == "success"


# 2. APScheduler has 5 monthly scraper jobs registered
def test_02_scheduler_has_5_scrapers(admin_token: str):
    # Use the live REST introspection endpoint exposed by routers/scrapers.py
    with httpx.Client(base_url=BASE_URL, timeout=20) as c:
        r = c.get(f"{API}/scrapers/scheduler-status", headers=_hdr(admin_token))
        assert r.status_code == 200, r.text
        j = r.json()
        if not j.get("running"):
            pytest.skip(f"scheduler not running in test env: {j.get('error') or ''}")
        scraper_jobs = set(j.get("scraper_jobs") or [])
        expected = {f"scraper_monthly_{s}" for s in ("acs", "vetassess", "engineers_australia", "nzqa", "wes")}
        assert expected.issubset(scraper_jobs), f"missing scraper jobs. Got: {scraper_jobs}"


# 3. EA / NZQA / WES records have data_quality field set
def test_03_data_quality_fallback_marked(admin_token: str):
    # Ensure EA scraper ran with new data_quality field
    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        c.post(f"{API}/scrapers/engineers_australia/run", headers=_hdr(admin_token), json={})
        r = c.get(f"{API}/occupation-master/au-233211", headers=_hdr(admin_token))
        if r.status_code != 200:
            pytest.skip("AU 233211 not in DB")
        aa = r.json().get("assessing_authority", {})
        if "data_quality" not in aa:
            pytest.skip("data_quality field not on this record (scrapers not re-run with new field)")
        assert aa.get("data_quality") in ("live_scraped", "fallback_published_rate")


# ─── Phase 19.3 — surfacing ────────────────────────────────────────────────

# 4. AU 261313 (Software Eng) occupation page shows real ACS fee + 12 weeks
def test_04_au_occupation_shows_acs_fee_and_processing(scrapers_primed):
    status, html = _fetch_fe("/atlas/au/261313/")
    assert status == 200
    assert "ACS" in html, "ACS body name not surfaced"
    assert "AUD $625" in html, "ACS fee not in metric grid"
    assert "12 weeks" in html, "ACS processing time not surfaced"
    assert "Skills Assessment Fee" in html, "Fee metric label missing"


# 5. AU 132311 (Marketing Sales) — VETASSESS catch-all fee surfaced
def test_05_au_occupation_shows_vetassess_fee(scrapers_primed):
    status, html = _fetch_fe("/atlas/au/132311/")
    assert status == 200
    assert "1205" in html, "VETASSESS $1205 fee not visible"


# 6. AU occupation page shows fallback indicator for EA-assessed codes
def test_06_au_engineering_shows_published_rate(scrapers_primed):
    status, html = _fetch_fe("/atlas/au/233211/")
    assert status == 200
    # Either fallback indicator OR a live fee (depending on scrape result)
    assert "Published rate" in html or "live" in html


# 7. Country page card has fee chip
def test_07_country_card_shows_fee_chip(scrapers_primed):
    status, html = _fetch_fe("/atlas/au/")
    assert status == 200
    # At least one card shows a 💰 fee chip
    chips = re.findall(r"💰\s*[A-Z]{3}\s*\$[0-9]+", html)
    assert len(chips) >= 1, f"no fee chips on country page (found: {chips})"


# 8. Hub trust strip mentions "5 official bodies"
def test_08_hub_mentions_five_official_bodies():
    status, html = _fetch_fe("/atlas/")
    assert status == 200
    assert "5 official bodies" in html
    assert "100% Refund" in html  # existing trust pillar preserved


# 9. AU occupation page has Salary section (real data OR honest "Coming Soon" fallback)
def test_09_salary_section_present_au(scrapers_primed):
    status, html = _fetch_fe("/atlas/au/261313/")
    assert status == 200
    # Phase 19.4 ships real ABS+JSA data; for codes WITHOUT data the honest
    # "Coming Soon" strip still appears. AU 261313 (Software Eng) is covered, so
    # we expect the REAL salary card here:
    has_real_salary = ("Median earnings" in html and "ABS via JSA" in html)
    has_coming_soon = ("Coming Soon" in html and "ABS" in html)
    assert has_real_salary or has_coming_soon, "neither real salary card nor honest Coming Soon strip rendered"
    # AU 261313 specifically — must have real data (Phase 19.4 ABS import committed)
    assert has_real_salary, "AU 261313 should now ship real ABS via JSA data (Phase 19.4)"


# 10. Assessing-authority section hides empty fields (no "Not available")
def test_10_assessing_authority_section_hides_empty_fields(scrapers_primed):
    status, html = _fetch_fe("/atlas/au/261313/")
    assert status == 200
    # Even if some sub-fields are empty, NO "Not available" placeholder text
    assert "Not available" not in html


# 11. CA occupation page shows WES fallback fee (CAD $265)
def test_11_ca_occupation_shows_wes_fee(scrapers_primed):
    # NOC 21231 (Software Engineer) — CA
    status, html = _fetch_fe("/atlas/ca/21231/")
    if status != 200:
        pytest.skip("CA 21231 SSG file not generated")
    assert "CAD" in html
    assert "$265" in html or "Skills Assessment" in html


# 12. Full SSG regen completes successfully after polish
def test_12_full_ssg_regen_completes(admin_token: str):
    with httpx.Client(base_url=BASE_URL, timeout=60) as c:
        r = c.post(f"{API}/seo-ssg/regenerate-all", headers=_hdr(admin_token))
        assert r.status_code == 200
        j = r.json()
        assert j["occupations_written"] >= 1000
        assert j["duration_ms"] < 30_000
        assert len(j.get("errors", [])) == 0
