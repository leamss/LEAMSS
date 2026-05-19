"""Regression tests for Phase 6.7 critical bug fix — marital_status is authoritative.

User reported: "I selected Single at start but then later added child to check.
So did not give 10 points, considered 5 and self added spouse information."

Root cause: when marital_status was changed to single but spouse data remained in DB,
the rules engine still applied spouse-based partner points.

Fix:
  1. Backend ProfileCreate/ProfilePatch now calls _strip_spouse_if_single() to wipe
     stale spouse data when marital_status is not married/de_facto.
  2. eligibility_rules.calculate_points() now treats marital_status as the SINGLE
     SOURCE OF TRUTH — ignores spouse_block entirely when marital is not married/de_facto.
"""
import pytest
from core.eligibility_rules import calculate_points, match_occupation_code, identify_skill_body


@pytest.fixture
def au_country():
    """Minimal AU rules for testing — points_system + partner_skills."""
    return {
        "country_code": "AU",
        "points_system": {
            "age": {"40-44": 15},
            "english": {"superior_8": 20},
            "experience_overseas": {"5-8_years": 10},
            "education": {"bachelor_masters": 15},
            "partner_skills": {
                "competent_english_only": 5,
                "skilled_partner": 10,
                "single_or_pr_partner": 10,
            },
        },
        "occupation_codes": [
            {"code": "141311", "title": "Hotel or Motel Manager", "group": "Accommodation and Hospitality Managers",
             "assessing_body": "VETASSESS", "pathway": "MLTSSL", "eligible_visas": ["189", "190"],
             "alternative_titles": ["Operations Head (Hotel)", "Hotel Manager"]},
            {"code": "132111", "title": "Corporate General Manager", "group": "Chief Executives",
             "assessing_body": "VETASSESS", "pathway": "STSOL", "eligible_visas": ["190", "491"],
             "alternative_titles": ["Operations Head", "Hospitality Operations Director"]},
            {"code": "225113", "title": "Marketing Specialist", "group": "Advertising and Marketing Professionals",
             "assessing_body": "VETASSESS", "pathway": "STSOL", "eligible_visas": ["190", "491"],
             "alternative_titles": ["Digital Marketing Manager", "Brand Manager"]},
        ],
        "skill_assessment_bodies": [
            {"body_id": "vetassess", "name": "VETASSESS", "full_name": "Vocational Education and Training Assessment Services",
             "assesses_occupations": ["141311", "132111", "225113"],
             "assessment_fee_inr": 70000,
             "fee_native": {"currency": "AUD", "standard": 1225, "priority": 2710,
                            "label": "AUD 1,225 (standard) / AUD 2,710 (priority)"}}
        ],
    }


def _base_profile(marital="single", age=40, profession="Operations Head"):
    return {
        "marital_status": marital,
        "primary_applicant": {
            "personal": {"age": age},
            "professional": {
                "current_profession": profession,
                "designation": "Hotel Operations Manager",
                "industry": "Hospitality",
                "years_experience_total": 7,
            },
            "education": {"highest_qualification": "master"},
            "language": {"test_completed": True, "scores": {
                "overall": 8.5, "listening": 8.5, "reading": 8.5, "writing": 8.0, "speaking": 8.5}},
        },
        "basic_info": {"age": age, "marital_status": marital},
        "professional": {"current_profession": profession, "designation": "Hotel Operations Manager",
                         "industry": "Hospitality", "years_experience_total": 7},
        "education": {"highest_qualification": "master"},
        "language_proficiency": {"test_completed": True, "scores": {
            "overall": 8.5, "listening": 8.5, "reading": 8.5, "writing": 8.0, "speaking": 8.5}},
        "family": {"spouse_present": False},
    }


# ════════════════════════════════════════════════════════════════
# THE CRITICAL BUG — single + stale spouse_block must STILL give +10
# ════════════════════════════════════════════════════════════════
def test_single_with_stale_spouse_block_still_gives_plus_10(au_country):
    """User reported bug: single marital_status but spouse data leftover in DB
    was giving +5 (competent_english_only). After fix: must give +10."""
    profile = _base_profile(marital="single")
    # EVIL: stale spouse data in profile dict (simulating un-cleaned old profile)
    profile["spouse"] = {
        "is_applicant_on_visa": True,
        "contribution_type": "english_only",
        "personal": {"age": 30},
        "language": {"test_completed": True, "scores": {
            "overall": 6.5, "listening": 6.5, "reading": 6.5, "writing": 6.0, "speaking": 6.5}},
    }

    pts = calculate_points(profile, au_country)
    partner = pts["breakdown"].get("partner") or {}

    # CRITICAL ASSERTIONS
    assert partner["matched_key"] == "single_or_pr_partner", (
        f"Single applicant must match single_or_pr_partner, got '{partner.get('matched_key')}'"
    )
    assert partner["points"] == 10, (
        f"Single applicant must get +10 partner points, got {partner.get('points')}"
    )
    assert partner["marital_status"] == "single"


