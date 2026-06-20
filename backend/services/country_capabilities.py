"""Phase 20.7 — Country capability helpers.

Centralises country-specific feature gating to keep validation logic
in one place. Sir's rule: Skill Assessment ONLY for AU + NZ.
"""
from __future__ import annotations

from typing import Iterable

SKILL_ASSESSMENT_COUNTRIES = frozenset({"AU", "NZ"})


def supports_skill_assessment(country_code: str) -> bool:
    """True if the country uses formal skill-assessment authorities (AU, NZ)."""
    return (country_code or "").upper() in SKILL_ASSESSMENT_COUNTRIES


def filter_authorities_by_country(authorities: Iterable[dict], country_code: str) -> list[dict]:
    """Hide assessing-authority entries for countries that don't support them."""
    if not supports_skill_assessment(country_code):
        return []
    cc = country_code.upper()
    return [a for a in authorities if (a.get("country_code") or "").upper() == cc]
