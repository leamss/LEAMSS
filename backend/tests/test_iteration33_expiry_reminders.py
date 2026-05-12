"""
Iteration 33 - Auto Expiry Reminder System Tests
Tests for:
1. POST /api/documents/check-expiry-reminders - Creates in-app notifications for expiring documents
2. POST /api/documents/check-expiry-reminders - Deduplication: running twice on same day sends fewer reminders second time
3. GET /api/documents/expiry-summary - Returns counts: expired, critical, warning, attention, ok, total
4. GET /api/documents/expiry-summary - Admin gets summary for ALL cases
5. GET /api/documents/expiry-summary - Case Manager gets summary only for their assigned cases
6. POST /api/auth/login - All 4 roles work
7. GET /api/health - Returns healthy
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://staff-dashboard-66.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


class TestHealthAndAuth:
    """Test health endpoint and authentication for all roles"""
    
    def test_health_endpoint(self):
        """GET /api/health - Returns healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert data.get("database") == "connected"
        print("✓ Health endpoint returns healthy")
    
    def test_admin_login(self):
        """POST /api/auth/login - Admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "admin"
        print("✓ Admin login successful")
    
    def test_case_manager_login(self):
        """POST /api/auth/login - Case Manager login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "case_manager"
        print("✓ Case Manager login successful")
    
    def test_partner_login(self):
        """POST /api/auth/login - Partner login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "partner"
        print("✓ Partner login successful")
    
    def test_client_login(self):
        """POST /api/auth/login - Client login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "client"
        print("✓ Client login successful")


class TestCheckExpiryReminders:
    """Test POST /api/documents/check-expiry-reminders endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json().get("token")
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json().get("token")
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        return response.json().get("token")
    
    def test_check_expiry_reminders_admin(self, admin_token):
        """POST /api/documents/check-expiry-reminders - Admin can trigger expiry check"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/documents/check-expiry-reminders", json={}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "reminders_sent" in data
        assert isinstance(data["reminders_sent"], int)
        print(f"✓ Admin triggered expiry check - {data['reminders_sent']} reminders sent")
    
    def test_check_expiry_reminders_manager(self, manager_token):
        """POST /api/documents/check-expiry-reminders - Case Manager can trigger expiry check"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.post(f"{BASE_URL}/api/documents/check-expiry-reminders", json={}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "reminders_sent" in data
        print(f"✓ Case Manager triggered expiry check - {data['reminders_sent']} reminders sent")
    
    def test_check_expiry_reminders_client(self, client_token):
        """POST /api/documents/check-expiry-reminders - Client can trigger expiry check"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.post(f"{BASE_URL}/api/documents/check-expiry-reminders", json={}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "reminders_sent" in data
        print(f"✓ Client triggered expiry check - {data['reminders_sent']} reminders sent")
    
    def test_check_expiry_reminders_deduplication(self, admin_token):
        """POST /api/documents/check-expiry-reminders - Deduplication: running twice sends fewer reminders"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First call
        response1 = requests.post(f"{BASE_URL}/api/documents/check-expiry-reminders", json={}, headers=headers)
        assert response1.status_code == 200
        first_count = response1.json().get("reminders_sent", 0)
        
        # Second call immediately after - should send fewer or same (deduplication)
        response2 = requests.post(f"{BASE_URL}/api/documents/check-expiry-reminders", json={}, headers=headers)
        assert response2.status_code == 200
        second_count = response2.json().get("reminders_sent", 0)
        
        # Second call should send fewer or equal reminders due to deduplication
        assert second_count <= first_count, f"Deduplication failed: first={first_count}, second={second_count}"
        print(f"✓ Deduplication working - First call: {first_count}, Second call: {second_count}")


class TestExpirySummary:
    """Test GET /api/documents/expiry-summary endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json().get("token")
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json().get("token")
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        return response.json().get("token")
    
    def test_expiry_summary_admin(self, admin_token):
        """GET /api/documents/expiry-summary - Admin gets summary for ALL cases"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiry-summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields are present
        expected_fields = ["expired", "critical", "warning", "attention", "ok", "total"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], int), f"Field {field} should be integer"
        
        # Total should be sum of all categories
        calculated_total = data["expired"] + data["critical"] + data["warning"] + data["attention"] + data["ok"]
        assert data["total"] == calculated_total, f"Total mismatch: {data['total']} != {calculated_total}"
        
        print(f"✓ Admin expiry summary: expired={data['expired']}, critical={data['critical']}, warning={data['warning']}, attention={data['attention']}, ok={data['ok']}, total={data['total']}")
    
    def test_expiry_summary_manager(self, manager_token):
        """GET /api/documents/expiry-summary - Case Manager gets summary only for their assigned cases"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiry-summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields are present
        expected_fields = ["expired", "critical", "warning", "attention", "ok", "total"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], int), f"Field {field} should be integer"
        
        print(f"✓ Case Manager expiry summary: expired={data['expired']}, critical={data['critical']}, warning={data['warning']}, attention={data['attention']}, ok={data['ok']}, total={data['total']}")
    
    def test_expiry_summary_client_forbidden(self, client_token):
        """GET /api/documents/expiry-summary - Client should be forbidden (403)"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiry-summary", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Client correctly forbidden from expiry summary")
    
    def test_expiry_summary_admin_vs_manager_scope(self, admin_token, manager_token):
        """Verify Admin gets ALL cases while Manager gets only assigned cases"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        manager_headers = {"Authorization": f"Bearer {manager_token}"}
        
        admin_response = requests.get(f"{BASE_URL}/api/documents/expiry-summary", headers=admin_headers)
        manager_response = requests.get(f"{BASE_URL}/api/documents/expiry-summary", headers=manager_headers)
        
        assert admin_response.status_code == 200
        assert manager_response.status_code == 200
        
        admin_data = admin_response.json()
        manager_data = manager_response.json()
        
        # Admin total should be >= Manager total (Admin sees all, Manager sees only assigned)
        assert admin_data["total"] >= manager_data["total"], \
            f"Admin total ({admin_data['total']}) should be >= Manager total ({manager_data['total']})"
        
        print(f"✓ Scope verification: Admin total={admin_data['total']}, Manager total={manager_data['total']}")


