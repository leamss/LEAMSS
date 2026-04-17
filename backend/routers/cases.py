"""Cases Router"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from typing import List
from core.database import (
    cases_col, case_steps_col, users_col, products_col, documents_col,
    additional_doc_requests_col, notifications_col, audit_logs_col,
    information_sheets_col, workflow_steps_col, case_transfers_col
)
from core.auth import get_current_user
from core.services import create_notification, notify_users, log_activity
from core.email_service import send_case_step_update_email
import uuid
from datetime import datetime, timezone, date, timedelta

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


# Product-specific intake fields
PRODUCT_INTAKE_FIELDS = {
    "canada_pr": {
        "label": "Canada PR (Express Entry) - Additional Fields",
        "keywords": ["canada", "pr", "express entry", "ircc"],
        "sections": [
            {
                "id": "language_scores",
                "title": "Language Test Scores",
                "fields": [
                    {"key": "primary_language_test", "label": "Primary Language Test", "type": "select", "options": ["IELTS General", "CELPIP General", "PTE Core", "TEF Canada", "TCF Canada"], "required": True},
                    {"key": "language_test_date", "label": "Test Date", "type": "date", "required": True},
                    {"key": "listening_score", "label": "Listening Score", "type": "text", "required": True},
                    {"key": "reading_score", "label": "Reading Score", "type": "text", "required": True},
                    {"key": "writing_score", "label": "Writing Score", "type": "text", "required": True},
                    {"key": "speaking_score", "label": "Speaking Score", "type": "text", "required": True},
                    {"key": "overall_score", "label": "Overall/CLB Score", "type": "text", "required": True},
                    {"key": "second_language_test", "label": "Second Language Test (French)", "type": "select", "options": ["None", "TEF Canada", "TCF Canada"]},
                    {"key": "second_lang_scores", "label": "Second Language Scores (L/R/W/S)", "type": "text"},
                ]
            },
            {
                "id": "eca_details",
                "title": "Education Credential Assessment (ECA)",
                "fields": [
                    {"key": "eca_body", "label": "ECA Assessing Body", "type": "select", "options": ["WES", "IQAS", "CES", "ICAS", "PEBC", "MCC", "NCDEA"], "required": True},
                    {"key": "eca_reference_number", "label": "ECA Reference Number", "type": "text", "required": True},
                    {"key": "eca_result_date", "label": "ECA Result Date", "type": "date"},
                    {"key": "eca_canadian_equivalent", "label": "Canadian Equivalent", "type": "select", "options": ["Doctoral", "Master's", "Two or more degrees (one 3+ years)", "Bachelor's (3+ years)", "Bachelor's (2 years)", "Diploma (3+ years)", "Diploma (1 year)", "Secondary School"]},
                ]
            },
            {
                "id": "express_entry_details",
                "title": "Express Entry Profile Details",
                "fields": [
                    {"key": "noc_code", "label": "Primary NOC Code (TEER 0/1/2/3)", "type": "text", "required": True},
                    {"key": "noc_job_title", "label": "NOC Job Title", "type": "text", "required": True},
                    {"key": "total_work_experience_years", "label": "Total Skilled Work Experience (years)", "type": "text", "required": True},
                    {"key": "canadian_work_experience_years", "label": "Canadian Work Experience (years)", "type": "text"},
                    {"key": "settlement_funds_cad", "label": "Settlement Funds (CAD)", "type": "text", "required": True},
                    {"key": "provincial_nomination", "label": "Provincial Nomination?", "type": "select", "options": ["No", "Ontario", "British Columbia", "Alberta", "Saskatchewan", "Manitoba", "Nova Scotia", "New Brunswick", "PEI", "NLPD"]},
                    {"key": "lmia_job_offer", "label": "Valid Job Offer/LMIA?", "type": "select", "options": ["No", "Yes - LMIA Exempt", "Yes - With LMIA"]},
                ]
            },
        ]
    },
    "australia_pr": {
        "label": "Australia PR (Skilled Migration) - Additional Fields",
        "keywords": ["australia", "pr", "189", "190", "491", "skilled"],
        "sections": [
            {
                "id": "skills_assessment",
                "title": "Skills Assessment Details",
                "fields": [
                    {"key": "assessing_authority", "label": "Skills Assessment Authority", "type": "select", "options": ["ACS", "VETASSESS", "Engineers Australia", "TRA", "ANMAC", "CPAA", "CAANZ", "AIQS", "Other"], "required": True},
                    {"key": "anzsco_code", "label": "ANZSCO Occupation Code", "type": "text", "required": True},
                    {"key": "anzsco_title", "label": "Nominated Occupation Title", "type": "text", "required": True},
                    {"key": "assessment_outcome", "label": "Assessment Outcome", "type": "select", "options": ["Positive", "Negative", "Pending", "Not Yet Applied"], "required": True},
                    {"key": "assessment_reference", "label": "Assessment Reference Number", "type": "text"},
                    {"key": "assessment_date", "label": "Assessment Date", "type": "date"},
                ]
            },
            {
                "id": "english_test_au",
                "title": "English Language Test",
                "fields": [
                    {"key": "english_test_type", "label": "Test Type", "type": "select", "options": ["PTE Academic", "IELTS (Academic/General)", "TOEFL iBT", "OET", "Cambridge C1 Advanced"], "required": True},
                    {"key": "english_test_date_au", "label": "Test Date", "type": "date", "required": True},
                    {"key": "english_listening", "label": "Listening", "type": "text", "required": True},
                    {"key": "english_reading", "label": "Reading", "type": "text", "required": True},
                    {"key": "english_writing", "label": "Writing", "type": "text", "required": True},
                    {"key": "english_speaking", "label": "Speaking", "type": "text", "required": True},
                    {"key": "english_overall", "label": "Overall Score", "type": "text", "required": True},
                ]
            },
            {
                "id": "points_claim",
                "title": "Points Test Claim",
                "fields": [
                    {"key": "age_points", "label": "Age Points (max 30)", "type": "text"},
                    {"key": "english_points", "label": "English Points (max 20)", "type": "text"},
                    {"key": "experience_points_overseas", "label": "Overseas Experience Points (max 15)", "type": "text"},
                    {"key": "experience_points_australia", "label": "Australian Experience Points (max 20)", "type": "text"},
                    {"key": "qualification_points", "label": "Qualification Points (max 20)", "type": "text"},
                    {"key": "specialist_education_points", "label": "Specialist Education Points (max 10)", "type": "text"},
                    {"key": "state_nomination", "label": "State Nomination (190/491)?", "type": "select", "options": ["No", "NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"]},
                    {"key": "total_points_claimed", "label": "Total Points Claimed", "type": "text", "required": True},
                ]
            },
        ]
    },
    "uk_work": {
        "label": "UK Skilled Worker - Additional Fields",
        "keywords": ["uk", "united kingdom", "skilled worker", "tier 2"],
        "sections": [
            {
                "id": "cos_details",
                "title": "Certificate of Sponsorship (CoS)",
                "fields": [
                    {"key": "cos_reference", "label": "CoS Reference Number", "type": "text", "required": True},
                    {"key": "sponsor_name", "label": "Sponsor/Employer Name", "type": "text", "required": True},
                    {"key": "sponsor_license_number", "label": "Sponsor License Number", "type": "text"},
                    {"key": "soc_code", "label": "SOC Occupation Code", "type": "text", "required": True},
                    {"key": "job_title_uk", "label": "Job Title", "type": "text", "required": True},
                    {"key": "annual_salary_gbp", "label": "Annual Salary (GBP)", "type": "text", "required": True},
                    {"key": "job_start_date", "label": "Job Start Date", "type": "date"},
                ]
            },
        ]
    },
    "student_visa": {
        "label": "Student Visa - Additional Fields",
        "keywords": ["student", "study", "university", "college"],
        "sections": [
            {
                "id": "admission_details",
                "title": "Admission Details",
                "fields": [
                    {"key": "university_name", "label": "University/College Name", "type": "text", "required": True},
                    {"key": "course_name", "label": "Course/Program Name", "type": "text", "required": True},
                    {"key": "course_level", "label": "Course Level", "type": "select", "options": ["Diploma", "Bachelor's", "Postgraduate Diploma", "Master's", "PhD/Doctorate", "Certificate", "Other"]},
                    {"key": "course_start_date", "label": "Course Start Date", "type": "date", "required": True},
                    {"key": "course_end_date", "label": "Course End Date", "type": "date"},
                    {"key": "offer_letter_ref", "label": "Offer Letter/CAS/CoE Reference", "type": "text", "required": True},
                    {"key": "tuition_fees", "label": "Annual Tuition Fees", "type": "text"},
                    {"key": "scholarship_details", "label": "Scholarship (if any)", "type": "text"},
                    {"key": "funding_source", "label": "Funding Source", "type": "select", "options": ["Self-funded", "Family Sponsor", "Education Loan", "Scholarship", "Government Sponsor", "Employer Sponsor"]},
                    {"key": "loan_amount", "label": "Loan Amount (if applicable)", "type": "text"},
                ]
            },
        ]
    },
    "usa_h1b": {
        "label": "USA H-1B - Additional Fields",
        "keywords": ["usa", "h1b", "h-1b", "america"],
        "sections": [
            {
                "id": "h1b_employer",
                "title": "H-1B Employer & Petition Details",
                "fields": [
                    {"key": "petitioner_company", "label": "Petitioning Company Name", "type": "text", "required": True},
                    {"key": "petitioner_ein", "label": "Company EIN", "type": "text"},
                    {"key": "lca_case_number", "label": "LCA Case Number", "type": "text"},
                    {"key": "job_title_h1b", "label": "Job Title (as per LCA)", "type": "text", "required": True},
                    {"key": "soc_code_h1b", "label": "SOC Code", "type": "text"},
                    {"key": "annual_wage_usd", "label": "Annual Wage (USD)", "type": "text", "required": True},
                    {"key": "work_location", "label": "Work Location (City, State)", "type": "text", "required": True},
                    {"key": "beneficiary_education", "label": "Highest Degree", "type": "select", "options": ["Bachelor's", "Master's", "PhD", "Professional Degree"]},
                    {"key": "us_degree", "label": "Is degree from US institution?", "type": "select", "options": ["Yes", "No"]},
                    {"key": "previous_h1b", "label": "Previous H-1B approval?", "type": "select", "options": ["No", "Yes - Same Employer", "Yes - Different Employer"]},
                ]
            },
        ]
    },
}


def _match_product_intake(product_name: str) -> list:
    """Find matching product-specific intake sections"""
    product_lower = (product_name or "").lower()
    matched = []
    for key, config in PRODUCT_INTAKE_FIELDS.items():
        score = sum(1 for kw in config["keywords"] if kw in product_lower)
        if score > 0:
            matched.append((score, config))
    matched.sort(key=lambda x: -x[0])
    return [m[1] for m in matched[:1]]  # Return best match only


@router.get("/info-sheet-schema/{product_name}")
async def get_product_info_sheet_schema(product_name: str, current_user: dict = Depends(get_current_user)):
    """Return info sheet schema enhanced with product-specific sections"""
    base_schema = dict(INFO_SHEET_SCHEMA)
    base_sections = list(base_schema["sections"])

    # Find product-specific sections
    matches = _match_product_intake(product_name)
    product_sections = []
    product_label = ""
    for match in matches:
        product_label = match["label"]
        product_sections.extend(match["sections"])

    return {
        "sections": base_sections,
        "product_sections": product_sections,
        "product_label": product_label,
        "total_fields": sum(len(s.get("fields", [])) + len(s.get("entry_fields", [])) for s in base_sections) + sum(len(s.get("fields", [])) for s in product_sections),
    }


@router.get("/overdue-steps")
async def get_overdue_steps(current_user: dict = Depends(get_current_user)):
    """Get steps that are past their SLA deadline"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    now_str = datetime.now(timezone.utc).isoformat()
    cm_id = current_user["id"] if current_user["role"] == "case_manager" else None
    case_query = {"status": "active"}
    if cm_id:
        case_query["case_manager_id"] = cm_id
    cases = await cases_col.find(case_query, {"_id": 0, "id": 1, "case_id": 1, "client_id": 1}).to_list(500)
    case_ids = [c["id"] for c in cases]
    case_map = {c["id"]: c for c in cases}
    steps = await case_steps_col.find({
        "case_id": {"$in": case_ids},
        "status": {"$in": ["pending", "in_progress"]},
        "deadline": {"$exists": True, "$ne": None}
    }, {"_id": 0}).to_list(1000)
    overdue = []
    approaching = []
    for s in steps:
        dl = s.get("deadline", "")
        if not dl:
            continue
        case_info = case_map.get(s["case_id"], {})
        entry = {
            "step_id": s["id"], "case_id": s["case_id"], "case_number": case_info.get("case_id", ""),
            "step_name": s["step_name"], "step_order": s.get("step_order", 0),
            "deadline": dl, "status": s["status"], "sla_days": s.get("sla_days", 0)
        }
        try:
            dl_dt = datetime.fromisoformat(dl.replace("Z", "+00:00"))
            diff = (dl_dt - datetime.now(timezone.utc)).days
            if diff < 0:
                entry["overdue_by"] = abs(diff)
                overdue.append(entry)
            elif diff <= 3:
                entry["days_remaining"] = diff
                approaching.append(entry)
        except Exception:
            continue
    return {"overdue": overdue, "approaching": approaching, "total_overdue": len(overdue), "total_approaching": len(approaching)}


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

    # Milestone notification to client about step update
    if case.get("client_id"):
        client = await users_col.find_one({"id": case["client_id"]}, {"_id": 0})
        if client:
            milestone_msg = f"Step '{request.step_name}' has been marked as {request.status.replace('_', ' ')}."
            if request.status == "completed":
                milestone_msg = f"Milestone achieved! Step '{request.step_name}' is now complete."
            await create_notification(
                case["client_id"],
                f"Case Update: {case.get('case_id', '')}",
                milestone_msg,
                "milestone",
                request.case_id
            )
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
            "repeatable": True, "max_entries": 20, "entry_prefix": "child",
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
            "repeatable": True, "max_entries": 20, "entry_prefix": "dependent",
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
            "repeatable": True, "max_entries": 20, "entry_prefix": "qualification",
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
            "repeatable": True, "max_entries": 20, "entry_prefix": "employment",
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


