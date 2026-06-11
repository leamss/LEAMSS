"""Phase 17.1.3 — Edit-page action endpoints accept slug identifier.

Verifies the "Occupation not found" toast bug from Sir's screenshot is fixed:
all action endpoints (GET, PUT, POST /verify, POST /ai-draft, DELETE) now
resolve identifiers via dual-lookup (`occupation_id` first, slug fallback)
and AU records have had `occupation_id` backfilled to `au-{code}`."""
from __future__ import annotations
import os, sys, asyncio, json
import httpx, pytest
from dotenv import load_dotenv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from motor.motor_asyncio import AsyncIOMotorClient  # noqa

API_BASE = os.environ.get("AUDIT_API_BASE", "http://localhost:8001/api")
_db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


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


def test_1_get_occupation_by_slug(H):
    """GET /occupation-master/au-111111 must return the full record."""
    r = httpx.get(f"{API_BASE}/occupation-master/au-111111", headers=H, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body["country_code"] == "AU"
    assert body["code"] == "111111"
    assert body.get("occupation_id") == "au-111111"


def test_2_verify_publish_by_slug(H):
    """POST /occupation-master/au-111111/verify must flip status to verified."""
    r = httpx.post(
        f"{API_BASE}/occupation-master/au-111111/verify", headers=H,
        json={"source_reference": "https://abs.gov.au/anzsco/111111",
              "review_notes": "Phase 17.1.3 test"},
        timeout=15,
    )
    assert r.status_code == 200, f"Verify failed: {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body["status"] == "verified"
    v = body.get("verification") or {}
    assert v.get("verified_at"), "verification.verified_at not set"


def test_3_save_draft_by_slug(H):
    """PUT /occupation-master/au-111111 must update description (Save Draft)."""
    test_marker = "Phase 17.1.3 description update marker"
    r = httpx.put(
        f"{API_BASE}/occupation-master/au-111111", headers=H,
        json={"description": test_marker},
        timeout=15,
    )
    assert r.status_code == 200, f"Save failed: {r.status_code}: {r.text[:200]}"
    assert r.json().get("description") == test_marker


def test_4_generate_ai_draft_by_slug(H):
    """POST /occupation-master/au-111111/ai-draft must produce description + tasks.
    Skips if LLM key not configured in this env."""
    r = httpx.post(
        f"{API_BASE}/occupation-master/au-111111/ai-draft",
        headers=H, timeout=60,
    )
    if r.status_code == 500 and "EMERGENT_LLM_KEY" in r.text:
        pytest.skip("LLM key not configured in test env")
    assert r.status_code == 200, f"AI draft failed: {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body.get("ok") is True
    ai = body.get("ai_draft") or {}
    assert ai.get("description"), "AI description empty"
    assert isinstance(ai.get("typical_tasks"), list)
    assert len(ai["typical_tasks"]) >= 1


def test_5_404_for_truly_missing_occupation(H):
    """Regression: non-existent slug returns 404 with helpful detail."""
    r = httpx.get(f"{API_BASE}/occupation-master/au-999999", headers=H, timeout=10)
    assert r.status_code == 404
    assert "not found" in r.json().get("detail", "").lower()


def test_6_au_records_have_occupation_id_after_backfill():
    """No AU record (or CA / NZ) should be missing `occupation_id` after Phase
    17.1.3 startup backfill runs."""
    n_au = _async(_db["occupation_master"].count_documents(
        {"country_code": "AU", "occupation_id": {"$exists": False}}))
    n_ca = _async(_db["occupation_master"].count_documents(
        {"country_code": "CA", "occupation_id": {"$exists": False}}))
    n_nz = _async(_db["occupation_master"].count_documents(
        {"country_code": "NZ", "occupation_id": {"$exists": False}}))
    assert n_au == 0, f"{n_au} AU records still missing occupation_id"
    assert n_ca == 0, f"{n_ca} CA records still missing occupation_id"
    assert n_nz == 0, f"{n_nz} NZ records still missing occupation_id"


def test_7_dual_lookup_safety_works_for_ca(H):
    """Dual-lookup helper accepts `ca-{code}` slug just like AU."""
    r = httpx.get(f"{API_BASE}/occupation-master/ca-10010", headers=H, timeout=10)
    assert r.status_code == 200
    assert r.json()["country_code"] == "CA"
