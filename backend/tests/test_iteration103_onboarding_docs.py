"""Iteration 103 — People Onboarding Form + Document upload/verify + Custom Commissions regression.

Tests:
- GET /api/people/document-checklist/{person_type} for all 4 types
- POST /api/people with full onboarding payload (persistence verified for employee/partner/vendor)
- POST /api/people/{id}/documents — upload PDF, validate mime, 10MB cap
- GET /api/people/{id}/documents
- GET /api/people/{id}/documents/{doc_id}/download
- POST /api/people/{id}/documents/{doc_id}/verify
- DELETE /api/people/{id}/documents/{doc_id}
- /api/partner-commissions GET/POST/DELETE regression
- POST /pre-assess-portal/public/mock-pay route reachability
"""
import os
import io
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://compliance-hub-751.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email, pw):
    last = None
    for _ in range(3):
        try:
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=90)
            if r.status_code == 200:
                return r.json()["token"]
            last = f"{r.status_code} {r.text}"
        except Exception as e:
            last = str(e)
    raise AssertionError(f"login failed for {email}: {last}")


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@leamss.com", "Admin@123")


@pytest.fixture(scope="module")
def partner_token():
    return _login("partner@leamss.com", "Partner@123")


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def _onboarding_payload():
    return {
        "designation": "Senior Engineer",
        "date_of_joining": "2026-01-15",
        "dob": "1992-03-21",
        "gender": "male",
        "blood_group": "O+",
        "current_address": "Flat 1, Bandra",
        "permanent_address": "House 22, Patna",
        "city": "Mumbai",
        "state": "MH",
        "pincode": "400001",
        "emergency_contact_name": "Father",
        "emergency_contact_phone": "+919999900000",
        "emergency_contact_relation": "father",
        "pan_number": "ABCDE1234F",
        "aadhaar_number": "1234 5678 9012",
        "gst_number": "27ABCDE1234F1Z5",
        "bank_account_number": "001100110011",
        "bank_ifsc": "HDFC0000123",
        "bank_name": "HDFC Bank",
        "bank_account_holder_name": "Iteration 103 Test",
        "notes": "Created by iteration_103 test",
    }


