"""AI Proposal Generator — GPT-5 powered personalised proposal writer.

Used by Partners to generate a professional proposal narrative for a client
based on the pre-assessment profile. Output is editable before sending.
"""
import os
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.auth import get_current_user
from core.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-proposal", tags=["AI Proposal"])

pre_assessments_col = db["pre_assessments"]
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

SYSTEM_PROMPT = (
    "You are an expert immigration consultant writing a professional, warm, and "
    "persuasive proposal letter to a prospective client. The client has already "
    "paid for pre-assessment and is now considering the main engagement. "
    "Write in a confident, empathetic, results-focused tone. "
    "Use Indian English conventions. Keep it 250-380 words. "
    "Structure the proposal in THREE parts, separated by a single blank line: "
    "1) Opening — acknowledge their goals and eligibility strengths. "
    "2) Our Approach — 3-4 concrete steps we will take for their case. "
    "3) Why us + clear call to action. "
    "Do NOT mention specific fees/pricing numbers. Do NOT use bullet-lists or markdown. "
    "Write in flowing paragraphs."
)


class AIGenerateRequest(BaseModel):
    pa_id: str
    tone: Optional[str] = "professional"  # professional | friendly | assertive
    custom_instructions: Optional[str] = ""


@router.post("/generate")
async def generate_proposal(data: AIGenerateRequest, current_user: dict = Depends(get_current_user)):
    """Generate a personalised proposal draft for a pre-assessment.

    Only the owning partner (or admin) can invoke. Uses Emergent LLM key with GPT-5.
    """
    if current_user.get("role") not in ("partner", "admin"):
        raise HTTPException(status_code=403, detail="Partners or admins only")

    pa = await pre_assessments_col.find_one({"id": data.pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if current_user.get("role") == "partner" and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your pre-assessment")

    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="Emergent LLM key not configured")

    # Build client profile brief
    profile_parts = [
        f"Client name: {pa.get('client_name', 'the applicant')}",
        f"Target country: {pa.get('country', 'N/A')}",
        f"Service type / visa: {pa.get('service_type', 'N/A')}",
    ]
    if pa.get("product_name"):
        profile_parts.append(f"Product: {pa['product_name']}")
    if pa.get("client_age"):
        profile_parts.append(f"Age: {pa['client_age']}")
    if pa.get("education"):
        profile_parts.append(f"Education: {pa['education']}")
    if pa.get("work_experience"):
        profile_parts.append(f"Work experience: {pa['work_experience']}")
    if pa.get("admin_reason"):
        profile_parts.append(f"Admin eligibility note: {pa['admin_reason']}")
    if pa.get("notes"):
        profile_parts.append(f"Partner notes: {pa['notes']}")

    profile = "\n".join(profile_parts)

    tone_hint = {
        "professional": "Use a polished, corporate tone.",
        "friendly": "Use a warm, conversational tone while staying professional.",
        "assertive": "Use a confident, decisive tone that signals expertise.",
    }.get(data.tone, "")

    user_prompt = (
        f"Write a proposal for this client profile:\n\n{profile}\n\n"
        f"{tone_hint}\n"
    )
    if data.custom_instructions:
        user_prompt += f"\nAdditional instructions from the partner: {data.custom_instructions}\n"

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError as e:
        logger.error(f"emergentintegrations not installed: {e}")
        raise HTTPException(status_code=500, detail="LLM library not installed")

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"propose-{uuid.uuid4()}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    try:
        response = await chat.send_message(UserMessage(text=user_prompt))
    except Exception as e:
        logger.error(f"AI proposal generation failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI generation failed: {str(e)[:200]}")

    text = str(response).strip()
    # Strip stray fences if present
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("markdown") or text.startswith("text"):
            first_nl = text.find("\n")
            if first_nl != -1:
                text = text[first_nl + 1:]

    return {
        "ok": True,
        "proposal_text": text,
        "tone": data.tone,
        "word_count": len(text.split()),
        "model": "anthropic/claude-sonnet-4-5",
    }
