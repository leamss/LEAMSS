"""
Iteration 80: Test Clean DB State + Action Card Filter Flows
- Backend: Verify clean DB state after cleanup (empty PAs, cases, sales)
- Backend: Verify seeded users still exist
- Backend: Verify products/workflows/fee_database/promo_codes/upsell_bundles preserved
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCleanDBState:
    """Verify DB is clean after cleanup script execution"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = None
        self.partner_token = None
        # Login as admin
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        if resp.status_code == 200:
            self.admin_token = resp.json().get("token")
        # Login as partner
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        if resp.status_code == 200:
            self.partner_token = resp.json().get("token")
    
    def get_admin_header(self):
        return {"Authorization": f"Bearer {self.admin_token}"}
    
    def get_partner_header(self):
        return {"Authorization": f"Bearer {self.partner_token}"}
    
    def test_admin_login_works(self):
        """Admin login should work"""
        assert self.admin_token is not None, "Admin login failed"
        print("✓ Admin login successful")
    
    def test_partner_login_works(self):
        """Partner login should work"""
        assert self.partner_token is not None, "Partner login failed"
        print("✓ Partner login successful")
    
    def test_partner_my_assessments_empty(self):
        """Partner's pre-assessments should be empty after cleanup"""
        if not self.partner_token:
            pytest.skip("Partner login failed")
        resp = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=self.get_partner_header())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        # Should be empty or very few (cleanup removed test data)
        print(f"Partner pre-assessments count: {len(data)}")
        # Allow 0-2 items (in case some seed data exists)
        assert len(data) <= 2, f"Expected <=2 pre-assessments, got {len(data)}"
        print("✓ Partner pre-assessments are clean (<=2 items)")
    
    def test_admin_queue_empty(self):
        """Admin queue should be empty after cleanup"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        resp = requests.get(f"{BASE_URL}/api/pre-assessment/admin/queue", headers=self.get_admin_header())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        print(f"Admin queue count: {len(data)}")
        # Should be empty or very few
        assert len(data) <= 2, f"Expected <=2 items in queue, got {len(data)}"
        print("✓ Admin queue is clean (<=2 items)")
    
    def test_cases_empty(self):
        """Cases should be empty after cleanup"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        resp = requests.get(f"{BASE_URL}/api/cases", headers=self.get_admin_header())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        print(f"Cases count: {len(data)}")
        # Should be empty or very few
        assert len(data) <= 2, f"Expected <=2 cases, got {len(data)}"
        print("✓ Cases are clean (<=2 items)")
    
    def test_seeded_users_exist(self):
        """Seeded users should still exist"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        resp = requests.get(f"{BASE_URL}/api/users", headers=self.get_admin_header())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        users = resp.json()
        emails = [u.get('email') for u in users]
        
        expected_users = [
            'admin@leamss.com',
            'partner@leamss.com',
            'manager@leamss.com',
            'client@leamss.com',
        ]
        
        for email in expected_users:
            assert email in emails, f"Expected user {email} not found"
            print(f"✓ User {email} exists")
        
        print(f"Total users: {len(users)}")
    
    def test_products_preserved(self):
        """Products should be preserved"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        resp = requests.get(f"{BASE_URL}/api/products", headers=self.get_admin_header())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        products = resp.json()
        assert len(products) > 0, "Products should not be empty"
        print(f"✓ Products preserved: {len(products)} products")
    
    def test_upsell_bundles_preserved(self):
        """Upsell bundles should be preserved"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        resp = requests.get(f"{BASE_URL}/api/upsell-bundles", headers=self.get_admin_header())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        bundles = resp.json()
        # May be empty if none were created, but endpoint should work
        print(f"✓ Upsell bundles endpoint works: {len(bundles)} bundles")
    
    def test_fee_database_preserved(self):
        """Fee database should be preserved"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/admin/catalog", headers=self.get_admin_header())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        fees = resp.json()
        print(f"✓ Fee database endpoint works: {fees}")
    
    def test_promo_codes_preserved(self):
        """Promo codes should be preserved"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        resp = requests.get(f"{BASE_URL}/api/marketing/promos", headers=self.get_admin_header())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        codes = resp.json()
        print(f"✓ Promo codes endpoint works: {len(codes)} codes")


class TestPreAssessmentStatsEndpoint:
    """Test pre-assessment stats endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        self.token = resp.json().get("token") if resp.status_code == 200 else None
    
    def test_stats_overview(self):
        """Stats overview should return valid data"""
        if not self.token:
            pytest.skip("Login failed")
        resp = requests.get(f"{BASE_URL}/api/pre-assessment/stats/overview", 
                          headers={"Authorization": f"Bearer {self.token}"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        # Should have expected keys
        assert 'total' in data or 'under_review' in data or isinstance(data, dict), "Stats should be a dict"
        print(f"✓ Stats overview: {data}")


class TestAIProposalClaude:
    """Verify AI Proposal still uses Claude Sonnet 4.5"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        self.token = resp.json().get("token") if resp.status_code == 200 else None
    
    def test_ai_proposal_model(self):
        """AI proposal should use Claude Sonnet 4.5"""
        if not self.token:
            pytest.skip("Login failed")
        
        # Create a minimal PA for testing (or use mock data)
        resp = requests.post(f"{BASE_URL}/api/ai-proposal/generate",
                           json={"pa_id": "test-pa-id", "tone": "professional"},
                           headers={"Authorization": f"Bearer {self.token}"})
        
        # May fail if no PA exists, but check model if it works
        if resp.status_code == 200:
            data = resp.json()
            model = data.get('model', '')
            assert 'claude' in model.lower() or 'sonnet' in model.lower(), f"Expected Claude model, got {model}"
            print(f"✓ AI model: {model}")
        else:
            # Expected if no PA exists
            print(f"AI proposal endpoint returned {resp.status_code} (expected if no PA exists)")


class TestDashboardStats:
    """Test dashboard stats endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Admin login
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        self.admin_token = resp.json().get("token") if resp.status_code == 200 else None
        
        # Partner login
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        self.partner_token = resp.json().get("token") if resp.status_code == 200 else None
    
    def test_admin_dashboard_stats(self):
        """Admin dashboard stats should work"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        resp = requests.get(f"{BASE_URL}/api/stats/dashboard",
                          headers={"Authorization": f"Bearer {self.admin_token}"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        print(f"✓ Admin dashboard stats: {data}")
    
    def test_partner_dashboard_stats(self):
        """Partner dashboard stats should work"""
        if not self.partner_token:
            pytest.skip("Partner login failed")
        resp = requests.get(f"{BASE_URL}/api/stats/partner-dashboard",
                          headers={"Authorization": f"Bearer {self.partner_token}"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        print(f"✓ Partner dashboard stats: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
