"""
Iteration 27 - Promo Code, Discount, and Pending Assignment Tests
Tests for:
1. POST /api/sales — Partner creates sale with promo_code and discount_percentage
2. POST /api/sales — Partner creates sale WITHOUT promo or discount
3. POST /api/marketing/promo/validate — Validate promo codes
4. POST /api/sales/approve — Admin approves sale with/without case_manager_id
5. GET /api/cases/unassigned — Admin only endpoint for unassigned cases
6. PUT /api/cases/{case_id}/assign-manager — Assigns case manager
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}

# Product ID for Canada PR (from context)
CANADA_PR_PRODUCT_ID = "a1006a91-2dd3-453c-93f9-8eb28b488e0e"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def partner_token():
    """Get partner auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
    assert response.status_code == 200, f"Partner login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def manager_token():
    """Get case manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def client_token():
    """Get client auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    assert response.status_code == 200, f"Client login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def manager_user_id(admin_token):
    """Get case manager user ID"""
    response = requests.get(f"{BASE_URL}/api/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    users = response.json()
    manager = next((u for u in users if u["email"] == "manager@leamss.com"), None)
    assert manager is not None, "Case manager not found"
    return manager["id"]


class TestPromoCodeValidation:
    """Test promo code validation endpoint"""
    
    def test_validate_test20_promo_code(self, partner_token):
        """Validate TEST20 promo code returns valid=true, discount_type=percentage, discount_value=20"""
        response = requests.post(
            f"{BASE_URL}/api/marketing/promo/validate",
            json={"code": "TEST20"},
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Promo validation failed: {response.text}"
        data = response.json()
        assert data["valid"] == True
        assert data["discount_type"] == "percentage"
        assert data["discount_value"] == 20
        assert data["code"] == "TEST20"
        print(f"PASS: TEST20 promo validated - {data['discount_value']}% off")
    
    def test_validate_invalid_promo_code(self, partner_token):
        """Validate INVALIDCODE returns error"""
        response = requests.post(
            f"{BASE_URL}/api/marketing/promo/validate",
            json={"code": "INVALIDCODE"},
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 404, f"Expected 404 for invalid promo, got {response.status_code}"
        print("PASS: Invalid promo code returns 404")


class TestSaleCreationWithDiscount:
    """Test sale creation with promo codes and discounts"""
    
    def test_create_sale_with_promo_and_discount(self, partner_token):
        """Partner creates sale with promo_code=TEST20 and discount_percentage=5 on ₹50,000 fee
        Expected: final_fee=38,000 (20% promo + 5% additional), discount_applied=true
        Calculation: 50000 - 20% = 40000, then 40000 - 5% = 38000
        """
        unique_email = f"TEST_promo_client_{uuid.uuid4().hex[:8]}@test.com"
        
        form_data = {
            "client_name": "TEST Promo Client",
            "client_email": unique_email,
            "client_mobile": "9876543210",
            "product_id": CANADA_PR_PRODUCT_ID,
            "fee_amount": "50000",
            "amount_received": "0",
            "payment_method": "bank_transfer",
            "payment_reference": "",
            "agreement_signed": "true",
            "currency": "INR",
            "promo_code": "TEST20",
            "discount_percentage": "5"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            data=form_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        data = response.json()
        
        # Verify discount was applied
        assert data.get("discount_applied") == True, "discount_applied should be True"
        
        # Verify final fee calculation: 50000 - 20% = 40000, then 40000 - 5% = 38000
        expected_final_fee = 38000
        assert data.get("final_fee") == expected_final_fee, f"Expected final_fee={expected_final_fee}, got {data.get('final_fee')}"
        
        print(f"PASS: Sale created with promo+discount. Final fee: ₹{data['final_fee']} (expected ₹{expected_final_fee})")
        return data["id"]
    
    def test_create_sale_without_promo_or_discount(self, partner_token):
        """Partner creates sale WITHOUT promo or discount. Expected: normal fee, no discount fields"""
        unique_email = f"TEST_no_discount_client_{uuid.uuid4().hex[:8]}@test.com"
        
        form_data = {
            "client_name": "TEST No Discount Client",
            "client_email": unique_email,
            "client_mobile": "9876543211",
            "product_id": CANADA_PR_PRODUCT_ID,
            "fee_amount": "50000",
            "amount_received": "10000",
            "payment_method": "cash",
            "payment_reference": "CASH001",
            "agreement_signed": "true",
            "currency": "INR"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            data=form_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        data = response.json()
        
        # Verify no discount was applied
        assert data.get("discount_applied") == False or data.get("discount_applied") is None, "discount_applied should be False or None"
        
        # Verify final fee equals original fee
        assert data.get("final_fee") == 50000, f"Expected final_fee=50000, got {data.get('final_fee')}"
        
        print(f"PASS: Sale created without discount. Final fee: ₹{data['final_fee']}")
        return data["id"]


class TestSaleApprovalFlow:
    """Test sale approval with and without case manager assignment"""
    
    @pytest.fixture
    def pending_sale_id(self, partner_token):
        """Create a pending sale for approval testing"""
        unique_email = f"TEST_approval_client_{uuid.uuid4().hex[:8]}@test.com"
        
        form_data = {
            "client_name": "TEST Approval Client",
            "client_email": unique_email,
            "client_mobile": "9876543212",
            "product_id": CANADA_PR_PRODUCT_ID,
            "fee_amount": "30000",
            "amount_received": "5000",
            "payment_method": "bank_transfer",
            "agreement_signed": "true",
            "currency": "INR"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            data=form_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        return response.json()["id"]
    
    def test_approve_sale_without_case_manager(self, admin_token, pending_sale_id):
        """Admin approves sale WITHOUT case_manager_id. 
        Expected: assignment_pending=true, case created with status='pending_assignment'
        """
        response = requests.post(
            f"{BASE_URL}/api/sales/approve",
            json={
                "sale_id": pending_sale_id,
                "status": "approved",
                "case_manager_id": None  # No case manager assigned
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Sale approval failed: {response.text}"
        data = response.json()
        
        # Verify assignment_pending flag
        assert data.get("assignment_pending") == True, "assignment_pending should be True when no case manager assigned"
        assert "case_id" in data, "Response should contain case_id"
        
        print(f"PASS: Sale approved without case manager. assignment_pending=True, case_id={data['case_id']}")
        return data["case_id"]
    
    def test_approve_sale_with_case_manager(self, admin_token, partner_token, manager_user_id):
        """Admin approves sale WITH case_manager_id. Expected: case created with status='active'"""
        # First create a new sale
        unique_email = f"TEST_with_manager_client_{uuid.uuid4().hex[:8]}@test.com"
        
        form_data = {
            "client_name": "TEST With Manager Client",
            "client_email": unique_email,
            "client_mobile": "9876543213",
            "product_id": CANADA_PR_PRODUCT_ID,
            "fee_amount": "40000",
            "amount_received": "10000",
            "payment_method": "bank_transfer",
            "agreement_signed": "true",
            "currency": "INR"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/sales",
            data=form_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert create_response.status_code == 200
        sale_id = create_response.json()["id"]
        
        # Approve with case manager
        response = requests.post(
            f"{BASE_URL}/api/sales/approve",
            json={
                "sale_id": sale_id,
                "status": "approved",
                "case_manager_id": manager_user_id
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Sale approval failed: {response.text}"
        data = response.json()
        
        # Verify no assignment_pending flag (or it's False)
        assert data.get("assignment_pending") != True, "assignment_pending should not be True when case manager is assigned"
        assert "case_id" in data, "Response should contain case_id"
        
        print(f"PASS: Sale approved with case manager. case_id={data['case_id']}")
        return data["case_id"]


class TestUnassignedCasesEndpoint:
    """Test GET /api/cases/unassigned endpoint"""
    
    def test_admin_can_get_unassigned_cases(self, admin_token):
        """Admin can access unassigned cases endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/cases/unassigned",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get unassigned cases: {response.text}"
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list), "Response should be a list"
        
        # If there are unassigned cases, verify structure
        if len(data) > 0:
            case = data[0]
            assert "id" in case, "Case should have id"
            assert "case_id" in case or "case_number" in case or "id" in case, "Case should have identifier"
            # Check for pending_assignment status or null case_manager_id
            has_pending_status = case.get("status") == "pending_assignment"
            has_null_manager = case.get("case_manager_id") is None or case.get("case_manager_id") == ""
            assert has_pending_status or has_null_manager, "Unassigned case should have pending_assignment status or null case_manager_id"
        
        print(f"PASS: Admin retrieved {len(data)} unassigned cases")
        return data
    
    def test_non_admin_cannot_get_unassigned_cases(self, partner_token, client_token, manager_token):
        """Non-admin users get 403 forbidden"""
        for token, role in [(partner_token, "partner"), (client_token, "client"), (manager_token, "case_manager")]:
            response = requests.get(
                f"{BASE_URL}/api/cases/unassigned",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 403, f"{role} should get 403, got {response.status_code}"
            print(f"PASS: {role} correctly gets 403 on unassigned cases endpoint")


class TestCaseManagerAssignment:
    """Test PUT /api/cases/{case_id}/assign-manager endpoint"""
    
    @pytest.fixture
    def unassigned_case_id(self, admin_token, partner_token):
        """Create a sale and approve without manager to get an unassigned case"""
        unique_email = f"TEST_unassigned_case_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create sale
        form_data = {
            "client_name": "TEST Unassigned Case Client",
            "client_email": unique_email,
            "client_mobile": "9876543214",
            "product_id": CANADA_PR_PRODUCT_ID,
            "fee_amount": "25000",
            "amount_received": "5000",
            "payment_method": "cash",
            "agreement_signed": "true",
            "currency": "INR"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/sales",
            data=form_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert create_response.status_code == 200
        sale_id = create_response.json()["id"]
        
        # Approve without case manager
        approve_response = requests.post(
            f"{BASE_URL}/api/sales/approve",
            json={"sale_id": sale_id, "status": "approved", "case_manager_id": None},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert approve_response.status_code == 200
        
        # Get the case ID from unassigned cases
        unassigned_response = requests.get(
            f"{BASE_URL}/api/cases/unassigned",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert unassigned_response.status_code == 200
        cases = unassigned_response.json()
        
        # Find the case we just created (by sale_id)
        case = next((c for c in cases if c.get("sale_id") == sale_id), None)
        assert case is not None, "Created case not found in unassigned cases"
        return case["id"]
    
    def test_assign_manager_changes_status_to_active(self, admin_token, manager_user_id, unassigned_case_id):
        """Assigns case manager and changes status from 'pending_assignment' to 'active'"""
        response = requests.put(
            f"{BASE_URL}/api/cases/{unassigned_case_id}/assign-manager?case_manager_id={manager_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to assign manager: {response.text}"
        
        # Verify the case is now active
        case_response = requests.get(
            f"{BASE_URL}/api/cases/{unassigned_case_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert case_response.status_code == 200
        case_data = case_response.json()
        
        assert case_data.get("case_manager_id") == manager_user_id, "Case manager should be assigned"
        assert case_data.get("status") == "active", f"Case status should be 'active', got '{case_data.get('status')}'"
        
        print(f"PASS: Case manager assigned, status changed to 'active'")


class TestSaleDiscountFieldsInResponse:
    """Test that discount info is properly returned in sale responses"""
    
    def test_sale_with_discount_has_discount_fields(self, partner_token, admin_token):
        """Verify sale with discount has all discount-related fields"""
        unique_email = f"TEST_discount_fields_{uuid.uuid4().hex[:8]}@test.com"
        
        form_data = {
            "client_name": "TEST Discount Fields Client",
            "client_email": unique_email,
            "client_mobile": "9876543215",
            "product_id": CANADA_PR_PRODUCT_ID,
            "fee_amount": "60000",
            "amount_received": "0",
            "payment_method": "bank_transfer",
            "agreement_signed": "true",
            "currency": "INR",
            "promo_code": "TEST20",
            "discount_percentage": "10"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            data=form_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        sale_id = response.json()["id"]
        
        # Get sale details
        sale_response = requests.get(
            f"{BASE_URL}/api/sales/{sale_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert sale_response.status_code == 200
        sale = sale_response.json()
        
        # Verify discount fields exist
        assert "promo_code" in sale, "Sale should have promo_code field"
        assert sale["promo_code"] == "TEST20", f"promo_code should be TEST20, got {sale.get('promo_code')}"
        
        assert "promo_discount_amount" in sale, "Sale should have promo_discount_amount"
        assert "additional_discount_percentage" in sale, "Sale should have additional_discount_percentage"
        assert "additional_discount_amount" in sale, "Sale should have additional_discount_amount"
        assert "total_discount_amount" in sale, "Sale should have total_discount_amount"
        assert "fee_before_discount" in sale, "Sale should have fee_before_discount"
        
        # Verify calculations
        # 60000 - 20% = 48000, then 48000 - 10% = 43200
        expected_promo_discount = 12000  # 20% of 60000
        expected_additional_discount = 4800  # 10% of 48000
        expected_total_discount = 16800
        expected_final_fee = 43200
        
        assert sale["fee_before_discount"] == 60000, f"fee_before_discount should be 60000"
        assert sale["promo_discount_amount"] == expected_promo_discount, f"promo_discount_amount should be {expected_promo_discount}"
        assert sale["additional_discount_percentage"] == 10, "additional_discount_percentage should be 10"
        assert sale["additional_discount_amount"] == expected_additional_discount, f"additional_discount_amount should be {expected_additional_discount}"
        assert sale["total_discount_amount"] == expected_total_discount, f"total_discount_amount should be {expected_total_discount}"
        assert sale["fee_amount"] == expected_final_fee, f"fee_amount (final) should be {expected_final_fee}"
        
        print(f"PASS: All discount fields present and calculated correctly")
        print(f"  - Original: ₹60,000")
        print(f"  - Promo (20%): -₹{expected_promo_discount}")
        print(f"  - Additional (10%): -₹{expected_additional_discount}")
        print(f"  - Final: ₹{expected_final_fee}")


class TestFullFlow:
    """Test complete flow: Partner creates sale with promo → Admin approves without manager → 
    Case appears in Pending Assignment → Admin assigns manager → Case moves to active"""
    
    def test_full_promo_to_assignment_flow(self, partner_token, admin_token, manager_user_id):
        """Full end-to-end flow test"""
        unique_email = f"TEST_full_flow_{uuid.uuid4().hex[:8]}@test.com"
        
        # Step 1: Partner creates sale with promo
        print("\n=== Step 1: Partner creates sale with promo ===")
        form_data = {
            "client_name": "TEST Full Flow Client",
            "client_email": unique_email,
            "client_mobile": "9876543216",
            "product_id": CANADA_PR_PRODUCT_ID,
            "fee_amount": "50000",
            "amount_received": "10000",
            "payment_method": "bank_transfer",
            "agreement_signed": "true",
            "currency": "INR",
            "promo_code": "TEST20",
            "discount_percentage": "5"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/sales",
            data=form_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert create_response.status_code == 200
        sale_data = create_response.json()
        sale_id = sale_data["id"]
        assert sale_data["discount_applied"] == True
        assert sale_data["final_fee"] == 38000  # 50000 - 20% - 5%
        print(f"  Sale created: {sale_id}, final_fee: ₹{sale_data['final_fee']}")
        
        # Step 2: Admin approves without case manager
        print("\n=== Step 2: Admin approves without case manager ===")
        approve_response = requests.post(
            f"{BASE_URL}/api/sales/approve",
            json={"sale_id": sale_id, "status": "approved", "case_manager_id": None},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert approve_response.status_code == 200
        approve_data = approve_response.json()
        assert approve_data.get("assignment_pending") == True
        case_number = approve_data["case_id"]
        print(f"  Sale approved, case created: {case_number}, assignment_pending=True")
        
        # Step 3: Verify case appears in unassigned cases
        print("\n=== Step 3: Verify case in Pending Assignment ===")
        unassigned_response = requests.get(
            f"{BASE_URL}/api/cases/unassigned",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert unassigned_response.status_code == 200
        unassigned_cases = unassigned_response.json()
        
        # Find our case
        our_case = next((c for c in unassigned_cases if c.get("sale_id") == sale_id), None)
        assert our_case is not None, "Case should appear in unassigned cases"
        case_id = our_case["id"]
        assert our_case.get("status") == "pending_assignment" or our_case.get("case_manager_id") is None
        print(f"  Case found in unassigned list: {case_id}")
        
        # Step 4: Admin assigns manager
        print("\n=== Step 4: Admin assigns case manager ===")
        assign_response = requests.put(
            f"{BASE_URL}/api/cases/{case_id}/assign-manager?case_manager_id={manager_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert assign_response.status_code == 200
        print(f"  Manager assigned to case")
        
        # Step 5: Verify case is now active and not in unassigned
        print("\n=== Step 5: Verify case is active ===")
        case_response = requests.get(
            f"{BASE_URL}/api/cases/{case_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert case_response.status_code == 200
        final_case = case_response.json()
        assert final_case["status"] == "active", f"Case status should be 'active', got '{final_case['status']}'"
        assert final_case["case_manager_id"] == manager_user_id
        print(f"  Case status: {final_case['status']}, manager assigned: {final_case['case_manager_name']}")
        
        # Verify case no longer in unassigned list
        unassigned_response2 = requests.get(
            f"{BASE_URL}/api/cases/unassigned",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        unassigned_cases2 = unassigned_response2.json()
        our_case_still_there = next((c for c in unassigned_cases2 if c.get("id") == case_id), None)
        assert our_case_still_there is None, "Case should no longer be in unassigned list"
        print(f"  Case removed from unassigned list")
        
        print("\n=== FULL FLOW TEST PASSED ===")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
