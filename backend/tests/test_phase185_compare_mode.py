"""Phase 18.5 — Compare Mode + Phase 18.3.1 SLA badge backend tests.

13 test cases (Sir's brief):
  1. POST /sales/compare returns 2-occupation comparison
  2. >3 codes → 400
  3. Empty codes → 400 (Pydantic min_length)
  4. Unknown occupation lands in `not_found`
  5. Cache hit returns identical compared_at within TTL
  6. summary_narrative non-empty for ≥2 occupations
  7. Single-occupation narrative gives "pin another" hint
  8. Common visa subclasses surfaced when shared
  9. Shortest processing-time highlighted in narrative
 10. outcome_distribution computed correctly from sample_cases
 11. Partner role allowed
 12. Unauthenticated → 401/403
 13. Phase 18.3.1 — GET /feedback-requests/summary returns oldest_open_age_days

Spec: deterministic narrative (no LLM). 60s in-memory cache. Max 3 codes.
"""
from __future__ import annotations
import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
import httpx
import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

API_BASE = os.environ.get("AUDIT_API_BASE", "http://localhost:8001/api")
MONGO = AsyncIOMotorClient(os.environ["MONGO_URL"])
DB = MONGO[os.environ["DB_NAME"]]


def _login(email: str = "admin@leamss.com", password: str = "Admin@123") -> dict:
    r = httpx.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=20)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def H():
    return _login()


@pytest.fixture(scope="module")
def P():
    try:
        return _login("partner@leamss.com", "Partner@123")
    except Exception:
        pytest.skip("partner account not available")


def _async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# Two stable verified CA occupations chosen for testing
A_CC, A_CODE = "CA", "21231"  # Software engineers
B_CC, B_CODE = "CA", "31102"  # Family physicians


@pytest.fixture(scope="module", autouse=True)
def _seed_known_state():
    """Seed minimal known data so narrative + outcome_distribution rows are deterministic.

    Idempotent — only touches the fields this test cares about and never wipes
    existing admin-curated payloads beyond a known reset to a fixture state.

    Phase 18.6 — also busts the /sales/compare 60s cache via an admin-only HTTP
    endpoint so prior tests that populated it with stale data don't bleed into
    this module's assertions. (The cache lives in the FastAPI process — direct
    in-process clears from pytest don't reach it.)
    """
    # Server-side cache bust
    try:
        H = _login()
        httpx.post(f"{API_BASE}/sales/compare/_test/clear-cache", headers=H, timeout=10)
    except Exception:
        pass

    async def _seed():
        # Occupation A — full skill_body + sample cases for outcome counts
        await DB.occupation_master.update_one(
            {"country_code": A_CC, "code": A_CODE},
            {"$set": {
                "occupation_id": f"{A_CC.lower()}-{A_CODE}",
                "country_code": A_CC,
                "code": A_CODE,
                "status": "verified",
                "title": "Software engineers and designers",
                "assessing_authority": {
                    "name": "ACS",
                    "processing_time_weeks": 6,
                    "fee_native": 530,
                    "fee_currency": "AUD",
                },
                "visa_pathways": {
                    "visa_eligibility": [
                        {"visa_subclass": "FSWP", "visa_name": "Federal Skilled Worker", "eligible": True},
                        {"visa_subclass": "CEC",  "visa_name": "Canadian Experience Class", "eligible": True},
                    ],
                },
                "recommended_visa_subclass": {"CA": "FSWP"},
                "required_documents": [
                    {"category": "Identity", "name": "Passport"},
                    {"category": "Education", "name": "Degree"},
                ],
                "similar_codes_override": ["ca-21232"],
                "sample_cases": [
                    {"id": "c1", "outcome": "approved",  "title": "Hari", "notes": ""},
                    {"id": "c2", "outcome": "refused",   "title": "Riya", "notes": ""},
                    {"id": "c3", "outcome": "withdrawn", "title": "Kabir", "notes": ""},
                    {"id": "c4", "outcome": "pending",   "title": "Naina", "notes": ""},
                ],
                "verification": {
                    "is_verified": True,
                    "verified_at": datetime.now(timezone.utc),
                    "verified_by_name": "Admin User",
                },
            }},
            upsert=True,
        )
        # Occupation B — slower processing + only CEC visa so narrative can prove
        # shortest-time AND common-subclass logic
        await DB.occupation_master.update_one(
            {"country_code": B_CC, "code": B_CODE},
            {"$set": {
                "occupation_id": f"{B_CC.lower()}-{B_CODE}",
                "country_code": B_CC,
                "code": B_CODE,
                "status": "verified",
                "title": "General practitioners and family physicians",
                "assessing_authority": {
                    "name": "MCC",
                    "processing_time_weeks": 14,
                    "fee_native": 800,
                    "fee_currency": "CAD",
                },
                "visa_pathways": {
                    "visa_eligibility": [
                        {"visa_subclass": "FSWP", "visa_name": "Federal Skilled Worker", "eligible": True},
                        {"visa_subclass": "PNP",  "visa_name": "Provincial Nominee", "eligible": True},
                    ],
                },
                "recommended_visa_subclass": {"CA": "PNP"},
                "required_documents": [{"category": "Identity", "name": "Passport"}],
                "similar_codes_override": [],
                "sample_cases": [],
                "verification": {"is_verified": True},
            }},
            upsert=True,
        )
    _async(_seed())
    yield


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /sales/compare returns 2-occupation comparison
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_two_occupations(H):
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=H,
        json={"codes": [{"country_code": A_CC, "code": A_CODE}, {"country_code": B_CC, "code": B_CODE}]},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "occupations" in body and isinstance(body["occupations"], list)
    assert len(body["occupations"]) == 2
    titles = [o["title"] for o in body["occupations"]]
    assert any("Software" in t for t in titles)
    assert any("physicians" in t.lower() for t in titles)


