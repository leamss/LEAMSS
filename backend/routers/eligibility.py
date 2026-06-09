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

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field

from core.database import db
from core.eligibility_scoring import (
    score_candidate, load_scoring_rules, DEFAULT_RULES, SCORING_RULES_ID,
)
from core.ai_models import model_for
from routers.auth import get_current_user
from routers.visa_compare import SEEDS as VISA_SEEDS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/eligibility", tags=["Eligibility Pre-Score"])

scores_col = db["eligibility_scores"]
leads_col = db["leads"]
pathways_col = db["visa_pathways"]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

SYSTEM_PROMPT = (
    "You are a senior MARA-registered immigration consultant writing a short, honest, "
    "encouraging narrative for a prospective client. The numeric eligibility scores are "
    "ALREADY computed by a transparent rules engine — DO NOT change or invent scores. "
    "Your job is ONLY to explain the results in warm, professional Indian English. "
    "Respond with VALID JSON ONLY (no markdown). Shape: "
    '{"overall_summary": "2-3 sentence honest assessment referencing the best pathway", '
    '"pathways": {"<slug>": {"strengths": ["1-3 short phrases"], '
    '"gaps_to_fix": ["1-3 short phrases"], "notes": "1 sentence pathway-specific advice"}}}'
)

class EligibilityRequest(BaseModel):
    full_name: str = "Website Visitor"
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    age: int = Field(..., ge=16, le=80)
    education: str  # "Bachelor", "Master", "PhD", "Diploma"
    work_experience_years: float = Field(0, ge=0, le=60)
    occupation: Optional[str] = None
    english_score: Optional[str] = None  # "IELTS 7.0", "PTE 65", "None"
    family_savings_inr: Optional[float] = None
    has_job_offer: bool = False
    spouse_education: Optional[str] = None
    children_count: int = 0
    preferred_countries: Optional[List[str]] = None
    consent_to_contact: bool = False


async def _ensure_pathways() -> List[Dict[str, Any]]:
    """Return active pathway requirement docs (auto-seed from visa_compare if empty)."""
    if await pathways_col.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        for s in VISA_SEEDS:
            await pathways_col.insert_one({
                **s, "id": str(uuid.uuid4()), "is_active": True,
                "created_at": now, "updated_at": now,
            })
    return await pathways_col.find({"is_active": True}, {"_id": 0}).sort("rank", 1).to_list(50)


def _profile_summary(data: "EligibilityRequest") -> str:
    lines = [
        "Candidate profile:",
        f"- Age: {data.age}",
        f"- Education: {data.education}",
        f"- Work experience: {data.work_experience_years} years",
        f"- Occupation: {data.occupation or 'Not specified'}",
        f"- English score: {data.english_score or 'Not taken yet'}",
        f"- Job offer abroad: {'Yes' if data.has_job_offer else 'No'}",
    ]
    if data.family_savings_inr:
        lines.append(f"- Family savings: ₹{data.family_savings_inr:,.0f}")
    if data.preferred_countries:
        lines.append(f"- Preferred countries: {', '.join(data.preferred_countries)}")
    return "\n".join(lines)


