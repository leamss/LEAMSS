import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from core.database import db
from core.auth import get_current_user


@pytest.mark.asyncio
async def test_sample_cases_and_similar_unified():
    """Verify that Sample Cases and Similar Occupations are fully editable and sync cleanly."""
    app.dependency_overrides[get_current_user] = lambda: {
        "email": "admin@leamss.com",
        "role": "admin",
        "permissions": ["*"],
    }
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch current AU-224111 doc
        doc = await db["occupation_master"].find_one({"country_code": "AU", "code": "224111"})
        assert doc is not None, "AU-224111 must exist in database"
        occ_id = str(doc.get("occupation_id") or doc.get("_id"))

        # 2. Define custom sample cases and similar codes override
        custom_sample_cases = [
            {
                "id": "case_test_224111_1",
                "client_age": 31,
                "visa_subclass": "190",
                "outcome": "Subclass 190 PR Granted in 4 Months",
                "timeline_months": 4,
                "profile_summary": "Actuarial Science graduate with 5 years experience. Positive VETASSESS assessment achieved on fast-track.",
                "notes": "Direct alignment to ANZSCO 224111 task statement; state nomination received within 45 days.",
            },
            {
                "id": "case_test_224111_2",
                "client_age": 28,
                "visa_subclass": "491",
                "outcome": "Regional Provisional Visa Approved",
                "timeline_months": 5,
                "profile_summary": "Master of Statistics holder with 3 years tenure as junior actuary.",
                "notes": "15 regional points secured; positive skills assessment granted without RFI.",
            },
            {
                "id": "case_test_224111_3",
                "client_age": 35,
                "visa_subclass": "186",
                "outcome": "Direct Entry Permanent Residency Approved",
                "timeline_months": 6,
                "profile_summary": "Lead Actuary with 8 years of corporate experience. Employer sponsored nomination.",
                "notes": "Direct entry PR navigated under ANZSCO 224111 with corporate sponsor.",
            },
        ]

        # Mixed format: plain 6-digit code and country-prefixed slug
        custom_similar_overrides = ["224112", "AU-224113", "224114"]

        # 3. Update occupation master via admin PUT endpoint
        update_payload = {
            "title": doc.get("title") or "Actuary",
            "country_code": "AU",
            "code": "224111",
            "status": "verified",
            "sample_cases": custom_sample_cases,
            "similar_codes_override": custom_similar_overrides,
        }

        put_res = await client.put(f"/api/occupation-master/{occ_id}", json=update_payload)
        assert put_res.status_code == 200, f"PUT failed: {put_res.text}"

        # 4. Verify in Sales Occupation Detail endpoint: /api/sales/occupations/AU/224111
        sales_res = await client.get("/api/sales/occupations/AU/224111")
        assert sales_res.status_code == 200, f"Sales detail failed: {sales_res.text}"
        sales_data = sales_res.json()

        # Check sample cases
        returned_cases = sales_data.get("sample_cases") or []
        assert len(returned_cases) == 3, f"Expected 3 custom sample cases, got {len(returned_cases)}"
        assert returned_cases[0]["client_age"] == 31
        assert returned_cases[0]["visa_subclass"] == "190"
        assert "190" in returned_cases[0]["visa_name"]
        assert returned_cases[0]["timeline_months"] == 4
        assert "Actuarial Science" in returned_cases[0]["profile_summary"]

        assert returned_cases[1]["client_age"] == 28
        assert returned_cases[1]["visa_subclass"] == "491"
        assert "491" in returned_cases[1]["visa_name"]
        assert returned_cases[1]["timeline_months"] == 5

        # Check similar occupations
        returned_similar = sales_data.get("similar_codes") or []
        assert len(returned_similar) >= 3, f"Expected at least 3 similar occupations, got {len(returned_similar)}"

        # Pinned overrides must appear at the top with is_override=True and score=100
        first_3_codes = [s["code"] for s in returned_similar[:3]]
        assert "224112" in first_3_codes, f"224112 should be pinned, got {first_3_codes}"
        assert "224113" in first_3_codes, f"224113 should be pinned, got {first_3_codes}"
        assert "224114" in first_3_codes, f"224114 should be pinned, got {first_3_codes}"

        for s in returned_similar[:3]:
            assert s.get("is_override") is True, f"Pinned code {s['code']} must have is_override=True"
            assert s.get("similarity_score") == 100, f"Pinned code {s['code']} must have similarity_score=100"

        # Check that auto-filled peer (e.g. 4th item) is relevant (starts with 2241 or 224)
        if len(returned_similar) > 3:
            fourth = returned_similar[3]
            assert fourth["code"].startswith("224"), f"Auto-matched peer {fourth['code']} should be in same ANZSCO minor group (224)"

        # 5. Verify in Public Atlas endpoint: /api/public-atlas/AU/224111
        atlas_res = await client.get("/api/public-atlas/AU/224111")
        assert atlas_res.status_code == 200, f"Atlas detail failed: {atlas_res.text}"
        atlas_data = atlas_res.json()

        atlas_similar = atlas_data.get("similar") or []
        atlas_similar_codes = [s.get("code") for s in atlas_similar]
        assert "224112" in atlas_similar_codes, f"Public atlas similar should contain 224112, got {atlas_similar_codes}"
        assert "224113" in atlas_similar_codes, f"Public atlas similar should contain 224113, got {atlas_similar_codes}"

        atlas_cases = (atlas_data.get("occupation") or {}).get("sample_cases") or []
        assert len(atlas_cases) == 3, f"Expected 3 sample cases in atlas occupation doc, got {len(atlas_cases)}"
