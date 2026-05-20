"""Phase 6.5 — Active Share Links Dashboard sales_report integration tests."""
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


def _seed_sales_report(headers, client="TEST_DASH_SR"):
    """Create a sales assessment and generate a public share link."""
    a = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": client,
        "client_email": f"{client.lower()}@test.com",
        "profile": {"marital_status": "single", "primary_applicant": {"personal": {"age": 30}, "education": {"highest_qualification": "bachelor"}}},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=headers, timeout=15)
    aid = a.json()["id"]
    s = requests.post(f"{BASE}/sales/assessments/{aid}/share", json={"expires_in_days": 7}, headers=headers, timeout=10)
    return aid, s.json()["token"]


def test_dashboard_lists_sales_reports(admin_headers):
    aid, tok = _seed_sales_report(admin_headers, client="TEST_DASH_LIST")
    r = requests.get(f"{BASE}/share-links/?link_type=sales_report", headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text
    d = r.json()
    # Our new row should be present
    found = next((row for row in d["items"] if row.get("token") == tok), None)
    assert found is not None, "Created sales_report token not surfaced in dashboard"
    assert found["type"] == "sales_report"
    assert found["client_name"] == "TEST_DASH_LIST"
    assert found["purpose"] == "sales_eligibility_report"
    assert "pts" in found["amount_label"] or "AU" in found["amount_label"]
    assert found["status"] == "active"
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_dashboard_default_includes_sales_reports(admin_headers):
    """Default listing (no link_type filter) should also include sales_report rows."""
    aid, tok = _seed_sales_report(admin_headers, client="TEST_DASH_DEFAULT")
    r = requests.get(f"{BASE}/share-links/", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    found = next((row for row in d["items"] if row.get("token") == tok), None)
    assert found is not None
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_dashboard_revoke_sales_report(admin_headers):
    aid, tok = _seed_sales_report(admin_headers, client="TEST_DASH_REVOKE")
    # Verify public access works first
    r1 = requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=10)
    assert r1.status_code == 200
    # Revoke via dashboard endpoint
    r2 = requests.post(f"{BASE}/share-links/revoke", json={"type": "sales_report", "token": tok, "reason": "admin-test-revoke"}, headers=admin_headers, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["revoked_type"] == "sales_report"
    # Public now returns 410
    r3 = requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=10)
    assert r3.status_code == 410
    # Dashboard now shows status=revoked
    r4 = requests.get(f"{BASE}/share-links/?link_type=sales_report&status=revoked", headers=admin_headers, timeout=10)
    found = next((row for row in r4.json()["items"] if row.get("token") == tok), None)
    assert found is not None
    assert found["status"] == "revoked"
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_dashboard_revoke_unknown_token_404(admin_headers):
    r = requests.post(f"{BASE}/share-links/revoke", json={"type": "sales_report", "token": "DOESNOTEXIST", "reason": "x"}, headers=admin_headers, timeout=10)
    assert r.status_code == 404


def test_dashboard_revoke_invalid_type_400(admin_headers):
    r = requests.post(f"{BASE}/share-links/revoke", json={"type": "bogus_type", "token": "x"}, headers=admin_headers, timeout=10)
    assert r.status_code == 400


def test_dashboard_partner_blocked(admin_headers):
    """Only admin can view share-links dashboard."""
    r = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if r.status_code != 200:
        pytest.skip("partner@leamss.com not seeded")
    p_tok = r.json()["token"]
    r2 = requests.get(f"{BASE}/share-links/?link_type=sales_report", headers={"Authorization": f"Bearer {p_tok}"}, timeout=10)
    assert r2.status_code == 403
