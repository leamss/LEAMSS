"""
Iteration 71: Automated Government Fee Calculator Tests
-------------------------------------------------------
Tests for the fee calculator endpoints:
- GET /api/fee-calculator/countries - List 20 supported countries
- GET /api/fee-calculator/country/{country_id} - Full fee detail per visa category
- GET /api/fee-calculator/exchange-rates - Live/static exchange rates
- POST /api/fee-calculator/calculate - Compute fee breakdown with math validation
- POST /api/fee-calculator/save-estimate - Persist estimate
- GET /api/fee-calculator/estimates - List estimates with filters
- DELETE /api/fee-calculator/estimates/{id} - Delete estimate (creator/admin only)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
MANAGER_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if resp.status_code == 200:
        return resp.json().get("token")
    pytest.skip("Admin login failed")


@pytest.fixture(scope="module")
def manager_token():
    """Get case manager auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    if resp.status_code == 200:
        return resp.json().get("token")
    pytest.skip("Manager login failed")


@pytest.fixture(scope="module")
def partner_token():
    """Get partner auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
    if resp.status_code == 200:
        return resp.json().get("token")
    pytest.skip("Partner login failed")


@pytest.fixture(scope="module")
def client_token():
    """Get client auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    if resp.status_code == 200:
        return resp.json().get("token")
    pytest.skip("Client login failed")


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# TEST: Auth required on all endpoints (401/403 without token)
# ============================================================================
class TestAuthRequired:
    """All fee calculator endpoints require authentication"""

    def test_countries_requires_auth(self):
        """GET /api/fee-calculator/countries returns 401/403 without token"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/countries")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_country_detail_requires_auth(self):
        """GET /api/fee-calculator/country/{id} returns 401/403 without token"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/country/canada")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_exchange_rates_requires_auth(self):
        """GET /api/fee-calculator/exchange-rates returns 401/403 without token"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/exchange-rates")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_calculate_requires_auth(self):
        """POST /api/fee-calculator/calculate returns 401/403 without token"""
        resp = requests.post(f"{BASE_URL}/api/fee-calculator/calculate", json={
            "country": "canada", "category": "express_entry_pr", "adults": 1, "children": 0
        })
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_save_estimate_requires_auth(self):
        """POST /api/fee-calculator/save-estimate returns 401/403 without token"""
        resp = requests.post(f"{BASE_URL}/api/fee-calculator/save-estimate", json={
            "label": "Test", "country": "canada", "category": "express_entry_pr", "payload": {}
        })
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_list_estimates_requires_auth(self):
        """GET /api/fee-calculator/estimates returns 401/403 without token"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/estimates")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_delete_estimate_requires_auth(self):
        """DELETE /api/fee-calculator/estimates/{id} returns 401/403 without token"""
        resp = requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/some-id")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"


