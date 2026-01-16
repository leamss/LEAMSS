"""
LEAMSS Portal API Tests
Tests for: Authentication, Products (with commission types), Sales, Cases, Documents, Tickets, Notifications
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


class TestAuthentication:
    """Test authentication endpoints for all user roles"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful - role: {data['user']['role']}")
    
    def test_case_manager_login(self):
        """Test case manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200, f"Case manager login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "case_manager"
        print(f"✓ Case manager login successful - role: {data['user']['role']}")
    
    def test_partner_login(self):
        """Test partner login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "partner"
        print(f"✓ Partner login successful - role: {data['user']['role']}")
    
    def test_client_login(self):
        """Test client login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "client"
        print(f"✓ Client login successful - role: {data['user']['role']}")
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected with 401")


class TestProducts:
    """Test product CRUD operations with commission types"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_get_products(self, admin_token):
        """Test fetching all products"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        print(f"✓ Get products successful - found {len(products)} products")
        return products
    
    def test_create_product_fixed_commission(self, admin_token):
        """Test creating product with fixed commission type"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        product_data = {
            "name": "TEST_Fixed_Commission_Product",
            "description": "Test product with fixed commission",
            "fee": 1000.0,
            "commission_rate": 10.0,
            "commission_type": "fixed"
        }
        response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=headers)
        assert response.status_code == 200, f"Create product failed: {response.text}"
        data = response.json()
        assert data["name"] == product_data["name"]
        assert data["commission_type"] == "fixed"
        assert data["commission_rate"] == 10.0
        print(f"✓ Created product with fixed commission: {data['name']}, type: {data['commission_type']}")
        return data["id"]
    
    def test_create_product_tiered_commission(self, admin_token):
        """Test creating product with tiered commission type"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        product_data = {
            "name": "TEST_Tiered_Commission_Product",
            "description": "Test product with tiered commission",
            "fee": 2000.0,
            "commission_rate": 5.0,
            "commission_type": "tiered",
            "commission_tiers": [
                {"min_sales": 0, "max_sales": 10, "rate": 5.0},
                {"min_sales": 11, "max_sales": 50, "rate": 7.0},
                {"min_sales": 51, "max_sales": 100, "rate": 10.0}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=headers)
        assert response.status_code == 200, f"Create tiered product failed: {response.text}"
        data = response.json()
        assert data["commission_type"] == "tiered"
        assert len(data["commission_tiers"]) == 3
        print(f"✓ Created product with tiered commission: {data['name']}, tiers: {len(data['commission_tiers'])}")
        return data["id"]
    
    def test_create_product_custom_commission(self, admin_token):
        """Test creating product with custom commission type"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        product_data = {
            "name": "TEST_Custom_Commission_Product",
            "description": "Test product with custom per-partner commission",
            "fee": 3000.0,
            "commission_rate": 8.0,
            "commission_type": "custom"
        }
        response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=headers)
        assert response.status_code == 200, f"Create custom product failed: {response.text}"
        data = response.json()
        assert data["commission_type"] == "custom"
        print(f"✓ Created product with custom commission: {data['name']}, type: {data['commission_type']}")
        return data["id"]
    
    def test_verify_commission_types_in_products_list(self, admin_token):
        """Verify commission_type field is returned in products list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200
        products = response.json()
        
        # Check that commission_type field exists in products
        for product in products:
            assert "commission_type" in product, f"Product {product['name']} missing commission_type field"
            assert product["commission_type"] in ["fixed", "tiered", "custom"], f"Invalid commission_type: {product['commission_type']}"
        
        print(f"✓ All {len(products)} products have valid commission_type field")
    
    def test_delete_test_products(self, admin_token):
        """Cleanup: Delete test products"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        products = response.json()
        
        deleted_count = 0
        for product in products:
            if product["name"].startswith("TEST_"):
                del_response = requests.delete(f"{BASE_URL}/api/products/{product['id']}", headers=headers)
                if del_response.status_code == 200:
                    deleted_count += 1
        
        print(f"✓ Cleanup: Deleted {deleted_count} test products")


