"""Option 2 / Y4 — Public Proposal Link E2E tests.

Covers Y1 endpoints: generate · view · accept · decline · revoke · pdf.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta

import jwt
import pytest
import requests
from pymongo import MongoClient

API = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
if not API.endswith("/api"):
    API = API.rstrip("/") + "/api"

_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login",
                       json={"email": "admin@leamss.com", "password": "Admin@123"},
                       timeout=15)
    return r.json()["token"]


@pytest.fixture(scope="module")
def seed_proposal():
    """Insert a sent proposal for testing."""
    pid = str(uuid.uuid4())
    cid = f"y4_pub_{uuid.uuid4().hex[:8]}"
    _db.proposals.insert_one({
        "id": pid, "client_id": cid,
        "client_email": f"{cid}@test.example",
        "status": "sent", "product_name": "Y4 Test Product",
        "country": "AU", "service_type": "190",
        "base_fees_inr": 150000, "addon_total_inr": 25000,
        "coupon_total_inr": 15000, "admin_discount_inr": 5000,
        "subtotal_inr": 155000, "gst_inr": 27900, "total_inr": 182900,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=14),
    })
    yield {"id": pid, "client_id": cid}
    _db.proposals.delete_one({"id": pid})
    _db.proposal_link_denylist.delete_many({"proposal_id": pid})


def _hdr(t): return {"Authorization": f"Bearer {t}"}


def test_y4_01_generate_public_link_returns_signed_token(admin_token, seed_proposal):
    r = requests.post(f"{API}/proposals/{seed_proposal['id']}/generate-public-link",
                       headers=_hdr(admin_token), timeout=10)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    assert "public_url" in d
    assert "t=" in d["public_url"]
    assert d["token_id"]
    # Persisted on proposal
    p = _db.proposals.find_one({"id": seed_proposal["id"]})
    assert p["active_public_token_id"] == d["token_id"]


def test_y4_02_public_view_returns_proposal_no_auth(admin_token, seed_proposal):
    # Get fresh token
    r1 = requests.post(f"{API}/proposals/{seed_proposal['id']}/generate-public-link",
                        headers=_hdr(admin_token), timeout=10)
    tok = r1.json()["public_url"].split("t=")[-1]

    # Public view WITHOUT auth header
    r = requests.get(f"{API}/proposals/public/view?t={tok}", timeout=10)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["_public_view"] is True
    assert d["proposal"]["id"] == seed_proposal["id"]
    assert d["proposal"]["total_inr"] == 182900


def test_y4_03_expired_token_rejected(seed_proposal):
    """Manually sign an already-expired token to test expiry validation."""
    from routers.proposals_public import PROPOSAL_LINK_SECRET
    payload = {
        "purpose": "proposal_view",
        "proposal_id": seed_proposal["id"],
        "client_id": seed_proposal["client_id"],
        "nonce": "deadbeef", "token_id": "expired_test",
        "iat": int((datetime.now(timezone.utc) - timedelta(days=40)).timestamp()),
        "exp": datetime.now(timezone.utc) - timedelta(days=10),  # ALREADY EXPIRED
    }
    tok = jwt.encode(payload, PROPOSAL_LINK_SECRET, algorithm="HS256")
    r = requests.get(f"{API}/proposals/public/view?t={tok}", timeout=10)
    assert r.status_code == 401
    assert "expired" in (r.json().get("detail", "")).lower()


def test_y4_04_revoked_token_rejected(admin_token, seed_proposal):
    r1 = requests.post(f"{API}/proposals/{seed_proposal['id']}/generate-public-link",
                        headers=_hdr(admin_token), timeout=10)
    tok = r1.json()["public_url"].split("t=")[-1]
    tok_id = r1.json()["token_id"]

    # Revoke it
    rv = requests.post(f"{API}/proposals/{seed_proposal['id']}/revoke-public-link?token_id={tok_id}",
                        headers=_hdr(admin_token), timeout=10)
    assert rv.status_code == 200

    # Now public view should fail
    r = requests.get(f"{API}/proposals/public/view?t={tok}", timeout=10)
    assert r.status_code == 401
    assert "revoked" in (r.json().get("detail", "")).lower()


def test_y4_05_public_accept_transitions_status(admin_token, seed_proposal):
    # Need a fresh sent proposal because previous tests may have mutated it
    fresh_id = str(uuid.uuid4())
    fresh_cid = f"y4_accept_{uuid.uuid4().hex[:6]}"
    _db.proposals.insert_one({
        "id": fresh_id, "client_id": fresh_cid,
        "status": "sent", "product_name": "Accept Test",
        "country": "AU", "service_type": "190",
        "base_fees_inr": 100000, "addon_total_inr": 0,
        "coupon_total_inr": 0, "admin_discount_inr": 0,
        "subtotal_inr": 100000, "gst_inr": 18000, "total_inr": 118000,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=14),
    })
    try:
        r1 = requests.post(f"{API}/proposals/{fresh_id}/generate-public-link",
                           headers=_hdr(admin_token), timeout=10)
        tok = r1.json()["public_url"].split("t=")[-1]

        # Accept publicly (no auth)
        r = requests.post(f"{API}/proposals/public/accept?t={tok}", timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True and d.get("status") == "accepted"

        # Verify DB state
        p = _db.proposals.find_one({"id": fresh_id})
        assert p["status"] == "accepted"
        assert p["accepted_via"] == "public_link"
        assert p["accepted_token_id"]
    finally:
        _db.proposals.delete_one({"id": fresh_id})
