"""
Iteration 83 - Phase B + C + D Backend Tests
=============================================
Tests for:
- Phase B: Proposal PDF, Invoice PDF, E-Sign, Send Invoice
- Phase C: Payment History Timeline, Milestones CRUD
- Phase D: Drop-off Recovery, Smart Doc Checklist, Risk Prediction
- Enhanced consent flow with reference_id
"""
import pytest
import requests
import os
import uuid
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASS = "Partner@123"
MANAGER_EMAIL = "manager@leamss.com"
MANAGER_PASS = "Manager@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASS = "Client@123"


class TestTokens:
    """Store tokens for reuse"""
    admin_token = None
    partner_token = None
    manager_token = None
    client_token = None
    test_pa_id = None
    test_case_id = None
    test_milestone_id = None


def get_auth(token):
    return {"Authorization": f"Bearer {token}"}


# ==================== AUTH TESTS ====================
class TestAuth:
    """Authentication tests"""
    
    def test_01_admin_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert r.status_code == 200, f"Admin login failed: {r.text}"
        TestTokens.admin_token = r.json().get("token")
        assert TestTokens.admin_token, "No admin token returned"
        print("PASS: Admin login successful")
    
    def test_02_partner_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": PARTNER_EMAIL, "password": PARTNER_PASS})
        assert r.status_code == 200, f"Partner login failed: {r.text}"
        TestTokens.partner_token = r.json().get("token")
        assert TestTokens.partner_token, "No partner token returned"
        print("PASS: Partner login successful")
    
    def test_03_manager_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": MANAGER_EMAIL, "password": MANAGER_PASS})
        assert r.status_code == 200, f"Manager login failed: {r.text}"
        TestTokens.manager_token = r.json().get("token")
        assert TestTokens.manager_token, "No manager token returned"
        print("PASS: Manager login successful")
    
    def test_04_client_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASS})
        assert r.status_code == 200, f"Client login failed: {r.text}"
        TestTokens.client_token = r.json().get("token")
        assert TestTokens.client_token, "No client token returned"
        print("PASS: Client login successful")


