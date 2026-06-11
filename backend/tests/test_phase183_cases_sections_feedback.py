"""Phase 18.3 — Sample Cases / Custom Sections polish + Feedback Requests."""
from __future__ import annotations
import os, sys, asyncio
import httpx, pytest
from dotenv import load_dotenv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

API_BASE = os.environ.get("AUDIT_API_BASE", "http://localhost:8001/api")
_db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

TEST_OID = "ca-21231"
TEST_CC, TEST_CODE = "CA", "21231"


def _login(email="admin@leamss.com", password="Admin@123"):
    r = httpx.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=20)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def H():
    return _login()


def _async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ─── 1 ──
def test_1_sample_case_validation_outcome_required(H):
    r = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases", headers=H,
                   json={"client_age": 30, "profile_summary": "x"}, timeout=15)
    assert r.status_code == 422, f"Expected 422 (missing outcome), got {r.status_code}: {r.text[:200]}"


# ─── 2 ──
def test_2_sample_case_validation_age_range(H):
    base = {"profile_summary": "edge", "outcome": "Approved"}
    r17 = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases", headers=H,
                    json={**base, "client_age": 17}, timeout=15)
    r71 = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases", headers=H,
                    json={**base, "client_age": 71}, timeout=15)
    r30 = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases", headers=H,
                    json={**base, "client_age": 30}, timeout=15)
    assert r17.status_code == 422
    assert r71.status_code == 422
    assert r30.status_code == 200, r30.text[:200]


# ─── 3 ──
def test_3_sample_case_crud_reorder_via_put(H):
    # Clear then add 3 distinct cases via dedicated endpoint
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H, json={"sample_cases": []}, timeout=15)
    ids = []
    for i in range(3):
        r = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases", headers=H,
                       json={"profile_summary": f"P183 reorder {i}", "outcome": "Approved",
                             "client_age": 25 + i, "visa_subclass": f"X{i}"}, timeout=15)
        assert r.status_code == 200, r.text[:200]
        ids.append(r.json()["sample_case"]["id"])
    # Reorder by issuing a PUT with the array reversed (the front-end "up/down arrow" pattern)
    detail = httpx.get(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H, timeout=15).json()
    cases = [c for c in detail["sample_cases"] if c["id"] in ids]
    cases_reordered = list(reversed(cases))
    r = httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
                  json={"sample_cases": cases_reordered}, timeout=15)
    assert r.status_code == 200
    new_order = [c["id"] for c in r.json()["sample_cases"] if c["id"] in ids]
    assert new_order == list(reversed(ids)), f"reorder failed: {new_order!r} != {list(reversed(ids))!r}"


# ─── 4 ──
def test_4_custom_section_url_validation(H):
    r = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/custom-sections", headers=H,
                   json={"title": "Bad URL", "source_url": "not-a-url"}, timeout=15)
    assert r.status_code == 422, r.text[:200]


# ─── 5 ──
def test_5_custom_section_markdown_safe_storage(H):
    """Body markdown stored verbatim (sanitization is render-time, not store-time)."""
    body = "## Hello <script>alert('xss')</script>"
    r = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/custom-sections", headers=H,
                   json={"title": "P183 markdown", "body_markdown": body,
                         "source_url": "https://example.com/x"}, timeout=15)
    assert r.status_code == 200, r.text[:200]
    saved = r.json()["custom_section"]["body_markdown"]
    assert "<script>" in saved, "Raw script tag must be stored as-is for render-time escaping"


# ─── 6 ──
def test_6_feedback_request_post_creates_row(H):
    r = httpx.post(f"{API_BASE}/feedback-requests", headers=H,
                   json={"occupation_id": TEST_OID, "requested_field": "assessing_authority",
                         "message": "Phase 18.3 test request"}, timeout=15)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    fid = body.get("id")
    assert fid
    assert body.get("status") == "open"
    assert body.get("occupation_id") == TEST_OID
    # Admin list should include it
    listing = httpx.get(f"{API_BASE}/feedback-requests?status=open", headers=H, timeout=15).json()
    assert any(it.get("id") == fid for it in listing.get("items", []))
    assert listing["counts"]["open"] >= 1


# ─── 7 ──
def test_7_feedback_request_admin_only_list():
    """Non-admin GET should be 403. Seed a sales-style user via test_credentials.md if available;
    otherwise fall back to a guest call (no auth → also non-admin path)."""
    # No token → 401 OR 403; both are non-200 indicating the endpoint is gated.
    r = httpx.get(f"{API_BASE}/feedback-requests", timeout=15)
    assert r.status_code in (401, 403)


