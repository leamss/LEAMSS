"""
Iteration 70: Intake Form Builder & Role-Based Form Filler Tests
Tests:
1. Admin creates intake form for a product (POST /api/intake-forms/save)
2. Get intake form for a product (GET /api/intake-forms/product/{product_id})
3. Get case intake form with role-based editable flags (GET /api/intake-forms/case/{case_id})
4. Save case intake data respecting role permissions (POST /api/intake-forms/case/save)
5. Role-based field editability (client vs cm vs admin)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
CM_EMAIL = "manager@leamss.com"
CM_PASSWORD = "Manager@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASSWORD = "Client@123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def cm_token():
    """Get case manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CM_EMAIL,
        "password": CM_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"CM authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def client_token():
    """Get client authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CLIENT_EMAIL,
        "password": CLIENT_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Client authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def client_case_id(client_token):
    """Get client's case ID"""
    response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers={
        "Authorization": f"Bearer {client_token}"
    })
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0]["id"]
    pytest.skip("No client case found")


@pytest.fixture(scope="module")
def canada_pr_product_id(admin_token):
    """Get Canada PR product ID"""
    response = requests.get(f"{BASE_URL}/api/products", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    if response.status_code == 200:
        products = response.json()
        for p in products:
            if "canada" in p.get("name", "").lower() and "pr" in p.get("name", "").lower():
                return p["id"]
        # Return first product if Canada PR not found
        if products:
            return products[0]["id"]
    pytest.skip("No products found")


class TestIntakeFormBuilder:
    """Test Admin Intake Form Builder APIs"""

    def test_admin_can_save_intake_form(self, admin_token, canada_pr_product_id):
        """Admin can create/update intake form for a product"""
        payload = {
            "product_id": canada_pr_product_id,
            "product_name": "Canada PR",
            "sections": [
                {
                    "id": "section_personal",
                    "title": "Personal Information",
                    "fields": [
                        {"key": "full_name", "label": "Full Name", "field_type": "text", "filled_by": "client", "required": True},
                        {"key": "date_of_birth", "label": "Date of Birth", "field_type": "date", "filled_by": "client", "required": True},
                        {"key": "passport_number", "label": "Passport Number", "field_type": "text", "filled_by": "client", "required": True},
                        {"key": "nationality", "label": "Nationality", "field_type": "text", "filled_by": "client", "required": False}
                    ]
                },
                {
                    "id": "section_language",
                    "title": "Language Scores",
                    "fields": [
                        {"key": "ielts_listening", "label": "IELTS Listening", "field_type": "text", "filled_by": "client", "required": False},
                        {"key": "ielts_reading", "label": "IELTS Reading", "field_type": "text", "filled_by": "client", "required": False},
                        {"key": "ielts_writing", "label": "IELTS Writing", "field_type": "text", "filled_by": "client", "required": False},
                        {"key": "ielts_speaking", "label": "IELTS Speaking", "field_type": "text", "filled_by": "client", "required": False},
                        {"key": "ielts_overall", "label": "IELTS Overall", "field_type": "text", "filled_by": "client", "required": False}
                    ]
                },
                {
                    "id": "section_cm_submissions",
                    "title": "CM Submissions",
                    "fields": [
                        {"key": "wes_reference", "label": "WES Reference Number", "field_type": "text", "filled_by": "cm", "required": False},
                        {"key": "noc_code", "label": "NOC Code", "field_type": "text", "filled_by": "cm", "required": False},
                        {"key": "visa_grant_date", "label": "Visa Grant Date", "field_type": "date", "filled_by": "cm", "required": False},
                        {"key": "application_number", "label": "Application Number", "field_type": "text", "filled_by": "cm", "required": False},
                        {"key": "submission_date", "label": "Submission Date", "field_type": "date", "filled_by": "cm", "required": False},
                        {"key": "case_notes", "label": "Case Notes", "field_type": "textarea", "filled_by": "cm", "required": False}
                    ]
                },
                {
                    "id": "section_settlement",
                    "title": "Settlement Details",
                    "fields": [
                        {"key": "intended_province", "label": "Intended Province", "field_type": "select", "options": ["Ontario", "British Columbia", "Alberta", "Quebec"], "filled_by": "both", "required": False},
                        {"key": "settlement_funds", "label": "Settlement Funds (CAD)", "field_type": "text", "filled_by": "client", "required": False},
                        {"key": "job_offer", "label": "Job Offer Status", "field_type": "select", "options": ["Yes", "No", "Pending"], "filled_by": "both", "required": False}
                    ]
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/intake-forms/save", json=payload, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        assert data.get("total_fields") == 18, f"Expected 18 fields, got {data.get('total_fields')}"
        print(f"PASS: Admin saved intake form with {data.get('total_fields')} fields")

    def test_non_admin_cannot_save_intake_form(self, client_token, canada_pr_product_id):
        """Non-admin users cannot create intake forms"""
        payload = {
            "product_id": canada_pr_product_id,
            "product_name": "Canada PR",
            "sections": []
        }
        
        response = requests.post(f"{BASE_URL}/api/intake-forms/save", json=payload, headers={
            "Authorization": f"Bearer {client_token}"
        })
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Non-admin cannot save intake form (403)")

    def test_get_intake_form_for_product(self, admin_token, canada_pr_product_id):
        """Get intake form for a product"""
        response = requests.get(f"{BASE_URL}/api/intake-forms/product/{canada_pr_product_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("exists") == True, "Form should exist"
        assert "sections" in data
        assert len(data["sections"]) == 4, f"Expected 4 sections, got {len(data['sections'])}"
        print(f"PASS: Retrieved intake form with {len(data['sections'])} sections")


class TestCaseIntakeForm:
    """Test Case Intake Form APIs with role-based access"""

    def test_client_gets_case_intake_with_role_flags(self, client_token, client_case_id):
        """Client gets intake form with editable flags based on role"""
        response = requests.get(f"{BASE_URL}/api/intake-forms/case/{client_case_id}", headers={
            "Authorization": f"Bearer {client_token}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "sections" in data
        assert "has_form" in data
        
        if data.get("has_form"):
            # Check role-based editability
            for section in data["sections"]:
                for field in section.get("fields", []):
                    filled_by = field.get("filled_by", "client")
                    editable = field.get("editable", False)
                    
                    # Client should be able to edit client/both fields
                    if filled_by in ("client", "both"):
                        assert editable == True, f"Field {field['key']} should be editable for client"
                    # Client should NOT be able to edit cm fields
                    elif filled_by == "cm":
                        assert editable == False, f"Field {field['key']} should NOT be editable for client"
            
            print(f"PASS: Client gets intake form with correct role-based editability")
        else:
            print("INFO: No intake form exists for this case's product")

    def test_cm_gets_case_intake_with_role_flags(self, cm_token, client_case_id):
        """CM gets intake form with editable flags based on role"""
        response = requests.get(f"{BASE_URL}/api/intake-forms/case/{client_case_id}", headers={
            "Authorization": f"Bearer {cm_token}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        if data.get("has_form"):
            # Check role-based editability for CM
            for section in data["sections"]:
                for field in section.get("fields", []):
                    filled_by = field.get("filled_by", "client")
                    editable = field.get("editable", False)
                    
                    # CM should be able to edit cm/both fields
                    if filled_by in ("cm", "both"):
                        assert editable == True, f"Field {field['key']} should be editable for CM"
                    # CM should NOT be able to edit client-only fields
                    elif filled_by == "client":
                        assert editable == False, f"Field {field['key']} should NOT be editable for CM"
            
            print(f"PASS: CM gets intake form with correct role-based editability")
        else:
            print("INFO: No intake form exists for this case's product")

    def test_client_can_save_client_fields(self, client_token, client_case_id):
        """Client can save client-only and both fields"""
        payload = {
            "case_id": client_case_id,
            "data": {
                "full_name": "Test Client Name",
                "date_of_birth": "1990-01-15",
                "passport_number": "AB1234567",
                "ielts_overall": "7.5",
                "intended_province": "Ontario"  # 'both' field
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/intake-forms/case/save", json=payload, headers={
            "Authorization": f"Bearer {client_token}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "updated_fields" in data
        print(f"PASS: Client saved {len(data.get('updated_fields', []))} fields")

    def test_client_cannot_save_cm_fields(self, client_token, client_case_id):
        """Client cannot save CM-only fields (they are silently ignored)"""
        payload = {
            "case_id": client_case_id,
            "data": {
                "wes_reference": "WES12345",  # CM-only field
                "noc_code": "21232"  # CM-only field
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/intake-forms/case/save", json=payload, headers={
            "Authorization": f"Bearer {client_token}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # CM fields should not be in updated_fields
        updated = data.get("updated_fields", [])
        assert "wes_reference" not in updated, "CM field should not be saved by client"
        assert "noc_code" not in updated, "CM field should not be saved by client"
        print("PASS: Client cannot save CM-only fields (correctly ignored)")

    def test_cm_can_save_cm_fields(self, cm_token, client_case_id):
        """CM can save CM-only and both fields"""
        payload = {
            "case_id": client_case_id,
            "data": {
                "wes_reference": "WES-2024-12345",
                "noc_code": "21232",
                "application_number": "APP-2024-001",
                "intended_province": "British Columbia"  # 'both' field
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/intake-forms/case/save", json=payload, headers={
            "Authorization": f"Bearer {cm_token}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        updated = data.get("updated_fields", [])
        assert "wes_reference" in updated, "CM should be able to save wes_reference"
        assert "noc_code" in updated, "CM should be able to save noc_code"
        print(f"PASS: CM saved {len(updated)} fields including CM-only fields")

    def test_cm_cannot_save_client_only_fields(self, cm_token, client_case_id):
        """CM cannot save client-only fields (they are silently ignored)"""
        payload = {
            "case_id": client_case_id,
            "data": {
                "passport_number": "CM-TRYING-TO-CHANGE",  # Client-only field
                "settlement_funds": "50000"  # Client-only field
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/intake-forms/case/save", json=payload, headers={
            "Authorization": f"Bearer {cm_token}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        updated = data.get("updated_fields", [])
        assert "passport_number" not in updated, "Client-only field should not be saved by CM"
        print("PASS: CM cannot save client-only fields (correctly ignored)")

    def test_verify_data_persistence(self, client_token, client_case_id):
        """Verify saved data persists and is returned correctly"""
        response = requests.get(f"{BASE_URL}/api/intake-forms/case/{client_case_id}", headers={
            "Authorization": f"Bearer {client_token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("has_form"):
            # Find fields and check values
            found_values = {}
            for section in data["sections"]:
                for field in section.get("fields", []):
                    if field.get("value"):
                        found_values[field["key"]] = field["value"]
            
            # Check some expected values
            if "full_name" in found_values:
                assert found_values["full_name"] == "Test Client Name"
            if "wes_reference" in found_values:
                assert found_values["wes_reference"] == "WES-2024-12345"
            
            print(f"PASS: Data persistence verified - found {len(found_values)} filled fields")
        else:
            print("INFO: No intake form to verify")


class TestIntakeFormList:
    """Test intake form listing for admin"""

    def test_admin_can_list_intake_forms(self, admin_token):
        """Admin can list all intake forms"""
        response = requests.get(f"{BASE_URL}/api/intake-forms/list", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Admin listed {len(data)} intake forms")

    def test_non_admin_cannot_list_intake_forms(self, client_token):
        """Non-admin cannot list intake forms"""
        response = requests.get(f"{BASE_URL}/api/intake-forms/list", headers={
            "Authorization": f"Bearer {client_token}"
        })
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Non-admin cannot list intake forms (403)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
