"""
Phase 10: Admin Superpowers - Backend API Tests
Tests for:
- 10A: Unified Approval Center
- 10B: Refund Manager Enhanced
- 10C: Revenue Dashboard Enhanced
- 10D: Custom Report Builder
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


class TestPhase10AdminSuperpowers:
    """Phase 10: Admin Superpowers API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.admin_token = login_response.json().get("token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Login as partner for permission tests
        partner_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARTNER_EMAIL,
            "password": PARTNER_PASSWORD
        })
        if partner_login.status_code == 200:
            self.partner_token = partner_login.json().get("token")
            self.partner_headers = {"Authorization": f"Bearer {self.partner_token}"}
        else:
            self.partner_token = None
            self.partner_headers = {}
    
    # ==================== 10A: UNIFIED APPROVAL CENTER ====================
    
    def test_approval_center_get_success(self):
        """10A: GET /api/admin-super/approval-center - Admin can access"""
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "items" in data, "Response should have 'items' array"
        assert "summary" in data, "Response should have 'summary' object"
        
        # Verify summary structure
        summary = data["summary"]
        assert "pending_sales" in summary, "Summary should have pending_sales count"
        assert "pending_pre_assessments" in summary, "Summary should have pending_pre_assessments count"
        assert "pending_documents" in summary, "Summary should have pending_documents count"
        assert "urgent_tickets" in summary, "Summary should have urgent_tickets count"
        assert "total" in summary, "Summary should have total count"
        
        # Verify items structure (if any exist)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item, "Item should have id"
            assert "type" in item, "Item should have type"
            assert "title" in item, "Item should have title"
            assert item["type"] in ["sale", "pre_assessment", "document", "ticket"], f"Invalid item type: {item['type']}"
        
        print(f"✓ Approval Center: {summary['total']} total items ({summary['pending_sales']} sales, {summary['pending_pre_assessments']} PAs, {summary['pending_documents']} docs, {summary['urgent_tickets']} tickets)")
    
    def test_approval_center_partner_forbidden(self):
        """10A: Partner should NOT access approval center"""
        if not self.partner_token:
            pytest.skip("Partner login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/approval-center",
            headers=self.partner_headers
        )
        assert response.status_code == 403, f"Expected 403 for partner, got {response.status_code}"
        print("✓ Approval Center correctly blocks non-admin access")
    
    # ==================== 10B: REFUND MANAGER ENHANCED ====================
    
    def test_refund_manager_get_success(self):
        """10B: GET /api/admin-super/refund-manager - Admin can access"""
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/refund-manager",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "refunds" in data, "Response should have 'refunds' array"
        assert "pa_refunds_pending" in data, "Response should have 'pa_refunds_pending' array"
        assert "eligible_for_refund" in data, "Response should have 'eligible_for_refund' array"
        assert "stats" in data, "Response should have 'stats' object"
        assert "monthly_trend" in data, "Response should have 'monthly_trend' array"
        
        # Verify stats structure
        stats = data["stats"]
        assert "total_refunded" in stats, "Stats should have total_refunded"
        assert "total_count" in stats, "Stats should have total_count"
        assert "pa_pending_count" in stats, "Stats should have pa_pending_count"
        assert "pa_pending_amount" in stats, "Stats should have pa_pending_amount"
        
        print(f"✓ Refund Manager: {stats['total_count']} refunds (₹{stats['total_refunded']}), {stats['pa_pending_count']} PA refunds pending")
    
    def test_refund_manager_partner_forbidden(self):
        """10B: Partner should NOT access refund manager"""
        if not self.partner_token:
            pytest.skip("Partner login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/refund-manager",
            headers=self.partner_headers
        )
        assert response.status_code == 403, f"Expected 403 for partner, got {response.status_code}"
        print("✓ Refund Manager correctly blocks non-admin access")
    
    # ==================== 10C: REVENUE DASHBOARD ENHANCED ====================
    
    def test_revenue_dashboard_get_success(self):
        """10C: GET /api/admin-super/revenue-dashboard - Admin can access"""
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/revenue-dashboard",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "summary" in data, "Response should have 'summary' object"
        assert "monthly_trend" in data, "Response should have 'monthly_trend' array"
        assert "by_partner" in data, "Response should have 'by_partner' array"
        assert "by_product" in data, "Response should have 'by_product' array"
        assert "payment_methods" in data, "Response should have 'payment_methods' array"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_revenue" in summary, "Summary should have total_revenue"
        assert "total_received" in summary, "Summary should have total_received"
        assert "total_pending" in summary, "Summary should have total_pending"
        assert "total_commission" in summary, "Summary should have total_commission"
        assert "total_refunded" in summary, "Summary should have total_refunded"
        assert "net_revenue" in summary, "Summary should have net_revenue"
        assert "pa_revenue" in summary, "Summary should have pa_revenue"
        assert "total_sales" in summary, "Summary should have total_sales"
        
        print(f"✓ Revenue Dashboard: ₹{summary['total_revenue']} total, ₹{summary['total_received']} received, ₹{summary['net_revenue']} net")
    
    def test_revenue_dashboard_partner_forbidden(self):
        """10C: Partner should NOT access revenue dashboard"""
        if not self.partner_token:
            pytest.skip("Partner login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/revenue-dashboard",
            headers=self.partner_headers
        )
        assert response.status_code == 403, f"Expected 403 for partner, got {response.status_code}"
        print("✓ Revenue Dashboard correctly blocks non-admin access")
    
    # ==================== 10D: CUSTOM REPORT BUILDER ====================
    
    def test_report_templates_get_success(self):
        """10D: GET /api/admin-super/report-templates - Admin can access"""
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/report-templates",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list of templates"
        assert len(data) >= 6, f"Expected at least 6 templates, got {len(data)}"
        
        # Verify template structure
        template_ids = [t["id"] for t in data]
        expected_templates = ["revenue_summary", "partner_performance", "case_status", "client_list", "pre_assessment_report", "refund_report"]
        for expected in expected_templates:
            assert expected in template_ids, f"Missing template: {expected}"
        
        # Verify template fields
        for template in data:
            assert "id" in template, "Template should have id"
            assert "name" in template, "Template should have name"
            assert "description" in template, "Template should have description"
            assert "report_type" in template, "Template should have report_type"
            assert "icon" in template, "Template should have icon"
        
        print(f"✓ Report Templates: {len(data)} templates available ({', '.join(template_ids)})")
    
    def test_report_builder_generate_revenue(self):
        """10D: POST /api/admin-super/report-builder/generate - Revenue report"""
        response = self.session.post(
            f"{BASE_URL}/api/admin-super/report-builder/generate",
            headers=self.admin_headers,
            json={"report_type": "revenue"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "title" in data, "Report should have title"
        assert "rows" in data, "Report should have rows"
        assert "summary" in data, "Report should have summary"
        assert "columns" in data, "Report should have columns"
        
        assert data["title"] == "Revenue Report", f"Expected 'Revenue Report', got '{data['title']}'"
        assert isinstance(data["rows"], list), "Rows should be a list"
        assert isinstance(data["columns"], list), "Columns should be a list"
        
        # Verify summary fields
        summary = data["summary"]
        assert "total_fee" in summary, "Summary should have total_fee"
        assert "total_received" in summary, "Summary should have total_received"
        assert "record_count" in summary, "Summary should have record_count"
        
        print(f"✓ Revenue Report: {summary['record_count']} records, ₹{summary['total_fee']} total fee")
    
    def test_report_builder_generate_cases(self):
        """10D: POST /api/admin-super/report-builder/generate - Cases report"""
        response = self.session.post(
            f"{BASE_URL}/api/admin-super/report-builder/generate",
            headers=self.admin_headers,
            json={"report_type": "cases"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == "Case Status Report", f"Expected 'Case Status Report', got '{data['title']}'"
        
        summary = data["summary"]
        assert "total" in summary, "Summary should have total"
        assert "active" in summary, "Summary should have active count"
        assert "completed" in summary, "Summary should have completed count"
        
        print(f"✓ Cases Report: {summary['total']} total ({summary['active']} active, {summary['completed']} completed)")
    
    def test_report_builder_generate_partners(self):
        """10D: POST /api/admin-super/report-builder/generate - Partners report"""
        response = self.session.post(
            f"{BASE_URL}/api/admin-super/report-builder/generate",
            headers=self.admin_headers,
            json={"report_type": "partners"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == "Partner Performance Report", f"Expected 'Partner Performance Report', got '{data['title']}'"
        
        summary = data["summary"]
        assert "total_partners" in summary, "Summary should have total_partners"
        assert "total_revenue" in summary, "Summary should have total_revenue"
        assert "total_commission" in summary, "Summary should have total_commission"
        
        print(f"✓ Partners Report: {summary['total_partners']} partners, ₹{summary['total_revenue']} revenue")
    
    def test_report_builder_generate_clients(self):
        """10D: POST /api/admin-super/report-builder/generate - Clients report"""
        response = self.session.post(
            f"{BASE_URL}/api/admin-super/report-builder/generate",
            headers=self.admin_headers,
            json={"report_type": "clients"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == "Client Directory Report", f"Expected 'Client Directory Report', got '{data['title']}'"
        
        summary = data["summary"]
        assert "total_clients" in summary, "Summary should have total_clients"
        
        print(f"✓ Clients Report: {summary['total_clients']} clients")
    
    def test_report_builder_generate_pre_assessments(self):
        """10D: POST /api/admin-super/report-builder/generate - Pre-assessments report"""
        response = self.session.post(
            f"{BASE_URL}/api/admin-super/report-builder/generate",
            headers=self.admin_headers,
            json={"report_type": "pre_assessments"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == "Pre-Assessment Pipeline Report", f"Expected 'Pre-Assessment Pipeline Report', got '{data['title']}'"
        
        summary = data["summary"]
        assert "total" in summary, "Summary should have total"
        assert "approved" in summary, "Summary should have approved count"
        assert "rejected" in summary, "Summary should have rejected count"
        assert "pending" in summary, "Summary should have pending count"
        
        print(f"✓ Pre-Assessments Report: {summary['total']} total ({summary['approved']} approved, {summary['rejected']} rejected, {summary['pending']} pending)")
    
    def test_report_builder_generate_refunds(self):
        """10D: POST /api/admin-super/report-builder/generate - Refunds report"""
        response = self.session.post(
            f"{BASE_URL}/api/admin-super/report-builder/generate",
            headers=self.admin_headers,
            json={"report_type": "refunds"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == "Refund Report", f"Expected 'Refund Report', got '{data['title']}'"
        
        summary = data["summary"]
        assert "total_refunds" in summary, "Summary should have total_refunds"
        assert "total_amount" in summary, "Summary should have total_amount"
        
        print(f"✓ Refunds Report: {summary['total_refunds']} refunds, ₹{summary['total_amount']} total")
    
    def test_report_builder_invalid_type(self):
        """10D: POST /api/admin-super/report-builder/generate - Invalid type returns 400"""
        response = self.session.post(
            f"{BASE_URL}/api/admin-super/report-builder/generate",
            headers=self.admin_headers,
            json={"report_type": "invalid_type"}
        )
        assert response.status_code == 400, f"Expected 400 for invalid type, got {response.status_code}"
        print("✓ Report Builder correctly rejects invalid report type")
    
    def test_report_templates_partner_forbidden(self):
        """10D: Partner should NOT access report templates"""
        if not self.partner_token:
            pytest.skip("Partner login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/admin-super/report-templates",
            headers=self.partner_headers
        )
        assert response.status_code == 403, f"Expected 403 for partner, got {response.status_code}"
        print("✓ Report Templates correctly blocks non-admin access")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