# ============================================================================
# TEST: GET /api/fee-calculator/countries
# ============================================================================
class TestListCountries:
    """Test listing all supported countries"""

    def test_list_countries_returns_20(self, admin_token):
        """Returns 20 supported countries with flag, currency, categories"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/countries", headers=auth_header(admin_token))
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "countries" in data
        assert "total" in data
        assert data["total"] == 20, f"Expected 20 countries, got {data['total']}"
        
        # Validate structure of first country
        country = data["countries"][0]
        assert "id" in country
        assert "name" in country
        assert "flag" in country
        assert "currency" in country
        assert "categories" in country
        assert isinstance(country["categories"], list)
        
        # Check category structure
        if country["categories"]:
            cat = country["categories"][0]
            assert "id" in cat
            assert "name" in cat
            assert "processing_days" in cat
            assert "official_url" in cat

    def test_list_countries_all_roles(self, admin_token, manager_token, partner_token, client_token):
        """All roles can access countries list"""
        for token, role in [(admin_token, "admin"), (manager_token, "manager"), 
                            (partner_token, "partner"), (client_token, "client")]:
            resp = requests.get(f"{BASE_URL}/api/fee-calculator/countries", headers=auth_header(token))
            assert resp.status_code == 200, f"{role} should access countries, got {resp.status_code}"


# ============================================================================
# TEST: GET /api/fee-calculator/country/{country_id}
# ============================================================================
class TestCountryDetail:
    """Test getting full fee detail for a country"""

    def test_canada_detail(self, admin_token):
        """Canada returns full fee detail with express_entry_pr category"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/country/canada", headers=auth_header(admin_token))
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        data = resp.json()
        assert data["id"] == "canada"
        assert data["name"] == "Canada"
        assert data["currency"] == "CAD"
        assert "categories" in data
        assert "express_entry_pr" in data["categories"]
        
        # Check express_entry_pr fees
        ee = data["categories"]["express_entry_pr"]
        assert ee["name"] == "Express Entry — Permanent Residence"
        assert "fees" in ee
        assert len(ee["fees"]) >= 6  # At least 6 fee items

    def test_australia_detail(self, admin_token):
        """Australia returns full fee detail"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/country/australia", headers=auth_header(admin_token))
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["id"] == "australia"
        assert data["currency"] == "AUD"
        assert "skilled_independent_189" in data["categories"]

    def test_uk_detail(self, admin_token):
        """UK returns full fee detail"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/country/uk", headers=auth_header(admin_token))
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["id"] == "uk"
        assert data["currency"] == "GBP"
        assert "skilled_worker" in data["categories"]

    def test_usa_detail(self, admin_token):
        """USA returns full fee detail"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/country/usa", headers=auth_header(admin_token))
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["id"] == "usa"
        assert data["currency"] == "USD"
        assert "h1b" in data["categories"]

    def test_invalid_country_returns_404(self, admin_token):
        """Invalid country returns 404"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/country/invalid_country", headers=auth_header(admin_token))
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ============================================================================
# TEST: GET /api/fee-calculator/exchange-rates
# ============================================================================
class TestExchangeRates:
    """Test exchange rates endpoint"""

    def test_exchange_rates_structure(self, admin_token):
        """Returns rates from frankfurter.dev or static fallback"""
        resp = requests.get(f"{BASE_URL}/api/fee-calculator/exchange-rates", headers=auth_header(admin_token))
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        data = resp.json()
        assert "base" in data
        assert data["base"] == "INR"
        assert "rates" in data
        assert "source" in data
        
        # Check required currencies exist
        rates = data["rates"]
        required_currencies = ["USD", "CAD", "AUD", "GBP", "EUR", "NZD", "SGD", "INR"]
        for cur in required_currencies:
            assert cur in rates, f"Missing currency: {cur}"
            assert rates[cur] > 0, f"Rate for {cur} should be positive"
        
        # INR should be 1.0
        assert rates["INR"] == 1.0


