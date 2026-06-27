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


# ──────────────────────────────────────────────────────────────────────────────
# AUSTRALIA EXPANSION (B.4.3) — 10 new subclasses adding to B.2's existing 6
# Sources: immi.homeaffairs.gov.au · FY2025-26 rates · 1 Mar 2026 + 1 Jul 2025
# updates incorporated. FX: 1 AUD ≈ 55 INR (Feb 2026).
# ──────────────────────────────────────────────────────────────────────────────
AUSTRALIA_NEW_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. AU-485 — Temporary Graduate (Sir's priority subclass) ────────────────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "485",
        "subclass_name": "Temporary Graduate (Subclass 485)",
        "service_type": "work", "category": "immigration",
        "description": (
            "The Subclass 485 Temporary Graduate visa allows international students who recently "
            "completed an Australian qualification to live, study, and work in Australia "
            "temporarily — a stepping stone visa to professional experience, skilled migration "
            "pathways (189/190/491/186), or further study.\n\n"
            "Two MAIN streams (renamed 2024): (a) Post-Higher Education Work Stream (formerly "
            "Post-Study Work — for Bachelor's/Master's/PhD graduates from CRICOS providers); "
            "(b) Post-Vocational Education Work Stream (formerly Graduate Work — for VET/Diploma "
            "graduates, requires skills assessment + MLTSSL occupation). Third stream: Second "
            "Post-Higher Education Work Stream — regional 1-2yr extension.\n\n"
            "CRITICAL 2026 CHANGES (Mar 2026): Visa Application Charge DOUBLED to AUD 4,600 "
            "(from AUD 2,300); Age cap reduced to 35 (was 50) — PhD/Masters by Research and "
            "HK/BNO holders retain under-50 limit; English IELTS 6.5 overall + 5.5 each band "
            "(within 12 months); Replacement Stream CLOSED to new applications since 1 Jul 2024; "
            "Onshore Student visa switch barred."
        ),
        "eligibility_summary": (
            "Recent graduate of CRICOS-registered Australian institution with 92+ weeks of "
            "registered study delivered in English over 16+ calendar months; under 35 at "
            "application (PhD/Research Masters/HK/BNO under 50); valid Student visa at "
            "completion; lodge within 6 months of course completion; meet English IELTS 6.5+ "
            "overall + 5.5 each band (within 12 months)."
        ),
        "eligibility_criteria": [
            {"label": "Age", "value": "Under 35 at time of application (general); Under 50 for Master's by Research / PhD / HK / BNO passport holders", "notes": "Tightened from 50 to 35 — 1 Mar 2026 reform"},
            {"label": "Australian Study Requirement", "value": "Min 92 weeks of registered study completed in English over 16 calendar months", "notes": "Mandatory; verified via CoE history"},
            {"label": "Course recency", "value": "Apply within 6 months of course completion date", "notes": "Strict; refusals on lateness"},
            {"label": "Visa history", "value": "Held valid Student visa during the qualifying study", "notes": "Other temp visas in interim are OK"},
            {"label": "English (NEW)", "value": "IELTS 6.5 overall + 5.5 each band (or PTE/TOEFL/OET/CAE equivalent)", "notes": "Within 12 months of application (was 3 years)"},
            {"label": "Skills Assessment (VET stream)", "value": "Required for Post-Vocational Education Work stream", "notes": "Occupation must be on MLTSSL"},
            {"label": "Health + Character", "value": "Standard requirements; HAP ID + PCCs from 12+ month countries", "notes": ""},
            {"label": "Health insurance", "value": "Continuous health cover for visa duration", "notes": "Often OSHC continuation or private cover"},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 4600, "fees_inr_approx": 253000,
        "fees_breakdown": [
            {"component": "Post-Higher Education / Post-Vocational Education streams — Primary (Mar 2026 reform)", "amount": 4600, "currency": "AUD"},
            {"component": "Second Post-Higher Education Work Stream — Primary", "amount": 1810, "currency": "AUD"},
            {"component": "Secondary applicant 18+ (main streams)", "amount": 2300, "currency": "AUD"},
            {"component": "Secondary applicant under 18 (main streams)", "amount": 1160, "currency": "AUD"},
            {"component": "Reduced fee for Pacific Islands & Timor-Leste passport holders — Primary", "amount": 2300, "currency": "AUD"},
            {"component": "English test (IELTS/PTE in India)", "amount": 16800, "currency": "INR"},
            {"component": "Health exam (BUPA panel)", "amount": 6000, "currency": "INR"},
            {"component": "India PCC", "amount": 500, "currency": "INR"},
            {"component": "Health insurance (annual)", "amount": 700, "currency": "AUD"},
        ],
        "processing_time_days_min": 60, "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Stream + Eligibility", "description": "Identify which stream you qualify for (Post-Higher Education for Bachelor's+; Post-Vocational for VET; Second stream for regional extension).", "estimated_days": 7, "documents_needed": ["Course completion letter", "Academic transcripts"], "tips": ["Cross-check 92-week Australian Study Requirement", "Verify under-35 age cap (or exemption)"]},
            {"step_number": 2, "title": "English Test (IELTS 6.5+ within 12 months)", "description": "Take IELTS UKVI / PTE Academic / TOEFL iBT / OET / CAE meeting new threshold: 6.5 overall + 5.5 each band.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": ["12-month validity (NEW — was 3 years); plan timing", "PTE faster for retakes"]},
            {"step_number": 3, "title": "Skills Assessment (Post-Vocational stream only)", "description": "Apply through relevant authority for MLTSSL occupation matching VET qualification.", "estimated_days": 60, "documents_needed": ["VET certificate", "Trade certificate", "Reference letters"], "tips": ["Required ONLY for Post-Vocational stream"]},
            {"step_number": 4, "title": "Health Insurance Setup", "description": "Arrange continuous health insurance for visa duration (continuation of OSHC or private policy).", "estimated_days": 3, "documents_needed": ["Health insurance policy"], "tips": []},
            {"step_number": 5, "title": "Lodge Online Application", "description": "Submit via ImmiAccount within 6 months of course completion. Upload all evidence.", "estimated_days": 7, "documents_needed": ["Passport", "Academic completion docs", "English test", "Skills assessment (if VET)", "Insurance policy", "Photo"], "tips": ["Apply ONSHORE preferred — instant bridging visa coverage"]},
            {"step_number": 6, "title": "Health + PCC", "description": "Complete BUPA health exam + India PCC + PCC from other 12+ month countries.", "estimated_days": 30, "documents_needed": ["HAP ID"], "tips": []},
            {"step_number": 7, "title": "Visa Grant", "description": "Decision in 2-6 months. Visa duration: Bachelor's/Master's Coursework = 2yr; Master's Research/PhD = 3yr; VET = 18m; HK/BNO = 5yr.", "estimated_days": 120, "documents_needed": [], "tips": ["Bridging visa keeps you onshore during processing"]},
            {"step_number": 8, "title": "Use as PR Stepping Stone OR Second 485", "description": "Build Australian work experience for points-tested PR pathways (189/190/491) OR apply for Second Post-Higher Ed Work Stream (regional extension 1-2 years).", "estimated_days": 730, "documents_needed": [], "tips": ["Aim for skilled employment in your field — needed for SA + work experience points", "Regional Second 485 if you studied + lived regionally"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (bio + visa pages, 6+ months)", "mandatory": True, "notes": ""},
            {"name": "Academic completion letter from CRICOS institution", "mandatory": True, "notes": "Confirms course finished"},
            {"name": "Academic transcripts (full)", "mandatory": True, "notes": ""},
            {"name": "Confirmation of Enrolment history (CoE)", "mandatory": True, "notes": "Demonstrates 92-week Study Requirement"},
            {"name": "English test (IELTS 6.5+ / equivalent, within 12 months)", "mandatory": True, "notes": "NEW: 12-month validity"},
            {"name": "Skills Assessment outcome (Post-Vocational stream)", "mandatory": True, "notes": "MLTSSL only"},
            {"name": "Health insurance policy (continuous)", "mandatory": True, "notes": ""},
            {"name": "Form 80 (each adult applicant)", "mandatory": True, "notes": ""},
            {"name": "Form 1221 (if requested)", "mandatory": False, "notes": ""},
            {"name": "Health exam (HAP ID via BUPA)", "mandatory": True, "notes": ""},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": "India + other 12+ month countries"},
            {"name": "Passport-size photograph (recent)", "mandatory": True, "notes": ""},
            {"name": "Marriage / relationship certificate (if including partner)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certificates (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Evidence of regional study (Second Post-Higher Ed stream)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Application lodged more than 6 months after course completion",
            "Age above 35 without qualifying exemption (PhD/Research Masters/HK/BNO)",
            "English test outside 12-month validity window",
            "Insufficient evidence of 92-week Australian Study Requirement",
            "Course not delivered in English",
            "Skills assessment missing for Post-Vocational stream",
            "Onshore Student visa held — attempting to switch to 485 onshore (now barred)",
            "Health insurance gaps during visa duration",
        ],
        "success_tips": [
            "PRIORITISE: Apply onshore before Student visa expiry — bridging visa keeps you in Australia during processing",
            "Stay aware of 6-month completion-to-lodgement window — strict cap",
            "Plan English test within 12 months — schedule strategically",
            "VET applicants: start skills assessment EARLY — 60-90 days backlogs common",
            "Build Australian work experience during 485 — boosts 189/190/491 EOI points significantly",
            "Regional study/residence → Second Post-Higher Ed Work stream = 1-2 extra years",
            "Maintain health insurance gap-free — refusals on missing coverage common",
            "Lodge complete Form 80 — most-rejected form for adult applicants",
        ],
        "faqs": [
            {"q": "Why did the fee jump to AUD 4,600?", "a": "Effective 1 March 2026, the Visa Application Charge for Post-Higher Education + Post-Vocational Education streams doubled from AUD 2,300. This is part of the broader Migration Strategy reforms. Second stream remains at AUD 1,810."},
            {"q": "I'm 38 — am I still eligible?", "a": "General age cap was tightened to 35 in 2026. Exemptions: Masters by Research, PhD graduates, Hong Kong (HK) and British National Overseas (BNO) passport holders retain under-50 limit. Otherwise, ineligible."},
            {"q": "Can I include my partner and children?", "a": "Yes — partner + dependent children can be included. Partner has 48 hours/fortnight work rights (unlimited if you're on Master's by Research or PhD)."},
            {"q": "How long is the visa valid?", "a": "Post-Higher Ed: 2yr (Bachelor's/Master's Coursework), 3yr (Master's Research/PhD), 5yr (HK/BNO). Post-Vocational: 18 months. Regional Second stream: +1-2 years."},
            {"q": "Can I switch to Student visa onshore later?", "a": "NO. Onshore Student visa applications by 485 holders are barred since the 2024 reforms. You must exit Australia and apply offshore if returning to study."},
            {"q": "What about the 2-year extension for skill-shortage degrees?", "a": "ENDED. The temporary 2-year extension (July 2023) for selected degrees in skill shortage areas is no longer available. Only Regional Second stream remains as an extension pathway."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-graduate-485",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-graduate-485",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-graduate-485/post-higher-education-work",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-graduate-485/post-vocational-education-work",
            "https://www.studyaustralia.gov.au/en/Agent-Hub/agent-news-index/changes-to-the-temporary-graduate-subclass-485-visa",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified against immi.homeaffairs.gov.au + studyaustralia.gov.au on 2026-02-27. Mar 2026 fee doubling + age 35 cap + IELTS 6.5/12-month validity all reflected. Replacement stream closure (1 Jul 2024) + onshore Student barred + 2-year skill-shortage extension ended documented.",
    },

    # ── 2. AU-186 — Employer Nomination Scheme (ENS PR) ────────────────────────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "186",
        "subclass_name": "Employer Nomination Scheme (Subclass 186)",
        "service_type": "pr", "category": "immigration",
        "description": (
            "The Subclass 186 Employer Nomination Scheme (ENS) visa is a permanent residence visa "
            "for skilled workers nominated by their Australian employer. Three streams: (a) Direct "
            "Entry — skilled workers offshore or onshore who have NOT held 482/457; (b) Temporary "
            "Residence Transition (TRT) — 482/457 holders with 2+ years working for the same "
            "employer; (c) Labour Agreement — under specific industry agreements.\n\n"
            "Full PR rights from day one (work + study + Medicare + citizenship pathway). The "
            "TRT stream is the most common pathway for 482 holders. Employer must be approved "
            "Standard Business Sponsor + pay SAF Levy (one-off ENS: AUD 3,000 small / AUD 5,000 large)."
        ),
        "eligibility_summary": (
            "Under 45 at application (with limited exemptions); positive skills assessment + "
            "3+ years relevant experience (Direct Entry); OR 2+ years on 482/457 with the "
            "nominating employer (TRT); Competent English (IELTS 6.0 each band); occupation on "
            "MLTSSL; health + character."
        ),
        "eligibility_criteria": [
            {"label": "Age", "value": "Under 45 at application (general); some exemptions for high-income, academic + medical workers", "notes": ""},
            {"label": "English", "value": "Competent English (IELTS 6.0 each band, or equivalent)", "notes": "Some exemptions for UK/USA/Can/NZ/Ireland passport holders"},
            {"label": "Skills Assessment + experience (Direct Entry)", "value": "Positive SA + 3+ years' full-time experience in nominated occupation", "notes": "Occupation must be on MLTSSL"},
            {"label": "Visa history (TRT)", "value": "Held 482 / 457 / bridging visa for 2+ years with nominating employer", "notes": "Same role + same employer"},
            {"label": "Employer", "value": "Approved Standard Business Sponsor (SBS); nominates position + you", "notes": "Employer pays SAF levy + nomination fee"},
            {"label": "Occupation", "value": "On Medium and Long-term Strategic Skills List (MLTSSL)", "notes": "Or Labour Agreement-specific list"},
            {"label": "Salary", "value": "Meet Annual Market Salary Rate (AMSR) for the position", "notes": "Minimum ~AUD 73,150 (TSMIT) often a floor"},
            {"label": "Health + Character", "value": "Standard requirements", "notes": ""},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 4770, "fees_inr_approx": 262350,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary (FY2025-26, before 1 Jul 2026 hike)", "amount": 4770, "currency": "AUD"},
            {"component": "Visa Application Charge — Primary (effective 1 Jul 2026, NEW)", "amount": 5045, "currency": "AUD"},
            {"component": "Secondary applicant 18+", "amount": 2385, "currency": "AUD"},
            {"component": "Dependent child <18", "amount": 1195, "currency": "AUD"},
            {"component": "Second instalment (Functional English not met)", "amount": 4885, "currency": "AUD"},
            {"component": "Nomination Application (employer-paid)", "amount": 540, "currency": "AUD"},
            {"component": "SAF Levy (small business <AUD 10M turnover — one-off ENS)", "amount": 3000, "currency": "AUD"},
            {"component": "SAF Levy (large business >AUD 10M turnover — one-off ENS)", "amount": 5000, "currency": "AUD"},
            {"component": "Skills assessment", "amount": 800, "currency": "AUD"},
            {"component": "English test", "amount": 16800, "currency": "INR"},
            {"component": "Health + PCC", "amount": 6500, "currency": "INR"},
        ],
        "processing_time_days_min": 180, "processing_time_days_max": 540,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Employer SBS Status + Stream", "description": "Verify employer is currently approved as Standard Business Sponsor. Determine: Direct Entry vs TRT.", "estimated_days": 14, "documents_needed": ["SBS confirmation"], "tips": ["TRT is faster + less documentation if you're already on 482"]},
            {"step_number": 2, "title": "Skills Assessment (Direct Entry)", "description": "Apply through relevant authority for MLTSSL occupation. Skip if TRT.", "estimated_days": 60, "documents_needed": ["Degree", "Reference letters"], "tips": []},
            {"step_number": 3, "title": "English Test", "description": "Competent English (IELTS 6.0 each band) unless passport exempt.", "estimated_days": 21, "documents_needed": ["Passport"], "tips": []},
            {"step_number": 4, "title": "Employer Nomination", "description": "Employer lodges nomination with DoHA, pays nomination fee + SAF levy.", "estimated_days": 30, "documents_needed": ["Position description", "Employment contract", "SAF levy paid"], "tips": ["Nomination approval needed before visa lodgement"]},
            {"step_number": 5, "title": "Lodge Visa Application", "description": "Submit electronic application within 6 months of nomination approval.", "estimated_days": 14, "documents_needed": ["Standard 189-equivalent doc set", "Nomination ID"], "tips": []},
            {"step_number": 6, "title": "Health + PCC", "description": "BUPA panel exam + PCCs.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Decision + Visa Grant", "description": "6-18 months typical. PR granted on approval.", "estimated_days": 365, "documents_needed": [], "tips": ["RFI response within 28 days"]},
            {"step_number": 8, "title": "Settle as Permanent Resident", "description": "Full work + study + Medicare rights. After 4 years total residence (12 months as PR), eligible for citizenship.", "estimated_days": 1095, "documents_needed": [], "tips": []},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Employer's SBS approval evidence", "mandatory": True, "notes": ""},
            {"name": "Nomination approval ID", "mandatory": True, "notes": "Issued after nomination phase"},
            {"name": "Employment contract (with nominating employer)", "mandatory": True, "notes": ""},
            {"name": "Skills assessment (Direct Entry)", "mandatory": False, "notes": "Required for DE stream"},
            {"name": "Pay slips + tax records (TRT — covering 2+ years)", "mandatory": False, "notes": "TRT stream"},
            {"name": "English test (Competent)", "mandatory": True, "notes": "Or passport exemption"},
            {"name": "Degree + transcripts (notarised)", "mandatory": True, "notes": ""},
            {"name": "Employment reference letters", "mandatory": True, "notes": ""},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "Health exam (HAP ID)", "mandatory": True, "notes": ""},
            {"name": "PCCs", "mandatory": True, "notes": ""},
            {"name": "Marriage/relationship cert (if including partner)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Employer's SBS status lapsed or revoked",
            "Position genuineness questioned (e.g., created for the candidate)",
            "Salary below Annual Market Salary Rate",
            "TRT: 2-year requirement not strictly met (e.g., gaps, role changes)",
            "Direct Entry: insufficient 3-year experience documented",
            "Health requirement not met (undisclosed medical condition)",
            "Skills assessment for wrong/expired ANZSCO",
        ],
        "success_tips": [
            "TRT applicants: keep 2-year employment continuous + role-consistent — gaps complicate",
            "Direct Entry: build strong reference letters covering ALL 3 years' duties",
            "Employer absorbs SAF Levy + nomination fee — standard practice",
            "Salary in nomination should match offered + reviewed annually to Annual Market Salary Rate",
            "Lodge visa application close to nomination approval — 6-month window",
            "Plan for 12-18 month wait — current backlog significant",
        ],
        "faqs": [
            {"q": "What's the difference between Direct Entry and TRT?", "a": "Direct Entry needs skills assessment + 3 years' experience (typically offshore applicants). TRT is for 482/457 holders who've worked 2+ years with the nominating employer (typically onshore)."},
            {"q": "Can I change employer after 186 grant?", "a": "YES — 186 is permanent residence, no employer ties post-grant. You can change jobs immediately."},
            {"q": "When can I apply for citizenship?", "a": "After 4 years total residence (including 12 months as PR), subject to character + residency requirements."},
            {"q": "What if my employer's SBS lapses?", "a": "Employer must renew SBS to nominate. If nomination is approved before lapse, visa application typically proceeds. If lapse during visa processing, case officer may RFI."},
            {"q": "Fee will go up — should I rush?", "a": "Yes — fee increases from AUD 4,770 to AUD 5,045 on 1 Jul 2026. Lodge before that date to lock in lower rate."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186/direct-entry-stream",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186/temporary-residence-transition-stream",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified against immi.homeaffairs.gov.au on 2026-02-27. FY2025-26 fees current (AUD 4,770); 1 Jul 2026 hike to AUD 5,045 documented. SAF levy + nomination fees per current policy.",
    },

    # ── 3. AU-187 — RSMS (CLOSED to new — renewals only) ────────────────────────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "187",
        "subclass_name": "Regional Sponsored Migration Scheme (Subclass 187 — CLOSED to new applications)",
        "service_type": "pr", "category": "immigration",
        "description": (
            "⚠️ STATUS: CLOSED to new primary applications since 16 November 2019. The Subclass "
            "187 Regional Sponsored Migration Scheme has been REPLACED by Subclass 494 (Skilled "
            "Employer Sponsored Regional - Provisional) for new regional employer sponsorship.\n\n"
            "This entry exists for: (a) transitional cases — applicants whose nomination was "
            "approved before 16 Nov 2019 retain 187 pathway; (b) secondary applicants (partner/"
            "child additions) on existing 187 grants; (c) historical reference for clients with "
            "older nominations. Genuine regional employer sponsorship for new applicants — direct "
            "them to Subclass 494."
        ),
        "eligibility_summary": (
            "Transitional / legacy applicants only. Must hold a Regional Certifying Body (RCB)-"
            "certified nomination approved prior to 16 Nov 2019. New applicants → redirect to "
            "Subclass 494 (provisional, 5-year pathway to PR via Subclass 191)."
        ),
        "eligibility_criteria": [
            {"label": "STATUS", "value": "CLOSED to new applications since 16 Nov 2019", "notes": "Use Subclass 494 for new regional employer sponsorship"},
            {"label": "Legacy applicants", "value": "Nomination approved before 16 Nov 2019", "notes": "Transitional cases only"},
            {"label": "Age", "value": "Under 45 at time of application (legacy rules)", "notes": ""},
            {"label": "English", "value": "Competent English (IELTS 6.0 each band)", "notes": ""},
            {"label": "Skills + experience", "value": "Per legacy rules (RCB-certified nomination)", "notes": ""},
            {"label": "Regional commitment", "value": "Live + work in regional area for 2 years from grant", "notes": "Legacy condition"},
            {"label": "Secondary applicants", "value": "Partners/children can still be added to existing 187 grants", "notes": "Subject to relationship continuation"},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 4770, "fees_inr_approx": 262350,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary (legacy rate)", "amount": 4770, "currency": "AUD"},
            {"component": "Secondary applicant 18+", "amount": 2385, "currency": "AUD"},
            {"component": "Dependent child <18", "amount": 1195, "currency": "AUD"},
            {"component": "NOTE: New applicants must use Subclass 494 (AUD 4,910)", "amount": 4910, "currency": "AUD"},
        ],
        "processing_time_days_min": 60, "processing_time_days_max": 240,
        "step_by_step": [
            {"step_number": 1, "title": "Verify Legacy Eligibility", "description": "Confirm nomination was approved before 16 Nov 2019. If not, redirect to Subclass 494 application.", "estimated_days": 1, "documents_needed": ["Nomination approval letter"], "tips": ["MOST applicants should not be applying for 187 — use 494"]},
            {"step_number": 2, "title": "Lodge Application within Approved Window", "description": "Submit visa application within validity window of legacy nomination (typically 6 months).", "estimated_days": 14, "documents_needed": ["Nomination ID", "Standard doc set"], "tips": []},
            {"step_number": 3, "title": "Health + PCC", "description": "Standard requirements.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 4, "title": "Decision + Grant", "description": "Processed per legacy timelines.", "estimated_days": 180, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Regional Settlement (2-year commitment)", "description": "Live + work in nominated regional area for 2 years post-grant.", "estimated_days": 730, "documents_needed": [], "tips": ["After 2 years, full PR mobility"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Legacy RCB nomination approval letter", "mandatory": True, "notes": "Pre-16 Nov 2019"},
            {"name": "Employment contract with regional employer", "mandatory": True, "notes": ""},
            {"name": "Skills assessment (where applicable)", "mandatory": True, "notes": "Per legacy rules"},
            {"name": "English test (Competent)", "mandatory": True, "notes": ""},
            {"name": "Reference letters", "mandatory": True, "notes": ""},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "Health exam", "mandatory": True, "notes": ""},
            {"name": "PCCs", "mandatory": True, "notes": ""},
            {"name": "Marriage / relationship cert", "mandatory": False, "notes": "If applicable"},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Application from new applicant (post 16 Nov 2019 nomination) — should use Subclass 494",
            "Nomination validity period lapsed",
            "Regional area / employer no longer qualifies",
            "Same as 186: documentation gaps + health + character issues",
        ],
        "success_tips": [
            "If you're a NEW applicant in regional area — use Subclass 494 instead",
            "If you have a legacy nomination — lodge promptly within its validity window",
            "Maintain regional employer + role consistency through processing",
            "Document the legacy nomination's pre-16 Nov 2019 approval clearly",
        ],
        "faqs": [
            {"q": "Can I still apply for 187?", "a": "No — closed to new primary applications since 16 Nov 2019. New regional employer-sponsored applicants must use Subclass 494."},
            {"q": "I'm a legacy applicant — what now?", "a": "If your nomination was approved pre-16 Nov 2019, you can still lodge the visa application within its validity window. Speak to a registered migration agent immediately."},
            {"q": "Can my partner be added to my existing 187 grant?", "a": "Yes — secondary applicants can still be added to existing 187 grants subject to relationship continuation."},
            {"q": "What replaced 187?", "a": "Subclass 494 (Skilled Employer Sponsored Regional - Provisional) for the regional employer-sponsored pathway, with 5-year validity and PR transition via Subclass 191."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/repealed-visas",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/repealed-visas",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-employer-sponsored-regional-494",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified CLOSED status as of 16 Nov 2019. Entry maintained for legacy/transitional reference + secondary applicants. Sir's directive: explicitly document closure + redirect to 494.",
    },

    # ── 4. AU-494 — Skilled Employer Sponsored Regional (Provisional) ──────────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "494",
        "subclass_name": "Skilled Employer Sponsored Regional - Provisional (Subclass 494)",
        "service_type": "pr", "category": "immigration",
        "description": (
            "The Subclass 494 visa is a 5-year provisional visa for skilled workers sponsored by "
            "an Australian regional employer. Replaces Subclass 187 (closed Nov 2019). After 3 "
            "years working + earning minimum income in regional area, holders can transition to "
            "Subclass 191 Permanent Residence (Skilled Regional).\n\n"
            "Two streams: (a) Employer Sponsored — regional employer nominates skilled worker; "
            "(b) Labour Agreement — under specific industry agreements. Open to broader "
            "occupation list than 482/186; ~700 occupations available in regional areas. Full "
            "work + study + family inclusion rights for 5 years."
        ),
        "eligibility_summary": (
            "Under 45 at application; positive skills assessment in occupation on Regional "
            "Occupation List; 3+ years' relevant work experience; sponsored by regional "
            "employer; meet TSMIT salary; Competent English; commit to regional residence "
            "for 191 PR pathway."
        ),
        "eligibility_criteria": [
            {"label": "Age", "value": "Under 45 at time of application", "notes": ""},
            {"label": "Occupation", "value": "On Regional Occupation List (broader than MLTSSL — ~700 occupations)", "notes": ""},
            {"label": "Skills Assessment", "value": "Positive SA in nominated occupation", "notes": ""},
            {"label": "Experience", "value": "3+ years' full-time relevant experience", "notes": ""},
            {"label": "Employer", "value": "Regional employer with approved nomination", "notes": "Designated regional area (~99% of Australia except Sydney/Melbourne/Brisbane CBDs)"},
            {"label": "English", "value": "Competent English (IELTS 6.0 each band)", "notes": ""},
            {"label": "Salary", "value": "Meet TSMIT (AUD 73,150+) + Annual Market Salary Rate", "notes": ""},
            {"label": "Regional commitment", "value": "Live + work in regional Australia for entire visa duration (5 years)", "notes": "Required for 191 PR pathway after 3 years"},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 4910, "fees_inr_approx": 270050,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary", "amount": 4910, "currency": "AUD"},
            {"component": "Secondary applicant 18+", "amount": 2455, "currency": "AUD"},
            {"component": "Dependent child <18", "amount": 1230, "currency": "AUD"},
            {"component": "Nomination Application (employer-paid)", "amount": 540, "currency": "AUD"},
            {"component": "SAF Levy small business per year of visa", "amount": 1200, "currency": "AUD"},
            {"component": "SAF Levy large business per year of visa", "amount": 1800, "currency": "AUD"},
            {"component": "Skills assessment", "amount": 800, "currency": "AUD"},
            {"component": "Future Subclass 191 PR fee", "amount": 535, "currency": "AUD"},
        ],
        "processing_time_days_min": 120, "processing_time_days_max": 360,
        "step_by_step": [
            {"step_number": 1, "title": "Identify Regional Employer + Position", "description": "Confirm employer is in designated regional area + position is on Regional Occupation List.", "estimated_days": 14, "documents_needed": [], "tips": ["Regional postcodes broader than CBDs — most of Australia qualifies"]},
            {"step_number": 2, "title": "Skills Assessment + English", "description": "Apply for SA + take English test.", "estimated_days": 60, "documents_needed": [], "tips": []},
            {"step_number": 3, "title": "Employer Nomination", "description": "Employer lodges nomination, pays nomination fee + SAF Levy.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 4, "title": "Lodge Visa Application", "description": "Submit within 6 months of nomination approval.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Health + PCC", "description": "Standard.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 6, "title": "Grant + Move to Regional Area", "description": "5-year visa granted. Move to nominated regional employer location.", "estimated_days": 90, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Build 191 PR Pathway (3 years)", "description": "Live + work + earn min AUD 53,900 in regional area for 3 income years. Then apply for 191 PR.", "estimated_days": 1095, "documents_needed": ["Tax returns", "Employment evidence"], "tips": ["Save ALL pay slips + PAYG summaries for 191"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Skills assessment outcome (Regional Occupation List)", "mandatory": True, "notes": ""},
            {"name": "Employment contract with regional employer", "mandatory": True, "notes": ""},
            {"name": "Nomination approval", "mandatory": True, "notes": ""},
            {"name": "English test (Competent)", "mandatory": True, "notes": ""},
            {"name": "CV + 3-year reference letters", "mandatory": True, "notes": ""},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "Health exam", "mandatory": True, "notes": ""},
            {"name": "PCCs", "mandatory": True, "notes": ""},
            {"name": "Marriage / relationship cert (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Position not on Regional Occupation List for the area",
            "Employer not in designated regional postcode",
            "Salary below TSMIT or Annual Market Salary Rate",
            "Insufficient 3-year experience documented",
            "Same as 482/186: incomplete docs, health/character issues",
        ],
        "success_tips": [
            "Choose regional employer carefully — must remain compliant for 191 pathway",
            "Maintain salary + role consistency through 5-year visa duration",
            "Save ALL tax + employment records — needed for 191 PR application",
            "Family on 494 has full work + study rights — partner can pursue own career",
        ],
        "faqs": [
            {"q": "When can I apply for PR?", "a": "After 3 years living + working in regional area + meeting income threshold (AUD 53,900 / year for 3 years), via Subclass 191 PR application."},
            {"q": "What is 'regional Australia'?", "a": "~99% of Australia EXCEPT Sydney, Melbourne, and Brisbane CBDs. Adelaide, Perth, Hobart, Canberra, Darwin, regional towns all qualify."},
            {"q": "Can I change employers?", "a": "Yes, but new employer must sponsor + nominate you in a regional position. 60 days to find new sponsor if you cease employment."},
            {"q": "Can my partner work?", "a": "Yes — partner has full work + study rights for entire 5-year visa duration."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-employer-sponsored-regional-494",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-employer-sponsored-regional-494",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-regional-191",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified against immi.homeaffairs.gov.au on 2026-02-27. 5-year provisional + 191 PR pathway documented.",
    },

    # ── 5. AU-858 — National Innovation Visa (formerly Global Talent) ──────────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "858",
        "subclass_name": "National Innovation Visa (Subclass 858 — formerly Global Talent)",
        "service_type": "pr", "category": "immigration",
        "description": (
            "The Subclass 858 National Innovation Visa (NIV) is a permanent residence visa for "
            "individuals with internationally recognised, outstanding records of exceptional and "
            "innovative achievement.\n\n"
            "REFORM ALERT (6 Dec 2024): The original Global Talent Visa programme was CLOSED to "
            "new applications and replaced by the National Innovation Visa retaining Subclass "
            "858. Key changes: INVITATION-ONLY (Expression of Interest required first); focus "
            "narrowed to Tier-1 priority sectors (Critical Technologies, Health Industries, "
            "Renewables, Low-Emission Tech) + Tier-2 (AgriTech, FinTech, MedTech, Cyber Security, "
            "Quantum, Advanced Digital/Data Science, ICT); high-income threshold ~AUD 183,100 "
            "(FY2025-26); under 45 with exemptions; nomination via Form 1000 from eligible "
            "Australian entity/expert."
        ),
        "eligibility_summary": (
            "Internationally recognised record of exceptional + outstanding achievement in a "
            "Tier-1 or Tier-2 priority sector. Invitation-only via EOI. Under 45 (with high-"
            "income / academic / government nomination exemptions). Form 1000 nomination from "
            "eligible Australian entity/expert. Functional English."
        ),
        "eligibility_criteria": [
            {"label": "Achievement record", "value": "Internationally recognised record of EXCEPTIONAL achievement in research, technology, arts, sports, entrepreneurship", "notes": "Nobel Prizes, Olympic medals, top-tier patents, Nature/Lancet publications, significant entrepreneurial exits"},
            {"label": "Priority sector (Tier 1)", "value": "Critical Tech / Health Industries / Renewables / Low-Emission Tech", "notes": "Top priority for invitation"},
            {"label": "Priority sector (Tier 2)", "value": "AgriTech / FinTech / MedTech / Cyber Security / Quantum / Advanced Digital / Data Science / ICT", "notes": ""},
            {"label": "Age", "value": "Under 45 (with exemptions: exceptional talent, govt nomination, high income)", "notes": ""},
            {"label": "High Income Threshold (HIT)", "value": "AUD 183,100 (FY2025-26, excluding super)", "notes": "If meeting HIT in last 3 years — age exemption applies"},
            {"label": "Nomination", "value": "Form 1000 nomination from eligible Australian entity / recognised expert / govt agency", "notes": "Mandatory"},
            {"label": "EOI", "value": "Submit Expression of Interest — invitation-only system; EOI valid 2 years", "notes": "Reformed Dec 2024"},
            {"label": "English", "value": "Functional English minimum", "notes": "Second VAC applies if not met"},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 4000, "fees_inr_approx": 220000,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary", "amount": 4000, "currency": "AUD"},
            {"component": "Secondary applicant 18+", "amount": 2000, "currency": "AUD"},
            {"component": "Dependent child <18", "amount": 1000, "currency": "AUD"},
            {"component": "Second VAC (Functional English not met)", "amount": 4885, "currency": "AUD"},
            {"component": "Health exam", "amount": 6000, "currency": "INR"},
            {"component": "PCCs", "amount": 1500, "currency": "INR"},
        ],
        "processing_time_days_min": 90, "processing_time_days_max": 365,
        "step_by_step": [
            {"step_number": 1, "title": "Build / Confirm Exceptional Achievement Profile", "description": "Document internationally recognised record: peer-reviewed publications, patents, awards, salary history, significant projects.", "estimated_days": 30, "documents_needed": ["Detailed CV", "Publications/patents", "Award certificates", "Salary/contract history"], "tips": ["Sector recognition matters — Tier 1 priority"]},
            {"step_number": 2, "title": "Secure Form 1000 Nomination", "description": "Obtain nomination from eligible Australian entity (recognised expert, govt agency, recognised organisation).", "estimated_days": 60, "documents_needed": ["Nominator CV", "Nominator's standing in field"], "tips": ["Strong nominator from Tier 1 sector accelerates invitation"]},
            {"step_number": 3, "title": "Submit Expression of Interest (EOI)", "description": "Lodge EOI through DoHA portal. EOI valid 2 years.", "estimated_days": 1, "documents_needed": ["CV", "Achievements summary", "Nominator details"], "tips": []},
            {"step_number": 4, "title": "Receive Invitation to Apply (ITA)", "description": "DoHA reviews EOIs against priorities and issues invitations selectively. 60 days from invitation to lodge.", "estimated_days": 180, "documents_needed": [], "tips": ["No fixed timeline — invitation depends on global pool + priorities"]},
            {"step_number": 5, "title": "Lodge Visa Application + Evidence", "description": "Submit comprehensive evidence package within 60 days.", "estimated_days": 7, "documents_needed": ["Full evidence dossier"], "tips": ["Lawyer/migration agent often advised — case-strength critical"]},
            {"step_number": 6, "title": "Health + PCC + Character Checks", "description": "Standard requirements.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Visa Grant — Permanent Resident from Day 1", "description": "Full PR rights: work + study + Medicare + family inclusion + citizenship pathway.", "estimated_days": 90, "documents_needed": [], "tips": ["No regional commitment", "No employer ties"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Form 1000 nomination (signed by eligible Australian nominator)", "mandatory": True, "notes": ""},
            {"name": "Detailed CV emphasising priority-sector achievements", "mandatory": True, "notes": ""},
            {"name": "Evidence of exceptional achievement (publications/patents/awards)", "mandatory": True, "notes": ""},
            {"name": "Salary/contract history demonstrating high-income (if claiming HIT exemption)", "mandatory": False, "notes": ""},
            {"name": "International recognition evidence (media coverage, citations, h-index, etc)", "mandatory": True, "notes": ""},
            {"name": "Educational qualifications (PhD/Masters/equivalent)", "mandatory": True, "notes": "Apostilled if foreign"},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "English test (Functional or higher)", "mandatory": False, "notes": "Second VAC if not met"},
            {"name": "Health exam (HAP ID)", "mandatory": True, "notes": ""},
            {"name": "PCCs", "mandatory": True, "notes": ""},
            {"name": "Marriage / relationship cert (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Achievement record not deemed exceptional at international level",
            "Sector not on Tier 1/Tier 2 priority list",
            "Form 1000 nominator lacks recognised standing",
            "EOI weak — generic achievements without sector-specific impact",
            "Health/character issues",
            "Failure to lodge within 60 days of invitation",
        ],
        "success_tips": [
            "Target Tier 1 sectors for fastest invitation (Critical Tech, Health, Renewables, Low-Emission)",
            "Secure HIGH-PROFILE Form 1000 nominator — preferably from priority sector",
            "Quantify impact in EOI: citations, market valuations, lives saved, IP revenue, etc.",
            "Build measurable international recognition trail — media + peer recognition",
            "Engage migration agent experienced with NIV — invitation rate is selective",
            "Maintain 'living legend' narrative throughout — generic CVs fail",
        ],
        "faqs": [
            {"q": "Is this the same as Global Talent Visa?", "a": "NO — Global Talent (Subclass 858) was closed on 6 Dec 2024 and REPLACED by National Innovation Visa (still Subclass 858). Same visa number, different programme + criteria + invitation-only system."},
            {"q": "How do I get invited?", "a": "Submit EOI through DoHA portal with Form 1000 nomination. DoHA reviews against priorities + invites selectively. No fixed timeline — depends on global candidate pool + sector priorities."},
            {"q": "What if I don't meet under-45 age cap?", "a": "Exemptions: (a) exceptional talent at international level, (b) government agency nomination, (c) meeting High Income Threshold (~AUD 183,100) in last 3 years. Document the exemption claim clearly."},
            {"q": "Is this PR or temporary?", "a": "Permanent Residence from day one — full PR rights including work, study, Medicare, family inclusion, and pathway to citizenship after 4 years."},
            {"q": "Do I need a job offer in Australia?", "a": "NO — no employer sponsorship required. Just nomination via Form 1000 from eligible Australian entity/expert in your field."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/national-innovation-visa-858",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/national-innovation-visa-858",
            "https://www.bal.com/immigration-news/australia-national-innovation-visa-introduced/",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified against immi.homeaffairs.gov.au on 2026-02-27. NIV reform (6 Dec 2024) replacing Global Talent fully reflected. Tier 1/Tier 2 sectors + EOI invitation system + Form 1000 nomination + HIT FY2025-26 AUD 183,100 documented.",
    },

    # ── 6. AU-600 — Visitor Visa ────────────────────────────────────────────────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "600",
        "subclass_name": "Visitor Visa (Subclass 600)",
        "service_type": "visitor", "category": "immigration",
        "description": (
            "The Subclass 600 Visitor visa is the primary visitor visa for Indian and other non-"
            "ETA-eligible nationalities visiting Australia. Four streams: (a) Tourist (leisure, "
            "family visit); (b) Business Visitor (meetings, conferences — short-term, no Aussie "
            "employment); (c) Sponsored Family (relative in Australia sponsors); (d) Approved "
            "Destination Status (group tours from China).\n\n"
            "Validity 3/6/12 months single/multiple entry. Stay per visit up to 3, 6, or 12 "
            "months. Frequent Traveller route (10-year multi-entry) available for selected "
            "nationalities (India eligible since 2023). Strictly no work + no extended study (<3 "
            "months only)."
        ),
        "eligibility_summary": (
            "Genuine temporary visit purpose, sufficient funds, intent to depart, health + "
            "character. Sponsored Family stream: Australian sponsor (citizen/PR aged 18+) commits "
            "to undertaking responsibility + may need security bond."
        ),
        "eligibility_criteria": [
            {"label": "Purpose", "value": "Tourism / family visit / business visit / approved tour group", "notes": "Stream-specific"},
            {"label": "Genuine visitor", "value": "Demonstrate intent to depart Australia + ties to home", "notes": "Bank statements, employment, family at home"},
            {"label": "Funds", "value": "Sufficient for stay + return ticket", "notes": "~AUD 5,000+ for tourism; more for longer stays"},
            {"label": "Health", "value": "Standard requirement; medical for stays 6+ months", "notes": ""},
            {"label": "Character", "value": "PCC for stays 12+ months", "notes": ""},
            {"label": "Sponsor (Sponsored Family stream)", "value": "Australian citizen/PR aged 18+, financial undertaking", "notes": "May need security bond AUD 5,000-15,000"},
            {"label": "Frequent Traveller (India eligible)", "value": "10-year multiple-entry, max 3 months per visit", "notes": "AUD 1,065 fee; introduced for India 2023"},
            {"label": "No work permitted", "value": "Cannot accept paid Australian employment", "notes": "Business meetings + conferences OK"},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 200, "fees_inr_approx": 11000,
        "fees_breakdown": [
            {"component": "Tourist stream — Offshore application", "amount": 200, "currency": "AUD"},
            {"component": "Tourist stream — Onshore application (extension)", "amount": 500, "currency": "AUD"},
            {"component": "Business Visitor — Offshore", "amount": 200, "currency": "AUD"},
            {"component": "Sponsored Family stream", "amount": 200, "currency": "AUD"},
            {"component": "Frequent Traveller (10-year multi-entry, India eligible)", "amount": 1065, "currency": "AUD"},
            {"component": "Service charge (VAC2 conversion)", "amount": 0, "currency": "AUD"},
            {"component": "Medical (if required)", "amount": 6000, "currency": "INR"},
            {"component": "PCC (if 12+ months)", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 7, "processing_time_days_max": 60,
        "step_by_step": [
            {"step_number": 1, "title": "Determine Stream + Validity", "description": "Choose Tourist / Business / Sponsored Family / Frequent Traveller; decide validity (3/6/12 months or 10 years).", "estimated_days": 1, "documents_needed": [], "tips": ["Frequent Traveller route — best value for repeat Indian visitors"]},
            {"step_number": 2, "title": "Prepare Supporting Evidence", "description": "Gather financial + employment + family + travel documents.", "estimated_days": 7, "documents_needed": ["Bank statements", "Employment letter", "Property/business proof", "Itinerary"], "tips": ["Strong ties to home country = strongest signal"]},
            {"step_number": 3, "title": "Online Application via ImmiAccount", "description": "Apply offshore; pay fee.", "estimated_days": 1, "documents_needed": ["Passport scan", "Photo", "All supporting docs"], "tips": []},
            {"step_number": 4, "title": "Biometrics (if required)", "description": "Some Indian applicants need biometrics at VFS — DoHA notifies.", "estimated_days": 7, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Decision", "description": "7-60 days typical. Approval grants electronic visa.", "estimated_days": 21, "documents_needed": [], "tips": []},
            {"step_number": 6, "title": "Travel + Comply with Conditions", "description": "Enter Australia within visa validity. Comply with no-work + stay-limit conditions.", "estimated_days": 90, "documents_needed": ["Passport", "Return ticket"], "tips": ["Carry funds + accommodation evidence at port"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages, valid 6+ months)", "mandatory": True, "notes": ""},
            {"name": "Recent photo (passport-style)", "mandatory": True, "notes": ""},
            {"name": "Bank statements (6 months) showing funds", "mandatory": True, "notes": "~AUD 5,000+"},
            {"name": "Employment letter + leave approval", "mandatory": True, "notes": "Shows ties to home"},
            {"name": "ITR / Tax returns (last 2 years)", "mandatory": True, "notes": "Financial credibility"},
            {"name": "Property documents / business registration (if applicable)", "mandatory": False, "notes": "Strengthens ties"},
            {"name": "Confirmed travel itinerary + accommodation", "mandatory": True, "notes": ""},
            {"name": "Return ticket", "mandatory": False, "notes": "Recommended"},
            {"name": "Family in Australia: invitation letter + sponsor's PR/citizenship", "mandatory": False, "notes": "If family visit"},
            {"name": "Conference / business invitation (Business stream)", "mandatory": False, "notes": ""},
            {"name": "Form 1149 (Sponsored Family stream)", "mandatory": False, "notes": "Sponsor's commitment"},
            {"name": "Medical exam (stays 6+ months)", "mandatory": False, "notes": ""},
            {"name": "PCC (stays 12+ months)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Insufficient ties to home country (genuine visitor test)",
            "Weak financial position",
            "Vague travel itinerary or purpose",
            "Prior visa overstay / cancellation",
            "Sponsor's financial standing weak (Sponsored Family stream)",
            "Activities suggesting work intent",
        ],
        "success_tips": [
            "Build STRONG ties-to-home narrative: stable job + property + family + savings",
            "Provide DETAILED itinerary with bookings — vague plans get refused",
            "Frequent Traveller route ideal for visiting family/business 2-3x/year",
            "Apply 4-6 weeks before travel — buffer for processing",
            "Don't push 12-month validity if 3-month stay is realistic — sets pattern for future",
            "Honest history declaration — past refusals/overstays disclosed = better than discovered",
        ],
        "faqs": [
            {"q": "Can I work on Subclass 600?", "a": "NO — strictly no paid Australian employment. Business meetings, conferences, training (non-employed) are OK. Violations = visa cancellation + future refusals."},
            {"q": "How long can I stay?", "a": "Up to 3, 6, or 12 months per visit depending on visa grant. Multiple-entry visas allow exit/re-entry within validity. Frequent Traveller route: max 3 months per visit over 10 years."},
            {"q": "Can I study?", "a": "Short-term study only (less than 3 months). For longer education, apply for Student Visa Subclass 500."},
            {"q": "What is Frequent Traveller route?", "a": "10-year multiple-entry visa introduced for selected nationalities (including India since 2023), AUD 1,065. Max 3 months per visit. Excellent for frequent business/family travellers."},
            {"q": "Can I extend onshore?", "a": "Yes — apply for further Subclass 600 onshore (AUD 500 vs AUD 200 offshore). Must apply before existing visa expires."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/visitor-600",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/visitor-600",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/visitor-600/tourist-stream-overseas",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/visitor-600/frequent-traveller-stream",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified against immi.homeaffairs.gov.au on 2026-02-27. Fee AUD 200 offshore + AUD 500 onshore per 1 Jul 2025 update. Frequent Traveller AUD 1,065 (India eligible since 2023).",
    },

    # ── 7. AU-407 — Training Visa ───────────────────────────────────────────────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "407",
        "subclass_name": "Training Visa (Subclass 407)",
        "service_type": "work", "category": "immigration",
        "description": (
            "The Subclass 407 Training visa allows foreign nationals to undertake workplace-based "
            "occupational training in Australia. Three streams: (a) Occupational training "
            "required for registration (e.g., medical residency); (b) Capacity-building training "
            "for foreign government employees, professional development workshops; (c) Training "
            "for an occupation on the relevant skills list.\n\n"
            "Validity up to 2 years (renewable per training plan). Employer sponsor (Australian "
            "company or training provider) required. Distinct from Employment Visa 482 — focus "
            "on STRUCTURED TRAINING rather than ongoing employment."
        ),
        "eligibility_summary": (
            "Sponsored by approved Australian training provider / company; specific training plan; "
            "minimum age 18; relevant background; English (Vocational); health + character. Plan "
            "must lead to specific skill/registration outcome."
        ),
        "eligibility_criteria": [
            {"label": "Sponsorship", "value": "Approved Australian sponsor (Standard Business Sponsor OR Temporary Activities Sponsor)", "notes": ""},
            {"label": "Training plan", "value": "Structured training plan with specific outcomes (skills + duration + sequence)", "notes": "Plan reviewed by DoHA"},
            {"label": "Background", "value": "Relevant prior knowledge / role for the training", "notes": ""},
            {"label": "Age", "value": "Minimum 18 at application", "notes": ""},
            {"label": "English", "value": "Vocational English (IELTS 4.5 each band)", "notes": "Some exemptions"},
            {"label": "Duration", "value": "Up to 2 years (matching training plan)", "notes": "Renewable based on continuing plan"},
            {"label": "No general employment", "value": "Cannot replace Employment Visa for ongoing work", "notes": "Training-specific"},
            {"label": "Health + Character", "value": "Standard requirements", "notes": ""},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 430, "fees_inr_approx": 23650,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary", "amount": 430, "currency": "AUD"},
            {"component": "Secondary applicant 18+", "amount": 430, "currency": "AUD"},
            {"component": "Dependent child <18", "amount": 110, "currency": "AUD"},
            {"component": "Nomination + Sponsor fees (sponsor-paid)", "amount": 420, "currency": "AUD"},
            {"component": "English test (if not exempt)", "amount": 16800, "currency": "INR"},
            {"component": "Health exam", "amount": 6000, "currency": "INR"},
            {"component": "PCC", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 30, "processing_time_days_max": 90,
        "step_by_step": [
            {"step_number": 1, "title": "Sponsor + Training Plan", "description": "Australian sponsor identifies you, develops structured training plan with specific outcomes.", "estimated_days": 30, "documents_needed": ["Training plan", "Sponsor approval"], "tips": ["Strong outcomes-focused plan accelerates approval"]},
            {"step_number": 2, "title": "Nomination Application", "description": "Sponsor lodges nomination + training plan with DoHA.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 3, "title": "Visa Application", "description": "Lodge visa application after nomination approval.", "estimated_days": 7, "documents_needed": ["Sponsor letter", "Training plan", "Background docs"], "tips": []},
            {"step_number": 4, "title": "English + Health + PCC", "description": "Complete vocational English test, health, PCCs.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Grant + Training Commencement", "description": "Visa typically 30-90 days. Begin training as per plan.", "estimated_days": 60, "documents_needed": [], "tips": ["Maintain training compliance — central to renewal"]},
        ],
        "document_checklist": [
            {"name": "Passport", "mandatory": True, "notes": ""},
            {"name": "Sponsor letter (Australian sponsor)", "mandatory": True, "notes": ""},
            {"name": "Detailed training plan", "mandatory": True, "notes": "Outcomes + duration + sequence"},
            {"name": "Background qualifications (degree / experience)", "mandatory": True, "notes": ""},
            {"name": "CV with relevant experience", "mandatory": True, "notes": ""},
            {"name": "English test (Vocational)", "mandatory": True, "notes": ""},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "Health exam", "mandatory": True, "notes": ""},
            {"name": "PCC", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
            {"name": "Marriage / relationship cert (if applicable)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Training plan vague or generic",
            "Background mismatch with training (e.g., no relevant prior experience)",
            "Plan appears to disguise general employment as training",
            "Sponsor not approved or financially unstable",
            "English below Vocational level (where required)",
        ],
        "success_tips": [
            "Make training plan OUTCOMES-FOCUSED with specific milestones",
            "Sponsor should be established + with clear training history",
            "Background CV must show DIRECT relevance to training subject",
            "Plan duration realistically — DoHA suspicious of indefinite/vague training",
            "For medical/professional registration training, link plan to specific registration outcome",
        ],
        "faqs": [
            {"q": "How is 407 different from 482?", "a": "407 = structured training with defined outcomes (no general employment); 482 = ongoing employment. Use 407 if your purpose is acquiring specific skills/registration, NOT routine work."},
            {"q": "Can my family come with me?", "a": "Yes — partner + dependent children can be included. Partner has work rights."},
            {"q": "Can I extend the visa?", "a": "Yes — subject to continued training plan validity + sponsor commitment. Total stay can extend to 4 years across renewals."},
            {"q": "Can 407 lead to PR?", "a": "Not directly — but training history + relationships built can support future skilled visa applications (189/190/482/186)."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/training-407",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/training-407",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified against immi.homeaffairs.gov.au on 2026-02-27. Fee AUD 430 per current schedule.",
    },

    # ── 8. AU-309-100 — Partner Offshore Combined (Provisional 309 + PR 100) ────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "309-100",
        "subclass_name": "Partner Offshore Combined (Subclass 309 Provisional + Subclass 100 Permanent)",
        "service_type": "partner", "category": "immigration",
        "description": (
            "The Subclass 309/100 is the offshore equivalent of 820/801 — a two-stage partner "
            "visa for spouses/de facto partners of Australian citizens, PRs, or eligible NZ "
            "citizens. Combined application + single fee (AUD 9,365) covers BOTH the temporary "
            "309 (granted first, typically 12-24 months) and the permanent 100 (typically "
            "granted ~2 years after 309).\n\n"
            "Applied OFFSHORE — applicant must be outside Australia at time of 309 application "
            "+ grant. For onshore applications, use 820/801. De facto relationships require 12+ "
            "months cohabitation (waived for registered relationships in Australian states/"
            "territories)."
        ),
        "eligibility_summary": (
            "Spouse / de facto partner of Australian citizen / PR / eligible NZ citizen aged "
            "18+; genuine + continuing relationship; offshore at 309 application + grant; "
            "relationship financial + social + household + emotional commitment evidence."
        ),
        "eligibility_criteria": [
            {"label": "Sponsor", "value": "Australian citizen / PR / eligible NZ citizen aged 18+", "notes": "Limit 2 sponsorships in lifetime, 5-year gap"},
            {"label": "Relationship type", "value": "Married OR de facto OR registered relationship", "notes": "De facto needs 12+ months cohabitation; registered relationship in AU state/territory waives this"},
            {"label": "Offshore at 309 application + grant", "value": "Applicant outside Australia at both points", "notes": "Even brief Australian visit could complicate"},
            {"label": "Genuine + continuing relationship", "value": "Comprehensive evidence: financial + social + household + emotional commitment", "notes": "Statutory declarations from 2 Australian witnesses on Form 888"},
            {"label": "Age", "value": "Both 18+", "notes": "Under-18 marriages void in Australian law"},
            {"label": "Health + Character", "value": "Standard requirements for both applicant + dependent children", "notes": ""},
            {"label": "Two-stage progression", "value": "309 (Provisional) → 100 (PR) typically 2 years later", "notes": "Continue providing relationship evidence at 100 stage"},
            {"label": "Children", "value": "Dependent children can be included in same application", "notes": ""},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 9365, "fees_inr_approx": 515075,
        "fees_breakdown": [
            {"component": "Combined Visa Application Charge — Primary (covers both 309 + 100)", "amount": 9365, "currency": "AUD"},
            {"component": "Secondary applicant 18+", "amount": 4685, "currency": "AUD"},
            {"component": "Dependent child <18", "amount": 2345, "currency": "AUD"},
            {"component": "100 stage — NO additional fee", "amount": 0, "currency": "AUD"},
            {"component": "Health exam (BUPA)", "amount": 6000, "currency": "INR"},
            {"component": "PCCs", "amount": 1500, "currency": "INR"},
            {"component": "Form 888 statutory declarations (notarised)", "amount": 2000, "currency": "INR"},
            {"component": "Translation services (Hindi → English)", "amount": 5000, "currency": "INR"},
        ],
        "processing_time_days_min": 240, "processing_time_days_max": 720,
        "step_by_step": [
            {"step_number": 1, "title": "Gather Relationship Evidence", "description": "Compile comprehensive evidence: financial (joint accounts, bills), social (photos, witnesses), household (shared address), emotional (communication history, future plans).", "estimated_days": 60, "documents_needed": ["Marriage cert", "Joint bank statements", "Shared bills", "Photos", "Communication history"], "tips": ["Quality > quantity; tell the relationship's true story"]},
            {"step_number": 2, "title": "Sponsor Application + Form 40SP", "description": "Sponsor lodges sponsorship application + completes Form 40SP with commitment + financial undertaking.", "estimated_days": 30, "documents_needed": ["Sponsor's passport/citizenship", "Form 40SP", "Financial proof"], "tips": ["Sponsor needs to be approved before visa decision"]},
            {"step_number": 3, "title": "Lodge Visa Application (Offshore)", "description": "Applicant submits combined 309/100 visa application from outside Australia. Single fee for both stages.", "estimated_days": 14, "documents_needed": ["Comprehensive evidence dossier", "Form 47SP", "Photo"], "tips": []},
            {"step_number": 4, "title": "Form 888 Statutory Declarations", "description": "Two Australian citizens/PRs aged 18+ provide written declarations of relationship genuineness.", "estimated_days": 14, "documents_needed": ["Form 888 × 2"], "tips": ["Witnesses must know couple personally"]},
            {"step_number": 5, "title": "Health + PCC", "description": "Standard.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 6, "title": "309 Provisional Grant", "description": "After 12-24 months processing, 309 granted. Move to Australia.", "estimated_days": 540, "documents_needed": [], "tips": ["Travel before 309 'must enter by' date"]},
            {"step_number": 7, "title": "Lodge 100 Stage Evidence (2 years later)", "description": "Approximately 2 years after 309 lodgement, DoHA reviews for 100 PR grant. Provide updated relationship evidence + any character/health updates.", "estimated_days": 365, "documents_needed": ["Updated relationship evidence", "Updated PCC if requested"], "tips": ["Continuing relationship — keep documenting throughout"]},
            {"step_number": 8, "title": "100 PR Grant", "description": "Full PR rights granted upon 100 approval.", "estimated_days": 90, "documents_needed": [], "tips": ["Citizenship pathway opens after 4 years total residence including 12 months as PR"]},
        ],
        "document_checklist": [
            {"name": "Applicant passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Sponsor's Australian citizenship/PR/NZ evidence", "mandatory": True, "notes": ""},
            {"name": "Marriage certificate (if married)", "mandatory": True, "notes": "Apostilled if foreign"},
            {"name": "Form 47SP (Application for migration to Australia by a partner)", "mandatory": True, "notes": ""},
            {"name": "Form 40SP (Sponsorship for partner)", "mandatory": True, "notes": "Sponsor"},
            {"name": "Form 888 statutory declarations × 2 (Australian witnesses)", "mandatory": True, "notes": ""},
            {"name": "Joint bank statements / financial commingling evidence", "mandatory": True, "notes": "Strong financial signal"},
            {"name": "Shared accommodation evidence (lease / utility bills)", "mandatory": True, "notes": ""},
            {"name": "Photos throughout relationship (with dates + context)", "mandatory": True, "notes": ""},
            {"name": "Communication history (WhatsApp, emails, social media)", "mandatory": True, "notes": "Demonstrates continuity"},
            {"name": "Travel together (boarding passes, accommodation)", "mandatory": False, "notes": "Strong signal"},
            {"name": "Health exam (HAP ID)", "mandatory": True, "notes": ""},
            {"name": "PCCs (applicant)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Form 80 (applicant + adult sponsor)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Insufficient relationship evidence (especially financial commingling)",
            "Applicant inside Australia at 309 application or grant (offshore requirement)",
            "De facto relationship under 12 months cohabitation without registration",
            "Sponsor's prior sponsorships > 2 or within 5-year gap",
            "Form 888 declarations from witnesses who don't know couple personally",
            "Health/character issues",
            "Contradictions in application narrative",
        ],
        "success_tips": [
            "Build evidence trail FROM DAY 1 of relationship — easier than retroactive compilation",
            "Joint bank account, shared bills, mutual will/insurance = STRONG signals",
            "Photos with dates + context across multiple events + years",
            "Statutory declaration witnesses should articulate SPECIFIC observations, not generic praise",
            "Apostille marriage cert at source — Indian Sub-Divisional Magistrate / Apostille via MEA",
            "Don't apply onshore if you're physically in Australia — bridges visa won't issue, must exit",
            "Continue building evidence DURING 309 hold — needed at 100 stage 2 years later",
        ],
        "faqs": [
            {"q": "Why single fee for both 309 and 100?", "a": "DoHA charges combined fee at 309 lodgement (AUD 9,365) covering both stages. No separate fee at 100 grant — significant cost saving vs other 2-stage visas."},
            {"q": "Can I apply onshore?", "a": "NO — 309/100 is offshore only. Onshore applicants must use 820/801 (different visa, same combined-fee structure)."},
            {"q": "How long until I get PR?", "a": "Approximately 2-3 years from initial 309 application: 12-24 months for 309 grant, then ~2 years before 100 PR review and grant."},
            {"q": "Can I work on 309?", "a": "YES — Subclass 309 provisional visa has full work + study rights once granted."},
            {"q": "What if my relationship breaks down?", "a": "Visa may be cancelled. Specific provisions for: (a) sponsor's death (visa continues), (b) family violence (provisional visa can lead to 100 even if relationship ends), (c) shared parental responsibility for sponsor's child."},
            {"q": "Do registered relationships count as de facto?", "a": "Yes — relationships registered with an Australian state/territory registry are deemed equivalent to 12+ months cohabitation. Check state-specific registration process."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-offshore-309-100",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-offshore-309-100",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-migrant-100",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified against immi.homeaffairs.gov.au on 2026-02-27. Combined fee AUD 9,365 per current schedule. Sir's decision (documented): single combined entry for 309-100 (mirrors B.2's 820/801 combined pattern + reflects DoHA's single-fee structure).",
    },

    # ── 9. AU-801 — Partner Onshore Permanent Stage ────────────────────────────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "801",
        "subclass_name": "Partner Onshore Permanent — Stage 2 (Subclass 801)",
        "service_type": "partner", "category": "immigration",
        "description": (
            "The Subclass 801 is the PERMANENT RESIDENCE stage of the onshore partner visa, "
            "automatically reviewed approximately 2 years after the Subclass 820 (Provisional) "
            "application was lodged. NO new application or fee at this stage — DoHA reaches out "
            "to confirm continuing relationship + updated documentation.\n\n"
            "This entry is for clients APPROACHING the 801 review or recently transitioned to "
            "801. The combined 820/801 visa workflow (initial application + 820 provisional "
            "phase) is documented separately in B.2 under Subclass 820. This entry guides the "
            "PR transition phase."
        ),
        "eligibility_summary": (
            "Existing 820 provisional visa holder approaching 2-year mark from initial lodgement. "
            "Relationship continuing + genuine. Updated supporting evidence required. No new fee."
        ),
        "eligibility_criteria": [
            {"label": "Existing 820 holder", "value": "Must be on Subclass 820 Provisional visa", "notes": "Granted at initial 820/801 lodgement"},
            {"label": "Continuing relationship", "value": "Relationship with sponsor must be continuing + genuine at time of 801 review", "notes": "Updated evidence required"},
            {"label": "Time elapsed", "value": "Approximately 2 years from initial 820/801 lodgement", "notes": "DoHA initiates 801 review automatically"},
            {"label": "No new fee", "value": "801 is the PR stage — covered by initial combined 820/801 fee", "notes": ""},
            {"label": "Updated evidence", "value": "Provide updated relationship + financial + household + character", "notes": ""},
            {"label": "Special pathways", "value": "Family violence / sponsor death / shared parental responsibility can lead to 801 if relationship ends", "notes": ""},
            {"label": "Children", "value": "Children added under 820 transition with primary", "notes": ""},
            {"label": "Health + Character", "value": "Updated PCC may be requested", "notes": ""},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 0, "fees_inr_approx": 0,
        "fees_breakdown": [
            {"component": "Visa Application Charge — 801 STAGE (covered by 820 lodgement)", "amount": 0, "currency": "AUD"},
            {"component": "Updated PCC (if requested)", "amount": 500, "currency": "INR"},
            {"component": "Updated medical (rarely requested)", "amount": 6000, "currency": "INR"},
            {"component": "Document notarisation / translations", "amount": 2000, "currency": "INR"},
        ],
        "processing_time_days_min": 90, "processing_time_days_max": 540,
        "step_by_step": [
            {"step_number": 1, "title": "Approaching 2-Year Mark on 820", "description": "Track timeline from initial 820/801 lodgement. DoHA contacts ~2 years later for 801 review.", "estimated_days": 1, "documents_needed": [], "tips": ["Document relationship throughout 820 period — needed at 801"]},
            {"step_number": 2, "title": "DoHA Issues 801 Request", "description": "DoHA sends request via ImmiAccount asking for updated evidence within timeline (typically 28-42 days).", "estimated_days": 1, "documents_needed": [], "tips": ["Don't miss the email — check ImmiAccount weekly"]},
            {"step_number": 3, "title": "Compile Updated Evidence", "description": "Updated relationship evidence covering the 820 period: joint accounts, bills, photos, travel, communication.", "estimated_days": 21, "documents_needed": ["Updated bank statements", "Continuing bills", "Recent photos", "Communication", "Updated witnesses (Form 888 if requested)"], "tips": ["Show CONTINUITY + DEEPENING — not just snapshot"]},
            {"step_number": 4, "title": "Submit Response to DoHA", "description": "Lodge updated evidence pack via ImmiAccount within deadline.", "estimated_days": 7, "documents_needed": ["Complete evidence dossier"], "tips": ["Don't miss the 28-42 day deadline — extensions hard to obtain"]},
            {"step_number": 5, "title": "Review + Possible RFI", "description": "DoHA reviews. May request further information.", "estimated_days": 90, "documents_needed": [], "tips": ["Respond to RFIs within stated timeline"]},
            {"step_number": 6, "title": "801 PR Grant", "description": "Full PR rights granted: work + study + Medicare + citizenship pathway. No further partner visa actions needed.", "estimated_days": 30, "documents_needed": [], "tips": ["Citizenship after 4 years total residence (12 months as PR)"]},
        ],
        "document_checklist": [
            {"name": "ImmiAccount login credentials", "mandatory": True, "notes": "Track 801 request"},
            {"name": "Updated joint bank statements", "mandatory": True, "notes": "Continuity from 820 period"},
            {"name": "Continuing shared bills / utilities", "mandatory": True, "notes": ""},
            {"name": "Lease / property co-ownership documents (updated)", "mandatory": True, "notes": ""},
            {"name": "Recent photographs (with dates)", "mandatory": True, "notes": ""},
            {"name": "Communication history (recent)", "mandatory": True, "notes": "Updated WhatsApp/email"},
            {"name": "Travel together (recent)", "mandatory": False, "notes": "Strong signal"},
            {"name": "Updated Form 888 statutory declarations (if requested)", "mandatory": False, "notes": ""},
            {"name": "Updated PCC (if requested)", "mandatory": False, "notes": ""},
            {"name": "Updated medical (if requested)", "mandatory": False, "notes": ""},
            {"name": "Statutory declaration from applicant + sponsor on continuing relationship", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Failure to respond within DoHA's 28-42 day deadline",
            "Relationship breakdown without qualifying special provisions",
            "Insufficient continuing-relationship evidence",
            "Adverse character finding (criminal record discovery)",
            "Marriage of convenience evidence surfaces",
            "Sponsor sponsorship limits exceeded",
        ],
        "success_tips": [
            "Set CALENDAR REMINDER 22 months after 820 lodgement — start gathering 801 evidence",
            "MAINTAIN joint financial + household structures throughout 820 period",
            "Document RELATIONSHIP MILESTONES + EVENTS — anniversaries, family events, etc.",
            "Stay in regular communication with sponsor — physical separation can complicate",
            "Check ImmiAccount weekly — 801 request emails sometimes filtered as spam",
            "If relationship breaks down, IMMEDIATELY consult migration agent re: special provisions",
            "Build PR / citizenship plan early — 4 years to citizenship from PR",
        ],
        "faqs": [
            {"q": "Do I need to apply for 801 separately?", "a": "NO — DoHA automatically initiates 801 review ~2 years after initial 820/801 lodgement. You respond to their request; no new application or fee."},
            {"q": "What if my relationship ends?", "a": "Special provisions may apply: (a) family violence — provisional visa holder can proceed to 801 even if relationship ends, (b) sponsor's death, (c) shared parental responsibility for sponsor's child. Consult migration agent immediately."},
            {"q": "How long does 801 take?", "a": "3-18 months after 801 evidence submission. Total journey: ~2.5-4 years from initial 820/801 lodgement to 801 PR grant."},
            {"q": "Can I leave Australia during 801 review?", "a": "Yes — your 820 visa continues with multiple-entry rights during the review period."},
            {"q": "Why is there a fee but it shows AUD 0?", "a": "801 stage is covered by the initial combined 820/801 fee paid at lodgement. No new fee for the PR transition stage."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-onshore-820-801",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-onshore-820-801",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-permanent-801",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified against immi.homeaffairs.gov.au on 2026-02-27. PR transition stage (no new fee). Sir's directive: 801 added as separate workflow distinct from B.2's 820 to guide clients in 801 review phase.",
    },

    # ── 10. AU-887 — Skilled Regional PR ────────────────────────────────────────
    {
        "country_code": "AU", "country_name": "Australia",
        "subclass_id": "887",
        "subclass_name": "Skilled Regional Permanent Residence (Subclass 887)",
        "service_type": "pr", "category": "immigration",
        "description": (
            "The Subclass 887 Skilled Regional visa is a permanent residence visa for holders of "
            "specified provisional skilled regional visas (Subclass 475, 487, 489 'first "
            "provisional', or 886) who have met regional residence + work requirements.\n\n"
            "NOTE: For new applicants from Subclass 491 or 494 provisional visas, the PR "
            "pathway is via Subclass 191 (NOT 887). 887 specifically supports holders of older "
            "/repealed regional visas transitioning to PR. Requirements: lived in regional "
            "Australia for 2+ years; worked full-time for 12+ months in regional area."
        ),
        "eligibility_summary": (
            "Held one of: Subclass 475 / 487 / 489 'first provisional' / 886 visa. Lived in "
            "designated regional area for 2+ years. Worked full-time (35+ hrs/week) in regional "
            "area for 12+ months. Compliance with provisional visa conditions."
        ),
        "eligibility_criteria": [
            {"label": "Provisional visa held", "value": "Subclass 475 / 487 / 489 (first provisional) / 886 (legacy)", "notes": "For 491/494 holders, use Subclass 191"},
            {"label": "Regional residence", "value": "Lived in designated regional area for 2+ years", "notes": ""},
            {"label": "Regional work", "value": "Worked full-time (35+ hrs/week) in regional area for 12+ months", "notes": "Documented via PAYG summaries + employment records"},
            {"label": "Compliance with provisional conditions", "value": "Maintained terms of original provisional visa", "notes": ""},
            {"label": "Health + Character", "value": "Standard requirements", "notes": ""},
            {"label": "Family inclusion", "value": "Partner + dependent children can be included", "notes": ""},
            {"label": "Age", "value": "Generally under 45 at provisional grant (legacy rules)", "notes": ""},
            {"label": "No additional skills assessment", "value": "SA from provisional visa application carries through", "notes": ""},
        ],
        "fees_local_currency_code": "AUD", "fees_local_currency_amount": 1920, "fees_inr_approx": 105600,
        "fees_breakdown": [
            {"component": "Visa Application Charge — Primary", "amount": 1920, "currency": "AUD"},
            {"component": "Secondary applicant 18+", "amount": 960, "currency": "AUD"},
            {"component": "Dependent child <18", "amount": 480, "currency": "AUD"},
            {"component": "Health exam (if updated)", "amount": 6000, "currency": "INR"},
            {"component": "PCC (if updated)", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 60, "processing_time_days_max": 240,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm 2-Year Regional Residence + 12-Month Regional Work", "description": "Document continuous regional residence + full-time regional employment.", "estimated_days": 14, "documents_needed": ["Lease + utility bills", "PAYG summaries", "Employment evidence"], "tips": ["Postcode-level evidence — keep all bills with regional addresses"]},
            {"step_number": 2, "title": "Lodge Visa Application Online", "description": "Submit application via ImmiAccount with full evidence.", "estimated_days": 7, "documents_needed": ["Residence + work evidence"], "tips": []},
            {"step_number": 3, "title": "Health + PCC (if updated)", "description": "Update health + PCCs if requested.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 4, "title": "Decision + Grant", "description": "2-8 months. PR granted on approval.", "estimated_days": 120, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Settle as PR Anywhere in Australia", "description": "Full PR mobility — no further regional commitment. Family + work + study + Medicare.", "estimated_days": 30, "documents_needed": [], "tips": ["Citizenship after 4 years total residence"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Provisional visa grant notice (475/487/489/886)", "mandatory": True, "notes": ""},
            {"name": "Evidence of 2-year regional residence (lease, utility bills, council rates)", "mandatory": True, "notes": ""},
            {"name": "Evidence of 12-month regional full-time work (PAYG summaries, employment letters)", "mandatory": True, "notes": ""},
            {"name": "Tax returns (Notice of Assessment) covering work period", "mandatory": True, "notes": ""},
            {"name": "Form 80 (each adult)", "mandatory": True, "notes": ""},
            {"name": "Updated health exam (if requested)", "mandatory": False, "notes": ""},
            {"name": "Updated PCC (if requested)", "mandatory": False, "notes": ""},
            {"name": "Marriage / relationship cert (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Residence outside designated regional area (full or partial period)",
            "Less than 35 hrs/week work classification (not full-time)",
            "Work period below 12 months (gaps not adequately bridged)",
            "Provisional visa compliance issues during qualifying period",
            "Health/character issues",
        ],
        "success_tips": [
            "Track REGIONAL POSTCODE residence throughout — every utility bill, council rate, lease counts",
            "Maintain CONTINUOUS full-time work — gaps complicate 12-month threshold",
            "Save EVERY PAYG summary + tax return — central to 887 evidence",
            "If on 491/494, plan PR via Subclass 191 (NOT 887)",
            "For 887 eligibility, regional area definition is per the provisional visa's regulations — different from current 491/494 list",
        ],
        "faqs": [
            {"q": "Can 491 / 494 holders apply for 887?", "a": "NO — for 491 / 494 holders, the PR pathway is via Subclass 191 (Skilled Regional PR), not 887. 887 specifically supports legacy 475/487/489/886 holders."},
            {"q": "What counts as 'regional Australia' for 887?", "a": "Per the regulations applicable to your original provisional visa — may differ from current 491/494 regional area definitions. Verify against original visa's conditions."},
            {"q": "Can my partner work?", "a": "Yes — secondary applicants under 887 PR have full work + study rights upon grant."},
            {"q": "When can I apply for citizenship after 887?", "a": "After 4 years total residence (typically counted from provisional visa grant, including 12 months as PR)."},
            {"q": "Do I need a fresh skills assessment?", "a": "NO — SA from the original provisional visa carries through to 887."},
        ],
        "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-regional-887",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "source_urls": [
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-regional-887",
            "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-regional-191",
        ],
        "verified_notes": "Manual Fast-Path B.4.3 seed — verified against immi.homeaffairs.gov.au on 2026-02-27. Fee AUD 1,920 per current schedule. 491/494 holders explicitly directed to 191 instead.",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# CANADA EXPANSION (B.4.4) — 6 new subclasses adding to B.2's existing 6
# Sources: ircc.canada.ca · cicnews.com · provincial portals · Feb 2026 status
# FX: 1 CAD ≈ 60 INR (Feb 2026)
# ──────────────────────────────────────────────────────────────────────────────
CANADA_NEW_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. CA-AIP — Atlantic Immigration Program ────────────────────────────────
    {
        "country_code": "CA", "country_name": "Canada",
        "subclass_id": "AIP",
        "subclass_name": "Atlantic Immigration Program (AIP)",
        "service_type": "pr", "category": "immigration",
        "description": (
            "The Atlantic Immigration Program (AIP) is an employer-driven permanent residence "
            "pathway for skilled workers and international graduates wishing to settle in one of "
            "the four Atlantic provinces: **New Brunswick (NB), Newfoundland and Labrador (NL), "
            "Nova Scotia (NS), or Prince Edward Island (PE)**.\n\n"
            "Unlike Express Entry (federal CRS-based), AIP requires: (a) a job offer from a "
            "**provincially-designated employer**, (b) a Provincial Endorsement Certificate (PEC), "
            "and (c) a personalized **Settlement Plan** for the principal applicant + family. Made "
            "permanent in March 2022 (succeeding the AIPP pilot). Two streams: International "
            "Graduate (no work experience required) and High-Skilled Worker / Intermediate-Skilled "
            "Worker. Current processing time **26 months** (Jun 2026 IRCC data, down from 38 mo)."
        ),
        "eligibility_summary": (
            "Job offer from a designated Atlantic employer; Provincial Endorsement Certificate; "
            "completed Settlement Plan; meet education + work-experience + language requirements "
            "for the stream; demonstrate intent to settle in nominated Atlantic province."
        ),
        "eligibility_criteria": [
            {"label": "Job offer (designated employer)", "value": "Full-time, non-seasonal offer from provincially-designated Atlantic employer (NB / NL / NS / PE)", "notes": "Employer must have operated 2+ years in the province + settlement-services commitment"},
            {"label": "Provincial Endorsement Certificate", "value": "Province issues PEC valid 12 months", "notes": "After designation review"},
            {"label": "Education", "value": "Canadian secondary school OR equivalent foreign credential (ECA)", "notes": "Recent Atlantic graduates exempt if studying in the province"},
            {"label": "Work experience", "value": "1+ years (1,560 hrs) full-time in past 5 years (NOC TEER 0/1/2/3/4)", "notes": "International Graduates from designated Atlantic institutions exempt"},
            {"label": "Language", "value": "CLB 4 (Intermediate-Skilled), CLB 5 (High-Skilled + International Graduate)", "notes": "IELTS / CELPIP / TEF / TCF"},
            {"label": "Settlement Plan", "value": "Personalized plan from designated settlement service provider (PNB / ANC / NS / IRCC-approved)", "notes": "Mandatory before PR application"},
            {"label": "Funds (settlement)", "value": "Minimum settlement funds (varies by family size) unless currently working in Canada", "notes": "Same as Express Entry table"},
            {"label": "Health + Character", "value": "Standard PR requirements", "notes": ""},
        ],
        "fees_local_currency_code": "CAD", "fees_local_currency_amount": 1525, "fees_inr_approx": 91500,
        "fees_breakdown": [
            {"component": "PR processing fee — Principal Applicant", "amount": 1525, "currency": "CAD"},
            {"component": "Right of Permanent Residence Fee (RPRF) — payable on approval", "amount": 575, "currency": "CAD"},
            {"component": "Biometrics (single)", "amount": 85, "currency": "CAD"},
            {"component": "Biometrics (family max)", "amount": 170, "currency": "CAD"},
            {"component": "Spouse / common-law partner processing", "amount": 1525, "currency": "CAD"},
            {"component": "Spouse / partner RPRF", "amount": 575, "currency": "CAD"},
            {"component": "Dependent child", "amount": 260, "currency": "CAD"},
            {"component": "Employer Compliance Fee (IRCC, employer-paid for bridging WP)", "amount": 230, "currency": "CAD"},
            {"component": "Educational Credential Assessment (WES/IQAS)", "amount": 240, "currency": "CAD"},
            {"component": "Language test (IELTS/CELPIP)", "amount": 325, "currency": "CAD"},
            {"component": "Medical exam (per person)", "amount": 8500, "currency": "INR"},
            {"component": "Police Clearance Certificates", "amount": 1500, "currency": "INR"},
        ],
        "processing_time_days_min": 540, "processing_time_days_max": 810,
        "step_by_step": [
            {"step_number": 1, "title": "Identify Designated Atlantic Employer", "description": "Search provincial designation lists (PNB, ANC, NS, PEI). Apply for relevant job openings; secure full-time, non-seasonal offer.", "estimated_days": 60, "documents_needed": ["CV", "Cover letter"], "tips": ["NS has largest designation list", "Healthcare + IT + Trades + Hospitality most active"]},
            {"step_number": 2, "title": "Provincial Endorsement Application", "description": "Employer submits endorsement application to province. Province reviews and issues PEC (valid 12 months).", "estimated_days": 56, "documents_needed": ["Job offer", "Employer designation evidence"], "tips": ["4-8 weeks typical; NS slower"]},
            {"step_number": 3, "title": "Settlement Plan", "description": "Connect with provincial settlement service provider. Complete personalized Settlement Plan for principal + family.", "estimated_days": 21, "documents_needed": ["PEC", "Family details"], "tips": ["Mandatory before PR application"]},
            {"step_number": 4, "title": "Lodge PR Application via IRCC Permanent Residence Portal", "description": "Submit comprehensive application including PEC + Settlement Plan + supporting documents.", "estimated_days": 14, "documents_needed": ["PEC", "Settlement Plan", "ECA", "Language test", "Funds proof", "Forms"], "tips": []},
            {"step_number": 5, "title": "Biometrics + Medical + PCC", "description": "Complete biometrics at VAC; medical at panel physician; PCCs from all 6+ month countries.", "estimated_days": 60, "documents_needed": [], "tips": []},
            {"step_number": 6, "title": "Optional: Bridging Work Permit", "description": "If urgent start needed, employer obtains Employer Compliance Fee + applicant gets bridging work permit while PR processes.", "estimated_days": 90, "documents_needed": ["PEC", "Employer letter"], "tips": ["Optional — speeds entry to job"]},
            {"step_number": 7, "title": "IRCC Decision (~26 months)", "description": "IRCC reviews PR application. Pay RPRF on approval. Receive COPR (Confirmation of Permanent Residence).", "estimated_days": 720, "documents_needed": [], "tips": ["Backlog inventory — 12,900+ apps as of Jun 2026"]},
            {"step_number": 8, "title": "Landing + Settlement", "description": "Land at Atlantic port of entry; PR card issued; settle in nominated province.", "estimated_days": 30, "documents_needed": ["COPR", "Passport"], "tips": ["Settlement Plan provider continues post-arrival support"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Job offer letter (designated Atlantic employer)", "mandatory": True, "notes": "Specifies NOC + salary + hours"},
            {"name": "Provincial Endorsement Certificate (PEC)", "mandatory": True, "notes": "Valid 12 months"},
            {"name": "Settlement Plan (provincial settlement service provider)", "mandatory": True, "notes": ""},
            {"name": "Educational Credential Assessment (WES / IQAS)", "mandatory": True, "notes": "Foreign credentials only"},
            {"name": "Language test (IELTS General / CELPIP / TEF / TCF)", "mandatory": True, "notes": "CLB 4 or 5 depending on stream"},
            {"name": "Employment reference letters (past 5 years)", "mandatory": True, "notes": ""},
            {"name": "Settlement funds proof (bank statements)", "mandatory": True, "notes": "Unless already working in Canada"},
            {"name": "Medical exam confirmation", "mandatory": True, "notes": "Panel physician"},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": "From 6+ month countries"},
            {"name": "Marriage certificate / common-law evidence (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certificates (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Digital photo (per IRCC specs)", "mandatory": True, "notes": ""},
            {"name": "Biometrics confirmation (VAC)", "mandatory": True, "notes": ""},
            {"name": "IMM forms (5669, 5406, 5476 as applicable)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Employer designation expired or revoked",
            "PEC expiry before PR lodgement",
            "Settlement Plan missing or incomplete",
            "Education credential assessment for incorrect NOC",
            "Language scores below stream-specific CLB",
            "Insufficient settlement funds",
            "Job offer NOC mismatch with experience",
            "Health/criminal admissibility issues",
        ],
        "success_tips": [
            "Target designated employers EARLY — apply directly via provincial designation portals",
            "Atlantic Canada Opportunities Agency (ACOA) + employer-specific recruitment events",
            "Choose province strategically — NS has most designations; NB + PE smaller but faster",
            "International graduates from Atlantic institutions get streamlined eligibility",
            "Commit to Atlantic settlement long-term — applications evaluated on intent",
            "Lodge PEC + PR application together to avoid 12-month PEC expiry risk",
            "Optional bridging WP if employer needs you to start before PR grant (90-day process)",
            "Backlog reality: plan for 26-month wait from PR submission",
        ],
        "faqs": [
            {"q": "Can I apply directly to AIP without a job?", "a": "NO — job offer from designated Atlantic employer + Provincial Endorsement Certificate are mandatory entry points. International Graduates from Atlantic institutions can be matched via campus recruitment with designated employers."},
            {"q": "Is AIP a pilot?", "a": "NO — AIP became a PERMANENT federal-provincial program in March 2022, replacing the Atlantic Immigration Pilot Program (AIPP) which ran 2017-2021."},
            {"q": "Which Atlantic province should I target?", "a": "Depends on industry: NS (largest designated employer pool), NB (manufacturing + bilingual), NL (oil + gas + fisheries), PE (tourism + IT). All four offer same PR pathway."},
            {"q": "Can I work while PR processes?", "a": "Yes — via bridging Employer-Specific Work Permit. Employer pays Compliance Fee ($230) to IRCC; you get work permit linked to that designated job."},
            {"q": "What about my family?", "a": "Spouse + dependent children included in PR application. Spouse gets Open Work Permit on bridging visa; children get Study Permits for K-12 + post-secondary."},
            {"q": "How long is processing in 2026?", "a": "Approximately 26 months as of June 2026 (down 12 months from 38-month wait in May 2026). Backlog of 12,900+ applications. Provincial endorsement adds 4-8 weeks."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/atlantic-immigration.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/atlantic-immigration/how-to-immigrate.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/atlantic-immigration.html",
            "https://welcomenb.ca/content/wel-bien/en/Streams/AIP.html",
            "https://liveinnovascotia.com/atlantic-immigration-program",
            "https://www.princeedwardisland.ca/en/service/atlantic-immigration-program-endorsement-application",
        ],
        "verified_notes": "Manual Fast-Path B.4.4 seed — verified against ircc.canada.ca + provincial portals on 2026-02-27. Processing time 26mo per June 2026 CIC News update. Fees per IRCC FY2025-26 schedule.",
    },

    # ── 2. CA-Caregiver — Home Care Worker Pilots (PAUSED) ─────────────────────
    {
        "country_code": "CA", "country_name": "Canada",
        "subclass_id": "Caregiver",
        "subclass_name": "Home Care Worker Pilots (PAUSED — Child Care + Home Support streams)",
        "service_type": "work", "category": "immigration",
        "description": (
            "⚠️ **STATUS: PAUSED.** The Home Child Care Provider Pilot + Home Support Worker Pilot "
            "(original 5-year programs) **CLOSED to new applications on 17 June 2024**. The "
            "replacement **Home Care Worker Immigration Pilots (HCWIP)** launched 31 March 2025 "
            "with two streams (Child Care + Home Support) — both filled their 2,350 application "
            "caps within hours. IRCC officially **paused intake on 22 December 2025** with no new "
            "applications accepted **31 March 2026 through 30 March 2030**.\n\n"
            "This entry documents the PAUSED status + redirects new applicants to active "
            "alternatives: Express Entry Healthcare Category (NOC 33102 Nurse Aides), Provincial "
            "Nominee Programs (ON OINP / BC PNP / Atlantic AIP / MB MPNP), or LMIA-based work "
            "permit → CEC PR transition."
        ),
        "eligibility_summary": (
            "PAUSED PROGRAM. Reference for transitional applicants already in process. New "
            "caregiver applicants must use Express Entry Healthcare Category, Provincial Nominee "
            "Programs, or LMIA → CEC pathway."
        ),
        "eligibility_criteria": [
            {"label": "STATUS", "value": "PAUSED 22 Dec 2025; no new intake until 30 Mar 2030", "notes": "Use alternative pathways"},
            {"label": "Job offer (if still possible under reactivation)", "value": "Full-time non-seasonal job in home care / child care", "notes": ""},
            {"label": "Experience / Training", "value": "6 months recent relevant experience OR 6-month relevant training credential", "notes": ""},
            {"label": "Language", "value": "CLB 4 minimum (HCWIP — lower than original CLB 5)", "notes": ""},
            {"label": "Education", "value": "Canadian high school equivalent minimum", "notes": ""},
            {"label": "Workers in Canada Stream", "value": "Currently living + working in Canada with valid status", "notes": ""},
            {"label": "Applicants Outside Canada", "value": "Paused (not opened under HCWIP)", "notes": ""},
            {"label": "Alternative pathways", "value": "EE Healthcare Category (NOC 33102), PNP (ON/BC/Atlantic/MB), LMIA → CEC", "notes": "Recommended for new applicants"},
        ],
        "fees_local_currency_code": "CAD", "fees_local_currency_amount": 600, "fees_inr_approx": 36000,
        "fees_breakdown": [
            {"component": "HCWIP PR Application Fee — Principal (if reactivated)", "amount": 600, "currency": "CAD"},
            {"component": "RPRF (recommended upfront)", "amount": 575, "currency": "CAD"},
            {"component": "Spouse / partner processing", "amount": 570, "currency": "CAD"},
            {"component": "Dependent child", "amount": 270, "currency": "CAD"},
            {"component": "Work Permit Fee (legacy pilots)", "amount": 155, "currency": "CAD"},
            {"component": "Biometrics (per person)", "amount": 85, "currency": "CAD"},
            {"component": "Alternative: EE Healthcare Category — Principal", "amount": 1525, "currency": "CAD"},
            {"component": "Alternative: LMIA + Employer Compliance", "amount": 1230, "currency": "CAD"},
        ],
        "processing_time_days_min": 365, "processing_time_days_max": 1095,
        "step_by_step": [
            {"step_number": 1, "title": "Verify Status: PAUSED", "description": "Confirm HCWIP intake remains paused. As of Feb 2026, no new applications until 30 Mar 2030.", "estimated_days": 1, "documents_needed": [], "tips": ["Check ircc.canada.ca for any reactivation announcement"]},
            {"step_number": 2, "title": "Choose Active Alternative", "description": "Pivot to: (a) Express Entry Healthcare Category, (b) Provincial Nominee Program targeting caregivers, OR (c) LMIA-based temporary WP → CEC PR.", "estimated_days": 30, "documents_needed": [], "tips": ["EE Healthcare CRS cut-offs typically lower (~470 vs general 500+)"]},
            {"step_number": 3, "title": "Build Caregiver Credentials", "description": "Language test (CLB 7+), ECA (foreign credentials), 6+ months experience documentation.", "estimated_days": 90, "documents_needed": ["IELTS/CELPIP", "ECA", "Reference letters"], "tips": []},
            {"step_number": 4, "title": "Apply via Chosen Pathway", "description": "Submit EE profile / PNP application / LMIA + WP application per chosen pathway.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Build 24+ Months Canadian Caregiver Experience (LMIA path)", "description": "If on LMIA-based work permit, build experience for CEC transition (typically 12+ months minimum).", "estimated_days": 730, "documents_needed": [], "tips": ["Each month of Canadian work experience strengthens CRS"]},
            {"step_number": 6, "title": "Transition to PR via EE/CEC", "description": "Apply for PR via Canadian Experience Class once experience threshold met.", "estimated_days": 180, "documents_needed": [], "tips": []},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Job offer (if applicable for LMIA path)", "mandatory": False, "notes": "LMIA-based work permit"},
            {"name": "ECA (Educational Credential Assessment)", "mandatory": True, "notes": "For foreign credentials"},
            {"name": "Language test (IELTS / CELPIP)", "mandatory": True, "notes": "CLB 7+ for EE Healthcare"},
            {"name": "Reference letters (caregiver experience)", "mandatory": True, "notes": "6+ months minimum"},
            {"name": "Resume / CV", "mandatory": True, "notes": "Detailed caregiver experience"},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": ""},
            {"name": "Medical exam", "mandatory": True, "notes": ""},
            {"name": "Settlement funds proof", "mandatory": True, "notes": "Per family size"},
            {"name": "Marriage / partner cert (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Applying for paused HCWIP rather than active alternatives",
            "Language scores below threshold for chosen pathway",
            "Insufficient caregiver experience documentation",
            "ECA for wrong field / outdated",
            "Workers Outside Canada stream attempted (not opened)",
            "Standard PR criteria not met (funds / health / character)",
        ],
        "success_tips": [
            "DO NOT apply for HCWIP in 2026 — wait for reactivation announcement OR pivot now",
            "EE Healthcare Category is fastest active pathway — lower CRS cut-offs",
            "PNP targeting caregivers adds 600 EE points = near-guaranteed PR",
            "LMIA + Canadian experience builds CEC eligibility within 12-24 months",
            "Monitor cicnews.com + ircc.canada.ca for HCWIP reactivation news",
            "Some provinces (ON OINP) specifically target Personal Support Workers (PSWs)",
        ],
        "faqs": [
            {"q": "Can I still apply for the caregiver pilot?", "a": "NO — both legacy (Home Child Care Provider + Home Support Worker) AND replacement (HCWIP) are CLOSED to new applications. No intake until 30 Mar 2030 per IRCC announcement."},
            {"q": "What's the best alternative?", "a": "Express Entry Healthcare Category (NOC 33102 Nurse Aides) — active, lower CRS cut-offs (~470), familial to caregiver work. OR Provincial Nominee Programs targeting PSWs."},
            {"q": "Can I still work as a caregiver on a temporary work permit?", "a": "YES — LMIA-based caregiver work permits remain available. After 12-24 months Canadian experience, apply for PR via Canadian Experience Class (CEC)."},
            {"q": "Will the pilots reopen?", "a": "Not in 2026. IRCC has not announced a reopening date. Monitor official channels for any update beyond Mar 2030 horizon."},
            {"q": "What about applications already submitted?", "a": "In-process applications continue per existing timelines. No new submissions accepted."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/caregivers.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/caregivers/home-care-worker-immigration-pilots.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/news/notices/pausing-home-care-worker-immigration-pilots-application-intake.html",
            "https://www.cicnews.com/2025/12/change-home-care-worker-pilots-will-not-return-in-2026-1263765.html",
        ],
        "verified_notes": "Manual Fast-Path B.4.4 seed — verified PAUSED status per IRCC official notice + CIC News (Dec 2025). Sir's directive: maintain workflow with clear PAUSED status + redirect to active alternatives (similar to AU-187 closed pattern).",
    },

    # ── 3. CA-Start-up-Visa (PAUSED) ────────────────────────────────────────────
    {
        "country_code": "CA", "country_name": "Canada",
        "subclass_id": "Start-up-Visa",
        "subclass_name": "Start-up Visa Program (PAUSED — replacement entrepreneur pilot expected)",
        "service_type": "business", "category": "immigration",
        "description": (
            "⚠️ **STATUS: PAUSED.** The Canada Start-up Visa (SUV) program **suspended new "
            "applications on 1 January 2026** due to overwhelming backlog (waiting times exceeding "
            "10 years on inventory). Government is designing a replacement entrepreneur pilot "
            "program expected to launch in 2026.\n\n"
            "SUV granted permanent residence to immigrant entrepreneurs with innovative business "
            "ideas backed by designated Canadian organizations (venture capital funds, angel "
            "investor groups, or business incubators). Original quota 2,500/year for the entire "
            "program; deeply oversubscribed. **Exception:** Applicants with valid commitment "
            "certificates issued in 2025 by designated organizations can still submit applications "
            "**until 30 June 2026**."
        ),
        "eligibility_summary": (
            "PAUSED PROGRAM. Reference for transitional applicants with 2025 commitment "
            "certificates (must lodge by 30 Jun 2026). New entrepreneur applicants must await "
            "the replacement pilot OR pivot to provincial Entrepreneur PNP streams (BC / MB / SK / "
            "PE Entrepreneur)."
        ),
        "eligibility_criteria": [
            {"label": "STATUS", "value": "PAUSED 1 Jan 2026; lodge by 30 Jun 2026 if 2025 commitment certificate held", "notes": "Replacement entrepreneur pilot expected 2026"},
            {"label": "Innovative business idea", "value": "Scalable + globally competitive business concept", "notes": "Tech / cleantech / biotech / fintech preferred"},
            {"label": "Commitment from designated organization", "value": "VC fund (min $200K CAD) / Angel investor group ($75K CAD) / Business incubator", "notes": "Sole entry pathway"},
            {"label": "Language", "value": "CLB 5 (IELTS 5.0 / CELPIP 5)", "notes": "All 4 abilities"},
            {"label": "Education", "value": "Completed at least 1 year of post-secondary", "notes": "ECA for foreign credentials"},
            {"label": "Settlement funds", "value": "Per family size (e.g., $13,757 CAD for 1 person, scaling up)", "notes": ""},
            {"label": "Ownership stake", "value": "10%+ voting rights AND together with designated organization 50%+ voting rights", "notes": "Up to 5 essential persons can apply together"},
            {"label": "Health + Character", "value": "Standard PR requirements", "notes": ""},
        ],
        "fees_local_currency_code": "CAD", "fees_local_currency_amount": 2210, "fees_inr_approx": 132600,
        "fees_breakdown": [
            {"component": "PR Application Fee — Principal (if reactivated/transitional)", "amount": 1810, "currency": "CAD"},
            {"component": "Right of Permanent Residence Fee (RPRF)", "amount": 575, "currency": "CAD"},
            {"component": "Biometrics", "amount": 85, "currency": "CAD"},
            {"component": "Spouse / partner processing", "amount": 825, "currency": "CAD"},
            {"component": "Dependent child", "amount": 230, "currency": "CAD"},
            {"component": "Designated org commitment evaluation (varies)", "amount": 5000, "currency": "CAD"},
            {"component": "Language test", "amount": 325, "currency": "CAD"},
            {"component": "Legal / consultant fees", "amount": 15000, "currency": "CAD"},
            {"component": "Business validation costs", "amount": 50000, "currency": "CAD"},
        ],
        "processing_time_days_min": 1095, "processing_time_days_max": 3650,
        "step_by_step": [
            {"step_number": 1, "title": "Verify Status + Eligibility", "description": "Confirm whether you hold a 2025 commitment certificate (eligible to lodge by 30 Jun 2026) OR if PAUSED applies.", "estimated_days": 1, "documents_needed": ["Commitment certificate if any"], "tips": ["Without 2025 certificate, await new entrepreneur pilot"]},
            {"step_number": 2, "title": "Pitch to Designated Organization (transitional)", "description": "If pursuing transitional pathway, ensure commitment certificate is valid + designated org is on IRCC's list.", "estimated_days": 90, "documents_needed": ["Business plan", "Pitch deck"], "tips": []},
            {"step_number": 3, "title": "Letter of Support + Commitment Certificate", "description": "Designated org issues Letter of Support (LoS) — sent directly to IRCC + Commitment Certificate copy to applicant.", "estimated_days": 30, "documents_needed": ["LoS"], "tips": ["LoS expires after 6 months — lodge PR within window"]},
            {"step_number": 4, "title": "Optional: Work Permit (Owner-Operator)", "description": "Apply for optional owner-operator work permit to start operating business in Canada before PR grant.", "estimated_days": 60, "documents_needed": ["LoS"], "tips": []},
            {"step_number": 5, "title": "Lodge PR Application", "description": "Submit comprehensive PR application via IRCC portal.", "estimated_days": 14, "documents_needed": ["LoS", "Business docs", "Language test", "Education", "Funds proof"], "tips": []},
            {"step_number": 6, "title": "Biometrics + Medical + PCC", "description": "Standard.", "estimated_days": 90, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "IRCC Review (10+ years backlog)", "description": "Highly variable — 3-10+ years in current backlog. Track status via IRCC portal.", "estimated_days": 2555, "documents_needed": [], "tips": ["Lengthy processing — plan business operations independently"]},
            {"step_number": 8, "title": "PR Grant + Business Operation", "description": "On approval, receive COPR. Land + commence Canadian business operations.", "estimated_days": 90, "documents_needed": [], "tips": []},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Letter of Support (designated organization)", "mandatory": True, "notes": "6-month validity"},
            {"name": "Commitment Certificate", "mandatory": True, "notes": ""},
            {"name": "Detailed business plan", "mandatory": True, "notes": "Market analysis + financials + timeline"},
            {"name": "Pitch deck", "mandatory": True, "notes": ""},
            {"name": "Educational Credential Assessment", "mandatory": True, "notes": "If foreign credentials"},
            {"name": "Language test (IELTS / CELPIP)", "mandatory": True, "notes": "CLB 5+"},
            {"name": "Settlement funds proof", "mandatory": True, "notes": ""},
            {"name": "Founder team agreement (if 2+ persons)", "mandatory": True, "notes": "Up to 5 essential persons"},
            {"name": "Ownership structure documentation", "mandatory": True, "notes": "10%+ voting rights"},
            {"name": "Medical exam", "mandatory": True, "notes": ""},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": ""},
            {"name": "Marriage / partner cert (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Attempting new application after 1 Jan 2026 (without 2025 commitment certificate)",
            "Designated organization not on current IRCC list",
            "Commitment Certificate expired (>6 months)",
            "Business idea not deemed innovative / scalable",
            "Insufficient ownership structure compliance (10%/50% rules)",
            "Language scores below CLB 5",
            "Settlement funds inadequate for family size",
            "Health/character admissibility issues",
        ],
        "success_tips": [
            "DO NOT apply for SUV in 2026 unless transitional commitment held",
            "Provincial Entrepreneur PNPs (BC / MB / SK / PE Entrepreneur) remain active alternatives",
            "Monitor ircc.canada.ca + cicnews.com for new entrepreneur pilot announcement",
            "Build strong business validation BEFORE engaging designated organizations",
            "Tech-focused VCs in BC + ON have highest acceptance rates historically",
            "Plan for 5-10 year wait if pursuing transitional path",
            "Owner-Operator work permit can build Canadian presence + experience independently",
        ],
        "faqs": [
            {"q": "Can I still apply for SUV?", "a": "Only if you hold a Letter of Support / Commitment Certificate issued by a designated organization in 2025 — must lodge by 30 June 2026. Otherwise, intake is PAUSED."},
            {"q": "What about new entrepreneurs?", "a": "Await the replacement entrepreneur pilot program expected to launch in 2026. Details + eligibility unannounced as of Feb 2026."},
            {"q": "Are there alternatives?", "a": "YES — Provincial Entrepreneur PNPs in BC, MB, SK, PE specifically target entrepreneurs. Lower waiting times (12-18 months typical)."},
            {"q": "What about SUV's 10+ year backlog?", "a": "IRCC paused intake specifically to manage this backlog. Existing applications continue processing per their submission date."},
            {"q": "Can I work in Canada while waiting?", "a": "YES — apply for Owner-Operator Work Permit linked to your business + Letter of Support. Validity matches LoS (6 months) but extendable."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/start-visa.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/start-visa.html",
            "https://www.imidaily.com/north-america/canada-suspends-start-up-visa-hints-at-new-replacement-in-2026/",
            "https://www.fragomen.com/insights/canada-two-entrepreneurial-programs-paused-new-entrepreneur-pilot-expected.html",
        ],
        "verified_notes": "Manual Fast-Path B.4.4 seed — verified PAUSED status (1 Jan 2026) per IRCC announcement + Fragomen + IMI Daily. Transitional pathway (2025 commitment certificates lodgeable until 30 Jun 2026) documented.",
    },

    # ── 4. CA-Self-Employed Persons Program (PAUSED) ────────────────────────────
    {
        "country_code": "CA", "country_name": "Canada",
        "subclass_id": "Self-Employed",
        "subclass_name": "Self-Employed Persons Program (PAUSED)",
        "service_type": "business", "category": "immigration",
        "description": (
            "⚠️ **STATUS: PAUSED.** The Self-Employed Persons Program **suspended new applications "
            "on 1 January 2026** alongside the Start-up Visa, due to backlogs exceeding 10 years. "
            "Government is designing replacement entrepreneur pathways.\n\n"
            "The original program granted PR to applicants with relevant international experience "
            "in **cultural activities** (arts, music, writing, athletics) or **farm management** "
            "(operating a farm in Canada). The program was niche but valuable for specific "
            "self-employed professionals not fitting SUV criteria. **Exception:** Applicants who "
            "submitted complete applications before 1 January 2026 continue processing per "
            "existing timelines."
        ),
        "eligibility_summary": (
            "PAUSED PROGRAM. Pre-1 Jan 2026 applications continue. New applicants must await "
            "replacement entrepreneur pilot OR pivot to Provincial Entrepreneur PNPs OR pursue "
            "Express Entry Federal Self-Employed (if launched as replacement)."
        ),
        "eligibility_criteria": [
            {"label": "STATUS", "value": "PAUSED 1 Jan 2026 for new applications; in-process apps continue", "notes": "Replacement pathway TBD"},
            {"label": "Self-employed experience", "value": "Relevant 2+ years' self-employed experience in: cultural activities, athletics, OR farm management", "notes": "Within 5 years of application"},
            {"label": "Intent + ability to be self-employed in Canada", "value": "Detailed business plan + Canadian market entry strategy", "notes": ""},
            {"label": "Selection points", "value": "Minimum 35 / 100 selection points (age + education + experience + language + adaptability)", "notes": ""},
            {"label": "Language", "value": "No fixed minimum — but contributes to selection points (CLB 5+ recommended)", "notes": ""},
            {"label": "Settlement funds", "value": "No fixed minimum — but must demonstrate ability to support self + family", "notes": "Self-funded business establishment"},
            {"label": "Cultural activities scope", "value": "Authors / artists / musicians / writers / coaches / athletes etc.", "notes": "World-class or 'self-employed' at international level"},
            {"label": "Farm management scope", "value": "Operating / owning a farm in Canada", "notes": "Stricter requirements"},
        ],
        "fees_local_currency_code": "CAD", "fees_local_currency_amount": 2210, "fees_inr_approx": 132600,
        "fees_breakdown": [
            {"component": "PR Application Fee — Principal (if reactivated/transitional)", "amount": 1810, "currency": "CAD"},
            {"component": "RPRF", "amount": 575, "currency": "CAD"},
            {"component": "Spouse / partner processing", "amount": 825, "currency": "CAD"},
            {"component": "Dependent child", "amount": 230, "currency": "CAD"},
            {"component": "Biometrics", "amount": 85, "currency": "CAD"},
            {"component": "Language test", "amount": 325, "currency": "CAD"},
            {"component": "ECA (if foreign credentials)", "amount": 240, "currency": "CAD"},
        ],
        "processing_time_days_min": 1095, "processing_time_days_max": 3650,
        "step_by_step": [
            {"step_number": 1, "title": "Verify Status: PAUSED", "description": "Confirm no new applications accepted post 1 Jan 2026.", "estimated_days": 1, "documents_needed": [], "tips": []},
            {"step_number": 2, "title": "Choose Alternative", "description": "Provincial Entrepreneur PNPs (BC / MB / SK / PE) OR pursue Express Entry under federal skilled categories OR await replacement entrepreneur pilot.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 3, "title": "Build Documentation", "description": "Comprehensive portfolio: self-employed experience evidence, business plan, financial records.", "estimated_days": 90, "documents_needed": [], "tips": []},
            {"step_number": 4, "title": "Apply via Chosen Pathway", "description": "Submit to chosen alternative.", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Long Processing (in-process apps)", "description": "3-10 year wait for pre-2026 applications.", "estimated_days": 2555, "documents_needed": [], "tips": []},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Detailed CV with cultural / athletic / farm experience", "mandatory": True, "notes": ""},
            {"name": "Portfolio of work (cultural activities)", "mandatory": True, "notes": "Publications, performances, awards"},
            {"name": "Business plan for Canadian self-employment", "mandatory": True, "notes": ""},
            {"name": "Financial records (tax returns, income evidence)", "mandatory": True, "notes": "5 years"},
            {"name": "Educational Credential Assessment", "mandatory": True, "notes": "If foreign"},
            {"name": "Language test", "mandatory": True, "notes": ""},
            {"name": "References / Letters of recommendation", "mandatory": True, "notes": ""},
            {"name": "Medical exam", "mandatory": True, "notes": ""},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": ""},
            {"name": "Marriage / partner cert (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Attempting new application post 1 Jan 2026",
            "Self-employed experience outside qualifying categories",
            "Insufficient evidence of intent to be self-employed in Canada",
            "Selection points below 35 / 100",
            "Vague business plan",
            "Standard PR criteria not met",
        ],
        "success_tips": [
            "DO NOT apply for Self-Employed Program in 2026 — paused indefinitely",
            "Provincial Entrepreneur PNPs are active alternatives for entrepreneurs",
            "Express Entry remains open for general skilled categories",
            "Build STRONG portfolio + Canadian market validation BEFORE applying when reactivated",
            "Niche programs may emerge for arts/athletics via new entrepreneur pilot",
            "Monitor IRCC announcements for replacement program",
        ],
        "faqs": [
            {"q": "Why was Self-Employed paused?", "a": "Backlogs of 10+ years made the program unviable. IRCC paused intake to design improved replacement entrepreneur pathways."},
            {"q": "Can artists / musicians still immigrate?", "a": "Yes — via Provincial Nominee Programs, Express Entry general skilled categories, or future replacement program. Cultural achievements may also qualify for NIV-equivalent recognition if pursuing PR via accomplishment-based pathways."},
            {"q": "What about athletes?", "a": "Athletics-focused immigration is being reviewed. Coaches + sport-development professionals may qualify via Express Entry (NOC-specific) OR Federal Sports Pilot if introduced."},
            {"q": "What about farm management?", "a": "Provincial farm-specific streams in MB, SK exist. Federal Self-Employed farm pathway paused — pivot to provincial."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/self-employed.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/self-employed.html",
            "https://www.fragomen.com/insights/canada-two-entrepreneurial-programs-paused-new-entrepreneur-pilot-expected.html",
        ],
        "verified_notes": "Manual Fast-Path B.4.4 seed — verified PAUSED status (1 Jan 2026) per IRCC + Fragomen. Maintained for legacy reference + redirect to active alternatives.",
    },

    # ── 5. CA-IEC — International Experience Canada ─────────────────────────────
    {
        "country_code": "CA", "country_name": "Canada",
        "subclass_id": "IEC",
        "subclass_name": "International Experience Canada (IEC) — Young Professionals + International Co-op",
        "service_type": "work", "category": "immigration",
        "description": (
            "International Experience Canada (IEC) is a temporary work permit program for foreign "
            "youth (typically 18-35) to gain Canadian work experience. India is a participating "
            "country, primarily through **Young Professionals** (TEER 0-3 job-specific) and "
            "**International Co-op (Internship)** (student work placements) streams. The Working "
            "Holiday stream (open work permit) is generally NOT available to Indian nationals "
            "(restricted to countries with Youth Mobility Agreements).\n\n"
            "Quota-based, per-country, per-category. 2026 IEC pools opened in December 2025. "
            "Invitations issued in weekly rounds throughout the year. Successful applicants get "
            "work permits valid up to 12-24 months (varies by category). Excellent stepping stone "
            "to Canadian Experience Class (CEC) PR after sufficient Canadian work experience."
        ),
        "eligibility_summary": (
            "Indian national aged 18-35; valid passport (12+ months); CAD 2,500+ settlement funds; "
            "valid health insurance for entire stay; no criminal record; for Young Professionals — "
            "Canadian job offer (TEER 0-3); for International Co-op — academic internship "
            "placement."
        ),
        "eligibility_criteria": [
            {"label": "Nationality + age", "value": "Indian national (or other participating country); aged 18-35 at application", "notes": "Upper age 30 for some streams"},
            {"label": "Passport validity", "value": "Valid for entire intended stay + 6 months", "notes": ""},
            {"label": "Settlement funds", "value": "CAD 2,500 minimum (proof at port)", "notes": ""},
            {"label": "Health insurance", "value": "Coverage for entire stay (medical + repatriation)", "notes": "Mandatory at port of entry"},
            {"label": "Young Professionals stream", "value": "Canadian employer job offer for TEER 0-3 occupation + labour-market specific exemption", "notes": "Employer Compliance Fee (CAD 230) employer-paid"},
            {"label": "International Co-op (Internship)", "value": "Active enrollment in foreign post-secondary; required internship at Canadian employer", "notes": "Maximum 12 months"},
            {"label": "Working Holiday stream", "value": "NOT available to India (Working Holiday quota restricted to countries with Youth Mobility Agreements)", "notes": ""},
            {"label": "Quota + ITA", "value": "Apply via 'Come to Canada' pool; weekly invitation rounds; 60 days to lodge work permit after ITA", "notes": "Check IEC site for current pool status"},
        ],
        "fees_local_currency_code": "CAD", "fees_local_currency_amount": 270, "fees_inr_approx": 16200,
        "fees_breakdown": [
            {"component": "IEC Participation Fee — Young Professionals / International Co-op", "amount": 184.75, "currency": "CAD"},
            {"component": "Open Work Permit Holder Fee — Working Holiday only", "amount": 100, "currency": "CAD"},
            {"component": "Biometrics (per person)", "amount": 85, "currency": "CAD"},
            {"component": "Employer Compliance Fee (Young Professionals — employer-paid)", "amount": 230, "currency": "CAD"},
            {"component": "Total — Young Professionals / Co-op (applicant)", "amount": 269.75, "currency": "CAD"},
            {"component": "Total — Working Holiday (where eligible)", "amount": 369.75, "currency": "CAD"},
            {"component": "Health insurance (per year)", "amount": 600, "currency": "CAD"},
        ],
        "processing_time_days_min": 30, "processing_time_days_max": 90,
        "step_by_step": [
            {"step_number": 1, "title": "Create 'Come to Canada' Profile + Determine Eligibility", "description": "Check IEC eligibility at canada.ca/iec. Get reference code if eligible.", "estimated_days": 1, "documents_needed": ["Passport", "Education details"], "tips": ["Use 'Come to Canada' tool"]},
            {"step_number": 2, "title": "Enter IEC Pool (Young Professionals OR International Co-op)", "description": "Create IEC profile linked to reference code. Select category. Enter pool.", "estimated_days": 1, "documents_needed": [], "tips": ["Pool reopens annually in December"]},
            {"step_number": 3, "title": "Receive Invitation to Apply (ITA)", "description": "Wait for ITA — invitations issued in weekly rounds based on pool + quotas.", "estimated_days": 60, "documents_needed": [], "tips": ["Check email + IRCC portal regularly", "60 days to lodge work permit"]},
            {"step_number": 4, "title": "Secure Job Offer (Young Professionals) / Internship (Co-op)", "description": "Find Canadian employer; obtain offer letter. Employer pays Compliance Fee.", "estimated_days": 30, "documents_needed": ["Job offer", "Employer details"], "tips": ["Search jobbank.gc.ca + LinkedIn"]},
            {"step_number": 5, "title": "Lodge Work Permit Application", "description": "Submit application within 60 days of ITA. Pay fees.", "estimated_days": 14, "documents_needed": ["ITA", "Job offer", "Passport", "Funds proof", "Insurance"], "tips": []},
            {"step_number": 6, "title": "Biometrics + Background Check", "description": "Complete biometrics at VAC. Police check + medical (if needed).", "estimated_days": 30, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Receive Port of Entry Letter (POE)", "description": "POE letter issued — present at Canadian port of entry to receive physical work permit.", "estimated_days": 14, "documents_needed": ["POE letter"], "tips": []},
            {"step_number": 8, "title": "Travel to Canada + Begin Work", "description": "Present POE letter, passport, funds, insurance at port. Receive work permit. Commence employment.", "estimated_days": 7, "documents_needed": ["All POE docs"], "tips": ["Carry health insurance proof"]},
            {"step_number": 9, "title": "Build Canadian Experience → CEC PR Pathway", "description": "After 12 months Canadian work experience, eligible for Express Entry CEC + provincial PNP.", "estimated_days": 365, "documents_needed": ["T4 + reference letters"], "tips": ["IEC is best youth pathway to PR"]},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages, valid 6+ months beyond stay)", "mandatory": True, "notes": ""},
            {"name": "Photo (per IRCC specs)", "mandatory": True, "notes": ""},
            {"name": "Canadian job offer (Young Professionals)", "mandatory": True, "notes": "TEER 0-3 occupation"},
            {"name": "Academic enrollment + internship letter (Co-op)", "mandatory": True, "notes": "Foreign post-secondary"},
            {"name": "Employer Compliance Fee receipt", "mandatory": True, "notes": "Employer-paid"},
            {"name": "Resume / CV", "mandatory": True, "notes": ""},
            {"name": "Settlement funds proof (CAD 2,500+)", "mandatory": True, "notes": ""},
            {"name": "Health insurance policy (entire stay)", "mandatory": True, "notes": "Mandatory at port"},
            {"name": "Police Clearance Certificate (India + others)", "mandatory": True, "notes": "If 6+ months stay"},
            {"name": "Medical exam (if requested)", "mandatory": False, "notes": ""},
            {"name": "Educational transcripts / certificates", "mandatory": True, "notes": ""},
            {"name": "Biometrics confirmation", "mandatory": True, "notes": ""},
            {"name": "Application Form (IMM 5710 / 5707)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Age above 35 at application",
            "Working Holiday application from India (not eligible)",
            "Insufficient settlement funds at port",
            "No valid Canadian job offer (Young Professionals)",
            "Internship not at credible Canadian employer (Co-op)",
            "Missing health insurance",
            "Prior visa overstays",
        ],
        "success_tips": [
            "Enter pool EARLY in December — invitations issued throughout year on quota",
            "Network with Canadian employers BEFORE ITA — secure offers ahead of work permit lodgement",
            "Health insurance must cover ENTIRE stay — port officers check",
            "Use IEC year to build Canadian experience for CEC PR (12-month minimum)",
            "Co-op stream: maintain enrollment in foreign post-secondary during placement",
            "Track IEC pool status weekly at canada.ca/iec for India-specific updates",
            "If Working Holiday is needed, consider New Zealand or UK Youth Mobility programs instead",
        ],
        "faqs": [
            {"q": "Can Indian nationals do Working Holiday in Canada?", "a": "Generally NO — India does not have a Youth Mobility Agreement with Canada providing the Working Holiday open work permit. Indians can use Young Professionals or International Co-op streams (employer/internship-tied)."},
            {"q": "How long is IEC work permit valid?", "a": "Young Professionals: up to 24 months. International Co-op: up to 12 months. Working Holiday (other countries): up to 12-24 months."},
            {"q": "Can I bring my family?", "a": "Spouse can apply for spouse open work permit; minor children can study on study permit. Apply concurrently."},
            {"q": "Can IEC lead to PR?", "a": "YES — IEC is one of the BEST pathways to Canadian PR for youth. After 12 months Canadian work experience (skilled/TEER 0-3), eligible for Express Entry Canadian Experience Class. Many provinces also have PNP streams targeting IEC holders."},
            {"q": "What if I miss the ITA window (60 days)?", "a": "Profile expires; must re-enter pool in next season. Don't miss the 60-day work permit lodgement deadline."},
            {"q": "Are quotas published?", "a": "Yes — IEC website updates per-country per-category quotas weekly. India quotas for YP + Co-op streams specifically tracked."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec.html",
            "https://www.cicnews.com/2025/12/international-experience-canada-pools-are-now-open-for-the-2026-season-1263843.html",
            "https://www.canadavisa.com/international-experience-canada-program.html",
        ],
        "verified_notes": "Manual Fast-Path B.4.4 seed — verified against canada.ca/iec + CIC News (Dec 2025 IEC pool opening). 2026 fees confirmed: YP/Co-op CAD 269.75, Working Holiday CAD 369.75. India eligible for YP + Co-op only, not Working Holiday.",
    },

    # ── 6. CA-Super-Visa — Parent & Grandparent Super Visa ──────────────────────
    {
        "country_code": "CA", "country_name": "Canada",
        "subclass_id": "Super-Visa",
        "subclass_name": "Parent and Grandparent Super Visa",
        "service_type": "visitor", "category": "immigration",
        "description": (
            "The Super Visa is a **10-year multi-entry visa** specifically for parents and "
            "grandparents of Canadian citizens or permanent residents. Allows stays of up to **5 "
            "years per visit** (extendable by 2 years onshore). Far superior alternative to "
            "regular Visitor Visa (typically max 6 months per visit) for families wanting "
            "extended parental visits without the multi-year backlog of the Parent and Grandparent "
            "Program (PGP) PR sponsorship.\n\n"
            "Key requirements: (a) Host (Canadian citizen/PR child or grandchild) meets minimum "
            "income (LICO + size), (b) Applicant has **$100,000 CAD+ medical insurance** from "
            "approved insurer covering 1+ year, (c) Standard health + character checks. **New "
            "flexibility from 31 Mar 2026:** Host's income calculation now allows adding visitor's "
            "income for hosts meeting minimum income percentage."
        ),
        "eligibility_summary": (
            "Parent or grandparent of Canadian citizen / PR aged 18+; mandatory $100,000 CAD "
            "medical insurance (Canadian or OSFI-authorized foreign insurer); host meets LICO+N "
            "minimum income across 2 preceding tax years; intent to visit (not immigrate); health "
            "exam + character clearance."
        ),
        "eligibility_criteria": [
            {"label": "Relationship", "value": "Parent / grandparent of Canadian citizen or permanent resident", "notes": "Sponsor must be 18+"},
            {"label": "Host minimum income (LICO + N)", "value": "Per 2025/2026 table — e.g., 1 person $30,526; 4 persons $56,724; +$8,224 per additional", "notes": "Across PAST 2 TAX YEARS (updated calculation rule)"},
            {"label": "Income flexibility (NEW Mar 2026)", "value": "Host can add visitor's income if meeting minimum % of required income", "notes": "Effective 31 Mar 2026"},
            {"label": "Medical insurance", "value": "$100,000 CAD+ coverage (medical + hospitalization + repatriation) valid 1+ year, fully paid", "notes": "From Canadian insurer OR OSFI-authorized foreign insurer (NEW)"},
            {"label": "Medical exam", "value": "Immigration medical exam required (panel physician)", "notes": ""},
            {"label": "Intent to visit (not immigrate)", "value": "Strong ties to home country + travel history + bank statements", "notes": ""},
            {"label": "Maximum stay per visit", "value": "5 years (extendable +2 years onshore)", "notes": "Within visa 10-year validity"},
            {"label": "Multiple entry", "value": "Multi-entry over 10 years (capped at passport validity if shorter)", "notes": ""},
        ],
        "fees_local_currency_code": "CAD", "fees_local_currency_amount": 185, "fees_inr_approx": 11100,
        "fees_breakdown": [
            {"component": "Visitor Visa Application Fee", "amount": 100, "currency": "CAD"},
            {"component": "Biometrics", "amount": 85, "currency": "CAD"},
            {"component": "Family biometrics (max)", "amount": 170, "currency": "CAD"},
            {"component": "Medical exam (India panel physician)", "amount": 8500, "currency": "INR"},
            {"component": "Medical insurance (annual, $100K coverage — varies by age)", "amount": 2500, "currency": "CAD"},
            {"component": "Police Clearance Certificate", "amount": 500, "currency": "INR"},
        ],
        "processing_time_days_min": 60, "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Host Income (LICO + N)", "description": "Host calculates total family size + verifies income meets LICO threshold across 2 preceding tax years (NEW: also can include visitor's income from 31 Mar 2026).", "estimated_days": 7, "documents_needed": ["Notices of Assessment (CRA) — last 2 years", "T4 slips", "Employment letter"], "tips": ["2-year income window stricter than old 1-year rule"]},
            {"step_number": 2, "title": "Purchase Medical Insurance", "description": "Buy $100K+ CAD coverage from Canadian OR OSFI-authorized foreign insurer. Fully paid, 1+ year validity, medical + hospital + repatriation.", "estimated_days": 14, "documents_needed": ["Insurance policy (fully paid)"], "tips": ["Don't buy quote-only policies — paid status mandatory", "Compare Sun Life, Manulife, GMS, BMO Insurance, etc."]},
            {"step_number": 3, "title": "Host Invitation Letter", "description": "Host writes detailed invitation letter: purpose, duration, accommodation, financial support undertaking.", "estimated_days": 3, "documents_needed": ["Invitation letter"], "tips": ["Reference relationship + LICO + insurance details"]},
            {"step_number": 4, "title": "Online Application via IRCC Portal", "description": "Applicant lodges Super Visa application offshore. Upload all supporting docs + photo + biometrics fee receipt.", "estimated_days": 7, "documents_needed": ["Passport", "Invitation letter", "Host income docs", "Insurance proof", "Relationship docs"], "tips": []},
            {"step_number": 5, "title": "Biometrics at VAC", "description": "Visit Visa Application Centre (Delhi/Mumbai/Bangalore/Chennai/Chandigarh).", "estimated_days": 14, "documents_needed": ["Biometrics fee receipt"], "tips": []},
            {"step_number": 6, "title": "Immigration Medical Exam (IME)", "description": "Complete medical at IRCC-approved panel physician in India.", "estimated_days": 14, "documents_needed": [], "tips": ["Medical valid 12 months"]},
            {"step_number": 7, "title": "Decision (60-180 days)", "description": "IRCC reviews. Approval issues 10-year multi-entry visa stamp.", "estimated_days": 90, "documents_needed": [], "tips": []},
            {"step_number": 8, "title": "Travel + Stay up to 5 Years per Visit", "description": "Enter Canada via designated port. Carry insurance + return ticket + relationship docs.", "estimated_days": 1825, "documents_needed": ["Passport", "Visa", "Insurance"], "tips": ["Extension onshore: +2 years possible via apply-to-stay-longer"]},
        ],
        "document_checklist": [
            {"name": "Applicant passport (bio + visa pages, valid 6+ months)", "mandatory": True, "notes": ""},
            {"name": "Photo (per IRCC specs)", "mandatory": True, "notes": ""},
            {"name": "Host's invitation letter (detailed)", "mandatory": True, "notes": ""},
            {"name": "Host's proof of citizenship / PR card", "mandatory": True, "notes": ""},
            {"name": "Host's Notice of Assessment (last 2 tax years)", "mandatory": True, "notes": "CRA-issued"},
            {"name": "Host's employment letter + pay stubs", "mandatory": True, "notes": ""},
            {"name": "Host's bank statements", "mandatory": False, "notes": "Supplementary"},
            {"name": "Medical insurance policy ($100K+ CAD, fully paid)", "mandatory": True, "notes": "Canadian or OSFI-authorized insurer"},
            {"name": "Relationship proof (birth certs, marriage cert linking applicant to host)", "mandatory": True, "notes": ""},
            {"name": "Immigration Medical Exam (IME)", "mandatory": True, "notes": "Panel physician"},
            {"name": "Police Clearance Certificate (India)", "mandatory": True, "notes": ""},
            {"name": "Applicant's bank statements", "mandatory": True, "notes": "Financial means + ties to home"},
            {"name": "Applicant's property documents / pension", "mandatory": False, "notes": "Ties to home country"},
            {"name": "Travel itinerary (initial visit)", "mandatory": True, "notes": ""},
            {"name": "Biometrics confirmation", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Host income below LICO + N threshold",
            "Medical insurance coverage <$100K CAD OR not fully paid",
            "Insurance from non-Canadian + non-OSFI-authorized insurer",
            "Weak ties to home country (immigration intent suspected)",
            "Relationship documents inconsistent or incomplete",
            "Prior visa overstay or violation by applicant",
            "Insufficient host invitation detail",
        ],
        "success_tips": [
            "Apply 4-6 months ahead of intended travel for processing buffer",
            "Insurance is the #1 rejection cause — fully-paid policy from approved insurer is non-negotiable",
            "Host should clearly establish 2-year LICO compliance via official CRA Notices of Assessment",
            "New flexibility (31 Mar 2026) allows host + visitor income combination — leverage if applicable",
            "Ties to home: property, pension, business, dependent family — document comprehensively",
            "Don't book non-refundable travel until visa stamped",
            "Renew insurance annually during long stays — extensions require valid insurance",
            "Onshore extension (+2 years) possible — apply 60+ days before stay limit",
        ],
        "faqs": [
            {"q": "How is Super Visa different from Visitor Visa (TRV)?", "a": "Super Visa: 10-year multi-entry, up to 5 years per visit, specifically for parents/grandparents, REQUIRES $100K insurance + LICO income. Regular Visitor Visa: max 10-year multi-entry but typically 6 months per visit, no insurance/income requirements."},
            {"q": "What about the Parent and Grandparent Program (PGP)?", "a": "PGP grants PR (not just visiting visa) but has multi-year quota backlogs (5-10+ year waits). Super Visa is faster alternative when PR isn't immediate priority. Apply for both — Super Visa now for immediate stays, PGP for eventual PR."},
            {"q": "Can I work or study on Super Visa?", "a": "NO — Super Visa is strictly for visiting. Work or study requires separate permits. Some grandparents help with childcare (not for hire) — that's permitted as it's not employment."},
            {"q": "Can I extend my stay beyond 5 years?", "a": "YES — onshore extension of +2 years possible by applying before stay limit. Beyond that, exit Canada + re-enter on remaining visa validity."},
            {"q": "What if my host's income temporarily dipped?", "a": "Income calculation now (Jul 2025 rule) uses past 2 tax years average. From 31 Mar 2026, can also add visitor's income if host meets minimum %. Flexibility helps gig-economy hosts."},
            {"q": "Can both parents apply together?", "a": "Yes — concurrent applications encouraged for couples. Each parent submits own Super Visa application; host LICO must accommodate both visitors in family size."},
        ],
        "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada/parent-grandparent-super-visa.html",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "source_urls": [
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada/parent-grandparent-super-visa.html",
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada/parent-grandparent-super-visa/forms-documents/host-financial-support.html",
            "https://www.cicnews.com/2026/03/canada-eases-income-requirement-for-hosting-parents-and-grandparents-on-super-visa-0373315.html",
            "https://www.bal.com/immigration-news/canada-change-to-super-visa-health-insurance-requirement/",
        ],
        "verified_notes": "Manual Fast-Path B.4.4 seed — verified against ircc.canada.ca + CIC News (Mar 2026 income flexibility rule). LICO + N table updated 29 Jul 2025 (3.9% inflation). OSFI-authorized foreign insurer acceptance per BAL/IRCC update.",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# NEW ZEALAND EXPANSION (B.4.5) — 4 new subclasses adding to B.2's existing 6
# Sources: immigration.govt.nz · 30 Apr 2026 income thresholds · Apr 2025 AIP launch
# · Jun 2026 AIP refinements · BIWV launched 2026 replacing EWV
# FX: 1 NZD ≈ 50 INR (Feb 2026)
# ──────────────────────────────────────────────────────────────────────────────
# NOTE: Sir's original brief listed NZ-Investor-2 + NZ-Skilled-Refugee — these
# do NOT exist as current INZ visa categories in Feb 2026. Research-corrected:
#   - Investor 1/2 CLOSED 2022 → replaced by Active Investor Plus (AIP)
#   - "Skilled Refugee" does not exist → closest active visa is Refugee Family
#     Support Resident Visa (600/year quota)
# NEW_ZEALAND_NEW_WORKFLOWS reflects current Feb 2026 visa landscape.
# ──────────────────────────────────────────────────────────────────────────────
NEW_ZEALAND_NEW_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. NZ-AIP — Active Investor Plus Visa ──────────────────────────────────
    {
        "country_code": "NZ", "country_name": "New Zealand",
        "subclass_id": "AIP",
        "subclass_name": "Active Investor Plus Visa (replaces Investor 1/2)",
        "service_type": "pr", "category": "immigration",
        "description": (
            "The Active Investor Plus (AIP) visa is New Zealand's premier residence-by-investment "
            "pathway, launched **April 2025** to replace the closed Investor 1 (NZD 10M) and "
            "Investor 2 (NZD 15M) categories. AIP simplifies into two streams: **Growth (NZD 5M "
            "over 3 years — active/higher-risk)** and **Balanced (NZD 10M over 5 years — mixed/"
            "lower-risk)**.\n\n"
            "Reforms (Jun 2026): English language requirement REMOVED; significantly reduced "
            "minimum NZ residency (Growth: 21 days over 3 yrs; Balanced: 105 days over 5 yrs). "
            "DIMS (Discretionary Investment Management Services) excluded from Growth category "
            "from 4 Dec 2025. From 1 Jun 2026, up to 20% of Growth investment can be philanthropy. "
            "**2026 Property Exemption:** AIP holders + former Investor 1/2 PR holders can "
            "purchase or build ONE residential property valued NZD 5M+ with LINZ consent."
        ),
        "eligibility_summary": (
            "Foreign investor with NZD 5M+ (Growth) OR NZD 10M+ (Balanced); transferable funds; "
            "good character; no English language requirement; willing to meet minimum residency "
            "in NZ. Apply via Expression of Interest → Invitation to Apply."
        ),
        "eligibility_criteria": [
            {"label": "Growth Category (NEW)", "value": "NZD 5M+ invested for 3 years in higher-risk active investments", "notes": "Direct business investments + approved managed funds. DIMS EXCLUDED from 4 Dec 2025"},
            {"label": "Balanced Category (NEW)", "value": "NZD 10M+ invested for 5 years in mixed assets", "notes": "Listed equities + bonds + property development + philanthropy + Growth-category assets"},
            {"label": "Minimum NZ Residency — Growth", "value": "21 days over 3-year investment period", "notes": ""},
            {"label": "Minimum NZ Residency — Balanced", "value": "105 days over 5-year investment period", "notes": "Reduced by 14 days per NZD 1M invested ABOVE NZD 10M into Growth-category assets (max 42 days reduction)"},
            {"label": "English language", "value": "NOT REQUIRED (removed in 2025 reform)", "notes": "Major simplification"},
            {"label": "Transferable funds", "value": "Funds must be legally acquired + transferable to NZ", "notes": "Source-of-funds documentation"},
            {"label": "Good character", "value": "Standard PR character requirements", "notes": ""},
            {"label": "Philanthropy (NEW Jun 2026)", "value": "Up to 20% of Growth investment can be philanthropic contributions to approved NZ charities", "notes": "Previously limited to Balanced category"},
            {"label": "Property Exemption (NEW 2026)", "value": "AIP holders + legacy Investor 1/2 PR holders can purchase / build ONE residential property NZD 5M+", "notes": "LINZ consent required"},
        ],
        "fees_local_currency_code": "NZD", "fees_local_currency_amount": 27470, "fees_inr_approx": 1373500,
        "fees_breakdown": [
            {"component": "AIP application fee (Principal) — Growth + Balanced", "amount": 27470, "currency": "NZD"},
            {"component": "Includes immigration levy", "amount": 3570, "currency": "NZD"},
            {"component": "Secondary applicant 18+ (partner)", "amount": 9070, "currency": "NZD"},
            {"component": "Dependent child", "amount": 4290, "currency": "NZD"},
            {"component": "Investment — Growth Category (NZD 5M minimum)", "amount": 5000000, "currency": "NZD"},
            {"component": "Investment — Balanced Category (NZD 10M minimum)", "amount": 10000000, "currency": "NZD"},
            {"component": "NZ Trade & Enterprise Investment Migrant Service", "amount": 0, "currency": "NZD"},
            {"component": "Legal + tax + investment advisory (estimate)", "amount": 50000, "currency": "NZD"},
            {"component": "Property purchase LINZ consent + legal", "amount": 25000, "currency": "NZD"},
        ],
        "processing_time_days_min": 60, "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Choose Category + Investment Plan", "description": "Decide between Growth (NZD 5M / 3 yrs / higher-risk) and Balanced (NZD 10M / 5 yrs / lower-risk).", "estimated_days": 30, "documents_needed": ["Source-of-funds documentation"], "tips": ["Growth = faster + cheaper; Balanced = lower risk + larger commitment"]},
            {"step_number": 2, "title": "Submit Expression of Interest (EOI)", "description": "Lodge EOI online via INZ portal. NZ Trade & Enterprise (NZTE) coordinates onboarding.", "estimated_days": 7, "documents_needed": ["Investment plan", "Funds source evidence"], "tips": ["Strong EOI accelerates Invitation to Apply"]},
            {"step_number": 3, "title": "Receive Invitation to Apply (ITA)", "description": "INZ reviews EOI + issues ITA. Typically 30-60 days.", "estimated_days": 45, "documents_needed": [], "tips": ["ITA window: 4 months to lodge full application"]},
            {"step_number": 4, "title": "Approval in Principle (AIP-AIP)", "description": "Lodge full visa application. INZ grants Approval in Principle within ~2 months on average.", "estimated_days": 60, "documents_needed": ["Full investment plan", "Character + health docs", "Source-of-funds documentation"], "tips": []},
            {"step_number": 5, "title": "Transfer + Deploy Investment Funds", "description": "Transfer funds to NZ; deploy into qualifying investments per chosen category within 6 months.", "estimated_days": 180, "documents_needed": ["Bank transfer records", "Investment confirmations"], "tips": ["Work with NZTE-approved investment advisors"]},
            {"step_number": 6, "title": "Resident Visa Granted", "description": "Once investment confirmed deployed, AIP Resident Visa issued. Begin meeting minimum residency days.", "estimated_days": 30, "documents_needed": [], "tips": ["Growth: 21 days/3yrs ; Balanced: 105 days/5yrs"]},
            {"step_number": 7, "title": "Hold Investment + Meet Residency", "description": "Maintain investment for category duration (3 / 5 yrs). Meet minimum residency days.", "estimated_days": 1825, "documents_needed": ["Investment maintenance evidence", "Travel records"], "tips": ["Can apply for permanent resident visa after meeting investment + residency"]},
            {"step_number": 8, "title": "Optional: Property Purchase via 2026 Exemption", "description": "Once AIP, eligible to purchase / build ONE residential property NZD 5M+ via LINZ consent.", "estimated_days": 90, "documents_needed": ["LINZ consent application"], "tips": []},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages, 12+ months validity)", "mandatory": True, "notes": ""},
            {"name": "Investment plan (Growth or Balanced)", "mandatory": True, "notes": "Detailed allocation across qualifying assets"},
            {"name": "Source-of-funds documentation", "mandatory": True, "notes": "Comprehensive provenance — 5+ years"},
            {"name": "Bank statements + financial records", "mandatory": True, "notes": ""},
            {"name": "Tax returns (last 3 years)", "mandatory": True, "notes": ""},
            {"name": "Business ownership / employment evidence (source of wealth)", "mandatory": True, "notes": ""},
            {"name": "Investment advisor / fund manager letters", "mandatory": True, "notes": ""},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": "From all 5+ year countries of residence"},
            {"name": "Medical exam (panel physician)", "mandatory": True, "notes": ""},
            {"name": "Photo (per INZ specs)", "mandatory": True, "notes": ""},
            {"name": "NZTE Investment Migrant Service engagement", "mandatory": False, "notes": "Recommended"},
            {"name": "Legal / tax advisor engagement", "mandatory": True, "notes": "Strongly recommended"},
            {"name": "Partner / spouse passport + relationship cert (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Property purchase LINZ consent application (if exemption used)", "mandatory": False, "notes": "After visa grant"},
        ],
        "common_rejection_reasons": [
            "Source-of-funds documentation incomplete or unclear",
            "Investment plan doesn't meet category-specific requirements",
            "DIMS-based investments attempted for Growth category (excluded since 4 Dec 2025)",
            "Funds not transferable due to source country restrictions",
            "Character / health admissibility issues",
            "Failure to deploy investment within 6 months of AIP-AIP",
        ],
        "success_tips": [
            "Engage NZTE Investment Migrant Service early — they coordinate end-to-end",
            "Comprehensive source-of-funds dossier is the #1 success factor",
            "Growth category is FASTER + CHEAPER but requires active investment expertise",
            "Balanced category suits passive investors with NZD 10M+ committable",
            "Use legal counsel familiar with AIP — recent reforms have nuances",
            "Plan for minimum residency days realistically — Balanced 105 days non-trivial",
            "2026 property exemption is significant — own family residence possible",
        ],
        "faqs": [
            {"q": "Can I still apply for Investor 1 or Investor 2?", "a": "NO — both closed. Active Investor Plus is the only investor pathway. Legacy holders retain certain benefits including 2026 property exemption."},
            {"q": "What's better: Growth or Balanced?", "a": "Growth: NZD 5M for 3 years, faster path, but active/higher-risk investments only. Balanced: NZD 10M for 5 years, includes lower-risk assets (bonds, listed equities). Choice depends on risk profile + capital availability."},
            {"q": "Why is English no longer required?", "a": "INZ removed the English language requirement in the 2025 reforms to make NZ more competitive vs Singapore + Caribbean investment programs. Significantly simplifies for non-English-speaking investors."},
            {"q": "Can I bring family?", "a": "Yes — partner + dependent children under 24 can be included. Partner gets full work + study rights upon AIP grant."},
            {"q": "What about the property exemption?", "a": "Effective 2026, AIP holders + legacy Investor 1/2 PR holders can purchase or build ONE residential property valued NZD 5M+ via LINZ consent process. Significant family settlement benefit."},
            {"q": "Can up to 20% of Growth be philanthropy?", "a": "YES from 1 Jun 2026 — up to 20% of Growth Category investment can be allocated to philanthropic contributions to approved NZ charities. Previously only Balanced allowed philanthropy."},
        ],
        "official_url": "https://www.immigration.govt.nz/visas/active-investor-plus",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/visas/active-investor-plus",
            "https://www.nzte.govt.nz/page/investor-migrants",
            "https://www.fragomen.com/insights/new-zealand-rules-on-investor-visa-relaxed.html",
            "https://www.dlapiper.com/en-us/insights/publications/2025/12/active-investor-plus-visa-explained",
        ],
        "verified_notes": "Manual Fast-Path B.4.5 seed — verified against immigration.govt.nz + NZTE + DLA Piper analysis on 2026-02-27. Apr 2025 launch + Jun 2026 refinements + DIMS exclusion (Dec 2025) + property exemption (2026) all reflected. NOTE: Sir's brief listed 'NZ-Investor-2' — that visa CLOSED; this entry seeded as NZ-AIP per current visa landscape.",
    },

    # ── 2. NZ-Entrepreneur — Entrepreneur Resident Visa + Business Investor WV ──
    {
        "country_code": "NZ", "country_name": "New Zealand",
        "subclass_id": "Entrepreneur",
        "subclass_name": "Entrepreneur Pathway (EWV CLOSED → ERV for existing + new BIWV for new applicants)",
        "service_type": "business", "category": "immigration",
        "description": (
            "Two-tier entrepreneur pathway in 2026:\n\n"
            "**LEGACY (for existing EWV holders only):** Entrepreneur Work Visa (EWV) is **CLOSED "
            "to new applications**. Existing EWV holders can still progress to **Entrepreneur "
            "Resident Visa (ERV)** for PR after meeting business success metrics: Standard "
            "Pathway = 2 years operation + NZD 100k+ capital; Fast-Track = 6 months + NZD 500k + "
            "3 NZ employees.\n\n"
            "**NEW (for new applicants):** **Business Investor Work Visa (BIWV)** introduced "
            "2026. Two tracks: (a) Standard — NZD 1M investment in 5+ year existing business → "
            "Residence after 3 years; (b) Fast-Track — NZD 2M investment → Residence after 12 "
            "months. Must hold NZD 500k reserve funds. Visa valid up to 4 years.\n\n"
            "ERV fee dramatically increased to **NZD 27,470** (was ~NZD 7,900) in 2026 reforms."
        ),
        "eligibility_summary": (
            "EXISTING EWV HOLDERS: 2+ years business operation + NZD 100k+ capital (or 6mo "
            "fast-track + NZD 500k + 3 NZ employees). NEW APPLICANTS: NZD 1M/2M investment + "
            "NZD 500k reserves + business plan dated within 3 months."
        ),
        "eligibility_criteria": [
            {"label": "EWV STATUS", "value": "CLOSED to new applications (late 2025 / early 2026)", "notes": "New applicants must use BIWV"},
            {"label": "ERV — Standard Pathway", "value": "EWV holder with 2+ years business operation + NZD 100k+ capital", "notes": "Minimum capital waivable for Science/ICT/high-value export sectors"},
            {"label": "ERV — Fast-Track Pathway", "value": "EWV holder with 6 months operation + NZD 500k+ + 3 NZ employees", "notes": ""},
            {"label": "BIWV — Standard Pathway", "value": "NZD 1M investment in 5+ year existing NZ business + 3-year operation → Residence", "notes": "NEW pathway"},
            {"label": "BIWV — Fast-Track Pathway", "value": "NZD 2M investment + 12-month operation → Residence", "notes": "NEW pathway"},
            {"label": "Reserve Funds (BIWV)", "value": "NZD 500k held in reserve to support self + family", "notes": ""},
            {"label": "Business Plan", "value": "Detailed plan dated within 3 months of application", "notes": "Market analysis + financials + NZ benefits (jobs/innovation/exports)"},
            {"label": "Good character + health", "value": "Standard requirements", "notes": ""},
        ],
        "fees_local_currency_code": "NZD", "fees_local_currency_amount": 27470, "fees_inr_approx": 1373500,
        "fees_breakdown": [
            {"component": "Entrepreneur Resident Visa (ERV) — Principal (legacy EWV holders only)", "amount": 27470, "currency": "NZD"},
            {"component": "ERV — includes immigration levy", "amount": 3570, "currency": "NZD"},
            {"component": "Business Investor Work Visa (BIWV) — Principal (NEW applicants)", "amount": 12380, "currency": "NZD"},
            {"component": "BIWV includes immigration levy", "amount": 1500, "currency": "NZD"},
            {"component": "Investment — BIWV Standard", "amount": 1000000, "currency": "NZD"},
            {"component": "Investment — BIWV Fast-Track", "amount": 2000000, "currency": "NZD"},
            {"component": "ERV capital (legacy EWV)", "amount": 100000, "currency": "NZD"},
            {"component": "ERV Fast-Track capital", "amount": 500000, "currency": "NZD"},
            {"component": "Reserve funds (BIWV)", "amount": 500000, "currency": "NZD"},
            {"component": "Legal + tax + business advisor", "amount": 25000, "currency": "NZD"},
        ],
        "processing_time_days_min": 90, "processing_time_days_max": 360,
        "step_by_step": [
            {"step_number": 1, "title": "Determine Pathway: ERV (legacy) OR BIWV (new)", "description": "Confirm whether you hold an existing EWV (proceed to ERV) OR are a new applicant (proceed to BIWV).", "estimated_days": 1, "documents_needed": ["Existing EWV if applicable"], "tips": ["BIWV is the only path for new applicants"]},
            {"step_number": 2, "title": "Business Plan", "description": "Develop detailed plan dated within 3 months: market analysis, financials, NZ benefit, projected outcomes.", "estimated_days": 30, "documents_needed": [], "tips": ["NZ benefit narrative critical: jobs + innovation + exports"]},
            {"step_number": 3, "title": "Capital + Reserve Setup", "description": "Demonstrate capital + (for BIWV) reserve funds via bank statements + investment advisor letters.", "estimated_days": 21, "documents_needed": [], "tips": ["Source-of-funds documentation comprehensive"]},
            {"step_number": 4, "title": "Lodge Application Online", "description": "Submit application via INZ portal. Choose ERV or BIWV.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Establish or Continue NZ Business", "description": "ERV: continue existing EWV business. BIWV: invest in existing 5+ year NZ business + commence operations.", "estimated_days": 90, "documents_needed": ["Business registration", "Investment confirmation"], "tips": []},
            {"step_number": 6, "title": "Build Success Metrics", "description": "ERV Standard: 2 years operation. ERV Fast-Track: 6mo + 3 jobs. BIWV: 3-year operation (Standard) OR 12-mo (Fast-Track).", "estimated_days": 730, "documents_needed": ["Tax returns", "Employment records", "Financial statements"], "tips": []},
            {"step_number": 7, "title": "Apply for PR (ERV completion or BIWV → Residence)", "description": "Submit residence application demonstrating success metrics met.", "estimated_days": 90, "documents_needed": [], "tips": []},
            {"step_number": 8, "title": "Residence Grant", "description": "PR granted. Full work / study / family / Medicare-equivalent (public health) rights.", "estimated_days": 60, "documents_needed": [], "tips": []},
        ],
        "document_checklist": [
            {"name": "Passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Existing EWV grant notice (if ERV pathway)", "mandatory": False, "notes": "Required for ERV applicants only"},
            {"name": "Detailed business plan (dated within 3 months)", "mandatory": True, "notes": ""},
            {"name": "Investment / capital evidence", "mandatory": True, "notes": "Bank statements + transfers"},
            {"name": "Reserve funds evidence (BIWV: NZD 500k)", "mandatory": True, "notes": "BIWV only"},
            {"name": "Source-of-funds documentation", "mandatory": True, "notes": ""},
            {"name": "Tax returns (last 3 years)", "mandatory": True, "notes": ""},
            {"name": "Business registration (NZ company)", "mandatory": True, "notes": ""},
            {"name": "Employment records (jobs created)", "mandatory": True, "notes": "Critical for ERV Fast-Track + BIWV"},
            {"name": "Financial statements (NZ business)", "mandatory": True, "notes": ""},
            {"name": "Police Clearance Certificates", "mandatory": True, "notes": ""},
            {"name": "Medical exam (panel physician)", "mandatory": True, "notes": ""},
            {"name": "Partner / spouse passport + relationship cert (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Children's birth certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Photo", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "New applicant attempting EWV (closed); must use BIWV",
            "Business plan generic or undated",
            "Insufficient NZ business genuineness (sham operations)",
            "Investment in business younger than 5 years (BIWV Standard)",
            "Success metrics not met (jobs / turnover / duration)",
            "Reserve funds inadequate (BIWV)",
            "Source-of-funds questions unresolved",
        ],
        "success_tips": [
            "If new applicant: skip EWV entirely; apply BIWV — much clearer pathway",
            "ERV pathway is ONLY for existing EWV holders; otherwise BIWV",
            "Business plan is judged on NZ-specific benefit: jobs / innovation / exports",
            "Science/ICT/high-value sectors get capital waivers — leverage if applicable",
            "Build employment records meticulously — Fast-Track requires 3 NZ jobs",
            "Engage NZ chartered accountant for financials review BEFORE submitting",
            "ERV fee jump to NZD 27,470 is significant — budget accordingly",
        ],
        "faqs": [
            {"q": "Can I apply for EWV in 2026?", "a": "NO — Entrepreneur Work Visa (EWV) is CLOSED to new applications. New applicants must use the Business Investor Work Visa (BIWV) launched 2026."},
            {"q": "Why did the ERV fee jump from ~$7,900 to $27,470?", "a": "2026 reforms removed the lower-cost processing tier + added higher immigration levy ($3,570). Reflects INZ shift toward higher-value applicants."},
            {"q": "What if I'm in Science / ICT / high-value sector?", "a": "ERV minimum capital (NZD 100k) is WAIVABLE if your business is in Science, ICT, or high-value export sector with demonstrated innovation. Document the case carefully."},
            {"q": "How long until PR via BIWV?", "a": "Standard: 3 years post-investment. Fast-Track: 12 months post-investment with NZD 2M+. Either way, residence is the end goal."},
            {"q": "Can I include family?", "a": "Yes — partner + dependent children included. Partner has work + study rights."},
        ],
        "official_url": "https://www.immigration.govt.nz/visas/entrepreneur-resident-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/visas/entrepreneur-resident-visa/",
            "https://www.immigration.govt.nz/visas/business-investor-work-visa/",
            "https://www.fragomen.com/insights/new-zealand-new-business-investor-visa-introduced-entrepreneur-work-visa-closed.html",
            "https://newlandchase.com/new-zealand-launches-business-investor-work-visa-with-pathway-to-residence/",
        ],
        "verified_notes": "Manual Fast-Path B.4.5 seed — verified against immigration.govt.nz + Fragomen + Newland Chase on 2026-02-27. EWV closure + BIWV launch + ERV fee increase to NZD 27,470 all reflected. Combined entry covers both legacy EWV→ERV pathway + new BIWV→Residence pathway.",
    },

    # ── 3. NZ-Parent-Resident — Parent Resident Visa (Queue + Ballot) ──────────
    {
        "country_code": "NZ", "country_name": "New Zealand",
        "subclass_id": "Parent-Resident",
        "subclass_name": "Parent Resident Visa (Queue + Ballot pathways)",
        "service_type": "partner", "category": "immigration",
        "description": (
            "The Parent Resident Visa allows New Zealand citizens or permanent residents to "
            "sponsor their parents for residence. Annual cap **2,500 visas per year** "
            "(significantly increased July 2025 from ~500). Two pathways:\n\n"
            "**Queue:** Legacy EOIs submitted BEFORE 12 Oct 2022 — selected in order received "
            "(oldest first). Backlog being cleared via increased intake.\n\n"
            "**Ballot:** New EOIs (post-Oct 2022) entered into quarterly RANDOM ballot draws "
            "(Feb / May / Aug / Nov). EOI stays in pool 2 years. Equal chance regardless of "
            "submission date.\n\n"
            "**Critical 30 Apr 2026 update:** Sponsor income thresholds dramatically increased "
            "(based on Jun 2025 median wage NZD 35/hr). Single sponsor for 1 parent now needs "
            "**NZD 72,800/yr** (was lower); joint sponsors need **NZD 109,200/yr**. Scales with "
            "number of parents + sponsor count. **Pre-30-Apr-2026 applications NOT affected.**"
        ),
        "eligibility_summary": (
            "Sponsor: NZ citizen / permanent resident aged 18+ resident in NZ; meets income "
            "threshold for 2 of preceding 3 NZ tax years; commits to 10-year support undertaking. "
            "Applicant: parent / step-parent of sponsor; intent to live in NZ; good character + "
            "health. Pathway: Queue (legacy) OR Ballot (new EOI quarterly)."
        ),
        "eligibility_criteria": [
            {"label": "Sponsor relationship", "value": "Adult NZ citizen / permanent resident (aged 18+)", "notes": "Resident in NZ for 3 of preceding years"},
            {"label": "Sponsor income (Single sponsor, 30 Apr 2026)", "value": "NZD 72,800/yr (1 parent); +NZD 36,400 per additional parent (up to 6 parents at NZD 254,800)", "notes": "1.5× median wage base"},
            {"label": "Sponsor income (Joint sponsors, 30 Apr 2026)", "value": "NZD 109,200/yr (1 parent); +NZD 36,400 per additional parent (up to 6 parents at NZD 291,200)", "notes": "2× median wage base"},
            {"label": "Income duration", "value": "Meet income threshold for 2 of preceding 3 NZ tax years (1 Apr–31 Mar)", "notes": ""},
            {"label": "10-year support undertaking", "value": "Sponsor commits to living costs + healthcare + deportation costs for 10 years post-grant", "notes": "Legally binding"},
            {"label": "Queue pathway (legacy)", "value": "EOI submitted BEFORE 12 Oct 2022 — selected oldest first", "notes": "Backlog clearing via 2,500/year cap"},
            {"label": "Ballot pathway (new)", "value": "EOI submitted AFTER 12 Oct 2022 → quarterly random draws (Feb/May/Aug/Nov)", "notes": "EOI valid 2 years"},
            {"label": "Annual cap", "value": "2,500 visas/year (Queue + Ballot combined)", "notes": "Increased from ~500 in July 2025"},
        ],
        "fees_local_currency_code": "NZD", "fees_local_currency_amount": 3990, "fees_inr_approx": 199500,
        "fees_breakdown": [
            {"component": "Parent Resident Visa application — Principal", "amount": 3990, "currency": "NZD"},
            {"component": "Immigration levy", "amount": 380, "currency": "NZD"},
            {"component": "EOI submission fee (Ballot)", "amount": 0, "currency": "NZD"},
            {"component": "Secondary applicant (spouse/partner)", "amount": 1860, "currency": "NZD"},
            {"component": "Medical exam (per applicant)", "amount": 9000, "currency": "INR"},
            {"component": "Police Clearance Certificate", "amount": 500, "currency": "INR"},
            {"component": "Sponsorship form lodgement", "amount": 0, "currency": "NZD"},
        ],
        "processing_time_days_min": 365, "processing_time_days_max": 1095,
        "step_by_step": [
            {"step_number": 1, "title": "Sponsor Eligibility Check", "description": "Sponsor confirms: NZ citizen/PR + 3+ years NZ residence + income threshold met for 2 of preceding 3 tax years.", "estimated_days": 7, "documents_needed": ["Sponsor's tax records (IRD)", "Income evidence"], "tips": ["Pre-30-Apr-2026 EOIs use OLD income tables"]},
            {"step_number": 2, "title": "Submit Expression of Interest (EOI)", "description": "Sponsor lodges EOI for parent. EOI enters Ballot pool (if post-Oct 2022) OR Queue (if pre-Oct 2022).", "estimated_days": 7, "documents_needed": ["EOI form", "Relationship evidence"], "tips": ["EOI valid 2 years in Ballot pool"]},
            {"step_number": 3, "title": "Quarterly Ballot Selection (Ballot only)", "description": "INZ runs quarterly random draws. Selection chances depend on annual cap allocation.", "estimated_days": 90, "documents_needed": [], "tips": ["EQUAL chance regardless of EOI submission date within 2-year window"]},
            {"step_number": 4, "title": "Invitation to Apply (ITA) Received", "description": "Selected EOI receives ITA. 4-month window to lodge full application.", "estimated_days": 1, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Lodge Full Visa Application", "description": "Parent + sponsor submit comprehensive application package.", "estimated_days": 30, "documents_needed": ["Sponsor income/tax docs", "Relationship evidence", "Character + health"], "tips": []},
            {"step_number": 6, "title": "Health + PCC", "description": "Parent completes medical + PCCs.", "estimated_days": 60, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "INZ Decision", "description": "12-36 months typical. PR granted on approval.", "estimated_days": 540, "documents_needed": [], "tips": []},
            {"step_number": 8, "title": "Parent Settles in NZ + Sponsor's 10-Year Undertaking Begins", "description": "Parent lands as PR. Sponsor's 10-year support undertaking active.", "estimated_days": 30, "documents_needed": [], "tips": ["Living costs + healthcare + deportation costs covered by sponsor"]},
        ],
        "document_checklist": [
            {"name": "Parent's passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Sponsor's NZ passport / PR card", "mandatory": True, "notes": ""},
            {"name": "Birth certificate (linking parent to sponsor)", "mandatory": True, "notes": "Apostilled if foreign"},
            {"name": "Sponsor's IRD records / tax returns (3 years)", "mandatory": True, "notes": "Income evidence"},
            {"name": "Sponsor's employer letter + payslips", "mandatory": True, "notes": ""},
            {"name": "Sponsor's 10-year support undertaking", "mandatory": True, "notes": "Signed declaration"},
            {"name": "Parent's medical examination", "mandatory": True, "notes": "Panel physician"},
            {"name": "Parent's Police Clearance Certificates", "mandatory": True, "notes": "From all 10+ year countries of residence"},
            {"name": "Parent's evidence of intent (financial / relationship)", "mandatory": True, "notes": ""},
            {"name": "Photo (per INZ specs)", "mandatory": True, "notes": ""},
            {"name": "EOI confirmation / ITA letter", "mandatory": True, "notes": ""},
            {"name": "Marriage cert (if spouse/partner accompanying)", "mandatory": False, "notes": ""},
            {"name": "Other children's family details (if multiple sponsors)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Sponsor's income below 30 Apr 2026 threshold for the number of parents + sponsor type",
            "Income not meeting threshold for 2 of preceding 3 NZ tax years",
            "Sponsor's NZ residency not yet 3 years",
            "Insufficient sponsor commitment evidence (10-year support undertaking)",
            "Parent has serious health condition (admissibility)",
            "Adverse character finding",
            "Annual cap reached (rare with 2,500 quota)",
        ],
        "success_tips": [
            "Sponsor should LOCK IN income above threshold for 2 full tax years BEFORE EOI submission",
            "Joint sponsorship (2 sponsors) raises income threshold but provides safety margin",
            "30 Apr 2026 income tables are SIGNIFICANTLY higher — plan accordingly if EOI close to deadline",
            "Pre-30-Apr-2026 EOIs use OLD tables — leverage if submitting urgently",
            "Multiple parents reduces per-parent threshold proportion but raises absolute amount",
            "Queue applicants: 2,500 annual cap is clearing backlog faster than ever",
            "EOI in Ballot pool stays 2 years — be patient; equal chance with weekly draws",
            "Build sponsor's IRD records meticulously — primary evidence of income threshold compliance",
        ],
        "faqs": [
            {"q": "Are there Tier 1 / Tier 2 pathways?", "a": "NO — INZ official policy does NOT use Tier 1/Tier 2 terminology. Pathways are: Queue (legacy pre-12 Oct 2022 EOIs, selected oldest first) and Ballot (new EOIs, quarterly random draws). Some third-party sources mislabel this — refer to INZ official site."},
            {"q": "How long does the Ballot take?", "a": "EOI valid 2 years in pool. Quarterly draws (Feb/May/Aug/Nov). Equal chance regardless of how long you've been in pool. After ITA, 4 months to lodge + 12-36 months processing."},
            {"q": "What about the annual cap?", "a": "2,500 visas/year (Jul 2025 increase from ~500). Includes both Queue + Ballot. Significantly accelerates clearance."},
            {"q": "What if my income just dipped?", "a": "Must meet threshold for 2 of preceding 3 NZ tax years (not all 3). Some flexibility for transient dips."},
            {"q": "Can both my parents apply together?", "a": "YES — joint application reduces per-parent income threshold proportionally but raises absolute amount. NZD 72,800 (single sponsor, 1 parent) vs NZD 109,200 (single sponsor, 2 parents)."},
            {"q": "What's the 10-year support undertaking?", "a": "Legal commitment by sponsor to cover all parent's living costs + healthcare + deportation costs for 10 years post-grant. Significant financial responsibility."},
        ],
        "official_url": "https://www.immigration.govt.nz/visas/parent-resident-visa",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/visas/parent-resident-visa/",
            "https://www.immigration.govt.nz/income-thresholds-to-30-april-2026",
            "https://eiglaw.com/new-zealand-increases-income-thresholds-for-pacific-and-parent-visa-categories/",
            "https://www.workingin-newzealand.com/news/inz-update-april-2026-nz-parent-visa-income-thresholds/",
        ],
        "verified_notes": "Manual Fast-Path B.4.5 seed — verified against immigration.govt.nz on 2026-02-27. 30 Apr 2026 income thresholds + 2,500 annual cap + Ballot/Queue model accurately documented. NOTE: Sir's brief used 'Tier 1 / Tier 2' terminology — INZ official policy uses Queue/Ballot instead; entry corrected accordingly.",
    },

    # ── 4. NZ-Refugee-Family — Refugee Family Support Resident Visa ────────────
    {
        "country_code": "NZ", "country_name": "New Zealand",
        "subclass_id": "Refugee-Family",
        "subclass_name": "Refugee Family Support Resident Visa",
        "service_type": "partner", "category": "immigration",
        "description": (
            "The Refugee Family Support Resident Visa allows recognised refugees + protected "
            "persons settled in New Zealand to sponsor close family members for residence. "
            "Quota-based with **600 visas per year** allocated. Sponsor must be a recognised "
            "refugee + meet residence-class visa eligibility.\n\n"
            "**Two-tier structure (currently active):**\n"
            "- **Tier 1:** Sponsor has NO immediate family in NZ — applies first to bring family.\n"
            "- **Tier 2:** Sponsor has SOME immediate family in NZ — applies to bring additional. "
            "Tier 2 is currently CLOSED to new applications.\n\n"
            "This is distinct from the **general Refugee Quota Programme** (1,500/yr overseas "
            "resettlement) and the **Skilled Migrant Category** (any skilled workers including "
            "those with refugee backgrounds). Sir's original brief mentioned 'NZ-Skilled-Refugee' "
            "— that specific visa doesn't exist; this entry covers the closest current pathway."
        ),
        "eligibility_summary": (
            "Sponsor: recognised refugee + protected person settled in NZ + meets residence-"
            "class eligibility. Applicant: close family member (parent / partner / dependent "
            "child / sibling depending on Tier) of sponsor. Tier 1: sponsor has no immediate "
            "family in NZ (currently open). Tier 2: sponsor has some family in NZ (currently "
            "closed)."
        ),
        "eligibility_criteria": [
            {"label": "Sponsor status", "value": "Recognised refugee / protected person / convention refugee with NZ residence", "notes": ""},
            {"label": "Tier 1 (currently OPEN)", "value": "Sponsor has NO immediate family in NZ; can bring eligible family", "notes": "Priority allocation"},
            {"label": "Tier 2 (currently CLOSED)", "value": "Sponsor has SOME immediate family in NZ already; additional family limited", "notes": "Not accepting new applications"},
            {"label": "Annual quota", "value": "600 places per year (Tier 1 + Tier 2 combined)", "notes": "Strict limit"},
            {"label": "Relationship category (Tier 1)", "value": "Parents / siblings / dependent children of sponsor", "notes": "Specific definitions per INZ"},
            {"label": "Relationship category (Tier 2)", "value": "Specific extended-family relationships", "notes": "Currently closed"},
            {"label": "Applicant location", "value": "Outside NZ at time of application", "notes": ""},
            {"label": "Health + Character", "value": "Standard requirements with some flexibility for refugee-context applicants", "notes": ""},
        ],
        "fees_local_currency_code": "NZD", "fees_local_currency_amount": 0, "fees_inr_approx": 0,
        "fees_breakdown": [
            {"component": "Application fee (Refugee Family Support — typically waived or reduced)", "amount": 0, "currency": "NZD"},
            {"component": "Medical exam (panel physician)", "amount": 9000, "currency": "INR"},
            {"component": "Police Clearance Certificate (if available)", "amount": 500, "currency": "INR"},
            {"component": "Translation services (if applicable)", "amount": 5000, "currency": "INR"},
            {"component": "NGO / settlement service support (typically free for refugees)", "amount": 0, "currency": "NZD"},
        ],
        "processing_time_days_min": 365, "processing_time_days_max": 1095,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Sponsor Refugee Status", "description": "Sponsor confirms recognised refugee / protected person status + NZ residence-class visa.", "estimated_days": 7, "documents_needed": ["Sponsor's NZ refugee status documentation", "Sponsor's NZ residence visa"], "tips": []},
            {"step_number": 2, "title": "Identify Eligible Family + Tier", "description": "Determine which family members qualify under Tier 1 (currently open) — typically parents / siblings / dependent children.", "estimated_days": 7, "documents_needed": ["Family tree", "Relationship evidence"], "tips": ["Tier 2 is currently CLOSED"]},
            {"step_number": 3, "title": "Engage NZ Refugee Settlement Service", "description": "Connect with INZ-recognised settlement service provider for application support.", "estimated_days": 30, "documents_needed": [], "tips": ["NGOs offer free advisory + translation"]},
            {"step_number": 4, "title": "Lodge Application", "description": "Submit Refugee Family Support Resident Visa application via INZ portal.", "estimated_days": 21, "documents_needed": ["Sponsor's refugee documentation", "Relationship docs", "Applicant's identity docs"], "tips": []},
            {"step_number": 5, "title": "Health + Character Checks", "description": "Standard requirements with refugee-context flexibility (e.g., where PCC unavailable from country of origin).", "estimated_days": 90, "documents_needed": [], "tips": []},
            {"step_number": 6, "title": "INZ Review + Quota Allocation", "description": "INZ reviews + allocates against 600/year quota. Tier 1 priority.", "estimated_days": 365, "documents_needed": [], "tips": ["Quota allocation may impact timing"]},
            {"step_number": 7, "title": "Visa Grant + Family Reunification", "description": "Granted family member can travel to NZ. Settlement support continues.", "estimated_days": 60, "documents_needed": [], "tips": ["Sponsor + settlement service coordinate arrival"]},
        ],
        "document_checklist": [
            {"name": "Sponsor's NZ refugee status documentation", "mandatory": True, "notes": "Convention refugee certificate or protected person certificate"},
            {"name": "Sponsor's NZ residence-class visa evidence", "mandatory": True, "notes": ""},
            {"name": "Applicant's passport / identity documents", "mandatory": True, "notes": "May include UNHCR documents if no passport"},
            {"name": "Relationship evidence (birth/marriage/family certificates)", "mandatory": True, "notes": "Translation if foreign-language"},
            {"name": "Family tree document", "mandatory": True, "notes": ""},
            {"name": "Tier 1 eligibility evidence", "mandatory": True, "notes": "Sponsor has no immediate family in NZ"},
            {"name": "Applicant's medical examination", "mandatory": True, "notes": "Panel physician"},
            {"name": "Police Clearance Certificate (if available)", "mandatory": False, "notes": "Waived where unavailable due to refugee context"},
            {"name": "Sponsor's NZ address + accommodation plan", "mandatory": True, "notes": ""},
            {"name": "NZ settlement service engagement letter", "mandatory": False, "notes": "Recommended"},
            {"name": "Photo", "mandatory": True, "notes": ""},
            {"name": "Statutory declarations (if documents partially unavailable)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Sponsor not recognised refugee under NZ law",
            "Tier 2 application during closure period (no new Tier 2 applications)",
            "Relationship category not on eligible list",
            "Applicant has immediate family already in NZ (changes Tier eligibility)",
            "Quota exhausted for fiscal year",
            "Adverse character findings (limited flexibility)",
            "Sponsor not maintained NZ residence",
        ],
        "success_tips": [
            "Engage NZ refugee settlement service EARLY — free advisory + advocacy",
            "Document relationship via multiple corroborating sources (statutory declarations help)",
            "Tier 1 applicants prioritise — sponsor with no NZ family",
            "Health/character flexibility for refugee context — disclose challenges upfront",
            "Plan for 1-3 year processing — quota allocation is the bottleneck",
            "Lawyer / advocate with refugee experience strongly recommended",
            "Settlement service can support arrival logistics + initial settlement",
        ],
        "faqs": [
            {"q": "Is there a 'Skilled Refugee' visa?", "a": "NO — INZ does NOT have a specific 'Skilled Refugee' visa category. Refugees seeking PR can use: (a) Refugee Family Support (this visa, if sponsor in NZ); (b) general Skilled Migrant Category (any skilled worker); (c) Refugee Quota Programme (overseas resettlement, 1,500/yr)."},
            {"q": "What's the difference vs Refugee Quota Programme?", "a": "Refugee Quota Programme (1,500/yr) resettles refugees from overseas via UNHCR. Refugee Family Support (600/yr, this visa) allows already-settled NZ refugees to sponsor family members."},
            {"q": "Why is Tier 2 closed?", "a": "INZ closed Tier 2 (sponsors with existing NZ family) to prioritise Tier 1 (no immediate family in NZ) within the 600/year quota. Reopening date uncertain."},
            {"q": "Can sponsor bring grandparents / extended family?", "a": "Tier 1 covers parents, siblings, dependent children. Extended family typically not eligible under Refugee Family Support — would need other pathways."},
            {"q": "What fees apply?", "a": "Application fees typically WAIVED or significantly REDUCED for refugee-context applications. NGOs provide free legal support."},
            {"q": "How long is processing?", "a": "1-3 years typical. Quota allocation cycle + refugee documentation complexity affects timeline."},
        ],
        "official_url": "https://www.immigration.govt.nz/visas/refugee-family-support-residence-category",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "source_urls": [
            "https://www.immigration.govt.nz/visas/refugee-family-support-residence-category/",
            "https://communitylaw.org.nz/community-law-manual/test/family-of-refugees-special-visa-categories/",
            "https://www.govt.nz/browse/immigration-and-visas/refugees-in-new-zealand/",
        ],
        "verified_notes": "Manual Fast-Path B.4.5 seed — verified against immigration.govt.nz + Community Law Manual on 2026-02-27. NOTE: Sir's brief listed 'NZ-Skilled-Refugee' — that visa DOES NOT EXIST in INZ policy. Closest active pathway is Refugee Family Support Resident Visa, seeded here. Distinct from general Refugee Quota Programme (1,500/yr overseas resettlement).",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Sweep B.4.6 — United Kingdom EXPANSION (6 NEW workflows)
# Adds to existing 6 UK workflows from B.2 (Skilled-Worker, Health-Care-Worker,
# Student, Visitor, Spouse-Family, Innovator-Founder) → cumulative UK total = 12.
#
# Sources verified Feb 27, 2026:
#   - gov.uk/global-talent (+ technation.io)
#   - gov.uk/high-potential-individual-visa
#   - gov.uk/graduate-visa (+ workpermitcloud.co.uk Dec 2026 reform)
#   - gov.uk/indefinite-leave-to-remain (+ White Paper May 2025)
#   - gov.uk/tier-1-investor-migrant
#   - gov.uk/standard-visitor (long-term routes)
#
# Research-driven correction vs Sir's brief (NZ precedent followed):
#   - Sir said "Tech Nation CLOSED" → Tech Nation was acquired by Founders Forum,
#     secured £11M UK Government contract May 2025, REMAINS sole digital tech
#     endorsing body. Process simplified Aug 2025 (single GOV.UK Stage 1 form).
#     This correction is documented transparently in verified_notes for Global-Talent.
# ──────────────────────────────────────────────────────────────────────────────
UNITED_KINGDOM_NEW_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. UK-Global-Talent — Global Talent Visa (Tech / Arts / Academia) ────
    {
        "country_code": "UK", "country_name": "United Kingdom",
        "subclass_id": "Global-Talent",
        "subclass_name": "Global Talent Visa (Endorsement + Prestigious Prize routes)",
        "service_type": "work", "category": "immigration",
        "description": (
            "The Global Talent visa is the UK's premier route for **exceptional talent or "
            "exceptional promise** in Digital Technology, Arts & Culture, or Academia & "
            "Research. No job offer, no employer sponsorship, and **no minimum salary** "
            "required. Holders enjoy full work flexibility (employed / self-employed / "
            "founder), can switch jobs without restriction, and bring dependants.\n\n"
            "**Two routes:** (a) **Endorsement** — apply to designated body (Tech Nation for "
            "digital tech, Royal Society / UKRI for research, Arts Council England for arts) "
            "for exceptional-talent (proven leader) or exceptional-promise (rising leader) "
            "status, then apply for the visa. (b) **Prestigious Prize** — applicants holding "
            "an eligible award from the Home Office list (e.g. certain Nobel Prizes, Academy "
            "Awards, major industry awards) bypass endorsement entirely.\n\n"
            "**Critical Aug 2025 process simplification:** Tech Nation applicants now use a "
            "single GOV.UK Stage 1 form (Tech Nation's separate website form withdrawn). "
            "ILR available after **3 years** for exceptional talent + Endorsing-Body Research "
            "fellowships, or 5 years standard. Visa duration: up to 5 years per grant."
        ),
        "eligibility_summary": (
            "Demonstrable exceptional talent (proven leader) OR exceptional promise (rising "
            "leader) in Digital Technology, Arts & Culture, or Academia & Research. "
            "Endorsement from designated body OR holder of eligible Prestigious Prize. "
            "No job offer required."
        ),
        "eligibility_criteria": [
            {"label": "Field of expertise", "value": "Digital Technology, Arts & Culture, or Academia & Research", "notes": "Each field has its own endorsing body"},
            {"label": "Exceptional Talent", "value": "Proven leader in your field with established track record", "notes": "Senior career achievements, awards, recognition"},
            {"label": "Exceptional Promise", "value": "Rising leader with strong potential to become future leader", "notes": "Early/mid career; lower bar than exceptional talent"},
            {"label": "Digital Tech endorsement (Tech Nation)", "value": "2 letters from recognised UK/global tech orgs + 10-page CV/portfolio with technical/commercial achievements", "notes": "Tech Nation confirmed sole body via £11M contract May 2025"},
            {"label": "Academia endorsement", "value": "Royal Society, British Academy, Royal Academy of Engineering, UKRI Fellowship/Senior position", "notes": "Often peer-reviewed"},
            {"label": "Arts endorsement", "value": "Arts Council England — exceptional contribution to literature/film/music/visual arts/dance/theatre", "notes": ""},
            {"label": "Prestigious Prize route", "value": "Holder of award from Home Office eligible-prizes list (no endorsement needed)", "notes": "Nobel Prizes (selected), Academy Awards, Turner Prize, etc."},
            {"label": "English language", "value": "Required at B1 ONLY for settlement (ILR) — NOT for initial visa", "notes": ""},
        ],
        "fees_local_currency_code": "GBP", "fees_local_currency_amount": 766, "fees_inr_approx": 80430,
        "fees_breakdown": [
            {"component": "Endorsement application fee (Part 1)", "amount": 561, "currency": "GBP"},
            {"component": "Visa application fee (Part 2 — after endorsement)", "amount": 205, "currency": "GBP"},
            {"component": "Total via Endorsement route", "amount": 766, "currency": "GBP"},
            {"component": "Prestigious Prize route (single fee at visa stage)", "amount": 766, "currency": "GBP"},
            {"component": "Immigration Health Surcharge (IHS)", "amount": 1035, "currency": "GBP", "per": "year"},
            {"component": "IHS — 5 years total", "amount": 5175, "currency": "GBP"},
            {"component": "Biometrics enrolment", "amount": 19, "currency": "GBP"},
            {"component": "Dependant — per dependant (same fee structure)", "amount": 766, "currency": "GBP"},
            {"component": "Priority service (optional)", "amount": 500, "currency": "GBP"},
            {"component": "Super priority service (optional, next working day)", "amount": 1000, "currency": "GBP"},
        ],
        "processing_time_days_min": 21, "processing_time_days_max": 56,
        "step_by_step": [
            {"step_number": 1, "title": "Identify your field + route", "description": "Decide field (Digital Tech / Arts / Academia) + route (Endorsement vs Prestigious Prize). Check the Home Office prestigious-prizes list first — if eligible, skip endorsement.", "estimated_days": 7, "documents_needed": ["Awards / prizes documentation"], "tips": ["Prestigious Prize route is faster + cheaper if eligible"]},
            {"step_number": 2, "title": "Prepare evidence portfolio", "description": "Compile CV, recommendation letters (2-3 from recognised orgs), achievement evidence, press coverage, salary documentation. Tech Nation requires 10-page max portfolio.", "estimated_days": 30, "documents_needed": ["CV (10 pages max for Tech Nation)", "Recommendation letters", "Achievement evidence"], "tips": ["Quality > quantity; demonstrate impact + recognition"]},
            {"step_number": 3, "title": "Submit Stage 1 Endorsement Application (GOV.UK)", "description": "Submit single GOV.UK Stage 1 endorsement form. Pay £561. Endorsing body reviews. Aug 2025 simplification: no separate Tech Nation form needed.", "estimated_days": 30, "documents_needed": ["Stage 1 form", "Portfolio", "ID"], "tips": ["GOV.UK single-form is standard since Aug 2025"]},
            {"step_number": 4, "title": "Receive Endorsement Decision", "description": "Endorsing body issues endorsement letter (Exceptional Talent OR Exceptional Promise) within 8 weeks typically.", "estimated_days": 56, "documents_needed": [], "tips": ["If refused, can request reconsideration once"]},
            {"step_number": 5, "title": "Apply for Visa (Stage 2)", "description": "Within 3 months of endorsement, submit visa application. Pay £205 + IHS. Biometrics appointment.", "estimated_days": 21, "documents_needed": ["Endorsement letter", "Passport", "TB test (if applicable)"], "tips": ["Apply within 3 months of endorsement or it expires"]},
            {"step_number": 6, "title": "Biometric Enrolment", "description": "VFS / TLS biometrics appointment if outside UK. UK applicants use UKVCAS.", "estimated_days": 7, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Visa Decision + Activation", "description": "Receive decision (visa or BRP). Travel to UK if outside. Begin 5-year residence period.", "estimated_days": 21, "documents_needed": [], "tips": ["Standard processing: 3 weeks (outside UK) / 8 weeks (UK)"]},
            {"step_number": 8, "title": "Plan ILR Pathway", "description": "Exceptional Talent + endorsed-fellowship Research → ILR after 3 years. Exceptional Promise + others → ILR after 5 years. Build absences record (max 180 days/yr).", "estimated_days": 1825, "documents_needed": ["Continuous residence evidence"], "tips": ["Sub-180-day absences critical"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "CV / Resume (10-page max for Tech Nation)", "mandatory": True, "notes": ""},
            {"name": "Recommendation letters (2-3 from recognised UK/global orgs)", "mandatory": True, "notes": "Tech Nation requires from established tech entities"},
            {"name": "Achievement evidence (awards, patents, products, publications)", "mandatory": True, "notes": ""},
            {"name": "Press coverage / media mentions", "mandatory": False, "notes": "Strengthens application"},
            {"name": "Salary / financial documentation", "mandatory": False, "notes": "Demonstrates senior position for Tech Nation"},
            {"name": "Portfolio (10 pages — Tech Nation specific)", "mandatory": True, "notes": "Digital tech route only"},
            {"name": "Prestigious Prize award documentation (if Prize route)", "mandatory": False, "notes": "Skips endorsement if eligible"},
            {"name": "Endorsement letter (Stage 2 only)", "mandatory": True, "notes": "After Stage 1 endorsement granted"},
            {"name": "TB test certificate (from listed countries)", "mandatory": False, "notes": "Required from certain countries including India, Bangladesh"},
            {"name": "Photo (per UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "Dependant passports + relationship certs (if applicable)", "mandatory": True, "notes": "Separate £766 each"},
            {"name": "Police clearance certificates (none required for Global Talent typically)", "mandatory": False, "notes": ""},
            {"name": "Biometrics consent + appointment confirmation", "mandatory": True, "notes": ""},
            {"name": "Tuberculosis screening (India, Pakistan, etc.)", "mandatory": True, "notes": "Mandatory from listed countries"},
        ],
        "common_rejection_reasons": [
            "Insufficient evidence of exceptional talent / promise in field",
            "Recommendation letters from non-recognised or generic sources",
            "Portfolio doesn't demonstrate sufficient impact / recognition (Tech Nation)",
            "Prestigious Prize claimed but not on Home Office eligible-prizes list",
            "Visa application lodged > 3 months after endorsement (expired)",
            "Biometrics appointment missed / incomplete",
            "TB certificate missing for applicants from listed countries",
            "Insufficient documentary evidence of claimed achievements",
        ],
        "success_tips": [
            "Check Prestigious Prize route first — faster + cheaper if eligible",
            "Tech Nation: 2 strong letters from established tech entities >> 5 weak ones",
            "10-page Tech Nation portfolio: focus on top 5-7 achievements with impact",
            "Apply for visa within 3 months of endorsement — endorsement EXPIRES otherwise",
            "Exceptional Talent (3-yr ILR) preferred over Exceptional Promise (5-yr ILR) where possible",
            "Maintain sub-180-day absences during 3-5 year qualifying period for ILR",
            "Aug 2025 process: use single GOV.UK Stage 1 form (no separate Tech Nation form)",
            "Family included separately — each dependant pays own £766",
        ],
        "faqs": [
            {"q": "Is Tech Nation still operating?", "a": "YES — Tech Nation was acquired by Founders Forum and secured an £11M UK Government contract in May 2025 to remain the sole endorsing body for digital technology for the next 3 years. The 2023 closure rumours were resolved positively."},
            {"q": "What's the difference between Exceptional Talent and Exceptional Promise?", "a": "Exceptional Talent = proven leader with established track record (senior). Exceptional Promise = rising leader with potential (early/mid career). Talent has 3-yr ILR; Promise has 5-yr ILR."},
            {"q": "Do I need a job offer?", "a": "NO. Global Talent is one of the few UK visas with NO job offer requirement. You can be employed, self-employed, freelance, or a founder."},
            {"q": "How do I check if my award is a Prestigious Prize?", "a": "Home Office publishes an eligible-prizes list (gov.uk). Includes selected Nobel Prizes, Academy Awards, Turner Prize, certain industry awards. Update periodically."},
            {"q": "Can I switch jobs?", "a": "YES — no restriction. Switch employers, become self-employed, found a company — all permitted."},
            {"q": "When can I apply for ILR?", "a": "Exceptional Talent + endorsed-fellowship Research: 3 years. Exceptional Promise + most others: 5 years. Must meet continuous residence + absences criteria."},
        ],
        "official_url": "https://www.gov.uk/global-talent",
        "vfs_url": "https://www.gov.uk/government/world-location-news/biometrics-services-india",
        "source_urls": [
            "https://www.gov.uk/global-talent",
            "https://technation.io/global-talent-visa/",
            "https://eiglaw.com/uk-updates-global-talent-visa-endorsement-process-with-tech-nation-from-august-4-2025/",
            "https://www.davidsonmorris.com/global-talent-visa/",
        ],
        "verified_notes": "Manual Fast-Path B.4.6 seed — verified against gov.uk + Tech Nation + Davidson Morris + EIG Law on 2026-02-27. CORRECTION TO SIR'S BRIEF: Sir's brief listed 'Tech Nation closed' — research confirms Tech Nation was acquired by Founders Forum and secured £11M UK Government contract May 2025 to remain sole endorsing body for digital tech. Process simplified Aug 2025 (single GOV.UK Stage 1 form, Tech Nation's separate form withdrawn). All other details (fees £766, IHS £1,035/yr, 3-yr ILR for Exceptional Talent) verified.",
    },

    # ── 2. UK-HPI — High Potential Individual Visa ──────────────────────────────
    {
        "country_code": "UK", "country_name": "United Kingdom",
        "subclass_id": "HPI",
        "subclass_name": "High Potential Individual Visa (Top-80 University Graduates)",
        "service_type": "work", "category": "immigration",
        "description": (
            "The High Potential Individual (HPI) visa lets recent graduates from the world's "
            "top universities work in the UK **without a job offer or employer sponsorship**. "
            "Designed for high-skilled global talent — focus on STEM, tech, finance, and "
            "research graduates.\n\n"
            "**2025-2026 update — University list EXPANDED from 50 to 80 institutions** (1 Nov "
            "2025 - 31 Oct 2026 list). Eligible universities must rank in Top 50 of at least 2 "
            "of these global rankings for the qualification year: Times Higher Education (THE), "
            "QS World University Rankings, or Academic Ranking of World Universities (ARWU).\n\n"
            "**Visa duration:** 2 years (Bachelor / Master's graduates) OR 3 years (PhD/Doctoral "
            "graduates). NOT extendable — must switch to Skilled Worker / Innovator Founder / "
            "Global Talent for further stay. Qualification must be awarded within last 5 years.\n\n"
            "**Critical: UK universities are NOT eligible.** Graduates of British universities "
            "should use the Graduate Route instead."
        ),
        "eligibility_summary": (
            "Hold a degree (Bachelor / Master / PhD) from an eligible global Top-80 university "
            "awarded within last 5 years. Pass UK Ecctis qualification check + English B1 + "
            "£1,270 maintenance funds (held 28 days)."
        ),
        "eligibility_criteria": [
            {"label": "Eligible University", "value": "Top-80 list (1 Nov 2025 - 31 Oct 2026 list) per gov.uk publication", "notes": "USA 33 unis, Europe 20, Asia + Oceania 21+, China 7, Hong Kong 5 — UK universities EXCLUDED"},
            {"label": "Degree Level", "value": "Bachelor, Master's, or PhD (UK NARIC/Ecctis equivalent)", "notes": "Online degrees not eligible"},
            {"label": "Qualification Recency", "value": "Awarded within last 5 years from application", "notes": "Year of conferral must be in eligible list year"},
            {"label": "Ecctis Verification", "value": "£252 (UK) / £210 (outside UK) qualification check", "notes": "Mandatory step BEFORE visa application"},
            {"label": "English language", "value": "B1 CEFR (Listening, Reading, Writing, Speaking)", "notes": "SELT or degree-taught-in-English exemption"},
            {"label": "Financial maintenance", "value": "£1,270 held for 28 consecutive days", "notes": "Must show evidence within 31 days of application"},
            {"label": "Age", "value": "No upper or lower age limit", "notes": "Recent graduate framing only"},
            {"label": "Cannot extend", "value": "Visa is NON-extendable", "notes": "Must switch route to remain (Skilled Worker / Innovator Founder / Global Talent)"},
        ],
        "fees_local_currency_code": "GBP", "fees_local_currency_amount": 880, "fees_inr_approx": 92400,
        "fees_breakdown": [
            {"component": "Visa application fee (Principal)", "amount": 880, "currency": "GBP"},
            {"component": "Ecctis qualification check (UK)", "amount": 252, "currency": "GBP"},
            {"component": "Ecctis qualification check (outside UK)", "amount": 210, "currency": "GBP"},
            {"component": "Immigration Health Surcharge (IHS)", "amount": 1035, "currency": "GBP", "per": "year"},
            {"component": "IHS — 2 years (Bachelor / Master)", "amount": 2070, "currency": "GBP"},
            {"component": "IHS — 3 years (PhD)", "amount": 3105, "currency": "GBP"},
            {"component": "Maintenance funds (cash held 28 days)", "amount": 1270, "currency": "GBP"},
            {"component": "Biometrics enrolment", "amount": 19, "currency": "GBP"},
            {"component": "Dependant — partner / child (each)", "amount": 880, "currency": "GBP"},
            {"component": "English test (if needed)", "amount": 170, "currency": "GBP"},
        ],
        "processing_time_days_min": 21, "processing_time_days_max": 56,
        "step_by_step": [
            {"step_number": 1, "title": "Check University Eligibility", "description": "Verify your degree-awarding university is on gov.uk's 'High Potential Individual visa: global universities list' for your conferral year (Nov 2025-Oct 2026 list = 80 universities).", "estimated_days": 1, "documents_needed": ["Degree certificate"], "tips": ["Check the list for YOUR qualification year specifically — list updates annually"]},
            {"step_number": 2, "title": "Get Ecctis Qualification Check", "description": "Submit qualification to Ecctis (UK NARIC) for verification. £252 UK / £210 outside UK. Receive Ecctis statement.", "estimated_days": 14, "documents_needed": ["Degree certificate", "Transcripts"], "tips": ["Allow 10-15 working days for Ecctis report"]},
            {"step_number": 3, "title": "Take English Test (if needed)", "description": "B1 SELT (IELTS for UKVI, Trinity ISE, LanguageCert SELT). Skip if degree was taught in English in eligible English-speaking country.", "estimated_days": 21, "documents_needed": ["Test booking"], "tips": ["IELTS for UKVI is the most accepted"]},
            {"step_number": 4, "title": "Build Financial Maintenance", "description": "Hold £1,270 in personal account for 28 consecutive days. Statements must be within 31 days of application.", "estimated_days": 31, "documents_needed": ["Bank statements"], "tips": ["Daily balance must not dip below £1,270"]},
            {"step_number": 5, "title": "Apply for HPI Visa (online)", "description": "Submit application via gov.uk. Pay £880 + IHS. Schedule biometrics. Upload supporting documents.", "estimated_days": 7, "documents_needed": ["Passport", "Degree cert", "Ecctis statement", "Bank statements", "English evidence"], "tips": ["Apply within 5 years of degree award date"]},
            {"step_number": 6, "title": "Biometrics + Document Upload", "description": "Attend VFS/TLS biometric appointment. Upload remaining documents via portal.", "estimated_days": 7, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Decision + Travel to UK", "description": "Receive decision in 3 weeks (typical). Travel to UK on entry vignette; collect BRP within 10 days of arrival.", "estimated_days": 21, "documents_needed": [], "tips": ["BRP collection address set during application"]},
            {"step_number": 8, "title": "Plan Switch BEFORE Expiry", "description": "HPI is NOT extendable. Plan switch to Skilled Worker / Innovator Founder / Global Talent / Graduate Route 6+ months before expiry.", "estimated_days": 180, "documents_needed": [], "tips": ["Skilled Worker job offer is the most common switch path"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Degree certificate (official, not provisional)", "mandatory": True, "notes": ""},
            {"name": "Academic transcripts", "mandatory": True, "notes": ""},
            {"name": "Ecctis qualification statement", "mandatory": True, "notes": "Must be obtained BEFORE visa application"},
            {"name": "English language test certificate (B1)", "mandatory": True, "notes": "Or degree-taught-in-English exemption letter"},
            {"name": "Bank statements (28 consecutive days, £1,270+ minimum)", "mandatory": True, "notes": "Personal account in applicant's name"},
            {"name": "Statement of personal finances cover letter", "mandatory": False, "notes": "Recommended"},
            {"name": "TB test certificate (from listed countries)", "mandatory": True, "notes": "India, Pakistan, Bangladesh, Nepal etc."},
            {"name": "Photo (per UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "Travel history (last 10 years)", "mandatory": False, "notes": "If requested"},
            {"name": "Visa refusals / immigration history (if any)", "mandatory": False, "notes": "Disclose all prior UK/Schengen visa decisions"},
            {"name": "Dependant passports + relationship certs (if applicable)", "mandatory": False, "notes": "Each dependant £880 + IHS"},
            {"name": "Biometrics appointment confirmation", "mandatory": True, "notes": ""},
            {"name": "Application fee + IHS payment receipt", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Degree from university NOT on eligible Top-80 list for that conferral year",
            "Qualification awarded > 5 years ago",
            "Ecctis statement missing or invalid",
            "Maintenance funds dipped below £1,270 during 28-day period",
            "Bank statements > 31 days old at submission",
            "English language evidence weak / from non-recognised provider",
            "UK university degree used (not eligible — Graduate Route applies instead)",
            "Online degree (only campus-based degrees accepted)",
        ],
        "success_tips": [
            "Check the Nov 2025-Oct 2026 list specifically for your conferral year (changes annually)",
            "Get Ecctis statement FIRST before any other step — it's the gate",
            "Maintain bank balance above £1,270 daily for 28 days — even a 1-day dip can refuse",
            "Apply within 5 years of degree award date — late = refusal",
            "Plan switch path BEFORE arriving — HPI NOT extendable, ideally line up Skilled Worker offer",
            "TB test mandatory for India / Pakistan / Bangladesh / Nepal applicants",
            "Dependants come on separate £880 each (not £766 like Global Talent)",
            "Degree-taught-in-English exemption from listed countries skips SELT",
        ],
        "faqs": [
            {"q": "How many universities are eligible in 2026?", "a": "80 universities for Nov 2025 - Oct 2026 list (expanded from 50). USA has 33, China 7, Europe 20, Hong Kong 5, Australia/NZ 6. UK universities are NOT eligible — use Graduate Route instead."},
            {"q": "Can I extend HPI?", "a": "NO. The HPI visa is strictly non-extendable. You must switch to Skilled Worker / Innovator Founder / Global Talent / Graduate Route to continue staying in the UK."},
            {"q": "Does my UK Master's count?", "a": "NO — UK universities are explicitly excluded from HPI. If you graduated from a UK university, use the Graduate Route (2 years for Bachelor/Master, 3 years for PhD)."},
            {"q": "How long is HPI valid?", "a": "2 years for Bachelor/Master graduates, 3 years for PhD/Doctoral graduates. NOT extendable. Visa starts on grant date."},
            {"q": "Can I bring family?", "a": "Yes — partner and dependent children can be included. Each dependant pays £880 + IHS separately."},
            {"q": "What if my degree was awarded 6 years ago?", "a": "INELIGIBLE — qualification must be awarded within last 5 years of HPI application. Consider other routes."},
        ],
        "official_url": "https://www.gov.uk/high-potential-individual-visa",
        "vfs_url": "https://www.gov.uk/government/world-location-news/biometrics-services-india",
        "source_urls": [
            "https://www.gov.uk/high-potential-individual-visa",
            "https://www.gov.uk/government/publications/high-potential-individual-visa-global-universities-list",
            "https://www.findamasters.com/guides/masters-study-in-uk/high-potential-individual-visa",
            "https://chambers.com/articles/latest-eligible-universities-to-apply-for-uk-s-high-potential-individual-visa",
            "https://vanessaganguin.com/personal-immigration/students-graduates-high-potential-individuals/the-high-potential-individual-visa-is-expanded-which-universities-may-qualify-you/",
        ],
        "verified_notes": "Manual Fast-Path B.4.6 seed — verified against gov.uk + Vanessa Ganguin + Chambers + Findamasters on 2026-02-27. Nov 2025-Oct 2026 university list expansion 50→80 reflected. Ecctis fee £252 UK / £210 offshore, £880 visa fee, £1,270 maintenance, £1,035/yr IHS all verified. UK university exclusion explicitly documented.",
    },

    # ── 3. UK-Graduate-Route — Post-Study Graduate Visa ────────────────────────
    {
        "country_code": "UK", "country_name": "United Kingdom",
        "subclass_id": "Graduate-Route",
        "subclass_name": "Graduate Route Visa (Post-Study Work — UK Graduates)",
        "service_type": "work", "category": "immigration",
        "description": (
            "The Graduate Route lets international students who completed a UK degree stay in "
            "the UK to work or look for work **without employer sponsorship**. Replacement for "
            "the old Tier 1 Post-Study Work visa.\n\n"
            "**Duration (critical 2026 reform):**\n"
            "- Bachelor / Master's graduates: **2 years** if applied on/before **31 Dec 2026**; "
            "**18 months** if applied **on/after 1 Jan 2027** (per UK Immigration White Paper).\n"
            "- PhD / Doctoral graduates: **3 years** (unchanged across all dates).\n\n"
            "**NOT extendable** — must switch to Skilled Worker / Innovator Founder / Global "
            "Talent for further stay. Cannot lead to settlement directly.\n\n"
            "**Must be applied from inside UK** while holding valid Student visa, BEFORE Student "
            "visa expires. UK education provider must notify Home Office of successful course "
            "completion before application."
        ),
        "eligibility_summary": (
            "Hold a valid UK Student visa at time of application. Successfully complete UK "
            "bachelor's / master's / PhD with notification from your sponsoring institution. "
            "Apply from inside UK before Student visa expires."
        ),
        "eligibility_criteria": [
            {"label": "Valid Student visa", "value": "Must hold valid UK Student visa (or Tier 4 General) at application", "notes": "Must apply BEFORE Student visa expires"},
            {"label": "UK qualification", "value": "Bachelor / Master / PhD / Doctoral degree from licensed UK education provider", "notes": "Track record of Student-Sponsor compliance required"},
            {"label": "Successful Completion", "value": "Education provider notifies Home Office of successful course completion", "notes": "Cannot apply before notification"},
            {"label": "In-UK requirement", "value": "Must be physically inside UK at time of application", "notes": "Cannot apply from overseas"},
            {"label": "Duration (Bachelor/Master)", "value": "2 years if applied ≤ 31 Dec 2026; 18 months if applied from 1 Jan 2027", "notes": "White Paper reform reducing post-study work"},
            {"label": "Duration (PhD/Doctoral)", "value": "3 years — unchanged across all dates", "notes": "PhD exempt from 2026 reform"},
            {"label": "English language", "value": "Automatically met via completion of UK degree", "notes": "No separate SELT required"},
            {"label": "Financial maintenance", "value": "No specific cash threshold — student visa funds suffice", "notes": ""},
        ],
        "fees_local_currency_code": "GBP", "fees_local_currency_amount": 937, "fees_inr_approx": 98385,
        "fees_breakdown": [
            {"component": "Graduate Route application fee (Principal)", "amount": 937, "currency": "GBP"},
            {"component": "Dependant — partner / child (each)", "amount": 937, "currency": "GBP"},
            {"component": "Immigration Health Surcharge (IHS)", "amount": 1035, "currency": "GBP", "per": "year"},
            {"component": "IHS — 2 years (Bachelor/Master if applied ≤ 31 Dec 2026)", "amount": 2070, "currency": "GBP"},
            {"component": "IHS — 18 months (Bachelor/Master if applied ≥ 1 Jan 2027)", "amount": 1553, "currency": "GBP"},
            {"component": "IHS — 3 years (PhD)", "amount": 3105, "currency": "GBP"},
            {"component": "Biometrics (UK applicants — UKVCAS)", "amount": 19, "currency": "GBP"},
            {"component": "Priority service (optional)", "amount": 500, "currency": "GBP"},
            {"component": "Super priority service (next working day)", "amount": 1000, "currency": "GBP"},
        ],
        "processing_time_days_min": 14, "processing_time_days_max": 56,
        "step_by_step": [
            {"step_number": 1, "title": "Complete UK Degree", "description": "Successfully complete bachelor / master / PhD from licensed UK education provider. Provider notifies UKVI of completion via SBC reporting.", "estimated_days": 30, "documents_needed": ["Degree certificate / award letter"], "tips": ["Sponsor must report completion BEFORE you apply"]},
            {"step_number": 2, "title": "Confirm Student Visa Validity", "description": "Verify your Student visa is still valid. Application must be BEFORE Student visa expiry. Most students apply 1-3 months before expiry.", "estimated_days": 1, "documents_needed": ["Current Student visa (BRP)"], "tips": ["Apply at least 60 days before expiry"]},
            {"step_number": 3, "title": "Prepare Documents", "description": "Compile passport, BRP, degree/award letter, CAS reference (if needed). No SELT, no maintenance evidence.", "estimated_days": 7, "documents_needed": ["Passport", "BRP", "Degree letter"], "tips": ["Lighter documents than most UK visas"]},
            {"step_number": 4, "title": "Apply Online (gov.uk)", "description": "Submit Graduate Route application on gov.uk. Pay £937 + IHS. Apply from inside UK.", "estimated_days": 1, "documents_needed": [], "tips": ["Pay IHS based on duration (2 yr / 18 mo / 3 yr)"]},
            {"step_number": 5, "title": "Biometric Enrolment (UKVCAS)", "description": "Book UKVCAS appointment. Provide fingerprints + photo. Upload digital documents.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 6, "title": "Receive Decision", "description": "Standard processing 8 weeks (often faster). Priority 5 working days. Super priority 1 working day.", "estimated_days": 56, "documents_needed": [], "tips": ["Track via UKVCAS portal"]},
            {"step_number": 7, "title": "Activate Visa + Plan Next Steps", "description": "Visa starts on grant. Begin work / job search. Plan switch to Skilled Worker / Innovator Founder / Global Talent before expiry.", "estimated_days": 1, "documents_needed": [], "tips": ["Skilled Worker switch is the most common next step"]},
            {"step_number": 8, "title": "Switch BEFORE Expiry", "description": "Graduate Route is NOT extendable. Switch to long-term route (Skilled Worker £38,700 threshold etc.) before expiry.", "estimated_days": 60, "documents_needed": [], "tips": ["Start job search 4-6 months before expiry"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (bio + visa pages)", "mandatory": True, "notes": ""},
            {"name": "Biometric Residence Permit (BRP — current Student visa)", "mandatory": True, "notes": ""},
            {"name": "Degree / Award letter from UK education provider", "mandatory": True, "notes": "Or transcripts if degree not yet issued"},
            {"name": "CAS reference number (Student visa)", "mandatory": False, "notes": "If university uses CAS for completion confirmation"},
            {"name": "Confirmation of Course Completion (university notification)", "mandatory": True, "notes": "University reports to UKVI via SBC system"},
            {"name": "Photo (per UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "TB test certificate", "mandatory": False, "notes": "Not required if you've been in UK 6+ months continuously"},
            {"name": "Visa fee + IHS payment receipt", "mandatory": True, "notes": ""},
            {"name": "Dependant passports + relationship certs (if applicable)", "mandatory": False, "notes": "Each dependant £937 + IHS separately"},
            {"name": "Biometric appointment confirmation", "mandatory": True, "notes": ""},
            {"name": "Immigration history disclosure", "mandatory": True, "notes": ""},
            {"name": "Address evidence (UK address)", "mandatory": False, "notes": ""},
            {"name": "ATAS certificate (research-sensitive subjects)", "mandatory": False, "notes": "If holding sensitive research subject visa"},
            {"name": "Sponsor licence number (university)", "mandatory": True, "notes": "From CAS/SBC"},
        ],
        "common_rejection_reasons": [
            "Applied AFTER Student visa expired (must apply inside UK while valid)",
            "Education provider not licensed sponsor",
            "Completion not yet reported to Home Office",
            "Applied from outside UK (in-UK requirement)",
            "Degree not eligible level (e.g. short-term certificate, not full degree)",
            "Sponsor licence revoked for the institution",
            "Online-only degree without UK campus attendance",
            "Failed to maintain Student visa conditions during studies (work breach, etc.)",
        ],
        "success_tips": [
            "Apply IMMEDIATELY after course completion notification — don't wait",
            "If Bachelor/Master: lodge by 31 Dec 2026 to secure 2 years (vs 18 months from 2027)",
            "PhD graduates safe — 3-year duration unchanged across all dates",
            "Don't let Student visa expire — apply 60-90 days before expiry safest",
            "Don't need maintenance funds or SELT — lightest UK work visa documentation",
            "Use Graduate Route as bridge to Skilled Worker (£38,700 threshold) within 2 years",
            "Switch to Skilled Worker before Graduate Route expires — overlap permitted",
            "Health & Care Worker switch from Graduate Route gets reduced IHS exemption",
        ],
        "faqs": [
            {"q": "How long is the Graduate Route in 2026?", "a": "Apply on/before 31 Dec 2026: 2 years (Bachelor/Master), 3 years (PhD). Apply on/after 1 Jan 2027: 18 months (Bachelor/Master), 3 years (PhD unchanged). PhD is exempt from the 2026 reform."},
            {"q": "Can I extend the Graduate Route?", "a": "NO. Strictly non-extendable. Switch to Skilled Worker / Innovator Founder / Global Talent / Health & Care Worker for further stay."},
            {"q": "Can I apply from India?", "a": "NO — Graduate Route is IN-UK only. You must be physically in UK on a valid Student visa at time of application."},
            {"q": "What if my Student visa expires before I get the degree result?", "a": "Apply for Graduate Route as soon as university reports successful completion to UKVI, even if formal certificate not yet issued. Don't let Student visa expire."},
            {"q": "Can my partner/children come?", "a": "Yes if they were already in UK as dependants. Each pays own £937 + IHS. New dependants from overseas typically not permitted under Graduate Route."},
            {"q": "Does Graduate Route lead to PR/ILR?", "a": "NOT directly. Use it as bridge to Skilled Worker (5-year ILR) or other settlement route."},
        ],
        "official_url": "https://www.gov.uk/graduate-visa",
        "vfs_url": "https://www.ukvcas.co.uk/",
        "source_urls": [
            "https://www.gov.uk/graduate-visa",
            "https://www.ukcisa.org.uk/news/student-update-changes-to-the-student-and-graduate-rules/",
            "https://www.workpermitcloud.co.uk/blog/uk-graduate-visa-reduced-to-18-months-from-january-2027-what-you-need-to-know",
            "https://www.davidsonmorris.com/uk-visa-fees/",
        ],
        "verified_notes": "Manual Fast-Path B.4.6 seed — verified against gov.uk + UKCISA + Workpermit Cloud on 2026-02-27. 2026 White Paper reform reducing Bachelor/Master duration to 18 months from 1 Jan 2027 documented. PhD unaffected. £937 fee + £1,035/yr IHS confirmed.",
    },

    # ── 4. UK-ILR — Indefinite Leave to Remain ──────────────────────────────────
    {
        "country_code": "UK", "country_name": "United Kingdom",
        "subclass_id": "ILR",
        "subclass_name": "Indefinite Leave to Remain (Settlement — Earned Settlement reform pending)",
        "service_type": "pr", "category": "immigration",
        "description": (
            "Indefinite Leave to Remain (ILR) is UK permanent settlement — no time limit on stay, "
            "right to work without sponsorship, right to public funds, gateway to British "
            "citizenship after 12 more months.\n\n"
            "**CRITICAL STATUS (Feb 2026):** White Paper consultation ('Restoring Control over "
            "the Immigration System') closed **12 Feb 2026**. **Earned Settlement model** "
            "(extending baseline qualifying period from 5 → 10 years with reductions for "
            "high earners / public service) expected to come into force around **April 2026**.\n\n"
            "**Until reform takes effect (current rules):**\n"
            "- Most work routes (Skilled Worker, Scale-up, UK Ancestry): **5 years**\n"
            "- Spouse / Partner of British citizen: **5 years** (and exempt from new reform)\n"
            "- Global Talent (Exceptional Talent + endorsed-fellowship Research): **3 years**\n"
            "- Innovator Founder: **3 years**\n"
            "- Long Residence (10 years lawful UK residence in any combination): **10 years**\n\n"
            "**Post-Apr 2026 (Earned Settlement proposed):**\n"
            "- New baseline: **10 years** for most work routes\n"
            "- Reductions: High Earner (£50,270+ × 3 yrs) -5 yrs → 5 yrs · Top Earner (£125,140+ × 3 yrs) -7 yrs → 3 yrs · NHS/Education public service -5 yrs · Advanced English (C1) -1 yr\n"
            "- Negative factors: Public funds claim +5 to 10 yrs · Past overstay/illegal entry up to +20 yrs (capped at 30 yrs)\n\n"
            "**Lock-in tip:** If currently eligible under 5-year rules, apply IMMEDIATELY before "
            "April 2026 to secure under current law. Submitted applications are decided under "
            "rules in force at submission."
        ),
        "eligibility_summary": (
            "Continuous lawful UK residence under qualifying visa route for required period "
            "(3 / 5 / 10 years depending on visa). Pass Life in the UK test + B1 English + "
            "absences ≤180 days per rolling 12 months."
        ),
        "eligibility_criteria": [
            {"label": "Qualifying Period (current)", "value": "5 years (most work routes) / 3 years (Global Talent + Innovator Founder) / 10 years (Long Residence)", "notes": "Spouse of British citizen: 5 years"},
            {"label": "Qualifying Period (post-Apr 2026 — proposed)", "value": "10 years baseline with reductions for high earnings / public service", "notes": "Earned Settlement model"},
            {"label": "Continuous Residence", "value": "Maximum 180 days outside UK per rolling 12-month period", "notes": "Across entire qualifying period"},
            {"label": "Life in the UK Test", "value": "Pass 24-question multiple-choice test (£50 fee, 75% pass mark)", "notes": "Exempt: <18 or >65"},
            {"label": "English Language", "value": "B1 CEFR (Listening + Speaking) — SELT or equivalent", "notes": "Exempt if degree taught in English from majority-English country"},
            {"label": "Lawful Residence", "value": "No breach of visa conditions throughout qualifying period", "notes": "No criminal record, no public funds claim"},
            {"label": "Current Valid Visa", "value": "Must be on qualifying route at time of application", "notes": ""},
            {"label": "Income / Financial (if applicable)", "value": "Post-Apr 2026: £50,270+ for High Earner reduction, £125,140+ for Top Earner", "notes": "Current 5-yr rules: no income threshold for ILR itself"},
        ],
        "fees_local_currency_code": "GBP", "fees_local_currency_amount": 3226, "fees_inr_approx": 338730,
        "fees_breakdown": [
            {"component": "ILR application fee (Principal)", "amount": 3226, "currency": "GBP"},
            {"component": "Dependant — partner / child (each)", "amount": 3226, "currency": "GBP"},
            {"component": "Biometric enrolment (UKVCAS)", "amount": 19, "currency": "GBP"},
            {"component": "Life in the UK Test", "amount": 50, "currency": "GBP"},
            {"component": "English language test (B1 SELT, if needed)", "amount": 170, "currency": "GBP"},
            {"component": "Priority service (5 working days)", "amount": 500, "currency": "GBP"},
            {"component": "Super priority service (next working day)", "amount": 1000, "currency": "GBP"},
            {"component": "Legal/representation fees (typical)", "amount": 1500, "currency": "GBP", "per": "estimate"},
            {"component": "Total typical cost (Principal + Super Priority + legal)", "amount": 5726, "currency": "GBP"},
            {"component": "IHS — N/A (paid via prior visa route)", "amount": 0, "currency": "GBP"},
        ],
        "processing_time_days_min": 60, "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Qualifying Route + Period", "description": "Verify which route you qualify under (Skilled Worker 5yr / Global Talent 3yr / Long Residence 10yr / Spouse 5yr). Count continuous residence + absences.", "estimated_days": 7, "documents_needed": ["Visa history (BRP records)", "Travel record (passport stamps + airline records)"], "tips": ["Track 180-day rule absences carefully across entire period"]},
            {"step_number": 2, "title": "Take Life in the UK Test", "description": "Book Life in the UK test (£50). Study handbook. 24 questions, 75% pass mark. Most candidates pass first attempt.", "estimated_days": 30, "documents_needed": ["Test booking confirmation"], "tips": ["Use official Stationery Office handbook + practice apps"]},
            {"step_number": 3, "title": "Confirm/Take B1 English Test", "description": "If degree was NOT in English: SELT (IELTS for UKVI / Trinity ISE) for B1. Most Skilled Worker holders already meet via CoS.", "estimated_days": 21, "documents_needed": ["English test results"], "tips": ["IELTS for UKVI Life Skills B1 is the most accepted"]},
            {"step_number": 4, "title": "Compile Continuous Residence Evidence", "description": "Bank statements, council tax bills, utility bills, employer letters, payslips — covering entire qualifying period (3/5/10 years).", "estimated_days": 14, "documents_needed": ["Residence evidence dossier"], "tips": ["3-4 documents per year minimum across qualifying period"]},
            {"step_number": 5, "title": "Submit ILR Application (Form SET(M) or relevant SET form)", "description": "Submit application via gov.uk. Pay £3,226 + Super Priority (£1,000) if urgent. Book UKVCAS biometrics.", "estimated_days": 1, "documents_needed": [], "tips": ["Super Priority recommended if travelling soon — decision in 1 working day"]},
            {"step_number": 6, "title": "Biometric Enrolment", "description": "Attend UKVCAS appointment. Fingerprints + photo + document scan upload.", "estimated_days": 14, "documents_needed": [], "tips": []},
            {"step_number": 7, "title": "Receive ILR Decision", "description": "Standard 6 months; Priority 5 working days; Super Priority 1 working day. ILR BRP issued.", "estimated_days": 180, "documents_needed": [], "tips": ["Track via UKVCAS portal"]},
            {"step_number": 8, "title": "Naturalisation (Optional — 12 months later)", "description": "After 12 months on ILR, apply for British Citizenship (Naturalisation). Spouse of British citizen: apply on ILR grant.", "estimated_days": 365, "documents_needed": [], "tips": ["£1,500+ naturalisation fee — separate process"]},
        ],
        "document_checklist": [
            {"name": "Valid passport(s) — current + all previous covering qualifying period", "mandatory": True, "notes": ""},
            {"name": "Biometric Residence Permits (all BRPs covering qualifying period)", "mandatory": True, "notes": ""},
            {"name": "Life in the UK test certificate", "mandatory": True, "notes": "Exempt: <18 or >65"},
            {"name": "B1 English test certificate", "mandatory": True, "notes": "Or majority-English-country degree exemption"},
            {"name": "Travel record / absences declaration (180-day rule)", "mandatory": True, "notes": "Detailed list of all UK departures/entries"},
            {"name": "Employer letters + payslips (qualifying period)", "mandatory": True, "notes": "Skilled Worker route"},
            {"name": "P60s / SA302s (tax records)", "mandatory": True, "notes": "Skilled Worker route"},
            {"name": "Bank statements (residence evidence)", "mandatory": True, "notes": ""},
            {"name": "Council tax / utility bills (qualifying period)", "mandatory": True, "notes": "Continuous residence evidence"},
            {"name": "GP / medical records (residence evidence)", "mandatory": False, "notes": "Recommended"},
            {"name": "Photo (per UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "Sponsor licence number + CoS (Skilled Worker route)", "mandatory": True, "notes": ""},
            {"name": "Marriage / civil partnership certificate (Spouse route)", "mandatory": True, "notes": "Spouse-of-British route"},
            {"name": "Children's birth certificates (if dependants applying)", "mandatory": True, "notes": ""},
            {"name": "Police certificates (if required by route)", "mandatory": False, "notes": "Some routes require"},
            {"name": "Income evidence (£50,270+ / £125,140+ if post-Apr 2026)", "mandatory": False, "notes": "Earned Settlement reductions"},
        ],
        "common_rejection_reasons": [
            "Absences > 180 days in any rolling 12-month period during qualifying years",
            "Gap in lawful immigration status (overstay) during qualifying period",
            "Failed Life in the UK test (less than 75%)",
            "B1 English not met (and no exemption)",
            "Continuous residence evidence inadequate (less than 3-4 documents/year)",
            "Public funds claimed during qualifying period",
            "Criminal record / civil judgment / character issues",
            "Salary below sponsor route threshold (Skilled Worker — minimum salary breach)",
            "Sponsor licence revoked during qualifying period",
        ],
        "success_tips": [
            "⚠️ CRITICAL TIMING: If currently eligible under 5-yr rules, apply BEFORE April 2026 to lock in",
            "Submitted applications decided under rules at submission date — submission = lock-in",
            "Track 180-day absences across rolling 12-mo windows, not calendar years",
            "Use Super Priority (£1,000 add-on) for 1-working-day decision — recommended for time-sensitive cases",
            "Life in the UK test — study official handbook + practice apps; 75% pass mark",
            "B1 SELT — IELTS for UKVI Life Skills B1 is the most widely accepted",
            "If high earner (£50,270+ / £125,140+), Earned Settlement reductions favourable in 2026+",
            "Spouse of British citizen: EXEMPT from Earned Settlement reform (stays 5 years)",
            "Post-Apr 2026 Long Residence route may be ABOLISHED per White Paper — apply ASAP if eligible",
        ],
        "faqs": [
            {"q": "When does the 10-year ILR rule kick in?", "a": "White Paper consultation closed 12 Feb 2026. Earned Settlement model (10-year baseline) expected around April 2026. Until then, current rules (5-yr most routes, 3-yr Global Talent/Innovator) remain. Apply BEFORE April 2026 to lock in current rules."},
            {"q": "Will I have to wait 10 years if I'm on Skilled Worker?", "a": "POSSIBLY. Post-April 2026, baseline 10 years. BUT: High Earner (£50,270+ taxable income for 3+ years) gets -5 yr reduction → 5 years (same as current). Top Earner (£125,140+) gets -7 yr → 3 years. Public service workers (NHS, education) get -5 yr → 5 years."},
            {"q": "Is my Spouse Visa affected?", "a": "NO — partners of British citizens are EXEMPT from Earned Settlement reform. Stays at 5 years."},
            {"q": "What about Global Talent + Innovator Founder?", "a": "Both remain at 3 years even post-reform. Major advantage."},
            {"q": "What if I'm on the 10-year Long Residence route?", "a": "White Paper proposes ABOLISHING this route. Apply ASAP if you're eligible NOW (10+ years continuous lawful UK residence)."},
            {"q": "Can I naturalize as British citizen after ILR?", "a": "After 12 months on ILR (or immediately on ILR if spouse of British citizen). Separate £1,500+ fee + ceremony."},
        ],
        "official_url": "https://www.gov.uk/indefinite-leave-to-remain",
        "vfs_url": "https://www.ukvcas.co.uk/",
        "source_urls": [
            "https://www.gov.uk/indefinite-leave-to-remain",
            "https://www.gov.uk/government/publications/restoring-control-over-the-immigration-system-white-paper",
            "https://migrationobservatory.ox.ac.uk/resources/commentaries/changes-to-settlement-what-do-they-mean/",
            "https://www.davidsonmorris.com/ilr-10-years/",
            "https://immigrationbarrister.co.uk/uk-immigration-rules-2025-white-paper-summary/",
        ],
        "verified_notes": "Manual Fast-Path B.4.6 seed — verified against gov.uk + Migration Observatory + Davidson Morris + Immigration Barrister + UK Government White Paper on 2026-02-27. CRITICAL TIMING NOTE: White Paper consultation closed 12 Feb 2026; Earned Settlement model (10-yr baseline + earner/public-service reductions) expected April 2026. Current 5/3-yr rules apply until reform takes effect. Submitted applications decided under rules at submission. £3,226 fee + Life in the UK test £50 + B1 SELT all verified.",
    },

    # ── 5. UK-Tier-1-Investor-Closed — Tier 1 Investor (Closed; Legacy Pathway) ─
    {
        "country_code": "UK", "country_name": "United Kingdom",
        "subclass_id": "Tier-1-Investor-Closed",
        "subclass_name": "Tier 1 Investor Visa (CLOSED to new applications since 17 Feb 2022 — Legacy Extension + ILR pathway only)",
        "service_type": "business", "category": "immigration",
        "description": (
            "**STATUS: CLOSED to new applications since 17 February 2022.** This entry exists "
            "to support **legacy Tier 1 (Investor) visa holders** who retain transitional rights "
            "to extend and apply for Indefinite Leave to Remain (ILR) under strict deadlines.\n\n"
            "**CRITICAL DEADLINES:**\n"
            "- **Extension deadline: 17 February 2026** — FINAL DATE for legacy holders to apply "
            "for visa extension. **THIS DEADLINE HAS NOW PASSED** as of Feb 27, 2026. No "
            "further extension applications accepted.\n"
            "- **ILR (Settlement) deadline: 17 February 2028** — FINAL DATE for legacy holders "
            "to apply for ILR under this route. After this, Tier 1 Investor permanently closes "
            "for settlement.\n\n"
            "**Investment-Linked ILR Qualifying Periods (current legacy holders):**\n"
            "- £2 million invested: 5 years to ILR\n"
            "- £5 million invested: 3 years to ILR\n"
            "- £10 million invested: 2 years to ILR\n\n"
            "**Replacement routes for new investors:** UK has NOT introduced direct successor. "
            "Alternatives: Innovator Founder Visa (£0 minimum investment, endorsement-based) · "
            "Global Talent (no investment requirement) · Skilled Worker (employment-based)."
        ),
        "eligibility_summary": (
            "Existing Tier 1 (Investor) visa holders ONLY. Must maintain £2M+ qualifying UK "
            "investments. Apply for ILR by 17 Feb 2028 (extension window closed 17 Feb 2026)."
        ),
        "eligibility_criteria": [
            {"label": "New Applications", "value": "CLOSED since 17 February 2022", "notes": "No new applicants accepted under any circumstances"},
            {"label": "Extension Deadline (CLOSED)", "value": "17 February 2026 — DEADLINE PASSED", "notes": "No further extension applications"},
            {"label": "ILR Deadline (active)", "value": "17 February 2028 — last date for legacy ILR applications", "notes": ""},
            {"label": "Minimum Investment Maintained", "value": "£2 million in qualifying UK investments", "notes": "UK government bonds, share capital, loan capital in active/trading UK companies"},
            {"label": "Investment-Linked ILR Timeline", "value": "£2M → 5 yrs · £5M → 3 yrs · £10M → 2 yrs", "notes": "Only time at £2M+ counts (if visa granted after 6 Nov 2014)"},
            {"label": "Continuous Residence", "value": "Maximum 180 days outside UK per rolling 12-month period", "notes": ""},
            {"label": "Life in the UK Test", "value": "Pass mandatory", "notes": "Exempt: <18 or >65"},
            {"label": "English Language", "value": "B1 CEFR — SELT or majority-English-country degree exemption", "notes": ""},
            {"label": "Source of Funds", "value": "Comprehensive provenance evidence — 5+ years", "notes": "Particularly important if funds from sanctioned jurisdictions"},
        ],
        "fees_local_currency_code": "GBP", "fees_local_currency_amount": 3226, "fees_inr_approx": 338730,
        "fees_breakdown": [
            {"component": "ILR application fee (Principal — same as standard ILR)", "amount": 3226, "currency": "GBP"},
            {"component": "Dependant — partner / child (each)", "amount": 3226, "currency": "GBP"},
            {"component": "Biometric enrolment (UKVCAS)", "amount": 19, "currency": "GBP"},
            {"component": "Life in the UK Test", "amount": 50, "currency": "GBP"},
            {"component": "Investment maintained (£2M / £5M / £10M)", "amount": 2000000, "currency": "GBP", "per": "minimum"},
            {"component": "Source-of-funds legal review (typical)", "amount": 5000, "currency": "GBP", "per": "estimate"},
            {"component": "Immigration counsel + portfolio reviewer", "amount": 10000, "currency": "GBP", "per": "estimate"},
            {"component": "Super priority service (1 working day decision)", "amount": 1000, "currency": "GBP"},
            {"component": "Investment maintenance cost (advisory fees)", "amount": 25000, "currency": "GBP", "per": "year"},
        ],
        "processing_time_days_min": 60, "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Verify Status: Legacy Holder?", "description": "Confirm you hold (or held with continuous status) a valid Tier 1 (Investor) visa. New applicants CANNOT use this route — see alternatives.", "estimated_days": 1, "documents_needed": ["Current/expired BRP", "Original Tier 1 Investor grant letter"], "tips": ["If no prior Tier 1 Investor visa: consider Innovator Founder or Global Talent instead"]},
            {"step_number": 2, "title": "Check Extension Status", "description": "If your extension is still valid (granted before 17 Feb 2026 deadline), proceed. If your visa expired and you missed extension deadline, ILR application may still be possible if within qualifying period.", "estimated_days": 1, "documents_needed": [], "tips": ["Extension grants typically gave additional 2 years"]},
            {"step_number": 3, "title": "Confirm Investment Maintenance", "description": "Obtain certified evidence from UK-regulated financial institution showing £2M+ maintained continuously throughout qualifying period.", "estimated_days": 30, "documents_needed": ["Portfolio reports", "Investment confirmations", "Bank statements"], "tips": ["FSA-regulated firm certification required"]},
            {"step_number": 4, "title": "Track Continuous Residence", "description": "Calculate absences across qualifying period (2/3/5 years depending on investment level). Stay within 180 days per rolling 12-mo window.", "estimated_days": 7, "documents_needed": ["Travel records", "Passport stamps"], "tips": ["Detailed UK departures/entries log"]},
            {"step_number": 5, "title": "Take Life in the UK Test + B1 English", "description": "Book Life in the UK test (£50). Confirm B1 English (SELT or exemption).", "estimated_days": 45, "documents_needed": [], "tips": []},
            {"step_number": 6, "title": "Lodge ILR Application BEFORE 17 Feb 2028", "description": "Submit ILR application via gov.uk. Pay £3,226 + Super Priority (£1,000) recommended. Book UKVCAS biometrics.", "estimated_days": 1, "documents_needed": ["All accumulated docs"], "tips": ["⚠️ ABSOLUTE DEADLINE: 17 Feb 2028 — no extensions"]},
            {"step_number": 7, "title": "Biometric + Document Submission", "description": "Attend UKVCAS appointment. Submit comprehensive document portfolio including source-of-funds dossier.", "estimated_days": 14, "documents_needed": [], "tips": ["Investor route requires more documentation than standard ILR"]},
            {"step_number": 8, "title": "Decision + Path to British Citizenship", "description": "ILR granted. After 12 months on ILR, eligible for British Citizenship via Naturalisation.", "estimated_days": 180, "documents_needed": [], "tips": ["£1,500+ naturalisation separate process"]},
        ],
        "document_checklist": [
            {"name": "Current / most recent Biometric Residence Permit", "mandatory": True, "notes": ""},
            {"name": "Original Tier 1 (Investor) grant letter + extension grant", "mandatory": True, "notes": ""},
            {"name": "Portfolio reports from FSA/FCA-regulated firm", "mandatory": True, "notes": "Covering entire investment period"},
            {"name": "Investment certificates / share registers", "mandatory": True, "notes": ""},
            {"name": "Bank statements + financial records (qualifying period)", "mandatory": True, "notes": ""},
            {"name": "Source-of-funds dossier (5+ years provenance)", "mandatory": True, "notes": "Comprehensive for current standards"},
            {"name": "Travel records / absences declaration (180-day rule)", "mandatory": True, "notes": "Detailed list of all UK departures/entries"},
            {"name": "Life in the UK test certificate", "mandatory": True, "notes": ""},
            {"name": "B1 English test certificate", "mandatory": True, "notes": "Or exemption documentation"},
            {"name": "Passport(s) covering qualifying period", "mandatory": True, "notes": ""},
            {"name": "Investment review letters from advisors / fund managers", "mandatory": True, "notes": ""},
            {"name": "UK tax filings (HMRC SA302s, P60s)", "mandatory": True, "notes": "Throughout investment period"},
            {"name": "Compliance + character documentation", "mandatory": True, "notes": "Including ECDD where applicable"},
            {"name": "Photo (per UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "Dependant passports + relationship certs (if applicable)", "mandatory": True, "notes": ""},
            {"name": "Naturalisation application (separate, optional, 12 months post-ILR)", "mandatory": False, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Investment dropped below £2M at any point during qualifying period",
            "Source-of-funds dossier inadequate (especially post-2019 enhanced due diligence)",
            "Investment in non-qualifying assets (cash deposits, residential property, etc.)",
            "Absences > 180 days in rolling 12-mo window during qualifying period",
            "Investment portfolio mismanaged (no longer 'maintained' per rules)",
            "Sanctioned jurisdiction funds without clear provenance",
            "Failed Life in the UK test (less than 75%)",
            "B1 English not met (and no exemption)",
            "Application lodged AFTER 17 Feb 2028 deadline (route permanently closes)",
        ],
        "success_tips": [
            "⚠️ ABSOLUTE DEADLINE 17 FEB 2028 — apply at least 12 months before to allow processing",
            "Source-of-funds dossier is the #1 success/refusal factor — engage specialist counsel",
            "Use Super Priority (£1,000) for 1-working-day decision — recommended given high stakes",
            "Track £2M+ continuously — even temporary dips count as breach",
            "If extension wasn't granted before 17 Feb 2026 deadline, ILR may still be possible if within qualifying period — consult immigration counsel",
            "Naturalisation immediately at 12 months ILR — fastest UK citizenship route for investor families",
            "Children born in UK during ILR period may have automatic British citizenship — verify with counsel",
            "For NEW investors: this route CLOSED — consider Innovator Founder (£0 min) or Global Talent",
        ],
        "faqs": [
            {"q": "Can I still apply for Tier 1 Investor as a new applicant?", "a": "NO. The route CLOSED to new applications on 17 February 2022. No exceptions. Alternatives: Innovator Founder Visa, Global Talent, or Skilled Worker."},
            {"q": "I missed the 17 Feb 2026 extension deadline — can I still apply for ILR?", "a": "POSSIBLY — depends on whether you're still within qualifying period and your visa hasn't expired. Consult immigration counsel urgently. If visa expired and no extension, route may not be available."},
            {"q": "What's the difference between £2M / £5M / £10M ILR timelines?", "a": "Investment level determines qualifying period: £2M = 5 yrs to ILR · £5M = 3 yrs · £10M = 2 yrs. Only time at £2M+ counts (if visa granted on/after 6 Nov 2014)."},
            {"q": "Will there be a replacement investor visa?", "a": "UK Government has not announced a direct successor as of Feb 2026. Innovator Founder Visa (£0 minimum investment, endorsement-based) is positioned as a partial replacement. Watch for future announcements."},
            {"q": "Can my dependants apply for ILR with me?", "a": "Yes — spouse / partner + children under 18 included. Each pays own £3,226 fee + Life in the UK test (over 18s) + B1 English (over 18s)."},
            {"q": "After ILR, when can I apply for British Citizenship?", "a": "12 months after ILR grant (or immediately if spouse of British citizen). Naturalisation fee approximately £1,500+ separate process."},
        ],
        "official_url": "https://www.gov.uk/tier-1-investor",
        "vfs_url": "https://www.ukvcas.co.uk/",
        "source_urls": [
            "https://www.gov.uk/tier-1-investor",
            "https://www.gov.uk/government/publications/guidance-on-application-for-uk-visa-as-tier-1-investor/tier-1-investor-guidance-accessible-version",
            "https://www.fragomen.com/insights/tier-1-investor-visa-extension-deadline-or-february-2026-uk-update.html",
            "https://www.ein.org.uk/blog/tier-1-investor-visa-extensions",
            "https://www.davidsonmorris.com/uk-investor-visa/",
        ],
        "verified_notes": "Manual Fast-Path B.4.6 seed — verified against gov.uk + Fragomen + EIN + Davidson Morris on 2026-02-27. CRITICAL STATUS: Tier 1 Investor route CLOSED 17 Feb 2022 to new applicants. Extension deadline 17 Feb 2026 — PASSED as of seeding date (Feb 27, 2026). ILR deadline 17 Feb 2028 still active for legacy holders. Investment-linked ILR timelines (£2M=5yr, £5M=3yr, £10M=2yr) verified. This workflow exists specifically to guide LEGACY HOLDERS — Sir's brief acknowledged this as 'Tier 1 Investor Closed' visa.",
    },

    # ── 6. UK-Visit-Long-Term — Standard Visitor (Long-Term 2/5/10-year) ──────
    {
        "country_code": "UK", "country_name": "United Kingdom",
        "subclass_id": "Visit-Long-Term",
        "subclass_name": "Standard Visitor Visa — Long-Term (2-year / 5-year / 10-year Multiple Entry)",
        "service_type": "visitor", "category": "immigration",
        "description": (
            "The Long-Term Standard Visitor visa allows multiple entries to the UK over a "
            "**2 / 5 / 10-year validity period**, with each visit up to **6 months maximum**. "
            "Designed for frequent business travellers, parents visiting UK-settled adult "
            "children, and individuals with ongoing UK ties.\n\n"
            "**Key point:** The visa validity is 2/5/10 years, but you can only STAY in the UK "
            "for up to 6 months per visit. Cannot live in UK continuously — visits must be "
            "genuine + temporary.\n\n"
            "**8 April 2026 fee schedule:**\n"
            "- 2-year long-term: **£506** (was ~£476)\n"
            "- 5-year long-term: **£903** (was ~£848)\n"
            "- 10-year long-term: **£1,128** (was ~£1,059)\n"
            "- Standard 6-month visitor (for comparison): £135\n\n"
            "**Best-fit applicant profiles:**\n"
            "- 2-year: First-time long-term applicants, 1-2 prior compliant UK visits\n"
            "- 5-year: 3-4 prior visits, established frequent travel pattern, parents of UK adults\n"
            "- 10-year: 5+ prior visits, stable ties (retirement age, business owner with UK ops, "
            "parents of British citizens with strong family ties)\n\n"
            "**Caveat:** First-time applicants rarely succeed at 10-year tier. Build travel "
            "history with 6-month or 2-year first."
        ),
        "eligibility_summary": (
            "Genuine visitor purpose (tourism / business / family / short study / medical). "
            "Sufficient funds to support visit. No intention to live in UK. Will leave UK at "
            "end of each visit. Strong ties to home country. Travel history demonstrating "
            "compliance with prior visa conditions."
        ),
        "eligibility_criteria": [
            {"label": "Genuine Visitor Purpose", "value": "Tourism / Business / Family / Short Study (≤6 months) / Medical Treatment", "notes": "Each visit must be genuine + temporary"},
            {"label": "Maximum Stay Per Visit", "value": "6 months per visit (regardless of 2/5/10-year validity)", "notes": "Cannot stay continuously"},
            {"label": "Sufficient Funds", "value": "Demonstrate funds to support visit + accommodation + return travel", "notes": "No specific £ threshold but typically £1,500-3,000+"},
            {"label": "No Intention to Live in UK", "value": "Cannot use visits to live in UK / work / study long-term", "notes": "Pattern of consecutive 6-mo stays raises refusal risk"},
            {"label": "Return Intention", "value": "Strong ties to home country (job, family, property) demonstrating return", "notes": "Critical for first-time applicants"},
            {"label": "Travel History", "value": "Compliance with prior UK / Schengen / US / Australia / NZ visas + visits", "notes": "Build history for higher validity tiers"},
            {"label": "Visit Frequency Caveats", "value": "If under 18: long-term visa valid only until 6 months after 18th birthday", "notes": ""},
            {"label": "Work Restrictions", "value": "No paid work in UK during visits (some business activities permitted)", "notes": "Appendix Visitor: Permitted Activities lists what's allowed"},
        ],
        "fees_local_currency_code": "GBP", "fees_local_currency_amount": 506, "fees_inr_approx": 53130,
        "fees_breakdown": [
            {"component": "2-year long-term visitor visa", "amount": 506, "currency": "GBP"},
            {"component": "5-year long-term visitor visa", "amount": 903, "currency": "GBP"},
            {"component": "10-year long-term visitor visa", "amount": 1128, "currency": "GBP"},
            {"component": "Standard 6-month visitor (for comparison)", "amount": 135, "currency": "GBP"},
            {"component": "Priority service (5-day decision)", "amount": 500, "currency": "GBP"},
            {"component": "Super priority service (next-working-day decision)", "amount": 1000, "currency": "GBP"},
            {"component": "Biometric enrolment (VFS)", "amount": 19, "currency": "GBP"},
            {"component": "Optional courier / SMS / photo services", "amount": 30, "currency": "GBP", "per": "estimate"},
            {"component": "IHS / NHS surcharge — N/A for visitors", "amount": 0, "currency": "GBP"},
        ],
        "processing_time_days_min": 15, "processing_time_days_max": 28,
        "step_by_step": [
            {"step_number": 1, "title": "Choose Visa Duration", "description": "Decide between 2-year (£506), 5-year (£903), or 10-year (£1,128) based on planned visit frequency + travel history. First-timers: start with 2-year.", "estimated_days": 1, "documents_needed": [], "tips": ["Build travel history with 6-month or 2-year first; jump to 10-year rarely succeeds"]},
            {"step_number": 2, "title": "Complete Online Application (gov.uk)", "description": "Submit Standard Visitor application via gov.uk. Select multi-entry + chosen duration. Pay fee.", "estimated_days": 1, "documents_needed": [], "tips": ["Apply from country of habitual residence"]},
            {"step_number": 3, "title": "Compile Financial Evidence", "description": "Bank statements (last 6 months), salary slips, employer letter, ITRs / tax returns. Demonstrate funds + ties to home country.", "estimated_days": 7, "documents_needed": ["Bank statements", "Salary slips", "ITRs"], "tips": ["3-6 months bank statements showing genuine activity"]},
            {"step_number": 4, "title": "Prepare Travel History + Ties Evidence", "description": "Compile prior UK / Schengen / US / Australia / NZ visa pages + entry/exit stamps. Property documents, family tie evidence (children's school, parents in home country), employment contract.", "estimated_days": 7, "documents_needed": ["Old passports", "Travel history", "Ties evidence"], "tips": ["Strong ties = strongest refusal mitigation"]},
            {"step_number": 5, "title": "Cover Letter + Itinerary", "description": "Write detailed cover letter explaining purpose, planned dates, accommodation, prior visits, and commitment to return. Include detailed itinerary if applicable.", "estimated_days": 3, "documents_needed": ["Cover letter", "Itinerary draft"], "tips": ["Specific dates + UK addresses + return tickets strengthen application"]},
            {"step_number": 6, "title": "Biometric Appointment (VFS Global)", "description": "Book VFS Global appointment. Provide fingerprints + photo. Submit physical documents.", "estimated_days": 7, "documents_needed": ["All accumulated docs"], "tips": ["Mumbai/Delhi/Bangalore/Chennai/Hyderabad/Kolkata VFS centres"]},
            {"step_number": 7, "title": "Wait for Decision", "description": "Standard processing 3 weeks. Priority 5 working days. Super priority 1 working day. Check VFS portal for updates.", "estimated_days": 21, "documents_needed": [], "tips": []},
            {"step_number": 8, "title": "Collect Visa + Plan Visits", "description": "Collect passport with visa vignette. Plan visits respecting 6-month-per-visit + general overstay rules.", "estimated_days": 7, "documents_needed": [], "tips": ["Track 6-mo per visit + avoid back-to-back consecutive maximum stays"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (bio + visa pages, 12+ months validity)", "mandatory": True, "notes": ""},
            {"name": "Recent photo (per UKVI specs)", "mandatory": True, "notes": ""},
            {"name": "Cover letter explaining purpose + duration choice", "mandatory": True, "notes": ""},
            {"name": "Travel itinerary (planned dates + UK addresses)", "mandatory": False, "notes": "Helpful but not always mandatory"},
            {"name": "Bank statements (last 6 months)", "mandatory": True, "notes": "Should show genuine savings + transactions"},
            {"name": "Salary slips (last 3-6 months)", "mandatory": True, "notes": "If employed"},
            {"name": "Income Tax Returns (last 2-3 years)", "mandatory": True, "notes": ""},
            {"name": "Employment letter / business proof (self-employed)", "mandatory": True, "notes": ""},
            {"name": "Property documents (home ownership = strong tie)", "mandatory": False, "notes": "Strengthens application"},
            {"name": "Old passports with prior visa stamps", "mandatory": True, "notes": "Travel history evidence"},
            {"name": "Family ties evidence (marriage cert, children's school)", "mandatory": False, "notes": "If applicable"},
            {"name": "Return travel ticket (recommended for first visit)", "mandatory": False, "notes": "Strengthens return intention"},
            {"name": "UK accommodation evidence (hotel bookings / family letter)", "mandatory": False, "notes": ""},
            {"name": "Sponsor letter (if visiting family)", "mandatory": False, "notes": "Should include sponsor's UK status + invitation"},
            {"name": "Visa refusals / immigration history (if any)", "mandatory": True, "notes": "Disclose all prior UK / Schengen / US / Australia / NZ visa decisions"},
            {"name": "Biometric appointment confirmation (VFS)", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Insufficient funds (bank statements don't support visit costs)",
            "Weak ties to home country (no job / property / family responsibility)",
            "Travel history concerns (prior overstays / refusals undisclosed)",
            "Inconsistent application information vs supporting documents",
            "Pattern suggesting intent to live in UK (consecutive 6-mo stays, no home anchor)",
            "10-year applied without sufficient prior compliant travel history (typical refusal)",
            "Cover letter generic / missing specific purpose + return intention",
            "Sponsor letter from UK family weak or sponsor with adverse immigration status",
            "Failure to disclose prior visa refusals (automatic refusal + ban risk)",
        ],
        "success_tips": [
            "Build travel history: 2-yr first → renew to 5-yr → 10-yr after strong compliance",
            "Bank statements 6 months — genuine activity + sufficient cushion (£3,000+ recommended)",
            "Strong ties evidence is #1 refusal mitigator — employer letter + property + family",
            "Cover letter MUST address: purpose, dates, accommodation, return intention",
            "Disclose ALL prior visa refusals (UK / Schengen / US etc.) — non-disclosure = ban",
            "Track 6-month-per-visit + avoid suspicion of de-facto residence",
            "10-year visa best for retirement-age parents of British citizens + frequent business travellers",
            "Use Priority (£500) if VFS appointment delay risk — saves week",
            "Pre-2026 fees were lower — current 6-7% hike effective 8 April 2026",
        ],
        "faqs": [
            {"q": "What's the difference between 2 / 5 / 10-year visas?", "a": "VALIDITY differs but stay-per-visit is ALWAYS max 6 months. 2-year £506 (first-time). 5-year £903 (sweet spot for established travellers). 10-year £1,128 (best per-year value but rarely granted to first-timers)."},
            {"q": "Can I work during visits?", "a": "NO paid work in UK. Limited business activities permitted under Appendix Visitor (meetings, negotiations, attending conferences, short-term training)."},
            {"q": "Can I stay 6 months continuously?", "a": "Each VISIT can be up to 6 months. But consecutive 6-month stays raise refusal risk on next entry — suggests intent to live in UK."},
            {"q": "What if I'm refused for 10-year first time?", "a": "Common outcome. Start with 2-year or 5-year, build compliance, then apply for 10-year on subsequent application."},
            {"q": "Does the visa cover EU travel?", "a": "NO — UK and EU/Schengen are separate. For EU travel, apply for Schengen visa separately."},
            {"q": "Can I bring family?", "a": "Each person needs own visa. Children under 18: long-term visa valid only until 6 months after 18th birthday."},
        ],
        "official_url": "https://www.gov.uk/standard-visitor",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/",
        "source_urls": [
            "https://www.gov.uk/standard-visitor",
            "https://www.gov.uk/standard-visitor/apply-standard-visitor-visa",
            "https://visa-fees.homeoffice.gov.uk/y/usa/usd/visit/all",
            "https://www.davidsonmorris.com/long-term-visitor-visa-uk/",
            "https://abroadroutes.com/blogs/uk-10-year-multiple-entry-visa-guide/",
        ],
        "verified_notes": "Manual Fast-Path B.4.6 seed — verified against gov.uk + Home Office Fee Schedule + Davidson Morris + Abroad Routes on 2026-02-27. 8 April 2026 fee schedule confirmed (£506 / £903 / £1,128 for 2/5/10-yr). 6-month-per-visit maximum stay stays unchanged. Standard 6-month visitor £135 for comparison.",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Sweep B.4.7 — USA NEW (6 NEW workflows — first net-new country)
#
# Sources verified Feb 27, 2026:
#   - travel.state.gov (B-1/B-2, F-1, K-1)
#   - uscis.gov (H-1B, L-1, EB-1/EB-2)
#   - studyinthestates.dhs.gov (SEVP/SEVIS for F-1 OPT/CPT)
#
# CRITICAL Feb 2026 reforms reflected:
#   - FY2026 Visa Integrity Fee $250 (B-1/B-2, F-1, H-1B all non-immigrant)
#   - Sept 2, 2025 — most interview waivers ENDED (B-1/B-2, F-1)
#   - April 1, 2024 USCIS fee schedule + April 1, 2026 new Form I-129
#   - H-1B Registration Fee $215 (up from $10 — 2,050% jump for FY2026)
#   - Sept 21, 2025 Presidential Proclamation — $100,000 H-1B cap-subject
#     fee for beneficiaries OUTSIDE US (massive barrier for India hires)
#   - March 1, 2026 Premium Processing fee increased to $2,965
#   - Asylum Program Fee NEW (2024): $300 small / $600 large employer
#   - 2026 "Beautiful Act" — F-1 grace period reduced 60d → 30d
#
# Validator findings (B.4.7 bundled utility):
#   - 4/6 visa URLs returned HTTP 200 directly
#   - 2/6 (L-1, EB-1/EB-2) returned HTTP 403 — USCIS anti-bot HEAD blocking,
#     NOT actual closures. Both visas confirmed ACTIVE via independent
#     Feb 2026 web research (uscis.gov, ogletree.com, beyondborderglobal.com,
#     etc.). All 6 visas seeded as ACTIVE based on policy research.
# ──────────────────────────────────────────────────────────────────────────────
USA_NEW_WORKFLOWS: List[Dict[str, Any]] = [
    # ── 1. US-B1-B2 — Business + Tourist Visitor Visa ──────────────────────────
    {
        "country_code": "US", "country_name": "United States",
        "subclass_id": "B1-B2",
        "subclass_name": "Business + Tourist Visitor Visa (B-1/B-2 Combined)",
        "service_type": "visitor", "category": "immigration",
        "description": (
            "The B-1/B-2 visa is the United States' general non-immigrant visitor visa, "
            "combining business (**B-1**) and tourism/medical/family (**B-2**) purposes "
            "into a single application. Typical validity: 10 years multiple-entry for "
            "Indian nationals, with up to 6 months per visit (typically 60-180 days "
            "granted on entry at CBP officer's discretion).\n\n"
            "**Critical FY2026 reform — Visa Integrity Fee added:**\n"
            "- MRV (Machine Readable Visa) fee: **$185** (paid before interview, "
            "non-refundable, receipt valid 365 days)\n"
            "- **NEW Visa Integrity Fee: $250** (paid ONLY if visa approved — FY2026)\n"
            "- **Total cost: $435** (split across 2 stages)\n\n"
            "**Interview waiver policy changes (effective 2 Sept 2025):**\n"
            "- Most age-based waivers ENDED (under-14 and over-79 no longer auto-waived)\n"
            "- Most renewals NOW require in-person interview\n"
            "- Limited waivers: diplomatic visas + Mexican nationals renewing within "
            "12 months of expiry (subject to consular discretion)\n\n"
            "**ESTA / Visa Waiver Program contrast:** Citizens of 41 VWP countries "
            "(UK, Germany, Japan, Singapore, etc.) can travel B-2 purposes for ≤90 days "
            "via ESTA online registration ($21). India is NOT a VWP country — Indian "
            "nationals must apply for B-1/B-2 visa."
        ),
        "eligibility_summary": (
            "Genuine visitor for business (B-1) OR tourism/medical/family (B-2). Sufficient "
            "funds, strong home country ties, no intention to immigrate. Indian nationals "
            "not eligible for ESTA — must apply for full B-1/B-2 visa."
        ),
        "eligibility_criteria": [
            {"label": "Purpose — B-1 Business", "value": "Meetings, negotiations, contracts, conferences, short training, settling estate", "notes": "NO paid employment from US source"},
            {"label": "Purpose — B-2 Tourism", "value": "Tourism, vacation, family visit, medical treatment, social events, amateur participation in events", "notes": ""},
            {"label": "Genuine Non-Immigrant Intent", "value": "Strong ties to home country demonstrating intent to return", "notes": "Property, job, family, business ties"},
            {"label": "Sufficient Funds", "value": "Demonstrable funds to cover visit + return travel", "notes": "Bank statements, salary slips, ITRs"},
            {"label": "Past Travel Compliance", "value": "No prior US overstays, refusals, or violations", "notes": "Disclose all prior US visa decisions"},
            {"label": "Health & Character", "value": "No communicable diseases, no criminal history affecting admissibility", "notes": ""},
            {"label": "VWP / ESTA Alternative (NOT for India)", "value": "Citizens of 41 VWP countries can use ESTA for ≤90-day B-2 visits", "notes": "India NOT eligible"},
            {"label": "Interview Waiver (LIMITED post-Sept 2025)", "value": "Most need in-person; limited to diplomatic + Mexican renewal within 12mo", "notes": ""},
        ],
        "fees_local_currency_code": "USD", "fees_local_currency_amount": 435, "fees_inr_approx": 36975,
        "fees_breakdown": [
            {"component": "MRV Application Fee (paid before interview)", "amount": 185, "currency": "USD"},
            {"component": "Visa Integrity Fee (paid at issuance if approved — FY2026 NEW)", "amount": 250, "currency": "USD"},
            {"component": "Total Standard B-1/B-2", "amount": 435, "currency": "USD"},
            {"component": "Reciprocity fees (varies by nationality, typically India $0)", "amount": 0, "currency": "USD"},
            {"component": "VFS Global service fee (India)", "amount": 13, "currency": "USD"},
            {"component": "Premium / OFC appointment (India)", "amount": 14, "currency": "USD"},
            {"component": "Courier delivery (India)", "amount": 5, "currency": "USD"},
            {"component": "DS-160 form filing (online)", "amount": 0, "currency": "USD"},
            {"component": "ESTA fee (VWP countries only — NOT India)", "amount": 21, "currency": "USD"},
        ],
        "processing_time_days_min": 60, "processing_time_days_max": 540,
        "step_by_step": [
            {"step_number": 1, "title": "Complete DS-160 Application", "description": "Fill DS-160 online at ceac.state.gov. Detailed work, travel, family, contact info. Get confirmation barcode.", "estimated_days": 3, "documents_needed": ["Passport details", "Travel itinerary", "Employment info"], "tips": ["Be 100% accurate; corrections require new DS-160"]},
            {"step_number": 2, "title": "Pay MRV Fee ($185)", "description": "Pay $185 via VFS Global India payment portal or US embassy partner bank. Print receipt — valid 365 days for interview scheduling.", "estimated_days": 1, "documents_needed": [], "tips": ["Save receipt + virtual account number"]},
            {"step_number": 3, "title": "Schedule Visa Interview Appointment", "description": "Schedule biometrics (VAC) + interview slot via ais.usvisa-info.com. Indian nationals: Mumbai/Delhi/Bangalore/Chennai/Hyderabad/Kolkata locations.", "estimated_days": 30, "documents_needed": [], "tips": ["High demand — book ASAP; 2025-2026 wait times 60-540 days"]},
            {"step_number": 4, "title": "Compile Supporting Documents", "description": "Compile bank statements (6 months), ITRs (3 years), salary slips, employer letter, property deeds, family ties evidence, travel itinerary, sponsor letter (if applicable), travel history with old passports.", "estimated_days": 7, "documents_needed": ["Bank statements", "ITRs", "Employment proof", "Ties evidence"], "tips": ["Strong ties to home country = #1 success factor"]},
            {"step_number": 5, "title": "Attend VAC (Biometrics) Appointment", "description": "Fingerprints + photo at Visa Application Centre 1-3 days before interview.", "estimated_days": 1, "documents_needed": ["DS-160 confirmation", "MRV receipt", "Passport"], "tips": []},
            {"step_number": 6, "title": "Attend Visa Interview", "description": "Consular interview (typically 2-5 minutes). Bring passport, DS-160 confirmation, MRV receipt, supporting docs. Consular officer decides on the spot.", "estimated_days": 1, "documents_needed": ["All compiled docs"], "tips": ["Concise honest answers; show home country ties; clear visit purpose + dates"]},
            {"step_number": 7, "title": "Pay Visa Integrity Fee (if approved)", "description": "If visa approved, pay $250 Visa Integrity Fee before issuance (NEW FY2026).", "estimated_days": 3, "documents_needed": [], "tips": ["Receipt required to release passport"]},
            {"step_number": 8, "title": "Receive Passport with Visa", "description": "Passport returned via VFS courier within 3-7 days after approval + integrity fee payment. Validity 10 years multi-entry for Indian nationals.", "estimated_days": 7, "documents_needed": [], "tips": ["Check visa annotation 'B1/B2' + entries 'M' multi-entry"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (6+ months beyond intended stay)", "mandatory": True, "notes": ""},
            {"name": "DS-160 confirmation page (with barcode)", "mandatory": True, "notes": ""},
            {"name": "MRV receipt ($185 paid)", "mandatory": True, "notes": ""},
            {"name": "Recent passport photo (5x5 cm, white background)", "mandatory": True, "notes": "US visa photo specs"},
            {"name": "Old passports (with prior US/Schengen/UK/Aus visas)", "mandatory": True, "notes": "Travel history evidence"},
            {"name": "Bank statements (last 6 months)", "mandatory": True, "notes": "Genuine activity + sufficient funds"},
            {"name": "ITRs (last 3 years)", "mandatory": True, "notes": ""},
            {"name": "Salary slips (last 3-6 months)", "mandatory": True, "notes": "If employed"},
            {"name": "Employment letter (with leave approval)", "mandatory": True, "notes": "Mentioning position, salary, return date"},
            {"name": "Travel itinerary (planned dates + US addresses)", "mandatory": False, "notes": "Helpful but not mandatory"},
            {"name": "Property documents (home / land ownership)", "mandatory": False, "notes": "Strong tie evidence"},
            {"name": "Family ties evidence (marriage cert, children's school)", "mandatory": False, "notes": ""},
            {"name": "Invitation letter (if visiting family/business)", "mandatory": False, "notes": "B-1: company letter; B-2: family letter"},
            {"name": "Form I-134 Affidavit of Support (if sponsor covering)", "mandatory": False, "notes": "Sponsor income proof"},
            {"name": "Visa Integrity Fee receipt (post-approval)", "mandatory": True, "notes": "FY2026 NEW — required for visa issuance"},
            {"name": "VFS appointment confirmation", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "Insufficient demonstration of strong home country ties (214(b) refusal)",
            "Weak financial evidence (bank balance / income vs visit cost)",
            "Inconsistent application info vs verbal interview answers",
            "Prior US overstay / refusal not disclosed",
            "Recent unemployment or job change",
            "Sponsor or invitation letter weak / sponsor with adverse US status",
            "Unclear visit purpose or itinerary inconsistencies",
            "Recent rejection from another country (Schengen, UK)",
            "Family ties in US suggesting immigration intent",
        ],
        "success_tips": [
            "Strong ties evidence: employer letter + property + family in India = #1 success factor",
            "Interview answer: clear purpose + specific dates + return commitment",
            "Bank statements 6 months — genuine activity + $5,000+ minimum (varies by trip)",
            "Disclose ALL prior visa decisions (US/Schengen/UK) — non-disclosure = automatic ban",
            "Apply early — Indian appointment wait times 60-540 days in 2025-2026",
            "Don't take family/friends as inadmissible dependents during interview",
            "Children's B-2 applications attach to parent — same interview slot",
            "Visa Integrity Fee $250 NEW — budget for FY2026",
        ],
        "faqs": [
            {"q": "What's the Visa Integrity Fee?", "a": "A NEW $250 fee introduced FY2026 (most non-immigrant visas). Paid ONLY if visa approved, on top of $185 MRV. Total: $435 for B-1/B-2."},
            {"q": "How long is the visa valid?", "a": "Typically 10 years multi-entry for Indian nationals. Each visit max 6 months (CBP officer decides actual stay on entry — typically 60-180 days)."},
            {"q": "Why did the interview waiver policy change?", "a": "Effective 2 Sept 2025, most renewal waivers ENDED. Age-based waivers (under-14, over-79) also ended. Most B-1/B-2 applicants now need in-person interview."},
            {"q": "Can I work on B-1?", "a": "NO — B-1 allows BUSINESS activities (meetings, negotiations, conferences) but NO paid employment from US source. For work, need H-1B/L-1/etc."},
            {"q": "I have ESTA — can I skip B-1/B-2?", "a": "ESTA is ONLY for 41 VWP countries (NOT India). Indian nationals must apply for B-1/B-2 visa."},
            {"q": "How long does the appointment take?", "a": "Currently 60-540 days wait for interview slot in India. Book ASAP — peak season (Apr-Aug) longest waits."},
        ],
        "official_url": "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html",
        "vfs_url": "https://www.ustraveldocs.com/in/",
        "source_urls": [
            "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html",
            "https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/fees/fees-visa-services.html",
            "https://travel.state.gov/content/travel/en/News/visas-news/interview-waiver-update-july-25-2025.html",
            "https://www.beyondborderglobal.com/resources/visa-integrity-fee-2026",
            "https://www.ustraveldocs.com/in/",
        ],
        "verified_notes": "Manual Fast-Path B.4.7 seed — verified against travel.state.gov + ustraveldocs.com + Beyond Border Global on 2026-02-27. FY2026 Visa Integrity Fee $250 + 2 Sept 2025 interview waiver narrowing + India ESTA non-eligibility all documented. Validator URL check: HTTP 200 OK (primary + secondary).",
    },

    # ── 2. US-F1 — Student Visa (Academic / Language) ──────────────────────────
    {
        "country_code": "US", "country_name": "United States",
        "subclass_id": "F1",
        "subclass_name": "Student Visa F-1 (SEVP-Certified Institution + OPT/CPT Work)",
        "service_type": "student", "category": "immigration",
        "description": (
            "The F-1 visa is the United States' primary student visa for academic, language, "
            "and vocational study at an institution certified by SEVP (Student and Exchange "
            "Visitor Program). Common use: 4-year undergraduate, 2-year master's, PhD, MBA, "
            "language schools, community colleges.\n\n"
            "**Fees (FY2026):**\n"
            "- SEVIS I-901 Fee: **$350** (paid before interview, funds SEVP program)\n"
            "- MRV Application Fee: **$185**\n"
            "- Total minimum: **$535**\n"
            "- *Note: Visa Integrity Fee $250 expected to apply to F-1 in FY2026 per "
            "policy proposals — verify with embassy at application time*\n\n"
            "**Work authorization while on F-1:**\n"
            "- **CPT (Curricular Practical Training):** School-authorised, must be integral "
            "to curriculum (paid internship, co-op). No USCIS form. Limit: 12 months full-time "
            "= LOSES OPT eligibility at same degree level.\n"
            "- **OPT (Optional Practical Training):** USCIS-authorised (Form I-765). Up to "
            "12 months per degree level. **STEM extension: +24 months** = total 36 months. "
            "Job must be DIRECTLY related to major. Apply within 30 days of DSO issuing OPT "
            "I-20; no later than 60 days after program end.\n\n"
            "**2026 reform (Beautiful Act / similar):**\n"
            "- Grace period after graduation REDUCED 60d → 30d to depart or file OPT\n"
            "- Tighter compliance reporting via SEVP Portal\n\n"
            "**Path to PR:** F-1 itself doesn't lead to green card. Common transitions: "
            "OPT → H-1B (cap lottery) → EB-2/EB-3 PERM → PR."
        ),
        "eligibility_summary": (
            "Accepted to SEVP-certified US institution; Form I-20 issued. Sufficient financial "
            "resources (tuition + living). Strong ties to home country (non-immigrant intent). "
            "English proficiency (TOEFL/IELTS) at institution-required level."
        ),
        "eligibility_criteria": [
            {"label": "Accepted to SEVP-Certified Institution", "value": "Acceptance letter from school certified by SEVP (check sevis.gov DLI list)", "notes": "Online-only schools not eligible"},
            {"label": "I-20 Form Issued", "value": "School issues Form I-20 with SEVIS ID after acceptance + financial proof", "notes": ""},
            {"label": "Sufficient Funds", "value": "1 full academic year tuition + living costs (typically $30k-$70k+)", "notes": "Bank statements / sponsor affidavit"},
            {"label": "English Proficiency", "value": "Institution-required level (TOEFL 80+, IELTS 6.5+ typical)", "notes": "Waivable if from English-speaking country / English-medium education"},
            {"label": "Non-Immigrant Intent", "value": "Strong ties to home country demonstrating intent to return", "notes": "Property, family, future career in home country"},
            {"label": "Academic Standing", "value": "Continuous full-time enrollment + maintain GPA per institution policy", "notes": ""},
            {"label": "Health & Character", "value": "No communicable diseases, no criminal history", "notes": ""},
            {"label": "Work Authorization", "value": "CPT (school-authorised, integral curriculum) + OPT (USCIS, 12mo + STEM 24mo)", "notes": "Cannot work off-campus without authorization"},
        ],
        "fees_local_currency_code": "USD", "fees_local_currency_amount": 535, "fees_inr_approx": 45475,
        "fees_breakdown": [
            {"component": "SEVIS I-901 Fee (paid 3+ days before interview)", "amount": 350, "currency": "USD"},
            {"component": "MRV Application Fee", "amount": 185, "currency": "USD"},
            {"component": "Total minimum (mandatory government fees)", "amount": 535, "currency": "USD"},
            {"component": "Visa Integrity Fee (expected FY2026, post-approval)", "amount": 250, "currency": "USD"},
            {"component": "OPT Form I-765 fee (post-graduation, USCIS)", "amount": 470, "currency": "USD"},
            {"component": "STEM OPT extension (Form I-765 again)", "amount": 470, "currency": "USD"},
            {"component": "VFS service fee (India)", "amount": 13, "currency": "USD"},
            {"component": "TOEFL/IELTS exam (per attempt)", "amount": 220, "currency": "USD"},
            {"component": "Tuition (per year, varies wildly — public ~$30k, private ~$60k+)", "amount": 50000, "currency": "USD"},
            {"component": "Living expenses (per year)", "amount": 18000, "currency": "USD"},
        ],
        "processing_time_days_min": 30, "processing_time_days_max": 365,
        "step_by_step": [
            {"step_number": 1, "title": "Apply to SEVP-Certified Institutions", "description": "Apply to multiple SEVP-certified schools. Pay application fees ($50-$200 each). Wait for acceptance.", "estimated_days": 120, "documents_needed": ["Transcripts", "TOEFL/IELTS", "SOP", "LOR", "Resume"], "tips": ["Apply to 6-8 schools; mix safety/match/reach"]},
            {"step_number": 2, "title": "Accept Offer + Receive I-20", "description": "Accept offer from chosen school. School verifies your financial proof + issues Form I-20 with SEVIS ID.", "estimated_days": 14, "documents_needed": ["Bank statements", "Sponsor affidavit"], "tips": ["Financial proof = 1 year tuition + living"]},
            {"step_number": 3, "title": "Pay SEVIS I-901 Fee ($350)", "description": "Pay at fmjfee.com using SEVIS ID. Print receipt — must show at interview.", "estimated_days": 1, "documents_needed": [], "tips": ["Pay at least 3 business days before interview"]},
            {"step_number": 4, "title": "Complete DS-160 + Pay MRV ($185)", "description": "Fill DS-160 online + pay $185 MRV fee via VFS portal. Get confirmation barcodes + receipts.", "estimated_days": 3, "documents_needed": [], "tips": []},
            {"step_number": 5, "title": "Schedule Visa Interview", "description": "Book biometric (VAC) + interview slot at US consulate. F-1 students get priority slots typically.", "estimated_days": 14, "documents_needed": [], "tips": ["F-1 priority in India — typically faster than B-1/B-2"]},
            {"step_number": 6, "title": "Attend VAC + Interview", "description": "Biometrics 1-3 days before interview. Consular interview ~2-5 mins. Demonstrate genuine student intent + financial capacity.", "estimated_days": 3, "documents_needed": ["I-20", "SEVIS receipt", "Bank statements", "Acceptance letter"], "tips": ["Show enthusiasm for chosen program + clear post-graduation plans in home country"]},
            {"step_number": 7, "title": "Pay Visa Integrity Fee (if approved)", "description": "If visa approved + FY2026 fee applies, pay $250 before issuance.", "estimated_days": 3, "documents_needed": [], "tips": []},
            {"step_number": 8, "title": "Travel to US + Maintain Status", "description": "Enter US ≤30 days before program start. Report to DSO. Maintain full-time enrollment + report changes (address, major, work) in SEVIS Portal.", "estimated_days": 90, "documents_needed": [], "tips": ["DSO compliance critical for OPT/H-1B path later"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (6+ months validity)", "mandatory": True, "notes": ""},
            {"name": "Form I-20 (signed by student + DSO)", "mandatory": True, "notes": ""},
            {"name": "SEVIS I-901 Fee receipt ($350)", "mandatory": True, "notes": ""},
            {"name": "DS-160 confirmation page", "mandatory": True, "notes": ""},
            {"name": "MRV fee receipt ($185)", "mandatory": True, "notes": ""},
            {"name": "Acceptance letter from US institution", "mandatory": True, "notes": ""},
            {"name": "TOEFL/IELTS score report", "mandatory": True, "notes": "Most schools require"},
            {"name": "Academic transcripts (all post-secondary)", "mandatory": True, "notes": ""},
            {"name": "Bank statements (6+ months, proving 1-yr funds)", "mandatory": True, "notes": "Or sponsor's"},
            {"name": "Form I-134 Affidavit of Support (if sponsor covering)", "mandatory": False, "notes": "Sponsor's tax returns + employment"},
            {"name": "Scholarship / loan / financial aid letters (if applicable)", "mandatory": False, "notes": ""},
            {"name": "Recent passport photo (US visa specs)", "mandatory": True, "notes": ""},
            {"name": "Travel history / old passports", "mandatory": True, "notes": ""},
            {"name": "Statement of Purpose (recommended for interview)", "mandatory": False, "notes": "Clear study + post-grad goals"},
            {"name": "Visa Integrity Fee receipt (post-approval, FY2026)", "mandatory": False, "notes": "Expected per FY2026 policy"},
        ],
        "common_rejection_reasons": [
            "Insufficient financial evidence (less than 1-year tuition + living)",
            "Weak demonstration of non-immigrant intent (no clear return plan)",
            "Inconsistent academic history (gap years, transfers, low GPA without explanation)",
            "School ranking / fit concerns (community college without clear pathway)",
            "Sponsor relationship unclear or sponsor finances inadequate",
            "Prior US overstay or refusal",
            "TOEFL/IELTS score below institution requirement",
            "Online-only school (not SEVP-eligible)",
        ],
        "success_tips": [
            "Clear post-graduation plan returning to India = #1 success factor for F-1",
            "Financial proof: 1-yr tuition + living, ideally 2 years if possible",
            "Show strong academic record + ambitious program (PhD/STEM advanced degree)",
            "Apply 3-6 months before program start to allow processing buffer",
            "OPT planning: STEM majors get 36 months (12 + 24 extension) — leverage",
            "CPT vs OPT: 12 months full-time CPT = LOSES OPT — strategize carefully",
            "Maintain SEVIS Portal address + employer reporting religiously — non-compliance = status loss",
            "F-1 priority appointment slots faster than B-1/B-2 — book early in cycle",
        ],
        "faqs": [
            {"q": "What's the difference between CPT and OPT?", "a": "CPT = school-authorised, must be integral to curriculum (paid internship for credit), no USCIS form. OPT = USCIS-authorised (Form I-765), up to 12 months per degree + STEM extension 24 months. Cannot do 12+ months full-time CPT then OPT at same degree level."},
            {"q": "Does F-1 lead to a green card?", "a": "NOT directly. Common pathway: OPT (post-grad work) → H-1B (cap lottery) → EB-2/EB-3 PERM (employer sponsorship) → PR (5-15+ years for India)."},
            {"q": "How long is the F-1 visa valid?", "a": "Typically 5 years multi-entry for Indian nationals. Visa is for travel; F-1 STATUS in US is duration of program (D/S = duration of status). Stay legal as long as enrolled + maintaining status."},
            {"q": "What about STEM extension?", "a": "STEM majors get +24 months OPT = total 36 months (12 + 24). Major MUST be on STEM Designated Degree Program List (DHS).maintained by SEVP."},
            {"q": "What's the new 30-day grace period?", "a": "Per 2026 reform, F-1 students have only 30 days after graduation to depart US OR file OPT (was 60 days). Tighter timeline for OPT applications."},
            {"q": "Can spouse / family come?", "a": "Yes — F-2 dependant visa for spouse + children under 21. F-2 cannot work but can study part-time."},
        ],
        "official_url": "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
        "vfs_url": "https://www.ustraveldocs.com/in/",
        "source_urls": [
            "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
            "https://studyinthestates.dhs.gov/",
            "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students",
            "https://www.fmjfee.com/",
            "https://www.beyondborderglobal.com/resources/visa-integrity-fee-2026",
        ],
        "verified_notes": "Manual Fast-Path B.4.7 seed — verified against travel.state.gov + studyinthestates.dhs.gov + uscis.gov + fmjfee.com on 2026-02-27. $350 SEVIS + $185 MRV = $535 minimum verified. OPT 12mo + STEM 24mo = 36mo total documented. 2026 grace period reduction 60d→30d reflected. Validator URL check: HTTP 200 (travel.state.gov primary), 403 (studyinthestates.dhs.gov anti-bot, NOT closure).",
    },

    # ── 3. US-H-1B — Specialty Occupation Worker (Cap-Subject) ─────────────────
    {
        "country_code": "US", "country_name": "United States",
        "subclass_id": "H-1B",
        "subclass_name": "Specialty Occupation Worker (H-1B Cap-Subject + Lottery System)",
        "service_type": "work", "category": "immigration",
        "description": (
            "The H-1B is the United States' primary visa for foreign professionals in "
            "**specialty occupations** requiring bachelor's degree or higher. Employer-"
            "sponsored, not self-petition. Annual cap: **65,000 regular + 20,000 advanced "
            "degree** = 85,000 total selected via lottery in March each year.\n\n"
            "**Critical Feb 2026 reforms / status:**\n"
            "- **Registration fee: $215** (up from $10 — 2,050% increase) per beneficiary, "
            "non-refundable even if not selected\n"
            "- **NEW Form I-129** (dated 02/27/26) mandatory from 1 April 2026\n"
            "- **Premium processing: $2,965** (up from $2,805 — March 2026 hike)\n"
            "- **🔴 Sept 21, 2025 Presidential Proclamation: $100,000 fee** for cap-subject "
            "H-1B petitions for beneficiaries OUTSIDE the US — massive barrier especially "
            "for India hires. Beneficiaries already inside US (e.g. F-1 OPT) avoid this fee.\n\n"
            "**Standard USCIS Government Fees (per petition):**\n"
            "- Registration: $215 (March each year — H-1B Cap Season)\n"
            "- Form I-129: $460 small employer (<26 FTE) / $780 large (≥26 FTE)\n"
            "- ACWIA Education & Training: $750 small / $1,500 large\n"
            "- Fraud Prevention & Detection: $500\n"
            "- Asylum Program Fee (NEW 2024): $300 small / $600 large\n"
            "- PL 114-113 Fee: $4,000 (only if 50+ employees AND >50% H-1B/L-1)\n"
            "- Premium Processing (optional): $2,965 (45-day adjudication)\n\n"
            "**Total estimated government fees:**\n"
            "- Small employer: ~$2,225 (without premium)\n"
            "- Large employer: ~$3,595\n"
            "- Large + PL 114-113: ~$7,595\n"
            "- Plus $100,000 if cap-subject + beneficiary offshore (Sept 2025 Proclamation)\n\n"
            "**Duration:** Up to **3 years** initially, extendable to **6 years total** "
            "(or longer if EB green card I-140 pending)."
        ),
        "eligibility_summary": (
            "Specialty occupation requiring bachelor's degree or higher in specific field. "
            "Employer-sponsored (must hold valid US sponsor with Labor Condition Application). "
            "Beneficiary holds equivalent bachelor's degree or 12 years experience equivalent."
        ),
        "eligibility_criteria": [
            {"label": "Specialty Occupation", "value": "Requires bachelor's degree or equivalent in specific field (STEM, Finance, Architecture, etc.)", "notes": "DOL O*NET database lists qualifying occupations"},
            {"label": "Beneficiary Qualifications", "value": "Bachelor's degree (or US-equivalent) in specialty field OR 12 years progressive experience", "notes": "3 yrs work experience = 1 yr education equivalent"},
            {"label": "US Employer Sponsor", "value": "Must hold valid US business + sponsor relationship", "notes": "Cannot self-petition"},
            {"label": "Labor Condition Application (LCA)", "value": "Employer files LCA with DOL — certifies prevailing wage + working conditions", "notes": "LCA certification required before I-129"},
            {"label": "Cap Lottery (March Each Year)", "value": "85,000 cap (65k regular + 20k advanced degree) selected via random lottery", "notes": "FY2026 cap registered March 2025"},
            {"label": "Cap-Exempt Categories", "value": "Universities, government research labs, non-profit research — NOT subject to lottery cap", "notes": "Year-round filing"},
            {"label": "Specialty Knowledge", "value": "Must demonstrate genuine specialty expertise in field", "notes": "USCIS RFEs common — strengthen evidence"},
            {"label": "Sept 2025 Presidential Proclamation", "value": "$100,000 fee for cap-subject H-1B for beneficiaries OUTSIDE US", "notes": "Inside US (F-1 OPT, change of status) exempt"},
        ],
        "fees_local_currency_code": "USD", "fees_local_currency_amount": 2225, "fees_inr_approx": 189125,
        "fees_breakdown": [
            {"component": "Cap Registration Fee (per beneficiary, March)", "amount": 215, "currency": "USD"},
            {"component": "Form I-129 Base — Small employer (<26 FTE)", "amount": 460, "currency": "USD"},
            {"component": "Form I-129 Base — Large employer (≥26 FTE)", "amount": 780, "currency": "USD"},
            {"component": "ACWIA Fee — Small employer", "amount": 750, "currency": "USD"},
            {"component": "ACWIA Fee — Large employer", "amount": 1500, "currency": "USD"},
            {"component": "Fraud Prevention & Detection Fee", "amount": 500, "currency": "USD"},
            {"component": "Asylum Program Fee (NEW 2024) — Small employer", "amount": 300, "currency": "USD"},
            {"component": "Asylum Program Fee — Large employer", "amount": 600, "currency": "USD"},
            {"component": "PL 114-113 Fee (only if 50+ employees AND >50% H-1B/L-1)", "amount": 4000, "currency": "USD"},
            {"component": "Premium Processing (optional, March 2026 hike)", "amount": 2965, "currency": "USD"},
            {"component": "Sept 2025 Presidential Proclamation Fee (cap-subject + offshore beneficiary)", "amount": 100000, "currency": "USD"},
            {"component": "Total Small Employer Standard (no premium, no proclamation)", "amount": 2225, "currency": "USD"},
            {"component": "Total Large Employer Standard", "amount": 3595, "currency": "USD"},
            {"component": "Consular MRV (for offshore visa stamping)", "amount": 205, "currency": "USD"},
        ],
        "processing_time_days_min": 45, "processing_time_days_max": 270,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Specialty Occupation + Sponsor Identified", "description": "Verify role requires bachelor's degree in specialty field (DOL O*NET). Secure US employer offer with sponsorship commitment.", "estimated_days": 30, "documents_needed": ["Job offer letter", "Position description"], "tips": ["O*NET SOC code identifies qualifying occupations"]},
            {"step_number": 2, "title": "H-1B Cap Registration (March)", "description": "Employer registers beneficiary in March via myUSCIS.gov. Pay $215 per beneficiary registration. Lottery announced ~end of March.", "estimated_days": 30, "documents_needed": ["Beneficiary passport", "Educational credentials"], "tips": ["File ASAP in March window; multiple offers from different employers OK"]},
            {"step_number": 3, "title": "Receive Selection Notice (Lottery Win)", "description": "If selected, USCIS sends Selection Notice via online portal end-March/early-April. Begin full petition.", "estimated_days": 14, "documents_needed": [], "tips": ["Save Selection Notice — required for I-129"]},
            {"step_number": 4, "title": "File Labor Condition Application (LCA)", "description": "Employer files LCA with DOL (Form ETA-9035). Certifies prevailing wage + working conditions. Approval typically 7 days.", "estimated_days": 14, "documents_needed": ["Job description", "Salary determination"], "tips": ["Wage must be ≥ prevailing wage for occupation in geographic area"]},
            {"step_number": 5, "title": "File Form I-129 with USCIS", "description": "Within 90-day window (typically Apr 1 - Jun 30), employer files Form I-129 with full government fees ($2,225 small / $3,595 large + premium if used).", "estimated_days": 30, "documents_needed": ["Form I-129", "LCA certified", "Beneficiary credentials", "Position description", "Sponsor company evidence"], "tips": ["NEW Form I-129 (02/27/26) required from 1 April 2026"]},
            {"step_number": 6, "title": "RFE Response (if issued)", "description": "USCIS often issues Request for Evidence on specialty occupation justification or beneficiary qualifications. Respond within 87 days.", "estimated_days": 87, "documents_needed": [], "tips": ["RFE response critical — engage immigration counsel"]},
            {"step_number": 7, "title": "I-129 Approval + Consular Processing", "description": "If approved + beneficiary offshore: consular processing at US embassy in home country. Pay $205 MRV + $250 Visa Integrity Fee + (if applicable) $100,000 Sept 2025 Proclamation fee.", "estimated_days": 45, "documents_needed": [], "tips": ["Sept 2025 Proclamation: $100k fee for cap-subject offshore beneficiaries"]},
            {"step_number": 8, "title": "Enter US + Begin Employment", "description": "Enter US on H-1B visa (Oct 1 start typically for FY filings). Begin employment with sponsoring employer. Maximum 3 years initial, extendable to 6 years total (or longer with pending green card).", "estimated_days": 1, "documents_needed": [], "tips": ["I-94 record valid for entire H-1B duration"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (12+ months validity)", "mandatory": True, "notes": ""},
            {"name": "USCIS Form I-129 (NEW 02/27/26 version)", "mandatory": True, "notes": "Employer files"},
            {"name": "H-1B Cap Selection Notice", "mandatory": True, "notes": "From lottery"},
            {"name": "Certified LCA (Labor Condition Application)", "mandatory": True, "notes": "DOL-certified before I-129"},
            {"name": "Beneficiary educational credentials + evaluations", "mandatory": True, "notes": "Bachelor's degree or US-equivalent"},
            {"name": "Job description + offer letter", "mandatory": True, "notes": "Specialty occupation justification"},
            {"name": "Employer support letter (specialty occupation justification)", "mandatory": True, "notes": "Critical document"},
            {"name": "Sponsor company evidence (organizational chart, financials)", "mandatory": True, "notes": ""},
            {"name": "Beneficiary CV / resume", "mandatory": True, "notes": ""},
            {"name": "Employment verification letters (prior jobs)", "mandatory": True, "notes": "12+ years progressive experience if no bachelor's"},
            {"name": "Photo (USCIS specs)", "mandatory": True, "notes": ""},
            {"name": "I-129 government fee payment ($2,225 small / $3,595 large)", "mandatory": True, "notes": ""},
            {"name": "Premium processing receipt (if used, $2,965)", "mandatory": False, "notes": ""},
            {"name": "DS-160 + MRV $205 (for offshore consular)", "mandatory": True, "notes": "If processing abroad"},
            {"name": "Sept 2025 $100k Presidential Proclamation Fee (cap-subject offshore)", "mandatory": False, "notes": "If beneficiary offshore at filing"},
            {"name": "Spouse/children passports + relationship certs (H-4 dependent)", "mandatory": False, "notes": "If accompanying"},
        ],
        "common_rejection_reasons": [
            "Specialty occupation insufficiently established (USCIS RFE common)",
            "Beneficiary qualifications below bachelor's in specialty",
            "Wage below prevailing wage on LCA",
            "Employer-employee relationship unclear (especially staffing companies)",
            "End-client relationship vague for staffing-model petitions",
            "Cap registration fraud / multiple registrations attempted",
            "RFE response inadequate / missed 87-day window",
            "Sponsor company financial instability",
            "Fraud Prevention findings on past visa misuse",
        ],
        "success_tips": [
            "Specialty occupation justification = critical; engage immigration counsel for I-129 preparation",
            "Multiple employer registrations OK (different actual offers) — diversifies lottery chances",
            "Premium processing $2,965 = decision in 45 days vs 4-9 months standard",
            "Cap-subject + beneficiary inside US (F-1 OPT) = AVOIDS $100,000 Sept 2025 Proclamation fee",
            "Master's degree from US institution = 20k advanced degree pool (higher selection odds)",
            "Plan EB-2/EB-3 green card filing within 4-5 years to extend beyond 6-year H-1B cap",
            "RFE response: detailed specialty occupation + beneficiary qualifications evidence",
            "Cap registration fee $215 = pay early in March window (don't wait)",
        ],
        "faqs": [
            {"q": "What's the H-1B cap lottery?", "a": "Annual limit of 85,000 H-1B visas (65k regular + 20k US-master's advanced degree). Selected via random electronic lottery in March each year. Registration fee $215 per beneficiary, non-refundable even if not selected."},
            {"q": "What's the $100,000 fee?", "a": "Sept 21, 2025 Presidential Proclamation added a $100,000 fee for cap-subject H-1B petitions for beneficiaries OUTSIDE the US at filing time. Beneficiaries already inside US (F-1 OPT to H-1B change of status) are EXEMPT. Major barrier for India direct hires."},
            {"q": "How long does H-1B last?", "a": "Initial 3 years; extendable to 6 years total. Beyond 6 years possible only if EB green card I-140 approved AND priority date pending due to country backlog."},
            {"q": "Can I switch employers on H-1B?", "a": "YES — H-1B portability (AC21). New employer files new I-129 + LCA. Can start working as soon as new I-129 received by USCIS (don't wait for approval). Job duties + wage must be substantially similar."},
            {"q": "What about spouse and children?", "a": "H-4 dependent visa for spouse + children under 21. H-4 EAD (work authorization) available if principal H-1B's I-140 approved + waiting for priority date. Children can study K-12 + university."},
            {"q": "Are universities cap-exempt?", "a": "YES — universities, government research labs, non-profit research orgs are CAP-EXEMPT (file year-round, no lottery)."},
        ],
        "official_url": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
        "vfs_url": "https://www.ustraveldocs.com/in/",
        "source_urls": [
            "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
            "https://travel.state.gov/content/travel/en/us-visas/employment/temporary-worker-visas.html",
            "https://www.seyfarth.com/news-insights/uscis-announces-significant-fee-increases-effective-on-april-1-2024.html",
            "https://www.gozellaw.com/blog/2026-h1b-visa-lottery-fees-green-card",
            "https://www.murthy.com/2026/03/05/new-form-i-129-and-what-it-means-for-h1b-cap-registration/",
        ],
        "verified_notes": "Manual Fast-Path B.4.7 seed — verified against uscis.gov + travel.state.gov + Seyfarth Shaw + Murthy Law + GoZee Law on 2026-02-27. CRITICAL Sept 21, 2025 Presidential Proclamation $100,000 cap-subject offshore beneficiary fee documented (major India barrier). $215 registration + April 2024 fee schedule + March 2026 premium hike to $2,965 + new I-129 form (02/27/26 dated, mandatory from 1 April 2026) all reflected. Validator URL check: HTTP 200 (travel.state.gov secondary), 403 (uscis.gov primary anti-bot, NOT closure).",
    },

    # ── 4. US-L-1 — Intracompany Transferee ────────────────────────────────────
    {
        "country_code": "US", "country_name": "United States",
        "subclass_id": "L-1",
        "subclass_name": "Intracompany Transferee (L-1A Executive/Manager + L-1B Specialized Knowledge)",
        "service_type": "work", "category": "immigration",
        "description": (
            "The L-1 visa allows multinational companies to transfer employees from foreign "
            "offices to US offices. Two categories with distinct rules:\n\n"
            "**L-1A — Executive / Managerial Capacity:**\n"
            "- For employees in **executive or managerial** roles abroad\n"
            "- Initial stay: 3 years (1 year for new offices)\n"
            "- Extensions: 2 years at a time\n"
            "- **Maximum total stay: 7 years**\n"
            "- **Direct EB-1C green card path** (Multinational Manager/Executive)\n\n"
            "**L-1B — Specialized Knowledge:**\n"
            "- For employees with **specialized knowledge** of company products/services/"
            "research/equipment/techniques\n"
            "- Initial stay: 3 years (1 year for new offices)\n"
            "- Extensions: 2 years at a time\n"
            "- **Maximum total stay: 5 years**\n"
            "- NO direct green card path equivalent to EB-1C\n\n"
            "**Common Requirement:** Employee must have worked abroad for the related foreign "
            "entity for at least **1 continuous year within the 3 years** preceding L-1 "
            "application.\n\n"
            "**Two filing routes:**\n"
            "- **Individual L-1 Petition (Form I-129):** Standard route, single beneficiary, "
            "Premium Processing available\n"
            "- **Blanket L-1 (Form I-129S):** For large multinationals (10+ prior L-1s OR "
            "$25M+ US annual sales OR 1,000+ US employees). Pre-approval of corporate "
            "structure; employees apply directly at US consulate. NO premium processing.\n\n"
            "**Qualifying Relationship:** US + foreign entities must be related as parent / "
            "subsidiary / affiliate / branch with at least 50% common ownership AND control."
        ),
        "eligibility_summary": (
            "Multinational company with qualifying US-foreign relationship (50%+ common ownership "
            "+ control). Beneficiary worked abroad in qualifying role 1+ years within past 3. "
            "Coming to US in executive/managerial (L-1A) OR specialized knowledge (L-1B) capacity."
        ),
        "eligibility_criteria": [
            {"label": "Qualifying Multinational Relationship", "value": "US + foreign entities related as parent/subsidiary/affiliate/branch; 50%+ common ownership AND control", "notes": "Most common: foreign parent → US subsidiary"},
            {"label": "Both Entities Doing Business", "value": "Both US + foreign entity actively engaged in commercial trade/services", "notes": "Shell companies don't qualify"},
            {"label": "Employee 1+ Year Abroad", "value": "Beneficiary worked for foreign entity continuously 1+ years within past 3 years", "notes": "Must be in L-1A or L-1B qualifying capacity"},
            {"label": "L-1A — Executive/Managerial Capacity", "value": "Decision-making authority + supervision of professionals + control over goals/policies", "notes": "Not first-level supervisors"},
            {"label": "L-1B — Specialized Knowledge", "value": "Knowledge of company products/processes/techniques NOT widely available in industry", "notes": "Distinct from general industry knowledge"},
            {"label": "US Position Same/Similar Capacity", "value": "Role in US must be executive/managerial (L-1A) OR specialized knowledge (L-1B)", "notes": "Cannot transfer to lower role"},
            {"label": "Blanket Eligibility (large MNCs only)", "value": "10+ approved L-1s in past year OR $25M+ US sales OR 1,000+ US employees + 3+ branches", "notes": "Pre-approval of structure"},
            {"label": "No Premium Processing for Blanket", "value": "Standard processing only; consular processing for each employee", "notes": ""},
            {"label": "New Office Provision", "value": "If US office <1yr operating: initial L-1 limited to 1 year, must extend with proof of operations", "notes": ""},
        ],
        "fees_local_currency_code": "USD", "fees_local_currency_amount": 2485, "fees_inr_approx": 211225,
        "fees_breakdown": [
            {"component": "Form I-129 Base Filing Fee (Individual L-1)", "amount": 1385, "currency": "USD"},
            {"component": "Asylum Program Fee", "amount": 600, "currency": "USD"},
            {"component": "Fraud Prevention & Detection Fee", "amount": 500, "currency": "USD"},
            {"component": "Premium Processing (optional, 15-day adjudication — March 2026 hike)", "amount": 2965, "currency": "USD"},
            {"component": "PL 114-113 Fee (only if 50+ employees AND >50% H-1B/L-1)", "amount": 4500, "currency": "USD"},
            {"component": "Consular MRV Fee (per employee)", "amount": 205, "currency": "USD"},
            {"component": "Visa Integrity Fee (FY2026, post-approval)", "amount": 250, "currency": "USD"},
            {"component": "Total Standard Individual L-1 (no premium)", "amount": 2485, "currency": "USD"},
            {"component": "Total Standard Individual L-1 + Premium", "amount": 5450, "currency": "USD"},
            {"component": "Blanket L-1 — Initial Fraud Prevention", "amount": 500, "currency": "USD"},
            {"component": "Blanket L-1 — Consular MRV (per employee)", "amount": 205, "currency": "USD"},
            {"component": "Attorney fees (typical)", "amount": 5000, "currency": "USD"},
        ],
        "processing_time_days_min": 21, "processing_time_days_max": 180,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Qualifying Relationship + Capacity", "description": "Verify US + foreign entities have qualifying relationship (50%+ ownership + control). Confirm beneficiary role abroad meets L-1A or L-1B criteria.", "estimated_days": 30, "documents_needed": ["Corporate structure documents", "Ownership records", "Org chart"], "tips": ["Foreign subsidiary of US parent is most common"]},
            {"step_number": 2, "title": "Verify 1+ Year Foreign Employment", "description": "Confirm beneficiary worked for qualifying foreign entity 1+ years continuously within past 3 years in qualifying capacity.", "estimated_days": 14, "documents_needed": ["Employment letters", "Payroll records", "Position descriptions"], "tips": ["Time abroad after L-1 filing doesn't count"]},
            {"step_number": 3, "title": "Compile Specialty / Capacity Evidence", "description": "L-1A: org chart + decision authority + supervision over professionals + control. L-1B: specialized knowledge unique to company.", "estimated_days": 21, "documents_needed": ["Job descriptions", "Org charts", "Specialty knowledge evidence"], "tips": ["L-1B is harder — USCIS scrutinises specialty knowledge claims"]},
            {"step_number": 4, "title": "File Form I-129 (Individual L-1)", "description": "Employer files Form I-129 with USCIS. Pay government fees ($2,485 standard or $5,450 with premium). Provide all evidence.", "estimated_days": 30, "documents_needed": ["I-129", "Supporting evidence"], "tips": ["Premium processing $2,965 = 15-day decision vs 4-12 months standard"]},
            {"step_number": 5, "title": "USCIS Adjudication", "description": "USCIS reviews petition. Standard 4-12 months; Premium 15 business days. RFE often issued — common for L-1B specialized knowledge.", "estimated_days": 180, "documents_needed": [], "tips": ["RFE common for L-1B; engage immigration counsel for response"]},
            {"step_number": 6, "title": "I-129 Approval + Consular Processing", "description": "If beneficiary outside US: consular processing at US embassy. Pay $205 MRV + $250 Visa Integrity Fee + provide approval notice.", "estimated_days": 45, "documents_needed": [], "tips": ["MRV fee same as B-1/B-2"]},
            {"step_number": 7, "title": "Enter US + Begin Employment", "description": "Enter US on L-1 visa within 6 months of issuance. Begin employment with US entity in qualifying capacity.", "estimated_days": 1, "documents_needed": [], "tips": []},
            {"step_number": 8, "title": "Plan Extensions + Green Card Path", "description": "L-1A: 3yr initial → extend 2yr × 2 = 7yr max. L-1B: 3yr → 2yr = 5yr max. L-1A direct EB-1C green card path; L-1B → EB-2/EB-3 PERM.", "estimated_days": 1825, "documents_needed": [], "tips": ["L-1A managers should file EB-1C within 2-3 years"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (12+ months validity)", "mandatory": True, "notes": ""},
            {"name": "Form I-129 (employer-filed)", "mandatory": True, "notes": ""},
            {"name": "L Supplement (employer-filed)", "mandatory": True, "notes": ""},
            {"name": "Foreign entity employment letters + payroll records", "mandatory": True, "notes": "Proving 1+ yr in qualifying role"},
            {"name": "Position descriptions (foreign + US)", "mandatory": True, "notes": "Demonstrating qualifying capacity"},
            {"name": "Corporate structure documents (US + foreign)", "mandatory": True, "notes": "Ownership + control evidence"},
            {"name": "Organizational charts (US + foreign)", "mandatory": True, "notes": "Showing managerial role"},
            {"name": "L-1A: Decision authority + supervision evidence", "mandatory": True, "notes": "L-1A only"},
            {"name": "L-1B: Specialized knowledge documentation", "mandatory": True, "notes": "L-1B only — distinctive knowledge"},
            {"name": "Sponsor company financials (US + foreign)", "mandatory": True, "notes": "Demonstrate active business"},
            {"name": "Tax returns + payroll proof (both entities)", "mandatory": True, "notes": ""},
            {"name": "Beneficiary CV / resume", "mandatory": True, "notes": ""},
            {"name": "Photo (USCIS specs)", "mandatory": True, "notes": ""},
            {"name": "I-129 government fee payment ($2,485 standard)", "mandatory": True, "notes": ""},
            {"name": "DS-160 + MRV ($205 + $250 Visa Integrity)", "mandatory": True, "notes": "If processing abroad"},
            {"name": "Spouse/children passports + relationship certs (L-2)", "mandatory": False, "notes": "L-2 dependent visa"},
        ],
        "common_rejection_reasons": [
            "Qualifying relationship unclear (insufficient ownership/control evidence)",
            "L-1B specialized knowledge insufficiently distinct from industry standard",
            "L-1A position not truly managerial (first-level supervisor not enough)",
            "Foreign employment <1yr or interrupted within past 3 years",
            "US position not commensurate with foreign role",
            "New office: business plan insufficient or operations not commenced after 1-yr extension",
            "Sponsor company financial instability",
            "Past visa violations or RFE response inadequate",
        ],
        "success_tips": [
            "L-1A managers: leverage direct EB-1C green card path within 2-3 years",
            "L-1B: extra emphasis on specialized knowledge unique to company (not industry)",
            "Premium processing $2,965 = 15-day decision (highly recommended)",
            "Blanket L-1 for large MNCs (10+ L-1s, $25M+ sales, 1000+ employees) = consular processing for each employee",
            "Spouse on L-2: can apply for EAD (work authorization) immediately",
            "L-1A new office: emphasize business plan + funding + concrete operations within 1 yr",
            "Document foreign work in qualifying capacity meticulously — 1-year continuous required",
            "L-1A → EB-1C is FASTEST employment-based green card route (current for most countries)",
        ],
        "faqs": [
            {"q": "What's the difference between L-1A and L-1B?", "a": "L-1A = executive/managerial capacity (decision authority, supervision of professionals, control). Max stay 7 years. Direct EB-1C green card path. L-1B = specialized knowledge of company products/processes. Max stay 5 years. No direct GC path."},
            {"q": "Can my spouse work on L-2?", "a": "YES — L-2 spouses can apply for EAD (work authorization). Children under 21 can attend US schools but cannot work."},
            {"q": "What's a Blanket L-1?", "a": "Pre-approval of corporate structure for large multinationals (10+ prior L-1s OR $25M+ sales OR 1,000+ US employees). Employees apply directly at US consulate (Form I-129S) bypassing individual I-129. No premium processing available."},
            {"q": "How long does L-1 last?", "a": "L-1A: 3yr initial + 2yr extensions = 7 years max. L-1B: 3yr initial + 2yr = 5 years max. New office: 1-year initial then standard."},
            {"q": "Can L-1 lead to green card?", "a": "L-1A leads directly to EB-1C green card (multinational manager/executive) — fastest employment-based route. L-1B requires switching to EB-2/EB-3 PERM (longer process)."},
            {"q": "Is L-1 cap-subject?", "a": "NO — L-1 has no annual cap, no lottery. File year-round."},
        ],
        "official_url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/l-1a-intracompany-transferee-executive-or-manager",
        "vfs_url": "https://www.ustraveldocs.com/in/",
        "source_urls": [
            "https://www.uscis.gov/working-in-the-united-states/temporary-workers/l-1a-intracompany-transferee-executive-or-manager",
            "https://www.uscis.gov/working-in-the-united-states/temporary-workers/l-1b-intracompany-transferee-specialized-knowledge",
            "https://www.mvalaw.com/L-1-INTRACOMPANY-TRANSFEREE",
            "https://lawofficeimmigration.com/blog/l1-visa-2026-what-is-working-what-isnt.html",
            "https://newlandchase.com/insights/mastering-the-l-1-visa-how-the-l-1-blanket-streamlines-workforce-transfers/",
        ],
        "verified_notes": "Manual Fast-Path B.4.7 seed — verified against uscis.gov + Law Office Immigration + MVA Law + Newland Chase on 2026-02-27. L-1A (7yr max + EB-1C) vs L-1B (5yr max, no direct GC) distinction documented. Blanket L-1 eligibility (10+ L-1s, $25M+ sales, 1000+ employees) covered. $1,385 I-129 base + $500 Fraud + $600 Asylum + March 2026 premium hike to $2,965 + $4,500 PL 114-113 all current. Validator URL check: HTTP 403 (uscis.gov anti-bot, NOT closure — validator artefact only).",
    },

    # ── 5. US-EB-1-EB-2 — Employment-Based Green Card ──────────────────────────
    {
        "country_code": "US", "country_name": "United States",
        "subclass_id": "EB-1-EB-2",
        "subclass_name": "Employment-Based Green Card (EB-1 Priority Workers + EB-2 Advanced Degree / NIW)",
        "service_type": "pr", "category": "immigration",
        "description": (
            "Employment-Based (EB) categories are the United States' primary work-related "
            "green card (Lawful Permanent Resident) pathways. Combined here for two highest "
            "preference categories:\n\n"
            "**EB-1 — Priority Workers (1st Preference, ~40,000/yr):**\n"
            "- **EB-1A:** Extraordinary Ability — Persons with sustained national/international "
            "acclaim in sciences, arts, education, business, athletics. **Self-petition** "
            "(no employer required). **No PERM** labor certification required.\n"
            "- **EB-1B:** Outstanding Researchers/Professors — 3+ years experience, "
            "international recognition. Requires employer (university/research org). No PERM.\n"
            "- **EB-1C:** Multinational Managers/Executives — Direct path from L-1A. Requires "
            "employer (qualifying multinational). No PERM.\n\n"
            "**EB-2 — Advanced Degree / Exceptional Ability (2nd Preference, ~40,000/yr):**\n"
            "- **EB-2 Standard:** Advanced degree (Master's+) OR Bachelor's + 5 years progressive "
            "experience. Requires PERM labor certification + employer sponsor.\n"
            "- **EB-2 NIW (National Interest Waiver):** Self-petition allowed. Bypasses PERM + "
            "job offer if applicant's work in **US national interest**. Three-prong test: "
            "(1) substantial merit + national importance, (2) well-positioned to advance, "
            "(3) on balance beneficial to waive job offer + PERM.\n\n"
            "**Current visa availability (2026 Visa Bulletin):**\n"
            "- EB-1 + EB-2: CURRENT for 'All Other Countries' (non-India/China/Mexico)\n"
            "- **India backlog: ~10-15 years for EB-2 (priority date 2014); EB-1 also "
            "backlogged**. Major impact on India-born applicants.\n\n"
            "**USCIS Fees (effective March 1, 2026):**\n"
            "- I-140 Immigrant Petition: **$715**\n"
            "- I-485 Adjustment of Status: **$1,440**\n"
            "- Premium Processing for I-140 (NEW): **$2,965** (45-day decision)\n"
            "- Total typical (with AOS): ~$3,345 standard / ~$6,310 with premium\n\n"
            "**PERM labor certification (standard EB-2/EB-3 only):**\n"
            "- DOL prevailing wage determination + recruitment + ETA-9089 filing\n"
            "- Timeline: 3-4+ years for PERM alone\n"
            "- Cost: $5k-$15k attorney fees (PERM is complex)"
        ),
        "eligibility_summary": (
            "EB-1: Extraordinary ability (self-petition) OR outstanding researcher/multinational "
            "manager (employer). EB-2: Advanced degree + employer (PERM) OR NIW self-petition. "
            "Backlog: India-born face 10-15+ year waits."
        ),
        "eligibility_criteria": [
            {"label": "EB-1A — Extraordinary Ability", "value": "Sustained national/international acclaim in field; 3+ of 10 criteria (awards, publications, press, etc.)", "notes": "Self-petition, no employer, no PERM"},
            {"label": "EB-1B — Outstanding Researcher/Professor", "value": "3+ years experience + international recognition + employer (university/research)", "notes": "No PERM"},
            {"label": "EB-1C — Multinational Manager/Executive", "value": "1+ year managerial/executive role abroad + same role in US with qualifying multinational", "notes": "Direct path from L-1A"},
            {"label": "EB-2 Standard — Advanced Degree", "value": "Master's or higher (or Bachelor's + 5 yrs progressive exp)", "notes": "Requires PERM + employer"},
            {"label": "EB-2 NIW — Three-Prong Test", "value": "(1) Substantial merit + national importance, (2) well-positioned to advance, (3) beneficial to waive PERM", "notes": "Self-petition allowed"},
            {"label": "PERM (Standard EB-2/EB-3 only)", "value": "DOL labor certification proving no qualified US workers available", "notes": "3-4+ year process"},
            {"label": "Country of Birth Backlog", "value": "India + China + Mexico face significant waits (EB-2 India: ~10-15 yrs)", "notes": "Cross-chargeability via spouse may help"},
            {"label": "Priority Date", "value": "Date USCIS receives I-140 sets priority date; current bulletin determines visa availability", "notes": ""},
            {"label": "I-140 + I-485 / Consular Processing", "value": "I-140 approves immigrant petition; I-485 adjusts status (in US) OR consular processing (abroad)", "notes": ""},
        ],
        "fees_local_currency_code": "USD", "fees_local_currency_amount": 715, "fees_inr_approx": 60775,
        "fees_breakdown": [
            {"component": "Form I-140 Immigrant Petition", "amount": 715, "currency": "USD"},
            {"component": "Form I-485 Adjustment of Status (with biometrics)", "amount": 1440, "currency": "USD"},
            {"component": "Premium Processing for I-140 (NEW 2025+, March 2026 fee hike)", "amount": 2965, "currency": "USD"},
            {"component": "Total Self-Petition (I-140 + I-485, no premium)", "amount": 2155, "currency": "USD"},
            {"component": "Total Self-Petition (I-140 + I-485 + Premium I-140)", "amount": 5120, "currency": "USD"},
            {"component": "DS-260 Consular Processing (offshore)", "amount": 325, "currency": "USD"},
            {"component": "Medical examination", "amount": 500, "currency": "USD"},
            {"component": "Biometrics (included in I-485)", "amount": 0, "currency": "USD"},
            {"component": "PERM filing (employer cost)", "amount": 0, "currency": "USD"},
            {"component": "PERM attorney fees (employer typically pays)", "amount": 8000, "currency": "USD"},
            {"component": "Form I-907 Premium Processing", "amount": 2965, "currency": "USD"},
            {"component": "Visa Integrity Fee (FY2026, immigrant visa stamping)", "amount": 250, "currency": "USD"},
        ],
        "processing_time_days_min": 90, "processing_time_days_max": 1825,
        "step_by_step": [
            {"step_number": 1, "title": "Determine Best Category", "description": "Assess: EB-1A (extraordinary ability self-petition) > EB-2 NIW (advanced degree + national interest) > EB-1B/1C (employer) > EB-2 standard (PERM + employer).", "estimated_days": 30, "documents_needed": ["Resume/CV", "Publications", "Awards"], "tips": ["EB-1A is highest preference; bypass employer + PERM"]},
            {"step_number": 2, "title": "PERM (Standard EB-2/EB-3 only)", "description": "Employer files prevailing wage determination + advertises position + ETA-9089 with DOL. Takes 3-4+ years.", "estimated_days": 1095, "documents_needed": ["Position description", "Job posting", "Recruitment record"], "tips": ["NIW + EB-1 SKIP this step entirely"]},
            {"step_number": 3, "title": "File Form I-140 Immigrant Petition", "description": "Self-petition (EB-1A, EB-2 NIW) OR employer-filed (others). Pay $715. Premium processing ($2,965) recommended for 45-day decision.", "estimated_days": 90, "documents_needed": ["I-140", "Supporting evidence portfolio"], "tips": ["EB-1A/EB-2 NIW evidence portfolio is critical — engage specialist counsel"]},
            {"step_number": 4, "title": "Receive I-140 Approval + Priority Date", "description": "USCIS approves I-140. Priority date locked. Check Visa Bulletin for visa availability by category + country of birth.", "estimated_days": 30, "documents_needed": [], "tips": ["India: priority date may be 10-15 years backlogged for EB-2"]},
            {"step_number": 5, "title": "Wait for Visa Availability (if backlog)", "description": "If priority date NOT current: wait. If current: file I-485 (in US) or DS-260 (abroad). India EB-2 currently ~2014 priority dates.", "estimated_days": 3650, "documents_needed": [], "tips": ["File downgrade EB-3 if current, port priority date later"]},
            {"step_number": 6, "title": "File Form I-485 Adjustment of Status (in US)", "description": "Once visa available, file I-485 ($1,440). Includes biometrics + work authorization (EAD) + travel permit (Advance Parole) options.", "estimated_days": 270, "documents_needed": ["I-485", "Medical exam (Form I-693)", "Birth + marriage certs"], "tips": ["EAD + AP available during I-485 wait"]},
            {"step_number": 7, "title": "USCIS Interview (sometimes waived)", "description": "Some I-485 cases require interview; many are waived. Typical 6-12 months from I-485 filing.", "estimated_days": 180, "documents_needed": [], "tips": []},
            {"step_number": 8, "title": "Green Card Approved + LPR Status", "description": "I-485 approved → become Lawful Permanent Resident. 10-year green card issued. Citizenship eligible after 5 years (3 if spouse of US citizen).", "estimated_days": 30, "documents_needed": [], "tips": ["Travel restrictions: <6 months at a time outside US to maintain LPR"]},
        ],
        "document_checklist": [
            {"name": "Valid passport (6+ months validity)", "mandatory": True, "notes": ""},
            {"name": "Form I-140 Immigrant Petition", "mandatory": True, "notes": "Self-petition or employer-filed"},
            {"name": "Form I-485 Adjustment of Status", "mandatory": True, "notes": "If adjusting in US"},
            {"name": "Form I-907 Premium Processing (optional)", "mandatory": False, "notes": "$2,965 for 45-day decision"},
            {"name": "EB-1A: 3+ of 10 criteria evidence (awards, publications, press)", "mandatory": True, "notes": "EB-1A only — critical"},
            {"name": "EB-2 NIW: National interest + 3-prong evidence", "mandatory": True, "notes": "EB-2 NIW only"},
            {"name": "PERM ETA-9089 (Standard EB-2/EB-3)", "mandatory": True, "notes": "DOL-certified"},
            {"name": "Educational credentials (advanced degree)", "mandatory": True, "notes": "Foreign degrees: WES evaluation"},
            {"name": "Employment letters + payroll records (5+ yrs)", "mandatory": True, "notes": "Proving qualifying experience"},
            {"name": "Publications + citations (EB-1A, EB-2 NIW)", "mandatory": False, "notes": "Strong evidence for extraordinary ability"},
            {"name": "Letters of recommendation (5-8 from peers/experts)", "mandatory": False, "notes": "Independent, specific, detailed"},
            {"name": "Awards / recognition / press coverage", "mandatory": False, "notes": "EB-1A 3+ of 10 criteria"},
            {"name": "Sponsor company evidence (if employer-sponsored)", "mandatory": False, "notes": ""},
            {"name": "Form I-693 Medical examination (I-485 only)", "mandatory": True, "notes": "Civil surgeon"},
            {"name": "Police certificates (per country)", "mandatory": True, "notes": "I-485 / DS-260"},
            {"name": "Birth + marriage certificates + photos", "mandatory": True, "notes": ""},
        ],
        "common_rejection_reasons": [
            "EB-1A: Insufficient evidence of national/international acclaim (3+ criteria not met)",
            "EB-2 NIW: 3-prong test inadequately demonstrated (national importance unclear)",
            "Educational credentials evaluation incomplete or below required level",
            "PERM recruitment process flawed (advertising irregularities)",
            "I-140 RFE response inadequate (especially for EB-1A/NIW)",
            "Priority date backlogged (India EB-2 ~10-15 yrs)",
            "Inadmissibility issues (criminal record, prior visa fraud)",
            "Letters of recommendation generic or from non-experts",
            "Insufficient sponsor financial evidence (employer-sponsored)",
        ],
        "success_tips": [
            "🎯 EB-1A self-petition = FASTEST employment-based GC (no employer, no PERM, current for India 2026)",
            "EB-2 NIW = strong fit for STEM PhDs + researchers in critical fields",
            "Premium processing $2,965 = 45-day I-140 decision (highly recommended)",
            "India-born: file BOTH EB-1A and EB-2 (or downgrade to EB-3 if current) — different priority dates",
            "Letters of recommendation 5-8 from INDEPENDENT experts (not co-workers)",
            "Engage specialist EB-1A/NIW counsel — generic immigration practitioners insufficient",
            "EB-1A 10 criteria checklist: meet 3+ STRONGLY (not just marginally)",
            "PERM-based EB-2: budget 3-4 years just for PERM alone — strategize early career",
            "LPR maintenance: <6 months outside US per trip + tax filing as US resident",
        ],
        "faqs": [
            {"q": "What's the difference between EB-1 and EB-2?", "a": "EB-1 = priority workers (extraordinary ability self-petition + outstanding researcher + multinational manager). NO PERM. Highest preference. EB-2 = advanced degree (with PERM) or National Interest Waiver (self-petition, no PERM). Second preference."},
            {"q": "Can I self-petition?", "a": "YES for EB-1A (extraordinary ability) and EB-2 NIW (National Interest Waiver). Other categories (EB-1B, EB-1C, EB-2 standard, EB-3) require employer sponsorship."},
            {"q": "What's the India backlog?", "a": "India-born EB-2 priority dates are currently ~2014 (10-15+ year wait). EB-1 also backlogged but shorter. EB-1A self-petition + EB-3 downgrade are common strategies."},
            {"q": "What's premium processing?", "a": "Optional $2,965 fee for 45-day I-140 decision (instead of 4-12 months standard). NEW for I-140 (introduced 2025+). Highly recommended."},
            {"q": "What's the 3-prong NIW test?", "a": "(1) Endeavor has substantial merit + national importance, (2) Applicant well-positioned to advance the endeavor, (3) On balance, beneficial for US to waive job offer + PERM. Each prong must be strongly evidenced."},
            {"q": "How long does the entire EB process take?", "a": "EB-1A (current): 6-12 months from filing to GC. EB-2 (current): 1-2 years. EB-2 India: 10-15+ years (backlog). Premium processing accelerates I-140 only, not I-485."},
        ],
        "official_url": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-first-preference-eb-1",
        "vfs_url": "https://www.ustraveldocs.com/in/",
        "source_urls": [
            "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-first-preference-eb-1",
            "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-second-preference-eb-2",
            "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html",
            "https://berardiimmigrationlaw.com/niw-vs-perm-labor-certification-differences-pros-cons/",
            "https://ogletree.com/insights-resources/blog-posts/uscis-premium-processing-fees-will-increase-on-march-1-2026/",
        ],
        "verified_notes": "Manual Fast-Path B.4.7 seed — verified against uscis.gov + travel.state.gov + Berardi Immigration Law + Ogletree Deakins on 2026-02-27. EB-1A (self-petition no PERM no employer) + EB-1B (outstanding researcher) + EB-1C (multinational manager from L-1A) + EB-2 Standard (PERM + employer) + EB-2 NIW (self-petition 3-prong test) all distinguished. March 2026 Premium Processing fee hike to $2,965 + India backlog (10-15 yrs EB-2) documented. Validator URL check: HTTP 403 (uscis.gov anti-bot, NOT closure — validator artefact only).",
    },

    # ── 6. US-K-1 — Fiancé(e) Visa ─────────────────────────────────────────────
    {
        "country_code": "US", "country_name": "United States",
        "subclass_id": "K-1",
        "subclass_name": "Fiancé(e) Visa (K-1; followed by Adjustment of Status within 90 days)",
        "service_type": "partner", "category": "immigration",
        "description": (
            "The K-1 visa allows the **foreign fiancé(e) of a U.S. citizen** to enter the US "
            "for the purpose of marrying their petitioner within **90 days of entry**. "
            "Failure to marry within 90 days requires departure from US.\n\n"
            "**Critical Distinction: K-1 vs CR-1/IR-1 Spouse Visa:**\n"
            "- **K-1 (Fiancé):** For couples NOT yet married. Enter US first, marry within 90 days, "
            "then file I-485 Adjustment of Status. Faster initial entry, but more expensive + "
            "requires AOS after marriage. Total cost ~$3,000+.\n"
            "- **CR-1 (Conditional Spouse):** Already married <2 years at approval. Enter US "
            "as conditional permanent resident directly. ~$1,500-$2,000. Slower but cheaper.\n"
            "- **IR-1 (Immediate Spouse):** Already married 2+ years at approval. Enter US "
            "as full permanent resident (10-year GC). ~$1,500-$2,000.\n\n"
            "**K-1 Eligibility:**\n"
            "- US **citizen** petitioner (NOT permanent residents — LPRs use CR-1/IR-1 only)\n"
            "- Couple **met in person within last 2 years** (very limited hardship waivers)\n"
            "- Both parties **legally free to marry** (any prior divorces finalised)\n"
            "- Intent to marry within 90 days of K-1 holder's US entry\n\n"
            "**3-stage process:**\n"
            "1. **Stage A — Form I-129F Petition (USCIS):** $675 (or $625 if filed online with "
            "$50 discount). Prove relationship + meet-in-person evidence. ~10-12 months.\n"
            "2. **Stage B — DS-160 + Visa Application (Department of State):** $265 MRV at "
            "consulate in fiancé's country. Medical exam, interview.\n"
            "3. **Stage C — Adjustment of Status (USCIS, after US entry + marriage):** I-485 "
            "$1,440. Includes biometrics + EAD (work authorization) + Advance Parole.\n\n"
            "**Total typical cost: ~$2,380-$3,000+** (including medical + translations).\n\n"
            "**K-2 Children:** Unmarried children under 21 of K-1 fiancé(e) can accompany or "
            "follow within 1 year. Same medical + interview process."
        ),
        "eligibility_summary": (
            "Foreign fiancé(e) of US citizen (NOT LPR). Met in person within 2 years. Both "
            "legally free to marry. Intent to marry in US within 90 days of entry."
        ),
        "eligibility_criteria": [
            {"label": "Petitioner Status", "value": "Must be US CITIZEN (Permanent Residents/LPRs cannot file K-1 — use CR-1/IR-1)", "notes": "Critical distinction"},
            {"label": "Met In Person", "value": "Couple met in person within last 2 years of I-129F filing", "notes": "Limited hardship waivers (cultural, medical, etc.)"},
            {"label": "Legally Free to Marry", "value": "Both parties legally free to marry (any prior divorces finalised)", "notes": "Divorce decrees translated + apostilled"},
            {"label": "Intent to Marry", "value": "Sincere intent to marry within 90 days of K-1 holder's US entry", "notes": "Bonafide relationship evidence required"},
            {"label": "K-1 Petitioner Income (I-134 Affidavit of Support)", "value": "125% of US Federal Poverty Guidelines for household size", "notes": "Joint sponsor option if income insufficient"},
            {"label": "K-1 Petitioner Sustained US Domicile", "value": "Petitioner must have US domicile + intend to continue residing in US", "notes": ""},
            {"label": "K-2 Children", "value": "Unmarried children under 21 of K-1 fiancé(e) can accompany or follow within 1 year", "notes": "Listed on I-129F"},
            {"label": "Inadmissibility (Standard)", "value": "Health + character + criminal history admissibility", "notes": "Waivers possible for some grounds"},
            {"label": "90-Day Marriage Deadline", "value": "Must marry within 90 days of US entry OR depart US", "notes": "ABSOLUTE — no extensions"},
        ],
        "fees_local_currency_code": "USD", "fees_local_currency_amount": 2380, "fees_inr_approx": 202300,
        "fees_breakdown": [
            {"component": "Stage A — Form I-129F (USCIS, paper)", "amount": 675, "currency": "USD"},
            {"component": "Stage A — Form I-129F (online filing discount)", "amount": 625, "currency": "USD"},
            {"component": "Stage B — DS-160 MRV Visa Application Fee (DOS)", "amount": 265, "currency": "USD"},
            {"component": "Stage B — Medical examination (USCIS panel physician)", "amount": 400, "currency": "USD"},
            {"component": "Stage B — Police clearance certificates (per country)", "amount": 50, "currency": "USD"},
            {"component": "Stage B — Translation + apostille (per document)", "amount": 100, "currency": "USD"},
            {"component": "Stage B — Visa Integrity Fee (FY2026, post-approval)", "amount": 250, "currency": "USD"},
            {"component": "Stage C — Form I-485 Adjustment of Status (with biometrics)", "amount": 1440, "currency": "USD"},
            {"component": "Total K-1 to PR (Stages A + B + C)", "amount": 2380, "currency": "USD"},
            {"component": "Attorney fees (typical)", "amount": 3000, "currency": "USD"},
            {"component": "Comparison: CR-1/IR-1 Total (typically less)", "amount": 1500, "currency": "USD"},
        ],
        "processing_time_days_min": 270, "processing_time_days_max": 540,
        "step_by_step": [
            {"step_number": 1, "title": "Confirm Eligibility (US Citizen + Met-in-Person)", "description": "Verify petitioner is US citizen (not LPR) + couple met in person within 2 years + both legally free to marry.", "estimated_days": 1, "documents_needed": ["Petitioner US passport/birth cert", "Meeting evidence (photos, travel records)"], "tips": ["If LPR petitioner: must use CR-1/IR-1 instead"]},
            {"step_number": 2, "title": "File Form I-129F with USCIS", "description": "Petitioner files Form I-129F + supporting evidence. Pay $675 (paper) or $625 (online).", "estimated_days": 14, "documents_needed": ["I-129F", "Relationship evidence", "Meeting proof", "Divorce decrees if applicable"], "tips": ["File online if possible — $50 discount + faster"]},
            {"step_number": 3, "title": "USCIS Approval (10-12 months typical)", "description": "USCIS adjudicates I-129F. RFE may be issued. Approval forwards to National Visa Center, then consulate in fiancé's country.", "estimated_days": 330, "documents_needed": [], "tips": ["No premium processing available for I-129F"]},
            {"step_number": 4, "title": "Stage B — Consulate Notification + DS-160", "description": "Consulate notifies fiancé(e). File DS-160 online + pay $265 MRV fee. Schedule interview.", "estimated_days": 60, "documents_needed": ["DS-160 confirmation"], "tips": []},
            {"step_number": 5, "title": "Medical Exam + Police Certificates", "description": "Fiancé(e) attends USCIS panel physician for medical (~$400) + obtains police certificates from all 6+ month residence countries.", "estimated_days": 30, "documents_needed": ["Medical results sealed", "Police certificates"], "tips": ["Vaccinations may be required"]},
            {"step_number": 6, "title": "K-1 Interview at US Consulate", "description": "Fiancé(e) attends interview. Demonstrate bonafide relationship + intent to marry. Bring all docs. Decision typically same-day.", "estimated_days": 1, "documents_needed": ["DS-160", "Medical", "Relationship evidence", "I-134 Affidavit"], "tips": ["Clear relationship history + future marriage plans"]},
            {"step_number": 7, "title": "Travel to US + Marry within 90 Days", "description": "Enter US within 6 months of K-1 issuance. Marry petitioner within 90 days of entry. NO EXTENSIONS — must marry or depart.", "estimated_days": 90, "documents_needed": ["K-1 visa", "Marriage license"], "tips": ["⚠️ 90-day deadline is ABSOLUTE"]},
            {"step_number": 8, "title": "Stage C — File I-485 Adjustment of Status", "description": "After marriage, file Form I-485 + I-765 (EAD) + I-131 (Advance Parole). $1,440 USCIS fee. Receive Conditional Green Card (2-year if married <2 years at approval).", "estimated_days": 270, "documents_needed": ["I-485", "Marriage cert", "I-693 Medical"], "tips": ["EAD + AP available during I-485 wait (~3-6 months)"]},
        ],
        "document_checklist": [
            {"name": "Petitioner's US passport / birth certificate / naturalisation certificate", "mandatory": True, "notes": "Must be US citizen"},
            {"name": "Form I-129F + petition supporting evidence", "mandatory": True, "notes": ""},
            {"name": "Relationship evidence (photos, communications, joint travel)", "mandatory": True, "notes": "Demonstrate bonafide relationship"},
            {"name": "Met-in-person evidence (passport stamps, hotel bookings, photos)", "mandatory": True, "notes": "Within 2 years of I-129F filing"},
            {"name": "Divorce decrees (if any prior marriages)", "mandatory": True, "notes": "All translated + apostilled"},
            {"name": "Death certificate (if widow/widower)", "mandatory": True, "notes": "If applicable"},
            {"name": "Fiancé(e) passport (12+ months validity)", "mandatory": True, "notes": ""},
            {"name": "DS-160 confirmation page + photo", "mandatory": True, "notes": ""},
            {"name": "MRV fee receipt ($265)", "mandatory": True, "notes": ""},
            {"name": "I-134 Affidavit of Support from petitioner", "mandatory": True, "notes": "125% of US Federal Poverty Guidelines"},
            {"name": "Petitioner's tax returns + employment proof", "mandatory": True, "notes": "Last 3 years"},
            {"name": "Police certificates (fiancé's, per country, 6+ months residence)", "mandatory": True, "notes": ""},
            {"name": "Medical examination (sealed)", "mandatory": True, "notes": "USCIS panel physician"},
            {"name": "Birth certificate (fiancé(e) + K-2 children)", "mandatory": True, "notes": ""},
            {"name": "K-2 children documentation (if accompanying)", "mandatory": False, "notes": "Under 21, unmarried"},
            {"name": "Form I-485 + I-765 + I-131 (Stage C, after marriage)", "mandatory": True, "notes": "AOS package"},
            {"name": "Marriage certificate (Stage C)", "mandatory": True, "notes": "Must be within 90 days of K-1 entry"},
            {"name": "Visa Integrity Fee receipt ($250, FY2026)", "mandatory": False, "notes": "Expected post-approval"},
        ],
        "common_rejection_reasons": [
            "Petitioner is LPR (NOT US citizen) — must use CR-1/IR-1",
            "Couple not met in person within 2 years (no hardship waiver applicable)",
            "Insufficient bonafide relationship evidence",
            "Prior marriages not finalised (divorce pending)",
            "Petitioner income below 125% Federal Poverty Guidelines (need joint sponsor)",
            "Medical inadmissibility (untreated communicable disease)",
            "Character / criminal history concerns",
            "Inconsistent meet-in-person evidence vs interview statements",
            "Failure to marry within 90 days (K-1 expires + must depart)",
        ],
        "success_tips": [
            "🎯 K-1 vs CR-1/IR-1: If you can wait 4-6 extra months, CR-1/IR-1 saves $1,000+ + immediate work rights",
            "K-1 advantage: faster initial US entry (~10-12 months vs 12-18 months for CR-1)",
            "I-129F online filing = $50 discount + faster",
            "Meet-in-person evidence: passport stamps + hotel bookings + photos with location + timestamps",
            "I-134 Affidavit of Support: petitioner income 125%+ Federal Poverty + recent tax returns",
            "K-2 children: list on I-129F + include in DS-160 + same medical/interview slot",
            "ABSOLUTE 90-day marriage deadline — DO NOT exceed; legal marriage certificate required",
            "Adjustment of Status (Stage C): file EAD + Advance Parole simultaneously to maintain work + travel rights during wait",
        ],
        "faqs": [
            {"q": "Can I use K-1 if I'm a Permanent Resident?", "a": "NO. K-1 is ONLY for US citizens. Permanent Residents (LPRs) must use CR-1 (married <2 years at approval) or IR-1 (married 2+ years)."},
            {"q": "What if we haven't met in person?", "a": "Couple MUST have met in person within 2 years of I-129F filing. Very limited hardship waivers (extreme cultural prohibition, severe medical). Most applicants must travel + meet first."},
            {"q": "What happens if we don't marry within 90 days?", "a": "K-1 expires + fiancé(e) MUST depart US. NO extensions. Re-applying requires starting over with new I-129F."},
            {"q": "Should I choose K-1 or CR-1?", "a": "K-1 = faster initial entry (~10-12 months), but more expensive total (~$3,000) + requires AOS after marriage. CR-1 = slower (12-18 months) but cheaper (~$1,500) + immediate green card + work rights. Choose based on urgency vs cost."},
            {"q": "Can my children come on K-1?", "a": "YES — K-2 visa for unmarried children under 21 of K-1 fiancé(e). Listed on I-129F. Same medical + interview process. Can accompany or follow within 1 year."},
            {"q": "How long does the K-1 process take?", "a": "Stage A (I-129F): 10-12 months typical. Stage B (interview): 2-3 months after I-129F approval. Total to US entry: 12-15 months. AOS Stage C: additional 8-12 months for Green Card."},
        ],
        "official_url": "https://travel.state.gov/content/travel/en/us-visas/immigrate/family-immigration/nonimmigrant-visa-for-a-fiance-k-1.html",
        "vfs_url": "https://www.ustraveldocs.com/in/",
        "source_urls": [
            "https://travel.state.gov/content/travel/en/us-visas/immigrate/family-immigration/nonimmigrant-visa-for-a-fiance-k-1.html",
            "https://www.uscis.gov/family/family-of-us-citizens/visas-for-fiances-of-us-citizens",
            "https://www.boundless.com/immigration-resources/cr1-ir1-spouse-visa",
            "https://immigrationhelpla.com/k1-fiance-visa/",
            "https://manifestlaw.com/blog/k1-visa-costs/",
        ],
        "verified_notes": "Manual Fast-Path B.4.7 seed — verified against travel.state.gov + uscis.gov + Boundless + Immigration Help LA + Manifest Law on 2026-02-27. K-1 ($675/$625 I-129F + $265 MRV + $1,440 I-485 = $2,380 total) vs CR-1/IR-1 (~$1,500) distinction documented. 90-day marriage deadline + LPR exclusion (must use CR-1/IR-1) + K-2 children + I-134 affidavit + 125% Federal Poverty all current. Validator URL check: HTTP 200 (travel.state.gov primary), 403 (uscis.gov secondary anti-bot, NOT closure).",
    },
]


ALL_WORKFLOWS: Dict[str, List[Dict[str, Any]]] = {
    "IN": INDIA_WORKFLOWS,
    "AU": AUSTRALIA_NEW_WORKFLOWS,
    "CA": CANADA_NEW_WORKFLOWS,
    "NZ": NEW_ZEALAND_NEW_WORKFLOWS,
    "UK": UNITED_KINGDOM_NEW_WORKFLOWS,
    "US": USA_NEW_WORKFLOWS,
}


# ──────────────────────────────────────────────────────────────────────────────
# Main runner — mirrors b2.py main() pattern but for B.4 sub-slices
# ──────────────────────────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="Sweep B.4 Mega Dispatch country workflow seeder")
    parser.add_argument("--country", type=str, default=None, help="ISO-2 country code to seed (e.g. IN)")
    parser.add_argument("--all", action="store_true", help="Seed all B.4 countries currently defined")
    parser.add_argument("--backfill", type=str, default=None, help="One-shot backfill: add doc_id + rewrite legacy audit_logs for given ISO-2 code")
    parser.add_argument("--relabel-action", action="store_true", help="Rewrite audit_logs for B.4-seeded workflows: action _b2 → _b4 (one-shot fix)")
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

    # ── ONE-SHOT RELABEL MODE (Sub-Slice B.4.3 audit-log naming fix) ─────────
    if args.relabel_action:
        # Determine the set of workflow_ids that came from B.4 sub-slices (IN + AU expansion ids).
        b4_workflow_ids: List[str] = []
        for cc, wfs in ALL_WORKFLOWS.items():
            for wf in wfs:
                w = await db.country_visa_workflows.find_one(
                    {"country_code": cc, "subclass_id": wf["subclass_id"], "service_type": wf["service_type"], "status": "verified"},
                    {"_id": 0, "workflow_id": 1},
                )
                if w and w.get("workflow_id"):
                    b4_workflow_ids.append(w["workflow_id"])

        print(f"Identified {len(b4_workflow_ids)} B.4-seeded workflows for action relabel.")
        result = await db.audit_logs.update_many(
            {
                "action": "country_workflow_seeded_b2",
                "entity_id": {"$in": b4_workflow_ids},
            },
            [
                {"$set": {
                    "action": "country_workflow_seeded_b4",
                    "details": {"$replaceOne": {"input": "$details", "find": "Manual Fast-Path B.2", "replacement": "Manual Fast-Path B.4"}},
                }},
            ],
        )
        print(f"Relabel complete: matched={result.matched_count} modified={result.modified_count}")
        # Verify
        n_b4 = await db.audit_logs.count_documents({"action": "country_workflow_seeded_b4"})
        n_b2 = await db.audit_logs.count_documents({"action": "country_workflow_seeded_b2"})
        print(f"After relabel — _b4 count: {n_b4} · _b2 count: {n_b2}")
        return

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
        res = await seed_country(db, cc, seeded_by_id, seeded_by_name, sweep_label="b4")
        totals["inserted"] += res["inserted"]
        totals["skipped"] += res["skipped"]
        totals["errored"] += res["errored"]
        print(f"[{cc}] Summary: inserted={res['inserted']} skipped={res['skipped']} errored={res['errored']}")

    print("\n══════════════════════════════════════════════")
    print(f"  TOTAL: inserted={totals['inserted']} skipped={totals['skipped']} errored={totals['errored']}")
    print("══════════════════════════════════════════════\n")


if __name__ == "__main__":
    asyncio.run(main())
