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

@pytest.fixture(scope="module")
def partner_auth():
    partner = db["users"].find_one({"role": "partner", "status": "approved"})
    if not partner:
        partner = {
            "id": str(uuid.uuid4()),
            "name": "Test Partner",
            "email": "test_partner_deduction@test.com",
            "role": "partner",
            "status": "approved",
            "is_active": True
        }
        db["users"].insert_one(partner)
    payload = build_token_payload(partner)
    token = create_access_token(payload)
    return {"headers": {"Authorization": f"Bearer {token}"}, "partner_id": partner["id"]}

def test_pa_fee_deduction_full_flow(partner_auth):
    partner_id = partner_auth["partner_id"]
    headers = partner_auth["headers"]

    product_id = f"prod-{uuid.uuid4().hex[:6]}"
    package_id = f"pkg-{uuid.uuid4().hex[:6]}"
    promo_code = f"PROMO{uuid.uuid4().hex[:4].upper()}"
    product = {
        "id": product_id,
        "name": "Global Visa Pro",
        "country": "USA",
        "service_type": "Immigration",
        "packages": [
            {
                "id": package_id,
                "name": "Executive Tier",
                "price": 100000.0,
                "payment_methods": {
                    "full_payment": {"enabled": True},
                    "split_50_50": {"enabled": True, "first_pct": 50},
                    "installments": {"enabled": True, "max_installments": 3}
                }
            }
        ]
    }
    db["products"].insert_one(product)

    # Insert test promo code: 10% discount
    db["promo_codes"].insert_one({
        "id": str(uuid.uuid4()),
        "code": promo_code,
        "discount_type": "percentage",
        "discount_value": 10,
        "is_active": True,
        "active": True,
        "max_uses": 100,
        "current_uses": 0
    })

    pa_id = f"pa-{uuid.uuid4().hex[:6]}"
    pa = {
        "id": pa_id,
        "client_name": "Alice Tester",
        "client_email": "alice@example.com",
        "client_mobile": "9999988888",
        "country": "USA",
        "service_type": "Immigration",
        "product_id": product_id,
        "product_name": "Global Visa Pro",
        "assigned_partner_id": partner_id,
        "stage": "package_selected",
        "selected_package": product["packages"][0],
        "selected_package_snapshot": product["packages"][0]
    }
    db["pre_assessments"].insert_one(pa)

    try:
        # Case 1: Checkbox checked (Deduct ₹5,100), Full payment, no GST
        db["pre_assessments"].update_one({"id": pa_id}, {"$set": {"stage": "package_selected"}})
        r1 = requests.post(
            f"{API}/pre-assessment/{pa_id}/finalize-payment-method",
            json={"payment_method_type": "full_payment", "include_gst": False, "deduct_pre_assessment_fee": True},
            headers=headers,
            timeout=15
        )
        assert r1.status_code == 200, r1.text
        doc1 = db["pre_assessments"].find_one({"id": pa_id})
        assert doc1["proposal_deduct_pa_fee"] is True
        assert doc1["proposal_pa_deduction"] == 5100.0
        assert doc1["proposal_fee"] == 94900.0
        assert doc1["proposal_payment_parts"][0]["amount"] == 94900.0

        # Case 2: Checkbox checked (Deduct ₹5,100), 50-50 Split, GST 18%
        db["pre_assessments"].update_one({"id": pa_id}, {"$set": {"stage": "package_selected"}})
        r2 = requests.post(
            f"{API}/pre-assessment/{pa_id}/finalize-payment-method",
            json={"payment_method_type": "split_50_50", "include_gst": True, "deduct_pre_assessment_fee": True},
            headers=headers,
            timeout=15
        )
        assert r2.status_code == 200, r2.text
        doc2 = db["pre_assessments"].find_one({"id": pa_id})
        assert doc2["proposal_deduct_pa_fee"] is True
        assert doc2["proposal_pa_deduction"] == 5100.0
        # 94900 + (94900 * 0.18 = 17082) = 111982
        assert doc2["proposal_fee"] == 111982.0
        assert doc2["proposal_payment_parts"][0]["amount"] == 55991.0
        assert doc2["proposal_payment_parts"][1]["amount"] == 55991.0

        # Case 3: Checkbox checked (Deduct ₹5,100) + Promo Code (10%) + GST (18%)
        db["pre_assessments"].update_one({"id": pa_id}, {"$set": {"stage": "package_selected"}})
        r3 = requests.post(
            f"{API}/pre-assessment/{pa_id}/finalize-payment-method",
            json={
                "payment_method_type": "full_payment",
                "include_gst": True,
                "deduct_pre_assessment_fee": True,
                "coupon_code": promo_code,
                "promo_code": promo_code
            },
            headers=headers,
            timeout=15
        )
        assert r3.status_code == 200, r3.text
        doc3 = db["pre_assessments"].find_one({"id": pa_id})
        assert doc3["proposal_deduct_pa_fee"] is True
        assert doc3["proposal_pa_deduction"] == 5100.0
        # Base: 100000 - 10000 (10% promo) - 5100 (PA deduction) = 84900
        # GST (18% on 84900) = 15282
        # Final Total: 84900 + 15282 = 100182
        assert doc3["proposal_fee"] == 100182.0
        assert doc3["proposal_payment_parts"][0]["amount"] == 100182.0

        # Case 4: Checkbox NOT checked (Do not deduct ₹5,100), 50-50 Split, GST 18%
        db["pre_assessments"].update_one({"id": pa_id}, {"$set": {"stage": "package_selected"}})
        r4 = requests.post(
            f"{API}/pre-assessment/{pa_id}/finalize-payment-method",
            json={"payment_method_type": "split_50_50", "include_gst": True, "deduct_pre_assessment_fee": False},
            headers=headers,
            timeout=15
        )
        assert r4.status_code == 200, r4.text
        doc4 = db["pre_assessments"].find_one({"id": pa_id})
        assert doc4["proposal_deduct_pa_fee"] is False
        assert doc4["proposal_pa_deduction"] == 0.0
        # 100000 + (100000 * 0.18 = 18000) = 118000
        assert doc4["proposal_fee"] == 118000.0
        assert doc4["proposal_payment_parts"][0]["amount"] == 59000.0
        assert doc4["proposal_payment_parts"][1]["amount"] == 59000.0

    finally:
        db["products"].delete_one({"id": product_id})
        db["promo_codes"].delete_one({"code": promo_code})
        db["pre_assessments"].delete_one({"id": pa_id})
        db["sales"].delete_many({"pre_assessment_id": pa_id})