# ============================================================================
# TEST: POST /api/fee-calculator/calculate - Math validation
# ============================================================================
class TestCalculateFees:
    """Test fee calculation with math validation"""

    def test_canada_express_entry_2_adults_1_child(self, admin_token):
        """
        Canada Express Entry: 2 adults + 1 child + service_fee=150000 + gst=18%
        Validates math: mandatory_native + optional_selected_native = govt_fees_native
        """
        payload = {
            "country": "canada",
            "category": "express_entry_pr",
            "adults": 2,
            "children": 1,
            "include_optional_ids": [],  # Mandatory only
            "service_fee_inr": 150000,
            "gst_pct": 18.0
        }
        resp = requests.post(f"{BASE_URL}/api/fee-calculator/calculate", 
                            json=payload, headers=auth_header(admin_token))
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        
        # Validate structure
        assert data["country"]["id"] == "canada"
        assert data["country"]["currency"] == "CAD"
        assert data["category"]["id"] == "express_entry_pr"
        assert data["applicants"]["adults"] == 2
        assert data["applicants"]["children"] == 1
        assert data["applicants"]["total"] == 3
        
        # Validate exchange rate
        fx_rate = data["exchange_rate"]["native_to_inr"]
        assert fx_rate > 0, "Exchange rate should be positive"
        
        # Validate line items
        assert "line_items" in data
        assert len(data["line_items"]) > 0
        
        # Validate totals structure
        totals = data["totals"]
        assert "govt_fees_native" in totals
        assert "govt_fees_inr" in totals
        assert "mandatory_native" in totals
        assert "mandatory_inr" in totals
        assert "optional_selected_native" in totals
        assert "optional_selected_inr" in totals
        assert "service_fee_inr" in totals
        assert "gst_pct" in totals
        assert "gst_amount_inr" in totals
        assert "service_total_inr" in totals
        assert "grand_total_inr" in totals
        
        # Math validation: mandatory_native + optional_selected_native = govt_fees_native
        assert abs(totals["mandatory_native"] + totals["optional_selected_native"] - totals["govt_fees_native"]) < 0.01, \
            f"Math error: {totals['mandatory_native']} + {totals['optional_selected_native']} != {totals['govt_fees_native']}"
        
        # Math validation: govt_fees_inr = govt_fees_native * fx_rate
        expected_govt_inr = round(totals["govt_fees_native"] * fx_rate, 2)
        assert abs(totals["govt_fees_inr"] - expected_govt_inr) < 1, \
            f"Math error: govt_fees_inr {totals['govt_fees_inr']} != {expected_govt_inr}"
        
        # Math validation: service_total_inr = service_fee_inr + gst_amount_inr
        expected_service_total = totals["service_fee_inr"] + totals["gst_amount_inr"]
        assert abs(totals["service_total_inr"] - expected_service_total) < 0.01, \
            f"Math error: service_total_inr {totals['service_total_inr']} != {expected_service_total}"
        
        # Math validation: gst_amount_inr = service_fee_inr * gst_pct / 100
        expected_gst = round(totals["service_fee_inr"] * totals["gst_pct"] / 100, 2)
        assert abs(totals["gst_amount_inr"] - expected_gst) < 0.01, \
            f"Math error: gst_amount_inr {totals['gst_amount_inr']} != {expected_gst}"
        
        # Math validation: grand_total_inr = govt_fees_inr + service_total_inr
        expected_grand = round(totals["govt_fees_inr"] + totals["service_total_inr"], 2)
        assert abs(totals["grand_total_inr"] - expected_grand) < 1, \
            f"Math error: grand_total_inr {totals['grand_total_inr']} != {expected_grand}"
        
        print(f"Canada Express Entry 2+1: govt_fees_native={totals['govt_fees_native']} CAD, "
              f"govt_fees_inr={totals['govt_fees_inr']}, grand_total_inr={totals['grand_total_inr']}")

    def test_mandatory_only_flow(self, admin_token):
        """Test calculation with mandatory fees only (no optionals selected)"""
        payload = {
            "country": "canada",
            "category": "express_entry_pr",
            "adults": 1,
            "children": 0,
            "include_optional_ids": [],
            "service_fee_inr": 0,
            "gst_pct": 0
        }
        resp = requests.post(f"{BASE_URL}/api/fee-calculator/calculate", 
                            json=payload, headers=auth_header(admin_token))
        assert resp.status_code == 200
        
        data = resp.json()
        totals = data["totals"]
        
        # With no optionals selected, optional_selected_native should be 0
        assert totals["optional_selected_native"] == 0, "No optionals selected, should be 0"
        
        # govt_fees_native should equal mandatory_native
        assert totals["govt_fees_native"] == totals["mandatory_native"], \
            "With no optionals, govt_fees should equal mandatory"

    def test_optional_selection_via_include_optional_ids(self, admin_token):
        """Test selecting optional fees via include_optional_ids"""
        # First get the fee structure to find optional fee IDs
        country_resp = requests.get(f"{BASE_URL}/api/fee-calculator/country/canada", 
                                    headers=auth_header(admin_token))
        country_data = country_resp.json()
        
        # Find optional fees in express_entry_pr
        ee_fees = country_data["categories"]["express_entry_pr"]["fees"]
        optional_labels = [f["label"] for f in ee_fees if not f.get("mandatory", True)]
        
        if optional_labels:
            # Include first optional by label
            payload = {
                "country": "canada",
                "category": "express_entry_pr",
                "adults": 1,
                "children": 0,
                "include_optional_ids": [optional_labels[0]],  # Include by label
                "service_fee_inr": 0,
                "gst_pct": 0
            }
            resp = requests.post(f"{BASE_URL}/api/fee-calculator/calculate", 
                                json=payload, headers=auth_header(admin_token))
            assert resp.status_code == 200
            
            data = resp.json()
            totals = data["totals"]
            
            # With optional selected, optional_selected_native should be > 0
            assert totals["optional_selected_native"] > 0, "Optional selected, should be > 0"
            print(f"Optional selected: {optional_labels[0]}, amount: {totals['optional_selected_native']}")

    def test_per_applicant_multiplier(self, admin_token):
        """Test that per_applicant=true multiplies by (adults+children)"""
        # Test with 1 applicant
        payload_1 = {
            "country": "canada",
            "category": "express_entry_pr",
            "adults": 1,
            "children": 0,
            "include_optional_ids": [],
            "service_fee_inr": 0,
            "gst_pct": 0
        }
        resp_1 = requests.post(f"{BASE_URL}/api/fee-calculator/calculate", 
                              json=payload_1, headers=auth_header(admin_token))
        data_1 = resp_1.json()
        
        # Test with 3 applicants
        payload_3 = {
            "country": "canada",
            "category": "express_entry_pr",
            "adults": 2,
            "children": 1,
            "include_optional_ids": [],
            "service_fee_inr": 0,
            "gst_pct": 0
        }
        resp_3 = requests.post(f"{BASE_URL}/api/fee-calculator/calculate", 
                              json=payload_3, headers=auth_header(admin_token))
        data_3 = resp_3.json()
        
        # Find a per_applicant=true fee and verify multiplier
        for item_1, item_3 in zip(data_1["line_items"], data_3["line_items"]):
            if item_1["per_applicant"]:
                assert item_1["multiplier"] == 1, f"1 applicant should have multiplier 1"
                assert item_3["multiplier"] == 3, f"3 applicants should have multiplier 3"
                assert item_3["total_native"] == item_1["amount_native"] * 3, \
                    f"Total should be amount * 3 for per_applicant fees"
                break

    def test_bad_country_returns_404(self, admin_token):
        """Invalid country returns 404"""
        payload = {
            "country": "invalid_country",
            "category": "express_entry_pr",
            "adults": 1,
            "children": 0
        }
        resp = requests.post(f"{BASE_URL}/api/fee-calculator/calculate", 
                            json=payload, headers=auth_header(admin_token))
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_bad_category_returns_404(self, admin_token):
        """Invalid category returns 404"""
        payload = {
            "country": "canada",
            "category": "invalid_category",
            "adults": 1,
            "children": 0
        }
        resp = requests.post(f"{BASE_URL}/api/fee-calculator/calculate", 
                            json=payload, headers=auth_header(admin_token))
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ============================================================================
# TEST: POST /api/fee-calculator/save-estimate & GET /api/fee-calculator/estimates
# ============================================================================
class TestSaveAndListEstimates:
    """Test saving and listing estimates"""

    def test_save_estimate_and_list(self, admin_token):
        """Save estimate and verify it appears in list"""
        unique_label = f"TEST_Estimate_{uuid.uuid4().hex[:8]}"
        
        # Save estimate
        payload = {
            "label": unique_label,
            "country": "canada",
            "category": "express_entry_pr",
            "payload": {"adults": 2, "children": 1, "grand_total_inr": 692289},
            "case_id": None,
            "sale_id": None
        }
        save_resp = requests.post(f"{BASE_URL}/api/fee-calculator/save-estimate", 
                                  json=payload, headers=auth_header(admin_token))
        assert save_resp.status_code == 200, f"Expected 200, got {save_resp.status_code}: {save_resp.text}"
        
        saved = save_resp.json()
        assert saved["label"] == unique_label
        assert saved["country"] == "canada"
        assert saved["category"] == "express_entry_pr"
        assert "id" in saved
        assert "created_by" in saved
        assert "created_at" in saved
        
        estimate_id = saved["id"]
        
        # List estimates and verify it's there
        list_resp = requests.get(f"{BASE_URL}/api/fee-calculator/estimates", 
                                 headers=auth_header(admin_token))
        assert list_resp.status_code == 200
        
        list_data = list_resp.json()
        assert "estimates" in list_data
        
        found = any(e["id"] == estimate_id for e in list_data["estimates"])
        assert found, f"Saved estimate {estimate_id} not found in list"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/{estimate_id}", 
                       headers=auth_header(admin_token))

    def test_list_estimates_with_case_id_filter(self, admin_token):
        """Test filtering estimates by case_id"""
        test_case_id = f"TEST_CASE_{uuid.uuid4().hex[:8]}"
        unique_label = f"TEST_Estimate_{uuid.uuid4().hex[:8]}"
        
        # Save estimate with case_id
        payload = {
            "label": unique_label,
            "country": "australia",
            "category": "skilled_independent_189",
            "payload": {"test": True},
            "case_id": test_case_id
        }
        save_resp = requests.post(f"{BASE_URL}/api/fee-calculator/save-estimate", 
                                  json=payload, headers=auth_header(admin_token))
        assert save_resp.status_code == 200
        estimate_id = save_resp.json()["id"]
        
        # Filter by case_id
        filter_resp = requests.get(f"{BASE_URL}/api/fee-calculator/estimates?case_id={test_case_id}", 
                                   headers=auth_header(admin_token))
        assert filter_resp.status_code == 200
        
        filter_data = filter_resp.json()
        assert len(filter_data["estimates"]) >= 1
        assert all(e["case_id"] == test_case_id for e in filter_data["estimates"])
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/{estimate_id}", 
                       headers=auth_header(admin_token))


