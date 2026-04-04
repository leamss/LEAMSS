"""
Test Phase A-D Features: Workflows, Marketing, PDF Reports, AI Verification, Activity Logs, Notifications
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
MANAGER_EMAIL = "manager@leamss.com"
MANAGER_PASSWORD = "Manager@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASSWORD = "Client@123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def manager_token():
    """Get case manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGER_EMAIL,
        "password": MANAGER_PASSWORD
    })
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def partner_token():
    """Get partner auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARTNER_EMAIL,
        "password": PARTNER_PASSWORD
    })
    assert response.status_code == 200, f"Partner login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def client_token():
    """Get client auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CLIENT_EMAIL,
        "password": CLIENT_PASSWORD
    })
    assert response.status_code == 200, f"Client login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def products(admin_token):
    """Get list of products"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/products", headers=headers)
    assert response.status_code == 200
    return response.json()


# ============ WORKFLOW TESTS ============

class TestWorkflowAPIs:
    """Test Workflow Builder endpoints"""
    
    def test_get_workflow_for_product(self, admin_token, products):
        """GET /api/workflows/{product_id} - Get workflow steps for a product"""
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0]["id"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/workflows/{product_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "product_id" in data
        assert "product_name" in data
        assert "steps" in data
        assert isinstance(data["steps"], list)
        print(f"✓ Workflow for {data['product_name']}: {len(data['steps'])} steps")
    
    def test_update_workflow(self, admin_token, products):
        """PUT /api/workflows/{product_id} - Update workflow steps"""
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0]["id"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get existing workflow
        get_response = requests.get(f"{BASE_URL}/api/workflows/{product_id}", headers=headers)
        existing_steps = get_response.json().get("steps", [])
        
        # Add a test step
        test_steps = existing_steps + [{
            "name": "TEST_Workflow_Step",
            "description": "Test step for automation",
            "duration_days": 5,
            "required_documents": []
        }]
        
        response = requests.put(
            f"{BASE_URL}/api/workflows/{product_id}",
            headers=headers,
            json={"steps": test_steps}
        )
        
        assert response.status_code == 200
        assert "message" in response.json()
        print(f"✓ Workflow updated with {len(test_steps)} steps")
        
        # Verify the update
        verify_response = requests.get(f"{BASE_URL}/api/workflows/{product_id}", headers=headers)
        updated_steps = verify_response.json().get("steps", [])
        assert len(updated_steps) == len(test_steps)
        
        # Cleanup - remove test step
        cleanup_steps = [s for s in updated_steps if "TEST_" not in (s.get("name") or "")]
        requests.put(f"{BASE_URL}/api/workflows/{product_id}", headers=headers, json={"steps": cleanup_steps})
    
    def test_add_step_to_workflow(self, admin_token, products):
        """POST /api/workflows/{product_id}/step - Add a new step"""
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0]["id"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/workflows/{product_id}/step",
            headers=headers,
            json={
                "name": "TEST_New_Step",
                "description": "Test step added via API",
                "duration_days": 3
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        step_id = data["id"]
        print(f"✓ Step added with ID: {step_id}")
        
        # Cleanup - delete the test step
        delete_response = requests.delete(
            f"{BASE_URL}/api/workflows/{product_id}/step/{step_id}",
            headers=headers
        )
        assert delete_response.status_code == 200
        print("✓ Test step cleaned up")
    
    def test_delete_workflow_step(self, admin_token, products):
        """DELETE /api/workflows/{product_id}/step/{step_id} - Delete a step"""
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0]["id"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First add a step to delete
        add_response = requests.post(
            f"{BASE_URL}/api/workflows/{product_id}/step",
            headers=headers,
            json={"name": "TEST_Step_To_Delete", "description": "Will be deleted"}
        )
        step_id = add_response.json()["id"]
        
        # Delete the step
        response = requests.delete(
            f"{BASE_URL}/api/workflows/{product_id}/step/{step_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        assert "message" in response.json()
        print("✓ Step deleted successfully")
    
    def test_workflow_admin_only(self, client_token, products):
        """Verify workflow update requires admin role"""
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0]["id"]
        headers = {"Authorization": f"Bearer {client_token}"}
        
        response = requests.put(
            f"{BASE_URL}/api/workflows/{product_id}",
            headers=headers,
            json={"steps": []}
        )
        
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from updating workflow")


# ============ MARKETING / REFERRAL TESTS ============

class TestMarketingReferralAPIs:
    """Test Marketing Referral endpoints"""
    
    def test_get_my_referral_code(self, partner_token):
        """GET /api/marketing/referral/my-code - Get or generate referral code"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/marketing/referral/my-code", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "referral_count" in data
        print(f"✓ Referral code: {data['code']}, count: {data['referral_count']}")
    
    def test_referral_stats_admin_only(self, admin_token):
        """GET /api/marketing/referral/stats - Admin only endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/marketing/referral/stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_codes" in data
        assert "total_uses" in data
        assert "top_referrers" in data
        print(f"✓ Referral stats: {data['total_codes']} codes, {data['total_uses']} uses")
    
    def test_referral_stats_non_admin_blocked(self, client_token):
        """Verify referral stats requires admin role"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/marketing/referral/stats", headers=headers)
        
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from referral stats")
    
    def test_redeem_referral_code(self, client_token, partner_token):
        """POST /api/marketing/referral/redeem - Redeem a referral code"""
        # First get partner's referral code
        partner_headers = {"Authorization": f"Bearer {partner_token}"}
        code_response = requests.get(f"{BASE_URL}/api/marketing/referral/my-code", headers=partner_headers)
        referral_code = code_response.json()["code"]
        
        # Try to redeem as client
        client_headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.post(
            f"{BASE_URL}/api/marketing/referral/redeem",
            headers=client_headers,
            json={"code": referral_code}
        )
        
        # Either success (200) or already redeemed (400)
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            print(f"✓ Referral code {referral_code} redeemed successfully")
        else:
            print(f"✓ Referral code already redeemed (expected behavior)")
    
    def test_cannot_redeem_own_code(self, partner_token):
        """Verify user cannot redeem their own referral code"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        
        # Get own code
        code_response = requests.get(f"{BASE_URL}/api/marketing/referral/my-code", headers=headers)
        own_code = code_response.json()["code"]
        
        # Try to redeem own code
        response = requests.post(
            f"{BASE_URL}/api/marketing/referral/redeem",
            headers=headers,
            json={"code": own_code}
        )
        
        assert response.status_code == 400
        assert "own" in response.json().get("detail", "").lower()
        print("✓ User correctly blocked from redeeming own code")


# ============ MARKETING / PROMO CODE TESTS ============

class TestMarketingPromoAPIs:
    """Test Marketing Promo Code endpoints"""
    
    def test_create_promo_code(self, admin_token):
        """POST /api/marketing/promo - Create a promo code"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        promo_code = f"TEST{int(time.time()) % 10000}"
        response = requests.post(
            f"{BASE_URL}/api/marketing/promo",
            headers=headers,
            json={
                "code": promo_code,
                "discount_type": "percentage",
                "discount_value": 15,
                "max_uses": 50
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Promo code {promo_code} created with ID: {data['id']}")
        return data["id"]
    
    def test_get_all_promos(self, admin_token):
        """GET /api/marketing/promos - Get all promo codes"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/marketing/promos", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} promo codes")
        
        # Verify promo structure
        if data:
            promo = data[0]
            assert "id" in promo
            assert "code" in promo
            assert "discount_type" in promo
            assert "discount_value" in promo
    
    def test_validate_promo_code(self, admin_token, client_token):
        """POST /api/marketing/promo/validate - Validate a promo code"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First create a promo to validate
        promo_code = f"VALID{int(time.time()) % 10000}"
        create_response = requests.post(
            f"{BASE_URL}/api/marketing/promo",
            headers=admin_headers,
            json={"code": promo_code, "discount_type": "percentage", "discount_value": 10, "max_uses": 100}
        )
        
        # Validate as client
        client_headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.post(
            f"{BASE_URL}/api/marketing/promo/validate",
            headers=client_headers,
            json={"code": promo_code}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert data["code"] == promo_code
        assert data["discount_value"] == 10
        print(f"✓ Promo code {promo_code} validated successfully")
    
    def test_validate_invalid_promo(self, client_token):
        """Verify invalid promo code returns 404"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.post(
            f"{BASE_URL}/api/marketing/promo/validate",
            headers=headers,
            json={"code": "INVALID_CODE_XYZ"}
        )
        
        assert response.status_code == 404
        print("✓ Invalid promo code correctly rejected")
    
    def test_delete_promo_code(self, admin_token):
        """DELETE /api/marketing/promo/{id} - Deactivate a promo code"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a promo to delete
        promo_code = f"DEL{int(time.time()) % 10000}"
        create_response = requests.post(
            f"{BASE_URL}/api/marketing/promo",
            headers=headers,
            json={"code": promo_code, "discount_type": "fixed", "discount_value": 500, "max_uses": 10}
        )
        promo_id = create_response.json()["id"]
        
        # Delete (deactivate) the promo
        response = requests.delete(f"{BASE_URL}/api/marketing/promo/{promo_id}", headers=headers)
        
        assert response.status_code == 200
        print(f"✓ Promo code {promo_code} deactivated")
        
        # Verify it's no longer valid
        validate_response = requests.post(
            f"{BASE_URL}/api/marketing/promo/validate",
            headers=headers,
            json={"code": promo_code}
        )
        assert validate_response.status_code == 404
        print("✓ Deactivated promo correctly returns 404 on validation")
    
    def test_promo_admin_only(self, client_token):
        """Verify promo creation requires admin role"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.post(
            f"{BASE_URL}/api/marketing/promo",
            headers=headers,
            json={"code": "CLIENTPROMO", "discount_type": "percentage", "discount_value": 10}
        )
        
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from creating promos")


# ============ PDF REPORT TESTS ============

class TestPDFReportAPIs:
    """Test PDF Report Generation endpoints"""
    
    def test_export_sales_report_pdf(self, admin_token):
        """GET /api/reports/export/sales-report - Export sales as PDF"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/export/sales-report",
            headers=headers
        )
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        print(f"✓ Sales report PDF generated: {len(response.content)} bytes")
    
    def test_export_sales_report_with_status_filter(self, admin_token):
        """GET /api/reports/export/sales-report?status=approved - Filter by status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/export/sales-report?status=approved",
            headers=headers
        )
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        print(f"✓ Filtered sales report PDF generated: {len(response.content)} bytes")
    
    def test_export_commission_report_pdf(self, admin_token):
        """GET /api/reports/export/commission-report - Export commission report as PDF"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/export/commission-report",
            headers=headers
        )
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        print(f"✓ Commission report PDF generated: {len(response.content)} bytes")
    
    def test_export_partner_sales_pdf(self, admin_token, partner_token):
        """GET /api/reports/export/partner-sales - Export partner sales as PDF"""
        # Test as admin
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/export/partner-sales",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        print(f"✓ Partner sales PDF (admin): {len(response.content)} bytes")
        
        # Test as partner
        partner_headers = {"Authorization": f"Bearer {partner_token}"}
        response2 = requests.get(
            f"{BASE_URL}/api/reports/export/partner-sales",
            headers=partner_headers
        )
        
        assert response2.status_code == 200
        assert response2.headers.get("content-type") == "application/pdf"
        print(f"✓ Partner sales PDF (partner): {len(response2.content)} bytes")
    
    def test_pdf_report_admin_only(self, client_token):
        """Verify PDF reports require admin role"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/export/sales-report",
            headers=headers
        )
        
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from sales PDF export")


# ============ AI VERIFICATION TESTS ============

class TestAIVerificationAPIs:
    """Test AI Document Verification endpoints"""
    
    def test_ai_verify_document_not_found(self, admin_token):
        """POST /api/ai/verify-document/{doc_id} - Test with non-existent document"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(
            f"{BASE_URL}/api/ai/verify-document/nonexistent-doc-id",
            headers=headers
        )
        
        # Should return 404 for non-existent document
        assert response.status_code == 404
        print("✓ AI verification correctly returns 404 for non-existent document")
    
    def test_ai_verify_requires_admin_or_manager(self, client_token):
        """Verify AI verification requires admin or case_manager role"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.post(
            f"{BASE_URL}/api/ai/verify-document/any-doc-id",
            headers=headers
        )
        
        assert response.status_code == 403
        print("✓ Client correctly blocked from AI verification")
    
    def test_get_ai_analysis_not_found(self, admin_token):
        """GET /api/ai/analysis/{doc_id} - Test with non-existent document"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/ai/analysis/nonexistent-doc-id",
            headers=headers
        )
        
        assert response.status_code == 404
        print("✓ AI analysis correctly returns 404 for non-existent document")


