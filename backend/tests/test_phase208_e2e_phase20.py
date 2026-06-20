"""Phase 20.8 — Coupons + Proposals + E2E + Bonus C Funnel Metrics."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


API_BASE = "http://localhost:8001"
API = f"{API_BASE}/api"


@pytest.fixture(scope="module")
def headers():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def db():
    env = Path("/app/backend/.env").read_text()
    mongo_url = env.split("MONGO_URL=")[1].split()[0]
    db_name = env.split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


@pytest.fixture(scope="module", autouse=True)
def cleanup(db):
    yield
    db["coupons"].delete_many({"code": {"$regex": "^P208TEST_"}})
    db["coupon_usages"].delete_many({"client_id": {"$regex": "^p208"}})
    db["proposals"].delete_many({"client_id": {"$regex": "^p208"}})
    db["products"].delete_many({"id": {"$regex": "^p208prod_"}})
    db["import_batches"].delete_many({"ingestion_path": {"$regex": "^phase_20\\.8"}})


# ── S1: Coupons CRUD + validation ─────────────────────────────────────────────
def test_208_seed_coupons(headers, db):
    r = requests.post(f"{API}/coupons/seed", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    # 3 seeds: LUMPSUM20, WELCOME5000, STUDENT15
    assert len(body["created"]) + len(body["skipped"]) >= 3
    for code in ("LUMPSUM20", "WELCOME5000", "STUDENT15"):
        c = db["coupons"].find_one({"code": code})
        assert c is not None
        assert c["status"] == "active"


def test_208_create_coupon(headers, db):
    payload = {
        "code": "P208TEST_PCT",
        "description": "Test 25% coupon",
        "discount_type": "pct", "discount_value": 25.0,
        "applicable_to": "any",
        "valid_from": datetime.now(timezone.utc).isoformat(),
        "valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "usage_limit_total": 100, "usage_limit_per_client": 1,
    }
    r = requests.post(f"{API}/coupons", headers=headers, json=payload, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == "P208TEST_PCT"
    # Duplicate → 409
    r2 = requests.post(f"{API}/coupons", headers=headers, json=payload, timeout=10)
    assert r2.status_code == 409


def test_208_validate_valid_coupon(headers):
    r = requests.get(f"{API}/coupons/validate",
                     headers=headers,
                     params={"code": "P208TEST_PCT", "order_value_inr": 100000}, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["eligible"] is True
    assert body["discount_amount_inr"] == 25000  # 25% of 100k


def test_208_validate_invalid_coupon_returns_404(headers):
    r = requests.get(f"{API}/coupons/validate", headers=headers,
                     params={"code": "DOES_NOT_EXIST_XYZ"}, timeout=10)
    assert r.status_code == 404


def test_208_apply_coupon_idempotent(headers, db):
    r = requests.post(f"{API}/coupons/P208TEST_PCT/apply",
                      headers=headers,
                      params={"client_id": "p208_client_idemp",
                              "product_id": "p208prod_xx", "order_value_inr": 50000},
                      timeout=10)
    assert r.status_code == 200
    assert r.json()["discount_amount_inr"] == 12500
    # Repeat → idempotent
    r2 = requests.post(f"{API}/coupons/P208TEST_PCT/apply",
                       headers=headers,
                       params={"client_id": "p208_client_idemp",
                               "product_id": "p208prod_xx", "order_value_inr": 50000},
                       timeout=10)
    assert r2.status_code == 200
    assert r2.json().get("already_applied") is True


# ── S2: Proposals ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def seed_product(db):
    pid = f"p208prod_{uuid.uuid4().hex[:8]}"
    db["products"].insert_one({
        "id": pid, "name": "Phase208 AU PR Migration Package",
        "country": "Australia", "service_type": "PR",
        "is_active": True, "is_deleted": False,
    })
    yield pid


def test_208_create_proposal_with_coupon(headers, seed_product):
    r = requests.post(f"{API}/proposals", headers=headers, json={
        "client_id": "p208_client_x", "product_id": seed_product,
        "base_fees_inr": 200000,
        "addon_products": [{"name": "Document Review", "price_inr": 15000}],
        "applied_coupon_codes": ["P208TEST_PCT"],
        "admin_special_discount_inr": 5000,
        "admin_special_discount_reason": "Festive offer Q4 2026",
        "closing_message": "Aap ka dhanyavaad Sir 🙏",
    }, timeout=10)
    assert r.status_code == 200, r.text
    p = r.json()
    # 200k + 15k = 215k; coupon 25% of 215k = 53750; admin 5k; subtotal = 215000 - 53750 - 5000 = 156250
    # GST 18% = 28125; total = 184375
    assert p["base_fees_inr"] == 200000
    assert p["addon_total_inr"] == 15000
    assert p["coupon_total_inr"] == 53750
    assert p["admin_discount_inr"] == 5000
    assert p["subtotal_inr"] == 156250
    assert p["gst_inr"] == 28125
    assert p["total_inr"] == 184375
    assert p["status"] == "draft"


def test_208_send_and_get_proposal_pdf(headers, seed_product, db):
    # Create fresh
    r = requests.post(f"{API}/proposals", headers=headers, json={
        "client_id": "p208_client_pdf", "product_id": seed_product,
        "base_fees_inr": 100000,
    }, timeout=10)
    pid = r.json()["id"]
    # Send
    r2 = requests.post(f"{API}/proposals/{pid}/send", headers=headers, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["status"] == "sent"
    # PDF
    r3 = requests.get(f"{API}/proposals/{pid}/pdf", headers=headers, timeout=20)
    assert r3.status_code == 200
    # Either PDF or HTML response - both have substantive body
    assert len(r3.content) > 1000, "PDF/HTML too small"
    # If PDF, content-type should be application/pdf
    assert r3.headers["content-type"] in ("application/pdf", "text/html; charset=utf-8")


def test_208_proposal_reject_unapproved_review(headers, seed_product, db):
    """Cannot create proposal when pa_review_id status != approved."""
    rev_id = f"p208_rev_pending_{uuid.uuid4().hex[:6]}"
    db["pre_assessment_reviews"].insert_one({
        "id": rev_id, "pa_id": "x", "status": "pending",
        "client_id": "p208_client_pending",
        "created_at": datetime.now(timezone.utc),
    })
    try:
        r = requests.post(f"{API}/proposals", headers=headers, json={
            "client_id": "p208_client_pending", "product_id": seed_product,
            "pa_review_id": rev_id, "base_fees_inr": 100000,
        }, timeout=10)
        assert r.status_code == 400
        assert "approved" in r.json().get("detail", "")
    finally:
        db["pre_assessment_reviews"].delete_one({"id": rev_id})


# ── S3: E2E Phase 20 happy path ──────────────────────────────────────────────
def test_208_e2e_full_funnel_happy_path(headers, db, seed_product):
    """End-to-end: PA → mock_payment → mini_portal+info_sheet → review approve → proposal → accept."""
    pa_id = f"p208_e2e_pa_{uuid.uuid4().hex[:6]}"
    client_id = f"p208_client_e2e_{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)
    db["pre_assessments"].insert_one({
        "id": pa_id, "client_name": "Phase208 E2E Client",
        "client_email": "p208e2e@example.com", "client_user_id": client_id,
        "country": "Australia", "service_type": "PR",
        "stage": "payment_pending",
        "partner_id": "test_partner", "partner_name": "Test",
        "pre_assessment_fee": 5100, "product_id": seed_product,
        "created_at": now, "updated_at": now,
    })
    try:
        # 1. Mock payment → mini portal + info sheet
        r1 = requests.post(f"{API}/pre-assessment/{pa_id}/mock-payment", timeout=30)
        assert r1.status_code == 200
        portal = db["client_mini_portals"].find_one({"client_id": client_id})
        assert portal is not None
        sheet = db["information_sheets"].find_one({"entity_type": "client", "entity_id": client_id})
        assert sheet is not None

        # 2. Move PA to under_review + ensure review record
        db["pre_assessments"].update_one({"id": pa_id},
                                          {"$set": {"stage": "under_review", "submitted_at": now}})
        requests.get(f"{API}/admin/pa-reviews?status=pending", headers=headers, timeout=10)
        rev = db["pre_assessment_reviews"].find_one({"pa_id": pa_id})
        assert rev is not None

        # 3. Approve review
        r3 = requests.post(f"{API}/admin/pa-reviews/{rev['id']}/approve",
                           headers=headers, json={"notes": "Looks good"}, timeout=10)
        assert r3.status_code == 200

        # 4. Build proposal with coupon
        r4 = requests.post(f"{API}/proposals", headers=headers, json={
            "client_id": client_id, "product_id": seed_product,
            "pa_review_id": rev["id"], "base_fees_inr": 150000,
            "applied_coupon_codes": ["LUMPSUM20"],
        }, timeout=10)
        assert r4.status_code == 200
        proposal = r4.json()
        assert proposal["coupon_total_inr"] == 30000  # 20% of 150k

        # 5. Send proposal
        r5 = requests.post(f"{API}/proposals/{proposal['id']}/send", headers=headers, timeout=10)
        assert r5.status_code == 200

        # 6. Accept proposal (as admin since we're not switching tokens for client login)
        r6 = requests.post(f"{API}/proposals/{proposal['id']}/accept",
                           headers=headers, timeout=10)
        # Note: only client or admin can accept; admin works
        assert r6.status_code == 200
        assert r6.json()["status"] == "accepted"
    finally:
        db["pre_assessments"].delete_one({"id": pa_id})
        db["client_mini_portals"].delete_one({"client_id": client_id})
        db["information_sheets"].delete_many({"entity_id": client_id})
        db["pre_assessment_reviews"].delete_many({"pa_id": pa_id})
        db["proposals"].delete_many({"client_id": client_id})


# ── Bonus C: Funnel metrics ───────────────────────────────────────────────────
def test_208_funnel_metrics_returns_pipeline(headers):
    r = requests.get(f"{API}/admin/funnel-metrics?days=30", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "funnel" in body
    assert len(body["funnel"]) >= 5
    assert "kpis" in body
    assert "by_pa_stage" in body
    # Conversion rates computed
    for stg in body["funnel"]:
        assert "count" in stg
        assert "pct_of_leads" in stg


def test_208_funnel_metrics_partner_blocked(partner_headers):
    r = requests.get(f"{API}/admin/funnel-metrics?days=30", headers=partner_headers, timeout=10)
    assert r.status_code == 403


def test_208_funnel_metrics_invalid_days(headers):
    r = requests.get(f"{API}/admin/funnel-metrics?days=400", headers=headers, timeout=10)
    assert r.status_code == 400
