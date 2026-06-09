"""Phase 6.7 Part 2 — Pre-Analysis Verification + Resume Extract + Client Info-Sheet.

Tests:
  A) GET /api/eligibility/profiles/{id}/completeness — score + RBAC + ready flag
  B) POST /api/eligibility/profiles/resume-extract — file validation + RBAC
  C) POST /api/eligibility/info-sheet/generate-link — admin/partner create link
  D) GET  /api/eligibility/info-sheet/public/{token}  — no-auth, error handling
  E) POST /api/eligibility/info-sheet/public/{token}/submit — no-auth, status flip
  F) GET  /api/eligibility/info-sheet/pending — admin/partner queue
  G) POST /api/eligibility/info-sheet/{profile_id}/approve — flip to complete
  H) POST /api/eligibility/info-sheet/revoke/{token} — revoke flow
"""
import io
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://compliance-hub-751.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT = {"email": "client@leamss.com", "password": "Client@123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Login failed for {creds['email']}: {r.status_code} {r.text}")
    token = r.json().get("access_token") or r.json().get("token")
    return token


@pytest.fixture(scope="session")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="session")
def partner_token():
    return _login(PARTNER)


@pytest.fixture(scope="session")
def client_token():
    return _login(CLIENT)


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


# Track created profiles / tokens to clean up at session end
_created_profiles = []
_created_tokens = []


@pytest.fixture(scope="session", autouse=True)
def _cleanup(admin_token):
    yield
    h = _hdr(admin_token)
    for pid in _created_profiles:
        try:
            requests.delete(f"{API}/eligibility/profiles/{pid}", headers=h, timeout=10)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _full_profile_payload(name: str = "TEST_67P2_Full"):
    return {
        "name": name,
        "email": f"{name.lower()}@example.com",
        "phone": "+919999999999",
        "marital_status": "single",
        "schema_version": 2,
        "primary_applicant": {
            "personal": {
                "full_name": name,
                "date_of_birth": "1990-04-12",
                "nationality": "Indian",
                "current_country": "India",
                "current_city": "Mumbai",
                "age": 35,
            },
            "professional": {
                "current_profession": "Software Engineer",
                "designation": "Senior Engineer",
                "years_experience_total": 10,
                "industry": "IT",
                "employer_name": "ACME Corp",
            },
            "education": {
                "highest_qualification": "master",
                "field_of_study": "Computer Science",
                "year_completed": 2015,
                "country": "India",
            },
            "language": {
                "primary_test": "IELTS",
                "test_completed": True,
                "scores": {"overall": 7.5, "listening": 8, "reading": 7.5, "writing": 7, "speaking": 7.5},
            },
            "work_history": [
                {"employer": "ACME Corp", "designation": "Sr Engineer", "from": "2018-01", "to": None}
            ],
        },
        "preferences": {"search_mode": "top_3", "preferred_countries": [], "timeline_months": 12},
        "additional_factors": {"criminal_record": False},
    }


def _create_profile(token, payload):
    r = requests.post(f"{API}/eligibility/profiles", json=payload, headers=_hdr(token), timeout=20)
    assert r.status_code in (200, 201), f"create failed: {r.status_code} {r.text}"
    pid = r.json().get("id")
    _created_profiles.append(pid)
    return pid


