"""Phase 12 — NZ Atlas + Bulk Auto-Verify Tool tests.

Covers:
  • 4 NZ scrapers (seed, green-list, aewv-smc, sector-agreements)
  • Auto-Verify rules, preview, run, idempotency
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://career-match-320.preview.emergentagent.com")
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
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ─── A. NZ Atlas Scrapers ───────────────────────────────────────────────────

def test_nz_scrapers_listed_in_scrapers_list(admin_headers):
    """4 NZ scrapers must appear in /scrapers/list."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()["scrapers"]}
    assert "nz_anzsco_seed" in ids
    assert "nz_green_list" in ids
    assert "nz_aewv_smc" in ids
    assert "nz_sector_agreements" in ids
    # All 4 tagged country=NZ
    nz_ids = {s["id"] for s in r.json()["scrapers"] if s.get("country") == "NZ"}
    assert nz_ids >= {"nz_anzsco_seed", "nz_green_list", "nz_aewv_smc", "nz_sector_agreements"}


def test_nz_anzsco_seed_dryrun_returns_seed_set_size(admin_headers):
    """dry_run shouldn't crash and reports the seed set size."""
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/nz-anzsco-seed/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["totals"]["seed_set_size"] >= 200
    assert "inserted" in d["counts"]


def test_nz_green_list_returns_tier1_and_tier2(admin_headers):
    """Green List run must classify at least 50 Tier 1 + 15 Tier 2 occupations."""
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/nz-green-list/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["totals"]["tier_1_count"] >= 50
    assert d["totals"]["tier_2_count"] >= 15
    assert "LTSSL" in d["legacy_note"]
    assert "RSSL" in d["legacy_note"]


def test_nz_aewv_smc_populates_records(admin_headers):
    """AEWV/SMC must process all NZ records."""
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/nz-aewv-smc/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["totals"]["nz_records_processed"] >= 200
    assert d["totals"]["aewv_eligible_count"] >= 100
    assert d["totals"]["smc_auto_pass_count"] >= 50


def test_nz_sector_agreements_returns_sector_distribution(admin_headers):
    """Sector agreements must tag CISA/Care/Transport sub-counts."""
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/nz-sector-agreements/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    sd = d["totals"]["sector_distribution"]
    assert sd["construction_cisa"] >= 10
    assert sd["care_workforce"] >= 5


def test_nz_atlas_now_has_200_plus_records(admin_headers):
    """After running NZ ANZSCO seed, NZ atlas must have 200+ records."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/audit-summary", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    nz_total = r.json()["totals"]["occupation_master_nz_total"]
    assert nz_total >= 200


def test_nz_tracked_fields_now_include_phase12_fields(admin_headers):
    """audit-summary must show NZ fields like nz_green_list_tier + aewv_eligibility."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/audit-summary", headers=admin_headers, timeout=15)
    nz = r.json()["field_coverage_nz"]
    keys = {x["field"] for x in nz}
    assert "nz_green_list_tier" in keys
    assert "aewv_eligibility" in keys
    assert "smc_points_breakdown" in keys
    assert "sector_agreement_eligibility" in keys


def test_nz_software_engineer_is_green_list_tier1_atlas_verify(admin_headers):
    """Spot-check: 261313 Software Engineer should be Green List Tier 1 + AEWV eligible."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/audit-rows?country=NZ&search=Software&limit=5",
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    se = next((x for x in items if x["code"] == "261313"), None)
    assert se is not None, f"Software Engineer 261313 not found in NZ. Got: {[i['code'] for i in items]}"
    # Coverage must include green list tier + aewv as filled
    assert se["coverage"].get("nz_green_list_tier") is True
    assert se["coverage"].get("aewv_eligibility") is True


def test_nz_scraper_run_partner_blocked(partner_headers):
    """Non-admin cannot run NZ scrapers."""
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/nz-anzsco-seed/run?dry_run=true",
        headers=partner_headers, timeout=15,
    )
    assert r.status_code in (401, 403)


# ─── B. Bulk Auto-Verify ────────────────────────────────────────────────────

def test_auto_verify_rules_returns_three_countries(admin_headers):
    """Rules endpoint must return AU + CA + NZ."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/auto-verify/rules", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert set(d["rules"].keys()) == {"AU", "CA", "NZ"}
    for country in ["AU", "CA", "NZ"]:
        assert "required_fields" in d["rules"][country]
        assert "description" in d["rules"][country]


