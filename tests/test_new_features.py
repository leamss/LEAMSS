"""
LEAMSS Portal - New Features Tests (Iteration 3)
Tests for:
1. System Settings API (GET/PUT /api/settings)
2. Case Search/Filter functionality
3. Document expiry/validity settings in product workflow
4. Case Manager workflow customization (custom document requests)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


class TestSystemSettings:
    """Test system settings endpoints - GET and PUT /api/settings"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        return response.json()["token"]
    
    def test_get_settings_as_admin(self, admin_token):
        """Test admin can get full system settings"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/settings", headers=headers)
        assert response.status_code == 200, f"GET settings failed: {response.text}"
        data = response.json()
        assert "allow_case_manager_workflow_customization" in data
        print(f"✓ Admin GET settings: allow_case_manager_workflow_customization = {data.get('allow_case_manager_workflow_customization')}")
        return data
    
    def test_get_settings_as_case_manager(self, manager_token):
        """Test case manager can get relevant settings"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/settings", headers=headers)
        assert response.status_code == 200, f"GET settings failed: {response.text}"
        data = response.json()
        assert "allow_case_manager_workflow_customization" in data
        print(f"✓ Case Manager GET settings: allow_case_manager_workflow_customization = {data.get('allow_case_manager_workflow_customization')}")
    
    def test_get_settings_as_client(self, client_token):
        """Test client can get relevant settings"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/settings", headers=headers)
        assert response.status_code == 200, f"GET settings failed: {response.text}"
        data = response.json()
        assert "allow_case_manager_workflow_customization" in data
        print(f"✓ Client GET settings: allow_case_manager_workflow_customization = {data.get('allow_case_manager_workflow_customization')}")
    
    def test_update_settings_as_admin(self, admin_token):
        """Test admin can update system settings"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get current settings
        get_response = requests.get(f"{BASE_URL}/api/settings", headers=headers)
        current_value = get_response.json().get("allow_case_manager_workflow_customization", False)
        
        # Toggle the setting
        new_value = not current_value
        update_data = {"allow_case_manager_workflow_customization": new_value}
        response = requests.put(f"{BASE_URL}/api/settings", json=update_data, headers=headers)
        assert response.status_code == 200, f"PUT settings failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✓ Admin PUT settings: toggled allow_case_manager_workflow_customization to {new_value}")
        
        # Verify the change
        verify_response = requests.get(f"{BASE_URL}/api/settings", headers=headers)
        assert verify_response.json().get("allow_case_manager_workflow_customization") == new_value
        print(f"✓ Verified setting change persisted")
        
        # Restore original value
        requests.put(f"{BASE_URL}/api/settings", json={"allow_case_manager_workflow_customization": current_value}, headers=headers)
        print(f"✓ Restored original setting value: {current_value}")
    
    def test_update_settings_as_case_manager_forbidden(self, manager_token):
        """Test case manager cannot update system settings"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        update_data = {"allow_case_manager_workflow_customization": True}
        response = requests.put(f"{BASE_URL}/api/settings", json=update_data, headers=headers)
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print(f"✓ Case Manager correctly denied from updating settings (403)")
    
    def test_update_settings_as_client_forbidden(self, client_token):
        """Test client cannot update system settings"""
        headers = {"Authorization": f"Bearer {client_token}"}
        update_data = {"allow_case_manager_workflow_customization": True}
        response = requests.put(f"{BASE_URL}/api/settings", json=update_data, headers=headers)
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print(f"✓ Client correctly denied from updating settings (403)")


class TestCaseFiltering:
    """Test case search and filter functionality"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_get_all_cases(self, admin_token):
        """Test admin can get all cases"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        assert response.status_code == 200, f"GET cases failed: {response.text}"
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✓ Retrieved {len(cases)} cases")
        
        # Verify case structure has required fields for filtering
        if len(cases) > 0:
            case = cases[0]
            assert "case_id" in case, "Case missing case_id field"
            assert "client_name" in case, "Case missing client_name field"
            assert "case_manager_name" in case, "Case missing case_manager_name field"
            assert "status" in case, "Case missing status field"
            print(f"✓ Case structure verified: case_id={case['case_id']}, client={case['client_name']}, manager={case['case_manager_name']}, status={case['status']}")
        return cases
    
    def test_get_case_managers_for_filter(self, admin_token):
        """Test getting case managers list for filter dropdown"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users/case-managers", headers=headers)
        assert response.status_code == 200, f"GET case-managers failed: {response.text}"
        managers = response.json()
        assert isinstance(managers, list)
        print(f"✓ Retrieved {len(managers)} case managers for filter dropdown")
        
        if len(managers) > 0:
            manager = managers[0]
            assert "id" in manager, "Manager missing id field"
            assert "name" in manager, "Manager missing name field"
            print(f"✓ Manager structure verified: id={manager['id']}, name={manager['name']}")
        return managers


