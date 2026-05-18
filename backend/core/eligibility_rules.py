"""Phase 6.3 — Custom Rules Engine (deterministic).

Pure-Python rule modules for the Eligibility Analysis. These run FIRST (before Claude AI)
to produce deterministic, verifiable calculations:

  • PointsCalculator   — applies country points_system to a profile
  • EligibilityChecker — hard-requirements per visa category
  • CodeMatcher        — profession string → occupation code (fuzzy)
  • BodyIdentifier     — occupation code → skill assessment body
  • SuccessPredictor   — heuristic high/medium/low probability

Designed to be country-agnostic — drives off the seeded `country_rules` documents
so adding new countries doesn't require code changes.
"""
from typing import Dict, Any, List, Tuple, Optional

# ════════════════════════════════════════════════════════════════
# Helper utilities
# ════════════════════════════════════════════════════════════════
def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (ValueError, TypeError):
        return default


def _to_int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(v)
    except (ValueError, TypeError):
        return default


def _safe_lower(s: Any) -> str:
    return (s or "").strip().lower() if isinstance(s, str) else ""


# ════════════════════════════════════════════════════════════════
# 1. PointsCalculator
# ════════════════════════════════════════════════════════════════
def _bucket_age(age: int, ranges: Dict[str, int]) -> Tuple[str, int]:
    """Map age to age bucket label and points.
    Accepts buckets in formats: '18-24', '45+', '18-29', etc.
    """
    for label, pts in ranges.items():
        if "-" in label:
            try:
                lo_s, hi_s = label.split("-")
                lo = int(lo_s)
                hi = int(hi_s) if not hi_s.endswith("+") else 200
                if lo <= age <= hi:
                    return label, pts
            except ValueError:
                continue
        elif label.endswith("+"):
            try:
                lo = int(label.rstrip("+"))
                if age >= lo:
                    return label, pts
            except ValueError:
                continue
    return "unmatched", 0


def _bucket_experience(years: float, ranges: Dict[str, int]) -> Tuple[str, int]:
    """Map years experience to bucket label and points.
    Accepts buckets like '0-3_years', '5-8_years', '8+_years', '5_years'.
    """
    for label, pts in ranges.items():
        if "_plus" in label or "+" in label:
            try:
                lo = int("".join(c for c in label.split("_")[0] if c.isdigit()))
                if years >= lo:
                    return label, pts
            except ValueError:
                continue
        elif "-" in label:
            try:
                parts = label.split("_")[0].split("-")
                lo = int(parts[0])
                hi = int(parts[1])
                if lo <= years < hi:
                    return label, pts
            except (ValueError, IndexError):
                continue
        else:
            # Single number bucket — exact match preferred, else >=
            try:
                lo = int("".join(c for c in label.split("_")[0] if c.isdigit()))
                if years >= lo:
                    return label, pts
            except ValueError:
                continue
    return "unmatched", 0


_EDU_MAPS = {
    # Profile education code → list of synonym keys the points_system might use
    "doctorate": ["doctorate", "phd", "doctoral"],
    "master": ["masters", "master", "bachelor_masters"],
    "bachelor": ["bachelor", "bachelor_3yr", "bachelor_2yr", "bachelor_masters", "bachelor_honours"],
    "diploma": ["diploma", "diploma_level_7", "diploma_1yr"],
    "trade": ["trade_qualification", "trade", "occupational_registration_or_trade"],
    "high_school": ["high_school"],
}


def _education_points(qual: str, edu_map: Dict[str, int]) -> Tuple[str, int]:
    keys = _EDU_MAPS.get(_safe_lower(qual), [_safe_lower(qual)])
    for k in keys:
        if k in edu_map:
            return k, edu_map[k]
    return "no_match", 0


