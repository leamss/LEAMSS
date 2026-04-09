"""
Phase 7A-7B Features Test Suite
Tests for: Case Timeline, Case Notes & Tags, Canned Responses, Referrals, Greetings,
Conversion Funnel, Country/Product Analytics, Commission Analytics, Survey Submit
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
CM_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if res.status_code == 200:
        return res.json().get("token")
    pytest.skip("Admin login failed")


@pytest.fixture(scope="module")
def cm_token():
    """Get case manager auth token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json=CM_CREDS)
    if res.status_code == 200:
        return res.json().get("token")
    pytest.skip("Case Manager login failed")


@pytest.fixture(scope="module")
def client_token():
    """Get client auth token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    if res.status_code == 200:
        return res.json().get("token")
    pytest.skip("Client login failed")


@pytest.fixture(scope="module")
def partner_token():
    """Get partner auth token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
    if res.status_code == 200:
        return res.json().get("token")
    pytest.skip("Partner login failed")


@pytest.fixture(scope="module")
def test_case_id(admin_token):
    """Get a case ID for testing"""
    res = requests.get(f"{BASE_URL}/api/cases", headers={"Authorization": f"Bearer {admin_token}"})
    if res.status_code == 200 and res.json():
        return res.json()[0]["id"]
    pytest.skip("No cases available for testing")


class TestAuthentication:
    """Test login for all 4 roles"""
    
    def test_admin_login(self):
        res = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print("PASS: Admin login successful")
    
    def test_case_manager_login(self):
        res = requests.post(f"{BASE_URL}/api/auth/login", json=CM_CREDS)
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print("PASS: Case Manager login successful")
    
    def test_client_login(self):
        res = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print("PASS: Client login successful")
    
    def test_partner_login(self):
        res = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print("PASS: Partner login successful")


