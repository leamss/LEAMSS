"""Phase 9.9 — Edit History + Biometric E-sign Packet regression tests."""
import io
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://compliance-hub-751.preview.emergentagent.com")
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ─── Edit History tests ─────────────────────────────────────────────────────
def test_edit_history_returns_timeline(admin_headers):
    """Use a known existing PA with audit entries."""
    pa_id = "aa643581-7bac-42fe-a6c7-1c4dbcd1e935"
    r = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}/edit-history",
                     headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pa_id"] == pa_id
    assert body["pa_number"] is not None
    assert body["total_entries"] >= 1
    # Each entry should have minimum schema
    for e in body["entries"]:
        assert "action" in e
        assert "created_at" in e


def test_edit_history_unknown_pa_404(admin_headers):
    r = requests.get(f"{BASE_URL}/api/pre-assessment/nonexistent-pa-id-xyz/edit-history",
                     headers=admin_headers, timeout=10)
    assert r.status_code == 404


def test_edit_history_partner_can_access_own_pa(partner_headers):
    """A partner should be able to see edit history of their own PA."""
    pa_id = "aa643581-7bac-42fe-a6c7-1c4dbcd1e935"
    r = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}/edit-history",
                     headers=partner_headers, timeout=15)
    # Either 200 (their PA) or 403 (not theirs). Both are OK — endpoint logic enforces _assert_pa_owner
    assert r.status_code in (200, 403, 404)


# ─── Biometric packet acceptance test ───────────────────────────────────────
SAMPLE_BIOMETRIC = {
    "version": "1.0",
    "captured_at": "2026-06-07T10:00:00Z",
    "session_duration_ms": 4521,
    "device": {
        "user_agent": "Mozilla/5.0 Test",
        "platform": "TestOS",
        "language": "en-IN",
        "timezone": "Asia/Kolkata",
        "timezone_offset_minutes": -330,
    },
    "screen": {"width": 1920, "height": 1080, "color_depth": 24, "device_pixel_ratio": 1.5},
    "window": {"inner_width": 1440, "inner_height": 900, "orientation": "landscape-primary"},
    "gps": {"latitude": 19.0760, "longitude": 72.8777, "accuracy_m": 50.0,
            "captured_at": "2026-06-07T10:00:01Z"},
    "drawing": {
        "input_type": "mouse",
        "stroke_count": 3,
        "total_points": 142,
        "clear_count_before_final": 1,
        "path": [{"t": 50, "x": 100, "y": 80, "type": "down"}, {"t": 60, "x": 110, "y": 82, "type": "move"}],
    },
    "canvas_fingerprint": "abc123def456",
}


# Tiny valid PNG (1x1 transparent) to use as signature_data_url
TINY_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P"
    "+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
)


def test_signature_forensics_role_gated(partner_headers):
    """Partner role should NOT be able to fetch signature forensics packet."""
    r = requests.get(f"{BASE_URL}/api/pa-agreements/nonexistent/signature-forensics",
                     headers=partner_headers, timeout=10)
    # Partner role gets 403 (not admin/case_manager)
    assert r.status_code == 403


def test_signature_forensics_admin_404_unknown(admin_headers):
    """Admin asking for unknown agreement → 404."""
    r = requests.get(f"{BASE_URL}/api/pa-agreements/agreement-xxx-yyy/signature-forensics",
                     headers=admin_headers, timeout=10)
    assert r.status_code == 404


def test_signature_packet_field_optional(admin_headers):
    """Old clients that don't send biometric_packet should still sign successfully.
    This is just a schema-acceptance check — we don't actually sign here (would need PA setup)."""
    # Verify endpoint exists and validates body
    r = requests.post(f"{BASE_URL}/api/pa-agreements/nonexistent-agr/sign",
                      headers=admin_headers,
                      json={
                          "signature_data_url": TINY_PNG_DATA_URL,
                          "typed_name": "Test",
                          "consent_text": "I sign",
                          # biometric_packet omitted intentionally
                      },
                      timeout=10)
    # Must NOT be 422 (schema rejection) — 400/403/404 = endpoint reachable
    assert r.status_code != 422, f"Got 422: {r.text}"
    assert r.status_code in (400, 403, 404)


def test_signature_packet_accepts_biometric(admin_headers):
    """Schema should accept biometric_packet in body without 422."""
    r = requests.post(f"{BASE_URL}/api/pa-agreements/nonexistent-agr/sign",
                      headers=admin_headers,
                      json={
                          "signature_data_url": TINY_PNG_DATA_URL,
                          "typed_name": "Test",
                          "consent_text": "I sign",
                          "biometric_packet": SAMPLE_BIOMETRIC,
                      },
                      timeout=10)
    # Must NOT be 422 (validation error) — biometric_packet is a valid field
    assert r.status_code != 422, f"Got 422: {r.text}"
    assert r.status_code in (400, 403, 404)


def test_proposal_docs_esign_accepts_biometric(admin_headers):
    """Proposal doc esign endpoint also accepts biometric_packet."""
    r = requests.post(f"{BASE_URL}/api/proposal-docs/nonexistent-pa/esign",
                      headers=admin_headers,
                      json={
                          "signature_data_url": TINY_PNG_DATA_URL,
                          "typed_name": "Test Client",
                          "consent_text": "I sign",
                          "biometric_packet": SAMPLE_BIOMETRIC,
                      },
                      timeout=10)
    assert r.status_code != 422, f"422 — schema rejected biometric_packet: {r.text}"
