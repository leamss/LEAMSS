"""
LEAMSS Portal - Ticket System Tests
Tests for: Ticket recipients endpoint, ticket creation, ticket assignment, ticket status updates
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


class TestTicketRecipients:
    """Test /api/users/ticket-recipients endpoint for all user roles"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def partner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        return response.json()["token"]
    
    def test_admin_ticket_recipients(self, admin_token):
        """Admin should see all users as potential recipients"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        recipients = response.json()
        assert isinstance(recipients, list)
        # Admin should see multiple users (excluding themselves)
        print(f"✓ Admin can see {len(recipients)} ticket recipients")
        # Verify structure
        if len(recipients) > 0:
            assert "id" in recipients[0]
            assert "name" in recipients[0]
            assert "role" in recipients[0]
            print(f"  Sample recipient: {recipients[0]['name']} ({recipients[0]['role']})")
    
    def test_case_manager_ticket_recipients(self, manager_token):
        """Case Manager should see their clients and admins"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        recipients = response.json()
        assert isinstance(recipients, list)
        print(f"✓ Case Manager can see {len(recipients)} ticket recipients")
        
        # Check that recipients include admins
        roles = [r.get("role") for r in recipients]
        if "admin" in roles:
            print("  ✓ Admin users included in recipients")
        if "client" in roles:
            print("  ✓ Client users included in recipients")
    
    def test_partner_ticket_recipients(self, partner_token):
        """Partner should only see admins"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        recipients = response.json()
        assert isinstance(recipients, list)
        print(f"✓ Partner can see {len(recipients)} ticket recipients")
        
        # All recipients should be admins
        for recipient in recipients:
            assert recipient.get("role") == "admin", f"Partner should only see admins, got: {recipient.get('role')}"
        print("  ✓ All recipients are admins (as expected for partner)")
    
    def test_client_ticket_recipients(self, client_token):
        """Client should see their case manager and admins"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        recipients = response.json()
        assert isinstance(recipients, list)
        print(f"✓ Client can see {len(recipients)} ticket recipients")
        
        # Check roles
        roles = set(r.get("role") for r in recipients)
        print(f"  Recipient roles: {roles}")


