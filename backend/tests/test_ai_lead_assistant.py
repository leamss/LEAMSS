"""Test Suite for LEAMSS AI Lead Assistant.

Verifies:
1. AI Configuration & Connection Testing (System Default & Custom AI Providers)
2. Intelligent Lead Qualification, Multi-Dimensional Scoring (0–100, HOT/WARM/COLD)
3. ANZSCO/NOC Occupation & Assessing Authority Matching
4. Instant Personalized Proposal Narrative Drafting
5. Real-Time CRM Lead Ingestion & Sample Lead Simulation
6. Batch Lead Evaluation on Refresh (Sync) & Stats Increment
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from server import app
from core.database import db, users_col, leads_col, integrations_col
from core.auth import create_access_token
from services.integrations.ai_assistant_service import (
    test_ai_assistant_connection as check_ai_connection,
    qualify_lead_with_ai,
    generate_instant_proposal,
    batch_evaluate_company_leads
)


@pytest_asyncio.fixture
async def auth_setup():
    test_user_id = "user_ai_admin_001"
    test_company_id = "comp_ai_test_company"

    await users_col.delete_many({"id": test_user_id})
    await users_col.insert_one({
        "id": test_user_id,
        "name": "AI Super Admin",
        "email": "aiadmin@leamsstest.com",
        "role": "admin",
        "status": "active",
        "company_id": test_company_id
    })

    token = create_access_token({"sub": test_user_id, "company_id": test_company_id, "role": "admin"})
    return {"headers": {"Authorization": f"Bearer {token}"}, "company_id": test_company_id}


@pytest.mark.asyncio
async def test_lead_ai_qualification_scoring_and_occupation():
    # 1. Hot Profile: Senior Software Developer for Australia PR
    lead_hot = {
        "name": "Karan Malhotra",
        "email": "karan.malhotra@techcorp.in",
        "phone": "+919811122334",
        "country_of_interest": "Australia",
        "service_interested": "Subclass 189 Skilled Independent",
        "latest_qualification": "Master of Computer Applications (MCA)",
        "experience_years": "6 Years Senior Java Fullstack",
        "occupation": "Software Engineer",
        "budget": "₹2,00,000",
        "source": "Website Form"
    }
    q_hot = qualify_lead_with_ai(lead_hot)
    assert q_hot["score"] >= 70
    assert q_hot["category"] == "HOT"
    assert "261313" in q_hot["code_identifier"]
    assert "ACS" in q_hot["assessing_authority"]
    assert "189" in q_hot["recommended_pathway"]

    # 2. Proposal generation
    proposal = generate_instant_proposal(lead_hot, q_hot)
    assert "Karan Malhotra" in proposal
    assert "ACS (Australian Computer Society)" in proposal
    assert "Subclass 189" in proposal or "Permanent Residency" in proposal
    assert "Document Audit" in proposal

    # 3. Warm Profile: Junior Accountant for Canada
    lead_warm = {
        "name": "Simran Kaur",
        "email": "simran.k@example.com",
        "phone": "+919700011223",
        "country_of_interest": "Canada",
        "service_interested": "Express Entry",
        "latest_qualification": "Bachelor of Commerce",
        "experience_years": "2 Years",
        "occupation": "Junior Accountant",
        "budget": "₹50,000",
        "source": "Instagram Ads"
    }
    q_warm = qualify_lead_with_ai(lead_warm)
    assert 40 <= q_warm["score"] < 70
    assert q_warm["category"] == "WARM"
    assert "Accountant" in q_warm["matched_occupation"]


@pytest.mark.asyncio
async def test_ai_connection_verification_endpoint(auth_setup):
    headers = auth_setup["headers"]
    company_id = auth_setup["company_id"]
    integration_id = "integ_ai_tools_test_01"

    await integrations_col.delete_many({"id": integration_id})
    await integrations_col.insert_one({
        "id": integration_id,
        "company_id": company_id,
        "provider": "ai_tools",
        "name": "LEAMSS AI Lead Assistant",
        "status": "connected",
        "credentials": {
            "provider": "system_default",
            "model": "sonar",
            "temperature": 0.5
        },
        "total_leads_synced": 0
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(f"/api/integrations/{integration_id}/test", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data.get("success") is True, f"Connection test failed: {data}"
        assert "verified" in data["message"].lower() or "active" in data["message"].lower()


@pytest.mark.asyncio
async def test_ai_sample_lead_simulation_workflow(auth_setup):
    headers = auth_setup["headers"]
    company_id = auth_setup["company_id"]
    integration_id = "integ_ai_tools_test_02"

    await integrations_col.delete_many({"id": integration_id})
    await integrations_col.insert_one({
        "id": integration_id,
        "company_id": company_id,
        "provider": "ai_tools",
        "name": "LEAMSS AI Lead Assistant",
        "status": "connected",
        "credentials": {
            "provider": "system_default",
            "model": "sonar"
        },
        "lead_assignment_rules": {
            "mode": "round_robin",
            "rep_ids": ["rep_test_rep_1"],
            "default_service": "Skilled Migration PR"
        },
        "duplicate_prevention": {
            "strategy": "skip",
            "match_fields": ["phone", "email"]
        },
        "total_leads_synced": 0
    })

    sample_lead = {
        "name": "Rohit Verma",
        "email": f"rohit_{datetime.now().timestamp()}@leamsstest.com",
        "phone": "+919876599881",
        "country_of_interest": "Australia",
        "service_interested": "Subclass 190 State Nominated",
        "latest_qualification": "B.Tech Mechanical Engineering",
        "experience_years": "5 Years Automotive CAD",
        "occupation": "Mechanical Engineer",
        "budget": "₹1,50,000",
        "source": "Website Direct Form"
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(f"/api/integrations/{integration_id}/sample-lead", json=sample_lead, headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "created"
        assert "ai_qualification" in data
        assert data["ai_qualification"]["score"] >= 70
        assert data["ai_qualification"]["category"] == "HOT"
        assert "Engineers Australia" in data["ai_qualification"]["assessing_authority"]
        assert len(data["ai_proposal_draft"]) > 100

        # Check total_leads_synced incremented
        integ = await integrations_col.find_one({"id": integration_id})
        assert integ["total_leads_synced"] >= 1


@pytest.mark.asyncio
async def test_batch_lead_evaluation_on_sync(auth_setup):
    headers = auth_setup["headers"]
    company_id = auth_setup["company_id"]
    integration_id = "integ_ai_tools_test_03"

    # Seed 3 company leads in database
    await leads_col.delete_many({"company_id": company_id})
    lead_docs = [
        {
            "id": f"LD_TEST_{i}",
            "company_id": company_id,
            "name": f"Applicant {i}",
            "email": f"applicant_{i}@test.com",
            "phone": f"+91980000000{i}",
            "country_of_interest": "Canada",
            "service_interested": "Express Entry",
            "latest_qualification": "Master of Science",
            "experience_years": "4 Years",
            "budget": "₹1,00,000",
            "created_at": datetime.now(timezone.utc)
        }
        for i in range(1, 4)
    ]
    await leads_col.insert_many(lead_docs)

    await integrations_col.delete_many({"id": integration_id})
    await integrations_col.insert_one({
        "id": integration_id,
        "company_id": company_id,
        "provider": "ai_tools",
        "name": "LEAMSS AI Lead Assistant",
        "status": "connected",
        "credentials": {
            "provider": "system_default",
            "model": "sonar"
        },
        "total_leads_synced": 0
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger manual sync (Refresh)
        sync_res = await client.post(f"/api/integrations/{integration_id}/sync", headers=headers)
        assert sync_res.status_code == 200, sync_res.text
        sync_data = sync_res.json()
        assert sync_data["success"] is True
        assert sync_data["leads_imported"] == 3

        # Check leads were updated with ai_qualification
        updated_lead = await leads_col.find_one({"id": "LD_TEST_1"})
        assert "ai_qualification" in updated_lead
        assert updated_lead["lead_score"] > 0
        assert updated_lead["score_category"] in ["HOT", "WARM", "COLD"]
        assert len(updated_lead["ai_proposal_draft"]) > 50

        # Check logs endpoint
        logs_res = await client.get(f"/api/integrations/{integration_id}/logs", headers=headers)
        assert logs_res.status_code == 200
        logs = logs_res.json()
        assert len(logs) >= 1
        assert logs[0]["provider"] == "ai_tools"
        assert logs[0]["status"] == "success"
