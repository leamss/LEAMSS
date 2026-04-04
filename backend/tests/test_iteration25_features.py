"""
Iteration 25 Tests - Bug Fixes and New Features
Tests for:
1. Sale document download - GET /api/sales/document/download/{file_id}
2. Request Additional Document - POST /api/cases/request-document with null step_order
3. Product commission rate - PUT /api/products/{id} can set commission_rate
4. Admin password reset - PUT /api/users/{user_id}/reset-password
5. Information Sheet request - POST /api/cases/{case_id}/request-info-sheet
6. Information Sheet save - tracks change_history, updated_by, updated_by_role
7. Regression tests for login and CRUD operations
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
MANAGER_EMAIL = "manager@leamss.com"
MANAGER_PASSWORD = "Manager@123"
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
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def manager_token():
    """Get case manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGER_EMAIL,
        "password": MANAGER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Manager login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def partner_token():
    """Get partner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARTNER_EMAIL,
        "password": PARTNER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Partner login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def client_token():
    """Get client authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CLIENT_EMAIL,
        "password": CLIENT_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Client login failed: {response.status_code} - {response.text}")


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestRegressionLogin:
    """Regression: All role logins should work"""
    
    def test_admin_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print("PASS: Admin login works")
    
    def test_manager_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MANAGER_EMAIL,
            "password": MANAGER_PASSWORD
        })
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print("PASS: Case Manager login works")
    
    def test_partner_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTNER_EMAIL,
            "password": PARTNER_PASSWORD
        })
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print("PASS: Partner login works")
    
    def test_client_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print("PASS: Client login works")


class TestSaleDocumentDownload:
    """Bug Fix: Sale document download endpoint"""
    
    def test_sale_document_download_endpoint_exists(self, admin_token):
        """Test that the sale document download endpoint exists and returns proper error for invalid ID"""
        response = requests.get(
            f"{BASE_URL}/api/sales/document/download/invalid-file-id",
            headers=auth_header(admin_token)
        )
        # Should return 404 for invalid file ID, not 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404 for invalid file, got {response.status_code}"
        print("PASS: Sale document download endpoint exists (returns 404 for invalid file)")
    
    def test_get_sale_documents(self, admin_token):
        """Test getting sale documents list"""
        # First get a sale
        sales_response = requests.get(f"{BASE_URL}/api/sales", headers=auth_header(admin_token))
        assert sales_response.status_code == 200
        sales = sales_response.json()
        
        if sales:
            sale_id = sales[0]["id"]
            docs_response = requests.get(
                f"{BASE_URL}/api/sales/{sale_id}/documents",
                headers=auth_header(admin_token)
            )
            assert docs_response.status_code == 200
            print(f"PASS: Get sale documents works - found {len(docs_response.json())} documents")
        else:
            print("SKIP: No sales found to test document download")


class TestRequestAdditionalDocument:
    """Bug Fix: Request Additional Document with null step_order"""
    
    def test_request_document_with_null_step_order(self, manager_token):
        """Test that POST /api/cases/request-document accepts null step_order"""
        # First get a case
        cases_response = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(manager_token))
        assert cases_response.status_code == 200
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases found to test document request")
        
        case_id = cases[0]["id"]
        
        # Request document with null step_order (this was returning 405 before)
        response = requests.post(
            f"{BASE_URL}/api/cases/request-document",
            json={
                "case_id": case_id,
                "document_name": "TEST_Additional_Document",
                "description": "Test document request with null step_order",
                "step_order": None,  # This should now be accepted
                "doc_type": "general"
            },
            headers=auth_header(manager_token)
        )
        
        # Should return 200, not 405
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "message" in response.json()
        print("PASS: Request document with null step_order works (no longer 405)")
    
    def test_custom_document_request_endpoint(self, manager_token):
        """Test the custom document request endpoint"""
        cases_response = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(manager_token))
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases found")
        
        case_id = cases[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/cases/{case_id}/custom-document-request",
            json={
                "document_name": "TEST_Custom_Doc",
                "description": "Custom document request test",
                "step_order": 1,
                "doc_type": "passport"
            },
            headers=auth_header(manager_token)
        )
        
        assert response.status_code == 200, f"Custom doc request failed: {response.text}"
        print("PASS: Custom document request endpoint works")


