"""Phase 20.3 + Bulk Importer — pre-assessment fee resolver & policy tests."""
from __future__ import annotations

import io
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


API_BASE = os.environ.get("API_BASE") or "http://localhost:8001"
API = f"{API_BASE}/api"
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASS = "Partner@123"


@pytest.fixture(scope="module")
def headers():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{API}/auth/login", json={"email": PARTNER_EMAIL, "password": PARTNER_PASS}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def db():
    mongo_url = Path("/app/backend/.env").read_text().split("MONGO_URL=")[1].split()[0]
    db_name = Path("/app/backend/.env").read_text().split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


# ── Resolver unit tests ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_203_resolver_safety_net_when_db_empty():
    from services.pre_assessment_fee_resolver import resolve_pre_assessment_fee, HARDCODED_SAFETY_NET_INR
    from motor.motor_asyncio import AsyncIOMotorClient
    # Use a temp DB so we don't disturb real one
    cli = AsyncIOMotorClient("mongodb://localhost:27017")
    tmpdb = cli[f"phase203_test_{uuid.uuid4().hex[:8]}"]
    try:
        r = await resolve_pre_assessment_fee(tmpdb, country_code="XX", visa_category="UNKNOWN")
        assert r["source"] == "hardcoded_safety_net"
        assert r["amount"] == HARDCODED_SAFETY_NET_INR
    finally:
        await cli.drop_database(tmpdb.name)
        cli.close()


