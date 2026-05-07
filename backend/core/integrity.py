"""SHA-256 tamper-detection for legal records.

Each immutable record (consent / signature / invoice) gets an `integrity_hash`
computed at insert-time over a canonical projection of its fields.
The bulk-verify endpoint recomputes the hash and flags any drift as `tampered`.
"""
import hashlib
import json
from datetime import datetime
from typing import Any


def _norm(v: Any) -> Any:
    """Normalize values so the canonical JSON is reproducible across timezones / float widths."""
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm(v[k]) for k in sorted(v.keys())}
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