async def _ai_narrative(data: "EligibilityRequest", deterministic: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort AI narrative layer. NEVER raises — returns {} on any failure."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        return {}
    # Compact deterministic context (slug, score, tier, top factors)
    ctx_lines = []
    for slug, p in deterministic["pathways"].items():
        tops = ", ".join(f"{b['label']} {b['earned']:g}/{b['max']:g}" for b in p["breakdown"])
        ctx_lines.append(f"  - {slug} ({p['name']}): score={p['score']} tier={p['tier']} | {tops}")
    user_prompt = (
        f"{_profile_summary(data)}\n\n"
        f"Pre-computed scores (DO NOT change them):\n" + "\n".join(ctx_lines) +
        f"\n\nBest pathway: {deterministic['top_recommendation']}.\n"
        "Write the narrative JSON now for ALL the slugs above."
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"elig-{uuid.uuid4()}",
            system_message=SYSTEM_PROMPT,
        ).with_model("anthropic", model_for("eligibility_narrative"))
        response = await chat.send_message(UserMessage(text=user_prompt))
    except Exception as e:
        logger.warning(f"Eligibility narrative AI failed (non-fatal): {e}")
        return {}
    raw = str(response).strip()
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    try:
        return json.loads(raw)
    except Exception:
        # last-ditch: extract the first {...} block
        try:
            start, end = raw.index("{"), raw.rindex("}")
            return json.loads(raw[start:end + 1])
        except Exception as e:
            logger.warning(f"Eligibility narrative parse failed (non-fatal): {e}")
            return {}


def _fallback_text(p: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic narrative when AI is unavailable — uses the breakdown."""
    strengths = [f"{b['label']}" for b in p["breakdown"] if b["max"] > 0 and b["earned"] >= 0.8 * b["max"]][:3]
    gaps = [b["label"] for b in p["breakdown"] if b["max"] > 0 and b["earned"] < 0.5 * b["max"]][:3]
    return {
        "strengths": strengths or ["Profile basics captured"],
        "gaps_to_fix": gaps or ["Share more details for a sharper score"],
        "notes": f"Indicative {p['tier']} match — talk to a LEAMSS expert for a verified assessment.",
    }


@router.get("/pathways")
async def list_pathways():
    """Public — list of pathways scored by the engine."""
    items = await _ensure_pathways()
    return {"pathways": [{"slug": p["slug"], "name": p["name"], "country": p.get("country")} for p in items]}


@router.post("/score")
async def score_eligibility(data: EligibilityRequest):
    """Public — transparent rule-based scoring + AI narrative; persists a lead on consent."""
    pathways = await _ensure_pathways()
    profile = data.dict()

    # 1) Deterministic, explainable scoring (the numbers)
    deterministic = await score_candidate(profile, pathways)

    # 2) Best-effort AI narrative (the words) — never fatal
    narrative = await _ai_narrative(data, deterministic)
    nar_paths = (narrative or {}).get("pathways") or {}

    # 3) Merge number + words
    merged_pathways: Dict[str, Any] = {}
    for slug, p in deterministic["pathways"].items():
        n = nar_paths.get(slug) or _fallback_text(p)
        merged_pathways[slug] = {
            **p,
            "strengths": n.get("strengths") or n.get("key_strengths") or [],
            "key_strengths": n.get("strengths") or n.get("key_strengths") or [],
            "gaps_to_fix": n.get("gaps_to_fix") or [],
            "notes": n.get("notes") or "",
        }

    top = deterministic["top_recommendation"]
    top_name = merged_pathways.get(top, {}).get("name", top)
    overall = (narrative or {}).get("overall_summary") or (
        f"Your strongest indicative match is {top_name} "
        f"({merged_pathways.get(top, {}).get('score', 0)}/100). "
        "This score is calculated from your age, education, experience, English and other factors — "
        "expand each pathway to see exactly how it was computed."
    )

    score_id = str(uuid.uuid4())
    await scores_col.insert_one({
        "id": score_id,
        "full_name": data.full_name,
        "email": data.email,
        "mobile": data.mobile,
        "profile": profile,
        "result": {
            "top_recommendation": top,
            "overall_summary": overall,
            "pathways": merged_pathways,
            "rules_source": deterministic.get("rules_source"),
        },
        "created_at": datetime.now(timezone.utc),
    })

    if data.consent_to_contact and (data.email or data.mobile):
        top_score = merged_pathways.get(top, {}).get("score") or 0
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
            "notes": overall[:500],
            "score_id": score_id,
            "status": "new",
            "created_at": datetime.now(timezone.utc),
        })

    return {
        "score_id": score_id,
        "top_recommendation": top,
        "overall_summary": overall,
        "pathways": merged_pathways,
        "lead_captured": data.consent_to_contact and bool(data.email or data.mobile),
    }


# ── Admin — Eligibility Scoring Rules (transparency & control) ───────────────

def _admin_only(u: dict):
    if u.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("/scoring-rules")
async def get_scoring_rules(current_user: dict = Depends(get_current_user)):
    """Admin — current scoring rules (DB override merged over defaults) + defaults."""
    _admin_only(current_user)
    rules = await load_scoring_rules()
    return {"rules": rules, "defaults": DEFAULT_RULES, "source": rules.get("_source", "defaults")}


class ScoringRulesUpdate(BaseModel):
    factors: Optional[Dict[str, Any]] = None
    tiers: Optional[Dict[str, int]] = None
    age_curve: Optional[Dict[str, float]] = None
    education_levels: Optional[Dict[str, int]] = None
    experience_buffer_years: Optional[float] = None


@router.put("/scoring-rules")
async def update_scoring_rules(body: ScoringRulesUpdate, current_user: dict = Depends(get_current_user)):
    """Admin — save scoring-rules override."""
    _admin_only(current_user)
    upd = {k: v for k, v in body.dict().items() if v is not None}
    if not upd:
        raise HTTPException(status_code=400, detail="No fields to update")
    upd["version"] = (await db["kb_settings"].find_one({"_id": SCORING_RULES_ID}) or {}).get("version", 1) + 1
    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
    upd["updated_by"] = current_user.get("email") or current_user.get("id")
    await db["kb_settings"].update_one({"_id": SCORING_RULES_ID}, {"$set": upd}, upsert=True)
    return {"ok": True, "rules": await load_scoring_rules()}


@router.post("/scoring-rules/reset")
async def reset_scoring_rules(current_user: dict = Depends(get_current_user)):
    """Admin — delete override → revert to hardcoded defaults."""
    _admin_only(current_user)
    await db["kb_settings"].delete_one({"_id": SCORING_RULES_ID})
    return {"ok": True, "rules": {**DEFAULT_RULES, "_source": "defaults"}}


class EligibilityLead(BaseModel):
    score_id: Optional[str] = None
    name: str = "Website Visitor"
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    preferred_country: Optional[str] = None


@router.post("/lead")
async def capture_lead(body: EligibilityLead):
    """Public — capture contact from the result screen and link to a prior score."""
    if not (body.email or body.mobile):
        raise HTTPException(status_code=400, detail="Provide an email or mobile number")
    top, top_score, summary = "unknown", 0, ""
    if body.score_id:
        rec = await scores_col.find_one({"id": body.score_id}, {"_id": 0, "result": 1})
        if rec:
            res = rec.get("result") or {}
            top = res.get("top_recommendation") or "unknown"
            top_score = (res.get("pathways") or {}).get(top, {}).get("score") or 0
            summary = res.get("overall_summary", "")
    await leads_col.insert_one({
        "id": str(uuid.uuid4()),
        "name": body.name,
        "email": body.email,
        "mobile": body.mobile,
        "country": body.preferred_country or "",
        "service_type": top,
        "source": "eligibility_quiz",
        "priority": "high" if top_score >= 70 else "normal",
        "tag": f"elig-{top_score}",
        "notes": summary[:500],
        "score_id": body.score_id,
        "status": "new",
        "created_at": datetime.now(timezone.utc),
    })
    return {"ok": True, "message": "Thanks! A LEAMSS expert will reach out within 24 hours."}


@router.get("/share/{score_id}")
async def get_share(score_id: str):
    """Public — fetch a previously generated score by id (shareable link)."""
    rec = await scores_col.find_one({"id": score_id}, {"_id": 0, "profile": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Score not found")
    if hasattr(rec.get("created_at"), "isoformat"):
        rec["created_at"] = rec["created_at"].isoformat()
    return rec
