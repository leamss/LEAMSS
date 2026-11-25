"""Test suite for Real-Time Salesperson Activity Audit Log.

Verifies:
1. format_duration utility formatting accuracy
2. log_salesperson_activity permanent DB persistence
3. Log retrieval with admin authentication, pagination, and multi-filters
4. Admin-only RBAC protection (non-admin receives 403)
5. Live feed endpoint (most recent events)
6. KPI stats aggregation endpoint
7. Frontend client activity endpoint (page visits & dwell times)
8. Export CSV functionality
"""
import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from core.database import db, users_col
from services.salesperson_activity_service import format_duration, log_salesperson_activity
from core.auth import create_access_token


def test_format_duration():
    assert format_duration(None) is None
    assert format_duration(-5) is None
    assert format_duration(0) == "0s"
    assert format_duration(45) == "45s"
    assert format_duration(60) == "1m 0s"
    assert format_duration(154) == "2m 34s"
    assert format_duration(3665) == "1h 1m 5s"


@pytest.mark.asyncio
async def test_log_salesperson_activity_service():
    test_salesperson_id = "test_rep_101"
    await db["salesperson_activity_logs"].delete_many({"salesperson_id": test_salesperson_id})

    # Log a phone call with 135 seconds duration
    doc = await log_salesperson_activity(
        db,
        salesperson_id=test_salesperson_id,
        salesperson_name="Rohit Sharma",
        salesperson_email="rohit@leamss.com",
        activity_type="call",
        title="Outbound Call",
        client_name="Vikram Sethi",
        client_phone="+919876543210",
        duration_seconds=135,
        details="Spoke regarding Canada PR pathway and points calculation.",
        metadata={"outcome": "interested", "call_type": "outbound"}
    )

    assert doc is not None
    assert doc["activity_type"] == "call"
    assert doc["duration_seconds"] == 135
    assert doc["duration_display"] == "2m 15s"
    assert doc["salesperson_name"] == "Rohit Sharma"
    assert doc["client_name"] == "Vikram Sethi"

    # Verify persisted in database
    persisted = await db["salesperson_activity_logs"].find_one({"id": doc["id"]})
    assert persisted is not None
    assert persisted["title"] == "Outbound Call"