# ─────────────────────────────────────────────────────────────────────────────
# 2. >3 codes → 400
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_over_3_codes_rejected(H):
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=H,
        json={"codes": [
            {"country_code": A_CC, "code": A_CODE},
            {"country_code": B_CC, "code": B_CODE},
            {"country_code": A_CC, "code": "21311"},
            {"country_code": A_CC, "code": "31301"},
        ]},
        timeout=20,
    )
    # FastAPI/Pydantic returns 422 for max_length violations; accept either 422 or 400
    assert r.status_code in (400, 422), r.text


# ─────────────────────────────────────────────────────────────────────────────
# 3. Empty codes → 400/422
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_empty_codes_rejected(H):
    r = httpx.post(f"{API_BASE}/sales/compare", headers=H, json={"codes": []}, timeout=20)
    assert r.status_code in (400, 422), r.text


# ─────────────────────────────────────────────────────────────────────────────
# 4. Unknown occupation lands in `not_found`
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_unknown_lands_in_not_found(H):
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=H,
        json={"codes": [{"country_code": "CA", "code": "99999"}, {"country_code": A_CC, "code": A_CODE}]},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["occupations"]) == 1
    assert {"country_code": "CA", "code": "99999"} in body["not_found"]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Cache hit returns identical compared_at within TTL
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_cache_returns_identical_payload(H):
    payload = {"codes": [{"country_code": A_CC, "code": A_CODE}, {"country_code": B_CC, "code": B_CODE}]}
    r1 = httpx.post(f"{API_BASE}/sales/compare", headers=H, json=payload, timeout=20)
    r2 = httpx.post(f"{API_BASE}/sales/compare", headers=H, json=payload, timeout=20)
    assert r1.status_code == r2.status_code == 200
    # Same compared_at proves the cache is hit (else 2nd call computes a new ISO ts)
    assert r1.json()["compared_at"] == r2.json()["compared_at"]


# ─────────────────────────────────────────────────────────────────────────────
# 6. summary_narrative non-empty for ≥2 occupations
# ─────────────────────────────────────────────────────────────────────────────
def test_summary_narrative_non_empty_for_two(H):
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=H,
        json={"codes": [{"country_code": A_CC, "code": A_CODE}, {"country_code": B_CC, "code": B_CODE}]},
        timeout=20,
    )
    assert r.status_code == 200
    narrative = r.json()["summary_narrative"]
    assert isinstance(narrative, str) and len(narrative) > 30


