"""Phase 4A — Sales Workflow Inheritance Tests.

Validates:
- POST /pre-assessment/create persists Phase 4A fields for sales_executive
- Scope isolation on GET my-assessments, stats/overview
- Ownership checks (sales_executive cannot read partner's PA)
- AI Proposal access (non-403 for sexec on their own PA)
- Document upload by sexec
- Partner regression: my-assessments + create
- Migration backfill: every PA has created_by_user_id
- Permission inheritance: sexec has 18 partner perms + 10 sales = >= 28
- Admin-only endpoints still blocked for sexec
- Phase 3 regression
"""
import os
import io
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://career-match-320.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@leamss.com", "Admin@123")
PARTNER = ("partner@leamss.com", "Partner@123")
SEXEC = ("sexec-test@leamss.com", "Pass@1234")
SMGR = ("smgr-test@leamss.com", "Pass@1234")


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    body = r.json()
    return body.get("access_token") or body.get("token")


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def partner_token():
    return _login(*PARTNER)


@pytest.fixture(scope="module")
def sexec_token():
    return _login(*SEXEC)


@pytest.fixture(scope="module")
def sexec_user(sexec_token):
    r = requests.get(f"{API}/auth/me", headers=_headers(sexec_token), timeout=15)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def partner_user(partner_token):
    r = requests.get(f"{API}/auth/me", headers=_headers(partner_token), timeout=15)
    assert r.status_code == 200
    return r.json()


# Shared mutable state
state = {}


# ===== Test 1 — sexec creates PA =====
def test_01_sexec_creates_pa(sexec_token, sexec_user):
    payload = {
        "client_name": "Phase4A Test Client",
        "client_email": "phase4a-test@x.com",
        "client_mobile": "+91-9000000001",
        "country": "Canada",
        "service_type": "Express Entry",
        "lead_source": "linkedin",
        "lead_source_detail": "Test LinkedIn outreach",
    }
    r = requests.post(f"{API}/pre-assessment/create", json=payload, headers=_headers(sexec_token), timeout=20)
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    body = r.json()
    assert "id" in body and "pa_number" in body
    state["sexec_pa_id"] = body["id"]
    state["sexec_user_id"] = sexec_user.get("id")

    # Verify persistence via GET (response doesn't include partner_id/created_by_role fields)
    g = requests.get(f"{API}/pre-assessment/{body['id']}", headers=_headers(sexec_token), timeout=15)
    assert g.status_code == 200, g.text
    pa = g.json()
    assert pa["partner_id"] == sexec_user.get("id"), f"partner_id should be sexec id, got {pa.get('partner_id')}"
    assert pa.get("created_by_user_id") == sexec_user.get("id")
    assert pa.get("created_by_role") == "sales_executive", f"created_by_role={pa.get('created_by_role')}"
    assert pa.get("lead_source") == "linkedin"
    assert pa.get("lead_source_detail") == "Test LinkedIn outreach"
    assert pa.get("created_by_user_type") == "internal", f"user_type={pa.get('created_by_user_type')}"


# ===== Test 2 — sexec my-assessments returns only own =====
def test_02_sexec_my_assessments_scope(sexec_token, sexec_user):
    r = requests.get(f"{API}/pre-assessment/my-assessments", headers=_headers(sexec_token), timeout=15)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    sid = sexec_user.get("id")
    for it in items:
        assert it.get("partner_id") == sid, f"PA {it.get('id')} not owned by sexec ({it.get('partner_id')})"
    ids = [it["id"] for it in items]
    assert state["sexec_pa_id"] in ids, "Newly created PA missing from my-assessments"


# ===== Test 3 — stats/overview scoped for sexec =====
def test_03_sexec_stats_overview_scoped(sexec_token, partner_token):
    r = requests.get(f"{API}/pre-assessment/stats/overview", headers=_headers(sexec_token), timeout=15)
    assert r.status_code == 200, r.text
    sexec_stats = r.json()
    assert "total" in sexec_stats
    # Compare to partner stats; they should differ (different scopes)
    rp = requests.get(f"{API}/pre-assessment/my-assessments", headers=_headers(sexec_token), timeout=15)
    list_total = len(rp.json())
    assert sexec_stats["total"] == list_total, f"stats.total ({sexec_stats['total']}) != list count ({list_total})"


# ===== Test 4 — GET /{pa_id} on own PA =====
def test_04_sexec_get_own_pa(sexec_token):
    pa_id = state["sexec_pa_id"]
    r = requests.get(f"{API}/pre-assessment/{pa_id}", headers=_headers(sexec_token), timeout=15)
    assert r.status_code == 200, r.text
    pa = r.json()
    assert pa["id"] == pa_id
    assert pa["client_name"] == "Phase4A Test Client"


# ===== Test 5 — sexec cannot access partner's PA =====
def test_05_sexec_forbidden_on_partner_pa(sexec_token, partner_token):
    # Find a partner PA
    pr = requests.get(f"{API}/pre-assessment/my-assessments", headers=_headers(partner_token), timeout=15)
    assert pr.status_code == 200
    partner_pas = pr.json()
    assert len(partner_pas) > 0, "Partner has no PAs to use for ownership test"
    partner_pa_id = partner_pas[0]["id"]
    state["partner_pa_id"] = partner_pa_id

    r = requests.get(f"{API}/pre-assessment/{partner_pa_id}", headers=_headers(sexec_token), timeout=15)
    # Expect 403 ownership check
    assert r.status_code == 403, f"Expected 403 on cross-owner GET; got {r.status_code} body={r.text[:200]}"