class TestDocumentExpiryValidity:
    """Test document expiry/validity settings in product workflow"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_create_product_with_document_expiry(self, admin_token):
        """Test creating product with document that has expiry date"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a test product
        product_data = {
            "name": "TEST_Document_Expiry_Product",
            "description": "Test product with document expiry settings",
            "fee": 1500.0,
            "commission_rate": 10.0,
            "commission_type": "fixed"
        }
        create_response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=headers)
        assert create_response.status_code == 200, f"Create product failed: {create_response.text}"
        product_id = create_response.json()["id"]
        print(f"✓ Created test product: {product_id}")
        
        # Add workflow step with document that has expiry date
        step_data = {
            "product_id": product_id,
            "step_name": "Document Verification",
            "step_order": 1,
            "description": "Verify client documents",
            "duration_days": 7,
            "required_documents": [
                {
                    "doc_name": "Passport",
                    "description": "Valid passport copy",
                    "is_mandatory": True,
                    "has_expiry": True,
                    "expiry_date": "2026-12-31",
                    "validity_months": None,
                    "doc_type": "passport"
                },
                {
                    "doc_name": "Bank Statement",
                    "description": "Recent bank statement",
                    "is_mandatory": True,
                    "has_expiry": True,
                    "expiry_date": None,
                    "validity_months": 3,
                    "doc_type": "financial"
                }
            ]
        }
        step_response = requests.post(f"{BASE_URL}/api/products/workflow-step", json=step_data, headers=headers)
        assert step_response.status_code == 200, f"Add workflow step failed: {step_response.text}"
        print(f"✓ Added workflow step with document expiry settings")
        
        # Verify the product has the workflow step with document settings
        get_response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        products = get_response.json()
        test_product = next((p for p in products if p["id"] == product_id), None)
        assert test_product is not None, "Test product not found"
        assert len(test_product["workflow_steps"]) == 1, "Workflow step not added"
        
        step = test_product["workflow_steps"][0]
        assert len(step["required_documents"]) == 2, "Documents not added to step"
        
        # Verify document expiry settings
        passport_doc = next((d for d in step["required_documents"] if d["doc_name"] == "Passport"), None)
        assert passport_doc is not None, "Passport document not found"
        assert passport_doc.get("has_expiry") == True, "Passport has_expiry not set"
        assert passport_doc.get("expiry_date") == "2026-12-31", "Passport expiry_date not set"
        assert passport_doc.get("doc_type") == "passport", "Passport doc_type not set"
        print(f"✓ Verified Passport document: has_expiry=True, expiry_date=2026-12-31, doc_type=passport")
        
        bank_doc = next((d for d in step["required_documents"] if d["doc_name"] == "Bank Statement"), None)
        assert bank_doc is not None, "Bank Statement document not found"
        assert bank_doc.get("has_expiry") == True, "Bank Statement has_expiry not set"
        assert bank_doc.get("validity_months") == 3, "Bank Statement validity_months not set"
        assert bank_doc.get("doc_type") == "financial", "Bank Statement doc_type not set"
        print(f"✓ Verified Bank Statement document: has_expiry=True, validity_months=3, doc_type=financial")
        
        # Cleanup - delete test product
        delete_response = requests.delete(f"{BASE_URL}/api/products/{product_id}", headers=headers)
        assert delete_response.status_code == 200, f"Delete product failed: {delete_response.text}"
        print(f"✓ Cleaned up test product")


