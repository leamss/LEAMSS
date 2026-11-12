import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from core.auth import get_current_user

@pytest.mark.asyncio
async def test_sales_occupations_detail_unified():
    app.dependency_overrides[get_current_user] = lambda: {
        "email": "admin@leamss.com",
        "role": "admin",
        "permissions": ["*"],
    }
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sales/occupations/AU/224111")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Check overview and abs_data
        overview = data.get("overview") or {}
        assert overview.get("code") == "224111"
        abs_data = overview.get("abs_data") or {}
        assert abs_data.get("median_ft_weekly_earnings_aud") in [1820, 1850], f"Expected 1820/1850, got {abs_data.get('median_ft_weekly_earnings_aud')}"
        assert abs_data.get("median_ft_annual_aud") in [94640, 96200], f"Expected 94640/96200, got {abs_data.get('median_ft_annual_aud')}"

        # Check jsa_data
        jsa_data = overview.get("jsa_data") or {}
        assert jsa_data.get("growth_pct_2025_to_2035") == 27.5, f"Expected 27.5, got {jsa_data.get('growth_pct_2025_to_2035')}"
        assert jsa_data.get("future_growth") in ["Strong Growth", "Very Strong Growth"]

        # Check documents
        docs = data.get("documents") or {}
        assert docs.get("total") == 16, f"Expected 16 docs, got {docs.get('total')}"
        categories = docs.get("by_category") or {}
        assert "Employment" in categories
        assert "Education" in categories

        # Check sample cases
        sample_cases = data.get("sample_cases") or []
        assert len(sample_cases) >= 3, f"Expected at least 3 sample cases, got {len(sample_cases)}"
        assert sample_cases[0].get("outcome") is not None

        # Check similar
        similar = data.get("similar") or []
        assert len(similar) > 0, "Expected similar occupations"

        # Check phase 19.10 enrichment
        p19 = data.get("_phase_19_10") or {}
        assert (p19.get("salary") or {}).get("median_native") == 96200
        assert (p19.get("growth") or {}).get("label") in ["Strong Growth", "Very Strong Growth"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_edit_synchronizes_to_sales_detail():
    app.dependency_overrides[get_current_user] = lambda: {
        "email": "admin@leamss.com",
        "role": "admin",
        "permissions": ["*"],
    }
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. First fetch occupation_id from occupation-master
        res = await client.get("/api/occupation-master?country_code=AU&search=224111")
        assert res.status_code == 200
        items = res.json().get("items") or []
        assert len(items) > 0
        occ_id = items[0]["occupation_id"]

        # 2. Update via PUT (simulate admin saving changes)
        update_payload = {
            "demand_rationale": "Updated demand analysis from Admin testing.",
            "abs_data": {
                "median_ft_weekly_earnings_aud": 1950,
                "median_ft_annual_aud": 101400,
            },
            "sample_cases": [
                {
                    "client_age": 30,
                    "profile_summary": "Actuarial specialist with 5 years experience in Melbourne.",
                    "visa_subclass": "190",
                    "outcome": "State Nomination Approved",
                    "timeline_months": 3,
                    "notes": "Fast-tracked nomination.",
                }
            ],
        }
        put_res = await client.put(f"/api/occupation-master/{occ_id}", json=update_payload)
        assert put_res.status_code == 200, f"PUT failed: {put_res.text}"

        # 3. Call sales occupations detail endpoint
        detail_res = await client.get("/api/sales/occupations/AU/224111")
        assert detail_res.status_code == 200
        detail = detail_res.json()

        # Verify synchronized fields
        assert detail["overview"]["demand_rationale"] == "Updated demand analysis from Admin testing."
        assert detail["overview"]["abs_data"]["median_ft_weekly_earnings_aud"] == 1950
        assert detail["overview"]["abs_data"]["median_ft_annual_aud"] == 101400
        assert len(detail["sample_cases"]) == 1
        assert detail["sample_cases"][0]["profile_summary"] == "Actuarial specialist with 5 years experience in Melbourne."

        # 4. Cleanup: restore original values
        restore_payload = {
            "demand_rationale": items[0].get("demand_rationale") or "",
            "abs_data": {
                "median_ft_weekly_earnings_aud": 1850,
                "median_ft_annual_aud": 96200,
            },
            "sample_cases": items[0].get("sample_cases") or [],
        }
        await client.put(f"/api/occupation-master/{occ_id}", json=restore_payload)

    app.dependency_overrides.clear()
