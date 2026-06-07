"""Smart Sales Helper — Phase 6 v2 Part 2: Eligibility Calculator (Rule-Based).

100% deterministic, no LLM. Follows OFFICIAL government rules for each country.

Inputs: profile (primary + optional spouse) + country + visa subclass.
Outputs: per-category breakdown + total points + visa eligibility verdicts.

References:
  • Australia points test: https://immi.homeaffairs.gov.au/visas/working-in-australia/skillselect/points-test
  • Canada CRS: https://www.canada.ca/en/immigration-refugees-citizenship/services/come-canada-tool-immigration-express-entry/eligibility/criteria-comprehensive-ranking-system.html
  • NZ SMC: https://www.immigration.govt.nz/new-zealand-visas/options/work/long-term-options/skilled-migrant-category-resident-visa
"""
from typing import Dict, Any, List, Optional, Tuple


# ════════════════════════════════════════════════════════════════
# Generic helpers
# ════════════════════════════════════════════════════════════════
def _to_int(v) -> int:
    try:
        return int(float(v)) if v is not None and v != "" else 0
    except (ValueError, TypeError):
        return 0


def _to_float(v) -> float:
    try:
        return float(v) if v is not None and v != "" else 0.0
    except (ValueError, TypeError):
        return 0.0


def _safe_lower(s) -> str:
    return (s or "").strip().lower()


# ════════════════════════════════════════════════════════════════
# Phase 9.7 — Rules-engine lookup helpers
# ────────────────────────────────────────────────────────────────
# These wrappers let any subsection of the calculator read its
# points from an optional admin-override `rules` dict (loaded from
# `kb_settings.calculator_rules_<country>`). When `rules` is None
# the calculator behaves IDENTICALLY to the hardcoded baseline.
# ════════════════════════════════════════════════════════════════
def _rules_table(rules: Optional[Dict[str, Any]], table_name: str) -> Optional[Dict[str, Any]]:
    """Return the rules.tables[<table_name>] sub-document or None."""
    if not rules:
        return None
    return ((rules.get("tables") or {}).get(table_name)) or None


def _lookup_band_points(
    rules: Optional[Dict[str, Any]], table_name: str, value: float,
    default_band: Tuple[int, str], default_bands: List[Tuple[int, int, int]],
) -> Tuple[int, str]:
    """Match an integer/float value against {bands: [{min, max, points}]}.
    Falls back to `default_bands` list of (min, max, points) tuples when no override.
    Returns (points, bucket_label)."""
    tbl = _rules_table(rules, table_name)
    bands = (tbl or {}).get("bands") if tbl else None
    if isinstance(bands, list) and bands:
        for b in bands:
            try:
                lo = float(b.get("min", 0))
                hi = float(b.get("max", 99))
            except (TypeError, ValueError):
                continue
            if lo <= value <= hi:
                return int(b.get("points", 0)), f"{int(lo)}-{int(hi)}"
        return default_band
    # Hardcoded fallback
    for lo, hi, pts in default_bands:
        if lo <= value <= hi:
            return pts, f"{lo}-{hi}"
    return default_band


def _lookup_tier_points(
    rules: Optional[Dict[str, Any]], table_name: str, tier_key: str, default_pts: int,
) -> int:
    """Lookup categorical tier value (e.g. english 'superior') from `tiers` dict."""
    tbl = _rules_table(rules, table_name)
    tiers = (tbl or {}).get("tiers") if tbl else None
    if isinstance(tiers, dict) and tier_key in tiers:
        try:
            return int(tiers[tier_key])
        except (TypeError, ValueError):
            return default_pts
    return default_pts


def _lookup_category_points(
    rules: Optional[Dict[str, Any]], table_name: str, key: str, default_pts: int,
) -> int:
    """Lookup categorical value (e.g. education 'master') from `categories` dict."""
    tbl = _rules_table(rules, table_name)
    cats = (tbl or {}).get("categories") if tbl else None
    if isinstance(cats, dict) and key in cats:
        try:
            return int(cats[key])
        except (TypeError, ValueError):
            return default_pts
    return default_pts


def _lookup_named_item(
    rules: Optional[Dict[str, Any]], table_name: str, item_key: str, default_pts: int,
) -> int:
    """Lookup named bonus from `items` dict (e.g. naati_accredited: 5)."""
    tbl = _rules_table(rules, table_name)
    items = (tbl or {}).get("items") if tbl else None
    if isinstance(items, dict) and item_key in items:
        try:
            return int(items[item_key])
        except (TypeError, ValueError):
            return default_pts
    return default_pts