# ── Integration tests ─────────────────────────────────────────────────────────
def test_203_seed_creates_six_policies(headers, db):
    """POST /seed creates 6 policies (idempotent — re-runs are no-ops)."""
    r = requests.post(f"{API}/pre-assessment-fee-policies/seed", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    # On 2nd run, all 6 will be skipped
    assert body["count_created"] + body["count_skipped"] == 6
    # Verify DB count
    count = db["pre_assessment_fee_policies"].count_documents(
        {"status": "active", "policy_name": {"$regex": "Standard 2026|PA 2026|Fallback"}})
    assert count >= 6


def test_203_resolve_au_pr_country_policy(headers):
    r = requests.get(f"{API}/pre-assessment-fee-policies/resolve?country=AU&visa_category=PR",
                     headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["amount"] == 5100
    assert body["source"] == "country_visa_policy"
    assert body["country_code"] == "AU"


def test_203_resolve_au_study_country_policy(headers):
    """AU + STUDY = ₹3,000 (cheaper student PA)."""
    r = requests.get(f"{API}/pre-assessment-fee-policies/resolve?country=AU&visa_category=STUDY",
                     headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["amount"] == 3000
    assert body["source"] == "country_visa_policy"


def test_203_resolve_unknown_falls_to_global(headers):
    """ZZ+UNKNOWN → global_fallback ₹5,100."""
    r = requests.get(f"{API}/pre-assessment-fee-policies/resolve?country=ZZ&visa_category=UNKNOWN",
                     headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["amount"] == 5100
    assert body["source"] == "global_fallback"


def test_203_resolve_product_override_priority(headers, db):
    """Product with pre_assessment_fee_inr set overrides country policy."""
    r0 = requests.get(f"{API}/products", headers=headers, timeout=10)
    pid = next((p["id"] for p in r0.json() if "Canada PR" in p.get("name", "")), None)
    assert pid
    # Set per-product override = ₹9,999
    requests.put(f"{API}/products/{pid}", headers=headers,
                 json={"pre_assessment_fee_inr": 9999}, timeout=10)
    r = requests.get(f"{API}/pre-assessment-fee-policies/resolve?product_id={pid}",
                     headers=headers, timeout=10)
    body = r.json()
    assert body["amount"] == 9999
    assert body["source"] == "product_override"
    assert body["product_id"] == pid
    # Cleanup
    requests.put(f"{API}/products/{pid}", headers=headers,
                 json={"pre_assessment_fee_inr": None}, timeout=10)


def test_203_partner_blocked_on_policy_create(partner_headers):
    """Non-admin gets 403 on policy POST."""
    r = requests.post(f"{API}/pre-assessment-fee-policies", headers=partner_headers,
                      json={"country_code": "XX", "visa_category": "TEST", "fee_inr": 9999,
                            "policy_name": "Test"}, timeout=10)
    assert r.status_code == 403


def test_203_partner_can_read_policies(partner_headers):
    """Partner can READ but not write."""
    r = requests.get(f"{API}/pre-assessment-fee-policies", headers=partner_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["count"] >= 6


def test_203_policy_crud_lifecycle(headers, db):
    """End-to-end: create → patch → deprecate."""
    # Create
    r1 = requests.post(f"{API}/pre-assessment-fee-policies", headers=headers, json={
        "country_code": "UK", "visa_category": "WORK", "fee_inr": 4000,
        "policy_name": "UK Work Test 2026", "rationale": "Test policy",
    }, timeout=10)
    assert r1.status_code == 200
    pid = r1.json()["id"]
    assert r1.json()["batch_id"].startswith("imp_")
    # Patch
    r2 = requests.patch(f"{API}/pre-assessment-fee-policies/{pid}", headers=headers,
                       json={"fee_inr": 4250}, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["fee_inr"] == 4250
    # Resolve should pick this up
    r3 = requests.get(f"{API}/pre-assessment-fee-policies/resolve?country=UK&visa_category=WORK",
                      headers=headers, timeout=10)
    assert r3.json()["amount"] == 4250
    # Deprecate
    r4 = requests.delete(f"{API}/pre-assessment-fee-policies/{pid}", headers=headers, timeout=10)
    assert r4.status_code == 200
    # After deprecation, resolver falls to global
    r5 = requests.get(f"{API}/pre-assessment-fee-policies/resolve?country=UK&visa_category=WORK",
                      headers=headers, timeout=10)
    assert r5.json()["source"] == "global_fallback"


def test_203_pa_payment_uses_resolved_fee(headers, db):
    """When a PA is created with product_id having override, stored fee = override (not hardcoded)."""
    r0 = requests.get(f"{API}/products", headers=headers, timeout=10)
    pid = next((p["id"] for p in r0.json() if "Australia PR" in p.get("name", "")), None)
    assert pid
    # Set override = ₹12,345
    requests.put(f"{API}/products/{pid}", headers=headers,
                 json={"pre_assessment_fee_inr": 12345}, timeout=10)
    # Create PA
    r = requests.post(f"{API}/pre-assessment/create", headers=headers, json={
        "client_name": "Resolver Test Client",
        "client_email": f"resolver-{uuid.uuid4().hex[:6]}@example.com",
        "client_phone": "+919999999999",
        "country": "Australia",
        "service_type": "PR",
        "product_id": pid,
        "sale_type": "standard",
    }, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    pa_id = body.get("id") or body.get("pa_id")
    assert pa_id, f"PA create returned no id: {body}"
    # Verify stored fee
    pa_doc = db["pre_assessments"].find_one({"id": pa_id})
    assert pa_doc["pre_assessment_fee"] == 12345, f"Expected 12345, got {pa_doc.get('pre_assessment_fee')}"
    assert pa_doc["pre_assessment_fee_source"] == "product_override"
    # Cleanup
    requests.put(f"{API}/products/{pid}", headers=headers,
                 json={"pre_assessment_fee_inr": None}, timeout=10)
    db["pre_assessments"].delete_one({"id": pa_id})


# ── Bulk Importer tests ───────────────────────────────────────────────────────
def test_203_bulk_template_download(headers):
    r = requests.get(f"{API}/products-bulk-import/template", headers=headers, timeout=10)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    csv_text = r.text
    assert "name" in csv_text and "country" in csv_text and "category" in csv_text


def test_203_bulk_preview_detects_new_and_invalid(headers):
    csv_content = (
        b"name,country,category,base_fee,is_pre_assessment\n"
        b"BulkTest_New_Product_001,UK,study,75000,true\n"
        b"BulkTest_New_Product_002,USA,study,80000,false\n"
        b",,,99999,false\n"  # row with missing required fields
    )
    files = {"file": ("test_bulk.csv", csv_content, "text/csv")}
    r = requests.post(f"{API}/products-bulk-import/preview", headers=headers, files=files, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["total_rows"] == 3
    assert body["new"] == 2
    assert body["invalid"] == 1


def test_203_bulk_commit_creates_and_registers_batch(headers, db):
    """Commit creates new products + registers revocable batch."""
    # Pre-clean
    db["products"].delete_many({"name": {"$regex": "^BulkTest_Commit_"}})
    csv_content = (
        b"name,country,category,base_fee\n"
        b"BulkTest_Commit_001,UK,study,75000\n"
        b"BulkTest_Commit_002,USA,study,80000\n"
    )
    files = {"file": ("commit_test.csv", csv_content, "text/csv")}
    r = requests.post(f"{API}/products-bulk-import/commit", headers=headers, files=files, timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["created"] == 2
    assert body["batch_id"].startswith("imp_")
    # Verify in DB
    created = list(db["products"].find({"name": {"$regex": "^BulkTest_Commit_"}}))
    assert len(created) == 2
    # Verify batch registered
    batch = db["import_batches"].find_one({"batch_id": body["batch_id"]})
    assert batch is not None
    # Cleanup
    db["products"].delete_many({"name": {"$regex": "^BulkTest_Commit_"}})


def test_203_bulk_partner_blocked(partner_headers):
    csv_content = b"name,country,category\nX,USA,study\n"
    files = {"file": ("x.csv", csv_content, "text/csv")}
    r = requests.post(f"{API}/products-bulk-import/preview", headers=partner_headers,
                      files=files, timeout=10)
    assert r.status_code == 403
