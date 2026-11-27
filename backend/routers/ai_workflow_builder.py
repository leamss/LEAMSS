"""AI Workflow Builder — Generate country-specific immigration workflows using GPT-5.2"""
import os
import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import re
from typing import Optional, List, Dict, Any
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-workflow", tags=["AI Workflow Builder"])

products_col = db["products"]
workflow_steps_col = db["workflow_steps"]
product_master_col = db["product_master"]
# Sweep A.2 — Background job collection for AI workflow generation
ai_workflow_jobs_col = db["ai_workflow_jobs"]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Sweep A.2 — Job config
JOB_CACHE_TTL_MINUTES = 60  # Reuse successful job within last 60 min for same country+service
MAX_CONCURRENT_JOBS_PER_USER = 3
AI_CALL_TIMEOUT_SECONDS = 300  # Per-AI-call timeout (longer than ingress because we're in bg)
JOB_OVERALL_TIMEOUT_SECONDS = 240  # 4 min hard ceiling for whole job


class WorkflowGenerateRequest(BaseModel):
    country: str
    service_type: str
    subclass_id: Optional[str] = None
    custom_instructions: Optional[str] = ""


class WorkflowSaveRequest(BaseModel):
    product_name: str
    description: str
    category: Optional[str] = "immigration"
    base_fee: Optional[float] = 0.0
    commission_rate: Optional[float] = 10.0
    steps: List[dict] = []
    country: Optional[str] = ""
    visa_type: Optional[str] = ""
    visa_subclass: Optional[str] = ""
    estimated_government_fees: Optional[str] = ""
    estimated_total_duration_days: Optional[int] = 120
    success_tips: Optional[List[str]] = []
    common_rejection_reasons: Optional[List[str]] = []


