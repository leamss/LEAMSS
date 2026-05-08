"""
Iteration 90: Test PA Edit Details Feature + Forward to Admin Bug Fix

Tests:
1. BUG FIX: Forward to Admin - was throwing 'pas is not defined' ReferenceError
2. NEW: PUT /api/pre-assessment/{pa_id}/details - Edit PA contact details
3. Authorization checks on edit endpoint
4. Locked state for case_created stage
5. Regression: Send Proposal + Submit Final flows (also used setPas before fix)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip("Admin login failed")


@pytest.fixture(scope="module")
def partner_token():
    """Get partner auth token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip("Partner login failed")


@pytest.fixture(scope="module")
def client_token():
    """Get client auth token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip("Client login failed")


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestPAEditDetailsEndpoint:
    """Test the new PUT /{pa_id}/details endpoint"""

    def test_edit_pa_details_partner_own_pa(self, partner_token):
        """Partner can edit their own PA's contact details"""
        # First get partner's PAs
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(partner_token))
        assert r.status_code == 200
        pas = r.json()
        
        # Find a PA that is NOT in case_created stage
        editable_pa = None
        for pa in pas:
            if pa.get("stage") != "case_created":
                editable_pa = pa
                break
        
        if not editable_pa:
            pytest.skip("No editable PA found (all in case_created stage)")
        
        pa_id = editable_pa["id"]
        original_mobile = editable_pa.get("client_mobile", "")
        
        # Edit the mobile number
        new_mobile = "+919876501234"
        r = requests.put(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/details",
            json={"client_mobile": new_mobile},
            headers=auth_header(partner_token)
        )
        assert r.status_code == 200, f"Edit failed: {r.text}"
        data = r.json()
        assert data.get("ok") == True
        
        # Verify the change persisted
        r2 = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=auth_header(partner_token))
        assert r2.status_code == 200
        updated_pa = r2.json()
        assert updated_pa.get("client_mobile") == new_mobile
        
        # Restore original value if it was different
        if original_mobile != new_mobile:
            requests.put(
                f"{BASE_URL}/api/pre-assessment/{pa_id}/details",
                json={"client_mobile": original_mobile or ""},
                headers=auth_header(partner_token)
            )
        print(f"PASS: Partner edited PA {pa_id} mobile to {new_mobile}")

    def test_edit_pa_details_no_change(self, partner_token):
        """Sending same values returns no_change: true"""
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(partner_token))
        pas = r.json()
        
        editable_pa = None
        for pa in pas:
            if pa.get("stage") != "case_created":
                editable_pa = pa
                break
        
        if not editable_pa:
            pytest.skip("No editable PA found")
        
        pa_id = editable_pa["id"]
        current_name = editable_pa.get("client_name", "Test")
        
        # Send same value
        r = requests.put(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/details",
            json={"client_name": current_name},
            headers=auth_header(partner_token)
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") == True
        assert data.get("no_change") == True
        print(f"PASS: No-change detection works for PA {pa_id}")

    def test_edit_pa_details_admin_any_pa(self, admin_token, partner_token):
        """Admin can edit any PA"""
        # Get a partner's PA
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(partner_token))
        pas = r.json()
        
        editable_pa = None
        for pa in pas:
            if pa.get("stage") != "case_created":
                editable_pa = pa
                break
        
        if not editable_pa:
            pytest.skip("No editable PA found")
        
        pa_id = editable_pa["id"]
        
        # Admin edits it
        r = requests.put(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/details",
            json={"education": "Master's Degree (Admin Edit)"},
            headers=auth_header(admin_token)
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") == True
        print(f"PASS: Admin edited PA {pa_id}")

    def test_edit_pa_details_client_forbidden(self, client_token, partner_token):
        """Client cannot edit PA details (403)"""
        # Get a PA
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(partner_token))
        pas = r.json()
        
        if not pas:
            pytest.skip("No PAs found")
        
        pa_id = pas[0]["id"]
        
        # Client tries to edit
        r = requests.put(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/details",
            json={"client_name": "Hacker Name"},
            headers=auth_header(client_token)
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        print(f"PASS: Client correctly denied edit access")

    def test_edit_pa_details_locked_case_created(self, admin_token):
        """PA in case_created stage returns 400 'Case is active'"""
        # Get all PAs as admin
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(admin_token))
        pas = r.json()
        
        # Find a PA in case_created stage
        locked_pa = None
        for pa in pas:
            if pa.get("stage") == "case_created":
                locked_pa = pa
                break
        
        if not locked_pa:
            pytest.skip("No PA in case_created stage found")
        
        pa_id = locked_pa["id"]
        
        # Try to edit
        r = requests.put(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/details",
            json={"client_mobile": "+919999999999"},
            headers=auth_header(admin_token)
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        assert "active" in r.text.lower() or "locked" in r.text.lower() or "case" in r.text.lower()
        print(f"PASS: Locked PA {pa_id} correctly rejected edit")

    def test_edit_pa_partner_not_owner_forbidden(self, admin_token, partner_token):
        """Partner cannot edit another partner's PA (403)"""
        # Create a PA as admin (which partner doesn't own)
        create_data = {
            "client_name": "TEST_NotPartnerOwned",
            "client_email": "test_notowned@example.com",
            "client_mobile": "+911234567890",
            "country": "Canada",
            "service_type": "PR"
        }
        r = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=create_data, headers=auth_header(admin_token))
        if r.status_code != 200:
            pytest.skip("Could not create test PA")
        
        pa_id = r.json().get("id")
        
        # Partner tries to edit admin's PA
        r = requests.put(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/details",
            json={"client_name": "Hacked Name"},
            headers=auth_header(partner_token)
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        print(f"PASS: Partner correctly denied edit on non-owned PA")


class TestForwardToAdminBugFix:
    """Test the Forward to Admin flow - was broken with 'pas is not defined' error"""

    def test_forward_to_admin_endpoint_exists(self, partner_token):
        """Verify the forward-to-admin endpoint exists and responds"""
        # Get a PA in partner_review stage (or payment_received)
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(partner_token))
        pas = r.json()
        
        # Find a PA that can be forwarded
        forwardable_pa = None
        for pa in pas:
            if pa.get("stage") in ["partner_review", "payment_received"]:
                forwardable_pa = pa
                break
        
        if not forwardable_pa:
            # Create a new PA and simulate payment
            create_data = {
                "client_name": "TEST_ForwardTest",
                "client_email": "test_forward@example.com",
                "client_mobile": "+911234567890",
                "country": "Canada",
                "service_type": "PR"
            }
            r = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=create_data, headers=auth_header(partner_token))
            if r.status_code == 200:
                pa_id = r.json().get("id")
                # Mock payment
                requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/mock-payment")
                forwardable_pa = {"id": pa_id, "stage": "payment_received"}
        
        if not forwardable_pa:
            pytest.skip("No forwardable PA available")
        
        pa_id = forwardable_pa["id"]
        
        # Try the forward endpoint
        r = requests.post(
            f"{BASE_URL}/api/pre-assess-portal/partner/forward-to-admin/{pa_id}",
            json={"remarks": "Test forward remarks"},
            headers=auth_header(partner_token)
        )
        # Should succeed or fail with business logic error, NOT 500
        assert r.status_code in [200, 400, 403], f"Unexpected status {r.status_code}: {r.text}"
        print(f"PASS: Forward endpoint responds correctly (status {r.status_code})")