class TestSalesApproval:
    """Test sales approval workflow with email notification integration"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def partner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        return response.json()["token"]
    
    def test_get_pending_sales(self, admin_token):
        """Test fetching pending sales"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/pending", headers=headers)
        assert response.status_code == 200
        sales = response.json()
        assert isinstance(sales, list)
        print(f"✓ Get pending sales successful - found {len(sales)} pending sales")
    
    def test_get_partner_sales(self, partner_token):
        """Test partner can view their sales"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/my-sales", headers=headers)
        assert response.status_code == 200
        sales = response.json()
        assert isinstance(sales, list)
        print(f"✓ Partner sales retrieved - found {len(sales)} sales")
    
    def test_get_case_managers(self, admin_token):
        """Test fetching case managers for sale approval"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users/case-managers", headers=headers)
        assert response.status_code == 200
        managers = response.json()
        assert isinstance(managers, list)
        assert len(managers) > 0, "No case managers found"
        print(f"✓ Case managers retrieved - found {len(managers)} managers")
        return managers


class TestCases:
    """Test case management endpoints"""
    
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
    
    def test_admin_get_all_cases(self, admin_token):
        """Test admin can view all cases"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✓ Admin retrieved all cases - found {len(cases)} cases")
        return cases
    
    def test_manager_get_my_cases(self, manager_token):
        """Test case manager can view assigned cases"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✓ Case manager retrieved assigned cases - found {len(cases)} cases")
        return cases
    
    def test_client_get_my_cases(self, client_token):
        """Test client can view their cases"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✓ Client retrieved their cases - found {len(cases)} cases")
        return cases
    
    def test_case_has_workflow_steps(self, admin_token):
        """Test that cases have workflow steps"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        cases = response.json()
        
        if len(cases) > 0:
            case = cases[0]
            assert "steps" in case, "Case missing steps field"
            assert "current_step" in case, "Case missing current_step field"
            print(f"✓ Case {case['case_id']} has {len(case.get('steps', []))} workflow steps")
        else:
            print("⚠ No cases found to verify workflow steps")


class TestDocuments:
    """Test document management endpoints"""
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_get_case_documents(self, admin_token):
        """Test fetching documents for a case"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get a case
        cases_response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        cases = cases_response.json()
        
        if len(cases) > 0:
            case_id = cases[0]["id"]
            response = requests.get(f"{BASE_URL}/api/documents/case/{case_id}", headers=headers)
            assert response.status_code == 200
            documents = response.json()
            assert isinstance(documents, list)
            print(f"✓ Retrieved {len(documents)} documents for case")
        else:
            print("⚠ No cases found to test document retrieval")


class TestTickets:
    """Test ticketing system endpoints"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_get_my_tickets(self, client_token):
        """Test client can view their tickets"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Client retrieved tickets - found {len(tickets)} tickets")
    
    def test_admin_get_all_tickets(self, admin_token):
        """Test admin can view all tickets"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Admin retrieved all tickets - found {len(tickets)} tickets")


class TestNotifications:
    """Test notification system endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_get_notifications(self, admin_token):
        """Test fetching user notifications"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200
        notifications = response.json()
        assert isinstance(notifications, list)
        print(f"✓ Retrieved {len(notifications)} notifications")


class TestDashboardStats:
    """Test dashboard statistics endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def partner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        return response.json()["token"]
    
    def test_admin_dashboard_stats(self, admin_token):
        """Test admin dashboard statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "pending_sales" in stats
        assert "active_cases" in stats
        assert "total_revenue" in stats
        print(f"✓ Admin stats: {stats['pending_sales']} pending sales, {stats['active_cases']} active cases")
    
    def test_partner_dashboard_stats(self, partner_token):
        """Test partner dashboard statistics"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "total_sales" in stats
        assert "total_commission" in stats
        print(f"✓ Partner stats: {stats['total_sales']} total sales, ${stats['total_commission']} commission")
    
    def test_manager_dashboard_stats(self, manager_token):
        """Test case manager dashboard statistics"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "my_cases" in stats
        print(f"✓ Manager stats: {stats['my_cases']} assigned cases")
    
    def test_client_dashboard_stats(self, client_token):
        """Test client dashboard statistics"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        # Client stats may vary based on whether they have a case
        print(f"✓ Client stats retrieved successfully")


class TestUserManagement:
    """Test user management endpoints (admin only)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_get_all_users(self, admin_token):
        """Test admin can view all users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0
        print(f"✓ Admin retrieved all users - found {len(users)} users")
        
        # Verify user roles
        roles = set(u["role"] for u in users)
        print(f"  User roles found: {roles}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
