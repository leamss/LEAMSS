"""
Iteration 84 Tests: AI Model Upgrade + Optimistic UI Backend Verification

Tests:
1. AI Proposal Generation with Claude Sonnet 4.6 (default)
2. AI Proposal Generation with Claude Opus 4.6 (premium=true)
3. Regression tests for Phase A/B/C/D endpoints
"""
import os
import pytest
import requests
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"
MANAGER_EMAIL = "manager@leamss.com"
MANAGER_PASSWORD = "Manager@123"


class TestAIModelUpgrade:
    """Test AI Proposal Generation with new Claude models"""
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        """Get partner authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTNER_EMAIL,
            "password": PARTNER_PASSWORD
        })
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def approved_pa_id(self, partner_token):
        """Find an approved PA for testing"""
        response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        pas = response.json()
        approved = [p for p in pas if p.get("stage") == "approved"]
        if not approved:
            pytest.skip("No approved PA found for AI testing")
        return approved[0]["id"]
    
    def test_01_ai_proposal_sonnet_46(self, partner_token, approved_pa_id):
        """Test AI proposal generation with Claude Sonnet 4.6 (default)"""
        response = requests.post(
            f"{BASE_URL}/api/ai-proposal/generate",
            headers={"Authorization": f"Bearer {partner_token}"},
            json={"pa_id": approved_pa_id, "premium": False}
        )
        assert response.status_code == 200, f"AI generation failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("ok") is True
        assert data.get("model") == "anthropic/claude-sonnet-4-6", f"Expected Sonnet 4.6, got {data.get('model')}"
        assert data.get("premium") is False
        assert "proposal_text" in data
        assert data.get("word_count", 0) >= 200, f"Expected 200+ words, got {data.get('word_count')}"
        print(f"✓ Sonnet 4.6: {data.get('word_count')} words generated")
    
    def test_02_ai_proposal_opus_46(self, partner_token, approved_pa_id):
        """Test AI proposal generation with Claude Opus 4.6 (premium=true)"""
        response = requests.post(
            f"{BASE_URL}/api/ai-proposal/generate",
            headers={"Authorization": f"Bearer {partner_token}"},
            json={"pa_id": approved_pa_id, "premium": True}
        )
        assert response.status_code == 200, f"AI generation failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("ok") is True
        assert data.get("model") == "anthropic/claude-opus-4-6", f"Expected Opus 4.6, got {data.get('model')}"
        assert data.get("premium") is True
        assert "proposal_text" in data
        assert data.get("word_count", 0) >= 200, f"Expected 200+ words, got {data.get('word_count')}"
        print(f"✓ Opus 4.6: {data.get('word_count')} words generated")
    
    def test_03_ai_proposal_unauthorized_role(self):
        """Test that client role cannot generate proposals"""
        # Login as client
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        if response.status_code != 200:
            pytest.skip("Client login failed")
        client_token = response.json().get("token")
        
        # Try to generate proposal
        response = requests.post(
            f"{BASE_URL}/api/ai-proposal/generate",
            headers={"Authorization": f"Bearer {client_token}"},
            json={"pa_id": "any-id", "premium": False}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Client role correctly blocked from AI generation")
    
    def test_04_ai_proposal_invalid_pa(self, partner_token):
        """Test AI proposal with non-existent PA"""
        response = requests.post(
            f"{BASE_URL}/api/ai-proposal/generate",
            headers={"Authorization": f"Bearer {partner_token}"},
            json={"pa_id": "non-existent-pa-id", "premium": False}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent PA correctly returns 404")


class TestPhaseARegression:
    """Regression tests for Phase A endpoints"""
    
    @pytest.fixture(scope="class")
    def tokens(self):
        """Get all role tokens"""
        tokens = {}
        for email, password, role in [
            (ADMIN_EMAIL, ADMIN_PASSWORD, "admin"),
            (PARTNER_EMAIL, PARTNER_PASSWORD, "partner"),
            (MANAGER_EMAIL, MANAGER_PASSWORD, "manager"),
        ]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": email, "password": password
            })
            if response.status_code == 200:
                tokens[role] = response.json().get("token")
        return tokens
    
    def test_05_pre_assessment_create(self, tokens):
        """Test PA creation endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/pre-assessment/create",
            headers={"Authorization": f"Bearer {tokens['partner']}"},
            json={
                "client_name": "TEST_Iteration84_Client",
                "client_email": "test_iter84@example.com",
                "country": "Canada",
                "service_type": "Express Entry"
            }
        )
        assert response.status_code == 200, f"PA creation failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "pa_number" in data
        print(f"✓ PA created: {data.get('pa_number')}")
    
    def test_06_my_assessments(self, tokens):
        """Test my-assessments endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {tokens['partner']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ my-assessments returned {len(data)} items")
    
    def test_07_stats_overview(self, tokens):
        """Test stats overview endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/pre-assessment/stats/overview",
            headers={"Authorization": f"Bearer {tokens['partner']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        print(f"✓ stats/overview: total={data.get('total')}")
    
    def test_08_admin_queue(self, tokens):
        """Test admin queue endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/pre-assessment/admin/queue",
            headers={"Authorization": f"Bearer {tokens['admin']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ admin/queue returned {len(data)} items")
    
    def test_09_products_endpoint(self, tokens):
        """Test products endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/products",
            headers={"Authorization": f"Bearer {tokens['partner']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ products returned {len(data)} items")


class TestPhaseBCDRegression:
    """Regression tests for Phase B/C/D endpoints"""
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        """Get partner token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTNER_EMAIL, "password": PARTNER_PASSWORD
        })
        assert response.status_code == 200
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def paid_pa_id(self, partner_token):
        """Find a PA with fee_payment_status=paid"""
        response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        pas = response.json()
        paid = [p for p in pas if p.get("fee_payment_status") == "paid"]
        if not paid:
            pytest.skip("No paid PA found")
        return paid[0]["id"]
    
    def test_10_payment_history_pa(self, partner_token, paid_pa_id):
        """Test payment history for PA"""
        response = requests.get(
            f"{BASE_URL}/api/payment-history/pa/{paid_pa_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "totals" in data
        print(f"✓ payment-history/pa: {len(data.get('events', []))} events")
    
    def test_11_dropoff_leads(self, partner_token):
        """Test dropoff leads endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/intelligence/dropoff-leads",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "items" in data
        print(f"✓ dropoff-leads: count={data.get('count')}")
    
    def test_12_smart_checklist(self, partner_token, paid_pa_id):
        """Test smart checklist endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/intelligence/checklist/{paid_pa_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # completion_pct is in stats sub-object
        stats = data.get("stats", {})
        assert "completion_pct" in stats or "completion_pct" in data
        pct = stats.get("completion_pct", data.get("completion_pct", 0))
        print(f"✓ checklist: {pct}% complete")
    
    def test_13_risk_score(self, partner_token, paid_pa_id):
        """Test risk score endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/intelligence/risk/{paid_pa_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "label" in data
        assert "factors" in data
        print(f"✓ risk: score={data.get('score')}, label={data.get('label')}")
    
    def test_14_pa_bundle(self, partner_token, paid_pa_id):
        """Test PA bundle endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/pre-assessment/{paid_pa_id}/bundle",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "activity" in data
        print(f"✓ bundle: {len(data.get('documents', []))} docs, {len(data.get('activity', []))} activities")
    
    def test_15_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ health check passed")


class TestOptimisticUIEndpoints:
    """Test endpoints used by optimistic UI flows"""
    
    @pytest.fixture(scope="class")
    def tokens(self):
        """Get all role tokens"""
        tokens = {}
        for email, password, role in [
            (ADMIN_EMAIL, ADMIN_PASSWORD, "admin"),
            (PARTNER_EMAIL, PARTNER_PASSWORD, "partner"),
        ]:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": email, "password": password
            })
            if response.status_code == 200:
                tokens[role] = response.json().get("token")
        return tokens
    
    def test_16_review_endpoint_exists(self, tokens):
        """Test that review endpoint exists (used by admin optimistic approve/reject)"""
        # Just verify endpoint exists - don't actually review
        response = requests.put(
            f"{BASE_URL}/api/pre-assessment/non-existent-id/review",
            headers={"Authorization": f"Bearer {tokens['admin']}"},
            json={"decision": "approved", "reason": "test"}
        )
        # Should return 404 for non-existent PA, not 405 (method not allowed)
        assert response.status_code in [404, 400], f"Expected 404/400, got {response.status_code}"
        print("✓ review endpoint exists")
    
    def test_17_send_proposal_endpoint_exists(self, tokens):
        """Test that send-proposal endpoint exists (used by partner optimistic)"""
        response = requests.post(
            f"{BASE_URL}/api/pre-assessment/non-existent-id/send-proposal",
            headers={"Authorization": f"Bearer {tokens['partner']}"},
            json={"fee_amount": 100000, "payment_method": "online"}
        )
        assert response.status_code in [404, 400], f"Expected 404/400, got {response.status_code}"
        print("✓ send-proposal endpoint exists")
    
    def test_18_forward_to_admin_endpoint_exists(self, tokens):
        """Test that forward-to-admin endpoint exists (used by partner optimistic)"""
        response = requests.post(
            f"{BASE_URL}/api/pre-assess-portal/partner/forward-to-admin/non-existent-id",
            headers={"Authorization": f"Bearer {tokens['partner']}"},
            json={"remarks": "test"}
        )
        assert response.status_code in [404, 400], f"Expected 404/400, got {response.status_code}"
        print("✓ forward-to-admin endpoint exists")
    
    def test_19_submit_final_endpoint_exists(self, tokens):
        """Test that submit-final endpoint exists (used by partner optimistic)"""
        response = requests.post(
            f"{BASE_URL}/api/pre-assess-portal/partner/submit-final/non-existent-id",
            headers={"Authorization": f"Bearer {tokens['partner']}"},
            json={"notes": "test"}
        )
        assert response.status_code in [404, 400], f"Expected 404/400, got {response.status_code}"
        print("✓ submit-final endpoint exists")
    
    def test_20_approve_final_endpoint_exists(self, tokens):
        """Test that approve-final endpoint exists (used by admin optimistic)"""
        response = requests.post(
            f"{BASE_URL}/api/pre-assess-portal/admin/approve-final/non-existent-id",
            headers={"Authorization": f"Bearer {tokens['admin']}"},
            json={}
        )
        assert response.status_code in [404, 400], f"Expected 404/400, got {response.status_code}"
        print("✓ approve-final endpoint exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