# ═══════════════════════════════════════════════════════════════
# A) Completeness API
# ═══════════════════════════════════════════════════════════════
class TestCompleteness:

    def test_requires_auth(self):
        # use a known existing profile id; any id is fine because auth checks first
        r = requests.get(f"{API}/eligibility/profiles/ELG-FAKE-0001/completeness", timeout=10)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_high_score_full_profile(self, admin_token):
        pid = _create_profile(admin_token, _full_profile_payload("TEST_67P2_HighScore"))
        r = requests.get(f"{API}/eligibility/profiles/{pid}/completeness", headers=_hdr(admin_token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "score" in data and isinstance(data["score"], int)
        assert "sections" in data and len(data["sections"]) == 8
        section_keys = [s["key"] for s in data["sections"]]
        for expected in ["personal", "professional", "education", "language", "marital", "spouse", "preferences", "additional"]:
            assert expected in section_keys
        assert data["score"] >= 80, f"Expected high score >=80, got {data['score']} - sections={data['sections']}"
        assert data["ready_for_assessment"] is True
        # Spouse N/A — single → full credit
        spouse_section = next(s for s in data["sections"] if s["key"] == "spouse")
        assert spouse_section["score"] == 100

    def test_low_score_empty_profile(self, admin_token):
        payload = {"name": "TEST_67P2_Empty", "schema_version": 2, "primary_applicant": {}, "preferences": {}}
        pid = _create_profile(admin_token, payload)
        r = requests.get(f"{API}/eligibility/profiles/{pid}/completeness", headers=_hdr(admin_token), timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data["score"] < 40, f"Expected <40, got {data['score']}"
        assert len(data["blockers"]) > 0, "Expected blockers on near-empty profile"

    def test_spouse_section_married_without_contribution(self, admin_token):
        payload = _full_profile_payload("TEST_67P2_MarriedNoContrib")
        payload["marital_status"] = "married"
        payload["spouse"] = {"personal": {"full_name": "Spouse", "age": 30}, "contribution_type": "not_applicable"}
        pid = _create_profile(admin_token, payload)
        r = requests.get(f"{API}/eligibility/profiles/{pid}/completeness", headers=_hdr(admin_token), timeout=20)
        assert r.status_code == 200
        data = r.json()
        spouse_section = next(s for s in data["sections"] if s["key"] == "spouse")
        # married + not_applicable → degraded score (0.2 → 20)
        assert spouse_section["score"] <= 30, f"Expected low spouse score, got {spouse_section['score']}"

    def test_rbac_non_owner_403(self, admin_token, client_token):
        # admin creates a profile; client (non-owner) should get 403
        pid = _create_profile(admin_token, _full_profile_payload("TEST_67P2_RBAC"))
        r = requests.get(f"{API}/eligibility/profiles/{pid}/completeness", headers=_hdr(client_token), timeout=10)
        assert r.status_code in (403, 401), f"Expected 403 for non-owner client, got {r.status_code} {r.text}"


# ═══════════════════════════════════════════════════════════════
# B) Resume Extract
# ═══════════════════════════════════════════════════════════════
class TestResumeExtract:

    def test_unsupported_file_type_rejected(self, admin_token):
        files = {"file": ("resume.jpg", io.BytesIO(b"\xff\xd8\xff\xe0" + b"x" * 500), "image/jpeg")}
        r = requests.post(f"{API}/eligibility/profiles/resume-extract", files=files, headers=_hdr(admin_token), timeout=30)
        assert r.status_code == 400, f"Expected 400 for jpg, got {r.status_code} {r.text}"

    def test_empty_file_rejected(self, admin_token):
        files = {"file": ("empty.txt", io.BytesIO(b"abc"), "text/plain")}
        r = requests.post(f"{API}/eligibility/profiles/resume-extract", files=files, headers=_hdr(admin_token), timeout=15)
        assert r.status_code == 400

    def test_oversized_file_rejected(self, admin_token):
        big = io.BytesIO(b"x" * (10 * 1024 * 1024 + 100))
        files = {"file": ("big.txt", big, "text/plain")}
        r = requests.post(f"{API}/eligibility/profiles/resume-extract", files=files, headers=_hdr(admin_token), timeout=60)
        assert r.status_code == 413

    def test_client_rbac_403(self, client_token):
        with open("/tmp/test_resume.txt", "rb") as f:
            files = {"file": ("resume.txt", f, "text/plain")}
            r = requests.post(f"{API}/eligibility/profiles/resume-extract", files=files, headers=_hdr(client_token), timeout=30)
        assert r.status_code == 403

    def test_partner_can_call_with_valid_txt(self, partner_token):
        with open("/tmp/test_resume.txt", "rb") as f:
            files = {"file": ("resume.txt", f, "text/plain")}
            r = requests.post(f"{API}/eligibility/profiles/resume-extract", files=files, headers=_hdr(partner_token), timeout=120)
        # AI budget may be exhausted → 502 is acceptable per requirements
        if r.status_code == 502:
            assert "detail" in r.json() or "error" in r.json()
            pytest.skip(f"AI budget exhausted (expected). Detail: {r.json()}")
        assert r.status_code == 200, f"Expected 200 or 502, got {r.status_code} {r.text}"
        data = r.json()
        # When AI returns OK, expect Phase 6.7 shape
        assert "primary_applicant" in data or "_ai_status" in data or "_source_meta" in data


# ═══════════════════════════════════════════════════════════════
# C+D+E) Info-Sheet generate / public-get / public-submit
# ═══════════════════════════════════════════════════════════════
class TestInfoSheetFlow:

    def test_generate_link_admin_no_profile(self, admin_token):
        body = {"client_name": "TEST_67P2_NewClient", "expires_in_days": 7}
        r = requests.post(f"{API}/eligibility/info-sheet/generate-link", json=body, headers=_hdr(admin_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["token"] and len(data["token"]) > 10
        assert data["profile_id"].startswith("ELG-")
        assert data["public_url"].startswith("https://compliance-hub-751.preview.emergentagent.com/info-sheet/"), f"public_url wrong: {data['public_url']}"
        _created_profiles.append(data["profile_id"])
        _created_tokens.append(data["token"])

    def test_generate_link_client_403(self, client_token):
        r = requests.post(f"{API}/eligibility/info-sheet/generate-link", json={"client_name": "X"}, headers=_hdr(client_token), timeout=10)
        assert r.status_code == 403

    def test_public_get_invalid_token_404(self):
        r = requests.get(f"{API}/eligibility/info-sheet/public/nope-not-real-token-12345", timeout=10)
        assert r.status_code == 404

    def test_public_get_no_auth_required(self, admin_token):
        # Generate fresh link
        body = {"client_name": "TEST_67P2_PubGet", "expires_in_days": 7}
        r = requests.post(f"{API}/eligibility/info-sheet/generate-link", json=body, headers=_hdr(admin_token), timeout=15)
        token = r.json()["token"]
        pid = r.json()["profile_id"]
        _created_profiles.append(pid)
        _created_tokens.append(token)
        # GET without auth header
        r2 = requests.get(f"{API}/eligibility/info-sheet/public/{token}", timeout=10)
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert data["ok"] is True
        assert "prefill" in data
        assert "invited_by" in data

    def test_public_submit_flow_and_reuse_410(self, admin_token):
        # Generate link
        body = {"client_name": "TEST_67P2_SubmitFlow", "expires_in_days": 7}
        r = requests.post(f"{API}/eligibility/info-sheet/generate-link", json=body, headers=_hdr(admin_token), timeout=15)
        token = r.json()["token"]
        pid = r.json()["profile_id"]
        _created_profiles.append(pid)
        _created_tokens.append(token)
        # Submit (no auth)
        sub = {
            "full_name": "TEST_67P2 Submitted Client",
            "email": "submitted@example.com",
            "phone": "+919876543210",
            "marital_status": "married",
            "current_profession": "Data Analyst",
            "years_experience_total": 6,
            "highest_qualification": "bachelor",
            "field_of_study": "Statistics",
            "language_test_taken": True,
            "language_overall_score": 7.0,
            "spouse_full_name": "TEST Spouse",
            "spouse_age": 33,
            "spouse_profession": "Designer",
            "spouse_english_overall": 6.5,
            "preferred_countries": ["AU"],
            "timeline_months": 12,
        }
        r2 = requests.post(f"{API}/eligibility/info-sheet/public/{token}/submit", json=sub, timeout=15)
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        assert body2["ok"] is True
        assert body2["status"] == "pending_review"
        # Verify profile flipped to pending_review with spouse mapped
        r3 = requests.get(f"{API}/eligibility/profiles/{pid}", headers=_hdr(admin_token), timeout=10)
        assert r3.status_code == 200
        p = r3.json()
        assert p["status"] == "pending_review"
        assert p.get("spouse") is not None, "Spouse block expected for married submission"
        assert (p["spouse"].get("personal") or {}).get("full_name") == "TEST Spouse"
        # Token reuse should 410
        r4 = requests.post(f"{API}/eligibility/info-sheet/public/{token}/submit", json=sub, timeout=10)
        assert r4.status_code == 410
        # GET on used token also 410
        r5 = requests.get(f"{API}/eligibility/info-sheet/public/{token}", timeout=10)
        assert r5.status_code == 410

    def test_public_submit_single_no_spouse_block(self, admin_token):
        body = {"client_name": "TEST_67P2_SingleSubmit", "expires_in_days": 7}
        r = requests.post(f"{API}/eligibility/info-sheet/generate-link", json=body, headers=_hdr(admin_token), timeout=15)
        token = r.json()["token"]
        pid = r.json()["profile_id"]
        _created_profiles.append(pid)
        _created_tokens.append(token)
        sub = {
            "full_name": "TEST_67P2 Single User",
            "marital_status": "single",
            "current_profession": "Accountant",
            "spouse_full_name": "ShouldBeIgnored",
        }
        r2 = requests.post(f"{API}/eligibility/info-sheet/public/{token}/submit", json=sub, timeout=15)
        assert r2.status_code == 200
        r3 = requests.get(f"{API}/eligibility/profiles/{pid}", headers=_hdr(admin_token), timeout=10)
        p = r3.json()
        assert p.get("spouse") in (None, {}), f"Single → no spouse block, got {p.get('spouse')}"


# ═══════════════════════════════════════════════════════════════
# F) Pending queue
# ═══════════════════════════════════════════════════════════════
class TestPendingQueue:

    def test_pending_admin_returns_items(self, admin_token):
        r = requests.get(f"{API}/eligibility/info-sheet/pending", headers=_hdr(admin_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and isinstance(data["items"], list)
        assert "count" in data

    def test_pending_client_403(self, client_token):
        r = requests.get(f"{API}/eligibility/info-sheet/pending", headers=_hdr(client_token), timeout=10)
        assert r.status_code == 403

    def test_pending_partner_scoped(self, partner_token):
        r = requests.get(f"{API}/eligibility/info-sheet/pending", headers=_hdr(partner_token), timeout=10)
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════
# G) Approve
# ═══════════════════════════════════════════════════════════════
class TestApprove:

    def _make_pending(self, admin_token):
        body = {"client_name": "TEST_67P2_Approve", "expires_in_days": 7}
        r = requests.post(f"{API}/eligibility/info-sheet/generate-link", json=body, headers=_hdr(admin_token), timeout=15)
        token = r.json()["token"]
        pid = r.json()["profile_id"]
        _created_profiles.append(pid)
        _created_tokens.append(token)
        sub = {"full_name": "TEST_67P2 ApproveMe", "marital_status": "married", "spouse_full_name": "TS", "spouse_age": 31}
        requests.post(f"{API}/eligibility/info-sheet/public/{token}/submit", json=sub, timeout=15)
        return pid

    def test_admin_approve_flips_to_complete(self, admin_token):
        pid = self._make_pending(admin_token)
        r = requests.post(f"{API}/eligibility/info-sheet/{pid}/approve", json={"note": "ok"}, headers=_hdr(admin_token), timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "complete"
        # Verify
        r2 = requests.get(f"{API}/eligibility/profiles/{pid}", headers=_hdr(admin_token), timeout=10)
        assert r2.json()["status"] == "complete"

    def test_approve_with_spouse_contribution(self, admin_token):
        pid = self._make_pending(admin_token)
        r = requests.post(f"{API}/eligibility/info-sheet/{pid}/approve",
                         json={"note": "approved with eng_only", "spouse_contribution_type": "english_only"},
                         headers=_hdr(admin_token), timeout=15)
        assert r.status_code == 200
        r2 = requests.get(f"{API}/eligibility/profiles/{pid}", headers=_hdr(admin_token), timeout=10)
        spouse = r2.json().get("spouse") or {}
        assert spouse.get("contribution_type") == "english_only"

    def test_approve_non_pending_400(self, admin_token):
        pid = self._make_pending(admin_token)
        # First approve
        requests.post(f"{API}/eligibility/info-sheet/{pid}/approve", json={}, headers=_hdr(admin_token), timeout=15)
        # Second approve → 400
        r = requests.post(f"{API}/eligibility/info-sheet/{pid}/approve", json={}, headers=_hdr(admin_token), timeout=10)
        assert r.status_code == 400

    def test_approve_partner_non_inviter_403(self, admin_token, partner_token):
        pid = self._make_pending(admin_token)  # invited_by = admin
        r = requests.post(f"{API}/eligibility/info-sheet/{pid}/approve", json={}, headers=_hdr(partner_token), timeout=10)
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════
# H) Revoke
# ═══════════════════════════════════════════════════════════════
class TestRevoke:
    def test_revoke_admin_succeeds(self, admin_token):
        body = {"client_name": "TEST_67P2_Revoke", "expires_in_days": 7}
        r = requests.post(f"{API}/eligibility/info-sheet/generate-link", json=body, headers=_hdr(admin_token), timeout=15)
        token = r.json()["token"]
        _created_profiles.append(r.json()["profile_id"])
        _created_tokens.append(token)
        r2 = requests.post(f"{API}/eligibility/info-sheet/revoke/{token}", headers=_hdr(admin_token), timeout=10)
        assert r2.status_code == 200
        assert r2.json()["ok"] is True

    def test_revoke_invalid_token_404(self, admin_token):
        r = requests.post(f"{API}/eligibility/info-sheet/revoke/nope-not-real-token", headers=_hdr(admin_token), timeout=10)
        assert r.status_code == 404
