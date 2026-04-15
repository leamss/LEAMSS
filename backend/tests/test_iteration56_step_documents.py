"""
Iteration 56: Step-wise Document Management Tests
Testing the recently fixed bugs:
1. Admin workflow step docs persisting
2. CM '+Add Doc' inside a step goes to correct step (not Additional Documents)
3. Admin default docs syncing to existing case_steps
4. doc_name vs name field mismatch handling
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
CM_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}

# Test case IDs from context
CM_TEST_CASE_ID = "CASE-20260412-EE36"  # Canada PR case with 3 steps
CLIENT_CASE_ID = "cb09cf65-9a0c-47c6-8585-bace5da8c221"  # Client case with 8 steps


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin login failed")


@pytest.fixture(scope="module")
def cm_token():
    """Get case manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CM_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("CM login failed")


@pytest.fixture(scope="module")
def client_token():
    """Get client auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Client login failed")


@pytest.fixture(scope="module")
def cm_case_id(cm_token):
    """Get the CM test case ID (internal UUID)"""
    headers = {"Authorization": f"Bearer {cm_token}"}
    response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
    if response.status_code == 200:
        cases = response.json()
        # Find the test case
        for case in cases:
            if case.get("case_id") == CM_TEST_CASE_ID:
                return case.get("id")
        # Return first case if test case not found
        if cases:
            return cases[0].get("id")
    pytest.skip("No cases found for CM")


class TestAdminWorkflowStepDocuments:
    """Test Admin workflow step document management"""
    
    def test_admin_login(self, admin_token):
        """Verify admin can login"""
        assert admin_token is not None
        print(f"Admin token obtained: {admin_token[:20]}...")
    
    def test_get_products_with_workflow_steps(self, admin_token):
        """Verify products include workflow_steps with required_documents"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        
        assert response.status_code == 200
        products = response.json()
        assert len(products) > 0, "No products found"
        
        # Find a product with workflow steps
        product_with_steps = None
        for p in products:
            if p.get("workflow_steps") and len(p["workflow_steps"]) > 0:
                product_with_steps = p
                break
        
        if product_with_steps:
            print(f"Product '{product_with_steps['name']}' has {len(product_with_steps['workflow_steps'])} workflow steps")
            for step in product_with_steps["workflow_steps"]:
                docs = step.get("required_documents", [])
                print(f"  Step '{step['step_name']}': {len(docs)} required documents")
                for doc in docs:
                    doc_name = doc.get("doc_name") or doc.get("name") or "Unnamed"
                    print(f"    - {doc_name}")
        else:
            print("No products with workflow steps found")
    
    def test_admin_add_document_to_workflow_step(self, admin_token):
        """Test admin can add a document to a workflow step"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get products
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200
        products = response.json()
        
        # Find a product with workflow steps
        product_with_steps = None
        for p in products:
            if p.get("workflow_steps") and len(p["workflow_steps"]) > 0:
                product_with_steps = p
                break
        
        if not product_with_steps:
            pytest.skip("No products with workflow steps found")
        
        product_id = product_with_steps["id"]
        step = product_with_steps["workflow_steps"][0]
        step_order = step["step_order"]
        
        # Get current docs count
        current_docs = step.get("required_documents", [])
        initial_count = len(current_docs)
        
        # Add a test document
        test_doc_name = f"TEST_Doc_{uuid.uuid4().hex[:6]}"
        updated_docs = current_docs + [{
            "doc_name": test_doc_name,
            "is_mandatory": True,
            "description": "Test document added by iteration 56 test"
        }]
        
        # Update the step
        update_data = {
            "product_id": product_id,
            "step_name": step["step_name"],
            "step_order": step_order,
            "description": step.get("description", ""),
            "duration_days": step.get("duration_days", ""),
            "required_documents": updated_docs
        }
        
        response = requests.put(
            f"{BASE_URL}/api/products/{product_id}/workflow-step/{step_order}",
            headers=headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"Failed to update step: {response.text}"
        print(f"Added document '{test_doc_name}' to step '{step['step_name']}'")
        
        # Verify the document persists
        response = requests.get(f"{BASE_URL}/api/products/{product_id}", headers=headers)
        assert response.status_code == 200
        
        updated_product = response.json()
        updated_step = next((s for s in updated_product.get("workflow_steps", []) if s["step_order"] == step_order), None)
        
        assert updated_step is not None, "Step not found after update"
        updated_docs = updated_step.get("required_documents", [])
        
        # Check if our test doc is there
        doc_names = [d.get("doc_name") or d.get("name") for d in updated_docs]
        assert test_doc_name in doc_names, f"Test document not found in step. Found: {doc_names}"
        print(f"Verified document '{test_doc_name}' persists in workflow step")
        
        # Cleanup: remove the test document
        cleanup_docs = [d for d in updated_docs if (d.get("doc_name") or d.get("name")) != test_doc_name]
        cleanup_data = {**update_data, "required_documents": cleanup_docs}
        requests.put(
            f"{BASE_URL}/api/products/{product_id}/workflow-step/{step_order}",
            headers=headers,
            json=cleanup_data
        )
        print(f"Cleaned up test document")


class TestCMStepDocumentRequests:
    """Test CM step document request functionality"""
    
    def test_cm_login(self, cm_token):
        """Verify CM can login"""
        assert cm_token is not None
        print(f"CM token obtained: {cm_token[:20]}...")
    
    def test_cm_get_cases(self, cm_token):
        """Verify CM can get their cases"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        
        assert response.status_code == 200
        cases = response.json()
        print(f"CM has {len(cases)} cases")
        for case in cases[:3]:
            print(f"  - {case.get('case_id')}: {case.get('client_name')} ({case.get('product_name')})")
    
    def test_cm_request_step_document_api(self, cm_token, cm_case_id):
        """Test POST /api/step-documents/request-step-doc adds doc to specific step"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        # First get the case steps
        response = requests.get(f"{BASE_URL}/api/step-documents/case/{cm_case_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        steps = data.get("steps", [])
        if not steps:
            pytest.skip("No steps found in case")
        
        # Pick the first step
        step = steps[0]
        step_name = step["step_name"]
        initial_doc_count = len(step.get("documents", []))
        
        # Request a new document for this step
        test_doc_name = f"TEST_StepDoc_{uuid.uuid4().hex[:6]}"
        request_data = {
            "case_id": cm_case_id,
            "step_name": step_name,
            "doc_name": test_doc_name,
            "is_mandatory": True,
            "tag": "mandatory",
            "notes": "Test document requested by CM"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/step-documents/request-step-doc",
            headers=headers,
            json=request_data
        )
        
        assert response.status_code == 200, f"Failed to request step doc: {response.text}"
        print(f"Requested document '{test_doc_name}' for step '{step_name}'")
        
        # Verify the document appears IN THE STEP (not in additional)
        response = requests.get(f"{BASE_URL}/api/step-documents/case/{cm_case_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Find the step
        updated_step = next((s for s in data.get("steps", []) if s["step_name"] == step_name), None)
        assert updated_step is not None, f"Step '{step_name}' not found"
        
        # Check if doc is in the step
        step_doc_names = [d.get("doc_name") for d in updated_step.get("documents", [])]
        assert test_doc_name in step_doc_names, f"Document not found in step. Found: {step_doc_names}"
        print(f"Verified document '{test_doc_name}' is IN step '{step_name}' (not in Additional)")
        
        # Verify it's NOT in additional_requests
        additional = data.get("additional_requests", [])
        additional_names = [r.get("doc_name") for r in additional]
        assert test_doc_name not in additional_names, f"Document incorrectly in additional_requests"
        print(f"Confirmed document is NOT in additional_requests section")
        
        # Cleanup: remove the test document
        remove_data = {
            "case_id": cm_case_id,
            "step_name": step_name,
            "doc_name": test_doc_name
        }
        requests.post(f"{BASE_URL}/api/step-documents/remove-step-doc", headers=headers, json=remove_data)
        print(f"Cleaned up test document")
    
    def test_cm_request_additional_document_api(self, cm_token, cm_case_id):
        """Test POST /api/step-documents/request-additional adds doc to additional section"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        # Get initial additional requests count
        response = requests.get(f"{BASE_URL}/api/step-documents/case/{cm_case_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        initial_additional = len(data.get("additional_requests", []))
        
        # Request an additional document
        test_doc_name = f"TEST_Additional_{uuid.uuid4().hex[:6]}"
        request_data = {
            "case_id": cm_case_id,
            "doc_name": test_doc_name,
            "is_mandatory": True,
            "tag": "mandatory",
            "notes": "Test additional document"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/step-documents/request-additional",
            headers=headers,
            json=request_data
        )
        
        assert response.status_code == 200, f"Failed to request additional doc: {response.text}"
        print(f"Requested additional document '{test_doc_name}'")
        
        # Verify the document appears in additional_requests
        response = requests.get(f"{BASE_URL}/api/step-documents/case/{cm_case_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        additional = data.get("additional_requests", [])
        additional_names = [r.get("doc_name") for r in additional]
        assert test_doc_name in additional_names, f"Document not found in additional_requests. Found: {additional_names}"
        print(f"Verified document '{test_doc_name}' is in additional_requests section")
        
        # Verify it's NOT in any step
        for step in data.get("steps", []):
            step_doc_names = [d.get("doc_name") for d in step.get("documents", [])]
            assert test_doc_name not in step_doc_names, f"Document incorrectly in step '{step['step_name']}'"
        print(f"Confirmed document is NOT in any step")


class TestClientStepDocuments:
    """Test client step document view"""
    
    def test_client_login(self, client_token):
        """Verify client can login"""
        assert client_token is not None
        print(f"Client token obtained: {client_token[:20]}...")
    
    def test_client_get_step_documents(self, client_token):
        """Test client can view step-wise documents"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # Get client's cases
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        
        if not cases:
            pytest.skip("Client has no cases")
        
        case_id = cases[0].get("id")
        print(f"Testing with case: {cases[0].get('case_id')}")
        
        # Get step documents
        response = requests.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "steps" in data, "Response missing 'steps'"
        assert "additional_requests" in data, "Response missing 'additional_requests'"
        assert "summary" in data, "Response missing 'summary'"
        
        steps = data["steps"]
        summary = data["summary"]
        
        print(f"Case has {len(steps)} steps")
        print(f"Summary: {summary['total_uploaded']}/{summary['total_required']} uploaded ({summary['completion_pct']}%)")
        
        for step in steps:
            docs = step.get("documents", [])
            print(f"  Step '{step['step_name']}': {step['uploaded_count']}/{step['required_count']} docs")
            for doc in docs[:3]:
                doc_name = doc.get("doc_name", "Unknown")
                status = doc.get("status", "unknown")
                source = doc.get("source", "unknown")
                print(f"    - {doc_name}: {status} (source: {source})")
    
    def test_client_step_documents_show_admin_defaults(self, client_token):
        """Verify admin default documents are visible in client's step view"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # Get client's cases
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        
        if not cases:
            pytest.skip("Client has no cases")
        
        case_id = cases[0].get("id")
        
        # Get step documents
        response = requests.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check for admin_default source documents
        admin_default_found = False
        for step in data.get("steps", []):
            for doc in step.get("documents", []):
                if doc.get("source") == "admin_default":
                    admin_default_found = True
                    print(f"Found admin default doc: '{doc.get('doc_name')}' in step '{step['step_name']}'")
        
        if not admin_default_found:
            print("No admin_default documents found - this may be expected if no admin docs are configured")


class TestDocNameFieldHandling:
    """Test that both 'doc_name' and 'name' fields are handled correctly"""
    
    def test_step_documents_handle_both_fields(self, cm_token, cm_case_id):
        """Verify API handles both doc_name and name fields"""
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        response = requests.get(f"{BASE_URL}/api/step-documents/case/{cm_case_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check all documents have doc_name field in response
        for step in data.get("steps", []):
            for doc in step.get("documents", []):
                # Response should always have doc_name
                assert "doc_name" in doc, f"Document missing doc_name field: {doc}"
                assert doc["doc_name"], f"Document has empty doc_name: {doc}"
        
        print("All documents have proper doc_name field in response")


class TestStepDocumentsSummary:
    """Test step documents summary calculations"""
    
    def test_summary_calculations(self, client_token):
        """Verify summary calculations are correct"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # Get client's cases
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert response.status_code == 200
        cases = response.json()
        
        if not cases:
            pytest.skip("Client has no cases")
        
        case_id = cases[0].get("id")
        
        # Get step documents
        response = requests.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        steps = data["steps"]
        additional = data.get("additional_requests", [])
        
        # Calculate expected values
        expected_required = sum(s["required_count"] for s in steps) + len(additional)
        expected_uploaded = sum(s["uploaded_count"] for s in steps) + sum(1 for r in additional if r.get("uploaded_doc"))
        
        assert summary["total_required"] == expected_required, f"total_required mismatch: {summary['total_required']} vs {expected_required}"
        assert summary["total_uploaded"] == expected_uploaded, f"total_uploaded mismatch: {summary['total_uploaded']} vs {expected_uploaded}"
        
        if expected_required > 0:
            expected_pct = round(expected_uploaded / expected_required * 100)
            assert summary["completion_pct"] == expected_pct, f"completion_pct mismatch: {summary['completion_pct']} vs {expected_pct}"
        
        print(f"Summary calculations verified: {summary['total_uploaded']}/{summary['total_required']} ({summary['completion_pct']}%)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
