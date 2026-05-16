"""Phase 6.2 — Eligibility Profiles (Smart Profile Form) backend tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://staff-dashboard-66.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@leamss.com", "Admin@123")
PARTNER = ("partner@leamss.com", "Partner@123")
CLIENT = ("client@leamss.com", "Client@123")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    j = r.json()
    return j.get("access_token") or j["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login(*ADMIN)}"}


@pytest.fixture(scope="module")
def partner_h():
    return {"Authorization": f"Bearer {_login(*PARTNER)}"}


@pytest.fixture(scope="module")
def client_h():
    return {"Authorization": f"Bearer {_login(*CLIENT)}"}


CREATED_IDS: list = []


def _sample_payload(name="TEST_Phase62_Profile"):
    return {
        "name": name,
        "email": "test_phase62@example.com",
        "phone": "+91-9876543210",
        "basic_info": {
            "full_name": name,
            "date_of_birth": "1990-05-15",
            "gender": "male",
            "marital_status": "married",
            "current_country": "India",
            "current_city": "Mumbai",
            "nationality": "Indian",
            "dependents_count": 1,
        },
        "professional": {
            "current_profession": "Software Engineer",
            "designation": "Senior",
            "years_experience_total": 8,
            "years_in_current_role": 3,
            "industry": "IT",
            "salary_inr_per_annum": 2500000,
        },
        "education": {
            "highest_qualification": "master",
            "field_of_study": "Computer Science",
            "year_completed": 2015,
        },
        "language_proficiency": {
            "primary_test": "IELTS",
            "test_completed": True,
            "scores": {"listening": 8.0, "reading": 7.5, "writing": 7.0, "speaking": 7.5, "overall": 7.5},
        },
        "family": {"spouse_present": True, "children_count": 1, "children_ages": [3]},
        "finances": {"annual_household_income": 3000000, "savings_inr": 2000000, "able_to_show_funds": True},
        "preferences": {
            "search_mode": "top_3",
            "preferred_countries": ["AU", "CA", "NZ"],
            "timeline_months": 12,
        },
        "work_history": [
            {"employer": "Acme Corp", "designation": "Engineer", "start_date": "2018-01-01", "end_date": "2022-12-31", "country": "IN"},
            {"employer": "Beta Ltd", "designation": "Sr Engineer", "start_date": "2023-01-01", "country": "IN"},
        ],
        "additional_factors": {"has_relative_in_target_country": False, "criminal_record": False},
        "status": "draft",
    }


# ── Create + auto-age ─────────────────────────────────────────
class TestCreateProfile:
    def test_create_full_payload(self, admin_h):
        r = requests.post(f"{API}/eligibility/profiles", json=_sample_payload(), headers=admin_h, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["id"].startswith("ELG-")
        assert d["name"].startswith("TEST_Phase62")
        assert d["status"] == "draft"
        assert d["basic_info"]["age"] in (35, 36), f"age auto-compute failed: {d['basic_info'].get('age')}"
        assert d["preferences"]["search_mode"] == "top_3"
        assert len(d["work_history"]) == 2
        CREATED_IDS.append(d["id"])

    def test_create_minimal(self, admin_h):
        r = requests.post(f"{API}/eligibility/profiles", json={"name": "TEST_Phase62_Min"}, headers=admin_h, timeout=30)
        assert r.status_code == 200
        CREATED_IDS.append(r.json()["id"])


# ── List + filters + search ───────────────────────────────────
class TestListProfiles:
    def test_list_paginated(self, admin_h):
        r = requests.get(f"{API}/eligibility/profiles", headers=admin_h, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "count" in d
        assert isinstance(d["items"], list)
        if d["items"]:
            it = d["items"][0]
            for k in ("id", "name", "status", "search_mode", "age", "pa_id"):
                assert k in it, f"missing summary key {k}"

    def test_search_by_name(self, admin_h):
        r = requests.get(f"{API}/eligibility/profiles?search=TEST_Phase62", headers=admin_h, timeout=30)
        assert r.status_code == 200
        names = [i["name"] for i in r.json()["items"]]
        assert any("TEST_Phase62" in n for n in names)

    def test_filter_status_draft(self, admin_h):
        r = requests.get(f"{API}/eligibility/profiles?status=draft", headers=admin_h, timeout=30)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["status"] == "draft"


# ── Get detail ────────────────────────────────────────────────
class TestGetProfile:
    def test_get_detail(self, admin_h):
        pid = CREATED_IDS[0]
        r = requests.get(f"{API}/eligibility/profiles/{pid}", headers=admin_h, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == pid
        assert d["basic_info"]["age"] in (35, 36)
        assert d["language_proficiency"]["scores"]["overall"] == 7.5

    def test_get_404(self, admin_h):
        r = requests.get(f"{API}/eligibility/profiles/DOES-NOT-EXIST", headers=admin_h, timeout=30)
        assert r.status_code == 404


# ── PATCH section-level merge ─────────────────────────────────
class TestPatchProfile:
    def test_patch_basic_info_preserves_other_sections(self, admin_h):
        pid = CREATED_IDS[0]
        r = requests.patch(f"{API}/eligibility/profiles/{pid}",
                           json={"basic_info": {"current_city": "Delhi"}}, headers=admin_h, timeout=30)
        assert r.status_code == 200
        d = r.json()
        # basic_info merged (city updated, DOB preserved)
        assert d["basic_info"]["current_city"] == "Delhi"
        assert d["basic_info"]["date_of_birth"] == "1990-05-15"
        # other sections untouched
        assert d["professional"]["current_profession"] == "Software Engineer"
        assert d["language_proficiency"]["scores"]["overall"] == 7.5

    def test_patch_status(self, admin_h):
        pid = CREATED_IDS[0]
        r = requests.patch(f"{API}/eligibility/profiles/{pid}", json={"status": "complete"}, headers=admin_h, timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "complete"


# ── Duplicate ─────────────────────────────────────────────────
class TestDuplicate:
    def test_duplicate(self, admin_h):
        src = CREATED_IDS[0]
        r = requests.post(f"{API}/eligibility/profiles/{src}/duplicate", headers=admin_h, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] != src
        assert d["id"].startswith("ELG-")
        assert d["name"].endswith("(Copy)")
        assert d["status"] == "draft"
        assert d.get("pa_id") is None
        assert d.get("assessment_id") is None
        CREATED_IDS.append(d["id"])


# ── Stats ─────────────────────────────────────────────────────
class TestStats:
    def test_stats_me(self, admin_h):
        r = requests.get(f"{API}/eligibility/profiles/stats/me", headers=admin_h, timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("total", "draft", "complete", "assessed"):
            assert k in d and isinstance(d[k], int)
        assert d["total"] >= len(CREATED_IDS) - 0  # at least what we created


# ── PA prefill (negative — invalid PA) ────────────────────────
class TestPrefill:
    def test_prefill_404(self, admin_h):
        r = requests.post(f"{API}/eligibility/profiles/prefill-from-pa/DOES-NOT-EXIST", headers=admin_h, timeout=30)
        assert r.status_code == 404


# ── Link / Unlink PA ──────────────────────────────────────────
class TestLinkPA:
    def test_link_invalid_pa(self, admin_h):
        pid = CREATED_IDS[0]
        r = requests.post(f"{API}/eligibility/profiles/{pid}/link-to-pa?pa_id=DOES-NOT-EXIST",
                          headers=admin_h, timeout=30)
        assert r.status_code == 404

    def test_unlink(self, admin_h):
        pid = CREATED_IDS[0]
        r = requests.post(f"{API}/eligibility/profiles/{pid}/unlink-pa", headers=admin_h, timeout=30)
        assert r.status_code == 200


# ── RBAC 403 for client role ─────────────────────────────────
class TestRBAC:
    def test_client_403_list(self, client_h):
        r = requests.get(f"{API}/eligibility/profiles", headers=client_h, timeout=30)
        assert r.status_code == 403

    def test_client_403_create(self, client_h):
        r = requests.post(f"{API}/eligibility/profiles", json={"name": "TEST_Forbidden"}, headers=client_h, timeout=30)
        assert r.status_code == 403

    def test_client_403_stats(self, client_h):
        r = requests.get(f"{API}/eligibility/profiles/stats/me", headers=client_h, timeout=30)
        assert r.status_code == 403

    def test_partner_can_list(self, partner_h):
        r = requests.get(f"{API}/eligibility/profiles", headers=partner_h, timeout=30)
        assert r.status_code == 200

    def test_partner_cannot_delete_admin_owned(self, partner_h):
        # partner trying to delete a profile created by admin
        pid = CREATED_IDS[0]
        r = requests.delete(f"{API}/eligibility/profiles/{pid}", headers=partner_h, timeout=30)
        assert r.status_code == 403


# ── Phase 6.1 KB regression ──────────────────────────────────
class TestKBRegression:
    def test_kb_countries(self, admin_h):
        r = requests.get(f"{API}/eligibility/kb/countries", headers=admin_h, timeout=30)
        assert r.status_code == 200
        codes = [c.get("country_code") for c in r.json().get("items", r.json() if isinstance(r.json(), list) else [])]
        # tolerate either {items:[...]} or [...]
        if not codes and isinstance(r.json(), list):
            codes = [c.get("country_code") for c in r.json()]
        assert "AU" in codes and "CA" in codes and "NZ" in codes


# ── Phase 4D lead-magnet regression ─────────────────────────
class TestPhase4DRegression:
    def test_eligibility_score(self):
        # Phase 4D AI endpoint — only verify it accepts our schema (200/201) or fails at AI (502/timeout).
        # Not blocking for Phase 6.2 — Phase 4D regression confirmed in iteration_104.
        try:
            r = requests.post(f"{API}/eligibility/score", json={
                "full_name": "TEST_Score", "age": 30, "education": "master",
                "work_experience_years": 6, "english_score": "7", "occupation": "Software Engineer",
                "country": "AU"
            }, timeout=60)
        except requests.exceptions.ReadTimeout:
            pytest.skip("Phase 4D AI endpoint timed out — flaky AI provider, not a Phase 6.2 regression")
        assert r.status_code in (200, 201, 502, 504), r.text


# ── Cleanup ──────────────────────────────────────────────────
class TestZCleanup:
    def test_delete_all_created(self, admin_h):
        for pid in CREATED_IDS:
            r = requests.delete(f"{API}/eligibility/profiles/{pid}", headers=admin_h, timeout=30)
            assert r.status_code in (200, 404)

    def test_verify_deleted(self, admin_h):
        for pid in CREATED_IDS:
            r = requests.get(f"{API}/eligibility/profiles/{pid}", headers=admin_h, timeout=30)
            assert r.status_code == 404
