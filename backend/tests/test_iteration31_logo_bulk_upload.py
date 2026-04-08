"""
Iteration 31 Tests: Logo Integration & Bulk Upload Features
- Logo in PDF reports (sales report, commission report, payment receipt)
- Bulk upload with per-file document_types and step_names
- Login for all 4 roles
- Health check
"""
import pytest
import requests
import os
import json
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CREDENTIALS = {
    "admin": {"email": "admin@leamss.com", "password": "Admin@123"},
    "case_manager": {"email": "manager@leamss.com", "password": "Manager@123"},
    "partner": {"email": "partner@leamss.com", "password": "Partner@123"},
    "client": {"email": "client@leamss.com", "password": "Client@123"},
}


class TestHealthAndAuth:
    """Health check and authentication tests"""

    def test_health_check(self):
        """Test health endpoint returns healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert data.get("database") == "connected"
        print(f"✓ Health check passed: {data}")

    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['email']}")

    def test_case_manager_login(self):
        """Test case manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["case_manager"])
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print(f"✓ Case Manager login successful: {data['user']['email']}")

    def test_partner_login(self):
        """Test partner login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["partner"])
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"✓ Partner login successful: {data['user']['email']}")

    def test_client_login(self):
        """Test client login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print(f"✓ Client login successful: {data['user']['email']}")


class TestPDFReportsWithLogo:
    """Test PDF reports include LEAMSS logo"""

    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")

    def test_sales_report_pdf_with_logo(self, admin_token):
        """Test sales report PDF is generated with logo (file > 100KB indicates logo included)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/export/sales-report", headers=headers)
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        
        # Check file size - with logo should be > 100KB
        content_length = len(response.content)
        print(f"Sales report PDF size: {content_length / 1024:.1f} KB")
        
        # PDF with logo should be larger than 100KB
        assert content_length > 100 * 1024, f"PDF size {content_length} bytes is too small, logo may be missing"
        print(f"✓ Sales report PDF generated with logo ({content_length / 1024:.1f} KB)")

    def test_commission_report_pdf_with_logo(self, admin_token):
        """Test commission report PDF is generated with logo"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reports/export/commission-report", headers=headers)
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        
        content_length = len(response.content)
        print(f"Commission report PDF size: {content_length / 1024:.1f} KB")
        
        # PDF with logo should be larger than 100KB
        assert content_length > 100 * 1024, f"PDF size {content_length} bytes is too small, logo may be missing"
        print(f"✓ Commission report PDF generated with logo ({content_length / 1024:.1f} KB)")


class TestPaymentReceiptPDF:
    """Test payment receipt PDF includes logo"""

    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")

    @pytest.fixture
    def sale_with_payment(self, admin_token):
        """Find a sale with at least one payment transaction"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all sales
        response = requests.get(f"{BASE_URL}/api/sales", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not fetch sales")
        
        sales = response.json()
        
        # Find a sale with transactions
        for sale in sales:
            if sale.get("transactions") and len(sale["transactions"]) > 0:
                return sale
        
        pytest.skip("No sales with payment transactions found")

    def test_payment_receipt_pdf_with_logo(self, admin_token, sale_with_payment):
        """Test payment receipt PDF is generated with logo"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        sale_id = sale_with_payment["id"]
        
        response = requests.get(f"{BASE_URL}/api/reports/export/sale-receipt/{sale_id}", headers=headers)
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        
        content_length = len(response.content)
        print(f"Payment receipt PDF size: {content_length / 1024:.1f} KB")
        
        # PDF with logo should be larger than 100KB
        assert content_length > 100 * 1024, f"PDF size {content_length} bytes is too small, logo may be missing"
        print(f"✓ Payment receipt PDF generated with logo ({content_length / 1024:.1f} KB)")


class TestBulkUploadWithPerFileMetadata:
    """Test bulk upload endpoint with per-file document_types and step_names"""

    @pytest.fixture
    def client_token(self):
        """Get client auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["client"])
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Client authentication failed")

    @pytest.fixture
    def client_case_id(self, client_token):
        """Get client's case ID"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/my-cases", headers=headers)
        if response.status_code == 200:
            cases = response.json()
            if cases and len(cases) > 0:
                return cases[0]["id"]
        pytest.skip("No cases found for client")

    def test_bulk_upload_with_per_file_types(self, client_token, client_case_id):
        """Test bulk upload accepts document_types and step_names JSON arrays"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # Create test files
        files = [
            ('files', ('test_passport.pdf', b'%PDF-1.4 test passport content', 'application/pdf')),
            ('files', ('test_photo.jpg', b'\xff\xd8\xff\xe0 test photo content', 'image/jpeg')),
            ('files', ('test_resume.pdf', b'%PDF-1.4 test resume content', 'application/pdf')),
        ]
        
        # Per-file metadata
        document_types = json.dumps(["passport", "photo", "resume"])
        step_names = json.dumps(["Document Collection", "Document Collection", "Document Collection"])
        
        data = {
            'case_id': client_case_id,
            'document_types': document_types,
            'step_names': step_names,
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/bulk-upload",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "uploaded" in result
        assert len(result["uploaded"]) == 3
        
        # Verify per-file types were applied
        uploaded_types = [u["document_type"] for u in result["uploaded"]]
        assert "passport" in uploaded_types
        assert "photo" in uploaded_types
        assert "resume" in uploaded_types
        
        print(f"✓ Bulk upload with per-file types successful: {result['message']}")
        print(f"  Uploaded files: {[u['filename'] for u in result['uploaded']]}")
        print(f"  Document types: {uploaded_types}")

    def test_bulk_upload_with_default_type(self, client_token, client_case_id):
        """Test bulk upload falls back to default document_type when per-file types not provided"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        files = [
            ('files', ('test_doc1.pdf', b'%PDF-1.4 test doc 1', 'application/pdf')),
            ('files', ('test_doc2.pdf', b'%PDF-1.4 test doc 2', 'application/pdf')),
        ]
        
        data = {
            'case_id': client_case_id,
            'document_type': 'general',  # Default type
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/bulk-upload",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "uploaded" in result
        assert len(result["uploaded"]) == 2
        
        # All should have default type
        for uploaded in result["uploaded"]:
            assert uploaded["document_type"] == "general"
        
        print(f"✓ Bulk upload with default type successful: {result['message']}")


class TestLogoFileExists:
    """Verify logo files exist in expected locations"""

    def test_frontend_logo_exists(self):
        """Test frontend logo file exists"""
        logo_path = "/app/frontend/public/leamss-logo.png"
        assert os.path.exists(logo_path), f"Frontend logo not found at {logo_path}"
        
        file_size = os.path.getsize(logo_path)
        assert file_size > 10000, f"Logo file too small ({file_size} bytes)"
        print(f"✓ Frontend logo exists: {logo_path} ({file_size / 1024:.1f} KB)")

    def test_backend_logo_exists(self):
        """Test backend logo file exists for PDF generation"""
        logo_path = "/app/backend/uploads/leamss-logo.png"
        assert os.path.exists(logo_path), f"Backend logo not found at {logo_path}"
        
        file_size = os.path.getsize(logo_path)
        assert file_size > 10000, f"Logo file too small ({file_size} bytes)"
        print(f"✓ Backend logo exists: {logo_path} ({file_size / 1024:.1f} KB)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
