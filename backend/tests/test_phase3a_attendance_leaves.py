"""Phase 3A - Attendance & Leave Management tests"""
import os
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://career-match-320.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@leamss.com", "Admin@123")
MGR = ("smgr-test@leamss.com", "Pass@1234")
EXEC = ("sexec-test@leamss.com", "Pass@1234")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"] if "access_token" in r.json() else r.json().get("token")


@pytest.fixture(scope="session")
def admin_h():
    return {"Authorization": f"Bearer {_login(*ADMIN)}"}


@pytest.fixture(scope="session")
def mgr_h():
    return {"Authorization": f"Bearer {_login(*MGR)}"}


@pytest.fixture(scope="session")
def exec_h():
    return {"Authorization": f"Bearer {_login(*EXEC)}"}


def _cleanup_sandwich_leaves_via_db():
    """Idempotency helper: clear any sandwich leave_requests from prior runs for sexec-test.

    Safe to call before sandwich tests. Uses pymongo directly because there is no DELETE
    leave endpoint (leaves are cancellable but cannot be deleted via API after approval).
    """
    try:
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "leamss_portal")
        client = MongoClient(mongo_url)
        db = client[db_name]
        # Find sexec user
        u = db["users"].find_one({"email": "sexec-test@leamss.com"}, {"_id": 0, "id": 1})
        if not u:
            return
        # Delete any leave_request in the sandwich date range
        r = db["leave_requests"].delete_many({
            "user_id": u["id"],
            "from_date": "2026-07-17",
            "to_date": "2026-07-20",
        })
        if r.deleted_count:
            print(f"[Sandwich cleanup] Removed {r.deleted_count} stale leave_request(s) for sexec-test")
        client.close()
    except Exception as e:
        print(f"[Sandwich cleanup] Skipped: {e}")


@pytest.fixture(autouse=True, scope="module")
def _ensure_sandwich_idempotent():
    """Run once before any test in this module to clear sandwich leftovers."""
    _cleanup_sandwich_leaves_via_db()
    yield
    _cleanup_sandwich_leaves_via_db()


# ─── Auth check ─────────────────────────────────────────────
def test_login_all_three():
    for email, pw in [ADMIN, MGR, EXEC]:
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
        assert r.status_code == 200, f"Login failed for {email}"


