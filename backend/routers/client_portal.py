"""Step 2 — Client Portal data router.

Client-scoped endpoints (require client JWT from `routers.client_auth`):
  GET  /api/client-portal/me           — same as /client-auth/me but namespaced
  GET  /api/client-portal/overview     — dashboard timeline + next action
  GET  /api/client-portal/info-sheet   — own info sheet
  PATCH /api/client-portal/info-sheet  — auto-save
  GET  /api/client-portal/documents    — list own documents
  POST /api/client-portal/documents    — upload document
  DELETE /api/client-portal/documents/{id}
  GET  /api/client-portal/proposal     — receive proposal (if sent)
  POST /api/client-portal/proposal/{id}/accept
  POST /api/client-portal/proposal/{id}/decline

X5 (Option D): Admin/CM/sales preview endpoint:
  GET  /api/admin/client-portal-preview/{client_id}/overview
  GET  /api/admin/client-portal-preview/{client_id}/info-sheet
  GET  /api/admin/client-portal-preview/{client_id}/documents
  GET  /api/admin/client-portal-preview/{client_id}/proposal
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                      Body)
from pydantic import BaseModel, Field

from core.database import db
from routers.client_auth import get_current_client
from services.audit_service import log_action
from services import import_batch_service as ibs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/client-portal", tags=["Step 2 Client Portal"])

DOCS_COLL = "client_documents"
PROP_COLL = "proposals"
INFO_SHEETS_COLL = "information_sheets"
PA_COLL = "pre_assessments"
UPLOAD_DIR = "/app/backend/uploads/client_docs"

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME = {"application/pdf", "image/png", "image/jpeg", "image/webp",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

DOC_CATEGORIES = ["identity", "qualifications", "employment", "english_test", "other"]


# ── /me + /overview ───────────────────────────────────────────────────────────
@router.get("/overview")
async def overview(client: Dict[str, Any] = Depends(get_current_client)):
    """Client dashboard overview — status timeline + next action recommendation."""
    cid = client["client_id"]

    portal = client["portal"]
    pa = await db[PA_COLL].find_one({"$or": [{"client_user_id": cid},
                                              {"created_by_user_id": cid},
                                              {"client_email": client.get("email")}]},
                                     sort=[("created_at", -1)])
    sheet = await db[INFO_SHEETS_COLL].find_one(
        {"id": portal.get("info_sheet_id")}, {"_id": 0}
    ) if portal.get("info_sheet_id") else None

    doc_count = await db[DOCS_COLL].count_documents({"client_id": cid})
    proposal = await db[PROP_COLL].find_one(
        {"client_id": cid, "status": {"$in": ["sent", "accepted", "declined"]}},
        {"_id": 0}, sort=[("created_at", -1)],
    )

    # Build 7-step timeline
    timeline = []

    paid = bool(pa and pa.get("payment_status") in ("paid", "completed"))
    timeline.append({"stage": "Pre-Assessment Paid",
                     "status": "done" if paid else "pending",
                     "at": pa.get("paid_at") if paid else None})

    sheet_done = bool(sheet and (sheet.get("personal", {}).get("given_names")))
    timeline.append({"stage": "Info Sheet Started",
                     "status": "done" if sheet_done else "pending",
                     "at": sheet.get("updated_at").isoformat() if sheet_done and isinstance(sheet.get("updated_at"), datetime) else None})

    timeline.append({"stage": "Documents Uploaded",
                     "status": "done" if doc_count >= 3 else ("in_progress" if doc_count > 0 else "pending"),
                     "count": doc_count})

    review = await db["pa_reviews"].find_one(
        {"$or": [{"client_id": cid}, {"pa_id": pa["id"] if pa else None}]},
        sort=[("created_at", -1)],
    )
    review_status = (review or {}).get("status", "pending")
    timeline.append({"stage": "Under Admin Review",
                     "status": "done" if review_status == "approved" else (
                         "in_progress" if review_status == "pending" else "pending"),
                     "review_status": review_status})

    timeline.append({"stage": "Proposal Received",
                     "status": "done" if proposal and proposal.get("status") in ("sent", "accepted", "declined") else "pending",
                     "at": proposal.get("created_at").isoformat() if proposal and isinstance(proposal.get("created_at"), datetime) else None})

    accepted = bool(proposal and proposal.get("status") == "accepted")
    timeline.append({"stage": "Proposal Accepted",
                     "status": "done" if accepted else "pending"})

    timeline.append({"stage": "Full Case Active",
                     "status": "done" if accepted else "pending"})

    # Next-action recommendation
    next_action = None
    if not sheet_done:
        next_action = {"label": "Complete your Info Sheet",
                       "subtitle": "Fill personal + qualifications sections to start your case",
                       "tab": "info_sheet"}
    elif doc_count < 3:
        next_action = {"label": f"Upload required documents ({doc_count} so far)",
                       "subtitle": "We need passport + qualifications + employment proofs",
                       "tab": "documents"}
    elif review_status == "pending":
        next_action = {"label": "Waiting for admin review",
                       "subtitle": "Our team is verifying your documents (1-2 business days)",
                       "tab": "overview"}
    elif proposal and proposal.get("status") == "sent":
        next_action = {"label": "Review your proposal",
                       "subtitle": "Your customised migration plan is ready",
                       "tab": "proposal"}
    elif accepted:
        next_action = {"label": "Welcome to LEAMSS!",
                       "subtitle": "Your full case is active — case manager will contact shortly",
                       "tab": "overview"}

    return {
        "client": {"id": cid, "name": client.get("name"), "email": client.get("email"),
                   "product_id": portal.get("product_id")},
        "timeline": timeline,
        "next_action": next_action,
        "summary": {
            "doc_count": doc_count,
            "has_info_sheet": sheet is not None,
            "has_proposal": proposal is not None,
            "proposal_status": (proposal or {}).get("status"),
        },
    }


# ── Info Sheet ────────────────────────────────────────────────────────────────
@router.get("/info-sheet")
async def get_info_sheet(client: Dict[str, Any] = Depends(get_current_client)):
    sheet_id = client["portal"].get("info_sheet_id")
    if not sheet_id:
        raise HTTPException(404, "No info sheet provisioned yet")
    sheet = await db[INFO_SHEETS_COLL].find_one({"id": sheet_id}, {"_id": 0})
    if not sheet:
        raise HTTPException(404, "Info sheet not found")
    for k, v in list(sheet.items()):
        if isinstance(v, datetime):
            sheet[k] = v.isoformat()
    return sheet


@router.patch("/info-sheet")
async def patch_info_sheet(
    payload: Dict[str, Any] = Body(...),
    client: Dict[str, Any] = Depends(get_current_client),
):
    sheet_id = client["portal"].get("info_sheet_id")
    if not sheet_id:
        raise HTTPException(404, "No info sheet provisioned yet")
    sheet = await db[INFO_SHEETS_COLL].find_one({"id": sheet_id}, {"locked": 1})
    if not sheet:
        raise HTTPException(404, "Info sheet not found")
    if sheet.get("locked"):
        raise HTTPException(409, "This info sheet has been locked by LEAMSS admin.")

    allowed = {"personal", "family", "dependents", "qualifications",
               "employment", "resume"}
    set_fields = {k: v for k, v in payload.items() if k in allowed}
    if not set_fields:
        raise HTTPException(400, "No valid fields to update")
    set_fields["updated_at"] = datetime.now(timezone.utc)
    set_fields["updated_by"] = "client_self"
    await db[INFO_SHEETS_COLL].update_one({"id": sheet_id}, {"$set": set_fields})
    return {"ok": True, "updated": list(set_fields.keys())}


# ── Documents ─────────────────────────────────────────────────────────────────
@router.get("/documents")
async def list_documents(client: Dict[str, Any] = Depends(get_current_client)):
    docs = []
    async for d in db[DOCS_COLL].find({"client_id": client["client_id"]},
                                       {"_id": 0}).sort("uploaded_at", -1):
        for k, v in list(d.items()):
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        docs.append(d)
    # Group by category for UI
    by_cat: Dict[str, List[Dict[str, Any]]] = {c: [] for c in DOC_CATEGORIES}
    for d in docs:
        cat = d.get("document_type", "other")
        if cat not in by_cat:
            cat = "other"
        by_cat[cat].append(d)
    return {"documents": docs, "by_category": by_cat,
            "categories": DOC_CATEGORIES, "total": len(docs)}


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    document_name: Optional[str] = Form(None),
    client: Dict[str, Any] = Depends(get_current_client),
):
    if document_type not in DOC_CATEGORIES:
        raise HTTPException(400, f"document_type must be one of {DOC_CATEGORIES}")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, f"Unsupported file type {file.content_type}")

    cid = client["client_id"]
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = (file.filename or "upload").replace("/", "_").replace("\\", "_")
    doc_id = str(uuid.uuid4())
    stored = f"{cid}_{doc_id}_{safe_name}"
    full_path = os.path.join(UPLOAD_DIR, stored)
    with open(full_path, "wb") as f:
        f.write(contents)

    body = f"upload_{cid}_{doc_id}".encode()
    batch = await ibs.open_batch(
        db, ingestion_path="step2_client_portal.upload_document",
        endpoint="POST /api/client-portal/documents",
        uploaded_by=cid, uploaded_by_name=client.get("name") or "Client",
        file_name=safe_name, file_hash=ibs.file_sha256(body),
        file_size_bytes=len(contents), target_collection=DOCS_COLL,
    )

    doc = {
        "id": doc_id, "client_id": cid,
        "product_id": client["portal"].get("product_id"),
        "document_type": document_type,
        "document_name": document_name or safe_name,
        "file_path": full_path,
        "file_url": f"/api/client-portal/documents/{doc_id}/download",
        "file_size_bytes": len(contents),
        "mime_type": file.content_type,
        "uploaded_at": datetime.now(timezone.utc),
        "uploaded_by_role": "client",
        "uploaded_by_id": cid,
        "status": "uploaded",
        "verified_by": None, "verified_at": None,
        "rejection_reason": None,
        "_provisioning_batch_id": batch["batch_id"],
    }
    await db[DOCS_COLL].insert_one(doc)
    ibs.record_create(batch, doc_id, {"document_type": document_type, "size": len(contents)})
    await ibs.close_batch(db, batch, total_rows=1, status="committed")

    await log_action(db, action="client.document_upload", user_id=cid,
                     severity="info",
                     summary={"document_id": doc_id, "type": document_type,
                              "size_bytes": len(contents)})
    return {"ok": True, "document_id": doc_id, "batch_id": batch["batch_id"]}


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str, client: Dict[str, Any] = Depends(get_current_client),
):
    doc = await db[DOCS_COLL].find_one({"id": doc_id, "client_id": client["client_id"]})
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.get("status") == "verified":
        raise HTTPException(409, "Cannot delete a verified document. Contact LEAMSS.")
    # Remove file from disk
    try:
        if doc.get("file_path") and os.path.exists(doc["file_path"]):
            os.remove(doc["file_path"])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[Step2] file delete failed: {e!r}")
    await db[DOCS_COLL].delete_one({"id": doc_id})
    await log_action(db, action="client.document_delete",
                     user_id=client["client_id"], severity="info",
                     summary={"document_id": doc_id})
    return {"ok": True}


# ── Proposal ──────────────────────────────────────────────────────────────────
@router.get("/proposal")
async def get_my_proposal(client: Dict[str, Any] = Depends(get_current_client)):
    proposal = await db[PROP_COLL].find_one(
        {"client_id": client["client_id"],
         "status": {"$in": ["sent", "accepted", "declined"]}},
        {"_id": 0}, sort=[("created_at", -1)],
    )
    if not proposal:
        return {"proposal": None,
                "message": "Your proposal will appear here after admin approval."}
    for k, v in list(proposal.items()):
        if isinstance(v, datetime):
            proposal[k] = v.isoformat()
    return {"proposal": proposal}


class AcceptIn(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=500)


class DeclineIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.post("/proposal/{proposal_id}/accept")
async def accept_proposal(
    proposal_id: str, body: AcceptIn = Body(default=AcceptIn()),
    client: Dict[str, Any] = Depends(get_current_client),
):
    p = await db[PROP_COLL].find_one({"id": proposal_id})
    if not p:
        raise HTTPException(404, "Proposal not found")
    if p.get("client_id") != client["client_id"]:
        raise HTTPException(403, "This proposal does not belong to you")
    if p.get("status") not in ("sent",):
        raise HTTPException(409, f"Cannot accept — current status: {p.get('status')}")
    await db[PROP_COLL].update_one(
        {"id": proposal_id},
        {"$set": {"status": "accepted",
                  "accepted_at": datetime.now(timezone.utc),
                  "accepted_by": "client_self",
                  "accept_notes": body.notes}},
    )
    await log_action(db, action="proposal.accepted_by_client",
                     user_id=client["client_id"], severity="info",
                     summary={"proposal_id": proposal_id})
    return {"ok": True, "status": "accepted"}


@router.post("/proposal/{proposal_id}/decline")
async def decline_proposal(
    proposal_id: str, body: DeclineIn,
    client: Dict[str, Any] = Depends(get_current_client),
):
    p = await db[PROP_COLL].find_one({"id": proposal_id})
    if not p:
        raise HTTPException(404, "Proposal not found")
    if p.get("client_id") != client["client_id"]:
        raise HTTPException(403, "This proposal does not belong to you")
    if p.get("status") not in ("sent",):
        raise HTTPException(409, f"Cannot decline — current status: {p.get('status')}")
    await db[PROP_COLL].update_one(
        {"id": proposal_id},
        {"$set": {"status": "declined",
                  "declined_at": datetime.now(timezone.utc),
                  "declined_by": "client_self",
                  "decline_reason": body.reason}},
    )
    await log_action(db, action="proposal.declined_by_client",
                     user_id=client["client_id"], severity="info",
                     summary={"proposal_id": proposal_id, "reason_len": len(body.reason)})
    return {"ok": True, "status": "declined"}
