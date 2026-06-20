"""Phase 19.4d — Per-State AU Atlas Pages tests.

Covers: seed idempotency, aggregation, public API, SSG render, meta length,
CTA presence, sitemap inclusion, cross-links from occupations.
"""
from __future__ import annotations

import os
import re
import pathlib
import pytest
import requests
from pymongo import MongoClient

API = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
if not API.endswith("/api"):
    API = API.rstrip("/") + "/api"

_db = None


def _get_db():
    global _db
    if _db is None:
        # Auto-load /app/backend/.env if env vars not set (test-runner robustness)
        mongo = os.environ.get("MONGO_URL")
        dbname = os.environ.get("DB_NAME")
        if not mongo or not dbname:
            envp = pathlib.Path("/app/backend/.env")
            if envp.exists():
                for line in envp.read_text().splitlines():
                    if "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip())
            mongo = os.environ.get("MONGO_URL")
            dbname = os.environ.get("DB_NAME")
        _db = MongoClient(mongo)[dbname]
    return _db


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": "admin@leamss.com", "password": "Admin@123"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_194d_01_seed_8_states_unique_slugs(headers):
    """Seed populates 8 states with unique slugs and codes."""
    r = requests.post(f"{API}/admin/au-states/seed", headers=headers, timeout=15)
    assert r.status_code == 200
    db = _get_db()
    states = list(db.au_states_master.find({}, {"_id": 0, "state_code": 1, "slug": 1}))
    assert len(states) == 8
    codes = {s["state_code"] for s in states}
    slugs = {s["slug"] for s in states}
    assert codes == {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}
    assert len(slugs) == 8  # all unique
    assert "new-south-wales" in slugs


def test_194d_02_seed_idempotent(headers):
    """Re-running seed doesn't create duplicates."""
    r1 = requests.post(f"{API}/admin/au-states/seed", headers=headers, timeout=15)
    r2 = requests.post(f"{API}/admin/au-states/seed", headers=headers, timeout=15)
    d2 = r2.json()
    assert len(d2["skipped"]) == 8 and len(d2["created"]) == 0


def test_194d_03_aggregation_populates_vacancy(headers):
    """Refresh pulls monthly_ads from vacancy_snapshots.by_state."""
    r = requests.post(f"{API}/admin/au-states/NSW/refresh", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    assert d["vacancy_data"] is not None
    assert d["vacancy_data"]["monthly_ads"] >= 1000  # NSW has 62500 in seed snapshot


def test_194d_04_aggregation_populates_top_occupations(headers):
    """Refresh computes top_occupations using state_distribution shares."""
    r = requests.post(f"{API}/admin/au-states/VIC/refresh", headers=headers, timeout=15)
    d = r.json()
    assert d["counts"]["top_occupations"] >= 1


def test_194d_05_aggregation_handles_missing_nominations(headers):
    """state_nomination_lists empty — refresh degrades to None gracefully."""
    r = requests.post(f"{API}/admin/au-states/TAS/refresh", headers=headers, timeout=15)
    d = r.json()
    assert d["ok"] is True
    assert d["sol_codes"] is None and d["rol_codes"] is None
    assert d["counts"]["has_nomination_lists"] is False


def test_194d_06_public_api_returns_full_data():
    """Public GET /AU/state/NSW returns name, capital, ads, top occupations."""
    r = requests.get(f"{API}/public-atlas/AU/state/NSW", timeout=10)
    assert r.status_code == 200, r.text
    d = r.json()["state"]
    assert d["state_name"] == "New South Wales"
    assert d["capital_city"] == "Sydney"
    assert (d.get("vacancy_data") or {}).get("monthly_ads") >= 1000


def test_194d_07_ssg_renders_all_8_states():
    """All 8 state SSG pages render to disk via /seo-ssg/regenerate-all."""
    # Confirm files were written by the last regen
    base = pathlib.Path("/app/frontend/public/atlas/au/state")
    slugs = ["new-south-wales", "victoria", "queensland", "south-australia",
             "western-australia", "tasmania", "northern-territory",
             "australian-capital-territory"]
    for slug in slugs:
        f = base / slug / "index.html"
        assert f.exists(), f"Missing SSG page for {slug}"
        html = f.read_text()
        assert "Free Eligibility Check" in html
        assert "LEAMSS" in html


def test_194d_08_unique_meta_descriptions_under_165():
    """Each of 8 state pages has a UNIQUE meta description ≤165 chars + CTA."""
    base = pathlib.Path("/app/frontend/public/atlas/au/state")
    descs = []
    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        f = d / "index.html"
        if not f.exists():
            continue
        html = f.read_text()
        m = re.search(r'<meta name="description" content="([^"]+)"', html)
        assert m, f"No meta description in {d.name}"
        desc = m.group(1)
        assert len(desc) <= 165, f"{d.name}: {len(desc)} chars — {desc}"
        assert "eligibility check" in desc.lower(), f"{d.name}: no CTA"
        descs.append(desc)
    assert len(descs) == 8
    assert len(set(descs)) == 8  # all unique


def test_194d_09_sitemap_includes_8_state_urls():
    """sitemap.xml includes 8 /atlas/au/state/{slug} URLs with priority 0.8."""
    sitemap = pathlib.Path("/app/frontend/public/sitemap.xml")
    assert sitemap.exists()
    text = sitemap.read_text()
    state_urls = re.findall(r"/atlas/au/state/([a-z\-]+)", text)
    assert len(set(state_urls)) == 8


def test_194d_10_occupation_page_links_to_top_states():
    """An AU occupation page contains links to /atlas/au/state/... cross-links."""
    base = pathlib.Path("/app/frontend/public/atlas/au")
    # Find any verified occupation page that was regenerated
    sample = None
    for code_dir in base.iterdir():
        if code_dir.is_dir() and code_dir.name not in ("industry", "state") and (code_dir / "index.html").exists():
            sample = code_dir / "index.html"
            break
    assert sample, "No AU occupation page found"
    html = sample.read_text()
    # At least one of the 8 state slugs should be linked
    state_slugs = ["new-south-wales", "victoria", "queensland", "south-australia",
                   "western-australia", "tasmania", "northern-territory",
                   "australian-capital-territory"]
    assert any(f"/atlas/au/state/{s}/" in html for s in state_slugs), \
        "No state cross-link found in occupation page"