@router.get("/workload/summary")
async def get_workload_summary(current_user: dict = Depends(get_current_user)):
    """Smart Workload Dashboard data for Case Manager"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Case Manager or Admin only")
    
    cm_id = current_user["id"] if current_user["role"] == "case_manager" else None
    case_query = {"case_manager_id": cm_id} if cm_id else {}
    
    cases = await cases_col.find({**case_query, "status": "active"}, {"_id": 0}).to_list(500)
    case_ids = [c["id"] for c in cases]
    
    # Pending document reviews
    pending_docs = await documents_col.find({
        "case_id": {"$in": case_ids},
        "status": "pending"
    }, {"_id": 0}).to_list(500)
    
    # Expiring documents
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=30)
    expiring_docs = await documents_col.find({
        "case_id": {"$in": case_ids},
        "expiry_date": {"$exists": True, "$ne": None, "$lte": soon.isoformat() if isinstance(soon, datetime) else soon}
    }, {"_id": 0}).to_list(200)
    
    # Additional doc requests pending
    pending_requests = await additional_doc_requests_col.find({
        "case_id": {"$in": case_ids},
        "status": "pending"
    }, {"_id": 0}).to_list(200)
    
    # Steps nearing completion (in_progress)
    in_progress_steps = await case_steps_col.find({
        "case_id": {"$in": case_ids},
        "status": "in_progress"
    }, {"_id": 0}).to_list(500)
    
    # Build urgent tasks list
    urgent_tasks = []
    
    for doc in pending_docs:
        case = next((c for c in cases if c["id"] == doc.get("case_id")), {})
        urgent_tasks.append({
            "type": "doc_review",
            "priority": "high",
            "title": f"Review: {doc.get('document_type', 'Document')}",
            "subtitle": f"{case.get('client_name', '')} - {case.get('case_id', '')}",
            "case_id": doc.get("case_id"),
            "entity_id": doc.get("id"),
            "created_at": doc.get("uploaded_at", "")
        })
    
    for req in pending_requests:
        case = next((c for c in cases if c["id"] == req.get("case_id")), {})
        urgent_tasks.append({
            "type": "additional_doc",
            "priority": "medium",
            "title": f"Awaiting: {req.get('document_name', 'Document')}",
            "subtitle": f"{case.get('client_name', '')} - {case.get('case_id', '')}",
            "case_id": req.get("case_id"),
            "entity_id": req.get("id"),
            "created_at": req.get("requested_at", "")
        })
    
    for doc in expiring_docs:
        case = next((c for c in cases if c["id"] == doc.get("case_id")), {})
        urgent_tasks.append({
            "type": "expiry_alert",
            "priority": "critical" if doc.get("expiry_date", "") < now.isoformat() else "medium",
            "title": f"Expiry: {doc.get('document_type', 'Document')}",
            "subtitle": f"{case.get('client_name', '')} - Expires {doc.get('expiry_date', '')[:10]}",
            "case_id": doc.get("case_id"),
            "entity_id": doc.get("id"),
            "created_at": doc.get("expiry_date", "")
        })
    
    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    urgent_tasks.sort(key=lambda t: priority_order.get(t["priority"], 3))
    
    # Case distribution by status
    status_counts = {}
    all_cases = await cases_col.find(case_query if cm_id else {}, {"_id": 0, "status": 1}).to_list(1000)
    for c in all_cases:
        s = c.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    
    return {
        "active_cases": len(cases),
        "pending_reviews": len(pending_docs),
        "expiring_documents": len(expiring_docs),
        "pending_additional_docs": len(pending_requests),
        "in_progress_steps": len(in_progress_steps),
        "urgent_tasks": urgent_tasks[:20],
        "total_urgent": len(urgent_tasks),
        "case_distribution": status_counts
    }



# ============ PHASE 6A: BULK OPERATIONS ============

class BulkAdvanceRequest(BaseModel):
    case_ids: List[str]
    notes: str = ""


@router.post("/bulk-advance")
async def bulk_advance_cases(request: BulkAdvanceRequest, current_user: dict = Depends(get_current_user)):
    """Advance multiple cases to next step"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    results = []
    for cid in request.case_ids:
        try:
            case = await cases_col.find_one({"id": cid}, {"_id": 0})
            if not case:
                results.append({"case_id": cid, "status": "error", "message": "Not found"})
                continue
            steps = await case_steps_col.find({"case_id": cid}, {"_id": 0}).sort("step_order", 1).to_list(100)
            current = next((s for s in steps if s["status"] in ["pending", "in_progress"]), None)
            if not current:
                results.append({"case_id": cid, "status": "skipped", "message": "No pending step"})
                continue
            await case_steps_col.update_one({"id": current["id"]}, {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc), "notes": request.notes}})
            next_step = next((s for s in steps if s["step_order"] > current["step_order"]), None)
            if next_step:
                await case_steps_col.update_one({"id": next_step["id"]}, {"$set": {"status": "in_progress", "started_at": datetime.now(timezone.utc)}})
                await cases_col.update_one({"id": cid}, {"$set": {"current_step": next_step["step_name"], "current_step_order": next_step["step_order"]}})
            else:
                await cases_col.update_one({"id": cid}, {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc)}})
            await log_activity(current_user["id"], current_user["name"], "bulk_advance_step", "case", cid, {"step": current["step_name"]})
            results.append({"case_id": cid, "status": "advanced", "step": current["step_name"]})
        except Exception as e:
            results.append({"case_id": cid, "status": "error", "message": str(e)})
    return {"results": results, "advanced": sum(1 for r in results if r["status"] == "advanced")}


