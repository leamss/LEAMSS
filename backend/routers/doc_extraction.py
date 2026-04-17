"""
Document Info Extraction
------------------------
Vision-LLM powered document field extraction.
- Auto-detects doc_type from image (passport, visa, educational, bank, PCC, marriage/birth certs, IELTS, etc.)
- Returns structured fields with per-field confidence scores
- Supports base64 upload (file or camera) and multipart upload
- Pre-loaded sample documents with mock extraction for demo mode
"""
import os
import uuid
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv

from core.auth import get_current_user
from core.database import db

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doc-extraction", tags=["Document Extraction"])

extractions_col = db["doc_extractions"]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


# =========================================================================
#  DOCUMENT TYPE CATALOG — known document types & their expected fields
# =========================================================================
DOC_TYPES: Dict[str, Dict[str, Any]] = {
    "passport": {
        "name": "Passport",
        "fields": [
            "full_name", "given_names", "surname", "passport_number", "nationality",
            "date_of_birth", "place_of_birth", "sex", "date_of_issue",
            "date_of_expiry", "issuing_country", "issuing_authority",
            "mrz_line_1", "mrz_line_2",
        ],
    },
    "visa": {
        "name": "Visa",
        "fields": [
            "visa_number", "visa_type", "issuing_country", "holder_name",
            "passport_number", "issue_date", "expiry_date", "entries_allowed",
            "duration_of_stay", "purpose",
        ],
    },
    "educational_certificate": {
        "name": "Educational Certificate",
        "fields": [
            "candidate_name", "institution", "degree_or_qualification",
            "field_of_study", "grade_or_percentage", "year_of_passing",
            "certificate_number", "issue_date", "university_board",
        ],
    },
    "academic_transcript": {
        "name": "Academic Transcript / Marksheet",
        "fields": [
            "candidate_name", "institution", "program", "semester_or_year",
            "subjects_and_scores", "total_marks", "cgpa_or_percentage",
            "roll_number", "issue_date",
        ],
    },
    "ielts_scorecard": {
        "name": "IELTS Scorecard",
        "fields": [
            "candidate_name", "trf_number", "test_date", "centre_number",
            "listening", "reading", "writing", "speaking", "overall_band_score",
            "test_module",
        ],
    },
    "bank_statement": {
        "name": "Bank Statement",
        "fields": [
            "account_holder_name", "account_number", "bank_name", "branch",
            "ifsc_or_swift", "statement_period", "opening_balance",
            "closing_balance", "currency", "statement_date",
        ],
    },
    "police_clearance": {
        "name": "Police Clearance Certificate (PCC)",
        "fields": [
            "holder_name", "passport_number", "date_of_birth", "nationality",
            "issuing_country", "issue_date", "certificate_number",
            "remarks",
        ],
    },
    "marriage_certificate": {
        "name": "Marriage Certificate",
        "fields": [
            "husband_name", "wife_name", "date_of_marriage", "place_of_marriage",
            "certificate_number", "issuing_authority", "registration_date",
        ],
    },
    "birth_certificate": {
        "name": "Birth Certificate",
        "fields": [
            "full_name", "date_of_birth", "place_of_birth", "father_name",
            "mother_name", "sex", "certificate_number", "issuing_authority",
            "registration_date",
        ],
    },
    "driver_license": {
        "name": "Driver's License",
        "fields": [
            "holder_name", "license_number", "date_of_birth", "issue_date",
            "expiry_date", "address", "license_class", "issuing_authority",
        ],
    },
    "offer_letter": {
        "name": "Offer Letter / Admission Letter",
        "fields": [
            "candidate_name", "institution_or_employer", "program_or_position",
            "start_date", "duration", "tuition_or_salary", "conditions",
            "issue_date",
        ],
    },
    "unknown": {
        "name": "Unknown / Other",
        "fields": ["content_summary"],
    },
}


