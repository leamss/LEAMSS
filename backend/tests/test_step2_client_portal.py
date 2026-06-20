"""Step 2 — Client Portal E2E tests.

Covers W1 auth (login/forgot/reset/change), W2 overview, W4 documents,
W5 proposal accept/decline, security isolation from staff JWT.
"""
from __future__ import annotations

import io
import os
import pathlib
import secrets
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

# Auto-load env (test runner robustness)
if not os.environ.get("MONGO_URL"):
    envp = pathlib.Path("/app/backend/.env")
    if envp.exists():
        for line in envp.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

API = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
if not API.endswith("/api"):
    API = API.rstrip("/") + "/api"

_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def seed_client():
    """Create a dedicated test client portal + linked info sheet."""
    cid = f"step2_test_{uuid.uuid4().hex[:8]}"
    email = f"step2.{cid}@test.example"
    pwd = "TempPwd1234"
    pid = str(uuid.uuid4())
    sheet_id = str(uuid.uuid4())
    _db.client_mini_portals.insert_one({
        "id": pid, "client_id": cid,
        "client_email": email, "client_name": "Step2 Test Client",
        "client_phone": "+91 99999 99999",
        "product_id": "test_product",
        "info_sheet_id": sheet_id,
        "temp_password": pwd, "password_must_change": True,
        "status": "active", "locked": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    _db.information_sheets.insert_one({
        "id": sheet_id, "entity_type": "client", "entity_id": cid,
        "client_id": cid, "personal": {"email": email},
        "schema_version": 2, "status": "draft", "locked": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    yield {"client_id": cid, "email": email, "password": pwd, "portal_id": pid,
           "info_sheet_id": sheet_id}
    # cleanup
    _db.client_mini_portals.delete_one({"id": pid})
    _db.information_sheets.delete_one({"id": sheet_id})
    _db.client_documents.delete_many({"client_id": cid})
    _db.client_login_audit.delete_many({"email": email})


@pytest.fixture
def client_token(seed_client):
    r = requests.post(f"{API}/client-auth/login", json={
        "email": seed_client["email"], "password": seed_client["password"],
    }, timeout=10)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _hdr(t): return {"Authorization": f"Bearer {t}"}


# ─── W1 Auth ──────────────────────────────────────────────────────────────────
def test_step2_01_client_login_success(seed_client):
    r = requests.post(f"{API}/client-auth/login", json={
        "email": seed_client["email"], "password": seed_client["password"],
    }, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["token"]
    assert d["client"]["client_id"] == seed_client["client_id"]
    assert d["client"]["must_change_password"] is True


def test_step2_02_client_login_wrong_password(seed_client):
    r = requests.post(f"{API}/client-auth/login", json={
        "email": seed_client["email"], "password": "WRONG_PWD",
    }, timeout=10)
    assert r.status_code == 401


def test_step2_03_locked_client_cannot_login(seed_client):
    _db.client_mini_portals.update_one({"id": seed_client["portal_id"]},
                                         {"$set": {"locked": True}})
    try:
        r = requests.post(f"{API}/client-auth/login", json={
            "email": seed_client["email"], "password": seed_client["password"],
        }, timeout=10)
        assert r.status_code == 403
    finally:
        _db.client_mini_portals.update_one({"id": seed_client["portal_id"]},
                                             {"$set": {"locked": False}})


def test_step2_04_forgot_password_creates_reset_token(seed_client):
    r = requests.post(f"{API}/client-auth/forgot-password", json={
        "email": seed_client["email"],
    }, timeout=10)
    assert r.status_code == 200
    rt = _db.client_password_resets.find_one({"client_id": seed_client["client_id"], "used": False})
    assert rt is not None
    assert rt["token"]


def test_step2_05_reset_password_with_valid_token(seed_client):
    rt = _db.client_password_resets.find_one({"client_id": seed_client["client_id"], "used": False},
                                              sort=[("created_at", -1)])
    new_pwd = "NewStrong#9876"
    r = requests.post(f"{API}/client-auth/reset-password", json={
        "token": rt["token"], "new_password": new_pwd,
    }, timeout=10)
    assert r.status_code == 200
    # Login with new password
    r2 = requests.post(f"{API}/client-auth/login", json={
        "email": seed_client["email"], "password": new_pwd,
    }, timeout=10)
    assert r2.status_code == 200
    # Restore temp pwd for other tests
    from core.auth import get_password_hash
    _db.client_mini_portals.update_one(
        {"id": seed_client["portal_id"]},
        {"$set": {"password_hash": get_password_hash(seed_client["password"])}},
    )


def test_step2_06_staff_token_rejected_by_client_endpoints():
    # Get staff token
    sr = requests.post(f"{API}/auth/login", json={
        "email": "admin@leamss.com", "password": "Admin@123",
    }, timeout=15)
    assert sr.status_code == 200
    staff = sr.json()["token"]
    r = requests.get(f"{API}/client-portal/overview", headers=_hdr(staff), timeout=10)
    assert r.status_code == 403  # user_type != client


def test_step2_07_client_overview_returns_timeline(client_token):
    r = requests.get(f"{API}/client-portal/overview", headers=_hdr(client_token), timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert len(d["timeline"]) == 7
    assert d["timeline"][0]["stage"] == "Pre-Assessment Paid"


def test_step2_08_client_can_only_see_own_documents(client_token, seed_client):
    # Upload one doc
    fd = {"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")}
    data = {"document_type": "identity", "document_name": "Test ID"}
    r = requests.post(f"{API}/client-portal/documents",
                       headers=_hdr(client_token), files=fd, data=data, timeout=15)
    assert r.status_code == 200, r.text

    # Insert a doc for another client
    other = f"other_{uuid.uuid4().hex[:6]}"
    _db.client_documents.insert_one({
        "id": str(uuid.uuid4()), "client_id": other, "document_type": "identity",
        "document_name": "OTHER", "file_size_bytes": 100,
        "uploaded_at": datetime.now(timezone.utc), "status": "uploaded",
    })

    r2 = requests.get(f"{API}/client-portal/documents", headers=_hdr(client_token), timeout=10)
    assert r2.status_code == 200
    docs = r2.json()["documents"]
    assert all(d["client_id"] == seed_client["client_id"] for d in docs)
    assert any(d["document_name"] == "Test ID" for d in docs)
    assert not any(d["document_name"] == "OTHER" for d in docs)
    _db.client_documents.delete_many({"client_id": other})


def test_step2_09_document_upload_rejects_bad_mime(client_token):
    fd = {"file": ("evil.exe", b"binary", "application/x-msdownload")}
    data = {"document_type": "identity"}
    r = requests.post(f"{API}/client-portal/documents",
                       headers=_hdr(client_token), files=fd, data=data, timeout=10)
    assert r.status_code == 400


def test_step2_10_client_accept_proposal(client_token, seed_client):
    # Seed a proposal
    pid = str(uuid.uuid4())
    _db.proposals.insert_one({
        "id": pid, "client_id": seed_client["client_id"],
        "status": "sent", "product_name": "Test Product",
        "country": "AU", "service_type": "190",
        "base_fees_inr": 100000, "addon_total_inr": 0,
        "coupon_total_inr": 0, "admin_discount_inr": 0,
        "subtotal_inr": 100000, "gst_inr": 18000, "total_inr": 118000,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc),
    })
    try:
        r = requests.post(f"{API}/client-portal/proposal/{pid}/accept",
                          headers=_hdr(client_token), json={}, timeout=10)
        assert r.status_code == 200, r.text
        p = _db.proposals.find_one({"id": pid})
        assert p["status"] == "accepted"
        assert p["accepted_by"] == "client_self"
    finally:
        _db.proposals.delete_one({"id": pid})


def test_step2_11_client_change_password(client_token, seed_client):
    new_pwd = "Another$Strong9"
    r = requests.post(f"{API}/client-auth/change-password",
                       headers=_hdr(client_token), json={
                           "current_password": seed_client["password"],
                           "new_password": new_pwd,
                       }, timeout=10)
    assert r.status_code == 200, r.text
    # Login with new password
    r2 = requests.post(f"{API}/client-auth/login", json={
        "email": seed_client["email"], "password": new_pwd,
    }, timeout=10)
    assert r2.status_code == 200
    # Restore for cleanup
    from core.auth import get_password_hash
    _db.client_mini_portals.update_one(
        {"id": seed_client["portal_id"]},
        {"$set": {"password_hash": get_password_hash(seed_client["password"]),
                  "password_must_change": True}},
    )


def test_step2_12_login_audit_recorded(seed_client):
    requests.post(f"{API}/client-auth/login", json={
        "email": seed_client["email"], "password": "BAD",
    }, timeout=10)
    requests.post(f"{API}/client-auth/login", json={
        "email": seed_client["email"], "password": seed_client["password"],
    }, timeout=10)
    audits = list(_db.client_login_audit.find({"email": seed_client["email"]}))
    assert len(audits) >= 2
    statuses = {a["status"] for a in audits}
    assert "bad_password" in statuses
    assert "ok" in statuses
