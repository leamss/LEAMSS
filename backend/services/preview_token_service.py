"""Phase 19.6 — Short-lived signed preview tokens.

Issued by `POST /api/occupation-master/import/preview` and required by
`POST /api/occupation-master/import/commit`. Prevents commits without a
prior dry-run review.

Token format: `<file_sha256>.<expiry_iso>.<hmac_sig>`
Lifetime: 5 minutes from issue.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone, timedelta

TOKEN_LIFETIME_SECONDS = 300  # 5 minutes


def _signing_key() -> bytes:
    secret = os.environ.get("JWT_SECRET") or os.environ.get("PREVIEW_TOKEN_SECRET") or "phase19.6-default-key"
    return secret.encode()


def issue_preview_token(file_content: bytes) -> str:
    """Produce a signed token tied to the file's SHA-256 + 5-min expiry."""
    file_hash = hashlib.sha256(file_content).hexdigest()
    expiry = int(time.time() + TOKEN_LIFETIME_SECONDS)
    payload = f"{file_hash}.{expiry}".encode()
    sig = hmac.new(_signing_key(), payload, hashlib.sha256).hexdigest()
    return f"{file_hash}.{expiry}.{sig}"


def verify_preview_token(token: str, file_content: bytes) -> bool:
    """Validate the token matches the exact file content + is non-expired."""
    try:
        file_hash, expiry_s, sig = token.split(".")
        expiry = int(expiry_s)
    except (ValueError, AttributeError):
        return False
    if expiry < int(time.time()):
        return False
    actual_hash = hashlib.sha256(file_content).hexdigest()
    if not hmac.compare_digest(file_hash, actual_hash):
        return False
    payload = f"{file_hash}.{expiry}".encode()
    expected_sig = hmac.new(_signing_key(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)
