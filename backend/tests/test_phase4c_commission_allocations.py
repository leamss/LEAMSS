"""Phase 4C.3 (Auto-Allocation Engine) + 4C.4 (Sales Commission Slabs) backend tests.

Covers:
  - Slab auto-seed, CRUD, validation, RBAC
  - /sales-commission/my, /all, /leaderboard
  - Approve / mark-paid / reverse transitions
  - Slab matching (cumulative monthly revenue → upgraded slab on 2nd deal)
  - Idempotency (same PA twice → no duplicate entry)
  - Allocations: get, recalculate, assign-vendor, approve, mark-paid,
    visa-approved bonuses, refund-clawback
  - Regression: cost-structures, vendors, vendors/categories, /api/auth/login, pre-assessment list
"""
import os
import time
import uuid
import asyncio
import pytest
import requests

# Single shared event loop for direct motor DB operations (avoids 'Event loop is closed' across tests)
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
    "partner": ("partner@leamss.com", "Partner@123"),
    "sexec": ("sexec-test@leamss.com", "Pass@1234"),
    "smgr": ("smgr-test@leamss.com", "Pass@1234"),
    "cm": ("manager@leamss.com", "Manager@123"),
    "client": ("client@leamss.com", "Client@123"),
}


# ──────────────────────────────────────────────────────────────
# Auth helpers / fixtures
# ──────────────────────────────────────────────────────────────
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


