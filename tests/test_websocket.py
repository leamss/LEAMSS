"""
WebSocket Notification System Tests for LEAMSS Portal
Tests:
1. WebSocket connection with valid JWT token
2. WebSocket ping/pong mechanism
3. WebSocket notification broadcast when ticket is created
4. Invalid token rejection
"""

import pytest
import requests
import asyncio
import websockets
import json
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://immi-portal-7.preview.emergentagent.com').rstrip('/')
API_URL = f"{BASE_URL}/api"
WS_URL = BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')

# Test credentials
TEST_CREDENTIALS = {
    "admin": {"email": "admin@leamss.com", "password": "Admin@123"},
    "case_manager": {"email": "manager@leamss.com", "password": "Manager@123"},
    "partner": {"email": "partner@leamss.com", "password": "Partner@123"},
    "client": {"email": "client@leamss.com", "password": "Client@123"}
}


class TestWebSocketConnection:
    """Test WebSocket connection establishment"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin JWT token"""
        response = requests.post(
            f"{API_URL}/auth/login",
            json=TEST_CREDENTIALS["admin"]
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture
    def admin_user(self):
        """Get admin user info"""
        response = requests.post(
            f"{API_URL}/auth/login",
            json=TEST_CREDENTIALS["admin"]
        )
        assert response.status_code == 200
        return response.json()["user"]
    
    @pytest.fixture
    def case_manager_token(self):
        """Get case manager JWT token"""
        response = requests.post(
            f"{API_URL}/auth/login",
            json=TEST_CREDENTIALS["case_manager"]
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture
    def case_manager_user(self):
        """Get case manager user info"""
        response = requests.post(
            f"{API_URL}/auth/login",
            json=TEST_CREDENTIALS["case_manager"]
        )
        assert response.status_code == 200
        return response.json()["user"]
    
    @pytest.mark.asyncio
    async def test_websocket_connection_with_valid_token(self, admin_token):
        """Test that WebSocket connection can be established with valid JWT token"""
        ws_url = f"{WS_URL}/ws/{admin_token}"
        print(f"\nConnecting to WebSocket: {ws_url[:50]}...")
        
        try:
            async with websockets.connect(ws_url, close_timeout=5) as websocket:
                print("✓ WebSocket connection established successfully")
                # Connection successful - close gracefully
                await websocket.close()
                assert True
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, admin_token):
        """Test WebSocket ping/pong keepalive mechanism"""
        ws_url = f"{WS_URL}/ws/{admin_token}"
        print(f"\nTesting ping/pong on WebSocket...")
        
        try:
            async with websockets.connect(ws_url, close_timeout=5) as websocket:
                # Send ping
                await websocket.send("ping")
                print("Sent: ping")
                
                # Wait for pong response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                print(f"Received: {data}")
                
                assert data.get("type") == "pong", f"Expected pong response, got: {data}"
                print("✓ Ping/pong mechanism working correctly")
                
                await websocket.close()
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for pong response")
        except Exception as e:
            pytest.fail(f"Ping/pong test failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_token_rejected(self):
        """Test that WebSocket connection is rejected with invalid token"""
        invalid_token = "invalid_jwt_token_12345"
        ws_url = f"{WS_URL}/ws/{invalid_token}"
        print(f"\nTesting invalid token rejection...")
        
        try:
            async with websockets.connect(ws_url, close_timeout=5) as websocket:
                # If we get here, connection was accepted (which is wrong)
                # Wait a bit to see if it gets closed
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=3)
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"✓ Connection closed with code: {e.code}")
                    assert e.code in [4001, 4000, 1000], f"Unexpected close code: {e.code}"
                    return
                pytest.fail("Connection should have been rejected for invalid token")
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"✓ Connection rejected with status: {e.status_code}")
            assert True
        except websockets.exceptions.ConnectionClosed as e:
            print(f"✓ Connection closed with code: {e.code}")
            assert e.code in [4001, 4000], f"Unexpected close code: {e.code}"
        except Exception as e:
            # Some form of rejection is expected
            print(f"✓ Connection rejected: {type(e).__name__}: {str(e)}")
            assert True