# =========================================================================
#  EXTRACTION PROMPT
# =========================================================================
SYSTEM_PROMPT = """You are a professional document information extractor for an immigration consultancy.
You analyze an uploaded document image and return STRICT JSON with:
  1. doc_type — one of: passport, visa, educational_certificate, academic_transcript, ielts_scorecard, bank_statement, police_clearance, marriage_certificate, birth_certificate, driver_license, offer_letter, unknown
  2. doc_type_name — human readable
  3. fields — object with key/value pairs relevant to that doc_type. Use snake_case keys. For missing values, use null (NOT empty string).
  4. confidences — object mapping each field key to a float 0.0-1.0
  5. overall_confidence — float 0.0-1.0 for overall extraction quality
  6. warnings — array of strings (e.g., ["blurry text", "partial crop", "low resolution"]) — empty if none
  7. summary — 1-2 sentence plain-English summary

RULES:
- Return ONLY valid JSON, no prose, no markdown fences.
- If the document is unreadable or not a document, set doc_type='unknown' with a warning.
- Extract dates in ISO 8601 (YYYY-MM-DD) where possible.
- Be conservative with confidence: if unsure, use <=0.5.
- DO NOT hallucinate fields that aren't visible — use null.
"""


# =========================================================================
#  SAMPLE DOCUMENTS (for Demo Mode)
# =========================================================================
SAMPLE_DOCS: List[Dict[str, Any]] = [
    {
        "id": "sample_passport_in",
        "name": "Indian Passport (Sample)",
        "doc_type": "passport",
        "thumbnail": "🛂",
        "description": "Specimen Indian passport — demonstrates MRZ parsing, dates, and personal data extraction",
        "extraction": {
            "doc_type": "passport",
            "doc_type_name": "Passport",
            "fields": {
                "full_name": "PRIYA SHARMA",
                "given_names": "PRIYA",
                "surname": "SHARMA",
                "passport_number": "Z7654321",
                "nationality": "INDIAN",
                "date_of_birth": "1995-04-12",
                "place_of_birth": "NEW DELHI",
                "sex": "F",
                "date_of_issue": "2021-06-15",
                "date_of_expiry": "2031-06-14",
                "issuing_country": "IND",
                "issuing_authority": "MINISTRY OF EXTERNAL AFFAIRS",
                "mrz_line_1": "P<INDSHARMA<<PRIYA<<<<<<<<<<<<<<<<<<<<<<<<<<",
                "mrz_line_2": "Z76543214IND9504124F3106147<<<<<<<<<<<<<<<06",
            },
            "confidences": {
                "full_name": 0.99, "given_names": 0.99, "surname": 0.99,
                "passport_number": 0.98, "nationality": 0.99,
                "date_of_birth": 0.97, "place_of_birth": 0.95, "sex": 0.99,
                "date_of_issue": 0.94, "date_of_expiry": 0.96,
                "issuing_country": 0.99, "issuing_authority": 0.92,
                "mrz_line_1": 0.99, "mrz_line_2": 0.99,
            },
            "overall_confidence": 0.97,
            "warnings": [],
            "summary": "Valid Indian passport for Priya Sharma issued in 2021, expires June 2031.",
        },
    },
    {
        "id": "sample_ielts",
        "name": "IELTS Academic Scorecard (Sample)",
        "doc_type": "ielts_scorecard",
        "thumbnail": "🎓",
        "description": "Specimen IELTS TRF — demonstrates band-score extraction per module",
        "extraction": {
            "doc_type": "ielts_scorecard",
            "doc_type_name": "IELTS Scorecard",
            "fields": {
                "candidate_name": "ROHIT KUMAR",
                "trf_number": "24IN002345RKUM024A",
                "test_date": "2024-11-16",
                "centre_number": "IN002",
                "listening": 7.5,
                "reading": 7.0,
                "writing": 6.5,
                "speaking": 7.5,
                "overall_band_score": 7.0,
                "test_module": "Academic",
            },
            "confidences": {
                "candidate_name": 0.99, "trf_number": 0.97, "test_date": 0.98,
                "centre_number": 0.96, "listening": 0.99, "reading": 0.99,
                "writing": 0.99, "speaking": 0.99, "overall_band_score": 0.99,
                "test_module": 0.99,
            },
            "overall_confidence": 0.98,
            "warnings": [],
            "summary": "IELTS Academic scorecard — overall band 7.0 (L7.5 R7.0 W6.5 S7.5), tested Nov 16, 2024.",
        },
    },
    {
        "id": "sample_bank_statement",
        "name": "Bank Statement (Sample)",
        "doc_type": "bank_statement",
        "thumbnail": "🏦",
        "description": "Specimen statement — demonstrates balance, account, and period extraction for proof-of-funds",
        "extraction": {
            "doc_type": "bank_statement",
            "doc_type_name": "Bank Statement",
            "fields": {
                "account_holder_name": "PRIYA SHARMA",
                "account_number": "XXXXXX4521",
                "bank_name": "HDFC BANK",
                "branch": "KORAMANGALA, BENGALURU",
                "ifsc_or_swift": "HDFC0001203",
                "statement_period": "2024-07-01 to 2024-12-31",
                "opening_balance": 485000.00,
                "closing_balance": 1284500.00,
                "currency": "INR",
                "statement_date": "2025-01-05",
            },
            "confidences": {
                "account_holder_name": 0.98, "account_number": 0.96,
                "bank_name": 0.99, "branch": 0.94, "ifsc_or_swift": 0.97,
                "statement_period": 0.93, "opening_balance": 0.99,
                "closing_balance": 0.99, "currency": 0.99, "statement_date": 0.95,
            },
            "overall_confidence": 0.96,
            "warnings": ["Account number partially masked"],
            "summary": "HDFC bank statement for Priya Sharma — closing balance ₹12,84,500 as of Dec 31, 2024.",
        },
    },
    {
        "id": "sample_degree",
        "name": "B.Tech Degree Certificate (Sample)",
        "doc_type": "educational_certificate",
        "thumbnail": "🎓",
        "description": "Specimen engineering degree — demonstrates qualification & grade extraction",
        "extraction": {
            "doc_type": "educational_certificate",
            "doc_type_name": "Educational Certificate",
            "fields": {
                "candidate_name": "ROHIT KUMAR",
                "institution": "Delhi Technological University",
                "degree_or_qualification": "Bachelor of Technology (B.Tech)",
                "field_of_study": "Computer Science & Engineering",
                "grade_or_percentage": "First Class with Distinction (CGPA 8.72)",
                "year_of_passing": "2022",
                "certificate_number": "DTU/2022/CSE/00428",
                "issue_date": "2022-08-20",
                "university_board": "Delhi Technological University",
            },
            "confidences": {
                "candidate_name": 0.99, "institution": 0.99,
                "degree_or_qualification": 0.98, "field_of_study": 0.97,
                "grade_or_percentage": 0.94, "year_of_passing": 0.99,
                "certificate_number": 0.95, "issue_date": 0.92,
                "university_board": 0.98,
            },
            "overall_confidence": 0.97,
            "warnings": [],
            "summary": "B.Tech Computer Science degree from Delhi Technological University, awarded 2022 with CGPA 8.72.",
        },
    },
    {
        "id": "sample_pcc",
        "name": "Police Clearance Certificate (Sample)",
        "doc_type": "police_clearance",
        "thumbnail": "🛡️",
        "description": "Specimen PCC — demonstrates clearance status extraction for visa applications",
        "extraction": {
            "doc_type": "police_clearance",
            "doc_type_name": "Police Clearance Certificate",
            "fields": {
                "holder_name": "PRIYA SHARMA",
                "passport_number": "Z7654321",
                "date_of_birth": "1995-04-12",
                "nationality": "INDIAN",
                "issuing_country": "INDIA",
                "issue_date": "2025-02-08",
                "certificate_number": "PCC/DEL/2025/001284",
                "remarks": "No adverse records found. Clearance valid for visa/immigration purposes.",
            },
            "confidences": {
                "holder_name": 0.99, "passport_number": 0.98,
                "date_of_birth": 0.97, "nationality": 0.99,
                "issuing_country": 0.99, "issue_date": 0.97,
                "certificate_number": 0.94, "remarks": 0.93,
            },
            "overall_confidence": 0.97,
            "warnings": [],
            "summary": "Clean PCC issued Feb 8, 2025 by Indian Passport Office — no adverse records.",
        },
    },
]


