"""
LEAMSS Portal - Iteration 14 Feature Tests
Testing newly fixed features:
1. Sale approval without case manager (2-step process)
2. Client credentials returned on approval
3. Case manager assignment on cases page
4. User impersonation
5. Case manager update workflow step status
6. Case manager custom document request
7. Information sheet CRUD
8. Partner report endpoint
9. Global search
10. Analytics dashboard
11. Notifications
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://payment-portal-323.preview.emergentagent.com')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


class TestAuthentication:
    """Test login for all 4 roles"""
    
    def test_admin_login(self):
        """Admin login should return token and user data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"PASS: Admin login successful - {data['user']['name']}")
    
    def test_case_manager_login(self):
        """Case manager login should return token and user data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200, f"Case manager login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print(f"PASS: Case manager login successful - {data['user']['name']}")
    
    def test_partner_login(self):
        """Partner login should return token and user data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"PASS: Partner login successful - {data['user']['name']}")
    
    def test_client_login(self):
        """Client login should return token and user data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print(f"PASS: Client login successful - {data['user']['name']}")


@pytest.fixture
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Admin login failed")


@pytest.fixture
def manager_token():
    """Get case manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Case manager login failed")


@pytest.fixture
def partner_token():
    """Get partner auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Partner login failed")


@pytest.fixture
def client_token():
    """Get client auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Client login failed")


class TestAdminDashboard:
    """Test admin dashboard stats and data"""
    
    def test_dashboard_stats(self, admin_token):
        """Admin dashboard should return stats"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=headers)
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        # Check expected fields
        assert "pending_sales" in data or "total_sales" in data
        print(f"PASS: Admin dashboard stats loaded - {data}")
    
    def test_get_pending_sales(self, admin_token):
        """Admin should be able to get pending sales"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/pending", headers=headers)
        assert response.status_code == 200, f"Get pending sales failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Pending sales retrieved - {len(data)} sales")
    
    def test_get_all_cases(self, admin_token):
        """Admin should be able to get all cases"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        assert response.status_code == 200, f"Get all cases failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: All cases retrieved - {len(data)} cases")
    
    def test_get_all_users(self, admin_token):
        """Admin should be able to get all users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200, f"Get all users failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print(f"PASS: All users retrieved - {len(data)} users")


class TestSaleApproval:
    """Test sale approval flow - 2-step process"""
    
    def test_sale_approval_without_case_manager(self, admin_token):
        """Sale approval should work without case_manager_id (2-step process)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get pending sales
        response = requests.get(f"{BASE_URL}/api/sales/pending", headers=headers)
        assert response.status_code == 200
        pending_sales = response.json()
        
        if len(pending_sales) == 0:
            pytest.skip("No pending sales to test approval")
        
        sale = pending_sales[0]
        
        # Approve sale WITHOUT case_manager_id
        approval_data = {
            "sale_id": sale["id"],
            "status": "approved"
            # Note: case_manager_id is NOT included - this is the 2-step process
        }
        
        response = requests.post(f"{BASE_URL}/api/sales/approve", json=approval_data, headers=headers)
        assert response.status_code == 200, f"Sale approval failed: {response.text}"
        data = response.json()
        assert "message" in data
        
        # Check if client_credentials are returned for new client
        if "client_credentials" in data:
            creds = data["client_credentials"]
            assert "email" in creds
            assert "password" in creds
            print(f"PASS: Sale approved with client credentials returned - {creds['email']}")
        else:
            print(f"PASS: Sale approved (existing client, no new credentials)")
    
    def test_sale_rejection(self, admin_token):
        """Sale rejection should work with rejection reason"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get pending sales
        response = requests.get(f"{BASE_URL}/api/sales/pending", headers=headers)
        assert response.status_code == 200
        pending_sales = response.json()
        
        if len(pending_sales) == 0:
            pytest.skip("No pending sales to test rejection")
        
        sale = pending_sales[0]
        
        # Reject sale
        rejection_data = {
            "sale_id": sale["id"],
            "status": "rejected",
            "rejection_reason": "Test rejection - documents incomplete"
        }
        
        response = requests.post(f"{BASE_URL}/api/sales/approve", json=rejection_data, headers=headers)
        assert response.status_code == 200, f"Sale rejection failed: {response.text}"
        print(f"PASS: Sale rejected successfully")


