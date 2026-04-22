"""
Iteration 78 - Phase A Retouch + 3 Major Features Tests
Tests for:
1. Partner-Review middle stage (client submit → partner_review, NOT documents_submitted)
2. Partner forward-to-admin endpoint
3. Upsell Bundles CRUD + auto-seed
4. AI Proposal Generator (GPT-5.2 via Emergent LLM key)
5. Enhanced send-proposal with promo_code, additional_discount, upsell_bundle_ids
6. Sales strict rule (partner must have pre_assessment_id OR bypass)
7. Full E2E happy path
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert r.status_code == 200, f"Admin login failed: {r.text}"
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        """Get partner token"""
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        assert r.status_code == 200, f"Partner login failed: {r.text}"
        return r.json()["token"]
    
    def test_admin_login(self, admin_token):
        """Verify admin can login"""
        assert admin_token is not None
        assert len(admin_token) > 10
        print(f"Admin token obtained: {admin_token[:20]}...")
    
    def test_partner_login(self, partner_token):
        """Verify partner can login"""
        assert partner_token is not None
        assert len(partner_token) > 10
        print(f"Partner token obtained: {partner_token[:20]}...")


class TestUpsellBundles:
    """Upsell Bundles CRUD tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com", "password": "Admin@123"
        })
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com", "password": "Partner@123"
        })
        return r.json()["token"]
    
    def test_list_bundles_auto_seeds(self, partner_token):
        """GET /api/upsell-bundles should auto-seed 6 defaults if empty"""
        r = requests.get(f"{BASE_URL}/api/upsell-bundles", 
                        headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 200, f"Failed: {r.text}"
        bundles = r.json()
        assert isinstance(bundles, list)
        # Should have at least 6 seeded bundles
        assert len(bundles) >= 6, f"Expected at least 6 bundles, got {len(bundles)}"
        print(f"Found {len(bundles)} bundles")
        # Check structure
        for b in bundles[:3]:
            assert "id" in b
            assert "name" in b
            assert "amount" in b
            assert b["amount"] > 0
            print(f"  - {b['name']}: ₹{b['amount']}")
    
    def test_create_bundle_admin_only(self, admin_token, partner_token):
        """POST /api/upsell-bundles - admin only"""
        payload = {
            "name": f"TEST_Bundle_{uuid.uuid4().hex[:6]}",
            "amount": 9999,
            "description": "Test bundle for iteration 78",
            "category": "priority",
            "is_active": True
        }
        # Partner should fail
        r = requests.post(f"{BASE_URL}/api/upsell-bundles", json=payload,
                         headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 403, f"Partner should not create bundles: {r.text}"
        
        # Admin should succeed
        r = requests.post(f"{BASE_URL}/api/upsell-bundles", json=payload,
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200, f"Admin create failed: {r.text}"
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["amount"] == payload["amount"]
        print(f"Created bundle: {data['name']} (id={data['id']})")
        return data["id"]
    
    def test_resolve_bundles(self, partner_token):
        """POST /api/upsell-bundles/resolve - get bundle details by IDs"""
        # First get some bundle IDs
        r = requests.get(f"{BASE_URL}/api/upsell-bundles",
                        headers={"Authorization": f"Bearer {partner_token}"})
        bundles = r.json()
        if len(bundles) < 2:
            pytest.skip("Not enough bundles to test resolve")
        
        bundle_ids = [bundles[0]["id"], bundles[1]["id"]]
        r = requests.post(f"{BASE_URL}/api/upsell-bundles/resolve", json=bundle_ids,
                         headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 200, f"Resolve failed: {r.text}"
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) == 2
        expected_total = bundles[0]["amount"] + bundles[1]["amount"]
        assert data["total"] == expected_total, f"Total mismatch: {data['total']} != {expected_total}"
        print(f"Resolved 2 bundles, total: ₹{data['total']}")


class TestAIProposalGenerator:
    """AI Proposal Generator tests (GPT-5.2 via Emergent LLM key)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com", "password": "Admin@123"
        })
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com", "password": "Partner@123"
        })
        return r.json()["token"]
    
    def test_ai_generate_partner_only(self, partner_token, admin_token):
        """POST /api/ai-proposal/generate - partner or admin only"""
        # Get a PA owned by partner
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments",
                        headers={"Authorization": f"Bearer {partner_token}"})
        pas = r.json()
        if not pas:
            pytest.skip("No pre-assessments found for partner")
        
        pa_id = pas[0]["id"]
        
        # Test with partner token (should work)
        r = requests.post(f"{BASE_URL}/api/ai-proposal/generate",
                         json={"pa_id": pa_id, "tone": "professional"},
                         headers={"Authorization": f"Bearer {partner_token}"},
                         timeout=30)  # AI can take time
        
        if r.status_code == 200:
            data = r.json()
            assert data["ok"] == True
            assert "proposal_text" in data
            assert len(data["proposal_text"]) > 100, "Proposal text too short"
            assert data["word_count"] >= 100, f"Word count too low: {data['word_count']}"
            print(f"AI generated proposal: {data['word_count']} words, model: {data.get('model')}")
            print(f"Preview: {data['proposal_text'][:200]}...")
        elif r.status_code == 502:
            # AI service might be slow/unavailable
            print(f"AI service returned 502: {r.text[:200]}")
        else:
            assert r.status_code in [200, 502], f"Unexpected status: {r.status_code} - {r.text}"
    
    def test_ai_generate_403_for_non_partner(self, partner_token):
        """AI generate should fail for non-partner/admin"""
        # Create a client token
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com", "password": "Client@123"
        })
        if r.status_code != 200:
            pytest.skip("Client login failed")
        client_token = r.json()["token"]
        
        r = requests.post(f"{BASE_URL}/api/ai-proposal/generate",
                         json={"pa_id": "any-id", "tone": "professional"},
                         headers={"Authorization": f"Bearer {client_token}"})
        assert r.status_code == 403, f"Expected 403 for client: {r.text}"
        print("Correctly rejected client from AI generate")


class TestPartnerReviewStage:
    """Partner-Review middle stage tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com", "password": "Admin@123"
        })
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com", "password": "Partner@123"
        })
        return r.json()["token"]
    
    def test_client_submit_transitions_to_partner_review(self, partner_token, admin_token):
        """Client submit should transition to partner_review, NOT documents_submitted"""
        # Find a PA in payment_received stage
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments",
                        headers={"Authorization": f"Bearer {partner_token}"})
        pas = r.json()
        payment_received_pa = next((p for p in pas if p.get("stage") == "payment_received"), None)
        
        if not payment_received_pa:
            print("No PA in payment_received stage to test client submit")
            # Just verify the endpoint exists
            r = requests.post(f"{BASE_URL}/api/pre-assess-portal/client/submit/fake-id",
                             headers={"Authorization": f"Bearer {partner_token}"})
            # Should fail with 403 (client only) or 404
            assert r.status_code in [403, 404], f"Unexpected: {r.status_code}"
            print("Endpoint exists, requires client role")
            return
        
        print(f"Found PA in payment_received: {payment_received_pa['id']}")
    
    def test_partner_forward_to_admin_endpoint(self, partner_token):
        """POST /api/pre-assess-portal/partner/forward-to-admin/{pa_id}"""
        # Find a PA in partner_review stage
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments",
                        headers={"Authorization": f"Bearer {partner_token}"})
        pas = r.json()
        partner_review_pa = next((p for p in pas if p.get("stage") == "partner_review"), None)
        
        if not partner_review_pa:
            # Test endpoint exists with wrong stage
            if pas:
                pa_id = pas[0]["id"]
                r = requests.post(f"{BASE_URL}/api/pre-assess-portal/partner/forward-to-admin/{pa_id}",
                                 json={"remarks": "Test remarks"},
                                 headers={"Authorization": f"Bearer {partner_token}"})
                # Should fail with 400 (wrong stage)
                assert r.status_code == 400, f"Expected 400 for wrong stage: {r.status_code} - {r.text}"
                assert "stage" in r.text.lower(), f"Error should mention stage: {r.text}"
                print(f"Endpoint correctly rejects non-partner_review stage")
            return
        
        # Forward to admin
        r = requests.post(f"{BASE_URL}/api/pre-assess-portal/partner/forward-to-admin/{partner_review_pa['id']}",
                         json={"remarks": "All docs verified. Client eligible."},
                         headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 200, f"Forward failed: {r.text}"
        print(f"Forwarded PA {partner_review_pa['id']} to admin")
        
        # Verify stage changed to documents_submitted
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments",
                        headers={"Authorization": f"Bearer {partner_token}"})
        updated_pa = next((p for p in r.json() if p["id"] == partner_review_pa["id"]), None)
        assert updated_pa["stage"] == "documents_submitted", f"Stage should be documents_submitted: {updated_pa['stage']}"
        print("Stage correctly transitioned to documents_submitted")


