"""Tests for Salesperson Target Management.

Covers:
1. Admin setting and managing individual salesperson targets for Daily, Weekly, and Monthly.
2. Tracking targets for leads, calls, follow-ups, conversions, revenue, and deal count.
3. Target vs. actual performance calculation, achievement %, and pending targets (max(0, target - actual)).
4. Automated activity tracking from CRM activities (leads, crm_calls, follow_ups).
5. Target updating with reason and audit history.
6. RBAC: Strictly restricts target configuration to Admin / authorized managers; salespersons can only view their own targets.
7. Performance Reports endpoint with filters (salesperson, period_type, date range) and CSV export.
"""
import os
import uuid
import csv
import io
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_CREDS = ("admin@leamss.com", "Admin@123")
MGR_EMAIL = "smgr-target-test@leamss.com"
EXEC_EMAIL = "sexec-target-test@leamss.com"
OTHER_EXEC_EMAIL = "other-target-test@leamss.com"
TEST_PASS = "Pass@1234"


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json().get("token")


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module", autouse=True)
def setup_test_users():
    """Ensure test sales manager and test sales executives exist in the database."""
    from pymongo import MongoClient
    from core.auth import get_password_hash

    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "leamss")]
    users_col = db["users"]

    # Manager
    mgr = users_col.find_one({"email": MGR_EMAIL})
    mgr_id = mgr["id"] if mgr else str(uuid.uuid4())
    if not mgr:
        users_col.insert_one({
            "id": mgr_id,
            "email": MGR_EMAIL,
            "name": "Test Sales Manager",
            "password": get_password_hash(TEST_PASS),
            "role": "sales_manager",
            "rbac_role": "sales_manager",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
        })

    # Sales Executive 1 (reports to manager)
    exec1 = users_col.find_one({"email": EXEC_EMAIL})
    exec1_id = exec1["id"] if exec1 else str(uuid.uuid4())
    if not exec1:
        users_col.insert_one({
            "id": exec1_id,
            "email": EXEC_EMAIL,
            "name": "Test Sales Executive",
            "password": get_password_hash(TEST_PASS),
            "role": "sales_executive",
            "rbac_role": "sales_executive",
            "reports_to": mgr_id,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
        })

    # Sales Executive 2 (other rep)
    exec2 = users_col.find_one({"email": OTHER_EXEC_EMAIL})
    exec2_id = exec2["id"] if exec2 else str(uuid.uuid4())
    if not exec2:
        users_col.insert_one({
            "id": exec2_id,
            "email": OTHER_EXEC_EMAIL,
            "name": "Other Sales Executive",
            "password": get_password_hash(TEST_PASS),
            "role": "sales_executive",
            "rbac_role": "sales_executive",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
        })

    yield {"mgr_id": mgr_id, "exec1_id": exec1_id, "exec2_id": exec2_id}

    # Clean up test targets and activity docs
    db["sales_targets"].delete_many({"user_id": {"$in": [exec1_id, exec2_id]}})
    db["leads"].delete_many({"assigned_to": exec1_id})
    db["crm_calls"].delete_many({"sales_person_id": exec1_id})
    db["follow_ups"].delete_many({"assigned_to": exec1_id})


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN_CREDS)


@pytest.fixture(scope="module")
def exec_token():
    return _login(EXEC_EMAIL, TEST_PASS)


@pytest.fixture(scope="module")
def other_exec_token():
    return _login(OTHER_EXEC_EMAIL, TEST_PASS)


def test_admin_can_set_daily_target_with_all_metrics(admin_token, setup_test_users):
    """Admin sets a Daily target for leads, calls, follow-ups, conversions, and revenue."""
    exec_id = setup_test_users["exec1_id"]
    future_date = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")

    body = {
        "user_id": exec_id,
        "period_type": "daily",
        "period_year": int(future_date.split("-")[0]),
        "period_date": future_date,
        "leads": 12,
        "calls": 35,
        "follow_ups": 15,
        "conversions": 3,
        "revenue": 50000,
        "pa_count": 2,
        "notes": "Daily blitz targets",
    }
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=10)
    assert r.status_code == 200, f"Failed: {r.status_code} {r.text}"
    target = r.json()["target"]

    assert target["period_type"] == "daily"
    assert target["period_date"] == future_date
    assert target["targets"]["leads"] == 12
    assert target["targets"]["calls"] == 35
    assert target["targets"]["follow_ups"] == 15
    assert target["targets"]["conversions"] == 3
    assert target["targets"]["revenue"] == 50000

    # Verify pending targets are initialized
    pending = target["achievement"]["pending"]
    assert pending["leads"] == 12
    assert pending["calls"] == 35
    assert pending["follow_ups"] == 15
    assert pending["conversions"] == 3
    assert pending["revenue"] == 50000


