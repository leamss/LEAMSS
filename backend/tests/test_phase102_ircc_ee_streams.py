"""Phase 10.2 — IRCC Express Entry Streams Classifier regression tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://career-match-320.preview.emergentagent.com")
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


# ─── Classifier unit tests (pure function) ──────────────────────────────────
def test_classify_software_engineer():
    """21231 (TEER 1) — eligible for FSWP/CEC + French only (not in 2026 STEM list)."""
    from core.scrapers.ircc_ee_streams import classify
    r = classify("21231", 1)
    assert r["fswp_eligible"] is True
    assert r["cec_eligible"] is True
    assert r["fstp_eligible"] is False
    assert "french_language" in r["categories"]
    assert "stem" not in r["categories"]
    assert "healthcare" not in r["categories"]


def test_classify_family_physician_multi_category():
    """31102 (TEER 1) — Healthcare + Physicians-CA + French."""
    from core.scrapers.ircc_ee_streams import classify
    r = classify("31102", 1)
    assert r["fswp_eligible"] is True
    assert "healthcare" in r["categories"]
    assert "physicians_ca_exp" in r["categories"]
    # Confirm the CA-experience flag is set on physician entry
    pca = [c for c in r["category_details"] if c["id"] == "physicians_ca_exp"][0]
    assert pca["requires_canadian_exp"] is True


def test_classify_civil_engineer_stem():
    from core.scrapers.ircc_ee_streams import classify
    r = classify("21300", 1)
    assert r["fswp_eligible"] is True
    assert "stem" in r["categories"]


def test_classify_carpenter_fstp_trade():
    """72310 (TEER 2) — Trade category + FSTP eligible (Major Group 72)."""
    from core.scrapers.ircc_ee_streams import classify
    r = classify("72310", 2)
    assert r["fswp_eligible"] is True
    assert r["fstp_eligible"] is True
    assert "trade" in r["categories"]


def test_classify_military_recruit():
    from core.scrapers.ircc_ee_streams import classify
    r = classify("40042", 0)
    assert "military_recruits" in r["categories"]


def test_classify_high_school_only_excluded_from_fswp():
    """TEER 5 (short-term work demo) — NOT eligible for FSWP/CEC."""
    from core.scrapers.ircc_ee_streams import classify
    r = classify("85100", 5)
    assert r["fswp_eligible"] is False
    assert r["cec_eligible"] is False
    assert r["fstp_eligible"] is False
    assert r["categories"] == []  # not in any category & french requires fswp/cec


def test_classify_senior_managers_ca_exp():
    """All 4 senior manager codes (00012-00015) — CA exp category."""
    from core.scrapers.ircc_ee_streams import classify
    for code in ["00012", "00013", "00014", "00015"]:
        r = classify(code, 0)
        assert "senior_managers_ca_exp" in r["categories"], f"Failed for {code}"


# ─── Endpoint tests ─────────────────────────────────────────────────────────
def test_scrapers_list_includes_ircc_ee_streams(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()["scrapers"]}
    assert "ircc_ee_streams" in ids


def test_ircc_ee_streams_dry_run_matches_official_2026_counts(admin_headers):
    """Category counts must EXACTLY match IRCC's published 2026 tables."""
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ircc-ee-streams/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_ca_codes_processed"] == 516
    cat = body["category_distribution"]
    # Counts from official IRCC tables (cross-checked manually)
    assert cat["healthcare"] == 37
    assert cat["stem"] == 11
    assert cat["trade"] == 25
    assert cat["education"] == 5
    assert cat["transport"] == 4
    assert cat["physicians_ca_exp"] == 3
    assert cat["senior_managers_ca_exp"] == 4
    assert cat["researchers_ca_exp"] == 2
    assert cat["military_recruits"] == 3
    # Federal programs (TEER 0-3 = 376 codes per Phase 10.1 distribution)
    assert body["federal_program_distribution"]["fswp"] == 376
    assert body["federal_program_distribution"]["cec"] == 376


def test_ircc_ee_idempotent(admin_headers):
    """Re-run after commit should produce 0 changes, 516 skipped."""
    # Ensure committed first
    requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ircc-ee-streams/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ircc-ee-streams/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    counts = r.json()["counts"]
    assert counts["updated"] == 0
    assert counts["skipped_unchanged"] == 516


def test_ircc_ee_partner_blocked(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ircc-ee-streams/run?dry_run=true",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 403


# ─── Schema integrity tests ─────────────────────────────────────────────────
def test_category_registry_completeness():
    """Every category in _CATEGORY_NOC_MAP must have a CATEGORY_REGISTRY entry."""
    from core.scrapers.ircc_ee_streams import CATEGORY_REGISTRY, _CATEGORY_NOC_MAP
    # All NOC-list-based categories must have a registry entry
    for cat_id in _CATEGORY_NOC_MAP:
        assert cat_id in CATEGORY_REGISTRY, f"Missing registry entry for {cat_id}"
    # French is registry-only (no NOC list since it's language-based)
    assert "french_language" in CATEGORY_REGISTRY
    assert "french_language" not in _CATEGORY_NOC_MAP


def test_agriculture_removed_per_2026():
    """Agriculture category was removed in 2026 — confirm it's NOT in the registry."""
    from core.scrapers.ircc_ee_streams import CATEGORY_REGISTRY
    assert "agriculture" not in CATEGORY_REGISTRY
    assert "agri_food" not in CATEGORY_REGISTRY


# ─── Atlas Verify endpoint surfacing EE eligibility ─────────────────────────
def test_atlas_verify_ca_surfaces_ee_eligibility(partner_headers):
    """Atlas Verify endpoint must return ee_eligibility for CA codes."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/31102?country=CA",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["country_code"] == "CA"
    assert body["teer_category"] == 1
    ee = body["ee_eligibility"]
    assert ee["fswp_eligible"] is True
    assert "healthcare" in ee["categories"]
    assert "physicians_ca_exp" in ee["categories"]


def test_atlas_verify_rejects_wrong_length_for_country(partner_headers):
    """AU requires 6-digit, CA requires 5-digit."""
    r1 = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/12345?country=AU",
        headers=partner_headers, timeout=10,
    )
    assert r1.status_code == 400
    r2 = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/123456?country=CA",
        headers=partner_headers, timeout=10,
    )
    assert r2.status_code == 400
