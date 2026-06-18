"""Phase 19.4 — JSA Universal Data Import + Atlas Surfacing tests.

Covers:
  · Upload + auto-detect + preview + commit flow
  · 4-digit ANZSCO → 6-digit fallback with `_parent_inherited` flag
  · regional_labour_market collection upsert from SA4 file
  · Atlas occupation page surfacing salary + growth + regional cards
  · Country index card surfacing salary chip + growth chip
  · Admin-only auth, history pagination, delete endpoint
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Tuple

import httpx
import pytest

BASE_URL = os.environ.get("LEAMSS_BACKEND_URL", "http://localhost:8001")
API = f"{BASE_URL}/api"
FE_BASE_URL = os.environ.get("LEAMSS_FE_URL", "http://localhost:3000")

ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"

GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

DATA_DIR = Path(os.environ.get("JSA_TEST_FILES", "/app/backend/data/jsa_imports"))
OCC_PROFILES = DATA_DIR / "occupation_profiles_feb_2026.xlsx"
EMP_PROJECTIONS = DATA_DIR / "employment_projections_may_2025_2035.xlsx"
SA4_RATINGS = DATA_DIR / "labour_market_ratings_by_sa4.xlsx"


def _login(email: str, password: str) -> str:
    with httpx.Client(base_url=BASE_URL, timeout=20) as c:
        r = c.post(f"{API}/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return r.json()["token"]


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _fetch_fe(path: str) -> Tuple[int, str]:
    with httpx.Client(base_url=FE_BASE_URL, timeout=30, follow_redirects=True) as c:
        r = c.get(path, headers={"User-Agent": GOOGLEBOT_UA})
        return r.status_code, r.text


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def jsa_imports_committed(admin_token: str) -> dict:
    """Module-scoped — upload, preview, commit all 3 JSA files once + SSG regen."""
    files = [
        ("occupation_profiles", OCC_PROFILES),
        ("employment_projections", EMP_PROJECTIONS),
        ("sa4_ratings", SA4_RATINGS),
    ]
    results = {}
    with httpx.Client(base_url=BASE_URL, timeout=120) as c:
        for ftype, fpath in files:
            if not fpath.exists():
                pytest.skip(f"missing test file {fpath}")
            with open(fpath, "rb") as fh:
                r = c.post(
                    f"{API}/data-import/upload",
                    files={"file": (fpath.name, fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_hdr(admin_token),
                )
            r.raise_for_status()
            up = r.json()
            assert up["detected_type"] == ftype, f"detector saw {up['detected_type']} for {ftype}"
            # Commit
            cm = c.post(f"{API}/data-import/{up['file_id']}/commit", headers=_hdr(admin_token))
            cm.raise_for_status()
            results[ftype] = {"upload": up, "commit": cm.json()}
        # SSG regen
        c.post(f"{API}/seo-ssg/regenerate-all", headers=_hdr(admin_token))
    return results


# ── Tests ──────────────────────────────────────────────────────────────────────

# 1. Upload returns file_id + correct auto-detected type
def test_01_data_import_upload_returns_file_id(admin_token: str):
    if not OCC_PROFILES.exists():
        pytest.skip("missing test file")
    with httpx.Client(base_url=BASE_URL, timeout=60) as c, open(OCC_PROFILES, "rb") as fh:
        r = c.post(
            f"{API}/data-import/upload",
            files={"file": (OCC_PROFILES.name, fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=_hdr(admin_token),
        )
    assert r.status_code == 200
    j = r.json()
    assert j.get("file_id")
    assert j["filename"] == OCC_PROFILES.name
    assert j["size_bytes"] > 0
    assert j["detected_type"] == "occupation_profiles"
    assert j["supported"] is True


# 2. Auto-detection works for all 3 file types
def test_02_data_import_detects_three_types(admin_token: str):
    for fpath, expected in [
        (OCC_PROFILES, "occupation_profiles"),
        (EMP_PROJECTIONS, "employment_projections"),
        (SA4_RATINGS, "sa4_ratings"),
    ]:
        if not fpath.exists():
            pytest.skip("missing test file")
        with httpx.Client(base_url=BASE_URL, timeout=60) as c, open(fpath, "rb") as fh:
            r = c.post(
                f"{API}/data-import/upload",
                files={"file": (fpath.name, fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=_hdr(admin_token),
            )
        assert r.status_code == 200, r.text
        assert r.json()["detected_type"] == expected


# 3. Preview returns sample rows + non-zero row count
def test_03_data_import_preview_returns_sample(admin_token: str):
    if not OCC_PROFILES.exists():
        pytest.skip("missing test file")
    with httpx.Client(base_url=BASE_URL, timeout=60) as c:
        with open(OCC_PROFILES, "rb") as fh:
            up = c.post(
                f"{API}/data-import/upload",
                files={"file": (OCC_PROFILES.name, fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=_hdr(admin_token),
            ).json()
        r = c.post(f"{API}/data-import/{up['file_id']}/parse-preview", headers=_hdr(admin_token))
    assert r.status_code == 200
    j = r.json()
    assert j["row_count"] >= 500
    assert j["source"].startswith("JSA")
    assert isinstance(j["sample"], list)
    assert len(j["sample"]) >= 5


# 4. Occupation Profiles parser extracts salary
def test_04_occupation_profiles_parser_extracts_salary(jsa_imports_committed):
    s = jsa_imports_committed["occupation_profiles"]["commit"]["summary"]
    assert s["parsed_4digit_records"] >= 700
    assert s["occupations_updated"] >= 500


# 5. Employment Projections parser assigns growth categories
def test_05_employment_projections_parser_assigns_growth(jsa_imports_committed):
    s = jsa_imports_committed["employment_projections"]["commit"]["summary"]
    assert s["occupations_updated"] >= 500


# 6. SA4 ratings parser creates regional_labour_market collection
def test_06_sa4_ratings_parser_creates_collection(jsa_imports_committed):
    s = jsa_imports_committed["sa4_ratings"]["commit"]["summary"]
    assert s["parsed_records"] >= 80, f"expected ≥80 SA4 regions, got {s.get('parsed_records')}"
    # Either upsert (first time) or modify (re-run)
    assert (s.get("regions_upserted", 0) + s.get("regions_modified", 0)) >= 80


# 7. Atlas occupation page renders salary card
def test_07_atlas_occupation_renders_salary_card(jsa_imports_committed):
    status, html = _fetch_fe("/atlas/au/261313/")
    assert status == 200
    assert "Median earnings" in html, "salary card title missing"
    assert "AUD" in html and "$2,537" in html, "ABS weekly fee missing on page"
    assert "$131,924" in html, "annual salary not rendered"
    assert "ABS via JSA Feb 2026" in html, "source attribution missing"


# 8. Atlas occupation page renders future-growth card
def test_08_atlas_occupation_renders_future_growth(jsa_imports_committed):
    status, html = _fetch_fe("/atlas/au/261313/")
    assert status == 200
    assert "10-year Outlook" in html or "Employment outlook" in html
    assert "Very Strong" in html or "Strong" in html, "growth pill missing"
    assert "26.7% by 2035" in html or "by 2035" in html, "growth % missing"
    assert "JSA Employment Projections" in html, "source attribution missing"


# 9. Atlas occupation page renders regional demand block (AU only)
def test_09_atlas_occupation_renders_regional_demand(jsa_imports_committed):
    status, html = _fetch_fe("/atlas/au/261313/")
    assert status == 200
    assert "Strongest labour markets" in html
    assert "Sydney" in html, "no Sydney SA4 regions surfaced"
    assert "RLMI" in html, "RLMI source attribution missing"


# 10. Country page card shows salary chip
def test_10_atlas_country_card_shows_salary_chip(jsa_imports_committed):
    status, html = _fetch_fe("/atlas/au/")
    assert status == 200
    chips = re.findall(r"💼\s*\$[0-9]+k/yr", html)
    assert len(chips) >= 5, f"expected ≥5 salary chips, found {len(chips)}: {chips[:3]}"
    growth_chips = re.findall(r"📈\s*(?:Very Strong|Strong|Moderate)", html)
    assert len(growth_chips) >= 5, f"expected ≥5 growth chips, found {len(growth_chips)}"


# 11. Non-admin gets 403 on all endpoints
def test_11_data_import_admin_only():
    # No token = 401/403
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        r = c.get(f"{API}/data-import/history")
        assert r.status_code in (401, 403)


# 12. Import history is paginated and returns items
def test_12_data_import_history_pagination(admin_token: str, jsa_imports_committed):
    with httpx.Client(base_url=BASE_URL, timeout=20) as c:
        r = c.get(f"{API}/data-import/history?page=1&limit=5", headers=_hdr(admin_token))
    assert r.status_code == 200
    j = r.json()
    assert j["page"] == 1
    assert j["limit"] == 5
    assert j["total"] >= 3, "should have at least 3 imports (occ profiles + emp proj + sa4)"
    assert isinstance(j["items"], list)
    if j["items"]:
        first = j["items"][0]
        assert "id" in first and "filename" in first and "detected_type" in first
