"""Deterministic, transparent & admin-configurable eligibility scoring engine.

The visitor-facing eligibility score is computed by an explicit, weighted formula
(NOT a black-box AI number). Each pathway is scored on 7 factors; every factor
returns `earned / max` points plus a human-readable reason. The total is
normalised to 0-100 and mapped to a tier.

Pathway requirements come from the `visa_pathways` collection (the same source the
public Visa-Compare tool uses) → single source of truth.

Factor weights, tier thresholds and lookup tables live in `kb_settings`
(doc _id = 'eligibility_scoring_rules') and are editable by admins; if no override
exists the DEFAULT_RULES below are used.
"""
import re
from typing import Any, Dict, List, Optional

from core.database import db

SCORING_RULES_ID = "eligibility_scoring_rules"

# ── Default, admin-overridable rule set ──────────────────────────────────────
DEFAULT_RULES: Dict[str, Any] = {
    "version": 1,
    # Each factor's `weight` is the MAX points it can contribute.
    "factors": {
        "age":        {"weight": 25, "label": "Age"},
        "education":  {"weight": 20, "label": "Education"},
        "experience": {"weight": 18, "label": "Work Experience"},
        "english":    {"weight": 20, "label": "English Proficiency"},
        "job_offer":  {"weight": 7,  "label": "Job Offer"},
        "occupation": {"weight": 5,  "label": "Occupation in Demand"},
        "funds":      {"weight": 5,  "label": "Settlement Funds"},
    },
    # Score (0-100) >= threshold => tier. Checked strong → weak.
    "tiers": {"strong": 75, "moderate": 55, "weak": 35},
    # Age full marks up to `optimal_max`, then linear decay to `floor_ratio` of
    # the weight at the pathway's max_age. Above max_age => 0.
    "age_curve": {"optimal_max": 32, "floor_ratio": 0.3},
    # Education level → ordinal rank.
    "education_levels": {
        "phd": 5, "doctorate": 5,
        "master": 4, "masters": 4,
        "bachelor": 3, "bachelors": 3, "degree": 3, "graduate": 3,
        "diploma": 2, "associate": 2,
        "class 12": 1, "12th": 1, "high school": 1, "highschool": 1, "secondary": 1,
    },
    # Extra buffer (years) above a pathway's min experience for FULL marks.
    "experience_buffer_years": 3,
}

# Map an IELTS-equivalent band (0-9) used for the English factor.
_IELTS_BANDS = {
    "8": 8.5, "8+": 8.5, "8.0": 8.0, "8.5": 8.5,
    "7": 7.25, "7.0": 7.0, "7.5": 7.5, "7.0-7.5": 7.25,
    "6.5": 6.5, "6": 6.0, "6.0": 6.0,
    "5.5": 5.5, "5": 5.0, "5.0": 5.0,
}


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _parse_english_band(text: Optional[str]) -> Optional[float]:
    """Return an IELTS-equivalent band (0-9) from a free-text english score, or
    None if not taken / unknown."""
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
        return {10: 8.0, 9: 7.5, 8: 7.0, 7: 6.0, 6: 5.5, 5: 5.0}.get(v, max(4.0, min(9.0, float(v) - 1)))
    # B1/B2/C1 (Germany etc.)
    if "c1" in t or "c2" in t:
        return 7.5
    if "b2" in t:
        return 6.5
    if "b1" in t:
        return 5.5
    # Plain IELTS number (e.g. "ielts 7.0", "7.5", "ielts 8+")
    num = re.search(r"(\d\.?\d?)\s*\+?", t)
    if num:
        try:
            return min(9.0, float(num.group(1)))
        except ValueError:
            pass
    return None


def _required_english_band(language_required: Optional[str]) -> float:
    band = _parse_english_band(language_required)
    return band if band is not None else 6.0


def _education_rank(text: Optional[str], levels: Dict[str, int]) -> int:
    t = _norm(text)
    best = 0
    for key, rank in levels.items():
        if key in t and rank > best:
            best = rank
    return best


def _tier_for(score: int, tiers: Dict[str, int]) -> str:
    if score >= tiers.get("strong", 75):
        return "strong"
    if score >= tiers.get("moderate", 55):
        return "moderate"
    if score >= tiers.get("weak", 35):
        return "weak"
    return "unlikely"