def test_single_clean_profile_gives_plus_10(au_country):
    profile = _base_profile(marital="single")
    profile["spouse"] = None
    pts = calculate_points(profile, au_country)
    assert pts["breakdown"]["partner"]["points"] == 10
    assert pts["breakdown"]["partner"]["matched_key"] == "single_or_pr_partner"


def test_divorced_with_stale_spouse_gives_plus_10(au_country):
    profile = _base_profile(marital="divorced")
    profile["spouse"] = {"contribution_type": "skill_assessment", "personal": {"age": 25}}
    pts = calculate_points(profile, au_country)
    assert pts["breakdown"]["partner"]["points"] == 10
    assert pts["breakdown"]["partner"]["matched_key"] == "single_or_pr_partner"


def test_widowed_with_stale_spouse_gives_plus_10(au_country):
    profile = _base_profile(marital="widowed")
    profile["spouse"] = {"contribution_type": "australian_pr_citizen"}
    pts = calculate_points(profile, au_country)
    assert pts["breakdown"]["partner"]["points"] == 10
    assert pts["breakdown"]["partner"]["matched_key"] == "single_or_pr_partner"


def test_separated_with_stale_spouse_gives_plus_10(au_country):
    profile = _base_profile(marital="separated")
    profile["spouse"] = {"contribution_type": "english_only", "language": {"scores": {"overall": 7.0}}}
    pts = calculate_points(profile, au_country)
    assert pts["breakdown"]["partner"]["points"] == 10


# ════════════════════════════════════════════════════════════════
# Married/de_facto still works correctly (no regression)
# ════════════════════════════════════════════════════════════════
def test_married_with_skill_assessment_spouse_still_gives_plus_10(au_country):
    profile = _base_profile(marital="married")
    profile["spouse"] = {
        "is_applicant_on_visa": True,
        "contribution_type": "skill_assessment",
        "personal": {"age": 30},
        "language": {"scores": {"overall": 7.0, "listening": 7, "reading": 7, "writing": 7, "speaking": 7}},
    }
    pts = calculate_points(profile, au_country)
    partner = pts["breakdown"]["partner"]
    assert partner["matched_key"] == "skilled_partner"
    assert partner["points"] == 10


def test_married_english_only_gives_plus_5(au_country):
    profile = _base_profile(marital="married")
    profile["spouse"] = {
        "is_applicant_on_visa": True,
        "contribution_type": "english_only",
        "language": {"scores": {"overall": 6.5, "listening": 6.5, "reading": 6.5, "writing": 6, "speaking": 6.5}},
    }
    pts = calculate_points(profile, au_country)
    partner = pts["breakdown"]["partner"]
    assert partner["matched_key"] == "competent_english_only"
    assert partner["points"] == 5


def test_married_non_contributing_gives_zero(au_country):
    profile = _base_profile(marital="married")
    profile["spouse"] = {"is_applicant_on_visa": True, "contribution_type": "non_contributing"}
    pts = calculate_points(profile, au_country)
    assert pts["breakdown"]["partner"]["points"] == 0
    assert pts["breakdown"]["partner"]["matched_key"] == "non_contributing"


# ════════════════════════════════════════════════════════════════
# Occupation matcher — Hotel Operations Manager should NOT match Construction Mgr
# ════════════════════════════════════════════════════════════════
def test_hotel_operations_manager_matches_hotel_motel_manager(au_country):
    profile = _base_profile(marital="single", profession="Operations Head")
    # Profile has industry=Hospitality, designation=Hotel Operations Manager
    occ = match_occupation_code(profile, au_country)
    primary = occ["primary"]
    assert primary is not None
    # Must be 141311 or 132111 — NOT a construction code
    assert primary["code"] in ("141311", "132111"), f"Expected hospitality code, got {primary['code']}"
    assert primary["confidence"] >= 0.5


def test_skill_body_returns_fee_native(au_country):
    body = identify_skill_body("141311", au_country)
    assert body is not None
    assert body["name"] == "VETASSESS"
    # Phase 6.7 — fee_native must be present
    assert body.get("fee_native") is not None
    assert body["fee_native"]["currency"] == "AUD"
    assert "AUD" in body["fee_native"]["label"]
