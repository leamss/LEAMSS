"""Phase 9 — Migration Atlas regression tests for the 3 new scrapers:
  • State Nominations (NSW + QLD + WA)
  • SkillSelect Tier Classifier
  • VETASSESS Group A-F Static Seed

Runs over HTTP against the same backend (REACT_APP_BACKEND_URL).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://compliance-hub-751.preview.emergentagent.com")
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


def test_scrapers_list_returns_all_four(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    scrapers = r.json()["scrapers"]
    ids = {s["id"] for s in scrapers}
    assert {"home_affairs", "state_nominations", "skillselect_tiers", "vetassess_groups"} <= ids
    ready = {s["id"] for s in scrapers if s["status"] == "ready"}
    assert {"state_nominations", "skillselect_tiers", "vetassess_groups"} <= ready


def test_skillselect_tier_dry_run(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/skillselect-tiers/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "skillselect_tier_classifier"
    assert body["dry_run"] is True
    dist = body["tier_distribution"]
    assert dist["tier_1"] >= 1
    assert dist["tier_2"] >= 10
    assert dist["tier_4"] >= 1
    assert sum(dist.values()) == body["total_au_codes_classified"]


def test_skillselect_idempotency(admin_headers):
    """2nd run should hit skipped_already_set for most records."""
    r1 = requests.post(f"{BASE_URL}/api/anz-intel/scrapers/skillselect-tiers/run?dry_run=false", headers=admin_headers, timeout=60)
    assert r1.status_code == 200
    r2 = requests.post(f"{BASE_URL}/api/anz-intel/scrapers/skillselect-tiers/run?dry_run=false", headers=admin_headers, timeout=60)
    assert r2.status_code == 200
    assert r2.json()["skipped_already_set"] >= 800


def test_vetassess_groups_dry_run(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/vetassess-groups/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "vetassess_groups_static_seed"
    assert body["dry_run"] is True
    assert body["total_seed_codes"] >= 100
    assert all(g in body["by_group"] for g in "ABCDEF")
    assert body["to_update"] + body["skipped_existing"] + body["skipped_verified"] >= 80


@pytest.mark.skipif(
    os.getenv("SKIP_NETWORK_TESTS") == "1",
    reason="Skipping live-network scraper test",
)
def test_state_nominations_dry_run(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/state-nominations/run?dry_run=true",
        headers=admin_headers, timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "state_nominations_scraper"
    assert body["dry_run"] is True
    counts = body["counts"]
    assert counts["nsw_4digit_unit_groups_scraped"] >= 50, counts
    assert counts["qld_6digit_codes_scraped"] >= 50, counts
    assert counts["total_unique_docs_touched"] >= 100


def test_audit_summary_includes_new_fields(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/audit-summary", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    body = r.json()
    field_keys = {f["field"] for f in body["field_coverage_au"]}
    assert "skillselect_tier" in field_keys
    assert "state_territory_eligibility" in field_keys
    assert "skill_assessment_details" in field_keys
    tier_row = next(f for f in body["field_coverage_au"] if f["field"] == "skillselect_tier")
    assert tier_row["pct_present"] >= 80, f"SkillSelect tier coverage low: {tier_row}"


def test_partner_blocked_from_scrapers(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/skillselect-tiers/run?dry_run=true",
        headers=partner_headers, timeout=15,
    )
    assert r.status_code == 403


# ─── Phase 9.2 — Atlas Verify endpoint (sales-accessible) ───────────────────
def test_atlas_verify_partner_can_read(partner_headers):
    """Partner role should be able to call /verify/{code} (sales-facing)."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/261313",
        headers=partner_headers, timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["code"] == "261313"
    assert "skillselect_tier" in data
    assert "vetassess" in data
    assert "visa_eligibility" in data
    assert "state_nomination_matrix" in data
    assert "assessing_authority" in data
    # tier sub-object
    assert "label" in data["skillselect_tier"]
    assert "tag" in data["skillselect_tier"]


def test_atlas_verify_bad_code_400(partner_headers):
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/abc",
        headers=partner_headers, timeout=15,
    )
    assert r.status_code == 400


def test_atlas_verify_unknown_code_404(partner_headers):
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/999999",
        headers=partner_headers, timeout=15,
    )
    assert r.status_code == 404


def test_atlas_verify_unauthenticated_blocked():
    r = requests.get(f"{BASE_URL}/api/anz-intel/verify/261313", timeout=15)
    assert r.status_code in (401, 403)


def test_atlas_verify_tier_1_classification(partner_headers):
    """Early Childhood Teacher should be Tier 1 (Health/Education priority)."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/241111",
        headers=partner_headers, timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["skillselect_tier"]["label"] == "Tier 1"
    assert "Health" in data["skillselect_tier"]["tag"] or "Education" in data["skillselect_tier"]["tag"]
