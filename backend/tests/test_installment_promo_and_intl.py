import pytest
import os
import uuid
import requests
from pymongo import MongoClient
from core.auth import create_access_token, build_token_payload

API_BASE = os.environ.get("API_BASE") or "http://localhost:8000"
API = f"{API_BASE}/api"
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "leamss")

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]

def test_promo_validate_and_international_claim():
    # Setup test client
    client_id = f"client-{uuid.uuid4().hex[:6]}"
    client_email = f"client_{uuid.uuid4().hex[:6]}@example.com"
    client_user = {
        "id": client_id,
        "name": "Test Client",
        "email": client_email,
        "role": "client",
        "is_active": True,
        "status": "approved"
    }
    db["users"].insert_one(client_user)

    admin_id = f"admin-{uuid.uuid4().hex[:6]}"
    admin_user = {
        "id": admin_id,
        "name": "Admin User",
        "email": f"admin_{uuid.uuid4().hex[:6]}@example.com",
        "role": "admin",
        "is_active": True,
        "status": "approved"
    }
    db["users"].insert_one(admin_user)

    promo_code = f"TESTPROMO_{uuid.uuid4().hex[:4].upper()}"
    promo_doc = {
        "id": str(uuid.uuid4()),
        "code": promo_code,
        "discount_type": "percentage",
        "discount_value": 10,
        "max_uses": 100,
        "current_uses": 0,
        "active": True,
        "status": "active"
    }
    db["promo_codes"].insert_one(promo_doc)

    sale_id = f"sale-{uuid.uuid4().hex[:6]}"
    sale = {
        "id": sale_id,
        "client_id": client_id,
        "client_email": client_email,
        "client_name": "Test Client",
        "product_name": "Canada PR",
        "status": "approved",
        "fee_amount": 129378.5,
        "pending_amount": 64689.5,
        "amount_received": 64689.0,
        "payment_parts": [
            {"index": 0, "label": "1st Installment (50%)", "amount": 64689.0, "status": "paid"},
            {"index": 1, "label": "2nd Installment (50%)", "amount": 64689.5, "status": "pending"}
        ]
    }
    db["sales"].insert_one(sale)

    try:
        payload = build_token_payload(client_user)
        token = create_access_token(payload)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test Promo Validation for 2nd Installment
        val_res = requests.post(f"{API}/marketing/promo/validate", json={
            "code": promo_code,
            "amount": 64689.5
        }, headers=headers, timeout=10)
        assert val_res.status_code == 200, val_res.text
        data = val_res.json()
        assert data["valid"] is True
        assert data["discount_amount"] == 6468.95
        assert data["final_amount"] == 58220.55

        # 2. Test International Wire Transfer Claim
        claim_res = requests.post(f"{API}/payments/international-claim", json={
            "sale_id": sale_id,
            "reference_note": "SWIFT-REF-998877",
            "country": "Australia",
            "promo_code": promo_code,
            "discount_amount": 6468.95,
            "original_amount": 64689.5
        }, headers=headers, timeout=10)
        assert claim_res.status_code == 200, claim_res.text
        claim_data = claim_res.json()
        assert claim_data["ok"] is True

        # Verify in database
        updated_sale = db["sales"].find_one({"id": sale_id})
        assert updated_sale["payment_parts"][1]["status"] == "pending_verification"
        assert updated_sale["last_payment_claim"]["reference_note"] == "SWIFT-REF-998877"

        # 3. Test Admin Confirmation of International Installment Payment
        admin_token = create_access_token(build_token_payload(admin_user))
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        confirm_res = requests.post(f"{API}/payments/confirm-installment/{sale_id}", headers=admin_headers, timeout=10)
        assert confirm_res.status_code == 200, confirm_res.text
        conf_data = confirm_res.json()
        assert conf_data["ok"] is True
        assert conf_data["payment_status"] == "paid"
        assert conf_data["fully_paid"] is True

        # Verify in database: status should now be "paid"
        final_sale = db["sales"].find_one({"id": sale_id})
        assert final_sale["payment_status"] == "paid"
        assert final_sale["payment_parts"][1]["status"] == "paid"
        assert final_sale["pending_amount"] == 0.0

        # Verify client sees "paid" in /payments/my-proposals
        proposals_res = requests.get(f"{API}/payments/my-proposals", headers=headers, timeout=10)
        assert proposals_res.status_code == 200
        client_proposals = proposals_res.json()
        matching_prop = next(p for p in client_proposals if p["id"] == sale_id)
        assert matching_prop["payment_status"] == "paid"
        assert matching_prop["payment_parts"][1]["status"] == "paid"

    finally:
        db["users"].delete_one({"id": client_id})
        db["users"].delete_one({"id": admin_id})
        db["promo_codes"].delete_one({"code": promo_code})
        db["sales"].delete_one({"id": sale_id})
