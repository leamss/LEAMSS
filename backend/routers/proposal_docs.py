"""Proposal + Invoice PDF Generator + E-Signature for Pre-Assessments.

Endpoints:
  GET  /api/proposal-docs/{pa_id}/proposal.pdf   — branded proposal PDF
  GET  /api/proposal-docs/{pa_id}/invoice.pdf    — branded invoice PDF
  POST /api/proposal-docs/{pa_id}/send-invoice   — mock-email the invoice + record
  POST /api/proposal-docs/{pa_id}/esign          — save client signature (base64 PNG)
  GET  /api/proposal-docs/{pa_id}/esign          — get signature meta + data_url
"""
import os
import uuid
import base64
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity
from core.integrity import compute_hash

router = APIRouter(prefix="/proposal-docs", tags=["Proposal Docs"])

pre_assessments_col = db["pre_assessments"]
signatures_col = db["pa_signatures"]
invoices_col = db["pa_invoices"]
notifications_col = db["notifications"]
users_col = db["users"]

PDF_DIR = "/app/uploads/proposal_docs"
SIG_DIR = "/app/uploads/signatures"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(SIG_DIR, exist_ok=True)


def _fmt_inr(v):
    try:
        return f"INR {float(v or 0):,.0f}"
    except Exception:
        return "INR 0"


async def _load_pa(pa_id: str):
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    return pa


def _authz(pa: dict, current_user: dict):
    role = current_user.get("role")
    if role == "admin":
        return
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa.get("partner_id") == current_user["id"]:
        return
    if role == "case_manager":
        return
    if role == "client":
        email_match = (pa.get("client_email") or "").lower() == (current_user.get("email") or "").lower()
        id_match = pa.get("client_user_id") == current_user["id"]
        if email_match or id_match:
            return
    raise HTTPException(status_code=403, detail="Not authorized for this PA")