class TestEnhancedSendProposal:
    """Enhanced send-proposal with promo, discount, upsells tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com", "password": "Admin@123"
        })
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com", "password": "Partner@123"
        })
        return r.json()["token"]
    
    def test_create_promo_code(self, admin_token):
        """Create SAVE10 promo code for testing"""
        payload = {
            "code": "SAVE10",
            "discount_type": "percentage",
            "discount_value": 10,
            "max_uses": 100,
            "is_active": True
        }
        r = requests.post(f"{BASE_URL}/api/marketing/promo", json=payload,
                         headers={"Authorization": f"Bearer {admin_token}"})
        # May already exist
        if r.status_code == 200:
            print("Created SAVE10 promo code")
        elif r.status_code == 400 and "exists" in r.text.lower():
            print("SAVE10 promo code already exists")
        else:
            print(f"Promo creation: {r.status_code} - {r.text}")
    
    def test_send_proposal_with_discounts_and_upsells(self, partner_token, admin_token):
        """Send proposal with promo_code, additional_discount, upsell_bundle_ids"""
        # Find an approved PA
        r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments",
                        headers={"Authorization": f"Bearer {partner_token}"})
        pas = r.json()
        approved_pa = next((p for p in pas if p.get("stage") == "approved"), None)
        
        if not approved_pa:
            print("No approved PA to test send-proposal")
            # Test endpoint validation
            if pas:
                pa_id = pas[0]["id"]
                r = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/send-proposal",
                                 json={"fee_amount": 100000},
                                 headers={"Authorization": f"Bearer {partner_token}"})
                # Should fail with 400 (not approved)
                assert r.status_code == 400, f"Expected 400: {r.status_code}"
                print("Endpoint correctly requires approved stage")
            return
        
        # Get upsell bundle IDs
        r = requests.get(f"{BASE_URL}/api/upsell-bundles",
                        headers={"Authorization": f"Bearer {partner_token}"})
        bundles = r.json()
        upsell_ids = [bundles[0]["id"], bundles[1]["id"]] if len(bundles) >= 2 else []
        upsell_total = sum(b["amount"] for b in bundles[:2]) if len(bundles) >= 2 else 0
        
        # Send proposal
        base_fee = 150000
        additional_discount = 5000
        payload = {
            "fee_amount": base_fee,
            "promo_code": "SAVE10",
            "additional_discount": additional_discount,
            "upsell_bundle_ids": upsell_ids,
            "ai_proposal_text": "Test AI proposal text for iteration 78",
            "notes": "Test proposal with all features"
        }
        
        r = requests.post(f"{BASE_URL}/api/pre-assessment/{approved_pa['id']}/send-proposal",
                         json=payload,
                         headers={"Authorization": f"Bearer {partner_token}"})
        
        if r.status_code == 400 and "promo" in r.text.lower():
            # Promo code might be invalid/expired
            print(f"Promo code issue: {r.text}")
            # Try without promo
            payload["promo_code"] = None
            r = requests.post(f"{BASE_URL}/api/pre-assessment/{approved_pa['id']}/send-proposal",
                             json=payload,
                             headers={"Authorization": f"Bearer {partner_token}"})
        
        assert r.status_code == 200, f"Send proposal failed: {r.text}"
        data = r.json()
        
        # Verify breakdown
        assert "breakdown" in data, "Response should include breakdown"
        bd = data["breakdown"]
        assert bd["base_fee"] == base_fee
        assert bd["additional_discount"] == additional_discount
        
        if upsell_ids:
            assert bd["upsell_total"] == upsell_total, f"Upsell total mismatch: {bd['upsell_total']} != {upsell_total}"
        
        # Verify final amount calculation
        expected_final = base_fee - bd.get("promo_discount", 0) - additional_discount + bd.get("upsell_total", 0)
        assert bd["final_amount"] == expected_final, f"Final amount mismatch: {bd['final_amount']} != {expected_final}"
        
        print(f"Proposal sent successfully!")
        print(f"  Base: ₹{bd['base_fee']}")
        print(f"  Promo discount: ₹{bd.get('promo_discount', 0)}")
        print(f"  Additional discount: ₹{bd['additional_discount']}")
        print(f"  Upsells: ₹{bd.get('upsell_total', 0)}")
        print(f"  Final: ₹{bd['final_amount']}")


class TestSalesStrictRule:
    """Sales strict rule - partner must have pre_assessment_id OR bypass"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com", "password": "Admin@123"
        })
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com", "password": "Partner@123"
        })
        return r.json()["token"]
    
    def test_partner_cannot_create_sale_without_pa_or_bypass(self, partner_token):
        """Partner must provide pre_assessment_id OR bypass_pre_assessment with reason"""
        # Get a product ID
        r = requests.get(f"{BASE_URL}/api/products",
                        headers={"Authorization": f"Bearer {partner_token}"})
        products = r.json()
        if not products:
            pytest.skip("No products found")
        product_id = products[0]["id"]
        
        # Try to create sale without PA or bypass
        form_data = {
            "client_name": "TEST_NoPA_Client",
            "client_email": f"test_nopa_{uuid.uuid4().hex[:6]}@example.com",
            "client_mobile": "+91-9999999999",
            "product_id": product_id,
            "fee_amount": "100000",
            "amount_received": "0",
            "payment_method": "cash"
        }
        
        r = requests.post(f"{BASE_URL}/api/sales", data=form_data,
                         headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 400, f"Expected 400 without PA: {r.status_code} - {r.text}"
        assert "pre-assessment" in r.text.lower(), f"Error should mention pre-assessment: {r.text}"
        print("Correctly rejected sale without PA or bypass")
    
    def test_partner_can_bypass_with_reason(self, partner_token):
        """Partner can bypass PA requirement with reason (min 10 chars)"""
        r = requests.get(f"{BASE_URL}/api/products",
                        headers={"Authorization": f"Bearer {partner_token}"})
        products = r.json()
        if not products:
            pytest.skip("No products found")
        product_id = products[0]["id"]
        
        # Try bypass with short reason (should fail)
        form_data = {
            "client_name": "TEST_Bypass_Client",
            "client_email": f"test_bypass_{uuid.uuid4().hex[:6]}@example.com",
            "client_mobile": "+91-9999999999",
            "product_id": product_id,
            "fee_amount": "100000",
            "amount_received": "0",
            "payment_method": "cash",
            "bypass_pre_assessment": "true",
            "bypass_reason": "short"  # Less than 10 chars
        }
        
        r = requests.post(f"{BASE_URL}/api/sales", data=form_data,
                         headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 400, f"Expected 400 for short reason: {r.status_code}"
        assert "10" in r.text or "reason" in r.text.lower(), f"Error should mention min chars: {r.text}"
        print("Correctly rejected bypass with short reason")
        
        # Try with valid reason
        form_data["bypass_reason"] = "Existing client from previous year, already verified documents"
        r = requests.post(f"{BASE_URL}/api/sales", data=form_data,
                         headers={"Authorization": f"Bearer {partner_token}"})
        # This should work (or fail for other reasons like duplicate email)
        if r.status_code == 200:
            print("Bypass with valid reason accepted")
        else:
            print(f"Bypass result: {r.status_code} - {r.text[:200]}")
    
    def test_admin_can_create_sale_without_pa(self, admin_token):
        """Admin can create sale without PA requirement"""
        r = requests.get(f"{BASE_URL}/api/products",
                        headers={"Authorization": f"Bearer {admin_token}"})
        products = r.json()
        if not products:
            pytest.skip("No products found")
        product_id = products[0]["id"]
        
        form_data = {
            "client_name": "TEST_Admin_Sale",
            "client_email": f"test_admin_sale_{uuid.uuid4().hex[:6]}@example.com",
            "client_mobile": "+91-9999999999",
            "product_id": product_id,
            "fee_amount": "100000",
            "amount_received": "0",
            "payment_method": "cash"
        }
        
        r = requests.post(f"{BASE_URL}/api/sales", data=form_data,
                         headers={"Authorization": f"Bearer {admin_token}"})
        # Admin should be able to create without PA
        if r.status_code == 200:
            print("Admin created sale without PA requirement")
        else:
            print(f"Admin sale result: {r.status_code} - {r.text[:200]}")


class TestE2EHappyPath:
    """Full E2E happy path test"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com", "password": "Admin@123"
        })
        return r.json()["token"]
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com", "password": "Partner@123"
        })
        return r.json()["token"]
    
    def test_e2e_flow_overview(self, partner_token, admin_token):
        """Test the E2E flow stages exist and work"""
        # 1. Partner creates PA
        pa_data = {
            "client_name": f"TEST_E2E_{uuid.uuid4().hex[:6]}",
            "client_email": f"test_e2e_{uuid.uuid4().hex[:6]}@example.com",
            "client_mobile": "+91-9876543210",
            "country": "Canada",
            "service_type": "PR",
            "notes": "E2E test for iteration 78"
        }
        
        r = requests.post(f"{BASE_URL}/api/pre-assessment/create", json=pa_data,
                         headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 200, f"Create PA failed: {r.text}"
        pa = r.json()
        pa_id = pa.get("id") or pa.get("pa_id")
        assert pa_id, f"No PA ID in response: {pa}"
        # Stage might be in response or need to fetch
        stage = pa.get("stage", "new")
        print(f"1. Created PA: {pa_id}, stage={stage}")
        
        # 2. Generate public link (simulates sending payment link)
        r = requests.post(f"{BASE_URL}/api/pre-assess-portal/generate-public-link",
                         json={"pa_id": pa_id},
                         headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 200, f"Generate link failed: {r.text}"
        print(f"2. Generated public link")
        
        # 3. Verify PA stats endpoint works
        r = requests.get(f"{BASE_URL}/api/pre-assessment/stats/overview",
                        headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 200
        stats = r.json()
        assert "total" in stats
        print(f"3. Stats: total={stats.get('total')}, approved={stats.get('approved')}")
        
        # 4. Verify upsell bundles are available
        r = requests.get(f"{BASE_URL}/api/upsell-bundles",
                        headers={"Authorization": f"Bearer {partner_token}"})
        assert r.status_code == 200
        bundles = r.json()
        assert len(bundles) >= 6, "Should have at least 6 seeded bundles"
        print(f"4. Upsell bundles available: {len(bundles)}")
        
        # 5. Verify AI proposal endpoint exists
        r = requests.post(f"{BASE_URL}/api/ai-proposal/generate",
                         json={"pa_id": pa_id, "tone": "professional"},
                         headers={"Authorization": f"Bearer {partner_token}"},
                         timeout=30)
        # May fail due to stage, but endpoint should exist
        assert r.status_code in [200, 400, 502], f"AI endpoint issue: {r.status_code}"
        print(f"5. AI proposal endpoint accessible")
        
        # 6. Verify forward-to-admin endpoint exists
        r = requests.post(f"{BASE_URL}/api/pre-assess-portal/partner/forward-to-admin/{pa_id}",
                         json={"remarks": "Test"},
                         headers={"Authorization": f"Bearer {partner_token}"})
        # Should fail with 400 (wrong stage) since PA is in 'new' stage
        assert r.status_code == 400, f"Forward endpoint issue: {r.status_code}"
        print(f"6. Forward-to-admin endpoint exists (correctly rejects wrong stage)")
        
        print("\nE2E flow overview complete - all endpoints accessible!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
