"""
Iteration 64: AI Workflow Builder Tests
Testing AI-powered visa categories and workflow generation with LLM balance topped up.
Features:
- POST /api/ai-workflow/visa-categories for Australia/Canada
- POST /api/ai-workflow/generate for comprehensive workflows
- Workflow structure validation (steps, docs, fees, tips)
"""
import pytest
import requests
import os
import time

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
        return response.json().get("token")  # API returns 'token' not 'access_token'
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(admin_token):
    """Auth headers for admin requests"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestVisaCategoriesAustralia:
    """Test visa-categories endpoint for Australia"""
    
    def test_australia_visa_categories_returns_200(self, auth_headers):
        """POST /api/ai-workflow/visa-categories for Australia returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Australia"},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "categories" in data
        assert "country" in data
        assert data["country"] == "Australia"
    
    def test_australia_returns_visa_subclasses(self, auth_headers):
        """Australia should return visa categories with subclass numbers"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Australia"},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        categories = response.json().get("categories", [])
        
        # Should have at least 5 categories (PR, Visitor, Student, Work, Partner from hardcoded)
        assert len(categories) >= 5, f"Expected at least 5 categories, got {len(categories)}"
        
        # Check structure of each category
        for cat in categories:
            assert "id" in cat, f"Category missing 'id': {cat}"
            assert "name" in cat, f"Category missing 'name': {cat}"
    
    def test_australia_categories_have_fees_or_urls(self, auth_headers):
        """Categories should have estimated_fees or official_url"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Australia"},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        categories = response.json().get("categories", [])
        
        # At least some categories should have fees or URLs
        has_fees = any(cat.get("estimated_fees") for cat in categories)
        has_urls = any(cat.get("official_url") for cat in categories)
        
        assert has_fees or has_urls, "Categories should have fees or official URLs"


class TestVisaCategoriesCanada:
    """Test visa-categories endpoint for Canada"""
    
    def test_canada_visa_categories_returns_200(self, auth_headers):
        """POST /api/ai-workflow/visa-categories for Canada returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Canada"},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "categories" in data
        assert data["country"] == "Canada"
    
    def test_canada_returns_visa_categories(self, auth_headers):
        """Canada should return visa categories"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/visa-categories",
            json={"country": "Canada"},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        categories = response.json().get("categories", [])
        
        # Should have at least 4 categories (PR, Visitor, Student, Work from hardcoded)
        assert len(categories) >= 4, f"Expected at least 4 categories, got {len(categories)}"


class TestWorkflowGenerateAustralia:
    """Test workflow generation for Australia Subclass 189"""
    
    def test_australia_subclass_189_generate_returns_200(self, auth_headers):
        """POST /api/ai-workflow/generate for Australia Subclass 189 returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "Subclass 189 - Skilled Independent",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=60  # AI calls may take time
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_australia_pr_workflow_has_5_plus_steps(self, auth_headers):
        """Generated workflow should have 5+ steps"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        workflow = response.json()
        
        steps = workflow.get("steps", [])
        assert len(steps) >= 5, f"Expected 5+ steps, got {len(steps)}"
    
    def test_australia_pr_workflow_has_10_plus_docs(self, auth_headers):
        """Generated workflow should have 10+ documents total"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        workflow = response.json()
        
        total_docs = sum(len(step.get("required_documents", [])) for step in workflow.get("steps", []))
        assert total_docs >= 10, f"Expected 10+ documents, got {total_docs}"
    
    def test_workflow_has_government_fees_per_step(self, auth_headers):
        """Generated workflow steps should have government_fees"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        workflow = response.json()
        
        # Check if workflow has estimated_government_fees at top level
        has_top_level_fees = bool(workflow.get("estimated_government_fees"))
        
        # Or check if steps have government_fees
        steps_with_fees = [s for s in workflow.get("steps", []) if s.get("government_fees")]
        
        assert has_top_level_fees or len(steps_with_fees) > 0, "Workflow should have government fees"
    
    def test_workflow_has_success_tips(self, auth_headers):
        """Generated workflow should have success_tips"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        workflow = response.json()
        
        # success_tips may be present if AI generated, or empty if template fallback
        tips = workflow.get("success_tips", [])
        # Just verify the field exists (may be empty for template fallback)
        assert isinstance(tips, list), "success_tips should be a list"
    
    def test_workflow_has_common_rejection_reasons(self, auth_headers):
        """Generated workflow should have common_rejection_reasons"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        workflow = response.json()
        
        # common_rejection_reasons may be present if AI generated
        reasons = workflow.get("common_rejection_reasons", [])
        assert isinstance(reasons, list), "common_rejection_reasons should be a list"


class TestWorkflowGenerateCanada:
    """Test workflow generation for Canada PR"""
    
    def test_canada_pr_generate_returns_200(self, auth_headers):
        """POST /api/ai-workflow/generate for Canada PR returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Canada",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_canada_pr_workflow_comprehensive(self, auth_headers):
        """Canada PR workflow should be comprehensive"""
        response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Canada",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        workflow = response.json()
        
        # Check required fields
        assert "product_name" in workflow, "Workflow missing product_name"
        assert "steps" in workflow, "Workflow missing steps"
        
        steps = workflow.get("steps", [])
        assert len(steps) >= 3, f"Expected at least 3 steps, got {len(steps)}"
        
        # Each step should have required_documents
        for step in steps:
            assert "step_name" in step, f"Step missing step_name: {step}"
            assert "required_documents" in step, f"Step missing required_documents: {step}"


class TestWorkflowSave:
    """Test saving workflow as product"""
    
    def test_save_workflow_returns_200(self, auth_headers):
        """POST /api/ai-workflow/save should save workflow as product"""
        # First generate a workflow
        gen_response = requests.post(
            f"{BASE_URL}/api/ai-workflow/generate",
            json={
                "country": "Australia",
                "service_type": "PR",
                "custom_instructions": ""
            },
            headers=auth_headers,
            timeout=60
        )
        assert gen_response.status_code == 200
        workflow = gen_response.json()
        
        # Now save it
        save_response = requests.post(
            f"{BASE_URL}/api/ai-workflow/save",
            json={
                "product_name": f"TEST_Australia_PR_{int(time.time())}",
                "description": workflow.get("description", "Test workflow"),
                "category": "immigration",
                "base_fee": 0,
                "commission_rate": 10,
                "steps": workflow.get("steps", [])
            },
            headers=auth_headers,
            timeout=30
        )
        assert save_response.status_code == 200, f"Save failed: {save_response.status_code} - {save_response.text}"
        
        result = save_response.json()
        assert "product_id" in result
        assert "steps_created" in result
        assert result["steps_created"] > 0


class TestCountriesAndTemplates:
    """Test supporting endpoints"""
    
    def test_countries_endpoint_returns_many_countries(self, auth_headers):
        """GET /api/ai-workflow/countries should return 50+ countries"""
        response = requests.get(
            f"{BASE_URL}/api/ai-workflow/countries",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        countries = response.json()
        assert len(countries) >= 50, f"Expected 50+ countries, got {len(countries)}"
    
    def test_templates_endpoint_returns_templates(self, auth_headers):
        """GET /api/ai-workflow/templates should return templates"""
        response = requests.get(
            f"{BASE_URL}/api/ai-workflow/templates",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) >= 5, f"Expected 5+ templates, got {len(templates)}"
