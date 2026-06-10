"""Phase 9.8 — CA + NZ calculator rules wiring verification."""
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
def reset_rules(admin_headers):
    """Ensure each test starts with hardcoded defaults for CA + NZ."""
    for country in ("CA", "NZ"):
        requests.post(f"{BASE_URL}/api/anz-intel/calculator-rules/{country}/reset",
                      headers=admin_headers, timeout=10)
    yield
    for country in ("CA", "NZ"):
        requests.post(f"{BASE_URL}/api/anz-intel/calculator-rules/{country}/reset",
                      headers=admin_headers, timeout=10)


# ─── CA ──────────────────────────────────────────────────────────────────────
def _calc_ca(admin_headers, **extras):
    """Canonical CA profile — 28yo bachelor IELTS 7.5 + 3 yrs Canadian work."""
    base = {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 28},
            "education": {"highest_qualification": "bachelor"},
            "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7.5, "writing": 7.5, "speaking": 7.5}},
            "professional": {"years_experience_total": 5.0},
            "ca_extras": {"canadian_work_years": 3.0, **extras},
        },
    }
    return requests.post(
        f"{BASE_URL}/api/sales/calculator/calculate",
        headers=admin_headers,
        json={"profile": base, "country": "CA"},
        timeout=15,
    )


def test_ca_baseline_with_pnp(admin_headers):
    """PNP gives +600 in default."""
    r = _calc_ca(admin_headers, provincial_nomination=True)
    assert r.status_code == 200
    body = r.json()
    assert body["rules_source"] == "hardcoded_defaults"
    pnp = body["breakdown"].get("ca_provincial_nomination") or {}
    assert pnp.get("points") == 600


def test_ca_pnp_override_to_999(admin_headers):
    """Admin override: PNP = 999."""
    custom = {"tables": {"additional": {"type": "named", "items": {"provincial_nomination": 999, "french_clb_7": 50, "sibling_in_canada": 15, "job_offer_noc_00": 200, "job_offer_noc_0_a_b": 50, "canadian_education_3plus_years": 30, "canadian_education_1_2_years": 15}}}}
    p = requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/CA",
                     headers=admin_headers, json=custom, timeout=10)
    assert p.status_code == 200

    r = _calc_ca(admin_headers, provincial_nomination=True)
    body = r.json()
    assert body["rules_source"] == "db_override"
    assert body["breakdown"]["ca_provincial_nomination"]["points"] == 999


def test_ca_job_offer_override(admin_headers):
    """Override NOC 00 job offer from 200 to 50, NOC 0/A/B from 50 to 25."""
    custom = {"tables": {"additional": {"type": "named", "items": {"job_offer_noc_00": 50, "job_offer_noc_0_a_b": 25}}}}
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/CA",
                 headers=admin_headers, json=custom, timeout=10)

    r1 = _calc_ca(admin_headers, job_offer_noc_00=True)
    assert r1.json()["breakdown"]["ca_job_offer"]["points"] == 50

    r2 = _calc_ca(admin_headers, job_offer_noc_0_a_b=True)
    assert r2.json()["breakdown"]["ca_job_offer"]["points"] == 25


def test_ca_french_and_sibling_overrides(admin_headers):
    """Override French CLB 7 and sibling bonuses."""
    custom = {"tables": {"additional": {"type": "named", "items": {"french_clb_7": 100, "sibling_in_canada": 30}}}}
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/CA",
                 headers=admin_headers, json=custom, timeout=10)

    r = _calc_ca(admin_headers, french_proficiency_clb_7=True, sibling_in_canada=True)
    body = r.json()
    assert body["breakdown"]["ca_french"]["points"] == 100
    assert body["breakdown"]["ca_sibling"]["points"] == 30


