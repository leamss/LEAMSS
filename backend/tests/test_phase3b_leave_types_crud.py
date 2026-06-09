"""Phase 3B Bug Fix - Leave Types Management CRUD - Backend Tests

Covers the 15 acceptance criteria from review_request:
- GET with stats
- PATCH system type name blocked (403)
- PATCH system type allowed fields
- DELETE system type forbidden
- Deactivate/Activate on system type
- Custom type CRUD (create, patch name allowed, soft delete with cancelled_applications)
- DELETE reason min_length=20 → 422
- Sales-exec permission denied (403)
- /leave-types/{key}/usage endpoint
- Audit log scope filter
- Phase 3A regression: employee GET /leaves/types hides inactive/soft_deleted
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://compliance-hub-751.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@leamss.com", "Admin@123")
EXEC = ("sexec-test@leamss.com", "Pass@1234")

CUSTOM_KEY = "study_leave_v2"


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


# ─── Test 1: GET leave-types as admin returns all + stats ───
def test_01_admin_get_leave_types_with_stats(admin_h):
    # default GET should return active types with stats
    r = requests.get(f"{API}/hr/leave-types", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list) and len(items) >= 7
    # verify stats keys exist
    for lt in items:
        assert "stats" in lt, f"Leave type {lt.get('key')} missing stats"
        s = lt["stats"]
        for k in ("active_applications", "approved_future", "employees_used", "historical_total"):
            assert k in s, f"stats missing key {k} for {lt.get('key')}"

    # include_inactive=true should also work
    r2 = requests.get(f"{API}/hr/leave-types?include_inactive=true",
                      headers=admin_h, timeout=20)
    assert r2.status_code == 200
    assert len(r2.json()) >= len(items)


# ─── Test 2: PATCH system type name → 403 ───
def test_02_patch_system_type_name_forbidden(admin_h):
    r = requests.patch(f"{API}/hr/leave-types/casual_leave",
                       json={"name": "Renamed CL"},
                       headers=admin_h, timeout=20)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
    detail = r.json().get("detail", "")
    assert "Cannot modify field" in detail or "system" in detail.lower(), detail


# ─── Test 3: PATCH casual_leave color + quota → 200 + audit ───
def test_03_patch_system_type_allowed_fields(admin_h):
    # snapshot
    items = requests.get(f"{API}/hr/leave-types", headers=admin_h, timeout=20).json()
    cl = next(lt for lt in items if lt["key"] == "casual_leave")
    orig_color = cl.get("color", "#3b82f6")
    orig_quota = cl.get("annual_quota")

    r = requests.patch(f"{API}/hr/leave-types/casual_leave",
                       json={"color": "#06b6d4", "annual_quota": 15},
                       headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    fields = body.get("fields", [])
    assert "color" in fields and "annual_quota" in fields

    # verify persistence
    items2 = requests.get(f"{API}/hr/leave-types", headers=admin_h, timeout=20).json()
    cl2 = next(lt for lt in items2 if lt["key"] == "casual_leave")
    assert cl2["color"] == "#06b6d4"
    assert cl2["annual_quota"] == 15

    # audit
    a = requests.get(f"{API}/hr/audit-log?scope=leave_type:casual_leave",
                     headers=admin_h, timeout=20).json()
    assert len(a) >= 1
    latest = a[0]
    assert latest["action"] == "update"
    assert latest["after"].get("color") == "#06b6d4"

    # restore color to #3b82f6, keep quota change minimal: restore both
    requests.patch(f"{API}/hr/leave-types/casual_leave",
                   json={"color": orig_color, "annual_quota": orig_quota},
                   headers=admin_h, timeout=20)


# ─── Test 4: DELETE system type forbidden (403) ───
def test_04_delete_system_type_forbidden(admin_h):
    r = requests.delete(
        f"{API}/hr/leave-types/casual_leave",
        json={"reason": "attempting system type delete which should fail"},
        headers=admin_h, timeout=20,
    )
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
    detail = r.json().get("detail", "")
    assert "cannot be deleted" in detail.lower()
    assert "deactivate" in detail.lower()

    # ensure casual_leave still exists and is_active
    items = requests.get(f"{API}/hr/leave-types?include_inactive=true",
                        headers=admin_h, timeout=20).json()
    cl = next(lt for lt in items if lt["key"] == "casual_leave")
    assert cl.get("soft_deleted", False) is False


# ─── Test 5: Deactivate sick_leave → 200, is_active=false ───
def test_05_deactivate_sick_leave(admin_h):
    r = requests.post(f"{API}/hr/leave-types/sick_leave/deactivate",
                      json={"reason": "Testing deactivation"},
                      headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text

    items = requests.get(f"{API}/hr/leave-types?include_inactive=true",
                        headers=admin_h, timeout=20).json()
    sl = next(lt for lt in items if lt["key"] == "sick_leave")
    assert sl["is_active"] is False
    assert sl.get("deactivation_reason") == "Testing deactivation"


# ─── Test 6: Activate sick_leave → 200, is_active=true ───
def test_06_activate_sick_leave(admin_h):
    r = requests.post(f"{API}/hr/leave-types/sick_leave/activate",
                      headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text

    items = requests.get(f"{API}/hr/leave-types", headers=admin_h, timeout=20).json()
    sl = next(lt for lt in items if lt["key"] == "sick_leave")
    assert sl["is_active"] is True


# ─── Test 7: Create custom leave type study_leave_v2 ───
def test_07_create_custom_leave_type(admin_h):
    # clean up if existing
    requests.delete(f"{API}/hr/leave-types/{CUSTOM_KEY}",
                    json={"reason": "Cleanup before create test - existed from prior run"},
                    headers=admin_h, timeout=20)

    payload = {
        "key": CUSTOM_KEY,
        "name": "Study Leave V2",
        "short_code": "STD2",
        "annual_quota": 5,
        "monthly_cap": 0,
        "max_consecutive": 3,
        "color": "#22d3ee",
    }
    r = requests.post(f"{API}/hr/leave-types", json=payload,
                     headers=admin_h, timeout=20)
    # if previous run soft-deleted with same key, may conflict
    if r.status_code != 200:
        # try delete by hard re-creation: still soft-deleted records prevent recreation?
        # Per code: POST checks existing key - skip if soft_deleted by allowing reuse only after hard delete
        pass
    assert r.status_code == 200, f"Create failed: {r.status_code} {r.text}"
    j = r.json()
    assert j.get("key") == CUSTOM_KEY or "Leave type" in str(j)


# ─── Test 8: PATCH custom type name allowed ───
def test_08_patch_custom_type_name_allowed(admin_h):
    r = requests.patch(f"{API}/hr/leave-types/{CUSTOM_KEY}",
                       json={"name": "Study Leave Renamed", "annual_quota": 7},
                       headers=admin_h, timeout=20)
    assert r.status_code == 200, f"Expected 200 for custom type name update, got {r.status_code}: {r.text}"

    items = requests.get(f"{API}/hr/leave-types", headers=admin_h, timeout=20).json()
    lt = next((x for x in items if x["key"] == CUSTOM_KEY), None)
    assert lt is not None
    assert lt["name"] == "Study Leave Renamed"
    assert lt["annual_quota"] == 7


# ─── Test 10 (run before 9): short reason → 422 ───
def test_10_delete_short_reason_returns_422(admin_h):
    r = requests.request(
        "DELETE", f"{API}/hr/leave-types/{CUSTOM_KEY}",
        json={"reason": "short"},  # 5 chars, less than min 20
        headers=admin_h, timeout=20,
    )
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"


# ─── Test 9: DELETE custom type → 200 + cancelled_applications + soft_deleted ───
def test_09_soft_delete_custom_leave_type(admin_h):
    r = requests.request(
        "DELETE", f"{API}/hr/leave-types/{CUSTOM_KEY}",
        json={"reason": "Cleanup of test custom leave type created"},
        headers=admin_h, timeout=20,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert "cancelled_applications" in body
    assert isinstance(body["cancelled_applications"], int)

    # subsequent GET with include_inactive should show soft_deleted=true, is_active=false
    items = requests.get(f"{API}/hr/leave-types?include_inactive=true",
                        headers=admin_h, timeout=20).json()
    lt = next((x for x in items if x["key"] == CUSTOM_KEY), None)
    assert lt is not None, f"Soft-deleted type should still be returned with include_inactive=true"
    assert lt.get("soft_deleted") is True
    assert lt.get("is_active") is False

    # GET with include_inactive=false should NOT include soft-deleted
    items_default = requests.get(f"{API}/hr/leave-types?include_inactive=false",
                                 headers=admin_h, timeout=20).json()
    assert CUSTOM_KEY not in [x["key"] for x in items_default]


# ─── Test 11: Sales exec PATCH → 403 ───
def test_11_patch_leave_type_forbidden_for_sexec(exec_h):
    r = requests.patch(f"{API}/hr/leave-types/casual_leave",
                       json={"color": "#999999"},
                       headers=exec_h, timeout=20)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


# ─── Test 12: GET /leave-types/{key}/usage as admin ───
def test_12_get_leave_type_usage(admin_h):
    r = requests.get(f"{API}/hr/leave-types/casual_leave/usage",
                     headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "stats" in body, f"usage response missing 'stats' key: {body}"
    s = body["stats"]
    for k in ("active_applications", "approved_future", "employees_used", "historical_total"):
        assert k in s, f"usage stats missing key {k}"
        assert isinstance(s[k], int)


# ─── Test 13: Audit log scope filter ───
def test_13_audit_log_scope_filter(admin_h):
    r = requests.get(f"{API}/hr/audit-log?scope=leave_type:casual_leave",
                     headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) >= 1, "Expected at least one audit entry from test_03 color change"
    for it in items:
        assert it["scope"] == "leave_type:casual_leave"


# ─── Test 14: Phase 3A regression — employee /leaves/types hides inactive/deleted ───
def test_14_employee_leaves_types_excludes_inactive_and_deleted(exec_h, admin_h):
    # First ensure study_leave_v2 is soft-deleted (test_09 should have done it)
    # And we will temporarily deactivate sick_leave to verify hidden flag
    requests.post(f"{API}/hr/leave-types/sick_leave/deactivate",
                  json={"reason": "Temporary regression test deactivation"},
                  headers=admin_h, timeout=20)

    try:
        r = requests.get(f"{API}/leaves/types", headers=exec_h, timeout=20)
        assert r.status_code == 200, r.text
        items = r.json()
        keys = [x.get("key") for x in items]
        assert CUSTOM_KEY not in keys, f"Soft-deleted {CUSTOM_KEY} leaked to employee endpoint"
        assert "sick_leave" not in keys, "Deactivated sick_leave leaked to employee endpoint"
    finally:
        # Always reactivate sick_leave
        requests.post(f"{API}/hr/leave-types/sick_leave/activate",
                      headers=admin_h, timeout=20)

    # Verify sick_leave returns after reactivation
    r2 = requests.get(f"{API}/leaves/types", headers=exec_h, timeout=20)
    assert r2.status_code == 200
    keys2 = [x.get("key") for x in r2.json()]
    assert "sick_leave" in keys2, "sick_leave should reappear after reactivation"