class TestCaseTimeline:
    """Phase 7A: Case Timeline API tests"""
    
    def test_get_case_timeline(self, admin_token, test_case_id):
        """GET /api/timeline/case/{case_id} returns events"""
        res = requests.get(
            f"{BASE_URL}/api/timeline/case/{test_case_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "case_id" in data
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)
        print(f"PASS: Timeline returned {data['total']} events for case {test_case_id}")
    
    def test_timeline_event_structure(self, admin_token, test_case_id):
        """Verify timeline event structure"""
        res = requests.get(
            f"{BASE_URL}/api/timeline/case/{test_case_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        if data["events"]:
            event = data["events"][0]
            assert "type" in event
            assert "title" in event
            assert "timestamp" in event
            print(f"PASS: Timeline event has correct structure: {event['type']}")
        else:
            print("PASS: Timeline returned empty events (no activity yet)")
    
    def test_timeline_as_case_manager(self, cm_token, test_case_id):
        """Case manager can access timeline"""
        res = requests.get(
            f"{BASE_URL}/api/timeline/case/{test_case_id}",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert res.status_code == 200
        print("PASS: Case manager can access timeline")


class TestCaseNotes:
    """Phase 7A: Case Notes CRUD tests"""
    
    def test_create_note_as_admin(self, admin_token, test_case_id):
        """POST /api/case-notes creates a note"""
        note_data = {
            "case_id": test_case_id,
            "content": f"TEST_Admin note {uuid.uuid4().hex[:8]}",
            "color": "yellow",
            "is_pinned": False
        }
        res = requests.post(
            f"{BASE_URL}/api/case-notes",
            json=note_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert data["content"] == note_data["content"]
        assert data["color"] == "yellow"
        print(f"PASS: Created note with ID {data['id']}")
        return data["id"]
    
    def test_create_note_as_cm(self, cm_token, test_case_id):
        """Case manager can create notes"""
        note_data = {
            "case_id": test_case_id,
            "content": f"TEST_CM note {uuid.uuid4().hex[:8]}",
            "color": "blue",
            "is_pinned": True
        }
        res = requests.post(
            f"{BASE_URL}/api/case-notes",
            json=note_data,
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_pinned"] == True
        print("PASS: Case manager created pinned note")
    
    def test_get_notes_for_case(self, admin_token, test_case_id):
        """GET /api/case-notes/case/{case_id} returns notes"""
        res = requests.get(
            f"{BASE_URL}/api/case-notes/case/{test_case_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        print(f"PASS: Retrieved {len(data)} notes for case")
    
    def test_client_cannot_create_note(self, client_token, test_case_id):
        """Client should not be able to create notes"""
        note_data = {
            "case_id": test_case_id,
            "content": "Client note attempt",
            "color": "yellow"
        }
        res = requests.post(
            f"{BASE_URL}/api/case-notes",
            json=note_data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert res.status_code == 403
        print("PASS: Client correctly forbidden from creating notes")


class TestCaseTags:
    """Phase 7A: Case Tags tests"""
    
    def test_update_case_tags(self, admin_token, test_case_id):
        """POST /api/case-notes/tags updates tags"""
        tag_data = {
            "case_id": test_case_id,
            "tags": ["urgent", "vip", "TEST_tag"]
        }
        res = requests.post(
            f"{BASE_URL}/api/case-notes/tags",
            json=tag_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "tags" in data
        assert "urgent" in data["tags"]
        print(f"PASS: Updated tags: {data['tags']}")
    
    def test_get_case_tags(self, admin_token, test_case_id):
        """GET /api/case-notes/tags/{case_id} returns tags"""
        res = requests.get(
            f"{BASE_URL}/api/case-notes/tags/{test_case_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "tags" in data
        assert isinstance(data["tags"], list)
        print(f"PASS: Retrieved tags: {data['tags']}")


class TestCannedResponses:
    """Phase 7A: Canned Responses CRUD tests"""
    
    @pytest.fixture
    def created_response_id(self, admin_token):
        """Create a canned response for testing"""
        resp_data = {
            "title": f"TEST_Response {uuid.uuid4().hex[:8]}",
            "content": "Thank you for your submission. We will review it shortly.",
            "category": "general",
            "shortcut": "/thanks",
            "is_shared": True
        }
        res = requests.post(
            f"{BASE_URL}/api/canned-responses",
            json=resp_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if res.status_code == 200:
            return res.json()["id"]
        return None
    
    def test_create_canned_response(self, admin_token):
        """POST /api/canned-responses creates response"""
        resp_data = {
            "title": f"TEST_Document Received {uuid.uuid4().hex[:8]}",
            "content": "We have received your document and will review it within 2 business days.",
            "category": "documents",
            "shortcut": "/docreceived",
            "is_shared": False
        }
        res = requests.post(
            f"{BASE_URL}/api/canned-responses",
            json=resp_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert data["title"] == resp_data["title"]
        assert data["usage_count"] == 0
        print(f"PASS: Created canned response: {data['title']}")
    
    def test_list_canned_responses(self, admin_token):
        """GET /api/canned-responses lists responses"""
        res = requests.get(
            f"{BASE_URL}/api/canned-responses",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        print(f"PASS: Listed {len(data)} canned responses")
    
    def test_use_canned_response(self, admin_token, created_response_id):
        """POST /api/canned-responses/{id}/use increments usage"""
        if not created_response_id:
            pytest.skip("No response created")
        res = requests.post(
            f"{BASE_URL}/api/canned-responses/{created_response_id}/use",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["usage_count"] >= 1
        print(f"PASS: Used response, count now: {data['usage_count']}")
    
    def test_cm_can_create_response(self, cm_token):
        """Case manager can create canned responses"""
        resp_data = {
            "title": f"TEST_CM Response {uuid.uuid4().hex[:8]}",
            "content": "Your case is progressing well.",
            "category": "updates"
        }
        res = requests.post(
            f"{BASE_URL}/api/canned-responses",
            json=resp_data,
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert res.status_code == 200
        print("PASS: Case manager created canned response")


class TestReferrals:
    """Phase 7B: Referral Program tests"""
    
    @pytest.fixture
    def created_referral_id(self, client_token):
        """Create a referral for testing"""
        ref_data = {
            "referred_name": f"TEST_Friend {uuid.uuid4().hex[:8]}",
            "referred_email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "referred_phone": "1234567890",
            "service_interested": "Canada PR",
            "notes": "Test referral"
        }
        res = requests.post(
            f"{BASE_URL}/api/referrals",
            json=ref_data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        if res.status_code == 200:
            return res.json()["id"]
        return None
    
    def test_create_referral_as_client(self, client_token):
        """POST /api/referrals creates referral"""
        ref_data = {
            "referred_name": f"TEST_John Doe {uuid.uuid4().hex[:8]}",
            "referred_email": f"john_{uuid.uuid4().hex[:8]}@example.com",
            "referred_phone": "9876543210",
            "service_interested": "Australia PR",
            "notes": "Interested in immigration"
        }
        res = requests.post(
            f"{BASE_URL}/api/referrals",
            json=ref_data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["reward_status"] == "pending"
        print(f"PASS: Created referral: {data['referred_name']}")
    
    def test_list_referrals_as_client(self, client_token):
        """GET /api/referrals lists client's referrals"""
        res = requests.get(
            f"{BASE_URL}/api/referrals",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        print(f"PASS: Client has {len(data)} referrals")
    
    def test_list_referrals_as_admin(self, admin_token):
        """Admin can see all referrals"""
        res = requests.get(
            f"{BASE_URL}/api/referrals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        print(f"PASS: Admin sees {len(data)} total referrals")
    
    def test_update_referral_status(self, admin_token, created_referral_id):
        """PUT /api/referrals/{id}/status updates status"""
        if not created_referral_id:
            pytest.skip("No referral created")
        res = requests.put(
            f"{BASE_URL}/api/referrals/{created_referral_id}/status?status=contacted",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        print("PASS: Updated referral status to contacted")
    
    def test_referral_stats(self, client_token):
        """GET /api/referrals/stats returns statistics"""
        res = requests.get(
            f"{BASE_URL}/api/referrals/stats",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "by_status" in data
        assert "conversion_rate" in data
        print(f"PASS: Referral stats - Total: {data['total']}, Rate: {data['conversion_rate']}%")


class TestGreetings:
    """Phase 7B: Client Greetings tests"""
    
    def test_get_greeting_templates(self, admin_token):
        """GET /api/greetings/templates returns templates"""
        res = requests.get(
            f"{BASE_URL}/api/greetings/templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check template structure
        template = data[0]
        assert "name" in template
        assert "message" in template
        print(f"PASS: Retrieved {len(data)} greeting templates")
    
    def test_send_greeting_custom(self, admin_token):
        """POST /api/greetings/send sends custom greeting"""
        greeting_data = {
            "type": "custom",
            "custom_message": "Thank you for being a valued client!",
            "send_to_all_clients": True
        }
        res = requests.post(
            f"{BASE_URL}/api/greetings/send",
            json=greeting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "greeting_id" in data
        assert "sent" in data
        print(f"PASS: Sent greeting to {data['sent']} clients")
    
    def test_send_greeting_festival(self, admin_token):
        """Send festival greeting using template"""
        greeting_data = {
            "type": "festival",
            "template_name": "Diwali",
            "send_to_all_clients": True
        }
        res = requests.post(
            f"{BASE_URL}/api/greetings/send",
            json=greeting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "greeting_id" in data
        print(f"PASS: Sent Diwali greeting to {data['sent']} clients")
    
    def test_greeting_history(self, admin_token):
        """GET /api/greetings/history returns history"""
        res = requests.get(
            f"{BASE_URL}/api/greetings/history",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        print(f"PASS: Retrieved {len(data)} greeting history entries")
    
    def test_client_cannot_send_greeting(self, client_token):
        """Client should not be able to send greetings"""
        greeting_data = {
            "type": "custom",
            "custom_message": "Hello",
            "send_to_all_clients": True
        }
        res = requests.post(
            f"{BASE_URL}/api/greetings/send",
            json=greeting_data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert res.status_code == 403
        print("PASS: Client correctly forbidden from sending greetings")


class TestConversionFunnel:
    """Phase 7B: Conversion Funnel Analytics tests"""
    
    def test_conversion_funnel_admin(self, admin_token):
        """GET /api/analytics/conversion-funnel returns funnel data"""
        res = requests.get(
            f"{BASE_URL}/api/analytics/conversion-funnel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "stages" in data
        assert isinstance(data["stages"], list)
        if data["stages"]:
            stage = data["stages"][0]
            assert "stage" in stage
            assert "total" in stage
            assert "rate" in stage
        print(f"PASS: Conversion funnel has {len(data['stages'])} stages")
    
    def test_conversion_funnel_partner(self, partner_token):
        """Partner can access conversion funnel"""
        res = requests.get(
            f"{BASE_URL}/api/analytics/conversion-funnel",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert res.status_code == 200
        print("PASS: Partner can access conversion funnel")
    
    def test_conversion_funnel_client_restricted(self, client_token):
        """Client gets empty funnel (restricted)"""
        res = requests.get(
            f"{BASE_URL}/api/analytics/conversion-funnel",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data.get("stages") == []
        print("PASS: Client correctly gets empty funnel data")


class TestCountryProductAnalytics:
    """Phase 7B: Country/Product Analytics tests"""
    
    def test_country_product_admin(self, admin_token):
        """GET /api/analytics/country-product returns analytics"""
        res = requests.get(
            f"{BASE_URL}/api/analytics/country-product",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "by_product" in data
        assert "by_country" in data
        assert isinstance(data["by_product"], list)
        assert isinstance(data["by_country"], list)
        print(f"PASS: Country/Product analytics - {len(data['by_country'])} countries, {len(data['by_product'])} products")
    
    def test_country_product_partner(self, partner_token):
        """Partner can access country/product analytics"""
        res = requests.get(
            f"{BASE_URL}/api/analytics/country-product",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert res.status_code == 200
        print("PASS: Partner can access country/product analytics")


class TestCommissionAnalytics:
    """Phase 7B: Commission Analytics tests"""
    
    def test_commission_analytics_admin(self, admin_token):
        """GET /api/analytics/commission-analytics returns data"""
        res = requests.get(
            f"{BASE_URL}/api/analytics/commission-analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "partners" in data
        assert "total_commission" in data
        assert isinstance(data["partners"], list)
        print(f"PASS: Commission analytics - Total: ${data['total_commission']}, Partners: {len(data['partners'])}")
    
    def test_commission_analytics_partner(self, partner_token):
        """Partner can access commission analytics"""
        res = requests.get(
            f"{BASE_URL}/api/analytics/commission-analytics",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert res.status_code == 200
        print("PASS: Partner can access commission analytics")
    
    def test_commission_analytics_monthly_trend(self, admin_token):
        """Commission analytics includes monthly trend"""
        res = requests.get(
            f"{BASE_URL}/api/analytics/commission-analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "monthly_trend" in data
        assert isinstance(data["monthly_trend"], list)
        print(f"PASS: Commission trend has {len(data['monthly_trend'])} months")


class TestSurveySubmit:
    """Phase 7B: Survey Submit tests"""
    
    def test_survey_stats_admin(self, admin_token):
        """GET /api/surveys/stats returns stats"""
        res = requests.get(
            f"{BASE_URL}/api/surveys/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "avg_rating" in data
        print(f"PASS: Survey stats - Total: {data['total']}, Avg: {data['avg_rating']}")


class TestHealthEndpoint:
    """Basic health check"""
    
    def test_health(self):
        """GET /api/health returns healthy"""
        res = requests.get(f"{BASE_URL}/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        print("PASS: Health endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