def _english_points(scores: Dict[str, Any], english_map: Dict[str, int]) -> Tuple[str, int]:
    """Pick points from the highest band the candidate qualifies for.
    Supports Australia-style 'competent_6/proficient_7/superior_8' AND
    Canada-style 'clb_9_plus/clb_8/clb_7/...' maps.
    """
    overall = _to_float(scores.get("overall"))
    listening = _to_float(scores.get("listening"))
    reading = _to_float(scores.get("reading"))
    writing = _to_float(scores.get("writing"))
    speaking = _to_float(scores.get("speaking"))
    per_band_min = min([b for b in (listening, reading, writing, speaking) if b > 0] or [0])

    # AU-style: each band must hit the threshold
    au_keys = [
        ("superior_8", 8.0, 20),
        ("proficient_7", 7.0, 10),
        ("competent_6", 6.0, 0),
    ]
    if any(k.startswith(("competent_", "proficient_", "superior_")) for k in english_map):
        for label, threshold, _ in au_keys:
            if label not in english_map:
                continue
            min_required = float(label.split("_")[-1])
            if per_band_min >= min_required and overall >= min_required:
                return label, english_map[label]
        return "below_competent", 0

    # CLB-style: map IELTS overall band → CLB approximation
    if any(k.startswith("clb_") for k in english_map):
        clb = _ielts_to_clb(overall, listening, reading, writing, speaking)
        if clb >= 9 and "clb_9_plus" in english_map:
            return "clb_9_plus", english_map["clb_9_plus"]
        if clb >= 8 and "clb_8" in english_map:
            return "clb_8", english_map["clb_8"]
        if clb >= 7 and "clb_7" in english_map:
            return "clb_7", english_map["clb_7"]
        if clb >= 6 and "clb_6" in english_map:
            return "clb_6", english_map["clb_6"]
        if "clb_5_or_less" in english_map:
            return "clb_5_or_less", english_map["clb_5_or_less"]
        return "clb_below", 0

    return "unknown_scheme", 0


def _ielts_to_clb(overall: float, l: float, r: float, w: float, s: float) -> int:
    """Approximate CLB level from IELTS bands (per IRCC published table).
    Uses the WORST of the four bands (CLB requires all-band min).
    """
    bands = [b for b in (l, r, w, s) if b > 0]
    if not bands:
        # Fallback to overall
        worst = overall
    else:
        worst = min(bands)
    if worst >= 8.0:
        return 10
    if worst >= 7.5:
        return 9
    if worst >= 7.0:
        return 9 if overall >= 7.0 else 8
    if worst >= 6.5:
        return 8 if overall >= 7.0 else 7
    if worst >= 6.0:
        return 7
    if worst >= 5.5:
        return 6
    if worst >= 5.0:
        return 5
    if worst >= 4.5:
        return 4
    return 0


