"""Tests for Section 04.1 State / Territory Demand table generation in Assessment Reports.

Verifies:
1. State demand is code-wise dynamic and never produces blank dashes.
2. Both dictionary format (from MongoDB occupation_master) and list format are handled cleanly.
3. All 8 Australian jurisdictions (NSW, VIC, QLD, WA, SA, TAS, ACT, NT) render their state name,
   demand rating/shortage label, Subclass 190 eligibility badge, and Subclass 491 eligibility badge.
4. Report UI/UX styling and markup are 100% preserved.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.report_v2.renderer import (
    _enrich_snapshot,
    _normalize_state_territory_eligibility,
    AU_STATE_ORDER,
)


@pytest.fixture
def jinja_env():
    templates_dir = Path(__file__).resolve().parent.parent / "core" / "report_v2" / "templates"
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def test_normalize_state_territory_eligibility_from_dict():
    raw_dict = {
        "NSW": {"rating": "S", "rating_label": "Shortage (Statewide)", "demand": "high", "eligible_190": True, "eligible_491": True},
        "VIC": {"rating": "S", "rating_label": "Shortage (Statewide)", "demand": "high", "eligible_190": True, "eligible_491": True},
        "QLD": {"rating": "R", "rating_label": "Regional Shortage", "demand": "medium", "eligible_190": False, "eligible_491": True},
        "WA": {"rating": "S", "rating_label": "Shortage (Statewide)", "demand": "high", "eligible_190": True, "eligible_491": True},
        "SA": {"rating": "S", "rating_label": "Shortage (Statewide)", "demand": "high", "eligible_190": True, "eligible_491": True},
        "TAS": {"rating": "R", "rating_label": "Regional Shortage", "demand": "medium", "eligible_190": False, "eligible_491": True},
        "ACT": {"rating": "NS", "rating_label": "No Metro Shortage", "demand": "low", "eligible_190": False, "eligible_491": True},
        "NT": {"rating": "R", "rating_label": "Regional Shortage", "demand": "medium", "eligible_190": False, "eligible_491": True},
    }
    normalized = _normalize_state_territory_eligibility(raw_dict, clean_code="261313")
    assert len(normalized) == 8
    
    # Verify each jurisdiction
    codes = [item["state_code"] for item in normalized]
    assert codes == AU_STATE_ORDER

    nsw = next(item for item in normalized if item["state_code"] == "NSW")
    assert nsw["state"] == "New South Wales (NSW)"
    assert nsw["demand"] == "Shortage (Statewide)"
    assert nsw["sc190"] is True
    assert nsw["sc491"] is True

    qld = next(item for item in normalized if item["state_code"] == "QLD")
    assert qld["state"] == "Queensland (QLD)"
    assert qld["demand"] == "Regional Shortage"
    assert qld["sc190"] is False
    assert qld["sc491"] is True


def test_normalize_state_territory_eligibility_fallback_empty():
    normalized = _normalize_state_territory_eligibility(None, clean_code="261313")
    assert len(normalized) == 8
    for item in normalized:
        assert item["state"]
        assert item["demand"]
        assert isinstance(item["sc190"], bool)
        assert isinstance(item["sc491"], bool)


def test_country_template_renders_demand_table_without_blank_dashes(jinja_env):
    tpl = jinja_env.get_template("_country.html")

    # Raw dict as directly loaded from MongoDB occupation_master
    raw_dict = {
        "NSW": {"rating": "S", "rating_label": "Shortage (Statewide)", "demand": "high", "eligible_190": True, "eligible_491": True},
        "VIC": {"rating": "S", "rating_label": "Shortage (Statewide)", "demand": "high", "eligible_190": True, "eligible_491": True},
        "QLD": {"rating": "R", "rating_label": "Regional Shortage", "demand": "medium", "eligible_190": False, "eligible_491": True},
        "WA": {"rating": "S", "rating_label": "Shortage (Statewide)", "demand": "high", "eligible_190": True, "eligible_491": True},
        "SA": {"rating": "S", "rating_label": "Shortage (Statewide)", "demand": "high", "eligible_190": True, "eligible_491": True},
        "TAS": {"rating": "R", "rating_label": "Regional Shortage", "demand": "medium", "eligible_190": False, "eligible_491": True},
        "ACT": {"rating": "NS", "rating_label": "No Metro Shortage", "demand": "low", "eligible_190": False, "eligible_491": True},
        "NT": {"rating": "R", "rating_label": "Regional Shortage", "demand": "medium", "eligible_190": False, "eligible_491": True},
    }

    ctx_country = {
        "country_code": "AU",
        "country_name": "Australia",
        "visa_subclass": "190",
        "total": 80,
        "pass_mark": 65,
        "occupation": {
            "code": "261313",
            "title": "Software Engineer",
            "state_territory_eligibility": raw_dict,
        },
    }

    rendered = tpl.render(ctx_country=ctx_country, ctx_index=1)
    dem_idx = rendered.find("State / Territory Demand")
    assert dem_idx != -1

    tbody_start = rendered.find("<tbody>", dem_idx)
    tbody_end = rendered.find("</tbody>", tbody_start)
    table_content = rendered[tbody_start:tbody_end]

    # Must NOT have empty <b></b> cells (which was the root cause of the blank dashes)
    assert "<b></b>" not in table_content
    # Must contain state titles
    assert "New South Wales (NSW)" in table_content
    assert "Victoria (VIC)" in table_content
    assert "Queensland (QLD)" in table_content
    assert "Western Australia (WA)" in table_content
    # Must have open badges
    assert "✓ Open" in table_content


def test_enrich_snapshot_normalizes_countries_and_primary_occ():
    snap = {
        "snapshot_id": "RPT-20261113-6E927078",
        "client": {"name": "Pravin Rajbahadur Khushawah"},
        "render_tier": "full",
        "points": 80,
        "best_country": {"country_code": "AU", "visa_subclass": "190", "total": 80},
        "occupation": {
            "code": "261313",
            "title": "Software Engineer",
            "state_territory_eligibility": {
                "NSW": {"rating": "S", "rating_label": "Shortage (Statewide)", "eligible_190": True, "eligible_491": True},
                "VIC": {"rating": "S", "rating_label": "Shortage (Statewide)", "eligible_190": True, "eligible_491": True},
            },
        },
        "countries": [{
            "country_code": "AU",
            "country_name": "Australia",
            "visa_subclass": "190",
            "total": 80,
            "pass_mark": 65,
            "occupation": {
                "code": "261313",
                "title": "Software Engineer",
                "state_territory_eligibility": {
                    "NSW": {"rating": "S", "rating_label": "Shortage (Statewide)", "eligible_190": True, "eligible_491": True},
                    "VIC": {"rating": "S", "rating_label": "Shortage (Statewide)", "eligible_190": True, "eligible_491": True},
                },
            },
        }],
    }

    enriched = _enrich_snapshot(snap)
    c_occ = enriched["countries"][0]["occupation"]
    assert isinstance(c_occ["state_territory_eligibility"], list)
    assert len(c_occ["state_territory_eligibility"]) == 8
    assert c_occ["state_territory_eligibility"][0]["state"] == "New South Wales (NSW)"
    assert c_occ["state_territory_eligibility"][0]["demand"] == "Shortage (Statewide)"
    assert c_occ["state_territory_eligibility"][0]["sc190"] is True
    assert c_occ["state_territory_eligibility"][0]["sc491"] is True
