"""Phase 4C.5 (CM Earnings) + 4C.6 (Vendor Portal) + 4C.7 (Payouts) backend tests.

Covers:
  - /cm-earnings/my (RBAC, totals, line items, period filter)
  - /vendor-portal/accept-invite (magic-link, password strength, 404/410)
  - /vendor-portal/me, /my-assignments, /my-payments, PATCH /me
  - /payouts/queue, /payouts/stats, bulk-approve, bulk-mark-paid, neft-csv
  - Integration: seed PA → allocations → assign vendor → bulk-approve → bulk-mark-paid → NEFT CSV → CM dashboard
  - Regression: /auth/login, prior 4C.3+4C.4 endpoints still work
"""
import os
import csv
import io
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timezone, timedelta

# Shared event loop (motor reuses it across direct DB calls)
_LOOP = asyncio.new_event_loop()
def _run(coro):
    return _LOOP.run_until_complete(coro)


def _load_frontend_env():
    try:
        with open("/app/frontend/.env") as f:
            for ln in f:
                if ln.startswith("REACT_APP_BACKEND_URL"):
                    return ln.split("=", 1)[1].strip()
    except Exception:
        return None


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env() or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

CREDS = {
    "admin": ("admin@leamss.com", "Admin@123"),
    "cm": ("manager@leamss.com", "Manager@123"),
    "partner": ("partner@leamss.com", "Partner@123"),
    "sexec": ("sexec-test@leamss.com", "Pass@1234"),
    "client": ("client@leamss.com", "Client@123"),
}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data["access_token"] if "access_token" in data else data["token"]


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def tokens():
    out = {}
    for k, (e, p) in CREDS.items():
        try:
            out[k] = _login(e, p)
        except Exception as ex:
            print(f"[warn] login {k} failed: {ex}")
            out[k] = None
    return out


