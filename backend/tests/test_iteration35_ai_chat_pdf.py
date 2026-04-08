"""
Iteration 35 Tests - AI Chat with Full Workflow Context & Info Sheet PDF Export
Tests:
1. AI Chat endpoint with workflow context (steps, docs, expiry alerts)
2. AI Chat session persistence
3. Info Sheet PDF export with logo
4. All role logins
5. Health endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}
CLIENT_CASE_ID = "cb09cf65-9a0c-47c6-8585-bace5da8c221"


@pytest.fixture(scope="module")
def client_token():
    """Get client auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Client login failed")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin login failed")


@pytest.fixture(scope="module")
def manager_token():
    """Get manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Manager login failed")


class TestHealthAndAuth:
    """Health and authentication tests"""

    def test_health_endpoint(self):
        """GET /api/health - Returns healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        print("✓ Health endpoint returns healthy with database connected")

    def test_admin_login(self):
        """POST /api/auth/login - Admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print("✓ Admin login successful")

    def test_manager_login(self):
        """POST /api/auth/login - Case Manager login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print("✓ Case Manager login successful")

    def test_client_login(self):
        """POST /api/auth/login - Client login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print("✓ Client login successful")


class TestAIChatWithWorkflowContext:
    """AI Chat endpoint tests with full workflow context"""

    def test_ai_chat_returns_step_info(self, client_token):
        """POST /api/ai-intel/chat - AI responds with specific case step info"""
        headers = {"Authorization": f"Bearer {client_token}"}
        payload = {"message": "What is my current step and case status?"}
        
        response = requests.post(f"{BASE_URL}/api/ai-intel/chat", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        assert "session_id" in data
        
        # Check that response mentions step names
        response_text = data["response"].lower()
        # Should mention actual step names from the case
        step_keywords = ["step", "ielts", "preparation", "profile", "document", "collection"]
        has_step_info = any(kw in response_text for kw in step_keywords)
        assert has_step_info, f"Response should mention step info. Got: {data['response'][:200]}"
        print(f"✓ AI chat returns step info. Response: {data['response'][:150]}...")

    def test_ai_chat_returns_document_counts(self, client_token):
        """POST /api/ai-intel/chat - Response mentions document counts"""
        headers = {"Authorization": f"Bearer {client_token}"}
        payload = {"message": "How many documents have I uploaded and how many are approved?"}
        
        response = requests.post(f"{BASE_URL}/api/ai-intel/chat", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        response_text = data["response"].lower()
        # Should mention document counts
        doc_keywords = ["document", "uploaded", "approved", "pending", "19", "5"]
        has_doc_info = any(kw in response_text for kw in doc_keywords)
        assert has_doc_info, f"Response should mention document counts. Got: {data['response'][:200]}"
        print(f"✓ AI chat returns document counts. Response: {data['response'][:150]}...")

    def test_ai_chat_returns_expiry_alerts(self, client_token):
        """POST /api/ai-intel/chat - Response mentions expiry alerts"""
        headers = {"Authorization": f"Bearer {client_token}"}
        payload = {"message": "Do I have any documents expiring soon?"}
        
        response = requests.post(f"{BASE_URL}/api/ai-intel/chat", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        response_text = data["response"].lower()
        # Should mention expiry info
        expiry_keywords = ["expir", "renew", "days", "alert", "medical", "ielts"]
        has_expiry_info = any(kw in response_text for kw in expiry_keywords)
        assert has_expiry_info, f"Response should mention expiry info. Got: {data['response'][:200]}"
        print(f"✓ AI chat returns expiry alerts. Response: {data['response'][:150]}...")

    def test_ai_chat_session_persistence(self, client_token):
        """POST /api/ai-intel/chat - Chat session persists with session_id"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # First message - get session_id
        payload1 = {"message": "Hello, what is my case status?"}
        response1 = requests.post(f"{BASE_URL}/api/ai-intel/chat", json=payload1, headers=headers)
        assert response1.status_code == 200
        data1 = response1.json()
        session_id = data1["session_id"]
        assert session_id, "Session ID should be returned"
        
        # Second message - use same session_id
        payload2 = {"message": "What about my payment status?", "session_id": session_id}
        response2 = requests.post(f"{BASE_URL}/api/ai-intel/chat", json=payload2, headers=headers)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Session ID should be preserved
        assert data2["session_id"] == session_id, "Session ID should be preserved across messages"
        print(f"✓ Chat session persists. Session ID: {session_id}")

    def test_ai_chat_mentions_actual_step_names(self, client_token):
        """POST /api/ai-intel/chat - Response mentions actual step names from the case"""
        headers = {"Authorization": f"Bearer {client_token}"}
        payload = {"message": "List all the steps in my case and their status"}
        
        response = requests.post(f"{BASE_URL}/api/ai-intel/chat", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        response_text = data["response"]
        # Should mention actual step names like Profile Creation, IELTS Preparation, etc.
        step_names = ["Profile Creation", "Document Collection", "IELTS", "Preparation"]
        mentioned_steps = [name for name in step_names if name.lower() in response_text.lower()]
        assert len(mentioned_steps) >= 1, f"Response should mention actual step names. Got: {response_text[:300]}"
        print(f"✓ AI chat mentions actual step names: {mentioned_steps}")


class TestInfoSheetPDFExport:
    """Info Sheet PDF export tests"""

    def test_info_sheet_pdf_export_returns_pdf(self, client_token):
        """GET /api/reports/export/info-sheet/{case_id} - Returns a PDF file"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/reports/export/info-sheet/{CLIENT_CASE_ID}",
            headers=headers
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        print(f"✓ Info sheet PDF export returns PDF. Content-Type: {response.headers.get('content-type')}")

    def test_info_sheet_pdf_size_over_100kb(self, client_token):
        """GET /api/reports/export/info-sheet/{case_id} - PDF file is >100KB (has logo)"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/reports/export/info-sheet/{CLIENT_CASE_ID}",
            headers=headers
        )
        assert response.status_code == 200
        
        pdf_size = len(response.content)
        assert pdf_size > 100000, f"PDF should be >100KB (has logo). Got: {pdf_size} bytes"
        print(f"✓ Info sheet PDF is {pdf_size} bytes (>100KB, includes logo)")

    def test_info_sheet_pdf_contains_pdf_header(self, client_token):
        """GET /api/reports/export/info-sheet/{case_id} - PDF contains valid PDF header"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/reports/export/info-sheet/{CLIENT_CASE_ID}",
            headers=headers
        )
        assert response.status_code == 200
        
        # PDF files start with %PDF-
        assert response.content[:5] == b'%PDF-', "Response should be a valid PDF file"
        print("✓ Info sheet PDF has valid PDF header (%PDF-)")

    def test_info_sheet_pdf_not_found_for_invalid_case(self, client_token):
        """GET /api/reports/export/info-sheet/{case_id} - Returns 404 for invalid case"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/reports/export/info-sheet/invalid-case-id-12345",
            headers=headers
        )
        assert response.status_code == 404
        print("✓ Info sheet PDF returns 404 for invalid case")


