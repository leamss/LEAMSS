"""Phase 10.7 — Quebec PSTQ + multi-country AI Atlas Auto-Suggest tests."""
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


# ─── Phase 10.7 — Quebec Immigration ────────────────────────────────────────
def test_quebec_scraper_in_list(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=10)
    ids = {s["id"] for s in r.json()["scrapers"]}
    assert "quebec_immigration" in ids


def test_quebec_dry_run_correct_pstq_distribution(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/quebec-immigration/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["active_program"] == "PSTQ"
    assert body["peq_status"] == "closed_2025"
    dist = body["totals"]["sections_distribution"]
    # PSTQ A applies to TEER 0-2 = ~ 48+97+162 = 307
    assert dist["pstq_a"] == 307
    # PSTQ B applies to TEER 3-5 = ~ 69+95+45 = 209
    assert dist["pstq_b"] == 209
    # Section D applies to everyone (Quebec graduates)
    assert dist["pstq_d"] == 516


def test_quebec_idempotent(admin_headers):
    requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/quebec-immigration/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/quebec-immigration/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    counts = r.json()["counts"]
    assert counts["updated"] == 0
    assert counts["skipped_unchanged"] == 516


def test_quebec_partner_blocked(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/quebec-immigration/run?dry_run=true",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 403


def test_atlas_verify_software_engineer_qc(partner_headers):
    """SW Engineer (NOC 21231, TEER 1) → Section A (priority), Section D."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/21231?country=CA",
        headers=partner_headers, timeout=10,
    )
    qe = r.json().get("quebec_eligibility") or {}
    assert qe["eligible"] is True
    assert qe["feer_category"] == 1
    section_ids = {s["section_id"] for s in qe.get("sections", [])}
    assert "pstq_a" in section_ids
    assert "pstq_d" in section_ids
    pstq_a = next(s for s in qe["sections"] if s["section_id"] == "pstq_a")
    assert pstq_a.get("priority") is True


def test_atlas_verify_physician_regulated_qc(partner_headers):
    """Family physician (31102) is REGULATED in Quebec — Section C applies."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/31102?country=CA",
        headers=partner_headers, timeout=10,
    )
    qe = r.json().get("quebec_eligibility") or {}
    assert qe["is_regulated"] is True
    section_ids = {s["section_id"] for s in qe.get("sections", [])}
    assert "pstq_c" in section_ids  # regulated stream applies


def test_atlas_verify_carpenter_no_section_c_qc(partner_headers):
    """Carpenter (72310, TEER 2) — NOT regulated, so Section C should NOT apply."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/72310?country=CA",
        headers=partner_headers, timeout=10,
    )
    qe = r.json().get("quebec_eligibility") or {}
    assert qe["is_regulated"] is False
    section_ids = {s["section_id"] for s in qe.get("sections", [])}
    assert "pstq_c" not in section_ids


def test_atlas_verify_lower_skill_low_french_section_b(partner_headers):
    """Livestock labourer (85100, TEER 5) → Section B (lower French oral 5+)."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/85100?country=CA",
        headers=partner_headers, timeout=10,
    )
    qe = r.json().get("quebec_eligibility") or {}
    assert qe["feer_category"] == 5
    section_ids = {s["section_id"] for s in qe.get("sections", [])}
    assert "pstq_b" in section_ids
    pstq_b = next(s for s in qe["sections"] if s["section_id"] == "pstq_b")
    assert pstq_b["french_required"]["oral"] == 5
    # Section A is for TEER 0-2 only — not applicable to TEER 5
    assert "pstq_a" not in section_ids


# ─── Phase 10.3/10.7 — Multi-Country AI Atlas Auto-Suggest ──────────────────
def test_auto_suggest_works_for_au(partner_headers):
    """Same endpoint now works for Australia (ANZSCO 6-digit codes)."""
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        headers=partner_headers,
        json={
            "description": "Civil engineer with 6 years experience designing roads and bridges. Wants to migrate to Australia.",
            "country_code": "AU",
            "region_code": "NSW",
            "max_suggestions": 2,
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["_country"] == "AU"
    # Should return AU 6-digit codes (most likely 233211 Civil Engineer)
    codes = [s["code"] for s in body["suggestions"]]
    assert all(len(c) == 6 for c in codes), f"Expected 6-digit ANZSCO codes, got {codes}"
    # Each suggestion has AU-specific atlas data
    if body["suggestions"]:
        atlas = body["suggestions"][0]["atlas"]
        assert atlas["country_code"] == "AU"
        assert "skill_level_or_teer" in atlas
        assert atlas["classification"] == "ANZSCO"


def test_auto_suggest_still_works_for_ca(partner_headers):
    """Backward compatible — CA mode still works with new signature."""
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        headers=partner_headers,
        json={
            "description": "Backend software engineer at fintech, 8 years Python distributed systems",
            "country_code": "CA",
            "region_code": "BC",
            "max_suggestions": 2,
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["_country"] == "CA"
    codes = [s["code"] for s in body["suggestions"]]
    assert all(len(c) == 5 for c in codes), f"Expected 5-digit NOC codes, got {codes}"
    if body["suggestions"]:
        atlas = body["suggestions"][0]["atlas"]
        assert atlas["country_code"] == "CA"
        assert "teer_category" in atlas
        assert "ee_eligibility" in atlas
        assert "pnp_eligibility" in atlas
        assert "quebec_eligibility" in atlas  # NEW — added in Phase 10.7


def test_auto_suggest_unsupported_country_400(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        headers=partner_headers,
        json={"description": "Software engineer with 5 years experience", "country_code": "XX"},
        timeout=10,
    )
    assert r.status_code == 400


def test_auto_suggest_ca_includes_quebec_data(partner_headers):
    """CA suggestion atlas payload now includes quebec_eligibility (Phase 10.7)."""
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        headers=partner_headers,
        json={
            "description": "Family physician with 8 years GP experience in primary healthcare",
            "country_code": "CA",
            "max_suggestions": 1,
        },
        timeout=60,
    )
    assert r.status_code == 200
    body = r.json()
    if body["suggestions"]:
        qc = body["suggestions"][0]["atlas"].get("quebec_eligibility") or {}
        assert "feer_category" in qc
        assert qc.get("is_regulated") is True  # physicians are regulated in QC


def test_scrapers_list_has_quebec(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=10)
    ids_by_country = {}
    for s in r.json()["scrapers"]:
        ids_by_country.setdefault(s.get("country", "AU"), set()).add(s["id"])
    assert "quebec_immigration" in ids_by_country.get("CA", set())
    # Total CA scrapers: noc_canada + ircc_ee_streams + pnp_canada + ircc_round_cutoffs + ca_regional_pilots + quebec_immigration = 6
    assert len(ids_by_country.get("CA", set())) == 6
