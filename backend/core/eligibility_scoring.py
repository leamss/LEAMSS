"""
Deterministic, transparent & admin-configurable eligibility scoring engine.

The visitor-facing eligibility score is computed by an explicit, weighted formula
(NOT a black-box AI number).

IMPORTANT:
- Australia / New Zealand / other pathways continue to use the existing
  generic 7-factor /100 scoring engine.
- Canada PNP is handled separately through a Canada-specific scoring path.
- Canada-specific scoring will contain:
    1. Express Entry CRS calculation
    2. PNP eligibility checks
    3. Province/stream-specific conditions

Pathway requirements come from the `visa_pathways` collection
(the same source the public Visa-Compare tool uses) → single source of truth.

Factor weights, tier thresholds and lookup tables live in `kb_settings`
(doc _id = 'eligibility_scoring_rules') and are editable by admins;
if no override exists the DEFAULT_RULES below are used.
"""

import re
from typing import Any, Dict, List, Optional

from core.database import db


SCORING_RULES_ID = "eligibility_scoring_rules"


# ── Default, admin-overridable rule set ──────────────────────────────────────

DEFAULT_RULES: Dict[str, Any] = {
    "version": 1,

    # Generic scoring factors.
    #
    # IMPORTANT:
    # These factors are still used for Australia, New Zealand and other
    # generic pathways.
    #
    # Canada PNP does NOT use these factors anymore.
    "factors": {
        "age":        {"weight": 25, "label": "Age"},
        "education":  {"weight": 20, "label": "Education"},
        "experience": {"weight": 18, "label": "Work Experience"},
        "english":    {"weight": 20, "label": "English Proficiency"},
        "job_offer":  {"weight": 7,  "label": "Job Offer"},
        "occupation": {"weight": 5,  "label": "Occupation in Demand"},
        "funds":      {"weight": 5,  "label": "Settlement Funds"},
    },

    # Generic score (0-100) >= threshold => tier.
    "tiers": {
        "strong": 75,
        "moderate": 55,
        "weak": 35,
    },

    # Generic pathway competitiveness penalty.
    #
    # IMPORTANT:
    # This is NOT used by the Canada PNP scoring path.
    "competitiveness_penalty_max": 22,

    # Generic job-offer penalty.
    #
    # IMPORTANT:
    # This is NOT used by the Canada PNP scoring path.
    "no_offer_penalty": 0.5,

    # Generic age curve.
    "age_curve": {
        "optimal_max": 32,
        "floor_ratio": 0.3,
    },

    # Education level → ordinal rank.
    "education_levels": {
        "phd": 5,
        "doctorate": 5,

        "master": 4,
        "masters": 4,

        "bachelor": 3,
        "bachelors": 3,
        "degree": 3,
        "graduate": 3,

        "diploma": 2,
        "associate": 2,

        "class 12": 1,
        "12th": 1,
        "high school": 1,
        "highschool": 1,
        "secondary": 1,
    },

    # Extra buffer (years) above a pathway's min experience
    # for FULL generic marks.
    "experience_buffer_years": 3,
}


# Map an IELTS-equivalent band (0-9) used for the generic English factor.
_IELTS_BANDS = {
    "8": 8.5,
    "8+": 8.5,
    "8.0": 8.0,
    "8.5": 8.5,

    "7": 7.25,
    "7.0": 7.0,
    "7.5": 7.5,
    "7.0-7.5": 7.25,

    "6.5": 6.5,
    "6": 6.0,
    "6.0": 6.0,

    "5.5": 5.5,
    "5": 5.0,
    "5.0": 5.0,
}


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _parse_english_band(text: Optional[str]) -> Optional[float]:
    """
    Return an IELTS-equivalent band (0-9) from a free-text English score.

    This function is used by the GENERIC scoring engine.

    Canada-specific CRS language scoring will be implemented separately
    because CRS requires individual language abilities / CLB values.
    """

    t = _norm(text)

    if not t or "not taken" in t or t in ("none", "no", "n/a"):
        return None

    # PTE → IELTS rough equivalence
    pte = re.search(r"pte\s*(\d{2,3})", t)

    if pte:
        v = int(pte.group(1))

        if v >= 79:
            return 8.0

        if v >= 65:
            return 7.0

        if v >= 58:
            return 6.5

        if v >= 50:
            return 6.0

        return 5.0

    # CLB → IELTS rough equivalence
    clb = re.search(r"clb\s*(\d{1,2})", t)

    if clb:
        v = int(clb.group(1))

        return {
            10: 8.0,
            9: 7.5,
            8: 7.0,
            7: 6.0,
            6: 5.5,
            5: 5.0,
        }.get(
            v,
            max(4.0, min(9.0, float(v) - 1))
        )

    # B1/B2/C1/C2
    if "c1" in t or "c2" in t:
        return 7.5

    if "b2" in t:
        return 6.5

    if "b1" in t:
        return 5.5

    # Plain IELTS number
    num = re.search(r"(\d\.?\d?)\s*\+?", t)

    if num:
        try:
            return min(9.0, float(num.group(1)))
        except ValueError:
            pass

    return None


def _required_english_band(
    language_required: Optional[str],
) -> float:

    band = _parse_english_band(language_required)

    return band if band is not None else 6.0


def _education_rank(
    text: Optional[str],
    levels: Dict[str, int],
) -> int:

    t = _norm(text)

    best = 0

    for key, rank in levels.items():

        if key in t and rank > best:
            best = rank

    return best


def _tier_for(
    score: int,
    tiers: Dict[str, int],
) -> str:

    if score >= tiers.get("strong", 75):
        return "strong"

    if score >= tiers.get("moderate", 55):
        return "moderate"

    if score >= tiers.get("weak", 35):
        return "weak"

    return "unlikely"


async def load_scoring_rules() -> Dict[str, Any]:
    """
    Load admin override merged over defaults.
    """

    doc = await db["kb_settings"].find_one(
        {"_id": SCORING_RULES_ID}
    )

    if not doc:
        return {
            **DEFAULT_RULES,
            "_source": "defaults",
        }

    merged = {
        **DEFAULT_RULES
    }

    for k, v in doc.items():

        if k == "_id":
            continue

        merged[k] = v

    merged["_source"] = "db_override"

    return merged


# ═════════════════════════════════════════════════════════════════════════════
# GENERIC SCORING FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def _score_age(
    age: int,
    pathway: Dict,
    weight: float,
    curve: Dict,
) -> Dict:

    max_age = int(
        pathway.get("max_age") or 50
    )

    min_age = int(
        pathway.get("min_age") or 18
    )

    optimal = int(
        curve.get("optimal_max", 32)
    )

    floor = float(
        curve.get("floor_ratio", 0.3)
    )

    if age < min_age:

        return {
            "earned": 0.0,
            "reason": (
                f"Below minimum age ({min_age}) "
                f"for this pathway"
            ),
        }

    if age > max_age:

        return {
            "earned": 0.0,
            "reason": (
                f"Above the age limit ({max_age}) "
                f"— most points lost"
            ),
        }

    if age <= optimal:

        return {
            "earned": weight,
            "reason": (
                f"Ideal age band (≤{optimal}) "
                f"— full points"
            ),
        }

    # Linear decay from optimal to max_age.
    span = max(
        1,
        max_age - optimal
    )

    ratio = (
        1
        - (1 - floor)
        * ((age - optimal) / span)
    )

    earned = round(
        weight * ratio,
        1
    )

    return {
        "earned": earned,
        "reason": (
            f"Age {age} is past the ideal band; "
            f"points taper toward the {max_age} limit"
        ),
    }


def _score_education(
    level: str,
    pathway: Dict,
    weight: float,
    levels: Dict,
) -> Dict:

    cand = _education_rank(
        level,
        levels
    )

    req = (
        _education_rank(
            pathway.get("min_education"),
            levels
        )
        or 3
    )

    if cand == 0:

        return {
            "earned": 0.0,
            "reason": "Education level not recognised",
        }

    if cand >= req:

        return {
            "earned": weight,
            "reason": (
                "Meets/exceeds the required education "
                f"({pathway.get('min_education', 'Bachelor')})"
            ),
        }

    earned = round(
        weight * (
            cand / max(1, req)
        ),
        1,
    )

    return {
        "earned": earned,
        "reason": (
            f"Below the required "
            f"{pathway.get('min_education', 'Bachelor')} "
            f"— partial credit"
        ),
    }


