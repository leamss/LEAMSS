"""
Iteration 29 - AI Features, Payment Reminders, and Admin Receipt Download Tests
Tests for:
- Payment Reminders: GET /api/reminders/pending-payments, POST /api/reminders/send/{sale_id}, POST /api/reminders/send-bulk
- Admin Receipt Download: GET /api/reports/export/sale-receipt/{sale_id}
- AI Chat: POST /api/ai-intel/chat, GET /api/ai-intel/chat/history
- Document Check: GET /api/ai-intel/case-document-check/{case_id}
- Document Validation: POST /api/ai-intel/validate-document/{document_id}
- OCR Extract: POST /api/ai-intel/extract-data/{document_id}
- Auto-Fill: POST /api/ai-intel/auto-fill/{case_id}
- Approval Prediction: GET /api/ai-intel/predict-approval/{case_id}
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication helpers"""
    
    @staticmethod
    def get_token(email: str, password: str) -> str:
        """Get auth token for a user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    @staticmethod
    def get_auth_header(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}


class TestPaymentReminders:
    """Payment Reminders endpoint tests - Admin only"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = TestAuth.get_token("admin@leamss.com", "Admin@123")
        self.client_token = TestAuth.get_token("client@leamss.com", "Client@123")
        assert self.admin_token, "Admin login failed"
    
    def test_get_pending_payments_admin(self):
        """GET /api/reminders/pending-payments - Admin can get pending payments list"""
        response = requests.get(
            f"{BASE_URL}/api/reminders/pending-payments",
            headers=TestAuth.get_auth_header(self.admin_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # Check structure if there are pending payments
        if len(data) > 0:
            item = data[0]
            assert "sale_id" in item, "Missing sale_id"
            assert "client_name" in item, "Missing client_name"
            assert "urgency" in item, "Missing urgency field"
            assert item["urgency"] in ["low", "medium", "high", "critical"], f"Invalid urgency: {item['urgency']}"
            print(f"Found {len(data)} pending payments")
    
    def test_get_pending_payments_client_forbidden(self):
        """GET /api/reminders/pending-payments - Client should be forbidden"""
        if not self.client_token:
            pytest.skip("Client login failed")
        response = requests.get(
            f"{BASE_URL}/api/reminders/pending-payments",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
    
    def test_send_reminder_invalid_sale(self):
        """POST /api/reminders/send/{sale_id} - Invalid sale returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/reminders/send/invalid-sale-id-12345",
            headers=TestAuth.get_auth_header(self.admin_token)
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_send_bulk_reminders(self):
        """POST /api/reminders/send-bulk - Admin can send bulk reminders"""
        response = requests.post(
            f"{BASE_URL}/api/reminders/send-bulk",
            headers=TestAuth.get_auth_header(self.admin_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data, "Missing message in response"
        assert "count" in data, "Missing count in response"
        print(f"Bulk reminders sent: {data['count']}")


class TestAdminReceiptDownload:
    """Admin Receipt Download tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = TestAuth.get_token("admin@leamss.com", "Admin@123")
        self.client_token = TestAuth.get_token("client@leamss.com", "Client@123")
        assert self.admin_token, "Admin login failed"
    
    def test_receipt_download_invalid_sale(self):
        """GET /api/reports/export/sale-receipt/{sale_id} - Invalid sale returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/reports/export/sale-receipt/invalid-sale-id",
            headers=TestAuth.get_auth_header(self.admin_token)
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_receipt_download_client_forbidden(self):
        """GET /api/reports/export/sale-receipt/{sale_id} - Client should be forbidden"""
        if not self.client_token:
            pytest.skip("Client login failed")
        response = requests.get(
            f"{BASE_URL}/api/reports/export/sale-receipt/any-sale-id",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
    
    def test_receipt_download_with_valid_sale(self):
        """GET /api/reports/export/sale-receipt/{sale_id} - Download receipt for valid approved sale"""
        # First get a valid sale ID from all sales
        response = requests.get(
            f"{BASE_URL}/api/sales",
            headers=TestAuth.get_auth_header(self.admin_token)
        )
        if response.status_code != 200:
            pytest.skip("Could not get sales list")
        
        sales = response.json()
        approved_sales = [s for s in sales if s.get("status") == "approved"]
        if not approved_sales:
            pytest.skip("No approved sales found")
        
        sale_id = approved_sales[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/reports/export/sale-receipt/{sale_id}",
            headers=TestAuth.get_auth_header(self.admin_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Expected PDF content type"
        print(f"Receipt downloaded for sale {sale_id}")


class TestAIChat:
    """AI Chat Assistant tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client_token = TestAuth.get_token("client@leamss.com", "Client@123")
        self.admin_token = TestAuth.get_token("admin@leamss.com", "Admin@123")
        assert self.client_token, "Client login failed"
    
    def test_ai_chat_basic(self):
        """POST /api/ai-intel/chat - Client can send chat message and get response"""
        response = requests.post(
            f"{BASE_URL}/api/ai-intel/chat",
            json={"message": "What documents do I need for a visa application?"},
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "response" in data, "Missing response field"
        assert "session_id" in data, "Missing session_id field"
        assert len(data["response"]) > 0, "Response should not be empty"
        print(f"AI Chat response received, session_id: {data['session_id']}")
    
    def test_ai_chat_with_session(self):
        """POST /api/ai-intel/chat - Chat with existing session_id"""
        # First message to get session_id
        response1 = requests.post(
            f"{BASE_URL}/api/ai-intel/chat",
            json={"message": "Hello"},
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response1.status_code == 200
        session_id = response1.json().get("session_id")
        
        # Second message with same session
        response2 = requests.post(
            f"{BASE_URL}/api/ai-intel/chat",
            json={"message": "What is my case status?", "session_id": session_id},
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
        assert response2.json().get("session_id") == session_id, "Session ID should be preserved"
    
    def test_ai_chat_history(self):
        """GET /api/ai-intel/chat/history - Get chat history"""
        response = requests.get(
            f"{BASE_URL}/api/ai-intel/chat/history",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Chat history has {len(data)} messages")
    
    def test_ai_chat_unauthenticated(self):
        """POST /api/ai-intel/chat - Unauthenticated request should fail"""
        response = requests.post(
            f"{BASE_URL}/api/ai-intel/chat",
            json={"message": "Hello"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestDocumentCheck:
    """Document Completeness Check tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client_token = TestAuth.get_token("client@leamss.com", "Client@123")
        self.admin_token = TestAuth.get_token("admin@leamss.com", "Admin@123")
        assert self.client_token, "Client login failed"
    
    def get_client_case_id(self):
        """Get case ID for client"""
        response = requests.get(
            f"{BASE_URL}/api/cases/my-cases",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0].get("id")
        return None
    
    def test_case_document_check(self):
        """GET /api/ai-intel/case-document-check/{case_id} - Check document completeness"""
        case_id = self.get_client_case_id()
        if not case_id:
            pytest.skip("No case found for client")
        
        response = requests.get(
            f"{BASE_URL}/api/ai-intel/case-document-check/{case_id}",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "case_id" in data, "Missing case_id"
        assert "completeness_percentage" in data, "Missing completeness_percentage"
        assert "missing_documents" in data, "Missing missing_documents"
        assert "total_required" in data, "Missing total_required"
        assert "uploaded_count" in data, "Missing uploaded_count"
        assert isinstance(data["missing_documents"], list), "missing_documents should be a list"
        assert 0 <= data["completeness_percentage"] <= 100, "completeness_percentage should be 0-100"
        
        print(f"Document completeness: {data['completeness_percentage']}%, missing: {len(data['missing_documents'])}")
    
    def test_case_document_check_invalid_case(self):
        """GET /api/ai-intel/case-document-check/{case_id} - Invalid case returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/ai-intel/case-document-check/invalid-case-id",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestApprovalPrediction:
    """Case Approval Prediction tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client_token = TestAuth.get_token("client@leamss.com", "Client@123")
        assert self.client_token, "Client login failed"
    
    def get_client_case_id(self):
        """Get case ID for client"""
        response = requests.get(
            f"{BASE_URL}/api/cases/my-cases",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0].get("id")
        return None
    
    def test_predict_approval(self):
        """GET /api/ai-intel/predict-approval/{case_id} - Get approval prediction"""
        case_id = self.get_client_case_id()
        if not case_id:
            pytest.skip("No case found for client")
        
        response = requests.get(
            f"{BASE_URL}/api/ai-intel/predict-approval/{case_id}",
            headers=TestAuth.get_auth_header(self.client_token),
            timeout=30  # AI calls may take time
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "case_id" in data, "Missing case_id"
        assert "approval_probability" in data, "Missing approval_probability"
        assert isinstance(data["approval_probability"], (int, float)), "approval_probability should be a number"
        assert 0 <= data["approval_probability"] <= 100, "approval_probability should be 0-100"
        
        # Optional fields
        if "risk_level" in data:
            assert data["risk_level"] in ["low", "medium", "high"], f"Invalid risk_level: {data['risk_level']}"
        if "strengths" in data:
            assert isinstance(data["strengths"], list), "strengths should be a list"
        if "weaknesses" in data:
            assert isinstance(data["weaknesses"], list), "weaknesses should be a list"
        
        print(f"Approval probability: {data['approval_probability']}%, risk: {data.get('risk_level', 'N/A')}")
    
    def test_predict_approval_invalid_case(self):
        """GET /api/ai-intel/predict-approval/{case_id} - Invalid case returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/ai-intel/predict-approval/invalid-case-id",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestDocumentValidation:
    """Document Validation and OCR tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = TestAuth.get_token("admin@leamss.com", "Admin@123")
        self.client_token = TestAuth.get_token("client@leamss.com", "Client@123")
        assert self.admin_token, "Admin login failed"
    
    def get_document_id(self):
        """Get a document ID from client's case"""
        # Get client's case
        response = requests.get(
            f"{BASE_URL}/api/cases/my-cases",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        if response.status_code != 200 or len(response.json()) == 0:
            return None
        
        case_id = response.json()[0].get("id")
        
        # Get documents for case
        response = requests.get(
            f"{BASE_URL}/api/documents/case/{case_id}",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0].get("id")
        return None
    
    def test_validate_document_invalid_id(self):
        """POST /api/ai-intel/validate-document/{document_id} - Invalid document returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/ai-intel/validate-document/invalid-doc-id",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_extract_data_invalid_id(self):
        """POST /api/ai-intel/extract-data/{document_id} - Invalid document returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/ai-intel/extract-data/invalid-doc-id",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestAutoFill:
    """Auto-Fill Client Info tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = TestAuth.get_token("admin@leamss.com", "Admin@123")
        self.client_token = TestAuth.get_token("client@leamss.com", "Client@123")
        self.manager_token = TestAuth.get_token("manager@leamss.com", "Manager@123")
        assert self.admin_token, "Admin login failed"
    
    def get_case_id(self):
        """Get a case ID"""
        response = requests.get(
            f"{BASE_URL}/api/cases",
            headers=TestAuth.get_auth_header(self.admin_token)
        )
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0].get("id")
        return None
    
    def test_auto_fill_admin(self):
        """POST /api/ai-intel/auto-fill/{case_id} - Admin can auto-fill"""
        case_id = self.get_case_id()
        if not case_id:
            pytest.skip("No case found")
        
        response = requests.post(
            f"{BASE_URL}/api/ai-intel/auto-fill/{case_id}",
            headers=TestAuth.get_auth_header(self.admin_token),
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Response can be either success with case_id or message when no documents
        assert "case_id" in data or "message" in data, "Missing case_id or message"
        if "auto_filled" in data:
            print(f"Auto-fill result: {data.get('auto_filled', False)}, fields: {data.get('fields_extracted', 0)}")
        else:
            print(f"Auto-fill message: {data.get('message', 'N/A')}")
    
    def test_auto_fill_client_forbidden(self):
        """POST /api/ai-intel/auto-fill/{case_id} - Client should be forbidden"""
        if not self.client_token:
            pytest.skip("Client login failed")
        
        case_id = self.get_case_id()
        if not case_id:
            pytest.skip("No case found")
        
        response = requests.post(
            f"{BASE_URL}/api/ai-intel/auto-fill/{case_id}",
            headers=TestAuth.get_auth_header(self.client_token)
        )
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
    
    def test_auto_fill_invalid_case(self):
        """POST /api/ai-intel/auto-fill/{case_id} - Invalid case returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/ai-intel/auto-fill/invalid-case-id",
            headers=TestAuth.get_auth_header(self.admin_token)
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