# ─── HR Admin: Settings ─────────────────────────────────────
def test_settings_admin(admin_h):
    r = requests.get(f"{API}/hr/settings", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    s = r.json()
    assert s.get("office_start_time") == "10:00"
    assert s.get("office_end_time") == "19:00"
    assert s.get("min_work_hours") == 9
    assert s.get("late_threshold_minutes") == 10
    assert s.get("late_marks_for_leave_deduction") == 3
    assert s.get("monthly_cl_limit") == 1
    assert s.get("max_consecutive_leave_days") == 7


def test_settings_forbidden_for_exec(exec_h):
    r = requests.get(f"{API}/hr/settings", headers=exec_h, timeout=20)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


# ─── HR Admin: Holidays ─────────────────────────────────────
def test_holidays_2026(admin_h):
    r = requests.get(f"{API}/hr/holidays?year=2026", headers=admin_h, timeout=20)
    assert r.status_code == 200
    holidays = r.json()
    assert len(holidays) >= 9, f"Expected at least 9 holidays for 2026, got {len(holidays)}"


def test_create_custom_holiday(admin_h):
    payload = {"date": "2026-12-30", "name": "TEST_Custom Holiday", "type": "company"}
    r = requests.post(f"{API}/hr/holidays", json=payload, headers=admin_h, timeout=20)
    if r.status_code == 400 and "already exists" in r.text:
        # cleanup-and-retry
        gh = requests.get(f"{API}/hr/holidays?year=2026", headers=admin_h, timeout=20).json()
        hid = next((h["id"] for h in gh if h["date"] == "2026-12-30"), None)
        if hid:
            requests.delete(f"{API}/hr/holidays/{hid}", headers=admin_h, timeout=20)
        r = requests.post(f"{API}/hr/holidays", json=payload, headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    hid = r.json()["id"]
    # cleanup
    requests.delete(f"{API}/hr/holidays/{hid}", headers=admin_h, timeout=20)


# ─── Leave types ────────────────────────────────────────────
def test_leave_types_seven(exec_h):
    r = requests.get(f"{API}/leaves/types", headers=exec_h, timeout=20)
    assert r.status_code == 200
    types = r.json()
    keys = {t["key"] for t in types}
    expected = {"casual_leave", "sick_leave", "earned_leave", "comp_off", "lwp", "maternity_leave", "paternity_leave"}
    assert expected.issubset(keys), f"Missing leave types. Got: {keys}"


def test_my_balance_seven(exec_h):
    r = requests.get(f"{API}/leaves/my-balance", headers=exec_h, timeout=20)
    assert r.status_code == 200
    data = r.json()
    balances = data["balances"]
    assert len(balances) == 7, f"Expected 7 balances, got {len(balances)}"
    cl = next((b for b in balances if b["leave_type_key"] == "casual_leave"), None)
    assert cl is not None
    assert cl["annual_quota"] == 12
    assert "available" in cl and "used" in cl and "used_this_month" in cl


# ─── Validate ───────────────────────────────────────────────
def test_validate_sandwich_cl(exec_h):
    """CL Fri-Mon → sandwich detected + exceeds 1-day cap"""
    r = requests.post(f"{API}/leaves/validate", json={
        "leave_type_key": "casual_leave", "from_date": "2026-05-15", "to_date": "2026-05-18"
    }, headers=exec_h, timeout=20)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["days_breakdown"]["is_sandwich"] is True
    assert j["total_days"] == 4
    assert j["days_breakdown"]["weekend_included"] == 2
    assert any("consecutive" in e.lower() or "casual" in e.lower() for e in j.get("errors", [])), \
        f"Expected consecutive-day error, got: {j.get('errors')}"


def test_validate_max_consecutive(exec_h):
    r = requests.post(f"{API}/leaves/validate", json={
        "leave_type_key": "earned_leave", "from_date": "2026-06-01", "to_date": "2026-06-08"
    }, headers=exec_h, timeout=20)
    assert r.status_code == 200, r.text
    j = r.json()
    assert any("7" in e or "consecutive" in e.lower() for e in j.get("errors", [])), \
        f"Expected max consecutive error, got: {j.get('errors')}"


# ─── Apply / Sandwich / Cap ─────────────────────────────────
def test_apply_cl_june_and_monthly_cap(exec_h):
    """Use June 2026 (since May already has approved+pending CL)."""
    # First CL in June
    payload = {
        "leave_type_key": "casual_leave",
        "from_date": "2026-06-15", "to_date": "2026-06-15",
        "reason": "Personal work TEST",
    }
    r = requests.post(f"{API}/leaves/apply", json=payload, headers=exec_h, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"Initial June CL apply failed (maybe already exists): {r.status_code} {r.text}")
    first = r.json()
    assert first["status"] == "pending_l1"
    first_id = first["request_id"]

    # 2nd CL same month should be blocked
    payload2 = {
        "leave_type_key": "casual_leave",
        "from_date": "2026-06-16", "to_date": "2026-06-16",
        "reason": "Second CL same month TEST",
    }
    r2 = requests.post(f"{API}/leaves/apply", json=payload2, headers=exec_h, timeout=20)
    assert r2.status_code == 400, f"Expected 400 monthly cap block, got {r2.status_code}: {r2.text}"
    body = r2.json()
    assert "monthly" in str(body).lower() or "cap" in str(body).lower() or "1" in str(body).lower(), \
        f"Expected monthly cap error, got: {body}"

    # Cleanup: cancel the first
    requests.post(f"{API}/leaves/{first_id}/cancel", headers=exec_h, timeout=20)


def test_apply_sandwich_requires_ack(exec_h):
    payload = {
        "leave_type_key": "earned_leave",
        "from_date": "2026-07-17",  # Fri
        "to_date": "2026-07-20",    # Mon
        "reason": "Sandwich EL test TEST",
        "accept_sandwich": False,
    }
    r = requests.post(f"{API}/leaves/apply", json=payload, headers=exec_h, timeout=20)
    assert r.status_code == 400, r.text
    body = r.json()
    detail = body.get("detail", body)
    assert detail.get("requires_acknowledgement") is True, f"Expected requires_acknowledgement, got: {body}"


def test_apply_sandwich_accepted(exec_h, mgr_h, admin_h):
    payload = {
        "leave_type_key": "earned_leave",
        "from_date": "2026-07-17", "to_date": "2026-07-20",
        "reason": "Sandwich EL accepted TEST",
        "accept_sandwich": True,
    }
    r = requests.post(f"{API}/leaves/apply", json=payload, headers=exec_h, timeout=20)
    assert r.status_code == 200, r.text
    req_id = r.json()["request_id"]
    assert r.json()["status"] == "pending_l1"
    assert r.json()["total_days"] == 4

    # Manager inbox
    inbox = requests.get(f"{API}/leaves/inbox", headers=mgr_h, timeout=20)
    assert inbox.status_code == 200
    assert any(i["id"] == req_id for i in inbox.json()), "Request not in mgr inbox"

    # L1 approve
    d1 = requests.post(f"{API}/leaves/{req_id}/decide",
                       json={"decision": "approved", "note": "OK TEST"},
                       headers=mgr_h, timeout=20)
    assert d1.status_code == 200, d1.text
    assert d1.json().get("new_status") == "pending_final"

    # Final approve (admin)
    d2 = requests.post(f"{API}/leaves/{req_id}/decide",
                       json={"decision": "approved", "note": "Final OK TEST"},
                       headers=admin_h, timeout=20)
    assert d2.status_code == 200, d2.text
    assert d2.json().get("new_status") == "approved"

    # Balance history
    hist = requests.get(f"{API}/leaves/balance-history/my", headers=exec_h, timeout=20)
    assert hist.status_code == 200
    changes = {h.get("change_type") for h in hist.json()}
    assert "applied" in changes


def test_cancel_pending(exec_h):
    payload = {
        "leave_type_key": "sick_leave",
        "from_date": "2026-08-10", "to_date": "2026-08-10",
        "reason": "To be cancelled TEST",
    }
    r = requests.post(f"{API}/leaves/apply", json=payload, headers=exec_h, timeout=20)
    assert r.status_code == 200, r.text
    req_id = r.json()["request_id"]

    c = requests.post(f"{API}/leaves/{req_id}/cancel", headers=exec_h, timeout=20)
    assert c.status_code == 200, c.text

    hist = requests.get(f"{API}/leaves/my-history", headers=exec_h, timeout=20)
    assert hist.status_code == 200
    statuses = {h["id"]: h["status"] for h in hist.json()}
    assert statuses.get(req_id) == "cancelled"


# ─── Attendance: punch & status ─────────────────────────────
def test_current_status(exec_h):
    r = requests.get(f"{API}/attendance/current-status", headers=exec_h, timeout=20)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] in ("not_punched", "in_progress", "completed")
    assert "late_marks" in j
    assert "late_threshold" in j


def test_punch_in_and_out(exec_h):
    """Test punch in (idempotent) then current-status structure"""
    r = requests.post(f"{API}/attendance/punch-in",
                      json={"work_mode": "office"}, headers=exec_h, timeout=20)
    # Accept either fresh punch (200) or already punched (200 with already_punched flag) or completed (400)
    assert r.status_code in (200, 400), r.text
    if r.status_code == 200:
        j = r.json()
        assert "log" in j or "already_punched" in j
        if not j.get("already_punched"):
            assert "is_late" in j
            assert "expected_clock_out_at" in j  # may be None if not late

    # current-status should now be in_progress or completed
    s = requests.get(f"{API}/attendance/current-status", headers=exec_h, timeout=20)
    assert s.status_code == 200
    sj = s.json()
    if sj["status"] == "in_progress":
        assert "elapsed_minutes" in sj
        assert "remaining_minutes" in sj


def test_punch_out_short_hours_confirmation(exec_h):
    """If punched-in today, punch-out without confirm should require confirmation if <9h."""
    # Ensure in progress
    s = requests.get(f"{API}/attendance/current-status", headers=exec_h, timeout=20).json()
    if s["status"] != "in_progress":
        pytest.skip(f"Not in progress (status={s['status']}), can't test short_hours")

    elapsed = s.get("elapsed_minutes", 0)
    if elapsed >= 540:
        pytest.skip("9h+ already elapsed; can't test short_hours flow")

    r = requests.post(f"{API}/attendance/punch-out",
                      json={"confirm_short_hours": False}, headers=exec_h, timeout=20)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j.get("requires_confirmation") is True
    assert j.get("short_hours") is True


# ─── Attendance my-month ────────────────────────────────────
def test_my_month(exec_h):
    r = requests.get(f"{API}/attendance/my-month?year=2026&month=5", headers=exec_h, timeout=20)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "days" in j and isinstance(j["days"], list)
    assert len(j["days"]) == 31
    assert "counters" in j
    for k in ("present", "late", "absent", "leave", "lwp"):
        assert k in j["counters"], f"Missing counter {k}"
    assert "late_marks" in j


# ─── Permissions ────────────────────────────────────────────
def test_exec_forbidden_today(exec_h):
    r = requests.get(f"{API}/attendance/today", headers=exec_h, timeout=20)
    assert r.status_code == 403, f"Expected 403 for sales_exec, got {r.status_code}"


def test_exec_my_balance_ok(exec_h):
    r = requests.get(f"{API}/leaves/my-balance", headers=exec_h, timeout=20)
    assert r.status_code == 200


def test_admin_today(admin_h):
    r = requests.get(f"{API}/attendance/today", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "counts" in j
    for k in ("present", "late", "absent", "leave"):
        assert k in j["counts"]


def test_admin_dashboard(admin_h):
    r = requests.get(f"{API}/attendance/dashboard", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    j = r.json()
    for k in ("total_late_marks_this_month", "total_cl_auto_deducted_this_month", "total_lwp_this_month"):
        assert k in j, f"Missing key {k}"


# ─── Regularization ────────────────────────────────────────
def test_regularize_recent(exec_h):
    # 1 day ago - within 3-day grace
    d = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    payload = {"date": d, "reason": "Forgot to punch TEST", "request_type": "missed_punch"}
    r = requests.post(f"{API}/attendance/regularize", json=payload, headers=exec_h, timeout=20)
    # If submitted previously it may fail with conflict; tolerate either accept or duplicate
    assert r.status_code in (200, 400), r.text
    if r.status_code == 200:
        assert "request_id" in r.json()


def test_regularize_too_old(exec_h):
    d = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
    payload = {"date": d, "reason": "Old date test TEST", "request_type": "missed_punch"}
    r = requests.post(f"{API}/attendance/regularize", json=payload, headers=exec_h, timeout=20)
    assert r.status_code == 400
    assert "expired" in r.text.lower() or "window" in r.text.lower() or "grace" in r.text.lower()
