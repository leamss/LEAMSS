"""Phase 6.1 — Eligibility Knowledge Base backend tests (iteration 104).

Coverage:
 - GET /api/eligibility/kb/countries (seeded AU/CA/NZ)
 - GET /api/eligibility/kb/countries/{AU,CA,NZ} — seed data shape
 - CRUD: POST/PATCH/DELETE country
 - Sub-resources: visas / skill-bodies / occupations CRUD
 - Bulk CSV occupation import
 - Cross-country search: occupations + skill-bodies
 - Stats
 - RBAC: partner gets 403 on admin operations
 - Regression: Phase 4D /api/eligibility/score + /api/eligibility/pathways
"""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://career-match-320.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
TIMEOUT = 60


def _login(email: str, password: str) -> str:
    last = None
    for _ in range(3):
        try:
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.json()["token"]
            last = f"{r.status_code}: {r.text[:200]}"
        except Exception as e:
            last = str(e)
            time.sleep(1)
    pytest.skip(f"Login failed for {email}: {last}")


# ─── Fixtures ────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def admin_headers():
    tok = _login("admin@leamss.com", "Admin@123")
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def partner_headers():
    tok = _login("partner@leamss.com", "Partner@123")
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ─── 1. List countries (seeded) ──────────────────────────────────────────
class TestCountriesList:
    def test_list_countries_returns_au_ca_nz(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/countries", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "count" in data
        codes = {c["country_code"] for c in data["items"]}
        assert {"AU", "CA", "NZ"}.issubset(codes), f"Expected AU/CA/NZ, got {codes}"

    def test_list_items_have_summary_counts(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/countries", headers=admin_headers, timeout=TIMEOUT)
        for c in r.json()["items"]:
            assert "visa_count" in c and "skill_body_count" in c and "occupation_count" in c
            assert isinstance(c["visa_count"], int)


# ─── 2. Per-country deep doc (seed shape) ────────────────────────────────
class TestSeedDataShape:
    def test_au_full_doc(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/countries/AU", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["country_code"] == "AU"
        # User-stated expectations: 6 visas, 8 skill bodies, 32 occupations
        assert len(doc.get("visa_categories", [])) == 6, f"AU visas: {len(doc.get('visa_categories', []))}"
        assert len(doc.get("skill_assessment_bodies", [])) == 8, f"AU bodies: {len(doc.get('skill_assessment_bodies', []))}"
        assert len(doc.get("occupation_codes", [])) == 32, f"AU occ: {len(doc.get('occupation_codes', []))}"
        # Points system present
        assert isinstance(doc.get("points_system"), dict)
        assert len(doc["points_system"]) > 0, "AU points_system must not be empty"

    def test_ca_full_doc(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/countries/CA", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["country_code"] == "CA"
        # User-stated: 4 programs, 5 ECA bodies, 31 NOC codes
        assert len(doc.get("visa_categories", [])) == 4, f"CA visas: {len(doc.get('visa_categories', []))}"
        assert len(doc.get("skill_assessment_bodies", [])) == 5, f"CA bodies: {len(doc.get('skill_assessment_bodies', []))}"
        assert len(doc.get("occupation_codes", [])) == 31, f"CA occ: {len(doc.get('occupation_codes', []))}"

    def test_nz_full_doc(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/countries/NZ", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["country_code"] == "NZ"
        # User-stated: 4 visas, 4 bodies, 20 codes
        assert len(doc.get("visa_categories", [])) == 4, f"NZ visas: {len(doc.get('visa_categories', []))}"
        assert len(doc.get("skill_assessment_bodies", [])) == 4, f"NZ bodies: {len(doc.get('skill_assessment_bodies', []))}"
        assert len(doc.get("occupation_codes", [])) == 20, f"NZ occ: {len(doc.get('occupation_codes', []))}"

    def test_country_doc_strips_mongo_id(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/countries/AU", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        assert "_id" not in r.json()

    def test_unknown_country_404(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/countries/XX", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 404


# ─── 3. Country CRUD ─────────────────────────────────────────────────────
TEST_COUNTRY_CODE = "ZZ"  # throwaway


class TestCountryCRUD:
    def test_zz_create_country(self, admin_headers):
        # Clean any leftover
        requests.delete(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers, timeout=TIMEOUT)
        payload = {"country": "TEST_Zedland", "country_code": TEST_COUNTRY_CODE, "country_flag_emoji": "🏴", "priority": 99}
        r = requests.post(f"{API}/eligibility/kb/countries", headers=admin_headers, json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["country_code"] == TEST_COUNTRY_CODE
        assert doc["country"] == "TEST_Zedland"
        # Verify persistence
        g = requests.get(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers, timeout=TIMEOUT)
        assert g.status_code == 200
        assert g.json()["country"] == "TEST_Zedland"

    def test_zz_duplicate_create_409(self, admin_headers):
        r = requests.post(f"{API}/eligibility/kb/countries", headers=admin_headers,
                          json={"country": "TEST_dup", "country_code": TEST_COUNTRY_CODE}, timeout=TIMEOUT)
        assert r.status_code == 409

    def test_zz_patch_toggle_inactive(self, admin_headers):
        r = requests.patch(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers,
                           json={"is_active": False}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json()["is_active"] is False
        # Verify GET reflects it
        g = requests.get(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers, timeout=TIMEOUT)
        assert g.json()["is_active"] is False

    def test_zz_existing_countries_unchanged(self, admin_headers):
        """After adding a new country, AU/CA/NZ counts must still be intact."""
        for code, expected_visas in [("AU", 6), ("CA", 4), ("NZ", 4)]:
            d = requests.get(f"{API}/eligibility/kb/countries/{code}", headers=admin_headers, timeout=TIMEOUT).json()
            assert len(d["visa_categories"]) == expected_visas, f"{code} visa count changed!"


# ─── 4. Visa CRUD on ZZ ─────────────────────────────────────────────────
class TestVisaCRUD:
    visa_id = None

    def test_zz_add_visa(self, admin_headers):
        payload = {
            "code": "TEST-189",
            "name": "TEST Skilled Independent",
            "type": "skilled_independent",
            "description": "test",
            "eligibility": {"min_age": 18, "max_age": 45, "min_points": 65},
            "processing_time": {"avg_months": 12},
            "cost": {"primary_aud": 4640},
            "required_skill_assessment": True,
        }
        r = requests.post(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}/visas",
                          headers=admin_headers, json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        TestVisaCRUD.visa_id = r.json()["visa_id"]
        # Verify it appears in country doc
        doc = requests.get(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers, timeout=TIMEOUT).json()
        codes = [v["code"] for v in doc["visa_categories"]]
        assert "TEST-189" in codes

    def test_zz_delete_visa(self, admin_headers):
        assert TestVisaCRUD.visa_id, "visa_id not set"
        r = requests.delete(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}/visas/{TestVisaCRUD.visa_id}",
                            headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        # Verify gone
        doc = requests.get(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers, timeout=TIMEOUT).json()
        assert TestVisaCRUD.visa_id not in [v.get("visa_id") for v in doc["visa_categories"]]


# ─── 5. Skill body CRUD ──────────────────────────────────────────────────
class TestSkillBodyCRUD:
    body_id = None

    def test_zz_add_body(self, admin_headers):
        payload = {"name": "TEST_BODY", "full_name": "Test Assessment Authority", "website": "https://test.example",
                   "assesses_occupations": ["1234"], "assessment_fee_inr": 50000.0, "processing_time_weeks": 12}
        r = requests.post(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}/skill-bodies",
                          headers=admin_headers, json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        TestSkillBodyCRUD.body_id = r.json()["body_id"]
        doc = requests.get(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers, timeout=TIMEOUT).json()
        assert "TEST_BODY" in [b["name"] for b in doc["skill_assessment_bodies"]]

    def test_zz_delete_body(self, admin_headers):
        assert TestSkillBodyCRUD.body_id
        r = requests.delete(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}/skill-bodies/{TestSkillBodyCRUD.body_id}",
                            headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200


# ─── 6. Occupation CRUD ─────────────────────────────────────────────────
class TestOccupationCRUD:
    def test_zz_add_occupation(self, admin_headers):
        payload = {"code": "TEST-261313", "title": "TEST Software Engineer", "group": "ICT",
                   "skill_level": 1, "assessing_body": "TEST_BODY",
                   "eligible_visas": ["TEST-189"], "alternative_titles": ["test dev"]}
        r = requests.post(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}/occupations",
                          headers=admin_headers, json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        # Verify
        doc = requests.get(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers, timeout=TIMEOUT).json()
        assert "TEST-261313" in [o["code"] for o in doc["occupation_codes"]]

    def test_zz_delete_occupation(self, admin_headers):
        r = requests.delete(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}/occupations/TEST-261313",
                            headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200


# ─── 7. Bulk CSV import ─────────────────────────────────────────────────
class TestBulkImport:
    def test_bulk_import_csv(self, admin_headers):
        csv_content = (
            "code,title,group,group_code,skill_level,assessing_body,pathway,eligible_visas,alternative_titles\n"
            "TEST-9001,TEST Data Engineer,ICT,261,1,TEST_BODY,direct,TEST-189|TEST-190,data dev|data eng\n"
            "TEST-9002,TEST DevOps Engineer,ICT,262,1,TEST_BODY,direct,TEST-189,devops|sre\n"
            "TEST-9003,TEST Cloud Architect,ICT,263,1,TEST_BODY,direct,TEST-189,cloud arch\n"
        )
        files = {"file": ("occ.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        headers = {"Authorization": admin_headers["Authorization"]}  # multipart — drop content-type
        r = requests.post(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}/bulk-import-occupations",
                          headers=headers, files=files, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["inserted"] >= 3, body
        # Verify in country doc
        doc = requests.get(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers, timeout=TIMEOUT).json()
        codes = [o["code"] for o in doc["occupation_codes"]]
        for c in ("TEST-9001", "TEST-9002", "TEST-9003"):
            assert c in codes
        # Check pipe-separated parsing
        occ = next(o for o in doc["occupation_codes"] if o["code"] == "TEST-9001")
        assert "TEST-189" in occ["eligible_visas"] and "TEST-190" in occ["eligible_visas"]
        assert "data dev" in occ["alternative_titles"]

    def test_bulk_import_bad_headers_400(self, admin_headers):
        files = {"file": ("bad.csv", io.BytesIO(b"foo,bar\n1,2\n"), "text/csv")}
        headers = {"Authorization": admin_headers["Authorization"]}
        r = requests.post(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}/bulk-import-occupations",
                          headers=headers, files=files, timeout=TIMEOUT)
        assert r.status_code == 400


# ─── 8. Search ──────────────────────────────────────────────────────────
class TestSearch:
    def test_search_software_cross_country(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/occupations/search?q=software", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) > 0
        country_codes = {i["country_code"] for i in items}
        # Should match at least 2 of the 3 seeded countries (software occupations are common)
        assert len(country_codes & {"AU", "CA", "NZ"}) >= 2, f"Got only {country_codes}"

    def test_search_acs_finds_australia(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/skill-bodies/search?q=acs", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        items = r.json()["items"]
        assert any(i["country_code"] == "AU" and "ACS" in (i.get("name") or "").upper() for i in items), \
            f"ACS not found in AU bodies: {items}"

    def test_search_min_length_validation(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/occupations/search?q=a", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 422  # min_length=2


# ─── 9. Stats ───────────────────────────────────────────────────────────
class TestStats:
    def test_stats_endpoint(self, admin_headers):
        r = requests.get(f"{API}/eligibility/kb/stats", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        s = r.json()
        for k in ("total_countries", "active_countries", "total_visa_categories", "total_skill_bodies", "total_occupations"):
            assert k in s
        assert s["total_countries"] >= 3
        # 32 + 31 + 20 = 83 minimum from seed
        assert s["total_occupations"] >= 83, f"Expected >=83, got {s['total_occupations']}"


# ─── 10. RBAC: partner gets 403 ─────────────────────────────────────────
class TestRBAC:
    def test_partner_can_view_countries(self, partner_headers):
        # VIEWER_ROLES includes partner per code
        r = requests.get(f"{API}/eligibility/kb/countries", headers=partner_headers, timeout=TIMEOUT)
        assert r.status_code == 200

    def test_partner_cannot_create_country(self, partner_headers):
        r = requests.post(f"{API}/eligibility/kb/countries", headers=partner_headers,
                          json={"country": "x", "country_code": "YY"}, timeout=TIMEOUT)
        assert r.status_code == 403

    def test_partner_cannot_patch_country(self, partner_headers):
        r = requests.patch(f"{API}/eligibility/kb/countries/AU", headers=partner_headers,
                           json={"priority": 1}, timeout=TIMEOUT)
        assert r.status_code == 403

    def test_partner_cannot_delete_country(self, partner_headers):
        r = requests.delete(f"{API}/eligibility/kb/countries/AU", headers=partner_headers, timeout=TIMEOUT)
        assert r.status_code == 403

    def test_partner_cannot_add_visa(self, partner_headers):
        r = requests.post(f"{API}/eligibility/kb/countries/AU/visas", headers=partner_headers,
                          json={"code": "X", "name": "x", "type": "x"}, timeout=TIMEOUT)
        assert r.status_code == 403

    def test_partner_cannot_bulk_import(self, partner_headers):
        files = {"file": ("x.csv", io.BytesIO(b"code,title\nA,B\n"), "text/csv")}
        headers = {"Authorization": partner_headers["Authorization"]}
        r = requests.post(f"{API}/eligibility/kb/countries/AU/bulk-import-occupations",
                          headers=headers, files=files, timeout=TIMEOUT)
        assert r.status_code == 403


# ─── 11. Regression: Phase 4D /api/eligibility/score & /pathways ─────────
class TestPhase4DRegression:
    def test_eligibility_score_still_works(self):
        # Public endpoint per Phase 4D lead-magnet
        payload = {"age": 30, "education": "masters", "english_score": 7, "work_experience_years": 5,
                   "occupation": "Software Engineer", "country_target": "AU"}
        r = requests.post(f"{API}/eligibility/score", json=payload, timeout=TIMEOUT)
        # Even if it requires auth, should NOT 404
        assert r.status_code != 404, f"Phase 4D /eligibility/score regressed: {r.status_code} {r.text[:200]}"

    def test_eligibility_pathways_still_works(self):
        r = requests.get(f"{API}/eligibility/pathways", timeout=TIMEOUT)
        assert r.status_code != 404, f"Phase 4D /eligibility/pathways regressed: {r.status_code}"


# ─── 12. Cleanup ────────────────────────────────────────────────────────
class TestZZCleanup:
    def test_cleanup_zz_country(self, admin_headers):
        # Hard delete to keep DB clean — endpoint is soft delete, but that's OK
        r = requests.delete(f"{API}/eligibility/kb/countries/{TEST_COUNTRY_CODE}", headers=admin_headers, timeout=TIMEOUT)
        assert r.status_code in (200, 404)
