"""Email Template Manager — user-authored, reusable email templates.

Consultants can create/edit/delete named templates (subject + body with
{placeholders}), mark one as the default per category, and preview them live.
When sending to a client, sending code picks a specific template (by id) or the
category default; if none, it falls back to the built-in default builders.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import get_current_user
from core.database import db
from core.report_email import render_custom_email, TEMPLATE_PLACEHOLDERS

router = APIRouter(prefix="/email-templates", tags=["email-templates"])

TEMPLATES = db["email_templates"]

ADMIN_ROLES = {"admin", "admin_owner"}
CATEGORIES = {"eligible", "not_eligible", "resume", "general"}


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
    subject: str = ""
    body: str = ""
    is_default: bool = False
    attach_report: bool = False
    attach_resume: bool = True


# ── Seed built-in starter templates once, so the manager is never empty ──────
_STARTERS = [
    {
        "name": "Positive — Report Delivery",
        "category": "eligible",
        "subject": "Congratulations {client_name} — Your Australia PR Pre-Assessment is Positive",
        "body": ("Dear {client_name},\n\n"
                 "We are delighted to share that your Australia migration profile evaluation outcome is POSITIVE. "
                 "Your best pathway is Subclass {best_subclass} with an indicative score of {points} points "
                 "(pass mark {pass_mark}).\n\n"
                 "Your detailed Pre-Assessment report is attached. Our expert team will support you across skills "
                 "assessment, EOI preparation, state nomination and visa documentation.\n\n"
                 "Book a free consultation: {calendly_link}\n\n"
                 "Warm Regards,\n{consultant_name}"),
        "is_default": False,
        "attach_report": True,
        "attach_resume": True,
    },
    {
        "name": "Not-Eligible — With Action Plan",
        "category": "not_eligible",
        "subject": "Your Australia PR Pre-Assessment Outcome — {client_name}",
        "body": ("Dear {client_name},\n\n"
                 "Thank you for choosing LEAMSS. After carefully reviewing your profile for occupation "
                 "{occupation} ({code}), here is an honest assessment.\n\n"
                 "Why you are not eligible right now:\n{reasons}\n\n"
                 "How you can become eligible:\n{improvements}\n\n"
                 "We would be glad to guide you — book a consultation: {calendly_link}\n\n"
                 "Warm Regards,\n{consultant_name}"),
        "is_default": False,
        "attach_report": True,
        "attach_resume": True,
    },
    {
        "name": "Reminder — Report Sent (Warm Follow-up)",
        "category": "eligible",
        "subject": "Gentle reminder {client_name} — your Australia PR offer is still open",
        "body": ("Dear {client_name},\n\n"
                 "I hope you are doing well. A little while ago we shared your Australia PR Pre-Assessment "
                 "report, which confirmed a POSITIVE outcome — an indicative {points} points on Subclass "
                 "{best_subclass}. Congratulations again; this is a strong profile.\n\n"
                 "I wanted to personally follow up because your special enrolment offer is still active:\n\n"
                 "• {offer_badge}\n"
                 "• Regular fee: {offer_regular_fee}\n"
                 "• Your price: {offer_price}  ({offer_savings})\n"
                 "• Valid till: {offer_valid_till} — only limited slots remain\n\n"
                 "Securing your slot now locks in this price and lets our team begin your skills assessment "
                 "and EOI preparation without delay. Every week matters in migration timelines.\n\n"
                 "To proceed, simply reply to this email, pay securely at {payment_link} (UPI: {upi_id}), or "
                 "book a quick call: {calendly_link}\n\n"
                 "I'm personally available for any questions.\n\n"
                 "Warm Regards,\n{consultant_name}"),
        "is_default": False,
        "attach_report": True,
        "attach_resume": True,
    },
    {
        "name": "Offer Extended — Good News",
        "category": "eligible",
        "subject": "Good news {client_name} — your special offer has been EXTENDED",
        "body": ("Dear {client_name},\n\n"
                 "Great news! Due to popular demand, we have EXTENDED our special enrolment offer — so you "
                 "still have a chance to begin your Australia PR journey at the best possible price.\n\n"
                 "Your positive Pre-Assessment confirmed {points} points on Subclass {best_subclass}, which "
                 "means you are ready to move forward.\n\n"
                 "Extended offer for you:\n"
                 "• {offer_badge}\n"
                 "• Regular fee: {offer_regular_fee}\n"
                 "• Your price: {offer_price}  ({offer_savings})\n\n"
                 "This extension is for a short window only and slots are limited. To lock your slot, reply to "
                 "this email, pay at {payment_link} (UPI: {upi_id}), or book a call: {calendly_link}\n\n"
                 "We would love to be part of your migration success story.\n\n"
                 "Warm Regards,\n{consultant_name}"),
        "is_default": False,
        "attach_report": False,
    },
    {
        "name": "Last Chance — Slots Filling Fast",
        "category": "eligible",
        "subject": "{client_name}, only a few slots left for your Australia PR offer",
        "body": ("Dear {client_name},\n\n"
                 "A quick and important update — the slots under your special offer are almost full.\n\n"
                 "You already have a POSITIVE Pre-Assessment ({points} points, Subclass {best_subclass}), so "
                 "you are perfectly placed to begin. I did not want you to miss this price:\n\n"
                 "• Your price: {offer_price} instead of {offer_regular_fee}  ({offer_savings})\n"
                 "• Valid till: {offer_valid_till}\n\n"
                 "Once the slots are gone, standard fees apply. If you're ready, reply 'YES' to this email or "
                 "book a 15-minute call and we'll handle the rest: {calendly_link}\n\n"
                 "Warm Regards,\n{consultant_name}"),
        "is_default": False,
        "attach_report": False,
    },
    {
        "name": "Free Consultation Nudge",
        "category": "general",
        "subject": "{client_name}, shall we plan your Australia PR — free 15-min call?",
        "body": ("Dear {client_name},\n\n"
                 "Migration decisions are important, and I'd love to make yours simple and clear. Based on your "
                 "profile ({occupation}), there is a genuine pathway worth discussing.\n\n"
                 "Let's have a free, no-obligation 15-minute consultation where we will:\n"
                 "• Review your best-fit visa pathway\n"
                 "• Explain the timeline, costs and documents\n"
                 "• Answer every question you have\n\n"
                 "Pick a time that suits you: {calendly_link}\n\n"
                 "Looking forward to speaking with you.\n\n"
                 "Warm Regards,\n{consultant_name}"),
        "is_default": False,
        "attach_report": False,
    },
    {
        "name": "Flexible Payment — Made Easy",
        "category": "eligible",
        "subject": "{client_name}, flexible payment options for your Australia PR",
        "body": ("Dear {client_name},\n\n"
                 "We understand that starting your Australia PR is a big step, so we've made the payment simple "
                 "and flexible for you.\n\n"
                 "Your enrolment: {offer_price} ({offer_savings} vs the regular {offer_regular_fee}).\n\n"
                 "You can pay conveniently via:\n"
                 "• Secure online link: {payment_link}\n"
                 "• UPI: {upi_id}\n"
                 "• NEFT / IMPS / Credit Card / instalment assistance on request\n\n"
                 "Reply to this email and our team will guide you through the option that suits you best, or "
                 "book a call: {calendly_link}\n\n"
                 "Warm Regards,\n{consultant_name}"),
        "is_default": False,
        "attach_report": False,
    },
    {
        "name": "Resume — Upload Request",
        "category": "resume",
        "subject": "Action needed: Upload your resume for your Australia PR assessment — {client_name}",
        "body": ("Dear {client_name},\n\n"
                 "To prepare your personalised Australia PR Pre-Assessment, we need your latest resume/CV. "
                 "It only takes a minute and no login is required.\n\n"
                 "Upload your resume here: {upload_link}\n\n"
                 "Once received, our team will match your best ANZSCO occupation and send your report.\n\n"
                 "Warm Regards,\n{consultant_name}"),
        "is_default": False,
        "attach_report": False,
    },
]


async def _ensure_seeded():
    """Idempotently add any starter template that isn't present yet (matched by name)."""
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
    return {"placeholders": TEMPLATE_PLACEHOLDERS}


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
        "id": uuid.uuid4().hex, "name": payload.name.strip() or "Untitled template",
        "category": cat, "subject": payload.subject, "body": payload.body,
        "is_default": bool(payload.is_default), "attach_report": bool(payload.attach_report),
        "attach_resume": bool(payload.attach_resume),
        "created_at": now, "updated_at": now,
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
        "name": payload.name.strip() or "Untitled template", "category": cat,
        "subject": payload.subject, "body": payload.body,
        "is_default": bool(payload.is_default), "attach_report": bool(payload.attach_report),
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
    subject: str = ""
    body: str = ""