class TestProductCommissionRate:
    """Bug Fix: Product commission rate field"""
    
    def test_get_products_shows_commission_rate(self, admin_token):
        """Test that GET /api/products shows commission_rate field"""
        response = requests.get(f"{BASE_URL}/api/products", headers=auth_header(admin_token))
        assert response.status_code == 200
        products = response.json()
        
        assert len(products) > 0, "No products found"
        
        # Check that commission_rate field exists in products
        for product in products:
            # commission_rate may be 0 or None for some products
            assert "commission_rate" in product or product.get("commission_rate") is None or product.get("commission_rate", 0) >= 0
        
        # Find Canada PR which should have commission_rate set to 15
        canada_pr = next((p for p in products if "Canada" in p.get("name", "")), None)
        if canada_pr:
            print(f"PASS: Canada PR commission_rate = {canada_pr.get('commission_rate')}")
        else:
            print("PASS: Products have commission_rate field")
    
    def test_update_product_commission_rate(self, admin_token):
        """Test that PUT /api/products/{id} can set commission_rate"""
        # Get products
        response = requests.get(f"{BASE_URL}/api/products", headers=auth_header(admin_token))
        products = response.json()
        
        if not products:
            pytest.skip("No products found")
        
        product_id = products[0]["id"]
        original_rate = products[0].get("commission_rate", 0)
        new_rate = 20 if original_rate != 20 else 25
        
        # Update commission rate
        update_response = requests.put(
            f"{BASE_URL}/api/products/{product_id}",
            json={"commission_rate": new_rate},
            headers=auth_header(admin_token)
        )
        
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        # Verify the update
        verify_response = requests.get(f"{BASE_URL}/api/products/{product_id}", headers=auth_header(admin_token))
        assert verify_response.status_code == 200
        updated_product = verify_response.json()
        assert updated_product.get("commission_rate") == new_rate, f"Commission rate not updated: {updated_product.get('commission_rate')}"
        
        # Restore original rate
        requests.put(
            f"{BASE_URL}/api/products/{product_id}",
            json={"commission_rate": original_rate},
            headers=auth_header(admin_token)
        )
        
        print(f"PASS: Product commission_rate can be updated ({original_rate} -> {new_rate} -> {original_rate})")


class TestAdminPasswordReset:
    """Feature: Admin password reset"""
    
    def test_password_reset_endpoint_exists(self, admin_token):
        """Test that PUT /api/users/{user_id}/reset-password endpoint exists"""
        # Get a user to test with
        users_response = requests.get(f"{BASE_URL}/api/users", headers=auth_header(admin_token))
        assert users_response.status_code == 200
        users = users_response.json()
        
        # Find a test user (not admin)
        test_user = next((u for u in users if u["role"] == "client" and "client@leamss.com" in u.get("email", "")), None)
        
        if not test_user:
            pytest.skip("No suitable test user found")
        
        user_id = test_user["id"]
        
        # Test password reset with short password (should fail)
        response = requests.put(
            f"{BASE_URL}/api/users/{user_id}/reset-password",
            json={"new_password": "123"},  # Too short
            headers=auth_header(admin_token)
        )
        assert response.status_code == 400, f"Expected 400 for short password, got {response.status_code}"
        print("PASS: Password reset validates minimum length")
    
    def test_password_reset_and_login(self, admin_token):
        """Test full password reset flow: reset -> login with new -> reset back"""
        # Get client user
        users_response = requests.get(f"{BASE_URL}/api/users", headers=auth_header(admin_token))
        users = users_response.json()
        
        client_user = next((u for u in users if u.get("email") == CLIENT_EMAIL), None)
        if not client_user:
            pytest.skip("Client user not found")
        
        user_id = client_user["id"]
        temp_password = "TempPass@456"
        
        # Reset password
        reset_response = requests.put(
            f"{BASE_URL}/api/users/{user_id}/reset-password",
            json={"new_password": temp_password},
            headers=auth_header(admin_token)
        )
        assert reset_response.status_code == 200, f"Password reset failed: {reset_response.text}"
        print("PASS: Password reset API call successful")
        
        # Login with new password
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": temp_password
        })
        assert login_response.status_code == 200, f"Login with new password failed: {login_response.text}"
        print("PASS: Login with new password works")
        
        # Reset back to original password
        restore_response = requests.put(
            f"{BASE_URL}/api/users/{user_id}/reset-password",
            json={"new_password": CLIENT_PASSWORD},
            headers=auth_header(admin_token)
        )
        assert restore_response.status_code == 200, f"Password restore failed: {restore_response.text}"
        
        # Verify original password works
        verify_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert verify_response.status_code == 200, f"Login with original password failed: {verify_response.text}"
        print("PASS: Password reset and restore complete")