# ============================================================================
# TEST: DELETE /api/fee-calculator/estimates/{id} - Authorization
# ============================================================================
class TestDeleteEstimate:
    """Test delete estimate authorization"""

    def test_creator_can_delete_own_estimate(self, partner_token):
        """Creator can delete their own estimate"""
        unique_label = f"TEST_Partner_Estimate_{uuid.uuid4().hex[:8]}"
        
        # Partner creates estimate
        payload = {
            "label": unique_label,
            "country": "uk",
            "category": "skilled_worker",
            "payload": {"test": True}
        }
        save_resp = requests.post(f"{BASE_URL}/api/fee-calculator/save-estimate", 
                                  json=payload, headers=auth_header(partner_token))
        assert save_resp.status_code == 200
        estimate_id = save_resp.json()["id"]
        
        # Partner deletes own estimate
        del_resp = requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/{estimate_id}", 
                                   headers=auth_header(partner_token))
        assert del_resp.status_code == 200, f"Creator should delete own estimate, got {del_resp.status_code}"
        assert del_resp.json()["deleted"] == True

    def test_admin_can_delete_any_estimate(self, partner_token, admin_token):
        """Admin can delete any estimate"""
        unique_label = f"TEST_Partner_Estimate_{uuid.uuid4().hex[:8]}"
        
        # Partner creates estimate
        payload = {
            "label": unique_label,
            "country": "usa",
            "category": "h1b",
            "payload": {"test": True}
        }
        save_resp = requests.post(f"{BASE_URL}/api/fee-calculator/save-estimate", 
                                  json=payload, headers=auth_header(partner_token))
        assert save_resp.status_code == 200
        estimate_id = save_resp.json()["id"]
        
        # Admin deletes partner's estimate
        del_resp = requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/{estimate_id}", 
                                   headers=auth_header(admin_token))
        assert del_resp.status_code == 200, f"Admin should delete any estimate, got {del_resp.status_code}"

    def test_non_creator_non_admin_gets_403(self, partner_token, manager_token):
        """Non-creator non-admin gets 403 when trying to delete"""
        unique_label = f"TEST_Partner_Estimate_{uuid.uuid4().hex[:8]}"
        
        # Partner creates estimate
        payload = {
            "label": unique_label,
            "country": "germany",
            "category": "eu_blue_card",
            "payload": {"test": True}
        }
        save_resp = requests.post(f"{BASE_URL}/api/fee-calculator/save-estimate", 
                                  json=payload, headers=auth_header(partner_token))
        assert save_resp.status_code == 200
        estimate_id = save_resp.json()["id"]
        
        # Manager (non-creator, non-admin) tries to delete
        del_resp = requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/{estimate_id}", 
                                   headers=auth_header(manager_token))
        assert del_resp.status_code == 403, f"Non-creator should get 403, got {del_resp.status_code}"
        
        # Cleanup with partner token
        requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/{estimate_id}", 
                       headers=auth_header(partner_token))

    def test_delete_nonexistent_returns_404(self, admin_token):
        """Deleting non-existent estimate returns 404"""
        fake_id = str(uuid.uuid4())
        del_resp = requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/{fake_id}", 
                                   headers=auth_header(admin_token))
        assert del_resp.status_code == 404, f"Expected 404, got {del_resp.status_code}"


