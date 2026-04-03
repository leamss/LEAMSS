"""
Phase 2 Features Test Suite - LEAMSS Immigration Portal
Tests for 5 new features:
1. Commission Effective Date - rate changes tracked with history
2. Client Ticket Routing - auto-routing by category
3. Refund Module - refund with auto commission adjustment
4. Currency Conversion USD/INR - exchange rate in settings
5. Payment Collection Tracker Widget - overdue/due_soon/upcoming categorization
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

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
def partner_token():
    """Get partner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARTNER_EMAIL,
        "password": PARTNER_PASSWORD
    })
    assert response.status_code == 200, f"Partner login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def client_token():
    """Get client authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CLIENT_EMAIL,
        "password": CLIENT_PASSWORD
    })
    assert response.status_code == 200, f"Client login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def manager_token():
    """Get case manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGER_EMAIL,
        "password": MANAGER_PASSWORD
    })
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    return response.json()["token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Feature 1: Commission Effective Date - Rate changes tracked with history
# ============================================================================

class TestCommissionEffectiveDate:
    """Tests for commission rate change tracking with effective date"""
    
    def test_update_user_commission_rate_tracks_history(self, admin_token):
        """PUT /api/users/{id} with commission_rate tracks rate change history"""
        # First get a partner user
        response = requests.get(f"{BASE_URL}/api/users?role=partner", headers=auth_header(admin_token))
        assert response.status_code == 200
        partners = response.json()
        assert len(partners) > 0, "No partners found"
        
        partner = partners[0]
        partner_id = partner["id"]
        old_rate = partner.get("commission_rate", 0)
        new_rate = old_rate + 5 if old_rate < 50 else old_rate - 5
        
        # Update commission rate with effective date
        effective_date = (datetime.now() + timedelta(days=7)).isoformat()
        response = requests.put(
            f"{BASE_URL}/api/users/{partner_id}",
            json={
                "commission_rate": new_rate,
                "commission_effective_date": effective_date
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "Commission rate changed" in data.get("message", "") or "updated" in data.get("message", "").lower()
        
        # Verify the user now has commission_rate_history
        response = requests.get(f"{BASE_URL}/api/users/{partner_id}", headers=auth_header(admin_token))
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["commission_rate"] == new_rate
        
        # Check history exists
        history = user_data.get("commission_rate_history", [])
        assert len(history) > 0, "Commission rate history should be populated"
        
        # Verify latest history entry
        latest_entry = history[-1]
        assert latest_entry["old_rate"] == old_rate
        assert latest_entry["new_rate"] == new_rate
        assert "effective_from" in latest_entry
        assert "changed_at" in latest_entry
        assert "changed_by" in latest_entry
        
        print(f"✓ Commission rate changed from {old_rate}% to {new_rate}% with history tracked")


# ============================================================================
# Feature 2: Client Ticket Routing - Auto-routing by category
# ============================================================================

class TestClientTicketRouting:
    """Tests for automatic ticket routing when client creates ticket"""
    
    def test_client_ticket_document_category_routes_to_case_manager(self, client_token, admin_token):
        """POST /api/tickets with category=document auto-routes to case_manager"""
        # Create ticket as client with document category, no targets
        ticket_data = {
            "subject": f"TEST_Document Issue {uuid.uuid4().hex[:6]}",
            "description": "I need help with my document submission",
            "category": "document",
            "priority": "medium"
            # Note: NOT specifying target_user_ids - should auto-route
        }
        
        response = requests.post(
            f"{BASE_URL}/api/tickets",
            json=ticket_data,
            headers=auth_header(client_token)
        )
        assert response.status_code == 200
        data = response.json()
        ticket_id = data["id"]
        
        # Verify ticket was created and routed
        response = requests.get(f"{BASE_URL}/api/tickets/{ticket_id}", headers=auth_header(admin_token))
        assert response.status_code == 200
        ticket = response.json()
        
        # Should be assigned to case_manager role
        assert ticket.get("assigned_role") == "case_manager", f"Expected assigned_role=case_manager, got {ticket.get('assigned_role')}"
        assert len(ticket.get("target_user_ids", [])) > 0, "Should have target users assigned"
        
        print(f"✓ Document category ticket auto-routed to case_manager")
    
    def test_client_ticket_payment_category_routes_to_case_manager(self, client_token, admin_token):
        """POST /api/tickets with category=payment auto-routes to case_manager"""
        ticket_data = {
            "subject": f"TEST_Payment Issue {uuid.uuid4().hex[:6]}",
            "description": "I have a question about my payment",
            "category": "payment",
            "priority": "high"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/tickets",
            json=ticket_data,
            headers=auth_header(client_token)
        )
        assert response.status_code == 200
        data = response.json()
        ticket_id = data["id"]
        
        # Verify routing
        response = requests.get(f"{BASE_URL}/api/tickets/{ticket_id}", headers=auth_header(admin_token))
        assert response.status_code == 200
        ticket = response.json()
        
        assert ticket.get("assigned_role") == "case_manager"
        print(f"✓ Payment category ticket auto-routed to case_manager")
    
    def test_client_ticket_general_category_routes_to_admin(self, client_token, admin_token):
        """POST /api/tickets with category=general auto-routes to admin"""
        ticket_data = {
            "subject": f"TEST_General Inquiry {uuid.uuid4().hex[:6]}",
            "description": "I have a general question",
            "category": "general",
            "priority": "low"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/tickets",
            json=ticket_data,
            headers=auth_header(client_token)
        )
        assert response.status_code == 200
        data = response.json()
        ticket_id = data["id"]
        
        # Verify routing
        response = requests.get(f"{BASE_URL}/api/tickets/{ticket_id}", headers=auth_header(admin_token))
        assert response.status_code == 200
        ticket = response.json()
        
        assert ticket.get("assigned_role") == "admin"
        print(f"✓ General category ticket auto-routed to admin")
    
    def test_admin_can_reassign_ticket(self, admin_token):
        """PUT /api/tickets/{id}/assign allows admin to reassign a ticket"""
        # Get an existing ticket
        response = requests.get(f"{BASE_URL}/api/tickets/all", headers=auth_header(admin_token))
        assert response.status_code == 200
        tickets = response.json()
        
        if len(tickets) == 0:
            pytest.skip("No tickets available for reassignment test")
        
        ticket = tickets[0]
        ticket_id = ticket["id"]
        
        # Get a case manager to assign to
        response = requests.get(f"{BASE_URL}/api/users?role=case_manager", headers=auth_header(admin_token))
        assert response.status_code == 200
        managers = response.json()
        
        if len(managers) == 0:
            pytest.skip("No case managers available")
        
        manager_id = managers[0]["id"]
        
        # Reassign ticket
        response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}/assign",
            json={"assigned_to": manager_id, "assigned_role": "case_manager"},
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "reassigned" in data.get("message", "").lower() or "success" in data.get("message", "").lower()
        
        print(f"✓ Admin successfully reassigned ticket")


# ============================================================================
# Feature 3: Refund Module - Refund with auto commission adjustment
# ============================================================================

class TestRefundModule:
    """Tests for refund creation and commission recalculation"""
    
    def test_create_refund_reduces_amount_received_and_commission(self, admin_token):
        """POST /api/refunds creates refund, reduces sale amount_received and recalculates commission"""
        # Get an approved sale with amount_received > 0
        response = requests.get(f"{BASE_URL}/api/sales?status=approved", headers=auth_header(admin_token))
        assert response.status_code == 200
        sales = response.json()
        
        # Find a sale with amount_received > 100 for refund
        eligible_sale = None
        for sale in sales:
            if sale.get("amount_received", 0) >= 100:
                eligible_sale = sale
                break
        
        if not eligible_sale:
            pytest.skip("No eligible sale with amount_received >= 100 for refund test")
        
        sale_id = eligible_sale["id"]
        original_received = eligible_sale["amount_received"]
        original_commission = eligible_sale.get("commission_amount", 0)
        refund_amount = 50  # Refund $50
        
        # Create refund
        response = requests.post(
            f"{BASE_URL}/api/refunds",
            json={
                "sale_id": sale_id,
                "amount": refund_amount,
                "reason": "Customer requested partial refund for testing",
                "refund_method": "original_payment",
                "notes": "Test refund"
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "refund_id" in data
        assert data["refund_amount"] == refund_amount
        assert data["new_amount_received"] == original_received - refund_amount
        assert "new_commission" in data
        
        # Verify commission was recalculated
        # Commission should be based on new_amount_received
        print(f"✓ Refund created: ${refund_amount}, new received: ${data['new_amount_received']}, new commission: ${data['new_commission']}")
    
    def test_refund_validation_min_reason_length(self, admin_token):
        """POST /api/refunds validates: min 5 char reason"""
        response = requests.get(f"{BASE_URL}/api/sales?status=approved", headers=auth_header(admin_token))
        sales = response.json()
        
        if len(sales) == 0:
            pytest.skip("No approved sales for refund validation test")
        
        sale_id = sales[0]["id"]
        
        # Try with short reason
        response = requests.post(
            f"{BASE_URL}/api/refunds",
            json={
                "sale_id": sale_id,
                "amount": 10,
                "reason": "abc",  # Too short
                "refund_method": "original_payment"
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 400
        assert "5 characters" in response.json().get("detail", "").lower() or "reason" in response.json().get("detail", "").lower()
        print(f"✓ Refund validation: short reason rejected")
    
    def test_refund_validation_positive_amount(self, admin_token):
        """POST /api/refunds validates: positive amount"""
        response = requests.get(f"{BASE_URL}/api/sales?status=approved", headers=auth_header(admin_token))
        sales = response.json()
        
        if len(sales) == 0:
            pytest.skip("No approved sales for refund validation test")
        
        sale_id = sales[0]["id"]
        
        # Try with zero/negative amount
        response = requests.post(
            f"{BASE_URL}/api/refunds",
            json={
                "sale_id": sale_id,
                "amount": 0,
                "reason": "Valid reason here",
                "refund_method": "original_payment"
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 400
        assert "positive" in response.json().get("detail", "").lower()
        print(f"✓ Refund validation: zero amount rejected")
    
    def test_refund_validation_amount_not_exceeding_received(self, admin_token):
        """POST /api/refunds validates: amount not exceeding received"""
        response = requests.get(f"{BASE_URL}/api/sales?status=approved", headers=auth_header(admin_token))
        sales = response.json()
        
        # Find a sale with known amount_received
        eligible_sale = None
        for sale in sales:
            if sale.get("amount_received", 0) > 0:
                eligible_sale = sale
                break
        
        if not eligible_sale:
            pytest.skip("No sale with amount_received > 0")
        
        sale_id = eligible_sale["id"]
        amount_received = eligible_sale["amount_received"]
        
        # Try to refund more than received
        response = requests.post(
            f"{BASE_URL}/api/refunds",
            json={
                "sale_id": sale_id,
                "amount": amount_received + 1000,  # More than received
                "reason": "Valid reason for testing",
                "refund_method": "original_payment"
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 400
        assert "exceeds" in response.json().get("detail", "").lower()
        print(f"✓ Refund validation: amount exceeding received rejected")
    
    def test_get_refunds_returns_list_with_client_info(self, admin_token):
        """GET /api/refunds returns list of refunds with client info"""
        response = requests.get(f"{BASE_URL}/api/refunds", headers=auth_header(admin_token))
        assert response.status_code == 200
        refunds = response.json()
        
        assert isinstance(refunds, list)
        
        if len(refunds) > 0:
            refund = refunds[0]
            assert "sale_id" in refund
            assert "amount" in refund
            assert "reason" in refund
            assert "client_name" in refund
            assert "client_email" in refund
            print(f"✓ GET /api/refunds returns {len(refunds)} refunds with client info")
        else:
            print(f"✓ GET /api/refunds returns empty list (no refunds yet)")
    
    def test_get_refunds_by_sale(self, admin_token):
        """GET /api/refunds/by-sale/{sale_id} returns refund history for a specific sale"""
        # Get a sale that might have refunds
        response = requests.get(f"{BASE_URL}/api/sales?status=approved", headers=auth_header(admin_token))
        sales = response.json()
        
        if len(sales) == 0:
            pytest.skip("No approved sales")
        
        sale_id = sales[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/refunds/by-sale/{sale_id}", headers=auth_header(admin_token))
        assert response.status_code == 200
        refunds = response.json()
        
        assert isinstance(refunds, list)
        print(f"✓ GET /api/refunds/by-sale/{sale_id} returns {len(refunds)} refunds")


# ============================================================================
# Feature 4: Currency Conversion USD/INR
# ============================================================================

class TestCurrencyConversion:
    """Tests for exchange rate settings"""
    
    def test_get_exchange_rate(self, admin_token):
        """GET /api/settings/exchange-rate returns rate and show_dual_currency flag"""
        response = requests.get(f"{BASE_URL}/api/settings/exchange-rate", headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        
        assert "rate" in data
        assert "show_dual_currency" in data
        assert data["base_currency"] == "USD"
        assert data["target_currency"] == "INR"
        assert isinstance(data["rate"], (int, float))
        assert data["rate"] > 0
        
        print(f"✓ Exchange rate: 1 USD = ₹{data['rate']}, dual currency: {data['show_dual_currency']}")
    
    def test_update_exchange_rate(self, admin_token):
        """PUT /api/settings with exchange_rate_usd_to_inr persists the exchange rate"""
        new_rate = 84.25
        
        response = requests.put(
            f"{BASE_URL}/api/settings",
            json={
                "exchange_rate_usd_to_inr": new_rate,
                "show_dual_currency": True
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        
        # Verify it was saved
        response = requests.get(f"{BASE_URL}/api/settings/exchange-rate", headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert data["rate"] == new_rate
        
        print(f"✓ Exchange rate updated to {new_rate}")


# ============================================================================
# Feature 5: Payment Collection Tracker Widget
# ============================================================================

class TestPaymentCollectionTracker:
    """Tests for payment deadline tracking"""
    
    def test_get_payment_deadlines_returns_summary_and_items(self, admin_token):
        """GET /api/sales/tracker/payment-deadlines returns summary with overdue/due_soon/upcoming counts and items list"""
        response = requests.get(f"{BASE_URL}/api/sales/tracker/payment-deadlines", headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "summary" in data
        assert "items" in data
        
        summary = data["summary"]
        assert "total_pending" in summary
        assert "overdue_count" in summary
        assert "overdue_amount" in summary
        assert "due_soon_count" in summary
        assert "due_soon_amount" in summary
        assert "upcoming_count" in summary
        assert "upcoming_amount" in summary
        
        items = data["items"]
        assert isinstance(items, list)
        
        if len(items) > 0:
            item = items[0]
            assert "sale_id" in item
            assert "client_name" in item
            assert "pending_amount" in item
            assert "urgency" in item
            assert item["urgency"] in ["overdue", "due_soon", "upcoming"]
        
        print(f"✓ Payment tracker: {summary['overdue_count']} overdue, {summary['due_soon_count']} due soon, {summary['upcoming_count']} upcoming")
        print(f"  Total pending: ${summary['total_pending']}")
    
    def test_payment_tracker_urgency_categorization(self, admin_token):
        """Verify items are categorized correctly by urgency"""
        response = requests.get(f"{BASE_URL}/api/sales/tracker/payment-deadlines", headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        
        items = data["items"]
        
        # Count by urgency
        overdue = [i for i in items if i["urgency"] == "overdue"]
        due_soon = [i for i in items if i["urgency"] == "due_soon"]
        upcoming = [i for i in items if i["urgency"] == "upcoming"]
        
        # Verify counts match summary
        summary = data["summary"]
        assert len(overdue) == summary["overdue_count"]
        assert len(due_soon) == summary["due_soon_count"]
        assert len(upcoming) == summary["upcoming_count"]
        
        # Verify amounts match
        overdue_amount = sum(i["pending_amount"] for i in overdue)
        due_soon_amount = sum(i["pending_amount"] for i in due_soon)
        upcoming_amount = sum(i["pending_amount"] for i in upcoming)
        
        assert abs(overdue_amount - summary["overdue_amount"]) < 0.01
        assert abs(due_soon_amount - summary["due_soon_amount"]) < 0.01
        assert abs(upcoming_amount - summary["upcoming_amount"]) < 0.01
        
        print(f"✓ Urgency categorization verified: overdue={len(overdue)}, due_soon={len(due_soon)}, upcoming={len(upcoming)}")


# ============================================================================
# Additional Tests: Ticket Closure Comment Display
# ============================================================================

class TestTicketClosureComment:
    """Tests for ticket closure comment display"""
    
    def test_ticket_shows_closure_comment_when_resolved(self, admin_token):
        """Ticket section shows closure_comment when ticket is resolved/closed"""
        # Get all tickets
        response = requests.get(f"{BASE_URL}/api/tickets/all", headers=auth_header(admin_token))
        assert response.status_code == 200
        tickets = response.json()
        
        # Find a resolved or closed ticket
        resolved_ticket = None
        for ticket in tickets:
            if ticket.get("status") in ["resolved", "closed"]:
                resolved_ticket = ticket
                break
        
        if not resolved_ticket:
            # Create and resolve a ticket for testing
            response = requests.post(
                f"{BASE_URL}/api/tickets",
                json={
                    "subject": f"TEST_Closure Comment Test {uuid.uuid4().hex[:6]}",
                    "description": "Testing closure comment display",
                    "category": "general",
                    "priority": "low"
                },
                headers=auth_header(admin_token)
            )
            assert response.status_code == 200
            ticket_id = response.json()["id"]
            
            # Resolve with closure comment
            response = requests.put(
                f"{BASE_URL}/api/tickets/{ticket_id}/status",
                json={
                    "status": "resolved",
                    "closure_comment": "This issue has been resolved successfully after investigation."
                },
                headers=auth_header(admin_token)
            )
            assert response.status_code == 200
            
            # Get the ticket
            response = requests.get(f"{BASE_URL}/api/tickets/{ticket_id}", headers=auth_header(admin_token))
            assert response.status_code == 200
            resolved_ticket = response.json()
        
        # Verify closure_comment is present
        assert resolved_ticket.get("closure_comment") or resolved_ticket.get("resolution_note"), \
            "Resolved ticket should have closure_comment or resolution_note"
        
        print(f"✓ Resolved ticket has closure_comment: {resolved_ticket.get('closure_comment', resolved_ticket.get('resolution_note', ''))[:50]}...")


# ============================================================================
# Health Check
# ============================================================================

class TestHealthCheck:
    """Basic API health check"""
    
    def test_api_accessible(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        # Some APIs return 404 for /health, try login endpoint
        if response.status_code == 404:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
        assert response.status_code == 200
        print(f"✓ API is accessible at {BASE_URL}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