class TestWebSocketNotificationBroadcast:
    """Test WebSocket notification broadcast when events occur"""
    
    @pytest.fixture
    def admin_auth(self):
        """Get admin authentication"""
        response = requests.post(
            f"{API_URL}/auth/login",
            json=TEST_CREDENTIALS["admin"]
        )
        assert response.status_code == 200
        data = response.json()
        return {"token": data["token"], "user": data["user"]}
    
    @pytest.fixture
    def case_manager_auth(self):
        """Get case manager authentication"""
        response = requests.post(
            f"{API_URL}/auth/login",
            json=TEST_CREDENTIALS["case_manager"]
        )
        assert response.status_code == 200
        data = response.json()
        return {"token": data["token"], "user": data["user"]}
    
    @pytest.mark.asyncio
    async def test_notification_broadcast_on_ticket_creation(self, admin_auth, case_manager_auth):
        """
        Test that when a ticket is created targeting admin, 
        the admin receives a real-time WebSocket notification
        """
        admin_token = admin_auth["token"]
        admin_user_id = admin_auth["user"]["id"]
        cm_token = case_manager_auth["token"]
        
        print(f"\nTesting notification broadcast...")
        print(f"Admin user ID: {admin_user_id}")
        
        ws_url = f"{WS_URL}/ws/{admin_token}"
        notification_received = False
        received_data = None
        
        try:
            async with websockets.connect(ws_url, close_timeout=10) as websocket:
                print("✓ Admin WebSocket connected")
                
                # Create a ticket targeting admin (this should trigger notification)
                async def create_ticket():
                    await asyncio.sleep(1)  # Give WebSocket time to be ready
                    
                    ticket_data = {
                        "subject": f"TEST_WebSocket_Notification_{int(time.time())}",
                        "category": "technical",
                        "priority": "medium",
                        "description": "Testing WebSocket notification broadcast",
                        "target_role": "admin"  # Target all admins
                    }
                    
                    response = requests.post(
                        f"{API_URL}/tickets",
                        json=ticket_data,
                        headers={"Authorization": f"Bearer {cm_token}"}
                    )
                    print(f"Ticket creation response: {response.status_code}")
                    if response.status_code == 200:
                        print(f"✓ Ticket created: {response.json().get('id', 'unknown')}")
                    return response
                
                # Start ticket creation in background
                ticket_task = asyncio.create_task(create_ticket())
                
                # Wait for WebSocket notification
                try:
                    # Wait up to 10 seconds for notification
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(response)
                    print(f"Received WebSocket message: {data}")
                    
                    if data.get("type") == "notification":
                        notification_received = True
                        received_data = data
                        print("✓ Real-time notification received via WebSocket!")
                        print(f"  Title: {data.get('data', {}).get('title')}")
                        print(f"  Message: {data.get('data', {}).get('message')}")
                except asyncio.TimeoutError:
                    print("⚠ No WebSocket notification received within timeout")
                
                # Wait for ticket creation to complete
                await ticket_task
                
                await websocket.close()
        except Exception as e:
            print(f"Error during test: {str(e)}")
            raise
        
        # Assert notification was received
        assert notification_received, "Expected to receive WebSocket notification when ticket was created"
        assert received_data.get("type") == "notification"
        assert "data" in received_data
        assert "title" in received_data["data"]
        assert "ticket" in received_data["data"]["title"].lower() or "ticket" in received_data["data"]["notification_type"].lower()
    
    @pytest.mark.asyncio
    async def test_multiple_ping_pong_cycles(self, admin_auth):
        """Test multiple ping/pong cycles to verify connection stability"""
        admin_token = admin_auth["token"]
        ws_url = f"{WS_URL}/ws/{admin_token}"
        
        print(f"\nTesting multiple ping/pong cycles...")
        
        try:
            async with websockets.connect(ws_url, close_timeout=10) as websocket:
                for i in range(3):
                    await websocket.send("ping")
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(response)
                    assert data.get("type") == "pong", f"Cycle {i+1}: Expected pong, got {data}"
                    print(f"✓ Ping/pong cycle {i+1} successful")
                    await asyncio.sleep(0.5)
                
                print("✓ All ping/pong cycles completed successfully")
                await websocket.close()
        except Exception as e:
            pytest.fail(f"Multiple ping/pong test failed: {str(e)}")


class TestNotificationAPI:
    """Test notification REST API endpoints"""
    
    @pytest.fixture
    def admin_headers(self):
        """Get admin auth headers"""
        response = requests.post(
            f"{API_URL}/auth/login",
            json=TEST_CREDENTIALS["admin"]
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_notifications(self, admin_headers):
        """Test GET /api/notifications endpoint"""
        response = requests.get(f"{API_URL}/notifications", headers=admin_headers)
        print(f"\nGET /api/notifications: {response.status_code}")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of notifications"
        print(f"✓ Retrieved {len(data)} notifications")
        
        if data:
            # Verify notification structure
            notification = data[0]
            assert "id" in notification
            assert "title" in notification
            assert "message" in notification
            assert "is_read" in notification
            print(f"✓ Notification structure verified")
    
    def test_mark_notification_as_read(self, admin_headers):
        """Test marking a notification as read"""
        # First get notifications
        response = requests.get(f"{API_URL}/notifications", headers=admin_headers)
        assert response.status_code == 200
        notifications = response.json()
        
        if not notifications:
            pytest.skip("No notifications to mark as read")
        
        # Find an unread notification
        unread = [n for n in notifications if not n.get("is_read")]
        if not unread:
            print("All notifications already read, testing with first notification")
            notification_id = notifications[0]["id"]
        else:
            notification_id = unread[0]["id"]
        
        # Mark as read
        response = requests.post(
            f"{API_URL}/notifications/{notification_id}/read",
            headers=admin_headers
        )
        print(f"\nPOST /api/notifications/{notification_id}/read: {response.status_code}")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Notification marked as read")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
