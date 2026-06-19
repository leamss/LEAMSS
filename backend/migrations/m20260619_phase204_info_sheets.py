"""Phase 20.4 M1 — Universal Info Sheet schema migration.

Migrates flat-keyed `information_sheets` docs to canonical 6-section schema:
  1. personal (Personal Details)
  2. family (Family Chart)
  3. dependents (merged Children + Migrating Dependents into single array
                 with `is_migrating: bool`)
  4. qualifications (array of dicts)
  5. employment (array of dicts)
  6. resume (NEW — file_url + AI-extracted JSON + summary)

Idempotent. Registers Phase 19.6 revocable batch with full pre-state snapshots.
Backup snapshot saved to /app/memory/snapshots/ before mutation.

Old flat-key pattern (Phase 6.7 era):
  child_0_name, child_0_dob, ... child_19_*
  dependent_0_full_name, dependent_0_relation, ...
  qualification_0_name, qualification_0_field_of_study, ...
  employment_0_business_name, employment_0_address, ...

New canonical pattern (Phase 20.4):
  personal: {given_names, family_name, ...}
  family: {father_dob, ...}
  dependents: [{full_name, relation, is_migrating, ...}, ...]
  qualifications: [{name, field_of_study, ...}, ...]
  employment: [{business_name, address, ...}, ...]
  resume: {}
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

COLLECTION = "information_sheets"
SCHEMA_VERSION = 2
SNAPSHOT_DIR = Path("/app/memory/snapshots")


# Personal Details section fields (flat → personal.*)
PERSONAL_FIELDS = {
    "given_names", "family_name", "other_names", "gender", "date_of_birth",
    "country_of_birth", "city_of_birth", "address", "email", "contact_number",
    "alternative_number", "aadhaar_number", "nationality", "passport_number",
    "passport_issue_date", "passport_expiry_date", "passport_place_of_issue",
    "marital_status", "spouse_name", "father_name", "mother_name",
}

# Family Chart fields
FAMILY_FIELDS = {
    "father_dob", "father_place_of_birth", "mother_dob", "mother_place_of_birth",
    "siblings_details", "date_of_marriage", "spouse_dob", "spouse_place_of_birth",
    "spouse_passport_number", "spouse_passport_issue_date", "spouse_passport_expiry_date",
    "spouse_passport_place",
}


def _extract_section(doc: Dict[str, Any], keys: set) -> Dict[str, Any]:
    """Pull section keys from flat doc."""
    return {k: doc.get(k) for k in keys if doc.get(k) not in (None, "")}


def _extract_array_section(doc: Dict[str, Any], prefix: str, fields: List[str]) -> List[Dict[str, Any]]:
    """Pull prefixed array entries (e.g. child_0_*, child_1_*) → [{...}, ...]"""
    pattern = re.compile(rf"^{prefix}_(\d+)_(.+)$")
    by_index: Dict[int, Dict[str, Any]] = {}
    for k, v in doc.items():
        m = pattern.match(k)
        if not m:
            continue
        idx = int(m.group(1))
        field = m.group(2)
        if field not in fields:
            continue
        if v in (None, ""):
            continue
        by_index.setdefault(idx, {})[field] = v
    # Return in index order, only non-empty entries
    return [by_index[i] for i in sorted(by_index.keys()) if by_index[i]]


def _doc_to_canonical(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a flat-keyed doc to the new canonical 6-section schema.

    Preserves: id, case_id, client_id, created_at, updated_at, change_history,
    required_fields, status (legacy).
    """
    children = _extract_array_section(
        doc, "child",
        ["name", "dob", "gender", "place_of_birth", "passport_number",
         "passport_issue_date", "passport_expiry_date", "migrating"],
    )
    migrating = _extract_array_section(
        doc, "dependent",
        ["full_name", "relation", "gender", "migrating_with_you",
         "residing_country", "resident_or_citizen", "postal_code"],
    )
    # Merge into single `dependents` array with is_migrating bool
    dependents: List[Dict[str, Any]] = []
    for c in children:
        dependents.append({
            "full_name": c.get("name"),
            "relation": "Child",
            "gender": c.get("gender"),
            "dob": c.get("dob"),
            "place_of_birth": c.get("place_of_birth"),
            "passport_number": c.get("passport_number"),
            "passport_issue_date": c.get("passport_issue_date"),
            "passport_expiry_date": c.get("passport_expiry_date"),
            "is_migrating": str(c.get("migrating") or "").lower() in ("yes", "true", "y"),
            "_source": "legacy_child",
        })
    for d in migrating:
        dependents.append({
            "full_name": d.get("full_name"),
            "relation": d.get("relation"),
            "gender": d.get("gender"),
            "is_migrating": str(d.get("migrating_with_you") or "").lower() in ("yes", "true", "y"),
            "presently_residing_country": d.get("residing_country"),
            "residency_status": d.get("resident_or_citizen"),
            "postal_code": d.get("postal_code"),
            "_source": "legacy_migrating_dep",
        })

    quals = _extract_array_section(
        doc, "qualification",
        ["name", "field_of_study", "awarding_body", "institute_name",
         "institute_address", "course_length", "start_date", "end_date",
         "award_date", "study_mode"],
    )
    employment = _extract_array_section(
        doc, "employment",
        ["business_name", "address", "website", "job_title",
         "start_date", "end_date", "working_hours"],
    )

    canonical = {
        "id": doc.get("id") or str(uuid.uuid4()),
        "case_id": doc.get("case_id"),
        "client_id": doc.get("client_id"),
        "entity_type": doc.get("entity_type") or ("case" if doc.get("case_id") else "standalone"),
        "entity_id": doc.get("entity_id") or doc.get("case_id"),
        "personal": _extract_section(doc, PERSONAL_FIELDS),
        "family": _extract_section(doc, FAMILY_FIELDS),
        "dependents": dependents,
        "qualifications": quals,
        "employment": employment,
        "resume": doc.get("resume") or {},
        "schema_version": SCHEMA_VERSION,
        "status": doc.get("status", "draft"),
        "required_fields": doc.get("required_fields", []),
        "change_history": doc.get("change_history", []),
        "audit_trail": doc.get("audit_trail", []),
        "locked": doc.get("locked", False),
        "locked_by": doc.get("locked_by"),
        "locked_at": doc.get("locked_at"),
        "created_at": doc.get("created_at") or datetime.now(timezone.utc),
        "updated_at": doc.get("updated_at") or datetime.now(timezone.utc),
        "_migration_batch_id": doc.get("_migration_batch_id"),
        "_migrated_from_schema_v1_at": datetime.now(timezone.utc),
    }
    if doc.get("updated_by"):
        canonical["updated_by"] = doc["updated_by"]
    if doc.get("updated_by_role"):
        canonical["updated_by_role"] = doc["updated_by_role"]
    return canonical


