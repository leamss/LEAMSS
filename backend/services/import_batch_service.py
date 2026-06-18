"""Phase 19.6 — Centralised import-batch registry + revoke service.

Every ingestion path that mutates a "library" collection (occupation_master,
anzsco_4digit_master, industry_master, vacancy_snapshots, regional_labour_market)
registers a batch here so the admin can audit + revoke. Batches are revocable
for 24 hours (or until manually finalised).

Schema (per Sir's brief):
    {
        "id": uuid,
        "batch_id": "imp_<ts>_<sha8>",
        "ingestion_path": "phase_6.9.2_bulk" | "phase_19.4_data_import" |
                          "phase_17_kb_unified" | "phase_19.4c_industry" |
                          "phase_19.4c_vacancy",
        "endpoint": "POST /api/...",
        "uploaded_by": user_id, "uploaded_by_name": str,
        "uploaded_at": iso, "file_name": str, "file_hash": sha256,
        "file_size_bytes": int, "target_collection": str,
        "operations": {"created": [...], "updated": [...], "skipped": [...]},
        "counts": {"created": N, "updated": M, "skipped": K, "total_rows": T},
        "status": "committed" | "revoked" | "partially_revoked",
        "revoked_at": iso | null, "revoked_by": user_id | null,
        "revoke_reason": str | null,
        "is_revocable": bool, "finalised_at": iso | null,
    }
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)
COLLECTION = "import_batches"
REVOCATION_WINDOW_HOURS = 24


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    coll = db[COLLECTION]
    await coll.create_index([("uploaded_at", -1)])
    await coll.create_index([("batch_id", 1)], unique=True)
    await coll.create_index([("status", 1), ("is_revocable", 1)])
    await coll.create_index([("ingestion_path", 1)])


def _generate_batch_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"imp_{now}_{short}"


def file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def open_batch(
    db: AsyncIOMotorDatabase,
    *,
    ingestion_path: str,
    endpoint: str,
    uploaded_by: str,
    uploaded_by_name: str,
    file_name: str,
    file_hash: str,
    file_size_bytes: int,
    target_collection: str,
) -> Dict[str, Any]:
    """Create a new batch record. Returns the full batch doc — caller must
    track `batch_id` and pass it to record_* / close_batch helpers."""
    await ensure_indexes(db)
    now = datetime.now(timezone.utc)
    batch = {
        "id": str(uuid.uuid4()),
        "batch_id": _generate_batch_id(),
        "ingestion_path": ingestion_path,
        "endpoint": endpoint,
        "uploaded_by": uploaded_by,
        "uploaded_by_name": uploaded_by_name,
        "uploaded_at": now,
        "file_name": file_name,
        "file_hash": file_hash,
        "file_size_bytes": file_size_bytes,
        "target_collection": target_collection,
        "operations": {"created": [], "updated": [], "skipped": []},
        "counts": {"created": 0, "updated": 0, "skipped": 0, "total_rows": 0},
        "status": "in_progress",
        "revoked_at": None,
        "revoked_by": None,
        "revoke_reason": None,
        "is_revocable": True,
        "finalised_at": None,
    }
    await db[COLLECTION].insert_one(batch)
    return batch


def record_create(batch: Dict[str, Any], doc_id: str, key: Dict[str, Any]) -> None:
    """Track a CREATE op on the batch dict (in-memory; flushed by close_batch)."""
    batch["operations"]["created"].append({"doc_id": doc_id, "key": key})


def record_update(
    batch: Dict[str, Any], doc_id: str, key: Dict[str, Any], pre_state: Dict[str, Any]
) -> None:
    """Track an UPDATE op with the FULL pre-state snapshot for revoke."""
    # Strip Mongo _id to keep JSON-safe
    snap = {k: v for k, v in pre_state.items() if k != "_id"}
    batch["operations"]["updated"].append({
        "doc_id": doc_id, "key": key, "pre_state": snap,
    })


def record_skip(batch: Dict[str, Any], key: Dict[str, Any], reason: str) -> None:
    batch["operations"]["skipped"].append({"key": key, "reason": reason})


async def close_batch(
    db: AsyncIOMotorDatabase, batch: Dict[str, Any], *, total_rows: int, status: str = "committed",
) -> Dict[str, Any]:
    """Persist final operations + counts. Status defaults to 'committed'."""
    counts = {
        "created": len(batch["operations"]["created"]),
        "updated": len(batch["operations"]["updated"]),
        "skipped": len(batch["operations"]["skipped"]),
        "total_rows": total_rows,
    }
    await db[COLLECTION].update_one(
        {"batch_id": batch["batch_id"]},
        {"$set": {
            "operations": batch["operations"],
            "counts": counts,
            "status": status,
        }},
    )
    batch["counts"] = counts
    batch["status"] = status
    return batch


async def revoke_batch(
    db: AsyncIOMotorDatabase, batch_id: str, reason: str, user_id: str,
) -> Dict[str, Any]:
    """Replay batch ops in reverse:
      created → hard-delete
      updated → restore pre_state snapshot
      skipped → no-op
    Returns {restored_count, deleted_count, status}."""
    batch = await db[COLLECTION].find_one({"batch_id": batch_id})
    if not batch:
        raise ValueError(f"batch {batch_id} not found")
    if batch.get("status") == "revoked":
        raise ValueError(f"batch {batch_id} already revoked")
    if not batch.get("is_revocable", False):
        # Re-check 24h window for safety (finalised batches stay non-revocable forever)
        if batch.get("finalised_at"):
            raise ValueError(f"batch {batch_id} finalised — cannot revoke")
        uploaded = batch.get("uploaded_at")
        # Mongo strips tzinfo on read — re-attach UTC before comparing.
        if isinstance(uploaded, datetime) and uploaded.tzinfo is None:
            uploaded = uploaded.replace(tzinfo=timezone.utc)
        if uploaded and (datetime.now(timezone.utc) - uploaded).total_seconds() > REVOCATION_WINDOW_HOURS * 3600:
            raise ValueError(f"batch {batch_id} outside 24h revocation window")

    target = batch["target_collection"]
    coll = db[target]
    deleted = 0
    restored = 0
    errors: List[str] = []

    # Map collection → its unique-id field name (used when `key` filter is empty)
    _ID_FIELD_BY_COLL = {
        "occupation_master": "occupation_id",
        "anzsco_4digit_master": "code",
        "industry_master": "id",
        "vacancy_snapshots": "id",
        "regional_labour_market": "sa4_code",
    }
    _id_field = _ID_FIELD_BY_COLL.get(target, "id")

    # 1. Hard-delete creates (prefer natural unique key when present, else doc_id)
    for op in batch["operations"].get("created", []):
        try:
            doc_id = op.get("doc_id")
            natural_key = op.get("key") or {}
            filt = natural_key if natural_key else {_id_field: doc_id}
            r = await coll.delete_one(filt)
            deleted += r.deleted_count
        except Exception as e:  # noqa: BLE001
            errors.append(f"create-rev fail {op.get('doc_id')}: {e}")

    # 2. Restore updates
    for op in batch["operations"].get("updated", []):
        try:
            doc_id = op.get("doc_id")
            natural_key = op.get("key") or {}
            pre = op["pre_state"]
            filt = natural_key if natural_key else {_id_field: doc_id}
            await coll.replace_one(filt, pre)
            restored += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"update-rev fail {op.get('doc_id')}: {e}")

    now = datetime.now(timezone.utc)
    status = "revoked" if not errors else "partially_revoked"
    await db[COLLECTION].update_one(
        {"batch_id": batch_id},
        {"$set": {
            "status": status,
            "revoked_at": now,
            "revoked_by": user_id,
            "revoke_reason": reason,
            "revoke_summary": {"deleted": deleted, "restored": restored, "errors": errors[:20]},
            "is_revocable": False,
        }},
    )

    # Audit log
    await db["audit_logs"].insert_one({
        "id": str(uuid.uuid4()),
        "action": "import_batch.revoke",
        "user_id": user_id,
        "at": now,
        "summary": {
            "batch_id": batch_id,
            "ingestion_path": batch.get("ingestion_path"),
            "file_name": batch.get("file_name"),
            "reason": reason,
            "deleted": deleted,
            "restored": restored,
            "errors": errors[:10],
        },
    })

    return {"deleted": deleted, "restored": restored, "status": status, "errors": errors}


async def finalise_batch(db: AsyncIOMotorDatabase, batch_id: str, user_id: str) -> Dict[str, Any]:
    """Mark a batch as permanently non-revocable (admin "lock in")."""
    now = datetime.now(timezone.utc)
    r = await db[COLLECTION].update_one(
        {"batch_id": batch_id, "status": {"$ne": "revoked"}},
        {"$set": {"is_revocable": False, "finalised_at": now}},
    )
    if not r.modified_count:
        raise ValueError(f"batch {batch_id} not finalisable (revoked or missing)")
    await db["audit_logs"].insert_one({
        "id": str(uuid.uuid4()),
        "action": "import_batch.finalise",
        "user_id": user_id,
        "at": now,
        "summary": {"batch_id": batch_id},
    })
    return {"batch_id": batch_id, "finalised_at": now.isoformat()}


async def auto_expire_revocability(db: AsyncIOMotorDatabase) -> int:
    """Flip is_revocable=False on batches older than 24h. Called by APScheduler."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=REVOCATION_WINDOW_HOURS)
    r = await db[COLLECTION].update_many(
        {"is_revocable": True, "uploaded_at": {"$lt": cutoff}, "finalised_at": None},
        {"$set": {"is_revocable": False}},
    )
    return r.modified_count


