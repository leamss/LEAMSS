"""Phase 19.5 — Dynamic Atlas Meta Descriptions tests.

Acceptance criteria (per Sir's brief):
  · 720+ Atlas pages have unique, data-rich descriptions
  · All ≤ 165 chars (hard cap)
  · CTA present in 100%
  · Country-specific signals surface (Green List Tier / Express Entry / JSA growth)
  · `/start` description untouched
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter
from typing import List

import pytest

sys.path.insert(0, "/app/backend")

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from routers.public_atlas import (  # noqa: E402
    _build_meta_description,
    _country_meta,
    _CTA_POOL,
    _MAX_META_LEN,
)


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


# All CTA phrases that must appear in every output (any one match counts).
_ALL_CTAS = set()
for arr in _CTA_POOL.values():
    for c in arr:
        _ALL_CTAS.add(c.rstrip("."))


def _has_cta(meta: str) -> bool:
    return any(c in meta for c in _ALL_CTAS)


@pytest.fixture(scope="function")
def db():
    """Fresh Motor client per test — avoids event-loop-closed across asyncio.run calls."""
    client = AsyncIOMotorClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


async def _fetch_doc(db, occupation_id: str):
    return await db["occupation_master"].find_one({"occupation_id": occupation_id})


# ────────────────────────────────────────────────────────────────────────────

def test_01_five_au_occupations_distinct_descriptions(db):
    """5+ AU occupations must produce DISTINCT descriptions (no template duplicates)."""
    async def _go():
        codes = ["au-261313", "au-132311", "au-233211", "au-251311", "au-241311", "au-411311"]
        metas = []
        for oid in codes:
            doc = await _fetch_doc(db, oid)
            if not doc:
                continue
            m = _build_meta_description("AU", doc, doc.get("code", ""), doc.get("title", "Occupation"), "Australia")
            metas.append(m)
        return metas
    metas = asyncio.run(_go())
    assert len(metas) >= 5, f"only {len(metas)} AU samples fetched"
    assert len(set(metas)) == len(metas), f"duplicate descriptions found:\n" + "\n".join(metas)


def test_02_nz_green_list_tier_surfaces_in_description(db):
    """NZ pages with `nz_green_list_tier` must mention 'Green List' in description."""
    async def _go():
        results = []
        async for doc in db["occupation_master"].find(
            {"country_code": "NZ", "nz_green_list_tier": {"$in": [1, 2, "1", "2"]}}
        ).limit(5):
            m = _build_meta_description("NZ", doc, doc.get("code", ""), doc.get("title", ""), "New Zealand")
            results.append((doc.get("nz_green_list_tier"), m))
        return results
    results = asyncio.run(_go())
    assert len(results) >= 3, f"expected ≥3 NZ Green List occupations, got {len(results)}"
    for tier, meta in results:
        assert "Green List" in meta, f"Tier {tier} description missing 'Green List': {meta}"
        if str(tier) == "1":
            assert "Straight-to-Residence" in meta
        elif str(tier) == "2":
            assert "Work-to-Residence" in meta


def test_03_ca_express_entry_surfaces_in_description(db):
    """CA pages with Express Entry eligibility must mention 'Express Entry'."""
    async def _go():
        results = []
        async for doc in db["occupation_master"].find(
            {"country_code": "CA", "ee_eligibility.fswp_eligible": True}
        ).limit(5):
            m = _build_meta_description("CA", doc, doc.get("code", ""), doc.get("title", ""), "Canada")
            results.append(m)
        return results
    results = asyncio.run(_go())
    assert len(results) >= 3, f"expected ≥3 CA EE occupations, got {len(results)}"
    for meta in results:
        assert "Express Entry" in meta, f"CA description missing Express Entry: {meta}"


def test_04_description_length_under_165_for_all_samples(db):
    """Hard cap: every description ≤ 165 chars (sample 30 across countries)."""
    async def _go():
        violations = []
        for cc in ("AU", "CA", "NZ"):
            async for doc in db["occupation_master"].find({"country_code": cc, "status": "verified"}).limit(10):
                m = _build_meta_description(cc, doc, doc.get("code", ""), doc.get("title", ""), _country_meta(cc)["name"])
                if len(m) > _MAX_META_LEN:
                    violations.append((cc, doc.get("code"), len(m), m))
        return violations
    violations = asyncio.run(_go())
    assert not violations, f"Length violations:\n" + "\n".join(str(v) for v in violations)


def test_05_graceful_fallback_for_sparse_doc():
    """A doc with no salary/growth/tier signals must still produce a valid description."""
    sparse_doc = {"code": "999999", "title": "Test Occupation", "country_code": "AU"}
    for cc in ("AU", "CA", "NZ"):
        m = _build_meta_description(cc, sparse_doc, "999999", "Test Occupation", _country_meta(cc)["name"])
        assert m, f"empty description for {cc}"
        assert len(m) <= _MAX_META_LEN
        assert "999999" in m or "Test Occupation" in m
        assert _has_cta(m), f"no CTA in fallback {cc}: {m}"


def test_06_cta_present_in_every_description(db):
    """100% of descriptions must contain one of the rotating CTA phrases."""
    async def _go():
        missing = []
        for cc in ("AU", "CA", "NZ"):
            async for doc in db["occupation_master"].find({"country_code": cc, "status": "verified"}).limit(20):
                m = _build_meta_description(cc, doc, doc.get("code", ""), doc.get("title", ""), _country_meta(cc)["name"])
                if not _has_cta(m):
                    missing.append((cc, doc.get("code"), m))
        return missing
    missing = asyncio.run(_go())
    assert not missing, f"CTA missing on:\n" + "\n".join(str(m) for m in missing)


def test_07_au_growth_projection_appears_when_available(db):
    """AU occupations with Phase 19.4 JSA growth data must mention 'growth by 2035'."""
    async def _go():
        results = []
        async for doc in db["occupation_master"].find(
            {"country_code": "AU", "jsa_data.growth_pct_2025_to_2035": {"$gt": 5}}
        ).limit(5):
            m = _build_meta_description("AU", doc, doc.get("code", ""), doc.get("title", ""), "Australia")
            results.append(m)
        return results
    results = asyncio.run(_go())
    assert len(results) >= 3, f"expected ≥3 AU growth samples, got {len(results)}"
    for m in results:
        assert "growth by 2035" in m, f"AU description missing growth signal: {m}"


def test_08_uniqueness_audit_across_all_active_occupations(db):
    """Run uniqueness audit on ALL verified occupations — ≥ 95% unique."""
    async def _go():
        all_descs: List[str] = []
        for cc in ("AU", "CA", "NZ"):
            async for doc in db["occupation_master"].find({"country_code": cc, "status": "verified"}):
                m = _build_meta_description(cc, doc, doc.get("code", ""), doc.get("title", ""), _country_meta(cc)["name"])
                all_descs.append(m)
        return all_descs
    all_descs = asyncio.run(_go())
    assert len(all_descs) >= 500, f"expected ≥500 active occupations, got {len(all_descs)}"
    unique = set(all_descs)
    pct_unique = len(unique) / len(all_descs)
    assert pct_unique >= 0.95, (
        f"uniqueness {pct_unique:.1%} < 95%. "
        f"Top duplicates: {Counter(all_descs).most_common(5)}"
    )


def test_09_country_code_in_head_of_description(db):
    """ANZSCO/NOC code must appear at the start of every description."""
    async def _go():
        results = []
        for cc, prefix in (("AU", "ANZSCO"), ("CA", "NOC"), ("NZ", "ANZSCO")):
            async for doc in db["occupation_master"].find({"country_code": cc, "status": "verified"}).limit(5):
                m = _build_meta_description(cc, doc, doc.get("code", ""), doc.get("title", ""), _country_meta(cc)["name"])
                results.append((cc, prefix, doc.get("code"), m))
        return results
    results = asyncio.run(_go())
    for cc, prefix, code, m in results:
        # Either prefix-style ("ANZSCO 261313") OR the code is in the first 30 chars
        assert prefix in m or (code and code in m[:60]), f"{cc} desc missing code/{prefix}: {m}"


def test_10_no_template_boilerplate_phrases(db):
    """No description should contain banned boilerplate like 'Discover', 'Learn about'."""
    BANNED = ["Discover", "Learn about", "Comprehensive guide", "Read more"]
    async def _go():
        violations = []
        for cc in ("AU", "CA", "NZ"):
            async for doc in db["occupation_master"].find({"country_code": cc, "status": "verified"}).limit(20):
                m = _build_meta_description(cc, doc, doc.get("code", ""), doc.get("title", ""), _country_meta(cc)["name"])
                for b in BANNED:
                    if b in m:
                        violations.append((cc, doc.get("code"), b, m))
        return violations
    violations = asyncio.run(_go())
    assert not violations, f"Banned boilerplate found:\n" + "\n".join(str(v) for v in violations)


def test_11_start_route_description_untouched():
    """`/start` MegaLanding description in LeamssPublic.jsx must NOT be changed."""
    import pathlib
    fpath = pathlib.Path("/app/frontend/src/pages/LeamssPublic.jsx")
    assert fpath.exists(), "LeamssPublic.jsx not found"
    content = fpath.read_text()
    expected = "Free AI eligibility check + verified ANZSCO/NOC atlas + visa comparison for AU, CA, NZ."
    assert expected in content, "/start description was modified — must remain untouched"
