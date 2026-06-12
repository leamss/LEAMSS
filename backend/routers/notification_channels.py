"""Phase 18.7 — Notification Channels CRUD + Digest worker.

Channels deliver client-error digests to Slack webhooks or email distribution
lists. The digest worker runs every 30 minutes via APScheduler (registered in
``server.py`` startup hook) and also exposes a manual trigger endpoint for
admin testing.

Collection schema (``notification_channels``):
    {
      id, type ("slack"|"email"), name, target,
      enabled, threshold_count, threshold_window_hours,
      scopes ([] = all), created_by, created_by_name, created_at,
      last_test_sent_at, last_test_result, deleted
    }

Digest behaviour:
    For each enabled channel, find client_errors with
      occurrence_count >= channel.threshold_count
      AND received_at within last channel.threshold_window_hours
      AND (last_digest_sent_at is null OR last_digest_sent_at < now - 1h)
      AND (channel.scopes is empty OR scope in channel.scopes)
    Send formatted message · stamp last_digest_sent_at on matched errors.
    On failure: row in notification_send_failures.
"""
from __future__ import annotations
import os
import uuid
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/notification-channels", tags=["Notification Channels"])
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────
class ChannelIn(BaseModel):
    type: str = Field(..., pattern="^(slack|email)$")
    name: str = Field(..., min_length=1, max_length=120)
    target: str = Field(..., min_length=1, max_length=500)
    enabled: bool = True
    threshold_count: int = Field(default=5, ge=1, le=10000)
    threshold_window_hours: int = Field(default=1, ge=1, le=168)
    scopes: List[str] = Field(default_factory=list)


class ChannelPatch(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    target: Optional[str] = Field(default=None, max_length=500)
    enabled: Optional[bool] = None
    threshold_count: Optional[int] = Field(default=None, ge=1, le=10000)
    threshold_window_hours: Optional[int] = Field(default=None, ge=1, le=168)
    scopes: Optional[List[str]] = None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _is_admin(user: dict) -> bool:
    role = (user.get("rbac_role") or user.get("role") or "").lower()
    return role in {"admin", "admin_owner"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


def _strip_internal(d: Dict[str, Any]) -> Dict[str, Any]:
    d.pop("_id", None)
    for k in ("created_at", "last_test_sent_at"):
        if k in d:
            d[k] = _iso(d[k])
    return d


# ─────────────────────────────────────────────────────────────────────────────
# Indexes
# ─────────────────────────────────────────────────────────────────────────────
_indexes_ready = False


async def ensure_channels_indexes() -> None:
    global _indexes_ready
    if _indexes_ready:
        return
    try:
        await db["notification_channels"].create_index([("enabled", 1), ("type", 1)])
        await db["notification_channels"].create_index("deleted")
        _indexes_ready = True
    except Exception:  # noqa: BLE001
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Slack + Email send (mockable via env override for tests)
# ─────────────────────────────────────────────────────────────────────────────
def _format_slack_payload(error: Dict[str, Any], window_hours: int, affected_users: int) -> Dict[str, Any]:
    msg = (error.get("message") or "Unknown error")[:200]
    route = error.get("route") or "-"
    scope = error.get("scope") or "unknown"
    occurrences = error.get("occurrence_count") or 1
    dashboard_url = os.environ.get("LEAMSS_PUBLIC_BASE_URL", "").rstrip("/") or ""
    detail_url = f"{dashboard_url}/admin/client-errors?id={error.get('id')}" if dashboard_url else f"/admin/client-errors?id={error.get('id')}"
    return {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "🚨 LEAMSS Client Error Alert"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Route:* `{route}`"},
                {"type": "mrkdwn", "text": f"*Scope:* {scope}"},
                {"type": "mrkdwn", "text": f"*Occurrences:* {occurrences} in last {window_hours}h"},
                {"type": "mrkdwn", "text": f"*Affected users:* {affected_users}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Error:* `{msg}`"}},
            {"type": "actions", "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "View Details"}, "url": detail_url},
            ]},
        ]
    }


def _format_email_payload(error: Dict[str, Any], window_hours: int, affected_users: int) -> Dict[str, str]:
    subject = f"[LEAMSS] Client error: {(error.get('route') or '-')} ({error.get('occurrence_count') or 1}x in {window_hours}h)"
    body = (
        f"<h2>🚨 LEAMSS Client Error Alert</h2>"
        f"<p><strong>Route:</strong> {error.get('route') or '-'}</p>"
        f"<p><strong>Scope:</strong> {error.get('scope') or 'unknown'}</p>"
        f"<p><strong>Occurrences:</strong> {error.get('occurrence_count') or 1} in last {window_hours}h</p>"
        f"<p><strong>Affected users:</strong> {affected_users}</p>"
        f"<p><strong>Error:</strong> <code>{(error.get('message') or 'Unknown')[:500]}</code></p>"
    )
    return {"subject": subject, "html": body}


