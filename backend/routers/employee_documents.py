"""Phase 21.C — Employee Documents Vault.

Provides:
- Per-employee document upload/list (RBAC: own or HR/admin)
- HR/admin verification flow (verify/reject)
- Version supersede (replace doc → bumps version, old marked superseded)
- Share token for temporary external download
- Soft-archive (delete)
- Expiring soon listing for HR alerts
"""
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.database import db, users_col
from core.auth import get_current_user

router = APIRouter(prefix="", tags=["Employee Documents"])

docs_col = db["employee_documents"]
activity_col = db["activity_log"]

VALID_DOC_TYPES = {
    "id_proof", "education", "experience_letter",
    "bank", "pf", "address_proof", "offer_letter",
    "passport", "visa", "other",
}
VALID_STATUS = {"uploaded", "verified", "rejected", "expired"}


class DocumentCreate(BaseModel):
    document_type: str
    document_name: str
    file_url: str
    file_size_bytes: Optional[int] = 0
    mime_type: Optional[str] = "application/octet-stream"
    expires_at: Optional[str] = None
    notes: Optional[str] = ""


class DocumentUpdate(BaseModel):
    status: Optional[str] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[str] = None


class DocumentShare(BaseModel):
    access_type: str = "view"  # view | download
    expires_in_hours: int = 24


