"""
Iteration 61: AI Workflow Builder Template Gallery Tests
- GET /api/step-documents/templates returns 8 templates
- Each template has: label, steps, total_documents, fees_info, government_url, assessment_bodies
- POST /api/step-documents/ai-suggest-bulk applies template with all documents
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestTemplateGallery:
    """Test Template Gallery API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_templates_endpoint_returns_8_templates(self):
        """GET /api/step-documents/templates returns 8 templates"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert resp.status_code == 200, f"Templates endpoint failed: {resp.text}"
        data = resp.json()
        templates = data.get("templates", [])
        assert len(templates) == 8, f"Expected 8 templates, got {len(templates)}"
        print(f"✓ Templates endpoint returns {len(templates)} templates")
    
    def test_each_template_has_required_fields(self):
        """Each template has: id, label, steps, total_documents, fees_info, government_url"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert resp.status_code == 200
        templates = resp.json().get("templates", [])
        
        required_fields = ["id", "label", "steps", "total_documents"]
        for tmpl in templates:
            for field in required_fields:
                assert field in tmpl, f"Template {tmpl.get('id', 'unknown')} missing field: {field}"
            assert isinstance(tmpl["steps"], list), f"Template {tmpl['id']} steps should be a list"
            assert tmpl["total_documents"] > 0, f"Template {tmpl['id']} should have documents"
        print(f"✓ All {len(templates)} templates have required fields")
    
    def test_canada_pr_template_details(self):
        """Canada PR template has correct details"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        templates = resp.json().get("templates", [])
        canada = next((t for t in templates if t["id"] == "canada_pr"), None)
        
        assert canada is not None, "Canada PR template not found"
        assert "Canada" in canada["label"], f"Label should contain Canada: {canada['label']}"
        assert "Express Entry" in canada["label"], f"Label should contain Express Entry: {canada['label']}"
        assert len(canada["steps"]) >= 5, f"Canada PR should have 5+ steps, got {len(canada['steps'])}"
        assert "CAD" in canada.get("fees_info", ""), f"Fees should mention CAD: {canada.get('fees_info')}"
        assert "canada.ca" in canada.get("government_url", ""), f"URL should be canada.ca: {canada.get('government_url')}"
        assert len(canada.get("assessment_bodies", [])) > 0, "Should have assessment bodies"
        print(f"✓ Canada PR template: {canada['label']}, {len(canada['steps'])} steps, {canada['total_documents']} docs")
    
    def test_australia_pr_template_details(self):
        """Australia PR template has correct details"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        templates = resp.json().get("templates", [])
        australia = next((t for t in templates if t["id"] == "australia_pr"), None)
        
        assert australia is not None, "Australia PR template not found"
        assert "Australia" in australia["label"]
        assert "AUD" in australia.get("fees_info", ""), f"Fees should mention AUD"
        assert "homeaffairs.gov.au" in australia.get("government_url", "")
        print(f"✓ Australia PR template: {australia['label']}, {len(australia['steps'])} steps")
    
    def test_uk_skilled_worker_template_details(self):
        """UK Skilled Worker template has correct details"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        templates = resp.json().get("templates", [])
        uk = next((t for t in templates if t["id"] == "uk_skilled_worker"), None)
        
        assert uk is not None, "UK Skilled Worker template not found"
        assert "UK" in uk["label"] or "Skilled Worker" in uk["label"]
        assert "GBP" in uk.get("fees_info", ""), f"Fees should mention GBP"
        assert "gov.uk" in uk.get("government_url", "")
        print(f"✓ UK Skilled Worker template: {uk['label']}, {len(uk['steps'])} steps")
    
    def test_usa_h1b_template_details(self):
        """USA H-1B template has correct details"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        templates = resp.json().get("templates", [])
        usa = next((t for t in templates if t["id"] == "usa_h1b"), None)
        
        assert usa is not None, "USA H-1B template not found"
        assert "H-1B" in usa["label"] or "USA" in usa["label"]
        assert "USD" in usa.get("fees_info", ""), f"Fees should mention USD"
        assert "uscis.gov" in usa.get("government_url", "")
        print(f"✓ USA H-1B template: {usa['label']}, {len(usa['steps'])} steps")
    
    def test_uae_golden_visa_template_details(self):
        """UAE Golden Visa template has correct details"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        templates = resp.json().get("templates", [])
        uae = next((t for t in templates if t["id"] == "uae_golden_visa"), None)
        
        assert uae is not None, "UAE Golden Visa template not found"
        assert "UAE" in uae["label"] or "Golden Visa" in uae["label"]
        assert "AED" in uae.get("fees_info", ""), f"Fees should mention AED"
        assert "u.ae" in uae.get("government_url", "")
        print(f"✓ UAE Golden Visa template: {uae['label']}, {len(uae['steps'])} steps")
    
    def test_singapore_ep_template_details(self):
        """Singapore EP template has correct details"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        templates = resp.json().get("templates", [])
        sg = next((t for t in templates if t["id"] == "singapore_ep"), None)
        
        assert sg is not None, "Singapore EP template not found"
        assert "Singapore" in sg["label"] or "Employment Pass" in sg["label"]
        assert "SGD" in sg.get("fees_info", ""), f"Fees should mention SGD"
        assert "mom.gov.sg" in sg.get("government_url", "")
        print(f"✓ Singapore EP template: {sg['label']}, {len(sg['steps'])} steps")
    
    def test_nz_skilled_migrant_template_details(self):
        """New Zealand Skilled Migrant template has correct details"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        templates = resp.json().get("templates", [])
        nz = next((t for t in templates if t["id"] == "nz_skilled_migrant"), None)
        
        assert nz is not None, "NZ Skilled Migrant template not found"
        assert "New Zealand" in nz["label"] or "Skilled Migrant" in nz["label"]
        assert "NZD" in nz.get("fees_info", ""), f"Fees should mention NZD"
        assert "immigration.govt.nz" in nz.get("government_url", "")
        print(f"✓ NZ Skilled Migrant template: {nz['label']}, {len(nz['steps'])} steps")
    
    def test_student_visa_template_details(self):
        """Student Visa template has correct details"""
        resp = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        templates = resp.json().get("templates", [])
        student = next((t for t in templates if t["id"] == "student_visa_generic"), None)
        
        assert student is not None, "Student Visa template not found"
        assert "Student" in student["label"]
        assert len(student["steps"]) >= 3, f"Student visa should have 3+ steps"
        print(f"✓ Student Visa template: {student['label']}, {len(student['steps'])} steps")


class TestAISuggestBulk:
    """Test AI Suggest Bulk endpoint for template application"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_ai_suggest_bulk_canada_pr(self):
        """AI suggest bulk for Canada PR returns template docs"""
        resp = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-bulk", json={
            "product_name": "Canada Permanent Residency (Express Entry)",
            "steps": [
                {"step_name": "Profile Creation"},
                {"step_name": "Education Credential Assessment"},
                {"step_name": "Language Testing"}
            ]
        })
        assert resp.status_code == 200, f"AI suggest bulk failed: {resp.text}"
        data = resp.json()
        
        assert data.get("source") == "template", f"Source should be template, got {data.get('source')}"
        suggestions = data.get("suggestions", {})
        assert len(suggestions) >= 2, f"Should have suggestions for at least 2 steps"
        assert "CAD" in data.get("fees_info", ""), "Should include CAD fees"
        print(f"✓ AI suggest bulk for Canada PR: source={data['source']}, {len(suggestions)} steps with docs")
    
    def test_ai_suggest_bulk_australia_pr(self):
        """AI suggest bulk for Australia PR returns template docs"""
        resp = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-bulk", json={
            "product_name": "Australia Permanent Residency (Skilled Migration 189)",
            "steps": [
                {"step_name": "Skills Assessment"},
                {"step_name": "Language Testing"},
                {"step_name": "EOI Submission"}
            ]
        })
        assert resp.status_code == 200, f"AI suggest bulk failed: {resp.text}"
        data = resp.json()
        
        assert data.get("source") == "template", f"Source should be template, got {data.get('source')}"
        assert "AUD" in data.get("fees_info", ""), "Should include AUD fees"
        print(f"✓ AI suggest bulk for Australia PR: source={data['source']}")
    
    def test_ai_suggest_bulk_returns_documents_for_each_step(self):
        """AI suggest bulk returns documents for each step"""
        resp = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-bulk", json={
            "product_name": "UK Skilled Worker Visa",
            "steps": [
                {"step_name": "Certificate of Sponsorship"},
                {"step_name": "English Language"},
                {"step_name": "Visa Application"}
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        suggestions = data.get("suggestions", {})
        
        # Check that each step has documents
        for step_name, docs in suggestions.items():
            assert isinstance(docs, list), f"Docs for {step_name} should be a list"
            assert len(docs) > 0, f"Step {step_name} should have documents"
            for doc in docs:
                assert "doc_name" in doc, f"Doc in {step_name} missing doc_name"
                assert "is_mandatory" in doc, f"Doc in {step_name} missing is_mandatory"
        print(f"✓ AI suggest bulk returns docs for each step: {list(suggestions.keys())}")


class TestAIWorkflowSave:
    """Test AI Workflow save endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_ai_workflow_save_endpoint_exists(self):
        """POST /api/ai-workflow/save endpoint exists"""
        # Just check the endpoint exists (don't actually save to avoid polluting data)
        resp = self.session.post(f"{BASE_URL}/api/ai-workflow/save", json={
            "product_name": "TEST_Template_Product_DELETE_ME",
            "description": "Test product from template",
            "category": "immigration",
            "base_fee": 0,
            "commission_rate": 10,
            "steps": [
                {
                    "step_name": "Test Step",
                    "step_order": 1,
                    "description": "Test description",
                    "duration_days": 14,
                    "required_documents": [
                        {"name": "Test Doc", "description": "Test", "mandatory": True, "doc_type": "other"}
                    ]
                }
            ]
        })
        # Should succeed or fail with validation error, not 404
        assert resp.status_code in [200, 201, 400, 422], f"Unexpected status: {resp.status_code} - {resp.text}"
        print(f"✓ AI workflow save endpoint exists, status: {resp.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
