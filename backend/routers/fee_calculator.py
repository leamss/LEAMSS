"""
Automated Government Fee Calculator
-----------------------------------
Real-time visa cost breakdown for immigration destinations.
- Uses official 2025-26 government fees (visa, biometrics, medicals, assessments, priority)
- Live currency conversion via frankfurter.app (free, no API key)
- Cached exchange rates for 1 hour
"""
import os
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
import httpx

from core.auth import get_current_user
from core.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fee-calculator", tags=["Fee Calculator"])

fee_estimates_col = db["fee_estimates"]


# =========================================================================
#  REAL GOVERNMENT FEE DATABASE (2025-26 official rates)
# =========================================================================
# Each entry: fees in native currency. Values sourced from official gov sites.
# Structure:
#   currency, categories: { <category_key>: { name, fees: [{label, amount, mandatory, per_applicant}], processing_days, notes, official_url } }
# =========================================================================

FEE_DATABASE: Dict[str, Dict[str, Any]] = {
    "canada": {
        "name": "Canada",
        "flag": "🇨🇦",
        "currency": "CAD",
        "categories": {
            "express_entry_pr": {
                "name": "Express Entry — Permanent Residence",
                "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/fees/list.html",
                "processing_days": "180-360",
                "fees": [
                    {"label": "Application Processing Fee", "amount": 950, "mandatory": True, "per_applicant": True},
                    {"label": "Right of Permanent Residence Fee (RPRF)", "amount": 575, "mandatory": True, "per_applicant": True, "notes": "Per adult only"},
                    {"label": "Biometrics Fee", "amount": 85, "mandatory": True, "per_applicant": True},
                    {"label": "Biometrics (family max)", "amount": 170, "mandatory": False, "per_applicant": False, "notes": "Cap for family of 2+"},
                    {"label": "Medical Exam (Panel Physician)", "amount": 250, "mandatory": True, "per_applicant": True, "notes": "Approx., varies by clinic"},
                    {"label": "Police Clearance Certificate (PCC)", "amount": 50, "mandatory": True, "per_applicant": True, "notes": "Per country resided"},
                    {"label": "Educational Credential Assessment (ECA)", "amount": 300, "mandatory": True, "per_applicant": True, "notes": "WES/ICAS/IQAS"},
                    {"label": "IELTS/CELPIP Language Test", "amount": 320, "mandatory": True, "per_applicant": True},
                ],
            },
            "study_permit": {
                "name": "Study Permit (Student Visa)",
                "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada.html",
                "processing_days": "30-90",
                "fees": [
                    {"label": "Study Permit Application Fee", "amount": 150, "mandatory": True, "per_applicant": True},
                    {"label": "Biometrics Fee", "amount": 85, "mandatory": True, "per_applicant": True},
                    {"label": "GIC (Guaranteed Investment Certificate)", "amount": 20635, "mandatory": True, "per_applicant": True, "notes": "Required for SDS stream"},
                    {"label": "Medical Exam", "amount": 250, "mandatory": False, "per_applicant": True},
                    {"label": "IELTS/TOEFL", "amount": 320, "mandatory": True, "per_applicant": True},
                ],
            },
            "work_permit": {
                "name": "Work Permit (LMIA-based)",
                "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada.html",
                "processing_days": "60-120",
                "fees": [
                    {"label": "Work Permit Application", "amount": 155, "mandatory": True, "per_applicant": True},
                    {"label": "Open Work Permit Holder Fee", "amount": 100, "mandatory": False, "per_applicant": True},
                    {"label": "Biometrics Fee", "amount": 85, "mandatory": True, "per_applicant": True},
                    {"label": "LMIA Processing (employer)", "amount": 1000, "mandatory": True, "per_applicant": False, "notes": "Paid by employer"},
                    {"label": "Medical Exam", "amount": 250, "mandatory": False, "per_applicant": True},
                ],
            },
            "visitor_visa": {
                "name": "Visitor Visa (TRV)",
                "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada.html",
                "processing_days": "14-60",
                "fees": [
                    {"label": "TRV Application Fee", "amount": 100, "mandatory": True, "per_applicant": True},
                    {"label": "Family TRV Fee (max 5)", "amount": 500, "mandatory": False, "per_applicant": False},
                    {"label": "Biometrics Fee", "amount": 85, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "australia": {
        "name": "Australia",
        "flag": "🇦🇺",
        "currency": "AUD",
        "categories": {
            "skilled_independent_189": {
                "name": "Subclass 189 — Skilled Independent",
                "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189",
                "processing_days": "180-540",
                "fees": [
                    {"label": "Visa Application Charge (main)", "amount": 4940, "mandatory": True, "per_applicant": False},
                    {"label": "Additional Adult Applicant", "amount": 2470, "mandatory": False, "per_applicant": False, "notes": "Per dependent 18+"},
                    {"label": "Additional Child Applicant", "amount": 1235, "mandatory": False, "per_applicant": False, "notes": "Per dependent under 18"},
                    {"label": "Skills Assessment (VETASSESS/ACS/etc.)", "amount": 1200, "mandatory": True, "per_applicant": True},
                    {"label": "IELTS/PTE Academic", "amount": 410, "mandatory": True, "per_applicant": True},
                    {"label": "Medical Exam (Panel Doctor)", "amount": 400, "mandatory": True, "per_applicant": True},
                    {"label": "Police Clearance (AFP + country)", "amount": 100, "mandatory": True, "per_applicant": True},
                ],
            },
            "student_500": {
                "name": "Subclass 500 — Student Visa",
                "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500",
                "processing_days": "30-120",
                "fees": [
                    {"label": "Student Visa Application", "amount": 1600, "mandatory": True, "per_applicant": True},
                    {"label": "Dependent Adult", "amount": 1190, "mandatory": False, "per_applicant": False},
                    {"label": "Dependent Child", "amount": 390, "mandatory": False, "per_applicant": False},
                    {"label": "OSHC (Overseas Student Health Cover)", "amount": 650, "mandatory": True, "per_applicant": True, "notes": "Annual"},
                    {"label": "IELTS/PTE", "amount": 410, "mandatory": True, "per_applicant": True},
                    {"label": "Medical Exam", "amount": 400, "mandatory": True, "per_applicant": True},
                ],
            },
            "work_482": {
                "name": "Subclass 482 — Temporary Skill Shortage",
                "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482",
                "processing_days": "60-180",
                "fees": [
                    {"label": "Visa Application Charge", "amount": 3210, "mandatory": True, "per_applicant": True, "notes": "Medium-term stream"},
                    {"label": "SAF Levy (employer, per yr)", "amount": 1800, "mandatory": True, "per_applicant": False, "notes": "Paid by sponsor"},
                    {"label": "Skills Assessment", "amount": 1200, "mandatory": True, "per_applicant": True},
                    {"label": "Medical Exam", "amount": 400, "mandatory": True, "per_applicant": True},
                ],
            },
            "visitor_600": {
                "name": "Subclass 600 — Visitor Visa",
                "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/visitor-600",
                "processing_days": "14-30",
                "fees": [
                    {"label": "Visitor Visa Application", "amount": 195, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "uk": {
        "name": "United Kingdom",
        "flag": "🇬🇧",
        "currency": "GBP",
        "categories": {
            "skilled_worker": {
                "name": "Skilled Worker Visa",
                "official_url": "https://www.gov.uk/skilled-worker-visa",
                "processing_days": "21-56",
                "fees": [
                    {"label": "Visa Application Fee (3 years)", "amount": 769, "mandatory": True, "per_applicant": True, "notes": "Outside UK, up to 3 yrs"},
                    {"label": "Immigration Health Surcharge (IHS/yr)", "amount": 1035, "mandatory": True, "per_applicant": True, "notes": "Per year of visa"},
                    {"label": "Certificate of Sponsorship (CoS)", "amount": 239, "mandatory": True, "per_applicant": False, "notes": "Employer pays"},
                    {"label": "Immigration Skills Charge (per yr)", "amount": 1000, "mandatory": True, "per_applicant": False, "notes": "Employer pays, medium sponsor"},
                    {"label": "IELTS / English Test", "amount": 195, "mandatory": True, "per_applicant": True},
                    {"label": "TB Test (if required)", "amount": 75, "mandatory": False, "per_applicant": True},
                ],
            },
            "student_visa": {
                "name": "Student Visa",
                "official_url": "https://www.gov.uk/student-visa",
                "processing_days": "21-56",
                "fees": [
                    {"label": "Student Visa Application", "amount": 524, "mandatory": True, "per_applicant": True, "notes": "Outside UK"},
                    {"label": "IHS (per year)", "amount": 776, "mandatory": True, "per_applicant": True, "notes": "Student rate"},
                    {"label": "IELTS/Academic English", "amount": 195, "mandatory": True, "per_applicant": True},
                    {"label": "TB Test", "amount": 75, "mandatory": False, "per_applicant": True},
                ],
            },
            "visitor": {
                "name": "Standard Visitor Visa",
                "official_url": "https://www.gov.uk/standard-visitor",
                "processing_days": "15-30",
                "fees": [
                    {"label": "Visitor Visa (6 months)", "amount": 115, "mandatory": True, "per_applicant": True},
                    {"label": "Priority Service (optional)", "amount": 500, "mandatory": False, "per_applicant": True},
                ],
            },
        },
    },
    "usa": {
        "name": "United States",
        "flag": "🇺🇸",
        "currency": "USD",
        "categories": {
            "h1b": {
                "name": "H-1B Specialty Occupation",
                "official_url": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
                "processing_days": "90-180",
                "fees": [
                    {"label": "H-1B Registration Fee", "amount": 215, "mandatory": True, "per_applicant": True},
                    {"label": "I-129 Base Filing Fee", "amount": 780, "mandatory": True, "per_applicant": False, "notes": "Employer pays"},
                    {"label": "Asylum Program Fee", "amount": 600, "mandatory": True, "per_applicant": False, "notes": "Employer"},
                    {"label": "ACWIA Training Fee", "amount": 1500, "mandatory": True, "per_applicant": False, "notes": "Employer, 26+ workers"},
                    {"label": "Fraud Prevention Fee", "amount": 500, "mandatory": True, "per_applicant": False},
                    {"label": "Premium Processing (optional)", "amount": 2805, "mandatory": False, "per_applicant": False, "notes": "15 business days"},
                    {"label": "Visa Stamping (DS-160)", "amount": 205, "mandatory": True, "per_applicant": True},
                ],
            },
            "f1_student": {
                "name": "F-1 Student Visa",
                "official_url": "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
                "processing_days": "30-120",
                "fees": [
                    {"label": "DS-160 Visa Application", "amount": 185, "mandatory": True, "per_applicant": True},
                    {"label": "SEVIS I-901 Fee", "amount": 350, "mandatory": True, "per_applicant": True},
                    {"label": "TOEFL/IELTS", "amount": 220, "mandatory": True, "per_applicant": True},
                ],
            },
            "eb2_niw": {
                "name": "EB-2 NIW Green Card",
                "official_url": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-second-preference-eb-2",
                "processing_days": "540-1095",
                "fees": [
                    {"label": "I-140 Petition Fee", "amount": 715, "mandatory": True, "per_applicant": True},
                    {"label": "I-485 Adjustment of Status", "amount": 1440, "mandatory": True, "per_applicant": True},
                    {"label": "Biometrics", "amount": 85, "mandatory": True, "per_applicant": True},
                    {"label": "Medical Exam (Civil Surgeon)", "amount": 500, "mandatory": True, "per_applicant": True},
                    {"label": "Premium Processing I-140", "amount": 2805, "mandatory": False, "per_applicant": False},
                ],
            },
            "b1b2_visitor": {
                "name": "B-1/B-2 Visitor Visa",
                "official_url": "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html",
                "processing_days": "14-60",
                "fees": [
                    {"label": "DS-160 Application Fee", "amount": 185, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "new_zealand": {
        "name": "New Zealand",
        "flag": "🇳🇿",
        "currency": "NZD",
        "categories": {
            "skilled_migrant": {
                "name": "Skilled Migrant Category Resident",
                "official_url": "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/skilled-migrant-category-resident-visa",
                "processing_days": "120-365",
                "fees": [
                    {"label": "Resident Visa Application Fee", "amount": 4890, "mandatory": True, "per_applicant": True},
                    {"label": "Immigration Levy", "amount": 420, "mandatory": True, "per_applicant": True},
                    {"label": "Skills Assessment (NZQA)", "amount": 810, "mandatory": True, "per_applicant": True},
                    {"label": "IELTS", "amount": 410, "mandatory": True, "per_applicant": True},
                    {"label": "Medical Exam", "amount": 350, "mandatory": True, "per_applicant": True},
                    {"label": "Police Clearance", "amount": 80, "mandatory": True, "per_applicant": True},
                ],
            },
            "student_visa": {
                "name": "Student Visa",
                "official_url": "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/fee-paying-student-visa",
                "processing_days": "30-90",
                "fees": [
                    {"label": "Student Visa Fee", "amount": 750, "mandatory": True, "per_applicant": True},
                    {"label": "IELTS", "amount": 410, "mandatory": True, "per_applicant": True},
                    {"label": "Medical Exam", "amount": 350, "mandatory": False, "per_applicant": True},
                ],
            },
            "work_visa": {
                "name": "Essential Skills Work Visa",
                "official_url": "https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/accredited-employer-work-visa",
                "processing_days": "60-120",
                "fees": [
                    {"label": "AEWV Application", "amount": 750, "mandatory": True, "per_applicant": True},
                    {"label": "Job Check (employer)", "amount": 735, "mandatory": True, "per_applicant": False},
                    {"label": "Medical Exam", "amount": 350, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "germany": {
        "name": "Germany",
        "flag": "🇩🇪",
        "currency": "EUR",
        "categories": {
            "eu_blue_card": {
                "name": "EU Blue Card",
                "official_url": "https://www.make-it-in-germany.com/en/visa-residence/eu-blue-card",
                "processing_days": "30-90",
                "fees": [
                    {"label": "National D-Visa Application", "amount": 75, "mandatory": True, "per_applicant": True},
                    {"label": "Residence Permit Issue", "amount": 110, "mandatory": True, "per_applicant": True},
                    {"label": "Document Translation", "amount": 150, "mandatory": True, "per_applicant": True},
                    {"label": "TestAS / IELTS (if required)", "amount": 150, "mandatory": False, "per_applicant": True},
                ],
            },
            "student_visa": {
                "name": "Student Visa",
                "official_url": "https://www.auswaertiges-amt.de/en/visa-service/-/231148",
                "processing_days": "30-90",
                "fees": [
                    {"label": "National Visa Fee", "amount": 75, "mandatory": True, "per_applicant": True},
                    {"label": "Blocked Account Proof", "amount": 11208, "mandatory": True, "per_applicant": True, "notes": "Annual proof of funds"},
                    {"label": "TestAS / DSH / IELTS", "amount": 150, "mandatory": True, "per_applicant": True},
                ],
            },
            "jobseeker": {
                "name": "Job Seeker Visa",
                "official_url": "https://www.make-it-in-germany.com/en/visa-residence/job-seeker-visa",
                "processing_days": "45-90",
                "fees": [
                    {"label": "Visa Application Fee", "amount": 75, "mandatory": True, "per_applicant": True},
                    {"label": "Proof of Funds (6 months)", "amount": 5000, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "singapore": {
        "name": "Singapore",
        "flag": "🇸🇬",
        "currency": "SGD",
        "categories": {
            "employment_pass": {
                "name": "Employment Pass (EP)",
                "official_url": "https://www.mom.gov.sg/passes-and-permits/employment-pass",
                "processing_days": "7-21",
                "fees": [
                    {"label": "EP Application Fee", "amount": 105, "mandatory": True, "per_applicant": True},
                    {"label": "EP Issuance Fee", "amount": 225, "mandatory": True, "per_applicant": True},
                    {"label": "Multiple Journey Visa", "amount": 30, "mandatory": False, "per_applicant": True},
                ],
            },
            "student_pass": {
                "name": "Student Pass",
                "official_url": "https://www.ica.gov.sg/pass/studentpass",
                "processing_days": "14-30",
                "fees": [
                    {"label": "Student Pass Application", "amount": 30, "mandatory": True, "per_applicant": True},
                    {"label": "Issuance Fee", "amount": 60, "mandatory": True, "per_applicant": True},
                ],
            },
            "pr": {
                "name": "Permanent Residence",
                "official_url": "https://www.ica.gov.sg/pr/apply_pr",
                "processing_days": "120-180",
                "fees": [
                    {"label": "PR Application Fee", "amount": 100, "mandatory": True, "per_applicant": True},
                    {"label": "Entry Permit Issue", "amount": 20, "mandatory": True, "per_applicant": True},
                    {"label": "Re-entry Permit (5 yrs)", "amount": 50, "mandatory": True, "per_applicant": True},
                    {"label": "Identity Card", "amount": 50, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "uae": {
        "name": "UAE",
        "flag": "🇦🇪",
        "currency": "AED",
        "categories": {
            "golden_visa": {
                "name": "Golden Visa (10-year)",
                "official_url": "https://u.ae/en/information-and-services/visa-and-emirates-id/residence-visas/golden-visa",
                "processing_days": "30-60",
                "fees": [
                    {"label": "Application + Processing", "amount": 2800, "mandatory": True, "per_applicant": True},
                    {"label": "Medical Fitness Test", "amount": 320, "mandatory": True, "per_applicant": True},
                    {"label": "Emirates ID (10 yrs)", "amount": 1070, "mandatory": True, "per_applicant": True},
                    {"label": "Document Attestation", "amount": 500, "mandatory": True, "per_applicant": True},
                ],
            },
            "employment_visa": {
                "name": "Employment Visa + Residency",
                "official_url": "https://u.ae/en/information-and-services/jobs",
                "processing_days": "14-30",
                "fees": [
                    {"label": "Employment Entry Permit", "amount": 1250, "mandatory": True, "per_applicant": True},
                    {"label": "Medical Fitness", "amount": 320, "mandatory": True, "per_applicant": True},
                    {"label": "Emirates ID (2 yrs)", "amount": 370, "mandatory": True, "per_applicant": True},
                    {"label": "Residence Visa Stamp", "amount": 600, "mandatory": True, "per_applicant": True},
                ],
            },
            "tourist": {
                "name": "Tourist Visa (60 days)",
                "official_url": "https://smartservices.icp.gov.ae/",
                "processing_days": "3-7",
                "fees": [
                    {"label": "Tourist Visa (60-day)", "amount": 370, "mandatory": True, "per_applicant": True},
                    {"label": "Service Fee", "amount": 100, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "ireland": {
        "name": "Ireland",
        "flag": "🇮🇪",
        "currency": "EUR",
        "categories": {
            "critical_skills": {
                "name": "Critical Skills Employment Permit",
                "official_url": "https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/",
                "processing_days": "30-90",
                "fees": [
                    {"label": "Critical Skills Permit", "amount": 1000, "mandatory": True, "per_applicant": True},
                    {"label": "Long-Stay D Visa", "amount": 60, "mandatory": True, "per_applicant": True},
                    {"label": "IRP Registration Fee", "amount": 300, "mandatory": True, "per_applicant": True},
                    {"label": "IELTS", "amount": 195, "mandatory": False, "per_applicant": True},
                ],
            },
            "student_visa": {
                "name": "Study Visa (Stamp 2)",
                "official_url": "https://www.irishimmigration.ie/coming-to-study-in-ireland/",
                "processing_days": "30-60",
                "fees": [
                    {"label": "Long-Stay Study D Visa", "amount": 60, "mandatory": True, "per_applicant": True},
                    {"label": "IRP Fee", "amount": 300, "mandatory": True, "per_applicant": True},
                    {"label": "IELTS / Academic English", "amount": 195, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "france": {
        "name": "France",
        "flag": "🇫🇷",
        "currency": "EUR",
        "categories": {
            "student_vls_ts": {
                "name": "Student Visa (VLS-TS)",
                "official_url": "https://france-visas.gouv.fr/en/student",
                "processing_days": "14-30",
                "fees": [
                    {"label": "VLS-TS Student Visa", "amount": 50, "mandatory": True, "per_applicant": True},
                    {"label": "OFII Validation", "amount": 60, "mandatory": True, "per_applicant": True},
                    {"label": "Campus France Fee", "amount": 120, "mandatory": True, "per_applicant": True},
                    {"label": "TCF/DELF French Test", "amount": 130, "mandatory": False, "per_applicant": True},
                ],
            },
            "talent_passport": {
                "name": "Talent Passport",
                "official_url": "https://france-visas.gouv.fr/en/passeport-talent",
                "processing_days": "30-60",
                "fees": [
                    {"label": "Talent Passport Visa", "amount": 99, "mandatory": True, "per_applicant": True},
                    {"label": "OFII Registration", "amount": 200, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "netherlands": {
        "name": "Netherlands",
        "flag": "🇳🇱",
        "currency": "EUR",
        "categories": {
            "highly_skilled": {
                "name": "Highly Skilled Migrant (Kennismigrant)",
                "official_url": "https://ind.nl/en/residence-permits/work/highly-skilled-migrant",
                "processing_days": "14-90",
                "fees": [
                    {"label": "MVV + Residence Permit", "amount": 380, "mandatory": True, "per_applicant": True},
                    {"label": "Spouse/Partner Permit", "amount": 210, "mandatory": False, "per_applicant": False},
                    {"label": "TB Test", "amount": 50, "mandatory": False, "per_applicant": True},
                ],
            },
            "student_visa": {
                "name": "Student MVV + Permit",
                "official_url": "https://ind.nl/en/residence-permits/study",
                "processing_days": "14-60",
                "fees": [
                    {"label": "MVV + Student Permit", "amount": 228, "mandatory": True, "per_applicant": True},
                    {"label": "IELTS/TOEFL", "amount": 195, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "portugal": {
        "name": "Portugal",
        "flag": "🇵🇹",
        "currency": "EUR",
        "categories": {
            "d7_visa": {
                "name": "D7 Passive Income Visa",
                "official_url": "https://www.sef.pt/en/pages/default.aspx",
                "processing_days": "60-120",
                "fees": [
                    {"label": "D7 Visa Application", "amount": 90, "mandatory": True, "per_applicant": True},
                    {"label": "Residence Permit Issue", "amount": 170, "mandatory": True, "per_applicant": True},
                    {"label": "Document Translation/Apostille", "amount": 300, "mandatory": True, "per_applicant": True},
                ],
            },
            "golden_visa": {
                "name": "Golden Visa (Investment)",
                "official_url": "https://www.sef.pt/en/pages/default.aspx",
                "processing_days": "180-540",
                "fees": [
                    {"label": "Initial Application", "amount": 5325, "mandatory": True, "per_applicant": True},
                    {"label": "Residence Card (per person)", "amount": 532, "mandatory": True, "per_applicant": True},
                    {"label": "Renewal (each 2 yrs)", "amount": 2663, "mandatory": True, "per_applicant": True},
                ],
            },
            "tech_visa": {
                "name": "Tech Visa (Work)",
                "official_url": "https://www.iapmei.pt/Paginas/Tech-Visa-EN.aspx",
                "processing_days": "30-60",
                "fees": [
                    {"label": "Tech Visa Application", "amount": 90, "mandatory": True, "per_applicant": True},
                    {"label": "Residence Permit", "amount": 170, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "spain": {
        "name": "Spain",
        "flag": "🇪🇸",
        "currency": "EUR",
        "categories": {
            "digital_nomad": {
                "name": "Digital Nomad Visa",
                "official_url": "https://www.exteriores.gob.es/",
                "processing_days": "15-45",
                "fees": [
                    {"label": "DNV Visa Fee", "amount": 80, "mandatory": True, "per_applicant": True},
                    {"label": "TIE Card Issue", "amount": 16, "mandatory": True, "per_applicant": True},
                    {"label": "Private Health Insurance (yr)", "amount": 900, "mandatory": True, "per_applicant": True},
                ],
            },
            "student_visa": {
                "name": "Student Visa",
                "official_url": "https://www.exteriores.gob.es/",
                "processing_days": "30-60",
                "fees": [
                    {"label": "Student Visa", "amount": 80, "mandatory": True, "per_applicant": True},
                    {"label": "NIE / TIE", "amount": 16, "mandatory": True, "per_applicant": True},
                    {"label": "Spanish Proficiency (DELE)", "amount": 130, "mandatory": False, "per_applicant": True},
                ],
            },
            "golden_visa": {
                "name": "Golden Visa (Investor)",
                "official_url": "https://www.exteriores.gob.es/",
                "processing_days": "60-120",
                "fees": [
                    {"label": "Visa Application", "amount": 80, "mandatory": True, "per_applicant": True},
                    {"label": "Residence Permit (TIE)", "amount": 16, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "japan": {
        "name": "Japan",
        "flag": "🇯🇵",
        "currency": "JPY",
        "categories": {
            "highly_skilled_professional": {
                "name": "Highly Skilled Professional",
                "official_url": "https://www.moj.go.jp/isa/applications/procedures/16-5.html",
                "processing_days": "30-90",
                "fees": [
                    {"label": "Certificate of Eligibility", "amount": 0, "mandatory": True, "per_applicant": True, "notes": "Free"},
                    {"label": "Working Visa Stamp", "amount": 3000, "mandatory": True, "per_applicant": True},
                    {"label": "JLPT Test (if required)", "amount": 7500, "mandatory": False, "per_applicant": True},
                ],
            },
            "student_visa": {
                "name": "Student Visa (Collage of Japanese Language)",
                "official_url": "https://www.mofa.go.jp/j_info/visit/visa/long/visa5.html",
                "processing_days": "60-120",
                "fees": [
                    {"label": "Student Visa Stamp", "amount": 3000, "mandatory": True, "per_applicant": True},
                    {"label": "JLPT / EJU Test", "amount": 7500, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "south_korea": {
        "name": "South Korea",
        "flag": "🇰🇷",
        "currency": "KRW",
        "categories": {
            "e7_work": {
                "name": "E-7 Special Occupation",
                "official_url": "https://www.visa.go.kr/",
                "processing_days": "14-30",
                "fees": [
                    {"label": "E-7 Visa Fee", "amount": 130000, "mandatory": True, "per_applicant": True},
                    {"label": "ARC (Alien Card)", "amount": 30000, "mandatory": True, "per_applicant": True},
                    {"label": "TOPIK Test", "amount": 55000, "mandatory": False, "per_applicant": True},
                ],
            },
            "d2_student": {
                "name": "D-2 Student Visa",
                "official_url": "https://www.visa.go.kr/",
                "processing_days": "14-30",
                "fees": [
                    {"label": "D-2 Visa Fee", "amount": 90000, "mandatory": True, "per_applicant": True},
                    {"label": "ARC Registration", "amount": 30000, "mandatory": True, "per_applicant": True},
                    {"label": "TOPIK Test", "amount": 55000, "mandatory": False, "per_applicant": True},
                ],
            },
        },
    },
    "sweden": {
        "name": "Sweden",
        "flag": "🇸🇪",
        "currency": "SEK",
        "categories": {
            "work_permit": {
                "name": "Work Permit",
                "official_url": "https://www.migrationsverket.se/English/Private-individuals/Working-in-Sweden.html",
                "processing_days": "30-180",
                "fees": [
                    {"label": "Work Permit Application", "amount": 2000, "mandatory": True, "per_applicant": True},
                    {"label": "Dependent (adult)", "amount": 1500, "mandatory": False, "per_applicant": False},
                    {"label": "Dependent (child)", "amount": 750, "mandatory": False, "per_applicant": False},
                ],
            },
            "student_permit": {
                "name": "Student Residence Permit",
                "official_url": "https://www.migrationsverket.se/English/Private-individuals/Studying-and-researching-in-Sweden.html",
                "processing_days": "60-90",
                "fees": [
                    {"label": "Student Permit Fee", "amount": 1500, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "denmark": {
        "name": "Denmark",
        "flag": "🇩🇰",
        "currency": "DKK",
        "categories": {
            "pay_limit_scheme": {
                "name": "Pay Limit Scheme",
                "official_url": "https://www.nyidanmark.dk/en-GB",
                "processing_days": "30-90",
                "fees": [
                    {"label": "Work Permit Application", "amount": 6180, "mandatory": True, "per_applicant": True},
                    {"label": "Family Accompanying (adult)", "amount": 6180, "mandatory": False, "per_applicant": False},
                ],
            },
        },
    },
    "switzerland": {
        "name": "Switzerland",
        "flag": "🇨🇭",
        "currency": "CHF",
        "categories": {
            "work_permit": {
                "name": "B Work Permit",
                "official_url": "https://www.sem.admin.ch/sem/en/home.html",
                "processing_days": "60-120",
                "fees": [
                    {"label": "Work Permit Application", "amount": 120, "mandatory": True, "per_applicant": True},
                    {"label": "Residence Permit Card", "amount": 100, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
    "hong_kong": {
        "name": "Hong Kong",
        "flag": "🇭🇰",
        "currency": "HKD",
        "categories": {
            "qmas": {
                "name": "Quality Migrant Admission Scheme",
                "official_url": "https://www.immd.gov.hk/eng/services/visas/QMAS.html",
                "processing_days": "180-540",
                "fees": [
                    {"label": "QMAS Application", "amount": 240, "mandatory": True, "per_applicant": True},
                    {"label": "Entry Visa", "amount": 290, "mandatory": True, "per_applicant": True},
                    {"label": "IELTS/Language Test", "amount": 1900, "mandatory": False, "per_applicant": True},
                ],
            },
            "employment_visa": {
                "name": "Employment Visa",
                "official_url": "https://www.immd.gov.hk/eng/services/visas/general_employment_policy.html",
                "processing_days": "30-60",
                "fees": [
                    {"label": "Employment Visa", "amount": 230, "mandatory": True, "per_applicant": True},
                    {"label": "Re-entry Endorsement", "amount": 230, "mandatory": False, "per_applicant": True},
                ],
            },
        },
    },
    "malaysia": {
        "name": "Malaysia",
        "flag": "🇲🇾",
        "currency": "MYR",
        "categories": {
            "mm2h": {
                "name": "Malaysia My Second Home",
                "official_url": "https://www.mm2h.gov.my/",
                "processing_days": "60-120",
                "fees": [
                    {"label": "MM2H Visa Fee (5-yr)", "amount": 500, "mandatory": True, "per_applicant": True},
                    {"label": "Application Processing", "amount": 5000, "mandatory": True, "per_applicant": True},
                    {"label": "Fixed Deposit Proof", "amount": 1000000, "mandatory": True, "per_applicant": True, "notes": "RM 1M for 10-yr silver"},
                ],
            },
            "employment_pass": {
                "name": "Employment Pass (Category I)",
                "official_url": "https://esd.imi.gov.my/",
                "processing_days": "14-30",
                "fees": [
                    {"label": "EP Cat-I Fee (5 yrs)", "amount": 1200, "mandatory": True, "per_applicant": True},
                    {"label": "Security Bond", "amount": 1500, "mandatory": True, "per_applicant": True},
                ],
            },
        },
    },
}


# =========================================================================
#  EXCHANGE RATE CACHE
# =========================================================================
_RATE_CACHE: Dict[str, Any] = {"data": None, "fetched_at": 0, "base": "INR"}
_CACHE_TTL = 3600  # 1 hour


async def _fetch_rates_to_inr() -> Dict[str, float]:
    """Fetch all relevant currency rates → 1 unit = X INR.
    Uses frankfurter.app (free, ECB source, no key).
    Fallback to static rates if API fails.
    """
    now = time.time()
    if _RATE_CACHE["data"] and (now - _RATE_CACHE["fetched_at"]) < _CACHE_TTL:
        return _RATE_CACHE["data"]

    currencies = ["CAD", "AUD", "GBP", "USD", "NZD", "EUR", "SGD", "JPY", "SEK",
                  "DKK", "CHF", "HKD", "MYR", "KRW", "AED"]

    # frankfurter supports base→to. We want: 1 XYZ = ? INR → base=XYZ, to=INR
    rates: Dict[str, float] = {}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # Single call: from=USD to=all supported → compute via EUR bridge
            # frankfurter supports: base=USD&symbols=INR,CAD,...
            # We'll get USD→INR, USD→others → rate XYZ→INR = (USD→INR)/(USD→XYZ)
            url = "https://api.frankfurter.dev/v1/latest"
            params = {"base": "USD", "symbols": ",".join(["INR"] + [c for c in currencies if c != "USD"])}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            usd_to = data.get("rates", {})
            usd_to_inr = usd_to.get("INR")
            if usd_to_inr:
                rates["USD"] = float(usd_to_inr)
                for cur in currencies:
                    if cur == "USD":
                        continue
                    usd_to_cur = usd_to.get(cur)
                    if usd_to_cur and usd_to_cur > 0:
                        rates[cur] = round(float(usd_to_inr) / float(usd_to_cur), 6)
                # AED not supported by frankfurter — use fallback
                if "AED" not in rates or not rates.get("AED"):
                    rates["AED"] = 22.85  # static fallback AED→INR
        rates["INR"] = 1.0
        _RATE_CACHE["data"] = rates
        _RATE_CACHE["fetched_at"] = now
        logger.info(f"Exchange rates fetched: {rates}")
        return rates
    except Exception as e:
        logger.warning(f"Live FX fetch failed, using static fallback: {e}")

    # Static fallback (approx 2025-26 rates)
    fallback = {
        "USD": 84.0, "CAD": 60.5, "AUD": 55.2, "GBP": 106.0, "EUR": 91.0,
        "NZD": 50.5, "SGD": 62.8, "JPY": 0.55, "SEK": 7.95, "DKK": 12.2,
        "CHF": 94.5, "HKD": 10.7, "MYR": 18.7, "KRW": 0.062, "AED": 22.85,
        "INR": 1.0,
    }
    _RATE_CACHE["data"] = fallback
    _RATE_CACHE["fetched_at"] = now
    return fallback


# =========================================================================
#  PYDANTIC MODELS
# =========================================================================
class CalculateRequest(BaseModel):
    country: str
    category: str
    adults: int = Field(1, ge=1, le=10)
    children: int = Field(0, ge=0, le=10)
    include_optional_ids: List[str] = []  # e.g. ["Priority Processing"]
    service_fee_inr: float = Field(0, ge=0)  # consultancy fee in INR
    gst_pct: float = Field(18.0, ge=0, le=50)  # GST on service fee
    show_currency: str = "INR"  # INR | native | both


class SaveEstimateRequest(BaseModel):
    label: str
    country: str
    category: str
    payload: Dict[str, Any]
    case_id: Optional[str] = None
    sale_id: Optional[str] = None


# =========================================================================
#  ENDPOINTS
# =========================================================================
@router.get("/countries")
async def list_countries(current_user: dict = Depends(get_current_user)):
    """List all supported countries with their visa categories (lightweight)."""
    out = []
    for key, c in FEE_DATABASE.items():
        out.append({
            "id": key,
            "name": c["name"],
            "flag": c.get("flag", ""),
            "currency": c["currency"],
            "categories": [
                {
                    "id": cat_id,
                    "name": cat["name"],
                    "processing_days": cat.get("processing_days", ""),
                    "official_url": cat.get("official_url", ""),
                }
                for cat_id, cat in c["categories"].items()
            ],
        })
    return {"countries": out, "total": len(out)}


@router.get("/country/{country_id}")
async def country_detail(country_id: str, current_user: dict = Depends(get_current_user)):
    """Full category + fee detail for a single country (for UI dropdown)."""
    c = FEE_DATABASE.get(country_id)
    if not c:
        raise HTTPException(status_code=404, detail="Country not supported")
    return {
        "id": country_id,
        "name": c["name"],
        "flag": c.get("flag", ""),
        "currency": c["currency"],
        "categories": c["categories"],
    }


@router.get("/exchange-rates")
async def get_exchange_rates(current_user: dict = Depends(get_current_user)):
    """Live exchange rates → INR (cached 1hr). Returns last-fetched timestamp."""
    rates = await _fetch_rates_to_inr()
    return {
        "base": "INR",
        "rates": rates,
        "fetched_at": datetime.fromtimestamp(_RATE_CACHE["fetched_at"], tz=timezone.utc).isoformat() if _RATE_CACHE["fetched_at"] else None,
        "source": "frankfurter.dev (ECB) with static fallback",
    }


@router.post("/calculate")
async def calculate_fees(data: CalculateRequest, current_user: dict = Depends(get_current_user)):
    """Produce a detailed fee breakdown with native & INR amounts."""
    country = FEE_DATABASE.get(data.country)
    if not country:
        raise HTTPException(status_code=404, detail="Country not supported")

    category = country["categories"].get(data.category)
    if not category:
        raise HTTPException(status_code=404, detail="Visa category not found")

    rates = await _fetch_rates_to_inr()
    native_cur = country["currency"]
    fx_to_inr = rates.get(native_cur, 1.0)

    line_items = []
    mandatory_native = 0.0
    optional_native = 0.0
    optional_selected_native = 0.0

    for idx, fee in enumerate(category["fees"]):
        is_mandatory = fee.get("mandatory", True)
        is_per_applicant = fee.get("per_applicant", True)
        amount = float(fee["amount"])
        multiplier = (data.adults + data.children) if is_per_applicant else 1
        line_total_native = amount * multiplier
        line_total_inr = round(line_total_native * fx_to_inr, 2)

        fee_id = f"{data.category}_{idx}"
        selected = True if is_mandatory else (fee_id in data.include_optional_ids or fee["label"] in data.include_optional_ids)

        line_items.append({
            "id": fee_id,
            "label": fee["label"],
            "amount_native": amount,
            "multiplier": multiplier,
            "total_native": round(line_total_native, 2),
            "total_inr": line_total_inr,
            "mandatory": is_mandatory,
            "per_applicant": is_per_applicant,
            "selected": selected,
            "notes": fee.get("notes", ""),
        })

        if is_mandatory:
            mandatory_native += line_total_native
        else:
            optional_native += line_total_native
            if selected:
                optional_selected_native += line_total_native

    govt_total_native = mandatory_native + optional_selected_native
    govt_total_inr = round(govt_total_native * fx_to_inr, 2)

    # Service fee + GST (always INR as this is consultancy billing)
    service_fee = data.service_fee_inr
    gst_amount = round(service_fee * (data.gst_pct / 100.0), 2)
    service_total_inr = service_fee + gst_amount

    grand_total_inr = govt_total_inr + service_total_inr

    return {
        "country": {
            "id": data.country,
            "name": country["name"],
            "flag": country.get("flag", ""),
            "currency": native_cur,
        },
        "category": {
            "id": data.category,
            "name": category["name"],
            "official_url": category.get("official_url", ""),
            "processing_days": category.get("processing_days", ""),
        },
        "applicants": {"adults": data.adults, "children": data.children, "total": data.adults + data.children},
        "exchange_rate": {"native_to_inr": fx_to_inr, "fetched_at": _RATE_CACHE.get("fetched_at", 0)},
        "line_items": line_items,
        "totals": {
            "govt_fees_native": round(govt_total_native, 2),
            "govt_fees_inr": govt_total_inr,
            "mandatory_native": round(mandatory_native, 2),
            "mandatory_inr": round(mandatory_native * fx_to_inr, 2),
            "optional_selected_native": round(optional_selected_native, 2),
            "optional_selected_inr": round(optional_selected_native * fx_to_inr, 2),
            "service_fee_inr": service_fee,
            "gst_pct": data.gst_pct,
            "gst_amount_inr": gst_amount,
            "service_total_inr": service_total_inr,
            "grand_total_inr": round(grand_total_inr, 2),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/save-estimate")
async def save_estimate(data: SaveEstimateRequest, current_user: dict = Depends(get_current_user)):
    """Persist a computed estimate (for proposal attachment / client sharing)."""
    estimate = {
        "id": str(uuid.uuid4()),
        "label": data.label,
        "country": data.country,
        "category": data.category,
        "payload": data.payload,
        "case_id": data.case_id,
        "sale_id": data.sale_id,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "created_by_role": current_user.get("role", ""),
        "created_at": datetime.now(timezone.utc),
    }
    await fee_estimates_col.insert_one(estimate)
    estimate.pop("_id", None)
    estimate["created_at"] = estimate["created_at"].isoformat()
    return estimate


@router.get("/estimates")
async def list_estimates(
    case_id: Optional[str] = Query(None),
    sale_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """List saved estimates, optionally filtered by case/sale."""
    query: Dict[str, Any] = {}
    if case_id:
        query["case_id"] = case_id
    if sale_id:
        query["sale_id"] = sale_id
    if current_user.get("role") == "partner":
        query["created_by"] = current_user["id"]
    elif current_user.get("role") == "client":
        # Clients see only estimates tagged to their cases / sales
        from core.database import cases_col, sales_col
        case_ids = [c["id"] async for c in cases_col.find({"client_id": current_user["id"]}, {"_id": 0, "id": 1})]
        sale_ids = [s["id"] async for s in sales_col.find({"client_email": current_user.get("email", "")}, {"_id": 0, "id": 1})]
        query["$or"] = [{"case_id": {"$in": case_ids}}, {"sale_id": {"$in": sale_ids}}]

    items = await fee_estimates_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    for it in items:
        if isinstance(it.get("created_at"), datetime):
            it["created_at"] = it["created_at"].isoformat()
    return {"estimates": items, "total": len(items)}


@router.delete("/estimates/{estimate_id}")
async def delete_estimate(estimate_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a saved estimate (only creator or admin)."""
    est = await fee_estimates_col.find_one({"id": estimate_id}, {"_id": 0})
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    if current_user.get("role") != "admin" and est.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed to delete this estimate")
    await fee_estimates_col.delete_one({"id": estimate_id})
    return {"deleted": True}
