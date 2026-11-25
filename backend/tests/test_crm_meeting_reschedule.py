import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from server import app
from core.auth import create_access_token
from core.database import db

crm_meetings_col = db["crm_meetings"]
leads_col = db["leads"]
users_col = db["users"]


@pytest.mark.asyncio
async def test_meeting_reschedule_mandatory_reason_validation():
    """Verify that attempting to reschedule a meeting without a reason fails with 400 Bad Request."""
    user_id = str(uuid.uuid4())
    test_user = {
        "id": user_id,
        "email": f"consultant_{uuid.uuid4().hex[:6]}@example.com",
        "name": "Consultant John",
        "role": "sales_person",
        "user_type": "internal_salesperson"
    }
    await users_col.insert_one(test_user)
    token = create_access_token({"sub": user_id, "role": "sales_person"})
    headers = {"Authorization": f"Bearer {token}"}

    meeting_id = str(uuid.uuid4())
    lead_id = str(uuid.uuid4())

    await crm_meetings_col.insert_one({
        "id": meeting_id,
        "lead_id": lead_id,
        "title": "PR Consultation",
        "meeting_type": "Calendly",
        "meeting_date": "2026-11-20",
        "meeting_time": "14:00",
        "duration_minutes": 30,
        "meeting_link": "https://meet.google.com/test-meet-123",
        "sales_person_id": user_id,
        "sales_person_name": "Consultant John",
        "contact_name": "Client Test",
        "contact_email": "client_test@example.com",
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc)
    })

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Missing reason completely
            res1 = await ac.post(
                f"/api/crm/meetings/{meeting_id}/reschedule",
                json={
                    "meeting_date": "2026-11-25",
                    "meeting_time": "15:30",
                    "duration_minutes": 30,
                    "reason": ""  # Empty reason
                },
                headers=headers
            )
            assert res1.status_code == 400
            assert "reason" in res1.json()["detail"].lower()

            # 2. Whitespace-only reason
            res2 = await ac.post(
                f"/api/crm/meetings/{meeting_id}/reschedule",
                json={
                    "meeting_date": "2026-11-25",
                    "meeting_time": "15:30",
                    "reason": "    "
                },
                headers=headers
            )
            assert res2.status_code == 400
            assert "reason" in res2.json()["detail"].lower()
    finally:
        await users_col.delete_one({"id": user_id})
        await crm_meetings_col.delete_one({"id": meeting_id})


