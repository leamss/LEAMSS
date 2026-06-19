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
        "student": "Study Permit. Reference: ircc.canada.ca. DLI acceptance letter, GIC proof, language scores, SDS stream.",
        "work": "LMIA-based Work Permit / PGWP / IEC Working Holiday. Reference: ircc.canada.ca. Employer LMIA, job offer, labour market impact assessment."
    },
    "australia": {
        "pr": "Department of Home Affairs - Skilled Migration (Subclass 189/190/491). Reference: homeaffairs.gov.au. SkillSelect EOI, skills assessment, points test.",
        "visitor": "Visitor Visa Subclass 600. Reference: homeaffairs.gov.au. Tourist/business/sponsored family streams.",
        "student": "Student Visa Subclass 500. Reference: homeaffairs.gov.au. CoE, GTE, OSHC, financial capacity.",
        "work": "Temporary Skill Shortage Subclass 482. Reference: homeaffairs.gov.au. Employer nomination, skills assessment.",
        "partner": "Partner Visa Subclass 820/801. Reference: homeaffairs.gov.au. Relationship evidence, sponsor approval."
    },
    "uk": {
        "visitor": "Standard Visitor Visa. Reference: gov.uk.",
        "work": "Skilled Worker Visa. Reference: gov.uk. CoS from licensed employer, minimum salary, English requirement.",
        "student": "Student Visa. Reference: gov.uk. CAS from licensed sponsor, financial requirement.",
        "family": "Family Visa. Reference: gov.uk. Spouse/partner/parent route, financial requirement £18,600+."
    },
    "new_zealand": {
        "visitor": "Visitor Visa. Reference: immigration.govt.nz.",
        "pr": "Skilled Migrant Category. Reference: immigration.govt.nz. EOI, points-based.",
        "work": "Essential Skills Work Visa. Reference: immigration.govt.nz.",
        "student": "Fee Paying Student Visa. Reference: immigration.govt.nz."
    },
    "usa": {
        "visitor": "B-1/B-2 Visitor Visa. Reference: travel.state.gov.",
        "student": "F-1 Student Visa. Reference: studyinthestates.dhs.gov.",
        "work": "H-1B Specialty Occupation. Reference: uscis.gov.",
        "immigrant": "EB-1/EB-2/EB-3 Employment-Based Green Card. Reference: uscis.gov.",
        "family": "Family-Based Immigration. Reference: uscis.gov."
    },
    "singapore": {
        "visitor": "Tourist Visa. Reference: ica.gov.sg.",
        "work": "Employment Pass (EP). Reference: mom.gov.sg. COMPASS framework.",
        "student": "Student Pass. Reference: ica.gov.sg.",
        "pr": "Singapore PR. Reference: ica.gov.sg."
    },
    "uae": {
        "visitor": "UAE Tourist Visa. Reference: icp.gov.ae.",
        "work": "UAE Employment Visa. Reference: mohre.gov.ae.",
        "golden": "UAE Golden Visa (10-year). Reference: icp.gov.ae.",
        "student": "UAE Student Visa. Reference: icp.gov.ae."
    },
    "germany": {
        "work": "EU Blue Card / Work Visa. Reference: make-it-in-germany.com, auswaertiges-amt.de.",
        "student": "Student Visa. Reference: auswaertiges-amt.de.",
        "jobseeker": "Job Seeker Visa. Reference: auswaertiges-amt.de."
    },
    "japan": {
        "work": "Work Visa (Engineer/Specialist/Humanities). Reference: mofa.go.jp, moj.go.jp.",
        "student": "Student Visa (College of Japanese Language). Reference: mofa.go.jp.",
        "pr": "Highly Skilled Professional Visa. Reference: moj.go.jp."
    },
    "south_korea": {
        "work": "E-7 Special Occupation Visa. Reference: visa.go.kr.",
        "student": "D-2 Student Visa. Reference: visa.go.kr.",
        "visitor": "Tourist Visa. Reference: visa.go.kr."
    },
    "ireland": {
        "work": "Critical Skills Employment Permit. Reference: enterprise.gov.ie.",
        "student": "Study Visa / Stamp 2. Reference: irishimmigration.ie.",
        "visitor": "Tourist Visa. Reference: irishimmigration.ie."
    },
    "france": {
        "work": "Talent Passport / Work Visa. Reference: france-visas.gouv.fr.",
        "student": "Student Visa (VLS-TS). Reference: france-visas.gouv.fr, campusfrance.org.",
        "visitor": "Short-stay Schengen Visa. Reference: france-visas.gouv.fr."
    },
    "netherlands": {
        "work": "Highly Skilled Migrant (Kennismigrant). Reference: ind.nl.",
        "student": "Student Visa MVV + Residence Permit. Reference: ind.nl.",
        "startup": "Startup Visa. Reference: ind.nl."
    },
    "sweden": {
        "work": "Work Permit. Reference: migrationsverket.se.",
        "student": "Residence Permit for Studies. Reference: migrationsverket.se.",
        "pr": "Permanent Residence. Reference: migrationsverket.se."
    },
    "switzerland": {
        "work": "L/B Work Permit. Reference: sem.admin.ch.",
        "student": "Student Visa. Reference: sem.admin.ch.",
        "visitor": "Schengen Visa. Reference: sem.admin.ch."
    },
    "hong_kong": {
        "work": "Employment Visa. Reference: immd.gov.hk.",
        "talent": "Quality Migrant Admission Scheme (QMAS). Reference: immd.gov.hk.",
        "student": "Student Visa. Reference: immd.gov.hk."
    },
    "malaysia": {
        "work": "Employment Pass (Category I/II/III). Reference: esd.imi.gov.my.",
        "mm2h": "Malaysia My Second Home (MM2H). Reference: mm2h.gov.my.",
        "student": "Student Pass. Reference: esd.imi.gov.my."
    },
    "thailand": {
        "work": "Non-Immigrant B Visa + Work Permit. Reference: mfa.go.th.",
        "elite": "Thailand Elite Visa (5-20 years). Reference: thailandelite.com.",
        "retirement": "Non-Immigrant O-A (Retirement). Reference: mfa.go.th."
    },
    "portugal": {
        "work": "Work Visa / Tech Visa. Reference: sef.pt, vfsvisaonline.com.",
        "d7": "D7 Passive Income Visa. Reference: sef.pt.",
        "golden": "Golden Visa (Investment). Reference: sef.pt.",
        "student": "Student Visa. Reference: sef.pt."
    },
    "spain": {
        "work": "Work Visa / Highly Qualified Professional. Reference: exteriores.gob.es.",
        "nomad": "Digital Nomad Visa. Reference: exteriores.gob.es.",
        "student": "Student Visa. Reference: exteriores.gob.es.",
        "golden": "Golden Visa (Investment). Reference: exteriores.gob.es."
    },
    "italy": {
        "work": "Work Visa (Nulla Osta). Reference: esteri.it.",
        "student": "Student Visa. Reference: esteri.it.",
        "elective": "Elective Residence Visa. Reference: esteri.it."
    },
    "south_africa": {
        "work": "Critical Skills Work Visa. Reference: dha.gov.za.",
        "general_work": "General Work Visa. Reference: dha.gov.za.",
        "study": "Study Visa. Reference: dha.gov.za."
    },
    "brazil": {
        "work": "VITEM V Work Visa. Reference: gov.br/mre.",
        "investor": "Investor Visa (VIPER). Reference: gov.br/mre.",
        "digital_nomad": "Digital Nomad Visa. Reference: gov.br/mre."
    },
    "mexico": {
        "work": "Temporary Resident Visa (Work). Reference: gob.mx/inm.",
        "visitor": "Tourist Visa. Reference: gob.mx/sre.",
        "pr": "Permanent Resident Visa. Reference: gob.mx/inm."
    },
    "india": {
        "work": "Employment Visa. Reference: indianvisaonline.gov.in.",
        "business": "Business Visa. Reference: indianvisaonline.gov.in.",
        "student": "Student Visa. Reference: indianvisaonline.gov.in.",
        "oci": "Overseas Citizen of India (OCI) Card. Reference: indianvisaonline.gov.in."
    },
    "china": {
        "work": "Z Visa (Work Permit). Reference: visaforchina.cn.",
        "student": "X1/X2 Student Visa. Reference: visaforchina.cn.",
        "business": "M Visa (Business). Reference: visaforchina.cn."
    },
    "qatar": {
        "work": "Work Visa / Residence Permit. Reference: moi.gov.qa.",
        "visitor": "Tourist Visa / Hayya. Reference: visitqatar.qa.",
        "family": "Family Residence Visa. Reference: moi.gov.qa."
    },
    "saudi_arabia": {
        "work": "Work Visa / Iqama. Reference: visa.visitsaudi.com, mol.gov.sa.",
        "visit": "Tourist / Visit Visa. Reference: visa.visitsaudi.com.",
        "premium": "Premium Residency (Green Card). Reference: saprc.gov.sa."
    },
    "bahrain": {
        "work": "Work Visa. Reference: lmra.bh.",
        "golden": "Golden Residence Visa. Reference: npra.gov.bh.",
        "visitor": "eVisa. Reference: evisa.gov.bh."
    },
    "oman": {
        "work": "Employment Visa. Reference: rop.gov.om.",
        "investor": "Investor Residence. Reference: rop.gov.om.",
        "visitor": "Tourist eVisa. Reference: evisa.rop.gov.om."
    },
    "denmark": {
        "work": "Pay Limit Scheme / Fast-Track. Reference: nyidanmark.dk.",
        "student": "Residence Permit for Study. Reference: nyidanmark.dk.",
        "startup": "Startup Denmark. Reference: startupdenmark.info."
    },
    "norway": {
        "work": "Skilled Worker Permit. Reference: udi.no.",
        "student": "Student Permit. Reference: udi.no.",
        "family": "Family Immigration. Reference: udi.no."
    },
    "finland": {
        "work": "Residence Permit for Employed Person. Reference: migri.fi.",
        "startup": "Startup Residence Permit. Reference: migri.fi.",
        "student": "Student Residence Permit. Reference: migri.fi."
    },
    "austria": {
        "work": "Red-White-Red Card. Reference: migration.gv.at.",
        "student": "Student Visa. Reference: migration.gv.at.",
        "eu_blue": "EU Blue Card Austria. Reference: migration.gv.at."
    },
    "belgium": {
        "work": "Single Permit / Work Permit B. Reference: dofi.ibz.be.",
        "student": "Student Visa. Reference: dofi.ibz.be."
    },
    "poland": {
        "work": "Work Permit / Temporary Residence. Reference: udsc.gov.pl.",
        "student": "Student Visa. Reference: udsc.gov.pl.",
        "pr": "Permanent Residence. Reference: udsc.gov.pl."
    },
    "czech_republic": {
        "work": "Employee Card / Blue Card. Reference: mvcr.cz.",
        "student": "Long-term Visa for Study. Reference: mvcr.cz."
    },
    "greece": {
        "golden": "Golden Visa (Property Investment). Reference: enterprise.gov.gr.",
        "work": "Work Visa. Reference: migration.gov.gr.",
        "nomad": "Digital Nomad Visa. Reference: migration.gov.gr."
    },
    "turkey": {
        "work": "Work Permit. Reference: csgb.gov.tr.",
        "turkuaz": "Turquoise Card (Highly Qualified). Reference: goc.gov.tr.",
        "investor": "Investor / Citizenship by Investment. Reference: goc.gov.tr."
    },
    "philippines": {
        "work": "9(g) Work Visa / AEP. Reference: immigration.gov.ph.",
        "retirement": "SRRV (Special Resident Retiree's Visa). Reference: pra.gov.ph.",
        "student": "Student Visa 9(f). Reference: immigration.gov.ph."
    },
    "indonesia": {
        "work": "ITAS Work Permit (KITAS). Reference: imigrasi.go.id.",
        "investor": "Investor KITAS. Reference: imigrasi.go.id.",
        "retirement": "Retirement ITAS. Reference: imigrasi.go.id."
    },
    "vietnam": {
        "work": "Work Permit + TRC. Reference: xuatnhapcanh.gov.vn.",
        "investor": "Investor Visa. Reference: xuatnhapcanh.gov.vn.",
        "student": "Student Visa. Reference: xuatnhapcanh.gov.vn."
    },
    "colombia": {
        "work": "M Visa (Work). Reference: cancilleria.gov.co.",
        "nomad": "Digital Nomad Visa (V Type). Reference: cancilleria.gov.co.",
        "investor": "Investor Visa. Reference: cancilleria.gov.co."
    },
    "chile": {
        "work": "Temporary Residence (Work). Reference: extranjeria.gob.cl.",
        "pr": "Permanent Residence. Reference: extranjeria.gob.cl."
    },
    "argentina": {
        "work": "Temporary Residence (Work). Reference: migraciones.gov.ar.",
        "nomad": "Digital Nomad Visa. Reference: migraciones.gov.ar."
    },
    "kenya": {
        "work": "Work Permit (Class D/G). Reference: fns.immigration.go.ke.",
        "investor": "Investor Permit (Class G). Reference: fns.immigration.go.ke."
    },
    "nigeria": {
        "work": "Subject to Regularization (STR) / TWP. Reference: immigration.gov.ng.",
        "business": "Business Visa. Reference: immigration.gov.ng."
    },
    "egypt": {
        "work": "Work Visa. Reference: visa2egypt.gov.eg.",
        "visitor": "Tourist Visa. Reference: visa2egypt.gov.eg."
    },
    "mauritius": {
        "work": "Occupation Permit. Reference: edbmauritius.org.",
        "premium": "Premium Visa (Remote Work). Reference: edbmauritius.org."
    },
    "panama": {
        "work": "Work Permit. Reference: migracion.gob.pa.",
        "friendly": "Friendly Nations Visa. Reference: migracion.gob.pa."
    },
    "costa_rica": {
        "work": "Work Permit. Reference: migracion.go.cr.",
        "nomad": "Digital Nomad Visa. Reference: migracion.go.cr.",
        "rentista": "Rentista (Passive Income). Reference: migracion.go.cr."
    },
}


