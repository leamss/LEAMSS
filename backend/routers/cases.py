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
from core.services import create_notification, notify_users, log_activity
from core.email_service import send_case_step_update_email
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
    step_order: Optional[int] = None
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


async def _enrich_cases(cases):
    """Batch-enrich cases with user/product/step data to avoid N+1 queries"""
    if not cases:
        return cases
    
    # Collect all unique IDs
    user_ids = set()
    product_ids = set()
    case_ids = []
    for c in cases:
        case_ids.append(c["id"])
        for field in ["client_id", "case_manager_id", "partner_id"]:
            if c.get(field):
                user_ids.add(c[field])
        if c.get("product_id"):
            product_ids.add(c["product_id"])
    
    # Batch fetch
    users_list = await users_col.find({"id": {"$in": list(user_ids)}}, {"_id": 0, "password": 0}).to_list(500) if user_ids else []
    products_list = await products_col.find({"id": {"$in": list(product_ids)}}, {"_id": 0}).to_list(500) if product_ids else []
    all_steps = await case_steps_col.find({"case_id": {"$in": case_ids}}, {"_id": 0}).to_list(5000)
    all_docs = await additional_doc_requests_col.find({"case_id": {"$in": case_ids}}, {"_id": 0}).to_list(5000)
    
    users_map = {u["id"]: u for u in users_list}
    products_map = {p["id"]: p for p in products_list}
    steps_map = {}
    for s in all_steps:
        steps_map.setdefault(s["case_id"], []).append(s)
    docs_map = {}
    for d in all_docs:
        docs_map.setdefault(d["case_id"], []).append(d)
    
    for case in cases:
        client = users_map.get(case.get("client_id"))
        product = products_map.get(case.get("product_id"))
        manager = users_map.get(case.get("case_manager_id"))
        partner = users_map.get(case.get("partner_id"))
        
        case["client_name"] = client["name"] if client else "N/A"
        case["client_email"] = client.get("email", "") if client else ""
        case["product_name"] = product["name"] if product else "N/A"
        case["case_manager_name"] = manager["name"] if manager else "Not Assigned"
        case["partner_name"] = partner["name"] if partner else "N/A"
        
        case_steps = steps_map.get(case["id"], [])
        case_steps.sort(key=lambda x: x.get("step_order", 0))
        case["steps"] = case_steps
        
        additional_docs = docs_map.get(case["id"], [])
        for doc in additional_docs:
            for f in ["created_at", "due_date", "expiry_date"]:
                if isinstance(doc.get(f), datetime):
                    doc[f] = doc[f].isoformat()
        case["additional_doc_requests"] = additional_docs
        
        for f in ["created_at", "updated_at"]:
            if isinstance(case.get(f), datetime):
                case[f] = case[f].isoformat()
    
    return cases


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
    return await _enrich_cases(cases)


