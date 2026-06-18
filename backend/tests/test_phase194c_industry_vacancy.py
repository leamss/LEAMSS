"""Phase 19.4c — Industry data + Vacancy report integration tests.

Coverage:
  · Industry data XLSX parser (Table_1..4)
  · Vacancy PDF parser (national + state + major groups)
  · End-to-end upload→preview→commit→atlas surfacing
  · Sitemap inclusion (19 industry URLs)
  · Country hub vacancy chip + industry footer
  · Occupation cross-link to industry hub
  · Industry hub dynamic meta description (≤165 chars, unique)
  · Admin-only auth
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("LEAMSS_BACKEND_URL", "http://localhost:8001")
API = f"{BASE_URL}/api"
FE_BASE_URL = os.environ.get("LEAMSS_FE_URL", "http://localhost:3000")
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1)"

DATA_DIR = Path("/app/backend/data/jsa_imports")
INDUSTRY_XLSX = DATA_DIR / "industry_data_feb_2026.xlsx"
VACANCY_PDF = DATA_DIR / "vacancy_report_apr_2026.pdf"


def _login(email: str, password: str) -> str:
    with httpx.Client(base_url=BASE_URL, timeout=20) as c:
        r = c.post(f"{API}/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return r.json()["token"]


def _hdr(token: str):
    return {"Authorization": f"Bearer {token}"}


def _fetch_fe(path: str):
    with httpx.Client(base_url=FE_BASE_URL, timeout=30, follow_redirects=True) as c:
        r = c.get(path, headers={"User-Agent": GOOGLEBOT_UA})
        return r.status_code, r.text


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def phase194c_committed(admin_token: str):
    """Upload + commit both files once per module."""
    results = {}
    with httpx.Client(base_url=BASE_URL, timeout=120) as c:
        for ftype, fpath, mime in [
            ("industry_data", INDUSTRY_XLSX, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("vacancy_report", VACANCY_PDF, "application/pdf"),
        ]:
            if not fpath.exists():
                pytest.skip(f"missing {fpath}")
            with open(fpath, "rb") as fh:
                r = c.post(
                    f"{API}/data-import/upload",
                    files={"file": (fpath.name, fh, mime)},
                    headers=_hdr(admin_token),
                )
            r.raise_for_status()
            up = r.json()
            assert up["detected_type"] == ftype, f"expected {ftype}, got {up['detected_type']}"
            cm = c.post(f"{API}/data-import/{up['file_id']}/commit", headers=_hdr(admin_token))
            cm.raise_for_status()
            results[ftype] = cm.json()
        c.post(f"{API}/seo-ssg/regenerate-all", headers=_hdr(admin_token))
    return results


# ── Tests ──────────────────────────────────────────────────────────────────


def test_01_industry_parser_extracts_19_industries():
    from parsers.jsa.industry_data import parse_workbook
    recs = list(parse_workbook(str(INDUSTRY_XLSX)))
    assert len(recs) == 19, f"expected 19 industries, got {len(recs)}"
    # Spot-check
    names = [r["industry_name"] for r in recs]
    assert "Professional, Scientific and Technical Services" in names
    assert "Health Care and Social Assistance" in names
    # Each must have anzsic_code + slug + employed_count + top_employing_occupations
    for r in recs:
        assert r["anzsic_code"] and len(r["anzsic_code"]) == 1
        assert r["slug"]
        assert r["employed_count"] is not None
        assert isinstance(r["top_employing_occupations"], list)
        assert len(r["top_employing_occupations"]) <= 10


def test_02_industry_parser_includes_employment_history():
    from parsers.jsa.industry_data import parse_workbook
    recs = list(parse_workbook(str(INDUSTRY_XLSX)))
    # First non-empty industry should have ~85 quarterly points (20y × 4)
    histories = [len(r.get("employment_history_20y") or []) for r in recs]
    assert max(histories) >= 80, f"expected >=80 history points, got {max(histories)}"


def test_03_vacancy_parser_extracts_national_total():
    from parsers.jsa.vacancy_report import parse_pdf
    rec = list(parse_pdf(str(VACANCY_PDF)))[0]
    assert rec["national_ads"] == 212000, f"expected 212000, got {rec['national_ads']}"
    assert rec["period"] == "April 2026"
    assert rec["monthly_change_pct"] is not None
    assert rec["annual_change_pct"] is not None


def test_04_vacancy_parser_extracts_all_8_states():
    from parsers.jsa.vacancy_report import parse_pdf
    rec = list(parse_pdf(str(VACANCY_PDF)))[0]
    by_state = rec["by_state"]
    expected = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}
    assert set(by_state.keys()) == expected, f"missing states: {expected - set(by_state.keys())}"
    # Sum of states should be close to national total
    state_sum = sum(by_state.values())
    nat = rec["national_ads"]
    assert abs(state_sum - nat) <= nat * 0.005, f"state sum {state_sum} differs from national {nat}"


def test_05_vacancy_parser_extracts_8_major_groups():
    from parsers.jsa.vacancy_report import parse_pdf
    rec = list(parse_pdf(str(VACANCY_PDF)))[0]
    majors = rec["by_anzsco_major_group"]
    expected = {"Managers", "Professionals", "Technicians and Trades Workers",
                "Community and Personal Service Workers", "Clerical and Administrative Workers",
                "Sales Workers", "Machinery Operators and Drivers", "Labourers"}
    assert set(majors.keys()) == expected


def test_06_industry_commit_upserts_19_docs(phase194c_committed):
    s = phase194c_committed["industry_data"]["summary"]
    assert s["parsed_records"] == 19
    assert (s.get("industries_upserted", 0) + s.get("industries_modified", 0)) == 19


def test_07_vacancy_commit_marks_latest(phase194c_committed):
    s = phase194c_committed["vacancy_report"]["summary"]
    assert s["period"] == "April 2026"
    assert s["parsed_records"] == 1


def test_08_au_country_hub_shows_vacancy_chip(phase194c_committed):
    status, html = _fetch_fe("/atlas/au/")
    assert status == 200
    assert "212,000 active job ads" in html, "vacancy chip missing"
    assert "MoM" in html, "monthly change Δ missing"


def test_09_au_country_hub_shows_industry_grid(phase194c_committed):
    status, html = _fetch_fe("/atlas/au/")
    assert status == 200
    assert "industry-grid" in html
    # All 19 industry cards
    matches = re.findall(r"industry-card-([a-z0-9\-]+)", html)
    assert len(set(matches)) >= 19, f"expected >=19 industry cards, got {len(set(matches))}: {matches[:5]}"


def test_10_industry_hub_page_renders_with_stats(phase194c_committed):
    status, html = _fetch_fe("/atlas/au/industry/professional-scientific-and-technical-services/")
    assert status == 200
    # Stat blocks
    for keyword in ("Workforce Share", "Median (Weekly)", "Annual (× 52)", "ANZSIC Industry"):
        assert keyword in html, f"missing '{keyword}'"
    # 20y trend
    assert "20-year employment trend" in html
    assert "industry-spark" in html
    # Top occupations
    assert "industry-top-occs" in html
    # Source attribution
    assert "JSA Industry Data" in html


def test_11_industry_hub_meta_description_under_165(phase194c_committed):
    """Every industry hub page meta description must be ≤165 chars + contain CTA."""
    from parsers.jsa.industry_data import parse_workbook
    recs = list(parse_workbook(str(INDUSTRY_XLSX)))
    too_long = []
    no_cta = []
    descs = []
    for r in recs:
        slug = r["slug"]
        status, html = _fetch_fe(f"/atlas/au/industry/{slug}/")
        assert status == 200, f"{slug}: status {status}"
        m = re.search(r'<meta name="description" content="([^"]+)"', html)
        if not m:
            no_cta.append((slug, "no meta tag"))
            continue
        desc = m.group(1)
        descs.append(desc)
        if len(desc) > 165:
            too_long.append((slug, len(desc), desc))
        if "guide" not in desc.lower() and "check" not in desc.lower() and "assessment" not in desc.lower():
            no_cta.append((slug, desc))
    assert not too_long, f"long: {too_long}"
    assert not no_cta, f"missing CTA: {no_cta}"
    # Uniqueness
    assert len(set(descs)) == len(descs), "duplicate industry meta descriptions"


def test_12_sitemap_includes_19_industry_urls(phase194c_committed):
    status, html = _fetch_fe("/sitemap.xml")
    assert status == 200
    urls = re.findall(r"<loc>(https?://[^<]+atlas/au/industry/[^<]+)</loc>", html)
    assert len(set(urls)) >= 19, f"sitemap has {len(set(urls))} industry URLs, expected >=19"


def test_13_occupation_page_cross_links_to_industries(phase194c_committed):
    status, html = _fetch_fe("/atlas/au/261313/")
    assert status == 200
    links = re.findall(r"occ-industry-link-([a-z0-9\-]+)", html)
    assert len(set(links)) >= 1, f"expected ≥1 industry cross-link on 261313, got {len(set(links))}"


def test_14_vacancy_latest_endpoint(admin_token: str, phase194c_committed):
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        r = c.get(f"{API}/data-import/vacancy/latest", headers=_hdr(admin_token))
    assert r.status_code == 200
    j = r.json()
    assert j["snapshot"] is not None
    s = j["snapshot"]
    assert s["period"] == "April 2026"
    assert s["national_ads"] == 212000
    assert s["is_latest"] is True


def test_15_industries_endpoint(admin_token: str, phase194c_committed):
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        r = c.get(f"{API}/data-import/industries", headers=_hdr(admin_token))
    assert r.status_code == 200
    j = r.json()
    assert j["count"] == 19
    assert all("industry_name" in it for it in j["items"])
    assert all("slug" in it for it in j["items"])


def test_16_admin_only_endpoints():
    """All Phase 19.4c data-import endpoints require admin token."""
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        for ep in ("/data-import/vacancy/latest", "/data-import/industries", "/data-import/history"):
            r = c.get(f"{API}{ep}")
            assert r.status_code in (401, 403), f"{ep} unprotected: {r.status_code}"