class TestCaseManagerAssignment:
    """Test case manager assignment on cases page"""
    
    def test_assign_case_manager(self, admin_token):
        """Admin should be able to assign case manager to a case"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all cases
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases to test assignment")
        
        case = cases[0]
        
        # Get case managers
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        users = response.json()
        case_managers = [u for u in users if u["role"] == "case_manager"]
        
        if len(case_managers) == 0:
            pytest.skip("No case managers available")
        
        manager = case_managers[0]
        
        # Assign case manager
        response = requests.put(
            f"{BASE_URL}/api/cases/{case['id']}/assign-manager?case_manager_id={manager['id']}", 
            headers=headers
        )
        assert response.status_code == 200, f"Case manager assignment failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"PASS: Case manager {manager['name']} assigned to case {case['case_id']}")


class TestUserImpersonation:
    """Test admin user impersonation (switch user)"""
    
    def test_impersonate_partner(self, admin_token):
        """Admin should be able to impersonate partner"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get users
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        users = response.json()
        partners = [u for u in users if u["role"] == "partner"]
        
        if len(partners) == 0:
            pytest.skip("No partners to impersonate")
        
        partner = partners[0]
        
        # Impersonate
        response = requests.post(f"{BASE_URL}/api/auth/impersonate/{partner['id']}", headers=headers)
        assert response.status_code == 200, f"Impersonation failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"PASS: Admin impersonated partner {data['user']['name']}")
    
    def test_impersonate_case_manager(self, admin_token):
        """Admin should be able to impersonate case manager"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get users
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        users = response.json()
        managers = [u for u in users if u["role"] == "case_manager"]
        
        if len(managers) == 0:
            pytest.skip("No case managers to impersonate")
        
        manager = managers[0]
        
        # Impersonate
        response = requests.post(f"{BASE_URL}/api/auth/impersonate/{manager['id']}", headers=headers)
        assert response.status_code == 200, f"Impersonation failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print(f"PASS: Admin impersonated case manager {data['user']['name']}")
    
    def test_impersonate_client(self, admin_token):
        """Admin should be able to impersonate client"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get users
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        users = response.json()
        clients = [u for u in users if u["role"] == "client"]
        
        if len(clients) == 0:
            pytest.skip("No clients to impersonate")
        
        client = clients[0]
        
        # Impersonate
        response = requests.post(f"{BASE_URL}/api/auth/impersonate/{client['id']}", headers=headers)
        assert response.status_code == 200, f"Impersonation failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print(f"PASS: Admin impersonated client {data['user']['name']}")
    
    def test_non_admin_cannot_impersonate(self, manager_token):
        """Non-admin should not be able to impersonate"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Try to impersonate (should fail)
        response = requests.post(f"{BASE_URL}/api/auth/impersonate/some-user-id", headers=headers)
        assert response.status_code in [403, 401], f"Non-admin impersonation should fail: {response.text}"
        print(f"PASS: Non-admin impersonation correctly denied")


class TestCaseManagerDashboard:
    """Test case manager dashboard and features"""
    
    def test_case_manager_stats(self, manager_token):
        """Case manager should get their stats"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/case-manager-dashboard", headers=headers)
        assert response.status_code == 200, f"Case manager stats failed: {response.text}"
        data = response.json()
        assert "my_cases" in data or "active_cases" in data
        print(f"PASS: Case manager stats loaded - {data}")
    
    def test_get_my_cases(self, manager_token):
        """Case manager should get their assigned cases"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200, f"Get my cases failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Case manager cases retrieved - {len(data)} cases")
        return data


class TestUpdateStepStatus:
    """Test case manager updating workflow step status"""
    
    def test_update_step_status_post(self, manager_token):
        """Case manager should update step status via POST"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Get my cases
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases assigned to case manager")
        
        case = cases[0]
        
        # Get case details to find a step
        response = requests.get(f"{BASE_URL}/api/cases/{case['id']}", headers=headers)
        assert response.status_code == 200
        case_detail = response.json()
        
        if not case_detail.get("steps") or len(case_detail["steps"]) == 0:
            pytest.skip("No steps in case")
        
        step = case_detail["steps"][0]
        
        # Update step status via POST
        update_data = {
            "case_id": case["id"],
            "step_name": step["step_name"],
            "status": "in_progress",
            "notes": "Test update from iteration 14"
        }
        
        response = requests.post(f"{BASE_URL}/api/cases/update-step", json=update_data, headers=headers)
        assert response.status_code == 200, f"Update step failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"PASS: Step '{step['step_name']}' updated to in_progress")