# ===== Test 6 — AI Proposal not 403 for sexec on own PA =====
def test_06_ai_proposal_access_for_sexec(sexec_token):
    pa_id = state["sexec_pa_id"]
    r = requests.post(f"{API}/ai-proposal/generate/{pa_id}", headers=_headers(sexec_token), timeout=60)
    # Acceptable: 200 success, 400/422 business rules, 500 AI-key error — NOT 403
    assert r.status_code != 403, f"AI proposal should not be 403 for sexec on own PA; got {r.status_code} {r.text[:200]}"


# ===== Test 7 — Document upload by sexec =====
def test_07_sexec_doc_upload(sexec_token):
    pa_id = state["sexec_pa_id"]
    files = {"file": ("test.txt", io.BytesIO(b"test phase 4A doc upload"), "text/plain")}
    data = {"document_type": "other", "doc_name": "Phase4A Test Doc"}
    headers = {"Authorization": f"Bearer {sexec_token}"}
    r = requests.post(
        f"{API}/pre-assessment/{pa_id}/upload-document",
        files=files, data=data, headers=headers, timeout=30
    )
    assert r.status_code == 200, f"Doc upload failed: {r.status_code} {r.text[:300]}"


# ===== Test 8 — Partner my-assessments regression =====
def test_08_partner_my_assessments_regression(partner_token, partner_user):
    r = requests.get(f"{API}/pre-assessment/my-assessments", headers=_headers(partner_token), timeout=15)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert len(items) > 0, "Partner should have existing PAs"
    pid = partner_user.get("id")
    for it in items:
        assert it["partner_id"] == pid


# ===== Test 9 — Partner create still works =====
def test_09_partner_create_pa(partner_token, partner_user):
    payload = {
        "client_name": "Phase4A Regression Partner Client",
        "client_email": "phase4a-partner-reg@x.com",
        "client_mobile": "+91-9000000099",
        "country": "Canada",
        "service_type": "Express Entry",
    }
    r = requests.post(f"{API}/pre-assessment/create", json=payload, headers=_headers(partner_token), timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    pa_id = body["id"]
    g = requests.get(f"{API}/pre-assessment/{pa_id}", headers=_headers(partner_token), timeout=15)
    assert g.status_code == 200
    pa = g.json()
    assert pa["partner_id"] == partner_user.get("id")
    assert pa.get("created_by_role") == "partner"


# ===== Test 10 — Migration backfill verified =====
def test_10_migration_backfill_all_have_created_by(admin_token):
    r = requests.get(f"{API}/pre-assessment/my-assessments", headers=_headers(admin_token), timeout=30)
    assert r.status_code == 200
    items = r.json()
    missing = [it["id"] for it in items if not it.get("created_by_user_id")]
    assert len(missing) == 0, f"{len(missing)} PAs missing created_by_user_id: {missing[:5]}"
    assert len(items) >= 15, f"Expected at least 15 PAs (per migration); got {len(items)}"


# ===== Test 11 — sexec permission inheritance =====
def test_11_sexec_permission_inheritance(sexec_user):
    perms = sexec_user.get("permissions", [])
    assert isinstance(perms, list)
    # Expected partner perms now on sexec
    required = [
        "pa.create.own",
        "agreement.view.own",
        "agreement.generate.own",
        "invoice.view.own",
    ]
    missing = [p for p in required if p not in perms]
    assert not missing, f"sexec missing perms: {missing}; got: {perms}"
    assert len(perms) >= 28, f"sexec should have >=28 perms; got {len(perms)}: {perms}"


# ===== Test 12 — sexec blocked from admin endpoint =====
def test_12_sexec_blocked_from_admin(sexec_token):
    # Use a real admin-only endpoint
    r = requests.get(f"{API}/admin-super/approval-center", headers=_headers(sexec_token), timeout=15)
    assert r.status_code in (401, 403), f"Expected 401/403 admin endpoint; got {r.status_code} {r.text[:200]}"


# ===== Test 13 — Phase 3 leave balance regression =====
def test_13_sexec_leaves_balance(sexec_token):
    r = requests.get(f"{API}/leaves/my-balance", headers=_headers(sexec_token), timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    # response may be list or dict — accept either
    if isinstance(body, dict) and "balances" in body:
        balances = body["balances"]
    elif isinstance(body, list):
        balances = body
    else:
        balances = body
    assert balances, f"Empty balances: {body}"
    if isinstance(balances, list):
        assert len(balances) == 7, f"Expected 7 leave types; got {len(balances)}"


# ===== Test 14 — Phase 3 attendance current-status =====
def test_14_sexec_attendance_status(sexec_token):
    r = requests.get(f"{API}/attendance/current-status", headers=_headers(sexec_token), timeout=15)
    assert r.status_code == 200, r.text


# ===== Test 15 — Phase 3B leave-types =====
def test_15_admin_leave_types(admin_token):
    r = requests.get(f"{API}/hr/leave-types", headers=_headers(admin_token), timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    types = body.get("leave_types") if isinstance(body, dict) else body
    assert types, f"No leave types returned: {body}"
    active_types = [t for t in types if not t.get("soft_deleted")]
    assert len(active_types) >= 7, f"Expected >=7 active leave types; got {len(active_types)}"