# ============ SLA/DEADLINE TRACKING ============

class SetStepDeadline(BaseModel):
    case_id: str
    step_name: str
    deadline: str
    sla_days: Optional[int] = None


@router.post("/set-step-deadline")
async def set_step_deadline(request: SetStepDeadline, current_user: dict = Depends(get_current_user)):
    """Set SLA deadline for a case step"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    step = await case_steps_col.find_one({"case_id": request.case_id, "step_name": request.step_name}, {"_id": 0})
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    await case_steps_col.update_one({"id": step["id"]}, {"$set": {"deadline": request.deadline, "sla_days": request.sla_days or 0}})
    await log_activity(current_user["id"], current_user["name"], "set_step_deadline", "case_step", step["id"], {"deadline": request.deadline})
    return {"message": "Deadline set", "step": request.step_name, "deadline": request.deadline}


# ============ AUTO CASE ASSIGNMENT ============

class AutoAssignRequest(BaseModel):
    case_id: str
    preferred_language: Optional[str] = None


@router.post("/auto-assign")
async def auto_assign_case(request: AutoAssignRequest, current_user: dict = Depends(get_current_user)):
    """Auto-assign case to least-loaded case manager, optionally matching language"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    case = await cases_col.find_one({"id": request.case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    cms = await users_col.find({"role": "case_manager", "status": "active"}, {"_id": 0}).to_list(100)
    if not cms:
        raise HTTPException(status_code=400, detail="No active case managers")
    # Count active cases per CM
    workloads = {}
    for cm in cms:
        count = await cases_col.count_documents({"case_manager_id": cm["id"], "status": "active"})
        workloads[cm["id"]] = {"count": count, "cm": cm}
    # Prefer language match if specified
    lang = request.preferred_language
    if lang:
        lang_cms = [cid for cid, w in workloads.items() if lang.lower() in [l.lower() for l in w["cm"].get("languages", [])]]
        if lang_cms:
            best = min(lang_cms, key=lambda cid: workloads[cid]["count"])
        else:
            best = min(workloads, key=lambda cid: workloads[cid]["count"])
    else:
        best = min(workloads, key=lambda cid: workloads[cid]["count"])
    chosen = workloads[best]["cm"]
    await cases_col.update_one({"id": request.case_id}, {"$set": {"case_manager_id": chosen["id"], "status": "active"}})
    await create_notification(chosen["id"], "New Case Assigned", f"Case {case.get('case_id','')} auto-assigned to you", "case_assigned", request.case_id)
    await log_activity(current_user["id"], current_user["name"], "auto_assign_case", "case", request.case_id, {"assigned_to": chosen["name"], "workload": workloads[best]["count"]})
    return {"message": f"Case assigned to {chosen['name']}", "case_manager_id": chosen["id"], "case_manager_name": chosen["name"], "active_cases": workloads[best]["count"]}


