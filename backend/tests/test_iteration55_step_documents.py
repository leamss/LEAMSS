"""
Iteration 55: Step-wise Document Management Tests
Tests for:
1. GET /api/step-documents/case/{id} - Returns steps with documents structure
2. POST /api/step-documents/request-step-doc - CM adds doc to step
3. POST /api/step-documents/request-additional - CM adds doc to separate section
4. POST /api/step-documents/remove-step-doc - CM removes CM-added doc (not admin docs)
5. PUT /api/products/{id}/workflow-step/{order} - Admin workflow step docs persist
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
CM_EMAIL = "manager@leamss.com"
CM_PASSWORD = "Manager@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASSWORD = "Client@123"


class TestStepDocumentsAPI:
    """Test step-wise document management APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_token(self, email, password):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_client_case_id(self, token):
        """Get client's case ID"""
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        if response.status_code == 200 and response.json():
            return response.json()[0].get("id")
        return None
    
    # ============ GET /api/step-documents/case/{id} Tests ============
    
    def test_get_stepwise_documents_client(self):
        """Test client can get step-wise documents for their case"""
        token = self.get_token(CLIENT_EMAIL, CLIENT_PASSWORD)
        assert token, "Client login failed"
        
        case_id = self.get_client_case_id(token)
        assert case_id, "No case found for client"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "steps" in data, "Response should have 'steps' field"
        assert "additional_requests" in data, "Response should have 'additional_requests' field"
        assert "summary" in data, "Response should have 'summary' field"
        
        print(f"SUCCESS: Client got step-wise documents - {len(data['steps'])} steps")
        
    def test_get_stepwise_documents_has_step_structure(self):
        """Test step-wise documents response has correct step structure"""
        token = self.get_token(CLIENT_EMAIL, CLIENT_PASSWORD)
        case_id = self.get_client_case_id(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["steps"]:
            step = data["steps"][0]
            # Verify step structure
            assert "step_name" in step, "Step should have step_name"
            assert "step_order" in step, "Step should have step_order"
            assert "required_count" in step, "Step should have required_count"
            assert "uploaded_count" in step, "Step should have uploaded_count"
            assert "documents" in step, "Step should have documents array"
            
            print(f"SUCCESS: Step structure verified - Step 1: {step['step_name']}, {step['required_count']} required docs")
            
    def test_get_stepwise_documents_has_summary(self):
        """Test step-wise documents response has summary with completion percentage"""
        token = self.get_token(CLIENT_EMAIL, CLIENT_PASSWORD)
        case_id = self.get_client_case_id(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        summary = data.get("summary", {})
        assert "total_required" in summary, "Summary should have total_required"
        assert "total_uploaded" in summary, "Summary should have total_uploaded"
        assert "completion_pct" in summary, "Summary should have completion_pct"
        
        print(f"SUCCESS: Summary verified - {summary['total_uploaded']}/{summary['total_required']} ({summary['completion_pct']}%)")
        
    def test_get_stepwise_documents_cm(self):
        """Test CM can get step-wise documents for any case"""
        cm_token = self.get_token(CM_EMAIL, CM_PASSWORD)
        assert cm_token, "CM login failed"
        
        # Get CM's cases
        headers = {"Authorization": f"Bearer {cm_token}"}
        cases_response = self.session.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        assert cases_response.status_code == 200
        
        cases = cases_response.json()
        if not cases:
            pytest.skip("No cases assigned to CM")
            
        case_id = cases[0]["id"]
        
        response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        assert response.status_code == 200, f"CM should access case step docs: {response.text}"
        
        print(f"SUCCESS: CM can access step-wise documents for case {case_id}")
        
    # ============ POST /api/step-documents/request-step-doc Tests ============
    
    def test_cm_request_step_document(self):
        """Test CM can request a document for a specific step"""
        cm_token = self.get_token(CM_EMAIL, CM_PASSWORD)
        assert cm_token, "CM login failed"
        
        # Get CM's cases
        headers = {"Authorization": f"Bearer {cm_token}"}
        cases_response = self.session.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases assigned to CM")
            
        case_id = cases[0]["id"]
        
        # Get steps for this case
        step_docs_response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        steps = step_docs_response.json().get("steps", [])
        
        if not steps:
            pytest.skip("No steps found for case")
            
        step_name = steps[0]["step_name"]
        test_doc_name = f"TEST_CM_Doc_{uuid.uuid4().hex[:6]}"
        
        # Request document for step
        response = self.session.post(f"{BASE_URL}/api/step-documents/request-step-doc", 
            headers=headers,
            json={
                "case_id": case_id,
                "step_name": step_name,
                "doc_name": test_doc_name,
                "is_mandatory": True,
                "tag": "mandatory",
                "notes": "Test document request"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "message" in response.json()
        
        print(f"SUCCESS: CM requested document '{test_doc_name}' for step '{step_name}'")
        
        # Verify document appears in step
        verify_response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        verify_data = verify_response.json()
        
        step_found = next((s for s in verify_data["steps"] if s["step_name"] == step_name), None)
        assert step_found, f"Step {step_name} not found"
        
        doc_found = any(d["doc_name"] == test_doc_name for d in step_found["documents"])
        assert doc_found, f"Document {test_doc_name} not found in step"
        
        print(f"SUCCESS: Document verified in step documents list")
        
    def test_cm_request_step_document_duplicate_rejected(self):
        """Test CM cannot add duplicate document to step"""
        cm_token = self.get_token(CM_EMAIL, CM_PASSWORD)
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        cases_response = self.session.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases assigned to CM")
            
        case_id = cases[0]["id"]
        
        # Get steps
        step_docs_response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        steps = step_docs_response.json().get("steps", [])
        
        if not steps or not steps[0].get("documents"):
            pytest.skip("No documents in first step")
            
        step_name = steps[0]["step_name"]
        existing_doc = steps[0]["documents"][0]["doc_name"]
        
        # Try to add duplicate
        response = self.session.post(f"{BASE_URL}/api/step-documents/request-step-doc", 
            headers=headers,
            json={
                "case_id": case_id,
                "step_name": step_name,
                "doc_name": existing_doc,
                "is_mandatory": True,
                "tag": "mandatory"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"
        print(f"SUCCESS: Duplicate document rejected as expected")
        
    def test_client_cannot_request_step_document(self):
        """Test client cannot request documents (CM/Admin only)"""
        client_token = self.get_token(CLIENT_EMAIL, CLIENT_PASSWORD)
        case_id = self.get_client_case_id(client_token)
        
        headers = {"Authorization": f"Bearer {client_token}"}
        response = self.session.post(f"{BASE_URL}/api/step-documents/request-step-doc", 
            headers=headers,
            json={
                "case_id": case_id,
                "step_name": "Profile Creation",
                "doc_name": "Test Doc",
                "is_mandatory": True
            }
        )
        
        assert response.status_code == 403, f"Expected 403 for client, got {response.status_code}"
        print(f"SUCCESS: Client correctly denied from requesting documents")
        
    # ============ POST /api/step-documents/request-additional Tests ============
    
    def test_cm_request_additional_document(self):
        """Test CM can request additional document (not tied to step)"""
        cm_token = self.get_token(CM_EMAIL, CM_PASSWORD)
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        cases_response = self.session.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases assigned to CM")
            
        case_id = cases[0]["id"]
        test_doc_name = f"TEST_Additional_{uuid.uuid4().hex[:6]}"
        
        response = self.session.post(f"{BASE_URL}/api/step-documents/request-additional", 
            headers=headers,
            json={
                "case_id": case_id,
                "doc_name": test_doc_name,
                "is_mandatory": True,
                "tag": "mandatory",
                "notes": "Additional document for testing"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response should have document request ID"
        
        print(f"SUCCESS: CM requested additional document '{test_doc_name}'")
        
        # Verify in additional_requests
        verify_response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        verify_data = verify_response.json()
        
        additional = verify_data.get("additional_requests", [])
        doc_found = any(r["doc_name"] == test_doc_name for r in additional)
        assert doc_found, f"Additional document {test_doc_name} not found"
        
        print(f"SUCCESS: Additional document verified in response")
        
    # ============ POST /api/step-documents/remove-step-doc Tests ============
    
    def test_cm_remove_cm_added_document(self):
        """Test CM can remove documents they added (source=cm_request)"""
        cm_token = self.get_token(CM_EMAIL, CM_PASSWORD)
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        cases_response = self.session.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases assigned to CM")
            
        case_id = cases[0]["id"]
        
        # Get steps
        step_docs_response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        steps = step_docs_response.json().get("steps", [])
        
        if not steps:
            pytest.skip("No steps found")
            
        step_name = steps[0]["step_name"]
        
        # First add a document
        test_doc_name = f"TEST_ToRemove_{uuid.uuid4().hex[:6]}"
        add_response = self.session.post(f"{BASE_URL}/api/step-documents/request-step-doc", 
            headers=headers,
            json={
                "case_id": case_id,
                "step_name": step_name,
                "doc_name": test_doc_name,
                "is_mandatory": False,
                "tag": "optional"
            }
        )
        assert add_response.status_code == 200, f"Failed to add doc: {add_response.text}"
        
        # Now remove it
        remove_response = self.session.post(f"{BASE_URL}/api/step-documents/remove-step-doc", 
            headers=headers,
            json={
                "case_id": case_id,
                "step_name": step_name,
                "doc_name": test_doc_name
            }
        )
        
        assert remove_response.status_code == 200, f"Expected 200, got {remove_response.status_code}: {remove_response.text}"
        
        print(f"SUCCESS: CM removed their own document '{test_doc_name}'")
        
        # Verify removal
        verify_response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        verify_data = verify_response.json()
        
        step_found = next((s for s in verify_data["steps"] if s["step_name"] == step_name), None)
        doc_still_exists = any(d["doc_name"] == test_doc_name for d in step_found.get("documents", []))
        assert not doc_still_exists, f"Document {test_doc_name} should have been removed"
        
        print(f"SUCCESS: Document removal verified")
        
    def test_cm_cannot_remove_admin_document(self):
        """Test CM cannot remove admin-defined documents (source=admin_default)"""
        cm_token = self.get_token(CM_EMAIL, CM_PASSWORD)
        headers = {"Authorization": f"Bearer {cm_token}"}
        
        cases_response = self.session.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases assigned to CM")
            
        case_id = cases[0]["id"]
        
        # Get steps and find an admin-defined document
        step_docs_response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=headers)
        steps = step_docs_response.json().get("steps", [])
        
        admin_doc = None
        step_name = None
        for step in steps:
            for doc in step.get("documents", []):
                if doc.get("source") == "admin_default":
                    admin_doc = doc["doc_name"]
                    step_name = step["step_name"]
                    break
            if admin_doc:
                break
                
        if not admin_doc:
            pytest.skip("No admin-defined documents found to test removal restriction")
            
        # Try to remove admin document
        remove_response = self.session.post(f"{BASE_URL}/api/step-documents/remove-step-doc", 
            headers=headers,
            json={
                "case_id": case_id,
                "step_name": step_name,
                "doc_name": admin_doc
            }
        )
        
        assert remove_response.status_code == 403, f"Expected 403 for admin doc removal, got {remove_response.status_code}"
        print(f"SUCCESS: CM correctly denied from removing admin document '{admin_doc}'")
        
    # ============ Admin Workflow Step Document Persistence Tests ============
    
    def test_admin_workflow_step_documents_persist(self):
        """Test admin workflow step documents are saved properly"""
        admin_token = self.get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert admin_token, "Admin login failed"
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get products
        products_response = self.session.get(f"{BASE_URL}/api/products", headers=headers)
        assert products_response.status_code == 200
        
        products = products_response.json()
        if not products:
            pytest.skip("No products found")
            
        product = products[0]
        product_id = product["id"]
        
        # Get workflow steps
        steps = product.get("workflow_steps", [])
        if not steps:
            pytest.skip("No workflow steps found")
            
        step = steps[0]
        step_order = step["step_order"]
        
        # Update step with new documents
        test_docs = [
            {"doc_name": f"TEST_Admin_Doc_{uuid.uuid4().hex[:4]}", "is_mandatory": True, "tag": "mandatory", "source": "admin_default"},
            {"doc_name": f"TEST_Admin_Doc_{uuid.uuid4().hex[:4]}", "is_mandatory": False, "tag": "optional", "source": "admin_default"}
        ]
        
        update_response = self.session.put(
            f"{BASE_URL}/api/products/{product_id}/workflow-step/{step_order}",
            headers=headers,
            json={
                "step_name": step["step_name"],
                "description": step.get("description", ""),
                "duration_days": step.get("duration_days", 7),
                "required_documents": test_docs
            }
        )
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        # Verify persistence by fetching product again
        verify_response = self.session.get(f"{BASE_URL}/api/products/{product_id}", headers=headers)
        assert verify_response.status_code == 200
        
        verify_product = verify_response.json()
        verify_steps = verify_product.get("workflow_steps", [])
        verify_step = next((s for s in verify_steps if s["step_order"] == step_order), None)
        
        assert verify_step, f"Step {step_order} not found after update"
        saved_docs = verify_step.get("required_documents", [])
        
        # Check our test docs are saved
        for test_doc in test_docs:
            found = any(d.get("doc_name") == test_doc["doc_name"] for d in saved_docs)
            assert found, f"Document {test_doc['doc_name']} not persisted"
            
        print(f"SUCCESS: Admin workflow step documents persisted correctly ({len(saved_docs)} docs)")


class TestStepDocumentsIntegration:
    """Integration tests for step-wise document flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_token(self, email, password):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
        
    def test_full_step_document_flow(self):
        """Test complete flow: CM adds doc -> Client sees it -> CM removes it"""
        cm_token = self.get_token(CM_EMAIL, CM_PASSWORD)
        client_token = self.get_token(CLIENT_EMAIL, CLIENT_PASSWORD)
        
        assert cm_token, "CM login failed"
        assert client_token, "Client login failed"
        
        # Get client's case
        client_headers = {"Authorization": f"Bearer {client_token}"}
        cases_response = self.session.get(f"{BASE_URL}/api/cases/my-cases", headers=client_headers)
        cases = cases_response.json()
        
        if not cases:
            pytest.skip("No cases for client")
            
        case_id = cases[0]["id"]
        
        # Get steps
        step_docs_response = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=client_headers)
        steps = step_docs_response.json().get("steps", [])
        
        if not steps:
            pytest.skip("No steps found")
            
        step_name = steps[0]["step_name"]
        test_doc_name = f"TEST_Flow_{uuid.uuid4().hex[:6]}"
        
        # Step 1: CM adds document
        cm_headers = {"Authorization": f"Bearer {cm_token}"}
        add_response = self.session.post(f"{BASE_URL}/api/step-documents/request-step-doc", 
            headers=cm_headers,
            json={
                "case_id": case_id,
                "step_name": step_name,
                "doc_name": test_doc_name,
                "is_mandatory": True,
                "tag": "mandatory",
                "notes": "Integration test document"
            }
        )
        assert add_response.status_code == 200, f"CM add failed: {add_response.text}"
        print(f"Step 1 PASS: CM added document '{test_doc_name}'")
        
        # Step 2: Client sees the document
        client_verify = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=client_headers)
        client_data = client_verify.json()
        
        step_found = next((s for s in client_data["steps"] if s["step_name"] == step_name), None)
        doc_visible = any(d["doc_name"] == test_doc_name for d in step_found.get("documents", []))
        assert doc_visible, "Client should see CM-added document"
        print(f"Step 2 PASS: Client sees document in their step-wise view")
        
        # Step 3: CM removes document
        remove_response = self.session.post(f"{BASE_URL}/api/step-documents/remove-step-doc", 
            headers=cm_headers,
            json={
                "case_id": case_id,
                "step_name": step_name,
                "doc_name": test_doc_name
            }
        )
        assert remove_response.status_code == 200, f"CM remove failed: {remove_response.text}"
        print(f"Step 3 PASS: CM removed document")
        
        # Step 4: Client no longer sees document
        final_verify = self.session.get(f"{BASE_URL}/api/step-documents/case/{case_id}", headers=client_headers)
        final_data = final_verify.json()
        
        step_found = next((s for s in final_data["steps"] if s["step_name"] == step_name), None)
        doc_gone = not any(d["doc_name"] == test_doc_name for d in step_found.get("documents", []))
        assert doc_gone, "Document should be removed from client view"
        print(f"Step 4 PASS: Document no longer visible to client")
        
        print(f"SUCCESS: Full step document flow completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
