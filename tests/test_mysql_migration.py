"""
LEAMSS Portal MySQL Migration Tests
Comprehensive tests for all API endpoints after MySQL migration
Tests: Authentication, Users, Products, Sales, Cases, Tickets, Notifications, Documents, Reports
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for all 4 roles
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


# ============== FIXTURES ==============
@pytest.fixture
def admin_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture
def manager_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture
def partner_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
    assert response.status_code == 200, f"Partner login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture
def client_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    assert response.status_code == 200, f"Client login failed: {response.text}"
    return response.json()["token"]


# ============== AUTHENTICATION TESTS ==============
class TestAuthentication:
    """Test authentication for all 4 user roles"""
    
    def test_admin_login(self):
        """Test admin login returns token and correct role"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == "admin@leamss.com"
        print(f"✓ Admin login: {data['user']['name']} ({data['user']['role']})")
    
    def test_case_manager_login(self):
        """Test case manager login returns token and correct role"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "case_manager"
        print(f"✓ Case Manager login: {data['user']['name']} ({data['user']['role']})")
    
    def test_partner_login(self):
        """Test partner login returns token and correct role"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "partner"
        print(f"✓ Partner login: {data['user']['name']} ({data['user']['role']})")
    
    def test_client_login(self):
        """Test client login returns token and correct role"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "client"
        print(f"✓ Client login: {data['user']['name']} ({data['user']['role']})")
    
    def test_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected")
    
    def test_get_current_user(self, admin_token):
        """Test /auth/me endpoint returns current user info"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        print(f"✓ Get current user: {data['email']}")


# ============== USERS API TESTS ==============
class TestUsersAPI:
    """Test user management endpoints (admin only)"""
    
    def test_admin_get_all_users(self, admin_token):
        """Test admin can list all users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 4  # At least 4 seeded users
        
        # Verify all roles exist
        roles = set(u["role"] for u in users)
        assert "admin" in roles
        assert "case_manager" in roles
        assert "partner" in roles
        assert "client" in roles
        print(f"✓ Admin retrieved {len(users)} users with roles: {roles}")
    
    def test_non_admin_cannot_list_users(self, partner_token):
        """Test non-admin users cannot list all users"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 403
        print("✓ Non-admin correctly denied access to users list")
    
    def test_get_users_by_role(self, admin_token):
        """Test getting users filtered by role"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users/by-role/case_manager", headers=headers)
        assert response.status_code == 200
        managers = response.json()
        assert isinstance(managers, list)
        assert len(managers) >= 1
        for m in managers:
            assert m["role"] == "case_manager"
        print(f"✓ Retrieved {len(managers)} case managers")
    
    def test_get_ticket_recipients(self, client_token):
        """Test getting potential ticket recipients"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        assert response.status_code == 200
        recipients = response.json()
        assert isinstance(recipients, list)
        print(f"✓ Client can get {len(recipients)} ticket recipients")


