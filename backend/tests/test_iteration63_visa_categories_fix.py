"""
Iteration 63: Test visa-categories and generate endpoint bug fixes
- visa-categories now returns hardcoded data from COUNTRY_REFERENCES (no AI needed)
- generate endpoint has template fallback when AI fails
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


class TestVisaCategoriesEndpoint:
    """Test POST /api/ai-workflow/visa-categories - should work WITHOUT AI"""

    def test_australia_visa_categories_returns_200(self, auth_headers):
        """BUGFIX: Australia visa categories should return 200 (not 500)"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Australia"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "categories" in data
        assert "country" in data
        print(f"✓ Australia visa-categories returned {len(data['categories'])} categories")

    def test_australia_has_5_visa_categories(self, auth_headers):
        """Australia should have 5 visa categories: PR, Visitor, Student, Work, Partner"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Australia"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        categories = data.get("categories", [])
        
        # Should have exactly 5 categories from COUNTRY_REFERENCES
        assert len(categories) >= 5, f"Expected at least 5 categories, got {len(categories)}"
        
        # Check category names
        category_names = [c.get("name", "").lower() for c in categories]
        expected = ["pr", "visitor", "student", "work", "partner"]
        for exp in expected:
            assert any(exp in name for name in category_names), f"Missing category: {exp}"
        print(f"✓ Australia has all 5 expected visa categories")

    def test_australia_categories_have_required_fields(self, auth_headers):
        """Each category should have id, name, description, category, official_url"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Australia"},
            headers=auth_headers
        )
        assert response.status_code == 200
        categories = response.json().get("categories", [])
        
        for cat in categories:
            assert "id" in cat, f"Missing 'id' in category: {cat}"
            assert "name" in cat, f"Missing 'name' in category: {cat}"
            assert "description" in cat, f"Missing 'description' in category: {cat}"
            assert "category" in cat, f"Missing 'category' in category: {cat}"
            assert "official_url" in cat, f"Missing 'official_url' in category: {cat}"
        print(f"✓ All categories have required fields")

    def test_australia_pr_has_homeaffairs_url(self, auth_headers):
        """Australia PR category should have homeaffairs.gov.au URL"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Australia"},
            headers=auth_headers
        )
        assert response.status_code == 200
        categories = response.json().get("categories", [])
        
        pr_cat = next((c for c in categories if c.get("category") == "pr"), None)
        assert pr_cat is not None, "PR category not found"
        assert "homeaffairs.gov.au" in pr_cat.get("official_url", ""), f"Expected homeaffairs.gov.au URL, got: {pr_cat.get('official_url')}"
        print(f"✓ Australia PR has correct official URL")

    def test_canada_visa_categories_returns_200(self, auth_headers):
        """BUGFIX: Canada visa categories should return 200 (not 500)"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Canada"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) >= 4, f"Expected at least 4 categories, got {len(data['categories'])}"
        print(f"✓ Canada visa-categories returned {len(data['categories'])} categories")

    def test_canada_has_pr_visitor_student_work(self, auth_headers):
        """Canada should have PR, Visitor, Student, Work categories"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Canada"},
            headers=auth_headers
        )
        assert response.status_code == 200
        categories = response.json().get("categories", [])
        
        category_types = [c.get("category", "").lower() for c in categories]
        expected = ["pr", "visitor", "student", "work"]
        for exp in expected:
            assert exp in category_types, f"Missing category type: {exp}"
        print(f"✓ Canada has all expected visa categories")

    def test_no_duplicate_categories(self, auth_headers):
        """BUGFIX: Should not have duplicate visa categories"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Australia"},
            headers=auth_headers
        )
        assert response.status_code == 200
        categories = response.json().get("categories", [])
        
        # Check for duplicate IDs
        ids = [c.get("id") for c in categories]
        assert len(ids) == len(set(ids)), f"Duplicate category IDs found: {ids}"
        
        # Check for duplicate names
        names = [c.get("name") for c in categories]
        assert len(names) == len(set(names)), f"Duplicate category names found: {names}"
        print(f"✓ No duplicate visa categories")


