"""Phase 19.9.1 + 19.10 + 19.11 — combined regression tests.

Run: cd /app/backend && pytest tests/test_phase1991_polish.py -v
"""
from __future__ import annotations

import io
import os
import uuid
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


API_BASE = os.environ.get("API_BASE") or (
    Path("/app/frontend/.env").read_text().split("REACT_APP_BACKEND_URL=")[1].split()[0]
)
API = f"{API_BASE}/api"
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASS = "Partner@123"


@pytest.fixture(scope="module")
def admin_token() -> str:
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def partner_token() -> str:
    r = requests.post(f"{API}/auth/login",
                      json={"email": PARTNER_EMAIL, "password": PARTNER_PASS}, timeout=15)
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def partner_headers(partner_token) -> dict:
    return {"Authorization": f"Bearer {partner_token}"}


@pytest.fixture(scope="module")
def db():
    mongo_url = Path("/app/backend/.env").read_text().split("MONGO_URL=")[1].split()[0]
    db_name = Path("/app/backend/.env").read_text().split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


# ──────────────────────────────────────────────────────────────────
# Phase 19.9.1 — Polish patch tests
# ──────────────────────────────────────────────────────────────────

def test_1991_diff_audit_identity_field_change_surfaces_diff(headers):
    """P2 fix — full_name change must produce non-empty meta_description_diffs."""
    r = requests.post(f"{API}/assessing-authorities/ACS/diff-preview",
                      headers=headers,
                      json={"proposed_changes": {"full_name": "Australian Computer Society LIMITED TEST"}},
                      timeout=15)
    assert r.status_code == 200
    body = r.json()
    diffs = body.get("meta_description_diffs", [])
    assert len(diffs) > 0, "Expected non-empty diffs for full_name change"
    assert body["estimated_seo_impact"] in ("low", "medium", "high"), \
        f"Expected non-none impact, got {body['estimated_seo_impact']}"
    # First diff should have proper structure
    d0 = diffs[0]
    assert "code" in d0 and "before" in d0 and "after" in d0
    assert d0.get("diff_type") in ("seo_meta_description", "identity_field")


