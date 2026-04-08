"""AI Intelligence Router — Document Analysis, OCR, Chat Assistant, Case Prediction"""
import os
import uuid
import base64
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from core.database import db
from routers.auth import get_current_user

router = APIRouter(prefix="/ai-intel", tags=["AI Intelligence"])

documents_col = db["documents"]
cases_col = db["cases"]
sales_col = db["sales"]
users_col = db["users"]
products_col = db["products"]
workflow_steps_col = db["workflow_steps"]
chat_history_col = db["ai_chat_history"]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


async def _call_gpt(prompt: str, system_msg: str = "") -> str:
    """Unified GPT-5.2 call"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    try:
        chat_instance = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ai-intel-{uuid.uuid4().hex[:8]}",
            system_message=system_msg or "You are a helpful AI assistant."
        )
        user_message = UserMessage(text=prompt)
        return await chat_instance.send_message(user_message)
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"


def _read_file_content(file_path: str, filename: str) -> str:
    """Extract text content from various file types"""
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.txt', '.csv', '.md']:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                return f.read(8000)
        except Exception:
            return ""
    elif ext == '.pdf':
        try:
            import subprocess
            result = subprocess.run(['pdftotext', file_path, '-'], capture_output=True, text=True, timeout=15)
            return result.stdout[:8000] if result.returncode == 0 else ""
        except Exception:
            return ""
    elif ext in ['.png', '.jpg', '.jpeg', '.webp']:
        return f"[Image: {filename}]"
    return f"[Binary: {filename}]"


# ========== 1. AUTO DOCUMENT VERIFICATION ==========

@router.get("/case-document-check/{case_id}")
async def check_case_documents(case_id: str, current_user: dict = Depends(get_current_user)):
    """Check required documents per workflow step — based on product workflow, NOT hardcoded"""
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    product = await products_col.find_one({"id": case.get("product_id")}, {"_id": 0})
    steps = await workflow_steps_col.find(
        {"product_id": case.get("product_id")}, {"_id": 0}
    ).sort("step_order", 1).to_list(100)

    case_docs = await documents_col.find({"case_id": case_id}, {"_id": 0}).to_list(200)
    uploaded_names = [d.get("document_type", "").lower().strip() for d in case_docs]
    uploaded_filenames = [d.get("filename", "").lower().strip() for d in case_docs]

    step_results = []
    total_required = 0
    total_uploaded = 0
    all_missing = []
    current_step_order = case.get("current_step_order", 1)

    for step in steps:
        required_docs = step.get("required_documents", [])
        step_doc_results = []
        for req in required_docs:
            doc_name = req.get("doc_name", "Unknown")
            is_mandatory = req.get("is_mandatory", True)
            doc_lower = doc_name.lower().strip()
            found = any(doc_lower in ut or ut in doc_lower for ut in uploaded_names) or \
                    any(doc_lower in fn for fn in uploaded_filenames)
            if is_mandatory:
                total_required += 1
                if found:
                    total_uploaded += 1
            matching = next((d for d in case_docs if doc_lower in d.get("document_type","").lower() or d.get("document_type","").lower() in doc_lower), None)
            step_doc_results.append({
                "doc_name": doc_name, "is_mandatory": is_mandatory,
                "status": "uploaded" if found else "missing",
                "document_id": matching.get("id") if matching else None,
                "filename": matching.get("filename","") if matching else None,
            })
            if not found and is_mandatory:
                all_missing.append({"doc_name": doc_name, "step_name": step.get("step_name",""), "step_order": step.get("step_order",0)})

        step_results.append({
            "step_name": step.get("step_name",""), "step_order": step.get("step_order",0),
            "required_documents": step_doc_results,
            "total_required": len([d for d in step_doc_results if d["is_mandatory"]]),
            "total_uploaded": len([d for d in step_doc_results if d["status"]=="uploaded" and d["is_mandatory"]]),
            "is_complete": all(d["status"]=="uploaded" for d in step_doc_results if d["is_mandatory"]) if step_doc_results else True,
            "is_locked": step.get("step_order",0) > current_step_order
        })

    completeness = round((total_uploaded / total_required) * 100) if total_required > 0 else 100
    return {
        "case_id": case_id,
        "product_name": product.get("name","Unknown") if product else "Unknown",
        "current_step": case.get("current_step",""),
        "current_step_order": current_step_order,
        "total_required": total_required,
        "uploaded_count": total_uploaded,
        "missing_count": len(all_missing),
        "completeness_percentage": completeness,
        "missing_documents": all_missing,
        "steps": step_results,
        "status": "complete" if completeness == 100 else "incomplete"
    }


# ========== 2. DOCUMENT FORMAT VALIDATION ==========

@router.post("/validate-document/{document_id}")
async def validate_document_format(document_id: str, current_user: dict = Depends(get_current_user)):
    """AI validates document format (passport, visa, etc.)"""
    doc = await documents_col.find_one({"id": document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    content = _read_file_content(file_path, doc.get("filename", ""))
    doc_type = doc.get("document_type", "general")

    prompt = f"""You are an immigration document format validator.
