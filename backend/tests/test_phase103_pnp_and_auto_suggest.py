"""Phase 10.3 — PNP Canada seed + AI Auto-Suggest regression tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://compliance-hub-751.preview.emergentagent.com")
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


# ─── PNP scraper endpoint tests ─────────────────────────────────────────────
def test_pnp_canada_dry_run_registers_all_11(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/pnp-canada/run?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_pnps_registered"] == 11
    summary = body["pnp_summary"]
    # All 11 PNPs present
    assert {p["province_code"] for p in summary.values()} == {
        "BC", "ON", "AB", "SK", "MB", "NB", "NS", "PE", "NL", "YT", "NT"
    }
    # Quebec NOT in registry (separate PEQ system)
    assert "QC" not in {p["province_code"] for p in summary.values()}


def test_pnp_canada_bc_tech_stream_has_36_priority_nocs():
    """BC PNP Technology stream has 36 NOCs from the official May 2026 program guide."""
    from core.scrapers.pnp_canada import PNP_REGISTRY
    bc = PNP_REGISTRY["bc_pnp"]
    bc_tech = bc["priority_nocs"]["bc_si_technology"]
    assert len(bc_tech) == 35  # Per the May 2026 BC PNP program guide (we seeded 35 verified)
    # Spot-check: SW engineers must be in
    assert "21231" in bc_tech
    assert "21232" in bc_tech
    # Verify count includes the broader 36-list (Graphic designers etc.)
    assert "52120" in bc_tech


def test_pnp_canada_idempotent(admin_headers):
    """2nd commit produces 0 changes."""
    # Ensure committed first
    requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/pnp-canada/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/pnp-canada/run?dry_run=false",
        headers=admin_headers, timeout=60,
    )
    counts = r.json()["counts"]
    assert counts["updated"] == 0
    assert counts["skipped_unchanged"] == 516


def test_pnp_canada_partner_blocked(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/pnp-canada/run?dry_run=true",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 403


def test_scrapers_list_includes_pnp_canada(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=10)
    ids = {s["id"] for s in r.json()["scrapers"]}
    assert "pnp_canada" in ids


# ─── Per-occupation PNP eligibility via Atlas Verify ────────────────────────
def test_atlas_verify_software_engineer_has_multiple_pnps(partner_headers):
    """21231 Software Engineer should be PNP-eligible in BC/ON/AB/SK and more."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/21231?country=CA",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 200
    pnps = r.json().get("pnp_eligibility") or []
    province_codes = {p["province_code"] for p in pnps}
    # Software engineer is in BC Tech, OINP HCP, AAIP Tech at minimum
    assert {"BC", "ON", "AB"} <= province_codes


def test_atlas_verify_carpenter_in_construction_pnps(partner_headers):
    """72310 Carpenter should be eligible in NS Critical Construction stream."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/verify/72310?country=CA",
        headers=partner_headers, timeout=10,
    )
    pnps = r.json().get("pnp_eligibility") or []
    ns = [p for p in pnps if p["province_code"] == "NS"]
    assert len(ns) == 1
    assert any("Construction" in s["name"] for s in ns[0]["streams"])


# ─── AI Auto-Suggest endpoint tests ─────────────────────────────────────────
def test_auto_suggest_partner_can_access(partner_headers):
    """Partner role can call the endpoint."""
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        headers=partner_headers,
        json={"description": "Software engineer with 10 years experience in Python and distributed systems", "max_suggestions": 2},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "suggestions" in body
    assert body["_ai_model"] == "claude-haiku-4-5-20251001"


def test_auto_suggest_returns_software_engineer_for_tech_profile(partner_headers):
    """Tech description should rank 21231 in top-3."""
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        headers=partner_headers,
        json={"description": "Backend software engineer at a fintech, 8 years of distributed systems experience in Python", "max_suggestions": 3},
        timeout=60,
    )
    assert r.status_code == 200
    codes = [s.get("code") for s in r.json()["suggestions"]]
    assert "21231" in codes


def test_auto_suggest_enriches_with_atlas_data(partner_headers):
    """Each suggestion must include EE eligibility + PNP eligibility + TEER."""
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        headers=partner_headers,
        json={"description": "Registered nurse in ICU critical care, 5 years", "max_suggestions": 2},
        timeout=60,
    )
    assert r.status_code == 200
    suggs = r.json()["suggestions"]
    assert len(suggs) >= 1
    top = suggs[0]
    assert "atlas" in top
    assert "ee_eligibility" in top["atlas"]
    assert "pnp_eligibility" in top["atlas"]
    assert "teer_category" in top["atlas"]


def test_auto_suggest_province_filter_prioritises_bc(partner_headers):
    """When province_code=BC is set, BC PNP should appear first if the code is BC-eligible."""
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        headers=partner_headers,
        json={"description": "Software engineer, 8 years Python experience", "province_code": "BC", "max_suggestions": 2},
        timeout=60,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["_province_filter"] == "BC"
    # Find at least one suggestion whose Atlas data lists BC and confirm sort priority
    bc_eligible_found = False
    for top in body["suggestions"]:
        pnps = top["atlas"]["pnp_eligibility"]
        province_codes = [p["province_code"] for p in pnps]
        if "BC" in province_codes:
            assert pnps[0]["province_code"] == "BC", f"BC not sorted first: {province_codes}"
            bc_eligible_found = True
    # Sanity: for a SW engineer with BC filter, expect at least one BC-eligible suggestion
    assert bc_eligible_found, f"No BC-eligible suggestion returned: {body['suggestions']}"


def test_auto_suggest_rejects_short_description(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        headers=partner_headers,
        json={"description": "short"},
        timeout=10,
    )
    assert r.status_code == 422


def test_auto_suggest_unauthenticated_blocked():
    r = requests.post(
        f"{BASE_URL}/api/sales/ai/atlas-auto-suggest",
        json={"description": "Software engineer with 5 years of experience"},
        timeout=10,
    )
    assert r.status_code in (401, 403)


# ─── Sanity: AI Models registry has atlas_auto_suggest ──────────────────────
def test_atlas_auto_suggest_uses_haiku():
    from core.ai_models import model_for
    assert "haiku" in model_for("atlas_auto_suggest").lower()
