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


ALL_WORKFLOWS: Dict[str, List[Dict[str, Any]]] = {
    "IN": INDIA_WORKFLOWS,
    "AU": AUSTRALIA_NEW_WORKFLOWS,
    "CA": CANADA_NEW_WORKFLOWS,
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
