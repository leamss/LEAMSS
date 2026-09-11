"""WhatsApp Template Manager — user-authored, reusable WhatsApp templates.

Consultants can create/edit/delete named WhatsApp templates (body with
{placeholders} and optional attachment toggles for Assessment Report, SLA, and Payment QR),
mark one as the default per category, draft with AI, and preview them live in a WhatsApp bubble.
"""
from __future__ import annotations

import os
import re
import uuid
import asyncio
import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/whatsapp-templates", tags=["whatsapp-templates"])

TEMPLATES = db["whatsapp_templates"]

ADMIN_ROLES = {"admin", "admin_owner"}
CATEGORIES = {"eligible", "not_eligible", "resume", "general"}

WHATSAPP_PLACEHOLDERS = [
    {"token": "{client_name}", "desc": "Client's full name", "sample": "Rahul Sharma"},
    {"token": "{occupation}", "desc": "Assessed occupation title", "sample": "Software Engineer"},
    {"token": "{code}", "desc": "ANZSCO occupation code", "sample": "261313"},
    {"token": "{points}", "desc": "Total immigration points scored", "sample": "75"},
    {"token": "{best_subclass}", "desc": "Best recommended visa subclass", "sample": "189"},
    {"token": "{pass_mark}", "desc": "Visa pass mark (usually 65)", "sample": "65"},
    {"token": "{report_url}", "desc": "Direct secure link to view assessment report online", "sample": "https://app.leamss.com/sales/report/xyz"},
    {"token": "{reasons}", "desc": "Bullet list explaining non-eligibility", "sample": "• Indicative score is below 65 points"},
    {"token": "{improvements}", "desc": "Bullet list of recommended steps", "sample": "• Improve English to Superior (+20 pts)"},
    {"token": "{consultant_name}", "desc": "Consultant / Migration team name", "sample": "LEAMSS Migration Team"},
    {"token": "{calendly_link}", "desc": "Consultation booking calendar link", "sample": "https://calendly.com/leamss"},
    {"token": "{offer_badge}", "desc": "Active promo offer badge title", "sample": "Independence Day Special Offer"},
    {"token": "{offer_price}", "desc": "Special promotional enrolment price", "sample": "₹80,000 + 18% GST"},
    {"token": "{offer_regular_fee}", "desc": "Standard regular service fee", "sample": "₹1,55,000 + 18% GST"},
    {"token": "{offer_savings}", "desc": "Total client savings amount", "sample": "You Save ₹75,000"},
    {"token": "{offer_valid_till}", "desc": "Expiry date of special pricing", "sample": "15 August 2026"},
    {"token": "{payment_link}", "desc": "Direct online payment link", "sample": "https://rzp.io/rzp/sample"},
    {"token": "{upi_id}", "desc": "Official LEAMSS UPI ID for direct transfer", "sample": "7738352427@okbizaxis"},
    {"token": "{company}", "desc": "Company name", "sample": "LEAMSS"},
    {"token": "{phone}", "desc": "Official contact phone number", "sample": "+91 77188 82427"},
]


def _can(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or []) or role in (
        "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "partner",
    )


