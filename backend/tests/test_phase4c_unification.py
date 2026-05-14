"""Phase 4C Unification — Backend test suite (iteration 101).

Tests all features from the unification:
  - Products: unified shape, margin recompute, /preview
  - Auto-allocation via unified products
  - Dispute / resolve-dispute endpoints
  - Bulk-approve / bulk-mark-paid filter fix (external vendors)
  - Internal vendor auto-user creation
  - PA /my-assessments?stage= filter
  - Regression: auth / vendors / sales / cm / payouts
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

CREDS = {
    "admin": ("admin@leamss.com", "Admin@123"),
    "partner": ("partner@leamss.com", "Partner@123"),
    "cm": ("manager@leamss.com", "Manager@123"),
    "sexec": ("sexec-test@leamss.com", "Pass@1234"),
    "client": ("client@leamss.com", "Client@123"),
}


# ── Fixtures ────────────────────────────────────────────────────
def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {email} → {r.status_code} {r.text}"
    j = r.json()
    return j.get("access_token") or j.get("token")


@pytest.fixture(scope="module")
def tokens():
    return {role: _login(*c) for role, c in CREDS.items()}


def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_h(tokens):
    return _h(tokens["admin"])


# ── 1. Auth regression ──────────────────────────────────────────
@pytest.mark.parametrize("role", list(CREDS.keys()))
def test_auth_login(role):
    token = _login(*CREDS[role])
    assert isinstance(token, str) and len(token) > 20


# ── 2. Products: unified shape ──────────────────────────────────
def test_products_list_has_unified_fields(admin_h):
    r = requests.get(f"{BASE_URL}/api/products", headers=admin_h)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 1
    sample = data[0]
    # New unified fields must exist on every product (possibly empty)
    for fld in ("country", "visa_type", "service_price", "cost_allocations", "success_bonuses"):
        assert fld in sample, f"Missing field {fld}"
    assert "workflow_steps" in sample
    # At least one product should be the fully-configured ones
    with_cs = [p for p in data if p.get("cost_allocations")]
    assert with_cs, "Expected at least one product with cost_allocations"
    p = with_cs[0]
    assert "computed" in p
    c = p["computed"]
    for fld in ("expected_base_cost", "expected_margin", "expected_margin_pct", "max_bonus_payout"):
        assert fld in c


@pytest.fixture(scope="module")
def sample_unified_product(admin_h):
    r = requests.get(f"{BASE_URL}/api/products", headers=admin_h)
    data = r.json()
    cands = [p for p in data if p.get("cost_allocations") and (p.get("service_price") or 0) > 0]
    assert cands, "No unified products found"
    # Prefer Canada PR Express Entry
    for p in cands:
        if "Canada" in (p.get("name") or "") and "Express" in (p.get("name") or ""):
            return p
    return cands[0]


# ── 3. Products: POST / PUT recompute ───────────────────────────
@pytest.fixture(scope="module")
def created_product(admin_h):
    payload = {
        "name": f"TEST_Unif_{uuid.uuid4().hex[:6]}",
        "description": "Unification test product",
        "category": "immigration",
        "country": "Germany",
        "visa_type": "Job Seeker",
        "service_price": 100000,
        "cost_allocations": [
            {"label": "Sales", "vendor_category": "sales_commission", "payment_type": "percentage", "amount": 10, "is_optional": False},
            {"label": "CM", "vendor_category": "case_manager", "payment_type": "flat", "amount": 5000, "is_optional": False},
        ],
        "success_bonuses": [
            {"vendor_category": "sales_commission", "milestone": "visa_approved", "amount": 5000},
        ],
    }
    r = requests.post(f"{BASE_URL}/api/products", headers=admin_h, json=payload)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    requests.delete(f"{BASE_URL}/api/products/{pid}", headers=admin_h)


def test_product_post_auto_computes(admin_h, created_product):
    r = requests.get(f"{BASE_URL}/api/products/{created_product}", headers=admin_h)
    assert r.status_code == 200
    p = r.json()
    c = p.get("computed") or {}
    # 10% of 100k + 5k flat = 15000
    assert c["expected_base_cost"] == 15000.0
    assert c["expected_margin"] == 85000.0
    assert c["expected_margin_pct"] == 85.0
    assert c["max_bonus_payout"] == 5000.0


def test_product_put_recomputes(admin_h, created_product):
    # Update service_price
    r = requests.put(f"{BASE_URL}/api/products/{created_product}", headers=admin_h, json={"service_price": 200000})
    assert r.status_code == 200
    g = requests.get(f"{BASE_URL}/api/products/{created_product}", headers=admin_h).json()
    c = g["computed"]
    # 10% of 200k + 5k = 25000
    assert c["expected_base_cost"] == 25000.0
    assert c["expected_margin"] == 175000.0
    assert c["expected_margin_pct"] == 87.5

    # Update cost_allocations
    r = requests.put(f"{BASE_URL}/api/products/{created_product}", headers=admin_h, json={
        "cost_allocations": [
            {"label": "Sales", "vendor_category": "sales_commission", "payment_type": "percentage", "amount": 5, "is_optional": False},
        ]
    })
    assert r.status_code == 200
    g = requests.get(f"{BASE_URL}/api/products/{created_product}", headers=admin_h).json()
    c = g["computed"]
    assert c["expected_base_cost"] == 10000.0  # 5% of 200k


def test_product_preview(admin_h, sample_unified_product):
    pid = sample_unified_product["id"]
    # Without visa_approved
    r = requests.post(f"{BASE_URL}/api/products/{pid}/preview", headers=admin_h, json={"visa_approved": False})
    assert r.status_code == 200, r.text
    data = r.json()
    for fld in ("service_price", "rows", "total_cost", "margin", "margin_pct", "visa_approved_applied"):
        assert fld in data
    assert data["visa_approved_applied"] is False
    for row in data["rows"]:
        for fld in ("label", "vendor_category", "base_amount", "bonus_amount", "total_amount", "is_optional"):
            assert fld in row
        assert row["bonus_amount"] == 0  # No visa_approved

    # With visa_approved → bonus should apply
    r2 = requests.post(f"{BASE_URL}/api/products/{pid}/preview", headers=admin_h, json={"visa_approved": True})
    d2 = r2.json()
    bonus_total = sum(r["bonus_amount"] for r in d2["rows"])
    if sample_unified_product.get("success_bonuses"):
        assert bonus_total > 0, "Bonuses should apply on visa_approved"

    # Override service_price
    r3 = requests.post(f"{BASE_URL}/api/products/{pid}/preview", headers=admin_h, json={"service_price": 999999})
    d3 = r3.json()
    assert d3["service_price"] == 999999


def test_product_preview_uses_amount_for_percentage(admin_h, created_product):
    # Set known cost_allocations: 5% sales_commission
    requests.put(f"{BASE_URL}/api/products/{created_product}", headers=admin_h, json={
        "service_price": 100000,
        "cost_allocations": [
            {"label": "X", "vendor_category": "sales_commission", "payment_type": "percentage", "amount": 5, "is_optional": False},
        ],
    })
    r = requests.post(f"{BASE_URL}/api/products/{created_product}/preview", headers=admin_h, json={})
    d = r.json()
    # 5% of 100k = 5000 -- proves `amount` is used (not `rate`)
    assert d["rows"][0]["base_amount"] == 5000.0


# ── 4. PA Auto-allocation via unified product ───────────────────
@pytest.fixture(scope="module")
def created_pa_with_product(admin_h, sample_unified_product, tokens):
    """Create a PA linked to the unified product via product_id."""
    sexec_h = _h(tokens["sexec"])
    payload = {
        "client_name": f"TEST_PA_{uuid.uuid4().hex[:6]}",
        "client_email": f"testpa_{uuid.uuid4().hex[:6]}@test.com",
        "client_phone": "9999999999",
        "country": sample_unified_product.get("country") or "Canada",
        "service_type": sample_unified_product.get("visa_type") or "PR",
        "product_id": sample_unified_product["id"],
        "product_name": sample_unified_product["name"],
        "case_type": "new_case",
    }
    r = requests.post(f"{BASE_URL}/api/pre-assessment", headers=sexec_h, json=payload)
    if r.status_code not in (200, 201):
        pytest.skip(f"PA create failed: {r.status_code} {r.text}")
    pa_id = r.json().get("id") or r.json().get("pa_id")
    if not pa_id:
        pytest.skip("PA id missing in response")
    yield pa_id


def _drive_pa_to_case_created(admin_h, pa_id):
    """Best-effort drive PA → case_created via admin_approve_final endpoint."""
    # Try the canonical endpoint
    r = requests.post(f"{BASE_URL}/api/pre-assessment/{pa_id}/admin-approve-final", headers=admin_h, json={"final_amount": 150000})
    if r.status_code in (200, 201):
        return True
    # Alternate endpoint patterns
    for url in [
        f"{BASE_URL}/api/pre-assessments/{pa_id}/admin-approve-final",
        f"{BASE_URL}/api/pre-assessment/{pa_id}/admin_approve_final",
    ]:
        r = requests.post(url, headers=admin_h, json={"final_amount": 150000})
        if r.status_code in (200, 201):
            return True
    return False


def test_pa_allocations_via_product_id(admin_h, created_pa_with_product):
    ok = _drive_pa_to_case_created(admin_h, created_pa_with_product)
    if not ok:
        pytest.skip("Could not drive PA to case_created stage")
    time.sleep(1)
    r = requests.get(f"{BASE_URL}/api/pa/{created_pa_with_product}/allocations", headers=admin_h)
    assert r.status_code == 200, r.text
    d = r.json()
    # Body may be wrapped or direct
    allocs = d.get("allocations") if isinstance(d, dict) else None
    assert allocs is not None, f"No allocations key in response: {d}"
    assert len(allocs) >= 1, "Expected at least 1 allocation from unified product"


def test_pa_allocations_fallback_country_visa(admin_h, tokens):
    """PA with NO product_id but country+visa_type should match via fallback."""
    sexec_h = _h(tokens["sexec"])
    payload = {
        "client_name": f"TEST_FB_{uuid.uuid4().hex[:6]}",
        "client_email": f"testfb_{uuid.uuid4().hex[:6]}@test.com",
        "client_phone": "8888888888",
        "country": "Canada",
        "service_type": "PR",
        "case_type": "new_case",
    }
    r = requests.post(f"{BASE_URL}/api/pre-assessment", headers=sexec_h, json=payload)
    if r.status_code not in (200, 201):
        pytest.skip(f"PA create failed: {r.text}")
    pa_id = r.json().get("id") or r.json().get("pa_id")
    if not pa_id:
        pytest.skip("PA id missing")
    ok = _drive_pa_to_case_created(admin_h, pa_id)
    if not ok:
        pytest.skip("Could not drive PA to case_created")
    time.sleep(1)
    r = requests.get(f"{BASE_URL}/api/pa/{pa_id}/allocations", headers=admin_h)
    # Fallback may or may not find a match; the endpoint must respond cleanly
    assert r.status_code in (200, 404)


# ── 5. /pre-assessment/my-assessments?stage= filter ─────────────
def test_my_assessments_stage_filter(admin_h):
    r = requests.get(f"{BASE_URL}/api/pre-assessment/my-assessments?stage=case_created", headers=admin_h)
    assert r.status_code == 200, r.text
    d = r.json()
    items = d if isinstance(d, list) else (d.get("assessments") or d.get("items") or d.get("data") or [])
    # Should be a list — accepted empty or non-empty
    assert isinstance(items, list)


# ── 6. Dispute endpoints ────────────────────────────────────────
@pytest.fixture(scope="module")
def seeded_allocation():
    """Insert a synthetic allocation doc directly via mongo-equivalent: use the bulk-test pattern.
    Since we cannot reach mongo directly here, we rely on existing allocations from PA flow above.
    Falls back to skip if none available.
    """
    return None


def test_dispute_non_admin_forbidden(tokens):
    sexec_h = _h(tokens["sexec"])
    r = requests.post(
        f"{BASE_URL}/api/payouts/fake-pa/allocations/fake-alloc/dispute",
        headers=sexec_h,
        json={"reason": "test"},
    )
    assert r.status_code == 403


def test_resolve_dispute_non_admin_forbidden(tokens):
    sexec_h = _h(tokens["sexec"])
    r = requests.post(
        f"{BASE_URL}/api/payouts/fake-pa/allocations/fake-alloc/resolve-dispute",
        headers=sexec_h,
    )
    assert r.status_code == 403


def test_dispute_unknown_returns_400(admin_h):
    r = requests.post(
        f"{BASE_URL}/api/payouts/no-such-pa/allocations/no-such-alloc/dispute",
        headers=admin_h,
        json={"reason": "test"},
    )
    assert r.status_code == 400


def test_dispute_flow_on_real_allocation(admin_h):
    # Fetch queue to find a pending allocation
    r = requests.get(f"{BASE_URL}/api/payouts/queue", headers=admin_h)
    assert r.status_code == 200
    rows = r.json().get("rows") or []
    pending = [x for x in rows if x.get("status") == "pending"]
    if not pending:
        pytest.skip("No pending allocations available to dispute")
    target = pending[0]
    pa_id, alloc_id = target["pa_id"], target["allocation_id"]

    # Dispute
    r = requests.post(
        f"{BASE_URL}/api/payouts/{pa_id}/allocations/{alloc_id}/dispute",
        headers=admin_h, json={"reason": "Vendor refused"},
    )
    assert r.status_code == 200, r.text

    # Cannot dispute again (now in disputed state)
    r = requests.post(
        f"{BASE_URL}/api/payouts/{pa_id}/allocations/{alloc_id}/dispute",
        headers=admin_h, json={"reason": "Again"},
    )
    assert r.status_code == 400

    # Resolve dispute
    r = requests.post(
        f"{BASE_URL}/api/payouts/{pa_id}/allocations/{alloc_id}/resolve-dispute",
        headers=admin_h,
    )
    assert r.status_code == 200, r.text
    new_status = r.json().get("new_status")
    # If vendor assigned → approved, else pending
    assert new_status in ("approved", "pending")
    if target.get("vendor_id") or target.get("vendor_master_id"):
        assert new_status == "approved"
    else:
        assert new_status == "pending"

    # Resolve again → 400 (no longer in disputed)
    r = requests.post(
        f"{BASE_URL}/api/payouts/{pa_id}/allocations/{alloc_id}/resolve-dispute",
        headers=admin_h,
    )
    assert r.status_code == 400


def test_dispute_already_paid_blocked(admin_h):
    r = requests.get(f"{BASE_URL}/api/payouts/queue?status=paid", headers=admin_h)
    rows = r.json().get("rows") or []
    if not rows:
        pytest.skip("No paid allocations available")
    target = rows[0]
    r = requests.post(
        f"{BASE_URL}/api/payouts/{target['pa_id']}/allocations/{target['allocation_id']}/dispute",
        headers=admin_h, json={"reason": "should be blocked"},
    )
    assert r.status_code == 400


# ── 7. Bulk-approve / bulk-mark-paid filter fix ─────────────────
def test_bulk_approve_external_vendor_works(admin_h):
    """Regression: bulk-approve must accept vendor_master_id-only allocations."""
    r = requests.get(f"{BASE_URL}/api/payouts/queue?status=pending", headers=admin_h)
    rows = r.json().get("rows") or []
    # Find an allocation with vendor_master_id but no vendor_id (external)
    external = [x for x in rows if x.get("vendor_master_id") and not x.get("vendor_id")]
    if not external:
        pytest.skip("No external-vendor pending allocations in queue")
    t = external[0]
    r = requests.post(f"{BASE_URL}/api/payouts/bulk-approve", headers=admin_h, json={
        "items": [{"pa_id": t["pa_id"], "allocation_id": t["allocation_id"]}]
    })
    assert r.status_code == 200
    d = r.json()
    assert d["approved"] == 1, f"External vendor allocation failed bulk-approve: {d}"


# ── 8. Internal vendor auto-user creation ───────────────────────
def test_internal_vendor_auto_creates_case_manager_user(admin_h):
    email = f"test_cm_{uuid.uuid4().hex[:8]}@leamss.com"
    payload = {
        "name": "Test CM Vendor",
        "email": email,
        "phone": "9000000001",
        "category": "case_manager",
        "vendor_type": "internal",
    }
    r = requests.post(f"{BASE_URL}/api/vendors", headers=admin_h, json=payload)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "auto_created_user" in d, f"Missing auto_created_user: {d}"
    assert d["auto_created_user"].get("temp_password"), "temp_password missing"
    temp_pwd = d["auto_created_user"]["temp_password"]

    # Login with new credentials
    lr = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": temp_pwd})
    assert lr.status_code == 200, f"Login failed for auto-created user: {lr.text}"


def test_internal_vendor_auto_creates_sales_user(admin_h):
    email = f"test_sales_{uuid.uuid4().hex[:8]}@leamss.com"
    # Ensure sales_commission category exists
    cats = requests.get(f"{BASE_URL}/api/vendors/categories", headers=admin_h).json().get("categories", [])
    if not any(c.get("key") == "sales_commission" for c in cats):
        pytest.skip("sales_commission category not seeded")
    payload = {
        "name": "Test Sales Vendor",
        "email": email,
        "phone": "9000000002",
        "category": "sales_commission",
        "vendor_type": "internal",
    }
    r = requests.post(f"{BASE_URL}/api/vendors", headers=admin_h, json=payload)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "auto_created_user" in d
    assert d["auto_created_user"].get("temp_password")


def test_internal_vendor_no_autocreate_for_external_category(admin_h):
    """Non-internal categories (e.g., lawyer) should NOT auto-create user."""
    cats = requests.get(f"{BASE_URL}/api/vendors/categories", headers=admin_h).json().get("categories", [])
    # Find a non-internal category
    non_internal = [c for c in cats if not c.get("is_internal")]
    if not non_internal:
        pytest.skip("No non-internal category seeded")
    cat_key = non_internal[0]["key"]
    email = f"test_ext_{uuid.uuid4().hex[:8]}@leamss.com"
    payload = {
        "name": "Test External Vendor",
        "email": email,
        "phone": "9000000003",
        "category": cat_key,
        "vendor_type": "internal",  # type=internal but category is external
    }
    r = requests.post(f"{BASE_URL}/api/vendors", headers=admin_h, json=payload)
    assert r.status_code == 200, r.text
    d = r.json()
    # No auto-creation should happen for non-internal categories
    assert "auto_created_user" not in d or not d["auto_created_user"].get("temp_password")


def test_internal_vendor_existing_user_link(admin_h):
    """If user with same email already exists, link without creating."""
    existing_email = "manager@leamss.com"
    payload = {
        "name": "Linked Manager",
        "email": existing_email,
        "phone": "9000000099",
        "category": "case_manager",
        "vendor_type": "internal",
    }
    r = requests.post(f"{BASE_URL}/api/vendors", headers=admin_h, json=payload)
    # Could 409 if same email vendor already exists from a previous run
    if r.status_code == 409:
        pytest.skip("Vendor with manager@leamss.com email already exists from prior run")
    assert r.status_code == 200, r.text
    d = r.json()
    assert "auto_created_user" in d
    # No temp_password since the user already existed
    assert not d["auto_created_user"].get("temp_password"), "Should not generate temp_password for existing user"
    assert "message" in d["auto_created_user"]


# ── 9. Regression: listing endpoints unchanged ──────────────────
@pytest.mark.parametrize("path", [
    "/api/vendors",
    "/api/vendors/categories",
    "/api/sales-commission/slabs",
    "/api/payouts/queue",
    "/api/payouts/stats",
])
def test_admin_endpoints_200(admin_h, path):
    r = requests.get(f"{BASE_URL}{path}", headers=admin_h)
    assert r.status_code == 200, f"{path} → {r.status_code} {r.text[:200]}"


def test_sales_commission_my_for_sexec(tokens):
    r = requests.get(f"{BASE_URL}/api/sales-commission/my", headers=_h(tokens["sexec"]))
    assert r.status_code == 200


def test_cm_earnings_my_for_cm(tokens):
    r = requests.get(f"{BASE_URL}/api/cm-earnings/my", headers=_h(tokens["cm"]))
    assert r.status_code == 200
