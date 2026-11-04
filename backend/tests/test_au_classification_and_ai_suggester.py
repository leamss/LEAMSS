"""Tests for Australia Occupation Suggestions, 6-Digit Strict Rule,
Work Experience Duty Alignment, and Dual Classification Versions (ANZSCO 2013 vs OSCA 2022).
"""
import pytest
import requests
import os
import json

BASE = os.environ.get("BACKEND_URL", "http://localhost:8001/api")


@pytest.fixture(scope="module")
def admin_token():
    # Login as admin
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    if r.status_code == 200:
        return r.json().get("token") or r.json().get("access_token")
    
    r2 = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "password123"}, timeout=10)
    if r2.status_code == 200:
        return r2.json().get("token") or r2.json().get("access_token")
    return None


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    if admin_token:
        return {"Authorization": f"Bearer {admin_token}"}
    return {}


def test_au_classification_versions_endpoint(auth_headers):
    """GET /sales/au-classification-versions should return ANZSCO 2013 and OSCA 2022 frameworks."""
    r = requests.get(f"{BASE}/sales/au-classification-versions", headers=auth_headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert "versions" in data
    versions = data["versions"]
    assert "ANZSCO_2013" in versions
    assert "OSCA_2022" in versions

    anz = versions["ANZSCO_2013"]
    assert "189" in anz.get("subclasses", [])
    assert "190" in anz.get("subclasses", [])
    assert "491" in anz.get("subclasses", [])

    osca = versions["OSCA_2022"]
    assert "482" in osca.get("subclasses", [])
    assert "186" in osca.get("subclasses", [])


def test_admin_add_and_remove_subclass(auth_headers):
    """Admin can dynamically add and remove visa subclasses from both versions."""
    # 1. Add subclass 494 to OSCA 2022
    r_add = requests.post(
        f"{BASE}/sales/au-classification-versions/subclasses",
        json={"version_key": "OSCA_2022", "subclass": "494", "action": "add"},
        headers=auth_headers,
    )
    assert r_add.status_code == 200, f"Add failed: {r_add.text}"
    res_add = r_add.json()
    assert "494" in res_add.get("subclasses", [])

    # 2. Verify it is present via GET
    r_get = requests.get(f"{BASE}/sales/au-classification-versions", headers=auth_headers)
    assert r_get.status_code == 200
    osca_subclasses = r_get.json()["versions"]["OSCA_2022"]["subclasses"]
    assert "494" in osca_subclasses

    # 3. Remove subclass 494 from OSCA 2022
    r_rem = requests.post(
        f"{BASE}/sales/au-classification-versions/subclasses",
        json={"version_key": "OSCA_2022", "subclass": "494", "action": "remove"},
        headers=auth_headers,
    )
    assert r_rem.status_code == 200, f"Remove failed: {r_rem.text}"
    res_rem = r_rem.json()
    assert "494" not in res_rem.get("subclasses", [])


def test_ai_suggest_occupation_strictly_six_digits(auth_headers):
    """AI code suggestion for Australia must NEVER suggest 4-digit unit group codes."""
    payload = {
        "description": "7 years experience in software engineering, backend API development with Django, microservices, cloud deployments on AWS and automated CI/CD pipelines.",
        "country_codes": ["AU"],
        "max_suggestions": 5,
        "qualification": "Bachelor",
        "field_of_study": "Computer Science",
        "years_experience_total": 7.0,
        "profile": {
            "primary_applicant": {
                "personal": {"age": 30, "full_name": "Software Engineer Applicant"},
                "education": {"highest_qualification": "Bachelor", "field_of_study": "Computer Science"},
                "professional": {
                    "current_profession": "Software Engineer",
                    "employer_name": "Tech Corp",
                    "employer_nature": "Information Technology",
                    "years_experience_total": 7.0,
                },
                "work_history": [
                    {
                        "designation": "Software Developer",
                        "employer": "Tech Corp",
                        "company_nature": "Information Technology",
                        "duties": "Designed microservices, developed REST APIs in Python/Django, optimized relational database queries, implemented unit tests with pytest.",
                    }
                ],
            }
        },
    }
    r = requests.post(f"{BASE}/sales/ai/suggest-occupation", json=payload, headers=auth_headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    res = r.json()
    suggestions = res.get("suggestions", [])
    assert len(suggestions) > 0, "Expected at least 1 suggestion"

    for s in suggestions:
        code_str = str(s.get("code", ""))
        assert len(code_str) == 6, f"Australia code must be exactly 6 digits, got '{code_str}'"
        assert code_str.isdigit(), f"Code must be all digits, got '{code_str}'"
        assert s.get("country_code") == "AU"


def test_ai_suggest_occupation_duty_matching_accuracy(auth_headers):
    """AI suggestion should accurately match occupation based on work experience duties."""
    # Test Accountant Duties
    accountant_payload = {
        "description": "5 years experience preparing balance sheets, profit and loss statements, GST/BAS statutory returns, reconciling general ledgers, and financial auditing.",
        "country_codes": ["AU"],
        "max_suggestions": 3,
        "qualification": "Bachelor",
        "field_of_study": "Accounting",
        "years_experience_total": 5.0,
        "profile": {
            "primary_applicant": {
                "personal": {"age": 28, "full_name": "Accountant Applicant"},
                "education": {"highest_qualification": "Bachelor", "field_of_study": "Accounting"},
                "professional": {
                    "current_profession": "Financial Accountant",
                    "employer_name": "PwC",
                    "employer_nature": "Financial & Accounting Services",
                    "years_experience_total": 5.0,
                },
                "work_history": [
                    {
                        "designation": "Accountant",
                        "employer": "PwC",
                        "company_nature": "Financial & Accounting Services",
                        "duties": "Prepared balance sheets, P&L accounts, statutory tax returns, reconciled bank accounts and general ledgers, conducted internal financial auditing.",
                    }
                ],
            }
        },
    }
    r = requests.post(f"{BASE}/sales/ai/suggest-occupation", json=accountant_payload, headers=auth_headers)
    assert r.status_code == 200
    suggestions = r.json().get("suggestions", [])
    assert len(suggestions) > 0

    top_code = str(suggestions[0]["code"])
    assert top_code.startswith("2211"), f"Expected Accountant 2211xx code, got {top_code}"
    assert len(top_code) == 6, f"Expected 6 digits, got {top_code}"
    assert "Accountant" in suggestions[0]["title"]


def test_ai_suggest_occupation_dual_framework_eligibility(auth_headers):
    """Suggestions for Australia must include dual framework classification_versions."""
    payload = {
        "description": "Software engineer with 6 years experience developing cloud backend services in Python and microservices architecture.",
        "country_codes": ["AU"],
        "qualification": "Bachelor",
        "field_of_study": "Computer Science",
        "years_experience_total": 6.0,
        "max_suggestions": 2,
    }
    r = requests.post(f"{BASE}/sales/ai/suggest-occupation", json=payload, headers=auth_headers)
    assert r.status_code == 200
    suggestions = r.json().get("suggestions", [])
    assert len(suggestions) > 0

    s0 = suggestions[0]
    assert "classification_versions" in s0, "Expected classification_versions in suggestion"
    cv = s0["classification_versions"]
    assert "anzsco_2013" in cv
    assert "osca_2022" in cv

    anz = cv["anzsco_2013"]
    assert anz.get("version_name") == "ANZSCO 2013"
    assert isinstance(anz.get("active_subclasses"), list)

    osca = cv["osca_2022"]
    assert osca.get("version_name") == "OSCA 2022"
    assert isinstance(osca.get("active_subclasses"), list)


def test_ai_suggest_occupation_experience_takes_precedence_over_degree(auth_headers):
    """Candidate with 5 years experience as a Senior Software Developer (even with a Commerce degree)
    must receive Software/Developer occupation codes (261312, 261313, 261399), NOT Management Consultant or sales.
    """
    payload = {
        "description": "5 years of experience in software development, creating backend web applications with Python/Django and React. Completed Bachelor of Commerce (B.Com). Current designation: Senior Software Developer.",
        "country_codes": ["AU"],
        "max_suggestions": 3,
        "qualification": "Bachelor of Commerce",
        "field_of_study": "Commerce",
        "years_experience_total": 5.0,
    }
    r = requests.post(f"{BASE}/sales/ai/suggest-occupation", json=payload, headers=auth_headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    suggestions = r.json().get("suggestions", [])
    assert len(suggestions) > 0, "Expected at least 1 suggestion"

    # Top suggested code must be in unit group 2613 (Developer Programmer / Software Engineer / Programmer)
    top_code = str(suggestions[0]["code"])
    assert top_code in ["261312", "261313", "261311", "261399", "261212"], (
        f"Expected Software/Developer occupation code (2613xx), got: {top_code} ({suggestions[0].get('title')})"
    )
    assert suggestions[0].get("assessing_body") == "Australian Computer Society"


def test_ai_suggest_occupation_multi_role_career_chronology(auth_headers):
    """Candidate with multi-role career history (e.g. 3 years as Systems Analyst + 4 years as Developer Programmer)
    must receive occupation code suggestions for BOTH eligible career stages across their entire work history,
    with total experience evaluated as 7.0 years.
    """
    payload = {
        "description": "7 years total IT experience across two roles. Worked 4 years as Developer Programmer developing Java and Python microservices and REST APIs at TechCorp. Currently working 3 years as Systems Analyst at DataSoft gathering system specifications, database schemas, and business process modeling.",
        "country_codes": ["AU"],
        "max_suggestions": 5,
        "qualification": "Bachelor of Information Technology",
        "field_of_study": "Information Technology",
        "years_experience_total": 7.0,
        "profile": {
            "primary_applicant": {
                "personal": {"age": 31, "full_name": "Multi Role Applicant"},
                "education": {"highest_qualification": "Bachelor", "field_of_study": "Information Technology"},
                "professional": {
                    "current_profession": "Systems Analyst",
                    "employer_name": "DataSoft",
                    "employer_nature": "Information Technology Services",
                    "years_experience_total": 7.0,
                },
                "work_history": [
                    {
                        "designation": "Systems Analyst",
                        "employer": "DataSoft",
                        "company_nature": "Information Technology Services",
                        "dates": "2022 - 2025",
                        "years": 3.0,
                        "duties": "Gathered business requirements, created UML system diagrams, designed relational database schemas, and integrated cloud microservices.",
                    },
                    {
                        "designation": "Developer Programmer",
                        "employer": "TechCorp",
                        "company_nature": "Software Development Services",
                        "dates": "2018 - 2022",
                        "years": 4.0,
                        "duties": "Developed REST APIs using Python and Java, wrote unit tests, maintained database queries, and deployed containerized services using Docker.",
                    },
                ],
            }
        },
    }
    r = requests.post(f"{BASE}/sales/ai/suggest-occupation", json=payload, headers=auth_headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    suggestions = r.json().get("suggestions", [])
    assert len(suggestions) >= 2, "Expected at least 2 suggestions"

    suggested_codes = [str(s.get("code")) for s in suggestions]
    # Verify that BOTH the current role (Systems Analyst: 261112) AND the past role (Developer Programmer/Software Engineer: 261312/261313) are suggested
    has_systems_analyst = any(c in ["261112", "261111"] for c in suggested_codes)
    has_developer = any(c in ["261312", "261313", "261311", "261399"] for c in suggested_codes)

    assert has_systems_analyst, f"Expected Systems Analyst (261112) to be suggested from current role. Got: {suggested_codes}"
    assert has_developer, f"Expected Developer Programmer / Software Engineer (2613xx) to be suggested from past role. Got: {suggested_codes}"

    # Verify that skills assessment total experience correctly reflects entire 7-year career
    for s in suggestions:
        sa = s.get("skills_assessment") or {}
        tot_exp = float(sa.get("total_experience_years") or 0.0)
        assert tot_exp >= 7.0, f"Expected at least 7.0 years total career experience evaluated, got {tot_exp}"


def test_ai_suggest_occupation_subclass_eligibility_and_targeting(auth_headers):
    """Suggestions for Australia must evaluate and attach active visa subclasses under ANZSCO 2013 and OSCA 2022,
    and prioritize target subclasses when requested.
    """
    # 1. Request targeting 189 & 190 GSM permanent visas
    payload_gsm = {
        "description": "5 years of experience in software engineering developing backend REST APIs in Python/Django and React. Candidate specifically targets Subclass 189 and 190 permanent visas.",
        "country_codes": ["AU"],
        "max_suggestions": 3,
        "qualification": "Bachelor of Science",
        "field_of_study": "Computer Science",
        "years_experience_total": 5.0,
        "target_subclasses": ["189", "190"],
        "target_framework": "ANZSCO_2013",
    }
    r = requests.post(f"{BASE}/sales/ai/suggest-occupation", json=payload_gsm, headers=auth_headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    suggestions = r.json().get("suggestions", [])
    assert len(suggestions) > 0

    for s in suggestions:
        assert "subclass_summary" in s, "Expected subclass_summary in suggestion"
        sub_sum = s["subclass_summary"]
        assert sub_sum["has_gsm_pathway"] is True, "Targeted GSM occupation must have active GSM pathway"
        assert "189" in sub_sum["anzsco_2013_subclasses"] or "190" in sub_sum["anzsco_2013_subclasses"]

        # Verify reasoning explicitly specifies subclass eligibility
        reasoning = s.get("reasoning", "")
        assert "Subclass" in reasoning or "subclass" in reasoning.lower()

    # 2. Request targeting OSCA 2022 Employer Sponsored visas (Subclass 482)
    payload_emp = {
        "description": "Chef with 6 years experience in commercial kitchens, menu development, and food safety looking for Employer Sponsored Subclass 482 visa.",
        "country_codes": ["AU"],
        "max_suggestions": 3,
        "qualification": "Certificate IV in Commercial Cookery",
        "field_of_study": "Culinary Arts",
        "years_experience_total": 6.0,
        "target_subclasses": ["482"],
        "target_framework": "OSCA_2022",
    }
    r_emp = requests.post(f"{BASE}/sales/ai/suggest-occupation", json=payload_emp, headers=auth_headers)
    assert r_emp.status_code == 200
    emp_suggs = r_emp.json().get("suggestions", [])
    assert len(emp_suggs) > 0
    top_chef = emp_suggs[0]
    assert "482" in top_chef.get("eligible_visas", [])
    assert top_chef.get("subclass_summary", {}).get("has_employer_pathway") is True


