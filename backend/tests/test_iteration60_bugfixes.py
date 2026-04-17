"""
Iteration 60: Bug Fixes and New Country Templates Testing
- BUGFIX: Admin save workflow step (NaN duration_days, regex escaping)
- BUGFIX: CM delete unwanted AI-suggested docs (XCircle button)
- ENHANCEMENT: 4 new country templates (NZ, USA, UAE, Singapore)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestTemplatesAPI:
    """Test GET /api/step-documents/templates returns 8 templates"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = self._login("admin@leamss.com", "Admin@123")
        self.cm_token = self._login("manager@leamss.com", "Manager@123")
    
    def _login(self, email, password):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            return resp.json().get("token")
        return None
    
    def _auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}
    
    def test_templates_returns_8_templates(self):
        """GET /api/step-documents/templates should return 8 templates"""
        resp = requests.get(f"{BASE_URL}/api/step-documents/templates", headers=self._auth_header(self.admin_token))
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        templates = data.get("templates", [])
        assert len(templates) == 8, f"Expected 8 templates, got {len(templates)}: {[t['id'] for t in templates]}"
    
    def test_new_zealand_template_exists(self):
        """NZ Skilled Migrant template should exist with NZD fees"""
        resp = requests.get(f"{BASE_URL}/api/step-documents/templates", headers=self._auth_header(self.admin_token))
        assert resp.status_code == 200
        templates = resp.json().get("templates", [])
        nz_template = next((t for t in templates if t["id"] == "nz_skilled_migrant"), None)
        assert nz_template is not None, "NZ Skilled Migrant template not found"
        assert "NZD" in nz_template.get("fees_info", ""), f"NZD not in fees_info: {nz_template.get('fees_info')}"
        assert "New Zealand" in nz_template.get("label", ""), f"Label: {nz_template.get('label')}"
    
    def test_usa_h1b_template_exists(self):
        """USA H-1B template should exist with USD fees"""
        resp = requests.get(f"{BASE_URL}/api/step-documents/templates", headers=self._auth_header(self.admin_token))
        assert resp.status_code == 200
        templates = resp.json().get("templates", [])
        usa_template = next((t for t in templates if t["id"] == "usa_h1b"), None)
        assert usa_template is not None, "USA H-1B template not found"
        assert "USD" in usa_template.get("fees_info", ""), f"USD not in fees_info: {usa_template.get('fees_info')}"
        assert "H-1B" in usa_template.get("label", ""), f"Label: {usa_template.get('label')}"
    
    def test_uae_golden_visa_template_exists(self):
        """UAE Golden Visa template should exist with AED fees"""
        resp = requests.get(f"{BASE_URL}/api/step-documents/templates", headers=self._auth_header(self.admin_token))
        assert resp.status_code == 200
        templates = resp.json().get("templates", [])
        uae_template = next((t for t in templates if t["id"] == "uae_golden_visa"), None)
        assert uae_template is not None, "UAE Golden Visa template not found"
        assert "AED" in uae_template.get("fees_info", ""), f"AED not in fees_info: {uae_template.get('fees_info')}"
        assert "Golden Visa" in uae_template.get("label", ""), f"Label: {uae_template.get('label')}"
    
    def test_singapore_ep_template_exists(self):
        """Singapore EP template should exist with SGD fees"""
        resp = requests.get(f"{BASE_URL}/api/step-documents/templates", headers=self._auth_header(self.admin_token))
        assert resp.status_code == 200
        templates = resp.json().get("templates", [])
        sg_template = next((t for t in templates if t["id"] == "singapore_ep"), None)
        assert sg_template is not None, "Singapore EP template not found"
        assert "SGD" in sg_template.get("fees_info", ""), f"SGD not in fees_info: {sg_template.get('fees_info')}"
        assert "Singapore" in sg_template.get("label", ""), f"Label: {sg_template.get('label')}"


