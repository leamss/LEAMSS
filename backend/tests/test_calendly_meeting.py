import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from server import app
from core.meeting_service import save_meeting_config, get_meeting_config, generate_meeting_link
from core.auth import create_access_token
from core.database import db

crm_meetings_col = db["crm_meetings"]
leads_col = db["leads"]
users_col = db["users"]


@pytest.mark.asyncio
async def test_calendly_config_and_link_generation():
    # 1. Test saving Calendly link to meeting config
    test_link = "https://calendly.com/partner-consultant/30min"
    res = await save_meeting_config({"default_calendly_link": test_link})
    assert res["message"] == "Meeting configuration updated successfully"

    # 2. Test get_meeting_config returns default_calendly_link
    cfg = await get_meeting_config()
    assert cfg.get("default_calendly_link") == test_link

    # 3. Test generate_meeting_link for Calendly returns configured link
    gen = await generate_meeting_link(platform="Calendly", topic="Express Entry Consultation")
    assert gen["platform"] == "Calendly"
    assert gen["meeting_link"] == test_link
    assert gen["is_default"] is True

    # 4. Test generate_meeting_link for Zoom and Google Meet still works properly
    meet_gen = await generate_meeting_link(platform="Google Meet", topic="Canada Study Visa")
    assert meet_gen["platform"] == "Google Meet"
    assert meet_gen["meeting_type"] == "google_meet"

    zoom_gen = await generate_meeting_link(platform="Zoom", topic="Work Permit Consultation")
    assert zoom_gen["platform"] == "Zoom"
    assert zoom_gen["meeting_type"] == "zoom"


@pytest.mark.asyncio
async def test_calendly_meeting_scheduling_and_timeline():
    # Create test user and token
    user_id = str(uuid.uuid4())
    test_user = {
        "id": user_id,
        "email": "consultant@example.com",
        "name": "Consultant Jane",
        "role": "sales_person",
        "user_type": "internal_salesperson"
    }
    await users_col.insert_one(test_user)
    token = create_access_token({"sub": user_id, "role": "sales_person"})
    headers = {"Authorization": f"Bearer {token}"}

    lead_id = str(uuid.uuid4())
    await leads_col.insert_one({
        "id": lead_id,
        "name": "Calendly Test Client",
        "email": "calendly_test@example.com",
        "phone": "+919876543210",
        "whatsapp_number": "+919876543210"
    })

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            cal_link = "https://calendly.com/leamss-team/pr-assessment"
            payload = {
                "lead_id": lead_id,
                "contact_name": "Calendly Test Client",
                "contact_phone": "+919876543210",
                "contact_email": "calendly_test@example.com",
                "title": "PR Assessment via Calendly",
                "meeting_type": "Calendly",
                "meeting_date": "2026-10-30",
                "meeting_time": "14:30",
                "duration_minutes": 30,
                "meeting_link": cal_link,
                "notes": "Discuss points breakdown and ITA timeline"
            }

            resp = await ac.post("/api/crm/meetings", json=payload, headers=headers)
            assert resp.status_code == 200, resp.text
            meeting_data = resp.json()
            assert meeting_data["meeting_link"] == cal_link
            meeting_id = meeting_data["id"]

            # Verify in meetings list
            list_resp = await ac.get("/api/crm/meetings", headers=headers)
            assert list_resp.status_code == 200
            meetings = list_resp.json()
            scheduled = [m for m in meetings if m.get("id") == meeting_id]
            assert len(scheduled) == 1
            assert scheduled[0]["meeting_type"] == "Calendly"
            assert scheduled[0]["meeting_link"] == cal_link

            # Verify timeline returns Calendly platform_label
            timeline_resp = await ac.get(f"/api/crm/timeline/lead/{lead_id}", headers=headers)
            assert timeline_resp.status_code == 200
            timeline_events = timeline_resp.json()
            m_events = [e for e in timeline_events if e.get("type") == "meeting"]
            assert len(m_events) >= 1
            assert "Calendly" in m_events[0]["title"]
            assert m_events[0]["extra"]["meeting_type"] == "Calendly"

    finally:
        await users_col.delete_one({"id": user_id})
        await leads_col.delete_one({"id": lead_id})
        await crm_meetings_col.delete_many({"lead_id": lead_id})
