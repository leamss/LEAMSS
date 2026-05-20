"""Phase 6.9b — IP Geo + Anomaly Alerts + Audit Insights tests."""
import os
import time
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
        "client_name": "TEST_P69B",
        "profile": {"marital_status": "single", "primary_applicant": {"personal": {"age": 30}, "education": {"highest_qualification": "bachelor"}}},
        "targets": [{"country": "AU"}],
    }, headers=headers, timeout=15).json()
    s = requests.post(f"{BASE}/sales/assessments/{a['id']}/share", json={"expires_in_days": 7}, headers=headers, timeout=10).json()
    return a["id"], s["token"]


# ════════════════════════════════════════════════════════════════
# Audit Insights Overview
# ════════════════════════════════════════════════════════════════
def test_insights_overview_returns_expected_keys(admin_headers):
    r = requests.get(f"{BASE}/audit-insights/overview?days=30", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    expected = {"window_days", "total_events", "by_event_type", "by_share_type", "trend",
                "top_anomalies", "anomaly_summary", "top_ips", "recent_alerts", "unique_ips", "unique_tokens"}
    assert expected.issubset(d.keys())
    assert d["window_days"] == 30
    # trend should have N+1 days
    assert len(d["trend"]) == 31
    # anomaly summary structure
    assert set(d["anomaly_summary"].keys()) == {"high", "medium", "low"}


def test_insights_overview_admin_only():
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    r = requests.get(f"{BASE}/audit-insights/overview", headers={"Authorization": f"Bearer {p.json()['token']}"}, timeout=10)
    assert r.status_code == 403


# ════════════════════════════════════════════════════════════════
# Anomaly Alerts Feed
# ════════════════════════════════════════════════════════════════
def test_alerts_feed_dispatch_dedup(admin_headers):
    """Triggering /anomalies twice should NOT create duplicate alerts within 1 hour."""
    aid, tok = _seed(admin_headers)
    # 12 rapid accesses → rapid_burst
    for _ in range(12):
        try:
            requests.get(f"{BASE}/sales/assessments/public/{tok}", timeout=10)
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.1)
    # First call — should dispatch (if high severity)
    r1 = requests.get(f"{BASE}/share-links/anomalies?since_hours=1&auto_alert=true", headers=admin_headers, timeout=15)
    # Second call — should dedupe (if dispatched)
    r2 = requests.get(f"{BASE}/share-links/anomalies?since_hours=1&auto_alert=true", headers=admin_headers, timeout=15)
    # If first dispatched any high, second should have deduped count >= 1
    d1 = r1.json().get("alert_dispatch", {})
    d2 = r2.json().get("alert_dispatch", {})
    if d1.get("sent", 0) > 0:
        assert d2.get("deduped", 0) >= 1
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_alerts_feed_listing(admin_headers):
    r = requests.get(f"{BASE}/share-links/anomaly-alerts?limit=10", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert "items" in d and "count" in d


def test_alert_acknowledge(admin_headers):
    # Find any unacknowledged alert
    r = requests.get(f"{BASE}/share-links/anomaly-alerts?acknowledged=false&limit=1", headers=admin_headers, timeout=10)
    items = r.json().get("items", [])
    if not items:
        pytest.skip("No unacknowledged alerts to test")
    aid = items[0]["id"]
    ack = requests.post(f"{BASE}/share-links/anomaly-alerts/{aid}/acknowledge", headers=admin_headers, timeout=10)
    assert ack.status_code == 200
    # Verify it's now acknowledged
    r2 = requests.get(f"{BASE}/share-links/anomaly-alerts?limit=50", headers=admin_headers, timeout=10)
    found = next((it for it in r2.json()["items"] if it["id"] == aid), None)
    assert found and found["acknowledged"] is True


def test_alert_acknowledge_unknown_404(admin_headers):
    r = requests.post(f"{BASE}/share-links/anomaly-alerts/NONEXISTENT/acknowledge", headers=admin_headers, timeout=10)
    assert r.status_code == 404


# ════════════════════════════════════════════════════════════════
# Compliance Report PDF
# ════════════════════════════════════════════════════════════════
def test_compliance_pdf_generation(admin_headers):
    r = requests.get(f"{BASE}/audit-insights/compliance-report.pdf?days=90", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert len(r.content) >= 2000


def test_compliance_pdf_admin_only():
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    r = requests.get(f"{BASE}/audit-insights/compliance-report.pdf", headers={"Authorization": f"Bearer {p.json()['token']}"}, timeout=10)
    assert r.status_code == 403


# ════════════════════════════════════════════════════════════════
# IP Geo helper (unit-level)
# ════════════════════════════════════════════════════════════════
def test_ip_geo_private_ip_returns_none():
    """Private/loopback IPs should not trigger any geo lookup."""
    import asyncio
    from core.ip_geo import lookup_ip
    result = asyncio.run(lookup_ip("127.0.0.1"))
    assert result is None
    result2 = asyncio.run(lookup_ip("10.0.0.1"))
    assert result2 is None
    result3 = asyncio.run(lookup_ip(""))
    assert result3 is None


def test_haversine_distance():
    """Sanity check the haversine math used by impossible_geo detection."""
    from core.ip_geo import haversine_km
    # Delhi → New York ≈ 11,750 km
    d = haversine_km(28.7, 77.1, 40.7, -74.0)
    assert 11000 < d < 12500
    # Same point = 0
    assert haversine_km(40.7, -74.0, 40.7, -74.0) < 0.01