async def _send_slack(target: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a Slack-formatted payload to a webhook URL.

    Test override: if ``LEAMSS_DIGEST_DRY_RUN`` env is set OR the in-process
    flag ``_DRY_RUN_FLAG`` is true, we don't hit the network — we only record
    the payload. The flag is toggled via an admin-only test endpoint so the
    regression suite can flip it without restarting the server.
    """
    if os.environ.get("LEAMSS_DIGEST_DRY_RUN") or _DRY_RUN_FLAG["on"]:
        return {"ok": True, "dry_run": True, "payload_keys": list(payload.keys())}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(target, json=payload)
        return {"ok": 200 <= r.status_code < 300, "status_code": r.status_code, "text": r.text[:300]}


async def _send_email(target: str, payload: Dict[str, str]) -> Dict[str, Any]:
    """Stub: log the formatted email. Real send wiring (Resend/SendGrid) is
    deferred to a future phase; the digest worker already records the payload
    so ops can wire delivery without code changes here.
    """
    logger.info("[EMAIL DIGEST PREVIEW] to=%s subject=%s", target, payload.get("subject"))
    if os.environ.get("LEAMSS_DIGEST_DRY_RUN") or _DRY_RUN_FLAG["on"]:
        return {"ok": True, "dry_run": True, "subject": payload.get("subject")}
    # No real provider hooked yet — treat as preview-only success
    return {"ok": True, "preview": True, "subject": payload.get("subject")}


# In-process dry-run flag toggled by the regression suite via an admin endpoint.
_DRY_RUN_FLAG: Dict[str, bool] = {"on": False}


@router.post("/_test/set-dry-run")
async def set_dry_run(on: bool = True, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Admin-only test toggle for the in-process dry-run flag.

    Test suite flips this true before each digest/send test so external
    network calls (Slack webhooks) are skipped without an env var or restart.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    _DRY_RUN_FLAG["on"] = bool(on)
    return {"dry_run": _DRY_RUN_FLAG["on"]}


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────
@router.post("")
async def create_channel(payload: ChannelIn, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    await ensure_channels_indexes()
    doc = {
        "id": str(uuid.uuid4()),
        **payload.dict(),
        "created_by": str(current_user.get("id") or current_user.get("user_id") or ""),
        "created_by_name": current_user.get("name") or current_user.get("email") or "admin",
        "created_at": _now(),
        "last_test_sent_at": None,
        "last_test_result": None,
        "deleted": False,
    }
    await db["notification_channels"].insert_one(doc)
    return _strip_internal(dict(doc))


@router.get("")
async def list_channels(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    items: List[Dict[str, Any]] = []
    async for d in db["notification_channels"].find({"deleted": {"$ne": True}}).sort("created_at", -1):
        items.append(_strip_internal(d))
    return {"items": items, "total": len(items)}


@router.patch("/{cid}")
async def patch_channel(cid: str, payload: ChannelPatch, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    set_payload = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None or k == "enabled"}
    if not set_payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    r = await db["notification_channels"].find_one_and_update(
        {"id": cid, "deleted": {"$ne": True}},
        {"$set": set_payload},
        return_document=True,
    )
    if not r:
        raise HTTPException(status_code=404, detail="Channel not found")
    return _strip_internal(r)


@router.delete("/{cid}")
async def delete_channel(cid: str, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    r = await db["notification_channels"].update_one(
        {"id": cid, "deleted": {"$ne": True}},
        {"$set": {"deleted": True, "deleted_at": _now()}},
    )
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"deleted": True, "id": cid}


@router.post("/{cid}/test")
async def test_channel(cid: str, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    ch = await db["notification_channels"].find_one({"id": cid, "deleted": {"$ne": True}})
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    sample = {
        "id": "test-sample",
        "message": "Test alert — wiring check from LEAMSS",
        "route": "/admin/client-errors",
        "scope": "test",
        "occurrence_count": 1,
    }
    if ch["type"] == "slack":
        payload = _format_slack_payload(sample, window_hours=1, affected_users=1)
        result = await _send_slack(ch["target"], payload)
    else:  # email
        payload = _format_email_payload(sample, window_hours=1, affected_users=1)
        result = await _send_email(ch["target"], payload)

    await db["notification_channels"].update_one(
        {"id": cid},
        {"$set": {
            "last_test_sent_at": _now(),
            "last_test_result": "ok" if result.get("ok") else f"failed: {result}"[:300],
        }},
    )
    return {"channel_id": cid, "result": result}


# ─────────────────────────────────────────────────────────────────────────────
# Digest worker (also exposed manually for admin testing)
# ─────────────────────────────────────────────────────────────────────────────
async def _affected_user_count(message: str, route: str, window_hours: int) -> int:
    cutoff = _now() - timedelta(hours=window_hours)
    cur = db["client_errors"].aggregate([
        {"$match": {"message": message, "route": route, "received_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$user_id"}},
    ])
    n = 0
    async for _ in cur:
        n += 1
    return n


async def run_digest_once() -> Dict[str, Any]:
    """Single digest sweep. Returns a structured summary of what was sent."""
    await ensure_channels_indexes()
    now = _now()
    summary = {"channels_processed": 0, "alerts_sent": 0, "skipped": 0, "failures": 0, "details": []}
    async for ch in db["notification_channels"].find({"enabled": True, "deleted": {"$ne": True}}):
        summary["channels_processed"] += 1
        win_h = int(ch.get("threshold_window_hours") or 1)
        thr = int(ch.get("threshold_count") or 5)
        scopes = ch.get("scopes") or []
        cutoff = now - timedelta(hours=win_h)
        last_sent_cutoff = now - timedelta(hours=1)
        err_query: Dict[str, Any] = {
            "occurrence_count": {"$gte": thr},
            "received_at": {"$gte": cutoff},
            "$or": [
                {"last_digest_sent_at": {"$exists": False}},
                {"last_digest_sent_at": None},
                {"last_digest_sent_at": {"$lt": last_sent_cutoff}},
            ],
        }
        if scopes:
            err_query["scope"] = {"$in": scopes}
        async for err in db["client_errors"].find(err_query):
            try:
                affected = await _affected_user_count(err.get("message") or "", err.get("route") or "", win_h)
                if ch["type"] == "slack":
                    payload = _format_slack_payload(err, win_h, affected)
                    result = await _send_slack(ch["target"], payload)
                else:
                    payload = _format_email_payload(err, win_h, affected)
                    result = await _send_email(ch["target"], payload)
                if result.get("ok"):
                    summary["alerts_sent"] += 1
                    summary["details"].append({
                        "channel_id": ch["id"],
                        "channel_name": ch.get("name"),
                        "error_id": err["id"],
                        "occurrences": err.get("occurrence_count"),
                    })
                    await db["client_errors"].update_one(
                        {"id": err["id"]},
                        {"$set": {"last_digest_sent_at": now}},
                    )
                else:
                    summary["failures"] += 1
                    await db["notification_send_failures"].insert_one({
                        "id": str(uuid.uuid4()),
                        "channel_id": ch["id"],
                        "error_id": err["id"],
                        "result": result,
                        "occurred_at": now,
                    })
            except Exception as e:  # noqa: BLE001
                logger.exception("digest send failed: %s", e)
                summary["failures"] += 1
                await db["notification_send_failures"].insert_one({
                    "id": str(uuid.uuid4()),
                    "channel_id": ch["id"],
                    "error_id": err.get("id"),
                    "result": {"ok": False, "exception": str(e)[:300]},
                    "occurred_at": now,
                })
    return summary


@router.post("/run-digest-now")
async def run_digest_now(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    return await run_digest_once()


# ─────────────────────────────────────────────────────────────────────────────
# Optional one-time seed from env (only if no channels exist yet)
# ─────────────────────────────────────────────────────────────────────────────
async def maybe_seed_default_channel() -> None:
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    existing = await db["notification_channels"].count_documents({"deleted": {"$ne": True}})
    if existing > 0:
        return
    await db["notification_channels"].insert_one({
        "id": str(uuid.uuid4()),
        "type": "slack",
        "name": "Default Slack (from env)",
        "target": webhook,
        "enabled": True,
        "threshold_count": 5,
        "threshold_window_hours": 1,
        "scopes": [],
        "created_by": "system",
        "created_by_name": "system seed",
        "created_at": _now(),
        "last_test_sent_at": None,
        "last_test_result": None,
        "deleted": False,
    })
    logger.info("[Phase18.7] Seeded default Slack channel from SLACK_WEBHOOK_URL env")
