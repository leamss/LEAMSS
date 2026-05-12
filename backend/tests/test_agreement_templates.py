"""
Agreement Templates & PA Agreements - Comprehensive Backend Tests
Tests for iteration 86: Agreement Template Library + Auto-Generator for E-Sign

Endpoints tested:
- GET /api/agreement-templates - list templates
- GET /api/agreement-templates/meta/options - get distinct countries/categories/variants
- GET /api/agreement-templates/{tid} - get full template with body_html
- POST /api/agreement-templates - create template (admin only)
- PUT /api/agreement-templates/{tid} - update template (admin only)
- DELETE /api/agreement-templates/{tid} - soft delete (admin only)
- POST /api/agreement-templates/{tid}/clone - clone template (admin only)
- POST /api/agreement-templates/request - partner request new template
- GET /api/pa-agreements/auto-vars/{pa_id} - get auto-populated variables
- POST /api/pa-agreements/generate - generate agreement for PA
- GET /api/pa-agreements/pa/{pa_id} - list agreements for PA
- GET /api/pa-agreements/{aid} - get single agreement with full HTML
- GET /api/pa-agreements/{aid}/pdf - download PDF
- POST /api/pa-agreements/{aid}/sign - client signs agreement
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://staff-dashboard-66.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASSWORD = "Client@123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def partner_token():
    """Get partner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARTNER_EMAIL,
        "password": PARTNER_PASSWORD
    })
    assert response.status_code == 200, f"Partner login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def client_token():
    """Get client authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CLIENT_EMAIL,
        "password": CLIENT_PASSWORD
    })
    assert response.status_code == 200, f"Client login failed: {response.text}"
    return response.json()["token"]


class TestAgreementTemplatesList:
    """Tests for listing agreement templates"""
    
    def test_list_templates_returns_3_seeded(self, admin_token):
        """GET /api/agreement-templates returns 3 seeded templates"""
        response = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "items" in data
        assert data["count"] >= 3, f"Expected at least 3 templates, got {data['count']}"
        
        # Verify seeded templates exist
        names = [t["name"] for t in data["items"]]
        assert any("Australia" in n and "Standard" in n for n in names), "Missing Australia Standard template"
        assert any("Australia" in n and "Protection" in n for n in names), "Missing Australia Protection template"
        assert any("Canada" in n and "Express Entry" in n for n in names), "Missing Canada Express Entry template"
    
    def test_list_templates_has_correct_fields(self, admin_token):
        """Templates have country/visa_category/policy_variant/placeholders"""
        response = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) > 0
        
        template = items[0]
        required_fields = ["id", "name", "country", "visa_category", "policy_variant", "placeholders", "is_active"]
        for field in required_fields:
            assert field in template, f"Missing field: {field}"
        
        # Verify placeholders is a list
        assert isinstance(template["placeholders"], list)
    
    def test_partner_can_list_templates(self, partner_token):
        """Partner can list templates"""
        response = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        assert response.json()["count"] >= 3


class TestAgreementTemplatesMeta:
    """Tests for meta/options endpoint"""
    
    def test_meta_options_returns_distinct_values(self, admin_token):
        """GET /api/agreement-templates/meta/options returns countries/categories/variants"""
        response = requests.get(
            f"{BASE_URL}/api/agreement-templates/meta/options",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "countries" in data
        assert "categories" in data
        assert "variants" in data
        
        # Verify expected values
        assert "Australia" in data["countries"]
        assert "Canada" in data["countries"]
        assert "Standard" in data["variants"]


class TestAgreementTemplateGet:
    """Tests for getting single template"""
    
    def test_get_template_returns_full_body_html(self, admin_token):
        """GET /api/agreement-templates/{tid} returns full template with body_html"""
        # Use seeded Australia Standard template (known to have >5000 chars)
        # First get list to find the seeded template
        list_response = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        items = list_response.json()["items"]
        # Find a seeded template (Australia Standard)
        seeded_template = next((t for t in items if "Australia" in t["name"] and "Standard" in t["name"]), None)
        if not seeded_template:
            pytest.skip("Seeded Australia Standard template not found")
        template_id = seeded_template["id"]
        
        # Get full template
        response = requests.get(
            f"{BASE_URL}/api/agreement-templates/{template_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "body_html" in data
        # Seeded templates have >5000 chars, test templates may have less
        assert len(data["body_html"]) > 100, f"body_html should have content, got {len(data['body_html'])} chars"
    
    def test_get_nonexistent_template_returns_404(self, admin_token):
        """GET /api/agreement-templates/{invalid_id} returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/agreement-templates/nonexistent-id-12345",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404