# ─────────────────────────────────────────────────────────────────────────────
# 7. Single-occupation narrative gives "pin another" hint
# ─────────────────────────────────────────────────────────────────────────────
def test_single_occupation_narrative_pin_hint(H):
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=H,
        json={"codes": [{"country_code": A_CC, "code": A_CODE}]},
        timeout=20,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["occupations"]) == 1
    assert "pin another" in body["summary_narrative"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# 8. Common visa subclasses surfaced when shared
# ─────────────────────────────────────────────────────────────────────────────
def test_narrative_surfaces_common_subclass(H):
    # A has [FSWP, CEC]; B has [FSWP, PNP] → common = FSWP
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=H,
        json={"codes": [{"country_code": A_CC, "code": A_CODE}, {"country_code": B_CC, "code": B_CODE}]},
        timeout=20,
    )
    narrative = r.json()["summary_narrative"]
    assert "FSWP" in narrative, narrative


# ─────────────────────────────────────────────────────────────────────────────
# 9. Shortest processing-time highlighted in narrative
# ─────────────────────────────────────────────────────────────────────────────
def test_narrative_highlights_shortest_processing(H):
    # A (ACS, 6 weeks) is faster than B (MCC, 14 weeks)
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=H,
        json={"codes": [{"country_code": A_CC, "code": A_CODE}, {"country_code": B_CC, "code": B_CODE}]},
        timeout=20,
    )
    narrative = r.json()["summary_narrative"]
    assert "6 weeks" in narrative
    assert A_CODE in narrative


# ─────────────────────────────────────────────────────────────────────────────
# 10. outcome_distribution computed correctly from sample_cases
# ─────────────────────────────────────────────────────────────────────────────
def test_outcome_distribution_from_sample_cases(H):
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=H,
        json={"codes": [{"country_code": A_CC, "code": A_CODE}]},
        timeout=20,
    )
    occ = r.json()["occupations"][0]
    od = occ["outcome_distribution"]
    assert od == {"approved": 1, "refused": 1, "withdrawn": 1, "pending": 1}, od
    assert occ["sample_cases_count"] == 4


# ─────────────────────────────────────────────────────────────────────────────
# 11. Partner role allowed
# ─────────────────────────────────────────────────────────────────────────────
def test_partner_role_allowed(P):
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        headers=P,
        json={"codes": [{"country_code": A_CC, "code": A_CODE}, {"country_code": B_CC, "code": B_CODE}]},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["occupations"]) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 12. Unauthenticated → 401/403
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_unauth_blocked():
    r = httpx.post(
        f"{API_BASE}/sales/compare",
        json={"codes": [{"country_code": A_CC, "code": A_CODE}]},
        timeout=20,
    )
    assert r.status_code in (401, 403), r.text


# ─────────────────────────────────────────────────────────────────────────────
# 13. Phase 18.3.1 — GET /feedback-requests/summary returns oldest_open_age_days
# ─────────────────────────────────────────────────────────────────────────────
def test_feedback_summary_oldest_open_age_days(H):
    # Seed one OPEN feedback request dated 10 days ago to make age non-zero
    async def _seed_old_open():
        ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
        await DB.feedback_requests.insert_one({
            "id": "phase185-test-old-open",
            "request_type": "verification_request",
            "occupation_id": f"{A_CC.lower()}-{A_CODE}",
            "country_code": A_CC,
            "code": A_CODE,
            "occupation_title": "Software engineers and designers",
            "requested_field": "general",
            "message": "Sla test seed",
            "requested_by": "test",
            "requested_by_name": "test",
            "requested_by_role": "admin",
            "requested_at": ten_days_ago,
            "status": "open",
            "resolved_by": None,
            "resolved_at": None,
            "resolution_notes": None,
        })
    async def _cleanup():
        await DB.feedback_requests.delete_one({"id": "phase185-test-old-open"})

    try:
        # Clean any prior stale seed first to guarantee deterministic age
        _async(_cleanup())
        _async(_seed_old_open())

        r = httpx.get(f"{API_BASE}/feedback-requests/summary", headers=H, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("open_count", "in_progress_count", "resolved_count", "oldest_open_at", "oldest_open_age_days"):
            assert k in body, f"missing key: {k}"
        # The seeded entry is at least 10 days old; we know it is the oldest
        # because no other test seed is allowed older — assert >= 10.
        assert body["oldest_open_age_days"] is not None
        assert body["oldest_open_age_days"] >= 10, body
    finally:
        _async(_cleanup())
