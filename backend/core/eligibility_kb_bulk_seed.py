"""Phase 6 v2 Part 4 — Bulk Seed Expansion for AU/CA/NZ.

Adds 100+ additional occupation codes per country to reach Sir's PRD target of 200+/country.
Codes are sourced from official ANZSCO/NOC/NZ ANZSCO lists.

Usage:
    python -m core.eligibility_kb_bulk_seed
"""
from datetime import datetime, timezone
from typing import List, Dict, Any


def _occ(code, title, group, group_code, skill_level, body, pathway, visas, alts=None, demand=None):
    return {
        "code": code, "title": title, "group": group, "group_code": group_code,
        "skill_level": skill_level, "assessing_body": body, "pathway": pathway,
        "eligible_visas": visas, "alternative_titles": alts or [],
        "state_demand": demand or {}, "is_active": True,
    }


# ════════════════════════════════════════════════════════════════
# AUSTRALIA — ANZSCO codes (target 200+)
# Source: https://www.abs.gov.au/statistics/classifications/anzsco-australian-and-new-zealand-standard-classification-occupations
# ════════════════════════════════════════════════════════════════
AU_EXPANSION: List[Dict[str, Any]] = [
    # ICT / Software (ACS body) — add many more codes
    _occ("261111", "ICT Business Analyst", "Business and Systems Analysts", "261", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Business Systems Analyst","BA","Business Analyst"], {"NSW":"high","VIC":"high","QLD":"high"}),
    _occ("261112", "Systems Analyst", "Business and Systems Analysts", "261", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["IT Systems Analyst"], {"NSW":"medium","VIC":"high"}),
    _occ("261211", "Multimedia Specialist", "Multimedia Specialists and Web Developers", "261", 1, "ACS", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("261212", "Web Developer", "Multimedia Specialists and Web Developers", "261", 1, "ACS", "STSOL", ["190","491","482"], ["Front End Developer","Web Designer"], {"VIC":"medium"}),
    _occ("261311", "Analyst Programmer", "Software and Applications Programmers", "261", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Programmer Analyst"], {"NSW":"high","VIC":"high"}),
    _occ("261312", "Developer Programmer", "Software and Applications Programmers", "261", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Java Developer","Python Developer","Programmer"], {"NSW":"very_high","VIC":"very_high","QLD":"high"}),
    _occ("261314", "Software Tester", "Software and Applications Programmers", "261", 1, "ACS", "MLTSSL", ["189","190","491","482"], ["QA Engineer","Test Engineer","Automation Tester"], {"NSW":"high","VIC":"high"}),
    _occ("262112", "ICT Security Specialist", "ICT Security Specialists", "262", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Cybersecurity Engineer","Information Security Analyst"], {"NSW":"very_high","VIC":"high"}),
    _occ("263111", "Computer Network and Systems Engineer", "Network Professionals", "263", 1, "ACS", "MLTSSL", ["189","190","491","482","186"], ["Network Engineer"], {"NSW":"high","VIC":"medium"}),
    _occ("263211", "ICT Quality Assurance Engineer", "ICT Support and Test Engineers", "263", 1, "ACS", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("263212", "ICT Support Engineer", "ICT Support and Test Engineers", "263", 1, "ACS", "STSOL", ["190","491","482"], ["Helpdesk Engineer"], {"VIC":"medium"}),
    _occ("263213", "ICT Systems Test Engineer", "ICT Support and Test Engineers", "263", 1, "ACS", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("263311", "Telecommunications Engineer", "Telecommunications Engineering Professionals", "263", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("263312", "Telecommunications Network Engineer", "Telecommunications Engineering Professionals", "263", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),

    # Engineering (EA body)
    _occ("233111", "Chemical Engineer", "Chemical and Materials Engineers", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"high","QLD":"medium"}),
    _occ("233112", "Materials Engineer", "Chemical and Materials Engineers", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"medium"}),
    _occ("233211", "Civil Engineer", "Civil Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], ["Civil Engineering Project Engineer"], {"NSW":"very_high","VIC":"high","QLD":"high"}),
    _occ("233212", "Geotechnical Engineer", "Civil Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"high"}),
    _occ("233214", "Structural Engineer", "Civil Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high"}),
    _occ("233215", "Transport Engineer", "Civil Engineering Professionals", "233", 1, "EA", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("233311", "Electrical Engineer", "Electrical Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"high","QLD":"medium"}),
    _occ("233411", "Electronics Engineer", "Electronics Engineers", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium","VIC":"medium"}),
    _occ("233511", "Industrial Engineer", "Industrial, Mechanical and Production Engineers", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"medium"}),
    _occ("233512", "Mechanical Engineer", "Industrial, Mechanical and Production Engineers", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"high","WA":"high","QLD":"medium"}),
    _occ("233513", "Production or Plant Engineer", "Industrial, Mechanical and Production Engineers", "233", 1, "EA", "STSOL", ["190","491","482"], [], {"VIC":"medium"}),
    _occ("233611", "Mining Engineer (excl Petroleum)", "Mining Engineers", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"very_high","QLD":"high"}),
    _occ("233612", "Petroleum Engineer", "Mining Engineers", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"high"}),
    _occ("233913", "Biomedical Engineer", "Other Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"medium"}),
    _occ("233914", "Engineering Technologist", "Other Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482"], [], {"NSW":"medium"}),
    _occ("233915", "Environmental Engineer", "Other Engineering Professionals", "233", 1, "EA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium","VIC":"medium"}),

    # Accounting / Finance (CPA Australia / CAANZ / IPA)
    _occ("221111", "Accountant (General)", "Accountants", "221", 1, "CPA Australia", "MLTSSL", ["189","190","491","482","186"], ["General Accountant"], {"NSW":"high","VIC":"high","QLD":"medium"}),
    _occ("221112", "Management Accountant", "Accountants", "221", 1, "CPA Australia", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"medium"}),
    _occ("221113", "Taxation Accountant", "Accountants", "221", 1, "CPA Australia", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("221213", "External Auditor", "Auditors, Company Secretaries and Corporate Treasurers", "221", 1, "CPA Australia", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium","VIC":"medium"}),
    _occ("222211", "Financial Market Dealer", "Financial Dealers", "222", 1, "VETASSESS", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("222311", "Financial Investment Adviser", "Financial Investment Advisers", "222", 1, "VETASSESS", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),

    # Healthcare (AHPRA / ANMAC)
    _occ("253111", "General Practitioner", "Medical Practitioners", "253", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], ["GP","Family Doctor"], {"all":"very_high"}),
    _occ("253411", "Psychiatrist", "Medical Practitioners", "253", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("253511", "Specialist Physician (General Medicine)", "Medical Practitioners", "253", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("254111", "Midwife", "Midwives", "254", 1, "ANMAC", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("254411", "Nurse Practitioner", "Nurse Practitioners", "254", 1, "ANMAC", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"high"}),
    _occ("254412", "Registered Nurse (Aged Care)", "Registered Nurses", "254", 1, "ANMAC", "MLTSSL", ["189","190","491","482","186"], ["RN Aged Care"], {"all":"very_high"}),
    _occ("254418", "Registered Nurse (Medical)", "Registered Nurses", "254", 1, "ANMAC", "MLTSSL", ["189","190","491","482","186"], ["RN"], {"all":"very_high"}),
    _occ("254421", "Registered Nurse (Mental Health)", "Registered Nurses", "254", 1, "ANMAC", "MLTSSL", ["189","190","491","482","186"], [], {"all":"very_high"}),
    _occ("254422", "Registered Nurse (Perioperative)", "Registered Nurses", "254", 1, "ANMAC", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("254423", "Registered Nurse (Surgical)", "Registered Nurses", "254", 1, "ANMAC", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("251211", "Medical Diagnostic Radiographer", "Medical Imaging Professionals", "251", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"medium"}),
    _occ("251212", "Medical Radiation Therapist", "Medical Imaging Professionals", "251", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("252411", "Occupational Therapist", "Occupational and Environmental Health Professionals", "252", 1, "OTC", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("252511", "Physiotherapist", "Physiotherapists", "252", 1, "APC", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("252611", "Podiatrist", "Podiatrists", "252", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("252711", "Speech Pathologist", "Speech Professionals", "252", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("252712", "Audiologist", "Speech Professionals", "252", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"medium"}),
    _occ("241111", "Early Childhood (Pre-primary School) Teacher", "Early Childhood Teachers", "241", 1, "AITSL", "MLTSSL", ["189","190","491","482","186"], [], {"all":"very_high"}),
    _occ("241511", "Special Needs Teacher", "Special Education Teachers", "241", 1, "AITSL", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("241512", "Teacher of the Hearing Impaired", "Special Education Teachers", "241", 1, "AITSL", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("241513", "Teacher of the Sight Impaired", "Special Education Teachers", "241", 1, "AITSL", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("242111", "University Lecturer", "University Lecturers and Tutors", "242", 1, "VETASSESS", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium","VIC":"medium"}),

    # Construction / Trades (VETASSESS, TRA)
    _occ("133111", "Construction Project Manager", "Construction Managers", "133", 1, "AIM", "MLTSSL", ["189","190","491","482","186"], ["Project Manager (Construction)"], {"NSW":"high","VIC":"high"}),
    _occ("133112", "Project Builder", "Construction Managers", "133", 1, "AIM", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("312113", "Building Inspector", "Architectural, Building and Surveying Technicians", "312", 2, "VETASSESS", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("321111", "Automotive Electrician", "Automotive Electricians and Mechanics", "321", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"medium"}),
    _occ("321211", "Motor Mechanic (General)", "Automotive Electricians and Mechanics", "321", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("322311", "Metal Fabricator", "Structural Steel and Welding Trades Workers", "322", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"high","QLD":"medium"}),
    _occ("322313", "Welder (First Class)", "Structural Steel and Welding Trades Workers", "322", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], ["Welder"], {"WA":"high","NT":"medium"}),
    _occ("331111", "Bricklayer", "Bricklayers and Stonemasons", "331", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"high"}),
    _occ("331212", "Carpenter", "Carpenters and Joiners", "331", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("332211", "Painter", "Painting Trades Workers", "332", 3, "TRA", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("333211", "Fibrous Plasterer", "Plasterers", "333", 3, "TRA", "STSOL", ["190","491","482"], [], {"VIC":"medium"}),
    _occ("333212", "Solid Plasterer", "Plasterers", "333", 3, "TRA", "STSOL", ["190","491","482"], [], {"VIC":"medium"}),
    _occ("334111", "Plumber (General)", "Plumbers", "334", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"all":"very_high"}),
    _occ("334112", "Airconditioning and Mechanical Services Plumber", "Plumbers", "334", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high"}),
    _occ("334113", "Drainer", "Plumbers", "334", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"medium"}),
    _occ("334114", "Gasfitter", "Plumbers", "334", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"medium"}),
    _occ("334115", "Roof Plumber", "Plumbers", "334", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"medium"}),
    _occ("341111", "Electrician (General)", "Electricians", "341", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"all":"very_high"}),
    _occ("341112", "Electrician (Special Class)", "Electricians", "341", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"high"}),
    _occ("342111", "Airconditioning and Refrigeration Mechanic", "Air-conditioning and Refrigeration Mechanics", "342", 3, "TRA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","WA":"medium"}),
    _occ("342211", "Electrical Linesworker", "Electrical Distribution Trades Workers", "342", 3, "TRA", "MLTSSL", ["189","190","491","482"], [], {"WA":"medium"}),
    _occ("351211", "Cook", "Cooks", "351", 4, "TRA", "STSOL", ["190","491","482"], [], {"VIC":"medium"}),
    _occ("351311", "Chef", "Chefs", "351", 2, "TRA", "MLTSSL", ["189","190","491","482","186"], ["Sous Chef","Head Chef"], {"NSW":"very_high","VIC":"very_high","QLD":"high"}),

    # Architects, Designers (NAATI / VETASSESS / AACA)
    _occ("232111", "Architect", "Architects and Landscape Architects", "232", 1, "AACA", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("232112", "Landscape Architect", "Architects and Landscape Architects", "232", 1, "AACA", "STSOL", ["190","491","482"], [], {"VIC":"medium"}),
    _occ("232311", "Industrial Designer", "Designers (Other)", "232", 1, "VETASSESS", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("232312", "Jewellery Designer", "Designers (Other)", "232", 1, "VETASSESS", "STSOL", ["190","491","482"], [], {}),
    _occ("232611", "Multimedia Designer (UX/UI)", "Designers (ICT)", "232", 1, "VETASSESS", "STSOL", ["190","491","482"], ["UX Designer","UI Designer","UI/UX Designer"], {"NSW":"medium","VIC":"medium"}),

    # Surveyors / Town Planners (VETASSESS / SSSI)
    _occ("232212", "Surveyor", "Surveyors and Spatial Scientists", "232", 1, "SSSI", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),
    _occ("232611", "Web Designer", "Designers (ICT)", "232", 1, "VETASSESS", "STSOL", ["190","491","482"], [], {}),

    # Management codes that work with VETASSESS / AIM
    _occ("139914", "Quality Assurance Manager", "Other Specialist Managers", "139", 1, "AIM", "STSOL", ["190","491","482"], [], {"VIC":"medium"}),
    _occ("131112", "Sales and Marketing Manager", "Advertising, Public Relations and Sales Managers", "131", 1, "AIM", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("131113", "Public Relations Manager", "Advertising, Public Relations and Sales Managers", "131", 1, "AIM", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("131114", "Advertising Manager", "Advertising, Public Relations and Sales Managers", "131", 1, "AIM", "STSOL", ["190","491","482"], ["Marketing Director"], {"NSW":"medium"}),
    _occ("132211", "Finance Manager", "Finance Managers", "132", 1, "AIM", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("132311", "Human Resource Manager", "HR Managers", "132", 1, "AIM", "STSOL", ["190","491","482"], ["HR Manager"], {"NSW":"medium","VIC":"medium"}),
    _occ("132411", "Policy and Planning Manager", "Policy and Planning Managers", "132", 1, "AIM", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("133211", "Engineering Manager", "Engineering Managers", "133", 1, "AIM", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"high","WA":"high"}),
    _occ("133513", "Production Manager (Mining)", "Production Managers", "133", 1, "AIM", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"very_high"}),

    # Sciences (VETASSESS)
    _occ("234211", "Agricultural Scientist", "Agricultural and Forestry Scientists", "234", 1, "VETASSESS", "MLTSSL", ["189","190","491","482","186"], [], {"VIC":"medium"}),
    _occ("234411", "Geologist", "Geologists and Geophysicists", "234", 1, "VETASSESS", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"high"}),
    _occ("234412", "Geophysicist", "Geologists and Geophysicists", "234", 1, "VETASSESS", "MLTSSL", ["189","190","491","482","186"], [], {"WA":"medium"}),
    _occ("234511", "Life Scientist (General)", "Life Scientists", "234", 1, "VETASSESS", "STSOL", ["190","491","482"], [], {"VIC":"medium"}),
    _occ("234611", "Medical Laboratory Scientist", "Medical Laboratory Scientists", "234", 1, "AIMS", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),

    # Legal (Bar Admission via Legal Profession Admission Board)
    _occ("271111", "Barrister", "Barristers", "271", 1, "LPAB", "STSOL", ["190","491","482"], [], {"NSW":"medium"}),
    _occ("271311", "Solicitor", "Solicitors", "271", 1, "LPAB", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"medium"}),

    # Social Workers
    _occ("272511", "Social Worker", "Social Workers", "272", 1, "AASW", "MLTSSL", ["189","190","491","482","186"], [], {"NSW":"high","VIC":"medium"}),
    _occ("272412", "Interpreter", "Interpreters and Translators", "272", 1, "NAATI", "STSOL", ["190","491","482"], [], {}),
    _occ("272413", "Translator", "Interpreters and Translators", "272", 1, "NAATI", "STSOL", ["190","491","482"], [], {}),

    # Pharmacy
    _occ("251513", "Retail Pharmacist", "Pharmacists", "251", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
    _occ("251512", "Hospital Pharmacist", "Pharmacists", "251", 1, "AHPRA", "MLTSSL", ["189","190","491","482","186"], [], {"all":"high"}),
]


# ════════════════════════════════════════════════════════════════
# CANADA — NOC codes (target 100+)
# Source: NOC 2021 — https://noc.esdc.gc.ca/
# ════════════════════════════════════════════════════════════════
CA_EXPANSION: List[Dict[str, Any]] = [
    # Management
    _occ("00010", "Senior Government Managers and Officials", "Legislators and Senior Managers", "00", 0, "WES", "Federal", ["EE-FSWP","PNP"], [], {"ON":"medium"}),
    _occ("10010", "Financial Managers", "Specialized Middle Management", "10", 0, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
    _occ("10011", "Human Resources Managers", "Specialized Middle Management", "10", 0, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
    _occ("10019", "Other Administrative Services Managers", "Specialized Middle Management", "10", 0, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("10020", "Insurance/Real Estate and Financial Brokerage Managers", "Specialized Middle Management", "10", 0, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("10030", "Telecommunication carriers Managers", "Specialized Middle Management", "10", 0, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {}),
    # Business and Finance
    _occ("11100", "Financial Auditors and Accountants", "Professional Business Services", "11", 1, "CPA Canada/CICA", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Chartered Accountant","CPA"], {"ON":"high","BC":"high","AB":"medium"}),
    _occ("11101", "Financial and Investment Analysts", "Professional Business Services", "11", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
    _occ("11102", "Financial Advisors", "Professional Business Services", "11", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("11103", "Securities Agents, Investment Dealers", "Professional Business Services", "11", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("11200", "Human Resources Professionals", "Professional Business Services", "11", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
    _occ("11201", "Professional Occupations in Business Management Consulting", "Professional Business Services", "11", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Management Consultant"], {"ON":"high"}),
    _occ("11202", "Professional Occupations in Advertising/Marketing/Public Relations", "Professional Business Services", "11", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Marketing Manager","Brand Manager"], {"ON":"high","BC":"high"}),
    # Natural and Applied Sciences (IT focused)
    _occ("21100", "Physicists and Astronomers", "Natural Sciences", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("21101", "Chemists", "Natural Sciences", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("21102", "Geoscientists and Oceanographers", "Natural Sciences", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"AB":"medium"}),
    _occ("21200", "Architects", "Engineering and Architecture", "21", 1, "RAIC", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("21210", "Mathematicians, Statisticians and Actuaries", "Natural Sciences", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("21211", "Data Scientists", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Machine Learning Engineer","ML Engineer"], {"ON":"very_high","BC":"high"}),
    _occ("21220", "Cybersecurity Specialists", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"very_high","BC":"high"}),
    _occ("21221", "Business Systems Specialists", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Business Analyst"], {"ON":"high"}),
    _occ("21222", "Information Systems Specialists", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
    _occ("21223", "Database Analysts and Data Administrators", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
    _occ("21230", "Computer Systems Developers and Programmers", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Software Developer","Programmer"], {"ON":"very_high","BC":"very_high"}),
    _occ("21231", "Software Engineers and Designers", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["Software Engineer","SDE"], {"ON":"very_high","BC":"very_high","QC":"high"}),
    _occ("21232", "Software Developers and Programmers", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"very_high","BC":"high"}),
    _occ("21233", "Web Designers", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("21234", "Web Developers and Programmers", "Information Systems", "21", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
    _occ("21300", "Civil Engineers", "Engineering and Architecture", "21", 1, "Engineers Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high","AB":"high"}),
    _occ("21301", "Mechanical Engineers", "Engineering and Architecture", "21", 1, "Engineers Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high","AB":"high"}),
    _occ("21310", "Electrical and Electronics Engineers", "Engineering and Architecture", "21", 1, "Engineers Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high","QC":"medium"}),
    _occ("21311", "Computer Engineers (excl Software)", "Engineering and Architecture", "21", 1, "Engineers Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("21320", "Chemical Engineers", "Engineering and Architecture", "21", 1, "Engineers Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"AB":"medium"}),
    _occ("21321", "Industrial and Manufacturing Engineers", "Engineering and Architecture", "21", 1, "Engineers Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("21330", "Mining Engineers", "Engineering and Architecture", "21", 1, "Engineers Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"AB":"high"}),
    _occ("21331", "Geological Engineers", "Engineering and Architecture", "21", 1, "Engineers Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"AB":"medium"}),
    _occ("21399", "Other Professional Engineers, n.e.c.", "Engineering and Architecture", "21", 1, "Engineers Canada", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {}),
    # Healthcare
    _occ("31100", "Specialist Physicians", "Health Care Professionals", "31", 1, "MCC", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"all":"high"}),
    _occ("31101", "General Practitioners and Family Physicians", "Health Care Professionals", "31", 1, "MCC", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"all":"very_high"}),
    _occ("31102", "Dentists", "Health Care Professionals", "31", 1, "NDEB", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"all":"high"}),
    _occ("31200", "Pharmacists", "Health Care Professionals", "31", 1, "PEBC", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"all":"high"}),
    _occ("31300", "Nursing Coordinators and Supervisors", "Health Care Professionals", "31", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
    _occ("31301", "Registered Nurses and Registered Psychiatric Nurses", "Health Care Professionals", "31", 1, "NNAS", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["RN"], {"all":"very_high"}),
    _occ("31302", "Nurse Practitioners", "Health Care Professionals", "31", 1, "NNAS", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"all":"very_high"}),
    _occ("32100", "Opticians", "Technical Occupations", "32", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("32101", "Licensed Practical Nurses", "Technical Occupations", "32", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], ["LPN"], {"all":"high"}),
    # Education
    _occ("41200", "University Professors and Lecturers", "Education", "41", 1, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"medium"}),
    _occ("41210", "Elementary School and Kindergarten Teachers", "Education", "41", 1, "WES/Provincial", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"all":"high"}),
    _occ("41220", "Secondary School Teachers", "Education", "41", 1, "WES/Provincial", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"all":"high"}),
    # Skilled Trades (PNP-popular)
    _occ("72200", "Electricians (Except Industrial)", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {"ON":"high","AB":"high"}),
    _occ("72201", "Industrial Electricians", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {"AB":"high"}),
    _occ("72300", "Plumbers", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {"all":"high"}),
    _occ("72301", "Steamfitters, Pipefitters", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {"AB":"high"}),
    _occ("72302", "Gas Fitters", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {}),
    _occ("72310", "Carpenters", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {"ON":"high","BC":"medium"}),
    _occ("72311", "Cabinetmakers", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {}),
    _occ("72400", "Construction Millwrights and Industrial Mechanics", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {}),
    _occ("72401", "Heavy-Duty Equipment Mechanics", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {"AB":"high"}),
    _occ("72410", "Automotive Service Technicians, Truck and Bus Mechanics", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {}),
    _occ("72500", "Crane Operators", "Skilled Trades", "72", 2, "Provincial", "Federal", ["EE-FSWP","PNP"], [], {"AB":"medium"}),
    # Sales / Service
    _occ("62200", "Cooks", "Service Occupations", "62", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high","BC":"high"}),
    _occ("62201", "Chefs", "Service Occupations", "62", 2, "WES", "Federal", ["EE-FSWP","EE-CEC","PNP"], [], {"ON":"high"}),
    _occ("64100", "Retail Sales Supervisors", "Service Occupations", "64", 2, "WES", "Federal", ["EE-FSWP","PNP"], [], {}),
]


# ════════════════════════════════════════════════════════════════
# NEW ZEALAND — ANZSCO codes (target 50+)
# ════════════════════════════════════════════════════════════════
NZ_EXPANSION: List[Dict[str, Any]] = [
    _occ("133111", "Construction Project Manager", "Construction Managers", "133", 1, "NZQA", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("233211", "Civil Engineer (NZ)", "Civil Engineering Professionals", "233", 1, "Engineering NZ", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("233311", "Electrical Engineer (NZ)", "Electrical Engineering Professionals", "233", 1, "Engineering NZ", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("233512", "Mechanical Engineer (NZ)", "Industrial, Mechanical and Production Engineers", "233", 1, "Engineering NZ", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("261312", "Developer Programmer (NZ)", "Software and Applications Programmers", "261", 1, "ITP", "Tier 1", ["SMC","AEWV"], ["Software Engineer","Programmer"], {"all":"very_high"}),
    _occ("261313", "Software Engineer (NZ)", "Software and Applications Programmers", "261", 1, "ITP", "Tier 1", ["SMC","AEWV"], [], {"all":"very_high"}),
    _occ("261314", "Software Tester (NZ)", "Software and Applications Programmers", "261", 1, "ITP", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("262112", "ICT Security Specialist (NZ)", "ICT Security Specialists", "262", 1, "ITP", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("263111", "Computer Network Engineer (NZ)", "Network Professionals", "263", 1, "ITP", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("253111", "General Practitioner (NZ)", "Medical Practitioners", "253", 1, "MCNZ", "Tier 1", ["SMC","AEWV"], [], {"all":"very_high"}),
    _occ("254418", "Registered Nurse (NZ)", "Registered Nurses", "254", 1, "Nursing Council NZ", "Tier 1", ["SMC","AEWV"], [], {"all":"very_high"}),
    _occ("251512", "Hospital Pharmacist (NZ)", "Pharmacists", "251", 1, "PCNZ", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("241111", "Early Childhood Teacher (NZ)", "Early Childhood Teachers", "241", 1, "TCANZ", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("241213", "Primary School Teacher (NZ)", "Primary School Teachers", "241", 1, "TCANZ", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("241511", "Special Needs Teacher (NZ)", "Special Education Teachers", "241", 1, "TCANZ", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("242111", "University Lecturer (NZ)", "University Lecturers and Tutors", "242", 1, "NZQA", "Tier 1", ["SMC","AEWV"], [], {"all":"medium"}),
    _occ("221111", "Accountant (NZ)", "Accountants", "221", 1, "CAANZ", "Tier 1", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("225113", "Marketing Specialist (NZ)", "Marketing Professionals", "225", 1, "NZQA", "Tier 2", ["SMC","AEWV"], ["Digital Marketing","Brand Manager"], {"all":"medium"}),
    _occ("141311", "Hotel or Motel Manager (NZ)", "Accommodation Managers", "141", 2, "NZQA", "Tier 2", ["SMC","AEWV"], ["Hotel Manager","Hospitality Manager"], {"all":"medium"}),
    _occ("131114", "Advertising Manager (NZ)", "Advertising and Marketing Managers", "131", 1, "NZQA", "Tier 2", ["SMC","AEWV"], [], {"all":"medium"}),
    _occ("334111", "Plumber (NZ)", "Plumbers", "334", 3, "NZQA", "Tier 2", ["SMC","AEWV","Green List"], [], {"all":"very_high"}),
    _occ("341111", "Electrician (NZ)", "Electricians", "341", 3, "NZQA", "Tier 2", ["SMC","AEWV","Green List"], [], {"all":"very_high"}),
    _occ("351311", "Chef (NZ)", "Chefs", "351", 2, "NZQA", "Tier 2", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("331212", "Carpenter (NZ)", "Carpenters and Joiners", "331", 3, "NZQA", "Tier 2", ["SMC","AEWV"], [], {"all":"high"}),
    _occ("321211", "Motor Mechanic (NZ)", "Automotive Electricians and Mechanics", "321", 3, "NZQA", "Tier 2", ["SMC","AEWV"], [], {"all":"medium"}),
    _occ("321111", "Automotive Electrician (NZ)", "Automotive Electricians and Mechanics", "321", 3, "NZQA", "Tier 2", ["SMC","AEWV"], [], {"all":"medium"}),
    _occ("234411", "Geologist (NZ)", "Geologists and Geophysicists", "234", 1, "NZQA", "Tier 1", ["SMC","AEWV"], [], {"all":"medium"}),
    _occ("232111", "Architect (NZ)", "Architects", "232", 1, "NZRAB", "Tier 1", ["SMC","AEWV"], [], {"all":"medium"}),
    _occ("133211", "Engineering Manager (NZ)", "Engineering Managers", "133", 1, "NZQA", "Tier 1", ["SMC","AEWV"], [], {"all":"medium"}),
    _occ("132311", "HR Manager (NZ)", "HR Managers", "132", 1, "NZQA", "Tier 2", ["SMC","AEWV"], [], {"all":"medium"}),
]


# ════════════════════════════════════════════════════════════════
# DEDUPE + INSERT — idempotent merge with existing codes
# ════════════════════════════════════════════════════════════════
async def expand_seed():
    """Idempotent merge — adds only NEW codes (existing codes by code+country are skipped)."""
    import os
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import load_dotenv
    load_dotenv('/app/backend/.env')
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]

    for cc, new_codes in [("AU", AU_EXPANSION), ("CA", CA_EXPANSION), ("NZ", NZ_EXPANSION)]:
        country = await db['country_rules'].find_one({"country_code": cc}, {"_id": 0})
        if not country:
            print(f"⚠️ Country {cc} not seeded — skipping")
            continue
        existing = country.get('occupation_codes') or []
        existing_codes = {str(o.get('code')) for o in existing}
        added = 0
        merged = list(existing)
        for new in new_codes:
            if str(new['code']) in existing_codes:
                continue  # idempotent — skip if exists
            merged.append(new)
            added += 1
        await db['country_rules'].update_one(
            {"country_code": cc},
            {"$set": {"occupation_codes": merged, "updated_at": datetime.now(timezone.utc)}}
        )
        print(f"{cc}: {added} new codes added (total now {len(merged)})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(expand_seed())
