"""Phase 6.10.1 — CA / NZ Rebuild + Calculator Wiring tests."""
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
# 1A — Canada template rebuilt with full CRS structure
# ════════════════════════════════════════════════════════════════
def test_canada_template_rebuilt(admin_headers):
    r = requests.get(f"{BASE}/country-templates/CA", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["country_code"] == "CA"
    assert d["classification_system"] == "NOC"
    assert d["pass_mark"] == 67
    assert d["status"] == "draft"  # awaiting admin verification
    # Must include the core CRS factor categories
    names = [f["factor_name"] for f in d["factors"]]
    assert any("Age" in n for n in names)
    assert any("Level of Education" in n or "Education" in n for n in names)
    assert any("First Official Language" in n for n in names)
    assert any("Canadian Work Experience" in n for n in names)
    # Spouse factor
    assert any("Spouse" in n for n in names)
    # Skill transferability
    assert any("Skill Transferability" in n for n in names)
    # Additional points
    assert any("Provincial Nomination" in n for n in names)
    assert any("Sibling in Canada" in n for n in names)
    assert any("French" in n for n in names)
    # PNP should be +600
    pnp = next(f for f in d["factors"] if "Provincial Nomination" in f["factor_name"])
    yes_option = next(o for o in pnp["options"] if "Yes" in o["label"])
    assert yes_option["points"] == 600


def test_canada_has_minimum_factor_count(admin_headers):
    """CRS has ~16 factor families in our structure."""
    r = requests.get(f"{BASE}/country-templates/CA", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert len(r.json()["factors"]) >= 12


# ════════════════════════════════════════════════════════════════
# 1B — New Zealand SMC 6-points
# ════════════════════════════════════════════════════════════════
def test_new_zealand_template_rebuilt(admin_headers):
    r = requests.get(f"{BASE}/country-templates/NZ", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["country_code"] == "NZ"
    assert d["pass_mark"] == 6  # current SMC 6-points threshold
    assert d["status"] == "draft"
    names = [f["factor_name"] for f in d["factors"]]
    assert any("Qualifications" in n for n in names)
    assert any("Income" in n for n in names)
    assert any("Occupational Registration" in n for n in names)
    assert any("NZ Skilled Work Experience" in n for n in names)
    # Doctoral should hit 6 points
    quals = next(f for f in d["factors"] if "Qualifications" in f["factor_name"])
    phd_opt = next(o for o in quals["options"] if "Doctoral" in o["label"] or "PhD" in o["label"])
    assert phd_opt["points"] == 6


# ════════════════════════════════════════════════════════════════
# 1C — Calculator template_status surfaced (draft for CA/NZ)
# ════════════════════════════════════════════════════════════════
def test_calculator_surfaces_template_status_ca(admin_headers):
    r = requests.post(
        f"{BASE}/sales/calculator/calculate-batch",
        json={
            "profile": {
                "marital_status": "single",
                "primary_applicant": {
                    "personal": {"age": 30},
                    "education": {"highest_qualification": "bachelor"},
                    "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
                    "professional": {"years_experience_total": 6},
                    "au_extras": {}, "ca_extras": {}, "nz_extras": {},
                },
            },
            "targets": [
                {"country": "AU", "visa_subclass": "189"},
                {"country": "CA", "visa_subclass": "express_entry"},
                {"country": "NZ", "visa_subclass": "smc"},
            ],
        },
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 200
    results = r.json()["results"]
    by_country = {x["country_code"]: x for x in results}
    # All 3 should be calculated successfully (legacy rules — zero regression)
    for cc in ("AU", "CA", "NZ"):
        assert "total" in by_country[cc]
        assert "template_status" in by_country[cc]
    # AU + CA + NZ are all draft right now (admin hasn't verified yet)
    assert by_country["AU"]["template_status"] == "draft"
    assert by_country["AU"]["template_in_use"] is False
    assert by_country["CA"]["template_status"] == "draft"
    assert by_country["NZ"]["template_status"] == "draft"


def test_calculator_legacy_values_intact_for_australia(admin_headers):
    """AU is the regression canary — score must remain the same as pre-6.10."""
    r = requests.post(
        f"{BASE}/sales/calculator/calculate",
        json={
            "country": "AU",
            "visa_subclass": "189",
            "profile": {
                "marital_status": "single",
                "primary_applicant": {
                    "personal": {"age": 30},
                    "education": {"highest_qualification": "bachelor"},
                    "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
                    "professional": {"years_experience_total": 6},
                    "au_extras": {}, "ca_extras": {}, "nz_extras": {},
                },
            },
        },
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 200
    d = r.json()
    # Same expected total as Phase 6.8 baseline (75)
    assert d["total"] == 75
    assert d["template_status"] == "draft"  # AU template not yet admin-verified


# ════════════════════════════════════════════════════════════════
# 1D — Admin can flip status to 'verified' via verify endpoint
# ════════════════════════════════════════════════════════════════
def test_admin_can_verify_au_template(admin_headers):
    r = requests.post(
        f"{BASE}/country-templates/AU/verify",
        json={"source_reference": "https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list",
              "review_notes": "Cross-checked against Schedule 6 + current SOL"},
        headers=admin_headers, timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "verified"

    # Calculator now reports template_in_use = True for AU
    r2 = requests.post(
        f"{BASE}/sales/calculator/calculate",
        json={
            "country": "AU", "visa_subclass": "189",
            "profile": {
                "marital_status": "single",
                "primary_applicant": {
                    "personal": {"age": 30},
                    "education": {"highest_qualification": "bachelor"},
                    "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
                    "professional": {"years_experience_total": 6},
                    "au_extras": {}, "ca_extras": {}, "nz_extras": {},
                },
            },
        },
        headers=admin_headers, timeout=10,
    )
    assert r2.status_code == 200
    assert r2.json()["template_status"] == "verified"
    assert r2.json()["template_in_use"] is True
    # Score must remain stable (still 75 — verified template doesn't override yet, but value matches legacy)
    assert r2.json()["total"] == 75

    # Reset for downstream tests
    r3 = requests.put(f"{BASE}/country-templates/AU", json={"status": "draft"}, headers=admin_headers, timeout=10)
    assert r3.status_code == 200


# ════════════════════════════════════════════════════════════════
# Regression — assessment flow still works
# ════════════════════════════════════════════════════════════════
def test_assessment_create_still_works(admin_headers):
    r = requests.post(
        f"{BASE}/sales/assessments",
        json={
            "client_name": "Phase 6.10.1 Smoke",
            "client_email": "smoke@test.com",
            "client_phone": "+91-9000000000",
            "profile": {
                "marital_status": "single",
                "primary_applicant": {
                    "personal": {"age": 30},
                    "education": {"highest_qualification": "bachelor"},
                    "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
                    "professional": {"years_experience_total": 6, "current_profession": "SE"},
                    "au_extras": {}, "ca_extras": {}, "nz_extras": {},
                },
            },
            "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"},
            "targets": [{"country": "AU", "visa_subclass": "189"}],
        },
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 200
    aid = r.json()["id"]
    assert r.json()["best_total"] == 75
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_occupation_master_unchanged(admin_headers):
    """88 records still intact — Part 1 didn't touch occupation_master."""
    r = requests.get(f"{BASE}/occupation-master?limit=200", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["total"] == 88
