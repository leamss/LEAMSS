"""Phase 21 — Portal Hub backend tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to internal (still uses /api prefix)
    BASE_URL = "http://localhost:8001"

ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=60,
    )
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    assert token, f"No token in response: {data}"
    return token


def test_portal_hub_stats_returns_5_keys(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/admin/portal-hub/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert r.status_code == 200, f"stats endpoint failed: {r.status_code} {r.text}"
    data = r.json()
    for k in ("employees", "hr", "marketing", "it", "me"):
        assert k in data, f"missing key {k} in stats response: {list(data.keys())}"


def test_portal_hub_stats_employees_shape(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/admin/portal-hub/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    data = r.json()
    emp = data["employees"]
    assert "active" in emp and "total" in emp
    assert isinstance(emp["active"], int)
    assert isinstance(emp["total"], int)


def test_portal_hub_stats_no_auth_returns_401(admin_token):
    r = requests.get(f"{BASE_URL}/api/admin/portal-hub/stats", timeout=15)
    assert r.status_code in (401, 403), f"unauth call should 401/403, got {r.status_code}"


def test_admin_portal_hub_legacy_no_route(admin_token):
    """The old /api/admin/portal-hub (no /stats) should not return a hub-page (it was frontend-only).
    Just ensure stats endpoint still works and that the frontend redirect is purely client-side.
    """
    # No backend route at /api/admin/portal-hub — should 404
    r = requests.get(
        f"{BASE_URL}/api/admin/portal-hub",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    # If a route accidentally matches /admin/portal-hub/{anything}, it would be 200 — ensure not.
    assert r.status_code in (404, 405), f"unexpected status {r.status_code} on bare hub path"