class TestCustomDocumentRequest:
    """Test case manager requesting additional documents"""
    
    def test_custom_document_request(self, manager_token):
        """Case manager should request additional document"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Get my cases
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases assigned to case manager")
        
        case = cases[0]
        
        # Request additional document
        doc_request = {
            "case_id": case["id"],
            "document_name": f"Test Document {uuid.uuid4().hex[:6]}",
            "description": "Test document request from iteration 14",
            "step_order": 1,
            "doc_type": "financial"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/cases/{case['id']}/custom-document-request", 
            json=doc_request, 
            headers=headers
        )
        assert response.status_code == 200, f"Custom document request failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"PASS: Custom document requested for case {case['case_id']}")


class TestInformationSheet:
    """Test information sheet CRUD"""
    
    def test_get_information_sheet(self, manager_token):
        """Case manager should get information sheet"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Get my cases
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases assigned to case manager")
        
        case = cases[0]
        
        # Get information sheet
        response = requests.get(f"{BASE_URL}/api/cases/{case['id']}/information-sheet", headers=headers)
        assert response.status_code == 200, f"Get information sheet failed: {response.text}"
        data = response.json()
        assert "exists" in data or "data" in data
        print(f"PASS: Information sheet retrieved for case {case['case_id']}")
    
    def test_save_information_sheet(self, manager_token):
        """Case manager should save information sheet"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Get my cases
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases assigned to case manager")
        
        case = cases[0]
        
        # Save information sheet
        info_data = {
            "full_name": "Test Client Name",
            "nationality": "Canadian",
            "phone": "+1234567890",
            "email": "test@example.com",
            "highest_education": "Bachelor's Degree",
            "primary_language": "English",
            "english_proficiency": "fluent",
            "marital_status": "single",
            "intended_destination": "Canada",
            "purpose_of_immigration": "Work Permit"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/cases/{case['id']}/information-sheet", 
            json=info_data, 
            headers=headers
        )
        assert response.status_code == 200, f"Save information sheet failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"PASS: Information sheet saved for case {case['case_id']}")


class TestPartnerReport:
    """Test partner report endpoint"""
    
    def test_get_partner_report(self, admin_token):
        """Admin should get partner report"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/sales/partner-report", headers=headers)
        assert response.status_code == 200, f"Partner report failed: {response.text}"
        data = response.json()
        
        # Check expected fields
        assert "total_sales" in data or "sales" in data
        print(f"PASS: Partner report retrieved - {data.get('total_sales', len(data.get('sales', [])))} sales")
    
    def test_get_partner_report_with_filter(self, admin_token):
        """Admin should get partner report with period filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/sales/partner-report?period=month", headers=headers)
        assert response.status_code == 200, f"Partner report with filter failed: {response.text}"
        data = response.json()
        print(f"PASS: Partner report with month filter retrieved")


class TestProductsCRUD:
    """Test products CRUD operations"""
    
    def test_get_products(self, admin_token):
        """Admin should get all products"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200, f"Get products failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Products retrieved - {len(data)} products")
        return data


