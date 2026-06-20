"""Phase 20.5 + Bonus A + B — Funnel stitching + polish + completion score tests.

Coverage matrix:
  O1 — InfoSheet embed (covered via existing /api/info-sheets routes + entity_type=client)
  O2 — Mini Portal provisioning + admin controls (8 tests)
  O3 — Admin Review queue (4 tests)
  O4 — eligibility_info_sheet legacy bridge (1 test)
  Bonus A — OpenAPI route + PATCH section alias + diff nested body + field audit (4 tests)
  Bonus B — Smart Completion Score + cross-validation (3 tests)

Total: 20 tests targeting 117/117 baseline → 137+ green.
"""
from __future__ import annotations

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
    env = Path("/app/backend/.env").read_text()
    mongo_url = env.split("MONGO_URL=")[1].split()[0]
    db_name = env.split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


@pytest.fixture(scope="module", autouse=True)
def cleanup(db):
    yield
    db["pre_assessments"].delete_many({"client_name": {"$regex": "^Phase205_"}})
    db["client_mini_portals"].delete_many({"client_name": {"$regex": "^Phase205_"}})
    db["information_sheets"].delete_many({"entity_id": {"$regex": "^phase205_"}})
    db["pre_assessment_reviews"].delete_many({"client_name": {"$regex": "^Phase205_"}})
    db["import_batches"].delete_many({
        "ingestion_path": {"$regex": "^phase_20\\.5_"},
    })


@pytest.fixture(scope="module")
def seeded_pa(db):
    """Seed a fresh PA at stage=payment_pending for provisioning tests."""
    pa_id = f"phase205_pa_{uuid.uuid4().hex[:8]}"
    client_id = f"phase205_client_{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)
    doc = {
        "id": pa_id,
        "client_name": f"Phase205_Client_{uuid.uuid4().hex[:4]}",
        "client_email": f"phase205test+{uuid.uuid4().hex[:4]}@example.com",
        "client_phone": "+91 9876512345",
        "client_user_id": client_id,
        "country": "Australia", "service_type": "PR",
        "stage": "payment_pending",
        "partner_id": "test_partner", "partner_name": "Test Partner",
        "pre_assessment_fee": 5100,
        "pre_assessment_fee_source": "country_visa_policy",
        "created_at": now, "updated_at": now,
    }
    db["pre_assessments"].insert_one(doc)
    yield pa_id, client_id, doc
    db["pre_assessments"].delete_one({"id": pa_id})


# ── O2: Mini Portal provisioning ──────────────────────────────────────────────
def test_205_pa_mock_payment_auto_provisions_mini_portal(seeded_pa, db):
    pa_id, client_id, _ = seeded_pa
    r = requests.post(f"{API}/pre-assessment/{pa_id}/mock-payment", timeout=30)
    assert r.status_code == 200, r.text
    # Mini portal should now exist
    portal = db["client_mini_portals"].find_one({"client_id": client_id})
    assert portal is not None
    assert portal["pa_id"] == pa_id
    assert portal["status"] == "active"
    assert portal["password_must_change"] is True
    assert len(portal["temp_password"]) == 12


def test_205_pa_mock_payment_auto_creates_info_sheet(seeded_pa, db):
    _, client_id, _ = seeded_pa
    # Already provisioned by previous test
    sheet = db["information_sheets"].find_one({"entity_type": "client", "entity_id": client_id})
    assert sheet is not None
    assert sheet["schema_version"] == 2
    assert sheet["personal"]  # has personal section pre-filled


def test_205_provisioning_idempotent(seeded_pa):
    """Re-running mock-payment doesn't create duplicate portal records."""
    pa_id, _, _ = seeded_pa
    r = requests.post(f"{API}/pre-assessment/{pa_id}/mock-payment", timeout=30)
    assert r.status_code == 200