def _build_proposal_pdf(pa: dict, out_path: str, doc_kind: str = "proposal"):
    """Render a branded A4 proposal or invoice PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    doc = SimpleDocTemplate(out_path, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=36, rightMargin=36)
    styles = getSampleStyleSheet()
    brand = colors.HexColor("#2a777a")
    accent = colors.HexColor("#f7620b")
    title_style = ParagraphStyle("t", parent=styles["Heading1"], fontSize=20, textColor=brand, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, textColor=brand, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10.5, leading=16)

    elems = []
    # Header
    logo_path = "/app/backend/uploads/leamss-logo.png"
    if os.path.exists(logo_path):
        img = Image(logo_path, width=140, height=60)
        img.hAlign = "LEFT"
        elems.append(img)
    else:
        elems.append(Paragraph("LEAMSS Immigration Services", title_style))
    elems.append(Spacer(1, 4))
    header_text = "Service Proposal" if doc_kind == "proposal" else "Tax Invoice"
    elems.append(Paragraph(header_text, title_style))
    ref_id = pa.get("pa_number") or pa.get("id", "")[:12]
    elems.append(Paragraph(f"Reference: <b>{ref_id}</b> &nbsp;&nbsp; | &nbsp;&nbsp; Date: {datetime.now().strftime('%d %b %Y')}", sub))
    elems.append(Spacer(1, 14))

    # Parties
    parties = [
        [Paragraph("<b>From (Partner)</b>", body), Paragraph("<b>To (Client)</b>", body)],
        [Paragraph(pa.get("partner_name") or "LEAMSS Partner", body),
         Paragraph(pa.get("client_name") or "—", body)],
        [Paragraph("via LEAMSS Immigration", sub),
         Paragraph(pa.get("client_email") or "", sub)],
    ]
    t = Table(parties, colWidths=[260, 260])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f9f9")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 14))

    # Case summary
    elems.append(Paragraph("Case Summary", h2))
    svc_data = [
        ["Country", pa.get("country") or "—"],
        ["Service Type", pa.get("service_type") or "—"],
        ["Product", pa.get("product_name") or "—"],
        ["Stage", (pa.get("stage") or "").replace("_", " ").title()],
    ]
    st = Table(svc_data, colWidths=[140, 380])
    st.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(st)
    elems.append(Spacer(1, 14))

    # Proposal text (if proposal)
    if doc_kind == "proposal" and pa.get("proposal_ai_text"):
        elems.append(Paragraph("Proposal Letter", h2))
        for para in str(pa["proposal_ai_text"]).split("\n"):
            if para.strip():
                elems.append(Paragraph(para.strip(), body))
                elems.append(Spacer(1, 4))
        elems.append(Spacer(1, 10))

    # Fee breakdown
    elems.append(Paragraph("Fee Breakdown", h2))
    rows = [["Item", "Amount"]]
    rows.append(["Pre-Assessment Fee (Step 1)", _fmt_inr(pa.get("pre_assessment_fee") or 5100)])
    if pa.get("proposal_base_fee"):
        rows.append(["Base Service Fee", _fmt_inr(pa.get("proposal_base_fee"))])
    if pa.get("proposal_promo_code"):
        rows.append([f"Promo ({pa['proposal_promo_code']})", f"- {_fmt_inr(pa.get('proposal_promo_discount'))}"])
    if (pa.get("proposal_additional_discount") or 0) > 0:
        rows.append(["Custom Discount", f"- {_fmt_inr(pa.get('proposal_additional_discount'))}"])
    for u in (pa.get("proposal_upsells") or []):
        rows.append([f"Upsell: {u.get('name', '')}", f"+ {_fmt_inr(u.get('amount'))}"])
    total_received = float(pa.get("pre_assessment_fee") or 0) + float(pa.get("proposal_fee") or 0)
    rows.append(["Main Service Final Amount", _fmt_inr(pa.get("proposal_fee"))])
    rows.append(["TOTAL RECEIVED", _fmt_inr(total_received)])

    ft = Table(rows, colWidths=[360, 160])
    ft.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ecfdf5")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#047857")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(ft)
    elems.append(Spacer(1, 14))

    if pa.get("proposal_notes"):
        elems.append(Paragraph("Partner Notes", h2))
        elems.append(Paragraph(pa["proposal_notes"].replace("\n", "<br/>"), body))
        elems.append(Spacer(1, 10))

    # Consent / legal
    if doc_kind == "proposal":
        elems.append(Paragraph("Terms & Consent", h2))
        elems.append(Paragraph(
            "By accepting this proposal, the client confirms that all information provided is accurate, "
            "understands that LEAMSS does not guarantee immigration outcomes, and agrees to the SLA timelines "
            "communicated by the assigned Case Manager. Fees are non-refundable once services have commenced "
            "except as per the refund policy applicable at the pre-assessment stage.", body))

    # Footer
    elems.append(Spacer(1, 18))
    elems.append(Paragraph(
        f"<font color='#94a3b8'>Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} · "
        f"LEAMSS Immigration Services · This is a system-generated document.</font>", sub))

    doc.build(elems)


async def _ensure_pdf(pa: dict, kind: str) -> str:
    fname = f"{kind}_{pa['id']}.pdf"
    path = os.path.join(PDF_DIR, fname)
    _build_proposal_pdf(pa, path, doc_kind=kind)
    return path


@router.get("/{pa_id}/proposal.pdf")
async def download_proposal_pdf(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await _load_pa(pa_id)
    _authz(pa, current_user)
    path = await _ensure_pdf(pa, "proposal")
    return FileResponse(path, media_type="application/pdf", filename=f"Proposal_{pa.get('pa_number', pa_id[:8])}.pdf")


@router.get("/{pa_id}/invoice.pdf")
async def download_invoice_pdf(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await _load_pa(pa_id)
    _authz(pa, current_user)
    path = await _ensure_pdf(pa, "invoice")
    return FileResponse(path, media_type="application/pdf", filename=f"Invoice_{pa.get('pa_number', pa_id[:8])}.pdf")


class SendInvoiceBody(BaseModel):
    channel: str = "email"  # "email" | "whatsapp"
    message: str = ""


@router.post("/{pa_id}/send-invoice")
async def send_invoice(pa_id: str, body: SendInvoiceBody, current_user: dict = Depends(get_current_user)):
    pa = await _load_pa(pa_id)
    _authz(pa, current_user)
    if current_user["role"] not in ["partner", "admin"]:
        raise HTTPException(status_code=403, detail="Only partner/admin can send invoice")
    # Ensure PDF exists
    await _ensure_pdf(pa, "invoice")
    ref_id = f"INV-{pa.get('pa_number', pa_id[:8])}"
    record = {
        "id": str(uuid.uuid4()),
        "reference_id": ref_id,
        "pre_assessment_id": pa_id,
        "pa_number": pa.get("pa_number"),
        "client_email": pa.get("client_email"),
        "client_name": pa.get("client_name"),
        "amount_received_total": float(pa.get("pre_assessment_fee") or 0) + float(pa.get("proposal_fee") or 0),
        "channel": body.channel,
        "message": body.message,
        "sent_by": current_user.get("id"),
        "sent_by_name": current_user.get("name"),
        "mode": "mock",  # Resend not wired
        "sent_at": datetime.now(timezone.utc),
    }
    record["integrity_hash"] = compute_hash("invoice", record)
    await invoices_col.insert_one(record)
    record.pop("_id", None)
    record["sent_at"] = record["sent_at"].isoformat()

    # Client-side notification (in-app)
    if pa.get("client_user_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["client_user_id"],
            "title": "Invoice Received",
            "message": f"Your invoice {ref_id} is available in your portal. Amount: INR {record['amount_received_total']:,.0f}",
            "type": "invoice", "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    await log_activity(current_user["id"], current_user.get("name", ""), "send_invoice",
                       "pre_assessment", pa_id, f"Invoice {ref_id} sent to {pa.get('client_email')} (MOCK email)")

    return {"ok": True, "reference_id": ref_id, "mode": "mock", "record": record}


# ===================== E-SIGNATURE =====================

class EsignBody(BaseModel):
    signature_data_url: str  # "data:image/png;base64,...."
    typed_name: str = ""
    consent_text: str = ""
    ip_hint: str = ""


@router.post("/{pa_id}/esign")
async def save_esign(pa_id: str, body: EsignBody, request: Request, current_user: dict = Depends(get_current_user)):
    pa = await _load_pa(pa_id)
    _authz(pa, current_user)
    if current_user["role"] != "client":
        raise HTTPException(status_code=403, detail="Only the client can e-sign their agreement")

    if not body.signature_data_url.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Invalid signature format")

    # Persist PNG to disk
    try:
        b64 = body.signature_data_url.split(",", 1)[1]
        raw = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Corrupt signature data")

    fname = f"sig_{pa_id}_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(SIG_DIR, fname)
    with open(path, "wb") as fp:
        fp.write(raw)

    ip = request.client.host if request.client else body.ip_hint
    rec = {
        "id": str(uuid.uuid4()),
        "pre_assessment_id": pa_id,
        "user_id": current_user["id"],
        "user_email": current_user.get("email"),
        "typed_name": body.typed_name,
        "consent_text": body.consent_text,
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent", ""),
        "file_path": path,
        "file_size": len(raw),
        "signed_at": datetime.now(timezone.utc),
    }
    rec["integrity_hash"] = compute_hash("signature", rec)
    await signatures_col.insert_one(rec)
    rec.pop("_id", None)
    rec["signed_at"] = rec["signed_at"].isoformat()

    # Also set a flag on PA doc
    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "agreement_signed": True,
        "agreement_signed_at": datetime.now(timezone.utc),
        "agreement_signature_id": rec["id"],
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "esign_agreement",
                       "pre_assessment", pa_id, f"Client e-signed agreement ({body.typed_name})")

    return {"ok": True, "signature_id": rec["id"], "signed_at": rec["signed_at"]}


@router.get("/{pa_id}/esign")
async def get_esign(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await _load_pa(pa_id)
    _authz(pa, current_user)
    rec = await signatures_col.find_one({"pre_assessment_id": pa_id}, {"_id": 0}, sort=[("signed_at", -1)])
    if not rec:
        return {"signed": False}
    data_url = None
    p = rec.get("file_path")
    if p and os.path.exists(p):
        with open(p, "rb") as fp:
            data_url = "data:image/png;base64," + base64.b64encode(fp.read()).decode("ascii")
    if hasattr(rec.get("signed_at"), "isoformat"):
        rec["signed_at"] = rec["signed_at"].isoformat()
    rec["signature_data_url"] = data_url
    return {"signed": True, "record": rec}


@router.get("/{pa_id}/invoices")
async def list_invoices(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await _load_pa(pa_id)
    _authz(pa, current_user)
    items = await invoices_col.find({"pre_assessment_id": pa_id}, {"_id": 0}).sort("sent_at", -1).to_list(200)
    for it in items:
        if hasattr(it.get("sent_at"), "isoformat"):
            it["sent_at"] = it["sent_at"].isoformat()
    return items