@pytest.mark.asyncio
async def test_meeting_reschedule_success_and_audit_history(monkeypatch):
    """Verify rescheduling with valid reason updates meeting, retains history, and syncs lead."""
    async def mock_resched(**kwargs):
        return {
            "success": True,
            "new_event_id": "test-resched-cal-id",
            "new_invitee_id": "test-resched-inv-id",
            "meeting_link": "https://meet.google.com/test-meet-resched",
            "reschedule_url": "https://calendly.com/reschedulings/test-uuid",
            "cancel_url": "https://calendly.com/cancellations/test-uuid"
        }
    from services.integrations import calendly_service
    monkeypatch.setattr(calendly_service, "reschedule_calendly_event_via_api", mock_resched)

    user_id = str(uuid.uuid4())
    test_user = {
        "id": user_id,
        "email": f"consultant_{uuid.uuid4().hex[:6]}@example.com",
        "name": "Consultant Sarah",
        "role": "sales_person",
        "user_type": "internal_salesperson"
    }
    await users_col.insert_one(test_user)
    token = create_access_token({"sub": user_id, "role": "sales_person"})
    headers = {"Authorization": f"Bearer {token}"}

    meeting_id = str(uuid.uuid4())
    lead_id = str(uuid.uuid4())

    await leads_col.insert_one({
        "id": lead_id,
        "name": "Client Reschedule Target",
        "email": "client_reschedule@example.com",
        "phone": "+919876543210",
        "source": "Website",
        "has_booking": True,
        "calendly_booking": {
            "event_name": "PR Assessment",
            "date": "2026-11-20",
            "time": "11:00",
            "meeting_link": "https://meet.google.com/test-meet-resched"
        }
    })

    await crm_meetings_col.insert_one({
        "id": meeting_id,
        "lead_id": lead_id,
        "title": "PR Assessment",
        "meeting_type": "Calendly",
        "meeting_date": "2026-11-20",
        "meeting_time": "11:00",
        "duration_minutes": 30,
        "meeting_link": "https://meet.google.com/test-meet-resched",
        "sales_person_id": user_id,
        "sales_person_name": "Consultant Sarah",
        "contact_name": "Client Reschedule Target",
        "contact_email": "client_reschedule@example.com",
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc)
    })

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            reschedule_payload = {
                "meeting_date": "2026-11-24",
                "meeting_time": "16:00",
                "duration_minutes": 45,
                "reason": "Client requested afternoon slot due to office meeting",
                "notes": "Client will provide IELTS TRF copy prior to the meeting",
                "notify_client": False  # Avoid real email in test
            }

            res = await ac.post(
                f"/api/crm/meetings/{meeting_id}/reschedule",
                json=reschedule_payload,
                headers=headers
            )
            assert res.status_code == 200, res.text
            res_data = res.json()
            assert res_data["success"] is True
            assert res_data["meeting"]["status"] == "rescheduled"
            assert res_data["meeting"]["meeting_date"] == "2026-11-24"
            assert res_data["meeting"]["meeting_time"] == "16:00"

            # Check DB meeting doc
            m_db = await crm_meetings_col.find_one({"id": meeting_id})
            assert m_db is not None
            assert m_db["status"] == "rescheduled"
            assert m_db["meeting_date"] == "2026-11-24"
            assert m_db["meeting_time"] == "16:00"
            assert m_db["duration_minutes"] == 45
            assert m_db["reschedule_reason"] == "Client requested afternoon slot due to office meeting"
            assert len(m_db.get("reschedule_history", [])) == 1
            hist_item = m_db["reschedule_history"][0]
            assert hist_item["old_date"] == "2026-11-20"
            assert hist_item["old_time"] == "11:00"
            assert hist_item["new_date"] == "2026-11-24"
            assert hist_item["new_time"] == "16:00"
            assert hist_item["reason"] == "Client requested afternoon slot due to office meeting"
            assert hist_item["rescheduled_by_name"] == "Consultant Sarah"

            # Check DB lead doc was synchronized
            l_db = await leads_col.find_one({"id": lead_id})
            assert l_db is not None
            cb = l_db.get("calendly_booking", {})
            assert cb.get("date") == "2026-11-24"
            assert cb.get("time") == "16:00"
            notes = l_db.get("notes", [])
            assert any("Client requested afternoon slot due to office meeting" in n.get("text", "") for n in notes)
    finally:
        await users_col.delete_one({"id": user_id})
        await crm_meetings_col.delete_one({"id": meeting_id})
        await leads_col.delete_one({"id": lead_id})


