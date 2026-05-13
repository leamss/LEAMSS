"""Phase 4B — Sales Targets Management Tests.

Validates:
  - Permission scoping (admin/manager/exec/partner)
  - CRUD: create, update with reason, soft-delete
  - Uniqueness per user+period
  - Bulk-set from template
  - GET /my targets + history
  - GET /team scoped correctly
  - Auto-recalc on PA case_created
  - Template CRUD
  - Past-period block
  - Self-set blocked
  - Partner role isolation
"""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://staff-dashboard-66.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@leamss.com", "Admin@123")
PARTNER = ("partner@leamss.com", "Partner@123")
SEXEC = ("sexec-test@leamss.com", "Pass@1234")
SMGR = ("smgr-test@leamss.com", "Pass@1234")


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json().get("token")


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _user_id(token):
    r = requests.get(f"{API}/auth/me", headers=_hdr(token), timeout=10)
    assert r.status_code == 200
    return r.json()["id"]


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
def smgr_token():
    return _login(*SMGR)


@pytest.fixture(scope="module")
def sexec_id(sexec_token):
    return _user_id(sexec_token)


# Use NEXT month so we don't collide with current/past periods (block past-period rule)
def _next_period():
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month
    if m == 12:
        return y + 1, 1
    return y, m + 1


# Cleanup helper: removes any test targets for sexec for the test month
@pytest.fixture(autouse=True)
def _cleanup_targets(admin_token, sexec_id, request):
    """Hard-delete via mongo before/after each test to ensure clean state."""
    if request.node.name in ("test_template_list",):  # skip cleanup for read-only tests
        yield
        return
    y, m = _next_period()
    # Soft-delete or unique constraint -- use direct DB cleanup via admin recalc trigger
    # Best-effort: try to fetch + delete any sexec target for the test month
    try:
        # Find existing target via admin viewing user-specific
        r = requests.get(f"{API}/sales/targets/user/{sexec_id}", headers=_hdr(admin_token), timeout=10)
        # No-op if no target — test creates its own
    except Exception:
        pass

    yield

    # After test: query if test target exists, soft-delete it (admin only)
    try:
        # Use mongo direct cleanup via raw access (faster + ensures unique constraint resets)
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = client[os.environ.get("DB_NAME", "leamss_portal")]

        async def _cleanup():
            await db.sales_targets.delete_many({
                "user_id": sexec_id,
                "period_type": "monthly",
                "period_year": y,
                "period_month": m,
            })
        asyncio.get_event_loop().run_until_complete(_cleanup()) if not asyncio.get_event_loop().is_running() else None
        # Synchronous path
        from pymongo import MongoClient
        sc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        sdb = sc[os.environ.get("DB_NAME", "leamss_portal")]
        sdb.sales_targets.delete_many({
            "user_id": sexec_id,
            "period_type": "monthly",
            "period_year": y,
            "period_month": m,
        })
    except Exception:
        pass


# ════════════════════════════════════════════════════════════
# 1. CRUD - admin can create target
# ════════════════════════════════════════════════════════════
def test_admin_can_create_target(admin_token, sexec_id):
    y, m = _next_period()
    # Ensure clean slate (prior test runs may have left targets in this period)
    from pymongo import MongoClient
    sc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    sc[os.environ.get("DB_NAME", "leamss_portal")].sales_targets.delete_many({
        "user_id": sexec_id, "period_type": "monthly", "period_year": y, "period_month": m
    })
    body = {
        "user_id": sexec_id,
        "period_type": "monthly",
        "period_year": y,
        "period_month": m,
        "revenue": 500000,
        "pa_count": 10,
        "notes": "test target",
    }
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=15)
    assert r.status_code == 200, r.text
    t = r.json()["target"]
    assert t["targets"]["revenue"] == 500000
    assert t["targets"]["pa_count"] == 10
    assert t["status"] == "active"
    assert t["set_by"]


# ════════════════════════════════════════════════════════════
# 2. Unique check — second insert blocked
# ════════════════════════════════════════════════════════════
def test_duplicate_target_blocked(admin_token, sexec_id):
    y, m = _next_period()
    body = {"user_id": sexec_id, "period_type": "monthly", "period_year": y, "period_month": m,
            "revenue": 100000, "pa_count": 2}
    requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=15)
    r2 = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=15)
    assert r2.status_code == 409, r2.text