def calculate_points(profile: Dict[str, Any], country: Dict[str, Any]) -> Dict[str, Any]:
    """Compute total points + per-category breakdown for the given country."""
    pts_sys = country.get("points_system") or {}
    breakdown: Dict[str, Dict[str, Any]] = {}
    total = 0

    # 1. Age
    age = _to_int((profile.get("basic_info") or {}).get("age"))
    age_pool = pts_sys.get("age") or pts_sys.get("core_human_capital_age") or {}
    if age and age_pool:
        label, pts = _bucket_age(age, age_pool)
        breakdown["age"] = {"value": age, "bucket": label, "points": pts}
        total += pts

    # 2. Education
    qual = (profile.get("education") or {}).get("highest_qualification")
    edu_pool = pts_sys.get("education") or pts_sys.get("core_education") or pts_sys.get("qualification") or {}
    if qual and edu_pool:
        label, pts = _education_points(qual, edu_pool)
        breakdown["education"] = {"value": qual, "matched_key": label, "points": pts}
        total += pts

    # 3. English
    lp = profile.get("language_proficiency") or {}
    scores = lp.get("scores") or {}
    english_pool = (pts_sys.get("english") or pts_sys.get("core_language_clb")
                    or pts_sys.get("english_proficiency") or {})
    if english_pool and lp.get("test_completed"):
        label, pts = _english_points(scores, english_pool)
        breakdown["english"] = {"overall": scores.get("overall"), "bucket": label, "points": pts}
        total += pts

    # 4. Experience
    yrs = _to_float((profile.get("professional") or {}).get("years_experience_total"))
    exp_pool = (pts_sys.get("experience_overseas") or pts_sys.get("core_canadian_experience")
                or pts_sys.get("skilled_experience_years") or pts_sys.get("experience") or {})
    if exp_pool:
        label, pts = _bucket_experience(yrs, exp_pool)
        breakdown["experience"] = {"value": yrs, "bucket": label, "points": pts}
        total += pts

    # 5. Partner / Spouse skills (Phase 6.7 — strict rule-based per AU/CA/NZ spec)
    #
    # Australia (Subclass 189/190/491) — partner_skills options:
    #   • single_or_pr_partner: +10 (single applicant OR spouse is AU PR/citizen)
    #   • skilled_partner:     +10 (spouse <45 + competent English + positive skill assessment + applicant on visa)
    #   • competent_english_only: +5 (spouse has IELTS 6+ overall but no skill assessment)
    #   • non_contributing:     0
    #
    # Reads from the NEW Phase 6.7 structure (profile.spouse) when available,
    # falls back to the legacy projection (profile.family.spouse_*) otherwise.
    partner_pool = pts_sys.get("partner_skills") or {}
    if partner_pool:
        spouse_block = profile.get("spouse") or None
        fam = profile.get("family") or {}
        bi = profile.get("basic_info") or {}
        marital = _safe_lower(bi.get("marital_status") or profile.get("marital_status"))
        contribution_type = (
            (spouse_block.get("contribution_type") if spouse_block else None)
            or fam.get("spouse_contribution_type")
            or "not_applicable"
        )
        spouse_is_pr = bool(
            (spouse_block.get("is_australian_pr_or_citizen") if spouse_block else False)
            or fam.get("spouse_is_australian_pr_or_citizen")
        )
        spouse_is_on_visa = bool(
            (spouse_block.get("is_applicant_on_visa") if spouse_block else None)
            if spouse_block else fam.get("spouse_is_applicant_on_visa")
        )
        if spouse_block is None and not fam.get("spouse_present"):
            spouse_is_on_visa = False  # No spouse → effectively single

        # Spouse english + age — needed for skill_assessment / english_only validation
        spouse_lang = (spouse_block.get("language") if spouse_block else {}) or {}
        spouse_scores = spouse_lang.get("scores") or {}
        spouse_overall = _to_float(spouse_scores.get("overall"))
        spouse_per_band = min(
            [_to_float(spouse_scores.get(b)) for b in ("listening", "reading", "writing", "speaking") if _to_float(spouse_scores.get(b)) > 0]
            or [spouse_overall]
        )
        spouse_age = _to_int((spouse_block.get("personal") or {}).get("age") if spouse_block else 0)
        spouse_competent_english = spouse_overall >= 6.0 and (spouse_per_band == 0 or spouse_per_band >= 6.0)

        spouse_pts = 0
        spouse_key = ""
        spouse_note = None

        # OPTION E: Single / divorced / widowed / separated → applicant is treated as single
        is_single_status = marital in ("single", "divorced", "widowed", "separated", "") or not marital
        # OPTION D: Spouse already AU PR/citizen (counts as no migrating partner)
        spouse_not_migrating = (not spouse_is_on_visa) and (spouse_block is not None or fam.get("spouse_present"))

        if (is_single_status and not spouse_block) or spouse_is_pr or contribution_type == "australian_pr_citizen" or spouse_not_migrating:
            if "single_or_pr_partner" in partner_pool:
                spouse_key = "single_or_pr_partner"
                spouse_pts = partner_pool["single_or_pr_partner"]
                if spouse_is_pr or contribution_type == "australian_pr_citizen":
                    spouse_note = "Spouse is AU PR / Citizen — counted as no migrating partner"
                elif spouse_not_migrating:
                    spouse_note = "Spouse not migrating on this visa — applicant treated as single"
                else:
                    spouse_note = "Single applicant — full points awarded"

        # OPTION A: skill_assessment — strict gate: age<45 + competent English + applicant on visa
        elif contribution_type == "skill_assessment":
            gates = []
            if spouse_age and spouse_age >= 45:
                gates.append(f"spouse age {spouse_age} ≥ 45")
            if not spouse_competent_english:
                gates.append("spouse English below competent (IELTS 6+ all bands)")
            if not spouse_is_on_visa:
                gates.append("spouse not on visa")
            if not gates and "skilled_partner" in partner_pool:
                spouse_key = "skilled_partner"
                spouse_pts = partner_pool["skilled_partner"]
                spouse_note = "Spouse meets all 4 gates: age<45, competent English, skill assessment, on visa"
            elif "competent_english_only" in partner_pool and spouse_competent_english and spouse_is_on_visa:
                # Downgrade to English-only if skill_assessment gates fail but English passes
                spouse_key = "competent_english_only"
                spouse_pts = partner_pool["competent_english_only"]
                spouse_note = f"Downgraded to English-only (gate failed: {', '.join(gates)})"
            else:
                spouse_key = "skill_assessment_blocked"
                spouse_pts = 0
                spouse_note = f"Skill-assessment partner points blocked: {', '.join(gates) or 'no partner pool key'}"

        # OPTION B: english_only — needs competent English + applicant on visa
        elif contribution_type == "english_only":
            if spouse_competent_english and spouse_is_on_visa and "competent_english_only" in partner_pool:
                spouse_key = "competent_english_only"
                spouse_pts = partner_pool["competent_english_only"]
                spouse_note = "Spouse has competent English (IELTS 6+ all bands)"
            else:
                spouse_key = "english_only_blocked"
                spouse_pts = 0
                if not spouse_competent_english:
                    spouse_note = "English-only points blocked: spouse English below IELTS 6 (per-band)"
                elif not spouse_is_on_visa:
                    spouse_note = "English-only points blocked: spouse not on visa"

        # OPTION C: non_contributing — explicitly 0
        elif contribution_type == "non_contributing":
            spouse_key = "non_contributing"
            spouse_pts = 0
            spouse_note = "Spouse will be on visa but is not contributing to points"

        # OPTION E variant: not_applicable / unknown
        else:
            spouse_key = "not_applicable"
            spouse_pts = 0
            spouse_note = "No spouse contribution declared"

        if spouse_pts or spouse_note:
            breakdown["partner"] = {
                "contribution_type": contribution_type,
                "marital_status": marital or "single",
                "matched_key": spouse_key,
                "points": spouse_pts,
                "spouse_age": spouse_age or None,
                "spouse_english_overall": spouse_overall or None,
                "spouse_competent_english": spouse_competent_english,
                "spouse_on_visa": spouse_is_on_visa,
                "note": spouse_note,
            }
            total += spouse_pts

    # 6. Job offer / relative in country (additional CRS-style)
    af = profile.get("additional_factors") or {}
    if af.get("has_job_offer") and pts_sys.get("additional_job_offer_other"):
        pts = pts_sys["additional_job_offer_other"]
        breakdown["job_offer"] = {"value": True, "points": pts}
        total += pts
    if af.get("has_relative_in_target_country") and pts_sys.get("additional_sibling_in_canada"):
        pts = pts_sys["additional_sibling_in_canada"]
        breakdown["sibling_in_country"] = {"value": True, "points": pts}
        total += pts

    return {"total": total, "breakdown": breakdown}


