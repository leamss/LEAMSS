"""Phase 7.2 — Unified Calculator + Cost Estimator tests."""
import os
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://career-match-320.preview.emergentagent.com"
BASE = f"{API}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    return r.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def sample_profile():
    return {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 29},
            "education": {"highest_qualification": "master"},
            "language": {"scores": {"overall": 8, "listening": 8, "reading": 8, "writing": 7.5, "speaking": 8}},
            "professional": {"current_profession": "Software Engineer", "years_experience_total": 5},
            "au_extras": {"naati_accredited": True}, "ca_extras": {}, "nz_extras": {},
        },
    }


@pytest.fixture
def sample_occupation():
    return {"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"}


# ─────────────────────────────────────────────────────────────────────────────
# Parallel multi-subclass calculator
# ─────────────────────────────────────────────────────────────────────────────
def test_parallel_calc_au_returns_3_subclasses(admin_headers, sample_profile, sample_occupation):
    r = requests.post(f"{BASE}/sales/wizard/calculate-parallel", headers=admin_headers, json={
        "country_code": "AU",
        "visa_subclasses": ["189", "190", "491"],
        "profile": sample_profile,
        "occupation": sample_occupation,
    }, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["country_code"] == "AU"
    assert d["pass_mark"] == 65
    assert len(d["subclasses"]) == 3
    sub_codes = [s["visa_subclass"] for s in d["subclasses"]]
    assert sub_codes == ["189", "190", "491"]
    # All eligible at 80 pts (>=65 pass mark)
    for s in d["subclasses"]:
        assert s.get("total") and s["total"] > 0
        assert s.get("eligible") is True


def test_parallel_calc_ca(admin_headers, sample_profile):
    r = requests.post(f"{BASE}/sales/wizard/calculate-parallel", headers=admin_headers, json={
        "country_code": "CA",
        "visa_subclasses": ["EE"],
        "profile": sample_profile,
    }, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["country_code"] == "CA"
    assert len(d["subclasses"]) == 1


def test_parallel_calc_invalid_country(admin_headers, sample_profile):
    r = requests.post(f"{BASE}/sales/wizard/calculate-parallel", headers=admin_headers, json={
        "country_code": "XX", "visa_subclasses": ["189"], "profile": sample_profile,
    }, timeout=10)
    assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Cost Estimator
# ─────────────────────────────────────────────────────────────────────────────
def test_cost_estimator_defaults_returns_kb_items(admin_headers):
    r = requests.get(
        f"{BASE}/sales/wizard/cost-estimator/defaults",
        headers=admin_headers,
        params={"country_code": "AU", "visa_subclass": "189", "assessing_body": "ACS"},
        timeout=10,
    )
    assert r.status_code == 200
    d = r.json()
    assert len(d["items"]) >= 3
    categories = {it["category"] for it in d["items"]}
    assert "Government Fees" in categories
    assert "LEAMSS Professional Fees" in categories
    # Total by currency exists
    assert d["total_by_currency"]


def test_cost_estimator_save_and_get(admin_headers, sample_profile):
    # Create an assessment first
    r = requests.post(f"{BASE}/sales/assessments", headers=admin_headers, json={
        "client_name": "Cost Estimator Test",
        "client_email": "ce@test.com", "client_phone": "+91-9000000099",
        "profile": sample_profile,
        "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, timeout=15)
    aid = r.json()["id"]
    try:
        # Save cost estimator
        r = requests.post(f"{BASE}/sales/wizard/cost-estimator/save", headers=admin_headers, json={
            "assessment_id": aid,
            "currency": "INR",
            "items": [
                {"category": "Government Fees", "label": "Visa Fee", "amount": 200000, "currency": "INR", "is_estimated": True, "is_editable": True},
                {"category": "LEAMSS Professional Fees", "label": "PR Processing", "amount": 195000, "currency": "INR", "is_estimated": False, "is_editable": True},
            ],
            "notes": "Test quote",
        }, timeout=10)
        assert r.status_code == 200
        ce = r.json()["cost_estimator"]
        assert ce["total_by_currency"]["INR"] == 395000
        # Get back
        r = requests.get(f"{BASE}/sales/wizard/cost-estimator/{aid}", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert r.json()["total_by_currency"]["INR"] == 395000
    finally:
        requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_cost_estimator_partner_403_on_others_assessment(admin_headers, sample_profile):
    """A partner cannot edit another user's assessment cost estimator."""
    partner = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if partner.status_code != 200:
        pytest.skip("partner not seeded")
    # Admin creates
    r = requests.post(f"{BASE}/sales/assessments", headers=admin_headers, json={
        "client_name": "RBAC test", "client_email": "rbac@t.com", "client_phone": "+91-9000000098",
        "profile": sample_profile,
        "occupation": {"country_code": "AU", "code": "261313", "title": "X", "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, timeout=15)
    aid = r.json()["id"]
    try:
        # Partner tries to save
        r = requests.post(
            f"{BASE}/sales/wizard/cost-estimator/save",
            headers={"Authorization": f"Bearer {partner.json()['token']}"},
            json={"assessment_id": aid, "currency": "INR", "items": []}, timeout=10,
        )
        # Either 403 (not owner) or 404 (not visible) — both are acceptable RBAC outcomes
        assert r.status_code in (403, 404)
    finally:
        requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_cost_estimator_404_on_missing_assessment(admin_headers):
    r = requests.get(f"{BASE}/sales/wizard/cost-estimator/non-existent-id", headers=admin_headers, timeout=10)
    assert r.status_code == 404
