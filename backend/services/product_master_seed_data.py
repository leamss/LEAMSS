"""Canonical Statutory Data & Seed Generator for Product Master Hub.

Populates verified, canonical records for key destination countries (Australia, Canada,
UK, Germany, USA, New Zealand) with complete statutory criteria, official forms,
timeline workflows, government costs, pricing milestones, and sales playbooks.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

CANONICAL_SEEDS: List[Dict[str, Any]] = [
    # ──────────────────────────────────────────────────────────────────────────
    # AUSTRALIA
    # ──────────────────────────────────────────────────────────────────────────
    {
        "id": "pm_australia_189",
        "name": "Skilled Independent Visa (Subclass 189)",
        "country": "Australia",
        "country_code": "AU",
        "flag": "🇦🇺",
        "category": "skilled_migration",
        "visa_type": "Permanent Residency (Points-Tested)",
        "visa_subclass": "189",
        "status": "active",
        "authority_name": "Department of Home Affairs (DHA)",
        "official_portal_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "migrate_page_url": "https://leamss.com/migrate",
        "official_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189",
            "https://immi.homeaffairs.gov.au/visas/working-in-australia/skillselect",
        ],
        "summary": "Permanent residency visa for invited skilled workers with eligible occupations on the Medium and Long-term Strategic Skills List (MLTSSL). No state or employer sponsorship required.",
        "description": "The Subclass 189 is an independent, points-tested permanent visa allowing skilled individuals and their eligible family members to live, work, and study anywhere in Australia indefinitely with full Medicare healthcare and Australian citizenship pathway after 4 years.",
        "eligibility_criteria": {
            "age_min": 18,
            "age_max": 44,
            "minimum_qualification": "Bachelor Degree or Higher (comparable to Australian AQF Level 7/8/9/10)",
            "work_experience_years": 3,
            "english_requirements": {
                "competency_level": "Competent English (minimum IELTS 6.0 in each band / PTE Academic 50)",
                "ielts_overall": 6.0,
                "pte_overall": 50,
                "toefl_overall": 64,
                "validity_years": 3,
                "exemptions": "Passport holders of UK, USA, Canada, NZ, Ireland"
            },
            "skills_assessment_authority": "ACS (IT), Engineers Australia, VETASSESS, CPA/CA ANZ (Accounting)",
            "anzsco_code": "261313 (Software Engineer) / 261312 (Developer Programmer) / 233512 (Mech Eng)",
            "points_based": {
                "is_points_tested": True,
                "minimum_points": 65,
                "competitive_target_points": 85,
                "scoring_factors": [
                    {"factor": "Age (25-32 years)", "points": 30},
                    {"factor": "English (Proficient - IELTS 7.0 / PTE 65)", "points": 10},
                    {"factor": "English (Superior - IELTS 8.0 / PTE 79)", "points": 20},
                    {"factor": "Overseas Work Experience (3-4 years)", "points": 5},
                    {"factor": "Overseas Work Experience (5-7 years)", "points": 10},
                    {"factor": "Overseas Work Experience (8+ years)", "points": 15},
                    {"factor": "Educational Qualification (Bachelor / Master)", "points": 15},
                    {"factor": "Doctoral Degree (PhD)", "points": 20},
                    {"factor": "Single Applicant or Partner with Competent English", "points": 10},
                    {"factor": "Partner with positive Skills Assessment", "points": 10},
                    {"factor": "NAATI CCL Credentialed Community Language", "points": 5}
                ]
            },
            "settlement_funds_required": "AUD 25,000 - AUD 35,000 (Recommended living allowance for first 6 months)",
            "health_character_mandatory": True
        },
        "visa_conditions": [
            "Condition 8501: Maintain adequate health insurance until Medicare enrollment",
            "Condition 8515: Must not marry or enter into a de facto relationship before initial entry"
        ],
        "government_costs": {
            "currency": "AUD",
            "primary_applicant": 4770.0,
            "secondary_applicant": 2385.0,
            "child_applicant": 1195.0,
            "effective_date": "2024-07-01",
            "source_link": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/fees-and-charges/current-visa-pricing",
            "line_items": [
                {"name": "Base Application Charge (Primary Applicant)", "amount": 4770, "currency": "AUD"},
                {"name": "Additional Applicant Charge (18 and over)", "amount": 2385, "currency": "AUD"},
                {"name": "Additional Applicant Charge (Under 18)", "amount": 1195, "currency": "AUD"},
                {"name": "Skills Assessment Fee (ACS / EA / VETASSESS)", "amount": 550, "currency": "AUD"},
                {"name": "Second Installment (if functional English not met)", "amount": 4885, "currency": "AUD"}
            ]
        },
        "pricing": {
            "base_fee": 15000000,  # 1,50,000 INR in paise
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 500000,
            "agent_commission": 300000,
            "milestones": [
                {"stage_number": 1, "name": "Enrollment & Skills Assessment Dossier", "percentage": 40, "amount_paise": 6000000},
                {"stage_number": 2, "name": "EOI Submission & State Filing", "percentage": 30, "amount_paise": 4500000},
                {"stage_number": 3, "name": "DHA Visa Application Lodgement & Grant Delivery", "percentage": 30, "amount_paise": 4500000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "6 to 12 months",
            "stages": [
                {"stage_order": 1, "stage_name": "Skills Assessment Lodgement", "duration_days": 45, "description": "Prepare employment evidence, reference letters, academic transcripts and lodge with assessing authority."},
                {"stage_order": 2, "stage_name": "English Test & SkillSelect EOI", "duration_days": 15, "description": "Achieve target PTE/IELTS benchmark and file Expression of Interest on SkillSelect."},
                {"stage_order": 3, "stage_name": "Invitation to Apply (ITA) Receipt", "duration_days": 60, "description": "DHA invitation round issuance (valid for 60 calendar days to lodge final application)."},
                {"stage_order": 4, "stage_name": "DHA Visa Lodgement & Statutory Forms", "duration_days": 30, "description": "Lodge online visa via ImmiAccount including Form 80 and Form 1221."},
                {"stage_order": 5, "stage_name": "Biometrics, Health (Form 26) & PCC", "duration_days": 21, "description": "Complete panel clinic medicals and biometric capture at VFS."},
                {"stage_order": 6, "stage_name": "Case Officer Assessment & PR Grant", "duration_days": 120, "description": "DHA assessment, verification checks, and final Permanent Residency Grant letter."}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Form 80 - Personal Particulars for Assessment", "category": "Statutory Government Form", "form_code": "Form 80", "applicant_scope": "both", "is_mandatory": True, "description": "Detailed 18-page character and travel history declaration."},
            {"id": str(uuid.uuid4()), "document_name": "Form 1221 - Additional Personal Particulars Information", "category": "Statutory Government Form", "form_code": "Form 1221", "applicant_scope": "both", "is_mandatory": True, "description": "Supplementary background form for security assessment."},
            {"id": str(uuid.uuid4()), "document_name": "Form 26 - Medical Examination", "category": "Health Examination", "form_code": "Form 26", "applicant_scope": "all_family", "is_mandatory": True, "description": "Completed by Bupa Medical / eMedical approved panel physician."},
            {"id": str(uuid.uuid4()), "document_name": "Positive Skills Assessment Outcome Letter", "category": "Skills Assessment", "form_code": "MSA", "applicant_scope": "primary_applicant", "is_mandatory": True, "description": "Official assessment letter from ACS, Engineers Australia, or VETASSESS."},
            {"id": str(uuid.uuid4()), "document_name": "English Language Test Scorecard (PTE / IELTS)", "category": "Language Proficiency", "form_code": "TRF", "applicant_scope": "primary_applicant", "is_mandatory": True, "description": "Scorecard valid within 3 years of visa invitation date."},
            {"id": str(uuid.uuid4()), "document_name": "Police Clearance Certificate (PCC) from Passport Office", "category": "Character Verification", "form_code": "PCC", "applicant_scope": "both", "is_mandatory": True, "description": "Regional Passport Office PCC for all countries lived in 12+ months in past 10 years."},
            {"id": str(uuid.uuid4()), "document_name": "Employment Reference Letters & Tax Filings (ITR / Form 16)", "category": "Work Experience Proof", "form_code": "EXP", "applicant_scope": "primary_applicant", "is_mandatory": True, "description": "Detailed roles and responsibilities on company letterhead with salary slips and Form 16."}
        ],
        "sales_playbook": {
            "elevator_pitch": "Subclass 189 is Australia's gold standard direct permanent residency visa. No employer lock-in, no state restrictions — you and your family can live, work, and access Medicare healthcare anywhere in Australia immediately upon arrival.",
            "target_client": "Skilled tech, engineering, healthcare and finance professionals aged 25-39 with 3+ years experience, a Bachelor's degree, and strong English proficiency.",
            "pitch_points": [
                "Direct Unconditional Permanent Residency from day one",
                "Full Medicare healthcare coverage for primary and dependents",
                "Free world-class public schooling for children",
                "Clear pathway to Australian Citizenship and passport after 4 years",
                "Right to work for any employer across Australia without visa sponsorship"
            ],
            "discovery_questions": [
                "What is your highest educational qualification and current job title?",
                "How many years of paid post-qualification experience do you have?",
                "Have you taken IELTS or PTE Academic recently? What were your section scores?",
                "Are you planning to migrate individually or with a spouse and children?",
                "Is your occupation listed on the MLTSSL medium and long-term skills list?"
            ],
            "upselling_pathways": [
                "Add-on: NAATI CCL Credentialed Community Language coaching (+5 points)",
                "Add-on: Professional Year / PTE Superior Score Accelerator (+10 points)",
                "Add-on: Spouse Skills Assessment preparation (+5 to +10 points)",
                "Add-on: Settlement Concierge, Tax File Number (TFN) & Bank Setup"
            ],
            "red_flags": [
                "Age 45 or older (statutory cutoff by Department of Home Affairs)",
                "Non-declared criminal conviction or immigration refusal in any Five Eyes country",
                "Unrecognized distance education degree lacking required credits"
            ]
        },
        "objections_rebuttals": [
            {
                "objection": "The minimum 65 points is too competitive; I heard 85+ points is needed for tech.",
                "rebuttal": "That's why our strategy includes optimizing your profile: PTE Superior gives you 20 points, partner skills add 10 points, and NAATI adds 5 points. We also dual-file Subclass 190 state nominations simultaneously so you maximize invitations.",
                "probability": "High"
            },
            {
                "objection": "Australia PR takes too long compared to European work permits.",
                "rebuttal": "A work permit binds you to one employer who controls your stay. Subclass 189 gives you permanent status, Medicare, and complete employment freedom from day one.",
                "probability": "Medium"
            }
        ],
        "faqs": [
            {"question": "Can I bring my spouse and dependent children under Subclass 189?", "answer": "Yes. All dependent family members are granted identical Permanent Residency status with Medicare and work rights."},
            {"question": "How long is the initial visa valid?", "answer": "The initial travel facility is valid for 5 years, after which a Resident Return Visa (Subclass 155) is issued if residency requirements are met."}
        ]
    },

    {
        "id": "pm_australia_190",
        "name": "Skilled Nominated Visa (Subclass 190)",
        "country": "Australia",
        "country_code": "AU",
        "flag": "🇦🇺",
        "category": "skilled_migration",
        "visa_type": "Permanent Residency (State Nominated)",
        "visa_subclass": "190",
        "status": "active",
        "authority_name": "Department of Home Affairs (DHA) & State Governments",
        "official_portal_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-nominated-190",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Permanent residency visa requiring nomination by an Australian State or Territory government (NSW, VIC, QLD, WA, SA, TAS, ACT, NT). Adds 5 bonus points to your points score.",
        "description": "Subclass 190 grants immediate permanent residency to skilled professionals nominated by an Australian state government. In exchange, the applicant commits to living and working in that state for the first 2 years.",
        "eligibility_criteria": {
            "age_min": 18,
            "age_max": 44,
            "minimum_qualification": "Bachelor Degree or Higher (comparable AQF Level 7+)",
            "work_experience_years": 3,
            "english_requirements": {"competency_level": "Competent English (IELTS 6.0 / PTE 50)", "ielts_overall": 6.0, "pte_overall": 50},
            "skills_assessment_authority": "ACS, Engineers Australia, VETASSESS, ANMAC",
            "anzsco_code": "Any eligible occupation on State Migration Occupation List",
            "points_based": {"is_points_tested": True, "minimum_points": 65, "state_bonus_points": 5},
            "settlement_funds_required": "AUD 30,000 - AUD 45,000 (State specific financial commitment)",
            "health_character_mandatory": True
        },
        "visa_conditions": ["Commitment to reside in nominating state for 2 years post-arrival"],
        "government_costs": {
            "currency": "AUD",
            "primary_applicant": 4770.0,
            "secondary_applicant": 2385.0,
            "child_applicant": 1195.0,
            "source_link": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/fees-and-charges/current-visa-pricing",
            "line_items": [
                {"name": "DHA Base Application Charge", "amount": 4770, "currency": "AUD"},
                {"name": "State Nomination Filing Fee (e.g. NSW / VIC)", "amount": 330, "currency": "AUD"}
            ]
        },
        "pricing": {
            "base_fee": 16000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 550000,
            "agent_commission": 350000,
            "milestones": [
                {"stage_number": 1, "name": "Skills Assessment & State Alignment", "percentage": 40, "amount_paise": 6400000},
                {"stage_number": 2, "name": "State ROI / Nomination Approval", "percentage": 30, "amount_paise": 4800000},
                {"stage_number": 3, "name": "DHA Lodgement & PR Issuance", "percentage": 30, "amount_paise": 4800000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "6 to 9 months",
            "stages": [
                {"stage_order": 1, "stage_name": "Skills Assessment Verification", "duration_days": 45, "description": "Assess academic and work experience credentials."},
                {"stage_order": 2, "stage_name": "EOI & State Registration of Interest (ROI)", "duration_days": 30, "description": "Target highest invitation state for your specific ANZSCO code."},
                {"stage_order": 3, "stage_name": "State Nomination Grant (+5 Points)", "duration_days": 45, "description": "State issues formal nomination adding 5 points."},
                {"stage_order": 4, "stage_name": "DHA Lodgement & Medicals (Form 80/26)", "duration_days": 60, "description": "Final visa application with statutory forms."},
                {"stage_order": 5, "stage_name": "PR Grant Delivery", "duration_days": 90, "description": "Permanent residency granted."}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Form 80 - Personal Particulars", "category": "Statutory Government Form", "form_code": "Form 80", "applicant_scope": "both", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "State Nomination Commitment Declaration", "category": "State Statutory Form", "form_code": "ROI-DECL", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Skills Assessment Positive Outcome", "category": "Assessment", "form_code": "MSA", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Subclass 190 gives you the 5 extra points you need through state government backing, securing direct permanent residency in booming economic regions like Victoria, New South Wales, or Western Australia.",
            "target_client": "Professionals sitting at 75-80 points who need the state nomination bonus to guarantee an ITA.",
            "pitch_points": ["Adds +5 points immediately", "Priority state invitation rounds", "Direct Permanent Residency"],
            "discovery_questions": ["Which Australian states are you open to living in?", "Does your occupation appear on Victoria or NSW priority lists?"],
            "upselling_pathways": ["Dual-State Filing Package", "State Job Search Mentorship"],
            "red_flags": ["Refusal to reside in nominating state for 2 years"]
        },
        "objections_rebuttals": [{"objection": "Is the 2-year state stay legally binding?", "rebuttal": "It is a moral and state commitment requirement that protects your residency standing during citizenship processing.", "probability": "High"}],
        "faqs": [{"question": "Can I move to Sydney if nominated by Victoria?", "answer": "After fulfilling the 2-year commitment in Victoria, you have complete constitutional freedom to live anywhere in Australia."}]
    },

    {
        "id": "pm_australia_491",
        "name": "Skilled Work Regional (Provisional) Visa (Subclass 491)",
        "country": "Australia",
        "country_code": "AU",
        "flag": "🇦🇺",
        "category": "skilled_migration",
        "visa_type": "Provisional Residency (Pathway to PR 191)",
        "visa_subclass": "491",
        "status": "active",
        "authority_name": "Department of Home Affairs (DHA)",
        "official_portal_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-work-regional-491",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "5-year provisional visa providing 15 bonus points for skilled workers nominated by a regional state or sponsored by an eligible family member. Direct pathway to Permanent Residency (Subclass 191) after 3 years.",
        "description": "Designated regional areas include entire cities like Adelaide, Perth, Gold Coast, Canberra, and Newcastle. Full work rights and Medicare healthcare included.",
        "eligibility_criteria": {
            "age_min": 18,
            "age_max": 44,
            "minimum_qualification": "Diploma or Bachelor Degree",
            "work_experience_years": 1,
            "english_requirements": {"competency_level": "Competent English (IELTS 6.0 / PTE 50)", "ielts_overall": 6.0, "pte_overall": 50},
            "skills_assessment_authority": "Relevant assessing body",
            "anzsco_code": "MLTSSL or ROL regional lists",
            "points_based": {"is_points_tested": True, "minimum_points": 65, "regional_bonus_points": 15},
            "settlement_funds_required": "AUD 20,000",
            "health_character_mandatory": True
        },
        "visa_conditions": ["Condition 8579: Must live, work, and study only in designated regional areas"],
        "government_costs": {
            "currency": "AUD",
            "primary_applicant": 4770.0,
            "secondary_applicant": 2385.0,
            "child_applicant": 1195.0,
            "source_link": "https://immi.homeaffairs.gov.au"
        },
        "pricing": {
            "base_fee": 15000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 500000,
            "agent_commission": 300000,
            "milestones": [
                {"stage_number": 1, "name": "Skills Assessment & Regional Alignment", "percentage": 40, "amount_paise": 6000000},
                {"stage_number": 2, "name": "Regional Nomination Receipt (+15 Pts)", "percentage": 30, "amount_paise": 4500000},
                {"stage_number": 3, "name": "DHA Grant & Regional Relocation Protocol", "percentage": 30, "amount_paise": 4500000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "6 to 10 months",
            "stages": [
                {"stage_order": 1, "stage_name": "Skills Assessment Dossier", "duration_days": 45},
                {"stage_order": 2, "stage_name": "Regional State Application (+15 Pts)", "duration_days": 30},
                {"stage_order": 3, "stage_name": "DHA Visa Lodgement", "duration_days": 60},
                {"stage_order": 4, "stage_name": "Subclass 491 Visa Grant", "duration_days": 90}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Form 80 - Personal Particulars", "category": "Statutory Form", "form_code": "Form 80", "applicant_scope": "both", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Regional Residential Evidence", "category": "Regional Proof", "form_code": "REG-01", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Subclass 491 gives you a massive 15-point boost from day one. Vibrant metropolitan cities like Perth, Adelaide, and Gold Coast are classified as regional, giving you top career opportunities and a guaranteed path to permanent residency.",
            "target_client": "Candidates with 50-65 points who need points boost to get invited quickly.",
            "pitch_points": ["15 bonus points instantly", "Perth, Adelaide, Gold Coast qualify", "Direct PR pathway (Subclass 191)"],
            "discovery_questions": ["Would you be open to living in high-growth cities like Perth or Adelaide?"]
        },
        "objections_rebuttals": [{"objection": "Is regional Australia remote?", "rebuttal": "Not at all. Perth and Adelaide are major global cities with top universities, tech hubs, and beaches.", "probability": "High"}],
        "faqs": [{"question": "When can I transition to PR Subclass 191?", "answer": "After 3 years of living and working in the regional area with tax returns."}]
    },

    {
        "id": "pm_australia_482",
        "name": "Temporary Skill Shortage Visa (Subclass 482 / TSS)",
        "country": "Australia",
        "country_code": "AU",
        "flag": "🇦🇺",
        "category": "work",
        "visa_type": "Employer Sponsored Work Visa",
        "visa_subclass": "482",
        "status": "active",
        "authority_name": "Department of Home Affairs (DHA)",
        "official_portal_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Employer-sponsored work visa enabling Australian businesses to hire skilled overseas workers for up to 4 years across Short-term and Medium-term streams, with direct PR transition via Subclass 186.",
        "description": "Requires an approved standard business sponsor (SBS), genuine nomination, and market salary rate (TSMIT minimum AUD 70,000).",
        "eligibility_criteria": {
            "age_min": 18,
            "age_max": 50,
            "minimum_qualification": "Relevant Degree or Diploma + 2 years work experience",
            "work_experience_years": 2,
            "english_requirements": {"competency_level": "IELTS 5.0 overall (minimum 4.5 in each) or PTE 36", "ielts_overall": 5.0, "pte_overall": 36},
            "skills_assessment_authority": "TRA / VETASSESS (if mandatory for occupation)",
            "anzsco_code": "Short-term / Medium-term skilled lists",
            "health_character_mandatory": True
        },
        "visa_conditions": ["Condition 8607: Must work only for nominating employer in nominated occupation"],
        "government_costs": {
            "currency": "AUD",
            "primary_applicant": 3115.0,
            "secondary_applicant": 3115.0,
            "child_applicant": 780.0,
            "source_link": "https://immi.homeaffairs.gov.au"
        },
        "pricing": {
            "base_fee": 12000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 400000,
            "agent_commission": 250000,
            "milestones": [
                {"stage_number": 1, "name": "Sponsorship & Nomination Review", "percentage": 50, "amount_paise": 6000000},
                {"stage_number": 2, "name": "Visa Lodgement & Grant", "percentage": 50, "amount_paise": 6000000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "2 to 3 months",
            "stages": [
                {"stage_order": 1, "stage_name": "Standard Business Sponsorship (SBS)", "duration_days": 15},
                {"stage_order": 2, "stage_name": "Employer Nomination & Labour Market Testing", "duration_days": 30},
                {"stage_order": 3, "stage_name": "Visa Application & Grant", "duration_days": 30}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Form 1424 - Application for Employer Nomination", "category": "Statutory Form", "form_code": "Form 1424", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Employment Contract & Salary Letter (TSMIT AUD 70k+)", "category": "Employment Proof", "form_code": "EMP-01", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Subclass 482 gets you working in Australia in under 90 days with your employer. All streams now offer a direct pathway to permanent residency after 2 years.",
            "target_client": "Professionals with an active job offer or Australian sponsor.",
            "pitch_points": ["Fast 60-90 day processing", "Transition to PR Subclass 186 ENS in 2 years", "Spouse gets full work rights"]
        },
        "objections_rebuttals": [{"objection": "What if my employer terminates my employment?", "rebuttal": "You have 180 days to find a new sponsor or transition to another visa category.", "probability": "High"}],
        "faqs": [{"question": "Can my spouse work full time?", "answer": "Yes, Subclass 482 dependent spouses have unrestricted work rights."}]
    },

    {
        "id": "pm_australia_500",
        "name": "Student Visa (Subclass 500)",
        "country": "Australia",
        "country_code": "AU",
        "flag": "🇦🇺",
        "category": "student",
        "visa_type": "Student / Education Visa",
        "visa_subclass": "500",
        "status": "active",
        "authority_name": "Department of Home Affairs (DHA)",
        "official_portal_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Study full-time in Australia at a recognized CRICOS educational institution with part-time work rights (48 hours per fortnight) and post-study work visa pathway (Subclass 485).",
        "description": "Requires Confirmation of Enrolment (CoE), Genuine Student (GS) statement, Overseas Student Health Cover (OSHC), and evidence of financial capacity.",
        "eligibility_criteria": {
            "age_min": 16,
            "minimum_qualification": "Completion of Year 12 (for Bachelor) or Bachelor (for Master)",
            "english_requirements": {"competency_level": "IELTS 6.0 overall (minimum 5.5 in each) or PTE 50", "ielts_overall": 6.0, "pte_overall": 50},
            "settlement_funds_required": "AUD 29,710/year living costs + tuition fee deposit",
            "health_character_mandatory": True
        },
        "visa_conditions": ["Condition 8105: Work limitation of 48 hours per fortnight during study sessions", "Condition 8501: Maintain continuous OSHC health cover"],
        "government_costs": {
            "currency": "AUD",
            "primary_applicant": 1600.0,
            "secondary_applicant": 1190.0,
            "child_applicant": 390.0,
            "source_link": "https://immi.homeaffairs.gov.au"
        },
        "pricing": {
            "base_fee": 7500000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 250000,
            "agent_commission": 150000,
            "milestones": [
                {"stage_number": 1, "name": "University Admission & CoE Receipt", "percentage": 50, "amount_paise": 3750000},
                {"stage_number": 2, "name": "Visa Lodgement & Grant", "percentage": 50, "amount_paise": 3750000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "4 to 8 weeks",
            "stages": [
                {"stage_order": 1, "stage_name": "University Application & Offer Letter", "duration_days": 21},
                {"stage_order": 2, "stage_name": "Tuition Payment & CoE Issuance", "duration_days": 7},
                {"stage_order": 3, "stage_name": "Genuine Student (GS) Statement & Visa Lodgement", "duration_days": 10},
                {"stage_order": 4, "stage_name": "Biometrics, Medicals & Visa Grant", "duration_days": 20}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Confirmation of Enrolment (CoE) Certificate", "category": "Academic", "form_code": "CoE", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Genuine Student (GS) Statement of Purpose", "category": "Statement", "form_code": "GS-SOP", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Overseas Student Health Cover (OSHC) Policy", "category": "Insurance", "form_code": "OSHC", "applicant_scope": "all_family", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Australia offers world top-50 universities, 48 hours per fortnight work rights, and up to 4 years of Post-Study Work rights (Subclass 485) leading directly to PR.",
            "target_client": "Students seeking internationally recognized degrees with PR pathways.",
            "pitch_points": ["Top Group of Eight (Go8) universities", "48 hrs/fortnight work rights", "Post-study work rights"]
        },
        "objections_rebuttals": [{"objection": "DHA visa fees increased to AUD 1,600.", "rebuttal": "Yes, but this filters out non-genuine applicants, giving genuine university students faster visa processing times.", "probability": "High"}],
        "faqs": [{"question": "Can my spouse accompany me?", "answer": "Yes, Master and PhD students can bring their spouse with unrestricted full-time work rights."}]
    },

    {
        "id": "pm_australia_600",
        "name": "Visitor Visa (Subclass 600)",
        "country": "Australia",
        "country_code": "AU",
        "flag": "🇦🇺",
        "category": "visitor",
        "visa_type": "Tourist & Business Visitor",
        "visa_subclass": "600",
        "status": "active",
        "authority_name": "Department of Home Affairs (DHA)",
        "official_portal_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/visitor-600",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Short-stay tourist, family visit, and business visitor stream visa for up to 3, 6, or 12 months with single or multiple entry facility.",
        "description": "Requires proof of genuine intent to return, strong ties to home country, financial funds, and clear travel itinerary.",
        "eligibility_criteria": {
            "age_min": 0,
            "settlement_funds_required": "AUD 5,000 - AUD 10,000 in bank statements",
            "health_character_mandatory": True
        },
        "visa_conditions": ["Condition 8101: No work allowed in Australia", "Condition 8201: Max 3 months study"],
        "government_costs": {
            "currency": "AUD",
            "primary_applicant": 192.0,
            "source_link": "https://immi.homeaffairs.gov.au"
        },
        "pricing": {
            "base_fee": 2500000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 75000,
            "agent_commission": 50000,
            "milestones": [{"stage_number": 1, "name": "Filing & Biometrics", "percentage": 100, "amount_paise": 2500000}]
        },
        "processing_timeline": {
            "standard_duration": "15 to 30 days",
            "stages": [
                {"stage_order": 1, "stage_name": "Dossier Preparation & Travel Plan", "duration_days": 5},
                {"stage_order": 2, "stage_name": "ImmiAccount Lodgement", "duration_days": 1},
                {"stage_order": 3, "stage_name": "Biometric Appointment at VFS", "duration_days": 5},
                {"stage_order": 4, "stage_name": "Visa Decision", "duration_days": 15}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Form 1419 - Application for a Visitor Visa", "category": "Statutory Form", "form_code": "Form 1419", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "6-Month Bank Statement with Sufficient Balance", "category": "Financial", "form_code": "FIN-01", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Employment Leave Approval Letter & ITRs", "category": "Home Ties", "form_code": "TIES-01", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Fast, error-free visitor visa filing with strong proof of home ties to guarantee approval.",
            "target_client": "Tourists, parents visiting children in Australia, and business delegates.",
            "pitch_points": ["Fast 15-30 day turnaround", "Multiple entry 1-year or 3-year options", "High approval rate with LEAMSS SOP"]
        },
        "objections_rebuttals": [{"objection": "Why not apply directly online?", "rebuttal": "Visitor visas have the highest rejection rates due to weak home ties. Our immigration experts craft a bulletproof SOP and documentation to guarantee compliance.", "probability": "High"}],
        "faqs": [{"question": "Can I extend my stay in Australia?", "answer": "If there is no 'No Further Stay' (Condition 8503) condition on your visa, you can apply for an extension or another visa."}]
    },

    {
        "id": "pm_australia_820_801",
        "name": "Partner Visa (Subclasses 820 & 801)",
        "country": "Australia",
        "country_code": "AU",
        "flag": "🇦🇺",
        "category": "family",
        "visa_type": "Partner & Spouse Permanent Residency",
        "visa_subclass": "820/801",
        "status": "active",
        "authority_name": "Department of Home Affairs (DHA)",
        "official_portal_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-onshore-820-801",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Combined temporary (Subclass 820) and permanent (Subclass 801) visa for spouses or de facto partners of Australian citizens, Australian permanent residents, or eligible NZ citizens.",
        "description": "Full work rights, Medicare healthcare, and travel rights granted upon Subclass 820 grant. Subclass 801 permanent visa assessed 2 years after initial lodgement.",
        "eligibility_criteria": {
            "age_min": 18,
            "sponsor_eligibility": "Must be an Australian citizen, Australian permanent resident, or eligible NZ citizen",
            "relationship_evidence": "4 pillars: Financial aspects, Nature of household, Social context, and Commitment",
            "health_character_mandatory": True
        },
        "visa_conditions": ["Maintain genuine and ongoing relationship with sponsor"],
        "government_costs": {
            "currency": "AUD",
            "primary_applicant": 9095.0,
            "child_applicant": 2280.0,
            "source_link": "https://immi.homeaffairs.gov.au"
        },
        "pricing": {
            "base_fee": 18000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 600000,
            "agent_commission": 400000,
            "milestones": [
                {"stage_number": 1, "name": "Relationship Evidence Portfolio & Form 40SP/47SP", "percentage": 50, "amount_paise": 9000000},
                {"stage_number": 2, "name": "DHA Lodgement & 820 Temporary Grant", "percentage": 30, "amount_paise": 5400000},
                {"stage_number": 3, "name": "Stage 2 Subclass 801 Permanent Residency Grant", "percentage": 20, "amount_paise": 3600000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "12 to 18 months",
            "stages": [
                {"stage_order": 1, "stage_name": "Pillar Evidence Compilation", "duration_days": 30},
                {"stage_order": 2, "stage_name": "Forms 40SP & 47SP Lodgement", "duration_days": 7},
                {"stage_order": 3, "stage_name": "Bridging Visa A Activation & Medicare", "duration_days": 1},
                {"stage_order": 4, "stage_name": "Subclass 820 Grant", "duration_days": 365},
                {"stage_order": 5, "stage_name": "Subclass 801 Permanent Grant", "duration_days": 365}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Form 47SP - Application for Migration by a Partner", "category": "Statutory Form", "form_code": "Form 47SP", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Form 40SP - Sponsorship for a Partner to Migrate", "category": "Statutory Form", "form_code": "Form 40SP", "applicant_scope": "sponsor", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Form 888 - Statutory Declarations by Supporting Witnesses", "category": "Evidence", "form_code": "Form 888", "applicant_scope": "both", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Marriage Certificate or 12-Month De Facto Evidence", "category": "Relationship", "form_code": "REL-01", "applicant_scope": "both", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Reunite with your partner in Australia with full work rights and Medicare from the moment your onshore bridging visa activates, leading to permanent residency.",
            "target_client": "Spouses and partners of Australian citizens or permanent residents.",
            "pitch_points": ["Immediate work rights & Medicare on onshore filing", "Comprehensive 4-pillar evidence preparation", "Two-stage seamless PR pathway"]
        },
        "objections_rebuttals": [{"objection": "The AUD 9,095 DHA government fee is high.", "rebuttal": "It covers both the temporary Subclass 820 AND the permanent Subclass 801 visa — you never have to pay a second government fee.", "probability": "High"}],
        "faqs": [{"question": "Can I work while waiting for the decision?", "answer": "Yes, if applied onshore, your Bridging Visa A gives you full unrestricted work rights and Medicare access."}]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # CANADA
    # ──────────────────────────────────────────────────────────────────────────
    {
        "id": "pm_canada_fsw",
        "name": "Federal Skilled Worker Program (Express Entry)",
        "country": "Canada",
        "country_code": "CA",
        "flag": "🇨🇦",
        "category": "skilled_migration",
        "visa_type": "Permanent Residency (Express Entry CRS)",
        "visa_subclass": "FSW",
        "status": "active",
        "authority_name": "Immigration, Refugees and Citizenship Canada (IRCC)",
        "official_portal_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/federal-skilled-workers.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Canada's premier points-based economic immigration system. Grants direct Permanent Resident status based on Comprehensive Ranking System (CRS) score.",
        "description": "Requires minimum 67/100 points on the six selection factors, valid Educational Credential Assessment (ECA), CLB 7 in English/French, and 1+ year continuous skilled work experience under TEER 0, 1, 2, or 3.",
        "eligibility_criteria": {
            "age_min": 18,
            "age_max": 45,
            "minimum_qualification": "Bachelor's Degree with positive WES / CES Educational Credential Assessment",
            "work_experience_years": 1,
            "english_requirements": {"competency_level": "Canadian Language Benchmark 7 (IELTS General: R 6.0, W 6.0, L 6.0, S 6.0 or CELPIP 7)", "ielts_overall": 6.0},
            "points_based": {"is_points_tested": True, "minimum_points": 67, "crs_target": 490},
            "settlement_funds_required": "CAD 14,690 (Single) / CAD 18,288 (Couple)",
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "CAD",
            "primary_applicant": 1365.0,  # 850 processing + 515 RPRF
            "secondary_applicant": 1365.0,
            "child_applicant": 230.0,
            "source_link": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/fees.html"
        },
        "pricing": {
            "base_fee": 15000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 500000,
            "agent_commission": 300000,
            "milestones": [
                {"stage_number": 1, "name": "ECA & Language Optimization", "percentage": 40, "amount_paise": 6000000},
                {"stage_number": 2, "name": "Express Entry Pool Submission & PNP Alignment", "percentage": 30, "amount_paise": 4500000},
                {"stage_number": 3, "name": "e-APR Lodgement post-ITA & COPR Issuance", "percentage": 30, "amount_paise": 4500000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "6 months post-ITA",
            "stages": [
                {"stage_order": 1, "stage_name": "ECA (WES) & Language Test", "duration_days": 45},
                {"stage_order": 2, "stage_name": "Express Entry Profile Creation", "duration_days": 7},
                {"stage_order": 3, "stage_name": "ITA Receipt in Category Draws", "duration_days": 60},
                {"stage_order": 4, "stage_name": "e-APR Filing & Biometrics (IMM 0008/5669)", "duration_days": 30},
                {"stage_order": 5, "stage_name": "COPR (Confirmation of PR) Issued", "duration_days": 150}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "IMM 0008 - Generic Application Form for Canada", "category": "Statutory Form", "form_code": "IMM 0008", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "IMM 5669 - Schedule A Background Declaration", "category": "Statutory Form", "form_code": "IMM 5669", "applicant_scope": "both", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "WES / CES Educational Credential Assessment (ECA)", "category": "Education", "form_code": "ECA", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Proof of Settlement Funds (Bank Letter)", "category": "Financial", "form_code": "POF", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Canada Express Entry gives you direct permanent resident status in as little as 6 months. Free healthcare, top education, and Canadian citizenship after 3 years.",
            "target_client": "Professionals under 35 with Master's degree, strong English, and 3+ years skilled experience.",
            "pitch_points": ["Fast 6-month processing post-ITA", "Direct Permanent Residency card", "Full Canadian healthcare & citizenship path"]
        },
        "objections_rebuttals": [{"objection": "General CRS cutoffs are above 500.", "rebuttal": "We target category-based draws (STEM, Healthcare, French, Trades) and Provincial Nominee Programs (PNP) which give an automatic 600 bonus points.", "probability": "High"}],
        "faqs": [{"question": "What is the Canadian citizenship requirement?", "answer": "You only need to reside in Canada for 3 out of 5 years (1,095 days) to apply for Canadian Citizenship."}]
    },
    {
        "id": "pm_canada_pnp",
        "name": "Canada Provincial Nominee Program (PNP - Enhanced & Base)",
        "country": "Canada",
        "country_code": "CA",
        "flag": "🇨🇦",
        "category": "skilled_migration",
        "visa_type": "Permanent Residency (Provincial Nomination)",
        "visa_subclass": "PNP",
        "status": "active",
        "authority_name": "IRCC / Provincial Immigration Programs (OINP, BCPNP, SINP, AAIP)",
        "official_portal_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/provincial-nominees.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Provinces nominate skilled workers to fill local economic needs. An enhanced nomination awards +600 points in Express Entry, virtually guaranteeing an Invitation to Apply (ITA) for Permanent Residency.",
        "description": "Available across Ontario (OINP), British Columbia (BC PNP), Saskatchewan (SINP), Alberta (AAIP), and Nova Scotia.",
        "eligibility_criteria": {
            "age_min": 18,
            "age_max": 49,
            "minimum_qualification": "Post-secondary diploma or degree (ECA verified)",
            "work_experience_years": 1,
            "english_requirements": {"competency_level": "CLB 5 to CLB 7", "ielts_overall": 6.0},
            "points_based": {"is_points_tested": True, "minimum_points": 60},
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "CAD",
            "primary_applicant": 1365.0,
            "source_link": "https://www.canada.ca"
        },
        "pricing": {
            "base_fee": 16000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 500000,
            "agent_commission": 350000,
            "milestones": [
                {"stage_number": 1, "name": "Provincial Stream Evaluation & EOI Submission", "percentage": 40, "amount_paise": 6400000},
                {"stage_number": 2, "name": "Provincial Nomination Dossier Filing", "percentage": 30, "amount_paise": 4800000},
                {"stage_number": 3, "name": "IRCC PR Lodgement (post +600 CRS Points)", "percentage": 30, "amount_paise": 4800000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "6 to 10 months",
            "stages": [
                {"stage_order": 1, "stage_name": "Provincial EOI & NOI Invitation", "duration_days": 30},
                {"stage_order": 2, "stage_name": "Provincial Nomination Approval (+600 CRS)", "duration_days": 60},
                {"stage_order": 3, "stage_name": "IRCC Federal PR Lodgement & Confirmation", "duration_days": 90}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Provincial Nomination Certificate / NOI Letter", "category": "Statutory Notice", "form_code": "PNP-CERT", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "WES / ICAS Educational Credential Assessment", "category": "Education", "form_code": "ECA", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Settlement Funds Proof (Provincial Threshold)", "category": "Financial", "form_code": "POF", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "If your CRS score is below 480, Provincial Nominee Programs grant +600 points instantly, guaranteeing your Canadian PR invitation in the very next draw.",
            "target_client": "Candidates with CRS between 360-470 who want a guaranteed route to Canadian permanent residence.",
            "pitch_points": ["+600 bonus CRS points guarantees PR invite", "Low IELTS score options (CLB 5 acceptable for several streams)", "Active provincial streams for tech, healthcare, and finance"]
        },
        "objections_rebuttals": [{"objection": "Do I have to live in that province forever?", "rebuttal": "Charter Section 6 grants freedom of movement once you receive Permanent Resident status.", "probability": "High"}],
        "faqs": [{"question": "Which province has the easiest nomination?", "answer": "Saskatchewan (SINP) and Alberta (AAIP) frequently invite candidates without job offers based solely on in-demand occupations."}]
    },
    {
        "id": "pm_canada_study_permit",
        "name": "Canada Study Permit (Student Visa - DLI / SDS)",
        "country": "Canada",
        "country_code": "CA",
        "flag": "🇨🇦",
        "category": "student",
        "visa_type": "Temporary Resident Student Visa",
        "visa_subclass": "Study Permit",
        "status": "active",
        "authority_name": "Immigration, Refugees and Citizenship Canada (IRCC)",
        "official_portal_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Full-time study authorization at a Canadian Designated Learning Institution (DLI). Eligible programs lead directly to Post-Graduation Work Permit (PGWP) of up to 3 years and Canadian PR under CEC.",
        "description": "Requires official Provincial Attestation Letter (PAL) and Letter of Acceptance (LOA) from an approved DLI.",
        "eligibility_criteria": {
            "age_min": 17,
            "minimum_qualification": "High School Graduation or Undergraduate Degree with valid LOA & PAL",
            "work_experience_years": 0,
            "english_requirements": {"competency_level": "IELTS Academic 6.0 overall (minimum 6.0 in each band) or PTE Academic 60", "ielts_overall": 6.0},
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "CAD",
            "primary_applicant": 150.0,
            "source_link": "https://www.canada.ca"
        },
        "pricing": {
            "base_fee": 7500000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 250000,
            "agent_commission": 150000,
            "milestones": [
                {"stage_number": 1, "name": "DLI Offer Letter & Provincial Attestation Letter (PAL)", "percentage": 50, "amount_paise": 3750000},
                {"stage_number": 2, "name": "GIC Setup, Medicals & Study Permit Lodgement", "percentage": 50, "amount_paise": 3750000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "4 to 8 weeks",
            "stages": [
                {"stage_order": 1, "stage_name": "DLI Admission & PAL Issuance", "duration_days": 21},
                {"stage_order": 2, "stage_name": "GIC Financial Verification & Medical Exam", "duration_days": 10},
                {"stage_order": 3, "stage_name": "IRCC Study Permit Decision & Visa Stamp", "duration_days": 30}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "DLI Letter of Acceptance (LOA) & PAL", "category": "Academic", "form_code": "LOA-PAL", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Guaranteed Investment Certificate (GIC) CAD 20,635 Receipt", "category": "Financial", "form_code": "GIC-RECEIPT", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Statement of Purpose (SOP) & Academic Ties", "category": "Statement", "form_code": "SOP", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Study in world-class Canadian colleges and universities, work up to 24 hours per week while studying, and secure a 3-year PGWP leading directly into Canadian Permanent Residence.",
            "target_client": "Students seeking diploma, bachelor's, or master's degrees with post-study immigration intent.",
            "pitch_points": ["Up to 3-year PGWP work permit post-graduation", "24 hrs/week part-time work permitted", "Direct PR pathway via Canadian Experience Class (CEC)"]
        },
        "objections_rebuttals": [{"objection": "Canada introduced caps on international student permits.", "rebuttal": "Master's and PhD programs are prioritized with 3-year PGWPs regardless of course length, and our designated institutions secure guaranteed PALs.", "probability": "High"}],
        "faqs": [{"question": "Can my spouse join me in Canada?", "answer": "Spouses of students enrolled in Master's or Doctoral degree programs qualify for an Open Work Permit."}]
    },
    {
        "id": "pm_canada_visitor",
        "name": "Canada Visitor Visa (Temporary Resident Visa / Super Visa)",
        "country": "Canada",
        "country_code": "CA",
        "flag": "🇨🇦",
        "category": "visitor",
        "visa_type": "Temporary Resident Visa (TRV)",
        "visa_subclass": "Visitor Visa",
        "status": "active",
        "authority_name": "Immigration, Refugees and Citizenship Canada (IRCC)",
        "official_portal_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Up to 10-year multiple-entry visa allowing stays of up to 6 months per entry for tourism, visiting family, business meetings, or exploring business opportunities. Parents qualify for 5-year Super Visa.",
        "description": "Requires demonstrating strong ties to home country, financial solvency, and genuine temporary intent under IRPA Section 179(b).",
        "eligibility_criteria": {
            "age_min": 0,
            "minimum_qualification": "None",
            "work_experience_years": 0,
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "CAD",
            "primary_applicant": 100.0,
            "source_link": "https://www.canada.ca"
        },
        "pricing": {
            "base_fee": 2500000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 100000,
            "agent_commission": 50000,
            "milestones": [
                {"stage_number": 1, "name": "Application Dossier & Ties Documentation", "percentage": 50, "amount_paise": 1250000},
                {"stage_number": 2, "name": "IRCC Portal Submission & Biometrics Booking", "percentage": 50, "amount_paise": 1250000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "2 to 6 weeks",
            "stages": [
                {"stage_order": 1, "stage_name": "Document Packaging & Financial Audit", "duration_days": 5},
                {"stage_order": 2, "stage_name": "Biometrics at VFS", "duration_days": 1},
                {"stage_order": 3, "stage_name": "Passport Request & Visa Foil", "duration_days": 14}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "IMM 5257 - Application for Temporary Resident Visa", "category": "Statutory Form", "form_code": "IMM 5257", "applicant_scope": "both", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Proof of Financial Means (Bank Statements & ITRs)", "category": "Financial", "form_code": "FIN-PROOF", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Letter of Invitation from Canadian Host or Travel Itinerary", "category": "Purpose", "form_code": "INVITATION", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Get a 10-year multiple-entry visa to Canada to visit family, attend business meetings, or explore Canadian provinces in person.",
            "target_client": "Tourists, parents of Canadian PRs/citizens, and business executives traveling for conferences.",
            "pitch_points": ["Valid up to passport expiry (up to 10 years)", "Multiple entries with up to 6 months stay", "Super Visa allows parents to stay up to 5 consecutive years"]
        },
        "objections_rebuttals": [{"objection": "Canada visitor visa refusal rates under Section 179(b) are high.", "rebuttal": "We prepare an airtight Legal Submission Letter detailing employment, tax returns, and property ties to eliminate any doubt of overstay.", "probability": "High"}],
        "faqs": [{"question": "Can I convert a Canadian visitor visa to a work permit inside Canada?", "answer": "Under current IRCC public policies, visitors holding valid job offers can apply for employer-specific work permits from within Canada."}]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # UNITED KINGDOM
    # ──────────────────────────────────────────────────────────────────────────
    {
        "id": "pm_uk_skilled_worker",
        "name": "UK Skilled Worker Visa",
        "country": "United Kingdom",
        "country_code": "GB",
        "flag": "🇬🇧",
        "category": "work",
        "visa_type": "Points-Based Work Visa (Pathway to ILR)",
        "visa_subclass": "Skilled Worker",
        "status": "active",
        "authority_name": "UK Visas and Immigration (UKVI) / Home Office",
        "official_portal_url": "https://www.gov.uk/skilled-worker-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Points-based employment visa for professionals with a job offer from an approved UK licensed sponsor company meeting the general salary threshold (GBP 38,700). Direct path to Indefinite Leave to Remain (ILR) after 5 years.",
        "description": "Requires a valid Certificate of Sponsorship (CoS), job on the eligible occupation code list, and English proficiency at CEFR Level B1.",
        "eligibility_criteria": {
            "age_min": 18,
            "minimum_qualification": "RQF Level 3 (A-level equivalent) or above",
            "work_experience_years": 2,
            "english_requirements": {"competency_level": "CEFR Level B1 (IELTS for UKVI: 4.0 in each band) or UK NARIC degree verification", "ielts_overall": 4.0},
            "points_based": {"is_points_tested": True, "minimum_points": 70},
            "salary_threshold": "GBP 38,700 or the going rate for the occupation code (whichever is higher)",
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "GBP",
            "primary_applicant": 719.0,
            "secondary_applicant": 719.0,
            "child_applicant": 719.0,
            "source_link": "https://www.gov.uk/skilled-worker-visa/how-much-it-costs",
            "line_items": [
                {"name": "UKVI Visa Application Fee (Up to 3 years)", "amount": 719, "currency": "GBP"},
                {"name": "Immigration Health Surcharge (IHS) per year", "amount": 1035, "currency": "GBP"}
            ]
        },
        "pricing": {
            "base_fee": 14000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 450000,
            "agent_commission": 300000,
            "milestones": [
                {"stage_number": 1, "name": "CoS Verification & Occupation Code Mapping", "percentage": 50, "amount_paise": 7000000},
                {"stage_number": 2, "name": "UKVI Online Submission & Priority Grant", "percentage": 50, "amount_paise": 7000000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "3 weeks (standard) / 5 days (priority)",
            "stages": [
                {"stage_order": 1, "stage_name": "CoS Issuance by Employer", "duration_days": 10},
                {"stage_order": 2, "stage_name": "TB Test & Ecctis English Verification", "duration_days": 7},
                {"stage_order": 3, "stage_name": "UKVI Online Application Lodgement", "duration_days": 2},
                {"stage_order": 4, "stage_name": "VFS Biometrics & Visa Vignette / eVisa", "duration_days": 15}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Certificate of Sponsorship (CoS) Reference Letter", "category": "Employer Statutory Form", "form_code": "CoS", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Tuberculosis (TB) Screening Medical Certificate", "category": "Health", "form_code": "TB-UKVI", "applicant_scope": "all_family", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Ecctis English Language / Degree Authenticity Certificate", "category": "Academic", "form_code": "ECCTIS", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "The UK Skilled Worker visa puts you in London or regional UK tech corridors in 3 weeks. Full NHS healthcare, schooling for children, and permanent ILR settlement in 5 years.",
            "target_client": "Professionals with a job offer from an approved UK sponsor.",
            "pitch_points": ["Lightning fast 3-week decision", "Full NHS healthcare access", "5-year direct path to UK ILR Settlement & British Passport"]
        },
        "objections_rebuttals": [{"objection": "The GBP 38,700 salary rule is strict.", "rebuttal": "New entrants (under 26, recent graduates, PhD holders) qualify with a 30% discount at only GBP 30,960.", "probability": "High"}],
        "faqs": [{"question": "Can my family come with me?", "answer": "Yes, spouse and dependent children under 18 can accompany you with full work rights."}]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # GERMANY
    # ──────────────────────────────────────────────────────────────────────────
    {
        "id": "pm_germany_blue_card",
        "name": "Germany EU Blue Card (Section 18g AufenthG)",
        "country": "Germany",
        "country_code": "DE",
        "flag": "🇩🇪",
        "category": "work",
        "visa_type": "EU Blue Card (Fast-Track PR)",
        "visa_subclass": "Blue Card",
        "status": "active",
        "authority_name": "Federal Foreign Office (Auswärtiges Amt) / BAMF",
        "official_portal_url": "https://www.make-it-in-germany.com/en/visa-residence/types/eu-blue-card",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/deu/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Premier fast-track residence and work permit for university graduates with a recognized degree and qualifying salary. Grants German Permanent Residency (Niederlassungserlaubnis) in just 21 months with B1 German (or 27 months without).",
        "description": "Qualifying salary threshold: EUR 45,300/year (standard) or EUR 41,041.80/year (bottleneck professions in IT, engineering, mathematics, healthcare, and career starters).",
        "eligibility_criteria": {
            "age_min": 18,
            "minimum_qualification": "Recognized University Degree (Anabin H+ comparable or ZAB Statement of Comparability)",
            "work_experience_years": 0,  # Degree + Job offer sufficient
            "english_requirements": {"competency_level": "Fluent English (B2) or Basic German (A1 recommended)"},
            "salary_threshold": "EUR 45,300 (Standard) / EUR 41,041.80 (STEM / Shortage)",
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "EUR",
            "primary_applicant": 75.0,  # National Visa Type D
            "secondary_applicant": 75.0,
            "child_applicant": 37.5,
            "source_link": "https://www.auswaertiges-amt.de"
        },
        "pricing": {
            "base_fee": 13000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 450000,
            "agent_commission": 300000,
            "milestones": [
                {"stage_number": 1, "name": "Anabin / ZAB Degree Evaluation & Contract Verification", "percentage": 50, "amount_paise": 6500000},
                {"stage_number": 2, "name": "VIDEX Filing & Embassy Blue Card Stamping", "percentage": 50, "amount_paise": 6500000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "4 to 8 weeks",
            "stages": [
                {"stage_order": 1, "stage_name": "ZAB / Anabin University Recognition Check", "duration_days": 14},
                {"stage_order": 2, "stage_name": "Erklärung zum Beschäftigungsverhältnis Employer Form", "duration_days": 7},
                {"stage_order": 3, "stage_name": "VIDEX D-Visa Appointment at VFS / Consulate", "duration_days": 14},
                {"stage_order": 4, "stage_name": "National Visa D Stamping & Travel", "duration_days": 21}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "VIDEX National Visa Application Form (Type D)", "category": "Statutory Form", "form_code": "VIDEX-D", "applicant_scope": "both", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Declaration of Employment (Erklärung zum Beschäftigungsverhältnis)", "category": "Employer Form", "form_code": "BA-044", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Section 54 (2) AufenthG Legal Declaration", "category": "Statutory Form", "form_code": "Sec-54", "applicant_scope": "both", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Anabin H+ University & Degree Recognition Extract", "category": "Academic", "form_code": "ANABIN", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "The German EU Blue Card offers Europe's fastest permanent residency: just 21 months to German PR. No labour market test, low government fees of EUR 75, and spouse gets immediate unrestricted work rights.",
            "target_client": "Engineers, software developers, and technical professionals with a German job offer.",
            "pitch_points": ["German PR in 21 months", "EU-wide mobility after 12 months", "Spouse works without German language requirement"]
        },
        "objections_rebuttals": [{"objection": "Do I need German to get the Blue Card?", "rebuttal": "No German language proficiency is required to obtain the EU Blue Card for English-speaking jobs.", "probability": "High"}],
        "faqs": [{"question": "How soon can I get German citizenship?", "answer": "Under the new German citizenship law, you can apply for German citizenship after just 3 to 5 years of legal residence."}]
    },

    {
        "id": "pm_germany_chancenkarte",
        "name": "Opportunity Card / Chancenkarte (Section 20a AufenthG)",
        "country": "Germany",
        "country_code": "DE",
        "flag": "🇩🇪",
        "category": "work",
        "visa_type": "Points-Based Job Seeker Visa",
        "visa_subclass": "Chancenkarte",
        "status": "active",
        "authority_name": "Federal Foreign Office (Auswärtiges Amt)",
        "official_portal_url": "https://www.make-it-in-germany.com/en/visa-residence/types/jobsearch-opportunity-card",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/deu/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Germany's points-based job search visa allowing skilled individuals to enter Germany for up to 1 year to find qualified employment. Part-time work (up to 20 hours/week) and 2-week trial jobs permitted.",
        "description": "Requires minimum 6 points under the statutory points grid (qualification recognition, work experience, age, German/English proficiency, and ties to Germany).",
        "eligibility_criteria": {
            "age_min": 18,
            "age_max": 40,
            "minimum_qualification": "At least 2 years vocational training or university degree recognized in country of origin",
            "english_requirements": {"competency_level": "German A1 or English B2 (IELTS 5.5+)"},
            "points_based": {"is_points_tested": True, "minimum_points": 6},
            "settlement_funds_required": "EUR 12,324 in a German Blocked Account (Sperrkonto) for 1 year",
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "EUR",
            "primary_applicant": 75.0,
            "source_link": "https://www.make-it-in-germany.com"
        },
        "pricing": {
            "base_fee": 12000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 400000,
            "agent_commission": 250000,
            "milestones": [
                {"stage_number": 1, "name": "Points Calculation & Blocked Account Setup", "percentage": 50, "amount_paise": 6000000},
                {"stage_number": 2, "name": "VIDEX Filing & Visa Stamping", "percentage": 50, "amount_paise": 6000000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "4 to 6 weeks",
            "stages": [
                {"stage_order": 1, "stage_name": "Points Assessment & ZAB Check", "duration_days": 10},
                {"stage_order": 2, "stage_name": "Blocked Account (Sperrkonto) Opening", "duration_days": 7},
                {"stage_order": 3, "stage_name": "VIDEX Application Submission", "duration_days": 14},
                {"stage_order": 4, "stage_name": "Chancenkarte Stamped", "duration_days": 14}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Chancenkarte Points Self-Assessment Sheet", "category": "Statutory Form", "form_code": "CK-POINTS", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "VIDEX National Visa D Form", "category": "Statutory Form", "form_code": "VIDEX-D", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "German Blocked Account (Sperrkonto) Confirmation (EUR 12,324)", "category": "Financial", "form_code": "SPERR", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Go to Germany with the Opportunity Card and search for high-paying jobs in person while working part-time. Converts directly to an EU Blue Card upon securing a contract.",
            "target_client": "Young skilled professionals who want to explore job opportunities directly on the ground in Germany.",
            "pitch_points": ["No job offer required upfront", "Part-time work up to 20 hrs/week allowed", "Seamless conversion to EU Blue Card"]
        },
        "objections_rebuttals": [{"objection": "What if I don't find a job in 12 months?", "rebuttal": "You can extend the Opportunity Card by up to 2 years if you have an employment trial or follow-up offer.", "probability": "Medium"}],
        "faqs": [{"question": "Can I work while searching for a job?", "answer": "Yes, you can work up to 20 hours per week and take 2-week trial employment periods with potential employers."}]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # UNITED STATES
    # ──────────────────────────────────────────────────────────────────────────
    {
        "id": "pm_usa_h1b",
        "name": "US H-1B Specialty Occupation Visa",
        "country": "United States",
        "country_code": "US",
        "flag": "🇺🇸",
        "category": "work",
        "visa_type": "Nonimmigrant Specialty Worker",
        "visa_subclass": "H-1B",
        "status": "active",
        "authority_name": "U.S. Citizenship and Immigration Services (USCIS) / Department of State",
        "official_portal_url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations",
        "vfs_url": "https://travel.state.gov",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Employer-sponsored nonimmigrant specialty occupation work visa for professionals holding at least a US bachelor's degree or foreign equivalent. Dual intent allows seamless filing for Green Card (EB-2 / EB-3).",
        "description": "Requires Department of Labor certified Labor Condition Application (Form ETA-9035) and approved USCIS Form I-129 petition.",
        "eligibility_criteria": {
            "age_min": 21,
            "minimum_qualification": "Bachelor's Degree or foreign 4-year equivalent in specialty field",
            "work_experience_years": 0,
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "USD",
            "primary_applicant": 205.0,  # MRV Consular Fee
            "source_link": "https://www.uscis.gov/i-129"
        },
        "pricing": {
            "base_fee": 16000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 500000,
            "agent_commission": 350000,
            "milestones": [
                {"stage_number": 1, "name": "LCA Certification & I-129 Petition Package", "percentage": 50, "amount_paise": 8000000},
                {"stage_number": 2, "name": "DS-160 Filing & Visa Stamping Interview", "percentage": 50, "amount_paise": 8000000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "2 to 4 months (or 15 days via Premium Processing)",
            "stages": [
                {"stage_order": 1, "stage_name": "LCA Filing with Department of Labor", "duration_days": 7},
                {"stage_order": 2, "stage_name": "USCIS Form I-129 Petition Approval", "duration_days": 30},
                {"stage_order": 3, "stage_name": "Form DS-160 & Consular Visa Stamping", "duration_days": 21}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Form DS-160 Nonimmigrant Visa Confirmation", "category": "Statutory Form", "form_code": "DS-160", "applicant_scope": "both", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "USCIS Form I-797 Approval Notice", "category": "Statutory Notice", "form_code": "I-797", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Certified Labor Condition Application (Form ETA-9035)", "category": "Labor Dept Form", "form_code": "ETA-9035", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "H-1B offers dual intent, meaning you can work legally in top US tech companies while simultaneously filing for your permanent US Green Card.",
            "target_client": "Specialty occupation professionals with a sponsoring US employer.",
            "pitch_points": ["Dual intent visa (PR pathway safe)", "Spouse eligible for H-4 EAD work permit once I-140 approved", "3+3 = 6 years total stay"]
        },
        "objections_rebuttals": [{"objection": "The H-1B lottery has low selection odds.", "rebuttal": "We advise cap-exempt H-1B routes (universities, non-profit research organizations) or L-1A executive transfer pathways.", "probability": "High"}],
        "faqs": [{"question": "Can my spouse work on H-4?", "answer": "Yes, once your Form I-140 immigrant petition is approved, your spouse can apply for an H-4 EAD work permit."}]
    },
    {
        "id": "pm_usa_l1",
        "name": "US L-1 Intracompany Transferee Visa (L-1A / L-1B)",
        "country": "United States",
        "country_code": "US",
        "flag": "🇺🇸",
        "category": "work",
        "visa_type": "Nonimmigrant Executive & Specialist Worker",
        "visa_subclass": "L-1",
        "status": "active",
        "authority_name": "U.S. Citizenship and Immigration Services (USCIS)",
        "official_portal_url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/l-1a-intracompany-transferee-executive-or-manager",
        "vfs_url": "https://travel.state.gov",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Transfer visa for executives, managers (L-1A) or specialized knowledge staff (L-1B) of international companies to a US subsidiary. L-1A allows direct EB-1C Green Card with zero PERM labor certification.",
        "description": "Requires at least 1 continuous year of overseas employment with qualifying corporate affiliate in previous 3 years.",
        "eligibility_criteria": {
            "age_min": 21,
            "minimum_qualification": "Bachelor Degree or specialized technical experience",
            "work_experience_years": 1,
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "USD",
            "primary_applicant": 205.0,
            "source_link": "https://www.uscis.gov/i-129"
        },
        "pricing": {
            "base_fee": 18000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 600000,
            "agent_commission": 400000,
            "milestones": [
                {"stage_number": 1, "name": "Corporate Affiliation Audit & I-129 Package", "percentage": 50, "amount_paise": 9000000},
                {"stage_number": 2, "name": "USCIS Approval & DS-160 Consular Stamping", "percentage": 50, "amount_paise": 9000000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "1 to 3 months (or 15 days via Premium Processing)",
            "stages": [
                {"stage_order": 1, "stage_name": "Form I-129 L Petition Package", "duration_days": 21},
                {"stage_order": 2, "stage_name": "USCIS Petition Adjudication", "duration_days": 15},
                {"stage_order": 3, "stage_name": "Consular Visa Stamping", "duration_days": 14}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "USCIS Form I-797 L-1 Approval Notice", "category": "Statutory Notice", "form_code": "I-797", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Qualifying Corporate Affiliate Structure Chart", "category": "Corporate", "form_code": "CORP-ORG", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "1-Year Foreign Employment Verification & Tax Records", "category": "Employment", "form_code": "EMP-VERIF", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "L-1 transfers you directly to the US without any lottery caps, and L-1A executives get the fastest Green Card pathway via EB-1C with zero labor cert waiting lines.",
            "target_client": "Mid-to-senior managers, directors, business owners, and tech leads working with global firms.",
            "pitch_points": ["No annual lottery cap", "Direct EB-1C Green Card within 12 months", "Spouse gets automatic L-2S work authorization without filing separate EAD"]
        },
        "objections_rebuttals": [{"objection": "Does my company need an existing US branch?", "rebuttal": "No! We can file a 'New Office L-1' petition allowing your company to establish its initial US subsidiary.", "probability": "High"}],
        "faqs": [{"question": "Can my spouse work immediately on L-2?", "answer": "Yes! L-2 spouses receive work authorization incident to status (L-2S) immediately upon entry without waiting for an EAD card."}]
    },
    {
        "id": "pm_usa_eb1",
        "name": "US EB-1 Priority Workers & Extraordinary Ability Green Card",
        "country": "United States",
        "country_code": "US",
        "flag": "🇺🇸",
        "category": "skilled_migration",
        "visa_type": "Permanent Residency Immigrant Visa",
        "visa_subclass": "EB-1",
        "status": "active",
        "authority_name": "U.S. Citizenship and Immigration Services (USCIS)",
        "official_portal_url": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-first-preference-eb-1",
        "vfs_url": "https://travel.state.gov",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "First preference employment-based permanent residence Green Card. Self-petition allowed under EB-1A extraordinary ability with zero employer requirement and zero PERM labor certification.",
        "description": "Fast-tracked immigrant visa for candidates at the very top of their field in sciences, arts, business, or education.",
        "eligibility_criteria": {
            "age_min": 21,
            "minimum_qualification": "Evidence of sustained national or international acclaim",
            "work_experience_years": 5,
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "USD",
            "primary_applicant": 715.0,  # Form I-140 fee
            "source_link": "https://www.uscis.gov/i-140"
        },
        "pricing": {
            "base_fee": 25000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 800000,
            "agent_commission": 500000,
            "milestones": [
                {"stage_number": 1, "name": "Extraordinary Criteria Evaluation & Evidence Dossier", "percentage": 40, "amount_paise": 10000000},
                {"stage_number": 2, "name": "Form I-140 Immigrant Petition Filing", "percentage": 30, "amount_paise": 7500000},
                {"stage_number": 3, "name": "I-485 Adjustment / DS-260 Immigrant Visa", "percentage": 30, "amount_paise": 7500000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "6 to 12 months (or 15 days for I-140 via Premium Processing)",
            "stages": [
                {"stage_order": 1, "stage_name": "Evidence Portfolio Assembly", "duration_days": 45},
                {"stage_order": 2, "stage_name": "USCIS Form I-140 Adjudication", "duration_days": 15},
                {"stage_order": 3, "stage_name": "Green Card Issuance", "duration_days": 120}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "USCIS Form I-140 Immigrant Petition for Alien Workers", "category": "Statutory Form", "form_code": "I-140", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Independent Expert Opinion Letters & Citations", "category": "Evidence", "form_code": "EB1-LETTERS", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "High Remuneration / Media Coverage / Major Awards Proof", "category": "Evidence", "form_code": "EB1-AWARDS", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "EB-1 gives you direct US Green Cards for your whole family without waiting decades in Indian backlogs, with zero employer sponsorship required for EB-1A.",
            "target_client": "Senior IT architects, researchers, founders, physicians, and executives with publications or high salaries.",
            "pitch_points": ["Zero employer lock-in (self-petition)", "Bypasses standard decade-long backlog", "Direct Green Card for primary applicant, spouse, and kids under 21"]
        },
        "objections_rebuttals": [{"objection": "I don't have a Nobel Prize or Olympic medal.", "rebuttal": "You only need to satisfy 3 out of 10 standard criteria (such as high salary, leading role in reputable company, scholarly articles, or judging others' work).", "probability": "High"}],
        "faqs": [{"question": "Do I need an employer sponsor for EB-1A?", "answer": "No. EB-1A is a self-petitioned category. You do not need any US employer sponsor."}]
    },
    {
        "id": "pm_usa_eb2_niw",
        "name": "US EB-2 National Interest Waiver (NIW)",
        "country": "United States",
        "country_code": "US",
        "flag": "🇺🇸",
        "category": "skilled_migration",
        "visa_type": "Permanent Residency Immigrant Visa",
        "visa_subclass": "EB-2",
        "status": "active",
        "authority_name": "U.S. Citizenship and Immigration Services (USCIS)",
        "official_portal_url": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-second-preference-eb-2",
        "vfs_url": "https://travel.state.gov",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Self-petitioned Green Card under EB-2 where the statutory PERM labor certification and job offer requirements are waived because your proposed endeavor holds substantial merit and national importance to the US.",
        "description": "Evaluated under the landmark Dhanasar 3-prong framework for STEM professionals, AI engineers, and healthcare researchers.",
        "eligibility_criteria": {
            "age_min": 21,
            "minimum_qualification": "Master's Degree (or Bachelor's + 5 years progressive post-degree experience)",
            "work_experience_years": 5,
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "USD",
            "primary_applicant": 715.0,
            "source_link": "https://www.uscis.gov/i-140"
        },
        "pricing": {
            "base_fee": 20000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 650000,
            "agent_commission": 400000,
            "milestones": [
                {"stage_number": 1, "name": "Endeavor Brief & Dhanasar Framework Strategy", "percentage": 40, "amount_paise": 8000000},
                {"stage_number": 2, "name": "Form I-140 Petition Filing & Premium Adjudication", "percentage": 30, "amount_paise": 6000000},
                {"stage_number": 3, "name": "Green Card Adjustment of Status Package", "percentage": 30, "amount_paise": 6000000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "4 to 8 months (or 45 days via Premium Processing)",
            "stages": [
                {"stage_order": 1, "stage_name": "Dhanasar 3-Prong Dossier Preparation", "duration_days": 35},
                {"stage_order": 2, "stage_name": "USCIS Form I-140 Adjudication", "duration_days": 45},
                {"stage_order": 3, "stage_name": "Adjustment of Status / Immigrant Visa", "duration_days": 90}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Proposed Endeavor Narrative Statement", "category": "Legal Dossier", "form_code": "NIW-ENDEAVOR", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Advanced Degree Evaluation / Master's Transcripts", "category": "Academic", "form_code": "DEGREE-EVAL", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "3 to 5 Independent Recommendation Letters from US Experts", "category": "Evidence", "form_code": "REC-LETTERS", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "EB-2 NIW allows advanced degree holders and tech professionals to self-sponsor their permanent US Green Card without relying on any employer or labor cert.",
            "target_client": "Professionals with Master's degrees in STEM, data science, cyber security, renewable energy, or biotech.",
            "pitch_points": ["No employer sponsorship needed", "Waiver of lengthy PERM labor certification", "Lock in a priority date permanently"]
        },
        "objections_rebuttals": [{"objection": "What if my employer refuses to file for my Green Card?", "rebuttal": "With EB-2 NIW, you file completely independently. Your employer does not even need to know or sign any documents.", "probability": "High"}],
        "faqs": [{"question": "Can I file while residing in India or the UAE?", "answer": "Yes! EB-2 NIW can be filed directly from outside the United States through consular processing."}]
    },
    {
        "id": "pm_usa_f1",
        "name": "US F-1 Academic Student Visa",
        "country": "United States",
        "country_code": "US",
        "flag": "🇺🇸",
        "category": "student",
        "visa_type": "Nonimmigrant Student Visa",
        "visa_subclass": "F-1",
        "status": "active",
        "authority_name": "U.S. Department of State / SEVP",
        "official_portal_url": "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
        "vfs_url": "https://travel.state.gov",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "Full-time degree academic student visa for accredited US colleges and universities. Includes 20 hrs/week on-campus work rights and 12-to-36 months STEM OPT post-graduation work authorization.",
        "description": "Requires official Form I-20 Certificate of Eligibility issued by an SEVP-certified institution and SEVIS I-901 fee payment.",
        "eligibility_criteria": {
            "age_min": 17,
            "minimum_qualification": "High School Diploma or Undergraduate Degree with valid SEVP I-20",
            "work_experience_years": 0,
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "USD",
            "primary_applicant": 185.0,  # MRV Fee + SEVIS I-901 $350
            "source_link": "https://travel.state.gov"
        },
        "pricing": {
            "base_fee": 7500000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 250000,
            "agent_commission": 150000,
            "milestones": [
                {"stage_number": 1, "name": "University Admission & Form I-20 Acquisition", "percentage": 50, "amount_paise": 3750000},
                {"stage_number": 2, "name": "DS-160 Filing & Visa Interview Coaching", "percentage": 50, "amount_paise": 3750000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "1 to 3 months",
            "stages": [
                {"stage_order": 1, "stage_name": "Form I-20 Issuance & SEVIS Fee", "duration_days": 14},
                {"stage_order": 2, "stage_name": "Form DS-160 & Consular Interview Slot", "duration_days": 21},
                {"stage_order": 3, "stage_name": "Visa Stamping & Passport Return", "duration_days": 7}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Form I-20 Certificate of Eligibility (SEVP)", "category": "Academic Form", "form_code": "I-20", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Form DS-160 Confirmation & SEVIS I-901 Payment Receipt", "category": "Statutory Form", "form_code": "DS-160", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Liquid Financial Solvency Proof (1st Year Tuition + Living Expenses)", "category": "Financial", "form_code": "FIN-PROOF", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Study in world-class American universities and access up to 3 years of STEM OPT work authorization leading into H-1B and Green Card sponsorship.",
            "target_client": "Students seeking Bachelor's, Master's, or PhD programs in the United States.",
            "pitch_points": ["Access top global universities", "36-month STEM OPT work rights", "On-campus employment allowed from Day 1"]
        },
        "objections_rebuttals": [{"objection": "US visa interview rejection rates are high.", "rebuttal": "We conduct 3 rounds of 1-on-1 mock consular interview preparation covering financial ties, intent to return, and university defense.", "probability": "High"}],
        "faqs": [{"question": "Can I work off-campus on F-1?", "answer": "You can work off-campus through Curricular Practical Training (CPT) after your first academic year, and through Optional Practical Training (OPT) upon graduation."}]
    },
    {
        "id": "pm_usa_b1_b2",
        "name": "US B-1 / B-2 Visitor Visa (Business & Tourism)",
        "country": "United States",
        "country_code": "US",
        "flag": "🇺🇸",
        "category": "visitor",
        "visa_type": "Nonimmigrant Visitor Visa",
        "visa_subclass": "B-1/B-2",
        "status": "active",
        "authority_name": "U.S. Department of State",
        "official_portal_url": "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html",
        "vfs_url": "https://travel.state.gov",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "10-year multiple-entry nonimmigrant visa allowing up to 6 months stay per visit for tourism, family visits, business meetings, contract negotiations, and medical treatment.",
        "description": "Requires proving strong social, economic, and family ties to your home country to rebut immigrant intent under INA 214(b).",
        "eligibility_criteria": {
            "age_min": 0,
            "minimum_qualification": "None",
            "work_experience_years": 0,
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "USD",
            "primary_applicant": 185.0,
            "source_link": "https://travel.state.gov"
        },
        "pricing": {
            "base_fee": 2500000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 100000,
            "agent_commission": 50000,
            "milestones": [
                {"stage_number": 1, "name": "DS-160 Filing & Fee Payment", "percentage": 50, "amount_paise": 1250000},
                {"stage_number": 2, "name": "Appointment Scheduling & Interview Prep", "percentage": 50, "amount_paise": 1250000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "Consular appointment wait times vary by post (emergency slots expedited in 5-10 days)",
            "stages": [
                {"stage_order": 1, "stage_name": "Form DS-160 Submission", "duration_days": 3},
                {"stage_order": 2, "stage_name": "Consular Biometrics & Interview", "duration_days": 1},
                {"stage_order": 3, "stage_name": "10-Year Visa Stamping & Return", "duration_days": 5}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "Form DS-160 Barcode Confirmation Page", "category": "Statutory Form", "form_code": "DS-160", "applicant_scope": "both", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Employment Letter / Business Ownership / Property Deeds (Strong Ties)", "category": "Financial", "form_code": "TIES-PROOF", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "Travel Itinerary / Conference Registration / Invitation Letter", "category": "Purpose", "form_code": "TRAVEL-ITIN", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "Get a 10-year multiple entry US visa for business conferences, client meetings, or holidaying across the United States with full family support.",
            "target_client": "Corporate travelers, tourists, conference attendees, and parents visiting children.",
            "pitch_points": ["10-year validity with multiple entries", "Up to 180 days stay per trip", "Fast emergency expedition available"]
        },
        "objections_rebuttals": [{"objection": "Appointment wait times are over 1 year in India.", "rebuttal": "We monitor daily slot cancellations and help file emergency expedited appointments for business or family reasons.", "probability": "High"}],
        "faqs": [{"question": "Can I convert B-1/B-2 to H-1B or F-1 while inside the US?", "answer": "Yes, you can file a Form I-539 change of status to F-1 or change of employer petition to H-1B under USCIS regulations."}]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # NEW ZEALAND
    # ──────────────────────────────────────────────────────────────────────────
    {
        "id": "pm_nz_smc",
        "name": "NZ Skilled Migrant Category Resident Visa (6-Point System)",
        "country": "New Zealand",
        "country_code": "NZ",
        "flag": "🇳🇿",
        "category": "skilled_migration",
        "visa_type": "Permanent Residency (6-Point SMC)",
        "visa_subclass": "SMC",
        "status": "active",
        "authority_name": "Immigration New Zealand (INZ)",
        "official_portal_url": "https://www.immigration.govt.nz/new-zealand-visas/visas/visa/skilled-migrant-category-resident-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "migrate_page_url": "https://leamss.com/migrate",
        "summary": "New Zealand's simplified 6-point permanent resident visa system based on NZ occupational registration, bachelor/master/doctoral qualifications, or high income, coupled with a skilled job offer.",
        "description": "Grants direct Indefinite Resident Visa with full public healthcare and schooling rights across New Zealand.",
        "eligibility_criteria": {
            "age_min": 18,
            "age_max": 55,
            "minimum_qualification": "Bachelor's Degree (NZQF Level 7+)",
            "work_experience_years": 1,
            "english_requirements": {"competency_level": "IELTS General 6.5 overall or PTE Academic 58", "ielts_overall": 6.5, "pte_overall": 58},
            "points_based": {"is_points_tested": True, "minimum_points": 6},
            "health_character_mandatory": True
        },
        "government_costs": {
            "currency": "NZD",
            "primary_applicant": 4290.0,
            "source_link": "https://www.immigration.govt.nz"
        },
        "pricing": {
            "base_fee": 15000000,
            "currency": "INR",
            "tax_rate": 18,
            "sales_commission": 500000,
            "agent_commission": 300000,
            "milestones": [
                {"stage_number": 1, "name": "NZQA Qualification Assessment & Points Audit", "percentage": 40, "amount_paise": 6000000},
                {"stage_number": 2, "name": "EOI Filing & Invitation", "percentage": 30, "amount_paise": 4500000},
                {"stage_number": 3, "name": "INZ Residence Grant", "percentage": 30, "amount_paise": 4500000}
            ]
        },
        "processing_timeline": {
            "standard_duration": "4 to 8 months",
            "stages": [
                {"stage_order": 1, "stage_name": "NZQA International Qualification Assessment", "duration_days": 35},
                {"stage_order": 2, "stage_name": "EOI Submission & Invitation to Apply", "duration_days": 14},
                {"stage_order": 3, "stage_name": "INZ Resident Visa Lodgement (INZ 1015/1007)", "duration_days": 30},
                {"stage_order": 4, "stage_name": "Resident Visa Grant", "duration_days": 90}
            ]
        },
        "document_checklist_template": [
            {"id": str(uuid.uuid4()), "document_name": "INZ 1015 - Skilled Migrant Category Expression of Interest", "category": "Statutory Form", "form_code": "INZ 1015", "applicant_scope": "primary_applicant", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "INZ 1007 - General Medical Certificate Form", "category": "Health", "form_code": "INZ 1007", "applicant_scope": "all_family", "is_mandatory": True},
            {"id": str(uuid.uuid4()), "document_name": "NZQA International Qualifications Assessment (IQA)", "category": "Academic", "form_code": "NZQA-IQA", "applicant_scope": "primary_applicant", "is_mandatory": True}
        ],
        "sales_playbook": {
            "elevator_pitch": "New Zealand's 6-point SMC is straightforward and transparent. Once you have 6 points, you get direct permanent resident status with pristine quality of life and safety.",
            "target_client": "Professionals with higher education or skilled NZ job offers.",
            "pitch_points": ["Clear 6-point threshold", "Direct Resident Visa", "Unrivaled safety and clean green lifestyle"]
        },
        "objections_rebuttals": [{"objection": "Do I need a job offer in New Zealand?", "rebuttal": "Yes, having an accredited employer job offer locks in your residency approval.", "probability": "High"}],
        "faqs": [{"question": "Can I travel to Australia with NZ Permanent Residence?", "answer": "Once you obtain New Zealand Citizenship, you have reciprocal rights to live and work in Australia without a visa."}]
    }
]


def get_canonical_seeds() -> List[Dict[str, Any]]:
    """Return all verified statutory canonical product seeds."""
    return CANONICAL_SEEDS
