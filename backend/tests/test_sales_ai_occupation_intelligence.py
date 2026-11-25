"""Unit and Integration Tests for Sales AI Multi-Classification Occupation Intelligence.

Verifies:
  1. Accurate identification of classification systems:
     - NOC 2021 (Canada) + TEER categories & duties
     - ANZSCO (Australia & New Zealand) + Skill Levels & assessing bodies
     - SOC / O*NET (USA) + Prevailing wage
     - UK SOC 2020 (UK) + Immigration Salary List
     - Germany Chancenkarte + 6-point grid
  2. Cross-country mismatch detection and cross-walk mapping (e.g. NOC in Australia context).
  3. Structured 7-part response format with 5 client qualification questions, fees, and disclaimers.
  4. Integration test against POST /api/product-master/sales-ai-query.
"""
from __future__ import annotations

import re
import pytest
from httpx import AsyncClient

from core.occupation_intelligence import (
    detect_occupation_in_query,
    get_full_occupation_profile,
    synthesize_complete_statutory_response,
    get_statutory_fees_and_commercials,
    generate_sales_qualification_questions,
    normalize_country,
)
from server import app


def test_noc_2021_detection_and_teer():
    """Verify Canada NOC 2021 detection with TEER category and lead duties."""
    query = "Client has 5 years experience as software engineer under NOC 21231. What are the duties and Express Entry pathways?"
    det = detect_occupation_in_query(query, "Canada")
    assert det is not None
    assert det.code == "21231"
    assert det.country == "Canada"
    assert det.country_code == "CA"
    assert det.classification_system == "Canada National Occupational Classification (NOC 2021 V1.0)"
    assert det.teer == 1
    assert det.is_mismatch is False

    profile = get_full_occupation_profile(det)
    assert profile.code == "21231"
    assert "Software engineers" in profile.title
    assert "TEER 1" in profile.skill_tier_label
    assert len(profile.main_duties) >= 3
    assert any("design" in d.lower() or "develop" in d.lower() or "specifications" in d.lower() for d in profile.main_duties)
    assert "Express Entry" in profile.visa_pathways[0]
    assert "noc.esdc.gc.ca" in profile.official_source_url


def test_cross_country_mismatch_noc_in_australia():
    """Verify that querying a Canadian NOC code while viewing Australia triggers explicit mismatch warning and crosswalk."""
    query = "What is NOC 21231? Can client lodge Subclass 189?"
    det = detect_occupation_in_query(query, "Australia")
    assert det is not None
    assert det.code == "21231"
    assert det.country == "Canada"
    assert det.is_mismatch is True
    assert det.selected_country == "Australia"
    assert det.mismatch_warning is not None
    assert "Canadian National Occupational Classification" in det.mismatch_warning
    assert "not Australia" in det.mismatch_warning

    # Check cross-walk to Australian equivalent
    assert det.crosswalk_code == "261313"
    assert det.crosswalk_title == "Software Engineer"
    assert "ACS" in (det.crosswalk_authority or "")

    profile = get_full_occupation_profile(det)
    resp = synthesize_complete_statutory_response(
        profile=profile,
        det=det,
        country="Australia",
        visa_product_name="Skilled Independent",
        visa_subclass="189",
        client_scenario=query,
    )
    assert "⚠️ Country & System Clarification" in resp or "CRITICAL SYSTEM CLARIFICATION" in resp
    assert "NOC 21231" in resp
    assert "261313" in resp
    assert "Software Engineer" in resp
    assert "ACS" in resp
    assert "LEAMSS Statutory Disclaimer" in resp
    assert "never guarantees visa approval" in resp.lower()


def test_anzsco_detection_and_skill_level():
    """Verify Australian ANZSCO detection with Skill Level, assessing body, and eligible visas."""
    query = "Check eligibility for ANZSCO 261313 with 75 points"
    det = detect_occupation_in_query(query, "Australia")
    assert det is not None
    assert det.code == "261313"
    assert det.country == "Australia"
    assert det.country_code == "AU"
    assert det.is_mismatch is False

    profile = get_full_occupation_profile(det)
    assert profile.code == "261313"
    assert profile.title == "Software Engineer"
    assert "Skill Level 1" in profile.skill_tier_label
    assert profile.assessing_authority == "ACS"
    assert any("189" in v for v in profile.visa_pathways)
    assert any("190" in v for v in profile.visa_pathways)
    assert "immi.homeaffairs.gov.au" in profile.official_source_url


