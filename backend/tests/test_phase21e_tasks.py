"""Phase 21.E — Tasks (Kanban) backend tests."""
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


@pytest.fixture(scope="module")
def admin_user_id(admin_token):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    return r.json()["id"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_create_task_assigned_to_self(admin_token, admin_user_id):
    r = requests.post(
        f"{BASE_URL}/api/tasks",
        json={
            "title": "Pytest task 1",
            "description": "Created by phase21e pytest",
            "assignee_id": admin_user_id,
            "priority": "medium",
            "status": "todo",
            "tags": ["pytest"],
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["title"] == "Pytest task 1"
    assert d["status"] == "todo"
    assert d["priority"] == "medium"


def test_list_tasks_includes_created(admin_token):
    r = requests.get(f"{BASE_URL}/api/tasks?assignee_id=me", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert any(t.get("title", "").startswith("Pytest task") for t in items)


def test_update_task_status_in_progress(admin_token, admin_user_id):
    # Create then update
    c = requests.post(
        f"{BASE_URL}/api/tasks",
        json={"title": "Pytest move", "assignee_id": admin_user_id, "priority": "high", "status": "todo"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    task_id = c["id"]
    r = requests.patch(
        f"{BASE_URL}/api/tasks/{task_id}",
        json={"status": "in_progress"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json().get("started_at") is not None


def test_invalid_status_returns_400(admin_token, admin_user_id):
    c = requests.post(
        f"{BASE_URL}/api/tasks",
        json={"title": "Pytest invalid", "assignee_id": admin_user_id},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.patch(
        f"{BASE_URL}/api/tasks/{c['id']}",
        json={"status": "invalid_state"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 400


def test_add_comment(admin_token, admin_user_id):
    c = requests.post(
        f"{BASE_URL}/api/tasks",
        json={"title": "Pytest comment", "assignee_id": admin_user_id},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.post(
        f"{BASE_URL}/api/tasks/{c['id']}/comments",
        json={"text": "First comment from pytest"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert "comment" in r.json()


def test_filter_by_priority(admin_token):
    r = requests.get(f"{BASE_URL}/api/tasks?priority=urgent", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    items = r.json()
    for t in items:
        assert t.get("priority") == "urgent"


def test_archive_task(admin_token, admin_user_id):
    c = requests.post(
        f"{BASE_URL}/api/tasks",
        json={"title": "Pytest archive", "assignee_id": admin_user_id},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.delete(f"{BASE_URL}/api/tasks/{c['id']}", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    # Should not appear in non-archived list
    listed = requests.get(f"{BASE_URL}/api/tasks", headers=_auth(admin_token), timeout=15).json()
    assert not any(t["id"] == c["id"] for t in listed)
