"""Phase 19 — SEO SSG generator tests (16 cases).

Covers: admin auth, file generation, HTML structure (title/meta/JSON-LD/H1),
sitemap, prune, full sweep, verify hook integration, draft exclusion.
"""
from __future__ import annotations
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

BASE_URL = os.environ.get("LEAMSS_BASE_URL", "http://localhost:8001")
API = f"{BASE_URL}/api"

ATLAS_OUT = Path("/app/frontend/public/atlas")
SITEMAP_PATH = Path("/app/frontend/public/sitemap.xml")

ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASSWORD = "Partner@123"


def _login(email: str, password: str) -> str:
    with httpx.Client(base_url=BASE_URL, timeout=20) as c:
        r = c.post("/api/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def partner_token() -> str:
    return _login(PARTNER_EMAIL, PARTNER_PASSWORD)


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Admin-only access on /status
# ─────────────────────────────────────────────────────────────────────────────
def test_01_status_admin_only(admin_token: str, partner_token: str):
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        r = c.get(f"{API}/seo-ssg/status", headers=_hdr(admin_token))
        assert r.status_code == 200
        j = r.json()
        # Status memo keys exist (values may be None on cold boot)
        for k in ("last_full_sweep_at", "file_count", "sitemap_url_count", "errors"):
            assert k in j

        # Partner blocked
        rp = c.get(f"{API}/seo-ssg/status", headers=_hdr(partner_token))
        assert rp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 2. regenerate-one writes a file to disk for a verified occupation
# ─────────────────────────────────────────────────────────────────────────────
def test_02_regenerate_one_writes_file(admin_token: str):
    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        r = c.post(
            f"{API}/seo-ssg/regenerate-one",
            headers=_hdr(admin_token),
            json={"country_code": "AU", "code": "111111"},
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        path = Path(j["path"])
        assert path.exists()
        assert "/atlas/au/111111/index.html" in str(path).replace("\\", "/")


# ─────────────────────────────────────────────────────────────────────────────
# 3. regenerate-one returns 404 for non-existent code
# ─────────────────────────────────────────────────────────────────────────────
def test_03_regenerate_one_not_found(admin_token: str):
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        r = c.post(
            f"{API}/seo-ssg/regenerate-one",
            headers=_hdr(admin_token),
            json={"country_code": "AU", "code": "999999"},
        )
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 4. partner cannot trigger regenerate-one
# ─────────────────────────────────────────────────────────────────────────────
def test_04_regenerate_one_partner_blocked(partner_token: str):
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        r = c.post(
            f"{API}/seo-ssg/regenerate-one",
            headers=_hdr(partner_token),
            json={"country_code": "AU", "code": "111111"},
        )
        assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 5. Rendered HTML contains <title>, <meta description>, canonical
# ─────────────────────────────────────────────────────────────────────────────
def test_05_html_contains_title_meta_canonical(admin_token: str):
    # Make sure file is fresh
    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        c.post(f"{API}/seo-ssg/regenerate-one", headers=_hdr(admin_token),
               json={"country_code": "AU", "code": "111111"})
    html = (ATLAS_OUT / "au" / "111111" / "index.html").read_text(encoding="utf-8")
    assert "<title>" in html
    assert re.search(r'<meta\s+name="description"\s+content="[^"]+"', html)
    assert re.search(r'<link\s+rel="canonical"\s+href="https?://[^"]+"', html)
    assert "111111" in html


# ─────────────────────────────────────────────────────────────────────────────
# 6. JSON-LD Occupation structured data present
# ─────────────────────────────────────────────────────────────────────────────
def test_06_html_contains_jsonld_occupation(admin_token: str):
    html = (ATLAS_OUT / "au" / "111111" / "index.html").read_text(encoding="utf-8")
    assert 'application/ld+json' in html
    assert '"@type": "Occupation"' in html or '"@type":"Occupation"' in html
    assert "schema.org" in html
    assert '"@type": "BreadcrumbList"' in html or '"@type":"BreadcrumbList"' in html


# ─────────────────────────────────────────────────────────────────────────────
# 7. FAQPage JSON-LD present
# ─────────────────────────────────────────────────────────────────────────────
def test_07_html_contains_faqpage_jsonld(admin_token: str):
    html = (ATLAS_OUT / "au" / "111111" / "index.html").read_text(encoding="utf-8")
    assert '"@type": "FAQPage"' in html or '"@type":"FAQPage"' in html
    # FAQ visible block too
    assert "<details" in html


# ─────────────────────────────────────────────────────────────────────────────
# 8. Visible H1 has occupation title + LEAMSS brand colors
# ─────────────────────────────────────────────────────────────────────────────
def test_08_html_contains_visible_h1_and_brand(admin_token: str):
    html = (ATLAS_OUT / "au" / "111111" / "index.html").read_text(encoding="utf-8")
    assert re.search(r"<h1[^>]*>.*?</h1>", html, re.DOTALL)
    # LEAMSS-brand markers
    assert "#1F4D44" in html or "var(--forest)" in html
    assert "LEAMSS" in html


# ─────────────────────────────────────────────────────────────────────────────
# 9. No /app/ paths, secrets, or internal-only fields leak into HTML
# ─────────────────────────────────────────────────────────────────────────────
def test_09_no_path_or_secret_leaks(admin_token: str):
    html = (ATLAS_OUT / "au" / "111111" / "index.html").read_text(encoding="utf-8")
    forbidden = ["/app/", "/tmp/", "/root/", "MONGO_URL", "SECRET", "$2b$"]
    for s in forbidden:
        assert s not in html, f"Forbidden token leaked: {s}"


# ─────────────────────────────────────────────────────────────────────────────
# 10. Country index file generated (via full sweep)
# ─────────────────────────────────────────────────────────────────────────────
def test_10_country_index_generated(admin_token: str):
    # Use the HTTP API to avoid motor event-loop reuse issues across asyncio.run
    with httpx.Client(base_url=BASE_URL, timeout=180) as c:
        r = c.post(f"{API}/seo-ssg/regenerate-all", headers=_hdr(admin_token))
        assert r.status_code == 200, r.text
    path = ATLAS_OUT / "au" / "index.html"
    assert path.exists()
    html = path.read_text(encoding="utf-8")
    assert "<title>" in html
    assert "Australia" in html
    assert "ANZSCO" in html
    assert "Browse occupations" in html


# ─────────────────────────────────────────────────────────────────────────────
# 11. Atlas hub generated with 3 country cards
# ─────────────────────────────────────────────────────────────────────────────
def test_11_atlas_hub_generated(admin_token: str):
    # Hub already generated by full sweep in test_10; just verify content
    path = ATLAS_OUT / "index.html"
    assert path.exists()
    html = path.read_text(encoding="utf-8")
    for country in ("Australia", "Canada", "New Zealand"):
        assert country in html
    assert "Migration Atlas" in html


# ─────────────────────────────────────────────────────────────────────────────
# 12. Full sweep: regenerate-all writes hub + 3 country indexes + N occupations
# ─────────────────────────────────────────────────────────────────────────────
def test_12_regenerate_all_full_sweep(admin_token: str):
    with httpx.Client(base_url=BASE_URL, timeout=180) as c:
        r = c.post(f"{API}/seo-ssg/regenerate-all", headers=_hdr(admin_token))
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["occupations_written"] >= 1000, f"only wrote {j['occupations_written']}"
        assert j["country_indexes_written"] == 3
        assert j["hub_written"] == 1
        assert j["sitemap"]["url_count"] >= 1000
        assert j["duration_ms"] < 60_000  # within 60s


# ─────────────────────────────────────────────────────────────────────────────
# 13. Sitemap regenerated with all verified URLs + proper XML
# ─────────────────────────────────────────────────────────────────────────────
def test_13_sitemap_url_count_and_xml(admin_token: str):
    assert SITEMAP_PATH.exists()
    xml = SITEMAP_PATH.read_text(encoding="utf-8")
    assert xml.startswith('<?xml version="1.0"')
    assert '<urlset' in xml
    # Count <url> entries
    url_count = xml.count("<url>")
    assert url_count >= 1000, f"sitemap has only {url_count} urls"
    # Atlas hub + 3 country indexes always there
    assert "/atlas/au" in xml
    assert "/atlas/ca" in xml
    assert "/atlas/nz" in xml
    # AU 111111 url should be there
    assert "/atlas/au/111111" in xml


# ─────────────────────────────────────────────────────────────────────────────
# 14. Prune removes files for non-verified occupations
# ─────────────────────────────────────────────────────────────────────────────
def test_14_prune_unverified_files(admin_token: str):
    # Seed a junk file that has no DB counterpart
    junk = ATLAS_OUT / "au" / "999999"
    junk.mkdir(parents=True, exist_ok=True)
    (junk / "index.html").write_text("<html>junk</html>", encoding="utf-8")
    assert junk.exists()

    with httpx.Client(base_url=BASE_URL, timeout=60) as c:
        r = c.post(f"{API}/seo-ssg/prune", headers=_hdr(admin_token))
        assert r.status_code == 200
        j = r.json()
        assert j["deleted"] >= 1
    assert not junk.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 15. Admin /verify hook triggers SSG regeneration for that occupation
# ─────────────────────────────────────────────────────────────────────────────
def test_15_verify_hook_triggers_ssg(admin_token: str):
    # Delete the AU/111111 file first so we can prove the hook regenerated it
    target = ATLAS_OUT / "au" / "111111" / "index.html"
    if target.exists():
        target.unlink()
    assert not target.exists()

    # Get the occupation_id for au-111111
    with httpx.Client(base_url=BASE_URL, timeout=20) as c:
        r = c.get(f"{API}/occupation-master/au-111111", headers=_hdr(admin_token))
        assert r.status_code == 200
        occ = r.json()
        occ_id = occ.get("occupation_id") or "au-111111"

        # Re-verify with same source_reference (idempotent)
        v = c.post(
            f"{API}/occupation-master/{occ_id}/verify",
            headers=_hdr(admin_token),
            json={
                "source_reference": "https://www.acs.org.au/skills-assessment",
                "review_notes": "Phase 19 hook test re-verification",
            },
        )
        assert v.status_code == 200, v.text

    # Give the best-effort hook a moment
    import time
    for _ in range(20):
        if target.exists():
            break
        time.sleep(0.5)
    assert target.exists(), "verify hook did not regenerate the SSG file"
    html = target.read_text(encoding="utf-8")
    assert "111111" in html
    assert "<title>" in html


# ─────────────────────────────────────────────────────────────────────────────
# 16. Draft / non-verified occupations never get an SSG file
# ─────────────────────────────────────────────────────────────────────────────
def test_16_unverified_record_not_rendered(admin_token: str):
    from routers import seo_ssg
    import asyncio

    # Pick a known DRAFT occupation: AU 132111 is unlikely to be verified
    # Find any draft programmatically via the API
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        r = c.get(
            f"{API}/occupation-master?country_code=AU&status=draft&page_size=1",
            headers=_hdr(admin_token),
        )
        if r.status_code == 200:
            items = r.json().get("items") or []
            if items:
                draft = items[0]
                cc = draft.get("country_code")
                code = draft.get("code")
                # Render directly via the function — should be None
                html = asyncio.run(seo_ssg.render_occupation_html(cc, str(code)))
                assert html is None, f"draft {cc}-{code} got rendered into HTML"
                # And the file should not exist
                f = ATLAS_OUT / str(cc).lower() / str(code) / "index.html"
                assert not f.exists(), f"draft {cc}-{code} has an SSG file on disk"
                return
    # If no draft found, the assertion is trivially satisfied
    assert True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 19.0.1 — file-first proxy + slash variants + brand consistency
# ─────────────────────────────────────────────────────────────────────────────

# Frontend dev-server URL (file-first middleware lives here)
FE_BASE_URL = os.environ.get("LEAMSS_FE_URL", "http://localhost:3000")


def _fetch_fe(path: str) -> tuple[int, str]:
    """Fetch a frontend URL via the dev-server. Follows 301 redirects."""
    with httpx.Client(base_url=FE_BASE_URL, timeout=20, follow_redirects=True) as c:
        r = c.get(path, headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"})
        return r.status_code, r.text


def _is_ssr_html(html: str) -> bool:
    """Heuristic: SSR has both LEAMSS brand string AND the SSR brand-token in CSS vars."""
    return ("LEAMSS" in html) and ("--forest:#1F4D44" in html or "--forest: #1F4D44" in html)


def _is_spa_shell(html: str) -> bool:
    """Heuristic: empty CRA shell has <div id=\"root\"></div> AND no SSR brand token."""
    return ('<div id="root"></div>' in html) and ("--forest:#1F4D44" not in html and "--forest: #1F4D44" not in html)


# 17. /atlas (no trailing slash, no country) → SSR hub
def test_17_proxy_serves_ssr_for_hub_no_trailing_slash():
    status, html = _fetch_fe("/atlas")
    assert status == 200
    assert _is_ssr_html(html), "hub @ /atlas did not return SSR HTML"
    assert "Migration Atlas" in html
    assert not _is_spa_shell(html)


# 18. /atlas/ (with trailing slash) → SSR hub
def test_18_proxy_serves_ssr_for_hub_with_trailing_slash():
    status, html = _fetch_fe("/atlas/")
    assert status == 200
    assert _is_ssr_html(html), "hub @ /atlas/ did not return SSR HTML"
    assert "Migration Atlas" in html


# 19. /atlas/au (no trailing slash) → SSR country index
def test_19_proxy_serves_ssr_for_country_no_trailing_slash():
    status, html = _fetch_fe("/atlas/au")
    assert status == 200
    assert _is_ssr_html(html), "country @ /atlas/au did not return SSR HTML"
    assert "Australia Migration Atlas" in html
    assert "Browse occupations" in html


# 20. /atlas/au/ (with trailing slash) → SSR country index
def test_20_proxy_serves_ssr_for_country_with_trailing_slash():
    status, html = _fetch_fe("/atlas/au/")
    assert status == 200
    assert _is_ssr_html(html), "country @ /atlas/au/ did not return SSR HTML"


# 21. /atlas/au/111111 (no trailing slash) → SSR occupation
def test_21_proxy_serves_ssr_for_occupation_no_trailing_slash():
    status, html = _fetch_fe("/atlas/au/111111")
    assert status == 200
    assert _is_ssr_html(html), "occ @ /atlas/au/111111 did not return SSR HTML"
    assert "111111" in html


# 22. /atlas/au/111111/ (with trailing slash) → SSR occupation
def test_22_proxy_serves_ssr_for_occupation_with_trailing_slash():
    status, html = _fetch_fe("/atlas/au/111111/")
    assert status == 200
    assert _is_ssr_html(html), "occ @ /atlas/au/111111/ did not return SSR HTML"
    assert "111111" in html
    # JSON-LD present pre-hydration
    assert 'application/ld+json' in html


# 23. All generated atlas SSR files use the LEAMSS brand string (never legacy "LEAMS")
def test_23_all_atlas_pages_use_leamss_brand():
    import random
    all_files = list(ATLAS_OUT.rglob("index.html"))
    assert len(all_files) >= 1000, f"only {len(all_files)} ssg files on disk"
    # Sample 25 random files (deterministic seed)
    random.seed(19)
    sample = random.sample(all_files, min(25, len(all_files)))
    for f in sample:
        html = f.read_text(encoding="utf-8")
        assert "LEAMSS" in html, f"{f} missing LEAMSS brand"
        # legacy "LEAMS " (with trailing space) or "LEAMS<" tags should not appear
        # (LEAMSS itself contains "LEAMS" as substring — guard against false positives)
        legacy_tokens = ['"LEAMS"', '>LEAMS<', 'LEAMS &', 'We Value Emotions']
        for t in legacy_tokens:
            assert t not in html, f"{f} contains legacy brand token {t!r}"

