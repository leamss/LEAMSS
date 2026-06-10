"""Phase 9.6 — Calculator Rules Engine + Bulk State Extract + DAMA/ILA PDF tests."""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://career-match-320.preview.emergentagent.com")
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS, timeout=15)
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ─── Task 1 — Calculator Rules Engine ────────────────────────────────────────
def test_get_rules_returns_au_defaults(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/calculator-rules/AU", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["country"] == "AU"
    assert "tables" in body
    keys = set(body["tables"].keys())
    assert {"age", "english", "education", "partner_skills", "bonuses", "state_nomination"} <= keys


def test_save_and_reload_override(admin_headers):
    # Save custom override
    custom_tables = {
        "english": {"type": "tiered", "rule": "test", "tiers": {"superior": 50}},
    }
    r = requests.put(
        f"{BASE_URL}/api/anz-intel/calculator-rules/AU",
        headers=admin_headers,
        json={"version": "TEST-2026", "tables": custom_tables},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["source"] == "db_override"
    assert r.json()["version"] == "TEST-2026"

    # Reload — must return override
    r2 = requests.get(f"{BASE_URL}/api/anz-intel/calculator-rules/AU", headers=admin_headers, timeout=10)
    assert r2.json()["source"] == "db_override"
    assert r2.json()["tables"]["english"]["tiers"]["superior"] == 50

    # Reset
    r3 = requests.post(f"{BASE_URL}/api/anz-intel/calculator-rules/AU/reset", headers=admin_headers, timeout=10)
    assert r3.json()["source"] == "hardcoded_defaults"

    # Reload — back to defaults
    r4 = requests.get(f"{BASE_URL}/api/anz-intel/calculator-rules/AU", headers=admin_headers, timeout=10)
    assert r4.json()["source"] == "hardcoded_defaults"
    assert r4.json()["tables"]["english"]["tiers"]["superior"] == 20


def test_rules_supports_au_ca_nz(admin_headers):
    for country in ("AU", "CA", "NZ"):
        r = requests.get(f"{BASE_URL}/api/anz-intel/calculator-rules/{country}", headers=admin_headers, timeout=10)
        assert r.status_code == 200, f"{country} failed: {r.text}"
        assert r.json()["country"] == country


def test_rules_rejects_unsupported_country(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/calculator-rules/XX", headers=admin_headers, timeout=10)
    assert r.status_code == 400


def test_rules_rbac_partner_blocked(partner_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/calculator-rules/AU", headers=partner_headers, timeout=10)
    assert r.status_code == 403


# ─── Task 2 — Bulk State Nomination AI Extract ───────────────────────────────
def test_bulk_state_extract_preview_vic(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/ai-extract-state-bulk/preview",
        headers=admin_headers,
        json={
            "state": "VIC",
            "source_url": "https://liveinmelbourne.vic.gov.au/migrate",
            "raw_text": (
                "Victoria Skilled Visa Program 2025-26: Priority occupations include "
                "Software Engineer (ANZSCO 261313), Database Administrator (262111), "
                "Network Engineer (263111), and ICT Security Specialist (262112). "
                "All listed occupations are eligible for Subclass 190 with high demand. "
                "Subclass 491 eligibility also applies."
            ),
        },
        timeout=60,  # AI call
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["state"] == "VIC"
    assert body["total_extracted"] >= 3
    assert body["matched_count"] >= 1
    assert len(body["records"]) >= 1


def test_bulk_state_bad_state_400(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/ai-extract-state-bulk/preview",
        headers=admin_headers,
        json={"state": "INVALID_LONG_NAME", "raw_text": "something"},
        timeout=15,
    )
    assert r.status_code == 400


# ─── Task 3 — DAMA PDF Parser ────────────────────────────────────────────────
def _build_test_dama_pdf() -> bytes:
    """Generate a tiny PDF in-memory containing a few ANZSCO codes for testing."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(50, 800, "NT DAMA Test Occupation List")
    codes = ["141999", "351411", "411111", "411712", "611111"]
    y = 760
    for code in codes:
        c.drawString(50, y, f"ANZSCO {code} — Test Title")
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue()


def test_dama_pdf_preview_extracts_codes(admin_headers):
    pdf_bytes = _build_test_dama_pdf()
    files = {"file": ("test_nt.pdf", pdf_bytes, "application/pdf")}
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/dama-pdf/preview?target_id=nt&target_type=dama",
        headers=admin_headers, files=files, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_id"] == "nt"
    assert body["target_type"] == "dama"
    assert body["total_codes_extracted"] >= 3
    # At least one should match in DB
    assert len(body["matched_in_db"]) >= 1


def test_dama_pdf_commit_updates_records(admin_headers):
    # Use a code we know is in the DB and not verified
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/dama-pdf/commit",
        headers=admin_headers,
        json={"target_id": "nt", "target_type": "dama",
              "codes": ["411111", "411712"], "source": "test_pdf.pdf"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["updated"] >= 0  # may be 0 if already committed
    # Verify record now has NT DAMA
    v = requests.get(f"{BASE_URL}/api/anz-intel/verify/411712", headers=admin_headers, timeout=10)
    assert v.status_code == 200
    damas = v.json().get("dama_eligibility") or []
    dama_ids = {d.get("id") for d in damas}
    assert "nt" in dama_ids, f"NT not in {dama_ids}"


def test_dama_pdf_rejects_invalid_target(admin_headers):
    pdf_bytes = _build_test_dama_pdf()
    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/dama-pdf/preview?target_id=nt&target_type=invalid",
        headers=admin_headers, files=files, timeout=15,
    )
    assert r.status_code == 400


def test_dama_pdf_rbac_partner_blocked(partner_headers):
    pdf_bytes = _build_test_dama_pdf()
    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/dama-pdf/preview?target_id=nt&target_type=dama",
        headers=partner_headers, files=files, timeout=15,
    )
    assert r.status_code == 403
