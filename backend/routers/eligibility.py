"""AI Eligibility Pre-Score — public endpoint that scores visa pathways.

A prospective client fills a quick form (90s) → backend uses Claude Sonnet 4.6 to
score 8-10 visa pathways and returns ranked recommendations.

Public (no auth) endpoint to maximize lead generation reach.
"""
import os
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from core.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/eligibility", tags=["Eligibility Pre-Score"])

scores_col = db["eligibility_scores"]
leads_col = db["leads"]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

SYSTEM_PROMPT = (
    "You are a senior immigration consultant scoring a prospective client's eligibility "
    "across multiple visa pathways. You MUST respond with VALID JSON ONLY (no markdown, no prose). "
    "Be honest, conservative, and never inflate eligibility scores. Use Indian English conventions. "
    "Score 8 specific pathways listed by the user. For each, output:\n"
    "  - score: integer 0-100 (eligibility likelihood)\n"
    "  - tier: one of 'strong' (75-100), 'moderate' (50-74), 'weak' (25-49), 'unlikely' (0-24)\n"
    "  - estimated_timeline: realistic months range (e.g. '8-14 months')\n"
    "  - key_strengths: array of 1-3 short bullet phrases\n"
    "  - gaps_to_fix: array of 1-3 short bullet phrases (what to improve)\n"
    "  - notes: 1-2 sentence pathway-specific advice\n"
    "Also include a top-level field 'top_recommendation' = the pathway slug with highest score "
    "and 'overall_summary' = a 2-sentence honest assessment."
)

PATHWAYS = [
    {"slug": "canada_express_entry", "name": "Canada · Express Entry (Federal Skilled Worker)"},
    {"slug": "canada_pnp", "name": "Canada · Provincial Nominee Program"},
    {"slug": "australia_189", "name": "Australia · Subclass 189 (Skilled Independent)"},
    {"slug": "australia_190", "name": "Australia · Subclass 190 (State Nominated)"},
    {"slug": "uk_skilled_worker", "name": "UK · Skilled Worker Visa"},
    {"slug": "germany_eu_blue_card", "name": "Germany · EU Blue Card"},
    {"slug": "usa_eb2_niw", "name": "USA · EB2-NIW (National Interest Waiver)"},
    {"slug": "new_zealand_swv", "name": "New Zealand · Skilled Migrant Category"},
]


class EligibilityRequest(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    age: int = Field(..., ge=18, le=70)
    education: str  # "Bachelor", "Master", "PhD", "Diploma"
    work_experience_years: float = Field(..., ge=0, le=50)
    occupation: str
    english_score: Optional[str] = None  # "IELTS 7.0", "PTE 65", "None"
    family_savings_inr: Optional[float] = None
    has_job_offer: bool = False
    spouse_education: Optional[str] = None
    children_count: int = 0
    preferred_countries: Optional[List[str]] = None
    consent_to_contact: bool = False


@router.get("/pathways")
async def list_pathways():
    """Public — list of pathways scored by the engine."""
    return {"pathways": PATHWAYS}


@router.post("/score")
async def score_eligibility(data: EligibilityRequest):
    """Public — score a candidate across all pathways and persist a lead if consent given."""
    profile_summary = (
        f"Candidate profile:\n"
        f"- Age: {data.age}\n"
        f"- Education: {data.education}\n"
        f"- Work experience: {data.work_experience_years} years\n"
        f"- Occupation: {data.occupation}\n"
        f"- English score: {data.english_score or 'Not taken yet'}\n"
        f"- Job offer abroad: {'Yes' if data.has_job_offer else 'No'}\n"
        + (f"- Family savings: ₹{data.family_savings_inr:,.0f}" if data.family_savings_inr else "- Family savings: Not disclosed")
        + (f"\n- Spouse education: {data.spouse_education}" if data.spouse_education else "")
        + (f"\n- Dependent children: {data.children_count}" if data.children_count else "")
        + (f"\n- Preferred countries: {', '.join(data.preferred_countries)}" if data.preferred_countries else "")
    )

    pathway_list = "\n".join([f"  - {p['slug']}: {p['name']}" for p in PATHWAYS])
    user_prompt = (
        f"{profile_summary}\n\n"
        f"Score this candidate against EXACTLY these 8 pathways:\n{pathway_list}\n\n"
        f'Output JSON: {{"top_recommendation": "<slug>", "overall_summary": "...", '
        f'"pathways": {{"<slug>": {{"score": int, "tier": "strong|moderate|weak|unlikely", '
        f'"estimated_timeline": "...", "key_strengths": [...], "gaps_to_fix": [...], "notes": "..."}}}}}}.'
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        raise HTTPException(status_code=500, detail="LLM library not available")

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"elig-{uuid.uuid4()}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-6")

    try:
        response = await chat.send_message(UserMessage(text=user_prompt))
    except Exception as e:
        logger.error(f"Eligibility AI failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI scoring failed: {str(e)[:200]}")

    raw = str(response).strip()
    # Strip fences
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    try:
        parsed: Dict[str, Any] = json.loads(raw)
    except Exception as e:
        logger.error(f"Eligibility JSON parse failed: {e}; raw={raw[:200]}")
        raise HTTPException(status_code=502, detail="AI returned invalid response, please retry")

    # Persist score for analytics
    score_id = str(uuid.uuid4())
    record = {
        "id": score_id,
        "full_name": data.full_name,
        "email": data.email,
        "mobile": data.mobile,
        "profile": data.dict(),
        "result": parsed,
        "created_at": datetime.now(timezone.utc),
    }
    await scores_col.insert_one(record)

    # If consent given, also create a lead
    if data.consent_to_contact and (data.email or data.mobile):
        top = parsed.get("top_recommendation") or "unknown"
        top_score = (parsed.get("pathways") or {}).get(top, {}).get("score") or 0
        await leads_col.insert_one({
            "id": str(uuid.uuid4()),
            "name": data.full_name,
            "email": data.email,
            "mobile": data.mobile,
            "country": (data.preferred_countries or [""])[0] if data.preferred_countries else "",
            "service_type": top,
            "source": "eligibility_pre_score",
            "priority": "high" if top_score >= 70 else "normal",
            "tag": f"elig-{top_score}",
            "notes": parsed.get("overall_summary", "")[:500],
            "score_id": score_id,
            "status": "new",
            "created_at": datetime.now(timezone.utc),
        })

    return {
        "score_id": score_id,
        "top_recommendation": parsed.get("top_recommendation"),
        "overall_summary": parsed.get("overall_summary"),
        "pathways": parsed.get("pathways") or {},
        "lead_captured": data.consent_to_contact and bool(data.email or data.mobile),
    }


@router.get("/share/{score_id}")
async def get_share(score_id: str):
    """Public — fetch a previously generated score by id (shareable link)."""
    rec = await scores_col.find_one({"id": score_id}, {"_id": 0, "profile": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Score not found")
    if hasattr(rec.get("created_at"), "isoformat"):
        rec["created_at"] = rec["created_at"].isoformat()
    return rec