async def list_batches(
    db: AsyncIOMotorDatabase, limit: int = 20, ingestion_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if ingestion_path:
        q["ingestion_path"] = ingestion_path
    cursor = db[COLLECTION].find(q, {"operations": 0}).sort("uploaded_at", -1).limit(limit)
    items = []
    async for b in cursor:
        b.pop("_id", None)
        # Refresh is_revocable on read (avoids stale 24h-window flag).
        # Mongo strips tzinfo on read — re-attach UTC before comparing.
        uploaded = b.get("uploaded_at")
        if isinstance(uploaded, datetime) and uploaded.tzinfo is None:
            uploaded = uploaded.replace(tzinfo=timezone.utc)
        if (b.get("is_revocable") and uploaded
                and (datetime.now(timezone.utc) - uploaded).total_seconds() > REVOCATION_WINDOW_HOURS * 3600
                and not b.get("finalised_at")):
            b["is_revocable"] = False
        for k in ("uploaded_at", "revoked_at", "finalised_at"):
            if isinstance(b.get(k), datetime):
                b[k] = b[k].isoformat()
        items.append(b)
    return items


async def get_batch(db: AsyncIOMotorDatabase, batch_id: str) -> Optional[Dict[str, Any]]:
    b = await db[COLLECTION].find_one({"batch_id": batch_id})
    if not b:
        return None
    b.pop("_id", None)
    for k in ("uploaded_at", "revoked_at", "finalised_at"):
        if isinstance(b.get(k), datetime):
            b[k] = b[k].isoformat()
    return b