COUNTRY_REFERENCES = {
    "canada": {
        "pr": "Immigration, Refugees and Citizenship Canada (IRCC) - Express Entry System. Reference: ircc.canada.ca. CRS scoring, ECA requirements, language testing (IELTS/CELPIP/TEF), NOC codes for skilled workers.",
        "visitor": "Temporary Resident Visa (TRV). Reference: ircc.canada.ca. eTA for visa-exempt countries, biometrics requirement, proof of funds, travel itinerary.",
        "student": "Study Permit. Reference: ircc.canada.ca. DLI acceptance letter, GIC proof, language scores, SDS stream.",
        "work": "LMIA-based Work Permit / PGWP / IEC Working Holiday. Reference: ircc.canada.ca. Employer LMIA, job offer, labour market impact assessment."
    },
    "australia": {
        "pr": "Department of Home Affairs - Skilled Migration (Subclass 189/190/491). Reference: homeaffairs.gov.au. SkillSelect EOI, skills assessment, points test.",
        "visitor": "Visitor Visa Subclass 600. Reference: homeaffairs.gov.au. Tourist/business/sponsored family streams.",
        "student": "Student Visa Subclass 500. Reference: homeaffairs.gov.au. CoE, GTE, OSHC, financial capacity.",
        "work": "Temporary Skill Shortage Subclass 482. Reference: homeaffairs.gov.au. Employer nomination, skills assessment.",
        "partner": "Partner Visa Subclass 820/801. Reference: homeaffairs.gov.au. Relationship evidence, sponsor approval."
    },
    "uk": {
        "visitor": "Standard Visitor Visa. Reference: gov.uk.",
        "work": "Skilled Worker / Global Talent / HPI / Graduate Route. Reference: gov.uk. CoS from licensed employer (Skilled Worker); endorsement (Global Talent); Top-80 university degree (HPI); UK student visa pathway (Graduate Route).",
        "student": "Student Visa. Reference: gov.uk. CAS from licensed sponsor, financial requirement.",
        "partner": "Family / Spouse Visa (Appendix FM). Reference: gov.uk. Sponsor income requirement, relationship evidence, English at A1/A2/B1 stages.",
        "family": "Family / Spouse Visa (Appendix FM). Reference: gov.uk. Sponsor income requirement, relationship evidence, English at A1/A2/B1 stages.",
        "pr": "Indefinite Leave to Remain (ILR / Settlement). Reference: gov.uk. 5-yr (Skilled Worker, Spouse) / 3-yr (Global Talent, Innovator Founder) / 10-yr (Long Residence). Earned Settlement reform proposed April 2026 — 10-yr baseline + reductions for high earners / public service.",
        "business": "Tier 1 Investor (CLOSED to new applications since 17 Feb 2022 — legacy ILR pathway). Reference: gov.uk. Investment-linked qualifying periods: £2M=5yr, £5M=3yr, £10M=2yr. Final ILR deadline 17 Feb 2028. Alternatives: Innovator Founder Visa."
    },
    "united_kingdom": {
        "visitor": "Standard Visitor Visa. Reference: gov.uk.",
        "work": "Skilled Worker / Global Talent / HPI / Graduate Route. Reference: gov.uk. CoS from licensed employer (Skilled Worker); endorsement (Global Talent); Top-80 university degree (HPI); UK student visa pathway (Graduate Route).",
        "student": "Student Visa. Reference: gov.uk. CAS from licensed sponsor, financial requirement.",
        "partner": "Family / Spouse Visa (Appendix FM). Reference: gov.uk. Sponsor income requirement, relationship evidence, English at A1/A2/B1 stages.",
        "family": "Family / Spouse Visa (Appendix FM). Reference: gov.uk. Sponsor income requirement, relationship evidence, English at A1/A2/B1 stages.",
        "pr": "Indefinite Leave to Remain (ILR / Settlement). Reference: gov.uk. 5-yr (Skilled Worker, Spouse) / 3-yr (Global Talent, Innovator Founder) / 10-yr (Long Residence). Earned Settlement reform proposed April 2026 — 10-yr baseline + reductions for high earners / public service.",
        "business": "Tier 1 Investor (CLOSED to new applications since 17 Feb 2022 — legacy ILR pathway). Reference: gov.uk. Investment-linked qualifying periods: £2M=5yr, £5M=3yr, £10M=2yr. Final ILR deadline 17 Feb 2028. Alternatives: Innovator Founder Visa."
    },
    "new_zealand": {
        "visitor": "Visitor Visa. Reference: immigration.govt.nz.",
        "pr": "Skilled Migrant Category. Reference: immigration.govt.nz. EOI, points-based.",
        "work": "Essential Skills Work Visa / Accredited Employer Work Visa. Reference: immigration.govt.nz.",
        "student": "Fee Paying Student Visa. Reference: immigration.govt.nz.",
        "partner": "Partner of a New Zealander Resident Visa. Reference: immigration.govt.nz. Genuine and stable relationship, 12+ months cohabitation evidence."
    },
    "usa": {
        "visitor": "B-1/B-2 Visitor Visa. Reference: travel.state.gov. MRV $185 + Visa Integrity Fee $250 (FY2026) = $435 total. Interview waiver narrowed 2 Sept 2025.",
        "student": "F-1 Student Visa. Reference: studyinthestates.dhs.gov. SEVIS $350 + MRV $185 = $535. OPT 12mo + STEM 24mo extension. Grace period 30d post-2026 reform.",
        "work": "H-1B Specialty Occupation / L-1 Intracompany Transferee. Reference: uscis.gov. H-1B: $215 reg + $2,225 small employer / $3,595 large + 85k cap lottery March. Sept 2025 Proclamation $100k fee for cap-subject offshore. L-1A 7yr + EB-1C path; L-1B 5yr.",
        "pr": "EB-1 (Priority Workers — self-petition for EB-1A) / EB-2 NIW (self-petition with national interest) / EB-1B (researcher) / EB-1C (multinational manager from L-1A) / EB-2 Standard (PERM + employer). Reference: uscis.gov. I-140 $715 + I-485 $1,440 + Premium $2,965. India backlog 10-15+ yrs EB-2.",
        "partner": "K-1 Fiancé Visa (US Citizen petitioner only) followed by AOS within 90 days. Reference: travel.state.gov. $675 I-129F + $265 MRV + $1,440 I-485. Compare CR-1/IR-1 for already-married couples.",
        "immigrant": "EB-1/EB-2/EB-3 Employment-Based Green Card. Reference: uscis.gov.",
        "family": "Family-Based Immigration (K-1, CR-1, IR-1, F1, F2A, F2B, F3, F4). Reference: uscis.gov."
    },
    "united_states": {
        "visitor": "B-1/B-2 Visitor Visa. Reference: travel.state.gov. MRV $185 + Visa Integrity Fee $250 (FY2026) = $435 total. Interview waiver narrowed 2 Sept 2025.",
        "student": "F-1 Student Visa. Reference: studyinthestates.dhs.gov. SEVIS $350 + MRV $185 = $535. OPT 12mo + STEM 24mo extension. Grace period 30d post-2026 reform.",
        "work": "H-1B Specialty Occupation / L-1 Intracompany Transferee. Reference: uscis.gov. H-1B: $215 reg + $2,225 small employer / $3,595 large + 85k cap lottery March. Sept 2025 Proclamation $100k fee for cap-subject offshore. L-1A 7yr + EB-1C path; L-1B 5yr.",
        "pr": "EB-1 (Priority Workers — self-petition for EB-1A) / EB-2 NIW (self-petition with national interest) / EB-1B (researcher) / EB-1C (multinational manager from L-1A) / EB-2 Standard (PERM + employer). Reference: uscis.gov. I-140 $715 + I-485 $1,440 + Premium $2,965. India backlog 10-15+ yrs EB-2.",
        "partner": "K-1 Fiancé Visa (US Citizen petitioner only) followed by AOS within 90 days. Reference: travel.state.gov. $675 I-129F + $265 MRV + $1,440 I-485. Compare CR-1/IR-1 for already-married couples.",
        "immigrant": "EB-1/EB-2/EB-3 Employment-Based Green Card. Reference: uscis.gov.",
        "family": "Family-Based Immigration (K-1, CR-1, IR-1, F1, F2A, F2B, F3, F4). Reference: uscis.gov."
    },
    "us": {
        "visitor": "B-1/B-2 Visitor Visa. Reference: travel.state.gov. MRV $185 + Visa Integrity Fee $250 (FY2026) = $435 total. Interview waiver narrowed 2 Sept 2025.",
        "student": "F-1 Student Visa. Reference: studyinthestates.dhs.gov. SEVIS $350 + MRV $185 = $535. OPT 12mo + STEM 24mo extension. Grace period 30d post-2026 reform.",
        "work": "H-1B Specialty Occupation / L-1 Intracompany Transferee. Reference: uscis.gov. H-1B: $215 reg + $2,225 small employer / $3,595 large + 85k cap lottery March. Sept 2025 Proclamation $100k fee for cap-subject offshore. L-1A 7yr + EB-1C path; L-1B 5yr.",
        "pr": "EB-1 (Priority Workers — self-petition for EB-1A) / EB-2 NIW (self-petition with national interest) / EB-1B (researcher) / EB-1C (multinational manager from L-1A) / EB-2 Standard (PERM + employer). Reference: uscis.gov. I-140 $715 + I-485 $1,440 + Premium $2,965. India backlog 10-15+ yrs EB-2.",
        "partner": "K-1 Fiancé Visa (US Citizen petitioner only) followed by AOS within 90 days. Reference: travel.state.gov. $675 I-129F + $265 MRV + $1,440 I-485. Compare CR-1/IR-1 for already-married couples.",
        "immigrant": "EB-1/EB-2/EB-3 Employment-Based Green Card. Reference: uscis.gov.",
        "family": "Family-Based Immigration (K-1, CR-1, IR-1, F1, F2A, F2B, F3, F4). Reference: uscis.gov."
    },
    "singapore": {
        "visitor": "Tourist Visa. Reference: ica.gov.sg.",
        "work": "Employment Pass (EP). Reference: mom.gov.sg. COMPASS framework.",
        "student": "Student Pass. Reference: ica.gov.sg.",
        "pr": "Singapore PR. Reference: ica.gov.sg."
    },
    "uae": {
        "visitor": "UAE Tourist Visa. Reference: icp.gov.ae.",
        "work": "UAE Employment Visa. Reference: mohre.gov.ae.",
        "golden": "UAE Golden Visa (10-year). Reference: icp.gov.ae.",
        "student": "UAE Student Visa. Reference: icp.gov.ae."
    },
    "germany": {
        "work": "EU Blue Card / Skilled Worker / Recognition Partnership / Chancenkarte (Opportunity Card). Reference: make-it-in-germany.com, auswaertiges-amt.de. EU Blue Card 2026: €50,700 general / €45,934.20 shortage/grad/IT (Jan 1, 2026 thresholds). Chancenkarte 6-point system, €13,092/yr financial. Recognition Partnership: enter without recognition + A2 German.",
        "student": "Student Visa (Aufenthaltserlaubnis zum Studium). Reference: auswaertiges-amt.de. Sperrkonto 2026: €11,904/yr (€992/mo BAföG rate). €75 visa fee. Public universities free for non-EU. 18-month post-grad job seeker.",
        "jobseeker": "Job Seeker Visa (6-month non-extendable). Reference: auswaertiges-amt.de. €6,162 Sperrkonto for 2026 (€1,027/mo × 6). NO full-time work; 2-week trial only.",
        "partner": "Family Reunion Visa (Familiennachzug). Reference: make-it-in-germany.com. A1 German for spouses EXEMPT if sponsor holds EU Blue Card / Skilled Worker / ICT / German citizenship. €75 adults / €37.50 minors / FREE for EU citizen family.",
        "family": "Family Reunion Visa (Familiennachzug). Reference: make-it-in-germany.com. A1 German for spouses EXEMPT if sponsor holds EU Blue Card / Skilled Worker / ICT / German citizenship. €75 adults / €37.50 minors / FREE for EU citizen family.",
        "business": "Self-Employment Visa (Selbständige Tätigkeit). Reference: make-it-in-germany.com. Two streams: Freiberufler (liberal professions, 2+ client letters) + Gewerbe (entrepreneur, business plan + IHK assessment). €250k rule abolished. Age 45+: €1,612.53/mo pension OR €232,204 assets."
    },
    "de": {
        "work": "EU Blue Card / Skilled Worker / Recognition Partnership / Chancenkarte (Opportunity Card). Reference: make-it-in-germany.com, auswaertiges-amt.de. EU Blue Card 2026: €50,700 general / €45,934.20 shortage/grad/IT. Chancenkarte 6-point system, €13,092/yr.",
        "student": "Student Visa (Aufenthaltserlaubnis zum Studium). Reference: auswaertiges-amt.de. Sperrkonto 2026: €11,904/yr. €75 visa fee. Public universities free.",
        "jobseeker": "Job Seeker Visa (6-month). Reference: auswaertiges-amt.de. €6,162 Sperrkonto.",
        "partner": "Family Reunion Visa (Familiennachzug). A1 German + sponsor exemptions documented.",
        "family": "Family Reunion Visa (Familiennachzug). A1 German + sponsor exemptions documented.",
        "business": "Self-Employment Visa (Selbständige Tätigkeit). Freiberufler + Gewerbe streams."
    },
    "deutschland": {
        "work": "EU Blue Card / Skilled Worker / Recognition Partnership / Chancenkarte (Opportunity Card). Reference: make-it-in-germany.com, auswaertiges-amt.de.",
        "student": "Student Visa (Aufenthaltserlaubnis zum Studium). Reference: auswaertiges-amt.de.",
        "jobseeker": "Job Seeker Visa (6-month). Reference: auswaertiges-amt.de.",
        "partner": "Family Reunion Visa (Familiennachzug).",
        "family": "Family Reunion Visa (Familiennachzug).",
        "business": "Self-Employment Visa (Selbständige Tätigkeit)."
    },
    "schengen": {
        "visitor": "Schengen Short-Stay Type C Tourist (€90 adult, raised from €60 on Jun 11, 2024; €45 child 6-12; FREE under 6). Reference: home-affairs.ec.europa.eu. Max 90 days in any 180-day rolling window. EES biometric border (full April 10, 2026). ETIAS irrelevant for India (postponed Q4 2026, only for visa-exempt nationalities).",
        "business": "Schengen Short-Stay Type C Business (same €90 fee). Invitation letter from EU host company + Indian employer letter required. Multi-entry common for repeat travelers.",
        "student": "Schengen Study Visa — Type C for <90 days uniform €90; Type D for full programs country-specific (€75-€228). Country-specific financial proof (DE €11,904 Sperrkonto / FR €7,928/yr / IT €500/mo / ES €7,200/yr / AT €1,200-€1,500/mo).",
        "pr": "Schengen Long-Stay National Visa Type D (>90 days). Country-specific issuance (IT €116 · DE €75 · FR €99 · ES €80+€16 TIE · NL €228 · AT €150 · PT €90). Gateway to national residence permit. ETIAS exempt for Type D holders.",
        "partner": "Schengen Short-Stay Family Visit Type C. Invitation letter from EU resident family + Verpflichtungserklärung (DE/CH) / Garanti d'accueil (FR) / relationship proof apostilled.",
        "transit": "Schengen Airport Transit Visa Type A. India NOT typically required. Required for specific nationalities (Afghanistan, Bangladesh, DR Congo, Eritrea, Ethiopia, Ghana, Iran, Iraq, Nigeria, Pakistan, Somalia, Sri Lanka, Syria + state-specific additions)."
    },
    "eu": {
        "visitor": "Schengen Short-Stay Type C Tourist (€90 adult). Reference: home-affairs.ec.europa.eu.",
        "business": "Schengen Short-Stay Type C Business (€90 adult, invitation letter required).",
        "student": "Schengen Study Visa — Type C (<90 days, €90) or Type D (country-specific).",
        "pr": "Schengen Long-Stay National Visa Type D (country-specific issuance).",
        "partner": "Schengen Short-Stay Family Visit Type C.",
        "transit": "Schengen Airport Transit Visa Type A (specific nationalities only)."
    },
    "japan": {
        "work": "Work Visa (Engineer/Specialist/Humanities). Reference: mofa.go.jp, moj.go.jp.",
        "student": "Student Visa (College of Japanese Language). Reference: mofa.go.jp.",
        "pr": "Highly Skilled Professional Visa. Reference: moj.go.jp."
    },
    "south_korea": {
        "work": "E-7 Special Occupation Visa. Reference: visa.go.kr.",
        "student": "D-2 Student Visa. Reference: visa.go.kr.",
        "visitor": "Tourist Visa. Reference: visa.go.kr."
    },
    "ireland": {
        "work": "Critical Skills Employment Permit. Reference: enterprise.gov.ie.",
        "student": "Study Visa / Stamp 2. Reference: irishimmigration.ie.",
        "visitor": "Tourist Visa. Reference: irishimmigration.ie."
    },
    "france": {
        "work": "Talent Passport / Work Visa. Reference: france-visas.gouv.fr.",
        "student": "Student Visa (VLS-TS). Reference: france-visas.gouv.fr, campusfrance.org.",
        "visitor": "Short-stay Schengen Visa. Reference: france-visas.gouv.fr."
    },
    "netherlands": {
        "work": "Highly Skilled Migrant (Kennismigrant). Reference: ind.nl.",
        "student": "Student Visa MVV + Residence Permit. Reference: ind.nl.",
        "startup": "Startup Visa. Reference: ind.nl."
    },
    "sweden": {
        "work": "Work Permit. Reference: migrationsverket.se.",
        "student": "Residence Permit for Studies. Reference: migrationsverket.se.",
        "pr": "Permanent Residence. Reference: migrationsverket.se."
    },
    "switzerland": {
        "work": "L/B Work Permit. Reference: sem.admin.ch.",
        "student": "Student Visa. Reference: sem.admin.ch.",
        "visitor": "Schengen Visa. Reference: sem.admin.ch."
    },
    "hong_kong": {
        "work": "Employment Visa. Reference: immd.gov.hk.",
        "talent": "Quality Migrant Admission Scheme (QMAS). Reference: immd.gov.hk.",
        "student": "Student Visa. Reference: immd.gov.hk."
    },
    "malaysia": {
        "work": "Employment Pass (Category I/II/III). Reference: esd.imi.gov.my.",
        "mm2h": "Malaysia My Second Home (MM2H). Reference: mm2h.gov.my.",
        "student": "Student Pass. Reference: esd.imi.gov.my."
    },
    "thailand": {
        "work": "Non-Immigrant B Visa + Work Permit. Reference: mfa.go.th.",
        "elite": "Thailand Elite Visa (5-20 years). Reference: thailandelite.com.",
        "retirement": "Non-Immigrant O-A (Retirement). Reference: mfa.go.th."
    },
    "portugal": {
        "work": "Work Visa / Tech Visa. Reference: sef.pt, vfsvisaonline.com.",
        "d7": "D7 Passive Income Visa. Reference: sef.pt.",
        "golden": "Golden Visa (Investment). Reference: sef.pt.",
        "student": "Student Visa. Reference: sef.pt."
    },
    "spain": {
        "work": "Work Visa / Highly Qualified Professional. Reference: exteriores.gob.es.",
        "nomad": "Digital Nomad Visa. Reference: exteriores.gob.es.",
        "student": "Student Visa. Reference: exteriores.gob.es.",
        "golden": "Golden Visa (Investment). Reference: exteriores.gob.es."
    },
    "italy": {
        "work": "Work Visa (Nulla Osta). Reference: esteri.it.",
        "student": "Student Visa. Reference: esteri.it.",
        "elective": "Elective Residence Visa. Reference: esteri.it."
    },
    "south_africa": {
        "work": "Critical Skills Work Visa. Reference: dha.gov.za.",
        "general_work": "General Work Visa. Reference: dha.gov.za.",
        "study": "Study Visa. Reference: dha.gov.za."
    },
    "brazil": {
        "work": "VITEM V Work Visa. Reference: gov.br/mre.",
        "investor": "Investor Visa (VIPER). Reference: gov.br/mre.",
        "digital_nomad": "Digital Nomad Visa. Reference: gov.br/mre."
    },
    "mexico": {
        "work": "Temporary Resident Visa (Work). Reference: gob.mx/inm.",
        "visitor": "Tourist Visa. Reference: gob.mx/sre.",
        "pr": "Permanent Resident Visa. Reference: gob.mx/inm."
    },
    "india": {
        "work": "Employment Visa (E). Reference: indianvisaonline.gov.in.",
        "business": "Business Visa (B). Reference: indianvisaonline.gov.in.",
        "student": "Student Visa (S). Reference: indianvisaonline.gov.in.",
        "oci": "Overseas Citizen of India (OCI) Card. Reference: ociservices.gov.in.",
        "pio": "Person of Indian Origin (PIO) Card — legacy / converts to OCI. Reference: ociservices.gov.in.",
        "visitor": "e-Tourist Visa (e-TV). Reference: indianvisaonline.gov.in/evisa/.",
        "medical": "Medical Visa (MED) + Medical Attendant (MED-X). Reference: indianvisaonline.gov.in.",
        "conference": "Conference Visa (C). Reference: indianvisaonline.gov.in.",
        "journalist": "Journalist Visa (J). Reference: indianvisaonline.gov.in. Requires MEA/XPD clearance.",
        "research": "Research Visa (R). Reference: indianvisaonline.gov.in. Requires MEA/MHA clearance.",
        "entry_x": "Entry (X) Visa — spouse/children of Indian citizens/OCI holders. Reference: indianvisaonline.gov.in.",
        "transit": "Transit Visa (T) — up to 72 hours. Reference: indianvisaonline.gov.in.",
    },
    "china": {
        "work": "Z Visa (Work Permit). Reference: visaforchina.cn.",
        "student": "X1/X2 Student Visa. Reference: visaforchina.cn.",
        "business": "M Visa (Business). Reference: visaforchina.cn."
    },
    "qatar": {
        "work": "Work Visa / Residence Permit. Reference: moi.gov.qa.",
        "visitor": "Tourist Visa / Hayya. Reference: visitqatar.qa.",
        "family": "Family Residence Visa. Reference: moi.gov.qa."
    },
    "saudi_arabia": {
        "work": "Work Visa / Iqama. Reference: visa.visitsaudi.com, mol.gov.sa.",
        "visit": "Tourist / Visit Visa. Reference: visa.visitsaudi.com.",
        "premium": "Premium Residency (Green Card). Reference: saprc.gov.sa."
    },
    "bahrain": {
        "work": "Work Visa. Reference: lmra.bh.",
        "golden": "Golden Residence Visa. Reference: npra.gov.bh.",
        "visitor": "eVisa. Reference: evisa.gov.bh."
    },
    "oman": {
        "work": "Employment Visa. Reference: rop.gov.om.",
        "investor": "Investor Residence. Reference: rop.gov.om.",
        "visitor": "Tourist eVisa. Reference: evisa.rop.gov.om."
    },
    "denmark": {
        "work": "Pay Limit Scheme / Fast-Track. Reference: nyidanmark.dk.",
        "student": "Residence Permit for Study. Reference: nyidanmark.dk.",
        "startup": "Startup Denmark. Reference: startupdenmark.info."
    },
    "norway": {
        "work": "Skilled Worker Permit. Reference: udi.no.",
        "student": "Student Permit. Reference: udi.no.",
        "family": "Family Immigration. Reference: udi.no."
    },
    "finland": {
        "work": "Residence Permit for Employed Person. Reference: migri.fi.",
        "startup": "Startup Residence Permit. Reference: migri.fi.",
        "student": "Student Residence Permit. Reference: migri.fi."
    },
    "austria": {
        "work": "Red-White-Red Card. Reference: migration.gv.at.",
        "student": "Student Visa. Reference: migration.gv.at.",
        "eu_blue": "EU Blue Card Austria. Reference: migration.gv.at."
    },
    "belgium": {
        "work": "Single Permit / Work Permit B. Reference: dofi.ibz.be.",
        "student": "Student Visa. Reference: dofi.ibz.be."
    },
    "poland": {
        "work": "Work Permit / Temporary Residence. Reference: udsc.gov.pl.",
        "student": "Student Visa. Reference: udsc.gov.pl.",
        "pr": "Permanent Residence. Reference: udsc.gov.pl."
    },
    "czech_republic": {
        "work": "Employee Card / Blue Card. Reference: mvcr.cz.",
        "student": "Long-term Visa for Study. Reference: mvcr.cz."
    },
    "greece": {
        "golden": "Golden Visa (Property Investment). Reference: enterprise.gov.gr.",
        "work": "Work Visa. Reference: migration.gov.gr.",
        "nomad": "Digital Nomad Visa. Reference: migration.gov.gr."
    },
    "turkey": {
        "work": "Work Permit. Reference: csgb.gov.tr.",
        "turkuaz": "Turquoise Card (Highly Qualified). Reference: goc.gov.tr.",
        "investor": "Investor / Citizenship by Investment. Reference: goc.gov.tr."
    },
    "philippines": {
        "work": "9(g) Work Visa / AEP. Reference: immigration.gov.ph.",
        "retirement": "SRRV (Special Resident Retiree's Visa). Reference: pra.gov.ph.",
        "student": "Student Visa 9(f). Reference: immigration.gov.ph."
    },
    "indonesia": {
        "work": "ITAS Work Permit (KITAS). Reference: imigrasi.go.id.",
        "investor": "Investor KITAS. Reference: imigrasi.go.id.",
        "retirement": "Retirement ITAS. Reference: imigrasi.go.id."
    },
    "vietnam": {
        "work": "Work Permit + TRC. Reference: xuatnhapcanh.gov.vn.",
        "investor": "Investor Visa. Reference: xuatnhapcanh.gov.vn.",
        "student": "Student Visa. Reference: xuatnhapcanh.gov.vn."
    },
    "colombia": {
        "work": "M Visa (Work). Reference: cancilleria.gov.co.",
        "nomad": "Digital Nomad Visa (V Type). Reference: cancilleria.gov.co.",
        "investor": "Investor Visa. Reference: cancilleria.gov.co."
    },
    "chile": {
        "work": "Temporary Residence (Work). Reference: extranjeria.gob.cl.",
        "pr": "Permanent Residence. Reference: extranjeria.gob.cl."
    },
    "argentina": {
        "work": "Temporary Residence (Work). Reference: migraciones.gov.ar.",
        "nomad": "Digital Nomad Visa. Reference: migraciones.gov.ar."
    },
    "kenya": {
        "work": "Work Permit (Class D/G). Reference: fns.immigration.go.ke.",
        "investor": "Investor Permit (Class G). Reference: fns.immigration.go.ke."
    },
    "nigeria": {
        "work": "Subject to Regularization (STR) / TWP. Reference: immigration.gov.ng.",
        "business": "Business Visa. Reference: immigration.gov.ng."
    },
    "egypt": {
        "work": "Work Visa. Reference: visa2egypt.gov.eg.",
        "visitor": "Tourist Visa. Reference: visa2egypt.gov.eg."
    },
    "mauritius": {
        "work": "Occupation Permit. Reference: edbmauritius.org.",
        "premium": "Premium Visa (Remote Work). Reference: edbmauritius.org."
    },
    "panama": {
        "work": "Work Permit. Reference: migracion.gob.pa.",
        "friendly": "Friendly Nations Visa. Reference: migracion.gob.pa."
    },
    "costa_rica": {
        "work": "Work Permit. Reference: migracion.go.cr.",
        "nomad": "Digital Nomad Visa. Reference: migracion.go.cr.",
        "rentista": "Rentista (Passive Income). Reference: migracion.go.cr."
    },
}


