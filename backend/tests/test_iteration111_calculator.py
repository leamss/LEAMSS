"""Phase 6 v2 Part 2 — Eligibility Calculator tests (deterministic, no LLM)."""
import pytest
from core.sales_calculator import (
    calculate_au_points,
    calculate_ca_crs,
    calculate_nz_smc,
    calculate,
)


def _base_primary(**overrides):
    base = {
        "personal": {"age": 30},
        "professional": {"current_profession": "Software Engineer", "years_experience_total": 6, "years_experience_australia": 0},
        "education": {"highest_qualification": "bachelor"},
        "language": {"test_completed": True, "scores": {
            "overall": 7.5, "listening": 7.5, "reading": 7.0, "writing": 7.0, "speaking": 7.5}},
        "au_extras": {},
        "ca_extras": {},
        "nz_extras": {},
    }
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════════
# AUSTRALIA — Age points (from official table)
# ═══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("age,expected_pts,bucket", [
    (17, 0, "below_18"),
    (18, 25, "18-24"),
    (24, 25, "18-24"),
    (25, 30, "25-32"),
    (32, 30, "25-32"),
    (33, 25, "33-39"),
    (39, 25, "33-39"),
    (40, 15, "40-44"),
    (44, 15, "40-44"),
    (45, 0, "45+_INELIGIBLE"),
    (50, 0, "45+_INELIGIBLE"),
])
def test_au_age_points(age, expected_pts, bucket):
    profile = {"marital_status": "single", "primary_applicant": _base_primary(personal={"age": age})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["age"]["points"] == expected_pts
    assert r["breakdown"]["age"]["bucket"] == bucket


# ═══════════════════════════════════════════════════════════════
# AUSTRALIA — English points (Competent 0, Proficient 10, Superior 20)
# ═══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("min_band,expected_pts,bucket", [
    (5.5, 0, "below_competent"),
    (6.0, 0, "competent_IELTS_6"),
    (6.5, 0, "competent_IELTS_6"),
    (7.0, 10, "proficient_IELTS_7"),
    (7.5, 10, "proficient_IELTS_7"),
    (8.0, 20, "superior_IELTS_8"),
    (9.0, 20, "superior_IELTS_8"),
])
def test_au_english_points(min_band, expected_pts, bucket):
    profile = {
        "marital_status": "single",
        "primary_applicant": _base_primary(language={
            "test_completed": True,
            "scores": {"overall": min_band, "listening": min_band, "reading": min_band, "writing": min_band, "speaking": min_band},
        }),
    }
    r = calculate_au_points(profile)
    assert r["breakdown"]["english"]["points"] == expected_pts
    assert r["breakdown"]["english"]["bucket"] == bucket


# ═══════════════════════════════════════════════════════════════
# AUSTRALIA — Experience overseas (5-7 → 10 pts)
# ═══════════════════════════════════════════════════════════════
def test_au_experience_overseas_3_years():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(professional={"years_experience_total": 3, "years_experience_australia": 0})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["experience_overseas"]["points"] == 5


def test_au_experience_overseas_5_years():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(professional={"years_experience_total": 5, "years_experience_australia": 0})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["experience_overseas"]["points"] == 10


def test_au_experience_overseas_8_years():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(professional={"years_experience_total": 8, "years_experience_australia": 0})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["experience_overseas"]["points"] == 15


def test_au_experience_australia_5_years():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(professional={"years_experience_total": 5, "years_experience_australia": 5})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["experience_australia"]["points"] == 15
    assert r["breakdown"]["experience_overseas"]["points"] == 0


