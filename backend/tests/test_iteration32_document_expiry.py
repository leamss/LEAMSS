"""
Iteration 32 - Document Expiry Tracking Feature Tests
Tests for:
- POST /api/documents/{doc_id}/set-expiry - Set expiry date (client AND manager tokens)
- GET /api/documents/expiring/all - Returns all expiring docs with urgency levels (manager only)
- GET /api/documents/expiring/case/{case_id} - Returns docs for a specific case with expiry info
- GET /api/documents/validity-presets - Returns known document types with validity periods
- POST /api/documents/upload - Now accepts optional expiry_date parameter
- POST /api/documents/bulk-upload - Now accepts optional expiry_dates JSON array
- Auto-set expiry for known doc types when uploaded without explicit expiry
- POST /api/auth/login - All 4 roles login correctly
"""
import pytest
import requests
import os
import json
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CREDENTIALS = {
    "admin": {"email": "admin@leamss.com", "password": "Admin@123"},
    "case_manager": {"email": "manager@leamss.com", "password": "Manager@123"},
    "partner": {"email": "partner@leamss.com", "password": "Partner@123"},
    "client": {"email": "client@leamss.com", "password": "Client@123"},
}

# Known case_id for client's case (from agent context)
CLIENT_CASE_ID = "cb09cf65-9a0c-47c6-8585-bace5da8c221"


class TestAuthLogin:
    """Test all 4 roles can login correctly"""
    
    def test_admin_login(self):
        """Admin should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("user", {}).get("role") == "admin", "Role should be admin"
        print(f"SUCCESS: Admin login - role={data['user']['role']}")
    
    def test_case_manager_login(self):
        """Case Manager should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["case_manager"])
        assert response.status_code == 200, f"Case Manager login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("user", {}).get("role") == "case_manager", "Role should be case_manager"
        print(f"SUCCESS: Case Manager login - role={data['user']['role']}")
    
    def test_partner_login(self):
        """Partner should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["partner"])
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("user", {}).get("role") == "partner", "Role should be partner"
        print(f"SUCCESS: Partner login - role={data['user']['role']}")
    
    def test_client_login(self):
        """Client should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("user", {}).get("role") == "client", "Role should be client"
        print(f"SUCCESS: Client login - role={data['user']['role']}")


class TestValidityPresets:
    """Test GET /api/documents/validity-presets endpoint"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        return response.json().get("token")
    
    def test_get_validity_presets(self, client_token):
        """Should return known document types with validity periods"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/validity-presets", headers=headers)
        
        assert response.status_code == 200, f"Failed to get validity presets: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one preset"
        
        # Check structure of presets
        for preset in data:
            assert "document_type" in preset, "Preset should have document_type"
            assert "label" in preset, "Preset should have label"
            assert "validity_days" in preset, "Preset should have validity_days"
            assert "validity_label" in preset, "Preset should have validity_label"
        
        # Check specific known types
        doc_types = [p["document_type"] for p in data]
        expected_types = ["passport", "medical", "ielts", "pte", "toefl", "skill_assessment", "eca", "police_clearance"]
        for expected in expected_types:
            assert expected in doc_types, f"Expected {expected} in presets"
        
        # Verify passport is 10 years (3650 days)
        passport = next((p for p in data if p["document_type"] == "passport"), None)
        assert passport is not None, "Passport preset should exist"
        assert passport["validity_days"] == 3650, f"Passport should be 3650 days, got {passport['validity_days']}"
        
        # Verify medical is 1 year (365 days)
        medical = next((p for p in data if p["document_type"] == "medical"), None)
        assert medical is not None, "Medical preset should exist"
        assert medical["validity_days"] == 365, f"Medical should be 365 days, got {medical['validity_days']}"
        
        print(f"SUCCESS: Got {len(data)} validity presets")
        print(f"  Presets: {[p['document_type'] for p in data]}")