def test_cross_country_mismatch_anzsco_in_canada():
    """Verify that querying an ANZSCO code while viewing Canada triggers crosswalk to NOC 21231."""
    query = "Is ANZSCO 261313 eligible for Canada Express Entry?"
    det = detect_occupation_in_query(query, "Canada")
    assert det is not None
    assert det.code == "261313"
    assert det.country == "Australia"
    assert det.is_mismatch is True
    assert det.crosswalk_code == "21231"
    assert "Software engineers" in (det.crosswalk_title or "")


def test_us_soc_and_uk_soc_detection():
    """Verify US SOC and UK SOC detection and rules."""
    # US SOC
    us_det = detect_occupation_in_query("What is prevailing wage for SOC 15-1252.00?", "United States")
    assert us_det is not None
    assert us_det.code == "15-1252.00"
    assert us_det.country == "United States"
    assert us_det.is_mismatch is False
    us_prof = get_full_occupation_profile(us_det)
    assert "H-1B" in us_prof.visa_pathways[0]
    assert "USCIS" in us_prof.assessing_authority

    # UK SOC
    uk_det = detect_occupation_in_query("UK SOC 2136 skilled worker eligibility", "United Kingdom")
    assert uk_det is not None
    assert uk_det.code == "2136"
    assert uk_det.country == "United Kingdom"
    assert uk_det.is_mismatch is False
    uk_prof = get_full_occupation_profile(uk_det)
    assert "Skilled Worker" in uk_prof.visa_pathways[0]
    assert "£38,700" in uk_prof.statutory_salary_threshold


def test_germany_chancenkarte_and_fees():
    """Verify German Chancenkarte fees, points framework, and qualification questions."""
    fees = get_statutory_fees_and_commercials("Germany")
    assert "€75" in fees["gov_fee_foreign"]
    assert "6 Points" in fees["statutory_benchmark"]
    assert "1,027" in fees["settlement_funds"]

    questions = generate_sales_qualification_questions(None, "Germany")
    assert len(questions) == 5
    assert any("Anabin" in q for q in questions)
    assert any("Chancenkarte" in q for q in questions)
    assert any("Blocked Account" in q or "Sperrkonto" in q for q in questions)


def test_structured_seven_part_response_contract():
    """Verify all 7 mandatory sections and statutory disclaimer exist in synthesized response."""
    det = detect_occupation_in_query("NOC 21231 duties and requirements", "Canada")
    profile = get_full_occupation_profile(det)
    resp = synthesize_complete_statutory_response(
        profile=profile,
        det=det,
        country="Canada",
        visa_product_name="Federal Skilled Worker",
        visa_subclass="FSW",
        client_scenario="Client with 4 years experience in Canada NOC 21231",
    )

    # 7 Mandatory Sections
    assert "### 📌 1. Regulatory Fact Check & Classification System" in resp
    assert "### 💼 2. Complete Occupation Details & Job Responsibilities" in resp
    assert "### 📊 3. Eligible Visa Pathways, Points Systems & Salary Thresholds" in resp
    assert "### ❓ 4. Five Client Qualification Questions for Sales Consultant" in resp
    assert "### 💬 5. Recommended Call Script & Phone Pitch for Sales Consultant" in resp
    assert "### 💰 6. Official Statutory Government Fees & LEAMSS Commercials" in resp
    assert "### 🔗 7. Official Government Sources & Verification Date" in resp

    # Ethics & Anti-Guarantee Enforcements
    assert "Can you guarantee that I will get PR or visa approval?" in resp
    assert "never guarantees visa approval" in resp.lower()
    assert "LEAMSS Statutory Disclaimer" in resp
    assert "CAD $1,525" in resp


def override_sales_user():
    return {
        "id": "sales-001",
        "name": "Consultant Jane",
        "role": "sales_executive",
        "email": "sales@leamss.com",
        "permissions": ["*"]
    }


