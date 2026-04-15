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
    admin_docs_by_step = {}
    for aws in admin_wf_steps:
        step_name = aws.get("step_name", "")
        admin_docs_by_step[step_name] = aws.get("required_documents", [])

    # Get all uploaded documents for this case
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

        # Build a set of doc names already in case_steps (CM-added or previously synced)
        existing_names = set()
        for rd in case_req_docs:
            existing_names.add(_get_doc_name(rd).lower())

        # Merge: start with case_step docs, then add any NEW admin defaults not yet in case_steps
        merged_docs = list(case_req_docs)
        new_admin_docs = []
        for ad in admin_defaults:
            ad_name = _get_doc_name(ad)
            if ad_name and ad_name.lower() not in existing_names:
                merged_docs.append({
                    "doc_name": ad_name,
                    "description": ad.get("description", ""),
                    "is_mandatory": ad.get("is_mandatory", ad.get("mandatory", True)),
                    "tag": ad.get("tag", "mandatory"),
                    "notes": ad.get("notes", ""),
                    "source": "admin_default",
                    "added_by_name": "Admin",
                })
                new_admin_docs.append(ad_name)

        # Sync new admin docs to case_steps in DB (so they persist)
        if new_admin_docs:
            await case_steps_col.update_one(
                {"case_id": case_id, "step_name": step_name},
                {"$set": {"required_documents": merged_docs}}
            )

        # Build doc items for response
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
                "doc_name": doc_name,
                "is_mandatory": rd.get("is_mandatory", rd.get("mandatory", True)),
                "tag": rd.get("tag", "mandatory"),
                "notes": rd.get("notes", rd.get("description", "")),
                "source": rd.get("source", "admin_default"),
                "added_by_name": rd.get("added_by_name", "Admin"),
                "uploaded": matching is not None,
                "uploaded_doc": matching,
                "status": matching.get("status", "pending") if matching else "not_uploaded",
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



# ============ AI DOCUMENT SUGGESTIONS ============

import os
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


async def _call_ai(prompt: str, system_msg: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"doc-suggest-{uuid.uuid4().hex[:8]}",
            system_message=system_msg
        )
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
    """AI suggests documents for a specific workflow step"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or CM only")

    existing_str = ""
    if data.existing_docs:
        existing_str = "\nAlready added documents (do NOT repeat these): " + ", ".join(data.existing_docs)

    desc_str = ""
    if data.step_description:
        desc_str = "Step description: " + data.step_description

    example = '[{"doc_name":"Passport Copy","description":"Clear copy of all passport pages","is_mandatory":true,"doc_type":"passport"}]'

    prompt = (
        f'For an immigration product called "{data.product_name}", suggest the required documents for the workflow step "{data.step_name}".\n'
        f'{desc_str}\n{existing_str}\n\n'
        'Return a JSON array of document objects. Each object should have:\n'
        '- "doc_name": clear, professional document name\n'
        '- "description": one-line description of what this document is\n'
        '- "is_mandatory": true or false\n'
        '- "doc_type": one of passport, visa, certificate, id_card, photo, financial, medical, legal, other\n\n'
        f'Suggest 3-6 relevant documents. Return ONLY the JSON array, no markdown or explanation.\nExample: {example}'
    )

    system_msg = "You are an immigration documentation expert. Suggest accurate, relevant documents for immigration workflows. Return ONLY valid JSON arrays."

    result = await _call_ai(prompt, system_msg)

    try:
        # Clean up AI response
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
        "action": "ai_doc_suggestion", "entity_type": "workflow_step",
        "entity_id": f"{data.product_name}/{data.step_name}",
        "new_value": {"suggestions_count": len(suggestions)},
        "created_at": datetime.now(timezone.utc)
    })

    return {"suggestions": suggestions}


@router.post("/ai-suggest-bulk")
async def ai_suggest_bulk_documents(data: AIBulkSuggestRequest, current_user: dict = Depends(get_current_user)):
    """AI suggests documents for ALL steps of a product at once"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or CM only")

    steps_str = ""
    for i, step in enumerate(data.steps, 1):
        steps_str += f"\n{i}. {step.get('step_name', 'Step ' + str(i))}"
        if step.get("description"):
            steps_str += f" - {step['description']}"

    desc_part = f" ({data.product_description})" if data.product_description else ""
    example_bulk = '{"Step 1 Name": [{"doc_name":"Passport","description":"Valid passport copy","is_mandatory":true,"doc_type":"passport"}]}'

    prompt = (
        f'For an immigration product called "{data.product_name}"{desc_part}, suggest required documents for EACH workflow step.\n\n'
        f'Workflow steps:{steps_str}\n\n'
        'For EACH step, suggest 2-5 relevant documents. Return a JSON object where keys are EXACT step names and values are arrays of document objects.\n\n'
        'Each document object should have:\n'
        '- "doc_name": clear professional name\n'
        '- "description": one-line description\n'
        '- "is_mandatory": true or false\n'
        '- "doc_type": one of passport, visa, certificate, id_card, photo, financial, medical, legal, other\n\n'
        f'Return ONLY the JSON object, no markdown.\nExample: {example_bulk}'
    )

    system_msg = "You are an immigration documentation expert. Suggest accurate documents for each step. Return ONLY valid JSON."

    result = await _call_ai(prompt, system_msg)

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            cleaned = cleaned.rsplit("```", 1)[0]
        suggestions = json.loads(cleaned)
        if not isinstance(suggestions, dict):
            suggestions = {}
    except (json.JSONDecodeError, Exception):
        suggestions = {}

    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "ai_bulk_doc_suggestion", "entity_type": "product",
        "entity_id": data.product_name,
        "new_value": {"steps_count": len(data.steps), "suggestions": {k: len(v) for k, v in suggestions.items()}},
        "created_at": datetime.now(timezone.utc)
    })

    return {"suggestions": suggestions}
