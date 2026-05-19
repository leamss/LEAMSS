"""Phase 6 v2 Part 1 — Smart Sales Helper backend tests."""
import os
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://staff-dashboard-66.preview.emergentagent.com"
BASE = f"{API}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ════════════════════════════════════════════════════════════════
# Search
# ════════════════════════════════════════════════════════════════
def test_search_marketing_finds_specialist(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/search", params={"q": "marketing", "limit": 5}, headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    codes = [i["code"] for i in d["items"]]
    assert "225113" in codes


def test_search_typo_marketig_still_finds_marketing(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/search", params={"q": "marketig", "limit": 3}, headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["count"] > 0, "Fuzzy search must handle typos"
    codes = [i["code"] for i in d["items"]]
    assert "225113" in codes


def test_search_operations_head_finds_hotel_manager(admin_headers):
    """Sir's actual case — 'Operations Head' should match Hotel/Motel Mgr (141311)."""
    r = requests.get(f"{BASE}/sales/occupations/search", params={"q": "operations head", "country": ["AU"], "limit": 5}, headers=admin_headers, timeout=10)
    d = r.json()
    codes = [i["code"] for i in d["items"]]
    # 132111 (Corp GM) or 141311 (Hotel Mgr) should be in top 5
    assert "132111" in codes or "141311" in codes


def test_search_exact_code_100_percent(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/search", params={"q": "225113"}, headers=admin_headers, timeout=10)
    d = r.json()
    top = d["items"][0]
    assert top["code"] == "225113"
    assert top["confidence"] == 100


def test_search_country_filter(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/search", params={"country": ["AU"], "limit": 100}, headers=admin_headers, timeout=10)
    d = r.json()
    assert all(i["country_code"] == "AU" for i in d["items"])


def test_search_pathway_filter(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/search", params={"pathway": "MLTSSL", "limit": 100}, headers=admin_headers, timeout=10)
    d = r.json()
    for i in d["items"]:
        assert (i.get("pathway") or "").upper() == "MLTSSL"


def test_search_in_demand_filter(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/search", params={"in_demand": "true", "limit": 100}, headers=admin_headers, timeout=10)
    d = r.json()
    assert all(i.get("in_demand") for i in d["items"])


def test_search_unauth_returns_403_or_401(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/search", timeout=10)
    assert r.status_code in (401, 403)


# ════════════════════════════════════════════════════════════════
# Typeahead
# ════════════════════════════════════════════════════════════════
def test_typeahead_returns_max_5(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/typeahead", params={"q": "eng"}, headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert len(d["items"]) <= 5


# ════════════════════════════════════════════════════════════════
# Detail
# ════════════════════════════════════════════════════════════════
def test_detail_141311_returns_all_6_sections(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/AU/141311", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["country_code"] == "AU"
    assert d["overview"]["code"] == "141311"
    assert d["overview"]["title"] == "Hotel or Motel Manager"
    # 6 tab payloads
    assert d.get("overview") is not None
    assert d.get("skill_assessment") is not None
    assert d["skill_assessment"]["name"] == "VETASSESS"
    assert d["skill_assessment"].get("fee_native", {}).get("currency") == "AUD"
    assert len(d.get("visa_pathways", [])) > 0
    assert d.get("document_checklist", {}).get("total_docs", 0) > 0
    assert isinstance(d.get("similar_codes"), list)


def test_detail_unknown_code_returns_404(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/AU/9999999", headers=admin_headers, timeout=10)
    assert r.status_code == 404


def test_detail_unknown_country_returns_404(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/XX/225113", headers=admin_headers, timeout=10)
    assert r.status_code == 404


# ════════════════════════════════════════════════════════════════
# Compare
# ════════════════════════════════════════════════════════════════
def test_compare_two_codes(admin_headers):
    r = requests.post(
        f"{BASE}/sales/occupations/compare",
        json={"items": [{"country_code": "AU", "code": "225113"}, {"country_code": "AU", "code": "141311"}]},
        headers=admin_headers, timeout=10,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["count"] == 2
    titles = [i["title"] for i in d["items"]]
    assert "Marketing Specialist" in titles
    assert "Hotel or Motel Manager" in titles


def test_compare_min_items_2(admin_headers):
    r = requests.post(
        f"{BASE}/sales/occupations/compare",
        json={"items": [{"country_code": "AU", "code": "225113"}]},
        headers=admin_headers, timeout=10,
    )
    assert r.status_code == 422  # Pydantic validation error


def test_compare_max_items_4(admin_headers):
    r = requests.post(
        f"{BASE}/sales/occupations/compare",
        json={"items": [{"country_code": "AU", "code": f"X{i}"} for i in range(5)]},
        headers=admin_headers, timeout=10,
    )
    assert r.status_code == 422


# ════════════════════════════════════════════════════════════════
# Filters meta
# ════════════════════════════════════════════════════════════════
def test_filter_meta(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/filters/meta", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert {c["code"] for c in d["countries"]} == {"AU", "CA", "NZ"}
    assert "MLTSSL" in d["pathways"]
    assert "VETASSESS" in d["skill_bodies"]
    assert d["skill_levels"] == [1, 2, 3, 4, 5]
    assert "AU" in d["states_by_country"]


# ════════════════════════════════════════════════════════════════
# Old endpoints removed
# ════════════════════════════════════════════════════════════════
def test_old_assessment_endpoint_gone(admin_headers):
    """Phase 6 v2 cleanup: old AI assessment endpoint must return 404."""
    r = requests.post(f"{BASE}/eligibility/assessments/run", json={"profile_id": "ELG-TEST"}, headers=admin_headers, timeout=5)
    assert r.status_code == 404, "Old AI assessment endpoint should be removed"
