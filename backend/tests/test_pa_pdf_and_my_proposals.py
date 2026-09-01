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

def test_pdf_invoice_single_promo_and_my_proposals():
    # Setup test user/client
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

    pa_id = f"pa-{uuid.uuid4().hex[:6]}"
    sale_id = f"sale-{uuid.uuid4().hex[:6]}"
    promo_code = "PROMO25_TEST"

    sale = {
        "id": sale_id,
        "client_email": client_email,
        "client_name": "Test Client",
        "product_name": "Canada PR",
        "status": "approved",
        "fee_before_discount": 152990.0,
        "base_fee": 152990.0,
        "deduct_pre_assessment_fee": True,
        "pre_assessment_deduction": 5100.0,
        "promo_code": promo_code,
        "promo_discount_amount": 38247.5,
        "coupon_code": promo_code,
        "coupon_discount_amount": 38247.5,
        "gst_included": True,
        "gst_amount": 19736.0,
        "fee_amount": 129378.5,
        "amount_received": 64689.0,
        "pending_amount": 64689.5,
        "pre_assessment_id": pa_id,
        "created_at": "2026-08-27T11:00:00Z",
        "payment_parts": [
            {"index": 0, "label": "1st Installment (50%)", "amount": 64689.0, "status": "paid"},
            {"index": 1, "label": "2nd Installment (50%)", "amount": 64689.5, "status": "pending"}
        ]
    }
    db["sales"].insert_one(sale)

    pa = {
        "id": pa_id,
        "sale_id": sale_id,
        "client_name": "Test Client",
        "client_email": client_email,
        "country": "canada",
        "service_type": "PR",
        "product_name": "Canada PR",
        "stage": "proposal_sent",
        "fee_base_amount": 5100.0,
        "fee_amount_paid": 6018.0,
        "fee_gst_included": True,
        "fee_gst_amount": 918.0,
        "proposal_base_fee": 152990.0,
        "proposal_deduct_pa_fee": True,
        "deduct_pre_assessment_fee": True,
        "proposal_pa_deduction": 5100.0,
        "proposal_promo_code": promo_code,
        "proposal_promo_discount": 38247.5,
        "proposal_coupon_code": promo_code,
        "proposal_coupon_discount_amount": 38247.5,
        "proposal_gst_included": True,
        "proposal_gst_amount": 19736.0,
        "proposal_fee": 129378.5,
        "proposal_payment_parts": sale["payment_parts"],
    }
    db["pre_assessments"].insert_one(pa)

    try:
        # 1. Test /payments/my-proposals
        payload = build_token_payload(client_user)
        token = create_access_token(payload)
        headers = {"Authorization": f"Bearer {token}"}

        r = requests.get(f"{API}/payments/my-proposals", headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        proposals_data = r.json()
        assert len(proposals_data) >= 1
        found_sale = next((s for s in proposals_data if s["id"] == sale_id), None)
        assert found_sale is not None
        assert found_sale.get("pre_assessment_deduction") == 5100.0
        assert found_sale.get("deduct_pre_assessment_fee") is True

        # 2. Test PDF document generation
        from routers.proposal_docs import _build_proposal_pdf
        pdf_path = f"uploads/test_invoice_{pa_id}.pdf"
        os.makedirs("uploads", exist_ok=True)
        _build_proposal_pdf(pa, pdf_path, "invoice")
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000  # valid PDF created

        # 3. Clean up generated file
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

    finally:
        db["users"].delete_one({"id": client_id})
        db["sales"].delete_one({"id": sale_id})
        db["pre_assessments"].delete_one({"id": pa_id})
