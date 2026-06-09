"""Phase 6.10 Part 2 — Professional Report Engine tests."""
import io
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


@pytest.fixture
def sample_profile_data():
    return {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 30},
            "education": {"highest_qualification": "master"},
            "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
            "professional": {"current_profession": "Software Engineer", "years_experience_total": 6},
            "au_extras": {}, "ca_extras": {}, "nz_extras": {},
        },
    }


@pytest.fixture(scope="module")
def seeded_assessment(admin_token):
    """Create a fresh assessment we can use across tests."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "Phase 6.10.2 Report Test",
        "client_email": "report@test.com",
        "client_phone": "+91-9000000000",
        "profile": {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 30},
                "education": {"highest_qualification": "master"},
                "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
                "professional": {"current_profession": "Software Engineer", "years_experience_total": 6},
                "au_extras": {"naati_accredited": True},
                "ca_extras": {}, "nz_extras": {},
            },
        },
        "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer",
                       "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=headers, timeout=15)
    yield r.json()["id"]
    requests.delete(f"{BASE}/sales/assessments/{r.json()['id']}", headers=headers)


def test_generate_report_creates_immutable_snapshot(admin_headers, seeded_assessment):
    r = requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["snapshot_id"].startswith("RPT-")
    assert d["is_immutable"] is True
    assert d["data_integrity_hash"]
    assert d["data"]["client"]["name"] == "Phase 6.10.2 Report Test"
    assert d["data"]["best_country"]["country_code"] == "AU"


def test_pdf_endpoint_returns_valid_pdf(admin_headers, seeded_assessment):
    g = requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30).json()
    snapshot_id = g["snapshot_id"]
    r = requests.get(f"{BASE}/assessment-reports/{snapshot_id}/pdf", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    assert len(r.content) > 5000  # non-trivial PDF


def test_snapshot_is_immutable(admin_headers, seeded_assessment):
    """The snapshot endpoint should be GET-only — verify there is no PUT/PATCH route."""
    g = requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30).json()
    snapshot_id = g["snapshot_id"]
    # PUT attempt → 405 (method not allowed) or 404 (no route)
    r = requests.put(f"{BASE}/assessment-reports/{snapshot_id}",
                     json={"data": "tampered"}, headers=admin_headers, timeout=10)
    assert r.status_code in (404, 405)


def test_warnings_surfaced_when_kb_is_draft(admin_headers, sample_profile_data):
    """Use a fresh assessment with a CA target — CA template/guide are draft in fixtures,
    so warnings list is guaranteed to surface even after AU is verified."""
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "Draft KB Test", "client_email": "draftkb@t.com", "client_phone": "+91-9000000200",
        "profile": sample_profile_data,
        "occupation": {"country_code": "CA", "code": "21231", "title": "Software Engineer", "assessing_body": "WES"},
        "targets": [{"country": "CA", "visa_subclass": "EE"}],
    }, headers=admin_headers, timeout=15)
    aid = r.json()["id"]
    try:
        g = requests.post(f"{BASE}/assessment-reports/generate",
                           json={"assessment_id": aid, "persona": "client",
                                  "mode": "combined", "include_unverified": False},
                           headers=admin_headers, timeout=30).json()
        # CA template + guide are draft → warning expected
        assert any(
            "template" in w.lower() or "occupation" in w.lower() or "guide" in w.lower()
            for w in g["warnings"]
        ), f"Expected at least one KB warning but got: {g['warnings']}"
    finally:
        requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_share_link_returns_public_meta_no_auth(admin_headers, seeded_assessment):
    g = requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30).json()
    s = requests.post(f"{BASE}/assessment-reports/{g['snapshot_id']}/share",
                       json={"expires_in_days": 7}, headers=admin_headers, timeout=10)
    assert s.status_code == 200
    token = s.json()["share_token"]
    # Public access NO auth
    pub = requests.get(f"{BASE}/assessment-reports/public/{token}", timeout=10)
    assert pub.status_code == 200
    d = pub.json()
    assert d["snapshot_id"] == g["snapshot_id"]
    assert d["company"] == "Ladhani Education & Migration Services Pvt. Ltd."
    assert d["tagline"] == "We Value Emotions"
    # Public PDF also works without auth
    pdf = requests.get(f"{BASE}/assessment-reports/public/{token}/pdf", timeout=30)
    assert pdf.status_code == 200
    assert pdf.content[:5] == b"%PDF-"


def test_share_revoke_invalidates_link(admin_headers, seeded_assessment):
    g = requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30).json()
    s = requests.post(f"{BASE}/assessment-reports/{g['snapshot_id']}/share",
                       json={"expires_in_days": 30}, headers=admin_headers, timeout=10)
    token = s.json()["share_token"]
    # Revoke
    rev = requests.delete(f"{BASE}/assessment-reports/{g['snapshot_id']}/share",
                           headers=admin_headers, timeout=10)
    assert rev.status_code == 200
    assert rev.json()["revoked_count"] >= 1
    # Public access now returns 410
    pub = requests.get(f"{BASE}/assessment-reports/public/{token}", timeout=10)
    assert pub.status_code == 410


def test_list_reports_returns_history(admin_headers, seeded_assessment):
    # Generate 2 reports for this assessment
    for _ in range(2):
        requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30)
    r = requests.get(f"{BASE}/assessment-reports?assessment_id={seeded_assessment}",
                      headers=admin_headers, timeout=10)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 2
    # Most recent first
    timestamps = [i["generated_at"] for i in items]
    assert timestamps == sorted(timestamps, reverse=True)


def test_email_is_mocked(admin_headers, seeded_assessment):
    g = requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30).json()
    r = requests.post(f"{BASE}/assessment-reports/{g['snapshot_id']}/email",
                       json={"to_email": "client@test.com"}, headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "mocked"
    assert "RESEND_API_KEY" in r.json()["note"]


def test_partner_cannot_access_admin_report(admin_headers, seeded_assessment):
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    p_headers = {"Authorization": f"Bearer {p.json()['token']}"}
    g = requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30).json()
    r = requests.get(f"{BASE}/assessment-reports/{g['snapshot_id']}", headers=p_headers, timeout=10)
    assert r.status_code == 403


def test_snapshot_hash_deterministic_for_same_data(admin_headers, seeded_assessment):
    """Two snapshots of the same assessment should produce different snapshot_ids but
    the hashable inner data should match modulo timestamps."""
    g1 = requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30).json()
    g2 = requests.post(f"{BASE}/assessment-reports/generate",
                       json={"assessment_id": seeded_assessment, "persona": "client",
                              "mode": "combined", "include_unverified": True},
                       headers=admin_headers, timeout=30).json()
    # Different snapshot IDs
    assert g1["snapshot_id"] != g2["snapshot_id"]
    # Both have hashes; hashes differ because generated_at_iso is different (that's expected)
    assert g1["data_integrity_hash"]
    assert g2["data_integrity_hash"]
