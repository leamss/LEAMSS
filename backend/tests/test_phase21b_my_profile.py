"""Phase 21.B — Employee self-service profile backend tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@leamss.com", "password": "Admin@123"},
        timeout=30,
    )
    assert r.status_code == 200
    return r.json()["token"]


def test_get_me_profile_returns_user(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/employees/me/profile",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("email") == "admin@leamss.com"
    assert "permissions" in data
    assert "doc_count" in data


def test_patch_section_personal(admin_token):
    payload = {"mobile": "+91 90000 00000", "address": {"city": "Bengaluru", "state": "KA"}}
    r = requests.patch(
        f"{BASE_URL}/api/employees/me/section/personal",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["section"] == "personal"
    assert "mobile" in data["updated_fields"] or "address" in data["updated_fields"]


def test_patch_section_bank_bad_ifsc_returns_400(admin_token):
    r = requests.patch(
        f"{BASE_URL}/api/employees/me/section/bank",
        json={"bank_account": {"ifsc": "BADIFSC", "account_number": "123"}},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert r.status_code == 400
    assert "ifsc" in r.text.lower()


def test_patch_section_bank_valid_ifsc(admin_token):
    r = requests.patch(
        f"{BASE_URL}/api/employees/me/section/bank",
        json={"bank_account": {"ifsc": "SBIN0001234", "account_number": "1234567890"}},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert r.status_code == 200


def test_patch_unknown_section_returns_400(admin_token):
    r = requests.patch(
        f"{BASE_URL}/api/employees/me/section/foobar",
        json={"mobile": "x"},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert r.status_code == 400


def test_audit_history_grows_after_patch(admin_token):
    # Trigger a save
    requests.patch(
        f"{BASE_URL}/api/employees/me/section/preferences",
        json={"work_location": "Hyderabad"},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    r = requests.get(
        f"{BASE_URL}/api/employees/me/audit-history?limit=10",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert any("section_updated" in str(i.get("action", "")) for i in items)
