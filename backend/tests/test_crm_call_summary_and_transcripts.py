"""
Automated Integration Tests for Complete Call Summary & Transcript Tracking System
in LEAMSS CRM.

Validates:
1. Call creation with/without transcript and automatic Call Intelligence Processing.
2. Verified genuine transcription status (completed when conversation captured, unavailable with reason when missing).
3. Structured AI Summary generation (Main Discussion, Client Requirements, Concerns, Next Steps, Sentiment).
4. Permanent saving and retrieval of Call Transcripts and AI Summaries on client profile.
5. On-demand AI Summary re-generation and manual transcript updates.
6. Role-Based Access Control (RBAC):
   - Admin can view all salespersons' call summaries and transcripts.
   - Salesperson can only view calls related to their assigned clients or own logged calls.
7. Search across client name, notes, transcripts, and AI summaries.
8. Date range filtering.
"""
import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import app
from core.auth import create_access_token
from core.database import db
from core.call_intelligence_service import (
    resolve_transcription_status,
    _heuristic_summary_extraction,
    generate_call_ai_summary,
    process_call_intelligence
)


@pytest.mark.asyncio
async def test_call_intelligence_service_logic():
    """Unit test for heuristic extraction and transcription status resolution."""
    # 1. No transcript -> unavailable
    res1 = resolve_transcription_status({"transcript": "", "recording_url": ""})
    assert res1["transcription_status"] == "unavailable"
    assert "No audio or speech" in res1["transcription_status_reason"]

    # 2. Transcript present -> completed
    res2 = resolve_transcription_status({"transcript": "Agent: Hello\nClient: Hi, I need Canada Express Entry"})
    assert res2["transcription_status"] == "completed"
    assert "recorded" in res2["transcription_status_reason"]

    # 3. Heuristic extraction
    extracted = _heuristic_summary_extraction({
        "notes": "Client asked about Canada PR Express Entry. Budget is an issue and client worried about ECA processing times. Need to send evaluation checklist tomorrow.",
        "transcript": "",
        "outcome": "interested"
    })
    assert extracted["main_discussion"]
    assert any("ECA" in c or "budget" in c.lower() or "worried" in c.lower() for c in extracted["concerns_objections"])
    assert len(extracted["next_steps"]) > 0


