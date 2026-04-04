"""
Iteration 24 Tests: Email Service Integration & Mobile Responsiveness
Tests:
1. Email logs endpoint (admin only)
2. Sale approval triggers email log
3. Sale rejection triggers email log
4. Document review triggers email notification
5. Ticket reply triggers email notification
6. Case step update triggers email notification
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://payment-portal-323.preview.emergentagent.com')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


class TestEmailServiceIntegration:
    """Test email service integration - emails are MOCKED to DB"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.partner_token = None
        self.manager_token = None
        self.client_token = None
    
    def login(self, creds):
        """Login and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_auth_header(self, token):
        """Get authorization header"""
        return {"Authorization": f"Bearer {token}"}
    
    # ==================== EMAIL LOGS ENDPOINT ====================
    
    def test_email_logs_endpoint_admin_access(self):
        """Test GET /api/activity/email-logs - admin only"""
        self.admin_token = self.login(ADMIN_CREDS)
        assert self.admin_token, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/activity/email-logs",
            headers=self.get_auth_header(self.admin_token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of email logs"
        print(f"✓ Email logs endpoint returned {len(data)} logs")
    
    def test_email_logs_endpoint_non_admin_forbidden(self):
        """Test GET /api/activity/email-logs - non-admin should get 403"""
        self.partner_token = self.login(PARTNER_CREDS)
        assert self.partner_token, "Partner login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/activity/email-logs",
            headers=self.get_auth_header(self.partner_token)
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("✓ Email logs endpoint correctly returns 403 for non-admin")
    
    def test_email_logs_endpoint_client_forbidden(self):
        """Test GET /api/activity/email-logs - client should get 403"""
        self.client_token = self.login(CLIENT_CREDS)
        assert self.client_token, "Client login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/activity/email-logs",
            headers=self.get_auth_header(self.client_token)
        )
        
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
        print("✓ Email logs endpoint correctly returns 403 for client")
    
    # ==================== SALE APPROVAL EMAIL ====================
    
    def test_sale_approval_creates_email_log(self):
        """Test that approving a sale creates an email log entry"""
        # Login as partner to create a sale
        self.partner_token = self.login(PARTNER_CREDS)
        assert self.partner_token, "Partner login failed"
        
        # Get products
        products_resp = self.session.get(
            f"{BASE_URL}/api/products",
            headers=self.get_auth_header(self.partner_token)
        )
        assert products_resp.status_code == 200
        products = products_resp.json()
        assert len(products) > 0, "No products available"
        product_id = products[0]["id"]
        
        # Create a test sale using multipart form data
        unique_email = f"test_approval_{uuid.uuid4().hex[:8]}@test.com"
        
        # Use requests with files parameter for multipart/form-data
        import io
        create_resp = requests.post(
            f"{BASE_URL}/api/sales",
            data={
                "client_name": "TEST_ApprovalEmailClient",
                "client_email": unique_email,
                "client_mobile": "1234567890",
                "product_id": product_id,
                "fee_amount": "10000",
                "amount_received": "5000",
                "payment_method": "bank_transfer",
                "payment_reference": "TEST_REF_APPROVAL",
                "agreement_signed": "true",
                "currency": "INR"
            },
            headers={"Authorization": f"Bearer {self.partner_token}"}
        )
        assert create_resp.status_code == 200, f"Sale creation failed: {create_resp.text}"
        sale_id = create_resp.json().get("id")
        assert sale_id, "No sale ID returned"
        print(f"✓ Created test sale: {sale_id}")
        
        # Get email logs count before approval
        self.admin_token = self.login(ADMIN_CREDS)
        assert self.admin_token, "Admin login failed"
        
        logs_before = self.session.get(
            f"{BASE_URL}/api/activity/email-logs",
            headers=self.get_auth_header(self.admin_token)
        ).json()
        count_before = len(logs_before)
        
        # Get case managers for assignment
        users_resp = self.session.get(
            f"{BASE_URL}/api/users",
            headers=self.get_auth_header(self.admin_token)
        )
        assert users_resp.status_code == 200
        users = users_resp.json()
        case_managers = [u for u in users if u.get("role") == "case_manager"]
        cm_id = case_managers[0]["id"] if case_managers else None
        
        # Approve the sale
        approve_resp = self.session.post(
            f"{BASE_URL}/api/sales/approve",
            json={
                "sale_id": sale_id,
                "status": "approved",
                "case_manager_id": cm_id
            },
            headers=self.get_auth_header(self.admin_token)
        )
        assert approve_resp.status_code == 200, f"Sale approval failed: {approve_resp.text}"
        print(f"✓ Sale approved successfully")
        
        # Check email logs after approval
        logs_after = self.session.get(
            f"{BASE_URL}/api/activity/email-logs",
            headers=self.get_auth_header(self.admin_token)
        ).json()
        count_after = len(logs_after)
        
        assert count_after > count_before, f"Expected new email log after approval. Before: {count_before}, After: {count_after}"
        
        # Verify the email log content
        new_logs = [log for log in logs_after if log.get("to") == unique_email]
        assert len(new_logs) > 0, f"No email log found for {unique_email}"
        
        approval_log = new_logs[0]
        assert "approved" in approval_log.get("subject", "").lower() or "approved" in approval_log.get("body", "").lower(), \
            "Email log should mention approval"
        assert approval_log.get("template") == "sale_approved", f"Expected template 'sale_approved', got {approval_log.get('template')}"
        print(f"✓ Email log created for sale approval: {approval_log.get('subject')}")
    
    def test_sale_rejection_creates_email_log(self):
        """Test that rejecting a sale creates an email log entry"""
        # Login as partner to create a sale
        self.partner_token = self.login(PARTNER_CREDS)
        assert self.partner_token, "Partner login failed"
        
        # Get products
        products_resp = self.session.get(
            f"{BASE_URL}/api/products",
            headers=self.get_auth_header(self.partner_token)
        )
        products = products_resp.json()
        product_id = products[0]["id"]
        
        # Create a test sale using multipart form data
        unique_email = f"test_rejection_{uuid.uuid4().hex[:8]}@test.com"
        
        create_resp = requests.post(
            f"{BASE_URL}/api/sales",
            data={
                "client_name": "TEST_RejectionEmailClient",
                "client_email": unique_email,
                "client_mobile": "1234567890",
                "product_id": product_id,
                "fee_amount": "10000",
                "amount_received": "5000",
                "payment_method": "bank_transfer",
                "payment_reference": "TEST_REF_REJECTION",
                "agreement_signed": "true",
                "currency": "INR"
            },
            headers={"Authorization": f"Bearer {self.partner_token}"}
        )
        assert create_resp.status_code == 200, f"Sale creation failed: {create_resp.text}"
        sale_id = create_resp.json().get("id")
        print(f"✓ Created test sale for rejection: {sale_id}")
        
        # Login as admin and reject
        self.admin_token = self.login(ADMIN_CREDS)
        
        # Get email logs count before rejection
        logs_before = self.session.get(
            f"{BASE_URL}/api/activity/email-logs",
            headers=self.get_auth_header(self.admin_token)
        ).json()
        count_before = len(logs_before)
        
        # Reject the sale
        reject_resp = self.session.post(
            f"{BASE_URL}/api/sales/approve",
            json={
                "sale_id": sale_id,
                "status": "rejected",
                "rejection_reason": "TEST_REJECTION: Documents incomplete for testing purposes"
            },
            headers=self.get_auth_header(self.admin_token)
        )
        assert reject_resp.status_code == 200, f"Sale rejection failed: {reject_resp.text}"
        print(f"✓ Sale rejected successfully")
        
        # Check email logs after rejection
        logs_after = self.session.get(
            f"{BASE_URL}/api/activity/email-logs",
            headers=self.get_auth_header(self.admin_token)
        ).json()
        count_after = len(logs_after)
        
        assert count_after > count_before, f"Expected new email log after rejection. Before: {count_before}, After: {count_after}"
        
        # Verify the email log content
        new_logs = [log for log in logs_after if log.get("to") == unique_email]
        assert len(new_logs) > 0, f"No email log found for {unique_email}"
        
        rejection_log = new_logs[0]
        assert rejection_log.get("template") == "sale_rejected", f"Expected template 'sale_rejected', got {rejection_log.get('template')}"
        print(f"✓ Email log created for sale rejection: {rejection_log.get('subject')}")


class TestTicketEmailNotification:
    """Test ticket reply email notifications"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, creds):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}
    
    def test_ticket_reply_creates_email_log(self):
        """Test that replying to a ticket creates an email log"""
        # Login as client to create a ticket
        client_token = self.login(CLIENT_CREDS)
        assert client_token, "Client login failed"
        
        # Create a ticket
        ticket_data = {
            "subject": f"TEST_TicketEmail_{uuid.uuid4().hex[:6]}",
            "description": "Test ticket for email notification testing",
            "priority": "medium",
            "category": "general"
        }
        
        create_resp = self.session.post(
            f"{BASE_URL}/api/tickets",
            json=ticket_data,
            headers=self.get_auth_header(client_token)
        )
        assert create_resp.status_code == 200, f"Ticket creation failed: {create_resp.text}"
        ticket_id = create_resp.json().get("id")
        print(f"✓ Created test ticket: {ticket_id}")
        
        # Login as admin
        admin_token = self.login(ADMIN_CREDS)
        assert admin_token, "Admin login failed"
        
        # Get email logs count before reply
        logs_before = self.session.get(
            f"{BASE_URL}/api/activity/email-logs",
            headers=self.get_auth_header(admin_token)
        ).json()
        count_before = len(logs_before)
        
        # Reply to the ticket as admin
        reply_resp = self.session.post(
            f"{BASE_URL}/api/tickets/{ticket_id}/message",
            json={"message": "TEST_REPLY: This is a test reply for email notification testing"},
            headers=self.get_auth_header(admin_token)
        )
        assert reply_resp.status_code == 200, f"Ticket reply failed: {reply_resp.text}"
        print(f"✓ Replied to ticket successfully")
        
        # Check email logs after reply
        logs_after = self.session.get(
            f"{BASE_URL}/api/activity/email-logs",
            headers=self.get_auth_header(admin_token)
        ).json()
        count_after = len(logs_after)
        
        assert count_after > count_before, f"Expected new email log after ticket reply. Before: {count_before}, After: {count_after}"
        
        # Find the ticket update email
        ticket_emails = [log for log in logs_after if log.get("template") == "ticket_update"]
        assert len(ticket_emails) > 0, "No ticket_update email log found"
        print(f"✓ Email log created for ticket reply")


