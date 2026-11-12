import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from core.database import db
from core.auth import get_current_user


@pytest.mark.asyncio
async def test_skill_assessment_unified_edit_and_sync():
    """Verify that editing Skill Assessment in Admin updates both Sales and Public Atlas."""
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

        # 2. Prepare payload with full Skill Assessment data matching user specification
        std_pathways = [
            {
                "pathway": "Group B Standard Pathway",
                "requirement": "AQF Bachelor degree or higher (relevant or unrelated field) + At least 1 year of post-qualification employment in a highly relevant occupation",
            },
            {
                "pathway": "Priority Processing",
                "requirement": "Available for urgent assessment (fast-tracked within 10 business days)",
            },
        ]
        std_docs = [
            "Passport bio-data page (colour scan)",
            "Official Degree / Diploma Certificate",
            "Full Academic Transcripts for all completed qualifications",
            "Formal Statement of Service on company letterhead (with duties, hours & dates)",
            "Payment evidence (payslips, tax returns, bank statements for all claimed periods)",
            "Organisational Chart on company letterhead (for Managerial / Group A occupations)",
            "Detailed Professional CV / Résumé",
            "Official English translations for any non-English documents",
        ]

        update_payload = {
            "title": doc.get("title", "Actuary"),
            "code": "224111",
            "country_code": "AU",
            "skill_level": 1,
            "assessing_authority": {
                "code": "VETASSESS",
                "short_name": "VETASSESS",
                "name": "Vocational Education and Training Assessment Services",
                "full_name": "Vocational Education and Training Assessment Services",
                "website": "https://www.vetassess.com.au/",
                "url": "https://www.vetassess.com.au/",
                "fee_native": 1188.0,
                "fee_currency": "AUD",
                "processing_time_weeks": 11,
            },
            "skill_assessment_details": {
                "authority": "VETASSESS",
                "short_name": "VETASSESS",
                "full_name": "Vocational Education and Training Assessment Services",
                "website": "https://www.vetassess.com.au/",
                "msa_fee_aud": 1188.0,
                "fee_native": 1188.0,
                "processing_time": "9–13 weeks",
                "fast_track_days": "10–20 days",
                "priority_days_min": 10,
                "priority_days_max": 20,
                "validity": "3 years",
                "validity_years": 3,
                "group": "Group B",
                "framework": "Group B Occupation",
                "framework_title": "Group B Occupation",
                "qualification_requirement": "AQF Bachelor degree or higher (relevant or unrelated field)",
                "employment_requirement": "At least 1 year of post-qualification employment in a highly relevant occupation",
                "english_required": "Competent English (IELTS 6.0 / PTE 50 or exempt)",
                "pathways": std_pathways,
                "standard_pathway": "Group B Standard Pathway",
                "pathway_requirement": "AQF Bachelor degree or higher + At least 1 year relevant employment",
                "documents_required": std_docs,
            },
            "qualification_rules": "VETASSESS General Professional Occupations Assessment — Group B. AQF Bachelor degree or higher with 1 year post-qualification experience.",
        }

        # 3. Save via Admin PUT
        put_resp = await client.put(f"/api/occupation-master/{occ_id}", json=update_payload)
        assert put_resp.status_code == 200, f"PUT failed: {put_resp.text}"

        # 4. Verify Sales Occupation Detail (/api/sales/occupations/AU/224111)
        sales_resp = await client.get("/api/sales/occupations/AU/224111")
        assert sales_resp.status_code == 200, f"Sales GET failed: {sales_resp.text}"
        sales_data = sales_resp.json()
        skill = sales_data.get("skill_assessment") or {}

        assert skill.get("short_name") == "VETASSESS"
        assert "vetassess.com.au" in skill.get("website", "")
        assert skill.get("assessment_fee_aud") == 1188.0
        assert skill.get("criteria_general", {}).get("qualification") == "AQF Bachelor degree or higher (relevant or unrelated field)"
        assert skill.get("criteria_general", {}).get("employment") == "At least 1 year of post-qualification employment in a highly relevant occupation"
        assert skill.get("criteria_general", {}).get("validity") in ["3 Years", "3 years"]
        assert len(skill.get("pathways", [])) == 2
        assert len(skill.get("documents_required", [])) == 8

        # 5. Verify Public Atlas Single Occupation (/api/public-atlas/AU/224111)
        atlas_resp = await client.get("/api/public-atlas/AU/224111")
        assert atlas_resp.status_code == 200, f"Atlas GET failed: {atlas_resp.text}"
        atlas_data = atlas_resp.json()
        occ = atlas_data.get("occupation") or {}

        aa = occ.get("assessing_authority") or {}
        sad = occ.get("skill_assessment_details") or {}

        assert aa.get("short_name") == "VETASSESS" or aa.get("code") == "VETASSESS"
        assert "vetassess.com.au" in (aa.get("website") or sad.get("website", ""))
        assert sad.get("msa_fee_aud") == 1188.0 or aa.get("fee_native") == 1188.0
        assert sad.get("qualification_requirement") == "AQF Bachelor degree or higher (relevant or unrelated field)"
        assert sad.get("employment_requirement") == "At least 1 year of post-qualification employment in a highly relevant occupation"
        assert len(sad.get("pathways", [])) == 2
        assert len(sad.get("documents_required", [])) == 8