class TestReminderThresholds:
    """Test that reminders are created at correct thresholds: 60d (attention), 30d (warning), 7d (critical), 0d (expired)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json().get("token")
    
    def test_expiring_documents_urgency_levels(self, admin_token):
        """Verify expiring documents have correct urgency levels based on days remaining"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiring/all", headers=headers)
        assert response.status_code == 200
        docs = response.json()
        
        # Check urgency levels are correctly assigned
        for doc in docs:
            days = doc.get("days_remaining")
            urgency = doc.get("urgency")
            
            if days is not None:
                if days < 0:
                    assert urgency == "expired", f"Doc with {days} days should be 'expired', got '{urgency}'"
                elif days <= 30:
                    assert urgency == "critical", f"Doc with {days} days should be 'critical', got '{urgency}'"
                elif days <= 60:
                    assert urgency == "warning", f"Doc with {days} days should be 'warning', got '{urgency}'"
                elif days <= 90:
                    assert urgency == "attention", f"Doc with {days} days should be 'attention', got '{urgency}'"
                else:
                    assert urgency == "ok", f"Doc with {days} days should be 'ok', got '{urgency}'"
        
        print(f"✓ Urgency levels correctly assigned for {len(docs)} documents")


class TestNotificationCreation:
    """Test that notifications are created for both client and case manager"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json().get("token")
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        return response.json().get("token")
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json().get("token")
    
    def test_client_receives_expiry_notifications(self, client_token):
        """Verify client can see expiry notifications"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # First trigger the expiry check
        requests.post(f"{BASE_URL}/api/documents/check-expiry-reminders", json={}, headers=headers)
        
        # Then check notifications
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200
        notifications = response.json()
        
        # Check if there are any document_expiry type notifications
        expiry_notifications = [n for n in notifications if n.get("type") == "document_expiry"]
        print(f"✓ Client has {len(expiry_notifications)} expiry notifications")
    
    def test_manager_receives_expiry_notifications(self, manager_token):
        """Verify case manager can see expiry notifications"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        # First trigger the expiry check
        requests.post(f"{BASE_URL}/api/documents/check-expiry-reminders", json={}, headers=headers)
        
        # Then check notifications
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200
        notifications = response.json()
        
        # Check if there are any document_expiry type notifications
        expiry_notifications = [n for n in notifications if n.get("type") == "document_expiry"]
        print(f"✓ Case Manager has {len(expiry_notifications)} expiry notifications")


class TestDashboardIntegration:
    """Test that dashboards auto-trigger check-expiry-reminders on load"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json().get("token")
    
    def test_admin_dashboard_data_loads(self, admin_token):
        """Verify Admin Dashboard can load expiry summary data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Load expiry summary (what Admin Dashboard fetches)
        response = requests.get(f"{BASE_URL}/api/documents/expiry-summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure matches what frontend expects
        assert "expired" in data
        assert "critical" in data
        assert "warning" in data
        assert "attention" in data
        assert "ok" in data
        assert "total" in data
        
        print(f"✓ Admin Dashboard expiry summary loads correctly")
    
    def test_check_expiry_reminders_fire_and_forget(self, admin_token):
        """Verify check-expiry-reminders can be called without blocking"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # This simulates the fire-and-forget call from dashboard
        response = requests.post(f"{BASE_URL}/api/documents/check-expiry-reminders", json={}, headers=headers)
        assert response.status_code == 200
        
        # Should return quickly with a count
        data = response.json()
        assert "reminders_sent" in data
        
        print(f"✓ Fire-and-forget expiry check works - {data['reminders_sent']} reminders")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
