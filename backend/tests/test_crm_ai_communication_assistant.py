"""Integration and Unit Tests for CRM AI Sales Communication Assistant.

Verifies:
  1. WhatsApp channel:
     - Analyzes client message, extracts client context & questions
     - Generates concise, professional, ready-to-send WhatsApp reply
     - Includes pricing / statutory fee breakdown if asked
     - Never guarantees visa / PR approval
  2. Email channel:
     - Formats complete, professional email with subject line, greeting,
       structured sections, document requests / fee slabs, and salesperson signoff
  3. Live Calls channel:
     - Produces direct verbal script ("Say this to client")
     - Provides key factual bullet points for instant phone reference
  4. Integration test on POST /api/crm/ai/suggest-reply.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from server import app
from services.crm_ai_communication_service import generate_communication_reply


async def override_sales_user():
    return {
        "id": "77389ca8-5879-4191-9358-cedacbd1f45c",
        "name": "Priya Sharma",
        "role": "sales_executive",
        "email": "priya.sales@leamss.com",
        "permissions": ["crm:read", "crm:write", "ai:access", "*"]
    }


@pytest.fixture(autouse=True)
def mock_crm_external_calls(monkeypatch):
    """Ensure CRM AI tests run lightning fast by simulating offline Perplexity and fast product lookup."""
    async def _mock_fail(*args, **kwargs):
        raise ConnectionError("Sandbox offline test mode")
    monkeypatch.setattr("core.perplexity_client.call_perplexity", _mock_fail)

    async def _mock_fetch_lead(lead_id):
        return {"id": lead_id, "name": "Rajesh Kumar", "country": "Canada"}
    monkeypatch.setattr("services.crm_ai_communication_service._fetch_lead_data", _mock_fetch_lead)

    async def _mock_find_product(country, service=None, subclass=None):
        return {
            "name": f"{country} Skilled Migration",
            "country": country,
            "visa_subclass": subclass or "FSW",
            "authority_name": f"{country} Immigration Department",
            "service_price": 125000,
        }
    monkeypatch.setattr("services.crm_ai_communication_service._find_product_master_doc", _mock_find_product)


@pytest.mark.asyncio
async def test_crm_ai_service_whatsapp_flow():
    """Verify WhatsApp suggestion generation with grounding."""
    res = await generate_communication_reply(
        channel="whatsapp",
        intent_type="reply_client",
        client_message="Hi Priya, what is the total cost for Canada Express Entry and how long will it take?",
        target_country="Canada",
        lead_context={
            "name": "Rajesh Kumar",
            "country": "Canada",
            "service": "Express Entry",
            "sales_rep_name": "Priya Sharma",
        }
    )

    assert res["channel"] == "whatsapp"
    assert res["status"] == "success"
    text = res["suggested_text"]
    assert "Rajesh" in text or "Hi" in text
    assert "Canada" in text or "Express Entry" in text or "CAD" in text or "INR" in text
    # Verify strict disclaimer compliance
    assert "guarantee" in text.lower() or "disclaimer" in text.lower() or "subject to" in text.lower()
    assert len(res["talking_points"]) > 0


@pytest.mark.asyncio
async def test_crm_ai_service_email_flow():
    """Verify Email suggestion generation with structured proposal & breakdown."""
    res = await generate_communication_reply(
        channel="email",
        intent_type="fees_proposal",
        client_message="Could you email me the formal fee proposal and process stages for Australian PR Subclass 189?",
        target_country="Australia",
        service_interested="Skilled Independent Subclass 189",
        lead_context={
            "name": "Amitabh Sen",
            "sales_rep_name": "Priya Sharma",
        }
    )

    assert res["channel"] == "email"
    assert res["status"] == "success"
    text = res["suggested_text"]
    assert "Subject:" in text or res.get("subject")
    assert "Australia" in text or "189" in text or "AUD" in text
    assert len(res["talking_points"]) >= 2


@pytest.mark.asyncio
async def test_crm_ai_service_live_call_copilot():
    """Verify Live Call copilot answers rapid client question with speaking script and factual bullet points."""
    res = await generate_communication_reply(
        channel="live_call",
        intent_type="live_qa",
        client_message="Can you guarantee my PR if I pay the full fee right now?",
        target_country="Canada",
        lead_context={
            "name": "Karan Malhotra",
            "sales_rep_name": "Priya Sharma",
        }
    )

    assert res["channel"] == "live_call"
    assert res["status"] == "success"
    speaking_script = res.get("speaking_script") or res["suggested_text"]
    # Must explicitly decline approval guarantee
    assert "guarantee" in speaking_script.lower()
    assert ("ircc" in speaking_script.lower() or "government" in speaking_script.lower() or "authority" in speaking_script.lower() or "sovereign" in speaking_script.lower() or "cannot" in speaking_script.lower() or "no consultant" in speaking_script.lower())
    assert len(res["talking_points"]) >= 2


@pytest.mark.asyncio
async def test_crm_ai_suggest_reply_endpoint():
    """Integration test against POST /api/crm/ai/suggest-reply endpoint."""
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. WhatsApp request
        resp_wa = await ac.post("/api/crm/ai/suggest-reply", json={
            "channel": "whatsapp",
            "intent_type": "reply_client",
            "client_message": "What documents do I need to begin my Germany Chancenkarte application?",
            "target_country": "Germany",
            "service_interested": "Opportunity Card (Chancenkarte)",
            "lead_context": {"name": "Siddharth Roy"}
        })
        assert resp_wa.status_code == 200
        wa_data = resp_wa.json()
        assert wa_data["channel"] == "whatsapp"
        assert len(wa_data["suggested_text"]) > 20
        assert "Germany" in wa_data["suggested_text"] or "Chancenkarte" in wa_data["suggested_text"] or "degree" in wa_data["suggested_text"].lower()

        # 2. Live call copilot request
        resp_call = await ac.post("/api/crm/ai/suggest-reply", json={
            "channel": "live_call",
            "intent_type": "objection_handling",
            "client_message": "Why is your consulting fee 1.25 Lakhs when others do it cheaper?",
            "target_country": "Canada",
            "lead_context": {"name": "Vikram Patel"}
        })
        assert resp_call.status_code == 200
        call_data = resp_call.json()
        assert call_data["channel"] == "live_call"
        assert "speaking_script" in call_data
        assert len(call_data["talking_points"]) > 0

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_crm_ai_family_inquiry_channels():
    """Verify family inquiries across WhatsApp, Email, and Live Call in CRM AI."""
    from services.crm_ai_communication_service import generate_communication_reply

    # 1. WhatsApp family inquiry
    wa_res = await generate_communication_reply(
        channel="whatsapp",
        client_message="Can I include my spouse and children in Australia Subclass 189?",
        target_country="Australia",
        service_interested="Skilled Independent Subclass 189",
        lead_context={"name": "Rohit Sharma"}
    )
    wa_text = wa_res["reply_text"].lower()
    assert "spouse" in wa_text or "family" in wa_text
    assert "only if" in wa_text
    assert "18" in wa_text
    assert "health" in wa_text and "character" in wa_text
    assert "4,770" not in wa_res["reply_text"]

    # 2. Live call family inquiry
    call_res = await generate_communication_reply(
        channel="live_call",
        client_message="Can I take my wife and kids on Australia 189 PR?",
        target_country="Australia",
        service_interested="Skilled Independent Subclass 189",
        lead_context={"name": "Rohit Sharma"}
    )
    call_script = (call_res.get("speaking_script") or call_res["suggested_text"]).lower()
    assert "spouse" in call_script or "dependent" in call_script or "children" in call_script
    assert "approved" in call_script
    assert "18" in call_script
    assert "4,770" not in call_res.get("speaking_script", "")
