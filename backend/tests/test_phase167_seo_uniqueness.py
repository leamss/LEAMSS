"""Phase 16.7 — Atlas occupation pages: data-driven meta_description.

Verifies that `_build_seo()` now produces:
  • UNIQUE descriptions per occupation (no two pages identical)
  • DATA-DRIVEN (real fields woven into the sentence, not boilerplate)
  • Length-controlled (120–200 chars, hard cap 200)
  • No artefacts (no "None", no empty parens, no doubled commas)
  • /start static description UNCHANGED (regression guard)

Run from /app/backend:
    pytest tests/test_phase167_seo_uniqueness.py -v
"""
from __future__ import annotations

import os
import re
import sys
import asyncio
from typing import Any, Dict, List

import httpx
import pytest
from dotenv import load_dotenv

# Ensure backend root is importable + .env loaded
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

API_BASE = os.environ.get("AUDIT_API_BASE", "http://localhost:8001/api")
_db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


# ─── Helpers ────────────────────────────────────────────────────────────────
def _get_meta(country: str, code: str) -> str:
    r = httpx.get(f"{API_BASE}/public-atlas/{country.lower()}/{code}", timeout=10)
    assert r.status_code == 200, f"{country}/{code} → {r.status_code}: {r.text[:120]}"
    return ((r.json().get("seo") or {}).get("meta_description") or "")


async def _verified_codes(country: str, n: int = 30) -> List[str]:
    cur = _db["occupation_master"].find(
        {"country_code": country, "status": "verified"},
        {"code": 1},
    ).limit(n)
    return [d["code"] async for d in cur]


