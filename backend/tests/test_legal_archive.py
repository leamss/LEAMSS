"""
Legal Archive API Tests - Iteration 85
Tests for the Legal Archive compliance dashboard feature:
- GET /api/legal-archive/stats (admin only)
- GET /api/legal-archive/search (with filters: q, record_type, start_date, end_date)
- GET /api/legal-archive/{ref_id} (fetch by reference ID)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"


class TestLegalArchiveAuth:
    """Test authentication and authorization for Legal Archive endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
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
    
    def test_01_admin_can_access_stats(self):
        """Admin should be able to access /api/legal-archive/stats"""
        token = self.get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "consents" in data, "Response should contain 'consents' count"
        assert "signatures" in data, "Response should contain 'signatures' count"
        assert "invoices" in data, "Response should contain 'invoices' count"
        assert "total" in data, "Response should contain 'total' count"
        
        # Verify total is sum of all types
        assert data["total"] == data["consents"] + data["signatures"] + data["invoices"], \
            f"Total ({data['total']}) should equal sum of consents ({data['consents']}) + signatures ({data['signatures']}) + invoices ({data['invoices']})"
        
        print(f"PASS: Stats returned - consents={data['consents']}, signatures={data['signatures']}, invoices={data['invoices']}, total={data['total']}")
    
    def test_02_partner_cannot_access_stats(self):
        """Partner should get 403 when accessing /api/legal-archive/stats"""
        token = self.get_token(PARTNER_EMAIL, PARTNER_PASSWORD)
        assert token is not None, "Partner login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        data = response.json()
        assert "Admin only" in data.get("detail", ""), f"Expected 'Admin only' in error message, got: {data}"
        print(f"PASS: Partner correctly blocked with 403 - {data.get('detail')}")
    
    def test_03_partner_cannot_access_search(self):
        """Partner should get 403 when accessing /api/legal-archive/search"""
        token = self.get_token(PARTNER_EMAIL, PARTNER_PASSWORD)
        assert token is not None, "Partner login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Partner correctly blocked from search endpoint")
    
    def test_04_unauthenticated_cannot_access(self):
        """Unauthenticated requests should get 401"""
        response = self.session.get(f"{BASE_URL}/api/legal-archive/stats")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Unauthenticated request correctly blocked")


class TestLegalArchiveSearch:
    """Test search functionality for Legal Archive"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, "Admin login failed"
        self.token = response.json().get("token")
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_05_search_returns_all_records(self):
        """Search without filters should return all records"""
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search",
            headers=self.auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "count" in data, "Response should contain 'count'"
        assert "filters" in data, "Response should contain 'filters'"
        assert "items" in data, "Response should contain 'items'"
        assert isinstance(data["items"], list), "Items should be a list"
        
        print(f"PASS: Search returned {data['count']} records")
        
        # Verify item structure if there are records
        if data["items"]:
            item = data["items"][0]
            required_fields = ["type", "reference_id", "pa_id", "client_name", "timestamp"]
            for field in required_fields:
                assert field in item, f"Item should contain '{field}'"
            print(f"PASS: Item structure verified - type={item['type']}, ref_id={item.get('reference_id')}")
    
    def test_06_search_filter_by_consent_type(self):
        """Search with record_type=consent should only return consent records"""
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=consent",
            headers=self.auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "consent", f"Expected type 'consent', got '{item['type']}'"
        
        print(f"PASS: Consent filter returned {data['count']} consent records")
    
    def test_07_search_filter_by_signature_type(self):
        """Search with record_type=signature should only return signature records"""
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=signature",
            headers=self.auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "signature", f"Expected type 'signature', got '{item['type']}'"
        
        print(f"PASS: Signature filter returned {data['count']} signature records")
    
    def test_08_search_filter_by_invoice_type(self):
        """Search with record_type=invoice should only return invoice records"""
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=invoice",
            headers=self.auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "invoice", f"Expected type 'invoice', got '{item['type']}'"
        
        print(f"PASS: Invoice filter returned {data['count']} invoice records")
    
    def test_09_search_free_text_query(self):
        """Search with q parameter should filter by text"""
        # First get all records to find a searchable term
        all_response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search",
            headers=self.auth_headers
        )
        all_data = all_response.json()
        
        if all_data["items"]:
            # Use client_name from first record as search term
            search_term = all_data["items"][0].get("client_name", "")
            if search_term:
                response = self.session.get(
                    f"{BASE_URL}/api/legal-archive/search?q={search_term[:5]}",
                    headers=self.auth_headers
                )
                assert response.status_code == 200
                data = response.json()
                print(f"PASS: Free text search for '{search_term[:5]}' returned {data['count']} records")
            else:
                print("SKIP: No client_name to search for")
        else:
            print("SKIP: No records to test free text search")
    
    def test_10_search_date_range_filter(self):
        """Search with date range should filter by timestamp"""
        # Use a wide date range to ensure we get results
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?start_date=2024-01-01&end_date=2027-12-31",
            headers=self.auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["filters"]["start_date"] == "2024-01-01"
        assert data["filters"]["end_date"] == "2027-12-31"
        print(f"PASS: Date range filter returned {data['count']} records")
    
    def test_11_search_results_sorted_desc(self):
        """Search results should be sorted by timestamp descending"""
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search",
            headers=self.auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        if len(items) >= 2:
            # Verify descending order
            for i in range(len(items) - 1):
                ts1 = items[i].get("timestamp") or ""
                ts2 = items[i + 1].get("timestamp") or ""
                assert ts1 >= ts2, f"Results not sorted desc: {ts1} should be >= {ts2}"
            print(f"PASS: Results are sorted by timestamp descending")
        else:
            print("SKIP: Not enough records to verify sorting")


class TestLegalArchiveGetByRefId:
    """Test fetching records by reference ID"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, "Admin login failed"
        self.token = response.json().get("token")
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_12_get_by_valid_ref_id(self):
        """Fetching by valid reference_id should return the record"""
        # First get a record with a reference_id
        search_response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search",
            headers=self.auth_headers
        )
        search_data = search_response.json()
        
        # Find a record with a reference_id (consents and invoices have them)
        ref_id = None
        for item in search_data["items"]:
            if item.get("reference_id") and (item["type"] == "consent" or item["type"] == "invoice"):
                ref_id = item["reference_id"]
                break
        
        if ref_id:
            response = self.session.get(
                f"{BASE_URL}/api/legal-archive/{ref_id}",
                headers=self.auth_headers
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert "type" in data, "Response should contain 'type'"
            assert "record" in data, "Response should contain 'record'"
            print(f"PASS: Fetched record by ref_id={ref_id}, type={data['type']}")
        else:
            print("SKIP: No records with reference_id found")
    
    def test_13_get_by_invalid_ref_id_returns_404(self):
        """Fetching by invalid reference_id should return 404"""
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/INVALID-REF-ID-12345",
            headers=self.auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Invalid ref_id correctly returns 404")
    
    def test_14_partner_cannot_get_by_ref_id(self):
        """Partner should get 403 when fetching by reference_id"""
        # Login as partner
        partner_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTNER_EMAIL,
            "password": PARTNER_PASSWORD
        })
        partner_token = partner_response.json().get("token")
        
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/CON-TEST-123",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Partner correctly blocked from fetching by ref_id")


