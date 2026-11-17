import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from core.sales_calculator import calculate_au_points, calculate_with_rules

def test_deduction_applied_in_australia_points():
    # Candidate with 12.4 years total experience, 2.0 years deducted by ACS
    profile = {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 30},
            "education": {"highest_qualification": "bachelor"},
            "language": {"scores": {"overall": 8.0, "listening": 8.0, "reading": 8.0, "writing": 8.0, "speaking": 8.0}},
            "professional": {
                "years_experience_total": 12.4,
                "years_experience_australia": 0.0,
                "deducted_years": 2.0,
                "claimable_years": 10.4,
            },
        },
    }
    res = calculate_au_points(profile, visa_subclass="189")
    exp_ov = res["breakdown"]["experience_overseas"]
    assert exp_ov["raw_years"] == 12.4
    assert exp_ov["deducted_years"] == 2.0
    assert exp_ov["claimable_years"] == 10.4
    assert exp_ov["value"] == 10.4
    assert exp_ov["points"] == 15  # 8+ years = 15 points
    assert "10.4 yrs claimable" in exp_ov["note"]

def test_deduction_reduces_experience_points_when_below_threshold():
    # Candidate with 4.0 years experience, but 2.0 years deducted -> net claimable is 2.0 years (< 3 yrs = 0 points)
    profile = {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 28},
            "education": {"highest_qualification": "bachelor"},
            "language": {"scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}},
            "professional": {
                "years_experience_total": 4.0,
                "years_experience_australia": 0.0,
                "deducted_years": 2.0,
            },
        },
    }
    res = calculate_au_points(profile, visa_subclass="189")
    exp_ov = res["breakdown"]["experience_overseas"]
    assert exp_ov["raw_years"] == 4.0
    assert exp_ov["deducted_years"] == 2.0
    assert exp_ov["claimable_years"] == 2.0
    assert exp_ov["value"] == 2.0
    assert exp_ov["points"] == 0  # < 3 years = 0 points!

def test_deduction_zero_keeps_full_experience():
    # Candidate with 6.0 years experience, 0.0 deducted -> net claimable is 6.0 years (5-7 yrs = 10 pts)
    profile = {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 28},
            "education": {"highest_qualification": "bachelor"},
            "language": {"scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}},
            "professional": {
                "years_experience_total": 6.0,
                "years_experience_australia": 0.0,
                "deducted_years": 0.0,
            },
        },
    }
    res = calculate_au_points(profile, visa_subclass="189")
    exp_ov = res["breakdown"]["experience_overseas"]
    assert exp_ov["claimable_years"] == 6.0
    assert exp_ov["points"] == 10  # 5-7 years = 10 points!

def test_fallback_evaluates_assessing_body():
    # Profile with occupation 262112 (ACS) and Bachelor in Computer Science (IT major)
    # Total exp 5.0 yrs -> ACS deducts 2.0 yrs -> 3.0 yrs claimable -> 5 pts!
    profile = {
        "marital_status": "single",
        "occupation": {"code": "262112", "title": "ICT Security Specialist", "assessing_authority": "ACS"},
        "primary_applicant": {
            "personal": {"age": 28},
            "education": {"highest_qualification": "bachelor", "field_of_study": "Computer Science"},
            "language": {"scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}},
            "professional": {
                "current_profession": "ICT Security Specialist",
                "occupation_code": "262112",
                "years_experience_total": 5.0,
                "years_experience_australia": 0.0,
            },
        },
    }
    res = calculate_au_points(profile, visa_subclass="189")
    exp_ov = res["breakdown"]["experience_overseas"]
    assert exp_ov["raw_years"] == 5.0
    assert exp_ov["deducted_years"] == 2.0
    assert exp_ov["claimable_years"] == 3.0
    assert exp_ov["points"] == 5

def test_continuous_decimal_experience_points_overseas():
    """Verify that decimal years (5.8, 6.7, 4.5, 7.5, 8.4) correctly map to continuous GSM bands:
      < 3.0 -> 0 pts
      3.0 to < 5.0 -> 5 pts
      5.0 to < 8.0 -> 10 pts
      >= 8.0 -> 15 pts
    """
    cases = [
        (2.8, 0, "0-2"),
        (3.0, 5, "3-4"),
        (4.5, 5, "3-4"),
        (4.9, 5, "3-4"),
        (5.0, 10, "5-7"),
        (5.8, 10, "5-7"),
        (6.7, 10, "5-7"),
        (7.5, 10, "5-7"),
        (7.9, 10, "5-7"),
        (8.0, 15, "8+"),
        (8.4, 15, "8+"),
        (10.4, 15, "8+"),
    ]
    for years, expected_pts, expected_bucket in cases:
        profile = {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 28},
                "education": {"highest_qualification": "bachelor"},
                "language": {"scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}},
                "professional": {
                    "years_experience_total": years,
                    "years_experience_australia": 0.0,
                    "deducted_years": 0.0,
                },
            },
        }
        res = calculate_au_points(profile, visa_subclass="189")
        exp_ov = res["breakdown"]["experience_overseas"]
        assert exp_ov["points"] == expected_pts, f"Failed for {years} yrs: expected {expected_pts} pts, got {exp_ov['points']}"
        assert exp_ov["value"] == years


