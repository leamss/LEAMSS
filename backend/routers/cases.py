"""
Case management routes for LEAMSS Portal
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from datetime import datetime, timezone
from typing import List
from bson import ObjectId

from core.database import db
from core.auth import get_current_user, require_role, UserRole
from core.models import CaseResponse, StepUpdate, AdditionalDocRequest
from services.notification_service import create_notification

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.get("/my-cases", response_model=List[CaseResponse])
async def get_my_cases(user: dict = Depends(get_current_user)):
    """Get cases for current user based on role"""
    if user["role"] == UserRole.CLIENT:
        cases = await db.cases.find({"client_id": user["id"]}, {"_id": 0}).to_list(100)
    elif user["role"] == UserRole.CASE_MANAGER:
        cases = await db.cases.find({"case_manager_id": user["id"]}, {"_id": 0}).to_list(100)
    elif user["role"] == UserRole.PARTNER:
        cases = await db.cases.find({"partner_id": user["id"]}, {"_id": 0}).to_list(100)
    else:
        cases = []
    return [CaseResponse(**c) for c in cases]


@router.get("", response_model=List[CaseResponse])
async def get_all_cases(user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Get all cases (Admin only)"""
    cases = await db.cases.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [CaseResponse(**c) for c in cases]


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, user: dict = Depends(get_current_user)):
    """Get case details"""
    case = await db.cases.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check access
    if user["role"] == UserRole.CLIENT and case["client_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if user["role"] == UserRole.CASE_MANAGER and case["case_manager_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if user["role"] == UserRole.PARTNER and case["partner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return CaseResponse(**case)


@router.post("/update-step")
async def update_case_step(
    update: StepUpdate, 
    background_tasks: BackgroundTasks, 
    user: dict = Depends(require_role([UserRole.CASE_MANAGER, UserRole.ADMIN]))
):
    """Update case step status (Case Manager/Admin only)"""
    case = await db.cases.find_one({"id": update.case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Update the specific step
    steps = case.get("steps", [])
    step_index = next((i for i, s in enumerate(steps) if s["step_name"] == update.step_name), None)
    
    if step_index is None:
        raise HTTPException(status_code=404, detail="Step not found")
    
    steps[step_index]["status"] = update.status
    if update.notes:
        steps[step_index]["notes"] = update.notes
    
    if update.status == "completed":
        steps[step_index]["approved_by"] = user["id"]
        steps[step_index]["approved_at"] = datetime.now(timezone.utc).isoformat()
        
        # Unlock next step
        if step_index + 1 < len(steps):
            steps[step_index + 1]["is_locked"] = False
    
    # Update current step if needed
    current_step = steps[step_index]["step_name"]
    current_step_order = steps[step_index]["step_order"]
    
    if update.status == "completed" and step_index + 1 < len(steps):
        current_step = steps[step_index + 1]["step_name"]
        current_step_order = steps[step_index + 1]["step_order"]
    
    # Check if all steps are completed
    case_status = "active"
    if all(s["status"] == "completed" for s in steps):
        case_status = "completed"
    
    await db.cases.update_one(
        {"id": update.case_id},
        {"$set": {
            "steps": steps,
            "current_step": current_step,
            "current_step_order": current_step_order,
            "status": case_status
        }}
    )
    
    # Notify client about step completion
    if update.status == "completed":
        await create_notification(
            case["client_id"],
            "Step Completed",
            f"Step '{update.step_name}' has been marked as completed in your case",
            "step_completed",
            case["id"]
        )
    
    return {"message": "Step updated successfully"}


@router.post("/request-additional-document")
async def request_additional_document(
    request: AdditionalDocRequest, 
    background_tasks: BackgroundTasks, 
    user: dict = Depends(require_role([UserRole.CASE_MANAGER, UserRole.ADMIN]))
):
    """Request additional document for a case"""
    case = await db.cases.find_one({"id": request.case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    doc_request = {
        "id": str(ObjectId()),
        "document_name": request.document_name,
        "description": request.description,
        "step_order": request.step_order,
        "due_date": request.due_date,
        "expiry_date": request.expiry_date,
        "validity_months": request.validity_months,
        "doc_type": request.doc_type,
        "requested_by": user["id"],
        "requested_by_name": user["name"],
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending"
    }
    
    await db.cases.update_one(
        {"id": request.case_id},
        {"$push": {"additional_doc_requests": doc_request}}
    )
    
    # Notify client
    await create_notification(
        case["client_id"],
        "Additional Document Required",
        f"A new document '{request.document_name}' has been requested for your case",
        "doc_requested",
        case["id"]
    )
    
    return {"message": "Additional document request added", "request_id": doc_request["id"]}


@router.post("/{case_id}/custom-document-request")
async def request_custom_document_for_case(
    case_id: str,
    request_data: dict,
    user: dict = Depends(require_role([UserRole.CASE_MANAGER, UserRole.ADMIN]))
):
    """
    Add a custom document request to a specific step (Case Manager with permission).
    This adds a new document requirement to the workflow step.
    
    Request body:
    - document_name: str (required)
    - step_order: int (required)
    - description: str (optional)
    - due_date: str (optional)
    - expiry_date: str (optional)
    - validity_months: int (optional)
    - doc_type: str (optional)
    """
    # Extract fields from request body
    document_name = request_data.get("document_name")
    step_order = request_data.get("step_order")
    description = request_data.get("description")
    due_date = request_data.get("due_date")
    expiry_date = request_data.get("expiry_date")
    validity_months = request_data.get("validity_months")
    doc_type = request_data.get("doc_type")
    
    if not document_name or step_order is None:
        raise HTTPException(status_code=400, detail="document_name and step_order are required")
    
    # Check if the feature is enabled
    settings = await db.settings.find_one({"key": "global"})
    if user["role"] == UserRole.CASE_MANAGER:
        if not settings or not settings.get("allow_case_manager_workflow_customization", False):
            raise HTTPException(
                status_code=403, 
                detail="Workflow customization is not enabled. Contact admin."
            )
    
    case = await db.cases.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Verify case manager owns this case (unless admin)
    if user["role"] == UserRole.CASE_MANAGER and case["case_manager_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="You are not assigned to this case")
    
    # Verify the previous step is completed (to allow customization)
    steps = case.get("steps", [])
    target_step_index = next((i for i, s in enumerate(steps) if s.get("step_order") == step_order), None)
    
    if target_step_index is None:
        raise HTTPException(status_code=404, detail="Step not found")
    
    if target_step_index > 0:
        prev_step = steps[target_step_index - 1]
        if prev_step.get("status") != "completed":
            raise HTTPException(
                status_code=400, 
                detail="Cannot add document request. Previous step must be completed first."
            )
    
    # Create the custom document request
    custom_doc = {
        "id": str(ObjectId()),
        "doc_name": document_name,
        "description": description or f"Custom document: {document_name}",
        "step_order": step_order,
        "step_name": steps[target_step_index]["step_name"],
        "due_date": due_date,
        "is_mandatory": True,
        "requested_by": user["id"],
        "requested_by_name": user["name"],
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "is_custom": True
    }
    
    # Add to both the step's required_documents and the case's additional_doc_requests
    steps[target_step_index]["required_documents"].append({
        "doc_name": document_name,
        "description": description or f"Custom document: {document_name}",
        "is_mandatory": True,
        "is_custom": True,
        "request_id": custom_doc["id"]
    })
    
    await db.cases.update_one(
        {"id": case_id},
        {
            "$set": {"steps": steps},
            "$push": {"additional_doc_requests": custom_doc}
        }
    )
    
    # Notify client
    await create_notification(
        case["client_id"],
        "New Document Required",
        f"A new document '{document_name}' has been requested for step '{steps[target_step_index]['step_name']}'",
        "document_request",
        case_id
    )
    
    return {
        "message": "Custom document request added successfully",
        "request_id": custom_doc["id"],
        "step_name": steps[target_step_index]["step_name"]
    }


@router.put("/{case_id}/assign-manager")
async def reassign_case_manager(
    case_id: str, 
    case_manager_id: str, 
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Reassign case to a different case manager (Admin only)"""
    case = await db.cases.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    new_manager = await db.users.find_one({"id": case_manager_id})
    if not new_manager or new_manager["role"] != UserRole.CASE_MANAGER:
        raise HTTPException(status_code=400, detail="Invalid case manager")
    
    old_manager_id = case["case_manager_id"]
    
    await db.cases.update_one(
        {"id": case_id},
        {"$set": {
            "case_manager_id": case_manager_id,
            "case_manager_name": new_manager["name"]
        }}
    )
    
    # Notify old manager
    if old_manager_id:
        await create_notification(
            old_manager_id,
            "Case Reassigned",
            f"Case {case['case_id']} has been reassigned to another manager",
            "case_reassigned",
            case_id
        )
    
    # Notify new manager
    await create_notification(
        case_manager_id,
        "New Case Assigned",
        f"Case {case['case_id']} for {case['client_name']} has been assigned to you",
        "case_assigned",
        case_id
    )
    
    return {"message": "Case manager reassigned successfully"}
