"""
Test Government Forms API Endpoints
Tests for official government form templates feature:
- GET /api/step-documents/government-forms - List all countries with form counts
- GET /api/step-documents/government-forms/{country} - Get forms for a country
- GET /api/step-documents/government-forms/{country}/{visa_type} - Get filtered forms
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture
def auth_headers(admin_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestGovernmentFormsAllCountries:
    """Test GET /api/step-documents/government-forms - List all countries"""
    
    def test_get_all_countries_returns_200(self, auth_headers):
        """API returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_returns_7_countries(self, auth_headers):
        """API returns exactly 7 countries"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        assert "countries" in data, "Response should have 'countries' key"
        assert len(data["countries"]) == 7, f"Expected 7 countries, got {len(data['countries'])}"
    
    def test_countries_have_required_fields(self, auth_headers):
        """Each country has id, country name, authority, total_forms, base_url"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        for country in data["countries"]:
            assert "id" in country, "Country should have 'id'"
            assert "country" in country, "Country should have 'country' name"
            assert "authority" in country, "Country should have 'authority'"
            assert "total_forms" in country, "Country should have 'total_forms'"
            assert "base_url" in country, "Country should have 'base_url'"
    
    def test_australia_has_12_forms(self, auth_headers):
        """Australia should have 12 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        australia = next((c for c in data["countries"] if c["id"] == "australia"), None)
        assert australia is not None, "Australia should be in the list"
        assert australia["total_forms"] == 12, f"Australia should have 12 forms, got {australia['total_forms']}"
    
    def test_canada_has_10_forms(self, auth_headers):
        """Canada should have 10 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        canada = next((c for c in data["countries"] if c["id"] == "canada"), None)
        assert canada is not None, "Canada should be in the list"
        assert canada["total_forms"] == 10, f"Canada should have 10 forms, got {canada['total_forms']}"
    
    def test_usa_has_10_forms(self, auth_headers):
        """USA should have 10 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        usa = next((c for c in data["countries"] if c["id"] == "usa"), None)
        assert usa is not None, "USA should be in the list"
        assert usa["total_forms"] == 10, f"USA should have 10 forms, got {usa['total_forms']}"
    
    def test_uk_has_5_forms(self, auth_headers):
        """UK should have 5 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        uk = next((c for c in data["countries"] if c["id"] == "uk"), None)
        assert uk is not None, "UK should be in the list"
        assert uk["total_forms"] == 5, f"UK should have 5 forms, got {uk['total_forms']}"
    
    def test_new_zealand_has_5_forms(self, auth_headers):
        """New Zealand should have 5 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        nz = next((c for c in data["countries"] if c["id"] == "new_zealand"), None)
        assert nz is not None, "New Zealand should be in the list"
        assert nz["total_forms"] == 5, f"New Zealand should have 5 forms, got {nz['total_forms']}"
    
    def test_uae_has_3_forms(self, auth_headers):
        """UAE should have 3 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        uae = next((c for c in data["countries"] if c["id"] == "uae"), None)
        assert uae is not None, "UAE should be in the list"
        assert uae["total_forms"] == 3, f"UAE should have 3 forms, got {uae['total_forms']}"
    
    def test_singapore_has_3_forms(self, auth_headers):
        """Singapore should have 3 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        sg = next((c for c in data["countries"] if c["id"] == "singapore"), None)
        assert sg is not None, "Singapore should be in the list"
        assert sg["total_forms"] == 3, f"Singapore should have 3 forms, got {sg['total_forms']}"


class TestGovernmentFormsByCountry:
    """Test GET /api/step-documents/government-forms/{country}"""
    
    def test_australia_returns_200(self, auth_headers):
        """Australia endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/australia", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_australia_returns_12_forms(self, auth_headers):
        """Australia returns 12 forms with all required fields"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/australia", headers=auth_headers)
        data = response.json()
        assert "forms" in data, "Response should have 'forms' key"
        assert len(data["forms"]) == 12, f"Expected 12 forms, got {len(data['forms'])}"
        assert data["country"] == "Australia"
        assert data["authority"] == "Department of Home Affairs"
    
    def test_australia_forms_have_urls(self, auth_headers):
        """Each Australia form has a valid URL"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/australia", headers=auth_headers)
        data = response.json()
        for form in data["forms"]:
            assert "url" in form, f"Form {form.get('name')} should have 'url'"
            assert form["url"].startswith("http"), f"Form URL should be valid: {form['url']}"
    
    def test_australia_forms_have_required_fields(self, auth_headers):
        """Each form has name, description, url, category, mandatory, applies_to"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/australia", headers=auth_headers)
        data = response.json()
        for form in data["forms"]:
            assert "name" in form, "Form should have 'name'"
            assert "description" in form, "Form should have 'description'"
            assert "url" in form, "Form should have 'url'"
            assert "category" in form, "Form should have 'category'"
            assert "mandatory" in form, "Form should have 'mandatory'"
            assert "applies_to" in form, "Form should have 'applies_to'"
    
    def test_canada_returns_10_forms(self, auth_headers):
        """Canada returns 10 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/canada", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) == 10, f"Expected 10 forms, got {len(data['forms'])}"
        assert data["country"] == "Canada"
        assert "IRCC" in data["authority"]
    
    def test_usa_returns_10_forms(self, auth_headers):
        """USA returns 10 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/usa", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) == 10, f"Expected 10 forms, got {len(data['forms'])}"
        assert data["country"] == "United States"
        assert "USCIS" in data["authority"]
    
    def test_uk_returns_5_forms(self, auth_headers):
        """UK returns 5 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/uk", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) == 5, f"Expected 5 forms, got {len(data['forms'])}"
        assert data["country"] == "United Kingdom"
    
    def test_new_zealand_returns_5_forms(self, auth_headers):
        """New Zealand returns 5 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/new_zealand", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) == 5, f"Expected 5 forms, got {len(data['forms'])}"
        assert data["country"] == "New Zealand"
    
    def test_uae_returns_3_forms(self, auth_headers):
        """UAE returns 3 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/uae", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) == 3, f"Expected 3 forms, got {len(data['forms'])}"
        assert data["country"] == "United Arab Emirates"
    
    def test_singapore_returns_3_forms(self, auth_headers):
        """Singapore returns 3 forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/singapore", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) == 3, f"Expected 3 forms, got {len(data['forms'])}"
        assert data["country"] == "Singapore"
    
    def test_unknown_country_returns_empty(self, auth_headers):
        """Unknown country returns empty forms list"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/unknown_country", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["forms"] == [], "Unknown country should return empty forms"


