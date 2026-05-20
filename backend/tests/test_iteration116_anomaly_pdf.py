"""Phase 6.9 — Anomaly Detection + PDF Audit Report tests."""
import os
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://staff-dashboard-66.preview.emergentagent.com"
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
        "client_name": "TEST_P69",
        "profile": {"marital_status": "single", "primary_applicant": {"personal": {"age": 30}, "education": {"highest_qualification": "bachelor"}}},
        "targets": [{"country": "AU"}],
    }, headers=headers, timeout=15).json()
    s = requests.post(f"{BASE}/sales/assessments/{a['id']}/share", json={"expires_in_days": 7}, headers=headers, timeout=10).json()
    return a["id"], s["token"]


# ════════════════════════════════════════════════════════════════
# Anomalies endpoint
# ════════════════════════════════════════════════════════════════
def test_anomaly_rapid_burst_detection(admin_headers):
    aid, tok = _seed(admin_headers)
    # 12 rapid accesses (above threshold of 10) → should trigger rapid_burst
    import time
    for _ in range(12):
        try:
            requests.get(f"{BASE}/sales/assessments/public/{tok}", headers={"User-Agent": "TestRapid/1.0"}, timeout=10)
        except requests.exceptions.RequestException:
            pass  # tolerate transient network errors during burst
        time.sleep(0.1)
    r = requests.get(f"{BASE}/share-links/anomalies?since_hours=1", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    flagged = next((a for a in d["anomalies"] if a.get("share_token") == tok), None)
    assert flagged is not None
    types = [f["type"] for f in flagged["flags"]]
    assert "rapid_burst" in types
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_anomaly_post_revoke_scrape(admin_headers):
    aid, tok = _seed(admin_headers)
    # 2 normal accesses → revoke → 3 denied attempts
    requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=5)
    requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=5)
    requests.post(f"{BASE}/share-links/revoke", json={"type": "sales_report", "token": tok, "reason": "p69"}, headers=admin_headers, timeout=10)
    for _ in range(3):
        requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=5)
    r = requests.get(f"{BASE}/share-links/anomalies?since_hours=1", headers=admin_headers, timeout=10)
    flagged = next((a for a in r.json()["anomalies"] if a.get("share_token") == tok), None)
    assert flagged is not None
    assert "post_revoke_scrape" in [f["type"] for f in flagged["flags"]]
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_anomaly_severity_aggregation(admin_headers):
    r = requests.get(f"{BASE}/share-links/anomalies?since_hours=1", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert "summary" in d
    assert set(d["summary"].keys()) == {"high", "medium", "low"}
    assert d["scanned_events"] >= 0
    assert d["scanned_tokens"] >= 0


def test_anomaly_admin_only():
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    r = requests.get(f"{BASE}/share-links/anomalies", headers={"Authorization": f"Bearer {p.json()['token']}"}, timeout=10)
    assert r.status_code == 403


# ════════════════════════════════════════════════════════════════
# Audit trail returns anomaly inline
# ════════════════════════════════════════════════════════════════
def test_audit_trail_includes_anomalies(admin_headers):
    aid, tok = _seed(admin_headers)
    import time
    for _ in range(12):
        try:
            requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=10)
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.1)
    r = requests.get(f"{BASE}/share-links/{tok}/audit-trail", headers=admin_headers, timeout=15)
    d = r.json()
    assert d["anomaly_severity"] in ("medium", "high")
    assert any(f["type"] == "rapid_burst" for f in d.get("anomalies", []))
    assert d["denied_count"] == 0
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


# ════════════════════════════════════════════════════════════════
# PDF export
# ════════════════════════════════════════════════════════════════
def test_pdf_export_returns_binary(admin_headers):
    aid, tok = _seed(admin_headers)
    requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=5)
    r = requests.get(f"{BASE}/share-links/{tok}/audit-trail.pdf", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert len(r.content) >= 2000  # at least 2KB
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_pdf_export_404_for_unknown_token(admin_headers):
    r = requests.get(f"{BASE}/share-links/UNKNOWN_TOKEN_XYZ/audit-trail.pdf", headers=admin_headers, timeout=10)
    assert r.status_code == 404


def test_pdf_export_admin_only():
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    r = requests.get(f"{BASE}/share-links/anytoken/audit-trail.pdf", headers={"Authorization": f"Bearer {p.json()['token']}"}, timeout=10)
    assert r.status_code == 403


# ════════════════════════════════════════════════════════════════
# Denied access logging (scraping signal)
# ════════════════════════════════════════════════════════════════
def test_denied_access_is_audit_logged(admin_headers):
    aid, tok = _seed(admin_headers)
    # Revoke immediately
    requests.post(f"{BASE}/share-links/revoke", json={"type": "sales_report", "token": tok, "reason": "p69-denied-test"}, headers=admin_headers, timeout=10)
    # Hit the now-revoked link
    r = requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=5)
    assert r.status_code == 410
    # Audit trail should contain a denied event
    trail = requests.get(f"{BASE}/share-links/{tok}/audit-trail", headers=admin_headers, timeout=10).json()
    denied = [e for e in trail["events"] if e["event_type"] == "share_access_denied"]
    assert len(denied) >= 1
    assert denied[-1]["details"]["reason"] == "revoked"
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)
