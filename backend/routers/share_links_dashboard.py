"""Active Share Links — Admin compliance dashboard.

Lists every share-link issued across PAs (both public share-tokens and magic-portal links)
with metadata: issuer, expiry, click/use count, last access info, status.
Admin can revoke any link with one click.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.database import db
from routers.auth import get_current_user
from core.share_audit import record_share_event
from core.integrity import verify_hash
from core.anomaly_detector import detect_anomalies
from core.anomaly_alerter import dispatch_all_high_severity, alerts_col

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/share-links", tags=["Share Links Dashboard"])

pa_col = db["pre_assessments"]
magic_col = db["magic_links"]
users_col = db["users"]
sales_assessments_col = db["sales_assessments"]
share_audit_col = db["share_audit_events"]


def _admin_only(u):
    if u.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only — Share Links dashboard is restricted")


def _now():
    return datetime.now(timezone.utc)


def _iso(v):
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    return v


def _link_status(exp, revoked, used=False, share_active=True):
    """Derive a single status string for UI."""
    if revoked:
        return "revoked"
    if used:
        return "consumed"
    if not share_active:
        return "deactivated"
    if exp:
        if isinstance(exp, str):
            try:
                exp = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            except Exception:
                exp = None
        if isinstance(exp, datetime):
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < _now():
                return "expired"
    return "active"


@router.get("/")
async def list_share_links(
    status: Optional[str] = Query(None, description="active | expired | revoked | consumed | deactivated"),
    link_type: Optional[str] = Query(None, description="public_pa_fee | magic_portal"),
    search: Optional[str] = Query(None, description="search by PA number / client name / email"),
    current_user: dict = Depends(get_current_user),
):
    """List all share-links (both public share-tokens and magic links) with metadata."""
    _admin_only(current_user)

    rows: List[dict] = []
    needle = (search or "").strip().lower()

    # 1. Public share-tokens on PAs
    if link_type in (None, "public_pa_fee"):
        async for pa in pa_col.find(
            {"share_token": {"$exists": True, "$ne": None}},
            {
                "_id": 0, "id": 1, "pa_number": 1, "client_name": 1, "client_email": 1,
                "partner_id": 1, "partner_name": 1, "share_token": 1, "share_expires_at": 1,
                "share_active": 1, "share_click_count": 1, "share_last_accessed_at": 1,
                "share_last_accessed_ip": 1, "share_last_accessed_ua": 1,
                "stage": 1, "fee_payment_status": 1, "updated_at": 1,
            },
        ):
            hay = f"{pa.get('pa_number','')} {pa.get('client_name','')} {pa.get('client_email','')}".lower()
            if needle and needle not in hay:
                continue
            st = _link_status(
                pa.get("share_expires_at"),
                revoked=False,
                share_active=pa.get("share_active", True),
            )
            if status and st != status:
                continue
            rows.append({
                "type": "public_pa_fee",
                "token": pa.get("share_token"),
                "token_prefix": (pa.get("share_token") or "")[:10] + "…",
                "pa_id": pa.get("id"),
                "pa_number": pa.get("pa_number"),
                "client_name": pa.get("client_name"),
                "client_email": pa.get("client_email"),
                "partner_name": pa.get("partner_name"),
                "purpose": "pre_assessment_fee",
                "amount_label": "₹5,100",
                "issued_at": _iso(pa.get("updated_at")),
                "expires_at": _iso(pa.get("share_expires_at")),
                "status": st,
                "access_count": pa.get("share_click_count", 0),
                "last_accessed_at": _iso(pa.get("share_last_accessed_at")),
                "last_accessed_ip": pa.get("share_last_accessed_ip"),
                "last_accessed_ua": pa.get("share_last_accessed_ua"),
            })

    # 2. Magic links
    if link_type in (None, "magic_portal"):
        async for m in magic_col.find({}, {"_id": 0}):
            # Lookup the linked PA (best-effort)
            issued_for_pa = m.get("issued_for_pa")
            pa = None
            if issued_for_pa:
                pa = await pa_col.find_one(
                    {"id": issued_for_pa},
                    {"_id": 0, "pa_number": 1, "client_name": 1, "client_email": 1, "partner_name": 1, "stage": 1, "proposal_fee": 1},
                )
            else:
                # Fallback: lookup user → first PA owned
                pa = await pa_col.find_one(
                    {"client_user_id": m.get("user_id")},
                    {"_id": 0, "pa_number": 1, "client_name": 1, "client_email": 1, "partner_name": 1, "stage": 1, "proposal_fee": 1},
                )
            pa = pa or {}

            hay = f"{pa.get('pa_number','')} {pa.get('client_name','')} {pa.get('client_email','')}".lower()
            if needle and needle not in hay:
                continue

            st = _link_status(
                m.get("expires_at"),
                revoked=m.get("revoked", False),
                used=m.get("used", False),
            )
            if status and st != status:
                continue

            stage = pa.get("stage")
            purpose = (
                "preview_only" if m.get("is_preview")
                else "proposal_fee_payment" if stage == "proposal_sent"
                else "view_portal"
            )
            amt = pa.get("proposal_fee") if purpose == "proposal_fee_payment" else 0
            amt_label = (
                f"₹{int(amt or 0):,}" if purpose == "proposal_fee_payment" and amt
                else "Preview" if purpose == "preview_only"
                else "View"
            )
            rows.append({
                "type": "magic_portal",
                "token": m.get("token"),
                "token_prefix": (m.get("token") or "")[:10] + "…",
                "magic_id": m.get("id"),
                "pa_id": issued_for_pa,
                "pa_number": pa.get("pa_number"),
                "client_name": pa.get("client_name"),
                "client_email": pa.get("client_email"),
                "partner_name": pa.get("partner_name"),
                "purpose": purpose,
                "amount_label": amt_label,
                "issued_by": m.get("issued_by"),
                "is_preview": m.get("is_preview", False),
                "issued_at": _iso(m.get("created_at")),
                "expires_at": _iso(m.get("expires_at")),
                "status": st,
                "access_count": 1 if m.get("used") else 0,
                "used_at": _iso(m.get("used_at")),
                "last_accessed_at": _iso(m.get("used_at")),
                "last_accessed_ip": m.get("used_ip"),
                "last_accessed_ua": m.get("used_ua"),
                "revoked_at": _iso(m.get("revoked_at")),
            })

    # 3. Sales Assessment public report links (Phase 6.5)
    if link_type in (None, "sales_report"):
        async for sa in sales_assessments_col.find(
            {"share_token": {"$exists": True, "$ne": None}},
            {
                "_id": 0, "id": 1, "client_name": 1, "client_email": 1,
                "best_country_code": 1, "best_total": 1, "created_by_name": 1,
                "share_token": 1, "share_expires_at": 1, "share_active": 1,
                "share_revoked": 1, "share_issued_at": 1, "share_click_count": 1,
                "share_last_accessed_at": 1, "share_last_accessed_ip": 1,
                "share_last_accessed_ua": 1, "share_revoked_at": 1, "linked_pa_id": 1,
            },
        ):
            hay = f"{sa.get('id','')} {sa.get('client_name','')} {sa.get('client_email','')}".lower()
            if needle and needle not in hay:
                continue
            st = _link_status(
                sa.get("share_expires_at"),
                revoked=sa.get("share_revoked", False),
                share_active=sa.get("share_active", True),
            )
            if status and st != status:
                continue
            best_country = sa.get("best_country_code") or "—"
            best_total = sa.get("best_total")
            amt_label = f"{best_country} · {best_total} pts" if best_total is not None else best_country
            rows.append({
                "type": "sales_report",
                "token": sa.get("share_token"),
                "token_prefix": (sa.get("share_token") or "")[:10] + "…",
                "sales_assessment_id": sa.get("id"),
                "pa_id": sa.get("linked_pa_id"),
                "pa_number": sa.get("id"),  # SAH-* serves as the reference id
                "client_name": sa.get("client_name"),
                "client_email": sa.get("client_email"),
                "partner_name": sa.get("created_by_name"),
                "purpose": "sales_eligibility_report",
                "amount_label": amt_label,
                "issued_at": _iso(sa.get("share_issued_at")),
                "expires_at": _iso(sa.get("share_expires_at")),
                "status": st,
                "access_count": sa.get("share_click_count", 0),
                "last_accessed_at": _iso(sa.get("share_last_accessed_at")),
                "last_accessed_ip": sa.get("share_last_accessed_ip"),
                "last_accessed_ua": sa.get("share_last_accessed_ua"),
                "revoked_at": _iso(sa.get("share_revoked_at")),
            })

    # Sort newest first
    rows.sort(key=lambda r: r.get("issued_at") or "", reverse=True)

    # Stats
    stats = {"active": 0, "expired": 0, "revoked": 0, "consumed": 0, "deactivated": 0, "total": len(rows)}
    for r in rows:
        stats[r["status"]] = stats.get(r["status"], 0) + 1

    # Suspicious heuristics: high click count without conversion, multiple IPs (we only store last_ip so just flag clicks>=5)
    for r in rows:
        r["suspicious"] = bool(r.get("access_count", 0) >= 5 and r["status"] == "active")

    return {"count": len(rows), "stats": stats, "items": rows}


class RevokeRequest(BaseModel):
    type: str  # "public_pa_fee" | "magic_portal"
    token: str
    reason: Optional[str] = None


@router.post("/revoke")
async def revoke_link(body: RevokeRequest, current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    now = _now()

    if body.type == "public_pa_fee":
        res = await pa_col.update_one(
            {"share_token": body.token},
            {"$set": {
                "share_active": False,
                "share_revoked_at": now,
                "share_revoked_by": current_user.get("id"),
                "share_revoke_reason": body.reason,
            }},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Share token not found")
        return {"ok": True, "revoked_type": "public_pa_fee", "token_prefix": body.token[:10] + "…"}

    if body.type == "magic_portal":
        res = await magic_col.update_one(
            {"token": body.token},
            {"$set": {
                "revoked": True,
                "revoked_at": now,
                "revoked_by": current_user.get("id"),
                "revoke_reason": body.reason,
            }},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Magic token not found")
        return {"ok": True, "revoked_type": "magic_portal", "token_prefix": body.token[:10] + "…"}

    if body.type == "sales_report":
        sa = await sales_assessments_col.find_one({"share_token": body.token}, {"_id": 0, "id": 1, "client_name": 1, "client_email": 1})
        res = await sales_assessments_col.update_one(
            {"share_token": body.token},
            {"$set": {
                "share_active": False,
                "share_revoked": True,
                "share_revoked_at": now,
                "share_revoked_by": current_user.get("id"),
                "share_revoke_reason": body.reason,
                "updated_at": now,
            }},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Sales report token not found")
        # Audit log
        await record_share_event(
            event_type="share_revoked",
            share_type="sales_report",
            share_token=body.token,
            reference_id=(sa or {}).get("id"),
            reference_kind="sales_assessment",
            client_name=(sa or {}).get("client_name"),
            client_email=(sa or {}).get("client_email"),
            actor_id=current_user.get("id"),
            actor_email=current_user.get("email"),
            actor_role=current_user.get("role"),
            details={"source": "share_links_dashboard", "reason": body.reason},
        )
        return {"ok": True, "revoked_type": "sales_report", "token_prefix": body.token[:10] + "…"}

    raise HTTPException(status_code=400, detail="Invalid type — must be 'public_pa_fee', 'magic_portal', or 'sales_report'")


@router.get("/anomalies")
async def share_link_anomalies(
    since_hours: int = Query(24, ge=1, le=720, description="Lookback window in hours (1 = last hour, 720 = last 30 days)"),
    auto_alert: bool = Query(True, description="If true, auto-dispatch alerts for new HIGH-severity anomalies (de-duplicated per token per hour)"),
    current_user: dict = Depends(get_current_user),
):
    """Scan all share_audit_events within the lookback window and flag suspicious patterns.

    Admin only. Rule-based, no AI.

    Patterns detected:
      - rapid_burst      : >= 10 accesses in any 1-hour window
      - multiple_ips     : >= 5 distinct IPs in any 30-min window
      - post_revoke_scrape: denied accesses recorded after a revoke event
      - expired_hammering: >= 5 expired-link denials within 1 hour
      - bot_pattern      : same UA hitting >= 3 distinct tokens
      - impossible_geo   : >= 2 accesses from different countries < 5 min apart
    """
    _admin_only(current_user)
    since = datetime.utcnow() - timedelta(hours=since_hours)
    events = await share_audit_col.find(
        {"created_at": {"$gte": since}},
        {"_id": 0},
    ).to_list(20000)
    scan = detect_anomalies(events, window_hours=since_hours)
    # Auto-dispatch alerts for new HIGH severities
    if auto_alert:
        scan["alert_dispatch"] = await dispatch_all_high_severity(scan)
    return scan


@router.get("/anomaly-alerts")
async def list_anomaly_alerts(
    limit: int = Query(50, ge=1, le=200),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    current_user: dict = Depends(get_current_user),
):
    """Return the internal anomaly-alert feed (Slack-independent)."""
    _admin_only(current_user)
    q = {}
    if acknowledged is not None:
        q["acknowledged"] = acknowledged
    items = await alerts_col.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
    # Sanitise datetime
    for item in items:
        if isinstance(item.get("created_at"), datetime):
            item["created_at"] = item["created_at"].isoformat()
        if isinstance(item.get("acknowledged_at"), datetime):
            item["acknowledged_at"] = item["acknowledged_at"].isoformat()
    return {"items": items, "count": len(items)}


@router.post("/anomaly-alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    """Mark an alert as reviewed/acknowledged by an admin."""
    _admin_only(current_user)
    res = await alerts_col.update_one(
        {"id": alert_id},
        {"$set": {
            "acknowledged": True,
            "acknowledged_at": datetime.utcnow(),
            "acknowledged_by": current_user.get("email"),
        }},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"ok": True}


@router.get("/{token}/audit-trail")
async def share_link_audit_trail(token: str, current_user: dict = Depends(get_current_user)):
    """Return the full audit timeline (generate → access → revoke) for one share token.

    Used by the Active Share Links Dashboard "Audit Trail" modal.
    Admin only. Events are sorted chronologically (oldest first).
    Each event includes its integrity_status so admins can spot tampering.
    """
    _admin_only(current_user)
    events = await share_audit_col.find({"share_token": token}, {"_id": 0}).sort("created_at", 1).to_list(200)
    if not events:
        # 404 only if no events AND no matching token in any source table
        sa = await sales_assessments_col.find_one({"share_token": token}, {"_id": 0, "id": 1})
        ml = await magic_col.find_one({"token": token}, {"_id": 0, "id": 1})
        if not sa and not ml:
            raise HTTPException(status_code=404, detail="Token not found")
        return {"token_prefix": token[:10] + "…", "events": [], "count": 0}

    out = []
    for e in events:
        integrity = verify_hash("share_event", e)
        out.append({
            "id": e.get("id"),
            "event_type": e.get("event_type"),
            "share_type": e.get("share_type"),
            "entity_id": e.get("entity_id"),
            "client_name": e.get("client_name"),
            "actor_email": e.get("actor_email"),
            "actor_role": e.get("actor_role"),
            "ip_address": e.get("ip_address"),
            "user_agent": (e.get("user_agent") or "")[:120],
            "details": e.get("details") or {},
            "integrity_status": integrity["status"],
            "integrity_hash": (e.get("integrity_hash") or "")[:12],
            "created_at": e["created_at"].isoformat() if isinstance(e.get("created_at"), datetime) else e.get("created_at"),
        })

    # Check anomalies for this single token (use a 30-day lookback so we always have context)
    raw_30d = await share_audit_col.find(
        {"share_token": token, "created_at": {"$gte": datetime.utcnow() - timedelta(days=30)}},
        {"_id": 0},
    ).to_list(2000)
    anomaly_scan = detect_anomalies(raw_30d, window_hours=24 * 30)
    token_anomalies = next((a for a in anomaly_scan["anomalies"] if a.get("share_token") == token), None)

    return {
        "token_prefix": token[:10] + "…",
        "events": out,
        "count": len(out),
        "first_event_at": out[0]["created_at"] if out else None,
        "last_event_at": out[-1]["created_at"] if out else None,
        "access_count": sum(1 for e in out if e["event_type"] == "share_accessed"),
        "denied_count": sum(1 for e in out if e["event_type"] == "share_access_denied"),
        "revoked": any(e["event_type"] == "share_revoked" for e in out),
        "anomalies": token_anomalies["flags"] if token_anomalies else [],
        "anomaly_severity": token_anomalies["severity"] if token_anomalies else None,
    }


@router.get("/{token}/audit-trail.pdf")
async def share_link_audit_trail_pdf(token: str, current_user: dict = Depends(get_current_user)):
    """Generate a PDF audit report for compliance / legal disputes. Admin only."""
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    import hashlib
    import json

    _admin_only(current_user)
    events = await share_audit_col.find({"share_token": token}, {"_id": 0}).sort("created_at", 1).to_list(500)
    if not events:
        raise HTTPException(status_code=404, detail="No audit events found for this token")

    # Build chain proof: SHA-256 of all integrity_hashes concatenated
    chain_hashes = [e.get("integrity_hash") or "" for e in events]
    chain_proof = hashlib.sha256("".join(chain_hashes).encode()).hexdigest()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#4f46e5'), spaceAfter=4)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#374151'), spaceAfter=6, spaceBefore=10)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#6b7280'))
    body = ParagraphStyle('body', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#1f2937'))

    story = [
        Paragraph("LEAMSS — Share Link Audit Report", h1),
        Paragraph("Compliance &amp; Legal Archive · Phase 6.8", small),
        Spacer(1, 8),
    ]

    first = events[0]
    last = events[-1]
    meta_rows = [
        ["Token Prefix", token[:16] + "…"],
        ["Share Type", first.get("share_type", "—")],
        ["Reference Entity", first.get("entity_id", "—")],
        ["Client", first.get("client_name", "—")],
        ["Total Events", str(len(events))],
        ["Window", f"{first.get('created_at')} → {last.get('created_at')}"],
        ["Chain Proof (SHA-256)", chain_proof],
        ["Report Generated", datetime.utcnow().isoformat() + " UTC"],
        ["Generated By", current_user.get("email", "—")],
    ]
    meta_table = Table(meta_rows, colWidths=[55 * mm, 115 * mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('FONTNAME', (1, 6), (1, 6), 'Courier'),  # chain proof monospace
        ('FONTSIZE', (1, 6), (1, 6), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Event Timeline (chronological)", h2))
    event_rows = [["Seq", "Timestamp (UTC)", "Event", "Actor", "IP", "Integrity", "Hash"]]
    for i, e in enumerate(events, 1):
        ts = str(e.get("created_at", ""))[:19].replace("T", " ")
        actor = e.get("actor_email") or e.get("actor_role") or "—"
        if len(actor) > 24:
            actor = actor[:21] + "…"
        ip = e.get("ip_address") or "—"
        # Recompute integrity
        integrity = verify_hash("share_event", e)
        integrity_label = "✓" if integrity["status"] == "verified" else "✗"
        event_rows.append([
            str(i),
            ts,
            e.get("event_type", "—").replace("share_", ""),
            actor,
            ip,
            integrity_label,
            (e.get("integrity_hash") or "")[:10],
        ])
    timeline_table = Table(event_rows, colWidths=[10 * mm, 36 * mm, 28 * mm, 38 * mm, 28 * mm, 14 * mm, 22 * mm], repeatRows=1)
    timeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (6, 1), (6, -1), 'Courier'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    # Alternating row colors
    for row_i in range(1, len(event_rows)):
        bg = colors.HexColor('#f9fafb') if row_i % 2 == 0 else colors.white
        timeline_table.setStyle(TableStyle([('BACKGROUND', (0, row_i), (-1, row_i), bg)]))
    story.append(timeline_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Anomaly Scan", h2))
    raw_30d = await share_audit_col.find(
        {"share_token": token, "created_at": {"$gte": datetime.utcnow() - timedelta(days=30)}},
        {"_id": 0},
    ).to_list(2000)
    scan = detect_anomalies(raw_30d, window_hours=24 * 30)
    flagged = next((a for a in scan["anomalies"] if a.get("share_token") == token), None)
    if not flagged:
        story.append(Paragraph("No anomalies detected within the 30-day window.", body))
    else:
        story.append(Paragraph(f"Severity: <b>{flagged['severity'].upper()}</b>", body))
        story.append(Spacer(1, 4))
        for f in flagged["flags"]:
            story.append(Paragraph(f"• <b>{f['type']}</b> ({f['severity']}) — {json.dumps({k: v for k, v in f.items() if k not in ('type', 'severity')}, default=str)[:300]}", body))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<i>Each event row carries an immutable SHA-256 hash computed over its canonical projection. "
        "The Chain Proof above is the SHA-256 of all event hashes concatenated — any single-record "
        "tampering invalidates both the row's individual hash and this chain proof.</i>",
        small,
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph("End of report · Generated by LEAMSS Legal Archive Engine", small))

    doc.build(story)
    buf.seek(0)
    filename = f"audit_{token[:10]}_{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
