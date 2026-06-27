"""Sweep B.2 — Manual Fast-Path seeder for verified country visa workflows.

Idempotent — skips if a workflow with same (country_code, subclass_id, service_type)
already exists with status='verified'.

Usage:
    cd /app/backend && python -m scripts.seed_country_workflows_b2 --country AU
    cd /app/backend && python -m scripts.seed_country_workflows_b2 --all

Sources cited per workflow in `verified_notes`. Fees + processing times verified
against official .gov references as of Feb 2026 (FY2025-26 for AU/NZ, IRCC current
for CA, UKVI current for UK).
"""
from __future__ import annotations
import argparse
import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────────────────────
# AUSTRALIA (AU) — 6 verified subclasses
# Source: immi.homeaffairs.gov.au · FY2025-26 rates · FX: 1 AUD ≈ 55 INR
# ──────────────────────────────────────────────────────────────────────────────
AUSTRALIA_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. Subclass 189 — Skilled Independent ───────────────────────────────────
    {
        "country_code": "AU",
        "country_name": "Australia",
        "subclass_id": "189",
        "subclass_name": "Skilled Independent (Subclass 189)",
        "service_type": "pr",
        "category": "immigration",
        "description": (
            "The Subclass 189 Skilled Independent visa is a permanent residence visa for skilled workers "
            "who are not sponsored by an employer, family member, or state/territory. It is points-tested "
            "(minimum 65 points; competitive invitation cutoffs typically 85-95+ in FY2025-26) and requires "
            "a positive skills assessment in an eligible occupation on the Medium and Long-term Strategic "
            "Skills List (MLTSSL).\n\nVisa holders gain full PR rights from day one — live, work, study "
            "anywhere in Australia, access Medicare, and after a residency period, apply for Australian "
            "citizenship. Family members (partner + dependent children) can be included in the application. "
            "Visa is granted indefinitely, with a 5-year travel facility (renewable via Resident Return Visa)."
        ),
        "eligibility_summary": (
            "Must be under 45 at invitation; demonstrate Competent English (IELTS 6.0 each band or equivalent); "
            "hold a positive skills assessment in an MLTSSL occupation; score minimum 65 points on the SkillSelect "
            "points test; pass health and character requirements."
        ),
        "eligibility_criteria": [
            {"label": "Age", "value": "Under 45 at time of invitation", "notes": "Hard cap — no exemptions"},
            {"label": "English", "value": "Competent (IELTS 6.0 each band, PTE 50, TOEFL iBT 60)", "notes": "Higher scores earn more points (Proficient 7.0 = +10, Superior 8.0 = +20)"},
            {"label": "Skills Assessment", "value": "Positive outcome from designated authority for MLTSSL occupation", "notes": "Valid for 3 years from issue OR validity period stated by authority"},
            {"label": "Points threshold", "value": "Minimum 65 points; competitive 85-95+", "notes": "FY2025-26 invitation rounds favoured 90+ for most occupations"},
            {"label": "Occupation list", "value": "MLTSSL (Medium and Long-term Strategic Skills List)", "notes": "Check current list at immi.homeaffairs.gov.au"},
            {"label": "Health", "value": "Pass health examinations", "notes": "Includes HIV test for 15+; medical exam from approved panel doctors"},
            {"label": "Character", "value": "Provide PCC from every country lived in 12+ months since age 16", "notes": "Includes India PCC; may need state-level certs"},
            {"label": "EOI in SkillSelect", "value": "Mandatory before invitation", "notes": "EOI valid for 2 years; updated as circumstances change"},
        ],
        "fees_local_currency_code": "AUD",
        "fees_local_currency_amount": 4640,
        "fees_inr_approx": 255200,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary Applicant", "amount": 4640, "currency": "AUD"},
            {"component": "Visa Application Charge — Secondary Applicant 18+", "amount": 2320, "currency": "AUD"},
            {"component": "Visa Application Charge — Dependent Child Under 18", "amount": 1160, "currency": "AUD"},
            {"component": "Skills Assessment (varies by authority — e.g. ACS ~AUD 530, VETASSESS ~AUD 1,131)", "amount": 800, "currency": "AUD"},
            {"component": "English Test (PTE/IELTS in India)", "amount": 16800, "currency": "INR"},
            {"component": "Health Examination (BUPA in India)", "amount": 6000, "currency": "INR"},
            {"component": "Police Clearance Certificate (India PSK)", "amount": 500, "currency": "INR"},
            {"component": "Document translation/notarisation buffer", "amount": 5000, "currency": "INR"},
        ],
        "processing_time_days_min": 240,
        "processing_time_days_max": 540,
        "step_by_step": [
            {"step_number": 1, "title": "Identify ANZSCO Occupation", "description": "Match your job role and qualifications to an MLTSSL occupation. Carefully read the ANZSCO unit group description.", "estimated_days": 7, "documents_needed": ["Resume/CV with detailed role descriptions", "Job descriptions from current/past employers"], "tips": ["Use exact ANZSCO occupation title — even minor variations can fail SA", "Verify your occupation is currently on MLTSSL (lists change)"]},
            {"step_number": 2, "title": "Skills Assessment", "description": "Apply to the relevant assessing authority for your occupation (e.g. ACS for ICT, VETASSESS for general professional, EA for engineers, AITSL for teachers).", "estimated_days": 60, "documents_needed": ["Degree certificates + transcripts (notarised)", "Employment reference letters (on letterhead, with role + dates + duties)", "Pay slips / Form 16 / tax returns", "Resume aligned to occupation"], "tips": ["Use the authority's exact reference letter template if provided", "Most authorities have a 'priority' option for an extra fee", "Apply early — backlogs can take 12+ weeks"]},
            {"step_number": 3, "title": "English Language Test", "description": "Take PTE Academic, IELTS, TOEFL iBT, OET, or CAE. Higher score = more points.", "estimated_days": 21, "documents_needed": ["Passport for ID at test centre"], "tips": ["PTE is widely preferred (faster results, computer-based)", "Book 2-3 attempts buffer — competitive applicants target Superior 8.0 IELTS / PTE 79"]},
            {"step_number": 4, "title": "Submit Expression of Interest (EOI) in SkillSelect", "description": "Create SkillSelect account at immi.homeaffairs.gov.au, submit EOI with full details: education, work, English, age, partner skills.", "estimated_days": 1, "documents_needed": ["Skills assessment outcome ref", "English test result", "Passport", "Marriage certificate (if claiming partner points)"], "tips": ["EOI valid 2 years — update if anything changes", "Claim ONLY points you can prove later", "Higher points = faster invitation"]},
            {"step_number": 5, "title": "Receive Invitation to Apply (ITA)", "description": "Wait for invitation round. DoHA conducts rounds monthly (currently quarterly for some pro rata occupations). You have 60 days from invitation to lodge.", "estimated_days": 90, "documents_needed": [], "tips": ["Keep all documents ready BEFORE invitation", "ITA can be received at any monthly round — be prepared"]},
            {"step_number": 6, "title": "Lodge Visa Application", "description": "Complete and submit Form 1276 (electronic), upload all evidence within 60 days of ITA.", "estimated_days": 14, "documents_needed": ["Passport bio page (all applicants)", "Birth certificates", "Marriage/relationship evidence", "Skills assessment outcome", "English test result", "Employment evidence (reference letters, pay slips, tax returns)", "Education certificates with transcripts", "Photo (passport size, recent)"], "tips": ["Upload organised by category (Form 80 for adult applicants is mandatory)", "Use clear, high-resolution scans"]},
            {"step_number": 7, "title": "Health Examinations", "description": "Complete at BUPA-approved panel clinic in India. Includes chest X-ray, HIV test, medical exam.", "estimated_days": 21, "documents_needed": ["HAP ID generated from ImmiAccount", "Passport for ID at clinic"], "tips": ["Book within 7 days of receiving HAP ID", "Bring previous medical records for chronic conditions"]},
            {"step_number": 8, "title": "Police Clearance Certificates (PCCs)", "description": "Obtain PCC from India (PSK or VFS), plus every country lived in 12+ months since age 16.", "estimated_days": 30, "documents_needed": ["Passport", "Address proof", "Form for PCC application"], "tips": ["India PCC valid for 12 months — time it close to lodgement", "For foreign PCCs, start early — some take 8+ weeks"]},
            {"step_number": 9, "title": "Decision and Visa Grant", "description": "Case officer reviews. May request more info (RFI) or interview. On approval, you receive a visa grant notice via ImmiAccount.", "estimated_days": 300, "documents_needed": ["Updated documents if RFI received"], "tips": ["Respond to RFI within 28 days", "Visa is electronic — no label in passport needed"]},
            {"step_number": 10, "title": "Initial Entry to Australia", "description": "Travel to Australia within the date specified on the visa grant notice (typically 12 months from grant or earliest of skills assessment / medical / PCC validity).", "estimated_days": 30, "documents_needed": ["Passport", "Grant notice (printed)"], "tips": ["Activate visa by entering before 'must-enter-by' date", "Settle in nominated state if claiming any state-related points"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (bio page + all visa pages)", "mandatory": True, "notes": "Min 6 months validity at time of grant"},
            {"name": "Birth certificate", "mandatory": True, "notes": "If not in English, notarised translation required"},
            {"name": "Skills Assessment outcome letter", "mandatory": True, "notes": "From designated authority for your ANZSCO"},
            {"name": "English test results (PTE/IELTS/TOEFL/OET/CAE)", "mandatory": True, "notes": "Valid 3 years from test date"},
            {"name": "Degree certificate + transcripts", "mandatory": True, "notes": "Notarised; transcripts must show subjects + grades"},
            {"name": "Employment reference letters", "mandatory": True, "notes": "On company letterhead, signed, with role + duties + dates + hours"},
            {"name": "Pay slips / Form 16 / Tax returns", "mandatory": True, "notes": "Covering each employment period claimed"},
            {"name": "Form 80 (Personal Particulars for Character Assessment)", "mandatory": True, "notes": "Mandatory for each adult applicant"},
            {"name": "Form 1221 (Additional Personal Particulars)", "mandatory": False, "notes": "May be requested for some applicants"},
            {"name": "Health Examination (HAP ID complete)", "mandatory": True, "notes": "BUPA panel clinic in India"},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": "India + every country lived in 12+ months since age 16"},
            {"name": "Marriage/relationship certificate (if migrating with partner)", "mandatory": True, "notes": "Plus evidence of de facto if not married"},
            {"name": "Children's birth certificates (if migrating with children)", "mandatory": True, "notes": "Establishing relationship"},
            {"name": "Passport-size photograph", "mandatory": True, "notes": "Recent (within 6 months)"},
            {"name": "CV/Resume", "mandatory": True, "notes": "Detailed, aligned to ANZSCO occupation"},
            {"name": "Partner English / Skills assessment (if claiming partner points)", "mandatory": False, "notes": "Required only if claiming 5 or 10 points for partner"},
        ],
        "common_rejection_reasons": [
            "Skills assessment expired or for a different ANZSCO than claimed in EOI",
            "Insufficient English score for points claimed in EOI",
            "Employment reference letters lack required detail (duties, dates, hours)",
            "Form 80 incomplete or inconsistent with other documents",
            "Health requirement not met — undisclosed medical condition",
            "Character issue — undisclosed criminal record or visa cancellation history",
            "Claimed points cannot be verified at lodgement (e.g., claiming partner skills without partner SA)",
            "Document not in English without certified translation",
        ],
        "success_tips": [
            "Maximise points BEFORE submitting EOI — aim 85+ to be competitive",
            "Use NAATI-accredited translator (5 points if NAATI-certified in community language)",
            "Submit complete application within 24 hours of ITA — no incremental uploads",
            "Get expert review of Form 80 before lodgement — it's the most-rejected form",
            "Front-load high-quality reference letters — request them from employers WELL before SA",
            "Keep EOI updated — even minor changes (new English score, work anniversary) may move you forward",
            "Bookmark immi.homeaffairs.gov.au for invitation round announcements",
            "Time medical and PCC close to lodgement — both have 12-month validity",
        ],
        "faqs": [
            {"q": "Can I include my partner and children in the same application?", "a": "Yes — partner (married/de facto) and dependent children under 23 (or older with disability) can be included. Each pays the secondary applicant visa fee. They get the same PR rights as you."},
            {"q": "Do I need a job offer to apply?", "a": "No — Subclass 189 is independent (non-sponsored). You can apply without any job offer. However, having Australian work experience earns points."},
            {"q": "What is the minimum points threshold for invitation?", "a": "Officially 65 but in practice 85-95+ in FY2025-26 for most occupations. Pro rata occupations (e.g. accountants, engineers) often need 95+."},
            {"q": "Can I apply onshore?", "a": "Yes — you can apply from inside or outside Australia. You must be onshore OR offshore at time of grant (your choice at application)."},
            {"q": "How long does the visa take to process?", "a": "Current published times: 75% within 11 months, 90% within 13 months. Some occupations may be quicker; complex cases longer."},
            {"q": "What if my English score expires while waiting?", "a": "English is valid 3 years from test date for points purposes. If it expires before lodgement, retake. Once lodged, validity is locked in."},
            {"q": "Can I change occupations after invitation?", "a": "Generally no — the visa is granted on the basis of your claimed occupation and skills assessment. You can change jobs after grant (PR has no occupation restriction)."},
            {"q": "Do I need to live in any particular state?", "a": "No — Subclass 189 is independent of any state. You can live anywhere in Australia."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189",
            "https://immi.homeaffairs.gov.au/visas/working-in-australia/skillselect",
            "https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list",
            "https://immi.homeaffairs.gov.au/help-support/meeting-our-requirements/health",
            "https://immi.homeaffairs.gov.au/help-support/meeting-our-requirements/character/character-requirements",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immi.homeaffairs.gov.au on 2026-02-26. FY2025-26 fees. Processing times per current Departmental processing time pages.",
    },

    # ── 2. Subclass 190 — Skilled Nominated ─────────────────────────────────────
    {
        "country_code": "AU",
        "country_name": "Australia",
        "subclass_id": "190",
        "subclass_name": "Skilled Nominated (Subclass 190)",
        "service_type": "pr",
        "category": "immigration",
        "description": (
            "The Subclass 190 Skilled Nominated visa is a points-tested permanent residence visa for skilled "
            "workers who have been nominated by an Australian state or territory government. Nomination earns "
            "an additional 5 points (often the difference between a competitive and uncompetitive EOI).\n\n"
            "Applicants must commit to living and working in the nominating state for 2 years after grant. The "
            "visa allows full PR rights nationwide, but the moral commitment to the nominating state matters for "
            "future eligibility under the same program for family/friends. Occupations must appear on the "
            "Combined State Occupation List or the state's own list — usually broader than the MLTSSL."
        ),
        "eligibility_summary": (
            "Under 45 at invitation, Competent English, positive skills assessment in an occupation on the "
            "Combined State Occupation List, minimum 65 points (with nomination bonus), and a successful nomination "
            "by an Australian state or territory."
        ),
        "eligibility_criteria": [
            {"label": "Age", "value": "Under 45 at time of invitation", "notes": "Hard cap"},
            {"label": "English", "value": "Competent (IELTS 6.0 / PTE 50)", "notes": "State may set higher English requirement"},
            {"label": "Skills Assessment", "value": "Positive outcome in eligible occupation", "notes": "Occupation must be on Combined State Occupation List or specific state's list"},
            {"label": "Points threshold", "value": "65 minimum (state nomination adds +5)", "notes": "Effective 70+ with nomination; competitive 80+"},
            {"label": "State Nomination", "value": "Must apply directly to the state/territory and be selected", "notes": "Each state has its own program, criteria, and quotas"},
            {"label": "Commitment to nominating state", "value": "Live + work in nominating state for 2 years", "notes": "Not legally enforceable on visa but reflects in future state programs"},
            {"label": "Health + Character", "value": "Same as 189", "notes": "Standard requirements"},
        ],
        "fees_local_currency_code": "AUD",
        "fees_local_currency_amount": 4640,
        "fees_inr_approx": 255200,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary", "amount": 4640, "currency": "AUD"},
            {"component": "Visa Application Charge — Secondary 18+", "amount": 2320, "currency": "AUD"},
            {"component": "State Nomination Application Fee (e.g. NSW ~AUD 300, VIC ~AUD 190, QLD ~AUD 200)", "amount": 250, "currency": "AUD"},
            {"component": "Skills Assessment", "amount": 800, "currency": "AUD"},
            {"component": "English Test (PTE/IELTS in India)", "amount": 16800, "currency": "INR"},
            {"component": "Health Examination", "amount": 6000, "currency": "INR"},
            {"component": "Police Clearance Certificates", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 270,
        "processing_time_days_max": 540,
        "step_by_step": [
            {"step_number": 1, "title": "Research State Programs", "description": "Each Australian state has its own nomination criteria, occupation list, quotas, and processing windows. Compare NSW, VIC, QLD, SA, WA, TAS, ACT, NT.", "estimated_days": 14, "documents_needed": [], "tips": ["Look at occupation list AND commitment requirements", "Some states require prior connection (study/work) — others don't"]},
            {"step_number": 2, "title": "Skills Assessment", "description": "Apply through relevant authority for your ANZSCO occupation on Combined State Occupation List.", "estimated_days": 60, "documents_needed": ["Degree", "Reference letters", "CV"], "tips": ["Same as 189 — but list may be broader"]},
            {"step_number": 3, "title": "English Test", "description": "PTE/IELTS/TOEFL/OET — state may require Proficient (7.0+) or higher for certain occupations.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["Check state-specific English requirements"]},
            {"step_number": 4, "title": "Submit EOI in SkillSelect", "description": "Indicate state nomination preference. State views your EOI and decides whether to invite you.", "estimated_days": 1, "documents_needed": ["SA outcome", "English test", "Passport"], "tips": ["You can list multiple states — but most reward strong commitment to ONE"]},
            {"step_number": 5, "title": "State Nomination Application", "description": "Once a state expresses interest (via EOI selection or open program), submit detailed nomination application with state-specific evidence (e.g., commitment statement, job search evidence).", "estimated_days": 45, "documents_needed": ["Detailed CV", "Cover letter / commitment statement", "Evidence of state ties (if any)", "Financial capacity evidence"], "tips": ["Be specific about why THIS state — generic applications fail", "Show research into local labour market"]},
            {"step_number": 6, "title": "Receive State Nomination + ITA", "description": "If approved by state, +5 points apply to your EOI. DoHA then sends ITA via SkillSelect (usually within days of nomination).", "estimated_days": 30, "documents_needed": [], "tips": ["State nomination is valid 6 months — use it before expiry"]},
            {"step_number": 7, "title": "Lodge Visa Application", "description": "Same as 189 — submit Form 1276 within 60 days of ITA.", "estimated_days": 14, "documents_needed": ["Full document set as 189"], "tips": []},
            {"step_number": 8, "title": "Health + PCCs", "description": "Standard health exam and PCCs.", "estimated_days": 30, "documents_needed": ["HAP ID", "Passport"], "tips": []},
            {"step_number": 9, "title": "Decision and Grant", "description": "Case officer reviews. Standard processing.", "estimated_days": 365, "documents_needed": [], "tips": ["Respond to RFIs within 28 days"]},
            {"step_number": 10, "title": "Settle in Nominating State", "description": "Move to and live/work in the nominating state for 2 years.", "estimated_days": 30, "documents_needed": ["Visa grant notice"], "tips": ["Maintain residence ties — utility bills, tenancy, employment in state"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio page)", "mandatory": True, "notes": ""},
            {"name": "Skills assessment outcome", "mandatory": True, "notes": "Combined State Occupation List or state-specific"},
            {"name": "English test results", "mandatory": True, "notes": "Competent minimum; state may require Proficient"},
            {"name": "Degree + transcripts", "mandatory": True, "notes": "Notarised"},
            {"name": "Employment reference letters", "mandatory": True, "notes": "Same standard as 189"},
            {"name": "State nomination evidence (commitment statement, job evidence)", "mandatory": True, "notes": "State-specific"},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "Health exam (HAP ID)", "mandatory": True, "notes": "BUPA"},
            {"name": "Police clearances (all 12+ month countries)", "mandatory": True, "notes": ""},
            {"name": "Marriage / relationship cert (if migrating with partner)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Photo (recent)", "mandatory": True, "notes": ""},
            {"name": "State-specific commitment statement", "mandatory": True, "notes": "Why this state — be specific"},
            {"name": "Financial capacity evidence", "mandatory": True, "notes": "State may require AUD 25-50k bank balance"},
        ],
        "common_rejection_reasons": [
            "Insufficient evidence of commitment to nominating state",
            "Generic, non-tailored state nomination application",
            "Occupation not on the state's specific list (despite being on Combined SOL)",
            "State quota exhausted for your occupation in that round",
            "Failure to meet state's higher English requirement",
            "Same as 189: insufficient documentation, points cannot be verified",
        ],
        "success_tips": [
            "Research EACH state's program carefully — they're not interchangeable",
            "Show specific local labour market research and job search evidence",
            "Demonstrate prior ties to state if any (study, family, work)",
            "Lock in state-required English score BEFORE applying",
            "Keep state's nomination criteria document for reference during visa lodgement",
            "Standard 189 points-building tips apply",
        ],
        "faqs": [
            {"q": "Can I apply to multiple states?", "a": "Technically you can list multiple states in your EOI. Practically, each state wants to see you committed to THEM specifically. Most successful applicants target ONE state."},
            {"q": "What if I don't stay in the nominating state for 2 years?", "a": "There's no legal sanction on the visa itself — once granted, you have full PR. However, the moral commitment matters; future state programs may scrutinize your file if you've broken a previous nomination."},
            {"q": "Do I get more points than Subclass 189?", "a": "Yes — state nomination adds 5 points. So if you're at 70 base, you'd be 75 effective. Some occupations only invite via 190 (not enough 189 invites)."},
            {"q": "Which state is easiest?", "a": "Depends on your occupation. NSW has biggest quota; TAS and NT historically had broader occupation lists; QLD and SA reward state-connected applicants. Check each state's current list."},
            {"q": "Can I change states after grant?", "a": "After 2 years of commitment, you have full PR mobility. Within 2 years, technically allowed but ethically discouraged."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-nominated-190",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-nominated-190",
            "https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-nominated-190/state-nominations",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immi.homeaffairs.gov.au and state migration websites on 2026-02-26. State fees averaged across NSW/VIC/QLD; check individual state at time of application.",
    },

    # ── 3. Subclass 491 — Skilled Work Regional (Provisional) ───────────────────
    {
        "country_code": "AU",
        "country_name": "Australia",
        "subclass_id": "491",
        "subclass_name": "Skilled Work Regional (Provisional) (Subclass 491)",
        "service_type": "pr",
        "category": "immigration",
        "description": (
            "The Subclass 491 Skilled Work Regional (Provisional) visa is a 5-year temporary visa for skilled "
            "workers willing to live and work in regional Australia. After 3 years of regional residence with "
            "minimum income thresholds met, holders can apply for the Subclass 191 Permanent Residence (Skilled "
            "Regional) visa.\n\nThe 491 carries a generous +15 points bonus from state nomination or eligible "
            "family sponsorship — often pushing borderline applicants comfortably above invitation thresholds. "
            "It's a popular pathway for those who didn't qualify for 189/190 but want to migrate to Australia. "
            "Regional Australia for this visa = anywhere except Sydney/Melbourne/Brisbane CBDs."
        ),
        "eligibility_summary": (
            "Under 45 at invitation, Competent English, positive skills assessment in regional occupation list, "
            "minimum 65 points (with +15 bonus from nomination/family sponsor), and either state nomination "
            "or eligible family sponsor in a designated regional area."
        ),
        "eligibility_criteria": [
            {"label": "Age", "value": "Under 45 at invitation", "notes": "Hard cap"},
            {"label": "English", "value": "Competent (IELTS 6.0)", "notes": "State may require higher"},
            {"label": "Skills Assessment", "value": "Positive outcome in regional occupation list", "notes": "Broader list than MLTSSL/STSOL"},
            {"label": "Points", "value": "65 minimum (+15 with nomination/sponsor = effective 80+)", "notes": "Most competitive at 90+"},
            {"label": "Sponsorship", "value": "EITHER state/territory nomination OR eligible family member living in designated regional area", "notes": "Family sponsor: parent, child, sibling, aunt/uncle, niece/nephew, grandparent who is AU citizen/PR"},
            {"label": "Regional commitment", "value": "Live + work + study in designated regional area for 3 years", "notes": "Mandatory to qualify for 191 PR pathway"},
            {"label": "Income threshold (for 191 pathway)", "value": "Minimum AUD 53,900 income (FY2024-25)", "notes": "Must be met for at least 3 years to apply for 191 PR"},
            {"label": "Health + Character", "value": "Same as 189", "notes": ""},
        ],
        "fees_local_currency_code": "AUD",
        "fees_local_currency_amount": 4640,
        "fees_inr_approx": 255200,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary", "amount": 4640, "currency": "AUD"},
            {"component": "Secondary applicant 18+", "amount": 2320, "currency": "AUD"},
            {"component": "Dependent child <18", "amount": 1160, "currency": "AUD"},
            {"component": "State nomination fee (varies)", "amount": 200, "currency": "AUD"},
            {"component": "Skills assessment", "amount": 800, "currency": "AUD"},
            {"component": "English test", "amount": 16800, "currency": "INR"},
            {"component": "Future Subclass 191 PR application (after 3 years regional)", "amount": 535, "currency": "AUD"},
        ],
        "processing_time_days_min": 240,
        "processing_time_days_max": 450,
        "step_by_step": [
            {"step_number": 1, "title": "Identify Regional Pathway", "description": "Decide: state nomination route, or family sponsorship route. Check which states have your occupation on regional list, or whether you have eligible family in designated regional area.", "estimated_days": 14, "documents_needed": [], "tips": ["Family sponsor must be in designated regional postcode — not just any non-CBD area", "States like TAS, SA, NT have broader regional occupation lists"]},
            {"step_number": 2, "title": "Skills Assessment", "description": "Apply for SA in regional occupation list ANZSCO.", "estimated_days": 60, "documents_needed": ["Degree", "Reference letters"], "tips": []},
            {"step_number": 3, "title": "English Test", "description": "Competent English minimum.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": []},
            {"step_number": 4, "title": "Submit EOI", "description": "Choose 491 visa, indicate nomination preference (state OR family).", "estimated_days": 1, "documents_needed": ["SA outcome", "English"], "tips": ["The +15 bonus is applied once nomination is in place"]},
            {"step_number": 5, "title": "Obtain State Nomination OR Family Sponsorship", "description": "For state: apply to state migration program. For family: complete sponsor's affidavit + evidence of regional residence + relationship proof.", "estimated_days": 60, "documents_needed": ["Family relationship proof (birth certs, marriage certs)", "Sponsor's PR/citizenship proof", "Sponsor's regional residence proof (utility bills, tenancy)"], "tips": ["Family sponsorship is faster than state nomination but has fewer occupations"]},
            {"step_number": 6, "title": "Receive ITA", "description": "DoHA issues invitation within ~14 days of nomination/sponsor approval.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Lodge Visa Application", "description": "Submit electronic application with full document set within 60 days.", "estimated_days": 14, "documents_needed": ["Standard 189/190 document set"], "tips": []},
            {"step_number": 8, "title": "Health + PCCs", "description": "Standard.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 9, "title": "Decision + Grant", "description": "Visa granted for 5 years.", "estimated_days": 240, "documents_needed": [], "tips": []},
            {"step_number": 10, "title": "Move to Regional Area + Build 191 Pathway", "description": "Live + work in designated regional area for 3 years minimum, earning AUD 53,900+ for 3 income years.", "estimated_days": 1095, "documents_needed": ["Tax returns (notice of assessment)", "Employment evidence"], "tips": ["Save all PAYG summaries — needed for 191", "Don't move outside regional area without checking compliance"]},
        ],
        "document_checklist": [
            {"name": "Passport", "mandatory": True, "notes": ""},
            {"name": "Skills Assessment (regional list)", "mandatory": True, "notes": ""},
            {"name": "English test results", "mandatory": True, "notes": ""},
            {"name": "Degree + transcripts", "mandatory": True, "notes": ""},
            {"name": "Employment reference letters", "mandatory": True, "notes": ""},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "Health exam", "mandatory": True, "notes": ""},
            {"name": "PCCs", "mandatory": True, "notes": ""},
            {"name": "State nomination letter OR Form 1232 (family sponsorship)", "mandatory": True, "notes": "One of the two routes"},
            {"name": "Sponsor's evidence of regional residence (if family route)", "mandatory": True, "notes": "Utility bills, tenancy, council rates"},
            {"name": "Sponsor's AU citizenship/PR evidence (if family route)", "mandatory": True, "notes": ""},
            {"name": "Relationship proof (if family route)", "mandatory": True, "notes": "Birth certs, marriage certs"},
            {"name": "Photo", "mandatory": True, "notes": ""},
            {"name": "Marriage/relationship cert (if migrating with partner)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Family sponsor not in designated regional postcode",
            "Sponsor not eligible (must be specific relation + 18+ + AU citizen/PR)",
            "Insufficient evidence of regional commitment",
            "Income threshold not yet met when applying for 191 PR pathway",
            "Occupation not on regional list for that state",
            "Same as 189/190: incomplete documentation, points cannot be verified",
        ],
        "success_tips": [
            "Family sponsorship route is faster than state nomination if you have eligible relative",
            "Plan your 3-year residence + income carefully BEFORE granting — 191 has strict requirements",
            "Save copies of every utility bill, tenancy, and tax return during the 3-year regional period",
            "Keep your employer aware that you may need PAYG summaries for 191 — request early",
            "Designated regional postcodes can change — check immi.gov.au regularly",
            "Many regional employers offer sponsorship + relocation — leverage this",
        ],
        "faqs": [
            {"q": "What is regional Australia?", "a": "Designated regional area excludes Sydney, Melbourne, and Brisbane CBDs. Most of Australia qualifies — including cities like Adelaide, Perth, Hobart, Darwin, Canberra, Newcastle, Wollongong."},
            {"q": "Can I move to a city after 3 years?", "a": "Yes — once you've qualified for and obtained the Subclass 191 PR visa (after 3 years regional residence + income met), you can live anywhere in Australia."},
            {"q": "What if I lose my job in the regional area?", "a": "You have 90 days to find new regional employment. The visa remains valid; just the 191 pathway resets/extends."},
            {"q": "Can my partner work?", "a": "Yes — secondary applicants have full work rights in regional area, but their income doesn't count toward your 191 income threshold."},
            {"q": "How does +15 points work?", "a": "Once you receive state nomination or family sponsor approval, +15 points are automatically applied to your EOI. This is the key advantage of 491 vs 189."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-work-regional-provisional-491",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-work-regional-provisional-491",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-regional-191",
            "https://immi.homeaffairs.gov.au/visas/working-in-australia/regional-migration",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immi.homeaffairs.gov.au on 2026-02-26. Regional postcode definition per current Form 1247.",
    },

    # ── 4. Subclass 482 — Temporary Skill Shortage (TSS) ────────────────────────
    {
        "country_code": "AU",
        "country_name": "Australia",
        "subclass_id": "482",
        "subclass_name": "Temporary Skill Shortage (Subclass 482)",
        "service_type": "work",
        "category": "immigration",
        "description": (
            "The Subclass 482 Temporary Skill Shortage (TSS) visa allows Australian employers to sponsor "
            "overseas skilled workers when they cannot find appropriately skilled Australians. The visa has "
            "three streams: Short-Term (up to 2 years, renewable once), Medium-Term (up to 4 years, with PR "
            "pathway via Subclass 186), and Labour Agreement (specific industry agreements).\n\nThe employer "
            "must first be an approved Standard Business Sponsor (SBS), then nominate the position and applicant. "
            "Labour Market Testing (LMT) is mandatory unless international trade obligations apply. The Skilling "
            "Australians Fund (SAF) levy is paid by the employer at nomination stage."
        ),
        "eligibility_summary": (
            "Skilled worker with at least 2 years' relevant work experience in the nominated occupation. "
            "Must be sponsored by an approved Australian employer in an occupation on the relevant skilled "
            "occupation list (STSOL for Short-Term, MLTSSL for Medium-Term)."
        ),
        "eligibility_criteria": [
            {"label": "Sponsorship", "value": "Australian employer must be approved Standard Business Sponsor (SBS)", "notes": "Employer's responsibility — they apply first"},
            {"label": "Occupation", "value": "On STSOL (Short-Term stream) or MLTSSL (Medium-Term stream)", "notes": "Different streams = different visa durations + PR pathways"},
            {"label": "Work Experience", "value": "Minimum 2 years' relevant experience in the nominated occupation", "notes": "In last 5 years; full-time equivalent"},
            {"label": "Skills Assessment", "value": "Required for some occupations (e.g. trades) — not all", "notes": "Check occupation requirements; often waived for those with strong qualifications + experience"},
            {"label": "English", "value": "Vocational English (IELTS 5.0 each band) for Short-Term; Competent (IELTS 5.0/5.0/5.0/5.0 overall 5.0) for Medium-Term", "notes": "Some passport holders (e.g. UK, USA, Canada, NZ, Ireland) exempt"},
            {"label": "Salary", "value": "Must meet Temporary Skilled Migration Income Threshold (TSMIT) = AUD 73,150 + market rate", "notes": "Effective Jul 2024; updated annually"},
            {"label": "Health + Character", "value": "Standard requirements", "notes": ""},
        ],
        "fees_local_currency_code": "AUD",
        "fees_local_currency_amount": 3115,
        "fees_inr_approx": 171325,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Short-Term stream Primary", "amount": 1495, "currency": "AUD"},
            {"component": "Visa Application Charge — Medium-Term stream Primary", "amount": 3115, "currency": "AUD"},
            {"component": "Secondary applicant 18+ (Medium-Term)", "amount": 3115, "currency": "AUD"},
            {"component": "Dependent child <18 (Medium-Term)", "amount": 780, "currency": "AUD"},
            {"component": "SBS Application (employer) — typically employer-paid", "amount": 420, "currency": "AUD"},
            {"component": "Nomination Application (employer) — typically employer-paid", "amount": 330, "currency": "AUD"},
            {"component": "SAF Levy (small business <AUD 10M turnover, per year of visa)", "amount": 1200, "currency": "AUD"},
            {"component": "SAF Levy (large business >AUD 10M turnover, per year)", "amount": 1800, "currency": "AUD"},
            {"component": "English test (if required)", "amount": 16800, "currency": "INR"},
            {"component": "Health exam", "amount": 6000, "currency": "INR"},
            {"component": "PCC", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 30,
        "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Employer Becomes Approved Sponsor", "description": "Employer applies for Standard Business Sponsor status with DoHA. Valid 5 years.", "estimated_days": 30, "documents_needed": ["Employer business documents (ABN, financials, employees)"], "tips": ["Employer's responsibility — may be in place if they've sponsored before"]},
            {"step_number": 2, "title": "Nomination Application", "description": "Employer nominates the specific position + employee. Includes LMT evidence, SAF levy payment.", "estimated_days": 30, "documents_needed": ["Job ad evidence (LMT)", "Position description", "Employment contract", "SAF levy paid"], "tips": ["LMT requires 28-day job ad on min 2 platforms (e.g. Seek, employer's website)", "Trade exemption applies for some passport nationalities"]},
            {"step_number": 3, "title": "Skills Assessment (if required)", "description": "Some occupations need formal SA; check immi.homeaffairs.gov.au.", "estimated_days": 45, "documents_needed": ["Same as 189"], "tips": ["Often waived for highly-qualified applicants"]},
            {"step_number": 4, "title": "English Test (if not exempt)", "description": "Vocational English for Short-Term (IELTS 5.0 each band).", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["Passport holders of UK, USA, Canada, NZ, Ireland are exempt"]},
            {"step_number": 5, "title": "Lodge Visa Application", "description": "Once nomination approved, employee lodges visa application. Can be onshore or offshore.", "estimated_days": 14, "documents_needed": ["Passport", "Employment evidence (CV + reference letters)", "English test (if required)", "Skills assessment (if required)", "Form 80 + 1221", "Health exam", "PCCs", "Photo"], "tips": ["Apply within 6 months of nomination approval"]},
            {"step_number": 6, "title": "Health + Character", "description": "Standard.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Decision + Grant", "description": "Visa granted for nominated period (2 years ST / 4 years MT). Conditions include sponsor + occupation restriction.", "estimated_days": 90, "documents_needed": [], "tips": ["Can switch employers but new employer must sponsor"]},
            {"step_number": 8, "title": "Work in Australia + Plan PR Pathway", "description": "For MT stream: after 2 years on 482, eligible for 186 ENS PR (Direct Entry stream possible).", "estimated_days": 730, "documents_needed": [], "tips": ["186 ENS Direct Entry requires SA + 3 years work experience"]},
        ],
        "document_checklist": [
            {"name": "Passport", "mandatory": True, "notes": ""},
            {"name": "Employment contract (signed)", "mandatory": True, "notes": "With nominating employer"},
            {"name": "Position description", "mandatory": True, "notes": "Must match nominated occupation"},
            {"name": "CV + reference letters from previous employers", "mandatory": True, "notes": "Demonstrating 2+ years' experience"},
            {"name": "Degree certificates + transcripts", "mandatory": True, "notes": "Notarised"},
            {"name": "English test (if not exempt)", "mandatory": True, "notes": "Vocational or Competent depending on stream"},
            {"name": "Skills Assessment (if required for occupation)", "mandatory": False, "notes": "Check occupation requirements"},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "Form 1221 (each adult)", "mandatory": False, "notes": "May be requested"},
            {"name": "Health exam (HAP ID)", "mandatory": True, "notes": ""},
            {"name": "PCCs (India + other 12+ month countries)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
            {"name": "Marriage/relationship cert (if including partner)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if including)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "LMT requirements not met by employer (insufficient advertising)",
            "Salary below TSMIT or below market rate for occupation",
            "Occupation not on relevant list (STSOL/MLTSSL)",
            "Insufficient evidence of 2 years' relevant work experience",
            "Employer's business position questionable (financial stability, genuine need)",
            "English requirement not met where not exempt",
            "Genuine position not established (e.g. role appears created for the candidate)",
        ],
        "success_tips": [
            "Verify your employer is currently an approved SBS BEFORE accepting offer",
            "Choose Medium-Term stream if PR is your goal — clearer 186 pathway",
            "Document your 2+ years' experience with strong reference letters specifying duties",
            "Ensure salary meets BOTH TSMIT AND market rate for your occupation in your location",
            "Maintain visa conditions strictly — must work in nominated occupation with nominating sponsor",
            "If changing employers, new employer must sponsor + nominate before you start work",
        ],
        "faqs": [
            {"q": "Can I bring my family?", "a": "Yes — partner and dependent children can be included. Partners have full work rights in any occupation on TSS."},
            {"q": "Can I switch employers?", "a": "Yes, but the new employer must become your sponsor + nominate you for the new position. You have 60 days to find a new sponsor if you cease employment."},
            {"q": "What's the difference between Short-Term and Medium-Term?", "a": "Short-Term (up to 2 years, renewable once) is for occupations on STSOL — no direct PR pathway. Medium-Term (up to 4 years) is for MLTSSL occupations — provides clear PR pathway via 186 ENS after 2 years."},
            {"q": "Do I need to pay the SAF levy?", "a": "No — the SAF (Skilling Australians Fund) levy is paid by the EMPLOYER at nomination stage, not by you. Amount depends on employer's turnover."},
            {"q": "Can I apply for PR while on 482?", "a": "Yes — Medium-Term stream provides direct pathway to 186 ENS (Employer Nomination Scheme) PR after 2 years working for the sponsor. Short-Term stream applicants generally cannot transition to PR through ENS."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482",
            "https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/sponsoring-workers/learn-about-sponsoring/saf-levy",
            "https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/sponsoring-workers/labour-market-testing",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immi.homeaffairs.gov.au on 2026-02-26. TSMIT and SAF levy rates per Jul 2024 update.",
    },

    # ── 5. Subclass 500 — Student Visa ──────────────────────────────────────────
    {
        "country_code": "AU",
        "country_name": "Australia",
        "subclass_id": "500",
        "subclass_name": "Student Visa (Subclass 500)",
        "service_type": "student",
        "category": "immigration",
        "description": (
            "The Subclass 500 Student visa allows international students to study full-time at a CRICOS-registered "
            "Australian education provider. Valid for the duration of the course plus 1-3 months. Common pathway to "
            "post-study work (Subclass 485) and longer-term migration via skilled visas.\n\n"
            "Since 2024, the Genuine Student (GS) requirement replaced the Genuine Temporary Entrant (GTE) test, "
            "requiring applicants to explain their genuine intent through a Statement and supporting evidence. "
            "Financial capacity, English proficiency, and a Confirmation of Enrolment (CoE) are core requirements."
        ),
        "eligibility_summary": (
            "Hold a CoE from a CRICOS-registered provider, meet Genuine Student requirement, demonstrate financial "
            "capacity (AUD 29,710/year + tuition + travel), pass English and health requirements, hold Overseas "
            "Student Health Cover (OSHC)."
        ),
        "eligibility_criteria": [
            {"label": "Course enrolment", "value": "CoE from CRICOS-registered provider", "notes": "Public universities and private colleges both eligible"},
            {"label": "Genuine Student", "value": "Statement + evidence of genuine intent", "notes": "Replaced GTE since 2024 — focus on academic history + ties to home country + study purpose"},
            {"label": "Financial capacity", "value": "AUD 29,710/year living costs + tuition + travel", "notes": "Updated to AUD 29,710 from May 2024; some applicants need to show 12 months upfront"},
            {"label": "English", "value": "IELTS 5.5 (under 5.0 for ELICOS) to 6.5 depending on course level", "notes": "Higher universities require 6.5; foundation courses 5.5"},
            {"label": "OSHC", "value": "Mandatory health cover for duration of visa", "notes": "Purchased before grant"},
            {"label": "Age", "value": "No upper limit; under 18 needs welfare arrangements", "notes": ""},
            {"label": "Health + Character", "value": "Standard requirements", "notes": ""},
            {"label": "Working rights", "value": "48 hours per fortnight during course; unlimited during breaks", "notes": "Effective Jul 2023 — relaxed from 40hrs"},
        ],
        "fees_local_currency_code": "AUD",
        "fees_local_currency_amount": 1940,
        "fees_inr_approx": 106700,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary", "amount": 1940, "currency": "AUD"},
            {"component": "Secondary applicant 18+", "amount": 1455, "currency": "AUD"},
            {"component": "Dependent child <18", "amount": 475, "currency": "AUD"},
            {"component": "OSHC (Overseas Student Health Cover) per year", "amount": 700, "currency": "AUD"},
            {"component": "English test (PTE/IELTS in India)", "amount": 16800, "currency": "INR"},
            {"component": "Health exam", "amount": 6000, "currency": "INR"},
            {"component": "PCC", "amount": 500, "currency": "INR"},
            {"component": "Tuition (per year, varies by program; avg)", "amount": 35000, "currency": "AUD"},
        ],
        "processing_time_days_min": 21,
        "processing_time_days_max": 120,
        "step_by_step": [
            {"step_number": 1, "title": "Choose Course + Provider", "description": "Research CRICOS-registered universities and colleges. Compare ranking, tuition, post-study work eligibility, location.", "estimated_days": 30, "documents_needed": [], "tips": ["Check provider rating (some Group of 8 universities better for PSW pathway)", "Group of 8 unis + public universities + dual sector are preferred"]},
            {"step_number": 2, "title": "Apply to University / College", "description": "Submit application to provider. They review and offer admission with conditions (English score, transcripts).", "estimated_days": 30, "documents_needed": ["Degree + transcripts", "English test (if completed)", "CV", "Statement of Purpose"], "tips": ["Apply 6-9 months before intake (Feb/Jul)", "Universities have multiple intakes — Feb (main), Jul (secondary), some Nov"]},
            {"step_number": 3, "title": "Accept Offer + Pay Tuition Deposit", "description": "Accept offer letter, pay first semester (or full year) tuition. Receive CoE.", "estimated_days": 14, "documents_needed": ["Offer letter", "Tuition payment evidence"], "tips": ["CoE is mandatory for visa application", "Some universities accept tuition payments via Flywire/PayMyTuition for Indian students"]},
            {"step_number": 4, "title": "Take English Test (if not already done)", "description": "PTE/IELTS/TOEFL — score must match university entry requirement.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["PTE results in 48 hours, IELTS in 5-7 days"]},
            {"step_number": 5, "title": "Arrange OSHC", "description": "Purchase from approved provider (BUPA, Medibank, Allianz, NIB). Must cover entire visa duration.", "estimated_days": 3, "documents_needed": ["Passport", "Course details"], "tips": ["Compare 4 providers — minor price difference but variable inclusions"]},
            {"step_number": 6, "title": "Prepare Genuine Student Statement", "description": "Write personalised statement covering: academic background, why this course/uni, why Australia (vs home country), ties to home, post-study plans.", "estimated_days": 7, "documents_needed": [], "tips": ["Be specific, not generic", "Mention Australian institution ranking + course content"]},
            {"step_number": 7, "title": "Arrange Financial Documents", "description": "Bank statements showing AUD 29,710 + tuition + travel. Or loan sanction letter from approved Indian bank.", "estimated_days": 14, "documents_needed": ["Bank statements (6 months)", "Loan sanction letter (if applicable)", "Income tax returns (parents/sponsor)", "Fixed deposits / property valuation reports"], "tips": ["Indian banks like SBI Education Loan, HDFC Credila widely accepted", "Funds must be in applicant's or sponsor's name, not borrowed last-minute"]},
            {"step_number": 8, "title": "Lodge Visa Application Online", "description": "Submit via ImmiAccount with all evidence.", "estimated_days": 7, "documents_needed": ["Passport", "CoE", "English test", "GS statement", "Financial evidence", "OSHC certificate", "Photo"], "tips": ["Apply 4-6 weeks before course start", "Indian applicants are Assessment Level 1 — straightforward processing"]},
            {"step_number": 9, "title": "Health + PCC", "description": "BUPA panel health exam, India PCC.", "estimated_days": 21, "documents_needed": ["HAP ID"], "tips": []},
            {"step_number": 10, "title": "Grant + Travel", "description": "Visa typically granted in 3-6 weeks for India. Plan arrival before course start.", "estimated_days": 60, "documents_needed": [], "tips": ["Activate visa by entering Australia before initial entry deadline", "OSHC starts from arrival date"]},
        ],
        "document_checklist": [
            {"name": "Passport", "mandatory": True, "notes": ""},
            {"name": "Confirmation of Enrolment (CoE)", "mandatory": True, "notes": "From CRICOS-registered provider"},
            {"name": "Genuine Student Statement", "mandatory": True, "notes": "Personalised, not template"},
            {"name": "English test results", "mandatory": True, "notes": "Meeting course requirement"},
            {"name": "Financial evidence (bank statements / loan / FD)", "mandatory": True, "notes": "AUD 29,710/year living + tuition + travel"},
            {"name": "OSHC certificate", "mandatory": True, "notes": "Active before visa grant"},
            {"name": "Academic transcripts (10th, 12th, Bachelor's if any)", "mandatory": True, "notes": ""},
            {"name": "Degree certificates", "mandatory": True, "notes": "Notarised if from non-English institution"},
            {"name": "Statement of Purpose (SOP)", "mandatory": True, "notes": "Often same as GS Statement"},
            {"name": "CV / Resume", "mandatory": True, "notes": ""},
            {"name": "Tuition payment receipt (at least 1 semester)", "mandatory": True, "notes": ""},
            {"name": "Health exam (HAP ID)", "mandatory": True, "notes": ""},
            {"name": "PCC (India)", "mandatory": True, "notes": "For applicants 16+"},
            {"name": "Sponsor's tax returns / Form 16 (if parent funding)", "mandatory": True, "notes": "Last 2-3 years"},
            {"name": "Property valuation report (if liquidating assets for funds)", "mandatory": False, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Genuine Student requirement not met — generic statement, no link to course/career",
            "Insufficient financial capacity (funds not in correct name, or unclear source)",
            "Course choice doesn't align with academic background or career goals",
            "English score below requirement",
            "Applicant has visa cancellation history in any country",
            "Sponsor/funding source unclear (parent's income not documented)",
            "CoE from low-reputation provider in city with many visa refusals",
            "Gaps in academic history not explained",
        ],
        "success_tips": [
            "Apply to Group of 8 or top public universities for higher visa approval rate",
            "Write GS Statement that connects course → career goal → return-to-India intent",
            "Show clear funding source: parent's income + tax returns + bank statements + (optional) loan",
            "Pay at least 1 semester tuition before lodgement — demonstrates seriousness",
            "Choose courses aligned with previous education (CS → Master of IT, not random switch)",
            "Apply 6+ weeks before course start to allow processing buffer",
            "Plan arrival 1-2 weeks before course start — orientation, accommodation, banking",
            "Avoid course-hopping after arrival — multiple changes flag your file",
        ],
        "faqs": [
            {"q": "Can I work while studying?", "a": "Yes — 48 hours per fortnight during course terms, unlimited hours during scheduled breaks. Effective Jul 2023."},
            {"q": "Can I bring my spouse and children?", "a": "Yes — partner and dependent children can be included. Partner can work 48 hrs/fortnight; if you're on Master's by research or PhD, partner has UNLIMITED work rights."},
            {"q": "What about post-study work?", "a": "After graduation, eligible for Subclass 485 Temporary Graduate visa (Post-Study Work stream): 2-3 years for Bachelor's, 3 years for Master's, 4 years for PhD. Plus regional bonus 1-2 extra years."},
            {"q": "How much money do I need to show?", "a": "AUD 29,710/year living costs (effective May 2024) + tuition + travel. So Bachelor's of 3 years would need ~AUD 89,130 living + tuition + travel."},
            {"q": "Can I switch courses mid-way?", "a": "Yes, but multiple changes may flag your file. Major changes (e.g. Bachelor's → unrelated Master's) may require new visa application."},
            {"q": "What's the success rate for Indian students?", "a": "Indian applicants are Assessment Level 1 (lowest scrutiny) — approval rate is high (>90%) for genuine applicants with complete documentation. Refusals are usually for GS/financial issues."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500/genuine-student-requirement",
            "https://cricos.education.gov.au/",
            "https://www.privatehealth.gov.au/health_insurance/overseas/oshc.htm",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immi.homeaffairs.gov.au on 2026-02-26. Genuine Student requirement (post-2024 update) + financial threshold AUD 29,710 (May 2024 update).",
    },

    # ── 6. Subclass 820 — Partner Visa (Onshore Temporary) ──────────────────────
    {
        "country_code": "AU",
        "country_name": "Australia",
        "subclass_id": "820",
        "subclass_name": "Partner Visa Onshore (Subclass 820/801)",
        "service_type": "partner",
        "category": "immigration",
        "description": (
            "The Subclass 820/801 Partner visa allows the de facto partner or spouse of an Australian citizen, "
            "PR, or eligible NZ citizen to live in Australia. It is a 2-stage application: first the temporary "
            "Subclass 820 (granted typically 12-24 months after lodgement), then the permanent Subclass 801 "
            "(granted typically 2 years after lodging the combined application).\n\n"
            "Applicants apply onshore — Subclass 309/100 is the offshore equivalent. Combined application fee is "
            "paid once at lodgement (AUD 9,365 in FY2025-26). De facto relationships require minimum 12 months "
            "of cohabitation evidence (waived for those in registered relationships)."
        ),
        "eligibility_summary": (
            "Sponsor is an Australian citizen/PR/eligible NZ citizen aged 18+. Applicant is the spouse or de facto "
            "partner. Relationship is genuine and continuing, with shared financial, social, household, and emotional "
            "commitment. Applicant must be onshore at time of application."
        ),
        "eligibility_criteria": [
            {"label": "Sponsor", "value": "Australian citizen / PR / eligible NZ citizen", "notes": "Aged 18+; limit of 2 sponsorships in lifetime, 5-year gap"},
            {"label": "Relationship type", "value": "Married OR de facto OR registered relationship", "notes": "De facto needs 12 months cohabitation OR registered in AU state/territory"},
            {"label": "Genuine and continuing relationship", "value": "Mutual commitment to shared life", "notes": "Heavy evidence requirement — financial, household, social, written/communication"},
            {"label": "Onshore", "value": "Must be in Australia at time of lodgement and grant of 820", "notes": "Bridging visa A granted upon lodgement (work rights included)"},
            {"label": "Sponsor obligations", "value": "Financial responsibility for 2 years", "notes": "Including Assurance of Support if requested"},
            {"label": "Health + Character", "value": "Standard requirements", "notes": "Plus disclosure of all relationship history"},
        ],
        "fees_local_currency_code": "AUD",
        "fees_local_currency_amount": 9365,
        "fees_inr_approx": 515075,
        "fees_breakdown": [
            {"component": "Combined Visa Application Charge (820+801) — Primary", "amount": 9365, "currency": "AUD"},
            {"component": "Secondary applicant 18+ (additional)", "amount": 4685, "currency": "AUD"},
            {"component": "Dependent child <18 (additional)", "amount": 2345, "currency": "AUD"},
            {"component": "Health exam", "amount": 6000, "currency": "INR"},
            {"component": "PCC", "amount": 500, "currency": "INR"},
            {"component": "AOS bond (if required — refundable)", "amount": 10000, "currency": "AUD"},
            {"component": "Migration agent fees (optional but common)", "amount": 3000, "currency": "AUD"},
        ],
        "processing_time_days_min": 365,
        "processing_time_days_max": 1095,
        "step_by_step": [
            {"step_number": 1, "title": "Establish Relationship Evidence", "description": "Compile evidence across 4 pillars: financial (joint bills, bank accounts), household (shared lease/property), social (joint photos, statements from friends/family), commitment (written communication, future plans).", "estimated_days": 30, "documents_needed": ["Joint bank statements", "Shared utility bills", "Joint lease / property documents", "Photos together (chronological)", "Statutory declarations from 4+ friends/family"], "tips": ["Don't wait — start collecting evidence the moment relationship starts", "More evidence = stronger application"]},
            {"step_number": 2, "title": "Sponsor Lodges Sponsorship Application", "description": "Sponsor completes Form 40SP (sponsorship for partner visa) and supporting documents.", "estimated_days": 7, "documents_needed": ["Sponsor's passport", "Sponsor's Australian citizenship/PR evidence", "Sponsor's police check"], "tips": ["Sponsorship application is electronic via ImmiAccount", "Sponsor must declare any prior partner sponsorships"]},
            {"step_number": 3, "title": "Applicant Lodges Visa Application (820+801 combined)", "description": "Submit Form 47SP + evidence. Visa fee paid at this stage covers both stages.", "estimated_days": 14, "documents_needed": ["Form 47SP", "All relationship evidence", "Passport", "Birth certificate", "Photos", "Police clearances", "Health exam"], "tips": ["Apply onshore — bridging visa A granted same day with work rights", "Comprehensive evidence at lodgement reduces RFI"]},
            {"step_number": 4, "title": "Bridging Visa A in Effect", "description": "Once lodged onshore, you're on Bridging Visa A with same conditions as previous visa + work + Medicare access (after registration).", "estimated_days": 1, "documents_needed": [], "tips": ["Apply for Medicare after Bridging Visa A grant", "Bridging Visa A continues until 820 decision"]},
            {"step_number": 5, "title": "Health + Character Checks", "description": "BUPA medical, India PCC, plus PCCs from every country lived 12+ months.", "estimated_days": 30, "documents_needed": ["HAP ID", "Passport"], "tips": []},
            {"step_number": 6, "title": "Wait for Subclass 820 Decision", "description": "Case officer reviews relationship genuineness, requests more info if needed. May request interview (rare).", "estimated_days": 540, "documents_needed": ["Updated relationship evidence (during wait)"], "tips": ["Respond to RFI within 28 days", "Continue building evidence — update file periodically"]},
            {"step_number": 7, "title": "Subclass 820 Grant", "description": "Temporary residency granted. Full work rights. Medicare access continues.", "estimated_days": 1, "documents_needed": [], "tips": ["820 is temporary — must still maintain relationship + apply for 801"]},
            {"step_number": 8, "title": "Apply for Subclass 801 (Permanent)", "description": "Approximately 2 years after lodging combined application, eligible for 801 PR. Update relationship evidence + submit additional Form 47SP/40SP supplements.", "estimated_days": 30, "documents_needed": ["Updated 2-year evidence of continuing relationship", "Form 47SP supplements"], "tips": ["No additional visa fee for 801 — already paid at 820 lodgement", "Continue documenting relationship throughout"]},
            {"step_number": 9, "title": "Subclass 801 Decision + Grant", "description": "Once approved, permanent residency granted. Pathway to citizenship after 4 years on Australian soil.", "estimated_days": 540, "documents_needed": [], "tips": ["801 PR is permanent — no further visa applications needed"]},
        ],
        "document_checklist": [
            {"name": "Passport (applicant + sponsor)", "mandatory": True, "notes": ""},
            {"name": "Sponsor's Australian citizenship/PR evidence", "mandatory": True, "notes": ""},
            {"name": "Birth certificates (both)", "mandatory": True, "notes": "Notarised"},
            {"name": "Marriage certificate", "mandatory": False, "notes": "If married — Indian registration acceptable"},
            {"name": "Statutory declarations from sponsor + applicant", "mandatory": True, "notes": "Form 888 + Form 40SP/47SP statements"},
            {"name": "Statutory declarations from family/friends (4+ recommended)", "mandatory": True, "notes": "Affirming genuine relationship"},
            {"name": "Joint financial evidence", "mandatory": True, "notes": "Bank statements, joint accounts, shared bills"},
            {"name": "Joint household evidence", "mandatory": True, "notes": "Lease, mortgage, utility bills with both names"},
            {"name": "Joint social evidence", "mandatory": True, "notes": "Photos (chronological), event tickets, travel together"},
            {"name": "Communication evidence", "mandatory": True, "notes": "Selected WhatsApp/text/email logs (not all — chronological samples)"},
            {"name": "Police clearances (each adult, each country 12+ months)", "mandatory": True, "notes": ""},
            {"name": "Health exam (HAP ID)", "mandatory": True, "notes": ""},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "Form 47SP + 40SP", "mandatory": True, "notes": "Applicant + sponsor forms"},
            {"name": "Form 888 (witness statements)", "mandatory": True, "notes": "Recommended minimum 2; better 4+"},
            {"name": "Photos", "mandatory": True, "notes": "Recent passport-size for applicant"},
        ],
        "common_rejection_reasons": [
            "Insufficient relationship evidence — gaps in chronology, no joint financial evidence",
            "Inconsistencies between applicant and sponsor statements",
            "Sponsor has recent prior partner sponsorship (within 5 years)",
            "Health or character issue (undisclosed criminal history)",
            "Applicant offshore at lodgement (must apply offshore Subclass 309/100 instead)",
            "Relationship evidence shows clear gaps or recent commencement",
            "Family/friend statutory declarations are generic templates",
        ],
        "success_tips": [
            "Build evidence from day 1 of relationship — joint accounts, shared lease, photos with dates",
            "Get 4+ DETAILED Form 888 witness statements — not generic, with specific stories",
            "Statutory declarations should be personalised — when did witness meet you both, observations of relationship",
            "Don't include EVERY photo/text — curate strong chronological samples",
            "Maintain Medicare + employment + tax records during wait — proves residence + stability",
            "Continue building evidence during 820→801 waiting period — relationship must be ongoing",
            "Use migration agent for complex situations (prior failed visas, character issues)",
            "Be honest about prior relationships, kids from previous partners — disclosure is key",
        ],
        "faqs": [
            {"q": "What's the difference between 820 and 309?", "a": "820 is onshore (you're in Australia at time of application). 309 is offshore (you're outside Australia). Both lead to PR (801 onshore, 100 offshore). Same fee."},
            {"q": "Do I need to be married?", "a": "No — de facto relationships qualify with 12 months of cohabitation, OR registered relationship (in AU state/territory) with no cohabitation minimum, OR married. Genuineness is more important than legal status."},
            {"q": "Can I work while waiting for 820?", "a": "Yes — Bridging Visa A grants full work rights from the day of application. You can also access Medicare."},
            {"q": "What if my relationship breaks down before 801?", "a": "Specific provisions exist: domestic violence (DV) provisions, child welfare provisions, or death of sponsor. Must inform DoHA within 28 days of separation."},
            {"q": "Can my children come too?", "a": "Yes — dependent children (under 23, or older with disability) can be included. Each pays additional fee."},
            {"q": "How long does the whole process take?", "a": "Total: typically 2-3 years from lodgement to 801 PR grant. Most of this is the mandatory 2-year wait between 820 grant and 801 eligibility."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-onshore-820-801",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-onshore-820-801",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-offshore-309-100",
            "https://immi.homeaffairs.gov.au/help-support/meeting-our-requirements/partner-visas/about-partner-visas",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immi.homeaffairs.gov.au on 2026-02-26. Combined VAC fee per FY2025-26 schedule.",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# CANADA (CA) — 6 verified subclasses
# Source: ircc.canada.ca · Feb 2026 fee schedule · FX: 1 CAD ≈ 60 INR
# ──────────────────────────────────────────────────────────────────────────────
CANADA_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. Express Entry: Federal Skilled Worker (FSW) ─────────────────────────
    {
        "country_code": "CA",
        "country_name": "Canada",
        "subclass_id": "EE-FSW",
        "subclass_name": "Express Entry — Federal Skilled Worker (FSW)",
        "service_type": "pr",
        "category": "immigration",
        "description": (
            "The Federal Skilled Worker (FSW) program is one of three economic streams within Canada's "
            "Express Entry system (alongside CEC and FSTP). It targets skilled workers with foreign work "
            "experience who want to immigrate as Canadian permanent residents. Candidates submit an Expression "
            "of Interest profile to the Express Entry pool, where they are ranked against all other candidates "
            "using the Comprehensive Ranking System (CRS) — a points-based assessment of age, education, "
            "language, work experience, adaptability, and arranged employment.\n\n"
            "IRCC conducts regular draws (general, program-specific, and category-based) where the highest-"
            "ranked candidates above the CRS cutoff receive an Invitation to Apply (ITA). Once invited, "
            "applicants have 60 days to submit a complete electronic Application for Permanent Residence "
            "(e-APR). Processing standard service is 6 months from complete application. Successful applicants "
            "receive Confirmation of Permanent Residence (COPR) and become PRs upon landing in Canada."
        ),
        "eligibility_summary": (
            "Minimum 1 year continuous full-time skilled work experience (NOC TEER 0/1/2/3) in past 10 years, "
            "Canadian Language Benchmark (CLB) 7 in all four English or French skills, education equivalent to "
            "Canadian secondary school (verified via ECA), minimum 67/100 on FSW eligibility grid, and proof "
            "of settlement funds (~CAD 14,690 for 1 person)."
        ),
        "eligibility_criteria": [
            {"label": "Work experience", "value": "≥1 year continuous full-time (or equivalent part-time) skilled work in past 10 years", "notes": "NOC TEER 0, 1, 2, or 3 only; paid work; in same NOC for the year"},
            {"label": "Language", "value": "CLB 7 (minimum) in English OR French — listening/reading/writing/speaking", "notes": "IELTS General Training 6.0 each band, or CELPIP 7 each, or TEF/TCF for French"},
            {"label": "Education", "value": "Canadian secondary school OR equivalent (with ECA from designated org)", "notes": "ECA providers: WES, ICAS, IQAS, ICES, CES (uOttawa), MCC (medical), PEBC (pharmacy)"},
            {"label": "FSW Selection grid", "value": "≥67 out of 100 points (separate from CRS)", "notes": "Age, education, language, experience, arranged employment, adaptability"},
            {"label": "CRS score", "value": "Competitive cutoff varies by draw (485-500+ for general, lower for category-based)", "notes": "Express Entry pool ranking — top scorers invited"},
            {"label": "Settlement funds", "value": "CAD 14,690 (1 person), scaling up to CAD 38,875 (7+ family)", "notes": "Updated annually; not required if you have a valid job offer + Canadian work permit"},
            {"label": "Admissibility", "value": "Pass medical and criminal background checks", "notes": "Includes medical exam by IRCC panel physician + PCC from every country lived in 6+ months since 18"},
        ],
        "fees_local_currency_code": "CAD",
        "fees_local_currency_amount": 1525,
        "fees_inr_approx": 91500,
        "fees_breakdown": [
            {"component": "Permanent Residence application fee — Principal applicant", "amount": 950, "currency": "CAD"},
            {"component": "Right of Permanent Residence Fee (RPRF) — Principal applicant", "amount": 575, "currency": "CAD"},
            {"component": "PR fee — Spouse/Partner", "amount": 950, "currency": "CAD"},
            {"component": "RPRF — Spouse/Partner", "amount": 575, "currency": "CAD"},
            {"component": "PR fee — Dependent child (each)", "amount": 260, "currency": "CAD"},
            {"component": "Biometrics — individual", "amount": 85, "currency": "CAD"},
            {"component": "Biometrics — family (2+ members)", "amount": 170, "currency": "CAD"},
            {"component": "Educational Credential Assessment (WES/ICAS/IQAS)", "amount": 250, "currency": "CAD"},
            {"component": "IELTS General Training (India)", "amount": 16800, "currency": "INR"},
            {"component": "Medical exam (IRCC panel physician in India)", "amount": 7500, "currency": "INR"},
            {"component": "Police Clearance Certificate (India PSK)", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 150,
        "processing_time_days_max": 240,
        "step_by_step": [
            {"step_number": 1, "title": "Educational Credential Assessment (ECA)", "description": "Apply to a designated ECA organisation (WES is most common for India) to verify your foreign degree is equivalent to a Canadian credential. ECA report is valid 5 years.", "estimated_days": 35, "documents_needed": ["Degree certificates (notarised)", "Final transcripts (sealed by university)", "Marks memos", "Identity proof (passport)"], "tips": ["WES gives degree-by-degree equivalency", "Order sealed transcript directly from university — must be unopened", "ECA usually takes 20-35 days; rush options exist"]},
            {"step_number": 2, "title": "Language Testing (IELTS-G / CELPIP / TEF)", "description": "Take an approved English (or French) test. Minimum CLB 7 needed; higher = more CRS points.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["IELTS General Training (NOT Academic) for immigration", "Aim CLB 9+ for substantially higher CRS points", "Test result valid 2 years"]},
            {"step_number": 3, "title": "Submit Express Entry Profile", "description": "Create a profile online at canada.ca/IRCC. Enter education, work history, language scores, family details. System calculates CRS score and places you in the pool.", "estimated_days": 1, "documents_needed": ["ECA report number", "Language test report", "NOC code for primary occupation", "Job reference letters (digital)"], "tips": ["Profile valid 12 months in pool", "Update profile if anything changes (new test score, work anniversary, marriage)", "CRS calculator on IRCC website helps estimate"]},
            {"step_number": 4, "title": "Receive Invitation to Apply (ITA)", "description": "If your CRS score meets/exceeds the draw cutoff, you receive an ITA in your account. You have 60 days from ITA to submit complete e-APR.", "estimated_days": 60, "documents_needed": [], "tips": ["Watch IRCC draw history — draws happen every 1-2 weeks", "Category-based draws (healthcare, STEM, French speakers, trades, transport, agriculture) have lower cutoffs", "Start gathering documents BEFORE ITA"]},
            {"step_number": 5, "title": "Submit Electronic Application for Permanent Residence (e-APR)", "description": "Upload all documents, complete forms (IMM 0008, Schedule A, additional family info), pay fees within 60 days of ITA.", "estimated_days": 14, "documents_needed": ["Passport", "Birth certificates", "Marriage certificate (if applicable)", "Children's birth certs (if applicable)", "Police clearances (all countries 6+ months since 18)", "Proof of work experience (reference letters, payslips, T4s/Form 16s)", "ECA report", "Language test results", "Proof of settlement funds (6 months bank statements)", "Photos", "Digital signed forms"], "tips": ["Upload documents in correct categories", "Use IRCC document checklist — it's the source of truth", "Form must match info in profile exactly"]},
            {"step_number": 6, "title": "Biometrics + Medical + PCC", "description": "Submit biometrics at VFS Canada within 30 days of biometric instruction letter. Medical exam at panel physician. PCC from each country.", "estimated_days": 21, "documents_needed": ["Biometric letter (BIL)", "Medical exam form (eMedical link)", "PCC application docs"], "tips": ["BIL valid 30 days — book early", "Medical valid 12 months", "Indian PCC must be apostilled if applying via mail"]},
            {"step_number": 7, "title": "Decision and COPR", "description": "IRCC reviews. May request additional documents (ADR). On approval, receive Confirmation of Permanent Residence (COPR) + PR Visa stamped in passport (visa-required nationals).", "estimated_days": 120, "documents_needed": [], "tips": ["Respond to ADR within deadline", "COPR has expiry — must land in Canada before"]},
            {"step_number": 8, "title": "Landing in Canada", "description": "Travel to Canada within COPR validity. CBSA officer at port of entry validates documents and grants PR status. Receive PR Card by mail within 60 days.", "estimated_days": 30, "documents_needed": ["Passport with PR Visa", "COPR (printed)", "Goods Accompanying / Goods To Follow lists", "Proof of funds"], "tips": ["Land before COPR expiry", "Bring goods-to-follow inventory if shipping later", "Apply for SIN, health card, driver's license post-landing"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (all family members)", "mandatory": True, "notes": "Min 6 months validity at time of e-APR"},
            {"name": "Birth certificates (all applicants)", "mandatory": True, "notes": "Notarised English translation if not in English"},
            {"name": "Marriage certificate (if applicable)", "mandatory": True, "notes": "Including common-law evidence if applicable"},
            {"name": "Children's birth certificates (if dependents)", "mandatory": True, "notes": "Establishing parent-child relationship"},
            {"name": "Educational Credential Assessment (ECA) report", "mandatory": True, "notes": "From IRCC-designated organisation"},
            {"name": "Degree certificates + transcripts (sealed)", "mandatory": True, "notes": "Submitted to ECA org"},
            {"name": "Language test results (IELTS-G / CELPIP / TEF / TCF)", "mandatory": True, "notes": "Valid 2 years; must be approved test type"},
            {"name": "Work experience reference letters (on company letterhead)", "mandatory": True, "notes": "Must include: position, duties, dates, hours/week, salary, supervisor signature, company contact"},
            {"name": "Payslips / Tax documents (T4s, Form 16, ITR)", "mandatory": True, "notes": "Supporting work experience claim"},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": "From every country lived 6+ months since age 18"},
            {"name": "Medical exam results (IRCC eMedical)", "mandatory": True, "notes": "Panel physician only"},
            {"name": "Biometrics (fingerprints + photo)", "mandatory": True, "notes": "VFS Canada in India"},
            {"name": "Proof of settlement funds (6-month bank statements)", "mandatory": True, "notes": "CAD 14,690+ depending on family size"},
            {"name": "Digital photos (passport-style)", "mandatory": True, "notes": "Per IRCC specifications"},
            {"name": "Personal History (Schedule A)", "mandatory": True, "notes": "Last 10 years address + employment + education timeline"},
            {"name": "Additional Family Info (IMM 5406)", "mandatory": True, "notes": "All family members listed even if not migrating"},
        ],
        "common_rejection_reasons": [
            "Insufficient or inconsistent work experience evidence (vague reference letters, missing duties)",
            "NOC mismatch — claimed occupation doesn't match actual duties performed",
            "Below minimum language threshold (CLB 7) on any one of the four skills",
            "Insufficient settlement funds (must be liquid + accessible, not gifts or borrowed)",
            "Misrepresentation — undisclosed prior visa refusals, criminal record, or family members",
            "Educational equivalency below Canadian secondary school",
            "Document not submitted within 60-day ITA window",
            "Medical inadmissibility — undiagnosed condition that would cause excessive demand on Canadian healthcare",
        ],
        "success_tips": [
            "Maximise CRS through second official language (French = +50 points)",
            "Get Canadian job offer with LMIA = +50 or +200 CRS points (worth chasing)",
            "Spouse education + language = up to 40 additional CRS points",
            "Consider Provincial Nominee Program if CRS too low for federal draws — adds +600 CRS",
            "Use NOC TEER 0/1/2/3 reference letters with EXACTLY matching duties to NOC profile",
            "Build 6 months bank statements showing stable funds — sudden deposits raise red flags",
            "Apply for ECA + language test 4-6 months before profile submission",
            "Watch for category-based draws — healthcare, STEM, French speakers have much lower cutoffs",
        ],
        "faqs": [
            {"q": "What is the minimum CRS score?", "a": "There's no fixed minimum — it varies per draw. General draws in 2025-26 have cutoffs of 485-500+. Category-based draws can be as low as 379 (French speakers). Check IRCC draw history."},
            {"q": "Do I need a Canadian job offer?", "a": "No — FSW is for foreign workers without Canadian experience. Job offer + LMIA gives bonus CRS points (50-200) but is NOT mandatory."},
            {"q": "How long does FSW take?", "a": "IRCC standard service: 6 months from complete application receipt. But ITA wait in pool can range from days (high CRS) to never (low CRS, profile expires at 12 months)."},
            {"q": "Can I include my family?", "a": "Yes — spouse/common-law partner and dependent children under 22 can be on same application. Each pays separate fees."},
            {"q": "What's the difference between FSW, CEC, and FSTP?", "a": "FSW = foreign skilled workers (no Canadian experience needed). CEC = Canadian Experience Class (need 1+ year Canadian work in NOC 0/1/2/3). FSTP = Federal Skilled Trades (for trades NOC 72/73/82/83 + job offer or certification)."},
            {"q": "Is FSW closed sometimes?", "a": "FSW general draws were paused in 2020-22 during COVID. As of 2025-26, regular FSW general draws are happening. Category-based draws also include FSW eligible candidates."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/federal-skilled-workers.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/federal-skilled-workers.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/criteria-comprehensive-ranking-system.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/submit-profile/express-entry-rounds-invitations.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/permanent-residence/economic-classes/federal-skilled-workers.html",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against ircc.canada.ca on 2026-02-27. Fees per IRCC current schedule. Settlement funds per latest annual update.",
    },

    # ── 2. Express Entry: Canadian Experience Class (CEC) ──────────────────────
    {
        "country_code": "CA",
        "country_name": "Canada",
        "subclass_id": "EE-CEC",
        "subclass_name": "Express Entry — Canadian Experience Class (CEC)",
        "service_type": "pr",
        "category": "immigration",
        "description": (
            "The Canadian Experience Class (CEC) is designed for skilled workers who have ALREADY worked in "
            "Canada legally and want to become permanent residents. It is the most-used Express Entry stream "
            "for international students who completed Canadian education + obtained Canadian work experience "
            "via a Post-Graduation Work Permit (PGWP), and for temporary foreign workers transitioning from "
            "work permits to PR.\n\n"
            "Compared to FSW, CEC has lower language requirements (CLB 7 for NOC 0/1, CLB 5 for NOC 2/3), "
            "no settlement funds requirement (since you're already in Canada with employment), and faster "
            "average processing. CEC draws historically have lower CRS cutoffs than general draws — making it "
            "the fastest realistic path to PR for those already in Canada."
        ),
        "eligibility_summary": (
            "Minimum 1 year (1,560 hours) skilled work experience in Canada in past 3 years on a valid work "
            "permit. Language: CLB 7 (NOC TEER 0/1) or CLB 5 (NOC TEER 2/3). Must intend to live outside "
            "Quebec. No settlement funds required if currently working in Canada."
        ),
        "eligibility_criteria": [
            {"label": "Canadian work experience", "value": "≥1 year (1,560 hrs full-time or equivalent part-time) in past 3 years", "notes": "On a valid work permit; self-employment, student work, or co-op do NOT count"},
            {"label": "NOC code", "value": "TEER 0, 1, 2, or 3", "notes": "Same NOC for the full year of experience"},
            {"label": "Language", "value": "CLB 7 (NOC TEER 0/1) or CLB 5 (NOC TEER 2/3)", "notes": "All 4 skills must meet the minimum"},
            {"label": "Residence intent", "value": "Must intend to reside outside Quebec", "notes": "Quebec has its own program (PEQ)"},
            {"label": "Status in Canada", "value": "Can apply from inside or outside Canada, but the Canadian work must be on valid permit", "notes": "Off-status work does NOT count"},
            {"label": "Admissibility", "value": "Pass medical + criminal background checks", "notes": "Standard requirements"},
        ],
        "fees_local_currency_code": "CAD",
        "fees_local_currency_amount": 1525,
        "fees_inr_approx": 91500,
        "fees_breakdown": [
            {"component": "PR application fee — Principal applicant", "amount": 950, "currency": "CAD"},
            {"component": "Right of Permanent Residence Fee (RPRF)", "amount": 575, "currency": "CAD"},
            {"component": "PR fee — Spouse/Partner", "amount": 950, "currency": "CAD"},
            {"component": "RPRF — Spouse/Partner", "amount": 575, "currency": "CAD"},
            {"component": "PR fee — Dependent child (each)", "amount": 260, "currency": "CAD"},
            {"component": "Biometrics — individual", "amount": 85, "currency": "CAD"},
            {"component": "Biometrics — family (2+)", "amount": 170, "currency": "CAD"},
            {"component": "Language test (IELTS-G in India OR CELPIP in Canada)", "amount": 16800, "currency": "INR"},
            {"component": "Medical exam (IRCC panel physician)", "amount": 7500, "currency": "INR"},
            {"component": "PCCs (India + other countries lived in 6+ mo since 18)", "amount": 1000, "currency": "INR"},
        ],
        "processing_time_days_min": 120,
        "processing_time_days_max": 210,
        "step_by_step": [
            {"step_number": 1, "title": "Accumulate Canadian Work Experience", "description": "Work full-time (≥30 hrs/week) in Canada on a valid work permit (typically PGWP for ex-students, or LMIA-based work permit) for 12 months in NOC TEER 0/1/2/3.", "estimated_days": 365, "documents_needed": ["Work permit (valid)", "T4 slips", "Pay statements"], "tips": ["Track exact hours weekly", "Get reference letter on company letterhead with full role details", "Stay in same NOC throughout"]},
            {"step_number": 2, "title": "Language Test", "description": "Take CELPIP General or IELTS General Training in Canada (or India before relocation).", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["CELPIP is Canadian-designed, may be easier than IELTS for some", "Aim CLB 9+ for max points"]},
            {"step_number": 3, "title": "Submit Express Entry Profile", "description": "Create EE profile. CRS calculated based on Canadian work + age + language + education.", "estimated_days": 1, "documents_needed": ["Language test result", "NOC for Canadian job", "Work permit details"], "tips": ["Profile valid 12 months", "Update if anything changes (new job, anniversary)"]},
            {"step_number": 4, "title": "Receive ITA in CEC Draw", "description": "CEC-specific draws or general draws can issue your ITA. CEC draw cutoffs are typically lower than FSW general.", "estimated_days": 30, "documents_needed": [], "tips": ["CEC draws happen frequently", "Watch IRCC for CEC-specific announcements"]},
            {"step_number": 5, "title": "Submit e-APR", "description": "Upload all docs within 60 days of ITA. CEC-specific: emphasis on Canadian work proof.", "estimated_days": 14, "documents_needed": ["Canadian work reference letter", "T4 slips", "Pay statements", "Work permits (all versions)", "Same as FSW for other docs"], "tips": ["Reference letter MUST contain hours/week, duties matching NOC, dates, salary, supervisor signature", "T4s are mandatory — proves real employment"]},
            {"step_number": 6, "title": "Biometrics + Medical + PCC", "description": "Standard process.", "estimated_days": 21, "documents_needed": ["BIL", "Medical referral"], "tips": ["Faster in Canada than India"]},
            {"step_number": 7, "title": "Decision + COPR", "description": "Standard processing.", "estimated_days": 120, "documents_needed": [], "tips": ["May need to do 'soft landing' if outside Canada"]},
            {"step_number": 8, "title": "Activate PR Status", "description": "If in Canada, status activates upon receipt of COPR. If outside, land at port of entry.", "estimated_days": 30, "documents_needed": ["COPR"], "tips": ["Apply for PR card and update SIN immediately"]},
        ],
        "document_checklist": [
            {"name": "Passport (valid, all family members)", "mandatory": True, "notes": ""},
            {"name": "All Canadian work permits (current + past)", "mandatory": True, "notes": "Critical for CEC"},
            {"name": "Canadian work reference letter", "mandatory": True, "notes": "Detailed: hours, duties matching NOC, supervisor signature"},
            {"name": "T4 slips (each tax year)", "mandatory": True, "notes": "Proves actual Canadian employment"},
            {"name": "Pay statements (last 6 months)", "mandatory": True, "notes": ""},
            {"name": "ECA report (if education claimed for CRS points)", "mandatory": False, "notes": "Not mandatory but boosts CRS"},
            {"name": "Language test results (CELPIP/IELTS-G/TEF)", "mandatory": True, "notes": "CLB 7 (NOC 0/1) or CLB 5 (NOC 2/3)"},
            {"name": "PCCs (every country lived 6+ months since 18)", "mandatory": True, "notes": ""},
            {"name": "Medical exam", "mandatory": True, "notes": "IRCC panel physician"},
            {"name": "Biometrics", "mandatory": True, "notes": "Within 30 days of BIL"},
            {"name": "Marriage cert + children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Schedule A — Background Declaration", "mandatory": True, "notes": "10 years address/employment/education"},
            {"name": "IMM 5406 — Additional Family Info", "mandatory": True, "notes": "All family members"},
            {"name": "Digital photos (passport-style)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Self-employment, co-op, or part-time-during-study work claimed (not eligible)",
            "Off-status work — even ONE day off-status invalidates the entire experience period",
            "Language test below CLB 7 (NOC 0/1) or CLB 5 (NOC 2/3) on any skill",
            "Reference letter missing critical fields (hours/duties/supervisor signature)",
            "NOC mismatch — duties don't align with claimed NOC code",
            "Intent to reside in Quebec (CEC requires intent to live outside Quebec)",
            "Misrepresentation of work hours or employer relationship",
        ],
        "success_tips": [
            "Track every work hour from day 1 of work permit — 1,560 hrs over 12 months is the threshold",
            "Get reference letter BEFORE leaving the employer — much harder later",
            "Use exact NOC duty language from Government of Canada NOC website in your reference letter",
            "If on PGWP — apply for PR before PGWP expires; bridging open work permit (BOWP) keeps you working",
            "CLB 9+ in English/French boosts CRS by 30+ points — worth retaking the test",
            "Check CEC-specific draw history — much lower CRS cutoffs than general FSW",
            "Don't switch NOCs mid-year — accumulate 12 months in SAME NOC",
        ],
        "faqs": [
            {"q": "Does PGWP work count for CEC?", "a": "YES — Post-Graduation Work Permit work is the most common path to CEC, as long as it's in NOC TEER 0/1/2/3 and you have at least 1 year accumulated."},
            {"q": "Can I claim part-time work?", "a": "Yes — 1,560 hours over 36 months from multiple part-time jobs counts. Full-time = 30 hrs/week."},
            {"q": "What's a Bridging Open Work Permit (BOWP)?", "a": "If you've submitted your PR e-APR and your current work permit will expire before PR decision, you can apply for BOWP to continue working with any employer until PR decision."},
            {"q": "Can I include spouse with CEC?", "a": "Yes — same as FSW. Spouse's language + education + work experience adds CRS points."},
            {"q": "How is CEC faster than FSW?", "a": "CEC has lower CRS draws (more frequent ITAs), already-verified Canadian work means fewer questions from IRCC, and processing is often faster."},
            {"q": "What if I leave Canada during PR processing?", "a": "You can be outside Canada during processing — but you must enter Canada to activate PR status."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/canadian-experience-class.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/canadian-experience-class.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit/post-graduation-work-permit-program.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit/temporary/bridging-open-work-permit.html",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against ircc.canada.ca on 2026-02-27. CEC fee structure same as other PR streams.",
    },

    # ── 3. Provincial Nominee Program (PNP) ───────────────────────────────────
    {
        "country_code": "CA",
        "country_name": "Canada",
        "subclass_id": "PNP",
        "subclass_name": "Provincial Nominee Program (PNP)",
        "service_type": "pr",
        "category": "immigration",
        "description": (
            "The Provincial Nominee Program (PNP) allows Canadian provinces and territories (except Quebec, "
            "which has PEQ) to nominate foreign nationals for permanent residence based on their specific "
            "labour market needs. Each province operates its own PNP streams with distinct criteria — "
            "Ontario (OINP), British Columbia (BC PNP), Alberta (AAIP), Saskatchewan (SINP), Manitoba (MPNP), "
            "Nova Scotia (NSNP), New Brunswick (NBPNP), PEI (PEI PNP), Newfoundland (NLPNP), and territories "
            "Yukon, NWT, Nunavut.\n\n"
            "PNPs have two pathways: (1) **Enhanced** (Express Entry-aligned) — provincial nomination adds "
            "+600 CRS points, virtually guaranteeing an ITA in the next federal draw; (2) **Base** (paper-based, "
            "non-EE) — direct to province, no CRS requirement but slower (11-21 months). PNP is the most "
            "effective path for candidates with lower CRS scores or those targeting specific provinces with "
            "labour shortages in their occupation."
        ),
        "eligibility_summary": (
            "Varies dramatically by province + stream. Most require: an in-demand occupation, valid job offer "
            "or Canadian work/study experience in the province, language proficiency, education, ties to the "
            "province (intention to live there). Express Entry-aligned streams also require an active Express "
            "Entry profile."
        ),
        "eligibility_criteria": [
            {"label": "Provincial occupation match", "value": "Occupation must be on the province's target list", "notes": "Each province publishes its own occupation list, often demand-driven"},
            {"label": "Job offer (varies by stream)", "value": "Some streams require valid job offer from provincial employer; others don't", "notes": "Employer-driven streams: job offer mandatory. International graduate streams: graduate from provincial institution"},
            {"label": "Language", "value": "CLB 5-7 minimum (varies by stream/NOC)", "notes": "Higher CLB earns more provincial points"},
            {"label": "Education", "value": "Secondary minimum; many streams require post-secondary or ECA", "notes": "Some have specific Canadian education requirements"},
            {"label": "Work experience", "value": "1-3 years in target occupation (varies)", "notes": "Some streams accept any experience; others target-specific"},
            {"label": "Intent to reside in nominating province", "value": "Required across all PNP streams", "notes": "Demonstrate via cover letter, family ties, job offer, prior residence"},
            {"label": "Settlement funds", "value": "Varies by province (CAD 10,000 - 15,000 typical)", "notes": "Not always required if job offer in place"},
            {"label": "Express Entry profile (Enhanced streams only)", "value": "Required for EE-aligned PNP nominations", "notes": "Base streams don't need EE profile"},
        ],
        "fees_local_currency_code": "CAD",
        "fees_local_currency_amount": 1875,
        "fees_inr_approx": 112500,
        "fees_breakdown": [
            {"component": "Provincial Nomination application fee (varies — Ontario CAD 1,500-2,000; BC CAD 1,150; SK CAD 350)", "amount": 350, "currency": "CAD"},
            {"component": "PR application fee — Principal applicant", "amount": 950, "currency": "CAD"},
            {"component": "RPRF — Principal", "amount": 575, "currency": "CAD"},
            {"component": "PR fee — Spouse/Partner", "amount": 950, "currency": "CAD"},
            {"component": "RPRF — Spouse/Partner", "amount": 575, "currency": "CAD"},
            {"component": "PR fee — Dependent child (each)", "amount": 260, "currency": "CAD"},
            {"component": "Biometrics — family", "amount": 170, "currency": "CAD"},
            {"component": "ECA", "amount": 250, "currency": "CAD"},
            {"component": "Language test", "amount": 16800, "currency": "INR"},
            {"component": "Medical exam + PCCs", "amount": 8500, "currency": "INR"},
        ],
        "processing_time_days_min": 210,
        "processing_time_days_max": 540,
        "step_by_step": [
            {"step_number": 1, "title": "Research Provincial Programs", "description": "Each province has multiple PNP streams. Identify which province matches your occupation, work history, language profile, and family situation.", "estimated_days": 30, "documents_needed": [], "tips": ["Check provincial occupation lists regularly — they change", "Some provinces (SK, MB, NB, NL) have lower CRS thresholds", "Tech-occupation streams (Ontario, BC, Alberta) are competitive"]},
            {"step_number": 2, "title": "Decide: Enhanced (EE) or Base (Paper)", "description": "Enhanced is EE-aligned — needs active EE profile; nomination = +600 CRS. Base is paper-based — slower but no EE needed.", "estimated_days": 7, "documents_needed": [], "tips": ["Enhanced = 6-8 months typically", "Base = 11-21 months but no CRS competition"]},
            {"step_number": 3, "title": "Submit EOI to Province (if required)", "description": "Most PNPs use an Expression of Interest system. You create a profile in the province's system, get scored, wait for invitation to apply to PNP.", "estimated_days": 30, "documents_needed": ["Language test", "ECA", "Resume", "Reference letters"], "tips": ["Some streams open/close based on quotas", "Higher provincial score = faster invitation"]},
            {"step_number": 4, "title": "Submit PNP Application", "description": "Once invited by province, submit full application to PNP with all evidence.", "estimated_days": 14, "documents_needed": ["EOI invitation", "Job offer (if applicable)", "Education docs", "Language results", "Work reference letters", "Settlement funds proof", "Intent letter explaining ties to province"], "tips": ["Tailor intent letter to specific province", "Include specific local labour market research"]},
            {"step_number": 5, "title": "Receive Provincial Nomination", "description": "Province reviews and either issues a Nomination Certificate (Enhanced) or sends Nomination Letter (Base).", "estimated_days": 90, "documents_needed": [], "tips": ["Nomination is valid 6 months", "If Enhanced, +600 CRS auto-added to your EE profile"]},
            {"step_number": 6, "title": "(Enhanced only) Receive ITA from IRCC", "description": "With +600 CRS, you'll receive an ITA in the next applicable EE draw.", "estimated_days": 14, "documents_needed": [], "tips": ["Almost certain ITA"]},
            {"step_number": 7, "title": "Submit Federal PR Application (e-APR or paper)", "description": "Enhanced: e-APR via Express Entry within 60 days. Base: paper APR to provincial Centralized Intake Office.", "estimated_days": 14, "documents_needed": ["Same as FSW/CEC: passport, education, language, PCCs, medical, biometrics, work proof, settlement funds"], "tips": ["Enhanced is faster — uses EE infrastructure"]},
            {"step_number": 8, "title": "Decision + COPR + Land in Province", "description": "Federal decision typically 6-12 months. COPR issued. Land at port of entry and settle in nominating province.", "estimated_days": 270, "documents_needed": [], "tips": ["Intent to reside in province is a CONTINUING obligation — don't relocate immediately"]},
        ],
        "document_checklist": [
            {"name": "Passport (all family members)", "mandatory": True, "notes": ""},
            {"name": "Provincial nomination certificate / letter", "mandatory": True, "notes": "The cornerstone document"},
            {"name": "Language test results", "mandatory": True, "notes": "Provincial minimum varies"},
            {"name": "ECA report (most streams)", "mandatory": True, "notes": "If non-Canadian education"},
            {"name": "Job offer letter (employer-driven streams)", "mandatory": False, "notes": "Required for streams like Ontario Employer Job Offer, BC Skilled Worker"},
            {"name": "Work reference letters (all employment)", "mandatory": True, "notes": "On letterhead with full details"},
            {"name": "Settlement funds proof (6 months)", "mandatory": False, "notes": "Required by some provinces; CAD 10,000-15,000 typical"},
            {"name": "Intent to reside letter / Affidavit", "mandatory": True, "notes": "Province-specific — tailored explanation"},
            {"name": "PCCs (every country lived 6+ months since 18)", "mandatory": True, "notes": ""},
            {"name": "Medical exam", "mandatory": True, "notes": "IRCC panel physician"},
            {"name": "Biometrics", "mandatory": True, "notes": ""},
            {"name": "Marriage cert + children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Schedule A + IMM 5406", "mandatory": True, "notes": ""},
            {"name": "Photos", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Insufficient evidence of intent to reside in nominating province",
            "Occupation not on provincial target list at time of application",
            "Job offer not LMIA-supported or not from designated employer (some streams)",
            "Provincial language threshold not met (varies by stream)",
            "Settlement funds insufficient or unstable",
            "Misrepresentation about prior nominations from other provinces (each PNP scrutinizes)",
            "Federal stage: same as other PR streams (PCC issues, medical, misrepresentation)",
        ],
        "success_tips": [
            "Choose province based on demand for YOUR occupation + ease of nomination, not just convenience",
            "If applying to Enhanced stream — keep EE profile updated continuously",
            "Demonstrate concrete provincial ties: family there, prior visit, job market research, savings allocated",
            "Saskatchewan, Manitoba, New Brunswick are historically easier — fewer EE-stream competitors",
            "International graduate streams (Ontario PNP, BC PNP, MPNP) reward graduates of provincial institutions",
            "Apply to ONE province at a time — multiple nominations create issues",
            "Read every line of province's program guide — minor disqualifiers are common",
        ],
        "faqs": [
            {"q": "Which province is the easiest for PNP?", "a": "Depends on occupation. Generally SK, MB, NB, NL have less competition. Ontario + BC are most competitive due to popularity but have very specific occupation streams (tech, healthcare)."},
            {"q": "Enhanced vs Base PNP — which is better?", "a": "Enhanced if your CRS is decent (300+) and your occupation has Enhanced stream open. Base if Enhanced isn't open, or CRS is very low (250-).  Enhanced is faster + uses EE infrastructure."},
            {"q": "Do I need a job offer for PNP?", "a": "Some streams yes (employer-driven), some no (international graduate, in-demand occupation). Read each stream's requirements."},
            {"q": "Can I switch province after PR?", "a": "Legally yes — PR is national. But moral commitment to nominating province matters; some provinces audit residence."},
            {"q": "How long does PNP take overall?", "a": "Enhanced: provincial 2-6 months + federal 6 months = ~12 months total. Base: provincial 6-12 months + federal 11-21 months = up to 33 months."},
            {"q": "What's the +600 CRS bonus?", "a": "When a province nominates you through an Enhanced (EE-aligned) stream, IRCC automatically adds 600 to your CRS score. This essentially guarantees an ITA in the next draw."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/provincial-nominees.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/provincial-nominees.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/provincial-nominees/apply.html",
            "https://www.ontario.ca/page/oinp-application-update-employer-job-offer-streams",
            "https://www.welcomebc.ca/Immigrate-to-B-C/B-C-Provincial-Nominee-Program",
            "https://www.alberta.ca/alberta-advantage-immigration-program.aspx",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/provincial-nominees/eligibility/process.html",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against ircc.canada.ca + multiple provincial sites on 2026-02-27. Provincial fees vary; example shows SK base fee; Ontario reaches up to CAD 1,500-2,000.",
    },

    # ── 4. Study Permit ────────────────────────────────────────────────────────
    {
        "country_code": "CA",
        "country_name": "Canada",
        "subclass_id": "Study-Permit",
        "subclass_name": "Study Permit (Post-Secondary at DLI)",
        "service_type": "student",
        "category": "immigration",
        "description": (
            "The Canada Study Permit allows international students to study at a Designated Learning Institution "
            "(DLI). It's the most popular pathway to long-term Canadian immigration: Indian students pursuing "
            "post-secondary education on a Study Permit can transition to PGWP (work permit) → 1+ years Canadian "
            "work experience → CEC/PNP PR.\n\n"
            "Since 2024 IRCC introduced a Provincial Attestation Letter (PAL) requirement for most undergraduate "
            "Study Permits — provinces vet applications to manage intake caps. Genuine Student factor (replaced "
            "GTE in some contexts) and Statement of Purpose remain critical. Financial proof is rigorous: tuition "
            "+ CAD 20,635/year living costs (effective 2024, up from CAD 10,000) for self; +CAD 4,000 spouse, "
            "+CAD 3,000 each child."
        ),
        "eligibility_summary": (
            "Acceptance letter from a Designated Learning Institution (DLI), Provincial Attestation Letter "
            "(PAL) for most undergraduate programs, proof of financial capacity (tuition + CAD 20,635/year "
            "living for principal), Statement of Purpose, language proficiency, intent to leave Canada at end "
            "of study (or transition to work permit/PR per IRCC's revised framework)."
        ),
        "eligibility_criteria": [
            {"label": "DLI acceptance", "value": "Acceptance letter from a Designated Learning Institution", "notes": "List published at canada.ca/study-permit DLI list"},
            {"label": "Provincial Attestation Letter (PAL)", "value": "Required for most undergraduate and college programs since Jan 2024", "notes": "Exemptions: master's, PhD, primary/secondary school, designated programs"},
            {"label": "Financial capacity", "value": "Tuition + CAD 20,635/year living for principal applicant + CAD 4,000 for first family member + CAD 3,000 each subsequent", "notes": "Effective Jan 2024, up from CAD 10,000/year"},
            {"label": "Language", "value": "Generally not a federal requirement but most DLIs require IELTS Academic 6.0/6.5 or TOEFL", "notes": "Provincial Attestation may add language thresholds"},
            {"label": "Statement of Purpose", "value": "Comprehensive intent letter", "notes": "Replaces simplistic 'why Canada' answer — must justify program choice + career goals"},
            {"label": "Medical exam (if studying healthcare/childcare/agriculture, or from designated countries)", "value": "Required for India applicants going to such programs OR studying >6 months", "notes": "Panel physician only"},
            {"label": "Working rights", "value": "20 hours/week off-campus during studies, full-time during scheduled breaks", "notes": "Effective Nov 2024 — increased from 20 hrs to ongoing assessment"},
        ],
        "fees_local_currency_code": "CAD",
        "fees_local_currency_amount": 235,
        "fees_inr_approx": 14100,
        "fees_breakdown": [
            {"component": "Study Permit application fee", "amount": 150, "currency": "CAD"},
            {"component": "Biometrics — individual", "amount": 85, "currency": "CAD"},
            {"component": "Biometrics — family (2+)", "amount": 170, "currency": "CAD"},
            {"component": "Tuition deposit (varies; Bachelor's avg)", "amount": 20000, "currency": "CAD"},
            {"component": "Living cost proof (1 year + tuition combined)", "amount": 20635, "currency": "CAD"},
            {"component": "GIC (Guaranteed Investment Certificate — SDS stream)", "amount": 20635, "currency": "CAD"},
            {"component": "IELTS Academic test (India)", "amount": 16800, "currency": "INR"},
            {"component": "Medical exam (if required)", "amount": 7500, "currency": "INR"},
            {"component": "PCC (India)", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 21,
        "processing_time_days_max": 90,
        "step_by_step": [
            {"step_number": 1, "title": "Choose DLI + Apply", "description": "Research Designated Learning Institutions. Submit application to chosen program. Pay first-year tuition or deposit on acceptance.", "estimated_days": 60, "documents_needed": ["Transcripts", "Degree certificates", "IELTS Academic / TOEFL", "Statement of Purpose"], "tips": ["Top DLIs: University of Toronto, UBC, McGill, Waterloo, McMaster, Queen's, Western, Alberta", "Public colleges + universities have higher visa success", "Apply 8-10 months before intake"]},
            {"step_number": 2, "title": "Receive Acceptance Letter", "description": "DLI issues an official Letter of Acceptance (LOA).", "estimated_days": 14, "documents_needed": [], "tips": ["LOA must include: program name, duration, tuition, DLI number", "If conditional, fulfill condition (language score, transcripts) before applying"]},
            {"step_number": 3, "title": "Get Provincial Attestation Letter (PAL) — if applicable", "description": "Provincial Attestation Letter required for most undergraduate/college programs since Jan 2024. Applied for through the DLI.", "estimated_days": 21, "documents_needed": ["Acceptance letter"], "tips": ["DLI handles PAL — you don't apply directly", "Some grad programs + designated programs are exempt"]},
            {"step_number": 4, "title": "Arrange Financial Proof", "description": "GIC (CAD 20,635) is common for India via SDS. Or bank statements + sponsor letter + tax returns.", "estimated_days": 14, "documents_needed": ["GIC certificate (Scotiabank/CIBC/ICICI/SBI)", "Tuition payment receipt", "Loan letter (if applicable)", "Sponsor's ITR (last 3 years)"], "tips": ["GIC is faster for processing under SDS (Student Direct Stream)", "SDS available for Indian nationals — IELTS Academic 6.0+ each band + GIC + 1-year tuition paid"]},
            {"step_number": 5, "title": "Take Language Test", "description": "IELTS Academic, TOEFL iBT, or PTE Academic (some DLIs).", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["IELTS 6.0+ each band for SDS"]},
            {"step_number": 6, "title": "Submit Study Permit Application Online", "description": "Apply via canada.ca/IRCC online portal with all docs.", "estimated_days": 7, "documents_needed": ["LOA", "PAL (if applicable)", "Financial proof (GIC + tuition + bank statements)", "Statement of Purpose", "Passport", "Photos", "Language test", "Past academic transcripts"], "tips": ["SDS is faster (20-30 days)", "Regular Study Permit can take 60-90 days"]},
            {"step_number": 7, "title": "Biometrics + Medical (if required)", "description": "Biometrics at VFS Canada in India. Medical if program is healthcare/childcare or duration >6 months from India.", "estimated_days": 21, "documents_needed": ["BIL", "Medical referral"], "tips": ["Book biometrics in 30 days of BIL", "Medical valid 1 year"]},
            {"step_number": 8, "title": "Decision + Port of Entry", "description": "Receive Port of Entry letter. Travel to Canada with all docs, complete final immigration interview at airport — actual Study Permit issued there.", "estimated_days": 60, "documents_needed": ["POE letter", "LOA", "Financial proof", "Passport"], "tips": ["You can enter Canada up to 4 weeks before program start", "Bring originals of all submitted docs to POE"]},
        ],
        "document_checklist": [
            {"name": "Passport (valid, all pages)", "mandatory": True, "notes": "Min 6 months validity"},
            {"name": "Letter of Acceptance from DLI", "mandatory": True, "notes": "Must include DLI number, program, duration, tuition"},
            {"name": "Provincial Attestation Letter (PAL) — if applicable", "mandatory": True, "notes": "DLI handles issuance; required for most undergrad/college"},
            {"name": "Proof of financial support", "mandatory": True, "notes": "GIC + tuition receipt OR bank statements + sponsor docs"},
            {"name": "GIC certificate (Scotiabank/CIBC/ICICI/SBI — for SDS)", "mandatory": False, "notes": "Required if applying via SDS"},
            {"name": "Tuition payment receipt (1st year or full)", "mandatory": True, "notes": ""},
            {"name": "Statement of Purpose (SOP) / Study Plan", "mandatory": True, "notes": "Detailed explanation of program choice + career link"},
            {"name": "Language test results (IELTS Academic/TOEFL/PTE)", "mandatory": True, "notes": "Per program + SDS requirements"},
            {"name": "Academic transcripts (10th, 12th, Bachelor's if applicable)", "mandatory": True, "notes": ""},
            {"name": "Degree certificates (sealed by university)", "mandatory": True, "notes": ""},
            {"name": "Medical exam (if program healthcare/childcare OR India-origin with 6+ month duration)", "mandatory": True, "notes": "Panel physician"},
            {"name": "Biometrics (VFS Canada in India)", "mandatory": True, "notes": "Within 30 days of BIL"},
            {"name": "Police Clearance Certificate (India PSK)", "mandatory": False, "notes": "May be requested"},
            {"name": "Sponsor's tax returns / Form 16 (last 3 years)", "mandatory": False, "notes": "Backs up financial proof"},
            {"name": "Photos (passport-style, IRCC specs)", "mandatory": True, "notes": ""},
            {"name": "Custodian declaration (if minor)", "mandatory": False, "notes": "For students under 18"},
        ],
        "common_rejection_reasons": [
            "Insufficient financial capacity — fund source unclear or sudden deposits",
            "Statement of Purpose generic / doesn't justify program choice for career",
            "Course choice doesn't align with previous education (random switch flagged)",
            "Past visa refusals from Canada, USA, UK, Schengen, Australia not declared",
            "Family ties to Canada with PR/citizen status (immigration intent concern)",
            "Weak ties to home country — IRCC believes you won't return",
            "Misrepresentation in IELTS / academic documents",
            "DLI of low reputation in cities with high refusal rates",
        ],
        "success_tips": [
            "Apply via SDS (Student Direct Stream) if Indian — much faster + higher approval rate",
            "Choose program directly related to your past education + career goals",
            "Write a UNIQUE Statement of Purpose — explain program choice, DLI choice, post-graduation plan",
            "Pay 1 year tuition + show GIC = strong financial proof",
            "Apply 4-6 months before program start date",
            "Choose public DLIs (universities + community colleges) over private institutes",
            "Demonstrate ties to home: family, property, return-after-study plan",
            "Don't apply to multiple unrelated programs — looks like 'visa fishing'",
        ],
        "faqs": [
            {"q": "What is SDS (Student Direct Stream)?", "a": "SDS is a fast-track Study Permit program for Indian nationals (plus 13 other countries). Requirements: GIC CAD 20,635, IELTS Academic 6.0+ each band, full 1-year tuition paid, medical+biometrics done. Processing: 20-30 days."},
            {"q": "Can I work while on Study Permit?", "a": "Yes — 20 hours/week off-campus during study terms; full-time during scheduled breaks (summer, winter). Some on-campus work has no hour limit."},
            {"q": "What's PGWP?", "a": "Post-Graduation Work Permit — issued after graduation from a DLI. Length: 1-3 years based on program length. Enables transition to CEC PR after 1+ year Canadian work."},
            {"q": "Can I bring my spouse?", "a": "Yes — spouse can come on Open Work Permit (full work rights) if you're at master's, PhD, professional program, or some bachelor's. Children can attend Canadian K-12 schools for free."},
            {"q": "What if I'm rejected?", "a": "You can reapply with stronger evidence (more funds, better SOP, different DLI). Or appeal in Federal Court (judicial review). Reapplication is usually faster."},
            {"q": "How much does it cost overall?", "a": "Application fee CAD 150 + biometrics CAD 85 + GIC CAD 20,635 (refunded over year) + tuition CAD 15,000-50,000 (varies by program) + IELTS ₹16,800 + medical ₹7,500 = approximately ₹15-25 lakh for first year all-in."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/student-direct-stream.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/eligibility.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/get-documents.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/news/2024/01/canada-to-stabilize-growth-and-decrease-number-of-new-international-student-permits-issued-to-approximately-360000-for-2024.html",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against ircc.canada.ca on 2026-02-27. Living cost minimum (CAD 20,635) per Jan 2024 update. PAL requirement per Jan 2024 IRCC policy.",
    },

    # ── 5. Open Work Permit ────────────────────────────────────────────────────
    {
        "country_code": "CA",
        "country_name": "Canada",
        "subclass_id": "Work-Permit-Open",
        "subclass_name": "Open Work Permit (PGWP / Spousal / IEC)",
        "service_type": "work",
        "category": "immigration",
        "description": (
            "An Open Work Permit (OWP) is a work permit that is NOT job-specific — it allows the holder to work "
            "for any Canadian employer (except those listed as ineligible). The most common OWP categories for "
            "Indian applicants are:\n\n"
            "1. **Post-Graduation Work Permit (PGWP)** — for graduates of Canadian DLIs (1-3 years validity, "
            "based on program length).\n"
            "2. **Spousal Open Work Permit (SOWP)** — for spouses/common-law partners of Canadian Study Permit "
            "holders (in graduate/professional programs) or skilled work permit holders.\n"
            "3. **International Experience Canada (IEC)** — Working Holiday for citizens of certain countries "
            "(India NOT currently a partner — not applicable).\n"
            "4. **Bridging Open Work Permit (BOWP)** — for those who applied for PR and need to continue working "
            "while waiting for decision.\n\n"
            "OWPs do NOT require an LMIA (Labour Market Impact Assessment) and are issued for varied periods."
        ),
        "eligibility_summary": (
            "Varies by category: PGWP needs DLI graduation + Study Permit history. SOWP needs spouse on eligible "
            "Study/Work Permit. BOWP needs pending PR application + valid current work permit. All OWPs require "
            "valid status in Canada (or be applying from abroad)."
        ),
        "eligibility_criteria": [
            {"label": "Category (PGWP)", "value": "Graduated from a DLI in an eligible program ≥8 months long", "notes": "Must apply within 180 days of getting final transcript; only ONE PGWP per lifetime"},
            {"label": "Category (SOWP)", "value": "Spouse/common-law partner of: (a) Study Permit holder in master's/PhD/professional/certain bachelor's programs, OR (b) Skilled Work Permit holder NOC TEER 0/1", "notes": "Tightened criteria since 2024; not all spouses qualify anymore"},
            {"label": "Category (BOWP)", "value": "PR e-APR submitted + accepted as eligible + current work permit valid", "notes": "Issued automatically when applying for BOWP in CEC stream"},
            {"label": "Status", "value": "If applying from inside Canada — must have valid temporary status", "notes": "Can apply from outside Canada in most cases"},
            {"label": "Admissibility", "value": "Pass medical (if applicable) + criminal checks", "notes": "Medical needed if working in healthcare/childcare/agriculture or from designated countries with 6+ month duration"},
            {"label": "Biometrics", "value": "Mandatory for Indian nationals", "notes": "Valid 10 years"},
        ],
        "fees_local_currency_code": "CAD",
        "fees_local_currency_amount": 340,
        "fees_inr_approx": 20400,
        "fees_breakdown": [
            {"component": "Work Permit application fee", "amount": 155, "currency": "CAD"},
            {"component": "Open Work Permit Holder fee", "amount": 100, "currency": "CAD"},
            {"component": "Biometrics — individual", "amount": 85, "currency": "CAD"},
            {"component": "Biometrics — family", "amount": 170, "currency": "CAD"},
            {"component": "Medical exam (if required)", "amount": 7500, "currency": "INR"},
            {"component": "PCC (if requested)", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 30,
        "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Eligibility for Specific Category", "description": "Determine which OWP category applies: PGWP, SOWP, BOWP. Check current IRCC eligibility (rules tightened in 2024).", "estimated_days": 7, "documents_needed": [], "tips": ["PGWP eligibility narrowed in 2024 — verify your program qualifies", "SOWP for spouses of bachelor's students mostly eliminated except specific programs"]},
            {"step_number": 2, "title": "Gather Category-Specific Documents", "description": "PGWP: final transcript + letter of completion. SOWP: spouse's Study/Work Permit + marriage cert + spouse's enrollment letter. BOWP: PR application acknowledgment.", "estimated_days": 14, "documents_needed": ["Category-specific docs"], "tips": ["PGWP transcript must be FINAL — partial transcripts rejected"]},
            {"step_number": 3, "title": "Complete Application Form", "description": "Form IMM 5710 (in Canada) or IMM 1295 (outside Canada). Open Work Permit checkbox.", "estimated_days": 3, "documents_needed": ["Application form (digitally signed)"], "tips": ["List 'Open Work Permit' specifically — don't tie to one employer"]},
            {"step_number": 4, "title": "Submit Application", "description": "Online via IRCC portal. Pay fees.", "estimated_days": 1, "documents_needed": ["Passport scan", "Photos", "Form IMM 5645 (Family Info)", "Category-specific docs"], "tips": ["Apply 30-60 days before current permit expiry (if in Canada)", "Maintained status applies if applied before expiry"]},
            {"step_number": 5, "title": "Biometrics", "description": "If within 10 years of previous biometrics, may be exempt. Else visit VFS Canada.", "estimated_days": 14, "documents_needed": ["BIL"], "tips": ["Re-use prior biometrics if within 10 years"]},
            {"step_number": 6, "title": "Medical (if required)", "description": "For healthcare/childcare/agriculture or from designated countries.", "estimated_days": 21, "documents_needed": ["Medical referral"], "tips": []},
            {"step_number": 7, "title": "Decision + Permit Issuance", "description": "If applying from in Canada, permit issued to mailing address. If outside Canada, Port of Entry Letter — work permit issued at POE.", "estimated_days": 90, "documents_needed": [], "tips": ["Apply for SIN (Social Insurance Number) immediately after receiving permit", "Bring permit to employer to start work legally"]},
        ],
        "document_checklist": [
            {"name": "Passport (valid)", "mandatory": True, "notes": ""},
            {"name": "Application form (IMM 5710 or IMM 1295)", "mandatory": True, "notes": "Digitally signed"},
            {"name": "Photos", "mandatory": True, "notes": "IRCC specs"},
            {"name": "PGWP-specific: Final transcript from DLI", "mandatory": True, "notes": "If applying for PGWP"},
            {"name": "PGWP-specific: Letter of program completion", "mandatory": True, "notes": "From DLI"},
            {"name": "SOWP-specific: Spouse's Study/Work Permit", "mandatory": True, "notes": "Copy"},
            {"name": "SOWP-specific: Marriage certificate / Common-law evidence", "mandatory": True, "notes": ""},
            {"name": "SOWP-specific: Spouse's enrollment / employment letter", "mandatory": True, "notes": "Confirming eligible program/job"},
            {"name": "BOWP-specific: PR application acknowledgment", "mandatory": True, "notes": "AOR letter"},
            {"name": "Form IMM 5645 — Family Information", "mandatory": True, "notes": ""},
            {"name": "Biometrics receipt", "mandatory": True, "notes": "If prior biometrics expired/never taken"},
            {"name": "Medical exam (if required)", "mandatory": False, "notes": "For specific occupations/durations"},
            {"name": "Police certificate (if requested)", "mandatory": False, "notes": "Not always asked for OWPs"},
            {"name": "Current work/study permit (if in Canada)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "PGWP: Program duration <8 months, or not in PGWP-eligible institution",
            "PGWP: Applied >180 days after final transcript",
            "PGWP: Online/distance learning beyond IRCC's tolerance",
            "SOWP: Spouse's program/job not eligible (changed criteria 2024)",
            "BOWP: PR application not yet 'accepted as eligible' (just submitted isn't enough)",
            "Misrepresentation in PGWP transcript / completion letter",
            "Inadmissibility (criminal record, medical condition)",
            "Insufficient evidence of relationship for SOWP",
        ],
        "success_tips": [
            "PGWP: Apply within 90 days of final transcript — much safer than waiting",
            "PGWP: Online study beyond 50% of program disqualifies you — keep records",
            "SOWP: Confirm your spouse's program is in the current eligible list (2024 changes excluded many)",
            "BOWP: File application 4-6 months before current permit expires — provides cushion",
            "Keep biometrics + medical valid — re-use within validity to skip steps",
            "Apply for SIN within 1 week of receiving permit",
        ],
        "faqs": [
            {"q": "How long is a PGWP valid?", "a": "Equal to program length: 8-23 months program = matching duration; 2+ years program = 3-year PGWP. Note: Master's <2yr = 3-year PGWP."},
            {"q": "Can I extend my PGWP?", "a": "No — PGWP is once-per-lifetime, non-extendable. After it expires, you must transition to LMIA-based work permit or other status."},
            {"q": "Can my spouse work on SOWP?", "a": "Yes — SOWP is OPEN, full work rights with any employer (except ineligible list). No LMIA needed."},
            {"q": "What's the eligible DLI list for PGWP?", "a": "Different from Study Permit DLI list. Many private colleges Study-Permit eligible are NOT PGWP eligible. Check IRCC's PGWP-eligible DLI list before enrolling."},
            {"q": "What if I'm waiting for PGWP — can I work?", "a": "If you applied for PGWP before your Study Permit expired, you can work full-time while waiting (implied status). After approval, switch to PGWP."},
            {"q": "Can I apply for OWP from outside Canada?", "a": "Yes for some categories (PGWP can be applied from inside or outside). SOWP often applied inside Canada. BOWP requires you to be in Canada."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit/temporary/open-work-permit.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit/temporary/open-work-permit.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit/post-graduation-work-permit-program.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit/temporary/work-permit-pgwp-eligibility.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit/temporary/bridging-open-work-permit.html",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against ircc.canada.ca on 2026-02-27. PGWP eligibility tightened Sep 2024 (program field restrictions). SOWP eligibility narrowed for spouses of undergraduate students.",
    },

    # ── 6. Visitor Visa (Temporary Resident Visa) ──────────────────────────────
    {
        "country_code": "CA",
        "country_name": "Canada",
        "subclass_id": "Visitor-Visa",
        "subclass_name": "Visitor Visa (Temporary Resident Visa)",
        "service_type": "visitor",
        "category": "immigration",
        "description": (
            "The Canada Visitor Visa, officially called a Temporary Resident Visa (TRV), is required for "
            "Indian nationals visiting Canada for tourism, business, family visits, or short-term study/work "
            "exempted activities. It is a counterfoil placed in the passport authorising the holder to seek "
            "entry at a Canadian port of entry (POE). The actual permitted stay is determined by the CBSA "
            "officer at POE (typically 6 months for tourists).\n\n"
            "Canada also offers a **Super Visa** for parents/grandparents of Canadian citizens or PRs — a "
            "multi-entry visa valid up to 10 years with each visit allowing up to 5 years stay. Super Visa "
            "requires private health insurance (CAD 100,000+ coverage) and Letter of Invitation from sponsoring "
            "child/grandchild with income above LICO threshold."
        ),
        "eligibility_summary": (
            "Demonstrate intent to leave Canada at end of authorized stay, sufficient funds for visit + return, "
            "no criminal/security concerns, in good health (medical exam may be required for stays >6 months), "
            "and clear purpose (tourism, family visit, business, conference)."
        ),
        "eligibility_criteria": [
            {"label": "Intent to leave Canada", "value": "Must demonstrate strong ties to home country", "notes": "Family, property, employment, financial obligations"},
            {"label": "Sufficient funds", "value": "Demonstrate ability to pay for stay + return trip", "notes": "Typically CAD 1,500-2,500/month + return ticket"},
            {"label": "Admissibility", "value": "No criminal record, no security concerns, medically admissible", "notes": "Medical only if stay >6 months or working in healthcare/childcare/agriculture"},
            {"label": "Purpose", "value": "Clear, specific reason for visit (tourism/family/business/conference)", "notes": "Vague itinerary = high refusal risk"},
            {"label": "Biometrics", "value": "Mandatory for Indian nationals", "notes": "Valid 10 years"},
            {"label": "Super Visa specifics", "value": "Parent/grandparent of Canadian citizen/PR + child's income above LICO + medical insurance ≥CAD 100,000", "notes": "Multi-entry, 10-year validity, 5-year stay each visit"},
        ],
        "fees_local_currency_code": "CAD",
        "fees_local_currency_amount": 185,
        "fees_inr_approx": 11100,
        "fees_breakdown": [
            {"component": "Visitor Visa (single/multi-entry) — per person", "amount": 100, "currency": "CAD"},
            {"component": "Family rate (max 5 family members)", "amount": 500, "currency": "CAD"},
            {"component": "Biometrics — individual", "amount": 85, "currency": "CAD"},
            {"component": "Biometrics — family (2+)", "amount": 170, "currency": "CAD"},
            {"component": "Super Visa medical insurance (1 year coverage, CAD 100k+)", "amount": 1500, "currency": "CAD"},
            {"component": "Medical exam (if required for >6 month stay)", "amount": 7500, "currency": "INR"},
        ],
        "processing_time_days_min": 14,
        "processing_time_days_max": 60,
        "step_by_step": [
            {"step_number": 1, "title": "Determine Visa Type", "description": "Standard Visitor Visa (up to 10 years multi-entry, 6 month stay each) OR Super Visa (parents/grandparents, 5 year stay).", "estimated_days": 3, "documents_needed": [], "tips": ["Multi-entry is standard now for most approvals", "Super Visa if parent/grandparent of Canadian citizen/PR"]},
            {"step_number": 2, "title": "Gather Supporting Documents", "description": "Purpose-specific docs: invitation letter (family visit), conference registration (business), tour itinerary (tourism).", "estimated_days": 14, "documents_needed": ["Letter of Invitation (if visiting family)", "Travel itinerary", "Hotel bookings (if tourism)", "Conference invitation (if business)"], "tips": ["LOI must include host's status, address, relationship, financial commitment", "Conference invitation should mention registration paid"]},
            {"step_number": 3, "title": "Prepare Financial Proof", "description": "Show ability to fund the trip + return.", "estimated_days": 14, "documents_needed": ["6 months bank statements", "ITRs (last 2-3 years)", "Salary slips / business income proof", "Property documents (showing ties)"], "tips": ["CAD 2,000-3,000/month is comfortable", "Don't show sudden deposits — gradual healthy balance is best"]},
            {"step_number": 4, "title": "Complete Online Application", "description": "Apply via canada.ca/IRCC online with eAPP for TRV.", "estimated_days": 3, "documents_needed": ["Passport scan", "Photos", "Form IMM 5257 (Application for TRV)", "Form IMM 5645 (Family Info)", "Supporting docs"], "tips": ["Be honest about prior visa refusals (any country)", "List ALL family in Canada — concealment = refusal"]},
            {"step_number": 5, "title": "Pay Fees + Submit Biometrics", "description": "Pay online. Visit VFS Canada in India for biometrics within 30 days of BIL.", "estimated_days": 14, "documents_needed": ["BIL"], "tips": ["Re-use biometrics if within 10 years of prior"]},
            {"step_number": 6, "title": "Medical (Super Visa or >6 month stays)", "description": "Panel physician exam.", "estimated_days": 14, "documents_needed": ["Medical referral"], "tips": []},
            {"step_number": 7, "title": "Decision + Visa Counterfoil", "description": "Receive decision letter. If approved, mail passport to VFS for visa counterfoil. Standard processing: 14-30 days for Indian nationals.", "estimated_days": 30, "documents_needed": ["Passport"], "tips": ["Multi-entry valid up to passport expiry or 10 years (whichever first)"]},
            {"step_number": 8, "title": "Travel + POE", "description": "Travel within visa validity. CBSA officer at airport decides actual stay duration.", "estimated_days": 1, "documents_needed": ["Passport", "Itinerary", "Invitation letter", "Return ticket"], "tips": ["Carry proof of ties to home country", "Carry funds for entire stay", "Don't bring large cash (>CAD 10,000 must be declared)"]},
        ],
        "document_checklist": [
            {"name": "Passport (valid, min 6 months beyond intended stay)", "mandatory": True, "notes": ""},
            {"name": "Application form IMM 5257", "mandatory": True, "notes": "Digitally signed"},
            {"name": "Form IMM 5645 — Family Information", "mandatory": True, "notes": "ALL family members listed"},
            {"name": "Photos", "mandatory": True, "notes": "IRCC specs"},
            {"name": "Letter of Invitation (if family visit)", "mandatory": False, "notes": "From Canadian host with relationship + commitment"},
            {"name": "Host's PR card / citizenship + ITR copy (if LOI)", "mandatory": False, "notes": "Establishes host status"},
            {"name": "Travel itinerary / Hotel bookings (if tourism)", "mandatory": False, "notes": "Tentative is acceptable"},
            {"name": "Conference invitation + registration (if business)", "mandatory": False, "notes": ""},
            {"name": "Bank statements (last 6 months)", "mandatory": True, "notes": "Demonstrate funds"},
            {"name": "Income Tax Returns (last 2-3 years)", "mandatory": True, "notes": "Demonstrates economic ties"},
            {"name": "Salary slips / Business income proof", "mandatory": True, "notes": "Last 3-6 months"},
            {"name": "Property documents (home ownership / rental)", "mandatory": False, "notes": "Demonstrates ties to home"},
            {"name": "Biometrics (VFS Canada)", "mandatory": True, "notes": "Within 30 days of BIL"},
            {"name": "Super Visa medical insurance certificate (if Super Visa)", "mandatory": False, "notes": "Min CAD 100,000 coverage, 1 year"},
            {"name": "Leave letter from employer (if employed)", "mandatory": False, "notes": "Shows return to job"},
            {"name": "Marriage cert + children's birth certs (if family travel)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Insufficient ties to home country — IRCC believes you won't return",
            "Insufficient funds for stay + return",
            "Vague or implausible purpose / itinerary",
            "Prior visa refusal (any country) not declared",
            "Family member already in Canada with PR/citizenship raises immigration intent concern",
            "Misrepresentation of finances or relationship to host",
            "Long stays (>30 days) without strong reason raises suspicion",
            "Lack of return ticket booking",
        ],
        "success_tips": [
            "Apply 2-3 months before intended travel — gives buffer for delays",
            "Multi-entry is now the default in approvals — apply with that intent",
            "If first-time Canada visitor: shorter stay (2-3 weeks) + strong return proof = highest approval rate",
            "Family visit applications: LOI from host + clear relationship docs + host's financial stability",
            "Super Visa: research insurance providers (Manulife, Sun Life, GMS) before application",
            "Don't bundle Canada with USA application — handle separately",
            "Have a clear itinerary even if not booked — purpose, places, return date",
        ],
        "faqs": [
            {"q": "How long can I stay on a Visitor Visa?", "a": "Decided by CBSA officer at port of entry — typically 6 months. Multi-entry visa allows multiple trips within visa validity period (up to 10 years)."},
            {"q": "What's the difference between Visitor Visa and eTA?", "a": "Visitor Visa is required for Indian nationals (and many other visa-required countries). eTA (Electronic Travel Authorization) is for visa-exempt nationalities (UK, USA, Australia, EU). Indians need Visitor Visa, not eTA."},
            {"q": "Can I extend my stay?", "a": "Yes — apply for a Visitor Record before current authorized stay expires. Allow 30+ days lead time."},
            {"q": "Can I work or study on Visitor Visa?", "a": "Generally NO — work requires Work Permit (with some exceptions for business visitors). Short courses (<6 months, non-credit) allowed without Study Permit."},
            {"q": "What is Super Visa?", "a": "Special visa for parents/grandparents of Canadian citizens/PRs. Multi-entry, valid up to 10 years, each visit can be up to 5 years. Requires CAD 100k+ medical insurance + sponsoring child's income above LICO."},
            {"q": "Can my Visitor Visa be cancelled at the airport?", "a": "Yes — CBSA officer has final discretion. They can refuse entry, grant shorter stay, or cancel visa. Carry strong evidence of purpose + ties to home."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada/apply-visitor-visa.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada/parent-grandparent-super-visa.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada/apply-visitor-visa/eligibility.html",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against ircc.canada.ca on 2026-02-27. Super Visa insurance threshold (CAD 100k) per 2022 update.",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# NEW ZEALAND (NZ) — 6 verified subclasses
# Source: immigration.govt.nz · Feb 2026 fee schedule · FX: 1 NZD ≈ 50 INR
# ──────────────────────────────────────────────────────────────────────────────
NEW_ZEALAND_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. Skilled Migrant Category (SMC) Resident Visa ───────────────────────
    {
        "country_code": "NZ",
        "country_name": "New Zealand",
        "subclass_id": "SMC",
        "subclass_name": "Skilled Migrant Category (SMC) Resident Visa — 6-Point System",
        "service_type": "pr",
        "category": "immigration",
        "description": (
            "The Skilled Migrant Category (SMC) Resident Visa is New Zealand's primary skilled migration "
            "pathway, granting direct permanent residence to skilled workers. Following the September 2023 "
            "reform, SMC moved from a complex points-based system to a streamlined **6-point system** where "
            "applicants must score a minimum of 6 points across three categories: occupational registration, "
            "qualifications, and skilled work experience or income.\n\n"
            "Candidates submit an Expression of Interest (EOI), and those meeting the threshold are invited to "
            "apply for residence directly. The system rewards candidates with NZ-recognised registration "
            "(medical, engineering, teaching), high-level qualifications, or strong income above multiples of "
            "the median wage. Successful applicants receive a Resident Visa with no conditions on travel and "
            "with the right to apply for Permanent Resident Visa after 2 years."
        ),
        "eligibility_summary": (
            "Minimum 6 points across: (a) occupational registration (3-6 pts), (b) qualifications "
            "(3-5 pts), (c) NZ income at multiples of median wage (3-6 pts). Plus: under 56 years, "
            "good health and character, IELTS 6.5 overall (or equivalent), and a skilled job offer "
            "from accredited employer paying ≥ median wage (NZD 33.56/hour as of 2025 update)."
        ),
        "eligibility_criteria": [
            {"label": "Age", "value": "Under 56 years at time of application", "notes": "Strict — no waiver"},
            {"label": "Health + Character", "value": "Acceptable health (medical exam) + good character (PCCs)", "notes": "Medical exam by INZ panel physician; PCCs from each country lived 12+ months"},
            {"label": "English", "value": "IELTS 6.5 overall OR equivalent (PTE 58, TOEFL iBT 79, OET grade B average)", "notes": "Both Principal + partner if Partner included in application"},
            {"label": "6 Points (minimum)", "value": "Across occupational registration + qualifications + income/experience", "notes": "Reg: NZ Medical Council/Engineering NZ etc. = 3-6 pts; Qual: Bachelor's = 3, Master's = 4, Doctorate = 5; Income: 1.5× median wage = 3 pts, 3× = 6 pts"},
            {"label": "Skilled employment", "value": "Job offer from accredited employer at or above NZ median wage", "notes": "NZD 33.56/hour as of 2025 update — verify current rate"},
            {"label": "Submitted EOI selected", "value": "EOI must meet 6 points and be selected from pool", "notes": "Selection typically every 2 weeks if meeting threshold"},
            {"label": "Settlement intent", "value": "Genuine intent to live and work in NZ long-term", "notes": "Demonstrated via family, ties, employment commitment"},
        ],
        "fees_local_currency_code": "NZD",
        "fees_local_currency_amount": 6280,
        "fees_inr_approx": 314000,
        "fees_breakdown": [
            {"component": "EOI submission fee", "amount": 530, "currency": "NZD"},
            {"component": "Resident Visa application — Principal applicant", "amount": 5860, "currency": "NZD"},
            {"component": "Resident Visa application — Partner (if included)", "amount": 5860, "currency": "NZD"},
            {"component": "Dependent child (each)", "amount": 530, "currency": "NZD"},
            {"component": "Migrant Levy (varies by country, India ~NZD 280)", "amount": 280, "currency": "NZD"},
            {"component": "IELTS Academic test (India)", "amount": 16800, "currency": "INR"},
            {"component": "Medical exam (INZ panel physician)", "amount": 7500, "currency": "INR"},
            {"component": "Police Clearance (India + each country 12+ months)", "amount": 1000, "currency": "INR"},
            {"component": "Qualification assessment (NZQA IQA — if non-NZ qualification)", "amount": 985, "currency": "NZD"},
        ],
        "processing_time_days_min": 180,
        "processing_time_days_max": 540,
        "step_by_step": [
            {"step_number": 1, "title": "NZQA International Qualifications Assessment (IQA)", "description": "Submit your foreign qualifications to NZQA for assessment. NZQA IQA confirms NZ equivalency of your degree. Validity: lifetime once issued.", "estimated_days": 30, "documents_needed": ["Degree certificates", "Final transcripts (sealed)", "Identity proof"], "tips": ["NZQA IQA is mandatory for non-NZ qualifications", "Order sealed transcripts directly from university", "Processing 4-6 weeks typically"]},
            {"step_number": 2, "title": "Language Test (IELTS / PTE / TOEFL / OET)", "description": "Take an approved English language test. Minimum IELTS 6.5 overall (no band below 6.0 in most cases).", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["IELTS results valid 2 years", "Aim for higher overall band for adaptability points"]},
            {"step_number": 3, "title": "Secure Job Offer from Accredited Employer", "description": "Job must be from an INZ-accredited employer at or above the NZ median wage. Employer accreditation can be verified via INZ employer list.", "estimated_days": 90, "documents_needed": ["Job offer letter (with hours, salary, role)", "Employer accreditation number"], "tips": ["Verify employer accreditation BEFORE accepting job", "Salary must be ≥ NZD 33.56/hour median (FY2025 update)", "Role must require Level 4+ qualification or 3+ years experience"]},
            {"step_number": 4, "title": "Submit Expression of Interest (EOI)", "description": "Complete EOI online via Immigration NZ portal. EOI captures qualifications, registration, income, work experience. System auto-calculates points.", "estimated_days": 3, "documents_needed": ["NZQA IQA result", "Language test", "Job offer details", "Registration certificate (if applicable)"], "tips": ["EOI valid 6 months in pool", "Selection happens fortnightly for those meeting 6 points"]},
            {"step_number": 5, "title": "Receive Invitation to Apply (ITA)", "description": "If EOI is selected, INZ issues ITA. You have 4 months from ITA to submit full Residence application.", "estimated_days": 60, "documents_needed": [], "tips": ["Start gathering documents during EOI wait", "Don't miss 4-month deadline"]},
            {"step_number": 6, "title": "Submit Full Residence Application", "description": "Complete online application with all documents, pay fees, declare any criminal/medical history.", "estimated_days": 14, "documents_needed": ["Passport", "Birth/marriage certs", "Children's birth certs", "Job offer + employer accreditation", "NZQA IQA", "Language test", "Registration cert (if applicable)", "Medical exam", "PCCs", "Income proof (payslips, IRD)", "Photos"], "tips": ["Use INZ-approved checklist", "Pay Migrant Levy along with application fee"]},
            {"step_number": 7, "title": "INZ Decision + Medical/Character Review", "description": "INZ reviews application, may request additional documents (Section 27). Processing 6-12 months typical.", "estimated_days": 270, "documents_needed": [], "tips": ["Respond to S27 requests within 14 days", "Keep employer informed if job offer expires"]},
            {"step_number": 8, "title": "Resident Visa Granted + Activation", "description": "Receive Resident Visa label in passport. Must enter NZ before 'first entry date' (usually 12 months). Can apply for Permanent Resident Visa after 2 years.", "estimated_days": 60, "documents_needed": [], "tips": ["Enter NZ before first-entry expiry", "Apply for IRD number + NZ bank account post-arrival"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (all family members)", "mandatory": True, "notes": "Min 6 months validity"},
            {"name": "Birth certificates (all applicants)", "mandatory": True, "notes": "Apostilled/notarised if not in English"},
            {"name": "Marriage certificate (if partner included)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certificates (if dependents)", "mandatory": True, "notes": ""},
            {"name": "NZQA International Qualifications Assessment (IQA)", "mandatory": True, "notes": "Required for non-NZ qualifications"},
            {"name": "Degree certificates + sealed transcripts", "mandatory": True, "notes": "Submitted to NZQA"},
            {"name": "IELTS/PTE/TOEFL/OET language test result", "mandatory": True, "notes": "Min IELTS 6.5 overall"},
            {"name": "Job offer letter from accredited employer", "mandatory": True, "notes": "Including pay, hours, role description, employer accreditation number"},
            {"name": "Employer accreditation evidence", "mandatory": True, "notes": "Verifiable via INZ portal"},
            {"name": "Occupational registration certificate (if claiming points)", "mandatory": False, "notes": "NZ Medical Council, Engineering NZ, NZ Teaching Council, etc."},
            {"name": "Work experience reference letters", "mandatory": True, "notes": "From past employers — duties, hours, dates"},
            {"name": "Income proof (recent payslips, IRD/tax records)", "mandatory": True, "notes": "Demonstrating role + remuneration claims"},
            {"name": "Medical exam (INZ panel physician)", "mandatory": True, "notes": "eMedical link from INZ"},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": "From each country lived 12+ months in past 10 years"},
            {"name": "Photos (INZ specifications)", "mandatory": True, "notes": ""},
            {"name": "Personal History form INZ 1027", "mandatory": True, "notes": "10-year address/employment timeline"},
        ],
        "common_rejection_reasons": [
            "Insufficient points — less than 6 across the 3 categories",
            "Job offer not from accredited employer or below median wage threshold",
            "NZQA IQA showing qualification below Bachelor's equivalency (when claiming qual points)",
            "Misrepresentation on income claims (claimed not matched by payslips/IRD records)",
            "Health inadmissibility — undisclosed serious condition raising acceptable threshold concerns",
            "Character issues — undisclosed prior visa refusals (any country) or criminal record",
            "Age over 56 at application (strict, no waiver)",
            "Insufficient English (IELTS below 6.5 overall)",
        ],
        "success_tips": [
            "Stack registration + qualifications + income to comfortably exceed 6 points",
            "Occupational registration in NZ before applying is a strong boost (e.g. NZ Medical Council)",
            "Salary at 1.5× median wage = 3 pts; aim for 2× or 3× for higher points",
            "Job offer must be GENUINE skilled employment matching ANZSCO Level 1-3",
            "Pre-verify employer accreditation status (INZ publishes accredited employer list)",
            "Get NZQA IQA done EARLY — it's a lifetime certificate worth obtaining anyway",
            "Partner's language and qualifications can add adaptability points",
            "Apply 6-12 months before age 56 cutoff if approaching",
        ],
        "faqs": [
            {"q": "How is the new 6-point system different from old?", "a": "Pre-2023 SMC used 160-point system with many small contributors. Post-2023 simplified to 3 categories with min 6 points: registration (3-6), qualifications (3-5), income (3-6) OR skilled work experience (3-6)."},
            {"q": "What is NZ's current median wage?", "a": "NZD 33.56/hour as of Feb 2025 update — INZ updates annually. Verify current rate at immigration.govt.nz before applying."},
            {"q": "Can I get SMC PR without a job offer?", "a": "Generally NO under new system — job offer from accredited employer at or above median wage is required for the income points. Exception: high-point income from non-NZ employment may suffice in rare cases."},
            {"q": "What if my qualification isn't on NZ skill shortage list?", "a": "SMC doesn't have a specific shortage list (different from Green List). Qualification just needs NZQA IQA equivalency at Bachelor's+ to score points."},
            {"q": "Difference between SMC and Green List?", "a": "Green List = priority occupations with direct-to-residence at Tier 1 (no points calculation, just qualifying occupation + job offer). SMC = points-based, broader occupational scope."},
            {"q": "How does Partner of Worker contribute?", "a": "Partner can be added to your Residence application. Partner with Bachelor's + good English does NOT add SMC points (post-2023 reform), but they get PR alongside you."},
        ],
        "official_url": "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/skilled-migrant-category-resident-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/skilled-migrant-category-resident-visa",
            "https://www.immigration.govt.nz/new-zealand-visas/preparing-a-visa-application/the-application-process/expressions-of-interest",
            "https://www.nzqa.govt.nz/qualifications-standards/international-qualifications/get-an-international-qualification-assessed/",
            "https://www.immigration.govt.nz/employ-migrants/employer-accreditation-and-the-accredited-employer-work-visa",
            "https://www.immigration.govt.nz/about-us/policy-and-law/how-the-immigration-system-operates/fees-and-levies",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immigration.govt.nz on 2026-02-27. 6-point system per Sep 2023 reform. Median wage NZD 33.56/hour per 2025 update; check current at INZ.",
    },

    # ── 2. Green List — Tier 1 Straight to Residence ──────────────────────────
    {
        "country_code": "NZ",
        "country_name": "New Zealand",
        "subclass_id": "Green-List-T1",
        "subclass_name": "Green List Tier 1 — Straight to Residence Visa",
        "service_type": "pr",
        "category": "immigration",
        "description": (
            "The Green List Tier 1 Visa provides a fast-tracked, **direct-to-Residence** pathway for highly "
            "skilled workers in occupations that NZ has identified as in critical, ongoing shortage. Unlike "
            "the points-based SMC, Tier 1 applicants do NOT need to accumulate 6 points — they simply need a "
            "qualifying Green List Tier 1 occupation, a job offer from an accredited NZ employer at or above "
            "median wage (or other remuneration threshold for specific roles), and standard health/character "
            "checks.\n\n"
            "Green List Tier 1 occupations include doctors (general practitioners + specialists), "
            "registered nurses, midwives, engineers (electrical, civil, mechanical, environmental, "
            "structural, telecommunications), ICT professionals (network/systems analysts, security "
            "specialists, multimedia specialists), construction project managers, surveyors, secondary "
            "school teachers (specific subjects), audiologists, dentists, and veterinarians, among others. "
            "Tier 2 (Work-to-Residence) is for less critical-shortage Green List roles requiring 24 months "
            "Work Visa before Residence."
        ),
        "eligibility_summary": (
            "Job offer in a Green List Tier 1 occupation from an accredited NZ employer at or above median "
            "wage (or specific remuneration threshold), occupational registration if required for role, "
            "IELTS 6.5 overall, age under 56, health and character compliance."
        ),
        "eligibility_criteria": [
            {"label": "Tier 1 Green List occupation", "value": "Job in INZ's published Green List Tier 1 occupations", "notes": "List published at immigration.govt.nz/green-list — updated periodically"},
            {"label": "Accredited employer + job offer", "value": "Job offer from INZ-accredited employer at or above median wage", "notes": "Median wage NZD 33.56/hour (Feb 2025); some roles have specific remuneration thresholds"},
            {"label": "Occupational registration (if applicable)", "value": "Required for medical, engineering, teaching, surveying, dentistry roles", "notes": "Examples: NZ Medical Council registration, Engineering NZ membership, NZ Teaching Council, etc."},
            {"label": "Qualifications", "value": "Meet qualification requirements for the specific Green List role", "notes": "Some roles require NZ-recognised degree, others accept overseas equivalent via NZQA IQA"},
            {"label": "Age", "value": "Under 56 years at time of application", "notes": ""},
            {"label": "English", "value": "IELTS 6.5 overall (or equivalent)", "notes": ""},
            {"label": "Health + Character", "value": "Acceptable health + clean criminal record", "notes": "Standard INZ medical + PCCs"},
        ],
        "fees_local_currency_code": "NZD",
        "fees_local_currency_amount": 4570,
        "fees_inr_approx": 228500,
        "fees_breakdown": [
            {"component": "Straight to Residence Visa application — Principal", "amount": 4290, "currency": "NZD"},
            {"component": "Resident Visa — Partner (if included)", "amount": 4290, "currency": "NZD"},
            {"component": "Dependent child (each)", "amount": 530, "currency": "NZD"},
            {"component": "Migrant Levy", "amount": 280, "currency": "NZD"},
            {"component": "IELTS Academic test", "amount": 16800, "currency": "INR"},
            {"component": "Medical exam", "amount": 7500, "currency": "INR"},
            {"component": "PCCs", "amount": 1000, "currency": "INR"},
            {"component": "NZQA IQA (if needed)", "amount": 985, "currency": "NZD"},
            {"component": "Occupational registration fees (varies; NZMC ~NZD 1,500)", "amount": 1500, "currency": "NZD"},
        ],
        "processing_time_days_min": 60,
        "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Green List Tier 1 Occupation", "description": "Verify your occupation is on the current Green List Tier 1 at immigration.govt.nz. Note: list updated periodically; check at time of application.", "estimated_days": 7, "documents_needed": [], "tips": ["Tier 1 = straight to PR; Tier 2 = 24 months work first then PR", "If your role isn't Tier 1, consider AEWV + Tier 2 pathway"]},
            {"step_number": 2, "title": "Obtain Occupational Registration (if required)", "description": "If role requires NZ registration (medical, engineering, teaching, surveying), apply to the relevant NZ body before visa application.", "estimated_days": 90, "documents_needed": ["Degree + transcripts", "Reference letters", "Profession-specific exams (e.g. NZ Medical Council OET, IELTS Academic)"], "tips": ["NZMC for doctors — 3-6 month process", "Engineering NZ for engineers — 2-3 month process", "Get registration BEFORE applying for the visa for cleaner approval"]},
            {"step_number": 3, "title": "Secure Job Offer from Accredited Employer", "description": "Accept job offer from INZ-accredited employer at or above median wage (or role-specific remuneration threshold).", "estimated_days": 60, "documents_needed": ["Job offer letter", "Employer accreditation number"], "tips": ["Many large NZ healthcare providers, IT firms, infrastructure companies are accredited", "Verify accreditation status via INZ portal"]},
            {"step_number": 4, "title": "Language Test (if needed)", "description": "Take IELTS / OET / TOEFL / PTE. Some Tier 1 roles + registration requires specific tests (e.g. OET for medical).", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["OET preferred for medical/nursing", "Min IELTS 6.5 overall for Resident Visa"]},
            {"step_number": 5, "title": "NZQA IQA (if needed)", "description": "For non-NZ qualifications. Some Green List roles waive IQA if registration is granted.", "estimated_days": 30, "documents_needed": ["Degree certificates", "Sealed transcripts"], "tips": ["Lifetime validity once issued"]},
            {"step_number": 6, "title": "Submit Straight to Residence Visa Application", "description": "Apply directly for Resident Visa via Immigration Online. No EOI/ITA needed — apply directly.", "estimated_days": 14, "documents_needed": ["Passport", "Birth/marriage certs", "Children's birth certs", "Job offer + accreditation", "Registration cert", "NZQA IQA (or exemption)", "Language test", "Income proof", "Medical exam", "PCCs"], "tips": ["No selection wait — submit when ready", "Use Immigration Online portal"]},
            {"step_number": 7, "title": "INZ Processing + Decision", "description": "Typically 3-6 months for Tier 1. INZ may request additional info (Section 27).", "estimated_days": 120, "documents_needed": [], "tips": ["Respond to S27 promptly", "Faster than SMC (no EOI/ITA steps)"]},
            {"step_number": 8, "title": "Resident Visa + Activation", "description": "Receive Resident Visa. Enter NZ before first-entry date.", "estimated_days": 60, "documents_needed": [], "tips": ["Apply for IRD number + NZ bank post-arrival", "Permanent Resident Visa available after 2 years"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (all family members)", "mandatory": True, "notes": ""},
            {"name": "Birth + marriage + children's birth certificates", "mandatory": True, "notes": ""},
            {"name": "Job offer letter from accredited employer", "mandatory": True, "notes": "On letterhead with pay, hours, role"},
            {"name": "Employer accreditation evidence (INZ verification)", "mandatory": True, "notes": ""},
            {"name": "Occupational registration certificate", "mandatory": False, "notes": "Mandatory for medical/engineering/teaching roles"},
            {"name": "NZQA IQA result (or exemption)", "mandatory": False, "notes": "May be waived if NZ registration granted"},
            {"name": "Degree certificates + sealed transcripts", "mandatory": True, "notes": ""},
            {"name": "Language test result (IELTS/OET/PTE)", "mandatory": True, "notes": "Min IELTS 6.5 overall"},
            {"name": "Income/payslip proof of current employment", "mandatory": True, "notes": "If transferring from current job"},
            {"name": "Work experience reference letters", "mandatory": True, "notes": "All relevant past employment"},
            {"name": "Medical exam (INZ panel physician)", "mandatory": True, "notes": ""},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": "Each country lived 12+ months past 10 years"},
            {"name": "Photos (INZ specifications)", "mandatory": True, "notes": ""},
            {"name": "Personal History form INZ 1027", "mandatory": True, "notes": ""},
            {"name": "Family Information form", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Occupation not on current Green List Tier 1 (changes periodically)",
            "Job offer not from INZ-accredited employer",
            "Pay below median wage threshold (or role-specific minimum)",
            "Occupational registration not in place when required (e.g. doctor without NZMC)",
            "Misrepresentation of qualifications or experience",
            "Health/character inadmissibility",
            "Age over 56 (no waiver)",
            "Insufficient English (below IELTS 6.5)",
        ],
        "success_tips": [
            "Get NZ occupational registration BEFORE applying for visa — strengthens approval significantly",
            "Choose employers known for accreditation + strong INZ track record",
            "Pay attention to role-specific remuneration thresholds (some Tier 1 roles have higher)",
            "Keep documents bundled before applying — INZ Section 27 requests slow processing",
            "Maintain English proficiency above IELTS 6.5 for adaptability",
            "Consider IQA early — lifetime validity, often required regardless",
            "Get strong reference letters from current employer covering NZ-relevant skills",
            "If applying with partner — partner's qualifications + language strengthen overall case",
        ],
        "faqs": [
            {"q": "What's the Green List?", "a": "INZ-published list of priority occupations divided into Tier 1 (straight to residence) and Tier 2 (work-to-residence after 24 months). Updated periodically based on labour market data."},
            {"q": "Do I need to be in NZ to apply for Tier 1?", "a": "No — you can apply from outside NZ. Some employers may prefer to interview in person but visa application is fully online."},
            {"q": "How long does Tier 1 take vs SMC?", "a": "Tier 1 typically 3-6 months (no EOI/ITA). SMC takes 6-12 months including EOI selection wait."},
            {"q": "Can I bring my family?", "a": "Yes — partner + dependent children up to 24 years (full-time student) can be included on Resident Visa. Same fees as Principal."},
            {"q": "Difference between Resident Visa and PR Visa?", "a": "Resident Visa = limited travel rights, granted first. After 2 years, eligible for Permanent Resident Visa (PRV) with unlimited travel rights. Both confer same residence in NZ."},
            {"q": "What if my Tier 1 role becomes Tier 2 between application stages?", "a": "Application is assessed at date of receipt. If role was Tier 1 when you applied, you continue under Tier 1 rules even if list changes after."},
        ],
        "official_url": "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/straight-to-residence-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/straight-to-residence-visa",
            "https://www.immigration.govt.nz/employ-migrants/recruit-overseas/green-list-skilled-jobs",
            "https://www.immigration.govt.nz/new-zealand-visas/preparing-a-visa-application/jobs/the-green-list",
            "https://www.nzqa.govt.nz/qualifications-standards/international-qualifications/",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immigration.govt.nz on 2026-02-27. Green List Tier 1 + Tier 2 occupational divisions per current INZ policy.",
    },

    # ── 3. Accredited Employer Work Visa (AEWV) ───────────────────────────────
    {
        "country_code": "NZ",
        "country_name": "New Zealand",
        "subclass_id": "AEWV",
        "subclass_name": "Accredited Employer Work Visa (AEWV)",
        "service_type": "work",
        "category": "immigration",
        "description": (
            "The Accredited Employer Work Visa (AEWV) is New Zealand's primary employer-sponsored temporary "
            "work visa, replacing the old Essential Skills Work Visa in mid-2022. It is a 3-step process "
            "from the employer + worker side: (1) **Employer accreditation** with INZ, (2) **Job check** "
            "(verifying the role can't be filled by NZ workers), (3) **Worker visa application** by the "
            "migrant.\n\n"
            "AEWV duration depends on the role's median wage band: roles paying at or above median wage = up "
            "to **3 years**; roles below median wage in approved sectors = up to **2 years** with no pathway "
            "to residence directly. AEWV holders working in Green List Tier 2 occupations can transition to "
            "Resident Visa after 24 months continuous work."
        ),
        "eligibility_summary": (
            "Job offer from INZ-accredited employer that passed Job Check, role pays at or above median wage "
            "(or sector-specific minimum), worker meets relevant qualifications/experience for the role, "
            "language proficiency where needed (IELTS 4.0 for low-skilled, 5.0+ for medium), good health "
            "and character."
        ),
        "eligibility_criteria": [
            {"label": "Accredited employer", "value": "Job offer must be from INZ-accredited employer (visible on INZ accredited employer list)", "notes": "Employer accreditation tiers: Standard (1-5 workers), High-Volume (6+ workers), Franchisee, Triangular"},
            {"label": "Job Check passed", "value": "Employer must have submitted + had approved a Job Check for the specific role", "notes": "Job Check valid 6 months; proves no NZ worker available"},
            {"label": "Skilled employment", "value": "Role must match ANZSCO Level 1-3 OR be on Green List", "notes": "Some sector-specific lower-skilled roles allowed at reduced thresholds"},
            {"label": "Pay threshold", "value": "Median wage (NZD 33.56/hour Feb 2025) OR sector-specific minimum", "notes": "Below median = 2-year max visa; at/above median = 3-year visa"},
            {"label": "Worker qualifications", "value": "Relevant qualifications + work experience for the role", "notes": "Specific to role; some require trade certificate, some degree, some experience only"},
            {"label": "Age", "value": "No specific age limit", "notes": "Standard 'genuine intention' assessment applies"},
            {"label": "Language", "value": "IELTS overall 4.0 minimum (or equivalent) for some sectors; not required for higher-skilled", "notes": "Higher language often improves approval odds"},
            {"label": "Health + Character", "value": "Medical (if 6+ month stay) + PCCs if requested", "notes": ""},
        ],
        "fees_local_currency_code": "NZD",
        "fees_local_currency_amount": 805,
        "fees_inr_approx": 40250,
        "fees_breakdown": [
            {"component": "AEWV application fee", "amount": 750, "currency": "NZD"},
            {"component": "Immigration Levy", "amount": 55, "currency": "NZD"},
            {"component": "Medical exam (if 6+ month stay)", "amount": 7500, "currency": "INR"},
            {"component": "PCC (India)", "amount": 500, "currency": "INR"},
            {"component": "IELTS test (if required)", "amount": 16800, "currency": "INR"},
        ],
        "processing_time_days_min": 14,
        "processing_time_days_max": 60,
        "step_by_step": [
            {"step_number": 1, "title": "Employer Accreditation + Job Check (by Employer)", "description": "Before worker can apply, employer must be INZ-accredited and the specific role must have passed a Job Check. Worker doesn't drive these steps but should verify both before accepting job.", "estimated_days": 60, "documents_needed": [], "tips": ["Verify employer accreditation via INZ public list", "Ask for Job Check approval reference number"]},
            {"step_number": 2, "title": "Accept Job Offer", "description": "Worker accepts written job offer from accredited employer. Offer must specify role, hours (≥30/week typically), pay, location, duration.", "estimated_days": 7, "documents_needed": ["Signed employment agreement", "Job offer letter"], "tips": ["Agreement must comply with NZ Employment Relations Act", "Pay must meet declared threshold"]},
            {"step_number": 3, "title": "Gather Qualifications + Experience Evidence", "description": "Compile proof of qualifications, work experience, and language test (if applicable).", "estimated_days": 14, "documents_needed": ["Degree certificates", "Transcripts", "Work reference letters", "Language test (if required)"], "tips": ["NZQA IQA not required for AEWV (unlike SMC/Tier 1)", "Reference letters with hours/duties strengthen application"]},
            {"step_number": 4, "title": "Medical Exam (if 6+ month visa)", "description": "Visit INZ panel physician in India.", "estimated_days": 14, "documents_needed": ["eMedical link"], "tips": ["Valid 36 months", "Required for visas >6 months OR working in healthcare/childcare"]},
            {"step_number": 5, "title": "Police Clearance Certificate", "description": "Apply at India PSK; required if applicant has lived in any country 5+ years OR for some sectors.", "estimated_days": 21, "documents_needed": ["PCC application"], "tips": ["Apostille if requested"]},
            {"step_number": 6, "title": "Submit AEWV Application Online", "description": "Complete application via Immigration Online portal. Upload all documents.", "estimated_days": 3, "documents_needed": ["Passport", "Job offer + employment agreement", "Accreditation + Job Check refs", "Qualifications", "Work experience", "Medical", "PCC", "Photos"], "tips": ["Pay application fee + Immigration Levy together", "Accredited employer can sometimes initiate the application on worker's behalf"]},
            {"step_number": 7, "title": "INZ Decision", "description": "Processing 2-4 weeks for accredited employer workers. Faster than non-AEWV visas.", "estimated_days": 21, "documents_needed": [], "tips": ["AEWV processing prioritised for accredited employer applications"]},
            {"step_number": 8, "title": "Visa Granted + Travel to NZ", "description": "Receive Work Visa electronically. Travel to NZ within visa validity (typically multi-entry). Start work upon arrival.", "estimated_days": 30, "documents_needed": [], "tips": ["AEWV is employer-specific — can't switch employers without new visa", "Must work full-time minimum hours specified"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (min 3 months beyond intended stay)", "mandatory": True, "notes": ""},
            {"name": "Signed employment agreement (NZ Employment Act compliant)", "mandatory": True, "notes": ""},
            {"name": "Job offer letter (role, pay, hours, duration)", "mandatory": True, "notes": ""},
            {"name": "Employer accreditation reference (INZ)", "mandatory": True, "notes": "Verify via INZ portal"},
            {"name": "Job Check approval reference", "mandatory": True, "notes": "Provided by employer"},
            {"name": "Qualifications relevant to role (degree/trade certificate)", "mandatory": True, "notes": "Translation if not English"},
            {"name": "Work experience reference letters", "mandatory": True, "notes": "Past relevant employment"},
            {"name": "Language test (if sector-required, e.g. care, transport)", "mandatory": False, "notes": "Min IELTS 4.0 for some sectors"},
            {"name": "Medical exam (if 6+ month stay)", "mandatory": False, "notes": "INZ panel physician"},
            {"name": "Police Clearance Certificate", "mandatory": False, "notes": "India PSK; required if lived in any country 5+ years"},
            {"name": "Passport-style photos", "mandatory": True, "notes": "INZ specifications"},
            {"name": "Personal History form INZ 1027 (if requested)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Employer not accredited or accreditation expired",
            "Job Check not approved or expired (6-month validity)",
            "Pay below applicable threshold (median wage or sector minimum)",
            "Worker doesn't meet qualifications/experience requirements for role",
            "ANZSCO level mismatch — role classified as lower than claimed",
            "Misrepresentation of qualifications or work history",
            "Health/character concerns",
            "Insufficient English when sector requires it",
        ],
        "success_tips": [
            "Verify employer accreditation + Job Check status BEFORE accepting job",
            "Get pay at or above median wage for 3-year visa (vs. 2-year below)",
            "Match ANZSCO description carefully — your role should match Level 1-3 duties",
            "Compile reference letters with explicit hours/duties early",
            "Don't job-hop — AEWV is employer-specific; new employer = new visa application",
            "Consider Green List Tier 2 occupations — pathway to PR after 24 months",
            "Keep employment continuous and full-time during AEWV duration",
        ],
        "faqs": [
            {"q": "Can I switch employers on AEWV?", "a": "No — AEWV is employer-specific. To switch, you need a new AEWV with new employer (who must also be accredited)."},
            {"q": "What is median wage threshold?", "a": "NZD 33.56/hour as of Feb 2025 update. INZ revises annually. Roles at/above this get 3-year visa; below get 2-year (in approved sectors only)."},
            {"q": "Can AEWV lead to PR?", "a": "Indirectly. AEWV roles in Green List Tier 2 occupations can transition to Resident Visa after 24 months continuous work. AEWV roles meeting SMC points criteria can also apply for SMC PR."},
            {"q": "Can family come with me?", "a": "Yes — partner and dependent children. Partner of AEWV holder paying median wage+ can get Open Work Visa. Children can attend NZ schools."},
            {"q": "What's employer accreditation?", "a": "INZ certifies that employers are stable, compliant with employment law, and committed to upskilling NZ workers. Without accreditation, employer cannot sponsor AEWVs."},
            {"q": "What is a Job Check?", "a": "Process where INZ verifies the specific role can't be filled by NZ workers (labour market test). Employer advertises, demonstrates no suitable NZ candidates, then Job Check approved. Valid 6 months."},
        ],
        "official_url": "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/accredited-employer-work-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/accredited-employer-work-visa",
            "https://www.immigration.govt.nz/employ-migrants/employer-accreditation-and-the-accredited-employer-work-visa",
            "https://www.immigration.govt.nz/employ-migrants/get-a-job-check",
            "https://www.immigration.govt.nz/about-us/policy-and-law/how-the-immigration-system-operates/fees-and-levies",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immigration.govt.nz on 2026-02-27. AEWV introduced mid-2022 replacing Essential Skills Work Visa.",
    },

    # ── 4. Student Visa ────────────────────────────────────────────────────────
    {
        "country_code": "NZ",
        "country_name": "New Zealand",
        "subclass_id": "Student",
        "subclass_name": "Fee-paying Student Visa (Long-term)",
        "service_type": "student",
        "category": "immigration",
        "description": (
            "The Fee-paying Student Visa allows international students to study full-time at a NZQA-approved "
            "educational provider in NZ. It's the standard student visa for university bachelor's, master's, "
            "PhD; polytechnic diplomas; and English language schools.\n\n"
            "Critically, NZ allows graduates of Level 7+ (Bachelor's and above) qualifications to qualify "
            "for a **Post-Study Work Visa (PSWV)** of 1-3 years, opening pathways to AEWV and eventually "
            "SMC/Green List PR. Working rights on Student Visa: up to **20 hours/week during term**, full-"
            "time during scheduled breaks. PhD + research master's students can work UNLIMITED hours."
        ),
        "eligibility_summary": (
            "Offer of Place from NZQA-approved educational provider (university, polytechnic, PTE), proof "
            "of funds (tuition + NZD 17,000/year for ≥36 month programs or NZD 1,667/month for ≤36 month "
            "programs for cost of living), IELTS Academic 5.5+ (varies by program), genuine student intent."
        ),
        "eligibility_criteria": [
            {"label": "Offer of Place (OoP)", "value": "From NZQA-approved educational provider", "notes": "Check NZQA register before paying any deposits"},
            {"label": "Tuition paid (1st year or full)", "value": "Receipt of payment to educational provider", "notes": "Some providers accept partial; most prefer 1 year"},
            {"label": "Proof of funds for living costs", "value": "NZD 17,000/year (full-year programs) OR NZD 1,667/month (shorter programs)", "notes": "Per dependent: additional NZD 7,000-9,000/year"},
            {"label": "English language", "value": "IELTS Academic 5.5 (Diploma) to 6.5 (Master's/PhD) — varies by program + provider", "notes": "PhD programs may accept lower IELTS if previous education in English"},
            {"label": "Acceptance from NZQA-approved provider", "value": "DLI must be Code of Practice-signatory provider", "notes": "Public universities + most polytechnics are auto-approved; PTEs vary"},
            {"label": "Medical (if 12+ month stay from India)", "value": "INZ panel physician exam", "notes": "Mandatory for stay >12 months from India"},
            {"label": "Genuine student intent", "value": "Statement of Purpose + program alignment with career goals", "notes": "Critical — vague intent = refusal"},
            {"label": "Health insurance (mandatory)", "value": "International student insurance covering NZ", "notes": "Most universities arrange via approved providers"},
        ],
        "fees_local_currency_code": "NZD",
        "fees_local_currency_amount": 375,
        "fees_inr_approx": 18750,
        "fees_breakdown": [
            {"component": "Student Visa application fee", "amount": 375, "currency": "NZD"},
            {"component": "Tuition deposit (1st year average Bachelor)", "amount": 28000, "currency": "NZD"},
            {"component": "Living cost proof (12 months)", "amount": 17000, "currency": "NZD"},
            {"component": "International student health insurance", "amount": 600, "currency": "NZD"},
            {"component": "IELTS Academic test", "amount": 16800, "currency": "INR"},
            {"component": "Medical exam (if 12+ month visa)", "amount": 7500, "currency": "INR"},
            {"component": "PCC (India)", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 28,
        "processing_time_days_max": 84,
        "step_by_step": [
            {"step_number": 1, "title": "Choose NZQA-Approved Provider + Apply", "description": "Research universities/polytechnics. Submit application directly to provider with required documents.", "estimated_days": 60, "documents_needed": ["Transcripts", "Degree certificates", "IELTS Academic", "Statement of Purpose"], "tips": ["Universities: Auckland, Otago, Canterbury, Victoria, Massey, Waikato, AUT, Lincoln — all NZQA-approved", "Public providers have higher visa success rates than private", "Apply 8-12 months before intake"]},
            {"step_number": 2, "title": "Receive Offer of Place (OoP)", "description": "Provider issues OoP with program details, tuition fees, start/end dates.", "estimated_days": 21, "documents_needed": [], "tips": ["OoP must specify NZQA approval", "Conditional OoP — fulfill conditions before applying for visa"]},
            {"step_number": 3, "title": "Pay Tuition + Arrange Living Cost Proof", "description": "Pay tuition deposit to provider. Show NZD 17,000 for living costs via bank statement, sponsor letter, or scholarship letter.", "estimated_days": 14, "documents_needed": ["Tuition payment receipt", "6 months bank statements", "Sponsor's ITR/income proof (if applicable)"], "tips": ["Funds shown must be stable 3+ months", "Sudden deposits raise red flags"]},
            {"step_number": 4, "title": "International Student Health Insurance", "description": "Required for all international students. Most providers arrange via approved insurers (Studentsafe, Uni-Care, Southern Cross).", "estimated_days": 7, "documents_needed": ["Insurance certificate"], "tips": ["Cost ~NZD 500-700/year", "Coverage must include medical + repatriation"]},
            {"step_number": 5, "title": "IELTS Academic Test", "description": "Min 5.5 (Diploma) to 6.5 (Master's/PhD). Some PhD programs accept lower if previous English-medium education.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["IELTS Academic, NOT General Training", "PTE Academic also accepted by most NZ universities"]},
            {"step_number": 6, "title": "Medical Exam + PCC", "description": "Medical required if stay 12+ months from India. PCC required if applicant 17+ years.", "estimated_days": 21, "documents_needed": ["eMedical referral", "PCC application"], "tips": ["Medical valid 36 months", "PCC apostilled if requested"]},
            {"step_number": 7, "title": "Submit Student Visa Application Online", "description": "Apply via Immigration Online portal with all docs.", "estimated_days": 7, "documents_needed": ["Passport", "OoP", "Tuition receipt", "Living cost proof", "Health insurance", "IELTS", "Medical", "PCC", "SoP", "Photos"], "tips": ["Apply 3-4 months before intake", "Pay application fee on submission"]},
            {"step_number": 8, "title": "Visa Granted + Travel to NZ", "description": "Receive Student Visa electronically. Travel to NZ. Can enter up to 4 weeks before program start.", "estimated_days": 30, "documents_needed": [], "tips": ["Carry all originals to NZ", "Apply for IRD number if planning to work part-time"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (min program duration + 3 months)", "mandatory": True, "notes": ""},
            {"name": "Offer of Place from NZQA-approved provider", "mandatory": True, "notes": "Includes program, tuition, duration"},
            {"name": "Tuition payment receipt (1st year or full)", "mandatory": True, "notes": ""},
            {"name": "Proof of living cost funds (NZD 17,000+/year)", "mandatory": True, "notes": "Bank statements, sponsor letter + ITR, scholarship"},
            {"name": "International student health insurance certificate", "mandatory": True, "notes": "Covers NZ stay"},
            {"name": "IELTS Academic / PTE Academic result", "mandatory": True, "notes": "Per program requirements"},
            {"name": "Statement of Purpose / Study Plan", "mandatory": True, "notes": "Detailed — program choice + career link"},
            {"name": "Academic transcripts (10th, 12th, Bachelor's if applicable)", "mandatory": True, "notes": ""},
            {"name": "Degree certificates (if previous education)", "mandatory": True, "notes": ""},
            {"name": "Medical exam (12+ month stay from India)", "mandatory": False, "notes": "INZ panel physician"},
            {"name": "Police Clearance Certificate (17+ years)", "mandatory": True, "notes": "India PSK"},
            {"name": "Photos (INZ specifications)", "mandatory": True, "notes": ""},
            {"name": "Sponsor's tax returns (if funds via sponsor)", "mandatory": False, "notes": "Last 2-3 years ITR"},
            {"name": "Custodian declaration (if minor)", "mandatory": False, "notes": "Students under 18"},
        ],
        "common_rejection_reasons": [
            "Insufficient or unstable living cost funds",
            "Provider not on NZQA-approved list",
            "Statement of Purpose generic / doesn't justify program choice",
            "Course choice doesn't align with previous education or career",
            "Genuine student intent doubts — INZ believes immigration motive",
            "Prior visa refusals (any country) undeclared",
            "Inadequate English (below program threshold)",
            "Misrepresentation in academic documents or sponsor info",
        ],
        "success_tips": [
            "Choose Level 7+ programs (Bachelor's, Master's, PhD) — opens PSWV pathway",
            "Pay 1 year tuition + show full living costs = strongest financial proof",
            "Write a UNIQUE Statement of Purpose tied to your career trajectory",
            "Choose public universities/polytechnics over private PTEs for higher approval",
            "Show clear post-graduation plan (return to home OR PSWV intent)",
            "If post-graduation work + PR is your goal, choose Level 7+ in NZ skill shortage area",
            "PhD students get unlimited work rights — strong long-term path",
            "Apply 4 months before intake start to allow buffer for delays",
        ],
        "faqs": [
            {"q": "Can I work on Student Visa?", "a": "Up to 20 hours/week during term (Level 7+ programs); full-time during scheduled breaks (summer, winter). PhD + research Master's students can work unlimited hours."},
            {"q": "What is Post-Study Work Visa (PSWV)?", "a": "Visa for Level 7+ graduates from NZ providers. Duration: 1-3 years based on qualification level and study location (regional locations get longer PSWV). Open work rights."},
            {"q": "Can my partner come with me?", "a": "Yes — partner can apply for Partner of Student Work Visa (open work rights) if you're studying Level 7+ at Bachelor's Honours or above. Children can attend NZ schools."},
            {"q": "Difference between NZQA-approved and Code of Practice signatory?", "a": "NZQA approval = quality assurance. Code of Practice signatory = additional commitment to international student welfare. Both required for student visa eligibility."},
            {"q": "How much does NZ study cost overall?", "a": "Tuition: NZD 25,000-50,000/year (Bachelor's), NZD 28,000-50,000/year (Master's), NZD 6,500-10,000/year (PhD — many fully funded). Living costs: NZD 17,000/year minimum. Total ≈ ₹25-45 lakh/year all-in."},
            {"q": "Can I extend my visa?", "a": "Yes — apply for extension before current visa expires. Same documents + updated proof of funds + continued enrollment."},
        ],
        "official_url": "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/fee-paying-student-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/fee-paying-student-visa",
            "https://www.immigration.govt.nz/new-zealand-visas/preparing-a-visa-application/study-in-nz",
            "https://www.nzqa.govt.nz/providers-partners/approval-accreditation-and-registration/",
            "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/post-study-work-visa",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immigration.govt.nz on 2026-02-27. Living cost threshold NZD 17,000/year for 36+ month programs per current policy.",
    },

    # ── 5. Partner of NZ Resident/Citizen — Resident Visa ─────────────────────
    {
        "country_code": "NZ",
        "country_name": "New Zealand",
        "subclass_id": "Partner-Resident",
        "subclass_name": "Partner of a New Zealander — Resident Visa",
        "service_type": "partner",
        "category": "immigration",
        "description": (
            "The Partner of a New Zealander Resident Visa is for spouses, civil union partners, and de facto "
            "partners (including same-sex partners) of NZ citizens or residents. There are two main streams: "
            "**Partnership-based Resident Visa** (direct PR if relationship has been ongoing 12+ months in a "
            "shared household) and **Partnership-based Work Visa** (open work visa to live in NZ while building "
            "the 12 months of cohabitation evidence).\n\n"
            "Key concept: **Partnership must be GENUINE AND STABLE** with strong evidence of mutual commitment, "
            "shared finances, shared social life, and intent to continue living together. Arranged marriages "
            "where couple hasn't yet built shared life history may need to use Work Visa first to accumulate "
            "evidence, then transition to Resident Visa."
        ),
        "eligibility_summary": (
            "Sponsoring partner must be NZ citizen or resident (in NZ for 184+ days in last 12 months). "
            "Genuine and stable partnership, ideally 12+ months cohabitation. Sponsor income/support capability. "
            "Worker meets standard character + health requirements. IELTS not always required but recommended."
        ),
        "eligibility_criteria": [
            {"label": "Sponsoring partner status", "value": "Must be NZ citizen or NZ resident", "notes": "Resident sponsor must be in NZ 184+ days in past 12 months OR have valid residence and demonstrated intent to remain"},
            {"label": "Genuine and stable relationship", "value": "Marriage/civil union/de facto with 12+ months cohabitation evidence", "notes": "If less than 12 months — Work Visa first, then Resident later"},
            {"label": "Mutual commitment evidence", "value": "Shared finances, social life, household, communication history", "notes": "Photos, joint accounts, joint lease, family/friends statements"},
            {"label": "Living together", "value": "Currently living together OR demonstrable plan to do so", "notes": "If long-distance — Work Visa permits joining"},
            {"label": "Age", "value": "Both 18+", "notes": "Under 18 with strict conditions"},
            {"label": "Sponsor's support capability", "value": "Sponsor commits to supporting partner; no specific income threshold but reasonable means expected", "notes": "Sponsor signs Sponsorship Form"},
            {"label": "Health + Character", "value": "Standard INZ requirements", "notes": "Medical (if 12+ month stay), PCCs"},
            {"label": "English (recommended)", "value": "IELTS 4.0 useful, not always mandatory for partner visa", "notes": "Demonstrates ability to settle"},
        ],
        "fees_local_currency_code": "NZD",
        "fees_local_currency_amount": 3070,
        "fees_inr_approx": 153500,
        "fees_breakdown": [
            {"component": "Partner Resident Visa application", "amount": 3070, "currency": "NZD"},
            {"component": "Dependent child (each)", "amount": 530, "currency": "NZD"},
            {"component": "Migrant Levy", "amount": 280, "currency": "NZD"},
            {"component": "Medical exam (12+ month stay)", "amount": 7500, "currency": "INR"},
            {"component": "PCCs", "amount": 1000, "currency": "INR"},
            {"component": "Translation of marriage cert / evidence (if needed)", "amount": 3000, "currency": "INR"},
        ],
        "processing_time_days_min": 180,
        "processing_time_days_max": 450,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Sponsoring Partner's Eligibility", "description": "Sponsor must be NZ citizen or resident with 184+ days in NZ in past 12 months. Verify status via sponsor's NZ documents.", "estimated_days": 7, "documents_needed": ["Sponsor's NZ passport / Resident Visa label", "Proof of NZ residency days"], "tips": ["Sponsor must not have sponsored 2+ partners in last 5 years", "Sponsor must not have any active sponsorship of another partner"]},
            {"step_number": 2, "title": "Build Relationship Evidence (12+ months cohabitation ideal)", "description": "Gather extensive evidence of genuine + stable partnership: photos across time, joint bank accounts, lease/property docs, communications, witness statements.", "estimated_days": 90, "documents_needed": ["Marriage/civil union certificate", "Photos (dated, varied locations + occasions)", "Joint bank account statements", "Joint lease/property docs", "Travel together itineraries", "Communication logs (WhatsApp/email screenshots)"], "tips": ["Build a STORY arc across timeline showing relationship growth", "Statutory declarations from family/friends who know couple", "Avoid only formal documents — include daily life"]},
            {"step_number": 3, "title": "Sponsor Form + Statement", "description": "Sponsor completes Sponsorship form (INZ 1146) committing to support, declaring marital status, prior sponsorships. Provides ID + status proof.", "estimated_days": 7, "documents_needed": ["Sponsor INZ 1146 form", "Sponsor passport/Resident Visa", "Sponsor address proof"], "tips": ["Sponsor signs declaration of support", "Sponsor must not have outstanding INZ debts"]},
            {"step_number": 4, "title": "Worker's Documents", "description": "Worker gathers personal documents: passport, birth certificate, PCCs, medical exam, photos.", "estimated_days": 30, "documents_needed": ["Passport", "Birth certificate", "Medical exam", "PCCs"], "tips": ["PCCs from each country lived 12+ months in past 10 years"]},
            {"step_number": 5, "title": "Submit Partner Resident Visa Application", "description": "Apply via Immigration Online portal. Upload all relationship evidence + sponsor + worker docs.", "estimated_days": 14, "documents_needed": ["All evidence + sponsor + worker docs", "Application fee + Migrant Levy"], "tips": ["Relationship evidence section is the heart of the application", "INZ scrutinises authenticity carefully"]},
            {"step_number": 6, "title": "INZ Interview (sometimes)", "description": "INZ may invite couple for interview to verify relationship genuineness. Common for newer relationships.", "estimated_days": 60, "documents_needed": ["Bring all originals to interview"], "tips": ["Be honest + consistent", "Each partner interviewed separately"]},
            {"step_number": 7, "title": "INZ Decision + Section 27 (if needed)", "description": "INZ reviews. May issue Section 27 request for additional evidence. Processing 8-18 months typical.", "estimated_days": 270, "documents_needed": [], "tips": ["Respond to S27 within 14 days", "Provide additional evidence proactively if relationship has evolved"]},
            {"step_number": 8, "title": "Resident Visa Granted", "description": "Receive Resident Visa label. Enter NZ before first-entry date. After 2 years, eligible for Permanent Resident Visa.", "estimated_days": 30, "documents_needed": [], "tips": ["Live with sponsor on arrival", "Apply for IRD + bank account"]},
        ],
        "document_checklist": [
            {"name": "Worker's passport (all family members)", "mandatory": True, "notes": ""},
            {"name": "Sponsor's NZ passport / Resident Visa label", "mandatory": True, "notes": ""},
            {"name": "Sponsor INZ 1146 Sponsorship Form", "mandatory": True, "notes": "Signed by sponsor"},
            {"name": "Marriage / Civil Union / De facto declaration certificate", "mandatory": True, "notes": "Apostilled if foreign"},
            {"name": "Joint bank account statements (6+ months)", "mandatory": True, "notes": "Strong evidence of shared finances"},
            {"name": "Joint lease / property ownership documents", "mandatory": True, "notes": "Shared household evidence"},
            {"name": "Photos (dated, varied occasions, with family + friends)", "mandatory": True, "notes": "Cover entire relationship timeline"},
            {"name": "Communication logs (WhatsApp/email screenshots, calls)", "mandatory": True, "notes": "Especially for long-distance phases"},
            {"name": "Travel together itineraries / boarding passes", "mandatory": False, "notes": ""},
            {"name": "Statutory declarations from family/friends (2-4)", "mandatory": True, "notes": "Witness statements supporting genuineness"},
            {"name": "Sponsor's income proof / tax records (last 2 years)", "mandatory": False, "notes": "Demonstrates support capability"},
            {"name": "Children's birth certificates (if applicable)", "mandatory": True, "notes": "Establishing parent-child relationship"},
            {"name": "Medical exam (12+ month stay)", "mandatory": True, "notes": "INZ panel physician"},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": "Each country lived 12+ months past 10 years"},
            {"name": "Worker's birth certificate", "mandatory": True, "notes": ""},
            {"name": "Translation of non-English documents", "mandatory": False, "notes": "Certified translator"},
        ],
        "common_rejection_reasons": [
            "Relationship not 'genuine and stable' — INZ doubts authenticity",
            "Insufficient cohabitation evidence (less than 12 months OR thin evidence)",
            "Sponsor doesn't meet eligibility (not in NZ 184+ days, multiple prior sponsorships)",
            "Inconsistencies between partners' statements at interview",
            "Misrepresentation of relationship origin or current status",
            "Sponsor has outstanding INZ debts or compliance issues",
            "Health or character inadmissibility",
            "Cultural/family arrangement raising 'arranged for visa' suspicion (more scrutiny for arranged marriages)",
        ],
        "success_tips": [
            "Build evidence ACROSS timeline — early relationship, daily life, recent",
            "Include candid photos with family + friends, not just couple selfies",
            "Joint accounts with consistent activity > one-time deposits",
            "If newly married — consider Partnership Work Visa first to accumulate evidence",
            "Statutory declarations from 2-4 people who know couple well are very strong",
            "Maintain communication logs across distance (WhatsApp/Skype/Zoom)",
            "Sponsor should write a detailed statement of how relationship developed",
            "Avoid only formal/legal docs — INZ wants daily life evidence too",
        ],
        "faqs": [
            {"q": "Do I need to be married for partner visa?", "a": "No — civil unions and de facto partnerships (same-sex or different-sex) qualify equally. Key is genuine + stable relationship with 12+ months cohabitation evidence."},
            {"q": "What if we've been married less than 12 months?", "a": "Apply for Partnership Work Visa first to live in NZ. Accumulate 12 months cohabitation evidence. Then apply for Resident Visa from inside NZ."},
            {"q": "Can my sponsor be in NZ on a temporary visa?", "a": "No — sponsor must be NZ citizen or NZ resident (Resident Visa). Temporary visa holders cannot sponsor partners for residence."},
            {"q": "What about arranged marriages?", "a": "INZ assesses genuineness equally — but arranged marriages face more scrutiny. Build strong post-marriage cohabitation + communication evidence. Photos with extended family help."},
            {"q": "Can children come with me?", "a": "Yes — dependent children of either partner can be included on the Resident Visa application. Same INZ fees as adults."},
            {"q": "Difference between Partner Resident Visa and Work Visa?", "a": "Resident Visa = direct PR (need 12+ months cohabitation evidence). Work Visa = open work rights while you build the evidence; convert to Resident later."},
        ],
        "official_url": "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/partner-of-a-new-zealander-resident-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/partner-of-a-new-zealander-resident-visa",
            "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/partner-of-a-new-zealander-work-visa",
            "https://www.immigration.govt.nz/new-zealand-visas/preparing-a-visa-application/your-partner/about-partner-visas",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immigration.govt.nz on 2026-02-27. Partnership evidence requirements per current INZ Operational Manual.",
    },

    # ── 6. Working Holiday Visa ────────────────────────────────────────────────
    {
        "country_code": "NZ",
        "country_name": "New Zealand",
        "subclass_id": "Working-Holiday",
        "subclass_name": "Working Holiday Visa",
        "service_type": "visitor",
        "category": "immigration",
        "description": (
            "The Working Holiday Visa allows young people (typically 18-30 or 18-35 depending on country) "
            "to live, travel, and work in New Zealand for up to 12 months (some countries 23 months). It's a "
            "bilateral scheme where NZ has reciprocal arrangements with about 45 partner countries.\n\n"
            "**IMPORTANT for Indian applicants:** India is **NOT currently a Working Holiday Scheme partner "
            "country with NZ**. Indian nationals cannot apply for this visa. Eligible nationals include: UK, "
            "Germany, France, Japan, USA, Canada, Ireland, Netherlands, Norway, Sweden, Singapore, South Korea, "
            "Chile, Argentina, Brazil, Uruguay, Mexico, and others. This workflow is documented for clients "
            "with dual nationality or eligible passport holders."
        ),
        "eligibility_summary": (
            "Citizen of a NZ Working Holiday Scheme partner country (India NOT included as of 2026), aged "
            "18-30 (or 18-35 for some countries), no dependent children accompanying, sufficient funds "
            "(typically NZD 4,200 + return ticket evidence), valid passport, no prior NZ Working Holiday Visa, "
            "good health and character."
        ),
        "eligibility_criteria": [
            {"label": "Citizenship", "value": "Citizen of a partner country (UK, Germany, France, Japan, USA, Canada, etc. — India NOT included)", "notes": "Full list at immigration.govt.nz/working-holiday"},
            {"label": "Age", "value": "18-30 years (or 18-35 for some countries: UK, Canada, Czech Republic, etc.)", "notes": "Apply BEFORE turning the upper age limit; visa can extend past that"},
            {"label": "Funds", "value": "NZD 4,200 minimum + return ticket evidence OR NZD 4,200 + NZD 2,500 for return", "notes": "Bank statements showing personal funds; sponsorship not accepted"},
            {"label": "Valid passport", "value": "Min 3 months beyond intended stay", "notes": ""},
            {"label": "No dependent children accompanying", "value": "Children cannot be on Working Holiday Visa", "notes": "Children must apply separately or stay home"},
            {"label": "First-time", "value": "Cannot have held a NZ Working Holiday Visa previously", "notes": "Once-in-a-lifetime opportunity for most countries"},
            {"label": "Health + Character", "value": "Standard checks; medical if working in healthcare/agriculture/childcare", "notes": ""},
            {"label": "No marketing services as primary purpose", "value": "Visa is for holiday + incidental work — not specific job arrangements", "notes": ""},
        ],
        "fees_local_currency_code": "NZD",
        "fees_local_currency_amount": 280,
        "fees_inr_approx": 14000,
        "fees_breakdown": [
            {"component": "Working Holiday Visa application fee", "amount": 280, "currency": "NZD"},
            {"component": "Immigration Levy (if applicable)", "amount": 55, "currency": "NZD"},
            {"component": "Funds proof required (NZD 4,200 + return)", "amount": 4200, "currency": "NZD"},
            {"component": "Medical exam (if healthcare/agriculture role anticipated)", "amount": 7500, "currency": "INR"},
        ],
        "processing_time_days_min": 7,
        "processing_time_days_max": 30,
        "step_by_step": [
            {"step_number": 1, "title": "Verify Country Eligibility + Quota", "description": "Confirm your country is a NZ Working Holiday Scheme partner. Check current annual quota — some have caps (UK, Germany unlimited; others may have quotas).", "estimated_days": 1, "documents_needed": [], "tips": ["India is NOT a partner — Indian-only passport holders cannot apply", "Check immigration.govt.nz for current quota status"]},
            {"step_number": 2, "title": "Demonstrate Sufficient Funds", "description": "Show NZD 4,200 (or NZD 4,200 + return ticket OR NZD 4,200 + NZD 2,500 for return) via bank statements in your own name.", "estimated_days": 7, "documents_needed": ["3 months bank statements", "Return ticket booking (recommended)"], "tips": ["Funds must be personal — gifts/loans not accepted", "Stable balance over 3 months > sudden lump sum"]},
            {"step_number": 3, "title": "Take Medical Exam (if anticipated)", "description": "Required only if working in healthcare/agriculture/childcare. Most Working Holiday makers don't need it.", "estimated_days": 14, "documents_needed": ["eMedical referral if needed"], "tips": ["Skip if not in those sectors"]},
            {"step_number": 4, "title": "Online Application", "description": "Apply via Immigration Online portal. Pay application fee. Upload passport scan, bank statements, photo.", "estimated_days": 3, "documents_needed": ["Passport scan", "Bank statements", "Photo", "Return ticket (if applicable)"], "tips": ["Fast online process — typically 7-14 days approval", "No biometrics required for most partner countries"]},
            {"step_number": 5, "title": "Visa Approval", "description": "Receive electronic Working Holiday Visa. Valid for 12 months from arrival (some countries 23 months).", "estimated_days": 14, "documents_needed": [], "tips": ["Carry approval email to airport"]},
            {"step_number": 6, "title": "Travel to NZ + Activation", "description": "Travel to NZ within visa validity period (typically 12 months from issue date). Visa activates on arrival.", "estimated_days": 30, "documents_needed": ["Passport", "Funds proof at POE"], "tips": ["Customs officer may ask for funds + return plan", "Carry copy of visa approval"]},
            {"step_number": 7, "title": "Work + Travel in NZ", "description": "Work for any employer (subject to standard NZ employment law), travel freely. Some restrictions on permanent positions (>12 months with same employer).", "estimated_days": 365, "documents_needed": ["IRD number application post-arrival"], "tips": ["Apply for IRD number to work legally", "Common Working Holiday jobs: hospitality, retail, farm work, ski resorts, tourism", "Some Working Holiday makers extend to AEWV if employer sponsors"]},
            {"step_number": 8, "title": "Optional Extensions / Conversions", "description": "Working Holiday Visa generally not extendable. UK + Canada eligible for 12-month extension on Working Holiday. May convert to AEWV/Student Visa with appropriate offer.", "estimated_days": 30, "documents_needed": [], "tips": ["Plan early if extending or converting", "AEWV pathway requires accredited employer + Job Check"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (partner country citizenship)", "mandatory": True, "notes": "India NOT eligible"},
            {"name": "Photo (INZ specifications)", "mandatory": True, "notes": ""},
            {"name": "Bank statements showing NZD 4,200+", "mandatory": True, "notes": "3 months minimum"},
            {"name": "Return flight booking (recommended)", "mandatory": False, "notes": "Alternative: extra NZD 2,500 funds"},
            {"name": "Medical exam (if healthcare/agriculture/childcare anticipated)", "mandatory": False, "notes": "Most don't need"},
            {"name": "Police Clearance Certificate (if requested)", "mandatory": False, "notes": "Usually not required for Working Holiday"},
            {"name": "Travel insurance certificate (recommended)", "mandatory": False, "notes": "Not mandatory but strongly advised"},
            {"name": "Itinerary / travel plan (informal)", "mandatory": False, "notes": "Helps demonstrate genuine holiday intent"},
            {"name": "Travel CV / list of past Working Holidays in other countries", "mandatory": False, "notes": "If applicable"},
            {"name": "Application form (online portal completes this)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Citizenship not on Working Holiday partner country list (India is NOT — common refusal cause for Indian-only passport holders)",
            "Insufficient funds (less than NZD 4,200 + return)",
            "Prior NZ Working Holiday Visa held (once-in-lifetime restriction)",
            "Age above eligible range at time of application",
            "Funds sponsored by parents (must be personal funds in own name)",
            "Outstanding debts to NZ government from prior visits",
            "Health/character concerns",
        ],
        "success_tips": [
            "For Indian-only passport holders — consider Student Visa or AEWV pathway instead (India NOT partner country)",
            "Maintain NZD 4,200+ stable in bank account for 3+ months before applying",
            "Book a one-way ticket only if showing NZD 2,500 extra funds for return",
            "Apply BEFORE turning upper age limit — visa can extend past birthday once issued",
            "Plan flexible itinerary — INZ wants to see holiday intent, not just work plan",
            "Once in NZ, network for AEWV conversion via accredited employer",
            "UK + Canada nationals: take advantage of 12-month extension after first 12 months",
            "Get IRD number first thing after arrival — required for legal work",
        ],
        "faqs": [
            {"q": "Can Indian nationals apply for NZ Working Holiday?", "a": "NO — India is NOT a partner country in NZ's Working Holiday Scheme as of 2026. Eligible nationals include UK, Germany, France, USA, Canada, Japan, and ~40 others. Dual nationals with eligible passport can apply."},
            {"q": "How long can I stay on Working Holiday Visa?", "a": "12 months for most countries; some (UK, Canada, Czech Republic, France, Germany, Ireland) get 23 months or 12 + 12 month extensions."},
            {"q": "Can I work full-time on this visa?", "a": "Yes — but restrictions on permanent positions with same employer (12 months max). Can work multiple jobs. Cannot study more than 6 months."},
            {"q": "Can I bring children?", "a": "No — dependent children cannot be on a Working Holiday Visa. They'd need separate visas (Student Visa, Visitor Visa) and must be supported separately."},
            {"q": "Can I convert to PR from Working Holiday?", "a": "Not directly. But Working Holiday makers often find accredited employer + sponsor for AEWV → Green List/SMC pathway to PR."},
            {"q": "What if I overstay?", "a": "Overstaying creates an immigration violation. May be banned from future NZ visas. Always extend or transition before visa expires."},
        ],
        "official_url": "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/working-holiday-visa-for-citizens-of-countries-other-than-the-uk",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/new-zealand-visas/preparing-a-visa-application/working-holiday-visas",
            "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/working-holiday-visa-for-citizens-of-countries-other-than-the-uk",
            "https://www.immigration.govt.nz/new-zealand-visas/options/work",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against immigration.govt.nz on 2026-02-27. CRITICAL NOTE: India is NOT a Working Holiday Scheme partner country with NZ — Indian-only passport holders cannot apply. Documented for clients with eligible second nationality or general consultancy reference.",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# UNITED KINGDOM (UK) — 6 verified subclasses
# Source: gov.uk + UKVI · Feb 2026 fee schedule · FX: 1 GBP ≈ 105 INR
# ──────────────────────────────────────────────────────────────────────────────
UNITED_KINGDOM_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. Skilled Worker Visa ────────────────────────────────────────────────
    {
        "country_code": "UK",
        "country_name": "United Kingdom",
        "subclass_id": "Skilled-Worker",
        "subclass_name": "Skilled Worker Visa (Post-Brexit Tier 2 Replacement)",
        "service_type": "work",
        "category": "immigration",
        "description": (
            "The Skilled Worker Visa is the UK's primary employer-sponsored work visa, replacing the old "
            "Tier 2 (General) Visa post-Brexit. It enables non-UK nationals (including Indians) to work for "
            "a UK-licensed sponsor employer in an eligible skilled occupation. It is the standard pathway "
            "to long-term settlement (ILR) after 5 years.\n\n"
            "Following the April 2024 reform, the minimum salary threshold was raised significantly to "
            "£38,700/year (or going-rate for the specific occupation, whichever is higher). Eligible "
            "occupations span RQF Level 3+ roles across healthcare, IT, engineering, finance, education, "
            "and skilled trades. The visa is sponsor-specific — workers cannot switch employers without "
            "new Certificate of Sponsorship (CoS) and visa application. Visa duration: up to 5 years per "
            "application, with extensions and ILR route built in."
        ),
        "eligibility_summary": (
            "Job offer from a UK-licensed sponsor with valid Certificate of Sponsorship (CoS), role at "
            "RQF Level 3+ in eligible occupation code, salary ≥£38,700/year (post-April 2024) OR going "
            "rate for occupation, English at B1 level (CEFR), maintenance funds (or sponsor certifies)."
        ),
        "eligibility_criteria": [
            {"label": "Licensed sponsor + CoS", "value": "Valid Certificate of Sponsorship from a UK-licensed sponsor", "notes": "Sponsor must hold a 'Worker' sponsor licence; CoS valid 3 months from assignment"},
            {"label": "Eligible occupation", "value": "Role on the UK Skilled Occupation List at RQF Level 3+", "notes": "SOC 2020 codes; new shortage occupation list (Immigration Salary List) replaced old SOL"},
            {"label": "Minimum salary", "value": "£38,700/year OR occupation going-rate, whichever is higher (post-April 2024)", "notes": "Some exceptions: new entrants, STEM PhD holders, Immigration Salary List = 80%, healthcare = £23,200 minimum"},
            {"label": "English language", "value": "CEFR B1 (intermediate) in all 4 skills — reading, writing, listening, speaking", "notes": "Approved tests: IELTS for UKVI (4.0+ each), Trinity ISE, PTE Academic UKVI, OET; or recognised qualification taught in English"},
            {"label": "Maintenance funds", "value": "£1,270 held in bank account for 28+ consecutive days", "notes": "OR sponsor certifies maintenance on CoS (A-rated sponsors)"},
            {"label": "TB test certificate (India)", "value": "Required for visa applications from India", "notes": "From a UKVI-approved clinic in India (IOM)"},
            {"label": "Genuine intent", "value": "Genuine work offer + intent to fulfil the role", "notes": "UKVI may interview"},
            {"label": "No criminal disqualification", "value": "Past 12-month+ prison sentences = bar; some other criminality flags", "notes": "Standard criminality + immigration history check"},
        ],
        "fees_local_currency_code": "GBP",
        "fees_local_currency_amount": 6694,
        "fees_inr_approx": 702870,
        "fees_breakdown": [
            {"component": "Skilled Worker Visa application — up to 3 years (out of UK)", "amount": 719, "currency": "GBP"},
            {"component": "Skilled Worker Visa application — over 3 years (out of UK)", "amount": 1500, "currency": "GBP"},
            {"component": "Immigration Health Surcharge (IHS) — £1,035/year × 5 years", "amount": 5175, "currency": "GBP"},
            {"component": "Priority Service (next working day decision)", "amount": 500, "currency": "GBP"},
            {"component": "Super-Priority Service (same/next working day)", "amount": 1000, "currency": "GBP"},
            {"component": "Biometric Enrolment fee (UKVI partner in India)", "amount": 19, "currency": "GBP"},
            {"component": "TB test (IOM India)", "amount": 6500, "currency": "INR"},
            {"component": "English test (IELTS UKVI)", "amount": 18800, "currency": "INR"},
            {"component": "Translation fees (if non-English docs)", "amount": 5000, "currency": "INR"},
        ],
        "processing_time_days_min": 15,
        "processing_time_days_max": 60,
        "step_by_step": [
            {"step_number": 1, "title": "Secure Job Offer from Licensed Sponsor", "description": "Find a UK employer with a valid sponsor licence (Worker tier). Negotiate offer at or above £38,700/year (or going rate). Employer assigns Certificate of Sponsorship (CoS).", "estimated_days": 90, "documents_needed": ["Job offer letter", "Employment contract"], "tips": ["Verify sponsor licence on UKVI's public Sponsor Register before accepting offer", "Going-rate for SOC code may exceed £38,700 — check at gov.uk/government/publications/skilled-worker-visa-going-rates", "CoS reference is the visa application's anchor"]},
            {"step_number": 2, "title": "Receive Certificate of Sponsorship", "description": "Employer assigns a CoS in the UKVI system. You receive a unique reference number (CoS number). Valid 3 months from assignment.", "estimated_days": 14, "documents_needed": ["CoS reference number"], "tips": ["Apply for visa within 3 months of CoS issue", "Defined CoS (out-of-country) vs Undefined CoS (in-country switch) — confirm correct type"]},
            {"step_number": 3, "title": "English Language Test (if no exemption)", "description": "Take an approved test at CEFR B1 minimum: IELTS UKVI (4.0 each band), Trinity ISE, PTE Academic UKVI, OET (healthcare). Or rely on degree taught in English.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["UKVI version of IELTS is mandatory — not General Training or Academic", "Indian university degrees taught in English qualify with NARIC equivalency"]},
            {"step_number": 4, "title": "TB Test (IOM India)", "description": "Visit a UKVI-approved TB testing clinic (IOM in Delhi, Mumbai, Chennai). Test valid 6 months.", "estimated_days": 7, "documents_needed": ["Passport"], "tips": ["Mandatory for India applicants staying 6+ months in UK", "Get appointment in advance — IOM clinics get booked up"]},
            {"step_number": 5, "title": "Maintenance Funds Proof", "description": "Hold £1,270 in your bank account for 28+ consecutive days within 31 days of application. OR sponsor certifies maintenance on CoS (A-rated sponsors only).", "estimated_days": 28, "documents_needed": ["Bank statements (28+ days)"], "tips": ["Funds must be in your name only", "Joint accounts allowed if both names on it for full 28 days", "Don't dip below £1,270 even once during 28 days"]},
            {"step_number": 6, "title": "Submit Online Application", "description": "Apply at gov.uk via the Skilled Worker route. Pay application fee + IHS. Upload documents.", "estimated_days": 3, "documents_needed": ["CoS reference", "Passport", "English test", "TB test", "Maintenance proof", "Qualifications", "Application form"], "tips": ["Choose Priority/Super-Priority service for faster decision", "Pay IHS in full upfront (5 years × £1,035 = £5,175)"]},
            {"step_number": 7, "title": "Biometric Enrolment", "description": "Visit UKVI partner (VFS in India). Submit fingerprints + photo. Upload documents.", "estimated_days": 14, "documents_needed": ["Application reference", "Passport"], "tips": ["Book biometric appointment after submitting application", "Can do priority biometric for faster processing"]},
            {"step_number": 8, "title": "Decision + Travel to UK", "description": "Receive decision (3 weeks standard, 5 days priority, 24 hr super-priority). On approval, get visa vignette in passport. Travel to UK before vignette expires (90 days), collect BRP within 10 days of arrival.", "estimated_days": 21, "documents_needed": ["Vignette in passport"], "tips": ["BRP collection within 10 days of arrival is critical", "Bring CoS reference + employment contract to airport"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (with min 1 blank page)", "mandatory": True, "notes": ""},
            {"name": "Certificate of Sponsorship (CoS) reference number", "mandatory": True, "notes": "From licensed sponsor"},
            {"name": "Job offer letter + employment contract", "mandatory": True, "notes": "On company letterhead; specifies salary, hours, role, SOC code"},
            {"name": "English language test result (IELTS UKVI / PTE UKVI / OET / Trinity ISE)", "mandatory": True, "notes": "Min CEFR B1 in all skills"},
            {"name": "Tuberculosis (TB) test certificate (from IOM India)", "mandatory": True, "notes": "Valid 6 months"},
            {"name": "Maintenance funds — bank statements (28 days)", "mandatory": True, "notes": "£1,270 minimum; OR sponsor A-rated certifies on CoS"},
            {"name": "Educational qualifications (degree, transcripts)", "mandatory": False, "notes": "Required if claiming skilled occupation via qualification"},
            {"name": "UK NARIC / Ecctis Statement of Comparability (if non-UK degree)", "mandatory": False, "notes": "For qualification-based skilled status claims"},
            {"name": "PhD certificate (if claiming PhD bonus for tradable points)", "mandatory": False, "notes": "STEM PhD reduces salary threshold"},
            {"name": "Police certificate (specific sectors: education, healthcare, social services)", "mandatory": False, "notes": "From each country lived 12+ months in past 10 years"},
            {"name": "Marriage cert + children's birth certs (if dependents applying together)", "mandatory": False, "notes": ""},
            {"name": "Biometric Residence Permit (BRP) collection details", "mandatory": True, "notes": "Issued post-arrival"},
            {"name": "Recent passport-style photos (UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "Application form printout (from gov.uk)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Salary below £38,700 OR occupation going-rate (whichever is higher)",
            "Sponsor licence not valid or sponsor on UKVI 'A-rated' downgrade list",
            "CoS expired (3-month validity from issue)",
            "English test below CEFR B1 on any one skill",
            "Maintenance funds dipped below £1,270 during 28-day period",
            "Occupation code not at RQF Level 3+ or not on Skilled Occupation List",
            "Genuine vacancy concerns — UKVI suspects role created just for visa sponsorship",
            "TB test missing or from non-UKVI-approved clinic",
        ],
        "success_tips": [
            "Verify sponsor licence + A-rating BEFORE accepting offer",
            "Check occupation going-rate against your offered salary — going-rate often exceeds £38,700",
            "Get sponsor to certify maintenance on CoS if you can — saves the 28-day bank requirement",
            "Take IELTS UKVI early — score above B1 minimum gives buffer",
            "Apply within first month of CoS issue — leaves buffer if any document issue",
            "Use Priority Service (£500) if joining date is tight — 5-day decision",
            "Bundle BRP collection details with hotel booking near collection centre",
            "Keep digital + hard copies of every document submitted",
        ],
        "faqs": [
            {"q": "What's the difference between Skilled Worker and old Tier 2 General?", "a": "Skilled Worker replaced Tier 2 General in Dec 2020 post-Brexit. Key changes: occupation list expanded to RQF Level 3 (was RQF Level 6), Resident Labour Market Test scrapped, broader sectors eligible. Salary thresholds raised significantly in April 2024."},
            {"q": "Can I switch employers on Skilled Worker?", "a": "No — visa is sponsor-specific. To switch, you need new CoS from new sponsor and new visa application (in-country switch possible)."},
            {"q": "Can my family join me?", "a": "Yes — spouse/partner and children under 18 can apply as dependants. Same IHS, separate application fees. Spouse can work in UK without restriction."},
            {"q": "When can I apply for ILR?", "a": "After 5 continuous years on Skilled Worker (or combined eligible routes). Need: continuous residence, salary still meets threshold at ILR application, KOL (Knowledge of Life in UK) test + English B1 maintained."},
            {"q": "What is IHS and can I get a refund?", "a": "Immigration Health Surcharge: £1,035/year, paid upfront for full visa length. Gives access to NHS. Refunded if visa rejected. Not refunded if visa granted but you leave early."},
            {"q": "What's the going rate?", "a": "Each SOC occupation has a minimum 'going rate' published by UKVI. You must be paid the higher of £38,700 OR your SOC's going rate. Some SOCs (e.g. senior medical) exceed £60,000."},
        ],
        "official_url": "https://www.gov.uk/skilled-worker-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/",
        "source_urls": [
            "https://www.gov.uk/skilled-worker-visa",
            "https://www.gov.uk/government/publications/skilled-worker-visa-going-rates-for-eligible-occupations",
            "https://www.gov.uk/government/publications/immigration-rules/immigration-rules-appendix-skilled-worker",
            "https://www.gov.uk/government/publications/skilled-worker-visa-eligible-occupations-and-codes",
            "https://www.gov.uk/healthcare-immigration-application/who-needs-pay",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against gov.uk on 2026-02-27. Salary threshold £38,700 per April 2024 reform. IHS £1,035/year per current rate.",
    },

    # ── 2. Health and Care Worker Visa ────────────────────────────────────────
    {
        "country_code": "UK",
        "country_name": "United Kingdom",
        "subclass_id": "Health-Care-Worker",
        "subclass_name": "Health and Care Worker Visa (Skilled Worker subset)",
        "service_type": "work",
        "category": "immigration",
        "description": (
            "The Health and Care Worker Visa is a special category within the Skilled Worker route, "
            "designed for qualified medical professionals coming to work for the NHS, NHS suppliers, "
            "or eligible care providers. It offers two huge benefits over the standard Skilled Worker "
            "Visa: (1) **Significantly reduced application fees** (£304 instead of £719 for 3-year visas), "
            "and (2) **Exemption from the Immigration Health Surcharge (IHS)** — saving £5,175+ over a "
            "5-year visa.\n\n"
            "Eligible occupations include doctors (NHS or eligible private), nurses, midwives, paramedics, "
            "social care workers (added Aug 2023, though some restrictions apply post-Mar 2024), pharmacists, "
            "psychologists, and allied health professionals. Sponsor must be CQC-regulated or NHS-affiliated. "
            "Note: From April 2024 the salary threshold for healthcare roles was set at £23,200 minimum "
            "(lower than the £38,700 general Skilled Worker threshold), making this route accessible."
        ),
        "eligibility_summary": (
            "Job offer from NHS or CQC-regulated/NHS-affiliated employer with valid CoS, eligible "
            "healthcare occupation code (SOC 2020 list), salary ≥£23,200/year OR going rate (whichever "
            "is higher), English at CEFR B1 (often via OET for clinical roles), professional registration "
            "with relevant UK body (GMC for doctors, NMC for nurses, GPhC for pharmacists)."
        ),
        "eligibility_criteria": [
            {"label": "Eligible employer", "value": "NHS, NHS supplier, OR CQC-regulated care provider", "notes": "Sponsor must hold a 'Health and Care Worker' sponsor licence"},
            {"label": "Eligible occupation code", "value": "Specific SOC 2020 codes for healthcare roles (doctors, nurses, paramedics, care workers etc.)", "notes": "List published at gov.uk; care worker eligibility narrowed Mar 2024 but doctors/nurses unaffected"},
            {"label": "Certificate of Sponsorship (CoS)", "value": "Defined CoS for out-of-country; Undefined for in-country switch", "notes": "Valid 3 months"},
            {"label": "Salary threshold", "value": "£23,200/year OR occupation going-rate, whichever is higher", "notes": "Lower than standard Skilled Worker £38,700; care worker minimum also £23,200"},
            {"label": "English language", "value": "CEFR B1 minimum; OET (Occupational English Test) preferred for clinical roles", "notes": "GMC/NMC may have higher requirements (e.g. OET B for nursing)"},
            {"label": "Professional registration", "value": "Required for regulated roles — GMC (doctors), NMC (nurses + midwives), GPhC (pharmacists), HCPC (allied health)", "notes": "Get registration BEFORE visa application for cleaner approval"},
            {"label": "Maintenance funds", "value": "£1,270 held in bank for 28+ consecutive days, OR sponsor certifies on CoS", "notes": ""},
            {"label": "TB test (India)", "value": "Required from UKVI-approved IOM clinic", "notes": ""},
        ],
        "fees_local_currency_code": "GBP",
        "fees_local_currency_amount": 304,
        "fees_inr_approx": 31920,
        "fees_breakdown": [
            {"component": "Health and Care Worker Visa — up to 3 years (out of UK)", "amount": 304, "currency": "GBP"},
            {"component": "Health and Care Worker Visa — over 3 years (out of UK)", "amount": 590, "currency": "GBP"},
            {"component": "IHS — EXEMPT for Health and Care Worker (savings of £5,175 over 5 years)", "amount": 0, "currency": "GBP"},
            {"component": "Priority Service", "amount": 500, "currency": "GBP"},
            {"component": "Biometric Enrolment fee", "amount": 19, "currency": "GBP"},
            {"component": "Professional registration (GMC ~£420, NMC ~£153 + £140 fee)", "amount": 420, "currency": "GBP"},
            {"component": "OET test (clinical)", "amount": 17500, "currency": "INR"},
            {"component": "TB test (IOM India)", "amount": 6500, "currency": "INR"},
            {"component": "ECCTIS qualification evaluation (if foreign degree)", "amount": 19000, "currency": "INR"},
        ],
        "processing_time_days_min": 15,
        "processing_time_days_max": 45,
        "step_by_step": [
            {"step_number": 1, "title": "Apply for UK Professional Registration", "description": "Doctors: GMC (General Medical Council). Nurses: NMC (Nursing and Midwifery Council). Pharmacists: GPhC. Allied health: HCPC. Each has profession-specific exams + assessments (e.g. PLAB for doctors, OSCE for nurses).", "estimated_days": 180, "documents_needed": ["Medical/Nursing degree", "Transcripts", "Identity proof", "Professional refs"], "tips": ["GMC PLAB Part 1 + Part 2 for International Medical Graduates", "NMC OSCE + CBT for nurses outside EU/UK education", "Get registration BEFORE visa application — strengthens approval"]},
            {"step_number": 2, "title": "Secure NHS/Eligible Job Offer + CoS", "description": "Apply for jobs via NHS Jobs portal or directly with CQC-regulated providers. On offer, employer issues CoS via Health and Care Worker Visa route.", "estimated_days": 90, "documents_needed": ["Job offer", "Employment contract", "CoS reference"], "tips": ["NHS Trusts are the largest sponsors", "Private hospitals + care providers must be CQC-regulated", "Care worker route added Aug 2023 but tightened Mar 2024 — verify current"]},
            {"step_number": 3, "title": "English Language (OET preferred for clinical)", "description": "OET grade B+ (for nursing/medical), or IELTS UKVI 4.0 each band minimum B1. Some applicants exempt if education was in English.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["OET tests medical English — easier for clinicians", "NMC requires OET grade B in Reading, Writing, Listening; B-/C+ in Speaking acceptable"]},
            {"step_number": 4, "title": "TB Test + Maintenance Funds", "description": "Standard for India applicants. Maintenance £1,270 for 28 days, or sponsor certifies on CoS.", "estimated_days": 28, "documents_needed": ["TB cert", "Bank statements"], "tips": ["Most NHS Trusts (A-rated) certify maintenance — saves bank requirement"]},
            {"step_number": 5, "title": "Submit Online Application", "description": "Apply at gov.uk via Health and Care Worker route (not standard Skilled Worker). Pay £304 fee. IHS automatically waived.", "estimated_days": 3, "documents_needed": ["CoS reference", "Passport", "English test", "TB test", "Professional registration", "Maintenance proof"], "tips": ["Confirm 'Health and Care Worker' route selected — IHS exemption depends on it", "Total cost savings vs general Skilled Worker: ~£5,500+ over 5 years"]},
            {"step_number": 6, "title": "Biometric Enrolment (VFS India)", "description": "Submit fingerprints + photo.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Decision + Travel to UK", "description": "3-week standard processing. Priority service available £500.", "estimated_days": 21, "documents_needed": [], "tips": ["Collect BRP within 10 days of arrival", "Start NHS induction promptly"]},
            {"step_number": 8, "title": "ILR after 5 years", "description": "5 continuous years on Health and Care Worker route → ILR eligible. Salary at ILR must still meet threshold + KOL + English B1.", "estimated_days": 90, "documents_needed": [], "tips": ["Keep employment continuous", "Document any breaks (max 180 days/year)"]},
        ],
        "document_checklist": [
            {"name": "Valid passport", "mandatory": True, "notes": ""},
            {"name": "Certificate of Sponsorship from NHS/CQC-regulated employer", "mandatory": True, "notes": "Health and Care Worker tier CoS specifically"},
            {"name": "Job offer letter on NHS/healthcare letterhead", "mandatory": True, "notes": "Specifies role, salary, SOC code, location"},
            {"name": "Professional registration (GMC/NMC/GPhC/HCPC)", "mandatory": True, "notes": "For regulated roles; get before visa application"},
            {"name": "English language test (OET / IELTS UKVI)", "mandatory": True, "notes": "OET preferred for clinical roles"},
            {"name": "TB test certificate (IOM India)", "mandatory": True, "notes": ""},
            {"name": "Maintenance funds — bank statements (28 days) OR sponsor certification on CoS", "mandatory": True, "notes": ""},
            {"name": "Medical/Nursing degree + transcripts", "mandatory": True, "notes": "Sealed transcripts from issuing institution"},
            {"name": "ECCTIS Statement of Comparability (foreign degree equivalency)", "mandatory": False, "notes": "Often required by professional bodies"},
            {"name": "Professional references (last 2-3 employers)", "mandatory": True, "notes": "Reference checks part of clinical roles"},
            {"name": "Identity documents + photos", "mandatory": True, "notes": ""},
            {"name": "Marriage cert + children's birth certs (if dependents)", "mandatory": False, "notes": ""},
            {"name": "Police clearance certificates", "mandatory": False, "notes": "Required for many healthcare roles; from each country 12+ months past 10 years"},
        ],
        "common_rejection_reasons": [
            "Sponsor not CQC-regulated or not eligible health employer",
            "Professional registration missing or not yet granted at application",
            "Salary below £23,200 OR going-rate (whichever higher)",
            "English language below required level (OET B for clinical typically)",
            "Care worker role under tightened post-Mar 2024 eligibility (some private domiciliary care excluded)",
            "Misrepresentation of qualifications or registration status",
            "Health/character inadmissibility (criminal history affecting fitness to practice)",
            "CoS expired (3-month validity)",
        ],
        "success_tips": [
            "Get UK professional registration BEFORE applying for visa — strengthens approval significantly",
            "NHS Trusts are A-rated sponsors — they certify maintenance on CoS, saving bank requirement",
            "OET is profession-specific and easier than IELTS for clinical English",
            "Apply via Health and Care Worker route specifically — confirms IHS exemption",
            "PLAB / OSCE / CBT preparation takes 3-6 months — start early",
            "Save £5,500+ vs general Skilled Worker — make sure all paperwork shows 'Health and Care Worker' route",
            "Sponsorship is health-employer-specific — can't switch to non-health employer without route change",
            "Apply 3-4 months before intended start date — leaves buffer",
        ],
        "faqs": [
            {"q": "Am I exempt from IHS?", "a": "YES — Health and Care Worker Visa holders are EXEMPT from Immigration Health Surcharge for entire visa duration. Dependants are also exempt. Massive savings (£5,175+ over 5 years for principal alone)."},
            {"q": "Is care worker still eligible?", "a": "Yes, with restrictions tightened from March 2024. Eligible: care workers in CQC-regulated services. NOT eligible: private domestic care, certain agency roles, supported living without CQC regulation. Verify with sponsor."},
            {"q": "Can I switch employers within healthcare?", "a": "Yes — within healthcare sector, you can switch to another CQC-regulated employer with new CoS. Switch outside healthcare requires standard Skilled Worker route (higher fee + IHS)."},
            {"q": "Do my family get IHS exemption too?", "a": "Yes — your spouse + children dependants on your visa also get IHS exemption. Family savings can exceed £15,000 over 5 years."},
            {"q": "What's PLAB and OSCE?", "a": "PLAB (Professional and Linguistic Assessments Board) — 2-part exam for International Medical Graduates seeking GMC registration. OSCE (Objective Structured Clinical Examination) — for nurses post-CBT to get NMC registration. Both take 3-6 months to prepare."},
            {"q": "When can I apply for ILR?", "a": "After 5 continuous years on Health and Care Worker route. Need: continuous employment, salary meeting threshold at ILR application, KOL test, English B1 maintained."},
        ],
        "official_url": "https://www.gov.uk/health-care-worker-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/",
        "source_urls": [
            "https://www.gov.uk/health-care-worker-visa",
            "https://www.gov.uk/government/publications/health-and-care-worker-visa-eligible-occupations",
            "https://www.gov.uk/healthcare-immigration-application/who-needs-pay",
            "https://www.gmc-uk.org/registration-and-licensing/join-the-register/registration-applications/specialist-application-guides",
            "https://www.nmc.org.uk/registration/joining-the-register/trained-outside-the-eu-eea-and-switzerland/",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against gov.uk on 2026-02-27. IHS exemption + reduced fee per current Health and Care Worker route policy. Care worker eligibility narrowed Mar 2024.",
    },

    # ── 3. Student Visa ────────────────────────────────────────────────────────
    {
        "country_code": "UK",
        "country_name": "United Kingdom",
        "subclass_id": "Student",
        "subclass_name": "Student Visa (formerly Tier 4)",
        "service_type": "student",
        "category": "immigration",
        "description": (
            "The UK Student Visa (renamed from Tier 4 in October 2020) allows international students to "
            "pursue full-time education at licensed sponsor educational institutions in the UK. It covers "
            "undergraduate, postgraduate, PhD, and pre-sessional language programmes. Crucially, on "
            "completion of a UK degree (Bachelor's, Master's, or PhD), graduates can apply for the **Graduate "
            "Route** — a 2-year (or 3-year for PhDs) open work visa enabling work for any UK employer "
            "without sponsorship.\n\n"
            "Key student visa requirements: CAS (Confirmation of Acceptance for Studies) from a licensed "
            "sponsor (university/college), proof of finances covering tuition + maintenance (London: "
            "£1,334/month, outside London: £1,023/month), English proficiency, and genuine student "
            "intent. Working rights: 20 hours/week during term-time, full-time during scheduled breaks."
        ),
        "eligibility_summary": (
            "Unconditional offer + CAS from licensed Student sponsor (university/college), proof of "
            "tuition payment or deposit, maintenance funds (£1,334/month London or £1,023/month outside "
            "London for up to 9 months), English language proficiency per course requirement, intent to "
            "leave UK at end of studies (or continue via Graduate Route)."
        ),
        "eligibility_criteria": [
            {"label": "Confirmation of Acceptance for Studies (CAS)", "value": "From a UKVI-licensed Student sponsor", "notes": "CAS reference valid 6 months from issue"},
            {"label": "Licensed sponsor on Student Sponsor Register", "value": "University/college on UKVI Student Sponsor list", "notes": "Verify at gov.uk register-of-licensed-sponsors-students"},
            {"label": "Tuition fee proof", "value": "1st year tuition paid OR deposit per CAS terms", "notes": "Some universities require full tuition before CAS issue"},
            {"label": "Maintenance funds", "value": "£1,334/month London OR £1,023/month outside London for up to 9 months", "notes": "Held in bank for 28+ days within 31 days of application"},
            {"label": "English language", "value": "Per course requirements — typically IELTS UKVI 6.0+ (UG) to 6.5+ (PG)", "notes": "Pre-sessional English programmes have lower thresholds"},
            {"label": "Academic background", "value": "Meets entry requirements for chosen course", "notes": "Sponsor verifies; UCAS for UG"},
            {"label": "Genuine student intent", "value": "Coherent study + career narrative", "notes": "Replaces old credibility interview in many cases; still possible"},
            {"label": "Health surcharge", "value": "IHS at £776/year (student rate, reduced from £1,035)", "notes": "Paid upfront for visa duration"},
            {"label": "TB test (India)", "value": "Required for stay 6+ months", "notes": "IOM-approved clinic"},
        ],
        "fees_local_currency_code": "GBP",
        "fees_local_currency_amount": 3082,
        "fees_inr_approx": 323610,
        "fees_breakdown": [
            {"component": "Student Visa application (out of UK)", "amount": 524, "currency": "GBP"},
            {"component": "Student Visa application (in-country extension)", "amount": 624, "currency": "GBP"},
            {"component": "IHS — Student rate £776/year × 3.3 years (UG average)", "amount": 2558, "currency": "GBP"},
            {"component": "Priority Service", "amount": 500, "currency": "GBP"},
            {"component": "Tuition deposit (Bachelor's 1st year average UK)", "amount": 18000, "currency": "GBP"},
            {"component": "Maintenance proof (9 months × £1,023 outside London)", "amount": 9207, "currency": "GBP"},
            {"component": "Maintenance proof (9 months × £1,334 London)", "amount": 12006, "currency": "GBP"},
            {"component": "TB test (IOM India)", "amount": 6500, "currency": "INR"},
            {"component": "English test (IELTS UKVI Academic)", "amount": 18800, "currency": "INR"},
        ],
        "processing_time_days_min": 21,
        "processing_time_days_max": 60,
        "step_by_step": [
            {"step_number": 1, "title": "Choose Course + University on Sponsor Register", "description": "Research courses at UKVI-licensed Student sponsors. Apply via UCAS (UG) or direct (PG).", "estimated_days": 60, "documents_needed": ["Transcripts", "Degree certificates (if PG)", "IELTS UKVI", "Personal statement"], "tips": ["Top Russell Group: Oxford, Cambridge, Imperial, UCL, KCL, Edinburgh, Manchester, Bristol, Warwick, LSE", "Check sponsor's Student rating before applying — Track Record A1 best", "Apply 6-12 months before intake"]},
            {"step_number": 2, "title": "Receive Unconditional Offer + CAS", "description": "On meeting offer conditions, university issues CAS reference number.", "estimated_days": 21, "documents_needed": ["University offer letter"], "tips": ["CAS valid 6 months", "Verify all CAS details match supporting docs"]},
            {"step_number": 3, "title": "Pay Tuition Deposit or Full Tuition", "description": "Per CAS conditions. Receipt becomes part of application.", "estimated_days": 7, "documents_needed": ["Tuition payment receipt"], "tips": ["Some universities require full 1st year tuition; others accept deposit", "Bank transfer with reference matching CAS"]},
            {"step_number": 4, "title": "English Language Test", "description": "IELTS UKVI Academic, PTE Academic UKVI, or accepted equivalents. Score per course requirement.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["UKVI version of IELTS for Pre-sessional + lower-level programmes", "Most degrees accept standard IELTS Academic"]},
            {"step_number": 5, "title": "TB Test + Maintenance Funds", "description": "TB at IOM India if 6+ months stay. Hold maintenance funds for 28+ consecutive days in own name.", "estimated_days": 28, "documents_needed": ["TB certificate", "Bank statements"], "tips": ["Sponsor/parent letter + tax returns for sponsor funds", "Maintenance amount per CAS specifies exact figure to show"]},
            {"step_number": 6, "title": "Submit Online Application", "description": "Apply at gov.uk via Student Route. Pay application fee + IHS. Choose Priority Service if needed.", "estimated_days": 3, "documents_needed": ["CAS reference", "Passport", "Tuition receipt", "Maintenance proof", "English test", "TB test", "Qualifications"], "tips": ["IHS at £776/year (lower than other routes)", "Apply 3-6 months before course start"]},
            {"step_number": 7, "title": "Biometric Enrolment", "description": "Visit VFS India. Submit fingerprints, photo, documents.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 8, "title": "Decision + Travel to UK", "description": "3-week standard. Travel on vignette within 90 days. Collect BRP within 10 days of arrival.", "estimated_days": 21, "documents_needed": [], "tips": ["Can enter UK up to 1 month before course start (longer courses)", "Apply for Graduate Route in final 6 weeks of course"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (with min 1 blank page)", "mandatory": True, "notes": ""},
            {"name": "Confirmation of Acceptance for Studies (CAS) reference", "mandatory": True, "notes": "From licensed Student sponsor"},
            {"name": "Tuition payment receipt", "mandatory": True, "notes": "Per CAS terms"},
            {"name": "Maintenance funds — bank statements (28 days)", "mandatory": True, "notes": "£1,334/month London or £1,023/month outside × 9 months"},
            {"name": "English language test (IELTS UKVI / PTE UKVI)", "mandatory": True, "notes": "Per course requirement"},
            {"name": "TB test certificate (IOM India)", "mandatory": True, "notes": "For stay 6+ months"},
            {"name": "Academic transcripts (10th, 12th, Bachelor's)", "mandatory": True, "notes": ""},
            {"name": "Degree certificates (if postgraduate)", "mandatory": True, "notes": "Sealed"},
            {"name": "Personal statement / Study plan", "mandatory": False, "notes": "Often required by university; useful for UKVI"},
            {"name": "Sponsor's tax returns / income proof (if sponsor funds)", "mandatory": False, "notes": "Last 2-3 years ITR"},
            {"name": "Parental consent + custodian letter (if under 18)", "mandatory": False, "notes": "For minors"},
            {"name": "ATAS certificate (specific STEM/research courses)", "mandatory": False, "notes": "Academic Technology Approval Scheme for sensitive subjects"},
            {"name": "Passport-style photos (UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "Translation of non-English docs", "mandatory": False, "notes": "Certified translator"},
        ],
        "common_rejection_reasons": [
            "Maintenance funds dipped below threshold during 28-day period",
            "Funds in non-applicant's name (parent's funds need full evidence trail)",
            "CAS expired (6-month validity from issue)",
            "Inconsistent course choice vs prior academic background (raises 'visa shopping' concern)",
            "English language below course requirement",
            "Prior visa refusals (any country) undeclared",
            "Insufficient credibility — vague answers about course, university, career link",
            "Tuition not paid per CAS terms",
        ],
        "success_tips": [
            "Choose Russell Group or top-ranked universities — higher visa success rates",
            "Maintain stable 28+ days of maintenance funds; document parent transfers clearly",
            "Write a tailored personal statement aligning course to career goals",
            "Apply via Graduate Route in your final 6 weeks — opens 2-year work without sponsorship",
            "PhD applicants get Graduate Route extension (3 years) + can apply for Global Talent later",
            "Pay full year tuition where possible — strongest financial proof",
            "Take IELTS UKVI Academic (not General Training) — required for Pre-sessional",
            "Apply 3-4 months before course intake for buffer",
        ],
        "faqs": [
            {"q": "What is the Graduate Route?", "a": "2-year open work visa (3 years for PhDs) after completing UK degree at Bachelor's+ level. No sponsorship needed. Work in any role, any employer. Cannot extend or convert to ILR directly — but bridges to Skilled Worker/Global Talent."},
            {"q": "Can I work during studies?", "a": "Yes — 20 hours/week during term, full-time during scheduled breaks. PhD/research Master's: unlimited hours."},
            {"q": "Can my family come with me?", "a": "Yes — but with restrictions. Spouse/partner can come for PhD/Master's by Research/Government-sponsored courses 6+ months. NOT for taught Master's under 9 months. Children under 18 can come."},
            {"q": "What's CAS?", "a": "Confirmation of Acceptance for Studies — UKVI-issued reference confirming unconditional offer from licensed sponsor. Required for visa application. Valid 6 months."},
            {"q": "How much does UK study cost overall?", "a": "Tuition: £15,000-£45,000/year UG, £18,000-£50,000/year PG. Living costs (London): £14,000-£18,000/year. Total: ₹30-70 lakh/year for full-time UG; PG similar."},
            {"q": "Can I switch to Skilled Worker after Graduate Route?", "a": "Yes — Graduate Route is designed to bridge to Skilled Worker. Find employer with sponsor licence, get CoS, apply for Skilled Worker switch (in-country)."},
        ],
        "official_url": "https://www.gov.uk/student-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/",
        "source_urls": [
            "https://www.gov.uk/student-visa",
            "https://www.gov.uk/student-visa/money",
            "https://www.gov.uk/government/publications/register-of-licensed-sponsors-students",
            "https://www.gov.uk/graduate-visa",
            "https://www.gov.uk/healthcare-immigration-application/who-needs-pay",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against gov.uk on 2026-02-27. Maintenance threshold £1,334 London / £1,023 outside London per Jan 2025 update. IHS Student rate £776/year.",
    },

    # ── 4. Standard Visitor Visa ──────────────────────────────────────────────
    {
        "country_code": "UK",
        "country_name": "United Kingdom",
        "subclass_id": "Visitor",
        "subclass_name": "Standard Visitor Visa (Tourism / Business / Family / Short Study)",
        "service_type": "visitor",
        "category": "immigration",
        "description": (
            "The Standard Visitor Visa is the UK's main short-term visa for non-visa-national tourists, "
            "business visitors, family visitors, and short-term students. Indian nationals require a "
            "Visitor Visa to enter the UK for any reason (UK is visa-required for India). Standard maximum "
            "stay per visit: **6 months**. Visa types include single-entry, multi-entry, and Long-Term "
            "Visitor Visa (2/5/10 years validity, with 6-month max per visit still applying).\n\n"
            "Allowed activities: tourism, visiting family/friends, business meetings + conferences, "
            "negotiating contracts, attending interviews, short-term study (up to 6 months at accredited "
            "institution), receiving private medical treatment, marriage as Marriage Visitor (different "
            "route required). PROHIBITED: paid employment, public funds, marriage at UK Civil Registry "
            "without separate Marriage Visitor Visa, frequent + long stays equivalent to UK residency."
        ),
        "eligibility_summary": (
            "Demonstrate intent to leave UK at end of authorised stay, sufficient funds for visit + return, "
            "specific purpose (tourism/family/business/short study), no criminal/security concerns. "
            "Visiting family: invitation letter + family member's UK status. Business: company invite + "
            "purpose. Frequent visits flagged if pattern looks residency-like."
        ),
        "eligibility_criteria": [
            {"label": "Genuine visitor intent", "value": "Will leave UK at end of authorised stay", "notes": "Strong ties to home country: family, employment, property"},
            {"label": "Sufficient funds", "value": "Demonstrate ability to fund visit + return", "notes": "No fixed minimum but typically £80-£150/day for stay duration + return ticket"},
            {"label": "Specific purpose", "value": "Tourism / family visit / business meetings / conference / short study / private medical / marriage (Marriage Visitor)", "notes": "Vague itinerary = refusal risk"},
            {"label": "No prohibited activity intent", "value": "No paid work, no public funds, no marriage at Civil Registry without Marriage Visitor Visa", "notes": "Short unpaid academic engagements allowed"},
            {"label": "Frequency check", "value": "Not making UK the main home via frequent + long visits", "notes": "Pattern of 6 months in, short out, 6 months back = high refusal"},
            {"label": "Admissibility", "value": "No criminal record affecting Good Character, no immigration violations", "notes": "Past refusals (any country) must be declared"},
            {"label": "Biometrics", "value": "Mandatory for Indian nationals", "notes": "Valid 5 years from collection"},
            {"label": "TB test (long-term Visitor Visa)", "value": "Only if applying for visa allowing 6+ month single stays", "notes": "Standard 6-month Visitor doesn't require"},
        ],
        "fees_local_currency_code": "GBP",
        "fees_local_currency_amount": 127,
        "fees_inr_approx": 13335,
        "fees_breakdown": [
            {"component": "Standard Visitor Visa (6 months single/multi)", "amount": 127, "currency": "GBP"},
            {"component": "Long-Term Visitor Visa (2 years)", "amount": 475, "currency": "GBP"},
            {"component": "Long-Term Visitor Visa (5 years)", "amount": 848, "currency": "GBP"},
            {"component": "Long-Term Visitor Visa (10 years)", "amount": 1059, "currency": "GBP"},
            {"component": "Priority Service (3-5 working days)", "amount": 250, "currency": "GBP"},
            {"component": "Super-Priority Service (24 hr decision)", "amount": 1000, "currency": "GBP"},
            {"component": "Biometric Enrolment fee", "amount": 19, "currency": "GBP"},
            {"component": "TB test (long-term Visitor only)", "amount": 6500, "currency": "INR"},
        ],
        "processing_time_days_min": 15,
        "processing_time_days_max": 21,
        "step_by_step": [
            {"step_number": 1, "title": "Determine Visa Type", "description": "Standard 6-month single/multi-entry visa is most common. Long-term variants (2/5/10 years) for frequent business or family visitors with 6-month max stay per visit still.", "estimated_days": 3, "documents_needed": [], "tips": ["Multi-entry default for tourist + business", "Long-term variants worth it for frequent family visitors"]},
            {"step_number": 2, "title": "Gather Purpose-Specific Documents", "description": "Tourism: itinerary + hotel bookings. Family visit: invitation letter + family's UK status. Business: company invite + purpose. Short study: institution invite.", "estimated_days": 14, "documents_needed": ["Itinerary / hotel bookings (tourism)", "Family member's BRP/Passport copy (family visit)", "Letter of Invitation", "Business meeting invite (business)"], "tips": ["Itinerary doesn't need 100% bookings — outline + tentative dates fine", "LOI from UK host should include relationship + duration + financial commitment"]},
            {"step_number": 3, "title": "Prepare Financial Evidence", "description": "Show funds to support visit + return.", "estimated_days": 14, "documents_needed": ["6 months bank statements", "ITRs (last 2-3 years)", "Salary slips / business income proof", "Property documents"], "tips": ["£3,000+ for 2-week trip (incl. return ticket) is comfortable", "Stable balance over 6 months > sudden lump sum"]},
            {"step_number": 4, "title": "Complete Online Application", "description": "Apply at gov.uk/standard-visitor-visa. Fill VAF (Visa Application Form) online.", "estimated_days": 3, "documents_needed": ["Passport scan", "Photo", "Form completion", "Supporting docs upload"], "tips": ["Declare prior refusals from ANY country (Schengen, US, AU, NZ etc.)", "List all family in UK — concealment = refusal"]},
            {"step_number": 5, "title": "Pay Fees + Book Biometric Appointment", "description": "Pay online. VFS UK in India for biometrics.", "estimated_days": 7, "documents_needed": ["Application reference"], "tips": ["Biometrics in 14 days of paying; choose Priority service if rushed"]},
            {"step_number": 6, "title": "Biometric Enrolment + Submit Docs", "description": "Visit VFS UK centre. Fingerprints + photo + document upload.", "estimated_days": 7, "documents_needed": ["Application form", "All supporting docs", "Passport"], "tips": ["Carry digital + printed copies of everything", "Re-use biometrics from any UK visa in last 5 years"]},
            {"step_number": 7, "title": "Decision + Visa Sticker", "description": "Standard 15-day processing. Priority 3-5 days. Super-Priority 24 hours.", "estimated_days": 21, "documents_needed": [], "tips": ["Receive passport with visa sticker via courier/collection", "Visa sticker shows entry validity"]},
            {"step_number": 8, "title": "Travel to UK + Border Crossing", "description": "Travel during visa validity. UK Border Force officer at airport decides entry + any conditions.", "estimated_days": 1, "documents_needed": ["Passport with visa sticker", "Itinerary", "Return ticket", "Funds proof"], "tips": ["Carry copy of LOI + family member status if visiting family", "Don't bring excessive cash undeclared (>£10,000 must be declared)", "Be honest about purpose — different from visa application invites refusal"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (min 6 months validity)", "mandatory": True, "notes": ""},
            {"name": "Visa Application Form (printout from gov.uk)", "mandatory": True, "notes": ""},
            {"name": "Photos (UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "Bank statements (last 6 months)", "mandatory": True, "notes": "Stable funds + transaction history"},
            {"name": "Income Tax Returns (last 2-3 years)", "mandatory": True, "notes": "Economic ties to India"},
            {"name": "Salary slips OR business income proof", "mandatory": True, "notes": "Last 3-6 months"},
            {"name": "Property documents (home ownership / rental)", "mandatory": False, "notes": "Strengthens home ties"},
            {"name": "Itinerary / Hotel bookings (if tourism)", "mandatory": False, "notes": "Tentative acceptable"},
            {"name": "Letter of Invitation from UK host (if family visit)", "mandatory": False, "notes": "Includes relationship, address, financial commitment"},
            {"name": "Host's BRP/Passport/Citizenship proof (if LOI)", "mandatory": False, "notes": ""},
            {"name": "Conference / Business meeting invitation (if business)", "mandatory": False, "notes": ""},
            {"name": "Travel insurance (recommended)", "mandatory": False, "notes": "Not mandatory but strongly advised"},
            {"name": "Leave letter from employer (if employed)", "mandatory": False, "notes": "Shows return to job"},
            {"name": "Marriage certificate + children's birth certs (if family travel)", "mandatory": False, "notes": ""},
            {"name": "Prior travel history / passport stamps copy", "mandatory": False, "notes": "Helps demonstrate compliance pattern"},
        ],
        "common_rejection_reasons": [
            "Insufficient ties to India — UKVI believes you won't return",
            "Insufficient funds for trip + return",
            "Inconsistent itinerary / purpose / sponsor info",
            "Prior visa refusal (any country) undeclared",
            "Family member in UK on temporary status raising 'overstay' concern",
            "Frequent prior UK visits forming residency pattern",
            "Vague answers to credibility questions about purpose, accommodation, return plans",
            "Misrepresentation in any document",
        ],
        "success_tips": [
            "Build a clear story: PURPOSE + DURATION + ACCOMMODATION + FUNDS + RETURN",
            "Apply 4-8 weeks before intended travel — gives buffer for delays/queries",
            "For family visits: detailed LOI with host's commitment is the strongest evidence",
            "For business: company invitation on letterhead with meeting itinerary",
            "Show stable employment + salary credits + ITRs going back 2 years",
            "Don't apply for first-time UK visa with US/Schengen refusals in last 12 months",
            "Consider Long-Term Visitor (2 years) if visiting family frequently",
            "Avoid showing intent to study/work — those need different visas",
        ],
        "faqs": [
            {"q": "How long can I stay on a Standard Visitor Visa?", "a": "Maximum 6 months per visit. UK Border officer at airport decides actual stay. Long-Term Visitor variants (2/5/10 years) allow MULTIPLE visits but still 6-month max per visit."},
            {"q": "Can I work on Visitor Visa?", "a": "NO paid work allowed. Permitted: business meetings, negotiating contracts, attending conferences. NOT permitted: providing services to UK employer (even unpaid), filling local positions, freelancing for UK clients."},
            {"q": "What's the difference between Standard Visitor and other visit visas?", "a": "Standard Visitor covers most short visits. Separate Marriage Visitor Visa for ceremony at UK Civil Registry. Permitted Paid Engagement Visa for specific paid activities (academics, sportspeople). Transit Visa for stopovers."},
            {"q": "Can I study on a Visitor Visa?", "a": "Yes — short courses up to 6 months at accredited institution. NOT for degree programs. For degree courses, need Student Visa."},
            {"q": "Can I extend my Visitor Visa in UK?", "a": "Generally no. Total stay capped at 6 months. Limited extension possible for serious reasons (medical, exam dates) up to maximum 6 months total."},
            {"q": "What's a frequent visitor pattern?", "a": "UKVI flags pattern of 5+ visits or 180+ days in last 12 months as making UK your main home. Pattern visitors should look at Long-Term Visitor or proper residence routes."},
        ],
        "official_url": "https://www.gov.uk/standard-visitor",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/",
        "source_urls": [
            "https://www.gov.uk/standard-visitor",
            "https://www.gov.uk/government/publications/visit-uk-guide-for-visitors",
            "https://www.gov.uk/standard-visitor/eligibility",
            "https://www.gov.uk/government/publications/visit-uk-immigration-rules-appendix-visitor-permitted-activities",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against gov.uk on 2026-02-27. Standard Visitor fees per current UKVI schedule. Long-Term variants priced per gov.uk fee schedule.",
    },

    # ── 5. Family / Spouse Visa (Appendix FM) ─────────────────────────────────
    {
        "country_code": "UK",
        "country_name": "United Kingdom",
        "subclass_id": "Spouse-Family",
        "subclass_name": "Spouse / Partner Visa (Appendix FM)",
        "service_type": "partner",
        "category": "immigration",
        "description": (
            "The Spouse/Partner Visa (under Immigration Rules Appendix FM) is for spouses, civil partners, "
            "and unmarried partners (with 2+ years cohabitation) of British citizens, persons settled in "
            "the UK (ILR), or refugees/humanitarian protection holders. It is the primary route for "
            "Indians married to or partnered with UK citizens/settled persons.\n\n"
            "**Key change April 2024:** Minimum income requirement raised from £18,600 to **£29,000/year** "
            "(rising in phases to £38,700 in early 2025). This is the most significant recent reform. "
            "Visa is granted 33 months initially (out-of-country) or 30 months (in-country). At 2.5 years, "
            "extension for further 2.5 years. After 5 years total continuous residence, eligible for ILR. "
            "English language requirements: A1 (initial), A2 (extension), B1 (ILR + KOL test)."
        ),
        "eligibility_summary": (
            "Sponsor (British citizen, ILR holder, refugee, or humanitarian protection) must be 18+ + meet "
            "minimum income £29,000/year (subject to phased rises) OR have £88,500 cash savings. Relationship "
            "must be genuine + subsisting. Couple must intend to live together permanently. Applicant must "
            "meet English A1 at entry, A2 at extension, B1 at ILR. Adequate accommodation in UK."
        ),
        "eligibility_criteria": [
            {"label": "Sponsor status", "value": "British citizen, ILR holder, refugee, or person with humanitarian protection", "notes": "Sponsor must be 18+"},
            {"label": "Genuine + subsisting relationship", "value": "Marriage/civil partnership recognised in UK OR 2+ years cohabitation as unmarried partners", "notes": "Marriage abroad recognised if legal in country of celebration"},
            {"label": "Minimum income (Financial Requirement)", "value": "£29,000/year from sponsor (post-April 2024); rising to £38,700 in stages; OR £88,500 cash savings; OR combination", "notes": "Some routes use applicant's income too; refugees exempt; pre-Apr 2024 applications grandfathered at £18,600"},
            {"label": "English language", "value": "CEFR A1 (entry/initial), A2 (extension at 2.5yr), B1 (ILR after 5yr)", "notes": "Approved tests: IELTS Life Skills, Trinity ISE, others; some nationalities exempt"},
            {"label": "Adequate accommodation", "value": "Sufficient + appropriate housing in UK without recourse to public funds", "notes": "Cannot be overcrowded; usually shown via tenancy / property documents"},
            {"label": "TB test (India)", "value": "Required from IOM-approved clinic", "notes": ""},
            {"label": "No criminal history affecting Good Character", "value": "Past offences may disqualify", "notes": "Standard checks"},
            {"label": "Intention to live together permanently", "value": "Strong evidence required", "notes": "Photos, communications, joint accounts, shared property"},
        ],
        "fees_local_currency_code": "GBP",
        "fees_local_currency_amount": 7113,
        "fees_inr_approx": 746865,
        "fees_breakdown": [
            {"component": "Spouse Visa application (out of UK, initial entry clearance)", "amount": 1938, "currency": "GBP"},
            {"component": "Spouse Visa application (in-country switch/extension)", "amount": 1048, "currency": "GBP"},
            {"component": "IHS — £1,035/year × 5 years (initial 2.5 + ext 2.5)", "amount": 5175, "currency": "GBP"},
            {"component": "Priority Service (decision in 30 working days)", "amount": 573, "currency": "GBP"},
            {"component": "Super-Priority (5 working days)", "amount": 1000, "currency": "GBP"},
            {"component": "TB test (IOM India)", "amount": 6500, "currency": "INR"},
            {"component": "English test (IELTS Life Skills A1)", "amount": 10500, "currency": "INR"},
            {"component": "Translation of marriage cert / documents", "amount": 4000, "currency": "INR"},
        ],
        "processing_time_days_min": 90,
        "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Verify Sponsor + Financial Requirement", "description": "Confirm sponsor status. Calculate £29,000/year income via salaried employment, self-employment, savings, or combination. Sponsor's job must be ongoing (6+ months) at time of application.", "estimated_days": 14, "documents_needed": ["Sponsor passport/BRP", "Sponsor's payslips (6 months)", "Employer letter", "Tax returns (SA302 forms)"], "tips": ["Salaried sponsors: 6 months consistent payslips at £29,000+", "Self-employed: 1-2 years SA302 (Self Assessment) tax calculations + business accounts", "Cash savings: £88,500 held 6 months in sponsor's name"]},
            {"step_number": 2, "title": "Marriage/Relationship Evidence", "description": "Build strong evidence of genuine + subsisting relationship.", "estimated_days": 30, "documents_needed": ["Marriage certificate (apostilled if Indian)", "Joint bank accounts", "Photos across timeline", "Communications (WhatsApp/email logs)", "Travel together", "Statutory declarations from family/friends"], "tips": ["Cover entire relationship — early courtship to current", "Include family + cultural events (wedding photos with both sides' family)", "Joint accounts opened well before application strengthen genuineness"]},
            {"step_number": 3, "title": "English Language Test (A1 Level)", "description": "Take IELTS Life Skills A1 or approved equivalent. Score Pass/Fail in Speaking + Listening.", "estimated_days": 14, "documents_needed": ["Passport"], "tips": ["IELTS Life Skills A1 is short + focused", "Some nationalities (UK-born majority English-speaking countries) exempt; Indians NOT exempt"]},
            {"step_number": 4, "title": "TB Test + Maintenance Documentation", "description": "TB at IOM India. Compile accommodation proof + maintenance.", "estimated_days": 21, "documents_needed": ["TB cert", "Sponsor's accommodation (tenancy/mortgage)", "Council tax bill"], "tips": ["Maintenance shown via sponsor's commitment + accommodation suitability", "If applicant has UK income, can contribute"]},
            {"step_number": 5, "title": "Submit Online Application", "description": "Apply at gov.uk via Spouse Route. Pay application fee + IHS. Upload all supporting docs.", "estimated_days": 7, "documents_needed": ["Marriage cert", "Sponsor docs", "Financial docs", "Relationship evidence", "English test", "TB test", "Photos"], "tips": ["Use Priority Service for faster decision", "Bundle docs by category — Sponsor's Finance, Relationship Evidence, etc."]},
            {"step_number": 6, "title": "Biometric Enrolment", "description": "Visit VFS UK in India. Submit fingerprints + photo + scanned documents.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Decision + Travel", "description": "Standard 12 weeks. Priority 30 days. Visa vignette in passport on approval. Travel to UK within 30 days, collect BRP within 10 days of arrival.", "estimated_days": 90, "documents_needed": [], "tips": ["Vignette valid 30 days for travel", "If interview requested, attend with all originals"]},
            {"step_number": 8, "title": "Extension (2.5 years) + ILR (5 years)", "description": "After 2.5 years initial visa, apply for extension (same financial requirement + A2 English). After 5 years total, apply for ILR (B1 English + KOL test + still meeting income requirement).", "estimated_days": 90, "documents_needed": [], "tips": ["Apply 28 days before current visa expires", "Maintain continuous residence — max 180 days outside UK in any 12-month period during the 5 years"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (applicant)", "mandatory": True, "notes": ""},
            {"name": "Sponsor's passport (British citizen) / BRP (ILR holder)", "mandatory": True, "notes": ""},
            {"name": "Marriage certificate (apostilled if Indian)", "mandatory": True, "notes": "Official translation if not in English"},
            {"name": "Sponsor's recent payslips (6 months)", "mandatory": True, "notes": "Salaried route"},
            {"name": "Sponsor's employer letter (confirming role + salary + 6+ months ongoing)", "mandatory": True, "notes": ""},
            {"name": "Sponsor's bank statements (6 months matching payslips)", "mandatory": True, "notes": ""},
            {"name": "Sponsor's P60 / Self Assessment SA302 (self-employed)", "mandatory": False, "notes": "For self-employed sponsors"},
            {"name": "Joint bank account statements", "mandatory": False, "notes": "Strengthens financial entanglement evidence"},
            {"name": "Photos throughout relationship", "mandatory": True, "notes": "Engagement, wedding, daily life — varied"},
            {"name": "Communication logs (WhatsApp/email — including pre-marriage period)", "mandatory": True, "notes": "Cover the relationship arc"},
            {"name": "Joint tenancy / mortgage / utility bills (if lived together)", "mandatory": False, "notes": ""},
            {"name": "Statutory declarations from 2-4 family/friends", "mandatory": True, "notes": "Confirming genuineness of relationship"},
            {"name": "Sponsor's UK accommodation (tenancy / mortgage / council tax)", "mandatory": True, "notes": "Proves adequate housing"},
            {"name": "English language test certificate (A1 minimum)", "mandatory": True, "notes": "IELTS Life Skills, Trinity ISE"},
            {"name": "TB test certificate (IOM India)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certificates (if children applying together)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Sponsor doesn't meet £29,000 minimum income (post-Apr 2024 rule)",
            "Documents don't match income claim (gaps in payslips, inconsistent SA302)",
            "Relationship evidence thin or arranged-marriage-only with no daily-life evidence",
            "English language test below A1 OR not from approved provider",
            "Accommodation inadequate (overcrowded or insecure)",
            "Sponsor's prior immigration violations or undisclosed criminality",
            "Misrepresentation of income, relationship origin, or accommodation",
            "Couple has not lived together (for unmarried partner route, need 2+ years cohabitation)",
        ],
        "success_tips": [
            "Verify sponsor's income meets post-Apr 2024 threshold (£29k, rising to £38.7k)",
            "Build relationship evidence ACROSS timeline — not just wedding photos",
            "Sponsor's employer letter should confirm role + salary + 'ongoing employment'",
            "Joint bank account opened pre-application strengthens genuineness significantly",
            "For arranged marriages: photos with extended family from both sides + post-wedding daily life",
            "Maintain communication logs (WhatsApp, video calls) across distance period",
            "Use Priority Service if family separation is stressful",
            "Plan for 5-year journey: initial 2.5yr + extension 2.5yr + ILR — total cost ~£10,000+ over the route",
        ],
        "faqs": [
            {"q": "What's the minimum income requirement?", "a": "£29,000/year as of April 2024 (raised from £18,600). Government has indicated further phased rise to £38,700. Sponsor's salaried employment, self-employment income, or £88,500 cash savings (held 6 months) can meet this."},
            {"q": "Can I include my children?", "a": "Yes — dependent children of either partner can apply with you. Same English (if 18+), TB test, accommodation requirements apply per child."},
            {"q": "How long is the visa initially?", "a": "33 months for out-of-country first application, 30 months for in-country switch. Extension granted 2.5 years if requirements still met."},
            {"q": "When can I apply for ILR (settlement)?", "a": "After 5 continuous years on Spouse/Family route. Need: continuous residence (max 180 days/12 months outside UK), still meeting financial requirement, English at B1, pass KOL (Life in UK) test."},
            {"q": "What if sponsor's income is below £29k?", "a": "Options: (a) Sponsor's salaried income + applicant's income combined, (b) Sponsor's cash savings £88,500 held 6 months, (c) Combination of income + savings (proportional), (d) Apply on basis of refugee/asylum status if sponsor qualifies (exemption applies)."},
            {"q": "Are joint accounts mandatory?", "a": "Not mandatory but VERY strong evidence. Even small joint accounts with regular usage demonstrate financial entanglement and relationship genuineness."},
        ],
        "official_url": "https://www.gov.uk/uk-family-visa/partner-spouse",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/",
        "source_urls": [
            "https://www.gov.uk/uk-family-visa/partner-spouse",
            "https://www.gov.uk/government/publications/chapter-8-family-members",
            "https://www.gov.uk/government/publications/immigration-rules/immigration-rules-appendix-fm-family-members",
            "https://www.gov.uk/government/publications/family-life-as-a-partner-or-parent-private-life-and-exceptional-circumstance",
            "https://www.gov.uk/healthcare-immigration-application/who-needs-pay",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against gov.uk on 2026-02-27. Minimum income £29,000 per April 2024 reform; further rises planned. Appendix FM rules per current Immigration Rules.",
    },

    # ── 6. Innovator Founder Visa ──────────────────────────────────────────────
    {
        "country_code": "UK",
        "country_name": "United Kingdom",
        "subclass_id": "Innovator-Founder",
        "subclass_name": "Innovator Founder Visa",
        "service_type": "work",
        "category": "immigration",
        "description": (
            "The Innovator Founder Visa, launched in April 2023, replaced the previous Innovator Visa and "
            "Start-up Visa routes. It enables non-UK nationals to establish an innovative, viable, and "
            "scalable business in the UK. The most significant change from the old Innovator Visa: the "
            "**£50,000 minimum investment requirement was REMOVED**. There is now NO MINIMUM INVESTMENT — "
            "the focus shifts entirely to the business being genuinely innovative and endorsed by a "
            "recognised endorsing body.\n\n"
            "Endorsing bodies (e.g. UK Tech Cluster body, accelerators like Tech Nation alumni, specific "
            "innovation incubators) assess the business plan for: innovation (genuinely new or significant "
            "differentiation), viability (realistic + achievable), scalability (growth potential + job "
            "creation). Initial visa: 3 years. After 3 years, eligible for ILR if business meets growth "
            "milestones. Alternative: continue on visa extensions if business needs more time. English at "
            "B2 level required."
        ),
        "eligibility_summary": (
            "Endorsement from UKVI-approved endorsing body for a NEW innovative, viable, scalable business "
            "(or already established business meeting criteria), £1,270 maintenance funds, English at "
            "CEFR B2, age 18+, sole/significant founder role in the business, intent to operate the "
            "business in UK."
        ),
        "eligibility_criteria": [
            {"label": "Endorsement from approved endorsing body", "value": "Endorsement letter from UKVI-listed endorsing body confirming innovation, viability, scalability", "notes": "Endorsing bodies: Tech Nation Alumni Network (Endeavor), Founders Forum Group, Envestors, RKK Innovation Centre, etc. — list at gov.uk"},
            {"label": "Innovative business", "value": "Genuinely new business OR significant difference from existing offerings", "notes": "Not just opening another restaurant or shop; must demonstrate IP, novel approach, or market gap addressed"},
            {"label": "Viable business", "value": "Realistic + achievable plan with reasonable assumptions", "notes": "Endorsing body assesses financial projections, market research, founder capability"},
            {"label": "Scalable business", "value": "Growth potential + job creation in UK over 3+ years", "notes": "Plan should show roadmap to revenue + UK employment"},
            {"label": "Founder role", "value": "Sole founder OR significant role in a founding team", "notes": "Not a passive investor; active operational involvement"},
            {"label": "No minimum investment", "value": "ZERO minimum financial investment required (changed April 2023)", "notes": "Old £50,000 requirement removed; endorsing body discretion on funding adequacy"},
            {"label": "Maintenance funds", "value": "£1,270 held in own bank account 28+ consecutive days", "notes": "Standard for non-Skilled Worker routes"},
            {"label": "English language", "value": "CEFR B2 (Upper-Intermediate) in all 4 skills", "notes": "IELTS UKVI 5.5+ each band, or degree taught in English (NARIC equivalency)"},
            {"label": "TB test (India)", "value": "Required", "notes": ""},
        ],
        "fees_local_currency_code": "GBP",
        "fees_local_currency_amount": 4296,
        "fees_inr_approx": 451080,
        "fees_breakdown": [
            {"component": "Innovator Founder Visa application (out of UK)", "amount": 1191, "currency": "GBP"},
            {"component": "Innovator Founder Visa application (in-country switch)", "amount": 1486, "currency": "GBP"},
            {"component": "IHS — £1,035/year × 3 years", "amount": 3105, "currency": "GBP"},
            {"component": "Priority Service", "amount": 500, "currency": "GBP"},
            {"component": "Biometric Enrolment fee", "amount": 19, "currency": "GBP"},
            {"component": "Endorsing body fee (varies; ~£3,000-£10,000 typical)", "amount": 5000, "currency": "GBP"},
            {"component": "TB test (IOM India)", "amount": 6500, "currency": "INR"},
            {"component": "English test (IELTS UKVI)", "amount": 18800, "currency": "INR"},
            {"component": "Business plan + legal advisory (recommended)", "amount": 100000, "currency": "INR"},
        ],
        "processing_time_days_min": 21,
        "processing_time_days_max": 90,
        "step_by_step": [
            {"step_number": 1, "title": "Develop Innovative Business Idea + Plan", "description": "Research UK market gap. Develop business plan emphasising innovation, viability, scalability. Document IP, market research, financial projections, team plan.", "estimated_days": 90, "documents_needed": ["Business plan", "Market research", "Financial projections", "Team CVs", "IP documentation"], "tips": ["Innovation must be GENUINE — not just convenience or location-based differentiation", "Scalability roadmap: revenue + UK headcount over 3-5 years", "Investor pitch decks help demonstrate viability"]},
            {"step_number": 2, "title": "Engage Endorsing Body", "description": "Approach UKVI-approved endorsing body (Tech Nation Alumni, Founders Forum, Envestors etc.) with business plan + founder profile. Pay endorsing body fee. Pitch + iterate.", "estimated_days": 60, "documents_needed": ["Pitch deck", "Business plan", "Founder CV", "Team CVs"], "tips": ["Different endorsing bodies have different focus areas (tech, social enterprise, deep tech)", "Some require physical interview", "Endorsement fee non-refundable"]},
            {"step_number": 3, "title": "Receive Endorsement Letter", "description": "Endorsing body issues formal letter confirming innovation + viability + scalability assessment. Valid 3 months for visa application.", "estimated_days": 14, "documents_needed": ["Endorsement letter"], "tips": ["Letter must explicitly confirm 3 criteria met", "Apply for visa within 3 months"]},
            {"step_number": 4, "title": "English Language + TB Test + Maintenance", "description": "Take IELTS UKVI B2. TB test at IOM India. Hold £1,270 for 28+ days.", "estimated_days": 28, "documents_needed": ["IELTS UKVI", "TB cert", "Bank statements"], "tips": ["B2 in IELTS UKVI = 5.5 each band", "Maintenance kept stable, not zero-balance days"]},
            {"step_number": 5, "title": "Submit Online Application", "description": "Apply at gov.uk via Innovator Founder route. Pay application fee + IHS.", "estimated_days": 7, "documents_needed": ["Endorsement letter", "Passport", "English test", "TB test", "Maintenance proof", "Business plan summary", "Photos"], "tips": ["Reference endorsing body + endorsement number", "Provide business plan summary in application"]},
            {"step_number": 6, "title": "Biometric Enrolment", "description": "Visit VFS UK in India.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Decision + Travel to UK + Start Business", "description": "3-week standard processing. On approval, travel to UK, register business at Companies House, open business bank account.", "estimated_days": 30, "documents_needed": [], "tips": ["Companies House registration: ~£12 online", "Open business account at Tide, Starling, Wise Business, or traditional banks"]},
            {"step_number": 8, "title": "Contact Point Check + ILR after 3 years", "description": "Endorsing body conducts contact point check at 12 and 24 months. After 3 years, eligible for ILR if business meeting growth milestones (revenue, jobs created, investment received).", "estimated_days": 1095, "documents_needed": [], "tips": ["Keep endorsing body informed of progress", "Document EVERY hire, investment, contract for ILR application", "Failed milestone = visa extension required (not ILR)"]},
        ],
        "document_checklist": [
            {"name": "Valid passport", "mandatory": True, "notes": ""},
            {"name": "Endorsement letter from UKVI-approved endorsing body", "mandatory": True, "notes": "Includes innovation/viability/scalability confirmation"},
            {"name": "Business plan (executive summary + full document)", "mandatory": True, "notes": "Submitted to endorsing body"},
            {"name": "Founder CV + LinkedIn", "mandatory": True, "notes": "Track record + relevant experience"},
            {"name": "Team CVs (if applicable)", "mandatory": False, "notes": "For founding team applications"},
            {"name": "Market research / IP documentation", "mandatory": False, "notes": "Supports innovation claim"},
            {"name": "Financial projections (3-5 years)", "mandatory": True, "notes": "Revenue + cost + employment + investment"},
            {"name": "English language test (IELTS UKVI B2+)", "mandatory": True, "notes": "All 4 skills"},
            {"name": "TB test certificate (IOM India)", "mandatory": True, "notes": ""},
            {"name": "Maintenance funds — bank statements (28 days, £1,270)", "mandatory": True, "notes": "Own name; consecutive days"},
            {"name": "Passport-style photos (UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "Educational qualifications", "mandatory": False, "notes": "Backs founder credibility"},
            {"name": "Prior business achievements / investments / IP", "mandatory": False, "notes": "Strengthens application"},
        ],
        "common_rejection_reasons": [
            "Endorsing body issues at endorsement stage (innovation not genuine, viability concerns)",
            "Business plan not aligned with endorsement claims",
            "English language below B2 in any skill",
            "Maintenance funds dipped below £1,270 during 28 days",
            "Misrepresentation of founder role / team composition / IP ownership",
            "Sector concerns (some sectors face heightened scrutiny — e.g. property, restaurants without unique IP)",
            "Endorsement expired (3-month validity)",
            "TB test missing or non-IOM clinic",
        ],
        "success_tips": [
            "Innovation must be GENUINE — endorsing bodies reject generic businesses (cafés, salons, generic e-commerce)",
            "Choose endorsing body matching your sector (tech, social enterprise, deep tech, fintech)",
            "Develop business plan to investor-grade quality — pitch deck + financial model + market research",
            "Demonstrate strong founder track record relevant to the business",
            "B2 English ahead of time — don't wait till visa application",
            "Document EVERY milestone — endorsement body's 12 + 24 month checks rely on growth evidence",
            "Plan for 3-year journey: visa → business establishment → milestones → ILR",
            "Endorsing body fees vary £3,000-£10,000 — budget upfront",
        ],
        "faqs": [
            {"q": "What's changed from old Innovator Visa?", "a": "April 2023 reform: (a) NO minimum £50,000 investment requirement, (b) Focus shifted from financial threshold to genuine innovation, (c) Endorsing bodies have more discretion, (d) Single Innovator Founder route replaces previous Innovator + Start-up split."},
            {"q": "Do I need investors?", "a": "No — there's NO minimum investment requirement. However, endorsing body may consider funding adequacy as part of viability assessment. Self-funded + endorsed is fully acceptable."},
            {"q": "How do I find an endorsing body?", "a": "Full list at gov.uk/innovator-founder-visa. Major ones: Tech Nation Alumni (Endeavor), Founders Forum Group, Envestors, Innovation Norway, RKK Innovation Centre, Coadec. Each has specific focus areas + fees."},
            {"q": "Can my family come with me?", "a": "Yes — spouse + dependent children can come as dependants. Spouse gets open work rights (full employment freedom). Children attend UK schools."},
            {"q": "What if my business fails or pivots?", "a": "Endorsing body conducts 12 + 24 month checks. Significant pivot OR failure may trigger withdrawal of endorsement, ending visa. Communicate proactively with endorsing body about changes."},
            {"q": "When can I apply for ILR?", "a": "After 3 years if business meets growth milestones (revenue, jobs, investment etc.). If milestones not met, can apply for visa extension instead — keeps you in UK while business develops."},
        ],
        "official_url": "https://www.gov.uk/innovator-founder-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/",
        "source_urls": [
            "https://www.gov.uk/innovator-founder-visa",
            "https://www.gov.uk/government/publications/innovator-founder-and-scale-up-visa-endorsing-bodies",
            "https://www.gov.uk/government/publications/immigration-rules/immigration-rules-appendix-innovator-founder",
            "https://www.gov.uk/innovator-founder-visa/eligibility",
        ],
        "verified_notes": "Manual Fast-Path B.2 seed — verified against gov.uk on 2026-02-27. £0 minimum investment per April 2023 reform replacing old Innovator Visa £50,000 threshold. Endorsing body list per current UKVI publication.",
    },
]


ALL_WORKFLOWS: Dict[str, List[Dict[str, Any]]] = {
    "AU": AUSTRALIA_WORKFLOWS,
    "CA": CANADA_WORKFLOWS,
    "NZ": NEW_ZEALAND_WORKFLOWS,
    "UK": UNITED_KINGDOM_WORKFLOWS,
}


# ──────────────────────────────────────────────────────────────────────────────
# Seeder
# ──────────────────────────────────────────────────────────────────────────────
async def seed_country(db, country_code: str, seeded_by_id: str, seeded_by_name: str, verbose: bool = True, sweep_label: str = "b2") -> Dict[str, int]:
    """Idempotent seeder for a single country.

    Skips workflows where (country_code, subclass_id, service_type) already exists
    in `verified` state. Inserts new workflows directly with status='verified'.

    Args:
        sweep_label: Audit log action suffix. Defaults to 'b2' (used by Sweep B.2 AU/CA/NZ/UK).
                     Pass 'b4' for B.4 sub-slices (India + AU expansion + future).
    """
    workflows = ALL_WORKFLOWS.get(country_code.upper(), [])
    if not workflows:
        if verbose:
            print(f"[{country_code}] No seed data defined yet.")
        return {"inserted": 0, "skipped": 0, "errored": 0}

    workflows_col = db["country_visa_workflows"]
    audit_logs_col = db["audit_logs"]

    inserted = 0
    skipped = 0
    errored = 0

    for wf in workflows:
        cc = wf["country_code"]
        sid = wf["subclass_id"]
        svc = wf["service_type"]
        existing = await workflows_col.find_one(
            {"country_code": cc, "subclass_id": sid, "service_type": svc, "status": "verified"},
            {"_id": 0, "workflow_id": 1, "subclass_name": 1},
        )
        if existing:
            if verbose:
                print(f"[{cc}] ⏭  SKIP {sid} ({existing.get('subclass_name')}) — already verified ({existing.get('workflow_id')[:8]}..)")
            skipped += 1
            continue

        try:
            workflow_id = str(uuid.uuid4())
            now = now_iso()
            doc = {**wf}
            # Fix 3 — Enrich document_checklist with stable doc_id per item
            enriched_docs = []
            for idx, d in enumerate(doc.get("document_checklist", []) or [], start=1):
                d_copy = {**d}
                if not d_copy.get("doc_id"):
                    d_copy["doc_id"] = f"{cc}-{sid}-DOC-{idx:02d}"
                enriched_docs.append(d_copy)
            doc["document_checklist"] = enriched_docs

            doc.update({
                "workflow_id": workflow_id,
                "version": 1,
                "status": "verified",
                "verified_by": seeded_by_id,
                "verified_by_name": seeded_by_name,
                "verified_at": now,
                "source_verified_at": now,
                "created_at": now,
                "created_by": seeded_by_id,
                "created_by_name": seeded_by_name,
                "updated_at": now,
                "updated_by": seeded_by_id,
                "updated_by_name": seeded_by_name,
            })
            await workflows_col.insert_one(doc)
            # Fix 1 — Central audit log using CANONICAL schema (matches core.services.log_activity)
            await audit_logs_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": seeded_by_id,
                "user_name": seeded_by_name,
                "action": f"country_workflow_seeded_{sweep_label}",
                "entity_type": "country_visa_workflow",
                "entity_id": workflow_id,
                "details": f"{cc} {sid} {svc} — {wf['subclass_name']} (Manual Fast-Path {sweep_label.upper()})",
                "old_value": None,
                "new_value": None,
                "case_id": None,
                "client_name": None,
                "created_at": datetime.now(timezone.utc),
            })
            inserted += 1
            if verbose:
                print(f"[{cc}] ✅ INSERT {sid} — {wf['subclass_name']} (workflow_id={workflow_id[:8]}..)")
        except Exception as e:
            errored += 1
            print(f"[{cc}] ❌ ERROR seeding {sid}: {type(e).__name__}: {e}")

    return {"inserted": inserted, "skipped": skipped, "errored": errored}


async def backfill_country(db, country_code: str, seeded_by_id: str, seeded_by_name: str) -> Dict[str, int]:
    """One-shot backfill for already-seeded workflows.

    1. For each existing verified workflow in country, add `doc_id` field on
       every document_checklist entry that is missing it.
    2. Find audit_logs entries with `action="country_workflow_seeded_b2"` that
       use the OLD divergent schema (target_id / actor_id / timestamp) and
       rewrite them to the canonical schema (entity_id / user_id / created_at).
    """
    cc = country_code.upper()
    workflows_col = db["country_visa_workflows"]
    audit_logs_col = db["audit_logs"]

    docs_patched = 0
    audit_patched = 0

    # 1. Patch document_checklist[].doc_id on existing workflows
    cursor = workflows_col.find({"country_code": cc, "status": "verified"}, {"_id": 0})
    async for wf in cursor:
        sid = wf.get("subclass_id")
        docs = wf.get("document_checklist", []) or []
        changed = False
        enriched = []
        for idx, d in enumerate(docs, start=1):
            d_copy = {**d}
            if not d_copy.get("doc_id"):
                d_copy["doc_id"] = f"{cc}-{sid}-DOC-{idx:02d}"
                changed = True
            enriched.append(d_copy)
        if changed:
            await workflows_col.update_one(
                {"workflow_id": wf["workflow_id"]},
                {"$set": {"document_checklist": enriched, "updated_at": now_iso()}},
            )
            docs_patched += 1
            print(f"[{cc}] 📎 doc_id added to {len(enriched)} docs on {sid} ({wf['workflow_id'][:8]}..)")

    # 2. Rewrite legacy audit_logs entries to canonical schema
    legacy_cursor = audit_logs_col.find({
        "action": "country_workflow_seeded_b2",
        "$or": [{"entity_id": {"$exists": False}}, {"entity_id": None}],
    })
    async for entry in legacy_cursor:
        details_text = entry.get("details", "") or ""
        # details format: "AU 189 pr — ..."
        parts = details_text.split(maxsplit=3)
        if len(parts) < 3 or parts[0].upper() != cc:
            continue
        wf_cc = parts[0].upper()
        wf_sid = parts[1]
        wf_svc = parts[2]
        # Find matching workflow
        wf = await workflows_col.find_one(
            {"country_code": wf_cc, "subclass_id": wf_sid, "service_type": wf_svc, "status": "verified"},
            {"_id": 0, "workflow_id": 1},
        )
        if not wf:
            continue
        # Build canonical fields, preserve timestamp if available
        legacy_ts = entry.get("timestamp")
        created_at_val: Any
        if isinstance(legacy_ts, str):
            try:
                created_at_val = datetime.fromisoformat(legacy_ts.replace("Z", "+00:00"))
            except Exception:
                created_at_val = datetime.now(timezone.utc)
        elif isinstance(legacy_ts, datetime):
            created_at_val = legacy_ts
        else:
            created_at_val = datetime.now(timezone.utc)

        # Pull legacy actor fields with fallback
        legacy_actor_id = entry.get("actor_id") or seeded_by_id
        legacy_actor_name = entry.get("actor_name") or seeded_by_name

        await audit_logs_col.update_one(
            {"id": entry["id"]} if entry.get("id") else {"_id": entry["_id"]},
            {
                "$set": {
                    "user_id": legacy_actor_id,
                    "user_name": legacy_actor_name,
                    "entity_type": "country_visa_workflow",
                    "entity_id": wf["workflow_id"],
                    "created_at": created_at_val,
                    "old_value": None,
                    "new_value": None,
                    "case_id": None,
                    "client_name": None,
                },
                "$unset": {"actor_id": "", "actor_name": "", "target_id": "", "target_type": "", "timestamp": ""},
            },
        )
        audit_patched += 1
        print(f"[{cc}] 🧾 audit_log rewritten for {wf_sid} → entity_id={wf['workflow_id'][:8]}..")

    return {"docs_patched": docs_patched, "audit_patched": audit_patched}


async def main():
    parser = argparse.ArgumentParser(description="Sweep B.2 Manual Fast-Path country workflow seeder")
    parser.add_argument("--country", type=str, default=None, help="ISO-2 country code to seed (e.g. AU). Omit for --all")
    parser.add_argument("--all", action="store_true", help="Seed all countries currently defined")
    parser.add_argument("--backfill", type=str, default=None, help="One-shot backfill: add doc_id + rewrite legacy audit_logs for given ISO-2 code")
    args = parser.parse_args()

    load_dotenv()
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # Use the admin user as the seeding actor
    admin = await db.users.find_one({"email": "admin@leamss.com"}, {"_id": 0, "id": 1, "name": 1})
    if not admin:
        print("❌ Admin user not found — cannot seed (verified_by would be null).")
        return
    seeded_by_id = admin["id"]
    seeded_by_name = admin.get("name", "Admin User")

    # ── BACKFILL MODE ─────────────────────────────────────────────────────────
    if args.backfill:
        cc = args.backfill.upper()
        print(f"\n══════════════════════════════════════════════")
        print(f"  BACKFILL {cc} — doc_id + canonical audit_logs")
        print(f"══════════════════════════════════════════════")
        res = await backfill_country(db, cc, seeded_by_id, seeded_by_name)
        print(f"[{cc}] Backfill summary: docs_patched={res['docs_patched']} audit_patched={res['audit_patched']}")
        return

    # ── SEED MODE ─────────────────────────────────────────────────────────────
    targets: List[str] = []
    if args.country:
        targets = [args.country.upper()]
    elif args.all:
        targets = list(ALL_WORKFLOWS.keys())
    else:
        print("⚠  Specify --country <ISO2> or --all (or --backfill <ISO2>).")
        return

    totals = {"inserted": 0, "skipped": 0, "errored": 0}
    for cc in targets:
        print(f"\n══════════════════════════════════════════════")
        print(f"  SEEDING {cc} — {len(ALL_WORKFLOWS.get(cc, []))} workflows")
        print(f"══════════════════════════════════════════════")
        res = await seed_country(db, cc, seeded_by_id, seeded_by_name)
        totals["inserted"] += res["inserted"]
        totals["skipped"] += res["skipped"]
        totals["errored"] += res["errored"]
        print(f"[{cc}] Summary: inserted={res['inserted']} skipped={res['skipped']} errored={res['errored']}")

    print(f"\n══════════════════════════════════════════════")
    print(f"  TOTAL: inserted={totals['inserted']} skipped={totals['skipped']} errored={totals['errored']}")
    print(f"══════════════════════════════════════════════\n")


if __name__ == "__main__":
    asyncio.run(main())
