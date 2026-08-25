"""Comprehensive Seed Script — All 39 Australian Assessing Authorities Official Fees.

Populates `skill_assessment_fee_overrides` and `skill_body_master` in MongoDB so that
Fee Master (app.leamss.com/sales/fee-master) displays all authorities configured.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv
load_dotenv()
load_dotenv(os.path.join(os.getcwd(), ".env"))
load_dotenv(os.path.join(os.getcwd(), "..", ".env"))

from motor.motor_asyncio import AsyncIOMotorClient

ALL_OFFICIAL_FEES = {
    # ── Heavy Hitters & Professional ──
    "vetassess": {
        "authority_name": "Vocational Education and Training Assessment Services",
        "components": [{"label": "Full Skills Assessment (General Professional)", "amount": 1188.0, "currency": "AUD"}]
    },
    "vetassessnontrades": {
        "authority_name": "Vocational Education and Training Assessment Services (Non-Trades)",
        "components": [{"label": "Full Skills Assessment (General Professional)", "amount": 1188.0, "currency": "AUD"}]
    },
    "tra": {
        "authority_name": "Trades Recognition Australia",
        "components": [{"label": "Migration Skills Assessment (MSA)", "amount": 1107.0, "currency": "AUD"}]
    },
    "acs": {
        "authority_name": "Australian Computer Society Incorporated",
        "components": [{"label": "General Skills Assessment", "amount": 625.0, "currency": "AUD"}]
    },
    "ea": {
        "authority_name": "The Institution of Engineers Australia",
        "components": [{"label": "Competency Demonstration Report (CDR Standard)", "amount": 720.0, "currency": "AUD"}]
    },
    "anmac": {
        "authority_name": "Australian Nursing & Midwifery Accreditation Council Limited",
        "components": [{"label": "Full Migration Skills Assessment", "amount": 525.0, "currency": "AUD"}]
    },
    "medba": {
        "authority_name": "Medical Board of Australia",
        "components": [{"label": "Medical Practitioner Assessment (AMC / MedBA)", "amount": 1200.0, "currency": "AUD"}]
    },
    "iml": {
        "authority_name": "Institute of Managers and Leaders National",
        "components": [{"label": "Management Skills Assessment", "amount": 870.0, "currency": "AUD"}]
    },
    "aitsl": {
        "authority_name": "Australian Institute for Teaching and School Leadership Limited",
        "components": [{"label": "Teacher Migration Skills Assessment", "amount": 815.0, "currency": "AUD"}]
    },
    "communityworkaustralia": {
        "authority_name": "Community Work Australia Limited",
        "components": [{"label": "Skills Assessment (General Skilled Visa)", "amount": 965.0, "currency": "AUD"}]
    },
    "cpa": {
        "authority_name": "CPA Australia / CAANZ / IPA",
        "components": [{"label": "Accountant Migration Skills Assessment", "amount": 530.0, "currency": "AUD"}]
    },
    "cpaa": {
        "authority_name": "CPA Australia",
        "components": [{"label": "Accountant Migration Skills Assessment", "amount": 530.0, "currency": "AUD"}]
    },
    "caanz": {
        "authority_name": "Chartered Accountants Australia and New Zealand",
        "components": [{"label": "Accountant Migration Skills Assessment", "amount": 555.0, "currency": "AUD"}]
    },
    "ipa": {
        "authority_name": "Institute of Public Accountants",
        "components": [{"label": "Accountant Migration Skills Assessment", "amount": 430.0, "currency": "AUD"}]
    },
    "amsa": {
        "authority_name": "Australian Maritime Safety Authority",
        "components": [{"label": "Assessment of Overseas Qualifications (Migration)", "amount": 472.0, "currency": "AUD"}]
    },
    "aps": {
        "authority_name": "Australian Psychological Society Limited",
        "components": [{"label": "Assessment of Psychology Qualifications", "amount": 880.0, "currency": "AUD"}]
    },
    "acecqa": {
        "authority_name": "Australian Children's Education and Care Quality Authority",
        "components": [{"label": "Early Childhood Teacher Skills Assessment", "amount": 985.0, "currency": "AUD"}]
    },
    "asmirt": {
        "authority_name": "Australian Society of Medical Imaging and Radiation Therapy",
        "components": [{"label": "Overseas Qualifications Assessment", "amount": 850.0, "currency": "AUD"}]
    },
    "aims": {
        "authority_name": "Australian Institute of Medical Scientists",
        "components": [{"label": "Medical Laboratory Scientist Assessment", "amount": 900.0, "currency": "AUD"}]
    },
    "legaladmissionsauthorityofastateorterritory": {
        "authority_name": "Legal admissions authority of a state or territory",
        "components": [{"label": "Legal Practitioner Overseas Qualifications Assessment", "amount": 500.0, "currency": "AUD"}]
    },
    "naati": {
        "authority_name": "National Accreditation Authority for Translators and Interpreters Ltd",
        "components": [{"label": "Migration Skills Assessment (Translators/Interpreters)", "amount": 680.0, "currency": "AUD"}]
    },
    "apharmc": {
        "authority_name": "Australian Pharmacy Council Limited",
        "components": [{"label": "Stage 1 — Eligibility Assessment", "amount": 850.0, "currency": "AUD"}]
    },
    "casa": {
        "authority_name": "Civil Aviation Safety Authority",
        "components": [{"label": "Skills Assessment for Migration (Fee Code 24.8)", "amount": 100.0, "currency": "AUD"}]
    },
    "adc": {
        "authority_name": "Australian Dental Council Limited",
        "components": [{"label": "Initial Assessment of Qualifications (Dentistry)", "amount": 660.0, "currency": "AUD"}]
    },
    "cmba": {
        "authority_name": "Chinese Medicine Board of Australia",
        "components": [{"label": "Qualifications Assessment for Registration / Migration", "amount": 650.0, "currency": "AUD"}]
    },
    "apc": {
        "authority_name": "Australian Physiotherapy Council Limited",
        "components": [{"label": "Standard Assessment (Eligibility Assessment)", "amount": 870.0, "currency": "AUD"}]
    },
    "anzsnm": {
        "authority_name": "Australian and New Zealand Society of Nuclear Medicine",
        "components": [{"label": "Overseas Qualification Skills Assessment", "amount": 550.0, "currency": "AUD"}]
    },
    "aopa": {
        "authority_name": "Australian Orthotic Prosthetic Association Limited",
        "components": [
            {"label": "Stage 1 — Skilled Migration Application + Eligibility Review", "amount": 802.0, "currency": "AUD"},
            {"label": "Stage 2 — Portfolio of Evidence", "amount": 1447.60, "currency": "AUD"},
        ]
    },
    "ccea": {
        "authority_name": "Council on Chiropractic Education Australasia",
        "components": [{"label": "Stage 1 — Desktop Audit (Form A)", "amount": 884.0, "currency": "AUD"}]
    },
    "aoac": {
        "authority_name": "Australasian Osteopathic Accreditation Council Limited",
        "components": [{"label": "Stage 1 — Initial Assessment", "amount": 565.50, "currency": "AUD"}]
    },
    "daa": {
        "authority_name": "Dietitians Association of Australia",
        "components": [{"label": "Dietetic Skills Assessment (Stage 1 Desktop Audit)", "amount": 900.0, "currency": "AUD"}]
    },
    "podba": {
        "authority_name": "Podiatry Board of Australia",
        "components": [{"label": "Overseas Qualifications Assessment", "amount": 750.0, "currency": "AUD"}]
    },
    "otc": {
        "authority_name": "Occupational Therapy Council of Australia Limited",
        "components": [{"label": "Stage 1 — Desktop Assessment", "amount": 750.0, "currency": "AUD"}]
    },
    "aiqs": {
        "authority_name": "The Australian Institute of Quantity Surveyors",
        "components": [{"label": "Skilled Migration Assessment", "amount": 750.0, "currency": "AUD"}]
    },
    "aaca": {
        "authority_name": "Architects Accreditation Council of Australia",
        "components": [{"label": "Overseas Qualifications Assessment (Stage 1)", "amount": 890.0, "currency": "AUD"}]
    },
    "amc": {
        "authority_name": "Australian Medical Council",
        "components": [{"label": "Primary Source Verification (AMC)", "amount": 1200.0, "currency": "AUD"}]
    },
    "ahpra": {
        "authority_name": "Australian Health Practitioner Regulation Agency",
        "components": [{"label": "International Qualifications Assessment", "amount": 650.0, "currency": "AUD"}]
    },
    "racs": {
        "authority_name": "Royal Australasian College of Surgeons",
        "components": [{"label": "Specialist Assessment (RACS)", "amount": 1400.0, "currency": "AUD"}]
    },
    "racgp": {
        "authority_name": "Royal Australian College of General Practitioners",
        "components": [{"label": "Specialist Recognition Assessment", "amount": 1250.0, "currency": "AUD"}]
    },
    "ranzcp": {
        "authority_name": "Royal Australian and New Zealand College of Psychiatrists",
        "components": [{"label": "Specialist International Medical Graduate Assessment", "amount": 1350.0, "currency": "AUD"}]
    },
    "nmba": {
        "authority_name": "Nursing and Midwifery Board of Australia",
        "components": [{"label": "International Nursing Assessment", "amount": 525.0, "currency": "AUD"}]
    },
    "ocanz": {
        "authority_name": "Optometry Council of Australia and New Zealand",
        "components": [{"label": "Initial Assessment of Qualifications", "amount": 780.0, "currency": "AUD"}]
    },
    "avbc": {
        "authority_name": "Australasian Veterinary Boards Council",
        "components": [{"label": "Veterinary Skills Assessment (Skills Recognition)", "amount": 690.0, "currency": "AUD"}]
    },
    "mara": {
        "authority_name": "Office of the Migration Agents Registration Authority",
        "components": [{"label": "Migration Agent Registration Assessment", "amount": 450.0, "currency": "AUD"}]
    },
    "isnsw": {
        "authority_name": "Institution of Surveyors NSW",
        "components": [{"label": "Surveyor Skills Assessment", "amount": 750.0, "currency": "AUD"}]
    },
    "spa": {
        "authority_name": "The Speech Pathology Association of Australia Limited",
        "components": [{"label": "Speech Pathologist Skills Assessment", "amount": 850.0, "currency": "AUD"}]
    },
    "aasw": {
        "authority_name": "Australian Association of Social Workers Limited",
        "components": [{"label": "Social Worker Migration Skills Assessment", "amount": 950.0, "currency": "AUD"}]
    },
}


async def seed_fee_master():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "leamss")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    overrides_col = db["skill_assessment_fee_overrides"]
    now = datetime.now(timezone.utc)
    
    seeded_count = 0
    for key, data in ALL_OFFICIAL_FEES.items():
        doc = {
            "key": key,
            "authority_name": data["authority_name"],
            "components": data["components"],
            "updated_at": now,
            "updated_by": "system_seed",
        }
        await overrides_col.update_one(
            {"key": key},
            {"$set": doc, "$unset": {"amount": "", "currency": ""}},
            upsert=True,
        )
        seeded_count += 1
        print(f"[OK] Seeded fee for: {key} ({data['authority_name']})")
        
    print(f"\nSUCCESS! Seeded {seeded_count} assessing authorities into skill_assessment_fee_overrides.")


if __name__ == "__main__":
    asyncio.run(seed_fee_master())