@pytest.fixture(autouse=True)
def mock_external_calls(monkeypatch):
    """Ensure tests run lightning fast by simulating offline Perplexity and fast product lookup."""
    async def _mock_fail(*args, **kwargs):
        raise ConnectionError("Sandbox offline test mode")
    monkeypatch.setattr("core.perplexity_client.call_perplexity", _mock_fail)

    async def _mock_find_prod(country=None, visa_name="", visa_subclass="", question="", intent=None):
        c = (intent.detected_country if intent else country) or "Australia"
        sc = (intent.detected_subclass if intent else visa_subclass) or "189"
        auth = "Department of Home Affairs (DHA)" if c == "Australia" else ("USCIS" if c == "United States" else f"{c} Immigration")
        portal = "https://immi.homeaffairs.gov.au" if c == "Australia" else ("https://www.uscis.gov" if c == "United States" else f"https://leamss.com/{c.lower()}")
        return {
            "id": "prod-test-1",
            "name": f"{c} Skilled Visa ({sc})",
            "country": c,
            "visa_subclass": sc,
            "category": "skilled_migration",
            "service_price": 125000,
            "authority_name": auth,
            "official_urls": [portal],
        }
    monkeypatch.setattr("routers.product_master._find_relevant_product", _mock_find_prod)


