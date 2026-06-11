"""Phase 18.1 — Verification Workspace expansion test suite.

Covers:
  • Phase 18.0 idempotent probe-pollution cleanup + au-111111 restored.
  • Phase 18.1 new editable fields persist via PUT and /verify.
  • /verify snapshots history + writes audit log + accepts full payload.
  • /copy-from-ai bulk-copies ai_draft into top-level fields.
  • Sample Cases + Custom Sections sub-CRUD with UUIDs.
  • Legacy /verify (source_reference + review_notes only) still works.
"""
from __future__ import annotations
import os, sys, asyncio
import httpx, pytest
from dotenv import load_dotenv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

API_BASE = os.environ.get("AUDIT_API_BASE", "http://localhost:8001/api")
_db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

# Use a CA record for most mutation tests to keep AU 111111 stable for test_13.
TEST_OID = "ca-21231"


def _login():
    r = httpx.post(f"{API_BASE}/auth/login",
                   json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def H():
    return _login()


def _async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — qualification_rules persists via PUT and survives /verify
# ─────────────────────────────────────────────────────────────────────────────
def test_1_qualification_rules_persisted_via_put_and_verify(H):
    rule_text = "Phase 18.1 — Bachelor's degree in software engineering or related field."
    r = httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
                  json={"qualification_rules": rule_text}, timeout=15)
    assert r.status_code == 200, r.text[:200]
    assert r.json().get("qualification_rules") == rule_text

    # Verify it survives /verify
    r2 = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/verify", headers=H,
                    json={"source_reference": "https://statcan.gc.ca/noc-21231",
                          "review_notes": "qualification rule check"}, timeout=15)
    assert r2.status_code == 200, r2.text[:200]
    body = r2.json()
    assert body["status"] == "verified"
    assert body.get("qualification_rules") == rule_text


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — /verify snapshots previous state into verification_history
# ─────────────────────────────────────────────────────────────────────────────
def test_2_verify_snapshots_to_history(H):
    # First verify — pin a description marker
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"description": "PHASE_18_HISTORY_VERSION_X"}, timeout=10)
    r1 = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/verify", headers=H,
                    json={"source_reference": "https://example.com/verify-x"}, timeout=10)
    assert r1.status_code == 200
    history_after_first = r1.json().get("verification_history") or []
    initial_len = len(history_after_first)

    # Second verify — change description, snapshot should preserve VERSION_X
    r2 = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/verify", headers=H,
                    json={"source_reference": "https://example.com/verify-y",
                          "description": "PHASE_18_HISTORY_VERSION_Y"}, timeout=10)
    assert r2.status_code == 200
    body = r2.json()
    assert body["description"] == "PHASE_18_HISTORY_VERSION_Y"
    history = body.get("verification_history") or []
    assert len(history) == initial_len + 1
    # The most-recent entry's snapshot should hold the BEFORE state (VERSION_X)
    latest_snapshot = history[-1].get("snapshot") or {}
    assert latest_snapshot.get("description") == "PHASE_18_HISTORY_VERSION_X"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — full assessing_authority object persists
# ─────────────────────────────────────────────────────────────────────────────
def test_3_assessing_authority_full_object_persisted(H):
    aa = {
        "name": "ACS", "full_name": "Australian Computer Society",
        "url": "https://acs.org.au", "processing_time_weeks": 8,
        "fee_native": 530.0, "fee_currency": "AUD",
        "contact_details": "members@acs.org.au",
        "rules_summary": "AQF Major in computing required.",
    }
    r = httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
                  json={"assessing_authority": aa}, timeout=10)
    assert r.status_code == 200
    got = r.json().get("assessing_authority") or {}
    for k, v in aa.items():
        assert got.get(k) == v, f"assessing_authority.{k} mismatch: {got.get(k)} != {v}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — required_documents replacement semantics
