"""Phase 10.1 — Canada NOC 2021 V1.0 Bulk Importer regression tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://staff-dashboard-66.preview.emergentagent.com")
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ─── Scraper endpoint tests ─────────────────────────────────────────────────
def test_scrapers_list_includes_noc_canada(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()["scrapers"]}
    assert "noc_canada" in ids
    noc = next(s for s in r.json()["scrapers"] if s["id"] == "noc_canada")
    assert noc["country"] == "CA"
    assert noc["estimated_records"] == 516


def test_noc_canada_dry_run_reports_516(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/noc-canada/run?dry_run=true",
        headers=admin_headers, timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "statcan_noc_2021_v1.0"
    assert body["total_unit_groups_in_csv"] == 516
    assert body["dry_run"] is True
    # TEER distribution covers all 6 levels (0-5) — JSON keys serialize as strings
    teer_dist = body["teer_distribution_in_csv"]
    assert set(teer_dist.keys()) == {"0", "1", "2", "3", "4", "5"}
    # Mid-skill (TEER 2) should be the largest cohort
    assert int(teer_dist["2"]) > int(teer_dist["5"])


def test_noc_canada_idempotent_after_commit(admin_headers):
    """Run twice in a row — 2nd run must have 0 changes."""
    # 1st run
    r1 = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/noc-canada/run?dry_run=false",
        headers=admin_headers, timeout=120,
    )
    assert r1.status_code == 200
    # 2nd run — every record identical → all skipped_unchanged
    r2 = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/noc-canada/run?dry_run=false",
        headers=admin_headers, timeout=120,
    )
    assert r2.status_code == 200
    counts = r2.json()["counts"]
    assert counts["created"] == 0
    assert counts["updated"] == 0
    assert counts["skipped_unchanged"] == 516


def test_noc_canada_partner_blocked(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/noc-canada/run?dry_run=true",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 403


# ─── Data integrity tests via sales API (RBAC-OK for partner) ───────────────
def test_sales_search_returns_516_ca_codes(partner_headers):
    r = requests.get(
        f"{BASE_URL}/api/sales/occupations/search?country=CA&limit=200",
        headers=partner_headers, timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["count"] == 516


def test_known_software_engineer_noc_21231(partner_headers):
    """The famous 21231 (Software engineers and designers) must exist with rich enrichment."""
    r = requests.get(
        f"{BASE_URL}/api/sales/occupations/typeahead?q=software%20engineer&country=CA",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    codes = {it["code"] for it in items}
    assert "21231" in codes


def test_audit_summary_now_includes_ca_totals(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/audit-summary", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    totals = r.json()["totals"]
    assert totals["occupation_master_ca_total"] == 516
    assert totals["occupation_master_ca_draft"] >= 486  # at least the new ones are draft


# ─── Direct importer behavior tests (function-level via fastapi async client) ──
def test_noc_data_files_exist():
    """Phase 10.1 ships static CSVs in the repo — verify they're present."""
    from pathlib import Path
    base = Path("/app/backend/data/noc_2021")
    assert (base / "noc-2021-v1.0-classification-structure.csv").exists()
    assert (base / "noc-2021-v1.0-elements.csv").exists()


def test_teer_label_helper():
    from core.scrapers.noc_canada import _teer_label
    assert _teer_label(0) == "Management"
    assert "University" in _teer_label(1)
    assert "College" in _teer_label(2)
    assert _teer_label(99) == "—"