class TestExpiringDocumentsCase:
    """Test GET /api/documents/expiring/case/{case_id} endpoint"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        return response.json().get("token")
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["case_manager"])
        return response.json().get("token")
    
    def test_get_case_expiring_documents_as_client(self, client_token):
        """Client should be able to get expiring documents for their case"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiring/case/{CLIENT_CASE_ID}", headers=headers)
        
        assert response.status_code == 200, f"Failed to get case expiring docs: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Got {len(data)} documents for case")
        
        # Check structure of documents
        for doc in data:
            assert "id" in doc, "Document should have id"
            assert "filename" in doc, "Document should have filename"
            assert "urgency" in doc, "Document should have urgency"
            assert "days_remaining" in doc or doc.get("urgency") == "no_expiry", "Document should have days_remaining or no_expiry"
            
            # Verify urgency values are valid
            valid_urgencies = ["expired", "critical", "warning", "attention", "ok", "no_expiry"]
            assert doc["urgency"] in valid_urgencies, f"Invalid urgency: {doc['urgency']}"
            
            # Check suggested_validity_days for known types
            if doc.get("document_type") in ["passport", "medical", "ielts", "pte"]:
                assert "suggested_validity_days" in doc, f"Known type {doc['document_type']} should have suggested_validity_days"
        
        # Print summary of urgency levels
        urgency_counts = {}
        for doc in data:
            urg = doc.get("urgency", "unknown")
            urgency_counts[urg] = urgency_counts.get(urg, 0) + 1
        print(f"  Urgency breakdown: {urgency_counts}")
    
    def test_get_case_expiring_documents_as_manager(self, manager_token):
        """Case Manager should also be able to get expiring documents for a case"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiring/case/{CLIENT_CASE_ID}", headers=headers)
        
        assert response.status_code == 200, f"Failed to get case expiring docs as manager: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Manager got {len(data)} documents for case")


class TestExpiringDocumentsAll:
    """Test GET /api/documents/expiring/all endpoint (manager/admin only)"""
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["case_manager"])
        return response.json().get("token")
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json().get("token")
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        return response.json().get("token")
    
    def test_get_all_expiring_documents_as_manager(self, manager_token):
        """Case Manager should be able to get all expiring documents"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiring/all", headers=headers)
        
        assert response.status_code == 200, f"Failed to get all expiring docs: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Manager got {len(data)} expiring documents")
        
        # Check structure includes client info
        for doc in data:
            assert "id" in doc, "Document should have id"
            assert "urgency" in doc, "Document should have urgency"
            assert "days_remaining" in doc, "Document should have days_remaining"
            assert "case_number" in doc, "Document should have case_number"
            assert "client_name" in doc, "Document should have client_name"
        
        # Print summary
        if data:
            urgency_counts = {}
            for doc in data:
                urg = doc.get("urgency", "unknown")
                urgency_counts[urg] = urgency_counts.get(urg, 0) + 1
            print(f"  Urgency breakdown: {urgency_counts}")
            print(f"  Sample doc: {data[0].get('filename')} - {data[0].get('urgency')} - {data[0].get('client_name')}")
    
    def test_get_all_expiring_documents_as_admin(self, admin_token):
        """Admin should be able to get all expiring documents"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiring/all", headers=headers)
        
        assert response.status_code == 200, f"Failed to get all expiring docs as admin: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Admin got {len(data)} expiring documents")
    
    def test_get_all_expiring_documents_forbidden_for_client(self, client_token):
        """Client should NOT be able to get all expiring documents"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiring/all", headers=headers)
        
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
        print("SUCCESS: Client correctly forbidden from /expiring/all endpoint")


