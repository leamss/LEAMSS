"""Phase 20.2 — Product Master upgrade tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


API_BASE = os.environ.get("API_BASE") or "http://localhost:8001"
API = f"{API_BASE}/api"
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"


@pytest.fixture(scope="module")
def headers():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def db():
    mongo_url = Path("/app/backend/.env").read_text().split("MONGO_URL=")[1].split()[0]
    db_name = Path("/app/backend/.env").read_text().split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


def test_202_existing_products_preserved(db):
    """Migration must NOT delete any existing product."""
    total = db["products"].count_documents({})
    assert total >= 19, f"Expected at least 19 products (pre-migration), got {total}"


def test_202_new_fields_default_correctly(db):
    """Every product must have the new Phase 20.2 fields with sensible defaults."""
    required_fields = [
        "is_pre_assessment", "pre_assessment_fee_inr", "pre_assessment_fee_currency",
        "workflow_id", "workflow_steps_count",
        "visa_subclass", "assessing_body_code",
        "commissions_v2", "archived_at", "archived_by", "archived_reason",
    ]
    sample = db["products"].find_one({"archived_at": None})
    assert sample is not None
    for f in required_fields:
        assert f in sample, f"Missing field: {f}"
    assert sample["is_pre_assessment"] is False
    assert sample["pre_assessment_fee_currency"] == "INR"


def test_202_test_products_soft_deleted(db):
    """All TEST_ products must be archived (not deleted)."""
    archived = db["products"].count_documents({"archived_at": {"$ne": None}})
    assert archived >= 9, f"Expected >=9 archived TEST_ products, got {archived}"
    # Verify none have hard-deleted (still exist)
    test_count = db["products"].count_documents({"name": {"$regex": "TEST_"}})
    assert test_count >= 9


def test_202_archived_excluded_by_default(headers):
    """GET /products without include_archived should exclude archived ones."""
    r = requests.get(f"{API}/products", headers=headers, timeout=10)
    assert r.status_code == 200
    items = r.json()
    for p in items:
        assert not p.get("archived_at"), f"Archived product leaked: {p.get('name')}"


def test_202_archived_included_when_requested(headers):
    r = requests.get(f"{API}/products?include_archived=true", headers=headers, timeout=10)
    assert r.status_code == 200
    items = r.json()
    arch = [p for p in items if p.get("archived_at")]
    assert len(arch) >= 9


def test_202_filter_by_category(headers):
    r = requests.get(f"{API}/products?category=pr", headers=headers, timeout=10)
    assert r.status_code == 200
    items = r.json()
    # All returned must be PR category
    for p in items:
        assert p.get("category") == "pr" or p.get("_category_v2") == "pr"


def test_202_filter_by_is_pre_assessment(headers):
    """Filter PA-flow products only."""
    # First set one to PA
    r0 = requests.get(f"{API}/products", headers=headers, timeout=10)
    pid = next((p["id"] for p in r0.json() if p["name"] == "Student Visa"), None)
    if pid:
        requests.put(f"{API}/products/{pid}", headers=headers,
                     json={"is_pre_assessment": True}, timeout=10)
        r = requests.get(f"{API}/products?is_pre_assessment=true", headers=headers, timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert all(p.get("is_pre_assessment") is True for p in items)
        # Cleanup
        requests.put(f"{API}/products/{pid}", headers=headers,
                     json={"is_pre_assessment": False}, timeout=10)


def test_202_archive_validates_reason(headers):
    """Archive endpoint requires reason."""
    r0 = requests.get(f"{API}/products", headers=headers, timeout=10)
    pid = r0.json()[0]["id"]
    r = requests.post(f"{API}/products/{pid}/archive", headers=headers, json={}, timeout=10)
    assert r.status_code in (400, 422)


def test_202_restore_archived_works(headers):
    """End-to-end archive → restore."""
    r0 = requests.get(f"{API}/products?include_archived=true", headers=headers, timeout=10)
    archived_pid = next((p["id"] for p in r0.json() if p.get("archived_at")), None)
    assert archived_pid is not None
    # Restore
    r1 = requests.post(f"{API}/products/{archived_pid}/restore", headers=headers, timeout=10)
    assert r1.status_code == 200
    assert r1.json()["ok"] is True
    # Verify
    r2 = requests.get(f"{API}/products/{archived_pid}", headers=headers, timeout=10)
    assert r2.json().get("archived_at") is None
    # Re-archive (cleanup)
    requests.post(f"{API}/products/{archived_pid}/archive", headers=headers,
                  json={"reason": "test cleanup"}, timeout=10)


def test_202_assessing_body_only_for_au_nz(headers):
    """Validation: assessing_body_code on non-AU/NZ rejects."""
    r0 = requests.get(f"{API}/products", headers=headers, timeout=10)
    usa_pid = next((p["id"] for p in r0.json() if "USA" in p.get("name", "")), None)
    assert usa_pid
    r = requests.put(f"{API}/products/{usa_pid}", headers=headers,
                     json={"assessing_body_code": "ACS"}, timeout=10)
    assert r.status_code == 400
    assert "AU/NZ" in r.json()["detail"] or "AU" in r.json()["detail"]


def test_202_workflow_id_validation(headers):
    """Validation: unknown workflow_id rejects."""
    r0 = requests.get(f"{API}/products", headers=headers, timeout=10)
    pid = r0.json()[0]["id"]
    r = requests.put(f"{API}/products/{pid}", headers=headers,
                     json={"workflow_id": "nonexistent_xyz"}, timeout=10)
    assert r.status_code == 400


def test_202_commissions_endpoint(headers):
    """GET /products/{id}/commissions returns role-filtered structure."""
    r0 = requests.get(f"{API}/products", headers=headers, timeout=10)
    pid = r0.json()[0]["id"]
    r = requests.get(f"{API}/products/{pid}/commissions", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "product_id" in body and "role" in body and "commissions" in body


def test_202_backup_snapshot_exists():
    """Migration backup file must exist."""
    snapshots = list(Path("/app/memory/snapshots").glob("pre_phase202_products_*.json"))
    assert len(snapshots) >= 1, "Pre-migration snapshot missing"
    # Snapshot must contain at least 19 product entries
    import json
    data = json.loads(snapshots[0].read_text())
    assert len(data) >= 19
