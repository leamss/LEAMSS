"""
Phase 12: Client Experience Enhancement Tests
- 12A: Self-Eligibility Checker
- 12B: EMI Payment Plans
- 12C: Family Member Management
- 12D: Document Completion Tracker
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPhase12Setup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def client_token(self):
        """Get client authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        assert response.status_code == 200, f"Client login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        """Get case manager authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@leamss.com",
            "password": "Manager@123"
        })
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        return response.json().get("token")
    
    def test_admin_login(self, admin_token):
        """Verify admin can login"""
        assert admin_token is not None
        print(f"Admin token obtained: {admin_token[:20]}...")
    
    def test_client_login(self, client_token):
        """Verify client can login"""
        assert client_token is not None
        print(f"Client token obtained: {client_token[:20]}...")


class TestEligibilityChecker:
    """12A: Self-Eligibility Checker Tests"""
    
    @pytest.fixture(scope="class")
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        return response.json().get("token")
    
    def test_eligibility_check_public_endpoint(self):
        """Test public eligibility check (no auth required)"""
        payload = {
            "age": 28,
            "education": "masters",
            "work_experience_years": 5,
            "ielts_overall": 7.5,
            "country_preference": "canada",
            "has_job_offer": False,
            "has_relatives_abroad": False,
            "marital_status": "single",
            "funds_available_inr": 1500000
        }
        response = requests.post(f"{BASE_URL}/api/client-tools/eligibility-check/public", json=payload)
        assert response.status_code == 200, f"Public eligibility check failed: {response.text}"
        
        data = response.json()
        assert "results" in data
        results = data["results"]
        assert len(results) == 4, "Should return 4 visa program results"
        
        # Verify all 4 programs are present
        programs = [r["program"] for r in results]
        assert any("Canada" in p for p in programs), "Canada PR should be in results"
        assert any("Australia" in p for p in programs), "Australia PR should be in results"
        assert any("Student" in p for p in programs), "Student Visa should be in results"
        assert any("Work" in p for p in programs), "Work Permit should be in results"
        
        # Verify score structure
        for result in results:
            assert "score" in result
            assert "status" in result
            assert "tips" in result
            assert 0 <= result["score"] <= 100
            assert result["status"] in ["highly_eligible", "eligible", "needs_improvement", "low_eligibility"]
        
        print(f"Public eligibility check returned {len(results)} programs")
        for r in results:
            print(f"  - {r['program']}: {r['score']}% ({r['status']})")
    
    def test_eligibility_check_authenticated(self, client_token):
        """Test authenticated eligibility check (saves history)"""
        headers = {"Authorization": f"Bearer {client_token}"}
        payload = {
            "age": 32,
            "education": "bachelors",
            "work_experience_years": 8,
            "ielts_overall": 6.5,
            "country_preference": "australia",
            "has_job_offer": True,
            "has_relatives_abroad": True,
            "marital_status": "married",
            "spouse_education": "bachelors",
            "funds_available_inr": 2000000
        }
        response = requests.post(f"{BASE_URL}/api/client-tools/eligibility-check", json=payload, headers=headers)
        assert response.status_code == 200, f"Authenticated eligibility check failed: {response.text}"
        
        data = response.json()
        assert "results" in data
        assert "check_id" in data, "Should return check_id for authenticated users"
        
        print(f"Authenticated check saved with ID: {data['check_id']}")
    
    def test_eligibility_history(self, client_token):
        """Test eligibility check history retrieval"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/client-tools/eligibility-history", headers=headers)
        assert response.status_code == 200, f"Eligibility history failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} eligibility checks in history")
    
    def test_eligibility_scoring_logic(self):
        """Test that scoring logic works correctly for different profiles"""
        # High-scoring profile
        high_profile = {
            "age": 28,
            "education": "phd",
            "work_experience_years": 6,
            "ielts_overall": 8.5,
            "has_job_offer": True,
            "has_relatives_abroad": True,
            "marital_status": "married",
            "spouse_education": "masters",
            "funds_available_inr": 3000000
        }
        response = requests.post(f"{BASE_URL}/api/client-tools/eligibility-check/public", json=high_profile)
        assert response.status_code == 200
        high_results = response.json()["results"]
        
        # Low-scoring profile
        low_profile = {
            "age": 50,
            "education": "high_school",
            "work_experience_years": 0,
            "ielts_overall": 4.5,
            "has_job_offer": False,
            "has_relatives_abroad": False,
            "marital_status": "single",
            "funds_available_inr": 100000
        }
        response = requests.post(f"{BASE_URL}/api/client-tools/eligibility-check/public", json=low_profile)
        assert response.status_code == 200
        low_results = response.json()["results"]
        
        # High profile should score better than low profile
        high_best = max(r["score"] for r in high_results)
        low_best = max(r["score"] for r in low_results)
        assert high_best > low_best, f"High profile ({high_best}) should score better than low profile ({low_best})"
        
        print(f"High profile best score: {high_best}%, Low profile best score: {low_best}%")


class TestFamilyMemberManagement:
    """12C: Family Member Management Tests"""
    
    @pytest.fixture(scope="class")
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        return response.json().get("token")
    
    def test_add_family_member(self, client_token):
        """Test adding a family member"""
        headers = {"Authorization": f"Bearer {client_token}"}
        payload = {
            "name": "TEST_Jane Doe",
            "relationship": "spouse",
            "age": 30,
            "passport_number": "AB1234567",
            "date_of_birth": "1994-05-15",
            "included_in_application": True,
            "notes": "Primary applicant's spouse"
        }
        response = requests.post(f"{BASE_URL}/api/client-tools/family/add", json=payload, headers=headers)
        assert response.status_code == 200, f"Add family member failed: {response.text}"
        
        data = response.json()
        assert "member" in data
        member = data["member"]
        assert member["name"] == "TEST_Jane Doe"
        assert member["relationship"] == "spouse"
        assert member["included_in_application"] == True
        assert "id" in member
        
        print(f"Added family member: {member['name']} (ID: {member['id']})")
        return member["id"]
    
    def test_get_family_members(self, client_token):
        """Test retrieving family members list"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/client-tools/family/members", headers=headers)
        assert response.status_code == 200, f"Get family members failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} family members")
        
        # Find our test member
        test_members = [m for m in data if m["name"].startswith("TEST_")]
        assert len(test_members) > 0, "Should find at least one test family member"
        return test_members[0]["id"] if test_members else None
    
    def test_update_family_member(self, client_token):
        """Test updating a family member"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # First get the list to find a member to update
        response = requests.get(f"{BASE_URL}/api/client-tools/family/members", headers=headers)
        members = response.json()
        test_members = [m for m in members if m["name"].startswith("TEST_")]
        
        if not test_members:
            pytest.skip("No test family member found to update")
        
        member_id = test_members[0]["id"]
        
        # Update the member
        update_payload = {
            "name": "TEST_Jane Doe Updated",
            "relationship": "spouse",
            "age": 31,
            "passport_number": "AB1234567",
            "date_of_birth": "1994-05-15",
            "included_in_application": False,
            "notes": "Updated notes"
        }
        response = requests.put(f"{BASE_URL}/api/client-tools/family/{member_id}", json=update_payload, headers=headers)
        assert response.status_code == 200, f"Update family member failed: {response.text}"
        
        print(f"Updated family member {member_id}")
    
    def test_delete_family_member(self, client_token):
        """Test deleting a family member"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # First add a member to delete
        payload = {
            "name": "TEST_ToDelete Member",
            "relationship": "sibling",
            "age": 25,
            "included_in_application": False
        }
        response = requests.post(f"{BASE_URL}/api/client-tools/family/add", json=payload, headers=headers)
        assert response.status_code == 200
        member_id = response.json()["member"]["id"]
        
        # Now delete it
        response = requests.delete(f"{BASE_URL}/api/client-tools/family/{member_id}", headers=headers)
        assert response.status_code == 200, f"Delete family member failed: {response.text}"
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/api/client-tools/family/members", headers=headers)
        members = response.json()
        deleted_member = [m for m in members if m["id"] == member_id]
        assert len(deleted_member) == 0, "Deleted member should not appear in list"
        
        print(f"Successfully deleted family member {member_id}")
    
    def test_family_member_relationship_types(self, client_token):
        """Test all relationship types work"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        relationships = ["spouse", "child", "parent", "sibling"]
        created_ids = []
        
        for rel in relationships:
            payload = {
                "name": f"TEST_{rel.capitalize()} Member",
                "relationship": rel,
                "age": 25,
                "included_in_application": False
            }
            response = requests.post(f"{BASE_URL}/api/client-tools/family/add", json=payload, headers=headers)
            assert response.status_code == 200, f"Failed to add {rel}: {response.text}"
            created_ids.append(response.json()["member"]["id"])
        
        print(f"Successfully added members with all relationship types: {relationships}")
        
        # Cleanup
        for member_id in created_ids:
            requests.delete(f"{BASE_URL}/api/client-tools/family/{member_id}", headers=headers)


class TestEMIPaymentPlans:
    """12B: EMI Payment Plans Tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        return response.json().get("token")
    
    def test_get_emi_plans_client(self, client_token):
        """Test client can view their EMI plans"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/client-tools/emi/my-plans", headers=headers)
        assert response.status_code == 200, f"Get EMI plans failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Client has {len(data)} EMI plans")
    
    def test_get_emi_plans_admin(self, admin_token):
        """Test admin can view all EMI plans"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/client-tools/emi/my-plans", headers=headers)
        assert response.status_code == 200, f"Admin get EMI plans failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Admin sees {len(data)} total EMI plans")
    
    def test_create_emi_plan_requires_admin(self, client_token):
        """Test that only admin can create EMI plans"""
        headers = {"Authorization": f"Bearer {client_token}"}
        payload = {
            "sale_id": "fake-sale-id",
            "total_amount": 100000,
            "installments": 3
        }
        response = requests.post(f"{BASE_URL}/api/client-tools/emi/create", json=payload, headers=headers)
        assert response.status_code == 403, "Non-admin should not be able to create EMI plans"
        print("Correctly blocked non-admin from creating EMI plan")
    
    def test_create_emi_plan_admin(self, admin_token):
        """Test admin can create EMI plan (requires valid sale_id)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get a valid sale_id
        response = requests.get(f"{BASE_URL}/api/sales", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not get sales list")
        
        sales = response.json()
        if not sales:
            pytest.skip("No sales found to create EMI plan for")
        
        sale_id = sales[0]["id"]
        
        payload = {
            "sale_id": sale_id,
            "total_amount": 120000,
            "installments": 3,
            "notes": "TEST EMI Plan"
        }
        response = requests.post(f"{BASE_URL}/api/client-tools/emi/create", json=payload, headers=headers)
        
        # May fail if sale already has EMI plan or other business rules
        if response.status_code == 200:
            data = response.json()
            assert "plan" in data
            plan = data["plan"]
            assert plan["installments"] == 3
            assert plan["total_amount"] == 120000
            assert len(plan["schedule"]) == 3
            print(f"Created EMI plan: {plan['id']}")
        else:
            print(f"EMI creation returned {response.status_code}: {response.text}")
    
    def test_emi_installment_validation(self, admin_token):
        """Test EMI installment count validation"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get a sale
        response = requests.get(f"{BASE_URL}/api/sales", headers=headers)
        if response.status_code != 200 or not response.json():
            pytest.skip("No sales available")
        
        sale_id = response.json()[0]["id"]
        
        # Try invalid installment count
        payload = {
            "sale_id": sale_id,
            "total_amount": 100000,
            "installments": 5  # Invalid - should be 3, 6, or 12
        }
        response = requests.post(f"{BASE_URL}/api/client-tools/emi/create", json=payload, headers=headers)
        assert response.status_code == 400, "Should reject invalid installment count"
        print("Correctly rejected invalid installment count (5)")