def _clean(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    return doc


class TemplateIn(BaseModel):
    name: str
    category: str = "general"
    body: str = ""
    is_default: bool = False
    attach_report: bool = True
    attach_sla: bool = False
    attach_qr: bool = False
    attach_resume: bool = True


# ── Built-in Starter WhatsApp Templates ─────────────────────────────────────
_STARTERS = [
    {
        "name": "Positive — Full Report & Welcome",
        "category": "eligible",
        "body": (
            "Hello {client_name}! 🎉\n\n"
            "Congratulations! Your Australia PR Profile Pre-Assessment outcome is *POSITIVE*.\n\n"
            "📋 *Occupation:* {occupation} ({code})\n"
            "🏆 *Score:* {points} points (Pass Mark: {pass_mark})\n"
            "🎯 *Recommended Pathway:* Subclass {best_subclass}\n\n"
            "📄 Your official 23-page Pre-Assessment Report and documentation are attached with this message.\n\n"
            "🔗 You can also review your online portal report here:\n{report_url}\n\n"
            "Would you like to schedule a quick 15-minute consultation with our senior migration expert to discuss next steps? Reply *YES* or book directly:\n{calendly_link}\n\n"
            "Warm Regards,\n*{consultant_name}* · LEAMSS"
        ),
        "is_default": True,
        "attach_report": True,
        "attach_sla": True,
        "attach_qr": True,
        "attach_resume": True,
    },
    {
        "name": "SLA & Fast-Track Enrolment",
        "category": "eligible",
        "body": (
            "Dear {client_name},\n\n"
            "Thank you for choosing LEAMSS for your Australia PR journey.\n\n"
            "We have attached our official *Service Level Agreement (SLA)* and *Payment QR* to fast-track your skills assessment and EOI lodgement.\n\n"
            "🏷️ *Special Enrolment Price:* {offer_price} ({offer_savings})\n"
            "⏳ *Offer Valid Till:* {offer_valid_till}\n"
            "💳 *Pay Online:* {payment_link}\n"
            "📲 *UPI ID:* {upi_id}\n\n"
            "Once payment is completed, please share the screenshot here to immediately activate your dedicated Case Manager.\n\n"
            "Warm Regards,\n*{consultant_name}* · LEAMSS"
        ),
        "is_default": False,
        "attach_report": True,
        "attach_sla": True,
        "attach_qr": True,
        "attach_resume": True,
    },
    {
        "name": "Not Eligible — Improvement Plan",
        "category": "not_eligible",
        "body": (
            "Hello {client_name},\n\n"
            "Thank you for evaluating your migration profile with LEAMSS for *{occupation}* ({code}).\n\n"
            "Your profile is currently short of the required threshold ({points} pts vs {pass_mark} pass mark). Here is your clear action plan:\n\n"
            "{improvements}\n\n"
            "📄 We have attached your diagnostic assessment breakdown. Let's discuss how you can achieve eligibility — book a free review call:\n{calendly_link}\n\n"
            "Warm Regards,\n*{consultant_name}* · LEAMSS"
        ),
        "is_default": True,
        "attach_report": True,
        "attach_sla": False,
        "attach_qr": False,
        "attach_resume": True,
    },
    {
        "name": "Warm Follow-Up & Limited Offer",
        "category": "eligible",
        "body": (
            "Hi {client_name}! 👋\n\n"
            "Hope you are doing well. Just following up on your Australia PR Pre-Assessment report ({points} points, Subclass {best_subclass}).\n\n"
            "Your exclusive discount ({offer_price} instead of {offer_regular_fee}) is valid until *{offer_valid_till}*.\n\n"
            "Locked slots are filling up fast for this intake. To reserve your spot, reply here or pay securely at {payment_link}.\n\n"
            "Feel free to reply with any questions!\n\n"
            "Best Regards,\n*{consultant_name}* · LEAMSS"
        ),
        "is_default": False,
        "attach_report": False,
        "attach_sla": True,
        "attach_qr": True,
        "attach_resume": False,
    },
    {
        "name": "Resume Upload Request",
        "category": "resume",
        "body": (
            "Hello {client_name},\n\n"
            "To complete your Australia PR Pre-Assessment and calculate your exact point score, please reply with your latest *Resume / CV* as a PDF or document here.\n\n"
            "Our certified MARA-aligned migration specialists will evaluate your profile within 2 hours.\n\n"
            "Thank you,\n*{consultant_name}* · LEAMSS"
        ),
        "is_default": True,
        "attach_report": False,
        "attach_sla": False,
        "attach_qr": False,
        "attach_resume": False,
    },
    {
        "name": "Consultation Nudge",
        "category": "general",
        "body": (
            "Hi {client_name}! 🌟\n\n"
            "Are you free for a quick 10-minute discovery call today to review your Australia visa options and timelines?\n\n"
            "You can pick a convenient time slot here: {calendly_link}\n\n"
            "Looking forward to speaking with you!\n\n"
            "Warm Regards,\n*{consultant_name}* · LEAMSS"
        ),
        "is_default": True,
        "attach_report": False,
        "attach_sla": False,
        "attach_qr": False,
        "attach_resume": False,
    },
]


async def _ensure_seeded():
    """Idempotently add any starter template that isn't present yet."""
    now = datetime.now(timezone.utc).isoformat()
    existing = set(await TEMPLATES.distinct("name"))
    for t in _STARTERS:
        if t["name"] in existing:
            continue
        await TEMPLATES.insert_one({
            "id": uuid.uuid4().hex, **t, "created_at": now, "updated_at": now,
        })
    await TEMPLATES.update_many({"attach_resume": {"$exists": False}}, {"$set": {"attach_resume": True}})


@router.get("/placeholders")
async def list_placeholders(current_user: dict = Depends(get_current_user)):
    return {"placeholders": WHATSAPP_PLACEHOLDERS}


@router.get("")
async def list_templates(current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    await _ensure_seeded()
    docs = await TEMPLATES.find({}).sort("created_at", 1).to_list(500)
    return {"templates": [_clean(d) for d in docs]}


@router.post("")
async def create_template(payload: TemplateIn, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    cat = payload.category if payload.category in CATEGORIES else "general"
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": uuid.uuid4().hex,
        "name": payload.name.strip() or "Untitled WhatsApp template",
        "category": cat,
        "body": payload.body,
        "is_default": bool(payload.is_default),
        "attach_report": bool(payload.attach_report),
        "attach_sla": bool(payload.attach_sla),
        "attach_qr": bool(payload.attach_qr),
        "attach_resume": bool(payload.attach_resume),
        "created_at": now,
        "updated_at": now,
    }
    if doc["is_default"]:
        await TEMPLATES.update_many({"category": cat}, {"$set": {"is_default": False}})
    await TEMPLATES.insert_one(doc)
    return _clean(doc)


@router.put("/{template_id}")
async def update_template(template_id: str, payload: TemplateIn, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    existing = await TEMPLATES.find_one({"id": template_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    cat = payload.category if payload.category in CATEGORIES else "general"
    updates = {
        "name": payload.name.strip() or "Untitled WhatsApp template",
        "category": cat,
        "body": payload.body,
        "is_default": bool(payload.is_default),
        "attach_report": bool(payload.attach_report),
        "attach_sla": bool(payload.attach_sla),
        "attach_qr": bool(payload.attach_qr),
        "attach_resume": bool(payload.attach_resume),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if updates["is_default"]:
        await TEMPLATES.update_many({"category": cat, "id": {"$ne": template_id}}, {"$set": {"is_default": False}})
    await TEMPLATES.update_one({"id": template_id}, {"$set": updates})
    doc = await TEMPLATES.find_one({"id": template_id})
    return _clean(doc)


@router.delete("/{template_id}")
async def delete_template(template_id: str, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    res = await TEMPLATES.delete_one({"id": template_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}


class PreviewRequest(BaseModel):
    body: str = ""


_SAMPLE_CTX = {
    "client_name": "Rahul Sharma",
    "occupation": "Software Engineer",
    "code": "261313",
    "points": "75",
    "best_subclass": "189",
    "pass_mark": "65",
    "report_url": "https://app.leamss.com/sales/report/demo-token-123",
    "reasons": "• Current points are 55 (pass mark 65)",
    "improvements": "• Superior English (IELTS 8+): +20 points\n• State Nomination Subclass 190: +5 points",
    "consultant_name": "LEAMSS Migration Team",
    "calendly_link": "https://calendly.com/leamss",
    "offer_badge": "Special Enrolment Offer",
    "offer_price": "₹80,000 + 18% GST",
    "offer_regular_fee": "₹1,55,000 + 18% GST",
    "offer_savings": "You Save ₹75,000",
    "offer_valid_till": "15 August 2026",
    "payment_link": "https://rzp.io/rzp/sample",
    "upi_id": "7738352427@okbizaxis",
    "company": "LEAMSS",
    "phone": "+91 77188 82427",
}


def render_whatsapp_preview(body: str, ctx: Dict[str, Any] = _SAMPLE_CTX) -> str:
    res = body or ""
    for k, v in ctx.items():
        res = res.replace(f"{{{k}}}", str(v))
    return res


@router.post("/preview")
async def preview_template(payload: PreviewRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    rendered = render_whatsapp_preview(payload.body)
    return {"rendered": rendered}


# ── AI Draft for WhatsApp ────────────────────────────────────────────────────
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
AI_WHATSAPP_MODEL = "claude-sonnet-4-6"

_AI_SYSTEM = (
    "You are an expert conversational sales copywriter for LEAMSS (Ladhani Education & Migration Services), "
    "an Australia immigration & education consultancy. You craft engaging, concise, high-converting WhatsApp messages. "
    "Use WhatsApp formatting: *bold* for emphasis, clean emojis (🎉, 📋, 🏆, 💳, 🔗, 👋, 📄), and bullet points. "
    "Keep messages between 60 to 180 words. Never be pushy, maintain a helpful, professional, and trustworthy tone. "
    "IMPORTANT: use these placeholder tokens wherever relevant (do NOT invent real values): "
    "{client_name}, {occupation}, {code}, {points}, {best_subclass}, {pass_mark}, {report_url}, "
    "{reasons}, {improvements}, {consultant_name}, {calendly_link}, {offer_badge}, {offer_price}, "
    "{offer_regular_fee}, {offer_savings}, {offer_valid_till}, {payment_link}, {upi_id}. "
    "Return ONLY valid JSON in format: {\"body\": \"...\"} with '\\n' for new lines."
)


class AiDraftRequest(BaseModel):
    prompt: str = ""
    category: Optional[str] = "general"
    tone: Optional[str] = None
    mode: Optional[str] = "draft"
    current_body: Optional[str] = None


@router.post("/ai-draft")
async def ai_draft_whatsapp(payload: AiDraftRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    is_rewrite = (payload.mode == "rewrite") or bool((payload.current_body or "").strip())
    if not is_rewrite and not (payload.prompt or "").strip():
        raise HTTPException(status_code=400, detail="Please describe the WhatsApp message you want.")
    if is_rewrite and not (payload.current_body or "").strip():
        raise HTTPException(status_code=400, detail="There is no message body to rewrite yet.")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="AI is not configured (EMERGENT_LLM_KEY missing).")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except ImportError:
        raise HTTPException(status_code=503, detail="AI library not available.")

    cat = payload.category if payload.category in CATEGORIES else "general"
    if is_rewrite:
        instruction = (payload.prompt or "").strip() or "Make it punchier, warmer, and more engaging with clean formatting and emojis."
        user_prompt = (
            "Here is an existing WhatsApp message. Improve it as instructed, keeping EVERY existing {placeholder} token intact:\n\n"
            f"Instruction: {instruction}\n\n"
            f"Current body:\n{payload.current_body}\n\n"
            "Return ONLY the JSON object with 'body'."
        )
    else:
        user_prompt = (
            f"Category: {cat}. "
            + (f"Tone: {payload.tone}. " if payload.tone else "")
            + f"Write a high-converting WhatsApp message for this purpose:\n\n{payload.prompt.strip()}\n\n"
            "Remember: return ONLY the JSON object with 'body'."
        )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"wa-draft-{os.urandom(3).hex()}",
            system_message=_AI_SYSTEM,
        ).with_model("anthropic", AI_WHATSAPP_MODEL)
        resp = await asyncio.to_thread(lambda: asyncio.run(chat.send_message(UserMessage(text=user_prompt))))
        raw = (str(resp) if resp is not None else "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        i, j = raw.find("{"), raw.rfind("}")
        if i == -1 or j == -1:
            raise ValueError("non-JSON response")
        data = _json.loads(raw[i:j + 1])
        return {"body": (data.get("body") or "").strip()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI draft failed: {type(e).__name__}. Please try again.")
