import pytest
import os
import uuid
import requests
from datetime import datetime, timezone
from pymongo import MongoClient
from core.auth import create_access_token, build_token_payload

API_BASE = os.environ.get("API_BASE") or "http://localhost:8000"
API = f"{API_BASE}/api"
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "leamss")

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]

def test_second_installment_trigger_flow():
    # 1. Setup Partner, Client, Admin, and Case Manager
    partner_id = f"partner-{uuid.uuid4().hex[:6]}"
    partner_email = f"partner_{uuid.uuid4().hex[:6]}@example.com"
    partner_user = {
        "id": partner_id, "name": "Partner Test", "email": partner_email,
        "role": "partner", "is_active": True, "status": "approved"
    }
    db["users"].insert_one(partner_user)

    client_id = f"client-{uuid.uuid4().hex[:6]}"
    client_email = f"client_{uuid.uuid4().hex[:6]}@example.com"
    client_user = {
        "id": client_id, "name": "Client Test", "email": client_email,
        "role": "client", "is_active": True, "status": "approved"
    }
    db["users"].insert_one(client_user)

    admin_id = f"admin-{uuid.uuid4().hex[:6]}"
    admin_user = {
        "id": admin_id, "name": "Admin Test", "email": f"admin_{uuid.uuid4().hex[:6]}@example.com",
        "role": "admin", "is_active": True, "status": "approved"
    }
    db["users"].insert_one(admin_user)

    cm_id = f"cm-{uuid.uuid4().hex[:6]}"
    cm_user = {
        "id": cm_id, "name": "CM Test", "email": f"cm_{uuid.uuid4().hex[:6]}@example.com",
        "role": "case_manager", "is_active": True, "status": "approved"
    }
    db["users"].insert_one(cm_user)

    product_id = f"prod-{uuid.uuid4().hex[:6]}"
    pkg_id = f"pkg-{uuid.uuid4().hex[:6]}"
    product_doc = {
        "id": product_id,
        "name": "Australia PR Visa",
        "country": "Australia",
        "service_type": "PR",
        "packages": [
            {
                "id": pkg_id,
                "name": "Gold PR Package",
                "price": 100000.0,
                "payment_methods": {
                    "full_payment": {"enabled": True},
                    "split_50_50": {"enabled": True, "first_pct": 50},
                    "installments": {"enabled": True, "max_installments": 5}
                }
            }
        ]
    }
    db["products"].insert_one(product_doc)

    workflow_steps = [
        {"id": str(uuid.uuid4()), "product_id": product_id, "step_order": 1, "step_name": "Profile Creation & Intake"},
        {"id": str(uuid.uuid4()), "product_id": product_id, "step_order": 2, "step_name": "Document Verification"},
        {"id": str(uuid.uuid4()), "product_id": product_id, "step_order": 3, "step_name": "Eligibility Assessment"},
        {"id": str(uuid.uuid4()), "product_id": product_id, "step_order": 4, "step_name": "Application Submission"},
    ]
    db["workflow_steps"].insert_many(workflow_steps)

    pa_id = f"pa-{uuid.uuid4().hex[:6]}"
    pa_doc = {
        "id": pa_id,
        "client_name": "Client Test",
        "client_email": client_email,
        "client_user_id": client_id,
        "partner_id": partner_id,
        "country": "Australia",
        "service_type": "PR",
        "product_id": product_id,
        "product_name": "Australia PR Visa",
        "stage": "package_selected",
        "selected_package_snapshot": product_doc["packages"][0],
        "created_at": datetime.now(timezone.utc),
    }
    db["pre_assessments"].insert_one(pa_doc)

    try:
        partner_token = create_access_token(build_token_payload(partner_user))
        partner_headers = {"Authorization": f"Bearer {partner_token}"}
        cm_token = create_access_token(build_token_payload(cm_user))
        cm_headers = {"Authorization": f"Bearer {cm_token}"}
        admin_token = create_access_token(build_token_payload(admin_user))
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Partner finalizes 50/50 payment with Step 3 trigger
        fin_res = requests.post(f"{API}/pre-assessment/{pa_id}/finalize-payment-method", json={
            "payment_method_type": "split_50_50",
            "include_gst": False,
            "deduct_pre_assessment_fee": False,
            "second_installment_trigger_type": "step",
            "second_installment_step_order": 3,
            "second_installment_step_name": "Eligibility Assessment",
        }, headers=partner_headers, timeout=10)
        assert fin_res.status_code == 200, fin_res.text
        
        # Verify PA and Sale in database
        pa_after = db["pre_assessments"].find_one({"id": pa_id})
        assert pa_after["stage"] == "proposal_sent"
        assert pa_after["second_installment_trigger_type"] == "step"
        assert pa_after["second_installment_step_order"] == 3
        assert pa_after["proposal_payment_parts"][1]["trigger_step_order"] == 3
        assert "Step 3" in pa_after["proposal_payment_parts"][1]["trigger_condition"]

        sale_id = pa_after["sale_id"]
        sale_after = db["sales"].find_one({"id": sale_id})
        assert sale_after["second_installment_step_order"] == 3
        assert sale_after["payment_parts"][1]["status"] == "locked"

        # 3. First installment paid
        db["sales"].update_one({"id": sale_id}, {
            "$set": {
                "payment_parts.0.status": "paid",
                "amount_received": 50000.0,
                "pending_amount": 50000.0,
                "payment_status": "partial"
            }
        })
        db["pre_assessments"].update_one({"id": pa_id}, {
            "$set": {
                "proposal_payment_parts.0.status": "paid",
                "proposal_amount_paid": 50000.0,
                "proposal_amount_pending": 50000.0
            }
        })

        # 4. Create active Case for this PA
        case_id = str(uuid.uuid4())
        case_doc = {
            "id": case_id,
            "case_id": f"LEAMSS-TEST-{uuid.uuid4().hex[:4]}",
            "client_id": client_id,
            "client_name": "Client Test",
            "client_email": client_email,
            "product_id": product_id,
            "product_name": "Australia PR Visa",
            "partner_id": partner_id,
            "case_manager_id": cm_id,
            "pre_assessment_id": pa_id,
            "sale_id": sale_id,
            "status": "active",
            "current_step": "Profile Creation & Intake",
            "current_step_order": 1,
            "created_at": datetime.now(timezone.utc),
        }
        db["cases"].insert_one(case_doc)

        case_steps_docs = [
            {"id": str(uuid.uuid4()), "case_id": case_id, "step_order": 1, "step_name": "Profile Creation & Intake", "status": "in_progress"},
            {"id": str(uuid.uuid4()), "case_id": case_id, "step_order": 2, "step_name": "Document Verification", "status": "pending"},
            {"id": str(uuid.uuid4()), "case_id": case_id, "step_order": 3, "step_name": "Eligibility Assessment", "status": "pending"},
            {"id": str(uuid.uuid4()), "case_id": case_id, "step_order": 4, "step_name": "Application Submission", "status": "pending"},
        ]
        db["case_steps"].insert_many(case_steps_docs)

        # 5. Fetch Case via API — check Step 3 is marked payment_required & is_locked
        case_res = requests.get(f"{API}/cases/{case_id}", headers=cm_headers, timeout=10)
        assert case_res.status_code == 200, case_res.text
        case_data = case_res.json()
        step3 = next(s for s in case_data["steps"] if s["step_order"] == 3)
        assert step3["is_locked"] is True
        assert step3["payment_required"] is True

        # 6. CM completes Step 1 -> Step 2 becomes in_progress
        up1 = requests.post(f"{API}/cases/update-step", json={
            "case_id": case_id,
            "step_name": "Profile Creation & Intake",
            "status": "completed"
        }, headers=cm_headers, timeout=10)
        assert up1.status_code == 200, up1.text

        # 7. CM completes Step 2 -> Target Step 3 is reached
        up2 = requests.post(f"{API}/cases/update-step", json={
            "case_id": case_id,
            "step_name": "Document Verification",
            "status": "completed"
        }, headers=cm_headers, timeout=10)
        assert up2.status_code == 200, up2.text

        # Check that 2nd installment is now unlocked to 'pending' in database
        pa_check = db["pre_assessments"].find_one({"id": pa_id})
        assert pa_check["proposal_payment_parts"][1]["status"] == "pending"

        # 8. Attempting to start or complete Step 3 BEFORE payment must fail with 400
        up3_fail = requests.post(f"{API}/cases/update-step", json={
            "case_id": case_id,
            "step_name": "Eligibility Assessment",
            "status": "completed"
        }, headers=cm_headers, timeout=10)
        assert up3_fail.status_code == 400, "Should block advancing Step 3 before payment"
        assert "unpaid" in up3_fail.text.lower() or "payment" in up3_fail.text.lower()

        # 9. Admin confirms 2nd installment payment
        conf_res = requests.post(f"{API}/payments/confirm-installment/{sale_id}", headers=admin_headers, timeout=10)
        assert conf_res.status_code == 200, conf_res.text
        assert conf_res.json()["fully_paid"] is True

        # 10. CM completes Step 3 NOW that payment is settled -> Success!
        up3_success = requests.post(f"{API}/cases/update-step", json={
            "case_id": case_id,
            "step_name": "Eligibility Assessment",
            "status": "completed"
        }, headers=cm_headers, timeout=10)
        assert up3_success.status_code == 200, up3_success.text

    finally:
        db["users"].delete_many({"id": {"$in": [partner_id, client_id, admin_id, cm_id]}})
        db["products"].delete_one({"id": product_id})
        db["workflow_steps"].delete_many({"product_id": product_id})
        db["pre_assessments"].delete_one({"id": pa_id})
        db["sales"].delete_many({"client_id": client_id})
        if 'case_id' in locals():
            db["cases"].delete_one({"id": case_id})
            db["case_steps"].delete_many({"case_id": case_id})
