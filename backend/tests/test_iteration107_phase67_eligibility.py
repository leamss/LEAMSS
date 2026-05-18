"""Phase 6.7 — Eligibility Engine bug-fix regression tests.

Covers:
  1. Partner skill points — all 5 Option A/B/C/D/E scenarios (AU profiles)
  2. ProfileCreate accepts new nested Phase 6.7 structure
  3. GET assessment returns marital_status + primary_applicant_snapshot + spouse_snapshot
  4. AI prompt picks NOC code from CURRENT profession (not past education)
  5. Cache invalidation when spouse.contribution_type changes
  6. Migration endpoint /admin/migrate-v67 idempotency + RBAC
  7. Phase 6.2 regression — CRUD/duplicate/link unaffected
"""
import os
import time
import pytest
import requests

def _load_backend_url():
    val = os.environ.get("REACT_APP_BACKEND_URL", "")
    if not val:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        val = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    return val.rstrip("/")

BASE_URL = _load_backend_url()
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

ADMIN = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT = {"email": "client@leamss.com", "password": "Client@123"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(ADMIN)}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def partner_headers():
    return {"Authorization": f"Bearer {_login(PARTNER)}", "Content-Type": "application/json"}


# ────────────────────────────────────────────────────────────
# Builder
# ────────────────────────────────────────────────────────────
def _base_profile(
    name,
    marital_status="single",
    spouse=None,
    current_profession="Marketing Specialist",
    field_of_study="Marketing",
    highest_qual="bachelor",
):
    """Builds a Phase 6.7 nested profile, AU-targeted."""
    payload = {
        "name": name,
        "schema_version": 2,
        "marital_status": marital_status,
        "primary_applicant": {
            "personal": {
                "full_name": name,
                "age": 32,
                "date_of_birth": "1993-05-10",
                "current_country": "India",
                "nationality": "Indian",
                "email": f"{name.lower().replace(' ', '_')}@test.com",
            },
            "professional": {
                "current_profession": current_profession,
                "designation": current_profession,
                "industry": "Marketing/Advertising",
                "years_experience_total": 6,
            },
            "education": {
                "highest_qualification": highest_qual,
                "field_of_study": field_of_study,
            },
            "language": {
                "test_completed": True,
                "test_type": "IELTS",
                "scores": {"overall": 7.5, "listening": 7.5, "reading": 7.0, "writing": 7.0, "speaking": 7.5},
            },
        },
        "spouse": spouse,
        "dependents": [],
        "additional_factors": {},
        "preferences": {"search_mode": "specific", "specific_country": "AU"},
    }
    return payload


def _create_profile(headers, payload):
    r = requests.post(f"{BASE_URL}/api/eligibility/profiles", json=payload, headers=headers, timeout=15)
    assert r.status_code in (200, 201), f"Create failed {r.status_code} {r.text}"
    return r.json()


def _run_assessment(headers, pid, mode="specific", country="AU", force=False):
    body = {"profile_id": pid, "mode": mode, "specific_country": country, "force": force}
    r = requests.post(f"{BASE_URL}/api/eligibility/assessments/run", json=body, headers=headers, timeout=90)
    assert r.status_code == 200, f"Assessment failed {r.status_code} {r.text}"
    return r.json()


def _partner_breakdown(asmt, country_code="AU"):
    for c in asmt.get("results", []):
        if c.get("country_code") == country_code:
            return ((c.get("points") or {}).get("breakdown") or {}).get("partner")
    return None


# Track created profiles for cleanup
_created_ids = []


@pytest.fixture(scope="module", autouse=True)
def _cleanup(admin_headers):
    yield
    for pid in _created_ids:
        try:
            requests.delete(f"{BASE_URL}/api/eligibility/profiles/{pid}", headers=admin_headers, timeout=10)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════
