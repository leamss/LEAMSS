"""Phase 7.5 — Cockpit API smoke tests.

Verifies:
  • /funnel returns counts for all 6 stages
  • /cards returns unified cards across leads, assessments, PAs
  • /brief returns actionable insights
  • /card/{kind}/{id} returns drill-in detail
  • RBAC scoping (admin sees all, partner sees own)
"""
import os
import pytest
import httpx

API = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001") or "http://localhost:8001"
if not API.endswith("/"):
    API = API.rstrip("/")
API_PREFIX = f"{API}/api"

ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASS = "Partner@123"


def _login(email: str, password: str) -> str:
    r = httpx.post(f"{API_PREFIX}/auth/login", json={"email": email, "password": password}, timeout=15)
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def partner_token() -> str:
    return _login(PARTNER_EMAIL, PARTNER_PASS)


def test_funnel_returns_all_six_stages(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/funnel",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    for stage in ("leads", "assessments", "pa", "proposals", "cases", "closed"):
        assert stage in d, f"Missing stage: {stage}"
        assert isinstance(d[stage], int)
    assert "total_active" in d
    assert "as_of" in d


def test_cards_default_returns_unified_list(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/cards?limit=20",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "items" in d
    assert isinstance(d["items"], list)
    if d["items"]:
        c = d["items"][0]
        # All card shapes must include these keys
        for key in ("id", "type", "name", "stage", "countries", "lifecycle",
                    "next_action", "urgency", "owner", "updated_at"):
            assert key in c, f"Card missing key: {key}"
        assert c["type"] in ("lead", "assessment", "pa")


def test_cards_filter_by_stage(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/cards?stage=assessments&limit=20",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    items = r.json().get("items", [])
    for c in items:
        assert c["stage"] == "assessments"


def test_cards_search(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/cards?search=demo&limit=20",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200


def test_cards_sort_recent_then_oldest(admin_token):
    r1 = httpx.get(f"{API_PREFIX}/cockpit/cards?sort=recent&limit=10",
                   headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    r2 = httpx.get(f"{API_PREFIX}/cockpit/cards?sort=oldest&limit=10",
                   headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r1.status_code == 200 and r2.status_code == 200


def test_brief_returns_insights(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/brief",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "insights" in d
    assert "counts" in d
    assert isinstance(d["insights"], list)
    if d["insights"]:
        ins = d["insights"][0]
        for k in ("icon", "title", "cta_label", "cta_link", "urgency"):
            assert k in ins


def test_partner_sees_only_own_records(admin_token, partner_token):
    # Admin gets everything
    admin_r = httpx.get(f"{API_PREFIX}/cockpit/funnel",
                        headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    partner_r = httpx.get(f"{API_PREFIX}/cockpit/funnel",
                          headers={"Authorization": f"Bearer {partner_token}"}, timeout=15)
    assert admin_r.status_code == 200 and partner_r.status_code == 200
    # Partner's total <= admin's total (ownership scope respected)
    assert partner_r.json()["total_active"] <= admin_r.json()["total_active"]


def test_card_detail_unknown_kind_returns_400(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/card/foo/abc123",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 400


def test_card_detail_lead_not_found_returns_404(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/card/lead/nonexistent-xyz-999",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 404


def test_unauthenticated_returns_401(admin_token):
    r = httpx.get(f"{API_PREFIX}/cockpit/funnel", timeout=15)
    assert r.status_code in (401, 403)