class VisaCategoriesRequest(BaseModel):
    country: str


async def _call_gpt(prompt: str, system_msg: str = "") -> str:
    """Call AI via Perplexity"""
    from services.ai_workflow_service import call_ai_with_fallback
    text, _ = await call_ai_with_fallback(prompt, system_msg)
    return text


@router.get("/countries")
async def get_supported_countries(current_user: dict = Depends(get_current_user)):
    """Get list of all supported countries with their service types"""
    countries = []
    for country, services in COUNTRY_REFERENCES.items():
        countries.append({
            "id": country,
            "name": country.replace("_", " ").title(),
            "services": [{"id": svc, "name": svc.upper().replace("_", " ")} for svc in services.keys()]
        })
    # Sort alphabetically
    countries.sort(key=lambda x: x["name"])
    return countries


@router.post("/visa-categories")
async def get_visa_categories(data: VisaCategoriesRequest, current_user: dict = Depends(get_current_user)):
    """Get all visa subclasses/categories for a country - checks verified database first, then Perplexity AI, then hardcoded fallback"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    country_key = data.country.lower().replace(" ", "_")
    country_name_clean = data.country.strip()

    from services import ai_workflow_service as ai_svc
    from services.country_regulatory_authorities import (
        get_country_authority_info,
        get_country_official_portal_url,
        get_country_vfs_url,
        get_country_visa_categories,
    )

    auth_info = get_country_authority_info(data.country)
    auth_portal = get_country_official_portal_url(data.country) or ""
    auth_vfs = get_country_vfs_url(data.country) or ai_svc.vfsglobal_url(country_key) or ""

    # 1. First check verified country workflows in MongoDB
    try:
        from routers.country_workflows import _normalise_country, workflows_col
        country_resolved = _normalise_country(country_name_clean)
        q = {}
        if country_resolved.get("code"):
            q = {
                "$or": [
                    {"country_code": country_resolved["code"]},
                    {"country_name": {"$regex": f"^{country_resolved['name_regex']}$", "$options": "i"}}
                ],
                "status": "verified"
            }
        else:
            q = {
                "country_name": {"$regex": f"^{re.escape(country_name_clean)}$", "$options": "i"},
                "status": "verified"
            }
        verified_docs = await workflows_col.find(q).to_list(100)
        if verified_docs:
            categories = []
            for w in verified_docs:
                sc_id = str(w.get("subclass_id", "")).strip()
                name = w.get("subclass_name") or (f"Subclass {sc_id}" if sc_id else "Visa")
                svc_type = w.get("service_type") or "pr"
                fees_code = w.get("fees_local_currency_code") or ""
                fees_amt = w.get("fees_local_currency_amount")
                fees_str = f"{fees_code} {fees_amt:,}" if (fees_code and isinstance(fees_amt, (int, float))) else (f"{fees_code} {fees_amt}" if fees_amt else "")
                
                categories.append({
                    "id": f"subclass_{sc_id}" if sc_id else f"{country_key}_{svc_type}",
                    "subclass_id": sc_id,
                    "name": name,
                    "description": (w.get("description") or "").split(". ")[0] if ". " in (w.get("description") or "") else (w.get("description") or "")[:150],
                    "category": svc_type,
                    "service_type": svc_type,
                    "official_url": w.get("official_url") or auth_portal,
                    "vfs_url": w.get("vfs_url") or auth_vfs,
                    "estimated_fees": fees_str,
                    "reference": w.get("eligibility_summary") or "",
                    "source": "verified_database"
                })
            return {"country": data.country, "categories": categories}
    except Exception as e:
        logger.warning(f"Error querying verified workflows for {data.country}: {e}")

    # 2. Check verified statutory streams from country_regulatory_authorities
    try:
        curated_streams = get_country_visa_categories(data.country)
        if curated_streams:
            return {"country": data.country, "categories": curated_streams}
    except Exception as e:
        logger.warning(f"Error querying country_regulatory_authorities for {data.country}: {e}")

    # 3. Try AI enrichment via Perplexity (returns live, accurate subclasses + fees)
    try:
        example = '[{"id":"work","name":"Temporary Residence (Work)","description":"For foreign nationals with a formal job offer in Argentina","category":"work","service_type":"work","official_url":"https://...","vfs_url":"https://...","estimated_fees":"USD 200"}]'
        prompt = (
            f'List ALL official visa categories and subclasses for {data.country} with subclass numbers or official names. '
            f'Include official government page URLs and current application fees. For each item include a '
            f'"service_type" field with one of: "pr" (permanent residence/skilled migration), "work" (work permits), '
            f'"student" (study visas), "visitor" (tourist/business visit), "partner" (spouse/family). '
            f'Return ONLY a JSON array. Example: {example}'
        )
        system_msg = "Immigration visa expert. List ALL visa subclasses with official URLs and fees. Each item MUST have a canonical service_type from {pr,work,student,visitor,partner}. Return ONLY valid JSON array."
        response = await _call_gpt(prompt, system_msg)
        cleaned = response.strip()
        m = re.search(r"(\[.*?\])", cleaned, re.DOTALL)
        if m:
            cleaned = m.group(1)
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start >= 0 and end > start:
            ai_cats = json.loads(cleaned[start:end])
            if isinstance(ai_cats, list) and len(ai_cats) > 0:
                _SERVICE_KEYWORD_INFER = (
                    ("pr", ["skilled", "permanent", "express entry", "smc", "pnp", "innovator", "subclass 189", "subclass 190", "subclass 491", "global talent", "green list", "residence"]),
                    ("work", ["work", "worker", "tss", "h-1b", "lmia", "aewv", "employment", "nomad"]),
                    ("student", ["student", "study", "tier 4", "f-1", "d-2", "cas"]),
                    ("visitor", ["visit", "tourist", "trv", "b-1", "b-2", "working holiday"]),
                    ("partner", ["partner", "spouse", "family", "marriage", "appendix fm"]),
                )
                for item in ai_cats:
                    if not isinstance(item, dict):
                        continue
                    if item.get("service_type"):
                        item["service_type"] = str(item["service_type"]).lower().strip()
                    else:
                        text_blob = f"{item.get('name','')} {item.get('category','')} {item.get('description','')}".lower()
                        for canonical, keywords in _SERVICE_KEYWORD_INFER:
                            if any(kw in text_blob for kw in keywords):
                                item["service_type"] = canonical
                                break
                    if not item.get("category"):
                        item["category"] = item.get("service_type", "immigration")
                    if not item.get("official_url"):
                        item["official_url"] = auth_portal
                    if not item.get("vfs_url"):
                        item["vfs_url"] = auth_vfs
                return {"country": data.country, "categories": ai_cats}
    except Exception as e:
        logger.warning(f"AI enrichment failed for {data.country}: {e}")

    # 4. Fallback to hardcoded COUNTRY_REFERENCES with clean display names
    SVC_DISPLAY_NAMES = {
        "pr": "Permanent Residence / Skilled Migration",
        "work": "Work Visa / Employment",
        "student": "Student / Study Visa",
        "visitor": "Visitor / Tourist Visa",
        "partner": "Partner / Spouse / Family Visa",
        "business": "Business / Investor Visa",
        "jobseeker": "Job Seeker Visa",
        "golden": "Golden Visa",
        "immigrant": "Immigrant Visa / Green Card",
        "family": "Family-Based Immigration",
        "transit": "Transit Visa",
        "nomad": "Digital Nomad Visa",
    }
    categories = []
    if country_key in COUNTRY_REFERENCES:
        for svc_key, ref_info in COUNTRY_REFERENCES[country_key].items():
            url = ""
            for part in ref_info.split(". "):
                if "Reference:" in part:
                    url_part = part.replace("Reference:", "").strip().rstrip(".")
                    url = url_part if url_part.startswith("http") else f"https://{url_part}"
                    break
            
            categories.append({
                "id": f"{country_key}_{svc_key}",
                "name": SVC_DISPLAY_NAMES.get(svc_key, svc_key.replace("_", " ").title()),
                "description": ref_info.split(". ")[0] if ". " in ref_info else ref_info,
                "category": svc_key,
                "service_type": svc_key,
                "official_url": url or auth_portal,
                "vfs_url": auth_vfs,
                "estimated_fees": "",
                "reference": ref_info,
            })

    return {"country": data.country, "categories": categories}



# ──────────────────────────────────────────────────────────────────────────
# Sweep A.2 — AI Workflow Background Job pattern
# Eliminates Cloudflare 60s ingress timeout by running generation in bg task.
# Client polls /generate/status/{job_id} until status=complete|failed.
# ──────────────────────────────────────────────────────────────────────────


async def _execute_workflow_generation(
    job_id: str,
    country: str,
    service_type: str,
    custom_instructions: str,
    user_id: str,
    user_name: str,
):
    """Background coroutine that runs the actual AI workflow generation.

    Updates the job doc throughout its lifecycle with progress + current_step.
    """
    from services import ai_workflow_service as ai_svc

    now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

    async def _update(patch: dict):
        patch["updated_at"] = now_iso()
        await ai_workflow_jobs_col.update_one({"job_id": job_id}, {"$set": patch})

    started_at = datetime.now(timezone.utc)
    await _update({"status": "running", "started_at": started_at.isoformat(), "progress": 10, "current_step": "analyzing"})

    try:
        country_key = country.lower().replace(" ", "_")
        service_key = service_type.lower().replace(" ", "_")

        ref_info = ""
        if country_key in COUNTRY_REFERENCES:
            ref_info = COUNTRY_REFERENCES[country_key].get(service_key, "")
            if not ref_info:
                for k, v in COUNTRY_REFERENCES[country_key].items():
                    ref_info += f"\n{k}: {v}"

        # Template context
        from routers.step_documents import _find_best_template
        template = _find_best_template(f"{country} {service_type}")
        template_context = ""
        if template:
            template_context = f"\nVerified template reference ({template.get('label','')}):\n"
            template_context += f"Fees: {template.get('fees_info','')}\n"
            template_context += f"Assessment bodies: {', '.join(template.get('assessment_bodies', []))}\n"
            for step_name, docs in template.get("steps", {}).items():
                doc_names = [d["doc_name"] for d in docs]
                template_context += f"Step '{step_name}': {', '.join(doc_names)}\n"

        vfs_url = ai_svc.vfsglobal_url(country_key)
        sa_url = await ai_svc.resolve_au_nz_skill_assessment_url(db, country_key, service_key)
        enrichment_block = ai_svc.build_enrichment_context(
            country_key, service_key, ref_info, vfs_url, sa_url, template_context,
        )

        system_msg = (
            "You are a Senior Licensed Immigration Attorney and International Regulatory Expert. "
            "You generate authoritative, legally accurate immigration workflows strictly reflecting current OFFICIAL government immigration laws and procedures. "
            "Output STRICT JSON only — no markdown wrapping, no extra conversational preamble or text.\n\n"
            "STRICT LANGUAGE MANDATE:\n"
            "ALL OUTPUT (product_name, description, step names, descriptions, required_documents names and descriptions, success_tips, common_rejection_reasons, fees) MUST BE 100% IN THE ENGLISH LANGUAGE FOR EVERY COUNTRY WITHOUT EXCEPTION. "
            "Even if the destination country is Argentina, Spain, France, Germany, Italy, Japan, etc., you MUST write EVERY document title and description in English (e.g. 'National Criminal Record Police Clearance Certificate (Apostilled with Certified Sworn Translation)', NEVER 'Certificado de Antecedentes Penales'; 'Valid National Biometric Passport', NEVER 'Pasaporte válido y vigente'; 'Official Electronic Residence Application Form (RADEX)', NEVER 'Solicitud de residencia correspondiente'; 'Evidentiary Documentation of Professional / Employment Activity', NEVER 'Documentación acreditativa de la actividad laboral'). NEVER output non-English text.\n\n"
            "MANDATE FOR DOCUMENT PRECISION AND ACCURACY (OFFICIAL GOVERNMENT STANDARDS):\n"
            "1. PRECISE OFFICIAL NOMENCLATURE: Use the exact statutory form code and official government document title in English (e.g. 'Form 80 - Personal Particulars for Assessment', 'IMM 5406 - Additional Family Information', 'Form DS-160 Online Nonimmigrant Visa Application Confirmation', 'National Police Clearance Certificate (Apostilled with Sworn Translation)', 'RADEX Online Residence Application Confirmation'). NEVER output generic terms like 'Identity Document', 'Proof of Funds', 'Application Form', 'Police Certificate', or 'Medical Report'.\n"
            "2. EXHAUSTIVE DOCUMENT SPECIFICATIONS: Every required document's 'description' MUST clearly specify in English: (a) Issuing authority/ministry, (b) Legalization standard (Hague Apostille Convention or Consular Legalization), (c) Translation requirement (must specify sworn certified translation into the official language by an accredited translator where applicable), (d) Specific validity duration (e.g. issued within 90 days, 180 days, or valid 6+ months beyond stay with 2 blank pages), and (e) Specific evidential benchmarks (e.g. 6 consecutive months stamped bank statements with bank branch seal, biometric photo 4x4cm on white background).\n"
            "3. ACCURATE STATUTORY FEES & PROCESSING TIMES: Provide realistic government processing times and current official fees in local statutory currency (e.g. AUD, USD, CAD, EUR, GBP, ARS) with estimated INR/USD equivalents."
        )

        base_prompt = f"""Generate a HIGHLY PRECISE, REGULATORY-ACCURATE immigration workflow for: {country} - {service_type}

