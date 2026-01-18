"""
Document management routes for LEAMSS Portal
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
import io

from core.database import db, fs
from core.auth import get_current_user, require_role, UserRole
from core.models import DocumentResponse, DocumentReview
from services.notification_service import create_notification

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload")
async def upload_document(
    case_id: str = Form(...),
    step_name: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    additional_doc_id: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(get_current_user)
):
    """Upload a document for a case"""
    case = await db.cases.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check access
    if user["role"] == UserRole.CLIENT and case["client_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    steps = case.get("steps", [])
    actual_step_name = step_name
    is_additional_doc = additional_doc_id is not None
    
    # For additional documents, find the step from the request
    if is_additional_doc:
        additional_requests = case.get("additional_doc_requests", [])
        request = next((r for r in additional_requests if r.get("id") == additional_doc_id), None)
        if request:
            # Use the step_name from the request if available
            actual_step_name = request.get("step_name") or step_name
            # If step_name is a document name, try to find the actual step
            if not any(s["step_name"] == actual_step_name for s in steps):
                # Use step_order to find the step
                step_order = request.get("step_order")
                if step_order:
                    step_by_order = next((s for s in steps if s.get("step_order") == step_order), None)
                    if step_by_order:
                        actual_step_name = step_by_order["step_name"]
    
    # Find the step
    step = next((s for s in steps if s["step_name"] == actual_step_name), None)
    
    # If step still not found for additional docs, use the first unlocked step
    if not step and is_additional_doc:
        step = next((s for s in steps if not s.get("is_locked", True)), None)
        if step:
            actual_step_name = step["step_name"]
    
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    # Only check step lock for non-additional documents
    if not is_additional_doc and step.get("is_locked", True):
        raise HTTPException(status_code=400, detail="This step is locked. Complete previous steps first.")
    
    # Upload file to GridFS
    content = await file.read()
    file_id = await fs.upload_from_stream(
        file.filename,
        io.BytesIO(content),
        metadata={
            "content_type": file.content_type,
            "case_id": case_id,
            "step_name": actual_step_name,
            "document_type": document_type,
            "additional_doc_id": additional_doc_id
        }
    )
    
    # Create document record
    doc_record = {
        "id": str(ObjectId()),
        "file_id": str(file_id),
        "filename": file.filename,
        "case_id": case_id,
        "step_name": actual_step_name,
        "document_type": document_type,
        "uploaded_by": user["id"],
        "uploaded_by_name": user["name"],
        "upload_date": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
        "file_size": len(content),
        "additional_doc_id": additional_doc_id
    }
    await db.documents.insert_one(doc_record)
    
    # Update step's uploaded_documents
    step["uploaded_documents"].append(doc_record["id"])
    
    # Update case steps
    step_index = next(i for i, s in enumerate(steps) if s["step_name"] == actual_step_name)
    steps[step_index] = step
    await db.cases.update_one({"id": case_id}, {"$set": {"steps": steps}})
    
    # Update additional doc request status if applicable
    if additional_doc_id:
        await db.cases.update_one(
            {"id": case_id, "additional_doc_requests.id": additional_doc_id},
            {
                "$set": {
                    "additional_doc_requests.$.status": "uploaded",
                    "additional_doc_requests.$.uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "additional_doc_requests.$.document_id": doc_record["id"]
                }
            }
        )
    
    # Notify case manager
    notification_msg = f"Client {case['client_name']} uploaded "
    if is_additional_doc:
        notification_msg += f"additional document '{document_type}' for '{actual_step_name}'"
    else:
        notification_msg += f"'{document_type}' for step '{actual_step_name}'"
    
    await create_notification(
        case["case_manager_id"],
        "New Document Uploaded",
        notification_msg,
        "doc_uploaded",
        case_id
    )
    
    return DocumentResponse(**doc_record)


@router.get("/download/{file_id}")
async def download_document(file_id: str, user: dict = Depends(get_current_user)):
    """Download a document"""
    try:
        grid_out = await fs.open_download_stream(ObjectId(file_id))
        content = await grid_out.read()
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=grid_out.metadata.get("content_type", "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename={grid_out.filename}"}
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/view/{file_id}")
async def view_document(file_id: str, user: dict = Depends(get_current_user)):
    """View a document inline (for PDFs, images, etc.)"""
    try:
        grid_out = await fs.open_download_stream(ObjectId(file_id))
        content = await grid_out.read()
        content_type = grid_out.metadata.get("content_type", "application/octet-stream")
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename={grid_out.filename}"}
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/case/{case_id}", response_model=List[DocumentResponse])
async def get_case_documents(case_id: str, user: dict = Depends(get_current_user)):
    """Get all documents for a case"""
    docs = await db.documents.find({"case_id": case_id}, {"_id": 0}).to_list(1000)
    return [DocumentResponse(**d) for d in docs]


@router.post("/review")
async def review_document(
    review: DocumentReview, 
    background_tasks: BackgroundTasks, 
    user: dict = Depends(require_role([UserRole.CASE_MANAGER, UserRole.ADMIN]))
):
    """Review (approve/reject) a document"""
    doc = await db.documents.find_one({"id": review.document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    update_data = {
        "status": review.status,
        "reviewed_by": user["id"],
        "reviewed_by_name": user["name"],
        "reviewed_at": datetime.now(timezone.utc).isoformat()
    }
    if review.comment:
        update_data["review_comment"] = review.comment
    
    await db.documents.update_one({"id": review.document_id}, {"$set": update_data})
    
    # Get case and notify client
    case = await db.cases.find_one({"id": doc["case_id"]})
    if case:
        status_text = "approved" if review.status == "approved" else "needs revision"
        await create_notification(
            case["client_id"],
            f"Document {status_text.title()}",
            f"Your document '{doc['document_type']}' has been {status_text}",
            f"doc_{review.status}",
            case["id"]
        )
    
    return {"message": f"Document {review.status}"}