# ─────────────────────────────────────────────────────────────────────────────
def test_4_required_documents_crud(H):
    # PUT with 17 documents (16 baseline + 1 extra)
    docs17 = [{"name": f"Doc {i}", "category": "Other", "required": True,
               "country_override": None} for i in range(17)]
    r = httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
                  json={"required_documents": docs17}, timeout=10)
    assert r.status_code == 200
    got = r.json().get("required_documents") or []
    assert len(got) == 17
    # Each item must have a backend-stamped UUID
    assert all(item.get("id") for item in got)

    # PUT with 5 → replacement, NOT merge
    docs5 = [{"name": f"Doc {i}", "category": "Identity", "required": False,
              "country_override": "AU"} for i in range(5)]
    r2 = httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
                   json={"required_documents": docs5}, timeout=10)
    assert r2.status_code == 200
    got2 = r2.json().get("required_documents") or []
    assert len(got2) == 5, f"Expected replacement to 5 docs, got {len(got2)}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — similar_codes_override persists (Phase 18.3 will wire into Sales)
# ─────────────────────────────────────────────────────────────────────────────
def test_5_similar_codes_override_persists(H):
    override = ["au-261313", "au-261311"]
    r = httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
                  json={"similar_codes_override": override}, timeout=10)
    assert r.status_code == 200
    got = r.json().get("similar_codes_override") or []
    assert got == override


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 — recommended_visa_subclass MERGE semantics per-country
# ─────────────────────────────────────────────────────────────────────────────
def test_6_recommended_visa_per_country_merges(H):
    # Reset to clean state by setting AU first
    r1 = httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
                   json={"recommended_visa_subclass": {"AU": "189"}}, timeout=10)
    assert r1.status_code == 200
    rvs1 = r1.json().get("recommended_visa_subclass") or {}
    assert rvs1.get("AU") == "189"

    # Now PUT with NZ key only — AU must survive (merge, not replace)
    r2 = httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
                   json={"recommended_visa_subclass": {"NZ": "SMC"}}, timeout=10)
    assert r2.status_code == 200
    rvs2 = r2.json().get("recommended_visa_subclass") or {}
    assert rvs2.get("AU") == "189", f"AU key lost during NZ merge: {rvs2}"
    assert rvs2.get("NZ") == "SMC"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7 — sample_cases sub-CRUD with backend-assigned UUIDs
# ─────────────────────────────────────────────────────────────────────────────
def test_7_sample_cases_crud_with_uuids(H):
    # POST — backend assigns UUID
    payload = {"client_age": 32, "profile_summary": "ACS-cleared SW eng",
               "visa_subclass": "189", "outcome": "Approved",
               "timeline_months": 14, "notes": "Phase 18.1 test case"}
    r = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases",
                   headers=H, json=payload, timeout=10)
    assert r.status_code == 200, r.text[:200]
    case = r.json().get("sample_case") or {}
    case_id = case.get("id")
    assert case_id, "POST sample case must return assigned UUID"

    # PATCH same case by UUID
    r2 = httpx.patch(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases/{case_id}",
                     headers=H, json={"timeline_months": 18, "notes": "updated"}, timeout=10)
    assert r2.status_code == 200, r2.text[:200]
    updated = r2.json().get("sample_case") or {}
    assert updated.get("timeline_months") == 18
    assert updated.get("notes") == "updated"
    assert updated.get("id") == case_id

    # DELETE by UUID
    r3 = httpx.delete(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases/{case_id}",
                      headers=H, timeout=10)
    assert r3.status_code == 200
    # Confirm gone
    r4 = httpx.get(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H, timeout=10)
    cases = r4.json().get("sample_cases") or []
    assert all(c.get("id") != case_id for c in cases)