# ════════════════════════════════════════════════════════════════
# 2. EligibilityChecker
# ════════════════════════════════════════════════════════════════
def check_eligibility(profile: Dict[str, Any], visa: Dict[str, Any], total_points: int) -> Dict[str, Any]:
    """Return eligibility verdict + per-criterion reasons for a single visa category."""
    e = visa.get("eligibility") or {}
    reasons: List[str] = []
    failures: List[str] = []
    warnings: List[str] = []

    age = _to_int((profile.get("basic_info") or {}).get("age"))
    if age:
        age_min = _to_int(e.get("age_min"), 0)
        age_max = _to_int(e.get("age_max"), 999)
        if age < age_min:
            failures.append(f"Age {age} below minimum {age_min}")
        elif age > age_max:
            failures.append(f"Age {age} exceeds maximum {age_max}")
        else:
            reasons.append(f"Age {age} within range ({age_min}–{age_max})")

    # Points
    pts_min = _to_int(e.get("points_minimum"), 0)
    if pts_min > 0:
        if total_points < pts_min:
            failures.append(f"Points {total_points} below required {pts_min}")
        else:
            reasons.append(f"Points {total_points} ≥ required {pts_min}")

    # Experience
    yrs = _to_float((profile.get("professional") or {}).get("years_experience_total"))
    exp_min = _to_float(e.get("experience_minimum_years"), 0)
    if exp_min > 0:
        if yrs < exp_min:
            failures.append(f"Experience {yrs}y below required {exp_min}y")
        else:
            reasons.append(f"Experience {yrs}y ≥ {exp_min}y")

    # Education
    edu_required = _safe_lower(e.get("education_minimum"))
    edu_order = ["high_school", "trade_qualification", "diploma", "bachelor", "master", "doctorate"]
    edu_synonyms = {"trade": "trade_qualification", "trade_qualification": "trade_qualification"}
    qual = _safe_lower((profile.get("education") or {}).get("highest_qualification"))
    qual = edu_synonyms.get(qual, qual)
    edu_required = edu_synonyms.get(edu_required, edu_required)
    if edu_required and qual:
        try:
            if edu_order.index(qual) < edu_order.index(edu_required):
                failures.append(f"Education '{qual}' below required '{edu_required}'")
            else:
                reasons.append(f"Education '{qual}' meets required '{edu_required}'")
        except ValueError:
            warnings.append(f"Couldn't compare education levels: {qual} vs {edu_required}")

    # Language
    lr = e.get("language_requirement") or {}
    lp = profile.get("language_proficiency") or {}
    scores = lp.get("scores") or {}
    if lp.get("test_completed") and scores.get("overall"):
        overall = _to_float(scores.get("overall"))
        per_band_min = min([_to_float(scores.get(b)) for b in ("listening", "reading", "writing", "speaking") if _to_float(scores.get(b)) > 0] or [overall])
        req_overall = _to_float(lr.get("ielts_overall"))
        req_per_band = _to_float(lr.get("ielts_per_band"))
        if req_overall > 0 and overall < req_overall:
            failures.append(f"IELTS overall {overall} below required {req_overall}")
        elif req_per_band > 0 and per_band_min < req_per_band:
            failures.append(f"IELTS per-band {per_band_min} below required {req_per_band}")
        elif req_overall > 0:
            reasons.append(f"IELTS overall {overall} ≥ {req_overall}")
    elif lr.get("ielts_overall"):
        warnings.append(f"English test not completed — required IELTS {lr.get('ielts_overall')}")

    # Sponsorship / state nomination — soft (warning, not failure)
    if e.get("sponsorship_required"):
        warnings.append("Employer sponsorship required")
    if e.get("state_nomination_required"):
        warnings.append("State / Provincial nomination required")

    if failures:
        verdict = "ineligible"
    elif warnings and not reasons:
        verdict = "marginal"
    elif warnings:
        verdict = "marginal"
    else:
        verdict = "eligible"

    return {"verdict": verdict, "reasons": reasons, "failures": failures, "warnings": warnings}