# ═══════════════════════════════════════════════════════════════
# AUSTRALIA — Education
# ═══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("qual,expected_pts", [
    ("doctorate", 20),
    ("master", 15),
    ("bachelor", 15),
    ("diploma", 10),
    ("trade", 10),
    ("high_school", 0),
])
def test_au_education_points(qual, expected_pts):
    profile = {"marital_status": "single", "primary_applicant": _base_primary(education={"highest_qualification": qual})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["education"]["points"] == expected_pts


# ═══════════════════════════════════════════════════════════════
# AUSTRALIA — Partner skills (critical, was broken before)
# ═══════════════════════════════════════════════════════════════
def test_au_partner_single_gets_10():
    profile = {"marital_status": "single", "primary_applicant": _base_primary()}
    r = calculate_au_points(profile)
    assert r["breakdown"]["partner"]["points"] == 10
    assert r["breakdown"]["partner"]["matched_key"] == "single_or_pr_partner"


def test_au_partner_divorced_with_stale_spouse_still_10():
    """The fix from iteration 109 — marital is authoritative."""
    profile = {
        "marital_status": "divorced",
        "primary_applicant": _base_primary(),
        "spouse": {"contribution_type": "skill_assessment", "personal": {"age": 30}, "language": {"scores": {"overall": 7}}},
    }
    r = calculate_au_points(profile)
    assert r["breakdown"]["partner"]["points"] == 10
    assert r["breakdown"]["partner"]["matched_key"] == "single_or_pr_partner"


def test_au_partner_skill_assessment_all_gates_pass_gets_10():
    profile = {
        "marital_status": "married",
        "primary_applicant": _base_primary(),
        "spouse": {
            "is_applicant_on_visa": True,
            "contribution_type": "skill_assessment",
            "personal": {"age": 30},
            "language": {"scores": {"overall": 7.0, "listening": 7, "reading": 7, "writing": 7, "speaking": 7}},
        },
    }
    r = calculate_au_points(profile)
    assert r["breakdown"]["partner"]["points"] == 10
    assert r["breakdown"]["partner"]["matched_key"] == "skilled_partner"


def test_au_partner_skill_assessment_age_47_downgrades_to_5():
    profile = {
        "marital_status": "married",
        "primary_applicant": _base_primary(),
        "spouse": {
            "is_applicant_on_visa": True,
            "contribution_type": "skill_assessment",
            "personal": {"age": 47},
            "language": {"scores": {"overall": 7.0, "listening": 7, "reading": 7, "writing": 7, "speaking": 7}},
        },
    }
    r = calculate_au_points(profile)
    assert r["breakdown"]["partner"]["points"] == 5  # downgraded
    assert r["breakdown"]["partner"]["matched_key"] == "competent_english_only"


def test_au_partner_english_only_competent_gets_5():
    profile = {
        "marital_status": "married",
        "primary_applicant": _base_primary(),
        "spouse": {
            "is_applicant_on_visa": True,
            "contribution_type": "english_only",
            "language": {"scores": {"overall": 6.5, "listening": 6.5, "reading": 6.5, "writing": 6, "speaking": 6.5}},
        },
    }
    r = calculate_au_points(profile)
    assert r["breakdown"]["partner"]["points"] == 5


def test_au_partner_non_contributing_zero():
    profile = {
        "marital_status": "married",
        "primary_applicant": _base_primary(),
        "spouse": {"is_applicant_on_visa": True, "contribution_type": "non_contributing"},
    }
    r = calculate_au_points(profile)
    assert r["breakdown"]["partner"]["points"] == 0


def test_au_partner_au_pr_spouse_gets_10():
    profile = {
        "marital_status": "married",
        "primary_applicant": _base_primary(),
        "spouse": {"is_australian_pr_or_citizen": True, "is_applicant_on_visa": False, "contribution_type": "australian_pr_citizen"},
    }
    r = calculate_au_points(profile)
    assert r["breakdown"]["partner"]["points"] == 10


# ═══════════════════════════════════════════════════════════════
# AUSTRALIA — Bonus Points (Australian Study, STEM, PY, NAATI, Regional)
# ═══════════════════════════════════════════════════════════════
def test_au_australian_study_adds_5():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(au_extras={"australian_study_2_years": True})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["australian_study"]["points"] == 5


def test_au_specialist_stem_adds_10():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(au_extras={"specialist_education_stem_au": True})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["specialist_education"]["points"] == 10


def test_au_professional_year_adds_5():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(au_extras={"professional_year_completed": True})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["professional_year"]["points"] == 5


def test_au_naati_adds_5():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(au_extras={"naati_accredited": True})}
    r = calculate_au_points(profile)
    assert r["breakdown"]["naati"]["points"] == 5


def test_au_state_nomination_190_adds_5():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(au_extras={"state_nominated": True})}
    r = calculate_au_points(profile, visa_subclass="190")
    assert r["breakdown"]["state_nomination"]["points"] == 5