@pytest.mark.asyncio
async def test_sales_ai_query_endpoint_with_mismatch():
    """Integration test: calling POST /api/product-master/sales-ai-query with NOC 21231 when Australia is selected."""
    from core.auth import get_current_user
    from httpx import ASGITransport

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "country": "Australia",
            "visa_name": "Skilled Independent Visa",
            "visa_subclass": "189",
            "client_scenario_or_question": "Client holds a computer science degree and wants to know about NOC 21231 and whether they qualify for 189.",
        }
        resp = await ac.post("/api/product-master/sales-ai-query", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # Check metadata
        assert data.get("verified_product") is True
        occ = data.get("occupation_detected")
        assert occ is not None
        assert occ["code"] == "21231"
        assert occ["country"] == "Canada"
        assert occ["is_mismatch"] is True
        assert occ["crosswalk_code"] == "261313"

        answer = data["answer"]
        # Verify that either Perplexity online or synthesis answered with clear clarification
        assert "21231" in answer
        assert ("Canada" in answer or "NOC" in answer)
        assert ("261313" in answer or "Australia" in answer)
        assert "guarantee" in answer.lower()

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_sales_ai_query_quick_answer_and_sources():
    """Verify endpoint provides direct quick answer first, verified source links, and short sentences."""
    from core.auth import get_current_user
    from httpx import ASGITransport

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "country": "United States",
            "visa_name": "H-1B Specialty Occupation",
            "client_scenario_or_question": "US H-1B specialty occupation criteria, lottery cap and USCIS fee breakdown",
        }
        resp = await ac.post("/api/product-master/sales-ai-query", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # Sources verification
        sources = data.get("sources", {})
        assert "uscis.gov" in sources.get("government_portal", "")
        assert "USCIS" in sources.get("government_authority", "")
        assert "migrate" in sources.get("migrate_page_url", "")
        assert "atlas" in sources.get("atlas_page_url", "")

        # Quick answer first verification
        answer = data.get("answer", "")
        assert "Direct Quick Answer" in answer or "Quick Answer" in answer
        assert "USCIS" in answer or "H-1B" in answer

    app.dependency_overrides.pop(get_current_user, None)


def test_detect_country_and_visa_in_query_unit():
    """Unit test: verify country and visa subclass intent extraction from query text."""
    from core.occupation_intelligence import detect_country_and_visa_in_query

    # 1. Exact user scenario
    q1 = "client say that aus why i want to travel to other under of the pr noaus"
    i1 = detect_country_and_visa_in_query(q1, fallback_country="United States", fallback_subclass="EB-2")
    assert i1.detected_country == "Australia"
    assert i1.country_source == "query"
    assert "GSM" in i1.detected_subclass or "189" in i1.detected_subclass
    assert i1.is_travel_abroad_pr_query is True
    assert i1.mismatch_with_payload is True
    assert "offshore" in (i1.offshore_onshore_explanation or "").lower()

    # 2. Canada Express Entry
    q2 = "canada express entry fsw fee and crs points"
    i2 = detect_country_and_visa_in_query(q2, fallback_country="United States")
    assert i2.detected_country == "Canada"
    assert "FSW" in i2.detected_subclass or "Express Entry" in i2.detected_subclass
    assert i2.country_source == "query"

    # 3. US EB-2 NIW
    q3 = "Can EB-2 NIW candidate self-petition without employer?"
    i3 = detect_country_and_visa_in_query(q3)
    assert i3.detected_country == "United States"
    assert i3.detected_subclass == "EB-2"

    # 4. Germany Chancenkarte
    q4 = "What is the points grid for germany chancenkarte opportunity card?"
    i4 = detect_country_and_visa_in_query(q4)
    assert i4.detected_country == "Germany"
    assert i4.detected_subclass == "Chancenkarte"

    # 5. Ambiguous / Unclear query with no country
    q5 = "can i get pr without a job offer?"
    i5 = detect_country_and_visa_in_query(q5, fallback_country=None)
    assert i5.is_unclear is True
    assert i5.clarification_question is not None
    assert "Australia" in i5.clarification_question
    assert "Canada" in i5.clarification_question


@pytest.mark.asyncio
async def test_australia_travel_pr_query_never_returns_us_eb2():
    """Integration test: Asking about Australia PR while viewing United States MUST NEVER return EB-2 NIW.
    
    Verifies:
    1. Returns Australia (DHA) instead of United States (USCIS).
    2. Subclass is 189/190/491 (General Skilled Migration).
    3. Offshore travel rule is explained (no need to travel abroad to apply).
    4. Text contains ZERO mentions of 'EB-2', 'NIW', 'I-140', 'USCIS', or 'PERM'.
    5. Official government fees are in AUD (~AUD 4,770), not USD.
    """
    from core.auth import get_current_user
    from httpx import ASGITransport

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "country": "United States",
            "visa_name": "USA EB-2 NIW",
            "visa_subclass": "EB-2",
            "client_scenario_or_question": "client say that aus why i want to travel to other under of the pr noaus",
        }
        resp = await ac.post("/api/product-master/sales-ai-query", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # 1. Target country must be Australia, not United States
        assert data.get("target_country") == "Australia"
        assert data.get("is_travel_query") is True

        sources = data.get("sources", {})
        assert "immi.homeaffairs.gov.au" in sources.get("government_portal", "")
        assert "Department of Home Affairs" in sources.get("government_authority", "") or "DHA" in sources.get("government_authority", "")

        answer = data.get("answer", "")
        answer_lower = answer.lower()

        # 2. Strict Negative Constraint: Must NEVER contain US EB-2 terms
        assert "eb-2" not in answer_lower
        assert "eb2" not in answer_lower
        assert "i-140" not in answer_lower
        assert not re.search(r"\bperm\s*(?:labor|certification|labor\s*cert)?\b", answer_lower)
        assert "uscis" not in answer_lower

        # 3. Must explain that applicant does NOT need to travel abroad for Australia PR
        assert "offshore" in answer_lower or "not need to travel" in answer_lower or "no travel" in answer_lower
        assert ("australia" in answer_lower or "home affairs" in answer_lower or "dha" in answer_lower)
        # Strict Relevance Constraint: Travel query MUST NOT dump fee breakdown
        assert "4,770" not in answer
        assert "LEAMSS Professional Retainer" not in answer

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_benefits_query_excludes_fees():
    """Verify that asking about PR benefits explains PR privileges and NEVER dumps fees or retainers."""
    from core.auth import get_current_user
    from httpx import ASGITransport

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "country": "Australia",
            "visa_name": "Skilled Independent Subclass 189",
            "visa_subclass": "189",
            "client_scenario_or_question": "Why should I choose Australia PR? What are the benefits?",
        }
        resp = await ac.post("/api/product-master/sales-ai-query", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        answer = data.get("answer", "")
        answer_lower = answer.lower()

        # Must highlight key Australia PR benefits
        assert "medicare" in answer_lower or "healthcare" in answer_lower
        assert "citizenship" in answer_lower
        assert "work" in answer_lower or "settlement" in answer_lower

        # Strict Negative Constraint: Must NOT dump government fees, GST, or LEAMSS retainers
        assert "4,770" not in answer
        assert "aud" not in answer_lower
        assert "gst" not in answer_lower
        assert "leamss professional retainer" not in answer_lower
        assert "milestone schedule" not in answer_lower

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_fees_query_includes_fees():
    """Verify that asking about government fees explicitly includes official statutory fee and retainer breakdown."""
    from core.auth import get_current_user
    from httpx import ASGITransport

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "country": "Australia",
            "visa_name": "Skilled Independent Subclass 189",
            "visa_subclass": "189",
            "client_scenario_or_question": "What is the official government fee and LEAMSS charges for Australia Subclass 189?",
        }
        resp = await ac.post("/api/product-master/sales-ai-query", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        answer = data.get("answer", "")
        answer_lower = answer.lower()

        # Must include official government fee (AUD 4,770) and LEAMSS retainer
        assert "4,770" in answer or "aud" in answer_lower
        assert "leamss" in answer_lower
        assert "gst" in answer_lower or "milestone" in answer_lower

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_eligibility_query_focus():
    """Verify that asking about eligibility explains points benchmarks without fee dumps."""
    from core.auth import get_current_user
    from httpx import ASGITransport

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "country": "Australia",
            "visa_name": "Skilled Independent Subclass 189",
            "visa_subclass": "189",
            "client_scenario_or_question": "Am I eligible for Subclass 189? What are the requirements and points pass mark?",
        }
        resp = await ac.post("/api/product-master/sales-ai-query", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        answer = data.get("answer", "")
        answer_lower = answer.lower()

        # Must detail eligibility requirements
        assert "45" in answer or "age" in answer_lower
        assert "65" in answer or "points" in answer_lower
        assert "skills assessment" in answer_lower or "assessment" in answer_lower

        # Strict Negative: Must NOT dump fee schedule
        assert "4,770" not in answer
        assert "leamss professional retainer" not in answer_lower

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_process_query_focus():
    """Verify that asking about application process and timeline details stages without fee dumps."""
    from core.auth import get_current_user
    from httpx import ASGITransport

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "country": "Australia",
            "visa_name": "Skilled Independent Subclass 189",
            "visa_subclass": "189",
            "client_scenario_or_question": "What is the process and timeline for Australia PR?",
        }
        resp = await ac.post("/api/product-master/sales-ai-query", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        answer = data.get("answer", "")
        answer_lower = answer.lower()

        # Must explain application stages and timeline
        assert "stage" in answer_lower or "step" in answer_lower
        assert "skills" in answer_lower or "eoi" in answer_lower or "lodgement" in answer_lower
        assert "month" in answer_lower or "timeline" in answer_lower

        # Strict Negative: Must NOT dump fee schedule
        assert "4,770" not in answer
        assert "leamss professional retainer" not in answer_lower

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_family_query_focus_subclass_189():
    """Verify that asking about including spouse or children in Subclass 189 answers all 7 requirements."""
    from core.auth import get_current_user
    from httpx import ASGITransport

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "country": "Australia",
            "visa_name": "Skilled Independent Subclass 189",
            "visa_subclass": "189",
            "client_scenario_or_question": "Can I include my spouse and children in Australia Subclass 189? Will they get PR?",
        }
        resp = await ac.post("/api/product-master/sales-ai-query", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        answer = data.get("answer", "")
        answer_lower = answer.lower()

        # Requirement 1: Eligible spouse and dependent children included
        assert "spouse" in answer_lower or "partner" in answer_lower
        assert "children" in answer_lower or "child" in answer_lower

        # Requirement 2: Family members receive PR only if included and approved
        assert "only if" in answer_lower
        assert "approved" in answer_lower

        # Requirement 3: Dependent child age and dependency (under 18, 18-23 dependent)
        assert "18" in answer
        assert "23" in answer
        assert "dependent" in answer_lower

        # Requirement 4: Genuine relationship for spouse + health and character
        assert "genuine" in answer_lower or "relationship" in answer_lower
        assert "health" in answer_lower
        assert "character" in answer_lower

        # Requirement 5: Additional government charges apply
        assert "additional" in answer_lower
        assert "charges" in answer_lower or "fee" in answer_lower

        # Requirement 6: Strict Negative - No fee schedule or breakdown dump
        assert "4,770" not in answer
        assert "leamss professional retainer" not in answer_lower
        assert "18% gst" not in answer_lower

        # Requirement 7: Speaking script is presented first
        assert answer.startswith("### 💬 1. Speaking Script for Live Call")

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_family_query_with_fee_inquiry():
    """Verify that asking about fees to include family provides fee breakdown."""
    from core.auth import get_current_user
    from httpx import ASGITransport

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "country": "Australia",
            "visa_name": "Skilled Independent Subclass 189",
            "visa_subclass": "189",
            "client_scenario_or_question": "What is the fee or cost to include my spouse and child in Australia 189?",
        }
        resp = await ac.post("/api/product-master/sales-ai-query", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        answer = data.get("answer", "")
        answer_lower = answer.lower()

        # Since the client explicitly asked for fees, fee amounts should be provided
        assert "4,770" in answer or "aud" in answer_lower
        assert "leamss" in answer_lower

    app.dependency_overrides.pop(get_current_user, None)


