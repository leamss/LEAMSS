"""AI Workflow Builder — Generate country-specific immigration workflows using GPT-5.2"""
import os
import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-workflow", tags=["AI Workflow Builder"])

products_col = db["products"]
workflow_steps_col = db["workflow_steps"]
# Sweep A.2 — Background job collection for AI workflow generation
ai_workflow_jobs_col = db["ai_workflow_jobs"]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Sweep A.2 — Job config
JOB_CACHE_TTL_MINUTES = 60  # Reuse successful job within last 60 min for same country+service
MAX_CONCURRENT_JOBS_PER_USER = 3
AI_CALL_TIMEOUT_SECONDS = 90  # Per-AI-call timeout (longer than ingress because we're in bg)
JOB_OVERALL_TIMEOUT_SECONDS = 240  # 4 min hard ceiling for whole job


class WorkflowGenerateRequest(BaseModel):
    country: str
    service_type: str
    custom_instructions: Optional[str] = ""


class WorkflowSaveRequest(BaseModel):
    product_name: str
    description: str
    category: str
    base_fee: float
    commission_rate: float
    steps: List[dict]


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
    """Call GPT-5.2 via emergentintegrations"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"workflow-builder-{uuid.uuid4().hex[:8]}",
            system_message=system_msg
        )
        return await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


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
    """Get all visa subclasses/categories for a country - uses hardcoded data first, AI as optional enrichment"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    country_key = data.country.lower().replace(" ", "_")
    
    # Build categories from COUNTRY_REFERENCES (no AI needed)
    categories = []
    if country_key in COUNTRY_REFERENCES:
        for svc_key, ref_info in COUNTRY_REFERENCES[country_key].items():
            # Extract URL from reference info
            url = ""
            for part in ref_info.split(". "):
                if "Reference:" in part:
                    url_part = part.replace("Reference:", "").strip().rstrip(".")
                    if url_part and not url_part.startswith("http"):
                        url = f"https://{url_part}"
                    elif url_part.startswith("http"):
                        url = url_part
                    break
            
            categories.append({
                "id": f"{country_key}_{svc_key}",
                "name": svc_key.replace("_", " ").title(),
                "description": ref_info.split(". ")[0] if ". " in ref_info else ref_info,
                "category": svc_key,
                "service_type": svc_key,  # B.2 HOTFIX — canonical token for /generate
                "official_url": url,
                "estimated_fees": "",
                "reference": ref_info,
            })

    # Try AI enrichment (optional - won't fail if budget exceeded)
    try:
        example = '[{"id":"subclass_189","name":"Subclass 189 - Skilled Independent","description":"Points-based visa for skilled workers","category":"skilled_migration","service_type":"pr","official_url":"https://homeaffairs.gov.au/...","estimated_fees":"AUD $4,910"}]'
        prompt = (
            f'List ALL visa categories and subclasses for {data.country} with subclass numbers where applicable. '
            f'Include official government page URLs and current application fees. For each item include a '
            f'"service_type" field with one of: "pr" (permanent residence/skilled migration), "work" (work permits), '
            f'"student" (study visas), "visitor" (tourist/business visit), "partner" (spouse/family). '
            f'Return ONLY a JSON array. Example: {example}'
        )
        system_msg = "Immigration visa expert. List ALL visa subclasses with official URLs and fees. Each item MUST have a canonical service_type from {pr,work,student,visitor,partner}. Return ONLY valid JSON."
        response = await _call_gpt(prompt, system_msg)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            cleaned = cleaned.rsplit("```", 1)[0]
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start >= 0 and end > start:
            ai_cats = json.loads(cleaned[start:end])
            if isinstance(ai_cats, list) and len(ai_cats) > 0:
                # B.2 HOTFIX — ensure each AI item has canonical service_type
                # If AI omitted it, infer from name/category via keyword scan
                _SERVICE_KEYWORD_INFER = (
                    ("pr", ["skilled", "permanent", "express entry", "smc", "pnp", "innovator", "subclass 189", "subclass 190", "subclass 491", "global talent", "green list"]),
                    ("work", ["work", "worker", "tss", "h-1b", "lmia", "aewv", "employment"]),
                    ("student", ["student", "study", "tier 4", "f-1", "d-2", "cas"]),
                    ("visitor", ["visit", "tourist", "trv", "b-1", "b-2", "working holiday"]),
                    ("partner", ["partner", "spouse", "family", "marriage", "appendix fm"]),
                )
                for item in ai_cats:
                    if not isinstance(item, dict):
                        continue
                    if item.get("service_type"):
                        item["service_type"] = str(item["service_type"]).lower().strip()
                        continue
                    # Infer from name/category
                    text_blob = f"{item.get('name','')} {item.get('category','')} {item.get('description','')}".lower()
                    for canonical, keywords in _SERVICE_KEYWORD_INFER:
                        if any(kw in text_blob for kw in keywords):
                            item["service_type"] = canonical
                            break
                categories = ai_cats  # AI gave better data, use it
    except Exception:
        pass  # AI failed (budget, timeout etc) - use hardcoded data

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
            "You are an expert immigration consultant AI with deep knowledge of global immigration processes. "
            "You generate accurate, step-by-step immigration workflows based on OFFICIAL government requirements "
            "and VFSglobal application centre procedures (for Indian applicants). "
            "You must return ONLY valid JSON, no markdown, no extra text. "
            "Every step MUST have at least 3 required documents. Include all documents that an applicant would need."
        )

        base_prompt = f"""Generate a COMPREHENSIVE immigration workflow for: {country} - {service_type}

{enrichment_block}
{f"Additional Instructions: {custom_instructions}" if custom_instructions else ""}

CRITICAL RULES:
1. At least 5 steps. Every step MUST have at least 3 required_documents.
2. Include specific document names as used by the government (e.g., "Form 80 - Personal Particulars")
3. Include ALL fees in local currency based on current official government fee schedules
4. Reference only official government websites (.gov / official portals) AND VFSglobal for application submission step
5. Be thorough — passport, photos, police clearances, medical exams, financial evidence, biometrics, etc.
6. For AU/NZ PR ONLY: include "Skills Assessment" as first or second step (mandatory). For all OTHER workflows, DO NOT include a skills assessment step.

Return a JSON object with this EXACT structure:
{{
  "product_name": "Country - Visa Type with Subclass Number",
  "description": "Brief description of this immigration pathway",
  "category": "immigration",
  "estimated_total_duration_days": 180,
  "estimated_government_fees": "Complete fee breakdown in local currency (application fee + biometrics + medical + skills assessment + language test)",
  "success_tips": ["tip1", "tip2", "tip3"],
  "common_rejection_reasons": ["reason1", "reason2"],
  "steps": [
    {{
      "step_name": "Step Name",
      "step_order": 1,
      "description": "Detailed description of what happens in this step",
      "duration_days": 30,
      "official_source_url": "https://...gov... (specific page URL)",
      "vfsglobal_url": "https://visa.vfsglobal.com/... (if applicable to this step)",
      "required_documents": [
        {{
          "name": "Official Document Name",
          "description": "What this document is, where to get it, and any specific requirements",
          "mandatory": true,
          "typical_validity_days": 365
        }}
      ],
      "important_notes": "Critical information for this step",
      "government_fees": "Specific fees for this step in local currency"
    }}
  ]
}}

Include 5-8 steps covering: preparation, assessment/testing, application submission, documentation, biometrics/medical, processing, and grant.
EVERY step must have 3-6 required_documents with detailed descriptions."""

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

        # Template fallback if AI fully failed
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
            return

        # Attach metadata
        workflow_data["_meta"] = {
            "model_used": model_used,
            "country_key": country_key,
            "service_key": service_key,
            "vfsglobal_url": vfs_url,
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
        verified = await find_verified_workflow(country, service_type)
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
                    "steps": [
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
        "You are an expert immigration consultant AI with deep knowledge of global immigration processes. "
        "You generate accurate, step-by-step immigration workflows based on OFFICIAL government requirements "
        "and VFSglobal application centre procedures (for Indian applicants). "
        "You must return ONLY valid JSON, no markdown, no extra text. "
        "Every step MUST have at least 3 required documents. Include all documents that an applicant would need."
    )

    base_prompt = f"""Generate a COMPREHENSIVE immigration workflow for: {request.country} - {request.service_type}

{enrichment_block}
{f"Additional Instructions: {request.custom_instructions}" if request.custom_instructions else ""}

CRITICAL RULES:
1. At least 5 steps. Every step MUST have at least 3 required_documents.
2. Include specific document names as used by the government (e.g., "Form 80 - Personal Particulars")
3. Include ALL fees in local currency based on current official government fee schedules
4. Reference only official government websites (.gov / official portals) AND VFSglobal for application submission step
5. Be thorough — passport, photos, police clearances, medical exams, financial evidence, biometrics, etc.
6. For AU/NZ PR ONLY: include "Skills Assessment" as first or second step (mandatory). For all OTHER workflows, DO NOT include a skills assessment step.

Return a JSON object with this EXACT structure:
{{
  "product_name": "Country - Visa Type with Subclass Number",
  "description": "Brief description of this immigration pathway",
  "category": "immigration",
  "estimated_total_duration_days": 180,
  "estimated_government_fees": "Complete fee breakdown in local currency (application fee + biometrics + medical + skills assessment + language test)",
  "success_tips": ["tip1", "tip2", "tip3"],
  "common_rejection_reasons": ["reason1", "reason2"],
  "steps": [
    {{
      "step_name": "Step Name",
      "step_order": 1,
      "description": "Detailed description of what happens in this step",
      "duration_days": 30,
      "official_source_url": "https://...gov... (specific page URL)",
      "vfsglobal_url": "https://visa.vfsglobal.com/... (if applicable to this step)",
      "required_documents": [
        {{
          "name": "Official Document Name",
          "description": "What this document is, where to get it, and any specific requirements",
          "mandatory": true,
          "typical_validity_days": 365
        }}
      ],
      "important_notes": "Critical information for this step",
      "government_fees": "Specific fees for this step in local currency"
    }}
  ]
}}

Include 5-8 steps covering: preparation, assessment/testing, application submission, documentation, biometrics/medical, processing, and grant.
EVERY step must have 3-6 required_documents with detailed descriptions."""

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
    """Save an AI-generated workflow as a new product"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    product = {
        "id": str(uuid.uuid4()),
        "name": request.product_name,
        "description": request.description,
        "category": request.category or "immigration",
        "base_fee": request.base_fee,
        "commission_rate": request.commission_rate,
        "commission_type": "percentage",
        "status": "active",
        "ai_generated": True,
        "created_at": datetime.now(timezone.utc)
    }
    await products_col.insert_one(product)
    
    saved_steps = []
    for step_data in request.steps:
        step = {
            "id": str(uuid.uuid4()),
            "product_id": product["id"],
            "step_name": step_data.get("step_name", ""),
            "step_order": step_data.get("step_order", 0),
            "description": step_data.get("description", ""),
            "duration_days": step_data.get("duration_days", 7),
            "required_documents": step_data.get("required_documents", []),
            "important_notes": step_data.get("important_notes", ""),
            "government_fees": step_data.get("government_fees", "")
        }
        await workflow_steps_col.insert_one(step)
        saved_steps.append({"id": step["id"], "step_name": step["step_name"]})
    
    await log_activity(current_user["id"], current_user["name"], "saved_ai_workflow", "product",
                       product["id"], f"Saved AI workflow as product: {request.product_name} with {len(saved_steps)} steps")
    
    return {
        "product_id": product["id"],
        "product_name": request.product_name,
        "steps_created": len(saved_steps),
        "message": "Workflow saved as product successfully"
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

