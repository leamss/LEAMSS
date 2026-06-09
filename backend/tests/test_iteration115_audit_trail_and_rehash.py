"""Phase 6.8 — Audit Trail endpoint + Legacy rehash backfill tests."""
import os
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://compliance-hub-751.preview.emergentagent.com"
BASE = f"{API}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    return r.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _seed(headers):
    a = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "TEST_AUDIT_EP",
        "client_email": "audit_ep@test.com",
        "profile": {"marital_status": "single", "primary_applicant": {"personal": {"age": 30}, "education": {"highest_qualification": "bachelor"}}},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=headers, timeout=15).json()
    s = requests.post(f"{BASE}/sales/assessments/{a['id']}/share", json={"expires_in_days": 30}, headers=headers, timeout=10).json()
    return a["id"], s["token"]


# ════════════════════════════════════════════════════════════════
# Audit-trail endpoint
# ════════════════════════════════════════════════════════════════
def test_audit_trail_full_lifecycle(admin_headers):
    aid, tok = _seed(admin_headers)
    # Access twice
    requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=10)
    requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=10)
    # Revoke
    requests.post(f"{BASE}/share-links/revoke", json={"type": "sales_report", "token": tok, "reason": "audit-test"}, headers=admin_headers, timeout=10)

    r = requests.get(f"{BASE}/share-links/{tok}/audit-trail", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["count"] >= 4  # generated + 2 accesses + revoked
    assert d["access_count"] == 2
    assert d["revoked"] is True
    types = [e["event_type"] for e in d["events"]]
    assert "share_generated" in types
    assert "share_accessed" in types
    assert "share_revoked" in types
    # All integrity verified
    assert all(e["integrity_status"] == "verified" for e in d["events"])
    # Timeline ordered chronologically
    timestamps = [e["created_at"] for e in d["events"]]
    assert timestamps == sorted(timestamps)
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_audit_trail_unknown_token_404(admin_headers):
    r = requests.get(f"{BASE}/share-links/DOESNOTEXIST/audit-trail", headers=admin_headers, timeout=10)
    assert r.status_code == 404


def test_audit_trail_admin_only(admin_headers):
    aid, tok = _seed(admin_headers)
    # Try as partner
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code == 200:
        r = requests.get(f"{BASE}/share-links/{tok}/audit-trail", headers={"Authorization": f"Bearer {p.json()['token']}"}, timeout=10)
        assert r.status_code == 403
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_audit_trail_access_tracks_ip_and_ua(admin_headers):
    aid, tok = _seed(admin_headers)
    requests.get(f"{BASE}/sales/assessments/public/{tok}", headers={"User-Agent": "TestBot/1.0"}, timeout=10)
    r = requests.get(f"{BASE}/share-links/{tok}/audit-trail", headers=admin_headers, timeout=10)
    access_events = [e for e in r.json()["events"] if e["event_type"] == "share_accessed"]
    assert any("TestBot" in (e.get("user_agent") or "") for e in access_events)
    assert any(e.get("ip_address") for e in access_events)
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


# ════════════════════════════════════════════════════════════════
# Legacy rehash backfill
# ════════════════════════════════════════════════════════════════
def test_rehash_legacy_dry_run(admin_headers):
    r = requests.post(f"{BASE}/legal-archive/integrity/rehash-legacy?dry_run=true", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["dry_run"] is True
    assert d["total_scanned"] == d["verified"] + d["rehashed"] + d["force_rehashed"] + d["still_tampered"]
    assert d["verified"] >= 1  # at least the share events we just created


def test_rehash_legacy_does_not_break_verified(admin_headers):
    # Run live (not force) — should not change verified counts in subsequent verify-all
    before = requests.get(f"{BASE}/legal-archive/integrity/verify-all", headers=admin_headers, timeout=15).json()
    requests.post(f"{BASE}/legal-archive/integrity/rehash-legacy", headers=admin_headers, timeout=20)
    after = requests.get(f"{BASE}/legal-archive/integrity/verify-all", headers=admin_headers, timeout=15).json()
    # Verified count must not decrease
    assert after["verified"] >= before["verified"]


def test_rehash_legacy_admin_only():
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    r = requests.post(f"{BASE}/legal-archive/integrity/rehash-legacy", headers={"Authorization": f"Bearer {p.json()['token']}"}, timeout=10)
    assert r.status_code == 403