def test_admin_can_set_weekly_target(admin_token, setup_test_users):
    """Admin sets a Weekly target for a salesperson."""
    exec_id = setup_test_users["exec1_id"]
    now = datetime.now(timezone.utc)
    future_week = (now.isocalendar()[1] + 2) % 52 or 1
    year = now.year + (1 if future_week < now.isocalendar()[1] else 0)

    body = {
        "user_id": exec_id,
        "period_type": "weekly",
        "period_year": year,
        "period_week": future_week,
        "leads": 50,
        "calls": 150,
        "follow_ups": 60,
        "conversions": 10,
        "revenue": 200000,
        "pa_count": 5,
        "notes": "Weekly team sprint",
    }
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=10)
    assert r.status_code == 200, f"Failed: {r.status_code} {r.text}"
    target = r.json()["target"]

    assert target["period_type"] == "weekly"
    assert target["period_week"] == future_week
    assert target["period_label"] == f"Week {future_week}, {year}"
    assert target["targets"]["leads"] == 50
    assert target["targets"]["calls"] == 150


def test_target_update_requires_reason(admin_token, setup_test_users):
    """Updating a target requires a descriptive reason (at least 5 chars)."""
    exec_id = setup_test_users["exec1_id"]
    future_date = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d")

    body = {
        "user_id": exec_id,
        "period_type": "daily",
        "period_year": int(future_date.split("-")[0]),
        "period_date": future_date,
        "leads": 10,
        "calls": 20,
    }
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=10)
    target_id = r.json()["target"]["id"]

    # Try updating without reason -> should fail 400
    r_bad = requests.patch(
        f"{API}/sales/targets/{target_id}",
        headers=_hdr(admin_token),
        json={"leads": 15, "reason": "bad"},
        timeout=10,
    )
    assert r_bad.status_code == 400

    # Update with valid reason -> should succeed
    r_good = requests.patch(
        f"{API}/sales/targets/{target_id}",
        headers=_hdr(admin_token),
        json={"leads": 15, "calls": 25, "reason": "Target revised due to inbound marketing boost"},
        timeout=10,
    )
    assert r_good.status_code == 200
    updated = r_good.json()["target"]
    assert updated["targets"]["leads"] == 15
    assert updated["targets"]["calls"] == 25

    # Check audit history
    assert len(updated["history"]) >= 2
    last_hist = updated["history"][-1]
    assert last_hist["action"] == "updated"
    assert "inbound marketing boost" in last_hist["reason"]


def test_salesperson_cannot_configure_targets(exec_token, other_exec_token, setup_test_users):
    """Salespersons are restricted from creating or updating targets."""
    other_id = setup_test_users["exec2_id"]
    future_date = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%d")

    # Salesperson trying to create target for another user -> 403
    r = requests.post(f"{API}/sales/targets", headers=_hdr(exec_token), json={
        "user_id": other_id,
        "period_type": "daily",
        "period_year": int(future_date.split("-")[0]),
        "period_date": future_date,
        "leads": 10,
    }, timeout=10)
    assert r.status_code == 403

    # Salesperson trying to create target for self -> 403
    r_self = requests.post(f"{API}/sales/targets", headers=_hdr(exec_token), json={
        "user_id": setup_test_users["exec1_id"],
        "period_type": "daily",
        "period_year": int(future_date.split("-")[0]),
        "period_date": future_date,
        "leads": 10,
    }, timeout=10)
    assert r_self.status_code == 403


def test_salesperson_views_only_own_targets(exec_token, admin_token, setup_test_users):
    """Salesperson can view /sales/targets/my, but cannot view other reps' targets."""
    exec_id = setup_test_users["exec1_id"]
    other_id = setup_test_users["exec2_id"]

    # Exec calling /api/sales/targets/my should succeed
    r_my = requests.get(f"{API}/sales/targets/my", headers=_hdr(exec_token), timeout=10)
    assert r_my.status_code == 200
    data = r_my.json()
    assert "daily" in data
    assert "weekly" in data
    assert "monthly" in data
    assert "quarterly" in data

    # Exec calling /api/sales/targets/user/{other_id} -> 403 Forbidden
    r_other = requests.get(f"{API}/sales/targets/user/{other_id}", headers=_hdr(exec_token), timeout=10)
    assert r_other.status_code == 403

    # But admin calling /api/sales/targets/user/{other_id} -> 200 OK
    r_admin = requests.get(f"{API}/sales/targets/user/{other_id}", headers=_hdr(admin_token), timeout=10)
    assert r_admin.status_code == 200


