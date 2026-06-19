"""Phase 19.9 — Authority Admin write endpoints + diff audit tests.

Run: cd /app/backend && pytest tests/test_phase199_authority_admin.py -v
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


API_BASE = os.environ.get("API_BASE") or (
    Path("/app/frontend/.env").read_text().split("REACT_APP_BACKEND_URL=")[1].split()[0]
)
API = f"{API_BASE}/api"
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"


@pytest.fixture(scope="module")
def admin_token() -> str:
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def db():
    mongo_url = Path("/app/backend/.env").read_text().split("MONGO_URL=")[1].split()[0]
    db_name = Path("/app/backend/.env").read_text().split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


@pytest.fixture(scope="module")
def tmp_code() -> str:
    """Unique throwaway code so tests are idempotent."""
    return f"TMP-{uuid.uuid4().hex[:6].upper()}"


def test_1_create_admin_only_no_auth_blocked(tmp_code):
    """T1: POST without auth → 401/403."""
    r = requests.post(f"{API}/assessing-authorities",
                      json={"code": tmp_code, "full_name": "Test Body"}, timeout=15)
    assert r.status_code in (401, 403)


def test_2_create_validates_required_fields(headers):
    """T2: Missing full_name → 422."""
    r = requests.post(f"{API}/assessing-authorities",
                      headers=headers,
                      json={"code": "X", "full_name": ""}, timeout=15)
    assert r.status_code == 422


def test_3_create_authority(headers, tmp_code, db):
    """T3: Successful create returns 200 + record."""
    r = requests.post(f"{API}/assessing-authorities",
                      headers=headers,
                      json={"code": tmp_code, "full_name": f"Phase 19.9 Test Body {tmp_code}",
                            "fees": {"msa_fee_aud": 500},
                            "processing": {"standard_days_min": 30, "standard_days_max": 60}}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == tmp_code
    assert body["status"] == "draft"
    assert body["batch_id"]
    # Verify in DB
    doc = db.assessing_authorities.find_one({"code": tmp_code})
    assert doc is not None


def test_4_create_duplicate_code_returns_409(headers, tmp_code):
    """T4: Creating same code twice → 409."""
    r = requests.post(f"{API}/assessing-authorities", headers=headers,
                      json={"code": tmp_code, "full_name": "duplicate"}, timeout=15)
    assert r.status_code == 409


def test_5_patch_updates_fields(headers, tmp_code, db):
    """T5: PATCH updates fees + records audit."""
    r = requests.patch(f"{API}/assessing-authorities/{tmp_code}",
                       headers=headers,
                       json={"fees": {"msa_fee_aud": 750},
                             "full_name": f"Phase 19.9 Test Body {tmp_code} (renamed)"}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fees"]["msa_fee_aud"] == 750
    assert "renamed" in body["full_name"]
    assert body["batch_id"]


def test_6_verify_flips_status(headers, tmp_code, db):
    """T6: POST /verify flips draft → active."""
    r = requests.post(f"{API}/assessing-authorities/{tmp_code}/verify", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "active"
    doc = db.assessing_authorities.find_one({"code": tmp_code})
    assert doc["status"] == "active"
    assert doc.get("verified_at")


def test_7_bulk_verify_processes_list(headers, db):
    """T7: bulk-verify accepts list of codes."""
    # Pick 3 known draft authority codes
    drafts = list(db.assessing_authorities.find({"status": "draft", "country": "AU"}, {"code": 1}).limit(3))
    codes = [d["code"] for d in drafts]
    if not codes:
        pytest.skip("No draft authorities to bulk-verify")
    r = requests.post(f"{API}/assessing-authorities/bulk-verify",
                      headers=headers, json={"codes": codes}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verified_count"] == len(codes)
    # Restore them to draft for other tests
    for code in codes:
        db.assessing_authorities.update_one(
            {"code": code}, {"$set": {"status": "draft"}, "$unset": {"verified_at": ""}},
        )


def test_8_delete_blocked_if_linked(headers, db):
    """T8: DELETE blocked if occupation_count > 0."""
    # ACS has 34 linked occupations
    r = requests.delete(f"{API}/assessing-authorities/ACS", headers=headers, timeout=15)
    assert r.status_code == 409
    assert "linked" in r.text.lower() or "occupations" in r.text.lower()


def test_9_delete_allowed_if_unlinked(headers, tmp_code, db):
    """T9: DELETE of throwaway test body succeeds."""
    r = requests.delete(f"{API}/assessing-authorities/{tmp_code}", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] is True
    assert db.assessing_authorities.find_one({"code": tmp_code}) is None


def test_10_diff_preview_returns_affected_pages(headers):
    """T10: diff-preview returns affected_occupation_count + meta_diffs sample."""
    r = requests.post(f"{API}/assessing-authorities/ACS/diff-preview", headers=headers,
                      json={"proposed_changes": {"full_name": "ACS (Renamed in Diff Test)"}}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["affected_occupation_count"] >= 30
    assert body["estimated_seo_impact"] in ("none", "low", "medium", "high")
    assert "meta_description_diffs" in body


def test_11_diff_preview_no_changes_returns_none_impact(headers):
    """T11: empty proposed_changes → estimated_seo_impact = 'none'."""
    r = requests.post(f"{API}/assessing-authorities/ACS/diff-preview", headers=headers,
                      json={"proposed_changes": {}}, timeout=15)
    assert r.status_code == 200
    assert r.json()["estimated_seo_impact"] == "none"


def test_12_split_laa_only_works_on_laa(headers):
    """T12: split-laa rejects non-LAA codes."""
    r = requests.post(f"{API}/assessing-authorities/ACS/split-laa", headers=headers,
                      json={}, timeout=15)
    assert r.status_code == 400


def test_13_split_laa_creates_state_bodies(headers, db):
    """T13: split-laa on LAA creates 6 state bodies + marks LAA deprecated."""
    # Cleanup any prior state bodies + reset LAA
    db.assessing_authorities.delete_many({"code": {"$regex": "^LAA-"}})
    db.assessing_authorities.update_one(
        {"code": "LAA"},
        {"$set": {"status": "draft"}, "$unset": {"_deprecated_by_split_at": "", "_deprecated_split_into": ""}},
    )
    r = requests.post(f"{API}/assessing-authorities/LAA/split-laa", headers=headers,
                      json={}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["created_codes"]) == 6
    assert body["deprecated"] == "LAA"
    # Verify LAA is now deprecated
    laa = db.assessing_authorities.find_one({"code": "LAA"})
    assert laa["status"] == "deprecated"
    # Verify 6 state bodies created
    states = list(db.assessing_authorities.find({"code": {"$regex": "^LAA-"}}))
    assert len(states) == 6


def test_14_migrate_occupation_moves_fk(headers, db):
    """T14: migrate-occupation reassigns an occupation FK to a different body."""
    # Find a CWA-mapped occupation
    cwa = db.assessing_authorities.find_one({"code": "CWA"})
    if not cwa:
        pytest.skip("CWA body not found")
    target_occ = db.occupation_master.find_one({"country_code": "AU", "assessing_authority_id": cwa["id"]})
    if not target_occ:
        pytest.skip("No CWA-linked occupation to migrate")
    occ_id = target_occ["occupation_id"]
    # Migrate to AASW
    r = requests.post(f"{API}/assessing-authorities/migrate-occupation",
                      headers=headers,
                      json={"occupation_id": occ_id, "new_authority_code": "AASW",
                            "reason": "test migrate"}, timeout=15)
    assert r.status_code == 200, r.text
    # Verify
    updated = db.occupation_master.find_one({"occupation_id": occ_id})
    aasw = db.assessing_authorities.find_one({"code": "AASW"})
    assert updated["assessing_authority_id"] == aasw["id"]
    # Restore
    db.occupation_master.update_one(
        {"occupation_id": occ_id},
        {"$set": {"assessing_authority_id": cwa["id"]}},
    )


def test_15_writes_register_import_batch(headers, db):
    """T15: Every Phase 19.9 write creates an import_batch."""
    n = db.import_batches.count_documents({"ingestion_path": {"$regex": "phase_19.9_authority_admin"}})
    assert n > 0, "No Phase 19.9 import_batches found — write endpoints didn't register batches"