class TestCoreAPIFunctionality:
    """Test that existing core APIs still work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, creds):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}
    
    def test_admin_login(self):
        """Test admin login works"""
        token = self.login(ADMIN_CREDS)
        assert token, "Admin login failed"
        print("✓ Admin login successful")
    
    def test_partner_login(self):
        """Test partner login works"""
        token = self.login(PARTNER_CREDS)
        assert token, "Partner login failed"
        print("✓ Partner login successful")
    
    def test_manager_login(self):
        """Test case manager login works"""
        token = self.login(MANAGER_CREDS)
        assert token, "Case manager login failed"
        print("✓ Case manager login successful")
    
    def test_client_login(self):
        """Test client login works"""
        token = self.login(CLIENT_CREDS)
        assert token, "Client login failed"
        print("✓ Client login successful")
    
    def test_products_endpoint(self):
        """Test products endpoint works"""
        admin_token = self.login(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/products",
            headers=self.get_auth_header(admin_token)
        )
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        print(f"✓ Products endpoint returned {len(products)} products")
    
    def test_sales_endpoint(self):
        """Test sales endpoint works"""
        admin_token = self.login(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/sales",
            headers=self.get_auth_header(admin_token)
        )
        assert response.status_code == 200
        sales = response.json()
        assert isinstance(sales, list)
        print(f"✓ Sales endpoint returned {len(sales)} sales")
    
    def test_cases_endpoint(self):
        """Test cases endpoint works"""
        admin_token = self.login(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/cases",
            headers=self.get_auth_header(admin_token)
        )
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        print(f"✓ Cases endpoint returned {len(cases)} cases")
    
    def test_tickets_endpoint(self):
        """Test tickets endpoint works"""
        admin_token = self.login(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/tickets/all",
            headers=self.get_auth_header(admin_token)
        )
        assert response.status_code == 200
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Tickets endpoint returned {len(tickets)} tickets")
    
    def test_dashboard_stats(self):
        """Test dashboard stats endpoint works"""
        admin_token = self.login(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/stats/dashboard",
            headers=self.get_auth_header(admin_token)
        )
        assert response.status_code == 200
        stats = response.json()
        assert "pending_sales" in stats or "active_cases" in stats
        print(f"✓ Dashboard stats endpoint works")
    
    def test_activity_logs_endpoint(self):
        """Test activity logs endpoint works"""
        admin_token = self.login(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/activity/logs",
            headers=self.get_auth_header(admin_token)
        )
        assert response.status_code == 200
        logs = response.json()
        assert isinstance(logs, list)
        print(f"✓ Activity logs endpoint returned {len(logs)} logs")
    
    def test_analytics_endpoint(self):
        """Test analytics endpoint works"""
        admin_token = self.login(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/analytics/dashboard",
            headers=self.get_auth_header(admin_token)
        )
        assert response.status_code == 200
        print("✓ Analytics endpoint works")
    
    def test_workflows_endpoint(self):
        """Test workflows endpoint works"""
        admin_token = self.login(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/workflows/products",
            headers=self.get_auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Workflow products endpoint works")
    
    def test_marketing_promo_codes(self):
        """Test marketing promo codes endpoint works"""
        admin_token = self.login(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/marketing/promos",
            headers=self.get_auth_header(admin_token)
        )
        assert response.status_code == 200
        print("✓ Marketing promo codes endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