@router.get("/unassigned")
async def get_unassigned_cases(current_user: dict = Depends(get_current_user)):
    """Get cases that are pending case manager assignment (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    query = {
        "$or": [
            {"case_manager_id": None},
            {"case_manager_id": ""},
            {"status": "pending_assignment"}
        ]
    }
    cases = await cases_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    enriched = await _enrich_cases(cases)

    # Also attach sale discount info for context
    from core.database import db
    sales_col = db["sales"]
    for case in enriched:
        if case.get("sale_id"):
            sale = await sales_col.find_one({"id": case["sale_id"]}, {
                "_id": 0, "fee_amount": 1, "fee_before_discount": 1,
                "total_discount_amount": 1, "promo_code": 1,
                "additional_discount_percentage": 1, "amount_received": 1,
                "payment_status": 1
            })
            if sale:
                case["sale_fee"] = sale.get("fee_amount", 0)
                case["sale_discount"] = sale.get("total_discount_amount", 0)
                case["sale_promo"] = sale.get("promo_code")
                case["sale_payment_status"] = sale.get("payment_status", "pending")
                case["sale_received"] = sale.get("amount_received", 0)

    return enriched


@router.get("/my-cases")
async def get_my_cases(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == "case_manager":
        query["case_manager_id"] = current_user["id"]
    elif current_user["role"] == "client":
        query["client_id"] = current_user["id"]
    
    cases = await cases_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return await _enrich_cases(cases)


@router.get("/info-sheet-schema")
async def get_info_sheet_schema(current_user: dict = Depends(get_current_user)):
    """Return the complete information sheet field schema"""
    return INFO_SHEET_SCHEMA


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
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Only admin or case manager can update steps")

    case = await cases_col.find_one({"id": request.case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get all steps for this case
    steps = await case_steps_col.find({"case_id": request.case_id}, {"_id": 0}).sort("step_order", 1).to_list(100)
    current_step = next((s for s in steps if s["step_name"] == request.step_name), None)
    if not current_step:
        raise HTTPException(status_code=404, detail="Step not found")

    target_order = current_step.get("step_order", 1)

    # ENFORCEMENT: Cannot update a step if previous steps are not completed
    for s in steps:
        if s["step_order"] < target_order and s.get("status") != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update step '{request.step_name}' — previous step '{s['step_name']}' (Step {s['step_order']}) is not completed yet."
            )

    # ENFORCEMENT: If marking as completed, check required documents for this step
    if request.status == "completed":
        workflow_steps = await workflow_steps_col.find(
            {"product_id": case.get("product_id"), "step_name": request.step_name}, {"_id": 0}
        ).to_list(1)
        if workflow_steps:
            required_docs = workflow_steps[0].get("required_documents", [])
            mandatory_docs = [d for d in required_docs if d.get("is_mandatory", True)]
            if mandatory_docs:
                case_docs = await documents_col.find({"case_id": request.case_id}, {"_id": 0}).to_list(200)
                uploaded_names = [d.get("document_type", "").lower().strip() for d in case_docs]
                for req in mandatory_docs:
                    doc_name = req.get("doc_name", "").lower().strip()
                    found = any(doc_name in ut or ut in doc_name for ut in uploaded_names)
                    if not found:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot complete step '{request.step_name}' — required document '{req.get('doc_name')}' is missing. Please ensure all required documents are uploaded."
                        )

    await case_steps_col.update_one(
        {"case_id": request.case_id, "step_name": request.step_name},
        {"$set": {"status": request.status, "notes": request.notes, "updated_at": datetime.now(timezone.utc)}}
    )

    if request.status == "completed":
        current_order = target_order
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

    # Email notification to client about step update
    if case.get("client_id"):
        client = await users_col.find_one({"id": case["client_id"]}, {"_id": 0})
        if client:
            await send_case_step_update_email(
                client.get("email", ""), client.get("name", ""),
                case.get("case_id", request.case_id), request.step_name, request.status
            )

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
    
    # Assign manager and activate case if it was pending assignment
    update_fields = {"case_manager_id": case_manager_id}
    if case.get("status") == "pending_assignment":
        update_fields["status"] = "active"
    
    await cases_col.update_one({"id": case_id}, {"$set": update_fields})
    
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": case_manager_id,
        "title": "Case Assigned", "message": f"You have been assigned to case {case.get('case_id', '')}",
        "type": "case_assigned", "related_id": case_id,
        "read": False, "created_at": datetime.now(timezone.utc)
    })
    
    await _log(current_user["id"], "assign_case_manager", "case", case_id, {"case_manager_id": case_manager_id})
    await log_activity(current_user["id"], current_user["name"], "assigned_manager", "case", case_id,
        f"Assigned case manager {manager['name']} to case {case.get('case_number', case_id)}")
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
        return {"exists": False, "data": {}, "required_fields": [], "completion": {}}

    for f in list(sheet.keys()):
        if isinstance(sheet.get(f), datetime):
            sheet[f] = sheet[f].isoformat()

    # Calculate field completion from all section fields
    required_fields = sheet.get("required_fields", [])
    filled_count = 0
    missing_fields = []
    for field in required_fields:
        val = sheet.get(field)
        if val and str(val).strip() and str(val).strip() != "null":
            filled_count += 1
        else:
            missing_fields.append(field)

    completion_pct = round((filled_count / len(required_fields)) * 100) if required_fields else 100

    return {
        "exists": True,
        "data": sheet,
        "required_fields": required_fields,
        "completion": {
            "total_fields": len(required_fields),
            "filled_count": filled_count,
            "missing_fields": missing_fields,
            "percentage": completion_pct,
            "is_complete": completion_pct == 100
        }
    }


# Complete field schema matching the Required Information Sheet document
INFO_SHEET_SCHEMA = {
    "sections": [
        {
            "id": "personal_details",
            "title": "Personal Details",
            "fields": [
                {"key": "given_names", "label": "Given Name(s)", "type": "text", "required": True},
                {"key": "family_name", "label": "Family Name", "type": "text", "required": True},
                {"key": "other_names", "label": "Other Names (if any)", "type": "text"},
                {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Other"], "required": True},
                {"key": "date_of_birth", "label": "Date of Birth", "type": "date", "required": True},
                {"key": "country_of_birth", "label": "Country of Birth", "type": "text", "required": True},
                {"key": "city_of_birth", "label": "City/Town of Birth", "type": "text"},
                {"key": "address", "label": "Address for Communication", "type": "textarea", "required": True},
                {"key": "email", "label": "Email ID", "type": "text", "required": True},
                {"key": "contact_number", "label": "Contact Number", "type": "text", "required": True},
                {"key": "alternative_number", "label": "Alternative Number", "type": "text"},
                {"key": "aadhaar_number", "label": "Aadhaar Card Number", "type": "text"},
                {"key": "nationality", "label": "Nationality", "type": "text", "required": True},
                {"key": "passport_number", "label": "Passport No.", "type": "text", "required": True},
                {"key": "passport_issue_date", "label": "Passport Issue Date", "type": "date", "required": True},
                {"key": "passport_expiry_date", "label": "Passport Expiry Date", "type": "date", "required": True},
                {"key": "passport_place_of_issue", "label": "Passport Place of Issue", "type": "text"},
                {"key": "marital_status", "label": "Marital Status", "type": "select", "options": ["Single", "Married", "Divorced", "Widowed", "Separated"], "required": True},
                {"key": "spouse_name", "label": "Spouse Name (if married)", "type": "text"},
                {"key": "father_name", "label": "Father's Name", "type": "text", "required": True},
                {"key": "mother_name", "label": "Mother's Name", "type": "text", "required": True},
            ]
        },
        {
            "id": "family_chart",
            "title": "Family Chart",
            "fields": [
                {"key": "father_dob", "label": "Father's Date of Birth", "type": "date"},
                {"key": "father_place_of_birth", "label": "Father's Place of Birth", "type": "text"},
                {"key": "mother_dob", "label": "Mother's Date of Birth", "type": "date"},
                {"key": "mother_place_of_birth", "label": "Mother's Place of Birth", "type": "text"},
                {"key": "siblings_details", "label": "Siblings (Name, DOB, Place of Birth - one per line)", "type": "textarea"},
                {"key": "date_of_marriage", "label": "Date of Marriage", "type": "date"},
                {"key": "spouse_dob", "label": "Spouse Date of Birth", "type": "date"},
                {"key": "spouse_place_of_birth", "label": "Spouse Place of Birth", "type": "text"},
                {"key": "spouse_passport_number", "label": "Spouse Passport Number", "type": "text"},
                {"key": "spouse_passport_issue_date", "label": "Spouse Passport Issue Date", "type": "date"},
                {"key": "spouse_passport_expiry_date", "label": "Spouse Passport Expiry Date", "type": "date"},
                {"key": "spouse_passport_place", "label": "Spouse Passport Place of Issue", "type": "text"},
            ]
        },
        {
            "id": "dependent_children",
            "title": "Dependent Children",
            "repeatable": True, "max_entries": 4, "entry_prefix": "child",
            "entry_fields": [
                {"key": "name", "label": "Child Full Name", "type": "text"},
                {"key": "dob", "label": "Date of Birth", "type": "date"},
                {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female"]},
                {"key": "place_of_birth", "label": "Place of Birth", "type": "text"},
                {"key": "passport_number", "label": "Passport Number", "type": "text"},
                {"key": "passport_issue_date", "label": "Passport Issue Date", "type": "date"},
                {"key": "passport_expiry_date", "label": "Passport Expiry Date", "type": "date"},
                {"key": "migrating", "label": "Migrating with you?", "type": "select", "options": ["Yes", "No"]},
            ]
        },
        {
            "id": "migrating_dependents",
            "title": "Migrating Dependents (Spouse & Children)",
            "repeatable": True, "max_entries": 5, "entry_prefix": "dependent",
            "entry_fields": [
                {"key": "full_name", "label": "Full Name", "type": "text"},
                {"key": "relation", "label": "Relation with Main Applicant", "type": "text"},
                {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female"]},
                {"key": "migrating_with_you", "label": "Migrating with you?", "type": "select", "options": ["Yes", "No"]},
                {"key": "residing_country", "label": "Presently Residing in Country", "type": "text"},
                {"key": "resident_or_citizen", "label": "Permanent Resident or Citizen", "type": "text"},
                {"key": "postal_code", "label": "Postal Code", "type": "text"},
            ]
        },
        {
            "id": "qualifications",
            "title": "Qualifications",
            "repeatable": True, "max_entries": 4, "entry_prefix": "qualification",
            "entry_fields": [
                {"key": "name", "label": "Qualification Name", "type": "text"},
                {"key": "field_of_study", "label": "Major Field of Study", "type": "text"},
                {"key": "awarding_body", "label": "Awarding Body", "type": "text"},
                {"key": "institute_name", "label": "Institute Name", "type": "text"},
                {"key": "institute_address", "label": "Institute Address", "type": "text"},
                {"key": "course_length", "label": "Course Length", "type": "text"},
                {"key": "start_date", "label": "Course Start Date", "type": "date"},
                {"key": "end_date", "label": "Course End Date", "type": "date"},
                {"key": "award_date", "label": "Course Awarded Date", "type": "date"},
                {"key": "study_mode", "label": "Full Time / Part Time", "type": "select", "options": ["Full Time", "Part Time"]},
            ]
        },
        {
            "id": "employment",
            "title": "Employment History",
            "repeatable": True, "max_entries": 4, "entry_prefix": "employment",
            "entry_fields": [
                {"key": "business_name", "label": "Business/Company Name", "type": "text"},
                {"key": "address", "label": "Employment Address", "type": "text"},
                {"key": "website", "label": "Employer Website", "type": "text"},
                {"key": "job_title", "label": "Job Title", "type": "text"},
                {"key": "start_date", "label": "Start Date", "type": "date"},
                {"key": "end_date", "label": "End Date (leave blank if current)", "type": "date"},
                {"key": "working_hours", "label": "Working Hours (per week)", "type": "text"},
            ]
        },
    ]
}


@router.post("/{case_id}/information-sheet")
async def save_information_sheet(case_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    case = await cases_col.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    data["case_id"] = case_id
    data["client_id"] = case.get("client_id")
    data["updated_at"] = datetime.now(timezone.utc)
    data["updated_by"] = current_user["id"]
    data["updated_by_role"] = current_user["role"]
    
    existing = await information_sheets_col.find_one({"case_id": case_id})
    if existing:
        # Track change history
        history_entry = {
            "changed_by": current_user["id"],
            "changed_by_name": current_user.get("name", ""),
            "changed_by_role": current_user["role"],
            "changed_at": datetime.now(timezone.utc).isoformat(),
            "changes_summary": data.get("changes_summary", "Updated information sheet")
        }
        await information_sheets_col.update_one({"case_id": case_id}, {
            "$set": data,
            "$push": {"change_history": history_entry}
        })
    else:
        data["id"] = str(uuid.uuid4())
        data["created_at"] = datetime.now(timezone.utc)
        data["change_history"] = []
        await information_sheets_col.insert_one(data)
    
    return {"message": "Information sheet saved successfully"}


@router.post("/{case_id}/request-info-sheet")
async def request_info_sheet(case_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Case manager requests client to fill information sheet with specific required fields"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")

    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    message = data.get("message", "Please fill/update your information sheet.")
    required_fields = data.get("required_fields", [
        "full_name", "date_of_birth", "gender", "nationality", "passport_number",
        "passport_expiry", "address", "phone", "email", "education_level",
        "occupation", "employer", "marital_status", "work_experience_years"
    ])

    # Create notification for client
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": case.get("client_id"),
        "title": "Information Sheet Required",
        "message": message,
        "type": "info_sheet_request",
        "related_id": case_id,
        "metadata": {"required_fields": required_fields},
        "read": False,
        "created_at": datetime.now(timezone.utc)
    })

    # Update case and info sheet with required fields
    await cases_col.update_one({"id": case_id}, {"$set": {
        "info_sheet_requested": True,
        "info_sheet_request_message": message,
        "info_sheet_requested_at": datetime.now(timezone.utc),
        "info_sheet_requested_by": current_user["id"],
        "info_sheet_required_fields": required_fields
    }})

    # Ensure info sheet exists with required_fields metadata
    existing = await information_sheets_col.find_one({"case_id": case_id})
    if not existing:
        await information_sheets_col.insert_one({
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "client_id": case.get("client_id"),
            "required_fields": required_fields,
            "status": "pending",
            "created_at": datetime.now(timezone.utc)
        })
    else:
        await information_sheets_col.update_one({"case_id": case_id}, {"$set": {
            "required_fields": required_fields,
            "status": "pending"
        }})

    return {"message": "Information sheet request sent to client", "required_fields": required_fields}


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
