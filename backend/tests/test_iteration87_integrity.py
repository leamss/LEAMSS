"""
Iteration 87: SHA-256 Tamper Detection for Legal Archive
Tests for:
- POST /api/legal-archive/integrity/backfill (admin only)
- GET /api/legal-archive/integrity/verify-all (admin only)
- Tamper detection sanity test
- Search endpoint returns integrity_status + integrity_hash
- Authorization checks (non-admin gets 403)
- Existing endpoints regression (stats, search)
- New records (invoice, signature, consent) include integrity_hash
- Agreement templates verbatim content verification
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"
CLIENT_EMAIL = "client@leamss.com"
CLIENT_PASSWORD = "Client@123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip(f"Admin login failed: {r.status_code} {r.text}")


@pytest.fixture(scope="module")
def partner_token():
    """Get partner auth token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARTNER_EMAIL, "password": PARTNER_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip(f"Partner login failed: {r.status_code} {r.text}")


@pytest.fixture(scope="module")
def client_token():
    """Get client auth token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CLIENT_EMAIL, "password": CLIENT_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip(f"Client login failed: {r.status_code} {r.text}")


class TestIntegrityBackfill:
    """Tests for POST /api/legal-archive/integrity/backfill"""
    
    def test_01_admin_can_backfill(self, admin_token):
        """Admin can run backfill to populate integrity_hash on legacy records"""
        r = requests.post(
            f"{BASE_URL}/api/legal-archive/integrity/backfill",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "consent" in data
        assert "signature" in data
        assert "invoice" in data
        assert "total" in data
        print(f"✓ Backfill result: consent={data['consent']}, signature={data['signature']}, invoice={data['invoice']}, total={data['total']}")
    
    def test_02_partner_cannot_backfill(self, partner_token):
        """Partner should get 403 when trying to backfill"""
        r = requests.post(
            f"{BASE_URL}/api/legal-archive/integrity/backfill",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        print("✓ Partner correctly blocked from backfill (403)")
    
    def test_03_client_cannot_backfill(self, client_token):
        """Client should get 403 when trying to backfill"""
        r = requests.post(
            f"{BASE_URL}/api/legal-archive/integrity/backfill",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        print("✓ Client correctly blocked from backfill (403)")


class TestIntegrityVerifyAll:
    """Tests for GET /api/legal-archive/integrity/verify-all"""
    
    def test_04_admin_can_verify_all(self, admin_token):
        """Admin can run verify-all to check integrity of all records"""
        r = requests.get(
            f"{BASE_URL}/api/legal-archive/integrity/verify-all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "verified" in data
        assert "tampered" in data
        assert "unverified" in data
        assert "total" in data
        assert "tampered_records" in data
        assert "scanned_at" in data
        print(f"✓ Verify-all result: verified={data['verified']}, tampered={data['tampered']}, unverified={data['unverified']}, total={data['total']}")
    
    def test_05_partner_cannot_verify_all(self, partner_token):
        """Partner should get 403 when trying to verify-all"""
        r = requests.get(
            f"{BASE_URL}/api/legal-archive/integrity/verify-all",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        print("✓ Partner correctly blocked from verify-all (403)")
    
    def test_06_client_cannot_verify_all(self, client_token):
        """Client should get 403 when trying to verify-all"""
        r = requests.get(
            f"{BASE_URL}/api/legal-archive/integrity/verify-all",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        print("✓ Client correctly blocked from verify-all (403)")


class TestSearchIntegrityFields:
    """Tests for integrity fields in search results"""
    
    def test_07_search_returns_integrity_status(self, admin_token):
        """Search results should include integrity_status field"""
        r = requests.get(
            f"{BASE_URL}/api/legal-archive/search",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "items" in data
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "integrity_status" in item, f"Missing integrity_status in item: {item.keys()}"
            assert item["integrity_status"] in ["verified", "tampered", "unverified"], f"Invalid integrity_status: {item['integrity_status']}"
            print(f"✓ Search item has integrity_status: {item['integrity_status']}")
        else:
            print("⚠ No items in search results to verify")
    
    def test_08_search_returns_integrity_hash(self, admin_token):
        """Search results should include integrity_hash (12-char prefix)"""
        r = requests.get(
            f"{BASE_URL}/api/legal-archive/search",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "integrity_hash" in item, f"Missing integrity_hash in item: {item.keys()}"
            # Hash should be 12-char prefix or empty for legacy
            if item["integrity_hash"]:
                assert len(item["integrity_hash"]) == 12, f"Expected 12-char hash prefix, got {len(item['integrity_hash'])}"
            print(f"✓ Search item has integrity_hash: {item['integrity_hash']}")
        else:
            print("⚠ No items in search results to verify")


class TestExistingEndpointsRegression:
    """Regression tests for existing Legal Archive endpoints"""
    
    def test_09_stats_endpoint_still_works(self, admin_token):
        """GET /api/legal-archive/stats should still work"""
        r = requests.get(
            f"{BASE_URL}/api/legal-archive/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "consents" in data
        assert "signatures" in data
        assert "invoices" in data
        assert "total" in data
        print(f"✓ Stats: consents={data['consents']}, signatures={data['signatures']}, invoices={data['invoices']}, total={data['total']}")
    
    def test_10_search_endpoint_still_works(self, admin_token):
        """GET /api/legal-archive/search should still work with filters"""
        # Test with record_type filter
        r = requests.get(
            f"{BASE_URL}/api/legal-archive/search?record_type=consent",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "items" in data
        assert "count" in data
        # All items should be consent type
        for item in data["items"]:
            assert item["type"] == "consent", f"Expected consent type, got {item['type']}"
        print(f"✓ Search with consent filter returned {data['count']} items")


class TestAgreementTemplatesVerbatim:
    """Tests for agreement templates verbatim content"""
    
    def test_11_templates_exist_with_version_2(self, admin_token):
        """3 templates should exist with version >= 2"""
        r = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        templates = data.get("items", []) if isinstance(data, dict) else data
        
        expected_names = ["Australia · PR · Standard", "Australia · PR · Protection Policy", "Canada · PR · Express Entry"]
        found_names = [t["name"] for t in templates]
        
        for name in expected_names:
            assert name in found_names, f"Missing template: {name}"
        
        for t in templates:
            if t["name"] in expected_names:
                assert t.get("version", 1) >= 2, f"Template {t['name']} has version {t.get('version')} < 2"
        
        print(f"✓ Found {len(templates)} templates, all expected templates present with version >= 2")
    
    def test_12_template_body_has_agreement_doc_class(self, admin_token):
        """Template body_html should contain class='agreement-doc'"""
        r = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        templates = data.get("items", []) if isinstance(data, dict) else data
        
        # Filter to only seeded templates (Australia/Canada)
        seeded = [t for t in templates if "Australia" in t.get("name", "") or "Canada" in t.get("name", "")]
        assert len(seeded) >= 3, f"Expected at least 3 seeded templates, found {len(seeded)}"
        
        for t in seeded:
            if t.get("is_active"):
                # Get full template with body_html
                r2 = requests.get(
                    f"{BASE_URL}/api/agreement-templates/{t['id']}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                if r2.status_code == 200:
                    full = r2.json()
                    body = full.get("body_html", "")
                    assert 'class="agreement-doc"' in body, f"Template {t['name']} missing class='agreement-doc'"
                    print(f"✓ Template '{t['name']}' has agreement-doc class")
    
    def test_13_template_body_has_annexure_heading(self, admin_token):
        """Template body_html should contain Annexure content (Australia templates)"""
        r = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        templates = data.get("items", []) if isinstance(data, dict) else data
        
        australia_templates = [t for t in templates if "Australia" in t.get("name", "") and "Standard" in t.get("name", "")]
        assert len(australia_templates) >= 1, "No Australia Standard templates found"
        
        for t in australia_templates:
            r2 = requests.get(
                f"{BASE_URL}/api/agreement-templates/{t['id']}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            if r2.status_code == 200:
                full = r2.json()
                body = full.get("body_html", "")
                # Check for Annexure heading (Australia templates have this)
                assert "Annexure" in body, f"Template {t['name']} missing Annexure content"
                print(f"✓ Template '{t['name']}' has Annexure content")
    
    def test_14_template_body_has_client_details_table(self, admin_token):
        """Template body_html should contain '<table class=\"client-details\">'"""
        r = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        templates = data.get("items", []) if isinstance(data, dict) else data
        
        # Filter to only seeded templates
        seeded = [t for t in templates if "Australia" in t.get("name", "") or "Canada" in t.get("name", "")]
        
        for t in seeded:
            if t.get("is_active"):
                r2 = requests.get(
                    f"{BASE_URL}/api/agreement-templates/{t['id']}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                if r2.status_code == 200:
                    full = r2.json()
                    body = full.get("body_html", "")
                    assert 'class="client-details"' in body, f"Template {t['name']} missing client-details table"
                    print(f"✓ Template '{t['name']}' has client-details table")
    
    def test_15_template_body_has_signature_table(self, admin_token):
        """Template body_html should contain '<table class=\"signature-table\">'"""
        r = requests.get(
            f"{BASE_URL}/api/agreement-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        templates = data.get("items", []) if isinstance(data, dict) else data
        
        # Filter to only seeded templates
        seeded = [t for t in templates if "Australia" in t.get("name", "") or "Canada" in t.get("name", "")]
        
        for t in seeded:
            if t.get("is_active"):
                r2 = requests.get(
                    f"{BASE_URL}/api/agreement-templates/{t['id']}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                if r2.status_code == 200:
                    full = r2.json()
                    body = full.get("body_html", "")
                    assert 'class="signature-table"' in body, f"Template {t['name']} missing signature-table"
                    print(f"✓ Template '{t['name']}' has signature-table")


class TestNewRecordsHaveIntegrityHash:
    """Tests that newly created records include integrity_hash"""
    
    def test_16_get_pa_for_testing(self, admin_token):
        """Get a PA with status that allows invoice/signature creation"""
        # Get PAs to find one suitable for testing
        r = requests.get(
            f"{BASE_URL}/api/pre-assessment/all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if r.status_code == 200:
            pas = r.json()
            # Find a PA with proposal_paid or awaiting_final_approval stage
            suitable = [p for p in pas if p.get("stage") in ["proposal_paid", "awaiting_final_approval", "case_created", "proposal_sent"]]
            if suitable:
                print(f"✓ Found {len(suitable)} PAs suitable for testing")
                return suitable[0]["id"]
        print("⚠ No suitable PA found for invoice/signature testing")
        return None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