# ─────────────────────────────────────────────────────────────────────────────
# Test 8 — custom_sections sub-CRUD (same pattern)
# ─────────────────────────────────────────────────────────────────────────────
def test_8_custom_sections_crud(H):
    r = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/custom-sections",
                   headers=H, json={"title": "Important", "body_markdown": "## Note",
                                    "source_url": "https://example.com"}, timeout=10)
    assert r.status_code == 200, r.text[:200]
    sec = r.json().get("custom_section") or {}
    sid = sec.get("id")
    assert sid

    r2 = httpx.patch(f"{API_BASE}/occupation-master/{TEST_OID}/custom-sections/{sid}",
                     headers=H, json={"title": "Updated Title"}, timeout=10)
    assert r2.status_code == 200
    assert r2.json().get("custom_section", {}).get("title") == "Updated Title"

    r3 = httpx.delete(f"{API_BASE}/occupation-master/{TEST_OID}/custom-sections/{sid}",
                      headers=H, timeout=10)
    assert r3.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Test 9 — /verify full payload persists ALL fields + snapshot
# ─────────────────────────────────────────────────────────────────────────────
def test_9_verify_endpoint_full_payload_persists_all_fields(H):
    payload = {
        "source_reference": "https://example.com/full-payload",
        "review_notes": "Phase 18.1 full payload",
        "title": "Software engineers and designers (full payload test)",
        "description": "Full payload description test.",
        "typical_tasks": ["Task A", "Task B"],
        "qualification_rules": "Bachelor's degree minimum.",
        "alternative_titles": ["software dev", "backend dev"],
        "assessing_authority": {"name": "ACS", "url": "https://acs.org.au"},
        "required_documents": [{"name": "Resume", "category": "Professional", "required": True}],
        "similar_codes_override": ["ca-21232"],
        "recommended_visa_subclass": {"CA": "FSWP"},
        "sample_cases": [{"client_age": 30, "outcome": "Granted"}],
        "custom_sections": [{"title": "Special note", "body_markdown": "Body"}],
    }
    r = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/verify",
                   headers=H, json=payload, timeout=15)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body["status"] == "verified"
    assert body["title"] == payload["title"]
    assert body["description"] == payload["description"]
    assert body["typical_tasks"] == payload["typical_tasks"]
    assert body["qualification_rules"] == payload["qualification_rules"]
    assert body["alternative_titles"] == payload["alternative_titles"]
    assert (body.get("assessing_authority") or {}).get("name") == "ACS"
    assert len(body.get("required_documents") or []) == 1
    assert body.get("similar_codes_override") == ["ca-21232"]
    assert (body.get("recommended_visa_subclass") or {}).get("CA") == "FSWP"
    assert len(body.get("sample_cases") or []) >= 1
    assert len(body.get("custom_sections") or []) >= 1
    # History snapshot exists
    history = body.get("verification_history") or []
    assert len(history) >= 1
    assert history[-1].get("source_reference") == payload["source_reference"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 10 — /copy-from-ai endpoint copies ai_draft → top-level
# ─────────────────────────────────────────────────────────────────────────────
def test_10_copy_from_ai_endpoint_works(H):
    # Seed an ai_draft directly via DB so we don't depend on the LLM call
    async def _seed():
        await _db["occupation_master"].update_one(
            {"occupation_id": TEST_OID},
            {"$set": {"ai_draft": {
                "description": "AI desc",
                "typical_tasks": ["AI t1", "AI t2"],
                "qualification_rules": "AI qual rules.",
                "generated_at": "2026-06-11T00:00:00Z",
                "generated_by_model": "claude-sonnet-4-6",
            }}},
        )
    _async(_seed())
    r = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/copy-from-ai",
                   headers=H, timeout=10)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body.get("description") == "AI desc"
    assert body.get("typical_tasks") == ["AI t1", "AI t2"]
    assert body.get("qualification_rules") == "AI qual rules."


