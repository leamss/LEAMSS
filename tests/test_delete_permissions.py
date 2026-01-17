"""
Test delete permissions - Only Admin should be able to delete users and products
Tests for LEAMSS Portal iteration 10
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://immigration-hub-3.preview.emergentagent.com')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
CASE_MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


class TestDeletePermissions:
    """Test that delete operations are restricted to Admin only"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, email, password):
        """Login and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_auth_header(self, token):
        """Get authorization header"""
        return {"Authorization": f"Bearer {token}"}
    
    # ============ ADMIN DELETE TESTS (Should succeed) ============
    
    def test_admin_can_login(self):
        """Test admin can login"""
        token = self.login(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        assert token is not None, "Admin login failed"
        print(f"SUCCESS: Admin login successful")
    
    def test_admin_can_access_users_list(self):
        """Test admin can access users list"""
        token = self.login(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        assert token is not None
        
        response = self.session.get(
            f"{BASE_URL}/api/users",
            headers=self.get_auth_header(token)
        )
        assert response.status_code == 200, f"Admin should access users list, got {response.status_code}"
        users = response.json()
        assert isinstance(users, list), "Users should be a list"
        print(f"SUCCESS: Admin can access users list ({len(users)} users)")
    
    def test_admin_can_access_products_list(self):
        """Test admin can access products list"""
        token = self.login(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        assert token is not None
        
        response = self.session.get(
            f"{BASE_URL}/api/products",
            headers=self.get_auth_header(token)
        )
        assert response.status_code == 200, f"Admin should access products list, got {response.status_code}"
        products = response.json()
        assert isinstance(products, list), "Products should be a list"
        print(f"SUCCESS: Admin can access products list ({len(products)} products)")
    
    # ============ CASE MANAGER DELETE TESTS (Should fail) ============
    
    def test_case_manager_can_login(self):
        """Test case manager can login"""
        token = self.login(CASE_MANAGER_CREDS["email"], CASE_MANAGER_CREDS["password"])
        assert token is not None, "Case Manager login failed"
        print(f"SUCCESS: Case Manager login successful")
    
    def test_case_manager_cannot_delete_user(self):
        """Test case manager cannot delete users"""
        token = self.login(CASE_MANAGER_CREDS["email"], CASE_MANAGER_CREDS["password"])
        assert token is not None
        
        # Try to delete a user (use a fake ID to avoid actually deleting)
        response = self.session.delete(
            f"{BASE_URL}/api/users/fake-user-id-12345",
            headers=self.get_auth_header(token)
        )
        # Should get 403 Forbidden (not authorized) or 401
        assert response.status_code in [401, 403], f"Case Manager should NOT be able to delete users, got {response.status_code}"
        print(f"SUCCESS: Case Manager correctly denied delete user access (status: {response.status_code})")
    
    def test_case_manager_cannot_delete_product(self):
        """Test case manager cannot delete products"""
        token = self.login(CASE_MANAGER_CREDS["email"], CASE_MANAGER_CREDS["password"])
        assert token is not None
        
        # Try to delete a product (use a fake ID to avoid actually deleting)
        response = self.session.delete(
            f"{BASE_URL}/api/products/fake-product-id-12345",
            headers=self.get_auth_header(token)
        )
        # Should get 403 Forbidden (not authorized) or 401
        assert response.status_code in [401, 403], f"Case Manager should NOT be able to delete products, got {response.status_code}"
        print(f"SUCCESS: Case Manager correctly denied delete product access (status: {response.status_code})")
    
    def test_case_manager_cannot_access_users_list(self):
        """Test case manager cannot access full users list (admin only)"""
        token = self.login(CASE_MANAGER_CREDS["email"], CASE_MANAGER_CREDS["password"])
        assert token is not None
        
        response = self.session.get(
            f"{BASE_URL}/api/users",
            headers=self.get_auth_header(token)
        )
        # Should get 403 Forbidden (not authorized) or 401
        assert response.status_code in [401, 403], f"Case Manager should NOT access users list, got {response.status_code}"
        print(f"SUCCESS: Case Manager correctly denied users list access (status: {response.status_code})")
    
    # ============ PARTNER DELETE TESTS (Should fail) ============
    
    def test_partner_can_login(self):
        """Test partner can login"""
        token = self.login(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        assert token is not None, "Partner login failed"
        print(f"SUCCESS: Partner login successful")
    
    def test_partner_cannot_delete_user(self):
        """Test partner cannot delete users"""
        token = self.login(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        assert token is not None
        
        response = self.session.delete(
            f"{BASE_URL}/api/users/fake-user-id-12345",
            headers=self.get_auth_header(token)
        )
        assert response.status_code in [401, 403], f"Partner should NOT be able to delete users, got {response.status_code}"
        print(f"SUCCESS: Partner correctly denied delete user access (status: {response.status_code})")
    
    def test_partner_cannot_delete_product(self):
        """Test partner cannot delete products"""
        token = self.login(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        assert token is not None
        
        response = self.session.delete(
            f"{BASE_URL}/api/products/fake-product-id-12345",
            headers=self.get_auth_header(token)
        )
        assert response.status_code in [401, 403], f"Partner should NOT be able to delete products, got {response.status_code}"
        print(f"SUCCESS: Partner correctly denied delete product access (status: {response.status_code})")
    
    # ============ CLIENT DELETE TESTS (Should fail) ============
    
    def test_client_can_login(self):
        """Test client can login"""
        token = self.login(CLIENT_CREDS["email"], CLIENT_CREDS["password"])
        assert token is not None, "Client login failed"
        print(f"SUCCESS: Client login successful")
    
    def test_client_cannot_delete_user(self):
        """Test client cannot delete users"""
        token = self.login(CLIENT_CREDS["email"], CLIENT_CREDS["password"])
        assert token is not None
        
        response = self.session.delete(
            f"{BASE_URL}/api/users/fake-user-id-12345",
            headers=self.get_auth_header(token)
        )
        assert response.status_code in [401, 403], f"Client should NOT be able to delete users, got {response.status_code}"
        print(f"SUCCESS: Client correctly denied delete user access (status: {response.status_code})")
    
    def test_client_cannot_delete_product(self):
        """Test client cannot delete products"""
        token = self.login(CLIENT_CREDS["email"], CLIENT_CREDS["password"])
        assert token is not None
        
        response = self.session.delete(
            f"{BASE_URL}/api/products/fake-product-id-12345",
            headers=self.get_auth_header(token)
        )
        assert response.status_code in [401, 403], f"Client should NOT be able to delete products, got {response.status_code}"
        print(f"SUCCESS: Client correctly denied delete product access (status: {response.status_code})")


class TestTicketAPI:
    """Test ticket API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, email, password):
        """Login and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_auth_header(self, token):
        """Get authorization header"""
        return {"Authorization": f"Bearer {token}"}
    
    def test_client_can_get_tickets(self):
        """Test client can get their tickets"""
        token = self.login(CLIENT_CREDS["email"], CLIENT_CREDS["password"])
        assert token is not None
        
        response = self.session.get(
            f"{BASE_URL}/api/tickets/my-tickets",
            headers=self.get_auth_header(token)
        )
        assert response.status_code == 200, f"Client should get tickets, got {response.status_code}"
        tickets = response.json()
        assert isinstance(tickets, list), "Tickets should be a list"
        print(f"SUCCESS: Client can get tickets ({len(tickets)} tickets)")
        return tickets
    
    def test_case_manager_can_get_tickets(self):
        """Test case manager can get their tickets"""
        token = self.login(CASE_MANAGER_CREDS["email"], CASE_MANAGER_CREDS["password"])
        assert token is not None
        
        response = self.session.get(
            f"{BASE_URL}/api/tickets/my-tickets",
            headers=self.get_auth_header(token)
        )
        assert response.status_code == 200, f"Case Manager should get tickets, got {response.status_code}"
        tickets = response.json()
        assert isinstance(tickets, list), "Tickets should be a list"
        print(f"SUCCESS: Case Manager can get tickets ({len(tickets)} tickets)")
        return tickets
    
    def test_partner_can_get_tickets(self):
        """Test partner can get their tickets"""
        token = self.login(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        assert token is not None
        
        response = self.session.get(
            f"{BASE_URL}/api/tickets/my-tickets",
            headers=self.get_auth_header(token)
        )
        assert response.status_code == 200, f"Partner should get tickets, got {response.status_code}"
        tickets = response.json()
        assert isinstance(tickets, list), "Tickets should be a list"
        print(f"SUCCESS: Partner can get tickets ({len(tickets)} tickets)")
        return tickets
    
    def test_ticket_detail_endpoint(self):
        """Test ticket detail endpoint returns full ticket data"""
        # Login as admin to get all tickets
        token = self.login(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        assert token is not None
        
        # Get all tickets
        response = self.session.get(
            f"{BASE_URL}/api/tickets/all",
            headers=self.get_auth_header(token)
        )
        assert response.status_code == 200
        tickets = response.json()
        
        if len(tickets) > 0:
            ticket_id = tickets[0]["id"]
            
            # Get ticket details
            detail_response = self.session.get(
                f"{BASE_URL}/api/tickets/{ticket_id}",
                headers=self.get_auth_header(token)
            )
            assert detail_response.status_code == 200, f"Should get ticket details, got {detail_response.status_code}"
            
            ticket_detail = detail_response.json()
            
            # Verify ticket detail has all required fields
            required_fields = ["id", "subject", "description", "status", "priority", "category", 
                             "created_by", "created_by_name", "messages", "attachments", "activity_log"]
            for field in required_fields:
                assert field in ticket_detail, f"Ticket detail should have '{field}' field"
            
            print(f"SUCCESS: Ticket detail endpoint returns full data")
            print(f"  - Subject: {ticket_detail['subject']}")
            print(f"  - Status: {ticket_detail['status']}")
            print(f"  - Messages: {len(ticket_detail.get('messages', []))}")
            print(f"  - Attachments: {len(ticket_detail.get('attachments', []))}")
            print(f"  - Activity Log: {len(ticket_detail.get('activity_log', []))}")
        else:
            print("INFO: No tickets found to test detail endpoint")


class TestNotificationAPI:
    """Test notification API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, email, password):
        """Login and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_auth_header(self, token):
        """Get authorization header"""
        return {"Authorization": f"Bearer {token}"}
    
    def test_client_can_get_notifications(self):
        """Test client can get their notifications"""
        token = self.login(CLIENT_CREDS["email"], CLIENT_CREDS["password"])
        assert token is not None
        
        response = self.session.get(
            f"{BASE_URL}/api/notifications",
            headers=self.get_auth_header(token)
        )
        assert response.status_code == 200, f"Client should get notifications, got {response.status_code}"
        notifications = response.json()
        assert isinstance(notifications, list), "Notifications should be a list"
        print(f"SUCCESS: Client can get notifications ({len(notifications)} notifications)")
        
        # Check notification structure
        if len(notifications) > 0:
            notif = notifications[0]
            required_fields = ["id", "title", "message", "type", "is_read", "created_at"]
            for field in required_fields:
                assert field in notif, f"Notification should have '{field}' field"
            print(f"  - First notification type: {notif.get('type')}")
            print(f"  - Has related_id: {'related_id' in notif}")
    
    def test_notification_has_related_id_for_navigation(self):
        """Test that notifications have related_id for navigation"""
        token = self.login(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        assert token is not None
        
        response = self.session.get(
            f"{BASE_URL}/api/notifications",
            headers=self.get_auth_header(token)
        )
        assert response.status_code == 200
        notifications = response.json()
        
        # Check if ticket-related notifications have related_id
        ticket_notifications = [n for n in notifications if 'ticket' in n.get('type', '')]
        if len(ticket_notifications) > 0:
            for notif in ticket_notifications[:3]:  # Check first 3
                assert 'related_id' in notif, f"Ticket notification should have related_id"
                print(f"SUCCESS: Ticket notification has related_id: {notif.get('related_id')}")
        else:
            print("INFO: No ticket notifications found to verify related_id")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
