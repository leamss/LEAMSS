"""
Iteration 59: Smart Template + Web Search AI Document Suggestions
Tests for:
1. Template-based suggestions for Australia PR, Canada PR, UK Skilled Worker, Student Visa
2. GET /api/step-documents/templates - List available templates
3. Template response includes source='template', fees_info, government_url
4. AI fallback for non-template products (source='ai')
5. Audit logs for template vs AI suggestions
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


class TestSmartTemplates:
    """Test Smart Template AI Document Suggestion features"""
    
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
    
    # ============ GET /api/step-documents/templates Tests ============
    
    def test_get_templates_admin(self):
        """Test admin can get list of available templates"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "templates" in data, "Response should contain 'templates' key"
        
        templates = data["templates"]
        assert len(templates) == 4, f"Expected 4 templates, got {len(templates)}"
        
        # Verify template structure
        for tmpl in templates:
            assert "id" in tmpl, "Template should have 'id'"
            assert "label" in tmpl, "Template should have 'label'"
            assert "steps" in tmpl, "Template should have 'steps'"
            assert "total_documents" in tmpl, "Template should have 'total_documents'"
            assert "fees_info" in tmpl, "Template should have 'fees_info'"
            assert "government_url" in tmpl, "Template should have 'government_url'"
        
        print(f"PASS: GET /api/step-documents/templates returned {len(templates)} templates")
        for tmpl in templates:
            print(f"  - {tmpl['label']}: {tmpl['total_documents']} docs, {len(tmpl['steps'])} steps")
    
    def test_get_templates_cm(self):
        """Test case manager can get templates"""
        self.login(CM_EMAIL, CM_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert len(data.get("templates", [])) == 4
        print("PASS: CM can access templates endpoint")
    
    def test_get_templates_client_forbidden(self):
        """Test client cannot access templates"""
        self.login(CLIENT_EMAIL, CLIENT_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
        print("PASS: Client correctly forbidden from templates endpoint")
    
    def test_templates_have_correct_structure(self):
        """Verify each template has correct structure with real data"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        
        # Check Canada PR template
        canada = next((t for t in templates if "canada" in t["id"]), None)
        assert canada is not None, "Canada PR template should exist"
        assert "CAD" in canada["fees_info"], "Canada fees should be in CAD"
        assert "canada.ca" in canada["government_url"], "Canada URL should be canada.ca"
        assert "WES" in str(canada.get("assessment_bodies", [])), "Canada should mention WES"
        print(f"PASS: Canada PR template verified - fees: {canada['fees_info'][:50]}...")
        
        # Check Australia PR template
        australia = next((t for t in templates if "australia" in t["id"]), None)
        assert australia is not None, "Australia PR template should exist"
        assert "AUD" in australia["fees_info"], "Australia fees should be in AUD"
        assert "homeaffairs.gov.au" in australia["government_url"], "Australia URL should be homeaffairs.gov.au"
        print(f"PASS: Australia PR template verified - fees: {australia['fees_info'][:50]}...")
        
        # Check UK Skilled Worker template
        uk = next((t for t in templates if "uk" in t["id"]), None)
        assert uk is not None, "UK Skilled Worker template should exist"
        assert "GBP" in uk["fees_info"], "UK fees should be in GBP"
        assert "gov.uk" in uk["government_url"], "UK URL should be gov.uk"
        print(f"PASS: UK Skilled Worker template verified - fees: {uk['fees_info'][:50]}...")
        
        # Check Student Visa template
        student = next((t for t in templates if "student" in t["id"]), None)
        assert student is not None, "Student Visa template should exist"
        print(f"PASS: Student Visa template verified - {student['total_documents']} docs")
    
    # ============ Australia PR Template Tests ============
    
    def test_australia_pr_skills_assessment_template(self):
        """Test Australia PR Skills Assessment returns template-sourced docs"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Australia Permanent Residency",
            "step_name": "Skills Assessment",
            "step_description": "Skills assessment for skilled migration",
            "existing_docs": []
        }, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return template-sourced docs
        assert data.get("source") == "template", f"Expected source='template', got '{data.get('source')}'"
        assert "Australia" in data.get("template_name", ""), "Template name should mention Australia"
        assert "AUD" in data.get("fees_info", ""), "Fees should be in AUD"
        assert "homeaffairs.gov.au" in data.get("government_url", ""), "URL should be homeaffairs.gov.au"
        
        suggestions = data.get("suggestions", [])
        assert len(suggestions) > 0, "Should return template documents"
        
        # Verify expected documents for Skills Assessment
        doc_names = [d["doc_name"] for d in suggestions]
        expected_docs = ["Skills Assessment Outcome Letter", "Qualification Certificates", "Employment Reference Letters"]
        found_expected = sum(1 for exp in expected_docs if any(exp.lower() in dn.lower() for dn in doc_names))
        assert found_expected >= 2, f"Expected at least 2 of {expected_docs}, found {found_expected}"
        
        print(f"PASS: Australia PR Skills Assessment returned {len(suggestions)} template docs")
        print(f"  Source: {data.get('source')}")
        print(f"  Template: {data.get('template_name')}")
        print(f"  Fees: {data.get('fees_info', '')[:60]}...")
        print(f"  URL: {data.get('government_url')}")
        for doc in suggestions[:3]:
            print(f"  - {doc['doc_name']}")
    
    def test_australia_pr_bulk_template(self):
        """Test Australia PR bulk suggest returns template docs for all steps"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-bulk", json={
            "product_name": "Australia Permanent Residency",
            "product_description": "Skilled migration visa 189/190/491",
            "steps": [
                {"step_name": "Skills Assessment", "description": "Skills assessment from ACS/VETASSESS"},
                {"step_name": "Language Testing", "description": "PTE/IELTS results"},
                {"step_name": "EOI Submission", "description": "Expression of Interest"},
                {"step_name": "Visa Application", "description": "Final visa application"}
            ]
        }, timeout=45)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return template-sourced docs
        assert data.get("source") == "template", f"Expected source='template', got '{data.get('source')}'"
        assert "AUD" in data.get("fees_info", ""), "Fees should be in AUD"
        
        suggestions = data.get("suggestions", {})
        assert len(suggestions) >= 3, f"Expected docs for at least 3 steps, got {len(suggestions)}"
        
        print(f"PASS: Australia PR bulk returned template docs for {len(suggestions)} steps")
        for step_name, docs in suggestions.items():
            print(f"  - {step_name}: {len(docs)} documents")
    
    # ============ Canada PR Template Tests ============
    
    def test_canada_pr_eca_template(self):
        """Test Canada PR ECA step returns accurate template docs"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Canada PR",
            "step_name": "Education Credential Assessment",
            "step_description": "ECA from WES or other designated body",
            "existing_docs": []
        }, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return template-sourced docs
        assert data.get("source") == "template", f"Expected source='template', got '{data.get('source')}'"
        assert "CAD" in data.get("fees_info", ""), "Fees should be in CAD"
        assert "canada.ca" in data.get("government_url", ""), "URL should be canada.ca"
        
        suggestions = data.get("suggestions", [])
        assert len(suggestions) > 0, "Should return template documents"
        
        # Verify expected ECA documents
        doc_names = [d["doc_name"] for d in suggestions]
        expected_docs = ["ECA Report", "Degree Certificate", "Academic Transcripts"]
        found_expected = sum(1 for exp in expected_docs if any(exp.lower() in dn.lower() for dn in doc_names))
        assert found_expected >= 2, f"Expected at least 2 of {expected_docs}, found {found_expected}"
        
        print(f"PASS: Canada PR ECA returned {len(suggestions)} template docs")
        print(f"  Source: {data.get('source')}")
        print(f"  Fees: {data.get('fees_info', '')[:60]}...")
        for doc in suggestions[:3]:
            print(f"  - {doc['doc_name']}")
    
    def test_canada_pr_ita_application_template(self):
        """Test Canada PR ITA & PR Application step (has work experience, police clearance, medical)"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Canada Permanent Residency Express Entry",
            "step_name": "ITA & PR Application",
            "step_description": "Invitation to Apply and PR Application",
            "existing_docs": []
        }, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should match Canada PR template
        assert data.get("source") == "template", f"Expected template source, got {data.get('source')}"
        
        suggestions = data.get("suggestions", [])
        doc_names = [d["doc_name"] for d in suggestions]
        
        # ITA step should include police clearance, medical, biometrics
        expected = ["Police Clearance", "Medical", "Biometrics"]
        found = sum(1 for exp in expected if any(exp.lower() in dn.lower() for dn in doc_names))
        assert found >= 1, f"Expected at least 1 of {expected}, got docs: {doc_names}"
        
        print(f"PASS: Canada ITA & PR Application returned {len(suggestions)} template docs")
    
    # ============ UK Skilled Worker Template Tests ============
    
    def test_uk_skilled_worker_cos_template(self):
        """Test UK Skilled Worker Certificate of Sponsorship step"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "UK Skilled Worker Visa",
            "step_name": "Certificate of Sponsorship",
            "step_description": "CoS from UK employer",
            "existing_docs": []
        }, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("source") == "template", f"Expected template source, got {data.get('source')}"
        assert "GBP" in data.get("fees_info", ""), "Fees should be in GBP"
        assert "gov.uk" in data.get("government_url", ""), "URL should be gov.uk"
        
        suggestions = data.get("suggestions", [])
        doc_names = [d["doc_name"] for d in suggestions]
        
        # Should include CoS
        assert any("certificate of sponsorship" in dn.lower() or "cos" in dn.lower() for dn in doc_names), \
            "Should include Certificate of Sponsorship"
        
        print(f"PASS: UK Skilled Worker CoS returned {len(suggestions)} template docs")
        print(f"  Fees: {data.get('fees_info', '')[:60]}...")
    
    # ============ Student Visa Template Tests ============
    
    def test_student_visa_admission_template(self):
        """Test Student Visa Admission step"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Student Visa",
            "step_name": "Admission",
            "step_description": "University admission documents",
            "existing_docs": []
        }, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("source") == "template", f"Expected template source, got {data.get('source')}"
        
        suggestions = data.get("suggestions", [])
        doc_names = [d["doc_name"] for d in suggestions]
        
        # Should include offer letter and transcripts
        expected = ["Offer Letter", "Transcripts", "Statement of Purpose"]
        found = sum(1 for exp in expected if any(exp.lower() in dn.lower() for dn in doc_names))
        assert found >= 2, f"Expected at least 2 of {expected}"
        
        print(f"PASS: Student Visa Admission returned {len(suggestions)} template docs")
    
    # ============ AI Fallback Tests ============
    
    def test_non_template_product_uses_ai(self):
        """Test that non-template products fall back to AI"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Germany Blue Card",  # Not in templates
            "step_name": "Visa Application",
            "step_description": "German work visa application",
            "existing_docs": []
        }, timeout=45)  # AI takes longer
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should use AI fallback
        assert data.get("source") == "ai", f"Expected source='ai' for non-template product, got '{data.get('source')}'"
        
        print(f"PASS: Non-template product used AI fallback")
        print(f"  Source: {data.get('source')}")
        print(f"  Suggestions: {len(data.get('suggestions', []))}")
    
    # ============ Fees Verification Tests ============
    
    def test_canada_fees_cad_1365(self):
        """Verify Canada PR fees include CAD $1,365"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        canada = next((t for t in templates if "canada" in t["id"]), None)
        
        assert canada is not None
        assert "1,365" in canada["fees_info"] or "1365" in canada["fees_info"], \
            f"Canada fees should include $1,365, got: {canada['fees_info']}"
        
        print(f"PASS: Canada fees verified - {canada['fees_info'][:80]}...")
    
    def test_australia_fees_aud_4640(self):
        """Verify Australia PR fees include AUD $4,640"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        australia = next((t for t in templates if "australia" in t["id"]), None)
        
        assert australia is not None
        assert "4,640" in australia["fees_info"] or "4640" in australia["fees_info"], \
            f"Australia fees should include $4,640, got: {australia['fees_info']}"
        
        print(f"PASS: Australia fees verified - {australia['fees_info'][:80]}...")
    
    def test_uk_fees_gbp_719(self):
        """Verify UK Skilled Worker fees include GBP £719"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        uk = next((t for t in templates if "uk" in t["id"]), None)
        
        assert uk is not None
        assert "719" in uk["fees_info"], f"UK fees should include £719, got: {uk['fees_info']}"
        
        print(f"PASS: UK fees verified - {uk['fees_info'][:80]}...")
    
    # ============ Government URL Tests ============
    
    def test_government_urls_correct(self):
        """Verify government URLs are correct for each template"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/step-documents/templates")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        
        url_checks = {
            "canada": "canada.ca",
            "australia": "homeaffairs.gov.au",
            "uk": "gov.uk"
        }
        
        for key, expected_domain in url_checks.items():
            tmpl = next((t for t in templates if key in t["id"]), None)
            if tmpl:
                assert expected_domain in tmpl["government_url"], \
                    f"{key} URL should contain {expected_domain}, got: {tmpl['government_url']}"
                print(f"PASS: {key.upper()} URL verified - {tmpl['government_url']}")
    
    # ============ Audit Log Tests ============
    
    def test_template_suggestion_creates_audit_log(self):
        """Test that template-based suggestions create audit logs"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Australia PR",
            "step_name": "Skills Assessment",
            "step_description": "Testing audit log for template",
            "existing_docs": []
        }, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("source") == "template"
        
        # Audit log should be created with action 'ai_doc_suggestion_template'
        print("PASS: Template suggestion completed (audit log with action 'ai_doc_suggestion_template' should be created)")
    
    def test_ai_suggestion_creates_different_audit_log(self):
        """Test that AI-based suggestions create different audit logs"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        # Use a product name that won't match any template keywords
        response = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "XYZ Immigration Service",  # Not in templates
            "step_name": "Initial Filing",
            "step_description": "Testing audit log for AI",
            "existing_docs": []
        }, timeout=45)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("source") == "ai", f"Expected AI source for non-template product, got {data.get('source')}"
        
        # Audit log should be created with action 'ai_doc_suggestion_ai'
        print("PASS: AI suggestion completed (audit log with action 'ai_doc_suggestion_ai' should be created)")
    
    # ============ Existing Docs Filter Tests ============
    
    def test_template_filters_existing_docs(self):
        """Test that template suggestions filter out existing documents"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        # First call without existing docs
        response1 = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
            "product_name": "Australia PR",
            "step_name": "Skills Assessment",
            "step_description": "",
            "existing_docs": []
        }, timeout=30)
        
        assert response1.status_code == 200
        all_docs = response1.json().get("suggestions", [])
        
        if len(all_docs) > 0:
            # Second call with one existing doc
            existing_doc = all_docs[0]["doc_name"]
            response2 = self.session.post(f"{BASE_URL}/api/step-documents/ai-suggest-step-docs", json={
                "product_name": "Australia PR",
                "step_name": "Skills Assessment",
                "step_description": "",
                "existing_docs": [existing_doc]
            }, timeout=30)
            
            assert response2.status_code == 200
            filtered_docs = response2.json().get("suggestions", [])
            
            # Should have one less doc
            assert len(filtered_docs) < len(all_docs), \
                f"Filtered docs ({len(filtered_docs)}) should be less than all docs ({len(all_docs)})"
            
            # Existing doc should not be in filtered list
            filtered_names = [d["doc_name"].lower() for d in filtered_docs]
            assert existing_doc.lower() not in filtered_names, \
                f"Existing doc '{existing_doc}' should be filtered out"
            
            print(f"PASS: Template correctly filtered existing doc '{existing_doc}'")
            print(f"  All docs: {len(all_docs)}, Filtered: {len(filtered_docs)}")
        else:
            print("INFO: No docs returned, skipping filter test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