# ============================================================================
# TEST: Partner visibility - sees only own estimates
# ============================================================================
class TestPartnerVisibility:
    """Test that partner sees only their own estimates"""

    def test_partner_sees_only_own_estimates(self, partner_token, admin_token):
        """Partner should only see estimates they created"""
        partner_label = f"TEST_Partner_Only_{uuid.uuid4().hex[:8]}"
        admin_label = f"TEST_Admin_Only_{uuid.uuid4().hex[:8]}"
        
        # Partner creates estimate
        partner_payload = {
            "label": partner_label,
            "country": "singapore",
            "category": "employment_pass",
            "payload": {"test": True}
        }
        partner_save = requests.post(f"{BASE_URL}/api/fee-calculator/save-estimate", 
                                     json=partner_payload, headers=auth_header(partner_token))
        partner_estimate_id = partner_save.json()["id"]
        
        # Admin creates estimate
        admin_payload = {
            "label": admin_label,
            "country": "singapore",
            "category": "pr",
            "payload": {"test": True}
        }
        admin_save = requests.post(f"{BASE_URL}/api/fee-calculator/save-estimate", 
                                   json=admin_payload, headers=auth_header(admin_token))
        admin_estimate_id = admin_save.json()["id"]
        
        # Partner lists estimates - should only see their own
        partner_list = requests.get(f"{BASE_URL}/api/fee-calculator/estimates", 
                                    headers=auth_header(partner_token))
        partner_data = partner_list.json()
        
        partner_ids = [e["id"] for e in partner_data["estimates"]]
        assert partner_estimate_id in partner_ids, "Partner should see own estimate"
        assert admin_estimate_id not in partner_ids, "Partner should NOT see admin's estimate"
        
        # Admin lists estimates - should see all
        admin_list = requests.get(f"{BASE_URL}/api/fee-calculator/estimates", 
                                  headers=auth_header(admin_token))
        admin_data = admin_list.json()
        
        admin_ids = [e["id"] for e in admin_data["estimates"]]
        assert partner_estimate_id in admin_ids, "Admin should see partner's estimate"
        assert admin_estimate_id in admin_ids, "Admin should see own estimate"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/{partner_estimate_id}", 
                       headers=auth_header(partner_token))
        requests.delete(f"{BASE_URL}/api/fee-calculator/estimates/{admin_estimate_id}", 
                       headers=auth_header(admin_token))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