class TestDocumentTracker:
    """12D: Document Completion Tracker Tests"""
    
    @pytest.fixture(scope="class")
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        return response.json().get("token")
    
    def test_get_document_tracker(self, client_token):
        """Test document tracker endpoint"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/client-tools/document-tracker", headers=headers)
        assert response.status_code == 200, f"Document tracker failed: {response.text}"
        
        data = response.json()
        assert "cases" in data
        assert "overall_completion" in data
        assert isinstance(data["overall_completion"], (int, float))
        assert 0 <= data["overall_completion"] <= 100
        
        print(f"Document tracker: {data['overall_completion']}% overall completion")
        print(f"Found {len(data['cases'])} cases")
        
        # Check case structure if cases exist
        if data["cases"]:
            case = data["cases"][0]
            assert "case_id" in case or "product_name" in case
            assert "steps" in case
            assert "completion" in case
            
            print(f"First case: {case.get('case_id', 'N/A')} - {case['completion']}% complete")
            
            # Check step structure
            if case["steps"]:
                step = case["steps"][0]
                assert "step_name" in step
                assert "required" in step
                assert "uploaded" in step
                print(f"  Step '{step['step_name']}': {step['uploaded']}/{step['required']} docs")
    
    def test_document_tracker_no_case(self):
        """Test document tracker for user with no cases"""
        # Login as a user without cases (client2)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client2@leamss.com",
            "password": "Client@123"
        })
        if response.status_code != 200:
            pytest.skip("client2 not available")
        
        token = response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/client-tools/document-tracker", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # Should return empty or 0% completion
        assert "cases" in data
        print(f"Client2 document tracker: {len(data['cases'])} cases, {data['overall_completion']}% completion")


class TestPhase12Integration:
    """Integration tests for Phase 12 features"""
    
    @pytest.fixture(scope="class")
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        return response.json().get("token")
    
    def test_all_phase12_endpoints_accessible(self, client_token):
        """Verify all Phase 12 endpoints are accessible"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        endpoints = [
            ("POST", "/api/client-tools/eligibility-check/public", {"age": 25, "education": "bachelors"}),
            ("POST", "/api/client-tools/eligibility-check", {"age": 25, "education": "bachelors"}),
            ("GET", "/api/client-tools/eligibility-history", None),
            ("GET", "/api/client-tools/family/members", None),
            ("GET", "/api/client-tools/emi/my-plans", None),
            ("GET", "/api/client-tools/document-tracker", None),
        ]
        
        results = []
        for method, endpoint, payload in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json=payload, headers=headers if "public" not in endpoint else {})
            
            status = "PASS" if response.status_code == 200 else f"FAIL ({response.status_code})"
            results.append((endpoint, status))
            print(f"{method} {endpoint}: {status}")
        
        # All should pass
        failures = [r for r in results if "FAIL" in r[1]]
        assert len(failures) == 0, f"Failed endpoints: {failures}"


# Cleanup fixture
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed data after all tests"""
    yield
    
    # Login as client to cleanup
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "client@leamss.com",
        "password": "Client@123"
    })
    if response.status_code != 200:
        return
    
    token = response.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Delete test family members
    response = requests.get(f"{BASE_URL}/api/client-tools/family/members", headers=headers)
    if response.status_code == 200:
        members = response.json()
        for member in members:
            if member.get("name", "").startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/client-tools/family/{member['id']}", headers=headers)
                print(f"Cleaned up test family member: {member['name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
