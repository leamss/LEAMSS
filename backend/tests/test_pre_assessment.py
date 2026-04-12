"""
Pre-Assessment Workflow Tests - Phase 8
Tests the complete pre-assessment workflow:
- Partner creates lead → Sends ₹5,100 payment link → Client pays → 
- Partner submits docs to Admin → Admin approves/rejects → 
- If approved: Partner sends sales proposal with payment link → Auto sale creation
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"


class TestPreAssessmentWorkflow:
    """Complete Pre-Assessment workflow tests"""
    
    partner_token = None
    admin_token = None
    created_pa_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens for tests"""
        # Get partner token
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTNER_EMAIL, "password": PARTNER_PASSWORD
        })
        assert res.status_code == 200, f"Partner login failed: {res.text}"
        TestPreAssessmentWorkflow.partner_token = res.json()["token"]
        
        # Get admin token
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        assert res.status_code == 200, f"Admin login failed: {res.text}"
        TestPreAssessmentWorkflow.admin_token = res.json()["token"]
    
    def partner_headers(self):
        return {"Authorization": f"Bearer {TestPreAssessmentWorkflow.partner_token}"}
    
    def admin_headers(self):
        return {"Authorization": f"Bearer {TestPreAssessmentWorkflow.admin_token}"}
    
    # ==================== CREATE PRE-ASSESSMENT ====================
    
    def test_01_create_pre_assessment_success(self):
        """POST /api/pre-assessment/create - Partner creates new pre-assessment"""
        unique_id = str(uuid.uuid4())[:6]
        payload = {
            "client_name": f"TEST_PA_Client_{unique_id}",
            "client_email": f"test_pa_{unique_id}@example.com",
            "client_mobile": "+91-9876543210",
            "country": "Canada",
            "service_type": "PR",
            "product_id": "",
            "notes": "Test pre-assessment for workflow testing",
            "client_age": 28,
            "education": "Bachelor's in Computer Science",
            "work_experience": "5 years in IT"
        }
        res = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=payload, headers=self.partner_headers())
        assert res.status_code == 200, f"Create PA failed: {res.text}"
        data = res.json()
        assert "id" in data
        assert "pa_number" in data
        assert data["pa_number"].startswith("PA-")
        TestPreAssessmentWorkflow.created_pa_id = data["id"]
        print(f"Created PA: {data['pa_number']} with ID: {data['id']}")
    
    def test_02_create_pre_assessment_missing_fields(self):
        """POST /api/pre-assessment/create - Fails without required fields"""
        payload = {"client_name": "Test"}  # Missing required fields
        res = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=payload, headers=self.partner_headers())
        assert res.status_code == 422, f"Expected 422 for missing fields, got {res.status_code}"
    
    # ==================== GET PRE-ASSESSMENTS ====================
    
    def test_03_get_my_assessments(self):
        """GET /api/pre-assessment/my-assessments - Partner gets their PAs"""
        res = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=self.partner_headers())
        assert res.status_code == 200, f"Get my assessments failed: {res.text}"
        data = res.json()
        assert isinstance(data, list)
        # Should contain the PA we just created
        pa_ids = [pa["id"] for pa in data]
        assert TestPreAssessmentWorkflow.created_pa_id in pa_ids, "Created PA not found in my-assessments"
    
    def test_04_get_single_pre_assessment(self):
        """GET /api/pre-assessment/{id} - Get single PA details"""
        pa_id = TestPreAssessmentWorkflow.created_pa_id
        res = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=self.partner_headers())
        assert res.status_code == 200, f"Get PA failed: {res.text}"
        data = res.json()
        assert data["id"] == pa_id
        assert data["stage"] == "new"
        assert data["pre_assessment_fee"] == 5100
        assert "documents" in data
    
    def test_05_get_stats_overview(self):
        """GET /api/pre-assessment/stats/overview - Get PA statistics"""
        res = requests.get(f"{BASE_URL}/api/pre-assessment/stats/overview", headers=self.partner_headers())
        assert res.status_code == 200, f"Get stats failed: {res.text}"
        data = res.json()
        assert "total" in data
        assert "new" in data
        assert "under_review" in data
        assert "approved" in data
        assert "conversion_rate" in data
    
    # ==================== SEND PAYMENT LINK ====================
    
    def test_06_send_payment_link(self):
        """POST /api/pre-assessment/{id}/send-payment-link - Partner sends ₹5,100 payment link"""
        pa_id = TestPreAssessmentWorkflow.created_pa_id
        res = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/send-payment-link", headers=self.partner_headers())
        assert res.status_code == 200, f"Send payment link failed: {res.text}"
        data = res.json()
        assert "message" in data
        assert "payment_url" in data
        # Verify stage changed to payment_pending
        pa_res = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=self.partner_headers())
        assert pa_res.json()["stage"] == "payment_pending"
    
    def test_07_send_payment_link_wrong_stage(self):
        """POST /api/pre-assessment/{id}/send-payment-link - Fails at wrong stage"""
        # First confirm payment to move to payment_received
        pa_id = TestPreAssessmentWorkflow.created_pa_id
        requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/confirm-payment", headers=self.partner_headers())
        # Now try to send payment link again - should fail
        res = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/send-payment-link", headers=self.partner_headers())
        assert res.status_code == 400, f"Expected 400 for wrong stage, got {res.status_code}"
    
    # ==================== CONFIRM PAYMENT ====================
    
    def test_08_confirm_payment(self):
        """POST /api/pre-assessment/{id}/confirm-payment - Confirm payment received"""
        # Create a new PA for this test
        unique_id = str(uuid.uuid4())[:6]
        payload = {
            "client_name": f"TEST_PA_Payment_{unique_id}",
            "client_email": f"test_payment_{unique_id}@example.com",
            "country": "Australia",
            "service_type": "Work Visa"
        }
        create_res = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=payload, headers=self.partner_headers())
        pa_id = create_res.json()["id"]
        
        # Send payment link first
        requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/send-payment-link", headers=self.partner_headers())
        
        # Confirm payment
        res = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/confirm-payment", headers=self.partner_headers())
        assert res.status_code == 200, f"Confirm payment failed: {res.text}"
        
        # Verify stage changed
        pa_res = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=self.partner_headers())
        assert pa_res.json()["stage"] == "payment_received"
        assert pa_res.json()["fee_payment_status"] == "paid"
    
    # ==================== MOCK PAYMENT ====================
    
    def test_09_mock_payment(self):
        """POST /api/pre-assessment/{id}/mock-payment - Mock payment for testing"""
        # Create a new PA
        unique_id = str(uuid.uuid4())[:6]
        payload = {
            "client_name": f"TEST_PA_Mock_{unique_id}",
            "client_email": f"test_mock_{unique_id}@example.com",
            "country": "UK",
            "service_type": "Student Visa"
        }
        create_res = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=payload, headers=self.partner_headers())
        pa_id = create_res.json()["id"]
        
        # Mock payment (no auth required)
        res = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/mock-payment")
        assert res.status_code == 200, f"Mock payment failed: {res.text}"
        
        # Verify stage changed
        pa_res = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=self.partner_headers())
        assert pa_res.json()["stage"] == "payment_received"
    
    # ==================== UPLOAD DOCUMENT ====================
    
    def test_10_upload_document(self):
        """POST /api/pre-assessment/{id}/upload-document - Upload document"""
        pa_id = TestPreAssessmentWorkflow.created_pa_id
        
        # Create a test file
        files = {"file": ("test_passport.pdf", b"Test PDF content", "application/pdf")}
        data = {"document_type": "passport"}
        
        res = requests.post(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/upload-document",
            files=files,
            data=data,
            headers=self.partner_headers()
        )
        assert res.status_code == 200, f"Upload document failed: {res.text}"
        assert "id" in res.json()
        assert res.json()["file_name"] == "test_passport.pdf"
    
    def test_11_get_documents(self):
        """GET /api/pre-assessment/{id}/documents - Get PA documents"""
        pa_id = TestPreAssessmentWorkflow.created_pa_id
        res = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}/documents", headers=self.partner_headers())
        assert res.status_code == 200, f"Get documents failed: {res.text}"
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the one we uploaded
    
    # ==================== SUBMIT DOCUMENTS ====================
    
    def test_12_submit_documents(self):
        """POST /api/pre-assessment/{id}/submit-documents - Submit to admin for review"""
        pa_id = TestPreAssessmentWorkflow.created_pa_id
        
        # Submit documents (multipart form)
        data = {"remarks": "Documents ready for review - test submission"}
        res = requests.post(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/submit-documents",
            data=data,
            headers=self.partner_headers()
        )
        assert res.status_code == 200, f"Submit documents failed: {res.text}"
        
        # Verify stage changed to under_review
        pa_res = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=self.partner_headers())
        assert pa_res.json()["stage"] == "under_review"
    
    def test_13_submit_documents_wrong_stage(self):
        """POST /api/pre-assessment/{id}/submit-documents - Fails at wrong stage"""
        # Create a new PA (stage=new)
        unique_id = str(uuid.uuid4())[:6]
        payload = {
            "client_name": f"TEST_PA_WrongStage_{unique_id}",
            "client_email": f"test_wrong_{unique_id}@example.com",
            "country": "Germany",
            "service_type": "Work Permit"
        }
        create_res = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=payload, headers=self.partner_headers())
        pa_id = create_res.json()["id"]
        
        # Try to submit without payment - should fail
        data = {"remarks": "Test"}
        res = requests.post(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/submit-documents",
            data=data,
            headers=self.partner_headers()
        )
        assert res.status_code == 400, f"Expected 400 for wrong stage, got {res.status_code}"
    
    # ==================== ADMIN QUEUE ====================
    
    def test_14_admin_queue(self):
        """GET /api/pre-assessment/admin/queue - Admin gets pending reviews"""
        res = requests.get(f"{BASE_URL}/api/pre-assessment/admin/queue", headers=self.admin_headers())
        assert res.status_code == 200, f"Admin queue failed: {res.text}"
        data = res.json()
        assert isinstance(data, list)
        # Should contain our submitted PA
        pa_ids = [pa["id"] for pa in data]
        assert TestPreAssessmentWorkflow.created_pa_id in pa_ids, "Submitted PA not in admin queue"
    
    def test_15_admin_queue_partner_forbidden(self):
        """GET /api/pre-assessment/admin/queue - Partner cannot access admin queue"""
        res = requests.get(f"{BASE_URL}/api/pre-assessment/admin/queue", headers=self.partner_headers())
        assert res.status_code == 403, f"Expected 403 for partner, got {res.status_code}"
    
    # ==================== ADMIN REVIEW ====================
    
    def test_16_admin_approve(self):
        """PUT /api/pre-assessment/{id}/review - Admin approves PA"""
        pa_id = TestPreAssessmentWorkflow.created_pa_id
        payload = {
            "decision": "approved",
            "reason": "Client meets all eligibility criteria for Canada PR",
            "notes": "Good profile, proceed with proposal"
        }
        res = requests.put(f"{BASE_URL}/api/pre-assessment/{pa_id}/review", json=payload, headers=self.admin_headers())
        assert res.status_code == 200, f"Admin approve failed: {res.text}"
        assert res.json()["stage"] == "approved"
        
        # Verify PA stage
        pa_res = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=self.partner_headers())
        assert pa_res.json()["stage"] == "approved"
        assert pa_res.json()["admin_decision"] == "approved"
    
    def test_17_admin_reject(self):
        """PUT /api/pre-assessment/{id}/review - Admin rejects PA"""
        # Create and submit a new PA for rejection test
        unique_id = str(uuid.uuid4())[:6]
        payload = {
            "client_name": f"TEST_PA_Reject_{unique_id}",
            "client_email": f"test_reject_{unique_id}@example.com",
            "country": "Canada",
            "service_type": "PR"
        }
        create_res = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=payload, headers=self.partner_headers())
        pa_id = create_res.json()["id"]
        
        # Move through stages
        requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/mock-payment")
        requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/submit-documents", data={"remarks": "Test"}, headers=self.partner_headers())
        
        # Admin rejects
        reject_payload = {
            "decision": "rejected",
            "reason": "Client does not meet minimum CRS score requirements",
            "notes": "Recommend improving IELTS score"
        }
        res = requests.put(f"{BASE_URL}/api/pre-assessment/{pa_id}/review", json=reject_payload, headers=self.admin_headers())
        assert res.status_code == 200, f"Admin reject failed: {res.text}"
        
        # Verify stage is refund_initiated (rejection triggers refund)
        pa_res = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=self.partner_headers())
        assert pa_res.json()["admin_decision"] == "rejected"
        assert pa_res.json()["stage"] == "refund_initiated"
    
    def test_18_admin_review_invalid_decision(self):
        """PUT /api/pre-assessment/{id}/review - Invalid decision fails"""
        # Create a new PA for this test
        unique_id = str(uuid.uuid4())[:6]
        payload = {
            "client_name": f"TEST_PA_Invalid_{unique_id}",
            "client_email": f"test_invalid_{unique_id}@example.com",
            "country": "USA",
            "service_type": "H1B"
        }
        create_res = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=payload, headers=self.partner_headers())
        pa_id = create_res.json()["id"]
        
        # Move through stages
        requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/mock-payment")
        requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/submit-documents", data={"remarks": "Test"}, headers=self.partner_headers())
        
        # Try invalid decision
        invalid_payload = {"decision": "maybe", "reason": "Test"}
        res = requests.put(f"{BASE_URL}/api/pre-assessment/{pa_id}/review", json=invalid_payload, headers=self.admin_headers())
        assert res.status_code == 400, f"Expected 400 for invalid decision, got {res.status_code}"
    
    def test_19_admin_review_partner_forbidden(self):
        """PUT /api/pre-assessment/{id}/review - Partner cannot review"""
        pa_id = TestPreAssessmentWorkflow.created_pa_id
        payload = {"decision": "approved", "reason": "Test"}
        res = requests.put(f"{BASE_URL}/api/pre-assessment/{pa_id}/review", json=payload, headers=self.partner_headers())
        assert res.status_code == 403, f"Expected 403 for partner, got {res.status_code}"
    
    # ==================== SEND PROPOSAL ====================
    
    def test_20_send_proposal(self):
        """POST /api/pre-assessment/{id}/send-proposal - Partner sends proposal after approval"""
        pa_id = TestPreAssessmentWorkflow.created_pa_id
        payload = {
            "fee_amount": 150000,
            "payment_method": "online",
            "notes": "Canada PR Express Entry - Full service package",
            "currency": "INR"
        }
        res = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/send-proposal", json=payload, headers=self.partner_headers())
        assert res.status_code == 200, f"Send proposal failed: {res.text}"
        data = res.json()
        assert "sale_id" in data
        assert data["message"].startswith("Proposal sent")
        
        # Verify stage changed
        pa_res = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=self.partner_headers())
        assert pa_res.json()["stage"] == "proposal_sent"
        assert pa_res.json()["proposal_fee"] == 150000
        assert pa_res.json()["sale_id"] is not None
    
    def test_21_send_proposal_not_approved(self):
        """POST /api/pre-assessment/{id}/send-proposal - Fails if not approved"""
        # Create a new PA (stage=new)
        unique_id = str(uuid.uuid4())[:6]
        payload = {
            "client_name": f"TEST_PA_NotApproved_{unique_id}",
            "client_email": f"test_notapproved_{unique_id}@example.com",
            "country": "Canada",
            "service_type": "PR"
        }
        create_res = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=payload, headers=self.partner_headers())
        pa_id = create_res.json()["id"]
        
        # Try to send proposal without approval
        proposal_payload = {"fee_amount": 100000, "currency": "INR"}
        res = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/send-proposal", json=proposal_payload, headers=self.partner_headers())
        assert res.status_code == 400, f"Expected 400 for not approved, got {res.status_code}"
    
    # ==================== NOT FOUND TESTS ====================
    
    def test_22_get_nonexistent_pa(self):
        """GET /api/pre-assessment/{id} - Returns 404 for non-existent PA"""
        res = requests.get(f"{BASE_URL}/api/pre-assessment/nonexistent-id-12345", headers=self.partner_headers())
        assert res.status_code == 404
    
    def test_23_review_nonexistent_pa(self):
        """PUT /api/pre-assessment/{id}/review - Returns 404 for non-existent PA"""
        payload = {"decision": "approved", "reason": "Test"}
        res = requests.put(f"{BASE_URL}/api/pre-assessment/nonexistent-id-12345/review", json=payload, headers=self.admin_headers())
        assert res.status_code == 404


