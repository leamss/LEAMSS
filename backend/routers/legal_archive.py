"""Legal Archive — searchable index of consents, signatures, invoices for compliance audit.

Endpoints:
  GET  /api/legal-archive/search   — unified search across all 3 record types
  GET  /api/legal-archive/stats    — counts per type
  GET  /api/legal-archive/{ref_id} — fetch full record by reference_id
  GET  /api/legal-archive/compliance-report.pdf — date-range stamped PDF audit report
"""
import io
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from core.database import db
from routers.auth import get_current_user
from core.integrity import compute_hash, verify_hash

router = APIRouter(prefix="/legal-archive", tags=["Legal Archive"])

consent_col = db["proposal_consent_emails"]
signatures_col = db["pa_signatures"]
invoices_col = db["pa_invoices"]
pa_col = db["pre_assessments"]
share_audit_col = db["share_audit_events"]


def _admin_only(current_user: dict):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only — Legal Archive is restricted to compliance officers")


def _iso(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


@router.get("/stats")
async def legal_stats(current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    consents = await consent_col.count_documents({})
    sigs = await signatures_col.count_documents({})
    invs = await invoices_col.count_documents({})
    shares = await share_audit_col.count_documents({})
    return {
        "consents": consents,
        "signatures": sigs,
        "invoices": invs,
        "share_events": shares,
        "total": consents + sigs + invs + shares,
    }


@router.get("/search")
async def legal_search(
    q: str = Query("", description="Free text — searches client name/email, ref_id, pa_number"),
    record_type: Optional[str] = Query("all", description="all | consent | signature | invoice | share_event"),
    start_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    """Unified search returning a single sorted timeline of records."""
    _admin_only(current_user)
    q_lower = (q or "").strip().lower()

    # Date filter
    date_q = {}
    if start_date:
        try:
            date_q["$gte"] = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    if end_date:
        try:
            date_q["$lt"] = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        except Exception:
            pass

    results = []

    async def _hydrate_pa(pa_id):
        if not pa_id:
            return {}
        pa = await pa_col.find_one({"id": pa_id}, {"_id": 0, "client_name": 1, "client_email": 1,
                                                    "partner_name": 1, "country": 1, "service_type": 1,
                                                    "pa_number": 1})
        return pa or {}

    def _matches(text: str):
        if not q_lower:
            return True
        return q_lower in (text or "").lower()

    # ===== CONSENTS =====
    if record_type in ("all", "consent"):
        cq = {"created_at": date_q} if date_q else {}
        cursor = consent_col.find(cq, {"_id": 0}).sort("created_at", -1).to_list(limit)
        consents = await cursor
        for c in consents:
            pa = await _hydrate_pa(c.get("pre_assessment_id"))
            haystack = " ".join([
                c.get("reference_id") or "", c.get("to_name") or "", c.get("to_email") or "",
                c.get("partner_name") or "", c.get("pa_number") or "",
                pa.get("client_name") or "", pa.get("client_email") or "",
            ])
            if not _matches(haystack):
                continue
            body = c.get("body_snapshot") or {}
            integrity = verify_hash("consent", c)
            results.append({
                "type": "consent",
                "id": c.get("id"),
                "reference_id": c.get("reference_id"),
                "pa_id": c.get("pre_assessment_id"),
                "pa_number": c.get("pa_number"),
                "client_name": c.get("to_name") or pa.get("client_name"),
                "client_email": c.get("to_email") or pa.get("client_email"),
                "partner_name": c.get("partner_name") or pa.get("partner_name"),
                "country": pa.get("country"),
                "service_type": pa.get("service_type"),
                "amount": body.get("final_amount"),
                "timestamp": _iso(c.get("created_at")),
                "channel": c.get("channel"),
                "mode": c.get("mode"),
                "integrity_status": integrity["status"],
                "integrity_hash": (c.get("integrity_hash") or "")[:12],
                "preview": {
                    "base_fee": body.get("base_fee"),
                    "promo_code": body.get("promo_code"),
                    "promo_discount": body.get("promo_discount"),
                    "custom_discount": body.get("custom_discount"),
                    "upsells": body.get("upsells") or [],
                    "upsell_total": body.get("upsell_total"),
                    "final_amount": body.get("final_amount"),
                },
            })

    # ===== SIGNATURES =====
    if record_type in ("all", "signature"):
        sq = {"signed_at": date_q} if date_q else {}
        sigs = await signatures_col.find(sq, {"_id": 0}).sort("signed_at", -1).to_list(limit)
        for s in sigs:
            pa = await _hydrate_pa(s.get("pre_assessment_id"))
            haystack = " ".join([
                s.get("typed_name") or "", s.get("user_email") or "",
                pa.get("client_name") or "", pa.get("client_email") or "",
                pa.get("pa_number") or "",
            ])
            if not _matches(haystack):
                continue
            integrity = verify_hash("signature", s)
            results.append({
                "type": "signature",
                "id": s.get("id"),
                "reference_id": f"SIG-{(pa.get('pa_number') or '')}-{s.get('id', '')[:6].upper()}",
                "pa_id": s.get("pre_assessment_id"),
                "pa_number": pa.get("pa_number"),
                "client_name": s.get("typed_name") or pa.get("client_name"),
                "client_email": s.get("user_email") or pa.get("client_email"),
                "partner_name": pa.get("partner_name"),
                "country": pa.get("country"),
                "service_type": pa.get("service_type"),
                "timestamp": _iso(s.get("signed_at")),
                "ip_address": s.get("ip_address"),
                "user_agent": (s.get("user_agent") or "")[:80],
                "file_size": s.get("file_size"),
                "integrity_status": integrity["status"],
                "integrity_hash": (s.get("integrity_hash") or "")[:12],
            })

    # ===== INVOICES =====
    if record_type in ("all", "invoice"):
        iq = {"sent_at": date_q} if date_q else {}
        invs = await invoices_col.find(iq, {"_id": 0}).sort("sent_at", -1).to_list(limit)
        for inv in invs:
            pa = await _hydrate_pa(inv.get("pre_assessment_id"))
            haystack = " ".join([
                inv.get("reference_id") or "", inv.get("client_name") or "",
                inv.get("client_email") or "", pa.get("client_name") or "",
                pa.get("pa_number") or "",
            ])
            if not _matches(haystack):
                continue
            integrity = verify_hash("invoice", inv)
            results.append({
                "type": "invoice",
                "id": inv.get("id"),
                "reference_id": inv.get("reference_id"),
                "pa_id": inv.get("pre_assessment_id"),
                "pa_number": inv.get("pa_number") or pa.get("pa_number"),
                "client_name": inv.get("client_name") or pa.get("client_name"),
                "client_email": inv.get("client_email") or pa.get("client_email"),
                "partner_name": pa.get("partner_name"),
                "country": pa.get("country"),
                "service_type": pa.get("service_type"),
                "amount": inv.get("amount_received_total"),
                "timestamp": _iso(inv.get("sent_at")),
                "channel": inv.get("channel"),
                "mode": inv.get("mode"),
                "integrity_status": integrity["status"],
                "integrity_hash": (inv.get("integrity_hash") or "")[:12],
            })

    # ===== SHARE EVENTS (Phase 6.7 audit log) =====
    if record_type in ("all", "share_event"):
        seq = {"created_at": date_q} if date_q else {}
        events = await share_audit_col.find(seq, {"_id": 0}).sort("created_at", -1).to_list(limit)
        for e in events:
            haystack = " ".join([
                e.get("reference_id") or "", e.get("entity_id") or "",
                e.get("client_name") or "", e.get("client_email") or "",
                e.get("actor_email") or "", e.get("share_token_prefix") or "",
                e.get("event_type") or "",
            ])
            if not _matches(haystack):
                continue
            integrity = verify_hash("share_event", e)
            results.append({
                "type": "share_event",
                "id": e.get("id"),
                "reference_id": e.get("reference_id"),
                "entity_id": e.get("entity_id"),
                "pa_id": e.get("entity_id") if e.get("entity_kind") == "pa" else None,
                "client_name": e.get("client_name"),
                "client_email": e.get("client_email"),
                "event_type": e.get("event_type"),
                "share_type": e.get("share_type"),
                "share_token_prefix": e.get("share_token_prefix"),
                "actor_email": e.get("actor_email"),
                "actor_role": e.get("actor_role"),
                "ip_address": e.get("ip_address"),
                "user_agent": (e.get("user_agent") or "")[:80],
                "timestamp": _iso(e.get("created_at")),
                "details": e.get("details") or {},
                "integrity_status": integrity["status"],
                "integrity_hash": (e.get("integrity_hash") or "")[:12],
            })

    # Sort all-typed combined by timestamp desc
    results.sort(key=lambda r: (r.get("timestamp") or ""), reverse=True)
    results = results[:limit]

    return {
        "count": len(results),
        "filters": {"q": q, "record_type": record_type, "start_date": start_date, "end_date": end_date},
        "items": results,
    }


@router.get("/integrity/verify-all")
async def integrity_verify_all(current_user: dict = Depends(get_current_user)):
    """Recompute SHA-256 hash for every record. Returns counts + tampered records."""
    _admin_only(current_user)
    summary = {"verified": 0, "tampered": 0, "unverified": 0}
    tampered = []
    for col, rtype in [(consent_col, "consent"), (signatures_col, "signature"), (invoices_col, "invoice"), (share_audit_col, "share_event")]:
        async for d in col.find({}, {"_id": 0}):
            r = verify_hash(rtype, d)
            summary[r["status"]] = summary.get(r["status"], 0) + 1
            if r["status"] == "tampered":
                tampered.append({
                    "type": rtype, "id": d.get("id"), "reference_id": d.get("reference_id"),
                    "expected": r["expected"][:16] + "…", "actual": (r["actual"] or "")[:16] + "…",
                })
    summary["total"] = summary["verified"] + summary["tampered"] + summary["unverified"]
    summary["tampered_records"] = tampered
    summary["scanned_at"] = datetime.now(timezone.utc).isoformat()
    return summary


@router.post("/integrity/backfill")
async def integrity_backfill(current_user: dict = Depends(get_current_user)):
    """Compute and persist integrity_hash on legacy records that lack one.
    Only writes when hash is missing — never overwrites an existing hash.
    """
    _admin_only(current_user)
    written = {"consent": 0, "signature": 0, "invoice": 0}
    for col, rtype in [(consent_col, "consent"), (signatures_col, "signature"), (invoices_col, "invoice")]:
        async for d in col.find({"integrity_hash": {"$exists": False}}, {"_id": 0}):
            h = compute_hash(rtype, d)
            await col.update_one({"id": d.get("id")}, {"$set": {"integrity_hash": h}})
            written[rtype] += 1
    written["total"] = written["consent"] + written["signature"] + written["invoice"]
    return written


@router.get("/compliance-report.pdf")
async def compliance_report_pdf(
    start_date: Optional[str] = Query(None, description="ISO YYYY-MM-DD; default = 90 days ago"),
    end_date: Optional[str] = Query(None, description="ISO YYYY-MM-DD; default = today"),
    current_user: dict = Depends(get_current_user),
):
    """Generate stamped A4 compliance PDF: cover + integrity scan + 3 record tables + SHA chain footer."""
    _admin_only(current_user)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm

    # ----- date window -----
    now = datetime.now(timezone.utc)
    try:
        end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) if end_date else now
    except Exception:
        end_dt = now
    try:
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc) if start_date else end_dt - timedelta(days=90)
    except Exception:
        start_dt = end_dt - timedelta(days=90)

    date_q = {"$gte": start_dt, "$lte": end_dt + timedelta(days=1)}

    # ----- pull records in window -----
    consents = await consent_col.find({"created_at": date_q}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    sigs = await signatures_col.find({"signed_at": date_q}, {"_id": 0}).sort("signed_at", -1).to_list(2000)
    invs = await invoices_col.find({"sent_at": date_q}, {"_id": 0}).sort("sent_at", -1).to_list(2000)

    # ----- integrity tally -----
    tally = {"verified": 0, "tampered": 0, "unverified": 0}
    tampered_records = []
    for col_name, items, rtype in [("consent", consents, "consent"), ("signature", sigs, "signature"), ("invoice", invs, "invoice")]:
        for d in items:
            r = verify_hash(rtype, d)
            tally[r["status"]] = tally.get(r["status"], 0) + 1
            if r["status"] == "tampered":
                tampered_records.append({"type": rtype, "ref": d.get("reference_id") or d.get("id")})

    # ----- styles -----
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=22, leading=26, alignment=1, textColor=colors.HexColor("#0f172a"), spaceAfter=8)
    subtitle = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, alignment=1, textColor=colors.HexColor("#64748b"), spaceAfter=18)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#2a777a"), spaceAfter=6, spaceBefore=14, leading=16)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5, leading=12, textColor=colors.HexColor("#1f2937"))
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"))

    # ----- Build elements -----
    el = []
    el.append(Paragraph("LEAMSS COMPLIANCE REPORT", title_style))
    el.append(Paragraph("SHA-256 verified · stamped legal audit trail", subtitle))

    cover_data = [
        ["Window", f"{start_dt.strftime('%d %b %Y')} → {end_dt.strftime('%d %b %Y')}"],
        ["Generated", now.strftime("%d %b %Y, %H:%M UTC")],
        ["Generated by", f"{current_user.get('name','')} ({current_user.get('email','')})"],
        ["Total records", str(len(consents) + len(sigs) + len(invs))],
        ["Consents", str(len(consents))],
        ["E-Signatures", str(len(sigs))],
        ["Invoices", str(len(invs))],
    ]
    t = Table(cover_data, colWidths=[55*mm, 110*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0,0), (0,-1), colors.HexColor("#334155")),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
    ]))
    el.append(t)
    el.append(Spacer(1, 16))

    # Integrity panel
    el.append(Paragraph("Integrity Scan", h2))
    integ_color = colors.HexColor("#dc2626") if tally["tampered"] > 0 else (colors.HexColor("#d97706") if tally["unverified"] > 0 else colors.HexColor("#059669"))
    integ_text = f"<b>{tally['verified']}</b> verified · <b>{tally['tampered']}</b> tampered · <b>{tally['unverified']}</b> unverified (scan time {now.strftime('%H:%M:%S UTC')})"
    el.append(Paragraph(f'<font color="{integ_color.hexval()}">{integ_text}</font>', body))
    if tampered_records:
        el.append(Spacer(1, 4))
        el.append(Paragraph("<b>Tampered records flagged:</b>", body))
        for tr in tampered_records:
            el.append(Paragraph(f"• [{tr['type']}] {tr['ref']}", small))
    el.append(Spacer(1, 6))

    def _hash_prefix(d): return (d.get("integrity_hash") or "")[:14] + ("…" if d.get("integrity_hash") else "")

    def _add_table(heading, headers, rows, widths):
        el.append(Paragraph(heading, h2))
        if not rows:
            el.append(Paragraph("<i>No records in window.</i>", small))
            el.append(Spacer(1, 6))
            return
        data = [headers] + rows
        tbl = Table(data, colWidths=widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2a777a")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        el.append(tbl)
        el.append(Spacer(1, 6))

    # Consents table
    crows = []
    for c in consents:
        body_snap = c.get("body_snapshot") or {}
        crows.append([
            c.get("reference_id") or "",
            (c.get("to_name") or "")[:24],
            (body_snap.get("country") or "")[:14],
            f"₹{(body_snap.get('final_amount') or 0):,.0f}",
            (c.get("created_at").strftime("%d-%b %H:%M") if hasattr(c.get("created_at"), "strftime") else ""),
            _hash_prefix(c),
        ])
    _add_table("Consents", ["Reference", "Client", "Country", "Final Amt", "Timestamp", "SHA-256"], crows, [40*mm, 36*mm, 22*mm, 22*mm, 24*mm, 30*mm])

    # Signatures table
    srows = []
    for s in sigs:
        srows.append([
            (s.get("typed_name") or "")[:24],
            (s.get("user_email") or "")[:30],
            (s.get("ip_address") or "")[:16],
            f"{(s.get('file_size') or 0)/1024:.1f} KB",
            (s.get("signed_at").strftime("%d-%b %H:%M") if hasattr(s.get("signed_at"), "strftime") else ""),
            _hash_prefix(s),
        ])
    _add_table("E-Signatures", ["Typed Name", "Email", "IP", "Size", "Timestamp", "SHA-256"], srows, [32*mm, 44*mm, 22*mm, 16*mm, 22*mm, 30*mm])

    # Invoices table
    irows = []
    for inv in invs:
        irows.append([
            inv.get("reference_id") or "",
            (inv.get("client_name") or "")[:24],
            f"₹{(inv.get('amount_received_total') or 0):,.0f}",
            (inv.get("channel") or "")[:10],
            (inv.get("sent_at").strftime("%d-%b %H:%M") if hasattr(inv.get("sent_at"), "strftime") else ""),
            _hash_prefix(inv),
        ])
    _add_table("Invoices", ["Reference", "Client", "Amount", "Channel", "Timestamp", "SHA-256"], irows, [40*mm, 36*mm, 22*mm, 22*mm, 22*mm, 30*mm])

    # Report-level chain hash (binds the whole report)
    chain_input = "|".join(
        [(d.get("integrity_hash") or "") for d in (consents + sigs + invs)]
        + [now.isoformat(), current_user.get("id", "")]
    )
    report_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()

    el.append(Spacer(1, 14))
    el.append(Paragraph("Report SHA-256 Chain", h2))
    el.append(Paragraph(
        f'<font face="Courier" size="8">{report_hash}</font>',
        body
    ))
    el.append(Paragraph(
        "This report digest binds the integrity hashes of all included records to the report timestamp and "
        "the issuing officer. Any divergence on a future verification scan indicates record-level tampering.",
        small
    ))

    # ----- Render to bytes -----
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm,
        title="LEAMSS Compliance Report", author="LEAMSS Legal Archive",
    )

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.drawString(18*mm, 8*mm, f"LEAMSS · Compliance Report · {now.strftime('%Y-%m-%d %H:%M UTC')}")
        canvas.drawRightString(A4[0] - 18*mm, 8*mm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(el, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)

    fname = f"leamss-compliance-{start_dt.strftime('%Y%m%d')}-{end_dt.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{fname}"', "X-Report-Hash": report_hash},
    )


@router.get("/{ref_id}")
async def get_by_reference_id(ref_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch full record by reference_id (CON-... / INV-... / SIG-...)."""
    _admin_only(current_user)
    rec = await consent_col.find_one({"reference_id": ref_id}, {"_id": 0})
    if rec:
        if hasattr(rec.get("created_at"), "isoformat"):
            rec["created_at"] = rec["created_at"].isoformat()
        return {"type": "consent", "record": rec}
    rec = await invoices_col.find_one({"reference_id": ref_id}, {"_id": 0})
    if rec:
        if hasattr(rec.get("sent_at"), "isoformat"):
            rec["sent_at"] = rec["sent_at"].isoformat()
        return {"type": "invoice", "record": rec}
    raise HTTPException(status_code=404, detail="Reference ID not found")
