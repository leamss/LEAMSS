"""AI Workflow Builder — Generate country-specific immigration workflows using GPT-5.2"""
import os
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

router = APIRouter(prefix="/ai-workflow", tags=["AI Workflow Builder"])

products_col = db["products"]
workflow_steps_col = db["workflow_steps"]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


class WorkflowGenerateRequest(BaseModel):
    country: str
    service_type: str
    custom_instructions: Optional[str] = ""


class WorkflowSaveRequest(BaseModel):
    product_name: str
    description: str
    category: str
    base_fee: float
    commission_rate: float
    steps: List[dict]


COUNTRY_REFERENCES = {
    "canada": {
        "pr": "Immigration, Refugees and Citizenship Canada (IRCC) - Express Entry System. Reference: ircc.canada.ca. CRS scoring, ECA requirements, language testing (IELTS/CELPIP/TEF), NOC codes for skilled workers.",
        "visitor": "Temporary Resident Visa (TRV). Reference: ircc.canada.ca. eTA for visa-exempt countries, biometrics requirement, proof of funds, travel itinerary.",
        "student": "Study Permit. Reference: ircc.canada.ca. DLI acceptance letter, GIC proof, language scores, SDS stream."
    },
    "australia": {
        "pr": "Department of Home Affairs - Skilled Migration (Subclass 189/190/491). Reference: homeaffairs.gov.au. SkillSelect EOI system, skills assessment (VETASSESS/ACS/Engineers Australia), points test, state nomination.",
        "visitor": "Visitor Visa Subclass 600. Reference: homeaffairs.gov.au. Tourist stream, business visitor, sponsored family stream. Online application via ImmiAccount.",
        "student": "Student Visa Subclass 500. Reference: homeaffairs.gov.au. CoE, Genuine Temporary Entrant (GTE), OSHC, financial capacity evidence."
    },
    "uk": {
        "visitor": "Standard Visitor Visa. Reference: gov.uk/standard-visitor. Up to 6 months, must not work, proof of accommodation and funds, return ticket.",
        "work": "Skilled Worker Visa. Reference: gov.uk/skilled-worker-visa. Certificate of Sponsorship from UK employer, minimum salary threshold, English language requirement.",
        "student": "Student Visa. Reference: gov.uk/student-visa. CAS from licensed sponsor, financial requirement, ATAS certificate for certain courses."
    },
    "new_zealand": {
        "visitor": "Visitor Visa. Reference: immigration.govt.nz. NZeTA for visa-waiver countries, proof of funds ($1000/month or $400 with accommodation), return ticket.",
        "pr": "Skilled Migrant Category Resident Visa. Reference: immigration.govt.nz. EOI system, points-based, job offer from accredited employer, skills assessment.",
        "work": "Essential Skills Work Visa. Reference: immigration.govt.nz. Job offer, labour market test, ANZSCO skill level assessment."
    },
    "usa": {
        "visitor": "B-1/B-2 Visitor Visa. Reference: travel.state.gov, ustraveldocs.com. DS-160 form, consular interview, proof of ties to home country, I-94 arrival record.",
        "student": "F-1 Student Visa. Reference: studyinthestates.dhs.gov. I-20 form from SEVP-certified school, SEVIS fee, financial proof, consular interview.",
        "work": "H-1B Specialty Occupation Visa. Reference: uscis.gov. Employer petition, USCIS lottery, LCA from DOL, bachelor's degree minimum."
    },
    "singapore": {
        "visitor": "Tourist Visa / Visa-Free Entry. Reference: ica.gov.sg. SG Arrival Card, proof of funds, return ticket, hotel booking. Most countries 30-90 days visa-free.",
        "work": "Employment Pass (EP). Reference: mom.gov.sg. Job offer from Singapore employer, minimum salary requirement, COMPASS framework, educational qualifications."
    },
    "dubai": {
        "visitor": "UAE Tourist Visa. Reference: icp.gov.ae, gdrfad.gov.ae. 30/60/90 day options, hotel/sponsor required, Emirates ID for longer stays. VFS Global processing available.",
        "work": "UAE Employment Visa. Reference: mohre.gov.ae. Employer sponsorship, medical fitness test, Emirates ID, labor contract approval.",
        "golden": "UAE Golden Visa (10-year). Reference: icp.gov.ae. For investors, entrepreneurs, specialized talents, outstanding students. Property investment route available."
    }
}


async def _call_gpt(prompt: str, system_msg: str = "") -> str:
    """Call GPT-5.2 via emergentintegrations"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"workflow-builder-{uuid.uuid4().hex[:8]}",
            system_message=system_msg
        )
        return await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.get("/countries")
async def get_supported_countries(current_user: dict = Depends(get_current_user)):
    """Get list of supported countries and service types"""
    countries = []
    for country, services in COUNTRY_REFERENCES.items():
        countries.append({
            "id": country,
            "name": country.replace("_", " ").title(),
            "services": [{"id": svc, "name": svc.upper().replace("_", " ")} for svc in services.keys()]
        })
    return countries


@router.post("/generate")
async def generate_workflow(
    request: WorkflowGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a complete immigration workflow using AI"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    country_key = request.country.lower().replace(" ", "_")
    service_key = request.service_type.lower().replace(" ", "_")
    
    ref_info = ""
    if country_key in COUNTRY_REFERENCES:
        ref_info = COUNTRY_REFERENCES[country_key].get(service_key, "")
        if not ref_info:
            for k, v in COUNTRY_REFERENCES[country_key].items():
                ref_info += f"\n{k}: {v}"
    
    system_msg = """You are an expert immigration consultant AI with deep knowledge of global immigration processes. 
