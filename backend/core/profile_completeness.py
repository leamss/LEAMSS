"""Phase 6.7 Part 2 — Profile Completeness Scorer.

Computes a 0-100 completeness score for an eligibility profile + a list of
warnings/missing-field hints so the user can review BEFORE running the AI analysis.

This drives the Pre-Analysis Verification Page.
"""
from typing import Dict, Any, List, Tuple


# Sections (key, label, weight) — weights sum to 100
SECTIONS = [
    ("personal", "Personal Information", 12),
    ("professional", "Profession & Experience", 22),
    ("education", "Education", 14),
    ("language", "Language Proficiency", 14),
    ("marital", "Marital Status & Family", 8),
    ("spouse", "Spouse Details (if applicable)", 10),
    ("preferences", "Country Preferences", 10),
    ("additional", "Additional Factors", 10),
]


def _has(v) -> bool:
    """Return True if a value is meaningfully present."""
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def _score_personal(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    primary = p.get("primary_applicant") or {}
    personal = primary.get("personal") or p.get("basic_info") or {}
    needed = [
        ("full_name", personal.get("full_name") or p.get("name"), "Full name"),
        ("date_of_birth", personal.get("date_of_birth"), "Date of birth"),
        ("current_country", personal.get("current_country"), "Current country of residence"),
        ("nationality", personal.get("nationality"), "Nationality"),
    ]
    filled = sum(1 for _, v, _ in needed if _has(v))
    score = filled / len(needed)
    missing = [label for _, v, label in needed if not _has(v)]
    return score, [f"Missing: {m}" for m in missing]


def _score_professional(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    primary = p.get("primary_applicant") or {}
    prof = primary.get("professional") or p.get("professional") or {}
    needed = [
        ("current_profession", prof.get("current_profession"), "Current profession (CRITICAL — drives occupation code)"),
        ("designation", prof.get("designation"), "Current designation"),
        ("years_experience_total", prof.get("years_experience_total"), "Total years of experience"),
        ("industry", prof.get("industry"), "Industry sector"),
        ("employer_name", prof.get("employer_name"), "Current employer name"),
    ]
    filled = 0
    warnings = []
    for key, v, label in needed:
        if _has(v) and (key != "years_experience_total" or float(v or 0) > 0):
            filled += 1
        else:
            warnings.append(f"Missing: {label}")

    # Add work_history bonus
    wh = primary.get("work_history") or p.get("work_history") or []
    if len(wh) >= 1:
        filled += 0.5  # partial bonus
    else:
        warnings.append("Tip: Add work history entries for stronger analysis")

    score = min(1.0, filled / len(needed))
    return score, warnings


def _score_education(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    primary = p.get("primary_applicant") or {}
    edu = primary.get("education") or p.get("education") or {}
    needed = [
        ("highest_qualification", edu.get("highest_qualification"), "Highest qualification (master/bachelor/etc.)"),
        ("field_of_study", edu.get("field_of_study"), "Field of study"),
        ("year_completed", edu.get("year_completed"), "Year completed"),
        ("country", edu.get("country"), "Country of education"),
    ]
    filled = sum(1 for _, v, _ in needed if _has(v))
    missing = [label for _, v, label in needed if not _has(v)]
    return filled / len(needed), [f"Missing: {m}" for m in missing]


def _score_language(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    primary = p.get("primary_applicant") or {}
    lang = primary.get("language") or p.get("language_proficiency") or {}
    scores = lang.get("scores") or {}
    test_completed = lang.get("test_completed")
    has_overall = scores.get("overall") and float(scores.get("overall") or 0) > 0
    bands = [scores.get(b) for b in ("listening", "reading", "writing", "speaking")]
    has_all_bands = all(b and float(b or 0) > 0 for b in bands)

    warnings = []
    score = 0.0
    if test_completed and has_overall and has_all_bands:
        score = 1.0
    elif test_completed and has_overall:
        score = 0.6
        warnings.append("Tip: Enter all 4 band scores (Listening, Reading, Writing, Speaking) for per-band gate checks")
    elif test_completed:
        score = 0.3
        warnings.append("Language test marked complete but overall score is missing")
    else:
        score = 0.0
        warnings.append("Tip: Language test NOT taken — most points-based visas REQUIRE English proficiency. Add target scores if planning a test.")

    return score, warnings


def _score_marital(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    marital = p.get("marital_status") or (p.get("basic_info") or {}).get("marital_status")
    if _has(marital):
        return 1.0, []
    return 0.0, ["Missing: Marital status (REQUIRED — drives spouse & partner points logic)"]


def _score_spouse(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Only applicable when marital_status implies a partner."""
    marital = p.get("marital_status") or (p.get("basic_info") or {}).get("marital_status") or "single"
    if marital not in ("married", "de_facto"):
        return 1.0, []  # N/A — full credit

    spouse = p.get("spouse") or {}
    fam = p.get("family") or {}
    contribution = spouse.get("contribution_type") or fam.get("spouse_contribution_type") or "not_applicable"

    warnings = []
    if contribution == "not_applicable":
        warnings.append("Spouse contribution type NOT set — please pick from skill_assessment / english_only / non_contributing / australian_pr_citizen")
        return 0.2, warnings

    # If contribution_type promises points, validate the supporting data
    if contribution == "skill_assessment":
        spouse_personal = spouse.get("personal") or {}
        spouse_lang = spouse.get("language") or {}
        scores = spouse_lang.get("scores") or {}
        if not spouse_personal.get("age"):
            warnings.append("Spouse age missing (skill_assessment requires age <45)")
        if not scores.get("overall") or float(scores.get("overall") or 0) < 6.0:
            warnings.append("Spouse IELTS overall missing or below 6.0 (skill_assessment requires competent English)")
        if not (spouse.get("professional") or {}).get("current_profession"):
            warnings.append("Spouse profession missing — needed for positive skill assessment")
    elif contribution == "english_only":
        spouse_lang = spouse.get("language") or {}
        scores = spouse_lang.get("scores") or {}
        if not scores.get("overall"):
            warnings.append("Spouse IELTS overall score missing (english_only requires IELTS 6+ all bands)")

    score = 0.7 if warnings else 1.0
    return score, warnings


def _score_preferences(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    prefs = p.get("preferences") or {}
    mode = prefs.get("search_mode")
    if not mode:
        return 0.0, ["Missing: Search mode (Specific / Top 3 / Custom / Top 5)"]
    if mode == "specific" and not prefs.get("specific_country"):
        return 0.5, ["Missing: Specific country selection"]
    if mode == "custom":
        cc = prefs.get("custom_countries") or []
        if len(cc) < 2:
            return 0.5, [f"Custom mode needs at least 2 countries (you picked {len(cc)})"]
    return 1.0, []


def _score_additional(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    af = p.get("additional_factors") or {}
    # This is bonus — even 1 declared factor gets full marks
    if any(_has(v) for v in af.values()) or af.get("criminal_record") is False:
        return 1.0, []
    return 0.5, ["Tip: Declare additional factors (job offer, relatives in target country, etc.) for accurate scoring"]


def compute_completeness(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Returns: {score:int 0-100, sections:[{key,label,weight,score,warnings}], blockers:[], warnings:[]}.

    A `blocker` is something that prevents the assessment from running (e.g., no marital status).
    A `warning` is a hint that the analysis quality may be degraded.
    """
    section_funcs = {
        "personal": _score_personal,
        "professional": _score_professional,
        "education": _score_education,
        "language": _score_language,
        "marital": _score_marital,
        "spouse": _score_spouse,
        "preferences": _score_preferences,
        "additional": _score_additional,
    }

    sections_out = []
    total_weighted = 0.0
    total_weight = 0.0
    all_warnings: List[str] = []
    blockers: List[str] = []

    for key, label, weight in SECTIONS:
        fn = section_funcs[key]
        s, ws = fn(profile)
        sections_out.append({
            "key": key,
            "label": label,
            "weight": weight,
            "score": round(s * 100),
            "warnings": ws,
        })
        total_weighted += s * weight
        total_weight += weight
        # Categorise warnings
        for w in ws:
            if "REQUIRED" in w or "CRITICAL" in w:
                blockers.append(f"[{label}] {w}")
            else:
                all_warnings.append(f"[{label}] {w}")

    overall = round((total_weighted / total_weight) * 100) if total_weight else 0
    return {
        "score": overall,
        "ready_for_assessment": len(blockers) == 0 and overall >= 40,
        "sections": sections_out,
        "blockers": blockers,
        "warnings": all_warnings,
    }
