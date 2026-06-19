"""Phase 20.1 — AI Workflow Builder polish tests.

Run: cd /app/backend && pytest tests/test_phase201_ai_workflow_polish.py -v
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, List

import pytest
import requests
from pymongo import MongoClient


API_BASE = os.environ.get("API_BASE") or "http://localhost:8001"
API = f"{API_BASE}/api"
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"


@pytest.fixture(scope="module")
def headers() -> Dict[str, str]:
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def db():
    mongo_url = Path("/app/backend/.env").read_text().split("MONGO_URL=")[1].split()[0]
    db_name = Path("/app/backend/.env").read_text().split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


# ── Unit tests for service helpers (no AI call) ──────────────────────────────
def test_201_vfsglobal_url_lookup():
    from services.ai_workflow_service import vfsglobal_url
    # AU should have aus slug
    url = vfsglobal_url("australia")
    assert url == "https://visa.vfsglobal.com/ind/en/aus/"
    # Singapore is null in map
    assert vfsglobal_url("singapore") is None
    # Unknown country
    assert vfsglobal_url("zorgon") is None


def test_201_validate_workflow_quality_pass():
    from services.ai_workflow_service import validate_workflow_quality, MIN_STEPS, MIN_DOCS_PER_STEP
    wf = {
        "estimated_government_fees": "AUD $4000",
        "steps": [
            {"step_name": f"Step {i}", "required_documents": [
                {"name": f"Doc {j}"} for j in range(MIN_DOCS_PER_STEP)
            ]} for i in range(MIN_STEPS)
        ],
    }
    passed, issues = validate_workflow_quality(wf)
    assert passed, f"Expected pass, got issues: {issues}"


def test_201_validate_workflow_quality_fails_few_steps():
    from services.ai_workflow_service import validate_workflow_quality
    wf = {"estimated_government_fees": "AUD $4000", "steps": [
        {"step_name": "Only one", "required_documents": [{"name": "D1"}, {"name": "D2"}, {"name": "D3"}]}
    ]}
    passed, issues = validate_workflow_quality(wf)
    assert not passed
    assert any("steps" in i.lower() for i in issues)


def test_201_validate_workflow_quality_fails_few_docs():
    from services.ai_workflow_service import validate_workflow_quality
    wf = {
        "estimated_government_fees": "AUD $4000",
        "steps": [
            {"step_name": f"S{i}", "required_documents": [{"name": "D1"}]} for i in range(5)
        ],
    }
    passed, issues = validate_workflow_quality(wf)
    assert not passed
    assert any("docs" in i.lower() or "doc" in i.lower() for i in issues)


def test_201_parse_json_response_handles_markdown():
    from services.ai_workflow_service import parse_json_response
    raw = '```json\n{"a": 1, "b": [2, 3]}\n```'
    d = parse_json_response(raw)
    assert d == {"a": 1, "b": [2, 3]}


def test_201_parse_json_response_handles_preamble():
    from services.ai_workflow_service import parse_json_response
    raw = 'Here is the workflow:\n{"product_name": "Test", "steps": []}'
    d = parse_json_response(raw)
    assert d["product_name"] == "Test"


def test_201_build_enrichment_includes_skill_assessment_for_au_pr():
    from services.ai_workflow_service import build_enrichment_context
    ctx = build_enrichment_context(
        "australia", "pr", "homeaffairs.gov.au reference",
        "https://visa.vfsglobal.com/ind/en/aus/",
        "https://www.vetassess.com.au/",
    )
    assert "Skills Assessment" in ctx or "Skill Assessment" in ctx
    assert "vfsglobal" in ctx
    assert "VETASSESS" in ctx.replace("vetassess", "VETASSESS") or "vetassess" in ctx


def test_201_build_enrichment_excludes_skill_for_singapore_visitor():
    from services.ai_workflow_service import build_enrichment_context
    ctx = build_enrichment_context("singapore", "visitor", "ica.gov.sg ref", None, None)
    # Should explicitly say "do NOT include" skill assessment for non-AU/NZ
    assert "do NOT include" in ctx or "not an AU/NZ" in ctx.lower() or "not AU/NZ" in ctx


# ── Integration tests with backend ───────────────────────────────────────────
def test_201_verified_templates_endpoint_lists_db_templates(headers):
    """GET /verified-templates returns the Singapore visitor we just added in curl test."""
    r = requests.get(f"{API}/ai-workflow/verified-templates", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "count" in body
    # At least the Singapore one should be there (created in curl test earlier)
    assert body["count"] >= 1


def test_201_templates_merges_hardcoded_with_db(headers):
    """GET /templates returns the 10 hardcoded + any DB-verified."""
    r = requests.get(f"{API}/ai-workflow/templates", headers=headers, timeout=10)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 10  # 10 hardcoded
    db_verified = [t for t in items if t.get("source") == "db_verified"]
    # At least the Singapore test entry persists
    assert len(db_verified) >= 1


def test_201_verify_endpoint_rejects_non_admin():
    """Non-admin (no token) → 401/403."""
    r = requests.post(
        f"{API}/ai-workflow/verify",
        json={"workflow_payload": {}, "country": "X", "service_type": "y"},
        timeout=10,
    )
    assert r.status_code in (401, 403)


def test_201_verify_endpoint_requires_country_and_service(headers):
    r = requests.post(
        f"{API}/ai-workflow/verify",
        headers=headers,
        json={"workflow_payload": {}, "country": "", "service_type": ""},
        timeout=10,
    )
    assert r.status_code == 400


def test_201_verify_endpoint_persists(headers, db):
    """Phase 20.1 — verify endpoint writes to ai_workflow_templates collection."""
    test_country = "TestLand"
    test_service = "PYTEST"
    payload = {
        "workflow_payload": {
            "product_name": "TestLand - PYTEST",
            "description": "pytest fixture",
            "steps": [{"step_name": "S1", "required_documents": []}],
            "_meta": {"model_used": "anthropic/claude-sonnet-4-5-20250929"},
        },
        "country": test_country,
        "service_type": test_service,
        "notes": "Test from pytest",
    }
    r = requests.post(f"{API}/ai-workflow/verify", headers=headers, json=payload, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["id"] == "testland_pytest_verified"

    # DB check
    doc = db["ai_workflow_templates"].find_one({"id": "testland_pytest_verified"})
    assert doc is not None
    assert doc["verified"] is True
    assert doc["country"] == test_country
    assert doc["model_used"] == "anthropic/claude-sonnet-4-5-20250929"
    # Cleanup
    db["ai_workflow_templates"].delete_one({"id": "testland_pytest_verified"})