def _score_experience(
    years: float,
    pathway: Dict,
    weight: float,
    buffer: int,
) -> Dict:

    min_req = float(
        pathway.get("min_work_exp_years") or 0
    )

    target = (
        min_req
        + float(buffer)
    )

    if target <= 0:

        target = float(buffer) or 3.0

    if years >= target:

        return {
            "earned": weight,
            "reason": (
                f"{years:g} yrs comfortably clears "
                f"this pathway's requirement"
            ),
        }

    earned = round(
        weight * (
            years / target
        ),
        1,
    )

    note = (
        "meets minimum"
        if years >= min_req
        else f"below the {min_req:g}-yr minimum"
    )

    return {
        "earned": earned,
        "reason": (
            f"{years:g} yrs experience — {note}"
        ),
    }


def _score_english(
    eng_text: str,
    pathway: Dict,
    weight: float,
) -> Dict:

    cand = _parse_english_band(
        eng_text
    )

    req = _required_english_band(
        pathway.get("language_required")
    )

    if cand is None:

        return {
            "earned": 0.0,
            "reason": (
                "English test not taken yet "
                "— take IELTS/PTE to unlock these points"
            ),
        }

    if cand >= req:

        return {
            "earned": weight,
            "reason": (
                f"English band {cand:g} "
                f"meets the requirement (~{req:g})"
            ),
        }

    earned = round(
        weight * (
            cand / max(0.1, req)
        ),
        1,
    )

    return {
        "earned": earned,
        "reason": (
            f"English band {cand:g} is below "
            f"the ~{req:g} needed — partial credit"
        ),
    }


def _score_job_offer(
    has_offer: bool,
    pathway: Dict,
    weight: float,
) -> Dict:

    requires = bool(
        pathway.get("requires_job_offer")
    )

    if has_offer:

        return {
            "earned": weight,
            "reason": (
                "Job offer in hand "
                "— strong positive signal"
            ),
        }

    reason = (
        "A job offer / employer sponsor is required "
        "for this route"
        if requires
        else
        "No job offer "
        "(optional for this pathway)"
    )

    return {
        "earned": 0.0,
        "reason": reason,
    }


_COUNTRY_TO_CODE = {
    "canada": "CA",
    "australia": "AU",
    "new zealand": "NZ",
}


async def _occupation_demand_ratio(
    occupation: str,
    country: Optional[str],
) -> Dict[str, Any]:

    """
    Per-country occupation demand → {ratio 0..1, reason}.

    Uses occupation_master.

    Generic scoring only.
    """

    occ = _norm(
        occupation
    )

    if not occ or occ in (
        "not specified",
        "na",
        "n/a",
    ):

        return {
            "ratio": 0.0,
            "reason": "Occupation not provided",
        }

    code = _COUNTRY_TO_CODE.get(
        _norm(country)
    )

    if not code:

        return {
            "ratio": 0.5,
            "reason": (
                f"Demand data for "
                f"{country or 'this country'} "
                "not catalogued — neutral credit"
            ),
        }

    try:

        regex = {
            "$regex": re.escape(
                occupation.strip()
            ),
            "$options": "i",
        }

        q = {
            "country_code": code,
            "$or": [
                {
                    "title": regex
                },
                {
                    "alternative_titles": regex
                },
            ],
        }

        doc = await db[
            "occupation_master"
        ].find_one(
            q,
            {
                "status": 1,
                "title": 1,
            },
        )

        if not doc:

            return {
                "ratio": 0.25,
                "reason": (
                    f"Not found on {country}'s "
                    "skilled occupation list"
                ),
            }

        if doc.get("status") == "verified":

            return {
                "ratio": 1.0,
                "reason": (
                    f"On {country}'s verified "
                    "in-demand occupation list"
                ),
            }

        return {
            "ratio": 0.6,
            "reason": (
                f"Listed for {country} "
                "(pending verification)"
            ),
        }

    except Exception:

        return {
            "ratio": 0.4,
            "reason": "Occupation provided",
        }


def _score_occupation(
    demand: Dict[str, Any],
    weight: float,
) -> Dict:

    ratio = demand.get(
        "ratio",
        0.0
    )

    return {
        "earned": round(
            weight * ratio,
            1,
        ),
        "reason": demand.get(
            "reason",
            "",
        ),
    }


