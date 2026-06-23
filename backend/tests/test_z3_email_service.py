"""Option 1 / Z3 — Email service Resend graceful fallback tests."""
from __future__ import annotations

import os
import pytest


@pytest.mark.asyncio
async def test_z3_preview_mode_when_no_key():
    """Without RESEND_API_KEY → returns preview_only without raising."""
    from services.email_service import send_email
    # Force unset for this test
    saved = os.environ.pop("RESEND_API_KEY", None)
    try:
        result = await send_email(
            to="test@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
        )
        assert result["status"] == "preview_only"
        assert result["to"] == "test@example.com"
        assert result["has_key"] is False
    finally:
        if saved:
            os.environ["RESEND_API_KEY"] = saved


@pytest.mark.asyncio
async def test_z3_preview_logs_audit_fields():
    """Preview return shape must include audit metadata."""
    from services.email_service import send_email
    saved = os.environ.pop("RESEND_API_KEY", None)
    try:
        result = await send_email(
            to="audit@example.com",
            subject="Subject audit",
            html_body="<p>Body</p>",
            from_name="LEAMSS Test",
        )
        for k in ("to", "subject", "from", "html_length", "has_key", "at"):
            assert k in result, f"Missing audit key: {k}"
        assert "LEAMSS Test" in result["from"]
        assert result["html_length"] == len("<p>Body</p>")
    finally:
        if saved:
            os.environ["RESEND_API_KEY"] = saved


@pytest.mark.asyncio
async def test_z3_graceful_when_resend_package_missing():
    """If RESEND_API_KEY set but `resend` not installed → preview_only fallback, no crash."""
    from services.email_service import send_email
    os.environ["RESEND_API_KEY"] = "test_key_for_unit_test_only"
    try:
        result = await send_email(
            to="x@example.com",
            subject="Graceful test",
            html_body="<p>x</p>",
        )
        # Could be 'preview_only' (resend not installed) or 'sent' / 'error' (if installed but bad key).
        # Either way, must not crash + must return a structured result.
        assert "status" in result
        assert result["to"] == "x@example.com"
    finally:
        del os.environ["RESEND_API_KEY"]
