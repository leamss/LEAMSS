"""Phase 15 — Public Pages Manager admin tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://compliance-hub-751.preview.emergentagent.com")
ADMIN = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER = {"email": "partner@leamss.com", "password": "Partner@123"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ─── URLs browser ───────────────────────────────────────────────────────────

def test_urls_list_returns_all_kinds(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin-public-pages/urls?limit=100", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] > 100
    kinds = {it["kind"] for it in d["items"]}
    assert "landing" in kinds or "hub" in kinds
    assert "occupation" in kinds


def test_urls_list_country_filter(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin-public-pages/urls?country=NZ&limit=50", headers=admin_headers, timeout=15)
    items = r.json()["items"]
    occ = [it for it in items if it["kind"] == "occupation"]
    assert all(it["country_code"] == "NZ" for it in occ), "Country filter failed"


def test_urls_partner_blocked(partner_headers):
    r = requests.get(f"{BASE_URL}/api/admin-public-pages/urls", headers=partner_headers, timeout=15)
    assert r.status_code in (401, 403)


def test_qr_generation(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/admin-public-pages/qr",
        json={"url": "https://compliance-hub-751.preview.emergentagent.com/atlas/au/261313"},
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["data_url"].startswith("data:image/png;base64,")
    assert len(d["data_url"]) > 500


def test_qr_invalid_url_400(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/admin-public-pages/qr",
        json={"url": "not-a-url"},
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 400


# ─── Content editor ─────────────────────────────────────────────────────────

def test_get_content_all_sections(admin_headers):
    for section in ["hero", "featured_codes", "testimonials", "faqs", "trust_strip"]:
        r = requests.get(f"{BASE_URL}/api/admin-public-pages/content/{section}", headers=admin_headers, timeout=15)
        assert r.status_code == 200, f"{section} failed: {r.text}"
        d = r.json()
        assert d["section"] == section
        assert "data" in d
        assert isinstance(d["is_default"], bool)


def test_get_content_unknown_400(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin-public-pages/content/foo", headers=admin_headers, timeout=15)
    assert r.status_code == 400


def test_put_hero_roundtrip(admin_headers):
    payload = {"data": {
        "eyebrow": "TEST EYEBROW",
        "title_line1": "Test Line 1",
        "title_line2": "test green",
        "title_line3_accent": "test orange.",
        "subtitle": "Test subtitle text",
        "cta_primary": "Start Quiz",
        "cta_secondary": "Browse Atlas",
        "rating": "5.0 / 5",
        "rating_subtitle": "from 1 review",
    }}
    r1 = requests.put(f"{BASE_URL}/api/admin-public-pages/content/hero", json=payload, headers=admin_headers, timeout=15)
    assert r1.status_code == 200, r1.text
    assert r1.json()["ok"] is True

    r2 = requests.get(f"{BASE_URL}/api/admin-public-pages/content/hero", headers=admin_headers, timeout=15)
    d = r2.json()
    assert d["is_default"] is False
    assert d["data"]["title_line1"] == "Test Line 1"

    # Public read (no auth) — must reflect the edit
    r3 = requests.get(f"{BASE_URL}/api/public-pages/content/hero", timeout=15)
    assert r3.status_code == 200
    assert r3.json()["data"]["eyebrow"] == "TEST EYEBROW"

    # Reset
    requests.post(f"{BASE_URL}/api/admin-public-pages/content/hero/reset", headers=admin_headers, timeout=15)
    r4 = requests.get(f"{BASE_URL}/api/public-pages/content/hero", timeout=15)
    assert r4.json()["data"]["eyebrow"] != "TEST EYEBROW"


def test_put_hero_validation(admin_headers):
    """Hero must reject missing required fields."""
    r = requests.put(f"{BASE_URL}/api/admin-public-pages/content/hero",
                     json={"data": {"title_line1": "x"}}, headers=admin_headers, timeout=15)
    assert r.status_code == 400


def test_put_featured_validation(admin_headers):
    """Featured must reject empty arrays + malformed items."""
    r1 = requests.put(f"{BASE_URL}/api/admin-public-pages/content/featured_codes",
                      json={"data": []}, headers=admin_headers, timeout=15)
    assert r1.status_code == 400

    r2 = requests.put(f"{BASE_URL}/api/admin-public-pages/content/featured_codes",
                      json={"data": [{"country_code": "AU"}]}, headers=admin_headers, timeout=15)
    assert r2.status_code == 400


def test_put_testimonials_validation(admin_headers):
    """Testimonials must require name + text."""
    r = requests.put(f"{BASE_URL}/api/admin-public-pages/content/testimonials",
                     json={"data": [{"name": "X"}]}, headers=admin_headers, timeout=15)
    assert r.status_code == 400


def test_partner_cannot_edit_content(partner_headers):
    r = requests.put(f"{BASE_URL}/api/admin-public-pages/content/hero",
                     json={"data": {"x": "y"}}, headers=partner_headers, timeout=15)
    assert r.status_code in (401, 403)


def test_public_content_no_auth():
    """Public content endpoint must work without auth."""
    r = requests.get(f"{BASE_URL}/api/public-pages/content/hero", timeout=15)
    assert r.status_code == 200
    assert "data" in r.json()

    r2 = requests.get(f"{BASE_URL}/api/public-pages/content", timeout=15)
    assert r2.status_code == 200
    assert {"hero", "featured_codes", "testimonials", "faqs", "trust_strip"}.issubset(set(r2.json().keys()))


# ─── Analytics ──────────────────────────────────────────────────────────────

def test_analytics_returns_window(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin-public-pages/analytics?days=30", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["days"] == 30
    assert isinstance(d["total_leads"], int)
    assert isinstance(d["top_codes"], list)
    assert isinstance(d["country_distribution"], dict)
    assert isinstance(d["daily_trend"], list)


def test_top_pages(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin-public-pages/top-pages?limit=5&days=30", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "pages" in d
    assert d["days"] == 30


def test_analytics_partner_blocked(partner_headers):
    r = requests.get(f"{BASE_URL}/api/admin-public-pages/analytics", headers=partner_headers, timeout=15)
    assert r.status_code in (401, 403)