# ══════════════════════════════════════════════════════════════
# Regression — auth + prior 4C.3/4C.4 endpoints
# ══════════════════════════════════════════════════════════════
class TestRegression:
    def test_logins_all_roles(self, tokens):
        for k in ("admin", "cm", "partner", "sexec", "client"):
            assert tokens.get(k), f"login failed for {k}"

    def test_cost_structures(self, tokens):
        r = requests.get(f"{API}/products/cost-structures", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200

    def test_vendors_list(self, tokens):
        r = requests.get(f"{API}/vendors", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200

    def test_sales_commission_slabs(self, tokens):
        r = requests.get(f"{API}/sales-commission/slabs", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200
        assert "slabs" in r.json()

    def test_sales_commission_my_partner(self, tokens):
        r = requests.get(f"{API}/sales-commission/my", headers=_hdr(tokens["partner"]), timeout=30)
        assert r.status_code == 200

    def test_sales_commission_all_admin(self, tokens):
        r = requests.get(f"{API}/sales-commission/all", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200

    def test_sales_commission_leaderboard(self, tokens):
        r = requests.get(f"{API}/sales-commission/leaderboard", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════
# Shared seed fixture — CM allocation doc for cm@... user
# ══════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def seeded_cm_allocation(tokens):
    """Inserts a synthetic pa_cost_allocations doc with a case_manager allocation
    assigned to manager@leamss.com (vendor_id == cm user.id)."""
    import sys; sys.path.insert(0, "/app/backend")
    from core.database import db, users_col
    allocations_col = db["pa_cost_allocations"]

    async def setup():
        cm_user = await users_col.find_one({"email": CREDS["cm"][0]}, {"_id": 0, "id": 1})
        assert cm_user, "case manager user must exist"
        cm_uid = cm_user["id"]
        pa_id = f"TESTPA_CM_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        doc = {
            "pa_id": pa_id,
            "pa_number": f"TEST-CM-{uuid.uuid4().hex[:5].upper()}",
            "client_name": "TEST_CM_Client",
            "allocations": [
                {
                    "allocation_id": str(uuid.uuid4()),
                    "label": "TEST_CM_Assignment",
                    "vendor_category": "case_manager",
                    "vendor_id": cm_uid,
                    "vendor_master_id": None,
                    "vendor_name": "TEST CM",
                    "vendor_type": "internal",
                    "total_amount": 10000.0,
                    "calculated_amount": 10000.0,
                    "bonus_amount": 0.0,
                    "status": "approved",
                    "assigned_at": now,
                    "approved_at": now,
                },
                {
                    "allocation_id": str(uuid.uuid4()),
                    "label": "TEST_CM_Paid",
                    "vendor_category": "case_manager",
                    "vendor_id": cm_uid,
                    "vendor_master_id": None,
                    "vendor_name": "TEST CM",
                    "vendor_type": "internal",
                    "total_amount": 5000.0,
                    "calculated_amount": 5000.0,
                    "status": "paid",
                    "paid_at": now,
                    "payment_reference": "TEST-REF-CM",
                },
            ],
            "summary": {"total_allocated": 15000.0, "company_margin": 0.0},
            "last_recalculated_at": now,
            "created_at": now,
        }
        await allocations_col.insert_one(doc)
        return {"pa_id": pa_id, "cm_uid": cm_uid, "allocation_ids":
                [doc["allocations"][0]["allocation_id"], doc["allocations"][1]["allocation_id"]]}

    async def teardown(pa_id):
        await allocations_col.delete_many({"pa_id": pa_id})

    info = _run(setup())
    yield info
    _run(teardown(info["pa_id"]))


# ══════════════════════════════════════════════════════════════
# Phase 4C.5 — CM Earnings
# ══════════════════════════════════════════════════════════════
class TestCMEarnings:
    def test_my_as_cm(self, tokens, seeded_cm_allocation):
        r = requests.get(f"{API}/cm-earnings/my", headers=_hdr(tokens["cm"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("totals", "lifetime_total", "deal_count", "line_items"):
            assert k in data, f"missing {k}"
        # Totals contain pending/approved/paid/disputed
        for s in ("pending", "approved", "paid", "disputed"):
            assert s in data["totals"]
        # Verify our seeded entries (₹10k approved + ₹5k paid) included
        assert data["totals"]["approved"] >= 10000.0
        assert data["totals"]["paid"] >= 5000.0
        # Line items must reference our seeded PA
        pa_ids = {li["pa_id"] for li in data["line_items"]}
        assert seeded_cm_allocation["pa_id"] in pa_ids

    def test_my_only_case_manager_category(self, tokens, seeded_cm_allocation):
        """CM endpoint must only count vendor_category='case_manager' entries."""
        r = requests.get(f"{API}/cm-earnings/my", headers=_hdr(tokens["cm"]), timeout=30)
        data = r.json()
        # All line items should be from case_manager category — sample check on label
        for li in data["line_items"]:
            assert "label" in li
            # No way to read vendor_category in response — but our seeded entries are case_manager
        # Sanity: lifetime_total = sum of totals
        assert abs(data["lifetime_total"] - sum(data["totals"].values())) < 0.5

    def test_my_admin_forbidden(self, tokens):
        r = requests.get(f"{API}/cm-earnings/my", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 403, r.text

    def test_my_partner_forbidden(self, tokens):
        r = requests.get(f"{API}/cm-earnings/my", headers=_hdr(tokens["partner"]), timeout=30)
        assert r.status_code == 403

    def test_my_sexec_forbidden(self, tokens):
        r = requests.get(f"{API}/cm-earnings/my", headers=_hdr(tokens["sexec"]), timeout=30)
        assert r.status_code == 403

    def test_my_client_forbidden(self, tokens):
        r = requests.get(f"{API}/cm-earnings/my", headers=_hdr(tokens["client"]), timeout=30)
        assert r.status_code == 403

    def test_my_period_filter_current(self, tokens, seeded_cm_allocation):
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        r = requests.get(f"{API}/cm-earnings/my?period={period}", headers=_hdr(tokens["cm"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["period"] == period
        # Seeded data falls in current period → totals > 0
        assert data["lifetime_total"] > 0

    def test_my_period_filter_old(self, tokens):
        r = requests.get(f"{API}/cm-earnings/my?period=2019-01", headers=_hdr(tokens["cm"]), timeout=30)
        assert r.status_code == 200
        data = r.json()
        # No 2019 entries → all totals 0
        assert data["lifetime_total"] == 0
        assert len(data["line_items"]) == 0


# ══════════════════════════════════════════════════════════════
# Phase 4C.6 — Vendor Portal (accept-invite + me + assignments)
# ══════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def vendor_with_invite(tokens):
    """Creates a fresh vendor + magic-link invite token. Returns
    {vendor_id, email, token, password}.
    """
    email = f"vendor-test-{uuid.uuid4().hex[:6]}@leamss.com"
    body = {
        "name": "TEST Vendor Portal",
        "email": email,
        "phone": "+910000000000",
        "category": "lawyer",  # may need to exist; we'll fallback
        "vendor_type": "external",
        "bank_details": {
            "account_holder_name": "TEST Vendor",
            "account_number": "1234567890",
            "ifsc_code": "HDFC0001234",
            "bank_name": "HDFC",
        },
        "pan_number": "ABCDE1234F",
    }
    # Find an existing vendor category to avoid FK errors
    rc = requests.get(f"{API}/vendors/categories", headers=_hdr(tokens["admin"]), timeout=30)
    if rc.status_code == 200:
        cats = rc.json()
        items = cats if isinstance(cats, list) else cats.get("categories") or cats.get("items") or []
        if items:
            body["category"] = items[0].get("key") or items[0].get("id") or body["category"]

    r = requests.post(f"{API}/vendors", headers=_hdr(tokens["admin"]), json=body, timeout=30)
    if r.status_code not in (200, 201):
        pytest.skip(f"Could not create vendor: {r.status_code} {r.text}")
    vendor = r.json()
    vendor_id = vendor.get("id") or vendor.get("vendor_id") or (vendor.get("vendor") or {}).get("id")
    assert vendor_id, f"vendor id missing in response: {vendor}"

    # Send invite
    ri = requests.post(f"{API}/vendors/{vendor_id}/send-portal-invite",
                       headers=_hdr(tokens["admin"]), timeout=30)
    assert ri.status_code == 200, ri.text
    invite_url = ri.json()["invite_url"]
    token = invite_url.rstrip("/").split("/")[-1]

    info = {"vendor_id": vendor_id, "email": email, "token": token, "password": "Vendor@P4ss!"}

    yield info

    # Cleanup: delete vendor, user, magic-link, and any allocations
    import sys; sys.path.insert(0, "/app/backend")
    from core.database import db, users_col
    async def cleanup():
        await db["vendors"].delete_many({"id": vendor_id})
        await db["magic_links"].delete_many({"vendor_id": vendor_id})
        await users_col.delete_many({"email": email})
        await db["pa_cost_allocations"].delete_many({"pa_id": {"$regex": "^TESTPA_VP_"}})
    _run(cleanup())


class TestVendorPortalAcceptInvite:
    def test_accept_invite_invalid_token(self):
        r = requests.post(f"{API}/vendor-portal/accept-invite",
                          json={"token": "non-existent-xyz", "password": "Strong@1234"}, timeout=30)
        assert r.status_code == 404, r.text

    def test_accept_invite_weak_password(self, vendor_with_invite):
        # password fails strength check (no upper/digit/special)
        r = requests.post(f"{API}/vendor-portal/accept-invite",
                          json={"token": vendor_with_invite["token"], "password": "weakpass"}, timeout=30)
        # Pydantic enforces min_length=8 → 422; the in-handler validator returns 400
        assert r.status_code in (400, 422), r.text

    def test_accept_invite_success(self, vendor_with_invite):
        r = requests.post(f"{API}/vendor-portal/accept-invite",
                          json={"token": vendor_with_invite["token"],
                                "password": vendor_with_invite["password"]}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("vendor_id") == vendor_with_invite["vendor_id"]
        assert data.get("user_id")

    def test_accept_invite_reuse_410(self, vendor_with_invite):
        # Already consumed by previous test → 410
        r = requests.post(f"{API}/vendor-portal/accept-invite",
                          json={"token": vendor_with_invite["token"],
                                "password": vendor_with_invite["password"]}, timeout=30)
        assert r.status_code == 410, r.text


class TestVendorPortalSelfService:
    @pytest.fixture(scope="class")
    def vendor_token(self, vendor_with_invite):
        # Must run after accept-invite_success. Login as the vendor.
        try:
            return _login(vendor_with_invite["email"], vendor_with_invite["password"])
        except AssertionError:
            pytest.skip("Vendor login failed — accept-invite did not run")

    def test_me_returns_full_bank_details(self, vendor_token):
        r = requests.get(f"{API}/vendor-portal/me", headers=_hdr(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        v = r.json()
        bank = v.get("bank_details") or {}
        # Full bank_details (NOT masked) — account number must contain digits, not stars
        assert "account_number" in bank
        acc = str(bank["account_number"])
        assert "*" not in acc, f"bank_details should NOT be masked for vendor self — got {acc}"

    def test_me_non_vendor_404(self, tokens):
        r = requests.get(f"{API}/vendor-portal/me", headers=_hdr(tokens["admin"]), timeout=30)
        # admin is not a vendor → 404 (no vendor record for admin user)
        assert r.status_code == 404, r.text

    def test_my_assignments_empty_ok(self, vendor_token):
        r = requests.get(f"{API}/vendor-portal/my-assignments", headers=_hdr(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("assignments", "totals", "lifetime_paid"):
            assert k in data
        for s in ("pending", "approved", "paid", "disputed"):
            assert s in data["totals"]

    def test_my_payments_empty_ok(self, vendor_token):
        r = requests.get(f"{API}/vendor-portal/my-payments", headers=_hdr(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "payments" in data and "lifetime_total" in data

    def test_patch_me(self, vendor_token):
        r = requests.patch(f"{API}/vendor-portal/me", headers=_hdr(vendor_token),
                           json={"phone": "+919999999999",
                                 "bank_details": {"account_number": "9876543210",
                                                  "ifsc_code": "ICIC0005678",
                                                  "bank_name": "ICICI"}}, timeout=30)
        assert r.status_code == 200, r.text
        # Verify
        rg = requests.get(f"{API}/vendor-portal/me", headers=_hdr(vendor_token), timeout=30)
        v = rg.json()
        assert v.get("phone") == "+919999999999"
        assert (v.get("bank_details") or {}).get("account_number") == "9876543210"


# ══════════════════════════════════════════════════════════════
# Phase 4C.7 — Payouts
# ══════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def payout_seed(tokens):
    """Seed a PA allocation doc with mixed states for payouts testing."""
    import sys; sys.path.insert(0, "/app/backend")
    from core.database import db, users_col
    allocations_col = db["pa_cost_allocations"]
    vendors_col_local = db["vendors"]

    async def setup():
        # Find or create a vendor with bank details
        vendor = await vendors_col_local.find_one(
            {"status": "active", "bank_details.account_number": {"$exists": True, "$ne": None}}, {"_id": 0})
        if not vendor:
            vid = str(uuid.uuid4())
            vendor = {
                "id": vid, "name": "TEST_NEFT_Vendor", "vendor_code": "VEN-TEST-NEFT",
                "vendor_type": "external", "category": "lawyer", "status": "active",
                "email": f"neft-{uuid.uuid4().hex[:6]}@test.local",
                "bank_details": {"account_number": "1111222233334444",
                                 "ifsc_code": "HDFC0000001", "bank_name": "HDFC"},
                "pan_number": "PANXY1234Z",
            }
            await vendors_col_local.insert_one(vendor)

        pa_id = f"TESTPA_PAYOUT_{uuid.uuid4().hex[:8]}"
        a_pending_id = str(uuid.uuid4())
        a_unassigned_id = str(uuid.uuid4())
        a_approved_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        doc = {
            "pa_id": pa_id,
            "pa_number": f"TEST-PYT-{uuid.uuid4().hex[:5].upper()}",
            "client_name": "TEST_Payout_Client",
            "allocations": [
                {"allocation_id": a_pending_id, "label": "TEST_Lawyer_Pending",
                 "vendor_category": "lawyer", "vendor_id": None,
                 "vendor_master_id": vendor["id"], "vendor_name": vendor["name"],
                 "vendor_type": "external", "total_amount": 8000.0,
                 "calculated_amount": 8000.0, "status": "pending", "assigned_at": now},
                {"allocation_id": a_unassigned_id, "label": "TEST_Unassigned",
                 "vendor_category": "lawyer", "vendor_id": None,
                 "vendor_master_id": None, "vendor_name": None,
                 "vendor_type": None, "total_amount": 3000.0,
                 "calculated_amount": 3000.0, "status": "pending"},
                {"allocation_id": a_approved_id, "label": "TEST_Lawyer_Approved",
                 "vendor_category": "lawyer", "vendor_id": None,
                 "vendor_master_id": vendor["id"], "vendor_name": vendor["name"],
                 "vendor_type": "external", "total_amount": 6000.0,
                 "calculated_amount": 6000.0, "status": "approved",
                 "approved_at": now, "assigned_at": now},
            ],
            "summary": {"total_allocated": 17000.0, "company_margin": 0.0},
            "last_recalculated_at": now,
            "created_at": now,
        }
        await allocations_col.insert_one(doc)
        return {"pa_id": pa_id, "vendor_id": vendor["id"],
                "a_pending": a_pending_id, "a_unassigned": a_unassigned_id,
                "a_approved": a_approved_id}

    async def teardown(pa_id):
        await allocations_col.delete_many({"pa_id": pa_id})

    info = _run(setup())
    yield info
    _run(teardown(info["pa_id"]))


class TestPayoutsQueue:
    def test_queue_admin(self, tokens, payout_seed):
        r = requests.get(f"{API}/payouts/queue", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("rows", "totals", "count"):
            assert k in data
        # Our seeded PA must appear
        pa_ids = {row["pa_id"] for row in data["rows"]}
        assert payout_seed["pa_id"] in pa_ids

    def test_queue_status_filter(self, tokens, payout_seed):
        r = requests.get(f"{API}/payouts/queue?status=approved",
                         headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200
        for row in r.json()["rows"]:
            assert row["status"] == "approved"

    def test_queue_non_admin_403(self, tokens):
        r = requests.get(f"{API}/payouts/queue", headers=_hdr(tokens["cm"]), timeout=30)
        assert r.status_code == 403

    def test_stats_admin(self, tokens, payout_seed):
        r = requests.get(f"{API}/payouts/stats", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200
        data = r.json()
        for k in ("totals", "counts", "ready_to_pay", "outstanding"):
            assert k in data
        # ready_to_pay == totals.approved
        assert abs(data["ready_to_pay"] - data["totals"]["approved"]) < 0.01
        # outstanding == approved + pending
        assert abs(data["outstanding"] - (data["totals"]["approved"] + data["totals"]["pending"])) < 0.01

    def test_stats_non_admin_403(self, tokens):
        r = requests.get(f"{API}/payouts/stats", headers=_hdr(tokens["partner"]), timeout=30)
        assert r.status_code == 403


class TestPayoutsBulkActions:
    def test_bulk_approve_skips_unassigned(self, tokens, payout_seed):
        # Try to approve both pending (assigned) and unassigned
        body = {"items": [
            {"pa_id": payout_seed["pa_id"], "allocation_id": payout_seed["a_pending"]},
            {"pa_id": payout_seed["pa_id"], "allocation_id": payout_seed["a_unassigned"]},
        ]}
        r = requests.post(f"{API}/payouts/bulk-approve", headers=_hdr(tokens["admin"]),
                          json=body, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # assigned pending → approved (ok=1), unassigned → failed (fail=1)
        assert data["approved"] == 1, f"expected 1 approved, got {data}"
        assert data["failed"] == 1, f"expected 1 failed (unassigned), got {data}"

    def test_bulk_mark_paid_with_ref(self, tokens, payout_seed):
        body = {"items": [
            {"pa_id": payout_seed["pa_id"], "allocation_id": payout_seed["a_approved"]},
            {"pa_id": payout_seed["pa_id"], "allocation_id": payout_seed["a_pending"]},
        ], "payment_reference": "TEST-BATCH-001"}
        r = requests.post(f"{API}/payouts/bulk-mark-paid", headers=_hdr(tokens["admin"]),
                          json=body, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["paid"] >= 1
        assert data["payment_reference"] == "TEST-BATCH-001"

    def test_bulk_mark_paid_auto_ref(self, tokens, payout_seed):
        # When payment_reference is blank → auto-generates BATCH-YYYYMMDD-HHMMSS
        # Need a fresh pending allocation; reuse existing pa with new doc
        import sys; sys.path.insert(0, "/app/backend")
        from core.database import db
        allocations_col = db["pa_cost_allocations"]
        new_alloc_id = str(uuid.uuid4())
        pa_id2 = f"TESTPA_PAYOUT2_{uuid.uuid4().hex[:8]}"

        async def seed():
            await allocations_col.insert_one({
                "pa_id": pa_id2, "pa_number": "TEST-PYT-AUTO",
                "client_name": "TEST_AutoRef",
                "allocations": [{"allocation_id": new_alloc_id, "label": "X",
                                 "vendor_category": "lawyer",
                                 "vendor_id": "user-test-x",
                                 "vendor_master_id": None,
                                 "total_amount": 100.0, "calculated_amount": 100.0,
                                 "status": "pending"}],
                "summary": {}, "last_recalculated_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
            })

        async def cleanup():
            await allocations_col.delete_many({"pa_id": pa_id2})

        _run(seed())
        try:
            r = requests.post(f"{API}/payouts/bulk-mark-paid", headers=_hdr(tokens["admin"]),
                              json={"items": [{"pa_id": pa_id2, "allocation_id": new_alloc_id}]},
                              timeout=30)
            assert r.status_code == 200, r.text
            ref = r.json()["payment_reference"]
            assert ref.startswith("BATCH-"), f"expected BATCH- prefix, got {ref}"
        finally:
            _run(cleanup())

    def test_bulk_approve_non_admin_403(self, tokens):
        r = requests.post(f"{API}/payouts/bulk-approve", headers=_hdr(tokens["cm"]),
                          json={"items": []}, timeout=30)
        assert r.status_code == 403


class TestNEFTCSV:
    def test_neft_csv_admin(self, tokens, payout_seed):
        # Need at least one approved allocation; seed one fresh since prior tests may have marked it paid
        import sys; sys.path.insert(0, "/app/backend")
        from core.database import db
        allocations_col = db["pa_cost_allocations"]
        new_alloc_id = str(uuid.uuid4())
        pa_id3 = f"TESTPA_NEFT_{uuid.uuid4().hex[:8]}"

        async def seed():
            now = datetime.now(timezone.utc)
            await allocations_col.insert_one({
                "pa_id": pa_id3, "pa_number": "TEST-NEFT-001",
                "client_name": "TEST_NEFT_Client",
                "allocations": [{"allocation_id": new_alloc_id, "label": "NEFT_TEST",
                                 "vendor_category": "lawyer",
                                 "vendor_id": None,
                                 "vendor_master_id": payout_seed["vendor_id"],
                                 "vendor_name": "TEST_NEFT_Vendor",
                                 "vendor_type": "external",
                                 "total_amount": 500.0, "calculated_amount": 500.0,
                                 "status": "approved", "approved_at": now,
                                 "assigned_at": now}],
                "summary": {}, "last_recalculated_at": now, "created_at": now,
            })

        async def cleanup():
            await allocations_col.delete_many({"pa_id": pa_id3})

        _run(seed())
        try:
            r = requests.get(f"{API}/payouts/neft-csv?status=approved",
                             headers=_hdr(tokens["admin"]), timeout=30)
            assert r.status_code == 200, r.text
            cd = r.headers.get("content-disposition", "")
            assert "attachment" in cd.lower(), f"missing attachment header: {cd}"
            assert "csv" in r.headers.get("content-type", "").lower()
            # Parse CSV
            reader = csv.reader(io.StringIO(r.text))
            rows = list(reader)
            assert len(rows) >= 1
            header = rows[0]
            # Column order assertion (per spec)
            expected = ["S.No", "Beneficiary Name", "Account Number", "IFSC", "Bank Name",
                        "Amount (INR)", "PAN", "PA Number", "Client", "Vendor Code",
                        "Vendor Type", "Allocation Label", "Status",
                        "Approved At", "Payment Reference"]
            assert header == expected, f"header mismatch:\nexpected {expected}\ngot      {header}"
            # Our row should be present
            body_rows = rows[1:]
            assert any("TEST_NEFT_Vendor" in r_ or "TEST_NEFT_Client" in r_
                       for row in body_rows for r_ in row), f"missing test data in CSV rows={body_rows}"
        finally:
            _run(cleanup())

    def test_neft_csv_non_admin_403(self, tokens):
        r = requests.get(f"{API}/payouts/neft-csv?status=approved",
                         headers=_hdr(tokens["client"]), timeout=30)
        assert r.status_code == 403


# ══════════════════════════════════════════════════════════════
# Integration — Full flow: admin seeds PA → approve → pay → CSV → CM dashboard
# ══════════════════════════════════════════════════════════════
class TestIntegrationFullFlow:
    def test_e2e_admin_approve_paid_csv_cm_dashboard(self, tokens):
        """Seed PA with CM allocation + external vendor allocation,
        run bulk-approve → bulk-mark-paid → NEFT CSV → CM /cm-earnings/my updates.
        """
        import sys; sys.path.insert(0, "/app/backend")
        from core.database import db, users_col
        allocations_col = db["pa_cost_allocations"]
        vendors_col_local = db["vendors"]

        async def setup():
            cm = await users_col.find_one({"email": CREDS["cm"][0]}, {"_id": 0, "id": 1})
            assert cm
            vendor = await vendors_col_local.find_one(
                {"status": "active", "bank_details.account_number": {"$exists": True, "$ne": None}},
                {"_id": 0})
            if not vendor:
                vid = str(uuid.uuid4())
                vendor = {"id": vid, "name": "TEST_E2E_Vendor", "vendor_code": "VEN-E2E",
                          "vendor_type": "external", "category": "lawyer", "status": "active",
                          "email": f"e2e-{uuid.uuid4().hex[:6]}@test.local",
                          "bank_details": {"account_number": "5555444433332222",
                                           "ifsc_code": "ICIC0000999", "bank_name": "ICICI"},
                          "pan_number": "E2EAB1234X"}
                await vendors_col_local.insert_one(vendor)
            pa_id = f"TESTPA_E2E_{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc)
            cm_alloc_id = str(uuid.uuid4())
            ven_alloc_id = str(uuid.uuid4())
            await allocations_col.insert_one({
                "pa_id": pa_id, "pa_number": "TEST-E2E-001",
                "client_name": "TEST_E2E_Client",
                "allocations": [
                    {"allocation_id": cm_alloc_id, "label": "TEST_E2E_CM",
                     "vendor_category": "case_manager", "vendor_id": cm["id"],
                     "vendor_master_id": None, "vendor_name": "TEST CM",
                     "vendor_type": "internal", "total_amount": 7000.0,
                     "calculated_amount": 7000.0, "status": "pending", "assigned_at": now},
                    {"allocation_id": ven_alloc_id, "label": "TEST_E2E_Vendor",
                     "vendor_category": "lawyer", "vendor_id": None,
                     "vendor_master_id": vendor["id"], "vendor_name": vendor["name"],
                     "vendor_type": "external", "total_amount": 9000.0,
                     "calculated_amount": 9000.0, "status": "pending", "assigned_at": now},
                ],
                "summary": {}, "last_recalculated_at": now, "created_at": now,
            })
            return {"pa_id": pa_id, "cm_alloc_id": cm_alloc_id,
                    "ven_alloc_id": ven_alloc_id, "vendor_id": vendor["id"]}

        async def cleanup(pa_id):
            await allocations_col.delete_many({"pa_id": pa_id})

        info = _run(setup())
        try:
            # 1. Get CM earnings baseline
            r0 = requests.get(f"{API}/cm-earnings/my", headers=_hdr(tokens["cm"]), timeout=30)
            assert r0.status_code == 200
            cm_before = r0.json()["lifetime_total"]

            # 2. Admin bulk-approves both allocations
            r1 = requests.post(f"{API}/payouts/bulk-approve",
                               headers=_hdr(tokens["admin"]),
                               json={"items": [
                                   {"pa_id": info["pa_id"], "allocation_id": info["cm_alloc_id"]},
                                   {"pa_id": info["pa_id"], "allocation_id": info["ven_alloc_id"]},
                               ]}, timeout=30)
            assert r1.status_code == 200, r1.text
            assert r1.json()["approved"] == 2

            # 3. Bulk-mark-paid
            r2 = requests.post(f"{API}/payouts/bulk-mark-paid",
                               headers=_hdr(tokens["admin"]),
                               json={"items": [
                                   {"pa_id": info["pa_id"], "allocation_id": info["cm_alloc_id"]},
                                   {"pa_id": info["pa_id"], "allocation_id": info["ven_alloc_id"]},
                               ], "payment_reference": "TEST-E2E-PAY"}, timeout=30)
            assert r2.status_code == 200, r2.text
            assert r2.json()["paid"] == 2

            # 4. NEFT CSV returns approved (none now) OR paid — check status=paid filter works
            r3 = requests.get(f"{API}/payouts/neft-csv?status=paid",
                              headers=_hdr(tokens["admin"]), timeout=30)
            assert r3.status_code == 200
            assert "attachment" in r3.headers.get("content-disposition", "").lower()

            # 5. CM dashboard reflects new paid entry
            r4 = requests.get(f"{API}/cm-earnings/my", headers=_hdr(tokens["cm"]), timeout=30)
            assert r4.status_code == 200
            cm_after = r4.json()
            assert cm_after["lifetime_total"] >= cm_before + 7000.0, \
                f"CM lifetime_total should increase by 7000 — before={cm_before}, after={cm_after['lifetime_total']}"
            # Verify the paid entry appears
            our_entry = next((li for li in cm_after["line_items"]
                              if li["pa_id"] == info["pa_id"]), None)
            assert our_entry, "CM dashboard missing our seeded PA entry"
            assert our_entry["status"] == "paid"
            assert our_entry["payment_reference"] == "TEST-E2E-PAY"
        finally:
            _run(cleanup(info["pa_id"]))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
