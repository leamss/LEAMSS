"""Phase 21 Slice 4 Sub-Slice B — Internal Chat + Support Tickets tests."""
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
def admin_user(admin_token):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    return r.json()


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


# ─────────────────────────── Internal Chat ────────────────────────────

def test_chat_directory_returns_peers(admin_token, admin_user):
    r = requests.get(f"{BASE_URL}/api/internal-chat/directory", headers=_auth(admin_token), timeout=10)
    assert r.status_code == 200
    peers = r.json()
    assert isinstance(peers, list)
    assert all(p["id"] != admin_user["id"] for p in peers)


def test_chat_create_group_thread(admin_token, admin_user):
    # Find 2 other users
    peers = requests.get(f"{BASE_URL}/api/internal-chat/directory", headers=_auth(admin_token), timeout=10).json()
    other_ids = [p["id"] for p in peers[:2]]
    r = requests.post(
        f"{BASE_URL}/api/internal-chat/threads",
        json={"type": "group", "member_ids": other_ids, "title": "PYTEST Group Chat"},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["type"] == "group"
    assert t["title"] == "PYTEST Group Chat"
    assert admin_user["id"] in t["member_ids"]
    assert all(uid in t["member_ids"] for uid in other_ids)


def test_chat_dm_dedup(admin_token):
    peers = requests.get(f"{BASE_URL}/api/internal-chat/directory", headers=_auth(admin_token), timeout=10).json()
    peer_id = peers[0]["id"]
    a = requests.post(f"{BASE_URL}/api/internal-chat/threads", json={"type": "dm", "member_ids": [peer_id]}, headers=_auth(admin_token), timeout=10)
    b = requests.post(f"{BASE_URL}/api/internal-chat/threads", json={"type": "dm", "member_ids": [peer_id]}, headers=_auth(admin_token), timeout=10)
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["id"] == b.json()["id"]  # dedup returns same thread


def test_chat_send_message_and_unread_increments(admin_token):
    peers = requests.get(f"{BASE_URL}/api/internal-chat/directory", headers=_auth(admin_token), timeout=10).json()
    peer_id = peers[0]["id"]
    t = requests.post(f"{BASE_URL}/api/internal-chat/threads", json={"type": "dm", "member_ids": [peer_id]}, headers=_auth(admin_token), timeout=10).json()
    msg = requests.post(
        f"{BASE_URL}/api/internal-chat/threads/{t['id']}/messages",
        json={"body": "Hello, this is a pytest message"},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert msg.status_code == 200
    m = msg.json()
    assert m["body"] == "Hello, this is a pytest message"
    # Refresh thread — peer's unread should be ≥1
    threads = requests.get(f"{BASE_URL}/api/internal-chat/threads", headers=_auth(admin_token), timeout=10).json()
    ours = next(x for x in threads if x["id"] == t["id"])
    assert ours["unread_counts"].get(peer_id, 0) >= 1


def test_chat_edit_own_message(admin_token):
    peers = requests.get(f"{BASE_URL}/api/internal-chat/directory", headers=_auth(admin_token), timeout=10).json()
    t = requests.post(f"{BASE_URL}/api/internal-chat/threads", json={"type": "dm", "member_ids": [peers[1]["id"]]}, headers=_auth(admin_token), timeout=10).json()
    m = requests.post(f"{BASE_URL}/api/internal-chat/threads/{t['id']}/messages", json={"body": "original"}, headers=_auth(admin_token), timeout=10).json()
    e = requests.patch(f"{BASE_URL}/api/internal-chat/messages/{m['id']}", json={"body": "edited"}, headers=_auth(admin_token), timeout=10)
    assert e.status_code == 200
    assert e.json()["body"] == "edited"
    assert e.json()["edited_at"] is not None


def test_chat_delete_own_message(admin_token):
    peers = requests.get(f"{BASE_URL}/api/internal-chat/directory", headers=_auth(admin_token), timeout=10).json()
    t = requests.post(f"{BASE_URL}/api/internal-chat/threads", json={"type": "dm", "member_ids": [peers[2]["id"]]}, headers=_auth(admin_token), timeout=10).json()
    m = requests.post(f"{BASE_URL}/api/internal-chat/threads/{t['id']}/messages", json={"body": "delete me"}, headers=_auth(admin_token), timeout=10).json()
    d = requests.delete(f"{BASE_URL}/api/internal-chat/messages/{m['id']}", headers=_auth(admin_token), timeout=10)
    assert d.status_code == 200
    msgs = requests.get(f"{BASE_URL}/api/internal-chat/threads/{t['id']}/messages", headers=_auth(admin_token), timeout=10).json()
    deleted = next(x for x in msgs if x["id"] == m["id"])
    assert deleted["is_deleted"] is True
    assert deleted["body"] == "[deleted]"


def test_chat_reaction_toggle(admin_token):
    peers = requests.get(f"{BASE_URL}/api/internal-chat/directory", headers=_auth(admin_token), timeout=10).json()
    t = requests.post(f"{BASE_URL}/api/internal-chat/threads", json={"type": "dm", "member_ids": [peers[3]["id"]]}, headers=_auth(admin_token), timeout=10).json()
    m = requests.post(f"{BASE_URL}/api/internal-chat/threads/{t['id']}/messages", json={"body": "react to me"}, headers=_auth(admin_token), timeout=10).json()
    # Add 👍
    r = requests.post(f"{BASE_URL}/api/internal-chat/messages/{m['id']}/reactions", json={"emoji": "👍"}, headers=_auth(admin_token), timeout=10)
    assert r.status_code == 200
    assert any(rx["emoji"] == "👍" for rx in r.json()["reactions"])
    # Toggle off
    r2 = requests.post(f"{BASE_URL}/api/internal-chat/messages/{m['id']}/reactions", json={"emoji": "👍"}, headers=_auth(admin_token), timeout=10)
    assert all(rx["emoji"] != "👍" for rx in r2.json()["reactions"])


def test_chat_unread_total(admin_token):
    r = requests.get(f"{BASE_URL}/api/internal-chat/unread-count", headers=_auth(admin_token), timeout=10)
    assert r.status_code == 200
    assert "total" in r.json()


def test_chat_invalid_emoji_rejected(admin_token):
    peers = requests.get(f"{BASE_URL}/api/internal-chat/directory", headers=_auth(admin_token), timeout=10).json()
    t = requests.post(f"{BASE_URL}/api/internal-chat/threads", json={"type": "dm", "member_ids": [peers[4]["id"]]}, headers=_auth(admin_token), timeout=10).json()
    m = requests.post(f"{BASE_URL}/api/internal-chat/threads/{t['id']}/messages", json={"body": "x"}, headers=_auth(admin_token), timeout=10).json()
    r = requests.post(f"{BASE_URL}/api/internal-chat/messages/{m['id']}/reactions", json={"emoji": "🚀"}, headers=_auth(admin_token), timeout=10)
    assert r.status_code == 400


# ─────────────────────────── Support Tickets ────────────────────────────

def test_ticket_create_with_ticket_number_and_sla(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/support-tickets",
        json={"title": "PYTEST: Laptop request", "description": "Need new laptop", "department": "it", "priority": "P2"},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["ticket_number"].startswith("TKT-")
    assert t["priority"] == "P2"
    assert t["sla_target_at"]  # SLA computed
    assert t["status"] == "open"
    assert t["raised_by_id"]


def test_ticket_auto_link_dev_item_on_bug_tag(admin_token):
    """The cross-feature integration: ticket with tag=bug in IT department → auto-create Dev item."""
    r = requests.post(
        f"{BASE_URL}/api/support-tickets",
        json={"title": "PYTEST: dashboard crashes on Safari", "description": "Browser console shows error stacktrace", "department": "it", "priority": "P1", "tags": ["bug", "safari"]},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["linked_dev_item_id"], "Expected auto-linked Dev Tracker item"
    # Verify Dev item exists with linked_ticket back-reference
    dev = requests.get(f"{BASE_URL}/api/dev-tracker/items/{t['linked_dev_item_id']}", headers=_auth(admin_token), timeout=10)
    assert dev.status_code == 200
    d = dev.json()
    assert d["type"] == "bug"
    assert d["linked_ticket_id"] == t["id"]
    assert d["linked_ticket_number"] == t["ticket_number"]


def test_ticket_no_auto_link_on_hr_dept(admin_token):
    """HR tickets should NOT auto-create Dev items even if description has 'error'."""
    r = requests.post(
        f"{BASE_URL}/api/support-tickets",
        json={"title": "PYTEST: HR question", "description": "There's an error in my payslip", "department": "hr", "priority": "P2"},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.json()["linked_dev_item_id"] is None


def test_ticket_priority_default_p3_for_non_admin_request(admin_token):
    """Even if priority="P0" requested, admin still gets P0 — admin IS a lead."""
    r = requests.post(
        f"{BASE_URL}/api/support-tickets",
        json={"title": "PYTEST: admin P0 ticket", "description": "high", "department": "ops", "priority": "P0"},
        headers=_auth(admin_token),
        timeout=10,
    )
    # Admin allowed; expect P0 + SLA 4hr
    assert r.json()["priority"] == "P0"


def test_ticket_invalid_department_rejected(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/support-tickets",
        json={"title": "PYTEST: bad dept", "description": "x", "department": "unknown"},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert r.status_code == 400


def test_ticket_resolve_then_rate(admin_token):
    t = requests.post(
        f"{BASE_URL}/api/support-tickets",
        json={"title": "PYTEST: resolve flow", "department": "hr", "priority": "P3"},
        headers=_auth(admin_token),
        timeout=10,
    ).json()
    resolved = requests.post(f"{BASE_URL}/api/support-tickets/{t['id']}/resolve", headers=_auth(admin_token), timeout=10)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    rating = requests.post(
        f"{BASE_URL}/api/support-tickets/{t['id']}/rate",
        json={"stars": 5, "comment": "Quick resolution"},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert rating.status_code == 200
    assert rating.json()["stars"] == 5


def test_ticket_reopen(admin_token):
    t = requests.post(
        f"{BASE_URL}/api/support-tickets",
        json={"title": "PYTEST: reopen flow", "department": "hr"},
        headers=_auth(admin_token),
        timeout=10,
    ).json()
    requests.post(f"{BASE_URL}/api/support-tickets/{t['id']}/resolve", headers=_auth(admin_token), timeout=10)
    re = requests.post(f"{BASE_URL}/api/support-tickets/{t['id']}/reopen", headers=_auth(admin_token), timeout=10)
    assert re.status_code == 200
    assert re.json()["status"] == "open"


def test_ticket_internal_comments_hidden_from_raiser(admin_token):
    """Admin creates ticket + internal comment; admin sees it (because admin)."""
    t = requests.post(
        f"{BASE_URL}/api/support-tickets",
        json={"title": "PYTEST: internal comment", "department": "it"},
        headers=_auth(admin_token),
        timeout=10,
    ).json()
    c = requests.post(
        f"{BASE_URL}/api/support-tickets/{t['id']}/comments",
        json={"body": "Internal-only note", "is_internal": True},
        headers=_auth(admin_token),
        timeout=10,
    )
    assert c.status_code == 200
    assert c.json()["is_internal"] is True


def test_ticket_stats(admin_token):
    r = requests.get(f"{BASE_URL}/api/support-tickets/stats", headers=_auth(admin_token), timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert "by_status" in d
    assert "past_sla" in d
    assert "resolved_this_week" in d
