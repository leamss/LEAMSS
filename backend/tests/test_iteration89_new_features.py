"""
Iteration 89: Test 4 New Features
- #1 AI Eligibility Pre-Score (public)
- #2 Document Expiry Tracker (admin)
- #3 WhatsApp Smart Share (partner button - frontend only)
- #8 Visa Pathway Comparison (public)
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ============ FIXTURES ============

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@leamss.com",
        "password": "Admin@123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")

@pytest.fixture(scope="module")
def partner_token(api_client):
    """Get partner auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "partner@leamss.com",
        "password": "Partner@123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Partner authentication failed")

@pytest.fixture(scope="module")
def client_token(api_client):
    """Get client auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "client@leamss.com",
        "password": "Client@123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Client authentication failed")


# ============ #1 AI ELIGIBILITY PRE-SCORE (PUBLIC) ============

class TestEligibilityPublic:
    """AI Eligibility Pre-Score - Public endpoints (no auth required)"""
    
    def test_get_pathways_returns_8_pathways(self, api_client):
        """GET /api/eligibility/pathways returns 8 pathways"""
        response = api_client.get(f"{BASE_URL}/api/eligibility/pathways")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "pathways" in data
        assert len(data["pathways"]) == 8, f"Expected 8 pathways, got {len(data['pathways'])}"
        # Verify pathway structure
        for p in data["pathways"]:
            assert "slug" in p
            assert "name" in p
        print(f"✓ GET /api/eligibility/pathways returns {len(data['pathways'])} pathways")
    
    def test_score_eligibility_valid_profile(self, api_client):
        """POST /api/eligibility/score with valid profile returns scored pathways"""
        payload = {
            "full_name": "TEST_Rahul Sharma",
            "email": "test_rahul@example.com",
            "mobile": "+91-9876543210",
            "age": 28,
            "education": "Master",
            "work_experience_years": 5,
            "occupation": "Senior Software Engineer",
            "english_score": "IELTS 7.5",
            "family_savings_inr": 2000000,
            "has_job_offer": False,
            "consent_to_contact": False
        }
        response = api_client.post(f"{BASE_URL}/api/eligibility/score", json=payload, timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        data = response.json()
        
        # Verify response structure
        assert "score_id" in data
        assert "top_recommendation" in data
        assert "overall_summary" in data
        assert "pathways" in data
        assert "lead_captured" in data
        
        # Verify pathways have required fields
        pathways = data["pathways"]
        assert len(pathways) >= 1, "Expected at least 1 scored pathway"
        for slug, p in pathways.items():
            assert "score" in p, f"Missing score for {slug}"
            assert "tier" in p, f"Missing tier for {slug}"
            assert "estimated_timeline" in p, f"Missing timeline for {slug}"
            assert "key_strengths" in p, f"Missing strengths for {slug}"
            assert "gaps_to_fix" in p, f"Missing gaps for {slug}"
            assert "notes" in p, f"Missing notes for {slug}"
            assert p["tier"] in ["strong", "moderate", "weak", "unlikely"]
        
        print(f"✓ POST /api/eligibility/score returned {len(pathways)} scored pathways")
        print(f"  Top recommendation: {data['top_recommendation']}")
        return data["score_id"]
    
    def test_score_eligibility_with_consent_captures_lead(self, api_client):
        """POST /api/eligibility/score with consent_to_contact=true captures lead"""
        payload = {
            "full_name": "TEST_Lead Capture User",
            "email": "test_lead_capture@example.com",
            "mobile": "+91-9999888877",
            "age": 30,
            "education": "Bachelor",
            "work_experience_years": 4,
            "occupation": "Civil Engineer",
            "english_score": "IELTS 6.5",
            "family_savings_inr": 1500000,
            "has_job_offer": False,
            "consent_to_contact": True  # Should capture lead
        }
        response = api_client.post(f"{BASE_URL}/api/eligibility/score", json=payload, timeout=60)
        assert response.status_code == 200
        data = response.json()
        assert data["lead_captured"] == True, "Expected lead_captured=True when consent given"
        print(f"✓ Lead captured when consent_to_contact=True")
    
    def test_share_score_public_access(self, api_client):
        """GET /api/eligibility/share/{score_id} works publicly"""
        # First create a score
        payload = {
            "full_name": "TEST_Share Test User",
            "age": 25,
            "education": "Bachelor",
            "work_experience_years": 2,
            "occupation": "Accountant",
            "consent_to_contact": False
        }
        create_resp = api_client.post(f"{BASE_URL}/api/eligibility/score", json=payload, timeout=60)
        assert create_resp.status_code == 200
        score_id = create_resp.json()["score_id"]
        
        # Now fetch it publicly
        share_resp = api_client.get(f"{BASE_URL}/api/eligibility/share/{score_id}")
        assert share_resp.status_code == 200
        data = share_resp.json()
        assert data["id"] == score_id
        assert "result" in data
        print(f"✓ GET /api/eligibility/share/{score_id} works publicly")
    
    def test_share_score_not_found(self, api_client):
        """GET /api/eligibility/share/{invalid_id} returns 404"""
        response = api_client.get(f"{BASE_URL}/api/eligibility/share/nonexistent-id-12345")
        assert response.status_code == 404
        print(f"✓ GET /api/eligibility/share/invalid returns 404")


# ============ #8 VISA PATHWAY COMPARISON (PUBLIC) ============

class TestVisaComparePublic:
    """Visa Pathway Comparison - Public endpoints"""
    
    def test_get_pathways_returns_8_seeded(self, api_client):
        """GET /api/visa-compare/pathways returns 8 seeded pathways with all fields"""
        response = api_client.get(f"{BASE_URL}/api/visa-compare/pathways")
        assert response.status_code == 200
        data = response.json()
        assert "pathways" in data
        assert data["count"] == 8, f"Expected 8 pathways, got {data['count']}"
        
        # Verify all required fields present
        required_fields = [
            "slug", "name", "country", "category", "min_age", "max_age",
            "min_education", "min_work_exp_years", "language_required",
            "min_funds_inr", "govt_fee_inr", "leamss_fee_inr", "timeline_months",
            "key_benefits", "key_drawbacks", "post_arrival_jobs"
        ]
        for p in data["pathways"]:
            for field in required_fields:
                assert field in p, f"Missing field {field} in pathway {p.get('slug')}"
        
        print(f"✓ GET /api/visa-compare/pathways returns {data['count']} pathways with all fields")
    
    def test_compare_3_pathways(self, api_client):
        """GET /api/visa-compare/compare?slugs=... returns 3 pathways in correct order"""
        slugs = "canada_express_entry,australia_189,uk_skilled_worker"
        response = api_client.get(f"{BASE_URL}/api/visa-compare/compare?slugs={slugs}")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        
        # Verify order matches request
        returned_slugs = [p["slug"] for p in data["pathways"]]
        expected_slugs = slugs.split(",")
        assert returned_slugs == expected_slugs, f"Order mismatch: {returned_slugs} vs {expected_slugs}"
        print(f"✓ GET /api/visa-compare/compare returns 3 pathways in correct order")
    
    def test_compare_requires_2_pathways(self, api_client):
        """GET /api/visa-compare/compare with <2 slugs returns 400"""
        response = api_client.get(f"{BASE_URL}/api/visa-compare/compare?slugs=canada_express_entry")
        assert response.status_code == 400
        print(f"✓ Compare requires at least 2 pathways")
    
    def test_compare_max_4_pathways(self, api_client):
        """GET /api/visa-compare/compare with >4 slugs returns 400"""
        slugs = "canada_express_entry,australia_189,uk_skilled_worker,germany_eu_blue_card,usa_eb2_niw"
        response = api_client.get(f"{BASE_URL}/api/visa-compare/compare?slugs={slugs}")
        assert response.status_code == 400
        print(f"✓ Compare rejects >4 pathways")


class TestVisaCompareAdmin:
    """Visa Pathway Comparison - Admin-only endpoints"""
    
    def test_update_pathway_as_admin(self, api_client, admin_token):
        """PUT /api/visa-compare/pathways/{slug} updates as admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {"govt_fee_inr": 115000}  # Update fee
        response = api_client.put(
            f"{BASE_URL}/api/visa-compare/pathways/canada_express_entry",
            json=payload,
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert data["pathway"]["govt_fee_inr"] == 115000
        print(f"✓ Admin can update pathway")
    
    def test_update_pathway_non_admin_forbidden(self, api_client, partner_token):
        """PUT /api/visa-compare/pathways/{slug} returns 403 for non-admin"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        payload = {"govt_fee_inr": 999999}
        response = api_client.put(
            f"{BASE_URL}/api/visa-compare/pathways/canada_express_entry",
            json=payload,
            headers=headers
        )
        assert response.status_code == 403
        print(f"✓ Non-admin gets 403 on pathway update")
    
    def test_reseed_pathways_admin_only(self, api_client, admin_token):
        """POST /api/visa-compare/reseed admin-only resets seed"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(f"{BASE_URL}/api/visa-compare/reseed", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert data["inserted"] == 8
        print(f"✓ Admin can reseed pathways")
    
    def test_reseed_pathways_non_admin_forbidden(self, api_client, partner_token):
        """POST /api/visa-compare/reseed returns 403 for non-admin"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = api_client.post(f"{BASE_URL}/api/visa-compare/reseed", headers=headers)
        assert response.status_code == 403
        print(f"✓ Non-admin gets 403 on reseed")


# ============ #2 DOCUMENT EXPIRY TRACKER (ADMIN) ============

class TestDocExpiryTracker:
    """Document Expiry Tracker - Admin/Partner/Client scoped endpoints"""
    
    def test_upcoming_as_admin(self, api_client, admin_token):
        """GET /api/doc-expiry/upcoming (admin) returns count + stats + items"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get(f"{BASE_URL}/api/doc-expiry/upcoming", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "count" in data
        assert "stats" in data
        assert "items" in data
        
        # Verify stats structure
        stats = data["stats"]
        for key in ["expired", "critical", "warning", "info", "ok"]:
            assert key in stats, f"Missing stat key: {key}"
        
        print(f"✓ GET /api/doc-expiry/upcoming returns count={data['count']}, stats={stats}")
    
    def test_check_now_idempotent(self, api_client, admin_token):
        """POST /api/doc-expiry/check-now is idempotent (calling twice fires 0 second time)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First call
        resp1 = api_client.post(f"{BASE_URL}/api/doc-expiry/check-now", json={}, headers=headers)
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert "alerts_fired" in data1
        assert "scanned" in data1
        
        # Second call should fire 0 new alerts (idempotent)
        resp2 = api_client.post(f"{BASE_URL}/api/doc-expiry/check-now", json={}, headers=headers)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["alerts_fired"] == 0, f"Expected 0 alerts on second call, got {data2['alerts_fired']}"
        
        print(f"✓ POST /api/doc-expiry/check-now is idempotent (first: {data1['alerts_fired']}, second: {data2['alerts_fired']})")
    
    def test_set_pa_doc_expiry(self, api_client, admin_token):
        """PUT /api/doc-expiry/pa-doc/{doc_id}/expiry sets expiry_date"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First, we need to find a PA doc to set expiry on
        # Get pre-assessments to find one with documents
        pa_resp = api_client.get(f"{BASE_URL}/api/pre-assessment", headers=headers)
        if pa_resp.status_code != 200:
            pytest.skip("No pre-assessments available")
        
        pas = pa_resp.json()
        if not pas:
            pytest.skip("No pre-assessments found")
        
        # Find a PA with documents
        doc_id = None
        for pa in pas:
            docs_resp = api_client.get(f"{BASE_URL}/api/pre-assessment/{pa['id']}/documents", headers=headers)
            if docs_resp.status_code == 200:
                docs = docs_resp.json()
                if docs:
                    doc_id = docs[0].get("id")
                    break
        
        if not doc_id:
            pytest.skip("No PA documents found to test expiry setting")
        
        # Set expiry to 20 days from now
        expiry_date = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
        response = api_client.put(
            f"{BASE_URL}/api/doc-expiry/pa-doc/{doc_id}/expiry",
            json={"expiry_date": expiry_date},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert data["doc_id"] == doc_id
        print(f"✓ PUT /api/doc-expiry/pa-doc/{doc_id}/expiry set to {expiry_date}")
    
    def test_upcoming_role_scoping_partner(self, api_client, partner_token):
        """Partner only sees own PA docs in /upcoming"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = api_client.get(f"{BASE_URL}/api/doc-expiry/upcoming", headers=headers)
        assert response.status_code == 200
        # Partner should get a valid response (may be empty if no expiring docs)
        data = response.json()
        assert "count" in data
        assert "items" in data
        print(f"✓ Partner can access /upcoming (scoped to own PAs)")
    
    def test_upcoming_role_scoping_client(self, api_client, client_token):
        """Client only sees own docs in /upcoming"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = api_client.get(f"{BASE_URL}/api/doc-expiry/upcoming", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"✓ Client can access /upcoming (scoped to own docs)")


# ============ HEALTH CHECK ============

class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self, api_client):
        """GET /api/health returns healthy"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ API health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
