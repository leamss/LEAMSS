"""Phase 21 Slice 3 Backlog B.1 — Reimbursement bill upload/download tests.

Uses requests (sync) like the rest of test_phase21_slice3.py for consistency.
"""
import io
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


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _make_claim(token: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/reimbursements",
        json={
            "category": "travel",
            "amount_inr": 1200,
            "vendor_name": "Test Vendor",
            "description": "Bill upload test claim",
            "expense_date": "2026-02-20",
            "bills": [],
        },
        headers=_auth(token),
        timeout=20,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_bill_upload_pdf_ok(admin_token):
    claim_id = _make_claim(admin_token)
    pdf_bytes = b"%PDF-1.4\n%demo bill\n"
    r = requests.post(
        f"{BASE_URL}/api/reimbursements/{claim_id}/bill",
        files={"file": ("bill.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=_auth(admin_token),
        timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mime_type"] == "application/pdf"
    assert body["size_bytes"] == len(pdf_bytes)
    assert body["bill_id"]


def test_bill_upload_jpg_ok(admin_token):
    claim_id = _make_claim(admin_token)
    fake_jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 200
    r = requests.post(
        f"{BASE_URL}/api/reimbursements/{claim_id}/bill",
        files={"file": ("bill.jpg", io.BytesIO(fake_jpg), "image/jpeg")},
        headers=_auth(admin_token),
        timeout=20,
    )
    assert r.status_code == 200, r.text
    assert r.json()["mime_type"] == "image/jpeg"


def test_bill_upload_rejects_unsupported_mime(admin_token):
    claim_id = _make_claim(admin_token)
    r = requests.post(
        f"{BASE_URL}/api/reimbursements/{claim_id}/bill",
        files={"file": ("readme.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=_auth(admin_token),
        timeout=20,
    )
    assert r.status_code == 400
    assert "Unsupported" in r.json()["detail"]


def test_bill_upload_rejects_oversize(admin_token):
    claim_id = _make_claim(admin_token)
    big = b"\xff\xd8\xff\xe0" + b"\x00" * (5 * 1024 * 1024 + 100)
    r = requests.post(
        f"{BASE_URL}/api/reimbursements/{claim_id}/bill",
        files={"file": ("big.jpg", io.BytesIO(big), "image/jpeg")},
        headers=_auth(admin_token),
        timeout=30,
    )
    assert r.status_code == 400
    assert "too large" in r.json()["detail"].lower()


def test_bill_download_returns_file(admin_token):
    claim_id = _make_claim(admin_token)
    pdf_bytes = b"%PDF-1.4\n%downloadable\n"
    up = requests.post(
        f"{BASE_URL}/api/reimbursements/{claim_id}/bill",
        files={"file": ("download_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=_auth(admin_token),
        timeout=20,
    )
    bill_id = up.json()["bill_id"]
    dl = requests.get(
        f"{BASE_URL}/api/reimbursements/{claim_id}/bill/{bill_id}",
        headers=_auth(admin_token),
        timeout=20,
    )
    assert dl.status_code == 200
    assert dl.content == pdf_bytes


def test_bill_404_for_unknown_bill_id(admin_token):
    claim_id = _make_claim(admin_token)
    r = requests.get(
        f"{BASE_URL}/api/reimbursements/{claim_id}/bill/unknown-bill-xyz",
        headers=_auth(admin_token),
        timeout=20,
    )
    assert r.status_code == 404


def test_bill_audit_log_records_attachment(admin_token):
    claim_id = _make_claim(admin_token)
    requests.post(
        f"{BASE_URL}/api/reimbursements/{claim_id}/bill",
        files={"file": ("bill.pdf", io.BytesIO(b"%PDF-1.4\nx"), "application/pdf")},
        headers=_auth(admin_token),
        timeout=20,
    )
    trail = requests.get(
        f"{BASE_URL}/api/reimbursements/{claim_id}/audit-trail",
        headers=_auth(admin_token),
        timeout=20,
    )
    assert trail.status_code == 200
    actions = {e["action"] for e in trail.json()}
    assert "bill_attached" in actions
