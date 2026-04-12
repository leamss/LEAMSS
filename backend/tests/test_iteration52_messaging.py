"""
Iteration 52: Client Messaging Bug Fixes Tests
- BUG FIX: Client can send messages via /api/cm-tools/client-messages/send
- BUG FIX: Chat history visible for both CM and Client
- Two-way sync: CM sends → Client sees, Client sends → CM sees
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestClientMessagingBugFixes:
    """Test client messaging bug fixes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.client_email = "client@leamss.com"
        self.client_password = "Client@123"
        self.cm_email = "manager@leamss.com"
        self.cm_password = "Manager@123"
        self.session = requests.Session()
    
    def get_token(self, email, password):
        """Get auth token for user"""
        res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if res.status_code == 200:
            return res.json().get("token")
        return None
    
    # ==================== CLIENT MESSAGING TESTS ====================
    
    def test_client_login(self):
        """Test client can login"""
        token = self.get_token(self.client_email, self.client_password)
        assert token is not None, "Client login failed"
        print(f"✓ Client login successful")
    
    def test_cm_login(self):
        """Test case manager can login"""
        token = self.get_token(self.cm_email, self.cm_password)
        assert token is not None, "CM login failed"
        print(f"✓ CM login successful")
    
    def test_client_get_conversations(self):
        """Test GET /api/cm-tools/client-messages returns conversations for client"""
        token = self.get_token(self.client_email, self.client_password)
        assert token, "Client login failed"
        
        res = self.session.get(
            f"{BASE_URL}/api/cm-tools/client-messages",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert isinstance(data, list), "Expected list of conversations"
        print(f"✓ Client has {len(data)} conversations")
        
        # Check conversation structure
        if len(data) > 0:
            conv = data[0]
            assert "case_id" in conv, "Missing case_id"
            assert "case_display_id" in conv, "Missing case_display_id"
            assert "case_manager_name" in conv, "Missing case_manager_name"
            print(f"✓ First conversation: {conv.get('case_display_id')} with CM: {conv.get('case_manager_name')}")
        
        return data
    
    def test_client_get_case_messages(self):
        """Test GET /api/cm-tools/communications/{case_id} allows client access"""
        token = self.get_token(self.client_email, self.client_password)
        assert token, "Client login failed"
        
        # First get conversations to find a case_id
        convos = self.session.get(
            f"{BASE_URL}/api/cm-tools/client-messages",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
        
        if len(convos) == 0:
            pytest.skip("No conversations found for client")
        
        case_id = convos[0]["case_id"]
        
        # Now get messages for that case
        res = self.session.get(
            f"{BASE_URL}/api/cm-tools/communications/{case_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "messages" in data, "Missing messages array"
        assert "client_name" in data, "Missing client_name"
        print(f"✓ Client can access messages for case {case_id}, found {len(data['messages'])} messages")
        
        return data
    
    def test_client_send_message(self):
        """BUG FIX TEST: Client can send message via POST /api/cm-tools/client-messages/send"""
        token = self.get_token(self.client_email, self.client_password)
        assert token, "Client login failed"
        
        # Get a case_id
        convos = self.session.get(
            f"{BASE_URL}/api/cm-tools/client-messages",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
        
        if len(convos) == 0:
            pytest.skip("No conversations found for client")
        
        case_id = convos[0]["case_id"]
        test_message = f"TEST_Client message at iteration 52"
        
        # Send message
        res = self.session.post(
            f"{BASE_URL}/api/cm-tools/client-messages/send",
            json={
                "case_id": case_id,
                "message": test_message
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "message" in data, "Missing message field in response"
        assert data.get("message") == "Message sent", f"Unexpected response: {data}"
        assert "data" in data, "Missing data field in response"
        
        msg_data = data["data"]
        assert msg_data.get("message") == test_message, "Message content mismatch"
        assert msg_data.get("sender_role") == "client", "Sender role should be client"
        print(f"✓ Client successfully sent message: '{test_message[:50]}...'")
        
        return case_id, msg_data
    
    def test_client_message_appears_in_history(self):
        """BUG FIX TEST: After sending, message appears in chat history"""
        token = self.get_token(self.client_email, self.client_password)
        assert token, "Client login failed"
        
        # Get a case_id
        convos = self.session.get(
            f"{BASE_URL}/api/cm-tools/client-messages",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
        
        if len(convos) == 0:
            pytest.skip("No conversations found for client")
        
        case_id = convos[0]["case_id"]
        
        # Send a unique message
        unique_msg = f"TEST_History check {os.urandom(4).hex()}"
        self.session.post(
            f"{BASE_URL}/api/cm-tools/client-messages/send",
            json={"case_id": case_id, "message": unique_msg},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Now fetch messages and verify it appears
        res = self.session.get(
            f"{BASE_URL}/api/cm-tools/communications/{case_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        
        messages = res.json().get("messages", [])
        found = any(m.get("message") == unique_msg for m in messages)
        assert found, f"Sent message not found in history. Messages: {[m.get('message')[:30] for m in messages[-5:]]}"
        print(f"✓ Sent message appears in chat history")
    
    # ==================== CM MESSAGING TESTS ====================
    
    def test_cm_get_communications(self):
        """Test CM can get communications for a case"""
        token = self.get_token(self.cm_email, self.cm_password)
        assert token, "CM login failed"
        
        # Get CM's cases first
        cases_res = self.session.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert cases_res.status_code == 200
        cases = cases_res.json()
        
        if len(cases) == 0:
            pytest.skip("No cases found for CM")
        
        case_id = cases[0]["id"]
        
        # Get communications
        res = self.session.get(
            f"{BASE_URL}/api/cm-tools/communications/{case_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        
        data = res.json()
        assert "messages" in data
        print(f"✓ CM can access communications for case {case_id}, found {len(data['messages'])} messages")
        
        return case_id, data
    
    def test_cm_send_message(self):
        """Test CM can send message to client"""
        token = self.get_token(self.cm_email, self.cm_password)
        assert token, "CM login failed"
        
        # Get CM's cases
        cases_res = self.session.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        cases = cases_res.json()
        
        if len(cases) == 0:
            pytest.skip("No cases found for CM")
        
        case = cases[0]
        test_message = f"TEST_CM message at iteration 52"
        
        # Send message
        res = self.session.post(
            f"{BASE_URL}/api/cm-tools/communications/send",
            json={
                "case_id": case["id"],
                "client_id": case.get("client_id", ""),
                "message": test_message,
                "message_type": "text"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert data.get("message") == "Message sent"
        print(f"✓ CM successfully sent message to client")
        
        return case["id"]
    
    def test_cm_message_appears_in_history(self):
        """Test CM message appears in chat history after sending"""
        token = self.get_token(self.cm_email, self.cm_password)
        assert token, "CM login failed"
        
        # Get CM's cases
        cases_res = self.session.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        cases = cases_res.json()
        
        if len(cases) == 0:
            pytest.skip("No cases found for CM")
        
        case = cases[0]
        unique_msg = f"TEST_CM History {os.urandom(4).hex()}"
        
        # Send message
        self.session.post(
            f"{BASE_URL}/api/cm-tools/communications/send",
            json={
                "case_id": case["id"],
                "client_id": case.get("client_id", ""),
                "message": unique_msg,
                "message_type": "text"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Fetch and verify
        res = self.session.get(
            f"{BASE_URL}/api/cm-tools/communications/{case['id']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        messages = res.json().get("messages", [])
        found = any(m.get("message") == unique_msg for m in messages)
        assert found, "CM message not found in history"
        print(f"✓ CM message appears in chat history")
    
    # ==================== TWO-WAY SYNC TESTS ====================
    
    def test_two_way_sync_cm_to_client(self):
        """Test: CM sends message → Client can see it"""
        cm_token = self.get_token(self.cm_email, self.cm_password)
        client_token = self.get_token(self.client_email, self.client_password)
        assert cm_token and client_token, "Login failed"
        
        # Get client's case
        convos = self.session.get(
            f"{BASE_URL}/api/cm-tools/client-messages",
            headers={"Authorization": f"Bearer {client_token}"}
        ).json()
        
        if len(convos) == 0:
            pytest.skip("No conversations for client")
        
        case_id = convos[0]["case_id"]
        
        # Get case details for client_id
        cases_res = self.session.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_res.json()
        case = next((c for c in cases if c["id"] == case_id), None)
        
        if not case:
            pytest.skip("Case not found in CM's cases")
        
        # CM sends message
        sync_msg = f"TEST_Sync CM→Client {os.urandom(4).hex()}"
        self.session.post(
            f"{BASE_URL}/api/cm-tools/communications/send",
            json={
                "case_id": case_id,
                "client_id": case.get("client_id", ""),
                "message": sync_msg,
                "message_type": "text"
            },
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        
        # Client fetches messages
        res = self.session.get(
            f"{BASE_URL}/api/cm-tools/communications/{case_id}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        messages = res.json().get("messages", [])
        found = any(m.get("message") == sync_msg for m in messages)
        assert found, "CM message not visible to client"
        print(f"✓ Two-way sync: CM → Client works")
    
    def test_two_way_sync_client_to_cm(self):
        """Test: Client sends message → CM can see it"""
        cm_token = self.get_token(self.cm_email, self.cm_password)
        client_token = self.get_token(self.client_email, self.client_password)
        assert cm_token and client_token, "Login failed"
        
        # Get client's case
        convos = self.session.get(
            f"{BASE_URL}/api/cm-tools/client-messages",
            headers={"Authorization": f"Bearer {client_token}"}
        ).json()
        
        if len(convos) == 0:
            pytest.skip("No conversations for client")
        
        case_id = convos[0]["case_id"]
        
        # Client sends message
        sync_msg = f"TEST_Sync Client→CM {os.urandom(4).hex()}"
        self.session.post(
            f"{BASE_URL}/api/cm-tools/client-messages/send",
            json={"case_id": case_id, "message": sync_msg},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        
        # CM fetches messages
        res = self.session.get(
            f"{BASE_URL}/api/cm-tools/communications/{case_id}",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        messages = res.json().get("messages", [])
        found = any(m.get("message") == sync_msg for m in messages)
        assert found, "Client message not visible to CM"
        print(f"✓ Two-way sync: Client → CM works")
    
    # ==================== EDGE CASES ====================
    
    def test_client_cannot_send_empty_message(self):
        """Test client cannot send empty message"""
        token = self.get_token(self.client_email, self.client_password)
        assert token, "Client login failed"
        
        convos = self.session.get(
            f"{BASE_URL}/api/cm-tools/client-messages",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
        
        if len(convos) == 0:
            pytest.skip("No conversations")
        
        res = self.session.post(
            f"{BASE_URL}/api/cm-tools/client-messages/send",
            json={"case_id": convos[0]["case_id"], "message": "   "},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 400, f"Expected 400 for empty message, got {res.status_code}"
        print(f"✓ Empty message rejected with 400")
    
    def test_client_cannot_access_other_case(self):
        """Test client cannot access messages for a case they don't own"""
        token = self.get_token(self.client_email, self.client_password)
        assert token, "Client login failed"
        
        # Try to access a non-existent case
        res = self.session.get(
            f"{BASE_URL}/api/cm-tools/communications/fake-case-id-12345",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code in [403, 404], f"Expected 403/404, got {res.status_code}"
        print(f"✓ Client cannot access other cases (got {res.status_code})")
    
    def test_unread_count_endpoint(self):
        """Test unread count endpoint works"""
        token = self.get_token(self.cm_email, self.cm_password)
        assert token, "CM login failed"
        
        res = self.session.get(
            f"{BASE_URL}/api/cm-tools/communications/unread-count",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "count" in data
        print(f"✓ Unread count endpoint works, count: {data['count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