class TestLegalArchiveDataIntegrity:
    """Test data integrity and field presence"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, "Admin login failed"
        self.token = response.json().get("token")
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_15_consent_record_fields(self):
        """Consent records should have expected fields"""
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=consent",
            headers=self.auth_headers
        )
        data = response.json()
        
        if data["items"]:
            item = data["items"][0]
            assert item["type"] == "consent"
            # Consent-specific fields
            expected_fields = ["reference_id", "client_name", "client_email", "timestamp", "preview"]
            for field in expected_fields:
                assert field in item, f"Consent record should have '{field}'"
            
            # Preview should have fee breakdown
            if item.get("preview"):
                preview = item["preview"]
                assert "base_fee" in preview or "final_amount" in preview, "Preview should have fee info"
            
            print(f"PASS: Consent record has all expected fields")
        else:
            print("SKIP: No consent records to verify")
    
    def test_16_signature_record_fields(self):
        """Signature records should have expected fields"""
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=signature",
            headers=self.auth_headers
        )
        data = response.json()
        
        if data["items"]:
            item = data["items"][0]
            assert item["type"] == "signature"
            # Signature-specific fields
            expected_fields = ["reference_id", "client_name", "timestamp", "ip_address"]
            for field in expected_fields:
                assert field in item, f"Signature record should have '{field}'"
            
            print(f"PASS: Signature record has all expected fields")
        else:
            print("SKIP: No signature records to verify")
    
    def test_17_invoice_record_fields(self):
        """Invoice records should have expected fields"""
        response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=invoice",
            headers=self.auth_headers
        )
        data = response.json()
        
        if data["items"]:
            item = data["items"][0]
            assert item["type"] == "invoice"
            # Invoice-specific fields
            expected_fields = ["reference_id", "client_name", "client_email", "timestamp", "amount"]
            for field in expected_fields:
                assert field in item, f"Invoice record should have '{field}'"
            
            print(f"PASS: Invoice record has all expected fields, amount={item.get('amount')}")
        else:
            print("SKIP: No invoice records to verify")
    
    def test_18_stats_match_search_counts(self):
        """Stats counts should match search results by type"""
        # Get stats
        stats_response = self.session.get(
            f"{BASE_URL}/api/legal-archive/stats",
            headers=self.auth_headers
        )
        stats = stats_response.json()
        
        # Get search counts by type
        consent_response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=consent",
            headers=self.auth_headers
        )
        consent_count = consent_response.json()["count"]
        
        signature_response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=signature",
            headers=self.auth_headers
        )
        signature_count = signature_response.json()["count"]
        
        invoice_response = self.session.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=invoice",
            headers=self.auth_headers
        )
        invoice_count = invoice_response.json()["count"]
        
        # Verify counts match (within limit of 100)
        assert stats["consents"] == consent_count or consent_count == 100, \
            f"Stats consents ({stats['consents']}) should match search count ({consent_count})"
        assert stats["signatures"] == signature_count or signature_count == 100, \
            f"Stats signatures ({stats['signatures']}) should match search count ({signature_count})"
        assert stats["invoices"] == invoice_count or invoice_count == 100, \
            f"Stats invoices ({stats['invoices']}) should match search count ({invoice_count})"
        
        print(f"PASS: Stats match search counts - consents={stats['consents']}, signatures={stats['signatures']}, invoices={stats['invoices']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
