"""Phase 20.4 — Universal Info Sheet pytests.

Covers:
1. GET /schema returns canonical 6-section structure
2. POST creates info sheet for standalone entity
3. PATCH auto-save updates personal section + completion %
4. PATCH adds dependents array (with is_migrating flag)
5. PATCH adds qualifications array
6. PATCH adds employment array
7. GET by-entity returns existing sheet
8. Duplicate POST for same entity returns 409
9. Lock endpoint admin-only
10. Locked sheet rejects PATCH from non-admin
11. Unlock restores edit access
12. Audit trail captures every patch
13. Migration handles legacy flat-keyed doc → canonical schema
14. Migration is idempotent (re-run skips already-migrated)
15. Schema includes resume section
16. Resume extraction service validates structured output
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


API_BASE = os.environ.get("API_BASE") or "http://localhost:8001"
API = f"{API_BASE}/api"
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASS = "Admin@123"
PARTNER_EMAIL = "partner@leamss.com"
PARTNER_PASS = "Partner@123"


@pytest.fixture(scope="module")
def headers():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{API}/auth/login", json={"email": PARTNER_EMAIL, "password": PARTNER_PASS}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def db():
    env = Path("/app/backend/.env").read_text()
    mongo_url = env.split("MONGO_URL=")[1].split()[0]
    db_name = env.split("DB_NAME=")[1].split()[0]
    return MongoClient(mongo_url)[db_name]


@pytest.fixture(scope="module")
def test_entity_id():
    return f"phase204test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module", autouse=True)
def cleanup(db):
    yield
    # Cleanup after all tests
    db["information_sheets"].delete_many({"entity_id": {"$regex": "^phase204test_"}})
    db["audit_logs"].delete_many({"action": {"$regex": "^info_sheet\\."},
                                  "summary.sheet_id": {"$regex": "^pha"}})


# ── 1. Schema endpoint ──
def test_204_schema_returns_six_sections(headers):
    r = requests.get(f"{API}/info-sheets/schema", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == 2
    assert len(body["sections"]) == 6
    ids = [s["id"] for s in body["sections"]]
    assert ids == ["personal", "family", "dependents", "qualifications", "employment", "resume"]


def test_204_schema_includes_resume_section(headers):
    r = requests.get(f"{API}/info-sheets/schema", headers=headers, timeout=10)
    body = r.json()
    resume_section = next(s for s in body["sections"] if s["id"] == "resume")
    assert resume_section["is_resume_section"] is True


# ── 2-3. Create + Patch ──
def test_204_create_info_sheet(headers, test_entity_id):
    r = requests.post(f"{API}/info-sheets", headers=headers,
                      json={"entity_type": "standalone", "entity_id": test_entity_id}, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["entity_type"] == "standalone"
    assert body["entity_id"] == test_entity_id
    assert body["schema_version"] == 2
    assert body["dependents"] == []
    assert body["qualifications"] == []
    assert body["employment"] == []
    assert body["resume"] == {}


def test_204_patch_personal_returns_completion(headers, test_entity_id, db):
    sheet = db["information_sheets"].find_one({"entity_id": test_entity_id})
    sheet_id = sheet["id"]
    r = requests.patch(f"{API}/info-sheets/{sheet_id}", headers=headers, json={
        "personal": {
            "given_names": "Rahul",
            "family_name": "Sharma",
            "gender": "Male",
            "date_of_birth": "1990-05-15",
            "country_of_birth": "India",
            "nationality": "Indian",
            "address": "Mumbai, India",
            "email": "rahul@example.com",
            "contact_number": "+91 9876543210",
            "passport_number": "Z1234567",
            "passport_issue_date": "2020-01-01",
            "passport_expiry_date": "2030-01-01",
            "marital_status": "Married",
            "father_name": "Ramesh Sharma",
            "mother_name": "Sunita Sharma",
        },
        "changes_summary": "filling personal details",
    }, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["completion"]["personal_percentage"] == 100
    assert body["completion"]["is_complete"] is True


def test_204_patch_dependents_with_is_migrating(headers, test_entity_id, db):
    sheet_id = db["information_sheets"].find_one({"entity_id": test_entity_id})["id"]
    r = requests.patch(f"{API}/info-sheets/{sheet_id}", headers=headers, json={
        "dependents": [
            {"full_name": "Priya Sharma", "relation": "Spouse", "gender": "Female",
             "is_migrating": True, "dob": "1992-06-20"},
            {"full_name": "Aarav Sharma", "relation": "Child", "gender": "Male",
             "is_migrating": True, "dob": "2018-03-10"},
            {"full_name": "Old Uncle", "relation": "Uncle", "is_migrating": False,
             "presently_residing_country": "India"},
        ],
    }, timeout=10)
    assert r.status_code == 200
    saved = db["information_sheets"].find_one({"id": sheet_id})
    assert len(saved["dependents"]) == 3
    assert sum(1 for d in saved["dependents"] if d["is_migrating"]) == 2


def test_204_patch_qualifications(headers, test_entity_id, db):
    sheet_id = db["information_sheets"].find_one({"entity_id": test_entity_id})["id"]
    r = requests.patch(f"{API}/info-sheets/{sheet_id}", headers=headers, json={
        "qualifications": [
            {"name": "B.Tech Computer Science", "field_of_study": "CS",
             "awarding_body": "IIT Bombay", "start_date": "2008-06-01", "end_date": "2012-05-31",
             "study_mode": "Full Time"},
        ],
    }, timeout=10)
    assert r.status_code == 200
    saved = db["information_sheets"].find_one({"id": sheet_id})
    assert len(saved["qualifications"]) == 1
    assert saved["qualifications"][0]["awarding_body"] == "IIT Bombay"


def test_204_patch_employment(headers, test_entity_id, db):
    sheet_id = db["information_sheets"].find_one({"entity_id": test_entity_id})["id"]
    r = requests.patch(f"{API}/info-sheets/{sheet_id}", headers=headers, json={
        "employment": [
            {"business_name": "TCS", "job_title": "Senior Engineer",
             "start_date": "2014-01-01", "end_date": "2020-12-31", "working_hours": "40"},
            {"business_name": "Infosys", "job_title": "Lead Architect",
             "start_date": "2021-01-15", "working_hours": "45"},
        ],
    }, timeout=10)
    assert r.status_code == 200
    saved = db["information_sheets"].find_one({"id": sheet_id})
    assert len(saved["employment"]) == 2


def test_204_get_by_entity(headers, test_entity_id):
    r = requests.get(f"{API}/info-sheets/by-entity",
                     headers=headers, params={"entity_type": "standalone", "entity_id": test_entity_id}, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["exists"] is True
    assert body["data"]["entity_id"] == test_entity_id


def test_204_duplicate_create_returns_409(headers, test_entity_id):
    r = requests.post(f"{API}/info-sheets", headers=headers,
                      json={"entity_type": "standalone", "entity_id": test_entity_id}, timeout=10)
    assert r.status_code == 409


# ── 4. Lock/Unlock ──
def test_204_lock_admin_only(partner_headers, test_entity_id, db):
    sheet_id = db["information_sheets"].find_one({"entity_id": test_entity_id})["id"]
    r = requests.post(f"{API}/info-sheets/{sheet_id}/lock", headers=partner_headers, timeout=10)
    assert r.status_code == 403


def test_204_lock_works(headers, test_entity_id, db):
    sheet_id = db["information_sheets"].find_one({"entity_id": test_entity_id})["id"]
    r = requests.post(f"{API}/info-sheets/{sheet_id}/lock", headers=headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["locked"] is True
    saved = db["information_sheets"].find_one({"id": sheet_id})
    assert saved["locked"] is True


def test_204_locked_rejects_partner_patch(partner_headers, test_entity_id, db):
    sheet_id = db["information_sheets"].find_one({"entity_id": test_entity_id})["id"]
    r = requests.patch(f"{API}/info-sheets/{sheet_id}", headers=partner_headers,
                       json={"personal": {"given_names": "TamperedName"}}, timeout=10)
    # Partner is blocked due to locked status (423) — admin can still patch
    assert r.status_code == 423


def test_204_unlock_restores_access(headers, test_entity_id, db):
    sheet_id = db["information_sheets"].find_one({"entity_id": test_entity_id})["id"]
    r = requests.post(f"{API}/info-sheets/{sheet_id}/unlock", headers=headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["locked"] is False


# ── 5. Audit trail ──
def test_204_audit_trail_captures_changes(headers, test_entity_id, db):
    sheet_id = db["information_sheets"].find_one({"entity_id": test_entity_id})["id"]
    r = requests.get(f"{API}/info-sheets/{sheet_id}/audit-trail", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 5  # create + 4 patches + lock + unlock
    # Most recent should be unlock
    actions = [e["action"] for e in body["events"]]
    assert "unlock" in actions
    assert "create" in actions
    assert "patch" in actions


# ── 6. Migration ──
@pytest.mark.asyncio
async def test_204_migration_handles_legacy_flat_doc(db):
    """Migrate a doc with old flat-keyed schema (Phase 6.7 era) → canonical schema."""
    from migrations.m20260619_phase204_info_sheets import _doc_to_canonical
    from motor.motor_asyncio import AsyncIOMotorClient

    env = Path("/app/backend/.env").read_text()
    mongo_url = env.split("MONGO_URL=")[1].split()[0]
    cli = AsyncIOMotorClient(mongo_url)
    tmpdb = cli[f"phase204_mig_test_{uuid.uuid4().hex[:8]}"]

    try:
        # Insert legacy doc
        legacy_id = str(uuid.uuid4())
        legacy_doc = {
            "id": legacy_id,
            "case_id": "case_xyz",
            "given_names": "Legacy",
            "family_name": "User",
            "gender": "Female",
            "marital_status": "Married",
            "father_name": "F",
            "mother_name": "M",
            "child_0_name": "Kid 1", "child_0_gender": "Male", "child_0_migrating": "Yes",
            "child_1_name": "Kid 2", "child_1_gender": "Female", "child_1_migrating": "No",
            "dependent_0_full_name": "Aunt", "dependent_0_relation": "Aunt", "dependent_0_migrating_with_you": "No",
            "qualification_0_name": "B.Sc", "qualification_0_field_of_study": "Math",
            "employment_0_business_name": "Acme Corp", "employment_0_job_title": "Manager",
            "created_at": datetime.now(timezone.utc),
        }
        canonical = _doc_to_canonical(legacy_doc)
        assert canonical["schema_version"] == 2
        assert canonical["case_id"] == "case_xyz"
        assert canonical["personal"]["given_names"] == "Legacy"
        assert canonical["family"] == {}
        assert len(canonical["dependents"]) == 3  # 2 children + 1 aunt
        # is_migrating boolean coercion
        kid1 = next(d for d in canonical["dependents"] if d["full_name"] == "Kid 1")
        assert kid1["is_migrating"] is True
        kid2 = next(d for d in canonical["dependents"] if d["full_name"] == "Kid 2")
        assert kid2["is_migrating"] is False
        aunt = next(d for d in canonical["dependents"] if d["full_name"] == "Aunt")
        assert aunt["is_migrating"] is False
        assert len(canonical["qualifications"]) == 1
        assert canonical["qualifications"][0]["name"] == "B.Sc"
        assert len(canonical["employment"]) == 1
        assert canonical["employment"][0]["business_name"] == "Acme Corp"
        assert canonical["resume"] == {}
    finally:
        await cli.drop_database(tmpdb.name)
        cli.close()


@pytest.mark.asyncio
async def test_204_migration_idempotent(db):
    """Re-running migration on already-migrated docs is a no-op."""
    from migrations.m20260619_phase204_info_sheets import migrate
    from motor.motor_asyncio import AsyncIOMotorClient

    env = Path("/app/backend/.env").read_text()
    mongo_url = env.split("MONGO_URL=")[1].split()[0]
    cli = AsyncIOMotorClient(mongo_url)
    tmpdb = cli[f"phase204_idem_{uuid.uuid4().hex[:8]}"]
    try:
        # Insert a v2 doc → migration should find 0 pending
        await tmpdb["information_sheets"].insert_one({
            "id": str(uuid.uuid4()),
            "entity_type": "case", "entity_id": "case_a",
            "personal": {}, "family": {}, "dependents": [],
            "qualifications": [], "employment": [], "resume": {},
            "schema_version": 2,
            "created_at": datetime.now(timezone.utc),
        })
        result = await migrate(tmpdb, user_id="test", dry_run=False)
        assert result["status"] == "already_migrated"
        assert result["pending"] == 0
        assert result["total_docs"] == 1
    finally:
        await cli.drop_database(tmpdb.name)
        cli.close()


# ── 7. Resume extraction service (unit) ──
def test_204_resume_extract_validates_output_shape():
    """Validate_extraction normalises AI output to canonical shape."""
    from services.resume_extraction_service import validate_extraction

    raw = {
        "extracted_qualifications": [
            {"degree": "BTech", "field_of_study": "CS", "confidence": 0.9},
            {"degree": "", "field_of_study": "X"},  # invalid (empty degree)
        ],
        "extracted_employment": [
            {"job_title": "Engineer", "business_name": "Acme", "is_current": True},
            {"business_name": "NoTitle"},  # invalid (no job_title)
        ],
        "summary": {"skills": ["python", "rust"], "total_years_experience": 5,
                    "certifications": ["AWS"]},
        "confidence_score": 0.85,
    }
    out = validate_extraction(raw)
    assert len(out["extracted_qualifications"]) == 1  # invalid one dropped
    assert out["extracted_qualifications"][0]["degree"] == "BTech"
    assert len(out["extracted_employment"]) == 1
    assert out["extracted_employment"][0]["job_title"] == "Engineer"
    assert out["summary"]["skills"] == ["python", "rust"]
    assert out["summary"]["total_years_experience"] == 5.0
    assert out["confidence_score"] == 0.85


def test_204_resume_parser_strips_markdown_fence():
    """parse_json_response handles markdown-wrapped JSON."""
    from services.resume_extraction_service import parse_json_response

    raw = """Here is the JSON:
```json
{"extracted_qualifications": [], "confidence_score": 0.9}
```
"""
    parsed = parse_json_response(raw)
    assert parsed["confidence_score"] == 0.9


def test_204_resume_text_extract_from_txt():
    """extract_text_from_pdf_or_docx works for TXT bytes."""
    from services.resume_extraction_service import extract_text_from_pdf_or_docx
    txt = "Hello World\nEducation: BTech 2014".encode()
    text = extract_text_from_pdf_or_docx(txt, "resume.txt")
    assert "BTech" in text


# ── 8. Partner role can also write (per RW_ROLES) ──
def test_204_partner_can_read_and_create(partner_headers, db):
    """Partner role is in RW_ROLES — can create + patch own entities."""
    eid = f"phase204test_partner_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/info-sheets", headers=partner_headers,
                      json={"entity_type": "standalone", "entity_id": eid}, timeout=10)
    assert r.status_code == 200
    sheet_id = r.json()["id"]
    # Partner cannot lock (admin-only)
    r2 = requests.post(f"{API}/info-sheets/{sheet_id}/lock", headers=partner_headers, timeout=10)
    assert r2.status_code == 403
    # Cleanup
    db["information_sheets"].delete_one({"id": sheet_id})
