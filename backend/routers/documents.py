"""Documents Router"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from core.database import documents_col, cases_col, notifications_col, audit_logs_col, users_col, case_steps_col
from core.auth import get_current_user
from core.services import create_notification, notify_role, log_activity
from core.email_service import send_document_review_email
from pydantic import BaseModel
from typing import Optional, List
import uuid, os
from datetime import datetime, timezone


router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DocumentReview(BaseModel):
    document_id: str
    status: str
    comment: str = ""


class SetExpiryRequest(BaseModel):
    expiry_date: str
    notes: str = ""

# Known document types with typical validity periods (in days)
DOCUMENT_VALIDITY = {
    "passport": 3650,         # ~10 years
    "medical": 365,           # 1 year
    "ielts": 730,             # 2 years
    "pte": 730,               # 2 years
    "toefl": 730,             # 2 years
    "skill_assessment": 1095, # 3 years
    "eca": 1825,              # 5 years (WES/IQAS)
    "police_clearance": 365,  # 1 year
    "visa": 365,              # varies
    "work_permit": 365,       # varies
    "offer_letter": 180,      # 6 months
}


async def _log(user_id, action, entity_type, entity_id=None, details=None):
    # X3: delegate to centralised audit_service.log_legacy_event
    from services.audit_service import log_legacy_event
    from core.database import db as _db
    await log_legacy_event(_db, user_id, action, entity_type, entity_id, details)


@router.get("/case/{case_id}")
async def get_case_documents(case_id: str, current_user: dict = Depends(get_current_user)):
    docs = await documents_col.find({"case_id": case_id}, {"_id": 0}).sort("uploaded_at", -1).to_list(500)
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
    files: List[UploadFile] = File(default=[]),
    file: Optional[UploadFile] = File(default=None),
    case_id: str = Form(...),
    step_name: str = Form(""),
    document_type: str = Form("general"),
    expiry_date: str = Form(""),
    additional_request_id: Optional[str] = Form(None),
    additional_doc_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    case = await cases_col.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Collect all files uploaded
    all_files: List[UploadFile] = []
    if files:
        all_files.extend(files)
    if file and file not in all_files:
        all_files.append(file)

    if not all_files:
        raise HTTPException(status_code=400, detail="No file(s) provided for upload")

    # ENFORCEMENT: If client is uploading to a specific step, check if it is locked
    if current_user["role"] == "client" and step_name:
        case_steps = await case_steps_col.find({"case_id": case_id}).sort("step_order", 1).to_list(100)
        target_step = next((s for s in case_steps if s.get("step_name") == step_name), None)
        if target_step:
            target_order = target_step.get("step_order", 1)
            if target_order > 1:
                current_order = case.get("current_step_order") or 1
                prev_steps = [s for s in case_steps if s.get("step_order", 0) < target_order]
                prev_uncompleted = next((s for s in prev_steps if s.get("status") != "completed"), None)
                is_active = target_step.get("status") in ("in_progress", "completed") or target_order <= current_order
                if prev_uncompleted is not None and not is_active:
                    prev_order = prev_uncompleted.get("step_order", target_order - 1)
                    prev_name = prev_uncompleted.get("step_name", "")
                    raise HTTPException(
                        status_code=403,
                        detail=f"Step '{step_name}' is locked. Please wait until your Case Manager completes Step {prev_order} ({prev_name})."
                    )

    saved_docs = []
    target_req_id = additional_request_id or additional_doc_id

    for single_file in all_files:
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(single_file.filename)[1]
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
        
        content = await single_file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        doc = {
            "id": file_id,
            "case_id": case_id,
            "step_name": step_name,
            "document_type": document_type,
            "filename": single_file.filename,
            "file_path": file_path,
            "file_size": len(content),
            "content_type": single_file.content_type,
            "status": "pending",
            "uploaded_by": current_user["id"],
            "uploader_name": current_user.get("name", ""),
            "uploaded_at": datetime.now(timezone.utc)
        }
        if target_req_id:
            doc["additional_request_id"] = target_req_id

        # Add expiry date if provided
        if expiry_date:
            try:
                doc["expiry_date"] = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
                doc["expiry_set_by"] = current_user["id"]
                doc["expiry_set_at"] = datetime.now(timezone.utc)
            except ValueError:
                pass
        # Auto-suggest expiry for known doc types
        elif document_type in DOCUMENT_VALIDITY:
            from datetime import timedelta
            doc["expiry_date"] = datetime.now(timezone.utc) + timedelta(days=DOCUMENT_VALIDITY[document_type])
            doc["expiry_notes"] = "Auto-set based on standard validity"
            doc["expiry_set_by"] = "system"
            doc["expiry_set_at"] = datetime.now(timezone.utc)

        await documents_col.insert_one(doc)
        await _log(current_user["id"], "upload_document", "document", file_id, {"filename": single_file.filename, "case_id": case_id, "document_type": document_type})
        
        # Clean up mongo _id for response
        doc.pop("_id", None)
        saved_docs.append(doc)

    # Notify case manager or client
    filenames_str = ", ".join([f.filename for f in all_files])
    if current_user["role"] == "client" and case.get("case_manager_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": case["case_manager_id"],
            "title": "Document(s) Uploaded",
            "message": f"{len(all_files)} document(s) uploaded for step '{step_name or document_type}': {filenames_str} (Case: {case.get('case_id', '')})",
            "type": "document_upload",
            "related_id": case_id,
            "read": False,
            "created_at": datetime.now(timezone.utc)
        })
    elif current_user["role"] in ["case_manager", "admin"] and case.get("client_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": case["client_id"],
            "title": "Document(s) Uploaded by Case Manager",
            "message": f"Case Manager uploaded {len(all_files)} document(s) for step '{step_name or document_type}': {filenames_str}",
            "type": "document_upload",
            "related_id": case_id,
            "read": False,
            "created_at": datetime.now(timezone.utc)
        })
    
    first_id = saved_docs[0]["id"] if saved_docs else None
    return {
        "id": first_id,
        "ids": [d["id"] for d in saved_docs],
        "count": len(saved_docs),
        "documents": saved_docs,
        "message": f"{len(saved_docs)} document(s) uploaded successfully"
    }


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an uploaded document"""
    doc = await documents_col.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    case = await cases_col.find_one({"id": doc.get("case_id")}, {"_id": 0})
    is_admin = current_user.get("role") == "admin"
    is_cm = current_user.get("role") == "case_manager" and (case and case.get("case_manager_id") == current_user.get("id"))
    is_uploader = doc.get("uploaded_by") == current_user.get("id")
    
    if not (is_admin or is_cm or is_uploader):
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")
    
    await documents_col.delete_one({"id": doc_id})
    if doc.get("file_path") and os.path.exists(doc["file_path"]):
        try:
            os.remove(doc["file_path"])
        except Exception:
            pass
    
    await _log(current_user["id"], "delete_document", "document", doc_id, {"filename": doc.get("filename"), "case_id": doc.get("case_id")})
    return {"message": "Document deleted successfully"}