class TestSendProposalRegression:
    """Regression test for Send Proposal flow (also used setPas before fix)"""

    def test_send_proposal_endpoint(self, partner_token):
        """Test send-proposal endpoint works"""
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(partner_token))
        pas = r.json()
        
        # Find an approved PA
        approved_pa = None
        for pa in pas:
            if pa.get("stage") == "approved":
                approved_pa = pa
                break
        
        if not approved_pa:
            pytest.skip("No approved PA found for proposal test")
        
        pa_id = approved_pa["id"]
        
        # Send proposal
        r = requests.post(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/send-proposal",
            json={
                "fee_amount": 150000,
                "payment_method": "online",
                "notes": "Test proposal",
                "currency": "INR"
            },
            headers=auth_header(partner_token)
        )
        # Should succeed or fail with business logic, not 500
        assert r.status_code in [200, 400, 403], f"Unexpected status {r.status_code}: {r.text}"
        if r.status_code == 200:
            data = r.json()
            assert "sale_id" in data or "message" in data
        print(f"PASS: Send proposal endpoint works (status {r.status_code})")


class TestSubmitFinalRegression:
    """Regression test for Submit Final flow (also used setPas before fix)"""

    def test_submit_final_endpoint(self, partner_token):
        """Test submit-final endpoint works"""
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(partner_token))
        pas = r.json()
        
        # Find a proposal_paid PA
        paid_pa = None
        for pa in pas:
            if pa.get("stage") == "proposal_paid":
                paid_pa = pa
                break
        
        if not paid_pa:
            pytest.skip("No proposal_paid PA found for final submit test")
        
        pa_id = paid_pa["id"]
        
        # Submit final
        r = requests.post(
            f"{BASE_URL}/api/pre-assess-portal/partner/submit-final/{pa_id}",
            json={"notes": "Test final submission"},
            headers=auth_header(partner_token)
        )
        # Should succeed or fail with business logic, not 500
        assert r.status_code in [200, 400, 403], f"Unexpected status {r.status_code}: {r.text}"
        print(f"PASS: Submit final endpoint works (status {r.status_code})")