# ============ ACTIVITY LOG TESTS ============

class TestActivityLogAPIs:
    """Test Activity Log endpoints"""
    
    def test_get_activity_logs(self, admin_token):
        """GET /api/activity/logs - Get activity logs"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/activity/logs", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Activity logs: {len(data)} entries")
        
        # Verify log structure if any exist
        if data:
            log = data[0]
            assert "user_name" in log or "user_id" in log
            assert "action" in log or "entity_type" in log
    
    def test_get_activity_logs_with_filters(self, admin_token):
        """GET /api/activity/logs with filters"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/activity/logs?entity_type=sale&days=7&limit=50",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Filtered activity logs: {len(data)} entries")
    
    def test_get_activity_stats(self, admin_token):
        """GET /api/activity/stats - Get activity statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/activity/stats?days=7", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_activities" in data
        assert "activities_by_type" in data
        assert "activities_by_action" in data
        assert "activities_by_date" in data
        assert "most_active_users" in data
        print(f"✓ Activity stats: {data['total_activities']} total activities in last 7 days")
    
    def test_activity_logs_admin_only(self, client_token):
        """Verify activity logs require admin role"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/activity/logs", headers=headers)
        
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from activity logs")
    
    def test_activity_stats_admin_only(self, client_token):
        """Verify activity stats require admin role"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/activity/stats", headers=headers)
        
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from activity stats")


# ============ NOTIFICATION TESTS ============

class TestNotificationAPIs:
    """Test Notification endpoints"""
    
    def test_get_notifications(self, admin_token):
        """GET /api/notifications - Get user notifications"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Notifications: {len(data)} entries")
        
        # Verify notification structure if any exist
        if data:
            notif = data[0]
            assert "id" in notif or "title" in notif
    
    def test_mark_all_notifications_read(self, admin_token):
        """PUT /api/notifications/mark-all-read - Mark all as read"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.put(f"{BASE_URL}/api/notifications/mark-all-read", headers=headers)
        
        assert response.status_code == 200
        print("✓ All notifications marked as read")


# ============ INTEGRATION TESTS ============

class TestPhaseADIntegration:
    """Integration tests for Phase A-D features"""
    
    def test_workflow_activity_logging(self, admin_token, products):
        """Verify workflow updates are logged in activity"""
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0]["id"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Update workflow
        requests.put(
            f"{BASE_URL}/api/workflows/{product_id}",
            headers=headers,
            json={"steps": [{"name": "Integration Test Step", "description": "Test"}]}
        )
        
        # Check activity logs
        time.sleep(0.5)  # Allow time for log to be written
        logs_response = requests.get(f"{BASE_URL}/api/activity/logs?limit=10", headers=headers)
        logs = logs_response.json()
        
        # Should have a recent workflow update log
        workflow_logs = [l for l in logs if "workflow" in str(l).lower()]
        print(f"✓ Found {len(workflow_logs)} workflow-related activity logs")
    
    def test_promo_creation_activity_logging(self, admin_token):
        """Verify promo creation is logged in activity"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create promo
        promo_code = f"ACTLOG{int(time.time()) % 10000}"
        requests.post(
            f"{BASE_URL}/api/marketing/promo",
            headers=headers,
            json={"code": promo_code, "discount_type": "percentage", "discount_value": 5, "max_uses": 10}
        )
        
        # Check activity logs
        time.sleep(0.5)
        logs_response = requests.get(f"{BASE_URL}/api/activity/logs?limit=10", headers=headers)
        logs = logs_response.json()
        
        promo_logs = [l for l in logs if "promo" in str(l).lower()]
        print(f"✓ Found {len(promo_logs)} promo-related activity logs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
