"""Audit Insights Dashboard — Phase 6.9b

Standalone admin page surfacing aggregate insights from the share-audit log:
  • Top-10 anomaly tokens (severity-weighted)
  • Daily trend chart (events / day for last 30 days, split by type)
  • Share-type breakdown (sales_report vs magic_portal vs public_pa_fee)
  • Top-flagging IPs (most denied, multi-token reach)
  • Compliance Report PDF — all share events from last quarter (90 days default)

Endpoints (all admin only):
  GET  /api/audit-insights/overview?days=30
  GET  /api/audit-insights/compliance-report.pdf?days=90
"""
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from io import BytesIO
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from core.auth import get_current_user
from core.database import db
from core.anomaly_detector import detect_anomalies
from core.integrity import verify_hash

share_audit_col = db["share_audit_events"]
alerts_col = db["anomaly_alerts"]

router = APIRouter(prefix="/audit-insights", tags=["Audit Insights"])


def _admin_only(user: dict):
    role = (user.get("rbac_role") or user.get("role") or "").lower()
    perms = user.get("permissions") or []
    if role in ("admin", "admin_owner") or "*" in perms:
        return
    raise HTTPException(status_code=403, detail="Admin only")


@router.get("/overview")
async def overview(days: int = Query(30, ge=1, le=180), current_user: dict = Depends(get_current_user)):
    """Aggregate insights for the admin dashboard."""
    _admin_only(current_user)
    since = datetime.utcnow() - timedelta(days=days)

    events = await share_audit_col.find(
        {"created_at": {"$gte": since}},
        {"_id": 0},
    ).to_list(50000)

    # Build daily trend buckets
    by_day_total: Counter = Counter()
    by_day_by_type: dict[str, Counter] = defaultdict(Counter)
    type_counts: Counter = Counter()
    share_type_counts: Counter = Counter()
    ip_counts: Counter = Counter()
    denied_by_ip: Counter = Counter()
    distinct_tokens_per_ip: dict[str, set[str]] = defaultdict(set)

    for e in events:
        ts = e.get("created_at")
        if not ts:
            continue
        if hasattr(ts, "tzinfo") and ts.tzinfo is None:
            ts = ts.replace(tzinfo=None)
        day = ts.strftime("%Y-%m-%d")
        evt = e.get("event_type", "unknown")
        by_day_total[day] += 1
        by_day_by_type[day][evt] += 1
        type_counts[evt] += 1
        share_type_counts[e.get("share_type", "?")] += 1
        ip = e.get("ip_address")
        if ip:
            ip_counts[ip] += 1
            distinct_tokens_per_ip[ip].add(e.get("share_token") or "")
            if evt == "share_access_denied":
                denied_by_ip[ip] += 1

    # Fill in zero-days so the chart is continuous
    today = datetime.utcnow().date()
    trend = []
    for d in range(days, -1, -1):
        day = (today - timedelta(days=d)).strftime("%Y-%m-%d")
        trend.append({
            "date": day,
            "total": by_day_total.get(day, 0),
            "generated": by_day_by_type[day].get("share_generated", 0),
            "accessed": by_day_by_type[day].get("share_accessed", 0),
            "denied": by_day_by_type[day].get("share_access_denied", 0),
            "revoked": by_day_by_type[day].get("share_revoked", 0),
        })

    # Run anomaly scan to get top tokens
    scan = detect_anomalies(events, window_hours=days * 24)
    top_anomalies = scan["anomalies"][:10]

    # Top IPs (most active + multi-token reach + denials)
    top_ips = sorted(
        [
            {
                "ip": ip,
                "total_events": cnt,
                "distinct_tokens": len(distinct_tokens_per_ip[ip]),
                "denied_count": denied_by_ip.get(ip, 0),
            }
            for ip, cnt in ip_counts.items()
        ],
        key=lambda x: (x["denied_count"], x["distinct_tokens"], x["total_events"]),
        reverse=True,
    )[:10]

    # Recent unacknowledged alerts
    recent_alerts = await alerts_col.find(
        {"acknowledged": False},
        {"_id": 0},
    ).sort("created_at", -1).limit(5).to_list(5)
    for a in recent_alerts:
        if isinstance(a.get("created_at"), datetime):
            a["created_at"] = a["created_at"].isoformat()

    return {
        "window_days": days,
        "total_events": len(events),
        "by_event_type": dict(type_counts),
        "by_share_type": dict(share_type_counts),
        "trend": trend,
        "top_anomalies": top_anomalies,
        "anomaly_summary": scan["summary"],
        "top_ips": top_ips,
        "recent_alerts": recent_alerts,
        "unique_ips": len(ip_counts),
        "unique_tokens": scan["scanned_tokens"],
    }


