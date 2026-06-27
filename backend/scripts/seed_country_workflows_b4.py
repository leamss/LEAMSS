"""Sweep B.4 — Mega Dispatch country workflow seeder (India + expansions).

Sub-Slice B.4.2 — India NEW (12 visas).
Sub-Slices B.4.3..9 to be added incrementally per Sir's Atomic Ship dispatch.

Idempotent — skips if a workflow with same (country_code, subclass_id, service_type)
already exists with status='verified'. Reuses `seed_country` and `backfill_country`
from b2 to avoid duplication.

Usage:
    cd /app/backend && python -m scripts.seed_country_workflows_b4 --country IN
    cd /app/backend && python -m scripts.seed_country_workflows_b4 --backfill IN

Sources cited per workflow in `verified_notes`. Fees verified against MHA + Indian
Embassy USA + Consulate fee schedules and indianvisaonline.gov.in as of Feb 2026.
FX: 1 USD ≈ 83 INR (Feb 2026 indicative).
"""
from __future__ import annotations
import argparse
import asyncio
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Reuse B.2 helpers — same idempotency + audit_log canonical schema
from scripts.seed_country_workflows_b2 import seed_country, backfill_country, now_iso  # noqa: F401


# ──────────────────────────────────────────────────────────────────────────────
# INDIA (IN) — 12 verified visas
# Sources: mha.gov.in, indianvisaonline.gov.in, indianembassyusa.gov.in,
#          cgimilan.gov.in, hcikl.gov.in, ociservices.gov.in
# FX: 1 USD ≈ 83 INR · 1 EUR ≈ 90 INR · 1 GBP ≈ 105 INR (Feb 2026 indicative)
# ──────────────────────────────────────────────────────────────────────────────
INDIA_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. IN-OCI — Overseas Citizen of India Card ─────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "OCI",
        "subclass_name": "Overseas Citizen of India Card (OCI)",
        "service_type": "oci",
        "category": "immigration",
        "description": (
            "The Overseas Citizen of India (OCI) Card is a lifelong multi-entry visa for foreign "
            "nationals of Indian origin (and certain spouses). OCI cardholders enjoy parity with "
            "NRIs in economic, financial, and educational fields (except agricultural land "
            "purchase), visa-free travel to India for life, and no requirement to register with "
            "FRRO regardless of length of stay.\n\n"
            "OCI replaced the older PIO card scheme in 2015 — existing PIO holders are deemed OCI "
            "holders and can update their records. Note: OCI is NOT dual citizenship — it does not "
            "confer voting rights, parliamentary office, or constitutional posts."
        ),
        "eligibility_summary": (
            "Foreign nationals who: (a) were Indian citizens on or after 26-Jan-1950, OR (b) were "
            "eligible to become Indian citizens on 26-Jan-1950, OR (c) belonged to a territory that "
            "became part of India after 15-Aug-1947, OR (d) are children/grandchildren/great-"
            "grandchildren of such persons. Spouses of Indian citizens or OCI holders married 2+ "
            "years are also eligible. Pakistani and Bangladeshi nationals are ineligible."
        ),
        "eligibility_criteria": [
            {"label": "Origin requirement", "value": "Indian origin up to 4 generations OR spouse of citizen/OCI (married 2+ years)", "notes": "Documentary proof required (parents/grandparents passport, birth cert)"},
            {"label": "Current citizenship", "value": "Foreign national (any country except Pakistan/Bangladesh)", "notes": "Must surrender Indian passport if previously Indian"},
            {"label": "Spouse pathway", "value": "Married to Indian citizen / OCI holder for 2+ years", "notes": "Continuing/genuine marriage; cohabitation evidence may be requested"},
            {"label": "Children of OCI parents", "value": "Eligible if at least one parent is OCI / former Indian citizen", "notes": "Minor children: separate application + parental consent"},
            {"label": "Surrender of Indian passport", "value": "Mandatory for former Indian citizens BEFORE OCI application", "notes": "Surrender Certificate from Indian Mission required"},
            {"label": "Exclusions", "value": "Pakistani / Bangladeshi nationals; service in foreign military", "notes": "Hard bar — no discretion"},
            {"label": "Re-issuance triggers", "value": "Mandatory at age 20 (new biometrics) and on every new passport", "notes": "Late update fee applies if not done within 3 months of new passport"},
            {"label": "Background", "value": "No serious criminal record / activities against India", "notes": "MHA security clearance"},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 275,
        "fees_inr_approx": 22825,
        "fees_breakdown": [
            {"component": "OCI Fresh Application (adults & minors abroad)", "amount": 275, "currency": "USD"},
            {"component": "ICWF (Indian Community Welfare Fund) — mandatory", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee (USA / approved centres)", "amount": 19, "currency": "USD"},
            {"component": "Re-issuance at age 20 / details change", "amount": 25, "currency": "USD"},
            {"component": "Late update fee (passport not updated within 3 months)", "amount": 25, "currency": "USD"},
            {"component": "Lost/damaged card re-issuance", "amount": 100, "currency": "USD"},
            {"component": "OCI application within India (Bureau of Immigration)", "amount": 15000, "currency": "INR"},
            {"component": "Renunciation of OCI", "amount": 25, "currency": "USD"},
        ],
        "processing_time_days_min": 30,
        "processing_time_days_max": 90,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Eligibility + Gather Indian Origin Proof", "description": "Collect documents proving Indian origin: parents/grandparents/great-grandparents' Indian passport, birth certificate, naturalization documents.", "estimated_days": 14, "documents_needed": ["Parent's/grandparent's Indian passport (front+back)", "Birth certificate (self)", "Birth certificate (parent linking to India)", "Marriage certificate (if spouse pathway)"], "tips": ["Apostille / notarise foreign documents", "Establish unbroken family chain back to Indian origin"]},
            {"step_number": 2, "title": "Surrender Indian Passport (if applicable)", "description": "Former Indian citizens MUST surrender Indian passport at the Indian Mission and obtain a Surrender Certificate BEFORE applying for OCI.", "estimated_days": 21, "documents_needed": ["Indian passport (original)", "Foreign naturalization certificate", "Surrender Form"], "tips": ["Surrender fee: USD 175 for those who naturalized after 1 Jun 2010, USD 20 before", "Without surrender certificate, OCI application is rejected"]},
            {"step_number": 3, "title": "Online Application at ociservices.gov.in", "description": "Fill Part A (online form) and Part B (uploaded documents). System assigns a File Reference Number (FRN).", "estimated_days": 3, "documents_needed": ["Recent photo (digital, 200x200 px, white background)", "Signature image", "All scanned documents"], "tips": ["Use original spelling exactly as on passports", "Save the FRN — needed for status enquiry"]},
            {"step_number": 4, "title": "Print + Sign Application + Schedule VFS Appointment", "description": "Print application, sign in correct places, book VFS Global appointment (or visit Indian Mission directly).", "estimated_days": 7, "documents_needed": ["Signed Part A + Part B printouts", "Appointment confirmation"], "tips": ["VFS slots can be limited — book early", "Bring originals + 2 sets of photocopies"]},
            {"step_number": 5, "title": "Document Submission at VFS / Mission", "description": "Submit application package, biometrics (if required), pay all fees. Get acknowledgement slip with tracking number.", "estimated_days": 1, "documents_needed": ["Full application package (originals + copies)", "Passport size photos (4)", "Self-addressed prepaid return envelope"], "tips": ["Carry payment by card/money order (no personal cheques)", "Track via VFS portal + ociservices.gov.in"]},
            {"step_number": 6, "title": "MHA Background Verification", "description": "Application sent to MHA (Ministry of Home Affairs), New Delhi for security clearance. This is the longest phase.", "estimated_days": 45, "documents_needed": [], "tips": ["No applicant action — automated/back-office", "Status visible online via FRN"]},
            {"step_number": 7, "title": "Card Printing + Dispatch", "description": "On approval, OCI card and 'U' visa sticker printed in India and dispatched back to applicant's mission/VFS for collection.", "estimated_days": 21, "documents_needed": [], "tips": ["Pickup or postal return based on application option", "Verify name spelling on receipt — corrections need re-issuance"]},
        ],
        "document_checklist": [
            {"name": "Foreign passport (bio page + visa page) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Recent photo (51mm x 51mm, white background)", "mandatory": True, "notes": "2 hard copies + digital upload"},
            {"name": "Signature image (white background)", "mandatory": True, "notes": ""},
            {"name": "Indian origin proof — parent's/grandparent's Indian passport", "mandatory": True, "notes": "If applying via origin pathway"},
            {"name": "Birth certificate of applicant", "mandatory": True, "notes": "Apostilled if foreign"},
            {"name": "Birth certificate establishing parent's Indian origin", "mandatory": True, "notes": "For multi-generation pathway"},
            {"name": "Marriage certificate (if spouse pathway)", "mandatory": True, "notes": "Apostilled; 2+ years marriage required"},
            {"name": "Spouse's Indian/OCI passport copy (if spouse pathway)", "mandatory": True, "notes": ""},
            {"name": "Renunciation/Surrender Certificate of Indian Citizenship", "mandatory": True, "notes": "Mandatory if applicant was previously Indian"},
            {"name": "Naturalization Certificate (current citizenship)", "mandatory": True, "notes": "From the country whose passport is held"},
            {"name": "Address proof (utility bill / driver's license / lease)", "mandatory": True, "notes": "Current residential address"},
            {"name": "Old PIO card (if applicable)", "mandatory": False, "notes": "PIO holders converting to OCI"},
            {"name": "Parental consent + ID (for minor applicants)", "mandatory": True, "notes": "Required for applicants under 18"},
            {"name": "Self-addressed prepaid return envelope (USPS / equivalent)", "mandatory": True, "notes": "For postal return of OCI card"},
        ],
        "common_rejection_reasons": [
            "Failure to surrender Indian passport before applying (former Indian citizens)",
            "Discrepancy in name/DOB between documents",
            "Missing apostille on foreign-issued documents",
            "Insufficient proof of Indian origin (broken family chain)",
            "Pakistani/Bangladeshi nationality (absolute bar)",
            "Past travel to/affiliation with restricted regions",
            "Marriage <2 years for spouse pathway (premature application)",
            "Poor quality photo not meeting biometric specs",
        ],
        "success_tips": [
            "Surrender Indian passport WELL before applying for OCI — adds 3-4 weeks if done together",
            "Use exact name spelling across ALL documents (passport, marriage, birth)",
            "Apostille foreign documents through the Hague Convention process (not just notary)",
            "Keep digital + hard copies of every document — VFS sometimes requests duplicates",
            "Update OCI within 3 months of getting new passport to avoid USD 25 late fee",
            "Book VFS appointment 4-6 weeks in advance — popular centres book out",
            "Track status weekly via FRN — early follow-up resolves issues faster",
            "OCI card 'U' visa sticker must be affixed in current passport for entry",
        ],
        "faqs": [
            {"q": "Is OCI dual citizenship?", "a": "NO. OCI is a multi-entry visa with NRI-like rights. It does NOT confer voting rights, ability to hold constitutional/parliamentary office, or buy agricultural land. You must travel on the foreign passport."},
            {"q": "Do I need to renew OCI?", "a": "OCI is lifelong. Mandatory re-issuance only at age 20 (one-time, for new biometrics) and on every new passport. The card itself doesn't expire."},
            {"q": "Can my non-Indian-origin spouse get OCI?", "a": "Yes — spouses of Indian citizens or OCI holders are eligible after 2+ years of continuing marriage. Apply through the spouse pathway with marriage certificate."},
            {"q": "What if I'm a Pakistani or Bangladeshi national?", "a": "Pakistani and Bangladeshi nationals (or those whose parents/grandparents held those citizenships) are NOT eligible for OCI. No exceptions."},
            {"q": "Do I need to register with FRRO?", "a": "NO. OCI holders are exempt from FRRO registration regardless of length of stay in India."},
            {"q": "Can OCI holders work in India?", "a": "Yes — full work rights including employment, business, and professional practice (with exceptions like CA, advocacy in courts above district level)."},
            {"q": "What happens to PIO cardholders?", "a": "PIO scheme was discontinued in 2015. Existing PIO cards remain valid as deemed OCI cards. Holders should apply for OCI conversion using the PIO-to-OCI online form."},
        ],
        "official_url": "https://ociservices.gov.in",
        "vfs_url": "https://services.vfsglobal.com/usa/en/ind/apply-oci-services",
        "source_urls": [
            "https://ociservices.gov.in",
            "https://www.mha.gov.in/PDF_Other/OCIregistrationfee_25042017.pdf",
            "https://www.indianembassyusa.gov.in/pages/NjI,",
            "https://services.vfsglobal.com/one-pager/india/united-states-of-america/oci-services/",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against ociservices.gov.in + mha.gov.in + indianembassyusa.gov.in on 2026-02-27. Fee USD 275 effective Apr 2026 hike. ICWF + VFS surcharges per US Mission notice.",
    },

    # ── 2. IN-PIO — Person of Indian Origin (Legacy / Conversion to OCI) ───────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "PIO",
        "subclass_name": "Person of Indian Origin Card (PIO — Legacy / Convert to OCI)",
        "service_type": "pio",
        "category": "immigration",
        "description": (
            "The Person of Indian Origin (PIO) Card scheme was DISCONTINUED on 9-Jan-2015 and merged "
            "into the OCI scheme. Existing PIO cards are deemed equivalent to OCI cards and remain "
            "valid until the underlying passport expires. However, PIO holders MUST convert to "
            "lifelong OCI cards (currently FREE of cost until further notice) for continued use.\n\n"
            "Conversion to OCI preserves all PIO benefits while adding lifelong validity, FRRO "
            "registration exemption, and no need to carry the booklet-style PIO card. The 'U' visa "
            "sticker is issued in the current passport."
        ),
        "eligibility_summary": (
            "Holders of valid PIO cards issued before 9-Jan-2015. Converting to OCI uses the same "
            "Indian-origin eligibility criteria as fresh OCI applications, but PIO conversion is "
            "fast-tracked since origin is already verified."
        ),
        "eligibility_criteria": [
            {"label": "Existing PIO card", "value": "PIO card issued before 9-Jan-2015", "notes": "Booklet-style, valid until current passport expires"},
            {"label": "Indian origin proof", "value": "Same documents as original PIO issuance", "notes": "Re-submitted; MHA verifies via FRN linkage"},
            {"label": "Current passport", "value": "Valid foreign passport (6+ months)", "notes": "OCI 'U' sticker affixed to current passport"},
            {"label": "Pakistani/Bangladeshi exclusion", "value": "PIO holders of those origins ineligible for OCI", "notes": "Hard bar"},
            {"label": "No fees (currently)", "value": "PIO-to-OCI conversion is FREE", "notes": "MHA may impose nominal processing fee in future"},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 0,
        "fees_inr_approx": 0,
        "fees_breakdown": [
            {"component": "PIO-to-OCI conversion application", "amount": 0, "currency": "USD"},
            {"component": "ICWF (Indian Community Welfare Fund)", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee", "amount": 19, "currency": "USD"},
            {"component": "Document apostille / notarisation (if updates required)", "amount": 2000, "currency": "INR"},
        ],
        "processing_time_days_min": 21,
        "processing_time_days_max": 60,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm PIO Card Validity", "description": "Verify your existing PIO card is genuine and the passport it was issued against is still in your possession.", "estimated_days": 1, "documents_needed": ["Existing PIO card", "Passport from PIO issuance"], "tips": ["If lost, file police report before applying for OCI"]},
            {"step_number": 2, "title": "Online PIO-to-OCI Form at ociservices.gov.in", "description": "Use the dedicated PIO-to-OCI conversion form (Part A). Most details auto-populate from PIO records.", "estimated_days": 1, "documents_needed": ["PIO card details", "Recent photo", "Signature image"], "tips": ["Same online portal as fresh OCI", "Save FRN for status tracking"]},
            {"step_number": 3, "title": "Upload Documents (Part B)", "description": "Upload current passport bio page, PIO card scan, recent photo. Original Indian-origin documents typically NOT re-required.", "estimated_days": 1, "documents_needed": ["Current passport scan", "PIO card scan", "Photo + signature"], "tips": ["File size limits apply — see portal"]},
            {"step_number": 4, "title": "VFS Appointment + Submission", "description": "Submit application package at VFS / Indian Mission. Free of cost for conversion (only VFS + ICWF surcharges).", "estimated_days": 7, "documents_needed": ["Signed application", "Original PIO card", "Current passport"], "tips": ["Original PIO card may be retained at submission and returned with OCI"]},
            {"step_number": 5, "title": "MHA Processing", "description": "Fast-tracked verification since PIO origin already authenticated. Typically 3-4 weeks.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 6, "title": "OCI Card + 'U' Visa Sticker Issued", "description": "OCI card dispatched; 'U' visa sticker affixed in current passport.", "estimated_days": 14, "documents_needed": [], "tips": ["Old PIO card surrendered to mission", "OCI is now lifelong"]},
        ],
        "document_checklist": [
            {"name": "Existing PIO card (original)", "mandatory": True, "notes": "Surrendered at submission"},
            {"name": "Current foreign passport (bio page + visa pages)", "mandatory": True, "notes": "OCI sticker affixed here"},
            {"name": "Recent passport-size photograph (51x51mm white bg)", "mandatory": True, "notes": ""},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Address proof (current)", "mandatory": True, "notes": ""},
            {"name": "Marriage certificate (if PIO via spouse)", "mandatory": False, "notes": ""},
            {"name": "Naturalization certificate", "mandatory": False, "notes": "If applicable"},
        ],
        "common_rejection_reasons": [
            "PIO card lost / damaged without police report",
            "Major discrepancy between PIO records and current details",
            "Applicant is now Pakistani / Bangladeshi national (absolute bar)",
            "Adverse security check arising during MHA verification",
        ],
        "success_tips": [
            "Apply for PIO-to-OCI conversion BEFORE travelling to India — the OCI 'U' sticker is needed in current passport",
            "Keep your PIO card safe until conversion is complete — it remains valid as deemed-OCI during transit",
            "Conversion remains free of cost at the time of writing — check ociservices.gov.in for any fee notification",
            "If PIO card is lost, lodge a police report immediately and follow lost-card OCI re-issuance route (USD 100)",
        ],
        "faqs": [
            {"q": "Is my PIO card still valid?", "a": "Yes — PIO cards issued before 9-Jan-2015 are deemed OCI cards and remain valid until the passport they were issued against expires. However, MHA strongly recommends conversion to OCI for lifelong validity."},
            {"q": "Why convert if PIO is deemed OCI?", "a": "OCI is lifelong (no passport-tied expiry), FRRO-exempt, and provides modern biometric records. PIO booklets are gradually being phased out at ports of entry."},
            {"q": "Do I need fresh Indian-origin documents?", "a": "Usually NO — MHA references the existing PIO record. Only current passport + photo + signature are mandatory. Some missions may request supplementary documents."},
            {"q": "How long does conversion take?", "a": "Typically 3-8 weeks — much faster than fresh OCI applications (45-90 days) due to pre-verified origin."},
        ],
        "official_url": "https://ociservices.gov.in/welcome",
        "vfs_url": "https://services.vfsglobal.com/usa/en/ind/apply-oci-services",
        "source_urls": [
            "https://ociservices.gov.in/welcome",
            "https://www.mha.gov.in/PDF_Other/PIOOCIMerger_09012015.pdf",
            "https://www.indianembassyusa.gov.in/pages/NjI,",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against MHA PIO-OCI merger notification dated 09-Jan-2015 + ociservices.gov.in (current). Conversion fee waiver in effect at time of writing.",
    },

    # ── 3. IN-EMP — Employment Visa (E) ─────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "EMP",
        "subclass_name": "Employment Visa (E)",
        "service_type": "work",
        "category": "immigration",
        "description": (
            "The Employment (E) Visa is for highly skilled foreign professionals taking up employment "
            "with an Indian company or organisation. Minimum drawn salary threshold is USD 25,000 "
            "per annum (with limited exceptions for non-profits, NGOs, and ethnic cuisine chefs). "
            "Initial visa duration matches contract length up to a maximum of 5 years (renewable in "
            "India via FRRO).\n\n"
            "Employment Visa holders staying 180+ days MUST register with the FRRO (Foreigners "
            "Regional Registration Office) within 14 days of arrival. The visa is single-employer "
            "tied; changing employers requires fresh approval."
        ),
        "eligibility_summary": (
            "Skilled professional with confirmed employment offer from Indian entity, drawing minimum "
            "USD 25,000 p.a. (some exemptions). Occupation should be highly skilled and not capable "
            "of being filled by Indian nationals. Tax-paying obligations apply."
        ),
        "eligibility_criteria": [
            {"label": "Indian employer", "value": "Registered Indian company / organisation with valid contract offer", "notes": "Public/private sector both eligible"},
            {"label": "Minimum salary", "value": "USD 25,000 per annum (gross)", "notes": "Exceptions: NGOs, ethnic chefs, language teachers, embassies, missionaries"},
            {"label": "Skilled position", "value": "Position cannot be easily filled by Indian national", "notes": "Senior management, technical experts, consultants typical"},
            {"label": "Sponsor commitment", "value": "Employer letter on letterhead + contract + payroll commitment", "notes": "Indian employer is co-sponsor"},
            {"label": "Tax obligation", "value": "Visa holder subject to Indian income tax", "notes": "PAN card mandatory; TDS by employer"},
            {"label": "Health insurance", "value": "Health coverage during stay", "notes": "Employer-provided or independent policy"},
            {"label": "FRRO registration", "value": "Mandatory within 14 days if staying 180+ days", "notes": "Renewable annually at FRRO"},
            {"label": "Police verification", "value": "PCC from home country (and other countries of residence)", "notes": "Within 6 months of application"},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 250,
        "fees_inr_approx": 20750,
        "fees_breakdown": [
            {"component": "Employment Visa — up to 6 months (single/multiple entry)", "amount": 100, "currency": "USD"},
            {"component": "Employment Visa — 6 months to 1 year (multiple entry)", "amount": 180, "currency": "USD"},
            {"component": "Employment Visa — 1 to 5 years (multiple entry)", "amount": 250, "currency": "USD"},
            {"component": "ICWF surcharge", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee", "amount": 19, "currency": "USD"},
            {"component": "Bank transaction charge (2.5% of fee)", "amount": 7, "currency": "USD"},
            {"component": "FRRO registration fee (within India)", "amount": 0, "currency": "INR"},
            {"component": "PCC from home country (variable)", "amount": 50, "currency": "USD"},
        ],
        "processing_time_days_min": 14,
        "processing_time_days_max": 30,
        "step_by_step": [
            {"step_number": 1, "title": "Receive Job Offer from Indian Employer", "description": "Confirm written employment offer, salary (≥USD 25k p.a.), role description, start date.", "estimated_days": 14, "documents_needed": ["Employment offer letter", "Employment contract", "Job description"], "tips": ["Verify employer's GST registration + financial standing", "Lock salary clearly in contract (not 'as per company policy')"]},
            {"step_number": 2, "title": "Employer Sponsor Documents", "description": "Employer issues sponsor letter on letterhead, attaches company incorporation docs, GST registration, IT returns, and undertaking on labour-law compliance.", "estimated_days": 7, "documents_needed": ["Sponsor letter", "Certificate of Incorporation", "GST certificate", "Last 2 years' IT returns"], "tips": ["Sponsor letter must explicitly mention salary, role, duration", "Employer absorbs PCC + medical examination costs typically"]},
            {"step_number": 3, "title": "Online Application at indianvisaonline.gov.in", "description": "Fill complete application, upload photo + signature + supporting documents. Generate File Reference Number.", "estimated_days": 1, "documents_needed": ["Passport bio page", "Photo (2x2 inch white bg)", "Signature image"], "tips": ["Use exact name as on passport", "Multiple categories — choose 'Employment'"]},
            {"step_number": 4, "title": "Document Submission at Indian Mission / VFS", "description": "Submit physical application package, biometrics enrolment, pay all fees.", "estimated_days": 7, "documents_needed": ["Printed application", "Employer documents", "Educational + experience certificates", "PCC", "Health insurance"], "tips": ["Bring originals + 2 sets of photocopies", "Some missions require in-person interview"]},
            {"step_number": 5, "title": "Visa Processing + Issuance", "description": "Indian Mission processes (14-30 days typical). May refer to MHA for security clearance.", "estimated_days": 21, "documents_needed": [], "tips": ["Track via VFS portal", "Avoid travel during processing"]},
            {"step_number": 6, "title": "Travel to India + FRRO Registration", "description": "Arrive in India, register at FRRO within 14 days if stay exceeds 180 days. Renew annually at FRRO.", "estimated_days": 14, "documents_needed": ["Passport", "Visa", "Employer letter", "Address proof", "Health insurance"], "tips": ["FRRO has e-FRRO portal — minimal in-person visits", "Save FRRO certificate for visa renewals"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Passport-size photograph (51x51mm white background)", "mandatory": True, "notes": "2 hard copies"},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Employment offer letter (Indian employer)", "mandatory": True, "notes": "On letterhead, signed by authorised signatory"},
            {"name": "Employment contract (signed)", "mandatory": True, "notes": "Salary, role, duration"},
            {"name": "Sponsor letter from Indian employer", "mandatory": True, "notes": "On letterhead"},
            {"name": "Indian employer's Certificate of Incorporation", "mandatory": True, "notes": ""},
            {"name": "Indian employer's GST registration", "mandatory": True, "notes": ""},
            {"name": "Indian employer's last 2 years' IT returns", "mandatory": True, "notes": ""},
            {"name": "Educational qualifications (degrees, transcripts)", "mandatory": True, "notes": "Apostilled"},
            {"name": "CV / Resume", "mandatory": True, "notes": "Detailed with relevant experience"},
            {"name": "Police Clearance Certificate (PCC) from home country", "mandatory": True, "notes": "Within 6 months"},
            {"name": "Health insurance policy", "mandatory": True, "notes": "Covering India stay"},
            {"name": "Address proof (current)", "mandatory": True, "notes": ""},
            {"name": "Yellow fever vaccination certificate (if from endemic country)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Salary offered below USD 25,000 p.a. threshold (without applicable exemption)",
            "Position appears low-skilled / fillable by Indian nationals",
            "Employer financial standing weak (low GST returns, insolvency signs)",
            "Inconsistencies between contract, sponsor letter, and online application",
            "Missing apostille on educational documents",
            "PCC not submitted or older than 6 months",
            "Applicant has prior visa cancellation / overstay in India",
        ],
        "success_tips": [
            "Have employer absorb all visa fees + PCC + health insurance — standard practice for senior hires",
            "Ensure salary mentioned in EVERY document is identical (USD 25k threshold strictly enforced)",
            "Apostille educational certificates from country of issue (not just notary)",
            "Plan PCC application 6 weeks ahead — Indian missions abroad take 4-8 weeks",
            "Register FRRO within 14 days of arrival to avoid penalty + cancellation risk",
            "Save copies of all visa application docs — needed at FRRO + future renewals",
            "Don't change employers without fresh visa application — single-employer tied",
        ],
        "faqs": [
            {"q": "Can my family come with me?", "a": "Yes — spouse + dependent children can apply for Entry (X) visa with co-terminus validity. Spouse does NOT get automatic work rights; needs own Employment Visa to work."},
            {"q": "Can I change employers?", "a": "Yes, but only with fresh Employment Visa approval. Cannot 'switch sponsor' on existing visa — requires re-application from scratch."},
            {"q": "What if my salary is below USD 25,000?", "a": "Strict bar except for: NGOs, ethnic cuisine chefs, language teachers (foreign-origin), missionary work, embassies, foreign government bodies. Document the exemption category clearly."},
            {"q": "Do I need to pay Indian taxes?", "a": "Yes — Employment Visa holders are subject to Indian income tax once they meet residency thresholds (typically 182+ days). PAN card mandatory. Employer deducts TDS."},
            {"q": "How do I extend my visa?", "a": "Approach FRRO 60 days before expiry with extension application + updated employer contract + payment of fees. Up to 5 years extension possible in stages."},
            {"q": "What about FRRO registration?", "a": "Mandatory within 14 days of arrival IF stay exceeds 180 days. Use e-FRRO portal (indianfrro.gov.in) — minimal in-person visits required."},
        ],
        "official_url": "https://indianvisaonline.gov.in/visa/visa-fee.html",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/visa/visa-fee.html",
            "https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf",
            "https://indianfrro.gov.in/eservices",
            "https://www.indianembassyusa.gov.in/extra?id=90",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in + MHA Annex III fee schedule on 2026-02-27. USD 25k salary threshold per current MHA instructions.",
    },

    # ── 4. IN-BUS — Business Visa (B) ───────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "BUS",
        "subclass_name": "Business Visa (B)",
        "service_type": "business",
        "category": "immigration",
        "description": (
            "The Business (B) Visa is for foreign nationals visiting India for commercial purposes "
            "such as meetings, conferences, exploring market opportunities, attending trade fairs, "
            "and short-term work that does NOT involve direct employment by an Indian entity. "
            "Available for 1, 5, and 10-year validity periods (multiple entry).\n\n"
            "Each stay is limited to 180 days (continuous). Business Visa does NOT permit direct "
            "employment — for employment, the E (Employment) Visa is required. Common uses include "
            "executive visits, project supervision, vendor/buyer meetings, and post-sale technical "
            "support."
        ),
        "eligibility_summary": (
            "Foreign business person with genuine commercial purpose in India — meetings, "
            "negotiations, market research, supervision, training. Must have demonstrable business "
            "ties (sponsoring Indian company OR overseas company with India business)."
        ),
        "eligibility_criteria": [
            {"label": "Business purpose", "value": "Genuine commercial reasons — meetings, conferences, vendor visits, training", "notes": "Cannot replace Employment Visa for direct employment"},
            {"label": "Indian sponsor / inviting entity", "value": "Indian company or organisation extends formal invitation", "notes": "Letter on letterhead + GST + IT returns"},
            {"label": "Overseas employer / business proof", "value": "Letter from foreign employer OR own company incorporation", "notes": "Establishes commercial standing"},
            {"label": "Financial means", "value": "Sufficient funds for stay (bank statements last 6 months)", "notes": "USD 5,000+ recommended"},
            {"label": "Maximum stay per visit", "value": "180 days continuous", "notes": "Exit and re-enter for further stays"},
            {"label": "Tax implication", "value": "180+ days continuous stay may trigger tax residency", "notes": "Plan exits accordingly"},
            {"label": "No employment", "value": "Cannot draw salary from Indian entity on B visa", "notes": "Switch to E visa if employed"},
            {"label": "Health insurance", "value": "Strongly recommended for stays >30 days", "notes": ""},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 160,
        "fees_inr_approx": 13280,
        "fees_breakdown": [
            {"component": "Business Visa — up to 1 year (multiple entry)", "amount": 160, "currency": "USD"},
            {"component": "Business Visa — up to 5 years (multiple entry)", "amount": 160, "currency": "USD"},
            {"component": "Business Visa — up to 10 years (multiple entry)", "amount": 160, "currency": "USD"},
            {"component": "ICWF surcharge", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee", "amount": 19, "currency": "USD"},
            {"component": "Bank transaction charge (2.5%)", "amount": 4, "currency": "USD"},
            {"component": "e-Business Visa (online; 365-day validity)", "amount": 89, "currency": "USD"},
        ],
        "processing_time_days_min": 7,
        "processing_time_days_max": 21,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Business Purpose + Indian Counterpart", "description": "Identify Indian company / partner / conference. Define scope of visit and dates.", "estimated_days": 7, "documents_needed": ["Email correspondence with Indian counterpart"], "tips": ["Be specific in purpose — vague applications get refused"]},
            {"step_number": 2, "title": "Indian Sponsor / Invitation Letter", "description": "Indian counterpart issues invitation letter on company letterhead.", "estimated_days": 5, "documents_needed": ["Invitation letter", "Indian sponsor's GST + IT returns + incorporation"], "tips": ["Letter must specify purpose, duration, dates, and that Indian party covers/does not cover expenses"]},
            {"step_number": 3, "title": "Overseas Employer / Own Business Documentation", "description": "Letter from foreign employer confirming role + India business OR own company registration documents.", "estimated_days": 5, "documents_needed": ["Foreign employer letter (if employed)", "Own company registration (if self-employed)"], "tips": []},
            {"step_number": 4, "title": "Online Application + Documents", "description": "Apply at indianvisaonline.gov.in. Choose Business category and visa validity (1/5/10 years).", "estimated_days": 1, "documents_needed": ["Passport scan", "Photo", "Signature", "Sponsor letter", "Financial proof"], "tips": ["e-Business Visa option available for shorter trips (faster, online-only)"]},
            {"step_number": 5, "title": "VFS Appointment + Submission", "description": "Submit application package, biometrics, pay fees.", "estimated_days": 7, "documents_needed": ["Full application package"], "tips": []},
            {"step_number": 6, "title": "Visa Processing + Issuance", "description": "7-21 days typical. Sticker visa in passport.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Travel + Conduct Business", "description": "Enter India, conduct business activities. Exit within 180 days of arrival.", "estimated_days": 180, "documents_needed": ["Passport with visa"], "tips": ["Keep return tickets + accommodation proof in case of port-of-entry queries"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Passport-size photograph (51x51mm white bg)", "mandatory": True, "notes": ""},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Invitation letter from Indian company", "mandatory": True, "notes": "Letterhead, dates, purpose"},
            {"name": "Indian sponsor's Certificate of Incorporation", "mandatory": True, "notes": ""},
            {"name": "Indian sponsor's GST + IT returns (last 2 years)", "mandatory": True, "notes": ""},
            {"name": "Letter from foreign employer (if employed)", "mandatory": True, "notes": "Confirming role + nature of visit"},
            {"name": "Own company registration (if self-employed)", "mandatory": False, "notes": ""},
            {"name": "Last 6 months' bank statements", "mandatory": True, "notes": "Showing financial means"},
            {"name": "Confirmed travel + accommodation booking", "mandatory": False, "notes": "Recommended"},
            {"name": "CV / business profile", "mandatory": False, "notes": ""},
            {"name": "Yellow fever vaccination (if from endemic country)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Vague business purpose — generic 'meetings' not detailed",
            "Sponsor letter lacks specifics (dates, purpose, location)",
            "Weak Indian sponsor (low GST returns, recent incorporation)",
            "Insufficient bank balance",
            "Inconsistency between application, sponsor letter, and travel plans",
            "Prior visa overstay or cancellation",
        ],
        "success_tips": [
            "Specify the EXACT purpose of visit, EXACT meetings/conferences, and EXACT dates",
            "Strong Indian sponsor improves approval — established companies with consistent GST + IT history",
            "Choose 5/10-year validity for frequent travellers — same fee as 1-year",
            "Consider e-Business Visa for trips under 12 months — fully online, faster",
            "Plan exits before 180-day continuous stay limit to avoid tax residency",
            "Carry sponsor letter + return tickets at port of entry — immigration may verify",
            "Don't accept Indian salary on B visa — convert to E visa or risk visa cancellation",
        ],
        "faqs": [
            {"q": "Can I work for an Indian company on Business Visa?", "a": "NO. Direct employment + salary from Indian entity requires Employment (E) Visa. Business Visa is strictly for commercial visits — no salary drawn from Indian payroll."},
            {"q": "How long can I stay per visit?", "a": "Maximum 180 days continuous. Exit India and re-enter for further stays. Each entry under multiple-entry visa is a fresh 180-day window."},
            {"q": "What's the difference between B Visa and e-Business Visa?", "a": "e-Business Visa is online, valid 365 days, max 180 days per visit, USD 89. Regular B Visa is sticker visa, valid 1/5/10 years, requires mission visit, USD 160."},
            {"q": "Do I need an Indian sponsor?", "a": "Yes — almost always. Either an Indian company invites you OR you have a credible foreign employer with India business operations."},
            {"q": "Can I do training or short-term project work?", "a": "Yes — training, knowledge transfer, project supervision, and short-term technical work where you're paid by foreign employer (not Indian entity) is permitted on B Visa."},
        ],
        "official_url": "https://indianvisaonline.gov.in/visa/visa-fee.html",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/visa/visa-fee.html",
            "https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf",
            "https://indianvisaonline.gov.in/evisa/",
            "https://www.indianembassyusa.gov.in/extra?id=90",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in + MHA Annex III on 2026-02-27. Business Visa fee uniform USD 160 across 1/5/10-year validities per 2018 reform.",
    },

    # ── 5. IN-STU — Student Visa (S) ────────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "STU",
        "subclass_name": "Student Visa (S)",
        "service_type": "student",
        "category": "immigration",
        "description": (
            "The Student (S) Visa is for foreign nationals pursuing full-time studies at recognised "
            "Indian educational institutions — universities, IITs, IIMs, AIIMS, medical colleges, "
            "schools (10+2 affiliation), professional courses, yoga/Ayurveda institutes etc. "
            "Initial validity matches course duration up to 5 years (renewable in India via FRRO).\n\n"
            "Student Visa permits part-time work limited to specific contexts (research assistantship, "
            "labs, internships under approved programmes). The dependent visa (X-S) is available for "
            "spouse + minor children. FRRO registration is mandatory within 14 days of arrival for "
            "stays over 180 days."
        ),
        "eligibility_summary": (
            "Confirmed admission to recognised Indian institution (UGC / AICTE / NMC / similar "
            "recognition), genuine intent of study, financial means (USD 500+ per month documented), "
            "good academic record, English proficiency or local-language fitness for the course."
        ),
        "eligibility_criteria": [
            {"label": "Course admission", "value": "Confirmed admission at UGC/AICTE/NMC-recognised institution", "notes": "Bonafide certificate + admission letter required"},
            {"label": "Course duration", "value": "Visa valid for course duration up to 5 years", "notes": "FRRO renewal for longer programs"},
            {"label": "Course type", "value": "Full-time degree, diploma, professional course; primary school NOT eligible", "notes": "Schools must have 10+2 affiliation"},
            {"label": "Financial means", "value": "USD 500+ per month living costs + tuition", "notes": "6 months' bank statements OR sponsor's financials"},
            {"label": "Tourist-to-Student conversion", "value": "NOT permitted on existing tourist visa", "notes": "Must apply from outside India"},
            {"label": "FRRO registration", "value": "Mandatory within 14 days if stay >180 days", "notes": "Annual renewal at FRRO"},
            {"label": "Restrictions on yoga / Ayurveda", "value": "Specific institutional list maintained by MHA", "notes": "Check approved list"},
            {"label": "Medical examination", "value": "Required for certain countries", "notes": "Yellow fever, polio vaccinations as applicable"},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 100,
        "fees_inr_approx": 8300,
        "fees_breakdown": [
            {"component": "Student Visa (standard duration)", "amount": 100, "currency": "USD"},
            {"component": "Student Visa (Indian-origin / SAARC nationals — discounted)", "amount": 50, "currency": "USD"},
            {"component": "ICWF surcharge", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee", "amount": 19, "currency": "USD"},
            {"component": "Bank transaction charge (2.5%)", "amount": 3, "currency": "USD"},
            {"component": "Medical exam + vaccinations (variable)", "amount": 100, "currency": "USD"},
            {"component": "Tuition fee (paid to institution separately)", "amount": 5000, "currency": "USD"},
        ],
        "processing_time_days_min": 14,
        "processing_time_days_max": 30,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Admission + Receive Bonafide Letter", "description": "Apply to and receive admission letter + bonafide certificate from Indian institution.", "estimated_days": 30, "documents_needed": ["Admission letter", "Bonafide certificate", "Course details"], "tips": ["Confirm institution is on MHA-approved list (UGC/AICTE/NMC)", "Bonafide certificate must mention course duration"]},
            {"step_number": 2, "title": "Online Application at indianvisaonline.gov.in", "description": "Fill Student Visa application form, upload photo + signature + supporting documents.", "estimated_days": 1, "documents_needed": ["Passport scan", "Photo", "Signature", "Admission letter scan"], "tips": ["Select correct sub-category (Degree / Diploma / Yoga / Ayurveda)"]},
            {"step_number": 3, "title": "Financial Documentation", "description": "Prepare 6 months' bank statements OR sponsor's financial documents demonstrating ability to fund tuition + living costs.", "estimated_days": 7, "documents_needed": ["Bank statements (self or sponsor)", "Sponsor's IT returns", "Loan letter (if applicable)"], "tips": ["USD 500+/month living + tuition adequate", "Education loan letters from Indian banks accepted"]},
            {"step_number": 4, "title": "Medical Examination (if required)", "description": "Complete medical examination if country requires (yellow fever, polio vaccinations etc).", "estimated_days": 7, "documents_needed": ["Medical certificate", "Vaccination records"], "tips": []},
            {"step_number": 5, "title": "VFS Appointment + Document Submission", "description": "Submit application package, biometrics, pay all fees.", "estimated_days": 7, "documents_needed": ["Full package"], "tips": []},
            {"step_number": 6, "title": "Visa Processing + Issuance", "description": "14-30 days typical. Sticker visa in passport.", "estimated_days": 21, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Travel + FRRO Registration", "description": "Arrive in India, register at FRRO within 14 days if stay >180 days. Renew annually.", "estimated_days": 14, "documents_needed": ["Passport + visa", "Admission letter", "Address proof"], "tips": ["e-FRRO portal preferred", "Carry FRRO certificate for institution"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Passport-size photograph", "mandatory": True, "notes": "51x51mm white background"},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Admission letter from Indian institution", "mandatory": True, "notes": "On institutional letterhead, with seal"},
            {"name": "Bonafide certificate from institution", "mandatory": True, "notes": "Confirming course + duration"},
            {"name": "Institution's recognition certificate (UGC/AICTE/NMC/etc)", "mandatory": True, "notes": "Demonstrating regulatory recognition"},
            {"name": "Academic transcripts (10th, 12th, Bachelor's if relevant)", "mandatory": True, "notes": ""},
            {"name": "Degree certificates / equivalent qualifications", "mandatory": True, "notes": "Apostilled"},
            {"name": "Bank statements (last 6 months — self or sponsor)", "mandatory": True, "notes": ""},
            {"name": "Sponsor's IT returns (if parent funding)", "mandatory": True, "notes": "Last 2-3 years"},
            {"name": "Loan sanction letter (if applicable)", "mandatory": False, "notes": ""},
            {"name": "Medical certificate / vaccination records", "mandatory": False, "notes": "Per country of origin"},
            {"name": "Health insurance policy", "mandatory": False, "notes": "Strongly recommended"},
            {"name": "Statement of Purpose", "mandatory": False, "notes": "Useful for narrative cohesion"},
            {"name": "Address proof", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Institution not on MHA-approved recognition list",
            "Insufficient financial documentation",
            "Tourist-to-Student conversion attempted from inside India",
            "Course type ineligible (e.g., primary school for non-resident family)",
            "Previous visa overstay or violation",
            "Genuine student intent doubted (gap year + random course choice)",
            "Apostille missing on academic documents",
        ],
        "success_tips": [
            "Choose institutions with strong international student support — they help with visa documentation",
            "Provide multi-year tuition payment receipt + savings — strongest financial signal",
            "Apostille all academic documents at country of issue (not just notarisation)",
            "Apply 3-6 months ahead of course start — Indian missions can be slow during peak season",
            "Register FRRO within 14 days of arrival — non-compliance = penalty + visa cancellation",
            "Use e-FRRO portal (indianfrro.gov.in) to avoid in-person queues",
            "Keep institutional liaison's contact handy — they assist with FRRO + renewals",
            "Carry health insurance — Indian medical care is affordable but cover protects against emergencies",
        ],
        "faqs": [
            {"q": "Can I work part-time on Student Visa?", "a": "Limited — research assistantships, labs, internships under approved programs OK. General part-time employment is NOT permitted. Violation = visa cancellation."},
            {"q": "Can my family come with me?", "a": "Yes — spouse + dependent children apply for Entry (X-S) Visa with co-terminus validity. Spouse cannot work in India without own Employment Visa."},
            {"q": "Can I switch courses?", "a": "Yes, but requires fresh application + admission to new course + FRRO endorsement. Significant changes (degree to diploma, switching fields) need new visa."},
            {"q": "Do I need to register at FRRO?", "a": "Yes, if stay exceeds 180 days. Within 14 days of arrival. Annual renewals via e-FRRO portal (indianfrro.gov.in). Institution provides assistance."},
            {"q": "Can I extend my visa from inside India?", "a": "Yes — Student Visa is extendable at FRRO subject to course continuation, good academic standing, and updated bonafide certificate. Apply 60 days before expiry."},
            {"q": "What if I want to take up employment after course?", "a": "Different visa needed — convert to Employment (E) Visa via Indian Mission abroad (typically requires exit + re-entry). Some institutions assist with this transition."},
        ],
        "official_url": "https://indianvisaonline.gov.in/visa/visa-fee.html",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/visa/visa-fee.html",
            "https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf",
            "https://indianfrro.gov.in/eservices",
            "https://www.ugc.gov.in",
            "https://www.aicte-india.org",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in + MHA + UGC/AICTE recognition lists on 2026-02-27.",
    },

    # ── 6. IN-ETV — e-Tourist Visa (T) ──────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "ETV",
        "subclass_name": "e-Tourist Visa (e-TV)",
        "service_type": "visitor",
        "category": "immigration",
        "description": (
            "The e-Tourist Visa (e-TV) is a fully online, paperless visa for nationals of ~170 "
            "eligible countries visiting India for tourism, casual visits to friends/family, short-"
            "term yoga programs, or short medical attendance. Available in 30-day (peak USD 25 / lean "
            "USD 10), 1-year (USD 40), and 5-year (USD 80) validity. Multiple entry permitted with "
            "stay limits per visit.\n\n"
            "Application is 100% online via indianvisaonline.gov.in/evisa with photo + passport "
            "scan upload. No mission visit, no biometrics for first issuance (biometrics captured at "
            "Indian airport on arrival). Approved by Email within 24-72 hours typically."
        ),
        "eligibility_summary": (
            "Nationals of eligible countries (US, UK, Australia, Canada, EU, Japan, Singapore, UAE "
            "and ~170 others) visiting India for tourism, leisure, short-term yoga / meditation, "
            "casual family/friend visit, or attending short conference. Not eligible for employment, "
            "studies, or commercial work."
        ),
        "eligibility_criteria": [
            {"label": "Eligible nationality", "value": "Citizen of one of ~170 eligible countries", "notes": "Full list at indianvisaonline.gov.in/evisa"},
            {"label": "Purpose", "value": "Tourism, leisure, family/friend visit, short yoga, short medical attendance, short conference", "notes": "NOT for employment / business / studies"},
            {"label": "Passport validity", "value": "Minimum 6 months from arrival + 2 blank pages", "notes": ""},
            {"label": "Entry ports", "value": "28 designated airports + 5 seaports for e-Visa entry", "notes": "List on portal"},
            {"label": "Maximum stay", "value": "30 days (continuous) for 30-day visa; up to 180 days / 90 days per visit for 1/5-year", "notes": "Varies by visa duration"},
            {"label": "Children", "value": "Each child needs own e-Visa (no inclusion in parent's)", "notes": ""},
            {"label": "Apply window", "value": "Apply 30 days before arrival; submit at least 4 days before travel", "notes": ""},
            {"label": "Non-extendable", "value": "e-TV cannot be extended in India", "notes": "Exit and re-apply if needed"},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 40,
        "fees_inr_approx": 3320,
        "fees_breakdown": [
            {"component": "30-day e-TV (Peak season Jul-Mar)", "amount": 25, "currency": "USD"},
            {"component": "30-day e-TV (Lean season Apr-Jun)", "amount": 10, "currency": "USD"},
            {"component": "1-year e-TV (multiple entry)", "amount": 40, "currency": "USD"},
            {"component": "5-year e-TV (multiple entry)", "amount": 80, "currency": "USD"},
            {"component": "Bank transaction charge (2.5%)", "amount": 2, "currency": "USD"},
            {"component": "Urgent processing fee (if expediting)", "amount": 99, "currency": "USD"},
        ],
        "processing_time_days_min": 1,
        "processing_time_days_max": 4,
        "step_by_step": [
            {"step_number": 1, "title": "Verify Eligibility + Choose Visa Duration", "description": "Check that your nationality is on the eligible list. Decide on 30-day / 1-year / 5-year option based on travel plans.", "estimated_days": 1, "documents_needed": [], "tips": ["5-year option ideal for repeat travellers — same per-visit limit", "Lean season (Apr-Jun) 30-day at USD 10 — bargain"]},
            {"step_number": 2, "title": "Online Application at indianvisaonline.gov.in/evisa", "description": "Fill application, upload digital photo + passport bio page scan. Pay fee online by credit/debit card or PayPal.", "estimated_days": 1, "documents_needed": ["Passport bio page scan", "Recent digital photo (2x2 inch white bg)", "Email + payment method"], "tips": ["Use exact spelling on passport", "Submit at least 4 days before travel"]},
            {"step_number": 3, "title": "Receive ETA (Electronic Travel Authorisation)", "description": "Approval email within 24-72 hours. Download ETA PDF — must be printed and carried during travel.", "estimated_days": 3, "documents_needed": [], "tips": ["Check spam folder", "Print 2 copies of ETA"]},
            {"step_number": 4, "title": "Travel to India via Designated Port", "description": "Fly into one of 28 designated airports / 5 seaports. Immigration officer captures biometrics, stamps passport with e-Visa entry.", "estimated_days": 1, "documents_needed": ["Passport", "ETA printout", "Return ticket", "Address of stay"], "tips": ["Carry ETA on phone + printed", "Designated airports include DEL, BOM, BLR, MAA, HYD, CCU, AMD, GOI, COK, TRV, JAI, LKO, etc."]},
            {"step_number": 5, "title": "Enjoy Stay + Exit Within Stay Limit", "description": "Stay within permitted duration per visit. Exit before stay limit / visa validity expires.", "estimated_days": 30, "documents_needed": ["Passport with stamped e-Visa"], "tips": ["Track days carefully — overstays incur fines + future visa difficulties", "Cannot extend e-TV in India — exit and re-apply"]},
        ],
        "document_checklist": [
            {"name": "Passport bio page scan (clear, colour)", "mandatory": True, "notes": "6+ months validity, 2 blank pages"},
            {"name": "Recent digital photograph (2x2 inch white bg)", "mandatory": True, "notes": "Face fills 80% of frame"},
            {"name": "Email address (active)", "mandatory": True, "notes": "For ETA delivery"},
            {"name": "Credit / Debit / PayPal payment method", "mandatory": True, "notes": "Online payment only"},
            {"name": "Confirmed return ticket / onward journey proof", "mandatory": False, "notes": "May be checked at port"},
            {"name": "Address proof in India (hotel / family)", "mandatory": False, "notes": "Recommended; may be asked at port"},
            {"name": "Yellow fever vaccination certificate (if from endemic country)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Nationality not on eligible list",
            "Poor quality / non-compliant photograph",
            "Passport validity less than 6 months",
            "Inconsistent name spelling vs passport",
            "Prior overstay or visa violation in India",
            "Submitted too close to travel date (<4 days)",
            "Purpose flagged (e.g., journalist / employment cover)",
        ],
        "success_tips": [
            "Use HIGH-QUALITY recent photo with white background — most common rejection cause",
            "Apply 7-30 days before travel (sweet spot — not too early, not too last-minute)",
            "5-year option pays for itself if visiting 3+ times — same fee structure for entries",
            "Print AND carry ETA on phone — both backups",
            "Check designated entry-port list — flying into non-listed airports requires sticker visa",
            "Plan exits within continuous stay limit — overstays trigger penalty + future refusals",
            "Lean season (Apr-Jun) 30-day visa at USD 10 — useful for short hot-season trips",
        ],
        "faqs": [
            {"q": "Can I enter India through any airport on e-TV?", "a": "NO. e-TV is valid only at 28 designated airports + 5 seaports. Exit can be from any airport / land border. Check current list at indianvisaonline.gov.in/evisa."},
            {"q": "Can I extend my e-TV in India?", "a": "NO. e-TV is non-extendable. Exit India and apply for a fresh e-TV from outside if you need more time."},
            {"q": "Can my child use my e-TV?", "a": "No — each traveller (including children) needs own e-TV with own photo + passport scan. Same family can apply together via the same payment."},
            {"q": "Why was my photo rejected?", "a": "Common causes: shadows, coloured background, glasses with glare, low resolution, face not 80% of frame. Use professional photo or smartphone with good lighting + white wall."},
            {"q": "Can I work on e-TV?", "a": "NO. e-TV is strictly tourism / casual visits / short conferences. Any commercial / employment activity = visa violation + immediate cancellation."},
            {"q": "Does e-TV require biometrics?", "a": "Yes — at port of entry (Indian airport). Application itself is online without biometrics. Biometrics captured by immigration on arrival."},
            {"q": "Can I convert e-TV to other visa types in India?", "a": "NO. All other visa types (Employment, Student, Medical) require fresh application from outside India through Indian Mission."},
        ],
        "official_url": "https://indianvisaonline.gov.in/evisa/",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/evisa/",
            "https://indianvisaonline.gov.in/evisa/tvoa.html",
            "https://indianvisaonline.gov.in/evisa/images/Etourist_fee_final.pdf",
            "https://www.indianembassyusa.gov.in/News?id=24889",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in/evisa on 2026-02-27. Lean/peak season fee differentiation per MHA 2018 reform; fees stable in 2026.",
    },

    # ── 7. IN-MED — Medical Visa (MED) ──────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "MED",
        "subclass_name": "Medical Visa (MED) + Medical Attendant (MED-X)",
        "service_type": "medical",
        "category": "immigration",
        "description": (
            "The Medical (MED) Visa is for foreign nationals travelling to India for specialised "
            "medical treatment at recognised Indian hospitals. Initial validity up to 1 year or "
            "treatment duration (whichever earlier), with up to 3 entries permitted. Renewable in "
            "India via FRRO based on treatment progress.\n\n"
            "Each Medical Visa holder may be accompanied by up to 2 Medical Attendants (MED-X visa, "
            "typically blood relatives) with co-terminus validity. The hospital provides a reference "
            "letter that triggers the application. e-Medical Visa is also available for short stays "
            "(60 days, triple entry, USD 69)."
        ),
        "eligibility_summary": (
            "Foreign patient with confirmed treatment at recognised Indian hospital, medical referral "
            "from home country, ability to fund treatment, and supporting family attendants where "
            "needed. Treatment types include surgery, organ transplant, oncology, cardiology, "
            "neurology, ophthalmology, and others."
        ),
        "eligibility_criteria": [
            {"label": "Indian hospital reference", "value": "Letter from JCI / NABH-accredited Indian hospital confirming treatment", "notes": "Hospital details + estimated treatment plan + cost"},
            {"label": "Home country medical referral", "value": "Diagnosis + recommendation from home doctor", "notes": "Translated to English if needed"},
            {"label": "Treatment type", "value": "Recognised speciality care (surgery / transplant / oncology / etc)", "notes": "Cosmetic procedures + IVF have specific rules"},
            {"label": "Financial means", "value": "Ability to fund treatment + stay (deposit / bank statements / insurance)", "notes": "Treatment costs often paid in advance to hospital"},
            {"label": "Medical attendants", "value": "Up to 2 blood relatives (spouse / parent / child / sibling) on MED-X visa", "notes": "Co-terminus with patient's visa"},
            {"label": "FRRO registration", "value": "Mandatory within 14 days for stays >180 days", "notes": "Hospital usually facilitates"},
            {"label": "Renewability", "value": "Up to 3 years total with FRRO endorsements based on treatment", "notes": "Beyond that — case-by-case MHA review"},
            {"label": "Health insurance / fund deposit", "value": "Most hospitals require advance deposit", "notes": "Plan financial logistics with hospital"},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 100,
        "fees_inr_approx": 8300,
        "fees_breakdown": [
            {"component": "Medical Visa (up to 6 months single/multiple entry)", "amount": 100, "currency": "USD"},
            {"component": "Medical Visa (>6 months up to 1 year multiple entry)", "amount": 100, "currency": "USD"},
            {"component": "Medical Attendant Visa (MED-X) per attendant", "amount": 100, "currency": "USD"},
            {"component": "e-Medical Visa (60 days triple entry — online)", "amount": 69, "currency": "USD"},
            {"component": "e-Medical Attendant Visa (60 days triple entry — online)", "amount": 69, "currency": "USD"},
            {"component": "ICWF + VFS surcharge", "amount": 22, "currency": "USD"},
            {"component": "FRRO registration (in India)", "amount": 0, "currency": "INR"},
            {"component": "Hospital deposit (variable, paid to hospital)", "amount": 5000, "currency": "USD"},
        ],
        "processing_time_days_min": 7,
        "processing_time_days_max": 21,
        "step_by_step": [
            {"step_number": 1, "title": "Consult Indian Hospital + Receive Reference Letter", "description": "Contact JCI/NABH-accredited Indian hospital, share medical reports, receive formal treatment plan + cost estimate + reference letter.", "estimated_days": 14, "documents_needed": ["Home country medical reports", "Diagnosis", "Treatment plan", "Cost estimate"], "tips": ["Hospitals like Apollo, Fortis, AIIMS, Medanta, Manipal, Narayana have international patient cells", "Get cost estimate in writing — visa application needs this"]},
            {"step_number": 2, "title": "Home Country Medical Referral", "description": "Obtain referral letter from home doctor recommending Indian treatment.", "estimated_days": 7, "documents_needed": ["Doctor's referral letter (English)"], "tips": []},
            {"step_number": 3, "title": "Online Application at indianvisaonline.gov.in", "description": "Apply for Medical Visa (and MED-X for attendants). Choose duration based on treatment plan.", "estimated_days": 1, "documents_needed": ["Passport scan", "Photo", "Signature", "Hospital reference letter", "Medical reports"], "tips": ["e-Medical Visa option for short stays (60 days, online)"]},
            {"step_number": 4, "title": "Medical Attendants Documentation", "description": "For each attendant: relationship proof (marriage / birth certificate), separate application with same hospital reference.", "estimated_days": 3, "documents_needed": ["Relationship proof", "Attendant's passport / photo"], "tips": ["Max 2 attendants per patient", "Must be blood relatives (or spouse)"]},
            {"step_number": 5, "title": "VFS / Mission Submission", "description": "Submit all applications together (patient + attendants), biometrics, fees.", "estimated_days": 7, "documents_needed": ["Full document set"], "tips": ["Highlight URGENT medical nature — missions often expedite"]},
            {"step_number": 6, "title": "Visa Issuance + Travel", "description": "Visa typically 7-21 days. Travel to India with all medical documents.", "estimated_days": 14, "documents_needed": [], "tips": ["Carry full medical history on flight", "Coordinate airport pickup with hospital if needed"]},
            {"step_number": 7, "title": "Hospital Admission + FRRO Registration", "description": "Admit to hospital, register at FRRO within 14 days if stay >180 days. Hospital facilitates FRRO.", "estimated_days": 14, "documents_needed": ["Passport", "Visa", "Hospital admission letter"], "tips": ["e-FRRO portal preferred", "Hospital's international patient cell handles paperwork"]},
            {"step_number": 8, "title": "Treatment + Recovery + Renewal", "description": "Receive treatment. If extension needed, FRRO with hospital reference can renew up to 3 years total.", "estimated_days": 180, "documents_needed": ["Hospital progress reports"], "tips": ["Keep all bills + reports for insurance / tax purposes"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Passport-size photograph (51x51mm white bg)", "mandatory": True, "notes": ""},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Indian hospital reference letter", "mandatory": True, "notes": "JCI / NABH-accredited; on letterhead"},
            {"name": "Treatment plan from Indian hospital", "mandatory": True, "notes": "Diagnosis + procedure + duration + cost"},
            {"name": "Home country doctor's referral letter", "mandatory": True, "notes": "Recommending Indian treatment"},
            {"name": "Medical history + diagnostic reports", "mandatory": True, "notes": "Comprehensive"},
            {"name": "Financial proof (bank statements / fund deposit / insurance)", "mandatory": True, "notes": "Covering treatment + stay"},
            {"name": "Hospital deposit receipt (if paid upfront)", "mandatory": False, "notes": "Strong financial signal"},
            {"name": "Health insurance (if applicable)", "mandatory": False, "notes": ""},
            {"name": "Relationship proof for attendants (marriage / birth certs)", "mandatory": True, "notes": "For MED-X applicants"},
            {"name": "Attendants' passport + photo", "mandatory": True, "notes": "For MED-X applicants"},
            {"name": "Address proof", "mandatory": True, "notes": ""},
            {"name": "Yellow fever vaccination (if from endemic country)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Hospital not JCI / NABH accredited",
            "Vague treatment plan (no diagnosis / duration / cost specified)",
            "Insufficient financial proof",
            "Attendants exceed 2 OR not blood relatives",
            "Prior visa overstay or compliance issues",
            "Treatment available in home country (officers may probe)",
            "e-Medical Visa applied for treatment exceeding 60 days",
        ],
        "success_tips": [
            "Choose hospital with established international patient cell — they handle most paperwork",
            "Request DETAILED treatment plan with phases + duration + costs — this is what missions evaluate",
            "Pay deposit to hospital before visa application — strongest financial signal",
            "Apply for patient + attendants simultaneously — missions process together",
            "For long treatments (>60 days), apply for MED Visa via Mission (not e-Medical)",
            "Coordinate FRRO registration with hospital — they have established processes",
            "Keep ALL bills + reports — useful for insurance claims + future renewals",
            "Highlight URGENT nature in cover letter — missions can expedite medical cases",
        ],
        "faqs": [
            {"q": "How many medical attendants can accompany?", "a": "Maximum 2, must be blood relatives (spouse / parent / child / sibling). Apply for MED-X visa for each; relationship proof mandatory."},
            {"q": "What's the difference between MED Visa and e-Medical Visa?", "a": "MED Visa: sticker visa from Mission, up to 1 year initial + renewable up to 3 years, multiple entry. e-Medical Visa: online, 60 days, triple entry, USD 69 — for short treatments only."},
            {"q": "Can I extend treatment beyond 1 year?", "a": "Yes — at FRRO with updated hospital reference. Total stay extendable up to 3 years (sometimes longer with MHA approval) based on continuing treatment."},
            {"q": "What about elective / cosmetic procedures?", "a": "Generally not eligible for MED Visa. Cosmetic procedures + IVF have specific rules — check with mission or apply for tourist visa for short cosmetic stays."},
            {"q": "Can my family stay with me?", "a": "Yes — up to 2 blood relatives on MED-X attendant visa with same validity as patient's visa. Additional family members need separate Entry / Tourist visa."},
            {"q": "Do I need to register with FRRO?", "a": "Yes if treatment exceeds 180 days. Within 14 days of arrival. Hospital's international patient cell typically facilitates the process at e-FRRO portal."},
        ],
        "official_url": "https://indianvisaonline.gov.in/visa/visa-fee.html",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/visa/visa-fee.html",
            "https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf",
            "https://indianvisaonline.gov.in/evisa/",
            "https://indianfrro.gov.in/eservices",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in + MHA Annex III on 2026-02-27. e-Medical Visa fee USD 69 per current MEA portal.",
    },

    # ── 8. IN-CONF — Conference Visa (C) ────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "CONF",
        "subclass_name": "Conference Visa (C)",
        "service_type": "conference",
        "category": "immigration",
        "description": (
            "The Conference (C) Visa is for foreign nationals attending conferences, seminars, "
            "workshops organised by Indian Government Ministries, PSUs, UN-affiliated bodies, or "
            "recognised institutions. Validity matches conference duration (typically single entry, "
            "up to 90 days). Special clearances required for conferences in restricted regions "
            "(J&K, North-East).\n\n"
            "Distinct from Business Visa — Conference Visa specifically for sponsored academic / "
            "policy / governmental events. Some events have political clearance requirements via "
            "MEA's Political (Conference) wing — typically 2-3 months processing."
        ),
        "eligibility_summary": (
            "Confirmed invitation to a conference organised by recognised Indian entity (government, "
            "PSU, university, UN body). Conference must have political clearance from MEA where "
            "required. Travel for personal academic events typically uses Business or Tourist Visa."
        ),
        "eligibility_criteria": [
            {"label": "Conference organiser type", "value": "Government / PSU / UN-affiliated / recognised university / international body", "notes": "Personal academic events typically not under this category"},
            {"label": "Formal invitation", "value": "Invitation from organising entity on letterhead", "notes": "Conference name, dates, your role"},
            {"label": "Political clearance", "value": "Required for some conferences (MEA clearance)", "notes": "Organising entity coordinates"},
            {"label": "Restricted areas", "value": "Additional clearance for J&K, NE States, Andaman", "notes": "Restricted Area Permit may be needed"},
            {"label": "Duration", "value": "Typically single-entry up to 90 days", "notes": "Matches event duration"},
            {"label": "Purpose strictly conference", "value": "Cannot use for general tourism or business", "notes": "Restricted to event + reasonable side travel"},
            {"label": "Financial means", "value": "Adequate funds for stay", "notes": "Often organiser covers"},
            {"label": "Yellow fever vaccination", "value": "Required if from endemic country", "notes": ""},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 100,
        "fees_inr_approx": 8300,
        "fees_breakdown": [
            {"component": "Conference Visa — single/multiple entry up to 6 months", "amount": 100, "currency": "USD"},
            {"component": "e-Conference Visa (online — short stays)", "amount": 80, "currency": "USD"},
            {"component": "ICWF surcharge", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee", "amount": 19, "currency": "USD"},
            {"component": "Bank transaction charge (2.5%)", "amount": 3, "currency": "USD"},
            {"component": "Political clearance processing (if applicable)", "amount": 0, "currency": "USD"},
        ],
        "processing_time_days_min": 14,
        "processing_time_days_max": 60,
        "step_by_step": [
            {"step_number": 1, "title": "Receive Conference Invitation", "description": "Organising entity issues formal invitation letter with event details (name, dates, venue, your role).", "estimated_days": 7, "documents_needed": ["Invitation letter", "Conference brochure / agenda"], "tips": ["Letter must be on official letterhead", "Specify role: speaker / delegate / panellist"]},
            {"step_number": 2, "title": "Political Clearance (if required)", "description": "For sensitive conferences, organising entity obtains political clearance from MEA — typically 2-3 months.", "estimated_days": 60, "documents_needed": ["Conference details for clearance"], "tips": ["This is OUTSIDE applicant's control — apply early"]},
            {"step_number": 3, "title": "Online Application at indianvisaonline.gov.in", "description": "Apply for Conference Visa, upload supporting documents.", "estimated_days": 1, "documents_needed": ["Passport scan", "Photo", "Signature", "Invitation letter", "Political clearance ref (if any)"], "tips": ["e-Conference Visa option for online application"]},
            {"step_number": 4, "title": "VFS / Mission Submission", "description": "Submit application, biometrics, fees.", "estimated_days": 7, "documents_needed": ["Full document set"], "tips": []},
            {"step_number": 5, "title": "Visa Processing + Issuance", "description": "14-60 days depending on political clearance. Sticker visa.", "estimated_days": 30, "documents_needed": [], "tips": ["Standard conferences: 14-21 days; clearance-required: 30-60 days"]},
            {"step_number": 6, "title": "Travel + Attend Conference", "description": "Arrive in India, attend conference, depart within visa validity.", "estimated_days": 7, "documents_needed": ["Passport", "Visa", "Conference confirmation"], "tips": ["Keep conference attendance certificate for future visa applications"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Passport-size photograph", "mandatory": True, "notes": ""},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Conference invitation letter (on letterhead)", "mandatory": True, "notes": "From organising entity"},
            {"name": "Conference agenda / brochure", "mandatory": True, "notes": ""},
            {"name": "Political clearance reference (if applicable)", "mandatory": False, "notes": "Provided by organising entity"},
            {"name": "Letter from home institution / employer", "mandatory": True, "notes": "Confirming role + funding (if relevant)"},
            {"name": "CV / Bio", "mandatory": True, "notes": "Highlights relevance to conference"},
            {"name": "Bank statements (financial means)", "mandatory": True, "notes": "Last 3-6 months"},
            {"name": "Confirmed travel + accommodation booking", "mandatory": False, "notes": ""},
            {"name": "Yellow fever vaccination (if from endemic country)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Conference not organised by recognised entity",
            "Political clearance pending / refused (some sensitive topics)",
            "Vague invitation letter (missing dates / venue / role)",
            "Insufficient financial means + no organiser-coverage proof",
            "Prior visa violations",
            "Conference category should be Business Visa instead (commercial events)",
        ],
        "success_tips": [
            "Confirm with organising entity whether political clearance is needed BEFORE applying",
            "Apply 3+ months ahead if political clearance involved",
            "Letter from home institution adds credibility (especially academics)",
            "If financially supported by organiser, get written confirmation — strengthens application",
            "Don't combine conference with long tourism — that needs separate Tourist Visa",
            "Carry conference confirmation + organiser's contact details at port of entry",
        ],
        "faqs": [
            {"q": "What's the difference between Conference Visa and Business Visa?", "a": "Conference Visa is for academic / policy / governmental events organised by recognised entities. Business Visa is for commercial meetings + market visits. Use right category based on the event nature."},
            {"q": "Do I need political clearance for every conference?", "a": "No — only for sensitive topics (foreign policy, defence, internal security, J&K, NE States, religious congregations etc). Organising entity advises and obtains."},
            {"q": "Can I do tourism after the conference?", "a": "Yes — short tourism within visa validity is permitted, but visa is technically conference-focussed. For extended tourism, plan separate Tourist Visa."},
            {"q": "How long does processing take?", "a": "Standard conferences: 14-21 days. Political-clearance-required conferences: 30-60+ days. Apply 3+ months ahead for the latter."},
            {"q": "Can my spouse accompany me?", "a": "Spouse needs separate visa (Entry / Tourist Visa) — Conference Visa typically single applicant. Apply together at the same mission for coordinated travel."},
        ],
        "official_url": "https://indianvisaonline.gov.in/visa/visa-fee.html",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/visa/visa-fee.html",
            "https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf",
            "https://www.mea.gov.in/political-clearance.htm",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in + MEA political clearance guidelines on 2026-02-27.",
    },

    # ── 9. IN-JRN — Journalist Visa (J) ─────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "JRN",
        "subclass_name": "Journalist Visa (J)",
        "service_type": "journalist",
        "category": "immigration",
        "description": (
            "The Journalist (J) Visa is for foreign professional journalists, film-makers, "
            "photographers, and media personnel travelling to India in professional capacity. "
            "Typically single-entry up to 3 months for short assignments; longer terms (up to 1 "
            "year) for accredited correspondents based in India.\n\n"
            "Requires prior clearance from MEA (External Publicity Division) and sometimes MHA. "
            "Considered HIGH-SCRUTINY category — applications processed conservatively and may "
            "involve interview at Indian Mission. Reporting in restricted areas (J&K, NE) requires "
            "additional Protected Area Permit."
        ),
        "eligibility_summary": (
            "Bona-fide professional journalist with established media affiliation, clear assignment "
            "in India, MEA/XPD clearance. Includes correspondents, reporters, photographers, "
            "documentary film-makers, and TV crews."
        ),
        "eligibility_criteria": [
            {"label": "Professional credentials", "value": "Established journalist / media professional with prior published work", "notes": "CV with portfolio / clippings / IMDB / press card"},
            {"label": "Media affiliation", "value": "Assignment letter from recognised media outlet", "notes": "Newspapers / news channels / production houses"},
            {"label": "MEA / XPD clearance", "value": "Mandatory pre-clearance from External Publicity Division, MEA", "notes": "Mission coordinates clearance"},
            {"label": "Assignment specificity", "value": "Clear assignment scope, dates, locations", "notes": "Vague applications routinely refused"},
            {"label": "Restricted areas", "value": "Additional Protected / Restricted Area Permit for J&K, NE, Andaman, etc.", "notes": "Coordinated through MHA"},
            {"label": "Single-entry typical", "value": "Mostly single-entry up to 3 months", "notes": "Multiple-entry for accredited correspondents"},
            {"label": "Equipment declaration", "value": "Filming/photography equipment must be declared at customs", "notes": "ATA Carnet may be needed"},
            {"label": "No commercial filming without permit", "value": "Feature films / commercial shoots need separate Film Permit", "notes": "Different from Journalist Visa"},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 100,
        "fees_inr_approx": 8300,
        "fees_breakdown": [
            {"component": "Journalist Visa (single entry up to 3 months)", "amount": 100, "currency": "USD"},
            {"component": "Journalist Visa (multiple entry — accredited correspondent)", "amount": 250, "currency": "USD"},
            {"component": "ICWF surcharge", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee", "amount": 19, "currency": "USD"},
            {"component": "Bank transaction charge (2.5%)", "amount": 3, "currency": "USD"},
            {"component": "Protected / Restricted Area Permit (if needed)", "amount": 50, "currency": "USD"},
            {"component": "Equipment customs deposit / ATA Carnet (variable)", "amount": 0, "currency": "USD"},
        ],
        "processing_time_days_min": 30,
        "processing_time_days_max": 90,
        "step_by_step": [
            {"step_number": 1, "title": "Define Assignment + Obtain Media Letter", "description": "Define EXACT assignment: scope, locations, interviews, dates. Obtain assignment letter from media outlet.", "estimated_days": 14, "documents_needed": ["Assignment letter from media outlet", "Editor's letter confirming role"], "tips": ["Be SPECIFIC — vague assignments routinely refused", "Avoid politically sensitive topics in initial application"]},
            {"step_number": 2, "title": "MEA / XPD Pre-Clearance Application", "description": "Indian Mission forwards application to MEA External Publicity Division for clearance. Takes 4-8 weeks.", "estimated_days": 45, "documents_needed": ["Assignment scope", "Locations", "List of interviewees"], "tips": ["Cannot proceed without XPD clearance", "Mission handles communication with MEA"]},
            {"step_number": 3, "title": "Online Application at indianvisaonline.gov.in", "description": "Apply for Journalist Visa, upload credentials + assignment letter.", "estimated_days": 1, "documents_needed": ["Passport scan", "Photo", "Signature", "Press card", "Assignment letter"], "tips": []},
            {"step_number": 4, "title": "VFS / Mission Submission + Interview", "description": "Submit application, biometrics, fees. Interview at Mission common for first-time J visa applicants.", "estimated_days": 14, "documents_needed": ["Full document set", "Portfolio of published work"], "tips": ["Be prepared to discuss assignment in detail", "Carry samples of published work"]},
            {"step_number": 5, "title": "Visa Issuance + Restricted Area Permits", "description": "Visa granted; if restricted areas in scope, separate RAP/PAP via MHA.", "estimated_days": 21, "documents_needed": [], "tips": ["RAP/PAP needed for J&K, NE states, Andaman", "Process in parallel"]},
            {"step_number": 6, "title": "Travel + Customs Declaration of Equipment", "description": "Arrive in India, declare professional equipment at customs (ATA Carnet helps).", "estimated_days": 1, "documents_needed": ["Passport", "Visa", "Equipment list", "ATA Carnet (if applicable)"], "tips": ["Declare ALL equipment — undeclared items confiscated", "Carry equipment list with serial numbers"]},
            {"step_number": 7, "title": "Conduct Assignment + Comply with Reporting Rules", "description": "Carry out assignment within visa scope. Inform local Press Information Bureau / MEA office if rules require.", "estimated_days": 60, "documents_needed": [], "tips": ["Stick to declared scope — deviations risk visa cancellation", "MEA may request copy of published work"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Passport-size photograph", "mandatory": True, "notes": ""},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Press card / press accreditation (home country)", "mandatory": True, "notes": "Recognised press body"},
            {"name": "Assignment letter from media outlet", "mandatory": True, "notes": "On letterhead, specific scope"},
            {"name": "Editor's letter / employer confirmation", "mandatory": True, "notes": ""},
            {"name": "Portfolio of published work", "mandatory": True, "notes": "Articles / clips / IMDB / showreel"},
            {"name": "Detailed assignment scope (locations, interviews, dates)", "mandatory": True, "notes": ""},
            {"name": "List of equipment (with serial numbers)", "mandatory": True, "notes": ""},
            {"name": "ATA Carnet (recommended for professional equipment)", "mandatory": False, "notes": ""},
            {"name": "MEA / XPD clearance reference", "mandatory": True, "notes": "Mission obtains"},
            {"name": "Bank statements", "mandatory": True, "notes": ""},
            {"name": "Confirmed travel + accommodation booking", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "MEA / XPD clearance refused (sensitive topics, prior issues)",
            "Vague assignment scope",
            "Insufficient media credentials",
            "Prior visa violation or unauthorised reporting in India",
            "Topic deemed prejudicial to national interest",
            "Equipment list missing or inconsistent",
            "Restricted area access without supplementary permits",
        ],
        "success_tips": [
            "Apply 3+ months ahead — XPD clearance is the bottleneck",
            "Frame assignment scope NEUTRALLY in initial application (avoid politically charged language)",
            "Build strong portfolio + media affiliations BEFORE applying",
            "Carry ATA Carnet for expensive professional equipment — saves customs deposit",
            "Coordinate with local stringers / fixers in India — they help with logistics + permits",
            "Stick to declared scope strictly — deviations + unauthorised reporting = immediate cancellation + deportation",
            "Keep MEA / PIB office informed of major activities — proactive disclosure helps",
        ],
        "faqs": [
            {"q": "Can I report from restricted areas (J&K, NE)?", "a": "Requires additional Protected / Restricted Area Permit from MHA, often with home-country embassy involvement. Process in parallel with visa; allow 2-3 months."},
            {"q": "Can I switch from Tourist Visa to Journalist Visa in India?", "a": "NO. Journalist Visa must be applied from outside India through Indian Mission with full XPD clearance."},
            {"q": "Do I need a separate Film Permit?", "a": "For commercial / feature films / documentaries: YES — separate Film Permit from MIB (Ministry of Information and Broadcasting). Journalist Visa is for news reporting + standard journalism."},
            {"q": "Why was my assignment rejected by XPD?", "a": "Common causes: politically sensitive topics, lack of clear scope, applicant's prior controversial reporting, sensitive locations. Mission usually shares reason in confidentiality."},
            {"q": "Can I be accompanied by my family?", "a": "Family typically needs separate visa (Entry / Tourist Visa). Some accredited correspondents have provisions for dependant visas — clarify with Mission."},
            {"q": "How is equipment customs handled?", "a": "Declare ALL professional equipment at customs. ATA Carnet (international temporary import document) is best — avoids deposit. Without Carnet, deposit equal to equipment value may be required."},
        ],
        "official_url": "https://indianvisaonline.gov.in/visa/visa-fee.html",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/visa/visa-fee.html",
            "https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf",
            "https://www.mea.gov.in/xpd-foreign-press.htm",
            "https://www.pib.gov.in",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in + MEA XPD foreign press guidelines on 2026-02-27. XPD clearance process per current MEA practice.",
    },

    # ── 10. IN-RES — Research Visa (R) ──────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "RES",
        "subclass_name": "Research Visa (R)",
        "service_type": "research",
        "category": "immigration",
        "description": (
            "The Research (R) Visa is for foreign academics conducting research at Indian "
            "institutions — universities, IITs, IIMs, research bodies (ICAR, CSIR, ICMR, DRDO), "
            "archives, museums. Validity typically up to 1 year (short research) extendable to 5 "
            "years for longer projects. Requires MEA / MHA clearance and host institution "
            "sponsorship.\n\n"
            "Field research, archival research, fieldwork in remote regions, ethnographic studies "
            "and similar academic activities fall under this category. For research in restricted "
            "areas (J&K, NE), supplementary permits apply. Field research is sensitive — applications "
            "involve scrutiny of research topic + methodology."
        ),
        "eligibility_summary": (
            "Foreign academic researcher with formal affiliation to Indian host institution, MEA / "
            "MHA security clearance for research topic, clear research scope + methodology + "
            "duration. Funding source must be transparent."
        ),
        "eligibility_criteria": [
            {"label": "Host institution affiliation", "value": "Formal invitation + supervision agreement with recognised Indian institution", "notes": "University / research body / archive"},
            {"label": "Research topic + methodology", "value": "Detailed research proposal submitted in advance", "notes": "Reviewed by MEA / MHA"},
            {"label": "Academic credentials", "value": "PhD / equivalent / advanced student status", "notes": "Some institutions accept PhD candidates"},
            {"label": "MEA / MHA clearance", "value": "Pre-clearance for research topic + locations", "notes": "Sensitive topics + locations face longer review"},
            {"label": "Funding source", "value": "Transparent funding — own university / grant / scholarship", "notes": "Funding from politically sensitive sources may be flagged"},
            {"label": "Duration", "value": "Up to 5 years (multiple entry for long projects)", "notes": "Initial 1 year; renewable at FRRO"},
            {"label": "Restricted areas", "value": "Supplementary permits for J&K, NE, Andaman field research", "notes": ""},
            {"label": "FRRO registration", "value": "Mandatory within 14 days if stay >180 days", "notes": ""},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 100,
        "fees_inr_approx": 8300,
        "fees_breakdown": [
            {"component": "Research Visa (up to 6 months)", "amount": 100, "currency": "USD"},
            {"component": "Research Visa (6 months to 1 year)", "amount": 100, "currency": "USD"},
            {"component": "Research Visa (1 to 5 years multiple entry)", "amount": 190, "currency": "USD"},
            {"component": "ICWF surcharge", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee", "amount": 19, "currency": "USD"},
            {"component": "Bank transaction charge (2.5%)", "amount": 3, "currency": "USD"},
            {"component": "Restricted Area Permit (if applicable)", "amount": 50, "currency": "USD"},
            {"component": "FRRO registration (in India)", "amount": 0, "currency": "INR"},
        ],
        "processing_time_days_min": 45,
        "processing_time_days_max": 120,
        "step_by_step": [
            {"step_number": 1, "title": "Identify Host Institution + Get Affiliation Letter", "description": "Engage Indian host institution. Receive formal invitation + supervision letter.", "estimated_days": 45, "documents_needed": ["Invitation letter", "Supervision agreement", "Research proposal"], "tips": ["Established institutions (JNU, IIT, IIM, IISc, TIFR) help expedite", "Specify exact research scope + locations"]},
            {"step_number": 2, "title": "Prepare Detailed Research Proposal", "description": "Write formal proposal: topic, methodology, locations, timeline, funding, ethics approvals, expected outputs.", "estimated_days": 30, "documents_needed": ["Research proposal", "Ethics committee approval", "Funding proof"], "tips": ["Avoid politically sensitive language", "Be specific about locations + interviews + archives"]},
            {"step_number": 3, "title": "Online Application at indianvisaonline.gov.in", "description": "Apply for Research Visa, upload all supporting documents.", "estimated_days": 1, "documents_needed": ["Passport scan", "Photo", "Signature", "Affiliation letter", "Proposal"], "tips": []},
            {"step_number": 4, "title": "MEA / MHA Clearance", "description": "Mission forwards application for security + topic clearance. Takes 6-12 weeks typical.", "estimated_days": 60, "documents_needed": [], "tips": ["Sensitive topics (defence, foreign policy, J&K) face longer review", "Clear funding source helps clearance"]},
            {"step_number": 5, "title": "VFS / Mission Submission + Interview", "description": "Submit physical application, biometrics, fees. Interview common for first-time R visa.", "estimated_days": 14, "documents_needed": ["Full document set"], "tips": ["Discuss research scope in depth", "Carry previous publications + CV"]},
            {"step_number": 6, "title": "Visa Issuance + Restricted Permits", "description": "Visa granted + supplementary permits for restricted locations if needed.", "estimated_days": 21, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Travel + FRRO Registration + Research Start", "description": "Arrive in India, register FRRO within 14 days (if >180 days), commence research with host institution.", "estimated_days": 14, "documents_needed": ["Passport + visa", "Affiliation letter", "Research permit"], "tips": ["Host institution facilitates FRRO"]},
            {"step_number": 8, "title": "Continuous Compliance + Periodic Reporting", "description": "Comply with research scope. Provide progress reports to MEA/MHA if requested. Renew visa via FRRO based on host's continuing affiliation.", "estimated_days": 180, "documents_needed": ["Progress reports"], "tips": ["Stick to declared scope strictly", "Inform supervisor of any topic / location shifts"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Passport-size photograph", "mandatory": True, "notes": ""},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Host institution invitation + affiliation letter", "mandatory": True, "notes": "On letterhead, signed"},
            {"name": "Supervision agreement (named supervisor + role)", "mandatory": True, "notes": ""},
            {"name": "Research proposal (detailed)", "mandatory": True, "notes": "Topic / methodology / locations / timeline"},
            {"name": "Ethics committee approval (home institution)", "mandatory": True, "notes": "If research involves human subjects"},
            {"name": "Academic transcripts + PhD / advanced degree certificates", "mandatory": True, "notes": "Apostilled"},
            {"name": "CV with publications + research history", "mandatory": True, "notes": ""},
            {"name": "Funding source proof (grant / fellowship / own university)", "mandatory": True, "notes": "Transparent funding"},
            {"name": "MEA / MHA clearance reference", "mandatory": True, "notes": "Mission obtains"},
            {"name": "Bank statements (last 6 months)", "mandatory": True, "notes": ""},
            {"name": "Address proof", "mandatory": True, "notes": ""},
            {"name": "Restricted Area Permit (if applicable)", "mandatory": False, "notes": ""},
            {"name": "List of locations / archives / interviewees", "mandatory": True, "notes": "Per research proposal"},
        ],
        "common_rejection_reasons": [
            "MEA / MHA clearance refused (sensitive topic / location)",
            "Vague research proposal (no methodology / locations)",
            "Host institution not recognised OR unclear supervision",
            "Funding source unclear or politically sensitive",
            "Ethics approvals missing for human subject research",
            "Prior compliance issues (unauthorised topic shifts / extensions)",
            "Topic falls under journalism / commercial research (wrong visa category)",
        ],
        "success_tips": [
            "Engage Indian host institution 6+ months ahead — strong affiliation accelerates clearance",
            "Frame research proposal NEUTRALLY — avoid politically charged language even on sensitive topics",
            "Document ethics approvals + funding transparently — both critical for MEA scrutiny",
            "Use established Indian researchers as supervisors / collaborators — adds credibility",
            "Plan locations carefully — restricted areas need separate permits processed in parallel",
            "Register FRRO promptly + maintain logs of interviews / archive visits",
            "Stick to declared scope — unauthorised shifts trigger immediate cancellation",
            "Coordinate progress reports with supervisor — useful for renewals",
        ],
        "faqs": [
            {"q": "How is Research Visa different from Student Visa?", "a": "Student Visa is for full-time course-based study (degree / diploma). Research Visa is for academic research at a host institution — independent research with supervision rather than coursework."},
            {"q": "Can I extend my research?", "a": "Yes — extendable at FRRO based on continuing host affiliation + updated proposal + supervisor's endorsement. Total stay up to 5 years possible."},
            {"q": "Can I conduct field research in restricted regions?", "a": "Requires supplementary Protected / Restricted Area Permit from MHA. Process in parallel with main visa application. Allow 2-3 months."},
            {"q": "What about ethnographic / sociological research?", "a": "Highly sensitive category — MEA / MHA scrutinise scope, methodology, communities involved, expected outputs. Apply with strong host backing + clear ethics framework."},
            {"q": "Can my family come with me?", "a": "Spouse + minor children eligible for Entry (X-R) Visa with co-terminus validity. Spouse cannot work without own Employment Visa."},
            {"q": "Do I need to submit my final research output?", "a": "MEA may request copies of publications / dissertations / papers arising from research. Acknowledge Indian host + funding sources transparently."},
        ],
        "official_url": "https://indianvisaonline.gov.in/visa/visa-fee.html",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/visa/visa-fee.html",
            "https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf",
            "https://www.mea.gov.in/research-visa.htm",
            "https://www.ugc.gov.in/page/Foreign-Scholars.aspx",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in + MEA Research Visa guidelines + UGC Foreign Scholar policy on 2026-02-27. Long Research fees per Consulate Milan / HC KL schedules.",
    },

    # ── 11. IN-EX — Entry (X) Visa ──────────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "EX",
        "subclass_name": "Entry (X) Visa — Spouse / Children of Indian Citizens or OCI Holders",
        "service_type": "entry_x",
        "category": "immigration",
        "description": (
            "The Entry (X) Visa is for foreign nationals who are: (a) spouses / children of Indian "
            "citizens, (b) spouses / children of OCI cardholders, (c) persons of Indian origin not "
            "applying for OCI, or (d) dependents accompanying primary visa holders (Employment, "
            "Student, Medical, Research — issued as X-E, X-S, X-M, X-R sub-categories).\n\n"
            "Validity typically matches the primary visa holder's stay OR up to 5 years for X-PIO "
            "cases. Multiple entry. Spouses / children of Indian citizens often get fee-waived / "
            "nominal-fee processing at most Indian Missions."
        ),
        "eligibility_summary": (
            "Foreign national who is spouse / minor child of an Indian citizen, OCI holder, or "
            "person of Indian origin; OR dependent of a primary visa holder (E / S / M / R). "
            "Relationship documentation mandatory."
        ),
        "eligibility_criteria": [
            {"label": "Relationship category", "value": "Spouse / child of Indian citizen / OCI / PIO / dependent of E-S-M-R primary visa holder", "notes": "Marriage cert / birth cert evidence"},
            {"label": "Primary visa holder", "value": "For X-E/S/M/R: primary visa holder's visa must be in force", "notes": "Co-terminus validity"},
            {"label": "Spouse waiver", "value": "Spouses of Indian citizens often fee-waived / nominal at most missions", "notes": "USA / UK / UAE generally free"},
            {"label": "Children under 18", "value": "Apply with parental consent + relationship proof", "notes": ""},
            {"label": "Validity duration", "value": "Up to 5 years for X-PIO; co-terminus for X-E/S/M/R", "notes": ""},
            {"label": "Pakistani / Bangladeshi exclusion", "value": "Same as OCI — those nationals ineligible for X visa relations", "notes": ""},
            {"label": "FRRO registration", "value": "Mandatory if stay >180 days", "notes": ""},
            {"label": "Marriage duration", "value": "No minimum for spouse-of-Indian-citizen pathway", "notes": "Unlike OCI which needs 2+ years"},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 250,
        "fees_inr_approx": 20750,
        "fees_breakdown": [
            {"component": "Entry (X) Visa — general (5-year multiple entry)", "amount": 250, "currency": "USD"},
            {"component": "Entry (X) Visa — up to 6 months", "amount": 100, "currency": "USD"},
            {"component": "Entry (X) Visa — 6 months to 1 year", "amount": 140, "currency": "USD"},
            {"component": "X-1 / X-2 (Spouse / Child of PIO or Indian citizen) — fee waived (most missions)", "amount": 0, "currency": "USD"},
            {"component": "ICWF surcharge", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee", "amount": 19, "currency": "USD"},
            {"component": "Bank transaction charge (2.5%)", "amount": 6, "currency": "USD"},
        ],
        "processing_time_days_min": 14,
        "processing_time_days_max": 30,
        "step_by_step": [
            {"step_number": 1, "title": "Identify Relationship Category", "description": "Determine: spouse of Indian citizen / OCI / PIO, dependent of E/S/M/R holder, or person of Indian origin not applying for OCI.", "estimated_days": 1, "documents_needed": [], "tips": ["Different sub-categories have different fee structures"]},
            {"step_number": 2, "title": "Gather Relationship + Sponsor Documents", "description": "Marriage certificate, birth certificate, primary visa holder's passport + visa, Indian citizen / OCI cardholder details.", "estimated_days": 14, "documents_needed": ["Marriage certificate", "Birth certificate(s)", "Indian sponsor's passport / OCI card", "Primary visa holder's visa (if X-E/S/M/R)"], "tips": ["Apostille foreign-issued certs", "Marriage cert must be original / apostilled"]},
            {"step_number": 3, "title": "Online Application at indianvisaonline.gov.in", "description": "Apply for X Visa with correct sub-category. Each applicant (including children) has own application.", "estimated_days": 1, "documents_needed": ["Passport scan", "Photo", "Signature", "Relationship docs"], "tips": ["Each child needs own application — no inclusion in parent's"]},
            {"step_number": 4, "title": "Submit at VFS / Mission", "description": "Submit applications (often family-grouped), biometrics, fees (or waiver).", "estimated_days": 7, "documents_needed": ["Full document set"], "tips": ["Spouses of Indian citizens claim fee waiver at submission", "Bring marriage cert + Indian spouse's passport original at submission"]},
            {"step_number": 5, "title": "Visa Processing + Issuance", "description": "14-30 days. Sticker visa.", "estimated_days": 21, "documents_needed": [], "tips": []},
            {"step_number": 6, "title": "Travel + FRRO Registration (if applicable)", "description": "Arrive in India. FRRO registration within 14 days if stay >180 days.", "estimated_days": 14, "documents_needed": ["Passport + visa", "Marriage cert / relationship proof"], "tips": []},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Passport-size photograph", "mandatory": True, "notes": ""},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Marriage certificate (if spouse)", "mandatory": True, "notes": "Apostilled if foreign-issued"},
            {"name": "Birth certificate (if child / minor)", "mandatory": True, "notes": "Apostilled if foreign-issued"},
            {"name": "Indian sponsor's passport copy / OCI card", "mandatory": True, "notes": "Establishes Indian connection"},
            {"name": "Primary visa holder's passport + visa (if X-E/S/M/R)", "mandatory": True, "notes": "Co-terminus validity"},
            {"name": "Parental consent letter (for minor children travelling without both parents)", "mandatory": True, "notes": ""},
            {"name": "Bank statements / sponsor support letter", "mandatory": True, "notes": ""},
            {"name": "Address proof", "mandatory": True, "notes": ""},
            {"name": "Old PIO / OCI card (if applicable)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Marriage certificate not apostilled (foreign-issued)",
            "Minor child traveling without both parents — missing consent",
            "Primary visa holder's visa expired or about to expire",
            "Relationship documents inconsistent (different name spellings)",
            "Pakistani / Bangladeshi nationality of spouse (absolute bar)",
            "Sponsor's Indian citizenship / OCI cannot be verified",
        ],
        "success_tips": [
            "Claim spouse / child of Indian citizen FEE WAIVER at submission — saves USD 100-250",
            "Apostille marriage + birth certificates at country of issue (not just notary)",
            "Match name spellings ACROSS all documents (passport, marriage, birth)",
            "Apply with primary visa holder's application — co-ordinated processing",
            "For OCI alternative: X visa is faster + simpler if OCI not urgent",
            "Renew X visa from inside India via FRRO — less hassle than re-applying abroad",
        ],
        "faqs": [
            {"q": "How is Entry X Visa different from OCI?", "a": "X Visa is renewable foreign visa (up to 5 years multiple entry); OCI is lifelong card with FRRO exemption. X is simpler/faster; OCI is permanent with more benefits. Many use X Visa initially, then upgrade to OCI."},
            {"q": "Do spouses of Indian citizens pay any visa fee?", "a": "Most Indian Missions waive the visa fee for spouses of Indian citizens (X-1) and children (X-2). VFS service fee + ICWF still applicable. Check specific Mission's policy."},
            {"q": "Can my spouse work in India on X Visa?", "a": "NO — X Visa is dependent visa without work rights. Spouse needs own Employment (E) Visa to work in India. Some flexibility for OCI cardholders (full work rights)."},
            {"q": "What if my Indian spouse's passport expires?", "a": "X visa is tied to relationship, not the Indian spouse's specific passport. Provide updated passport at renewal. Marriage continuation is the key requirement."},
            {"q": "Can a divorced spouse continue on X Visa?", "a": "NO — divorce ends the X visa eligibility. Must apply for separate visa category (Tourist / Business / Employment) based on purpose."},
            {"q": "How are children's X visas processed?", "a": "Each child needs own application + own photo + own passport. Parental consent letter mandatory for minors traveling without both parents. Co-terminus validity with parent's visa."},
        ],
        "official_url": "https://indianvisaonline.gov.in/visa/visa-fee.html",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/visa/visa-fee.html",
            "https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf",
            "https://www.indianembassyusa.gov.in/extra?id=90",
            "https://www.blsinternational.com/india/uae/visa/cgi-entry-visa.php/visa-fee.php",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in + MHA Annex III + Indian Embassy USA fee schedules on 2026-02-27. Spouse-of-citizen fee waiver per multiple Mission notifications.",
    },

    # ── 12. IN-TRN — Transit Visa (T) ──────────────────────────────────────────
    {
        "country_code": "IN",
        "country_name": "India",
        "subclass_id": "TRN",
        "subclass_name": "Transit Visa (T)",
        "service_type": "transit",
        "category": "immigration",
        "description": (
            "The Transit (T) Visa is for foreign nationals passing through India on their way to a "
            "third country, with maximum stay of 72 hours (3 days) per transit. Issued as single or "
            "double entry, valid 15 days from issuance. Cheaper and faster than full Tourist Visa "
            "for genuine layovers / multi-stop itineraries.\n\n"
            "Required only if planning to exit airport / leave international transit zone. Direct "
            "airside transits without exiting do NOT need Transit Visa. Some nationalities are "
            "exempt (e.g., diplomatic travellers under specific agreements)."
        ),
        "eligibility_summary": (
            "Foreign national in genuine transit to a third country, with confirmed onward ticket "
            "within 72 hours of arrival in India. Purpose strictly layover / short stop, not "
            "tourism or business."
        ),
        "eligibility_criteria": [
            {"label": "Genuine transit", "value": "Confirmed onward ticket to a third country within 72 hours", "notes": "Round-trip to home country NOT transit"},
            {"label": "Maximum stay", "value": "72 hours (3 days) per transit", "notes": "Exceeding requires Tourist / Business Visa"},
            {"label": "Single / Double entry", "value": "Choose based on round-trip transit needs", "notes": "Double entry useful for return journey transit"},
            {"label": "Visa validity", "value": "15 days from issuance", "notes": "Must use within validity"},
            {"label": "Onward visa", "value": "Valid visa for destination country (if required)", "notes": "Immigration checks at port of entry"},
            {"label": "No employment / business", "value": "Cannot engage in any commercial activity", "notes": "Strict transit purpose"},
            {"label": "Yellow fever vaccination", "value": "If transiting from endemic country", "notes": "Required by Indian health regulations"},
            {"label": "Children", "value": "Each child needs own Transit Visa", "notes": "No inclusion in parent's"},
        ],
        "fees_local_currency_code": "USD",
        "fees_local_currency_amount": 10,
        "fees_inr_approx": 830,
        "fees_breakdown": [
            {"component": "Transit Visa — Single Entry (most nationalities)", "amount": 10, "currency": "USD"},
            {"component": "Transit Visa — Double Entry (most nationalities)", "amount": 20, "currency": "USD"},
            {"component": "Transit Visa — Japanese nationals", "amount": 1, "currency": "USD"},
            {"component": "ICWF surcharge", "amount": 3, "currency": "USD"},
            {"component": "VFS Service Fee", "amount": 19, "currency": "USD"},
            {"component": "Bank transaction charge (2.5%)", "amount": 1, "currency": "USD"},
        ],
        "processing_time_days_min": 3,
        "processing_time_days_max": 7,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Genuine Transit Need", "description": "Verify onward journey to third country within 72 hours of India arrival. Confirm onward ticket + destination visa.", "estimated_days": 1, "documents_needed": ["Onward ticket", "Destination country visa (if applicable)"], "tips": ["Stay <24h = airside transit (no visa); 24-72h = Transit Visa; >72h = Tourist Visa"]},
            {"step_number": 2, "title": "Online Application at indianvisaonline.gov.in", "description": "Apply for Transit Visa. Choose single / double entry.", "estimated_days": 1, "documents_needed": ["Passport scan", "Photo", "Signature", "Onward ticket"], "tips": ["Double entry useful for round-trip transits via India"]},
            {"step_number": 3, "title": "VFS / Mission Submission", "description": "Submit application, biometrics, fees.", "estimated_days": 3, "documents_needed": ["Onward ticket", "Destination visa", "Travel itinerary"], "tips": ["Demonstrate genuine transit (not extended tourism in disguise)"]},
            {"step_number": 4, "title": "Visa Issuance", "description": "3-7 days processing. Sticker visa in passport.", "estimated_days": 5, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Transit Through India + Exit Within 72 Hours", "description": "Arrive in India, complete transit / brief layover, depart to third country within 72 hours.", "estimated_days": 1, "documents_needed": ["Passport with visa", "Onward boarding pass"], "tips": ["Carry full itinerary at port of entry — immigration may check", "Avoid extending stay — overstay penalties + future visa difficulties"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages) — valid 6+ months", "mandatory": True, "notes": ""},
            {"name": "Passport-size photograph", "mandatory": True, "notes": ""},
            {"name": "Signature image", "mandatory": True, "notes": ""},
            {"name": "Confirmed onward ticket to third country", "mandatory": True, "notes": "Within 72 hours of India arrival"},
            {"name": "Destination country visa (if required for third country)", "mandatory": True, "notes": "Immigration officer verifies"},
            {"name": "Travel itinerary (complete journey)", "mandatory": True, "notes": ""},
            {"name": "Accommodation booking (for layover, if applicable)", "mandatory": False, "notes": ""},
            {"name": "Yellow fever vaccination (if from endemic country)", "mandatory": False, "notes": ""},
            {"name": "Bank statements (financial sufficiency for layover)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "No confirmed onward ticket to third country",
            "Destination country visa missing / invalid",
            "Itinerary suggests extended stay rather than transit (>72 hours)",
            "Round-trip back to home country (not genuine transit)",
            "Past overstay / immigration violation",
            "Application appears to disguise tourism as transit",
        ],
        "success_tips": [
            "Plan transit duration carefully — 72 hours hard limit",
            "Get destination visa BEFORE applying for India transit — Indian mission verifies",
            "Choose double entry if returning via India — same fee structure",
            "Avoid Transit Visa for layovers under 24 hours — airside transit doesn't need visa",
            "For longer stays / sightseeing, opt for e-Tourist Visa (e-TV) at USD 25 — better value",
            "Carry full itinerary printed + on phone at port of entry",
            "Yellow fever vaccination cert critical if transiting from endemic countries",
        ],
        "faqs": [
            {"q": "Do I need a Transit Visa for short layover?", "a": "Only if you exit the airport / leave international transit zone. Airside transit (staying in international zone) typically doesn't need Transit Visa. Confirm with airline + immigration."},
            {"q": "Can I do tourism during transit?", "a": "Limited — quick local visit during layover is fine, but anything beyond 72 hours requires e-Tourist / Tourist Visa. Don't risk extending stay."},
            {"q": "What about my round-trip via India?", "a": "Use Double Entry Transit Visa (USD 20) — covers both legs. Or get e-Tourist Visa if you want flexibility for sightseeing on either leg."},
            {"q": "How is Transit Visa different from e-Tourist Visa?", "a": "Transit: cheap (USD 10), max 72hrs, strictly transit. e-TV: USD 25, 30+ days, full tourism rights. For genuine layover use Transit; for any flexibility use e-TV."},
            {"q": "Can I extend Transit Visa in India?", "a": "NO. Transit Visa is non-extendable. Exit India within 72 hours or face overstay penalties. Apply for proper category visa if longer stay needed."},
        ],
        "official_url": "https://indianvisaonline.gov.in/visa/visa-fee.html",
        "vfs_url": "https://www.vfsglobal.com/india/",
        "source_urls": [
            "https://indianvisaonline.gov.in/visa/visa-fee.html",
            "https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf",
            "https://www.indianeagle.com/traveldiary/transit-visa-india-complete-guide-for-smooth-international-travel/",
        ],
        "verified_notes": "Manual Fast-Path B.4.2 seed — verified against indianvisaonline.gov.in + MHA Annex III on 2026-02-27. Country-specific Transit fees per various Mission notices.",
    },
]


ALL_WORKFLOWS: Dict[str, List[Dict[str, Any]]] = {
    "IN": INDIA_WORKFLOWS,
}


# ──────────────────────────────────────────────────────────────────────────────
# Main runner — mirrors b2.py main() pattern but for B.4 sub-slices
# ──────────────────────────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="Sweep B.4 Mega Dispatch country workflow seeder")
    parser.add_argument("--country", type=str, default=None, help="ISO-2 country code to seed (e.g. IN)")
    parser.add_argument("--all", action="store_true", help="Seed all B.4 countries currently defined")
    parser.add_argument("--backfill", type=str, default=None, help="One-shot backfill: add doc_id + rewrite legacy audit_logs for given ISO-2 code")
    args = parser.parse_args()

    load_dotenv()
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    admin = await db.users.find_one({"email": "admin@leamss.com"}, {"_id": 0, "id": 1, "name": 1})
    if not admin:
        print("❌ Admin user not found — cannot seed (verified_by would be null).")
        return
    seeded_by_id = admin["id"]
    seeded_by_name = admin.get("name", "Admin User")

    # ── BACKFILL MODE ─────────────────────────────────────────────────────────
    if args.backfill:
        cc = args.backfill.upper()
        print("\n══════════════════════════════════════════════")
        print(f"  BACKFILL {cc} — doc_id + canonical audit_logs")
        print("══════════════════════════════════════════════")
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

    # B.4 uses ALL_WORKFLOWS local to this module; we monkey-patch into the b2
    # seeder's expected location so it picks up our IN workflows for seeding.
    import scripts.seed_country_workflows_b2 as b2
    for cc, wfs in ALL_WORKFLOWS.items():
        b2.ALL_WORKFLOWS[cc] = wfs

    totals = {"inserted": 0, "skipped": 0, "errored": 0}
    for cc in targets:
        print("\n══════════════════════════════════════════════")
        print(f"  SEEDING {cc} (B.4) — {len(ALL_WORKFLOWS.get(cc, []))} workflows")
        print("══════════════════════════════════════════════")
        res = await seed_country(db, cc, seeded_by_id, seeded_by_name)
        totals["inserted"] += res["inserted"]
        totals["skipped"] += res["skipped"]
        totals["errored"] += res["errored"]
        print(f"[{cc}] Summary: inserted={res['inserted']} skipped={res['skipped']} errored={res['errored']}")

    print("\n══════════════════════════════════════════════")
    print(f"  TOTAL: inserted={totals['inserted']} skipped={totals['skipped']} errored={totals['errored']}")
    print("══════════════════════════════════════════════\n")


if __name__ == "__main__":
    asyncio.run(main())
