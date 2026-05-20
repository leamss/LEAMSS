"""Share Link Audit Log — Phase 6.7

Records every lifecycle event of a public share link (generate / access / revoke)
into a tamper-evident audit collection. Surfaced in the Legal Archive timeline.

Events tracked:
  • share_generated  — sales rep / admin creates a public link
  • share_accessed   — anyone hits the public URL (no-auth)
  • share_revoked    — admin revokes either from the assessment page
                       or from the Active Share Links dashboard

Each event is stored with a SHA-256 `integrity_hash` (canonical payload)
so that the timeline cannot be silently mutated.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.database import db
from core.integrity import compute_hash

share_audit_col = db["share_audit_events"]


async def record_share_event(
    *,
    event_type: str,
    share_type: str,
    share_token: str,
    reference_id: Optional[str] = None,
    reference_kind: Optional[str] = None,
    client_name: Optional[str] = None,
    client_email: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    actor_role: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
) -> dict:
    """Insert a single audit event into `share_audit_events`.

    `event_type` must be one of: share_generated | share_accessed | share_revoked.
    `share_type` matches the dashboard taxonomy: sales_report | magic_portal | public_pa_fee.
    `reference_id` = the entity id (SAH-* or PA-*) so the event can be timeline-grouped.

    Returns the inserted document (without `_id`).
    """
    if event_type not in {"share_generated", "share_accessed", "share_access_denied", "share_revoked", "share_emailed"}:
        raise ValueError(f"Invalid event_type: {event_type}")

    now = datetime.now(timezone.utc)
    # BSON stores datetime at millisecond precision AND drops tzinfo on retrieval.
    # To make the hash reproducible, normalise to naive UTC + millisecond precision.
    now = now.replace(microsecond=(now.microsecond // 1000) * 1000, tzinfo=None)
    event_id = f"SAE-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    token_prefix = (share_token or "")[:10] + "…" if share_token else None

    doc = {
        "id": event_id,
        "reference_id": f"SAE-{event_id[4:]}",  # `SAE-<ts>-<rand>` displayed in Legal Archive
        "event_type": event_type,
        "share_type": share_type,
        "share_token": share_token,
        "share_token_prefix": token_prefix,
        "entity_id": reference_id,
        "entity_kind": reference_kind,  # 'sales_assessment' | 'pa' | etc.
        "client_name": client_name,
        "client_email": client_email,
        "actor_id": actor_id,
        "actor_email": actor_email,
        "actor_role": actor_role,
        "ip_address": ip_address,
        "user_agent": (user_agent or "")[:240] if user_agent else None,
        "details": details or {},
        "created_at": now,
    }
    # SHA-256 over canonical payload — tamper-evident
    doc["integrity_hash"] = compute_hash("share_event", doc)
    await share_audit_col.insert_one(doc)
    doc.pop("_id", None)
    return doc