class VisaCategoriesRequest(BaseModel):
    country: str


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
    """Get list of all supported countries with their service types"""
    countries = []
    for country, services in COUNTRY_REFERENCES.items():
        countries.append({
            "id": country,
            "name": country.replace("_", " ").title(),
            "services": [{"id": svc, "name": svc.upper().replace("_", " ")} for svc in services.keys()]
        })
    # Sort alphabetically
    countries.sort(key=lambda x: x["name"])
    return countries


@router.post("/visa-categories")
async def get_visa_categories(data: VisaCategoriesRequest, current_user: dict = Depends(get_current_user)):
    """Get all visa subclasses/categories for a country - uses hardcoded data first, AI as optional enrichment"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    country_key = data.country.lower().replace(" ", "_")
    
    # Build categories from COUNTRY_REFERENCES (no AI needed)
    categories = []
    if country_key in COUNTRY_REFERENCES:
        for svc_key, ref_info in COUNTRY_REFERENCES[country_key].items():
            # Extract URL from reference info
            url = ""
            for part in ref_info.split(". "):
                if "Reference:" in part:
                    url_part = part.replace("Reference:", "").strip().rstrip(".")
                    if url_part and not url_part.startswith("http"):
                        url = f"https://{url_part}"
                    elif url_part.startswith("http"):
                        url = url_part
                    break
            
            categories.append({
                "id": f"{country_key}_{svc_key}",
                "name": svc_key.replace("_", " ").title(),
                "description": ref_info.split(". ")[0] if ". " in ref_info else ref_info,
                "category": svc_key,
                "official_url": url,
                "estimated_fees": "",
                "reference": ref_info,
            })

    # Try AI enrichment (optional - won't fail if budget exceeded)
    try:
        example = '[{"id":"subclass_189","name":"Subclass 189 - Skilled Independent","description":"Points-based visa for skilled workers","category":"skilled_migration","official_url":"https://homeaffairs.gov.au/...","estimated_fees":"AUD $4,910"}]'
        prompt = (
            f'List ALL visa categories and subclasses for {data.country} with subclass numbers where applicable. '
            f'Include official government page URLs and current application fees. '
            f'Return ONLY a JSON array. Example: {example}'
        )
        system_msg = "Immigration visa expert. List ALL visa subclasses with official URLs and fees. Return ONLY valid JSON."
        response = await _call_gpt(prompt, system_msg)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            cleaned = cleaned.rsplit("```", 1)[0]
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start >= 0 and end > start:
            ai_cats = json.loads(cleaned[start:end])
            if isinstance(ai_cats, list) and len(ai_cats) > 0:
                categories = ai_cats  # AI gave better data, use it
    except Exception:
        pass  # AI failed (budget, timeout etc) - use hardcoded data

    return {"country": data.country, "categories": categories}


@router.post("/generate")
async def generate_workflow(
    request: WorkflowGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a complete immigration workflow using AI (Phase 20.1).

    Wires Claude Sonnet 4.5 primary with GPT-5.2 silent fallback.
    Enforces quality bar (≥5 steps, ≥3 docs per step) with auto-retry.
    Injects VFSglobal URL + AU/NZ skill-assessment authority URL into context.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    from services import ai_workflow_service as ai_svc

    country_key = request.country.lower().replace(" ", "_")
    service_key = request.service_type.lower().replace(" ", "_")

    ref_info = ""
    if country_key in COUNTRY_REFERENCES:
        ref_info = COUNTRY_REFERENCES[country_key].get(service_key, "")
        if not ref_info:
            for k, v in COUNTRY_REFERENCES[country_key].items():
                ref_info += f"\n{k}: {v}"

    # Verified template context (for richer prompts)
    from routers.step_documents import _find_best_template
    template = _find_best_template(f"{request.country} {request.service_type}")
    template_context = ""
    if template:
        template_context = f"\nVerified template reference ({template.get('label','')}):\n"
        template_context += f"Fees: {template.get('fees_info','')}\n"
        template_context += f"Assessment bodies: {', '.join(template.get('assessment_bodies', []))}\n"
        for step_name, docs in template.get("steps", {}).items():
            doc_names = [d["doc_name"] for d in docs]
            template_context += f"Step '{step_name}': {', '.join(doc_names)}\n"

    # Phase 20.1 — VFSglobal + AU/NZ skill assessment URLs
    vfs_url = ai_svc.vfsglobal_url(country_key)
    sa_url = await ai_svc.resolve_au_nz_skill_assessment_url(db, country_key, service_key)
    enrichment_block = ai_svc.build_enrichment_context(
        country_key, service_key, ref_info, vfs_url, sa_url, template_context,
    )

    system_msg = (
        "You are an expert immigration consultant AI with deep knowledge of global immigration processes. "
        "You generate accurate, step-by-step immigration workflows based on OFFICIAL government requirements "
        "and VFSglobal application centre procedures (for Indian applicants). "
        "You must return ONLY valid JSON, no markdown, no extra text. "
        "Every step MUST have at least 3 required documents. Include all documents that an applicant would need."
    )

    base_prompt = f"""Generate a COMPREHENSIVE immigration workflow for: {request.country} - {request.service_type}

