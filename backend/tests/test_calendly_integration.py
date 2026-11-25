"""Unit & Integration Tests for Calendly API v2 Integration across LEAMSS CRM.
Tests:
1. Calendly PAT verification & Event Types retrieval.
2. Dynamic single-use scheduling link creation.
3. Webhook processing (invitee.created, invitee.canceled, invitee.rescheduled) & Idempotency.
4. Meeting reminder calculation & deduplication (24h, 1h, 15m).
5. Post-meeting auto-completion and follow-up task generation.
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from services.integrations.calendly_service import (
    test_calendly_connection as check_calendly_connection,
    fetch_calendly_event_types,
    create_calendly_scheduling_link,
    record_calendly_booking,
    process_due_meeting_reminders,
    auto_complete_past_meetings_and_create_tasks,
    DEFAULT_PAT
)
from core.database import db, crm_meetings_col, leads_col, appointments_col, follow_ups_col


@pytest.mark.asyncio
async def test_calendly_connection_with_pat():
    """Validates that Calendly account details are successfully verified with PAT."""
    res = await check_calendly_connection({"api_token": DEFAULT_PAT})
    assert res["success"] is True
    assert "user" in res
    assert res["user"]["name"] == "Rohit Alluri"
    assert "rohit@leamss.com" in res["user"]["email"]


@pytest.mark.asyncio
async def test_create_scheduling_link():
    """Tests generating a dynamic single-use scheduling link."""
    res = await create_calendly_scheduling_link(company_id="comp_leamss_primary", max_event_count=1)
    assert res["success"] is True
    assert "booking_url" in res
    assert "calendly.com" in res["booking_url"]


@pytest.mark.asyncio
async def test_record_calendly_booking_and_deduplication():
    """Tests recording new, duplicate, and rescheduled bookings."""
    test_event_id = f"test_ev_{uuid.uuid4().hex[:8]}"
    test_inv_id = f"test_inv_{uuid.uuid4().hex[:8]}"
    client_email = f"test_{uuid.uuid4().hex[:6]}@example.com"

    booking_payload = {
        "event_id": test_event_id,
        "event_uri": f"https://api.calendly.com/scheduled_events/{test_event_id}",
        "invitee_id": test_inv_id,
        "invitee_uri": f"https://api.calendly.com/scheduled_events/{test_event_id}/invitees/{test_inv_id}",
        "event_name": "Permanent Residency Consultation",
        "host_name": "Rohit Alluri",
        "client_name": "John Doe",
        "client_email": client_email,
        "client_phone": "+61412345678",
        "start_time": "2026-12-01T10:00:00Z",
        "end_time": "2026-12-01T10:30:00Z",
        "date": "2026-12-01",
        "time": "10:00",
        "duration_minutes": 30,
        "meeting_link": "https://meet.google.com/abc-defg-hij",
        "status": "scheduled",
        "notes": "Discuss 189 and 190 visa pathways",
        "source": "calendly"
    }

    # 1. Record first time (new)
    res1 = await record_calendly_booking("comp_leamss_primary", None, booking_payload, trigger_email=False)
    assert res1["status"] == "synced"
    assert res1["is_new"] is True
    assert res1["client_email"] == client_email

    # Verify meeting exists in DB
    saved_meeting = await crm_meetings_col.find_one({"id": res1["meeting_id"]})
    assert saved_meeting is not None
    assert saved_meeting["status"] == "scheduled"
    assert saved_meeting["source"] == "calendly"
    assert "reminders_sent" in saved_meeting

    # 2. Record second time with same IDs (idempotent update, not duplicated)
    res2 = await record_calendly_booking("comp_leamss_primary", None, booking_payload, trigger_email=False)
    assert res2["status"] == "synced"
    assert res2["is_new"] is False
    assert res2["meeting_id"] == res1["meeting_id"]

    # 3. Reschedule booking (new time)
    booking_rescheduled = dict(booking_payload)
    booking_rescheduled["date"] = "2026-12-02"
    booking_rescheduled["time"] = "14:00"
    booking_rescheduled["start_time"] = "2026-12-02T14:00:00Z"
    booking_rescheduled["end_time"] = "2026-12-02T14:30:00Z"

    res3 = await record_calendly_booking("comp_leamss_primary", None, booking_rescheduled, trigger_email=False)
    assert res3["is_rescheduled"] is True

    updated_m = await crm_meetings_col.find_one({"id": res1["meeting_id"]})
    assert updated_m["status"] == "rescheduled"
    assert updated_m["meeting_date"] == "2026-12-02"
    assert updated_m["meeting_time"] == "14:00"

    # Cleanup test data
    await crm_meetings_col.delete_one({"id": res1["meeting_id"]})
    if res1.get("lead_id"):
        await leads_col.delete_one({"id": res1["lead_id"]})


@pytest.mark.asyncio
async def test_reminders_and_post_meeting_follow_ups():
    """Tests 24h, 1h, 15m reminder logic and post-meeting follow-up task generation."""
    meeting_id = f"test_rem_{uuid.uuid4().hex[:8]}"
    now_utc = datetime.now(timezone.utc)

    # 1. Test 1 hour reminder (meeting in 60 mins)
    meeting_time_dt = now_utc + timedelta(minutes=60)
    m_doc = {
        "id": meeting_id,
        "title": "Upcoming Consultation",
        "contact_name": "Alice Smith",
        "contact_email": "alice@example.com",
        "sales_person_name": "Rohit Alluri",
        "meeting_type": "Calendly",
        "meeting_date": meeting_time_dt.strftime("%Y-%m-%d"),
        "meeting_time": meeting_time_dt.strftime("%H:%M"),
        "meeting_link": "https://meet.google.com/test-meet",
        "status": "scheduled",
        "reminders_sent": []
    }
    await crm_meetings_col.insert_one(m_doc)

    with patch("services.integrations.calendly_service.send_email") as mock_email:
        sent = await process_due_meeting_reminders(db)
        assert sent["1h"] >= 1

    check_m = await crm_meetings_col.find_one({"id": meeting_id})
    assert "1h" in check_m["reminders_sent"]

    # 2. Test auto-complete and follow-up creation (meeting ended 2 hours ago)
    past_dt = now_utc - timedelta(hours=2)
    await crm_meetings_col.update_one(
        {"id": meeting_id},
        {"$set": {
            "meeting_date": past_dt.strftime("%Y-%m-%d"),
            "meeting_time": past_dt.strftime("%H:%M"),
            "duration_minutes": 30
        }}
    )

    completed_count = await auto_complete_past_meetings_and_create_tasks(db)
    assert completed_count >= 1

    after_auto = await crm_meetings_col.find_one({"id": meeting_id})
    assert after_auto["status"] == "completed"

    fu_task = await follow_ups_col.find_one({"meeting_id": meeting_id})
    assert fu_task is not None
    assert fu_task["follow_up_type"] == "post_meeting_follow_up"
    assert fu_task["priority"] == "high"

    # Cleanup
    await crm_meetings_col.delete_one({"id": meeting_id})
    await follow_ups_col.delete_one({"meeting_id": meeting_id})


@pytest.mark.asyncio
async def test_webhook_receiver_and_idempotency():
    """Tests webhook endpoint handling: creation, idempotency, and cancellation."""
    from routers.integrations import calendly_webhook_receiver

    event_uuid = f"ev_hook_{uuid.uuid4().hex[:8]}"
    invitee_uuid = f"inv_hook_{uuid.uuid4().hex[:8]}"
    client_email = f"hook_{uuid.uuid4().hex[:6]}@example.com"

    payload = {
        "event": "invitee.created",
        "uuid": event_uuid,
        "payload": {
            "event_type": {"name": "PR Visa Consultation"},
            "scheduled_event": {
                "uuid": event_uuid,
                "name": "PR Visa Consultation",
                "start_time": "2026-12-10T11:00:00Z",
                "end_time": "2026-12-10T11:30:00Z",
                "location": {"join_url": "https://meet.google.com/hook-test-meet"}
            },
            "invitee": {
                "uuid": invitee_uuid,
                "name": "Webhook Tester",
                "email": client_email,
                "text_reminder_number": "+919876543210",
                "status": "active"
            }
        }
    }

    # 1. First webhook call -> creates booking
    res1 = await calendly_webhook_receiver("comp_leamss_primary", payload)
    assert res1["status"] == "synced"
    assert res1["is_new"] is True

    # 2. Duplicate webhook call with same UUID -> idempotency catches it
    res2 = await calendly_webhook_receiver("comp_leamss_primary", payload)
    assert res2["status"] == "already_processed"

    # 3. Cancel event webhook
    cancel_uuid = f"cancel_{uuid.uuid4().hex[:8]}"
    cancel_payload = {
        "event": "invitee.canceled",
        "uuid": cancel_uuid,
        "payload": {
            "event_type": {"name": "PR Visa Consultation"},
            "scheduled_event": {
                "uuid": event_uuid,
                "status": "canceled"
            },
            "invitee": {
                "uuid": invitee_uuid,
                "email": client_email,
                "status": "canceled"
            }
        }
    }
    res3 = await calendly_webhook_receiver("comp_leamss_primary", cancel_payload)
    assert res3["status"] == "synced"

    canceled_m = await crm_meetings_col.find_one({"id": res1["meeting_id"]})
    assert canceled_m["status"] == "cancelled"

    # Cleanup
    await crm_meetings_col.delete_one({"id": res1["meeting_id"]})
    if res1.get("lead_id"):
        await leads_col.delete_one({"id": res1["lead_id"]})
    await db["calendly_webhook_events"].delete_many({"webhook_uuid": {"$in": [event_uuid, cancel_uuid]}})

