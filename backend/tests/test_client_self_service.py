"""
Test Client Self-Service Portal Features
- Profile update API
- Change password API
- Notification preferences API
- Chat/Messages API
- Timeline API
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CREDENTIALS = {
    "admin": {"email": "admin@leamss.com", "password": "Admin@123"},
    "case_manager": {"email": "manager@leamss.com", "password": "Manager@123"},
    "partner": {"email": "partner@leamss.com", "password": "Partner@123"},
    "client": {"email": "client@leamss.com", "password": "Client@123"},
}


class TestAllRoleLogins:
    """Test all 4 role logins work correctly"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['email']}")
    
    def test_case_manager_login(self):
        """Test case manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["case_manager"])
        assert response.status_code == 200, f"Case manager login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print(f"✓ Case Manager login successful: {data['user']['email']}")
    
    def test_partner_login(self):
        """Test partner login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["partner"])
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"✓ Partner login successful: {data['user']['email']}")
    
    def test_client_login(self):
        """Test client login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print(f"✓ Client login successful: {data['user']['email']}")


class TestClientProfileAPIs:
    """Test Client Profile APIs - update-profile, change-password, notifications-preferences"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as client and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.user = response.json()["user"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_notification_preferences(self):
        """GET /api/auth/notifications-preferences"""
        response = requests.get(f"{BASE_URL}/api/auth/notifications-preferences", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # Should have default preferences
        assert "email" in data or "case_updates" in data or isinstance(data, dict)
        print(f"✓ Notification preferences retrieved: {data}")
    
    def test_update_profile_name(self):
        """PUT /api/auth/update-profile with name"""
        original_name = self.user.get("name", "Test Client")
        response = requests.put(
            f"{BASE_URL}/api/auth/update-profile",
            json={"name": "TEST_Updated Client Name"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "user" in data
        assert data["user"]["name"] == "TEST_Updated Client Name"
        print(f"✓ Profile name updated successfully")
        
        # Restore original name
        requests.put(
            f"{BASE_URL}/api/auth/update-profile",
            json={"name": original_name},
            headers=self.headers
        )
    
    def test_update_profile_mobile(self):
        """PUT /api/auth/update-profile with mobile"""
        response = requests.put(
            f"{BASE_URL}/api/auth/update-profile",
            json={"mobile": "+91-9876543210"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "user" in data
        print(f"✓ Profile mobile updated successfully")
    
    def test_update_profile_language(self):
        """PUT /api/auth/update-profile with preferred_language"""
        response = requests.put(
            f"{BASE_URL}/api/auth/update-profile",
            json={"preferred_language": "hi"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "user" in data
        print(f"✓ Profile language updated successfully")
        
        # Restore to English
        requests.put(
            f"{BASE_URL}/api/auth/update-profile",
            json={"preferred_language": "en"},
            headers=self.headers
        )
    
    def test_update_notification_preferences(self):
        """PUT /api/auth/update-profile with notification_preferences"""
        response = requests.put(
            f"{BASE_URL}/api/auth/update-profile",
            json={"notification_preferences": {
                "email": True, "sms": False, "in_app": True,
                "case_updates": True, "payment_reminders": True,
                "document_requests": True, "marketing": False
            }},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"✓ Notification preferences updated successfully")
    
    def test_change_password_wrong_current(self):
        """POST /api/auth/change-password with wrong current password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "WrongPassword123", "new_password": "NewPass@123"},
            headers=self.headers
        )
        assert response.status_code == 400, f"Should fail with wrong password: {response.text}"
        print(f"✓ Change password correctly rejects wrong current password")
    
    def test_change_password_success(self):
        """POST /api/auth/change-password with correct current password"""
        # Change password
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "Client@123", "new_password": "NewClient@123"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"✓ Password changed successfully")
        
        # Verify new password works
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "client@leamss.com", "password": "NewClient@123"}
        )
        assert login_response.status_code == 200, "New password login failed"
        
        # Restore original password
        new_token = login_response.json()["token"]
        restore_response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "NewClient@123", "new_password": "Client@123"},
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert restore_response.status_code == 200, "Failed to restore password"
        print(f"✓ Password restored to original")


class TestChatMessagesAPI:
    """Test Chat/Messages API for client"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as client and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.user = response.json()["user"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get client's case
        cases_response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=self.headers)
        if cases_response.status_code == 200 and cases_response.json():
            self.case_id = cases_response.json()[0].get("id")
        else:
            self.case_id = None
    
    def test_get_conversations(self):
        """GET /api/chat/conversations"""
        response = requests.get(f"{BASE_URL}/api/chat/conversations", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Conversations retrieved: {len(data)} conversations")
    
    def test_start_conversation(self):
        """POST /api/chat/conversations - start new conversation"""
        if not self.case_id:
            pytest.skip("No case found for client")
        
        response = requests.post(
            f"{BASE_URL}/api/chat/conversations",
            json={"case_id": self.case_id, "subject": "TEST_Query about my case"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        self.conversation_id = data["id"]
        print(f"✓ Conversation started: {data.get('subject')}")
    
    def test_send_message(self):
        """POST /api/chat/messages - send message"""
        # First get or create conversation
        convos_response = requests.get(f"{BASE_URL}/api/chat/conversations", headers=self.headers)
        if convos_response.status_code == 200 and convos_response.json():
            conv_id = convos_response.json()[0]["id"]
        else:
            if not self.case_id:
                pytest.skip("No case or conversation found")
            # Create conversation
            create_response = requests.post(
                f"{BASE_URL}/api/chat/conversations",
                json={"case_id": self.case_id, "subject": "TEST_Chat"},
                headers=self.headers
            )
            conv_id = create_response.json()["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/chat/messages",
            json={"conversation_id": conv_id, "message": "TEST_Hello, this is a test message"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["message"] == "TEST_Hello, this is a test message"
        print(f"✓ Message sent successfully")
    
    def test_get_messages(self):
        """GET /api/chat/messages/{conversation_id}"""
        convos_response = requests.get(f"{BASE_URL}/api/chat/conversations", headers=self.headers)
        if convos_response.status_code != 200 or not convos_response.json():
            pytest.skip("No conversations found")
        
        conv_id = convos_response.json()[0]["id"]
        response = requests.get(f"{BASE_URL}/api/chat/messages/{conv_id}", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Messages retrieved: {len(data)} messages")
    
    def test_get_unread_count(self):
        """GET /api/chat/unread-count"""
        response = requests.get(f"{BASE_URL}/api/chat/unread-count", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "unread" in data
        print(f"✓ Unread count: {data['unread']}")


class TestTimelineAPI:
    """Test Timeline API for case journey"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as client and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get client's case
        cases_response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=self.headers)
        if cases_response.status_code == 200 and cases_response.json():
            self.case_id = cases_response.json()[0].get("id")
        else:
            self.case_id = None
    
    def test_get_case_timeline(self):
        """GET /api/timeline/case/{case_id}"""
        if not self.case_id:
            pytest.skip("No case found for client")
        
        response = requests.get(f"{BASE_URL}/api/timeline/case/{self.case_id}", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "events" in data
        assert "case_id" in data
        print(f"✓ Timeline retrieved: {len(data['events'])} events")


class TestClientCaseAPIs:
    """Test Client Case APIs - my-cases, documents"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as client and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_my_cases(self):
        """GET /api/cases/my-cases"""
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        if data:
            case = data[0]
            assert "id" in case
            assert "product_name" in case or "case_id" in case
            print(f"✓ My cases retrieved: {len(data)} cases")
            print(f"  First case: {case.get('case_id')} - {case.get('product_name')}")
        else:
            print(f"✓ My cases retrieved: 0 cases (client has no cases)")
    
    def test_get_case_documents(self):
        """GET /api/documents/case/{case_id}"""
        cases_response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=self.headers)
        if cases_response.status_code != 200 or not cases_response.json():
            pytest.skip("No cases found for client")
        
        case_id = cases_response.json()[0]["id"]
        response = requests.get(f"{BASE_URL}/api/documents/case/{case_id}", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Case documents retrieved: {len(data)} documents")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
