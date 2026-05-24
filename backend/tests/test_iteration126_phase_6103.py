"""Phase 6.10 Part 3 — Unified Workflow + Checklist Gating + Country Guides tests."""
import os
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://staff-dashboard-66.preview.emergentagent.com"
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


@pytest.fixture(scope="module")
def seeded_assessment(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "Phase 6.10.3 Lifecycle Test",
        "client_email": "lc-test@test.com",
        "client_phone": "+91-9000000010",
        "profile": {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 28},
                "education": {"highest_qualification": "master"},
                "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
                "professional": {"current_profession": "Software Engineer", "years_experience_total": 5},
                "au_extras": {}, "ca_extras": {}, "nz_extras": {},
            },
        },
        "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer",
                       "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=headers, timeout=15)
    aid = r.json()["id"]
    yield aid
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=headers)


# ─────────────────────────────────────────────────────────────────────────────
# Section 1: Lifecycle Tracker
# ─────────────────────────────────────────────────────────────────────────────
def test_lifecycle_returns_7_steps(admin_headers, seeded_assessment):
    r = requests.get(f"{BASE}/sales/assessments/{seeded_assessment}/lifecycle", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert len(d["steps"]) == 7
    keys = [s["key"] for s in d["steps"]]
    assert keys == ["created", "calculated", "report_generated", "pa_created", "pa_fee_paid", "main_fee_paid", "case_created"]


def test_lifecycle_progress_advances_after_report_generate(admin_headers, seeded_assessment):
    # Initial: only created + calculated done (2/7)
    before = requests.get(f"{BASE}/sales/assessments/{seeded_assessment}/lifecycle", headers=admin_headers, timeout=10).json()
    assert before["steps"][0]["completed"] is True   # created
    assert before["steps"][1]["completed"] is True   # calculated
    assert before["steps"][2]["completed"] is False  # report_generated

    # Generate a report
    requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": seeded_assessment, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30)

    after = requests.get(f"{BASE}/sales/assessments/{seeded_assessment}/lifecycle", headers=admin_headers, timeout=10).json()
    assert after["steps"][2]["completed"] is True
    assert after["current_step_index"] >= 2
    assert after["progress_pct"] > before["progress_pct"]


def test_lifecycle_404_on_missing(admin_headers):
    r = requests.get(f"{BASE}/sales/assessments/nonexistent-aid/lifecycle", headers=admin_headers, timeout=10)
    assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Section 2: Checklist Gating
# ─────────────────────────────────────────────────────────────────────────────
def test_checklist_is_locked_without_pa(admin_headers, seeded_assessment):
    r = requests.get(f"{BASE}/sales/assessments/{seeded_assessment}/checklist", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["is_locked"] is True
    assert "Create the Pre-Assessment" in d["unlock_reason"]
    assert d["items"] == []
    # Stats must still be present (summary view)
    assert d["stats"]["total"] > 0
    assert d["stats"]["required"] >= 0


def test_checklist_stats_preserved_when_locked(admin_headers, seeded_assessment):
    r = requests.get(f"{BASE}/sales/assessments/{seeded_assessment}/checklist", headers=admin_headers, timeout=10)
    d = r.json()
    # Locked state must still tell admin/partner how many docs are anticipated
    assert d["stats"]["categories"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Section 3: Country Guides
# ─────────────────────────────────────────────────────────────────────────────
def test_country_guides_list_auto_seeds_defaults(admin_headers):
    r = requests.get(f"{BASE}/country-guides/", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["count"] >= 5
    codes = [g["country_code"] for g in d["items"]]
    for cc in ("AU", "CA", "NZ", "UK", "USA"):
        assert cc in codes


def test_country_guide_update_reverts_to_draft(admin_headers):
    # Verify AU first (if not already)
    requests.put(f"{BASE}/country-guides/CA",
                  json={"hero": {"title": "🇨🇦 Canada Updated", "subtitle": "Test", "image_url": None}},
                  headers=admin_headers, timeout=10)
    requests.post(f"{BASE}/country-guides/CA/verify",
                  json={"source_reference": "https://ircc.gc.ca/test"},
                  headers=admin_headers, timeout=10)
    # Now edit again — should flip back to draft
    r = requests.put(f"{BASE}/country-guides/CA",
                     json={"hero": {"title": "🇨🇦 Canada", "subtitle": "v2", "image_url": None}},
                     headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "draft"


def test_country_guide_verify_publishes_to_public(admin_headers):
    requests.put(f"{BASE}/country-guides/UK",
                  json={"hero": {"title": "🇬🇧 UK", "subtitle": "Skilled routes", "image_url": None}},
                  headers=admin_headers, timeout=10)
    requests.post(f"{BASE}/country-guides/UK/verify",
                  json={"source_reference": "https://gov.uk/skilled-worker-visa"},
                  headers=admin_headers, timeout=10)
    # Public endpoint should now return UK
    r = requests.get(f"{BASE}/country-guides/public/UK", timeout=10)
    assert r.status_code == 200
    assert r.json()["country_code"] == "UK"
    assert "ai_draft" not in r.json()


def test_country_guide_public_404_on_draft(admin_headers):
    """Drafts must not be exposed publicly."""
    # First make sure USA is draft (edit reverts to draft)
    requests.put(f"{BASE}/country-guides/USA",
                  json={"hero": {"title": "🇺🇸 USA", "subtitle": "draft test", "image_url": None}},
                  headers=admin_headers, timeout=10)
    r = requests.get(f"{BASE}/country-guides/public/USA", timeout=10)
    assert r.status_code == 404


def test_country_guide_partner_403_on_admin_endpoint(partner_token):
    if not partner_token:
        pytest.skip("partner not seeded")
    r = requests.get(f"{BASE}/country-guides/", headers={"Authorization": f"Bearer {partner_token}"}, timeout=10)
    assert r.status_code == 403


def test_country_guide_public_list_only_verified(admin_headers):
    r = requests.get(f"{BASE}/country-guides/public", timeout=10)
    assert r.status_code == 200
    items = r.json()["items"]
    # All items in public list must be verified
    for item in items:
        # public list doesn't expose 'status' — but we can re-check with admin
        full = requests.get(f"{BASE}/country-guides/{item['country_code']}", headers=admin_headers, timeout=10).json()
        assert full["status"] == "verified"