{enrichment_block}
{f"Additional Instructions: {custom_instructions}" if custom_instructions else ""}

CRITICAL REGULATORY COMPLIANCE RULES:
1. STRICT ENGLISH MANDATE: ALL OUTPUT MUST BE 100% IN ENGLISH FOR EVERY COUNTRY WITHOUT EXCEPTION. Even for non-English speaking countries, all step names, descriptions, and document titles must be strictly in English.
2. OFFICIAL STATUTORY FORM NAMES: Every required document MUST state its exact official form number and title in English as published on the destination country's government immigration website.
3. APOSTILLE & SWORN TRANSLATION: For all documents originating outside the destination country, explicitly state whether Hague Apostille authentication (e.g. from MEA India) and certified sworn translation (Traductor Público / NAATI / Sworn Court Translator) are mandatory.
4. EXHAUSTIVE SPECIFICATIONS: Each document's 'description' must specify in English the issuing agency, required format (original with physical seal vs certified copy), validity window, and financial or evidential thresholds.
5. OFFICIAL GOVERNMENT SOURCES: Reference only real .gov / official ministerial portals and VFSglobal/authorized centers.
6. WORKFLOW COMPLETENESS: Include 5-8 chronological stages (e.g., Eligibility & Legalization, Assessment/Testing, Official Application Submission, Biometrics & Panel Medicals, Grant & Activation). EVERY step must have 3-6 thoroughly specified required_documents.