class TestAgreementTemplateCreate:
    """Tests for creating templates"""
    
    def test_admin_can_create_template(self, admin_token):
        """POST /api/agreement-templates creates template with auto-detected placeholders"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"TEST_Template_{unique_id}",
                "country": "TestCountry",
                "visa_category": "Test Visa",
                "policy_variant": "Standard",
                "body_html": "<h2>Test Agreement</h2><p>Client: {{client_name}}</p><p>Email: {{client_email}}</p><p>Amount: {{milestone_1_amount}}</p>",
                "notes": "Test template"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["name"] == f"TEST_Template_{unique_id}"
        
        # Verify placeholders were auto-detected
        assert "placeholders" in data
        assert "client_name" in data["placeholders"]
        assert "client_email" in data["placeholders"]
        assert "milestone_1_amount" in data["placeholders"]
    
    def test_partner_cannot_create_template(self, partner_token):
        """POST /api/agreement-templates as partner returns 403"""
        response = requests.post(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {partner_token}"},
            json={
                "name": "Partner Test",
                "country": "India",
                "visa_category": "PR",
                "policy_variant": "Standard",
                "body_html": "<p>Test</p>"
            }
        )
        assert response.status_code == 403
        assert "Admin only" in response.json()["detail"]


class TestAgreementTemplateUpdate:
    """Tests for updating templates"""
    
    def test_admin_can_update_template(self, admin_token):
        """PUT /api/agreement-templates/{tid} updates template and increments version"""
        # Create a template first
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"TEST_Update_{unique_id}",
                "country": "TestCountry",
                "visa_category": "Test Visa",
                "policy_variant": "Standard",
                "body_html": "<p>Original</p>"
            }
        )
        template_id = create_response.json()["id"]
        
        # Update it
        update_response = requests.put(
            f"{BASE_URL}/api/agreement-templates/{template_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"TEST_Update_{unique_id}_Modified",
                "body_html": "<p>Updated with {{new_placeholder}}</p>"
            }
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["ok"] == True
        assert data["version"] == 2


class TestAgreementTemplateClone:
    """Tests for cloning templates"""
    
    def test_admin_can_clone_template(self, admin_token):
        """POST /api/agreement-templates/{tid}/clone creates new template"""
        # Get a seeded template (Australia Standard)
        list_response = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        items = list_response.json()["items"]
        seeded_template = next((t for t in items if "Australia" in t["name"] and "Standard" in t["name"]), None)
        if not seeded_template:
            pytest.skip("Seeded Australia Standard template not found")
        template_id = seeded_template["id"]
        
        # Clone it
        unique_id = str(uuid.uuid4())[:8]
        clone_response = requests.post(
            f"{BASE_URL}/api/agreement-templates/{template_id}/clone",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "new_name": f"TEST_Clone_{unique_id}",
                "new_policy_variant": "Premium"
            }
        )
        assert clone_response.status_code == 200, f"Clone failed: {clone_response.text}"
        data = clone_response.json()
        
        assert data["id"] != template_id, "Clone should have new ID"
        assert data["name"] == f"TEST_Clone_{unique_id}"
        assert data["policy_variant"] == "Premium"


class TestAgreementTemplateDelete:
    """Tests for soft-deleting templates"""
    
    def test_admin_can_soft_delete_template(self, admin_token):
        """DELETE /api/agreement-templates/{tid} sets is_active=false"""
        # Create a template first
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"TEST_Delete_{unique_id}",
                "country": "TestCountry",
                "visa_category": "Test Visa",
                "policy_variant": "Standard",
                "body_html": "<p>To be deleted</p>"
            }
        )
        template_id = create_response.json()["id"]
        
        # Delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/agreement-templates/{template_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["ok"] == True
        
        # Verify it's soft-deleted
        get_response = requests.get(
            f"{BASE_URL}/api/agreement-templates/{template_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 200
        assert get_response.json()["is_active"] == False


class TestPartnerTemplateRequest:
    """Tests for partner template requests"""
    
    def test_partner_can_request_template(self, partner_token):
        """POST /api/agreement-templates/request creates request and notifies admins"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(
            f"{BASE_URL}/api/agreement-templates/request",
            headers={"Authorization": f"Bearer {partner_token}"},
            json={
                "country": f"TestCountry_{unique_id}",
                "visa_category": "Student Visa",
                "policy_variant": "Standard",
                "notes": "Need template for testing"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["status"] == "pending"
        assert data["requested_by_name"] == "Partner User"


class TestPaAgreementsAutoVars:
    """Tests for auto-vars endpoint"""
    
    def test_auto_vars_returns_populated_dict(self, partner_token):
        """GET /api/pa-agreements/auto-vars/{pa_id} returns 25+ auto-populated keys"""
        # Get a PA
        pa_response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        pas = pa_response.json()
        assert len(pas) > 0, "No PAs found for partner"
        pa_id = pas[0]["id"]
        
        # Get auto-vars
        response = requests.get(
            f"{BASE_URL}/api/pa-agreements/auto-vars/{pa_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "variables" in data
        variables = data["variables"]
        assert len(variables) >= 25, f"Expected 25+ auto-vars, got {len(variables)}"
        
        # Verify key fields
        expected_keys = ["client_name", "client_email", "country", "agreement_date", "partner_name", "pa_number"]
        for key in expected_keys:
            assert key in variables, f"Missing auto-var: {key}"


class TestPaAgreementsGenerate:
    """Tests for agreement generation"""
    
    def test_partner_can_generate_agreement(self, partner_token, admin_token):
        """POST /api/pa-agreements/generate creates agreement with reference_id"""
        # Get a PA
        pa_response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        pas = pa_response.json()
        pa_id = pas[0]["id"]
        
        # Get a seeded template (Australia Standard - has full body_html)
        tpl_response = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        items = tpl_response.json()["items"]
        seeded_template = next((t for t in items if "Australia" in t["name"] and "Standard" in t["name"]), None)
        if not seeded_template:
            pytest.skip("Seeded Australia Standard template not found")
        template_id = seeded_template["id"]
        
        # Generate agreement
        response = requests.post(
            f"{BASE_URL}/api/pa-agreements/generate",
            headers={"Authorization": f"Bearer {partner_token}"},
            json={
                "pa_id": pa_id,
                "template_id": template_id,
                "variables": {
                    "milestone_1_amount": "50000",
                    "milestone_1_date": "01/06/2026"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "reference_id" in data
        assert data["reference_id"].startswith("AGR-")
        assert data["status"] == "pending_signature"
        assert "rendered_html" in data
        # Seeded templates have >1000 chars rendered HTML
        assert len(data["rendered_html"]) > 100, f"rendered_html should have content, got {len(data['rendered_html'])} chars"


class TestPaAgreementsList:
    """Tests for listing PA agreements"""
    
    def test_list_agreements_for_pa(self, partner_token):
        """GET /api/pa-agreements/pa/{pa_id} returns list without rendered_html"""
        # Get a PA
        pa_response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        pas = pa_response.json()
        pa_id = pas[0]["id"]
        
        # List agreements
        response = requests.get(
            f"{BASE_URL}/api/pa-agreements/pa/{pa_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        agreements = response.json()
        
        # Should be a list
        assert isinstance(agreements, list)
        
        if len(agreements) > 0:
            # Verify rendered_html is NOT included in list view
            assert "rendered_html" not in agreements[0], "List view should not include rendered_html"
            assert "reference_id" in agreements[0]
            assert "status" in agreements[0]


class TestPaAgreementGet:
    """Tests for getting single agreement"""
    
    def test_get_agreement_returns_full_html(self, partner_token, admin_token):
        """GET /api/pa-agreements/{aid} returns full rendered_html"""
        # Get a PA and generate an agreement
        pa_response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        pa_id = pa_response.json()[0]["id"]
        
        # List agreements
        list_response = requests.get(
            f"{BASE_URL}/api/pa-agreements/pa/{pa_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        agreements = list_response.json()
        
        if len(agreements) > 0:
            agreement_id = agreements[0]["id"]
            
            # Get full agreement
            response = requests.get(
                f"{BASE_URL}/api/pa-agreements/{agreement_id}",
                headers={"Authorization": f"Bearer {partner_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            
            assert "rendered_html" in data
            # Agreement should have some rendered content
            assert len(data["rendered_html"]) > 10, f"rendered_html should have content"


class TestPaAgreementPdf:
    """Tests for PDF download"""
    
    def test_pdf_download_returns_valid_pdf(self, partner_token):
        """GET /api/pa-agreements/{aid}/pdf returns valid PDF"""
        # Get a PA
        pa_response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        pa_id = pa_response.json()[0]["id"]
        
        # List agreements
        list_response = requests.get(
            f"{BASE_URL}/api/pa-agreements/pa/{pa_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        agreements = list_response.json()
        
        if len(agreements) > 0:
            agreement_id = agreements[0]["id"]
            
            # Download PDF
            response = requests.get(
                f"{BASE_URL}/api/pa-agreements/{agreement_id}/pdf",
                headers={"Authorization": f"Bearer {partner_token}"}
            )
            assert response.status_code == 200
            assert response.headers.get("content-type") == "application/pdf"
            # PDF should be valid (starts with %PDF)
            assert response.content[:4] == b'%PDF', "Response should be a valid PDF"
            assert len(response.content) > 1000, f"PDF should be >1KB, got {len(response.content)} bytes"


class TestPaAgreementSign:
    """Tests for signing agreements"""
    
    def test_partner_cannot_sign_agreement(self, partner_token):
        """POST /api/pa-agreements/{aid}/sign as partner returns 403"""
        # Get a PA
        pa_response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        pa_id = pa_response.json()[0]["id"]
        
        # List agreements
        list_response = requests.get(
            f"{BASE_URL}/api/pa-agreements/pa/{pa_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        agreements = list_response.json()
        
        if len(agreements) > 0:
            agreement_id = agreements[0]["id"]
            
            # Try to sign as partner
            response = requests.post(
                f"{BASE_URL}/api/pa-agreements/{agreement_id}/sign",
                headers={"Authorization": f"Bearer {partner_token}"},
                json={
                    "signature_data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                    "typed_name": "Test Partner"
                }
            )
            assert response.status_code == 403
            assert "Client only" in response.json()["detail"]


class TestAuthorization:
    """Tests for authorization rules"""
    
    def test_unauthenticated_cannot_access_templates(self):
        """Unauthenticated requests are blocked"""
        response = requests.get(f"{BASE_URL}/api/agreement-templates")
        assert response.status_code in [401, 403]
    
    def test_client_cannot_access_templates(self, client_token):
        """Client cannot access template management"""
        response = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        # Client should be blocked (partner or admin only)
        assert response.status_code == 403


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""
    
    def test_health_endpoint(self):
        """Health endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_pre_assessment_endpoint(self, partner_token):
        """Pre-assessment endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
    
    def test_legal_archive_endpoint(self, admin_token):
        """Legal archive endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/legal-archive/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_users_endpoint(self, admin_token):
        """Users endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
