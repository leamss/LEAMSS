"""
Phase A Part 3 Tests - Admin 2nd Approval with Case Manager Assignment
Tests:
1. GET /api/pre-assess-portal/admin/case-managers - admin-only, returns active CMs
2. POST /api/pre-assess-portal/admin/approve-final/{pa_id} - with optional case_manager_id
3. GET /api/pre-assessment/admin/queue - includes proposal_paid stage
4. Full E2E flow from Partner creates PA to Case created with CM assigned
5. Partner preview-magic endpoint validation
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"
CM_EMAIL = "manager@leamss.com"
CM_PASSWORD = "Manager@123"
CM_ID = "67cd3b9e-add6-4056-9107-d26dce979d37"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def partner_token():
    """Get partner auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": PARTNER_EMAIL, "password": PARTNER_PASSWORD})
    assert resp.status_code == 200, f"Partner login failed: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def cm_token():
    """Get case manager auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": CM_EMAIL, "password": CM_PASSWORD})
    assert resp.status_code == 200, f"CM login failed: {resp.text}"
    return resp.json()["token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestAdminCaseManagersEndpoint:
    """Test GET /api/pre-assess-portal/admin/case-managers"""

    def test_admin_can_list_case_managers(self, admin_token):
        """Admin should be able to list active case managers"""
        resp = requests.get(f"{BASE_URL}/api/pre-assess-portal/admin/case-managers", headers=auth_header(admin_token))
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "case_managers" in data
        assert isinstance(data["case_managers"], list)
        # Should have at least the seeded case manager
        if len(data["case_managers"]) > 0:
            cm = data["case_managers"][0]
            assert "id" in cm
            assert "name" in cm
            assert "email" in cm
        print(f"✓ Admin listed {len(data['case_managers'])} case managers")

    def test_partner_cannot_list_case_managers(self, partner_token):
        """Partner should NOT be able to access admin/case-managers"""
        resp = requests.get(f"{BASE_URL}/api/pre-assess-portal/admin/case-managers", headers=auth_header(partner_token))
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print("✓ Partner correctly denied access to case-managers endpoint")

    def test_cm_cannot_list_case_managers(self, cm_token):
        """Case manager should NOT be able to access admin/case-managers"""
        resp = requests.get(f"{BASE_URL}/api/pre-assess-portal/admin/case-managers", headers=auth_header(cm_token))
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print("✓ Case manager correctly denied access to case-managers endpoint")


class TestAdminQueueIncludesProposalPaid:
    """Test GET /api/pre-assessment/admin/queue includes proposal_paid stage"""

    def test_admin_queue_returns_proposal_paid_items(self, admin_token, partner_token):
        """Admin queue should include items at proposal_paid stage"""
        # First create a PA and move it to proposal_paid stage
        unique_email = f"test_queue_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create PA
        create_resp = requests.post(f"{BASE_URL}/api/pre-assessment/create", json={
            "client_name": "Queue Test Client",
            "client_email": unique_email,
            "client_mobile": "+91-9999999999",
            "country": "Canada",
            "service_type": "PR"
        }, headers=auth_header(partner_token))
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        pa_id = create_resp.json()["id"]
        
        # Generate public link
        link_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/generate-public-link", 
            json={"pa_id": pa_id}, headers=auth_header(partner_token))
        assert link_resp.status_code == 200
        token = link_resp.json()["token"]
        
        # Mock pay
        pay_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/public/mock-pay", json={"token": token})
        assert pay_resp.status_code == 200
        magic_link = pay_resp.json()["magic_link"]
        magic_token = magic_link.split("/magic/")[-1]
        
        # Magic login
        login_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/magic-login", json={"token": magic_token})
        assert login_resp.status_code == 200
        client_token = login_resp.json()["token"]
        
        # Upload a document
        files = {"file": ("test.pdf", b"test content", "application/pdf")}
        upload_resp = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/upload-document",
            data={"document_type": "passport"}, files=files, headers=auth_header(client_token))
        assert upload_resp.status_code == 200
        
        # Client submit for review
        submit_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/client/submit/{pa_id}", 
            headers=auth_header(client_token))
        assert submit_resp.status_code == 200
        
        # Partner submit to admin
        submit_admin_resp = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/submit-documents",
            data={"remarks": "Ready"}, headers=auth_header(partner_token))
        assert submit_admin_resp.status_code == 200
        
        # Admin approve (1st approval)
        review_resp = requests.put(f"{BASE_URL}/api/pre-assessment/{pa_id}/review", json={
            "decision": "approved", "reason": "Eligible", "notes": ""
        }, headers=auth_header(admin_token))
        assert review_resp.status_code == 200
        
        # Partner send proposal
        proposal_resp = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/send-proposal", json={
            "fee_amount": 150000, "payment_method": "online", "notes": "Test", "currency": "INR"
        }, headers=auth_header(partner_token))
        assert proposal_resp.status_code == 200
        
        # Client accept proposal
        accept_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/client/accept-proposal/{pa_id}",
            headers=auth_header(client_token))
        assert accept_resp.status_code == 200
        
        # Client mock pay proposal
        pay_proposal_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/client/mock-pay-proposal/{pa_id}",
            headers=auth_header(client_token))
        assert pay_proposal_resp.status_code == 200
        
        # Now check admin queue includes this PA at proposal_paid
        queue_resp = requests.get(f"{BASE_URL}/api/pre-assessment/admin/queue", headers=auth_header(admin_token))
        assert queue_resp.status_code == 200
        queue_items = queue_resp.json()
        
        # Find our PA in the queue
        found = False
        for item in queue_items:
            if item["id"] == pa_id:
                assert item["stage"] == "proposal_paid", f"Expected proposal_paid, got {item['stage']}"
                found = True
                break
        
        assert found, f"PA {pa_id} at proposal_paid stage not found in admin queue"
        print(f"✓ Admin queue includes proposal_paid items (PA {pa_id} found)")


class TestApproveFinalWithCaseManager:
    """Test POST /api/pre-assess-portal/admin/approve-final/{pa_id} with case_manager_id"""

    def test_approve_final_with_valid_cm_id(self, admin_token, partner_token):
        """Admin can approve-final with a valid case_manager_id"""
        unique_email = f"test_cm_assign_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create and progress PA to proposal_paid
        pa_id, client_token = self._create_pa_to_proposal_paid(partner_token, admin_token, unique_email)
        
        # Get case managers to find a valid ID
        cm_resp = requests.get(f"{BASE_URL}/api/pre-assess-portal/admin/case-managers", headers=auth_header(admin_token))
        assert cm_resp.status_code == 200
        cms = cm_resp.json()["case_managers"]
        
        if len(cms) == 0:
            pytest.skip("No case managers available for testing")
        
        cm_id = cms[0]["id"]
        cm_name = cms[0]["name"]
        
        # Approve final with CM assignment
        approve_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/admin/approve-final/{pa_id}",
            json={"case_manager_id": cm_id}, headers=auth_header(admin_token))
        assert approve_resp.status_code == 200, f"Approve final failed: {approve_resp.text}"
        
        data = approve_resp.json()
        assert data["ok"] == True
        assert "case_id" in data
        assert "case_code" in data
        assert data["case_manager_id"] == cm_id
        assert data["case_manager_name"] == cm_name
        assert data["stage"] == "case_created"
        
        print(f"✓ Case {data['case_code']} created with CM {cm_name} assigned")
        
        # Verify case in database via /api/cases/my-cases (as admin)
        cases_resp = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=auth_header(admin_token))
        if cases_resp.status_code == 200:
            cases = cases_resp.json()
            found_case = None
            for c in cases:
                if c.get("id") == data["case_id"]:
                    found_case = c
                    break
            if found_case:
                assert found_case.get("case_manager_id") == cm_id
                assert found_case.get("case_manager_name") == cm_name
                print(f"✓ Case verified in database with case_manager_id={cm_id}")

    def test_approve_final_with_invalid_cm_id(self, admin_token, partner_token):
        """Admin should get 400 when using invalid case_manager_id"""
        unique_email = f"test_invalid_cm_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create and progress PA to proposal_paid
        pa_id, client_token = self._create_pa_to_proposal_paid(partner_token, admin_token, unique_email)
        
        # Try to approve with invalid CM ID
        approve_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/admin/approve-final/{pa_id}",
            json={"case_manager_id": "invalid-uuid-12345"}, headers=auth_header(admin_token))
        assert approve_resp.status_code == 400, f"Expected 400, got {approve_resp.status_code}: {approve_resp.text}"
        print("✓ Invalid case_manager_id correctly returns 400")

    def test_approve_final_without_cm_id(self, admin_token, partner_token):
        """Admin can approve-final without case_manager_id (unassigned)"""
        unique_email = f"test_no_cm_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create and progress PA to proposal_paid
        pa_id, client_token = self._create_pa_to_proposal_paid(partner_token, admin_token, unique_email)
        
        # Approve final without CM
        approve_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/admin/approve-final/{pa_id}",
            json={}, headers=auth_header(admin_token))
        assert approve_resp.status_code == 200, f"Approve final failed: {approve_resp.text}"
        
        data = approve_resp.json()
        assert data["ok"] == True
        assert data["case_manager_id"] is None
        assert data["case_manager_name"] == "Pending assignment"
        print(f"✓ Case {data['case_code']} created without CM (unassigned)")

    def _create_pa_to_proposal_paid(self, partner_token, admin_token, client_email):
        """Helper to create PA and progress to proposal_paid stage"""
        # Create PA
        create_resp = requests.post(f"{BASE_URL}/api/pre-assessment/create", json={
            "client_name": "Test Client",
            "client_email": client_email,
            "client_mobile": "+91-9999999999",
            "country": "Canada",
            "service_type": "PR"
        }, headers=auth_header(partner_token))
        assert create_resp.status_code == 200
        pa_id = create_resp.json()["id"]
        
        # Generate public link
        link_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/generate-public-link", 
            json={"pa_id": pa_id}, headers=auth_header(partner_token))
        token = link_resp.json()["token"]
        
        # Mock pay
        pay_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/public/mock-pay", json={"token": token})
        magic_link = pay_resp.json()["magic_link"]
        magic_token = magic_link.split("/magic/")[-1]
        
        # Magic login
        login_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/magic-login", json={"token": magic_token})
        client_token = login_resp.json()["token"]
        
        # Upload document
        files = {"file": ("test.pdf", b"test content", "application/pdf")}
        requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/upload-document",
            data={"document_type": "passport"}, files=files, headers=auth_header(client_token))
        
        # Client submit
        requests.post(f"{BASE_URL}/api/pre-assess-portal/client/submit/{pa_id}", headers=auth_header(client_token))
        
        # Partner submit to admin
        requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/submit-documents",
            data={"remarks": "Ready"}, headers=auth_header(partner_token))
        
        # Admin approve
        requests.put(f"{BASE_URL}/api/pre-assessment/{pa_id}/review", json={
            "decision": "approved", "reason": "Eligible", "notes": ""
        }, headers=auth_header(admin_token))
        
        # Partner send proposal
        requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/send-proposal", json={
            "fee_amount": 150000, "payment_method": "online", "notes": "Test", "currency": "INR"
        }, headers=auth_header(partner_token))
        
        # Client accept proposal
        requests.post(f"{BASE_URL}/api/pre-assess-portal/client/accept-proposal/{pa_id}",
            headers=auth_header(client_token))
        
        # Client mock pay proposal
        requests.post(f"{BASE_URL}/api/pre-assess-portal/client/mock-pay-proposal/{pa_id}",
            headers=auth_header(client_token))
        
        return pa_id, client_token


class TestPartnerPreviewMagic:
    """Test POST /api/pre-assess-portal/partner/preview-magic/{pa_id}"""

    def test_partner_preview_magic_on_paid_pa(self, partner_token, admin_token):
        """Partner can preview as client on a PA where client has paid"""
        unique_email = f"test_preview_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create PA
        create_resp = requests.post(f"{BASE_URL}/api/pre-assessment/create", json={
            "client_name": "Preview Test",
            "client_email": unique_email,
            "country": "UK",
            "service_type": "Work Visa"
        }, headers=auth_header(partner_token))
        pa_id = create_resp.json()["id"]
        
        # Generate link and mock pay
        link_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/generate-public-link", 
            json={"pa_id": pa_id}, headers=auth_header(partner_token))
        token = link_resp.json()["token"]
        requests.post(f"{BASE_URL}/api/pre-assess-portal/public/mock-pay", json={"token": token})
        
        # Now partner can preview
        preview_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/partner/preview-magic/{pa_id}",
            json={}, headers=auth_header(partner_token))
        assert preview_resp.status_code == 200, f"Preview failed: {preview_resp.text}"
        
        data = preview_resp.json()
        assert "portal_url" in data
        assert "/magic/" in data["portal_url"]
        assert data["expires_in_minutes"] == 30
        print(f"✓ Partner preview magic link generated: {data['portal_url'][:50]}...")

    def test_partner_preview_magic_on_unpaid_pa(self, partner_token):
        """Partner should get 400 when trying to preview unpaid PA"""
        unique_email = f"test_preview_unpaid_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create PA but don't pay
        create_resp = requests.post(f"{BASE_URL}/api/pre-assessment/create", json={
            "client_name": "Unpaid Preview Test",
            "client_email": unique_email,
            "country": "Australia",
            "service_type": "Student Visa"
        }, headers=auth_header(partner_token))
        pa_id = create_resp.json()["id"]
        
        # Try to preview without payment
        preview_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/partner/preview-magic/{pa_id}",
            json={}, headers=auth_header(partner_token))
        assert preview_resp.status_code == 400, f"Expected 400, got {preview_resp.status_code}: {preview_resp.text}"
        assert "not paid" in preview_resp.json().get("detail", "").lower() or "payment" in preview_resp.json().get("detail", "").lower()
        print("✓ Partner correctly denied preview on unpaid PA")


class TestFullE2EFlow:
    """Full E2E flow test from Partner creates PA to Case created with CM assigned"""

    def test_complete_e2e_flow_with_cm_assignment(self, admin_token, partner_token):
        """Complete E2E: Partner creates PA → Client pays → uploads → submits → Admin 1st approves → 
        Partner sends proposal → Client accepts + pays → Admin 2nd approves with CM → Case created"""
        
        unique_email = f"test_e2e_full_{uuid.uuid4().hex[:8]}@example.com"
        
        # Step 1: Partner creates PA
        print("\n--- Step 1: Partner creates PA ---")
        create_resp = requests.post(f"{BASE_URL}/api/pre-assessment/create", json={
            "client_name": "E2E Full Test Client",
            "client_email": unique_email,
            "client_mobile": "+91-8888888888",
            "country": "Canada",
            "service_type": "Express Entry PR",
            "notes": "Full E2E test"
        }, headers=auth_header(partner_token))
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        pa_id = create_resp.json()["id"]
        pa_number = create_resp.json()["pa_number"]
        print(f"✓ PA created: {pa_number} (id: {pa_id})")
        
        # Step 2: Partner generates public link
        print("\n--- Step 2: Partner generates public link ---")
        link_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/generate-public-link", 
            json={"pa_id": pa_id}, headers=auth_header(partner_token))
        assert link_resp.status_code == 200
        share_token = link_resp.json()["token"]
        public_url = link_resp.json()["public_url"]
        print(f"✓ Public link generated: {public_url[:50]}...")
        
        # Step 3: Client mock pays (unauth)
        print("\n--- Step 3: Client mock pays ---")
        pay_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/public/mock-pay", json={"token": share_token})
        assert pay_resp.status_code == 200
        magic_link = pay_resp.json()["magic_link"]
        magic_token = magic_link.split("/magic/")[-1]
        print(f"✓ Payment received, magic link: {magic_link[:50]}...")
        
        # Step 4: Client magic login
        print("\n--- Step 4: Client magic login ---")
        login_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/magic-login", json={"token": magic_token})
        assert login_resp.status_code == 200
        client_token = login_resp.json()["token"]
        client_user = login_resp.json()["user"]
        print(f"✓ Client logged in: {client_user['email']}")
        
        # Step 5: Client uploads document
        print("\n--- Step 5: Client uploads document ---")
        files = {"file": ("passport_scan.pdf", b"PDF content here", "application/pdf")}
        upload_resp = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/upload-document",
            data={"document_type": "passport"}, files=files, headers=auth_header(client_token))
        assert upload_resp.status_code == 200
        print(f"✓ Document uploaded: {upload_resp.json()['file_name']}")
        
        # Step 6: Client submits for review
        print("\n--- Step 6: Client submits for review ---")
        submit_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/client/submit/{pa_id}", 
            headers=auth_header(client_token))
        assert submit_resp.status_code == 200
        assert submit_resp.json()["stage"] == "documents_submitted"
        print("✓ Client submitted for review")
        
        # Step 7: Partner submits to admin
        print("\n--- Step 7: Partner submits to admin ---")
        submit_admin_resp = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/submit-documents",
            data={"remarks": "Client ready for eligibility check"}, headers=auth_header(partner_token))
        assert submit_admin_resp.status_code == 200
        print("✓ Partner submitted to admin")
        
        # Step 8: Admin 1st approval
        print("\n--- Step 8: Admin 1st approval ---")
        review_resp = requests.put(f"{BASE_URL}/api/pre-assessment/{pa_id}/review", json={
            "decision": "approved",
            "reason": "Client meets all eligibility criteria for Express Entry",
            "notes": "Strong profile"
        }, headers=auth_header(admin_token))
        assert review_resp.status_code == 200
        assert review_resp.json()["stage"] == "approved"
        print("✓ Admin approved (1st approval)")
        
        # Step 9: Partner sends proposal
        print("\n--- Step 9: Partner sends proposal ---")
        proposal_resp = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/send-proposal", json={
            "fee_amount": 150000,
            "payment_method": "online",
            "notes": "Canada Express Entry PR package",
            "currency": "INR"
        }, headers=auth_header(partner_token))
        assert proposal_resp.status_code == 200
        sale_id = proposal_resp.json()["sale_id"]
        print(f"✓ Proposal sent, sale_id: {sale_id}")
        
        # Step 10: Client accepts proposal
        print("\n--- Step 10: Client accepts proposal ---")
        accept_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/client/accept-proposal/{pa_id}",
            headers=auth_header(client_token))
        assert accept_resp.status_code == 200
        assert accept_resp.json()["proposal_status"] == "accepted"
        print("✓ Client accepted proposal")
        
        # Step 11: Client pays main fee (mock)
        print("\n--- Step 11: Client pays main fee ---")
        pay_proposal_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/client/mock-pay-proposal/{pa_id}",
            headers=auth_header(client_token))
        assert pay_proposal_resp.status_code == 200
        assert pay_proposal_resp.json()["stage"] == "proposal_paid"
        print("✓ Client paid main fee (₹150,000)")
        
        # Step 12: Admin 2nd approval with CM assignment
        print("\n--- Step 12: Admin 2nd approval with CM assignment ---")
        
        # Get available case managers
        cm_resp = requests.get(f"{BASE_URL}/api/pre-assess-portal/admin/case-managers", headers=auth_header(admin_token))
        assert cm_resp.status_code == 200
        cms = cm_resp.json()["case_managers"]
        
        cm_id = cms[0]["id"] if cms else None
        cm_name = cms[0]["name"] if cms else "Pending assignment"
        
        approve_payload = {"case_manager_id": cm_id} if cm_id else {}
        approve_resp = requests.post(f"{BASE_URL}/api/pre-assess-portal/admin/approve-final/{pa_id}",
            json=approve_payload, headers=auth_header(admin_token))
        assert approve_resp.status_code == 200
        
        result = approve_resp.json()
        assert result["ok"] == True
        assert "case_id" in result
        assert "case_code" in result
        case_id = result["case_id"]
        case_code = result["case_code"]
        print(f"✓ Case created: {case_code}")
        print(f"  - case_id: {case_id}")
        print(f"  - case_manager_id: {result['case_manager_id']}")
        print(f"  - case_manager_name: {result['case_manager_name']}")
        
        # Step 13: Verify case in database
        print("\n--- Step 13: Verify case in database ---")
        cases_resp = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=auth_header(admin_token))
        if cases_resp.status_code == 200:
            cases = cases_resp.json()
            found_case = None
            for c in cases:
                if c.get("id") == case_id:
                    found_case = c
                    break
            
            if found_case:
                print(f"✓ Case verified in database:")
                print(f"  - case_id: {found_case.get('case_id')}")
                print(f"  - client_name: {found_case.get('client_name')}")
                print(f"  - case_manager_id: {found_case.get('case_manager_id')}")
                print(f"  - case_manager_name: {found_case.get('case_manager_name')}")
                print(f"  - status: {found_case.get('status')}")
                
                if cm_id:
                    assert found_case.get("case_manager_id") == cm_id
                    assert found_case.get("case_manager_name") == cm_name
        
        print("\n" + "="*60)
        print("✓ FULL E2E FLOW COMPLETED SUCCESSFULLY!")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