async def load_scoring_rules() -> Dict[str, Any]:
    """Load admin override merged over defaults, else defaults."""
    doc = await db["kb_settings"].find_one({"_id": SCORING_RULES_ID})
    if not doc:
        return {**DEFAULT_RULES, "_source": "defaults"}
    merged = {**DEFAULT_RULES}
    for k, v in doc.items():
        if k == "_id":
            continue
        merged[k] = v
    merged["_source"] = "db_override"
    return merged


def _score_age(age: int, pathway: Dict, weight: float, curve: Dict) -> Dict:
    max_age = int(pathway.get("max_age") or 50)
    min_age = int(pathway.get("min_age") or 18)
    optimal = int(curve.get("optimal_max", 32))
    floor = float(curve.get("floor_ratio", 0.3))
    if age < min_age:
        return {"earned": 0.0, "reason": f"Below minimum age ({min_age}) for this pathway"}
    if age > max_age:
        return {"earned": 0.0, "reason": f"Above the age limit ({max_age}) — most points lost"}
    if age <= optimal:
        return {"earned": weight, "reason": f"Ideal age band (≤{optimal}) — full points"}
    # Linear decay from `optimal` to `max_age`
    span = max(1, max_age - optimal)
    ratio = 1 - (1 - floor) * ((age - optimal) / span)
    earned = round(weight * ratio, 1)
    return {"earned": earned, "reason": f"Age {age} is past the ideal band; points taper toward the {max_age} limit"}


def _score_education(level: str, pathway: Dict, weight: float, levels: Dict) -> Dict:
    cand = _education_rank(level, levels)
    req = _education_rank(pathway.get("min_education"), levels) or 3  # default Bachelor
    if cand == 0:
        return {"earned": 0.0, "reason": "Education level not recognised"}
    if cand >= req:
        return {"earned": weight, "reason": f"Meets/exceeds the required education ({pathway.get('min_education', 'Bachelor')})"}
    earned = round(weight * (cand / max(1, req)), 1)
    return {"earned": earned, "reason": f"Below the required {pathway.get('min_education', 'Bachelor')} — partial credit"}


def _score_experience(years: float, pathway: Dict, weight: float, buffer: int) -> Dict:
    min_req = float(pathway.get("min_work_exp_years") or 0)
    target = min_req + float(buffer)
    if target <= 0:
        target = float(buffer) or 3.0
    if years >= target:
        return {"earned": weight, "reason": f"{years:g} yrs comfortably clears this pathway's requirement"}
    earned = round(weight * (years / target), 1)
    note = "meets minimum" if years >= min_req else f"below the {min_req:g}-yr minimum"
    return {"earned": earned, "reason": f"{years:g} yrs experience — {note}"}


def _score_english(eng_text: str, pathway: Dict, weight: float) -> Dict:
    cand = _parse_english_band(eng_text)
    req = _required_english_band(pathway.get("language_required"))
    if cand is None:
        return {"earned": 0.0, "reason": "English test not taken yet — take IELTS/PTE to unlock these points"}
    if cand >= req:
        return {"earned": weight, "reason": f"English band {cand:g} meets the requirement (~{req:g})"}
    earned = round(weight * (cand / max(0.1, req)), 1)
    return {"earned": earned, "reason": f"English band {cand:g} is below the ~{req:g} needed — partial credit"}


def _score_job_offer(has_offer: bool, pathway: Dict, weight: float) -> Dict:
    requires = float(pathway.get("min_work_exp_years") or 0) == 0 and (
        "work visa" in _norm(pathway.get("category")) or "sponsor" in _norm(pathway.get("post_arrival_jobs"))
    )
    if has_offer:
        return {"earned": weight, "reason": "Job offer in hand — strong positive signal"}
    reason = "A job offer is essentially required for this route" if requires else "No job offer (optional for this pathway)"
    return {"earned": 0.0, "reason": reason}


def _score_occupation(demand_ratio: float, weight: float) -> Dict:
    earned = round(weight * demand_ratio, 1)
    if demand_ratio >= 0.99:
        reason = "Occupation found on a verified in-demand list"
    elif demand_ratio >= 0.5:
        reason = "Occupation recognised in our atlas"
    elif demand_ratio > 0:
        reason = "Occupation provided but not matched to a verified list"
    else:
        reason = "Occupation not provided"
    return {"earned": earned, "reason": reason}