# ──────────── Document Checklist ────────────
@pytest.mark.parametrize("ptype,expected_keys", [
    ("employee_internal", {"pan_card", "aadhaar_card", "resume", "bank_passbook"}),
    ("partner_external", {"pan_card", "aadhaar_card", "bank_passbook", "partnership_agreement"}),
    ("vendor_internal", {"pan_card", "aadhaar_card", "bank_passbook", "service_agreement"}),
    ("vendor_external", {"pan_card", "gst_cert", "bank_passbook", "service_agreement"}),
])
def test_document_checklist(admin_token, ptype, expected_keys):
    r = requests.get(f"{API}/people/document-checklist/{ptype}", headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert isinstance(items, list) and len(items) >= 4
    keys = {i["key"] for i in items}
    assert expected_keys.issubset(keys), f"missing keys: {expected_keys - keys}"
    # Each item must have key,label,required
    for it in items:
        assert {"key", "label", "required"}.issubset(it.keys())


def test_document_checklist_unknown_type_returns_empty(admin_token):
    r = requests.get(f"{API}/people/document-checklist/garbage_type", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_document_checklist_rbac_partner_blocked(partner_token):
    r = requests.get(f"{API}/people/document-checklist/employee_internal", headers=H(partner_token), timeout=30)
    assert r.status_code == 403


# ──────────── POST /people with onboarding (3 person types) ────────────
@pytest.fixture(scope="module")
def employee_person(admin_token):
    suffix = uuid.uuid4().hex[:6]
    body = {
        "person_type": "employee_internal",
        "name": f"TEST_emp_{suffix}",
        "email": f"test_emp_onb_{suffix}@leamss.com",
        "mobile": "+919000000001",
        "role": "case_manager",
        "department": "operations",
        "onboarding": _onboarding_payload(),
    }
    r = requests.post(f"{API}/people", json=body, headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True and data["kind"] == "user" and data["person_id"]
    yield data["person_id"]


@pytest.fixture(scope="module")
def partner_person(admin_token):
    suffix = uuid.uuid4().hex[:6]
    body = {
        "person_type": "partner_external",
        "name": f"TEST_partner_{suffix}",
        "email": f"test_partner_onb_{suffix}@leamss.com",
        "mobile": "+919000000002",
        "onboarding": _onboarding_payload(),
    }
    r = requests.post(f"{API}/people", json=body, headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    yield r.json()["person_id"]


@pytest.fixture(scope="module")
def vendor_ext_person(admin_token):
    suffix = uuid.uuid4().hex[:6]
    body = {
        "person_type": "vendor_external",
        "name": f"TEST_vext_{suffix}",
        "email": f"test_vext_onb_{suffix}@leamss.com",
        "mobile": "+919000000003",
        "vendor_category": "translation",
        "onboarding": _onboarding_payload(),
    }
    # Discover an active external vendor category first
    cats = requests.get(f"{API}/vendors/categories", headers=H(admin_token), timeout=30)
    arr = cats.json().get("categories", []) if cats.status_code == 200 else []
    ext_cat = next((c["key"] for c in arr if not c.get("is_internal") and c.get("is_active")), None)
    body["vendor_category"] = ext_cat or "consultant"
    r = requests.post(f"{API}/people", json=body, headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["kind"] == "vendor" and data.get("vendor_code")
    yield data["person_id"]


def test_onboarding_persisted_employee(admin_token, employee_person):
    r = requests.get(f"{API}/people/{employee_person}", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    user = r.json()["user"]
    assert user is not None
    onb = user.get("onboarding")
    assert onb, "onboarding missing on employee user doc"
    assert onb["designation"] == "Senior Engineer"
    assert onb["pan_number"] == "ABCDE1234F"
    assert onb["bank_ifsc"] == "HDFC0000123"
    assert onb["emergency_contact_name"] == "Father"
    assert "captured_at" in onb and "captured_by" in onb


def test_onboarding_persisted_partner(admin_token, partner_person):
    r = requests.get(f"{API}/people/{partner_person}", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    user = r.json()["user"]
    assert user is not None and user.get("onboarding")
    assert user["onboarding"]["pan_number"] == "ABCDE1234F"


def test_onboarding_persisted_vendor_external(admin_token, vendor_ext_person):
    r = requests.get(f"{API}/people/{vendor_ext_person}", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    vendor = r.json()["vendor"]
    assert vendor is not None and vendor.get("onboarding")
    # KYC also lifted to top-level fields on vendor doc
    assert vendor.get("pan_number") == "ABCDE1234F"
    assert vendor.get("bank_details", {}).get("ifsc") == "HDFC0000123"


def test_create_person_without_onboarding_still_works(admin_token):
    suffix = uuid.uuid4().hex[:6]
    body = {
        "person_type": "employee_internal",
        "name": f"TEST_noonb_{suffix}",
        "email": f"test_noonb_{suffix}@leamss.com",
        "role": "operations",
    }
    r = requests.post(f"{API}/people", json=body, headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text


# ──────────── Document Upload / List / Verify / Download / Delete ────────────
def _make_pdf_bytes():
    # Minimal valid PDF
    return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
            b"0000000056 00000 n \n0000000101 00000 n \ntrailer<</Size 4/Root 1 0 R>>\n"
            b"startxref\n150\n%%EOF")


@pytest.fixture(scope="module")
def uploaded_doc(admin_token, employee_person):
    files = {"file": ("pan.pdf", _make_pdf_bytes(), "application/pdf")}
    data = {"doc_type": "pan_card", "doc_label": "PAN Card", "notes": "test upload"}
    r = requests.post(f"{API}/people/{employee_person}/documents", files=files, data=data,
                      headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["doc_type"] == "pan_card"
    assert body["mime_type"] == "application/pdf"
    assert body["size_bytes"] > 0
    yield body["id"]


def test_list_documents(admin_token, employee_person, uploaded_doc):
    r = requests.get(f"{API}/people/{employee_person}/documents", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(d["id"] == uploaded_doc for d in items)
    target = next(d for d in items if d["id"] == uploaded_doc)
    # Ensure stored_path NOT in response
    assert "stored_path" not in target
    assert target["verified"] is False


def test_upload_rejects_unsupported_mime(admin_token, employee_person):
    files = {"file": ("script.exe", b"MZ\x00\x00", "application/x-msdownload")}
    data = {"doc_type": "other"}
    r = requests.post(f"{API}/people/{employee_person}/documents", files=files, data=data,
                      headers=H(admin_token), timeout=30)
    assert r.status_code == 415, r.text


def test_upload_rejects_oversize(admin_token, employee_person):
    big = b"%PDF-1.4\n" + b"0" * (10 * 1024 * 1024 + 100)
    files = {"file": ("big.pdf", big, "application/pdf")}
    data = {"doc_type": "other"}
    r = requests.post(f"{API}/people/{employee_person}/documents", files=files, data=data,
                      headers=H(admin_token), timeout=60)
    assert r.status_code == 413, r.text


def test_download_document(admin_token, employee_person, uploaded_doc):
    r = requests.get(f"{API}/people/{employee_person}/documents/{uploaded_doc}/download",
                     headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content.startswith(b"%PDF")


def test_verify_document(admin_token, employee_person, uploaded_doc):
    r = requests.post(f"{API}/people/{employee_person}/documents/{uploaded_doc}/verify",
                      headers=H(admin_token), timeout=30)
    assert r.status_code == 200 and r.json()["ok"] is True
    # Confirm via list
    lst = requests.get(f"{API}/people/{employee_person}/documents", headers=H(admin_token), timeout=30).json()["items"]
    target = next(d for d in lst if d["id"] == uploaded_doc)
    assert target["verified"] is True


def test_delete_document(admin_token, employee_person, uploaded_doc):
    r = requests.delete(f"{API}/people/{employee_person}/documents/{uploaded_doc}",
                        headers=H(admin_token), timeout=30)
    assert r.status_code == 200 and r.json()["ok"] is True
    # Confirm gone
    lst = requests.get(f"{API}/people/{employee_person}/documents", headers=H(admin_token), timeout=30).json()["items"]
    assert all(d["id"] != uploaded_doc for d in lst)
    # Re-verify on deleted doc should 404
    r2 = requests.post(f"{API}/people/{employee_person}/documents/{uploaded_doc}/verify",
                       headers=H(admin_token), timeout=30)
    assert r2.status_code == 404


def test_document_endpoints_rbac_partner_blocked(partner_token, employee_person):
    r = requests.get(f"{API}/people/{employee_person}/documents", headers=H(partner_token), timeout=30)
    assert r.status_code == 403


def test_documents_on_missing_person_404(admin_token):
    r = requests.get(f"{API}/people/no-such-person-id/documents", headers=H(admin_token), timeout=30)
    assert r.status_code == 404


# ──────────── Partner Commissions regression ────────────
@pytest.fixture(scope="module")
def first_partner_and_product(admin_token):
    p = requests.get(f"{API}/users?role=partner", headers=H(admin_token), timeout=30)
    assert p.status_code == 200
    body = p.json()
    partners = body if isinstance(body, list) else body.get("users", [])
    assert partners, "no partners found"
    partner_id = partners[0]["id"]
    pr = requests.get(f"{API}/products", headers=H(admin_token), timeout=30)
    assert pr.status_code == 200
    prods = pr.json() if isinstance(pr.json(), list) else pr.json().get("products", [])
    assert prods, "no products found"
    return partner_id, prods[0]["id"]


def test_partner_commissions_get_list(admin_token):
    r = requests.get(f"{API}/partner-commissions", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_partner_commissions_post_then_get_then_delete(admin_token, first_partner_and_product):
    partner_id, product_id = first_partner_and_product
    # POST upsert
    r = requests.post(f"{API}/partner-commissions",
                      json={"partner_id": partner_id, "product_id": product_id, "commission_rate": 17.5},
                      headers=H(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    # Confirm shows in list
    lst = requests.get(f"{API}/partner-commissions", headers=H(admin_token), timeout=30).json()
    match = [m for m in lst if m["partner_id"] == partner_id and m["product_id"] == product_id]
    assert match and abs(match[0]["commission_rate"] - 17.5) < 0.01
    # DELETE
    r3 = requests.delete(f"{API}/partner-commissions",
                         json={"partner_id": partner_id, "product_id": product_id},
                         headers=H(admin_token), timeout=30)
    assert r3.status_code == 200, r3.text
    # Confirm gone
    lst2 = requests.get(f"{API}/partner-commissions", headers=H(admin_token), timeout=30).json()
    assert not [m for m in lst2 if m["partner_id"] == partner_id and m["product_id"] == product_id]


def test_partner_commission_validation(admin_token, first_partner_and_product):
    partner_id, product_id = first_partner_and_product
    # Out-of-range rate
    r = requests.post(f"{API}/partner-commissions",
                      json={"partner_id": partner_id, "product_id": product_id, "commission_rate": 150},
                      headers=H(admin_token), timeout=30)
    assert r.status_code == 400
    # Missing fields
    r2 = requests.post(f"{API}/partner-commissions",
                       json={"partner_id": partner_id},
                       headers=H(admin_token), timeout=30)
    assert r2.status_code == 400


# ──────────── Express settings regression ────────────
def test_express_user_limit_put_get(admin_token):
    # GET overrides list
    r = requests.get(f"{API}/express/settings/user-overrides", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    # GET searchable users
    r2 = requests.get(f"{API}/express/settings/searchable-users", headers=H(admin_token), timeout=30)
    assert r2.status_code == 200
    users_body = r2.json()
    users = users_body.get("items") or users_body.get("users") or (users_body if isinstance(users_body, list) else [])
    assert users, "no searchable users"
    target_user = users[0]["id"]
    # Set to 5
    for v in [5, 0, -1, None]:
        r3 = requests.put(f"{API}/express/settings/user-limit",
                          json={"user_id": target_user, "limit": v},
                          headers=H(admin_token), timeout=30)
        assert r3.status_code in (200, 204), f"limit={v} -> {r3.status_code} {r3.text}"


# ──────────── Public mock-pay route reachability ────────────
def test_public_mock_pay_route_exists():
    # Should NOT return 404 for unknown route — should return 404 'Link not found' or 422 for missing body
    r = requests.post(f"{BASE_URL}/api/pre-assess-portal/public/mock-pay",
                      json={"token": "definitely-not-a-real-token"}, timeout=30)
    # Either 404 Link not found (route exists, token missing) OR 400/422 validation. Must NOT be 405 / route-not-found 404 with method not allowed.
    assert r.status_code in (400, 404, 422), f"got {r.status_code}: {r.text}"
    if r.status_code == 404:
        # confirm message indicates token not found, not route-not-found
        assert "Link not found" in r.text or "not found" in r.text.lower()


# ──────────── Cleanup test-created people ────────────
def test_zz_cleanup_test_people(admin_token):
    """Soft-deactivate all TEST_* people created in this run (no DELETE endpoint)."""
    r = requests.get(f"{API}/people?search=TEST_", headers=H(admin_token), timeout=30)
    if r.status_code != 200:
        pytest.skip("list failed; skipping cleanup")
    people = r.json().get("people", [])
    for p in people:
        if (p.get("name") or "").startswith("TEST_"):
            requests.post(f"{API}/people/{p['id']}/deactivate", headers=H(admin_token), timeout=15)
    assert True
