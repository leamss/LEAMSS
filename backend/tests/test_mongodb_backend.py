"""
LEAMSS Immigration Portal - MongoDB Backend Tests
Tests all API endpoints after migration from MySQL to MongoDB
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

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


class TestHealthCheck:
    """Health check endpoint tests"""
    
    def test_health_endpoint(self):
        """Test API health and MongoDB connection"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        print(f"✓ Health check passed: {data}")


class TestAuthentication:
    """Authentication tests for all 4 roles"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful: {data['user']['name']}")
    
    def test_case_manager_login(self):
        """Test case manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MANAGER_EMAIL,
            "password": MANAGER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print(f"✓ Case Manager login successful: {data['user']['name']}")
    
    def test_partner_login(self):
        """Test partner login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTNER_EMAIL,
            "password": PARTNER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"✓ Partner login successful: {data['user']['name']}")
    
    def test_client_login(self):
        """Test client login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print(f"✓ Client login successful: {data['user']['name']}")
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")


@pytest.fixture
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Admin login failed")


@pytest.fixture
def manager_token():
    """Get case manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGER_EMAIL, "password": MANAGER_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Manager login failed")


@pytest.fixture
def partner_token():
    """Get partner auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARTNER_EMAIL, "password": PARTNER_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Partner login failed")


@pytest.fixture
def client_token():
    """Get client auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CLIENT_EMAIL, "password": CLIENT_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Client login failed")


class TestAdminDashboard:
    """Admin dashboard and stats tests"""
    
    def test_admin_dashboard_stats(self, admin_token):
        """Test admin dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/admin-dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "pending_sales" in data
        assert "active_cases" in data
        assert "total_revenue" in data
        assert "total_commission" in data
        print(f"✓ Admin dashboard stats: pending_sales={data['pending_sales']}, revenue={data['total_revenue']}")
    
    def test_get_all_sales(self, admin_token):
        """Test getting all sales"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ All sales retrieved: {len(data)} sales")
    
    def test_get_sales_with_status_filter(self, admin_token):
        """Test getting sales with status filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales?status=pending", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for sale in data:
            assert sale["status"] == "pending"
        print(f"✓ Pending sales filtered: {len(data)} sales")
    
    def test_get_all_cases(self, admin_token):
        """Test getting all cases"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ All cases retrieved: {len(data)} cases")
    
    def test_get_all_users(self, admin_token):
        """Test getting all users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 4  # At least 4 seeded users
        print(f"✓ All users retrieved: {len(data)} users")