def _is_manager_or_admin(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    rbac = (user.get("rbac_role") or "").lower()
    if role == "admin" or "*" in (user.get("permissions") or []):
        return True
    return any(k in rbac for k in ["admin", "owner", "head", "hr"])


def _can_access_employee_docs(user: dict, employee_id: str) -> bool:
    return user["id"] == employee_id or _is_manager_or_admin(user)


def _serialize_doc(d: dict) -> dict:
    out = dict(d)
    out.pop("_id", None)
    for k in ("created_at", "updated_at", "verified_at", "expires_at"):
        if isinstance(out.get(k), datetime):
            out[k] = out[k].isoformat()
    return out


@router.get("/employees/{employee_id}/documents")
async def list_employee_documents(
    employee_id: str,
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
):
    if not _can_access_employee_docs(current_user, employee_id):
        raise HTTPException(status_code=403, detail="No access to other employee's documents")
    q = {"employee_id": employee_id}
    if not include_archived:
        q["archived"] = {"$ne": True}
    items = []
    async for d in docs_col.find(q, {"_id": 0}).sort("created_at", -1):
        items.append(_serialize_doc(d))
    return items


@router.post("/employees/{employee_id}/documents")
async def create_document(
    employee_id: str,
    payload: DocumentCreate,
    current_user: dict = Depends(get_current_user),
):
    if not _can_access_employee_docs(current_user, employee_id):
        raise HTTPException(status_code=403, detail="No access")
    # Ensure employee exists
    emp = await users_col.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if payload.document_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type. Allowed: {sorted(VALID_DOC_TYPES)}")
    if not (payload.file_url or "").strip():
        raise HTTPException(status_code=400, detail="file_url required")

    doc = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "uploaded_by": current_user["id"],
        "uploaded_by_name": current_user.get("name"),
        "document_type": payload.document_type,
        "document_name": payload.document_name.strip() or payload.document_type,
        "file_url": payload.file_url.strip(),
        "file_size_bytes": payload.file_size_bytes or 0,
        "mime_type": payload.mime_type or "application/octet-stream",
        "version": 1,
        "superseded_by_doc_id": None,
        "status": "uploaded",
        "verified_by": None,
        "verified_at": None,
        "rejection_reason": None,
        "expires_at": payload.expires_at,
        "notes": payload.notes or "",
        "shared_with": [],
        "share_tokens": [],
        "archived": False,
        "audit_log": [{
            "action": "uploaded",
            "actor_id": current_user["id"],
            "actor_name": current_user.get("name"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await docs_col.insert_one(doc)
    await activity_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "employee_document",
        "entity_id": doc["id"],
        "action": "document_uploaded",
        "details": {"doc_type": doc["document_type"], "employee_id": employee_id},
        "created_at": datetime.now(timezone.utc),
    })
    return _serialize_doc(doc)


@router.patch("/employees/{employee_id}/documents/{doc_id}")
async def update_document_status(
    employee_id: str,
    doc_id: str,
    payload: DocumentUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Verify / reject (HR/admin only) or update expiry."""
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="HR/admin only")
    d = await docs_col.find_one({"id": doc_id, "employee_id": employee_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")

    updates: dict = {}
    if payload.status:
        if payload.status not in VALID_STATUS:
            raise HTTPException(status_code=400, detail="Invalid status")
        updates["status"] = payload.status
        if payload.status == "verified":
            updates["verified_by"] = current_user["id"]
            updates["verified_at"] = datetime.now(timezone.utc)
            updates["rejection_reason"] = None
        elif payload.status == "rejected":
            updates["rejection_reason"] = (payload.rejection_reason or "").strip() or "Rejected by HR"
            updates["verified_by"] = current_user["id"]
            updates["verified_at"] = datetime.now(timezone.utc)
    if payload.expires_at is not None:
        updates["expires_at"] = payload.expires_at
    if not updates:
        return {"message": "No changes"}

    updates["updated_at"] = datetime.now(timezone.utc)
    await docs_col.update_one(
        {"id": doc_id},
        {"$set": updates, "$push": {"audit_log": {
            "action": f"status_changed:{payload.status or 'expires_only'}",
            "actor_id": current_user["id"],
            "actor_name": current_user.get("name"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }}},
    )
    return {"message": "Updated", "fields": list(updates.keys())}


@router.post("/employees/{employee_id}/documents/{doc_id}/replace")
async def replace_document(
    employee_id: str,
    doc_id: str,
    payload: DocumentCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new version that supersedes the existing document."""
    if not _can_access_employee_docs(current_user, employee_id):
        raise HTTPException(status_code=403, detail="No access")
    old = await docs_col.find_one({"id": doc_id, "employee_id": employee_id}, {"_id": 0})
    if not old:
        raise HTTPException(status_code=404, detail="Original document not found")
    new_id = str(uuid.uuid4())
    new_doc = {
        "id": new_id,
        "employee_id": employee_id,
        "uploaded_by": current_user["id"],
        "uploaded_by_name": current_user.get("name"),
        "document_type": payload.document_type if payload.document_type in VALID_DOC_TYPES else old["document_type"],
        "document_name": payload.document_name.strip() or old["document_name"],
        "file_url": payload.file_url.strip() or old["file_url"],
        "file_size_bytes": payload.file_size_bytes or 0,
        "mime_type": payload.mime_type or old.get("mime_type", "application/octet-stream"),
        "version": (old.get("version") or 1) + 1,
        "supersedes": doc_id,
        "superseded_by_doc_id": None,
        "status": "uploaded",
        "expires_at": payload.expires_at,
        "notes": payload.notes or "",
        "shared_with": [],
        "share_tokens": [],
        "archived": False,
        "audit_log": [{
            "action": f"replaced:{doc_id}",
            "actor_id": current_user["id"],
            "actor_name": current_user.get("name"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await docs_col.insert_one(new_doc)
    await docs_col.update_one(
        {"id": doc_id},
        {"$set": {"superseded_by_doc_id": new_id, "status": "expired", "updated_at": datetime.now(timezone.utc)}},
    )
    return _serialize_doc(new_doc)


@router.post("/employees/{employee_id}/documents/{doc_id}/share")
async def share_document(
    employee_id: str,
    doc_id: str,
    payload: DocumentShare,
    current_user: dict = Depends(get_current_user),
):
    if not _can_access_employee_docs(current_user, employee_id):
        raise HTTPException(status_code=403, detail="No access")
    d = await docs_col.find_one({"id": doc_id, "employee_id": employee_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=max(1, payload.expires_in_hours))
    share_obj = {
        "token": token,
        "access_type": payload.access_type,
        "expires_at": expires_at.isoformat(),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await docs_col.update_one({"id": doc_id}, {"$push": {"share_tokens": share_obj}})
    return {"share_url": f"/api/employee-documents/share/{token}", "token": token, "expires_at": share_obj["expires_at"]}


@router.get("/employee-documents/share/{token}")
async def access_shared_document(token: str):
    """No-auth endpoint that returns doc metadata + file_url if share-token is valid + not expired."""
    d = await docs_col.find_one({"share_tokens.token": token}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Invalid or expired share link")
    matching = next((s for s in (d.get("share_tokens") or []) if s.get("token") == token), None)
    if not matching:
        raise HTTPException(status_code=404, detail="Invalid share link")
    try:
        exp = datetime.fromisoformat(matching["expires_at"].replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed share token")
    if exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Share link expired")
    return {
        "document_name": d.get("document_name"),
        "document_type": d.get("document_type"),
        "file_url": d.get("file_url"),
        "mime_type": d.get("mime_type"),
        "access_type": matching.get("access_type"),
        "expires_at": matching.get("expires_at"),
    }


@router.delete("/employees/{employee_id}/documents/{doc_id}")
async def archive_document(
    employee_id: str,
    doc_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not _can_access_employee_docs(current_user, employee_id):
        raise HTTPException(status_code=403, detail="No access")
    res = await docs_col.update_one(
        {"id": doc_id, "employee_id": employee_id},
        {"$set": {"archived": True, "updated_at": datetime.now(timezone.utc)}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Archived"}


@router.get("/employee-documents/expiring-soon")
async def documents_expiring_soon(
    days_ahead: int = 30,
    current_user: dict = Depends(get_current_user),
):
    """HR alert: docs expiring within N days."""
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="HR/admin only")
    today = datetime.now(timezone.utc).date().isoformat()
    deadline = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).date().isoformat()
    items = []
    async for d in docs_col.find(
        {
            "archived": {"$ne": True},
            "expires_at": {"$gte": today, "$lte": deadline},
            "status": {"$ne": "expired"},
        },
        {"_id": 0},
    ).sort("expires_at", 1):
        items.append(_serialize_doc(d))
    return items
