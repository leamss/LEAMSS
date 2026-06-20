"""Option D / X5 — Admin Client-Portal Preview tests.

Validates: admin/CM/sales can preview · clients cannot · audit log written.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

API = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
if not API.endswith("/api"):
    API = API.rstrip("/") + "/api"

_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def seed_client():
    cid = f"x5_preview_{uuid.uuid4().hex[:8]}"
    pid = str(uuid.uuid4())
    sheet_id = str(uuid.uuid4())
    _db.client_mini_portals.insert_one({
        "id": pid, "client_id": cid,
        "client_email": f"x5.{cid}@test.example",
        "client_name": "X5 Preview Test",
        "product_id": "test_prod",
        "info_sheet_id": sheet_id,
        "temp_password": "X5TempPwd",
        "status": "active", "locked": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    _db.information_sheets.insert_one({
        "id": sheet_id, "entity_type": "client", "entity_id": cid,
        "client_id": cid,
        "personal": {"given_names": "X5", "family_name": "Preview"},
        "schema_version": 2, "status": "draft", "locked": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    yield {"client_id": cid, "portal_id": pid}
    _db.client_mini_portals.delete_one({"id": pid})
    _db.information_sheets.delete_one({"id": sheet_id})


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login",
                       json={"email": "admin@leamss.com", "password": "Admin@123"},
                       timeout=15)
    assert r.status_code == 200
    return r.json()["token"]


def _hdr(t): return {"Authorization": f"Bearer {t}"}


def test_x5_01_admin_can_preview_overview(admin_token, seed_client):
    r = requests.get(
        f"{API}/admin/client-portal-preview/{seed_client['client_id']}/overview",
        headers=_hdr(admin_token), timeout=10,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["_preview_mode"] is True
    assert d["_viewing_as"]["client_id"] == seed_client["client_id"]
    assert len(d["timeline"]) == 7


def test_x5_02_client_token_cannot_use_preview(seed_client):
    # Login as client first
    r = requests.post(f"{API}/client-auth/login", json={
        "email": f"x5.{seed_client['client_id']}@test.example",
        "password": "X5TempPwd",
    }, timeout=10)
    assert r.status_code == 200
    client_tok = r.json()["token"]
    # Try to use client token on admin endpoint
    r2 = requests.get(
        f"{API}/admin/client-portal-preview/{seed_client['client_id']}/overview",
        headers=_hdr(client_tok), timeout=10,
    )
    # Client tokens have user_type=client → no rbac_role, so get_current_user rejects them at the auth layer
    # If they slip through, the role check returns 403
    assert r2.status_code in (401, 403)


def test_x5_03_preview_writes_audit_log(admin_token, seed_client):
    before = _db.audit_logs.count_documents({
        "action": {"$regex": "^admin.client_portal_preview"}
    })
    requests.get(
        f"{API}/admin/client-portal-preview/{seed_client['client_id']}/info-sheet",
        headers=_hdr(admin_token), timeout=10,
    )
    requests.get(
        f"{API}/admin/client-portal-preview/{seed_client['client_id']}/documents",
        headers=_hdr(admin_token), timeout=10,
    )
    after = _db.audit_logs.count_documents({
        "action": {"$regex": "^admin.client_portal_preview"}
    })
    assert after >= before + 2  # at least 2 new audit entries
