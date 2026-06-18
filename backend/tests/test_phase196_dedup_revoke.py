"""Phase 19.6 — Pytest integration tests for import_batches + revoke + dedup.

These hit the running backend (preview URL) end-to-end. Run with:
    cd /app/backend && pytest tests/test_phase196_dedup_revoke.py -v

Tests cover:
  1. /preview returns preview_token + token_expires_in
  2. /commit without token → 400
  3. /commit with token → 200 + batch_id + creates 2 ZZ rows
  4. /import-batches lists the new batch (status=committed, is_revocable=True)
  5. /import-batches/{id}/revoke → 200, deletes 2 ZZ rows
  6. Revoke twice → 400 "already revoked"
  7. Dedup: re-running same file with on_duplicate=skip → skipped=N
  8. Force-revoke without admin_override=true → 400
  9. /occupation-master/stats has `enrichment` sub-object (3-way)
 10. file_hash mismatch on /commit → 400 (token bound to file content)
"""
from __future__ import annotations

import hashlib
import os
import time
from io import BytesIO
from pathlib import Path

import pytest
import requests


# ─── Setup ────────────────────────────────────────────────────────────────────
API_BASE = os.environ.get("API_BASE") or (
    Path("/app/frontend/.env").read_text().split("REACT_APP_BACKEND_URL=")[1].split()[0]
)
API = f"{API_BASE}/api"
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"
TEST_COUNTRY = "ZZ"  # ISO sandbox code — never collides with real data
CSV_BODY = (
    "code,title,description\n"
    "PH196-PYTEST-1,Phase 19.6 Pytest Code 1,Pytest smoke row\n"
    "PH196-PYTEST-2,Phase 19.6 Pytest Code 2,Pytest smoke row\n"
)


@pytest.fixture(scope="module")
def admin_token() -> str:
    r = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def cleanup_zz(headers):
    """Wipe any prior ZZ rows + pytest test_batches before/after each test."""
    yield
    # Cleanup pytest rows on teardown
    try:
        # Hard-delete via internal Mongo through revoke-list-and-revoke path won't
        # catch already-revoked. We use direct delete only as defensive cleanup
        # of test artifacts — production data is country_code=ZZ which is sandbox.
        import pymongo  # noqa: PLC0415
        from urllib.parse import urlparse  # noqa: PLC0415
        mongo_url = Path("/app/backend/.env").read_text().split("MONGO_URL=")[1].split()[0]
        db_name = Path("/app/backend/.env").read_text().split("DB_NAME=")[1].split()[0]
        client = pymongo.MongoClient(mongo_url)
        db = client[db_name]
        db.occupation_master.delete_many({"country_code": TEST_COUNTRY})
        db.import_batches.delete_many({
            "target_collection": "occupation_master",
            "file_name": {"$regex": "PH196.*pytest|phase196.*pytest", "$options": "i"},
        })
    except Exception:  # noqa: BLE001
        pass


def _csv_file():
    return ("phase196_pytest.csv", BytesIO(CSV_BODY.encode()), "text/csv")