@pytest.mark.asyncio
async def test_create_call_with_transcript_and_get_ai_summary():
    """Test creating a call with a full transcript and verifying permanent AI summary extraction."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sales_id = f"sales_{uuid.uuid4().hex[:6]}"
        sales_email = f"sales_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": sales_id},
            {"$set": {
                "id": sales_id,
                "email": sales_email,
                "name": "Sarah Sales",
                "role": "sales_executive",
                "rbac_role": "sales_executive"
            }},
            upsert=True
        )
        token = create_access_token({
            "sub": sales_id,
            "id": sales_id,
            "email": sales_email,
            "role": "sales_executive",
            "name": "Sarah Sales",
            "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        lead_id = f"lead_{uuid.uuid4().hex[:6]}"
        await db["leads"].update_one(
            {"id": lead_id},
            {"$set": {
                "id": lead_id,
                "name": "Rohan Sharma",
                "phone": "+91 98111 22334",
                "assigned_to": sales_id,
                "assigned_to_name": "Sarah Sales"
            }},
            upsert=True
        )

        transcript_text = (
            "Advisor: Good afternoon Rohan, thank you for reaching out to LEAMSS Immigration.\n"
            "Client: Hi Sarah. I want to check my eligibility for Canada Express Entry PR. I have 6 years experience in Java.\n"
            "Advisor: Fantastic, your IT background is high demand under STEM Category-Based Express Entry draws.\n"
            "Client: My only concern is that my IELTS score is currently 6.5 and I am worried it might lower my CRS points.\n"
            "Advisor: Understood. We will calculate your exact CRS and explore Ontario OINP Tech Draw. I will send you the document checklist by 5 PM."
        )

        # 1. Post call with transcript
        call_payload = {
            "lead_id": lead_id,
            "direction": "outgoing",
            "duration_seconds": 310,
            "status": "connected",
            "outcome": "interested",
            "notes": "Discussed STEM draws and IELTS concern",
            "lead_phone": "+91 98111 22334",
            "lead_name": "Rohan Sharma",
            "transcript": transcript_text
        }
        res = await client.post("/api/crm/calls", json=call_payload, headers=headers)
        assert res.status_code == 200
        call_id = res.json()["call_id"]
        assert call_id

        # 2. Fetch call details
        get_res = await client.get(f"/api/crm/calls/{call_id}", headers=headers)
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["transcription_status"] == "completed"
        assert data["transcript"] == transcript_text
        assert data["ai_summary"]
        assert data["ai_summary_structured"] is not None
        assert "main_discussion" in data["ai_summary_structured"]
        assert "client_requirements" in data["ai_summary_structured"]
        assert "concerns" in data["ai_summary_structured"]
        assert "next_steps" in data["ai_summary_structured"]


@pytest.mark.asyncio
async def test_update_transcript_and_regenerate_ai_summary():
    """Test updating transcript on an existing call and verifying AI summary regeneration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_id = f"admin_{uuid.uuid4().hex[:6]}"
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": admin_id},
            {"$set": {
                "id": admin_id,
                "email": admin_email,
                "name": "Super Admin",
                "role": "admin",
                "rbac_role": "admin"
            }},
            upsert=True
        )
        token = create_access_token({
            "sub": admin_id,
            "id": admin_id,
            "email": admin_email,
            "role": "admin",
            "name": "Super Admin",
            "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create call without transcript first
        call_payload = {
            "direction": "incoming",
            "duration_seconds": 180,
            "status": "connected",
            "outcome": "interested",
            "notes": "Initial consultation call",
            "lead_phone": "+91 99887 76655",
            "lead_name": "Aman Verma"
        }
        res = await client.post("/api/crm/calls", json=call_payload, headers=headers)
        assert res.status_code == 200
        call_id = res.json()["call_id"]

        # Check that transcription_status is initially unavailable
        call_get = await client.get(f"/api/crm/calls/{call_id}", headers=headers)
        assert call_get.json()["transcription_status"] == "unavailable"

        # 2. Add transcript via POST /crm/calls/{call_id}/transcript
        new_transcript = (
            "Consultant: Welcome to LEAMSS. Are you looking for Australia PR or Canada PR?\n"
            "Client: Australia Subclass 189 Skilled Independent visa. My occupation is Civil Engineer.\n"
            "Consultant: Great! Engineers Australia CDR assessment is needed. I'll email the requirements."
        )
        up_res = await client.post(
            f"/api/crm/calls/{call_id}/transcript",
            json={"transcript": new_transcript},
            headers=headers
        )
        assert up_res.status_code == 200
        up_data = up_res.json()
        assert up_data["transcription_status"] == "completed"
        assert up_data["transcript"] == new_transcript
        assert up_data["ai_summary_structured"]["main_discussion"]

        # 3. Test on-demand regenerate AI summary
        regen_res = await client.post(
            f"/api/crm/calls/{call_id}/ai-summary",
            headers=headers
        )
        assert regen_res.status_code == 200
        assert regen_res.json()["ai_summary_structured"] is not None


@pytest.mark.asyncio
async def test_rbac_salesperson_isolation_and_admin_full_access():
    """Verify salespersons only see calls for their assigned clients while admin can view all."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Sales Rep 1
        rep1_id = f"rep1_{uuid.uuid4().hex[:6]}"
        await db["users"].update_one(
            {"id": rep1_id},
            {"$set": {
                "id": rep1_id,
                "email": f"{rep1_id}@leamss.com",
                "name": "Rep One",
                "role": "sales_executive",
                "rbac_role": "sales_executive"
            }},
            upsert=True
        )
        token1 = create_access_token({
            "sub": rep1_id,
            "id": rep1_id,
            "email": f"{rep1_id}@leamss.com",
            "role": "sales_executive",
            "name": "Rep One"
        })
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Sales Rep 2
        rep2_id = f"rep2_{uuid.uuid4().hex[:6]}"
        await db["users"].update_one(
            {"id": rep2_id},
            {"$set": {
                "id": rep2_id,
                "email": f"{rep2_id}@leamss.com",
                "name": "Rep Two",
                "role": "sales_executive",
                "rbac_role": "sales_executive"
            }},
            upsert=True
        )
        token2 = create_access_token({
            "sub": rep2_id,
            "id": rep2_id,
            "email": f"{rep2_id}@leamss.com",
            "role": "sales_executive",
            "name": "Rep Two"
        })
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Admin
        admin_id = f"admin_{uuid.uuid4().hex[:6]}"
        await db["users"].update_one(
            {"id": admin_id},
            {"$set": {
                "id": admin_id,
                "email": f"{admin_id}@leamss.com",
                "name": "Global Admin",
                "role": "admin",
                "rbac_role": "admin"
            }},
            upsert=True
        )
        token_admin = create_access_token({
            "sub": admin_id,
            "id": admin_id,
            "email": f"{admin_id}@leamss.com",
            "role": "admin",
            "name": "Global Admin"
        })
        headers_admin = {"Authorization": f"Bearer {token_admin}"}

        # Rep 1 logs a call
        res1 = await client.post("/api/crm/calls", json={
            "direction": "outgoing",
            "duration_seconds": 120,
            "status": "connected",
            "notes": "Confidential client call of Rep 1",
            "lead_name": "Private Client 1",
            "lead_phone": "+91 91111 22222",
            "transcript": "Rep1: Private negotiation notes..."
        }, headers=headers1)
        assert res1.status_code == 200
        call1_id = res1.json()["call_id"]

        # Rep 2 cannot access call1 directly
        res_forbidden = await client.get(f"/api/crm/calls/{call1_id}", headers=headers2)
        assert res_forbidden.status_code == 403

        # Admin can access call1 directly
        res_admin_access = await client.get(f"/api/crm/calls/{call1_id}", headers=headers_admin)
        assert res_admin_access.status_code == 200

        # Rep 2 calls list does not contain call1
        calls_rep2 = (await client.get("/api/crm/calls", headers=headers2)).json()
        assert not any(c.get("id") == call1_id for c in calls_rep2)

        # Admin calls list contains call1
        calls_admin = (await client.get("/api/crm/calls", headers=headers_admin)).json()
        assert any(c.get("id") == call1_id for c in calls_admin)


@pytest.mark.asyncio
async def test_search_and_date_filtering():
    """Verify searching across transcript, summary, client name, and date filtering."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_id = f"admin_{uuid.uuid4().hex[:6]}"
        await db["users"].update_one(
            {"id": admin_id},
            {"$set": {
                "id": admin_id,
                "email": f"{admin_id}@leamss.com",
                "name": "Admin Tester",
                "role": "admin",
                "rbac_role": "admin"
            }},
            upsert=True
        )
        token = create_access_token({
            "sub": admin_id,
            "id": admin_id,
            "email": f"{admin_id}@leamss.com",
            "role": "admin",
            "name": "Admin Tester"
        })
        headers = {"Authorization": f"Bearer {token}"}

        unique_keyword = f"ZetaTech_{uuid.uuid4().hex[:6]}"
        call_payload = {
            "direction": "incoming",
            "duration_seconds": 250,
            "status": "connected",
            "notes": f"Client from {unique_keyword} requested Express Entry",
            "lead_name": "Special Applicant",
            "lead_phone": "+91 97777 88888",
            "transcript": f"Advisor: Hello, are you working at {unique_keyword}? Client: Yes I am."
        }
        res = await client.post("/api/crm/calls", json=call_payload, headers=headers)
        assert res.status_code == 200
        call_id = res.json()["call_id"]

        # Search by unique keyword
        search_res = await client.get(f"/api/crm/calls?search={unique_keyword}", headers=headers)
        assert search_res.status_code == 200
        calls = search_res.json()
        assert any(c["id"] == call_id for c in calls)

        # Search by non-existent keyword
        no_res = await client.get("/api/crm/calls?search=NonExistentKeywordXYZ999", headers=headers)
        assert no_res.status_code == 200
        calls_empty = no_res.json()
        assert len(calls_empty) == 0

        # Date range filtering (today)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        date_res = await client.get(f"/api/crm/calls?from_date={today_str}&to_date={today_str}", headers=headers)
        assert date_res.status_code == 200
        assert any(c["id"] == call_id for c in date_res.json())

        # Date range in past year (should not include this call)
        past_res = await client.get("/api/crm/calls?from_date=2020-01-01&to_date=2020-01-02", headers=headers)
        assert past_res.status_code == 200
        assert not any(c["id"] == call_id for c in past_res.json())


@pytest.mark.asyncio
async def test_transcript_edge_cases_and_lead_upsert():
    """Verify that saving a transcript works for ObjectId lookups and creates a call record if given lead_id."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_id = f"admin_{uuid.uuid4().hex[:6]}"
        await db["users"].update_one(
            {"id": admin_id},
            {"$set": {
                "id": admin_id,
                "email": f"{admin_id}@leamss.com",
                "name": "Admin Tester",
                "role": "admin",
                "rbac_role": "admin"
            }},
            upsert=True
        )
        token = create_access_token({
            "sub": admin_id,
            "id": admin_id,
            "email": f"{admin_id}@leamss.com",
            "role": "admin",
            "name": "Admin Tester"
        })
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test lead upsert: attach transcript to a lead that doesn't have a call yet
        lead_id = f"lead_{uuid.uuid4().hex[:6]}"
        await db["leads"].update_one(
            {"id": lead_id},
            {"$set": {
                "id": lead_id,
                "name": "Manali Client",
                "phone": "+91 1234567890",
                "assigned_to": admin_id
            }},
            upsert=True
        )

        res = await client.post(
            f"/api/crm/calls/{lead_id}/transcript",
            json={
                "transcript": "Sales Rep: Hello Manali\nClient: Hi, I need immigration help with Canada PR.",
                "lead_id": lead_id
            },
            headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["transcription_status"] == "completed"
        assert data["ai_summary_structured"] is not None
        assert "main_discussion" in data["ai_summary_structured"]

        # 2. Test lookup by MongoDB ObjectId
        call_doc = await db["crm_calls"].find_one({"lead_id": lead_id})
        assert call_doc is not None
        oid_str = str(call_doc["_id"])

        res2 = await client.post(
            f"/api/crm/calls/{oid_str}/transcript",
            json={
                "transcript": "Sales Rep: Updating dialogue with Manali\nClient: Sure, thank you."
            },
            headers=headers
        )
        assert res2.status_code == 200
        assert res2.json()["transcription_status"] == "completed"