# ============== PRODUCTS API TESTS ==============
class TestProductsAPI:
    """Test product CRUD with workflow steps"""
    
    def test_get_products(self, admin_token):
        """Test listing all products"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        print(f"✓ Retrieved {len(products)} products")
        
        # Verify product structure
        if products:
            p = products[0]
            assert "id" in p
            assert "name" in p
            assert "fee" in p
            assert "commission_rate" in p
            assert "commission_type" in p
            assert "workflow_steps" in p
            print(f"  First product: {p['name']} - ${p['fee']} - {p['commission_type']}")
    
    def test_product_has_workflow_steps(self, admin_token):
        """Test products include workflow steps"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        products = response.json()
        
        products_with_steps = [p for p in products if p.get("workflow_steps")]
        if products_with_steps:
            p = products_with_steps[0]
            steps = p["workflow_steps"]
            assert isinstance(steps, list)
            if steps:
                step = steps[0]
                assert "step_name" in step
                assert "step_order" in step
                print(f"✓ Product '{p['name']}' has {len(steps)} workflow steps")
        else:
            print("⚠ No products with workflow steps found")
    
    def test_create_product_fixed_commission(self, admin_token):
        """Test creating product with fixed commission"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        product_data = {
            "name": "TEST_Fixed_Product",
            "description": "Test product with fixed commission",
            "fee": 1000.0,
            "commission_rate": 10.0,
            "commission_type": "fixed"
        }
        response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["commission_type"] == "fixed"
        print(f"✓ Created product with fixed commission: {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/products/{data['id']}", headers=headers)
    
    def test_create_product_percentage_commission(self, admin_token):
        """Test creating product with percentage commission"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        product_data = {
            "name": "TEST_Percentage_Product",
            "description": "Test product with percentage commission",
            "fee": 2000.0,
            "commission_rate": 15.0,
            "commission_type": "percentage"
        }
        response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["commission_type"] == "percentage"
        print(f"✓ Created product with percentage commission: {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/products/{data['id']}", headers=headers)
    
    def test_create_product_tiered_commission(self, admin_token):
        """Test creating product with tiered commission"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        product_data = {
            "name": "TEST_Tiered_Product",
            "description": "Test product with tiered commission",
            "fee": 3000.0,
            "commission_rate": 5.0,
            "commission_type": "tiered",
            "commission_tiers": [
                {"min_sales": 0, "max_sales": 10, "commission_rate": 5.0},
                {"min_sales": 11, "max_sales": 50, "commission_rate": 7.0}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["commission_type"] == "tiered"
        print(f"✓ Created product with tiered commission: {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/products/{data['id']}", headers=headers)


# ============== SALES API TESTS ==============
class TestSalesAPI:
    """Test sales management endpoints"""
    
    def test_admin_get_all_sales(self, admin_token):
        """Test admin can list all sales"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales", headers=headers)
        assert response.status_code == 200
        sales = response.json()
        assert isinstance(sales, list)
        print(f"✓ Admin retrieved {len(sales)} sales")
    
    def test_admin_get_pending_sales(self, admin_token):
        """Test admin can list pending sales"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/pending", headers=headers)
        assert response.status_code == 200
        sales = response.json()
        assert isinstance(sales, list)
        for s in sales:
            assert s["status"] == "pending"
        print(f"✓ Admin retrieved {len(sales)} pending sales")
    
    def test_partner_get_my_sales(self, partner_token):
        """Test partner can list their own sales"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/my-sales", headers=headers)
        assert response.status_code == 200
        sales = response.json()
        assert isinstance(sales, list)
        print(f"✓ Partner retrieved {len(sales)} of their sales")
    
    def test_sales_stats(self, admin_token):
        """Test sales statistics endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales/stats", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "total_sales" in stats
        assert "pending_sales" in stats
        print(f"✓ Sales stats: {stats['total_sales']} total, {stats['pending_sales']} pending")


# ============== CASES API TESTS ==============
class TestCasesAPI:
    """Test case management endpoints"""
    
    def test_admin_get_all_cases(self, admin_token):
        """Test admin can list all cases"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✓ Admin retrieved {len(cases)} cases")
        
        # Verify case structure
        if cases:
            c = cases[0]
            assert "id" in c
            assert "case_id" in c
            assert "client_name" in c
            assert "product_name" in c
            assert "status" in c
            assert "steps" in c
            print(f"  First case: {c['case_id']} - {c['client_name']} - {c['status']}")
    
    def test_manager_get_my_cases(self, manager_token):
        """Test case manager can list assigned cases"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✓ Case manager retrieved {len(cases)} assigned cases")
    
    def test_client_get_my_cases(self, client_token):
        """Test client can list their cases"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✓ Client retrieved {len(cases)} of their cases")
    
    def test_partner_get_my_cases(self, partner_token):
        """Test partner can list cases from their sales"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✓ Partner retrieved {len(cases)} cases from their sales")
    
    def test_get_case_detail(self, admin_token):
        """Test getting case details by ID"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get a case
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        cases = response.json()
        
        if cases:
            case_id = cases[0]["id"]
            response = requests.get(f"{BASE_URL}/api/cases/{case_id}", headers=headers)
            assert response.status_code == 200
            case = response.json()
            assert case["id"] == case_id
            assert "steps" in case
            print(f"✓ Retrieved case detail: {case['case_id']} with {len(case['steps'])} steps")
        else:
            print("⚠ No cases found to test detail view")


# ============== TICKETS API TESTS ==============
class TestTicketsAPI:
    """Test ticketing system endpoints"""
    
    def test_client_get_my_tickets(self, client_token):
        """Test client can list their tickets"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Client retrieved {len(tickets)} tickets")
    
    def test_admin_get_all_tickets(self, admin_token):
        """Test admin can list all tickets"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/all", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Admin retrieved {len(tickets)} tickets")
    
    def test_ticket_stats(self, admin_token):
        """Test ticket statistics endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/stats", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "total" in stats
        assert "open" in stats
        print(f"✓ Ticket stats: {stats['total']} total, {stats['open']} open")
    
    def test_create_ticket(self, client_token):
        """Test creating a new ticket"""
        headers = {"Authorization": f"Bearer {client_token}"}
        ticket_data = {
            "subject": "TEST_Ticket_Subject",
            "description": "This is a test ticket description",
            "category": "general",
            "priority": "medium",
            "target_role": "admin"
        }
        response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ Created ticket: {data['id']}")
    
    def test_get_ticket_detail(self, admin_token):
        """Test getting ticket details"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get a ticket
        response = requests.get(f"{BASE_URL}/api/tickets/all", headers=headers)
        tickets = response.json()
        
        if tickets:
            ticket_id = tickets[0]["id"]
            response = requests.get(f"{BASE_URL}/api/tickets/{ticket_id}", headers=headers)
            assert response.status_code == 200
            ticket = response.json()
            assert "id" in ticket
            assert "subject" in ticket
            assert "messages" in ticket
            assert "attachments" in ticket
            assert "activity_log" in ticket
            print(f"✓ Retrieved ticket detail: {ticket['subject']}")
        else:
            print("⚠ No tickets found to test detail view")


