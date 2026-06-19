"""Phase 20.3+ — Fee Policy Diff-Preview Bundle tests.

Covers:
1. Diff-preview endpoint computes affected PA count + breakdown
2. Diff modal NOT required for metadata-only edits (fee unchanged)
3. Diff modal IS required when fee_inr changes
4. Retroactive apply updates unpaid PAs + registers revocable batch
5. Retroactive apply rejects partner role
6. Retroactive apply requires min-10-char reason
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
    env_text = Path("/app/backend/.env").read_text()
    mongo_url = env_text.split("MONGO_URL=")[1].split()[0]
    db_name = env_text.split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


@pytest.fixture(scope="module")
def au_pr_policy_id(headers, db):
    """Find the existing AU/PR policy id (seeded in Phase 20.3)."""
    # Ensure seed has been run
    requests.post(f"{API}/pre-assessment-fee-policies/seed", headers=headers, timeout=10)
    pol = db["pre_assessment_fee_policies"].find_one(
        {"country_code": "AU", "visa_category": "PR", "status": "active"}
    )
    assert pol is not None
    return pol["id"]


@pytest.fixture(scope="module")
def seeded_pa_ids(db, au_pr_policy_id):
    """Create 4 test PAs tied to AU/PR policy: 2 unpaid, 1 paid, 1 in_progress."""
    db["pre_assessments"].delete_many({"client_name": {"$regex": "^DiffTest_"}})
    now = datetime.now(timezone.utc)
    pa_docs = [
        {
            "id": f"pa_difftest_{i}",
            "client_name": f"DiffTest_{i}",
            "client_email": f"difftest{i}@example.com",
            "country": "Australia", "service_type": "PR",
            "stage": stage,
            "partner_id": "test_partner", "partner_name": "Test Partner",
            "pre_assessment_fee": 5100,
            "pre_assessment_fee_source": "country_visa_policy",
            "pre_assessment_fee_policy_id": au_pr_policy_id,
            "created_at": now - timedelta(days=5),
            "updated_at": now,
        }
        for i, stage in enumerate(["new", "payment_pending", "payment_received", "documents_submitted"])
    ]
    db["pre_assessments"].insert_many(pa_docs)
    yield [p["id"] for p in pa_docs]
    db["pre_assessments"].delete_many({"client_name": {"$regex": "^DiffTest_"}})
    db["import_batches"].delete_many({"ingestion_path": "phase_20.3_fee_policy.retroactive_apply"})


def test_n1_diff_preview_returns_affected_count(headers, au_pr_policy_id, seeded_pa_ids):
    """Diff-preview endpoint returns 4 affected PAs (2 unpaid + 2 paid)."""
    r = requests.post(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}/diff-preview",
        headers=headers, json={"fee_inr": 6500, "lookback_days": 90}, timeout=10,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["affected_pas_count"] >= 4
    assert body["unpaid_count"] >= 2
    assert body["paid_count"] >= 2
    assert body["old_fee"] == 5100
    assert body["new_fee"] == 6500
    assert body["fee_delta_inr"] == 1400
    assert body["fee_changed"] is True
    assert body["requires_diff_modal"] is True
    assert len(body["sample_pas"]) >= 2  # at least 2 in sample


def test_n1_diff_preview_no_modal_when_fee_unchanged(headers, au_pr_policy_id):
    """When fee_inr is unchanged (or omitted), requires_diff_modal=False."""
    r = requests.post(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}/diff-preview",
        headers=headers, json={"fee_inr": 5100, "lookback_days": 90}, timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["fee_changed"] is False
    assert body["requires_diff_modal"] is False


def test_n1_diff_preview_partner_blocked(partner_headers, au_pr_policy_id):
    r = requests.post(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}/diff-preview",
        headers=partner_headers, json={"fee_inr": 7000}, timeout=10,
    )
    assert r.status_code == 403


def test_n3_apply_retroactive_unpaid_only(headers, db, au_pr_policy_id, seeded_pa_ids):
    """Retroactive apply with affect_unpaid_only=True only touches 2 unpaid PAs.

    Sets policy fee to 6500 first, then applies retroactively.
    """
    # Step 1: Update policy fee_inr to 6500
    r = requests.patch(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}",
        headers=headers, json={"fee_inr": 6500}, timeout=10,
    )
    assert r.status_code == 200

    # Step 2: Apply retroactive
    r = requests.post(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}/apply-retroactive",
        headers=headers,
        json={
            "reason": "Test retroactive update — pricing review Q2 2026",
            "affect_unpaid_only": True,
            "lookback_days": 90,
        },
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["batch_id"].startswith("imp_")
    assert body["updated_count"] >= 2  # 2 unpaid PAs
    assert body["new_fee_inr"] == 6500
    assert body["is_revocable"] is True

    # Verify in DB: unpaid PAs got new fee, paid PAs unchanged
    new_pa = db["pre_assessments"].find_one({"id": "pa_difftest_0"})  # stage=new
    assert new_pa["pre_assessment_fee"] == 6500
    assert new_pa["pre_assessment_fee_source"] == "retroactive_policy_apply"
    paid_pa = db["pre_assessments"].find_one({"id": "pa_difftest_2"})  # stage=payment_received
    assert paid_pa["pre_assessment_fee"] == 5100  # untouched

    # Verify batch registered
    batch = db["import_batches"].find_one({"batch_id": body["batch_id"]})
    assert batch is not None
    assert batch["ingestion_path"] == "phase_20.3_fee_policy.retroactive_apply"
    assert batch["counts"]["updated"] >= 2

    # Revert policy fee for clean state
    requests.patch(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}",
        headers=headers, json={"fee_inr": 5100}, timeout=10,
    )


def test_n3_apply_retroactive_partner_blocked(partner_headers, au_pr_policy_id):
    r = requests.post(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}/apply-retroactive",
        headers=partner_headers,
        json={"reason": "test partner blocked attempt", "affect_unpaid_only": True},
        timeout=10,
    )
    assert r.status_code == 403


def test_n3_apply_retroactive_requires_min_reason_length(headers, au_pr_policy_id):
    """Reason must be ≥10 chars for audit safety."""
    r = requests.post(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}/apply-retroactive",
        headers=headers,
        json={"reason": "short", "affect_unpaid_only": True},
        timeout=10,
    )
    assert r.status_code == 422  # Pydantic validation error


def test_n3_audit_log_written_on_retroactive_apply(headers, db, au_pr_policy_id, seeded_pa_ids):
    """Audit log should have a fee_policy.retroactive_apply entry with severity=warn."""
    # Set fee and apply
    requests.patch(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}",
        headers=headers, json={"fee_inr": 5500}, timeout=10,
    )
    r = requests.post(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}/apply-retroactive",
        headers=headers,
        json={
            "reason": "Audit log test — verify severity=warn is written",
            "affect_unpaid_only": True,
        },
        timeout=15,
    )
    assert r.status_code == 200

    # Check audit log
    log = db["audit_logs"].find_one(
        {"action": "fee_policy.retroactive_apply"},
        sort=[("at", -1)],
    )
    assert log is not None
    assert log["severity"] == "warn"
    assert log["summary"]["policy_id"] == au_pr_policy_id

    # Revert
    requests.patch(
        f"{API}/pre-assessment-fee-policies/{au_pr_policy_id}",
        headers=headers, json={"fee_inr": 5100}, timeout=10,
    )
