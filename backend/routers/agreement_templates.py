"""Agreement Template Library — Country/Category/Variant-aware templates with auto-fill.

Core model:
  - agreement_templates: HTML body with {{placeholder}} syntax, country+category+variant key
  - pa_agreements: Per-PA generated agreement instance (auto-filled from template)
  - agreement_requests: Partner requests for new templates (admin review)

Endpoints:
  # Template management (admin-only writes, partner can list)
  GET    /api/agreement-templates                          — list (filter by country/category/variant)
  POST   /api/agreement-templates                          — create (admin)
  PUT    /api/agreement-templates/{tid}                    — edit (admin)
  DELETE /api/agreement-templates/{tid}                    — soft delete (admin)
  POST   /api/agreement-templates/{tid}/clone              — clone to new variant (admin)
  POST   /api/agreement-templates/upload-docx              — DOCX upload + AI placeholder detection (admin, future)

  # Partner requests for new templates
  POST   /api/agreement-templates/request                  — partner requests
  GET    /api/agreement-templates/requests                 — admin list
  PUT    /api/agreement-templates/requests/{rid}           — admin approve/reject

  # Per-PA agreement generation
  POST   /api/pa-agreements/generate                       — partner generates agreement for PA
  GET    /api/pa-agreements/pa/{pa_id}                     — list agreements for a PA
  GET    /api/pa-agreements/{aid}                          — get agreement (html body + placeholders)
  GET    /api/pa-agreements/{aid}/pdf                      — render as PDF
  POST   /api/pa-agreements/{aid}/sign                     — client signs (attaches canvas signature)
"""
import os
import uuid
import base64
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from jinja2 import Template as JinjaTemplate, StrictUndefined, UndefinedError, Environment
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

router = APIRouter(tags=["Agreement Templates"])

templates_col = db["agreement_templates"]
pa_agreements_col = db["pa_agreements"]
agreement_requests_col = db["agreement_template_requests"]
pa_col = db["pre_assessments"]
notifications_col = db["notifications"]
signatures_col = db["pa_signatures"]

AGREEMENT_PDF_DIR = "/app/uploads/agreements"
SIG_DIR = "/app/uploads/signatures"
os.makedirs(AGREEMENT_PDF_DIR, exist_ok=True)

jinja_env = Environment(autoescape=False)  # templates are admin-controlled HTML


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _admin_only(user):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def _partner_or_admin(user):
    if user.get("role") not in ("partner", "admin"):
        raise HTTPException(status_code=403, detail="Partner or admin only")


# ============================================================
# TEMPLATE CRUD
# ============================================================

class TemplateCreate(BaseModel):
    name: str
    country: str
    visa_category: str  # e.g. 'PR', 'Tourist/Visit', 'Student', 'Work'
    policy_variant: str  # e.g. 'Standard', 'Protection'
    body_html: str
    placeholders: List[str] = []  # optional; auto-detected if empty
    is_active: bool = True
    notes: str = ""


_AUTO_DETECT_PATTERN = None
def _detect_placeholders(body: str) -> List[str]:
    global _AUTO_DETECT_PATTERN
    if _AUTO_DETECT_PATTERN is None:
        import re
        _AUTO_DETECT_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
    return sorted(set(_AUTO_DETECT_PATTERN.findall(body or "")))


router_templates = APIRouter(prefix="/agreement-templates", tags=["Agreement Templates"])


@router_templates.get("")
async def list_templates(
    country: Optional[str] = None,
    visa_category: Optional[str] = None,
    policy_variant: Optional[str] = None,
    include_inactive: bool = False,
    current_user: dict = Depends(get_current_user),
):
    _partner_or_admin(current_user)
    q = {}
    if not include_inactive:
        q["is_active"] = True
    if country:
        q["country"] = country
    if visa_category:
        q["visa_category"] = visa_category
    if policy_variant:
        q["policy_variant"] = policy_variant
    items = await templates_col.find(q, {"_id": 0, "body_html": 0}).sort("created_at", -1).to_list(500)
    for it in items:
        for k in ("created_at", "updated_at"):
            if k in it and hasattr(it[k], "isoformat"):
                it[k] = it[k].isoformat()
    return {"count": len(items), "items": items}


@router_templates.get("/meta/options")
async def templates_meta(current_user: dict = Depends(get_current_user)):
    """Return distinct country/category/variant values for drop-downs."""
    _partner_or_admin(current_user)
    countries = await templates_col.distinct("country", {"is_active": True})
    categories = await templates_col.distinct("visa_category", {"is_active": True})
    variants = await templates_col.distinct("policy_variant", {"is_active": True})
    return {"countries": sorted(countries), "categories": sorted(categories), "variants": sorted(variants)}