Return a JSON object with this EXACT structure:
{{
  "product_name": "Official Country - Visa Pathway with Subclass / Category",
  "description": "Authoritative overview of this statutory immigration pathway, legal basis, and eligibility criteria",
  "category": "immigration",
  "estimated_total_duration_days": 180,
  "estimated_government_fees": "Detailed breakdown of all official government statutory fees in local currency",
  "success_tips": ["Actionable compliance tip 1", "Actionable compliance tip 2", "Actionable compliance tip 3"],
  "common_rejection_reasons": ["Specific statutory refusal ground 1", "Specific statutory refusal ground 2"],
  "steps": [
    {{
      "step_name": "Official Step Name",
      "step_order": 1,
      "description": "Detailed explanation of this step per official government guidelines",
      "duration_days": 30,
      "official_source_url": "https://...official .gov link...",
      "vfsglobal_url": "https://visa.vfsglobal.com/... (if applicable)",
      "required_documents": [
        {{
          "name": "Exact Statutory Document Name with Form Code",
          "description": "Specific issuing authority, Hague apostille/legalization rules, certified sworn translation standard, and exact validity window",
          "mandatory": true,
          "typical_validity_days": 180
        }}
      ],
      "important_notes": "Statutory advice, procedural caveats, or embassy guidelines for this step",
      "government_fees": "Specific fee for this step in local currency"
    }}
  ]
}}"""

        await _update({"progress": 30, "current_step": "generating"})

        workflow_data: Optional[dict] = None
        model_used = "unknown"
        last_quality_issues: List[str] = []
        prompt = base_prompt

        for attempt in range(ai_svc.MAX_QUALITY_RETRIES + 1):
            try:
                response, model_used = await asyncio.wait_for(
                    ai_svc.call_ai_with_fallback(prompt, system_msg),
                    timeout=AI_CALL_TIMEOUT_SECONDS,
                )
                workflow_data = ai_svc.parse_json_response(response)
            except asyncio.TimeoutError:
                workflow_data = None
                last_quality_issues = [f"ai_call_timeout_attempt_{attempt+1}_after_{AI_CALL_TIMEOUT_SECONDS}s"]
                logger.warning(f"AI workflow job {job_id} attempt {attempt+1} timed out after {AI_CALL_TIMEOUT_SECONDS}s")
                continue
            except Exception as e:  # noqa: BLE001
                workflow_data = None
                last_quality_issues = [f"ai_call_error_{str(e)[:120]}"]
                logger.exception(f"AI workflow job {job_id} attempt {attempt+1} errored")
                break  # don't retry on hard non-timeout failure

            passed, issues = ai_svc.validate_workflow_quality(workflow_data)
            if passed:
                break
            last_quality_issues = issues
            if attempt < ai_svc.MAX_QUALITY_RETRIES:
                prompt = ai_svc.build_stricter_retry_prompt(base_prompt, issues)
                await _update({"progress": 30 + (attempt + 1) * 20, "current_step": "regenerating"})

        await _update({"progress": 80, "current_step": "formatting"})

        # Country-aware fallback if AI fully failed
        if not workflow_data:
            from services.country_regulatory_authorities import get_country_authority_info, get_country_official_forms
            auth_info = get_country_authority_info(country)
            if auth_info:
                country_name = auth_info["country_name"]
                authority_name = auth_info["authority_name"]
                portal_url = auth_info["official_portal_url"]
                vfs_url_target = vfs_url or auth_info.get("vfs_url", "")
                official_forms = get_country_official_forms(country, service_type) or auth_info.get("official_forms", [])

                matched_stream = next((s for s in auth_info.get("visa_streams", []) if s.get("service_type") == service_key or s.get("category") == service_key), None)
                stream_name = matched_stream.get("name") if matched_stream else f"{country_name} - {service_type.replace('_', ' ').title()}"
                stream_fees = matched_stream.get("estimated_fees") if matched_stream else "Official statutory fees per destination ministerial schedule"

                steps = [
                    {
                        "step_name": f"Eligibility & Document Legalization ({country_name})",
                        "step_order": 1,
                        "description": f"Verify eligibility criteria per {authority_name} guidelines and legalize civil and educational documents via Hague Apostille Convention.",
                        "duration_days": 30,
                        "required_documents": [
                            {"name": "Valid National Biometric Passport", "description": "Color scan of bio-data and signature pages valid for at least 6 months beyond intended stay with minimum 2 blank pages.", "mandatory": True, "typical_validity_days": 180},
                            {"name": "Apostilled Educational Degree & Transcripts", "description": "Highest degree certificate and academic transcripts authenticated with Hague Apostille Convention certification and sworn translation.", "mandatory": True, "typical_validity_days": 365},
                            {"name": "Apostilled National Police Clearance Certificate (PCC)", "description": "National criminal record clearance issued by Passport Seva Kendra / MEA within last 6 months with certified sworn translation.", "mandatory": True, "typical_validity_days": 180},
                        ],
                        "important_notes": "All foreign documents must have Hague Apostille authentication from MEA India prior to sworn translation.",
                        "government_fees": "Apostille: ~INR 50 per document",
                        "official_source_url": portal_url,
                        "vfsglobal_url": vfs_url_target,
                    },
                    {
                        "step_name": "Statutory Application Filing & Ministerial Forms",
                        "step_order": 2,
                        "description": f"Complete official electronic application forms published by {authority_name}.",
                        "duration_days": 30,
                        "required_documents": [
                            {"name": f["name"], "description": f["description"], "mandatory": f.get("mandatory", True), "typical_validity_days": 180}
                            for f in official_forms[:3]
                        ] if official_forms else [
                            {"name": f"Official {country_name} Visa Application Form", "description": f"Completed and signed statutory visa application form for {country_name}.", "mandatory": True, "typical_validity_days": 90},
                            {"name": "Comprehensive CV / Resume", "description": "Detailed curriculum vitae formatted according to European / destination standards.", "mandatory": True, "typical_validity_days": 180},
                        ],
                        "important_notes": "Ensure all form fields strictly match passport details.",
                        "government_fees": stream_fees,
                        "official_source_url": portal_url,
                        "vfsglobal_url": vfs_url_target,
                    },
                    {
                        "step_name": "Financial Capacity & Accommodation Evidence",
                        "step_order": 3,
                        "description": f"Demonstrate financial self-sufficiency and verified accommodation arrangements per {authority_name} requirements.",
                        "duration_days": 15,
                        "required_documents": [
                            {"name": "Bank Account Statements (Past 6 Consecutive Months)", "description": "Original stamped and signed bank statements showing sufficient subsistence funds meeting destination statutory threshold.", "mandatory": True, "typical_validity_days": 30},
                            {"name": "Proof of Accommodation / Lodging Guarantee", "description": "Confirmed rental agreement, hotel reservation, or official host invitation declaration.", "mandatory": True, "typical_validity_days": 90},
                            {"name": "Comprehensive International Travel & Health Insurance", "description": "Medical insurance policy providing minimum EUR 30,000 / USD 50,000 coverage valid for entire initial stay.", "mandatory": True, "typical_validity_days": 180},
                        ],
                        "important_notes": "Unexplained lump sum deposits may trigger statutory scrutiny.",
                        "government_fees": "",
                        "official_source_url": portal_url,
                        "vfsglobal_url": vfs_url_target,
                    },
                    {
                        "step_name": "Biometrics Appointment & Submission at VFS Global",
                        "step_order": 4,
                        "description": f"Schedule and attend appointment at authorized VFS Global Application Centre for biometric enrolment and document submission.",
                        "duration_days": 14,
                        "required_documents": [
                            {"name": "VFS Global Appointment Confirmation Letter", "description": "Official appointment booking confirmation with barcode for document submission.", "mandatory": True, "typical_validity_days": 30},
                            {"name": "Biometric Photographs (ICAO Standard)", "description": "Recent passport-sized color photographs on light background meeting destination biometric standards.", "mandatory": True, "typical_validity_days": 90},
                            {"name": "Complete Hard-Copy Application Dossier", "description": "Original passport, statutory forms, and complete set of photocopies.", "mandatory": True, "typical_validity_days": 30},
                        ],
                        "important_notes": "All applicants must appear in person for fingerprint and facial biometric collection.",
                        "government_fees": "VFS Service Fee: ~INR 1,800 - 2,500",
                        "official_source_url": portal_url,
                        "vfsglobal_url": vfs_url_target,
                    },
                    {
                        "step_name": "Consular Processing, Visa Grant & Activation",
                        "step_order": 5,
                        "description": f"Passport collection with entry visa sticker and post-arrival registration with local municipal / migration authorities in {country_name}.",
                        "duration_days": 30,
                        "required_documents": [
                            {"name": "Original Valid Passport with Entry Visa Vignette", "description": "Passport containing valid entry visa sticker / approval grant notification.", "mandatory": True, "typical_validity_days": 180},
                            {"name": "Local Residence Registration Document", "description": f"Post-arrival registration certificate at local municipal authority / police headquarters in {country_name}.", "mandatory": True, "typical_validity_days": 365},
                        ],
                        "important_notes": f"Register with local immigration authorities within designated window (typically 8 to 14 days) after arrival in {country_name}.",
                        "government_fees": "",
                        "official_source_url": portal_url,
                        "vfsglobal_url": vfs_url_target,
                    },
                ]

                workflow_data = {
                    "product_name": f"{country_name} - {stream_name}",
                    "description": f"Authoritative statutory immigration and visa pathway for {country_name} regulated by {authority_name}. Procedures, official forms, and appointment protocols adhere to official ministerial directives and VFS Global requirements.",
                    "category": "immigration",
                    "estimated_government_fees": stream_fees,
                    "estimated_total_duration_days": 120,
                    "success_tips": [
                        "Ensure all educational and police records are authenticated with Hague Apostille Convention stamps.",
                        "Verify that certified translations into the destination language are executed by sworn translators.",
                        "Submit complete financial statements with bank branch manager stamp and signature.",
                    ],
                    "common_rejection_reasons": [
                        "Incomplete document dossier or uncertified sworn translations",
                        "Failure to meet statutory minimum financial threshold",
                        "Discrepancies in employment history or statutory form entries",
                    ],
                    "steps": steps,
                    "_degraded_mode": "country_authorities_fallback",
                }
                model_used = "country_authorities_fallback"
            elif template:
                steps = []
                for i, (step_name, docs) in enumerate(template.get("steps", {}).items(), 1):
                    steps.append({
                        "step_name": step_name, "step_order": i, "description": "", "duration_days": 14,
                        "required_documents": [
                            {"name": d["doc_name"], "description": d.get("description", ""),
                             "mandatory": d.get("is_mandatory", True)} for d in docs],
                        "important_notes": "", "government_fees": "",
                        "official_source_url": "", "vfsglobal_url": vfs_url or "",
                    })
                workflow_data = {
                    "product_name": f"{country} - {service_type}",
                    "description": template.get("label", ""),
                    "category": "immigration",
                    "estimated_government_fees": template.get("fees_info", ""),
                    "steps": steps, "success_tips": [], "common_rejection_reasons": [],
                    "_degraded_mode": "template_fallback",
                }
                model_used = "template_fallback"

        elif not workflow_data:
            # Hard failure — mark job as failed
            await _update({
                "status": "failed",
                "progress": 100,
                "current_step": "failed",
                "error": "AI providers exhausted and no verified template available for this country/visa combo. Try a different category or retry shortly.",
                "completed_at": now_iso(),
            })
            await log_activity(user_id, user_name, "workflow_generate_failed", "ai_workflow",
                               details=f"{country}-{service_type} · job={job_id} · {';'.join(last_quality_issues)[:200]}")
        # Enrich and sanitize workflow to ensure 100% English and official statutory standards
        from services.statutory_document_standards import sanitize_workflow_to_english
        if workflow_data:
            workflow_data = sanitize_workflow_to_english(
                workflow_data,
                country,
                service_type,
            )

        # Attach metadata and populate official URLs
        from services.country_regulatory_authorities import get_country_authority_info
        auth_data = get_country_authority_info(country)
        official_portal_url = auth_data["official_portal_url"] if auth_data else ""
        authority_name = auth_data["authority_name"] if auth_data else ""
        vfs_portal_url = vfs_url or (auth_data.get("vfs_url") if auth_data else "")

        for s in workflow_data.get("steps", []):
            if not s.get("official_source_url") or "..." in s.get("official_source_url", ""):
                s["official_source_url"] = official_portal_url
            if not s.get("vfsglobal_url") or "..." in s.get("vfsglobal_url", ""):
                s["vfsglobal_url"] = vfs_portal_url

        workflow_data["_meta"] = {
            "model_used": model_used,
            "country_key": country_key,
            "service_key": service_key,
            "vfsglobal_url": vfs_portal_url,
            "official_source_url": official_portal_url,
            "authority_name": authority_name,
            "skill_assessment_url": sa_url,
            "is_skill_assessment_required": (country_key in ("australia", "new_zealand") and service_key == "pr"),
            "quality_issues": last_quality_issues,
            "generated_at": now_iso(),
            "generated_by": user_id,
            "job_id": job_id,
        }

        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        await _update({
            "status": "complete",
            "progress": 100,
            "current_step": "done",
            "result": workflow_data,
            "completed_at": completed_at.isoformat(),
            "duration_ms": duration_ms,
            "model_used": model_used,
        })

        await log_activity(user_id, user_name, "generated_workflow", "ai_workflow",
                           details=f"{country}-{service_type} via {model_used} · {len(workflow_data.get('steps', []))} steps · job={job_id} · {duration_ms}ms")
    except asyncio.CancelledError:
        await _update({"status": "failed", "error": "Cancelled by user", "completed_at": now_iso(), "current_step": "cancelled"})
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception(f"AI workflow job {job_id} crashed")
        await _update({
            "status": "failed",
            "progress": 100,
            "current_step": "failed",
            "error": f"Unexpected error: {str(e)[:200]}",
            "completed_at": now_iso(),
        })


def _serialize_job(job: dict) -> dict:
    """Strip Mongo internals before returning to client."""
    if not job:
        return {}
    job.pop("_id", None)
    return job


@router.post("/generate")
async def generate_workflow(
    request: WorkflowGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Kick off AI workflow generation as a background job. Returns instantly.

    Client must poll GET /api/ai-workflow/generate/status/{job_id} until status=complete|failed.
    Cache: if a recent successful job (<60min old) exists for same country+service_type
    by this user, returns it immediately with cached=true.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    country = request.country.strip()
    service_type = request.service_type.strip()
    if not country or not service_type:
        raise HTTPException(status_code=400, detail="country + service_type required")

    user_id = current_user["id"]
    user_name = current_user.get("name", "")

    # Sweep B.1 — Check for VERIFIED seeded workflow first; skips AI entirely if found
    try:
        from routers.country_workflows import find_verified_workflow
        verified = await find_verified_workflow(country, service_type, getattr(request, "subclass_id", None))
        if verified:
            # Build a flat document_checklist (with doc_id) and a lookup map for nested step docs
            flat_doc_checklist = verified.get("document_checklist", []) or []
            # Lookup by lowercased document name for matching against step.documents_needed strings
            doc_lookup_by_name: Dict[str, Dict[str, Any]] = {}
            for d in flat_doc_checklist:
                if isinstance(d, dict) and d.get("name"):
                    doc_lookup_by_name[d["name"].lower().strip()] = d

            def _resolve_step_doc(doc_ref: Any, fallback_id: str) -> Dict[str, Any]:
                """Resolve a step.documents_needed entry to a full doc object with doc_id."""
                if isinstance(doc_ref, dict):
                    # Already a dict — pass through, ensure doc_id present
                    out = {**doc_ref}
                    if not out.get("doc_id"):
                        out["doc_id"] = fallback_id
                    return out
                # It's a string — try to match against flat checklist by exact / substring
                name_str = str(doc_ref).strip()
                key = name_str.lower()
                # Exact match first
                match = doc_lookup_by_name.get(key)
                # Substring match fallback (step doc may be shorter / abbreviated)
                if not match:
                    for ck, cv in doc_lookup_by_name.items():
                        if key and (key in ck or ck in key):
                            match = cv
                            break
                if match:
                    return {
                        "doc_id": match.get("doc_id", fallback_id),
                        "name": match.get("name", name_str),
                        "mandatory": match.get("mandatory", True),
                        "notes": match.get("notes", ""),
                        "description": match.get("notes", ""),
                    }
                # No match — return as-is with fallback doc_id (so downstream can still reference)
                return {"doc_id": fallback_id, "name": name_str, "mandatory": True, "notes": "", "description": ""}

            # Format into the same response shape as a complete job
            return {
                "job_id": f"seeded-{verified.get('workflow_id', 'unknown')[:8]}",
                "status": "complete",
                "progress": 100,
                "current_step": "done",
                "cached": False,
                "source": "seeded_verified",
                "model_used": "verified_seed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result": {
                    "product_name": f"{verified.get('country_name')} - {verified.get('subclass_name') or verified.get('subclass_id')}",
                    "description": verified.get("description", ""),
                    "category": verified.get("category", "immigration"),
                    "estimated_total_duration_days": verified.get("processing_time_days_max", 0),
                    "estimated_government_fees": (
                        f"{verified.get('fees_local_currency_code', '')} {verified.get('fees_local_currency_amount', 0)} "
                        f"(~₹{int(verified.get('fees_inr_approx', 0)):,} INR)"
                    ),
                    "success_tips": verified.get("success_tips", []),
                    "common_rejection_reasons": verified.get("common_rejection_reasons", []),
                    # Sweep B.2 — Surface flat document_checklist with doc_id for downstream consumers
                    "document_checklist": flat_doc_checklist,
                    "steps": (lambda: (
                        __import__("services.statutory_document_standards", fromlist=["enrich_workflow_steps"]).enrich_workflow_steps(
                            verified.get("country_name", country),
                            [
                                {
                                    "step_name": s.get("title", ""),
                                    "step_order": s.get("step_number", i + 1),
                                    "description": s.get("description", ""),
                                    "duration_days": s.get("estimated_days", 0),
                                    "required_documents": [
                                        _resolve_step_doc(
                                            d,
                                            fallback_id=f"{verified.get('country_code','??')}-{verified.get('subclass_id','??')}-STEP{s.get('step_number', i+1):02d}-DOC-{di+1:02d}",
                                        )
                                        for di, d in enumerate(s.get("documents_needed", []) or [])
                                    ],
                                    "important_notes": "; ".join(s.get("tips", []) or []),
                                    "government_fees": "",
                                    "official_source_url": verified.get("official_url", ""),
                                    "vfsglobal_url": verified.get("vfs_url", ""),
                                }
                                for i, s in enumerate(verified.get("step_by_step", []) or [])
                            ],
                            service_type,
                            verified.get("subclass_id")
                        )
                    ))(),
                    "_meta": {
                        "model_used": "verified_seed",
                        "source": "country_visa_workflows",
                        "workflow_id": verified.get("workflow_id"),
                        "verified_by": verified.get("verified_by_name"),
                        "verified_at": verified.get("verified_at"),
                        "version": verified.get("version"),
                    },
                },
            }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Seeded-workflow lookup failed (non-fatal): {e}")

    # Cache lookup: most recent successful job for same country+service in last hour
    cache_cutoff = datetime.now(timezone.utc) - timedelta(minutes=JOB_CACHE_TTL_MINUTES)
    cached = await ai_workflow_jobs_col.find_one(
        {
            "user_id": user_id,
            "country": country,
            "service_type": service_type,
            "status": "complete",
            "completed_at": {"$gte": cache_cutoff.isoformat()},
        },
        sort=[("completed_at", -1)],
    )
    if cached and cached.get("result"):
        cached_job = _serialize_job(cached)
        return {
            "job_id": cached_job["job_id"],
            "status": "complete",
            "progress": 100,
            "current_step": "done",
            "result": cached_job.get("result"),
            "cached": True,
            "model_used": cached_job.get("model_used"),
            "completed_at": cached_job.get("completed_at"),
        }

    # Concurrency cap: max N simultaneous jobs per user
    active_count = await ai_workflow_jobs_col.count_documents({
        "user_id": user_id,
        "status": {"$in": ["queued", "running"]},
    })
    if active_count >= MAX_CONCURRENT_JOBS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"Maximum {MAX_CONCURRENT_JOBS_PER_USER} concurrent workflow jobs per user. Please wait for an existing one to finish or cancel it.",
        )

    job_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    await ai_workflow_jobs_col.insert_one({
        "job_id": job_id,
        "user_id": user_id,
        "user_name": user_name,
        "country": country,
        "service_type": service_type,
        "custom_instructions": request.custom_instructions or "",
        "status": "queued",
        "progress": 0,
        "current_step": "queued",
        "result": None,
        "error": None,
        "model_used": None,
        "created_at": now_iso,
        "updated_at": now_iso,
        "started_at": None,
        "completed_at": None,
        "duration_ms": None,
    })

    # Kick off background generation. We DO NOT await it — return immediately.
    async def _runner():
        try:
            await asyncio.wait_for(
                _execute_workflow_generation(
                    job_id, country, service_type, request.custom_instructions or "", user_id, user_name,
                ),
                timeout=JOB_OVERALL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            await ai_workflow_jobs_col.update_one(
                {"job_id": job_id},
                {"$set": {
                    "status": "failed",
                    "current_step": "timeout",
                    "error": f"Job exceeded {JOB_OVERALL_TIMEOUT_SECONDS}s overall timeout",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }},
            )

    asyncio.create_task(_runner())

    return {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "current_step": "queued",
        "cached": False,
        "poll_url": f"/api/ai-workflow/generate/status/{job_id}",
    }


@router.get("/generate/status/{job_id}")
async def get_workflow_job_status(job_id: str, current_user: dict = Depends(get_current_user)):
    """Poll endpoint — returns current state of a generation job."""
    job = await ai_workflow_jobs_col.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Authz: owner OR admin
    if job.get("user_id") != current_user["id"] and current_user.get("role") not in ("admin", "admin_owner"):
        raise HTTPException(status_code=403, detail="Not authorized for this job")
    return job


@router.delete("/generate/{job_id}")
async def cancel_workflow_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel a queued or running job (best-effort — marks status=failed/cancelled).

    Note: the underlying asyncio task may still finish briefly after cancel because
    we don't track task handles across requests; the next status poll will reflect
    the cancellation state we wrote.
    """
    job = await ai_workflow_jobs_col.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != current_user["id"] and current_user.get("role") not in ("admin", "admin_owner"):
        raise HTTPException(status_code=403, detail="Not authorized for this job")
    if job.get("status") in ("complete", "failed"):
        return {"job_id": job_id, "status": job["status"], "already_terminal": True}
    await ai_workflow_jobs_col.update_one(
        {"job_id": job_id},
        {"$set": {
            "status": "failed",
            "current_step": "cancelled",
            "error": "Cancelled by user",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"job_id": job_id, "status": "failed", "cancelled": True}


@router.get("/generate/recent")
async def list_recent_workflow_jobs(
    country: Optional[str] = None,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """List user's most recent generation jobs (for cache hit detection client-side)."""
    q: dict = {"user_id": current_user["id"]}
    if country:
        q["country"] = country
    cursor = ai_workflow_jobs_col.find(q, {"_id": 0, "result": 0}).sort("created_at", -1).limit(min(limit, 50))
    items = await cursor.to_list(length=limit)
    return {"items": items, "count": len(items)}


@router.post("/generate-sync")
async def generate_workflow_sync_legacy(
    request: WorkflowGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """DEPRECATED — Legacy synchronous endpoint kept for backward compat.

    Generation may exceed Cloudflare's 60s ingress timeout, causing 502 errors.
    Always prefer POST /generate (returns job_id) + polling /generate/status/{job_id}.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    from services import ai_workflow_service as ai_svc

    country_key = request.country.lower().replace(" ", "_")
    service_key = request.service_type.lower().replace(" ", "_")

    ref_info = ""
    if country_key in COUNTRY_REFERENCES:
        ref_info = COUNTRY_REFERENCES[country_key].get(service_key, "")
        if not ref_info:
            for k, v in COUNTRY_REFERENCES[country_key].items():
                ref_info += f"\n{k}: {v}"

    # Verified template context (for richer prompts)
    from routers.step_documents import _find_best_template
    template = _find_best_template(f"{request.country} {request.service_type}")
    template_context = ""
    if template:
        template_context = f"\nVerified template reference ({template.get('label','')}):\n"
        template_context += f"Fees: {template.get('fees_info','')}\n"
        template_context += f"Assessment bodies: {', '.join(template.get('assessment_bodies', []))}\n"
        for step_name, docs in template.get("steps", {}).items():
            doc_names = [d["doc_name"] for d in docs]
            template_context += f"Step '{step_name}': {', '.join(doc_names)}\n"

    # Phase 20.1 — VFSglobal + AU/NZ skill assessment URLs
    vfs_url = ai_svc.vfsglobal_url(country_key)
    sa_url = await ai_svc.resolve_au_nz_skill_assessment_url(db, country_key, service_key)
    enrichment_block = ai_svc.build_enrichment_context(
        country_key, service_key, ref_info, vfs_url, sa_url, template_context,
    )

    system_msg = (
        "You are a Senior Licensed Immigration Attorney and International Regulatory Expert. "
        "You generate authoritative, legally accurate immigration workflows strictly reflecting current OFFICIAL government immigration laws and procedures. "
        "Output STRICT JSON only — no markdown wrapping, no extra conversational preamble or text.\n\n"
        "STRICT LANGUAGE MANDATE:\n"
        "ALL OUTPUT (product_name, description, step names, descriptions, required_documents names and descriptions, success_tips, common_rejection_reasons, fees) MUST BE 100% IN THE ENGLISH LANGUAGE FOR EVERY COUNTRY WITHOUT EXCEPTION. "
        "Even if the destination country is Argentina, Spain, France, Germany, Italy, Japan, etc., you MUST write EVERY document title and description in English (e.g. 'National Criminal Record Police Clearance Certificate (Apostilled with Certified Sworn Translation)', NEVER 'Certificado de Antecedentes Penales'; 'Valid National Biometric Passport', NEVER 'Pasaporte válido y vigente'; 'Official Electronic Residence Application Form (RADEX)', NEVER 'Solicitud de residencia correspondiente'; 'Evidentiary Documentation of Professional / Employment Activity', NEVER 'Documentación acreditativa de la actividad laboral'). NEVER output non-English text.\n\n"
        "MANDATE FOR DOCUMENT PRECISION AND ACCURACY (OFFICIAL GOVERNMENT STANDARDS):\n"
        "1. PRECISE OFFICIAL NOMENCLATURE: Use the exact statutory form code and official government document title in English (e.g. 'Form 80 - Personal Particulars for Assessment', 'IMM 5406 - Additional Family Information', 'Form DS-160 Online Nonimmigrant Visa Application Confirmation', 'National Police Clearance Certificate (Apostilled with Sworn Translation)', 'RADEX Online Residence Application Confirmation'). NEVER output generic terms like 'Identity Document', 'Proof of Funds', 'Application Form', 'Police Certificate', or 'Medical Report'.\n"
        "2. EXHAUSTIVE DOCUMENT SPECIFICATIONS: Every required document's 'description' MUST clearly specify in English: (a) Issuing authority/ministry, (b) Legalization standard (Hague Apostille Convention or Consular Legalization), (c) Translation requirement (must specify sworn certified translation into the official language by an accredited translator where applicable), (d) Specific validity duration (e.g. issued within 90 days, 180 days, or valid 6+ months beyond stay with 2 blank pages), and (e) Specific evidential benchmarks (e.g. 6 consecutive months stamped bank statements with bank branch seal, biometric photo 4x4cm on white background).\n"
        "3. ACCURATE STATUTORY FEES & PROCESSING TIMES: Provide realistic government processing times and current official fees in local statutory currency (e.g. AUD, USD, CAD, EUR, GBP, ARS) with estimated INR/USD equivalents."
    )

    base_prompt = f"""Generate a HIGHLY PRECISE, REGULATORY-ACCURATE immigration workflow for: {request.country} - {request.service_type}

{enrichment_block}
{f"Additional Instructions: {request.custom_instructions}" if request.custom_instructions else ""}

CRITICAL REGULATORY COMPLIANCE RULES:
1. STRICT ENGLISH MANDATE: ALL OUTPUT MUST BE 100% IN ENGLISH FOR EVERY COUNTRY WITHOUT EXCEPTION. Even for non-English speaking countries, all step names, descriptions, and document titles must be strictly in English.
2. OFFICIAL STATUTORY FORM NAMES: Every required document MUST state its exact official form number and title in English as published on the destination country's government immigration website.
3. APOSTILLE & SWORN TRANSLATION: For all documents originating outside the destination country, explicitly state whether Hague Apostille authentication (e.g. from MEA India) and certified sworn translation (Traductor Público / NAATI / Sworn Court Translator) are mandatory.
4. EXHAUSTIVE SPECIFICATIONS: Each document's 'description' must specify in English the issuing agency, required format (original with physical seal vs certified copy), validity window, and financial or evidential thresholds.
5. OFFICIAL GOVERNMENT SOURCES: Reference only real .gov / official ministerial portals and VFSglobal/authorized centers.
6. WORKFLOW COMPLETENESS: Include 5-8 chronological stages (e.g., Eligibility & Legalization, Assessment/Testing, Official Application Submission, Biometrics & Panel Medicals, Grant & Activation). EVERY step must have 3-6 thoroughly specified required_documents.

Return a JSON object with this EXACT structure:
{{
  "product_name": "Official Country - Visa Pathway with Subclass / Category",
  "description": "Authoritative overview of this statutory immigration pathway, legal basis, and eligibility criteria",
  "category": "immigration",
  "estimated_total_duration_days": 180,
  "estimated_government_fees": "Detailed breakdown of all official government statutory fees in local currency",
  "success_tips": ["Actionable compliance tip 1", "Actionable compliance tip 2", "Actionable compliance tip 3"],
  "common_rejection_reasons": ["Specific statutory refusal ground 1", "Specific statutory refusal ground 2"],
  "steps": [
    {{
      "step_name": "Official Step Name",
      "step_order": 1,
      "description": "Detailed explanation of this step per official government guidelines",
      "duration_days": 30,
      "official_source_url": "https://...official .gov link...",
      "vfsglobal_url": "https://visa.vfsglobal.com/... (if applicable)",
      "required_documents": [
        {{
          "name": "Exact Statutory Document Name with Form Code",
          "description": "Specific issuing authority, Hague apostille/legalization rules, certified sworn translation standard, and exact validity window",
          "mandatory": true,
          "typical_validity_days": 180
        }}
      ],
      "important_notes": "Statutory advice, procedural caveats, or embassy guidelines for this step",
      "government_fees": "Specific fee for this step in local currency"
    }}
  ]
}}"""

    workflow_data: dict = None
    model_used = "unknown"
    last_quality_issues: List[str] = []

    # Try up to MAX_QUALITY_RETRIES (Claude → GPT → stricter retry)
    prompt = base_prompt
    for attempt in range(ai_svc.MAX_QUALITY_RETRIES + 1):
        try:
            response, model_used = await ai_svc.call_ai_with_fallback(prompt, system_msg)
            workflow_data = ai_svc.parse_json_response(response)
        except Exception as e:  # noqa: BLE001
            # Both providers failed OR JSON unparseable
            workflow_data = None
            last_err = str(e)[:200]
            await log_activity(current_user["id"], current_user.get("name", ""), "workflow_generate_failed",
                               "ai_workflow",
                               details=f"{request.country}-{request.service_type} · attempt {attempt+1} · {last_err}")
            break  # Don't retry on hard failure — exit to template fallback

        # Quality bar check
        passed, issues = ai_svc.validate_workflow_quality(workflow_data)
        if passed:
            break  # ✅ Good output
        last_quality_issues = issues
        if attempt < ai_svc.MAX_QUALITY_RETRIES:
            prompt = ai_svc.build_stricter_retry_prompt(base_prompt, issues)
            await log_activity(current_user["id"], current_user.get("name", ""), "workflow_retry_quality",
                               "ai_workflow",
                               details=f"{request.country}-{request.service_type} · attempt {attempt+1} · issues={len(issues)}")

    # If still no workflow → template fallback
    if not workflow_data and template:
        steps = []
        for i, (step_name, docs) in enumerate(template.get("steps", {}).items(), 1):
            steps.append({
                "step_name": step_name, "step_order": i, "description": "", "duration_days": 14,
                "required_documents": [
                    {"name": d["doc_name"], "description": d.get("description", ""),
                     "mandatory": d.get("is_mandatory", True)} for d in docs],
                "important_notes": "", "government_fees": "",
                "official_source_url": "", "vfsglobal_url": vfs_url or "",
            })
        workflow_data = {
            "product_name": f"{request.country} - {request.service_type}",
            "description": template.get("label", ""),
            "category": "immigration",
            "estimated_government_fees": template.get("fees_info", ""),
            "steps": steps, "success_tips": [], "common_rejection_reasons": [],
            "_degraded_mode": "template_fallback",
        }
        model_used = "template_fallback"
    elif not workflow_data:
        raise HTTPException(
            status_code=503,
            detail="AI workflow generation temporarily unavailable. No verified template exists for this country/visa combo. Please try a different category or retry in a minute.",
        )

    # Enrich and sanitize workflow to ensure 100% English and official statutory standards
    from services.statutory_document_standards import sanitize_workflow_to_english
    if workflow_data:
        workflow_data = sanitize_workflow_to_english(
            workflow_data,
            request.country,
            request.service_type,
            getattr(request, "subclass_id", None)
        )

    # Phase 20.1 — attach metadata for audit
    workflow_data["_meta"] = {
        "model_used": model_used,
        "country_key": country_key,
        "service_key": service_key,
        "vfsglobal_url": vfs_url,
        "skill_assessment_url": sa_url,
        "is_skill_assessment_required": (country_key in ("australia", "new_zealand") and service_key == "pr"),
        "quality_issues": last_quality_issues,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": current_user.get("id"),
    }

    await log_activity(current_user["id"], current_user.get("name", ""), "generated_workflow", "ai_workflow",
                       details=f"{request.country}-{request.service_type} via {model_used} · {len(workflow_data.get('steps', []))} steps")
    return workflow_data


@router.post("/save")
async def save_workflow_as_product(
    request: WorkflowSaveRequest,
    current_user: dict = Depends(get_current_user)
):
    """Save an AI-generated workflow as a product and sync seamlessly to Product Master."""
    if current_user.get("role") not in ("admin", "admin_owner", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    
    clean_name = request.product_name.strip()
    clean_subclass = (request.visa_subclass or "").strip()

    # Import country regulatory helpers
    from services.country_regulatory_authorities import (
        resolve_country_meta,
        get_country_authority_info,
        get_country_official_portal_url,
    )

    clean_country, country_code, flag = resolve_country_meta(request.country or "", clean_name)
    auth_info = get_country_authority_info(clean_country)
    authority_name = (auth_info.get("authority_name") if isinstance(auth_info, dict) else "") or ""
    official_portal_url = get_country_official_portal_url(clean_country) or ""

    if not clean_subclass:
        match = re.search(r'\b(?:subclass\s*)?(\d{3,4})\b', clean_name, re.IGNORECASE)
        if match:
            clean_subclass = match.group(1)

    # Normalize category for seamless Product Master alignment
    clean_cat_raw = (request.category or "").strip().lower()
    if clean_cat_raw in ("skilled_migration", "pr", "immigration", "residence", "permanent_residence", "skilled"):
        clean_category = "skilled_migration"
    elif clean_cat_raw in ("work", "work_visa", "employment"):
        clean_category = "work"
    elif clean_cat_raw in ("student", "study", "education"):
        clean_category = "student"
    elif clean_cat_raw in ("visitor", "tourist", "visit"):
        clean_category = "visitor"
    elif clean_cat_raw in ("family", "partner", "spouse"):
        clean_category = "family"
    elif clean_cat_raw in ("business", "investor", "investment"):
        clean_category = "business"
    else:
        clean_category = "skilled_migration"

    # Deduplicate against existing products
    query: Dict[str, Any] = {"name": clean_name}
    if clean_country and clean_country != "Other" and clean_subclass:
        query = {
            "$or": [
                {"name": clean_name},
                {"country": clean_country, "visa_subclass": clean_subclass}
            ]
        }
    existing_product = await product_master_col.find_one(query, {"_id": 0})
    if not existing_product:
        existing_product = await products_col.find_one(query, {"_id": 0})

    prod_id = existing_product["id"] if existing_product else str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # 1. Compile document checklist template from steps
    checklist_template = []
    for step_idx, step_data in enumerate(request.steps or []):
        s_name = step_data.get("step_name") or f"Stage {step_idx + 1}"
        for doc in step_data.get("required_documents") or []:
            if isinstance(doc, dict):
                d_name = doc.get("name") or "Document"
                d_desc = doc.get("description") or ""
                d_mand = bool(doc.get("mandatory", True))
                d_lock = bool(doc.get("is_locked_until_paid", False))
                d_cat = doc.get("category") or (
                    "Identity & Legal" if any(k in d_name.lower() for k in ("passport", "birth", "police", "id", "photo", "pcc", "national"))
                    else "Professional & Academic" if any(k in d_name.lower() for k in ("degree", "transcript", "resume", "experience", "cv", "assessment", "acs", "vetassess", "ea"))
                    else "Financial & Sponsorship" if any(k in d_name.lower() for k in ("bank", "fund", "statement", "tax", "sponsor", "income"))
                    else "Health & Biometrics" if any(k in d_name.lower() for k in ("medical", "health", "biometric", "x-ray", "panel"))
                    else "General Statutory Dossier"
                )
            else:
                d_name = str(doc)
                d_desc = ""
                d_mand = True
                d_lock = False
                d_cat = "General Statutory Dossier"

            checklist_template.append({
                "id": str(uuid.uuid4()),
                "document_name": d_name,
                "category": d_cat,
                "applicant_scope": "primary_applicant",
                "is_mandatory": d_mand,
                "is_locked_until_paid": d_lock,
                "stage_name": s_name,
                "step_order": step_idx + 1,
                "description": d_desc,
                "issuing_authority": "",
                "validity_window": "",
            })

    # 2. Compile processing timeline stages
    processing_timeline = {
        "standard_duration": f"{request.estimated_total_duration_days or 120} days",
        "stages": [
            {
                "stage_order": step_idx + 1,
                "stage_name": s.get("step_name") or f"Stage {step_idx + 1}",
                "duration_days": s.get("duration_days") or 14,
                "description": s.get("description") or "",
                "government_fees": s.get("government_fees") or "",
                "important_notes": s.get("important_notes") or "",
                "authority": s.get("official_source_url") or "",
            }
            for step_idx, s in enumerate(request.steps or [])
        ]
    }

    # 3. Compile government costs
    government_costs = {
        "currency": "INR",
        "line_items": [
            {
                "title": "Estimated Statutory Authority Fees",
                "amount_inr": 0,
                "original_amount": request.estimated_government_fees or "",
                "original_currency": "Local Statutory Currency"
            }
        ] if request.estimated_government_fees else [],
        "effective_date": now.strftime("%Y-%m-%d"),
        "source_link": "",
        "notes": request.estimated_government_fees or ""
    }

    # 4. Compile sales playbook
    sales_playbook = {
        "elevator_pitch": f"Secure your official {clean_name} through LEAMSS. Our registered attorneys and case managers deliver comprehensive, statutory compliance across every stage of your visa process.",
        "target_client": f"Candidates seeking statutory immigration pathway for {clean_country or clean_name}",
        "pitch_points": request.success_tips or [
            "Official statutory visa pathway fully managed by LEAMSS registered experts",
            "End-to-end documentation auditing and legal verification",
            "Milestone-based service delivery and transparent progress tracking"
        ],
        "key_benefits": [
            f"Authorized immigration pathway for {clean_country or 'destination country'}",
            "Direct processing adhering strictly to statutory government guidelines",
            "Pre-assessment qualification check and continuous case updates"
        ],
        "discovery_questions": [
            "What is your target timeline for relocation?",
            "Have you completed an English language proficiency test (IELTS / PTE) or skills assessment?",
            "Do you have family members or dependents accompanying you?"
        ],
        "upselling": [
            "Spouse Skills Assessment & language points addition",
            "Premium Concierge Case Management tier with priority lawyer reviews",
            "Professional resume rebuild and ANZSCO alignment"
        ],
        "red_flags": request.common_rejection_reasons or [
            "Uncertified document translations or missing apostille stamps",
            "Discrepancies in declared work history or statutory employment records",
            "Insufficient verifiable proof of maintenance funds"
        ],
        "faqs": [
            {"question": "How long does the entire visa process take?", "answer": f"The statutory timeline is approximately {request.estimated_total_duration_days or 120} days depending on government processing queues."},
            {"question": "Can I include my family members?", "answer": "Yes, secondary applicants (spouse and dependent children) can be included in the primary application dossier."}
        ]
    }

    # 5. Extract official URLs from steps
    official_urls = []
    for s in request.steps or []:
        url = s.get("official_source_url")
        if url and url not in official_urls:
            official_urls.append(url)

    # 6. Build Master Document
    product_doc = {
        "id": prod_id,
        "name": clean_name,
        "summary": request.description or f"Immigration pathway for {clean_name}",
        "description": request.description or f"Immigration pathway for {clean_name}",
        "country": clean_country or (existing_product.get("country") if existing_product else "Other"),
        "country_code": country_code,
        "flag": flag,
        "authority_name": authority_name or (existing_product.get("authority_name") if existing_product else ""),
        "official_portal_url": official_portal_url or (existing_product.get("official_portal_url") if existing_product else ""),
        "visa_type": request.visa_type or (existing_product.get("visa_type") if existing_product else "Immigration / Residency"),
        "visa_subclass": clean_subclass or (existing_product.get("visa_subclass") if existing_product else ""),
        "category": clean_category,
        "status": "active",
        "base_fee": float(request.base_fee or (existing_product.get("base_fee") if existing_product else 150000)),
        "service_price": float(request.base_fee or (existing_product.get("service_price") if existing_product else 150000)),
        "commission_rate": float(request.commission_rate or 10),
        "commission_type": "percentage",
        "ai_generated": True,
        "version": int(existing_product.get("version", 1)) + 1 if existing_product else 1,
        "document_checklist_template": checklist_template or (existing_product.get("document_checklist_template") if existing_product else []),
        "processing_timeline": processing_timeline,
        "government_costs": government_costs,
        "sales_playbook": sales_playbook,
        "official_urls": official_urls or (existing_product.get("official_urls") if existing_product else []),
        "official_domains": existing_product.get("official_domains") if existing_product else [],
        "migrate_page_url": existing_product.get("migrate_page_url") if existing_product else "",
        "eligibility_criteria": existing_product.get("eligibility_criteria") if (existing_product and existing_product.get("eligibility_criteria")) else {
            "mandatory": ["Valid Passport with 6+ Months Validity", "Age Qualification Standard", "Clear Police & Character Clearance"],
            "optional": ["State / Territory Nomination", "Partner Qualifications"],
            "points_based": {
                "is_points_tested": bool(clean_subclass in ("189", "190", "491")),
                "minimum_points": 65 if clean_subclass in ("189", "190", "491") else 0,
                "scoring_factors": []
            }
        },
        "visa_conditions": existing_product.get("visa_conditions") if existing_product else [],
        "packages": existing_product.get("packages") if existing_product else [
            {"id": str(uuid.uuid4()), "package_type": "standard", "name": "Standard Package", "price": float(request.base_fee or 150000), "description": "Core visa application guidance & assessment filing", "is_active": True},
            {"id": str(uuid.uuid4()), "package_type": "smart", "name": "Smart Package", "price": float(request.base_fee or 150000) * 1.25, "description": "Includes documentation prep, priority reviews & exam support", "is_active": True},
            {"id": str(uuid.uuid4()), "package_type": "premium", "name": "Premium Package", "price": float(request.base_fee or 150000) * 1.5, "description": "Full concierge, dedicated senior case manager & resume rebuild", "is_active": True},
        ],
        "cost_allocations": existing_product.get("cost_allocations") if existing_product else [
            {"vendor_category": "internal_partner", "label": "Internal Salesperson Commission", "payment_type": "percentage", "rate": float(request.commission_rate or 10), "amount": 0, "is_optional": False},
            {"vendor_category": "external_partner", "label": "External Partner Fee", "payment_type": "percentage", "rate": 8.0, "amount": 0, "is_optional": False},
            {"vendor_category": "case_manager", "label": "Case Manager Fee", "payment_type": "flat", "rate": 0, "amount": 5000, "is_optional": False},
        ],
        "updated_at": now,
        "created_at": existing_product.get("created_at") if existing_product else now,
    }

    # Upsert into products collection
    await products_col.update_one({"id": prod_id}, {"$set": product_doc}, upsert=True)

    # Upsert into product_master collection (Single Source of Truth)
    await product_master_col.update_one({"id": prod_id}, {"$set": product_doc}, upsert=True)

    # Clean existing workflow steps for this product to prevent duplicates
    await workflow_steps_col.delete_many({"product_id": prod_id})

    # Insert steps into workflow_steps_col
    saved_steps = []
    for step_data in request.steps or []:
        required_documents = step_data.get("required_documents", [])
        document_fields = []
        for doc_index, doc in enumerate(required_documents):
            if isinstance(doc, dict):
                doc_name = doc.get("name", f"Document {doc_index + 1}")
                doc_description = doc.get("description", "")
                is_required = doc.get("mandatory", True)
                is_locked_until_paid = doc.get("is_locked_until_paid", False)
            else:
                doc_name = str(doc)
                doc_description = ""
                is_required = True
                is_locked_until_paid = False

            field_key = (
                doc_name.lower()
                .replace(" ", "_")
                .replace("-", "_")
                .replace("/", "_")
                .replace("&", "and")
            )

            document_fields.append({
                "key": f"document_{field_key}_{doc_index}",
                "label": doc_name,
                "field_type": "file",
                "options": [],
                "required": is_required,
                "filled_by": "client",
                "placeholder": "",
                "help_text": doc_description or f"Upload {doc_name}",
                "is_locked_until_paid": is_locked_until_paid,
            })

        sections = []
        if document_fields:
            sections.append({
                "id": f"section_documents_{uuid.uuid4()}",
                "title": "Required Documents",
                "fields": document_fields
            })

        step = {
            "id": str(uuid.uuid4()),
            "product_id": prod_id,
            "step_name": step_data.get("step_name", ""),
            "name": step_data.get("step_name", ""),
            "step_order": step_data.get("step_order", 0),
            "order": step_data.get("step_order", 0),
            "description": step_data.get("description", ""),
            "duration_days": step_data.get("duration_days", 7),
            "required_documents": required_documents,
            "sections": sections,
            "important_notes": step_data.get("important_notes", ""),
            "government_fees": step_data.get("government_fees", ""),
            "official_source_url": step_data.get("official_source_url", ""),
            "vfsglobal_url": step_data.get("vfsglobal_url", ""),
            "is_active": True,
            "created_at": now
        }
        await workflow_steps_col.insert_one(step)
        saved_steps.append({"id": step["id"], "step_name": step["step_name"]})

    await log_activity(
        current_user["id"],
        current_user.get("name", "Admin"),
        "saved_ai_workflow",
        "product_master",
        prod_id,
        f"Saved AI workflow to Product Master: {clean_name} ({len(saved_steps)} steps)"
    )

    return {
        "product_id": prod_id,
        "product_name": clean_name,
        "country": product_doc["country"],
        "country_code": product_doc.get("country_code", ""),
        "flag": product_doc.get("flag", "🌐"),
        "category": product_doc.get("category", "skilled_migration"),
        "visa_subclass": product_doc["visa_subclass"],
        "steps_created": len(saved_steps),
        "checklists_created": len(checklist_template),
        "message": "Workflow saved and synchronized to Product Master successfully"
    }


@router.get("/templates")
async def get_workflow_templates(current_user: dict = Depends(get_current_user)):
    """Get quick-access templates for common immigration workflows"""
    templates = [
        {"id": "canada_pr", "country": "Canada", "service": "PR", "label": "Canada PR - Express Entry", "icon": "maple-leaf"},
        {"id": "australia_pr", "country": "Australia", "service": "PR", "label": "Australia PR - Skilled Migration", "icon": "kangaroo"},
        {"id": "canada_visitor", "country": "Canada", "service": "Visitor", "label": "Canada Tourist/Visitor Visa", "icon": "plane"},
        {"id": "australia_visitor", "country": "Australia", "service": "Visitor", "label": "Australia Tourist Visa", "icon": "plane"},
        {"id": "uk_visitor", "country": "UK", "service": "Visitor", "label": "UK Standard Visitor Visa", "icon": "plane"},
        {"id": "nz_visitor", "country": "New Zealand", "service": "Visitor", "label": "New Zealand Visitor Visa", "icon": "plane"},
        {"id": "usa_visitor", "country": "USA", "service": "Visitor", "label": "USA B1/B2 Visitor Visa", "icon": "plane"},
        {"id": "singapore_visitor", "country": "Singapore", "service": "Visitor", "label": "Singapore Tourist Visa", "icon": "plane"},
        {"id": "dubai_visitor", "country": "Dubai", "service": "Visitor", "label": "UAE Tourist Visa", "icon": "plane"},
        {"id": "dubai_golden", "country": "Dubai", "service": "Golden", "label": "UAE Golden Visa (10-Year)", "icon": "star"},
    ]
    # Phase 20.1 — merge any admin-verified DB workflow templates
    verified_db = db["ai_workflow_templates"]
    async for t in verified_db.find({"verified": True}, {"_id": 0,
                                                          "id": 1, "country": 1, "service": 1,
                                                          "label": 1, "icon": 1, "model_used": 1,
                                                          "verified_by": 1, "verified_at": 1}):
        templates.append({**t, "source": "db_verified"})
    return templates


# ── Phase 20.1 — Verify endpoint (admin-only persistence) ────────────────────
class VerifyRequest(BaseModel):
    workflow_payload: dict
    country: str
    service_type: str
    notes: Optional[str] = ""


@router.post("/verify")
async def verify_workflow(
    request: VerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Persist an admin-verified AI workflow into `ai_workflow_templates` collection.

    The frontend calls this after the admin ticks "I have verified this information".
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    country_key = (request.country or "").lower().replace(" ", "_")
    service_key = (request.service_type or "").lower().replace(" ", "_")
    if not country_key or not service_key:
        raise HTTPException(status_code=400, detail="country and service_type required")

    meta = (request.workflow_payload or {}).get("_meta", {})
    template_id = f"{country_key}_{service_key}_verified"
    label = f"{request.country} - {request.service_type} (Verified)"

    doc = {
        "id": template_id,
        "country": request.country,
        "country_key": country_key,
        "service": request.service_type,
        "service_key": service_key,
        "label": label,
        "icon": "shield-check",
        "verified": True,
        "verified_by": current_user.get("id"),
        "verified_by_name": current_user.get("name") or current_user.get("email"),
        "verified_at": datetime.now(timezone.utc),
        "model_used": meta.get("model_used", "unknown"),
        "vfsglobal_url": meta.get("vfsglobal_url"),
        "skill_assessment_url": meta.get("skill_assessment_url"),
        "is_skill_assessment_required": meta.get("is_skill_assessment_required", False),
        "workflow_payload": request.workflow_payload,
        "notes": request.notes or "",
        "updated_at": datetime.now(timezone.utc),
    }
    await db["ai_workflow_templates"].update_one(
        {"id": template_id},
        {"$set": doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    await log_activity(current_user["id"], current_user.get("name", ""), "verified_workflow",
                       "ai_workflow_template", template_id,
                       f"Verified {request.country} - {request.service_type} (model: {meta.get('model_used', 'unknown')})")
    return {"ok": True, "id": template_id, "label": label,
            "verified_at": doc["verified_at"].isoformat()}


@router.get("/verified-templates")
async def list_verified_templates(current_user: dict = Depends(get_current_user)):
    """Phase 20.1 — list all admin-verified workflow templates in DB."""
    out = []
    async for t in db["ai_workflow_templates"].find({"verified": True}, {"_id": 0}):
        for k in ("verified_at", "created_at", "updated_at"):
            if hasattr(t.get(k), "isoformat"):
                t[k] = t[k].isoformat()
        out.append(t)
    return {"items": out, "count": len(out)}