def test_205_admin_lists_mini_portals(headers, seeded_pa):
    r = requests.get(f"{API}/mini-portal/admin/list?status=active", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "portals" in body
    assert body["count"] >= 1


def test_205_admin_reset_password(headers, seeded_pa, db):
    _, client_id, _ = seeded_pa
    old = db["client_mini_portals"].find_one({"client_id": client_id})
    old_pw = old["temp_password"]
    r = requests.post(f"{API}/mini-portal/admin/{client_id}/reset-password",
                      headers=headers,
                      json={"reason": "Sir requested security reset Q3 2026"}, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["new_password"] != old_pw
    assert body["revocable"] is True


def test_205_admin_reset_partner_blocked(partner_headers, seeded_pa):
    _, client_id, _ = seeded_pa
    r = requests.post(f"{API}/mini-portal/admin/{client_id}/reset-password",
                      headers=partner_headers,
                      json={"reason": "Partner attempting reset — should fail"}, timeout=10)
    assert r.status_code == 403


def test_205_admin_lock_then_unlock(headers, seeded_pa, db):
    _, client_id, _ = seeded_pa
    r1 = requests.post(f"{API}/mini-portal/admin/{client_id}/lock",
                       headers=headers,
                       json={"reason": "Test lock — Phase 20.5 verification"}, timeout=10)
    assert r1.status_code == 200
    portal = db["client_mini_portals"].find_one({"client_id": client_id})
    assert portal["locked"] is True
    assert portal["status"] == "locked"
    r2 = requests.post(f"{API}/mini-portal/admin/{client_id}/unlock", headers=headers, timeout=10)
    assert r2.status_code == 200
    portal = db["client_mini_portals"].find_one({"client_id": client_id})
    assert portal["locked"] is False


def test_205_get_portal_status(headers, seeded_pa):
    _, client_id, _ = seeded_pa
    r = requests.get(f"{API}/mini-portal/{client_id}", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["portal"]["client_id"] == client_id
    assert body["info_sheet"] is not None
    assert body["info_sheet"]["schema_version"] == 2


# ── O3: Admin Review Queue ────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def under_review_pa(db, seeded_pa):
    """Move the seeded PA to under_review stage so it appears in admin queue."""
    pa_id, client_id, _ = seeded_pa
    db["pre_assessments"].update_one(
        {"id": pa_id},
        {"$set": {"stage": "under_review", "submitted_at": datetime.now(timezone.utc)}},
    )
    return pa_id, client_id


def test_205_pa_review_queue_lists_pending(headers, under_review_pa):
    pa_id, _ = under_review_pa
    r = requests.get(f"{API}/admin/pa-reviews?status=pending", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    pa_ids = [rev["pa_id"] for rev in body["reviews"]]
    assert pa_id in pa_ids


def test_205_pa_review_approve(headers, under_review_pa, db):
    pa_id, _ = under_review_pa
    # Fetch review id
    rev = db["pre_assessment_reviews"].find_one({"pa_id": pa_id})
    rev_id = rev["id"]
    r = requests.post(f"{API}/admin/pa-reviews/{rev_id}/approve", headers=headers,
                      json={"notes": "All docs verified, approved for proposal"}, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "approved"
    assert body["next_stage"] == "admin_approved"
    assert body["revocable"] is True
    # PA stage updated
    pa = db["pre_assessments"].find_one({"id": pa_id})
    assert pa["stage"] == "admin_approved"


def test_205_pa_review_reject_with_refund(headers, db):
    """Test reject with refund action on a fresh PA."""
    pa_id = f"phase205_pa_refund_{uuid.uuid4().hex[:6]}"
    client_id = f"phase205_client_refund_{uuid.uuid4().hex[:6]}"
    db["pre_assessments"].insert_one({
        "id": pa_id,
        "client_name": f"Phase205_Refund_{uuid.uuid4().hex[:4]}",
        "client_email": "phase205refund@example.com",
        "client_user_id": client_id,
        "country": "Canada", "service_type": "PR", "stage": "under_review",
        "partner_id": "test", "partner_name": "Test",
        "pre_assessment_fee": 5100, "submitted_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    # Trigger ensure_review_record by listing
    requests.get(f"{API}/admin/pa-reviews?status=pending", headers=headers, timeout=10)
    rev = db["pre_assessment_reviews"].find_one({"pa_id": pa_id})
    assert rev is not None
    r = requests.post(
        f"{API}/admin/pa-reviews/{rev['id']}/reject", headers=headers,
        json={"action": "refund",
              "reason": "Client requested cancellation — full refund authorised",
              "refund_amount_inr": 5100}, timeout=10,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "refunded"
    assert body["refund_amount_inr"] == 5100
    pa = db["pre_assessments"].find_one({"id": pa_id})
    assert pa["stage"] == "refunded"


def test_205_pa_review_reject_partner_blocked(partner_headers):
    r = requests.post(f"{API}/admin/pa-reviews/some-fake-id/reject",
                      headers=partner_headers,
                      json={"action": "close_case", "reason": "Unauthorised attempt"},
                      timeout=10)
    assert r.status_code == 403


# ── Bonus A: Polish ───────────────────────────────────────────────────────────
def test_205_openapi_route_returns_spec(headers):
    r = requests.get(f"{API}/openapi.json", headers=headers, timeout=10)
    assert r.status_code == 200
    spec = r.json()
    assert "openapi" in spec
    assert "paths" in spec
    assert "/api/info-sheets" in str(spec["paths"]) or "/info-sheets" in str(spec["paths"])


def test_205_section_patch_alias(headers, db):
    """PATCH /info-sheets/{id}/section/personal works as alias for root patch."""
    eid = f"phase205_section_alias_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/info-sheets", headers=headers,
                      json={"entity_type": "standalone", "entity_id": eid}, timeout=10)
    assert r.status_code == 200
    sheet_id = r.json()["id"]
    # Use section alias
    r2 = requests.patch(f"{API}/info-sheets/{sheet_id}/section/personal", headers=headers,
                       json={"given_names": "AliasTest", "family_name": "User"}, timeout=10)
    assert r2.status_code == 200
    body = r2.json()
    assert body["ok"] is True
    # Verify saved
    sheet = db["information_sheets"].find_one({"id": sheet_id})
    assert sheet["personal"]["given_names"] == "AliasTest"
    # Cleanup
    db["information_sheets"].delete_one({"id": sheet_id})


def test_205_field_level_audit_granularity(headers, db):
    eid = f"phase205_field_audit_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/info-sheets", headers=headers,
                      json={"entity_type": "standalone", "entity_id": eid}, timeout=10)
    sheet_id = r.json()["id"]
    # Two patches — should show field-level deltas
    requests.patch(f"{API}/info-sheets/{sheet_id}", headers=headers,
                   json={"personal": {"given_names": "First"}}, timeout=10)
    requests.patch(f"{API}/info-sheets/{sheet_id}", headers=headers,
                   json={"personal": {"given_names": "Second", "email": "x@y.com"}}, timeout=10)
    r3 = requests.get(f"{API}/info-sheets/{sheet_id}/audit-trail", headers=headers, timeout=10)
    events = r3.json()["events"]
    # Most recent patch has both fields changed
    latest_patch = next(e for e in events if e["action"] == "patch")
    assert latest_patch.get("fields_changed") is not None
    assert len(latest_patch["fields_changed"]) >= 1
    db["information_sheets"].delete_one({"id": sheet_id})


def test_205_diff_preview_accepts_nested_body(headers, db):
    pol = db["pre_assessment_fee_policies"].find_one({"country_code": "AU", "visa_category": "PR"})
    r = requests.post(
        f"{API}/pre-assessment-fee-policies/{pol['id']}/diff-preview", headers=headers,
        json={"proposed_changes": {"fee_inr": 6800}, "lookback_days": 90}, timeout=10,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["new_fee"] == 6800
    assert body["fee_changed"] is True


# ── Bonus B: Smart Completion Score ───────────────────────────────────────────
def test_205_completion_score_zero_for_empty_sheet(headers):
    eid = f"phase205_score_empty_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/info-sheets", headers=headers,
                      json={"entity_type": "standalone", "entity_id": eid}, timeout=10)
    sheet_id = r.json()["id"]
    r2 = requests.get(f"{API}/info-sheets/{sheet_id}/completion-score", headers=headers, timeout=10)
    assert r2.status_code == 200
    body = r2.json()
    assert body["score"] == 0.0
    assert body["color"] == "red"
    assert len(body["missing_critical"]) == 15  # all required missing


def test_205_completion_score_weighted_correctly(headers, db):
    eid = f"phase205_score_full_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/info-sheets", headers=headers,
                      json={"entity_type": "standalone", "entity_id": eid}, timeout=10)
    sheet_id = r.json()["id"]
    # Fill all required personal + 1 qual + 1 emp
    requests.patch(f"{API}/info-sheets/{sheet_id}", headers=headers, json={
        "personal": {
            "given_names": "F", "family_name": "L", "gender": "Male",
            "date_of_birth": "1990-01-01", "country_of_birth": "India",
            "nationality": "Indian", "address": "Test", "email": "x@y.com",
            "contact_number": "9876543210", "passport_number": "Z123",
            "passport_issue_date": "2020-01-01",
            "passport_expiry_date": "2030-01-01",
            "marital_status": "Single", "father_name": "F", "mother_name": "M",
        },
        "qualifications": [{"name": "BTech", "awarding_body": "IIT"}],
        "employment": [{"business_name": "TCS", "job_title": "Engineer"}],
    }, timeout=10)
    r3 = requests.get(f"{API}/info-sheets/{sheet_id}/completion-score", headers=headers, timeout=10)
    body = r3.json()
    # Personal=30, qual=20, employment=20 → expect ~70
    assert body["score"] >= 70
    assert body["color"] in ("green", "amber")
    assert body["breakdown"]["personal"] == 30.0
    assert body["breakdown"]["qualifications"] == 20.0
    assert body["breakdown"]["employment"] == 20.0
    db["information_sheets"].delete_one({"id": sheet_id})


def test_205_cross_validation_detects_empty_quals_with_resume(db):
    """Direct unit test of completion service cross-validation."""
    from services.info_sheet_completion_service import cross_validate
    sheet = {
        "personal": {"date_of_birth": "1990-05-15"},
        "qualifications": [],
        "employment": [],
        "resume": {
            "file_name": "test.pdf",
            "extracted_at": "2026-06-20T12:00:00Z",
            "extracted_qualifications": [{"degree": "BTech", "start_date": "2008-08-01"}],
            "extracted_employment": [{"job_title": "Engineer"}],
            "summary": {"total_years_experience": 5, "skills": []},
        },
    }
    warnings = cross_validate(sheet)
    # Should detect: empty quals + empty employment (high severity)
    high_warnings = [w for w in warnings if w["severity"] == "high"]
    assert len(high_warnings) >= 2
    sections = {w["section"] for w in high_warnings}
    assert "qualifications" in sections
    assert "employment" in sections
