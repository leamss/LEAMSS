"""Phase 4B Part 2 — Express Sales tests.

Validates:
  - Settings GET/PATCH (admin only)
  - my-usage endpoint
  - Standard sale creation (regression — sale_type defaults to standard)
  - Express creation: short justification (400), bad reason (400), valid (200)
  - Limit enforcement (429 on 6th)
  - Auto-approve for admin
  - Admin queue (pending), approve, reject
  - Rejection requires remarks
  - Stage transitions: pending → approved / rejected
  - Permission isolation (partner cannot approve, sexec cannot view pending)
"""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

API = f"{os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "leamss_portal")

ADMIN = ("admin@leamss.com", "Admin@123")
PARTNER = ("partner@leamss.com", "Partner@123")
SEXEC = ("sexec-test@leamss.com", "Pass@1234")


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def partner_token():
    return _login(*PARTNER)


@pytest.fixture(scope="module")
def sexec_token():
    return _login(*SEXEC)


@pytest.fixture(autouse=True)
def _cleanup():
    """Hard-delete express test PAs created by sexec before each test."""
    c = MongoClient(MONGO_URL)[DB_NAME]
    # Look up sexec user_id
    sexec = c.users.find_one({"email": "sexec-test@leamss.com"}, {"_id": 0, "id": 1})
    if sexec:
        c.pre_assessments.delete_many({"created_by_user_id": sexec["id"], "sale_type": "express"})
    yield
    if sexec:
        c.pre_assessments.delete_many({"created_by_user_id": sexec["id"], "sale_type": "express"})


def _valid_express_body(client_name="Test Express Client"):
    return {
        "client_name": client_name,
        "client_email": f"{uuid.uuid4().hex[:8]}@test.com",
        "country": "Canada",
        "service_type": "Express Entry",
        "sale_type": "express",
        "express_sale_reason": "vip_customer",
        "express_sale_justification": "VIP referral from existing client. Pre-screened by sales head as a strong candidate.",
    }


# ════════════════════════════════════════════════════════════
# 1. Settings - GET/PATCH
# ════════════════════════════════════════════════════════════
def test_get_express_settings(admin_token):
    r = requests.get(f"{API}/express/settings", headers=_hdr(admin_token), timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert "express_sale_enabled" in d
    assert "express_monthly_limits" in d
    assert d["express_monthly_limits"]["sales_executive"] == 5


def test_patch_settings_admin_only(admin_token, sexec_token):
    # Non-admin cannot patch
    r = requests.patch(f"{API}/express/settings", headers=_hdr(sexec_token), json={"express_max_value": 1000}, timeout=10)
    assert r.status_code == 403

    # Admin can patch (then restore)
    r2 = requests.patch(f"{API}/express/settings", headers=_hdr(admin_token), json={"express_max_value": 4000000}, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["settings"]["express_max_value"] == 4000000
    # Restore
    requests.patch(f"{API}/express/settings", headers=_hdr(admin_token), json={"express_max_value": 5000000}, timeout=10)


# ════════════════════════════════════════════════════════════
# 2. my-usage
# ════════════════════════════════════════════════════════════
def test_my_usage_sexec(sexec_token):
    r = requests.get(f"{API}/express/my-usage", headers=_hdr(sexec_token), timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["limit_per_month"] == 5
    assert d["used_this_month"] == 0
    assert d["remaining"] == 5
    assert d["allowed"] is True


# ════════════════════════════════════════════════════════════
# 3. Standard sale still works (regression)
# ════════════════════════════════════════════════════════════
def test_standard_sale_works(sexec_token):
    body = {
        "client_name": "Standard Test",
        "client_email": f"{uuid.uuid4().hex[:8]}@x.com",
        "country": "USA",
        "service_type": "H1B",
        # No sale_type — should default to 'standard'
    }
    r = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token), json=body, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["sale_type"] == "standard"
    assert d["stage"] == "new"


# ════════════════════════════════════════════════════════════
# 4. Express validation
# ════════════════════════════════════════════════════════════
def test_express_short_justification(sexec_token):
    body = _valid_express_body()
    body["express_sale_justification"] = "too short"
    r = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token), json=body, timeout=10)
    assert r.status_code == 400
    assert "Justification must be at least" in r.json()["detail"]


def test_express_invalid_reason(sexec_token):
    body = _valid_express_body()
    body["express_sale_reason"] = "bogus_reason"
    r = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token), json=body, timeout=10)
    assert r.status_code == 400


# ════════════════════════════════════════════════════════════
# 5. Express creation by sexec → pending
# ════════════════════════════════════════════════════════════
def test_express_creation_sexec_pending(sexec_token):
    r = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token), json=_valid_express_body(), timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["sale_type"] == "express"
    assert d["stage"] == "express_pending_approval"
    assert d["express_sale_approval_status"] == "pending"


# ════════════════════════════════════════════════════════════
# 6. Admin auto-approve
# ════════════════════════════════════════════════════════════
def test_express_admin_auto_approves(admin_token):
    body = _valid_express_body("Admin Express Client")
    r = requests.post(f"{API}/pre-assessment/create", headers=_hdr(admin_token), json=body, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["express_sale_approval_status"] == "approved"
    assert d["stage"] == "approved"  # ready for proposal


# ════════════════════════════════════════════════════════════
# 7. Admin queue + approve flow
# ════════════════════════════════════════════════════════════
def test_pending_queue_and_approve(admin_token, sexec_token):
    # Create one express
    create_resp = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token), json=_valid_express_body(), timeout=15)
    pa_id = create_resp.json()["id"]

    # Admin can list pending
    r = requests.get(f"{API}/express/pending", headers=_hdr(admin_token), timeout=10)
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["id"] == pa_id for i in items)

    # Approve
    r2 = requests.post(f"{API}/express/approve/{pa_id}", headers=_hdr(admin_token), json={"remarks": "Looks good"}, timeout=10)
    assert r2.status_code == 200, r2.text
    assert r2.json()["express_sale_approval_status"] == "approved"

    # Cannot approve twice
    r3 = requests.post(f"{API}/express/approve/{pa_id}", headers=_hdr(admin_token), json={"remarks": "again"}, timeout=10)
    assert r3.status_code == 400