# ============== NOTIFICATIONS API TESTS ==============
class TestNotificationsAPI:
    """Test notification system endpoints"""
    
    def test_get_notifications(self, admin_token):
        """Test getting user notifications"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200
        notifications = response.json()
        assert isinstance(notifications, list)
        print(f"✓ Retrieved {len(notifications)} notifications")
        
        # Verify notification structure
        if notifications:
            n = notifications[0]
            assert "id" in n
            assert "title" in n
            assert "message" in n
            assert "type" in n
            assert "is_read" in n
    
    def test_get_unread_notifications(self, admin_token):
        """Test getting unread notifications"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications/unread", headers=headers)
        assert response.status_code == 200
        notifications = response.json()
        assert isinstance(notifications, list)
        for n in notifications:
            assert n["is_read"] == False
        print(f"✓ Retrieved {len(notifications)} unread notifications")
    
    def test_mark_all_read(self, admin_token):
        """Test marking all notifications as read"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.put(f"{BASE_URL}/api/notifications/read-all", headers=headers)
        assert response.status_code == 200
        print("✓ Marked all notifications as read")


# ============== DOCUMENTS API TESTS ==============
class TestDocumentsAPI:
    """Test document management endpoints"""
    
    def test_get_case_documents(self, admin_token):
        """Test getting documents for a case"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get a case
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        cases = response.json()
        
        if cases:
            case_id = cases[0]["id"]
            response = requests.get(f"{BASE_URL}/api/documents/case/{case_id}", headers=headers)
            assert response.status_code == 200
            documents = response.json()
            assert isinstance(documents, list)
            print(f"✓ Retrieved {len(documents)} documents for case")
        else:
            print("⚠ No cases found to test document retrieval")


# ============== REPORTS API TESTS ==============
class TestReportsAPI:
    """Test reporting endpoints"""
    
    def test_admin_dashboard_stats(self, admin_token):
        """Test admin dashboard statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/dashboard-stats", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "total_users" in stats
        assert "total_cases" in stats
        assert "total_sales" in stats
        assert "total_revenue" in stats
        print(f"✓ Dashboard stats: {stats['total_users']} users, {stats['total_cases']} cases, ${stats['total_revenue']} revenue")
    
    def test_partner_commissions_report(self, admin_token):
        """Test partner commissions report"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/partner-commissions", headers=headers)
        assert response.status_code == 200
        commissions = response.json()
        assert isinstance(commissions, list)
        print(f"✓ Retrieved commission data for {len(commissions)} partners")
    
    def test_sales_report(self, admin_token):
        """Test sales report"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/sales", headers=headers)
        assert response.status_code == 200
        sales = response.json()
        assert isinstance(sales, list)
        print(f"✓ Sales report: {len(sales)} sales records")
    
    def test_commission_report(self, admin_token):
        """Test commission report"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/commission", headers=headers)
        assert response.status_code == 200
        commissions = response.json()
        assert isinstance(commissions, list)
        print(f"✓ Commission report: {len(commissions)} records")


# ============== ROLE-SPECIFIC DASHBOARD STATS ==============
class TestRoleDashboardStats:
    """Test role-specific dashboard statistics"""
    
    def test_admin_stats_dashboard(self, admin_token):
        """Test admin dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "total_users" in stats
        assert "pending_sales" in stats
        assert "active_cases" in stats
        print(f"✓ Admin stats: {stats['pending_sales']} pending sales, {stats['active_cases']} active cases")
    
    def test_partner_stats_dashboard(self, partner_token):
        """Test partner dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/partner-dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "total_sales" in stats
        assert "total_commission" in stats
        print(f"✓ Partner stats: {stats['total_sales']} sales, ${stats['total_commission']} commission")
    
    def test_case_manager_stats_dashboard(self, manager_token):
        """Test case manager dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/case-manager-dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "total_cases" in stats
        assert "active_cases" in stats
        print(f"✓ Manager stats: {stats['total_cases']} total, {stats['active_cases']} active cases")
    
    def test_client_stats_dashboard(self, client_token):
        """Test client dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/client-dashboard", headers=headers)
        assert response.status_code == 200
        stats = response.json()
        assert "total_cases" in stats
        assert "active_cases" in stats
        print(f"✓ Client stats: {stats['total_cases']} total, {stats['active_cases']} active cases")


# ============== HEALTH CHECK ==============
class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Test API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        print(f"✓ Health check: {data['status']}, DB: {data['database']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
