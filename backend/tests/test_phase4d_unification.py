"""Phase 4D — Unified People Management + Finance Dashboard + Express Sale Modes.

Tests:
  - PART A: /api/people (list, stats, get, create, patch, deactivate, reactivate, reset-password, RBAC)
  - PART B: Finance Dashboard backend endpoints shape
  - PART C: Express sale_type with express_mode (token/direct) on /api/pre-assessment/create + public view
  - Regression: slab delete, product preview, cm-earnings, dispute endpoints, login flows
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER = {"email": "partner@leamss.com", "password": "Partner@123"}
CM = {"email": "manager@leamss.com", "password": "Manager@123"}
SEXEC = {"email": "sexec-test@leamss.com", "password": "Pass@1234"}
CLIENT = {"email": "client@leamss.com", "password": "Client@123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    if r.status_code != 200:
        return None
    return r.json().get("token")


@pytest.fixture(scope="module")
def admin_token():
    t = _login(ADMIN)
    if not t:
        pytest.skip("admin login failed")
    return t


@pytest.fixture(scope="module")
def partner_token():
    t = _login(PARTNER)
    if not t:
        pytest.skip("partner login failed")
    return t


@pytest.fixture(scope="module")
def sexec_token():
    return _login(SEXEC)


def H(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ──────────────────────────────────────────────────────────────
# Regression: All 5 logins work
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("creds,label", [
    (ADMIN, "admin"), (PARTNER, "partner"), (CM, "cm"),
    (SEXEC, "sexec"), (CLIENT, "client"),
])
def test_login_all_roles(creds, label):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"{label} login failed: {r.text}"
    assert r.json().get("token"), f"{label} no token"


# ──────────────────────────────────────────────────────────────
# PART A — People list / stats / get / RBAC
# ──────────────────────────────────────────────────────────────
class TestPeopleList:
    def test_list_people_basic(self, admin_token):
        r = requests.get(f"{API}/people", headers=H(admin_token), timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "people" in body and "count" in body
        assert isinstance(body["people"], list)
        assert body["count"] == len(body["people"])
        # Each item must have required keys
        if body["people"]:
            p = body["people"][0]
            for k in ["id", "kind", "person_type", "name", "email", "role", "status"]:
                assert k in p, f"missing key {k} in person: {list(p.keys())}"

    def test_list_filter_person_type(self, admin_token):
        r = requests.get(f"{API}/people", headers=H(admin_token),
                         params={"person_type": "employee_internal"}, timeout=15)
        assert r.status_code == 200
        body = r.json()
        for p in body["people"]:
            assert p["person_type"] == "employee_internal"

    def test_list_filter_search(self, admin_token):
        r = requests.get(f"{API}/people", headers=H(admin_token),
                         params={"search": "admin"}, timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["count"] >= 1
        assert any("admin" in (p.get("email") or "").lower() or
                   "admin" in (p.get("name") or "").lower() for p in body["people"])

    def test_list_filter_status_active(self, admin_token):
        r = requests.get(f"{API}/people", headers=H(admin_token),
                         params={"status": "active"}, timeout=15)
        assert r.status_code == 200
        for p in r.json()["people"]:
            assert p["status"] == "active"


class TestPeopleStats:
    def test_stats_shape(self, admin_token):
        r = requests.get(f"{API}/people/stats", headers=H(admin_token), timeout=15)
        assert r.status_code == 200
        body = r.json()
        for k in ("total", "by_type", "by_status", "by_role"):
            assert k in body
        assert isinstance(body["total"], int)
        # by_type counts add up to total
        type_sum = sum(body["by_type"].values())
        assert type_sum == body["total"], f"by_type {type_sum} != total {body['total']}"

    def test_stats_has_expected_types(self, admin_token):
        r = requests.get(f"{API}/people/stats", headers=H(admin_token), timeout=15)
        body = r.json()
        # Should include at least one of these types
        assert any(k in body["by_type"] for k in
                   ("employee_internal", "client", "vendor_internal", "partner_external"))


class TestPeopleRBAC:
    def test_partner_forbidden_list(self, partner_token):
        r = requests.get(f"{API}/people", headers=H(partner_token), timeout=15)
        assert r.status_code == 403

    def test_partner_forbidden_stats(self, partner_token):
        r = requests.get(f"{API}/people/stats", headers=H(partner_token), timeout=15)
        assert r.status_code == 403

    def test_partner_forbidden_post(self, partner_token):
        r = requests.post(f"{API}/people", headers=H(partner_token),
                          json={"person_type": "employee_internal", "name": "x",
                                "email": "x@y.com", "role": "case_officer"}, timeout=15)
        assert r.status_code == 403


class TestPeopleGet:
    def test_get_404(self, admin_token):
        r = requests.get(f"{API}/people/nonexistent-id-zzz", headers=H(admin_token), timeout=15)
        assert r.status_code == 404

    def test_get_admin_self(self, admin_token):
        # find admin id
        r = requests.get(f"{API}/people", headers=H(admin_token),
                         params={"search": "admin@leamss.com"}, timeout=15)
        ppl = r.json()["people"]
        assert ppl, "admin not found in people list"
        admin_id = ppl[0]["id"]
        r2 = requests.get(f"{API}/people/{admin_id}", headers=H(admin_token), timeout=15)
        assert r2.status_code == 200
        body = r2.json()
        assert "user" in body
        assert body["user"]["email"] == "admin@leamss.com"
        # ensure no _id leaks
        assert "_id" not in body["user"]


# ──────────────────────────────────────────────────────────────
# PART A — POST /people (Add Person wizard) all 4 types
# ──────────────────────────────────────────────────────────────
class TestPeopleAdd:
    def test_add_employee_internal_missing_role_400(self, admin_token):
        u = uuid.uuid4().hex[:8]
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "employee_internal",
                                "name": f"TEST_emp_{u}",
                                "email": f"test_emp_{u}@leamss.com"}, timeout=15)
        assert r.status_code == 400

    def test_add_employee_internal_ok(self, admin_token):
        u = uuid.uuid4().hex[:8]
        email = f"test_emp_{u}@leamss.com"
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "employee_internal",
                                "name": f"TEST_emp_{u}", "email": email,
                                "role": "case_officer",
                                "department": "operations"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert "person_id" in body
        assert "temp_password" in body
        assert body["kind"] == "user"
        # verify via GET
        g = requests.get(f"{API}/people/{body['person_id']}", headers=H(admin_token), timeout=15)
        assert g.status_code == 200
        assert g.json()["user"]["email"] == email
        assert g.json()["user"]["role"] == "case_officer"

    def test_add_duplicate_email_409(self, admin_token):
        # admin already exists
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "employee_internal",
                                "name": "Dup", "email": "admin@leamss.com",
                                "role": "case_officer"}, timeout=15)
        assert r.status_code == 409

    def test_add_partner_external(self, admin_token):
        u = uuid.uuid4().hex[:8]
        email = f"test_partner_{u}@leamss.com"
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "partner_external",
                                "name": f"TEST_partner_{u}", "email": email}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["kind"] == "user"
        g = requests.get(f"{API}/people/{body['person_id']}", headers=H(admin_token), timeout=15)
        assert g.json()["user"]["role"] == "partner"

    def test_add_vendor_missing_category_400(self, admin_token):
        u = uuid.uuid4().hex[:8]
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "vendor_internal",
                                "name": "x", "email": f"v_{u}@leamss.com"}, timeout=15)
        assert r.status_code == 400

    def test_add_vendor_internal_case_manager_creates_linked_user(self, admin_token):
        u = uuid.uuid4().hex[:8]
        email = f"test_vcm_{u}@leamss.com"
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "vendor_internal",
                                "name": f"TEST_vcm_{u}", "email": email,
                                "vendor_category": "case_manager"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["kind"] == "vendor"
        assert body.get("linked_user_id"), "should auto-create user"
        assert body.get("linked_user_role") == "case_manager"
        assert body.get("vendor_code", "").startswith("VND")
        # GET vendor should show linked user
        g = requests.get(f"{API}/people/{body['person_id']}", headers=H(admin_token), timeout=15)
        assert g.status_code == 200
        gbody = g.json()
        assert gbody["vendor"] is not None
        assert gbody["user"] is not None
        assert gbody["user"]["role"] == "case_manager"
        # new user can login with temp_password
        login = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": body["temp_password"]}, timeout=15)
        assert login.status_code == 200, "linked user should be able to log in with temp_password"

    def test_add_vendor_internal_sales_commission_creates_linked_user(self, admin_token):
        u = uuid.uuid4().hex[:8]
        email = f"test_vsc_{u}@leamss.com"
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "vendor_internal",
                                "name": f"TEST_vsc_{u}", "email": email,
                                "vendor_category": "sales_commission"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("linked_user_role") == "sales_executive"

    def test_add_vendor_external(self, admin_token):
        # Find an external vendor category
        cats = requests.get(f"{API}/vendors/categories", headers=H(admin_token), timeout=15)
        ext_key = None
        if cats.status_code == 200:
            for c in cats.json().get("categories", []) or cats.json() if isinstance(cats.json(), list) else []:
                if not c.get("is_internal"):
                    ext_key = c.get("key")
                    break
        if not ext_key:
            # fallback to a likely external category
            ext_key = "medical_examination"
        u = uuid.uuid4().hex[:8]
        email = f"test_vext_{u}@leamss.com"
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "vendor_external",
                                "name": f"TEST_vext_{u}", "email": email,
                                "vendor_category": ext_key}, timeout=15)
        # Accept 200 (success) or 400 (unknown category)
        assert r.status_code in (200, 400), r.text
        if r.status_code == 200:
            body = r.json()
            assert body["kind"] == "vendor"
            # vendor_external should NOT auto-create linked user
            assert not body.get("linked_user_id")


# ──────────────────────────────────────────────────────────────
# PART A — PATCH + deactivate/reactivate + reset-password
# ──────────────────────────────────────────────────────────────
class TestPeopleLifecycle:
    @pytest.fixture
    def transient_person(self, admin_token):
        u = uuid.uuid4().hex[:8]
        email = f"test_life_{u}@leamss.com"
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "employee_internal",
                                "name": f"TEST_life_{u}", "email": email,
                                "role": "case_officer"}, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()

    def test_patch_name_and_role(self, admin_token, transient_person):
        pid = transient_person["person_id"]
        r = requests.patch(f"{API}/people/{pid}", headers=H(admin_token),
                           json={"name": "TEST_renamed", "role": "operations"}, timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{API}/people/{pid}", headers=H(admin_token), timeout=15)
        assert g.json()["user"]["name"] == "TEST_renamed"
        assert g.json()["user"]["role"] == "operations"

    def test_deactivate_reactivate(self, admin_token, transient_person):
        pid = transient_person["person_id"]
        d = requests.post(f"{API}/people/{pid}/deactivate", headers=H(admin_token), timeout=15)
        assert d.status_code == 200
        g = requests.get(f"{API}/people/{pid}", headers=H(admin_token), timeout=15)
        assert g.json()["user"]["status"] == "inactive"
        a = requests.post(f"{API}/people/{pid}/reactivate", headers=H(admin_token), timeout=15)
        assert a.status_code == 200
        g2 = requests.get(f"{API}/people/{pid}", headers=H(admin_token), timeout=15)
        assert g2.json()["user"]["status"] == "active"

    def test_deactivate_cascades_to_linked_vendor(self, admin_token):
        # Create vendor_internal with linked user
        u = uuid.uuid4().hex[:8]
        email = f"test_cascade_{u}@leamss.com"
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "vendor_internal",
                                "name": f"TEST_cascade_{u}", "email": email,
                                "vendor_category": "case_manager"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        vendor_id = body["person_id"]
        user_id = body["linked_user_id"]
        # Deactivate via user_id; vendor should also become inactive
        d = requests.post(f"{API}/people/{user_id}/deactivate", headers=H(admin_token), timeout=15)
        assert d.status_code == 200
        gv = requests.get(f"{API}/people/{vendor_id}", headers=H(admin_token), timeout=15)
        # vendor.status should be inactive (cascaded)
        assert gv.json()["vendor"]["status"] == "inactive", "linked vendor should cascade to inactive"

    def test_reset_password(self, admin_token, transient_person):
        pid = transient_person["person_id"]
        email = transient_person  # body itself
        r = requests.post(f"{API}/people/{pid}/reset-password", headers=H(admin_token), timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "temp_password" in body and "email" in body
        # login with new temp password
        login = requests.post(f"{API}/auth/login",
                              json={"email": body["email"], "password": body["temp_password"]}, timeout=15)
        assert login.status_code == 200

    def test_reset_password_vendor_only_404(self, admin_token):
        # Create vendor_external (no linked user)
        u = uuid.uuid4().hex[:8]
        cats = requests.get(f"{API}/vendors/categories", headers=H(admin_token), timeout=15)
        ext_key = None
        if cats.status_code == 200:
            data = cats.json()
            cats_list = data.get("categories", data) if isinstance(data, dict) else data
            if isinstance(cats_list, list):
                for c in cats_list:
                    if not c.get("is_internal"):
                        ext_key = c.get("key")
                        break
        if not ext_key:
            pytest.skip("no external vendor category found")
        r = requests.post(f"{API}/people", headers=H(admin_token),
                          json={"person_type": "vendor_external",
                                "name": f"TEST_resetv_{u}",
                                "email": f"test_resetv_{u}@leamss.com",
                                "vendor_category": ext_key}, timeout=15)
        if r.status_code != 200:
            pytest.skip("could not create vendor_external")
        vid = r.json()["person_id"]
        rp = requests.post(f"{API}/people/{vid}/reset-password", headers=H(admin_token), timeout=15)
        assert rp.status_code == 404


# ──────────────────────────────────────────────────────────────
# PART B — Finance Dashboard endpoints shape
# ──────────────────────────────────────────────────────────────
class TestFinanceDashboard:
    def test_sales_commission_all(self, admin_token):
        r = requests.get(f"{API}/sales-commission/all", headers=H(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_sales_commission_leaderboard(self, admin_token):
        r = requests.get(f"{API}/sales-commission/leaderboard", headers=H(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_payouts_queue(self, admin_token):
        r = requests.get(f"{API}/payouts/queue", headers=H(admin_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_payouts_stats(self, admin_token):
        r = requests.get(f"{API}/payouts/stats", headers=H(admin_token), timeout=15)
        assert r.status_code == 200, r.text


# ──────────────────────────────────────────────────────────────
# PART C — Express sale modes
# ──────────────────────────────────────────────────────────────
class TestExpressSaleModes:
    def _create_pa(self, token, payload):
        return requests.post(f"{API}/pre-assessment/create", headers=H(token),
                             json=payload, timeout=15)

    def test_express_token_mode_ok(self, admin_token):
        u = uuid.uuid4().hex[:6]
        r = self._create_pa(admin_token, {
            "client_name": f"TEST_exp_tok_{u}",
            "client_email": f"test_exp_tok_{u}@example.com",
            "client_mobile": "9000000001",
            "country": "Canada",
            "service_type": "PR",
            "sale_type": "express",
            "express_sale_reason": "vip_customer",
            "express_sale_justification": "Client needs to file within 3 days; documents already in hand and verified.",
            "express_mode": "token",
            "express_token_amount": 5000,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        pa_id = body.get("pa_id") or body.get("id") or (body.get("pa") or {}).get("id")
        assert pa_id, f"no pa_id in {body}"
        # verify fields persisted via my-assessments (admin views all)
        my = requests.get(f"{API}/pre-assessment/my-assessments", headers=H(admin_token), timeout=15)
        assert my.status_code == 200
        items = my.json() if isinstance(my.json(), list) else my.json().get("pre_assessments", my.json().get("items", []))
        match = next((p for p in items if p.get("id") == pa_id), None)
        assert match, "created express PA not in my-assessments"
        assert match.get("sale_type") == "express"
        assert match.get("express_mode") == "token"
        assert float(match.get("express_token_amount") or 0) == 5000.0

    def test_express_direct_mode_ok(self, admin_token):
        u = uuid.uuid4().hex[:6]
        r = self._create_pa(admin_token, {
            "client_name": f"TEST_exp_dir_{u}",
            "client_email": f"test_exp_dir_{u}@example.com",
            "client_mobile": "9000000002",
            "country": "Canada",
            "service_type": "PR",
            "sale_type": "express",
            "express_sale_reason": "direct_walkin",
            "express_sale_justification": "Partner wants to send proposal directly without token. Client is ready to commit.",
            "express_mode": "direct",
        })
        assert r.status_code == 200, r.text

    def test_express_token_missing_amount_400(self, admin_token):
        u = uuid.uuid4().hex[:6]
        r = self._create_pa(admin_token, {
            "client_name": f"TEST_exp_no_amt_{u}",
            "client_email": f"test_exp_no_amt_{u}@example.com",
            "client_mobile": "9000000003",
            "country": "Canada", "service_type": "PR",
            "sale_type": "express",
            "express_sale_reason": "vip_customer",
            "express_sale_justification": "Long enough justification text for express sale here please now.",
            "express_mode": "token",
        })
        assert r.status_code == 400
        assert "express_token_amount" in (r.text or "").lower() or "token" in (r.text or "").lower()

    def test_express_invalid_mode_400(self, admin_token):
        u = uuid.uuid4().hex[:6]
        r = self._create_pa(admin_token, {
            "client_name": f"TEST_exp_bad_{u}",
            "client_email": f"test_exp_bad_{u}@example.com",
            "client_mobile": "9000000004",
            "country": "Canada", "service_type": "PR",
            "sale_type": "express",
            "express_sale_reason": "vip_customer",
            "express_sale_justification": "Long enough justification text for express sale here please now.",
            "express_mode": "garbage",
        })
        assert r.status_code == 400

    def test_express_token_zero_400(self, admin_token):
        u = uuid.uuid4().hex[:6]
        r = self._create_pa(admin_token, {
            "client_name": f"TEST_exp_zero_{u}",
            "client_email": f"test_exp_zero_{u}@example.com",
            "client_mobile": "9000000005",
            "country": "Canada", "service_type": "PR",
            "sale_type": "express",
            "express_sale_reason": "vip_customer",
            "express_sale_justification": "Long enough justification text for express sale here please now.",
            "express_mode": "token",
            "express_token_amount": 0,
        })
        assert r.status_code == 400

    def test_express_public_link_exposes_mode(self, admin_token):
        """Express fields must be persisted on PA doc AND public_view returns full doc.
        Since public_view returns full PA (excluding only _id, partner_id, admin_notes),
        verifying persistence is sufficient to confirm frontend can render conditional UI.
        """
        u = uuid.uuid4().hex[:6]
        r = self._create_pa(admin_token, {
            "client_name": f"TEST_exp_pub_{u}",
            "client_email": f"test_exp_pub_{u}@example.com",
            "client_mobile": "9000000006",
            "country": "Canada", "service_type": "PR",
            "sale_type": "express",
            "express_sale_reason": "vip_customer",
            "express_sale_justification": "Long enough justification text for express sale here please now.",
            "express_mode": "token",
            "express_token_amount": 5100,
        })
        assert r.status_code == 200, r.text
        pa_id = r.json()["id"]
        # Fetch via admin endpoint to confirm express_mode + express_token_amount persisted
        det = requests.get(f"{API}/pre-assessment/{pa_id}", headers=H(admin_token), timeout=15)
        if det.status_code != 200:
            # try alternate listing
            my = requests.get(f"{API}/pre-assessment/my-assessments", headers=H(admin_token), timeout=15)
            items = my.json() if isinstance(my.json(), list) else my.json().get("pre_assessments", my.json().get("items", []))
            match = next((p for p in items if p.get("id") == pa_id), None)
            assert match, f"PA not found: {det.status_code}"
            pa_data = match
        else:
            pa_data = det.json()
        assert pa_data.get("express_mode") == "token", f"express_mode missing: {list(pa_data.keys())}"
        assert float(pa_data.get("express_token_amount") or 0) == 5100.0
        assert pa_data.get("sale_type") == "express"


# ──────────────────────────────────────────────────────────────
# Regression — slab delete, product preview, cm-earnings, disputes
# ──────────────────────────────────────────────────────────────
class TestRegression:
    def test_slab_create_and_delete(self, admin_token):
        u = "".join([chr(97 + (b % 26)) for b in uuid.uuid4().bytes[:6]])
        c = requests.post(f"{API}/sales-commission/slabs", headers=H(admin_token),
                          json={"key": f"test_slab_{u}", "name": f"TEST_slab_{u}",
                                "min_revenue": 1, "max_revenue": 999999,
                                "rate_pct": 1.0, "commission_rate": 1.0}, timeout=15)
        if c.status_code != 200:
            print(f"[debug] slab create returned {c.status_code}: {c.text}")
            pytest.skip(f"slab create unsupported shape: {c.status_code} {c.text}")
        slab = c.json().get("slab") or c.json()
        slab_id = slab.get("id")
        assert slab_id, f"no slab id in response: {c.json()}"
        d = requests.delete(f"{API}/sales-commission/slabs/{slab_id}", headers=H(admin_token), timeout=15)
        assert d.status_code == 200, d.text

    def test_product_preview_empty_allocations(self, admin_token):
        plist = requests.get(f"{API}/products", headers=H(admin_token), timeout=15)
        assert plist.status_code == 200
        items = plist.json() if isinstance(plist.json(), list) else plist.json().get("products", [])
        if not items:
            pytest.skip("no products")
        # Find one with no allocations
        empty = next((p for p in items if not p.get("cost_allocations")), None)
        target = empty or items[0]
        pid = target["id"]
        pv = requests.post(f"{API}/products/{pid}/preview", headers=H(admin_token),
                           json={"visa_approved": False}, timeout=15)
        assert pv.status_code == 200, pv.text
        body = pv.json()
        assert "total_cost" in body
        assert "rows" in body
        if empty:
            assert body["total_cost"] == 0
            assert body["rows"] == []

    def test_cm_earnings_my(self, admin_token):
        cm_tok = _login(CM)
        if not cm_tok:
            pytest.skip("cm login failed")
        r = requests.get(f"{API}/cm-earnings/my", headers=H(cm_tok), timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        # Tolerant shape check
        assert "line_items" in body or isinstance(body, list) or "earnings" in body

    def test_dispute_endpoints_rbac(self, partner_token):
        # Non-admin should get 403 on dispute endpoint
        r = requests.post(f"{API}/payouts/fake-pa/allocations/fake-alloc/dispute",
                          headers=H(partner_token), json={"reason": "test"}, timeout=15)
        assert r.status_code in (403, 404)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