from core.database import documents_col, cases_col, notifications_col, audit_logs_col, users_col, case_steps_col, workflow_steps_col, sales_col, pre_assessments_col


async def _is_doc_payment_locked_for_user(doc: dict, current_user: dict) -> tuple[bool, float, Optional[str]]:
    """Checks if a document is locked due to pending payment for client user"""
    if current_user.get("role") != "client":
        return False, 0.0, None
    
    case_id = doc.get("case_id")
    if not case_id:
        return False, 0.0, None
    
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        return False, 0.0, None
    
    # Check if doc requirement is marked is_locked_until_paid
    is_locked_rule = False
    doc_type = (doc.get("document_type") or "").lower().strip()
    product_id = case.get("product_id")
    if product_id:
        wf_steps = await workflow_steps_col.find({"product_id": product_id}, {"_id": 0}).to_list(100)
        for ws in wf_steps:
            # Check sections[].fields[]
            for sec in ws.get("sections", []):
                for f in sec.get("fields", []):
                    f_label = (f.get("label") or f.get("name") or f.get("key") or "").lower().strip()
                    if f_label == doc_type or doc_type in f_label or f_label in doc_type:
                        if f.get("is_locked_until_paid") or f.get("payment_locked"):
                            is_locked_rule = True
                            break
            # Check required_documents[]
            for req in ws.get("required_documents", []):
                req_name = (req.get("name") or req.get("doc_name") or "").lower().strip()
                if req_name == doc_type or doc_type in req_name or req_name in doc_type:
                    if req.get("is_locked_until_paid") or req.get("payment_locked"):
                        is_locked_rule = True
                        break
            if is_locked_rule:
                break
    
    if not is_locked_rule and (doc.get("is_locked_until_paid") or doc.get("payment_locked")):
        is_locked_rule = True
        
    if not is_locked_rule:
        return False, 0.0, None
    
    # Now check if case has pending payment
    pa = None
    if case.get("pre_assessment_id"):
        pa = await pre_assessments_col.find_one({"id": case["pre_assessment_id"]}, {"_id": 0})
    sale = None
    if case.get("sale_id"):
        sale = await sales_col.find_one({"id": case["sale_id"]}, {"_id": 0})
    elif case.get("client_id"):
        sale = await sales_col.find_one({"client_id": case["client_id"]}, {"_id": 0})

    is_fully_paid = True
    pending_amount = 0.0
    sale_id = (sale and sale.get("id")) or case.get("sale_id") or (pa and pa.get("sale_id"))

    if sale:
        sale_status = sale.get("payment_status")
        pending_amt = float(sale.get("pending_amount", 0))
        unpaid_parts = [p for p in sale.get("payment_parts", []) if p.get("status") != "paid"]
        if sale_status != "paid" or pending_amt > 0 or len(unpaid_parts) > 0:
            is_fully_paid = False
            unpaid_sum = sum(float(p.get("amount", 0)) for p in unpaid_parts) if unpaid_parts else pending_amt
            pending_amount = max(pending_amt, unpaid_sum)
        else:
            is_fully_paid = True
            pending_amount = 0.0
    elif pa:
        unpaid_parts = [p for p in pa.get("proposal_payment_parts", []) if p.get("status") != "paid"]
        pending_amt = float(pa.get("proposal_amount_pending", 0))
        if pa.get("stage") not in ("proposal_paid", "paid") and (pending_amt > 0 or len(unpaid_parts) > 0):
            is_fully_paid = False
            unpaid_sum = sum(float(p.get("amount", 0)) for p in unpaid_parts) if unpaid_parts else pending_amt
            pending_amount = max(pending_amt, unpaid_sum)
        else:
            is_fully_paid = True
            pending_amount = 0.0

    if not is_fully_paid and pending_amount > 0:
        return True, pending_amount, sale_id
    
    return False, 0.0, sale_id


