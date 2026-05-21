"""Phase 6.8.2 / 6.8.3 / 6.8.4 — Stabilization backend tests."""
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


def _seed_assessment(headers, name="LIST_TEST", profile_override=None):
    base_profile = {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 30},
            "education": {"highest_qualification": "bachelor"},
            "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7.0, "writing": 7.0, "speaking": 7.5}},
            "professional": {"current_profession": "SE", "years_experience_total": 6},
            "au_extras": {},
            "ca_extras": {},
            "nz_extras": {},
        },
    }
    if profile_override:
        base_profile["primary_applicant"].update(profile_override)
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": name,
        "client_email": f"{name.lower()}@test.com",
        "client_phone": "+91-9000000000",
        "profile": base_profile,
        "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ════════════════════════════════════════════════════════════════
# Phase 6.8.2 — List Assessments + Filtering
# ════════════════════════════════════════════════════════════════
def test_list_assessments_admin_sees_all(admin_headers):
    aid = _seed_assessment(admin_headers, name="ADMIN_LIST_A")
    r = requests.get(f"{BASE}/sales/assessments?limit=100", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert "items" in d and "count" in d
    ids = {it["id"] for it in d["items"]}
    assert aid in ids
    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_list_assessments_search_filter(admin_headers):
    aid = _seed_assessment(admin_headers, name="UNIQUE_SEARCH_TAG_8821")
    r = requests.get(f"{BASE}/sales/assessments?search=UNIQUE_SEARCH_TAG_8821&limit=10", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(it["id"] == aid for it in items)
    # Filter mismatch
    r2 = requests.get(f"{BASE}/sales/assessments?search=DEFINITELY_DOES_NOT_MATCH_XYZ_999&limit=10", headers=admin_headers, timeout=10)
    assert r2.status_code == 200
    assert all(it["id"] != aid for it in r2.json()["items"])
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_list_assessments_partner_sees_only_own(admin_headers):
    """Partner should NOT see admin's assessments."""
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    p_headers = {"Authorization": f"Bearer {p.json()['token']}"}
    admin_aid = _seed_assessment(admin_headers, name="ADMIN_PRIVATE_77")
    r = requests.get(f"{BASE}/sales/assessments?limit=200", headers=p_headers, timeout=10)
    assert r.status_code == 200
    partner_ids = {it["id"] for it in r.json()["items"]}
    assert admin_aid not in partner_ids
    requests.delete(f"{BASE}/sales/assessments/{admin_aid}", headers=admin_headers)


def test_list_assessments_includes_link_and_share_status(admin_headers):
    """List rows must surface linked_pa_id and share_active so the UI can pill them."""
    aid = _seed_assessment(admin_headers, name="STATUS_PILL_TEST")
    r = requests.get(f"{BASE}/sales/assessments?limit=10", headers=admin_headers, timeout=10)
    items = r.json()["items"]
    me = next((it for it in items if it["id"] == aid), None)
    assert me is not None
    # Brand new — no PA, no share
    assert not me.get("linked_pa_id")
    assert not me.get("share_active")
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


# ════════════════════════════════════════════════════════════════
# Phase 6.8.3 — Compare Endpoint
# ════════════════════════════════════════════════════════════════
def test_compare_two_au_codes(admin_headers):
    r = requests.post(
        f"{BASE}/sales/occupations/compare",
        json={"items": [
            {"country_code": "AU", "code": "261313"},
            {"country_code": "AU", "code": "141311"},
        ]},
        headers=admin_headers, timeout=10,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["count"] == 2
    assert len(d["items"]) == 2
    for it in d["items"]:
        assert "title" in it
        assert "country_code" in it
        assert it["country_code"] == "AU"


def test_compare_cross_country(admin_headers):
    r = requests.post(
        f"{BASE}/sales/occupations/compare",
        json={"items": [
            {"country_code": "AU", "code": "261313"},
            {"country_code": "CA", "code": "21231"},
        ]},
        headers=admin_headers, timeout=10,
    )
    assert r.status_code == 200, r.text
    codes = {it["country_code"] for it in r.json()["items"]}
    assert "AU" in codes or "CA" in codes  # at least one resolves


def test_compare_rejects_too_few_items(admin_headers):
    r = requests.post(
        f"{BASE}/sales/occupations/compare",
        json={"items": [{"country_code": "AU", "code": "261313"}]},
        headers=admin_headers, timeout=10,
    )
    assert r.status_code == 422  # min_length=2


def test_compare_rejects_too_many_items(admin_headers):
    items = [{"country_code": "AU", "code": "261313"} for _ in range(5)]
    r = requests.post(
        f"{BASE}/sales/occupations/compare",
        json={"items": items},
        headers=admin_headers, timeout=10,
    )
    assert r.status_code == 422  # max_length=4


# ════════════════════════════════════════════════════════════════
# Phase 6.8.4 — Calculator picks up extra factors
# ════════════════════════════════════════════════════════════════
def _calc(profile, country, visa_subclass, headers):
    r = requests.post(
        f"{BASE}/sales/calculator/calculate-batch",
        json={"profile": profile, "targets": [{"country": country, "visa_subclass": visa_subclass}]},
        headers=headers, timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()["results"][0]


def _base_profile():
    return {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 30},
            "education": {"highest_qualification": "bachelor"},
            "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7.0, "writing": 7.0, "speaking": 7.5}},
            "professional": {"years_experience_total": 6, "current_profession": "SE"},
            "au_extras": {},
            "ca_extras": {},
            "nz_extras": {},
        },
    }


def test_factor_au_naati_adds_5_points(admin_headers):
    p1 = _base_profile()
    p2 = _base_profile()
    p2["primary_applicant"]["au_extras"]["naati_accredited"] = True
    r1 = _calc(p1, "AU", "189", admin_headers)
    r2 = _calc(p2, "AU", "189", admin_headers)
    assert r2["total"] == r1["total"] + 5, f"NAATI should add +5: {r1['total']} → {r2['total']}"


def test_factor_au_professional_year_adds_5_points(admin_headers):
    p1 = _base_profile()
    p2 = _base_profile()
    p2["primary_applicant"]["au_extras"]["professional_year_completed"] = True
    r1 = _calc(p1, "AU", "189", admin_headers)
    r2 = _calc(p2, "AU", "189", admin_headers)
    assert r2["total"] == r1["total"] + 5


def test_factor_au_stem_specialist_adds_10_points(admin_headers):
    p1 = _base_profile()
    p2 = _base_profile()
    p2["primary_applicant"]["au_extras"]["specialist_education_stem_au"] = True
    r1 = _calc(p1, "AU", "189", admin_headers)
    r2 = _calc(p2, "AU", "189", admin_headers)
    assert r2["total"] == r1["total"] + 10


def test_factor_au_state_nomination_190_adds_5_points(admin_headers):
    """State-nominated subclass 190 adds 5 points."""
    p1 = _base_profile()
    p2 = _base_profile()
    p2["primary_applicant"]["au_extras"]["state_nominated"] = True
    r1 = _calc(p1, "AU", "190", admin_headers)
    r2 = _calc(p2, "AU", "190", admin_headers)
    assert r2["total"] == r1["total"] + 5


def test_factor_ca_pnp_dominates(admin_headers):
    """PNP adds 600 — should move CRS into Express Entry range."""
    p1 = _base_profile()
    p2 = _base_profile()
    p2["primary_applicant"]["ca_extras"]["provincial_nomination"] = True
    r1 = _calc(p1, "CA", "express_entry", admin_headers)
    r2 = _calc(p2, "CA", "express_entry", admin_headers)
    assert r2["total"] >= r1["total"] + 600


def test_factor_ca_french_clb7_adds_50_points(admin_headers):
    p1 = _base_profile()
    p2 = _base_profile()
    p2["primary_applicant"]["ca_extras"]["french_proficiency_clb_7"] = True
    r1 = _calc(p1, "CA", "express_entry", admin_headers)
    r2 = _calc(p2, "CA", "express_entry", admin_headers)
    assert r2["total"] == r1["total"] + 50


def test_factor_nz_skilled_employment_adds_50_points(admin_headers):
    p1 = _base_profile()
    p2 = _base_profile()
    p2["primary_applicant"]["nz_extras"]["nz_skilled_employment_current"] = True
    r1 = _calc(p1, "NZ", "smc", admin_headers)
    r2 = _calc(p2, "NZ", "smc", admin_headers)
    assert r2["total"] == r1["total"] + 50


def test_factor_nz_job_offer_adds_30_points(admin_headers):
    p1 = _base_profile()
    p2 = _base_profile()
    p2["primary_applicant"]["nz_extras"]["nz_job_offer"] = True
    r1 = _calc(p1, "NZ", "smc", admin_headers)
    r2 = _calc(p2, "NZ", "smc", admin_headers)
    assert r2["total"] == r1["total"] + 30
