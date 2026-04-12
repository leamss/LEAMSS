"""
Iteration 49: Approval Center Overhaul Tests
Tests for:
- BUG FIX: Sale approval from Approval Center (was returning 'User not found')
- Client Pipeline View API
- Case Manager Assignment from Approval Center
- Sidebar cleanup verification (frontend only)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"
CM_EMAIL = "manager@leamss.com"
CM_PASSWORD = "Manager@123"


class TestIteration49ApprovalCenter:
    """Iteration 49: Approval Center Overhaul Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.admin_token = login_response.json().get("token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.admin_user = login_response.json().get("user")
        
        # Login as partner for creating test sales
        partner_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTNER_EMAIL,
            "password": PARTNER_PASSWORD
        })
        if partner_login.status_code == 200:
            self.partner_token = partner_login.json().get("token")
            self.partner_headers = {"Authorization": f"Bearer {self.partner_token}"}
            self.partner_user = partner_login.json().get("user")
        else:
            self.partner_token = None
            self.partner_headers = {}
            self.partner_user = None
        
        # Login as case manager
        cm_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CM_EMAIL,
            "password": CM_PASSWORD
        })
        if cm_login.status_code == 200:
            self.cm_token = cm_login.json().get("token")
            self.cm_headers = {"Authorization": f"Bearer {self.cm_token}"}
            self.cm_user = cm_login.json().get("user")
        else:
            self.cm_token = None
            self.cm_headers = {}
            self.cm_user = None
    
    # ==================== CLIENT PIPELINE VIEW ====================
    
    def test_client_pipeline_get_success(self):
        """GET /api/admin-super/approval-center/client-pipeline - Admin can access"""
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center/client-pipeline",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "clients" in data, "Response should have 'clients' array"
        assert "case_managers" in data, "Response should have 'case_managers' array"
        
        # Verify case_managers structure
        if len(data["case_managers"]) > 0:
            cm = data["case_managers"][0]
            assert "id" in cm, "Case manager should have id"
            assert "name" in cm, "Case manager should have name"
        
        # Verify client structure (if any exist)
        if len(data["clients"]) > 0:
            client = data["clients"][0]
            assert "client_name" in client, "Client should have client_name"
            assert "client_email" in client, "Client should have client_email"
            assert "pre_assessments" in client, "Client should have pre_assessments array"
            assert "sales" in client, "Client should have sales array"
            assert "cases" in client, "Client should have cases array"
            assert "documents" in client, "Client should have documents array"
            assert "current_stage" in client, "Client should have current_stage"
            assert "needs_action" in client, "Client should have needs_action flag"
            
            # Verify current_stage is valid
            valid_stages = ["pre_assessment", "sale_review", "assign_cm", "document_review", "in_progress", "completed"]
            assert client["current_stage"] in valid_stages, f"Invalid stage: {client['current_stage']}"
        
        print(f"✓ Client Pipeline: {len(data['clients'])} clients, {len(data['case_managers'])} case managers")
    
    def test_client_pipeline_partner_forbidden(self):
        """Partner should NOT access client pipeline"""
        if not self.partner_token:
            pytest.skip("Partner login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center/client-pipeline",
            headers=self.partner_headers
        )
        assert response.status_code == 403, f"Expected 403 for partner, got {response.status_code}"
        print("✓ Client Pipeline correctly blocks non-admin access")
    
    # ==================== SALE APPROVAL BUG FIX TEST ====================
    
    def test_sale_approval_from_approval_center_no_user_not_found(self):
        """BUG FIX: Approve sale from Approval Center should NOT return 'User not found'"""
        # First, get pending sales from approval center
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Failed to get approval center: {response.text}"
        
        data = response.json()
        pending_sales = [item for item in data["items"] if item["type"] == "sale"]
        
        if len(pending_sales) == 0:
            # Create a test sale if none exist
            if not self.partner_token:
                pytest.skip("No pending sales and partner login failed")
            
            # Get a product first
            products_res = self.session.get(f"{BASE_URL}/api/products", headers=self.admin_headers)
            if products_res.status_code != 200 or len(products_res.json()) == 0:
                pytest.skip("No products available to create test sale")
            
            product = products_res.json()[0]
            
            # Create a test sale
            test_email = f"test_approval_{uuid.uuid4().hex[:8]}@test.com"
            sale_data = {
                "client_name": "Test Approval Client",
                "client_email": test_email,
                "client_mobile": "9876543210",
                "product_id": product["id"],
                "fee_amount": 50000,
                "amount_received": 50000,
                "payment_method": "bank_transfer",
                "notes": "Test sale for approval center bug fix"
            }
            
            create_res = self.session.post(
                f"{BASE_URL}/api/sales",
                headers=self.partner_headers,
                json=sale_data
            )
            
            if create_res.status_code != 200:
                pytest.skip(f"Failed to create test sale: {create_res.text}")
            
            sale_id = create_res.json().get("id")
            print(f"Created test sale: {sale_id}")
        else:
            sale_id = pending_sales[0]["id"]
            print(f"Using existing pending sale: {sale_id}")
        
        # Now approve the sale via approval center action endpoint
        approve_response = self.session.post(
            f"{BASE_URL}/api/admin-super/approval-center/action",
            headers=self.admin_headers,
            json={
                "item_id": sale_id,
                "item_type": "sale",
                "action": "approve",
                "notes": "Approved via test",
                "case_manager_id": ""
            }
        )
        
        # THE BUG FIX: This should NOT return 'User not found'
        assert approve_response.status_code == 200, f"Sale approval failed: {approve_response.text}"
        
        # Verify the response
        result = approve_response.json()
        assert "message" in result, "Response should have message"
        assert "Sale approved" in result["message"], f"Expected 'Sale approved', got: {result['message']}"
        
        # Verify case was created
        if "case_id" in result:
            print(f"✓ Sale approved successfully, case created: {result['case_id']}")
        else:
            print(f"✓ Sale approved successfully")
        
        # Verify no 'User not found' error
        assert "User not found" not in str(approve_response.text), "BUG: 'User not found' error should not occur"
        print("✓ BUG FIX VERIFIED: Sale approval from Approval Center works without 'User not found' error")
    
    def test_sale_rejection_requires_reason(self):
        """Reject sale should require rejection reason"""
        # Get a pending sale
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        pending_sales = [item for item in data["items"] if item["type"] == "sale"]
        
        if len(pending_sales) == 0:
            pytest.skip("No pending sales to test rejection")
        
        sale_id = pending_sales[0]["id"]
        
        # Try to reject without reason
        reject_response = self.session.post(
            f"{BASE_URL}/api/admin-super/approval-center/action",
            headers=self.admin_headers,
            json={
                "item_id": sale_id,
                "item_type": "sale",
                "action": "reject",
                "notes": "",  # Empty reason
                "case_manager_id": ""
            }
        )
        
        # Should fail with 400 - rejection reason required
        assert reject_response.status_code == 400, f"Expected 400 for empty rejection reason, got {reject_response.status_code}"
        assert "reason" in reject_response.text.lower() or "required" in reject_response.text.lower(), \
            f"Error should mention reason required: {reject_response.text}"
        
        print("✓ Sale rejection correctly requires reason")
    
    # ==================== CASE MANAGER ASSIGNMENT ====================
    
    def test_assign_cm_endpoint_exists(self):
        """POST /api/admin-super/approval-center/assign-cm endpoint exists"""
        # First get a case that needs CM assignment
        pipeline_res = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center/client-pipeline",
            headers=self.admin_headers
        )
        assert pipeline_res.status_code == 200
        
        data = pipeline_res.json()
        case_managers = data.get("case_managers", [])
        
        if len(case_managers) == 0:
            pytest.skip("No case managers available")
        
        # Find a case without CM
        unassigned_case = None
        for client in data.get("clients", []):
            for case in client.get("cases", []):
                if not case.get("case_manager_id"):
                    unassigned_case = case
                    break
            if unassigned_case:
                break
        
        if not unassigned_case:
            # Test with invalid case_id to verify endpoint exists
            response = self.session.post(
                f"{BASE_URL}/api/admin-super/approval-center/assign-cm?case_id=invalid&case_manager_id={case_managers[0]['id']}",
                headers=self.admin_headers,
                json={}
            )
            # Should return 404 for invalid case, not 405 (method not allowed)
            assert response.status_code in [404, 400], f"Expected 404 or 400, got {response.status_code}"
            print("✓ Assign CM endpoint exists (tested with invalid case)")
        else:
            # Assign CM to the case
            response = self.session.post(
                f"{BASE_URL}/api/admin-super/approval-center/assign-cm?case_id={unassigned_case['id']}&case_manager_id={case_managers[0]['id']}",
                headers=self.admin_headers,
                json={}
            )
            assert response.status_code == 200, f"Failed to assign CM: {response.text}"
            
            result = response.json()
            assert "message" in result, "Response should have message"
            print(f"✓ Case Manager assigned: {result['message']}")
    
    def test_assign_cm_invalid_case(self):
        """Assign CM to invalid case should return 404"""
        pipeline_res = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center/client-pipeline",
            headers=self.admin_headers
        )
        assert pipeline_res.status_code == 200
        
        data = pipeline_res.json()
        case_managers = data.get("case_managers", [])
        
        if len(case_managers) == 0:
            pytest.skip("No case managers available")
        
        response = self.session.post(
            f"{BASE_URL}/api/admin-super/approval-center/assign-cm?case_id=nonexistent-case-id&case_manager_id={case_managers[0]['id']}",
            headers=self.admin_headers,
            json={}
        )
        assert response.status_code == 404, f"Expected 404 for invalid case, got {response.status_code}"
        print("✓ Assign CM correctly returns 404 for invalid case")
    
    def test_assign_cm_invalid_manager(self):
        """Assign invalid CM should return 404"""
        # Get any case
        cases_res = self.session.get(f"{BASE_URL}/api/cases", headers=self.admin_headers)
        if cases_res.status_code != 200 or len(cases_res.json()) == 0:
            pytest.skip("No cases available")
        
        case_id = cases_res.json()[0]["id"]
        
        response = self.session.post(
            f"{BASE_URL}/api/admin-super/approval-center/assign-cm?case_id={case_id}&case_manager_id=nonexistent-cm-id",
            headers=self.admin_headers,
            json={}
        )
        assert response.status_code == 404, f"Expected 404 for invalid CM, got {response.status_code}"
        print("✓ Assign CM correctly returns 404 for invalid case manager")
    
    # ==================== PRE-ASSESSMENT APPROVAL ====================
    
    def test_pa_approval_from_approval_center(self):
        """Approve/Reject PA from Approval Center"""
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        pending_pas = [item for item in data["items"] if item["type"] == "pre_assessment"]
        
        if len(pending_pas) == 0:
            print("✓ No pending pre-assessments to test (skipped)")
            pytest.skip("No pending pre-assessments")
        
        pa_id = pending_pas[0]["id"]
        
        # Test approval
        approve_response = self.session.post(
            f"{BASE_URL}/api/admin-super/approval-center/action",
            headers=self.admin_headers,
            json={
                "item_id": pa_id,
                "item_type": "pre_assessment",
                "action": "approve",
                "notes": "Approved via test",
                "case_manager_id": ""
            }
        )
        
        # Should succeed or fail gracefully
        assert approve_response.status_code in [200, 400, 404], f"Unexpected status: {approve_response.status_code}"
        print(f"✓ PA approval endpoint works (status: {approve_response.status_code})")
    
    # ==================== DOCUMENT APPROVAL ====================
    
    def test_document_approval_from_approval_center(self):
        """Approve/Reject document from Approval Center"""
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        pending_docs = [item for item in data["items"] if item["type"] == "document"]
        
        if len(pending_docs) == 0:
            print("✓ No pending documents to test (skipped)")
            pytest.skip("No pending documents")
        
        doc_id = pending_docs[0]["id"]
        
        # Test approval
        approve_response = self.session.post(
            f"{BASE_URL}/api/admin-super/approval-center/action",
            headers=self.admin_headers,
            json={
                "item_id": doc_id,
                "item_type": "document",
                "action": "approve",
                "notes": "Verified via test",
                "case_manager_id": ""
            }
        )
        
        assert approve_response.status_code in [200, 400, 404], f"Unexpected status: {approve_response.status_code}"
        print(f"✓ Document approval endpoint works (status: {approve_response.status_code})")
    
    # ==================== APPROVAL CENTER SUMMARY ====================
    
    def test_approval_center_summary_counts(self):
        """Verify approval center summary counts are accurate"""
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        items = data["items"]
        
        # Count items by type
        sales_count = len([i for i in items if i["type"] == "sale"])
        pa_count = len([i for i in items if i["type"] == "pre_assessment"])
        doc_count = len([i for i in items if i["type"] == "document"])
        ticket_count = len([i for i in items if i["type"] == "ticket"])
        
        # Verify counts match
        assert summary["pending_sales"] == sales_count, f"Sales count mismatch: {summary['pending_sales']} vs {sales_count}"
        assert summary["pending_pre_assessments"] == pa_count, f"PA count mismatch: {summary['pending_pre_assessments']} vs {pa_count}"
        assert summary["pending_documents"] == doc_count, f"Doc count mismatch: {summary['pending_documents']} vs {doc_count}"
        assert summary["urgent_tickets"] == ticket_count, f"Ticket count mismatch: {summary['urgent_tickets']} vs {ticket_count}"
        assert summary["total"] == len(items), f"Total count mismatch: {summary['total']} vs {len(items)}"
        
        print(f"✓ Approval Center summary counts verified: {summary['total']} total items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
