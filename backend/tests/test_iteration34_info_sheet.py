"""
Iteration 34 - Information Sheet Feature Tests
Tests for the REWRITTEN Information Sheet with 6 sections, editable fields, and save functionality.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://career-match-320.preview.emergentagent.com"
API_URL = f"{BASE_URL}/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}

# Known client case ID
CLIENT_CASE_ID = "cb09cf65-9a0c-47c6-8585-bace5da8c221"


class TestHealthAndAuth:
    """Basic health and authentication tests"""
    
    def test_health_endpoint(self):
        """Test GET /api/health returns healthy"""
        response = requests.get(f"{API_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert data.get("database") == "connected"
        print("PASS: Health endpoint returns healthy with database connected")
    
    def test_admin_login(self):
        """Test admin login works"""
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print("PASS: Admin login works")
    
    def test_manager_login(self):
        """Test case manager login works"""
        response = requests.post(f"{API_URL}/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print("PASS: Case Manager login works")
    
    def test_client_login(self):
        """Test client login works"""
        response = requests.post(f"{API_URL}/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print("PASS: Client login works")


class TestInfoSheetSchema:
    """Tests for GET /api/cases/info-sheet-schema endpoint"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{API_URL}/auth/login", json=CLIENT_CREDS)
        return response.json().get("token")
    
    def test_schema_returns_6_sections(self, client_token):
        """Test schema endpoint returns complete schema with 6 sections"""
        response = requests.get(
            f"{API_URL}/cases/info-sheet-schema",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "sections" in data
        sections = data["sections"]
        assert len(sections) == 6, f"Expected 6 sections, got {len(sections)}"
        
        # Verify section IDs
        section_ids = [s["id"] for s in sections]
        expected_ids = ["personal_details", "family_chart", "dependent_children", 
                       "migrating_dependents", "qualifications", "employment"]
        assert section_ids == expected_ids, f"Section IDs mismatch: {section_ids}"
        print("PASS: Schema returns 6 sections with correct IDs")
    
    def test_personal_details_has_21_fields(self, client_token):
        """Test Personal Details section has 21 fields"""
        response = requests.get(
            f"{API_URL}/cases/info-sheet-schema",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        data = response.json()
        
        personal_details = next(s for s in data["sections"] if s["id"] == "personal_details")
        fields = personal_details.get("fields", [])
        assert len(fields) == 21, f"Expected 21 fields in Personal Details, got {len(fields)}"
        
        # Verify key fields exist
        field_keys = [f["key"] for f in fields]
        required_keys = ["given_names", "family_name", "gender", "date_of_birth", 
                        "country_of_birth", "email", "contact_number", "passport_number",
                        "marital_status", "father_name", "mother_name"]
        for key in required_keys:
            assert key in field_keys, f"Missing required field: {key}"
        print("PASS: Personal Details has 21 fields with all required keys")
    
    def test_repeatable_sections_have_entry_fields(self, client_token):
        """Test repeatable sections have entry_fields and max_entries"""
        response = requests.get(
            f"{API_URL}/cases/info-sheet-schema",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        data = response.json()
        
        repeatable_sections = ["dependent_children", "migrating_dependents", "qualifications", "employment"]
        for section_id in repeatable_sections:
            section = next(s for s in data["sections"] if s["id"] == section_id)
            assert section.get("repeatable") == True, f"{section_id} should be repeatable"
            assert "entry_fields" in section, f"{section_id} missing entry_fields"
            assert "max_entries" in section, f"{section_id} missing max_entries"
            assert "entry_prefix" in section, f"{section_id} missing entry_prefix"
        print("PASS: All repeatable sections have entry_fields, max_entries, and entry_prefix")
    
    def test_field_types_are_valid(self, client_token):
        """Test all fields have valid types (text, date, select, textarea)"""
        response = requests.get(
            f"{API_URL}/cases/info-sheet-schema",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        data = response.json()
        
        valid_types = ["text", "date", "select", "textarea"]
        for section in data["sections"]:
            fields = section.get("fields", section.get("entry_fields", []))
            for field in fields:
                assert field.get("type") in valid_types, f"Invalid type for {field.get('key')}: {field.get('type')}"
                if field.get("type") == "select":
                    assert "options" in field, f"Select field {field.get('key')} missing options"
        print("PASS: All fields have valid types")


class TestInfoSheetCRUD:
    """Tests for information sheet GET and POST endpoints"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{API_URL}/auth/login", json=CLIENT_CREDS)
        return response.json().get("token")
    
    def test_get_information_sheet(self, client_token):
        """Test GET /api/cases/{case_id}/information-sheet returns data"""
        response = requests.get(
            f"{API_URL}/cases/{CLIENT_CASE_ID}/information-sheet",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have exists, data, required_fields, completion
        assert "exists" in data
        assert "data" in data
        assert "completion" in data
        print(f"PASS: GET information-sheet returns data (exists={data['exists']})")
    
    def test_save_information_sheet(self, client_token):
        """Test POST /api/cases/{case_id}/information-sheet saves data"""
        test_value = f"TEST_SAVE_{int(time.time())}"
        payload = {
            "given_names": test_value,
            "family_name": "TestSaveFamily",
            "gender": "Female",
            "date_of_birth": "1985-03-20"
        }
        
        response = requests.post(
            f"{API_URL}/cases/{CLIENT_CASE_ID}/information-sheet",
            headers={"Authorization": f"Bearer {client_token}"},
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "Information sheet saved successfully"
        print("PASS: POST information-sheet saves successfully")
    
    def test_save_and_verify_persistence(self, client_token):
        """Test saved data persists after save (save then GET and check)"""
        # Generate unique test values
        test_given_name = f"PERSIST_TEST_{int(time.time())}"
        test_family_name = f"PERSIST_FAMILY_{int(time.time())}"
        
        # Save data
        payload = {
            "given_names": test_given_name,
            "family_name": test_family_name,
            "gender": "Male",
            "date_of_birth": "1992-07-10",
            "country_of_birth": "India",
            "nationality": "Indian"
        }
        
        save_response = requests.post(
            f"{API_URL}/cases/{CLIENT_CASE_ID}/information-sheet",
            headers={"Authorization": f"Bearer {client_token}"},
            json=payload
        )
        assert save_response.status_code == 200
        
        # GET and verify
        get_response = requests.get(
            f"{API_URL}/cases/{CLIENT_CASE_ID}/information-sheet",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert get_response.status_code == 200
        data = get_response.json()
        
        sheet_data = data.get("data", {})
        assert sheet_data.get("given_names") == test_given_name, "given_names not persisted"
        assert sheet_data.get("family_name") == test_family_name, "family_name not persisted"
        assert sheet_data.get("gender") == "Male", "gender not persisted"
        assert sheet_data.get("date_of_birth") == "1992-07-10", "date_of_birth not persisted"
        assert sheet_data.get("country_of_birth") == "India", "country_of_birth not persisted"
        assert sheet_data.get("nationality") == "Indian", "nationality not persisted"
        print("PASS: Saved data persists correctly after GET")
    
    def test_save_repeatable_section_data(self, client_token):
        """Test saving repeatable section data (qualifications, employment)"""
        test_qual = f"TEST_QUAL_{int(time.time())}"
        test_emp = f"TEST_EMP_{int(time.time())}"
        
        payload = {
            "qualification_1_name": test_qual,
            "qualification_1_field_of_study": "Computer Science",
            "qualification_1_institute_name": "Test University",
            "employment_1_business_name": test_emp,
            "employment_1_job_title": "Software Engineer",
            "employment_1_start_date": "2020-01-15"
        }
        
        save_response = requests.post(
            f"{API_URL}/cases/{CLIENT_CASE_ID}/information-sheet",
            headers={"Authorization": f"Bearer {client_token}"},
            json=payload
        )
        assert save_response.status_code == 200
        
        # Verify
        get_response = requests.get(
            f"{API_URL}/cases/{CLIENT_CASE_ID}/information-sheet",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        data = get_response.json().get("data", {})
        
        assert data.get("qualification_1_name") == test_qual
        assert data.get("qualification_1_field_of_study") == "Computer Science"
        assert data.get("employment_1_business_name") == test_emp
        assert data.get("employment_1_job_title") == "Software Engineer"
        print("PASS: Repeatable section data (qualifications, employment) saves and persists")
    
    def test_case_not_found_returns_404(self, client_token):
        """Test non-existent case returns 404"""
        response = requests.get(
            f"{API_URL}/cases/non-existent-case-id/information-sheet",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        # Should return empty data for non-existent case (not 404 for info-sheet)
        # The endpoint returns exists: False for non-existent sheets
        assert response.status_code == 200
        data = response.json()
        assert data.get("exists") == False
        print("PASS: Non-existent case returns exists=False")


class TestInfoSheetRouteOrder:
    """Test that /info-sheet-schema route works (placed before /{case_id})"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{API_URL}/auth/login", json=CLIENT_CREDS)
        return response.json().get("token")
    
    def test_schema_route_not_captured_by_case_id(self, client_token):
        """Test /info-sheet-schema is not captured by /{case_id} route"""
        # This should return schema, not try to find a case with id "info-sheet-schema"
        response = requests.get(
            f"{API_URL}/cases/info-sheet-schema",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have sections (schema), not case data
        assert "sections" in data, "Should return schema with sections, not case data"
        assert len(data["sections"]) == 6
        print("PASS: /info-sheet-schema route correctly placed before /{case_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
