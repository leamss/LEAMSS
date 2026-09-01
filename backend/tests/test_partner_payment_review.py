import pytest
import requests
from pymongo import MongoClient

def test_payment_review_and_forward():
    # Login as admin / partner
    login_res = requests.post("http://localhost:8001/api/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"})
    assert login_res.status_code == 200, "Login failed"
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = MongoClient("mongodb://localhost:27017")["leamss"]
    pa = db["pre_assessments"].find_one({"client_name": "saanikaa"}, {"_id": 0})
    assert pa is not None, "saanikaa PA not found"
    pa_id = pa["id"]

    # 1. Simulate client making a payment -> stage becomes proposal_paid
    db["pre_assessments"].update_one(
        {"id": pa_id},
        {"$set": {
            "stage": "proposal_paid",
            "proposal_amount_paid": 75989,
            "proposal_paid_at": "2026-08-29T12:15:00Z",
            "partner_final_submitted_at": None,
        }}
    )

    # 2. Partner retrieves assessments
    res = requests.get("http://localhost:8001/api/pre-assessment/my-assessments", headers=headers)
    assert res.status_code == 200
    pas = res.json()
    target_pa = next((p for p in pas if p["id"] == pa_id), None)
    assert target_pa is not None
    assert target_pa["stage"] == "proposal_paid"
    assert target_pa.get("proposal_amount_paid") == 75989
    print("Stage 1 Verified: Client made payment, stage=proposal_paid (Payment is Under Review)")

    # 3. Partner forwards payment to Admin
    fwd_res = requests.post(f"http://localhost:8001/api/pre-assessment/{pa_id}/forward-final-approval", headers=headers)
    assert fwd_res.status_code == 200
    fwd_data = fwd_res.json()
    assert fwd_data["stage"] == "awaiting_final_approval"
    print("Stage 2 Verified: Forwarded to Admin successfully")

    # 4. Re-fetch PA and verify new stage
    updated_res = requests.get(f"http://localhost:8001/api/pre-assessment/{pa_id}", headers=headers)
    assert updated_res.status_code == 200
    updated_pa = updated_res.json()
    assert updated_pa["stage"] == "awaiting_final_approval"
    assert updated_pa.get("partner_final_submitted_at") is not None
    print("Stage 3 Verified: PA is now in awaiting_final_approval (Payment is Under Review – Forwarded to Admin)")

if __name__ == "__main__":
    test_payment_review_and_forward()