# ─── Tests ────────────────────────────────────────────────────────────────────
def test_1_preview_returns_preview_token(headers, cleanup_zz):
    """T1: /preview returns preview_token + ttl."""
    r = requests.post(
        f"{API}/occupation-master/import/preview",
        headers=headers,
        files={"file": _csv_file()},
        data={"country_code": TEST_COUNTRY, "classification_type": "TEST"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert body.get("total_rows") == 2
    assert body.get("preview_token"), "preview_token missing"
    assert body.get("preview_token_expires_in_seconds") == 300
    # Token shape: <sha256>.<expiry>.<sig>
    assert body["preview_token"].count(".") == 2


def test_2_commit_without_token_returns_400(headers, cleanup_zz):
    """T2: /commit MUST 400 without preview_token."""
    r = requests.post(
        f"{API}/occupation-master/import/commit",
        headers=headers,
        files={"file": _csv_file()},
        data={
            "country_code": TEST_COUNTRY, "classification_type": "TEST",
            "classification_version": "TEST-1.0", "on_duplicate": "skip",
        },
        timeout=15,
    )
    assert r.status_code == 400, r.text
    assert "preview_token required" in r.text.lower()


def test_3_commit_with_token_creates_rows_and_batch(headers, cleanup_zz):
    """T3: Full preview→commit flow creates 2 rows + 1 batch."""
    # Preview to get token
    pr = requests.post(
        f"{API}/occupation-master/import/preview",
        headers=headers,
        files={"file": _csv_file()},
        data={"country_code": TEST_COUNTRY, "classification_type": "TEST"},
        timeout=15,
    )
    token = pr.json()["preview_token"]

    # Commit
    r = requests.post(
        f"{API}/occupation-master/import/commit",
        headers=headers,
        files={"file": _csv_file()},
        data={
            "country_code": TEST_COUNTRY, "classification_type": "TEST",
            "classification_version": "TEST-1.0", "on_duplicate": "skip",
            "preview_token": token,
        },
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert body.get("imported") == 2
    assert body.get("batch_id"), "batch_id missing in commit response"


def test_4_import_batches_lists_committed_batch(headers, cleanup_zz):
    """T4: /import-batches lists the new batch with is_revocable=True."""
    # First create one
    pr = requests.post(f"{API}/occupation-master/import/preview", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST"}, timeout=15)
    token = pr.json()["preview_token"]
    cr = requests.post(f"{API}/occupation-master/import/commit", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST",
                             "classification_version": "TEST-1.0", "on_duplicate": "skip",
                             "preview_token": token}, timeout=15)
    bid = cr.json()["batch_id"]

    r = requests.get(f"{API}/import-batches?limit=20", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    matching = [b for b in items if b["batch_id"] == bid]
    assert matching, f"batch {bid} not in list"
    b = matching[0]
    assert b["status"] == "committed"
    assert b["is_revocable"] is True
    assert b["counts"]["created"] == 2


def test_5_revoke_deletes_rows(headers, cleanup_zz):
    """T5: /revoke replays-reverse → deletes 2 created rows."""
    # Setup: commit
    pr = requests.post(f"{API}/occupation-master/import/preview", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST"}, timeout=15)
    token = pr.json()["preview_token"]
    cr = requests.post(f"{API}/occupation-master/import/commit", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST",
                             "classification_version": "TEST-1.0", "on_duplicate": "skip",
                             "preview_token": token}, timeout=15)
    bid = cr.json()["batch_id"]

    # Revoke
    r = requests.post(f"{API}/import-batches/{bid}/revoke",
                      headers=headers, json={"reason": "pytest T5 revoke"}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "revoked"
    assert body["deleted"] == 2

    # Verify rows actually gone
    list_r = requests.get(
        f"{API}/occupation-master?country={TEST_COUNTRY}&limit=10",
        headers=headers, timeout=15,
    )
    rows = list_r.json().get("items") or list_r.json().get("occupations") or []
    assert len(rows) == 0, f"Expected 0 ZZ rows after revoke, got {len(rows)}"


def test_6_double_revoke_returns_400(headers, cleanup_zz):
    """T6: Revoking an already-revoked batch must 400."""
    pr = requests.post(f"{API}/occupation-master/import/preview", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST"}, timeout=15)
    token = pr.json()["preview_token"]
    cr = requests.post(f"{API}/occupation-master/import/commit", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST",
                             "classification_version": "TEST-1.0", "on_duplicate": "skip",
                             "preview_token": token}, timeout=15)
    bid = cr.json()["batch_id"]
    requests.post(f"{API}/import-batches/{bid}/revoke",
                  headers=headers, json={"reason": "pytest T6 first revoke"}, timeout=15)
    # Second revoke
    r = requests.post(f"{API}/import-batches/{bid}/revoke",
                      headers=headers, json={"reason": "pytest T6 double revoke attempt"}, timeout=15)
    assert r.status_code == 400, r.text
    assert "already revoked" in r.text.lower()


def test_7_dedup_skip_on_existing_codes(headers, cleanup_zz):
    """T7: Re-running same file with on_duplicate=skip → 2 skipped, 0 imported."""
    # First insert
    pr = requests.post(f"{API}/occupation-master/import/preview", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST"}, timeout=15)
    token = pr.json()["preview_token"]
    requests.post(f"{API}/occupation-master/import/commit", headers=headers,
                  files={"file": _csv_file()},
                  data={"country_code": TEST_COUNTRY, "classification_type": "TEST",
                        "classification_version": "TEST-1.0", "on_duplicate": "skip",
                        "preview_token": token}, timeout=15)
    # Second insert with same file
    pr2 = requests.post(f"{API}/occupation-master/import/preview", headers=headers,
                        files={"file": _csv_file()},
                        data={"country_code": TEST_COUNTRY, "classification_type": "TEST"}, timeout=15)
    token2 = pr2.json()["preview_token"]
    r = requests.post(f"{API}/occupation-master/import/commit", headers=headers,
                      files={"file": _csv_file()},
                      data={"country_code": TEST_COUNTRY, "classification_type": "TEST",
                            "classification_version": "TEST-1.0", "on_duplicate": "skip",
                            "preview_token": token2}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["imported"] == 0, f"Expected 0 imported on re-run, got {body['imported']}"
    assert body["skipped"] == 2, f"Expected 2 skipped on re-run, got {body['skipped']}"


def test_8_force_revoke_requires_admin_override(headers, cleanup_zz):
    """T8: /force-revoke without admin_override=true → 400."""
    # Create + commit
    pr = requests.post(f"{API}/occupation-master/import/preview", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST"}, timeout=15)
    token = pr.json()["preview_token"]
    cr = requests.post(f"{API}/occupation-master/import/commit", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST",
                             "classification_version": "TEST-1.0", "on_duplicate": "skip",
                             "preview_token": token}, timeout=15)
    bid = cr.json()["batch_id"]

    r = requests.post(
        f"{API}/import-batches/{bid}/force-revoke",
        headers=headers,
        json={"reason": "pytest force revoke without override", "admin_override": False},
        timeout=15,
    )
    assert r.status_code == 400, r.text
    assert "admin_override" in r.text.lower()


def test_9_stats_has_3way_enrichment(headers):
    """T9: /occupation-master/stats returns enrichment {verified, raw_drafts, pending_enrichment, outdated}."""
    r = requests.get(f"{API}/occupation-master/stats", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    enr = body.get("enrichment")
    assert enr is not None, "enrichment sub-object missing"
    for k in ("verified", "raw_drafts", "pending_enrichment", "outdated"):
        assert k in enr, f"key {k} missing from enrichment"
        assert isinstance(enr[k], int), f"enrichment.{k} must be int"


def test_10_file_hash_mismatch_rejects_commit(headers, cleanup_zz):
    """T10: preview_token is bound to file SHA-256 — different file body → 400."""
    # Get token for original csv
    pr = requests.post(f"{API}/occupation-master/import/preview", headers=headers,
                       files={"file": _csv_file()},
                       data={"country_code": TEST_COUNTRY, "classification_type": "TEST"}, timeout=15)
    token = pr.json()["preview_token"]

    # Commit with a DIFFERENT file body (tampered)
    tampered = "code,title\nTAMPERED-1,Different body\n"
    r = requests.post(
        f"{API}/occupation-master/import/commit",
        headers=headers,
        files={"file": ("tampered.csv", BytesIO(tampered.encode()), "text/csv")},
        data={"country_code": TEST_COUNTRY, "classification_type": "TEST",
              "classification_version": "TEST-1.0", "on_duplicate": "skip",
              "preview_token": token},
        timeout=15,
    )
    assert r.status_code == 400, r.text
    assert "invalid or expired preview_token" in r.text.lower()
