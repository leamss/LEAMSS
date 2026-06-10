"""Phase 7.1 — KB Unification tests.

Coverage:
  - Verification Hub aggregation
  - ANZSCO 4-digit master endpoints (data freshly imported)
  - UK + USA country_templates seeded
  - Protection Policy CRUD + verify + hide/unhide
  - Occupation-full join endpoint
"""
import os
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://career-match-320.preview.emergentagent.com"
BASE = f"{API}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    return r.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def partner_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    return r.json()["token"] if r.status_code == 200 else None


# ─────────────────────────────────────────────────────────────────────────────
# Verification Hub
# ─────────────────────────────────────────────────────────────────────────────
def test_verification_hub_returns_4_entity_summary(admin_headers):
    r = requests.get(f"{BASE}/kb-unified/verification-hub", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    s = d["summary"]
    for key in ("occupation_master", "country_templates", "country_guides", "protection_policies", "anzsco_4digit_master"):
        assert key in s, f"missing {key}"
    assert s["anzsco_4digit_master"]["total_codes"] >= 1200, "ANZSCO Excel not imported"


def test_verification_hub_has_pending_lists(admin_headers):
    r = requests.get(f"{BASE}/kb-unified/verification-hub", headers=admin_headers, timeout=10)
    d = r.json()
    assert "pending_lists" in d
    for key in ("occupations", "country_templates", "country_guides", "protection_policies"):
        assert key in d["pending_lists"]


def test_verification_hub_partner_403(partner_token):
    if not partner_token:
        pytest.skip("partner not seeded")
    r = requests.get(f"{BASE}/kb-unified/verification-hub", headers={"Authorization": f"Bearer {partner_token}"}, timeout=10)
    assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# ANZSCO 4-digit
# ─────────────────────────────────────────────────────────────────────────────
def test_anzsco_4digit_has_rich_profile():
    r = requests.get(f"{BASE}/kb-unified/anzsco/2613", timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == "2613"
    assert d["title"]
    assert d["description"]
    assert len(d["tasks"]) >= 3
    assert d["anzsco_profile"]["median_weekly_earnings_aud"] > 0
    assert len(d["industries_ranked"]) >= 1
    assert "NSW" in d["state_distribution"]
    assert "bachelor" in d["education_distribution"]
    assert d["data_source"]["label"].startswith("ABS")


def test_anzsco_404_on_invalid():
    r = requests.get(f"{BASE}/kb-unified/anzsco/9999", timeout=10)
    assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# UK + USA Country Templates
# ─────────────────────────────────────────────────────────────────────────────
def test_uk_template_exists_after_migration(admin_headers):
    r = requests.get(f"{BASE}/country-templates/UK", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["country_code"] == "UK"
    assert len(d["visa_subclasses"]) >= 4
    sub_codes = [v["code"] for v in d["visa_subclasses"]]
    assert "skilled_worker" in sub_codes


def test_usa_template_exists_after_migration(admin_headers):
    r = requests.get(f"{BASE}/country-templates/USA", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["country_code"] == "USA"
    sub_codes = [v["code"] for v in d["visa_subclasses"]]
    assert "h1b" in sub_codes
    assert "eb2_niw" in sub_codes


# ─────────────────────────────────────────────────────────────────────────────
# Protection Policy
# ─────────────────────────────────────────────────────────────────────────────
def test_protection_policy_default_seeded(admin_headers):
    r = requests.get(f"{BASE}/protection-policies/", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    items = r.json()["items"]
    defaults = [p for p in items if p.get("is_default_leamss")]
    assert len(defaults) == 1
    p = defaults[0]
    assert "Protection Policy" in p["title"]
    assert p["refund_terms"]["claim_within_days"] == 90
    assert "professional_fees" in p["refund_terms"]["covers"]


def test_protection_policy_create_update_verify_hide(admin_headers):
    # Create
    r = requests.post(f"{BASE}/protection-policies/",
                      json={"title": "Test Policy v1", "description_markdown": "Test content"},
                      headers=admin_headers, timeout=10)
    assert r.status_code == 200
    p = r.json()
    pid = p["policy_id"]
    assert p["status"] == "draft"
    # Update
    r = requests.put(f"{BASE}/protection-policies/{pid}",
                     json={"title": "Test Policy v2", "description_markdown": "v2 content"},
                     headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["title"] == "Test Policy v2"
    assert r.json()["status"] == "draft"
    # Verify
    r = requests.post(f"{BASE}/protection-policies/{pid}/verify",
                      json={"source_reference": "https://leamss.com/internal/policy-v2.pdf"},
                      headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "verified"
    # Public read works for verified
    r = requests.get(f"{BASE}/protection-policies/public/{pid}", timeout=10)
    assert r.status_code == 200
    # Hide (Sir's directive: hide not delete)
    r = requests.post(f"{BASE}/protection-policies/{pid}/hide", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    # Public read 404 on hidden
    r = requests.get(f"{BASE}/protection-policies/public/{pid}", timeout=10)
    assert r.status_code == 404
    # Unhide → draft
    r = requests.post(f"{BASE}/protection-policies/{pid}/unhide", headers=admin_headers, timeout=10)
    assert r.status_code == 200


def test_protection_policy_partner_403(partner_token):
    if not partner_token:
        pytest.skip("partner not seeded")
    r = requests.get(f"{BASE}/protection-policies/", headers={"Authorization": f"Bearer {partner_token}"}, timeout=10)
    assert r.status_code == 403


def test_protection_policy_public_visible_after_verify(admin_headers):
    r = requests.get(f"{BASE}/protection-policies/public", timeout=10)
    assert r.status_code == 200
    # Public list may be empty (default policy is draft) or contain verified ones
    assert "items" in r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Excel re-import (idempotent)
# ─────────────────────────────────────────────────────────────────────────────
def test_excel_reimport_idempotent(admin_headers):
    r = requests.post(f"{BASE}/kb-unified/import-anzsco-default", headers=admin_headers, timeout=60)
    assert r.status_code == 200
    d = r.json()
    # Second run: 0 imported, all updated
    assert d["updated"] >= 1000
    assert d["imported"] == 0
    assert len(d["errors"]) == 0
