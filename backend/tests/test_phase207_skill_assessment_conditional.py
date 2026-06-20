"""Phase 20.7 — Skill Assessment conditional rendering tests."""
from __future__ import annotations

import uuid
from pathlib import Path
import pytest
import requests
from pymongo import MongoClient


API_BASE = "http://localhost:8001"
API = f"{API_BASE}/api"


@pytest.fixture(scope="module")
def headers():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def db():
    env = Path("/app/backend/.env").read_text()
    mongo_url = env.split("MONGO_URL=")[1].split()[0]
    db_name = env.split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


def test_207_supports_skill_assessment_helper():
    from services.country_capabilities import supports_skill_assessment
    assert supports_skill_assessment("AU") is True
    assert supports_skill_assessment("au") is True
    assert supports_skill_assessment("NZ") is True
    assert supports_skill_assessment("USA") is False
    assert supports_skill_assessment("CA") is False
    assert supports_skill_assessment("") is False
    assert supports_skill_assessment(None) is False


def test_207_filter_authorities_returns_empty_for_non_au_nz():
    from services.country_capabilities import filter_authorities_by_country
    authorities = [
        {"code": "ACS", "country_code": "AU"},
        {"code": "NZQA", "country_code": "NZ"},
    ]
    assert filter_authorities_by_country(authorities, "USA") == []
    assert filter_authorities_by_country(authorities, "CA") == []
    au_only = filter_authorities_by_country(authorities, "AU")
    assert len(au_only) == 1
    assert au_only[0]["code"] == "ACS"


def test_207_patch_product_rejects_non_au_nz_with_assessing_body(headers, db):
    """PATCH product with country=USA + assessing_body_code → 400."""
    pid = f"phase207test_{uuid.uuid4().hex[:8]}"
    db["products"].insert_one({
        "id": pid, "name": "Phase207_USA_Product",
        "country": "USA", "service_type": "H1B",
        "is_active": True, "is_deleted": False,
    })
    try:
        r = requests.patch(f"{API}/products/{pid}", headers=headers,
                          json={"assessing_body_code": "ACS"}, timeout=10)
        assert r.status_code == 400
        assert "AU/NZ" in r.json().get("detail", "")
    finally:
        db["products"].delete_one({"id": pid})


def test_207_patch_product_accepts_au_with_assessing_body(headers, db):
    """PATCH product with country=Australia + valid assessing_body_code → 200."""
    pid = f"phase207test_au_{uuid.uuid4().hex[:8]}"
    db["products"].insert_one({
        "id": pid, "name": "Phase207_AU_Product",
        "country": "Australia", "service_type": "PR",
        "is_active": True, "is_deleted": False,
    })
    try:
        r = requests.patch(f"{API}/products/{pid}", headers=headers,
                          json={"assessing_body_code": "ACS"}, timeout=10)
        assert r.status_code == 200, r.text
    finally:
        db["products"].delete_one({"id": pid})
