"""Phase 6.5 — Document Checklist + Save & Share Report tests."""
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


def _new_assessment(headers, **overrides):
    payload = {
        "client_name": overrides.get("client_name", "TEST_P65"),
        "client_email": overrides.get("client_email"),
        "profile": overrides.get("profile", {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 30},
                "professional": {"current_profession": "Software Engineer", "years_experience_total": 6},
                "education": {"highest_qualification": "bachelor"},
                "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
            },
        }),
        "occupation": overrides.get("occupation"),
        "targets": overrides.get("targets", [{"country": "AU", "visa_subclass": "189"}]),
    }
    r = requests.post(f"{BASE}/sales/assessments", json=payload, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ════════════════════════════════════════════════════════════════
# Checklist endpoint
# ════════════════════════════════════════════════════════════════
def test_checklist_AU_single(admin_headers):
    aid = _new_assessment(admin_headers, client_name="TEST_P65_AU_Single")
    r = requests.get(f"{BASE}/sales/assessments/{aid}/checklist", headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["template_key"] == "AU"
    assert d["stats"]["total"] >= 10
    assert d["stats"]["required"] >= 8
    # Spot-check items
    names = [it["name"] for it in d["items"]]
    assert any("Passport" in n for n in names)
    assert any("IELTS" in n or "PTE" in n for n in names)
    # Spouse docs should NOT appear for single
    assert not any(it["category"] == "Spouse" for it in d["items"])
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_checklist_AU_married_with_ACS(admin_headers):
    aid = _new_assessment(
        admin_headers,
        client_name="TEST_P65_AU_Married_ACS",
        profile={
            "marital_status": "married",
            "primary_applicant": {
                "personal": {"age": 30},
                "professional": {"current_profession": "Software Engineer", "years_experience_total": 6},
                "education": {"highest_qualification": "bachelor"},
                "language": {"scores": {"overall": 7.5}},
            },
            "spouse": {"contribution_type": "skill_assessment", "personal": {"age": 28}, "education": {"highest_qualification": "master"}},
        },
        occupation={"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"},
    )
    r = requests.get(f"{BASE}/sales/assessments/{aid}/checklist", headers=admin_headers, timeout=10)
    d = r.json()
    # ACS docs should be present
    assert any("ACS" in it["name"] for it in d["items"])
    # Spouse docs should be present for married
    assert any(it["category"] == "Spouse" for it in d["items"])
    # AU 189 pathway docs should be present
    assert any("SkillSelect" in it["name"] or "EOI" in it["name"] for it in d["items"])
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_checklist_CA_with_WES(admin_headers):
    aid = _new_assessment(
        admin_headers,
        client_name="TEST_P65_CA",
        targets=[{"country": "CA"}],
        occupation={"country_code": "CA", "code": "21231", "title": "Software Engineer", "assessing_body": "WES", "pathway": "FSW"},
    )
    r = requests.get(f"{BASE}/sales/assessments/{aid}/checklist", headers=admin_headers, timeout=10)
    d = r.json()
    assert d["template_key"] == "CA"
    # WES docs
    assert any("WES" in it["name"] for it in d["items"])
    # ECA + 6 months bank statement should be in base
    names = " ".join(it["name"] for it in d["items"])
    assert "ECA" in names or "Educational Credential Assessment" in names
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_checklist_NZ_basic(admin_headers):
    aid = _new_assessment(admin_headers, client_name="TEST_P65_NZ", targets=[{"country": "NZ"}])
    r = requests.get(f"{BASE}/sales/assessments/{aid}/checklist", headers=admin_headers, timeout=10)
    d = r.json()
    assert d["template_key"] == "NZ"
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_checklist_requires_auth():
    r = requests.get(f"{BASE}/sales/assessments/SAH-FAKE/checklist", timeout=5)
    assert r.status_code in (401, 403)


def test_checklist_unknown_id_404(admin_headers):
    r = requests.get(f"{BASE}/sales/assessments/SAH-DOESNOTEXIST/checklist", headers=admin_headers, timeout=5)
    assert r.status_code == 404


# ════════════════════════════════════════════════════════════════
# Share endpoint
# ════════════════════════════════════════════════════════════════
def test_share_create_and_public_access(admin_headers):
    aid = _new_assessment(admin_headers, client_name="TEST_P65_Share")
    # Generate share link
    r = requests.post(f"{BASE}/sales/assessments/{aid}/share", json={"expires_in_days": 7}, headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    assert d["token"]
    assert "/sales/report/" in d["public_url"]
    assert d["expires_in_days"] == 7
    assert d["expires_at"] is not None
    token = d["token"]

    # Public access — no auth header
    r2 = requests.get(f"{BASE}/sales/assessments/public/{token}", timeout=10)
    assert r2.status_code == 200, r2.text
    pub = r2.json()
    assert pub["client_name"] == "TEST_P65_Share"
    assert pub["best_country_code"] == "AU"
    assert pub["best_total"] == 75
    assert "checklist" in pub
    assert pub["checklist"]["stats"]["total"] >= 10
    # Internal fields should be stripped
    assert "created_by" not in pub  # Internal user ID
    assert "profile_snapshot" not in pub  # Detailed profile snapshot stripped

    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_share_invalid_expiry_422(admin_headers):
    aid = _new_assessment(admin_headers, client_name="TEST_P65_Expiry422")
    r = requests.post(f"{BASE}/sales/assessments/{aid}/share", json={"expires_in_days": 5}, headers=admin_headers, timeout=10)
    assert r.status_code == 422
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_share_never_expires(admin_headers):
    aid = _new_assessment(admin_headers, client_name="TEST_P65_NeverExpire")
    r = requests.post(f"{BASE}/sales/assessments/{aid}/share", json={"expires_in_days": 0}, headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["expires_at"] is None
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_share_revoke_then_410(admin_headers):
    aid = _new_assessment(admin_headers, client_name="TEST_P65_Revoke")
    r = requests.post(f"{BASE}/sales/assessments/{aid}/share", json={"expires_in_days": 30}, headers=admin_headers, timeout=10)
    token = r.json()["token"]
    # Access works
    r2 = requests.get(f"{BASE}/sales/assessments/public/{token}", timeout=10)
    assert r2.status_code == 200
    # Revoke
    r3 = requests.post(f"{BASE}/sales/assessments/{aid}/share/revoke", headers=admin_headers, timeout=10)
    assert r3.status_code == 200
    # Public access now returns 410
    r4 = requests.get(f"{BASE}/sales/assessments/public/{token}", timeout=10)
    assert r4.status_code == 410
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_public_unknown_token_404():
    r = requests.get(f"{BASE}/sales/assessments/public/NONEXISTENTTOKEN12345", timeout=5)
    assert r.status_code == 404


def test_public_tracks_click_count(admin_headers):
    aid = _new_assessment(admin_headers, client_name="TEST_P65_Tracking")
    r = requests.post(f"{BASE}/sales/assessments/{aid}/share", json={"expires_in_days": 7}, headers=admin_headers, timeout=10)
    token = r.json()["token"]
    # Hit 3 times
    for _ in range(3):
        requests.get(f"{BASE}/sales/assessments/public/{token}", timeout=10)
    # Fetch assessment (admin) → click count should be 3
    r2 = requests.get(f"{BASE}/sales/assessments/{aid}", headers=admin_headers, timeout=10)
    assert r2.json().get("share_click_count") == 3
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_share_requires_owner(admin_headers):
    # Login as partner, try to share an admin-owned assessment
    aid = _new_assessment(admin_headers, client_name="TEST_P65_OwnerCheck")
    r = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if r.status_code == 200:
        partner_tok = r.json()["token"]
        r2 = requests.post(
            f"{BASE}/sales/assessments/{aid}/share",
            json={"expires_in_days": 7},
            headers={"Authorization": f"Bearer {partner_tok}"}, timeout=10,
        )
        assert r2.status_code == 403
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)