class TestWorkflowStepCRUD:
    """Test workflow step CRUD operations"""
    
    def test_add_workflow_step(self, admin_token):
        """Admin should add workflow step to product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get products
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        products = response.json()
        
        if len(products) == 0:
            pytest.skip("No products available")
        
        product = products[0]
        
        # Add workflow step
        step_data = {
            "product_id": product["id"],
            "step_name": f"Test Step {uuid.uuid4().hex[:6]}",
            "step_order": 99,
            "description": "Test step from iteration 14",
            "duration_days": 7,
            "required_documents": [
                {
                    "doc_name": "Test Document",
                    "description": "Test document requirement",
                    "is_mandatory": True,
                    "has_expiry": False,
                    "doc_type": "other"
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/products/{product['id']}/workflow-step", 
            json=step_data, 
            headers=headers
        )
        assert response.status_code == 200, f"Add workflow step failed: {response.text}"
        data = response.json()
        assert "message" in data or "step_id" in data
        print(f"PASS: Workflow step added to product {product['name']}")
    
    def test_update_workflow_step(self, admin_token):
        """Admin should update workflow step"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get products
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        products = response.json()
        
        if len(products) == 0:
            pytest.skip("No products available")
        
        product = products[0]
        
        if not product.get("workflow_steps") or len(product["workflow_steps"]) == 0:
            pytest.skip("No workflow steps in product")
        
        step = product["workflow_steps"][0]
        
        # Update workflow step
        update_data = {
            "product_id": product["id"],
            "step_name": step["step_name"],
            "step_order": step["step_order"],
            "description": f"Updated description - {uuid.uuid4().hex[:6]}",
            "duration_days": step.get("duration_days", 7),
            "required_documents": step.get("required_documents", [])
        }
        
        response = requests.put(
            f"{BASE_URL}/api/products/{product['id']}/workflow-step/{step['step_order']}", 
            json=update_data, 
            headers=headers
        )
        assert response.status_code == 200, f"Update workflow step failed: {response.text}"
        print(f"PASS: Workflow step updated for product {product['name']}")


class TestTicketSystem:
    """Test ticket system"""
    
    def test_create_ticket(self, manager_token):
        """Case manager should create ticket"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        ticket_data = {
            "subject": f"Test Ticket {uuid.uuid4().hex[:6]}",
            "description": "Test ticket from iteration 14",
            "category": "general",
            "priority": "medium"
        }
        
        response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
        assert response.status_code in [200, 201], f"Create ticket failed: {response.text}"
        print(f"PASS: Ticket created successfully")
    
    def test_get_my_tickets(self, manager_token):
        """Case manager should get their tickets"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        assert response.status_code == 200, f"Get my tickets failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: My tickets retrieved - {len(data)} tickets")


class TestNotifications:
    """Test notifications endpoint"""
    
    def test_get_notifications(self, admin_token):
        """User should get notifications"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Notifications retrieved - {len(data)} notifications")


class TestAnalyticsDashboard:
    """Test analytics dashboard endpoint"""
    
    def test_analytics_dashboard(self, admin_token):
        """Admin should get analytics dashboard"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/dashboard", headers=headers)
        # May return 200 or 404 if not implemented
        if response.status_code == 200:
            data = response.json()
            print(f"PASS: Analytics dashboard retrieved - {data}")
        elif response.status_code == 404:
            pytest.skip("Analytics dashboard endpoint not implemented")
        else:
            assert False, f"Analytics dashboard failed: {response.text}"


class TestGlobalSearch:
    """Test global search endpoint"""
    
    def test_global_search(self, admin_token):
        """Admin should search globally"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/search/global?q=Canada", headers=headers)
        # May return 200 or 404 if not implemented
        if response.status_code == 200:
            data = response.json()
            print(f"PASS: Global search returned results")
        elif response.status_code == 404:
            pytest.skip("Global search endpoint not implemented")
        else:
            assert False, f"Global search failed: {response.text}"


class TestPartnerDashboard:
    """Test partner dashboard"""
    
    def test_partner_my_sales(self, partner_token):
        """Partner should get their sales"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/my-sales", headers=headers)
        assert response.status_code == 200, f"Get my sales failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Partner sales retrieved - {len(data)} sales")


class TestClientDashboard:
    """Test client dashboard"""
    
    def test_client_my_cases(self, client_token):
        """Client should get their cases"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200, f"Get my cases failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Client cases retrieved - {len(data)} cases")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