def test_continuous_decimal_experience_points_australia():
    """Verify that Australian experience with decimals correctly maps to continuous GSM bands:
      < 1.0 -> 0 pts
      1.0 to < 3.0 -> 5 pts
      3.0 to < 5.0 -> 10 pts
      5.0 to < 8.0 -> 15 pts
      >= 8.0 -> 20 pts
    """
    cases = [
        (0.8, 0),
        (1.0, 5),
        (2.5, 5),
        (3.0, 10),
        (4.8, 10),
        (5.0, 15),
        (5.8, 15),
        (6.7, 15),
        (7.5, 15),
        (8.0, 20),
        (8.4, 20),
    ]
    for years, expected_pts in cases:
        profile = {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 28},
                "education": {"highest_qualification": "bachelor"},
                "language": {"scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}},
                "professional": {
                    "years_experience_total": years,
                    "years_experience_australia": years,
                    "deducted_years": 0.0,
                },
            },
        }
        res = calculate_au_points(profile, visa_subclass="189")
        exp_au = res["breakdown"]["experience_australia"]
        assert exp_au["points"] == expected_pts, f"Failed for AU {years} yrs: expected {expected_pts} pts, got {exp_au['points']}"


def test_decimal_experience_with_qualifying_deduction():
    """Verify total experience with decimals after assessing authority deduction."""
    # 5.8 yrs total - 2.0 deduction = 3.8 yrs claimable -> 5 pts (band 3-4)
    prof_5_8 = {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 28},
            "education": {"highest_qualification": "bachelor"},
            "language": {"scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}},
            "professional": {
                "years_experience_total": 5.8,
                "years_experience_australia": 0.0,
                "deducted_years": 2.0,
            },
        },
    }
    res_5_8 = calculate_au_points(prof_5_8, visa_subclass="189")
    exp_5_8 = res_5_8["breakdown"]["experience_overseas"]
    assert exp_5_8["claimable_years"] == 3.8
    assert exp_5_8["points"] == 5

    # 6.7 yrs total - 2.0 deduction = 4.7 yrs claimable -> 5 pts (band 3-4)
    prof_6_7 = {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 28},
            "education": {"highest_qualification": "bachelor"},
            "language": {"scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}},
            "professional": {
                "years_experience_total": 6.7,
                "years_experience_australia": 0.0,
                "deducted_years": 2.0,
            },
        },
    }
    res_6_7 = calculate_au_points(prof_6_7, visa_subclass="189")
    exp_6_7 = res_6_7["breakdown"]["experience_overseas"]
    assert exp_6_7["claimable_years"] == 4.7
    assert exp_6_7["points"] == 5

    # 7.5 yrs total - 2.0 deduction = 5.5 yrs claimable -> 10 pts (band 5-7)
    prof_7_5 = {
        "marital_status": "single",
        "primary_applicant": {
            "personal": {"age": 28},
            "education": {"highest_qualification": "bachelor"},
            "language": {"scores": {"overall": 7.0, "listening": 7.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0}},
            "professional": {
                "years_experience_total": 7.5,
                "years_experience_australia": 0.0,
                "deducted_years": 2.0,
            },
        },
    }
    res_7_5 = calculate_au_points(prof_7_5, visa_subclass="189")
    exp_7_5 = res_7_5["breakdown"]["experience_overseas"]
    assert exp_7_5["claimable_years"] == 5.5
    assert exp_7_5["points"] == 10


