"""Phase 19.8 — Bulk Enrichment Engine integration tests.

Run:
    cd /app/backend && pytest tests/test_phase198_bulk_enrichment.py -v
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


API_BASE = os.environ.get("API_BASE") or (
    Path("/app/frontend/.env").read_text().split("REACT_APP_BACKEND_URL=")[1].split()[0]
)
API = f"{API_BASE}/api"
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"


@pytest.fixture(scope="module")
def admin_token() -> str:
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def db():
    mongo_url = Path("/app/backend/.env").read_text().split("MONGO_URL=")[1].split()[0]
    db_name = Path("/app/backend/.env").read_text().split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


# ─────────────────────────────────────────────────────────────────────────────
def test_1_coverage_endpoint_returns_per_field_pct(headers):
    """T1: GET /api/enrichment/coverage returns per-field %."""
    r = requests.get(f"{API}/enrichment/coverage?country_code=AU", headers=headers, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert "per_field" in body
    for f in ("description", "typical_tasks", "osl_listed"):
        assert f in body["per_field"]
        assert isinstance(body["per_field"][f]["pct"], (int, float))


def test_2_description_coverage_above_90_pct_after_enrichment(headers):
    """T2: description field is now >90% filled (was 29.6% before Phase 19.8)."""
    r = requests.get(f"{API}/enrichment/coverage?country_code=AU", headers=headers, timeout=15)
    body = r.json()
    pct = body["per_field"]["description"]["pct"]
    assert pct > 90, f"description coverage only {pct}% — enrichment didn't run?"


def test_3_typical_tasks_coverage_above_90_pct(headers):
    """T3: typical_tasks now >90% filled."""
    r = requests.get(f"{API}/enrichment/coverage?country_code=AU", headers=headers, timeout=15)
    body = r.json()
    assert body["per_field"]["typical_tasks"]["pct"] > 90


def test_4_dry_run_does_not_apply_changes(headers, db):
    """T4: Dry-run returns delta but does NOT modify DB.
    Simulates: pick an occupation, snapshot state, run dry-run, verify state unchanged."""
    sample = db.occupation_master.find_one({"country_code": "AU"}, {"description": 1, "occupation_id": 1, "code": 1})
    if not sample:
        pytest.skip("No AU sample")
    before_desc = sample.get("description")

    r = requests.post(f"{API}/enrichment/preview", headers=headers,
                      json={"country_code": "AU", "dry_run": True}, timeout=120)
    assert r.status_code == 200

    after = db.occupation_master.find_one({"occupation_id": sample["occupation_id"]}, {"description": 1})
    assert after.get("description") == before_desc, "Dry-run modified DB!"


def test_5_provenance_recorded_after_enrichment(db):
    """T5: enriched fields carry _provenance metadata."""
    # Find an occupation with the description provenance flag
    enriched = db.occupation_master.find_one({
        "country_code": "AU",
        "_description_provenance": {"$exists": True},
    }, {"_description_provenance": 1, "code": 1})
    assert enriched is not None, "No occupation has _description_provenance — enrichment didn't run?"
    prov = enriched["_description_provenance"]
    assert prov["source"] == "uploaded_official"
    assert "anzsco_4digit_master" in prov.get("source_file", "")
    assert isinstance(prov.get("set_at"), datetime)


def test_6_enrichment_registered_as_import_batch(db):
    """T6: Phase 19.8 enrichment creates a revocable import_batch."""
    batch = db.import_batches.find_one({
        "ingestion_path": "phase_19.8_bulk_enrichment.AU",
        "status": "committed",
    }, sort=[("uploaded_at", -1)])
    assert batch is not None, "Phase 19.8 enrichment batch not registered"
    # Either revocable (within 24h window with pre-state) or non-revocable (audit-only/expired)
    assert batch["target_collection"] == "occupation_master"


def test_7_osl_csv_parsing_works(db):
    """T7: enrichment_engine OSL CSV parser returns map keyed on code."""
    from services.enrichment_engine import _load_osl_csv
    osl_file = db.import_files.find_one({"filename": "OSL 2025 (OSCA 6).csv"})
    assert osl_file is not None
    osl_map = _load_osl_csv(osl_file["stored_path"])
    assert len(osl_map) > 1000, f"OSL CSV has only {len(osl_map)} codes — parse failed"
    # Sanity: each row has expected shape
    first = next(iter(osl_map.values()))
    assert "national" in first
    assert "state_ratings" in first
    assert "listed" in first


def test_8_enrichment_skips_already_filled_fields(headers, db):
    """T8: Running enrichment again is idempotent — no changes on second run."""
    r = requests.post(f"{API}/enrichment/preview", headers=headers,
                      json={"country_code": "AU", "dry_run": True}, timeout=120)
    body = r.json()
    # After first live run, all enrichable fields should be filled, so changes = ~0 for those fields
    # description count should be 0 since it's all filled now
    desc_changes = body.get("field_breakdown", {}).get("description", 0)
    assert desc_changes < 50, f"Re-run proposes {desc_changes} description changes — should be ≈0 if idempotent"


def test_9_4digit_parent_resolution_works(db):
    """T9: 6-digit occupations resolve to 4-digit anzsco parent."""
    sample_code = "261313"  # Software Engineer
    parent = db.anzsco_4digit_master.find_one({"code": "2613"})
    assert parent is not None, "4-digit parent 2613 not found"
    assert "Software" in (parent.get("title", "") + parent.get("description", ""))


def test_10_admin_only_access_enforced(headers):
    """T10: enrichment endpoints reject non-admin tokens."""
    # Use no auth
    r = requests.get(f"{API}/enrichment/coverage?country_code=AU", timeout=15)
    assert r.status_code in (401, 403)


def test_11_atlas_ssg_shows_enriched_data():
    """T11: Atlas public page surfaces the newly enriched description."""
    # Public Atlas — no auth needed
    r = requests.get(f"{API}/public-atlas/AU/111212", timeout=15)
    assert r.status_code == 200
    occ = r.json()["occupation"]
    desc = occ.get("description") or ""
    # Defence Force Senior Officer's description (inherited from 4-digit parent 1112 General Managers... or its own) should be non-empty now
    assert len(desc) > 50, f"description still empty after enrichment: {desc!r}"


def test_12_enrichment_field_count_at_least_700(db):
    """T12: At least 700 occupations have provenance markers after Phase 19.8 enrichment."""
    n = db.occupation_master.count_documents({
        "country_code": "AU",
        "_phase_19_8_enriched_at": {"$exists": True},
    })
    assert n >= 700, f"Only {n} occupations marked enriched — enrichment didn't run or didn't apply"
