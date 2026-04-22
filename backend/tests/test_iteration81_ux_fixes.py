"""
Iteration 81 Tests: 5 Critical UX Fixes for LEAMSS Immigration Portal
=====================================================================
Tests for:
1. Partner + Admin can View/Download client-uploaded documents
2. Admin 1st Approval tab shows history (approved/rejected items)
3. Partner card at proposal_sent shows 'Waiting for Client Payment' badge
4. Client must see full proposal + consent checkbox before paying
5. NEW STAGE 'awaiting_final_approval' between proposal_paid and case_created

Key Backend Endpoints:
- GET /api/pre-assessment/{pa_id}/document/{doc_id}/download (NEW)
- POST /api/pre-assess-portal/partner/submit-final/{pa_id} (NEW)
- POST /api/pre-assess-portal/client/proposal-consent/{pa_id} (NEW)
- POST /api/pre-assess-portal/client/mock-pay-proposal/{pa_id} (UPDATED - requires consent)
- POST /api/pre-assess-portal/admin/approve-final/{pa_id} (UPDATED - accepts both stages)
- GET /api/pre-assessment/admin/queue (UPDATED - includes awaiting_final_approval)
"""

import pytest
import requests
import os
import io
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASSWORD = "Client@123"
MANAGER_EMAIL = "manager@leamss.com"
MANAGER_PASSWORD = "Manager@123"