class TestGovernmentFormsByVisa:
    """Test GET /api/step-documents/government-forms/{country}/{visa_type}"""
    
    def test_australia_189_returns_filtered_forms(self, auth_headers):
        """Australia 189 visa returns filtered forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/australia/189", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "forms" in data
        assert len(data["forms"]) > 0, "Should return forms for Subclass 189"
        # Check that returned forms apply to 189
        for form in data["forms"]:
            assert "189" in form["applies_to"], f"Form {form['name']} should apply to 189"
    
    def test_australia_500_returns_student_forms(self, auth_headers):
        """Australia 500 visa returns student-related forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/australia/500", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) > 0, "Should return forms for Subclass 500"
        # Should include Form 1276 (Student Visa application)
        form_names = [f["name"] for f in data["forms"]]
        assert any("1276" in name for name in form_names), "Should include Form 1276 for student visa"
    
    def test_canada_express_entry_returns_filtered_forms(self, auth_headers):
        """Canada Express Entry returns filtered forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/canada/express_entry", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["forms"]) > 0, "Should return forms for Express Entry"
        # Check that returned forms apply to express_entry
        for form in data["forms"]:
            assert any("express_entry" in a or "pr" in a for a in form["applies_to"]), \
                f"Form {form['name']} should apply to express_entry or pr"
    
    def test_canada_student_returns_study_permit_form(self, auth_headers):
        """Canada student visa returns study permit form"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/canada/student", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) > 0
        form_names = [f["name"] for f in data["forms"]]
        assert any("1294" in name or "Study Permit" in name for name in form_names), \
            "Should include IMM 1294 for study permit"
    
    def test_usa_h1b_returns_employer_forms(self, auth_headers):
        """USA H1B returns employer petition forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/usa/h1b", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) > 0
        form_names = [f["name"] for f in data["forms"]]
        # Should include I-129 and DS-160
        assert any("I-129" in name for name in form_names), "Should include Form I-129"
        assert any("DS-160" in name for name in form_names), "Should include DS-160"
    
    def test_usa_green_card_returns_immigrant_forms(self, auth_headers):
        """USA green card returns immigrant petition forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/usa/green_card", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) > 0
        form_names = [f["name"] for f in data["forms"]]
        # Should include I-140 and I-485
        assert any("I-140" in name or "I-485" in name for name in form_names), \
            "Should include I-140 or I-485 for green card"
    
    def test_uk_skilled_worker_returns_forms(self, auth_headers):
        """UK skilled worker returns relevant forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/uk/skilled_worker", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) > 0
    
    def test_singapore_ep_returns_forms(self, auth_headers):
        """Singapore EP returns employment pass forms"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/singapore/ep", headers=auth_headers)
        data = response.json()
        assert len(data["forms"]) > 0
        form_names = [f["name"] for f in data["forms"]]
        assert any("EP" in name or "Employment Pass" in name for name in form_names)


class TestFormDataIntegrity:
    """Test that form data is complete and valid"""
    
    def test_all_forms_have_valid_urls(self, auth_headers):
        """All forms across all countries have valid URLs"""
        countries = ["australia", "canada", "usa", "uk", "new_zealand", "uae", "singapore"]
        for country in countries:
            response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/{country}", headers=auth_headers)
            data = response.json()
            for form in data.get("forms", []):
                assert form["url"].startswith("http"), f"{country} form {form['name']} has invalid URL"
    
    def test_total_forms_count_is_48(self, auth_headers):
        """Total forms across all countries is 48"""
        response = requests.get(f"{BASE_URL}/api/step-documents/government-forms", headers=auth_headers)
        data = response.json()
        total = sum(c["total_forms"] for c in data["countries"])
        assert total == 48, f"Expected 48 total forms, got {total}"
    
    def test_mandatory_forms_exist(self, auth_headers):
        """Each country has at least one mandatory form"""
        countries = ["australia", "canada", "usa", "uk", "new_zealand", "uae", "singapore"]
        for country in countries:
            response = requests.get(f"{BASE_URL}/api/step-documents/government-forms/{country}", headers=auth_headers)
            data = response.json()
            mandatory_forms = [f for f in data.get("forms", []) if f.get("mandatory")]
            assert len(mandatory_forms) > 0, f"{country} should have at least one mandatory form"
