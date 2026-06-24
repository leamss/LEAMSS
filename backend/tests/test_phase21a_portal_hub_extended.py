"""Phase 21.A — Portal Hub extended backend tests (Day 0 backfill)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")

ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200
    return r.json()["token"]


def test_hub_stats_employees_active_positive(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/admin/portal-hub/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    data = r.json()
    assert data["employees"]["active"] >= 1, "Should have at least 1 active employee"


def test_hub_stats_hr_keys_present(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/admin/portal-hub/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    hr = r.json()["hr"]
    for k in ("pending_leaves", "pending_regularizations", "active_policies"):
        assert k in hr, f"missing HR key {k}"
        assert isinstance(hr[k], int)


def test_hub_stats_marketing_keys(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/admin/portal-hub/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    mk = r.json()["marketing"]
    for k in ("active_campaigns", "draft_campaigns", "open_leads"):
        assert k in mk


def test_hub_stats_me_includes_unread_announcements(admin_token):
    """Day-0 regression test for the bug where 'unread_announcements' was computed but not returned."""
    r = requests.get(
        f"{BASE_URL}/api/admin/portal-hub/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    me = r.json()["me"]
    assert "my_tasks" in me
    assert "my_pending_leaves" in me
    assert "unread_announcements" in me, "fix applied — must include unread_announcements"
    assert isinstance(me["unread_announcements"], int)


def test_hub_stats_response_cached(admin_token):
    """Two consecutive calls should return identical numbers (60s cache)."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    r1 = requests.get(f"{BASE_URL}/api/admin/portal-hub/stats", headers=headers, timeout=15).json()
    r2 = requests.get(f"{BASE_URL}/api/admin/portal-hub/stats", headers=headers, timeout=15).json()
    assert r1 == r2, "Cache should make consecutive responses identical"
