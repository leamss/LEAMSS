"""Phase 21 Slice 2 — Documents Vault + Onboarding + Assets + Payroll backend tests."""
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
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_id(admin_token):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    return r.json()["id"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


# ══════════════════════════════════════════════════════
# 21.C — DOCUMENTS VAULT (6 tests)
# ══════════════════════════════════════════════════════

def test_doc_list_own_empty_or_list(admin_token, admin_id):
    r = requests.get(f"{BASE_URL}/api/employees/{admin_id}/documents", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_doc_create(admin_token, admin_id):
    r = requests.post(
        f"{BASE_URL}/api/employees/{admin_id}/documents",
        json={
            "document_type": "id_proof",
            "document_name": "Aadhar (test)",
            "file_url": "https://example.com/aadhar.pdf",
            "file_size_bytes": 1024,
            "mime_type": "application/pdf",
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["document_type"] == "id_proof"
    assert d["status"] == "uploaded"
    assert d["version"] == 1


def test_doc_invalid_type_returns_400(admin_token, admin_id):
    r = requests.post(
        f"{BASE_URL}/api/employees/{admin_id}/documents",
        json={"document_type": "invalid", "document_name": "x", "file_url": "https://x"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 400


def test_doc_verify_workflow(admin_token, admin_id):
    create = requests.post(
        f"{BASE_URL}/api/employees/{admin_id}/documents",
        json={"document_type": "education", "document_name": "Degree", "file_url": "https://x/degree.pdf"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.patch(
        f"{BASE_URL}/api/employees/{admin_id}/documents/{create['id']}",
        json={"status": "verified"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200


def test_doc_replace_creates_version_2(admin_token, admin_id):
    create = requests.post(
        f"{BASE_URL}/api/employees/{admin_id}/documents",
        json={"document_type": "bank", "document_name": "Bank slip", "file_url": "https://x/v1.pdf"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.post(
        f"{BASE_URL}/api/employees/{admin_id}/documents/{create['id']}/replace",
        json={"document_type": "bank", "document_name": "Bank slip v2", "file_url": "https://x/v2.pdf"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2


def test_doc_share_token(admin_token, admin_id):
    create = requests.post(
        f"{BASE_URL}/api/employees/{admin_id}/documents",
        json={"document_type": "passport", "document_name": "Passport", "file_url": "https://x/passport.pdf"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    r = requests.post(
        f"{BASE_URL}/api/employees/{admin_id}/documents/{create['id']}/share",
        json={"access_type": "view", "expires_in_hours": 1},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    token = r.json()["token"]
    # Public access via share token (no auth)
    sr = requests.get(f"{BASE_URL}/api/employee-documents/share/{token}", timeout=15)
    assert sr.status_code == 200
    assert sr.json()["file_url"] == "https://x/passport.pdf"


# ══════════════════════════════════════════════════════
# 21.D — ONBOARDING + ASSETS (8 tests)
# ══════════════════════════════════════════════════════

def test_onboarding_create_template(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/onboarding/templates",
        json={
            "name": "Pytest standard onboarding",
            "steps": [
                {"step_number": 1, "name": "Sign contract", "type": "acknowledgment", "assigned_to_role": "employee"},
                {"step_number": 2, "name": "Submit ID proof", "type": "document_upload", "assigned_to_role": "employee"},
                {"step_number": 3, "name": "Assign laptop", "type": "manual_check", "assigned_to_role": "it"},
            ],
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert len(r.json()["steps"]) == 3


def test_onboarding_invalid_step_type_returns_400(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/onboarding/templates",
        json={
            "name": "bad",
            "steps": [{"step_number": 1, "name": "x", "type": "invalid_type"}],
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 400


def test_onboarding_start_and_complete_step(admin_token, admin_id):
    # Create template
    tpl = requests.post(
        f"{BASE_URL}/api/onboarding/templates",
        json={
            "name": "Pytest start template",
            "steps": [
                {"step_number": 1, "name": "Step one", "type": "manual_check"},
                {"step_number": 2, "name": "Step two", "type": "manual_check"},
            ],
        },
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    # Start workflow
    wf = requests.post(
        f"{BASE_URL}/api/onboarding/start",
        json={"employee_id": admin_id, "template_id": tpl["id"]},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    assert wf["status"] == "in_progress"
    # Complete step 1
    r1 = requests.patch(
        f"{BASE_URL}/api/onboarding/{wf['id']}/step/1/complete",
        json={"notes": "done"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r1.status_code == 200
    # Complete step 2
    r2 = requests.patch(
        f"{BASE_URL}/api/onboarding/{wf['id']}/step/2/complete",
        json={"notes": "done"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"


def test_asset_create(admin_token):
    import uuid as _u
    tag = "PYT-" + _u.uuid4().hex[:6].upper()
    r = requests.post(
        f"{BASE_URL}/api/assets",
        json={
            "asset_tag": tag,
            "asset_type": "laptop",
            "brand": "Dell",
            "model": "Latitude 5530",
            "serial_number": "SN12345",
            "condition": "new",
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["asset_tag"] == tag
    assert r.json()["status"] == "available"


def test_asset_unique_tag_enforced(admin_token):
    import uuid as _u
    tag = "DUP-" + _u.uuid4().hex[:6].upper()
    r1 = requests.post(
        f"{BASE_URL}/api/assets",
        json={"asset_tag": tag, "asset_type": "laptop"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r1.status_code == 200
    r2 = requests.post(
        f"{BASE_URL}/api/assets",
        json={"asset_tag": tag, "asset_type": "phone"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r2.status_code == 400


def test_asset_issue_and_return(admin_token, admin_id):
    import uuid as _u
    tag = "IR-" + _u.uuid4().hex[:6].upper()
    a = requests.post(
        f"{BASE_URL}/api/assets",
        json={"asset_tag": tag, "asset_type": "headset", "brand": "Jabra"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    # Issue
    r1 = requests.post(
        f"{BASE_URL}/api/assets/{a['id']}/issue",
        json={"employee_id": admin_id, "expected_return_date": "2026-12-31"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "issued"
    assert r1.json()["current_holder_id"] == admin_id
    # Cannot re-issue
    r_dup = requests.post(
        f"{BASE_URL}/api/assets/{a['id']}/issue",
        json={"employee_id": admin_id},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r_dup.status_code == 400
    # Return
    r2 = requests.post(
        f"{BASE_URL}/api/assets/{a['id']}/return",
        json={"condition": "good", "notes": "back from owner"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "available"


def test_my_assets_lists_holdings(admin_token, admin_id):
    import uuid as _u
    tag = "MY-" + _u.uuid4().hex[:6].upper()
    a = requests.post(
        f"{BASE_URL}/api/assets",
        json={"asset_tag": tag, "asset_type": "monitor"},
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    requests.post(
        f"{BASE_URL}/api/assets/{a['id']}/issue",
        json={"employee_id": admin_id},
        headers=_auth(admin_token),
        timeout=15,
    )
    r = requests.get(f"{BASE_URL}/api/employees/{admin_id}/assets", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert any(x["id"] == a["id"] for x in r.json())


def test_onboarding_get_workflow_unauthorized(admin_token):
    # Non-existent workflow returns 404
    r = requests.get(
        f"{BASE_URL}/api/onboarding/nonexistent-id",
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 404


# ══════════════════════════════════════════════════════
# 21.G — SALARY + PAYROLL (12 tests)
# ══════════════════════════════════════════════════════

def test_calculate_ctc_preview(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/salary-structures/calculate-ctc",
        json={
            "components": {"basic": 30000, "hra": 12000, "special_allowance": 8000, "conveyance": 1600, "medical_allowance": 1250, "lta": 2000, "custom": []},
            "deductions": {},
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["gross_monthly_inr"] == 54850
    # PF employer on basic 30000 (capped at 15000 wage cap) × 12% = 1800
    assert d["pf_employer_monthly_inr"] == 1800
    assert d["ctc_monthly_inr"] == 56650
    assert d["ctc_annual_inr"] == 56650 * 12


def test_create_salary_structure(admin_token, admin_id):
    r = requests.post(
        f"{BASE_URL}/api/employees/{admin_id}/salary-structure",
        json={
            "effective_from": "2026-01-01",
            "components": {"basic": 50000, "hra": 20000, "special_allowance": 10000, "conveyance": 1600, "medical_allowance": 1250, "lta": 5000},
            "deductions": {},
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    assert r.json()["gross_monthly_inr"] == 87850


def test_current_salary_structure(admin_token, admin_id):
    r = requests.get(
        f"{BASE_URL}/api/employees/{admin_id}/salary-structure",
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    if r.json():
        assert r.json()["status"] == "active"


def test_salary_supersession(admin_token, admin_id):
    # Create new structure → old one should be superseded
    requests.post(
        f"{BASE_URL}/api/employees/{admin_id}/salary-structure",
        json={
            "effective_from": "2026-04-01",
            "components": {"basic": 60000, "hra": 24000, "special_allowance": 12000, "conveyance": 1600, "medical_allowance": 1250},
        },
        headers=_auth(admin_token),
        timeout=15,
    )
    history = requests.get(
        f"{BASE_URL}/api/employees/{admin_id}/salary-structure/history",
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    # At least one structure superseded
    superseded = [h for h in history if h["status"] == "superseded"]
    assert len(superseded) >= 1


def test_payslip_generate_for_self(admin_token, admin_id):
    r = requests.post(
        f"{BASE_URL}/api/payslips/generate",
        json={"employee_ids": [admin_id], "period": "2026-02"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    # Either freshly created OR previously paid/approved (idempotent skip)
    if data["count"] >= 1:
        payslip_info = data["created"][0]
        assert "payslip_id" in payslip_info
        assert payslip_info["net_pay_inr"] > 0
    else:
        # Was skipped because already approved/paid from prior run
        assert len(data["skipped"]) >= 1
        # Verify a payslip exists for this employee + period
        listed = requests.get(
            f"{BASE_URL}/api/payslips?employee_id={admin_id}&period=2026-02",
            headers=_auth(admin_token),
            timeout=15,
        ).json()
        assert len(listed) >= 1


def test_payslip_get_detail(admin_token, admin_id):
    # Find a payslip from previous test
    listed = requests.get(
        f"{BASE_URL}/api/payslips?employee_id={admin_id}&period=2026-02",
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    assert len(listed) >= 1
    pid = listed[0]["id"]
    r = requests.get(f"{BASE_URL}/api/payslips/{pid}", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert "earnings" in r.json()
    assert "deductions" in r.json()


def test_payslip_pdf_download(admin_token, admin_id):
    listed = requests.get(
        f"{BASE_URL}/api/payslips?employee_id={admin_id}&period=2026-02",
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    pid = listed[0]["id"]
    r = requests.get(f"{BASE_URL}/api/payslips/{pid}/pdf", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    # PDF magic
    assert r.content[:5] == b"%PDF-"


def test_payslip_approve_workflow(admin_token, admin_id):
    listed = requests.get(
        f"{BASE_URL}/api/payslips?employee_id={admin_id}&period=2026-02",
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    draft = [p for p in listed if p["status"] == "draft"]
    if not draft:
        pytest.skip("No draft payslip available")
    pid = draft[0]["id"]
    r = requests.patch(f"{BASE_URL}/api/payslips/{pid}/approve", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200


def test_payslip_mark_paid(admin_token, admin_id):
    listed = requests.get(
        f"{BASE_URL}/api/payslips?employee_id={admin_id}&period=2026-02",
        headers=_auth(admin_token),
        timeout=15,
    ).json()
    approved = [p for p in listed if p["status"] == "approved"]
    if not approved:
        pytest.skip("No approved payslip available")
    pid = approved[0]["id"]
    r = requests.patch(
        f"{BASE_URL}/api/payslips/{pid}/mark-paid",
        json={"payment_reference": "PYTEST-REF-001"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 200


def test_my_payslips_view(admin_token):
    r = requests.get(f"{BASE_URL}/api/employees/me/payslips", headers=_auth(admin_token), timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_payslip_pf_calc_boundary(admin_token, admin_id):
    """When basic > 15000, PF should cap at 15000 × 12% = 1800."""
    r = requests.post(
        f"{BASE_URL}/api/salary-structures/calculate-ctc",
        json={"components": {"basic": 50000}, "deductions": {}},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.json()["pf_employer_monthly_inr"] == 1800


def test_payslip_invalid_period_returns_400(admin_token, admin_id):
    r = requests.post(
        f"{BASE_URL}/api/payslips/generate",
        json={"employee_ids": [admin_id], "period": "bad-period"},
        headers=_auth(admin_token),
        timeout=15,
    )
    assert r.status_code == 400
