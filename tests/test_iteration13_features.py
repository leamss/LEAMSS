"""
LEAMSS Portal - Iteration 13 Feature Tests
Tests for newly fixed endpoints and critical features:
1. Sale approval flow with case manager selection
2. Sale documents endpoint
3. Case manager reassignment
4. User impersonation
5. Workflow step CRUD
6. Multi-role login and dashboard access
7. Products CRUD
8. Document download
9. Ticket system
10. Notifications
11. Analytics/Reports
12. Global search
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://compliance-hub-751.preview.emergentagent.com')

# Test credentials
CREDENTIALS = {
    "admin": {"email": "admin@leamss.com", "password": "Admin@123"},
    "case_manager": {"email": "manager@leamss.com", "password": "Manager@123"},
    "partner": {"email": "partner@leamss.com", "password": "Partner@123"},
    "client": {"email": "client@leamss.com", "password": "Client@123"}
}


class TestAuthentication:
    """Test authentication for all user roles"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['email']}")
    
    def test_case_manager_login(self):
        """Test case manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["case_manager"])
        assert response.status_code == 200, f"Case manager login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print(f"✓ Case manager login successful: {data['user']['email']}")
    
    def test_partner_login(self):
        """Test partner login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["partner"])
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"✓ Partner login successful: {data['user']['email']}")
    
    def test_client_login(self):
        """Test client login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print(f"✓ Client login successful: {data['user']['email']}")


class TestUserImpersonation:
    """Test admin user impersonation feature"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_impersonate_partner(self, admin_token):
        """Admin can impersonate a partner"""
        # First get list of users to find a partner
        headers = {"Authorization": f"Bearer {admin_token}"}
        users_response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert users_response.status_code == 200
        
        users = users_response.json()
        partner = next((u for u in users if u["role"] == "partner"), None)
        
        if not partner:
            pytest.skip("No partner user found to impersonate")
        
        # Impersonate the partner
        response = requests.post(
            f"{BASE_URL}/api/auth/impersonate/{partner['id']}", 
            headers=headers
        )
        assert response.status_code == 200, f"Impersonation failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"✓ Admin successfully impersonated partner: {data['user']['email']}")
    
    def test_impersonate_case_manager(self, admin_token):
        """Admin can impersonate a case manager"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        users_response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        users = users_response.json()
        
        case_manager = next((u for u in users if u["role"] == "case_manager"), None)
        
        if not case_manager:
            pytest.skip("No case manager found to impersonate")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/impersonate/{case_manager['id']}", 
            headers=headers
        )
        assert response.status_code == 200, f"Impersonation failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "case_manager"
        print(f"✓ Admin successfully impersonated case manager: {data['user']['email']}")
    
    def test_impersonate_client(self, admin_token):
        """Admin can impersonate a client"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        users_response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        users = users_response.json()
        
        client = next((u for u in users if u["role"] == "client"), None)
        
        if not client:
            pytest.skip("No client found to impersonate")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/impersonate/{client['id']}", 
            headers=headers
        )
        assert response.status_code == 200, f"Impersonation failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "client"
        print(f"✓ Admin successfully impersonated client: {data['user']['email']}")
    
    def test_non_admin_cannot_impersonate(self):
        """Non-admin users cannot impersonate"""
        # Login as partner
        partner_response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["partner"])
        partner_token = partner_response.json()["token"]
        
        headers = {"Authorization": f"Bearer {partner_token}"}
        
        # Try to impersonate (should fail)
        response = requests.post(
            f"{BASE_URL}/api/auth/impersonate/some-user-id", 
            headers=headers
        )
        assert response.status_code == 403, "Non-admin should not be able to impersonate"
        print("✓ Non-admin correctly denied impersonation access")