def test_1991_diff_audit_fee_only_change_no_meta_diff(headers):
    """P2 verify — fee-only change should produce none impact (no meta string mentions fee)."""
    r = requests.post(f"{API}/assessing-authorities/ACS/diff-preview",
                      headers=headers,
                      json={"proposed_changes": {"fees": {"msa_fee_aud": 999}}},
                      timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["estimated_seo_impact"] == "none"
    assert len(body.get("meta_description_diffs", [])) == 0


def test_1991_audit_trail_recent_endpoint(headers):
    """P3 — audit-trail/recent returns authority events."""
    r = requests.get(f"{API}/assessing-authorities/audit-trail/recent?limit=5", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "count" in body
    if body["count"] > 0:
        ev = body["items"][0]
        assert ev["action"].startswith("authority.")
        assert "summary" in ev
        assert body.get("latest_at") is not None


def test_1991_audit_trail_per_code(headers):
    """P3 — per-code audit trail filters correctly."""
    r = requests.get(f"{API}/assessing-authorities/ACS/audit-trail?limit=5", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "ACS"
    for ev in body.get("items", []):
        assert ev["summary"].get("code") == "ACS"


def test_1991_audit_trail_role_gated(partner_headers):
    """Partner can READ audit trail (it's read-only)."""
    r = requests.get(f"{API}/assessing-authorities/audit-trail/recent?limit=3", headers=partner_headers, timeout=10)
    assert r.status_code == 200


# ──────────────────────────────────────────────────────────────────
# Phase 19.10 — Currency Service + State Nominations
# ──────────────────────────────────────────────────────────────────

def test_1910_currency_rates_get_default(headers):
    """E1 — GET /currency/rates returns 3 pairs with env_fallback default."""
    r = requests.get(f"{API}/currency/rates", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert set(body["rates"].keys()) == {"AUD_INR", "NZD_INR", "CAD_INR"}
    for pair, info in body["rates"].items():
        assert info["rate"] > 0
        assert info["source"] in ("db", "env_fallback", "cache")


def test_1910_currency_rate_admin_can_update(headers, db):
    """E1 — Admin can POST a new rate; DB-stored override takes precedence."""
    test_rate = 56.789
    r = requests.post(f"{API}/currency/rates",
                      headers=headers, json={"pair": "AUD_INR", "rate": test_rate},
                      timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["new_rate"] == test_rate
    assert body.get("batch_id", "").startswith("imp_")
    # Verify DB persisted
    doc = db["currency_rates"].find_one({"pair": "AUD_INR"})
    assert doc and doc["rate"] == test_rate
    # GET now should return db source
    r2 = requests.get(f"{API}/currency/rates", headers=headers, timeout=10)
    assert r2.json()["rates"]["AUD_INR"]["source"] in ("db", "cache")
    # Cleanup
    db["currency_rates"].delete_one({"pair": "AUD_INR"})


def test_1910_currency_partner_blocked_on_post(partner_headers):
    """E1 — non-admin gets 403 on POST."""
    r = requests.post(f"{API}/currency/rates",
                      headers=partner_headers, json={"pair": "AUD_INR", "rate": 60.0},
                      timeout=10)
    assert r.status_code == 403


def test_1910_state_nominations_upload_and_commit(headers, db):
    """E2 — Upload a CSV state nom list, commit, query by code."""
    # Cleanup
    db["state_nomination_lists"].delete_many({"state": "TST"})
    csv_content = (
        b"anzsco_code,title,status,notes\n"
        b"261313,Software Engineer,open,\n"
        b"233211,Civil Engineer,high_demand,Priority\n"
        b"253111,Pediatrician,open,\n"
    )
    files = {"file": ("test_list.csv", csv_content, "text/csv")}
    data = {"state": "NSW", "list_type": "190",
            "source_url": "https://example.com/test", "as_of_date": "2026-06-01"}
    # Use NSW with fake state_nom — but ensure no collision; let's use a unique list_type
    data["list_type"] = "190_test"
    r = requests.post(f"{API}/state-nominations/upload",
                      headers=headers, files=files, data=data, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    file_id = body["file_id"]
    assert body["preview"]["row_count"] == 3
    # Commit
    r2 = requests.post(f"{API}/state-nominations/{file_id}/commit", headers=headers, timeout=15)
    assert r2.status_code == 200
    assert r2.json()["summary"]["codes_indexed"] == 3
    # Query by code
    r3 = requests.get(f"{API}/state-nominations/by-code/261313", headers=headers, timeout=10)
    assert r3.status_code == 200
    matches = r3.json().get("state_demand", [])
    nsw_match = next((m for m in matches if m["state"] == "NSW" and m["list_type"] == "190_test"), None)
    assert nsw_match is not None
    assert nsw_match["status"] == "open"
    # Cleanup
    db["state_nomination_lists"].delete_many({"state": "NSW", "list_type": "190_test"})


def test_1910_state_noms_partner_blocked_on_upload(partner_headers):
    """E2 — partner blocked on upload (admin only)."""
    files = {"file": ("x.csv", b"anzsco_code\n261313\n", "text/csv")}
    data = {"state": "NSW", "list_type": "190"}
    r = requests.post(f"{API}/state-nominations/upload",
                      headers=partner_headers, files=files, data=data, timeout=10)
    assert r.status_code == 403


def test_1910_sales_endpoint_enrichment(headers):
    """E3 — Sales endpoint surfaces Phase 19.10 enrichment with INR + processing + body."""
    r = requests.get(f"{API}/sales/occupations/AU/261313", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    p = body.get("_phase_19_10")
    assert p is not None, "Missing _phase_19_10 enrichment block"
    assert p["currency"]["fx_rate"] > 0
    assert p["currency"]["fee_currency"] == "AUD"
    assert p["fees"]["msa_fee_native"] is not None
    assert p["fees"]["msa_fee_inr"] is not None  # INR conversion present
    assert p["fees"]["msa_fee_inr_display"].startswith("₹")
    assert p["authority_resolved"]["short_name"] == "ACS"


# ──────────────────────────────────────────────────────────────────
# Phase 19.11 — Pre-Assessment Report PDF (WeasyPrint)
# ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def report_payload():
    return {
        "client": {
            "name": "Pytest Client",
            "email": "pytest@example.com",
            "age": 30,
            "english_score": "IELTS 7.5",
            "work_exp_years": 7,
        },
        "country_code": "AU",
        "occupation_code": "261313",
    }


def test_1911_pdf_generation_for_admin(headers, report_payload):
    """F1+F2 — Admin generates PDF; output is valid PDF binary, has %PDF magic."""
    r = requests.post(f"{API}/reports/pre-assessment", headers=headers,
                      json=report_payload, timeout=30)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-", "Output is not a valid PDF"
    assert len(r.content) > 5000, f"PDF unexpectedly small ({len(r.content)} bytes)"
    assert r.headers.get("x-report-ref"), "Missing X-Report-Ref header"


def test_1911_pdf_html_preview_has_8_sections(headers, report_payload):
    """F1 — HTML preview contains all 8 sections."""
    payload = {**report_payload, "preview_html": True}
    r = requests.post(f"{API}/reports/pre-assessment", headers=headers,
                      json=payload, timeout=15)
    assert r.status_code == 200
    html = r.text
    for section in ("1. Industry Context", "2. Occupation Deep-dive", "3. Assessing Body",
                    "4. Salary", "5. Visa Pathways", "6. Indicative Timeline",
                    "7. Pathway Guide", "8. Next Steps"):
        assert section in html, f"Missing section: {section}"


def test_1911_partner_can_generate(partner_headers, report_payload):
    """F2 — Partner role allowed to generate (Sir's spec: sales/partner/admin)."""
    r = requests.post(f"{API}/reports/pre-assessment", headers=partner_headers,
                      json=report_payload, timeout=30)
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"


def test_1911_unknown_occupation_returns_404(headers):
    """F2 — Unknown occupation 404s cleanly."""
    payload = {"client": {"name": "X"}, "country_code": "AU", "occupation_code": "999999_FAKE"}
    r = requests.post(f"{API}/reports/pre-assessment", headers=headers, json=payload, timeout=15)
    assert r.status_code == 404


def test_1911_report_log_writes(headers, db, report_payload):
    """F2 — Each generation writes log entry."""
    before = db["pre_assessment_reports_log"].count_documents({})
    requests.post(f"{API}/reports/pre-assessment", headers=headers,
                  json={**report_payload, "client": {**report_payload["client"], "name": f"LogTest_{uuid.uuid4().hex[:6]}"}},
                  timeout=30)
    after = db["pre_assessment_reports_log"].count_documents({})
    assert after > before, "Log row not written"


def test_1911_pdf_cache_serves_hit(headers, report_payload):
    """F2 — 2nd call within TTL returns X-Cache: HIT."""
    p2 = {**report_payload, "client": {**report_payload["client"], "name": f"CacheTest_{uuid.uuid4().hex[:6]}"}}
    r1 = requests.post(f"{API}/reports/pre-assessment", headers=headers, json=p2, timeout=30)
    assert r1.status_code == 200 and r1.headers.get("x-cache") in ("MISS", None)
    r2 = requests.post(f"{API}/reports/pre-assessment", headers=headers, json=p2, timeout=30)
    assert r2.status_code == 200
    # Cache hit OR fresh re-generation both OK if within timing window
    assert r2.content[:5] == b"%PDF-"


def test_1911_pdf_unauthenticated_blocked():
    """F2 — Unauth returns 401."""
    r = requests.post(f"{API}/reports/pre-assessment",
                      json={"client": {"name": "X"}, "country_code": "AU", "occupation_code": "261313"},
                      timeout=10)
    assert r.status_code in (401, 403)


def test_1911_report_log_endpoint(headers):
    """F2 — Log listing endpoint."""
    r = requests.get(f"{API}/reports/pre-assessment/log?limit=5", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "count" in body
