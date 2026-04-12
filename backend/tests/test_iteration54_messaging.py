"""
Iteration 54: CM Communication Hub & Client Messages Testing
Tests the messaging fix:
1. CM Communication Hub shows clients with names, case IDs, products
2. Chat history visible with sent/received messages
3. Client Messages shows same messages as CM sees
4. Two-way sync between CM and Client
5. my-cases-summary returns client_name and client_email from users collection
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CM_EMAIL = "manager@leamss.com"
CM_PASSWORD = "Manager@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASSWORD = "Client@123"


class TestMyCasesSummary:
    """Test /api/cm-tools/my-cases-summary returns client names from users collection"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login as CM
        resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CM_EMAIL,
            "password": CM_PASSWORD
        })
        assert resp.status_code == 200, f"CM login failed: {resp.text}"
        self.cm_token = resp.json()["token"]
        self.cm_headers = {"Authorization": f"Bearer {self.cm_token}"}
    
    def test_my_cases_summary_returns_cases(self):
        """Test that my-cases-summary returns cases"""
        resp = self.session.get(f"{BASE_URL}/api/cm-tools/my-cases-summary", headers=self.cm_headers)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        cases = resp.json()
        assert isinstance(cases, list), "Expected list of cases"
        assert len(cases) > 0, "Expected at least one case"
        print(f"Found {len(cases)} cases")
    
    def test_my_cases_summary_has_client_name(self):
        """Test that each case has client_name populated from users collection"""
        resp = self.session.get(f"{BASE_URL}/api/cm-tools/my-cases-summary", headers=self.cm_headers)
        assert resp.status_code == 200
        cases = resp.json()
        
        # Check that at least some cases have client_name
        cases_with_names = [c for c in cases if c.get("client_name")]
        assert len(cases_with_names) > 0, "No cases have client_name populated"
        
        # Print sample
        for c in cases[:3]:
            print(f"Case: {c.get('case_id')} - Client: {c.get('client_name')} - Email: {c.get('client_email')}")
    
    def test_my_cases_summary_has_required_fields(self):
        """Test that each case has all required fields"""
        resp = self.session.get(f"{BASE_URL}/api/cm-tools/my-cases-summary", headers=self.cm_headers)
        assert resp.status_code == 200
        cases = resp.json()
        
        required_fields = ["id", "case_id", "client_name", "client_email", "client_id", "product_name", "status"]
        for case in cases[:5]:
            for field in required_fields:
                assert field in case, f"Missing field: {field} in case {case.get('case_id')}"
            print(f"Case {case.get('case_id')}: client_name={case.get('client_name')}, product={case.get('product_name')}")


