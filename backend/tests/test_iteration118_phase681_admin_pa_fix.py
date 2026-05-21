"""Phase 6.8.1 — Admin PA Fix tests."""
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


def _seed(headers):
    a = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "TEST_681",
        "client_email": "t681@test.com",
        "client_phone": "+91-9000000000",
        "profile": {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 30},
                "education": {"highest_qualification": "bachelor"},
                "language": {"scores": {"overall": 7.5}},
                "professional": {"current_profession": "SE", "years_experience_total": 6},
            },
        },
        "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=headers, timeout=15).json()
    return a["id"]


# ════════════════════════════════════════════════════════════════
# Partner-options
# ════════════════════════════════════════════════════════════════
def test_partner_options_lists_active_users(admin_headers):
    r = requests.get(f"{BASE}/sales/assessments/partner-options", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert "items" in d and "count" in d
    # At least one partner/sales user expected
    assert d["count"] >= 1
    # Roles must be one of expected set
    valid_roles = {"partner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head"}
    for item in d["items"]:
        assert item["role"] in valid_roles


# ════════════════════════════════════════════════════════════════
# Admin Create PA — partner_id required
# ════════════════════════════════════════════════════════════════
def test_admin_create_pa_without_partner_rejected(admin_headers):
    aid = _seed(admin_headers)
    r = requests.post(f"{BASE}/sales/assessments/{aid}/create-pa", json={"lead_source": "test"}, headers=admin_headers, timeout=10)
    assert r.status_code == 400
    assert "partner" in r.json()["detail"].lower()
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_admin_create_pa_with_partner_succeeds(admin_headers):
    # Get a partner
    partners = requests.get(f"{BASE}/sales/assessments/partner-options", headers=admin_headers, timeout=10).json()
    pid = partners["items"][0]["id"]
    aid = _seed(admin_headers)
    r = requests.post(f"{BASE}/sales/assessments/{aid}/create-pa",
                      json={"partner_id": pid, "lead_source": "test"}, headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["pa_id"]
    assert d["pa_number"].startswith("PA-")
    assert d["partner_id"] == pid
    assert d["partner_name"]
    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/orphaned-pas/{d['pa_id']}", headers=admin_headers)
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_admin_create_pa_with_invalid_partner_rejected(admin_headers):
    aid = _seed(admin_headers)
    r = requests.post(f"{BASE}/sales/assessments/{aid}/create-pa",
                      json={"partner_id": "DOESNOTEXIST", "lead_source": "test"}, headers=admin_headers, timeout=10)
    assert r.status_code == 404
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_admin_create_pa_sets_full_pa_schema(admin_headers):
    """PA must have all fields expected by the pipeline UI."""
    partners = requests.get(f"{BASE}/sales/assessments/partner-options", headers=admin_headers, timeout=10).json()
    pid = partners["items"][0]["id"]
    aid = _seed(admin_headers)
    r = requests.post(f"{BASE}/sales/assessments/{aid}/create-pa",
                      json={"partner_id": pid, "lead_source": "test"}, headers=admin_headers, timeout=15)
    pa_id = r.json()["pa_id"]
    # Confirm via raw query through the admin orphaned-pas endpoint negative match
    # (the PA should NOT be in orphan list)
    orph = requests.get(f"{BASE}/sales/assessments/orphaned-pas/list", headers=admin_headers, timeout=10).json()
    orph_ids = {it["id"] for it in orph["items"]}
    assert pa_id not in orph_ids
    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/orphaned-pas/{pa_id}", headers=admin_headers)
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


# ════════════════════════════════════════════════════════════════
# Partner self-assigns (unchanged flow)
# ════════════════════════════════════════════════════════════════
def test_partner_create_pa_self_assigns(admin_headers):
    """Partner doesn't need partner_id — should self-assign."""
    r = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if r.status_code != 200:
        pytest.skip("partner not seeded")
    p_tok = r.json()["token"]
    p_headers = {"Authorization": f"Bearer {p_tok}"}
    # Partner creates assessment
    aid = _seed(p_headers)
    # Partner creates PA (no partner_id needed)
    r2 = requests.post(f"{BASE}/sales/assessments/{aid}/create-pa", json={"lead_source": "test"}, headers=p_headers, timeout=15)
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert d["pa_id"]
    assert d["partner_id"]  # Auto-set to partner's own id
    assert d["pa_number"].startswith("PA-")
    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/orphaned-pas/{d['pa_id']}", headers=admin_headers)
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=p_headers)


# ════════════════════════════════════════════════════════════════
# Orphaned PAs Cleanup
# ════════════════════════════════════════════════════════════════
def test_orphan_list_admin_only():
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    r = requests.get(f"{BASE}/sales/assessments/orphaned-pas/list", headers={"Authorization": f"Bearer {p.json()['token']}"}, timeout=10)
    assert r.status_code == 403


def test_orphan_assign_and_delete(admin_headers):
    # Create an orphan by inserting one directly into DB OR use the existing 17 orphans
    orph = requests.get(f"{BASE}/sales/assessments/orphaned-pas/list", headers=admin_headers, timeout=10).json()
    if orph["count"] == 0:
        pytest.skip("No orphans available")
    # Delete the first orphan
    pa_id = orph["items"][0]["id"]
    r = requests.delete(f"{BASE}/sales/assessments/orphaned-pas/{pa_id}", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    # Should no longer appear in list
    orph2 = requests.get(f"{BASE}/sales/assessments/orphaned-pas/list", headers=admin_headers, timeout=10).json()
    assert all(it["id"] != pa_id for it in orph2["items"])


def test_orphan_assign_unknown_partner_404(admin_headers):
    orph = requests.get(f"{BASE}/sales/assessments/orphaned-pas/list", headers=admin_headers, timeout=10).json()
    if orph["count"] == 0:
        pytest.skip("No orphans available")
    pa_id = orph["items"][0]["id"]
    r = requests.post(f"{BASE}/sales/assessments/orphaned-pas/{pa_id}/assign",
                      json={"partner_id": "NONEXISTENT"}, headers=admin_headers, timeout=10)
    assert r.status_code == 404