# ─── NZ ──────────────────────────────────────────────────────────────────────
def _calc_nz(admin_headers, **extras):
    """Canonical NZ profile — 25yo master + 5 yrs experience + job offer."""
    base = {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 25},
            "education": {"highest_qualification": "master"},
            "professional": {"years_experience_total": 5.0},
            "nz_extras": extras,
        },
    }
    return requests.post(
        f"{BASE_URL}/api/sales/calculator/calculate",
        headers=admin_headers,
        json={"profile": base, "country": "NZ"},
        timeout=15,
    )


def test_nz_baseline_no_extras(admin_headers):
    """Baseline: 25yo (30) + master (50) + 5yrs (10) = 90."""
    r = _calc_nz(admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["rules_source"] == "hardcoded_defaults"
    assert body["total"] == 90, f"Baseline 90, got {body['total']}: {body['breakdown']}"


def test_nz_age_override_changes_score(admin_headers):
    """Override age band 20-29 from 30 → 99."""
    custom = {"tables": {"age": {"type": "bands", "bands": [
        {"min": 20, "max": 29, "points": 99},
        {"min": 30, "max": 39, "points": 25},
        {"min": 40, "max": 44, "points": 20},
        {"min": 45, "max": 49, "points": 10},
        {"min": 50, "max": 99, "points": 0},
    ]}}}
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/NZ",
                 headers=admin_headers, json=custom, timeout=10)

    r = _calc_nz(admin_headers)
    body = r.json()
    assert body["rules_source"] == "db_override"
    assert body["breakdown"]["nz_age"]["points"] == 99
    # baseline 90, age was 30 → now 99 → +69 → 159
    assert body["total"] == 159


def test_nz_qualification_override(admin_headers):
    """Master = 80 (vs default 50)."""
    custom = {"tables": {"qualification": {"type": "categorical", "categories": {"master": 80}}}}
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/NZ",
                 headers=admin_headers, json=custom, timeout=10)

    r = _calc_nz(admin_headers)
    body = r.json()
    assert body["breakdown"]["nz_qualification"]["points"] == 80


def test_nz_work_experience_band_override(admin_headers):
    """Override 4-5yrs band from 10 → 25."""
    custom = {"tables": {"skilled_employment_years": {"type": "bands", "bands": [
        {"min": 0, "max": 1, "points": 0},
        {"min": 2, "max": 3, "points": 5},
        {"min": 4, "max": 5, "points": 25},  # was 10
        {"min": 6, "max": 99, "points": 30},
    ]}}}
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/NZ",
                 headers=admin_headers, json=custom, timeout=10)

    r = _calc_nz(admin_headers)
    body = r.json()
    assert body["breakdown"]["nz_work_experience"]["points"] == 25


def test_nz_job_offer_extra_override(admin_headers):
    """Override job_offer extra from 30 → 80."""
    custom = {"tables": {"extras": {"type": "named", "items": {"nz_job_offer": 80}}}}
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/NZ",
                 headers=admin_headers, json=custom, timeout=10)

    r = _calc_nz(admin_headers, nz_job_offer=True)
    body = r.json()
    assert body["breakdown"]["nz_job_offer"]["points"] == 80


def test_nz_partner_master_override(admin_headers):
    """Married + partner with master degree → partner_skilled_master override."""
    custom = {"tables": {"extras": {"type": "named", "items": {"partner_skilled_master": 50}}}}
    requests.put(f"{BASE_URL}/api/anz-intel/calculator-rules/NZ",
                 headers=admin_headers, json=custom, timeout=10)

    r = requests.post(
        f"{BASE_URL}/api/sales/calculator/calculate",
        headers=admin_headers,
        json={
            "profile": {
                "marital_status": "married",
                "primary_applicant": {
                    "personal": {"age": 25},
                    "education": {"highest_qualification": "master"},
                    "professional": {"years_experience_total": 5.0},
                    "nz_extras": {},
                },
                "spouse": {"education": {"highest_qualification": "master"}},
            },
            "country": "NZ",
        },
        timeout=15,
    )
    body = r.json()
    assert body["breakdown"]["nz_partner_qual"]["points"] == 50
