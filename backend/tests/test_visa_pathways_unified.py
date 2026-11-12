import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from core.database import db
from core.auth import get_current_user


@pytest.mark.asyncio
async def test_visa_pathways_unified_edit_and_sync():
    """Verify that editing Visa Pathways in Admin updates both Sales and Public Atlas views."""
    app.dependency_overrides[get_current_user] = lambda: {
        "email": "admin@leamss.com",
        "role": "admin",
        "permissions": ["*"],
    }
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch current occupation doc for AU-224111
        doc = await db["occupation_master"].find_one({"country_code": "AU", "code": "224111"})
        assert doc is not None, "AU-224111 must exist in database"
        occ_id = str(doc.get("occupation_id") or doc.get("_id"))

        # 2. Prepare custom visa pathways data matching user specification
        custom_visa_eligibility = [
            {
                "visa_subclass": "189",
                "name": "Subclass 189",
                "stream": "Skilled Independent (PR)",
                "pathway_type": "Skilled Independent (PR)",
                "description": "Permanent residence for skilled workers not sponsored by employer/family/state.",
                "eligible": True,
                "age_limit": 44,
                "points_minimum": 65,
                "experience_required": "1+ yr",
                "processing_time_months": "3–6 mo",
                "fee_native": "AUD $4,770",
                "list": "MLTSSL",
            },
            {
                "visa_subclass": "186",
                "name": "Subclass 186",
                "stream": "Employer Nomination Scheme (PR)",
                "pathway_type": "Employer Nomination Scheme (PR)",
                "description": "Permanent residency via employer sponsorship.",
                "eligible": True,
                "age_limit": 44,
                "points_minimum": 0,
                "experience_required": "3 yrs",
                "processing_time_months": "3–6 mo",
                "fee_native": "AUD $4,770",
                "list": "MLTSSL",
            },
            {
                "visa_subclass": "190",
                "name": "Subclass 190",
                "stream": "Skilled Nominated (PR)",
                "pathway_type": "Skilled Nominated (PR)",
                "description": "Permanent visa requiring nomination from an Australian state/territory.",
                "eligible": True,
                "age_limit": 44,
                "points_minimum": 65,
                "experience_required": "1+ yr",
                "processing_time_months": "3–6 mo",
                "fee_native": "AUD $4,770",
                "list": "MLTSSL",
            },
            {
                "visa_subclass": "482",
                "name": "Subclass 482",
                "stream": "Temporary Skill Shortage (Employer-Sponsored)",
                "pathway_type": "Temporary Skill Shortage (Employer-Sponsored)",
                "description": "Temporary work visa (up to 4 years) sponsored by an Australian employer.",
                "eligible": True,
                "age_limit": 99,
                "points_minimum": 0,
                "experience_required": "2 yrs",
                "processing_time_months": "3–6 mo",
                "fee_native": "AUD $4,770",
                "list": "CSOL",
            },
            {
                "visa_subclass": "485",
                "name": "Subclass 485",
                "stream": "General Skilled Migration",
                "pathway_type": "General Skilled Migration",
                "description": "Post-study work visa for international qualification holders in MLTSSL occupations.",
                "eligible": True,
                "age_limit": 44,
                "points_minimum": 65,
                "experience_required": "1+ yr",
                "processing_time_months": "3–6 mo",
                "fee_native": "AUD $4,770",
                "list": "MLTSSL",
            },
            {
                "visa_subclass": "491",
                "name": "Subclass 491",
                "stream": "Skilled Work Regional (Provisional, 5 years)",
                "pathway_type": "Skilled Work Regional (Provisional, 5 years)",
                "description": "5-year provisional visa for regional skilled workers; pathway to PR via 191.",
                "eligible": True,
                "age_limit": 44,
                "points_minimum": 65,
                "experience_required": "1+ yr",
                "processing_time_months": "3–6 mo",
                "fee_native": "AUD $4,770",
                "list": "MLTSSL",
            },
            {
                "visa_subclass": "494",
                "name": "Subclass 494",
                "stream": "Regional Sponsored (SESR)",
                "pathway_type": "Regional Sponsored (SESR)",
                "description": "Regional employer sponsored visa with PR pathway via Subclass 191.",
                "eligible": True,
                "age_limit": 44,
                "points_minimum": 0,
                "experience_required": "3 yrs",
                "processing_time_months": "3–6 mo",
                "fee_native": "AUD $4,770",
                "list": "MLTSSL",
            },
        ]

        update_payload = {
            "title": doc.get("title", "Actuary"),
            "code": "224111",
            "country_code": "AU",
            "visa_pathways": {
                "visa_eligibility": custom_visa_eligibility,
                "pathway_lists": ["MLTSSL", "CSOL"],
            },
            "pathway_lists": ["MLTSSL", "CSOL"],
            "recommended_visa_subclass": {"AU": "189"},
            "min_invitation_points": {
                "subclass_189": 80,
                "subclass_190": 75,
                "subclass_491": 65,
            },
        }

        # 3. Save via Admin PUT
        put_resp = await client.put(f"/api/occupation-master/{occ_id}", json=update_payload)
        assert put_resp.status_code == 200, f"PUT failed: {put_resp.text}"

        # 4. Verify Sales Occupation Detail (/api/sales/occupations/AU/224111)
        sales_resp = await client.get("/api/sales/occupations/AU/224111")
        assert sales_resp.status_code == 200, f"Sales GET failed: {sales_resp.text}"
        sales_data = sales_resp.json()
        visas = sales_data.get("visa_pathways") or []

        assert len(visas) >= 7, f"Expected at least 7 visa pathways, got {len(visas)}"

        # Check Subclass 189
        v189 = next((v for v in visas if v.get("subclass") == "189"), None)
        assert v189 is not None
        assert v189.get("pathway_type") == "Skilled Independent (PR)"
        assert "Permanent residence for skilled workers" in v189.get("description", "")
        assert v189.get("age_limit") == 44
        assert v189.get("points_minimum") == 65
        assert v189.get("fee_native") == "AUD $4,770"

        # Check Subclass 186
        v186 = next((v for v in visas if v.get("subclass") == "186"), None)
        assert v186 is not None
        assert v186.get("pathway_type") == "Employer Nomination Scheme (PR)"
        assert "Permanent residency via employer sponsorship" in v186.get("description", "")
        assert v186.get("experience_required") in ["3 yrs", "3"]
        assert v186.get("points_minimum") == 0

        # Check Subclass 482
        v482 = next((v for v in visas if v.get("subclass") == "482"), None)
        assert v482 is not None
        assert v482.get("age_limit") == 99
        assert v482.get("experience_required") in ["2 yrs", "2"]

        # Check Subclass 491
        v491 = next((v for v in visas if v.get("subclass") == "491"), None)
        assert v491 is not None
        assert "Skilled Work Regional" in v491.get("pathway_type", "")
        assert "PR via 191" in v491.get("description", "")

        # 5. Verify Public Atlas Single Occupation (/api/public-atlas/AU/224111)
        atlas_resp = await client.get("/api/public-atlas/AU/224111")
        assert atlas_resp.status_code == 200, f"Atlas GET failed: {atlas_resp.text}"
        atlas_data = atlas_resp.json()
        occ = atlas_data.get("occupation") or {}
        vp = occ.get("visa_pathways") or {}
        elig = vp.get("visa_eligibility") or []

        assert len(elig) >= 7
        e189 = next((e for e in elig if e.get("visa_subclass") == "189"), None)
        assert e189 is not None
        assert e189.get("stream") == "Skilled Independent (PR)"
        assert e189.get("fee_native") == "AUD $4,770"
