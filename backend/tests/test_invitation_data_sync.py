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
            {"date": "2026-10-18", "subclass": "189", "score": 85, "invitations": 150},
            {"date": "2026-08-22", "subclass": "190", "score": 75, "invitations": 110},
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
                    "as_of_program_year": "2026-27",
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


@pytest.mark.asyncio
async def test_codewise_differentiation_and_oct_2026_rounds():
    """Verify that different ANZSCO codes return differentiated cutoff scores,
    proper 189/190/491 allocations, and recent invitation rounds up to October 2026."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Software Engineer (261313) - Tier 2 Core Skills
        dev_res = await client.get("/api/public-atlas/AU/261313")
        assert dev_res.status_code == 200
        dev_occ = dev_res.json().get("occupation", {})
        dev_pts = dev_occ.get("min_invitation_points", {})
        dev_rounds = dev_res.json().get("migroto_live", {}).get("invitations", {}).get("data", [])

        # Registered Nurse (254411) - Tier 1 Healthcare
        nurse_res = await client.get("/api/public-atlas/AU/254411")
        assert nurse_res.status_code == 200
        nurse_occ = nurse_res.json().get("occupation", {})
        nurse_pts = nurse_occ.get("min_invitation_points", {})
        nurse_rounds = nurse_res.json().get("migroto_live", {}).get("invitations", {}).get("data", [])

        # Accountant (221111) - Tier 2 High Competition
        acc_res = await client.get("/api/public-atlas/AU/221111")
        assert acc_res.status_code == 200
        acc_occ = acc_res.json().get("occupation", {})
        acc_pts = acc_occ.get("min_invitation_points", {})

        # Marketing Specialist (225113) - Tier 4 STSOL
        mkt_res = await client.get("/api/public-atlas/AU/225113")
        assert mkt_res.status_code == 200
        mkt_occ = mkt_res.json().get("occupation", {})
        mkt_pts = mkt_occ.get("min_invitation_points", {})
        mkt_rounds = mkt_res.json().get("migroto_live", {}).get("invitations", {}).get("data", [])

        # 1. Verify cutoffs are strictly differentiated between codes
        assert dev_pts.get("subclass_189") == 85, f"Expected 85 for 261313, got {dev_pts.get('subclass_189')}"
        assert nurse_pts.get("subclass_189") == 65, f"Expected 65 for 254411, got {nurse_pts.get('subclass_189')}"
        assert acc_pts.get("subclass_189") == 90, f"Expected 90 for 221111, got {acc_pts.get('subclass_189')}"
        # Marketing (STSOL) must NOT have 189 score
        assert mkt_pts.get("subclass_189") is None, f"STSOL 225113 must not have 189 score, got {mkt_pts.get('subclass_189')}"

        # 2. Verify recent rounds extend through October 2026
        assert len(dev_rounds) >= 6
        assert any("2026-10" in r.get("date", "") for r in dev_rounds), "Expected October 2026 round for Software Engineer"
        assert any("2026-10" in r.get("date", "") for r in nurse_rounds), "Expected October 2026 round for Nurse"
        assert any("2026-10" in r.get("date", "") for r in mkt_rounds), "Expected October 2026 round for Marketing"

        # 3. Verify STSOL rounds only have 190 and 491 (no 189)
        assert all(str(r.get("subclass")) in ("190", "491") for r in mkt_rounds), "STSOL should only have 190/491 rounds"


@pytest.mark.asyncio
async def test_migroto_sync_updates_cutoffs_and_rounds_for_future_updates():
    """Verify that calling POST /api/migroto/sync/{code} updates occupation_master
    with the latest cutoff benchmarks and invitation rounds, and auto-regenerates the public page."""
    app.dependency_overrides[get_current_user] = lambda: {
        "email": "admin@leamss.com",
        "role": "admin",
        "permissions": ["*"],
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Sync Software Engineer (261313)
        res = await client.post("/api/migroto/sync/261313")
        assert res.status_code == 200, f"Sync failed: {res.text}"
        data = res.json()
        assert data.get("status") == "success"
        assert "min_invitation_points" in data.get("enriched_fields", [])
        assert "invitation_rounds" in data.get("enriched_fields", [])

        # Verify DB doc was updated
        doc = await db["occupation_master"].find_one({"country_code": "AU", "code": "261313"})
        assert doc is not None
        assert doc.get("migroto_synced") is True
        assert doc.get("min_invitation_points", {}).get("subclass_189") == 85
        assert len(doc.get("invitation_rounds", [])) >= 6
        assert any("2026-10" in r.get("date", "") for r in doc.get("invitation_rounds", []))
