import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from core.database import db
from core.auth import create_access_token


@pytest.mark.asyncio
async def test_calendly_all_leads_visibility_and_filter():
    import uuid
    from datetime import datetime, timezone

    admin = await db["users"].find_one({"role": "admin"})
    token = create_access_token({"sub": admin["id"], "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    # Ensure test data exists with Calendly leads
    count_cal = await db["leads"].count_documents({"source": "Calendly"})
    if count_cal < 20:
        docs = []
        for i in range(25):
            docs.append({
                "id": str(uuid.uuid4()),
                "name": f"Calendly Test Lead {i}",
                "email": f"calendly_test_{i}@example.com",
                "phone": f"+9198765{i:05d}",
                "source": "Calendly",
                "has_booking": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
        await db["leads"].insert_many(docs)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Fetch leads sorted by created_at desc
        res = await ac.get("/api/leads/?limit=30", headers=headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) > 0

        # Verify newest Calendly leads stay in the recent list
        has_calendly = any(l.get("source") == "Calendly" for l in leads[:20])
        assert has_calendly is True

        # 2. Test dedicated source=Calendly filter
        c_res = await ac.get("/api/leads/?source=Calendly", headers=headers)
        assert c_res.status_code == 200
        c_leads = c_res.json()
        assert len(c_leads) >= 20

        # Verify all returned leads either have source=Calendly, has_booking=True, or are in crm_meetings
        for lead in c_leads[:10]:
            is_calendly = lead.get("source") == "Calendly" or lead.get("has_booking") is True or "calendly" in (lead.get("tags") or [])
            assert is_calendly is True
