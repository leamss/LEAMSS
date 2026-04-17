"""
Iteration 62: AI Workflow Builder - 51 Countries + Editable Review View Tests
Tests:
- GET /api/ai-workflow/countries returns 51 countries sorted alphabetically
- POST /api/step-documents/ai-suggest-bulk returns template docs (no AI needed)
- POST /api/step-documents/ai-suggest-step-docs returns template source for known products
- GET /api/step-documents/templates returns 8 verified templates
- POST /api/ai-workflow/save saves workflow as product
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(admin_token):
    """Auth headers for admin requests"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestCountriesAPI:
    """Test GET /api/ai-workflow/countries endpoint"""
    
    def test_countries_endpoint_returns_51_countries(self, auth_headers):
        """Verify endpoint returns exactly 51 countries"""
        response = requests.get(f"{BASE_URL}/api/ai-workflow/countries", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        countries = response.json()
        assert isinstance(countries, list), "Response should be a list"
        assert len(countries) == 51, f"Expected 51 countries, got {len(countries)}"
    
    def test_countries_sorted_alphabetically(self, auth_headers):
        """Verify countries are sorted alphabetically by name"""
        response = requests.get(f"{BASE_URL}/api/ai-workflow/countries", headers=auth_headers)
        assert response.status_code == 200
        
        countries = response.json()
        names = [c["name"] for c in countries]
        assert names == sorted(names), "Countries should be sorted alphabetically"
    
    def test_countries_have_required_fields(self, auth_headers):
        """Verify each country has id, name, and services"""
        response = requests.get(f"{BASE_URL}/api/ai-workflow/countries", headers=auth_headers)
        assert response.status_code == 200
        
        countries = response.json()
        for country in countries:
            assert "id" in country, f"Country missing 'id': {country}"
            assert "name" in country, f"Country missing 'name': {country}"
            assert "services" in country, f"Country missing 'services': {country}"
            assert isinstance(country["services"], list), f"Services should be a list: {country}"
    
    def test_expected_countries_present(self, auth_headers):
        """Verify all 51 expected countries are present"""
        expected_countries = [
            "Argentina", "Australia", "Austria", "Bahrain", "Belgium", "Brazil", "Canada",
            "Chile", "China", "Colombia", "Costa Rica", "Czech Republic", "Denmark", "Egypt",
            "Finland", "France", "Germany", "Greece", "Hong Kong", "India", "Indonesia",
            "Ireland", "Italy", "Japan", "Kenya", "Malaysia", "Mauritius", "Mexico",
            "Netherlands", "New Zealand", "Nigeria", "Norway", "Oman", "Panama", "Philippines",
            "Poland", "Portugal", "Qatar", "Saudi Arabia", "Singapore", "South Africa",
            "South Korea", "Spain", "Sweden", "Switzerland", "Thailand", "Turkey", "Uae",
            "Uk", "Usa", "Vietnam"
        ]
        
        response = requests.get(f"{BASE_URL}/api/ai-workflow/countries", headers=auth_headers)
        assert response.status_code == 200
        
        countries = response.json()
        country_names = [c["name"] for c in countries]
        
        for expected in expected_countries:
            assert expected in country_names, f"Missing country: {expected}"


class TestTemplatesAPI:
    """Test GET /api/step-documents/templates endpoint"""
    
    def test_templates_endpoint_returns_8_templates(self, auth_headers):
        """Verify endpoint returns exactly 8 templates"""
        response = requests.get(f"{BASE_URL}/api/step-documents/templates", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "templates" in data, "Response should have 'templates' key"
        templates = data["templates"]
        assert len(templates) == 8, f"Expected 8 templates, got {len(templates)}"
    
    def test_templates_have_required_fields(self, auth_headers):
        """Verify each template has required fields"""
        response = requests.get(f"{BASE_URL}/api/step-documents/templates", headers=auth_headers)
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        required_fields = ["id", "label", "steps", "total_documents"]
        
        for tmpl in templates:
            for field in required_fields:
                assert field in tmpl, f"Template {tmpl.get('id', 'unknown')} missing '{field}'"
    
    def test_template_ids_present(self, auth_headers):
        """Verify expected template IDs are present"""
        expected_ids = [
            "canada_pr", "australia_pr", "uk_skilled_worker", "student_visa_generic",
            "nz_skilled_migrant", "usa_h1b", "uae_golden_visa", "singapore_ep"
        ]
        
        response = requests.get(f"{BASE_URL}/api/step-documents/templates", headers=auth_headers)
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        for expected_id in expected_ids:
            assert expected_id in template_ids, f"Missing template: {expected_id}"


class TestAISuggestBulkAPI:
    """Test POST /api/step-documents/ai-suggest-bulk endpoint (template-based, no AI)"""
    
    def test_ai_suggest_bulk_australia_pr(self, auth_headers):
        """Test template-based suggestion for Australia PR"""
        payload = {
            "product_name": "Australia PR - Skilled Migration",
            "steps": [
                {"step_name": "Skills Assessment"},
                {"step_name": "Language Testing"},
                {"step_name": "EOI Submission"},
                {"step_name": "Visa Application"},
                {"step_name": "Decision & Grant"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/step-documents/ai-suggest-bulk",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "suggestions" in data, "Response should have 'suggestions'"
        assert "source" in data, "Response should have 'source'"
        assert data["source"] == "template", f"Expected source='template', got {data['source']}"
        
        # Verify suggestions for each step
        suggestions = data["suggestions"]
        assert len(suggestions) > 0, "Should have suggestions for at least one step"
    
    def test_ai_suggest_bulk_canada_pr(self, auth_headers):
        """Test template-based suggestion for Canada PR"""
        payload = {
            "product_name": "Canada PR - Express Entry",
            "steps": [
                {"step_name": "Profile Creation"},
                {"step_name": "Education Credential Assessment"},
                {"step_name": "Language Testing"},
                {"step_name": "Express Entry Profile"},
                {"step_name": "ITA & PR Application"},
                {"step_name": "Final Review"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/step-documents/ai-suggest-bulk",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["source"] == "template", f"Expected source='template', got {data['source']}"
        assert "fees_info" in data, "Response should have 'fees_info'"
        assert "CAD" in data.get("fees_info", ""), "Canada PR should have CAD fees"
    
    def test_ai_suggest_bulk_returns_documents(self, auth_headers):
        """Verify suggestions contain actual document objects"""
        payload = {
            "product_name": "UK Skilled Worker Visa",
            "steps": [
                {"step_name": "Certificate of Sponsorship"},
                {"step_name": "English Language"},
                {"step_name": "Visa Application"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/step-documents/ai-suggest-bulk",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        suggestions = data.get("suggestions", {})
        
        # Check at least one step has documents
        has_docs = False
        for step_name, docs in suggestions.items():
            if docs and len(docs) > 0:
                has_docs = True
                # Verify document structure
                for doc in docs:
                    assert "doc_name" in doc, f"Document missing 'doc_name': {doc}"
                    assert "is_mandatory" in doc, f"Document missing 'is_mandatory': {doc}"
                break
        
        assert has_docs, "Should have documents for at least one step"


class TestAISuggestStepDocsAPI:
    """Test POST /api/step-documents/ai-suggest-step-docs endpoint"""
    
    def test_ai_suggest_step_docs_returns_template_source(self, auth_headers):
        """Test that known products return template source"""
        payload = {
            "product_name": "Australia PR - Skilled Migration",
            "step_name": "Skills Assessment",
            "step_description": "Skills assessment by relevant authority",
            "existing_docs": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/step-documents/ai-suggest-step-docs",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "suggestions" in data, "Response should have 'suggestions'"
        assert "source" in data, "Response should have 'source'"
        # For known templates, source should be 'template'
        assert data["source"] == "template", f"Expected source='template', got {data['source']}"


class TestWorkflowSaveAPI:
    """Test POST /api/ai-workflow/save endpoint"""
    
    def test_save_workflow_as_product(self, auth_headers):
        """Test saving a workflow as a product"""
        import uuid
        unique_name = f"TEST_Workflow_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "product_name": unique_name,
            "description": "Test workflow for iteration 62",
            "category": "immigration",
            "base_fee": 0,
            "commission_rate": 10,
            "steps": [
                {
                    "step_name": "Test Step 1",
                    "step_order": 1,
                    "description": "First test step",
                    "duration_days": 14,
                    "required_documents": [
                        {"name": "Test Document", "description": "Test doc", "mandatory": True}
                    ]
                },
                {
                    "step_name": "Test Step 2",
                    "step_order": 2,
                    "description": "Second test step",
                    "duration_days": 7,
                    "required_documents": []
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/save",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "product_id" in data, "Response should have 'product_id'"
        assert "steps_created" in data, "Response should have 'steps_created'"
        assert data["steps_created"] == 2, f"Expected 2 steps created, got {data['steps_created']}"


class TestCountryDetails:
    """Test specific country details in the countries list"""
    
    def test_australia_has_services(self, auth_headers):
        """Verify Australia has expected service types"""
        response = requests.get(f"{BASE_URL}/api/ai-workflow/countries", headers=auth_headers)
        assert response.status_code == 200
        
        countries = response.json()
        australia = next((c for c in countries if c["name"] == "Australia"), None)
        assert australia is not None, "Australia should be in the list"
        
        service_ids = [s["id"] for s in australia["services"]]
        expected_services = ["pr", "visitor", "student", "work", "partner"]
        for svc in expected_services:
            assert svc in service_ids, f"Australia missing service: {svc}"
    
    def test_canada_has_services(self, auth_headers):
        """Verify Canada has expected service types"""
        response = requests.get(f"{BASE_URL}/api/ai-workflow/countries", headers=auth_headers)
        assert response.status_code == 200
        
        countries = response.json()
        canada = next((c for c in countries if c["name"] == "Canada"), None)
        assert canada is not None, "Canada should be in the list"
        
        service_ids = [s["id"] for s in canada["services"]]
        expected_services = ["pr", "visitor", "student", "work"]
        for svc in expected_services:
            assert svc in service_ids, f"Canada missing service: {svc}"
    
    def test_first_country_is_argentina(self, auth_headers):
        """Verify first country alphabetically is Argentina"""
        response = requests.get(f"{BASE_URL}/api/ai-workflow/countries", headers=auth_headers)
        assert response.status_code == 200
        
        countries = response.json()
        assert countries[0]["name"] == "Argentina", f"First country should be Argentina, got {countries[0]['name']}"
    
    def test_last_country_is_vietnam(self, auth_headers):
        """Verify last country alphabetically is Vietnam"""
        response = requests.get(f"{BASE_URL}/api/ai-workflow/countries", headers=auth_headers)
        assert response.status_code == 200
        
        countries = response.json()
        assert countries[-1]["name"] == "Vietnam", f"Last country should be Vietnam, got {countries[-1]['name']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