@pytest.mark.asyncio
async def test_meeting_recording_transcript_and_recap():
    """Verify saving and retrieving meeting recording link, transcripts, participants, and AI summary."""
    user_id = str(uuid.uuid4())
    test_user = {
        "id": user_id,
        "email": f"admin_{uuid.uuid4().hex[:6]}@example.com",
        "name": "Admin Director",
        "role": "admin",
        "user_type": "super_admin"
    }
    await users_col.insert_one(test_user)
    token = create_access_token({"sub": user_id, "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    meeting_id = str(uuid.uuid4())
    await crm_meetings_col.insert_one({
        "id": meeting_id,
        "title": "Express Entry Consultation",
        "meeting_type": "Google Meet",
        "meeting_date": "2026-11-18",
        "meeting_time": "10:00",
        "duration_minutes": 30,
        "meeting_link": "https://meet.google.com/test-rec",
        "contact_name": "Transcript Client",
        "contact_email": "transcript_client@example.com",
        "status": "completed",
        "created_at": datetime.now(timezone.utc)
    })

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            recap_payload = {
                "summary": "Discussed CRS score of 478. Recommended Alberta PNP stream to bridge 50-point gap.",
                "recording_url": "https://drive.google.com/file/d/test-recording-file/view",
                "transcripts": "[00:01] Consultant: Welcome! [00:05] Client: Hi, I wanted to discuss my Express Entry score.",
                "action_items": [
                    "Client to submit ECA reference number",
                    "Consultant to send Alberta PNP nomination checklist"
                ],
                "participants": ["Consultant Sarah", "Transcript Client"]
            }

            res = await ac.post(
                f"/api/crm/meetings/{meeting_id}/recap",
                json=recap_payload,
                headers=headers
            )
            assert res.status_code == 200, res.text
            saved_recap = res.json()["recap"]
            assert saved_recap["recording_url"] == recap_payload["recording_url"]
            assert saved_recap["summary"] == recap_payload["summary"]
            assert len(saved_recap["action_items"]) == 2

            # Verify in meetings list endpoint
            list_res = await ac.get(f"/api/crm/meetings?limit=10", headers=headers)
            assert list_res.status_code == 200
            m_list = list_res.json()
            target_m = next((m for m in m_list if m.get("id") == meeting_id), None)
            assert target_m is not None
            assert target_m.get("recap") is not None
            assert target_m["recap"]["recording_url"] == recap_payload["recording_url"]
            assert target_m["recap"]["summary"] == recap_payload["summary"]
    finally:
        await users_col.delete_one({"id": user_id})
        await crm_meetings_col.delete_one({"id": meeting_id})


@pytest.mark.asyncio
async def test_calendly_api_reschedule_sync(monkeypatch):
    """Verify that rescheduling a Calendly meeting syncs with Calendly API and updates IDs and Meet links."""
    user_id = str(uuid.uuid4())
    test_user = {
        "id": user_id,
        "email": f"partner_{uuid.uuid4().hex[:6]}@example.com",
        "name": "Partner Consultant",
        "role": "partner",
        "user_type": "internal_salesperson"
    }
    await users_col.insert_one(test_user)
    token = create_access_token({"sub": user_id, "role": "partner"})
    headers = {"Authorization": f"Bearer {token}"}

    meeting_id = str(uuid.uuid4())
    lead_id = str(uuid.uuid4())
    old_cal_event_id = "old-cal-event-uuid-111"

    await leads_col.insert_one({
        "id": lead_id,
        "name": "Calendly Sync Client",
        "email": "sync_client@example.com",
        "phone": "+919876543210",
        "source": "Calendly",
        "has_booking": True,
        "calendly_booking": {
            "event_name": "PR Assessment",
            "date": "2026-11-21",
            "time": "11:30",
            "meeting_link": f"https://calendly.com/events/{old_cal_event_id}/google_meet"
        }
    })

    await crm_meetings_col.insert_one({
        "id": meeting_id,
        "lead_id": lead_id,
        "calendly_event_id": old_cal_event_id,
        "calendly_invitee_id": "old-inv-uuid-111",
        "title": "Calendly: PR Assessment - Calendly Sync Client",
        "meeting_type": "Calendly",
        "meeting_date": "2026-11-21",
        "meeting_time": "11:30",
        "duration_minutes": 30,
        "meeting_link": f"https://calendly.com/events/{old_cal_event_id}/google_meet",
        "contact_name": "Calendly Sync Client",
        "contact_email": "sync_client@example.com",
        "sales_person_id": user_id,
        "sales_person_name": "Partner Consultant",
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc)
    })

    new_cal_event_id = "new-cal-event-uuid-222"
    new_meet_link = f"https://meet.google.com/new-meet-xyz"

    async def mock_reschedule_calendly_event_via_api(**kwargs):
        return {
            "success": True,
            "new_event_id": new_cal_event_id,
            "new_event_uri": f"https://api.calendly.com/scheduled_events/{new_cal_event_id}",
            "new_invitee_id": "new-inv-uuid-222",
            "new_invitee_uri": "https://api.calendly.com/scheduled_events/new-cal-event-uuid-222/invitees/new-inv-uuid-222",
            "meeting_link": new_meet_link,
            "cancel_url": "https://calendly.com/cancellations/new-uuid",
            "reschedule_url": "https://calendly.com/reschedulings/new-uuid"
        }

    from services.integrations import calendly_service
    monkeypatch.setattr(calendly_service, "reschedule_calendly_event_via_api", mock_reschedule_calendly_event_via_api)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(
                f"/api/crm/meetings/{meeting_id}/reschedule",
                json={
                    "meeting_date": "2026-11-23",
                    "meeting_time": "15:00",
                    "duration_minutes": 30,
                    "reason": "Client requested shifting consultation to Monday",
                    "notify_client": False
                },
                headers=headers
            )
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["success"] is True

            # Verify CRM meeting document has updated Calendly Event ID and new Meet link
            m_db = await crm_meetings_col.find_one({"id": meeting_id})
            assert m_db["calendly_event_id"] == new_cal_event_id
            assert m_db["meeting_link"] == new_meet_link
            assert m_db["status"] == "rescheduled"
            assert m_db["meeting_date"] == "2026-11-23"
            assert m_db["meeting_time"] == "15:00"
            assert len(m_db["reschedule_history"]) == 1
            assert m_db["reschedule_history"][0]["calendly_synced"] is True

            # Verify Lead record was synchronized with new date and new Meet link
            l_db = await leads_col.find_one({"id": lead_id})
            assert l_db["calendly_booking"]["date"] == "2026-11-23"
            assert l_db["calendly_booking"]["time"] == "15:00"
            assert l_db["calendly_booking"]["meeting_link"] == new_meet_link
    finally:
        await users_col.delete_one({"id": user_id})
        await crm_meetings_col.delete_one({"id": meeting_id})
        await leads_col.delete_one({"id": lead_id})


@pytest.mark.asyncio
async def test_calendly_to_crm_reschedule_deduplication():
    """Verify that when a rescheduled Calendly booking is received, it updates existing meeting without creating duplicates."""
    from services.integrations.calendly_service import record_calendly_booking

    lead_id = str(uuid.uuid4())
    meeting_id = str(uuid.uuid4())
    orig_event_id = f"ev_orig_{uuid.uuid4().hex[:6]}"
    resched_event_id = f"ev_resched_{uuid.uuid4().hex[:6]}"
    client_email = f"dedup_test_{uuid.uuid4().hex[:6]}@example.com"

    # Pre-existing lead
    await leads_col.insert_one({
        "id": lead_id,
        "name": "Dedup Client",
        "email": client_email,
        "phone": "+919988776655",
        "source": "Calendly",
        "has_booking": True
    })

    # Pre-existing meeting
    await crm_meetings_col.insert_one({
        "id": meeting_id,
        "lead_id": lead_id,
        "calendly_event_id": orig_event_id,
        "calendly_invitee_id": "inv_orig_123",
        "title": "Calendly: Permanent Residency Visa - Dedup Client",
        "meeting_type": "Calendly",
        "meeting_date": "2026-11-21",
        "meeting_time": "11:30",
        "duration_minutes": 30,
        "meeting_link": f"https://calendly.com/events/{orig_event_id}/google_meet",
        "contact_name": "Dedup Client",
        "contact_email": client_email,
        "status": "scheduled",
        "source": "calendly",
        "created_at": datetime.now(timezone.utc)
    })

    try:
        # Simulate incoming rescheduled event from Calendly
        booking_data = {
            "event_id": resched_event_id,
            "old_event_id": orig_event_id,
            "invitee_id": "inv_new_456",
            "event_name": "Permanent Residency Visa",
            "host_name": "Rohit Alluri",
            "client_name": "Dedup Client",
            "client_email": client_email,
            "client_phone": "+919988776655",
            "date": "2026-11-25",
            "time": "14:00",
            "duration_minutes": 30,
            "meeting_link": f"https://calendly.com/events/{resched_event_id}/google_meet",
            "status": "rescheduled",
            "reschedule_reason": "Rescheduled directly by invitee on Calendly",
            "notes": "Calendly Event: Permanent Residency Visa",
            "source": "calendly"
        }

        res = await record_calendly_booking(
            company_id="comp_leamss_primary",
            integration_id=None,
            booking=booking_data,
            trigger_email=False
        )

        assert res.get("status") in ["recorded", "success"] or res.get("meeting_id") is not None

        # Assert no duplicate meetings were created
        total_meetings = await crm_meetings_col.count_documents({"contact_email": client_email})
        assert total_meetings == 1, f"Expected exactly 1 meeting, found {total_meetings}"

        # Assert meeting was updated in-place with new date, time, and new event ID
        m = await crm_meetings_col.find_one({"id": meeting_id})
        assert m is not None
        assert m["meeting_date"] == "2026-11-25"
        assert m["meeting_time"] == "14:00"
        assert m["calendly_event_id"] == resched_event_id
        assert m["status"] == "rescheduled"
        assert len(m.get("reschedule_history", [])) == 1
    finally:
        await leads_col.delete_one({"id": lead_id})
        await crm_meetings_col.delete_one({"id": meeting_id})
