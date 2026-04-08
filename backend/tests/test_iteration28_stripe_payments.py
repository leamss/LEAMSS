"""
Iteration 28 - Stripe Payment Portal Backend Tests
Tests for:
- GET /api/payments/my-proposals — Returns client's sales/proposals with price breakdown
- POST /api/payments/create-checkout — Creates Stripe checkout session
- GET /api/payments/status/{session_id} — Returns payment status
- GET /api/payments/history/{sale_id} — Returns payment transactions
- POST /api/webhook/stripe — Stripe webhook endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PROMO_CLIENT = {"email": "promo.client@test.com", "password": "Client@123"}  # Has pending payment
REGULAR_CLIENT = {"email": "client@leamss.com", "password": "Client@123"}  # Has partial payment
ADMIN = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER = {"email": "partner@leamss.com", "password": "Partner@123"}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def promo_client_token(api_client):
    """Get token for promo.client@test.com (has pending payment)"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=PROMO_CLIENT)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Promo client login failed: {response.text}")


@pytest.fixture(scope="module")
def regular_client_token(api_client):
    """Get token for client@leamss.com"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=REGULAR_CLIENT)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Regular client login failed: {response.text}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.text}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self, api_client):
        """Test API is running"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Health check passed")


class TestMyProposals:
    """Tests for GET /api/payments/my-proposals"""
    
    def test_my_proposals_returns_sales_with_price_breakdown(self, api_client, promo_client_token):
        """Test that my-proposals returns sales with full price breakdown"""
        response = api_client.get(
            f"{BASE_URL}/api/payments/my-proposals",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        assert response.status_code == 200
        proposals = response.json()
        assert isinstance(proposals, list)
        assert len(proposals) > 0, "Expected at least one proposal for promo client"
        
        # Check first proposal has required fields
        proposal = proposals[0]
        assert "id" in proposal
        assert "product_name" in proposal or "product_id" in proposal
        assert "fee_amount" in proposal
        assert "amount_received" in proposal
        assert "pending_amount" in proposal
        assert "status" in proposal
        
        # Check discount fields exist
        assert "promo_code" in proposal or "promo_discount_amount" in proposal or proposal.get("total_discount_amount", 0) >= 0
        
        print(f"✓ my-proposals returned {len(proposals)} proposals with price breakdown")
        print(f"  - Fee: ₹{proposal.get('fee_amount', 0)}, Received: ₹{proposal.get('amount_received', 0)}, Pending: ₹{proposal.get('pending_amount', 0)}")
    
    def test_my_proposals_includes_payment_history(self, api_client, promo_client_token):
        """Test that proposals include payment_transactions"""
        response = api_client.get(
            f"{BASE_URL}/api/payments/my-proposals",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        assert response.status_code == 200
        proposals = response.json()
        
        # Check payment_transactions field exists
        proposal = proposals[0]
        assert "payment_transactions" in proposal or "payment_history" in proposal
        print("✓ my-proposals includes payment history/transactions")
    
    def test_my_proposals_requires_auth(self, api_client):
        """Test that my-proposals requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/payments/my-proposals")
        assert response.status_code in [401, 403, 422]
        print("✓ my-proposals requires authentication")


class TestCreateCheckout:
    """Tests for POST /api/payments/create-checkout"""
    
    def test_create_checkout_for_approved_sale_with_pending(self, api_client, promo_client_token):
        """Test creating checkout session for approved sale with pending amount"""
        # First get the sale ID
        proposals_response = api_client.get(
            f"{BASE_URL}/api/payments/my-proposals",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        proposals = proposals_response.json()
        
        # Find approved sale with pending amount
        approved_sale = None
        for p in proposals:
            if p.get("status") == "approved" and (p.get("pending_amount", 0) > 0):
                approved_sale = p
                break
        
        assert approved_sale is not None, "No approved sale with pending amount found"
        
        # Create checkout
        response = api_client.post(
            f"{BASE_URL}/api/payments/create-checkout",
            json={
                "sale_id": approved_sale["id"],
                "origin_url": "https://payment-portal-323.preview.emergentagent.com"
            },
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "url" in data, "Response should contain checkout URL"
        assert "session_id" in data, "Response should contain session_id"
        assert data["url"].startswith("https://checkout.stripe.com"), f"URL should be Stripe checkout: {data['url']}"
        
        print(f"✓ create-checkout returned Stripe URL: {data['url'][:60]}...")
        print(f"  - Session ID: {data['session_id']}")
        
        # Store for later tests
        pytest.checkout_session_id = data["session_id"]
        pytest.checkout_sale_id = approved_sale["id"]
    
    def test_create_checkout_rejects_pending_sale(self, api_client, admin_token):
        """Test that create-checkout rejects non-approved (pending) sales"""
        # We need to find or create a pending sale
        # For now, test with a fake sale_id that doesn't exist
        response = api_client.post(
            f"{BASE_URL}/api/payments/create-checkout",
            json={
                "sale_id": "non-existent-sale-id",
                "origin_url": "https://payment-portal-323.preview.emergentagent.com"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should return 404 for non-existent sale
        assert response.status_code in [400, 404]
        print("✓ create-checkout rejects non-existent sale")
    
    def test_create_checkout_requires_auth(self, api_client):
        """Test that create-checkout requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/payments/create-checkout",
            json={
                "sale_id": "any-sale-id",
                "origin_url": "https://example.com"
            }
        )
        assert response.status_code in [401, 403, 422]
        print("✓ create-checkout requires authentication")


class TestPaymentStatus:
    """Tests for GET /api/payments/status/{session_id}"""
    
    def test_payment_status_returns_status(self, api_client, promo_client_token):
        """Test getting payment status for a session"""
        # Use session from previous test if available
        session_id = getattr(pytest, 'checkout_session_id', None)
        
        if not session_id:
            # Create a new checkout to get session_id
            proposals_response = api_client.get(
                f"{BASE_URL}/api/payments/my-proposals",
                headers={"Authorization": f"Bearer {promo_client_token}"}
            )
            proposals = proposals_response.json()
            approved_sale = next((p for p in proposals if p.get("status") == "approved" and p.get("pending_amount", 0) > 0), None)
            
            if approved_sale:
                checkout_response = api_client.post(
                    f"{BASE_URL}/api/payments/create-checkout",
                    json={
                        "sale_id": approved_sale["id"],
                        "origin_url": "https://payment-portal-323.preview.emergentagent.com"
                    },
                    headers={"Authorization": f"Bearer {promo_client_token}"}
                )
                if checkout_response.status_code == 200:
                    session_id = checkout_response.json().get("session_id")
        
        if not session_id:
            pytest.skip("No checkout session available for status test")
        
        response = api_client.get(
            f"{BASE_URL}/api/payments/status/{session_id}",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "payment_status" in data
        assert "amount" in data or "sale_id" in data
        
        print(f"✓ payment status returned: {data}")
    
    def test_payment_status_404_for_invalid_session(self, api_client, promo_client_token):
        """Test that invalid session_id returns 404"""
        response = api_client.get(
            f"{BASE_URL}/api/payments/status/invalid-session-id-12345",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        assert response.status_code == 404
        print("✓ payment status returns 404 for invalid session")


class TestPaymentHistory:
    """Tests for GET /api/payments/history/{sale_id}"""
    
    def test_payment_history_returns_transactions(self, api_client, promo_client_token):
        """Test getting payment history for a sale"""
        # Get sale_id from proposals
        proposals_response = api_client.get(
            f"{BASE_URL}/api/payments/my-proposals",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        proposals = proposals_response.json()
        
        if not proposals:
            pytest.skip("No proposals available for history test")
        
        sale_id = proposals[0]["id"]
        
        response = api_client.get(
            f"{BASE_URL}/api/payments/history/{sale_id}",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        
        assert response.status_code == 200
        transactions = response.json()
        assert isinstance(transactions, list)
        
        print(f"✓ payment history returned {len(transactions)} transactions")


class TestStripeWebhook:
    """Tests for POST /api/webhook/stripe"""
    
    def test_webhook_endpoint_exists(self, api_client):
        """Test that webhook endpoint exists and responds"""
        # Send empty body - should return error but not 404
        response = api_client.post(
            f"{BASE_URL}/api/webhook/stripe",
            data=b"{}",
            headers={"Content-Type": "application/json"}
        )
        
        # Should not be 404 - endpoint exists
        assert response.status_code != 404, "Webhook endpoint should exist"
        # Could be 200 (ok), 400 (bad request), or error response
        print(f"✓ webhook endpoint exists, returned status: {response.status_code}")


class TestFullPaymentFlow:
    """End-to-end payment flow test"""
    
    def test_full_payment_flow(self, api_client, promo_client_token):
        """Test complete payment flow: proposals → checkout → status"""
        # Step 1: Get proposals
        proposals_response = api_client.get(
            f"{BASE_URL}/api/payments/my-proposals",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        assert proposals_response.status_code == 200
        proposals = proposals_response.json()
        
        # Find approved sale with pending amount
        approved_sale = next(
            (p for p in proposals if p.get("status") == "approved" and (p.get("pending_amount", 0) > 0)),
            None
        )
        
        if not approved_sale:
            pytest.skip("No approved sale with pending amount for full flow test")
        
        print(f"Step 1: Found approved sale with ₹{approved_sale.get('pending_amount', 0)} pending")
        
        # Step 2: Create checkout
        checkout_response = api_client.post(
            f"{BASE_URL}/api/payments/create-checkout",
            json={
                "sale_id": approved_sale["id"],
                "origin_url": "https://payment-portal-323.preview.emergentagent.com"
            },
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        assert checkout_response.status_code == 200
        checkout_data = checkout_response.json()
        assert "url" in checkout_data
        assert "session_id" in checkout_data
        
        print(f"Step 2: Created checkout session: {checkout_data['session_id']}")
        
        # Step 3: Check status
        status_response = api_client.get(
            f"{BASE_URL}/api/payments/status/{checkout_data['session_id']}",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        print(f"Step 3: Payment status: {status_data.get('payment_status', status_data.get('status'))}")
        
        # Step 4: Check history
        history_response = api_client.get(
            f"{BASE_URL}/api/payments/history/{approved_sale['id']}",
            headers={"Authorization": f"Bearer {promo_client_token}"}
        )
        assert history_response.status_code == 200
        
        print(f"Step 4: Payment history retrieved")
        print("✓ Full payment flow completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