class TestCMCommunicationHub:
    """Test CM Communication Hub functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login as CM
        resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CM_EMAIL,
            "password": CM_PASSWORD
        })
        assert resp.status_code == 200, f"CM login failed: {resp.text}"
        self.cm_token = resp.json()["token"]
        self.cm_headers = {"Authorization": f"Bearer {self.cm_token}"}
        self.cm_user = resp.json()["user"]
    
    def test_get_communications_for_case(self):
        """Test getting communications for a specific case"""
        # First get cases
        cases_resp = self.session.get(f"{BASE_URL}/api/cm-tools/my-cases-summary", headers=self.cm_headers)
        assert cases_resp.status_code == 200
        cases = cases_resp.json()
        assert len(cases) > 0, "No cases found"
        
        # Get communications for first case
        case_id = cases[0]["id"]
        comm_resp = self.session.get(f"{BASE_URL}/api/cm-tools/communications/{case_id}", headers=self.cm_headers)
        assert comm_resp.status_code == 200, f"Failed to get communications: {comm_resp.text}"
        
        data = comm_resp.json()
        assert "messages" in data, "Missing messages field"
        assert "client_name" in data, "Missing client_name field"
        assert "client_email" in data, "Missing client_email field"
        print(f"Case {data.get('case_id')}: {len(data['messages'])} messages, client: {data.get('client_name')}")
    
    def test_cm_can_send_message(self):
        """Test CM can send a message to client"""
        # Get first case
        cases_resp = self.session.get(f"{BASE_URL}/api/cm-tools/my-cases-summary", headers=self.cm_headers)
        cases = cases_resp.json()
        case = cases[0]
        
        # Send message
        test_msg = f"Test message from CM at {os.urandom(4).hex()}"
        send_resp = self.session.post(f"{BASE_URL}/api/cm-tools/communications/send", 
            headers=self.cm_headers,
            json={
                "case_id": case["id"],
                "client_id": case["client_id"],
                "message": test_msg,
                "message_type": "text"
            }
        )
        assert send_resp.status_code == 200, f"Failed to send: {send_resp.text}"
        
        # Verify message appears in communications
        comm_resp = self.session.get(f"{BASE_URL}/api/cm-tools/communications/{case['id']}", headers=self.cm_headers)
        messages = comm_resp.json()["messages"]
        found = any(m["message"] == test_msg for m in messages)
        assert found, "Sent message not found in communications"
        print(f"CM sent message successfully: {test_msg[:50]}")


class TestClientMessages:
    """Test Client Messages functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login as Client
        resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert resp.status_code == 200, f"Client login failed: {resp.text}"
        self.client_token = resp.json()["token"]
        self.client_headers = {"Authorization": f"Bearer {self.client_token}"}
        self.client_user = resp.json()["user"]
    
    def test_get_client_messages(self):
        """Test client can get their conversations"""
        resp = self.session.get(f"{BASE_URL}/api/cm-tools/client-messages", headers=self.client_headers)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        conversations = resp.json()
        assert isinstance(conversations, list), "Expected list"
        print(f"Client has {len(conversations)} conversations")
        
        for conv in conversations[:3]:
            print(f"  - {conv.get('case_display_id')}: CM={conv.get('case_manager_name')}, last_msg={conv.get('last_message')[:30] if conv.get('last_message') else 'None'}")
    
    def test_client_can_view_messages(self):
        """Test client can view messages for their case"""
        # Get conversations
        convos_resp = self.session.get(f"{BASE_URL}/api/cm-tools/client-messages", headers=self.client_headers)
        conversations = convos_resp.json()
        
        if len(conversations) == 0:
            pytest.skip("No conversations for client")
        
        # Get messages for first conversation
        case_id = conversations[0]["case_id"]
        msgs_resp = self.session.get(f"{BASE_URL}/api/cm-tools/communications/{case_id}", headers=self.client_headers)
        assert msgs_resp.status_code == 200, f"Failed: {msgs_resp.text}"
        
        data = msgs_resp.json()
        print(f"Case {data.get('case_id')}: {len(data['messages'])} messages")
        for m in data["messages"][-3:]:
            print(f"  [{m.get('sender_role')}] {m.get('sender_name')}: {m.get('message')[:50]}")
    
    def test_client_can_send_message(self):
        """Test client can send a message"""
        # Get conversations
        convos_resp = self.session.get(f"{BASE_URL}/api/cm-tools/client-messages", headers=self.client_headers)
        conversations = convos_resp.json()
        
        if len(conversations) == 0:
            pytest.skip("No conversations for client")
        
        case_id = conversations[0]["case_id"]
        test_msg = f"Test message from client at {os.urandom(4).hex()}"
        
        send_resp = self.session.post(f"{BASE_URL}/api/cm-tools/client-messages/send",
            headers=self.client_headers,
            json={
                "case_id": case_id,
                "message": test_msg
            }
        )
        assert send_resp.status_code == 200, f"Failed to send: {send_resp.text}"
        
        # Verify message appears
        msgs_resp = self.session.get(f"{BASE_URL}/api/cm-tools/communications/{case_id}", headers=self.client_headers)
        messages = msgs_resp.json()["messages"]
        found = any(m["message"] == test_msg for m in messages)
        assert found, "Sent message not found"
        print(f"Client sent message successfully: {test_msg[:50]}")


