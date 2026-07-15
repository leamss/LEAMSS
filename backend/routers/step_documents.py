"""Step-wise Document Management Router
- Admin: Add/remove default documents per step
- CM: Request documents (step-level or additional)
- Client: View step-wise document requirements + upload
"""
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from core.database import (
    db, cases_col, users_col, documents_col, notifications_col,
    audit_logs_col, workflow_steps_col, case_steps_col, additional_doc_requests_col
)
from core.auth import get_current_user

router = APIRouter(prefix="/step-documents", tags=["Step Documents"])

doc_requests_col = db["document_requests"]


# ============ CM: REQUEST DOCUMENTS (STEP-LEVEL) ============

class StepDocRequest(BaseModel):
    case_id: str
    step_name: str
    doc_name: str
    is_mandatory: bool = True
    notes: str = ""
    tag: str = "mandatory"  # mandatory, optional, conditional


@router.post("/request-step-doc")
async def request_step_document(data: StepDocRequest, current_user: dict = Depends(get_current_user)):
    """CM requests a document within a specific step (client-specific)"""
    if current_user["role"] not in ["case_manager", "admin"]:
        raise HTTPException(status_code=403, detail="CM or Admin only")

    case = await cases_col.find_one({"id": data.case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Add to case_steps required_documents as CM-added
    step = await case_steps_col.find_one(
        {"case_id": data.case_id, "step_name": data.step_name}, {"_id": 0}
    )
    if not step:
        raise HTTPException(status_code=404, detail="Step not found in case")

    existing_docs = step.get("required_documents", [])
    # Check if doc already exists (handle both 'doc_name' and 'name' fields)
    if any(_get_doc_name(d).lower() == data.doc_name.lower() for d in existing_docs):
        raise HTTPException(status_code=400, detail="Document already exists in this step")

    new_doc = {
        "doc_name": data.doc_name,
        "is_mandatory": data.is_mandatory,
        "tag": data.tag,
        "notes": data.notes,
        "added_by": current_user["id"],
        "added_by_name": current_user.get("name", ""),
        "added_by_role": current_user["role"],
        "added_at": datetime.now(timezone.utc).isoformat(),
        "source": "cm_request",  # vs "admin_default"
    }

    await case_steps_col.update_one(
        {"case_id": data.case_id, "step_name": data.step_name},
        {"$push": {"required_documents": new_doc}}
    )

    # Notify client
    if case.get("client_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": case["client_id"],
            "title": "Document Requested",
            "message": f"'{data.doc_name}' required for step '{data.step_name}'",
            "type": "document_request", "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "step_doc_requested", "entity_type": "case_step",
        "entity_id": data.case_id,
        "new_value": {"step": data.step_name, "doc": data.doc_name, "client_id": case.get("client_id")},
        "created_at": datetime.now(timezone.utc)
    })

    return {"message": f"Document '{data.doc_name}' added to step '{data.step_name}'"}


# ============ CM: REQUEST ADDITIONAL DOCUMENTS (SEPARATE SECTION) ============

class AdditionalDocRequest(BaseModel):
    case_id: str
    doc_name: str
    is_mandatory: bool = True
    notes: str = ""
    tag: str = "mandatory"


@router.post("/request-additional")
async def request_additional_document(data: AdditionalDocRequest, current_user: dict = Depends(get_current_user)):
    """CM requests an additional document (not tied to any step)"""
    if current_user["role"] not in ["case_manager", "admin"]:
        raise HTTPException(status_code=403, detail="CM or Admin only")

    case = await cases_col.find_one({"id": data.case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    request_doc = {
        "id": str(uuid.uuid4()),
        "case_id": data.case_id,
        "client_id": case.get("client_id", ""),
        "doc_name": data.doc_name,
        "is_mandatory": data.is_mandatory,
        "tag": data.tag,
        "notes": data.notes,
        "status": "pending",  # pending, uploaded, verified, rejected
        "requested_by": current_user["id"],
        "requested_by_name": current_user.get("name", ""),
        "section": "additional",  # separate from step docs
        "created_at": datetime.now(timezone.utc),
    }
    await doc_requests_col.insert_one(request_doc)
    request_doc.pop("_id", None)

    # Notify client
    if case.get("client_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": case["client_id"],
            "title": "Additional Document Requested",
            "message": f"'{data.doc_name}' has been requested for your case.",
            "type": "additional_doc_request", "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    return {"message": f"Additional document '{data.doc_name}' requested", "id": request_doc["id"]}


# ============ HELPER: normalize doc_name from both "doc_name" and "name" ============

def _get_doc_name(rd: dict) -> str:
    """Get document name from either 'doc_name' or 'name' field"""
    return rd.get("doc_name") or rd.get("name") or ""


# ============ GET STEP-WISE DOCUMENT VIEW (CLIENT + CM) ============

@router.get("/case/{case_id}")
async def get_stepwise_documents(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get complete step-wise document structure for a case.
    Merges admin-default docs from workflow_steps with case-specific docs from case_steps.
    """
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Access check
    if current_user["role"] == "client" and current_user["id"] != case.get("client_id"):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get case steps
    case_steps = await case_steps_col.find(
        {"case_id": case_id}, {"_id": 0}
    ).sort("step_order", 1).to_list(50)

    # Get latest admin-defined workflow steps for this product
    product_id = case.get("product_id", "")
    admin_wf_steps = []
    if product_id:
        admin_wf_steps = await workflow_steps_col.find(
            {"product_id": product_id}, {"_id": 0}
        ).sort("step_order", 1).to_list(50)

    # Build lookup: step_name -> admin default required_documents
        # Build lookup of client-visible intake document fields by step
        # Build step-wise documents from Workflow Builder intake form
    admin_docs_by_step = {}

    for aws in admin_wf_steps:
        step_name = aws.get("step_name", "")
        intake_documents = []

        for section in aws.get("sections", []):
            for field in section.get("fields", []):

                # Only file upload fields are documents
                # if field.get("field_type") != "file":
                #     continue

                filled_by = field.get("filled_by", "client")

                # Hide CM-only fields from client
                if (
                    current_user["role"] == "client"
                    and filled_by not in ("client", "both")
                ):
                    continue

                intake_documents.append({
                    "key": field.get("key", ""),
                    "doc_name": field.get("label", ""),
                    "label": field.get("label", ""),
                    "field_type": field.get("field_type", "text"),
                    "options": field.get("options", []),
                    "is_mandatory": field.get("required", False),
                    "mandatory": field.get("required", False),
                    "tag": (
                        "mandatory"
                        if field.get("required", False)
                        else "optional"
                    ),
                    "notes": field.get("help_text", ""),
                    "description": field.get("help_text", ""),
                    "source": "intake_form",
                    "filled_by": filled_by,
                })

        admin_docs_by_step[step_name] = intake_documents
    uploaded_docs = await documents_col.find(
        {"case_id": case_id}, {"_id": 0, "file_path": 0}
    ).to_list(500)

    for d in uploaded_docs:
        for f in ["uploaded_at", "reviewed_at", "expiry_date"]:
            if isinstance(d.get(f), datetime):
                d[f] = d[f].isoformat()

    # Get additional doc requests
    additional_requests = await doc_requests_col.find(
        {"case_id": case_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)

    # Also fetch from the legacy additional_doc_requests collection
    legacy_requests = await additional_doc_requests_col.find(
        {"case_id": case_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)

    # Merge legacy requests (avoid duplicates by id)
    existing_ids = {r.get("id") for r in additional_requests}
    for lr in legacy_requests:
        if lr.get("id") not in existing_ids:
            # Normalize field names
            lr["doc_name"] = lr.get("doc_name") or lr.get("document_name") or ""
            lr["notes"] = lr.get("notes") or lr.get("description") or ""
            lr["requested_by_name"] = lr.get("requested_by_name") or lr.get("requested_by") or ""
            lr["is_mandatory"] = lr.get("is_mandatory", True)
            lr["tag"] = lr.get("tag", "mandatory")
            lr["section"] = "additional"
            additional_requests.append(lr)

    for r in additional_requests:
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
        matching_doc = next(
            (d for d in uploaded_docs if d.get("additional_request_id") == r.get("id")),
            None
        )
        r["uploaded_doc"] = matching_doc

    # Build step-wise structure by merging admin defaults + case-specific docs
    step_docs = []
    for cs in case_steps:
        step_name = cs.get("step_name", "")
        case_req_docs = cs.get("required_documents", [])
        step_uploaded = [d for d in uploaded_docs if d.get("step_name") == step_name]

        # Get latest admin default docs for this step
        admin_defaults = admin_docs_by_step.get(step_name, [])

#         # Build a set of doc names already in case_steps (CM-added or previously synced)
#         existing_names = set()
#         for rd in case_req_docs:
#             existing_names.add(_get_doc_name(rd).lower())

#         # Merge: start with case_step docs, then add any NEW admin defaults not yet in case_steps
#         # Merge client-visible case documents only
#         merged_docs = []

#         for rd in case_req_docs:
#             filled_by = rd.get("filled_by")

#             # Hide CM-only intake fields from client
#             if (
#                 current_user["role"] == "client"
#                 and filled_by == "cm"
#             ):
#                 continue

#             merged_docs.append(rd)

#         new_admin_docs = []
#         for ad in admin_defaults:
#             ad_name = _get_doc_name(ad)
#             if ad_name and ad_name.lower() not in existing_names:
#                 merged_docs.append({
#     "doc_name": ad_name,
#     "description": ad.get("description", ""),
#     "is_mandatory": ad.get(
#         "is_mandatory",
#         ad.get("mandatory", True)
#     ),
#     "tag": ad.get("tag", "mandatory"),
#     "notes": ad.get("notes", ""),
#     "source": "intake_form",
#     "added_by_name": "Admin",
#     "filled_by": ad.get("filled_by", "client"),
# })
#                 new_admin_docs.append(ad_name)

        # Sync new admin docs to case_steps in DB (so they persist)
        # if new_admin_docs:
        #     await case_steps_col.update_one(
        #         {"case_id": case_id, "step_name": step_name},
        #         {"$set": {"required_documents": merged_docs}}
        #     )

        # Build doc items for response
                # CLIENT:
        # Show ONLY Workflow Builder intake file fields
        # where filled_by is client or both
        if current_user["role"] == "client":
            merged_docs = list(admin_defaults)

        # CASE MANAGER / ADMIN:
        # Show case required documents + workflow intake documents
        else:
            merged_docs = list(case_req_docs)

            existing_names = {
                _get_doc_name(rd).lower()
                for rd in merged_docs
                if _get_doc_name(rd)
            }

            for ad in admin_defaults:
                ad_name = _get_doc_name(ad)

                if (
                    ad_name
                    and ad_name.lower() not in existing_names
                ):
                    merged_docs.append(ad)
                    existing_names.add(ad_name.lower())
        doc_items = []
        for rd in merged_docs:
            doc_name = _get_doc_name(rd)
            if not doc_name:
                continue
            matching = next(
                (d for d in step_uploaded
                 if d.get("document_type", "").lower() == doc_name.lower()
                 or d.get("filename", "").lower().startswith(doc_name.lower()[:5])),
                None
            )
            doc_items.append({
                "key": rd.get("key", ""),
                "doc_name": doc_name,
                "label": rd.get("label", doc_name),
                "field_type": rd.get("field_type", "file"),
                "options": rd.get("options", []),
                "placeholder": rd.get("placeholder", ""),
                "help_text": rd.get("help_text", ""),
                "filled_by": rd.get(
    "filled_by",
    "cm" if rd.get("source") == "cm_request" else "client"
),
                "is_mandatory": rd.get(
                    "is_mandatory",
                    rd.get("mandatory", False)
                ),
                "required": rd.get(
                    "required",
                    rd.get("mandatory", False)
                ),
                "tag": rd.get("tag", "optional"),
                "notes": rd.get(
                    "notes",
                    rd.get("description", "")
                ),
                "source": rd.get("source", "intake_form"),
                "added_by_name": rd.get("added_by_name", "Admin"),

                "uploaded": matching is not None,
                "uploaded_doc": matching,
                "status": (
                    matching.get("status", "pending")
                    if matching
                    else "not_uploaded"
                ),
            })
        step_docs.append({
            "step_name": step_name,
            "step_order": cs.get("step_order", 0),
            "description": cs.get("description", ""),
            "status": cs.get("status", "pending"),
            "required_count": len(doc_items),
            "uploaded_count": sum(1 for d in doc_items if d["uploaded"]),
            "verified_count": sum(1 for d in doc_items if d["status"] == "approved"),
            "documents": doc_items,
        })

    # Count unmatched uploads
    matched_doc_ids = set()
    for sd in step_docs:
        for d in sd["documents"]:
            if d["uploaded_doc"]:
                matched_doc_ids.add(d["uploaded_doc"]["id"])
    for r in additional_requests:
        if r.get("uploaded_doc"):
            matched_doc_ids.add(r["uploaded_doc"]["id"])

    other_uploads = [d for d in uploaded_docs if d.get("id") not in matched_doc_ids and not d.get("additional_request_id")]

    total_required = sum(s["required_count"] for s in step_docs) + len(additional_requests)
    total_uploaded = sum(s["uploaded_count"] for s in step_docs) + sum(1 for r in additional_requests if r.get("uploaded_doc"))
    overall_pct = round(total_uploaded / total_required * 100) if total_required > 0 else 0

    return {
        "steps": step_docs,
        "additional_requests": additional_requests,
        "other_uploads": other_uploads,
        "summary": {
            "total_required": total_required,
            "total_uploaded": total_uploaded,
            "completion_pct": overall_pct,
        }
    }


# ============ CM: REMOVE DOCUMENT FROM STEP ============

class RemoveDocRequest(BaseModel):
    case_id: str
    step_name: str
    doc_name: str


@router.post("/remove-step-doc")
async def remove_step_document(data: RemoveDocRequest, current_user: dict = Depends(get_current_user)):
    """Remove a document requirement from a step"""
    if current_user["role"] not in ["case_manager", "admin"]:
        raise HTTPException(status_code=403, detail="CM or Admin only")

    step = await case_steps_col.find_one(
        {"case_id": data.case_id, "step_name": data.step_name}, {"_id": 0}
    )
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    docs = step.get("required_documents", [])
    target = next((d for d in docs if _get_doc_name(d).lower() == data.doc_name.lower()), None)

    if not target:
        raise HTTPException(status_code=404, detail="Document not found in step")

    # CM can only remove CM-added docs, Admin can remove any
    if current_user["role"] == "case_manager" and target.get("source") == "admin_default":
        raise HTTPException(status_code=403, detail="Cannot remove admin-defined documents. Request admin approval.")

    updated = [d for d in docs if _get_doc_name(d).lower() != data.doc_name.lower()]
    await case_steps_col.update_one(
        {"case_id": data.case_id, "step_name": data.step_name},
        {"$set": {"required_documents": updated}}
    )

    return {"message": f"Document '{data.doc_name}' removed from step '{data.step_name}'"}



# ============ AI DOCUMENT SUGGESTIONS (Smart Template + Web Search) ============

import os
import httpx
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# --- COMPREHENSIVE IMMIGRATION TEMPLATES ---
# Real government requirements per country/visa type with assessment bodies, fees, and official sources

IMMIGRATION_TEMPLATES = {
    "canada_pr": {
        "label": "Canada Permanent Residency (Express Entry)",
        "keywords": ["canada", "pr", "permanent resid", "express entry", "ircc"],
        "government_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry.html",
        "assessment_bodies": ["WES (World Education Services)", "IQAS", "CES", "ICAS", "PEBC"],
        "language_tests": ["IELTS General", "CELPIP General", "TEF Canada", "TCF Canada"],
        "steps": {
            "Profile Creation": [
                {"doc_name": "Valid Passport", "description": "All pages of current valid passport", "is_mandatory": True, "doc_type": "passport"},
                {"doc_name": "Digital Photograph", "description": "IRCC specification photos (35x45mm)", "is_mandatory": True, "doc_type": "photo"},
                {"doc_name": "National Identity Card", "description": "Government-issued national ID (both sides)", "is_mandatory": False, "doc_type": "id_card"},
            ],
            "Education Credential Assessment": [
                {"doc_name": "ECA Report", "description": "Education Credential Assessment from designated body (WES/IQAS/CES/ICAS)", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Degree Certificate", "description": "Original degree/diploma certificate", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Academic Transcripts", "description": "Official sealed transcripts from university/college", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Course Completion Letter", "description": "Letter confirming course completion from institution", "is_mandatory": False, "doc_type": "certificate"},
            ],
            "Language Testing": [
                {"doc_name": "IELTS/CELPIP Score Report", "description": "Official language test results (IELTS General or CELPIP General)", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "French Language Results", "description": "TEF Canada or TCF Canada results (if claiming French points)", "is_mandatory": False, "doc_type": "certificate"},
            ],
            "Express Entry Profile": [
                {"doc_name": "Work Experience Letters", "description": "Reference letters from employers on company letterhead with duties, hours, salary", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "NOC Code Documentation", "description": "Evidence that work experience matches claimed NOC code", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Proof of Funds", "description": "Bank statements/investment proof showing minimum settlement funds (CAD $13,757 single, $25,564 family of 4)", "is_mandatory": True, "doc_type": "financial"},
            ],
            "ITA & PR Application": [
                {"doc_name": "Police Clearance Certificate", "description": "PCC from each country lived in 6+ months since age 18", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Medical Examination Report", "description": "IME from IRCC panel physician (valid 12 months)", "is_mandatory": True, "doc_type": "medical"},
                {"doc_name": "Biometrics Confirmation", "description": "Biometrics collection receipt from VAC", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Marriage Certificate", "description": "Official marriage certificate (if applicable)", "is_mandatory": False, "doc_type": "legal"},
                {"doc_name": "Birth Certificates", "description": "Birth certificates for dependent children", "is_mandatory": False, "doc_type": "legal"},
                {"doc_name": "Proof of Relationship", "description": "Photos, communications, joint accounts for spouse/partner", "is_mandatory": False, "doc_type": "other"},
            ],
            "Final Review": [
                {"doc_name": "Confirmation of PR (COPR)", "description": "Signed COPR document", "is_mandatory": True, "doc_type": "visa"},
                {"doc_name": "PR Card Photo", "description": "Photos meeting PR card specifications", "is_mandatory": True, "doc_type": "photo"},
            ],
        },
        "fees_info": "Application fee: CAD $1,365 per adult (processing $850 + RPRF $515). Biometrics: CAD $85/person. ECA (WES): CAD $220. IELTS: approx CAD $320."
    },
    "australia_pr": {
        "label": "Australia Permanent Residency (Skilled Migration 189/190/491)",
        "keywords": ["australia", "pr", "permanent resid", "skilled", "189", "190", "491", "dha", "home affairs"],
        "government_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189",
        "assessment_bodies": ["VETASSESS", "ACS (Australian Computer Society)", "Engineers Australia", "TRA (Trades Recognition Australia)", "ANMAC", "CPAA", "CAANZ"],
        "language_tests": ["IELTS Academic", "PTE Academic", "TOEFL iBT", "OET", "Cambridge C1 Advanced"],
        "steps": {
            "Skills Assessment": [
                {"doc_name": "Skills Assessment Outcome Letter", "description": "Positive skills assessment from relevant assessing authority (ACS/VETASSESS/EA)", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Qualification Certificates", "description": "All degree/diploma certificates relevant to nominated occupation", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Academic Transcripts", "description": "Official transcripts for all qualifications", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Employment Reference Letters", "description": "Detailed reference letters on company letterhead with duties, dates, hours, salary", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Payslips/Tax Returns", "description": "Payslips, tax returns, or bank statements as evidence of employment", "is_mandatory": True, "doc_type": "financial"},
                {"doc_name": "CV/Resume", "description": "Detailed resume matching employment claims", "is_mandatory": True, "doc_type": "other"},
            ],
            "Language Testing": [
                {"doc_name": "English Test Score Report", "description": "PTE Academic/IELTS/TOEFL/OET score report (valid 3 years)", "is_mandatory": True, "doc_type": "certificate"},
            ],
            "EOI Submission": [
                {"doc_name": "Passport", "description": "Valid passport (all bio pages + any travel stamps)", "is_mandatory": True, "doc_type": "passport"},
                {"doc_name": "Points Calculation Evidence", "description": "Evidence for each points claim (age, English, qualifications, experience)", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "State Nomination Letter", "description": "State/territory nomination approval (for Subclass 190/491)", "is_mandatory": False, "doc_type": "legal"},
            ],
            "Visa Application": [
                {"doc_name": "Police Clearance Certificate", "description": "National PCC from each country lived 12+ months since age 16", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Health Examination Report", "description": "Medical examination by Bupa Medical Visa Services panel doctor", "is_mandatory": True, "doc_type": "medical"},
                {"doc_name": "Chest X-Ray Report", "description": "Chest X-ray if required based on country of origin", "is_mandatory": False, "doc_type": "medical"},
                {"doc_name": "Health Insurance (OVHC)", "description": "Overseas Visitor Health Cover evidence", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Birth Certificate", "description": "Full birth certificate for applicant and dependents", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Marriage Certificate", "description": "Official marriage certificate (if applicable)", "is_mandatory": False, "doc_type": "legal"},
                {"doc_name": "Relationship Evidence", "description": "Statutory declarations, photos, financial evidence for partner", "is_mandatory": False, "doc_type": "other"},
                {"doc_name": "Form 80 - Personal Particulars", "description": "Completed Form 80 with full travel and address history", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Form 1221 - Additional Info", "description": "Completed Form 1221 additional personal particulars", "is_mandatory": False, "doc_type": "other"},
            ],
            "Decision & Grant": [
                {"doc_name": "Visa Grant Letter", "description": "Official visa grant notification from DHA", "is_mandatory": True, "doc_type": "visa"},
                {"doc_name": "Travel Document", "description": "Valid passport for initial entry before first entry deadline", "is_mandatory": True, "doc_type": "passport"},
            ],
        },
        "fees_info": "Visa application (Subclass 189): AUD $4,640 primary applicant. Skills assessment: AUD $500-$1,200 depending on body. PTE Academic: AUD $410. Health exam: AUD $350-$500. Police clearance varies by country."
    },
    "uk_skilled_worker": {
        "label": "UK Skilled Worker Visa",
        "keywords": ["uk", "united kingdom", "britain", "skilled worker", "work visa", "tier 2"],
        "government_url": "https://www.gov.uk/skilled-worker-visa",
        "steps": {
            "Certificate of Sponsorship": [
                {"doc_name": "Certificate of Sponsorship (CoS)", "description": "Valid CoS reference number from licensed UK employer", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Job Description", "description": "Detailed job description matching SOC code requirements", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Salary Confirmation", "description": "Evidence of salary meeting minimum threshold for occupation", "is_mandatory": True, "doc_type": "financial"},
            ],
            "English Language": [
                {"doc_name": "IELTS for UKVI Score", "description": "IELTS for UKVI or approved SELT provider results", "is_mandatory": True, "doc_type": "certificate"},
            ],
            "Visa Application": [
                {"doc_name": "Valid Passport", "description": "Current passport with at least 1 blank page", "is_mandatory": True, "doc_type": "passport"},
                {"doc_name": "TB Test Certificate", "description": "TB test results from approved clinic (if from listed country)", "is_mandatory": False, "doc_type": "medical"},
                {"doc_name": "Criminal Record Certificate", "description": "Police certificate from countries lived 12+ months", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Bank Statements", "description": "Evidence of £1,270 maintenance funds held for 28 consecutive days", "is_mandatory": True, "doc_type": "financial"},
                {"doc_name": "Qualification Certificates", "description": "Degree/diploma certificates relevant to job", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "ATAS Certificate", "description": "Academic Technology Approval Scheme certificate (if applicable)", "is_mandatory": False, "doc_type": "certificate"},
            ],
        },
        "fees_info": "Visa fee: GBP £719 (up to 3 years) or £1,420 (more than 3 years). IHS surcharge: GBP £1,035/year. Priority: GBP £500. Super priority: GBP £1,000."
    },
    "student_visa_generic": {
        "label": "Student Visa (Generic)",
        "keywords": ["student", "study", "university", "college", "education visa"],
        "steps": {
            "Admission": [
                {"doc_name": "University Offer Letter", "description": "Unconditional offer letter from recognized institution", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Academic Transcripts", "description": "Official transcripts from previous education", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Statement of Purpose (SOP)", "description": "Personal statement explaining study plans and career goals", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Letters of Recommendation", "description": "Academic/professional recommendation letters", "is_mandatory": False, "doc_type": "other"},
            ],
            "Financial Documentation": [
                {"doc_name": "Bank Statements", "description": "6-12 months bank statements showing sufficient funds", "is_mandatory": True, "doc_type": "financial"},
                {"doc_name": "Scholarship Letter", "description": "Scholarship award letter if applicable", "is_mandatory": False, "doc_type": "financial"},
                {"doc_name": "Financial Sponsor Letter", "description": "Sponsorship letter with sponsor's financial proof", "is_mandatory": False, "doc_type": "financial"},
                {"doc_name": "Education Loan Approval", "description": "Loan sanction letter from bank if applicable", "is_mandatory": False, "doc_type": "financial"},
            ],
            "Visa Filing": [
                {"doc_name": "Valid Passport", "description": "Passport valid for duration of study plus 6 months", "is_mandatory": True, "doc_type": "passport"},
                {"doc_name": "Visa Application Form", "description": "Completed visa application form", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Passport Photos", "description": "Photos meeting destination country specifications", "is_mandatory": True, "doc_type": "photo"},
                {"doc_name": "Medical Certificate", "description": "Medical fitness certificate from approved doctor", "is_mandatory": True, "doc_type": "medical"},
                {"doc_name": "Police Clearance", "description": "Police clearance certificate from home country", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "English Proficiency", "description": "IELTS/TOEFL/PTE score report", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Health Insurance", "description": "Health insurance coverage for study period", "is_mandatory": True, "doc_type": "other"},
            ],
        },
        "fees_info": "Varies by country. Typical: Application fee $100-$500, health exam $200-$500, biometrics $80-$100."
    },
    "nz_skilled_migrant": {
        "label": "New Zealand Skilled Migrant Category Resident Visa",
        "keywords": ["new zealand", "nz", "skilled migrant", "permanent resid", "smcr"],
        "government_url": "https://www.immigration.govt.nz/new-zealand-visas/visas/visa/skilled-migrant-category-resident-visa",
        "assessment_bodies": ["NZQA (NZ Qualifications Authority)", "Registration bodies for regulated professions"],
        "language_tests": ["IELTS General/Academic", "TOEFL iBT", "PTE Academic", "OET", "Cambridge English"],
        "steps": {
            "Eligibility & Preparation": [
                {"doc_name": "Valid Passport", "description": "Current valid passport with 6+ months validity", "is_mandatory": True, "doc_type": "passport"},
                {"doc_name": "NZQA Qualification Assessment", "description": "NZ Qualifications Authority assessment of overseas qualifications", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "English Language Test Results", "description": "IELTS 6.5+ overall or equivalent (PTE 58+)", "is_mandatory": True, "doc_type": "certificate"},
            ],
            "Skills Assessment": [
                {"doc_name": "Qualification Certificates", "description": "All degree/diploma certificates", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Employment References", "description": "Reference letters with detailed duties, dates, hours from employers", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Professional Registration", "description": "NZ registration for regulated occupations (if applicable)", "is_mandatory": False, "doc_type": "certificate"},
            ],
            "EOI Submission": [
                {"doc_name": "Points Calculation Evidence", "description": "Evidence for all claimed points (age, qualification, experience, job offer)", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Job Offer/Employment Agreement", "description": "Offer from accredited NZ employer (if claiming points)", "is_mandatory": False, "doc_type": "legal"},
            ],
            "ITA & Residence Application": [
                {"doc_name": "Police Certificates", "description": "Police clearance from every country lived 5+ years since age 17", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Medical Certificate (INZ 1007)", "description": "Medical examination by Immigration NZ panel physician", "is_mandatory": True, "doc_type": "medical"},
                {"doc_name": "Chest X-Ray (INZ 1096)", "description": "Chest X-ray certificate", "is_mandatory": True, "doc_type": "medical"},
                {"doc_name": "Birth Certificate", "description": "Full birth certificate for applicant and dependents", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Marriage/Partnership Certificate", "description": "Evidence of relationship (if applicable)", "is_mandatory": False, "doc_type": "legal"},
                {"doc_name": "Settlement Funds Evidence", "description": "Proof of NZD $4,000+ settlement funds", "is_mandatory": True, "doc_type": "financial"},
            ],
        },
        "fees_info": "EOI fee: NZD $680. Residence application: NZD $3,310 principal applicant. Medical exam: NZD $400-$600. IELTS: NZD $385."
    },
    "usa_h1b": {
        "label": "USA H-1B Specialty Occupation Visa",
        "keywords": ["usa", "us", "america", "h1b", "h-1b", "work visa", "specialty"],
        "government_url": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
        "assessment_bodies": ["USCIS", "Department of Labor (DOL)", "SEVP"],
        "language_tests": [],
        "steps": {
            "Employer Petition & LCA": [
                {"doc_name": "Labor Condition Application (LCA)", "description": "Certified LCA from DOL (Form ETA-9035/9035E)", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Job Offer Letter", "description": "Detailed offer letter with job title, duties, salary, work location", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Form I-129 Petition", "description": "Petition for Nonimmigrant Worker filed by employer", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Company Support Letter", "description": "Employer support letter explaining specialty occupation need", "is_mandatory": True, "doc_type": "legal"},
            ],
            "Beneficiary Documentation": [
                {"doc_name": "Valid Passport", "description": "Current passport valid for travel", "is_mandatory": True, "doc_type": "passport"},
                {"doc_name": "Bachelor's Degree or Higher", "description": "US bachelor's degree or foreign equivalent in specialty field", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Academic Transcripts", "description": "Official transcripts from all universities attended", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Credential Evaluation", "description": "Foreign degree evaluation by NACES/AICE member (if foreign degree)", "is_mandatory": False, "doc_type": "certificate"},
                {"doc_name": "Resume/CV", "description": "Detailed resume showing relevant work experience", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Previous H-1B Approvals", "description": "Prior I-797 approval notices (if transfer/extension)", "is_mandatory": False, "doc_type": "visa"},
            ],
            "Visa Stamping (Consular Processing)": [
                {"doc_name": "DS-160 Confirmation Page", "description": "Online Nonimmigrant Visa Application confirmation", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "I-797 Approval Notice", "description": "USCIS approval notice for H-1B petition", "is_mandatory": True, "doc_type": "visa"},
                {"doc_name": "Passport Photos", "description": "2x2 inch photos per US visa specifications", "is_mandatory": True, "doc_type": "photo"},
                {"doc_name": "Interview Appointment Letter", "description": "US Embassy/Consulate interview confirmation", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Pay Stubs/Tax Returns", "description": "Recent pay stubs or W-2 forms (if extension/transfer)", "is_mandatory": False, "doc_type": "financial"},
            ],
        },
        "fees_info": "H-1B filing fee: USD $460. ACWIA fee: $750/$1,500 (based on company size). Fraud prevention: $500. Lottery registration: $215. Premium processing (optional): $2,805. Visa stamping MRV fee: $205."
    },
    "uae_golden_visa": {
        "label": "UAE Golden Visa (10-Year Long-Term Residence)",
        "keywords": ["uae", "dubai", "golden visa", "emirates", "abu dhabi", "10 year"],
        "government_url": "https://u.ae/en/information-and-services/visa-and-emirates-id/residence-visas/golden-visa",
        "assessment_bodies": ["ICP (Federal Authority for Identity, Citizenship, Customs and Port Security)", "GDRFA"],
        "steps": {
            "Eligibility & Category Selection": [
                {"doc_name": "Valid Passport", "description": "Passport with minimum 6 months validity", "is_mandatory": True, "doc_type": "passport"},
                {"doc_name": "Passport-size Photographs", "description": "Recent photos with white background", "is_mandatory": True, "doc_type": "photo"},
                {"doc_name": "Category Evidence", "description": "Proof for selected category: property deed (AED 2M+), business license, investor certificates, or talent recognition", "is_mandatory": True, "doc_type": "other"},
            ],
            "Document Preparation": [
                {"doc_name": "Emirates ID Application", "description": "Emirates ID application or existing EID copy", "is_mandatory": True, "doc_type": "id_card"},
                {"doc_name": "Medical Fitness Certificate", "description": "Medical fitness test from DHA-approved center", "is_mandatory": True, "doc_type": "medical"},
                {"doc_name": "Health Insurance Policy", "description": "UAE health insurance coverage", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Qualification Certificates (Attested)", "description": "UAE-attested educational certificates", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Salary Certificate/Income Proof", "description": "Monthly income proof (AED 30,000+ for specialized talent)", "is_mandatory": False, "doc_type": "financial"},
                {"doc_name": "Property Title Deed", "description": "DLD title deed for property worth AED 2M+ (investor route)", "is_mandatory": False, "doc_type": "legal"},
            ],
            "Application & Visa Issuance": [
                {"doc_name": "Golden Visa Application Form", "description": "Completed online application via ICP smart services", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Sponsor Approval/NOC", "description": "No Objection Certificate from current sponsor (if changing)", "is_mandatory": False, "doc_type": "legal"},
                {"doc_name": "Entry Permit/Change Status", "description": "Entry permit or status change approval", "is_mandatory": True, "doc_type": "visa"},
            ],
        },
        "fees_info": "Golden Visa application: AED 2,800. Emirates ID: AED 370 (10 years). Medical fitness: AED 320. Health insurance: varies. Entry permit: AED 1,150. Visa stamping: AED 650."
    },
    "singapore_ep": {
        "label": "Singapore Employment Pass (EP)",
        "keywords": ["singapore", "ep", "employment pass", "mom", "work"],
        "government_url": "https://www.mom.gov.sg/passes-and-permits/employment-pass",
        "assessment_bodies": ["Ministry of Manpower (MOM)", "COMPASS Framework"],
        "steps": {
            "COMPASS Assessment": [
                {"doc_name": "Educational Certificates", "description": "Degree certificates from recognized universities", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Academic Transcripts", "description": "Official transcripts showing subjects and grades", "is_mandatory": True, "doc_type": "certificate"},
                {"doc_name": "Resume/CV", "description": "Detailed CV showing career history and skills", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "COMPASS Self-Assessment", "description": "COMPASS framework self-assessment score calculation", "is_mandatory": True, "doc_type": "other"},
            ],
            "EP Application": [
                {"doc_name": "Valid Passport", "description": "Passport with minimum 6 months validity", "is_mandatory": True, "doc_type": "passport"},
                {"doc_name": "Passport-size Photo", "description": "Recent photo meeting MOM specifications", "is_mandatory": True, "doc_type": "photo"},
                {"doc_name": "Employment Contract", "description": "Signed employment contract with Singapore company", "is_mandatory": True, "doc_type": "legal"},
                {"doc_name": "Company ACRA Profile", "description": "Employer's ACRA business profile", "is_mandatory": True, "doc_type": "other"},
                {"doc_name": "Salary Details", "description": "Fixed monthly salary meeting minimum threshold (SGD $5,600+)", "is_mandatory": True, "doc_type": "financial"},
                {"doc_name": "Professional Certifications", "description": "Relevant professional licenses or certifications", "is_mandatory": False, "doc_type": "certificate"},
            ],
            "Pass Issuance": [
                {"doc_name": "In-Principle Approval (IPA) Letter", "description": "MOM IPA letter for entry into Singapore", "is_mandatory": True, "doc_type": "visa"},
                {"doc_name": "Medical Examination Report", "description": "Medical checkup at registered Singapore clinic (if required)", "is_mandatory": False, "doc_type": "medical"},
                {"doc_name": "EP Card Collection", "description": "Visit MOM for photo and fingerprint for EP card", "is_mandatory": True, "doc_type": "other"},
            ],
        },
        "fees_info": "EP application: SGD $105. EP issuance: SGD $225. Multiple journey visa: SGD $30. COMPASS does not have a separate fee."
    },
}


def _find_best_template(product_name: str) -> dict:
    """Find the best matching template for a product name using keyword matching."""
    product_lower = product_name.lower()
    best_match = None
    best_score = 0
    for key, tmpl in IMMIGRATION_TEMPLATES.items():
        score = sum(1 for kw in tmpl["keywords"] if kw in product_lower)
        if score > best_score:
            best_score = score
            best_match = tmpl
    return best_match


def _find_step_docs_from_template(template: dict, step_name: str) -> list:
    """Find matching step documents from template using fuzzy matching."""
    if not template:
        return []
    step_lower = step_name.lower()
    for tmpl_step_name, docs in template.get("steps", {}).items():
        # Check if step names are similar
        tmpl_lower = tmpl_step_name.lower()
        if (tmpl_lower in step_lower or step_lower in tmpl_lower or
            any(w in step_lower for w in tmpl_lower.split() if len(w) > 3)):
            return docs
    return []


async def _web_search_context(product_name: str, step_name: str) -> str:
    """Fetch current immigration info via web search for AI context enrichment."""
    search_query = f"{product_name} {step_name} required documents official government"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://www.google.com/search",
                params={"q": search_query, "num": 3},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                follow_redirects=True
            )
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                snippets = []
                for g in soup.select(".BNeawe, .VwiC3b, .IsZvec"):
                    text = g.get_text(strip=True)
                    if len(text) > 30:
                        snippets.append(text)
                if snippets:
                    return "Current web search results:\n" + "\n".join(snippets[:5])
    except Exception:
        pass
    return ""


async def _call_ai(prompt: str, system_msg: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    from core.ai_models import model_for
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"doc-suggest-{uuid.uuid4().hex[:8]}",
            system_message=system_msg
        ).with_model("anthropic", model_for("step_document_helper"))  # Phase 9.7 — Haiku 4.5
        return await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


class AISuggestRequest(BaseModel):
    product_name: str
    step_name: str
    step_description: str = ""
    existing_docs: List[str] = []


class AIBulkSuggestRequest(BaseModel):
    product_name: str
    product_description: str = ""
    steps: List[dict] = []  # [{"step_name": "...", "description": "..."}]


@router.post("/ai-suggest-step-docs")
async def ai_suggest_step_documents(data: AISuggestRequest, current_user: dict = Depends(get_current_user)):
    """AI suggests documents for a specific workflow step using templates + web search + GPT."""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or CM only")

    # 1. Check templates first
    template = _find_best_template(data.product_name)
    template_docs = _find_step_docs_from_template(template, data.step_name) if template else []

    # If we have strong template match, return template docs directly (filtered)
    if template_docs:
        existing_lower = {d.lower() for d in data.existing_docs}
        filtered = [d for d in template_docs if d["doc_name"].lower() not in existing_lower]
        if filtered:
            await audit_logs_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": current_user["id"],
                "action": "ai_doc_suggestion_template", "entity_type": "workflow_step",
                "entity_id": f"{data.product_name}/{data.step_name}",
                "new_value": {"source": "template", "count": len(filtered), "template": template.get("label", "")},
                "created_at": datetime.now(timezone.utc)
            })
            return {
                "suggestions": filtered,
                "source": "template",
                "template_name": template.get("label", ""),
                "fees_info": template.get("fees_info", ""),
                "government_url": template.get("government_url", ""),
            }

    # 2. No template match - use web search + AI
    web_context = await _web_search_context(data.product_name, data.step_name)

    existing_str = ""
    if data.existing_docs:
        existing_str = "\nAlready added documents (do NOT repeat these): " + ", ".join(data.existing_docs)

    template_context = ""
    if template:
        template_context = (
            f"\nReference info: {template.get('label', '')}. "
            f"Assessment bodies: {', '.join(template.get('assessment_bodies', []))}. "
            f"Language tests: {', '.join(template.get('language_tests', []))}. "
            f"Fees: {template.get('fees_info', 'N/A')}. "
            f"Official source: {template.get('government_url', '')}."
        )

    example = '[{"doc_name":"Passport Copy","description":"Clear copy of all passport pages","is_mandatory":true,"doc_type":"passport"}]'

    prompt = (
        f'For the immigration product "{data.product_name}", suggest ACCURATE required documents for step "{data.step_name}".\n'
        f'{("Step description: " + data.step_description) if data.step_description else ""}\n'
        f'{template_context}\n{web_context}\n{existing_str}\n\n'
        'IMPORTANT: Only suggest documents that are ACTUALLY required by the relevant government authority. '
        'Do NOT suggest generic/random documents. Base suggestions on real immigration requirements.\n\n'
        'Return a JSON array of document objects with:\n'
        '- "doc_name": exact professional document name as used by the government\n'
        '- "description": specific description including issuing authority where applicable\n'
        '- "is_mandatory": true if legally required, false if supporting\n'
        '- "doc_type": one of passport, visa, certificate, id_card, photo, financial, medical, legal, other\n\n'
        f'Suggest 3-6 documents. Return ONLY the JSON array.\nExample: {example}'
    )

    system_msg = (
        "You are an immigration documentation expert with up-to-date knowledge of global visa requirements. "
        "Only suggest documents that are genuinely required by government authorities. "
        "Include specific details like issuing bodies, validity periods, and official form numbers where applicable. "
        "Return ONLY valid JSON arrays."
    )

    result = await _call_ai(prompt, system_msg)

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            cleaned = cleaned.rsplit("```", 1)[0]
        suggestions = json.loads(cleaned)
        if not isinstance(suggestions, list):
            suggestions = []
    except (json.JSONDecodeError, Exception):
        suggestions = []

    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "ai_doc_suggestion_ai", "entity_type": "workflow_step",
        "entity_id": f"{data.product_name}/{data.step_name}",
        "new_value": {"source": "ai+web", "count": len(suggestions)},
        "created_at": datetime.now(timezone.utc)
    })

    return {
        "suggestions": suggestions,
        "source": "ai",
        "fees_info": template.get("fees_info", "") if template else "",
        "government_url": template.get("government_url", "") if template else "",
    }


@router.post("/ai-suggest-bulk")
async def ai_suggest_bulk_documents(data: AIBulkSuggestRequest, current_user: dict = Depends(get_current_user)):
    """AI suggests documents for ALL steps of a product at once using templates + AI."""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or CM only")

    template = _find_best_template(data.product_name)
    suggestions = {}
    source = "ai"

    # Try template-first approach
    if template:
        for step in data.steps:
            step_name = step.get("step_name", "")
            tmpl_docs = _find_step_docs_from_template(template, step_name)
            if tmpl_docs:
                suggestions[step_name] = tmpl_docs
                source = "template"

    # If template covered all steps, return immediately
    if len(suggestions) == len(data.steps) and all(suggestions.values()):
        await audit_logs_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": current_user["id"],
            "action": "ai_bulk_doc_suggestion_template", "entity_type": "product",
            "entity_id": data.product_name,
            "new_value": {"source": "template", "steps": len(data.steps), "template": template.get("label", "")},
            "created_at": datetime.now(timezone.utc)
        })
        return {
            "suggestions": suggestions,
            "source": "template",
            "template_name": template.get("label", ""),
            "fees_info": template.get("fees_info", ""),
            "government_url": template.get("government_url", ""),
        }

    # Steps not covered by template - use AI for those
    uncovered_steps = [s for s in data.steps if s.get("step_name", "") not in suggestions]
    if uncovered_steps:
        steps_str = ""
        for i, step in enumerate(uncovered_steps, 1):
            steps_str += f"\n{i}. {step.get('step_name', 'Step ' + str(i))}"
            if step.get("description"):
                steps_str += f" - {step['description']}"

        template_context = ""
        if template:
            template_context = (
                f"\nReference: {template.get('label', '')}. "
                f"Assessment bodies: {', '.join(template.get('assessment_bodies', []))}. "
                f"Fees: {template.get('fees_info', 'N/A')}."
            )

        desc_part = f" ({data.product_description})" if data.product_description else ""
        example_bulk = '{"Step Name": [{"doc_name":"Passport","description":"Valid passport","is_mandatory":true,"doc_type":"passport"}]}'

        prompt = (
            f'For "{data.product_name}"{desc_part}, suggest ACCURATE required documents for these steps:\n'
            f'{steps_str}\n{template_context}\n\n'
            'IMPORTANT: Only suggest documents ACTUALLY required by the government authority. No generic documents.\n\n'
            'Return a JSON object where keys are EXACT step names. Each doc must have:\n'
            '- "doc_name": official document name\n- "description": specific description with issuing authority\n'
            '- "is_mandatory": true/false\n- "doc_type": passport/visa/certificate/id_card/photo/financial/medical/legal/other\n\n'
            f'Return ONLY JSON.\nExample: {example_bulk}'
        )

        system_msg = (
            "You are an immigration documentation expert. Only suggest documents genuinely required by government authorities. "
            "Include specific details like form numbers, issuing bodies, and validity periods. Return ONLY valid JSON."
        )

        result = await _call_ai(prompt, system_msg)
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                cleaned = cleaned.rsplit("```", 1)[0]
            ai_suggestions = json.loads(cleaned)
            if isinstance(ai_suggestions, dict):
                # Match step names flexibly
                for step in uncovered_steps:
                    sn = step.get("step_name", "")
                    matched = ai_suggestions.get(sn) or next(
                        (v for k, v in ai_suggestions.items() if k.startswith(sn) or sn.startswith(k)), []
                    )
                    if matched:
                        suggestions[sn] = matched
                source = "template+ai" if any(s.get("step_name", "") in suggestions for s in data.steps) else "ai"
        except (json.JSONDecodeError, Exception):
            pass

    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "ai_bulk_doc_suggestion", "entity_type": "product",
        "entity_id": data.product_name,
        "new_value": {"source": source, "steps": {k: len(v) for k, v in suggestions.items()}},
        "created_at": datetime.now(timezone.utc)
    })

    return {
        "suggestions": suggestions,
        "source": source,
        "fees_info": template.get("fees_info", "") if template else "",
        "government_url": template.get("government_url", "") if template else "",
    }


@router.get("/templates")
async def get_available_templates(current_user: dict = Depends(get_current_user)):
    """Get list of available immigration document templates."""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or CM only")
    templates = []
    for key, tmpl in IMMIGRATION_TEMPLATES.items():
        step_names = list(tmpl.get("steps", {}).keys())
        total_docs = sum(len(docs) for docs in tmpl.get("steps", {}).values())
        templates.append({
            "id": key,
            "label": tmpl["label"],
            "steps": step_names,
            "total_documents": total_docs,
            "government_url": tmpl.get("government_url", ""),
            "fees_info": tmpl.get("fees_info", ""),
            "assessment_bodies": tmpl.get("assessment_bodies", []),
        })
    return {"templates": templates}


# ============ OFFICIAL GOVERNMENT FORMS DATABASE ============

GOVERNMENT_FORMS = {
    "australia": {
        "country": "Australia",
        "authority": "Department of Home Affairs",
        "base_url": "https://immi.homeaffairs.gov.au",
        "forms": [
            {"form_id": "form_80", "name": "Form 80 - Personal Particulars for Assessment", "description": "Detailed personal history including travel, employment, education, and military service", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/80.pdf", "applies_to": ["189", "190", "491", "482", "500"], "category": "application", "mandatory": True},
            {"form_id": "form_1221", "name": "Form 1221 - Additional Personal Particulars", "description": "Supplementary personal details form required for some visa applications", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1221.pdf", "applies_to": ["189", "190", "491"], "category": "application", "mandatory": False},
            {"form_id": "form_1393", "name": "Form 1393 - Application for Migration to Australia by a Skilled Worker", "description": "Main application form for skilled migration visa subclasses", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1393.pdf", "applies_to": ["189", "190", "491"], "category": "application", "mandatory": True},
            {"form_id": "form_1276", "name": "Form 1276 - Application for a Student Visa", "description": "Application form for Student Visa Subclass 500", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1276.pdf", "applies_to": ["500"], "category": "application", "mandatory": True},
            {"form_id": "form_1419", "name": "Form 1419 - Application for a Visitor Visa", "description": "Application form for Visitor Visa Subclass 600", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1419.pdf", "applies_to": ["600"], "category": "application", "mandatory": True},
            {"form_id": "form_26", "name": "Form 26 - Medical Examination for Visa Applicant", "description": "Health examination form to be completed by a Bupa Medical Visa Services panel doctor", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/26.pdf", "applies_to": ["189", "190", "491", "482", "500", "600", "820"], "category": "medical", "mandatory": True},
            {"form_id": "form_160", "name": "Form 160 - Chest X-Ray Referral", "description": "Chest X-ray referral form for health assessment", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/160.pdf", "applies_to": ["189", "190", "491", "500"], "category": "medical", "mandatory": False},
            {"form_id": "form_956", "name": "Form 956 - Appointment of a Migration Agent", "description": "Authorise a registered migration agent to act on your behalf", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/956.pdf", "applies_to": ["189", "190", "491", "482", "500", "600", "820"], "category": "agent", "mandatory": False},
            {"form_id": "form_1023", "name": "Form 1023 - Notification of Changes in Circumstances", "description": "Notify DHA of changes to your application details", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1023.pdf", "applies_to": ["189", "190", "491", "482", "500"], "category": "update", "mandatory": False},
            {"form_id": "form_40sp", "name": "Form 40SP - Sponsorship for Partner Visa", "description": "Sponsorship application form for partner visa", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/40sp.pdf", "applies_to": ["820", "801"], "category": "application", "mandatory": True},
            {"form_id": "form_47sp", "name": "Form 47SP - Application for Partner Visa", "description": "Main application form for Partner visa", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/47sp.pdf", "applies_to": ["820", "801"], "category": "application", "mandatory": True},
            {"form_id": "form_1424", "name": "Form 1424 - Application for Employer Nomination", "description": "Employer nomination form for TSS visa", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1424.pdf", "applies_to": ["482"], "category": "employer", "mandatory": True},
        ]
    },
    "canada": {
        "country": "Canada",
        "authority": "Immigration, Refugees and Citizenship Canada (IRCC)",
        "base_url": "https://www.canada.ca/en/immigration-refugees-citizenship",
        "forms": [
            {"form_id": "imm_0008", "name": "IMM 0008 - Generic Application Form for Canada", "description": "Main application form for permanent residence applications", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm0008enu_2d.pdf", "applies_to": ["express_entry", "pr", "family"], "category": "application", "mandatory": True},
            {"form_id": "imm_5645", "name": "IMM 5645 - Family Information", "description": "Detailed family member information for all immigration applications", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5645e.pdf", "applies_to": ["express_entry", "pr", "family", "student", "work"], "category": "application", "mandatory": True},
            {"form_id": "imm_5669", "name": "IMM 5669 - Schedule A - Background/Declaration", "description": "Personal history including addresses, education, employment, and military service", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5669e.pdf", "applies_to": ["express_entry", "pr"], "category": "application", "mandatory": True},
            {"form_id": "imm_5562", "name": "IMM 5562 - Supplementary Information Form", "description": "Additional personal information and travel history", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5562e.pdf", "applies_to": ["express_entry", "pr"], "category": "application", "mandatory": True},
            {"form_id": "imm_5406", "name": "IMM 5406 - Additional Family Information", "description": "Additional details about family members for PR applications", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5406e.pdf", "applies_to": ["express_entry", "pr", "family"], "category": "application", "mandatory": True},
            {"form_id": "imm_5707", "name": "IMM 5707 - Use of a Representative", "description": "Authorise a representative (lawyer, consultant, or other) to act on your behalf", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5707e.pdf", "applies_to": ["express_entry", "pr", "student", "work", "visitor"], "category": "agent", "mandatory": False},
            {"form_id": "imm_1294", "name": "IMM 1294 - Application for Study Permit", "description": "Main application form for study permits", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm1294e.pdf", "applies_to": ["student"], "category": "application", "mandatory": True},
            {"form_id": "imm_1295", "name": "IMM 1295 - Application for Work Permit", "description": "Main application form for work permits (LMIA-based and open)", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm1295e.pdf", "applies_to": ["work"], "category": "application", "mandatory": True},
            {"form_id": "imm_5257", "name": "IMM 5257 - Application for Temporary Resident Visa", "description": "Visitor visa application form", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5257e.pdf", "applies_to": ["visitor"], "category": "application", "mandatory": True},
            {"form_id": "imm_5476", "name": "IMM 5476 - Authority to Release Personal Information", "description": "Consent form for IRCC to release your info to a designated person", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5476e.pdf", "applies_to": ["express_entry", "pr", "student", "work", "visitor"], "category": "consent", "mandatory": False},
        ]
    },
    "uk": {
        "country": "United Kingdom",
        "authority": "UK Visas and Immigration (UKVI)",
        "base_url": "https://www.gov.uk/government/organisations/uk-visas-and-immigration",
        "forms": [
            {"form_id": "vaf1a", "name": "VAF1A - Skilled Worker Application", "description": "Main application form for Skilled Worker visa (online via gov.uk)", "url": "https://www.gov.uk/skilled-worker-visa/apply", "applies_to": ["skilled_worker", "work"], "category": "application", "mandatory": True},
            {"form_id": "appendix_2", "name": "Appendix 2 - Household Income", "description": "Financial requirement evidence form for family route applications", "url": "https://www.gov.uk/government/publications/form-appendix-2-household-income", "applies_to": ["family", "spouse"], "category": "financial", "mandatory": True},
            {"form_id": "cas_form", "name": "CAS - Confirmation of Acceptance for Studies", "description": "Electronic document issued by licensed sponsor (university/college)", "url": "https://www.gov.uk/student-visa/your-course", "applies_to": ["student"], "category": "application", "mandatory": True},
            {"form_id": "tb_test", "name": "TB Test Certificate", "description": "Tuberculosis test from approved clinic (required for certain nationalities)", "url": "https://www.gov.uk/tb-test-visa/countries-where-you-need-a-tb-test", "applies_to": ["skilled_worker", "student", "family", "work"], "category": "medical", "mandatory": False},
            {"form_id": "atas", "name": "ATAS Certificate", "description": "Academic Technology Approval Scheme certificate for sensitive research subjects", "url": "https://www.gov.uk/guidance/academic-technology-approval-scheme", "applies_to": ["student"], "category": "academic", "mandatory": False},
        ]
    },
    "usa": {
        "country": "United States",
        "authority": "U.S. Citizenship and Immigration Services (USCIS)",
        "base_url": "https://www.uscis.gov",
        "forms": [
            {"form_id": "ds_160", "name": "DS-160 - Online Nonimmigrant Visa Application", "description": "Electronic visa application form for all nonimmigrant visa categories", "url": "https://ceac.state.gov/genniv/", "applies_to": ["h1b", "visitor", "student", "work", "b1b2", "f1", "j1"], "category": "application", "mandatory": True},
            {"form_id": "i_129", "name": "Form I-129 - Petition for Nonimmigrant Worker", "description": "Employer petition form for H-1B and other work visa categories", "url": "https://www.uscis.gov/i-129", "applies_to": ["h1b", "work", "l1"], "category": "employer", "mandatory": True},
            {"form_id": "i_20", "name": "Form I-20 - Certificate of Eligibility", "description": "Issued by SEVP-certified school for F-1 student visa applicants", "url": "https://studyinthestates.dhs.gov/students/prepare/students-and-the-form-i-20", "applies_to": ["f1", "student"], "category": "academic", "mandatory": True},
            {"form_id": "i_140", "name": "Form I-140 - Immigrant Petition for Alien Workers", "description": "Employer-filed petition for employment-based green card (EB-1/EB-2/EB-3)", "url": "https://www.uscis.gov/i-140", "applies_to": ["eb1", "eb2", "eb3", "green_card", "immigrant"], "category": "application", "mandatory": True},
            {"form_id": "i_485", "name": "Form I-485 - Application to Register Permanent Residence", "description": "Adjustment of status application for green card (filed within the US)", "url": "https://www.uscis.gov/i-485", "applies_to": ["green_card", "immigrant", "eb1", "eb2", "eb3"], "category": "application", "mandatory": True},
            {"form_id": "i_130", "name": "Form I-130 - Petition for Alien Relative", "description": "Family-based immigration petition filed by US citizen or permanent resident", "url": "https://www.uscis.gov/i-130", "applies_to": ["family", "spouse", "parent"], "category": "application", "mandatory": True},
            {"form_id": "i_864", "name": "Form I-864 - Affidavit of Support", "description": "Financial sponsorship form showing ability to support immigrant at 125% of poverty line", "url": "https://www.uscis.gov/i-864", "applies_to": ["family", "spouse", "green_card"], "category": "financial", "mandatory": True},
            {"form_id": "eta_9035", "name": "Form ETA-9035 - Labor Condition Application (LCA)", "description": "Department of Labor form certifying wage and working conditions for H-1B", "url": "https://flag.dol.gov/", "applies_to": ["h1b"], "category": "employer", "mandatory": True},
            {"form_id": "i_765", "name": "Form I-765 - Application for Employment Authorization", "description": "EAD (work permit) application for eligible immigrants", "url": "https://www.uscis.gov/i-765", "applies_to": ["green_card", "student", "asylum"], "category": "application", "mandatory": False},
            {"form_id": "i_131", "name": "Form I-131 - Application for Travel Document", "description": "Advance Parole for travel while adjustment of status is pending", "url": "https://www.uscis.gov/i-131", "applies_to": ["green_card", "asylum"], "category": "application", "mandatory": False},
        ]
    },
    "new_zealand": {
        "country": "New Zealand",
        "authority": "Immigration New Zealand (INZ)",
        "base_url": "https://www.immigration.govt.nz",
        "forms": [
            {"form_id": "inz_1015", "name": "INZ 1015 - Skilled Migrant Category Expression of Interest", "description": "EOI form for Skilled Migrant Category", "url": "https://www.immigration.govt.nz/documents/forms-and-guides/inz1015.pdf", "applies_to": ["skilled_migrant", "pr"], "category": "application", "mandatory": True},
            {"form_id": "inz_1007", "name": "INZ 1007 - Medical Certificate", "description": "Medical examination form completed by panel physician", "url": "https://www.immigration.govt.nz/documents/forms-and-guides/inz1007.pdf", "applies_to": ["skilled_migrant", "pr", "work", "student"], "category": "medical", "mandatory": True},
            {"form_id": "inz_1096", "name": "INZ 1096 - Chest X-Ray Certificate", "description": "Chest X-ray certificate for health screening", "url": "https://www.immigration.govt.nz/documents/forms-and-guides/inz1096.pdf", "applies_to": ["skilled_migrant", "pr", "work", "student"], "category": "medical", "mandatory": True},
            {"form_id": "inz_1025", "name": "INZ 1025 - Application for Work Visa", "description": "Main application form for work visa", "url": "https://www.immigration.govt.nz/documents/forms-and-guides/inz1025.pdf", "applies_to": ["work"], "category": "application", "mandatory": True},
            {"form_id": "inz_1012", "name": "INZ 1012 - Application for Student Visa", "description": "Application form for student visa", "url": "https://www.immigration.govt.nz/documents/forms-and-guides/inz1012.pdf", "applies_to": ["student"], "category": "application", "mandatory": True},
        ]
    },
    "uae": {
        "country": "United Arab Emirates",
        "authority": "Federal Authority for Identity, Citizenship, Customs and Port Security (ICP)",
        "base_url": "https://u.ae",
        "forms": [
            {"form_id": "uae_entry_permit", "name": "Entry Permit Application", "description": "Online entry permit application via ICP Smart Services or GDRFA", "url": "https://smartservices.icp.gov.ae/echannels/web/client/default.html", "applies_to": ["work", "golden", "visit", "student"], "category": "application", "mandatory": True},
            {"form_id": "uae_medical", "name": "Medical Fitness Test", "description": "Medical fitness certificate from DHA-approved center", "url": "https://www.dha.gov.ae/en/ServiceCatalogue/Service.aspx?ServiceId=186", "applies_to": ["work", "golden", "student"], "category": "medical", "mandatory": True},
            {"form_id": "uae_eid", "name": "Emirates ID Application", "description": "Emirates ID registration/renewal application", "url": "https://smartservices.icp.gov.ae/echannels/web/client/default.html", "applies_to": ["work", "golden", "student"], "category": "identity", "mandatory": True},
        ]
    },
    "singapore": {
        "country": "Singapore",
        "authority": "Ministry of Manpower (MOM) / Immigration & Checkpoints Authority (ICA)",
        "base_url": "https://www.mom.gov.sg",
        "forms": [
            {"form_id": "sg_ep_online", "name": "EP Online Application", "description": "Employment Pass online application via MOM EP Online portal", "url": "https://www.mom.gov.sg/passes-and-permits/employment-pass/apply-for-a-pass", "applies_to": ["ep", "work"], "category": "application", "mandatory": True},
            {"form_id": "sg_form_8", "name": "Form 8 - Application for Entry Permit / PR", "description": "Application for Singapore Permanent Residence", "url": "https://www.ica.gov.sg/reside/PR/apply", "applies_to": ["pr"], "category": "application", "mandatory": True},
            {"form_id": "sg_stpass", "name": "Student Pass Application (SOLAR)", "description": "Student Pass application via Student's Pass Online Application & Registration (SOLAR)", "url": "https://www.ica.gov.sg/enter/stpass/apply", "applies_to": ["student"], "category": "application", "mandatory": True},
        ]
    },
}


@router.get("/government-forms/{country}")
async def get_government_forms(country: str, current_user: dict = Depends(get_current_user)):
    """Get all official government forms for a country"""
    country_key = country.lower().replace(" ", "_")
    
    # Try direct match
    forms_data = GOVERNMENT_FORMS.get(country_key)
    
    # Try partial match
    if not forms_data:
        for key, data in GOVERNMENT_FORMS.items():
            if key in country_key or country_key in key or data["country"].lower() == country_key:
                forms_data = data
                break
    
    if not forms_data:
        return {"country": country, "authority": "", "forms": [], "message": "No forms available for this country yet"}
    
    return {
        "country": forms_data["country"],
        "authority": forms_data["authority"],
        "base_url": forms_data["base_url"],
        "forms": forms_data["forms"],
    }


@router.get("/government-forms/{country}/{visa_type}")
async def get_government_forms_by_visa(country: str, visa_type: str, current_user: dict = Depends(get_current_user)):
    """Get official government forms filtered by visa type"""
    country_key = country.lower().replace(" ", "_")
    visa_lower = visa_type.lower().replace(" ", "_").replace("-", "_")
    
    forms_data = GOVERNMENT_FORMS.get(country_key)
    if not forms_data:
        for key, data in GOVERNMENT_FORMS.items():
            if key in country_key or country_key in key or data["country"].lower() == country_key:
                forms_data = data
                break
    
    if not forms_data:
        return {"country": country, "visa_type": visa_type, "forms": []}
    
    # Filter forms that apply to this visa type
    filtered = [f for f in forms_data["forms"] if any(visa_lower in a or a in visa_lower for a in f["applies_to"])]
    
    # If no specific match, return all mandatory forms
    if not filtered:
        filtered = [f for f in forms_data["forms"] if f.get("mandatory")]
    
    return {
        "country": forms_data["country"],
        "authority": forms_data["authority"],
        "visa_type": visa_type,
        "forms": filtered,
    }


@router.get("/government-forms")
async def get_all_government_forms_countries(current_user: dict = Depends(get_current_user)):
    """Get list of countries that have government forms available"""
    countries = []
    for key, data in GOVERNMENT_FORMS.items():
        countries.append({
            "id": key,
            "country": data["country"],
            "authority": data["authority"],
            "total_forms": len(data["forms"]),
            "base_url": data["base_url"],
        })
    return {"countries": countries}
