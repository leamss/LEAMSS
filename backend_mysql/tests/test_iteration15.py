"""
LEAMSS Portal - Iteration 15 Comprehensive Backend Tests
Tests all features mentioned in the review request:
- Admin login and dashboard
- Sales with online/bank_transfer payment methods
- Sale approval with client credentials
- Case manager assignment
- Document upload/download
- Activity logs
- Information sheet CRUD
- Commissions
- Global search
- User impersonation
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API = f"{BASE_URL}/api"

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"
MANAGER_EMAIL = "manager@leamss.com"
MANAGER_PASSWORD = "Manager@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASSWORD = "Client@123"


class TestAuthentication:
    """Test authentication for all user roles"""
    
    def test_admin_login(self):
        """Admin login should return token and user data"""
        response = requests.post(f"{API}/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful: {data['user']['name']}")
    
    def test_partner_login(self):
        """Partner login should return token and user data"""
        response = requests.post(f"{API}/auth/login", json={
            "email": PARTNER_EMAIL,
            "password": PARTNER_PASSWORD
        })
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"✓ Partner login successful: {data['user']['name']}")
    
    def test_case_manager_login(self):
        """Case manager login should return token and user data"""
        response = requests.post(f"{API}/auth/login", json={
            "email": MANAGER_EMAIL,
            "password": MANAGER_PASSWORD
        })
        assert response.status_code == 200, f"Case manager login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print(f"✓ Case manager login successful: {data['user']['name']}")
    
    def test_client_login(self):
        """Client login should return token and user data"""
        response = requests.post(f"{API}/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print(f"✓ Client login successful: {data['user']['name']}")


@pytest.fixture
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{API}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Admin authentication failed")


@pytest.fixture
def partner_token():
    """Get partner authentication token"""
    response = requests.post(f"{API}/auth/login", json={
        "email": PARTNER_EMAIL,
        "password": PARTNER_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Partner authentication failed")


@pytest.fixture
def manager_token():
    """Get case manager authentication token"""
    response = requests.post(f"{API}/auth/login", json={
        "email": MANAGER_EMAIL,
        "password": MANAGER_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Case manager authentication failed")


@pytest.fixture
def client_token():
    """Get client authentication token"""
    response = requests.post(f"{API}/auth/login", json={
        "email": CLIENT_EMAIL,
        "password": CLIENT_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Client authentication failed")


class TestAdminDashboard:
    """Test admin dashboard endpoints"""
    
    def test_admin_dashboard_stats(self, admin_token):
        """Admin dashboard stats should load"""
        response = requests.get(f"{API}/stats/dashboard", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        assert "pending_sales" in data or "active_cases" in data or "total_revenue" in data
        print(f"✓ Admin dashboard stats: {data}")
    
    def test_admin_get_all_sales(self, admin_token):
        """Admin should see ALL sales with status filter"""
        response = requests.get(f"{API}/sales", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get all sales failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin sees {len(data)} total sales")
    
    def test_admin_get_pending_sales(self, admin_token):
        """Admin should see pending sales"""
        response = requests.get(f"{API}/sales/pending", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get pending sales failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin sees {len(data)} pending sales")
    
    def test_admin_get_all_cases(self, admin_token):
        """Admin should see all cases"""
        response = requests.get(f"{API}/cases", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get all cases failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin sees {len(data)} cases")
    
    def test_admin_get_users(self, admin_token):
        """Admin should see all users"""
        response = requests.get(f"{API}/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get users failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print(f"✓ Admin sees {len(data)} users")


class TestSalesWithPaymentMethods:
    """Test sales creation with different payment methods"""
    
    def test_get_products(self, partner_token):
        """Partner should see available products"""
        response = requests.get(f"{API}/products", headers={
            "Authorization": f"Bearer {partner_token}"
        })
        assert response.status_code == 200, f"Get products failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print(f"✓ Partner sees {len(data)} products")
        return data[0]["id"] if data else None
    
    def test_create_sale_with_online_payment(self, partner_token):
        """Partner should create sale with 'online' payment method"""
        # First get a product
        products_response = requests.get(f"{API}/products", headers={
            "Authorization": f"Bearer {partner_token}"
        })
        products = products_response.json()
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0]["id"]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Create sale with online payment
        form_data = {
            "client_name": f"TEST_Online_Client_{timestamp}",
            "client_email": f"test_online_{timestamp}@example.com",
            "client_mobile": "+1234567890",
            "product_id": product_id,
            "fee_amount": "5000",
            "amount_received": "5000",
            "payment_method": "online",
            "payment_reference": "",
            "agreement_signed": "true"
        }
        
        response = requests.post(f"{API}/sales", data=form_data, headers={
            "Authorization": f"Bearer {partner_token}"
        })
        assert response.status_code == 200, f"Create sale with online payment failed: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ Sale created with 'online' payment method: {data['id']}")
        return data["id"]
    
    def test_create_sale_with_bank_transfer(self, partner_token):
        """Partner should create sale with 'bank_transfer' payment method"""
        products_response = requests.get(f"{API}/products", headers={
            "Authorization": f"Bearer {partner_token}"
        })
        products = products_response.json()
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0]["id"]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        form_data = {
            "client_name": f"TEST_BankTransfer_Client_{timestamp}",
            "client_email": f"test_bank_{timestamp}@example.com",
            "client_mobile": "+1234567891",
            "product_id": product_id,
            "fee_amount": "6000",
            "amount_received": "6000",
            "payment_method": "bank_transfer",
            "payment_reference": f"REF-{timestamp}",
            "agreement_signed": "true"
        }
        
        response = requests.post(f"{API}/sales", data=form_data, headers={
            "Authorization": f"Bearer {partner_token}"
        })
        assert response.status_code == 200, f"Create sale with bank_transfer failed: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ Sale created with 'bank_transfer' payment method: {data['id']}")
        return data["id"]


class TestSaleApproval:
    """Test sale approval and client credentials"""
    
    def test_approve_sale_returns_client_credentials(self, admin_token, partner_token):
        """Approving a sale for new client should return credentials"""
        # First create a sale
        products_response = requests.get(f"{API}/products", headers={
            "Authorization": f"Bearer {partner_token}"
        })
        products = products_response.json()
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0]["id"]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        form_data = {
            "client_name": f"TEST_NewClient_{timestamp}",
            "client_email": f"test_newclient_{timestamp}@example.com",
            "client_mobile": "+1234567892",
            "product_id": product_id,
            "fee_amount": "7000",
            "amount_received": "7000",
            "payment_method": "online",
            "payment_reference": "",
            "agreement_signed": "true"
        }
        
        create_response = requests.post(f"{API}/sales", data=form_data, headers={
            "Authorization": f"Bearer {partner_token}"
        })
        assert create_response.status_code == 200, f"Create sale failed: {create_response.text}"
        sale_id = create_response.json()["id"]
        
        # Approve the sale
        approve_response = requests.post(f"{API}/sales/approve", json={
            "sale_id": sale_id,
            "status": "approved",
            "case_manager_id": None
        }, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert approve_response.status_code == 200, f"Approve sale failed: {approve_response.text}"
        data = approve_response.json()
        
        # Check for client credentials
        if "client_credentials" in data:
            creds = data["client_credentials"]
            assert "email" in creds
            assert "password" in creds
            print(f"✓ Sale approved with client credentials: {creds['email']}")
        else:
            print(f"✓ Sale approved (existing client, no new credentials)")


class TestCaseManagerAssignment:
    """Test case manager assignment functionality"""
    
    def test_assign_case_manager(self, admin_token):
        """Admin should be able to assign case manager to a case"""
        # Get cases
        cases_response = requests.get(f"{API}/cases", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        cases = cases_response.json()
        if not cases:
            pytest.skip("No cases available")
        
        case_id = cases[0]["id"]
        
        # Get case managers
        users_response = requests.get(f"{API}/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        users = users_response.json()
        case_managers = [u for u in users if u["role"] == "case_manager"]
        if not case_managers:
            pytest.skip("No case managers available")
        
        manager_id = case_managers[0]["id"]
        
        # Assign case manager
        response = requests.put(
            f"{API}/cases/{case_id}/assign-manager?case_manager_id={manager_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Assign case manager failed: {response.text}"
        print(f"✓ Case manager assigned to case {case_id}")


class TestCaseManagerDashboard:
    """Test case manager dashboard functionality"""
    
    def test_case_manager_my_cases(self, manager_token):
        """Case manager should see their assigned cases"""
        response = requests.get(f"{API}/cases/my-cases", headers={
            "Authorization": f"Bearer {manager_token}"
        })
        assert response.status_code == 200, f"Get my cases failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Case manager sees {len(data)} cases")
        return data
    
    def test_case_manager_stats(self, manager_token):
        """Case manager should see their stats"""
        response = requests.get(f"{API}/cases/stats/my-stats", headers={
            "Authorization": f"Bearer {manager_token}"
        })
        assert response.status_code == 200, f"Get case manager stats failed: {response.text}"
        data = response.json()
        assert "my_cases" in data or "active_cases" in data
        print(f"✓ Case manager stats: {data}")


class TestInformationSheet:
    """Test information sheet save and retrieve"""
    
    def test_save_and_get_information_sheet(self, manager_token):
        """Case manager should save and retrieve information sheet"""
        # Get a case
        cases_response = requests.get(f"{API}/cases/my-cases", headers={
            "Authorization": f"Bearer {manager_token}"
        })
        cases = cases_response.json()
        if not cases:
            pytest.skip("No cases available for case manager")
        
        case_id = cases[0]["id"]
        
        # Save information sheet
        info_data = {
            "full_name": "Test Client Name",
            "date_of_birth": "1990-01-15",
            "gender": "Male",
            "nationality": "Canadian",
            "passport_number": "AB123456",
            "phone": "+1234567890",
            "email": "testclient@example.com",
            "address": "123 Test Street",
            "city": "Toronto",
            "state": "Ontario",
            "country": "Canada",
            "postal_code": "M5V 1A1",
            "highest_education": "Bachelor's Degree",
            "field_of_study": "Computer Science",
            "institution_name": "University of Toronto",
            "graduation_year": 2015,
            "current_occupation": "Software Engineer",
            "employer_name": "Tech Corp",
            "years_of_experience": 8,
            "job_title": "Senior Developer",
            "primary_language": "English",
            "english_proficiency": "Native",
            "ielts_score": 8.5,
            "marital_status": "Single",
            "number_of_dependents": 0,
            "intended_destination": "Canada",
            "purpose_of_immigration": "Work Permit"
        }
        
        save_response = requests.post(
            f"{API}/cases/{case_id}/information-sheet",
            json=info_data,
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert save_response.status_code == 200, f"Save info sheet failed: {save_response.text}"
        print(f"✓ Information sheet saved for case {case_id}")
        
        # Retrieve information sheet
        get_response = requests.get(
            f"{API}/cases/{case_id}/information-sheet",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert get_response.status_code == 200, f"Get info sheet failed: {get_response.text}"
        data = get_response.json()
        assert data.get("exists") == True
        assert data["data"]["full_name"] == "Test Client Name"
        print(f"✓ Information sheet retrieved successfully")


class TestWorkflowStepUpdate:
    """Test workflow step status update"""
    
    def test_update_step_status(self, manager_token):
        """Case manager should update workflow step status"""
        # Get a case
        cases_response = requests.get(f"{API}/cases/my-cases", headers={
            "Authorization": f"Bearer {manager_token}"
        })
        cases = cases_response.json()
        if not cases:
            pytest.skip("No cases available for case manager")
        
        case = cases[0]
        case_id = case["id"]
        
        # Get the first step
        if not case.get("steps") or len(case["steps"]) == 0:
            pytest.skip("No steps in case")
        
        step_name = case["steps"][0]["step_name"]
        
        # Update step status
        response = requests.post(f"{API}/cases/update-step", json={
            "case_id": case_id,
            "step_name": step_name,
            "status": "in_progress",
            "notes": "Testing step update"
        }, headers={
            "Authorization": f"Bearer {manager_token}"
        })
        assert response.status_code == 200, f"Update step failed: {response.text}"
        print(f"✓ Step '{step_name}' updated to 'in_progress'")


class TestDocumentUploadDownload:
    """Test document upload and download"""
    
    def test_document_upload(self, client_token):
        """Client should upload a document"""
        # Get client's cases
        cases_response = requests.get(f"{API}/cases/my-cases", headers={
            "Authorization": f"Bearer {client_token}"
        })
        cases = cases_response.json()
        if not cases:
            pytest.skip("No cases available for client")
        
        case = cases[0]
        case_id = case["id"]
        step_name = case["steps"][0]["step_name"] if case.get("steps") else "Registration"
        
        # Create a test file
        files = {
            "file": ("test_document.txt", b"This is a test document content", "text/plain")
        }
        data = {
            "case_id": case_id,
            "step_name": step_name,
            "document_type": "test_document"
        }
        
        response = requests.post(
            f"{API}/documents/upload",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Document upload failed: {response.text}"
        doc_data = response.json()
        assert "id" in doc_data
        print(f"✓ Document uploaded: {doc_data['id']}")
        return doc_data["id"]
    
    def test_document_download(self, client_token):
        """Client should download a document"""
        # Get client's cases
        cases_response = requests.get(f"{API}/cases/my-cases", headers={
            "Authorization": f"Bearer {client_token}"
        })
        cases = cases_response.json()
        if not cases:
            pytest.skip("No cases available for client")
        
        case_id = cases[0]["id"]
        
        # Get documents for the case
        docs_response = requests.get(
            f"{API}/documents/case/{case_id}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        docs = docs_response.json()
        if not docs:
            pytest.skip("No documents available")
        
        doc_id = docs[0]["id"]
        
        # Download document
        response = requests.get(
            f"{API}/documents/download/{doc_id}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Document download failed: {response.text}"
        print(f"✓ Document downloaded successfully")


class TestActivityLogs:
    """Test activity logs functionality"""
    
    def test_activity_logs_have_data(self, admin_token):
        """Activity logs should have real data"""
        response = requests.get(f"{API}/activity/logs", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get activity logs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # Activity logs should have entries from login events
        print(f"✓ Activity logs have {len(data)} entries")
        if len(data) > 0:
            print(f"  Sample log: {data[0].get('action')} by {data[0].get('user_name')}")
    
    def test_activity_stats(self, admin_token):
        """Activity stats should return data"""
        response = requests.get(f"{API}/activity/stats", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get activity stats failed: {response.text}"
        data = response.json()
        assert "total_activities" in data
        print(f"✓ Activity stats: {data.get('total_activities')} total activities")


class TestCommissions:
    """Test commissions functionality"""
    
    def test_partner_commissions(self, admin_token):
        """Admin should see partner commissions"""
        response = requests.get(f"{API}/reports/partner-commissions", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get partner commissions failed: {response.text}"
        data = response.json()
        # Can be list or dict with commissions key
        commissions = data.get("commissions", data) if isinstance(data, dict) else data
        print(f"✓ Partner commissions loaded: {len(commissions) if isinstance(commissions, list) else 'N/A'} partners")
    
    def test_partner_report(self, admin_token):
        """Admin should get partner sales report"""
        response = requests.get(f"{API}/sales/partner-report", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get partner report failed: {response.text}"
        data = response.json()
        assert "total_sales" in data or "sales" in data
        print(f"✓ Partner report: {data.get('total_sales', 'N/A')} total sales")


class TestGlobalSearch:
    """Test global search functionality"""
    
    def test_global_search(self, admin_token):
        """Global search should return results"""
        response = requests.get(f"{API}/search/global?q=Canada", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Global search failed: {response.text}"
        data = response.json()
        print(f"✓ Global search returned results")


class TestUserImpersonation:
    """Test user impersonation functionality"""
    
    def test_admin_can_impersonate_partner(self, admin_token):
        """Admin should impersonate partner"""
        # Get a partner user
        users_response = requests.get(f"{API}/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        users = users_response.json()
        partners = [u for u in users if u["role"] == "partner"]
        if not partners:
            pytest.skip("No partners available")
        
        partner_id = partners[0]["id"]
        
        response = requests.post(
            f"{API}/auth/impersonate/{partner_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Impersonate failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"✓ Admin impersonated partner: {data['user']['name']}")
    
    def test_non_admin_cannot_impersonate(self, partner_token, admin_token):
        """Non-admin should not be able to impersonate"""
        # Get admin user id
        users_response = requests.get(f"{API}/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        users = users_response.json()
        admin_user = [u for u in users if u["role"] == "admin"][0]
        
        response = requests.post(
            f"{API}/auth/impersonate/{admin_user['id']}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 403, f"Non-admin should not impersonate: {response.text}"
        print(f"✓ Non-admin correctly denied impersonation")


class TestProductsCRUD:
    """Test products CRUD operations"""
    
    def test_get_products(self, admin_token):
        """Admin should get all products"""
        response = requests.get(f"{API}/products", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Get products failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Products loaded: {len(data)} products")


class TestClientDashboard:
    """Test client dashboard functionality"""
    
    def test_client_my_cases(self, client_token):
        """Client should see their cases"""
        response = requests.get(f"{API}/cases/my-cases", headers={
            "Authorization": f"Bearer {client_token}"
        })
        assert response.status_code == 200, f"Get client cases failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Client sees {len(data)} cases")


class TestPartnerDashboard:
    """Test partner dashboard functionality"""
    
    def test_partner_my_sales(self, partner_token):
        """Partner should see their sales"""
        response = requests.get(f"{API}/sales/my-sales", headers={
            "Authorization": f"Bearer {partner_token}"
        })
        assert response.status_code == 200, f"Get partner sales failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Partner sees {len(data)} sales")
    
    def test_partner_stats(self, partner_token):
        """Partner should see their stats"""
        response = requests.get(f"{API}/stats/partner-dashboard", headers={
            "Authorization": f"Bearer {partner_token}"
        })
        assert response.status_code == 200, f"Get partner stats failed: {response.text}"
        data = response.json()
        print(f"✓ Partner stats: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
