"""Phase 19.6 — Centralised audit logging service.

All admin-mutating ops should call `log_action(...)` instead of writing to
`audit_logs` directly. Keeps schema, severity, and actor enrichment consistent
across all routers (occupation_master_import, data_import, kb_unified, import_batches).

Schema written to `db.audit_logs`:
    {
        "id": uuid,
        "action": "occupation_master.bulk_import" | "import_batch.revoke" | ...,
        "severity": "info" | "warn" | "critical",
        "user_id": str, "user_name": str | None,
        "ip": str | None,
        "summary": Dict[str, Any],   # action-specific payload
        "at": datetime (UTC),
    }
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)
COLLECTION = "audit_logs"

VALID_SEVERITIES = {"info", "warn", "critical"}


# ─── Option D / X3 — Legacy compat helpers ────────────────────────────────────
# 4 routers (cases.py, documents.py, auth.py, sales.py) defined an identical
# `_log(user_id, action, entity_type, entity_id, details)` helper writing to
# `audit_logs` with `new_value` field. Consolidated here to single canonical impl.

async def log_legacy_event(
    db: AsyncIOMotorDatabase,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> str:
    """Centralised replacement for the 4 duplicated `_log()` helpers.

    Preserves original schema (`new_value=details`) for backward compat.
    """
    event_id = str(uuid.uuid4())
    await db[COLLECTION].insert_one({
        "id": event_id,
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "new_value": details,
        "created_at": datetime.now(timezone.utc),
    })
    return event_id


async def log_action(
    db: AsyncIOMotorDatabase,
    *,
    action: str,
    user_id: str,
    summary: Dict[str, Any],
    user_name: Optional[str] = None,
    severity: str = "info",
    ip: Optional[str] = None,
) -> None:
    """Persist an audit log row. Never raises — logs warning on failure.

    Args:
        action: Dot-separated event id e.g. 'import_batch.revoke'.
        user_id: Actor user-id (or email if no id).
        summary: Action-specific structured payload (always JSON-serialisable).
        user_name: Optional display name of actor.
        severity: 'info' | 'warn' | 'critical' (critical for force-revoke etc).
        ip: Optional client IP.
    """
    if severity not in VALID_SEVERITIES:
        severity = "info"
    doc = {
        "id": str(uuid.uuid4()),
        "action": action,
        "severity": severity,
        "user_id": user_id,
        "user_name": user_name,
        "ip": ip,
        "summary": summary,
        "at": datetime.now(timezone.utc),
    }
    try:
        await db[COLLECTION].insert_one(doc)
    except Exception as e:  # noqa: BLE001
        logger.warning("audit log write failed for action=%s: %s", action, e)