Analyze this document and validate its format:

Document Type Expected: {doc_type}
Filename: {doc.get('filename', '')}
Content: {content[:4000]}

Provide your analysis in this EXACT JSON format (no markdown, just raw JSON):
{{
    "format_valid": true/false,
    "document_type_detected": "passport/visa/birth_cert/bank_statement/education/employment/medical/police_clearance/other",
    "type_matches_expected": true/false,
    "quality_score": 1-10,
    "issues": ["list of format issues found"],
    "details_found": {{
        "name": "extracted name or null",
        "date_of_birth": "extracted DOB or null",
        "document_number": "extracted number or null",
        "expiry_date": "extracted expiry or null",
        "issuing_authority": "extracted authority or null",
        "nationality": "extracted nationality or null"
    }},
    "recommendation": "APPROVED/NEEDS_REUPLOAD/REJECTED",
    "notes": "brief explanation"
}}"""

    result = await _call_gpt(prompt, "You are a strict document format validator. Always respond with valid JSON only.")

    # Parse AI response
    import json
    try:
        parsed = json.loads(result.strip().strip('```json').strip('```'))
    except (json.JSONDecodeError, Exception):
        parsed = {"raw_analysis": result, "format_valid": None, "recommendation": "NEEDS_REVIEW"}

    # Store validation result
    await documents_col.update_one({"id": document_id}, {"$set": {
        "format_validation": parsed,
        "format_validated_at": datetime.now(timezone.utc).isoformat()
    }})

    return {**parsed, "document_id": document_id, "filename": doc.get("filename", "")}


# ========== 3. OCR & DATA EXTRACTION ==========

@router.post("/extract-data/{document_id}")
async def extract_document_data(document_id: str, current_user: dict = Depends(get_current_user)):
    """OCR — Extract structured data from a document"""
    doc = await documents_col.find_one({"id": document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    content = _read_file_content(file_path, doc.get("filename", ""))

    prompt = f"""Extract ALL structured data from this immigration document.

Document: {doc.get('filename', '')}
Type: {doc.get('document_type', 'unknown')}
Content: {content[:5000]}

