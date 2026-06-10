"""Phase 9.7 — Verify admin-configured rules override the calculator."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://career-match-320.preview.emergentagent.com")
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(autouse=True)
def reset_au_rules(admin_headers):
    """Ensure each test starts with hardcoded defaults."""
    requests.post(f"{BASE_URL}/api/anz-intel/calculator-rules/AU/reset",
                  headers=admin_headers, timeout=10)
    yield
    requests.post(f"{BASE_URL}/api/anz-intel/calculator-rules/AU/reset",
                  headers=admin_headers, timeout=10)


def _calc_single_25yo_bachelor_ielts7(admin_headers):
    """Canonical reference profile — used to verify rule overrides."""
    return requests.post(
        f"{BASE_URL}/api/sales/calculator/calculate",
        headers=admin_headers,
        json={
            "profile": {
                "marital_status": "single",
                "primary_applicant": {
                    "personal": {"age": 27},
                    "education": {"highest_qualification": "bachelor"},
                    "language": {"scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}},
                    "professional": {"years_experience_total": 6.0, "years_experience_australia": 0.0},
                    "au_extras": {"naati_accredited": False, "professional_year_completed": False,
                                  "australian_study_2_years": False, "specialist_education_stem_au": False,
                                  "regional_study_au": False, "state_nominated": False},
                },
            },
            "country": "AU",
            "visa_subclass": "189",
        },
        timeout=15,
    )


def test_default_baseline_score(admin_headers):
    """Hardcoded defaults: 27yo bachelor IELTS 7 single + 6yr OS exp = 30+10+15+10+10 = 75."""
    r = _calc_single_25yo_bachelor_ielts7(admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # age 25-32 = 30, english 7 = 10, exp 5-7 = 10, education bachelor = 15, partner single = 10
    assert body["total"] == 75, f"Expected 75 default, got {body['total']}: {body['breakdown']}"
    assert body["rules_source"] == "hardcoded_defaults"


def test_override_age_band_changes_score(admin_headers):
    """Override age band 25-32 → 99 pts. Result should jump by 99-30 = +69."""
    custom = {
        "tables": {
            "age": {
                "type": "bands", "rule": "test",
                "bands": [
                    {"min": 18, "max": 24, "points": 25},
                    {"min": 25, "max": 32, "points": 99},  # boosted
                    {"min": 33, "max": 39, "points": 25},
                    {"min": 40, "max": 44, "points": 15},
                    {"min": 45, "max": 99, "points": 0},
                ],
            },
        },
    }
    p = requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/AU",
                     headers=admin_headers, json=custom, timeout=10)
    assert p.status_code == 200

    r = _calc_single_25yo_bachelor_ielts7(admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["rules_source"] == "db_override"
    # baseline was 75 with age=30. New age=99 → +69 = 144
    assert body["total"] == 144, f"Expected 144 with override, got {body['total']}: {body['breakdown']}"
    assert body["breakdown"]["age"]["points"] == 99


def test_override_english_tier_changes_score(admin_headers):
    """Override english proficient 10 → 50."""
    custom = {
        "tables": {
            "english": {"type": "tiered", "rule": "test", "tiers": {"superior": 20, "proficient": 50, "competent": 0}},
        },
    }
    p = requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/AU",
                     headers=admin_headers, json=custom, timeout=10)
    assert p.status_code == 200

    r = _calc_single_25yo_bachelor_ielts7(admin_headers)
    body = r.json()
    # baseline 75, english was 10 → now 50 → +40 → 115
    assert body["total"] == 115, f"Expected 115, got {body['total']}: {body['breakdown']}"
    assert body["breakdown"]["english"]["points"] == 50


def test_override_partner_skills_single_value(admin_headers):
    """Override single_or_pr_partner 10 → 0 (sanity)."""
    custom = {
        "tables": {
            "partner_skills": {
                "type": "categorical", "rule": "test",
                "categories": {"single_or_pr_partner": 0, "skilled_partner": 10, "competent_english_only": 5, "non_contributing": 0},
            },
        },
    }
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/AU", headers=admin_headers, json=custom, timeout=10)
    r = _calc_single_25yo_bachelor_ielts7(admin_headers)
    body = r.json()
    # baseline 75, partner was 10 → now 0 → -10 → 65
    assert body["total"] == 65, f"Expected 65, got {body['total']}: {body['breakdown']}"
    assert body["breakdown"]["partner"]["points"] == 0


def test_reset_returns_to_baseline(admin_headers):
    """After PUT + RESET, the override must be cleared and baseline restored."""
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/AU",
                 headers=admin_headers,
                 json={"tables": {"english": {"type": "tiered", "tiers": {"proficient": 999}}}},
                 timeout=10)
    rr = requests.post(f"{BASE_URL}/api/anz-intel/calculator-rules/AU/reset",
                       headers=admin_headers, timeout=10)
    assert rr.status_code == 200
    r = _calc_single_25yo_bachelor_ielts7(admin_headers)
    body = r.json()
    assert body["total"] == 75, f"Expected baseline 75 after reset, got {body['total']}"


def test_partial_override_other_tables_use_defaults(admin_headers):
    """An override that only touches age must NOT affect english/education/partner."""
    custom = {"tables": {"age": {"type": "bands", "bands": [{"min": 25, "max": 32, "points": 40}]}}}
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/AU",
                 headers=admin_headers, json=custom, timeout=10)
    r = _calc_single_25yo_bachelor_ielts7(admin_headers)
    body = r.json()
    # age 40 (override) + english 10 (default) + exp 10 + edu 15 + partner 10 = 85
    assert body["total"] == 85, f"Expected 85, got {body['total']}: {body['breakdown']}"
    assert body["breakdown"]["age"]["points"] == 40
    assert body["breakdown"]["english"]["points"] == 10
    assert body["breakdown"]["partner"]["points"] == 10
