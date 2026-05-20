"""SHA-256 tamper-detection for legal records.

Each immutable record (consent / signature / invoice / share_event) gets an
`integrity_hash` computed at insert-time over a canonical projection of its
fields. The bulk-verify endpoint recomputes the hash and flags any drift as
`tampered`.

CANONICAL DATETIME RULE
=======================
All datetime fields are normalised to NAIVE UTC + ISO format before hashing.
Reason: MongoDB BSON drops tzinfo on retrieval, so pre-insert (tz-aware) and
post-fetch (naive) values must produce the same canonical string.

Legacy records inserted before this fix used tz-aware ISO (e.g. `+00:00`
suffix) — those are detectable via `compute_hash_legacy()` and can be safely
re-hashed via the `/legal-archive/integrity/rehash-legacy` endpoint.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _norm(v: Any) -> Any:
    """Canonical normalisation. Strips tzinfo + rounds floats so JSON is reproducible."""
    if isinstance(v, datetime):
        # Strip tzinfo — Mongo returns naive datetimes, so both pre-insert
        # (typically tz-aware) and post-fetch (naive) values produce the same
        # canonical string.
        if v.tzinfo is not None:
            v = v.replace(tzinfo=None)
        return v.isoformat()
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm(v[k]) for k in sorted(v.keys())}
    return v


def _norm_legacy(v: Any) -> Any:
    """Old behaviour — keeps tzinfo on datetimes (so ISO includes `+00:00`).
    Only used by `compute_hash_legacy` to detect records that were hashed under
    the previous (pre-Phase 6.7) convention.
    """
    if isinstance(v, datetime):
        # Assume legacy records were tz-aware UTC if currently naive.
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, list):
        return [_norm_legacy(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm_legacy(v[k]) for k in sorted(v.keys())}
    return v


# Field projections per record type — only IMMUTABLE fields go into the hash.
PROJECTIONS = {
    "consent": [
        "id", "reference_id", "pre_assessment_id", "pa_number",
        "to_email", "to_name", "channel", "subject", "body_snapshot", "created_at",
    ],
    "signature": [
        "id", "pre_assessment_id", "user_id", "user_email",
        "typed_name", "consent_text", "ip_address", "user_agent",
        "file_size", "signed_at",
    ],
    "invoice": [
        "id", "reference_id", "pre_assessment_id", "pa_number",
        "client_email", "client_name", "amount_received_total",
        "channel", "message", "sent_by", "sent_at",
    ],
    "share_event": [
        "id", "reference_id", "event_type", "share_type", "share_token",
        "entity_id", "entity_kind", "client_name", "client_email",
        "actor_id", "actor_email", "actor_role",
        "ip_address", "user_agent", "details", "created_at",
    ],
}


def canonical_payload(record_type: str, doc: dict) -> dict:
    fields = PROJECTIONS.get(record_type)
    if not fields:
        raise ValueError(f"Unknown record_type: {record_type}")
    return {f: _norm(doc.get(f)) for f in fields}


def compute_hash(record_type: str, doc: dict) -> str:
    payload = canonical_payload(record_type, doc)
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_hash_legacy(record_type: str, doc: dict) -> str:
    """Recompute the hash using the pre-Phase-6.7 (tz-aware ISO) algorithm.
    Used by the backfill endpoint to distinguish 'precision-bug tampered' from
    'genuinely tampered' records.
    """
    fields = PROJECTIONS.get(record_type)
    if not fields:
        raise ValueError(f"Unknown record_type: {record_type}")
    payload = {f: _norm_legacy(doc.get(f)) for f in fields}
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_hash(record_type: str, doc: dict) -> dict:
    """Returns {ok, expected, actual, tampered}.
    Records that lack a stored hash are flagged `unverified` rather than tampered.
    """
    actual = doc.get("integrity_hash")
    expected = compute_hash(record_type, doc)
    if not actual:
        return {"ok": False, "status": "unverified", "expected": expected, "actual": None}
    if actual != expected:
        return {"ok": False, "status": "tampered", "expected": expected, "actual": actual}
    return {"ok": True, "status": "verified", "expected": expected, "actual": actual}
