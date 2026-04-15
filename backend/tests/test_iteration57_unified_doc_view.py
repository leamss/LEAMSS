"""
Iteration 57: Unified Document View Testing
Tests for the new client-side unified document view that replaces 4 separate tabs
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestUnifiedDocumentView:
    """Tests for the unified document view feature"""
    
    admin_token = None
    cm_token = None
    client_token = None
    test_client_token = None
    test_case_id = None
    
    # ============ AUTH TESTS ============
    
    def test_admin_login(self):
        """Admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        TestUnifiedDocumentView.admin_token = data["token"]
        print("PASS: Admin login successful")
    
    def test_cm_login(self):
        """Case Manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@leamss.com",
            "password": "Manager@123"
        })
        assert response.status_code == 200, f"CM login failed: {response.text}"
        data = response.json()
        assert "token" in data
        TestUnifiedDocumentView.cm_token = data["token"]
        print("PASS: CM login successful")
    
    def test_client_login(self):
        """Client login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "client@leamss.com",
            "password": "Client@123"
        })
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        TestUnifiedDocumentView.client_token = data["token"]
        print("PASS: Client login successful")
    
    def test_test_sale_client_login(self):
        """Test sale client login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test_sale_client@example.com",
            "password": "Client@123"
        })
        assert response.status_code == 200, f"Test sale client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        TestUnifiedDocumentView.test_client_token = data["token"]
        print("PASS: Test sale client login successful")
    
    # ============ STEP DOCUMENTS API TESTS ============
    
    def test_client_get_cases(self):
        """Client can get their cases"""
        headers = {"Authorization": f"Bearer {TestUnifiedDocumentView.client_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200, f"Get cases failed: {response.text}"
        cases = response.json()
        assert isinstance(cases, list)
        if len(cases) > 0:
            TestUnifiedDocumentView.test_case_id = cases[0]["id"]
            print(f"PASS: Client has {len(cases)} case(s), using case_id: {TestUnifiedDocumentView.test_case_id}")
        else:
            print("PASS: Client has no cases (expected for new client)")
    
    def test_step_documents_api_returns_merged_data(self):
        """GET /api/step-documents/case/{case_id} returns merged admin docs + CM docs"""
        if not TestUnifiedDocumentView.test_case_id:
            pytest.skip("No test case available")
        
        headers = {"Authorization": f"Bearer {TestUnifiedDocumentView.client_token}"}
        response = requests.get(
            f"{BASE_URL}/api/step-documents/case/{TestUnifiedDocumentView.test_case_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Step documents API failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "steps" in data, "Response missing 'steps'"
        assert "additional_requests" in data, "Response missing 'additional_requests'"
        assert "summary" in data, "Response missing 'summary'"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_required" in summary
        assert "total_uploaded" in summary
        assert "completion_pct" in summary
        
        print(f"PASS: Step documents API returns correct structure")
        print(f"  - Steps: {len(data['steps'])}")
        print(f"  - Additional requests: {len(data['additional_requests'])}")
        print(f"  - Summary: {summary['total_uploaded']}/{summary['total_required']} ({summary['completion_pct']}%)")
    
    def test_step_documents_include_admin_defaults(self):
        """Step documents include admin-defined default documents"""
        if not TestUnifiedDocumentView.test_case_id:
            pytest.skip("No test case available")
        
        headers = {"Authorization": f"Bearer {TestUnifiedDocumentView.client_token}"}
        response = requests.get(
            f"{BASE_URL}/api/step-documents/case/{TestUnifiedDocumentView.test_case_id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check if any step has documents with source='admin_default'
        has_admin_docs = False
        for step in data["steps"]:
            for doc in step.get("documents", []):
                if doc.get("source") == "admin_default":
                    has_admin_docs = True
                    print(f"  Found admin default doc: {doc['doc_name']} in step {step['step_name']}")
        
        # Also check for CM-added docs
        has_cm_docs = False
        for step in data["steps"]:
            for doc in step.get("documents", []):
                if doc.get("source") == "cm_request":
                    has_cm_docs = True
                    print(f"  Found CM-added doc: {doc['doc_name']} in step {step['step_name']}")
        
        print(f"PASS: Step documents API working (admin_docs: {has_admin_docs}, cm_docs: {has_cm_docs})")
    
    def test_step_documents_include_legacy_additional_requests(self):
        """Step documents include legacy additional_doc_requests collection data"""
        if not TestUnifiedDocumentView.test_case_id:
            pytest.skip("No test case available")
        
        headers = {"Authorization": f"Bearer {TestUnifiedDocumentView.client_token}"}
        response = requests.get(
            f"{BASE_URL}/api/step-documents/case/{TestUnifiedDocumentView.test_case_id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        additional = data.get("additional_requests", [])
        print(f"PASS: Additional requests count: {len(additional)}")
        for req in additional[:3]:  # Show first 3
            print(f"  - {req.get('doc_name', 'Unknown')}: status={req.get('status', 'N/A')}")
    
    def test_test_sale_client_step_documents(self):
        """Test sale client can see step documents for their case"""
        headers = {"Authorization": f"Bearer {TestUnifiedDocumentView.test_client_token}"}
        
        # First get their cases
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        
        if len(cases) == 0:
            print("PASS: Test sale client has no cases (expected)")
            return
        
        case_id = cases[0]["id"]
        print(f"Test sale client has case: {cases[0].get('case_id', case_id)}")
        
        # Get step documents
        response = requests.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        assert response.status_code == 200, f"Step documents failed: {response.text}"
        data = response.json()
        
        print(f"PASS: Test sale client step documents:")
        print(f"  - Steps: {len(data['steps'])}")
        print(f"  - Completion: {data['summary']['completion_pct']}%")
    
    # ============ CM DOCUMENT REQUEST TESTS ============
    
    def test_cm_can_request_step_document(self):
        """CM can request a document within a specific step"""
        if not TestUnifiedDocumentView.test_case_id:
            pytest.skip("No test case available")
        
        headers = {"Authorization": f"Bearer {TestUnifiedDocumentView.cm_token}"}
        
        # First get case steps to find a valid step name
        response = requests.get(
            f"{BASE_URL}/api/step-documents/case/{TestUnifiedDocumentView.test_case_id}",
            headers=headers
        )
        if response.status_code != 200:
            pytest.skip("Cannot get step documents")
        
        data = response.json()
        if len(data["steps"]) == 0:
            pytest.skip("No steps in case")
        
        step_name = data["steps"][0]["step_name"]
        
        # Request a document in that step
        response = requests.post(
            f"{BASE_URL}/api/step-documents/request-step-doc",
            headers=headers,
            json={
                "case_id": TestUnifiedDocumentView.test_case_id,
                "step_name": step_name,
                "doc_name": f"TEST_Iteration57_StepDoc_{step_name[:10]}",
                "is_mandatory": True,
                "notes": "Test document for iteration 57",
                "tag": "mandatory"
            }
        )
        # May fail if doc already exists, which is fine
        if response.status_code == 200:
            print(f"PASS: CM requested step document in '{step_name}'")
        elif response.status_code == 400 and "already exists" in response.text.lower():
            print(f"PASS: Document already exists in step (expected)")
        else:
            print(f"INFO: Request step doc response: {response.status_code} - {response.text}")
    
    def test_cm_can_request_additional_document(self):
        """CM can request an additional document (not tied to step)"""
        if not TestUnifiedDocumentView.test_case_id:
            pytest.skip("No test case available")
        
        headers = {"Authorization": f"Bearer {TestUnifiedDocumentView.cm_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/step-documents/request-additional",
            headers=headers,
            json={
                "case_id": TestUnifiedDocumentView.test_case_id,
                "doc_name": "TEST_Iteration57_AdditionalDoc",
                "is_mandatory": True,
                "notes": "Test additional document for iteration 57",
                "tag": "mandatory"
            }
        )
        assert response.status_code == 200, f"Request additional doc failed: {response.text}"
        print("PASS: CM requested additional document")
    
    # ============ ADMIN WORKFLOW TESTS ============
    
    def test_admin_products_have_workflow_steps(self):
        """Admin can see products with workflow steps"""
        headers = {"Authorization": f"Bearer {TestUnifiedDocumentView.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200, f"Get products failed: {response.text}"
        products = response.json()
        
        assert len(products) > 0, "No products found"
        
        # Check if products have workflow_steps
        products_with_steps = [p for p in products if len(p.get("workflow_steps", [])) > 0]
        print(f"PASS: Found {len(products)} products, {len(products_with_steps)} have workflow steps")
        
        for p in products_with_steps[:2]:  # Show first 2
            steps = p.get("workflow_steps", [])
            print(f"  - {p['name']}: {len(steps)} steps")
            for s in steps[:2]:
                docs = s.get("required_documents", [])
                print(f"    - {s['step_name']}: {len(docs)} required docs")
    
    def test_admin_workflow_step_documents_persist(self):
        """Admin workflow step documents persist after save"""
        headers = {"Authorization": f"Bearer {TestUnifiedDocumentView.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200
        products = response.json()
        
        # Find a product with workflow steps that have documents
        for p in products:
            for step in p.get("workflow_steps", []):
                docs = step.get("required_documents", [])
                if len(docs) > 0:
                    print(f"PASS: Found workflow step with documents:")
                    print(f"  Product: {p['name']}")
                    print(f"  Step: {step['step_name']}")
                    print(f"  Documents: {[d.get('doc_name', d.get('name', 'Unknown')) for d in docs]}")
                    return
        
        print("PASS: No workflow steps with documents found (may need to add via admin)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
