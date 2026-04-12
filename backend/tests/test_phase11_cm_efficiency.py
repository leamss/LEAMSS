"""
Phase 11: CM Efficiency Features + Email Digest Tests
- Email Digest (Admin): Preview, Send Now, Settings
- 11A Smart Workload (CM): Prioritized workload view
- 11B Communication Hub (CM): Client messaging
- 11C Batch Case Operations (CM): Batch actions on cases
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
CM_EMAIL = "manager@leamss.com"
CM_PASSWORD = "Manager@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def cm_token():
    """Get case manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CM_EMAIL,
        "password": CM_PASSWORD
    })
    assert response.status_code == 200, f"CM login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def partner_token():
    """Get partner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARTNER_EMAIL,
        "password": PARTNER_PASSWORD
    })
    assert response.status_code == 200, f"Partner login failed: {response.text}"
    return response.json()["token"]


class TestEmailDigest:
    """Email Digest feature tests (Admin only)"""
    
    def test_email_digest_preview_admin(self, admin_token):
        """Admin can preview email digest"""
        response = requests.get(
            f"{BASE_URL}/api/email-digest/preview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Preview failed: {response.text}"
        data = response.json()
        
        # Verify digest structure
        assert "generated_at" in data
        assert "period" in data
        assert "revenue" in data
        assert "approvals" in data
        assert "cases" in data
        assert "tickets" in data
        
        # Verify revenue structure
        revenue = data["revenue"]
        assert "total" in revenue
        assert "received" in revenue
        assert "pending" in revenue
        assert "commission" in revenue
        assert "net" in revenue
        assert "week_new_sales" in revenue
        assert "week_revenue" in revenue
        
        # Verify approvals structure
        approvals = data["approvals"]
        assert "pending_sales" in approvals
        assert "pending_pre_assessments" in approvals
        assert "total_pending" in approvals
        
        # Verify cases structure
        cases = data["cases"]
        assert "total" in cases
        assert "active" in cases
        assert "completed" in cases
        assert "completion_rate" in cases
        
        # Verify tickets structure
        tickets = data["tickets"]
        assert "open" in tickets
        assert "urgent" in tickets
        
        print(f"✓ Email digest preview: Revenue total={revenue['total']}, Active cases={cases['active']}, Open tickets={tickets['open']}")
    
    def test_email_digest_preview_forbidden_for_non_admin(self, cm_token):
        """Non-admin cannot access email digest preview"""
        response = requests.get(
            f"{BASE_URL}/api/email-digest/preview",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Email digest preview correctly forbidden for non-admin")
    
    def test_email_digest_send_now_admin(self, admin_token):
        """Admin can send digest email (mock mode)"""
        response = requests.post(
            f"{BASE_URL}/api/email-digest/send-now",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Send failed: {response.text}"
        data = response.json()
        
        assert "message" in data
        assert "recipients" in data
        assert data["recipients"] >= 0  # At least 0 admins (mock mode)
        print(f"✓ Email digest sent to {data['recipients']} admin(s)")
    
    def test_email_digest_settings_get(self, admin_token):
        """Admin can get digest settings"""
        response = requests.get(
            f"{BASE_URL}/api/email-digest/settings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get settings failed: {response.text}"
        data = response.json()
        
        assert "frequency" in data
        assert data["frequency"] in ["daily", "weekly", "monthly"]
        print(f"✓ Email digest settings: frequency={data['frequency']}")
    
    def test_email_digest_settings_update(self, admin_token):
        """Admin can update digest settings"""
        response = requests.put(
            f"{BASE_URL}/api/email-digest/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"frequency": "weekly", "recipients": [], "enabled": True}
        )
        assert response.status_code == 200, f"Update settings failed: {response.text}"
        data = response.json()
        assert "message" in data
        print("✓ Email digest settings updated")


class TestSmartWorkload:
    """Phase 11A: Smart Workload View tests (CM)"""
    
    def test_workload_endpoint_cm(self, cm_token):
        """CM can access smart workload view"""
        response = requests.get(
            f"{BASE_URL}/api/cm-tools/workload",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert response.status_code == 200, f"Workload failed: {response.text}"
        data = response.json()
        
        # Verify workload categories
        assert "overdue" in data
        assert "due_today" in data
        assert "action_needed" in data
        assert "upcoming" in data
        assert "on_track" in data
        assert "summary" in data
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_active" in summary
        assert "overdue_count" in summary
        assert "due_today_count" in summary
        assert "action_needed_count" in summary
        assert "upcoming_count" in summary
        assert "on_track_count" in summary
        assert "workload_score" in summary
        
        # Workload score should be 0-100
        assert 0 <= summary["workload_score"] <= 100
        
        print(f"✓ Smart workload: score={summary['workload_score']}, total_active={summary['total_active']}")
        print(f"  Overdue={summary['overdue_count']}, Due today={summary['due_today_count']}, Action needed={summary['action_needed_count']}")
    
    def test_workload_endpoint_admin(self, admin_token):
        """Admin can also access smart workload view (sees all cases)"""
        response = requests.get(
            f"{BASE_URL}/api/cm-tools/workload",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Admin workload failed: {response.text}"
        data = response.json()
        assert "summary" in data
        print(f"✓ Admin workload access: total_active={data['summary']['total_active']}")
    
    def test_workload_forbidden_for_partner(self, partner_token):
        """Partner cannot access workload view"""
        response = requests.get(
            f"{BASE_URL}/api/cm-tools/workload",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Workload correctly forbidden for partner")
    
    def test_workload_case_structure(self, cm_token):
        """Verify case structure in workload response"""
        response = requests.get(
            f"{BASE_URL}/api/cm-tools/workload",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check if there are any cases in any category
        all_cases = data["overdue"] + data["due_today"] + data["action_needed"] + data["upcoming"] + data["on_track"]
        
        if len(all_cases) > 0:
            case = all_cases[0]
            assert "id" in case
            assert "case_id" in case
            assert "client_name" in case
            assert "product_name" in case
            assert "status" in case
            assert "priority" in case
            print(f"✓ Case structure verified: {case['case_id']} - {case['client_name']}")
        else:
            print("✓ No active cases found (structure check skipped)")


class TestCommunicationHub:
    """Phase 11B: Communication Hub tests (CM)"""
    
    def test_my_cases_summary(self, cm_token):
        """CM can get cases summary for communication"""
        response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert response.status_code == 200, f"Cases summary failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        if len(data) > 0:
            case = data[0]
            assert "id" in case
            assert "case_id" in case
            assert "client_name" in case
            assert "client_id" in case
            assert "product_name" in case
            assert "status" in case
            print(f"✓ Cases summary: {len(data)} active cases")
        else:
            print("✓ Cases summary: No active cases")
        return data
    
    def test_communications_get_for_case(self, cm_token):
        """CM can get communications for a case"""
        # First get a case
        cases_response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases available for communication test")
        
        case_id = cases[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/cm-tools/communications/{case_id}",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert response.status_code == 200, f"Get communications failed: {response.text}"
        data = response.json()
        
        assert "messages" in data
        assert "case_id" in data
        assert "client_name" in data
        assert isinstance(data["messages"], list)
        print(f"✓ Communications for case {data['case_id']}: {len(data['messages'])} messages")
    
    def test_send_message_to_client(self, cm_token):
        """CM can send message to client"""
        # First get a case
        cases_response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases available for message test")
        
        case = cases[0]
        response = requests.post(
            f"{BASE_URL}/api/cm-tools/communications/send",
            headers={"Authorization": f"Bearer {cm_token}"},
            json={
                "case_id": case["id"],
                "client_id": case["client_id"],
                "message": "TEST_MESSAGE: This is a test message from CM",
                "message_type": "text"
            }
        )
        assert response.status_code == 200, f"Send message failed: {response.text}"
        data = response.json()
        
        assert "message" in data
        assert "data" in data
        assert data["data"]["message"] == "TEST_MESSAGE: This is a test message from CM"
        print(f"✓ Message sent to client for case {case['case_id']}")
    
    def test_send_message_empty_fails(self, cm_token):
        """Empty message should fail"""
        cases_response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases available")
        
        case = cases[0]
        response = requests.post(
            f"{BASE_URL}/api/cm-tools/communications/send",
            headers={"Authorization": f"Bearer {cm_token}"},
            json={
                "case_id": case["id"],
                "client_id": case["client_id"],
                "message": "   ",  # Empty/whitespace
                "message_type": "text"
            }
        )
        assert response.status_code == 400, f"Expected 400 for empty message, got {response.status_code}"
        print("✓ Empty message correctly rejected")
    
    def test_unread_count(self, cm_token):
        """CM can get unread message count"""
        response = requests.get(
            f"{BASE_URL}/api/cm-tools/communications/unread-count",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert response.status_code == 200, f"Unread count failed: {response.text}"
        data = response.json()
        
        assert "count" in data
        assert isinstance(data["count"], int)
        print(f"✓ Unread message count: {data['count']}")
    
    def test_mark_messages_read(self, cm_token):
        """CM can mark messages as read"""
        cases_response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases available")
        
        case_id = cases[0]["id"]
        response = requests.put(
            f"{BASE_URL}/api/cm-tools/communications/{case_id}/mark-read",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        assert response.status_code == 200, f"Mark read failed: {response.text}"
        print("✓ Messages marked as read")


class TestBatchCaseOperations:
    """Phase 11C: Batch Case Operations tests (CM)"""
    
    def test_batch_operations_no_cases_fails(self, cm_token):
        """Batch operation with no cases should fail"""
        response = requests.post(
            f"{BASE_URL}/api/cm-tools/batch-operations",
            headers={"Authorization": f"Bearer {cm_token}"},
            json={
                "case_ids": [],
                "action": "add_note",
                "notes": "Test note"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Batch operation correctly rejected with no cases")
    
    def test_batch_add_note(self, cm_token):
        """CM can add note to multiple cases"""
        cases_response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases available for batch test")
        
        case_ids = [c["id"] for c in cases[:2]]  # Take up to 2 cases
        response = requests.post(
            f"{BASE_URL}/api/cm-tools/batch-operations",
            headers={"Authorization": f"Bearer {cm_token}"},
            json={
                "case_ids": case_ids,
                "action": "add_note",
                "notes": "TEST_BATCH_NOTE: Batch note from testing"
            }
        )
        assert response.status_code == 200, f"Batch add note failed: {response.text}"
        data = response.json()
        
        assert "success" in data
        assert "failed" in data
        assert data["success"] > 0
        print(f"✓ Batch add note: {data['success']} success, {data['failed']} failed")
    
    def test_batch_add_note_empty_fails(self, cm_token):
        """Batch add note with empty note should fail"""
        cases_response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases available")
        
        response = requests.post(
            f"{BASE_URL}/api/cm-tools/batch-operations",
            headers={"Authorization": f"Bearer {cm_token}"},
            json={
                "case_ids": [cases[0]["id"]],
                "action": "add_note",
                "notes": ""  # Empty note
            }
        )
        assert response.status_code == 200  # Returns 200 but with failed count
        data = response.json()
        assert data["failed"] > 0 or "empty" in str(data.get("errors", [])).lower()
        print("✓ Batch add note with empty note correctly handled")
    
    def test_batch_send_notification(self, cm_token):
        """CM can send notification to multiple clients"""
        cases_response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases available")
        
        case_ids = [c["id"] for c in cases[:2]]
        response = requests.post(
            f"{BASE_URL}/api/cm-tools/batch-operations",
            headers={"Authorization": f"Bearer {cm_token}"},
            json={
                "case_ids": case_ids,
                "action": "send_notification",
                "notes": "TEST_BATCH_NOTIFICATION: Important update for your case"
            }
        )
        assert response.status_code == 200, f"Batch notification failed: {response.text}"
        data = response.json()
        
        assert "success" in data
        print(f"✓ Batch notification: {data['success']} success, {data['failed']} failed")
    
    def test_batch_request_documents(self, cm_token):
        """CM can request documents from multiple clients"""
        cases_response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases available")
        
        case_ids = [c["id"] for c in cases[:2]]
        response = requests.post(
            f"{BASE_URL}/api/cm-tools/batch-operations",
            headers={"Authorization": f"Bearer {cm_token}"},
            json={
                "case_ids": case_ids,
                "action": "request_documents",
                "notes": "TEST_DOC_REQUEST: Please upload updated passport copy"
            }
        )
        assert response.status_code == 200, f"Batch doc request failed: {response.text}"
        data = response.json()
        
        assert "success" in data
        print(f"✓ Batch document request: {data['success']} success, {data['failed']} failed")
    
    def test_batch_change_status_invalid(self, cm_token):
        """Batch change status with invalid status should fail"""
        cases_response = requests.get(
            f"{BASE_URL}/api/cm-tools/my-cases-summary",
            headers={"Authorization": f"Bearer {cm_token}"}
        )
        cases = cases_response.json()
        
        if len(cases) == 0:
            pytest.skip("No cases available")
        
        response = requests.post(
            f"{BASE_URL}/api/cm-tools/batch-operations",
            headers={"Authorization": f"Bearer {cm_token}"},
            json={
                "case_ids": [cases[0]["id"]],
                "action": "change_status",
                "value": "invalid_status"
            }
        )
        assert response.status_code == 200  # Returns 200 but with failed count
        data = response.json()
        assert data["failed"] > 0
        print("✓ Batch change status with invalid status correctly handled")
    
    def test_batch_operations_forbidden_for_partner(self, partner_token):
        """Partner cannot perform batch operations"""
        response = requests.post(
            f"{BASE_URL}/api/cm-tools/batch-operations",
            headers={"Authorization": f"Bearer {partner_token}"},
            json={
                "case_ids": ["some-id"],
                "action": "add_note",
                "notes": "Test"
            }
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Batch operations correctly forbidden for partner")


class TestAccessControl:
    """Access control tests for all Phase 11 endpoints"""
    
    def test_cm_tools_require_auth(self):
        """CM tools endpoints require authentication"""
        endpoints = [
            ("GET", "/api/cm-tools/workload"),
            ("GET", "/api/cm-tools/my-cases-summary"),
            ("GET", "/api/cm-tools/communications/unread-count"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            
            assert response.status_code in [401, 403, 422], f"{endpoint} should require auth, got {response.status_code}"
        
        print("✓ All CM tools endpoints require authentication")
    
    def test_email_digest_require_auth(self):
        """Email digest endpoints require authentication"""
        endpoints = [
            ("GET", "/api/email-digest/preview"),
            ("POST", "/api/email-digest/send-now"),
            ("GET", "/api/email-digest/settings"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            
            assert response.status_code in [401, 403, 422], f"{endpoint} should require auth, got {response.status_code}"
        
        print("✓ All email digest endpoints require authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
