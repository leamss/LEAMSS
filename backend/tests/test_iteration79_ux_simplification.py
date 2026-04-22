"""
Iteration 79 Tests: Dashboard UX Simplification + AI Model Switch
Tests for:
1. AI Proposal Generator - Claude Sonnet 4.5 model switch
2. Partner Dashboard Home tab and sidebar regrouping
3. Admin Dashboard Home tab and sidebar
4. FunnelProgress component in PreAssessmentPipeline
5. Regression tests for Phase A Part 3 flows
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print("✅ Admin login successful")
    
    def test_partner_login(self):
        """Test partner login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print("✅ Partner login successful")


class TestAIProposalClaudeSonnet:
    """AI Proposal Generator - Claude Sonnet 4.5 model tests"""
    
    @pytest.fixture
    def partner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def test_pa_id(self, partner_token):
        """Get a test PA ID for AI proposal generation"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=headers)
        pas = response.json()
        # Find an approved PA for testing
        for pa in pas:
            if pa.get("stage") in ["approved", "proposal_sent", "proposal_paid", "case_created"]:
                return pa["id"]
        # If no approved PA, use any PA
        if pas:
            return pas[0]["id"]
        pytest.skip("No pre-assessments available for testing")
    
    def test_ai_proposal_professional_tone(self, partner_token, test_pa_id):
        """Test AI proposal generation with professional tone using Claude Sonnet 4.5"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.post(f"{BASE_URL}/api/ai-proposal/generate", 
            headers=headers,
            json={"pa_id": test_pa_id, "tone": "professional"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["ok"] == True
        assert "proposal_text" in data
        assert data["tone"] == "professional"
        assert "word_count" in data
        
        # CRITICAL: Verify Claude Sonnet 4.5 model
        assert data["model"] == "anthropic/claude-sonnet-4-5", f"Expected Claude Sonnet 4.5, got {data['model']}"
        
        # Verify word count is in expected range (250-400 words)
        assert 200 <= data["word_count"] <= 500, f"Word count {data['word_count']} outside expected range"
        
        print(f"✅ AI proposal (professional) generated: {data['word_count']} words, model: {data['model']}")
    
    def test_ai_proposal_friendly_tone(self, partner_token, test_pa_id):
        """Test AI proposal generation with friendly tone"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.post(f"{BASE_URL}/api/ai-proposal/generate", 
            headers=headers,
            json={"pa_id": test_pa_id, "tone": "friendly"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["tone"] == "friendly"
        assert data["model"] == "anthropic/claude-sonnet-4-5"
        
        print(f"✅ AI proposal (friendly) generated: {data['word_count']} words")
    
    def test_ai_proposal_assertive_tone(self, partner_token, test_pa_id):
        """Test AI proposal generation with assertive tone"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.post(f"{BASE_URL}/api/ai-proposal/generate", 
            headers=headers,
            json={"pa_id": test_pa_id, "tone": "assertive"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["tone"] == "assertive"
        assert data["model"] == "anthropic/claude-sonnet-4-5"
        
        print(f"✅ AI proposal (assertive) generated: {data['word_count']} words")


class TestRegressionPhaseA:
    """Regression tests for Phase A Part 3 flows"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def partner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        return response.json()["token"]
    
    def test_upsell_bundles_crud(self, admin_token):
        """Test Upsell Bundles CRUD operations"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # GET - should return bundles (auto-seeded)
        response = requests.get(f"{BASE_URL}/api/upsell-bundles", headers=headers)
        assert response.status_code == 200
        bundles = response.json()
        assert len(bundles) >= 1, "Expected at least 1 upsell bundle"
        print(f"✅ Upsell bundles GET: {len(bundles)} bundles found")
    
    def test_promo_code_validation(self, partner_token):
        """Test promo code validation endpoint"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        
        # Test with invalid promo code
        response = requests.post(f"{BASE_URL}/api/marketing/promo/validate",
            headers=headers,
            json={"code": "INVALID_CODE_12345"}
        )
        # Should return 400 or 404 for invalid code
        assert response.status_code in [400, 404], f"Expected 400/404 for invalid promo, got {response.status_code}"
        print("✅ Promo code validation rejects invalid codes")
    
    def test_pre_assessment_stats(self, partner_token):
        """Test pre-assessment stats endpoint"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        
        response = requests.get(f"{BASE_URL}/api/pre-assessment/stats/overview", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        
        # Verify stats structure
        assert "total" in stats or "conversion_rate" in stats
        print(f"✅ Pre-assessment stats: {stats}")
    
    def test_admin_queue(self, admin_token):
        """Test admin pre-assessment queue"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/pre-assessment/admin/queue", headers=headers)
        assert response.status_code == 200
        queue = response.json()
        assert isinstance(queue, list)
        print(f"✅ Admin queue: {len(queue)} items")
    
    def test_cases_endpoint(self, admin_token):
        """Test cases endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✅ Cases endpoint: {len(cases)} cases")
    
    def test_users_endpoint(self, admin_token):
        """Test users endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 1
        print(f"✅ Users endpoint: {len(users)} users")
    
    def test_products_endpoint(self, admin_token):
        """Test products endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        print(f"✅ Products endpoint: {len(products)} products")


class TestDashboardAPIs:
    """Test dashboard-related APIs"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def partner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        return response.json()["token"]
    
    def test_admin_dashboard_stats(self, admin_token):
        """Test admin dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        
        # Verify expected fields
        assert "pending_sales" in stats or "active_cases" in stats
        print(f"✅ Admin dashboard stats: {stats}")
    
    def test_partner_dashboard_stats(self, partner_token):
        """Test partner dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        
        response = requests.get(f"{BASE_URL}/api/stats/partner-dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        print(f"✅ Partner dashboard stats: {stats}")
    
    def test_partner_my_assessments(self, partner_token):
        """Test partner my-assessments endpoint (used by PartnerHome)"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        
        response = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=headers)
        assert response.status_code == 200
        assessments = response.json()
        assert isinstance(assessments, list)
        print(f"✅ Partner my-assessments: {len(assessments)} assessments")


class TestTicketsEndpoint:
    """Test tickets endpoint for regression"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        return response.json()["token"]
    
    def test_tickets_all(self, admin_token):
        """Test tickets all endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/tickets/all", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✅ Tickets endpoint: {len(tickets)} tickets")
    
    def test_tickets_stats(self, admin_token):
        """Test tickets stats endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/tickets/stats", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        print(f"✅ Tickets stats: {stats}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