{enrichment_block}
{f"Additional Instructions: {request.custom_instructions}" if request.custom_instructions else ""}

CRITICAL RULES:
1. At least 5 steps. Every step MUST have at least 3 required_documents.
2. Include specific document names as used by the government (e.g., "Form 80 - Personal Particulars")
3. Include ALL fees in local currency based on current official government fee schedules
4. Reference only official government websites (.gov / official portals) AND VFSglobal for application submission step
5. Be thorough — passport, photos, police clearances, medical exams, financial evidence, biometrics, etc.
6. For AU/NZ PR ONLY: include "Skills Assessment" as first or second step (mandatory). For all OTHER workflows, DO NOT include a skills assessment step.

Return a JSON object with this EXACT structure:
{{
  "product_name": "Country - Visa Type with Subclass Number",
  "description": "Brief description of this immigration pathway",
  "category": "immigration",
  "estimated_total_duration_days": 180,
  "estimated_government_fees": "Complete fee breakdown in local currency (application fee + biometrics + medical + skills assessment + language test)",
  "success_tips": ["tip1", "tip2", "tip3"],
  "common_rejection_reasons": ["reason1", "reason2"],
  "steps": [
    {{
      "step_name": "Step Name",
      "step_order": 1,
      "description": "Detailed description of what happens in this step",
      "duration_days": 30,
      "official_source_url": "https://...gov... (specific page URL)",
      "vfsglobal_url": "https://visa.vfsglobal.com/... (if applicable to this step)",
      "required_documents": [
        {{
          "name": "Official Document Name",
          "description": "What this document is, where to get it, and any specific requirements",
          "mandatory": true,
          "typical_validity_days": 365
        }}
      ],
      "important_notes": "Critical information for this step",
      "government_fees": "Specific fees for this step in local currency"
    }}
  ]
}}