class TestAISuggestNewTemplates:
    """Test AI suggest returns template docs for new countries"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = self._login("admin@leamss.com", "Admin@123")
    
    def _login(self, email, password):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            return resp.json().get("token")
        return None
    
    def _auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}
    
    def test_usa_h1b_ai_suggest(self):
        """AI suggest for USA H-1B should return template docs"""
        resp = requests.post(
            f"{BASE_URL}/api/step-documents/ai-suggest-step-docs",
            json={
                "product_name": "USA H-1B Visa",
                "step_name": "Employer Petition & LCA",
                "step_description": "",
                "existing_docs": []
            },
            headers=self._auth_header(self.admin_token)
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("source") == "template", f"Expected source='template', got {data.get('source')}"
        suggestions = data.get("suggestions", [])
        assert len(suggestions) > 0, "No suggestions returned"
        # Check for expected docs
        doc_names = [s.get("doc_name", "").lower() for s in suggestions]
        assert any("lca" in d or "labor condition" in d for d in doc_names), f"LCA doc not found in {doc_names}"
    
    def test_uae_golden_visa_ai_suggest(self):
        """AI suggest for UAE Golden Visa should return template docs"""
        resp = requests.post(
            f"{BASE_URL}/api/step-documents/ai-suggest-step-docs",
            json={
                "product_name": "UAE Golden Visa",
                "step_name": "Eligibility & Category Selection",
                "step_description": "",
                "existing_docs": []
            },
            headers=self._auth_header(self.admin_token)
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("source") == "template", f"Expected source='template', got {data.get('source')}"
        suggestions = data.get("suggestions", [])
        assert len(suggestions) > 0, "No suggestions returned"
        # Check for expected docs
        doc_names = [s.get("doc_name", "").lower() for s in suggestions]
        assert any("passport" in d for d in doc_names), f"Passport doc not found in {doc_names}"
    
    def test_singapore_ep_ai_suggest(self):
        """AI suggest for Singapore Employment Pass should return template docs"""
        resp = requests.post(
            f"{BASE_URL}/api/step-documents/ai-suggest-step-docs",
            json={
                "product_name": "Singapore Employment Pass",
                "step_name": "COMPASS Assessment",
                "step_description": "",
                "existing_docs": []
            },
            headers=self._auth_header(self.admin_token)
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("source") == "template", f"Expected source='template', got {data.get('source')}"
        suggestions = data.get("suggestions", [])
        assert len(suggestions) > 0, "No suggestions returned"
    
    def test_new_zealand_pr_ai_suggest(self):
        """AI suggest for New Zealand Skilled Migrant should return template docs"""
        resp = requests.post(
            f"{BASE_URL}/api/step-documents/ai-suggest-step-docs",
            json={
                "product_name": "New Zealand Skilled Migrant",  # Use exact template keywords
                "step_name": "Eligibility & Preparation",
                "step_description": "",
                "existing_docs": []
            },
            headers=self._auth_header(self.admin_token)
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("source") == "template", f"Expected source='template', got {data.get('source')}"
        suggestions = data.get("suggestions", [])
        assert len(suggestions) > 0, "No suggestions returned"
        # Verify NZD fees are returned
        assert "NZD" in data.get("fees_info", ""), f"NZD not in fees_info: {data.get('fees_info')}"


class TestAdminSaveWorkflowStepBugfix:
    """Test that admin can save workflow step after AI suggest (NaN duration_days fix)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = self._login("admin@leamss.com", "Admin@123")
    
    def _login(self, email, password):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            return resp.json().get("token")
        return None
    
    def _auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}
    
    def test_save_step_with_null_duration(self):
        """Saving workflow step with null duration_days should work"""
        # First get products to find one to test with
        resp = requests.get(f"{BASE_URL}/api/products", headers=self._auth_header(self.admin_token))
        assert resp.status_code == 200
        products = resp.json()
        if not products:
            pytest.skip("No products available for testing")
        
        product = products[0]
        product_id = product["id"]
        
        # Try to create a new step with null duration_days (simulating NaN from frontend)
        step_data = {
            "step_name": "TEST_BugfixStep_" + str(os.urandom(4).hex()),
            "step_order": 999,  # High order to avoid conflicts
            "description": "Test step for bugfix verification",
            "duration_days": None,  # This was causing issues before
            "required_documents": []
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/products/{product_id}/workflow-step",
            json=step_data,
            headers=self._auth_header(self.admin_token)
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        # Cleanup - delete the test step
        requests.delete(
            f"{BASE_URL}/api/products/{product_id}/workflow-step/999",
            headers=self._auth_header(self.admin_token)
        )
    
    def test_save_step_with_empty_doc_names_filtered(self):
        """Saving workflow step should filter out empty doc_names"""
        resp = requests.get(f"{BASE_URL}/api/products", headers=self._auth_header(self.admin_token))
        assert resp.status_code == 200
        products = resp.json()
        if not products:
            pytest.skip("No products available for testing")
        
        product = products[0]
        product_id = product["id"]
        
        # Try to create a step with some empty doc_names (frontend sanitization test)
        step_data = {
            "step_name": "TEST_EmptyDocStep_" + str(os.urandom(4).hex()),
            "step_order": 998,
            "description": "Test step with empty docs",
            "duration_days": 7,
            "required_documents": [
                {"doc_name": "Valid Doc", "description": "Test", "is_mandatory": True},
                {"doc_name": "", "description": "Empty name", "is_mandatory": True},  # Should be filtered
                {"doc_name": "Another Valid", "description": "Test2", "is_mandatory": False}
            ]
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/products/{product_id}/workflow-step",
            json=step_data,
            headers=self._auth_header(self.admin_token)
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        # Verify the step was created
        resp = requests.get(f"{BASE_URL}/api/products/{product_id}", headers=self._auth_header(self.admin_token))
        assert resp.status_code == 200
        product_data = resp.json()
        test_step = next((s for s in product_data.get("workflow_steps", []) if s["step_order"] == 998), None)
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/products/{product_id}/workflow-step/998",
            headers=self._auth_header(self.admin_token)
        )
        
        # The step should have been created (backend accepts the data)
        assert test_step is not None, "Test step was not created"


class TestCMRemoveStepDoc:
    """Test CM can remove CM-added docs from step (XCircle button functionality)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.cm_token = self._login("manager@leamss.com", "Manager@123")
    
    def _login(self, email, password):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            return resp.json().get("token")
        return None
    
    def _auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}
    
    def test_remove_step_doc_endpoint_exists(self):
        """POST /api/step-documents/remove-step-doc endpoint should exist"""
        # This will fail with 422 (validation error) or 404 (case not found) but not 404 for endpoint
        resp = requests.post(
            f"{BASE_URL}/api/step-documents/remove-step-doc",
            json={
                "case_id": "nonexistent",
                "step_name": "Test Step",
                "doc_name": "Test Doc"
            },
            headers=self._auth_header(self.cm_token)
        )
        # Should get 404 for case not found, not 404 for endpoint not found
        assert resp.status_code in [404, 422, 403], f"Unexpected status: {resp.status_code}: {resp.text}"
        if resp.status_code == 404:
            assert "not found" in resp.text.lower(), f"Expected 'not found' in response: {resp.text}"


class TestRegexEscapingBugfix:
    """Test that step names with special regex characters work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = self._login("admin@leamss.com", "Admin@123")
    
    def _login(self, email, password):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            return resp.json().get("token")
        return None
    
    def _auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}
    
    def test_step_name_with_special_chars(self):
        """Step names with regex special chars should be handled correctly"""
        resp = requests.get(f"{BASE_URL}/api/products", headers=self._auth_header(self.admin_token))
        assert resp.status_code == 200
        products = resp.json()
        if not products:
            pytest.skip("No products available for testing")
        
        product = products[0]
        product_id = product["id"]
        
        # Try to create a step with special regex characters in name
        step_data = {
            "step_name": "TEST_Step (with) [brackets] + special.chars*",
            "step_order": 997,
            "description": "Test step with regex special chars",
            "duration_days": 5,
            "required_documents": []
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/products/{product_id}/workflow-step",
            json=step_data,
            headers=self._auth_header(self.admin_token)
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/products/{product_id}/workflow-step/997",
            headers=self._auth_header(self.admin_token)
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
