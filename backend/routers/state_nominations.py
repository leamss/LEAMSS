"""Phase 19.10 — State Nomination Lists upload endpoint.

Separate endpoint (NOT in /data-import/upload) because parsing state nom files
needs extra context (state code, list_type) that must come from admin's request,
not from auto-detection.

Endpoints:
  POST  /api/state-nominations/upload          — admin uploads CSV/XLSX
  POST  /api/state-nominations/{file_id}/commit — admin commits to DB
  GET   /api/state-nominations                 — list all state nom lists (admin/sales)
  GET   /api/state-nominations/by-code/{anzsco_code} — quick lookup: which states want this code?
  DELETE /api/state-nominations/{file_id}      — admin cleanup
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.auth import get_current_user
from scrapers.base import _db as db
from parsers import state_nominations as sn_parser
from services import import_batch_service as ibs, jsa_importer
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/state-nominations", tags=["state-nominations"])

STORAGE_DIR = Path(os.environ.get("STATE_NOM_STORAGE", "/app/backend/storage/state_nominations"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}
READ_ROLES = {"admin", "admin_owner", "super_admin", "sales", "partner"}


def _is_admin(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _can_read(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in READ_ROLES or "*" in (user.get("permissions") or [])


@router.post("/upload")
async def upload_state_nom(
    file: UploadFile = File(...),
    state: str = Form(...),
    list_type: str = Form("190"),
    source_url: str = Form(""),
    as_of_date: str = Form(""),
    user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    file_id = str(uuid.uuid4())
    safe_name = (file.filename or "list.csv").replace("/", "_")[:255]
    storage_path = STORAGE_DIR / f"{file_id}__{safe_name}"
    content = await file.read()
    storage_path.write_bytes(content)

    # Run parse-summary immediately (dry-run preview)
    try:
        summary = sn_parser.parse_summary(str(storage_path), state, list_type)
    except Exception as e:  # noqa: BLE001
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Parse failed: {e}") from e

    doc = {
        "id": file_id, "filename": safe_name,
        "stored_path": str(storage_path), "size_bytes": len(content),
        "state": state.upper(), "list_type": list_type.lower(),
        "source_url": source_url, "as_of_date": as_of_date,
        "preview_row_count": summary.get("row_count", 0),
        "preview_sample": summary.get("sample", []),
        "status": "uploaded",
        "uploaded_by": user.get("id") or user.get("email"),
        "uploaded_at": datetime.now(timezone.utc),
    }
    await db["state_nom_uploads"].insert_one(doc)
    return {"file_id": file_id, "filename": safe_name, "state": state.upper(),
            "list_type": list_type.lower(), "preview": summary}


@router.post("/{file_id}/commit")
async def commit_state_nom(
    file_id: str, user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    doc = await db["state_nom_uploads"].find_one({"id": file_id})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    # Parse full file
    p = Path(doc["stored_path"])
    if p.suffix.lower() in (".csv", ".tsv"):
        env = sn_parser.parse_csv(str(p), doc["state"], doc["list_type"],
                                  doc.get("source_url", ""), doc.get("as_of_date"))
    else:
        env = sn_parser.parse_xlsx(str(p), doc["state"], doc["list_type"],
                                   doc.get("source_url", ""), doc.get("as_of_date"))

    user_id = str(user.get("id") or user.get("email") or "admin")
    user_name = str(user.get("name") or user.get("email") or "admin")
    file_bytes = p.read_bytes()
    batch = await ibs.open_batch(
        db, ingestion_path=f"phase_19.10_state_nominations.{doc['state']}.{doc['list_type']}",
        endpoint="POST /api/state-nominations/{file_id}/commit",
        uploaded_by=user_id, uploaded_by_name=user_name,
        file_name=doc.get("filename"), file_hash=ibs.file_sha256(file_bytes),
        file_size_bytes=len(file_bytes), target_collection="state_nomination_lists",
    )
    summary = await jsa_importer.commit_state_nominations(db, [env])
    await ibs.close_batch(db, batch, total_rows=summary.get("codes_indexed", 0),
                          status="committed")
    # Bulk upsert path: audit-only
    await db["import_batches"].update_one(
        {"batch_id": batch["batch_id"]},
        {"$set": {"is_revocable": False, "audit_only": True,
                  "non_revocable_reason": "bulk_upsert_audit_only",
                  "summary_payload": summary}},
    )
    await db["state_nom_uploads"].update_one(
        {"id": file_id},
        {"$set": {"status": "committed", "committed_at": datetime.now(timezone.utc),
                  "commit_summary": summary, "batch_id": batch["batch_id"]}},
    )
    await log_action(db, action="state_nominations.commit",
                     user_id=user_id, user_name=user_name,
                     severity="info",
                     summary={"state": doc["state"], "list_type": doc["list_type"],
                              "codes_indexed": summary["codes_indexed"],
                              "batch_id": batch["batch_id"]})
    return {"ok": True, "summary": summary, "batch_id": batch["batch_id"]}


@router.get("")
async def list_state_noms(
    user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_read(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    items = []
    async for d in db["state_nomination_lists"].find({}, {"_id": 0}).sort("state", 1):
        if isinstance(d.get("uploaded_at"), datetime):
            d["uploaded_at"] = d["uploaded_at"].isoformat()
        items.append(d)
    return {"items": items, "count": len(items)}


@router.get("/by-code/{anzsco_code}")
async def state_demand_for_code(
    anzsco_code: str, user: Dict[str, Any] = Depends(get_current_user),
):
    """For Smart Sales Helper: which states currently want this occupation?

    Returns a flat list of {state, list_type, status, title, notes}.
    """
    if not _can_read(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    matches: List[Dict[str, Any]] = []
    async for d in db["state_nomination_lists"].find({}, {"_id": 0}):
        for entry in (d.get("codes") or []):
            if entry.get("anzsco_code") == anzsco_code:
                matches.append({
                    "state": d["state"], "list_type": d["list_type"],
                    "as_of_date": d.get("as_of_date"),
                    "status": entry.get("status"), "title": entry.get("title"),
                    "notes": entry.get("notes"),
                    "source_url": d.get("source_url"),
                })
    return {"anzsco_code": anzsco_code, "state_demand": matches,
            "states_count": len({m["state"] for m in matches}),
            "open_count": sum(1 for m in matches if m.get("status") == "open"
                              or m.get("status") == "high_demand")}


@router.delete("/{file_id}")
async def delete_state_nom(
    file_id: str, user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    doc = await db["state_nom_uploads"].find_one({"id": file_id})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        Path(doc["stored_path"]).unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass
    await db["state_nom_uploads"].delete_one({"id": file_id})
    return {"ok": True, "deleted": file_id}
