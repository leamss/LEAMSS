"""Phase 6.8.5 — Resume / Continue (PUT update) tests."""
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


def _payload(name="RESUME_TEST", naati=False):
    return {
        "client_name": name,
        "client_email": "resume@test.com",
        "client_phone": "+91-9000000000",
        "profile": {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 30},
                "education": {"highest_qualification": "bachelor"},
                "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7.0, "writing": 7.0, "speaking": 7.5}},
                "professional": {"current_profession": "SE", "years_experience_total": 6},
                "au_extras": {"naati_accredited": naati},
                "ca_extras": {}, "nz_extras": {},
            },
        },
        "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }


def test_put_updates_existing_assessment(admin_headers):
    """PUT should mutate the same id, refresh results, and bump best_total."""
    r1 = requests.post(f"{BASE}/sales/assessments", json=_payload(), headers=admin_headers, timeout=15)
    assert r1.status_code == 200
    aid = r1.json()["id"]
    base_total = r1.json()["best_total"]

    # Update with NAATI = true → should add +5
    r2 = requests.put(f"{BASE}/sales/assessments/{aid}", json=_payload(naati=True), headers=admin_headers, timeout=15)
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert d["id"] == aid, "PUT must not change the id"
    assert d["best_total"] == base_total + 5, f"NAATI should add +5: {base_total} → {d['best_total']}"

    # Confirm GET also reflects the update
    r3 = requests.get(f"{BASE}/sales/assessments/{aid}", headers=admin_headers, timeout=10)
    assert r3.json()["best_total"] == base_total + 5

    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_put_preserves_linked_pa_id(admin_headers):
    """PUT must not erase linked_pa_id or share_* fields."""
    # Seed + link PA
    r1 = requests.post(f"{BASE}/sales/assessments", json=_payload(name="RESUME_LINK"), headers=admin_headers, timeout=15)
    aid = r1.json()["id"]
    partners = requests.get(f"{BASE}/sales/assessments/partner-options", headers=admin_headers, timeout=10).json()
    pid = partners["items"][0]["id"]
    pa = requests.post(f"{BASE}/sales/assessments/{aid}/create-pa", json={"partner_id": pid}, headers=admin_headers, timeout=15).json()
    assert pa["pa_id"]

    # Now PUT to update profile
    r2 = requests.put(f"{BASE}/sales/assessments/{aid}", json=_payload(name="RESUME_LINK", naati=True), headers=admin_headers, timeout=15)
    assert r2.status_code == 200
    # Linked PA should still be present
    g = requests.get(f"{BASE}/sales/assessments/{aid}", headers=admin_headers, timeout=10).json()
    assert g.get("linked_pa_id") == pa["pa_id"]

    # Cleanup
    requests.delete(f"{BASE}/sales/assessments/orphaned-pas/{pa['pa_id']}", headers=admin_headers)
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_put_unknown_id_404(admin_headers):
    r = requests.put(f"{BASE}/sales/assessments/DOESNOTEXIST_XYZ", json=_payload(), headers=admin_headers, timeout=10)
    assert r.status_code == 404


def test_put_partner_cannot_update_admin_assessment(admin_headers):
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    p_headers = {"Authorization": f"Bearer {p.json()['token']}"}
    # Admin seeds
    r1 = requests.post(f"{BASE}/sales/assessments", json=_payload(name="RESUME_FORBID"), headers=admin_headers, timeout=15)
    aid = r1.json()["id"]
    # Partner tries to update it → 403
    r2 = requests.put(f"{BASE}/sales/assessments/{aid}", json=_payload(name="HACKED", naati=True), headers=p_headers, timeout=15)
    assert r2.status_code == 403
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_get_returns_full_profile_for_resume(admin_headers):
    """GET single must include profile_snapshot + targets + occupation for resume hydrate."""
    r1 = requests.post(f"{BASE}/sales/assessments", json=_payload(name="RESUME_GET"), headers=admin_headers, timeout=15)
    aid = r1.json()["id"]
    g = requests.get(f"{BASE}/sales/assessments/{aid}", headers=admin_headers, timeout=10).json()
    assert g["id"] == aid
    assert "profile_snapshot" in g
    assert g["profile_snapshot"]["marital_status"] == "single"
    assert "targets" in g and len(g["targets"]) >= 1
    assert g["occupation"]["code"] == "261313"
    requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)