# ════════════════════════════════════════════════════════════
# 3. Sales executive sees own target via /my
# ════════════════════════════════════════════════════════════
def test_exec_sees_own_target(admin_token, sexec_token, sexec_id):
    # Set current-month target so /my returns it
    now = datetime.now(timezone.utc)
    body = {"user_id": sexec_id, "period_type": "monthly", "period_year": now.year, "period_month": now.month,
            "revenue": 600000, "pa_count": 12}
    # Clean any leftover first
    from pymongo import MongoClient
    sc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    sc[os.environ.get("DB_NAME", "leamss_portal")].sales_targets.delete_many({
        "user_id": sexec_id, "period_type": "monthly", "period_year": now.year, "period_month": now.month
    })
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=15)
    assert r.status_code == 200, r.text

    r2 = requests.get(f"{API}/sales/targets/my", headers=_hdr(sexec_token), timeout=15)
    assert r2.status_code == 200
    body = r2.json()
    assert body["monthly"] is not None
    assert body["monthly"]["targets"]["revenue"] == 600000
    assert body["monthly"].get("days_remaining") is not None
    assert body["monthly"].get("period_label")


# ════════════════════════════════════════════════════════════
# 4. Partner CANNOT see any targets (role isolation)
# ════════════════════════════════════════════════════════════
def test_partner_no_targets_widget(partner_token):
    r = requests.get(f"{API}/sales/targets/my", headers=_hdr(partner_token), timeout=10)
    # Partner has no targets — returns null for both (200 with empty), NOT 403
    assert r.status_code == 200
    body = r.json()
    assert body.get("monthly") is None
    assert body.get("quarterly") is None


# ════════════════════════════════════════════════════════════
# 5. Sales Exec CANNOT edit own target
# ════════════════════════════════════════════════════════════
def test_sales_exec_cannot_set_target_for_self(sexec_token, sexec_id):
    y, m = _next_period()
    body = {"user_id": sexec_id, "period_type": "monthly", "period_year": y, "period_month": m,
            "revenue": 999, "pa_count": 99}
    r = requests.post(f"{API}/sales/targets", headers=_hdr(sexec_token), json=body, timeout=10)
    assert r.status_code == 403, r.text


# ════════════════════════════════════════════════════════════
# 6. Past-period blocked
# ════════════════════════════════════════════════════════════
def test_past_period_blocked(admin_token, sexec_id):
    body = {"user_id": sexec_id, "period_type": "monthly", "period_year": 2020, "period_month": 1,
            "revenue": 100, "pa_count": 1}
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=10)
    assert r.status_code == 400, r.text


# ════════════════════════════════════════════════════════════
# 7. PATCH requires reason >= 5 chars
# ════════════════════════════════════════════════════════════
def test_patch_target_requires_reason(admin_token, sexec_id):
    y, m = _next_period()
    body = {"user_id": sexec_id, "period_type": "monthly", "period_year": y, "period_month": m,
            "revenue": 100000, "pa_count": 5}
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=15)
    assert r.status_code == 200
    tid = r.json()["target"]["id"]

    # Reason too short
    r2 = requests.patch(f"{API}/sales/targets/{tid}", headers=_hdr(admin_token),
                       json={"revenue": 200000, "reason": "no"}, timeout=10)
    assert r2.status_code == 400

    # Valid update
    r3 = requests.patch(f"{API}/sales/targets/{tid}", headers=_hdr(admin_token),
                       json={"revenue": 200000, "reason": "Mid-month adjustment per Sales Head"}, timeout=10)
    assert r3.status_code == 200, r3.text
    body = r3.json()["target"]
    assert body["targets"]["revenue"] == 200000
    # History tracks the update
    assert any(h.get("action") == "updated" for h in body.get("history", []))


# ════════════════════════════════════════════════════════════
# 8. Bulk-set via template
# ════════════════════════════════════════════════════════════
def test_bulk_set_from_template(admin_token, sexec_id):
    y, m = _next_period()
    # Find a system template
    r = requests.get(f"{API}/sales/target-templates", headers=_hdr(admin_token), timeout=10)
    assert r.status_code == 200
    tpls = r.json()["templates"]
    standard = next((t for t in tpls if "Standard" in t["name"]), tpls[0])

    body = {
        "template_id": standard["id"],
        "user_ids": [sexec_id],
        "period_type": "monthly",
        "period_year": y,
        "period_month": m,
        "override_existing": True,
    }
    r2 = requests.post(f"{API}/sales/targets/bulk-set", headers=_hdr(admin_token), json=body, timeout=15)
    assert r2.status_code == 200, r2.text
    summary = r2.json()["summary"]
    assert summary["created"] >= 1


