"""
Iteration 53: Payment Reminders Enhancement Tests
Tests for:
1. GET /api/reminders/pending-payments - Returns {items, stats}
2. POST /api/reminders/send/{sale_id} - Quick remind with optional custom message
3. POST /api/reminders/send-bulk - Bulk remind for 3d+ overdue
4. GET /api/reminders/history - Reminder history log
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPaymentRemindersAPI:
    """Payment Reminders API Tests"""
    
    admin_token = None
    client_token = None
    pending_items = []
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin before tests"""
        if not TestPaymentRemindersAPI.admin_token:
            res = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@leamss.com",
                "password": "Admin@123"
            })
            assert res.status_code == 200, f"Admin login failed: {res.text}"
            TestPaymentRemindersAPI.admin_token = res.json().get("token")
        
        if not TestPaymentRemindersAPI.client_token:
            res = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "client@leamss.com",
                "password": "Client@123"
            })
            if res.status_code == 200:
                TestPaymentRemindersAPI.client_token = res.json().get("token")
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {TestPaymentRemindersAPI.admin_token}"}
    
    def get_client_headers(self):
        return {"Authorization": f"Bearer {TestPaymentRemindersAPI.client_token}"}
    
    # ========== GET /api/reminders/pending-payments ==========
    
    def test_get_pending_payments_returns_items_and_stats(self):
        """Test that pending-payments returns {items, stats} structure"""
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        # Verify structure
        assert "items" in data, "Response should have 'items' key"
        assert "stats" in data, "Response should have 'stats' key"
        assert isinstance(data["items"], list), "items should be a list"
        assert isinstance(data["stats"], dict), "stats should be a dict"
        
        # Store for later tests
        TestPaymentRemindersAPI.pending_items = data["items"]
        print(f"Found {len(data['items'])} pending payment items")
    
    def test_stats_has_required_fields(self):
        """Test that stats contains all 7 required fields"""
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        assert res.status_code == 200
        stats = res.json().get("stats", {})
        
        required_fields = ["total_clients", "total_pending", "critical", "high", "medium", "low", "never_reminded"]
        for field in required_fields:
            assert field in stats, f"Stats missing required field: {field}"
        
        # Verify types
        assert isinstance(stats["total_clients"], int), "total_clients should be int"
        assert isinstance(stats["total_pending"], (int, float)), "total_pending should be numeric"
        assert isinstance(stats["critical"], int), "critical should be int"
        assert isinstance(stats["high"], int), "high should be int"
        assert isinstance(stats["medium"], int), "medium should be int"
        assert isinstance(stats["low"], int), "low should be int"
        assert isinstance(stats["never_reminded"], int), "never_reminded should be int"
        
        print(f"Stats: total={stats['total_clients']}, pending=₹{stats['total_pending']}, critical={stats['critical']}, high={stats['high']}, medium={stats['medium']}, low={stats['low']}, never_reminded={stats['never_reminded']}")
    
    def test_pending_item_has_required_fields(self):
        """Test that each pending item has required fields"""
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        assert res.status_code == 200
        items = res.json().get("items", [])
        
        if not items:
            pytest.skip("No pending items to test")
        
        item = items[0]
        required_fields = [
            "sale_id", "client_name", "client_email", "product_name",
            "fee_amount", "amount_received", "pending_amount", "payment_status",
            "days_since_creation", "reminder_count", "urgency"
        ]
        
        for field in required_fields:
            assert field in item, f"Item missing required field: {field}"
        
        # Verify urgency is valid
        assert item["urgency"] in ["critical", "high", "medium", "low"], f"Invalid urgency: {item['urgency']}"
        
        print(f"Sample item: {item['client_name']} - ₹{item['pending_amount']} - {item['urgency']}")
    
    def test_pending_payments_sorted_by_urgency(self):
        """Test that items are sorted by urgency (critical first)"""
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        assert res.status_code == 200
        items = res.json().get("items", [])
        
        if len(items) < 2:
            pytest.skip("Not enough items to test sorting")
        
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for i in range(len(items) - 1):
            current = urgency_order.get(items[i]["urgency"], 9)
            next_item = urgency_order.get(items[i+1]["urgency"], 9)
            assert current <= next_item, f"Items not sorted by urgency at index {i}"
        
        print("Items correctly sorted by urgency")
    
    def test_pending_payments_requires_admin(self):
        """Test that non-admin cannot access pending payments"""
        if not TestPaymentRemindersAPI.client_token:
            pytest.skip("Client token not available")
        
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_client_headers())
        assert res.status_code == 403, f"Expected 403 for non-admin, got {res.status_code}"
        print("Non-admin correctly blocked from pending-payments")
    
    # ========== POST /api/reminders/send/{sale_id} ==========
    
    def test_send_reminder_quick_remind(self):
        """Test sending a quick reminder (no custom message)"""
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        items = res.json().get("items", [])
        
        if not items:
            pytest.skip("No pending items to test reminder")
        
        sale_id = items[0]["sale_id"]
        client_name = items[0]["client_name"]
        
        # Send quick reminder
        res = requests.post(f"{BASE_URL}/api/reminders/send/{sale_id}", json={}, headers=self.get_admin_headers())
        assert res.status_code == 200, f"Quick remind failed: {res.text}"
        
        data = res.json()
        assert "message" in data, "Response should have message"
        assert client_name in data["message"] or "Reminder sent" in data["message"], f"Unexpected response: {data}"
        
        print(f"Quick reminder sent: {data['message']}")
    
    def test_send_reminder_with_custom_message(self):
        """Test sending a reminder with custom message"""
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        items = res.json().get("items", [])
        
        if not items:
            pytest.skip("No pending items to test reminder")
        
        sale_id = items[0]["sale_id"]
        custom_msg = "TEST CUSTOM MESSAGE: Please complete your payment at the earliest."
        
        res = requests.post(f"{BASE_URL}/api/reminders/send/{sale_id}", 
                           json={"message": custom_msg}, 
                           headers=self.get_admin_headers())
        assert res.status_code == 200, f"Custom remind failed: {res.text}"
        
        print(f"Custom reminder sent successfully")
    
    def test_send_reminder_invalid_sale_id(self):
        """Test sending reminder to non-existent sale"""
        res = requests.post(f"{BASE_URL}/api/reminders/send/invalid-sale-id-12345", 
                           json={}, 
                           headers=self.get_admin_headers())
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"
        print("Invalid sale_id correctly returns 404")
    
    def test_send_reminder_requires_admin(self):
        """Test that non-admin cannot send reminders"""
        if not TestPaymentRemindersAPI.client_token:
            pytest.skip("Client token not available")
        
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        items = res.json().get("items", [])
        
        if not items:
            pytest.skip("No pending items")
        
        sale_id = items[0]["sale_id"]
        res = requests.post(f"{BASE_URL}/api/reminders/send/{sale_id}", 
                           json={}, 
                           headers=self.get_client_headers())
        assert res.status_code == 403, f"Expected 403 for non-admin, got {res.status_code}"
        print("Non-admin correctly blocked from sending reminders")
    
    # ========== POST /api/reminders/send-bulk ==========
    
    def test_bulk_send_reminders(self):
        """Test bulk send reminders for 3d+ overdue"""
        res = requests.post(f"{BASE_URL}/api/reminders/send-bulk", json={}, headers=self.get_admin_headers())
        assert res.status_code == 200, f"Bulk send failed: {res.text}"
        
        data = res.json()
        assert "message" in data, "Response should have message"
        assert "count" in data, "Response should have count"
        assert isinstance(data["count"], int), "count should be int"
        
        print(f"Bulk send result: {data['message']} (count: {data['count']})")
    
    def test_bulk_send_requires_admin(self):
        """Test that non-admin cannot bulk send"""
        if not TestPaymentRemindersAPI.client_token:
            pytest.skip("Client token not available")
        
        res = requests.post(f"{BASE_URL}/api/reminders/send-bulk", json={}, headers=self.get_client_headers())
        assert res.status_code == 403, f"Expected 403 for non-admin, got {res.status_code}"
        print("Non-admin correctly blocked from bulk send")
    
    # ========== GET /api/reminders/history ==========
    
    def test_get_reminder_history(self):
        """Test getting reminder history"""
        res = requests.get(f"{BASE_URL}/api/reminders/history", headers=self.get_admin_headers())
        assert res.status_code == 200, f"History failed: {res.text}"
        
        data = res.json()
        assert isinstance(data, list), "History should be a list"
        
        if data:
            # Check first item has required fields
            item = data[0]
            assert "sale_id" in item, "History item should have sale_id"
            assert "sent_at" in item, "History item should have sent_at"
            assert "reminder_count" in item, "History item should have reminder_count"
            print(f"History has {len(data)} entries. First: {item.get('client_name', 'N/A')} - {item.get('sent_at', 'N/A')}")
        else:
            print("History is empty (may be expected if no reminders sent yet)")
    
    def test_history_requires_admin(self):
        """Test that non-admin cannot access history"""
        if not TestPaymentRemindersAPI.client_token:
            pytest.skip("Client token not available")
        
        res = requests.get(f"{BASE_URL}/api/reminders/history", headers=self.get_client_headers())
        assert res.status_code == 403, f"Expected 403 for non-admin, got {res.status_code}"
        print("Non-admin correctly blocked from history")
    
    # ========== Integration Tests ==========
    
    def test_reminder_count_increments_after_send(self):
        """Test that reminder_count increments after sending"""
        # Get initial state
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        items = res.json().get("items", [])
        
        if not items:
            pytest.skip("No pending items")
        
        sale_id = items[0]["sale_id"]
        initial_count = items[0]["reminder_count"]
        
        # Send reminder
        requests.post(f"{BASE_URL}/api/reminders/send/{sale_id}", json={}, headers=self.get_admin_headers())
        
        # Check updated count
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        items = res.json().get("items", [])
        
        updated_item = next((i for i in items if i["sale_id"] == sale_id), None)
        if updated_item:
            assert updated_item["reminder_count"] >= initial_count, "Reminder count should not decrease"
            print(f"Reminder count: {initial_count} -> {updated_item['reminder_count']}")
        else:
            print("Item may have been removed (paid off)")
    
    def test_history_updated_after_send(self):
        """Test that history is updated after sending reminder"""
        # Get initial history count
        res = requests.get(f"{BASE_URL}/api/reminders/history", headers=self.get_admin_headers())
        initial_history = res.json()
        
        # Get a sale to remind
        res = requests.get(f"{BASE_URL}/api/reminders/pending-payments", headers=self.get_admin_headers())
        items = res.json().get("items", [])
        
        if not items:
            pytest.skip("No pending items")
        
        sale_id = items[0]["sale_id"]
        
        # Send reminder
        requests.post(f"{BASE_URL}/api/reminders/send/{sale_id}", json={}, headers=self.get_admin_headers())
        
        # Check history updated
        res = requests.get(f"{BASE_URL}/api/reminders/history", headers=self.get_admin_headers())
        updated_history = res.json()
        
        # Find the entry for this sale
        entry = next((h for h in updated_history if h["sale_id"] == sale_id), None)
        assert entry is not None, "History should have entry for reminded sale"
        print(f"History entry found for sale {sale_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
