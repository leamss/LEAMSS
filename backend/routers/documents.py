"""Documents Router"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from core.database import documents_col, cases_col, notifications_col, audit_logs_col, users_col
from core.auth import get_current_user
from pydantic import BaseModel
from typing import Optional
import uuid, os
from datetime import datetime, timezone

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DocumentReview(BaseModel):
    document_id: str
    status: str
    comment: str = ""


async def _log(user_id, action, entity_type, entity_id=None, details=None):
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "action": action,
        "entity_type": entity_type, "entity_id": entity_id,
        "new_value": details, "created_at": datetime.now(timezone.utc)
    })


@router.get("/case/{case_id}")
async def get_case_documents(case_id: str, current_user: dict = Depends(get_current_user)):
    docs = await documents_col.find({"case_id": case_id}, {"_id": 0}).to_list(500)
    if docs:
        user_ids = set()
        for d in docs:
            if d.get("uploaded_by"): user_ids.add(d["uploaded_by"])
            if d.get("reviewed_by"): user_ids.add(d["reviewed_by"])
        users_list = await users_col.find({"id": {"$in": list(user_ids)}}, {"_id": 0, "password": 0}).to_list(500) if user_ids else []
        users_map = {u["id"]: u for u in users_list}
        for d in docs:
            uploader = users_map.get(d.get("uploaded_by"))
            d["uploader_name"] = uploader["name"] if uploader else "Unknown"
            reviewer = users_map.get(d.get("reviewed_by"))
            d["reviewer_name"] = reviewer["name"] if reviewer else None
            for f in ["uploaded_at", "reviewed_at"]:
                if isinstance(d.get(f), datetime):
                    d[f] = d[f].isoformat()
    return docs


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    case_id: str = Form(...),
    step_name: str = Form(""),
    document_type: str = Form("general"),
    current_user: dict = Depends(get_current_user)
):
    case = await cases_col.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    doc = {
        "id": file_id, "case_id": case_id, "step_name": step_name,
        "document_type": document_type, "filename": file.filename,
        "file_path": file_path, "file_size": len(content),
        "content_type": file.content_type,
        "status": "pending", "uploaded_by": current_user["id"],
        "uploaded_at": datetime.now(timezone.utc)
    }
    await documents_col.insert_one(doc)
    
    await _log(current_user["id"], "upload_document", "document", file_id, {"filename": file.filename, "case_id": case_id})
    
    # Notify case manager
    if case.get("case_manager_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": case["case_manager_id"],
            "title": "Document Uploaded",
            "message": f"New document '{file.filename}' uploaded for case {case.get('case_id', '')}",
            "type": "document_upload", "related_id": case_id,
            "read": False, "created_at": datetime.now(timezone.utc)
        })
    
    return {"id": doc["id"], "message": "Document uploaded successfully"}


@router.get("/download/{file_id}")
async def download_document(file_id: str, current_user: dict = Depends(get_current_user)):
    doc = await documents_col.find_one({"id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(doc["file_path"]):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        doc["file_path"],
        filename=doc["filename"],
        media_type=doc.get("content_type", "application/octet-stream")
    )


@router.post("/review")
async def review_document(request: DocumentReview, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")
    
    doc = await documents_col.find_one({"id": request.document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Require comment for rejection and revision_required
    if request.status in ["rejected", "revision_required"] and (not request.comment or len(request.comment.strip()) < 5):
        raise HTTPException(status_code=400, detail="Comment is required when rejecting or requesting revision (min 5 characters)")
    
    await documents_col.update_one({"id": request.document_id}, {"$set": {
        "status": request.status, "review_comment": request.comment,
        "reviewed_by": current_user["id"], "reviewer_name": current_user.get("name", ""),
        "reviewed_at": datetime.now(timezone.utc)
    }})
    
    await _log(current_user["id"], f"review_document_{request.status}", "document", request.document_id, {"filename": doc["filename"], "comment": request.comment})
    
    # Notify uploader
    if doc.get("uploaded_by"):
        status_msg = {
            "approved": "approved",
            "rejected": f"rejected. Reason: {request.comment}",
            "revision_required": f"marked for revision. Feedback: {request.comment}"
        }.get(request.status, request.status)
        
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": doc["uploaded_by"],
            "title": f"Document {request.status.replace('_', ' ').title()}",
            "message": f"Your document '{doc['filename']}' has been {status_msg}",
            "type": "document_review", "related_id": doc.get("case_id"),
            "read": False, "created_at": datetime.now(timezone.utc)
        })
    
    return {"message": f"Document {request.status}"}


@router.post("/upload-additional")
async def upload_additional_document(
    file: UploadFile = File(...),
    case_id: str = Form(...),
    request_id: str = Form(""),
    document_type: str = Form("general"),
    current_user: dict = Depends(get_current_user)
):
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    doc = {
        "id": file_id, "case_id": case_id, "document_type": document_type,
        "filename": file.filename, "file_path": file_path,
        "file_size": len(content), "content_type": file.content_type,
        "status": "pending", "uploaded_by": current_user["id"],
        "additional_request_id": request_id,
        "uploaded_at": datetime.now(timezone.utc)
    }
    await documents_col.insert_one(doc)
    return {"id": doc["id"], "message": "Document uploaded successfully"}