class TestProducts:
    """Products CRUD tests"""
    
    def test_get_products(self, admin_token):
        """Test getting all products"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # At least 3 seeded products
        for product in data:
            assert "workflow_steps" in product
        print(f"✓ Products retrieved: {len(data)} products")
    
    def test_create_product(self, admin_token):
        """Test creating a new product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        product_data = {
            "name": f"TEST_Product_{uuid.uuid4().hex[:6]}",
            "description": "Test product for testing",
            "category": "test",
            "base_fee": 10000,
            "workflow_steps": [
                {"step_name": "Step 1", "step_order": 1, "description": "First step", "duration_days": 5}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/products", headers=headers, json=product_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Product created: {data['id']}")
        return data["id"]
    
    def test_update_product(self, admin_token):
        """Test updating a product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # First create a product
        product_data = {
            "name": f"TEST_Update_{uuid.uuid4().hex[:6]}",
            "description": "To be updated",
            "category": "test",
            "base_fee": 5000
        }
        create_resp = requests.post(f"{BASE_URL}/api/products", headers=headers, json=product_data)
        product_id = create_resp.json()["id"]
        
        # Update it
        update_data = {"name": "TEST_Updated_Product", "base_fee": 7500}
        response = requests.put(f"{BASE_URL}/api/products/{product_id}", headers=headers, json=update_data)
        assert response.status_code == 200
        print(f"✓ Product updated: {product_id}")
    
    def test_delete_product(self, admin_token):
        """Test deleting a product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # First create a product
        product_data = {
            "name": f"TEST_Delete_{uuid.uuid4().hex[:6]}",
            "description": "To be deleted",
            "category": "test",
            "base_fee": 1000
        }
        create_resp = requests.post(f"{BASE_URL}/api/products", headers=headers, json=product_data)
        product_id = create_resp.json()["id"]
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/api/products/{product_id}", headers=headers)
        assert response.status_code == 200
        print(f"✓ Product deleted: {product_id}")


class TestSales:
    """Sales creation and approval tests"""
    
    def test_create_sale_bank_transfer(self, partner_token, admin_token):
        """Test creating a sale with bank_transfer payment method"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        
        # Get a product first
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        products = requests.get(f"{BASE_URL}/api/products", headers=admin_headers).json()
        product_id = products[0]["id"]
        
        sale_data = {
            "client_name": f"TEST_Client_{uuid.uuid4().hex[:6]}",
            "client_email": f"test_{uuid.uuid4().hex[:6]}@test.com",
            "client_mobile": "+1-555-9999",
            "product_id": product_id,
            "fee_amount": 50000,
            "amount_received": 25000,
            "payment_method": "bank_transfer",
            "payment_reference": "TXN-TEST-001",
            "agreement_signed": True
        }
        response = requests.post(f"{BASE_URL}/api/sales", headers=headers, data=sale_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Sale created with bank_transfer: {data['id']}")
        return data["id"]
    
    def test_create_sale_online_payment(self, partner_token, admin_token):
        """Test creating a sale with online payment method"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        products = requests.get(f"{BASE_URL}/api/products", headers=admin_headers).json()
        product_id = products[0]["id"]
        
        sale_data = {
            "client_name": f"TEST_Online_{uuid.uuid4().hex[:6]}",
            "client_email": f"online_{uuid.uuid4().hex[:6]}@test.com",
            "client_mobile": "+1-555-8888",
            "product_id": product_id,
            "fee_amount": 75000,
            "amount_received": 75000,
            "payment_method": "online",
            "payment_reference": "ONLINE-TEST-001",
            "agreement_signed": True
        }
        response = requests.post(f"{BASE_URL}/api/sales", headers=headers, data=sale_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Sale created with online payment: {data['id']}")
    
    def test_approve_sale_returns_credentials(self, partner_token, admin_token):
        """Test that approving a sale returns client credentials for new clients"""
        # Create a sale first
        partner_headers = {"Authorization": f"Bearer {partner_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        products = requests.get(f"{BASE_URL}/api/products", headers=admin_headers).json()
        product_id = products[0]["id"]
        
        unique_email = f"newclient_{uuid.uuid4().hex[:8]}@test.com"
        sale_data = {
            "client_name": f"TEST_NewClient_{uuid.uuid4().hex[:6]}",
            "client_email": unique_email,
            "client_mobile": "+1-555-7777",
            "product_id": product_id,
            "fee_amount": 100000,
            "amount_received": 50000,
            "payment_method": "cash",
            "agreement_signed": True
        }
        create_resp = requests.post(f"{BASE_URL}/api/sales", headers=partner_headers, data=sale_data)
        sale_id = create_resp.json()["id"]
        
        # Get case managers
        users = requests.get(f"{BASE_URL}/api/users?role=case_manager", headers=admin_headers).json()
        manager_id = users[0]["id"] if users else None
        
        # Approve the sale
        approve_data = {
            "sale_id": sale_id,
            "status": "approved",
            "case_manager_id": manager_id
        }
        response = requests.post(f"{BASE_URL}/api/sales/approve", headers=admin_headers, json=approve_data)
        assert response.status_code == 200
        data = response.json()
        assert "client_credentials" in data
        assert data["client_credentials"]["email"] == unique_email
        assert data["client_credentials"]["password"] == "Client@123"
        print(f"✓ Sale approved with client credentials: {data['client_credentials']['email']}")


class TestCaseManager:
    """Case manager specific tests"""
    
    def test_my_cases(self, manager_token):
        """Test case manager my-cases endpoint"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Case manager my-cases: {len(data)} cases")
    
    def test_case_manager_stats(self, manager_token):
        """Test case manager dashboard stats"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/case-manager-dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_cases" in data
        assert "my_cases" in data
        print(f"✓ Case manager stats: {data['my_cases']} cases")
    
    def test_update_workflow_step(self, manager_token, admin_token):
        """Test updating workflow step status"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        manager_headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Get a case
        cases = requests.get(f"{BASE_URL}/api/cases", headers=admin_headers).json()
        if not cases:
            pytest.skip("No cases available")
        
        case = cases[0]
        if not case.get("steps"):
            pytest.skip("No steps in case")
        
        step_name = case["steps"][0]["step_name"]
        
        update_data = {
            "case_id": case["id"],
            "step_name": step_name,
            "status": "in_progress",
            "notes": "Test update from pytest"
        }
        response = requests.post(f"{BASE_URL}/api/cases/update-step", headers=manager_headers, json=update_data)
        assert response.status_code == 200
        print(f"✓ Workflow step updated: {step_name}")


class TestInformationSheet:
    """Information sheet CRUD tests"""
    
    def test_save_and_retrieve_information_sheet(self, manager_token, admin_token):
        """Test saving and retrieving information sheet"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        manager_headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Get a case
        cases = requests.get(f"{BASE_URL}/api/cases", headers=admin_headers).json()
        if not cases:
            pytest.skip("No cases available")
        
        case_id = cases[0]["id"]
        
        # Save information sheet
        sheet_data = {
            "full_name": "Test Client Name",
            "date_of_birth": "1990-01-15",
            "nationality": "Canadian",
            "passport_number": "AB123456",
            "email": "testclient@test.com",
            "phone": "+1-555-1234",
            "address": "123 Test Street",
            "education_level": "Bachelor's Degree",
            "work_experience": "5 years in IT"
        }
        save_resp = requests.post(f"{BASE_URL}/api/cases/{case_id}/information-sheet", 
                                  headers=manager_headers, json=sheet_data)
        assert save_resp.status_code == 200
        
        # Retrieve it
        get_resp = requests.get(f"{BASE_URL}/api/cases/{case_id}/information-sheet", headers=manager_headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["exists"] == True
        assert data["data"]["full_name"] == "Test Client Name"
        print(f"✓ Information sheet saved and retrieved for case {case_id}")


class TestDocuments:
    """Document upload and download tests"""
    
    def test_upload_document(self, client_token, admin_token):
        """Test document upload"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        client_headers = {"Authorization": f"Bearer {client_token}"}
        
        # Get a case for the client
        cases = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=client_headers).json()
        if not cases:
            pytest.skip("No cases for client")
        
        case_id = cases[0]["id"]
        
        # Create a test file
        files = {"file": ("test_document.txt", b"Test document content", "text/plain")}
        data = {"case_id": case_id, "step_name": "Profile Creation", "document_type": "general"}
        
        response = requests.post(f"{BASE_URL}/api/documents/upload", 
                                headers=client_headers, files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert "id" in result
        print(f"✓ Document uploaded: {result['id']}")
        return result["id"]
    
    def test_get_case_documents(self, client_token, admin_token):
        """Test getting documents for a case"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        client_headers = {"Authorization": f"Bearer {client_token}"}
        
        cases = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=client_headers).json()
        if not cases:
            pytest.skip("No cases for client")
        
        case_id = cases[0]["id"]
        response = requests.get(f"{BASE_URL}/api/documents/case/{case_id}", headers=client_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Case documents retrieved: {len(data)} documents")


class TestCaseManagerAssignment:
    """Case manager assignment tests"""
    
    def test_assign_case_manager(self, admin_token):
        """Test assigning case manager to a case"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get cases and case managers
        cases = requests.get(f"{BASE_URL}/api/cases", headers=headers).json()
        managers = requests.get(f"{BASE_URL}/api/users?role=case_manager", headers=headers).json()
        
        if not cases or not managers:
            pytest.skip("No cases or managers available")
        
        case_id = cases[0]["id"]
        manager_id = managers[0]["id"]
        
        response = requests.put(f"{BASE_URL}/api/cases/{case_id}/assign-manager?case_manager_id={manager_id}", 
                               headers=headers)
        assert response.status_code == 200
        print(f"✓ Case manager assigned to case {case_id}")


class TestActivityLogs:
    """Activity/Audit logs tests"""
    
    def test_get_activity_logs(self, admin_token):
        """Test getting activity logs"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/activity/logs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Activity logs retrieved: {len(data)} logs")
    
    def test_get_activity_stats(self, admin_token):
        """Test getting activity stats"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/activity/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_activities" in data
        assert "activities_by_type" in data
        print(f"✓ Activity stats: {data['total_activities']} total activities")


class TestAnalytics:
    """Analytics endpoints tests"""
    
    def test_sales_trend(self, admin_token):
        """Test sales trend analytics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/sales-trend", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        print(f"✓ Sales trend data: {len(data['data'])} data points")
    
    def test_sales_by_status(self, admin_token):
        """Test sales by status analytics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/sales-by-status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        print(f"✓ Sales by status: {len(data['data'])} statuses")
    
    def test_top_products(self, admin_token):
        """Test top products analytics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/top-products", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        print(f"✓ Top products: {len(data['data'])} products")
    
    def test_top_partners(self, admin_token):
        """Test top partners analytics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/top-partners", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        print(f"✓ Top partners: {len(data['data'])} partners")


class TestGlobalSearch:
    """Global search tests"""
    
    def test_global_search(self, admin_token):
        """Test global search"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/search/global?q=Canada", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_count" in data
        print(f"✓ Global search results: {data['total_count']} items")
    
    def test_quick_search(self, admin_token):
        """Test quick search"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/search/quick?q=admin", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Quick search results: {len(data)} items")


class TestPartnerCommissions:
    """Partner commission tests"""
    
    def test_partner_dashboard_stats(self, partner_token):
        """Test partner dashboard stats"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/partner-dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_sales" in data
        assert "total_commission" in data
        print(f"✓ Partner stats: {data['total_sales']} sales, ${data['total_commission']} commission")
    
    def test_partner_report(self, admin_token):
        """Test partner commission report"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/partner-report", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_sales" in data
        assert "total_commission" in data
        print(f"✓ Partner report: {data['total_sales']} sales, ${data['total_commission']} commission")
    
    def test_partner_commissions_report(self, admin_token):
        """Test partner commissions breakdown"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/partner-commissions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Partner commissions: {len(data)} partners")


class TestTickets:
    """Tickets CRUD tests"""
    
    def test_get_tickets(self, admin_token):
        """Test getting tickets"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Tickets retrieved: {len(data)} tickets")
    
    def test_create_ticket(self, client_token):
        """Test creating a ticket"""
        headers = {"Authorization": f"Bearer {client_token}"}
        ticket_data = {
            "subject": f"TEST_Ticket_{uuid.uuid4().hex[:6]}",
            "description": "Test ticket description",
            "priority": "medium",
            "category": "general"
        }
        response = requests.post(f"{BASE_URL}/api/tickets", headers=headers, json=ticket_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Ticket created: {data['id']}")
        return data["id"]


class TestNotifications:
    """Notifications tests"""
    
    def test_get_notifications(self, client_token):
        """Test getting notifications"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Notifications retrieved: {len(data)} notifications")


class TestSettings:
    """Settings tests"""
    
    def test_get_settings(self, admin_token):
        """Test getting settings"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/settings", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "company_name" in data or "default_commission_rate" in data
        print(f"✓ Settings retrieved")


class TestImpersonation:
    """User impersonation tests"""
    
    def test_admin_can_impersonate(self, admin_token):
        """Test admin can impersonate other users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get a user to impersonate
        users = requests.get(f"{BASE_URL}/api/users?role=client", headers=headers).json()
        if not users:
            pytest.skip("No users to impersonate")
        
        user_id = users[0]["id"]
        response = requests.post(f"{BASE_URL}/api/auth/impersonate/{user_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print(f"✓ Admin impersonated user: {data['user']['name']}")
    
    def test_non_admin_cannot_impersonate(self, partner_token, admin_token):
        """Test non-admin cannot impersonate"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        users = requests.get(f"{BASE_URL}/api/users?role=client", headers=admin_headers).json()
        if not users:
            pytest.skip("No users to impersonate")
        
        user_id = users[0]["id"]
        response = requests.post(f"{BASE_URL}/api/auth/impersonate/{user_id}", headers=headers)
        assert response.status_code == 403
        print("✓ Non-admin correctly denied impersonation")


class TestClientDashboard:
    """Client dashboard tests"""
    
    def test_client_dashboard_stats(self, client_token):
        """Test client dashboard stats"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/client-dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_cases" in data
        assert "active_cases" in data
        print(f"✓ Client stats: {data['total_cases']} cases")
    
    def test_client_my_cases(self, client_token):
        """Test client my-cases endpoint"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Client my-cases: {len(data)} cases")


class TestRequestAdditionalDocuments:
    """Additional document request tests"""
    
    def test_request_additional_document(self, manager_token, admin_token):
        """Test requesting additional documents"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        manager_headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Get a case
        cases = requests.get(f"{BASE_URL}/api/cases", headers=admin_headers).json()
        if not cases:
            pytest.skip("No cases available")
        
        case_id = cases[0]["id"]
        
        request_data = {
            "case_id": case_id,
            "document_name": "TEST_Additional_Document",
            "description": "Please provide this document",
            "step_order": 1,
            "doc_type": "general"
        }
        response = requests.post(f"{BASE_URL}/api/cases/request-document", 
                                headers=manager_headers, json=request_data)
        assert response.status_code == 200
        print(f"✓ Additional document requested for case {case_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