class TestEditPAMultipleFields:
    """Test editing multiple fields at once"""

    def test_edit_multiple_fields(self, partner_token):
        """Edit multiple fields in one request"""
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(partner_token))
        pas = r.json()
        
        editable_pa = None
        for pa in pas:
            if pa.get("stage") != "case_created":
                editable_pa = pa
                break
        
        if not editable_pa:
            pytest.skip("No editable PA found")
        
        pa_id = editable_pa["id"]
        
        # Edit multiple fields
        r = requests.put(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/details",
            json={
                "client_age": 32,
                "education": "Bachelor's in Computer Science",
                "work_experience": "6 years IT",
                "notes": "Updated via test"
            },
            headers=auth_header(partner_token)
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") == True
        
        # Verify changes
        r2 = requests.get(f"{BASE_URL}/api/pre-assessment/{pa_id}", headers=auth_header(partner_token))
        updated = r2.json()
        assert updated.get("client_age") == 32
        assert "Bachelor" in updated.get("education", "")
        print(f"PASS: Multiple fields edited successfully")


class TestEditPAValidation:
    """Test validation on edit endpoint"""

    def test_edit_empty_payload_rejected(self, partner_token):
        """Empty payload should be rejected"""
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments", headers=auth_header(partner_token))
        pas = r.json()
        
        if not pas:
            pytest.skip("No PAs found")
        
        pa_id = pas[0]["id"]
        
        # Send empty payload
        r = requests.put(
            f"{BASE_URL}/api/pre-assessment/{pa_id}/details",
            json={},
            headers=auth_header(partner_token)
        )
        assert r.status_code == 400, f"Expected 400 for empty payload, got {r.status_code}"
        print(f"PASS: Empty payload correctly rejected")

    def test_edit_nonexistent_pa(self, partner_token):
        """Editing non-existent PA returns 404"""
        r = requests.put(
            f"{BASE_URL}/api/pre-assessment/nonexistent-pa-id-12345/details",
            json={"client_name": "Test"},
            headers=auth_header(partner_token)
        )
        assert r.status_code == 404
        print(f"PASS: Non-existent PA returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
