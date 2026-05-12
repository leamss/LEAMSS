"""
Test suite for P1-P4 features of LEAMSS Portal
P1: Admin Sales & Commission reports with date filters and export
P2: Enhanced notification system with auto-read and history
P3: Case Manager Pending Review and Document Search
P4: Modernized UI for Admin, Case Manager, and Partner portals
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://staff-dashboard-66.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{API}/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        response = requests.post(f"{API}/auth/login", json=MANAGER_CREDS)
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        response = requests.post(f"{API}/auth/login", json=PARTNER_CREDS)
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def client_token(self):
        response = requests.post(f"{API}/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200, f"Client login failed: {response.text}"
        return response.json()["token"]
    
    def test_admin_login(self, admin_token):
        """Test admin can login"""
        assert admin_token is not None
        print("PASSED: Admin login successful")
    
    def test_manager_login(self, manager_token):
        """Test case manager can login"""
        assert manager_token is not None
        print("PASSED: Case Manager login successful")
    
    def test_partner_login(self, partner_token):
        """Test partner can login"""
        assert partner_token is not None
        print("PASSED: Partner login successful")
    
    def test_client_login(self, client_token):
        """Test client can login"""
        assert client_token is not None
        print("PASSED: Client login successful")


class TestP1SalesReport:
    """P1: Admin Sales Report with period filter"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{API}/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_sales_report_no_filter(self, admin_token):
        """Test sales report without filters (lifetime)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/sales", headers=headers)
        assert response.status_code == 200, f"Sales report failed: {response.text}"
        data = response.json()
        assert "sales" in data or isinstance(data, list), "Response should contain sales data"
        print(f"PASSED: Sales report returned {len(data.get('sales', data))} records")
    
    def test_sales_report_weekly_filter(self, admin_token):
        """Test sales report with weekly period filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/sales?period=weekly", headers=headers)
        assert response.status_code == 200, f"Weekly sales report failed: {response.text}"
        data = response.json()
        assert "sales" in data or isinstance(data, list)
        print(f"PASSED: Weekly sales report returned {len(data.get('sales', data))} records")
    
    def test_sales_report_monthly_filter(self, admin_token):
        """Test sales report with monthly period filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/sales?period=monthly", headers=headers)
        assert response.status_code == 200, f"Monthly sales report failed: {response.text}"
        data = response.json()
        assert "sales" in data or isinstance(data, list)
        print(f"PASSED: Monthly sales report returned {len(data.get('sales', data))} records")
    
    def test_sales_report_quarterly_filter(self, admin_token):
        """Test sales report with quarterly period filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/sales?period=quarterly", headers=headers)
        assert response.status_code == 200, f"Quarterly sales report failed: {response.text}"
        data = response.json()
        assert "sales" in data or isinstance(data, list)
        print(f"PASSED: Quarterly sales report returned {len(data.get('sales', data))} records")
    
    def test_sales_report_yearly_filter(self, admin_token):
        """Test sales report with yearly period filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/sales?period=yearly", headers=headers)
        assert response.status_code == 200, f"Yearly sales report failed: {response.text}"
        data = response.json()
        assert "sales" in data or isinstance(data, list)
        print(f"PASSED: Yearly sales report returned {len(data.get('sales', data))} records")
    
    def test_sales_report_csv_export(self, admin_token):
        """Test sales report CSV export"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/sales?format=csv", headers=headers)
        assert response.status_code == 200, f"CSV export failed: {response.text}"
        # Check content type is CSV
        content_type = response.headers.get('content-type', '')
        assert 'text/csv' in content_type or 'application/octet-stream' in content_type, f"Expected CSV content type, got: {content_type}"
        print("PASSED: Sales report CSV export works")


