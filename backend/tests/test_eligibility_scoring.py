"""Tests for the deterministic eligibility scoring engine + endpoints.

Run: cd /app/backend && python -m pytest tests/test_eligibility_scoring.py -q
"""
import asyncio
import os
import httpx
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
API = f"{BASE}/api"
ADMIN = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER = {"email": "partner@leamss.com", "password": "Partner@123"}


def _login(creds):
    r = httpx.post(f"{API}/auth/login", json=creds, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d.get("token") or d.get("access_token")


# ── Pure engine unit tests (no HTTP) ─────────────────────────────────────────
def test_engine_strong_vs_weak_profile_is_deterministic():
    from core.eligibility_scoring import score_candidate
    pathways = [{
        "slug": "canada_express_entry", "name": "Canada EE", "country": "Canada",
        "min_age": 18, "max_age": 47, "min_education": "Bachelor's Degree",
        "min_work_exp_years": 1, "language_required": "IELTS 6.0", "min_funds_inr": 1300000,
        "timeline_months": "8-14",
    }]
    strong = {"age": 27, "education": "Master", "work_experience_years": 7,
              "english_score": "IELTS 8.0", "occupation": "Software Engineer", "has_job_offer": True,
              "family_savings_inr": 2000000}
    weak = {"age": 46, "education": "Class 12", "work_experience_years": 0,
            "english_score": "Not taken yet", "occupation": "", "has_job_offer": False,
            "family_savings_inr": None}

    r1 = asyncio.get_event_loop().run_until_complete(score_candidate(strong, pathways))
    r2 = asyncio.get_event_loop().run_until_complete(score_candidate(strong, pathways))
    r3 = asyncio.get_event_loop().run_until_complete(score_candidate(weak, pathways))

    s_strong = r1["pathways"]["canada_express_entry"]["score"]
    s_weak = r3["pathways"]["canada_express_entry"]["score"]
    # Deterministic — same input, same score
    assert r1["pathways"]["canada_express_entry"]["score"] == r2["pathways"]["canada_express_entry"]["score"]
    # Strong profile must beat weak profile
    assert s_strong > s_weak
    assert s_strong >= 75  # strong tier
    # Breakdown present + earned never exceeds max
    bd = r1["pathways"]["canada_express_entry"]["breakdown"]
    assert len(bd) == 7
    for b in bd:
        assert 0 <= b["earned"] <= b["max"]
        assert b["reason"]


def test_engine_age_over_limit_zeroes_age_factor():
    from core.eligibility_scoring import score_candidate
    pathways = [{"slug": "p", "name": "P", "country": "X", "min_age": 18, "max_age": 44,
                 "min_education": "Bachelor's Degree", "min_work_exp_years": 3,
                 "language_required": "IELTS 6.0", "min_funds_inr": 1000000}]
    over = {"age": 60, "education": "Bachelor", "work_experience_years": 5,
            "english_score": "IELTS 7.0", "occupation": "Nurse", "has_job_offer": False}
    r = asyncio.get_event_loop().run_until_complete(score_candidate(over, pathways))
    age_b = next(b for b in r["pathways"]["p"]["breakdown"] if b["factor"] == "age")
    assert age_b["earned"] == 0


def test_job_offer_gate_drops_required_pathways():
    from core.eligibility_scoring import score_candidate
    base = {"min_age": 18, "max_age": 60, "min_education": "Bachelor's Degree",
            "min_work_exp_years": 0, "language_required": "IELTS 6.0", "min_funds_inr": 100000,
            "competitiveness": 50}
    pathways = [
        {**base, "slug": "needs_offer", "name": "UK", "country": "United Kingdom", "requires_job_offer": True},
        {**base, "slug": "no_offer", "name": "CA", "country": "Canada", "requires_job_offer": False},
    ]
    prof = {"age": 28, "education": "Master", "work_experience_years": 6,
            "english_score": "IELTS 8.0", "occupation": "Engineer", "has_job_offer": False}
    r = asyncio.get_event_loop().run_until_complete(score_candidate(prof, pathways))
    needs = r["pathways"]["needs_offer"]
    free = r["pathways"]["no_offer"]
    # Job-offer-required pathway must score lower and expose an adjustment
    assert needs["score"] < free["score"]
    assert any(a["label"] == "Job offer required" for a in needs["adjustments"])


def test_competitiveness_differentiates_scores():
    from core.eligibility_scoring import score_candidate
    base = {"min_age": 18, "max_age": 60, "min_education": "Bachelor's Degree",
            "min_work_exp_years": 0, "language_required": "IELTS 6.0", "min_funds_inr": 100000,
            "requires_job_offer": False}
    pathways = [
        {**base, "slug": "easy", "name": "NZ", "country": "New Zealand", "competitiveness": 30},
        {**base, "slug": "hard", "name": "US", "country": "United States", "competitiveness": 95},
    ]
    prof = {"age": 28, "education": "Master", "work_experience_years": 6,
            "english_score": "IELTS 8.0", "occupation": "Engineer", "has_job_offer": False}
    r = asyncio.get_event_loop().run_until_complete(score_candidate(prof, pathways))
    assert r["pathways"]["easy"]["score"] > r["pathways"]["hard"]["score"]
    assert r["top_recommendation"] == "easy"


def test_live_scores_are_not_all_identical():
    # Regression for the "all 86" bug — a strong profile must yield varied scores
    payload = {"age": 29, "education": "Master", "work_experience_years": 10,
               "occupation": "Software Engineer", "english_score": "IELTS 7.0-7.5",
               "has_job_offer": False, "preferred_countries": ["Canada"]}
    r = httpx.post(f"{API}/eligibility/score", json=payload, timeout=90)
    assert r.status_code == 200, r.text
    scores = {s: p["score"] for s, p in r.json()["pathways"].items()}
    assert len(set(scores.values())) >= 3, f"Scores not differentiated: {scores}"
    # UK/Germany (require offer) should be clearly lower than the top
    top = max(scores.values())
    assert scores.get("uk_skilled_worker", 0) < top


# ── HTTP endpoint tests ──────────────────────────────────────────────────────
def test_score_endpoint_returns_breakdown_and_no_422_on_minimal():
    payload = {"age": 29, "education": "Bachelors", "work_experience_years": 4,
               "occupation": "Civil Engineer", "english_score": "IELTS 7.0",
               "preferred_countries": ["Australia"]}
    r = httpx.post(f"{API}/eligibility/score", json=payload, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["top_recommendation"]
    assert d["overall_summary"]
    assert d["pathways"]
    any_path = next(iter(d["pathways"].values()))
    assert "breakdown" in any_path and len(any_path["breakdown"]) >= 5
    assert 0 <= any_path["score"] <= 100


def test_score_empty_email_does_not_422():
    # Empty email must be coerced/omitted — never a 422 crash
    payload = {"age": 30, "education": "Master", "work_experience_years": 6,
               "occupation": "Doctor", "english_score": "IELTS 7.5", "email": None}
    r = httpx.post(f"{API}/eligibility/score", json=payload, timeout=90)
    assert r.status_code == 200, r.text


def test_lead_capture_requires_contact():
    r = httpx.post(f"{API}/eligibility/lead", json={"name": "Test"}, timeout=30)
    assert r.status_code == 400


def test_lead_capture_succeeds_with_email():
    r = httpx.post(f"{API}/eligibility/lead",
                   json={"name": "Test Lead", "email": "lead@example.com", "preferred_country": "Canada"},
                   timeout=30)
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_scoring_rules_admin_crud_and_rbac():
    admin = _login(ADMIN)
    h = {"Authorization": f"Bearer {admin}"}
    # GET defaults
    r = httpx.get(f"{API}/eligibility/scoring-rules", headers=h, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "age" in body["rules"]["factors"]
    # PUT override
    r = httpx.put(f"{API}/eligibility/scoring-rules", headers=h,
                  json={"tiers": {"strong": 80, "moderate": 60, "weak": 40}}, timeout=30)
    assert r.status_code == 200
    assert r.json()["rules"]["tiers"]["strong"] == 80
    assert r.json()["rules"]["_source"] == "db_override"
    # RESET
    r = httpx.post(f"{API}/eligibility/scoring-rules/reset", headers=h, timeout=30)
    assert r.status_code == 200
    assert r.json()["rules"]["_source"] == "defaults"


def test_scoring_rules_partner_blocked():
    partner = _login(PARTNER)
    h = {"Authorization": f"Bearer {partner}"}
    r = httpx.get(f"{API}/eligibility/scoring-rules", headers=h, timeout=30)
    assert r.status_code == 403


def test_visa_compare_pathways_public():
    r = httpx.get(f"{API}/visa-compare/pathways", timeout=30)
    assert r.status_code == 200
    assert len(r.json()["pathways"]) >= 2


def test_visa_compare_compare_two():
    r = httpx.get(f"{API}/visa-compare/compare?slugs=canada_express_entry,australia_189", timeout=30)
    assert r.status_code == 200
    assert len(r.json()["pathways"]) == 2


def _make_score():
    payload = {"full_name": "PDF Tester", "age": 29, "education": "Master",
               "work_experience_years": 6, "occupation": "Software Engineer",
               "english_score": "IELTS 7.0-7.5", "preferred_countries": ["Canada"]}
    r = httpx.post(f"{API}/eligibility/score", json=payload, timeout=90)
    r.raise_for_status()
    return r.json()["score_id"]


def test_share_endpoint_returns_scorecard():
    sid = _make_score()
    r = httpx.get(f"{API}/eligibility/share/{sid}", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == sid
    assert d["result"]["pathways"]
    # profile must NOT leak on the shareable endpoint
    assert "profile" not in d


def test_pdf_report_endpoint_returns_valid_pdf():
    sid = _make_score()
    r = httpx.get(f"{API}/eligibility/report/{sid}", timeout=60)
    assert r.status_code == 200
    assert "application/pdf" in r.headers.get("content-type", "")
    assert r.content[:5] == b"%PDF-"
    assert len(r.content) > 1000


def test_pdf_report_404_for_bad_id():
    r = httpx.get(f"{API}/eligibility/report/nonexistent-id", timeout=30)
    assert r.status_code == 404


def test_scorecard_lead_flow_list_and_assign():
    # 1) Public lead capture (download gate) linked to a score
    sid = _make_score()
    r = httpx.post(f"{API}/eligibility/lead", json={
        "score_id": sid, "name": "Assign Test", "email": "assign@example.com",
        "mobile": "9990001112", "preferred_country": "Canada"}, timeout=30)
    assert r.status_code == 200

    admin = _login(ADMIN)
    h = {"Authorization": f"Bearer {admin}"}
    # 2) Admin sees it in scorecard-leads, enriched
    r = httpx.get(f"{API}/eligibility/admin/scorecard-leads", headers=h, timeout=30)
    assert r.status_code == 200
    leads = r.json()
    mine = next((l for l in leads if l["email"] == "assign@example.com"), None)
    assert mine is not None
    assert mine["score_id"] == sid
    assert mine["top_pathway_name"] and mine["phone"] == "9990001112"

    # 3) Pick an assignable user and assign
    users = httpx.get(f"{API}/users", headers=h, timeout=30).json()
    roles = ("partner", "sales_executive", "sr_sales_executive", "sales_manager", "case_manager")
    target = next((u for u in users if u.get("role") in roles), None)
    assert target, "No assignable user found"
    r = httpx.put(f"{API}/eligibility/admin/scorecard-leads/{mine['id']}/assign",
                  headers=h, json={"assigned_to": target["id"]}, timeout=30)
    assert r.status_code == 200
    assert r.json()["assigned_to_name"] == target["name"]

    # 4) Verify persisted
    leads2 = httpx.get(f"{API}/eligibility/admin/scorecard-leads", headers=h, timeout=30).json()
    again = next(l for l in leads2 if l["id"] == mine["id"])
    assert again["assigned_to_name"] == target["name"]


def test_scorecard_leads_requires_auth():
    r = httpx.get(f"{API}/eligibility/admin/scorecard-leads", timeout=30)
    assert r.status_code in (401, 403)