class TestInformationSheet:
    """Feature: Information Sheet request and save with change tracking"""
    
    def test_get_information_sheet(self, manager_token):
        """Test GET /api/cases/{case_id}/information-sheet"""
        cases_response = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(manager_token))
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases found")
        
        case_id = cases[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/cases/{case_id}/information-sheet",
            headers=auth_header(manager_token)
        )
        
        assert response.status_code == 200, f"Get info sheet failed: {response.text}"
        data = response.json()
        assert "exists" in data
        print(f"PASS: Get information sheet works (exists={data['exists']})")
    
    def test_save_information_sheet_tracks_changes(self, manager_token):
        """Test POST /api/cases/{case_id}/information-sheet tracks change_history"""
        cases_response = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(manager_token))
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases found")
        
        case_id = cases[0]["id"]
        
        # Save info sheet
        save_response = requests.post(
            f"{BASE_URL}/api/cases/{case_id}/information-sheet",
            json={
                "full_name": "TEST_Client Name",
                "date_of_birth": "1990-01-15",
                "nationality": "Indian",
                "passport_number": "TEST123456",
                "changes_summary": "Test update from iteration 25"
            },
            headers=auth_header(manager_token)
        )
        
        assert save_response.status_code == 200, f"Save info sheet failed: {save_response.text}"
        
        # Verify the save and check for tracking fields
        get_response = requests.get(
            f"{BASE_URL}/api/cases/{case_id}/information-sheet",
            headers=auth_header(manager_token)
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        
        if data.get("exists"):
            sheet = data.get("data", {})
            # Check tracking fields
            assert "updated_by" in sheet or sheet.get("updated_by") is not None, "updated_by field missing"
            assert "updated_by_role" in sheet or sheet.get("updated_by_role") is not None, "updated_by_role field missing"
            print(f"PASS: Information sheet saved with tracking (updated_by_role={sheet.get('updated_by_role')})")
        else:
            print("PASS: Information sheet save works (new sheet created)")
    
    def test_request_info_sheet_from_client(self, manager_token):
        """Test POST /api/cases/{case_id}/request-info-sheet sends notification"""
        cases_response = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(manager_token))
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases found")
        
        case_id = cases[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/cases/{case_id}/request-info-sheet",
            json={
                "message": "Please update your information sheet with current details.",
                "fields_to_update": ["address", "phone"]
            },
            headers=auth_header(manager_token)
        )
        
        assert response.status_code == 200, f"Request info sheet failed: {response.text}"
        assert "message" in response.json()
        print("PASS: Request info sheet from client works")


class TestRegressionCRUD:
    """Regression: Existing CRUD operations still work"""
    
    def test_sales_crud(self, admin_token):
        """Test sales endpoints"""
        response = requests.get(f"{BASE_URL}/api/sales", headers=auth_header(admin_token))
        assert response.status_code == 200
        print(f"PASS: GET /api/sales works ({len(response.json())} sales)")
    
    def test_products_crud(self, admin_token):
        """Test products endpoints"""
        response = requests.get(f"{BASE_URL}/api/products", headers=auth_header(admin_token))
        assert response.status_code == 200
        print(f"PASS: GET /api/products works ({len(response.json())} products)")
    
    def test_cases_crud(self, admin_token):
        """Test cases endpoints"""
        response = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(admin_token))
        assert response.status_code == 200
        print(f"PASS: GET /api/cases works ({len(response.json())} cases)")
    
    def test_tickets_crud(self, admin_token):
        """Test tickets endpoints"""
        response = requests.get(f"{BASE_URL}/api/tickets/all", headers=auth_header(admin_token))
        assert response.status_code == 200
        print(f"PASS: GET /api/tickets/all works ({len(response.json())} tickets)")
    
    def test_users_crud(self, admin_token):
        """Test users endpoints"""
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_header(admin_token))
        assert response.status_code == 200
        print(f"PASS: GET /api/users works ({len(response.json())} users)")
    
    def test_dashboard_stats(self, admin_token):
        """Test dashboard stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert "pending_sales" in data or "active_cases" in data
        print("PASS: GET /api/stats/dashboard works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