class TestPreAssessmentAuth:
    """Authentication tests for pre-assessment endpoints"""
    
    def test_01_create_without_auth(self):
        """POST /api/pre-assessment/create - Requires authentication"""
        payload = {"client_name": "Test", "client_email": "test@test.com", "country": "Canada", "service_type": "PR"}
        res = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=payload)
        assert res.status_code == 401 or res.status_code == 403
    
    def test_02_my_assessments_without_auth(self):
        """GET /api/pre-assessment/my-assessments - Requires authentication"""
        res = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments")
        assert res.status_code == 401 or res.status_code == 403
    
    def test_03_stats_without_auth(self):
        """GET /api/pre-assessment/stats/overview - Requires authentication"""
        res = requests.get(f"{BASE_URL}/api/pre-assessment/stats/overview")
        assert res.status_code == 401 or res.status_code == 403


class TestExistingFeatures:
    """Verify existing features still work"""
    
    partner_token = None
    admin_token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens"""
        res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": PARTNER_EMAIL, "password": PARTNER_PASSWORD})
        TestExistingFeatures.partner_token = res.json()["token"]
        res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        TestExistingFeatures.admin_token = res.json()["token"]
    
    def partner_headers(self):
        return {"Authorization": f"Bearer {TestExistingFeatures.partner_token}"}
    
    def admin_headers(self):
        return {"Authorization": f"Bearer {TestExistingFeatures.admin_token}"}
    
    def test_01_partner_dashboard_stats(self):
        """GET /api/stats/partner-dashboard - Partner dashboard still works"""
        res = requests.get(f"{BASE_URL}/api/stats/partner-dashboard", headers=self.partner_headers())
        assert res.status_code == 200
        data = res.json()
        assert "total_sales" in data
        assert "approved_sales" in data
    
    def test_02_partner_my_sales(self):
        """GET /api/sales/my-sales - Partner sales still works"""
        res = requests.get(f"{BASE_URL}/api/sales/my-sales", headers=self.partner_headers())
        assert res.status_code == 200
        assert isinstance(res.json(), list)
    
    def test_03_admin_dashboard_stats(self):
        """GET /api/stats/dashboard - Admin dashboard still works"""
        res = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=self.admin_headers())
        assert res.status_code == 200
        data = res.json()
        assert "pending_sales" in data
        assert "active_cases" in data
    
    def test_04_admin_pending_sales(self):
        """GET /api/sales/pending - Admin pending sales still works"""
        res = requests.get(f"{BASE_URL}/api/sales/pending", headers=self.admin_headers())
        assert res.status_code == 200
        assert isinstance(res.json(), list)
    
    def test_05_products_list(self):
        """GET /api/products - Products list still works"""
        res = requests.get(f"{BASE_URL}/api/products", headers=self.partner_headers())
        assert res.status_code == 200
        assert isinstance(res.json(), list)
    
    def test_06_health_check(self):
        """GET /api/health - Health check still works"""
        res = requests.get(f"{BASE_URL}/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"