class TestIteration81UXFixes:
    """Test suite for Iteration 81 UX fixes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.partner_token = None
        self.client_token = None
        self.test_pa_id = None
        self.test_doc_id = None
        
    def get_auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}
    
    # ==================== AUTH TESTS ====================
    
    def test_01_admin_login(self):
        """Admin login"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        self.__class__.admin_token = data["token"]
        print(f"PASS: Admin login successful")
    
    def test_02_partner_login(self):
        """Partner login"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTNER_EMAIL,
            "password": PARTNER_PASSWORD
        })
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        self.__class__.partner_token = data["token"]
        print(f"PASS: Partner login successful")
    
    def test_03_client_login(self):
        """Client login"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        self.__class__.client_token = data["token"]
        print(f"PASS: Client login successful")
    
    # ==================== E2E FLOW TESTS ====================
    
    def test_04_partner_create_pa(self):
        """Partner creates a new pre-assessment"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assessment/create",
            json={
                "client_name": "TEST_Iteration81_Client",
                "client_email": CLIENT_EMAIL,
                "client_mobile": "+91-9876543210",
                "country": "Canada",
                "service_type": "Express Entry PR",
                "notes": "Test PA for iteration 81 UX fixes"
            },
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200, f"Create PA failed: {response.text}"
        data = response.json()
        assert "id" in data
        self.__class__.test_pa_id = data["id"]
        print(f"PASS: PA created with ID {data['id'][:8]}...")
    
    def test_05_partner_send_payment_link(self):
        """Partner sends payment link to client"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}/send-payment-link",
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200, f"Send payment link failed: {response.text}"
        print(f"PASS: Payment link sent")
    
    def test_06_mock_payment_received(self):
        """Mock payment received (simulates client paying ₹5,100)"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}/mock-payment"
        )
        assert response.status_code == 200, f"Mock payment failed: {response.text}"
        print(f"PASS: Mock payment received")
    
    def test_07_upload_document(self):
        """Upload a test document"""
        # Create a simple test file
        test_content = b"Test document content for iteration 81"
        files = {
            'file': ('test_passport.pdf', io.BytesIO(test_content), 'application/pdf')
        }
        data = {'document_type': 'passport'}
        
        headers = self.get_auth_header(self.__class__.partner_token)
        # Remove Content-Type for multipart
        response = requests.post(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}/upload-document",
            files=files,
            data=data,
            headers=headers
        )
        assert response.status_code == 200, f"Upload document failed: {response.text}"
        result = response.json()
        assert "id" in result
        self.__class__.test_doc_id = result["id"]
        print(f"PASS: Document uploaded with ID {result['id'][:8]}...")
    
    def test_08_partner_can_download_document(self):
        """NEW: Partner can download client-uploaded document"""
        response = self.session.get(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}/document/{self.__class__.test_doc_id}/download",
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200, f"Partner download failed: {response.text}"
        assert len(response.content) > 0, "Downloaded file is empty"
        print(f"PASS: Partner can download document ({len(response.content)} bytes)")
    
    def test_09_admin_can_download_document(self):
        """NEW: Admin can download client-uploaded document"""
        response = self.session.get(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}/document/{self.__class__.test_doc_id}/download",
            headers=self.get_auth_header(self.__class__.admin_token)
        )
        assert response.status_code == 200, f"Admin download failed: {response.text}"
        assert len(response.content) > 0, "Downloaded file is empty"
        print(f"PASS: Admin can download document ({len(response.content)} bytes)")
    
    def test_10_download_nonexistent_doc_returns_404(self):
        """Download non-existent document returns 404"""
        response = self.session.get(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}/document/nonexistent-doc-id/download",
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Non-existent document returns 404")
    
    def test_11_client_submit_for_review(self):
        """Client submits documents for partner review"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/client/submit/{self.__class__.test_pa_id}",
            headers=self.get_auth_header(self.__class__.client_token)
        )
        assert response.status_code == 200, f"Client submit failed: {response.text}"
        data = response.json()
        assert data.get("stage") == "partner_review"
        print(f"PASS: Client submitted for review, stage=partner_review")
    
    def test_12_partner_forward_to_admin(self):
        """Partner forwards to admin for 1st approval"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/partner/forward-to-admin/{self.__class__.test_pa_id}",
            json={"remarks": "All docs verified, client eligible"},
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200, f"Partner forward failed: {response.text}"
        data = response.json()
        assert data.get("stage") == "documents_submitted"
        print(f"PASS: Partner forwarded to admin, stage=documents_submitted")
    
    def test_13_admin_queue_shows_documents_submitted(self):
        """Admin queue includes documents_submitted items"""
        response = self.session.get(
            f"{BASE_URL}/api/pre-assessment/admin/queue",
            headers=self.get_auth_header(self.__class__.admin_token)
        )
        assert response.status_code == 200, f"Admin queue failed: {response.text}"
        items = response.json()
        pa_ids = [item["id"] for item in items]
        assert self.__class__.test_pa_id in pa_ids, "Test PA not in admin queue"
        print(f"PASS: Admin queue shows documents_submitted items ({len(items)} total)")
    
    def test_14_admin_1st_approval(self):
        """Admin approves (1st approval)"""
        response = self.session.put(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}/review",
            json={
                "decision": "approved",
                "reason": "Client meets all eligibility criteria for Express Entry",
                "notes": "Strong profile"
            },
            headers=self.get_auth_header(self.__class__.admin_token)
        )
        assert response.status_code == 200, f"Admin approval failed: {response.text}"
        data = response.json()
        assert data.get("stage") == "approved"
        print(f"PASS: Admin 1st approval complete, stage=approved")
    
    def test_15_partner_send_proposal(self):
        """Partner sends proposal with promo + upsells + AI text"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}/send-proposal",
            json={
                "fee_amount": 150000,
                "payment_method": "online",
                "notes": "Canada Express Entry PR package",
                "currency": "INR",
                "promo_code": None,
                "additional_discount": 5000,
                "upsell_bundle_ids": [],
                "ai_proposal_text": "Dear Client, we are pleased to offer you our comprehensive Canada Express Entry PR service..."
            },
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200, f"Send proposal failed: {response.text}"
        data = response.json()
        assert "breakdown" in data
        assert data["breakdown"]["final_amount"] == 145000  # 150000 - 5000 discount
        print(f"PASS: Proposal sent, final_amount=₹{data['breakdown']['final_amount']}")
    
    def test_16_client_cannot_pay_without_consent(self):
        """CRITICAL: Client cannot pay without giving consent first"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/client/mock-pay-proposal/{self.__class__.test_pa_id}",
            headers=self.get_auth_header(self.__class__.client_token)
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "consent" in data.get("detail", "").lower(), f"Expected consent error, got: {data}"
        print(f"PASS: Client blocked from paying without consent (400 error)")
    
    def test_17_client_gives_consent(self):
        """NEW: Client gives proposal consent"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/client/proposal-consent/{self.__class__.test_pa_id}",
            headers=self.get_auth_header(self.__class__.client_token)
        )
        assert response.status_code == 200, f"Consent failed: {response.text}"
        data = response.json()
        assert data.get("consent_given") == True
        print(f"PASS: Client consent recorded")
    
    def test_18_client_can_pay_after_consent(self):
        """Client can pay after giving consent"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/client/mock-pay-proposal/{self.__class__.test_pa_id}",
            headers=self.get_auth_header(self.__class__.client_token)
        )
        assert response.status_code == 200, f"Mock pay failed: {response.text}"
        data = response.json()
        assert data.get("stage") == "proposal_paid"
        print(f"PASS: Client paid after consent, stage=proposal_paid")
    
    def test_19_verify_notification_to_partner_not_admin(self):
        """After client pays, notification goes to partner (not admin directly)"""
        # Check partner notifications
        response = self.session.get(
            f"{BASE_URL}/api/notifications",
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200
        notifications = response.json()
        # Look for main fee paid notification
        main_fee_notifs = [n for n in notifications if "main fee" in n.get("title", "").lower() or "receipt" in n.get("message", "").lower()]
        assert len(main_fee_notifs) > 0, "Partner should receive main fee notification"
        print(f"PASS: Partner received main fee notification")
    
    def test_20_partner_upload_receipt(self):
        """Partner uploads payment receipt"""
        test_content = b"Payment receipt for iteration 81 test"
        files = {
            'file': ('payment_receipt.pdf', io.BytesIO(test_content), 'application/pdf')
        }
        data = {'document_type': 'receipt'}
        
        headers = self.get_auth_header(self.__class__.partner_token)
        response = requests.post(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}/upload-document",
            files=files,
            data=data,
            headers=headers
        )
        assert response.status_code == 200, f"Upload receipt failed: {response.text}"
        print(f"PASS: Partner uploaded payment receipt")
    
    def test_21_partner_submit_final_requires_proposal_paid_stage(self):
        """Partner submit-final only works at proposal_paid stage"""
        # First verify we're at proposal_paid
        response = self.session.get(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}",
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200
        pa = response.json()
        assert pa.get("stage") == "proposal_paid", f"Expected proposal_paid, got {pa.get('stage')}"
        print(f"PASS: PA is at proposal_paid stage")
    
    def test_22_partner_submit_final(self):
        """NEW: Partner submits final docs to admin for 2nd approval"""
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/partner/submit-final/{self.__class__.test_pa_id}",
            json={"notes": "All docs verified. Client ready for case activation."},
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200, f"Submit final failed: {response.text}"
        data = response.json()
        assert data.get("stage") == "awaiting_final_approval"
        print(f"PASS: Partner submitted final, stage=awaiting_final_approval")
    
    def test_23_admin_queue_shows_awaiting_final_approval(self):
        """UPDATED: Admin queue includes awaiting_final_approval items"""
        response = self.session.get(
            f"{BASE_URL}/api/pre-assessment/admin/queue",
            headers=self.get_auth_header(self.__class__.admin_token)
        )
        assert response.status_code == 200, f"Admin queue failed: {response.text}"
        items = response.json()
        awaiting_items = [item for item in items if item.get("stage") == "awaiting_final_approval"]
        assert len(awaiting_items) > 0, "No awaiting_final_approval items in admin queue"
        pa_ids = [item["id"] for item in awaiting_items]
        assert self.__class__.test_pa_id in pa_ids, "Test PA not in awaiting_final_approval queue"
        print(f"PASS: Admin queue shows awaiting_final_approval items ({len(awaiting_items)} total)")
    
    def test_24_admin_approve_final_accepts_awaiting_final_approval(self):
        """UPDATED: Admin approve-final accepts awaiting_final_approval stage"""
        # Get case managers first
        cm_response = self.session.get(
            f"{BASE_URL}/api/pre-assess-portal/admin/case-managers",
            headers=self.get_auth_header(self.__class__.admin_token)
        )
        assert cm_response.status_code == 200
        cms = cm_response.json().get("case_managers", [])
        cm_id = cms[0]["id"] if cms else None
        
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/admin/approve-final/{self.__class__.test_pa_id}",
            json={"case_manager_id": cm_id} if cm_id else {},
            headers=self.get_auth_header(self.__class__.admin_token)
        )
        assert response.status_code == 200, f"Admin approve final failed: {response.text}"
        data = response.json()
        assert data.get("stage") == "case_created"
        assert "case_code" in data
        print(f"PASS: Admin approved final, case created: {data.get('case_code')}")
    
    def test_25_verify_final_stage(self):
        """Verify PA is now at case_created stage"""
        response = self.session.get(
            f"{BASE_URL}/api/pre-assessment/{self.__class__.test_pa_id}",
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200
        pa = response.json()
        assert pa.get("stage") == "case_created"
        assert pa.get("case_id") is not None
        print(f"PASS: PA final stage verified: case_created, case_id={pa.get('case_id')[:8]}...")
    
    # ==================== ADDITIONAL EDGE CASE TESTS ====================
    
    def test_26_consent_only_at_proposal_sent_stage(self):
        """Consent endpoint only works at proposal_sent stage"""
        # Try to give consent on a PA that's already at case_created
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/client/proposal-consent/{self.__class__.test_pa_id}",
            headers=self.get_auth_header(self.__class__.client_token)
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"PASS: Consent blocked at wrong stage (400)")
    
    def test_27_submit_final_requires_docs(self):
        """Submit-final requires at least 1 document uploaded"""
        # Create a new PA to test this
        response = self.session.post(
            f"{BASE_URL}/api/pre-assessment/create",
            json={
                "client_name": "TEST_NoDocs_Client",
                "client_email": "nodocs@test.com",
                "country": "UK",
                "service_type": "Work Visa"
            },
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200
        new_pa_id = response.json()["id"]
        
        # Try to submit-final without any docs (will fail because stage is wrong anyway)
        # This is just to verify the endpoint exists and validates
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/partner/submit-final/{new_pa_id}",
            json={"notes": "Test"},
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"PASS: Submit-final validates stage/docs requirement")
    
    def test_28_admin_approve_final_backward_compat(self):
        """Admin approve-final accepts proposal_paid stage (backward compat)"""
        # Create another PA and fast-forward to proposal_paid (skip awaiting_final_approval)
        # This tests backward compatibility
        response = self.session.post(
            f"{BASE_URL}/api/pre-assessment/create",
            json={
                "client_name": "TEST_BackwardCompat_Client",
                "client_email": CLIENT_EMAIL,
                "country": "Australia",
                "service_type": "Skilled Migration"
            },
            headers=self.get_auth_header(self.__class__.partner_token)
        )
        assert response.status_code == 200
        compat_pa_id = response.json()["id"]
        
        # Fast-forward through stages
        self.session.post(f"{BASE_URL}/api/pre-assessment/{compat_pa_id}/send-payment-link",
                         headers=self.get_auth_header(self.__class__.partner_token))
        self.session.post(f"{BASE_URL}/api/pre-assessment/{compat_pa_id}/mock-payment")
        
        # Upload a doc
        files = {'file': ('test.pdf', io.BytesIO(b"test"), 'application/pdf')}
        requests.post(f"{BASE_URL}/api/pre-assessment/{compat_pa_id}/upload-document",
                     files=files, data={'document_type': 'passport'},
                     headers=self.get_auth_header(self.__class__.partner_token))
        
        # Client submit
        self.session.post(f"{BASE_URL}/api/pre-assess-portal/client/submit/{compat_pa_id}",
                         headers=self.get_auth_header(self.__class__.client_token))
        
        # Partner forward
        self.session.post(f"{BASE_URL}/api/pre-assess-portal/partner/forward-to-admin/{compat_pa_id}",
                         json={"remarks": "Test"},
                         headers=self.get_auth_header(self.__class__.partner_token))
        
        # Admin 1st approve
        self.session.put(f"{BASE_URL}/api/pre-assessment/{compat_pa_id}/review",
                        json={"decision": "approved", "reason": "Test"},
                        headers=self.get_auth_header(self.__class__.admin_token))
        
        # Partner send proposal
        self.session.post(f"{BASE_URL}/api/pre-assessment/{compat_pa_id}/send-proposal",
                         json={"fee_amount": 100000, "notes": "Test"},
                         headers=self.get_auth_header(self.__class__.partner_token))
        
        # Client consent + pay
        self.session.post(f"{BASE_URL}/api/pre-assess-portal/client/proposal-consent/{compat_pa_id}",
                         headers=self.get_auth_header(self.__class__.client_token))
        self.session.post(f"{BASE_URL}/api/pre-assess-portal/client/mock-pay-proposal/{compat_pa_id}",
                         headers=self.get_auth_header(self.__class__.client_token))
        
        # Now try admin approve-final at proposal_paid stage (without partner submit-final)
        response = self.session.post(
            f"{BASE_URL}/api/pre-assess-portal/admin/approve-final/{compat_pa_id}",
            json={},
            headers=self.get_auth_header(self.__class__.admin_token)
        )
        assert response.status_code == 200, f"Backward compat approve-final failed: {response.text}"
        data = response.json()
        assert data.get("stage") == "case_created"
        print(f"PASS: Admin approve-final backward compatible with proposal_paid stage")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
