import pytest
import uuid
import httpx
from datetime import datetime, timezone
from pymongo import MongoClient
from server import app
from core.auth import create_access_token, build_token_payload
from core.mail_dispatch import test_smtp_connection as run_test_smtp_connection

@pytest.mark.asyncio
async def test_smtp_connection_detects_auth_failure_cleanly():
    """Verify test_smtp_connection detects Google auth rejection and does not return 'Connection lost'."""
    res = await run_test_smtp_connection(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="pooja.ghatkar@leamss.com",
        smtp_pass="zfyufqvulbmtoyyi"
    )
    assert res["success"] is False
    assert "authentication failed" in res["error"].lower() or "rejected credentials" in res["error"].lower()
    # Ensure raw "Connection lost" error is not exposed
    assert res["error"] != "Connection lost"
    assert "Failed to connect to smtp.gmail.com:587 — Connection lost" not in res["error"]


@pytest.mark.asyncio
async def test_crm_email_send_with_unverified_personal_mailbox():
    """Verify sending email from CRM when salesperson has invalid/unverified personal credentials:
    1. Does NOT crash with 'Connection lost'.
    2. Gracefully dispatches/records in CRM timeline with status 'sent'.
    3. Returns clear feedback with mailbox warning.
    """
    client = MongoClient("mongodb://localhost:27017")
    db = client["leamss"]

    test_uid = str(uuid.uuid4())
    test_sales_email = f"sales_{test_uid[:8]}@leamss.com"
    test_client_email = f"client_{test_uid[:8]}@example.com"
    lead_id = f"lead_{test_uid[:8]}"

    sales_user = {
        "id": test_uid,
        "name": "Test Sales Rep",
        "email": test_sales_email,
        "role": "sr_sales_executive",
        "mailbox_settings": {
            "provider": "gmail",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": test_sales_email,
            "smtp_pass": "invalid_app_pass",
            "sender_name": "Test Sales Rep",
            "sender_email": test_sales_email,
        }
    }
    db.users.insert_one(sales_user)

    test_lead = {
        "id": lead_id,
        "name": "Manali Test Client",
        "email": test_client_email,
        "phone": "9876543210",
        "status": "new",
        "assigned_to": test_uid,
        "created_at": datetime.now(timezone.utc)
    }
    db.leads.insert_one(test_lead)

    sales_token = create_access_token(build_token_payload(sales_user))

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver/api") as http:
            payload = {
                "lead_id": lead_id,
                "to_email": test_client_email,
                "contact_name": "Manali Test Client",
                "subject": "Test Follow-up Consultation",
                "body_html": "<p>Dear Client, your consultation has been scheduled.</p>",
                "notify_by_email": False
            }

            resp = await http.post(
                "/crm/emails/send",
                headers={"Authorization": f"Bearer {sales_token}"},
                json=payload
            )

            assert resp.status_code == 200, f"Send failed: {resp.text}"
            data = resp.json()
            assert data["success"] is True
            # Status must be 'sent' or 'delivered' - NOT 'failed'
            assert data["status"] in ("sent", "delivered")
            # Delivery error must not be "Connection lost"
            assert data.get("delivery_error") != "Connection lost"

            # Check DB record
            email_doc = db.crm_emails.find_one({"id": data["id"]})
            assert email_doc is not None
            assert email_doc["status"] in ("sent", "delivered")
            assert email_doc["to_email"] == test_client_email

            # Check audit log
            activity = db.audit_logs.find_one({"entity_id": lead_id, "action": "email_sent"})
            assert activity is not None

    finally:
        db.users.delete_one({"id": test_uid})
        db.leads.delete_one({"id": lead_id})
        db.crm_emails.delete_many({"lead_id": lead_id})
        db.audit_logs.delete_many({"entity_id": lead_id})
        client.close()
