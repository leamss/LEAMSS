"""
Iteration 51: Analytics Priority 3-6 Tests
- Currency Fix: ₹ instead of $ (frontend verification)
- Revenue Forecast API with real data
- Commission Analytics API with partner breakdown
- Country/Product Analytics with partner drill-down
- Revenue Dashboard with By Currency tab
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAnalyticsAPIs:
    """Test analytics endpoints for Priority 3-6 features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as admin
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        self.token = login_res.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    # ============ Revenue Forecast Tests ============
    
    def test_revenue_forecast_returns_data(self):
        """Revenue Forecast API returns historical and forecast data"""
        res = self.session.get(f"{BASE_URL}/api/analytics/revenue-forecast?months=6")
        assert res.status_code == 200
        data = res.json()
        
        # Verify structure
        assert "historical" in data
        assert "forecast" in data
        assert "summary" in data
        
        # Verify summary fields
        summary = data["summary"]
        assert "avg_monthly" in summary
        assert "growth_rate" in summary
        assert "trend" in summary
        assert "pipeline_value" in summary
        assert "total_active_cases" in summary
        assert "pa_revenue" in summary
        assert "total_approved_revenue" in summary
    
    def test_revenue_forecast_has_real_data(self):
        """Revenue Forecast uses real approved sales data (fee_amount field)"""
        res = self.session.get(f"{BASE_URL}/api/analytics/revenue-forecast?months=6")
        assert res.status_code == 200
        data = res.json()
        
        # Should have historical data with revenue > 0
        historical = data.get("historical", [])
        if historical:
            total_historical = sum(h.get("revenue", 0) for h in historical)
            assert total_historical > 0, "Historical revenue should be > 0 with approved sales"
        
        # Summary avg_monthly should be > 0
        assert data["summary"]["avg_monthly"] > 0, "Avg monthly revenue should be > 0"
    
    def test_revenue_forecast_trend_values(self):
        """Revenue Forecast trend is one of: growing, declining, stable"""
        res = self.session.get(f"{BASE_URL}/api/analytics/revenue-forecast?months=6")
        assert res.status_code == 200
        data = res.json()
        
        trend = data["summary"].get("trend", "")
        assert trend in ["growing", "declining", "stable"], f"Invalid trend: {trend}"
    
    # ============ Commission Analytics Tests ============
    
    def test_commission_analytics_returns_data(self):
        """Commission Analytics API returns partner breakdown"""
        res = self.session.get(f"{BASE_URL}/api/analytics/commission-analytics")
        assert res.status_code == 200
        data = res.json()
        
        # Verify structure
        assert "partners" in data
        assert "total_commission" in data
        assert "monthly_trend" in data
    
    def test_commission_analytics_partner_breakdown(self):
        """Commission Analytics shows per-partner commission amounts"""
        res = self.session.get(f"{BASE_URL}/api/analytics/commission-analytics")
        assert res.status_code == 200
        data = res.json()
        
        partners = data.get("partners", [])
        assert len(partners) > 0, "Should have at least one partner"
        
        # Verify partner fields
        for p in partners:
            assert "partner_id" in p
            assert "partner_name" in p
            assert "total_commission" in p
            assert "total_sales" in p
            assert "total_revenue" in p
    
    def test_commission_analytics_total_matches_sum(self):
        """Total commission matches sum of partner commissions"""
        res = self.session.get(f"{BASE_URL}/api/analytics/commission-analytics")
        assert res.status_code == 200
        data = res.json()
        
        partners = data.get("partners", [])
        sum_commission = sum(p.get("total_commission", 0) for p in partners)
        total_commission = data.get("total_commission", 0)
        
        # Allow small floating point difference
        assert abs(sum_commission - total_commission) < 0.01, \
            f"Sum {sum_commission} != Total {total_commission}"
    
    def test_commission_analytics_monthly_trend(self):
        """Commission Analytics includes monthly trend data"""
        res = self.session.get(f"{BASE_URL}/api/analytics/commission-analytics")
        assert res.status_code == 200
        data = res.json()
        
        trend = data.get("monthly_trend", [])
        if trend:
            for t in trend:
                assert "month" in t
                assert "commission" in t
    
    # ============ Country/Product Analytics Tests ============
    
    def test_country_product_returns_data(self):
        """Country/Product Analytics API returns both breakdowns"""
        res = self.session.get(f"{BASE_URL}/api/analytics/country-product")
        assert res.status_code == 200
        data = res.json()
        
        assert "by_product" in data
        assert "by_country" in data
    
    def test_country_product_has_partner_drilldown(self):
        """Country/Product Analytics includes partner drill-down"""
        res = self.session.get(f"{BASE_URL}/api/analytics/country-product")
        assert res.status_code == 200
        data = res.json()
        
        # Check by_country has partners array
        by_country = data.get("by_country", [])
        if by_country:
            for country in by_country:
                assert "partners" in country, f"Country {country.get('country')} missing partners"
                assert isinstance(country["partners"], list)
        
        # Check by_product has partners array
        by_product = data.get("by_product", [])
        if by_product:
            for product in by_product:
                assert "partners" in product, f"Product {product.get('name')} missing partners"
                assert isinstance(product["partners"], list)
    
    def test_country_product_partner_fields(self):
        """Partner drill-down has required fields: sales, revenue, received, commission"""
        res = self.session.get(f"{BASE_URL}/api/analytics/country-product")
        assert res.status_code == 200
        data = res.json()
        
        by_country = data.get("by_country", [])
        for country in by_country:
            for partner in country.get("partners", []):
                assert "name" in partner
                assert "sales" in partner
                assert "revenue" in partner
                assert "received" in partner
                assert "commission" in partner
    
    def test_country_product_revenue_received_commission(self):
        """Country/Product items have revenue, received, commission fields"""
        res = self.session.get(f"{BASE_URL}/api/analytics/country-product")
        assert res.status_code == 200
        data = res.json()
        
        for country in data.get("by_country", []):
            assert "revenue" in country
            assert "received" in country
            assert "commission" in country
            assert "total_sales" in country
        
        for product in data.get("by_product", []):
            assert "revenue" in product
            assert "received" in product
            assert "commission" in product
            assert "total_sales" in product
    
    # ============ Revenue Dashboard Tests ============
    
    def test_revenue_dashboard_returns_data(self):
        """Revenue Dashboard API returns comprehensive data"""
        res = self.session.get(f"{BASE_URL}/api/admin-super/revenue-dashboard")
        assert res.status_code == 200
        data = res.json()
        
        assert "summary" in data
        assert "monthly_trend" in data
        assert "by_partner" in data
        assert "by_product" in data
        assert "payment_methods" in data
    
    def test_revenue_dashboard_has_by_currency(self):
        """Revenue Dashboard includes by_currency breakdown"""
        res = self.session.get(f"{BASE_URL}/api/admin-super/revenue-dashboard")
        assert res.status_code == 200
        data = res.json()
        
        assert "by_currency" in data, "Missing by_currency field"
        by_currency = data["by_currency"]
        assert isinstance(by_currency, list)
        
        # Should have at least INR
        if by_currency:
            for c in by_currency:
                assert "currency" in c
                assert "label" in c
                assert "count" in c
                assert "revenue" in c
                assert "received" in c
    
    def test_revenue_dashboard_summary_fields(self):
        """Revenue Dashboard summary has all required fields"""
        res = self.session.get(f"{BASE_URL}/api/admin-super/revenue-dashboard")
        assert res.status_code == 200
        data = res.json()
        
        summary = data["summary"]
        required_fields = [
            "total_revenue", "total_received", "total_pending",
            "total_commission", "total_refunded", "net_revenue",
            "pa_revenue", "total_sales"
        ]
        for field in required_fields:
            assert field in summary, f"Missing summary field: {field}"
    
    # ============ Authorization Tests ============
    
    def test_revenue_forecast_requires_auth(self):
        """Revenue Forecast requires authentication"""
        session = requests.Session()
        res = session.get(f"{BASE_URL}/api/analytics/revenue-forecast")
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"
    
    def test_commission_analytics_requires_auth(self):
        """Commission Analytics requires authentication"""
        session = requests.Session()
        res = session.get(f"{BASE_URL}/api/analytics/commission-analytics")
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"
    
    def test_country_product_requires_auth(self):
        """Country/Product Analytics requires authentication"""
        session = requests.Session()
        res = session.get(f"{BASE_URL}/api/analytics/country-product")
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"
    
    def test_revenue_dashboard_admin_only(self):
        """Revenue Dashboard is admin only"""
        # Login as partner
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        login_res = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@leamss.com",
            "password": "Partner@123"
        })
        if login_res.status_code == 200:
            token = login_res.json().get("token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            res = session.get(f"{BASE_URL}/api/admin-super/revenue-dashboard")
            assert res.status_code == 403, "Partner should not access revenue dashboard"


class TestAnalyticsDashboard:
    """Test general analytics dashboard endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@leamss.com",
            "password": "Admin@123"
        })
        assert login_res.status_code == 200
        self.token = login_res.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_analytics_dashboard_endpoint(self):
        """Analytics dashboard returns summary data"""
        res = self.session.get(f"{BASE_URL}/api/analytics/dashboard?days=30")
        assert res.status_code == 200
        data = res.json()
        
        assert "total_revenue" in data
        assert "total_commission" in data
        assert "total_sales" in data
        assert "completion_rate" in data