# 1. Phase 6.7 ProfileCreate accepts new structure
# ════════════════════════════════════════════════════════════════
class TestNewProfileStructure:
    def test_create_with_new_phase67_structure(self, admin_headers):
        payload = _base_profile("TEST_67_NewStructure")
        doc = _create_profile(admin_headers, payload)
        _created_ids.append(doc["id"])
        assert doc.get("schema_version") == 2
        assert doc.get("marital_status") == "single"
        assert doc.get("primary_applicant", {}).get("personal", {}).get("full_name") == "TEST_67_NewStructure"
        # Legacy projection backwards-compat
        assert doc.get("basic_info"), "Legacy basic_info projection missing"
        assert doc.get("professional"), "Legacy professional projection missing"
        assert doc.get("education"), "Legacy education projection missing"


# ════════════════════════════════════════════════════════════════
# 2. Partner Skill Points — 5 scenarios for Australia
# ════════════════════════════════════════════════════════════════
class TestPartnerSkillPoints:
    def test_a_single_applicant(self, admin_headers):
        p = _base_profile("TEST_67_Single", marital_status="single", spouse=None)
        doc = _create_profile(admin_headers, p)
        _created_ids.append(doc["id"])
        asmt = _run_assessment(admin_headers, doc["id"])
        partner = _partner_breakdown(asmt)
        assert partner is not None, "partner breakdown missing"
        assert partner["matched_key"] == "single_or_pr_partner", partner
        assert partner["points"] == 10

    def test_b_skilled_partner_full(self, admin_headers):
        spouse = {
            "contribution_type": "skill_assessment",
            "is_applicant_on_visa": True,
            "personal": {"full_name": "Spouse SK", "age": 35},
            "language": {"test_completed": True, "scores": {"overall": 7, "listening": 7, "reading": 7, "writing": 7, "speaking": 7}},
            "professional": {"current_profession": "Software Engineer"},
        }
        p = _base_profile("TEST_67_SkilledPartner", marital_status="married", spouse=spouse)
        doc = _create_profile(admin_headers, p)
        _created_ids.append(doc["id"])
        asmt = _run_assessment(admin_headers, doc["id"])
        partner = _partner_breakdown(asmt)
        assert partner["matched_key"] == "skilled_partner", partner
        assert partner["points"] == 10

    def test_c_skilled_partner_downgrade_age(self, admin_headers):
        spouse = {
            "contribution_type": "skill_assessment",
            "is_applicant_on_visa": True,
            "personal": {"full_name": "Spouse Old", "age": 47},
            "language": {"test_completed": True, "scores": {"overall": 7, "listening": 7, "reading": 7, "writing": 7, "speaking": 7}},
        }
        p = _base_profile("TEST_67_SkilledDowngrade", marital_status="married", spouse=spouse)
        doc = _create_profile(admin_headers, p)
        _created_ids.append(doc["id"])
        asmt = _run_assessment(admin_headers, doc["id"])
        partner = _partner_breakdown(asmt)
        # Spec says: gate failure → downgrade to competent_english_only pts=5
        assert partner["matched_key"] == "competent_english_only", partner
        assert partner["points"] == 5

    def test_d_non_contributing(self, admin_headers):
        spouse = {
            "contribution_type": "non_contributing",
            "is_applicant_on_visa": True,
            "personal": {"full_name": "Spouse NC", "age": 33},
            "language": {"test_completed": False, "scores": {}},
        }
        p = _base_profile("TEST_67_NonContrib", marital_status="married", spouse=spouse)
        doc = _create_profile(admin_headers, p)
        _created_ids.append(doc["id"])
        asmt = _run_assessment(admin_headers, doc["id"])
        partner = _partner_breakdown(asmt)
        assert partner["matched_key"] == "non_contributing", partner
        assert partner["points"] == 0

    def test_e_au_pr_spouse(self, admin_headers):
        spouse = {
            "contribution_type": "australian_pr_citizen",
            "is_australian_pr_or_citizen": True,
            "is_applicant_on_visa": False,
            "personal": {"full_name": "Spouse PR", "age": 33},
        }
        p = _base_profile("TEST_67_AUPRSpouse", marital_status="married", spouse=spouse)
        doc = _create_profile(admin_headers, p)
        _created_ids.append(doc["id"])
        asmt = _run_assessment(admin_headers, doc["id"])
        partner = _partner_breakdown(asmt)
        assert partner["matched_key"] == "single_or_pr_partner", partner
        assert partner["points"] == 10

    def test_f_english_only_competent(self, admin_headers):
        spouse = {
            "contribution_type": "english_only",
            "is_applicant_on_visa": True,
            "personal": {"full_name": "Spouse Eng", "age": 33},
            "language": {"test_completed": True, "scores": {"overall": 6.5, "listening": 6.5, "reading": 6, "writing": 6, "speaking": 6.5}},
        }
        p = _base_profile("TEST_67_EngOnly", marital_status="married", spouse=spouse)
        doc = _create_profile(admin_headers, p)
        _created_ids.append(doc["id"])
        asmt = _run_assessment(admin_headers, doc["id"])
        partner = _partner_breakdown(asmt)
        assert partner["matched_key"] == "competent_english_only", partner
        assert partner["points"] == 5

    def test_g_divorced_single_points(self, admin_headers):
        p = _base_profile("TEST_67_Divorced", marital_status="divorced", spouse=None)
        doc = _create_profile(admin_headers, p)
        _created_ids.append(doc["id"])
        asmt = _run_assessment(admin_headers, doc["id"])
        partner = _partner_breakdown(asmt)
        assert partner["matched_key"] == "single_or_pr_partner", partner
        assert partner["points"] == 10


