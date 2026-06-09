"""Phase 3B - HR Admin Settings UI - Backend Tests

Tests all new HR admin endpoints under /api/hr prefix:
- /settings GET/PATCH + audit log
- /holidays GET / import-indian / copy-from
- /leave-types POST/PATCH/DELETE (incl. system type protection)
- /approvers/config GET/PATCH, /approvers/simulate, /eligible-approvers
- /audit-log
- Permission isolation (sales_executive denied)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://compliance-hub-751.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@leamss.com", "Admin@123")
MGR = ("smgr-test@leamss.com", "Pass@1234")
EXEC = ("sexec-test@leamss.com", "Pass@1234")

ADMIN_ID = "07ef3894-e58b-4429-bdec-bd14a7a05975"
SEXEC_ID = "44bd0424-9e5b-4390-8dd2-ec0ecb50253f"
SMGR_ID = "5b3a3c68-f854-42a4-bb16-0179cb6efae6"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    j = r.json()
    return j.get("access_token") or j.get("token")


@pytest.fixture(scope="session")
def admin_h():
    return {"Authorization": f"Bearer {_login(*ADMIN)}"}


@pytest.fixture(scope="session")
def exec_h():
    return {"Authorization": f"Bearer {_login(*EXEC)}"}


# ─── Settings ─────────────────────────────────────────────
def test_get_settings_admin(admin_h):
    r = requests.get(f"{API}/hr/settings", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    s = r.json()
    assert "office_start_time" in s
    assert "late_threshold_minutes" in s
    assert "monthly_cl_limit" in s


def test_patch_settings_admin_creates_audit(admin_h):
    # Snapshot original
    orig = requests.get(f"{API}/hr/settings", headers=admin_h, timeout=20).json()
    original_time = orig.get("office_start_time", "10:00")

    # Patch to 09:30
    r = requests.patch(f"{API}/hr/settings", json={"office_start_time": "09:30"},
                       headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    assert "fields" in r.json()
    assert "office_start_time" in r.json()["fields"]

    # Verify persistence
    g = requests.get(f"{API}/hr/settings", headers=admin_h, timeout=20).json()
    assert g["office_start_time"] == "09:30"

    # Verify audit log entry
    a = requests.get(f"{API}/hr/audit-log?scope=attendance_settings",
                     headers=admin_h, timeout=20)
    assert a.status_code == 200, a.text
    entries = a.json()
    assert len(entries) >= 1
    latest = entries[0]
    assert latest["scope"] == "attendance_settings"
    assert latest["action"] == "update"
    assert latest["after"].get("office_start_time") == "09:30"

    # Restore
    requests.patch(f"{API}/hr/settings", json={"office_start_time": original_time},
                   headers=admin_h, timeout=20)


# ─── Holidays ─────────────────────────────────────────────
def test_get_holidays_2026(admin_h):
    r = requests.get(f"{API}/hr/holidays?year=2026", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    # Should have at least 9 holidays (seeded from DEFAULT_HOLIDAYS_2026)
    assert len(items) >= 9, f"Expected >=9 holidays for 2026, got {len(items)}"
    for h in items:
        assert "date" in h and "name" in h
        assert h["date"].startswith("2026-")


def test_import_indian_holidays_2027(admin_h):
    r = requests.post(f"{API}/hr/holidays/import-indian/2027",
                      headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "inserted" in j and "skipped" in j
    # First run inserts, repeat run skips. Either way list returns 9+ entries.
    g = requests.get(f"{API}/hr/holidays?year=2027", headers=admin_h, timeout=20).json()
    assert len(g) >= 9, f"Expected >=9 holidays for 2027, got {len(g)}"


def test_copy_holidays_2026_to_2028(admin_h):
    r = requests.post(f"{API}/hr/holidays/copy-from/2026/to/2028",
                      headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "inserted" in j and "skipped" in j
    g = requests.get(f"{API}/hr/holidays?year=2028", headers=admin_h, timeout=20).json()
    src_count = len(requests.get(f"{API}/hr/holidays?year=2026",
                                 headers=admin_h, timeout=20).json())
    assert len(g) >= src_count, f"Expected >={src_count} holidays for 2028 copied from 2026"


# ─── Leave Types ─────────────────────────────────────────────
def test_create_custom_leave_type(admin_h):
    # Clean any pre-existing study_leave
    requests.delete(f"{API}/hr/leave-types/study_leave",
                    headers=admin_h, timeout=20)

    payload = {
        "key": "study_leave",
        "name": "Study Leave",
        "short_code": "STD",
        "annual_quota": 5,
        "monthly_cap": 0,
        "max_consecutive": 3,
        "color": "#22d3ee",
    }
    r = requests.post(f"{API}/hr/leave-types", json=payload, headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    assert r.json()["key"] == "study_leave"


def test_list_leave_types_has_study_leave(admin_h):
    r = requests.get(f"{API}/hr/leave-types", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    items = r.json()
    keys = [lt.get("key") for lt in items]
    assert "study_leave" in keys
    assert len(items) >= 8, f"Expected >=8 leave types incl study_leave, got {len(items)}"


def test_patch_study_leave_quota(admin_h):
    r = requests.patch(f"{API}/hr/leave-types/study_leave",
                       json={"annual_quota": 7}, headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    # Verify persistence
    items = requests.get(f"{API}/hr/leave-types", headers=admin_h, timeout=20).json()
    sl = next(lt for lt in items if lt["key"] == "study_leave")
    assert sl["annual_quota"] == 7

    # Verify audit
    a = requests.get(f"{API}/hr/audit-log?scope=leave_type:study_leave",
                     headers=admin_h, timeout=20).json()
    assert len(a) >= 1
    assert a[0]["action"] == "update"


def test_delete_custom_leave_type(admin_h):
    r = requests.delete(f"{API}/hr/leave-types/study_leave",
                        json={"reason": "Cleanup of test custom leave type for regression suite"},
                        headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    items = requests.get(f"{API}/hr/leave-types?include_inactive=false",
                         headers=admin_h, timeout=20).json()
    assert "study_leave" not in [lt["key"] for lt in items]


def test_delete_system_leave_type_forbidden(admin_h):
    r = requests.delete(f"{API}/hr/leave-types/casual_leave",
                        json={"reason": "Attempting system type delete which should fail with 403"},
                        headers=admin_h, timeout=20)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
    # Verify still exists
    items = requests.get(f"{API}/hr/leave-types", headers=admin_h, timeout=20).json()
    assert "casual_leave" in [lt["key"] for lt in items]


# ─── Approver Config ─────────────────────────────────────────────
def test_get_approver_config_admin(admin_h):
    r = requests.get(f"{API}/hr/approvers/config", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    c = r.json()
    assert "final_approver_logic" in c
    assert "final_approver_user" in c
    assert "final_approvers_by_department" in c


def test_patch_approver_config(admin_h):
    r = requests.patch(
        f"{API}/hr/approvers/config",
        json={"final_approver_logic": "specific_user",
              "final_approver_user_id": ADMIN_ID},
        headers=admin_h, timeout=20,
    )
    assert r.status_code == 200, r.text
    c = requests.get(f"{API}/hr/approvers/config", headers=admin_h, timeout=20).json()
    assert c["final_approver_logic"] == "specific_user"
    assert c["final_approver_user_id"] == ADMIN_ID
    assert c["final_approver_user"] is not None
    assert c["final_approver_user"]["id"] == ADMIN_ID


def test_simulate_approval_chain_for_sexec(admin_h):
    r = requests.get(f"{API}/hr/approvers/simulate/{SEXEC_ID}",
                     headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["applicant"]["id"] == SEXEC_ID
    assert j["l1_manager"] is not None
    assert j["l1_manager"]["user_id"] == SMGR_ID
    assert j["final_approver"] is not None
    assert j["final_approver"]["user_id"] == ADMIN_ID
    assert j["skips_l1"] is False
    assert j["single_stage"] is False


def test_eligible_approvers_admin(admin_h):
    r = requests.get(f"{API}/hr/eligible-approvers", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    roles = {u.get("rbac_role") for u in items}
    # Should include heads/admin/managers
    assert any(r in roles for r in
               ["admin_owner", "sales_head", "hr_head", "sales_manager"])


# ─── Audit Log endpoint ─────────────────────────────────────────────
def test_audit_log_returns_entries(admin_h):
    r = requests.get(f"{API}/hr/audit-log?limit=20", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    for it in items:
        assert "scope" in it and "action" in it and "actor_id" in it
        assert "created_at" in it


# ─── Permission Isolation ─────────────────────────────────────────────
def test_settings_forbidden_for_sexec(exec_h):
    r = requests.get(f"{API}/hr/settings", headers=exec_h, timeout=20)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


def test_patch_leave_type_forbidden_for_sexec(exec_h):
    r = requests.patch(f"{API}/hr/leave-types/casual_leave",
                       json={"annual_quota": 99}, headers=exec_h, timeout=20)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


def test_approver_config_forbidden_for_sexec(exec_h):
    r = requests.get(f"{API}/hr/approvers/config", headers=exec_h, timeout=20)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


def test_import_indian_forbidden_for_sexec(exec_h):
    r = requests.post(f"{API}/hr/holidays/import-indian/2029",
                      headers=exec_h, timeout=20)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
