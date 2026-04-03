"""Cases Router"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import (
    cases_col, case_steps_col, users_col, products_col, documents_col,
    additional_doc_requests_col, notifications_col, audit_logs_col,
    information_sheets_col, workflow_steps_col
)
from core.auth import get_current_user
import uuid
from datetime import datetime, timezone, date

router = APIRouter(prefix="/cases", tags=["Cases"])


class StepUpdate(BaseModel):
    case_id: str
    step_name: str
    status: str
    notes: str = ""


class DocRequest(BaseModel):
    case_id: Optional[str] = None
    document_name: str
    description: str = ""
    step_order: int = 1
    due_date: Optional[str] = None
    expiry_date: Optional[str] = None
    validity_months: Optional[int] = None
    doc_type: str = "general"


async def _log(user_id, action, entity_type, entity_id=None, details=None):
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "action": action,
        "entity_type": entity_type, "entity_id": entity_id,
        "new_value": details, "created_at": datetime.now(timezone.utc)
    })


def _serialize(case):
    c = {k: v for k, v in case.items() if k != "_id"}
    for f in ["created_at", "updated_at"]:
        if isinstance(c.get(f), datetime):
            c[f] = c[f].isoformat()
    return c


@router.get("")
async def get_cases(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == "case_manager":
        query["case_manager_id"] = current_user["id"]
    elif current_user["role"] == "client":
        query["client_id"] = current_user["id"]
    elif current_user["role"] == "partner":
        query["partner_id"] = current_user["id"]
    
    cases = await cases_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    for case in cases:
        client = await users_col.find_one({"id": case.get("client_id")}, {"_id": 0, "password": 0})
        product = await products_col.find_one({"id": case.get("product_id")}, {"_id": 0})
        manager = await users_col.find_one({"id": case.get("case_manager_id")}, {"_id": 0, "password": 0})
        partner = await users_col.find_one({"id": case.get("partner_id")}, {"_id": 0, "password": 0})
        
        case["client_name"] = client["name"] if client else "N/A"
        case["client_email"] = client.get("email", "") if client else ""
        case["product_name"] = product["name"] if product else "N/A"
        case["case_manager_name"] = manager["name"] if manager else "Not Assigned"
        case["partner_name"] = partner["name"] if partner else "N/A"
        
        steps = await case_steps_col.find({"case_id": case["id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        case["steps"] = steps
        
        additional_docs = await additional_doc_requests_col.find({"case_id": case["id"]}, {"_id": 0}).to_list(100)
        for doc in additional_docs:
            for f in ["created_at", "due_date", "expiry_date"]:
                if isinstance(doc.get(f), datetime):
                    doc[f] = doc[f].isoformat()
        case["additional_doc_requests"] = additional_docs
        
        for f in ["created_at", "updated_at"]:
            if isinstance(case.get(f), datetime):
                case[f] = case[f].isoformat()
    
    return cases


@router.get("/my-cases")
async def get_my_cases(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == "case_manager":
        query["case_manager_id"] = current_user["id"]
    elif current_user["role"] == "client":
        query["client_id"] = current_user["id"]
    
    cases = await cases_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    for case in cases:
        client = await users_col.find_one({"id": case.get("client_id")}, {"_id": 0, "password": 0})
        product = await products_col.find_one({"id": case.get("product_id")}, {"_id": 0})
        manager = await users_col.find_one({"id": case.get("case_manager_id")}, {"_id": 0, "password": 0})
        partner = await users_col.find_one({"id": case.get("partner_id")}, {"_id": 0, "password": 0})
        
        case["client_name"] = client["name"] if client else "N/A"
        case["client_email"] = client.get("email", "") if client else ""
        case["product_name"] = product["name"] if product else "N/A"
        case["case_manager_name"] = manager["name"] if manager else "Not Assigned"
        case["partner_name"] = partner["name"] if partner else "N/A"
        
        steps = await case_steps_col.find({"case_id": case["id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        case["steps"] = steps
        
        additional_docs = await additional_doc_requests_col.find({"case_id": case["id"]}, {"_id": 0}).to_list(100)
        for doc in additional_docs:
            for f in ["created_at", "due_date", "expiry_date"]:
                if isinstance(doc.get(f), datetime):
                    doc[f] = doc[f].isoformat()
        case["additional_doc_requests"] = additional_docs
        
        for f in ["created_at", "updated_at"]:
            if isinstance(case.get(f), datetime):
                case[f] = case[f].isoformat()
    
    return cases


@router.get("/{case_id}")
async def get_case(case_id: str, current_user: dict = Depends(get_current_user)):
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    client = await users_col.find_one({"id": case.get("client_id")}, {"_id": 0, "password": 0})
    product = await products_col.find_one({"id": case.get("product_id")}, {"_id": 0})
    manager = await users_col.find_one({"id": case.get("case_manager_id")}, {"_id": 0, "password": 0})
    partner = await users_col.find_one({"id": case.get("partner_id")}, {"_id": 0, "password": 0})
    
    case["client_name"] = client["name"] if client else "N/A"
    case["client_email"] = client.get("email", "") if client else ""
    case["product_name"] = product["name"] if product else "N/A"
    case["case_manager_name"] = manager["name"] if manager else "Not Assigned"
    case["partner_name"] = partner["name"] if partner else "N/A"
    
    steps = await case_steps_col.find({"case_id": case["id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
    case["steps"] = steps
    
    additional_docs = await additional_doc_requests_col.find({"case_id": case["id"]}, {"_id": 0}).to_list(100)
    for doc in additional_docs:
        for f in ["created_at", "due_date", "expiry_date"]:
            if isinstance(doc.get(f), datetime):
                doc[f] = doc[f].isoformat()
    case["additional_doc_requests"] = additional_docs
    
    for f in ["created_at", "updated_at"]:
        if isinstance(case.get(f), datetime):
            case[f] = case[f].isoformat()
    
    return case


@router.post("/update-step")
async def update_step(request: StepUpdate, current_user: dict = Depends(get_current_user)):
    case = await cases_col.find_one({"id": request.case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    await case_steps_col.update_one(
        {"case_id": request.case_id, "step_name": request.step_name},
        {"$set": {"status": request.status, "notes": request.notes, "updated_at": datetime.now(timezone.utc)}}
    )
    
    if request.status == "completed":
        steps = await case_steps_col.find({"case_id": request.case_id}, {"_id": 0}).sort("step_order", 1).to_list(100)
        current_order = next((s["step_order"] for s in steps if s["step_name"] == request.step_name), 1)
        next_step = next((s for s in steps if s["step_order"] > current_order), None)
        
        if next_step:
            await cases_col.update_one({"id": request.case_id}, {"$set": {
                "current_step": next_step["step_name"],
                "current_step_order": next_step["step_order"]
            }})
        else:
            all_completed = all(s["status"] == "completed" for s in steps if s["step_name"] != request.step_name)
            if all_completed:
                await cases_col.update_one({"id": request.case_id}, {"$set": {"status": "completed"}})
    
    await _log(current_user["id"], "update_step", "case", request.case_id, {"step_name": request.step_name, "status": request.status})
    return {"message": "Step updated successfully"}


@router.put("/{case_id}/assign-manager")
async def assign_manager(case_id: str, case_manager_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    case = await cases_col.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    manager = await users_col.find_one({"id": case_manager_id, "role": "case_manager"})
    if not manager:
        raise HTTPException(status_code=404, detail="Case manager not found")
    
    await cases_col.update_one({"id": case_id}, {"$set": {"case_manager_id": case_manager_id}})
    
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": case_manager_id,
        "title": "Case Assigned", "message": f"You have been assigned to case {case.get('case_id', '')}",
        "type": "case_assigned", "related_id": case_id,
        "read": False, "created_at": datetime.now(timezone.utc)
    })
    
    await _log(current_user["id"], "assign_case_manager", "case", case_id, {"case_manager_id": case_manager_id})
    return {"message": "Case manager reassigned successfully"}


@router.post("/request-document")
async def request_document(request: DocRequest, current_user: dict = Depends(get_current_user)):
    doc_req = {
        "id": str(uuid.uuid4()), "case_id": request.case_id,
        "document_name": request.document_name, "description": request.description,
        "step_order": request.step_order, "doc_type": request.doc_type,
        "status": "pending", "requested_by": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }
    await additional_doc_requests_col.insert_one(doc_req)
    return {"message": "Document requested successfully"}


@router.post("/{case_id}/custom-document-request")
async def custom_document_request(case_id: str, request: DocRequest, current_user: dict = Depends(get_current_user)):
    doc_req = {
        "id": str(uuid.uuid4()), "case_id": case_id,
        "document_name": request.document_name, "description": request.description,
        "step_order": request.step_order, "doc_type": request.doc_type,
        "status": "pending", "requested_by": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }
    await additional_doc_requests_col.insert_one(doc_req)
    
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if case:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": case.get("client_id"),
            "title": "Document Requested",
            "message": f"A new document '{request.document_name}' has been requested",
            "type": "document_request", "related_id": case_id,
            "read": False, "created_at": datetime.now(timezone.utc)
        })
    return {"message": "Document requested successfully"}


# ==================== INFORMATION SHEET ====================

@router.get("/{case_id}/information-sheet")
async def get_information_sheet(case_id: str, current_user: dict = Depends(get_current_user)):
    sheet = await information_sheets_col.find_one({"case_id": case_id}, {"_id": 0})
    if not sheet:
        return {"exists": False, "data": {}}
    
    for f in ["created_at", "updated_at"]:
        if isinstance(sheet.get(f), datetime):
            sheet[f] = sheet[f].isoformat()
    for f in ["date_of_birth", "passport_expiry"]:
        if isinstance(sheet.get(f), datetime):
            sheet[f] = sheet[f].strftime("%Y-%m-%d")
    
    return {"exists": True, "data": sheet}


@router.post("/{case_id}/information-sheet")
async def save_information_sheet(case_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    case = await cases_col.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    data["case_id"] = case_id
    data["client_id"] = case.get("client_id")
    data["updated_at"] = datetime.now(timezone.utc)
    
    existing = await information_sheets_col.find_one({"case_id": case_id})
    if existing:
        await information_sheets_col.update_one({"case_id": case_id}, {"$set": data})
    else:
        data["id"] = str(uuid.uuid4())
        data["created_at"] = datetime.now(timezone.utc)
        await information_sheets_col.insert_one(data)
    
    return {"message": "Information sheet saved successfully"}


@router.get("/stats/my-stats")
async def get_my_stats(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == "case_manager":
        query["case_manager_id"] = current_user["id"]
    elif current_user["role"] == "client":
        query["client_id"] = current_user["id"]
    
    total = await cases_col.count_documents(query)
    active = await cases_col.count_documents({**query, "status": "active"})
    completed = await cases_col.count_documents({**query, "status": "completed"})
    
    return {"total_cases": total, "active_cases": active, "completed_cases": completed}
