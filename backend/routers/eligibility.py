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
            "phone": data.mobile,
            "country": (data.preferred_countries or [""])[0] if data.preferred_countries else "",
            "service_type": top,
            "service_interested": top_name,
            "top_pathway_name": top_name,
            "top_score": top_score,
            "source": "eligibility_pre_score",
            "priority": "high" if top_score >= 70 else "normal",
            "tag": f"elig-{top_score}",
            "notes": overall[:500],
            "score_id": score_id,
            "status": "new",
            "stage": "new",
            "assigned_to": None,
            "assigned_to_name": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
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
    competitiveness_penalty_max: Optional[float] = None
    no_offer_penalty: Optional[float] = None


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
    top, top_score, summary, top_name = "unknown", 0, "", "Pathway"
    if body.score_id:
        rec = await scores_col.find_one({"id": body.score_id}, {"_id": 0, "result": 1})
        if rec:
            res = rec.get("result") or {}
            top = res.get("top_recommendation") or "unknown"
            top_p = (res.get("pathways") or {}).get(top, {})
            top_score = top_p.get("score") or 0
            top_name = top_p.get("name") or top
            summary = res.get("overall_summary", "")
    await leads_col.insert_one({
        "id": str(uuid.uuid4()),
        "name": body.name,
        "email": body.email,
        "mobile": body.mobile,
        "phone": body.mobile,
        "country": body.preferred_country or "",
        "service_type": top,
        "service_interested": top_name,
        "top_pathway_name": top_name,
        "top_score": top_score,
        "source": "eligibility_quiz",
        "priority": "high" if top_score >= 70 else "normal",
        "tag": f"elig-{top_score}",
        "notes": summary[:500],
        "score_id": body.score_id,
        "status": "new",
        "stage": "new",
        "assigned_to": None,
        "assigned_to_name": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    return {"ok": True, "message": "Thanks! A LEAMSS expert will reach out within 24 hours."}


@router.get("/admin/scorecard-leads")
async def admin_scorecard_leads(current_user: dict = Depends(get_current_user)):
    """Admin/partner — eligibility scorecard leads (with PDF link data + assignment)."""
    if current_user.get("role") not in ("admin", "partner", "case_manager", "sales_manager"):
        raise HTTPException(status_code=403, detail="Not authorized")
    q = {"source": {"$in": ["eligibility_quiz", "eligibility_pre_score"]}}
    # Partners only see leads assigned to them
    if current_user.get("role") == "partner":
        q["assigned_to"] = current_user["id"]
    leads = await leads_col.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    out = []
    for ld in leads:
        ca = ld.get("created_at")
        out.append({
            "id": ld.get("id"),
            "name": ld.get("name"),
            "email": ld.get("email"),
            "phone": ld.get("phone") or ld.get("mobile"),
            "country": ld.get("country"),
            "top_pathway_name": ld.get("top_pathway_name") or ld.get("service_interested") or ld.get("service_type"),
            "top_score": ld.get("top_score"),
            "score_id": ld.get("score_id"),
            "source": ld.get("source"),
            "stage": ld.get("stage") or ld.get("status") or "new",
            "assigned_to": ld.get("assigned_to"),
            "assigned_to_name": ld.get("assigned_to_name"),
            "created_at": ca.isoformat() if hasattr(ca, "isoformat") else ca,
        })
    return out


class AssignLead(BaseModel):
    assigned_to: str
    assigned_to_name: Optional[str] = None


@router.put("/admin/scorecard-leads/{lead_id}/assign")
async def assign_scorecard_lead(lead_id: str, body: AssignLead, current_user: dict = Depends(get_current_user)):
    """Admin — assign a scorecard lead (with client details + PDF) to a partner/sales person."""
    if current_user.get("role") not in ("admin", "sales_manager"):
        raise HTTPException(status_code=403, detail="Admin only")
    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "id": 1})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    name = body.assigned_to_name
    if not name:
        u = await db["users"].find_one({"id": body.assigned_to}, {"_id": 0, "name": 1})
        name = u.get("name") if u else None
    await leads_col.update_one({"id": lead_id}, {"$set": {
        "assigned_to": body.assigned_to,
        "assigned_to_name": name,
        "stage": "contacted",
        "updated_at": datetime.now(timezone.utc),
    }})
    return {"ok": True, "assigned_to_name": name}