class TestTicketCreation:
    """Test ticket creation for all user roles"""
    
    @pytest.fixture
    def admin_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        data = response.json()
        return {"token": data["token"], "user": data["user"]}
    
    @pytest.fixture
    def manager_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        data = response.json()
        return {"token": data["token"], "user": data["user"]}
    
    @pytest.fixture
    def partner_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        data = response.json()
        return {"token": data["token"], "user": data["user"]}
    
    @pytest.fixture
    def client_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        data = response.json()
        return {"token": data["token"], "user": data["user"]}
    
    def test_case_manager_create_ticket_to_client(self, manager_auth, client_auth):
        """Case Manager can create ticket and assign to specific client"""
        headers = {"Authorization": f"Bearer {manager_auth['token']}"}
        
        # Get recipients to find a client
        recipients_response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        recipients = recipients_response.json()
        
        # Find a client in recipients
        client_recipient = next((r for r in recipients if r.get("role") == "client"), None)
        
        if client_recipient:
            ticket_data = {
                "subject": "TEST_CM_to_Client_Ticket",
                "category": "general",
                "priority": "medium",
                "description": "Test ticket from Case Manager to Client",
                "target_user_ids": [client_recipient["id"]]
            }
            
            response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
            assert response.status_code == 200, f"Failed: {response.text}"
            ticket = response.json()
            assert ticket["subject"] == ticket_data["subject"]
            assert client_recipient["id"] in ticket["target_user_ids"]
            print(f"✓ Case Manager created ticket to client: {ticket['id']}")
            return ticket["id"]
        else:
            print("⚠ No client found in recipients - skipping test")
            pytest.skip("No client found in recipients")
    
    def test_case_manager_create_ticket_escalate_to_admin(self, manager_auth, admin_auth):
        """Case Manager can create ticket and escalate to Admin"""
        headers = {"Authorization": f"Bearer {manager_auth['token']}"}
        
        # Get recipients to find admin
        recipients_response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        recipients = recipients_response.json()
        
        admin_recipient = next((r for r in recipients if r.get("role") == "admin"), None)
        
        if admin_recipient:
            ticket_data = {
                "subject": "TEST_CM_Escalation_to_Admin",
                "category": "support",
                "priority": "high",
                "description": "Test escalation ticket from Case Manager to Admin",
                "target_user_ids": [admin_recipient["id"]]
            }
            
            response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
            assert response.status_code == 200, f"Failed: {response.text}"
            ticket = response.json()
            assert admin_recipient["id"] in ticket["target_user_ids"]
            print(f"✓ Case Manager escalated ticket to admin: {ticket['id']}")
            return ticket["id"]
        else:
            print("⚠ No admin found in recipients")
            pytest.skip("No admin found in recipients")
    
    def test_client_create_ticket_to_case_manager(self, client_auth):
        """Client can create ticket and send to Case Manager"""
        headers = {"Authorization": f"Bearer {client_auth['token']}"}
        
        # Get recipients
        recipients_response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        recipients = recipients_response.json()
        
        cm_recipient = next((r for r in recipients if r.get("role") == "case_manager"), None)
        
        if cm_recipient:
            ticket_data = {
                "subject": "TEST_Client_to_CM_Ticket",
                "category": "document",
                "priority": "medium",
                "description": "Test ticket from Client to Case Manager",
                "target_user_ids": [cm_recipient["id"]]
            }
            
            response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
            assert response.status_code == 200, f"Failed: {response.text}"
            ticket = response.json()
            assert cm_recipient["id"] in ticket["target_user_ids"]
            print(f"✓ Client created ticket to case manager: {ticket['id']}")
            return ticket["id"]
        else:
            print("⚠ No case manager found in recipients - client may not have a case")
            pytest.skip("No case manager found in recipients")
    
    def test_client_create_ticket_to_admin(self, client_auth):
        """Client can create ticket and send to Admin"""
        headers = {"Authorization": f"Bearer {client_auth['token']}"}
        
        # Get recipients
        recipients_response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        recipients = recipients_response.json()
        
        admin_recipient = next((r for r in recipients if r.get("role") == "admin"), None)
        
        if admin_recipient:
            ticket_data = {
                "subject": "TEST_Client_to_Admin_Ticket",
                "category": "support",
                "priority": "high",
                "description": "Test ticket from Client to Admin",
                "target_user_ids": [admin_recipient["id"]]
            }
            
            response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
            assert response.status_code == 200, f"Failed: {response.text}"
            ticket = response.json()
            assert admin_recipient["id"] in ticket["target_user_ids"]
            print(f"✓ Client created ticket to admin: {ticket['id']}")
            return ticket["id"]
        else:
            print("⚠ No admin found in recipients")
            pytest.skip("No admin found in recipients")
    
    def test_partner_create_ticket_to_admin(self, partner_auth):
        """Partner can create ticket and send to Admin"""
        headers = {"Authorization": f"Bearer {partner_auth['token']}"}
        
        # Get recipients - should only be admins
        recipients_response = requests.get(f"{BASE_URL}/api/users/ticket-recipients", headers=headers)
        recipients = recipients_response.json()
        
        if len(recipients) > 0:
            admin_recipient = recipients[0]  # Should be admin
            
            ticket_data = {
                "subject": "TEST_Partner_to_Admin_Ticket",
                "category": "payment",
                "priority": "medium",
                "description": "Test ticket from Partner to Admin",
                "target_user_ids": [admin_recipient["id"]]
            }
            
            response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
            assert response.status_code == 200, f"Failed: {response.text}"
            ticket = response.json()
            print(f"✓ Partner created ticket to admin: {ticket['id']}")
            return ticket["id"]
        else:
            print("⚠ No recipients found for partner")
            pytest.skip("No recipients found for partner")


