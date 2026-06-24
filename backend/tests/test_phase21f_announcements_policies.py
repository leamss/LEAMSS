"""Phase 21.F — Announcements + Internal Policies backend tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@leamss.com", "password": "Admin@123"},
        timeout=30,
    )
    return r.json()["token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


# ─────────── ANNOUNCEMENTS ───────────

def test_create_and_list_announcement(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/announcements",
        json={
            "title": "Pytest announcement",
            "content": "From phase21f tests",
            "priority": "info",
            "target_audience": "all",
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    ann_id = r.json()["id"]
    listed = requests.get(f"{BASE_URL}/api/announcements", headers=_auth(admin_token), timeout=15).json()
    assert any(a["id"] == ann_id for a in listed)


def test_invalid_priority_returns_400(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/announcements",
        json={"title": "bad", "content": "bad", "priority": "nonsense", "target_audience": "all"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 400


def test_mark_announcement_read(admin_token):
    create = requests.post(
        f"{BASE_URL}/api/announcements",
        json={"title": "Pytest read", "content": "Read me", "priority": "info", "target_audience": "all"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.patch(
        f"{BASE_URL}/api/announcements/{create['id']}/mark-read",
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["read_count"] >= 1


def test_for_true_filter_audience(admin_token):
    """When for=true, audience matching should apply (all=ok for admin too)."""
    r = requests.get(f"{BASE_URL}/api/announcements?for=true", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ─────────── POLICIES ───────────

def test_create_policy(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/internal-policies",
        json={
            "title": "Pytest policy",
            "category": "HR",
            "content": "Test content",
            "requires_acknowledgment": True,
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["category"] == "HR"
    assert data["version"] == 1
    assert data["acknowledgment_count"] == 0


def test_acknowledge_policy_creates_signature(admin_token):
    create = requests.post(
        f"{BASE_URL}/api/internal-policies",
        json={"title": "Pytest ack", "category": "HR", "content": "Ack test", "requires_acknowledgment": True},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.post(
        f"{BASE_URL}/api/internal-policies/{create['id']}/acknowledge",
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert "signature_hash" in r.json()


def test_supersede_policy_with_new_version(admin_token):
    create = requests.post(
        f"{BASE_URL}/api/internal-policies",
        json={"title": "Pytest supersede", "category": "HR", "content": "v1"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    old_id = create["id"]
    r = requests.post(
        f"{BASE_URL}/api/internal-policies/{old_id}/new-version",
        json={"title": "Pytest supersede", "category": "HR", "content": "v2"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert r.json().get("supersedes") == old_id


def test_invalid_category_returns_400(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/internal-policies",
        json={"title": "bad cat", "category": "WeirdCat", "content": "x"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 400