class TestTwoWaySync:
    """Test that CM and Client see the same messages (unified chat)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        
        # Login as CM
        cm_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CM_EMAIL,
            "password": CM_PASSWORD
        })
        assert cm_resp.status_code == 200
        self.cm_token = cm_resp.json()["token"]
        self.cm_headers = {"Authorization": f"Bearer {self.cm_token}"}
        
        # Login as Client
        client_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert client_resp.status_code == 200
        self.client_token = client_resp.json()["token"]
        self.client_headers = {"Authorization": f"Bearer {self.client_token}"}
        self.client_user = client_resp.json()["user"]
    
    def test_cm_and_client_see_same_messages(self):
        """Test that CM and Client see the same messages for a case"""
        # Get client's case
        client_convos = self.session.get(f"{BASE_URL}/api/cm-tools/client-messages", headers=self.client_headers).json()
        if len(client_convos) == 0:
            pytest.skip("No conversations for client")
        
        case_id = client_convos[0]["case_id"]
        
        # Get messages as client
        client_msgs = self.session.get(f"{BASE_URL}/api/cm-tools/communications/{case_id}", headers=self.client_headers).json()
        
        # Get messages as CM
        cm_msgs = self.session.get(f"{BASE_URL}/api/cm-tools/communications/{case_id}", headers=self.cm_headers).json()
        
        # Compare message counts
        client_count = len(client_msgs["messages"])
        cm_count = len(cm_msgs["messages"])
        
        print(f"Case {case_id}: Client sees {client_count} messages, CM sees {cm_count} messages")
        assert client_count == cm_count, f"Message count mismatch: client={client_count}, cm={cm_count}"
        
        # Compare message IDs
        client_ids = set(m["id"] for m in client_msgs["messages"])
        cm_ids = set(m["id"] for m in cm_msgs["messages"])
        assert client_ids == cm_ids, "Message IDs don't match between client and CM views"
        print("SUCCESS: CM and Client see the same messages")
    
    def test_cm_message_visible_to_client(self):
        """Test that a message sent by CM is visible to client"""
        # Get client's case
        client_convos = self.session.get(f"{BASE_URL}/api/cm-tools/client-messages", headers=self.client_headers).json()
        if len(client_convos) == 0:
            pytest.skip("No conversations for client")
        
        case_id = client_convos[0]["case_id"]
        
        # Get CM's cases to find client_id
        cm_cases = self.session.get(f"{BASE_URL}/api/cm-tools/my-cases-summary", headers=self.cm_headers).json()
        case_info = next((c for c in cm_cases if c["id"] == case_id), None)
        if not case_info:
            pytest.skip("Case not found in CM's cases")
        
        # CM sends message
        unique_msg = f"CM_SYNC_TEST_{os.urandom(4).hex()}"
        send_resp = self.session.post(f"{BASE_URL}/api/cm-tools/communications/send",
            headers=self.cm_headers,
            json={
                "case_id": case_id,
                "client_id": case_info["client_id"],
                "message": unique_msg,
                "message_type": "text"
            }
        )
        assert send_resp.status_code == 200
        
        # Client checks messages
        client_msgs = self.session.get(f"{BASE_URL}/api/cm-tools/communications/{case_id}", headers=self.client_headers).json()
        found = any(m["message"] == unique_msg for m in client_msgs["messages"])
        assert found, "CM's message not visible to client"
        print(f"SUCCESS: CM message '{unique_msg[:30]}' visible to client")
    
    def test_client_message_visible_to_cm(self):
        """Test that a message sent by client is visible to CM"""
        # Get client's case
        client_convos = self.session.get(f"{BASE_URL}/api/cm-tools/client-messages", headers=self.client_headers).json()
        if len(client_convos) == 0:
            pytest.skip("No conversations for client")
        
        case_id = client_convos[0]["case_id"]
        
        # Client sends message
        unique_msg = f"CLIENT_SYNC_TEST_{os.urandom(4).hex()}"
        send_resp = self.session.post(f"{BASE_URL}/api/cm-tools/client-messages/send",
            headers=self.client_headers,
            json={
                "case_id": case_id,
                "message": unique_msg
            }
        )
        assert send_resp.status_code == 200
        
        # CM checks messages
        cm_msgs = self.session.get(f"{BASE_URL}/api/cm-tools/communications/{case_id}", headers=self.cm_headers).json()
        found = any(m["message"] == unique_msg for m in cm_msgs["messages"])
        assert found, "Client's message not visible to CM"
        print(f"SUCCESS: Client message '{unique_msg[:30]}' visible to CM")


class TestUnreadCount:
    """Test unread message count functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login as CM
        resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CM_EMAIL,
            "password": CM_PASSWORD
        })
        assert resp.status_code == 200
        self.cm_token = resp.json()["token"]
        self.cm_headers = {"Authorization": f"Bearer {self.cm_token}"}
    
    def test_get_unread_count(self):
        """Test getting unread message count"""
        resp = self.session.get(f"{BASE_URL}/api/cm-tools/communications/unread-count", headers=self.cm_headers)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "count" in data, "Missing count field"
        print(f"CM has {data['count']} unread messages")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