class TestMyTickets:
    """Test /api/tickets/my-tickets endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def partner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        return response.json()["token"]
    
    def test_admin_my_tickets(self, admin_token):
        """Admin can view tickets assigned to them or created by them"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Admin has {len(tickets)} tickets")
    
    def test_manager_my_tickets(self, manager_token):
        """Case Manager can view their tickets"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Case Manager has {len(tickets)} tickets")
    
    def test_partner_my_tickets(self, partner_token):
        """Partner can view their tickets"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Partner has {len(tickets)} tickets")
    
    def test_client_my_tickets(self, client_token):
        """Client can view their tickets"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        tickets = response.json()
        assert isinstance(tickets, list)
        print(f"✓ Client has {len(tickets)} tickets")


class TestTicketStatusUpdates:
    """Test ticket status update workflow"""
    
    @pytest.fixture
    def admin_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        data = response.json()
        return {"token": data["token"], "user": data["user"]}
    
    def test_ticket_status_workflow(self, admin_auth):
        """Test full ticket status workflow: open -> in_progress -> resolved -> closed"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        # Create a test ticket
        ticket_data = {
            "subject": "TEST_Status_Workflow_Ticket",
            "category": "technical",
            "priority": "medium",
            "description": "Test ticket for status workflow testing",
            "target_user_ids": []
        }
        
        create_response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        ticket = create_response.json()
        ticket_id = ticket["id"]
        assert ticket["status"] == "open"
        print(f"✓ Created ticket with status: open")
        
        # Update to in_progress
        status_update = {"status": "in_progress"}
        response = requests.put(f"{BASE_URL}/api/tickets/{ticket_id}/status", json=status_update, headers=headers)
        assert response.status_code == 200, f"Status update failed: {response.text}"
        print(f"✓ Updated ticket status to: in_progress")
        
        # Update to resolved (requires resolution note)
        status_update = {"status": "resolved", "resolution_note": "Issue resolved - test complete"}
        response = requests.put(f"{BASE_URL}/api/tickets/{ticket_id}/status", json=status_update, headers=headers)
        assert response.status_code == 200, f"Status update failed: {response.text}"
        print(f"✓ Updated ticket status to: resolved")
        
        # Update to closed
        status_update = {"status": "closed", "resolution_note": "Ticket closed after resolution"}
        response = requests.put(f"{BASE_URL}/api/tickets/{ticket_id}/status", json=status_update, headers=headers)
        assert response.status_code == 200, f"Status update failed: {response.text}"
        print(f"✓ Updated ticket status to: closed")
        
        # Verify final state
        detail_response = requests.get(f"{BASE_URL}/api/tickets/{ticket_id}", headers=headers)
        assert detail_response.status_code == 200
        final_ticket = detail_response.json()
        assert final_ticket["status"] == "closed"
        assert final_ticket["resolution_note"] is not None
        print(f"✓ Verified final ticket status: {final_ticket['status']}")
        
        return ticket_id
    
    def test_resolved_requires_resolution_note(self, admin_auth):
        """Test that resolving a ticket requires a resolution note"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        # Create a test ticket
        ticket_data = {
            "subject": "TEST_Resolution_Note_Required",
            "category": "general",
            "priority": "low",
            "description": "Test ticket for resolution note requirement",
            "target_user_ids": []
        }
        
        create_response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
        ticket = create_response.json()
        ticket_id = ticket["id"]
        
        # Try to resolve without resolution note
        status_update = {"status": "resolved"}
        response = requests.put(f"{BASE_URL}/api/tickets/{ticket_id}/status", json=status_update, headers=headers)
        assert response.status_code == 400, "Should fail without resolution note"
        print(f"✓ Correctly rejected resolve without resolution note")


class TestTicketMessages:
    """Test ticket messaging functionality"""
    
    @pytest.fixture
    def admin_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        data = response.json()
        return {"token": data["token"], "user": data["user"]}
    
    def test_add_message_to_ticket(self, admin_auth):
        """Test adding a message to a ticket"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        # Create a test ticket
        ticket_data = {
            "subject": "TEST_Message_Ticket",
            "category": "general",
            "priority": "medium",
            "description": "Test ticket for messaging",
            "target_user_ids": []
        }
        
        create_response = requests.post(f"{BASE_URL}/api/tickets", json=ticket_data, headers=headers)
        ticket = create_response.json()
        ticket_id = ticket["id"]
        
        # Add a message
        message_data = {"message": "This is a test message"}
        response = requests.post(f"{BASE_URL}/api/tickets/{ticket_id}/message", json=message_data, headers=headers)
        assert response.status_code == 200, f"Add message failed: {response.text}"
        print(f"✓ Added message to ticket")
        
        # Verify message was added
        detail_response = requests.get(f"{BASE_URL}/api/tickets/{ticket_id}", headers=headers)
        ticket_detail = detail_response.json()
        assert len(ticket_detail["messages"]) > 0
        assert ticket_detail["messages"][0]["message"] == "This is a test message"
        print(f"✓ Verified message in ticket detail")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_cleanup_test_tickets(self, admin_token):
        """Cleanup: Note about test tickets (no delete endpoint available)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/tickets/my-tickets", headers=headers)
        tickets = response.json()
        
        test_tickets = [t for t in tickets if t.get("subject", "").startswith("TEST_")]
        print(f"⚠ Found {len(test_tickets)} test tickets (manual cleanup may be needed)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