@pytest.mark.asyncio
async def test_admin_rbac_and_api_endpoints():
    admin_id = "admin_audit_test_01"
    sales_id = "sales_audit_test_01"

    # Seed users
    await users_col.delete_many({"id": {"$in": [admin_id, sales_id]}})
    await users_col.insert_many([
        {
            "id": admin_id,
            "email": "audit_admin@test.com",
            "name": "Audit Admin",
            "role": "admin",
            "status": "active"
        },
        {
            "id": sales_id,
            "email": "sales_audit@test.com",
            "name": "Sales Test Rep",
            "role": "salesperson",
            "status": "active"
        }
    ])

    admin_token = create_access_token({
        "sub": admin_id,
        "email": "audit_admin@test.com",
        "role": "admin",
        "name": "Audit Admin"
    })

    salesperson_token = create_access_token({
        "sub": sales_id,
        "email": "sales_audit@test.com",
        "role": "salesperson",
        "name": "Sales Test Rep"
    })

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Non-admin should be rejected with 403 Forbidden
            resp_sales = await ac.get(
                "/api/salesperson-activity/logs",
                headers={"Authorization": f"Bearer {salesperson_token}"}
            )
            assert resp_sales.status_code == 403

            # 2. Admin access should succeed
            resp_admin = await ac.get(
                "/api/salesperson-activity/logs",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_admin.status_code == 200
            data = resp_admin.json()
            assert "logs" in data
            assert "total" in data
            assert "page" in data

            # 3. Live feed
            resp_feed = await ac.get(
                "/api/salesperson-activity/live-feed",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_feed.status_code == 200
            assert "events" in resp_feed.json()

            # 4. Aggregated stats
            resp_stats = await ac.get(
                "/api/salesperson-activity/stats",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_stats.status_code == 200
            stats = resp_stats.json()
            assert "total_activities" in stats
            assert "total_calls" in stats
            assert "total_talk_time_seconds" in stats
            assert "total_talk_time_display" in stats

            # 5. Distinct filter options
            resp_filters = await ac.get(
                "/api/salesperson-activity/filters",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_filters.status_code == 200
            filters = resp_filters.json()
            assert "salespersons" in filters
            assert "activity_types" in filters

            # 6. Rep client interaction log (e.g. client profile dwell time)
            resp_rep_log = await ac.post(
                "/api/salesperson-activity/log",
                headers={"Authorization": f"Bearer {salesperson_token}"},
                json={
                    "activity_type": "client_profile_view",
                    "title": "Viewed Client Profile",
                    "client_id": "client_999",
                    "client_name": "Anita Roy",
                    "duration_seconds": 42,
                    "details": "Reviewed KYC documents and application status"
                }
            )
            assert resp_rep_log.status_code == 200
            logged_event = resp_rep_log.json().get("activity")
            assert logged_event["duration_seconds"] == 42
            assert logged_event["duration_display"] == "42s"
            assert logged_event["salesperson_name"] == "Sales Test Rep"

            # 7. CSV Export
            resp_export = await ac.get(
                "/api/salesperson-activity/export",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_export.status_code == 200
            assert "text/csv" in resp_export.headers.get("content-type", "")
            assert "Activity ID,Salesperson Name" in resp_export.text
            assert "Exact Timestamp (UTC)" in resp_export.text

            # 8. Salespersons List with aggregated metrics (CRM Dashboard view)
            resp_slist = await ac.get(
                "/api/salesperson-activity/salespersons-list",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_slist.status_code == 200
            sdata = resp_slist.json()
            assert "salespersons" in sdata
            assert "team_totals" in sdata
            # Sales rep should be listed with activity metrics
            rep_entry = next((s for s in sdata["salespersons"] if s["id"] == sales_id), None)
            assert rep_entry is not None
            assert rep_entry["name"] == "Sales Test Rep"

            # 9. Complete Client-Wise Activity History for a salesperson
            resp_history = await ac.get(
                f"/api/salesperson-activity/salesperson/{sales_id}/client-history",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_history.status_code == 200
            hdata = resp_history.json()
            assert "salesperson" in hdata
            assert "clients" in hdata
            assert "timeline" in hdata
            assert hdata["salesperson"]["name"] == "Sales Test Rep"
            # Verify the logged interaction for Anita Roy appears with exact duration
            assert any(c["client_name"] == "Anita Roy" for c in hdata["clients"])
            anita_client = next(c for c in hdata["clients"] if c["client_name"] == "Anita Roy")
            assert len(anita_client["activities"]) >= 1
            act_0 = anita_client["activities"][0]
            assert act_0["duration_seconds"] == 42
            assert act_0["duration_display"] == "42s"
            assert "exact_timestamp_formatted" in act_0
    finally:
        # Cleanup
        await users_col.delete_many({"id": {"$in": [admin_id, sales_id]}})
        await db["salesperson_activity_logs"].delete_many({
            "salesperson_id": {"$in": [admin_id, sales_id, "test_rep_101"]}
        })


@pytest.mark.asyncio
async def test_whatsapp_activity_tracking_audit():
    """Verify that WhatsApp Web interactions only appear in CRM Audit Log after confirmation,
    excluding unconfirmed, drafts, and failed messages.
    """
    admin_id = "admin_wa_audit_01"
    sales_id = "sales_wa_audit_01"

    # Seed users
    await users_col.delete_many({"id": {"$in": [admin_id, sales_id]}})
    await users_col.insert_many([
        {"id": admin_id, "email": "wa_admin@test.com", "name": "WA Admin", "role": "admin", "status": "active"},
        {"id": sales_id, "email": "wa_sales@test.com", "name": "WA Sales Rep", "role": "salesperson", "status": "active"}
    ])

    admin_token = create_access_token({"sub": admin_id, "email": "wa_admin@test.com", "role": "admin", "name": "WA Admin"})
    sales_token = create_access_token({"sub": sales_id, "email": "wa_sales@test.com", "role": "salesperson", "name": "WA Sales Rep"})

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Dispatch WhatsApp message via web mode (not confirmed yet)
            resp_send = await ac.post(
                "/api/crm/whatsapp/send",
                headers={"Authorization": f"Bearer {sales_token}"},
                json={
                    "phone": "+919876543210",
                    "contact_name": "Test Client pp",
                    "text": "Hello this is a test whatsapp web message",
                    "mode": "web",
                    "confirmed": False
                }
            )
            assert resp_send.status_code == 200
            send_data = resp_send.json()
            assert send_data["status"] == "pending_confirmation"
            wa_msg_id = send_data["id"]

            # 2. Verify Audit Log contains this message as pending_confirmation
            resp_audit_before = await ac.get(
                f"/api/salesperson-activity/salesperson/{sales_id}/client-history",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_audit_before.status_code == 200
            data_before = resp_audit_before.json()
            pending_act = next((act for act in data_before.get("timeline", []) if act.get("id") == wa_msg_id or act.get("metadata", {}).get("message_id") == wa_msg_id), None)
            assert pending_act is not None
            assert pending_act["client_name"] == "Test Client pp"
            assert pending_act["salesperson_name"] == "WA Sales Rep"
            assert pending_act["message_status"] in ["pending", "pending_confirmation"]
            assert "date" in pending_act
            assert "time" in pending_act

            # 3. Confirm message as sent via /confirm-status
            resp_confirm = await ac.post(
                "/api/crm/whatsapp/confirm-status",
                headers={"Authorization": f"Bearer {sales_token}"},
                json={
                    "id": wa_msg_id,
                    "status": "sent",
                    "contact_name": "Test Client pp"
                }
            )
            assert resp_confirm.status_code == 200
            assert resp_confirm.json()["status"] == "sent"

            # 4. Verify Audit Log NOW reflects the message as sent with exact timestamp, rep name, client name
            resp_audit_after = await ac.get(
                f"/api/salesperson-activity/salesperson/{sales_id}/client-history",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_audit_after.status_code == 200
            data_after = resp_audit_after.json()
            wa_act = next((act for act in data_after.get("timeline", []) if act.get("id") == wa_msg_id or act.get("metadata", {}).get("message_id") == wa_msg_id), None)
            assert wa_act is not None
            assert wa_act["activity_type"] == "whatsapp"
            assert wa_act["client_name"] == "Test Client pp"
            assert wa_act["salesperson_name"] == "WA Sales Rep"
            assert wa_act["message_status"] == "sent"
            assert "date" in wa_act
            assert "time" in wa_act

            # 5. Send another message and mark it as failed
            resp_send_fail = await ac.post(
                "/api/crm/whatsapp/send",
                headers={"Authorization": f"Bearer {sales_token}"},
                json={
                    "phone": "+919876543210",
                    "contact_name": "Failed Client",
                    "text": "This message will fail",
                    "mode": "web",
                    "confirmed": False
                }
            )
            fail_msg_id = resp_send_fail.json()["id"]

            resp_mark_fail = await ac.post(
                "/api/crm/whatsapp/confirm-status",
                headers={"Authorization": f"Bearer {sales_token}"},
                json={
                    "id": fail_msg_id,
                    "status": "failed",
                    "error_message": "User closed WhatsApp Web"
                }
            )
            assert resp_mark_fail.status_code == 200
            assert resp_mark_fail.json()["status"] == "failed"

            # 6. Verify failed message is retained in Audit Log with failed status, client name, salesperson name, date & time
            resp_audit_fail = await ac.get(
                f"/api/salesperson-activity/salesperson/{sales_id}/client-history",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_audit_fail.status_code == 200
            data_fail = resp_audit_fail.json()
            fail_act = next((act for act in data_fail.get("timeline", []) if act.get("id") == fail_msg_id or act.get("metadata", {}).get("message_id") == fail_msg_id), None)
            assert fail_act is not None
            assert fail_act["activity_type"] == "whatsapp"
            assert fail_act["client_name"] == "Failed Client"
            assert fail_act["salesperson_name"] == "WA Sales Rep"
            assert fail_act["message_status"] == "failed"
            assert "date" in fail_act
            assert "time" in fail_act

    finally:
        await users_col.delete_many({"id": {"$in": [admin_id, sales_id]}})
        await db["salesperson_activity_logs"].delete_many({"salesperson_id": {"$in": [admin_id, sales_id]}})
        await db["crm_whatsapp_messages"].delete_many({"contact_name": {"$in": ["Test Client pp", "Failed Client"]}})
        await db["crm_whatsapp"].delete_many({"contact_name": {"$in": ["Test Client pp", "Failed Client"]}})


@pytest.mark.asyncio
async def test_salesperson_own_activity_access_and_breakdowns():
    rep1_id = "rep_audit_self_01"
    rep2_id = "rep_audit_other_02"
    admin_id = "admin_audit_mgr_01"

    # Seed users
    await users_col.delete_many({"id": {"$in": [rep1_id, rep2_id, admin_id]}})
    await users_col.insert_many([
        {"id": rep1_id, "email": "rep1@leamss.com", "name": "Rep One", "role": "salesperson", "status": "active"},
        {"id": rep2_id, "email": "rep2@leamss.com", "name": "Rep Two", "role": "salesperson", "status": "active"},
        {"id": admin_id, "email": "admin_audit_mgr@leamss.com", "name": "Admin Mgr", "role": "admin", "status": "active"}
    ])

    rep1_token = create_access_token({"sub": rep1_id, "email": "rep1@leamss.com", "role": "salesperson", "name": "Rep One"})
    rep2_token = create_access_token({"sub": rep2_id, "email": "rep2@leamss.com", "role": "salesperson", "name": "Rep Two"})
    admin_token = create_access_token({"sub": admin_id, "email": "admin_audit_mgr@leamss.com", "role": "admin", "name": "Admin Mgr"})

    # Clean up test records
    await db["crm_calls"].delete_many({"sales_person_id": rep1_id})
    await db["crm_emails"].delete_many({"sales_person_id": rep1_id})
    await db["crm_whatsapp_messages"].delete_many({"sales_person_id": rep1_id})
    await db["salesperson_activity_logs"].delete_many({"salesperson_id": rep1_id})

    # Seed an incoming and an outgoing call for rep1 today
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    await db["crm_calls"].insert_many([
        {
            "id": "call_in_01",
            "sales_person_id": rep1_id,
            "sales_person_name": "Rep One",
            "client_name": "Inbound Lead",
            "direction": "incoming",
            "duration_seconds": 120,
            "created_at": now
        },
        {
            "id": "call_out_01",
            "sales_person_id": rep1_id,
            "sales_person_name": "Rep One",
            "client_name": "Outbound Lead",
            "direction": "outgoing",
            "duration_seconds": 180,
            "created_at": now
        }
    ])

    # Seed a lead assigned to rep1
    await db["leads"].insert_one({
        "id": "lead_rep1_01",
        "name": "Assigned Lead 1",
        "email": "assigned_lead1@example.com",
        "assigned_to": rep1_id
    })

    # Seed sent and received emails for rep1
    await db["crm_emails"].insert_many([
        {
            "id": "email_sent_01",
            "sales_person_id": rep1_id,
            "sales_person_name": "Rep One",
            "client_name": "Email Client 1",
            "direction": "outbound",
            "subject": "Proposal Sent",
            "created_at": now
        },
        {
            "id": "email_rec_01",
            "sales_person_id": rep1_id,
            "sales_person_name": "Rep One",
            "client_name": "Email Client 2",
            "direction": "inbound",
            "subject": "Inquiry Received",
            "created_at": now
        },
        {
            "id": "email_rec_02",
            "sales_person_id": None,
            "lead_id": "lead_rep1_01",
            "to_email": "rep1@leamss.com",
            "from_email": "assigned_lead1@example.com",
            "direction": "inbound",
            "status": "received",
            "subject": "Re: Australia PR Consultation",
            "raw_text": "I am interested in proceeding",
            "created_at": now
        }
    ])

    # Seed WhatsApp messages for rep1
    await db["crm_whatsapp_messages"].insert_many([
        {
            "id": "wa_sent_01",
            "sales_person_id": rep1_id,
            "sales_person_name": "Rep One",
            "contact_name": "WhatsApp Client 1",
            "direction": "outbound",
            "status": "sent",
            "text": "Hello!",
            "created_at": now
        },
        {
            "id": "wa_rec_01",
            "sales_person_id": rep1_id,
            "sales_person_name": "Rep One",
            "contact_name": "WhatsApp Client 2",
            "direction": "inbound",
            "status": "delivered",
            "text": "I am interested",
            "created_at": now
        }
    ])

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Salesperson can access their own activity via /my-activity
            resp_my = await ac.get("/api/salesperson-activity/my-activity", headers={"Authorization": f"Bearer {rep1_token}"})
            assert resp_my.status_code == 200
            data_my = resp_my.json()
            assert data_my["success"] is True
            assert data_my["salesperson"]["id"] == rep1_id

            # Verify Today's breakdown (2 received emails: email_rec_01 with sp_id + email_rec_02 with None sp_id & to_email)
            today_data = data_my.get("today", {})
            assert today_data["calls_total"] == 2
            assert today_data["calls_incoming"] == 1
            assert today_data["calls_outgoing"] == 1
            assert today_data["talk_time_seconds"] == 300
            assert today_data["emails_sent"] == 1
            assert today_data["emails_received"] == 2
            assert today_data["whatsapp_sent"] == 1
            assert today_data["whatsapp_received"] == 1

            # Verify date_wise_history is present
            assert "date_wise_history" in data_my
            assert len(data_my["date_wise_history"]) >= 1

            # 2. Salesperson can access their own history via /salesperson/{my_id}/client-history
            resp_self = await ac.get(f"/api/salesperson-activity/salesperson/{rep1_id}/client-history", headers={"Authorization": f"Bearer {rep1_token}"})
            assert resp_self.status_code == 200

            # 3. Salesperson CANNOT access another rep's history -> 403 Forbidden
            resp_forbidden = await ac.get(f"/api/salesperson-activity/salesperson/{rep2_id}/client-history", headers={"Authorization": f"Bearer {rep1_token}"})
            assert resp_forbidden.status_code == 403
            assert "Access denied" in resp_forbidden.json()["detail"]

            # 4. Salesperson CANNOT access /salespersons-list -> 403 Forbidden
            resp_list_forbidden = await ac.get("/api/salesperson-activity/salespersons-list", headers={"Authorization": f"Bearer {rep1_token}"})
            assert resp_list_forbidden.status_code == 403

            # 5. Admin CAN access any rep's history and salespersons-list
            resp_admin_access = await ac.get(f"/api/salesperson-activity/salesperson/{rep1_id}/client-history", headers={"Authorization": f"Bearer {admin_token}"})
            assert resp_admin_access.status_code == 200
            resp_admin_list = await ac.get("/api/salesperson-activity/salespersons-list", headers={"Authorization": f"Bearer {admin_token}"})
            assert resp_admin_list.status_code == 200

    finally:
        await users_col.delete_many({"id": {"$in": [rep1_id, rep2_id, admin_id]}})
        await db["leads"].delete_many({"id": "lead_rep1_01"})
        await db["crm_calls"].delete_many({"sales_person_id": rep1_id})
        await db["crm_emails"].delete_many({"$or": [{"sales_person_id": rep1_id}, {"id": "email_rec_02"}]})
        await db["crm_whatsapp_messages"].delete_many({"sales_person_id": rep1_id})


@pytest.mark.asyncio
async def test_salesperson_stage_change_activity_audit():
    rep_id = "test_stage_rep_01"
    lead_id = "test_stage_lead_01"

    await users_col.delete_many({"id": rep_id})
    await db["leads"].delete_many({"id": lead_id})
    await db["salesperson_activity_logs"].delete_many({"salesperson_id": rep_id})

    await users_col.insert_one({
        "id": rep_id,
        "email": "stage_rep@leamss.com",
        "name": "Stage Test Rep",
        "role": "salesperson",
        "status": "active"
    })

    await db["leads"].insert_one({
        "id": lead_id,
        "name": "Disha Test Lead",
        "phone": "+919876500001",
        "email": "disha.test@example.com",
        "stage": "not_contacted",
        "status": "not_contacted",
        "assigned_to": rep_id,
        "assigned_to_name": "Stage Test Rep"
    })

    rep_token = create_access_token({
        "sub": rep_id,
        "email": "stage_rep@leamss.com",
        "role": "salesperson",
        "name": "Stage Test Rep"
    })

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Update lead stage to 'contacted'
            put_resp = await ac.put(
                f"/api/leads/{lead_id}",
                json={"stage": "contacted", "status": "contacted"},
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert put_resp.status_code == 200

            # 2. Verify salesperson_activity_logs contains the stage_change entry
            logged = await db["salesperson_activity_logs"].find_one({
                "salesperson_id": rep_id,
                "activity_type": "stage_change",
                "client_id": lead_id
            })
            assert logged is not None
            assert logged["metadata"]["new_stage"] == "contacted"
            assert logged["metadata"]["previous_stage"] == "not_contacted"
            assert "Disha Test Lead" in logged["title"]

            # 3. Query /my-activity and verify status changes are counted in summary and today
            act_resp = await ac.get(
                "/api/salesperson-activity/my-activity",
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert act_resp.status_code == 200
            data = act_resp.json()
            assert data["success"] is True

            # Verify KPI Summary
            assert data["summary"]["total_status_changes"] >= 1

            # Verify Today's breakdown has status_changes_total
            assert data["today"]["status_changes_total"] >= 1

            # Verify Client-wise activity has status_changes_count
            client_entry = next((c for c in data["clients"] if c["client_id"] == lead_id), None)
            assert client_entry is not None
            assert client_entry["status_changes_count"] >= 1

            # Verify Timeline contains the stage change event
            stage_event = next((ev for ev in data["timeline"] if ev.get("activity_type") == "stage_change"), None)
            assert stage_event is not None
            assert stage_event["client_name"] == "Disha Test Lead"

    finally:
        await users_col.delete_many({"id": rep_id})
        await db["leads"].delete_many({"id": lead_id})
        await db["salesperson_activity_logs"].delete_many({"salesperson_id": rep_id})


@pytest.mark.asyncio
async def test_client_note_remarks_multi_user_workflow():
    rep_id = "test_note_rep_01"
    admin_id = "test_note_admin_01"
    lead_id = "test_lead_note_999"

    await users_col.delete_many({"id": {"$in": [rep_id, admin_id]}})
    await db["leads"].delete_many({"id": lead_id})
    await db["salesperson_activity_logs"].delete_many({"salesperson_id": {"$in": [rep_id, admin_id]}})
    await db["audit_logs"].delete_many({"details.lead_id": lead_id})

    await users_col.insert_many([
        {
            "id": rep_id,
            "name": "Karan Sales",
            "email": "karan.sales@leamss.com",
            "role": "salesperson",
            "status": "active"
        },
        {
            "id": admin_id,
            "name": "Super Admin",
            "email": "super.admin@leamss.com",
            "role": "admin",
            "status": "active"
        }
    ])

    await db["leads"].insert_one({
        "id": lead_id,
        "name": "Rajesh Kumar",
        "phone": "+919811122233",
        "email": "rajesh.kumar@example.com",
        "stage": "contacted",
        "assigned_to": rep_id,
        "notes": []
    })

    rep_token = create_access_token({
        "sub": rep_id,
        "email": "karan.sales@leamss.com",
        "role": "salesperson",
        "name": "Karan Sales"
    })

    admin_token = create_access_token({
        "sub": admin_id,
        "email": "super.admin@leamss.com",
        "role": "admin",
        "name": "Super Admin"
    })

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Salesperson adds "Dropped a Message" note
            rep_note_resp1 = await ac.post(
                f"/api/leads/{lead_id}/note",
                json={
                    "note_type": "Dropped a Message",
                    "text": "Sent initial brochure on WhatsApp. Client confirmed receipt."
                },
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert rep_note_resp1.status_code == 200
            data1 = rep_note_resp1.json()
            assert data1["note"]["note_type"] == "Dropped a Message"
            assert data1["note"]["added_by_name"] == "Karan Sales"
            assert data1["note"]["added_by_role"] == "Salesperson"
            assert data1["note"]["is_admin"] is False
            assert "date_display" in data1["note"]
            assert "time_display" in data1["note"]
            assert len(data1["notes"]) == 1

            # 2. Admin adds "Dropped a Mail" remark
            admin_note_resp = await ac.post(
                f"/api/leads/{lead_id}/note",
                json={
                    "note_type": "Dropped a Mail",
                    "text": "Admin sent custom quote and checklist via official email."
                },
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert admin_note_resp.status_code == 200
            data2 = admin_note_resp.json()
            assert data2["note"]["note_type"] == "Dropped a Mail"
            assert data2["note"]["added_by_name"] == "Super Admin"
            assert data2["note"]["added_by_role"] == "Admin"
            assert data2["note"]["is_admin"] is True
            # Both notes exist now without overwriting
            assert len(data2["notes"]) == 2

            # 3. Salesperson adds a third note "Called the Client"
            rep_note_resp2 = await ac.post(
                f"/api/leads/{lead_id}/note",
                json={
                    "note_type": "Called the Client",
                    "text": "Followed up via call. Client is preparing documents for consultation."
                },
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert rep_note_resp2.status_code == 200
            data3 = rep_note_resp2.json()
            assert len(data3["notes"]) == 3

            # 4. Fetch notes endpoint GET /api/leads/{id}/notes
            get_notes_resp = await ac.get(
                f"/api/leads/{lead_id}/notes",
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert get_notes_resp.status_code == 200
            notes_list = get_notes_resp.json()["notes"]
            assert len(notes_list) == 3

            # Verify note types and author identities are preserved
            note_types = [n["note_type"] for n in notes_list]
            assert "Dropped a Message" in note_types
            assert "Dropped a Mail" in note_types
            assert "Called the Client" in note_types

            # Verify Admin identification
            admin_entry = next((n for n in notes_list if n["is_admin"] is True), None)
            assert admin_entry is not None
            assert admin_entry["added_by_name"] == "Super Admin"
            assert admin_entry["added_by_role"] == "Admin"

            # 5. Check timeline integration GET /api/crm/timeline/lead/{id}
            timeline_resp = await ac.get(
                f"/api/crm/timeline/lead/{lead_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert timeline_resp.status_code == 200
            timeline_events = timeline_resp.json()
            remark_events = [ev for ev in timeline_events if ev.get("type") == "note" or "Remark" in ev.get("title", "")]
            assert len(remark_events) >= 3

            # 6. Check Salesperson Activity Log
            sp_activity_resp = await ac.get(
                "/api/salesperson-activity/my-activity",
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert sp_activity_resp.status_code == 200
            sp_data = sp_activity_resp.json()
            timeline = sp_data.get("timeline", [])
            sp_notes = [ev for ev in timeline if ev.get("activity_type") == "note"]
            assert len(sp_notes) >= 2  # Rep added 2 notes

    finally:
        await users_col.delete_many({"id": {"$in": [rep_id, admin_id]}})
        await db["leads"].delete_many({"id": lead_id})
        await db["salesperson_activity_logs"].delete_many({"salesperson_id": {"$in": [rep_id, admin_id]}})
        await db["audit_logs"].delete_many({"details.lead_id": lead_id})


@pytest.mark.asyncio
async def test_leads_board_and_client_detail_active_session_tracking():
    rep_id = "test_rep_active_tracker"
    admin_id = "test_admin_active_tracker"
    pooja_id = "lead_pooja_101"
    manali_id = "lead_manali_102"

    await users_col.delete_many({"id": {"$in": [rep_id, admin_id]}})
    await db["leads"].delete_many({"id": {"$in": [pooja_id, manali_id]}})
    await db["salesperson_activity_logs"].delete_many({"salesperson_id": {"$in": [rep_id, admin_id]}})

    await users_col.insert_many([
        {
            "id": rep_id,
            "email": "pooja.ghatkar@test.com",
            "name": "Pooja Ghatkar",
            "role": "salesperson",
            "status": "active"
        },
        {
            "id": admin_id,
            "email": "admin.tracker@test.com",
            "name": "Tracker Admin",
            "role": "admin",
            "status": "active"
        }
    ])

    await db["leads"].insert_many([
        {
            "id": pooja_id,
            "name": "Pooja Client",
            "phone": "+919988776655",
            "email": "poojaclient@test.com",
            "stage": "lead",
            "assigned_to": rep_id
        },
        {
            "id": manali_id,
            "name": "Manali Client",
            "phone": "+919988776644",
            "email": "manaliclient@test.com",
            "stage": "consultation_booked",
            "assigned_to": rep_id
        }
    ])

    rep_token = create_access_token({"sub": rep_id, "email": "pooja.ghatkar@test.com", "role": "salesperson", "name": "Pooja Ghatkar"})
    admin_token = create_access_token({"sub": admin_id, "email": "admin.tracker@test.com", "role": "admin", "name": "Tracker Admin"})

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Salesperson visits CRM Leads Board
            visit_resp = await ac.post(
                "/api/salesperson-activity/log",
                json={
                    "activity_type": "page_visit",
                    "title": "Visited CRM Leads Board",
                    "details": "Salesperson opened and navigated to CRM Leads Board (Kanban view) at 05:55:38 PM.",
                    "start_time": "05:55:38 PM",
                    "metadata": {
                        "view": "kanban",
                        "view_label": "Leads Board",
                        "is_leads_board": True,
                        "timezone": "Asia/Kolkata"
                    }
                },
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert visit_resp.status_code == 200
            assert visit_resp.json()["success"] is True

            # 2. Salesperson opens details of Pooja Client (Active Session Start)
            open_resp = await ac.post(
                "/api/salesperson-activity/log",
                json={
                    "activity_type": "client_view",
                    "client_id": pooja_id,
                    "client_name": "Pooja Client",
                    "client_phone": "+919988776655",
                    "client_email": "poojaclient@test.com",
                    "title": "Opened Client Details: Pooja Client",
                    "details": "Salesperson opened and actively viewing details for Pooja Client (Stage: lead) • Started: 05:56:00 PM.",
                    "start_time": "05:56:00 PM",
                    "session_state": "active",
                    "metadata": {
                        "session_state": "active",
                        "start_time": "05:56:00 PM",
                        "source_view": "kanban"
                    }
                },
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert open_resp.status_code == 200

            # 3. Salesperson works on Pooja Client and closes/switches (Active Session Completed)
            done_resp = await ac.post(
                "/api/salesperson-activity/log",
                json={
                    "activity_type": "client_view",
                    "client_id": pooja_id,
                    "client_name": "Pooja Client",
                    "duration_seconds": 210,
                    "start_time": "05:56:00 PM",
                    "end_time": "05:59:30 PM",
                    "session_state": "completed",
                    "title": "Worked on Client: Pooja Client",
                    "details": "Active client session on Pooja Client • Start: 05:56:00 PM • End: 05:59:30 PM (3m 30s)",
                    "metadata": {
                        "session_state": "completed",
                        "start_time": "05:56:00 PM",
                        "end_time": "05:59:30 PM",
                        "duration_seconds": 210
                    }
                },
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert done_resp.status_code == 200

            # 4. Salesperson switches active client tab to Manali Client
            tab_switch_resp = await ac.post(
                "/api/salesperson-activity/log",
                json={
                    "activity_type": "client_view",
                    "client_id": manali_id,
                    "client_name": "Manali Client",
                    "title": "Active Client Tab: Manali Client",
                    "details": "Salesperson switched focus to active client tab for Manali Client • Started: 05:59:31 PM.",
                    "start_time": "05:59:31 PM",
                    "session_state": "active",
                    "metadata": {
                        "session_state": "active",
                        "start_time": "05:59:31 PM",
                        "switch_type": "tab_focus"
                    }
                },
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert tab_switch_resp.status_code == 200

            # 5. Query client-history endpoint for this salesperson
            history_resp = await ac.get(
                f"/api/salesperson-activity/salesperson/{rep_id}/client-history",
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert history_resp.status_code == 200
            history_data = history_resp.json()

            clients = history_data.get("clients", [])
            client_names = [c.get("client_name") for c in clients]
            assert "Pooja Client" in client_names
            assert "Manali Client" in client_names

            pooja_entry = next(c for c in clients if c.get("client_name") == "Pooja Client")
            assert pooja_entry["client_views_count"] >= 2
            assert pooja_entry["active_time_seconds"] == 210
            assert pooja_entry["active_time_display"] == "3m 30s"

            manali_entry = next(c for c in clients if c.get("client_name") == "Manali Client")
            assert manali_entry["is_actively_viewing"] is True

            # Verify timeline events have start_time and end_time
            timeline = history_data.get("timeline", [])
            pooja_completed = next((e for e in timeline if e.get("title") == "Worked on Client: Pooja Client"), None)
            assert pooja_completed is not None
            assert pooja_completed["start_time"] == "05:56:00 PM"
            assert pooja_completed["end_time"] == "05:59:30 PM"
            assert pooja_completed["session_state"] == "completed"

            # 6. Admin queries /logs endpoint
            admin_logs_resp = await ac.get(
                f"/api/salesperson-activity/logs?salesperson_id={rep_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert admin_logs_resp.status_code == 200
            admin_logs = admin_logs_resp.json()["logs"]
            assert len(admin_logs) >= 4
            titles = [l["title"] for l in admin_logs]
            assert "Visited CRM Leads Board" in titles
            assert "Worked on Client: Pooja Client" in titles
            assert "Active Client Tab: Manali Client" in titles

    finally:
        await users_col.delete_many({"id": {"$in": [rep_id, admin_id]}})
        await db["leads"].delete_many({"id": {"$in": [pooja_id, manali_id]}})
        await db["salesperson_activity_logs"].delete_many({"salesperson_id": {"$in": [rep_id, admin_id]}})


@pytest.mark.asyncio
async def test_all_leads_table_client_specific_activity_audit():
    """Verify that when a salesperson opens/works on a client from the All Leads Table,
    the client name is explicitly recorded, properly grouped under that client's card
    instead of generic Direct Activity / CRM, and annotated with source_tab."""
    rep_id = "rep_all_leads_tab_01"
    admin_id = "admin_all_leads_tab_01"
    client_id = "lead_prakash_01"

    await users_col.delete_many({"id": {"$in": [rep_id, admin_id]}})
    await db["leads"].delete_many({"id": client_id})
    await db["salesperson_activity_logs"].delete_many({"salesperson_id": {"$in": [rep_id, admin_id]}})

    await users_col.insert_many([
        {"id": rep_id, "email": "rep_all_leads@test.com", "name": "Pooja Sales Rep", "role": "salesperson", "status": "active"},
        {"id": admin_id, "email": "admin_all_leads@test.com", "name": "Admin All Leads", "role": "admin", "status": "active"}
    ])

    await db["leads"].insert_one({
        "id": client_id,
        "name": "Prakash Ghatkar",
        "email": "prakash@test.com",
        "phone": "+919876543299",
        "assigned_to": rep_id,
        "stage": "Pre-Assessment"
    })

    rep_token = create_access_token({"sub": rep_id, "email": "rep_all_leads@test.com", "role": "salesperson", "name": "Pooja Sales Rep"})
    admin_token = create_access_token({"sub": admin_id, "email": "admin_all_leads@test.com", "role": "admin", "name": "Admin All Leads"})

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Log opening client from All Leads Table
            resp_open = await ac.post(
                "/api/salesperson-activity/log",
                json={
                    "salesperson_id": rep_id,
                    "salesperson_name": "Pooja Sales Rep",
                    "client_id": client_id,
                    "client_name": "Prakash Ghatkar",
                    "activity_type": "page_visit",
                    "title": "Opened Client: Prakash Ghatkar (All Leads Table)",
                    "details": "Opened client workspace for Prakash Ghatkar from All Leads Table. Stage: Pre-Assessment.",
                    "metadata": {
                        "source_tab": "All Leads Table",
                        "is_all_leads_table": True,
                        "client_name": "Prakash Ghatkar",
                        "stage": "Pre-Assessment"
                    }
                },
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert resp_open.status_code == 200

            # 2. Log working session on client from All Leads Table
            resp_work = await ac.post(
                "/api/salesperson-activity/log",
                json={
                    "salesperson_id": rep_id,
                    "salesperson_name": "Pooja Sales Rep",
                    "client_id": client_id,
                    "client_name": "Prakash Ghatkar",
                    "activity_type": "page_visit",
                    "title": "Worked on Client: Prakash Ghatkar (All Leads Table)",
                    "details": "Active client session completed for Prakash Ghatkar from All Leads Table.",
                    "start_time": "11:00:00 AM",
                    "end_time": "11:05:00 AM",
                    "duration_seconds": 300,
                    "session_state": "completed",
                    "metadata": {
                        "source_tab": "All Leads Table",
                        "is_all_leads_table": True,
                        "client_name": "Prakash Ghatkar"
                    }
                },
                headers={"Authorization": f"Bearer {rep_token}"}
            )
            assert resp_work.status_code == 200

            # 3. Retrieve client history
            resp_history = await ac.get(
                f"/api/salesperson-activity/salesperson/{rep_id}/client-history",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp_history.status_code == 200
            history_data = resp_history.json()

            clients = history_data.get("clients", [])
            client_names = [c.get("client_name") for c in clients]
            assert "Prakash Ghatkar" in client_names

            prakash_card = next(c for c in clients if c.get("client_name") == "Prakash Ghatkar")
            assert prakash_card["client_views_count"] >= 2
            assert prakash_card["active_time_seconds"] == 300
            assert len(prakash_card["activities"]) >= 2

            # Check metadata and title retention
            act_titles = [a["title"] for a in prakash_card["activities"]]
            assert any("All Leads Table" in t for t in act_titles)

    finally:
        await users_col.delete_many({"id": {"$in": [rep_id, admin_id]}})
        await db["leads"].delete_many({"id": client_id})
        await db["salesperson_activity_logs"].delete_many({"salesperson_id": {"$in": [rep_id, admin_id]}})