def test_au_state_nomination_491_adds_15():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(au_extras={"state_nominated": True})}
    r = calculate_au_points(profile, visa_subclass="491")
    assert r["breakdown"]["state_nomination"]["points"] == 15


def test_au_state_nomination_189_no_bonus():
    """189 is independent — no state nomination points even if checked."""
    profile = {"marital_status": "single", "primary_applicant": _base_primary(au_extras={"state_nominated": True})}
    r = calculate_au_points(profile, visa_subclass="189")
    assert "state_nomination" not in r["breakdown"]


# ═══════════════════════════════════════════════════════════════
# AUSTRALIA — Full scenario test
# ═══════════════════════════════════════════════════════════════
def test_au_full_scenario_software_engineer_subclass_189():
    """Single, 30 years, Bachelor, IELTS 7.5 all bands, 6 years overseas exp."""
    profile = {
        "marital_status": "single",
        "primary_applicant": _base_primary(),
    }
    r = calculate_au_points(profile, visa_subclass="189")
    # 30 (age 30) + 10 (IELTS 7 proficient) + 10 (5-7 yr overseas) + 15 (Bachelor) + 10 (single partner) = 75
    assert r["total"] == 75
    assert r["visa_eligibility"]["189"]["eligible"] is True


def test_au_age_45_ineligible_all_visas():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(personal={"age": 45})}
    r = calculate_au_points(profile)
    assert all(not v["eligible"] for v in r["visa_eligibility"].values())


# ═══════════════════════════════════════════════════════════════
# CANADA CRS — Smoke test
# ═══════════════════════════════════════════════════════════════
def test_ca_crs_basic_single():
    profile = {"marital_status": "single", "primary_applicant": _base_primary()}
    r = calculate_ca_crs(profile, with_spouse=False)
    # Age 30 + Bachelor + IELTS 7 (CLB 9 per band)
    assert r["total"] > 200
    assert r["country_code"] == "CA"


def test_ca_pnp_gives_600_points():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(ca_extras={"provincial_nomination": True})}
    r = calculate_ca_crs(profile, with_spouse=False)
    assert r["breakdown"]["ca_provincial_nomination"]["points"] == 600


def test_ca_french_clb_7_gives_50_pts():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(ca_extras={"french_proficiency_clb_7": True})}
    r = calculate_ca_crs(profile, with_spouse=False)
    assert r["breakdown"]["ca_french"]["points"] == 50


# ═══════════════════════════════════════════════════════════════
# NEW ZEALAND SMC — Smoke test
# ═══════════════════════════════════════════════════════════════
def test_nz_smc_basic_single():
    profile = {"marital_status": "single", "primary_applicant": _base_primary()}
    r = calculate_nz_smc(profile)
    # Age 30 (25) + Bachelor (40) + 6 yrs exp (15) = 80
    assert r["total"] == 80


def test_nz_smc_job_offer_adds_30():
    profile = {"marital_status": "single", "primary_applicant": _base_primary(nz_extras={"nz_job_offer": True})}
    r = calculate_nz_smc(profile)
    assert r["breakdown"]["nz_job_offer"]["points"] == 30


def test_nz_smc_partner_master_adds_20():
    profile = {
        "marital_status": "married",
        "primary_applicant": _base_primary(),
        "spouse": {"is_applicant_on_visa": True, "education": {"highest_qualification": "master"}},
    }
    r = calculate_nz_smc(profile)
    assert r["breakdown"]["nz_partner_qual"]["points"] == 20


# ═══════════════════════════════════════════════════════════════
# Master dispatcher
# ═══════════════════════════════════════════════════════════════
def test_calculate_dispatcher_au():
    profile = {"marital_status": "single", "primary_applicant": _base_primary()}
    r = calculate(profile, "AU", "189")
    assert r["country_code"] == "AU"


def test_calculate_dispatcher_ca():
    profile = {"marital_status": "single", "primary_applicant": _base_primary()}
    r = calculate(profile, "CA")
    assert r["country_code"] == "CA"


def test_calculate_dispatcher_nz():
    profile = {"marital_status": "single", "primary_applicant": _base_primary()}
    r = calculate(profile, "NZ")
    assert r["country_code"] == "NZ"


def test_calculate_dispatcher_unknown_country_returns_error():
    profile = {"marital_status": "single", "primary_applicant": _base_primary()}
    r = calculate(profile, "XX")
    assert "error" in r
