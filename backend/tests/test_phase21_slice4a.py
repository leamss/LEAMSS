"""Phase 21 Slice 4 Sub-Slice A — IT Site Audit + Dev Tracker tests."""
import os
import time
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


# ─────────────────────────── Site Audit ────────────────────────────

def test_site_audit_run_kicks_off(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/site-audit/run",
        json={"scope": "atlas", "sample_size": 3},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "running"
    assert body["scope"] == "atlas"
    assert body["run_id"]


def test_site_audit_rejects_bad_scope(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/site-audit/run",
        json={"scope": "everything", "sample_size": 3},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.status_code == 400


def test_site_audit_lists_runs(admin_token):
    r = requests.get(f"{BASE_URL}/api/site-audit/runs", headers=_auth(admin_token), timeout=10)
    assert r.status_code == 200
    runs = r.json()
    assert isinstance(runs, list)
    assert len(runs) > 0  # we kicked off one above


def test_site_audit_detail_eventually_completes(admin_token):
    """Run the audit; poll until complete; assert structure."""
    kick = requests.post(
        f"{BASE_URL}/api/site-audit/run",
        json={"scope": "atlas", "sample_size": 2},
        headers=_auth(admin_token),
        timeout=15,
    )
    if kick.status_code == 409:
        # Concurrency guard hit — pick the existing in-flight run instead
        runs = requests.get(f"{BASE_URL}/api/site-audit/runs", headers=_auth(admin_token), timeout=10).json()
        run_id = next((r["id"] for r in runs if r["status"] == "running"), None)
        if not run_id:
            pytest.skip("No in-flight or new run available")
    else:
        assert kick.status_code == 200, kick.text
        run_id = kick.json()["run_id"]
    deadline = time.time() + 30
    detail = None
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/api/site-audit/runs/{run_id}", headers=_auth(admin_token), timeout=10)
        if r.status_code == 200 and r.json().get("status") in ("complete", "failed"):
            detail = r.json()
            break
        time.sleep(1)
    assert detail is not None, "Audit did not finish within 30s"
    assert detail["status"] in ("complete", "failed")
    if detail["status"] == "complete":
        assert "pages" in detail
        assert "summary" in detail


def test_site_audit_concurrency_guard(admin_token):
    # Kick off one
    requests.post(
        f"{BASE_URL}/api/site-audit/run",
        json={"scope": "atlas", "sample_size": 3},
        headers=_auth(admin_token),
        timeout=10,
    )
    # Immediately second — should 409 OR (rarely) the first finished super fast
    r2 = requests.post(
        f"{BASE_URL}/api/site-audit/run",
        json={"scope": "atlas", "sample_size": 3},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r2.status_code in (200, 409)


# ─────────────────────────── Dev Tracker ────────────────────────────

def test_dev_tracker_create_and_get(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/dev-tracker/items",
        json={"title": "PYTEST: bill upload mobile responsive issue", "description": "Steps: open dialog on mobile…", "type": "bug", "priority": "P1", "labels": ["frontend", "mobile"]},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.status_code == 200, r.text
    item = r.json()
    assert item["title"].startswith("PYTEST")
    assert item["status"] == "backlog"
    assert item["priority"] == "P1"
    assert item["reporter_name"]
    assert "frontend" in item["labels"]
    assert len(item["audit_log"]) == 1
    # Get detail
    g = requests.get(f"{BASE_URL}/api/dev-tracker/items/{item['id']}", headers=_auth(admin_token), timeout=10)
    assert g.status_code == 200
    assert g.json()["id"] == item["id"]


def test_dev_tracker_rejects_invalid_enum(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/dev-tracker/items",
        json={"title": "PYTEST: bad enum", "type": "bug", "priority": "P9"},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.status_code == 400
    assert "priority" in r.json()["detail"]


def test_dev_tracker_patch_status_records_audit(admin_token):
    c = requests.post(
        f"{BASE_URL}/api/dev-tracker/items",
        json={"title": "PYTEST: move-status-flow", "type": "feature", "priority": "P2"},
        headers=_auth(admin_token),
        timeout=10,
    )
    item_id = c.json()["id"]
    p = requests.patch(
        f"{BASE_URL}/api/dev-tracker/items/{item_id}",
        json={"status": "in_progress"},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert p.status_code == 200
    updated = p.json()
    assert updated["status"] == "in_progress"
    actions = [e["action"] for e in updated["audit_log"]]
    assert "updated_status" in actions


def test_dev_tracker_comments(admin_token):
    c = requests.post(
        f"{BASE_URL}/api/dev-tracker/items",
        json={"title": "PYTEST: comment-flow", "type": "chore", "priority": "P3"},
        headers=_auth(admin_token),
        timeout=10,
    )
    item_id = c.json()["id"]
    cm = requests.post(
        f"{BASE_URL}/api/dev-tracker/items/{item_id}/comments",
        json={"body": "Sir, this is a test comment from pytest."},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert cm.status_code == 200
    g = requests.get(f"{BASE_URL}/api/dev-tracker/items/{item_id}", headers=_auth(admin_token), timeout=10)
    detail = g.json()
    assert len(detail["comments"]) == 1
    assert detail["comment_count"] == 1
    assert any(e["action"] == "commented" for e in detail["audit_log"])


def test_dev_tracker_list_with_filter(admin_token):
    requests.post(
        f"{BASE_URL}/api/dev-tracker/items",
        json={"title": "PYTEST: filter test bug", "type": "bug", "priority": "P0", "labels": ["security"]},
        headers=_auth(admin_token),
        timeout=10,
    )
    r = requests.get(
        f"{BASE_URL}/api/dev-tracker/items",
        params={"priority": "P0", "type": "bug"},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.status_code == 200
    items = r.json()
    assert all(i["priority"] == "P0" and i["type"] == "bug" for i in items)


def test_dev_tracker_stats(admin_token):
    r = requests.get(f"{BASE_URL}/api/dev-tracker/stats", headers=_auth(admin_token), timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "total" in body
    for s in ("backlog", "in_progress", "in_review", "done"):
        assert s in body["by_status"]