def _score_funds(savings: Optional[float], pathway: Dict, weight: float) -> Dict:
    req = float(pathway.get("min_funds_inr") or 0)
    if savings is None:
        return {"earned": 0.0, "reason": "Settlement funds not disclosed"}
    if req <= 0 or savings >= req:
        return {"earned": weight, "reason": "Sufficient settlement funds"}
    earned = round(weight * (savings / req), 1)
    return {"earned": earned, "reason": f"Funds below the ~₹{req/100000:.1f}L typically required"}


async def _occupation_demand_ratio(occupation: str, country_codes: List[str]) -> float:
    """One lightweight lookup → a 0..1 demand signal applied to all pathways."""
    occ = _norm(occupation)
    if not occ or occ in ("not specified", "na", "n/a"):
        return 0.0
    try:
        col = db["occupation_master"]
        regex = {"$regex": re.escape(occupation.strip()), "$options": "i"}
        query: Dict[str, Any] = {"$or": [{"title": regex}, {"alternative_titles": regex}]}
        doc = await col.find_one(query, {"in_demand": 1, "status": 1})
        if not doc:
            return 0.4  # provided but unmatched
        if doc.get("in_demand") or doc.get("status") == "verified":
            return 1.0
        return 0.7
    except Exception:
        return 0.4


async def score_candidate(profile: Dict[str, Any], pathways: List[Dict[str, Any]],
                          rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compute deterministic per-pathway scores + breakdown.

    profile keys: age, education, work_experience_years, english_score, occupation,
                  has_job_offer, family_savings_inr, preferred_countries
    """
    if rules is None:
        rules = await load_scoring_rules()
    factors = rules.get("factors", DEFAULT_RULES["factors"])
    tiers = rules.get("tiers", DEFAULT_RULES["tiers"])
    curve = rules.get("age_curve", DEFAULT_RULES["age_curve"])
    levels = rules.get("education_levels", DEFAULT_RULES["education_levels"])
    buffer = rules.get("experience_buffer_years", DEFAULT_RULES["experience_buffer_years"])

    age = int(profile.get("age") or 0)
    education = profile.get("education") or ""
    years = float(profile.get("work_experience_years") or 0)
    english = profile.get("english_score") or ""
    occupation = profile.get("occupation") or ""
    has_offer = bool(profile.get("has_job_offer"))
    savings = profile.get("family_savings_inr")

    country_codes = profile.get("preferred_countries") or []
    demand_ratio = await _occupation_demand_ratio(occupation, country_codes)

    def w(name: str) -> float:
        return float(factors.get(name, {}).get("weight", 0))

    def lbl(name: str) -> str:
        return factors.get(name, {}).get("label", name.title())

    max_total = sum(w(n) for n in factors)
    results: Dict[str, Any] = {}
    best_slug, best_score = None, -1

    for p in pathways:
        slug = p.get("slug")
        if not slug:
            continue
        parts = [
            ("age", _score_age(age, p, w("age"), curve)),
            ("education", _score_education(education, p, w("education"), levels)),
            ("experience", _score_experience(years, p, w("experience"), buffer)),
            ("english", _score_english(english, p, w("english"))),
            ("job_offer", _score_job_offer(has_offer, p, w("job_offer"))),
            ("occupation", _score_occupation(demand_ratio, w("occupation"))),
            ("funds", _score_funds(savings, p, w("funds"))),
        ]
        breakdown = []
        earned_total = 0.0
        for name, res in parts:
            mx = w(name)
            if mx <= 0:
                continue
            earned_total += res["earned"]
            breakdown.append({
                "factor": name,
                "label": lbl(name),
                "earned": round(res["earned"], 1),
                "max": round(mx, 1),
                "reason": res["reason"],
            })
        score = int(round(100 * earned_total / max_total)) if max_total else 0
        score = max(0, min(100, score))
        results[slug] = {
            "name": p.get("name", slug),
            "country": p.get("country", ""),
            "score": score,
            "tier": _tier_for(score, tiers),
            "estimated_timeline": (f"{p.get('timeline_months')} months" if p.get("timeline_months") else None),
            "breakdown": breakdown,
        }
        if score > best_score:
            best_score, best_slug = score, slug

    return {
        "top_recommendation": best_slug,
        "max_total": max_total,
        "rules_source": rules.get("_source", "defaults"),
        "pathways": results,
    }