class TestSetDocumentExpiry:
    """Test POST /api/documents/{doc_id}/set-expiry endpoint"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        return response.json().get("token")
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["case_manager"])
        return response.json().get("token")
    
    def get_document_id_for_case(self, token):
        """Helper to get a document ID from the case"""
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiring/case/{CLIENT_CASE_ID}", headers=headers)
        if response.status_code == 200:
            docs = response.json()
            if docs:
                return docs[0]["id"]
        return None
    
    def test_client_can_set_expiry(self, client_token):
        """Client should be able to set expiry date on their documents"""
        doc_id = self.get_document_id_for_case(client_token)
        if not doc_id:
            pytest.skip("No documents found in case to test")
        
        headers = {"Authorization": f"Bearer {client_token}"}
        future_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/documents/{doc_id}/set-expiry",
            json={"expiry_date": future_date, "notes": "Test expiry set by client"},
            headers=headers
        )
        
        assert response.status_code == 200, f"Client failed to set expiry: {response.text}"
        data = response.json()
        assert "message" in data, "Response should have message"
        assert "expiry_date" in data, "Response should have expiry_date"
        print(f"SUCCESS: Client set expiry to {future_date}")
    
    def test_manager_can_set_expiry(self, manager_token):
        """Case Manager should be able to set expiry date on documents"""
        doc_id = self.get_document_id_for_case(manager_token)
        if not doc_id:
            pytest.skip("No documents found in case to test")
        
        headers = {"Authorization": f"Bearer {manager_token}"}
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/documents/{doc_id}/set-expiry",
            json={"expiry_date": future_date, "notes": "Test expiry set by manager"},
            headers=headers
        )
        
        assert response.status_code == 200, f"Manager failed to set expiry: {response.text}"
        data = response.json()
        assert "message" in data, "Response should have message"
        print(f"SUCCESS: Manager set expiry to {future_date}")
    
    def test_set_expiry_invalid_date_format(self, client_token):
        """Should reject invalid date format"""
        doc_id = self.get_document_id_for_case(client_token)
        if not doc_id:
            pytest.skip("No documents found in case to test")
        
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/documents/{doc_id}/set-expiry",
            json={"expiry_date": "invalid-date", "notes": ""},
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid date, got {response.status_code}"
        print("SUCCESS: Invalid date format correctly rejected")
    
    def test_set_expiry_nonexistent_document(self, client_token):
        """Should return 404 for non-existent document"""
        headers = {"Authorization": f"Bearer {client_token}"}
        future_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/documents/nonexistent-doc-id/set-expiry",
            json={"expiry_date": future_date, "notes": ""},
            headers=headers
        )
        
        assert response.status_code == 404, f"Expected 404 for nonexistent doc, got {response.status_code}"
        print("SUCCESS: Nonexistent document correctly returns 404")


class TestUploadWithExpiry:
    """Test document upload with optional expiry_date parameter"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        return response.json().get("token")
    
    def test_upload_with_explicit_expiry(self, client_token):
        """Upload document with explicit expiry_date should set the expiry"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # Create a test file
        files = {"file": ("test_expiry_doc.txt", b"Test document content", "text/plain")}
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        data = {
            "case_id": CLIENT_CASE_ID,
            "document_type": "general",
            "step_name": "Test Step",
            "expiry_date": future_date
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload with expiry failed: {response.text}"
        result = response.json()
        assert "id" in result, "Response should have document id"
        print(f"SUCCESS: Uploaded document with explicit expiry date {future_date}")
        
        # Verify the expiry was set by fetching the document
        doc_id = result["id"]
        docs_response = requests.get(
            f"{BASE_URL}/api/documents/expiring/case/{CLIENT_CASE_ID}",
            headers=headers
        )
        if docs_response.status_code == 200:
            docs = docs_response.json()
            uploaded_doc = next((d for d in docs if d["id"] == doc_id), None)
            if uploaded_doc:
                assert uploaded_doc.get("expiry_date") is not None, "Expiry date should be set"
                print(f"  Verified expiry_date is set: {uploaded_doc.get('expiry_date')}")
    
    def test_upload_known_type_auto_expiry(self, client_token):
        """Upload known document type without expiry should auto-set expiry"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # Upload a passport (known type with 10 year validity)
        files = {"file": ("test_passport.pdf", b"Test passport content", "application/pdf")}
        
        data = {
            "case_id": CLIENT_CASE_ID,
            "document_type": "passport",  # Known type - should auto-set 10 year expiry
            "step_name": "Test Step"
            # No expiry_date provided - should auto-set
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload passport failed: {response.text}"
        result = response.json()
        doc_id = result["id"]
        print(f"SUCCESS: Uploaded passport document (id: {doc_id})")
        
        # Verify auto-expiry was set
        docs_response = requests.get(
            f"{BASE_URL}/api/documents/expiring/case/{CLIENT_CASE_ID}",
            headers=headers
        )
        if docs_response.status_code == 200:
            docs = docs_response.json()
            uploaded_doc = next((d for d in docs if d["id"] == doc_id), None)
            if uploaded_doc:
                assert uploaded_doc.get("expiry_date") is not None, "Passport should have auto-set expiry"
                # Should be approximately 10 years from now (3650 days)
                days_remaining = uploaded_doc.get("days_remaining")
                if days_remaining:
                    assert days_remaining > 3600, f"Passport expiry should be ~10 years, got {days_remaining} days"
                    print(f"  Auto-set expiry verified: {days_remaining} days remaining")


class TestBulkUploadWithExpiry:
    """Test bulk upload with optional expiry_dates JSON array"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        return response.json().get("token")
    
    def test_bulk_upload_with_expiry_dates(self, client_token):
        """Bulk upload with expiry_dates array should set expiry for each file"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # Create test files
        files = [
            ("files", ("bulk_doc1.txt", b"Document 1 content", "text/plain")),
            ("files", ("bulk_doc2.txt", b"Document 2 content", "text/plain")),
        ]
        
        future_date1 = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        future_date2 = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        data = {
            "case_id": CLIENT_CASE_ID,
            "document_type": "general",
            "document_types": json.dumps(["general", "general"]),
            "step_names": json.dumps(["Step 1", "Step 2"]),
            "expiry_dates": json.dumps([future_date1, future_date2])
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/bulk-upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Bulk upload with expiry failed: {response.text}"
        result = response.json()
        assert "uploaded" in result, "Response should have uploaded list"
        assert len(result["uploaded"]) == 2, f"Should have uploaded 2 files, got {len(result['uploaded'])}"
        print(f"SUCCESS: Bulk uploaded {len(result['uploaded'])} documents with expiry dates")
    
    def test_bulk_upload_known_types_auto_expiry(self, client_token):
        """Bulk upload known types without expiry should auto-set expiry"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # Create test files with known types
        files = [
            ("files", ("bulk_medical.pdf", b"Medical report content", "application/pdf")),
            ("files", ("bulk_ielts.pdf", b"IELTS score content", "application/pdf")),
        ]
        
        data = {
            "case_id": CLIENT_CASE_ID,
            "document_type": "general",
            "document_types": json.dumps(["medical", "ielts"]),  # Known types
            "step_names": json.dumps(["Medical Step", "Language Step"]),
            # No expiry_dates - should auto-set based on type
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/bulk-upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Bulk upload known types failed: {response.text}"
        result = response.json()
        assert len(result["uploaded"]) == 2, "Should have uploaded 2 files"
        print(f"SUCCESS: Bulk uploaded known types (medical, ielts) - should have auto-expiry")


class TestExpiryUrgencyLevels:
    """Test that urgency levels are calculated correctly"""
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["case_manager"])
        return response.json().get("token")
    
    def test_urgency_levels_in_response(self, manager_token):
        """Verify urgency levels are correctly calculated based on days remaining"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/documents/expiring/all", headers=headers)
        
        assert response.status_code == 200, f"Failed to get expiring docs: {response.text}"
        data = response.json()
        
        # Verify urgency calculation logic
        for doc in data:
            days = doc.get("days_remaining")
            urgency = doc.get("urgency")
            
            if days is not None:
                if days < 0:
                    assert urgency == "expired", f"Days {days} should be 'expired', got '{urgency}'"
                elif days <= 30:
                    assert urgency == "critical", f"Days {days} should be 'critical', got '{urgency}'"
                elif days <= 60:
                    assert urgency == "warning", f"Days {days} should be 'warning', got '{urgency}'"
                elif days <= 90:
                    assert urgency == "attention", f"Days {days} should be 'attention', got '{urgency}'"
                else:
                    assert urgency == "ok", f"Days {days} should be 'ok', got '{urgency}'"
        
        print(f"SUCCESS: Verified urgency levels for {len(data)} documents")
        
        # Print summary
        urgency_counts = {}
        for doc in data:
            urg = doc.get("urgency", "unknown")
            urgency_counts[urg] = urgency_counts.get(urg, 0) + 1
        print(f"  Urgency breakdown: {urgency_counts}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
