"""Phase 6 — Eligibility Knowledge Base Seed Data.

Seeds country_rules collection with comprehensive immigration data for:
  • 🇦🇺 Australia (6 visas, 8 skill bodies, 30+ ANZSCO codes, full points system)
  • 🇨🇦 Canada (4 programs, 5 ECA bodies, 30+ NOC codes, CRS system)
  • 🇳🇿 New Zealand (4 visas, 4 bodies, 20+ codes, points system)

Admin can bulk-import additional occupation codes via CSV.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List

NOW = datetime.now(timezone.utc)


def _occ(code: str, title: str, group: str, group_code: str, skill_level: int,
         body: str, pathway: str, eligible_visas: List[str], alt: List[str] = None,
         state_demand: Dict[str, str] = None) -> Dict[str, Any]:
    return {
        "code": code, "title": title, "group": group, "group_code": group_code,
        "skill_level": skill_level, "assessing_body": body, "pathway": pathway,
        "alternative_titles": alt or [], "eligible_visas": eligible_visas,
        "state_demand": state_demand or {},
    }


# ═══════════════════════════════════════════════════════════════════════
# 🇦🇺 AUSTRALIA
# ═══════════════════════════════════════════════════════════════════════
AUSTRALIA = {
    "country": "Australia",
    "country_code": "AU",
    "country_flag_emoji": "🇦🇺",
    "is_active": True,
    "priority": 1,
    "visa_categories": [
        {
            "visa_id": "au_189", "code": "189", "name": "Subclass 189",
            "type": "Skilled Independent (PR)",
            "description": "Permanent residence for skilled workers not sponsored by employer/family/state.",
            "eligibility": {
                "age_min": 18, "age_max": 44, "points_minimum": 65,
                "language_requirement": {"ielts_overall": 6.0, "ielts_per_band": 6.0, "pte_equivalent": 50, "accepts": ["IELTS", "PTE", "TOEFL"]},
                "experience_minimum_years": 0, "education_minimum": "diploma",
                "sponsorship_required": False, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 8, "max_months": 14, "average_months": 10},
            "cost": {"government_fee_inr": 250000, "average_total_inr": 500000},
            "required_skill_assessment": True, "pathway_type": "MLTSSL",
            "success_factors": ["High points score (75+)", "Strong skill assessment", "English proficiency (PTE 65+/IELTS 7+)"],
            "is_active": True,
        },
        {
            "visa_id": "au_190", "code": "190", "name": "Subclass 190",
            "type": "Skilled Nominated (PR)",
            "description": "Permanent visa requiring nomination from an Australian state/territory.",
            "eligibility": {
                "age_min": 18, "age_max": 44, "points_minimum": 65,
                "language_requirement": {"ielts_overall": 6.0, "ielts_per_band": 6.0, "pte_equivalent": 50, "accepts": ["IELTS", "PTE"]},
                "experience_minimum_years": 0, "education_minimum": "diploma",
                "sponsorship_required": False, "state_nomination_required": True,
            },
            "processing_time": {"min_months": 8, "max_months": 12, "average_months": 10},
            "cost": {"government_fee_inr": 250000, "average_total_inr": 600000},
            "required_skill_assessment": True, "pathway_type": "STSOL",
            "success_factors": ["State nomination (+5 points)", "Profession on state list", "Commitment to live in state for 2 years"],
            "is_active": True,
        },
        {
            "visa_id": "au_491", "code": "491", "name": "Subclass 491",
            "type": "Skilled Work Regional (Provisional, 5 years)",
            "description": "5-year provisional visa for regional skilled workers; pathway to PR via 191.",
            "eligibility": {
                "age_min": 18, "age_max": 44, "points_minimum": 65,
                "language_requirement": {"ielts_overall": 6.0, "ielts_per_band": 6.0, "pte_equivalent": 50, "accepts": ["IELTS", "PTE"]},
                "experience_minimum_years": 0, "education_minimum": "diploma",
                "sponsorship_required": False, "state_nomination_required": True,
            },
            "processing_time": {"min_months": 4, "max_months": 10, "average_months": 7},
            "cost": {"government_fee_inr": 250000, "average_total_inr": 550000},
            "required_skill_assessment": True, "pathway_type": "ROL",
            "success_factors": ["Regional nomination (+15 points)", "Willingness to live regional 3 years", "Lower competition"],
            "is_active": True,
        },
        {
            "visa_id": "au_482", "code": "482", "name": "Subclass 482",
            "type": "Temporary Skill Shortage (Employer-Sponsored)",
            "description": "Temporary work visa (up to 4 years) sponsored by an Australian employer.",
            "eligibility": {
                "age_min": 18, "age_max": 99, "points_minimum": 0,
                "language_requirement": {"ielts_overall": 5.0, "ielts_per_band": 5.0, "pte_equivalent": 36, "accepts": ["IELTS", "PTE"]},
                "experience_minimum_years": 2, "education_minimum": "diploma",
                "sponsorship_required": True, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 2, "max_months": 6, "average_months": 4},
            "cost": {"government_fee_inr": 200000, "average_total_inr": 450000},
            "required_skill_assessment": True, "pathway_type": "STSOL",
            "success_factors": ["Genuine job offer from approved sponsor", "Minimum 2 years experience", "Salary above TSMIT (AUD 70,000+)"],
            "is_active": True,
        },
        {
            "visa_id": "au_186", "code": "186", "name": "Subclass 186",
            "type": "Employer Nomination Scheme (PR)",
            "description": "Permanent residency via employer sponsorship.",
            "eligibility": {
                "age_min": 18, "age_max": 44, "points_minimum": 0,
                "language_requirement": {"ielts_overall": 6.0, "ielts_per_band": 6.0, "pte_equivalent": 50, "accepts": ["IELTS", "PTE"]},
                "experience_minimum_years": 3, "education_minimum": "diploma",
                "sponsorship_required": True, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 4, "max_months": 12, "average_months": 8},
            "cost": {"government_fee_inr": 350000, "average_total_inr": 700000},
            "required_skill_assessment": True, "pathway_type": "MLTSSL",
            "success_factors": ["Genuine PR-track employer", "Profession on MLTSSL", "3+ years post-qualification experience"],
            "is_active": True,
        },
        {
            "visa_id": "au_187", "code": "187", "name": "Subclass 187 (RSMS)",
            "type": "Regional Sponsored Migration (closed for new — DAMA alt.)",
            "description": "Replaced by 494 for new applicants. Still active for existing pipeline.",
            "eligibility": {
                "age_min": 18, "age_max": 44, "points_minimum": 0,
                "language_requirement": {"ielts_overall": 6.0, "ielts_per_band": 6.0, "pte_equivalent": 50, "accepts": ["IELTS", "PTE"]},
                "experience_minimum_years": 3, "education_minimum": "diploma",
                "sponsorship_required": True, "state_nomination_required": True,
            },
            "processing_time": {"min_months": 6, "max_months": 18, "average_months": 12},
            "cost": {"government_fee_inr": 350000, "average_total_inr": 700000},
            "required_skill_assessment": True, "pathway_type": "ROL",
            "success_factors": ["Regional employer sponsorship", "DAMA-approved occupation", "Long-term regional commitment"],
            "is_active": False,
        },
    ],
    "skill_assessment_bodies": [
        {
            "body_id": "acs", "name": "ACS", "full_name": "Australian Computer Society",
            "website": "https://acs.org.au",
            "assesses_occupations": ["261313", "261311", "261312", "263111", "262112", "261314", "261112", "261111", "261212"],
            "criteria_general": {"minimum_education": "Bachelor in IT or related", "relevant_work_experience": "varies by qualification match", "english_required": False},
            "documents_required": ["Bachelor's degree certificate", "Academic transcripts", "Employment reference letters (statutory declaration accepted)", "Roles & responsibilities document", "Pay slips (most recent 3 months)", "Bank statements showing salary credit", "Passport bio page"],
            "assessment_fee_inr": 50000, "processing_time_weeks": 8,
            "contact_info": {"email": "info@acs.org.au", "phone": "+61 2 9929 2900"},
        },
        {
            "body_id": "ea", "name": "EA", "full_name": "Engineers Australia",
            "website": "https://engineersaustralia.org.au",
            "assesses_occupations": ["233211", "233311", "233411", "233512", "233611", "233914", "233913", "263311"],
            "criteria_general": {"minimum_education": "Washington Accord accredited Bachelor", "relevant_work_experience": "0 (for accredited) to 3+ years (for CDR)", "english_required": True},
            "documents_required": ["Engineering degree (Bachelor/Masters)", "Academic transcripts", "CDR (3 career episodes + summary) for non-WA degrees", "Employment evidence", "CV", "Passport"],
            "assessment_fee_inr": 80000, "processing_time_weeks": 12,
            "contact_info": {"email": "memberservices@engineersaustralia.org.au"},
        },
        {
            "body_id": "vetassess", "name": "VETASSESS", "full_name": "Vocational Education and Training Assessment Services",
            "website": "https://vetassess.com.au",
            "assesses_occupations": ["221111", "222311", "224711", "234212", "234411", "139999"],
            "criteria_general": {"minimum_education": "Bachelor or equivalent in field", "relevant_work_experience": "1-3 years post-qualification (full-time)", "english_required": False},
            "documents_required": ["Degree certificate + transcripts", "Employment reference letters", "Job descriptions", "Pay slips", "Tax documents"],
            "assessment_fee_inr": 70000, "processing_time_weeks": 10,
            "contact_info": {"email": "info@vetassess.com.au"},
        },
        {
            "body_id": "cpa_au", "name": "CPA Australia", "full_name": "CPA Australia",
            "website": "https://cpaaustralia.com.au",
            "assesses_occupations": ["221111", "221112", "221213"],
            "criteria_general": {"minimum_education": "Bachelor in Accounting", "relevant_work_experience": "varies", "english_required": True, "english_minimum": "IELTS 7 each band / PTE 65 each band"},
            "documents_required": ["Bachelor of Accounting degree", "Transcripts", "Membership cert if applicable", "Employment letters"],
            "assessment_fee_inr": 60000, "processing_time_weeks": 8,
            "contact_info": {"email": "skills@cpaaustralia.com.au"},
        },
        {
            "body_id": "aim", "name": "AIM", "full_name": "Australian Institute of Management",
            "website": "https://aim.com.au",
            "assesses_occupations": ["133111", "133211", "133511", "139914"],
            "criteria_general": {"minimum_education": "Bachelor + Postgraduate or 8+ years experience", "relevant_work_experience": "varies", "english_required": False},
            "documents_required": ["Qualifications", "Detailed CV", "Employment evidence including team-size letters"],
            "assessment_fee_inr": 65000, "processing_time_weeks": 10,
            "contact_info": {"email": "skills@aim.com.au"},
        },
        {
            "body_id": "ahpra", "name": "AHPRA", "full_name": "Australian Health Practitioner Regulation Agency",
            "website": "https://ahpra.gov.au",
            "assesses_occupations": ["254111", "254411", "254412", "253111", "253411", "252411"],
            "criteria_general": {"minimum_education": "Recognized health qualification", "relevant_work_experience": "Registration-based", "english_required": True, "english_minimum": "OET B / IELTS 7"},
            "documents_required": ["Healthcare degree + transcripts", "Registration in home country", "OET / IELTS certificate", "Police clearance"],
            "assessment_fee_inr": 100000, "processing_time_weeks": 16,
            "contact_info": {"email": "info@ahpra.gov.au"},
        },
        {
            "body_id": "trades_tra", "name": "TRA", "full_name": "Trades Recognition Australia",
            "website": "https://tradesrecognitionaustralia.gov.au",
            "assesses_occupations": ["321111", "322311", "331212", "342111"],
            "criteria_general": {"minimum_education": "Trade qualification + apprenticeship", "relevant_work_experience": "3+ years post-qualification", "english_required": False},
            "documents_required": ["Trade certificate", "Apprenticeship records", "Employment letters", "Practical evidence (job tools photos)"],
            "assessment_fee_inr": 55000, "processing_time_weeks": 12,
            "contact_info": {"email": "tra@dewr.gov.au"},
        },
        {
            "body_id": "anmac", "name": "ANMAC", "full_name": "Australian Nursing and Midwifery Accreditation Council",
            "website": "https://anmac.org.au",
            "assesses_occupations": ["254418", "254423", "254499"],
            "criteria_general": {"minimum_education": "Bachelor of Nursing", "relevant_work_experience": "Registration + 1+ year practice", "english_required": True, "english_minimum": "IELTS 7 / OET B"},
            "documents_required": ["Nursing degree + transcripts", "Registration certificate", "Practice evidence", "English score"],
            "assessment_fee_inr": 70000, "processing_time_weeks": 10,
            "contact_info": {"email": "info@anmac.org.au"},
        },
    ],
    "occupation_codes": [
        # ICT (ACS)
        _occ("261313", "Software Engineer", "ICT Professionals", "261", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Software Developer","Application Programmer"], {"NSW":"high","VIC":"high","QLD":"high","WA":"medium"}),
        _occ("261311", "Analyst Programmer", "ICT Professionals", "261", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Programmer Analyst"], {"NSW":"high","VIC":"high"}),
        _occ("261312", "Developer Programmer", "ICT Professionals", "261", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Application Developer"], {"NSW":"high","VIC":"medium"}),
        _occ("263111", "Computer Network and Systems Engineer", "ICT Network and Support Professionals", "263", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Network Engineer","Systems Engineer"], {"NSW":"high","VIC":"high"}),
        _occ("262112", "ICT Security Specialist", "Database and Systems Administrators", "262", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Cybersecurity Specialist"], {"NSW":"high","VIC":"high","WA":"high"}),
        _occ("261111", "ICT Business Analyst", "ICT Professionals", "261", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Business Analyst (ICT)"], {"NSW":"high","VIC":"high"}),
        _occ("261112", "Systems Analyst", "ICT Professionals", "261", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium","VIC":"medium"}),
        # Engineering (EA)
        _occ("233211", "Civil Engineer", "Civil Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], ["Structural Engineer"], {"NSW":"medium","VIC":"medium","QLD":"high"}),
        _occ("233311", "Electrical Engineer", "Electrical Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium","VIC":"high","WA":"high"}),
        _occ("233411", "Electronics Engineer", "Telecommunications Engineering", "233", 1, "EA", "STSOL", ["190","491","482"], [], {"NSW":"medium","VIC":"medium"}),
        _occ("233512", "Mechanical Engineer", "Industrial, Mechanical and Production Engineers", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"high","SA":"high","WA":"high"}),
        _occ("233611", "Mining Engineer", "Resources and Energy Engineers", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"high","QLD":"high"}),
        _occ("233914", "Engineering Technologist", "Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
        # Accounting (CPA / VETASSESS)
        _occ("221111", "Accountant (General)", "Accountants", "221", 1, "CPA Australia", "MLTSSL", ["189","190","491","482","186"], ["Chartered Accountant"], {"NSW":"medium","VIC":"medium"}),
        _occ("221112", "Management Accountant", "Accountants", "221", 1, "CPA Australia", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium","VIC":"medium"}),
        _occ("221213", "External Auditor", "Auditors, Company Secretaries", "221", 1, "CPA Australia", "MLTSSL", ["189","190","491","482"], [], {"NSW":"medium"}),
        _occ("222311", "Financial Investment Adviser", "Financial Brokers and Dealers", "222", 1, "VETASSESS", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
        # Healthcare (AHPRA / ANMAC)
        _occ("254418", "Registered Nurse (Aged Care)", "Registered Nurses", "254", 1, "ANMAC", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"very_high","VIC":"very_high","QLD":"very_high"}),
        _occ("254423", "Registered Nurse (Critical Care)", "Registered Nurses", "254", 1, "ANMAC", "MLTSSL", ["189","190","491","482","186"], ["ICU Nurse"], {"NSW":"very_high","VIC":"very_high"}),
        _occ("253111", "General Practitioner", "Medical Practitioners", "253", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"very_high","VIC":"very_high","QLD":"very_high"}),
        _occ("254111", "Midwife", "Midwives", "254", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"high"}),
        _occ("252411", "Occupational Therapist", "Occupational Therapists", "252", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high"}),
        # Management (AIM)
        _occ("133111", "Construction Project Manager", "Construction Managers", "133", 1, "AIM", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"high"}),
        _occ("133211", "Engineering Manager", "Engineering Managers", "133", 1, "AIM", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"high","WA":"high"}),
        _occ("133511", "Production Manager (Manufacturing)", "Production Managers", "133", 1, "AIM", "STSOL", ["190","491","482"], [], {"VIC":"medium"}),
        # Trades (TRA)
        _occ("321111", "Automotive Electrician", "Automotive Electricians", "321", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"high"}),
        _occ("322311", "Metal Fabricator", "Structural Steel and Welding Trades", "322", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"high","QLD":"high"}),
        _occ("331212", "Carpenter", "Carpenters and Joiners", "331", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"very_high","VIC":"high"}),
        _occ("342111", "Electrician (General)", "Electricians", "342", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"high","QLD":"high"}),
        # Education / Misc
        _occ("241111", "Early Childhood (Pre-primary School) Teacher", "Early Childhood Teachers", "241", 1, "AITSL", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"high"}),
        _occ("241411", "Secondary School Teacher", "Secondary School Teachers", "241", 1, "AITSL", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium","VIC":"medium"}),
        _occ("234212", "Food Technologist", "Agricultural and Forestry Scientists", "234", 1, "VETASSESS", "STSOL", ["190","491","482"], [], {"VIC":"medium"}),
    ],
    "points_system": {
        "age": {"18-24": 25, "25-32": 30, "33-39": 25, "40-44": 15, "45+": 0},
        "english": {"competent_6": 0, "proficient_7": 10, "superior_8": 20},
        "experience_overseas": {"0-3_years": 0, "3-5_years": 5, "5-8_years": 10, "8+_years": 15},
        "experience_australia": {"0-1_year": 0, "1-3_years": 5, "3-5_years": 10, "5-8_years": 15, "8+_years": 20},
        "education": {"doctorate": 20, "bachelor_masters": 15, "diploma": 10, "trade_qualification": 10},
        "australian_education": {"1_year_or_more": 5, "specialist_qualification": 10, "regional_study": 5},
        "partner_skills": {"competent_english_only": 5, "skilled_partner": 10, "single_or_pr_partner": 10},
        "state_nomination": {"190": 5, "491": 15},
        "regional_study": 5,
        "professional_year": 5,
        "community_language": 5,
    },
    "document_templates": {
        "common_identity": [
            {"name": "Passport bio page (all family members)", "required": True},
            {"name": "Birth certificate", "required": True},
            {"name": "Marriage certificate (if applicable)", "required": False},
            {"name": "Children's birth certificates", "required": False},
            {"name": "Police clearance from all countries lived 12+ months", "required": True},
            {"name": "Medical examination (post-invitation)", "required": True},
        ],
        "skill_assessment_specific": {},
        "visa_specific": {
            "189": [
                {"name": "Skill assessment result (positive)", "required": True},
                {"name": "English test result (IELTS/PTE)", "required": True},
                {"name": "Form 80 (personal particulars)", "required": True},
                {"name": "CV", "required": True},
            ],
            "190": [
                {"name": "State nomination approval", "required": True},
                {"name": "Skill assessment result", "required": True},
                {"name": "English test result", "required": True},
                {"name": "Form 80", "required": True},
            ],
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════
# 🇨🇦 CANADA
# ═══════════════════════════════════════════════════════════════════════
CANADA = {
    "country": "Canada",
    "country_code": "CA",
    "country_flag_emoji": "🇨🇦",
    "is_active": True,
    "priority": 2,
    "visa_categories": [
        {
            "visa_id": "ca_ee_fswp", "code": "EE-FSWP", "name": "Express Entry · FSWP",
            "type": "Federal Skilled Worker Program (PR)",
            "description": "Points-based PR pathway under Express Entry. Most common for skilled foreign workers.",
            "eligibility": {
                "age_min": 18, "age_max": 47, "points_minimum": 67,
                "crs_typical_cutoff": 470,
                "language_requirement": {"clb_minimum": 7, "ielts_overall": 6.0, "ielts_per_band": 6.0, "accepts": ["IELTS General", "CELPIP"]},
                "experience_minimum_years": 1, "education_minimum": "bachelor",
                "sponsorship_required": False, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 6, "max_months": 8, "average_months": 6},
            "cost": {"government_fee_inr": 130000, "average_total_inr": 400000},
            "required_skill_assessment": True, "pathway_type": "Federal",
            "success_factors": ["CRS score 470+", "Strong language scores (CLB 9+)", "Canadian relatives or job offer (boost)"],
            "is_active": True,
        },
        {
            "visa_id": "ca_ee_cec", "code": "EE-CEC", "name": "Express Entry · CEC",
            "type": "Canadian Experience Class (PR)",
            "description": "PR for those with 1+ year Canadian skilled work experience.",
            "eligibility": {
                "age_min": 18, "age_max": 99, "points_minimum": 0,
                "crs_typical_cutoff": 460,
                "language_requirement": {"clb_minimum": 7, "ielts_overall": 6.0, "ielts_per_band": 6.0, "accepts": ["IELTS General", "CELPIP"]},
                "experience_minimum_years": 1, "education_minimum": "diploma",
                "sponsorship_required": False, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 3, "max_months": 6, "average_months": 5},
            "cost": {"government_fee_inr": 130000, "average_total_inr": 350000},
            "required_skill_assessment": False, "pathway_type": "Federal",
            "success_factors": ["1+ year Canadian experience", "TEER 0/1/2/3 occupation", "Strong CRS due to Canadian experience boost"],
            "is_active": True,
        },
        {
            "visa_id": "ca_ee_fstp", "code": "EE-FSTP", "name": "Express Entry · FSTP",
            "type": "Federal Skilled Trades Program (PR)",
            "description": "PR for skilled tradespeople with qualifying work experience.",
            "eligibility": {
                "age_min": 18, "age_max": 99, "points_minimum": 0,
                "crs_typical_cutoff": 430,
                "language_requirement": {"clb_minimum": 5, "ielts_overall": 5.0, "ielts_per_band": 4.5, "accepts": ["IELTS General", "CELPIP"]},
                "experience_minimum_years": 2, "education_minimum": "trade_qualification",
                "sponsorship_required": False, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 6, "max_months": 12, "average_months": 8},
            "cost": {"government_fee_inr": 130000, "average_total_inr": 350000},
            "required_skill_assessment": True, "pathway_type": "Federal",
            "success_factors": ["2+ years trade experience", "Valid trade qualification cert", "Job offer or PNP nomination"],
            "is_active": True,
        },
        {
            "visa_id": "ca_pnp", "code": "PNP", "name": "Provincial Nominee Program",
            "type": "Provincial Pathway (PR)",
            "description": "Province-driven PR streams; provincial nomination adds 600 CRS points.",
            "eligibility": {
                "age_min": 18, "age_max": 55, "points_minimum": 0,
                "language_requirement": {"clb_minimum": 4, "ielts_overall": 4.5, "ielts_per_band": 4.0, "accepts": ["IELTS General", "CELPIP"]},
                "experience_minimum_years": 1, "education_minimum": "diploma",
                "sponsorship_required": False, "state_nomination_required": True,
            },
            "processing_time": {"min_months": 9, "max_months": 18, "average_months": 12},
            "cost": {"government_fee_inr": 150000, "average_total_inr": 450000},
            "required_skill_assessment": False, "pathway_type": "Provincial",
            "success_factors": ["Provincial nomination (+600 CRS)", "Connection to province", "In-demand occupation in target province"],
            "is_active": True,
        },
    ],
    "skill_assessment_bodies": [
        {
            "body_id": "wes", "name": "WES", "full_name": "World Education Services",
            "website": "https://wes.org",
            "assesses_occupations": ["all_education"],
            "criteria_general": {"minimum_education": "Any post-secondary qualification", "english_required": False},
            "documents_required": ["Degree certificate (notarized)", "Transcripts (sent directly by institution)", "Application form"],
            "assessment_fee_inr": 20000, "processing_time_weeks": 4,
            "contact_info": {"email": "ca@wes.org", "phone": "+1 416 972 0070"},
        },
        {
            "body_id": "iqas", "name": "IQAS", "full_name": "International Qualifications Assessment Service (Alberta)",
            "website": "https://www.alberta.ca/iqas",
            "assesses_occupations": ["all_education"],
            "criteria_general": {"minimum_education": "Any post-secondary qualification", "english_required": False},
            "documents_required": ["Degree", "Transcripts", "Application + fee"],
            "assessment_fee_inr": 18000, "processing_time_weeks": 22,
            "contact_info": {"email": "iqas@gov.ab.ca"},
        },
        {
            "body_id": "icas", "name": "ICAS", "full_name": "International Credential Assessment Service of Canada",
            "website": "https://www.icascanada.ca",
            "assesses_occupations": ["all_education"],
            "criteria_general": {"minimum_education": "Post-secondary qualification", "english_required": False},
            "documents_required": ["Degree", "Transcripts", "Application"],
            "assessment_fee_inr": 22000, "processing_time_weeks": 6,
            "contact_info": {"email": "info@icascanada.ca"},
        },
        {
            "body_id": "ices", "name": "ICES", "full_name": "International Credential Evaluation Service (BC)",
            "website": "https://www.bcit.ca/ices",
            "assesses_occupations": ["all_education"],
            "criteria_general": {"minimum_education": "Post-secondary qualification", "english_required": False},
            "documents_required": ["Degree", "Transcripts", "Application"],
            "assessment_fee_inr": 21000, "processing_time_weeks": 8,
            "contact_info": {"email": "ices@bcit.ca"},
        },
        {
            "body_id": "mcc", "name": "MCC", "full_name": "Medical Council of Canada",
            "website": "https://mcc.ca",
            "assesses_occupations": ["31100", "31102", "31300"],
            "criteria_general": {"minimum_education": "MBBS / MD", "english_required": True, "english_minimum": "IELTS Academic 7+"},
            "documents_required": ["Medical degree", "Internship completion certificate", "Licensing exams (MCCQE)", "Medical license home country"],
            "assessment_fee_inr": 250000, "processing_time_weeks": 24,
            "contact_info": {"email": "info@mcc.ca"},
        },
    ],
    "occupation_codes": [
        # NOC 2021 — TEER 0/1/2 (high-demand)
        _occ("21231", "Software Engineers and Designers", "Computer and Information Systems", "212", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Software Developer"], {"ON":"high","BC":"high","AB":"high"}),
        _occ("21232", "Software Developers and Programmers", "Computer and Information Systems", "212", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Application Programmer"], {"ON":"high","BC":"high"}),
        _occ("21233", "Web Designers", "Computer and Information Systems", "212", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
        _occ("21234", "Web Developers and Programmers", "Computer and Information Systems", "212", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high","BC":"high"}),
        _occ("21311", "Computer Engineers", "Engineering", "213", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high","BC":"high"}),
        _occ("21221", "Business Systems Specialists", "Computer and Information Systems", "212", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["IT Business Analyst"], {"ON":"high"}),
        # Engineering
        _occ("21300", "Civil Engineers", "Civil and Mechanical Engineering", "213", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium","AB":"medium","BC":"medium"}),
        _occ("21301", "Mechanical Engineers", "Civil and Mechanical Engineering", "213", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium","AB":"high"}),
        _occ("21310", "Electrical and Electronics Engineers", "Engineering", "213", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium","AB":"medium"}),
        _occ("22300", "Civil Engineering Technologists", "Engineering Technologists", "223", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
        # Healthcare
        _occ("31301", "Registered Nurses", "Professional Occupations in Nursing", "313", 1, "MCC / NNAS", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"very_high","BC":"very_high","AB":"very_high","NS":"very_high"}),
        _occ("31100", "Specialist Physicians", "Professional Occupations in Health", "311", 1, "MCC", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"very_high","BC":"very_high"}),
        _occ("31102", "General Practitioners and Family Physicians", "Professional Occupations in Health", "311", 1, "MCC", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"all":"very_high"}),
        _occ("31300", "Pharmacists", "Professional Occupations in Health", "313", 1, "PEBC", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
        # Trades (TEER 2/3)
        _occ("72200", "Electricians (except Industrial and Power System)", "Electrical Trades", "722", 2, "Red Seal", "Federal", ["EE-FSTP","PNP"], [], {"ON":"high","AB":"high"}),
        _occ("72310", "Carpenters", "Carpentry Trades", "723", 2, "Red Seal", "Federal", ["EE-FSTP","PNP"], [], {"ON":"high","BC":"high"}),
        _occ("72400", "Welders and Related Machine Operators", "Welders", "724", 2, "Red Seal", "Federal", ["EE-FSTP","PNP"], [], {"AB":"high","ON":"medium"}),
        _occ("72500", "Heavy-Duty Equipment Mechanics", "Heavy Equipment Mechanics", "725", 2, "Red Seal", "Federal", ["EE-FSTP","PNP"], [], {"AB":"high","BC":"medium"}),
        # Finance / Management
        _occ("11100", "Financial Auditors and Accountants", "Auditors, Accountants", "111", 1, "CPA Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Chartered Accountant"], {"ON":"high","BC":"medium"}),
        _occ("11101", "Financial and Investment Analysts", "Financial Analysts", "111", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
        _occ("10010", "Financial Managers", "Specialized Middle Management", "100", 0, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
        _occ("10020", "Banking Managers", "Specialized Middle Management", "100", 0, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
        # Sales / Marketing
        _occ("10022", "Advertising, Marketing and Public Relations Managers", "Specialized Management", "100", 0, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
        # Education
        _occ("41200", "University Professors and Lecturers", "Professional Occupations in Education", "412", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium","BC":"medium"}),
        _occ("41220", "Secondary School Teachers", "Secondary School Teachers", "412", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"AB":"medium","ON":"medium"}),
        _occ("42202", "Early Childhood Educators", "Childcare and Home Support Workers", "422", 3, "WES", "Federal", ["EE-FSTP","PNP"], [], {"ON":"very_high","BC":"high"}),
        # Construction
        _occ("21300", "Construction Managers", "Specialized Management", "100", 0, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high","BC":"high"}),
        # IT Security
        _occ("22220", "Computer Network Technicians", "Computer Support", "222", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Network Administrator"], {"ON":"high"}),
        _occ("22222", "Information Systems Testing Technicians", "Computer Support", "222", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
        # Hospitality (PNP-friendly)
        _occ("63200", "Cooks", "Cooks", "632", 3, "—", "PNP", ["PNP"], [], {"all":"medium"}),
        _occ("63201", "Bakers", "Bakers", "632", 3, "—", "PNP", ["PNP"], [], {"BC":"medium","ON":"medium"}),
    ],
    "points_system": {
        # CRS — simplified categories
        "core_human_capital_age": {"18-29": 110, "30-32": 100, "33-35": 90, "36-39": 75, "40-44": 50, "45+": 25},
        "core_education": {"phd": 150, "masters": 135, "bachelor_3yr": 120, "bachelor_2yr": 98, "diploma_1yr": 90, "high_school": 30},
        "core_language_clb": {"clb_9_plus": 136, "clb_8": 92, "clb_7": 68, "clb_6": 36, "clb_5_or_less": 0},
        "core_canadian_experience": {"5_years": 80, "3_years": 64, "2_years": 53, "1_year": 40},
        "spouse_education": {"phd": 10, "masters": 10, "bachelor_3yr": 8, "diploma": 5},
        "skill_transferability_education_language": "up to 50",
        "additional_pnp": 600,
        "additional_job_offer_noc_00": 200,
        "additional_job_offer_other": 50,
        "additional_canadian_study_3yr_plus": 30,
        "additional_canadian_study_1_2yr": 15,
        "additional_sibling_in_canada": 15,
        "additional_french_strong": 50,
    },
    "document_templates": {
        "common_identity": [
            {"name": "Passport (all family)", "required": True},
            {"name": "Birth certificate", "required": True},
            {"name": "Marriage certificate (if applicable)", "required": False},
            {"name": "Police certificates from all countries lived 6+ months as adult", "required": True},
            {"name": "Proof of funds (settlement)", "required": True},
            {"name": "Medical examination (post-invitation)", "required": True},
        ],
        "visa_specific": {
            "EE-FSWP": [
                {"name": "ECA (Educational Credential Assessment)", "required": True},
                {"name": "IELTS General or CELPIP result", "required": True},
                {"name": "Employment reference letters (last 10 years)", "required": True},
            ],
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════
# 🇳🇿 NEW ZEALAND
# ═══════════════════════════════════════════════════════════════════════
NEW_ZEALAND = {
    "country": "New Zealand",
    "country_code": "NZ",
    "country_flag_emoji": "🇳🇿",
    "is_active": True,
    "priority": 3,
    "visa_categories": [
        {
            "visa_id": "nz_smc", "code": "SMC", "name": "Skilled Migrant Category",
            "type": "Skilled Migrant (PR)",
            "description": "Points-based pathway for skilled workers (post-2023: 6-point system).",
            "eligibility": {
                "age_min": 18, "age_max": 55, "points_minimum": 6,
                "language_requirement": {"ielts_overall": 6.5, "ielts_per_band": 6.5, "accepts": ["IELTS", "PTE", "TOEFL"]},
                "experience_minimum_years": 0, "education_minimum": "bachelor",
                "sponsorship_required": False, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 4, "max_months": 12, "average_months": 8},
            "cost": {"government_fee_inr": 200000, "average_total_inr": 500000},
            "required_skill_assessment": True, "pathway_type": "Federal",
            "success_factors": ["Job offer in NZ (most reliable)", "Recognised qualification", "Skilled work experience"],
            "is_active": True,
        },
        {
            "visa_id": "nz_green_tier_1", "code": "Green-T1", "name": "Green List · Tier 1",
            "type": "Straight to Residence",
            "description": "Direct PR pathway for highly-skilled in-demand professions (engineers, doctors, etc.).",
            "eligibility": {
                "age_min": 18, "age_max": 55, "points_minimum": 0,
                "language_requirement": {"ielts_overall": 6.5, "ielts_per_band": 6.5, "accepts": ["IELTS", "PTE"]},
                "experience_minimum_years": 0, "education_minimum": "bachelor",
                "sponsorship_required": True, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 2, "max_months": 6, "average_months": 4},
            "cost": {"government_fee_inr": 180000, "average_total_inr": 400000},
            "required_skill_assessment": True, "pathway_type": "Green List",
            "success_factors": ["Profession on Tier 1 Green List", "Recognized qualification", "Skill body assessment passed"],
            "is_active": True,
        },
        {
            "visa_id": "nz_green_tier_2", "code": "Green-T2", "name": "Green List · Tier 2",
            "type": "Work to Residence (2-year pathway)",
            "description": "Work for 2 years then transition to PR; professions like nurses, secondary teachers, etc.",
            "eligibility": {
                "age_min": 18, "age_max": 55, "points_minimum": 0,
                "language_requirement": {"ielts_overall": 6.5, "ielts_per_band": 6.5, "accepts": ["IELTS", "PTE"]},
                "experience_minimum_years": 2, "education_minimum": "bachelor",
                "sponsorship_required": True, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 3, "max_months": 7, "average_months": 5},
            "cost": {"government_fee_inr": 200000, "average_total_inr": 450000},
            "required_skill_assessment": True, "pathway_type": "Green List",
            "success_factors": ["Profession on Tier 2 Green List", "2 years experience", "NZ employer sponsorship"],
            "is_active": True,
        },
        {
            "visa_id": "nz_aewv", "code": "AEWV", "name": "Accredited Employer Work Visa",
            "type": "Temporary Work Visa (up to 5 years)",
            "description": "Work visa requiring accredited employer sponsorship.",
            "eligibility": {
                "age_min": 18, "age_max": 99, "points_minimum": 0,
                "language_requirement": {"ielts_overall": 5.0, "ielts_per_band": 5.0, "accepts": ["IELTS", "PTE"]},
                "experience_minimum_years": 0, "education_minimum": "trade_qualification",
                "sponsorship_required": True, "state_nomination_required": False,
            },
            "processing_time": {"min_months": 2, "max_months": 5, "average_months": 3},
            "cost": {"government_fee_inr": 140000, "average_total_inr": 280000},
            "required_skill_assessment": False, "pathway_type": "Temporary",
            "success_factors": ["Accredited employer", "Genuine job offer", "Pay above NZ median wage"],
            "is_active": True,
        },
    ],
    "skill_assessment_bodies": [
        {
            "body_id": "nzqa", "name": "NZQA", "full_name": "New Zealand Qualifications Authority",
            "website": "https://nzqa.govt.nz",
            "assesses_occupations": ["all_education"],
            "criteria_general": {"minimum_education": "Any post-secondary qualification", "english_required": False},
            "documents_required": ["Degree certificate", "Academic transcripts", "Translations (if not English)", "Application form"],
            "assessment_fee_inr": 30000, "processing_time_weeks": 6,
            "contact_info": {"email": "qualifications@nzqa.govt.nz"},
        },
        {
            "body_id": "ipenz", "name": "Engineering NZ", "full_name": "Engineering New Zealand (formerly IPENZ)",
            "website": "https://engineeringnz.org",
            "assesses_occupations": ["233211", "233311", "233512"],
            "criteria_general": {"minimum_education": "Bachelor of Engineering (Washington Accord accredited)", "english_required": True},
            "documents_required": ["Engineering degree", "Transcripts", "Work experience evidence", "CV"],
            "assessment_fee_inr": 75000, "processing_time_weeks": 12,
            "contact_info": {"email": "engineers@engineeringnz.org"},
        },
        {
            "body_id": "nzncea", "name": "Nursing Council of NZ", "full_name": "Nursing Council of New Zealand",
            "website": "https://nursingcouncil.org.nz",
            "assesses_occupations": ["254418", "254423"],
            "criteria_general": {"minimum_education": "Bachelor of Nursing", "english_required": True, "english_minimum": "IELTS 7 / OET B"},
            "documents_required": ["Nursing degree", "Registration in home country", "English score", "CPR cert"],
            "assessment_fee_inr": 90000, "processing_time_weeks": 14,
            "contact_info": {"email": "info@nursingcouncil.org.nz"},
        },
        {
            "body_id": "tcnz", "name": "Teaching Council NZ", "full_name": "Teaching Council of Aotearoa New Zealand",
            "website": "https://teachingcouncil.nz",
            "assesses_occupations": ["241111", "241411"],
            "criteria_general": {"minimum_education": "Bachelor + teaching qualification", "english_required": True},
            "documents_required": ["Teaching degree", "Teaching certification", "Police clearance", "References"],
            "assessment_fee_inr": 50000, "processing_time_weeks": 10,
            "contact_info": {"email": "info@teachingcouncil.nz"},
        },
    ],
    "occupation_codes": [
        # IT (Tier 1 Green List)
        _occ("261313", "Software Engineer", "ICT Professionals", "261", 1, "NZQA", "Green-T1", ["SMC","Green-T1","AEWV"], ["Software Developer"], {"all":"high"}),
        _occ("261311", "Analyst Programmer", "ICT Professionals", "261", 1, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"medium"}),
        _occ("261312", "Developer Programmer", "ICT Professionals", "261", 1, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"medium"}),
        _occ("263111", "Network Engineer", "ICT Professionals", "263", 1, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"medium"}),
        _occ("262112", "ICT Security Specialist", "ICT Professionals", "262", 1, "NZQA", "Green-T1", ["SMC","Green-T1","AEWV"], [], {"all":"high"}),
        # Engineering (Tier 1)
        _occ("233211", "Civil Engineer", "Civil Engineers", "233", 1, "Engineering NZ", "Green-T1", ["SMC","Green-T1","AEWV"], [], {"all":"very_high"}),
        _occ("233311", "Electrical Engineer", "Electrical Engineers", "233", 1, "Engineering NZ", "Green-T1", ["SMC","Green-T1","AEWV"], [], {"all":"high"}),
        _occ("233512", "Mechanical Engineer", "Mechanical Engineers", "233", 1, "Engineering NZ", "Green-T1", ["SMC","Green-T1","AEWV"], [], {"all":"high"}),
        # Healthcare (Tier 1)
        _occ("253111", "General Practitioner", "General Practitioners", "253", 1, "MCNZ", "Green-T1", ["SMC","Green-T1","AEWV"], [], {"all":"very_high"}),
        _occ("254418", "Registered Nurse", "Registered Nurses", "254", 1, "Nursing Council NZ", "Green-T1", ["SMC","Green-T1","AEWV"], [], {"all":"very_high"}),
        _occ("254412", "Registered Nurse (Mental Health)", "Registered Nurses", "254", 1, "Nursing Council NZ", "Green-T1", ["SMC","Green-T1","AEWV"], [], {"all":"very_high"}),
        # Education (Tier 2)
        _occ("241111", "Early Childhood Teacher", "Early Childhood Teachers", "241", 1, "Teaching Council NZ", "Green-T2", ["SMC","Green-T2","AEWV"], [], {"all":"high"}),
        _occ("241411", "Secondary School Teacher", "Secondary Teachers", "241", 1, "Teaching Council NZ", "Green-T2", ["SMC","Green-T2","AEWV"], [], {"all":"medium"}),
        # Trades (AEWV common)
        _occ("321111", "Automotive Electrician", "Automotive Technicians", "321", 3, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"medium"}),
        _occ("331212", "Carpenter", "Carpenters", "331", 3, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"high"}),
        _occ("342111", "Electrician (General)", "Electricians", "342", 3, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"high"}),
        # Finance / Accounting
        _occ("221111", "Accountant (General)", "Accountants", "221", 1, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"medium"}),
        # Construction
        _occ("133111", "Construction Project Manager", "Construction Managers", "133", 1, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"high"}),
        # Hospitality / Service
        _occ("351311", "Chef", "Chefs", "351", 2, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"medium"}),
        _occ("141311", "Hotel/Motel Manager", "Hospitality Managers", "141", 2, "NZQA", "Federal", ["SMC","AEWV"], [], {"all":"medium"}),
    ],
    "points_system": {
        # Post-Oct 2023 SMC: 6-point system based on qualification + occupation + income/experience
        "qualification": {"phd": 6, "masters": 5, "bachelor_honours": 4, "bachelor": 3, "diploma_level_7": 2, "occupational_registration_or_trade": 3},
        "income_multiplier_median_wage": {"3x_or_more": 6, "2x": 4, "1.5x": 3, "1x": 1},
        "skilled_experience_years": {"3_plus": 3, "2": 2, "1": 1},
        "english_minimum": "IELTS 6.5 / equivalent (mandatory entry)",
        "minimum_total_points": 6,
    },
    "document_templates": {
        "common_identity": [
            {"name": "Passport (all family members)", "required": True},
            {"name": "Birth certificate", "required": True},
            {"name": "Marriage certificate (if applicable)", "required": False},
            {"name": "Police clearance from all countries lived 5+ years as adult", "required": True},
            {"name": "Medical examination", "required": True},
            {"name": "Chest X-ray", "required": True},
        ],
        "visa_specific": {
            "SMC": [
                {"name": "Skill body assessment", "required": True},
                {"name": "Job offer (highly recommended)", "required": False},
                {"name": "IELTS / PTE result", "required": True},
                {"name": "Employment reference letters", "required": True},
            ],
        },
    },
}


SEED_COUNTRIES = [AUSTRALIA, CANADA, NEW_ZEALAND]


async def seed_country_rules(col):
    """Idempotent seed — only inserts if collection is empty or country missing.
    Existing data is NOT overwritten (so admin edits persist across restarts).
    """
    inserted = 0
    for country in SEED_COUNTRIES:
        existing = await col.find_one({"country_code": country["country_code"]}, {"_id": 1})
        if existing:
            continue
        doc = dict(country)
        doc["meta"] = {
            "last_updated": NOW,
            "data_source": "official_government_websites",
            "source_url": _source_url_for(country["country_code"]),
            "next_review_date": NOW.replace(year=NOW.year + 1),
            "seeded": True,
        }
        doc["created_at"] = NOW
        doc["updated_at"] = NOW
        await col.insert_one(doc)
        inserted += 1
    return inserted


def _source_url_for(code: str) -> str:
    return {
        "AU": "https://immi.homeaffairs.gov.au",
        "CA": "https://www.canada.ca/en/immigration-refugees-citizenship.html",
        "NZ": "https://www.immigration.govt.nz",
    }.get(code, "")