class TestP1CommissionReport:
    """P1: Admin Commission Report with date filters and export"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{API}/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_commission_report_no_filter(self, admin_token):
        """Test commission report without filters (lifetime)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/partner-commissions", headers=headers)
        assert response.status_code == 200, f"Commission report failed: {response.text}"
        data = response.json()
        assert "commissions" in data or isinstance(data, list), "Response should contain commissions data"
        print(f"PASSED: Commission report returned data")
    
    def test_commission_report_weekly_filter(self, admin_token):
        """Test commission report with weekly period filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/partner-commissions?period=weekly", headers=headers)
        assert response.status_code == 200, f"Weekly commission report failed: {response.text}"
        print("PASSED: Weekly commission report filter works")
    
    def test_commission_report_monthly_filter(self, admin_token):
        """Test commission report with monthly period filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/partner-commissions?period=monthly", headers=headers)
        assert response.status_code == 200, f"Monthly commission report failed: {response.text}"
        print("PASSED: Monthly commission report filter works")
    
    def test_commission_report_quarterly_filter(self, admin_token):
        """Test commission report with quarterly period filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/partner-commissions?period=quarterly", headers=headers)
        assert response.status_code == 200, f"Quarterly commission report failed: {response.text}"
        print("PASSED: Quarterly commission report filter works")
    
    def test_commission_report_yearly_filter(self, admin_token):
        """Test commission report with yearly period filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/partner-commissions?period=yearly", headers=headers)
        assert response.status_code == 200, f"Yearly commission report failed: {response.text}"
        print("PASSED: Yearly commission report filter works")
    
    def test_commission_report_csv_export(self, admin_token):
        """Test commission report CSV export"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/reports/partner-commissions?format=csv", headers=headers)
        assert response.status_code == 200, f"CSV export failed: {response.text}"
        content_type = response.headers.get('content-type', '')
        assert 'text/csv' in content_type or 'application/octet-stream' in content_type, f"Expected CSV content type, got: {content_type}"
        print("PASSED: Commission report CSV export works")


class TestP2Notifications:
    """P2: Enhanced notification system"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{API}/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def client_token(self):
        response = requests.post(f"{API}/auth/login", json=CLIENT_CREDS)
        return response.json()["token"]
    
    def test_get_notifications(self, admin_token):
        """Test fetching notifications"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API}/notifications", headers=headers)
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Notifications should be a list"
        print(f"PASSED: Fetched {len(data)} notifications")
    
    def test_mark_notification_as_read(self, admin_token):
        """Test marking notification as read"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # First get notifications
        response = requests.get(f"{API}/notifications", headers=headers)
        notifications = response.json()
        
        if len(notifications) > 0:
            notification_id = notifications[0]["id"]
            # Mark as read
            response = requests.post(f"{API}/notifications/{notification_id}/read", headers=headers)
            assert response.status_code == 200, f"Mark as read failed: {response.text}"
            print("PASSED: Notification marked as read")
        else:
            print("SKIPPED: No notifications to mark as read")
    
    def test_notification_stream_endpoint_exists(self, admin_token):
        """Test that notification stream endpoint exists (SSE)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Just check the endpoint exists - SSE requires special handling
        response = requests.get(f"{API}/notifications/stream?token={admin_token}", stream=True, timeout=5)
        # SSE should return 200 and start streaming
        assert response.status_code == 200, f"SSE endpoint failed: {response.status_code}"
        response.close()
        print("PASSED: Notification stream endpoint exists")


class TestP3CaseManagerFeatures:
    """P3: Case Manager Pending Review and Document Search"""
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        response = requests.post(f"{API}/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    def test_get_my_cases(self, manager_token):
        """Test case manager can get their assigned cases"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{API}/cases/my-cases", headers=headers)
        assert response.status_code == 200, f"Get my cases failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Cases should be a list"
        print(f"PASSED: Case manager has {len(data)} assigned cases")
        return data
    
    def test_get_case_documents(self, manager_token):
        """Test fetching documents for a case"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        # First get cases
        cases_response = requests.get(f"{API}/cases/my-cases", headers=headers)
        cases = cases_response.json()
        
        if len(cases) > 0:
            case_id = cases[0]["id"]
            response = requests.get(f"{API}/documents/case/{case_id}", headers=headers)
            assert response.status_code == 200, f"Get case documents failed: {response.text}"
            data = response.json()
            assert isinstance(data, list), "Documents should be a list"
            print(f"PASSED: Case has {len(data)} documents")
        else:
            print("SKIPPED: No cases to check documents")
    
    def test_dashboard_stats(self, manager_token):
        """Test dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        response = requests.get(f"{API}/stats/dashboard", headers=headers)
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        print(f"PASSED: Dashboard stats returned: {data}")


class TestP4ModernUI:
    """P4: Verify API endpoints work for modernized dashboards"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{API}/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        response = requests.post(f"{API}/auth/login", json=MANAGER_CREDS)
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        response = requests.post(f"{API}/auth/login", json=PARTNER_CREDS)
        return response.json()["token"]
    
    def test_admin_dashboard_data(self, admin_token):
        """Test admin dashboard loads all required data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test all endpoints admin dashboard needs
        endpoints = [
            "/stats/dashboard",
            "/sales/pending",
            "/cases",
            "/products",
            "/users",
            "/tickets/all",
            "/tickets/stats",
            "/settings"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{API}{endpoint}", headers=headers)
            assert response.status_code == 200, f"Admin endpoint {endpoint} failed: {response.text}"
        
        print("PASSED: All admin dashboard endpoints work")
    
    def test_case_manager_dashboard_data(self, manager_token):
        """Test case manager dashboard loads all required data"""
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        endpoints = [
            "/stats/dashboard",
            "/cases/my-cases",
            "/settings"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{API}{endpoint}", headers=headers)
            assert response.status_code == 200, f"Manager endpoint {endpoint} failed: {response.text}"
        
        print("PASSED: All case manager dashboard endpoints work")
    
    def test_partner_dashboard_data(self, partner_token):
        """Test partner dashboard loads all required data"""
        headers = {"Authorization": f"Bearer {partner_token}"}
        
        endpoints = [
            "/stats/dashboard",
            "/sales/my-sales",
            "/products"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{API}{endpoint}", headers=headers)
            assert response.status_code == 200, f"Partner endpoint {endpoint} failed: {response.text}"
        
        print("PASSED: All partner dashboard endpoints work")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
