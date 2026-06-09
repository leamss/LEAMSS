"""Phase 12.2 — Bulk Auto-Verify Tool for Occupation Codes.

Each country has a per-record verification gate. If the record meets ALL the
required fields AND the overall coverage % crosses `min_coverage_pct`, the
record is auto-promoted from `status="draft"` → `status="verified"` and an
audit footprint is dropped:
    {
      auto_verified_at: <ISO>,
      auto_verified_by: <admin_email>,
      auto_verify_version: "2026-Q1",
      auto_verify_pct: 87.5,
    }

Per-country rules:
  AU: assessing_authority + visa_pathways + skillselect_tier (or fallback).
  CA: teer_category + ee_eligibility + (pnp_eligibility OR quebec_eligibility OR regional_pilot_eligibility).
  NZ: skill_level + assessing_authority + (nz_green_list_tier OR aewv_eligibility).

Idempotent: re-running won't touch already-verified records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

AUTO_VERIFY_VERSION = "2026-Q1"


def _is_filled(v) -> bool:
    if v is None or v == "" or v == [] or v == {}:
        return False
    if isinstance(v, dict):
        # Has at least one truthy nested value (excluding empty strings/lists)
        return any(_is_filled(sub) for sub in v.values())
    if isinstance(v, list):
        return len(v) > 0
    return True


def _coverage_pct(doc: Dict[str, Any], required: List[str]) -> float:
    filled = sum(1 for f in required if _is_filled(doc.get(f)))
    return round(filled / len(required) * 100, 1) if required else 0.0


def _check_au(doc: Dict[str, Any]) -> Tuple[bool, List[str], float]:
    required = [
        "assessing_authority", "visa_pathways",
        "skillselect_tier", "min_invitation_points",
    ]
    missing = [f for f in required if not _is_filled(doc.get(f))]
    pct = _coverage_pct(doc, required)
    return (len(missing) == 0, missing, pct)


def _check_ca(doc: Dict[str, Any]) -> Tuple[bool, List[str], float]:
    base_required = ["teer_category", "ee_eligibility", "hierarchy"]
    # At least one of these provincial pathways must be present
    one_of = ["pnp_eligibility", "quebec_eligibility", "regional_pilot_eligibility"]
    missing_base = [f for f in base_required if not _is_filled(doc.get(f))]
    has_one_of = any(_is_filled(doc.get(f)) for f in one_of)
    pct = _coverage_pct(doc, base_required + one_of)
    missing = list(missing_base)
    if not has_one_of:
        missing.append("provincial_pathway (one of pnp/quebec/regional_pilot)")
    return (not missing_base and has_one_of, missing, pct)


def _check_nz(doc: Dict[str, Any]) -> Tuple[bool, List[str], float]:
    base_required = ["skill_level", "assessing_authority", "visa_pathways"]
    # At least one of these green-list/AEWV pathways must be set
    one_of = ["nz_green_list_tier", "aewv_eligibility"]
    missing_base = [f for f in base_required if not _is_filled(doc.get(f))]
    has_pathway = False
    if _is_filled(doc.get("aewv_eligibility")):
        has_pathway = True
    if doc.get("nz_green_list_tier") in (1, 2):
        has_pathway = True
    pct = _coverage_pct(doc, base_required + one_of)
    missing = list(missing_base)
    if not has_pathway:
        missing.append("nz_pathway (green_list_tier or aewv_eligibility)")
    return (not missing_base and has_pathway, missing, pct)


CHECKERS = {"AU": _check_au, "CA": _check_ca, "NZ": _check_nz}


def get_rules_summary() -> Dict[str, Any]:
    return {
        "version": AUTO_VERIFY_VERSION,
        "rules": {
            "AU": {
                "required_fields": ["assessing_authority", "visa_pathways", "skillselect_tier", "min_invitation_points"],
                "description": "Requires assessing body + visa pathway + SkillSelect tier + min invite points.",
            },
            "CA": {
                "required_fields": ["teer_category", "ee_eligibility", "hierarchy"],
                "one_of": ["pnp_eligibility", "quebec_eligibility", "regional_pilot_eligibility"],
                "description": "Requires TEER + Express Entry block + hierarchy + at least one provincial pathway.",
            },
            "NZ": {
                "required_fields": ["skill_level", "assessing_authority", "visa_pathways"],
                "one_of": ["nz_green_list_tier (1 or 2)", "aewv_eligibility"],
                "description": "Requires skill_level + NZQA assessing body + visa pathways + Green List Tier OR AEWV.",
            },
        },
    }


async def preview(db, country: str, min_coverage_pct: float = 70.0) -> Dict[str, Any]:
    """Return which codes would be auto-verified vs skipped + why."""
    country = country.upper()
    if country not in CHECKERS:
        raise ValueError(f"Unsupported country: {country}")
    checker = CHECKERS[country]

    coll = db["occupation_master"]
    pass_codes: List[Dict[str, Any]] = []
    fail_codes: List[Dict[str, Any]] = []
    already_verified = 0
    total = 0

    async for d in coll.find({"country_code": country}, {"_id": 0}):
        total += 1
        if (d.get("status") or "") == "verified":
            already_verified += 1
            continue
        passes, missing, pct = checker(d)
        record = {
            "code": d.get("code"),
            "title": d.get("title"),
            "coverage_pct": pct,
            "missing_fields": missing,
            "passes_rules": passes,
            "passes_threshold": pct >= min_coverage_pct,
        }
        if passes and pct >= min_coverage_pct:
            pass_codes.append(record)
        else:
            fail_codes.append(record)
    return {
        "country": country,
        "min_coverage_pct": min_coverage_pct,
        "version": AUTO_VERIFY_VERSION,
        "totals": {
            "total_records": total,
            "already_verified": already_verified,
            "would_verify": len(pass_codes),
            "would_skip": len(fail_codes),
        },
        "pass_codes": pass_codes[:50],   # cap for UI payload size
        "pass_codes_truncated": len(pass_codes) > 50,
        "fail_codes": fail_codes[:50],
        "fail_codes_truncated": len(fail_codes) > 50,
        "rules": get_rules_summary()["rules"][country],
    }


async def run(db, country: str, min_coverage_pct: float = 70.0, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Actually flip status=draft → status=verified for qualifying records."""
    country = country.upper()
    if country not in CHECKERS:
        raise ValueError(f"Unsupported country: {country}")
    checker = CHECKERS[country]

    coll = db["occupation_master"]
    now = datetime.now(timezone.utc)
    verified = 0
    skipped_incomplete = 0
    already_verified = 0
    total = 0

    async for d in coll.find(
        {"country_code": country},
        {"_id": 0},
    ):
        total += 1
        code = d.get("code")
        if not code:
            continue
        if (d.get("status") or "") == "verified":
            already_verified += 1
            continue
        passes, missing, pct = checker(d)
        if not (passes and pct >= min_coverage_pct):
            skipped_incomplete += 1
            continue
        verified += 1
        if not dry_run:
            await coll.update_one(
                {"country_code": country, "code": code},
                {"$set": {
                    "status": "verified",
                    "auto_verified_at": now.isoformat(),
                    "auto_verified_by": actor,
                    "auto_verify_version": AUTO_VERIFY_VERSION,
                    "auto_verify_pct": pct,
                    "updated_at": now,
                }},
            )

    return {
        "country": country,
        "dry_run": dry_run,
        "version": AUTO_VERIFY_VERSION,
        "min_coverage_pct": min_coverage_pct,
        "totals": {
            "total_records": total,
            "verified_now": verified,
            "skipped_incomplete": skipped_incomplete,
            "already_verified": already_verified,
        },
        "ran_at": now.isoformat(),
        "actor": actor,
    }