class TestCaseManagerWorkflowCustomization:
    """Test Case Manager workflow customization - custom document requests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    def get_manager_case(self, manager_token):
        """Helper to get a case assigned to the manager"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = response.json()
        if len(cases) > 0:
            return cases[0]
        return None
    
    def test_custom_doc_request_when_disabled(self, admin_token, manager_token):
        """Test CM cannot request custom doc when setting is disabled"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        manager_headers = {"Authorization": f"Bearer {manager_token}"}
        
        # First, ensure the setting is disabled
        requests.put(f"{BASE_URL}/api/settings", json={"allow_case_manager_workflow_customization": False}, headers=admin_headers)
        print(f"✓ Disabled CM workflow customization setting")
        
        # Get a case assigned to the manager
        case = self.get_manager_case(manager_token)
        if not case:
            pytest.skip("No cases assigned to case manager")
        
        # Try to request custom document
        request_data = {
            "case_id": case["id"],
            "document_name": "TEST_Custom_Document",
            "description": "Test custom document request",
            "step_order": 1
        }
        response = requests.post(f"{BASE_URL}/api/cases/{case['id']}/custom-document-request", json=request_data, headers=manager_headers)
        assert response.status_code == 403, f"Expected 403 when setting disabled, got {response.status_code}"
        assert "not enabled" in response.json().get("detail", "").lower() or "workflow customization" in response.json().get("detail", "").lower()
        print(f"✓ CM correctly denied custom doc request when setting disabled (403)")
    
    def test_custom_doc_request_when_enabled(self, admin_token, manager_token):
        """Test CM can request custom doc when setting is enabled"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        manager_headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Enable the setting
        requests.put(f"{BASE_URL}/api/settings", json={"allow_case_manager_workflow_customization": True}, headers=admin_headers)
        print(f"✓ Enabled CM workflow customization setting")
        
        # Get a case assigned to the manager
        case = self.get_manager_case(manager_token)
        if not case:
            pytest.skip("No cases assigned to case manager")
        
        # Request custom document with expiry/validity settings
        request_data = {
            "case_id": case["id"],
            "document_name": "TEST_Custom_Medical_Certificate",
            "description": "Medical certificate for visa application",
            "step_order": 1,
            "due_date": "2025-01-15",
            "expiry_date": "2025-06-15",
            "validity_months": None,
            "doc_type": "medical"
        }
        response = requests.post(f"{BASE_URL}/api/cases/{case['id']}/custom-document-request", json=request_data, headers=manager_headers)
        assert response.status_code == 200, f"Custom doc request failed: {response.text}"
        data = response.json()
        assert "document_id" in data or "message" in data
        print(f"✓ CM successfully requested custom document when setting enabled")
        
        # Disable the setting again for cleanup
        requests.put(f"{BASE_URL}/api/settings", json={"allow_case_manager_workflow_customization": False}, headers=admin_headers)
        print(f"✓ Restored setting to disabled")
    
    def test_admin_can_always_request_custom_doc(self, admin_token):
        """Test admin can always request custom doc regardless of setting"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Ensure setting is disabled
        requests.put(f"{BASE_URL}/api/settings", json={"allow_case_manager_workflow_customization": False}, headers=headers)
        
        # Get any case
        cases_response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        cases = cases_response.json()
        if len(cases) == 0:
            pytest.skip("No cases available")
        
        case = cases[0]
        
        # Admin should be able to request custom doc even when setting is disabled
        request_data = {
            "case_id": case["id"],
            "document_name": "TEST_Admin_Custom_Document",
            "description": "Admin requested document",
            "step_order": 1
        }
        response = requests.post(f"{BASE_URL}/api/cases/{case['id']}/custom-document-request", json=request_data, headers=headers)
        assert response.status_code == 200, f"Admin custom doc request failed: {response.text}"
        print(f"✓ Admin can request custom doc regardless of setting")


class TestAdditionalDocumentRequest:
    """Test the existing additional document request endpoint"""
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    def test_request_additional_document(self, manager_token):
        """Test case manager can request additional document via standard endpoint"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Get a case assigned to the manager
        cases_response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = cases_response.json()
        if len(cases) == 0:
            pytest.skip("No cases assigned to case manager")
        
        case = cases[0]
        
        # Request additional document
        request_data = {
            "case_id": case["id"],
            "document_name": "TEST_Additional_Document",
            "description": "Additional document for case processing",
            "step_order": 1,
            "due_date": "2025-01-20",
            "expiry_date": None,
            "validity_months": 6,
            "doc_type": "other"
        }
        response = requests.post(f"{BASE_URL}/api/cases/request-additional-document", json=request_data, headers=headers)
        assert response.status_code == 200, f"Additional doc request failed: {response.text}"
        data = response.json()
        assert "request_id" in data or "message" in data
        print(f"✓ Additional document request successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