@router.get("/download/{file_id}")
async def download_document(file_id: str, current_user: dict = Depends(get_current_user)):
    doc = await documents_col.find_one({"id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # ENFORCEMENT: Check if document is locked due to pending payment
    is_locked, pending_amt, sale_id = await _is_doc_payment_locked_for_user(doc, current_user)
    if is_locked:
        raise HTTPException(
            status_code=402,
            detail=f"This document is locked until full payment is completed (₹{pending_amt:,.0f} pending). Please complete payment to download."
        )

    if not os.path.exists(doc["file_path"]):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        doc["file_path"],
        filename=doc["filename"],
        media_type=doc.get("content_type", "application/octet-stream")
    )

@router.get("/view/{file_id}")
async def view_document(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    doc = await documents_col.find_one(
        {"id": file_id},
        {"_id": 0}
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # ENFORCEMENT: Check if document is locked due to pending payment
    is_locked, pending_amt, sale_id = await _is_doc_payment_locked_for_user(doc, current_user)
    if is_locked:
        raise HTTPException(
            status_code=402,
            detail=f"This document is locked until full payment is completed (₹{pending_amt:,.0f} pending). Please complete payment to view."
        )

    if not os.path.exists(doc["file_path"]):
        raise HTTPException(
            status_code=404,
            detail="File not found on server"
        )

    return FileResponse(
        doc["file_path"],
        media_type=doc.get(
            "content_type",
            "application/octet-stream"
        ),
        headers={
            "Content-Disposition": (
                f'inline; filename="{doc["filename"]}"'
            )
        }
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
        
        # Email notification to document uploader
        uploader = await users_col.find_one({"id": doc["uploaded_by"]}, {"_id": 0})
        if uploader:
            await send_document_review_email(
                uploader.get("email", ""), uploader.get("name", ""),
                doc.get("filename", "Document"), request.status, request.comment or ""
            )
    
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
    
    # Notify case manager about new upload
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if case and case.get("case_manager_id"):
        await create_notification(case["case_manager_id"], "New Document Upload",
            f"Client uploaded '{file.filename}' for case {case.get('case_number', case_id)}",
            "document_upload", case_id)
    await log_activity(current_user["id"], current_user.get("name", ""), "uploaded", "document", file_id,
        f"Uploaded document: {file.filename}")
    
    return {"id": doc["id"], "message": "Document uploaded successfully"}


@router.post("/bulk-upload")
async def bulk_upload_documents(
    files: List[UploadFile] = File(...),
    case_id: str = Form(...),
    document_type: str = Form("general"),
    document_types: str = Form(""),
    step_names: str = Form(""),
    expiry_dates: str = Form(""),
    current_user: dict = Depends(get_current_user)
):
    """Upload multiple documents at once with optional per-file types and expiry dates"""
    import json as json_mod
    uploaded = []
    errors = []

    try:
        type_list = json_mod.loads(document_types) if document_types else []
    except Exception:
        type_list = []
    try:
        step_list = json_mod.loads(step_names) if step_names else []
    except Exception:
        step_list = []
    try:
        expiry_list = json_mod.loads(expiry_dates) if expiry_dates else []
    except Exception:
        expiry_list = []

    for i, file in enumerate(files):
        try:
            file_id = str(uuid.uuid4())
            file_ext = os.path.splitext(file.filename)[1]
            file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")

            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            doc_type = type_list[i] if i < len(type_list) else document_type
            step_name = step_list[i] if i < len(step_list) else ""
            expiry_str = expiry_list[i] if i < len(expiry_list) else ""

            # Check if step is locked for client
            if current_user["role"] == "client" and step_name:
                case_steps = await case_steps_col.find({"case_id": case_id}).sort("step_order", 1).to_list(100)
                target_step = next((s for s in case_steps if s.get("step_name") == step_name), None)
                if target_step:
                    target_order = target_step.get("step_order", 1)
                    if target_order > 1:
                        current_order = (await cases_col.find_one({"id": case_id}, {"_id": 0, "current_step_order": 1}) or {}).get("current_step_order", 1)
                        prev_steps = [s for s in case_steps if s.get("step_order", 0) < target_order]
                        prev_uncompleted = next((s for s in prev_steps if s.get("status") != "completed"), None)
                        is_active = target_step.get("status") in ("in_progress", "completed") or target_order <= current_order
                        if prev_uncompleted is not None and not is_active:
                            errors.append({"file": file.filename, "error": f"Step '{step_name}' is locked until previous steps are completed"})
                            continue

            doc = {
                "id": file_id, "case_id": case_id, "document_type": doc_type,
                "step_name": step_name,
                "filename": file.filename, "file_path": file_path,
                "file_size": len(content), "content_type": file.content_type,
                "status": "pending", "uploaded_by": current_user["id"],
                "uploader_name": current_user.get("name", ""),
                "uploaded_at": datetime.now(timezone.utc)
            }
            # Add expiry if provided
            if expiry_str:
                try:
                    doc["expiry_date"] = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                    doc["expiry_set_by"] = current_user["id"]
                    doc["expiry_set_at"] = datetime.now(timezone.utc)
                except ValueError:
                    pass
            elif doc_type in DOCUMENT_VALIDITY:
                from datetime import timedelta
                doc["expiry_date"] = datetime.now(timezone.utc) + timedelta(days=DOCUMENT_VALIDITY[doc_type])
                doc["expiry_notes"] = "Auto-set based on standard validity"
                doc["expiry_set_by"] = "system"
                doc["expiry_set_at"] = datetime.now(timezone.utc)

            await documents_col.insert_one(doc)
            uploaded.append({"id": file_id, "filename": file.filename, "document_type": doc_type})
        except Exception as e:
            errors.append({"filename": file.filename, "error": str(e)})

    if uploaded:
        case = await cases_col.find_one({"id": case_id}, {"_id": 0})
        if case and case.get("case_manager_id"):
            await create_notification(case["case_manager_id"], "Bulk Document Upload",
                f"{len(uploaded)} documents uploaded for case {case.get('case_number', case_id)}",
                "document_upload", case_id)
        await log_activity(current_user["id"], current_user.get("name", ""), "bulk_uploaded", "document", case_id,
            f"Uploaded {len(uploaded)} documents")

    return {
        "message": f"{len(uploaded)} documents uploaded successfully" + (f", {len(errors)} failed" if errors else ""),
        "uploaded": uploaded,
        "errors": errors
    }


@router.post("/{doc_id}/set-expiry")
async def set_document_expiry(doc_id: str, request: SetExpiryRequest, current_user: dict = Depends(get_current_user)):
    """Set or update expiry date for a document"""
    if current_user["role"] not in ["admin", "case_manager", "client"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    doc = await documents_col.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        expiry_dt = datetime.fromisoformat(request.expiry_date.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")

    update_data = {
        "expiry_date": expiry_dt,
        "expiry_notes": request.notes,
        "expiry_set_by": current_user["id"],
        "expiry_set_at": datetime.now(timezone.utc)
    }
    await documents_col.update_one({"id": doc_id}, {"$set": update_data})

    await log_activity(current_user["id"], current_user.get("name", ""), "set_expiry", "document", doc_id,
        f"Set expiry for '{doc.get('filename', '')}' to {request.expiry_date}")

    # Notify relevant parties
    case = await cases_col.find_one({"id": doc.get("case_id")}, {"_id": 0})
    if case:
        notify_user = None
        if current_user["role"] == "client" and case.get("case_manager_id"):
            notify_user = case["case_manager_id"]
        elif current_user["role"] in ["admin", "case_manager"] and doc.get("uploaded_by"):
            notify_user = doc["uploaded_by"]
        if notify_user and notify_user != current_user["id"]:
            await create_notification(notify_user, "Document Expiry Set",
                f"Expiry date set for '{doc.get('filename', '')}': {request.expiry_date[:10]}",
                "document_expiry", doc.get("case_id"))

    return {"message": "Expiry date updated", "expiry_date": request.expiry_date}


@router.get("/expiring/all")
async def get_all_expiring_documents(current_user: dict = Depends(get_current_user)):
    """Get all documents with expiry tracking — for Case Managers and Admins"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")

    now = datetime.now(timezone.utc)

    query = {"expiry_date": {"$exists": True, "$ne": None}}
    if current_user["role"] == "case_manager":
        # Only show documents for cases assigned to this manager
        cases = await cases_col.find({"case_manager_id": current_user["id"]}, {"_id": 0, "id": 1}).to_list(500)
        case_ids = [c["id"] for c in cases]
        query["case_id"] = {"$in": case_ids}

    docs = await documents_col.find(query, {"_id": 0, "file_path": 0}).to_list(1000)

    result = []
    for d in docs:
        exp = d.get("expiry_date")
        if not isinstance(exp, datetime):
            continue
        # Make timezone-aware if naive
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days_remaining = (exp - now).days
        if days_remaining < 0:
            urgency = "expired"
        elif days_remaining <= 30:
            urgency = "critical"
        elif days_remaining <= 60:
            urgency = "warning"
        elif days_remaining <= 90:
            urgency = "attention"
        else:
            urgency = "ok"

        # Get case info
        case = await cases_col.find_one({"id": d.get("case_id")}, {"_id": 0, "case_id": 1, "client_id": 1, "product_name": 1})
        client_name = ""
        if case and case.get("client_id"):
            client = await users_col.find_one({"id": case["client_id"]}, {"_id": 0, "name": 1})
            client_name = client.get("name", "") if client else ""

        for f in ["uploaded_at", "reviewed_at", "expiry_date", "expiry_set_at"]:
            if isinstance(d.get(f), datetime):
                d[f] = d[f].isoformat()

        result.append({
            **d,
            "days_remaining": days_remaining,
            "urgency": urgency,
            "case_number": case.get("case_id", "") if case else "",
            "client_name": client_name,
            "product_name": case.get("product_name", "") if case else "",
        })

    result.sort(key=lambda x: x.get("days_remaining", 9999))
    return result


@router.get("/expiring/case/{case_id}")
async def get_case_expiring_documents(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get expiring documents for a specific case"""
    now = datetime.now(timezone.utc)
    docs = await documents_col.find({"case_id": case_id}, {"_id": 0, "file_path": 0}).to_list(500)

    result = []
    for d in docs:
        exp = d.get("expiry_date")
        days_remaining = None
        urgency = "no_expiry"
        if isinstance(exp, datetime):
            # Make timezone-aware if naive
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            days_remaining = (exp - now).days
            if days_remaining < 0:
                urgency = "expired"
            elif days_remaining <= 30:
                urgency = "critical"
            elif days_remaining <= 60:
                urgency = "warning"
            elif days_remaining <= 90:
                urgency = "attention"
            else:
                urgency = "ok"

        for f in ["uploaded_at", "reviewed_at", "expiry_date", "expiry_set_at"]:
            if isinstance(d.get(f), datetime):
                d[f] = d[f].isoformat()

        # Auto-suggest validity if no expiry set
        suggested_validity = DOCUMENT_VALIDITY.get(d.get("document_type"), None)

        result.append({
            **d,
            "days_remaining": days_remaining,
            "urgency": urgency,
            "suggested_validity_days": suggested_validity,
        })

    result.sort(key=lambda x: (x.get("days_remaining") is None, x.get("days_remaining", 9999)))
    return result


@router.get("/validity-presets")
async def get_validity_presets(current_user: dict = Depends(get_current_user)):
    """Get known document types and their typical validity periods"""
    presets = []
    for doc_type, days in DOCUMENT_VALIDITY.items():
        label = doc_type.replace("_", " ").title()
        if days >= 365:
            period = f"{days // 365} year{'s' if days // 365 > 1 else ''}"
        else:
            period = f"{days} days"
        presets.append({"document_type": doc_type, "label": label, "validity_days": days, "validity_label": period})
    return presets


# Expiry reminder thresholds (days before expiry)
REMINDER_THRESHOLDS = [
    {"days": 60, "level": "attention", "title": "Document Expiring in 60 Days"},
    {"days": 30, "level": "warning", "title": "Document Expiring in 30 Days"},
    {"days": 7, "level": "critical", "title": "Document Expiring in 7 Days!"},
    {"days": 0, "level": "expired", "title": "Document Has Expired"},
]


@router.post("/check-expiry-reminders")
async def check_expiry_reminders(current_user: dict = Depends(get_current_user)):
    """Check all documents with expiry dates and send in-app notifications.
    Smart: won't send duplicate notifications for the same threshold."""

    now = datetime.now(timezone.utc)
    docs_with_expiry = await documents_col.find(
        {"expiry_date": {"$exists": True, "$ne": None}},
        {"_id": 0, "file_path": 0}
    ).to_list(2000)

    reminders_sent = 0

    for doc in docs_with_expiry:
        exp = doc.get("expiry_date")
        if not isinstance(exp, datetime):
            continue
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        days_remaining = (exp - now).days

        # Get case info for notifications
        case = await cases_col.find_one({"id": doc.get("case_id")}, {"_id": 0, "client_id": 1, "case_manager_id": 1, "case_id": 1})
        if not case:
            continue

        for threshold in REMINDER_THRESHOLDS:
            if (threshold["days"] == 0 and days_remaining <= 0) or \
               (threshold["days"] > 0 and 0 < days_remaining <= threshold["days"]):

                reminder_key = f"expiry_{doc['id']}_{threshold['level']}"

                # Check if this exact reminder was already sent (dedupe)
                existing = await notifications_col.find_one({
                    "reminder_key": reminder_key,
                    "created_at": {"$gte": datetime(now.year, now.month, now.day, tzinfo=timezone.utc)}
                })
                if existing:
                    continue

                doc_label = f"{doc.get('filename', 'Document')} ({doc.get('document_type', 'unknown').replace('_', ' ').title()})"

                if days_remaining <= 0:
                    message = f"{doc_label} has expired ({abs(days_remaining)} days ago). Please renew/update."
                else:
                    message = f"{doc_label} will expire in {days_remaining} days ({exp.strftime('%d %b %Y')}). Please renew before expiry."

                # Notify client
                if case.get("client_id"):
                    await notifications_col.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": case["client_id"],
                        "title": threshold["title"],
                        "message": message,
                        "type": "document_expiry",
                        "related_id": doc.get("case_id"),
                        "read": False,
                        "reminder_key": reminder_key,
                        "urgency": threshold["level"],
                        "created_at": datetime.now(timezone.utc)
                    })
                    reminders_sent += 1

                # Notify case manager
                if case.get("case_manager_id"):
                    client_info = ""
                    if case.get("client_id"):
                        client = await users_col.find_one({"id": case["client_id"]}, {"_id": 0, "name": 1})
                        client_info = f" (Client: {client.get('name', 'Unknown')})" if client else ""

                    await notifications_col.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": case["case_manager_id"],
                        "title": threshold["title"],
                        "message": f"{message}{client_info} - Case {case.get('case_id', '')}",
                        "type": "document_expiry",
                        "related_id": doc.get("case_id"),
                        "read": False,
                        "reminder_key": f"{reminder_key}_cm",
                        "urgency": threshold["level"],
                        "created_at": datetime.now(timezone.utc)
                    })
                    reminders_sent += 1

                break  # Only send the most relevant threshold per document

    return {"message": f"{reminders_sent} expiry reminders sent", "reminders_sent": reminders_sent}


@router.get("/expiry-summary")
async def get_expiry_summary(current_user: dict = Depends(get_current_user)):
    """Get expiry summary counts for Admin/Case Manager dashboard widgets"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")

    now = datetime.now(timezone.utc)
    query = {"expiry_date": {"$exists": True, "$ne": None}}

    if current_user["role"] == "case_manager":
        cases = await cases_col.find({"case_manager_id": current_user["id"]}, {"_id": 0, "id": 1}).to_list(500)
        case_ids = [c["id"] for c in cases]
        query["case_id"] = {"$in": case_ids}

    docs = await documents_col.find(query, {"_id": 0, "expiry_date": 1}).to_list(2000)

    counts = {"expired": 0, "critical": 0, "warning": 0, "attention": 0, "ok": 0, "total": len(docs)}
    for d in docs:
        exp = d.get("expiry_date")
        if not isinstance(exp, datetime):
            continue
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days = (exp - now).days
        if days < 0:
            counts["expired"] += 1
        elif days <= 30:
            counts["critical"] += 1
        elif days <= 60:
            counts["warning"] += 1
        elif days <= 90:
            counts["attention"] += 1
        else:
            counts["ok"] += 1

    return counts



# ============ BULK DOCUMENT REVIEW ============

class BulkReviewRequest(BaseModel):
    document_ids: List[str]
    status: str
    comment: str = ""


@router.post("/bulk-review")
async def bulk_review_documents(request: BulkReviewRequest, current_user: dict = Depends(get_current_user)):
    """Approve or reject multiple documents at once"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if request.status not in ["approved", "rejected", "revision_required"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    results = []
    for doc_id in request.document_ids:
        doc = await documents_col.find_one({"id": doc_id}, {"_id": 0})
        if not doc:
            results.append({"id": doc_id, "result": "not_found"})
            continue
        await documents_col.update_one({"id": doc_id}, {"$set": {
            "status": request.status, "review_comment": request.comment or f"Bulk {request.status}",
            "reviewed_by": current_user["id"], "reviewer_name": current_user["name"],
            "reviewed_at": datetime.now(timezone.utc)
        }})
        # Notify uploader
        if doc.get("uploaded_by"):
            await create_notification(doc["uploaded_by"], f"Document {request.status}", f"{doc.get('filename','')} has been {request.status}", "document_review", doc_id)
        await log_activity(current_user["id"], current_user["name"], f"bulk_{request.status}_document", "document", doc_id, {"filename": doc.get("filename","")})
        results.append({"id": doc_id, "result": request.status})
    return {"results": results, "processed": len([r for r in results if r["result"] != "not_found"])}


# ============ DOCUMENT ANNOTATION ============

class AnnotationRequest(BaseModel):
    text: str
    page: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None


@router.post("/{doc_id}/annotate")
async def annotate_document(doc_id: str, request: AnnotationRequest, current_user: dict = Depends(get_current_user)):
    """Add annotation to a document"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    doc = await documents_col.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    annotation = {
        "id": str(uuid.uuid4()), "text": request.text, "page": request.page,
        "x": request.x, "y": request.y, "author_id": current_user["id"],
        "author_name": current_user["name"], "created_at": datetime.now(timezone.utc).isoformat()
    }
    await documents_col.update_one({"id": doc_id}, {"$push": {"annotations": annotation}})
    await log_activity(current_user["id"], current_user["name"], "annotate_document", "document", doc_id, {"text": request.text[:50]})
    return annotation


@router.get("/{doc_id}/annotations")
async def get_annotations(doc_id: str, current_user: dict = Depends(get_current_user)):
    """Get all annotations for a document"""
    doc = await documents_col.find_one({"id": doc_id}, {"_id": 0, "annotations": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.get("annotations", [])
