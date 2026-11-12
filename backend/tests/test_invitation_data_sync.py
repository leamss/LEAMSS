import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from core.database import db
from core.auth import get_current_user


@pytest.mark.asyncio
async def test_invitation_data_sales_and_public_sync():
    """Verify that invitation rounds and cutoff points are returned by Public Atlas,
    returned by Sales occupations detail, and can be updated via Admin Master."""
    app.dependency_overrides[get_current_user] = lambda: {
        "email": "admin@leamss.com",
        "role": "admin",
        "permissions": ["*"],
    }
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Public Atlas endpoint for AU 224111
        pub_res = await client.get("/api/public-atlas/AU/224111")
        assert pub_res.status_code == 200, f"Public Atlas error: {pub_res.text}"
        pub_data = pub_res.json()
        assert pub_data.get("migroto_live") is not None
        assert "invitations" in pub_data["migroto_live"]
        assert len(pub_data["migroto_live"]["invitations"].get("data", [])) > 0
        assert pub_data.get("occupation", {}).get("min_invitation_points") is not None

        # 2. Test Sales detail endpoint for AU 224111
        sales_res = await client.get("/api/sales/occupations/AU/224111")
        assert sales_res.status_code == 200, f"Sales error: {sales_res.text}"
        sales_data = sales_res.json()
        assert sales_data.get("min_invitation_points") is not None
        assert sales_data["min_invitation_points"].get("subclass_189") is not None
        assert sales_data["min_invitation_points"].get("subclass_190") is not None
        assert sales_data["min_invitation_points"].get("subclass_491") is not None
        assert sales_data.get("invitation_rounds") is not None
        assert len(sales_data["invitation_rounds"]) >= 3

        # 3. Test Admin PUT updating invitation_rounds
        doc = await db["occupation_master"].find_one({"country_code": "AU", "code": "224111"})
        assert doc is not None
        occ_id = str(doc.get("occupation_id") or doc.get("_id"))

        custom_rounds = [
            {"date": "2026-07-01", "subclass": "189", "score": 85, "invitations": 150},
            {"date": "2026-06-15", "subclass": "190", "score": 75, "invitations": 110},
            {"date": "2026-05-20", "subclass": "491", "score": 65, "invitations": 80},
        ]

        put_res = await client.put(
            f"/api/occupation-master/{occ_id}",
            json={
                "title": doc.get("title"),
                "status": "verified",
                "invitation_rounds": custom_rounds,
                "min_invitation_points": {
                    "subclass_189": 85,
                    "subclass_190": 75,
                    "subclass_491": 65,
                    "as_of_program_year": "2025-26",
                },
            },
        )
        assert put_res.status_code == 200, f"Admin PUT failed: {put_res.text}"
        put_data = put_res.json()
        assert put_data.get("invitation_rounds") == custom_rounds

        # 4. Verify that Sales detail now reflects the updated invitation_rounds
        sales_res2 = await client.get("/api/sales/occupations/AU/224111")
        assert sales_res2.status_code == 200
        sales_data2 = sales_res2.json()
        assert sales_data2.get("invitation_rounds") == custom_rounds
        assert sales_data2["min_invitation_points"]["subclass_189"] == 85

        # 5. Verify that Public Atlas also reflects the updated rounds
        pub_res2 = await client.get("/api/public-atlas/AU/224111")
        assert pub_res2.status_code == 200
        pub_data2 = pub_res2.json()
        assert pub_data2["migroto_live"]["invitations"]["data"] == custom_rounds