@router_templates.get("/{tid}")
async def get_template(tid: str, current_user: dict = Depends(get_current_user)):
    _partner_or_admin(current_user)
    t = await templates_col.find_one({"id": tid}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    for k in ("created_at", "updated_at"):
        if k in t and hasattr(t[k], "isoformat"):
            t[k] = t[k].isoformat()
    return t


@router_templates.post("")
async def create_template(data: TemplateCreate, current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    placeholders = data.placeholders or _detect_placeholders(data.body_html)
    tid = str(uuid.uuid4())
    rec = {
        "id": tid, "name": data.name.strip(),
        "country": data.country.strip(),
        "visa_category": data.visa_category.strip(),
        "policy_variant": data.policy_variant.strip(),
        "body_html": data.body_html,
        "placeholders": placeholders,
        "is_active": data.is_active, "notes": data.notes,
        "version": 1,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await templates_col.insert_one(rec)
    await log_activity(current_user["id"], current_user.get("name", ""), "template_create",
                       "agreement_template", tid, f"Created template: {data.name} ({data.country}/{data.visa_category}/{data.policy_variant})")
    rec.pop("_id", None)
    for k in ("created_at", "updated_at"):
        rec[k] = rec[k].isoformat()
    return rec


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    visa_category: Optional[str] = None
    policy_variant: Optional[str] = None
    body_html: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


@router_templates.put("/{tid}")
async def update_template(tid: str, data: TemplateUpdate, current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    t = await templates_col.find_one({"id": tid})
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    update = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "body_html" in update:
        update["placeholders"] = _detect_placeholders(update["body_html"])
    update["updated_at"] = datetime.now(timezone.utc)
    update["version"] = (t.get("version") or 1) + 1
    await templates_col.update_one({"id": tid}, {"$set": update})
    return {"ok": True, "version": update["version"]}


@router_templates.delete("/{tid}")
async def delete_template(tid: str, current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    await templates_col.update_one({"id": tid}, {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}})
    return {"ok": True}


class CloneBody(BaseModel):
    new_name: str
    new_policy_variant: Optional[str] = None
    new_country: Optional[str] = None
    new_visa_category: Optional[str] = None


@router_templates.post("/{tid}/clone")
async def clone_template(tid: str, body: CloneBody, current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    t = await templates_col.find_one({"id": tid}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    new_id = str(uuid.uuid4())
    clone = dict(t)
    clone["id"] = new_id
    clone["name"] = body.new_name
    if body.new_policy_variant: clone["policy_variant"] = body.new_policy_variant
    if body.new_country: clone["country"] = body.new_country
    if body.new_visa_category: clone["visa_category"] = body.new_visa_category
    clone["version"] = 1
    clone["created_by"] = current_user["id"]
    clone["created_by_name"] = current_user.get("name", "")
    clone["created_at"] = datetime.now(timezone.utc)
    clone["updated_at"] = datetime.now(timezone.utc)
    clone["notes"] = f"Cloned from {t['name']}"
    await templates_col.insert_one(clone)
    clone.pop("_id", None)  # Remove MongoDB _id before returning
    for k in ("created_at", "updated_at"):
        clone[k] = clone[k].isoformat()
    return clone


# ============================================================
# DOCX UPLOAD + AI PLACEHOLDER DETECTION
# ============================================================

from fastapi import UploadFile, File, Form

@router_templates.post("/upload-docx")
async def upload_docx_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    country: str = Form(...),
    visa_category: str = Form(...),
    policy_variant: str = Form("Standard"),
    current_user: dict = Depends(get_current_user),
):
    """Upload a DOCX, extract text, optionally run AI placeholder detection."""
    _admin_only(current_user)
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files supported")
    try:
        from docx import Document
    except ImportError:
        raise HTTPException(status_code=500, detail="python-docx not installed")

    tmp_path = f"/tmp/{uuid.uuid4().hex}.docx"
    with open(tmp_path, "wb") as fp:
        fp.write(await file.read())

    doc = Document(tmp_path)
    html_parts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            html_parts.append("<br/>")
            continue
        style = (para.style.name or "").lower() if para.style else ""
        if "heading 1" in style or "title" in style:
            html_parts.append(f"<h2>{text}</h2>")
        elif "heading 2" in style:
            html_parts.append(f"<h3>{text}</h3>")
        elif "heading" in style:
            html_parts.append(f"<h4>{text}</h4>")
        else:
            # Basic bold detection
            runs_html = []
            for run in para.runs:
                t = run.text
                if not t:
                    continue
                if run.bold:
                    t = f"<strong>{t}</strong>"
                if run.italic:
                    t = f"<em>{t}</em>"
                runs_html.append(t)
            html_parts.append(f"<p>{''.join(runs_html) or text}</p>")
    body_html = "\n".join(html_parts)

    try:
        os.remove(tmp_path)
    except Exception:
        pass

    placeholders = _detect_placeholders(body_html)
    # Draft template — admin must review & save
    return {
        "ok": True,
        "draft": {
            "name": name, "country": country,
            "visa_category": visa_category, "policy_variant": policy_variant,
            "body_html": body_html,
            "placeholders": placeholders,
            "notes": f"Auto-extracted from {file.filename}",
        },
    }


# ============================================================
# PARTNER REQUESTS (for new templates)
# ============================================================

class RequestCreate(BaseModel):
    country: str
    visa_category: str
    policy_variant: str = "Standard"
    notes: str = ""


@router_templates.post("/request")
async def partner_request_template(data: RequestCreate, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "partner":
        raise HTTPException(status_code=403, detail="Partners only")
    rid = str(uuid.uuid4())
    rec = {
        "id": rid,
        "country": data.country, "visa_category": data.visa_category,
        "policy_variant": data.policy_variant, "notes": data.notes,
        "status": "pending",
        "requested_by": current_user["id"], "requested_by_name": current_user.get("name", ""),
        "requested_at": datetime.now(timezone.utc),
    }
    await agreement_requests_col.insert_one(rec)
    rec.pop("_id", None)
    rec["requested_at"] = rec["requested_at"].isoformat()
    # Notify all admins (simple: notify user_id='admin_broadcast' — actually emit per admin)
    admins = await db["users"].find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(50)
    for a in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": a["id"],
            "title": "New Template Request",
            "message": f"{current_user.get('name')} requested: {data.country} / {data.visa_category} / {data.policy_variant}",
            "type": "template_request", "read": False,
            "created_at": datetime.now(timezone.utc),
        })
    return rec


@router_templates.get("/requests/list")
async def list_requests(current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    items = await agreement_requests_col.find({}, {"_id": 0}).sort("requested_at", -1).to_list(200)
    for i in items:
        if hasattr(i.get("requested_at"), "isoformat"):
            i["requested_at"] = i["requested_at"].isoformat()
    return items


# ============================================================
# PER-PA AGREEMENT GENERATION (partner flow)
# ============================================================

router_pa_agree = APIRouter(prefix="/pa-agreements", tags=["Per-PA Agreements"])


class GenerateBody(BaseModel):
    pa_id: str
    template_id: str
    variables: dict  # user-filled map; keys match placeholders


def _auto_vars_from_pa(pa: dict) -> dict:
    """Build best-effort auto variables from a pre-assessment doc."""
    today = datetime.now()
    return {
        "client_name": pa.get("client_name") or "",
        "client_given_name": (pa.get("client_name") or "").split(" ")[0],
        "client_family_name": " ".join((pa.get("client_name") or "").split(" ")[1:]),
        "client_email": pa.get("client_email") or "",
        "client_phone": pa.get("client_mobile") or pa.get("client_phone") or "",
        "client_dob": pa.get("client_dob") or pa.get("date_of_birth") or "",
        "client_age": str(pa.get("client_age") or ""),
        "client_address": pa.get("client_address") or "",
        "client_passport": pa.get("passport_number") or "",
        "country": pa.get("country") or "",
        "service_type": pa.get("service_type") or "",
        "product_name": pa.get("product_name") or "",
        "agreement_date": today.strftime("%d/%m/%Y"),
        "agreement_year": str(today.year),
        "partner_name": pa.get("partner_name") or "",
        "agent_name": pa.get("partner_name") or "",
        "pa_number": pa.get("pa_number") or "",
        "pre_assessment_fee": str(pa.get("pre_assessment_fee") or 5100),
        "proposal_base_fee": str(pa.get("proposal_base_fee") or ""),
        "proposal_final_amount": str(pa.get("proposal_fee") or ""),
        "promo_code": pa.get("proposal_promo_code") or "",
        "milestone_1_amount": "",  # partner fills
        "milestone_2_amount": "",
        "milestone_3_amount": "",
        "milestone_1_date": "",
        "milestone_2_date": "",
        "milestone_3_date": "",
        "payment_mode": pa.get("proposal_payment_method") or "Lumpsum",
        "leamss_agent_email": "migration@leamss.com",
    }


@router_pa_agree.get("/auto-vars/{pa_id}")
async def auto_vars(pa_id: str, current_user: dict = Depends(get_current_user)):
    _partner_or_admin(current_user)
    pa = await pa_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="PA not found")
    if current_user["role"] == "partner" and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your PA")
    return {"variables": _auto_vars_from_pa(pa)}


@router_pa_agree.post("/generate")
async def generate_agreement(body: GenerateBody, current_user: dict = Depends(get_current_user)):
    _partner_or_admin(current_user)
    pa = await pa_col.find_one({"id": body.pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="PA not found")
    if current_user["role"] == "partner" and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your PA")
    tpl = await templates_col.find_one({"id": body.template_id, "is_active": True}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    # Render HTML via Jinja (loose undefined: unknown vars become empty)
    auto = _auto_vars_from_pa(pa)
    merged = {**auto, **(body.variables or {})}
    try:
        tpl_obj = jinja_env.from_string(tpl["body_html"])
        rendered_html = tpl_obj.render(**merged)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Template render error: {str(e)[:120]}")

    aid = str(uuid.uuid4())
    ref_id = f"AGR-{(pa.get('pa_number') or '')}-{aid[:6].upper()}"
    agreement = {
        "id": aid,
        "reference_id": ref_id,
        "pa_id": body.pa_id, "pa_number": pa.get("pa_number"),
        "template_id": body.template_id, "template_name": tpl["name"],
        "country": tpl["country"], "visa_category": tpl["visa_category"],
        "policy_variant": tpl["policy_variant"],
        "variables_used": merged,
        "rendered_html": rendered_html,
        "status": "pending_signature",  # pending_signature | signed | voided
        "signature_id": None,
        "client_name": pa.get("client_name"),
        "client_email": pa.get("client_email"),
        "client_user_id": pa.get("client_user_id"),
        "partner_id": pa.get("partner_id"),
        "partner_name": pa.get("partner_name"),
        "generated_by": current_user["id"],
        "generated_by_name": current_user.get("name", ""),
        "generated_at": datetime.now(timezone.utc),
    }
    await pa_agreements_col.insert_one(agreement)

    # Mark PA as having active agreement (handy for UI)
    await pa_col.update_one({"id": body.pa_id}, {"$set": {
        "active_agreement_id": aid,
        "active_agreement_ref": ref_id,
        "active_agreement_status": "pending_signature",
    }})

    # Notify client in-app
    if pa.get("client_user_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["client_user_id"],
            "title": "Service Agreement Ready to Sign",
            "message": f"Your {tpl['country']} {tpl['visa_category']} agreement is ready. Reference: {ref_id}",
            "type": "agreement_ready", "read": False,
            "created_at": datetime.now(timezone.utc),
        })
    await log_activity(current_user["id"], current_user.get("name", ""), "agreement_generated",
                       "pa_agreement", aid, f"Generated {tpl['name']} for PA {pa.get('pa_number')}")

    agreement.pop("_id", None)
    agreement["generated_at"] = agreement["generated_at"].isoformat()
    return agreement


@router_pa_agree.get("/pa/{pa_id}")
async def list_pa_agreements(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await pa_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="PA not found")
    role = current_user.get("role")
    if role == "partner" and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your PA")
    if role == "client":
        is_client = (pa.get("client_user_id") == current_user["id"]) or \
                    ((pa.get("client_email") or "").lower() == (current_user.get("email") or "").lower())
        if not is_client:
            raise HTTPException(status_code=403, detail="Not your PA")
    items = await pa_agreements_col.find({"pa_id": pa_id}, {"_id": 0, "rendered_html": 0}).sort("generated_at", -1).to_list(50)
    for i in items:
        if hasattr(i.get("generated_at"), "isoformat"):
            i["generated_at"] = i["generated_at"].isoformat()
        if hasattr(i.get("signed_at"), "isoformat"):
            i["signed_at"] = i["signed_at"].isoformat()
    return items


@router_pa_agree.get("/{aid}")
async def get_agreement(aid: str, current_user: dict = Depends(get_current_user)):
    a = await pa_agreements_col.find_one({"id": aid}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Agreement not found")
    role = current_user.get("role")
    if role == "partner" and a.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if role == "client":
        if a.get("client_user_id") != current_user["id"] and (a.get("client_email") or "").lower() != (current_user.get("email") or "").lower():
            raise HTTPException(status_code=403, detail="Not authorized")
    for k in ("generated_at", "signed_at"):
        if k in a and hasattr(a[k], "isoformat"):
            a[k] = a[k].isoformat()
    return a


class SignBody(BaseModel):
    signature_data_url: str
    typed_name: str
    consent_text: str = ""


@router_pa_agree.post("/{aid}/sign")
async def sign_agreement(aid: str, body: SignBody, request: Request, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")
    a = await pa_agreements_col.find_one({"id": aid}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Agreement not found")
    if a.get("client_user_id") != current_user["id"] and (a.get("client_email") or "").lower() != (current_user.get("email") or "").lower():
        raise HTTPException(status_code=403, detail="Not your agreement")
    if a.get("status") == "signed":
        raise HTTPException(status_code=400, detail="Already signed")
    if not body.signature_data_url.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Invalid signature format")

    try:
        b64 = body.signature_data_url.split(",", 1)[1]
        raw = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Corrupt signature data")

    os.makedirs(SIG_DIR, exist_ok=True)
    fname = f"agr_sig_{aid}_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(SIG_DIR, fname)
    with open(path, "wb") as fp:
        fp.write(raw)

    ip = request.client.host if request.client else ""
    sig_id = str(uuid.uuid4())
    sig_rec = {
        "id": sig_id,
        "pre_assessment_id": a["pa_id"],
        "agreement_id": aid,
        "user_id": current_user["id"],
        "user_email": current_user.get("email"),
        "typed_name": body.typed_name,
        "consent_text": body.consent_text or f"I electronically sign agreement {a['reference_id']}",
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent", "")[:250],
        "file_path": path,
        "file_size": len(raw),
        "signed_at": datetime.now(timezone.utc),
    }
    await signatures_col.insert_one(sig_rec)

    await pa_agreements_col.update_one({"id": aid}, {"$set": {
        "status": "signed",
        "signature_id": sig_id,
        "signed_at": datetime.now(timezone.utc),
        "signed_by_typed_name": body.typed_name,
        "signed_ip": ip,
    }})
    await pa_col.update_one({"id": a["pa_id"]}, {"$set": {
        "active_agreement_status": "signed",
        "agreement_signed": True,
        "agreement_signed_at": datetime.now(timezone.utc),
        "agreement_signature_id": sig_id,
    }})

    # Notify partner + admins
    notif_targets = []
    if a.get("partner_id"):
        notif_targets.append(a["partner_id"])
    admins = await db["users"].find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(20)
    notif_targets.extend([x["id"] for x in admins])
    for uid in notif_targets:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": uid,
            "title": "Agreement Signed",
            "message": f"{a.get('client_name')} signed the {a.get('country')} agreement ({a.get('reference_id')})",
            "type": "agreement_signed", "read": False,
            "created_at": datetime.now(timezone.utc),
        })

    await log_activity(current_user["id"], current_user.get("name", ""), "agreement_signed",
                       "pa_agreement", aid, f"Client signed {a.get('reference_id')}")

    return {"ok": True, "signature_id": sig_id, "signed_at": sig_rec["signed_at"].isoformat()}


@router_pa_agree.get("/{aid}/pdf")
async def agreement_pdf(aid: str, current_user: dict = Depends(get_current_user)):
    a = await pa_agreements_col.find_one({"id": aid}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Agreement not found")
    role = current_user.get("role")
    if role == "partner" and a.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if role == "client":
        if a.get("client_user_id") != current_user["id"] and (a.get("client_email") or "").lower() != (current_user.get("email") or "").lower():
            raise HTTPException(status_code=403, detail="Not authorized")

    path = os.path.join(AGREEMENT_PDF_DIR, f"agreement_{aid}.pdf")
    # Always regenerate to include latest signature if any
    _render_agreement_pdf(a, path)
    return FileResponse(path, media_type="application/pdf",
                        filename=f"Agreement_{a.get('reference_id', aid[:8])}.pdf")


def _render_agreement_pdf(a: dict, out_path: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from html.parser import HTMLParser

    doc = SimpleDocTemplate(out_path, pagesize=A4, topMargin=36, bottomMargin=36, leftMargin=48, rightMargin=48)
    styles = getSampleStyleSheet()
    brand = colors.HexColor("#2a777a")
    title_style = ParagraphStyle("t", parent=styles["Heading1"], fontSize=20, textColor=brand, spaceAfter=10)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14, textColor=brand, spaceAfter=6, spaceBefore=10)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], fontSize=12, textColor=colors.HexColor("#1e293b"), spaceAfter=4, spaceBefore=8)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10.5, leading=16, alignment=4)  # justify
    small = ParagraphStyle("s", parent=styles["Normal"], fontSize=9, textColor=colors.grey)

    elems = []

    # Header
    elems.append(Paragraph("LEAMSS Immigration Services", title_style))
    elems.append(Paragraph(f"{a.get('country', '')} — {a.get('visa_category', '')} — {a.get('policy_variant', '')}", h3))
    elems.append(Paragraph(f"Reference: <b>{a.get('reference_id')}</b> &nbsp;|&nbsp; Generated: {datetime.now().strftime('%d %b %Y')}", small))
    elems.append(Spacer(1, 12))

    # Parse the rendered HTML body into paragraphs
    class TextCollector(HTMLParser):
        def __init__(self):
            super().__init__()
            self.buf = []
            self.current = []
            self.tag_stack = []
        def handle_starttag(self, tag, attrs):
            self.tag_stack.append(tag)
            if tag in ("h1", "h2", "h3", "h4", "p"):
                if self.current:
                    self.buf.append(("p", " ".join(self.current).strip()))
                    self.current = []
            if tag == "br":
                self.buf.append(("br", ""))
            if tag == "strong" or tag == "b":
                self.current.append("<b>")
            if tag == "em" or tag == "i":
                self.current.append("<i>")
        def handle_endtag(self, tag):
            if tag == "strong" or tag == "b":
                self.current.append("</b>")
            if tag == "em" or tag == "i":
                self.current.append("</i>")
            if tag in ("h1", "h2", "h3", "h4", "p"):
                text = " ".join(self.current).strip()
                if text:
                    self.buf.append((tag, text))
                self.current = []
            if self.tag_stack and self.tag_stack[-1] == tag:
                self.tag_stack.pop()
        def handle_data(self, data):
            self.current.append(data)

    parser = TextCollector()
    parser.feed(a.get("rendered_html") or "")
    if parser.current:
        text = " ".join(parser.current).strip()
        if text:
            parser.buf.append(("p", text))

    for kind, text in parser.buf:
        try:
            if kind in ("h1", "h2"):
                elems.append(Paragraph(text, h2))
            elif kind in ("h3", "h4"):
                elems.append(Paragraph(text, h3))
            elif kind == "br":
                elems.append(Spacer(1, 6))
            else:
                elems.append(Paragraph(text, body))
                elems.append(Spacer(1, 3))
        except Exception:
            # Skip malformed paragraphs
            continue

    # Signature block
    elems.append(Spacer(1, 20))
    elems.append(Paragraph("— Signatures —", h2))
    sig_rows = []
    client_name = a.get("signed_by_typed_name") or a.get("client_name") or "Client"
    if a.get("status") == "signed":
        # Embed signature image
        sig = None
        if a.get("signature_id"):
            # best-effort fetch from file system via id pattern
            import glob
            found = glob.glob(f"/app/uploads/signatures/agr_sig_{a['id']}_*.png")
            if found:
                sig = Image(found[0], width=160, height=60)
        left = [Paragraph("<b>Client Signature</b>", body)]
        if sig: left.append(sig)
        left.append(Paragraph(client_name, body))
        left.append(Paragraph(f"Signed: {a.get('signed_at') or ''}", small))
        left.append(Paragraph(f"IP: {a.get('signed_ip') or ''}", small))
        sig_rows.append([left, [Paragraph("<b>LEAMSS (Authorized Signatory)</b>", body), Paragraph("__________________________", body), Paragraph("For Ladhani Education &amp; Migration Services Pvt Ltd", small)]])
    else:
        sig_rows.append([[Paragraph("<b>Client Signature</b>", body), Paragraph("__________________________", body), Paragraph(client_name, body)], [Paragraph("<b>LEAMSS (Authorized Signatory)</b>", body), Paragraph("__________________________", body), Paragraph("For Ladhani Education &amp; Migration Services Pvt Ltd", small)]])

    sig_table = Table(sig_rows, colWidths=[250, 250])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elems.append(sig_table)

    elems.append(Spacer(1, 20))
    elems.append(Paragraph(
        f"<font color='#94a3b8'>Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} · Reference {a.get('reference_id')} · "
        f"This is a system-generated digital agreement.</font>", small))

    doc.build(elems)


# Export the three routers so server can include them
router = router_templates
pa_agreements_router = router_pa_agree
