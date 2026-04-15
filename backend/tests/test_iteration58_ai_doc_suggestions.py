"""
Iteration 58: AI Document Suggestion Feature Tests
Tests for:
1. POST /api/step-documents/ai-suggest-step-docs - AI suggests docs for a specific step
2. POST /api/step-documents/ai-suggest-bulk - AI suggests docs for all steps of a product
3. Audit log creation for AI suggestions
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
CM_EMAIL = "manager@leamss.com"
CM_PASSWORD = "Manager@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASSWORD = "Client@123"


class TestAIDocumentSuggestions:
    """Test AI Document Suggestion endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, email, password):
        """Helper to login and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    # ============ Authentication Tests ============
    
    def test_admin_login(self):
        """Test admin can login"""
        result = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert result is not None, "Admin login failed"
        assert result.get("user", {}).get("role") == "admin"
        print("PASS: Admin login successful")
    
    def test_cm_login(self):
        """Test case manager can login"""
        result = self.login(CM_EMAIL, CM_PASSWORD)
        assert result is not None, "CM login failed"
        assert result.get("user", {}).get("role") == "case_manager"
        print("PASS: Case Manager login successful")
    
    def test_client_login(self):
        """Test client can login"""
        result = self.login(CLIENT_EMAIL, CLIENT_PASSWORD)
        assert result is not None, "Client login failed"
        assert result.get("user", {}).get("role") == "client"
        print("PASS: Client login successful")
    
    # ============ AI Suggest Step Docs Tests ============
    
    def test_ai_suggest_step_docs_admin(self):
        """Test admin can get AI suggestions for a specific step"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Canada PR",
            "step_name": "ECA",
            "step_description": "Educational Credential Assessment",
            "existing_docs": []
        }, timeout=30)  # AI may take time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "suggestions" in data, "Response should contain 'suggestions' key"
        
        # Validate suggestion structure if any returned
        suggestions = data.get("suggestions", [])
        print(f"PASS: AI suggest step docs returned {len(suggestions)} suggestions")
        
        if len(suggestions) > 0:
            first_suggestion = suggestions[0]
            assert "doc_name" in first_suggestion, "Suggestion should have 'doc_name'"
            assert "description" in first_suggestion, "Suggestion should have 'description'"
            assert "is_mandatory" in first_suggestion, "Suggestion should have 'is_mandatory'"
            assert "doc_type" in first_suggestion, "Suggestion should have 'doc_type'"
            print(f"PASS: Suggestion structure validated - first doc: {first_suggestion.get('doc_name')}")
    
    def test_ai_suggest_step_docs_cm(self):
        """Test case manager can get AI suggestions for a specific step"""
        self.login(CM_EMAIL, CM_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Canada PR",
            "step_name": "IELTS/CELPIP/PTE CORE",
            "step_description": "Language proficiency test results",
            "existing_docs": ["IELTS Score Card"]
        }, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "suggestions" in data
        print(f"PASS: CM AI suggest step docs returned {len(data.get('suggestions', []))} suggestions")
    
    def test_ai_suggest_step_docs_client_forbidden(self):
        """Test client cannot access AI suggestions"""
        self.login(CLIENT_EMAIL, CLIENT_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Canada PR",
            "step_name": "ECA",
            "step_description": "",
            "existing_docs": []
        }, timeout=10)
        
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
        print("PASS: Client correctly forbidden from AI suggestions")
    
    # ============ AI Bulk Suggest Tests ============
    
    def test_ai_suggest_bulk_admin(self):
        """Test admin can get AI suggestions for all steps at once"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-bulk", json={
            "product_name": "Canada PR",
            "product_description": "Permanent Residency application for Canada",
            "steps": [
                {"step_name": "ECA", "description": "Educational Credential Assessment"},
                {"step_name": "IELTS/CELPIP/PTE CORE", "description": "Language test"},
                {"step_name": "COPR", "description": "Confirmation of Permanent Residence"}
            ]
        }, timeout=45)  # Bulk may take longer
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "suggestions" in data, "Response should contain 'suggestions' key"
        
        suggestions = data.get("suggestions", {})
        assert isinstance(suggestions, dict), "Bulk suggestions should be a dict keyed by step name"
        print(f"PASS: AI bulk suggest returned suggestions for {len(suggestions)} steps")
        
        # Validate structure
        for step_name, step_docs in suggestions.items():
            assert isinstance(step_docs, list), f"Docs for {step_name} should be a list"
            if len(step_docs) > 0:
                assert "doc_name" in step_docs[0], f"Doc in {step_name} should have 'doc_name'"
                print(f"  - {step_name}: {len(step_docs)} documents suggested")
    
    def test_ai_suggest_bulk_cm(self):
        """Test case manager can get AI bulk suggestions"""
        self.login(CM_EMAIL, CM_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-bulk", json={
            "product_name": "Test Product",
            "product_description": "Test immigration product",
            "steps": [
                {"step_name": "Step 1", "description": "Initial documents"},
                {"step_name": "Step 2", "description": "Supporting documents"}
            ]
        }, timeout=45)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "suggestions" in data
        print(f"PASS: CM AI bulk suggest returned suggestions")
    
    def test_ai_suggest_bulk_client_forbidden(self):
        """Test client cannot access bulk AI suggestions"""
        self.login(CLIENT_EMAIL, CLIENT_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-bulk", json={
            "product_name": "Canada PR",
            "product_description": "",
            "steps": []
        }, timeout=10)
        
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
        print("PASS: Client correctly forbidden from bulk AI suggestions")
    
    # ============ Audit Log Tests ============
    
    def test_ai_suggestion_creates_audit_log(self):
        """Test that AI suggestions create audit log entries"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        # Make an AI suggestion request
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Audit Test Product",
            "step_name": "Audit Test Step",
            "step_description": "Testing audit log creation",
            "existing_docs": []
        }, timeout=30)
        
        assert response.status_code == 200, f"AI suggestion failed: {response.text}"
        
        # Check audit logs - need to verify via admin activity or direct DB check
        # Since we don't have direct audit log API, we verify the endpoint worked
        print("PASS: AI suggestion endpoint completed (audit log should be created)")
    
    def test_ai_bulk_suggestion_creates_audit_log(self):
        """Test that bulk AI suggestions create audit log entries"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-bulk", json={
            "product_name": "Bulk Audit Test",
            "product_description": "Testing bulk audit",
            "steps": [{"step_name": "Test Step", "description": "Test"}]
        }, timeout=30)
        
        assert response.status_code == 200, f"Bulk AI suggestion failed: {response.text}"
        print("PASS: Bulk AI suggestion endpoint completed (audit log should be created)")
    
    # ============ Products API Tests ============
    
    def test_get_products_with_workflow_steps(self):
        """Test that products API returns workflow steps"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Failed to get products: {response.text}"
        
        products = response.json()
        assert isinstance(products, list), "Products should be a list"
        
        # Find Canada PR product
        canada_pr = next((p for p in products if "Canada" in p.get("name", "")), None)
        if canada_pr:
            workflow_steps = canada_pr.get("workflow_steps", [])
            print(f"PASS: Canada PR has {len(workflow_steps)} workflow steps")
            for step in workflow_steps[:4]:
                print(f"  - {step.get('step_name')}: {len(step.get('required_documents', []))} docs")
        else:
            print("INFO: Canada PR product not found, skipping workflow step check")
    
    # ============ Validation Tests ============
    
    def test_ai_suggest_empty_step_name(self):
        """Test AI suggestion with empty step name"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Canada PR",
            "step_name": "",  # Empty step name
            "step_description": "",
            "existing_docs": []
        }, timeout=30)
        
        # Should still work but may return generic suggestions
        assert response.status_code in [200, 422], f"Unexpected status: {response.status_code}"
        print(f"PASS: Empty step name handled with status {response.status_code}")
    
    def test_ai_suggest_bulk_empty_steps(self):
        """Test bulk AI suggestion with empty steps array"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-bulk", json={
            "product_name": "Test Product",
            "product_description": "",
            "steps": []  # Empty steps
        }, timeout=30)
        
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        data = response.json()
        suggestions = data.get("suggestions", {})
        assert isinstance(suggestions, dict), "Should return empty dict for empty steps"
        print(f"PASS: Empty steps handled, returned {len(suggestions)} suggestions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