def _lookup_subclass_points(
    rules: Optional[Dict[str, Any]], table_name: str, subclass: str, default_pts: int,
) -> int:
    """Lookup state-nomination points by visa subclass."""
    tbl = _rules_table(rules, table_name)
    by = (tbl or {}).get("by_subclass") if tbl else None
    if isinstance(by, dict) and subclass in by:
        try:
            return int(by[subclass])
        except (TypeError, ValueError):
            return default_pts
    return default_pts


# ════════════════════════════════════════════════════════════════
# AUSTRALIA — Subclass 189 / 190 / 491
# ════════════════════════════════════════════════════════════════
def calculate_au_points(profile: Dict[str, Any], visa_subclass: str = "189", rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Australia GSM points calculator — STRICTLY per official rules.
    Returns: { breakdown: {...}, total, visa_eligibility: {...}, recommendation }

    Phase 9.7 — accepts optional `rules` dict (loaded from `kb_settings.calculator_rules_au`)
    to override point values per band/tier/category. When `rules=None`, behavior is identical
    to the hardcoded baseline (2025-26 official program-year rules).
    """
    primary = profile.get("primary_applicant") or {}
    personal = primary.get("personal") or {}
    professional = primary.get("professional") or {}
    education = primary.get("education") or {}
    language = primary.get("language") or {}
    extras = primary.get("au_extras") or {}  # NAATI, Australian Study, PY, etc.

    spouse_block = profile.get("spouse")
    marital = _safe_lower(profile.get("marital_status")) or "single"
    has_partner = marital in ("married", "de_facto")
    if not has_partner:
        spouse_block = None  # CRITICAL: marital_status is authoritative

    breakdown: Dict[str, Dict[str, Any]] = {}
    total = 0

    # 1) AGE — 18-24:25, 25-32:30, 33-39:25, 40-44:15, 45+:0 (ineligible)
    age = _to_int(personal.get("age"))
    if age >= 45:
        age_pts, age_bucket = 0, "45+_INELIGIBLE"
    elif age < 18:
        age_pts, age_bucket = 0, "below_18"
    else:
        age_pts, age_bucket = _lookup_band_points(
            rules, "age", age,
            default_band=(0, "no_band"),
            default_bands=[(18, 24, 25), (25, 32, 30), (33, 39, 25), (40, 44, 15)],
        )
    breakdown["age"] = {"value": age, "bucket": age_bucket, "points": age_pts}
    total += age_pts

    # 2) ENGLISH — Competent IELTS6:0, Proficient 7:10, Superior 8:20 (ALL BANDS min)
    scores = language.get("scores") or {}
    overall = _to_float(scores.get("overall"))
    bands = [_to_float(scores.get(b)) for b in ("listening", "reading", "writing", "speaking")]
    min_band = min([b for b in bands if b > 0] or [0])
    eng_pts = 0
    eng_bucket = "below_competent"
    if overall and min_band >= 8.0:
        eng_pts = _lookup_tier_points(rules, "english", "superior", 20)
        eng_bucket = "superior_IELTS_8"
    elif overall and min_band >= 7.0:
        eng_pts = _lookup_tier_points(rules, "english", "proficient", 10)
        eng_bucket = "proficient_IELTS_7"
    elif overall and min_band >= 6.0:
        eng_pts = _lookup_tier_points(rules, "english", "competent", 0)
        eng_bucket = "competent_IELTS_6"
    breakdown["english"] = {"overall": overall, "min_band": min_band, "bucket": eng_bucket, "points": eng_pts}
    total += eng_pts

    # 3) SKILLED EMPLOYMENT — Outside AU + Inside AU (separate)
    years_total = _to_float(professional.get("years_experience_total"))
    years_au = _to_float(professional.get("years_experience_australia"))
    years_overseas = max(0.0, years_total - years_au)

    # Outside AU
    out_pts, out_bucket = _lookup_band_points(
        rules, "overseas_experience", years_overseas,
        default_band=(0, "less_than_3"),
        default_bands=[(0, 2, 0), (3, 4, 5), (5, 7, 10), (8, 99, 15)],
    )
    breakdown["experience_overseas"] = {"value": years_overseas, "bucket": out_bucket, "points": out_pts}
    total += out_pts

    # Inside AU
    in_pts, in_bucket = _lookup_band_points(
        rules, "australia_experience", years_au,
        default_band=(0, "less_than_1"),
        default_bands=[(0, 0, 0), (1, 2, 5), (3, 4, 10), (5, 7, 15), (8, 99, 20)],
    )
    breakdown["experience_australia"] = {"value": years_au, "bucket": in_bucket, "points": in_pts}
    total += in_pts

    # 4) EDUCATION — PhD:20, Bachelor/Master:15, Diploma/Trade:10, Other:0
    qual = _safe_lower(education.get("highest_qualification"))
    edu_pts = 0
    edu_bucket = "other"
    if qual in ("doctorate", "phd"):
        edu_pts = _lookup_category_points(rules, "education", "doctorate", 20)
        edu_bucket = "doctorate"
    elif qual in ("master", "bachelor", "bachelor_3yr", "honours"):
        edu_pts = _lookup_category_points(rules, "education", qual if qual in ("master", "bachelor") else "bachelor", 15)
        edu_bucket = "bachelor_or_masters"
    elif qual in ("diploma", "trade", "advanced_diploma"):
        edu_pts = _lookup_category_points(rules, "education", qual if qual in ("diploma", "trade") else "diploma", 10)
        edu_bucket = "diploma_or_trade"
    breakdown["education"] = {"value": qual, "bucket": edu_bucket, "points": edu_pts}
    total += edu_pts

    # 5) AUSTRALIAN STUDY REQUIREMENT — 2+ years study in AU = 5 pts
    if bool(extras.get("australian_study_2_years")):
        pts = _lookup_named_item(rules, "bonuses", "australian_study_2_years", 5)
        breakdown["australian_study"] = {"value": True, "points": pts}
        total += pts

    # 6) SPECIALIST EDUCATION (STEM at AU) — 10 pts
    if bool(extras.get("specialist_education_stem_au")):
        pts = _lookup_named_item(rules, "bonuses", "specialist_education_stem_au", 10)
        breakdown["specialist_education"] = {"value": True, "points": pts}
        total += pts

    # 7) PROFESSIONAL YEAR — 5 pts
    if bool(extras.get("professional_year_completed")):
        pts = _lookup_named_item(rules, "bonuses", "professional_year_completed", 5)
        breakdown["professional_year"] = {"value": True, "points": pts}
        total += pts

    # 8) NAATI — 5 pts
    if bool(extras.get("naati_accredited")):
        pts = _lookup_named_item(rules, "bonuses", "naati_accredited", 5)
        breakdown["naati"] = {"value": True, "points": pts}
        total += pts

    # 9) REGIONAL STUDY (AU) — 5 pts
    if bool(extras.get("regional_study_au")):
        pts = _lookup_named_item(rules, "bonuses", "regional_study_au", 5)
        breakdown["regional_study"] = {"value": True, "points": pts}
        total += pts

    # 10) PARTNER SKILLS — EXACT rules
    partner_block = _au_partner_skills(marital, spouse_block, rules=rules)
    if partner_block["points"] or partner_block.get("note"):
        breakdown["partner"] = partner_block
        total += partner_block["points"]

    # 11) STATE/TERRITORY NOMINATION — only if 190 (5) or 491 (15)
    visa = (visa_subclass or "189").strip()
    nomination_pts = 0
    if visa == "190" and bool(extras.get("state_nominated")):
        nomination_pts = _lookup_subclass_points(rules, "state_nomination", "190", 5)
        breakdown["state_nomination"] = {"value": "190_state", "points": nomination_pts}
    elif visa == "491" and bool(extras.get("state_nominated")):
        nomination_pts = _lookup_subclass_points(rules, "state_nomination", "491", 15)
        breakdown["state_nomination"] = {"value": "491_regional", "points": nomination_pts}
    total += nomination_pts

    # Visa eligibility — official minimum is 65 for 189/190/491; age 45+ = ineligible
    age_eligible = age < 45 and age >= 18
    english_eligible = overall >= 6.0 and (min_band == 0 or min_band >= 6.0)  # at least competent
    base_eligible = age_eligible and english_eligible and total >= 65

    visa_eligibility = {
        "189": {
            "eligible": base_eligible and edu_pts >= 10,  # 189 typically needs skill assessment + bachelor+
            "min_required": 65,
            "your_score": total,
            "gap": max(0, 65 - total),
            "requires_state_nomination": False,
            "notes": "Independent Skilled visa. No nomination/sponsor needed.",
        },
        "190": {
            "eligible": base_eligible and bool(extras.get("state_nominated")),
            "min_required": 65,
            "your_score": total,
            "gap": max(0, 65 - total),
            "requires_state_nomination": True,
            "notes": "Requires nomination by a state/territory government.",
        },
        "491": {
            "eligible": base_eligible and bool(extras.get("state_nominated")),
            "min_required": 65,
            "your_score": total,
            "gap": max(0, 65 - total),
            "requires_state_nomination": True,
            "notes": "Regional 5-year provisional, leads to PR via 191. State or family sponsorship required.",
        },
    }

    if not age_eligible:
        for v in visa_eligibility.values():
            v["eligible"] = False
            v["notes"] = f"INELIGIBLE: Age must be 18-44 (you are {age})"

    # Recommendation
    recommendation = _au_visa_recommendation(total, visa_eligibility, age, english_eligible)

    return {
        "country_code": "AU",
        "visa_subclass": visa,
        "breakdown": breakdown,
        "total": total,
        "visa_eligibility": visa_eligibility,
        "recommendation": recommendation,
    }


def _au_partner_skills(marital: str, spouse_block: Optional[Dict[str, Any]], rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Exact AU partner-skills rules.
    Returns: {matched_key, points, note, contribution_type, marital_status}.

    Phase 9.7 — accepts optional `rules` so admins can override the 4 outcome point values
    via `kb_settings.calculator_rules_au.tables.partner_skills.categories.{key}`.
    """
    # Helper to fetch the points for a given outcome key
    def _pts(key: str, default: int) -> int:
        return _lookup_category_points(rules, "partner_skills", key, default)

    # SINGLE / DIVORCED / WIDOWED / SEPARATED → +10 single_or_pr_partner
    if marital not in ("married", "de_facto"):
        return {
            "matched_key": "single_or_pr_partner",
            "points": _pts("single_or_pr_partner", 10),
            "note": f"{marital.title()} applicant — full +10 partner-skills bonus awarded",
            "contribution_type": "not_applicable",
            "marital_status": marital,
        }

    if not spouse_block:
        return {
            "matched_key": "not_applicable",
            "points": 0,
            "note": "Marital status married/de_facto but no spouse details provided — please fill spouse section",
            "contribution_type": "not_applicable",
            "marital_status": marital,
        }

    contribution = (spouse_block.get("contribution_type") or "not_applicable").lower()
    is_pr = bool(spouse_block.get("is_australian_pr_or_citizen"))
    on_visa = bool(spouse_block.get("is_applicant_on_visa"))

    # AU PR/Citizen spouse → +10
    if is_pr or contribution == "australian_pr_citizen":
        return {
            "matched_key": "single_or_pr_partner",
            "points": _pts("single_or_pr_partner", 10),
            "note": "Spouse is AU PR / Citizen — counted as no migrating partner",
            "contribution_type": contribution,
            "marital_status": marital,
        }

    # Spouse not migrating on this visa → treat as single
    if not on_visa:
        return {
            "matched_key": "single_or_pr_partner",
            "points": _pts("single_or_pr_partner", 10),
            "note": "Spouse will not migrate on this visa — applicant treated as single",
            "contribution_type": contribution,
            "marital_status": marital,
        }

    # Spouse details
    sp_age = _to_int((spouse_block.get("personal") or {}).get("age"))
    sp_lang = spouse_block.get("language") or {}
    sp_scores = sp_lang.get("scores") or {}
    sp_overall = _to_float(sp_scores.get("overall"))
    sp_bands = [_to_float(sp_scores.get(b)) for b in ("listening", "reading", "writing", "speaking")]
    sp_min_band = min([b for b in sp_bands if b > 0] or [sp_overall])
    sp_competent_eng = sp_overall >= 6.0 and (sp_min_band == 0 or sp_min_band >= 6.0)

    # Option A — Skill assessment: gates age<45 + competent eng
    if contribution == "skill_assessment":
        gates = []
        if sp_age and sp_age >= 45:
            gates.append(f"spouse age {sp_age} ≥ 45")
        if not sp_competent_eng:
            gates.append("spouse English below competent (IELTS 6+ all bands)")
        if not gates:
            return {
                "matched_key": "skilled_partner",
                "points": _pts("skilled_partner", 10),
                "note": "Spouse meets all gates: age<45, competent English, positive skill assessment, on visa",
                "contribution_type": contribution,
                "marital_status": marital,
            }
        if sp_competent_eng:
            return {
                "matched_key": "competent_english_only",
                "points": _pts("competent_english_only", 5),
                "note": f"Downgraded to English-only (gate failed: {', '.join(gates)})",
                "contribution_type": contribution,
                "marital_status": marital,
            }
        return {
            "matched_key": "skill_assessment_blocked",
            "points": 0,
            "note": f"Skill-assessment partner points blocked: {', '.join(gates)}",
            "contribution_type": contribution,
            "marital_status": marital,
        }

    # Option B — English only
    if contribution == "english_only":
        if sp_competent_eng:
            return {
                "matched_key": "competent_english_only",
                "points": _pts("competent_english_only", 5),
                "note": "Spouse has competent English (IELTS 6+ all bands)",
                "contribution_type": contribution,
                "marital_status": marital,
            }
        return {
            "matched_key": "english_only_blocked",
            "points": 0,
            "note": "English-only points blocked: spouse English below IELTS 6 (per-band)",
            "contribution_type": contribution,
            "marital_status": marital,
        }

    # Option C — Non-contributing
    if contribution == "non_contributing":
        return {
            "matched_key": "non_contributing",
            "points": _pts("non_contributing", 0),
            "note": "Spouse will be on visa but is not contributing to points",
            "contribution_type": contribution,
            "marital_status": marital,
        }

    return {
        "matched_key": "not_applicable",
        "points": 0,
        "note": "Spouse contribution type not declared — please pick Option A/B/C/D",
        "contribution_type": contribution,
        "marital_status": marital,
    }


def _au_visa_recommendation(total: int, visa_eligibility: Dict[str, Any], age: int, eng_ok: bool) -> str:
    if age >= 45:
        return f"INELIGIBLE: Age {age} exceeds 44-year cap for all GSM visas. Consider Employer-Sponsored (482/186) where age caps may differ."
    if not eng_ok:
        return "English below Competent (IELTS 6 all bands) — most GSM visas require at least Competent English. Recommend taking IELTS / PTE."
    if total >= 80:
        return "EXCELLENT — Strong invitation chance across 189/190/491. Apply for 189 (no nomination needed)."
    if total >= 75:
        return "GOOD — Apply for 189 if occupation on MLTSSL. Otherwise pursue 190 or 491 with state nomination."
    if total >= 65:
        return "MINIMUM viable — Eligible for invitation, but the more competitive the occupation, the higher the cutoff. Strongly consider 190/491 with state nomination."
    return f"BELOW MINIMUM — Need {65 - total} more points. Recommend IELTS upgrade, NAATI, Professional Year, or pursuing employer-sponsored pathway."


# ════════════════════════════════════════════════════════════════
# CANADA — Express Entry CRS (simplified to core + skill transferability)
# ════════════════════════════════════════════════════════════════
def calculate_ca_crs(profile: Dict[str, Any], with_spouse: bool = False) -> Dict[str, Any]:
    """Canada CRS — covers the 4 high-level groups:
       A. Core (age, edu, language, CA work)
       B. Spouse (edu, language, CA work) — if applicable
       C. Skill transferability (education + language, edu + CA work, foreign work + language, etc.)
       D. Additional points (provincial nomination, job offer, French, sibling, CA edu)
    """
    primary = profile.get("primary_applicant") or {}
    personal = primary.get("personal") or {}
    education = primary.get("education") or {}
    language = primary.get("language") or {}
    extras = primary.get("ca_extras") or {}

    marital = _safe_lower(profile.get("marital_status")) or "single"
    has_partner = marital in ("married", "de_facto")
    spouse_block = profile.get("spouse") if has_partner else None
    spouse_present = bool(spouse_block) and with_spouse

    breakdown: Dict[str, Dict[str, Any]] = {}
    total = 0

    # ── A. Core / Human Capital ───────────────────────────────
    # A.1 Age (different table for with/without spouse)
    age = _to_int(personal.get("age"))
    age_pts = _ca_age_points(age, spouse_present)
    breakdown["ca_age"] = {"value": age, "points": age_pts}
    total += age_pts

    # A.2 Education
    qual = _safe_lower(education.get("highest_qualification"))
    edu_pts = _ca_education_points(qual, spouse_present)
    breakdown["ca_education"] = {"value": qual, "points": edu_pts}
    total += edu_pts

    # A.3 First Official Language (English IELTS → CLB)
    scores = language.get("scores") or {}
    bands = [_to_float(scores.get(b)) for b in ("listening", "reading", "writing", "speaking")]
    if all(b == 0 for b in bands) and _to_float(scores.get("overall")):
        # Approximate from overall if individual bands missing
        bands = [_to_float(scores.get("overall"))] * 4
    clb_per_band = [_ielts_to_clb(b) for b in bands]
    eng_pts = sum(_ca_lang_points_per_clb(c, spouse_present) for c in clb_per_band)
    breakdown["ca_first_language"] = {"clb_per_band": clb_per_band, "points": eng_pts}
    total += eng_pts

    # A.4 Canadian work experience
    years_ca = _to_float(extras.get("canadian_work_years"))
    ca_work_pts = _ca_work_points(years_ca, spouse_present)
    breakdown["ca_canadian_work"] = {"value": years_ca, "points": ca_work_pts}
    total += ca_work_pts

    # ── B. Spouse Factors ─────────────────────────────────────
    if spouse_present and spouse_block:
        sp_edu = _safe_lower((spouse_block.get("education") or {}).get("highest_qualification"))
        sp_edu_pts = min(_ca_education_points(sp_edu, False) // 15, 10)  # spouse caps at 10
        breakdown["ca_spouse_education"] = {"value": sp_edu, "points": sp_edu_pts}
        total += sp_edu_pts

        sp_scores = (spouse_block.get("language") or {}).get("scores") or {}
        sp_bands = [_to_float(sp_scores.get(b)) for b in ("listening", "reading", "writing", "speaking")]
        sp_clb = [_ielts_to_clb(b) for b in sp_bands if b]
        sp_lang_pts = min(sum(1 for c in sp_clb if c >= 9) * 5, 20)  # simplified
        breakdown["ca_spouse_language"] = {"clb": sp_clb, "points": sp_lang_pts}
        total += sp_lang_pts

    # ── D. Additional Points (most impactful first) ──────────
    if bool(extras.get("provincial_nomination")):
        breakdown["ca_provincial_nomination"] = {"value": True, "points": 600}
        total += 600
    if bool(extras.get("job_offer_noc_00")):
        breakdown["ca_job_offer"] = {"value": "NOC 00 senior management", "points": 200}
        total += 200
    elif bool(extras.get("job_offer_noc_0_a_b")):
        breakdown["ca_job_offer"] = {"value": "NOC 0/A/B job offer", "points": 50}
        total += 50
    if bool(extras.get("canadian_education_3plus_years")):
        breakdown["ca_canadian_education"] = {"value": "3+ years", "points": 30}
        total += 30
    elif bool(extras.get("canadian_education_1_2_years")):
        breakdown["ca_canadian_education"] = {"value": "1-2 years", "points": 15}
        total += 15
    if bool(extras.get("sibling_in_canada")):
        breakdown["ca_sibling"] = {"value": True, "points": 15}
        total += 15
    if bool(extras.get("french_proficiency_clb_7")):
        breakdown["ca_french"] = {"value": "CLB 7+", "points": 50}
        total += 50

    # Visa eligibility — Express Entry needs minimum CRS that varies by draw
    visa_eligibility = {
        "EE-FSWP": {
            "eligible": total >= 67,  # FSWP threshold 67 (one-time eligibility test, not CRS)
            "min_required": 67,
            "your_score": total,
            "gap": max(0, 67 - total),
            "notes": "Federal Skilled Worker — needs ≥67 points on FSWP grid + valid Express Entry profile.",
        },
        "EE-CEC": {
            "eligible": years_ca >= 1,
            "min_required": "1 year Canadian work",
            "your_score": total,
            "notes": "Canadian Experience Class — needs 1+ year of skilled Canadian work in last 3 years.",
        },
        "PNP": {
            "eligible": bool(extras.get("provincial_nomination")),
            "min_required": "Provincial Nomination",
            "your_score": total,
            "notes": "Provincial Nominee Program — automatic 600 CRS points if nominated.",
        },
    }
    return {
        "country_code": "CA",
        "with_spouse_factors": spouse_present,
        "breakdown": breakdown,
        "total": total,
        "visa_eligibility": visa_eligibility,
        "recommendation": _ca_recommendation(total, visa_eligibility),
    }


def _ca_age_points(age: int, with_spouse: bool) -> int:
    """CRS age points (with vs without spouse). Source: IRCC CRS table."""
    table_no_spouse = {17: 0, 18: 99, 19: 105, 20: 110, 21: 110, 22: 110, 23: 110, 24: 110, 25: 110, 26: 110, 27: 110, 28: 110, 29: 110,
                      30: 105, 31: 99, 32: 94, 33: 88, 34: 83, 35: 77, 36: 72, 37: 66, 38: 61, 39: 55, 40: 50, 41: 39, 42: 28,
                      43: 17, 44: 6, 45: 0}
    table_with_spouse = {17: 0, 18: 90, 19: 95, 20: 100, 21: 100, 22: 100, 23: 100, 24: 100, 25: 100, 26: 100, 27: 100, 28: 100,
                        29: 100, 30: 95, 31: 90, 32: 85, 33: 80, 34: 75, 35: 70, 36: 65, 37: 60, 38: 55, 39: 50, 40: 45, 41: 35,
                        42: 25, 43: 15, 44: 5, 45: 0}
    tbl = table_with_spouse if with_spouse else table_no_spouse
    return tbl.get(age, 0)


def _ca_education_points(qual: str, with_spouse: bool) -> int:
    no_sp = {"doctorate": 150, "phd": 150, "master": 135, "bachelor": 120, "honours": 120,
             "diploma": 98, "trade": 90, "high_school": 30}
    with_sp = {"doctorate": 140, "phd": 140, "master": 126, "bachelor": 112, "honours": 112,
              "diploma": 91, "trade": 84, "high_school": 28}
    tbl = with_sp if with_spouse else no_sp
    return tbl.get(qual, 0)


def _ielts_to_clb(score: float) -> int:
    """IELTS overall to CLB level mapping (per IRCC)."""
    if score >= 8.0:
        return 10
    if score >= 7.5:
        return 9
    if score >= 7.0:
        return 9
    if score >= 6.5:
        return 8
    if score >= 6.0:
        return 7
    if score >= 5.5:
        return 6
    if score >= 5.0:
        return 5
    return 4


def _ca_lang_points_per_clb(clb: int, with_spouse: bool) -> int:
    """Points per ability (L/R/W/S) for first official language. Max 32/ability without spouse, 29 with."""
    no_sp = {4: 0, 5: 1, 6: 1, 7: 17, 8: 23, 9: 31, 10: 32}
    with_sp = {4: 0, 5: 1, 6: 1, 7: 16, 8: 22, 9: 29, 10: 32}
    tbl = with_sp if with_spouse else no_sp
    return tbl.get(clb, 0)


def _ca_work_points(years: float, with_spouse: bool) -> int:
    no_sp = [(0, 0), (1, 40), (2, 53), (3, 64), (4, 72), (5, 80)]
    with_sp = [(0, 0), (1, 35), (2, 46), (3, 56), (4, 63), (5, 70)]
    tbl = with_sp if with_spouse else no_sp
    pts = 0
    for threshold, p in tbl:
        if years >= threshold:
            pts = p
    return pts


def _ca_recommendation(total: int, ve: Dict[str, Any]) -> str:
    if ve["PNP"]["eligible"]:
        return "EXCELLENT — PNP nomination gives automatic +600 CRS. Apply via the nominating province."
    if total >= 480:
        return "STRONG profile — Recent CRS cutoffs have been 480-500. High chance of an ITA in 1-3 rounds."
    if total >= 440:
        return "GOOD profile — Within striking distance of CRS cutoff. Consider improving language (CLB 9+) or pursuing PNP."
    if total >= 380:
        return "BORDERLINE — CRS cutoffs vary by program. Consider IRCC CEC, French ability, or PNP routes to boost score."
    return "BELOW current cutoffs (most draws need 470+). Focus on: IELTS upgrade to CLB 9+ all bands (+~50), French (+50), provincial nomination (+600)."


# ════════════════════════════════════════════════════════════════
# NEW ZEALAND — Skilled Migrant Category (SMC) Points
# ════════════════════════════════════════════════════════════════
def calculate_nz_smc(profile: Dict[str, Any]) -> Dict[str, Any]:
    """NZ SMC points. New system uses 6-pt minimum threshold across categories."""
    primary = profile.get("primary_applicant") or {}
    personal = primary.get("personal") or {}
    education = primary.get("education") or {}
    professional = primary.get("professional") or {}
    extras = primary.get("nz_extras") or {}

    marital = _safe_lower(profile.get("marital_status")) or "single"
    has_partner = marital in ("married", "de_facto")
    spouse_block = profile.get("spouse") if has_partner else None

    breakdown: Dict[str, Dict[str, Any]] = {}
    total = 0

    # 1) AGE (max 30)
    age = _to_int(personal.get("age"))
    age_pts = 0
    if age >= 20 and age <= 29:
        age_pts = 30
    elif age >= 30 and age <= 39:
        age_pts = 25
    elif age >= 40 and age <= 44:
        age_pts = 20
    elif age >= 45 and age <= 49:
        age_pts = 10
    breakdown["nz_age"] = {"value": age, "points": age_pts}
    total += age_pts

    # 2) Qualification (max 70)
    qual = _safe_lower(education.get("highest_qualification"))
    if qual in ("doctorate", "phd"):
        q_pts = 70
    elif qual in ("master", "honours"):
        q_pts = 50
    elif qual in ("bachelor", "bachelor_3yr"):
        q_pts = 40
    elif qual in ("diploma", "trade", "advanced_diploma"):
        q_pts = 20
    else:
        q_pts = 0
    breakdown["nz_qualification"] = {"value": qual, "points": q_pts}
    total += q_pts

    # 3) Skilled Employment (max 50)
    if bool(extras.get("nz_skilled_employment_current")):
        breakdown["nz_skilled_employment"] = {"value": True, "points": 50}
        total += 50

    # 4) Work Experience (max 30)
    years_skilled = _to_float(professional.get("years_experience_total"))
    if years_skilled >= 10:
        we_pts = 30
    elif years_skilled >= 8:
        we_pts = 20
    elif years_skilled >= 6:
        we_pts = 15
    elif years_skilled >= 4:
        we_pts = 10
    elif years_skilled >= 2:
        we_pts = 5
    else:
        we_pts = 0
    breakdown["nz_work_experience"] = {"value": years_skilled, "points": we_pts}
    total += we_pts

    # 5) Job Offer (max 30) — if not already counted as current employment
    if not extras.get("nz_skilled_employment_current") and bool(extras.get("nz_job_offer")):
        breakdown["nz_job_offer"] = {"value": True, "points": 30}
        total += 30

    # 6) Partner Qualification (max 20)
    if has_partner and spouse_block:
        sp_qual = _safe_lower((spouse_block.get("education") or {}).get("highest_qualification"))
        if sp_qual in ("doctorate", "phd", "master"):
            breakdown["nz_partner_qual"] = {"value": sp_qual, "points": 20}
            total += 20
        elif sp_qual in ("bachelor", "honours"):
            breakdown["nz_partner_qual"] = {"value": sp_qual, "points": 10}
            total += 10

    # 7) Bonus — Regional employment (max 30)
    if bool(extras.get("regional_employment_nz")):
        breakdown["nz_regional"] = {"value": True, "points": 30}
        total += 30

    # NZ SMC: minimum 6 points needed across the categories (new SMC threshold post-2023)
    visa_eligibility = {
        "SMC-SkilledMigrant": {
            "eligible": total >= 100,  # Pre-2023 threshold; current 6-point system overlay below
            "min_required": 100,
            "your_score": total,
            "gap": max(0, 100 - total),
            "notes": "Skilled Migrant Category (SMC). Post-2023 reform also requires 6+ points from points categories; check immigration.govt.nz for the current threshold.",
        },
        "AEWV": {
            "eligible": bool(extras.get("nz_job_offer")) or bool(extras.get("nz_skilled_employment_current")),
            "min_required": "Accredited employer job offer",
            "your_score": total,
            "notes": "Accredited Employer Work Visa — first step to PR via Green List or 24-month residence pathway.",
        },
    }
    return {
        "country_code": "NZ",
        "breakdown": breakdown,
        "total": total,
        "visa_eligibility": visa_eligibility,
        "recommendation": _nz_recommendation(total, visa_eligibility, age),
    }


def _nz_recommendation(total: int, ve: Dict[str, Any], age: int) -> str:
    if age >= 56:
        return "INELIGIBLE: Age 56+ is over the SMC cap. Consider AEWV via Accredited Employer."
    if total >= 160:
        return "EXCELLENT — High chance of Expression of Interest selection."
    if total >= 120:
        return "GOOD — Above the typical 100-point threshold. Apply EOI via SkillFinder."
    if total >= 100:
        return "MINIMUM viable — Eligible to submit EOI. Consider boosting via job offer (+30) or regional employment (+30)."
    return f"BELOW threshold — Need {100 - total} more points. Strongest options: skilled job offer in NZ (+30-50) or partner with Bachelor+ (+10-20)."


# ════════════════════════════════════════════════════════════════
# Master dispatcher
# ════════════════════════════════════════════════════════════════
def calculate(profile: Dict[str, Any], country: str, visa_subclass: Optional[str] = None, rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run the calculator for a country.

    Phase 6.10.1 note: the result is a pure synchronous rule-engine output.
    Callers that want to surface `template_status` / `template_in_use` should
    look up `core.template_calculator.template_status(country)` themselves
    (async) and merge the result. This keeps `calculate()` testable without DB.

    Phase 9.7: optional `rules` dict (loaded from `kb_settings.calculator_rules_<country>`
    via `core.rules_engine.load_rules()`) allows admin overrides. When None, hardcoded
    defaults are used (identical to pre-9.7 behavior).
    """
    c = (country or "AU").upper()
    if c == "AU":
        return calculate_au_points(profile, visa_subclass or "189", rules=rules)
    if c == "CA":
        marital = _safe_lower(profile.get("marital_status"))
        with_spouse = marital in ("married", "de_facto") and bool(profile.get("spouse"))
        return calculate_ca_crs(profile, with_spouse)
    if c == "NZ":
        return calculate_nz_smc(profile)
    return {"error": f"Country '{c}' not supported by calculator yet (only AU, CA, NZ)"}


async def calculate_with_rules(db, profile: Dict[str, Any], country: str, visa_subclass: Optional[str] = None) -> Dict[str, Any]:
    """Phase 9.7 — async wrapper that loads admin overrides from `kb_settings`
    then calls `calculate()`. Includes the rules `source` in the response under
    `rules_source` so the UI can show whether DB-override or hardcoded-defaults
    were applied.
    """
    from core.rules_engine import load_rules, supported_countries
    c = (country or "AU").upper()
    if c not in supported_countries():
        return calculate(profile, c, visa_subclass)
    try:
        rules = await load_rules(db, c)
    except Exception:
        rules = None
    result = calculate(profile, c, visa_subclass, rules=rules)
    if isinstance(result, dict) and rules:
        result["rules_source"] = rules.get("source")
        result["rules_version"] = rules.get("version")
    return result