_SAMPLE_CTX = {
    "client_name": "Rahul Sharma", "occupation": "Software Engineer", "code": "261313",
    "points": 70, "best_subclass": "189", "pass_mark": 65,
    "reasons": ["Your current indicative score is 55 points, which is 10 points below the 65-point minimum."],
    "improvements": ["Improve English to Superior (IELTS 8 each band) for +20 points.",
                     "Apply for State nomination (Subclass 190) for +5 points."],
    "alternatives": ["Employer-Sponsored pathways (Subclass 482 / 186)."],
    "upload_link": "https://leamss.com/upload-resume/sample-token",
    "consultant_name": "LEAMSS Migration Team", "calendly_link": "https://calendly.com/leamss",
    "offer_badge": "Independence Day Special Offer", "offer_price": "₹80,000 + 18% GST",
    "offer_regular_fee": "₹1,55,000 + 18% GST", "offer_savings": "You Save ₹75,000",
    "offer_valid_till": "15 August 2026", "payment_link": "https://rzp.io/rzp/sample",
    "upi_id": "7738352427@okbizaxis",
    "company": "LEAMSS", "phone": "+91 77188 82427", "email": "info@leamss.com", "website": "www.leamss.com",
}


@router.post("/preview")
async def preview_template(payload: PreviewRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    subject, html, _plain = render_custom_email(
        {"subject": payload.subject, "body": payload.body}, _SAMPLE_CTX,
        sender_name="LEAMSS Migration Team", settings=None,
    )
    return {"subject": subject, "html": html}



# ── AI draft: write an email template from a short prompt ────────────────────
import asyncio  # noqa: E402
import os  # noqa: E402
import json as _json  # noqa: E402

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
AI_EMAIL_MODEL = "claude-sonnet-4-6"

_AI_SYSTEM = (
    "You are a senior sales copywriter for LEAMSS (Ladhani Education & Migration Services), an Australia "
    "immigration & education consultancy. You write warm, professional, high-converting emails that respect "
    "the reader and drive action (booking a consultation or paying to enrol). Tone: confident, encouraging, "
    "trustworthy, never pushy or spammy. Keep it concise (150-260 words). Use short paragraphs; for lists, "
    "start each line with '• '. IMPORTANT: use these placeholder tokens wherever relevant (do NOT invent real "
    "values): {client_name}, {occupation}, {code}, {points}, {best_subclass}, {pass_mark}, {reasons}, "
    "{improvements}, {alternatives}, {upload_link}, {consultant_name}, {calendly_link}, {offer_badge}, "
    "{offer_price}, {offer_regular_fee}, {offer_savings}, {offer_valid_till}, {payment_link}, {upi_id}. "
    "Always end with a sign-off using {consultant_name}. Do NOT add a company letterhead or footer — that is "
    "added automatically. Return ONLY valid minified JSON: {\"subject\": \"...\", \"body\": \"...\"} with '\\n' "
    "for line breaks in the body."
)


class AiDraftRequest(BaseModel):
    prompt: str = ""
    category: Optional[str] = "general"
    tone: Optional[str] = None
    mode: Optional[str] = "draft"  # 'draft' | 'rewrite'
    current_subject: Optional[str] = None
    current_body: Optional[str] = None


@router.post("/ai-draft")
async def ai_draft_template(payload: AiDraftRequest, current_user: dict = Depends(get_current_user)):
    """Generate OR rewrite an email template (subject + body with placeholders) using Claude."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    is_rewrite = (payload.mode == "rewrite") or bool((payload.current_body or "").strip())
    if not is_rewrite and not (payload.prompt or "").strip():
        raise HTTPException(status_code=400, detail="Please describe the email you want.")
    if is_rewrite and not (payload.current_body or "").strip():
        raise HTTPException(status_code=400, detail="There is no email body to rewrite yet.")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="AI is not configured (EMERGENT_LLM_KEY missing).")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except ImportError:
        raise HTTPException(status_code=503, detail="AI library not available.")

    cat = payload.category if payload.category in CATEGORIES else "general"
    if is_rewrite:
        instruction = (payload.prompt or "").strip() or "Polish it: make it clearer, warmer and more persuasive while keeping it concise."
        user_prompt = (
            "Here is an existing email. Improve it as instructed, keeping EVERY existing {placeholder} token intact "
            "(do not remove or rename them).\n\n"
            f"Instruction: {instruction}\n\n"
            f"Current subject: {payload.current_subject or ''}\n"
            f"Current body:\n{payload.current_body}\n\n"
            "Return ONLY the JSON object with 'subject' and 'body'."
        )
    else:
        user_prompt = (
            f"Category: {cat}. "
            + (f"Tone: {payload.tone}. " if payload.tone else "")
            + f"Write an email for this purpose:\n\n{payload.prompt.strip()}\n\n"
            "Remember: return ONLY the JSON object with 'subject' and 'body'."
        )
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"email-draft-{os.urandom(3).hex()}",
                       system_message=_AI_SYSTEM).with_model("anthropic", AI_EMAIL_MODEL)
        resp = await asyncio.to_thread(lambda: asyncio.run(chat.send_message(UserMessage(text=user_prompt))))
        raw = (str(resp) if resp is not None else "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        i, j = raw.find("{"), raw.rfind("}")
        if i == -1 or j == -1:
            raise ValueError("non-JSON response")
        data = _json.loads(raw[i:j + 1])
        return {"subject": (data.get("subject") or "").strip(), "body": (data.get("body") or "").strip()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI draft failed: {type(e).__name__}. Please try again.")