# ════════════════════════════════════════════════════════════════
# 3. CodeMatcher
# ════════════════════════════════════════════════════════════════
def _tokenize(s: str) -> set:
    return {t for t in _safe_lower(s).replace("/", " ").replace("-", " ").replace(",", " ").split() if len(t) > 2}


def match_occupation_code(profile: Dict[str, Any], country: Dict[str, Any]) -> Dict[str, Any]:
    """Returns primary occupation match + up to 3 alternatives with confidence scores."""
    prof = profile.get("professional") or {}
    query = " ".join(filter(None, [prof.get("current_profession"), prof.get("designation"), prof.get("industry")]))
    query_tokens = _tokenize(query)
    if not query_tokens:
        return {"primary": None, "alternatives": [], "reason": "No profession/designation in profile"}

    candidates = []
    for occ in (country.get("occupation_codes") or []):
        title_tokens = _tokenize(occ.get("title", ""))
        alt_tokens = set()
        for t in (occ.get("alternative_titles") or []):
            alt_tokens.update(_tokenize(t))
        group_tokens = _tokenize(occ.get("group", ""))
        all_tokens = title_tokens | alt_tokens | group_tokens
        if not all_tokens:
            continue
        overlap = query_tokens & all_tokens
        if not overlap:
            continue
        # Confidence = overlap size / max(query_tokens, all_tokens)
        confidence = len(overlap) / max(len(query_tokens), 1)
        candidates.append({
            "code": occ.get("code"),
            "title": occ.get("title"),
            "group": occ.get("group"),
            "assessing_body": occ.get("assessing_body"),
            "pathway": occ.get("pathway"),
            "eligible_visas": occ.get("eligible_visas") or [],
            "confidence": round(confidence, 2),
            "match_reason": f"Matched on: {', '.join(sorted(overlap))}",
        })

    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    primary = candidates[0] if candidates else None
    return {
        "primary": primary,
        "alternatives": candidates[1:4],
        "reason": "AI-augmented review recommended" if primary and primary["confidence"] < 0.5 else "Strong match",
    }