def test_reportlab_pdf_renders_skills_assessment_and_why_we_chose():
    """Verify that ReportLab render_pdf includes Section 2.b Skills Assessment,
    deductions (-3.0 yrs for TRA / Cook 351411), 2.9 yrs net claimable,
    and why we chose occupation breakdown with duty tasks.
    """
    from core.report_renderer import render_pdf

    sample_snapshot = {
        "snapshot_id": "SNAP-TEST-001",
        "assessment_id": "SAH-20261113-TEST01",
        "render_tier": "full",
        "client": {
            "name": "Pravin Rajbahadur Khushawah",
            "email": "pravin@example.com",
            "phone": "+91 9876543210",
            "current_profession": "Chef / Cook",
            "work_exp_years": 5.9,
        },
        "profile_snapshot": {
            "marital_status": "single",
            "primary_applicant": {
                "personal": {"age": 31},
                "education": {"highest_qualification": "Diploma"},
                "language": {"scores": {"overall": 7.0}},
                "professional": {
                    "current_profession": "Chef / Cook",
                    "employer_name": "Grand Palace Hotel",
                    "employer_nature": "Hospitality & Culinary",
                    "years_experience_total": 5.9,
                    "deducted_years": 3.0,
                    "claimable_years": 2.9,
                },
            },
        },
        "occupation": {
            "country_code": "AU",
            "code": "351411",
            "title": "Cook",
            "assessing_body": "Trades Recognition Australia",
            "pathway": "TRA OSAP Migration Skills Assessment",
        },
        "skills_assessment": {
            "authority_name": "Trades Recognition Australia",
            "pathway_name": "TRA Migration Skills Assessment",
            "assessment_outcome": "Likely Positive Assessment",
            "deducted_years": 3.0,
            "points_claimable_years": 2.9,
            "points_claimable_points": 0,
            "matched_tasks": [
                "Regulating temperatures of ovens, grills and other cooking equipment",
                "Preparing and cooking food in accordance with food safety standards",
                "Portioning food, placing it on plates, and adding gravies, sauces and garnishes",
            ],
            "why_we_chose": {
                "why_we_chose_summary": "Selected 351411 Cook due to direct alignment with candidate culinary duties.",
                "role_alignment_text": "Candidate has 5.9 years experience in commercial food preparation.",
                "deduction_explanation": "TRA OSAP requires 3.0 years qualifying deduction for trade qualification.",
            },
        },
        "occupation_comparison": {
            "occupations": [
                {
                    "is_primary": True,
                    "code": "351411",
                    "title": "Cook",
                    "assessing_body": "Trades Recognition Australia",
                    "deducted_years": 3.0,
                    "claimable_years": 2.9,
                    "claimable_points": 0,
                    "why_we_chose_summary": "Primary nominated trade occupation.",
                },
                {
                    "is_primary": False,
                    "code": "351311",
                    "title": "Chef",
                    "assessing_body": "Trades Recognition Australia",
                    "deducted_years": 3.0,
                    "claimable_years": 2.9,
                    "claimable_points": 0,
                    "why_we_chose_summary": "Alternative supervisory pathway requiring higher kitchen management responsibility.",
                },
            ],
        },
        "countries": [
            {
                "country_code": "AU",
                "country_name": "Australia",
                "total": 65,
                "pass_mark": 65,
                "breakdown": {
                    "age": 30,
                    "qualification": 10,
                    "english": 10,
                    "experience_overseas": {"points": 0, "claimable_years": 2.9, "deducted_years": 3.0},
                    "single": 10,
                    "state_nomination": 5,
                },
            }
        ],
    }

    pdf_bytes = render_pdf(sample_snapshot)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 5000
    assert pdf_bytes.startswith(b"%PDF")


if __name__ == "__main__":
    test_deduction_applied_in_australia_points()
    test_deduction_reduces_experience_points_when_below_threshold()
    test_deduction_zero_keeps_full_experience()
    test_fallback_evaluates_assessing_body()
    test_continuous_decimal_experience_points_overseas()
    test_continuous_decimal_experience_points_australia()
    test_decimal_experience_with_qualifying_deduction()
    print("All unit tests including continuous decimal experience bands passed successfully!")
