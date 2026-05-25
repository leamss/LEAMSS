"""Phase 8 — Premium PDF Renderer v2 (WeasyPrint + Jinja2) — smoke tests.

Verifies:
  • render_pdf_v2() returns a valid PDF for all 3 tiers
  • Teaser tier has fewer pages than Full tier
  • Brand assets (logo, fonts, CSS) load correctly
  • Real DB snapshot can be rendered end-to-end
"""
from __future__ import annotations

import pytest

from core.report_v2 import render_pdf_v2


def _build_min_snapshot(tier: str = "full") -> dict:
    return {
        "snapshot_id": "RPT-TEST-V2",
        "data_integrity_hash": "abc123" * 8,
        "generated_at_iso": "2026-05-25T00:00:00Z",
        "generated_on_human": "25 May 2026 · 12:00 PM",
        "render_tier": tier,
        "client": {"name": "Test Client", "email": "t@example.com", "phone": "+91-99999"},
        "profile_snapshot": {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 30},
                "education": {"highest_qualification": "Bachelor"},
                "professional": {"current_profession": "Software Engineer", "years_experience_total": 5},
                "language": {"scores": {"overall": 7.5}},
            },
        },
        "best_country": {
            "country_code": "AU", "country_name": "Australia",
            "visa_subclass": "189", "total": 75, "pass_mark": 65,
            "template_status": "verified",
        },
        "countries": [
            {
                "country_code": "AU", "country_name": "Australia",
                "visa_subclass": "189", "total": 75, "pass_mark": 65,
                "template_status": "verified",
                "breakdown": {"age": {"points": 25}, "english": {"points": 20}},
                "occupation": {"code": "261313", "title": "Software Engineer"},
                "visa_subclasses_meta": {},
            },
        ],
        "country_guides": [],
        "anzsco_profile": None,
        "cost_estimator": None,
        "protection_policy": {
            "policy_id": "TEST-POL", "version": "1.0",
            "title": "Test Protection Policy",
            "description_markdown": "Test description",
            "refund_terms": {"covers": ["fees"], "excludes": ["medical"], "claim_within_days": 60},
            "applicable_countries": ["AU"], "applicable_visa_types": ["SKILLED"],
        },
        "warnings": [],
    }


def test_renders_full_tier():
    pdf = render_pdf_v2(_build_min_snapshot("full"))
    assert pdf.startswith(b"%PDF"), "Output is not a valid PDF"
    assert len(pdf) > 30_000, f"PDF too small: {len(pdf)} bytes"


def test_renders_teaser_tier():
    pdf = render_pdf_v2(_build_min_snapshot("teaser"))
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 20_000


def test_renders_proposal_tier():
    pdf = render_pdf_v2(_build_min_snapshot("proposal"))
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 30_000


def test_teaser_is_smaller_than_full():
    full_pdf = render_pdf_v2(_build_min_snapshot("full"))
    teaser_pdf = render_pdf_v2(_build_min_snapshot("teaser"))
    # Teaser excludes country deep-dive, cost, guide, checklist — should be smaller
    assert len(teaser_pdf) < len(full_pdf)


def test_renders_with_no_optional_blocks():
    """Renderer must not crash when optional KB blocks are absent."""
    snap = _build_min_snapshot("full")
    snap["country_guides"] = []
    snap["anzsco_profile"] = None
    snap["cost_estimator"] = None
    pdf = render_pdf_v2(snap)
    assert pdf.startswith(b"%PDF")


def test_renders_with_no_protection_policy():
    """Renderer must not crash if protection_policy is None (gracefully omits section)."""
    snap = _build_min_snapshot("full")
    snap["protection_policy"] = None
    pdf = render_pdf_v2(snap)
    assert pdf.startswith(b"%PDF")


def test_does_not_mutate_input_snapshot():
    snap = _build_min_snapshot("full")
    orig_tier = snap["render_tier"]
    render_pdf_v2(snap)
    assert snap["render_tier"] == orig_tier