def _score_funds(
    savings: Optional[float],
    pathway: Dict,
    weight: float,
) -> Dict:

    req = float(
        pathway.get("min_funds_inr") or 0
    )

    if savings is None:

        return {
            "earned": 0.0,
            "reason": (
                "Settlement funds not disclosed"
            ),
        }

    if req <= 0 or savings >= req:

        return {
            "earned": weight,
            "reason": (
                "Sufficient settlement funds"
            ),
        }

    earned = round(
        weight * (
            savings / req
        ),
        1,
    )

    return {
        "earned": earned,
        "reason": (
            f"Funds below the "
            f"~₹{req/100000:.1f}L "
            "typically required"
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# CANADA PNP SCORING ENGINE
# ═════════════════════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════════════════════════════
# CANADA CRS — AGE
# ═════════════════════════════════════════════════════════════════════════════


def _profile_text(
    profile: Dict[str, Any],
    *names: str,
) -> str:
    """Return the first non-empty profile value as text."""
    for name in names:
        value = profile.get(name)

        if value is None:
            continue

        text = str(value).strip()

        if text:
            return text

    return ""


def _profile_number(
    profile: Dict[str, Any],
    *names: str,
    default: float = 0.0,
) -> float:
    """Read a numeric profile value using supported field aliases."""
    for name in names:
        value = profile.get(name)

        if value is None or value == "":
            continue

        if isinstance(value, str):
            import re as _re

            match = _re.search(
                r"-?\d+(?:\.\d+)?",
                value,
            )

            if not match:
                continue

            value = match.group(0)

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            continue

    return default


def _profile_bool(
    profile: Dict[str, Any],
    *names: str,
) -> bool:
    """Read a boolean-like profile value using supported field aliases."""
    true_values = {
        "yes",
        "true",
        "1",
        "y",
        "on",
        "available",
        "eligible",
        "confirmed",
    }

    for name in names:
        if name not in profile:
            continue

        value = profile.get(name)

        if isinstance(value, bool):
            if value:
                return True
            continue

        if isinstance(value, (int, float)):
            if value != 0:
                return True
            continue

        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in true_values:
                return True

    return False


def _score_canada_age(
    age: int,
    has_spouse: bool,
) -> Dict[str, Any]:
    """
    Calculate official Canada CRS age points.

    CRS age points:

    WITHOUT spouse/common-law partner:
        18 = 99
        19 = 105
        20-29 = 110
        30 = 105
        31 = 99
        32 = 94
        33 = 88
        34 = 83
        35 = 77
        36 = 72
        37 = 66
        38 = 61
        39 = 55
        40 = 50
        41 = 39
        42 = 28
        43 = 17
        44 = 6
        45+ = 0

    WITH spouse/common-law partner:
        18 = 90
        19 = 95
        20-29 = 100
        30 = 95
        31 = 90
        32 = 85
        33 = 80
        34 = 75
        35 = 70
        36 = 65
        37 = 60
        38 = 55
        39 = 50
        40 = 45
        41 = 35
        42 = 25
        43 = 15
        44 = 5
        45+ = 0
    """

    # Invalid / missing age
    if age <= 0:
        return {
            "earned": 0,
            "max": 100 if has_spouse else 110,
            "factor": "age",
            "label": "Age",
            "reason": "Age not provided",
        }

    # ─────────────────────────────────────────────────────────────────────
    # Applicant has spouse/common-law partner
    # ─────────────────────────────────────────────────────────────────────

    if has_spouse:

        age_points = {
            18: 90,
            19: 95,
            20: 100,
            21: 100,
            22: 100,
            23: 100,
            24: 100,
            25: 100,
            26: 100,
            27: 100,
            28: 100,
            29: 100,
            30: 95,
            31: 90,
            32: 85,
            33: 80,
            34: 75,
            35: 70,
            36: 65,
            37: 60,
            38: 55,
            39: 50,
            40: 45,
            41: 35,
            42: 25,
            43: 15,
            44: 5,
        }

        points = age_points.get(age, 0)

        max_points = 100

    # ─────────────────────────────────────────────────────────────────────
    # Applicant does NOT have spouse/common-law partner
    # ─────────────────────────────────────────────────────────────────────

    else:

        age_points = {
            18: 99,
            19: 105,
            20: 110,
            21: 110,
            22: 110,
            23: 110,
            24: 110,
            25: 110,
            26: 110,
            27: 110,
            28: 110,
            29: 110,
            30: 105,
            31: 99,
            32: 94,
            33: 88,
            34: 83,
            35: 77,
            36: 72,
            37: 66,
            38: 61,
            39: 55,
            40: 50,
            41: 39,
            42: 28,
            43: 17,
            44: 6,
        }

        points = age_points.get(age, 0)

        max_points = 110

    # ─────────────────────────────────────────────────────────────────────
    # Human-readable reason
    # ─────────────────────────────────────────────────────────────────────

    if age < 18:
        reason = (
            f"Age {age} — below the CRS age range"
        )

    elif age >= 45:
        reason = (
            "Age 45 or older — 0 CRS age points"
        )

    elif points == max_points:
        reason = (
            f"Age {age} — maximum CRS age points"
        )

    else:
        reason = (
            f"Age {age} — {points} CRS age points"
        )

    return {
        "earned": points,
        "max": max_points,
        "factor": "age",
        "label": "Age",
        "reason": reason,
    }

# ═════════════════════════════════════════════════════════════════════════════
# CANADA CRS — FIRST OFFICIAL LANGUAGE
# ═════════════════════════════════════════════════════════════════════════════

def _score_canada_first_language(
    profile: Dict[str, Any],
    has_spouse: bool,
) -> Dict[str, Any]:
    """
    Calculate Canada CRS points for the applicant's first official language.

    Four abilities are scored separately:
        - Reading
        - Writing
        - Speaking
        - Listening

    If no scores are supplied, the result is "not_assessed".
    If only some scores are supplied, the result is "partial".
    If all four scores are supplied, the result is "assessed".
    """

    if has_spouse:
        points_by_clb = {
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 6,
            5: 6,
            6: 8,
            7: 16,
            8: 22,
            9: 29,
            10: 32,
        }
        max_per_ability = 32
        max_total = 128
    else:
        points_by_clb = {
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 6,
            5: 6,
            6: 9,
            7: 17,
            8: 23,
            9: 31,
            10: 34,
        }
        max_per_ability = 34
        max_total = 136

    def get_clb(*field_names: str) -> Optional[int]:
        value = None

        for field_name in field_names:
            if profile.get(field_name) is not None:
                value = profile.get(field_name)
                break

        if value is None:
            return None

        if isinstance(value, str):
            text = value.strip().lower()

            if text in (
                "",
                "not taken",
                "not provided",
                "none",
                "n/a",
                "na",
                "no",
            ):
                return None

            match = re.search(r"(\d{1,2})", text)

            if not match:
                return None

            value = match.group(1)

        try:
            clb = int(float(value))
        except (TypeError, ValueError):
            return None

        return max(0, min(10, clb))

    abilities = {
        "reading": get_clb(
            "english_reading_clb",
            "first_language_reading_clb",
            "first_official_language_reading_clb",
        ),
        "writing": get_clb(
            "english_writing_clb",
            "first_language_writing_clb",
            "first_official_language_writing_clb",
        ),
        "speaking": get_clb(
            "english_speaking_clb",
            "first_language_speaking_clb",
            "first_official_language_speaking_clb",
        ),
        "listening": get_clb(
            "english_listening_clb",
            "first_language_listening_clb",
            "first_official_language_listening_clb",
        ),
    }

    provided_count = sum(
        1 for value in abilities.values()
        if value is not None
    )

    if provided_count == 0:
        return {
            "earned": 0,
            "max": max_total,
            "factor": "first_official_language",
            "label": "First Official Language",
            "status": "not_assessed",
            "reason": "Language test not taken yet",
            "abilities": [],
        }

    breakdown = []
    total = 0
    missing = []

    for ability, clb in abilities.items():
        if clb is None:
            earned = 0
            missing.append(ability)
            reason = f"{ability.title()} score not provided"
        else:
            earned = points_by_clb.get(clb, 0)
            reason = (
                f"{ability.title()}: CLB {clb} — "
                f"{earned} CRS points"
            )

        total += earned

        breakdown.append({
            "ability": ability,
            "clb": clb,
            "earned": earned,
            "max": max_per_ability,
            "reason": reason,
        })

    if missing:
        status = "partial"
        reason = (
            "Some language scores are missing: "
            + ", ".join(item.title() for item in missing)
        )
    else:
        status = "assessed"
        reason = (
            f"First Official Language: "
            f"{total}/{max_total} CRS points"
        )

    return {
        "earned": total,
        "max": max_total,
        "factor": "first_official_language",
        "label": "First Official Language",
        "status": status,
        "reason": reason,
        "abilities": breakdown,
    }



# ═════════════════════════════════════════════════════════════════════════════
# CANADA CRS — SECOND OFFICIAL LANGUAGE
# ═════════════════════════════════════════════════════════════════════════════

def _score_canada_second_language(
    profile: Dict[str, Any],
    has_spouse: bool,
) -> Dict[str, Any]:
    """
    Calculate Canada CRS points for the applicant's second official language.

    Four abilities:
        - Reading
        - Writing
        - Speaking
        - Listening

    CRS points per ability:
        CLB/NCLC 4 or less = 0
        CLB/NCLC 5 or 6    = 1
        CLB/NCLC 7 or 8    = 3
        CLB/NCLC 9+        = 6

    Maximum:
        With spouse    = 22
        Without spouse = 24

    Missing/no test:
        status = not_assessed

    Some abilities:
        status = partial

    All abilities:
        status = assessed
    """

    max_total = 22 if has_spouse else 24

    def get_clb(*field_names: str) -> Optional[int]:
        value = None

        for field_name in field_names:
            if profile.get(field_name) is not None:
                value = profile.get(field_name)
                break

        if value is None:
            return None

        if isinstance(value, str):
            text = value.strip().lower()

            if text in (
                "",
                "not taken",
                "not provided",
                "none",
                "n/a",
                "na",
                "no",
            ):
                return None

            match = re.search(r"(\d{1,2})", text)

            if not match:
                return None

            value = match.group(1)

        try:
            clb = int(float(value))
        except (TypeError, ValueError):
            return None

        return max(0, min(10, clb))

    abilities = {
        "reading": get_clb(
            "second_language_reading_clb",
            "second_official_language_reading_clb",
            "french_reading_clb",
            "french_reading_nclc",
        ),
        "writing": get_clb(
            "second_language_writing_clb",
            "second_official_language_writing_clb",
            "french_writing_clb",
            "french_writing_nclc",
        ),
        "speaking": get_clb(
            "second_language_speaking_clb",
            "second_official_language_speaking_clb",
            "french_speaking_clb",
            "french_speaking_nclc",
        ),
        "listening": get_clb(
            "second_language_listening_clb",
            "second_official_language_listening_clb",
            "french_listening_clb",
            "french_listening_nclc",
        ),
    }

    provided_count = sum(
        1
        for value in abilities.values()
        if value is not None
    )

    if provided_count == 0:
        return {
            "earned": 0,
            "max": max_total,
            "factor": "second_official_language",
            "label": "Second Official Language",
            "status": "not_assessed",
            "reason": "Second official language test not taken yet",
            "abilities": [],
        }

    def points_for_clb(clb: Optional[int]) -> int:
        if clb is None:
            return 0

        if clb <= 4:
            return 0

        if clb <= 6:
            return 1

        if clb <= 8:
            return 3

        return 6

    breakdown = []
    total = 0
    missing = []

    for ability, clb in abilities.items():

        if clb is None:
            earned = 0
            missing.append(ability)
            reason = f"{ability.title()} score not provided"
        else:
            earned = points_for_clb(clb)
            reason = (
                f"{ability.title()}: CLB/NCLC {clb} — "
                f"{earned} CRS points"
            )

        total += earned

        breakdown.append({
            "ability": ability,
            "clb": clb,
            "earned": earned,
            "max": 6,
            "reason": reason,
        })

    # The official section maximum is 22 with a spouse and 24 without.
    total = min(total, max_total)

    if missing:
        status = "partial"
        reason = (
            "Some second official language scores are missing: "
            + ", ".join(item.title() for item in missing)
        )
    else:
        status = "assessed"
        reason = (
            f"Second Official Language: "
            f"{total}/{max_total} CRS points"
        )

    return {
        "earned": total,
        "max": max_total,
        "factor": "second_official_language",
        "label": "Second Official Language",
        "status": status,
        "reason": reason,
        "abilities": breakdown,
    }



# ═════════════════════════════════════════════════════════════════════════════
# CANADA CRS — SPOUSE / COMMON-LAW PARTNER FACTORS
# ═════════════════════════════════════════════════════════════════════════════

def _score_canada_spouse_factors(
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate Canada CRS spouse/common-law partner factors.

    Maximum = 40 points:
        Spouse education              = 10
        Spouse official language      = 20
        Spouse Canadian work          = 10

    If the applicant has no accompanying spouse/common-law partner,
    this section is not applicable and earns 0 points.
    """

    # This function is called only after the PNP profile determines
    # that the applicant has a spouse/common-law partner.
    has_spouse = bool(
        profile.get("has_spouse")
        or profile.get("married")
        or profile.get("has_partner")
    )

    marital_status = _norm(
        profile.get("marital_status")
    )

    if marital_status in (
        "married",
        "common-law",
        "common law",
        "common_law",
        "partner",
    ):
        has_spouse = True

    if not has_spouse:
        return {
            "earned": 0,
            "max": 40,
            "factor": "spouse_factors",
            "label": "Spouse / Common-law Partner Factors",
            "status": "not_applicable",
            "reason": "No spouse/common-law partner",
            "breakdown": [],
        }

    # ─────────────────────────────────────────────────────────────────────
    # Spouse education — maximum 10
    # ─────────────────────────────────────────────────────────────────────

    education = _norm(
        profile.get("spouse_education")
        or profile.get("partner_education")
        or ""
    )

    if not education:

        spouse_education_points = 0

        education_status = "not_assessed"

        education_reason = (
            "Spouse education not provided"
        )

    elif (
        "doctorate" in education
        or "phd" in education
        or "ph.d" in education
    ):

        spouse_education_points = 10

        education_status = "assessed"

        education_reason = (
            "Spouse doctoral degree — 10 CRS points"
        )

    elif (
        "master" in education
        or "masters" in education
        or "professional degree" in education
    ):

        spouse_education_points = 10

        education_status = "assessed"

        education_reason = (
            "Spouse master's/professional degree "
            "— 10 CRS points"
        )

    elif (
        "bachelor" in education
        or "bachelors" in education
        or "degree" in education
        or "three-year" in education
        or "3 year" in education
        or "two or more" in education
        or "2 or more" in education
    ):

        spouse_education_points = 9

        education_status = "assessed"

        education_reason = (
            "Spouse bachelor's/3+ year credential "
            "— 9 CRS points"
        )

    elif (
        "two-year" in education
        or "2 year" in education
    ):

        spouse_education_points = 7

        education_status = "assessed"

        education_reason = (
            "Spouse two-year post-secondary credential "
            "— 7 CRS points"
        )

    elif (
        "one-year" in education
        or "1 year" in education
        or "diploma" in education
        or "certificate" in education
        or "associate" in education
    ):

        spouse_education_points = 6

        education_status = "assessed"

        education_reason = (
            "Spouse one-year post-secondary credential "
            "— 6 CRS points"
        )

    elif (
        "secondary" in education
        or "high school" in education
        or "class 12" in education
        or "12th" in education
    ):

        spouse_education_points = 2

        education_status = "assessed"

        education_reason = (
            "Spouse secondary school "
            "— 2 CRS points"
        )

    else:

        spouse_education_points = 0

        education_status = "not_recognised"

        education_reason = (
            "Spouse education level not recognised"
        )

    # ─────────────────────────────────────────────────────────────────────
    # Spouse official language — maximum 20
    # ─────────────────────────────────────────────────────────────────────

    def get_spouse_clb(
        *field_names: str,
    ) -> Optional[int]:

        value = None

        for field_name in field_names:

            if profile.get(field_name) is not None:

                value = profile.get(
                    field_name
                )

                break

        if value is None:
            return None

        if isinstance(value, str):

            text = value.strip().lower()

            if text in (
                "",
                "not taken",
                "not provided",
                "none",
                "n/a",
                "na",
                "no",
            ):

                return None

            match = re.search(
                r"(\d{1,2})",
                text,
            )

            if not match:
                return None

            value = match.group(1)

        try:

            clb = int(
                float(value)
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

        return max(
            0,
            min(
                10,
                clb,
            ),
        )

    spouse_language = {
        "reading": get_spouse_clb(
            "spouse_reading_clb",
            "spouse_language_reading_clb",
            "spouse_english_reading_clb",
        ),

        "writing": get_spouse_clb(
            "spouse_writing_clb",
            "spouse_language_writing_clb",
            "spouse_english_writing_clb",
        ),

        "speaking": get_spouse_clb(
            "spouse_speaking_clb",
            "spouse_language_speaking_clb",
            "spouse_english_speaking_clb",
        ),

        "listening": get_spouse_clb(
            "spouse_listening_clb",
            "spouse_language_listening_clb",
            "spouse_english_listening_clb",
        ),
    }

    spouse_language_points = 0

    spouse_language_breakdown = []

    missing_language = []

    for ability, clb in spouse_language.items():

        if clb is None:

            earned = 0

            missing_language.append(
                ability
            )

            reason = (
                f"Spouse {ability} score not provided"
            )

        elif clb <= 4:

            earned = 0

            reason = (
                f"Spouse {ability.title()}: "
                f"CLB {clb} — 0 CRS points"
            )

        elif clb <= 6:

            earned = 1

            reason = (
                f"Spouse {ability.title()}: "
                f"CLB {clb} — 1 CRS point"
            )

        elif clb <= 8:

            earned = 3

            reason = (
                f"Spouse {ability.title()}: "
                f"CLB {clb} — 3 CRS points"
            )

        else:

            earned = 5

            reason = (
                f"Spouse {ability.title()}: "
                f"CLB {clb} — 5 CRS points"
            )

        spouse_language_points += earned

        spouse_language_breakdown.append({
            "ability": ability,
            "clb": clb,
            "earned": earned,
            "max": 5,
            "reason": reason,
        })

    spouse_language_points = min(
        spouse_language_points,
        20,
    )

    if not any(
        value is not None
        for value in spouse_language.values()
    ):

        language_status = "not_assessed"

        language_reason = (
            "Spouse official language test not taken yet"
        )

    elif missing_language:

        language_status = "partial"

        language_reason = (
            "Some spouse language scores are missing: "
            + ", ".join(
                item.title()
                for item in missing_language
            )
        )

    else:

        language_status = "assessed"

        language_reason = (
            f"Spouse official language: "
            f"{spouse_language_points}/20 CRS points"
        )

    # ─────────────────────────────────────────────────────────────────────
    # Spouse Canadian work experience — maximum 10
    # ─────────────────────────────────────────────────────────────────────

    try:

        spouse_canadian_work_years = float(
            profile.get(
                "spouse_canadian_work_experience_years"
            )
            or profile.get(
                "partner_canadian_work_experience_years"
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        spouse_canadian_work_years = 0.0

    spouse_canadian_work_years = max(
        0.0,
        spouse_canadian_work_years,
    )

    if spouse_canadian_work_years < 1:

        spouse_work_points = 0

        spouse_work_label = (
            "Less than 1 year"
        )

    elif spouse_canadian_work_years < 2:

        spouse_work_points = 5

        spouse_work_label = "1 year"

    elif spouse_canadian_work_years < 3:

        spouse_work_points = 7

        spouse_work_label = "2 years"

    elif spouse_canadian_work_years < 4:

        spouse_work_points = 8

        spouse_work_label = "3 years"

    elif spouse_canadian_work_years < 5:

        spouse_work_points = 9

        spouse_work_label = "4 years"

    else:

        spouse_work_points = 10

        spouse_work_label = "5 years or more"

    spouse_work_reason = (
        f"Spouse Canadian work experience: "
        f"{spouse_work_label} — "
        f"{spouse_work_points}/10 CRS points"
    )

    # ─────────────────────────────────────────────────────────────────────
    # Total spouse points
    # ─────────────────────────────────────────────────────────────────────

    total = (
        spouse_education_points
        + spouse_language_points
        + spouse_work_points
    )

    return {
        "earned": total,
        "max": 40,
        "factor": "spouse_factors",
        "label": "Spouse / Common-law Partner Factors",
        "status": "assessed",
        "reason": (
            f"Spouse / common-law partner factors: "
            f"{total}/40 CRS points"
        ),
        "breakdown": [
            {
                "factor": "spouse_education",
                "label": "Spouse Education",
                "earned": spouse_education_points,
                "max": 10,
                "status": education_status,
                "reason": education_reason,
            },
            {
                "factor": "spouse_language",
                "label": "Spouse Official Language",
                "earned": spouse_language_points,
                "max": 20,
                "status": language_status,
                "reason": language_reason,
                "abilities": spouse_language_breakdown,
            },
            {
                "factor": "spouse_canadian_work_experience",
                "label": "Spouse Canadian Work Experience",
                "earned": spouse_work_points,
                "max": 10,
                "status": "assessed",
                "reason": spouse_work_reason,
            },
        ],
    }




# ═════════════════════════════════════════════════════════════════════════════
# CANADA CRS — SKILL TRANSFERABILITY
# ═════════════════════════════════════════════════════════════════════════════

def _canada_education_category(
    education: Optional[str],
) -> str:
    text = _norm(education or "")

    if not text:
        return "unknown"
    if "doctorate" in text or "phd" in text or "ph.d" in text:
        return "doctorate"
    if "master" in text or "masters" in text:
        return "master"
    if "two or more" in text or "2 or more" in text or "multiple post-secondary" in text:
        return "two_plus"
    if (
        "bachelor" in text
        or "bachelors" in text
        or "degree" in text
        or "three-year" in text
        or "3 year" in text
        or "four-year" in text
        or "4 year" in text
    ):
        return "bachelor"
    if "two-year" in text or "2 year" in text:
        return "two_year"
    if (
        "one-year" in text
        or "1 year" in text
        or "diploma" in text
        or "certificate" in text
        or "associate" in text
    ):
        return "one_year"
    if (
        "secondary" in text
        or "high school" in text
        or "class 12" in text
        or "12th" in text
    ):
        return "secondary"

    return "unknown"


def _canada_first_language_abilities(
    profile: Dict[str, Any],
) -> Dict[str, Optional[int]]:
    def get_clb(*names: str) -> Optional[int]:
        value = None

        for name in names:
            if profile.get(name) is not None:
                value = profile.get(name)
                break

        if value is None or value == "":
            return None

        if isinstance(value, str):
            match = re.search(r"(\d{1,2})", value)
            if not match:
                return None
            value = match.group(1)

        try:
            return max(0, min(10, int(float(value))))
        except (TypeError, ValueError):
            return None

    return {
        "reading": get_clb(
            "english_reading_clb",
            "first_language_reading_clb",
            "first_official_language_reading_clb",
        ),
        "writing": get_clb(
            "english_writing_clb",
            "first_language_writing_clb",
            "first_official_language_writing_clb",
        ),
        "speaking": get_clb(
            "english_speaking_clb",
            "first_language_speaking_clb",
            "first_official_language_speaking_clb",
        ),
        "listening": get_clb(
            "english_listening_clb",
            "first_language_listening_clb",
            "first_official_language_listening_clb",
        ),
    }


def _canada_all_clb_at_least(
    abilities: Dict[str, Optional[int]],
    level: int,
) -> bool:
    return (
        all(value is not None for value in abilities.values())
        and all(value >= level for value in abilities.values())
    )


def _score_canada_skill_transferability(
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Canada CRS Skill Transferability.

    Maximum = 100 CRS points.

    Components:
        1. Education + Official Language
        2. Education + Canadian Work Experience
        3. Foreign Work Experience + Official Language
        4. Foreign Work Experience + Canadian Work Experience
        5. Certificate of Qualification + Official Language
    """

    education_category = _canada_education_category(
        _profile_text(profile, "education")
    )

    first_language = _canada_first_language_abilities(profile)

    language_7 = _canada_all_clb_at_least(
        first_language,
        7,
    )

    language_9 = _canada_all_clb_at_least(
        first_language,
        9,
    )

    canadian_work_years = _profile_number(
        profile,
        "canadian_work_experience_years",
        default=0,
    )

    foreign_work_years = _profile_number(
        profile,
        "foreign_work_experience_years",
        "overseas_work_experience_years",
        "international_work_experience_years",
        default=0,
    )

    has_post_secondary = education_category not in {
        "unknown",
        "secondary",
    }

    # 1. Education + Official Language
    education_language = 0

    if has_post_secondary:

        if education_category in (
            "one_year",
            "two_year",
            "bachelor",
        ):

            if language_9:
                education_language = 25

            elif language_7:
                education_language = 13

        elif education_category in (
            "two_plus",
            "master",
            "doctorate",
        ):

            if language_9:
                education_language = 50

            elif language_7:
                education_language = 25

    # 2. Education + Canadian Work Experience
    education_canadian_work = 0

    if has_post_secondary and canadian_work_years >= 1:

        if education_category in (
            "one_year",
            "two_year",
            "bachelor",
        ):

            if canadian_work_years >= 2:
                education_canadian_work = 25

            else:
                education_canadian_work = 13

        elif education_category in (
            "two_plus",
            "master",
            "doctorate",
        ):

            if canadian_work_years >= 2:
                education_canadian_work = 50

            else:
                education_canadian_work = 25

    # 3. Foreign Work Experience + Official Language
    foreign_work_language = 0

    if foreign_work_years >= 1:

        if foreign_work_years >= 3:

            if language_9:
                foreign_work_language = 50

            elif language_7:
                foreign_work_language = 25

        elif language_9:

            foreign_work_language = 25

        elif language_7:

            foreign_work_language = 13

    # 4. Foreign Work Experience + Canadian Work Experience
    foreign_canadian_work = 0

    if (
        foreign_work_years >= 1
        and canadian_work_years >= 1
    ):

        if (
            foreign_work_years >= 3
            and canadian_work_years >= 2
        ):

            foreign_canadian_work = 50

        elif (
            foreign_work_years >= 3
            or canadian_work_years >= 2
        ):

            foreign_canadian_work = 25

        else:

            foreign_canadian_work = 13

    # 5. Certificate of Qualification + Official Language
    has_certificate = _profile_bool(
        profile,
        "has_certificate_of_qualification",
        "certificate_of_qualification",
        "trade_certificate",
    )

    certificate_language = 0

    if has_certificate:

        if language_9:
            certificate_language = 50

        elif language_7:
            certificate_language = 25

    raw_total = (
        education_language
        + education_canadian_work
        + foreign_work_language
        + foreign_canadian_work
        + certificate_language
    )

    total = min(
        raw_total,
        100,
    )

    return {
        "earned": total,
        "max": 100,
        "factor": "skill_transferability",
        "label": "Skill Transferability",
        "status": (
            "assessed"
            if total > 0
            else "not_assessed"
        ),
        "reason": (
            f"Skill transferability: "
            f"{total}/100 CRS points"
        ),
        "breakdown": [
            {
                "factor": "education_language",
                "label": "Education + Official Language",
                "earned": education_language,
                "max": 50,
            },
            {
                "factor": "education_canadian_work",
                "label": (
                    "Education + Canadian Work Experience"
                ),
                "earned": education_canadian_work,
                "max": 50,
            },
            {
                "factor": "foreign_work_language",
                "label": (
                    "Foreign Work + Official Language"
                ),
                "earned": foreign_work_language,
                "max": 50,
            },
            {
                "factor": "foreign_work_canadian_work",
                "label": (
                    "Foreign Work + Canadian Work Experience"
                ),
                "earned": foreign_canadian_work,
                "max": 50,
            },
            {
                "factor": "certificate_language",
                "label": (
                    "Certificate of Qualification "
                    "+ Official Language"
                ),
                "earned": certificate_language,
                "max": 50,
            },
        ],
    }



def _score_canada_additional_points(
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Canada CRS additional points.

    Current supported categories:
        - Provincial / territorial nomination: 600
        - French-language proficiency: 25 or 50
        - Canadian post-secondary education: 15 or 30
        - Sibling in Canada: 15

    Important:
        A valid provincial nomination is the only category here that can
        independently add 600 CRS points.

        Job-offer CRS points are intentionally NOT added here.
    """

    total = 0
    breakdown = []

    # ─────────────────────────────────────────────────────────────────────
    # 1. Provincial / Territorial Nomination
    # ─────────────────────────────────────────────────────────────────────

    has_nomination = _profile_bool(
        profile,
        "has_provincial_nomination",
        "provincial_nomination",
        "pnp_nomination",
        "provincial_nominee",
    )

    if has_nomination:
        total += 600

        breakdown.append({
            "factor": "provincial_nomination",
            "label": "Provincial / Territorial Nomination",
            "earned": 600,
            "max": 600,
            "status": "assessed",
            "reason": (
                "Provincial or territorial nomination — "
                "600 CRS points"
            ),
        })

    # ─────────────────────────────────────────────────────────────────────
    # 2. French-language proficiency
    #
    # French NCLC 7+ in all four abilities:
    #
    #   English CLB 4 or lower / no English result -> 25
    #   English CLB 5+ in all four                 -> 50
    #
    # The profile may use french_*_nclc or french_*_clb.
    # ─────────────────────────────────────────────────────────────────────

    def get_language_level(
        *names: str,
    ) -> Optional[int]:

        value = None

        for name in names:
            if profile.get(name) is not None:
                value = profile.get(name)
                break

        if value is None or value == "":
            return None

        if isinstance(value, str):
            match = re.search(
                r"(\d{1,2})",
                value,
            )

            if not match:
                return None

            value = match.group(1)

        try:
            return max(
                0,
                min(
                    10,
                    int(float(value)),
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    french = {
        "reading": get_language_level(
            "french_reading_nclc",
            "french_reading_clb",
        ),
        "writing": get_language_level(
            "french_writing_nclc",
            "french_writing_clb",
        ),
        "speaking": get_language_level(
            "french_speaking_nclc",
            "french_speaking_clb",
        ),
        "listening": get_language_level(
            "french_listening_nclc",
            "french_listening_clb",
        ),
    }

    english = {
        "reading": get_language_level(
            "english_reading_clb",
            "first_language_reading_clb",
            "first_official_language_reading_clb",
        ),
        "writing": get_language_level(
            "english_writing_clb",
            "first_language_writing_clb",
            "first_official_language_writing_clb",
        ),
        "speaking": get_language_level(
            "english_speaking_clb",
            "first_language_speaking_clb",
            "first_official_language_speaking_clb",
        ),
        "listening": get_language_level(
            "english_listening_clb",
            "first_language_listening_clb",
            "first_official_language_listening_clb",
        ),
    }

    french_provided = all(
        value is not None
        for value in french.values()
    )

    french_points = 0

    if french_provided and all(
        value >= 7
        for value in french.values()
    ):

        english_provided = all(
            value is not None
            for value in english.values()
        )

        english_5_plus = (
            english_provided
            and all(
                value >= 5
                for value in english.values()
            )
        )

        if english_5_plus:
            french_points = 50
        else:
            french_points = 25

        total += french_points

        breakdown.append({
            "factor": "french_language",
            "label": "French Language Proficiency",
            "earned": french_points,
            "max": 50,
            "status": "assessed",
            "reason": (
                "French NCLC 7+ in all four abilities — "
                f"{french_points} additional CRS points"
            ),
        })

    elif any(
        value is not None
        for value in french.values()
    ):

        breakdown.append({
            "factor": "french_language",
            "label": "French Language Proficiency",
            "earned": 0,
            "max": 50,
            "status": "partial",
            "reason": (
                "French language results do not meet "
                "NCLC 7 in all four abilities"
            ),
        })

    # ─────────────────────────────────────────────────────────────────────
    # 3. Canadian post-secondary education
    #
    # 1-year credential -> 15
    # 2+ year credential -> 30
    # ─────────────────────────────────────────────────────────────────────

    has_canadian_education = _profile_bool(
        profile,
        "has_canadian_education",
        "education_in_canada",
        "post_secondary_education_in_canada",
    )

    canadian_education_years = 0.0

    raw_canadian_years = profile.get(
        "canadian_education_years"
    )

    if raw_canadian_years is not None:
        try:
            canadian_education_years = float(
                raw_canadian_years
            )
        except (
            TypeError,
            ValueError,
        ):
            canadian_education_years = 0.0

    if (
        canadian_education_years > 0
        or has_canadian_education
    ):

        if canadian_education_years >= 2:
            canadian_education_points = 30
        else:
            canadian_education_points = 15

        total += canadian_education_points

        breakdown.append({
            "factor": "canadian_education",
            "label": "Canadian Post-secondary Education",
            "earned": canadian_education_points,
            "max": 30,
            "status": "assessed",
            "reason": (
                "Canadian post-secondary education — "
                f"{canadian_education_points} CRS points"
            ),
        })

    # ─────────────────────────────────────────────────────────────────────
    # 4. Sibling in Canada
    #
    # Must be a qualifying sibling who is a Canadian citizen or PR.
    # ─────────────────────────────────────────────────────────────────────

    has_sibling = _profile_bool(
        profile,
        "has_sibling_in_canada",
        "sibling_in_canada",
        "brother_or_sister_in_canada",
    )

    if has_sibling:
        total += 15

        breakdown.append({
            "factor": "sibling_in_canada",
            "label": "Sibling in Canada",
            "earned": 15,
            "max": 15,
            "status": "assessed",
            "reason": (
                "Qualifying sibling in Canada — "
                "15 additional CRS points"
            ),
        })

    return {
        "earned": total,
        "max": 600,
        "factor": "additional_points",
        "label": "Additional Points",
        "status": (
            "assessed"
            if breakdown
            else "not_assessed"
        ),
        "reason": (
            f"Additional points: {total}/600"
        ),
        "breakdown": breakdown,
    }



def _score_canada_pnp_profile(
    profile: Dict[str, Any],
    pathway: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Canada PNP-specific CRS scoring.

    Currently included:
        - Age
        - Education
        - Canadian Work Experience
        - First Official Language
        - Second Official Language
        - Spouse / Common-law Partner Factors
    """

    age = int(profile.get("age") or 0)

    try:
        canadian_work_years = float(
            profile.get("canadian_work_experience_years") or 0
        )
    except (TypeError, ValueError):
        canadian_work_years = 0.0

    has_spouse = bool(
        profile.get("has_spouse")
        or profile.get("married")
        or profile.get("has_partner")
    )

    marital_status = _norm(profile.get("marital_status"))

    if marital_status in (
        "married",
        "common-law",
        "common law",
        "common_law",
        "partner",
    ):
        has_spouse = True

    age_result = _score_canada_age(
        age=age,
        has_spouse=has_spouse,
    )

    education = profile.get("education") or ""

    education_result = _score_canada_education(
        education=education,
        has_spouse=has_spouse,
    )

    work_result = _score_canada_work_experience(
        years=canadian_work_years,
        has_spouse=has_spouse,
    )

    language_result = _score_canada_first_language(
        profile=profile,
        has_spouse=has_spouse,
    )

    skill_transferability_result = _score_canada_skill_transferability(
        profile=profile,
    )

    additional_points_result = _score_canada_additional_points(
        profile=profile,
    )

    second_language_result = _score_canada_second_language(
        profile=profile,
        has_spouse=has_spouse,
    )

    spouse_result = _score_canada_spouse_factors(
        profile=profile,
    )

    crs_breakdown = [
        age_result,
        education_result,
        work_result,
        language_result,
        second_language_result,
        spouse_result,
        skill_transferability_result,
        additional_points_result,
    ]

    crs_score = (
        age_result["earned"]
        + education_result["earned"]
        + work_result["earned"]
        + language_result["earned"]
        + second_language_result["earned"]
        + spouse_result["earned"]
        + skill_transferability_result["earned"]
        + additional_points_result["earned"]
    )

    pnp_eligibility = [
        {
            "factor": "age",
            "label": "Age",
            "status": "pass" if age >= 18 else "fail",
            "reason": f"Applicant age: {age}",
        }
    ]

    return {
        "match_score": 0,
        "match_score_max": 100,

        "crs_score": crs_score,
        "crs_score_max": 1200,

        "crs_breakdown": crs_breakdown,

        "pnp_eligibility": pnp_eligibility,

        "adjustments": [],
    }


# ═════════════════════════════════════════════════════════════════════════════
# CANADA CRS — EDUCATION
# ═════════════════════════════════════════════════════════════════════════════

def _score_canada_education(
    education: Optional[str],
    has_spouse: bool,
) -> Dict[str, Any]:
    """
    Calculate Canada CRS education points.

    WITHOUT spouse:
        Secondary school                  30
        1-year post-secondary             90
        2-year post-secondary             98
        Bachelor's / 3+ year credential   120
        2+ post-secondary credentials     128
        Master's / professional degree    135
        Doctorate                         150

    WITH spouse:
        Secondary school                  28
        1-year post-secondary             84
        2-year post-secondary             91
        Bachelor's / 3+ year credential   112
        2+ post-secondary credentials     119
        Master's / professional degree    126
        Doctorate                         140
    """

    text = _norm(education)

    if not text:
        return {
            "earned": 0,
            "max": 140 if has_spouse else 150,
            "factor": "education",
            "label": "Education",
            "reason": "Education level not provided",
        }

    if has_spouse:
        points = {
            "doctorate": 140,
            "phd": 140,
            "professional": 126,
            "master": 126,
            "masters": 126,
            "two or more": 119,
            "2 or more": 119,
            "bachelor": 112,
            "bachelors": 112,
            "three-year": 112,
            "3 year": 112,
            "two-year": 91,
            "2 year": 91,
            "one-year": 84,
            "1 year": 84,
            "diploma": 84,
            "secondary": 28,
            "high school": 28,
            "class 12": 28,
            "12th": 28,
        }

        max_points = 140

    else:
        points = {
            "doctorate": 150,
            "phd": 150,
            "professional": 135,
            "master": 135,
            "masters": 135,
            "two or more": 128,
            "2 or more": 128,
            "bachelor": 120,
            "bachelors": 120,
            "three-year": 120,
            "3 year": 120,
            "two-year": 98,
            "2 year": 98,
            "one-year": 90,
            "1 year": 90,
            "diploma": 90,
            "secondary": 30,
            "high school": 30,
            "class 12": 30,
            "12th": 30,
        }

        max_points = 150

    # Check the most specific qualifications first.
    if "doctorate" in text or "phd" in text:
        earned = points["doctorate"]
        qualification = "Doctorate"

    elif "master" in text:
        earned = points["master"]
        qualification = "Master's degree"

    elif (
        "two or more" in text
        or "2 or more" in text
    ):
        earned = points["two or more"]
        qualification = "Two or more post-secondary credentials"

    elif (
        "bachelor" in text
        or "bachelors" in text
        or "three-year" in text
        or "3 year" in text
        or "degree" in text
    ):
        earned = points["bachelor"]
        qualification = "Bachelor's degree / 3+ year credential"

    elif (
        "two-year" in text
        or "2 year" in text
    ):
        earned = points["two-year"]
        qualification = "Two-year post-secondary credential"

    elif (
        "one-year" in text
        or "1 year" in text
        or "diploma" in text
    ):
        earned = points["one-year"]
        qualification = "One-year post-secondary credential"

    elif (
        "secondary" in text
        or "high school" in text
        or "class 12" in text
        or "12th" in text
    ):
        earned = points["secondary"]
        qualification = "Secondary school"

    else:
        earned = 0
        qualification = "Education level not recognised"

    return {
        "earned": earned,
        "max": max_points,
        "factor": "education",
        "label": "Education",
        "reason": (
            f"{qualification} — "
            f"{earned} CRS education points"
            if earned > 0
            else "Education level not recognised"
        ),
    }

# ═════════════════════════════════════════════════════════════════════════════
# CANADA CRS — CANADIAN WORK EXPERIENCE
# ═════════════════════════════════════════════════════════════════════════════

def _score_canada_work_experience(
    years: float,
    has_spouse: bool,
) -> Dict[str, Any]:
    """
    Calculate Canada CRS points for Canadian work experience.

    WITHOUT spouse/common-law partner:
        Less than 1 year = 0
        1 year            = 40
        2 years           = 53
        3 years           = 64
        4 years           = 72
        5+ years          = 80

    WITH spouse/common-law partner:
        Less than 1 year = 0
        1 year            = 35
        2 years           = 46
        3 years           = 56
        4 years           = 63
        5+ years          = 70
    """

    try:
        years = float(years or 0)
    except (TypeError, ValueError):
        years = 0.0

    years = max(0.0, years)

    if has_spouse:
        points_by_year = {
            1: 35,
            2: 46,
            3: 56,
            4: 63,
            5: 70,
        }
        max_points = 70
    else:
        points_by_year = {
            1: 40,
            2: 53,
            3: 64,
            4: 72,
            5: 80,
        }
        max_points = 80

    if years < 1:
        earned = 0
        experience_label = "Less than 1 year"
    elif years < 2:
        earned = points_by_year[1]
        experience_label = "1 year"
    elif years < 3:
        earned = points_by_year[2]
        experience_label = "2 years"
    elif years < 4:
        earned = points_by_year[3]
        experience_label = "3 years"
    elif years < 5:
        earned = points_by_year[4]
        experience_label = "4 years"
    else:
        earned = points_by_year[5]
        experience_label = "5 years or more"

    return {
        "earned": earned,
        "max": max_points,
        "factor": "canadian_work_experience",
        "label": "Canadian Work Experience",
        "reason": (
            f"{experience_label} Canadian work experience "
            f"— {earned} CRS points"
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# MAIN SCORING ENGINE
# ═════════════════════════════════════════════════════════════════════════════

async def score_candidate(
    profile: Dict[str, Any],
    pathways: List[Dict[str, Any]],
    rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    """
    Compute deterministic per-pathway scores + breakdown + adjustments.

    IMPORTANT:

    Canada PNP:
        Uses _score_canada_pnp_profile()

    All other pathways:
        Continue using the existing generic 7-factor /100 scoring engine.
    """

    if rules is None:

        rules = await load_scoring_rules()

    factors = rules.get(
        "factors",
        DEFAULT_RULES["factors"],
    )

    tiers = rules.get(
        "tiers",
        DEFAULT_RULES["tiers"],
    )

    curve = rules.get(
        "age_curve",
        DEFAULT_RULES["age_curve"],
    )

    levels = rules.get(
        "education_levels",
        DEFAULT_RULES["education_levels"],
    )

    buffer = rules.get(
        "experience_buffer_years",
        DEFAULT_RULES["experience_buffer_years"],
    )

    comp_max = float(
        rules.get(
            "competitiveness_penalty_max",
            DEFAULT_RULES[
                "competitiveness_penalty_max"
            ],
        )
    )

    no_offer_penalty = float(
        rules.get(
            "no_offer_penalty",
            DEFAULT_RULES[
                "no_offer_penalty"
            ],
        )
    )

    age = int(
        profile.get("age") or 0
    )

    education = (
        profile.get("education")
        or ""
    )

    years = float(
        profile.get(
            "work_experience_years"
        )
        or 0
    )

    english = (
        profile.get("english_score")
        or ""
    )

    occupation = (
        profile.get("occupation")
        or ""
    )

    has_offer = bool(
        profile.get("has_job_offer")
    )

    savings = profile.get(
        "family_savings_inr"
    )

    def w(name: str) -> float:

        return float(
            factors.get(
                name,
                {}
            ).get(
                "weight",
                0
            )
        )

    def lbl(name: str) -> str:

        return factors.get(
            name,
            {}
        ).get(
            "label",
            name.title()
        )

    # Generic pathways still use the existing 100-point maximum.
    max_total = sum(
        w(n)
        for n in factors
    )

    # Cache occupation demand per country.
    demand_cache: Dict[
        str,
        Dict[str, Any]
    ] = {}

    results: Dict[
        str,
        Any
    ] = {}

    best_slug = None
    best_score = -1

    # ═══════════════════════════════════════════════════════════════════════
    # PATHWAY LOOP
    # ═══════════════════════════════════════════════════════════════════════

    for p in pathways:

        slug = p.get("slug")

        if not slug:
            continue

        # ════════════════════════════════════════════════════════════════
        # CANADA PNP
        # ════════════════════════════════════════════════════════════════
        #
        # IMPORTANT:
        # Canada does NOT enter the generic 7-factor scoring below.
        #
        # This prevents:
        #   - generic age curve
        #   - generic education scoring
        #   - generic job offer scoring
        #   - generic competitiveness penalty
        #   - generic no-offer penalty
        #
        # from being incorrectly applied to Canada.
        # ════════════════════════════════════════════════════════════════

        if slug == "canada_pnp":

            canada_result = (
                _score_canada_pnp_profile(
                    profile,
                    p,
                )
            )

            # IMPORTANT:
            # Canada uses CRS (0-1200), NOT the generic 0-100 score.
            canada_score = int(
                canada_result.get(
                    "crs_score",
                    0,
                )
            )

            canada_score_max = int(
                canada_result.get(
                    "crs_score_max",
                    1200,
                )
            )

            results[slug] = {

                "name": p.get(
                    "name",
                    slug,
                ),

                "country": p.get(
                    "country",
                    "Canada",
                ),

                # Canada CRS score.
                "score": canada_score,

                "raw_score": canada_score,

                "score_max": canada_score_max,

                "crs_score": canada_score,

                "crs_score_max": canada_score_max,

                "crs_breakdown": canada_result.get(
                    "crs_breakdown",
                    [],
                ),

                "pnp_eligibility": canada_result.get(
                    "pnp_eligibility",
                    [],
                ),

                "adjustments": canada_result.get(
                    "adjustments",
                    [],
                ),

                # Canada CRS is not a generic 0-100 tier.
                "tier": "assessed",

                "estimated_timeline": (
                    f"{p.get('timeline_months')} months"
                    if p.get("timeline_months")
                    else None
                ),

                # Canada frontend should use crs_breakdown.
                "breakdown": [],
            }

            # Do NOT compare Canada's 1200-point CRS directly against
            # generic pathways whose scores are 0-100.
            #
            # IMPORTANT:
            # Skip the generic 7-factor calculation.
            continue

        # ════════════════════════════════════════════════════════════════
        # EXISTING GENERIC SCORING
        # ════════════════════════════════════════════════════════════════

        country = p.get(
            "country",
            "",
        )

        if country not in demand_cache:

            demand_cache[country] = (
                await _occupation_demand_ratio(
                    occupation,
                    country,
                )
            )

        demand = demand_cache[
            country
        ]

        # ─────────────────────────────────────────────────────────────
        # Existing 7-factor calculation.
        # This remains unchanged for non-Canada pathways.
        # ─────────────────────────────────────────────────────────────

        parts = [

            (
                "age",
                _score_age(
                    age,
                    p,
                    w("age"),
                    curve,
                ),
            ),

            (
                "education",
                _score_education(
                    education,
                    p,
                    w("education"),
                    levels,
                ),
            ),

            (
                "experience",
                _score_experience(
                    years,
                    p,
                    w("experience"),
                    buffer,
                ),
            ),

            (
                "english",
                _score_english(
                    english,
                    p,
                    w("english"),
                ),
            ),

            (
                "job_offer",
                _score_job_offer(
                    has_offer,
                    p,
                    w("job_offer"),
                ),
            ),

            (
                "occupation",
                _score_occupation(
                    demand,
                    w("occupation"),
                ),
            ),

            (
                "funds",
                _score_funds(
                    savings,
                    p,
                    w("funds"),
                ),
            ),
        ]

        breakdown = []

        earned_total = 0.0

        for name, res in parts:

            mx = w(name)

            if mx <= 0:
                continue

            earned_total += (
                res["earned"]
            )

            breakdown.append({

                "factor": name,

                "label": lbl(name),

                "earned": round(
                    res["earned"],
                    1,
                ),

                "max": round(
                    mx,
                    1,
                ),

                "reason": res[
                    "reason"
                ],
            })

        raw = (
            int(
                round(
                    100
                    * earned_total
                    / max_total
                )
            )
            if max_total
            else 0
        )

        raw = max(
            0,
            min(
                100,
                raw,
            ),
        )

        # ── Per-pathway adjustments ──────────────────────────────────

        adjustments: List[
            Dict[str, Any]
        ] = []

        score = float(
            raw
        )

        # ── Job-offer gate ───────────────────────────────────────────

        requires_offer = bool(
            p.get(
                "requires_job_offer"
            )
        )

        if (
            requires_offer
            and not has_offer
        ):

            before = score

            score = (
                score
                * (
                    1
                    - no_offer_penalty
                )
            )

            adjustments.append({

                "label":
                    "Job offer required",

                "delta":
                    -int(
                        round(
                            before
                            - score
                        )
                    ),

                "reason":
                    (
                        f"{p.get('name', slug)} "
                        "essentially needs an "
                        "employer/sponsor — "
                        "without an offer your "
                        "realistic chance drops sharply."
                    ),
            })

        # ── Selection competitiveness ───────────────────────────────

        comp = float(
            p.get(
                "competitiveness"
            )
            or 0
        )

        if (
            comp > 0
            and comp_max > 0
        ):

            penalty = int(
                round(
                    (
                        comp
                        / 100.0
                    )
                    * comp_max
                )
            )

            if penalty > 0:

                score -= penalty

                adjustments.append({

                    "label":
                        "Selection competitiveness",

                    "delta":
                        -penalty,

                    "reason":
                        (
                            "This is a highly "
                            f"selective route "
                            f"(competitiveness "
                            f"{int(comp)}/100) "
                            "— even strong profiles "
                            "face tough cut-offs."
                        ),
                })

        score = max(
            0,
            min(
                100,
                int(
                    round(score)
                ),
            ),
        )

        results[slug] = {

            "name": p.get(
                "name",
                slug,
            ),

            "country": country,

            "score": score,

            "raw_score": raw,

            "tier": _tier_for(
                score,
                tiers,
            ),

            "estimated_timeline": (
                f"{p.get('timeline_months')} months"
                if p.get("timeline_months")
                else None
            ),

            "breakdown": breakdown,

            "adjustments": adjustments,
        }

        if score > best_score:

            best_score = score
            best_slug = slug

    # ═══════════════════════════════════════════════════════════════════════
    # FINAL RESPONSE
    # ═══════════════════════════════════════════════════════════════════════

    return {

        "top_recommendation":
            best_slug,

        # Generic maximum.
        #
        # Canada has its own CRS maximum inside:
        # pathways[canada_pnp].crs_score_max
        "max_total":
            max_total,

        "rules_source":
            rules.get(
                "_source",
                "defaults",
            ),

        "pathways":
            results,
    }