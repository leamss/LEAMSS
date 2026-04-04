"""
Iteration 26 - Marketing Tools Testing
Tests for: Service Calculator, Lead CRM, Email Campaigns, Testimonials, Partner Leaderboard
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPublicEndpoints:
    """Public endpoints - no auth required"""
    
    def test_health_check(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("PASS: Health check endpoint working")
    
    def test_calculator_assess_eligibility(self):
        """Test POST /api/marketing-tools/calculator/assess - public endpoint"""
        payload = {
            "age": 28,
            "education": "masters",
            "work_experience_years": 5,
            "language_score": 7.5,
            "country_of_interest": "Canada"
        }
        response = requests.post(f"{BASE_URL}/api/marketing-tools/calculator/assess", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "profile_summary" in data
        assert "recommendations" in data
        assert "top_recommendation" in data
        
        # Verify profile summary
        assert data["profile_summary"]["age"] == 28
        assert data["profile_summary"]["education"] == "masters"
        
        # Verify recommendations
        assert isinstance(data["recommendations"], list)
        if len(data["recommendations"]) > 0:
            rec = data["recommendations"][0]
            assert "product_name" in rec
            assert "score" in rec
            assert "eligibility" in rec
            assert "reasons" in rec
        print(f"PASS: Calculator returned {len(data['recommendations'])} recommendations")
    
    def test_lead_capture_public(self):
        """Test POST /api/leads/capture - public endpoint"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"TEST_Lead_{unique_id}",
            "email": f"test_lead_{unique_id}@example.com",
            "phone": "+91 9876543210",
            "service_interested": "Canada PR",
            "country_of_interest": "Canada",
            "message": "Testing lead capture",
            "source": "website"
        }
        response = requests.post(f"{BASE_URL}/api/leads/capture", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "lead_id" in data
        assert data["message"] == "Thank you! We will contact you shortly."
        print(f"PASS: Lead captured with ID: {data['lead_id']}")
        return data["lead_id"]
    
    def test_testimonials_public(self):
        """Test GET /api/marketing-tools/testimonials - public endpoint"""
        response = requests.get(f"{BASE_URL}/api/marketing-tools/testimonials")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Public testimonials endpoint returned {len(data)} testimonials")


class TestAdminLeadsCRM:
    """Admin-only Lead CRM endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_resp.status_code == 200, "Admin login failed"
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_leads(self):
        """Test GET /api/leads/ - admin only"""
        response = requests.get(f"{BASE_URL}/api/leads/", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/leads/ returned {len(data)} leads")
    
    def test_get_pipeline_stats(self):
        """Test GET /api/leads/pipeline-stats - admin only"""
        response = requests.get(f"{BASE_URL}/api/leads/pipeline-stats", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "stages" in data
        assert "total" in data
        assert "conversion_rate" in data
        assert "sources" in data
        
        # Verify stages structure
        expected_stages = ["new", "contacted", "qualified", "proposal", "negotiation", "won", "lost"]
        for stage in expected_stages:
            assert stage in data["stages"]
        print(f"PASS: Pipeline stats - Total: {data['total']}, Conversion: {data['conversion_rate']}%")
    
    def test_get_pending_follow_ups(self):
        """Test GET /api/leads/follow-ups/pending - admin only"""
        response = requests.get(f"{BASE_URL}/api/leads/follow-ups/pending", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/leads/follow-ups/pending returned {len(data)} follow-ups")
    
    def test_update_lead_stage(self):
        """Test PUT /api/leads/{lead_id} - update lead stage"""
        # First get a lead
        leads_resp = requests.get(f"{BASE_URL}/api/leads/", headers=self.headers)
        leads = leads_resp.json()
        if len(leads) == 0:
            pytest.skip("No leads to update")
        
        lead_id = leads[0]["id"]
        
        # Update stage
        response = requests.put(
            f"{BASE_URL}/api/leads/{lead_id}",
            headers=self.headers,
            json={"stage": "qualified"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Lead updated"
        print(f"PASS: Lead {lead_id} stage updated to 'qualified'")
    
    def test_add_note_to_lead(self):
        """Test POST /api/leads/{lead_id}/note - add note"""
        # First get a lead
        leads_resp = requests.get(f"{BASE_URL}/api/leads/", headers=self.headers)
        leads = leads_resp.json()
        if len(leads) == 0:
            pytest.skip("No leads to add note")
        
        lead_id = leads[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/note",
            headers=self.headers,
            json={"text": "TEST_Note: Automated test note"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Note added"
        print(f"PASS: Note added to lead {lead_id}")
    
    def test_schedule_follow_up(self):
        """Test POST /api/leads/{lead_id}/follow-up - schedule follow-up"""
        # First get a lead
        leads_resp = requests.get(f"{BASE_URL}/api/leads/", headers=self.headers)
        leads = leads_resp.json()
        if len(leads) == 0:
            pytest.skip("No leads for follow-up")
        
        lead_id = leads[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/follow-up",
            headers=self.headers,
            json={
                "type": "email",
                "scheduled_at": "2026-01-25T14:00:00",
                "message": "TEST_FollowUp: Send pricing details"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Follow-up scheduled"
        assert "id" in data
        print(f"PASS: Follow-up scheduled with ID: {data['id']}")
        return data["id"]
    
    def test_complete_follow_up(self):
        """Test PUT /api/leads/follow-ups/{follow_up_id}/complete"""
        # First get pending follow-ups
        pending_resp = requests.get(f"{BASE_URL}/api/leads/follow-ups/pending", headers=self.headers)
        pending = pending_resp.json()
        if len(pending) == 0:
            pytest.skip("No pending follow-ups to complete")
        
        follow_up_id = pending[0]["id"]
        
        response = requests.put(
            f"{BASE_URL}/api/leads/follow-ups/{follow_up_id}/complete",
            headers=self.headers,
            json={"outcome": "completed via test"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Follow-up completed"
        print(f"PASS: Follow-up {follow_up_id} completed")


class TestAdminCampaigns:
    """Admin-only Campaign endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_resp.status_code == 200, "Admin login failed"
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_create_campaign(self):
        """Test POST /api/campaigns/ - create campaign"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"TEST_Campaign_{unique_id}",
            "subject": "Special Immigration Offer",
            "body": "Dear Client, We have a special offer for you!",
            "target_audience": "all"
        }
        response = requests.post(f"{BASE_URL}/api/campaigns/", headers=self.headers, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Campaign created"
        assert "id" in data
        print(f"PASS: Campaign created with ID: {data['id']}")
        return data["id"]
    
    def test_get_campaigns(self):
        """Test GET /api/campaigns/ - list campaigns"""
        response = requests.get(f"{BASE_URL}/api/campaigns/", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/campaigns/ returned {len(data)} campaigns")
    
    def test_get_campaign_stats(self):
        """Test GET /api/campaigns/stats/overview"""
        response = requests.get(f"{BASE_URL}/api/campaigns/stats/overview", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "total_campaigns" in data
        assert "sent_campaigns" in data
        assert "draft_campaigns" in data
        assert "total_recipients" in data
        print(f"PASS: Campaign stats - Total: {data['total_campaigns']}, Sent: {data['sent_campaigns']}")
    
    def test_send_campaign_mocked(self):
        """Test POST /api/campaigns/{id}/send - MOCKED email delivery"""
        # First get a draft campaign
        campaigns_resp = requests.get(f"{BASE_URL}/api/campaigns/", headers=self.headers)
        campaigns = campaigns_resp.json()
        draft_campaigns = [c for c in campaigns if c.get("status") == "draft"]
        
        if len(draft_campaigns) == 0:
            # Create a new campaign
            unique_id = str(uuid.uuid4())[:8]
            create_resp = requests.post(f"{BASE_URL}/api/campaigns/", headers=self.headers, json={
                "name": f"TEST_SendCampaign_{unique_id}",
                "subject": "Test Send",
                "body": "Test body",
                "target_audience": "all"
            })
            campaign_id = create_resp.json()["id"]
        else:
            campaign_id = draft_campaigns[0]["id"]
        
        response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/send", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "Campaign sent to" in data["message"]
        print(f"PASS: Campaign sent (MOCKED) - {data['message']}")


class TestAdminTestimonials:
    """Admin-only Testimonial endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_resp.status_code == 200, "Admin login failed"
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_create_testimonial(self):
        """Test POST /api/marketing-tools/testimonials - admin only"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "client_name": f"TEST_Client_{unique_id}",
            "client_country": "India",
            "service_used": "Canada PR",
            "rating": 5,
            "text": "Excellent service! Got my PR approved quickly.",
            "featured": False
        }
        response = requests.post(f"{BASE_URL}/api/marketing-tools/testimonials", headers=self.headers, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Testimonial created"
        assert "id" in data
        print(f"PASS: Testimonial created with ID: {data['id']}")
        return data["id"]
    
    def test_get_all_testimonials_admin(self):
        """Test GET /api/marketing-tools/testimonials?status=all - admin view"""
        response = requests.get(f"{BASE_URL}/api/marketing-tools/testimonials?status=all", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Admin testimonials view returned {len(data)} testimonials")


class TestPartnerLeaderboard:
    """Partner Leaderboard endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_resp.status_code == 200, "Admin login failed"
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_leaderboard(self):
        """Test GET /api/marketing-tools/leaderboard - admin/partner only"""
        response = requests.get(f"{BASE_URL}/api/marketing-tools/leaderboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            partner = data[0]
            assert "partner_id" in partner
            assert "partner_name" in partner
            assert "total_sales" in partner
            assert "total_revenue" in partner
            assert "conversion_rate" in partner
            assert "tier" in partner
            assert "rank" in partner
        print(f"PASS: Leaderboard returned {len(data)} partners")
    
    def test_partner_can_view_leaderboard(self):
        """Test partner role can access leaderboard"""
        # Login as partner
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        assert login_resp.status_code == 200, "Partner login failed"
        partner_token = login_resp.json()["token"]
        partner_headers = {"Authorization": f"Bearer {partner_token}"}
        
        response = requests.get(f"{BASE_URL}/api/marketing-tools/leaderboard", headers=partner_headers)
        assert response.status_code == 200
        print("PASS: Partner can view leaderboard")


class TestUnauthorizedAccess:
    """Test that protected endpoints require auth"""
    
    def test_leads_requires_auth(self):
        """Test GET /api/leads/ requires authentication"""
        response = requests.get(f"{BASE_URL}/api/leads/")
        assert response.status_code in [401, 403]  # Either unauthorized or forbidden
        print(f"PASS: /api/leads/ requires authentication (status: {response.status_code})")
    
    def test_campaigns_requires_auth(self):
        """Test GET /api/campaigns/ requires authentication"""
        response = requests.get(f"{BASE_URL}/api/campaigns/")
        assert response.status_code in [401, 403]  # Either unauthorized or forbidden
        print(f"PASS: /api/campaigns/ requires authentication (status: {response.status_code})")
    
    def test_leaderboard_requires_auth(self):
        """Test GET /api/marketing-tools/leaderboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/marketing-tools/leaderboard")
        assert response.status_code in [401, 403]  # Either unauthorized or forbidden
        print(f"PASS: /api/marketing-tools/leaderboard requires authentication (status: {response.status_code})")
    
    def test_client_cannot_access_leads(self):
        """Test client role cannot access leads"""
        # Login as client
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        assert login_resp.status_code == 200, "Client login failed"
        client_token = login_resp.json()["token"]
        client_headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(f"{BASE_URL}/api/leads/", headers=client_headers)
        assert response.status_code == 403
        print("PASS: Client cannot access leads (403 Forbidden)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