# ════════════════════════════════════════════════════════════════
# 3. Assessment returns Phase 6.7 snapshots
# ════════════════════════════════════════════════════════════════
class TestAssessmentSnapshots:
    def test_assessment_includes_new_fields(self, admin_headers):
        spouse = {
            "contribution_type": "english_only",
            "is_applicant_on_visa": True,
            "personal": {"full_name": "Snapshot Spouse", "age": 30},
            "language": {"test_completed": True, "scores": {"overall": 6.5, "listening": 6.5, "reading": 6, "writing": 6, "speaking": 6.5}},
        }
        p = _base_profile("TEST_67_Snapshot", marital_status="married", spouse=spouse)
        doc = _create_profile(admin_headers, p)
        _created_ids.append(doc["id"])
        asmt = _run_assessment(admin_headers, doc["id"])
        aid = asmt["id"]
        r = requests.get(f"{BASE_URL}/api/eligibility/assessments/{aid}", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "marital_status" in data and data["marital_status"] == "married"
        assert "primary_applicant_snapshot" in data
        assert "spouse_snapshot" in data
        assert data["spouse_snapshot"]["personal"]["full_name"] == "Snapshot Spouse"


# ════════════════════════════════════════════════════════════════
# 4. AI prompt — current profession (Marketing) NOT past education (Vet)
# ════════════════════════════════════════════════════════════════
class TestAIOccupationCodeChoice:
    def test_marketing_profession_not_vet_degree(self, admin_headers):
        p = _base_profile(
            "TEST_67_VetMarketing",
            marital_status="single",
            current_profession="Marketing Specialist",
            field_of_study="Veterinary Science",
            highest_qual="bachelor",
        )
        p["preferences"] = {"search_mode": "specific", "specific_country": "CA"}
        doc = _create_profile(admin_headers, p)
        _created_ids.append(doc["id"])
        asmt = _run_assessment(admin_headers, doc["id"], country="CA")
        # Inspect AI enrichment
        ca = next((c for c in asmt.get("results", []) if c.get("country_code") == "CA"), None)
        assert ca is not None
        ai = ca.get("ai_enrichment") or {}
        # Combine all narrative text for keyword check
        text = " ".join(
            str(v) for v in [
                ai.get("narrative", ""),
                ai.get("occupation_code_reasoning", ""),
                str(ai.get("recommended_occupation_code", "")),
            ]
        ).lower()
        # Must NOT recommend veterinary-related codes
        # NOC 10022 = advertising/marketing/PR managers, or any marketing-related NOC
        assert "marketing" in text or "advertising" in text or "10022" in text, (
            f"AI did not focus on Marketing profession. Text snippet: {text[:500]}"
        )
        # Vet code shouldn't be the recommended code (best-effort check)
        rec_code = str(ai.get("recommended_occupation_code") or "")
        assert "veterinar" not in text.split("recommended")[0] if "recommended" in text else True, text[:500]
        # Hard check: should not pick NOC 31103 (Veterinarians) as primary
        assert rec_code not in ("31103",), f"AI wrongly picked Vet NOC: {rec_code}"


# ════════════════════════════════════════════════════════════════
# 5. Cache invalidation when spouse.contribution_type changes
# ════════════════════════════════════════════════════════════════
class TestCacheInvalidation:
    def test_contribution_type_change_invalidates_cache(self, admin_headers):
        spouse = {
            "contribution_type": "skill_assessment",
            "is_applicant_on_visa": True,
            "personal": {"full_name": "Cache Spouse", "age": 33},
            "language": {"test_completed": True, "scores": {"overall": 7, "listening": 7, "reading": 7, "writing": 7, "speaking": 7}},
        }
        p = _base_profile("TEST_67_Cache", marital_status="married", spouse=spouse)
        doc = _create_profile(admin_headers, p)
        pid = doc["id"]
        _created_ids.append(pid)
        a1 = _run_assessment(admin_headers, pid)
        partner1 = _partner_breakdown(a1)
        assert partner1["points"] == 10

        # PATCH spouse.contribution_type → non_contributing
        new_spouse = {**spouse, "contribution_type": "non_contributing"}
        r = requests.patch(
            f"{BASE_URL}/api/eligibility/profiles/{pid}",
            json={"spouse": new_spouse},
            headers=admin_headers,
            timeout=15,
        )
        assert r.status_code == 200, r.text

        a2 = _run_assessment(admin_headers, pid)
        partner2 = _partner_breakdown(a2)
        # Cache key should have changed → fresh result
        assert partner2["matched_key"] == "non_contributing"
        assert partner2["points"] == 0
        # And confirm not from cache
        assert a2.get("from_cache") is False or a1["id"] != a2["id"]


# ════════════════════════════════════════════════════════════════
# 6. Migration endpoint
# ════════════════════════════════════════════════════════════════
class TestMigrationEndpoint:
    def test_migrate_idempotent(self, admin_headers):
        r1 = requests.post(f"{BASE_URL}/api/eligibility/profiles/admin/migrate-v67", headers=admin_headers, timeout=60)
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert d1.get("ok") is True
        r2 = requests.post(f"{BASE_URL}/api/eligibility/profiles/admin/migrate-v67", headers=admin_headers, timeout=60)
        assert r2.status_code == 200
        d2 = r2.json()
        # Already-migrated count should equal total minus newly migrated; second run migrated should be 0
        assert d2.get("migrated", 0) == 0, f"Second run was not idempotent: {d2}"

    def test_migrate_partner_forbidden(self, partner_headers):
        r = requests.post(f"{BASE_URL}/api/eligibility/profiles/admin/migrate-v67", headers=partner_headers, timeout=30)
        assert r.status_code == 403


# ════════════════════════════════════════════════════════════════
# 7. Phase 6.2 regression — basic CRUD still works
# ════════════════════════════════════════════════════════════════
class TestPhase62Regression:
    def test_list_endpoint(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/eligibility/profiles?limit=5", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data or isinstance(data, list)

    def test_stats_me(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/eligibility/profiles/stats/me", headers=admin_headers, timeout=15)
        assert r.status_code == 200

    def test_client_403(self):
        token = _login(CLIENT)
        h = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{BASE_URL}/api/eligibility/profiles", headers=h, timeout=10)
        assert r.status_code == 403
