"""Phase 6.10.1 — Template-aware calculator overlay.

Bridges the country_templates collection to the existing rule engine
(sales_calculator.py) WITHOUT rewriting it.

Rule:
  • If country_template.status == 'verified' → calculator MAY override factor
    point values from the template's `options` per matching condition.
  • Else → existing legacy values stand (zero regression).

This is intentionally light-touch: structural rules (which factors exist, partner
logic, eligibility checks) remain in code. Only POINT VALUES per factor option
become admin-controllable for verified templates. Phase 6.10 Part 1 minimum.
"""
from typing import Any, Dict, Optional

from core.database import db

_COUNTRY_TEMPLATES = db["country_templates"]


async def get_verified_template(country_code: str) -> Optional[Dict[str, Any]]:
    """Return the country template if it exists AND is admin-verified, else None."""
    doc = await _COUNTRY_TEMPLATES.find_one(
        {"country_code": country_code.upper(), "status": "verified"},
        {"_id": 0},
    )
    return doc


async def template_status(country_code: str) -> str:
    """Returns 'verified' | 'draft' | 'outdated' | 'none' (no template)."""
    doc = await _COUNTRY_TEMPLATES.find_one(
        {"country_code": country_code.upper()}, {"_id": 0, "status": 1}
    )
    if not doc:
        return "none"
    return doc.get("status", "draft")


def _options_to_lookup(options) -> Dict[str, int]:
    """Flatten {label, condition, points}[] → {condition: points} for fast O(1) lookup."""
    if not options:
        return {}
    out: Dict[str, int] = {}
    for o in options:
        cond = o.get("condition") or o.get("label") or ""
        cond = str(cond).strip().lower()
        if cond:
            out[cond] = int(o.get("points") or 0)
    return out


def find_factor(template: Dict[str, Any], factor_name_match: str) -> Optional[Dict[str, Any]]:
    """Locate a factor by case-insensitive name substring (admin may rename factors)."""
    if not template:
        return None
    needle = factor_name_match.lower()
    for f in (template.get("factors") or []):
        if needle in (f.get("factor_name") or "").lower():
            return f
    return None
