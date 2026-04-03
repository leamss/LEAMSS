"""
Documents Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, date
import os
import uuid
import io
from core.database import get_db
from core.models import (
    Document, Case, CaseStep, CaseStepRequirement, AdditionalDocRequest,
    User, UserRole, DocumentStatus, Notification, AuditLog
)
from core.auth import get_current_user, require_role
from core.schemas import DocumentReview

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _log(db, user_id, action, entity_type, entity_id=None, new_value=None):
    try:
        db.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, new_value=new_value))
    except Exception:
        pass


def serialize_document(doc: Document, uploader_name: str = None) -> dict:
    """Convert document model to dict"""
    return {
        "id": doc.id,
        "file_id": doc.id,  # Using doc id as file_id for MySQL
        "filename": doc.filename,
        "case_id": doc.case_id,
        "uploaded_by": doc.uploaded_by,
        "uploaded_by_name": uploader_name,
        "upload_date": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "status": doc.status.value if doc.status else "uploaded",
        "step_name": doc.step_name,
        "document_type": doc.document_type,
        "review_comment": doc.review_comment,
        "file_size": doc.file_size,
        "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None
    }


@router.get("/case/{case_id}", response_model=List[dict])
async def get_case_documents(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all documents for a case"""
    result = await db.execute(
        select(Document, User.name)
        .join(User, Document.uploaded_by == User.id)
        .where(Document.case_id == case_id)
        .order_by(Document.uploaded_at.desc())
    )
    rows = result.all()
    
    return [serialize_document(doc, name) for doc, name in rows]


@router.post("/upload")
async def upload_document(
    case_id: str = Form(...),
    step_name: str = Form(...),
    document_type: str = Form(None),
    expiry_date: str = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document"""
    # Verify case exists
    result = await db.execute(
        select(Case)
        .options(selectinload(Case.case_manager))
        .where(Case.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Save file
    file_ext = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_dir = os.path.join(UPLOAD_DIR, "documents", case_id)
    os.makedirs(file_dir, exist_ok=True)
    file_path = os.path.join(file_dir, file_name)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Parse expiry date
    parsed_expiry = None
    if expiry_date:
        try:
            parsed_expiry = datetime.fromisoformat(expiry_date.replace('Z', '+00:00')).date()
        except:
            pass
    
    # Find the step
    step_result = await db.execute(
        select(CaseStep).where(CaseStep.case_id == case_id).where(CaseStep.step_name == step_name)
    )
    case_step = step_result.scalar_one_or_none()
    
    # Create document record
    document = Document(
        case_id=case_id,
        case_step_id=case_step.id if case_step else None,
        filename=file.filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        content_type=file.content_type,
        document_type=document_type,
        step_name=step_name,
        status=DocumentStatus.pending_review,
        uploaded_by=current_user["id"],
        expiry_date=parsed_expiry
    )
    
    db.add(document)
    
    # Log activity
    await _log(db, current_user["id"], "upload_document", "document", document.id, {"filename": file.filename, "case_id": case_id, "step_name": step_name})
    
    # Notify case manager
    if case.case_manager_id:
        notification = Notification(
            user_id=case.case_manager_id,
            title="Document Uploaded",
            message=f"A new document '{file.filename}' has been uploaded for case {case.case_id}",
            type="document_upload",
            related_id=document.id
        )
        db.add(notification)
    
    await db.commit()
    await db.refresh(document)
    
    return {"id": document.id, "message": "Document uploaded successfully"}


@router.post("/review")
async def review_document(
    request: DocumentReview,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Review a document (approve/reject)"""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.case).selectinload(Case.client))
        .where(Document.id == request.document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update document
    document.status = DocumentStatus(request.status)
    document.review_comment = request.comment
    document.reviewed_by = current_user["id"]
    document.reviewed_at = datetime.utcnow()
    
    await _log(db, current_user["id"], f"review_document_{request.status}", "document", request.document_id, {"filename": document.filename, "status": request.status})
    
    # Notify client
    if document.case and document.case.client:
        notification = Notification(
            user_id=document.case.client_id,
            title=f"Document {request.status.capitalize()}",
            message=f"Your document '{document.filename}' has been {request.status}",
            type=f"document_{request.status}",
            related_id=document.id
        )
        db.add(notification)
    
    await db.commit()
    
    return {"message": f"Document {request.status}"}


@router.get("/download/{file_id}")
async def download_document(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download a document"""
    result = await db.execute(select(Document).where(Document.id == file_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    with open(document.file_path, "rb") as f:
        content = f.read()
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type=document.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={document.filename}"}
    )


@router.get("/view/{file_id}")
async def view_document(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """View a document inline"""
    result = await db.execute(select(Document).where(Document.id == file_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    with open(document.file_path, "rb") as f:
        content = f.read()
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type=document.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"inline; filename={document.filename}"}
    )


@router.post("/upload-additional")
async def upload_additional_document(
    request_id: str = Form(...),
    case_id: str = Form(...),
    expiry_date: str = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload document for additional request"""
    # Get the request
    result = await db.execute(
        select(AdditionalDocRequest)
        .where(AdditionalDocRequest.id == request_id)
    )
    doc_request = result.scalar_one_or_none()
    
    if not doc_request:
        raise HTTPException(status_code=404, detail="Document request not found")
    
    # Save file
    file_ext = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_dir = os.path.join(UPLOAD_DIR, "documents", case_id)
    os.makedirs(file_dir, exist_ok=True)
    file_path = os.path.join(file_dir, file_name)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Parse expiry date
    parsed_expiry = None
    if expiry_date:
        try:
            parsed_expiry = datetime.fromisoformat(expiry_date.replace('Z', '+00:00')).date()
        except:
            pass
    
    # Create document record
    document = Document(
        case_id=case_id,
        filename=file.filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        content_type=file.content_type,
        document_type=doc_request.doc_type,
        step_name=f"Step {doc_request.step_order}" if doc_request.step_order else "Additional",
        status=DocumentStatus.pending_review,
        uploaded_by=current_user["id"],
        expiry_date=parsed_expiry or doc_request.expiry_date
    )
    
    db.add(document)
    await db.flush()
    
    # Update request status
    doc_request.status = DocumentStatus.uploaded
    doc_request.uploaded_document_id = document.id
    
    await db.commit()
    
    return {"id": document.id, "message": "Document uploaded successfully"}
