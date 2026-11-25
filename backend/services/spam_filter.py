"""Spam and Fake Lead Detection Service for LEAMSS CRM.
Detects, filters, and blocks bot spam, scam submissions, disposable emails, and test entries.
"""
import re
from typing import Dict, Any, Optional

SPAM_NAME_PATTERNS = [
    r"scam\s*service",
    r"myxa\.cc",
    r"<a\s+href",
    r"\[url=",
    r"https?://",
    r"www\.",
    r"^\s*\*\s*\*\s*\*",
    r"hs=[a-f0-9]{20,}",
    r"ххх",
    r"casino",
    r"viagra",
    r"cryptocurrency\s*giveaway",
    r"\btest\s+(lead|client|user|visitor|integration)\b",
    r"^integration\s+test",
    r"^sample\s+lead",
    r"^fake\s+lead",
    r"^mock\s+lead",
    r"^dummy\s+lead"
]

DISPOSABLE_OR_TEST_DOMAINS = [
    "merepost.com",
    "myxa.cc",
    "example.com",
    "mailinator.com",
    "tempmail.com",
    "temp-mail.org",
    "guerrillamail.com",
    "10minutemail.com",
    "sharklasers.com",
    "dispostable.com",
    "throwawaymail.com",
    "trashmail.com",
    "yopmail.com",
    "fake.com",
    "test.com"
]

DUMMY_TEST_EMAILS = {
    "abc@gmail.com"
}


def is_spam_or_fake_lead(data: Dict[str, Any]) -> bool:
    """Returns True if the lead data matches malicious bot spam, scam promotions, or disposable spam domains."""
    name = str(data.get("name") or "").strip().lower()
    email = str(data.get("email") or "").strip().lower()
    phone = str(data.get("phone") or "").strip()
    msg = str(data.get("message") or data.get("msg") or "").strip().lower()
    source = str(data.get("source") or "").strip().lower()

    if source in ["sample leads"]:
        return True

    # 1. Check Name patterns for automated bot/scam promotions
    for pat in SPAM_NAME_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return True

    # 2. Check Email domains and known bot formats
    if email:
        if email in DUMMY_TEST_EMAILS:
            return True
        if any(email.endswith(f"@{d}") or f"@{d}" in email for d in DISPOSABLE_OR_TEST_DOMAINS):
            return True
        if "~" in email or "merepost" in email or "myxa" in email:
            return True
        # Check repeated characters like sahil1111111111111111111111111111111@gmail.com
        if re.search(r"(.)\1{12,}", email):
            return True

    # 3. Check Message for malicious spam promotions
    if msg:
        if any(k in msg for k in ["myxa.cc", "scam service", "<a href", "[url=", "casino", "viagra"]):
            return True

    # 4. Check Phone for confirmed bot spam signatures
    clean_phone = re.sub(r"[^\d]", "", phone)
    if clean_phone in [
        "840407572018",
        "0000000000"
    ]:
        return True

    return False


def get_spam_reason(data: Dict[str, Any]) -> Optional[str]:
    """Returns human-readable explanation if lead is spam, else None."""
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    msg = str(data.get("message") or data.get("msg") or "").strip()
    source = str(data.get("source") or "").strip()

    if source.lower() == "sample leads":
        return "Sample/test fixture source"
    for pat in SPAM_NAME_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return f"Spam keywords in name: {name}"
    if email:
        for d in DISPOSABLE_OR_TEST_DOMAINS:
            if email.endswith(f"@{d}"):
                return f"Disposable or test email domain: {d}"
        if "~" in email or "merepost" in email:
            return "Spam mail domain signature"
    if msg and any(k in msg.lower() for k in ["myxa.cc", "scam service", "<a href", "[url="]):
        return "Spam promotion link in message"
    return None