# ════════════════════════════════════════════════════════════
# 8. Rejection requires remarks
# ════════════════════════════════════════════════════════════
def test_reject_requires_remarks(admin_token, sexec_token):
    create_resp = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token), json=_valid_express_body(), timeout=15)
    pa_id = create_resp.json()["id"]

    # Empty remarks → 422 (pydantic validation min_length=5)
    r = requests.post(f"{API}/express/reject/{pa_id}", headers=_hdr(admin_token), json={"remarks": "no"}, timeout=10)
    assert r.status_code in (400, 422)

    # Valid rejection
    r2 = requests.post(f"{API}/express/reject/{pa_id}", headers=_hdr(admin_token), json={"remarks": "Not aligned with policy"}, timeout=10)
    assert r2.status_code == 200, r2.text
    assert r2.json()["express_sale_approval_status"] == "rejected"
    assert r2.json()["stage"] == "express_rejected"


# ════════════════════════════════════════════════════════════
# 9. Permission isolation
# ════════════════════════════════════════════════════════════
def test_partner_cannot_approve(partner_token, sexec_token, admin_token):
    create_resp = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token), json=_valid_express_body(), timeout=15)
    pa_id = create_resp.json()["id"]
    r = requests.post(f"{API}/express/approve/{pa_id}", headers=_hdr(partner_token), json={"remarks": "trying"}, timeout=10)
    assert r.status_code == 403


def test_sexec_cannot_view_pending(sexec_token):
    r = requests.get(f"{API}/express/pending", headers=_hdr(sexec_token), timeout=10)
    assert r.status_code == 403


# ════════════════════════════════════════════════════════════
# 10. Monthly limit enforcement (sales_executive=5)
# ════════════════════════════════════════════════════════════
def test_monthly_limit_enforcement(sexec_token):
    # Create 5
    for i in range(5):
        r = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token),
                         json=_valid_express_body(f"Limit Test {i}"), timeout=15)
        assert r.status_code == 200, f"Iter {i}: {r.text}"

    # 6th → 429
    r6 = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token),
                      json=_valid_express_body("Limit Test 6"), timeout=15)
    assert r6.status_code == 429, r6.text
    assert "limit" in r6.json()["detail"].lower()


# ════════════════════════════════════════════════════════════
# 11. Verify pa_fees_skipped flag on express
# ════════════════════════════════════════════════════════════
def test_pa_fees_skipped_flag(sexec_token):
    create_resp = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token), json=_valid_express_body(), timeout=15)
    pa_id = create_resp.json()["id"]

    # Check via Mongo
    c = MongoClient(MONGO_URL)[DB_NAME]
    pa = c.pre_assessments.find_one({"id": pa_id}, {"_id": 0})
    assert pa["pa_fees_skipped"] is True
    assert pa["fee_payment_status"] == "skipped"
    assert pa["pa_fees_amount"] == 5100  # PRE_ASSESSMENT_FEE


# ════════════════════════════════════════════════════════════
# 12. Approved express PA contributes to target (revenue counted)
# ════════════════════════════════════════════════════════════
def test_express_approved_contributes_to_target_on_case_created(admin_token, sexec_token):
    """End-to-end: express → approve → set proposal_fee → approve final → revenue in target."""
    c = MongoClient(MONGO_URL)[DB_NAME]
    sexec_user = c.users.find_one({"email": "sexec-test@leamss.com"}, {"_id": 0, "id": 1})
    sexec_id = sexec_user["id"]

    # Clean up any current-month target + test data
    now = datetime.now(timezone.utc)
    c.sales_targets.delete_many({"user_id": sexec_id, "period_type": "monthly", "period_year": now.year, "period_month": now.month})

    # Admin creates target for sexec
    body = {"user_id": sexec_id, "period_type": "monthly", "period_year": now.year, "period_month": now.month,
            "revenue": 500000, "pa_count": 10}
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=15)
    assert r.status_code == 200, r.text

    # Sexec creates express PA
    create = requests.post(f"{API}/pre-assessment/create", headers=_hdr(sexec_token), json=_valid_express_body(), timeout=15)
    pa_id = create.json()["id"]

    # Admin approves express → stage=approved
    requests.post(f"{API}/express/approve/{pa_id}", headers=_hdr(admin_token), json={"remarks": "approved"}, timeout=10)

    # Manually push to case_created with a revenue value (simulate full flow)
    c.pre_assessments.update_one({"id": pa_id}, {"$set": {
        "stage": "case_created",
        "proposal_fee": 75000,
        "final_amount": 75000,
        "final_approved_at": datetime.now(timezone.utc),
    }})

    # Trigger recalc explicitly
    r2 = requests.post(f"{API}/sales/targets/recalculate", headers=_hdr(admin_token), timeout=15)
    assert r2.status_code == 200

    # Check target now reflects revenue
    my = requests.get(f"{API}/sales/targets/my", headers=_hdr(sexec_token), timeout=10)
    monthly = my.json()["monthly"]
    assert monthly is not None
    assert monthly["achievement"]["revenue"] == 75000, f"Expected ₹75K, got {monthly['achievement']['revenue']}"
    assert monthly["achievement"]["pa_count"] == 1
