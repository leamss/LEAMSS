"""Phase D · Intelligence Layer.

Endpoints:
  GET  /api/intelligence/dropoff-leads        — stuck PAs with nudge suggestions (partner/admin view)
  POST /api/intelligence/nudge/{pa_id}        — send mock nudge (email + in-app)
  GET  /api/intelligence/checklist/{pa_id}    — smart document checklist per country/visa
  GET  /api/intelligence/risk/{pa_id}         — rule-based risk score
"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

router = APIRouter(prefix="/intelligence", tags=["Intelligence Layer"])

pa_col = db["pre_assessments"]
pa_docs_col = db["pre_assessment_documents"]
notifications_col = db["notifications"]
nudges_col = db["pa_nudges"]

# Stage → max idle days before flagged as drop-off
STAGE_SLA_DAYS = {
    "new": 2,
    "payment_pending": 3,
    "payment_received": 3,
    "partner_review": 2,
    "under_review": 4,
    "approved": 3,
    "proposal_sent": 4,
    "proposal_paid": 2,
    "awaiting_final_approval": 3,
}


def _days_since(dt):
    if not dt:
        return 0
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return 0
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (now - dt).days)


@router.get("/dropoff-leads")
async def dropoff_leads(current_user: dict = Depends(get_current_user)):
    """Detect leads stuck at the same stage beyond SLA days."""
    query = {}
    if current_user["role"] == "partner":
        query["partner_id"] = current_user["id"]
    elif current_user["role"] not in ("admin", "case_manager"):
        raise HTTPException(status_code=403, detail="Not authorized")

    items = await pa_col.find(query, {"_id": 0}).to_list(1000)
    flagged = []
    for pa in items:
        stage = pa.get("stage")
        sla = STAGE_SLA_DAYS.get(stage)
        if not sla:
            continue
        idle = _days_since(pa.get("updated_at"))
        if idle >= sla:
            last_nudge = await nudges_col.find_one({"pre_assessment_id": pa["id"]}, {"_id": 0}, sort=[("sent_at", -1)])
            flagged.append({
                "id": pa["id"],
                "pa_number": pa.get("pa_number"),
                "client_name": pa.get("client_name"),
                "client_email": pa.get("client_email"),
                "country": pa.get("country"),
                "service_type": pa.get("service_type"),
                "stage": stage,
                "idle_days": idle,
                "sla_days": sla,
                "severity": "high" if idle >= sla * 2 else "medium",
                "last_nudge_at": last_nudge.get("sent_at").isoformat() if last_nudge and hasattr(last_nudge.get("sent_at"), "isoformat") else (last_nudge.get("sent_at") if last_nudge else None),
                "suggested_action": _suggest_action(stage),
            })
    flagged.sort(key=lambda x: x["idle_days"], reverse=True)
    return {"count": len(flagged), "items": flagged}


def _suggest_action(stage):
    return {
        "new": "Send payment link to client now",
        "payment_pending": "Remind client to complete ₹5,100 payment",
        "payment_received": "Ask client to upload documents",
        "partner_review": "Review client docs and forward to Admin",
        "under_review": "Escalate to Admin — pending approval",
        "approved": "Send service proposal now",
        "proposal_sent": "Nudge client to accept + pay main fee",
        "proposal_paid": "Upload receipt + agreement to submit for final approval",
        "awaiting_final_approval": "Ping Admin for final approval",
    }.get(stage, "Review lead status")


@router.post("/nudge/{pa_id}")
async def nudge_lead(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await pa_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    # Auth — partner-owner, admin, CM
    if current_user["role"] == "partner" and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your lead")

    nudge = {
        "id": str(uuid.uuid4()),
        "pre_assessment_id": pa_id,
        "stage": pa.get("stage"),
        "channel": "email",  # mock
        "sent_by": current_user["id"],
        "sent_by_name": current_user.get("name", ""),
        "sent_at": datetime.now(timezone.utc),
        "mode": "mock",
    }
    await nudges_col.insert_one(nudge)
    nudge.pop("_id", None)
    nudge["sent_at"] = nudge["sent_at"].isoformat()

    # In-app nudge to client if they have account
    if pa.get("client_user_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["client_user_id"],
            "title": "Reminder",
            "message": f"Hey {pa.get('client_name', '')}, {_suggest_action(pa.get('stage'))}. Please open your portal.",
            "type": "nudge", "read": False,
            "created_at": datetime.now(timezone.utc),
        })

    await log_activity(current_user["id"], current_user.get("name", ""), "nudge_lead",
                       "pre_assessment", pa_id, f"Nudge sent at stage={pa.get('stage')} (MOCK email)")
    return {"ok": True, "mode": "mock", "nudge": nudge}


# ===================== SMART CHECKLIST =====================

_CHECKLIST_TEMPLATES = {
    "canada_express_entry": [
        {"name": "Passport (first + last page)", "category": "identity", "required": True},
        {"name": "IELTS / CELPIP score report", "category": "language", "required": True},
        {"name": "Educational Credential Assessment (ECA)", "category": "education", "required": True},
        {"name": "All Degree Certificates + Transcripts", "category": "education", "required": True},
        {"name": "Work Experience Reference Letters (with NOC)", "category": "experience", "required": True},
        {"name": "Proof of Funds (6 months bank statement)", "category": "financial", "required": True},
        {"name": "Police Clearance Certificate", "category": "legal", "required": True},
        {"name": "Medical Examination Report (after ITA)", "category": "medical", "required": False},
        {"name": "Photographs (2 passport-size)", "category": "identity", "required": True},
    ],
    "australia_skilled": [
        {"name": "Passport", "category": "identity", "required": True},
        {"name": "PTE / IELTS score", "category": "language", "required": True},
        {"name": "Skills Assessment (ACS/VETASSESS)", "category": "skills", "required": True},
        {"name": "Degree + Transcripts", "category": "education", "required": True},
        {"name": "Work Reference Letters", "category": "experience", "required": True},
        {"name": "PCC (Police Check)", "category": "legal", "required": True},
        {"name": "Medical Exam Report", "category": "medical", "required": False},
    ],
    "uk_work_visa": [
        {"name": "Passport", "category": "identity", "required": True},
        {"name": "Certificate of Sponsorship (CoS)", "category": "employer", "required": True},
        {"name": "IELTS UKVI", "category": "language", "required": True},
        {"name": "Degree Certificate", "category": "education", "required": True},
        {"name": "TB Test Certificate (if applicable)", "category": "medical", "required": False},
        {"name": "Proof of Funds (28 days statement)", "category": "financial", "required": True},
    ],
    "usa_h1b": [
        {"name": "Passport", "category": "identity", "required": True},
        {"name": "Degree + Transcripts", "category": "education", "required": True},
        {"name": "Experience Letters", "category": "experience", "required": True},
        {"name": "I-797 Approval Notice (if applicable)", "category": "legal", "required": False},
        {"name": "Visa Application Photo (US spec)", "category": "identity", "required": True},
    ],
    "default": [
        {"name": "Passport (bio page)", "category": "identity", "required": True},
        {"name": "Language Proficiency Test", "category": "language", "required": True},
        {"name": "Highest Degree Certificate", "category": "education", "required": True},
        {"name": "Work Experience Letters", "category": "experience", "required": True},
        {"name": "Bank Statement (Proof of Funds)", "category": "financial", "required": True},
        {"name": "Police Clearance Certificate", "category": "legal", "required": True},
    ],
}


def _pick_template(pa: dict) -> str:
    c = (pa.get("country") or "").lower()
    s = (pa.get("service_type") or "").lower()
    if "canada" in c and ("express" in s or "pr" in s):
        return "canada_express_entry"
    if "australia" in c:
        return "australia_skilled"
    if "uk" in c or "united kingdom" in c:
        return "uk_work_visa"
    if "usa" in c or "us" in c or "united states" in c:
        return "usa_h1b"
    return "default"


@router.get("/checklist/{pa_id}")
async def smart_checklist(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await pa_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    template_key = _pick_template(pa)
    items = list(_CHECKLIST_TEMPLATES[template_key])
    # Figure out which docs client has uploaded (by category hint in document_type)
    uploaded = await pa_docs_col.find({"pre_assessment_id": pa_id}, {"_id": 0}).to_list(200)
    uploaded_types = [(d.get("document_type") or "").lower() for d in uploaded]
    # Heuristic match: category or first-word of name in uploaded_types
    for it in items:
        cat = it["category"].lower()
        name_word = it["name"].split()[0].lower()
        it["uploaded"] = any(cat in u or name_word in u for u in uploaded_types)
    total = len(items)
    done = sum(1 for it in items if it["uploaded"])
    required_total = sum(1 for it in items if it["required"])
    required_done = sum(1 for it in items if it["required"] and it["uploaded"])
    completion = round((done / total * 100) if total else 0, 1)
    return {
        "template": template_key,
        "country": pa.get("country"),
        "service_type": pa.get("service_type"),
        "items": items,
        "stats": {
            "total": total, "done": done,
            "required_total": required_total, "required_done": required_done,
            "completion_pct": completion,
        },
    }


# ===================== RISK PREDICTION =====================

@router.get("/risk/{pa_id}")
async def risk_score(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await pa_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    score = 50.0  # baseline
    factors = []

    # Positive factors
    age = int(pa.get("client_age") or 0)
    if 25 <= age <= 35:
        score += 15
        factors.append({"+": "Prime age band (25-35)", "delta": 15})
    elif 35 < age <= 45:
        score += 5
        factors.append({"+": "Moderate age band (36-45)", "delta": 5})
    elif age > 45:
        score -= 10
        factors.append({"-": "Age above 45 reduces eligibility", "delta": -10})

    edu = (pa.get("education") or "").lower()
    if "masters" in edu or "phd" in edu or "doctorate" in edu:
        score += 15
        factors.append({"+": "Advanced degree (Masters/PhD)", "delta": 15})
    elif "bachelor" in edu or "degree" in edu:
        score += 8
        factors.append({"+": "Bachelor's degree", "delta": 8})

    exp = (pa.get("work_experience") or "").lower()
    if any(t in exp for t in ["5+", "6 ", "7 ", "8 ", "9 ", "10 ", "senior", "lead"]):
        score += 12
        factors.append({"+": "5+ years of work experience", "delta": 12})

    # Stage-based flags (pipeline health)
    if pa.get("fee_payment_status") == "paid":
        score += 8
        factors.append({"+": "Pre-assessment fee paid", "delta": 8})

    docs_count = await pa_docs_col.count_documents({"pre_assessment_id": pa_id})
    if docs_count >= 5:
        score += 8
        factors.append({"+": f"{docs_count} documents uploaded", "delta": 8})
    elif docs_count == 0 and pa.get("stage") not in ("new", "payment_pending"):
        score -= 15
        factors.append({"-": "No documents uploaded yet", "delta": -15})

    # Idle penalty
    idle = _days_since(pa.get("updated_at"))
    sla = STAGE_SLA_DAYS.get(pa.get("stage"), 5)
    if idle > sla * 2:
        score -= 15
        factors.append({"-": f"Stuck {idle} days at '{pa.get('stage')}'", "delta": -15})
    elif idle > sla:
        score -= 7
        factors.append({"-": f"Idle {idle} days", "delta": -7})

    # Rejected history
    if pa.get("admin_decision") == "rejected":
        score -= 25
        factors.append({"-": "Previously rejected", "delta": -25})

    score = max(0, min(100, round(score, 1)))
    if score >= 75:
        label, color = "High Conversion Likelihood", "green"
    elif score >= 50:
        label, color = "Moderate", "amber"
    else:
        label, color = "At Risk", "red"

    return {
        "pa_id": pa_id, "score": score, "label": label, "color": color, "factors": factors,
    }