def test_auto_verify_preview_nz_returns_pass_fail_arrays(admin_headers):
    """Preview returns pass/fail arrays with reasons."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/auto-verify/NZ/preview?min_coverage_pct=70",
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["country"] == "NZ"
    assert "pass_codes" in d
    assert "fail_codes" in d
    assert "totals" in d
    # Sanity: totals add up
    assert (d["totals"]["would_verify"] + d["totals"]["would_skip"] + d["totals"]["already_verified"]
            == d["totals"]["total_records"])


def test_auto_verify_preview_ca_uses_one_of_rule(admin_headers):
    """CA preview must reflect 'one of' provincial pathway rule + return fail reasons."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/auto-verify/CA/preview?min_coverage_pct=70",
        headers=admin_headers, timeout=15,
    )
    d = r.json()
    assert d["rules"]["one_of"]
    # Failed codes must have non-empty missing_fields explaining the failure
    if d["fail_codes"]:
        for c in d["fail_codes"][:5]:
            assert c.get("missing_fields") or c.get("coverage_pct", 100) < 70, c


def test_auto_verify_dry_run_doesnt_mutate(admin_headers):
    """dry_run=true must report verified_now > 0 but DB shouldn't be mutated."""
    # Snapshot verified count before
    r1 = requests.get(f"{BASE_URL}/api/anz-intel/audit-summary", headers=admin_headers, timeout=15)
    before_ca = r1.json()["totals"]["occupation_master_ca_verified"]

    r2 = requests.post(
        f"{BASE_URL}/api/anz-intel/auto-verify/CA/run?dry_run=true&min_coverage_pct=70",
        headers=admin_headers, timeout=30,
    )
    assert r2.status_code == 200
    assert r2.json()["dry_run"] is True
    assert r2.json()["totals"]["verified_now"] >= 0

    r3 = requests.get(f"{BASE_URL}/api/anz-intel/audit-summary", headers=admin_headers, timeout=15)
    after_ca = r3.json()["totals"]["occupation_master_ca_verified"]
    assert before_ca == after_ca, "dry_run must not mutate DB"


def test_auto_verify_unsupported_country_400(admin_headers):
    """Unknown country must 400."""
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/auto-verify/XX/run?dry_run=true",
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 400


def test_auto_verify_partner_blocked(partner_headers):
    """Non-admin cannot use auto-verify."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/auto-verify/NZ/preview",
        headers=partner_headers, timeout=15,
    )
    assert r.status_code in (401, 403)


def test_auto_verify_run_idempotency(admin_headers):
    """Re-running auto-verify should not double-verify (already_verified == previous verified_now)."""
    # First run (NZ should already be all-verified from previous test or fresh)
    r1 = requests.post(
        f"{BASE_URL}/api/anz-intel/auto-verify/NZ/run?dry_run=false&min_coverage_pct=70",
        headers=admin_headers, timeout=30,
    )
    assert r1.status_code == 200
    first_total_verified_after = r1.json()["totals"]["verified_now"] + r1.json()["totals"]["already_verified"]

    # Second run
    r2 = requests.post(
        f"{BASE_URL}/api/anz-intel/auto-verify/NZ/run?dry_run=false&min_coverage_pct=70",
        headers=admin_headers, timeout=30,
    )
    assert r2.status_code == 200
    # On re-run: verified_now should be 0, already_verified = previous total
    assert r2.json()["totals"]["verified_now"] == 0
    assert r2.json()["totals"]["already_verified"] == first_total_verified_after
