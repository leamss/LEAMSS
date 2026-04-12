"""
Iteration 50: Refund Manager Overhaul Tests
Tests the 2-step refund flow: Initiate → Review (approve/reject)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRefundManagerAPIs:
    """Test Refund Manager 2-step flow APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        self.token = login_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print(f"Admin logged in successfully")
    
    # ========== GET /api/refunds ==========
    def test_get_refunds_success(self):
        """Test GET /api/refunds returns list of refunds"""
        resp = self.session.get(f"{BASE_URL}/api/refunds")
        assert resp.status_code == 200, f"GET /api/refunds failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        # Check structure if refunds exist
        if len(data) > 0:
            refund = data[0]
            assert "id" in refund, "Refund should have id"
            assert "status" in refund, "Refund should have status"
            assert "amount" in refund, "Refund should have amount"
            print(f"Found {len(data)} refunds")
    
    def test_get_refunds_unauthorized(self):
        """Test GET /api/refunds requires auth"""
        session = requests.Session()
        resp = session.get(f"{BASE_URL}/api/refunds")
        assert resp.status_code in [401, 403], "Should require authentication"
    
    # ========== GET /api/admin-super/refund-manager ==========
    def test_refund_manager_dashboard(self):
        """Test refund manager dashboard endpoint"""
        resp = self.session.get(f"{BASE_URL}/api/admin-super/refund-manager")
        assert resp.status_code == 200, f"Refund manager dashboard failed: {resp.text}"
        data = resp.json()
        # Check expected fields
        assert "refunds" in data, "Should have refunds list"
        assert "stats" in data, "Should have stats"
        assert "eligible_for_refund" in data, "Should have eligible_for_refund list"
        print(f"Dashboard: {len(data.get('refunds', []))} refunds, {len(data.get('eligible_for_refund', []))} eligible")
    
    # ========== POST /api/refunds (Initiate) ==========
    def test_initiate_refund_requires_reason(self):
        """Test POST /api/refunds requires reason (min 5 chars)"""
        # First get an eligible sale
        dashboard = self.session.get(f"{BASE_URL}/api/admin-super/refund-manager").json()
        eligible = dashboard.get("eligible_for_refund", [])
        
        if not eligible:
            pytest.skip("No eligible sales for refund")
        
        sale = eligible[0]
        resp = self.session.post(f"{BASE_URL}/api/refunds", json={
            "sale_id": sale["sale_id"],
            "amount": 100,
            "reason": "abc",  # Too short
            "category": "other"
        })
        assert resp.status_code == 400, "Should reject short reason"
        assert "minimum 5" in resp.json().get("detail", "").lower(), "Should mention minimum chars"
    
    def test_initiate_refund_requires_positive_amount(self):
        """Test POST /api/refunds requires positive amount"""
        dashboard = self.session.get(f"{BASE_URL}/api/admin-super/refund-manager").json()
        eligible = dashboard.get("eligible_for_refund", [])
        
        if not eligible:
            pytest.skip("No eligible sales for refund")
        
        sale = eligible[0]
        resp = self.session.post(f"{BASE_URL}/api/refunds", json={
            "sale_id": sale["sale_id"],
            "amount": 0,
            "reason": "Test refund reason",
            "category": "other"
        })
        assert resp.status_code == 400, "Should reject zero amount"
    
    def test_initiate_refund_success(self):
        """Test POST /api/refunds creates pending_review refund"""
        dashboard = self.session.get(f"{BASE_URL}/api/admin-super/refund-manager").json()
        eligible = dashboard.get("eligible_for_refund", [])
        
        if not eligible:
            pytest.skip("No eligible sales for refund")
        
        sale = eligible[0]
        refund_amount = min(100, sale.get("max_refundable", 100))
        
        resp = self.session.post(f"{BASE_URL}/api/refunds", json={
            "sale_id": sale["sale_id"],
            "amount": refund_amount,
            "reason": "Test refund for iteration 50",
            "category": "client_request",
            "refund_method": "original_payment",
            "notes": "Testing 2-step flow"
        })
        assert resp.status_code == 200, f"Initiate refund failed: {resp.text}"
        data = resp.json()
        assert data.get("status") == "pending_review", "Status should be pending_review"
        assert "refund_id" in data, "Should return refund_id"
        print(f"Created refund {data['refund_id']} with status pending_review")
        
        # Store for later tests
        self.__class__.test_refund_id = data["refund_id"]
    
    # ========== GET /api/refunds/detail/{id} ==========
    def test_refund_detail_endpoint(self):
        """Test GET /api/refunds/detail/{id} returns full detail"""
        # Get any refund
        refunds = self.session.get(f"{BASE_URL}/api/refunds").json()
        if not refunds:
            pytest.skip("No refunds to test detail")
        
        refund_id = refunds[0]["id"]
        resp = self.session.get(f"{BASE_URL}/api/refunds/detail/{refund_id}")
        assert resp.status_code == 200, f"Detail endpoint failed: {resp.text}"
        data = resp.json()
        
        # Check detail fields
        assert "id" in data, "Should have id"
        assert "sale" in data, "Should have sale info"
        assert "initiator" in data or "initiated_by_name" in data, "Should have initiator info"
        print(f"Detail for refund {refund_id}: status={data.get('status')}, amount={data.get('amount')}")
    
    def test_refund_detail_not_found(self):
        """Test GET /api/refunds/detail/{id} returns 404 for invalid id"""
        resp = self.session.get(f"{BASE_URL}/api/refunds/detail/invalid-id-12345")
        assert resp.status_code == 404, "Should return 404 for invalid id"
    
    # ========== POST /api/refunds/review (Approve/Reject) ==========
    def test_review_refund_reject_requires_reason(self):
        """Test POST /api/refunds/review reject requires reason"""
        # Get a pending_review refund
        refunds = self.session.get(f"{BASE_URL}/api/refunds").json()
        pending = [r for r in refunds if r.get("status") == "pending_review"]
        
        if not pending:
            pytest.skip("No pending_review refunds to test")
        
        refund = pending[0]
        resp = self.session.post(f"{BASE_URL}/api/refunds/review", json={
            "refund_id": refund["id"],
            "action": "reject",
            "review_notes": "abc"  # Too short
        })
        assert resp.status_code == 400, "Should reject short rejection reason"
        assert "min" in resp.json().get("detail", "").lower() or "required" in resp.json().get("detail", "").lower()
    
    def test_review_refund_approve_success(self):
        """Test POST /api/refunds/review approve processes refund"""
        # First create a new refund to approve
        dashboard = self.session.get(f"{BASE_URL}/api/admin-super/refund-manager").json()
        eligible = dashboard.get("eligible_for_refund", [])
        
        if not eligible:
            pytest.skip("No eligible sales for refund")
        
        sale = eligible[0]
        refund_amount = min(50, sale.get("max_refundable", 50))
        
        # Create refund
        create_resp = self.session.post(f"{BASE_URL}/api/refunds", json={
            "sale_id": sale["sale_id"],
            "amount": refund_amount,
            "reason": "Test approve flow iteration 50",
            "category": "service_issue"
        })
        
        if create_resp.status_code != 200:
            pytest.skip(f"Could not create refund: {create_resp.text}")
        
        refund_id = create_resp.json()["refund_id"]
        
        # Approve it
        resp = self.session.post(f"{BASE_URL}/api/refunds/review", json={
            "refund_id": refund_id,
            "action": "approve",
            "review_notes": "Approved for testing"
        })
        assert resp.status_code == 200, f"Approve failed: {resp.text}"
        data = resp.json()
        assert "approved" in data.get("message", "").lower() or "processed" in data.get("message", "").lower()
        print(f"Approved refund {refund_id}")
        
        # Verify status changed
        detail = self.session.get(f"{BASE_URL}/api/refunds/detail/{refund_id}").json()
        assert detail.get("status") == "processed", f"Status should be processed, got {detail.get('status')}"
    
    def test_review_refund_reject_success(self):
        """Test POST /api/refunds/review reject works with reason"""
        # First create a new refund to reject
        dashboard = self.session.get(f"{BASE_URL}/api/admin-super/refund-manager").json()
        eligible = dashboard.get("eligible_for_refund", [])
        
        if not eligible:
            pytest.skip("No eligible sales for refund")
        
        sale = eligible[0]
        refund_amount = min(25, sale.get("max_refundable", 25))
        
        # Create refund
        create_resp = self.session.post(f"{BASE_URL}/api/refunds", json={
            "sale_id": sale["sale_id"],
            "amount": refund_amount,
            "reason": "Test reject flow iteration 50",
            "category": "duplicate_payment"
        })
        
        if create_resp.status_code != 200:
            pytest.skip(f"Could not create refund: {create_resp.text}")
        
        refund_id = create_resp.json()["refund_id"]
        
        # Reject it
        resp = self.session.post(f"{BASE_URL}/api/refunds/review", json={
            "refund_id": refund_id,
            "action": "reject",
            "review_notes": "Rejected for testing - not a valid duplicate"
        })
        assert resp.status_code == 200, f"Reject failed: {resp.text}"
        data = resp.json()
        assert "rejected" in data.get("message", "").lower()
        print(f"Rejected refund {refund_id}")
        
        # Verify status changed
        detail = self.session.get(f"{BASE_URL}/api/refunds/detail/{refund_id}").json()
        assert detail.get("status") == "rejected", f"Status should be rejected, got {detail.get('status')}"
    
    def test_review_already_processed_refund(self):
        """Test cannot review already processed refund"""
        refunds = self.session.get(f"{BASE_URL}/api/refunds").json()
        processed = [r for r in refunds if r.get("status") in ["processed", "rejected"]]
        
        if not processed:
            pytest.skip("No processed refunds to test")
        
        refund = processed[0]
        resp = self.session.post(f"{BASE_URL}/api/refunds/review", json={
            "refund_id": refund["id"],
            "action": "approve",
            "review_notes": "Try to re-approve"
        })
        assert resp.status_code == 400, "Should not allow reviewing already processed refund"
    
    # ========== Category field ==========
    def test_refund_categories(self):
        """Test refund categories are stored correctly"""
        dashboard = self.session.get(f"{BASE_URL}/api/admin-super/refund-manager").json()
        eligible = dashboard.get("eligible_for_refund", [])
        
        if not eligible:
            pytest.skip("No eligible sales for refund")
        
        sale = eligible[0]
        categories = ["service_issue", "client_request", "overcharge", "duplicate_payment", "other"]
        
        for category in categories[:2]:  # Test first 2 to avoid too many refunds
            resp = self.session.post(f"{BASE_URL}/api/refunds", json={
                "sale_id": sale["sale_id"],
                "amount": 10,
                "reason": f"Test category {category}",
                "category": category
            })
            if resp.status_code == 200:
                refund_id = resp.json()["refund_id"]
                detail = self.session.get(f"{BASE_URL}/api/refunds/detail/{refund_id}").json()
                assert detail.get("category") == category, f"Category should be {category}"
                print(f"Category {category} stored correctly")


class TestRefundManagerPartnerAccess:
    """Test that partners cannot access refund manager"""
    
    def test_partner_cannot_access_refunds(self):
        """Partners should not access refund endpoints"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login as partner
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        if login_resp.status_code != 200:
            pytest.skip("Partner login failed")
        
        token = login_resp.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        resp = session.get(f"{BASE_URL}/api/refunds")
        assert resp.status_code == 403, "Partner should not access refunds"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
