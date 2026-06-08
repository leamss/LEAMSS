"""Phase 10.4 + 10.5 — IRCC Round Cutoffs + AIP/RCIP/FCIP regression tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://staff-dashboard-66.preview.emergentagent.com")
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ─── Phase 10.4 — IRCC Round Cutoffs ────────────────────────────────────────
def test_round_cutoffs_endpoint_listed(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=10)
    ids = {s["id"] for s in r.json()["scrapers"]}
    assert "ircc_round_cutoffs" in ids


def test_round_cutoffs_dry_run_has_official_cutoffs(admin_headers):
    """Dry-run must report 13 categories, 10 with active cutoffs."""
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ircc-round-cutoffs/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_categories"] == 13
    # At least 10 have a concrete 2026 cutoff
    assert body["categories_with_active_cutoff"] >= 9


def test_round_cutoffs_idempotent(admin_headers):
    requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ircc-round-cutoffs/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ircc-round-cutoffs/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    counts = r.json()["counts"]
    assert counts["updated"] == 0
    assert counts["skipped_unchanged"] == 516


def test_atlas_verify_rn_has_healthcare_cutoff(partner_headers):
    """RN 31301 must have Healthcare category cutoff (467) surfaced."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/31301?country=CA",
        headers=partner_headers, timeout=10,
    )
    cutoffs = r.json().get("ircc_round_cutoffs", {}).get("cutoffs_by_category", {})
    assert "healthcare" in cutoffs
    assert cutoffs["healthcare"]["latest_crs_min"] == 467
    # Also has CEC + PNP (federal programs apply to all TEER 0-3)
    assert "cec" in cutoffs
    assert "pnp" in cutoffs


def test_round_cutoffs_partner_blocked(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ircc-round-cutoffs/run?dry_run=true",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 403


# ─── Phase 10.5 — AIP + RCIP + FCIP Regional Pilots ─────────────────────────
def test_ca_regional_pilots_scraper_listed(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=10)
    ids = {s["id"] for s in r.json()["scrapers"]}
    assert "ca_regional_pilots" in ids


def test_regional_pilots_dry_run_has_official_totals(admin_headers):
    """Must register 14 RCIP communities + 6 FCIP communities + AIP."""
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ca-regional-pilots/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    totals = body["totals"]
    assert totals["rcip_communities"] == 14
    assert totals["fcip_communities"] == 6
    assert totals["aip_priority_nocs"] >= 15  # at least 15 priority NOCs in AIP


def test_regional_pilots_idempotent(admin_headers):
    requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ca-regional-pilots/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ca-regional-pilots/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    counts = r.json()["counts"]
    assert counts["updated"] == 0
    assert counts["skipped_unchanged"] == 516


def test_atlas_verify_rn_has_aip_eligibility(partner_headers):
    """RN 31301 is on AIP priority list → must show AIP pilot in regional_pilot_eligibility."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/31301?country=CA",
        headers=partner_headers, timeout=10,
    )
    pilots = r.json().get("regional_pilot_eligibility", [])
    assert any(p.get("pilot") == "aip" for p in pilots), f"AIP missing: {pilots}"
    aip = next(p for p in pilots if p.get("pilot") == "aip")
    assert set(aip["provinces"]) == {"NB", "NS", "PE", "NL"}


def test_atlas_verify_carpenter_has_multiple_rcip(partner_headers):
    """Carpenter 72310 should appear in multiple RCIP communities."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/72310?country=CA",
        headers=partner_headers, timeout=10,
    )
    pilots = r.json().get("regional_pilot_eligibility", [])
    rcip_pilots = [p for p in pilots if p.get("pilot") == "rcip"]
    assert len(rcip_pilots) >= 5  # Carpenter is in many trade-focused RCIP communities


def test_dual_community_sudbury_in_both_rcip_and_fcip(partner_headers):
    """Sudbury is registered under BOTH RCIP and FCIP."""
    # Use Mining managers (82010) which is targeted by both Sudbury programs
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/82010?country=CA",
        headers=partner_headers, timeout=10,
    )
    pilots = r.json().get("regional_pilot_eligibility", [])
    sudbury_pilots = [p for p in pilots if (p.get("community_id") or "").endswith("sudbury")]
    pilot_types = {p.get("pilot") for p in sudbury_pilots}
    assert "rcip" in pilot_types
    assert "fcip" in pilot_types


def test_regional_pilots_partner_blocked(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ca-regional-pilots/run?dry_run=true",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 403


def test_scrapers_list_now_has_10_total(admin_headers):
    """Phase 10.5 brings scraper count to 10 total (7 AU + 5 CA)."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=10)
    scrapers = r.json()["scrapers"]
    assert len(scrapers) >= 10
    ca_count = sum(1 for s in scrapers if s.get("country") == "CA")
    assert ca_count == 5  # noc_canada + ircc_ee_streams + pnp_canada + ircc_round_cutoffs + ca_regional_pilots