Return ONLY valid JSON with these fields (use null for missing):
{{
    "full_name": "string",
    "date_of_birth": "YYYY-MM-DD",
    "gender": "male/female/other",
    "nationality": "string",
    "passport_number": "string",
    "passport_expiry": "YYYY-MM-DD",
    "address": "string",
    "phone": "string",
    "email": "string",
    "education_level": "string",
    "occupation": "string",
    "employer": "string",
    "annual_income": "string",
    "marital_status": "string",
    "language_scores": {{"ielts": null, "pte": null, "toefl": null}},
    "additional_data": {{}}
}}"""

    result = await _call_gpt(prompt, "You are an OCR specialist. Extract data accurately. Return only valid JSON.")

    import json
    try:
        extracted = json.loads(result.strip().strip('```json').strip('```'))
    except (json.JSONDecodeError, Exception):
        extracted = {"raw_extraction": result, "extraction_status": "partial"}

    # Store extraction
    await documents_col.update_one({"id": document_id}, {"$set": {
        "extracted_data": extracted,
        "extracted_at": datetime.now(timezone.utc).isoformat()
    }})

    return {"document_id": document_id, "filename": doc.get("filename", ""), "extracted_data": extracted}


# ========== 4. AUTO-FILL CLIENT INFO ==========

@router.post("/auto-fill/{case_id}")
async def auto_fill_client_info(case_id: str, current_user: dict = Depends(get_current_user)):
    """Extract data from all case documents and auto-fill client info sheet"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")

    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get all documents with extracted data
    case_docs = await documents_col.find(
        {"case_id": case_id, "extracted_data": {"$exists": True}},
        {"_id": 0}
    ).to_list(50)

    if not case_docs:
        # Try extracting from all docs first
        all_docs = await documents_col.find({"case_id": case_id}, {"_id": 0}).to_list(50)
        all_content = []
        for d in all_docs:
            fp = d.get("file_path", "")
            if fp and os.path.exists(fp):
                c = _read_file_content(fp, d.get("filename", ""))
                if c:
                    all_content.append(f"[{d.get('document_type', 'doc')}: {d.get('filename', '')}]\n{c[:2000]}")

        if not all_content:
            return {"message": "No documents found to extract from", "auto_filled": False}

        combined = "\n\n---\n\n".join(all_content[:5])

        prompt = f"""From these immigration case documents, extract all client information.

Documents:
{combined[:6000]}

Return ONLY valid JSON:
{{
    "full_name": "string or null",
    "date_of_birth": "YYYY-MM-DD or null",
    "gender": "string or null",
    "nationality": "string or null",
    "passport_number": "string or null",
    "passport_expiry": "YYYY-MM-DD or null",
    "address": "string or null",
    "phone": "string or null",
    "email": "string or null",
    "education_level": "string or null",
    "occupation": "string or null",
    "employer": "string or null",
    "marital_status": "string or null",
    "dependents": 0,
    "language_test_type": "IELTS/PTE/TOEFL or null",
    "language_score": "score or null",
    "work_experience_years": 0
}}"""

        result = await _call_gpt(prompt, "Extract client data accurately from documents. JSON only.")
        import json
        try:
            auto_data = json.loads(result.strip().strip('```json').strip('```'))
        except Exception:
            auto_data = {}
    else:
        # Merge extracted data from all documents
        auto_data = {}
        for doc in case_docs:
            ed = doc.get("extracted_data", {})
            for k, v in ed.items():
                if v and v != "null" and k not in ["raw_extraction", "extraction_status", "additional_data"]:
                    if k not in auto_data or not auto_data[k]:
                        auto_data[k] = v

    # Save as auto-fill suggestion for the case
    info_sheets_col = db["information_sheets"]
    await info_sheets_col.update_one(
        {"case_id": case_id},
        {"$set": {
            "auto_filled_data": auto_data,
            "auto_filled_at": datetime.now(timezone.utc).isoformat(),
            "auto_filled_by": "ai_system"
        }},
        upsert=True
    )

    return {"case_id": case_id, "auto_filled_data": auto_data, "auto_filled": True, "fields_extracted": len([v for v in auto_data.values() if v])}