# ──────────────────────────────────────────────────────────────
# Regression — basic auth + existing routes
# ──────────────────────────────────────────────────────────────
class TestRegression:
    def test_login_admin(self, tokens):
        assert tokens["admin"]

    def test_cost_structures(self, tokens):
        r = requests.get(f"{API}/products/cost-structures", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Either list or {structures: [...]}
        items = data if isinstance(data, list) else data.get("structures") or data.get("items") or []
        assert len(items) >= 1

    def test_vendors_list(self, tokens):
        r = requests.get(f"{API}/vendors", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text

    def test_vendor_categories(self, tokens):
        r = requests.get(f"{API}/vendors/categories", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text

    def test_pre_assessment_admin_queue(self, tokens):
        r = requests.get(f"{API}/pre-assessment/admin/queue", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text


# ──────────────────────────────────────────────────────────────
# Phase 4C.4 — Slabs
# ──────────────────────────────────────────────────────────────
class TestSlabs:
    def test_slabs_auto_seed_on_first_get(self, tokens):
        r = requests.get(f"{API}/sales-commission/slabs", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "slabs" in data
        keys = [s["key"] for s in data["slabs"]]
        # Bronze/Silver/Gold should exist (seeded if collection was empty)
        assert "bronze" in keys
        assert "silver" in keys
        assert "gold" in keys
        # rate_pct validation
        for s in data["slabs"]:
            assert "rate_pct" in s and isinstance(s["rate_pct"], (int, float))

    def test_slabs_seed_idempotent(self, tokens):
        r = requests.post(f"{API}/sales-commission/slabs/seed", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200
        # 0 means collection already populated → no re-seed
        assert r.json().get("seeded") == 0

    def test_slabs_client_403(self, tokens):
        if not tokens.get("client"):
            pytest.skip("client login unavailable")
        # client should not see slab management nor /my
        r = requests.get(f"{API}/sales-commission/my", headers=_hdr(tokens["client"]), timeout=30)
        assert r.status_code == 403, f"Expected 403 for client /my, got {r.status_code}"

    def test_create_slab_validation_max_lt_min(self, tokens):
        body = {"key": "test_bad", "name": "Bad", "min_revenue": 1000, "max_revenue": 500, "rate_pct": 3}
        r = requests.post(f"{API}/sales-commission/slabs", headers=_hdr(tokens["admin"]), json=body, timeout=30)
        assert r.status_code == 400, r.text

    def test_create_and_patch_and_delete_slab(self, tokens):
        key = f"test_slab_{uuid.uuid4().hex[:6]}"
        # key pattern only allows [a-z_] → strip digits
        key = "".join(c for c in key if c.isalpha() or c == "_")
        body = {"key": key, "name": "TEST Slab", "min_revenue": 0, "max_revenue": 100, "rate_pct": 1.5}
        r = requests.post(f"{API}/sales-commission/slabs", headers=_hdr(tokens["admin"]), json=body, timeout=30)
        assert r.status_code == 200, r.text
        slab = r.json()["slab"]
        sid = slab["id"]

        # duplicate key → 409
        r2 = requests.post(f"{API}/sales-commission/slabs", headers=_hdr(tokens["admin"]), json=body, timeout=30)
        assert r2.status_code == 409

        # patch
        rp = requests.patch(f"{API}/sales-commission/slabs/{sid}", headers=_hdr(tokens["admin"]),
                            json={"rate_pct": 2.5}, timeout=30)
        assert rp.status_code == 200, rp.text

        # delete non-system → allowed
        rd = requests.delete(f"{API}/sales-commission/slabs/{sid}", headers=_hdr(tokens["admin"]), timeout=30)
        assert rd.status_code == 200, rd.text

    def test_delete_system_slab_protected(self, tokens):
        r = requests.get(f"{API}/sales-commission/slabs", headers=_hdr(tokens["admin"]), timeout=30)
        sys_slab = next((s for s in r.json()["slabs"] if s.get("is_system")), None)
        assert sys_slab, "Need at least one system slab"
        rd = requests.delete(f"{API}/sales-commission/slabs/{sys_slab['id']}",
                             headers=_hdr(tokens["admin"]), timeout=30)
        assert rd.status_code == 400, rd.text
        assert "system" in rd.text.lower()


# ──────────────────────────────────────────────────────────────
# Phase 4C.4 — /my, /all, /leaderboard, RBAC
# ──────────────────────────────────────────────────────────────
class TestCommissionViews:
    def test_my_as_partner(self, tokens):
        r = requests.get(f"{API}/sales-commission/my", headers=_hdr(tokens["partner"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Required summary keys
        for k in ("current_slab", "next_slab", "gap_to_next_slab", "total_commission",
                  "deal_count", "entries", "period"):
            assert k in data, f"missing key: {k}"

    def test_my_as_sexec(self, tokens):
        if not tokens.get("sexec"):
            pytest.skip("sexec login unavailable")
        r = requests.get(f"{API}/sales-commission/my", headers=_hdr(tokens["sexec"]), timeout=30)
        assert r.status_code == 200, r.text

    def test_my_client_403(self, tokens):
        if not tokens.get("client"):
            pytest.skip("client login unavailable")
        r = requests.get(f"{API}/sales-commission/my", headers=_hdr(tokens["client"]), timeout=30)
        assert r.status_code == 403

    def test_all_admin(self, tokens):
        r = requests.get(f"{API}/sales-commission/all", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "entries" in data and "total_revenue" in data and "total_commission" in data

    def test_all_client_403(self, tokens):
        if not tokens.get("client"):
            pytest.skip("client login unavailable")
        r = requests.get(f"{API}/sales-commission/all", headers=_hdr(tokens["client"]), timeout=30)
        assert r.status_code == 403

    def test_leaderboard_admin(self, tokens):
        r = requests.get(f"{API}/sales-commission/leaderboard", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text
        assert "leaderboard" in r.json()


# ──────────────────────────────────────────────────────────────
# Phase 4C.4 — Slab matching (cumulative) + Idempotency via direct logic
# Use direct DB access to seed two PA-like dicts and call apply_commission_for_pa
# ──────────────────────────────────────────────────────────────
class TestSlabMatching:
    def test_cumulative_slab_upgrade_and_idempotency(self):
        """Rep with 0 prior revenue: 1st PA ₹3L → Bronze 5% → ₹15k.
        2nd PA ₹4L (cumulative ₹7L) → Silver 7% → ₹28k.
        Same PA twice → no duplicate.
        """
        import sys
        sys.path.insert(0, "/app/backend")
        from core.commission_logic import (
            apply_commission_for_pa, ensure_default_slabs, entries_col, _period_key,
        )
        from core.database import users_col

        async def run():
            await ensure_default_slabs()
            # Find a sales_executive user to attribute to
            user = await users_col.find_one({"email": CREDS["sexec"][0]}, {"_id": 0, "id": 1, "rbac_role": 1})
            assert user, "sexec user must exist"
            uid = user["id"]
            period = _period_key()

            # Cleanup any prior test entries for this user & period
            await entries_col.delete_many({"user_id": uid, "period": period,
                                            "pa_id": {"$regex": "^TESTPA_"}})

            pa1 = {
                "id": f"TESTPA_{uuid.uuid4().hex[:8]}",
                "pa_number": "TEST-PA-001",
                "created_by_user_id": uid,
                "proposal_fee": 300000,
                "client_name": "TEST_Client_A",
            }
            e1 = await apply_commission_for_pa(pa1)
            assert e1 is not None, "1st commission entry should be created"
            assert e1["slab_key"] == "bronze", f"expected bronze, got {e1['slab_key']}"
            assert abs(e1["commission_amount"] - 15000.0) < 0.5

            # Idempotency: same PA again → return existing, no duplicate
            e1b = await apply_commission_for_pa(pa1)
            assert e1b is not None
            assert e1b["id"] == e1["id"], "Idempotency broken — duplicate entry created"
            count1 = await entries_col.count_documents({"pa_id": pa1["id"]})
            assert count1 == 1

            # 2nd PA — cumulative crosses ₹5L → upgraded to Silver
            pa2 = {
                "id": f"TESTPA_{uuid.uuid4().hex[:8]}",
                "pa_number": "TEST-PA-002",
                "created_by_user_id": uid,
                "proposal_fee": 400000,
                "client_name": "TEST_Client_B",
            }
            e2 = await apply_commission_for_pa(pa2)
            assert e2 is not None
            assert e2["slab_key"] == "silver", \
                f"expected silver after cumulative ₹7L, got {e2['slab_key']} (achieved_after={e2.get('achieved_after')})"
            assert abs(e2["commission_amount"] - 28000.0) < 0.5

            # Cleanup
            await entries_col.delete_many({"pa_id": {"$in": [pa1["id"], pa2["id"]]}})

        _run(run())


# ──────────────────────────────────────────────────────────────
# Phase 4C.4 — Entry workflow (approve/mark-paid/reverse) via direct insert
# ──────────────────────────────────────────────────────────────
class TestEntryWorkflow:
    def test_approve_mark_paid_reverse(self, tokens):
        import sys; sys.path.insert(0, "/app/backend")
        from core.commission_logic import entries_col

        async def seed():
            from datetime import datetime, timezone
            eid = str(uuid.uuid4())
            doc = {
                "id": eid, "user_id": "TEST_USER_X", "pa_id": f"TESTPA_{uuid.uuid4().hex[:8]}",
                "period": "2026-01", "revenue": 100000, "commission_amount": 5000,
                "status": "pending", "slab_key": "bronze", "rate_pct": 5.0,
                "applied_at": datetime.now(timezone.utc), "created_at": datetime.now(timezone.utc),
            }
            await entries_col.insert_one(doc)
            return eid

        async def cleanup(eid):
            await entries_col.delete_one({"id": eid})

        eid = _run(seed())
        try:
            # approve
            r = requests.post(f"{API}/sales-commission/entries/{eid}/approve",
                              headers=_hdr(tokens["admin"]), timeout=30)
            assert r.status_code == 200, r.text
            assert r.json()["entry"]["status"] == "approved"

            # cannot re-approve
            r2 = requests.post(f"{API}/sales-commission/entries/{eid}/approve",
                               headers=_hdr(tokens["admin"]), timeout=30)
            assert r2.status_code == 404

            # mark-paid
            r3 = requests.post(f"{API}/sales-commission/entries/{eid}/mark-paid",
                               headers=_hdr(tokens["admin"]), json={"payment_reference": "TEST-REF"}, timeout=30)
            assert r3.status_code == 200, r3.text
            assert r3.json()["entry"]["status"] == "paid"

            # reverse
            r4 = requests.post(f"{API}/sales-commission/entries/{eid}/reverse",
                               headers=_hdr(tokens["admin"]), timeout=30)
            assert r4.status_code == 200, r4.text
            assert r4.json()["entry"]["status"] == "reversed"
        finally:
            _run(cleanup(eid))


# ──────────────────────────────────────────────────────────────
# Phase 4C.3 — Allocations on a real or seeded PA
# We use direct DB seeding to create a case_created PA tied to an existing
# cost structure, then exercise the API endpoints.
# ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def seeded_pa():
    """Seed a case_created PA referencing an existing cost structure.
    Returns dict with pa_id, cost_structure used, and cleanup at module end.
    """
    import sys; sys.path.insert(0, "/app/backend")
    from core.database import pre_assessments_col, db, users_col
    cost_structures_col = db["product_cost_structures"]
    allocations_col = db["pa_cost_allocations"]
    entries_col = db["sales_commission_entries"]

    async def setup():
        # Pick a cost structure with at least one allocation
        struct = await cost_structures_col.find_one(
            {"is_active": True, "deleted_at": None, "cost_allocations.0": {"$exists": True}},
            {"_id": 0},
        )
        if not struct:
            return None
        # use partner user as creator (so apply_commission auto-creates entry)
        partner = await users_col.find_one({"email": CREDS["partner"][0]}, {"_id": 0, "id": 1})
        pa_id = f"TESTPA_{uuid.uuid4().hex[:10]}"
        pa = {
            "id": pa_id,
            "pa_number": f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "client_name": "TEST_Phase4C3_Client",
            "country": struct.get("country") or "Canada",
            "service_type": struct.get("visa_type") or "PR",
            "product_name": struct.get("product_name"),
            "proposal_fee": 500000,
            "final_amount": 500000,
            "stage": "case_created",
            "status": "active",
            "created_by_user_id": partner["id"] if partner else None,
            "partner_id": partner["id"] if partner else None,
            "case_manager_id": None,
        }
        await pre_assessments_col.insert_one(pa)
        return {"pa_id": pa_id, "struct": struct}

    async def teardown(pa_id):
        await pre_assessments_col.delete_one({"id": pa_id})
        await allocations_col.delete_many({"pa_id": pa_id})
        await entries_col.delete_many({"pa_id": pa_id})

    info = _run(setup())
    if not info:
        pytest.skip("No cost structure available to seed PA")
    yield info
    _run(teardown(info["pa_id"]))


class TestAllocations:
    def test_get_allocations_non_case_created(self, tokens):
        # Find a PA that's not in case_created
        r = requests.get(f"{API}/pre-assessment/admin/queue", headers=_hdr(tokens["admin"]), timeout=30)
        data = r.json()
        items = data if isinstance(data, list) else data.get("items") or data.get("pre_assessments") or data.get("queue") or []
        non_cc = next((p for p in items if p.get("stage") and p.get("stage") != "case_created"), None)
        if not non_cc:
            pytest.skip("No non case_created PA available")
        rg = requests.get(f"{API}/pa/{non_cc['id']}/allocations", headers=_hdr(tokens["admin"]), timeout=30)
        assert rg.status_code == 200, rg.text
        assert rg.json().get("has_allocations") is False

    def test_get_allocations_auto_build(self, tokens, seeded_pa):
        pa_id = seeded_pa["pa_id"]
        r = requests.get(f"{API}/pa/{pa_id}/allocations", headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("has_allocations") is True
        alloc = data["allocations"]
        assert alloc["pa_id"] == pa_id
        assert isinstance(alloc.get("allocations"), list) and len(alloc["allocations"]) >= 1
        # summary present
        for k in ("total_allocated", "company_margin"):
            assert k in alloc.get("summary", {})

    def test_recalculate(self, tokens, seeded_pa):
        r = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/recalculate",
                          headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200, r.text

    def test_recalculate_no_match(self, tokens):
        import sys; sys.path.insert(0, "/app/backend")
        from core.database import pre_assessments_col
        async def seed():
            pid = f"TESTPA_{uuid.uuid4().hex[:10]}"
            await pre_assessments_col.insert_one({
                "id": pid, "pa_number": "TEST-NOMATCH",
                "client_name": "TEST_NoMatch",
                "country": "Antarctica", "service_type": "NoSuchVisa",
                "product_name": "GHOST_PRODUCT_DOES_NOT_EXIST",
                "stage": "case_created", "proposal_fee": 1000,
            })
            return pid
        async def cleanup(pid):
            await pre_assessments_col.delete_one({"id": pid})
        pid = _run(seed())
        try:
            r = requests.post(f"{API}/pa/{pid}/allocations/recalculate",
                              headers=_hdr(tokens["admin"]), timeout=30)
            assert r.status_code == 400, r.text
        finally:
            _run(cleanup(pid))

    def test_assign_vendor_invalid(self, tokens, seeded_pa):
        # Get allocations first
        r = requests.get(f"{API}/pa/{seeded_pa['pa_id']}/allocations",
                         headers=_hdr(tokens["admin"]), timeout=30)
        alloc = r.json()["allocations"]["allocations"][0]
        aid = alloc["allocation_id"]
        # Try fake vendor_id
        rv = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/{aid}/assign-vendor",
                           headers=_hdr(tokens["admin"]),
                           json={"vendor_id": "non-existent-vendor"}, timeout=30)
        assert rv.status_code == 400, rv.text

    def test_assign_vendor_and_approve_and_pay(self, tokens, seeded_pa):
        import sys; sys.path.insert(0, "/app/backend")
        from core.database import db
        vendors_col = db["vendors"]

        async def get_or_create_vendor():
            v = await vendors_col.find_one({"status": "active"}, {"_id": 0})
            if v:
                return v
            vid = str(uuid.uuid4())
            doc = {"id": vid, "name": "TEST_Vendor_Lawyer", "vendor_type": "external",
                   "category": "lawyer", "status": "active", "email": "v@test.local"}
            await vendors_col.insert_one(doc)
            return doc
        vendor = _run(get_or_create_vendor())

        # find an unassigned allocation (lawyer or tutor likely)
        r = requests.get(f"{API}/pa/{seeded_pa['pa_id']}/allocations",
                         headers=_hdr(tokens["admin"]), timeout=30)
        allocs = r.json()["allocations"]["allocations"]
        target = next((a for a in allocs if not a.get("vendor_id")), allocs[0])
        aid = target["allocation_id"]

        # Approve unassigned → 400 (if unassigned)
        if not target.get("vendor_id"):
            ra = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/{aid}/approve",
                               headers=_hdr(tokens["admin"]), timeout=30)
            assert ra.status_code == 400, ra.text

        # Assign
        rv = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/{aid}/assign-vendor",
                           headers=_hdr(tokens["admin"]),
                           json={"vendor_id": vendor["id"]}, timeout=30)
        assert rv.status_code == 200, rv.text

        # Approve
        ra2 = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/{aid}/approve",
                            headers=_hdr(tokens["admin"]), timeout=30)
        assert ra2.status_code == 200, ra2.text
        # find updated state
        updated = next(a for a in ra2.json()["allocations"]["allocations"] if a["allocation_id"] == aid)
        assert updated["status"] == "approved"

        # Mark paid
        rp = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/{aid}/mark-paid",
                           headers=_hdr(tokens["admin"]),
                           json={"payment_reference": "TEST-PAY-001"}, timeout=30)
        assert rp.status_code == 200, rp.text
        paid = next(a for a in rp.json()["allocations"]["allocations"] if a["allocation_id"] == aid)
        assert paid["status"] == "paid"
        assert paid.get("payment_reference") == "TEST-PAY-001"

    def test_visa_approved_idempotent(self, tokens, seeded_pa):
        r1 = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/visa-approved",
                           headers=_hdr(tokens["admin"]), timeout=30)
        # Could be 200 (applied) or 400 (no bonuses) — both acceptable
        assert r1.status_code in (200, 400), r1.text
        if r1.status_code == 200:
            m1 = r1.json()["allocations"]["milestones"]
            assert m1.get("visa_approved") is True

            # second call should be a no-op (still 200, same milestone)
            r2 = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/visa-approved",
                               headers=_hdr(tokens["admin"]), timeout=30)
            assert r2.status_code == 200
            assert r2.json()["allocations"]["milestones"].get("visa_approved") is True

    def test_refund_clawback_idempotent(self, tokens, seeded_pa):
        # capture pre-state
        r0 = requests.get(f"{API}/pa/{seeded_pa['pa_id']}/allocations",
                          headers=_hdr(tokens["admin"]), timeout=30)
        pre_allocations = r0.json()["allocations"]["allocations"]
        # pick an unpaid alloc
        before = next((a for a in pre_allocations if a.get("status") != "paid"), None)

        r1 = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/refund-clawback?recovery_rate=0.5",
                           headers=_hdr(tokens["admin"]), timeout=30)
        assert r1.status_code == 200, r1.text
        assert r1.json()["allocations"]["milestones"].get("refunded") is True

        if before:
            after = next((a for a in r1.json()["allocations"]["allocations"]
                          if a["allocation_id"] == before["allocation_id"]), None)
            if after and before.get("calculated_amount", 0) > 0:
                assert after["calculated_amount"] < before["calculated_amount"] + 0.01

        # second call → still refunded=True, no further reduction
        r2 = requests.post(f"{API}/pa/{seeded_pa['pa_id']}/allocations/refund-clawback?recovery_rate=0.5",
                           headers=_hdr(tokens["admin"]), timeout=30)
        assert r2.status_code == 200
        # Idempotency check — second clawback should NOT further reduce
        if before:
            a1 = next((a for a in r1.json()["allocations"]["allocations"]
                       if a["allocation_id"] == before["allocation_id"]), None)
            a2 = next((a for a in r2.json()["allocations"]["allocations"]
                       if a["allocation_id"] == before["allocation_id"]), None)
            if a1 and a2:
                assert abs(a1["calculated_amount"] - a2["calculated_amount"]) < 0.01

    def test_allocations_client_403(self, tokens):
        if not tokens.get("client"):
            pytest.skip("client login unavailable")
        r = requests.get(f"{API}/pa/anyid/allocations", headers=_hdr(tokens["client"]), timeout=30)
        assert r.status_code in (403, 404)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