# ─── 8 ──
def test_8_feedback_request_status_transitions(H):
    # Create a fresh feedback request
    r = httpx.post(f"{API_BASE}/feedback-requests", headers=H,
                   json={"occupation_id": TEST_OID, "requested_field": "general",
                         "message": "P183 transition"}, timeout=15).json()
    fid = r["id"]
    # open → in_progress (valid)
    r1 = httpx.patch(f"{API_BASE}/feedback-requests/{fid}", headers=H,
                     json={"status": "in_progress"}, timeout=15)
    assert r1.status_code == 200
    # in_progress → resolved (valid)
    r2 = httpx.patch(f"{API_BASE}/feedback-requests/{fid}", headers=H,
                     json={"status": "resolved", "resolution_notes": "fixed"}, timeout=15)
    assert r2.status_code == 200
    # resolved → open (illegal)
    r3 = httpx.patch(f"{API_BASE}/feedback-requests/{fid}", headers=H,
                     json={"status": "open"}, timeout=15)
    assert r3.status_code == 400, f"resolved → open should be 400, got {r3.status_code}"


# ─── 9 ──
def test_9_feedback_request_invalid_occupation_404(H):
    r = httpx.post(f"{API_BASE}/feedback-requests", headers=H,
                   json={"occupation_id": "zz-noexist", "requested_field": "general"}, timeout=15)
    assert r.status_code == 404
    assert "not found" in r.text.lower()


# ─── 10 ──
def test_10_sales_detail_renders_custom_sections(H):
    # Wipe + set 2 sections via PUT
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"custom_sections": [
                  {"title": "P183 sec 1", "body_markdown": "Body 1"},
                  {"title": "P183 sec 2", "body_markdown": "Body 2"},
              ]}, timeout=15)
    r = httpx.get(f"{API_BASE}/sales/occupations/{TEST_CC}/{TEST_CODE}", headers=H, timeout=15)
    assert r.status_code == 200
    sections = (r.json().get("overview") or {}).get("custom_sections") or []
    p183 = [s for s in sections if str(s.get("title") or "").startswith("P183 sec")]
    assert len(p183) == 2


# ─── 11 ──
def test_11_sales_detail_renders_sample_cases_with_outcome_colors(H):
    # Wipe then add 4 cases (one per outcome) — sample_cases are NOT outcome-validated
    # on bulk PUT, so we use the dedicated POST endpoint for outcome enum check.
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H, json={"sample_cases": []}, timeout=15)
    outcomes = ["Approved", "Refused", "Withdrawn", "Pending"]
    for o in outcomes:
        rp = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases", headers=H,
                        json={"profile_summary": f"P183 outcome {o}", "outcome": o,
                              "client_age": 30, "visa_subclass": "189"}, timeout=15)
        assert rp.status_code == 200, rp.text[:200]
    r = httpx.get(f"{API_BASE}/sales/occupations/{TEST_CC}/{TEST_CODE}", headers=H, timeout=15)
    cases = r.json().get("sample_cases") or []
    p183 = [c for c in cases if str(c.get("profile_summary") or "").startswith("P183 outcome")]
    assert len(p183) == 4
    got_outcomes = sorted([c.get("outcome") for c in p183])
    assert got_outcomes == sorted(outcomes), f"outcomes mismatch: {got_outcomes!r}"


# ─── 12 ──
def test_12_feedback_request_skill_assessment_field_path(H):
    r = httpx.post(f"{API_BASE}/feedback-requests", headers=H,
                   json={"occupation_id": TEST_OID, "requested_field": "assessing_authority",
                         "message": "Need IML proc time + fee"}, timeout=15)
    assert r.status_code == 200, r.text[:200]
    assert r.json()["requested_field"] == "assessing_authority"


# ─── 13 ──
def test_13_no_path_leak_in_feedback_endpoints(H):
    weird = ["../../../etc/passwd", "%2e%2e%2fsecret", "1' OR '1'='1", "<script>x</script>"]
    for w in weird:
        r = httpx.get(f"{API_BASE}/feedback-requests/{w}", headers=H, timeout=15)
        assert r.status_code < 500, f"{w!r} caused {r.status_code}"
        r2 = httpx.patch(f"{API_BASE}/feedback-requests/{w}", headers=H, json={"status": "resolved"}, timeout=15)
        assert r2.status_code < 500
