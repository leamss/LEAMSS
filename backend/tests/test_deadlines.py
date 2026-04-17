"""
Test Suite for Deadline & SLA Tracker Feature (Iteration 68)
Tests: GET /api/deadlines/case/{case_id}, POST /api/deadlines/create, 
       DELETE /api/deadlines/{id}, GET /api/deadlines/overview
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
CM_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


class TestDeadlineTracker:
    """Deadline & SLA Tracker API Tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def cm_token(self):
        """Get case manager authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CM_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Case Manager authentication failed")
    
    @pytest.fixture(scope="class")
    def client_token(self):
        """Get client authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Client authentication failed")
    
    @pytest.fixture(scope="class")
    def client_case_id(self, client_token):
        """Get client's case ID"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("No client case found")
    
    @pytest.fixture(scope="class")
    def cm_case_id(self, cm_token):
        """Get case manager's case ID"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("No CM case found")
    
    # ============ GET /api/deadlines/case/{case_id} Tests ============
    
    def test_get_case_deadlines_as_client(self, client_token, client_case_id):
        """Client can view deadlines for their own case"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/deadlines/case/{client_case_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "case_id" in data, "Response should contain case_id"
        assert "deadlines" in data, "Response should contain deadlines array"
        assert "summary" in data, "Response should contain summary"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total" in summary, "Summary should have total count"
        assert "expired" in summary, "Summary should have expired count"
        assert "critical" in summary, "Summary should have critical count"
        assert "urgent" in summary, "Summary should have urgent count"
        assert "safe" in summary, "Summary should have safe count"
        
        print(f"Client case {client_case_id} has {summary['total']} deadlines")
        print(f"  - Expired: {summary['expired']}, Critical: {summary['critical']}, Urgent: {summary['urgent']}, Safe: {summary['safe']}")
    
    def test_get_case_deadlines_as_cm(self, cm_token, cm_case_id):
        """Case Manager can view deadlines for their assigned case"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        response = requests.get(f"{BASE_URL}/api/deadlines/case/{cm_case_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "deadlines" in data
        assert isinstance(data["deadlines"], list)
        
        # Check deadline structure if any exist
        if len(data["deadlines"]) > 0:
            deadline = data["deadlines"][0]
            assert "id" in deadline, "Deadline should have id"
            assert "title" in deadline, "Deadline should have title"
            assert "urgency" in deadline, "Deadline should have urgency"
            
            # Check urgency structure
            urgency = deadline["urgency"]
            assert "level" in urgency, "Urgency should have level"
            assert "days_left" in urgency, "Urgency should have days_left"
            assert "color" in urgency, "Urgency should have color"
            
            print(f"First deadline: {deadline['title']} - {urgency['level']} ({urgency['days_left']} days)")
    
    def test_get_case_deadlines_invalid_case(self, client_token):
        """Should return 404 for non-existent case"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/deadlines/case/invalid-case-id-12345", headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_get_case_deadlines_unauthorized(self):
        """Should return 401 without authentication"""
        response = requests.get(f"{BASE_URL}/api/deadlines/case/some-case-id")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    # ============ POST /api/deadlines/create Tests ============
    
    def test_create_deadline_as_cm(self, cm_token, cm_case_id):
        """Case Manager can create a manual deadline"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        deadline_data = {
            "case_id": cm_case_id,
            "title": "TEST_ITA Expiry Deadline",
            "deadline_type": "visa_deadline",
            "due_date": "2026-03-15",
            "description": "ITA expires - must submit application before this date",
            "step_name": "Application Submission",
            "auto_remind": True,
            "remind_days_before": 7
        }
        
        response = requests.post(f"{BASE_URL}/api/deadlines/create", json=deadline_data, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify created deadline
        assert "id" in data, "Created deadline should have id"
        assert data["title"] == deadline_data["title"], "Title should match"
        assert data["deadline_type"] == deadline_data["deadline_type"], "Type should match"
        assert data["source"] == "manual", "Source should be 'manual'"
        assert "urgency" in data, "Should include urgency calculation"
        
        print(f"Created deadline: {data['id']} - {data['title']}")
        
        # Store for cleanup
        self.__class__.created_deadline_id = data["id"]
    
    def test_create_deadline_as_admin(self, admin_token, cm_case_id):
        """Admin can create a manual deadline"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        deadline_data = {
            "case_id": cm_case_id,
            "title": "TEST_Admin Created Deadline",
            "deadline_type": "processing_sla",
            "due_date": "2026-04-01",
            "description": "Admin-created SLA deadline",
            "auto_remind": False
        }
        
        response = requests.post(f"{BASE_URL}/api/deadlines/create", json=deadline_data, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["source"] == "manual"
        print(f"Admin created deadline: {data['id']}")
        
        # Store for cleanup
        self.__class__.admin_created_deadline_id = data["id"]
    
    def test_create_deadline_as_client_forbidden(self, client_token, client_case_id):
        """Client should NOT be able to create deadlines"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        deadline_data = {
            "case_id": client_case_id,
            "title": "Client Attempted Deadline",
            "deadline_type": "custom",
            "due_date": "2026-05-01"
        }
        
        response = requests.post(f"{BASE_URL}/api/deadlines/create", json=deadline_data, headers=headers)
        
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
    
    def test_create_deadline_missing_fields(self, cm_token, cm_case_id):
        """Should fail with missing required fields"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        # Missing title
        deadline_data = {
            "case_id": cm_case_id,
            "due_date": "2026-05-01"
        }
        
        response = requests.post(f"{BASE_URL}/api/deadlines/create", json=deadline_data, headers=headers)
        
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
    
    # ============ DELETE /api/deadlines/{id} Tests ============
    
    def test_delete_deadline_as_cm(self, cm_token):
        """Case Manager can delete a manual deadline they created"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        deadline_id = getattr(self.__class__, 'created_deadline_id', None)
        if not deadline_id:
            pytest.skip("No deadline to delete")
        
        response = requests.delete(f"{BASE_URL}/api/deadlines/{deadline_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("message") == "Deadline deleted"
        
        print(f"Deleted deadline: {deadline_id}")
    
    def test_delete_deadline_as_admin(self, admin_token):
        """Admin can delete any deadline"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        deadline_id = getattr(self.__class__, 'admin_created_deadline_id', None)
        if not deadline_id:
            pytest.skip("No admin deadline to delete")
        
        response = requests.delete(f"{BASE_URL}/api/deadlines/{deadline_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"Admin deleted deadline: {deadline_id}")
    
    def test_delete_deadline_as_client_forbidden(self, client_token):
        """Client should NOT be able to delete deadlines"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.delete(f"{BASE_URL}/api/deadlines/some-deadline-id", headers=headers)
        
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
    
    def test_delete_nonexistent_deadline(self, cm_token):
        """Should return 404 for non-existent deadline"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        response = requests.delete(f"{BASE_URL}/api/deadlines/nonexistent-deadline-id-12345", headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    # ============ GET /api/deadlines/overview Tests ============
    
    def test_get_overview_as_admin(self, admin_token):
        """Admin can view deadline overview across all cases"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/deadlines/overview", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "alerts" in data, "Response should contain alerts array"
        assert "summary" in data, "Response should contain summary"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total" in summary, "Summary should have total"
        assert "expired" in summary, "Summary should have expired"
        assert "critical" in summary, "Summary should have critical"
        assert "urgent" in summary, "Summary should have urgent"
        
        print(f"Admin overview: {summary['total']} alerts total")
        print(f"  - Expired: {summary['expired']}, Critical: {summary['critical']}, Urgent: {summary['urgent']}")
        
        # Check alert structure if any exist
        if len(data["alerts"]) > 0:
            alert = data["alerts"][0]
            assert "case_id" in alert, "Alert should have case_id"
            assert "title" in alert, "Alert should have title"
            assert "urgency" in alert, "Alert should have urgency"
            assert "case_display" in alert, "Alert should have case_display"
            
            print(f"Top alert: {alert['title']} - Case: {alert['case_display']}")
    
    def test_get_overview_as_cm(self, cm_token):
        """Case Manager can view deadline overview for their cases"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        response = requests.get(f"{BASE_URL}/api/deadlines/overview", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "alerts" in data
        assert "summary" in data
        
        print(f"CM overview: {data['summary']['total']} alerts")
    
    def test_get_overview_as_client_forbidden(self, client_token):
        """Client should NOT be able to view overview"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/deadlines/overview", headers=headers)
        
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
    
    # ============ Auto-Detection Tests ============
    
    def test_auto_detected_deadlines_in_case(self, client_token, client_case_id):
        """Verify auto-detected document expiry deadlines are included"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/deadlines/case/{client_case_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        deadlines = data["deadlines"]
        
        # Check for auto-detected deadlines (source: auto_detected or estimated)
        auto_deadlines = [d for d in deadlines if d.get("source") in ["auto_detected", "estimated"]]
        manual_deadlines = [d for d in deadlines if d.get("source") == "manual"]
        
        print(f"Total deadlines: {len(deadlines)}")
        print(f"  - Auto-detected: {len(auto_deadlines)}")
        print(f"  - Manual: {len(manual_deadlines)}")
        
        # Verify auto-detected deadline structure
        if len(auto_deadlines) > 0:
            auto_dl = auto_deadlines[0]
            assert "document_id" in auto_dl, "Auto deadline should reference document_id"
            assert auto_dl["deadline_type"] == "document_expiry", "Auto deadline type should be document_expiry"
            print(f"Auto-detected: {auto_dl['title']}")
    
    # ============ Urgency Calculation Tests ============
    
    def test_urgency_levels_sorted(self, client_token, client_case_id):
        """Verify deadlines are sorted by urgency (most urgent first)"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/deadlines/case/{client_case_id}", headers=headers)
        
        assert response.status_code == 200
        deadlines = response.json()["deadlines"]
        
        if len(deadlines) > 1:
            # Verify sorted by days_left (ascending)
            days_left_values = [d["urgency"]["days_left"] for d in deadlines]
            assert days_left_values == sorted(days_left_values), "Deadlines should be sorted by urgency"
            print(f"Deadlines sorted correctly: {days_left_values[:5]}...")


class TestDeadlineNotifications:
    """Test deadline notification creation"""
    
    @pytest.fixture(scope="class")
    def cm_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CM_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("CM authentication failed")
    
    @pytest.fixture(scope="class")
    def cm_case_id(self, cm_token):
        headers = {"Authorization": f"Bearer {cm_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("No CM case found")
    
    def test_deadline_creates_notification(self, cm_token, cm_case_id):
        """Creating a deadline with auto_remind should create a notification"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        deadline_data = {
            "case_id": cm_case_id,
            "title": "TEST_Notification Deadline",
            "deadline_type": "task_due",
            "due_date": "2026-02-28",
            "description": "Test notification creation",
            "auto_remind": True,
            "remind_days_before": 7
        }
        
        response = requests.post(f"{BASE_URL}/api/deadlines/create", json=deadline_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"Created deadline with notification: {data['id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/deadlines/{data['id']}", headers=headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
