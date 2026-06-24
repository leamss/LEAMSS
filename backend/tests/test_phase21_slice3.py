"""Phase 21 Slice 3 backend tests — Reimbursements + HR Analytics + Content Studio + SEO/AEO/GEO.

Note: Content Studio + SEO/AEO/GEO tests hit Claude Sonnet 4.5 live via Emergent LLM Key.
Cached by sha256(system|||user) for 1 hour, so repeated runs hit cache.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@leamss.com", "password": "Admin@123"},
        timeout=30,
    )
    return r.json()["token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


# ══════════════════════════════════════════════════════
# REIMBURSEMENTS (7 tests)
# ══════════════════════════════════════════════════════

def test_reimb_submit(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/reimbursements",
        json={"category": "travel", "amount_inr": 1500, "description": "Cab to client meeting", "expense_date": "2026-02-10"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"
    assert r.json()["amount_inr"] == 1500


def test_reimb_invalid_category(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/reimbursements",
        json={"category": "bogus", "amount_inr": 100, "description": "x", "expense_date": "2026-02-10"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 400


def test_reimb_negative_amount(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/reimbursements",
        json={"category": "food", "amount_inr": -50, "description": "x", "expense_date": "2026-02-10"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 400


def test_reimb_list_for_me(admin_token):
    r = requests.get(f"{BASE_URL}/api/reimbursements?for_view=me", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_reimb_manager_approve_then_hr_approve(admin_token):
    # admin has full permissions, can do both as admin
    c = requests.post(
        f"{BASE_URL}/api/reimbursements",
        json={"category": "office_supplies", "amount_inr": 800, "description": "Stationary buy", "expense_date": "2026-02-12"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r1 = requests.patch(
        f"{BASE_URL}/api/reimbursements/{c['id']}/manager-approve",
        json={"notes": "Approved by manager (pytest)"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r1.status_code == 200
    r2 = requests.patch(
        f"{BASE_URL}/api/reimbursements/{c['id']}/hr-approve",
        json={"notes": "HR confirmed (pytest)"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r2.status_code == 200


def test_reimb_reject_with_reason(admin_token):
    c = requests.post(
        f"{BASE_URL}/api/reimbursements",
        json={"category": "food", "amount_inr": 3000, "description": "Team lunch", "expense_date": "2026-02-13"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    # Reject with reason
    r = requests.patch(
        f"{BASE_URL}/api/reimbursements/{c['id']}/reject",
        json={"reason": "Exceeds per-meal cap"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    # No reason → 400
    c2 = requests.post(
        f"{BASE_URL}/api/reimbursements",
        json={"category": "food", "amount_inr": 1000, "description": "x", "expense_date": "2026-02-14"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r_no = requests.patch(
        f"{BASE_URL}/api/reimbursements/{c2['id']}/reject",
        json={"reason": ""},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r_no.status_code == 400


def test_reimb_audit_trail(admin_token):
    c = requests.post(
        f"{BASE_URL}/api/reimbursements",
        json={"category": "phone", "amount_inr": 1200, "description": "Phone bill", "expense_date": "2026-02-15"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.get(f"{BASE_URL}/api/reimbursements/{c['id']}/audit-trail", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    audit = r.json()
    assert any(e["action"] == "submitted" for e in audit)


# ══════════════════════════════════════════════════════
# HR ANALYTICS (6 tests)
# ══════════════════════════════════════════════════════

def test_hra_headcount(admin_token):
    r = requests.get(f"{BASE_URL}/api/hr-analytics/headcount", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ("total", "active", "on_leave", "terminated"):
        assert k in d


def test_hra_department_breakdown(admin_token):
    r = requests.get(f"{BASE_URL}/api/hr-analytics/department-breakdown", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_hra_attrition(admin_token):
    r = requests.get(f"{BASE_URL}/api/hr-analytics/attrition?days=365", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert "attrition_rate_pct" in r.json()


def test_hra_leave_patterns(admin_token):
    r = requests.get(f"{BASE_URL}/api/hr-analytics/leave-patterns", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_hra_attendance_summary(admin_token):
    r = requests.get(f"{BASE_URL}/api/hr-analytics/attendance-summary", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert "by_status" in r.json()


def test_hra_overview(admin_token):
    r = requests.get(f"{BASE_URL}/api/hr-analytics/overview", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ("headcount", "attrition", "attendance", "onboarding", "departments", "leaves"):
        assert k in d


# ══════════════════════════════════════════════════════
# CONTENT STUDIO (Claude live — cached for 1h) (5 tests)
# ══════════════════════════════════════════════════════

def test_content_generate_3_variants(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/content-studio/generate",
        json={
            "brief": "Pytest stable seed brief — promote Australia PR consultation",
            "content_type": "email",
            "target_audience": "IT pros",
            "keywords": ["Australia PR"],
            "brand_voice": "professional",
            "language": "en",
            "variants_count": 3,
        },
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    d = r.json()
    assert len(d["variants"]) >= 1
    v = d["variants"][0]
    for k in ("subject_or_headline", "body", "cta"):
        assert k in v


def test_content_invalid_content_type_400(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/content-studio/generate",
        json={"brief": "x", "content_type": "podcast", "target_audience": "x"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 400


def test_content_save_and_list_draft(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/content-studio/save-draft",
        json={
            "title": "Pytest draft",
            "type": "email",
            "brief": "x",
            "variants": [{"variant_number": 1, "subject_or_headline": "Test", "body": "..."}],
            "selected_variant": 1,
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    draft_id = r.json()["id"]
    listed = requests.get(f"{BASE_URL}/api/content-studio/drafts", headers=_auth(admin_token), timeout=15).json()
    assert any(d["id"] == draft_id for d in listed)


def test_content_edit_draft(admin_token):
    save = requests.post(
        f"{BASE_URL}/api/content-studio/save-draft",
        json={
            "title": "Pytest edit draft",
            "type": "blog",
            "brief": "x",
            "variants": [{"variant_number": 1, "subject_or_headline": "T", "body": "B"}],
        },
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.patch(
        f"{BASE_URL}/api/content-studio/drafts/{save['id']}",
        json={"final_content": "Edited final body", "published": True},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200


def test_content_cache_idempotency(admin_token):
    """Two identical brief requests should be served from LLM cache (no re-bill)."""
    payload = {
        "brief": "PYTEST-CACHE-PROBE-12345 unique brief seed for cache",
        "content_type": "social_post",
        "target_audience": "Indian students",
        "keywords": [],
        "brand_voice": "witty",
        "language": "en",
        "variants_count": 1,
    }
    r1 = requests.post(f"{BASE_URL}/api/content-studio/generate", json=payload, headers=_auth(admin_token), timeout=60)
    r2 = requests.post(f"{BASE_URL}/api/content-studio/generate", json=payload, headers=_auth(admin_token), timeout=15)
    assert r1.status_code == 200 and r2.status_code == 200
    # Both should have same first variant from cache
    if r1.json()["variants"] and r2.json()["variants"]:
        assert r1.json()["variants"][0].get("subject_or_headline") == r2.json()["variants"][0].get("subject_or_headline")


# ══════════════════════════════════════════════════════
# SEO TOOLS (Claude live cached) (3 tests)
# ══════════════════════════════════════════════════════

def test_seo_keyword_research(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/seo/keyword-research",
        json={"seed_keyword": "australia pr"},
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    assert "keywords" in r.json()


def test_seo_meta_optimize(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/seo/meta-optimize",
        json={"raw_content": "Australia offers many PR pathways for IT professionals.", "target_keywords": ["australia pr", "189 visa"]},
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    assert "options" in r.json()


def test_seo_internal_link(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/seo/internal-link-suggestions",
        json={"page_content": "Discover the pathways to migrate to Australia.",
              "available_pages": [{"url": "/au/atlas", "title": "AU State Atlas", "summary": "..."}]},
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    assert "suggestions" in r.json()


# ══════════════════════════════════════════════════════
# AEO TOOLS (3 tests)
# ══════════════════════════════════════════════════════

def test_aeo_faq_schema(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/aeo/faq-schema-generate",
        json={"questions": ["What is Australia PR?", "How long does 189 visa take?"], "topic": "Australia PR"},
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    d = r.json()
    assert "answers" in d
    assert "json_ld" in d


def test_aeo_voice_search(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/aeo/voice-search-optimize",
        json={"content": "LEAMSS helps Indian IT professionals migrate to Australia."},
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    assert "natural_language_phrasings" in r.json() or "question_variants" in r.json()


def test_aeo_featured_snippet(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/aeo/featured-snippet-target",
        json={"topic": "how to apply for australia 189 visa"},
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    assert "best_snippet_type" in r.json()


# ══════════════════════════════════════════════════════
# GEO TOOLS (4 tests)
# ══════════════════════════════════════════════════════

def test_geo_llm_audit(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/geo/llm-content-audit",
        json={"content": "LEAMSS is an Indian immigration consultancy specialising in Australia PR pathways."},
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    d = r.json()
    for k in ("clarity_score", "citation_worthiness_score", "improvements"):
        assert k in d


def test_geo_structured_data(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/geo/structured-data-validator",
        json={"html": "<html><head><script type='application/ld+json'>{\"@type\":\"Article\"}</script></head></html>"},
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    assert "compliance_score" in r.json()


def test_geo_crawl_tracker(admin_token):
    r = requests.get(f"{BASE_URL}/api/geo/llm-crawl-tracker", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert "bots_detected" in r.json()


def test_geo_citation_optimizer(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/geo/citation-optimizer",
        json={"content": "Australia has many PR pathways for skilled migrants. We help with Subclass 189."},
        headers=_auth(admin_token),
        timeout=60,
    )
    assert r.status_code == 200
    assert "suggestions" in r.json()