def test_crm_activities_automatically_track_actuals_and_pending(admin_token, setup_test_users):
    """Verify that CRM activities (leads, calls, follow-ups) automatically count towards actuals and reduce pending."""
    from pymongo import MongoClient
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "leamss")]

    exec_id = setup_test_users["exec1_id"]
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    tomorrow = now + timedelta(days=1)

    # Clean existing target for today if any
    db["sales_targets"].delete_many({
        "user_id": exec_id,
        "period_type": "daily",
        "period_date": today_str,
    })

    # Set daily target for today: leads=5, calls=10, follow_ups=8, conversions=2
    # Note: to set target for current period (which ends tomorrow), period_end > now is satisfied
    body = {
        "user_id": exec_id,
        "period_type": "daily",
        "period_year": now.year,
        "period_date": today_str,
        "leads": 5,
        "calls": 10,
        "follow_ups": 8,
        "conversions": 2,
        "revenue": 100000,
    }
    r = requests.post(f"{API}/sales/targets", headers=_hdr(admin_token), json=body, timeout=10)
    assert r.status_code == 200
    target_id = r.json()["target"]["id"]

    # Insert 2 leads assigned to exec_id for today
    for _ in range(2):
        db["leads"].insert_one({
            "id": str(uuid.uuid4()),
            "name": "Auto Activity Lead",
            "assigned_to": exec_id,
            "stage": "new",
            "status": "new",
            "created_at": now,
        })

    # Insert 4 calls for exec_id for today
    for _ in range(4):
        db["crm_calls"].insert_one({
            "id": str(uuid.uuid4()),
            "sales_person_id": exec_id,
            "call_date": now,
            "created_at": now,
        })

    # Insert 3 completed follow-ups for exec_id for today
    for _ in range(3):
        db["follow_ups"].insert_one({
            "id": str(uuid.uuid4()),
            "assigned_to": exec_id,
            "status": "completed",
            "completed_at": now,
            "created_at": now,
        })

    # Recalculate target
    r_recalc = requests.post(f"{API}/sales/targets/{target_id}/recalculate", headers=_hdr(admin_token), timeout=10)
    assert r_recalc.status_code == 200
    ach = r_recalc.json()["target"]["achievement"]

    # Assert automatic tracking of activities
    assert ach["leads"] == 2
    assert ach["calls"] == 4
    assert ach["follow_ups"] == 3

    # Assert pending targets are updated accurately
    assert ach["pending"]["leads"] == 3   # 5 target - 2 actual
    assert ach["pending"]["calls"] == 6   # 10 target - 4 actual
    assert ach["pending"]["follow_ups"] == 5  # 8 target - 3 actual

    # Assert percentages are computed
    assert ach["leads_percentage"] == 40.0   # 2/5 * 100
    assert ach["calls_percentage"] == 40.0   # 4/10 * 100
    assert ach["follow_ups_percentage"] == 37.5  # 3/8 * 100


def test_performance_reports_json_and_csv(admin_token, setup_test_users):
    """Performance Reports endpoint returns aggregated summary and CSV export."""
    exec_id = setup_test_users["exec1_id"]

    # 1. JSON report
    r_json = requests.get(
        f"{API}/sales/targets/reports?salesperson_id={exec_id}&period_type=all",
        headers=_hdr(admin_token),
        timeout=10,
    )
    assert r_json.status_code == 200
    data = r_json.json()
    assert "summary" in data
    assert "rows" in data
    summary = data["summary"]
    assert "targets" in summary
    assert "actuals" in summary
    assert "pending" in summary
    assert "overall_achievement_percentage" in summary

    # 2. CSV report
    r_csv = requests.get(
        f"{API}/sales/targets/reports?salesperson_id={exec_id}&period_type=all&format=csv",
        headers=_hdr(admin_token),
        timeout=10,
    )
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers.get("content-type", "")
    assert "Content-Disposition" in r_csv.headers

    csv_text = r_csv.text
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader)
    assert "Salesperson Name" in header
    assert "Leads Target" in header
    assert "Calls Target" in header
    assert "Follow-ups Target" in header
    assert "Conversions Target" in header
    assert "Overall Achievement %" in header
