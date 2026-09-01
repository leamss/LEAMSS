import pytest
import os
import io
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

def test_locked_document_full_payment_gate():
    # 1. Setup users: Admin, CM, Client
    client_id = f"client-{uuid.uuid4().hex[:6]}"
    client_email = f"client_{uuid.uuid4().hex[:6]}@example.com"
    client_user = {
        "id": client_id, "name": "LockedDoc Client", "email": client_email,
        "role": "client", "is_active": True, "status": "approved"
    }
    db["users"].insert_one(client_user)

    admin_id = f"admin-{uuid.uuid4().hex[:6]}"
    admin_user = {
        "id": admin_id, "name": "LockedDoc Admin", "email": f"admin_{uuid.uuid4().hex[:6]}@example.com",
        "role": "admin", "is_active": True, "status": "approved"
    }
    db["users"].insert_one(admin_user)

    cm_id = f"cm-{uuid.uuid4().hex[:6]}"
    cm_user = {
        "id": cm_id, "name": "LockedDoc CM", "email": f"cm_{uuid.uuid4().hex[:6]}@example.com",
        "role": "case_manager", "is_active": True, "status": "approved"
    }
    db["users"].insert_one(cm_user)

    # 2. Setup Product & Workflow Step with Locked Document
    product_id = f"prod-{uuid.uuid4().hex[:6]}"
    product_doc = {
        "id": product_id,
        "name": "Canada Express Entry",
        "country": "Canada",
        "service_type": "PR",
        "packages": [
            {
                "id": str(uuid.uuid4()),
                "name": "Express Package",
                "price": 80000.0,
                "payment_methods": {
                    "full_payment": {"enabled": True},
                    "split_50_50": {"enabled": True}
                }
            }
        ]
    }
    db["products"].insert_one(product_doc)

    wf_step_id = str(uuid.uuid4())
    wf_step = {
        "id": wf_step_id,
        "product_id": product_id,
        "step_order": 1,
        "step_name": "Assessment & Verification",
        "description": "Initial assessment step",
        "sections": [
            {
                "id": str(uuid.uuid4()),
                "title": "Required Documents",
                "fields": [
                    {
                        "key": "client_passport",
                        "label": "Passport Copy",
                        "field_type": "file",
                        "required": True,
                        "filled_by": "client",
                        "is_locked_until_paid": False
                    },
                    {
                        "key": "official_assessment_report",
                        "label": "Official Assessment Report",
                        "field_type": "file",
                        "required": True,
                        "filled_by": "both",
                        "is_locked_until_paid": True # 🔒 Admin marked as locked!
                    }
                ]
            }
        ],
        "required_documents": [
            {
                "name": "Official Assessment Report",
                "mandatory": True,
                "is_locked_until_paid": True
            }
        ]
    }
    db["workflow_steps"].insert_one(wf_step)

    # 3. Setup PA & Sale with 50/50 split (1st part paid, 2nd part pending)
    sale_id = f"sale-{uuid.uuid4().hex[:6]}"
    pa_id = f"pa-{uuid.uuid4().hex[:6]}"
    
    sale_doc = {
        "id": sale_id,
        "client_id": client_id,
        "client_name": "LockedDoc Client",
        "client_email": client_email,
        "product_id": product_id,
        "total_amount": 80000.0,
        "amount_received": 40000.0,
        "pending_amount": 40000.0,
        "payment_status": "partial",
        "payment_parts": [
            {"id": "part-1", "label": "1st Installment", "amount": 40000.0, "status": "paid"},
            {"id": "part-2", "label": "2nd Installment", "amount": 40000.0, "status": "pending"}
        ],
        "created_at": datetime.now(timezone.utc)
    }
    db["sales"].insert_one(sale_doc)

    pa_doc = {
        "id": pa_id,
        "sale_id": sale_id,
        "client_id": client_id,
        "client_user_id": client_id,
        "product_id": product_id,
        "proposal_amount_paid": 40000.0,
        "proposal_amount_pending": 40000.0,
        "proposal_payment_parts": [
            {"id": "part-1", "label": "1st Installment", "amount": 40000.0, "status": "paid"},
            {"id": "part-2", "label": "2nd Installment", "amount": 40000.0, "status": "pending"}
        ],
        "stage": "in_progress"
    }
    db["pre_assessments"].insert_one(pa_doc)

    # 4. Setup Case
    case_id = str(uuid.uuid4())
    case_doc = {
        "id": case_id,
        "case_id": f"LEAMSS-TEST-DOC-{uuid.uuid4().hex[:4]}",
        "client_id": client_id,
        "client_name": "LockedDoc Client",
        "client_email": client_email,
        "product_id": product_id,
        "product_name": "Canada Express Entry",
        "case_manager_id": cm_id,
        "pre_assessment_id": pa_id,
        "sale_id": sale_id,
        "status": "active",
        "current_step": "Assessment & Verification",
        "current_step_order": 1,
        "created_at": datetime.now(timezone.utc)
    }
    db["cases"].insert_one(case_doc)

    case_step_doc = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "step_order": 1,
        "step_name": "Assessment & Verification",
        "status": "in_progress",
        "required_documents": [
            {"doc_name": "Passport Copy", "is_mandatory": True},
            {"doc_name": "Official Assessment Report", "is_mandatory": True, "is_locked_until_paid": True}
        ]
    }
    db["case_steps"].insert_one(case_step_doc)

    try:
        client_token = create_access_token(build_token_payload(client_user))
        client_headers = {"Authorization": f"Bearer {client_token}"}
        cm_token = create_access_token(build_token_payload(cm_user))
        cm_headers = {"Authorization": f"Bearer {cm_token}"}
        admin_token = create_access_token(build_token_payload(admin_user))
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 5. Case Manager uploads the locked document "Official Assessment Report"
        file_content = b"%PDF-1.4 Mock Official Assessment Report content"
        files = {"file": ("Official_Assessment_Report.pdf", io.BytesIO(file_content), "application/pdf")}
        upload_data = {
            "case_id": case_id,
            "step_name": "Assessment & Verification",
            "document_type": "Official Assessment Report"
        }
        up_res = requests.post(f"{API}/documents/upload", files=files, data=upload_data, headers=cm_headers, timeout=10)
        assert up_res.status_code == 200, up_res.text
        doc_id = up_res.json()["id"]

        # 6. Client fetches stepwise documents
        step_docs_res = requests.get(f"{API}/step-documents/case/{case_id}", headers=client_headers, timeout=10)
        assert step_docs_res.status_code == 200, step_docs_res.text
        step_data = step_docs_res.json()
        step1 = step_data["steps"][0]
        locked_doc_item = next(d for d in step1["documents"] if d["doc_name"] == "Official Assessment Report")
        
        # Verify it shows as uploaded, but is_payment_locked is True for client
        assert locked_doc_item["uploaded"] is True
        assert locked_doc_item["is_locked_until_paid"] is True
        assert locked_doc_item["is_payment_locked"] is True
        assert locked_doc_item["payment_pending_amount"] == 40000.0

        # Normal doc (Passport Copy) should NOT be payment locked
        passport_item = next(d for d in step1["documents"] if d["doc_name"] == "Passport Copy")
        assert passport_item["is_payment_locked"] is False

        # 7. Client tries to download locked document -> MUST RETURN 402
        dl_res = requests.get(f"{API}/documents/download/{doc_id}", headers=client_headers, timeout=10)
        assert dl_res.status_code == 402, f"Expected 402 Payment Required, got {dl_res.status_code}"
        assert "locked until full payment" in dl_res.text.lower()

        # 8. Client tries to view locked document -> MUST RETURN 402
        view_res = requests.get(f"{API}/documents/view/{doc_id}", headers=client_headers, timeout=10)
        assert view_res.status_code == 402, f"Expected 402 Payment Required, got {view_res.status_code}"

        # 9. Case Manager CAN download/view the document without restriction
        cm_dl_res = requests.get(f"{API}/documents/download/{doc_id}", headers=cm_headers, timeout=10)
        assert cm_dl_res.status_code == 200

        # 10. Admin confirms full payment (2nd installment paid)
        conf_res = requests.post(f"{API}/payments/confirm-installment/{sale_id}", headers=admin_headers, timeout=10)
        assert conf_res.status_code == 200, conf_res.text
        assert conf_res.json()["fully_paid"] is True

        # 11. Client fetches stepwise documents again -> is_payment_locked is now FALSE!
        step_docs_after = requests.get(f"{API}/step-documents/case/{case_id}", headers=client_headers, timeout=10)
        assert step_docs_after.status_code == 200
        locked_doc_after = next(d for d in step_docs_after.json()["steps"][0]["documents"] if d["doc_name"] == "Official Assessment Report")
        assert locked_doc_after["is_payment_locked"] is False

        # 12. Client downloads document now -> SUCCESS HTTP 200!
        client_dl_after = requests.get(f"{API}/documents/download/{doc_id}", headers=client_headers, timeout=10)
        assert client_dl_after.status_code == 200
        assert client_dl_after.content == file_content

    finally:
        db["users"].delete_many({"id": {"$in": [client_id, admin_id, cm_id]}})
        db["products"].delete_one({"id": product_id})
        db["workflow_steps"].delete_many({"product_id": product_id})
        db["sales"].delete_one({"id": sale_id})
        db["pre_assessments"].delete_one({"id": pa_id})
        db["cases"].delete_one({"id": case_id})
        db["case_steps"].delete_many({"case_id": case_id})
        if 'doc_id' in locals():
            db["documents"].delete_one({"id": doc_id})
