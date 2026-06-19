"""Phase 20.6 — VFS URL health verifier tests."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


SCRIPT_PATH = Path("/app/backend/scripts/verify_vfsglobal_urls.py")
MAP_PATH = Path("/app/backend/data/vfsglobal_country_map.json")
HEALTH_PATH = Path("/app/memory/seeds/vfsglobal_url_health.json")


def test_206_vfs_map_file_exists():
    assert MAP_PATH.exists(), f"VFS map missing at {MAP_PATH}"
    data = json.loads(MAP_PATH.read_text())
    assert "countries" in data
    assert len(data["countries"]) == 51, f"Expected 51 countries, got {len(data['countries'])}"
    # Spot check: AU + UK should have valid slugs
    assert data["countries"]["australia"] == "aus"
    assert data["countries"]["uk"] == "gbr"
    assert data["countries"]["canada"] == "can"


def test_206_vfs_health_report_structure():
    """The verifier script must produce a report with required keys."""
    assert HEALTH_PATH.exists(), f"VFS health report missing at {HEALTH_PATH}"
    report = json.loads(HEALTH_PATH.read_text())
    # Required keys
    assert "verified_at" in report
    assert "total_with_slug" in report
    assert "total_null_slug" in report
    assert "categories" in report
    assert "counts_by_category" in report
    assert "results" in report
    # Spot check
    assert report["total_with_slug"] + report["total_null_slug"] == 51
    assert report["total_with_slug"] == 25
    # Every result should have country + slug + category
    for r in report["results"]:
        assert "country" in r and "slug" in r and "category" in r
        assert "primary_url" in r
        assert r["primary_url"].startswith("https://visa.vfsglobal.com/ind/en/")


def test_206_vfs_verifier_script_executable():
    """Script must be syntactically valid Python."""
    result = subprocess.run(
        ["python3", "-m", "py_compile", str(SCRIPT_PATH)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, f"Script syntax error: {result.stderr[:300]}"


def test_206_vfs_no_dead_urls_critical_countries():
    """For critical-revenue countries (AU, CA, UK), URLs must NOT be 404."""
    report = json.loads(HEALTH_PATH.read_text())
    critical = ["australia", "canada", "uk", "new_zealand"]
    dead_critical = []
    for r in report["results"]:
        if r["country"] in critical and r["category"] == "404_dead":
            dead_critical.append(r["country"])
    assert not dead_critical, f"Critical countries have 404 VFS URLs: {dead_critical}"