async def migrate(db: AsyncIOMotorDatabase, user_id: str = "system", dry_run: bool = False) -> Dict[str, Any]:
    """Run idempotent migration.

    Skips docs already at SCHEMA_VERSION=2. Backs up entire collection
    to /app/memory/snapshots/<ts>_information_sheets_premigration.json.
    """
    from services import import_batch_service as ibs

    coll = db[COLLECTION]
    total = await coll.count_documents({})
    pending = await coll.count_documents({"schema_version": {"$ne": SCHEMA_VERSION}})

    if pending == 0:
        return {
            "ok": True, "status": "already_migrated",
            "total_docs": total, "pending": 0, "migrated": 0,
        }

    # ── Snapshot backup ──
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_path = SNAPSHOT_DIR / f"pre_phase204_info_sheets_{ts}.json"
    all_docs: List[Dict[str, Any]] = []
    async for d in coll.find({}, {"_id": 0}):
        # JSON-serialise datetimes
        for k, v in list(d.items()):
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        all_docs.append(d)
    snapshot_json = json.dumps(all_docs, indent=2, default=str)
    snapshot_path.write_text(snapshot_json)
    md5 = hashlib.md5(snapshot_json.encode()).hexdigest()
    logger.info(f"Phase 20.4 snapshot saved: {snapshot_path} (MD5={md5})")

    if dry_run:
        return {
            "ok": True, "status": "dry_run",
            "total_docs": total, "pending": pending,
            "snapshot_path": str(snapshot_path), "snapshot_md5": md5,
        }

    # ── Open Phase 19.6 batch ──
    batch = await ibs.open_batch(
        db,
        ingestion_path="phase_20.4_info_sheet_migration",
        endpoint="internal:migrations.m20260619_phase204_info_sheets",
        uploaded_by=user_id, uploaded_by_name="phase204_migration",
        file_name=f"info_sheets_v1_to_v2_{ts}",
        file_hash=md5,
        file_size_bytes=len(snapshot_json),
        target_collection=COLLECTION,
    )

    migrated_count = 0
    async for doc in coll.find({"schema_version": {"$ne": SCHEMA_VERSION}}):
        old_doc = {k: v for k, v in doc.items() if k != "_id"}
        canonical = _doc_to_canonical(old_doc)
        canonical["_migration_batch_id"] = batch["batch_id"]
        await coll.replace_one({"id": old_doc.get("id")}, canonical) \
            if old_doc.get("id") else \
            await coll.update_one({"_id": doc["_id"]}, {"$set": canonical})
        ibs.record_update(batch, canonical["id"], {"id": canonical["id"]}, old_doc)
        migrated_count += 1

    await ibs.close_batch(db, batch, total_rows=migrated_count, status="committed")

    return {
        "ok": True, "status": "migrated",
        "total_docs": total, "pending_before": pending, "migrated": migrated_count,
        "batch_id": batch["batch_id"], "snapshot_path": str(snapshot_path),
        "snapshot_md5": md5, "schema_version": SCHEMA_VERSION,
        "is_revocable": True, "revocation_window_hours": 24,
    }