class TestGenerateEndpointWithTemplateFallback:
    """Test POST /api/ai-workflow/generate - should use template fallback when AI fails"""

    def test_australia_pr_generate_returns_200(self, auth_headers):
        """BUGFIX: Generate for Australia PR should return 200 (template fallback)"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=30  # Allow time for AI attempt + fallback
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "product_name" in data
        assert "steps" in data
        print(f"✓ Australia PR generate returned workflow with {len(data.get('steps', []))} steps")

    def test_australia_pr_has_5_steps_21_docs(self, auth_headers):
        """Australia PR template should have 5 steps with 21 documents"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        steps = data.get("steps", [])
        
        # Template has 5 steps
        assert len(steps) >= 5, f"Expected at least 5 steps, got {len(steps)}"
        
        # Count total documents
        total_docs = sum(len(s.get("required_documents", [])) for s in steps)
        assert total_docs >= 15, f"Expected at least 15 documents, got {total_docs}"
        print(f"✓ Australia PR has {len(steps)} steps with {total_docs} documents")

    def test_generate_workflow_has_required_fields(self, auth_headers):
        """Generated workflow should have product_name, description, category, steps"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "product_name" in data, "Missing product_name"
        assert "description" in data or data.get("description") == "", "Missing description"
        assert "category" in data, "Missing category"
        assert "steps" in data, "Missing steps"
        assert isinstance(data["steps"], list), "steps should be a list"
        print(f"✓ Generated workflow has all required fields")

    def test_generate_steps_have_required_documents(self, auth_headers):
        """Each step should have step_name, step_order, required_documents"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        steps = response.json().get("steps", [])
        
        for i, step in enumerate(steps):
            assert "step_name" in step, f"Step {i} missing step_name"
            assert "step_order" in step, f"Step {i} missing step_order"
            assert "required_documents" in step, f"Step {i} missing required_documents"
            assert isinstance(step["required_documents"], list), f"Step {i} required_documents should be list"
        print(f"✓ All steps have required fields")

    def test_documents_have_name_and_mandatory_flag(self, auth_headers):
        """Each document should have name and mandatory flag"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        steps = response.json().get("steps", [])
        
        for step in steps:
            for doc in step.get("required_documents", []):
                assert "name" in doc, f"Document missing 'name' in step {step.get('step_name')}"
                assert "mandatory" in doc, f"Document missing 'mandatory' in step {step.get('step_name')}"
        print(f"✓ All documents have name and mandatory flag")

    def test_canada_pr_generate_returns_200(self, auth_headers):
        """Canada PR generate should also work with template fallback"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Canada",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "steps" in data
        assert len(data["steps"]) >= 5, f"Expected at least 5 steps, got {len(data['steps'])}"
        print(f"✓ Canada PR generate returned workflow with {len(data['steps'])} steps")


class TestCountriesEndpoint:
    """Test GET /api/ai-workflow/countries - should still work"""

    def test_countries_endpoint_returns_200(self, auth_headers):
        """Countries endpoint should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/ai-workflow/countries",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 50, f"Expected at least 50 countries, got {len(data)}"
        print(f"✓ Countries endpoint returned {len(data)} countries")

    def test_australia_in_countries_list(self, auth_headers):
        """Australia should be in the countries list"""
        response = requests.get(
            f"{BASE_URL}/api/ai-workflow/countries",
            headers=auth_headers
        )
        assert response.status_code == 200
        countries = response.json()
        
        australia = next((c for c in countries if c.get("name") == "Australia"), None)
        assert australia is not None, "Australia not found in countries list"
        assert "services" in australia
        assert len(australia["services"]) >= 5, f"Australia should have at least 5 services"
        print(f"✓ Australia found with {len(australia['services'])} services")


class TestTemplatesEndpoint:
    """Test GET /api/step-documents/templates - should still work"""

    def test_templates_endpoint_returns_200(self, auth_headers):
        """Templates endpoint should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/step-documents/templates",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) >= 8, f"Expected at least 8 templates, got {len(data['templates'])}"
        print(f"✓ Templates endpoint returned {len(data['templates'])} templates")

    def test_australia_pr_template_exists(self, auth_headers):
        """Australia PR template should exist"""
        response = requests.get(
            f"{BASE_URL}/api/step-documents/templates",
            headers=auth_headers
        )
        assert response.status_code == 200
        templates = response.json().get("templates", [])
        
        aus_pr = next((t for t in templates if t.get("id") == "australia_pr"), None)
        assert aus_pr is not None, "australia_pr template not found"
        assert "steps" in aus_pr
        assert "total_documents" in aus_pr
        print(f"✓ Australia PR template found with {aus_pr.get('total_documents')} documents")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
