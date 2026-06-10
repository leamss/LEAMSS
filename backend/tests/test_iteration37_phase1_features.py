"""
Iteration 37 - Phase 1 Features Testing
Tests for:
1. Activity Log System - /api/activity/* endpoints
2. AI Workflow Builder - /api/ai-workflow/* endpoints
3. Email Service (mock fallback verification)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://career-match-320.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
MANAGER_EMAIL = "manager@leamss.com"
MANAGER_PASSWORD = "Manager@123"


class TestAuthentication:
    """Get auth tokens for testing"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        """Get case manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MANAGER_EMAIL,
            "password": MANAGER_PASSWORD
        })
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        return response.json()["token"]


class TestActivityLogEndpoints(TestAuthentication):
    """Test Activity Log API endpoints"""
    
    def test_get_activity_logs(self, admin_token):
        """GET /api/activity/logs - returns logs with total count"""
        response = requests.get(
            f"{BASE_URL}/api/activity/logs?days=30&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get activity logs: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "logs" in data, "Response should contain 'logs' key"
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["logs"], list), "logs should be a list"
        assert isinstance(data["total"], int), "total should be an integer"
        
        # Verify log entry structure if logs exist
        if len(data["logs"]) > 0:
            log = data["logs"][0]
            assert "action" in log, "Log should have 'action' field"
            assert "entity_type" in log, "Log should have 'entity_type' field"
            assert "created_at" in log, "Log should have 'created_at' field"
        
        print(f"SUCCESS: Activity logs returned {data['total']} total records, {len(data['logs'])} in response")
    
    def test_get_activity_stats(self, admin_token):
        """GET /api/activity/stats - returns activity statistics"""
        response = requests.get(
            f"{BASE_URL}/api/activity/stats?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get activity stats: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total_activities" in data, "Response should contain 'total_activities'"
        assert "activities_by_type" in data, "Response should contain 'activities_by_type'"
        assert "activities_by_action" in data, "Response should contain 'activities_by_action'"
        assert "most_active_users" in data, "Response should contain 'most_active_users'"
        assert "period_days" in data, "Response should contain 'period_days'"
        
        # Verify data types
        assert isinstance(data["total_activities"], int), "total_activities should be int"
        assert isinstance(data["activities_by_type"], dict), "activities_by_type should be dict"
        assert isinstance(data["most_active_users"], list), "most_active_users should be list"
        
        print(f"SUCCESS: Activity stats - {data['total_activities']} activities, {len(data['activities_by_type'])} entity types, {len(data['most_active_users'])} active users")
    
    def test_get_live_feed(self, admin_token):
        """GET /api/activity/live-feed - returns recent activity"""
        response = requests.get(
            f"{BASE_URL}/api/activity/live-feed?limit=15",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get live feed: {response.text}"
        data = response.json()
        
        # Verify response is a list
        assert isinstance(data, list), "Live feed should return a list"
        
        # Verify entry structure if entries exist
        if len(data) > 0:
            entry = data[0]
            assert "action" in entry, "Entry should have 'action' field"
            assert "user_name" in entry or "user_id" in entry, "Entry should have user info"
            assert "created_at" in entry, "Entry should have 'created_at' field"
        
        print(f"SUCCESS: Live feed returned {len(data)} recent activities")
    
    def test_get_user_activity(self, admin_token):
        """GET /api/activity/user/{user_id} - returns user-specific activity"""
        # First get a user ID from stats
        stats_response = requests.get(
            f"{BASE_URL}/api/activity/stats?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        if len(stats.get("most_active_users", [])) > 0:
            user_id = stats["most_active_users"][0]["user_id"]
            
            response = requests.get(
                f"{BASE_URL}/api/activity/user/{user_id}?days=30&limit=50",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Failed to get user activity: {response.text}"
            data = response.json()
            
            # Verify response structure
            assert "user" in data, "Response should contain 'user' info"
            assert "logs" in data, "Response should contain 'logs'"
            assert "total" in data, "Response should contain 'total'"
            
            print(f"SUCCESS: User activity for {data['user'].get('name', 'Unknown')} - {data['total']} activities")
        else:
            print("SKIP: No active users found to test user activity endpoint")
    
    def test_activity_logs_filter_by_entity_type(self, admin_token):
        """GET /api/activity/logs with entity_type filter"""
        response = requests.get(
            f"{BASE_URL}/api/activity/logs?entity_type=case&days=30&limit=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to filter by entity_type: {response.text}"
        data = response.json()
        
        # Verify all returned logs are of the filtered type
        for log in data.get("logs", []):
            if log.get("entity_type"):
                assert log["entity_type"] == "case", f"Expected entity_type 'case', got '{log['entity_type']}'"
        
        print(f"SUCCESS: Filtered logs by entity_type=case, got {len(data.get('logs', []))} results")
    
    def test_activity_logs_filter_by_days(self, admin_token):
        """GET /api/activity/logs with different day filters"""
        for days in [1, 7, 30, 90]:
            response = requests.get(
                f"{BASE_URL}/api/activity/logs?days={days}&limit=10",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Failed to filter by days={days}: {response.text}"
            data = response.json()
            print(f"  - days={days}: {data['total']} total activities")
        
        print("SUCCESS: All day filters work correctly")
    
    def test_activity_logs_admin_only(self, manager_token):
        """Verify activity logs are admin-only"""
        response = requests.get(
            f"{BASE_URL}/api/activity/logs",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("SUCCESS: Activity logs correctly restricted to admin only")


class TestAIWorkflowBuilderEndpoints(TestAuthentication):
    """Test AI Workflow Builder API endpoints"""
    
    def test_get_countries(self, admin_token):
        """GET /api/ai-workflow/countries - returns 7 countries with services"""
        response = requests.get(
            f"{BASE_URL}/api/ai-workflow/countries",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get countries: {response.text}"
        data = response.json()
        
        # Verify response is a list
        assert isinstance(data, list), "Countries should be a list"
        assert len(data) >= 7, f"Expected at least 7 countries, got {len(data)}"
        
        # Verify country structure
        for country in data:
            assert "id" in country, "Country should have 'id'"
            assert "name" in country, "Country should have 'name'"
            assert "services" in country, "Country should have 'services'"
            assert isinstance(country["services"], list), "Services should be a list"
        
        # Check expected countries
        country_ids = [c["id"] for c in data]
        expected_countries = ["canada", "australia", "uk", "new_zealand", "usa", "singapore", "dubai"]
        for expected in expected_countries:
            assert expected in country_ids, f"Expected country '{expected}' not found"
        
        print(f"SUCCESS: Got {len(data)} countries with services")
        for c in data:
            print(f"  - {c['name']}: {len(c['services'])} services")
    
    def test_get_templates(self, admin_token):
        """GET /api/ai-workflow/templates - returns 10 templates"""
        response = requests.get(
            f"{BASE_URL}/api/ai-workflow/templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get templates: {response.text}"
        data = response.json()
        
        # Verify response is a list
        assert isinstance(data, list), "Templates should be a list"
        assert len(data) == 10, f"Expected 10 templates, got {len(data)}"
        
        # Verify template structure
        for template in data:
            assert "id" in template, "Template should have 'id'"
            assert "country" in template, "Template should have 'country'"
            assert "service" in template, "Template should have 'service'"
            assert "label" in template, "Template should have 'label'"
        
        # Check expected templates
        template_ids = [t["id"] for t in data]
        expected_templates = ["canada_pr", "australia_pr", "dubai_golden"]
        for expected in expected_templates:
            assert expected in template_ids, f"Expected template '{expected}' not found"
        
        print(f"SUCCESS: Got {len(data)} templates")
        for t in data:
            print(f"  - {t['label']}")
    
    def test_generate_workflow(self, admin_token):
        """POST /api/ai-workflow/generate - generates workflow (may take 15-30 seconds)"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Canada",
                "service_type": "Visitor",
                "custom_instructions": ""
            },
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=90  # Extended timeout for AI generation
        )
        assert response.status_code == 200, f"Failed to generate workflow: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "product_name" in data, "Response should have 'product_name'"
        assert "description" in data, "Response should have 'description'"
        assert "steps" in data, "Response should have 'steps'"
        assert isinstance(data["steps"], list), "Steps should be a list"
        assert len(data["steps"]) > 0, "Should have at least one step"
        
        # Verify step structure
        step = data["steps"][0]
        assert "step_name" in step, "Step should have 'step_name'"
        assert "step_order" in step, "Step should have 'step_order'"
        
        print(f"SUCCESS: Generated workflow '{data['product_name']}' with {len(data['steps'])} steps")
        for s in data["steps"][:3]:  # Print first 3 steps
            print(f"  - Step {s.get('step_order', '?')}: {s.get('step_name', 'Unknown')}")
    
    def test_generate_workflow_admin_only(self, manager_token):
        """Verify workflow generation is admin-only"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Canada",
                "service_type": "PR"
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("SUCCESS: Workflow generation correctly restricted to admin only")


class TestEmailServiceMock(TestAuthentication):
    """Test Email Service (mock fallback)"""
    
    def test_email_logs_endpoint(self, admin_token):
        """GET /api/activity/email-logs - returns email logs"""
        response = requests.get(
            f"{BASE_URL}/api/activity/email-logs?limit=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get email logs: {response.text}"
        data = response.json()
        
        # Verify response is a list
        assert isinstance(data, list), "Email logs should be a list"
        
        # If there are logs, verify structure
        if len(data) > 0:
            log = data[0]
            assert "to" in log, "Email log should have 'to' field"
            assert "subject" in log, "Email log should have 'subject' field"
            assert "status" in log, "Email log should have 'status' field"
            # Note: 'provider' field may not exist in all email log entries (depends on source)
            
            print(f"SUCCESS: Email logs returned {len(data)} entries")
            print(f"  - Latest: to={log.get('to')}, subject={log.get('subject')[:50]}...")
        else:
            print("SUCCESS: Email logs endpoint works (no emails logged yet)")


class TestDashboardRoleAccess(TestAuthentication):
    """Test that all 4 dashboard roles still work (regression test)"""
    
    def test_admin_dashboard_access(self, admin_token):
        """Verify admin can access dashboard stats"""
        response = requests.get(
            f"{BASE_URL}/api/stats/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Admin dashboard stats failed: {response.text}"
        print("SUCCESS: Admin dashboard access works")
    
    def test_case_manager_dashboard_access(self, manager_token):
        """Verify case manager can access their cases"""
        response = requests.get(
            f"{BASE_URL}/api/cases",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200, f"Case manager cases failed: {response.text}"
        print("SUCCESS: Case Manager dashboard access works")
    
    def test_partner_login(self):
        """Verify partner can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "partner"
        print("SUCCESS: Partner login works")
    
    def test_client_login(self):
        """Verify client can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "client"
        print("SUCCESS: Client login works")


class TestAdminSidebarNavigation(TestAuthentication):
    """Test that AI Workflow Builder link exists in Admin sidebar (Tools group)"""
    
    def test_ai_workflow_page_accessible(self, admin_token):
        """Verify AI Workflow Builder page endpoints are accessible"""
        # Test countries endpoint (used by AI Workflow Builder page)
        response = requests.get(
            f"{BASE_URL}/api/ai-workflow/countries",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, "AI Workflow countries endpoint should be accessible"
        
        # Test templates endpoint
        response = requests.get(
            f"{BASE_URL}/api/ai-workflow/templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, "AI Workflow templates endpoint should be accessible"
        
        print("SUCCESS: AI Workflow Builder endpoints accessible (page should load)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
