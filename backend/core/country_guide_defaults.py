"""Phase 8 / 7.3 — Curated Country Guide Defaults (AU, CA, NZ, UK, USA).

Provides complete, verified markdown content and FAQs for all 7 standard sections:
  1. Country Overview
  2. PR Pathways
  3. Eligibility Snapshot
  4. Fees & Costs
  5. Processing Timeline
  6. Pros & Cons
  7. Settlement & Life After PR
  + Frequently Asked Questions

Used whenever live DB content has not yet been edited or verified by admin,
ensuring every generated assessment report renders the full 3-page Country Guide.
"""
from typing import Dict, Any, List

CURATED_COUNTRY_GUIDES: Dict[str, Dict[str, Any]] = {
    "AU": {
        "country_code": "AU",
        "country_name": "Australia",
        "flag": "🇦🇺",
        "tagline": "Skilled Migration to the Land Down Under",
        "hero": {
            "title": "🇦🇺 Australia",
            "subtitle": "Skilled Migration to the Land Down Under",
            "image_url": None,
        },
        "sections": [
            {
                "key": "overview",
                "title": "Country Overview",
                "body_markdown": (
                    "Australia offers one of the world's most transparent, merit-based points-tested immigration systems. "
                    "Renowned for its high standard of living, world-class healthcare, clean environment, and strong economy, "
                    "Australia continues to attract ambitious skilled professionals and families from around the globe.\n\n"
                    "Permanent residents enjoy unrestricted rights to live, work, and study anywhere in the country, with access to "
                    "Australia's universal healthcare system (Medicare) from day one and high-quality free government schooling for children."
                ),
            },
            {
                "key": "pr_pathways",
                "title": "PR Pathways",
                "body_markdown": (
                    "- **Subclass 189 (Skilled Independent):** Direct, independent Permanent Residency. Requires no employer or state sponsorship. Complete freedom to settle anywhere in Australia.\n"
                    "- **Subclass 190 (Skilled Nominated):** State/Territory nominated Permanent Residency. Awards +5 bonus points toward your overall points score with a 2-year state settlement commitment.\n"
                    "- **Subclass 491 (Skilled Work Regional):** 5-year provisional pathway for regional Australia. Awards +15 bonus points, leading to direct Permanent Residency (Subclass 191) after 3 years of living and working in designated regional areas.\n"
                    "- **Subclass 186 (Employer Nomination Scheme):** Direct permanent residency sponsored by an Australian employer for high-demand occupations."
                ),
            },
            {
                "key": "eligibility",
                "title": "Eligibility Snapshot",
                "body_markdown": (
                    "- **Minimum Points Score:** 65 points on the Department of Home Affairs statutory points test.\n"
                    "- **Age Limit:** Must be under 45 years of age at the time of receiving an Invitation to Apply (ITA).\n"
                    "- **English Language:** Competent English minimum (IELTS 6.0 / PTE 50+); Proficient (IELTS 7.0 / PTE 65+) awards 10 points; Superior (IELTS 8.0 / PTE 79+) awards 20 points.\n"
                    "- **Skill Assessment:** Positive outcome from the designated assessing authority (ACS, Engineers Australia, VETASSESS, TRA, CPA/CAANZ, ANMAC)."
                ),
            },
            {
                "key": "fees",
                "title": "Fees & Costs",
                "body_markdown": (
                    "- **Assessing Authority Fee:** AUD 500 – AUD 1,500 (dependent on specific assessing body and fast-track options).\n"
                    "- **Primary Applicant Visa Fee:** AUD 4,765 (statutory Department of Home Affairs fee).\n"
                    "- **Secondary Applicant (Spouse):** AUD 2,385.\n"
                    "- **Dependent Child:** AUD 1,195 per child under 18 years.\n"
                    "- **Third-Party Costs:** English Test (PTE/IELTS) ~₹17,000; Medical Examination & Police Clearance ~₹10,000 per adult."
                ),
            },
            {
                "key": "timeline",
                "title": "Processing Timeline",
                "body_markdown": (
                    "- **Stage 1 (Skill Assessment):** 4 to 12 weeks from submission to positive outcome.\n"
                    "- **Stage 2 (EOI & Nomination):** 1 to 6 months depending on points band and invitation round frequency.\n"
                    "- **Stage 3 (Visa Lodgement to Grant):** 6 to 12 months following formal Invitation to Apply (ITA)."
                ),
            },
            {
                "key": "pros_cons",
                "title": "Pros & Cons",
                "body_markdown": (
                    "- **Advantages:** Direct permanent residency from arrival, world-class Medicare coverage, high minimum wage and strong salaries, pathway to citizenship after 4 years.\n"
                    "- **Key Considerations:** High competitive points cutoffs for popular occupations (Software Engineering, Accounting), regional living commitment required for Subclass 491 holders."
                ),
            },
            {
                "key": "settlement",
                "title": "Settlement & Life After PR",
                "body_markdown": (
                    "Upon visa grant, permanent residents receive unrestricted work rights, access to Medicare, interest-free government student loan schemes (HELP) for higher studies, "
                    "and eligibility to purchase residential property without foreign buyer duties. After 4 years of lawful residence, you can apply for Australian Citizenship and obtain an Australian passport."
                ),
            },
        ],
        "faq": [
            {
                "question": "What is the minimum pass mark for Australian Skilled Migration?",
                "answer": "The statutory minimum threshold is 65 points. However, invitation cutoffs vary by occupation demand; competitive IT and Engineering roles typically invite at 75-85+ points.",
            },
            {
                "question": "Can my spouse add points to my Australian PR application?",
                "answer": "Yes! A skilled spouse with a positive skill assessment and Competent English awards +10 points. If your spouse has Competent English alone, they add +5 points. Single applicants automatically receive +10 points.",
            },
            {
                "question": "Do I need a job offer to apply for Australian PR?",
                "answer": "No. General Skilled Migration (Subclasses 189, 190, and 491) does not require a pre-existing job offer or employer sponsorship.",
            },
            {
                "question": "What is the difference between Subclass 190 and Subclass 491?",
                "answer": "Subclass 190 is a direct Permanent Residency visa with +5 state nomination points. Subclass 491 is a 5-year provisional visa with +15 regional points that converts to permanent residency (Subclass 191) after 3 years.",
            },
        ],
    },
    "CA": {
        "country_code": "CA",
        "country_name": "Canada",
        "flag": "🇨🇦",
        "tagline": "Permanent Residency through Express Entry & PNP",
        "hero": {
            "title": "🇨🇦 Canada",
            "subtitle": "Permanent Residency through Express Entry & PNP",
            "image_url": None,
        },
        "sections": [
            {
                "key": "overview",
                "title": "Country Overview",
                "body_markdown": (
                    "Canada is internationally recognized as one of the most welcoming, progressive, and multicultural nations. "
                    "Through its economic immigration programs, Canada offers skilled immigrants direct permanent resident status with full access to "
                    "universal healthcare, exceptional public education, and safe, vibrant communities across all provinces."
                ),
            },
            {
                "key": "pr_pathways",
                "title": "PR Pathways",
                "body_markdown": (
                    "- **Express Entry (Federal Skilled Worker - FSW):** Flagship economic points system ranking candidates via the Comprehensive Ranking System (CRS).\n"
                    "- **Provincial Nominee Programs (PNP):** Province-specific nominations (Ontario OINP, BC PNP, Alberta AAIP, etc.) that grant a massive +600 points boost in Express Entry.\n"
                    "- **Category-Based Express Entry Draws:** Targeted selection rounds for Tech, Healthcare, STEM, Trades, and French-language speakers.\n"
                    "- **Atlantic Immigration Program (AIP):** Employer-driven fast-track pathway for the 4 Atlantic provinces."
                ),
            },
            {
                "key": "eligibility",
                "title": "Eligibility Snapshot",
                "body_markdown": (
                    "- **67-Point Selection Grid:** Must score 67/100 points on the FSW selection grid (Age, Education, Experience, Language, Arranged Employment, Adaptability).\n"
                    "- **Educational Credential Assessment (ECA):** Verification of foreign degrees through WES, IQAS, or ICAS.\n"
                    "- **Language Benchmark:** Minimum CLB 7 in English (IELTS General: 6.0 in all bands or CELPIP 7+).\n"
                    "- **Skilled Experience:** Minimum 1 continuous year of skilled work experience under TEER 0, 1, 2, or 3."
                ),
            },
            {
                "key": "fees",
                "title": "Fees & Costs",
                "body_markdown": (
                    "- **Primary Applicant PR Processing Fee:** CAD 1,525 (includes CAD 950 processing + CAD 575 Right of Permanent Residence Fee).\n"
                    "- **Spouse / Common-Law Partner:** CAD 1,525.\n"
                    "- **Dependent Child:** CAD 260 per child.\n"
                    "- **ECA Verification:** ~CAD 240 – CAD 300 (WES/IQAS).\n"
                    "- **Settlement Funds (Proof of Funds):** ~CAD 14,690 for a single applicant (exempt if working in Canada with valid job offer)."
                ),
            },
            {
                "key": "timeline",
                "title": "Processing Timeline",
                "body_markdown": (
                    "- **Stage 1 (ECA & Language Test):** 4 to 8 weeks.\n"
                    "- **Stage 2 (Express Entry Pool Entry & PNP):** 1 to 6 months.\n"
                    "- **Stage 3 (Post-ITA PR Processing):** Standard 6-month processing service standard by IRCC."
                ),
            },
            {
                "key": "pros_cons",
                "title": "Pros & Cons",
                "body_markdown": (
                    "- **Advantages:** Direct permanent residency from day one, universal healthcare, Canada Child Benefit (CCB) financial support, fast pathway to Canadian Citizenship (3 years out of 5).\n"
                    "- **Key Considerations:** High CRS score cutoffs in general draws, cold winter weather in central and prairie provinces."
                ),
            },
            {
                "key": "settlement",
                "title": "Settlement & Life After PR",
                "body_markdown": (
                    "Permanent residents receive a PR Card upon landing, enroll in provincial health insurance (OHIP, MSP, AHCIP), "
                    "obtain a Social Insurance Number (SIN), and can work for any Canadian employer without restriction."
                ),
            },
        ],
        "faq": [
            {
                "question": "What is the difference between FSW 67 points and CRS score?",
                "answer": "The 67-point grid is the entry gate to be eligible for Express Entry. Once eligible, your profile enters the Express Entry pool and is ranked using the 1,200-point Comprehensive Ranking System (CRS).",
            },
            {
                "question": "How can I increase my CRS score for Express Entry?",
                "answer": "Key boosters include achieving maximum language scores (CLB 9+), securing a Provincial Nomination (+600 points), completing a secondary credential or Master's degree, or learning French as a second language.",
            },
            {
                "question": "Is a job offer mandatory for Canadian PR?",
                "answer": "No. A Canadian job offer is not mandatory under Express Entry FSW. However, a valid LMIA-approved job offer can add 50 to 200 CRS points.",
            },
        ],
    },
    "NZ": {
        "country_code": "NZ",
        "country_name": "New Zealand",
        "flag": "🇳🇿",
        "tagline": "Skilled Migrant Category to Aotearoa",
        "hero": {
            "title": "🇳🇿 New Zealand",
            "subtitle": "Skilled Migrant Category to Aotearoa",
            "image_url": None,
        },
        "sections": [
            {
                "key": "overview",
                "title": "Country Overview",
                "body_markdown": (
                    "New Zealand offers an enviable quality of life, safe communities, outstanding work-life balance, and scenic landscapes. "
                    "Immigration New Zealand operates a streamlined 6-Point Skilled Migrant Category (SMC) providing a direct pathway to permanent residence."
                ),
            },
            {
                "key": "pr_pathways",
                "title": "PR Pathways",
                "body_markdown": (
                    "- **Skilled Migrant Category (6-Point SMC):** Points claimed from New Zealand occupational registration, recognized qualification (Master's/PhD), or high income.\n"
                    "- **Green List Straight to Residence:** Immediate residence for Tier 1 occupations (Engineers, Doctors, ICT Specialists) with an accredited employer job offer.\n"
                    "- **Green List Work to Residence:** Residence after 2 years of working in a Tier 2 Green List role."
                ),
            },
            {
                "key": "eligibility",
                "title": "Eligibility Snapshot",
                "body_markdown": (
                    "- **Points Required:** Exactly 6 points from recognized skill criteria.\n"
                    "- **Job Offer:** An offer of full-time skilled employment from an Accredited Employer in NZ paying at or above the median wage.\n"
                    "- **Age Limit:** Must be 55 years of age or younger.\n"
                    "- **English Requirement:** Minimum IELTS 6.5 overall (or equivalent PTE/TOEFL score)."
                ),
            },
            {
                "key": "fees",
                "title": "Fees & Costs",
                "body_markdown": (
                    "- **SMC Application Fee:** NZD 4,290 (includes statutory immigration levy).\n"
                    "- **NZQA Qualifications Assessment (IQA):** ~NZD 745.\n"
                    "- **Medical & Police Clearance:** ~₹12,000 per applicant."
                ),
            },
            {
                "key": "timeline",
                "title": "Processing Timeline",
                "body_markdown": (
                    "- **Stage 1 (NZQA Assessment):** 4 to 6 weeks.\n"
                    "- **Stage 2 (Job Offer / Accreditation):** 1 to 3 months.\n"
                    "- **Stage 3 (SMC Residence Processing):** 4 to 8 months."
                ),
            },
            {
                "key": "pros_cons",
                "title": "Pros & Cons",
                "body_markdown": (
                    "- **Advantages:** Clean environment, direct residence for Green List roles, peaceful lifestyle, Australian work privileges after obtaining NZ citizenship.\n"
                    "- **Key Considerations:** Skilled job offer in NZ is a mandatory requirement for SMC residence."
                ),
            },
            {
                "key": "settlement",
                "title": "Settlement & Life After PR",
                "body_markdown": (
                    "New Zealand residents receive subsidized public healthcare, domestic tuition fees for university education, and can transition to Permanent Resident Visa (PRV) status after 2 years with no further travel conditions."
                ),
            },
        ],
        "faq": [
            {
                "question": "What is the 6-point system for New Zealand?",
                "answer": "Under the new SMC, you need 6 points which can come from NZ professional registration (3-6 pts), recognized overseas qualification like a Master's (5 pts) or PhD (6 pts), or high income (3-6 pts), plus 1 pt per year of NZ skilled work experience.",
            },
            {
                "question": "What is the Green List in New Zealand?",
                "answer": "The Green List contains high-demand occupations in Healthcare, Engineering, and ICT. Tier 1 roles offer Straight to Residence without waiting, while Tier 2 roles offer Work to Residence after 24 months.",
            },
        ],
    },
    "UK": {
        "country_code": "UK",
        "country_name": "United Kingdom",
        "flag": "🇬🇧",
        "tagline": "Skilled Worker & Global Talent Routes",
        "hero": {
            "title": "🇬🇧 United Kingdom",
            "subtitle": "Skilled Worker & Global Talent Routes",
            "image_url": None,
        },
        "sections": [
            {
                "key": "overview",
                "title": "Country Overview",
                "body_markdown": (
                    "The United Kingdom is a global financial, technological, and cultural powerhouse. "
                    "Its Points-Based Immigration System provides direct pathways for skilled talent, innovators, and specialists to live and build long-term careers in the UK."
                ),
            },
            {
                "key": "pr_pathways",
                "title": "PR Pathways",
                "body_markdown": (
                    "- **Skilled Worker Visa:** Points-tested visa requiring a Certificate of Sponsorship (CoS) from a licensed UK sponsor in an eligible SOC occupation.\n"
                    "- **Global Talent Visa:** Prestigious unsponsored route for leaders and emerging leaders in Tech Nation, Science, Research, and Arts.\n"
                    "- **Scale-up Worker Visa:** Fast-track route for professionals joining high-growth UK scale-up enterprises.\n"
                    "- **High Potential Individual (HPI):** 2-3 year open work visa for recent graduates of top-ranked global universities."
                ),
            },
            {
                "key": "eligibility",
                "title": "Eligibility Snapshot",
                "body_markdown": (
                    "- **Points Required:** 70 points under the Points-Based System (Job Offer at RQF Level 3+ = 20 pts, English B1 = 10 pts, Salary threshold = 20 pts, tradeable points = 20 pts).\n"
                    "- **English Level:** CEFR B1 level minimum (IELTS 4.0 in each band or degree taught in English).\n"
                    "- **Minimum Salary:** Must meet the general salary threshold or the occupation-specific going rate."
                ),
            },
            {
                "key": "fees",
                "title": "Fees & Costs",
                "body_markdown": (
                    "- **Visa Application Fee:** £719 to £1,500 (depending on visa duration and shortage occupation status).\n"
                    "- **Immigration Health Surcharge (IHS):** £1,035 per year of visa duration.\n"
                    "- **TB Test & Biometrics:** ~₹5,000 per applicant."
                ),
            },
            {
                "key": "timeline",
                "title": "Processing Timeline",
                "body_markdown": (
                    "- **Stage 1 (Sponsorship / Endorsement):** 1 to 4 weeks.\n"
                    "- **Stage 2 (Visa Application):** 3 weeks standard (5-day priority processing available).\n"
                    "- **Stage 3 (Settlement / ILR):** Eligible for Indefinite Leave to Remain after 5 continuous years (or 3 years under Global Talent)."
                ),
            },
            {
                "key": "pros_cons",
                "title": "Pros & Cons",
                "body_markdown": (
                    "- **Advantages:** Proximity to European and global markets, NHS healthcare access, premier universities, direct route to permanent settlement (ILR).\n"
                    "- **Key Considerations:** Upfront Immigration Health Surcharge (IHS) costs, requirement of a licensed UK employer sponsor."
                ),
            },
            {
                "key": "settlement",
                "title": "Settlement & Life After PR",
                "body_markdown": (
                    "After 5 years of lawful residence, holders obtain Indefinite Leave to Remain (ILR), removing all visa restrictions. British Citizenship can be acquired 12 months after receiving ILR."
                ),
            },
        ],
        "faq": [
            {
                "question": "What is a Certificate of Sponsorship (CoS)?",
                "answer": "A CoS is an electronic record generated by a UK Home Office licensed employer confirming that you have been offered a genuine skilled job meeting salary and skill requirements.",
            },
            {
                "question": "Can my family join me in the UK?",
                "answer": "Yes! Dependent partners and children under 18 can accompany Skilled Worker and Global Talent visa holders with full work and study rights in the UK.",
            },
        ],
    },
    "USA": {
        "country_code": "USA",
        "country_name": "United States",
        "flag": "🇺🇸",
        "tagline": "H1B, EB-2 NIW & Green Card Pathways",
        "hero": {
            "title": "🇺🇸 United States",
            "subtitle": "H1B, EB-2 NIW & Green Card Pathways",
            "image_url": None,
        },
        "sections": [
            {
                "key": "overview",
                "title": "Country Overview",
                "body_markdown": (
                    "The United States is the world's leading technology, commercial, and research destination. "
                    "For highly skilled professionals, entrepreneurs, and researchers, the US immigration system provides specialized immigrant and non-immigrant pathways."
                ),
            },
            {
                "key": "pr_pathways",
                "title": "PR Pathways",
                "body_markdown": (
                    "- **EB-2 National Interest Waiver (NIW):** Self-petitioned Green Card route for professionals with advanced degrees or exceptional ability whose work has substantial national importance — no employer or labor certification needed.\n"
                    "- **EB-1A (Extraordinary Ability):** Green Card route for individuals with recognized acclaim in sciences, business, or education.\n"
                    "- **H-1B Specialty Occupation:** Employer-sponsored work visa for professional roles requiring bachelor's or master's degrees.\n"
                    "- **L-1 Intra-Company Transfer:** Transfer for multinational executives, managers, and specialized knowledge employees."
                ),
            },
            {
                "key": "eligibility",
                "title": "Eligibility Snapshot",
                "body_markdown": (
                    "- **EB-2 NIW Criteria:** Advanced degree (Master's or Bachelor's + 5 years progressive experience) + meeting the three-prong Dhanasar legal test (substantial merit, well-positioned to advance endeavor, national benefit to waive labor cert).\n"
                    "- **H-1B Criteria:** Bachelor's degree equivalent in a specific specialty occupation with an approved Labor Condition Application (LCA)."
                ),
            },
            {
                "key": "fees",
                "title": "Fees & Costs",
                "body_markdown": (
                    "- **Form I-140 Immigrant Petition:** USD 715 + Asylum Program Fee USD 300 – USD 600.\n"
                    "- **Premium Processing (Optional):** USD 2,805 (guarantees 45-day adjudication).\n"
                    "- **Adjustment of Status (I-485):** USD 1,440 per adult."
                ),
            },
            {
                "key": "timeline",
                "title": "Processing Timeline",
                "body_markdown": (
                    "- **I-140 Adjudication:** 45 days (with Premium Processing) or 4 to 8 months standard.\n"
                    "- **Priority Date & Green Card Issuance:** Varies based on Visa Bulletin priority dates and country of birth."
                ),
            },
            {
                "key": "pros_cons",
                "title": "Pros & Cons",
                "body_markdown": (
                    "- **Advantages:** Highest global tech and professional compensation, ability to self-petition under EB-2 NIW without employer lock-in, unparalleled entrepreneurial ecosystem.\n"
                    "- **Key Considerations:** Annual H-1B lottery cap, Visa Bulletin wait times for specific countries of birth."
                ),
            },
            {
                "key": "settlement",
                "title": "Settlement & Life After PR",
                "body_markdown": (
                    "Permanent Residents (Green Card holders) enjoy permanent work and residence rights throughout the US, access to federal grants and financial aid, and can apply for US Citizenship after 5 years."
                ),
            },
        ],
        "faq": [
            {
                "question": "What is the EB-2 National Interest Waiver (NIW)?",
                "answer": "The EB-2 NIW is a self-petitioned Green Card category that allows advanced degree professionals or individuals with exceptional ability to apply directly without an employer sponsor or labor certification.",
            },
            {
                "question": "Can I apply for EB-2 NIW from outside the United States?",
                "answer": "Yes! EB-2 NIW petitions can be filed directly from India or any country through consular processing at the US Embassy once approved.",
            },
        ],
    },
}


def get_curated_country_guide(country_code: str) -> Dict[str, Any]:
    """Retrieve curated default guide for a normalized country code."""
    cc = (country_code or "AU").upper().strip()
    if cc in ("AUSTRALIA", "AU"):
        return dict(CURATED_COUNTRY_GUIDES["AU"])
    elif cc in ("CANADA", "CA"):
        return dict(CURATED_COUNTRY_GUIDES["CA"])
    elif cc in ("NEW ZEALAND", "NZ"):
        return dict(CURATED_COUNTRY_GUIDES["NZ"])
    elif cc in ("UNITED KINGDOM", "UK", "GB"):
        return dict(CURATED_COUNTRY_GUIDES["UK"])
    elif cc in ("UNITED STATES", "UNITED STATES OF AMERICA", "USA", "US"):
        return dict(CURATED_COUNTRY_GUIDES["USA"])
    return dict(CURATED_COUNTRY_GUIDES.get(cc, CURATED_COUNTRY_GUIDES["AU"]))
