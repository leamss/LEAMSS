"""Anomaly Alert Dispatcher.

When a HIGH-severity share-link anomaly is detected, this module:
  1. Records the alert in `anomaly_alerts` (de-duplicated per token per hour).
  2. Optionally fires a Slack webhook (if SLACK_WEBHOOK_URL env is set).
  3. Optionally sends an admin email (if RESEND_API_KEY is set — currently a no-op).
  4. Returns a structured `dispatch_result` so the caller can display in-UI.

The internal `anomaly_alerts` feed is always populated regardless of external
webhook availability — visible in the Audit Insights Dashboard.
"""
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx

from core.database import db

alerts_col = db["anomaly_alerts"]

# De-duplication window — don't spam the same token's alert more than once / hour.
DEDUP_WINDOW = timedelta(hours=1)


async def _send_slack(anomaly: dict, webhook_url: str) -> bool:
    """POST a formatted Slack message. Returns True on success."""
    try:
        flags = anomaly.get("flags", [])
        flag_lines = "\n".join(
            f"• *{f['type']}* ({f.get('severity', '?')}) — count: {f.get('count', '?')}"
            for f in flags
        )
        payload = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "🔥 High-Severity Anomaly Detected"}},
                {"type": "section", "fields": [
                    {"type": "mrkdwn", "text": f"*Client:*\n{anomaly.get('client_name', '—')}"},
                    {"type": "mrkdwn", "text": f"*Token:*\n`{anomaly.get('token_prefix', '?')}`"},
                    {"type": "mrkdwn", "text": f"*Entity:*\n{anomaly.get('entity_id', '—')}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{anomaly.get('severity', '?').upper()}"},
                ]},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*Detected Flags:*\n{flag_lines}"}},
                {"type": "context", "elements": [
                    {"type": "mrkdwn", "text": f"_LEAMSS Audit Engine · {datetime.utcnow().isoformat()}Z_"},
                ]},
            ],
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(webhook_url, json=payload)
            return 200 <= r.status_code < 300
    except Exception:
        return False


async def dispatch_alert(anomaly: dict, channels: Optional[list[str]] = None) -> dict:
    """Send an alert for a single anomaly. De-duplicated per token per hour.

    Args:
      anomaly: a single anomaly dict from `detect_anomalies()`
      channels: optionally restrict to ['slack', 'email', 'internal']. Default = all available.
    """
    if anomaly.get("severity") != "high":
        return {"sent": False, "reason": "below_threshold"}

    token = anomaly.get("share_token")
    if not token:
        return {"sent": False, "reason": "no_token"}

    # Dedup check
    since = datetime.utcnow() - DEDUP_WINDOW
    existing = await alerts_col.find_one(
        {"share_token": token, "created_at": {"$gte": since}},
        {"_id": 0, "id": 1, "created_at": 1},
    )
    if existing:
        return {"sent": False, "reason": "deduped", "previous_alert_at": existing["created_at"].isoformat()}

    channels = channels or ["slack", "email", "internal"]
    result = {"sent": True, "channels": {}, "anomaly_token": token}

    # 1) Slack (if configured)
    if "slack" in channels:
        webhook = os.environ.get("SLACK_WEBHOOK_URL")
        if webhook:
            ok = await _send_slack(anomaly, webhook)
            result["channels"]["slack"] = "delivered" if ok else "failed"
        else:
            result["channels"]["slack"] = "no_webhook_configured"

    # 2) Email (Resend) — stub until RESEND_API_KEY provided
    if "email" in channels:
        if os.environ.get("RESEND_API_KEY"):
            result["channels"]["email"] = "not_implemented_yet"
        else:
            result["channels"]["email"] = "no_api_key"

    # 3) Internal feed (always)
    if "internal" in channels:
        now = datetime.utcnow()
        alert_doc = {
            "id": f"AL-{now.strftime('%Y%m%d-%H%M%S')}-{token[:6]}",
            "share_token": token,
            "token_prefix": anomaly.get("token_prefix"),
            "client_name": anomaly.get("client_name"),
            "entity_id": anomaly.get("entity_id"),
            "share_type": anomaly.get("share_type"),
            "severity": anomaly.get("severity"),
            "flag_types": [f.get("type") for f in anomaly.get("flags", [])],
            "flags": anomaly.get("flags", []),
            "created_at": now,
            "delivery": result["channels"],
            "acknowledged": False,
        }
        await alerts_col.insert_one(alert_doc)
        result["channels"]["internal"] = "recorded"
        result["alert_id"] = alert_doc["id"]

    return result


async def dispatch_all_high_severity(scan_result: dict) -> dict:
    """Process all high-severity anomalies from a `detect_anomalies()` result.

    Returns a summary {processed, sent, deduped}.
    """
    sent = 0
    deduped = 0
    failed = 0
    details = []
    for a in scan_result.get("anomalies", []):
        if a.get("severity") != "high":
            continue
        d = await dispatch_alert(a)
        details.append({"token_prefix": a.get("token_prefix"), **d})
        if d.get("sent"):
            sent += 1
        elif d.get("reason") == "deduped":
            deduped += 1
        else:
            failed += 1
    return {"processed": len(details), "sent": sent, "deduped": deduped, "failed": failed, "details": details}
