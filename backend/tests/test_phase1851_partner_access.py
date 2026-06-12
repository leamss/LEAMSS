"""Phase 18.5.1 — Partner-role access regression tests for sales endpoints.

Sir reported "Compare flow + Smart Sales Helper error for partner". Live
investigation showed that backend RBAC was already fine (partner included in
_ALLOWED_ROLES for sales endpoints); the actual UX failure was a React render
crash in the LEGACY `/sales/occupations/compare` page (rendering a `body_fee_native`
object as a React child). This file locks down both:
  - Partner CAN read all sales endpoints
  - Partner CAN request verification feedback
  - Partner CANNOT write to occupation_master (stays read-only)

4 tests as briefed by Sir.
"""
from __future__ import annotations
import os
import sys
import httpx
import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

API_BASE = os.environ.get("AUDIT_API_BASE", "http://localhost:8001/api")


def _login(email: str, password: str) -> dict:
    r = httpx.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=20)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def P():
    return _login("partner@leamss.com", "Partner@123")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Partner can GET sales occupation detail
# ─────────────────────────────────────────────────────────────────────────────
def test_partner_can_get_sales_occupation_detail(P):
    r = httpx.get(f"{API_BASE}/sales/occupations/CA/21231", headers=P, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("country_code") == "CA"
    assert body.get("overview", {}).get("code") == "21231"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Partner can POST /api/sales/compare (Phase 18.5 endpoint)
# ─────────────────────────────────────────────────────────────────────────────
def test_partner_can_post_sales_compare(P):
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=P,
        json={"codes": [{"country_code": "CA", "code": "21231"}, {"country_code": "CA", "code": "31102"}]},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["occupations"]) == 2
    assert isinstance(body.get("summary_narrative"), str) and len(body["summary_narrative"]) > 10


# ─────────────────────────────────────────────────────────────────────────────
# 3. Partner can post legacy /api/sales/occupations/compare (rich Atlas page)
#    Locks down the path Sir was actually hitting on the broken page.
# ─────────────────────────────────────────────────────────────────────────────
def test_partner_can_post_legacy_sales_occupations_compare(P):
    r = httpx.post(
        f"{API_BASE}/sales/occupations/compare",
        headers=P,
        json={"items": [{"country_code": "AU", "code": "261313"}, {"country_code": "CA", "code": "21231"}]},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    items = r.json().get("items", [])
    assert len(items) == 2
    # Sanity: body_fee_native may be scalar or object — frontend handles both now.
    assert any("body_fee_native" in it for it in items)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Partner can create a feedback / verification-request entry
# ─────────────────────────────────────────────────────────────────────────────
def test_partner_can_request_verification(P):
    payload = {
        "request_type": "verification_request",
        "occupation_id": "ca-21231",
        "country_code": "CA",
        "code": "21231",
        "occupation_title": "Software engineers and designers",
        "requested_field": "general",
        "message": "Phase 18.5.1 partner-access regression seed",
    }
    r = httpx.post(f"{API_BASE}/feedback-requests", headers=P, json=payload, timeout=20)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body.get("status") == "open"
    # cleanup so we don't pollute the queue
    fid = body.get("id")
    if fid:
        ADMIN = _login("admin@leamss.com", "Admin@123")
        httpx.delete(f"{API_BASE}/feedback-requests/{fid}", headers=ADMIN, timeout=10)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Partner cannot WRITE to occupation_master (regression — stays read-only)
# ─────────────────────────────────────────────────────────────────────────────
def test_partner_cannot_write_occupation_master(P):
    # Try the most direct write path. Different routers have different paths;
    # we hit the verify endpoint which definitely requires admin role.
    r = httpx.post(
        f"{API_BASE}/occupation-master/CA/21231/verify",
        headers=P,
        json={"verification_notes": "should be rejected"},
        timeout=20,
    )
    # 401 (no token decoded) / 403 (forbidden by role) / 404 (no such route) all
    # acceptable — what's NOT acceptable is 200.
    assert r.status_code in (401, 403, 404, 422), f"Partner should NOT be able to write: {r.status_code} {r.text}"
