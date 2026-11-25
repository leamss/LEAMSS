import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import app
from core.auth import create_access_token
from core.database import db

@pytest.mark.asyncio
async def test_lead_conversion_and_salesperson_visibility():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Seed Salesperson Pooja
        rep_id = f"test_sales_rep_{uuid.uuid4().hex[:6]}"
        rep_email = f"rep_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": rep_id},
            {"$set": {
                "id": rep_id,
                "email": rep_email,
                "name": "Pooja Ghatkar",
                "role": "sales_executive",
                "rbac_role": "sales_executive",
                "user_type": "internal",
                "department": "sales"
            }},
            upsert=True
        )

        rep_token = create_access_token({
            "sub": rep_id,
            "id": rep_id,
            "email": rep_email,
            "role": "sales_executive",
            "rbac_role": "sales_executive",
            "name": "Pooja Ghatkar",
            "permissions": ["pa.view.own", "pa.create.own", "lead_pool"]
        })
        rep_headers = {"Authorization": f"Bearer {rep_token}"}

        # 2. Seed Lead Manali assigned to Pooja
        lead_id = f"lead_{uuid.uuid4().hex[:6]}"
        client_email = f"manali_{uuid.uuid4().hex[:6]}@example.com"
        await db["leads"].update_one(
            {"id": lead_id},
            {"$set": {
                "id": lead_id,
                "name": "Manali Patkar",
                "email": client_email,
                "phone": "+91 99999 88888",
                "country_of_interest": "Canada",
                "service_interested": "PR Visa",
                "assigned_to": rep_id,
                "assigned_to_name": "Pooja Ghatkar",
                "stage": "connected",
                "source": "Website",
                "tags": []
            }},
            upsert=True
        )

        # 3. Salesperson updates lead stage to 'converted' via PUT /api/leads/{id}
        put_res = await client.put(
            f"/api/leads/{lead_id}",
            json={"stage": "converted"},
            headers=rep_headers
        )
        assert put_res.status_code == 200, f"Expected 200, got {put_res.status_code}: {put_res.text}"
        lead_in_db = await db["leads"].find_one({"id": lead_id})
        assert lead_in_db.get("stage") == "converted"
        assert lead_in_db.get("converted") is True

        # Verify client record was created/updated in users collection with correct assignment
        client_user = await db["users"].find_one({"email": client_email})
        assert client_user is not None, "Client user should be created in users collection"
        assert client_user.get("role") == "client"
        assert client_user.get("assigned_sales_person_id") == rep_id
        assert client_user.get("assigned_sales_person_name") == "Pooja Ghatkar"

        # 4. Check Salesperson can access their own drilldown detail
        detail_res = await client.get(
            f"/api/crm/sales-reps/{rep_id}/detail",
            headers=rep_headers
        )
        assert detail_res.status_code == 200, f"Expected 200, got {detail_res.status_code}: {detail_res.text}"
        detail_data = detail_res.json()
        clients = detail_data.get("clients", [])
        
        # Verify converted client appears in salesperson's clients list
        converted_client = next((c for c in clients if c.get("id") == lead_id or c.get("email") == client_email), None)
        assert converted_client is not None, f"Converted client {client_email} should appear in salesperson clients list"
        assert converted_client.get("stage") == "converted"
        assert converted_client.get("converted") is True

        # 5. Check Overview endpoint for the salesperson
        overview_res = await client.get(
            "/api/crm/sales-reps/overview",
            headers=rep_headers
        )
        assert overview_res.status_code == 200
        overview_data = overview_res.json()
        assert len(overview_data.get("sales_reps", [])) >= 1
        my_rep_summary = next((r for r in overview_data["sales_reps"] if r.get("id") == rep_id), None)
        assert my_rep_summary is not None
        assert my_rep_summary.get("converted_clients", 0) >= 1

        # 6. Verify existing Pre-Assessment flow remains fully functional
        pa_res = await client.post(
            f"/api/leads/{lead_id}/convert-to-pa",
            headers=rep_headers
        )
        assert pa_res.status_code == 200, f"Expected 200, got {pa_res.status_code}: {pa_res.text}"
        pa_data = pa_res.json()
        assert pa_data.get("status") == "success" or "pre_assessment_id" in pa_data or "id" in pa_data

        # 7. Also test convert-to-client endpoint for another lead
        lead_id2 = f"lead2_{uuid.uuid4().hex[:6]}"
        client_email2 = f"manali2_{uuid.uuid4().hex[:6]}@example.com"
        await db["leads"].update_one(
            {"id": lead_id2},
            {"$set": {
                "id": lead_id2,
                "name": "Manali Second Client",
                "email": client_email2,
                "phone": "+91 99999 77777",
                "assigned_to": rep_id,
                "assigned_to_name": "Pooja Ghatkar",
                "stage": "qualified",
                "source": "Website"
            }},
            upsert=True
        )
        conv_btn_res = await client.post(
            f"/api/leads/{lead_id2}/convert-to-client",
            headers=rep_headers
        )
        assert conv_btn_res.status_code == 200
        btn_data = conv_btn_res.json()
        assert btn_data.get("client_id") is not None
        assert btn_data.get("deal_id") is not None
        assert btn_data.get("message") == "Lead successfully converted to Client"
        
        # Verify users collection has client assigned to Pooja
        user2 = await db["users"].find_one({"email": client_email2})
        assert user2 is not None
        assert user2.get("assigned_sales_person_id") == rep_id
