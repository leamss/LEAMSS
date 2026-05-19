"""Phase 6 v2 Part 3 — Integrated Workflow + AI Helpers tests."""
import os
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://staff-dashboard-66.preview.emergentagent.com"
BASE = f"{API}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    return r.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ════════════════════════════════════════════════════════════════
# Save Assessment
# ════════════════════════════════════════════════════════════════
def test_save_assessment(admin_headers):
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "TEST_P3_Save",
        "client_email": "test@example.com",
        "profile": {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 30},
                "professional": {"current_profession": "Software Engineer", "years_experience_total": 6},
                "education": {"highest_qualification": "bachelor"},
                "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
            },
        },
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["id"].startswith("SAH-")
    assert d["best_country_code"] == "AU"
    assert d["best_total"] == 75
    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/{d['id']}", headers=admin_headers)


def test_save_assessment_multi_country(admin_headers):
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "TEST_P3_MultiCountry",
        "profile": {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 30},
                "professional": {"current_profession": "Engineer", "years_experience_total": 6},
                "education": {"highest_qualification": "bachelor"},
                "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
            },
        },
        "targets": [{"country": "AU", "visa_subclass": "189"}, {"country": "CA"}, {"country": "NZ"}],
    }, headers=admin_headers, timeout=15)
    d = r.json()
    assert len(d["targets"]) == 3
    assert len(d["results"]) == 3
    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/{d['id']}", headers=admin_headers)


def test_list_assessments(admin_headers):
    # Create
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "TEST_P3_List",
        "profile": {"marital_status": "single", "primary_applicant": {"personal": {"age": 30}, "education": {"highest_qualification": "bachelor"}}},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=admin_headers, timeout=15)
    aid = r.json()["id"]

    r2 = requests.get(f"{BASE}/sales/assessments?limit=10", headers=admin_headers, timeout=10)
    assert r2.status_code == 200
    d = r2.json()
    assert d["count"] >= 1
    assert any(i["id"] == aid for i in d["items"])
    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_get_assessment_by_id(admin_headers):
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "TEST_P3_Get",
        "profile": {"marital_status": "single", "primary_applicant": {"personal": {"age": 30}, "education": {"highest_qualification": "bachelor"}}},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=admin_headers, timeout=15)
    aid = r.json()["id"]
    r2 = requests.get(f"{BASE}/sales/assessments/{aid}", headers=admin_headers, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["id"] == aid
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_create_pa_from_assessment(admin_headers):
    # Save
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "TEST_P3_PA",
        "client_email": "pa-test@example.com",
        "profile": {"marital_status": "single", "primary_applicant": {"personal": {"age": 30}, "education": {"highest_qualification": "bachelor"}}},
        "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=admin_headers, timeout=15)
    aid = r.json()["id"]
    # Create PA
    r2 = requests.post(f"{BASE}/sales/assessments/{aid}/create-pa", json={}, headers=admin_headers, timeout=10)
    assert r2.status_code == 200
    d = r2.json()
    assert d["pa_id"].startswith("PA-")
    assert d["already_linked"] is False
    # Idempotent
    r3 = requests.post(f"{BASE}/sales/assessments/{aid}/create-pa", json={}, headers=admin_headers, timeout=10)
    d3 = r3.json()
    assert d3["pa_id"] == d["pa_id"]
    assert d3["already_linked"] is True
    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


# ════════════════════════════════════════════════════════════════
# Calculator batch
# ════════════════════════════════════════════════════════════════
def test_calculator_batch_3_countries(admin_headers):
    r = requests.post(f"{BASE}/sales/calculator/calculate-batch", json={
        "profile": {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 30},
                "professional": {"current_profession": "Software Engineer", "years_experience_total": 6},
                "education": {"highest_qualification": "bachelor"},
                "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
            },
        },
        "targets": [{"country": "AU", "visa_subclass": "189"}, {"country": "CA"}, {"country": "NZ"}],
    }, headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["count"] == 3
    codes = [x["country_code"] for x in d["results"]]
    assert codes == ["AU", "CA", "NZ"]


# ════════════════════════════════════════════════════════════════
# AI Occupation Suggester (skipped if LLM budget exhausted)
# ════════════════════════════════════════════════════════════════
def test_ai_suggest_occupation_endpoint_shape(admin_headers):
    """Suggester endpoint contract test — may return 502 if AI budget low.
    Either way, the response should not crash the server."""
    r = requests.post(f"{BASE}/sales/ai/suggest-occupation", json={
        "description": "8 years in digital marketing managing social media campaigns, brand strategy and content for tech companies. Bachelor's in marketing.",
        "country_codes": ["AU"],
        "max_suggestions": 3,
    }, headers=admin_headers, timeout=60)
    assert r.status_code in (200, 502), f"Unexpected {r.status_code}: {r.text[:200]}"
    if r.status_code == 200:
        d = r.json()
        assert "suggestions" in d
        assert isinstance(d["suggestions"], list)
        if d["suggestions"]:
            # All suggested codes must be _verified=True (exist in available_codes)
            for s in d["suggestions"]:
                assert "country_code" in s
                assert "code" in s
                assert s.get("_verified") is True, f"AI returned an invalid code {s.get('code')}"
            # Confidence should be one of high/medium/low
            assert all(s.get("confidence", "").lower() in ("high", "medium", "low") for s in d["suggestions"])


def test_ai_suggest_min_description_length(admin_headers):
    r = requests.post(f"{BASE}/sales/ai/suggest-occupation", json={
        "description": "short", "country_codes": ["AU"],
    }, headers=admin_headers, timeout=10)
    assert r.status_code == 422  # Pydantic min_length=20


# ════════════════════════════════════════════════════════════════
# RBAC
# ════════════════════════════════════════════════════════════════
def test_save_assessment_requires_auth():
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "Anon", "profile": {}, "targets": [{"country": "AU"}],
    }, timeout=5)
    assert r.status_code in (401, 403)


def test_client_cannot_save_assessment():
    """Client role should NOT have access to sales assessments."""
    r = requests.post(f"{BASE}/auth/login", json={"email": "client@leamss.com", "password": "Client@123"}, timeout=10)
    if r.status_code != 200:
        pytest.skip("client@leamss.com not seeded")
    tok = r.json()["token"]
    r2 = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "X", "profile": {}, "targets": [{"country": "AU"}],
    }, headers={"Authorization": f"Bearer {tok}"}, timeout=5)
    assert r2.status_code == 403