def _async(coro):
    """Run an async helper in the sync test context."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ─── Tests ──────────────────────────────────────────────────────────────────
def test_descriptions_are_unique_across_countries():
    """Pull 30 codes per country → 90 total → assert ZERO duplicates."""
    codes_au = _async(_verified_codes("AU", 30))
    codes_ca = _async(_verified_codes("CA", 30))
    codes_nz = _async(_verified_codes("NZ", 30))
    assert len(codes_au) >= 25, f"Need ≥25 AU verified codes, got {len(codes_au)}"
    assert len(codes_ca) >= 25, f"Need ≥25 CA verified codes, got {len(codes_ca)}"
    assert len(codes_nz) >= 25, f"Need ≥25 NZ verified codes, got {len(codes_nz)}"

    metas: List[str] = []
    for c in codes_au:
        metas.append(_get_meta("AU", c))
    for c in codes_ca:
        metas.append(_get_meta("CA", c))
    for c in codes_nz:
        metas.append(_get_meta("NZ", c))

    # Strict cardinality check — every page must produce a distinct meta.
    dupes = [m for m in metas if metas.count(m) > 1]
    assert not dupes, f"Found {len(dupes)} duplicate descriptions, e.g. {dupes[:2]}"
    assert len(set(metas)) == len(metas)


def test_descriptions_are_data_driven_au_software_engineer():
    """261313 in AU must mention ACS + a subclass like 189/190/491."""
    m = _get_meta("AU", "261313")
    assert "ACS" in m, f"Expected ACS in AU 261313 meta: {m}"
    assert any(sc in m for sc in ("189", "190", "491")), f"No AU subclass in: {m}"
    assert "Australia" in m
    assert "LEAMSS" in m  # Subtle brand CTA present


def test_descriptions_are_data_driven_ca_software_engineer():
    """21231 in CA must mention TEER 1 + Express Entry + FSWP/CEC."""
    m = _get_meta("CA", "21231")
    assert "TEER 1" in m, f"Expected 'TEER 1' in CA 21231 meta: {m}"
    assert "Express Entry" in m, f"Expected 'Express Entry' in: {m}"
    assert ("FSWP" in m) or ("CEC" in m), f"Expected FSWP/CEC in: {m}"
    assert "NOC 21231" in m
    assert "Canada" in m


def test_descriptions_are_data_driven_nz_green_list():
    """261313 in NZ is Green List Tier 1 → meta must say so."""
    m = _get_meta("NZ", "261313")
    assert "Green List Tier 1" in m, f"Expected 'Green List Tier 1' in NZ 261313: {m}"
    assert "Residence" in m, f"Expected Residence pathway phrasing in: {m}"
    assert "New Zealand" in m


def test_descriptions_under_200_chars():
    """No description must exceed the hard cap of 200 chars."""
    codes = (
        [("AU", c) for c in _async(_verified_codes("AU", 30))]
        + [("CA", c) for c in _async(_verified_codes("CA", 30))]
        + [("NZ", c) for c in _async(_verified_codes("NZ", 30))]
    )
    over = []
    for country, c in codes:
        m = _get_meta(country, c)
        if len(m) > 200:
            over.append((country, c, len(m), m))
    assert not over, f"{len(over)} descriptions exceed 200 chars: {over[:3]}"


def test_descriptions_no_none_no_empty_brackets():
    """Graceful fallback must not leak 'None', empty parens, or dangling commas."""
    codes = (
        [("AU", c) for c in _async(_verified_codes("AU", 30))]
        + [("CA", c) for c in _async(_verified_codes("CA", 30))]
        + [("NZ", c) for c in _async(_verified_codes("NZ", 30))]
    )
    bad_patterns = [
        re.compile(r"\bNone\b"),
        re.compile(r"\(\s*\)"),
        re.compile(r"\[\s*\]"),
        re.compile(r",\s*,"),
        re.compile(r"  +"),
        re.compile(r"\s+[.,;]"),
    ]
    failures = []
    for country, c in codes:
        m = _get_meta(country, c)
        for p in bad_patterns:
            if p.search(m):
                failures.append((country, c, p.pattern, m))
                break
    assert not failures, f"Artefact found in {len(failures)} metas: {failures[:3]}"


def test_descriptions_minimum_length_120():
    """Catch under-stuffed fallback metas — anything <120 chars is too thin."""
    codes = (
        [("AU", c) for c in _async(_verified_codes("AU", 20))]
        + [("CA", c) for c in _async(_verified_codes("CA", 20))]
        + [("NZ", c) for c in _async(_verified_codes("NZ", 20))]
    )
    short = []
    for country, c in codes:
        m = _get_meta(country, c)
        if len(m) < 120:
            short.append((country, c, len(m), m))
    assert not short, f"{len(short)} descriptions under 120 chars: {short[:3]}"


def test_start_static_description_unchanged():
    """LeamssPublic.jsx /start MegaLanding SEO config must NOT be altered.
    This is a regression guard — if anyone edits the static MegaLanding
    description by mistake, this test breaks loudly."""
    front_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..",
        "frontend",
        "src",
        "pages",
        "LeamssPublic.jsx",
    )
    front_file = os.path.normpath(front_file)
    if not os.path.exists(front_file):
        pytest.skip("Frontend file not present in this environment")
    with open(front_file, "r", encoding="utf-8") as f:
        content = f.read()
    # The /start page description is part of MegaLanding's seo config.
    # We verify a specific anchor phrase ("60 seconds") that has been on the
    # /start page since Phase 14 and lives inside that SEO block.
    assert "60 seconds" in content, (
        "MegaLanding /start static SEO description appears to have been altered "
        "(expected anchor phrase '60 seconds' missing)."
    )


def test_au_meta_uses_short_authority_label():
    """ACS / EA / VETASSESS short names must appear (not just long legal names)."""
    cases = [
        ("261313", "ACS"),       # Software Engineer → ACS
        ("254499", "ANMAC"),     # Nurses → ANMAC
        ("141311", "VETASSESS"), # Hotel Manager → VETASSESS
    ]
    for code, body in cases:
        m = _get_meta("AU", code)
        assert body in m, f"Expected {body} in AU {code}: {m}"



# ─── Phase 16.7.1 Patch — single-CTA + no filler artefact regression ───────
async def _all_verified() -> List[Dict[str, str]]:
    cur = _db["occupation_master"].find(
        {"status": "verified"},
        {"code": 1, "country_code": 1},
    )
    return [{"code": d["code"], "country_code": d["country_code"]} async for d in cur]


def test_no_cta_duplicated():
    """Across ALL 1,467 verified occupations, the CTA phrase must appear
    EXACTLY ONCE per meta_description (never zero, never twice)."""
    rows = _async(_all_verified())
    assert len(rows) >= 1000, f"Expected ≥1000 verified docs, got {len(rows)}"
    failures = []
    for r in rows:
        m = _get_meta(r["country_code"], r["code"])
        count = m.count("Check eligibility with LEAMSS")
        if count != 1:
            failures.append((r["country_code"], r["code"], count, m))
    assert not failures, (
        f"CTA-count violations in {len(failures)} pages, "
        f"e.g.: {failures[:3]}"
    )


def test_no_filler_artefact():
    """Legacy 'Pathway code XXX' filler (removed in 16.7.1) must never leak
    into ANY verified-page meta_description."""
    rows = _async(_all_verified())
    failures = []
    for r in rows:
        m = _get_meta(r["country_code"], r["code"])
        if "Pathway code " in m:
            failures.append((r["country_code"], r["code"], m))
    assert not failures, f"'Pathway code' leak in {len(failures)} pages: {failures[:3]}"


def test_nz_low_data_grammatical():
    """For NZ occupations lacking Green List tier (low-data path),
    meta_description must end with EXACTLY one CTA, contain no 'Pathway code'
    filler, and be a grammatical sentence — not an ungrammatical glue.

    Includes the specific regression case `nz/331213` Joiner that triggered
    the bug."""
    cases = ["331213"]
    # Programmatically add another low-data NZ code (no Green List tier).
    async def _find_more():
        cur = _db["occupation_master"].find(
            {
                "country_code": "NZ",
                "status": "verified",
                "$or": [
                    {"nz_green_list_tier": {"$in": [None, "", 0]}},
                    {"nz_green_list_tier": {"$exists": False}},
                ],
            },
            {"code": 1},
        ).limit(5)
        return [d["code"] async for d in cur]
    cases += [c for c in _async(_find_more()) if c not in cases]

    for code in cases:
        m = _get_meta("NZ", code)
        assert m.count("Check eligibility with LEAMSS") == 1, (
            f"NZ {code} CTA count != 1: {m}"
        )
        assert m.endswith("Check eligibility with LEAMSS."), (
            f"NZ {code} doesn't end with single CTA: {m}"
        )
        assert "Pathway code " not in m, f"NZ {code} contains 'Pathway code' filler: {m}"
        # Grammatical: no truncated trailing word right before CTA
        body = m[: -len("Check eligibility with LEAMSS.")].strip()
        assert body.endswith((".", "!", "?", ":")), (
            f"NZ {code} body doesn't end with proper terminator before CTA: {m!r}"
        )
        # Length still within hard cap
        assert len(m) <= 200, f"NZ {code} over 200 chars: {len(m)}"