@router.get("/share/{score_id}")
async def get_share(score_id: str):
    """Public — fetch a previously generated score by id (shareable link)."""
    rec = await scores_col.find_one({"id": score_id}, {"_id": 0, "profile": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Score not found")
    if hasattr(rec.get("created_at"), "isoformat"):
        rec["created_at"] = rec["created_at"].isoformat()
    return rec


REPORTS_DIR = "/app/uploads/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

_TIER_PDF = {
    "strong": ("Strong fit", "#2E7D32"),
    "moderate": ("Moderate fit", "#1F4D44"),
    "weak": ("Needs work", "#D4633F"),
    "unlikely": ("Unlikely", "#8A8A8A"),
}


LOGO_PATH = "/app/frontend/public/leamss-logo.png"
_CONTACT = {
    "website": "www.leamss.com",
    "phone": "+91 77188 82427",
    "whatsapp": "+91 77383 52427",
    "email": "info@leamss.com",
    "legal": "Ladhani Education & Migration Services (OPC) Pvt. Ltd",
}
_REVIEWS = [
    ("Sophia Chowdhury", "Mumbai \u2192 Sydney", "So grateful to LEAMSS for guiding my Australian PR journey. Their expertise and support made a huge difference."),
    ("Varsha Bhatia", "Pune \u2192 Toronto", "Extremely happy with the service. The team was supportive, professional and highly responsive \u2014 patiently addressed every query."),
    ("Krishna K V", "Bangalore \u2192 Brisbane", "Practical, supportive and expert at analysing profiles for the ideal destination. Strongly recommend for anyone exploring migration."),
    ("Gurleen Kaur", "Delhi \u2192 Auckland", "A wonderful team to work with. Professional and lucid \u2014 they kept their word and made the whole journey wonderful."),
]
_VALUES = [
    ("Radical Transparency", "Fixed, written fees with zero hidden charges. You always know exactly what you pay \u2014 and why."),
    ("Integrity First", "MARA-registered, legally-compliant advice. We never over-promise just to win a client."),
    ("Client at the Centre", "A dedicated case manager, 24-hour response times and genuine end-to-end support."),
    ("Speed with Accuracy", "Streamlined, fixed-timeline processing on eligible profiles \u2014 fast, without cutting corners."),
]


def _generate_scorecard_pdf(rec: dict, filename: str):
    import os as _os
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                    Spacer, HRFlowable, Image, PageBreak)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.graphics.shapes import Drawing, Rect, Polygon
    import math

    GREEN = colors.HexColor("#1F4D44")
    ACCENT = colors.HexColor("#D4633F")
    INK = colors.HexColor("#1A2A30")
    BODY = colors.HexColor("#33444C")
    MUTE = colors.HexColor("#6B7B82")
    CREAM = colors.HexColor("#F5F2EC")
    GOLD = colors.HexColor("#E0A82E")
    LINE = colors.HexColor("#E3DED5")
    PAGE_W, PAGE_H = A4
    CONTENT_W = PAGE_W - 32 * mm  # margins 16mm each side

    result = rec.get("result") or {}
    pathways = result.get("pathways") or {}
    ordered = sorted(pathways.items(), key=lambda kv: -(kv[1].get("score") or 0))
    top = result.get("top_recommendation")
    top_name = pathways.get(top, {}).get("name", top) if top else "\u2014"

    styles = getSampleStyleSheet()

    def PS(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    title_st = PS("t", fontName="Helvetica-Bold", fontSize=19, textColor=GREEN, leading=22, alignment=TA_LEFT)
    sub_st = PS("s", fontName="Helvetica", fontSize=8.5, textColor=MUTE, leading=11, alignment=TA_LEFT)
    sect_st = PS("sec", fontName="Helvetica-Bold", fontSize=13.5, textColor=GREEN, leading=16, spaceAfter=2)
    body_st = PS("b", fontName="Helvetica", fontSize=9.5, textColor=BODY, leading=14)
    bodyc_st = PS("bc", fontName="Helvetica", fontSize=9, textColor=colors.white, leading=14)
    small_st = PS("sm", fontName="Helvetica", fontSize=8, textColor=MUTE, leading=11)
    italic_st = PS("it", fontName="Helvetica-Oblique", fontSize=8.5, textColor=BODY, leading=12.5)
    disc_st = PS("d", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#8a4b22"), leading=11)
    vtitle_st = PS("vt", fontName="Helvetica-Bold", fontSize=9.5, textColor=GREEN, leading=12)
    vbody_st = PS("vb", fontName="Helvetica", fontSize=8, textColor=BODY, leading=11)

    def fit_tag(tier):
        label, hexc = _TIER_PDF.get(tier, ("\u2014", "#888888"))
        return Paragraph(label, PS("ft", fontName="Helvetica-Bold", fontSize=7.5,
                                   textColor=colors.white, backColor=colors.HexColor(hexc),
                                   alignment=TA_CENTER, leading=12, borderPadding=(2, 3, 2, 3)))

    def score_bar(score, hexc):
        w = 58
        d = Drawing(w, 7)
        d.add(Rect(0, 0, w, 6, fillColor=CREAM, strokeColor=None))
        d.add(Rect(0, 0, max(2, w * float(score) / 100.0), 6, fillColor=colors.HexColor(hexc), strokeColor=None))
        return d

    def stars(n=5, size=9):
        d = Drawing(n * (size + 1.5), size + 2)
        R = size / 2.0
        r = R * 0.42
        cy = (size + 2) / 2.0
        for i in range(n):
            cx = R + i * (size + 1.5)
            pts = []
            for k in range(10):
                ang = -math.pi / 2.0 + k * math.pi / 5.0
                rad = R if k % 2 == 0 else r
                pts.extend([cx + rad * math.cos(ang), cy + rad * math.sin(ang)])
            d.add(Polygon(points=pts, fillColor=GOLD, strokeColor=None))
        return d

    def card(flowables, bg=CREAM, border=LINE, accent_left=None, width=CONTENT_W, pad=10):
        rows = [[f] for f in flowables]
        t = Table(rows, colWidths=[width])
        st = [
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0.75, border),
            ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
            ("LEFTPADDING", (0, 0), (-1, -1), pad + 2), ("RIGHTPADDING", (0, 0), (-1, -1), pad + 2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        if accent_left:
            st.append(("LINEBEFORE", (0, 0), (0, -1), 3, accent_left))
        t.setStyle(TableStyle(st))
        return t

    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=16 * mm, bottomMargin=22 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm, title="LEAMSS Pathway Fit Scorecard")
    story = []

    # ── Header: logo + title ─────────────────────────────────────────────────
    if _os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=46 * mm, height=46 * mm * 1177.0 / 1883.0)
    else:
        logo = Paragraph("LEAMSS", title_st)
    title_block = [Paragraph("Pathway Fit Scorecard", title_st),
                   Paragraph("We Value Consultants &nbsp;\u00b7&nbsp; MARA Registered &nbsp;\u00b7&nbsp; Trusted since 2014", sub_st)]
    htab = Table([[logo, title_block]], colWidths=[58 * mm, CONTENT_W - 58 * mm])
    htab.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(htab)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", color=GREEN, thickness=2))
    story.append(Spacer(1, 8))

    name = rec.get("full_name") or "Website Visitor"
    created = rec.get("created_at")
    created = created if isinstance(created, str) else (created.isoformat() if created else "")
    ref = (rec.get("id") or "")[:8].upper()
    story.append(Paragraph(f"Prepared for: <b>{name}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Date: {created[:10]} &nbsp;&nbsp;|&nbsp;&nbsp; Ref: {ref}", small_st))
    story.append(Spacer(1, 10))

    # ── Best Fit card ────────────────────────────────────────────────────────
    bf = [Paragraph(f'<font color="#D4633F"><b>\u2605 YOUR BEST FIT</b></font>', PS("bf", fontName="Helvetica-Bold", fontSize=9, textColor=ACCENT, leading=12)),
          Paragraph(f"<b>{top_name}</b>", PS("bfn", fontName="Helvetica-Bold", fontSize=13, textColor=GREEN, leading=16))]
    if result.get("overall_summary"):
        bf.append(Spacer(1, 3))
        bf.append(Paragraph(result["overall_summary"], body_st))
    story.append(card(bf, bg=CREAM, accent_left=ACCENT))
    story.append(Spacer(1, 10))

    # ── Ranked table ─────────────────────────────────────────────────────────
    hdr_st = PS("h", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white, leading=11)
    data = [[Paragraph("#", hdr_st), Paragraph("PATHWAY", hdr_st), Paragraph("SCORE", hdr_st), Paragraph("FIT", hdr_st)]]
    for i, (slug, p) in enumerate(ordered, 1):
        _, hexc = _TIER_PDF.get(p.get("tier"), ("\u2014", "#888888"))
        pname = [Paragraph(f"<b>{p.get('name', slug)}</b>", PS('pn', fontName='Helvetica-Bold', fontSize=9, textColor=INK, leading=11)),
                 Paragraph(p.get("country", ""), small_st)]
        sc = [Paragraph(f'<font color="{hexc}"><b>{p.get("score", 0)}</b></font><font color="#9aa5aa">/100</font>',
                        PS('sc', fontName='Helvetica-Bold', fontSize=10, leading=12)),
              Spacer(1, 2), score_bar(p.get("score", 0), hexc)]
        data.append([str(i), pname, sc, fit_tag(p.get("tier"))])
    table = Table(data, colWidths=[9 * mm, CONTENT_W - 9 * mm - 32 * mm - 26 * mm, 32 * mm, 26 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CREAM]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("TEXTCOLOR", (0, 1), (0, -1), MUTE),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
    ]))
    story.append(table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<b>Note:</b> This is a \u201cbest-fit\u201d ranking to help you shortlist the right pathway \u2014 it is "
        "<b>not</b> an official visa points / CRS score. Final eligibility depends on document verification, "
        "skills assessment and current policy. Please consult a LEAMSS expert before any decision.", disc_st))

    # ── Page 2 : About / Aim / Values / Protection / Reviews ─────────────────
    story.append(PageBreak())
    story.append(Paragraph("Our Aim", sect_st))
    story.append(HRFlowable(width="22%", color=ACCENT, thickness=2, spaceAfter=6))
    story.append(Paragraph(
        "At <b>LEAMSS</b>, our aim is simple \u2014 to help skilled Indian professionals and families migrate to "
        "<b>Australia, Canada and New Zealand</b> with complete transparency, speed and legal certainty. Since 2014 we "
        "have guided thousands of applicants, replacing guesswork and hidden costs with honest, MARA-registered advice "
        "and a clear, fixed-fee roadmap to permanent residence.", body_st))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Our Core Values", sect_st))
    story.append(HRFlowable(width="22%", color=ACCENT, thickness=2, spaceAfter=6))
    half = (CONTENT_W - 6 * mm) / 2.0
    vcards = [card([Paragraph(t, vtitle_st), Spacer(1, 2), Paragraph(d, vbody_st)], width=half, pad=8) for t, d in _VALUES]
    vrows = []
    for i in range(0, len(vcards), 2):
        vrows.append([vcards[i], vcards[i + 1] if i + 1 < len(vcards) else ""])
    vgrid = Table(vrows, colWidths=[half + 3 * mm, half + 3 * mm])
    vgrid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 6),
                               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(vgrid)
    story.append(Spacer(1, 10))

    # Protection policy — green highlight
    story.append(Paragraph("Your Protection", sect_st))
    story.append(HRFlowable(width="22%", color=ACCENT, thickness=2, spaceAfter=6))
    prot = [Paragraph('<font color="#FFFFFF"><b>\u2713 100% Refund Guarantee \u2014 in writing</b></font>',
                      PS('ph', fontName='Helvetica-Bold', fontSize=11, textColor=colors.white, leading=14)),
            Spacer(1, 3),
            Paragraph(
                "We stand behind our assessments. If your <b>skill assessment is negative</b>, or your visa is "
                "<b>rejected due to a LEAMSS-attributable error</b>, you receive a full refund of LEAMSS professional fees. "
                "The only exclusion is rejection caused by false information provided by the applicant (a legal disqualifier "
                "in any case). Full policy at leamss.com/privacy-policy.", bodyc_st)]
    story.append(card(prot, bg=GREEN, border=GREEN, pad=12))
    story.append(Spacer(1, 12))

    # Reviews
    story.append(Paragraph("What Our Clients Say", sect_st))
    story.append(HRFlowable(width="22%", color=ACCENT, thickness=2, spaceAfter=4))
    badge = Table([[stars(5, 10), Paragraph('<b>4.9 / 5</b>  <font color="#6B7B82">from 500+ Google reviews</font>',
                                            PS('bg', fontName='Helvetica', fontSize=9, textColor=INK, leading=13))]],
                  colWidths=[58, CONTENT_W - 58])
    badge.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(badge)
    story.append(Spacer(1, 6))
    rcards = []
    for nm, city, txt in _REVIEWS:
        rcards.append(card([stars(5, 8), Spacer(1, 3), Paragraph(f'\u201c{txt}\u201d', italic_st), Spacer(1, 3),
                            Paragraph(f'<b>{nm}</b>  <font color="#6B7B82">{city}</font>', small_st)],
                           bg=colors.white, width=half, pad=9))
    rrows = []
    for i in range(0, len(rcards), 2):
        rrows.append([rcards[i], rcards[i + 1] if i + 1 < len(rcards) else ""])
    rgrid = Table(rrows, colWidths=[half + 3 * mm, half + 3 * mm])
    rgrid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 6),
                               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(rgrid)
    story.append(Spacer(1, 12))

    # Final CTA
    cta = [Paragraph('<font color="#FFFFFF"><b>Ready for your verified, personalised plan?</b></font>',
                     PS('ct', fontName='Helvetica-Bold', fontSize=12, textColor=colors.white, leading=15)),
           Spacer(1, 3),
           Paragraph(f'<font color="#FFFFFF">Book a free consultation with a MARA-registered LEAMSS expert today. '
                     f'Call {_CONTACT["phone"]} &nbsp;\u00b7&nbsp; WhatsApp {_CONTACT["whatsapp"]} &nbsp;\u00b7&nbsp; {_CONTACT["website"]}</font>',
                     bodyc_st)]
    story.append(card(cta, bg=ACCENT, border=ACCENT, pad=12))

    def _on_page(canvas, _doc):
        canvas.saveState()
        canvas.setFillColor(GREEN)
        canvas.rect(0, 0, PAGE_W, 15 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(PAGE_W / 2.0, 8.5 * mm,
                                 f'{_CONTACT["website"]}   \u00b7   Phone {_CONTACT["phone"]}   \u00b7   WhatsApp {_CONTACT["whatsapp"]}   \u00b7   {_CONTACT["email"]}')
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(colors.HexColor("#BFD6CF"))
        canvas.drawCentredString(PAGE_W / 2.0, 4.5 * mm,
                                 f'\u00a9 {_CONTACT["legal"]}  \u00b7  MARA Registered  \u00b7  Indicative assessment only, generated automatically.')
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)


@router.get("/report/{score_id}")
async def download_scorecard_pdf(score_id: str):
    """Public — branded PDF of a scorecard (for the 'Download report' button)."""
    from fastapi.responses import FileResponse
    rec = await scores_col.find_one({"id": score_id}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Score not found")
    filename = os.path.join(REPORTS_DIR, f"scorecard_{score_id[:8]}_{uuid.uuid4().hex[:6]}.pdf")
    _generate_scorecard_pdf(rec, filename)
    return FileResponse(filename, media_type="application/pdf",
                        filename=f"LEAMSS_Pathway_Scorecard_{score_id[:8]}.pdf")
