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
    """Check if all required documents are uploaded for a case"""
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    product = await products_col.find_one({"id": case.get("product_id")}, {"_id": 0})

    # Get uploaded documents for this case
    case_docs = await documents_col.find({"case_id": case_id}, {"_id": 0}).to_list(200)
    uploaded_types = [d.get("document_type", "").lower() for d in case_docs]

    # Standard required documents for immigration
    standard_required = [
        {"type": "passport", "label": "Passport Copy", "description": "Valid passport with at least 6 months validity"},
        {"type": "photo", "label": "Passport Photo", "description": "Recent passport-size photograph"},
        {"type": "birth_certificate", "label": "Birth Certificate", "description": "Certified birth certificate"},
        {"type": "education", "label": "Education Documents", "description": "Degree certificates, transcripts"},
        {"type": "employment", "label": "Employment Letter", "description": "Current employment verification letter"},
        {"type": "bank_statement", "label": "Bank Statement", "description": "Last 6 months bank statements"},
        {"type": "medical", "label": "Medical Report", "description": "Medical examination report"},
        {"type": "police_clearance", "label": "Police Clearance", "description": "Police verification certificate"},
    ]

    results = []
    missing = []
    for req in standard_required:
        found = any(req["type"] in ut or req["label"].lower() in ut for ut in uploaded_types)
        status = "uploaded" if found else "missing"
        entry = {**req, "status": status}
        if found:
            matching_doc = next((d for d in case_docs if req["type"] in d.get("document_type", "").lower() or req["label"].lower() in d.get("document_type", "").lower()), None)
            if matching_doc:
                entry["document_id"] = matching_doc.get("id")
                entry["filename"] = matching_doc.get("filename", "")
                entry["uploaded_at"] = matching_doc.get("uploaded_at", "")
        else:
            missing.append(req["label"])
        results.append(entry)

    total = len(standard_required)
    uploaded_count = sum(1 for r in results if r["status"] == "uploaded")
    completeness = round((uploaded_count / total) * 100) if total > 0 else 0

    return {
        "case_id": case_id,
        "product_name": product.get("name", "Unknown") if product else "Unknown",
        "total_required": total,
        "uploaded_count": uploaded_count,
        "missing_count": len(missing),
        "completeness_percentage": completeness,
        "missing_documents": missing,
        "document_checklist": results,
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
