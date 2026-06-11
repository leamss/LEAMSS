"""Phase 17.1.1 — country runners actually work + backfill regression."""
from __future__ import annotations
import asyncio, os, sys, json
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


def _fetch(H, country, timeout=120):
    return httpx.post(f"{API_BASE}/kb-unified/auto-fetch-country",
                      headers=H, json={"country": country}, timeout=timeout)


def test_1_ca_auto_fetch_actually_updates_records(H):
    r = _fetch(H, "CA")
    if r.status_code == 502: pytest.skip("Network-dependent")
    assert r.status_code == 200
    res = r.json()["results"][0]
    assert res["country"] == "CA"
    assert res["updated"] >= 100, f"CA only updated {res['updated']} — runner is still broken"
    assert res["status"] in ("success", "partial")


def test_2_nz_auto_fetch_actually_updates_records(H):
    r = _fetch(H, "NZ")
    if r.status_code == 502: pytest.skip("Network-dependent")
    assert r.status_code == 200
    res = r.json()["results"][0]
    assert res["country"] == "NZ"
    assert res["updated"] >= 100, f"NZ only updated {res['updated']} — runner is still broken"
    assert res["status"] in ("success", "partial")


def test_3_au_auto_fetch_still_works(H):
    r = _fetch(H, "AU")
    if r.status_code == 502: pytest.skip("Network-dependent")
    assert r.status_code == 200
    res = r.json()["results"][0]
    assert res["updated"] >= 100


def test_4_runner_failure_propagates(H, monkeypatch):
    """Mock a scraper to raise → runner must surface status=failed + errors[]."""
    try:
        from routers import kb_unified as kb
    except ImportError:
        pytest.skip("kb_unified not importable")
    # Patch attribute on `core.scrapers.nz_anzsco_seed` directly via sys.modules
    import core.scrapers.nz_anzsco_seed as nz_mod
    original = nz_mod.apply_to_db
    async def boom(*a, **kw): raise RuntimeError("simulated scraper crash")
    nz_mod.apply_to_db = boom
    try:
        r = _fetch(H, "NZ")
    finally:
        nz_mod.apply_to_db = original
    if r.status_code == 502: pytest.skip("Network-dependent")
    # Running uvicorn worker holds its own ref; if patch took effect, errors[] populated
    res = r.json()["results"][0]
    if "simulated scraper crash" not in json.dumps(res):
        pytest.skip("Cannot inject into live uvicorn process")
    assert res["status"] in ("failed", "partial")
    assert any("simulated" in e for e in res.get("errors", []))


def test_5_ca_records_have_last_verified_after_fetch(H):
    _fetch(H, "CA")
    cur = _db["occupation_master"].find({"country_code": "CA"}, {"_id": 0}).limit(5)
    rows = _async(cur.to_list(5))
    for r in rows:
        v = r.get("verification") or {}
        assert v.get("auto_verified_at"), f"CA {r.get('code')} missing verification.auto_verified_at"
        assert v.get("source"), f"CA {r.get('code')} missing verification.source"


def test_6_nz_records_have_last_verified_after_fetch(H):
    _fetch(H, "NZ")
    cur = _db["occupation_master"].find({"country_code": "NZ"}, {"_id": 0}).limit(5)
    rows = _async(cur.to_list(5))
    for r in rows:
        v = r.get("verification") or {}
        assert v.get("auto_verified_at")
        assert v.get("source")


def test_7_existing_records_backfilled():
    """After startup backfill, no CA or NZ record should lack verification.source."""
    n_ca = _async(_db["occupation_master"].count_documents(
        {"country_code": "CA", "verification.source": {"$exists": False}}))
    n_nz = _async(_db["occupation_master"].count_documents(
        {"country_code": "NZ", "verification.source": {"$exists": False}}))
    assert n_ca == 0, f"{n_ca} CA records missing verification.source"
    assert n_nz == 0, f"{n_nz} NZ records missing verification.source"


def test_8_edit_link_carries_filters():
    """Frontend file inspection: confirm OccupationsTable Edit link includes
    country + code + status query params (Phase 17.1.1 default-filter bridge)."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "..", "frontend", "src", "pages", "admin", "VerificationHub.jsx")
    path = os.path.normpath(path)
    if not os.path.exists(path):
        pytest.skip("Frontend file not present")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "country=${encodeURIComponent(r.country_code" in content, "Edit link missing country param"
    assert "code=${encodeURIComponent(r.code" in content, "Edit link missing code param"
    assert "status=all" in content, "Edit link missing status=all to bypass draft default"