# ════════════════════════════════════════════════════════════════
# 4. BodyIdentifier
# ════════════════════════════════════════════════════════════════
def identify_skill_body(occ_code: Optional[str], country: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not occ_code:
        return None
    for body in (country.get("skill_assessment_bodies") or []):
        assesses = body.get("assesses_occupations") or []
        if occ_code in assesses or "all_education" in assesses:
            return {
                "body_id": body.get("body_id"),
                "name": body.get("name"),
                "full_name": body.get("full_name"),
                "website": body.get("website"),
                "assessment_fee_inr": body.get("assessment_fee_inr"),
                "processing_time_weeks": body.get("processing_time_weeks"),
                "documents_required": body.get("documents_required") or [],
                "criteria_general": body.get("criteria_general") or {},
            }
    return None


# ════════════════════════════════════════════════════════════════
# 5. SuccessPredictor
# ════════════════════════════════════════════════════════════════
def predict_success(
    profile: Dict[str, Any],
    points_total: int,
    points_required: int,
    eligibility_verdict: str,
    occupation_confidence: float,
    has_body_match: bool,
) -> Dict[str, Any]:
    """Heuristic success probability: high/medium/low + numeric score 0–100."""
    score = 50
    factors_positive: List[str] = []
    factors_negative: List[str] = []

    # Points buffer
    if points_required > 0:
        buffer = points_total - points_required
        if buffer >= 15:
            score += 20; factors_positive.append(f"Strong points buffer ({buffer} above minimum)")
        elif buffer >= 5:
            score += 10; factors_positive.append(f"Comfortable points buffer ({buffer} above)")
        elif buffer >= 0:
            score += 5; factors_positive.append(f"Just meets points ({points_total}/{points_required})")
        else:
            score -= 20; factors_negative.append(f"Points shortfall by {-buffer}")
    else:
        # Points not required (e.g. employer sponsorship) — neutral
        factors_positive.append("Visa doesn't require points test")
        score += 5

    # Eligibility verdict
    if eligibility_verdict == "eligible":
        score += 15; factors_positive.append("All hard requirements met")
    elif eligibility_verdict == "marginal":
        factors_negative.append("Marginal eligibility — verify sponsorship/state nomination")
    elif eligibility_verdict == "ineligible":
        score -= 30; factors_negative.append("Fails one or more hard requirements")

    # Occupation match
    if occupation_confidence >= 0.7:
        score += 10; factors_positive.append("Strong occupation code match")
    elif occupation_confidence >= 0.4:
        score += 5; factors_positive.append("Moderate occupation match")
    else:
        factors_negative.append("Weak occupation match — manual verification recommended")

    # Body match
    if has_body_match:
        score += 5; factors_positive.append("Skill assessment body identified")
    else:
        factors_negative.append("No clear skill assessment body — may need broader research")

    # Language (if test completed and overall >= 7)
    lp = profile.get("language_proficiency") or {}
    if lp.get("test_completed"):
        overall = _to_float((lp.get("scores") or {}).get("overall"))
        if overall >= 8:
            score += 10; factors_positive.append(f"Superior English ({overall})")
        elif overall >= 7:
            score += 5; factors_positive.append(f"Proficient English ({overall})")
    else:
        factors_negative.append("English test not completed yet")

    # Finances
    fin = profile.get("finances") or {}
    if fin.get("able_to_show_funds"):
        score += 5; factors_positive.append("Proof of funds available")

    # Additional factors
    af = profile.get("additional_factors") or {}
    if af.get("has_job_offer"):
        score += 10; factors_positive.append("Job offer in target country")
    if af.get("has_relative_in_target_country"):
        score += 5; factors_positive.append("Relative in target country (CRS bonus)")
    if af.get("criminal_record"):
        score -= 25; factors_negative.append("Criminal record — requires legal review")

    # Clamp + label
    score = max(0, min(100, score))
    if score >= 75:
        label = "high"
    elif score >= 50:
        label = "medium"
    else:
        label = "low"

    return {
        "label": label,
        "score": score,
        "factors_positive": factors_positive,
        "factors_negative": factors_negative,
    }


# ════════════════════════════════════════════════════════════════
# Aggregate per-country analysis (pure rules, no AI)
# ════════════════════════════════════════════════════════════════
def analyze_country_rules(profile: Dict[str, Any], country: Dict[str, Any]) -> Dict[str, Any]:
    """Run all 5 rule modules against a single country.
    Returns the per-country rule output ready to be enriched by Claude AI.
    """
    points = calculate_points(profile, country)

    # Match occupation code first (drives visa eligibility filtering)
    occ_match = match_occupation_code(profile, country)
    primary_occ = occ_match.get("primary")
    body = identify_skill_body(primary_occ.get("code") if primary_occ else None, country)

    # Per-visa eligibility (cross-checked against occupation's eligible_visas)
    eligible_visa_codes = set((primary_occ or {}).get("eligible_visas") or [])
    visa_results = []
    best_visa = None
    best_verdict = None
    best_points_min = 0
    for v in (country.get("visa_categories") or []):
        if not v.get("is_active", True):
            continue
        # Skip if occupation explicitly doesn't list it (but allow if occupation match is weak/none)
        if eligible_visa_codes and v.get("code") not in eligible_visa_codes:
            continue
        check = check_eligibility(profile, v, points["total"])
        visa_results.append({
            "visa_id": v.get("visa_id"),
            "code": v.get("code"),
            "name": v.get("name"),
            "type": v.get("type"),
            "pathway_type": v.get("pathway_type"),
            "processing_time": v.get("processing_time"),
            "cost": v.get("cost"),
            "points_minimum": (v.get("eligibility") or {}).get("points_minimum", 0),
            "verdict": check["verdict"],
            "reasons": check["reasons"],
            "failures": check["failures"],
            "warnings": check["warnings"],
        })
        # Rank "best" — prefer eligible, then highest points_min met
        if check["verdict"] == "eligible":
            if best_visa is None or (v.get("eligibility") or {}).get("points_minimum", 0) > best_points_min:
                best_visa = v
                best_verdict = check
                best_points_min = (v.get("eligibility") or {}).get("points_minimum", 0)

    # If no eligible, pick best marginal
    if best_visa is None:
        marginal = [r for r in visa_results if r["verdict"] == "marginal"]
        if marginal:
            best_visa_dict = next((v for v in country["visa_categories"] if v.get("code") == marginal[0]["code"]), None)
            if best_visa_dict:
                best_visa = best_visa_dict
                best_verdict = {"verdict": "marginal", "reasons": marginal[0]["reasons"], "failures": [], "warnings": marginal[0]["warnings"]}

    overall_verdict = "eligible" if best_visa and best_verdict and best_verdict.get("verdict") == "eligible" else (
        "marginal" if best_visa else "ineligible"
    )

    success = predict_success(
        profile,
        points_total=points["total"],
        points_required=best_points_min or 0,
        eligibility_verdict=overall_verdict,
        occupation_confidence=(primary_occ or {}).get("confidence", 0.0),
        has_body_match=bool(body),
    )

    return {
        "country": country.get("country"),
        "country_code": country.get("country_code"),
        "country_flag": country.get("country_flag_emoji"),
        "points": points,
        "occupation": occ_match,
        "skill_body": body,
        "visas_evaluated": visa_results,
        "recommended_visa": {
            "code": best_visa.get("code") if best_visa else None,
            "name": best_visa.get("name") if best_visa else None,
            "verdict": best_verdict.get("verdict") if best_verdict else None,
            "reasons": (best_verdict or {}).get("reasons", []),
            "warnings": (best_verdict or {}).get("warnings", []),
        } if best_visa else None,
        "overall_verdict": overall_verdict,
        "success_prediction": success,
    }