Include 5-8 steps covering: preparation, assessment/testing, application submission, documentation, biometrics/medical, processing, and grant.
EVERY step must have 3-6 required_documents with detailed descriptions."""

    workflow_data: dict = None
    model_used = "unknown"
    last_quality_issues: List[str] = []

    # Try up to MAX_QUALITY_RETRIES (Claude → GPT → stricter retry)
    prompt = base_prompt
    for attempt in range(ai_svc.MAX_QUALITY_RETRIES + 1):
        try:
            response, model_used = await ai_svc.call_ai_with_fallback(prompt, system_msg)
            workflow_data = ai_svc.parse_json_response(response)
        except Exception as e:  # noqa: BLE001
            # Both providers failed OR JSON unparseable
            workflow_data = None
            last_err = str(e)[:200]
            await log_activity(current_user["id"], current_user.get("name", ""), "workflow_generate_failed",
                               "ai_workflow",
                               details=f"{request.country}-{request.service_type} · attempt {attempt+1} · {last_err}")
            break  # Don't retry on hard failure — exit to template fallback

        # Quality bar check
        passed, issues = ai_svc.validate_workflow_quality(workflow_data)
        if passed:
            break  # ✅ Good output
        last_quality_issues = issues
        if attempt < ai_svc.MAX_QUALITY_RETRIES:
            prompt = ai_svc.build_stricter_retry_prompt(base_prompt, issues)
            await log_activity(current_user["id"], current_user.get("name", ""), "workflow_retry_quality",
                               "ai_workflow",
                               details=f"{request.country}-{request.service_type} · attempt {attempt+1} · issues={len(issues)}")

    # If still no workflow → template fallback
    if not workflow_data and template:
        steps = []
        for i, (step_name, docs) in enumerate(template.get("steps", {}).items(), 1):
            steps.append({
                "step_name": step_name, "step_order": i, "description": "", "duration_days": 14,
                "required_documents": [
                    {"name": d["doc_name"], "description": d.get("description", ""),
                     "mandatory": d.get("is_mandatory", True)} for d in docs],
                "important_notes": "", "government_fees": "",
                "official_source_url": "", "vfsglobal_url": vfs_url or "",
            })
        workflow_data = {
            "product_name": f"{request.country} - {request.service_type}",
            "description": template.get("label", ""),
            "category": "immigration",
            "estimated_government_fees": template.get("fees_info", ""),
            "steps": steps, "success_tips": [], "common_rejection_reasons": [],
            "_degraded_mode": "template_fallback",
        }
        model_used = "template_fallback"
    elif not workflow_data:
        raise HTTPException(
            status_code=503,
            detail="AI workflow generation temporarily unavailable. No verified template exists for this country/visa combo. Please try a different category or retry in a minute.",
        )

    # Phase 20.1 — attach metadata for audit
    workflow_data["_meta"] = {
        "model_used": model_used,
        "country_key": country_key,
        "service_key": service_key,
        "vfsglobal_url": vfs_url,
        "skill_assessment_url": sa_url,
        "is_skill_assessment_required": (country_key in ("australia", "new_zealand") and service_key == "pr"),
        "quality_issues": last_quality_issues,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": current_user.get("id"),
    }

    await log_activity(current_user["id"], current_user.get("name", ""), "generated_workflow", "ai_workflow",
                       details=f"{request.country}-{request.service_type} via {model_used} · {len(workflow_data.get('steps', []))} steps")
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
    # Phase 20.1 — merge any admin-verified DB workflow templates
    verified_db = db["ai_workflow_templates"]
    async for t in verified_db.find({"verified": True}, {"_id": 0,
                                                          "id": 1, "country": 1, "service": 1,
                                                          "label": 1, "icon": 1, "model_used": 1,
                                                          "verified_by": 1, "verified_at": 1}):
        templates.append({**t, "source": "db_verified"})
    return templates


# ── Phase 20.1 — Verify endpoint (admin-only persistence) ────────────────────
class VerifyRequest(BaseModel):
    workflow_payload: dict
    country: str
    service_type: str
    notes: Optional[str] = ""


@router.post("/verify")
async def verify_workflow(
    request: VerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Persist an admin-verified AI workflow into `ai_workflow_templates` collection.

    The frontend calls this after the admin ticks "I have verified this information".
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    country_key = (request.country or "").lower().replace(" ", "_")
    service_key = (request.service_type or "").lower().replace(" ", "_")
    if not country_key or not service_key:
        raise HTTPException(status_code=400, detail="country and service_type required")

    meta = (request.workflow_payload or {}).get("_meta", {})
    template_id = f"{country_key}_{service_key}_verified"
    label = f"{request.country} - {request.service_type} (Verified)"

    doc = {
        "id": template_id,
        "country": request.country,
        "country_key": country_key,
        "service": request.service_type,
        "service_key": service_key,
        "label": label,
        "icon": "shield-check",
        "verified": True,
        "verified_by": current_user.get("id"),
        "verified_by_name": current_user.get("name") or current_user.get("email"),
        "verified_at": datetime.now(timezone.utc),
        "model_used": meta.get("model_used", "unknown"),
        "vfsglobal_url": meta.get("vfsglobal_url"),
        "skill_assessment_url": meta.get("skill_assessment_url"),
        "is_skill_assessment_required": meta.get("is_skill_assessment_required", False),
        "workflow_payload": request.workflow_payload,
        "notes": request.notes or "",
        "updated_at": datetime.now(timezone.utc),
    }
    await db["ai_workflow_templates"].update_one(
        {"id": template_id},
        {"$set": doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    await log_activity(current_user["id"], current_user.get("name", ""), "verified_workflow",
                       "ai_workflow_template", template_id,
                       f"Verified {request.country} - {request.service_type} (model: {meta.get('model_used', 'unknown')})")
    return {"ok": True, "id": template_id, "label": label,
            "verified_at": doc["verified_at"].isoformat()}


@router.get("/verified-templates")
async def list_verified_templates(current_user: dict = Depends(get_current_user)):
    """Phase 20.1 — list all admin-verified workflow templates in DB."""
    out = []
    async for t in db["ai_workflow_templates"].find({"verified": True}, {"_id": 0}):
        for k in ("verified_at", "created_at", "updated_at"):
            if hasattr(t.get(k), "isoformat"):
                t[k] = t[k].isoformat()
        out.append(t)
    return {"items": out, "count": len(out)}

