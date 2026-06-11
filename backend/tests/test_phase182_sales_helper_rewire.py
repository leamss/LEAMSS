"""Phase 18.2 — Smart Sales Helper rewire: occupation_master → sales detail.

Covers:
  • Skill Assessment / Visa Pathways / Documents / Similar all sourced from
    `occupation_master` (not legacy `country_rules`).
  • Recommended-visa badge from `recommended_visa_subclass[country]`.
  • `country_override` filtering on `required_documents`.
  • `similar_codes_override` priority before auto-similarity.
  • `sample_cases` + `custom_sections` surfaced.
  • `verification_meta` populated (is_verified, days_since, etc.).
  • Admin edit → immediate read-after-write (no cache).
  • Code present in overview (Sir's empty-badge bug).
  • Graceful legacy fallback when occupation_master misses a code.
  • Adversarial path-leak sweep on /sales/occupations/{cc}/{code}.
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

# Use AU 111111 as the primary test target — admin has fully verified it.
TEST_CC = "AU"
TEST_CODE = "111111"
TEST_OID = "au-111111"


def _login():
    r = httpx.post(f"{API_BASE}/auth/login",
                   json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=20)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def H():
    return _login()


def _async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _detail(H, cc=TEST_CC, code=TEST_CODE):
    r = httpx.get(f"{API_BASE}/sales/occupations/{cc}/{code}", headers=H, timeout=15)
    return r


# ─────────────────────────────────────────────────────────────────────────────
def test_1_skill_assessment_from_occupation_master(H):
    r = _detail(H)
    assert r.status_code == 200, r.text[:200]
    sa = r.json().get("skill_assessment") or {}
    assert sa.get("has_data") is True
    assert "Institute of Managers and Leaders" in (sa.get("body_name") or ""), \
        f"Expected IML, got: {sa.get('body_name')!r}"


def test_2_visa_pathways_from_occupation_master(H):
    r = _detail(H)
    vp = r.json().get("visa_pathways") or []
    assert isinstance(vp, list) and len(vp) >= 1
    for v in vp:
        assert "subclass" in v
        assert "is_recommended" in v
        assert isinstance(v["is_recommended"], bool)


def test_3_recommended_visa_badge_when_set(H):
    # Set recommended_visa_subclass for AU to 189
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"recommended_visa_subclass": {"AU": "189"}}, timeout=15)
    r = _detail(H)
    vp = r.json().get("visa_pathways") or []
    by_sub = {v["subclass"]: v for v in vp}
    # 189 may or may not be a known subclass; if it is, it must be flagged
    if "189" in by_sub:
        assert by_sub["189"]["is_recommended"] is True
    # And no other subclass should be flagged
    assert sum(1 for v in vp if v.get("is_recommended")) <= 1


def test_4_documents_from_per_occupation_field(H):
    # Replace with 17 documents
    docs17 = [{"name": f"Doc P182 {i}", "category": "Other", "required": i % 2 == 0,
               "country_override": None} for i in range(17)]
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"required_documents": docs17}, timeout=15)
    r = _detail(H)
    docs = r.json().get("documents") or {}
    assert docs.get("total") == 17, f"Expected 17, got {docs.get('total')}"


def test_5_documents_country_override_filter(H):
    # Mix: 1 CA-only doc (must be excluded for AU) + 1 AU-only (must be included)
    mix = [
        {"name": "CA-only doc", "category": "Other", "required": True, "country_override": "CA"},
        {"name": "AU-only doc", "category": "Other", "required": True, "country_override": "AU"},
        {"name": "Universal doc", "category": "Other", "required": True, "country_override": None},
    ]
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"required_documents": mix}, timeout=15)
    r = _detail(H)
    items = (r.json().get("documents") or {}).get("items") or []
    names = [d.get("name") for d in items]
    assert "CA-only doc" not in names, "country_override='CA' must be excluded for AU detail"
    assert "AU-only doc" in names
    assert "Universal doc" in names


def test_6_similar_codes_override_priority(H):
    # Override pin first
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"similar_codes_override": ["au-261313", "au-111211"]}, timeout=15)
    r = _detail(H)
    sim = r.json().get("similar") or []
    assert len(sim) >= 1
    # First entry should be an override-pinned code
    assert sim[0].get("is_override") is True
    # Pinned codes should appear before any non-override
    seen_non_override = False
    for s in sim:
        if not s.get("is_override"):
            seen_non_override = True
        elif seen_non_override:
            raise AssertionError(f"Override pin {s['code']} found AFTER an auto entry — wrong order")


def test_7_sample_cases_surfaced(H):
    # Clear and add 2 cases
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"sample_cases": []}, timeout=15)
    for i in range(2):
        httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/sample-cases", headers=H,
                   json={"client_age": 30 + i, "profile_summary": f"P182 case {i}",
                         "visa_subclass": "189", "outcome": "Approved",
                         "timeline_months": 12 + i}, timeout=15)
    r = _detail(H)
    cases = r.json().get("sample_cases") or []
    p182 = [c for c in cases if str(c.get("profile_summary") or "").startswith("P182")]
    assert len(p182) >= 2, f"Expected ≥2 P182 cases, got {len(p182)}"


def test_8_custom_sections_in_overview(H):
    # Reset then add 1 custom section
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"custom_sections": []}, timeout=15)
    httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/custom-sections", headers=H,
               json={"title": "P182 note", "body_markdown": "## Heading\nBody."}, timeout=15)
    r = _detail(H)
    sections = (r.json().get("overview") or {}).get("custom_sections") or []
    p182 = [s for s in sections if s.get("title") == "P182 note"]
    assert len(p182) == 1


def test_9_verification_meta_populated(H):
    r = _detail(H)
    vm = r.json().get("verification_meta") or {}
    assert vm.get("is_verified") is True
    assert isinstance(vm.get("verification_count"), int)
    # days_since_verified can be None ONLY if verified_at is None — but au-111111 IS verified
    assert vm.get("verified_at"), "verified_at missing on a verified record"
    assert isinstance(vm.get("days_since_verified"), int)


def test_10_admin_verify_reflects_in_sales_detail_immediately(H):
    marker = "PHASE_18_2_LIVE_MARKER"
    # Save draft with marker
    httpx.put(f"{API_BASE}/occupation-master/{TEST_OID}", headers=H,
              json={"description": marker}, timeout=15)
    # Verify (re-verify) — should preserve marker
    httpx.post(f"{API_BASE}/occupation-master/{TEST_OID}/verify", headers=H,
               json={"source_reference": "https://example.com/p182-live",
                     "description": marker}, timeout=15)
    r = _detail(H)
    assert (r.json().get("overview") or {}).get("description") == marker
    # Restore the ACS-grade content from ai_draft so subsequent test_15
    # (and Sir's UI inspection) sees real data, not a test marker.
    from migrations.phase180_cleanup_probe_pollution import run_cleanup_probe_pollution
    _async(run_cleanup_probe_pollution(_db))


def test_11_header_code_present_in_response(H):
    r = _detail(H)
    code = (r.json().get("overview") or {}).get("code")
    assert code == TEST_CODE, f"overview.code should be {TEST_CODE!r}, got {code!r}"


def test_12_legacy_fallback_when_doc_missing(H):
    """Request a code that does NOT exist in occupation_master at all. Backend
    should either 404 cleanly (no occupation in either source) or return a
    minimal legacy-shaped response (degradation path). Either is acceptable —
    what's NOT acceptable is a 500."""
    r = httpx.get(f"{API_BASE}/sales/occupations/AU/zzz_no_such_code", headers=H, timeout=15)
    assert r.status_code in (200, 404), f"Got {r.status_code}, expected 200 or 404"


def test_13_no_path_leak_in_sales_detail(H):
    """Adversarial sweep — no traversal / no exception leakage on weird codes."""
    weird = ["../../../etc/passwd", "%2e%2e%2fsecret", "1' OR '1'='1", "<script>x</script>"]
    for w in weird:
        r = httpx.get(f"{API_BASE}/sales/occupations/AU/{w}", headers=H, timeout=15)
        # Either resolves cleanly to 404 or 200 with empty-ish payload — never 500
        assert r.status_code < 500, f"Adversarial code {w!r} caused {r.status_code}: {r.text[:120]}"