# =========================================================================
#  PYDANTIC MODELS
# =========================================================================
class ExtractRequest(BaseModel):
    image_base64: str  # may include data URI prefix
    mime_type: Optional[str] = None
    hint_doc_type: Optional[str] = None  # optional hint to guide extraction
    filename: Optional[str] = None


class SaveExtractionRequest(BaseModel):
    extraction: Dict[str, Any]
    case_id: Optional[str] = None
    document_id: Optional[str] = None
    filename: Optional[str] = None


# =========================================================================
#  HELPERS
# =========================================================================
def _strip_data_uri(b64: str) -> str:
    if not b64:
        return b64
    if b64.startswith("data:"):
        # data:image/png;base64,AAAA...
        comma = b64.find(",")
        if comma != -1:
            return b64[comma + 1:]
    return b64


def _guess_mime_from_header(b64: str) -> str:
    """Quick magic-byte sniff on the first decoded bytes."""
    try:
        raw = base64.b64decode(b64[:200] + "==")
    except Exception:
        return "image/png"
    if raw.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if raw.startswith(b"\x89PNG"):
        return "image/png"
    if raw.startswith(b"RIFF") and b"WEBP" in raw[:16]:
        return "image/webp"
    return "image/png"


async def _run_extraction(image_b64: str, mime_type: str, hint: Optional[str] = None) -> Dict[str, Any]:
    """Call the vision LLM and return parsed extraction JSON."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="Emergent LLM key not configured")

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"docx-{uuid.uuid4()}",
        system_message=SYSTEM_PROMPT,
    ).with_model("openai", "gpt-4o")

    user_text = "Extract all fields from this document image."
    if hint and hint in DOC_TYPES:
        expected = DOC_TYPES[hint]
        user_text += f" User hints this is a {expected['name']}. Expected fields: {', '.join(expected['fields'])}. Return JSON only."
    else:
        user_text += " Auto-detect document type. Return JSON only."

    image_content = ImageContent(image_base64=image_b64)
    message = UserMessage(text=user_text, file_contents=[image_content])

    try:
        raw_response = await chat.send_message(message)
    except Exception as e:
        logger.error(f"LLM vision call failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI extraction failed: {str(e)[:180]}")

    # Parse JSON from response
    text = str(raw_response).strip()
    # Strip accidental markdown fences
    if text.startswith("```"):
        text = text.strip("`")
        # remove leading 'json\n'
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3]
    text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to find embedded JSON
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
            except json.JSONDecodeError as e:
                logger.error(f"LLM JSON parse failed: {e}; raw: {text[:300]}")
                raise HTTPException(status_code=502, detail="AI returned unparseable response")
        else:
            raise HTTPException(status_code=502, detail="AI returned non-JSON response")

    # Normalize
    parsed.setdefault("doc_type", "unknown")
    parsed.setdefault("doc_type_name", DOC_TYPES.get(parsed["doc_type"], {}).get("name", "Document"))
    parsed.setdefault("fields", {})
    parsed.setdefault("confidences", {})
    parsed.setdefault("warnings", [])
    parsed.setdefault("summary", "")
    if "overall_confidence" not in parsed:
        confs = [float(v) for v in parsed.get("confidences", {}).values() if isinstance(v, (int, float))]
        parsed["overall_confidence"] = round(sum(confs) / len(confs), 3) if confs else 0.0
    return parsed


# =========================================================================
#  ENDPOINTS
# =========================================================================
@router.get("/doc-types")
async def list_doc_types(current_user: dict = Depends(get_current_user)):
    """List supported document types and their expected fields."""
    return {"doc_types": DOC_TYPES}


@router.get("/sample-docs")
async def list_sample_docs():
    """Public demo — list pre-loaded sample documents (no auth)."""
    return {
        "samples": [
            {k: v for k, v in s.items() if k != "extraction"}
            for s in SAMPLE_DOCS
        ]
    }


@router.get("/sample-docs/{sample_id}/extraction")
async def get_sample_extraction(sample_id: str):
    """Demo mode — return pre-computed extraction for an animated demo preview (no auth, no API cost)."""
    for s in SAMPLE_DOCS:
        if s["id"] == sample_id:
            return {
                "sample_id": sample_id,
                "name": s["name"],
                "doc_type": s["doc_type"],
                "extraction": s["extraction"],
                "demo": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
    raise HTTPException(status_code=404, detail="Sample not found")


@router.post("/extract")
async def extract_from_base64(data: ExtractRequest, current_user: dict = Depends(get_current_user)):
    """Extract fields from a base64-encoded image."""
    if not data.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    image_b64 = _strip_data_uri(data.image_base64)
    mime = (data.mime_type or _guess_mime_from_header(image_b64)).lower()
    if mime not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"Unsupported mime: {mime}. Use JPEG/PNG/WEBP.")

    # Rough size check
    try:
        approx_bytes = (len(image_b64) * 3) // 4
    except Exception:
        approx_bytes = 0
    if approx_bytes > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 8 MB)")

    extraction = await _run_extraction(image_b64, mime, data.hint_doc_type)
    return {
        "id": str(uuid.uuid4()),
        "doc_type": extraction.get("doc_type", "unknown"),
        "mime_type": mime,
        "extraction": extraction,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/extract-upload")
async def extract_from_upload(
    file: UploadFile = File(...),
    hint_doc_type: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Extract fields from a multipart file upload."""
    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 8 MB)")

    mime = (file.content_type or "").lower()
    # Reject non-image content types early
    if not mime.startswith("image/"):
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}. Use JPEG/PNG/WEBP.")
    if mime not in ALLOWED_MIME:
        # fall back to sniff on real bytes
        b64_head = base64.b64encode(content[:16]).decode()
        mime = _guess_mime_from_header(b64_head)
    if mime not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}. Use JPEG/PNG/WEBP.")

    image_b64 = base64.b64encode(content).decode()
    extraction = await _run_extraction(image_b64, mime, hint_doc_type)
    return {
        "id": str(uuid.uuid4()),
        "filename": file.filename,
        "doc_type": extraction.get("doc_type", "unknown"),
        "mime_type": mime,
        "extraction": extraction,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/save")
async def save_extraction(data: SaveExtractionRequest, current_user: dict = Depends(get_current_user)):
    """Persist an extraction for later retrieval (attach to case/document)."""
    doc = {
        "id": str(uuid.uuid4()),
        "extraction": data.extraction,
        "case_id": data.case_id,
        "document_id": data.document_id,
        "filename": data.filename,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "created_by_role": current_user.get("role", ""),
        "created_at": datetime.now(timezone.utc),
    }
    await extractions_col.insert_one(doc)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc


@router.get("/history")
async def list_history(
    case_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List saved extractions — filterable by case."""
    q: Dict[str, Any] = {}
    if case_id:
        q["case_id"] = case_id
    if current_user.get("role") == "client":
        q["created_by"] = current_user["id"]
    elif current_user.get("role") == "partner":
        q["created_by"] = current_user["id"]
    items = await extractions_col.find(q, {"_id": 0}).sort("created_at", -1).to_list(100)
    for it in items:
        if isinstance(it.get("created_at"), datetime):
            it["created_at"] = it["created_at"].isoformat()
    return {"extractions": items, "total": len(items)}
