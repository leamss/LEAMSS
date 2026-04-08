"""AI Document Verification Router — GPT-5.2 powered analysis"""
from fastapi import APIRouter, HTTPException, Depends, Query
from core.database import documents_col, cases_col
from core.auth import get_current_user
from core.services import create_notification, log_activity
import os, base64
from datetime import datetime, timezone

router = APIRouter(prefix="/ai", tags=["AI Verification"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


async def _analyze_document_with_gpt(file_path: str, filename: str, doc_type: str):
    """Analyze document content using GPT-5.2"""

    # Read file content
    content_preview = ""
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext in ['.txt', '.csv', '.md']:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                content_preview = f.read(5000)
        except Exception:
            content_preview = "Could not read file content"
    elif file_ext in ['.pdf']:
        try:
            import subprocess
            result = subprocess.run(['pdftotext', file_path, '-'], capture_output=True, text=True, timeout=15)
            content_preview = result.stdout[:5000] if result.returncode == 0 else "Could not extract PDF text"
        except Exception:
            content_preview = "PDF text extraction not available"
    elif file_ext in ['.png', '.jpg', '.jpeg', '.webp']:
        # For images, encode as base64 for vision
        try:
            with open(file_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            content_preview = f"[Image file: {filename}]"
        except Exception:
            content_preview = "Could not read image"
    else:
        content_preview = f"Binary file: {filename} ({file_ext})"

    prompt = f"""You are an immigration document verification specialist for LEAMSS Immigration Services.
Analyze this document and provide:
1. **Document Type**: What kind of document is this? (passport, visa, birth certificate, bank statement, employment letter, etc.)
2. **Completeness Score**: Rate 1-10 how complete/valid the document appears
3. **Key Information Extracted**: List any names, dates, ID numbers, or important details found
4. **Verification Status**: VERIFIED, NEEDS_REVIEW, or REJECTED
5. **Issues Found**: List any problems (blurry, missing info, expired, suspicious formatting)
6. **Recommendations**: What actions should the case manager take?

Document name: {filename}
Expected type: {doc_type}
Content:
{content_preview[:3000]}"""

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        import uuid as _uuid
        chat_instance = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"doc-verify-{_uuid.uuid4().hex[:8]}",
            system_message="You are an immigration document verification specialist."
        )
        user_message = UserMessage(text=prompt)
        response = await chat_instance.send_message(user_message)
        return {
            "analysis": response,
            "status": "completed",
            "model": "gpt-5.2",
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "analysis": f"AI analysis failed: {str(e)}",
            "status": "error",
            "model": "gpt-5.2",
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }


@router.post("/verify-document/{document_id}")
async def verify_document(document_id: str, current_user: dict = Depends(get_current_user)):
    """AI-powered document verification"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")

    doc = await documents_col.find_one({"id": document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    result = await _analyze_document_with_gpt(
        file_path, doc.get("filename", "unknown"), doc.get("document_type", "general")
    )

    # Store analysis result
    await documents_col.update_one({"id": document_id}, {"$set": {
        "ai_analysis": result,
        "ai_verified_at": datetime.now(timezone.utc),
        "ai_verified_by": current_user["id"]
    }})

    await log_activity(current_user["id"], current_user["name"], "ai_verify", "document", document_id,
        f"AI verification on: {doc.get('filename', '')}")

    return result


@router.get("/analysis/{document_id}")
async def get_analysis(document_id: str, current_user: dict = Depends(get_current_user)):
    """Get AI analysis result for a document"""
    doc = await documents_col.find_one({"id": document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    analysis = doc.get("ai_analysis")
    if not analysis:
        return {"status": "not_analyzed", "message": "This document has not been AI-verified yet"}
    return analysis