class TestSalesApproval:
    """Test sale approval flow with case manager selection"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_get_pending_sales(self, admin_token):
        """Admin can get pending sales"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/pending", headers=headers)
        assert response.status_code == 200, f"Failed to get pending sales: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} pending sales")
    
    def test_get_all_sales(self, admin_token):
        """Admin can get all sales"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales", headers=headers)
        assert response.status_code == 200, f"Failed to get sales: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} total sales")
    
    def test_sale_approval_with_case_manager(self, admin_token):
        """Test approving a sale with case manager assignment"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get pending sales
        pending_response = requests.get(f"{BASE_URL}/api/sales/pending", headers=headers)
        pending_sales = pending_response.json()
        
        if not pending_sales:
            print("⚠ No pending sales to approve - skipping approval test")
            pytest.skip("No pending sales available")
        
        # Get case managers
        users_response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        users = users_response.json()
        case_manager = next((u for u in users if u["role"] == "case_manager"), None)
        
        if not case_manager:
            pytest.skip("No case manager found")
        
        sale = pending_sales[0]
        
        # Approve the sale
        approval_data = {
            "sale_id": sale["id"],
            "status": "approved",
            "case_manager_id": case_manager["id"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales/approve",
            json=approval_data,
            headers=headers
        )
        assert response.status_code == 200, f"Sale approval failed: {response.text}"
        print(f"✓ Sale approved successfully with case manager: {case_manager['name']}")


class TestSaleDocuments:
    """Test sale documents endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_get_sale_documents(self, admin_token):
        """Test GET /api/sales/{sale_id}/documents endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all sales first
        sales_response = requests.get(f"{BASE_URL}/api/sales", headers=headers)
        sales = sales_response.json()
        
        if not sales:
            pytest.skip("No sales found")
        
        sale = sales[0]
        
        # Get documents for the sale
        response = requests.get(
            f"{BASE_URL}/api/sales/{sale['id']}/documents",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get sale documents: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} documents for sale {sale['id']}")


class TestCaseManagerReassignment:
    """Test case manager reassignment"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_reassign_case_manager(self, admin_token):
        """Test PUT /api/cases/{case_id}/assign-manager endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all cases
        cases_response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases found")
        
        # Get case managers
        users_response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        users = users_response.json()
        case_managers = [u for u in users if u["role"] == "case_manager"]
        
        if not case_managers:
            pytest.skip("No case managers found")
        
        case = cases[0]
        new_manager = case_managers[0]
        
        # Reassign case manager
        response = requests.put(
            f"{BASE_URL}/api/cases/{case['id']}/assign-manager?case_manager_id={new_manager['id']}",
            headers=headers
        )
        assert response.status_code == 200, f"Case manager reassignment failed: {response.text}"
        print(f"✓ Case {case['case_id']} reassigned to {new_manager['name']}")


class TestWorkflowStepCRUD:
    """Test workflow step CRUD operations"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_get_products_with_workflow_steps(self, admin_token):
        """Get products with their workflow steps"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200, f"Failed to get products: {response.text}"
        products = response.json()
        assert isinstance(products, list)
        
        for product in products:
            assert "workflow_steps" in product
            print(f"✓ Product '{product['name']}' has {len(product['workflow_steps'])} workflow steps")
    
    def test_create_workflow_step(self, admin_token):
        """Test creating a new workflow step"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get a product
        products_response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        products = products_response.json()
        
        if not products:
            pytest.skip("No products found")
        
        product = products[0]
        existing_steps = len(product.get("workflow_steps", []))
        new_step_order = existing_steps + 10  # Use high number to avoid conflicts
        
        step_data = {
            "step_name": f"TEST_Step_{new_step_order}",
            "step_order": new_step_order,
            "description": "Test workflow step",
            "duration_days": 7,
            "required_documents": [
                {
                    "doc_name": "Test Document",
                    "description": "Test document description",
                    "is_mandatory": True,
                    "has_expiry": False,
                    "validity_months": None,
                    "doc_type": "pdf"
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/products/{product['id']}/workflow-step",
            json=step_data,
            headers=headers
        )
        assert response.status_code == 200, f"Failed to create workflow step: {response.text}"
        print(f"✓ Created workflow step for product '{product['name']}'")
        
        # Cleanup - delete the test step
        delete_response = requests.delete(
            f"{BASE_URL}/api/products/{product['id']}/workflow-step/{new_step_order}",
            headers=headers
        )
        if delete_response.status_code == 200:
            print(f"✓ Cleaned up test workflow step")
    
    def test_update_workflow_step(self, admin_token):
        """Test updating a workflow step"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get a product with workflow steps
        products_response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        products = products_response.json()
        
        product_with_steps = next(
            (p for p in products if p.get("workflow_steps")), 
            None
        )
        
        if not product_with_steps:
            pytest.skip("No product with workflow steps found")
        
        step = product_with_steps["workflow_steps"][0]
        
        update_data = {
            "step_name": step["step_name"],
            "step_order": step["step_order"],
            "description": f"Updated description at {time.time()}",
            "duration_days": step.get("duration_days", 7),
            "required_documents": step.get("required_documents", [])
        }
        
        response = requests.put(
            f"{BASE_URL}/api/products/{product_with_steps['id']}/workflow-step/{step['step_order']}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200, f"Failed to update workflow step: {response.text}"
        print(f"✓ Updated workflow step '{step['step_name']}'")


class TestProductsCRUD:
    """Test products CRUD operations"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_list_products(self, admin_token):
        """List all products"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        print(f"✓ Listed {len(products)} products")
    
    def test_create_product(self, admin_token):
        """Create a new product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        product_data = {
            "name": f"TEST_Product_{int(time.time())}",
            "description": "Test product description",
            "fee": 1000.00,
            "commission_rate": 10.0,
            "commission_type": "fixed"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/products",
            json=product_data,
            headers=headers
        )
        assert response.status_code == 200, f"Failed to create product: {response.text}"
        data = response.json()
        assert data["name"] == product_data["name"]
        print(f"✓ Created product: {data['name']}")
        
        # Cleanup - delete the product
        delete_response = requests.delete(
            f"{BASE_URL}/api/products/{data['id']}",
            headers=headers
        )
        if delete_response.status_code == 200:
            print(f"✓ Cleaned up test product")
    
    def test_update_product(self, admin_token):
        """Update a product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get products
        products_response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        products = products_response.json()
        
        if not products:
            pytest.skip("No products found")
        
        product = products[0]
        
        update_data = {
            "description": f"Updated description at {time.time()}"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/products/{product['id']}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200, f"Failed to update product: {response.text}"
        print(f"✓ Updated product: {product['name']}")


class TestDocumentDownload:
    """Test document download functionality"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_document_download_endpoint_exists(self, admin_token):
        """Test that document download endpoint exists"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Try to download a non-existent document (should return 404, not 500)
        response = requests.get(
            f"{BASE_URL}/api/documents/download/non-existent-id",
            headers=headers
        )
        # Should return 404 for non-existent document, not 500
        assert response.status_code in [404, 400], f"Unexpected status: {response.status_code}"
        print("✓ Document download endpoint exists and handles missing documents correctly")


class TestTicketSystem:
    """Test ticket system"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_list_my_tickets(self, admin_token):
        """List user's tickets"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Listed {len(tickets)} tickets")
    
    def test_list_all_tickets_admin(self, admin_token):
        """Admin can list all tickets"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/all", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Admin listed {len(tickets)} total tickets")
    
    def test_create_ticket(self, client_token):
        """Create a new ticket"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        ticket_data = {
            "subject": f"TEST_Ticket_{int(time.time())}",
            "description": "This is a test ticket description",
            "priority": "medium",
            "category": "general"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/tickets",
            json=ticket_data,
            headers=headers
        )
        assert response.status_code == 200, f"Failed to create ticket: {response.text}"
        print(f"✓ Created ticket: {ticket_data['subject']}")


class TestNotifications:
    """Test notifications endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_get_notifications(self, admin_token):
        """Get user notifications"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200, f"Failed to get notifications: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} notifications")


class TestAnalyticsDashboard:
    """Test analytics/reports endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_dashboard_stats(self, admin_token):
        """Get dashboard statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/dashboard-stats", headers=headers)
        assert response.status_code == 200, f"Failed to get dashboard stats: {response.text}"
        data = response.json()
        print(f"✓ Got dashboard stats: {data}")
    
    def test_sales_stats(self, admin_token):
        """Get sales statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/stats", headers=headers)
        assert response.status_code == 200, f"Failed to get sales stats: {response.text}"
        data = response.json()
        print(f"✓ Got sales stats: {data}")


class TestGlobalSearch:
    """Test global search endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["token"]
    
    def test_global_search(self, admin_token):
        """Test global search functionality"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/search?q=test",
            headers=headers
        )
        # Search endpoint may or may not exist
        if response.status_code == 404:
            print("⚠ Global search endpoint not implemented")
            pytest.skip("Global search endpoint not implemented")
        
        assert response.status_code == 200, f"Search failed: {response.text}"
        print(f"✓ Global search working")


class TestRoleDashboards:
    """Test role-specific dashboard data"""
    
    def test_admin_dashboard_data(self):
        """Admin can access dashboard data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        token = response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test various admin endpoints
        endpoints = [
            "/api/sales/pending",
            "/api/cases",
            "/api/users",
            "/api/products",
            "/api/tickets/all",
            "/api/reports/dashboard-stats"
        ]
        
        for endpoint in endpoints:
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert resp.status_code == 200, f"Admin failed to access {endpoint}: {resp.text}"
        
        print("✓ Admin can access all dashboard endpoints")
    
    def test_case_manager_dashboard_data(self):
        """Case manager can access their dashboard data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["case_manager"])
        token = response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test case manager endpoints
        endpoints = [
            "/api/cases/my-cases",
            "/api/cases/stats/my-stats",
            "/api/tickets/my-tickets"
        ]
        
        for endpoint in endpoints:
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert resp.status_code == 200, f"Case manager failed to access {endpoint}: {resp.text}"
        
        print("✓ Case manager can access their dashboard endpoints")
    
    def test_partner_dashboard_data(self):
        """Partner can access their dashboard data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["partner"])
        token = response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test partner endpoints
        endpoints = [
            "/api/sales/my-sales",
            "/api/sales/stats",
            "/api/products"
        ]
        
        for endpoint in endpoints:
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert resp.status_code == 200, f"Partner failed to access {endpoint}: {resp.text}"
        
        print("✓ Partner can access their dashboard endpoints")
    
    def test_client_dashboard_data(self):
        """Client can access their dashboard data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        token = response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test client endpoints
        endpoints = [
            "/api/cases/my-cases",
            "/api/tickets/my-tickets",
            "/api/notifications"
        ]
        
        for endpoint in endpoints:
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert resp.status_code == 200, f"Client failed to access {endpoint}: {resp.text}"
        
        print("✓ Client can access their dashboard endpoints")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
