"""Statutory Document Standards Service for LEAMSS.

Provides authoritative, legally precise document nomenclature, form numbers,
issuing authorities, Hague Apostille / consular legalization standards,
certified sworn translation mandates, and validity windows across all
countries and visa categories in the AI Workflow Builder.
"""

import re
from typing import Any, Dict, List, Optional


# Authoritative Global & Country-Specific Statutory Document Definitions
DOCUMENT_STANDARDS = {
    # ── Universal / Multilateral Documents ─────────────────────────────────────
    "passport": {
        "canonical_name": "Valid National Biometric Passport (Bio Page & All Stamped Pages)",
        "description": (
            "Original international biometric passport with minimum 6 months remaining validity "
            "beyond the intended date of grant/departure and at least 2 consecutive blank visa pages. "
            "Full colour high-resolution scan of personal particulars page, amendment pages, and all "
            "prior entry/exit clearance stamps and active/expired visas."
        ),
        "typical_validity_days": 180,
        "mandatory": True,
        "doc_type": "passport",
    },
    "photo": {
        "canonical_name": "Recent Passport-Sized Biometric Photographs (ICAO Standard)",
        "description": (
            "Recent (taken within the last 6 months) identical colour photographs on plain white or "
            "light neutral background, 35mm x 45mm (or 2x2 inches for US), neutral facial expression, "
            "eyes open and clearly visible, strictly compliant with international ICAO biometric photo standards."
        ),
        "typical_validity_days": 180,
        "mandatory": True,
        "doc_type": "photo",
    },
    "birth_certificate": {
        "canonical_name": "Full Birth Certificate with Parental Particulars",
        "description": (
            "Official municipal or civil registry birth certificate showing names of both parents. "
            "If originating outside the destination country, must bear a Hague Apostille (from Ministry "
            "of External Affairs / designated state authority) or Consular Legalization, accompanied by an "
            "accredited certified sworn translation into the official language of the destination country."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "legal",
    },
    "marriage_certificate": {
        "canonical_name": "Official Marriage Certificate / Civil Partnership Registration",
        "description": (
            "Government-issued civil marriage certificate or registered partnership certificate. "
            "For foreign documents, mandatory Hague Apostille authentication or consular legalization, "
            "supported by an accredited certified sworn translation. For de facto relationships, comprehensive "
            "cohabitation evidence covering 12 consecutive months (joint lease, joint bank accounts, statutory declarations)."
        ),
        "typical_validity_days": None,
        "mandatory": False,
        "doc_type": "legal",
    },
    "police_certificate": {
        "canonical_name": "Police Clearance Certificate (PCC) / National Criminal Record Search",
        "description": (
            "Official Police Clearance Certificate issued by Passport Seva Kendra (PSK) / Ministry of External "
            "Affairs (for India) or the national central police registry of each country resided in for 12+ months "
            "since age 16. Must be apostilled or legalized where applicable, and accompanied by a sworn certified "
            "translation. Must be issued within 6 to 12 months of application lodgement."
        ),
        "typical_validity_days": 180,
        "mandatory": True,
        "doc_type": "legal",
    },
    "medical_exam": {
        "canonical_name": "Immigration Health Examination & Medical Clearance Record (eMedical / Panel Doctor)",
        "description": (
            "Comprehensive immigration medical examination, chest X-ray for tuberculosis screening, and mandatory "
            "serological/pathology tests conducted exclusively by an officially designated panel physician / Bupa Medical "
            "Visa Services clinic. Associated with official electronic referral ID (e.g. HAP ID, IME, or eMedical ref). "
            "Strictly valid for 12 months from the examination date."
        ),
        "typical_validity_days": 365,
        "mandatory": True,
        "doc_type": "medical",
    },
    "education_degree": {
        "canonical_name": "Official Degree / Diploma Parchments & Consolidated Academic Transcripts",
        "description": (
            "Original graduation degree parchments and complete semester-wise / year-wise official academic "
            "transcripts indicating subjects taken, credit values, and grading criteria from an accredited university. "
            "Accompanied by educational credential assessment / recognition (e.g. WES, IQAS, ZAB, Anabin) and certified "
            "sworn translations where the original language is not English or the official destination language."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "certificate",
    },
    "employment_reference": {
        "canonical_name": "Statutory Employment Reference Letters & Work Experience Verification Dossier",
        "description": (
            "Formal reference letters on official company letterhead signed by authorized HR or managing director, "
            "detailing exact dates of employment, weekly full-time hours (38+ hrs/week), official job title, "
            "statutory occupation code (ANZSCO/NOC/SOC), and 5+ detailed core duties. Must be corroborated by "
            "official pay slips (minimum 3-6 months per role), Form 16 / Income Tax Returns, and bank salary credit statements."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "legal",
    },
    "english_test": {
        "canonical_name": "Accredited English Language Test Scorecard (PTE / IELTS / TOEFL iBT / OET)",
        "description": (
            "Official scorecard issued by an accredited testing agency proving required proficiency level "
            "(Competent / Proficient / Superior or CEFR B1/B2/C1). Valid for 2 to 3 years from test date depending "
            "on jurisdiction. Scores must be directly verifiable by the immigration department via Pearson, IDP, "
            "British Council, or ETS online verification systems."
        ),
        "typical_validity_days": 1095,
        "mandatory": True,
        "doc_type": "certificate",
    },
    "proof_of_funds": {
        "canonical_name": "Statutory Proof of Financial Means & Bank Settlement Funds Dossier",
        "description": (
            "Official original bank statement or formal balance certificate printed on financial institution letterhead "
            "with branch seal and signature, covering the last 6 consecutive months without large unexplainable deposits. "
            "Must clearly demonstrate unencumbered liquid funds meeting or exceeding statutory subsistence thresholds "
            "(e.g. IRCC settlement funds, UKVI maintenance, or destination statutory minimum)."
        ),
        "typical_validity_days": 30,
        "mandatory": True,
        "doc_type": "financial",
    },
    "residence_application": {
        "canonical_name": "Official Visa & Residence Application Form (RADEX / Ministerial Portal)",
        "description": (
            "Complete statutory application form submitted through the competent national immigration authority's "
            "official electronic portal (e.g. RADEX for Argentina, VIDEX for Germany, ImmiAccount for Australia, "
            "or consular platform). Form must contain verified biographical details, accurate travel history, "
            "and declarations, signed and validated with official confirmation receipt."
        ),
        "typical_validity_days": 90,
        "mandatory": True,
        "doc_type": "application",
    },
    "accommodation_proof": {
        "canonical_name": "Certified Proof of Accommodation / Residential Lease Agreement",
        "description": (
            "Official proof of residential address or accommodation covering the intended period of stay, such as a "
            "registered residential lease agreement, notarized host declaration, hotel/serviced apartment reservation, "
            "or property title deed. Must clearly specify the applicant's name and residential address."
        ),
        "typical_validity_days": 90,
        "mandatory": True,
        "doc_type": "legal",
    },
    "health_insurance": {
        "canonical_name": "Comprehensive International Travel & Health Insurance Policy",
        "description": (
            "Valid international medical and travel insurance policy providing statutory coverage for emergency medical "
            "treatment, hospitalization, repatriation of remains, and urgent medical evacuation for the entire period of stay. "
            "Policy certificate must clearly show the applicant as the named insured and meet destination minimum limits."
        ),
        "typical_validity_days": 365,
        "mandatory": True,
        "doc_type": "other",
    },
    "visa_fee_receipt": {
        "canonical_name": "Official Consular & Statutory Visa Fee Payment Receipt",
        "description": (
            "Official banking or ministerial electronic transaction receipt verifying full settlement of the required "
            "statutory visa application processing fee, consular tariff, and administrative immigration fees."
        ),
        "typical_validity_days": 90,
        "mandatory": True,
        "doc_type": "financial",
    },

    # ── Australia Statutory Forms ──────────────────────────────────────────────
    "form_80": {
        "canonical_name": "Form 80 - Personal Particulars for Character Assessment",
        "description": (
            "Department of Home Affairs statutory character declaration form for all applicants aged 16 and over. "
            "Exhaustive 18-page disclosure of full travel history, residential addresses with no date gaps, "
            "complete employment history, military/government service, and international character questions."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "legal",
    },
    "form_1221": {
        "canonical_name": "Form 1221 - Additional Personal Particulars Information",
        "description": (
            "Department of Home Affairs supplementary disclosure form detailing military service, government "
            "employment, scientific/technical research background, and previous international travel."
        ),
        "typical_validity_days": None,
        "mandatory": False,
        "doc_type": "legal",
    },
    "skills_assessment_au": {
        "canonical_name": "Official Skills Assessment Outcome Letter (Designated Assessing Authority)",
        "description": (
            "Positive outcome assessment letter from the legislated assessing authority for the nominated MLTSSL/STSOL "
            "occupation (e.g. ACS, Engineers Australia, VETASSESS, TRA, ANMAC). Must be valid on the date of SkillSelect "
            "invitation and visa application lodgement."
        ),
        "typical_validity_days": 1095,
        "mandatory": True,
        "doc_type": "certificate",
    },
    "form_1419": {
        "canonical_name": "Form 1419 - Application for General Tourist / Visitor Visa",
        "description": (
            "Official Department of Home Affairs application form for Visitor Visa Subclass 600 Tourist Stream, "
            "accompanied by comprehensive genuine temporary entrant (GTE) evidence and return itinerary."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "application",
    },
    "form_1276": {
        "canonical_name": "Form 1276 - Application for Skilled Migration to Australia",
        "description": (
            "Official electronic lodgement form through ImmiAccount for General Skilled Migration (Subclass 189, 190, 491) "
            "with declaration of points claimed in SkillSelect EOI."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "application",
    },
    "form_47sp": {
        "canonical_name": "Form 47SP - Application for Migration to Australia by a Partner",
        "description": (
            "Statutory primary application form for onshore/offshore Partner Visa (Subclass 820/801 or 309/100) "
            "lodged via ImmiAccount detailing relationship history across financial, household, and social pillars."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "application",
    },
    "form_40sp": {
        "canonical_name": "Form 40SP - Sponsorship for a Partner to Migrate to Australia",
        "description": (
            "Official sponsorship application lodged by the Australian citizen, permanent resident, or eligible New Zealand "
            "citizen partner, including Australian Federal Police (AFP) clearance and character disclosures."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "application",
    },

    # ── Canada Statutory Forms (IRCC) ──────────────────────────────────────────
    "imm_0008": {
        "canonical_name": "IMM 0008 - Generic Application Form for Canada",
        "description": (
            "Official IRCC permanent residence application form with 2D barcode generation, validated and signed "
            "electronically through the permanent residence online portal."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "application",
    },
    "imm_5406": {
        "canonical_name": "IMM 5406 - Additional Family Information",
        "description": (
            "Statutory IRCC declaration listing spouse/common-law partner, parents, all children (biological, adopted, "
            "step), and all siblings with complete full names in native script, dates of birth, and current residential addresses."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "legal",
    },
    "imm_5669": {
        "canonical_name": "IMM 5669 Schedule A - Background / Declaration",
        "description": (
            "Statutory IRCC personal history disclosure covering all post-secondary education, military/civil defence service, "
            "government positions, political affiliations, and complete employment history with ZERO gaps in time since age 18."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "legal",
    },
    "imm_5562": {
        "canonical_name": "IMM 5562 - Supplementary Information: Your Travels",
        "description": (
            "Exhaustive chronological travel history form detailing all international trips taken outside home country "
            "in the past 10 years by principal applicant and all accompanying family members."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "legal",
    },
    "imm_1294": {
        "canonical_name": "IMM 1294 - Application for Study Permit Made Outside of Canada",
        "description": (
            "Official IRCC study permit application form validated with 2D barcodes, submitted alongside provincial attestation "
            "letter (PAL), Designated Learning Institution (DLI) acceptance letter, and GIC financial certificate."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "application",
    },
    "imm_1295": {
        "canonical_name": "IMM 1295 - Application for Work Permit Made Outside of Canada",
        "description": (
            "Official IRCC work permit application form for employer-specific LMIA or LMIA-exempt pathways, "
            "linked with verified employer compliance fee receipt and job offer number."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "application",
    },
    "imm_5257": {
        "canonical_name": "IMM 5257 - Application for Temporary Resident Visa (TRV)",
        "description": (
            "Official IRCC visitor visa application form with validated 2D barcodes, submitted online via the IRCC portal "
            "accompanied by comprehensive proof of home ties, itinerary, and financial support."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "application",
    },
    "eca_report": {
        "canonical_name": "Educational Credential Assessment (ECA) Report (WES / IQAS / ICAS / CES)",
        "description": (
            "Official ECA report from an IRCC-designated assessing organization evaluating foreign educational credentials "
            "against Canadian standards. Strictly valid for 5 years from date of issuance."
        ),
        "typical_validity_days": 1825,
        "mandatory": True,
        "doc_type": "certificate",
    },

    # ── United Kingdom Statutory Requirements ──────────────────────────────────
    "uk_cos": {
        "canonical_name": "Certificate of Sponsorship (CoS) & UKVI Application Summary",
        "description": (
            "Official Certificate of Sponsorship reference number issued by a licensed UKVI A-rated sponsor, "
            "confirming occupation code (SOC 2020), eligible statutory salary rate, and approved sponsorship status."
        ),
        "typical_validity_days": 90,
        "mandatory": True,
        "doc_type": "legal",
    },
    "uk_tb_test": {
        "canonical_name": "Tuberculosis (TB) Screening Certificate (UKVI Approved Clinic)",
        "description": (
            "Official medical certificate verifying chest X-ray clearance issued by an International Organization for "
            "Migration (IOM) or UKVI-approved medical clinic in India or resident country. Valid for 6 months."
        ),
        "typical_validity_days": 180,
        "mandatory": True,
        "doc_type": "medical",
    },
    "uk_atas": {
        "canonical_name": "Academic Technology Approval Scheme (ATAS) Clearance Certificate",
        "description": (
            "Statutory clearance certificate issued by the Foreign, Commonwealth & Development Office (FCDO) "
            "for study or research in sensitive advanced science and technology subjects."
        ),
        "typical_validity_days": 180,
        "mandatory": False,
        "doc_type": "certificate",
    },

    # ── United States Statutory Forms ──────────────────────────────────────────
    "ds_160": {
        "canonical_name": "Form DS-160 - Online Nonimmigrant Visa Application Confirmation",
        "description": (
            "Official barcode confirmation page generated upon submission of the online DS-160 via CEAC portal, "
            "with matching MRV fee receipt and scheduled visa appointment confirmation at the US Embassy/Consulate."
        ),
        "typical_validity_days": 365,
        "mandatory": True,
        "doc_type": "application",
    },
    "i_129_approval": {
        "canonical_name": "Form I-797 Notice of Action (Form I-129 Nonimmigrant Worker Approval)",
        "description": (
            "Official USCIS Form I-797 Notice of Action confirming approval of employer petition Form I-129, "
            "including certified Department of Labor LCA Form ETA-9035, validity period, and consular notification."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "visa",
    },
    "i_20": {
        "canonical_name": "Form I-20 - Certificate of Eligibility for Nonimmigrant Student Status",
        "description": (
            "Official SEVP-endorsed Form I-20 issued by the Designated School Official (DSO) at an accredited US institution, "
            "with paid SEVIS I-901 fee receipt and verified financial capability documentation."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "academic",
    },

    "sworn_declaration": {
        "canonical_name": "Sworn Statutory Declaration / Formal Legal Affidavit",
        "description": (
            "Legally binding sworn statutory declaration or formal affidavit executed before a licensed notary public, "
            "magistrate, or consular officer, affirming required statutory statements (e.g. absence of international criminal record, "
            "financial dependency, or legal custody)."
        ),
        "typical_validity_days": 180,
        "mandatory": True,
        "doc_type": "legal",
    },
    "flight_itinerary": {
        "canonical_name": "Confirmed Flight Reservation & Round-Trip Travel Itinerary",
        "description": (
            "Verifiable round-trip airline booking reservation or travel itinerary showing passenger name, flight numbers, "
            "entry/exit dates, and booking reference (PNR) aligned with the visa validity period requested."
        ),
        "typical_validity_days": 90,
        "mandatory": True,
        "doc_type": "travel",
    },
    "invitation_letter": {
        "canonical_name": "Official Notarized Letter of Invitation & Sponsorship Guarantee",
        "description": (
            "Formal notarized invitation letter from the host, institution, or sponsor specifying applicant details, "
            "relationship, exact duration of stay, accommodation guarantee, and financial responsibility."
        ),
        "typical_validity_days": 180,
        "mandatory": False,
        "doc_type": "legal",
    },
    "consular_appointment": {
        "canonical_name": "Official Consular / VFS Biometrics Appointment Confirmation Receipt",
        "description": (
            "Official booking confirmation voucher and QR code receipt issued by the consular authority or authorized "
            "visa application centre (VFS Global / TLScontact) for biometric enrollment and document lodgement."
        ),
        "typical_validity_days": 90,
        "mandatory": True,
        "doc_type": "appointment",
    },
    "work_activity_dossier": {
        "canonical_name": "Evidentiary Documentation of Professional / Employment Activity & Tax Compliance",
        "description": (
            "Comprehensive dossier substantiating ongoing employment, remote digital nomad contracts, registered business "
            "ownership, professional credentials, and tax returns (Form 16 / ITR) covering the statutory qualifying period."
        ),
        "typical_validity_days": None,
        "mandatory": True,
        "doc_type": "legal",
    },
}


FOREIGN_INDICATORS = {
    # Spanish
    "pasaporte", "válido", "valido", "vigente", "solicitud", "residencia", "documentación", "documentacion",
    "acreditativa", "actividad", "laboral", "antecedentes", "penales", "médico", "medico", "médica", "medica",
    "nacimiento", "matrimonio", "partida", "acta", "alojamiento", "domicilio", "arancel", "tasa", "retributiva",
    "ingresos", "fondos", "seguro", "declaración", "declaracion", "jurada", "título", "titulo", "extranjero",
    "traducción", "traduccion", "correspondiente", "comprobante", "viaje", "visado", "titular", "estudio",
    "estudios", "trabajo", "cuenta", "bancaria", "bancario", "económicos", "economicos", "certificación",
    "certificacion", "apostilla", "apostillado", "legalizado", "legalizada", "trámite", "tramite", "radicación",
    "radicacion", "permanente", "temporaria", "consulado", "embajada", "migraciones", "policial", "penal",
    "constancia", "recibo", "sueldo", "empleo", "haberes", "alquiler", "padrón", "padron", "turno", "cita",
    # French
    "passeport", "demande", "casier", "judiciaire", "hébergement", "hebergement", "attestation", "justificatif",
    "relevé", "releve", "bancaire", "séjour", "sejour", "titre", "identité", "identite", "acte", "naissance",
    "mariage", "frais", "ambassade",
    # German
    "reisepass", "antrag", "führungszeugnis", "fuehrungszeugnis", "wohnungsgeber", "nachweis", "bescheinigung",
    "aufenthaltstitel", "visum", "antragsteller", "finanzierungsnachweis", "krankenversicherung", "gebühr",
    # Italian & Portuguese
    "passaporto", "requerimento", "permesso", "soggiorno", "certificato", "dichiarazione", "alloggio",
    "nascita", "certidão", "certidao", "estrangeiro"
}


def is_foreign_text(text: str) -> bool:
    if not text:
        return False
    # Check for non-standard Latin accent marks heavily indicative of Romance/Germanic official text
    if re.search(r'[áéíóúüñÁÉÍÓÚÜÑçÇàèìòùÀÈÌÒÙäöüÄÖÜß]', str(text)):
        return True
    words = set(re.findall(r'[a-zA-Z]+', str(text).lower()))
    return bool(words & FOREIGN_INDICATORS)


def _match_standard_key(name: str) -> Optional[str]:
    """Map any input document name/phrase to a canonical statutory standard key."""
    n = name.lower().strip()

    # Form code exact matches
    if "form 80" in n or "form_80" in n:
        return "form_80"
    if "form 1221" in n or "form_1221" in n:
        return "form_1221"
    if "form 1419" in n:
        return "form_1419"
    if "form 1276" in n:
        return "form_1276"
    if "form 47sp" in n or "47sp" in n:
        return "form_47sp"
    if "form 40sp" in n or "40sp" in n:
        return "form_40sp"
    if "imm 0008" in n or "imm0008" in n:
        return "imm_0008"
    if "imm 5406" in n or "imm5406" in n:
        return "imm_5406"
    if "imm 5669" in n or "imm5669" in n:
        return "imm_5669"
    if "imm 5562" in n or "imm5562" in n:
        return "imm_5562"
    if "imm 1294" in n or "imm1294" in n:
        return "imm_1294"
    if "imm 1295" in n or "imm1295" in n:
        return "imm_1295"
    if "imm 5257" in n or "imm5257" in n:
        return "imm_5257"
    if "ds-160" in n or "ds 160" in n:
        return "ds_160"
    if "i-129" in n or "i-797" in n or "lca" in n:
        return "i_129_approval"
    if "i-20" in n or "form i-20" in n:
        return "i_20"
    if "certificate of sponsorship" in n or "cos" in n:
        return "uk_cos"
    if "tb test" in n or "tuberculosis" in n:
        return "uk_tb_test"
    if "atas" in n:
        return "uk_atas"

    # Multilingual & Category concepts (Spanish, French, German, Italian, English)
    if any(k in n for k in ["solicitud", "residencia", "residence application", "application form", "antrag", "demande de visa", "radex", "videx", "visa application form", "formulario de solicitud", "trámite de radicación", "tramite de radicacion", "radicación", "radicacion"]):
        return "residence_application"
    if any(k in n for k in ["alojamiento", "domicilio", "accommodation", "lease agreement", "rental agreement", "hébergement", "wohnungsgeber", "alloggio", "alquiler"]):
        return "accommodation_proof"
    if any(k in n for k in ["seguro médico", "seguro de salud", "health insurance", "insurance policy", "assurance voyage", "krankenversicherung", "assicurazione", "seguro"]):
        return "health_insurance"
    if any(k in n for k in ["tasa retributiva", "arancel", "fee payment", "fee receipt", "consular fee", "frais de visa", "gebühr", "comprobante de pago", "tasa"]):
        return "visa_fee_receipt"
    if any(k in n for k in ["photo", "photograph", "picture", "specifications", "foto carnet", "fotografía", "fotografia", "foto"]):
        return "photo"
    if any(k in n for k in ["passport", "travel document", "pasaporte", "passeport", "reisepass", "passaporto", "viaje"]):
        return "passport"
    if any(k in n for k in ["birth certificate", "birth proof", "partida de nacimiento", "acta de nacimiento", "acte de naissance", "geburtsurkunde", "nacimiento"]):
        return "birth_certificate"
    if any(k in n for k in ["marriage certificate", "marriage/relationship", "relationship evidence", "de facto", "partida de matrimonio", "acta de matrimonio", "acte de mariage", "heiratsurkunde", "matrimonio"]):
        return "marriage_certificate"
    if any(k in n for k in ["police clearance", "pcc", "criminal record", "penales", "police certificate", "antecedentes", "casier judiciaire", "führungszeugnis", "carencia de antecedentes", "policial"]):
        return "police_certificate"
    if any(k in n for k in ["medical exam", "health examination", "hap id", "ime", "bupa panel", "chest x-ray", "certificado médico", "certificado medico", "médica", "medica", "médico", "medico", "certificat médical", "ärztliches", "salud"]):
        return "medical_exam"
    if any(k in n for k in ["skills assessment", "skill assessment", "assessment outcome", "anzsco assessment"]):
        return "skills_assessment_au"
    if any(k in n for k in ["eca report", "credential assessment", "wes report"]):
        return "eca_report"
    if any(k in n for k in ["degree certificate", "education certificate", "academic transcript", "diploma", "título", "titulo", "titulacion", "diplôme", "zeugnis", "estudios", "universitario", "analítico"]):
        return "education_degree"
    if any(k in n for k in ["employment evidence", "reference letter", "employment reference", "experience letter", "job description", "pay slip", "payslip", "actividad laboral", "acreditativa", "laboral", "empleo", "contrato de trabajo", "travail", "arbeitsvertrag", "recibo de sueldo", "haberes", "trabajo", "actividad"]):
        return "work_activity_dossier"
    if any(k in n for k in ["english test", "pte", "ielts", "toefl", "oet", "language test"]):
        return "english_test"
    if any(k in n for k in ["proof of funds", "bank statement", "settlement funds", "financial means", "bank letter", "medios económicos", "medios economicos", "fondos", "ingresos", "recursos", "ressources", "extracto bancario", "cuenta bancaria", "resumen de cuenta"]):
        return "proof_of_funds"
    if any(k in n for k in ["declaración jurada", "declaracion jurada", "jurada", "affidavit", "statutory declaration"]):
        return "sworn_declaration"
    if any(k in n for k in ["vuelo", "pasaje", "billete", "itinerario", "flight", "itinerary", "airline"]):
        return "flight_itinerary"
    if any(k in n for k in ["invitación", "invitacion", "carta de invitación", "carta de invitacion", "invitation", "sponsorship letter"]):
        return "invitation_letter"
    if any(k in n for k in ["turno", "cita", "appointment", "rendez-vous"]):
        return "consular_appointment"

    return None


def enrich_step_document(country_name: str, doc: Any, step_name: str = "") -> Dict[str, Any]:
    """Enrich a document entry with precise official nomenclature and statutory specs strictly in English."""
    if isinstance(doc, dict):
        raw_name = doc.get("name") or doc.get("doc_name") or ""
        doc_id = doc.get("doc_id") or ""
        desc = doc.get("description") or doc.get("notes") or ""
        mandatory = doc.get("mandatory", doc.get("is_mandatory", True))
        validity = doc.get("typical_validity_days")
    else:
        raw_name = str(doc).strip()
        doc_id = ""
        desc = ""
        mandatory = True
        validity = None

    matched_key = _match_standard_key(raw_name)

    # Country-specific form rules
    c_lower = (country_name or "").lower()
    if "australia" in c_lower:
        if "character" in raw_name.lower() or "personal particulars" in raw_name.lower():
            matched_key = "form_80"
        elif "form for pcc" in raw_name.lower() or "address proof" in raw_name.lower():
            matched_key = "police_certificate"
    elif "canada" in c_lower:
        if "family information" in raw_name.lower():
            matched_key = "imm_5406"
        elif "background declaration" in raw_name.lower() or "schedule a" in raw_name.lower():
            matched_key = "imm_5669"

    if matched_key and matched_key in DOCUMENT_STANDARDS:
        std = DOCUMENT_STANDARDS[matched_key]
        canonical_name = std["canonical_name"]
        
        # If raw_name is foreign or generic, ALWAYS use the canonical English name
        if is_foreign_text(raw_name) or len(raw_name) < 14 or raw_name.lower() in [
            "passport", "photo", "birth certificate", "birth certificates", "address proof",
            "form for pcc application", "passport for id at clinic", "passport for id at test centre",
            "grant notice (printed)", "passport bio page (all applicants)", "photo (passport size, recent)"
        ]:
            final_name = canonical_name
        else:
            final_name = raw_name

        # If description is empty or too short or in foreign language, apply statutory standard description in English
        final_desc = std["description"] if (len(desc.strip()) < 35 or is_foreign_text(desc)) else desc
        final_validity = validity or std.get("typical_validity_days")
        final_mandatory = mandatory if mandatory is not None else std.get("mandatory", True)

        return {
            "doc_id": doc_id,
            "name": final_name,
            "description": final_desc,
            "mandatory": bool(final_mandatory),
            "typical_validity_days": final_validity,
            "notes": final_desc,
            "doc_type": std.get("doc_type", "legal")
        }

    # If no exact standard key, but title contains foreign words, replace with English title
    if is_foreign_text(raw_name):
        final_name = "Official Regulatory Dossier & Evidentiary Documentation (Sworn English Translation)"
    else:
        final_name = raw_name

    final_desc = desc if (len(desc.strip()) >= 30 and not is_foreign_text(desc)) else (
        f"Official document issued by competent authority in {country_name or 'destination jurisdiction'}. "
        f"Must comply with destination government authentication rules (Hague Apostille / Consular Legalization) "
        f"and include an accredited certified sworn translation where applicable."
    )

    return {
        "doc_id": doc_id,
        "name": final_name,
        "description": final_desc,
        "mandatory": bool(mandatory),
        "typical_validity_days": validity,
        "notes": final_desc,
        "doc_type": "legal"
    }


def enrich_workflow_steps(
    country_name: str,
    steps: List[dict],
    service_type: str = "",
    subclass_id: Optional[str] = None
) -> List[dict]:
    """Pass all workflow steps through statutory document enrichment.
    
    Also normalizes foreign step titles and descriptions strictly to English,
    and injects official statutory forms into lodgement steps if missing.
    """
    enriched_steps = []
    c_lower = (country_name or "").lower()
    s_lower = (service_type or "").lower()

    for idx, step in enumerate(steps or []):
        s = dict(step)
        raw_step_title = s.get("step_name") or s.get("title") or f"Step {idx+1}"
        step_title = raw_step_title
        if is_foreign_text(raw_step_title):
            t_low = raw_step_title.lower()
            if any(k in t_low for k in ["solicitud", "demande", "antrag", "radex", "presentación", "presentacion"]):
                step_title = "Application Lodgement & Official Electronic Submission"
            elif any(k in t_low for k in ["documentaci", "legalizaci", "apostil", "traducc", "unterlagen", "preparaci"]):
                step_title = "Document Legalization, Sworn Translation & Evidentiary Dossier"
            elif any(k in t_low for k in ["biom", "huella", "visado", "cita", "turno", "consular"]):
                step_title = "Biometric Appointment & Consular Verification"
            elif any(k in t_low for k in ["entrada", "llegada", "einreise", "arribo"]):
                step_title = "Entry to Destination & Arrival Formalities"
            elif any(k in t_low for k in ["dni", "tarjeta", "permiso", "abholung", "resoluci", "concesi"]):
                step_title = "Residence Permit Grant & National ID Registration"
            else:
                step_title = f"Procedural Stage {idx+1} - Statutory Compliance & Requirements"
        s["step_name"] = step_title

        if is_foreign_text(s.get("description", "")):
            s["description"] = f"Complete the statutory requirements for this phase according to the destination country's official government immigration regulations."

        if "important_notes" in s and is_foreign_text(s["important_notes"]):
            s["important_notes"] = "Ensure all documents originating outside the destination country bear Hague Apostille authentication and certified sworn translation."

        raw_docs = s.get("required_documents") or s.get("documents_needed") or []

        enriched_docs = []
        doc_names_lower = []
        for d in raw_docs:
            ed = enrich_step_document(country_name, d, step_title)
            enriched_docs.append(ed)
            doc_names_lower.append(ed["name"].lower())

        # Statutory form injection for actual visa application lodgement steps
        st_low = step_title.lower()
        is_lodge_step = (
            "e-apr" in st_low
            or "lodge" in st_low
            or "application submission" in st_low
            or ("submit" in st_low and "application" in st_low)
            or ("filing" in st_low and "application" in st_low)
            or ("file" in st_low and "visa" in st_low)
            or ("visa" in st_low and "application" in st_low and "submit" in st_low)
        ) and not any(k in st_low for k in ["eoi", "invitation", "skill assessment", "english", "health", "police", "initial entry", "landing", "decision", "grant", "profile creation", "language testing"])

        if is_lodge_step:
            # Australia PR / Work: Form 80 and Form 1221
            if "australia" in c_lower and ("pr" in s_lower or "189" in str(subclass_id) or "190" in str(subclass_id) or "491" in str(subclass_id) or "482" in s_lower):
                if not any("form 80" in n for n in doc_names_lower):
                    enriched_docs.append(enrich_step_document("Australia", "Form 80 - Personal Particulars for Character Assessment", step_title))
                if not any("form 1221" in n for n in doc_names_lower):
                    enriched_docs.append(enrich_step_document("Australia", "Form 1221 - Additional Personal Particulars Information", step_title))

            # Canada PR / Express Entry: IMM 5406 and IMM 5669
            elif "canada" in c_lower and ("pr" in s_lower or "express" in s_lower):
                if not any("5406" in n for n in doc_names_lower):
                    enriched_docs.append(enrich_step_document("Canada", "IMM 5406 - Additional Family Information", step_title))
                if not any("5669" in n for n in doc_names_lower):
                    enriched_docs.append(enrich_step_document("Canada", "IMM 5669 Schedule A - Background / Declaration", step_title))

            # USA: Form DS-160
            elif "united states" in c_lower or "usa" in c_lower or c_lower == "us":
                if not any("ds-160" in n for n in doc_names_lower) and not any("i-140" in n for n in doc_names_lower):
                    enriched_docs.append(enrich_step_document("USA", "Form DS-160 - Online Nonimmigrant Visa Application Confirmation", step_title))

        s["required_documents"] = enriched_docs
        enriched_steps.append(s)

    return enriched_steps


def sanitize_workflow_to_english(
    workflow_data: Dict[str, Any],
    country_name: str = "",
    service_type: str = "",
    subclass_id: Optional[str] = None
) -> Dict[str, Any]:
    """Ensure every single text field of a generated workflow is 100% in English."""
    if not isinstance(workflow_data, dict):
        return workflow_data

    # Product Name
    pname = workflow_data.get("product_name") or ""
    if is_foreign_text(pname) or not pname:
        workflow_data["product_name"] = f"{country_name} - {service_type or 'Official Visa Pathway'}"

    # Description
    desc = workflow_data.get("description") or ""
    if is_foreign_text(desc) or len(desc.strip()) < 30:
        workflow_data["description"] = (
            f"Official statutory immigration pathway for {country_name}. "
            f"Governed strictly by destination immigration regulations, requiring verified legal documentation, "
            f"statutory form submissions, Hague Apostille authentication, and accredited sworn translations."
        )

    # Success Tips
    tips = workflow_data.get("success_tips") or []
    cleaned_tips = []
    canonical_english_tips = [
        "Ensure all civil and educational documents originating abroad bear Hague Apostille authentication and certified sworn translation.",
        "Maintain clean, stamped bank statements verifying required subsistence settlement funds for the entire mandated period.",
        "Double-check that all applicant biographical particulars across all statutory forms strictly match the international passport bio-data page.",
        "Attend panel medical examinations and consular biometrics promptly upon receiving official appointment referral vouchers."
    ]
    for i, tip in enumerate(tips):
        if is_foreign_text(str(tip)) or len(str(tip).strip()) < 15:
            cleaned_tips.append(canonical_english_tips[i % len(canonical_english_tips)])
        else:
            cleaned_tips.append(str(tip))
    if not cleaned_tips:
        cleaned_tips = canonical_english_tips[:3]
    workflow_data["success_tips"] = cleaned_tips

    # Common Rejection Reasons
    reasons = workflow_data.get("common_rejection_reasons") or []
    cleaned_reasons = []
    canonical_english_reasons = [
        "Failure to submit foreign civil documents with mandatory Hague Apostille authentication or accredited sworn translation.",
        "Insufficient demonstration of genuine statutory subsistence funds or unverified recent lump-sum bank deposits.",
        "Incomplete statutory character/police clearance disclosures or failure to meet mandatory health clearance benchmarks.",
        "Discrepancies in employment references or inability to verify employer tax compliance."
    ]
    for i, r in enumerate(reasons):
        if is_foreign_text(str(r)) or len(str(r).strip()) < 15:
            cleaned_reasons.append(canonical_english_reasons[i % len(canonical_english_reasons)])
        else:
            cleaned_reasons.append(str(r))
    if not cleaned_reasons:
        cleaned_reasons = canonical_english_reasons[:3]
    workflow_data["common_rejection_reasons"] = cleaned_reasons

    # Estimated Fees
    fees = workflow_data.get("estimated_government_fees") or ""
    if is_foreign_text(str(fees)):
        workflow_data["estimated_government_fees"] = f"Official statutory visa application and consular processing fees per current ministerial tariffs in {country_name}."

    # Steps & Step Documents
    if "steps" in workflow_data:
        workflow_data["steps"] = enrich_workflow_steps(
            country_name,
            workflow_data.get("steps", []),
            service_type,
            subclass_id
        )

    # Flat Document Checklist (if present)
    if "document_checklist" in workflow_data and isinstance(workflow_data["document_checklist"], list):
        cleaned_checklist = []
        for item in workflow_data["document_checklist"]:
            cleaned_checklist.append(enrich_step_document(country_name, item))
        workflow_data["document_checklist"] = cleaned_checklist

    return workflow_data