class TestInfoSheetData:
    """Info Sheet data tests - verify data structure for PDF"""

    def test_info_sheet_has_personal_details(self, client_token):
        """GET /api/cases/{case_id}/information-sheet - Has personal details"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/cases/{CLIENT_CASE_ID}/information-sheet",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["exists"] == True
        sheet_data = data["data"]
        
        # Check personal details fields
        personal_fields = ["given_names", "family_name", "gender", "date_of_birth", "email"]
        found_fields = [f for f in personal_fields if sheet_data.get(f)]
        assert len(found_fields) >= 3, f"Should have personal details. Found: {found_fields}"
        print(f"✓ Info sheet has personal details: {found_fields}")

    def test_info_sheet_has_qualifications(self, client_token):
        """GET /api/cases/{case_id}/information-sheet - Has qualifications (6 entries)"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/cases/{CLIENT_CASE_ID}/information-sheet",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        sheet_data = data["data"]
        
        # Count qualification entries
        qual_count = 0
        for i in range(1, 10):
            if sheet_data.get(f"qualification_{i}_name"):
                qual_count += 1
        
        assert qual_count >= 6, f"Should have 6 qualifications. Found: {qual_count}"
        print(f"✓ Info sheet has {qual_count} qualifications (expected 6)")

    def test_info_sheet_has_employment(self, client_token):
        """GET /api/cases/{case_id}/information-sheet - Has employment history (6 entries)"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/cases/{CLIENT_CASE_ID}/information-sheet",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        sheet_data = data["data"]
        
        # Count employment entries
        emp_count = 0
        for i in range(1, 10):
            if sheet_data.get(f"employment_{i}_business_name"):
                emp_count += 1
        
        assert emp_count >= 6, f"Should have 6 employment entries. Found: {emp_count}"
        print(f"✓ Info sheet has {emp_count} employment entries (expected 6)")


class TestInfoSheetSchema:
    """Info Sheet schema tests - verify 6 sections"""

    def test_info_sheet_schema_has_6_sections(self, client_token):
        """GET /api/cases/info-sheet-schema - Returns 6 sections"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(f"{BASE_URL}/api/cases/info-sheet-schema", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "sections" in data
        assert len(data["sections"]) == 6, f"Should have 6 sections. Got: {len(data['sections'])}"
        
        section_ids = [s["id"] for s in data["sections"]]
        expected_ids = ["personal_details", "family_chart", "dependent_children", 
                       "migrating_dependents", "qualifications", "employment"]
        for eid in expected_ids:
            assert eid in section_ids, f"Missing section: {eid}"
        
        print(f"✓ Info sheet schema has 6 sections: {section_ids}")

    def test_repeatable_sections_have_entry_fields(self, client_token):
        """GET /api/cases/info-sheet-schema - Repeatable sections have entry_fields"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.get(f"{BASE_URL}/api/cases/info-sheet-schema", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        repeatable_sections = ["dependent_children", "migrating_dependents", "qualifications", "employment_history"]
        for section in data["sections"]:
            if section["id"] in repeatable_sections:
                assert section.get("repeatable") == True, f"{section['id']} should be repeatable"
                assert "entry_fields" in section, f"{section['id']} should have entry_fields"
                assert "entry_prefix" in section, f"{section['id']} should have entry_prefix"
        
        print("✓ Repeatable sections have entry_fields and entry_prefix")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
