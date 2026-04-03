"""
Phase 1 Features Test Suite for LEAMSS Immigration Portal
Tests:
1. Commission calculated on amount_received (not fee_amount)
2. Mandatory rejection reason for sales (min 5 chars)
3. Mandatory closure comment for tickets (min 10 chars)
4. Workflow duplicate step prevention (case-insensitive)
5. Record payment endpoint updates amount_received and recalculates commission
6. Enhanced sales reports with Service Type/Date/Rejection Reason fields
7. Dashboard stats with total_received and total_pending_amount
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}


class TestSetup:
    """Setup and authentication helpers"""
    
    @staticmethod
    def get_token(email, password):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    @staticmethod
    def auth_header(token):
        return {"Authorization": f"Bearer {token}"}


class TestCommissionCalculation:
    """Test commission is calculated on amount_received, NOT fee_amount"""
    
    def test_create_sale_commission_on_received(self):
        """POST /api/sales - Commission should be calculated on amount_received"""
        # Login as partner
        token = TestSetup.get_token(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        assert token, "Partner login failed"
        
        # Get a product
        products_res = requests.get(f"{BASE_URL}/api/products", headers=TestSetup.auth_header(token))
        assert products_res.status_code == 200
        products = products_res.json()
        assert len(products) > 0, "No products found"
        product_id = products[0]["id"]
        
        # Create sale with partial payment
        unique_email = f"test_commission_{uuid.uuid4().hex[:8]}@test.com"
        form_data = {
            "client_name": "Commission Test Client",
            "client_email": unique_email,
            "client_mobile": "1234567890",
            "product_id": product_id,
            "fee_amount": "1000",  # Total fee
            "amount_received": "500",  # Only 500 received
            "payment_method": "cash",
            "payment_reference": "TEST-COMM-001",
            "agreement_signed": "true"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            data=form_data,
            headers=TestSetup.auth_header(token)
        )
        assert response.status_code == 200, f"Create sale failed: {response.text}"
        sale_id = response.json().get("id")
        assert sale_id, "No sale ID returned"
        
        # Get sale details to verify commission
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        sale_res = requests.get(f"{BASE_URL}/api/sales/{sale_id}", headers=TestSetup.auth_header(admin_token))
        assert sale_res.status_code == 200, f"Get sale failed: {sale_res.text}"
        sale = sale_res.json()
        
        # Verify commission is based on amount_received (500), not fee_amount (1000)
        commission_rate = sale.get("commission_rate", 0)
        expected_commission = round(500 * (commission_rate / 100), 2)
        actual_commission = sale.get("commission_amount", 0)
        
        print(f"Fee: {sale.get('fee_amount')}, Received: {sale.get('amount_received')}, Rate: {commission_rate}%, Commission: {actual_commission}")
        assert actual_commission == expected_commission, f"Commission should be {expected_commission} (based on received), got {actual_commission}"
        
        # Verify pending_amount is calculated correctly
        pending = sale.get("pending_amount", 0)
        assert pending == 500, f"Pending amount should be 500, got {pending}"
        
        print(f"✓ Commission correctly calculated on amount_received: ${actual_commission}")
    
    def test_approve_sale_commission_on_received(self):
        """POST /api/sales/approve - Commission should be recalculated on amount_received"""
        # Login as partner and create a sale
        partner_token = TestSetup.get_token(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        assert partner_token, "Partner login failed"
        
        products_res = requests.get(f"{BASE_URL}/api/products", headers=TestSetup.auth_header(partner_token))
        products = products_res.json()
        product_id = products[0]["id"]
        
        unique_email = f"test_approve_{uuid.uuid4().hex[:8]}@test.com"
        form_data = {
            "client_name": "Approve Commission Test",
            "client_email": unique_email,
            "client_mobile": "1234567890",
            "product_id": product_id,
            "fee_amount": "2000",
            "amount_received": "800",  # Partial payment
            "payment_method": "bank_transfer",
            "payment_reference": "TEST-APPROVE-001",
            "agreement_signed": "true"
        }
        
        response = requests.post(f"{BASE_URL}/api/sales", data=form_data, headers=TestSetup.auth_header(partner_token))
        assert response.status_code == 200
        sale_id = response.json().get("id")
        
        # Admin approves the sale
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        approve_res = requests.post(
            f"{BASE_URL}/api/sales/approve",
            json={"sale_id": sale_id, "status": "approved"},
            headers=TestSetup.auth_header(admin_token)
        )
        assert approve_res.status_code == 200, f"Approve failed: {approve_res.text}"
        
        # Verify commission after approval
        sale_res = requests.get(f"{BASE_URL}/api/sales/{sale_id}", headers=TestSetup.auth_header(admin_token))
        sale = sale_res.json()
        
        commission_rate = sale.get("commission_rate", 0)
        expected_commission = round(800 * (commission_rate / 100), 2)  # Based on 800 received
        actual_commission = sale.get("commission_amount", 0)
        
        print(f"After approval - Fee: {sale.get('fee_amount')}, Received: {sale.get('amount_received')}, Commission: {actual_commission}")
        assert actual_commission == expected_commission, f"Commission after approval should be {expected_commission}, got {actual_commission}"
        print(f"✓ Commission correctly recalculated on approval: ${actual_commission}")


class TestRejectionReason:
    """Test mandatory rejection reason for sales"""
    
    def test_reject_without_reason_fails(self):
        """POST /api/sales/approve with status=rejected requires rejection_reason"""
        # Create a sale first
        partner_token = TestSetup.get_token(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        products_res = requests.get(f"{BASE_URL}/api/products", headers=TestSetup.auth_header(partner_token))
        product_id = products_res.json()[0]["id"]
        
        unique_email = f"test_reject_{uuid.uuid4().hex[:8]}@test.com"
        form_data = {
            "client_name": "Reject Test Client",
            "client_email": unique_email,
            "client_mobile": "1234567890",
            "product_id": product_id,
            "fee_amount": "1000",
            "amount_received": "0",
            "payment_method": "cash",
            "agreement_signed": "true"
        }
        
        response = requests.post(f"{BASE_URL}/api/sales", data=form_data, headers=TestSetup.auth_header(partner_token))
        sale_id = response.json().get("id")
        
        # Try to reject without reason
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        reject_res = requests.post(
            f"{BASE_URL}/api/sales/approve",
            json={"sale_id": sale_id, "status": "rejected"},  # No rejection_reason
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert reject_res.status_code == 400, f"Should return 400 without rejection reason, got {reject_res.status_code}"
        assert "reason" in reject_res.text.lower() or "required" in reject_res.text.lower(), f"Error should mention reason: {reject_res.text}"
        print(f"✓ Rejection without reason correctly returns 400: {reject_res.json().get('detail')}")
    
    def test_reject_with_short_reason_fails(self):
        """Rejection reason must be at least 5 characters"""
        partner_token = TestSetup.get_token(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        products_res = requests.get(f"{BASE_URL}/api/products", headers=TestSetup.auth_header(partner_token))
        product_id = products_res.json()[0]["id"]
        
        unique_email = f"test_reject_short_{uuid.uuid4().hex[:8]}@test.com"
        form_data = {
            "client_name": "Reject Short Reason Test",
            "client_email": unique_email,
            "client_mobile": "1234567890",
            "product_id": product_id,
            "fee_amount": "1000",
            "amount_received": "0",
            "payment_method": "cash",
            "agreement_signed": "true"
        }
        
        response = requests.post(f"{BASE_URL}/api/sales", data=form_data, headers=TestSetup.auth_header(partner_token))
        sale_id = response.json().get("id")
        
        # Try to reject with short reason (less than 5 chars)
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        reject_res = requests.post(
            f"{BASE_URL}/api/sales/approve",
            json={"sale_id": sale_id, "status": "rejected", "rejection_reason": "bad"},  # Only 3 chars
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert reject_res.status_code == 400, f"Should return 400 with short reason, got {reject_res.status_code}"
        print(f"✓ Rejection with short reason correctly returns 400: {reject_res.json().get('detail')}")
    
    def test_reject_with_valid_reason_succeeds(self):
        """Rejection with valid reason (5+ chars) should succeed"""
        partner_token = TestSetup.get_token(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        products_res = requests.get(f"{BASE_URL}/api/products", headers=TestSetup.auth_header(partner_token))
        product_id = products_res.json()[0]["id"]
        
        unique_email = f"test_reject_valid_{uuid.uuid4().hex[:8]}@test.com"
        form_data = {
            "client_name": "Reject Valid Reason Test",
            "client_email": unique_email,
            "client_mobile": "1234567890",
            "product_id": product_id,
            "fee_amount": "1000",
            "amount_received": "0",
            "payment_method": "cash",
            "agreement_signed": "true"
        }
        
        response = requests.post(f"{BASE_URL}/api/sales", data=form_data, headers=TestSetup.auth_header(partner_token))
        sale_id = response.json().get("id")
        
        # Reject with valid reason
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        reject_res = requests.post(
            f"{BASE_URL}/api/sales/approve",
            json={"sale_id": sale_id, "status": "rejected", "rejection_reason": "Missing required documents"},
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert reject_res.status_code == 200, f"Should succeed with valid reason, got {reject_res.status_code}: {reject_res.text}"
        
        # Verify rejection reason is stored
        sale_res = requests.get(f"{BASE_URL}/api/sales/{sale_id}", headers=TestSetup.auth_header(admin_token))
        sale = sale_res.json()
        assert sale.get("rejection_reason") == "Missing required documents", f"Rejection reason not stored: {sale}"
        print(f"✓ Rejection with valid reason succeeds and stores reason")


class TestTicketClosureComment:
    """Test mandatory closure comment for tickets"""
    
    def test_close_ticket_without_comment_fails(self):
        """PUT /api/tickets/{id}/status with status=closed requires closure_comment"""
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        
        # Create a ticket first
        ticket_res = requests.post(
            f"{BASE_URL}/api/tickets",
            json={"subject": "Test Closure Comment", "description": "Testing closure comment requirement", "priority": "medium", "category": "general"},
            headers=TestSetup.auth_header(admin_token)
        )
        assert ticket_res.status_code == 200, f"Create ticket failed: {ticket_res.text}"
        ticket_id = ticket_res.json().get("id")
        
        # Try to close without comment
        close_res = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}/status",
            json={"status": "closed"},  # No closure_comment
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert close_res.status_code == 400, f"Should return 400 without closure comment, got {close_res.status_code}"
        assert "closure" in close_res.text.lower() or "comment" in close_res.text.lower() or "10" in close_res.text, f"Error should mention closure comment: {close_res.text}"
        print(f"✓ Close ticket without comment correctly returns 400: {close_res.json().get('detail')}")
    
    def test_close_ticket_with_short_comment_fails(self):
        """Closure comment must be at least 10 characters"""
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        
        ticket_res = requests.post(
            f"{BASE_URL}/api/tickets",
            json={"subject": "Test Short Comment", "description": "Testing short comment", "priority": "low", "category": "general"},
            headers=TestSetup.auth_header(admin_token)
        )
        ticket_id = ticket_res.json().get("id")
        
        # Try to close with short comment (less than 10 chars)
        close_res = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}/status",
            json={"status": "closed", "closure_comment": "done"},  # Only 4 chars
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert close_res.status_code == 400, f"Should return 400 with short comment, got {close_res.status_code}"
        print(f"✓ Close ticket with short comment correctly returns 400: {close_res.json().get('detail')}")
    
    def test_close_ticket_with_valid_comment_succeeds(self):
        """Closure with valid comment (10+ chars) should succeed"""
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        
        ticket_res = requests.post(
            f"{BASE_URL}/api/tickets",
            json={"subject": "Test Valid Comment", "description": "Testing valid comment", "priority": "low", "category": "general"},
            headers=TestSetup.auth_header(admin_token)
        )
        ticket_id = ticket_res.json().get("id")
        
        # Close with valid comment
        close_res = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}/status",
            json={"status": "closed", "closure_comment": "Issue resolved successfully after investigation"},
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert close_res.status_code == 200, f"Should succeed with valid comment, got {close_res.status_code}: {close_res.text}"
        print(f"✓ Close ticket with valid comment succeeds")
    
    def test_resolve_ticket_requires_comment(self):
        """PUT /api/tickets/{id}/status with status=resolved also requires closure_comment"""
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        
        ticket_res = requests.post(
            f"{BASE_URL}/api/tickets",
            json={"subject": "Test Resolve Comment", "description": "Testing resolve comment", "priority": "medium", "category": "general"},
            headers=TestSetup.auth_header(admin_token)
        )
        ticket_id = ticket_res.json().get("id")
        
        # Try to resolve without comment
        resolve_res = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}/status",
            json={"status": "resolved"},  # No closure_comment
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert resolve_res.status_code == 400, f"Should return 400 without closure comment for resolve, got {resolve_res.status_code}"
        print(f"✓ Resolve ticket without comment correctly returns 400")


class TestWorkflowDuplicatePrevention:
    """Test duplicate workflow step prevention"""
    
    def test_duplicate_step_name_fails(self):
        """POST /api/products/{id}/workflow-step prevents duplicate step names"""
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        
        # Get a product
        products_res = requests.get(f"{BASE_URL}/api/products", headers=TestSetup.auth_header(admin_token))
        products = products_res.json()
        assert len(products) > 0, "No products found"
        product = products[0]
        product_id = product["id"]
        
        # Get existing steps to find a unique order
        existing_steps = product.get("workflow_steps", [])
        max_order = max([s.get("step_order", 0) for s in existing_steps], default=0)
        
        # Create a step with unique name
        unique_step_name = f"Test Step {uuid.uuid4().hex[:6]}"
        step1_res = requests.post(
            f"{BASE_URL}/api/products/{product_id}/workflow-step",
            json={"step_name": unique_step_name, "step_order": max_order + 1, "description": "First step"},
            headers=TestSetup.auth_header(admin_token)
        )
        assert step1_res.status_code == 200, f"First step creation failed: {step1_res.text}"
        
        # Try to create duplicate step (same name, different order)
        step2_res = requests.post(
            f"{BASE_URL}/api/products/{product_id}/workflow-step",
            json={"step_name": unique_step_name, "step_order": max_order + 2, "description": "Duplicate step"},
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert step2_res.status_code == 400, f"Should return 400 for duplicate step name, got {step2_res.status_code}"
        assert "already exists" in step2_res.text.lower() or "duplicate" in step2_res.text.lower(), f"Error should mention duplicate: {step2_res.text}"
        print(f"✓ Duplicate step name correctly returns 400: {step2_res.json().get('detail')}")
        
        # Cleanup - delete the test step
        requests.delete(f"{BASE_URL}/api/products/{product_id}/workflow-step/{max_order + 1}", headers=TestSetup.auth_header(admin_token))
    
    def test_duplicate_step_name_case_insensitive(self):
        """Duplicate check should be case-insensitive"""
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        
        products_res = requests.get(f"{BASE_URL}/api/products", headers=TestSetup.auth_header(admin_token))
        product = products_res.json()[0]
        product_id = product["id"]
        
        existing_steps = product.get("workflow_steps", [])
        max_order = max([s.get("step_order", 0) for s in existing_steps], default=0)
        
        # Create a step with lowercase name
        unique_step_name = f"case test {uuid.uuid4().hex[:6]}"
        step1_res = requests.post(
            f"{BASE_URL}/api/products/{product_id}/workflow-step",
            json={"step_name": unique_step_name, "step_order": max_order + 1, "description": "Lowercase step"},
            headers=TestSetup.auth_header(admin_token)
        )
        assert step1_res.status_code == 200, f"First step creation failed: {step1_res.text}"
        
        # Try to create with UPPERCASE version
        step2_res = requests.post(
            f"{BASE_URL}/api/products/{product_id}/workflow-step",
            json={"step_name": unique_step_name.upper(), "step_order": max_order + 2, "description": "Uppercase duplicate"},
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert step2_res.status_code == 400, f"Should return 400 for case-insensitive duplicate, got {step2_res.status_code}"
        print(f"✓ Case-insensitive duplicate correctly returns 400")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/products/{product_id}/workflow-step/{max_order + 1}", headers=TestSetup.auth_header(admin_token))


class TestRecordPayment:
    """Test record-payment endpoint"""
    
    def test_record_payment_updates_received_and_commission(self):
        """POST /api/sales/record-payment updates amount_received and recalculates commission"""
        # Create a sale with partial payment
        partner_token = TestSetup.get_token(PARTNER_CREDS["email"], PARTNER_CREDS["password"])
        products_res = requests.get(f"{BASE_URL}/api/products", headers=TestSetup.auth_header(partner_token))
        product_id = products_res.json()[0]["id"]
        
        unique_email = f"test_payment_{uuid.uuid4().hex[:8]}@test.com"
        form_data = {
            "client_name": "Payment Test Client",
            "client_email": unique_email,
            "client_mobile": "1234567890",
            "product_id": product_id,
            "fee_amount": "1000",
            "amount_received": "300",  # Initial payment
            "payment_method": "cash",
            "agreement_signed": "true"
        }
        
        response = requests.post(f"{BASE_URL}/api/sales", data=form_data, headers=TestSetup.auth_header(partner_token))
        assert response.status_code == 200
        sale_id = response.json().get("id")
        
        # Get initial sale state
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        initial_sale = requests.get(f"{BASE_URL}/api/sales/{sale_id}", headers=TestSetup.auth_header(admin_token)).json()
        initial_received = initial_sale.get("amount_received", 0)
        initial_commission = initial_sale.get("commission_amount", 0)
        commission_rate = initial_sale.get("commission_rate", 0)
        
        print(f"Initial - Received: {initial_received}, Commission: {initial_commission}")
        
        # Record additional payment
        payment_res = requests.post(
            f"{BASE_URL}/api/sales/record-payment",
            json={"sale_id": sale_id, "amount": 200, "payment_method": "bank_transfer", "payment_reference": "PAY-002"},
            headers=TestSetup.auth_header(admin_token)
        )
        
        assert payment_res.status_code == 200, f"Record payment failed: {payment_res.text}"
        payment_data = payment_res.json()
        
        # Verify response contains updated values
        assert payment_data.get("amount_received") == 500, f"Expected 500 received, got {payment_data.get('amount_received')}"
        assert payment_data.get("pending_amount") == 500, f"Expected 500 pending, got {payment_data.get('pending_amount')}"
        
        # Verify commission recalculated
        expected_commission = round(500 * (commission_rate / 100), 2)
        assert payment_data.get("commission_amount") == expected_commission, f"Expected commission {expected_commission}, got {payment_data.get('commission_amount')}"
        
        print(f"After payment - Received: {payment_data.get('amount_received')}, Commission: {payment_data.get('commission_amount')}")
        print(f"✓ Record payment correctly updates amount_received and recalculates commission")


class TestEnhancedSalesReport:
    """Test enhanced sales report fields"""
    
    def test_sales_report_has_required_fields(self):
        """GET /api/reports/sales returns product_category, amount_received, pending_amount, rejection_reason"""
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        
        response = requests.get(f"{BASE_URL}/api/reports/sales", headers=TestSetup.auth_header(admin_token))
        assert response.status_code == 200, f"Sales report failed: {response.text}"
        
        sales = response.json()
        assert len(sales) > 0, "No sales in report"
        
        # Check first sale has all required fields
        sale = sales[0]
        required_fields = ["product_category", "amount_received", "pending_amount", "rejection_reason", "created_at"]
        
        for field in required_fields:
            assert field in sale, f"Missing field '{field}' in sales report"
        
        print(f"✓ Sales report contains all required fields: {required_fields}")
        print(f"  Sample: category={sale.get('product_category')}, received={sale.get('amount_received')}, pending={sale.get('pending_amount')}")
    
    def test_get_sales_returns_pending_and_category(self):
        """GET /api/sales returns pending_amount and product_category for each sale"""
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        
        response = requests.get(f"{BASE_URL}/api/sales", headers=TestSetup.auth_header(admin_token))
        assert response.status_code == 200
        
        sales = response.json()
        if len(sales) > 0:
            sale = sales[0]
            assert "pending_amount" in sale, "Missing pending_amount in GET /api/sales"
            assert "product_category" in sale, "Missing product_category in GET /api/sales"
            print(f"✓ GET /api/sales returns pending_amount and product_category")


class TestDashboardStats:
    """Test dashboard stats include received/pending breakdown"""
    
    def test_dashboard_has_received_and_pending(self):
        """GET /api/stats/dashboard returns total_received and total_pending_amount"""
        admin_token = TestSetup.get_token(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
        
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=TestSetup.auth_header(admin_token))
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        stats = response.json()
        
        assert "total_received" in stats, "Missing total_received in dashboard stats"
        assert "total_pending_amount" in stats, "Missing total_pending_amount in dashboard stats"
        assert "total_revenue" in stats, "Missing total_revenue in dashboard stats"
        
        # Verify math: total_revenue = total_received + total_pending_amount
        total_revenue = stats.get("total_revenue", 0)
        total_received = stats.get("total_received", 0)
        total_pending = stats.get("total_pending_amount", 0)
        
        # Allow small floating point differences
        assert abs(total_revenue - (total_received + total_pending)) < 0.01, f"Revenue math doesn't add up: {total_revenue} != {total_received} + {total_pending}"
        
        print(f"✓ Dashboard stats include received/pending breakdown")
        print(f"  Revenue: ${total_revenue}, Received: ${total_received}, Pending: ${total_pending}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print(f"✓ API health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