You generate accurate, step-by-step immigration workflows based on official government requirements.
You must return ONLY valid JSON, no markdown, no extra text.
Your workflows must be practical, actionable, and based on real immigration processes."""

    prompt = f"""Generate a detailed immigration workflow for: {request.country} - {request.service_type}

Official Reference Information:
{ref_info}

{f"Additional Instructions: {request.custom_instructions}" if request.custom_instructions else ""}

Return a JSON object with this EXACT structure:
{{
  "product_name": "Country - Service Type (e.g., Canada PR - Express Entry)",
  "description": "Brief description of this immigration pathway",
  "category": "immigration",
  "estimated_total_duration_days": 180,
  "estimated_government_fees": "approximate fees in local currency",
  "success_tips": ["tip1", "tip2", "tip3"],
  "common_rejection_reasons": ["reason1", "reason2"],
  "steps": [
    {{
      "step_name": "Step Name",
      "step_order": 1,
      "description": "Detailed description of what happens in this step",
      "duration_days": 30,
      "required_documents": [
        {{
          "name": "Document Name",
          "description": "What this document is and how to get it",
          "mandatory": true,
          "typical_validity_days": 365
        }}
      ],
      "important_notes": "Any critical information for this step",
      "government_fees": "Fees specific to this step if any"
    }}
  ]
}}

Include ALL steps from initial preparation to final visa/PR approval. Be thorough and accurate.
Each step should have specific required documents with descriptions.
Include realistic duration estimates and government fees where applicable."""

    response = await _call_gpt(prompt, system_msg)
    
    # Parse JSON from response
    try:
        # Try to extract JSON from response
        json_str = response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        
        workflow_data = json.loads(json_str.strip())
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                workflow_data = json.loads(response[start:end])
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="AI returned invalid workflow format. Please try again.")
        else:
            raise HTTPException(status_code=500, detail="AI returned invalid workflow format. Please try again.")
    
    await log_activity(current_user["id"], current_user["name"], "generated_workflow", "ai_workflow",
                       details=f"Generated workflow for {request.country} - {request.service_type}")
    
    return workflow_data


@router.post("/save")
async def save_workflow_as_product(
    request: WorkflowSaveRequest,
    current_user: dict = Depends(get_current_user)
):
    """Save an AI-generated workflow as a new product"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    product = {
        "id": str(uuid.uuid4()),
        "name": request.product_name,
        "description": request.description,
        "category": request.category or "immigration",
        "base_fee": request.base_fee,
        "commission_rate": request.commission_rate,
        "commission_type": "percentage",
        "status": "active",
        "ai_generated": True,
        "created_at": datetime.now(timezone.utc)
    }
    await products_col.insert_one(product)
    
    saved_steps = []
    for step_data in request.steps:
        step = {
            "id": str(uuid.uuid4()),
            "product_id": product["id"],
            "step_name": step_data.get("step_name", ""),
            "step_order": step_data.get("step_order", 0),
            "description": step_data.get("description", ""),
            "duration_days": step_data.get("duration_days", 7),
            "required_documents": step_data.get("required_documents", []),
            "important_notes": step_data.get("important_notes", ""),
            "government_fees": step_data.get("government_fees", "")
        }
        await workflow_steps_col.insert_one(step)
        saved_steps.append({"id": step["id"], "step_name": step["step_name"]})
    
    await log_activity(current_user["id"], current_user["name"], "saved_ai_workflow", "product",
                       product["id"], f"Saved AI workflow as product: {request.product_name} with {len(saved_steps)} steps")
    
    return {
        "product_id": product["id"],
        "product_name": request.product_name,
        "steps_created": len(saved_steps),
        "message": "Workflow saved as product successfully"
    }


@router.get("/templates")
async def get_workflow_templates(current_user: dict = Depends(get_current_user)):
    """Get quick-access templates for common immigration workflows"""
    templates = [
        {"id": "canada_pr", "country": "Canada", "service": "PR", "label": "Canada PR - Express Entry", "icon": "maple-leaf"},
        {"id": "australia_pr", "country": "Australia", "service": "PR", "label": "Australia PR - Skilled Migration", "icon": "kangaroo"},
        {"id": "canada_visitor", "country": "Canada", "service": "Visitor", "label": "Canada Tourist/Visitor Visa", "icon": "plane"},
        {"id": "australia_visitor", "country": "Australia", "service": "Visitor", "label": "Australia Tourist Visa", "icon": "plane"},
        {"id": "uk_visitor", "country": "UK", "service": "Visitor", "label": "UK Standard Visitor Visa", "icon": "plane"},
        {"id": "nz_visitor", "country": "New Zealand", "service": "Visitor", "label": "New Zealand Visitor Visa", "icon": "plane"},
        {"id": "usa_visitor", "country": "USA", "service": "Visitor", "label": "USA B1/B2 Visitor Visa", "icon": "plane"},
        {"id": "singapore_visitor", "country": "Singapore", "service": "Visitor", "label": "Singapore Tourist Visa", "icon": "plane"},
        {"id": "dubai_visitor", "country": "Dubai", "service": "Visitor", "label": "UAE Tourist Visa", "icon": "plane"},
        {"id": "dubai_golden", "country": "Dubai", "service": "Golden", "label": "UAE Golden Visa (10-Year)", "icon": "star"},
    ]
    return templates