# ─────────────────────────────────────────────────────────────────────────────
# Test 11 — Legacy /verify payload still works (back-compat)
# ─────────────────────────────────────────────────────────────────────────────
def test_11_legacy_verify_payload_still_works(H):
    # Set known state
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"description": "PRE_LEGACY_VERIFY"}, timeout=10)
    r = httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/verify",
                   headers=H, json={"source_reference": "https://example.com/legacy",
                                    "review_notes": "legacy back-compat"}, timeout=10)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body["status"] == "verified"
    # Description must NOT have been overwritten (no body field sent)
    assert body["description"] == "PRE_LEGACY_VERIFY"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12 — Phase 18.0 cleanup migration is idempotent
# ─────────────────────────────────────────────────────────────────────────────
def test_12_phase180_cleanup_idempotent():
    from migrations.phase180_cleanup_probe_pollution import run_cleanup_probe_pollution
    r1 = _async(run_cleanup_probe_pollution(_db))
    r2 = _async(run_cleanup_probe_pollution(_db))
    # Second run must report zero new cleanings (system is already clean)
    assert r2.get("cleaned") == 0, f"Second run reported {r2.get('cleaned')} cleanings, expected 0"
    assert r1.get("status") == r2.get("status") == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Test 13 — AU 111111 restored after Phase 18.0 startup cleanup
# ─────────────────────────────────────────────────────────────────────────────
def test_13_phase180_au_111111_restored():
    doc = _async(_db["occupation_master"].find_one({"occupation_id": "au-111111"}, {"_id": 0}))
    assert doc is not None
    desc = doc.get("description") or ""
    assert not desc.lower().startswith("tester probe"), \
        f"au-111111 description still polluted: {desc[:80]}"
    tasks = doc.get("typical_tasks") or []
    assert len(tasks) >= 8, f"au-111111 typical_tasks too few ({len(tasks)}) — restore failed"
    assert not any((t or "").lower().startswith("probe task") for t in tasks), \
        f"au-111111 still has probe-task entries: {tasks[:3]}"



# ─────────────────────────────────────────────────────────────────────────────
# Patch 18.0.1 — additional cleanup-regex coverage tests
# ─────────────────────────────────────────────────────────────────────────────
import re as _re

_PHASE_MARKER_RE = _re.compile(r"^Phase\s+\d+(\.\d+)*\b", _re.IGNORECASE)


def test_14_phase17_marker_description_cleaned():
    """No record may have a top-level `description` starting with
    ``Phase X(.Y…)?`` placeholder strings after Patch 18.0.1 ran."""
    async def _scan():
        coll = _db["occupation_master"]
        hits = []
        async for d in coll.find({}, {"_id": 0, "occupation_id": 1, "description": 1}):
            desc = (d.get("description") or "").strip()
            if _PHASE_MARKER_RE.match(desc):
                hits.append((d.get("occupation_id"), desc[:80]))
        return hits
    leftover = _async(_scan())
    assert not leftover, f"{len(leftover)} records still hold a Phase-marker description: {leftover[:3]}"


def test_15_au_111111_description_real():
    """au-111111.description is the real ACS-grade content (>=500 chars,
    mentions ``Chief Executive`` or ``executive leadership``)."""
    doc = _async(_db["occupation_master"].find_one({"occupation_id": "au-111111"}, {"_id": 0}))
    assert doc is not None
    desc = doc.get("description") or ""
    assert len(desc) >= 500, f"au-111111 description too short ({len(desc)} chars) — restore failed"
    haystack = desc.lower()
    assert ("chief executive" in haystack) or ("executive leadership" in haystack), \
        f"au-111111 description missing expected ACS-grade phrasing: {desc[:200]!r}"


def test_16_au_111111_qualification_rules_populated():
    """au-111111.qualification_rules carries substantive content (>=100 chars)
    after Patch 18.0.1 promoted the AI baseline into the top-level field."""
    doc = _async(_db["occupation_master"].find_one({"occupation_id": "au-111111"}, {"_id": 0}))
    assert doc is not None
    qual = (doc.get("qualification_rules") or "").strip()
    assert len(qual) >= 100, f"au-111111 qualification_rules too short ({len(qual)} chars): {qual[:120]!r}"
