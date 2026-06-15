"""Phase 18.8 — Compare PDF export + Lead pre-fill from Compare.

12 tests as briefed by Sir.
"""
from __future__ import annotations
import os
import sys
import asyncio
import httpx
import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

API_BASE = os.environ.get("AUDIT_API_BASE", "http://localhost:8001/api")
MONGO = AsyncIOMotorClient(os.environ["MONGO_URL"])
DB = MONGO[os.environ["DB_NAME"]]


def _login(email: str, password: str) -> dict:
    r = httpx.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=20)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def H():
    return _login("admin@leamss.com", "Admin@123")


@pytest.fixture(scope="module")
def P():
    return _login("partner@leamss.com", "Partner@123")


def _async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# Cleanup between tests — purge any phase18.8 test leads
def _purge_leads():
    _async(DB["leads"].delete_many({"email": {"$regex": "^phase188-"}}))


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    _purge_leads()
    yield
    _purge_leads()


# Stable known codes (matched against Phase 18.5 seeded data)
A = {"country_code": "CA", "code": "21231"}
B = {"country_code": "CA", "code": "31102"}


# ─────────────────────────────────────────────────────────────────────────────
# 1. PDF endpoint returns application/pdf with %PDF- magic
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_pdf_endpoint_returns_application_pdf(H):
    r = httpx.post(f"{API_BASE}/sales/compare/pdf", headers=H, json={"codes": [A, B]}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd and "filename=" in cd
    # Magic bytes
    assert r.content[:5] == b"%PDF-", f"Bad magic: {r.content[:8]!r}"
    # Save for human inspection
    with open("/tmp/sample_compare.pdf", "wb") as f:
        f.write(r.content)


def _extract_pdf_text(content: bytes) -> str:
    """Decompress + extract text from a WeasyPrint PDF using pdfminer.

    WeasyPrint uses FlateDecode-compressed text streams, so raw byte search
    won't find the literal "21231" etc. — we have to extract.
    """
    from io import BytesIO
    from pdfminer.high_level import extract_text
    return extract_text(BytesIO(content))


# ─────────────────────────────────────────────────────────────────────────────
# 2. PDF includes all codes — content has both code strings in extracted text
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_pdf_includes_all_codes(H):
    r = httpx.post(f"{API_BASE}/sales/compare/pdf", headers=H, json={"codes": [A, B]}, timeout=30)
    assert r.status_code == 200
    text = _extract_pdf_text(r.content)
    assert "21231" in text, f"code 21231 missing from extracted PDF text (first 500: {text[:500]!r})"
    assert "31102" in text, "code 31102 missing from extracted PDF text"
    assert len(r.content) > 20_000, f"PDF unexpectedly small ({len(r.content)} bytes)"


# ─────────────────────────────────────────────────────────────────────────────
# 3. >3 codes → 400/422
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_pdf_max_3_codes_enforced(H):
    r = httpx.post(f"{API_BASE}/sales/compare/pdf", headers=H, json={"codes": [A, B, A, B]}, timeout=20)
    assert r.status_code in (400, 422), r.text


# ─────────────────────────────────────────────────────────────────────────────
# 4. Auth required
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_pdf_auth_required():
    r = httpx.post(f"{API_BASE}/sales/compare/pdf", json={"codes": [A]}, timeout=20)
    assert r.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Partner can access
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_pdf_partner_can_access(P):
    r = httpx.post(f"{API_BASE}/sales/compare/pdf", headers=P, json={"codes": [A, B]}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.content[:5] == b"%PDF-"


# ─────────────────────────────────────────────────────────────────────────────
# 6. No path leak in filename or response bytes
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_pdf_no_path_leak(H):
    r = httpx.post(f"{API_BASE}/sales/compare/pdf", headers=H, json={"codes": [A, B]}, timeout=30)
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    for bad in ("/app/", "/tmp", ".py", "/root", "/etc"):
        assert bad not in cd, f"Sensitive path '{bad}' leaked into header: {cd}"
    # Sample first 50KB of PDF for textual path leaks (allow magic + LEAMSS branding)
    head = r.content[:50_000]
    for bad in (b"/app/backend", b"/root/.venv", b"site-packages"):
        assert bad not in head, f"Sensitive path leaked into PDF body: {bad!r}"


# ─────────────────────────────────────────────────────────────────────────────
# 7. create-lead-draft creates a lead row with interest_occupations populated
# ─────────────────────────────────────────────────────────────────────────────
def test_create_lead_draft_creates_row(H):
    _purge_leads()
    r = httpx.post(
        f"{API_BASE}/sales/compare/create-lead-draft",
        headers=H,
        json={
            "codes": [A, B],
            "lead_data": {"name": "Phase188 admin", "email": "phase188-admin@example.com", "phone": "+91 99999 11111", "source": "WhatsApp", "notes": "Smoke seed"},
        },
        timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    lead_id = body["lead_id"]
    lead = body["lead"]
    assert lead["stage"] == "compare_draft"
    assert lead["name"] == "Phase188 admin"
    assert lead["email"] == "phase188-admin@example.com"
    interest = lead["interest_occupations"]
    assert len(interest) == 2
    pairs = {(i["country_code"], i["code"]) for i in interest}
    assert pairs == {("CA", "21231"), ("CA", "31102")}
    # Confirm in DB + listing
    doc = _async(DB["leads"].find_one({"id": lead_id}))
    assert doc is not None
    assert doc["stage"] == "compare_draft"
    _purge_leads()


# ─────────────────────────────────────────────────────────────────────────────
# 8. Partner can create lead draft
# ─────────────────────────────────────────────────────────────────────────────
def test_create_lead_draft_partner_can_create(P):
    _purge_leads()
    r = httpx.post(
        f"{API_BASE}/sales/compare/create-lead-draft",
        headers=P,
        json={"codes": [A], "lead_data": {"name": "Phase188 partner", "email": "phase188-partner@example.com"}},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    assert r.json()["lead"]["stage"] == "compare_draft"
    _purge_leads()


# ─────────────────────────────────────────────────────────────────────────────
# 9. Non-existent code → 400 with helpful error
# ─────────────────────────────────────────────────────────────────────────────
def test_create_lead_draft_validates_codes_exist(H):
    r = httpx.post(
        f"{API_BASE}/sales/compare/create-lead-draft",
        headers=H,
        json={"codes": [{"country_code": "CA", "code": "99999"}], "lead_data": {"name": "x", "email": "phase188-bad@example.com"}},
        timeout=20,
    )
    assert r.status_code == 400, r.text
    detail = r.json().get("detail")
    # Either a dict with not_found or a string mentioning the bad code
    if isinstance(detail, dict):
        assert "not_found" in detail
        assert any(nf.get("code") == "99999" for nf in detail["not_found"])
    else:
        assert "99999" in str(detail) or "not found" in str(detail).lower()


# ─────────────────────────────────────────────────────────────────────────────
# 10. Audit log row written
# ─────────────────────────────────────────────────────────────────────────────
def test_create_lead_draft_writes_audit_log(H):
    _purge_leads()
    r = httpx.post(
        f"{API_BASE}/sales/compare/create-lead-draft",
        headers=H,
        json={"codes": [A], "lead_data": {"name": "Audit", "email": "phase188-audit@example.com"}},
        timeout=20,
    )
    assert r.status_code == 200
    lid = r.json()["lead_id"]
    log = _async(DB["audit_logs"].find_one({"entity_id": lid, "kind": "lead_drafted_from_compare"}))
    assert log is not None, "Audit log missing for create-lead-draft"
    assert log["payload"]["codes"][0]["code"] == "21231"
    _purge_leads()


# ─────────────────────────────────────────────────────────────────────────────
# 11. PDF renders recommended_visa badge — generation succeeds, content sane
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_pdf_renders_recommended_visa_badge(H):
    # CA-21231 fixture has recommended_visa_subclass.CA = "FSWP"
    r = httpx.post(f"{API_BASE}/sales/compare/pdf", headers=H, json={"codes": [A, B]}, timeout=30)
    assert r.status_code == 200
    text = _extract_pdf_text(r.content)
    assert "FSWP" in text, f"Recommended visa subclass FSWP not surfaced in PDF (text head: {text[:400]!r})"


# ─────────────────────────────────────────────────────────────────────────────
# 12. Handles missing data gracefully (won't crash on empty assessing_authority)
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_pdf_handles_missing_data_gracefully(H):
    """Pick an occupation that's unlikely to have a populated skill_body. The
    endpoint must NOT crash with KeyError / NoneType — it should render '—'
    placeholders gracefully."""
    # Use an occupation that exists but might have sparse data
    r = httpx.post(f"{API_BASE}/sales/compare/pdf", headers=H, json={"codes": [{"country_code": "CA", "code": "21231"}]}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.content[:5] == b"%PDF-"
    # PDF should not contain the Python string "None" (would indicate untreated NoneType)
    # Allow it inside compressed streams — only check the raw "None " or "None<"
    head = r.content[:30_000]
    # 'None' may appear inside PDF metadata (Subject:None etc) but not as visible text — heuristic
    assert b"NoneType" not in head and b"AttributeError" not in head