# ========== 5. AI CHAT ASSISTANT ==========

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@router.post("/chat")
async def ai_chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """AI Chat Assistant for client queries — visa status, requirements, process"""
    session_id = request.session_id or str(uuid.uuid4())

    # Get user context
    user_cases = await cases_col.find(
        {"client_id": current_user["id"]}, {"_id": 0}
    ).to_list(10) if current_user["role"] == "client" else []

    # Enrich case info
    case_summaries = []
    for c in user_cases:
        product = await products_col.find_one({"id": c.get("product_id")}, {"_id": 0, "name": 1})
        case_summaries.append(
            f"Case {c.get('case_id','?')}: {product.get('name','?') if product else '?'} | Status: {c.get('status','?')} | Step: {c.get('current_step','?')}"
        )

    # Get recent chat history for context
    history = await chat_history_col.find(
        {"session_id": session_id, "user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(6).to_list(6)
    history.reverse()

    history_text = "\n".join([f"{'User' if h['role']=='user' else 'Assistant'}: {h['content'][:200]}" for h in history])

    case_info = "\n".join(case_summaries) if case_summaries else "No active cases found."

    # Build context-aware prompt
    system_msg = f"""You are the LEAMSS Immigration Services AI Assistant. You help clients with:
- Visa status inquiries and case updates
- Document requirements for different immigration programs
- Immigration process explanations
- General immigration queries
- Fee and payment queries

Current user: {current_user.get('name', 'Client')} (Role: {current_user['role']})
Active Cases:
{case_info}

Rules:
- Be helpful, professional, and concise
- For specific case status, refer to the case details above
- For document queries, list specific required documents
- Never share other clients' data
- If unsure, suggest contacting the case manager directly
- Keep responses under 300 words"""

    prompt = f"""Chat History:
{history_text}

User message: {request.message}"""

    response = await _call_gpt(prompt, system_msg)

    # Save chat history
    now = datetime.now(timezone.utc)
    await chat_history_col.insert_many([
        {"id": str(uuid.uuid4()), "session_id": session_id, "user_id": current_user["id"],
         "role": "user", "content": request.message, "created_at": now},
        {"id": str(uuid.uuid4()), "session_id": session_id, "user_id": current_user["id"],
         "role": "assistant", "content": response, "created_at": now}
    ])

    return {"response": response, "session_id": session_id}


@router.get("/chat/history")
async def get_chat_history(session_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Get chat history for current user"""
    query = {"user_id": current_user["id"]}
    if session_id:
        query["session_id"] = session_id

    messages = await chat_history_col.find(query, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    messages.reverse()

    for m in messages:
        if "created_at" in m and hasattr(m["created_at"], "isoformat"):
            m["created_at"] = m["created_at"].isoformat()

    return messages


# ========== 6. CASE APPROVAL PREDICTION ==========

@router.get("/predict-approval/{case_id}")
async def predict_approval(case_id: str, current_user: dict = Depends(get_current_user)):
    """AI predicts approval probability based on client profile + documents"""
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Gather case data
    product = await products_col.find_one({"id": case.get("product_id")}, {"_id": 0})
    client = await users_col.find_one({"id": case.get("client_id")}, {"_id": 0, "password": 0})
    sale = await sales_col.find_one({"id": case.get("sale_id")}, {"_id": 0})

    # Document completeness
    case_docs = await documents_col.find({"case_id": case_id}, {"_id": 0}).to_list(50)
    doc_types = [d.get("document_type", "") for d in case_docs]
    doc_statuses = [d.get("status", "pending") for d in case_docs]

    # Info sheet data
    info_sheets_col = db["information_sheets"]
    info = await info_sheets_col.find_one({"case_id": case_id}, {"_id": 0})
    auto_data = info.get("auto_filled_data", {}) if info else {}

    prompt = f"""You are an immigration case assessment AI.
Analyze this case and predict approval probability.

Program: {product.get('name', 'Unknown') if product else 'Unknown'}
Category: {product.get('category', '') if product else ''}

Client Profile:
- Name: {client.get('name', 'Unknown') if client else 'Unknown'}
- Documents uploaded: {len(case_docs)} ({', '.join(doc_types[:10])})
- Document review status: {dict((s, doc_statuses.count(s)) for s in set(doc_statuses))}
- Current step: {case.get('current_step', 'N/A')}
- Case status: {case.get('status', 'N/A')}
- Auto-extracted profile: {str(auto_data)[:500] if auto_data else 'Not available'}
- Payment status: {sale.get('payment_status', 'N/A') if sale else 'N/A'}

Return ONLY valid JSON:
{{
    "approval_probability": 0-100,
    "confidence": "high/medium/low",
    "risk_level": "low/medium/high",
    "strengths": ["list up to 4 positive factors"],
    "weaknesses": ["list up to 4 risk factors"],
    "missing_actions": ["list up to 4 recommended actions"],
    "prediction_summary": "2-3 sentence summary",
    "estimated_timeline": "estimated processing time"
}}"""

    result = await _call_gpt(prompt, "You are an immigration case assessor. Provide realistic predictions based on available data. JSON only.")

    import json
    try:
        prediction = json.loads(result.strip().strip('```json').strip('```'))
    except Exception:
        prediction = {
            "approval_probability": 50,
            "confidence": "low",
            "risk_level": "medium",
            "strengths": ["Case is in progress"],
            "weaknesses": ["Insufficient data for accurate prediction"],
            "missing_actions": ["Upload all required documents", "Complete profile information"],
            "prediction_summary": "Unable to provide detailed prediction. Please ensure all documents are uploaded and profile is complete.",
            "estimated_timeline": "Varies by program"
        }

    # Store prediction
    await cases_col.update_one({"id": case_id}, {"$set": {
        "ai_prediction": prediction,
        "ai_prediction_at": datetime.now(timezone.utc).isoformat()
    }})

    return {
        "case_id": case_id,
        "product_name": product.get("name", "Unknown") if product else "Unknown",
        **prediction
    }



# ========== 7. RESUME EXTRACT & AUTO-FILL INFO SHEET ==========

@router.post("/extract-resume-to-infosheet/{case_id}")
async def extract_resume_to_infosheet(case_id: str, document_id: str, current_user: dict = Depends(get_current_user)):
    """Extract data from a resume/document and auto-fill the information sheet"""
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    doc = await documents_col.find_one({"id": document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    content = _read_file_content(file_path, doc.get("filename", ""))

    prompt = f"""Extract ALL personal, educational, and professional information from this document for an immigration application.
IMPORTANT: Extract COMPLETE data — full phone numbers (all digits), full addresses, complete dates.

Document: {doc.get('filename', '')}
Content:
{content[:8000]}

Return ONLY valid JSON with these fields (use null for fields you cannot find):
{{
    "given_names": "first and middle names",
    "family_name": "last/surname",
    "other_names": "any alternative names or null",
    "gender": "Male/Female",
    "date_of_birth": "YYYY-MM-DD",
    "country_of_birth": "string",
    "city_of_birth": "string",
    "address": "full communication address with city, state, pin code",
    "email": "complete email address",
    "contact_number": "COMPLETE phone number with country code (all digits)",
    "alternative_number": "COMPLETE alternative number or null",
    "aadhaar_number": "12 digit aadhaar or null",
    "nationality": "string",
    "passport_number": "string",
    "passport_issue_date": "YYYY-MM-DD or null",
    "passport_expiry_date": "YYYY-MM-DD or null",
    "passport_place_of_issue": "string or null",
    "marital_status": "Single/Married/Divorced/Widowed",
    "spouse_name": "string or null",
    "father_name": "string",
    "mother_name": "string or null",
    "qualifications": [
        {{
            "name": "qualification name (e.g., B.Tech, MBA)",
            "field_of_study": "major/specialization",
            "institute_name": "college/university name",
            "start_date": "YYYY-MM-DD or null",
            "end_date": "YYYY-MM-DD or null"
        }}
    ],
    "employment_history": [
        {{
            "business_name": "company name",
            "job_title": "designation/role",
            "start_date": "YYYY-MM-DD or null",
            "end_date": "YYYY-MM-DD or null (null if current job)",
            "address": "company address or null"
        }}
    ],
    "skills": "comma separated skills",
    "language_test_type": "IELTS/PTE/TOEFL or null",
    "language_score": "score or null"
}}

RULES:
- Phone numbers MUST include ALL digits (e.g., +91-9876543210 or 9876543210). Never truncate.
- Dates must be YYYY-MM-DD format.
- Extract education details from ALL degrees/qualifications mentioned.
- Extract ALL work experiences mentioned.
- If the document mentions name as "John Doe", given_names="John", family_name="Doe"."""

    result = await _call_gpt(prompt, "You are an expert data extractor for immigration applications. Extract COMPLETE and ACCURATE data from documents. Return ONLY valid JSON, no markdown.")

    import json
    try:
        cleaned = result.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1] if '\n' in cleaned else cleaned[3:]
            cleaned = cleaned.rsplit('```', 1)[0]
        extracted = json.loads(cleaned)
    except Exception:
        extracted = {}

    if not extracted:
        return {"success": False, "message": "Could not extract data from this document. Try a clearer document.", "extracted": {}}

    # Auto-fill info sheet — map extracted data to schema fields
    info_sheets_col = db["information_sheets"]
    existing = await info_sheets_col.find_one({"case_id": case_id}, {"_id": 0})

    fields_filled = 0
    update_data = {}

    # Map flat fields
    flat_keys = ["given_names", "family_name", "other_names", "gender", "date_of_birth",
                 "country_of_birth", "city_of_birth", "address", "email", "contact_number",
                 "alternative_number", "aadhaar_number", "nationality", "passport_number",
                 "passport_issue_date", "passport_expiry_date", "passport_place_of_issue",
                 "marital_status", "spouse_name", "father_name", "mother_name",
                 "skills", "language_test_type", "language_score"]

    for key in flat_keys:
        value = extracted.get(key)
        if value and str(value).strip() and str(value).strip().lower() != "null":
            if not existing or not existing.get(key) or str(existing.get(key, "")).strip() in ["", "null", "None"]:
                update_data[key] = str(value).strip()
                fields_filled += 1

    # Map qualifications array to schema format
    quals = extracted.get("qualifications", [])
    if isinstance(quals, list):
        for i, q in enumerate(quals[:4]):
            if isinstance(q, dict):
                prefix = f"qualification_{i+1}"
                for qk, qv in q.items():
                    if qv and str(qv).strip().lower() != "null":
                        full_key = f"{prefix}_{qk}"
                        if not existing or not existing.get(full_key):
                            update_data[full_key] = str(qv).strip()
                            fields_filled += 1

    # Map employment array to schema format
    emps = extracted.get("employment_history", [])
    if isinstance(emps, list):
        for i, emp in enumerate(emps[:4]):
            if isinstance(emp, dict):
                prefix = f"employment_{i+1}"
                for ek, ev in emp.items():
                    if ev and str(ev).strip().lower() != "null":
                        full_key = f"{prefix}_{ek}"
                        if not existing or not existing.get(full_key):
                            update_data[full_key] = str(ev).strip()
                            fields_filled += 1

    if update_data:
        update_data["auto_filled_at"] = datetime.now(timezone.utc).isoformat()
        update_data["auto_filled_from"] = document_id
        update_data["case_id"] = case_id
        update_data["client_id"] = case.get("client_id")
        await info_sheets_col.update_one(
            {"case_id": case_id},
            {"$set": update_data},
            upsert=True
        )

    return {
        "success": True,
        "fields_extracted": len([v for v in extracted.values() if v and str(v) != "null"]),
        "fields_filled": fields_filled,
        "extracted_data": extracted,
        "message": f"Extracted {fields_filled} fields and auto-filled into information sheet."
    }


# ========== 8. STEP STATUS WITH LOCK INFO ==========

@router.get("/step-status/{case_id}")
async def get_step_status(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get all steps with lock/unlock status and document requirements"""
    from core.database import db
    case_steps_col = db["case_steps"]

    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    steps = await case_steps_col.find({"case_id": case_id}, {"_id": 0}).sort("step_order", 1).to_list(100)
    workflow_steps = await workflow_steps_col.find(
        {"product_id": case.get("product_id")}, {"_id": 0}
    ).sort("step_order", 1).to_list(100)

    case_docs = await documents_col.find({"case_id": case_id}, {"_id": 0}).to_list(200)
    uploaded_names = [d.get("document_type", "").lower().strip() for d in case_docs]

    current_step_order = case.get("current_step_order", 1)
    result = []

    for step in steps:
        order = step.get("step_order", 0)
        wf = next((w for w in workflow_steps if w.get("step_name") == step.get("step_name")), {})
        required_docs = wf.get("required_documents", [])

        # Check doc completion for this step
        docs_status = []
        all_docs_uploaded = True
        for req in required_docs:
            doc_lower = req.get("doc_name", "").lower().strip()
            found = any(doc_lower in ut or ut in doc_lower for ut in uploaded_names)
            docs_status.append({"doc_name": req.get("doc_name"), "is_mandatory": req.get("is_mandatory", True), "uploaded": found})
            if req.get("is_mandatory", True) and not found:
                all_docs_uploaded = False

        # Check if all previous steps are completed
        prev_completed = all(s.get("status") == "completed" for s in steps if s.get("step_order", 0) < order)

        is_locked = not prev_completed and order > 1
        can_complete = prev_completed and all_docs_uploaded

        result.append({
            "step_name": step.get("step_name"),
            "step_order": order,
            "status": step.get("status", "pending"),
            "notes": step.get("notes", ""),
            "is_current": order == current_step_order,
            "is_locked": is_locked,
            "can_complete": can_complete,
            "required_documents": docs_status,
            "all_docs_uploaded": all_docs_uploaded,
            "previous_completed": prev_completed
        })

    return {"case_id": case_id, "steps": result, "current_step_order": current_step_order}
