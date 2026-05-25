"""Iteration 114 — verify Cockpit brief cta_link and card detail deep_link
use the corrected (existing) frontend routes after Phase 7.5 sanity fix.

Old broken routes (should NOT appear): /admin/leads, /admin/cases,
/admin/pre-assessments, /admin/verification-hub, /admin/share-links,
/admin/country-templates, /sales/assessments
New valid routes: /admin?tab=..., /admin/verify-hub, /sales/my-assessments,
/sales/client-assessment, /admin/kb/occupation-master, /admin/cockpit
"""
import os
import httpx
import pytest

API = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/")
API_PREFIX = f"{API}/api"

ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"

BAD_PATTERNS = (
    "/admin/leads",
    "/admin/cases",
    "/admin/pre-assessments",
    "/admin/verification-hub",
    "/admin/share-links",
    "/admin/country-templates",
    "/sales/assessments",
)


@pytest.fixture(scope="module")
def admin_token() -> str:
    r = httpx.post(f"{API_PREFIX}/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    r.raise_for_status()
    return r.json()["token"]


# ------- /api/cockpit/brief: cta_links must use valid routes -------
def test_brief_cta_links_use_valid_routes(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/brief",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    insights = r.json().get("insights", [])
    assert isinstance(insights, list)
    for ins in insights:
        link = ins.get("cta_link", "")
        assert link, f"insight missing cta_link: {ins}"
        for bad in BAD_PATTERNS:
            assert not link.startswith(bad), \
                f"insight '{ins.get('title')}' still uses broken route {link}"
        # Must be one of the known valid prefixes
        assert (
            link.startswith("/admin?tab=")
            or link.startswith("/admin/verify-hub")
            or link.startswith("/sales/my-assessments")
            or link.startswith("/sales/client-assessment")
            or link.startswith("/admin/kb/")
            or link.startswith("/admin/cockpit")
            or link == "/admin"
        ), f"insight cta_link uses unknown route: {link}"


# ------- /api/cockpit/card/pa/{id}: deep_link must point to /admin?tab=pre-assessments -------
def test_pa_card_detail_deep_link_is_admin_tab(admin_token):
    # Fetch a real PA id from /cards
    r = httpx.get(f"{API_PREFIX}/cockpit/cards?stage=pa&limit=5",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    items = r.json().get("items", [])
    if not items:
        pytest.skip("No PA cards available in seed data")
    pa_id = items[0]["id"]
    r2 = httpx.get(f"{API_PREFIX}/cockpit/card/pa/{pa_id}",
                   headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r2.status_code == 200, r2.text
    detail = r2.json()
    assert "deep_link" in detail
    assert detail["deep_link"] == "/admin?tab=pre-assessments", \
        f"PA deep_link is wrong: {detail['deep_link']}"


# ------- /api/cockpit/card/assessment/{id}: deep_link must point to /sales/client-assessment?id= -------
def test_assessment_card_detail_deep_link(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/cards?stage=assessments&limit=5",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    items = r.json().get("items", [])
    if not items:
        pytest.skip("No assessment cards available in seed data")
    aid = items[0]["id"]
    r2 = httpx.get(f"{API_PREFIX}/cockpit/card/assessment/{aid}",
                   headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r2.status_code == 200, r2.text
    detail = r2.json()
    assert "deep_link" in detail
    assert detail["deep_link"].startswith("/sales/client-assessment"), \
        f"assessment deep_link wrong: {detail['deep_link']}"