# ==================== SETUP: CREATE TEST PA ====================
class TestSetupPA:
    """Create a test PA and drive it through stages for testing"""
    
    def test_05_partner_create_pa(self):
        """Partner creates a new PA for testing"""
        r = requests.post(f"{BASE_URL}/api/pre-assessment/create", json={
            "client_name": "TEST_Iteration83_Client",
            "client_email": f"test_iter83_{uuid.uuid4().hex[:6]}@example.com",
            "client_mobile": "+91-9876543210",
            "country": "Canada",
            "service_type": "Express Entry PR",
            "client_age": 30,
            "education": "Master's Degree",
            "work_experience": "6 years IT"
        }, headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Create PA failed: {r.text}"
        data = r.json()
        TestTokens.test_pa_id = data.get("id")
        assert TestTokens.test_pa_id, "No PA ID returned"
        print(f"PASS: Created PA {data.get('pa_number')}")
    
    def test_06_send_payment_link(self):
        """Partner sends payment link"""
        r = requests.post(f"{BASE_URL}/api/pre-assess-portal/generate-public-link",
            json={"pa_id": TestTokens.test_pa_id},
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Send payment link failed: {r.text}"
        print("PASS: Payment link generated")
    
    def test_07_mock_payment(self):
        """Get share token and mock payment"""
        # Get PA to find share token
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200
        pas = r.json()
        pa = next((p for p in pas if p["id"] == TestTokens.test_pa_id), None)
        assert pa, "PA not found"
        token = pa.get("share_token")
        assert token, "No share token"
        
        # Mock payment
        r = requests.post(f"{BASE_URL}/api/pre-assess-portal/public/mock-pay",
            json={"token": token})
        assert r.status_code == 200, f"Mock payment failed: {r.text}"
        print("PASS: Mock payment successful")
    
    def test_08_upload_document(self):
        """Upload a test document"""
        files = {"file": ("test_passport.pdf", b"PDF content for testing", "application/pdf")}
        data = {"document_type": "passport"}
        r = requests.post(f"{BASE_URL}/api/pre-assessment/{TestTokens.test_pa_id}/upload-document",
            files=files, data=data, headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Upload failed: {r.text}"
        print("PASS: Document uploaded")
    
    def test_09_client_submit_for_review(self):
        """Client submits for review"""
        # Get client token for this PA
        r = requests.post(f"{BASE_URL}/api/pre-assess-portal/partner/preview-magic/{TestTokens.test_pa_id}",
            headers=get_auth(TestTokens.partner_token))
        if r.status_code == 200:
            magic_token = r.json().get("portal_url", "").split("/magic/")[-1]
            if magic_token:
                r2 = requests.post(f"{BASE_URL}/api/pre-assess-portal/magic-login",
                    json={"token": magic_token})
                if r2.status_code == 200:
                    client_token = r2.json().get("token")
                    r3 = requests.post(f"{BASE_URL}/api/pre-assess-portal/client/submit/{TestTokens.test_pa_id}",
                        headers=get_auth(client_token))
                    assert r3.status_code == 200, f"Submit failed: {r3.text}"
                    print("PASS: Client submitted for review")
                    return
        # Fallback - use partner to forward
        print("INFO: Using partner forward flow")
    
    def test_10_partner_forward_to_admin(self):
        """Partner forwards to admin"""
        r = requests.post(f"{BASE_URL}/api/pre-assess-portal/partner/forward-to-admin/{TestTokens.test_pa_id}",
            json={"remarks": "Test iteration 83"},
            headers=get_auth(TestTokens.partner_token))
        # May fail if already forwarded
        if r.status_code == 200:
            print("PASS: Forwarded to admin")
        else:
            print(f"INFO: Forward status {r.status_code} - may already be forwarded")
    
    def test_11_admin_approve(self):
        """Admin approves PA"""
        r = requests.post(f"{BASE_URL}/api/pre-assessment/{TestTokens.test_pa_id}/admin/review",
            json={"decision": "approved", "reason": "Test approval"},
            headers=get_auth(TestTokens.admin_token))
        if r.status_code == 200:
            print("PASS: Admin approved")
        else:
            print(f"INFO: Admin review status {r.status_code}")
    
    def test_12_partner_send_proposal(self):
        """Partner sends proposal"""
        r = requests.post(f"{BASE_URL}/api/pre-assessment/{TestTokens.test_pa_id}/send-proposal",
            json={
                "fee_amount": 150000,
                "payment_method": "online",
                "notes": "Test proposal for iteration 83",
                "currency": "INR",
                "promo_code": None,
                "additional_discount": 5000,
                "upsell_bundle_ids": [],
                "ai_proposal_text": "This is a test AI-generated proposal text for Canada Express Entry."
            },
            headers=get_auth(TestTokens.partner_token))
        if r.status_code == 200:
            print("PASS: Proposal sent")
        else:
            print(f"INFO: Send proposal status {r.status_code} - {r.text}")


# ==================== PHASE B: PROPOSAL DOCS ====================
class TestProposalDocs:
    """Phase B: Proposal PDF, Invoice PDF, E-Sign, Send Invoice"""
    
    def test_13_proposal_pdf_partner(self):
        """GET /api/proposal-docs/{pa_id}/proposal.pdf - Partner access"""
        r = requests.get(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/proposal.pdf",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Proposal PDF failed: {r.status_code}"
        assert r.headers.get("content-type") == "application/pdf", "Not a PDF"
        assert len(r.content) > 5000, f"PDF too small: {len(r.content)} bytes"
        print(f"PASS: Proposal PDF returned ({len(r.content)} bytes)")
    
    def test_14_proposal_pdf_admin(self):
        """GET /api/proposal-docs/{pa_id}/proposal.pdf - Admin access"""
        r = requests.get(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/proposal.pdf",
            headers=get_auth(TestTokens.admin_token))
        assert r.status_code == 200, f"Admin proposal PDF failed: {r.status_code}"
        print("PASS: Admin can access proposal PDF")
    
    def test_15_proposal_pdf_case_manager(self):
        """GET /api/proposal-docs/{pa_id}/proposal.pdf - Case Manager access"""
        r = requests.get(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/proposal.pdf",
            headers=get_auth(TestTokens.manager_token))
        assert r.status_code == 200, f"CM proposal PDF failed: {r.status_code}"
        print("PASS: Case Manager can access proposal PDF")
    
    def test_16_proposal_pdf_invalid_pa(self):
        """GET /api/proposal-docs/{pa_id}/proposal.pdf - 404 for invalid PA"""
        r = requests.get(f"{BASE_URL}/api/proposal-docs/invalid-pa-id-12345/proposal.pdf",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        print("PASS: 404 for invalid PA ID")
    
    def test_17_invoice_pdf_partner(self):
        """GET /api/proposal-docs/{pa_id}/invoice.pdf - Partner access"""
        r = requests.get(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/invoice.pdf",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Invoice PDF failed: {r.status_code}"
        assert r.headers.get("content-type") == "application/pdf", "Not a PDF"
        print(f"PASS: Invoice PDF returned ({len(r.content)} bytes)")
    
    def test_18_send_invoice_partner(self):
        """POST /api/proposal-docs/{pa_id}/send-invoice - Partner only"""
        r = requests.post(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/send-invoice",
            json={"channel": "email", "message": "Test invoice"},
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Send invoice failed: {r.text}"
        data = r.json()
        assert data.get("ok") == True
        assert "reference_id" in data
        assert data.get("mode") == "mock"
        print(f"PASS: Invoice sent, ref={data.get('reference_id')}")
    
    def test_19_send_invoice_admin(self):
        """POST /api/proposal-docs/{pa_id}/send-invoice - Admin can also send"""
        r = requests.post(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/send-invoice",
            json={"channel": "email"},
            headers=get_auth(TestTokens.admin_token))
        assert r.status_code == 200, f"Admin send invoice failed: {r.text}"
        print("PASS: Admin can send invoice")
    
    def test_20_list_invoices(self):
        """GET /api/proposal-docs/{pa_id}/invoices - List sent invoices"""
        r = requests.get(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/invoices",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"List invoices failed: {r.text}"
        invoices = r.json()
        assert isinstance(invoices, list)
        assert len(invoices) >= 2, "Should have at least 2 invoices"
        print(f"PASS: Listed {len(invoices)} invoices")
    
    def test_21_esign_requires_client(self):
        """POST /api/proposal-docs/{pa_id}/esign - 403 for non-client"""
        # Create a minimal valid base64 PNG
        png_data = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100).decode()
        r = requests.post(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/esign",
            json={
                "signature_data_url": f"data:image/png;base64,{png_data}",
                "typed_name": "Test Partner",
                "consent_text": "I agree"
            },
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 403, f"Expected 403 for partner, got {r.status_code}"
        print("PASS: E-sign requires client role (403 for partner)")
    
    def test_22_esign_invalid_data_url(self):
        """POST /api/proposal-docs/{pa_id}/esign - 400 for invalid data URL"""
        # First get a client token for this PA
        r = requests.post(f"{BASE_URL}/api/pre-assess-portal/partner/preview-magic/{TestTokens.test_pa_id}",
            headers=get_auth(TestTokens.partner_token))
        if r.status_code != 200:
            pytest.skip("Cannot get client token for this PA")
        
        magic_token = r.json().get("portal_url", "").split("/magic/")[-1]
        r2 = requests.post(f"{BASE_URL}/api/pre-assess-portal/magic-login",
            json={"token": magic_token})
        if r2.status_code != 200:
            pytest.skip("Magic login failed")
        
        client_token = r2.json().get("token")
        
        r3 = requests.post(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/esign",
            json={
                "signature_data_url": "invalid-not-a-data-url",
                "typed_name": "Test Client"
            },
            headers=get_auth(client_token))
        assert r3.status_code == 400, f"Expected 400 for invalid data URL, got {r3.status_code}"
        print("PASS: 400 for invalid signature data URL")
    
    def test_23_get_esign_not_signed(self):
        """GET /api/proposal-docs/{pa_id}/esign - Returns signed:false if not signed"""
        r = requests.get(f"{BASE_URL}/api/proposal-docs/{TestTokens.test_pa_id}/esign",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Get esign failed: {r.text}"
        data = r.json()
        # May be signed or not depending on test order
        assert "signed" in data
        print(f"PASS: Get esign returned signed={data.get('signed')}")


# ==================== CONSENT FLOW WITH REFERENCE ID ====================
class TestConsentFlow:
    """Enhanced consent flow with reference_id"""
    
    def test_24_consent_requires_proposal_sent_stage(self):
        """POST /api/pre-assess-portal/client/proposal-consent - requires proposal_sent stage"""
        # This PA may not be at proposal_sent stage
        r = requests.post(f"{BASE_URL}/api/pre-assess-portal/client/proposal-consent/{TestTokens.test_pa_id}",
            headers=get_auth(TestTokens.client_token))
        # Will fail with 404 (not client's PA) or 400 (wrong stage)
        assert r.status_code in [400, 403, 404], f"Expected 400/403/404, got {r.status_code}"
        print(f"PASS: Consent endpoint validates stage/auth ({r.status_code})")
    
    def test_25_get_consent_summary(self):
        """GET /api/pre-assess-portal/client/consent-summary/{pa_id}"""
        r = requests.get(f"{BASE_URL}/api/pre-assess-portal/client/consent-summary/{TestTokens.test_pa_id}",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Get consent summary failed: {r.text}"
        data = r.json()
        assert "exists" in data
        print(f"PASS: Consent summary exists={data.get('exists')}")


# ==================== PHASE C: PAYMENT HISTORY ====================
class TestPaymentHistory:
    """Phase C: Payment History Timeline"""
    
    def test_26_payment_history_pa(self):
        """GET /api/payment-history/pa/{pa_id}"""
        r = requests.get(f"{BASE_URL}/api/payment-history/pa/{TestTokens.test_pa_id}",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Payment history failed: {r.text}"
        data = r.json()
        assert "events" in data
        assert "totals" in data
        assert "received" in data["totals"]
        assert "pending" in data["totals"]
        print(f"PASS: Payment history returned {len(data['events'])} events, received={data['totals']['received']}")
    
    def test_27_payment_history_pa_admin(self):
        """GET /api/payment-history/pa/{pa_id} - Admin access"""
        r = requests.get(f"{BASE_URL}/api/payment-history/pa/{TestTokens.test_pa_id}",
            headers=get_auth(TestTokens.admin_token))
        assert r.status_code == 200, f"Admin payment history failed: {r.text}"
        print("PASS: Admin can access payment history")
    
    def test_28_payment_history_invalid_pa(self):
        """GET /api/payment-history/pa/{pa_id} - 404 for invalid PA"""
        r = requests.get(f"{BASE_URL}/api/payment-history/pa/invalid-pa-12345",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        print("PASS: 404 for invalid PA in payment history")


# ==================== PHASE C: MILESTONES ====================
class TestMilestones:
    """Phase C: Milestone Payments CRUD"""
    
    def test_29_find_or_create_case(self):
        """Find an existing case or note that we need one"""
        r = requests.get(f"{BASE_URL}/api/cases", headers=get_auth(TestTokens.admin_token))
        assert r.status_code == 200, f"Get cases failed: {r.text}"
        cases = r.json()
        if cases and len(cases) > 0:
            TestTokens.test_case_id = cases[0].get("id")
            print(f"PASS: Found existing case {cases[0].get('case_id')}")
        else:
            print("INFO: No cases found - milestone tests will be skipped")
    
    def test_30_create_milestone(self):
        """POST /api/milestones/case/{case_id}/create"""
        if not TestTokens.test_case_id:
            pytest.skip("No case available for milestone tests")
        
        r = requests.post(f"{BASE_URL}/api/milestones/case/{TestTokens.test_case_id}/create",
            json={
                "title": "TEST_Iteration83_Milestone",
                "amount": 25000,
                "description": "Test milestone for iteration 83",
                "due_date": "2026-02-15"
            },
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Create milestone failed: {r.text}"
        data = r.json()
        TestTokens.test_milestone_id = data.get("id")
        assert TestTokens.test_milestone_id
        assert data.get("title") == "TEST_Iteration83_Milestone"
        assert data.get("amount") == 25000
        assert data.get("status") == "pending"
        print(f"PASS: Created milestone {TestTokens.test_milestone_id}")
    
    def test_31_create_milestone_invalid_amount(self):
        """POST /api/milestones/case/{case_id}/create - Amount must be > 0"""
        if not TestTokens.test_case_id:
            pytest.skip("No case available")
        
        r = requests.post(f"{BASE_URL}/api/milestones/case/{TestTokens.test_case_id}/create",
            json={"title": "Invalid", "amount": 0},
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 400, f"Expected 400 for zero amount, got {r.status_code}"
        print("PASS: 400 for amount <= 0")
    
    def test_32_list_milestones(self):
        """GET /api/milestones/case/{case_id}"""
        if not TestTokens.test_case_id:
            pytest.skip("No case available")
        
        r = requests.get(f"{BASE_URL}/api/milestones/case/{TestTokens.test_case_id}",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"List milestones failed: {r.text}"
        milestones = r.json()
        assert isinstance(milestones, list)
        print(f"PASS: Listed {len(milestones)} milestones")
    
    def test_33_mark_milestone_paid(self):
        """POST /api/milestones/{mid}/mark-paid - Partner/Admin manual mark"""
        if not TestTokens.test_milestone_id:
            pytest.skip("No milestone available")
        
        r = requests.post(f"{BASE_URL}/api/milestones/{TestTokens.test_milestone_id}/mark-paid",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Mark paid failed: {r.text}"
        assert r.json().get("ok") == True
        print("PASS: Milestone marked as paid")
    
    def test_34_delete_milestone(self):
        """DELETE /api/milestones/{mid} - Partner/Admin only"""
        if not TestTokens.test_case_id:
            pytest.skip("No case available")
        
        # Create a new milestone to delete
        r = requests.post(f"{BASE_URL}/api/milestones/case/{TestTokens.test_case_id}/create",
            json={"title": "TEST_ToDelete", "amount": 1000},
            headers=get_auth(TestTokens.partner_token))
        if r.status_code != 200:
            pytest.skip("Could not create milestone to delete")
        
        mid = r.json().get("id")
        r2 = requests.delete(f"{BASE_URL}/api/milestones/{mid}",
            headers=get_auth(TestTokens.partner_token))
        assert r2.status_code == 200, f"Delete failed: {r2.text}"
        print("PASS: Milestone deleted")
    
    def test_35_payment_history_case(self):
        """GET /api/payment-history/case/{case_id}"""
        if not TestTokens.test_case_id:
            pytest.skip("No case available")
        
        r = requests.get(f"{BASE_URL}/api/payment-history/case/{TestTokens.test_case_id}",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Case payment history failed: {r.text}"
        data = r.json()
        assert "events" in data
        assert "totals" in data
        print(f"PASS: Case payment history returned {len(data['events'])} events")


# ==================== PHASE D: INTELLIGENCE ====================
class TestIntelligence:
    """Phase D: Drop-off Recovery, Smart Checklist, Risk Prediction"""
    
    def test_36_dropoff_leads_partner(self):
        """GET /api/intelligence/dropoff-leads - Partner sees own"""
        r = requests.get(f"{BASE_URL}/api/intelligence/dropoff-leads",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Dropoff leads failed: {r.text}"
        data = r.json()
        assert "count" in data
        assert "items" in data
        assert isinstance(data["items"], list)
        print(f"PASS: Partner dropoff leads returned {data['count']} items")
    
    def test_37_dropoff_leads_admin(self):
        """GET /api/intelligence/dropoff-leads - Admin sees all"""
        r = requests.get(f"{BASE_URL}/api/intelligence/dropoff-leads",
            headers=get_auth(TestTokens.admin_token))
        assert r.status_code == 200, f"Admin dropoff leads failed: {r.text}"
        data = r.json()
        print(f"PASS: Admin dropoff leads returned {data['count']} items")
    
    def test_38_dropoff_leads_client_forbidden(self):
        """GET /api/intelligence/dropoff-leads - 403 for client"""
        r = requests.get(f"{BASE_URL}/api/intelligence/dropoff-leads",
            headers=get_auth(TestTokens.client_token))
        assert r.status_code == 403, f"Expected 403 for client, got {r.status_code}"
        print("PASS: 403 for client on dropoff leads")
    
    def test_39_nudge_lead(self):
        """POST /api/intelligence/nudge/{pa_id}"""
        r = requests.post(f"{BASE_URL}/api/intelligence/nudge/{TestTokens.test_pa_id}",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Nudge failed: {r.text}"
        data = r.json()
        assert data.get("ok") == True
        assert data.get("mode") == "mock"
        assert "nudge" in data
        print("PASS: Nudge sent (mock)")
    
    def test_40_nudge_invalid_pa(self):
        """POST /api/intelligence/nudge/{pa_id} - 404 for invalid PA"""
        r = requests.post(f"{BASE_URL}/api/intelligence/nudge/invalid-pa-12345",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        print("PASS: 404 for invalid PA nudge")
    
    def test_41_smart_checklist(self):
        """GET /api/intelligence/checklist/{pa_id}"""
        r = requests.get(f"{BASE_URL}/api/intelligence/checklist/{TestTokens.test_pa_id}",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Checklist failed: {r.text}"
        data = r.json()
        assert "template" in data
        assert "items" in data
        assert "stats" in data
        assert "completion_pct" in data["stats"]
        # Should be canada_express_entry template
        assert data["template"] == "canada_express_entry", f"Expected canada_express_entry, got {data['template']}"
        print(f"PASS: Smart checklist returned {len(data['items'])} items, {data['stats']['completion_pct']}% complete")
    
    def test_42_risk_score(self):
        """GET /api/intelligence/risk/{pa_id}"""
        r = requests.get(f"{BASE_URL}/api/intelligence/risk/{TestTokens.test_pa_id}",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Risk score failed: {r.text}"
        data = r.json()
        assert "score" in data
        assert "label" in data
        assert "color" in data
        assert "factors" in data
        assert 0 <= data["score"] <= 100
        assert data["color"] in ["green", "amber", "red"]
        print(f"PASS: Risk score={data['score']}, label={data['label']}, color={data['color']}")
    
    def test_43_risk_score_invalid_pa(self):
        """GET /api/intelligence/risk/{pa_id} - 404 for invalid PA"""
        r = requests.get(f"{BASE_URL}/api/intelligence/risk/invalid-pa-12345",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        print("PASS: 404 for invalid PA risk score")


# ==================== REGRESSION: PHASE A ENDPOINTS ====================
class TestRegressionPhaseA:
    """Verify Phase A endpoints still work"""
    
    def test_44_pre_assessment_create(self):
        """POST /api/pre-assessment/create still works"""
        r = requests.post(f"{BASE_URL}/api/pre-assessment/create", json={
            "client_name": "TEST_Regression_Client",
            "client_email": f"test_reg_{uuid.uuid4().hex[:6]}@example.com",
            "country": "Australia",
            "service_type": "Skilled Migration"
        }, headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Create PA failed: {r.text}"
        print("PASS: Regression - pre-assessment/create works")
    
    def test_45_my_assessments(self):
        """GET /api/pre-assessment/my-assessments still works"""
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"My assessments failed: {r.text}"
        print(f"PASS: Regression - my-assessments returns {len(r.json())} items")
    
    def test_46_stats_overview(self):
        """GET /api/pre-assessment/stats/overview still works"""
        r = requests.get(f"{BASE_URL}/api/pre-assessment/stats/overview",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Stats overview failed: {r.text}"
        print("PASS: Regression - stats/overview works")
    
    def test_47_admin_queue(self):
        """GET /api/pre-assessment/admin/queue still works"""
        r = requests.get(f"{BASE_URL}/api/pre-assessment/admin/queue",
            headers=get_auth(TestTokens.admin_token))
        assert r.status_code == 200, f"Admin queue failed: {r.text}"
        print(f"PASS: Regression - admin/queue returns {len(r.json())} items")
    
    def test_48_products_endpoint(self):
        """GET /api/products still works"""
        r = requests.get(f"{BASE_URL}/api/products",
            headers=get_auth(TestTokens.partner_token))
        assert r.status_code == 200, f"Products failed: {r.text}"
        print(f"PASS: Regression - products returns {len(r.json())} items")
    
    def test_49_health_check(self):
        """GET /api/health still works"""
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        data = r.json()
        assert data.get("status") == "healthy"
        print("PASS: Regression - health check works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
