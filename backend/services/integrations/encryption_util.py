"""Encryption and secret masking utility for Integration credentials."""
import os
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet

_SECRET = os.environ.get("JWT_SECRET", "leamss-portal-secret-key-2024-secure")
# Derive 32-byte key for Fernet
_KEY = base64.urlsafe_b64encode(hashlib.sha256(_SECRET.encode("utf-8")).digest())
_cipher = Fernet(_KEY)


def encrypt_secret(val: Optional[str]) -> str:
    """Encrypt plain secret or token string."""
    if not val:
        return ""
    try:
        return _cipher.encrypt(val.encode("utf-8")).decode("utf-8")
    except Exception:
        return val


def decrypt_secret(val: Optional[str]) -> str:
    """Decrypt encrypted secret or token string."""
    if not val:
        return ""
    try:
        return _cipher.decrypt(val.encode("utf-8")).decode("utf-8")
    except Exception:
        # In case value was stored unencrypted
        return val


def mask_secret(val: Optional[str]) -> str:
    """Mask secret value for safe client UI display."""
    if not val:
        return ""
    plain = decrypt_secret(val)
    if not plain:
        return ""
    if len(plain) <= 8:
        return "••••••••"
    return f"{plain[:4]}••••••••{plain[-4:]}"
