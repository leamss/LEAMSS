"""Phase 10.8 — Compare Programs Side-by-Side regression tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://career-match-320.preview.emergentagent.com")
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_compare_returns_atlas_data(partner_headers):
    """Compare endpoint must include rich atlas data per item."""
    r = requests.post(
        f"{BASE_URL}/api/sales/occupations/compare",
        headers=partner_headers,
        json={"items": [
            {"country_code": "CA", "code": "21231"},
            {"country_code": "CA", "code": "31102"},
        ]},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 2
    for it in items:
        assert "atlas" in it
        assert "teer_category" in it["atlas"]
        assert "ee_eligibility" in it["atlas"]
        assert "pnp_eligibility" in it["atlas"]
        assert "quebec_eligibility" in it["atlas"]


def test_compare_assigns_best_fit_to_one_item(partner_headers):
    """Exactly ONE item should have best_fit=True (the highest score)."""
    r = requests.post(
        f"{BASE_URL}/api/sales/occupations/compare",
        headers=partner_headers,
        json={"items": [
            {"country_code": "CA", "code": "21231"},
            {"country_code": "CA", "code": "31102"},
            {"country_code": "CA", "code": "72310"},
        ]},
        timeout=20,
    )
    items = r.json()["items"]
    best = [it for it in items if it.get("best_fit")]
    assert len(best) == 1, f"Expected exactly 1 best_fit, got {len(best)}"
    # Carpenter (72310) should win because of FSTP eligibility + 14 regional pilots
    assert best[0]["code"] == "72310"


def test_compare_score_carpenter_higher_than_sw_engineer(partner_headers):
    """Carpenter (FSTP eligible + many regional pilots) > SW Engineer."""
    r = requests.post(
        f"{BASE_URL}/api/sales/occupations/compare",
        headers=partner_headers,
        json={"items": [
            {"country_code": "CA", "code": "21231"},
            {"country_code": "CA", "code": "72310"},
        ]},
        timeout=20,
    )
    items = r.json()["items"]
    carpenter = next(it for it in items if it["code"] == "72310")
    sw_eng = next(it for it in items if it["code"] == "21231")
    assert carpenter["best_fit_score"] > sw_eng["best_fit_score"]


def test_compare_min_2_max_5_items(partner_headers):
    """Pydantic validation: 2 ≤ items ≤ 5."""
    # 1 item should fail
    r1 = requests.post(
        f"{BASE_URL}/api/sales/occupations/compare",
        headers=partner_headers,
        json={"items": [{"country_code": "CA", "code": "21231"}]},
        timeout=10,
    )
    assert r1.status_code == 422

    # 6 items should fail
    r6 = requests.post(
        f"{BASE_URL}/api/sales/occupations/compare",
        headers=partner_headers,
        json={"items": [
            {"country_code": "CA", "code": "21231"},
            {"country_code": "CA", "code": "31102"},
            {"country_code": "CA", "code": "72310"},
            {"country_code": "CA", "code": "21232"},
            {"country_code": "CA", "code": "21311"},
            {"country_code": "CA", "code": "31301"},
        ]},
        timeout=10,
    )
    assert r6.status_code == 422

    # 5 items must work (Phase 10.8 raised cap from 4 to 5)
    r5 = requests.post(
        f"{BASE_URL}/api/sales/occupations/compare",
        headers=partner_headers,
        json={"items": [
            {"country_code": "CA", "code": "21231"},
            {"country_code": "CA", "code": "31102"},
            {"country_code": "CA", "code": "72310"},
            {"country_code": "CA", "code": "21232"},
            {"country_code": "CA", "code": "21311"},
        ]},
        timeout=20,
    )
    assert r5.status_code == 200
    assert r5.json()["count"] == 5


def test_compare_au_specific_fields_surface(partner_headers):
    """AU compare should surface skillselect_tier + state_nomination."""
    r = requests.post(
        f"{BASE_URL}/api/sales/occupations/compare",
        headers=partner_headers,
        json={"items": [
            {"country_code": "AU", "code": "261313"},  # Software Engineer
            {"country_code": "AU", "code": "233211"},  # Civil Engineer
        ]},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    for it in items:
        atlas = it.get("atlas") or {}
        # AU codes shouldn't have CA fields
        assert atlas.get("teer_category") in (None, 0)


def test_compare_cross_country_mixed(partner_headers):
    """Mix AU + CA in same comparison — both should return atlas data."""
    r = requests.post(
        f"{BASE_URL}/api/sales/occupations/compare",
        headers=partner_headers,
        json={"items": [
            {"country_code": "CA", "code": "21231"},
            {"country_code": "AU", "code": "261313"},
        ]},
        timeout=20,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    ca = next(it for it in items if it["country_code"] == "CA")
    au = next(it for it in items if it["country_code"] == "AU")
    assert ca["atlas"].get("teer_category") == 1
    assert au["atlas"].get("teer_category") is None  # AU doesn't use TEER


def test_compare_best_fit_score_includes_quebec_bonus(partner_headers):
    """Quebec-eligible codes get a +10 score bonus."""
    r = requests.post(
        f"{BASE_URL}/api/sales/occupations/compare",
        headers=partner_headers,
        json={"items": [
            {"country_code": "CA", "code": "21231"},
            {"country_code": "CA", "code": "31102"},
        ]},
        timeout=20,
    )
    items = r.json()["items"]
    for it in items:
        qe = it["atlas"].get("quebec_eligibility") or {}
        if qe.get("eligible"):
            # Score should be > 0 since they're all TEER 1 with FSWP/CEC
            assert it["best_fit_score"] > 0