@router.get("/compliance-report.pdf")
async def compliance_report_pdf(
    days: int = Query(90, ge=7, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Quarterly compliance report (PDF) — all share events + anomaly scan + integrity chain proof."""
    _admin_only(current_user)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    since = datetime.utcnow() - timedelta(days=days)
    events = await share_audit_col.find(
        {"created_at": {"$gte": since}},
        {"_id": 0},
    ).sort("created_at", 1).to_list(50000)

    # Compute chain proof
    chain_hashes = [e.get("integrity_hash") or "" for e in events]
    chain_proof = hashlib.sha256("".join(chain_hashes).encode()).hexdigest()

    # Anomaly scan
    scan = detect_anomalies(events, window_hours=days * 24)

    # Event-type breakdown
    type_counts: Counter = Counter()
    share_type_counts: Counter = Counter()
    integrity_tampered = 0
    for e in events:
        type_counts[e.get("event_type", "?")] += 1
        share_type_counts[e.get("share_type", "?")] += 1
        if verify_hash("share_event", e)["status"] != "verified":
            integrity_tampered += 1

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#4f46e5'), spaceAfter=4)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#1f2937'), spaceAfter=6, spaceBefore=12)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#6b7280'))

    story = [
        Paragraph("LEAMSS — Compliance Report", h1),
        Paragraph(f"Share-Link Audit Log · {days}-day window · Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", small),
        Spacer(1, 8),
    ]

    # Executive summary table
    summary_rows = [
        ["Window", f"{since.strftime('%Y-%m-%d')} → {datetime.utcnow().strftime('%Y-%m-%d')}"],
        ["Total Events", str(len(events))],
        ["Unique Tokens", str(scan["scanned_tokens"])],
        ["Anomalies — HIGH", str(scan["summary"]["high"])],
        ["Anomalies — MEDIUM", str(scan["summary"]["medium"])],
        ["Anomalies — LOW", str(scan["summary"]["low"])],
        ["Tampered Records", str(integrity_tampered)],
        ["Integrity Chain Proof (SHA-256)", chain_proof],
        ["Generated By", current_user.get("email", "—")],
    ]
    t = Table(summary_rows, colWidths=[55 * mm, 125 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (1, 7), (1, 7), 'Courier'),  # chain proof monospace
        ('FONTSIZE', (1, 7), (1, 7), 6),
    ]))
    story.append(t)

    # Event type breakdown
    story.append(Paragraph("Event Type Breakdown", h2))
    et_rows = [["Event Type", "Count"]] + [[k, str(v)] for k, v in type_counts.most_common()]
    et = Table(et_rows, colWidths=[80 * mm, 30 * mm])
    et.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(et)

    # Share type breakdown
    story.append(Paragraph("Share Type Breakdown", h2))
    st_rows = [["Share Type", "Count"]] + [[k, str(v)] for k, v in share_type_counts.most_common()]
    stb = Table(st_rows, colWidths=[80 * mm, 30 * mm])
    stb.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(stb)

    # Top anomalies (high+medium only)
    if scan["anomalies"]:
        story.append(Paragraph("Top Anomalies", h2))
        rows = [["Severity", "Client", "Token", "Flags"]]
        for a in scan["anomalies"][:25]:
            rows.append([
                a["severity"].upper(),
                (a.get("client_name") or "—")[:30],
                a["token_prefix"],
                ", ".join(f["type"] for f in a["flags"])[:60],
            ])
        at = Table(rows, colWidths=[20 * mm, 50 * mm, 30 * mm, 80 * mm], repeatRows=1)
        at.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(at)

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<i>This report is generated from the LEAMSS share-link audit log. Every event row carries an "
        "immutable SHA-256 hash; the Chain Proof above is the SHA-256 of all event hashes concatenated. "
        "Tampered Records count > 0 indicates that one or more events have been mutated after their "
        "original insertion — those rows are flagged in the per-event integrity scan.</i>",
        small,
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph("End of report · LEAMSS Audit Engine · Phase 6.9b", small))

    doc.build(story)
    buf.seek(0)
    filename = f"leamss_compliance_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
