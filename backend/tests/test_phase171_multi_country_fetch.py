"""Phase 17.1 — Multi-country auto-fetch + tab-count parity tests."""
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


PATH_LEAK = ("/tmp/", "/app/backend/storage", "Traceback")


def _no_leak(body, label=""):
    s = json.dumps(body, default=str)
    for p in PATH_LEAK:
        assert p not in s, f"Leak '{p}' in {label}: {s[:160]}"


def test_tab_count_matches_tile_total(H):
    """Tab badges (KPI sum across all status buckets) match the actual record
    count from each entity's list endpoint.

    Phase 18.6 fix — the verification hub counts ALL records (incl. ``superseded``)
    while the public list endpoint excludes superseded entries. The meaningful
    invariant is ``hub.counts.verified == list.total``; that's what the UI tile
    actually shows users.
    """
    hub = httpx.get(f"{API_BASE}/kb-unified/verification-hub", headers=H, timeout=10).json()
    counts = hub["summary"]["occupation_master"]["counts"]
    occ_actual = httpx.get(f"{API_BASE}/occupation-master?limit=1", headers=H, timeout=10).json()["total"]
    verified_tile = counts.get("verified", 0)
    total_tile = sum(counts.values())
    # 1) Verified count matches the list endpoint's total (no drift)
    assert verified_tile == occ_actual, f"Verified tile={verified_tile} vs list total={occ_actual}"
    # 2) Superseded is the only allowed delta — hub is total ≥ list
    assert total_tile >= occ_actual, f"Hub total={total_tile} smaller than list={occ_actual}"


def test_occupation_list_endpoint_pagination(H):
    r1 = httpx.get(f"{API_BASE}/occupation-master?limit=25&skip=0", headers=H, timeout=10).json()
    r2 = httpx.get(f"{API_BASE}/occupation-master?limit=25&skip=25", headers=H, timeout=10).json()
    assert len(r1["items"]) == 25
    assert len(r2["items"]) == 25
    # Pages don't overlap
    ids1 = {(d["country_code"], d["code"]) for d in r1["items"]}
    ids2 = {(d["country_code"], d["code"]) for d in r2["items"]}
    assert not (ids1 & ids2), "Pages overlap"


def test_occupation_list_country_filter(H):
    for c, lo, hi in [("AU", 600, 900), ("CA", 400, 700), ("NZ", 100, 400)]:
        n = httpx.get(f"{API_BASE}/occupation-master?country={c}&limit=1", headers=H, timeout=10).json()["total"]
        assert lo <= n <= hi, f"{c} count {n} outside [{lo},{hi}]"


def test_auto_fetch_country_au(H):
    r = httpx.post(f"{API_BASE}/kb-unified/auto-fetch-country",
                   headers=H, json={"country": "AU"}, timeout=60)
    if r.status_code == 502:
        pytest.skip("Network-dependent")
    assert r.status_code == 200
    body = r.json()
    assert body["results"][0]["country"] == "AU"
    assert "Home Affairs" in body["results"][0]["source"]
    _no_leak(body, "AU")


def test_auto_fetch_country_ca(H):
    r = httpx.post(f"{API_BASE}/kb-unified/auto-fetch-country",
                   headers=H, json={"country": "CA"}, timeout=90)
    if r.status_code == 502:
        pytest.skip("Network-dependent")
    assert r.status_code == 200
    body = r.json()
    assert body["results"][0]["country"] == "CA"
    src = body["results"][0]["source"]
    assert "NOC" in src or "StatCan" in src or "IRCC" in src or src == "(failed)"
    _no_leak(body, "CA")


def test_auto_fetch_country_nz(H):
    r = httpx.post(f"{API_BASE}/kb-unified/auto-fetch-country",
                   headers=H, json={"country": "NZ"}, timeout=90)
    if r.status_code == 502:
        pytest.skip("Network-dependent")
    assert r.status_code == 200
    body = r.json()
    assert body["results"][0]["country"] == "NZ"
    src = body["results"][0]["source"]
    assert "Green List" in src or "INZ" in src or src == "(failed)"
    _no_leak(body, "NZ")


def test_auto_fetch_all_orders_au_ca_nz(H):
    r = httpx.post(f"{API_BASE}/kb-unified/auto-fetch-country",
                   headers=H, json={"country": "ALL"}, timeout=180)
    if r.status_code == 502:
        pytest.skip("Network-dependent")
    assert r.status_code == 200
    body = r.json()
    countries = [x["country"] for x in body["results"]]
    assert countries == ["AU", "CA", "NZ"], f"Order wrong: {countries}"
    t = body["totals"]
    assert t["imported"] + t["updated"] >= 100
    _no_leak(body, "ALL")


def test_import_runs_row_written(H):
    before = _async(_db["import_runs"].count_documents({"method": "auto_fetch"}))
    httpx.post(f"{API_BASE}/kb-unified/auto-fetch-country",
               headers=H, json={"country": "AU"}, timeout=60)
    after = _async(_db["import_runs"].count_documents({"method": "auto_fetch"}))
    assert after > before, "import_runs row was not written"
    latest = _async(_db["import_runs"].find_one({"method": "auto_fetch", "country": "AU"},
                                                  sort=[("started_at", -1)]))
    assert latest is not None
    assert latest["status"] in ("success", "partial", "failed")
    assert latest["triggered_by"]
    assert "summary" in latest


def test_backcompat_anzsco_alias(H):
    r = httpx.post(f"{API_BASE}/kb-unified/auto-fetch-anzsco", headers=H, timeout=60)
    if r.status_code == 502:
        pytest.skip("Network-dependent")
    assert r.status_code == 200
    assert r.json()["results"][0]["country"] == "AU"


def test_no_path_leak_on_new_endpoints(H):
    for c in ("AU", "CA", "NZ", "ALL"):
        r = httpx.post(f"{API_BASE}/kb-unified/auto-fetch-country",
                       headers=H, json={"country": c}, timeout=180)
        if r.status_code == 502:
            continue
        _no_leak(r.json(), f"auto-fetch {c}")
    r = httpx.get(f"{API_BASE}/kb-unified/import-runs?limit=10", headers=H, timeout=10)
    _no_leak(r.json(), "import-runs list")
