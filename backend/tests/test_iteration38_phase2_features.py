"""
Iteration 38 - Phase 2 Features Testing
Tests for: Chat API, Workload Dashboard API, Core APIs
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


class TestHealthAndCore:
    """Core API health checks"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy"
        print("PASS: Health endpoint working")
    
    def test_dashboard_stats(self):
        """Test /api/stats/dashboard returns data"""
        # Login as admin
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        token = login_res.json().get("token")
        
        response = requests.get(
            f"{BASE_URL}/api/stats/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        assert "total_cases" in data or "cases" in data or isinstance(data, dict)
        print("PASS: Dashboard stats endpoint working")


class TestAuthentication:
    """Test login for all 4 roles"""
    
    def test_admin_login(self):
        """Admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "admin"
        print("PASS: Admin login successful")
    
    def test_case_manager_login(self):
        """Case Manager login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "case_manager"
        print("PASS: Case Manager login successful")
    
    def test_partner_login(self):
        """Partner login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "partner"
        print("PASS: Partner login successful")
    
    def test_client_login(self):
        """Client login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "client"
        print("PASS: Client login successful")


class TestWorkloadDashboard:
    """Test Workload Dashboard API for Case Manager"""
    
    @pytest.fixture
    def manager_token(self):
        """Get case manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        return response.json().get("token")
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        return response.json().get("token")
    
    def test_workload_summary_case_manager(self, manager_token):
        """GET /api/cases/workload/summary returns workload data for case manager"""
        response = requests.get(
            f"{BASE_URL}/api/cases/workload/summary",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200, f"Workload summary failed: {response.text}"
        data = response.json()
        
        # Verify expected fields
        assert "active_cases" in data, "Missing active_cases field"
        assert "pending_reviews" in data, "Missing pending_reviews field"
        assert "expiring_documents" in data, "Missing expiring_documents field"
        assert "pending_additional_docs" in data, "Missing pending_additional_docs field"
        assert "in_progress_steps" in data, "Missing in_progress_steps field"
        assert "urgent_tasks" in data, "Missing urgent_tasks field"
        assert "total_urgent" in data, "Missing total_urgent field"
        assert "case_distribution" in data, "Missing case_distribution field"
        
        # Verify data types
        assert isinstance(data["active_cases"], int)
        assert isinstance(data["pending_reviews"], int)
        assert isinstance(data["urgent_tasks"], list)
        assert isinstance(data["case_distribution"], dict)
        
        print(f"PASS: Workload summary - Active cases: {data['active_cases']}, Pending reviews: {data['pending_reviews']}")
    
    def test_workload_summary_admin(self, admin_token):
        """GET /api/cases/workload/summary works for admin too"""
        response = requests.get(
            f"{BASE_URL}/api/cases/workload/summary",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Admin workload summary failed: {response.text}"
        data = response.json()
        assert "active_cases" in data
        print("PASS: Admin can access workload summary")
    
    def test_workload_summary_client_forbidden(self):
        """Client should not access workload summary"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        token = login_res.json().get("token")
        
        response = requests.get(
            f"{BASE_URL}/api/cases/workload/summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
        print("PASS: Client correctly denied access to workload summary")


class TestChatAPI:
    """Test Chat API endpoints"""
    
    @pytest.fixture
    def client_token(self):
        """Get client auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200
        return response.json().get("token")
    
    @pytest.fixture
    def manager_token(self):
        """Get case manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        return response.json().get("token")
    
    @pytest.fixture
    def client_case_id(self, client_token):
        """Get a case ID for the client"""
        response = requests.get(
            f"{BASE_URL}/api/cases/my-cases",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        cases = response.json()
        if cases:
            return cases[0]["id"]
        pytest.skip("No cases found for client")
    
    def test_get_conversations_client(self, client_token):
        """GET /api/chat/conversations returns list for client"""
        response = requests.get(
            f"{BASE_URL}/api/chat/conversations",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Get conversations failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of conversations"
        print(f"PASS: Client can get conversations (count: {len(data)})")
    
    def test_get_conversations_manager(self, manager_token):
        """GET /api/chat/conversations returns list for case manager"""
        response = requests.get(
            f"{BASE_URL}/api/chat/conversations",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200, f"Get conversations failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of conversations"
        print(f"PASS: Case Manager can get conversations (count: {len(data)})")
    
    def test_create_conversation(self, client_token, client_case_id):
        """POST /api/chat/conversations creates or returns existing conversation"""
        response = requests.post(
            f"{BASE_URL}/api/chat/conversations",
            json={"case_id": client_case_id, "subject": "Test Chat"},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Create conversation failed: {response.text}"
        data = response.json()
        
        # Verify conversation structure
        assert "id" in data, "Missing conversation id"
        assert "case_id" in data, "Missing case_id"
        assert data["case_id"] == client_case_id
        
        print(f"PASS: Conversation created/retrieved - ID: {data['id']}")
        return data["id"]
    
    def test_send_message_client(self, client_token, client_case_id):
        """POST /api/chat/messages sends a message"""
        # First create/get conversation
        convo_res = requests.post(
            f"{BASE_URL}/api/chat/conversations",
            json={"case_id": client_case_id},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert convo_res.status_code == 200
        convo_id = convo_res.json()["id"]
        
        # Send message
        test_message = f"Test message from client - {uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/chat/messages",
            json={"conversation_id": convo_id, "message": test_message},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Send message failed: {response.text}"
        data = response.json()
        
        # Verify message structure
        assert "id" in data, "Missing message id"
        assert "message" in data, "Missing message content"
        assert data["message"] == test_message
        assert "sender_id" in data
        assert "created_at" in data
        
        print(f"PASS: Client sent message - ID: {data['id']}")
        return convo_id
    
    def test_get_messages(self, client_token, client_case_id):
        """GET /api/chat/messages/{conversation_id} returns messages"""
        # First create/get conversation
        convo_res = requests.post(
            f"{BASE_URL}/api/chat/conversations",
            json={"case_id": client_case_id},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert convo_res.status_code == 200
        convo_id = convo_res.json()["id"]
        
        # Get messages
        response = requests.get(
            f"{BASE_URL}/api/chat/messages/{convo_id}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Get messages failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of messages"
        
        print(f"PASS: Retrieved messages (count: {len(data)})")
    
    def test_get_unread_count_client(self, client_token):
        """GET /api/chat/unread-count returns unread count"""
        response = requests.get(
            f"{BASE_URL}/api/chat/unread-count",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Get unread count failed: {response.text}"
        data = response.json()
        assert "unread" in data, "Missing unread field"
        assert isinstance(data["unread"], int)
        
        print(f"PASS: Client unread count: {data['unread']}")
    
    def test_get_unread_count_manager(self, manager_token):
        """GET /api/chat/unread-count returns unread count for manager"""
        response = requests.get(
            f"{BASE_URL}/api/chat/unread-count",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200, f"Get unread count failed: {response.text}"
        data = response.json()
        assert "unread" in data
        
        print(f"PASS: Manager unread count: {data['unread']}")
    
    def test_cross_role_chat(self, client_token, manager_token, client_case_id):
        """Test that client can send message and manager can see it"""
        # Client creates/gets conversation
        convo_res = requests.post(
            f"{BASE_URL}/api/chat/conversations",
            json={"case_id": client_case_id},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert convo_res.status_code == 200
        convo_id = convo_res.json()["id"]
        
        # Client sends message
        test_msg = f"Cross-role test - {uuid.uuid4().hex[:8]}"
        send_res = requests.post(
            f"{BASE_URL}/api/chat/messages",
            json={"conversation_id": convo_id, "message": test_msg},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert send_res.status_code == 200
        
        # Manager retrieves messages
        msg_res = requests.get(
            f"{BASE_URL}/api/chat/messages/{convo_id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert msg_res.status_code == 200, f"Manager get messages failed: {msg_res.text}"
        messages = msg_res.json()
        
        # Verify the message is visible to manager
        found = any(m.get("message") == test_msg for m in messages)
        assert found, "Manager should see client's message"
        
        print("PASS: Cross-role chat working - Client message visible to Manager")
    
    def test_manager_reply_to_client(self, client_token, manager_token, client_case_id):
        """Test that manager can reply to client's conversation"""
        # Client creates/gets conversation
        convo_res = requests.post(
            f"{BASE_URL}/api/chat/conversations",
            json={"case_id": client_case_id},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert convo_res.status_code == 200
        convo_id = convo_res.json()["id"]
        
        # Manager sends reply
        reply_msg = f"Manager reply - {uuid.uuid4().hex[:8]}"
        reply_res = requests.post(
            f"{BASE_URL}/api/chat/messages",
            json={"conversation_id": convo_id, "message": reply_msg},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert reply_res.status_code == 200, f"Manager reply failed: {reply_res.text}"
        
        # Client retrieves messages and sees manager's reply
        msg_res = requests.get(
            f"{BASE_URL}/api/chat/messages/{convo_id}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert msg_res.status_code == 200
        messages = msg_res.json()
        
        found = any(m.get("message") == reply_msg for m in messages)
        assert found, "Client should see manager's reply"
        
        print("PASS: Manager can reply to client conversation")


class TestCasesAPI:
    """Test Cases API endpoints"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        return response.json().get("token")
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json().get("token")
    
    def test_get_my_cases_client(self, client_token):
        """Client can get their cases"""
        response = requests.get(
            f"{BASE_URL}/api/cases/my-cases",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Get my cases failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        if data:
            case = data[0]
            assert "id" in case
            assert "case_id" in case
            assert "steps" in case
        print(f"PASS: Client has {len(data)} case(s)")
    
    def test_get_my_cases_manager(self, manager_token):
        """Case Manager can get their assigned cases"""
        response = requests.get(
            f"{BASE_URL}/api/cases/my-cases",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200, f"Get my cases failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Manager has {len(data)} assigned case(s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
