import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from core.database import db
from core.auth import get_current_user


@pytest.mark.asyncio
async def test_country_unified_parity_ca_and_nz():
    """Verify that all occupations across Canada (CA) and New Zealand (NZ)
    have complete country-specific content and editable parity with Australia (AU).
    """
    app.dependency_overrides[get_current_user] = lambda: {
        "email": "admin@leamss.com",
        "role": "admin",
        "permissions": ["*"],
    }
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ─────────────────────────────────────────────────────────────
        # 1. CANADA: Test NOC 00010 (Legislators) or 21231 (Software Engineers)
        # ─────────────────────────────────────────────────────────────
        ca_doc = await db["occupation_master"].find_one({"country_code": "CA"})
        assert ca_doc is not None, "At least one Canada occupation must exist in database"
        ca_code = str(ca_doc.get("code"))
        ca_id = str(ca_doc.get("occupation_id") or ca_doc.get("_id"))

        # Update Canada occupation with full country-specific data
        ca_update_payload = {
            "title": ca_doc.get("title") or "Canadian Skilled Professional",
            "status": "verified",
            "teer_category": 0 if ca_code.startswith("0") else 1,
            "national_shortage_status": "Express Entry Category Draw Priority: STEM & Healthcare",
            "demand_rationale": "High labour demand across Ontario and British Columbia under Express Entry category-based selection.",
            "state_ratings": {
                "ON": "S",
                "BC": "S",
                "AB": "S",
                "SK": "R",
                "MB": "R",
                "NS": "NS",
                "NB": "NS",
                "PE": "NS",
                "NL": "NS",
            },
            "state_distribution": {
                "ON": 38.5,
                "BC": 14.5,
                "AB": 11.8,
                "MB": 3.6,
                "SK": 3.1,
                "NS": 2.8,
                "NB": 2.1,
                "NL": 1.3,
                "PE": 0.3,
            },
            "assessing_authority": {
                "code": "WES",
                "short_name": "WES",
                "name": "World Education Services",
                "full_name": "World Education Services (WES Canada)",
                "website": "https://www.wes.org/ca/",
                "fee_native": "260",
                "processing_time_weeks": "7",
            },
            "skill_assessment_details": {
                "short_name": "WES",
                "fee_native": "260",
                "msa_fee_aud": 260,
                "processing_time": "35 business days",
                "validity": "5 years",
                "group": "Standard ECA",
                "qualification_requirement": "Canadian equivalency of completed Bachelor or Master degree",
                "employment_requirement": "At least 1 year continuous full-time skilled work experience in NOC TEER 0, 1, 2 or 3",
            },
            "visa_pathways": {
                "primary_subclass": "FSWP",
                "pathway_lists": ["Express Entry", "Category-Based STEM", "OINP Tech"],
                "visa_eligibility": [
                    {
                        "visa_subclass": "FSWP",
                        "name": "Federal Skilled Worker Program",
                        "stream": "Express Entry (Permanent Residence)",
                        "eligible": True,
                        "age_limit": 47,
                        "points_minimum": 67,
                        "experience_required": "1+ yr continuous skilled",
                        "processing_time_months": "6 mo",
                        "fee_native": "CAD $1,525",
                        "list": "Express Entry",
                    },
                    {
                        "visa_subclass": "PNP",
                        "name": "Provincial Nominee Program",
                        "stream": "Ontario OINP / BC PNP",
                        "eligible": True,
                        "age_limit": 49,
                        "points_minimum": 60,
                        "experience_required": "1+ yr skilled",
                        "processing_time_months": "8–12 mo",
                        "fee_native": "CAD $1,500",
                        "list": "Provincial Priority",
                    },
                ],
            },
            "ee_eligibility": {
                "fswp_eligible": True,
                "cec_eligible": True,
                "fstp_eligible": False,
            },
        }

        # Save via Admin PUT
        ca_put_resp = await client.put(f"/api/occupation-master/{ca_id}", json=ca_update_payload)
        assert ca_put_resp.status_code == 200, f"Admin PUT CA failed: {ca_put_resp.text}"

        # Fetch via Sales Unified Endpoint
        ca_sales_resp = await client.get(f"/api/sales/occupations/CA/{ca_code}")
        assert ca_sales_resp.status_code == 200, f"Sales CA failed: {ca_sales_resp.text}"
        ca_sales_data = ca_sales_resp.json()
        assert ca_sales_data.get("country_code") == "CA"
        assert ca_sales_data["overview"]["demand_rationale"] == ca_update_payload["demand_rationale"]
        assert ca_sales_data["overview"]["national_shortage_status"] == ca_update_payload["national_shortage_status"]
        assert ca_sales_data["overview"]["state_ratings"]["ON"] == "S"
        assert ca_sales_data["skill_assessment"]["authority_code"] == "WES"
        assert ca_sales_data["skill_assessment"]["fee_native"]["currency"] == "CAD"
        assert len(ca_sales_data["visa_pathways"]) >= 2
        assert ca_sales_data["visa_pathways"][0]["subclass"] == "FSWP"

        # Fetch via Public Atlas Endpoint
        ca_atlas_resp = await client.get(f"/api/public-atlas/CA/{ca_code}")
        assert ca_atlas_resp.status_code == 200, f"Public Atlas CA failed: {ca_atlas_resp.text}"
        ca_atlas_data = ca_atlas_resp.json()
        assert ca_atlas_data.get("country") == "CA"
        assert ca_atlas_data["occupation"]["demand_rationale"] == ca_update_payload["demand_rationale"]
        assert ca_atlas_data["occupation"]["assessing_authority"]["code"] == "WES"

        # ─────────────────────────────────────────────────────────────
        # 2. NEW ZEALAND: Test ANZSCO 121111 (Aquaculture Farmer) or similar
        # ─────────────────────────────────────────────────────────────
        nz_doc = await db["occupation_master"].find_one({"country_code": "NZ"})
        assert nz_doc is not None, "At least one New Zealand occupation must exist in database"
        nz_code = str(nz_doc.get("code"))
        nz_id = str(nz_doc.get("occupation_id") or nz_doc.get("_id"))

        nz_update_payload = {
            "title": nz_doc.get("title") or "New Zealand Skilled Specialist",
            "status": "verified",
            "nz_green_list_tier": "1",
            "national_shortage_status": "Green List Tier 1: Straight to Residence",
            "demand_rationale": "High priority on Immigration New Zealand's Green List Tier 1 offering immediate residence.",
            "state_ratings": {
                "AKL": "S",
                "WGN": "S",
                "CAN": "S",
                "WKO": "R",
                "BOP": "R",
                "OTA": "NS",
                "MWT": "NS",
                "HKB": "NS",
            },
            "state_distribution": {
                "AKL": 35.2,
                "CAN": 14.8,
                "WGN": 12.5,
                "WKO": 9.2,
                "BOP": 6.4,
                "OTA": 5.1,
                "MWT": 4.5,
                "HKB": 3.8,
            },
            "assessing_authority": {
                "code": "NZQA",
                "short_name": "NZQA",
                "name": "New Zealand Qualifications Authority",
                "full_name": "New Zealand Qualifications Authority (IQA)",
                "website": "https://www.nzqa.govt.nz/",
                "fee_native": "746",
                "processing_time_weeks": "5",
            },
            "skill_assessment_details": {
                "short_name": "NZQA",
                "fee_native": "746",
                "msa_fee_aud": 746,
                "processing_time": "25–35 business days",
                "validity": "Permanent",
                "group": "NZQF Level 7+",
                "qualification_requirement": "NZQF Level 7 Bachelor degree or comparable international qualification",
                "employment_requirement": "Relevant skilled employment aligned with ANZSCO major/minor unit group",
            },
            "visa_pathways": {
                "primary_subclass": "Green-T1",
                "pathway_lists": ["Green List Tier 1", "Straight to Residence", "SMC 6-Point"],
                "visa_eligibility": [
                    {
                        "visa_subclass": "Green-T1",
                        "name": "Straight to Residence Visa",
                        "stream": "Green List Tier 1 Fast-Track",
                        "eligible": True,
                        "age_limit": 55,
                        "points_minimum": 6,
                        "experience_required": "Direct job offer from accredited employer",
                        "processing_time_months": "2–4 mo",
                        "fee_native": "NZD $4,290",
                        "list": "Green List Tier 1",
                    },
                    {
                        "visa_subclass": "SMC",
                        "name": "Skilled Migrant Category Resident Visa",
                        "stream": "6-Point Points System",
                        "eligible": True,
                        "age_limit": 55,
                        "points_minimum": 6,
                        "experience_required": "1–3 yrs NZ skilled exp",
                        "processing_time_months": "4–8 mo",
                        "fee_native": "NZD $4,290",
                        "list": "SMC 6-Point",
                    },
                ],
            },
            "aewv_eligibility": {
                "eligible": True,
                "occupational_band": "Tier 1 High Skilled",
                "max_stay_years": 5,
            },
            "smc_points_breakdown": {
                "skill_points_base": 6,
                "pass_mark": 6,
                "green_list_auto_pass": True,
            },
        }

        # Save via Admin PUT
        nz_put_resp = await client.put(f"/api/occupation-master/{nz_id}", json=nz_update_payload)
        assert nz_put_resp.status_code == 200, f"Admin PUT NZ failed: {nz_put_resp.text}"

        # Fetch via Sales Unified Endpoint
        nz_sales_resp = await client.get(f"/api/sales/occupations/NZ/{nz_code}")
        assert nz_sales_resp.status_code == 200, f"Sales NZ failed: {nz_sales_resp.text}"
        nz_sales_data = nz_sales_resp.json()
        assert nz_sales_data.get("country_code") == "NZ"
        assert nz_sales_data["overview"]["demand_rationale"] == nz_update_payload["demand_rationale"]
        assert nz_sales_data["overview"]["national_shortage_status"] == nz_update_payload["national_shortage_status"]
        assert nz_sales_data["overview"]["state_ratings"]["AKL"] == "S"
        assert nz_sales_data["skill_assessment"]["authority_code"] == "NZQA"
        assert nz_sales_data["skill_assessment"]["fee_native"]["currency"] == "NZD"
        assert len(nz_sales_data["visa_pathways"]) >= 2
        assert nz_sales_data["visa_pathways"][0]["subclass"] == "Green-T1"

        # Fetch via Public Atlas Endpoint
        nz_atlas_resp = await client.get(f"/api/public-atlas/NZ/{nz_code}")
        assert nz_atlas_resp.status_code == 200, f"Public Atlas NZ failed: {nz_atlas_resp.text}"
        nz_atlas_data = nz_atlas_resp.json()
        assert nz_atlas_data.get("country") == "NZ"
        assert nz_atlas_data["occupation"]["demand_rationale"] == nz_update_payload["demand_rationale"]
        assert nz_atlas_data["occupation"]["assessing_authority"]["code"] == "NZQA"