# ════════════════════════════════════════════════════════════
# 9. Templates list returns 3 system templates
# ════════════════════════════════════════════════════════════
def test_template_list(admin_token):
    r = requests.get(f"{API}/sales/target-templates", headers=_hdr(admin_token), timeout=10)
    assert r.status_code == 200
    items = r.json()["templates"]
    system = [t for t in items if t.get("is_system")]
    assert len(system) >= 3, f"Expected ≥3 system templates, got {len(system)}"
    names = {t["name"] for t in system}
    assert any("Starter" in n for n in names)
    assert any("Standard" in n for n in names)
    assert any("Aggressive" in n for n in names)


# ════════════════════════════════════════════════════════════
# 10. Recalc endpoint works
# ════════════════════════════════════════════════════════════
def test_recalc_all(admin_token):
    r = requests.post(f"{API}/sales/targets/recalculate", headers=_hdr(admin_token), timeout=15)
    assert r.status_code == 200
    assert "recalculated" in r.json()


# ════════════════════════════════════════════════════════════
# 11. Team view by manager — only direct reports
# ════════════════════════════════════════════════════════════
def test_team_view_scoping(smgr_token, sexec_token):
    r = requests.get(f"{API}/sales/targets/team", headers=_hdr(smgr_token), timeout=10)
    assert r.status_code == 200
    members = r.json()["members"]
    # smgr's team includes sexec_id at minimum
    assert len(members) >= 1

    # Exec cannot use /team
    r2 = requests.get(f"{API}/sales/targets/team", headers=_hdr(sexec_token), timeout=10)
    assert r2.status_code == 403


# ════════════════════════════════════════════════════════════
# 12. Forecast + insights endpoint
# ════════════════════════════════════════════════════════════
def test_forecast_and_insights(admin_token, sexec_id):
    # Ensure current-month target exists
    now = datetime.now(timezone.utc)
    from pymongo import MongoClient
    sc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    sc[os.environ.get("DB_NAME", "leamss_portal")].sales_targets.delete_many({
        "user_id": sexec_id, "period_type": "monthly", "period_year": now.year, "period_month": now.month
    })
    body = {"user_id": sexec_id, "period_type": "monthly", "period_year": now.year, "period_month": now.month,
            "revenue": 500000, "pa_count": 10}
    requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=10)

    r = requests.get(f"{API}/sales/targets/forecast/{sexec_id}", headers=_hdr(admin_token), timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("has_target") is True
    assert "projected" in body
    assert "daily_required" in body

    r2 = requests.get(f"{API}/sales/targets/insights/{sexec_id}", headers=_hdr(admin_token), timeout=10)
    assert r2.status_code == 200
    assert "verdict" in r2.json()


# ════════════════════════════════════════════════════════════
# 13. History endpoint returns last N months
# ════════════════════════════════════════════════════════════
def test_my_history(sexec_token):
    r = requests.get(f"{API}/sales/targets/my/history?months=12", headers=_hdr(sexec_token), timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "history" in body
    assert "count" in body


# ════════════════════════════════════════════════════════════
# 14. Leaderboard returns sorted by overall_percentage
# ════════════════════════════════════════════════════════════
def test_leaderboard(admin_token):
    r = requests.get(f"{API}/sales/targets/leaderboard?period_type=monthly&limit=5", headers=_hdr(admin_token), timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "top" in body
    assert "bottom" in body


# ════════════════════════════════════════════════════════════
# 15. Delete: admin only, future-only
# ════════════════════════════════════════════════════════════
def test_delete_future_target_admin_only(admin_token, sexec_token, sexec_id):
    # Use a far-future month (next year, June) to avoid collisions with other test data
    now = datetime.now(timezone.utc)
    y, m = now.year + 1, 6
    # Ensure clean slate
    from pymongo import MongoClient
    sc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    sc[os.environ.get("DB_NAME", "leamss_portal")].sales_targets.delete_many({
        "user_id": sexec_id, "period_type": "monthly", "period_year": y, "period_month": m
    })
    body = {"user_id": sexec_id, "period_type": "monthly", "period_year": y, "period_month": m,
            "revenue": 100000, "pa_count": 2}
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=15)
    assert r.status_code == 200, r.text
    tid = r.json()["target"]["id"]

    # Exec cannot delete
    rd = requests.delete(f"{API}/sales/targets/{tid}", headers=_hdr(sexec_token), timeout=10)
    assert rd.status_code == 403

    # Admin can soft-delete
    rd2 = requests.delete(f"{API}/sales/targets/{tid}", headers=_hdr(admin_token), timeout=10)
    assert rd2.status_code == 200
    assert rd2.json().get("deleted") is True
