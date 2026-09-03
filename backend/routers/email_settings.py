"""Email Settings — admin-editable content for the client report email.

Stores a single settings doc (id='global') plus binary assets (SLA PDF, payment QR,
optional offer banner) in a GridFS bucket. The report email template reads these.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pydantic import BaseModel

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/email-settings", tags=["email-settings"])

SETTINGS = db["email_settings"]
_assets = AsyncIOMotorGridFSBucket(db, bucket_name="email_assets")

ADMIN_ROLES = {"admin", "admin_owner"}


def _can(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or []) or role in (
        "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "partner",
    )


DEFAULTS: Dict[str, Any] = {
    "id": "global",
    "subject_template": "Congratulations! Your Australia Migration Profile Evaluation is Positive — {name}",
    "outcome_title": "Your Australia Migration Profile Pre-Assessment Evaluation Outcome is Positive",
    "body_message": (
        "Please find below your Pre-Assessment report and our Service Level Agreement attached.\n\n"
        "We are delighted to inform you that our expert migration team has successfully completed your "
        "detailed Australia migration profile evaluation. After carefully reviewing your qualification, "
        "professional experience, skills and migration factors, we are pleased to share that your profile "
        "evaluation outcome is Positive.\n\n"
        "This is an important milestone towards your Australian migration journey. With the right strategy "
        "and professional guidance, you can now move forward to the next stage with confidence.\n\n"
        "Your Next Step: Complete Your Australia Migration Process with LEAMSS. Our experienced team will "
        "support you across migration strategy, ANZSCO guidance, skills assessment, EOI preparation, state "
        "nomination strategy, visa documentation and dedicated case management."
    ),
    "services_list": [
        "End-to-End Documentation Assistance",
        "Dedicated Case Manager Support",
        "Skills Assessment Assistance",
        "Migration Strategy Consultation",
        "PR Application Guidance",
        "Application Review & Process Management",
        "Regular Progress Updates & Transparent Communication",
        "Flexible Payment Assistance",
        "100% Refund Policy* (As per applicable Terms & Conditions)",
    ],
    "gov_charges": [
        {"label": "Principal Applicant", "amount": "AUD 6,140"},
        {"label": "Adult Secondary Applicant", "amount": "AUD 3,070"},
        {"label": "Child Applicant (Under 18 Years)", "amount": "AUD 1,535"},
    ],
    # Offer
    "offer_enabled": True,
    "offer_badge": "80th Independence Day Special Offer",
    "offer_title": "Independence Day Special Offer — Limited Slots",
    "offer_regular_fee": "₹1,55,000 + 18% GST",
    "offer_price": "₹80,000 + 18% GST",
    "offer_savings": "You Save ₹75,000",
    "offer_valid_till": "15 August 2026 (End of Day)",
    "offer_note": "Only 10 Independence Day promotional slots — valid for 3 days from your positive profile evaluation outcome.",
    # Payment
    "payment_enabled": True,
    "payment_intro": ("To proceed with the next steps, please find our payment details below. You can pay by "
                      "Credit Card / NEFT / IMPS / UPI, or scan our QR code (also attached)."),
    "payment_link": "https://rzp.io/rzp/IndepdenceJjMJwx1",
    "upi_id": "7738352427@okbizaxis",
    "bank_domestic": {
        "account_name": "Ladhani Education & Migration Services OPC PVT LTD",
        "account_number": "924020021437590",
        "ifsc": "UTIB0001364",
        "bank_name": "AXIS Bank",
        "branch": "Dombivali East",
        "account_type": "Current",
    },
    "banks_international": [
        {"label": "United States (USD)", "details": "Beneficiary: LADHANI EDUCATION & MIGRATION SERVICES (OPC) PVT LTD\nAccount: 8331627764\nBank: Community Federal Savings Bank\n5 Penn Plaza, 14th Floor, New York, NY 10001, US\nACH routing: 026073150 · Fedwire: 026073008"},
        {"label": "United Kingdom (GBP)", "details": "Beneficiary: LADHANI EDUCATION & MIGRATION SERVICES (OPC) PVT LTD\nAccount: 51475035 · Sort code: 608382\nBank: Banking Circle\n68 King William Street, London, EC4N 7HR, UK"},
        {"label": "Europe (EUR)", "details": "Beneficiary: LADHANI EDUCATION & MIGRATION SERVICES (OPC) PVT LTD\nIBAN: DE77202208000051475035 · BIC: SXPYDEHH\nBank: Banking Circle S.A. — German Branch\nMaximilianstraße 54, 80538 München"},
        {"label": "UAE (AED)", "details": "Beneficiary: LADHANI EDUCATION & MIGRATION SERVICES (OPC) PVT LTD\nIBAN: AE070960000691060025232 · BIC: ZANDAEAAXXX\nBank: Zand Bank PJSC\n1st Floor, Emaar Square, Building 6, Dubai, UAE"},
        {"label": "Canada (CAD)", "details": "Beneficiary: LADHANI EDUCATION & MIGRATION SERVICES (OPC) PVT LTD\nAccount: 921789038 · Routing: 035210009\nInstitution: 352 · Transit: 10009\nBank: Digital Commerce Bank\n736 Meridian Road N.E, Calgary, Alberta, CA"},
        {"label": "Australia (AUD)", "details": "Beneficiary: LADHANI EDUCATION & MIGRATION SERVICES (OPC) PVT LTD\nAccount: 051475035 · BSB: 252000\nBank: BC Payments\nLevel 11/10 Carrington St, Sydney NSW 2000, Australia"},
        {"label": "Singapore (SGD)", "details": "Beneficiary: LADHANI EDUCATION & MIGRATION SERVICES (OPC) PVT LTD\nAccount: 885414530114 · SWIFT: DBSSSGSG\nBank: DBS Bank Limited\n12 Marina Boulevard, MBFC Tower 3, Singapore 018982"},
        {"label": "Rest of the World", "details": "Beneficiary: LADHANI EDUCATION & MIGRATION SERVICES (OPC) PVT LTD\nIBAN: GB40TCCL04140458379980 · SWIFT: TCCLGB3L\nBank: The Currency Cloud Limited\n12 Steward Street, London, E1 6FQ, UK\nRemark: DO NOT CONVERT TO GBP"},
    ],
    # Consultation
    "calendly_link": "https://calendly.com/rohit-leamss/30min",
    "indicative_note": ("This is an indicative assessment. Our migration team will be glad to walk you through "
                        "the report and plan your next steps. Simply reply to this email or call us on the numbers below."),
    # Closing / contact
    "closing": "Warm Regards,\nLEAMSS – Ladhani Education & Migration Services Pvt. Ltd.\nGlobal Education & Immigration Experts\nYour Success, Our Dream.",
    "contact_phone": "+91 77188 82427",
    "contact_email": "info@leamss.com",
    "website": "www.leamss.com",
    # Attachments
    "attach_report": True,
    "attach_sla": True,
    "sla_file_id": None,
    "sla_filename": "LEAMSS-Service-Level-Agreement-2026.pdf",
    "attach_resume": True,
    "qr_file_id": None,
    "offer_banner_file_id": None,
}

# Fields the client may PUT (assets are handled by upload endpoints).
_EDITABLE = {
    "subject_template", "outcome_title", "body_message", "services_list", "gov_charges",
    "offer_enabled", "offer_badge", "offer_title", "offer_regular_fee", "offer_price",
    "offer_savings", "offer_valid_till", "offer_note",
    "payment_enabled", "payment_intro", "payment_link", "upi_id", "bank_domestic",
    "banks_international", "calendly_link", "indicative_note", "closing", "contact_phone",
    "contact_email", "website", "attach_report", "attach_sla", "sla_filename", "attach_resume",
}


async def get_settings() -> Dict[str, Any]:
    """Return the settings doc, seeding defaults on first access. Never returns _id."""
    doc = await SETTINGS.find_one({"id": "global"}, {"_id": 0})
    if not doc:
        doc = dict(DEFAULTS)
        doc["created_at"] = datetime.now(timezone.utc)
        await SETTINGS.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc
    # backfill any newly-added default keys
    changed = {k: v for k, v in DEFAULTS.items() if k not in doc}
    if changed:
        await SETTINGS.update_one({"id": "global"}, {"$set": changed})
        doc.update(changed)
    return doc


async def read_asset_bytes(file_id: str) -> Optional[bytes]:
    try:
        buf = io.BytesIO()
        await _assets.download_to_stream(ObjectId(file_id), buf)
        return buf.getvalue()
    except Exception:
        return None


@router.get("")
async def read_settings(current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    s = await get_settings()
    s["has_sla"] = bool(s.get("sla_file_id"))
    s["has_qr"] = bool(s.get("qr_file_id"))
    s["has_offer_banner"] = bool(s.get("offer_banner_file_id"))
    return s


class SettingsUpdate(BaseModel):
    updates: Dict[str, Any]


@router.put("")
async def update_settings(req: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    await get_settings()  # ensure seeded
    clean = {k: v for k, v in (req.updates or {}).items() if k in _EDITABLE}
    if not clean:
        raise HTTPException(status_code=400, detail="No editable fields provided.")
    clean["updated_at"] = datetime.now(timezone.utc)
    clean["updated_by"] = current_user.get("email")
    await SETTINGS.update_one({"id": "global"}, {"$set": clean})
    return {"ok": True, "updated": list(clean.keys())}


_ASSET_FIELDS = {"sla": "sla_file_id", "qr": "qr_file_id", "offer_banner": "offer_banner_file_id"}


@router.post("/upload/{asset}")
async def upload_asset(asset: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if asset not in _ASSET_FIELDS:
        raise HTTPException(status_code=400, detail="Unknown asset type")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    await get_settings()
    field = _ASSET_FIELDS[asset]
    # remove old asset if present
    old = (await SETTINGS.find_one({"id": "global"}, {field: 1})) or {}
    old_id = old.get(field)
    file_id = await _assets.upload_from_stream(
        file.filename or asset,
        io.BytesIO(data),
        metadata={"asset": asset, "content_type": file.content_type},
    )
    update = {field: str(file_id)}
    if asset == "sla":
        update["sla_filename"] = file.filename or "LEAMSS-Service-Level-Agreement.pdf"
    await SETTINGS.update_one({"id": "global"}, {"$set": update})
    if old_id:
        try:
            await _assets.delete(ObjectId(old_id))
        except Exception:
            pass
    return {"ok": True, "asset": asset, "file_id": str(file_id), "filename": file.filename}


@router.delete("/asset/{asset}")
async def delete_asset(asset: str, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if asset not in _ASSET_FIELDS:
        raise HTTPException(status_code=400, detail="Unknown asset type")
    field = _ASSET_FIELDS[asset]
    cur = (await SETTINGS.find_one({"id": "global"}, {field: 1})) or {}
    if cur.get(field):
        try:
            await _assets.delete(ObjectId(cur[field]))
        except Exception:
            pass
    await SETTINGS.update_one({"id": "global"}, {"$set": {field: None}})
    return {"ok": True}


@router.get("/asset/{asset}")
async def get_asset(asset: str):
    """PUBLIC — serves the QR / offer banner image (used by <img> in emails) and SLA."""
    if asset not in _ASSET_FIELDS:
        raise HTTPException(status_code=404, detail="Not found")
    field = _ASSET_FIELDS[asset]
    s = await SETTINGS.find_one({"id": "global"}, {field: 1})
    fid = (s or {}).get(field)
    if not fid:
        raise HTTPException(status_code=404, detail="Asset not set")
    data = await read_asset_bytes(fid)
    if not data:
        raise HTTPException(status_code=404, detail="Asset missing")
    if asset == "sla":
        return Response(content=data, media_type="application/pdf")
    # infer image type from header
    ctype = "image/png"
    if data[:3] == b"\xff\xd8\xff":
        ctype = "image/jpeg"
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "public, max-age=300"})


class TestEmailRequest(BaseModel):
    to: str
    sender_email: Optional[str] = None


@router.post("/test")
async def send_test(req: TestEmailRequest, current_user: dict = Depends(get_current_user)):
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    import os
    from core.gmail_dwd import send as gmail_send, is_configured, default_sender
    from core.report_email import build_report_email
    if not is_configured():
        raise HTTPException(status_code=503, detail="Gmail is not configured yet.")
    to = (req.to or "").strip()
    if "@" not in to:
        raise HTTPException(status_code=400, detail="Enter a valid recipient email.")
    s = await get_settings()
    sender = (req.sender_email or default_sender()).strip().lower()
    subject, html, plain = build_report_email(
        s, client_name="Test Client", occupation="Software Engineer", code="261313",
        points={"189": 70, "190": 75, "491": 85}, sender_name="LEAMSS",
        backend_url=os.environ.get("PUBLIC_BASE_URL", ""),
    )
    attachments = []
    if s.get("attach_sla") and s.get("sla_file_id"):
        sla = await read_asset_bytes(s["sla_file_id"])
        if sla:
            attachments.append({"bytes": sla, "filename": s.get("sla_filename") or "SLA.pdf", "maintype": "application", "subtype": "pdf"})
    if s.get("qr_file_id"):
        qr = await read_asset_bytes(s["qr_file_id"])
        if qr:
            attachments.append({"bytes": qr, "filename": "LEAMSS-Payment-QR.png", "maintype": "image", "subtype": "png"})
    try:
        await gmail_send(sender_email=sender, sender_name="LEAMSS", recipient=to,
                         subject="[TEST] " + subject, html=html, plain=plain,
                         attachments=attachments, bcc=None)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"ok": True, "sent_to": to, "from": sender}
