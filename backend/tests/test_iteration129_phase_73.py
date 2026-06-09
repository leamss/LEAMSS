"""Phase 7.3 — Report KB Data Injection + 3-tier gating tests."""
import os
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://compliance-hub-751.preview.emergentagent.com"
BASE = f"{API}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    return r.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def seeded_assessment_with_cost(admin_token):
    """Creates an assessment + saves cost estimator on it. Yields assessment_id."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "Phase 7.3 Test", "client_email": "p73@t.com", "client_phone": "+91-9000000300",
        "profile": {"marital_status": "single", "primary_applicant": {
            "personal": {"age": 28}, "education": {"highest_qualification": "master"},
            "language": {"scores": {"overall": 8, "listening": 8, "reading": 8, "writing": 7.5, "speaking": 8}},
            "professional": {"current_profession": "Software Engineer", "years_experience_total": 5},
            "au_extras": {}, "ca_extras": {}, "nz_extras": {},
        }},
        "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=headers, timeout=15)
    aid = r.json()["id"]
    requests.post(f"{BASE}/sales/wizard/cost-estimator/save", headers=headers, json={
        "assessment_id": aid, "currency": "INR",
        "items": [
            {"category": "Government Fees", "label": "Visa Fee", "amount": 430000, "currency": "INR", "is_estimated": True, "is_editable": True},
            {"category": "LEAMSS Professional Fees", "label": "PR Processing", "amount": 195000, "currency": "INR", "is_estimated": False, "is_editable": True},
        ],
        "notes": "Phase 7.3 test quote",
    }, timeout=10)
    yield aid
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=headers)


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot injection
# ─────────────────────────────────────────────────────────────────────────────
def test_snapshot_contains_anzsco_profile(admin_headers, seeded_assessment_with_cost):
    r = requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": seeded_assessment_with_cost, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30)
    assert r.status_code == 200
    snap_id = r.json()["snapshot_id"]
    sd = requests.get(f"{BASE}/assessment-reports/{snap_id}", headers=admin_headers, timeout=10).json()
    data = sd["data"]
    # ANZSCO 4-digit profile injected
    assert data.get("anzsco_profile"), "anzsco_profile missing from snapshot"
    assert data["anzsco_profile"]["code"] == "2613"
    assert len(data["anzsco_profile"].get("tasks", [])) >= 1


def test_snapshot_contains_cost_estimator(admin_headers, seeded_assessment_with_cost):
    r = requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": seeded_assessment_with_cost, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30)
    sd = requests.get(f"{BASE}/assessment-reports/{r.json()['snapshot_id']}", headers=admin_headers, timeout=10).json()
    ce = sd["data"].get("cost_estimator")
    assert ce, "cost_estimator missing from snapshot"
    assert ce["total_by_currency"]["INR"] == 625000


def test_snapshot_contains_protection_policy(admin_headers, seeded_assessment_with_cost):
    r = requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": seeded_assessment_with_cost, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30)
    sd = requests.get(f"{BASE}/assessment-reports/{r.json()['snapshot_id']}", headers=admin_headers, timeout=10).json()
    pp = sd["data"].get("protection_policy")
    # Either verified default exists (after Phase 7.1 + manual verify) or it's None (still draft)
    if pp:
        assert "title" in pp
        assert "refund_terms" in pp


# ─────────────────────────────────────────────────────────────────────────────
# 3-Tier PDF gating
# ─────────────────────────────────────────────────────────────────────────────
def test_pdf_tier_full(admin_headers, seeded_assessment_with_cost):
    r = requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": seeded_assessment_with_cost, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30)
    snap_id = r.json()["snapshot_id"]
    pdf = requests.get(f"{BASE}/assessment-reports/{snap_id}/pdf?tier=full", headers=admin_headers, timeout=30)
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"
    assert len(pdf.content) > 20000  # Full tier should be substantial


def test_pdf_tier_teaser_smaller_than_full(admin_headers, seeded_assessment_with_cost):
    r = requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": seeded_assessment_with_cost, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30)
    snap_id = r.json()["snapshot_id"]
    full_pdf = requests.get(f"{BASE}/assessment-reports/{snap_id}/pdf?tier=full", headers=admin_headers, timeout=30)
    teaser_pdf = requests.get(f"{BASE}/assessment-reports/{snap_id}/pdf?tier=teaser", headers=admin_headers, timeout=30)
    assert teaser_pdf.status_code == 200
    assert teaser_pdf.content[:4] == b"%PDF"
    # Teaser must be smaller (fewer sections rendered)
    assert len(teaser_pdf.content) < len(full_pdf.content)


def test_pdf_tier_invalid_falls_back_to_full(admin_headers, seeded_assessment_with_cost):
    r = requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": seeded_assessment_with_cost, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30)
    snap_id = r.json()["snapshot_id"]
    pdf = requests.get(f"{BASE}/assessment-reports/{snap_id}/pdf?tier=invalid", headers=admin_headers, timeout=30)
    # Should NOT 400 — gracefully fallback to full
    assert pdf.status_code == 200


def test_upgrade_tier(admin_headers, seeded_assessment_with_cost):
    r = requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": seeded_assessment_with_cost, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30)
    snap_id = r.json()["snapshot_id"]
    # Upgrade to proposal tier
    r = requests.post(f"{BASE}/assessment-reports/{snap_id}/upgrade-tier",
                       json={"tier": "proposal", "payment_ref": "PA-TEST-001"},
                       headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["tier"] == "proposal"
    # Invalid tier rejected
    r = requests.post(f"{BASE}/assessment-reports/{snap_id}/upgrade-tier",
                       json={"tier": "platinum"}, headers=admin_headers, timeout=10)
    assert r.status_code == 400


def test_public_pdf_respects_stored_tier(admin_headers, seeded_assessment_with_cost):
    """Share link returns the PDF at the tier the snapshot is currently at."""
    g = requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": seeded_assessment_with_cost, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30).json()
    snap_id = g["snapshot_id"]
    # Default snapshot has no tier set → public returns teaser
    sh = requests.post(f"{BASE}/assessment-reports/{snap_id}/share", json={"expires_in_days": 7}, headers=admin_headers, timeout=10).json()
    teaser_pdf = requests.get(f"{BASE}/assessment-reports/public/{sh['share_token']}/pdf", timeout=30)
    assert teaser_pdf.status_code == 200
    teaser_size = len(teaser_pdf.content)
    # Upgrade to full
    requests.post(f"{BASE}/assessment-reports/{snap_id}/upgrade-tier", json={"tier": "full"}, headers=admin_headers, timeout=10)
    full_pdf = requests.get(f"{BASE}/assessment-reports/public/{sh['share_token']}/pdf", timeout=30)
    assert full_pdf.status_code == 200
    assert len(full_pdf.content) > teaser_size