# ============ CASE TRANSFER ============

class CaseTransferRequest(BaseModel):
    case_id: str
    to_case_manager_id: str
    reason: str = ""


@router.post("/transfer")
async def transfer_case(request: CaseTransferRequest, current_user: dict = Depends(get_current_user)):
    """Transfer case from one CM to another with history tracking"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    case = await cases_col.find_one({"id": request.case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    to_cm = await users_col.find_one({"id": request.to_case_manager_id, "role": "case_manager"}, {"_id": 0})
    if not to_cm:
        raise HTTPException(status_code=404, detail="Target case manager not found")
    from_cm_id = case.get("case_manager_id", "")
    from_cm = await users_col.find_one({"id": from_cm_id}, {"_id": 0, "name": 1}) if from_cm_id else None
    transfer = {
        "id": str(uuid.uuid4()), "case_id": request.case_id,
        "from_cm_id": from_cm_id, "from_cm_name": from_cm["name"] if from_cm else "Unassigned",
        "to_cm_id": request.to_case_manager_id, "to_cm_name": to_cm["name"],
        "reason": request.reason, "transferred_by": current_user["id"],
        "transferred_by_name": current_user["name"], "created_at": datetime.now(timezone.utc)
    }
    await case_transfers_col.insert_one(transfer)
    transfer.pop("_id", None)
    await cases_col.update_one({"id": request.case_id}, {"$set": {"case_manager_id": request.to_case_manager_id}})
    await create_notification(request.to_case_manager_id, "Case Transferred", f"Case {case.get('case_id','')} transferred to you. Reason: {request.reason}", "case_transfer", request.case_id)
    if from_cm_id:
        await create_notification(from_cm_id, "Case Transferred", f"Case {case.get('case_id','')} transferred to {to_cm['name']}", "case_transfer", request.case_id)
    await log_activity(current_user["id"], current_user["name"], "transfer_case", "case", request.case_id, {"from": from_cm["name"] if from_cm else "None", "to": to_cm["name"]})
    return {"message": f"Case transferred to {to_cm['name']}", "transfer_id": transfer["id"]}


@router.get("/transfer-history/{case_id}")
async def get_transfer_history(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get transfer history for a case"""
    transfers = await case_transfers_col.find({"case_id": case_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for t in transfers:
        if isinstance(t.get("created_at"), datetime):
            t["created_at"] = t["created_at"].isoformat()
    return transfers
