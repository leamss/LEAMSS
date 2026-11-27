"""Country-wise Regulatory Authorities, Official Government Portals, and VFS Global Mapping.

Provides official destination government immigration authorities, direct ministerial URLs,
VFS Global application center URLs, statutory government forms (strictly in English),
and visa streams for 45+ destination countries.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

COUNTRY_REGULATORY_AUTHORITIES: Dict[str, Dict[str, Any]] = {
    "australia": {
        "country_name": "Australia",
        "country_code": "AU",
        "authority_name": "Department of Home Affairs (DHA)",
        "official_portal_url": "https://immi.homeaffairs.gov.au",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/",
        "official_forms": [
            {"form_id": "form_80", "name": "Form 80 - Personal Particulars for Assessment", "description": "Detailed personal history including travel, employment, education, and character assessment", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/80.pdf", "applies_to": ["189", "190", "491", "482", "500", "pr", "work"], "category": "application", "mandatory": True},
            {"form_id": "form_1221", "name": "Form 1221 - Additional Personal Particulars", "description": "Supplementary personal details and travel background form", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1221.pdf", "applies_to": ["189", "190", "491", "pr"], "category": "application", "mandatory": False},
            {"form_id": "form_1393", "name": "Form 1393 - Application for Migration by a Skilled Worker", "description": "Main application form for skilled migration visa subclasses", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1393.pdf", "applies_to": ["189", "190", "491", "pr"], "category": "application", "mandatory": True},
            {"form_id": "form_1276", "name": "Form 1276 - Application for a Student Visa", "description": "Application form for Student Visa Subclass 500", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1276.pdf", "applies_to": ["500", "student"], "category": "application", "mandatory": True},
            {"form_id": "form_1419", "name": "Form 1419 - Application for a Visitor Visa", "description": "Application form for Visitor Visa Subclass 600", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1419.pdf", "applies_to": ["600", "visitor"], "category": "application", "mandatory": True},
            {"form_id": "form_26", "name": "Form 26 - Medical Examination for Visa Applicant", "description": "Health examination form completed by a Bupa Medical panel doctor", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/26.pdf", "applies_to": ["189", "190", "491", "482", "500", "600", "pr", "work"], "category": "medical", "mandatory": True},
            {"form_id": "form_160", "name": "Form 160 - Chest X-Ray Referral", "description": "Chest X-ray referral form for statutory health assessment", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/160.pdf", "applies_to": ["189", "190", "491", "500", "pr"], "category": "medical", "mandatory": False},
            {"form_id": "form_956", "name": "Form 956 - Appointment of a Registered Migration Agent", "description": "Authorisation to appoint a registered migration agent (OMARA)", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/956.pdf", "applies_to": ["189", "190", "491", "482", "500", "600"], "category": "agent", "mandatory": False},
            {"form_id": "form_1023", "name": "Form 1023 - Notification of Incorrect Answer(s)", "description": "Notify DHA of incorrect information in previously submitted applications", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1023.pdf", "applies_to": ["189", "190", "491", "482"], "category": "update", "mandatory": False},
            {"form_id": "form_40sp", "name": "Form 40SP - Sponsorship for a Partner to Migrate", "description": "Sponsorship application form for Partner Visa Subclasses 820/801 and 309/100", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/40sp.pdf", "applies_to": ["820", "801", "partner", "family"], "category": "application", "mandatory": True},
            {"form_id": "form_47sp", "name": "Form 47SP - Application for Migration to Australia by a Partner", "description": "Main applicant form for Partner Visa", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/47sp.pdf", "applies_to": ["820", "801", "partner", "family"], "category": "application", "mandatory": True},
            {"form_id": "form_1424", "name": "Form 1424 - Application for Employer Nomination", "description": "Employer nomination form for Subclass 482 / 186 employer-sponsored visas", "url": "https://immi.homeaffairs.gov.au/form-listing/forms/1424.pdf", "applies_to": ["482", "186", "work"], "category": "employer", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "subclass_189", "name": "Skilled Independent Visa (Subclass 189)", "category": "pr", "service_type": "pr", "description": "Points-tested permanent residency for skilled workers not sponsored by an employer or state.", "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189", "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/", "estimated_fees": "AUD 4,770"},
            {"id": "subclass_190", "name": "Skilled Nominated Visa (Subclass 190)", "category": "pr", "service_type": "pr", "description": "State-nominated permanent residency visa for skilled workers.", "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-nominated-190", "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/", "estimated_fees": "AUD 4,770"},
            {"id": "subclass_491", "name": "Skilled Work Regional (Provisional) Visa (Subclass 491)", "category": "pr", "service_type": "pr", "description": "Provisional points-tested visa leading to PR (Subclass 191) after 3 years living in regional Australia.", "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-work-regional-491", "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/", "estimated_fees": "AUD 4,770"},
            {"id": "subclass_482", "name": "Temporary Skill Shortage Visa (Subclass 482 / TSS)", "category": "work", "service_type": "work", "description": "Employer-sponsored work visa across Short-term, Medium-term, and Labour Agreement streams.", "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482", "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/", "estimated_fees": "AUD 3,115 (Medium-term) / AUD 1,490 (Short-term)"},
            {"id": "subclass_500", "name": "Student Visa (Subclass 500)", "category": "student", "service_type": "student", "description": "Study full-time at a registered Australian educational institution (CRICOS).", "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500", "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/", "estimated_fees": "AUD 1,600"},
            {"id": "subclass_600", "name": "Visitor Visa (Subclass 600)", "category": "visitor", "service_type": "visitor", "description": "Tourist and Business Visitor streams for up to 3, 6, or 12 months.", "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/visitor-600", "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/", "estimated_fees": "AUD 192"},
            {"id": "subclass_820_801", "name": "Partner Visa (Subclasses 820 & 801)", "category": "partner", "service_type": "partner", "description": "Combined temporary and permanent visa for spouses or de facto partners of Australian citizens or PRs.", "official_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-onshore-820-801", "vfs_url": "https://visa.vfsglobal.com/ind/en/aus/", "estimated_fees": "AUD 9,095"},
        ],
    },
    "germany": {
        "country_name": "Germany",
        "country_code": "DE",
        "authority_name": "Federal Foreign Office (Auswärtiges Amt) / Federal Employment Agency (BA)",
        "official_portal_url": "https://www.auswaertiges-amt.de",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/deu/",
        "official_forms": [
            {"form_id": "videx_national", "name": "VIDEX National Visa Application Form (Type D)", "description": "Official statutory electronic application form for long-term stay, employment, and study in Germany", "url": "https://videx.diplo.de/videx/desktop/index.html#start", "applies_to": ["work", "blue_card", "student", "jobseeker", "partner", "pr"], "category": "application", "mandatory": True},
            {"form_id": "erkl_beschaeftigung", "name": "Declaration of Employment Relationship (Erklärung zum Beschäftigungsverhältnis)", "description": "Mandatory Federal Employment Agency form completed by German employer detailing job duties, salary, and working hours", "url": "https://www.arbeitsagentur.de/datei/erklaerung-zum-beschaeftigungsverhaeltnis_ba044431.pdf", "applies_to": ["work", "blue_card"], "category": "employer", "mandatory": True},
            {"form_id": "sec_54_declaration", "name": "Declaration of Accuracy of Information (Section 54 (2) No. 8 AufenthG)", "description": "Statutory declaration acknowledging legal consequences of false or incomplete statements under the German Residence Act", "url": "https://india.diplo.de/in-en/service/-/1801264", "applies_to": ["work", "student", "visitor", "partner", "jobseeker"], "category": "legal", "mandatory": True},
            {"form_id": "sec_55_contact", "name": "Contact and Representation Form (Section 55 AufenthG)", "description": "Declaration authorizing consular correspondence and designating legal representatives", "url": "https://india.diplo.de/in-en/service/-/1801264", "applies_to": ["work", "student", "visitor", "partner"], "category": "legal", "mandatory": True},
            {"form_id": "chancenkarte_points_sheet", "name": "Opportunity Card Points Self-Assessment Form (Chancenkarte)", "description": "Official statutory points self-assessment sheet under Section 20a Residence Act for qualified job-seekers", "url": "https://www.make-it-in-germany.com/en/visa-residence/types/jobsearch-opportunity-card", "applies_to": ["jobseeker", "work"], "category": "application", "mandatory": True},
            {"form_id": "verpflichtungserklaerung", "name": "Formal Obligation Letter (Verpflichtungserklärung)", "description": "Official financial sponsorship commitment under Sections 66-68 AufenthG authenticated by German immigration authority", "url": "https://www.auswaertiges-amt.de/en/visa-service/buergerservice/faq/-/606848", "applies_to": ["visitor", "student", "partner"], "category": "financial", "mandatory": False},
        ],
        "visa_streams": [
            {"id": "de_blue_card", "name": "EU Blue Card (Section 18g AufenthG)", "category": "work", "service_type": "work", "description": "Fast-track residence and work permit for university graduates with recognized qualification and qualifying salary threshold.", "official_url": "https://www.make-it-in-germany.com/en/visa-residence/types/eu-blue-card", "vfs_url": "https://visa.vfsglobal.com/ind/en/deu/", "estimated_fees": "EUR 75 (National Visa) + EUR 100 (Residence Permit)"},
            {"id": "de_chancenkarte", "name": "Opportunity Card / Chancenkarte (Section 20a AufenthG)", "category": "work", "service_type": "work", "description": "Points-based job search visa allowing 1 year stay with part-time work and 2-week trial employment permitted.", "official_url": "https://www.make-it-in-germany.com/en/visa-residence/types/jobsearch-opportunity-card", "vfs_url": "https://visa.vfsglobal.com/ind/en/deu/", "estimated_fees": "EUR 75"},
            {"id": "de_skilled_worker", "name": "Skilled Worker with Academic / Vocational Training (Section 18a/18b AufenthG)", "category": "work", "service_type": "work", "description": "Residence permit for professionals with recognized vocational training or university degrees with a binding job offer.", "official_url": "https://www.make-it-in-germany.com/en/visa-residence/types/work-qualified-professionals", "vfs_url": "https://visa.vfsglobal.com/ind/en/deu/", "estimated_fees": "EUR 75"},
            {"id": "de_student", "name": "Student Visa (Section 16b AufenthG)", "category": "student", "service_type": "student", "description": "National visa for full-time degree programs at recognized German universities, requiring blocked account (Sperrkonto).", "official_url": "https://www.auswaertiges-amt.de/en/visa-service/visabestimmungen-node", "vfs_url": "https://visa.vfsglobal.com/ind/en/deu/", "estimated_fees": "EUR 75"},
            {"id": "de_family_reunion", "name": "Family Reunion Visa (Sections 27-36 AufenthG)", "category": "partner", "service_type": "partner", "description": "Residence permit for spouses and minor children of individuals residing legally in Germany.", "official_url": "https://www.make-it-in-germany.com/en/living-in-germany/family-reunification", "vfs_url": "https://visa.vfsglobal.com/ind/en/deu/", "estimated_fees": "EUR 75 (adult) / EUR 37.50 (minor)"},
            {"id": "de_schengen_tourist", "name": "Schengen Short-Stay Visa (Type C Tourist / Business)", "category": "visitor", "service_type": "visitor", "description": "Short-stay tourist or business visit for up to 90 days in any 180-day period.", "official_url": "https://www.auswaertiges-amt.de/en/visa-service/visabestimmungen-node", "vfs_url": "https://visa.vfsglobal.com/ind/en/deu/", "estimated_fees": "EUR 90 (adult) / EUR 45 (child 6-12)"},
        ],
    },
    "france": {
        "country_name": "France",
        "country_code": "FR",
        "authority_name": "France-Visas / Ministry of the Interior and Overseas France",
        "official_portal_url": "https://france-visas.gouv.fr",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/fra/",
        "official_forms": [
            {"form_id": "cerfa_14571", "name": "Cerfa Form No. 14571*05 - Long-Stay Visa Application Form", "description": "Official statutory application form for French National Long-Stay Visa (VLS-TS / VLS)", "url": "https://france-visas.gouv.fr", "applies_to": ["work", "talent_passport", "student", "partner", "pr"], "category": "application", "mandatory": True},
            {"form_id": "cerfa_14076", "name": "Cerfa Form No. 14076*04 - Short-Stay Schengen Visa Application Form", "description": "Official statutory application form for Short-Stay Tourist and Business Visas", "url": "https://france-visas.gouv.fr", "applies_to": ["visitor", "business"], "category": "application", "mandatory": True},
            {"form_id": "ofii_attestation", "name": "OFII Residence Certificate Form (Office Français de l'Immigration)", "description": "Form required for validation and registration of Long-Stay Visa with OFII upon arrival in France", "url": "https://www.ofii.fr", "applies_to": ["work", "talent_passport", "student", "partner"], "category": "registration", "mandatory": True},
            {"form_id": "cerfa_15614", "name": "Cerfa Form No. 15614*04 - Work Authorization Application (Autorisation de Travail)", "description": "Employer application form for foreign employee work authorization submitted on the ANEF online portal", "url": "https://administration-etrangers-en-france.interieur.gouv.fr", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "campus_france_eef", "name": "Campus France EEF Dossier Confirmation Certificate", "description": "Mandatory academic pre-consular authorization certificate for higher education students", "url": "https://www.campusfrance.org", "applies_to": ["student"], "category": "academic", "mandatory": True},
            {"form_id": "attestation_accueil", "name": "Certificate of Board and Lodging (Attestation d'Accueil)", "description": "Town hall (Mairie) stamped accommodation guarantee certificate for private visitors", "url": "https://www.service-public.fr/particuliers/vosdroits/F2191", "applies_to": ["visitor"], "category": "accommodation", "mandatory": False},
        ],
        "visa_streams": [
            {"id": "fr_talent_passport", "name": "Talent Passport / Passeport Talent (Employee / Startup / Artist)", "category": "work", "service_type": "work", "description": "Multi-year residence permit for highly qualified employees, startup founders, investors, and researchers.", "official_url": "https://france-visas.gouv.fr/en/web/france-visas/talent-passport", "vfs_url": "https://visa.vfsglobal.com/ind/en/fra/", "estimated_fees": "EUR 99 (Visa) + EUR 225 (Taxe de séjour)"},
            {"id": "fr_salaried_work", "name": "Long-Stay Work Visa (Salarié / Travailleur Temporaire)", "category": "work", "service_type": "work", "description": "Long-stay employment visa supported by an approved work authorization (Autorisation de Travail).", "official_url": "https://france-visas.gouv.fr/en/web/france-visas/salaried-employment", "vfs_url": "https://visa.vfsglobal.com/ind/en/fra/", "estimated_fees": "EUR 99"},
            {"id": "fr_student_vls", "name": "Long-Stay Student Visa (VLS-TS Étudiant)", "category": "student", "service_type": "student", "description": "Student visa for accredited degree programs in France, processed in conjunction with Campus France.", "official_url": "https://france-visas.gouv.fr/en/web/france-visas/student", "vfs_url": "https://visa.vfsglobal.com/ind/en/fra/", "estimated_fees": "EUR 50 (Visa) + EUR 75 (OFII tax)"},
            {"id": "fr_visitor_schengen", "name": "Short-Stay Tourist / Business Visa (Schengen Type C)", "category": "visitor", "service_type": "visitor", "description": "Tourism, family visit, or business meetings for up to 90 days in France and the Schengen Area.", "official_url": "https://france-visas.gouv.fr/en/web/france-visas/tourism-private-stay", "vfs_url": "https://visa.vfsglobal.com/ind/en/fra/", "estimated_fees": "EUR 90"},
            {"id": "fr_family_reunion", "name": "Spouse of French National / Family Reunion Visa", "category": "partner", "service_type": "partner", "description": "Long-stay visa leading to multi-year residence permit for spouses of French citizens or legal residents.", "official_url": "https://france-visas.gouv.fr/en/web/france-visas/family-purpose", "vfs_url": "https://visa.vfsglobal.com/ind/en/fra/", "estimated_fees": "EUR 99"},
        ],
    },
    "italy": {
        "country_name": "Italy",
        "country_code": "IT",
        "authority_name": "Ministry of Foreign Affairs and International Cooperation (Farnesina) / Ministry of Interior",
        "official_portal_url": "https://vistoperitalia.esteri.it",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/ita/",
        "official_forms": [
            {"form_id": "modulo_visto_nazionale", "name": "National Visa Type D Application Form (Modulo di Domanda Visto D)", "description": "Official statutory Italian application form for long-stay visas exceeding 90 days", "url": "https://vistoperitalia.esteri.it/Moduli/it/Formulario%20Visto%20Nazionale.pdf", "applies_to": ["work", "student", "family", "elective_residence", "pr"], "category": "application", "mandatory": True},
            {"form_id": "modulo_visto_schengen", "name": "Schengen Visa Type C Application Form (Modulo di Domanda Visto Schengen)", "description": "Official application form for short-term tourism and business visits", "url": "https://vistoperitalia.esteri.it/Moduli/it/Formulario%20Visto%20Schengen.pdf", "applies_to": ["visitor", "business"], "category": "application", "mandatory": True},
            {"form_id": "nulla_osta_lavoro", "name": "Work Clearance Authorization Certificate (Nulla Osta al Lavoro)", "description": "Mandatory statutory work authorization issued by the Prefettura (Sportello Unico per l'Immigrazione)", "url": "https://portaleservizi.dlci.interno.it", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "dichiarazione_ospitalita", "name": "Declaration of Hospitality and Lodging Guarantee Form", "description": "Official hospitality certificate and accommodation declaration signed by host in Italy", "url": "https://vistoperitalia.esteri.it", "applies_to": ["visitor", "family"], "category": "accommodation", "mandatory": False},
            {"form_id": "dichiarazione_valore", "name": "Declaration of Value of Academic Qualifications (Dichiarazione di Valore - DoV)", "description": "Consular certification verifying equivalency and authenticity of educational credentials", "url": "https://vistoperitalia.esteri.it", "applies_to": ["student", "work"], "category": "academic", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "it_work_subordinate", "name": "Subordinate Work Visa (Lavoro Subordinato / Decreto Flussi)", "category": "work", "service_type": "work", "description": "Employment visa governed by annual quota decree requiring prior Nulla Osta from Sportello Unico.", "official_url": "https://vistoperitalia.esteri.it/home/en", "vfs_url": "https://visa.vfsglobal.com/ind/en/ita/", "estimated_fees": "EUR 116"},
            {"id": "it_blue_card", "name": "Italy EU Blue Card (Carta Blu UE - Extra Flussi)", "category": "work", "service_type": "work", "description": "Exempt from quota limits for highly skilled workers with university degree and employment contract.", "official_url": "https://vistoperitalia.esteri.it/home/en", "vfs_url": "https://visa.vfsglobal.com/ind/en/ita/", "estimated_fees": "EUR 116"},
            {"id": "it_student", "name": "Study Visa (Studio / Immatricolazione Università)", "category": "student", "service_type": "student", "description": "National visa for university enrolment via Universitaly portal with financial guarantee.", "official_url": "https://vistoperitalia.esteri.it/home/en", "vfs_url": "https://visa.vfsglobal.com/ind/en/ita/", "estimated_fees": "EUR 50"},
            {"id": "it_tourist", "name": "Tourist Visa (Turismo Schengen Type C)", "category": "visitor", "service_type": "visitor", "description": "Short stay tourist travel for leisure and sightseeing for up to 90 days.", "official_url": "https://vistoperitalia.esteri.it/home/en", "vfs_url": "https://visa.vfsglobal.com/ind/en/ita/", "estimated_fees": "EUR 90"},
            {"id": "it_family_reunion", "name": "Family Reunion Visa (Ricongiungimento Familiare)", "category": "partner", "service_type": "partner", "description": "Entry visa for eligible family members of foreign residents holding Italian residence permit.", "official_url": "https://vistoperitalia.esteri.it/home/en", "vfs_url": "https://visa.vfsglobal.com/ind/en/ita/", "estimated_fees": "EUR 116"},
        ],
    },
    "spain": {
        "country_name": "Spain",
        "country_code": "ES",
        "authority_name": "Ministry of Foreign Affairs, European Union and Cooperation (MAEC) / Ministry of Inclusion, Social Security and Migration",
        "official_portal_url": "https://www.exteriores.gob.es",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/esp/",
        "official_forms": [
            {"form_id": "solicitud_visado_nacional", "name": "National Visa Application Form (Formulario de Solicitud de Visado Nacional)", "description": "Official statutory application form for long-term residence, employment, study, and digital nomad visas in Spain", "url": "https://www.exteriores.gob.es/es/ServiciosAlCiudadano/Paginas/Visados-Nacionales.aspx", "applies_to": ["work", "nomad", "student", "golden", "partner", "pr"], "category": "application", "mandatory": True},
            {"form_id": "form_ex_01", "name": "Form EX-01 - Non-Lucrative Temporary Residence Application Form", "description": "Application form for residence without engaging in labor or professional activities", "url": "https://inclusion.seg-social.gob.es/en/web/migraciones/modelos-generales", "applies_to": ["pr", "retiree"], "category": "application", "mandatory": True},
            {"form_id": "form_ex_03", "name": "Form EX-03 - Temporary Residence and Work Permit for Account of Others (Cuenta Ajena)", "description": "Statutory employer application form for employing foreign workers in Spain", "url": "https://inclusion.seg-social.gob.es/en/web/migraciones/modelos-generales", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "tasa_790_052", "name": "Official Fee Payment Form 790 Code 052 (Tasa Modelo 790 Código 052)", "description": "Mandatory administrative fee payment form for initial residence authorization processing", "url": "https://sede.administracionespublicas.gob.es/pagina/index/directorio/tasa052", "applies_to": ["work", "nomad", "student", "partner"], "category": "financial", "mandatory": True},
            {"form_id": "digital_nomad_uge", "name": "Telework Application Protocol Form (UGE-CE Digital Nomad)", "description": "Application protocol under Law 14/2013 for international teleworkers and remote entrepreneurs", "url": "https://prie.comercio.gob.es/es-es/Paginas/Teletrabajadores-Caracter-Internacional.aspx", "applies_to": ["nomad", "work"], "category": "application", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "es_digital_nomad", "name": "Spain Digital Nomad Visa (Ley de Startups 28/2022)", "category": "nomad", "service_type": "work", "description": "Residence visa for non-EEA nationals working remotely for foreign companies or self-employed with maximum 20% Spanish revenue.", "official_url": "https://www.exteriores.gob.es/Consulados/mumbai/en/ServiciosConsulares/Paginas/index.aspx?scco=India&scd=201&scca=Visados&secc=VisadosNacionales", "vfs_url": "https://visa.vfsglobal.com/ind/en/esp/", "estimated_fees": "EUR 80 (Visa) + EUR 73.26 (Tasa 790-038)"},
            {"id": "es_highly_qualified", "name": "Highly Qualified Professional Visa (Personal Altamente Cualificado - PAC)", "category": "work", "service_type": "work", "description": "Fast-track permit processed via Large Business Unit (UGE) for managers, specialists, and technical graduates.", "official_url": "https://prie.comercio.gob.es/es-es/Paginas/Profesionales-Altamente-Cualificados.aspx", "vfs_url": "https://visa.vfsglobal.com/ind/en/esp/", "estimated_fees": "EUR 80"},
            {"id": "es_student", "name": "Student Visa (Estancia por Estudios)", "category": "student", "service_type": "student", "description": "National visa for higher education, master's degrees, and doctoral programs with part-time work authorization permitted (up to 30 hrs/wk).", "official_url": "https://www.exteriores.gob.es/es/ServiciosAlCiudadano/Paginas/Visados-Nacionales.aspx", "vfs_url": "https://visa.vfsglobal.com/ind/en/esp/", "estimated_fees": "EUR 80"},
            {"id": "es_non_lucrative", "name": "Non-Lucrative Residence Visa (Residencia No Lucrativa)", "category": "pr", "service_type": "pr", "description": "Long-term residence permit for self-funded individuals with passive income (400% IPREM benchmark).", "official_url": "https://www.exteriores.gob.es/es/ServiciosAlCiudadano/Paginas/Visados-Nacionales.aspx", "vfs_url": "https://visa.vfsglobal.com/ind/en/esp/", "estimated_fees": "EUR 80 + EUR 10.94 (Tasa)"},
            {"id": "es_schengen_tourist", "name": "Schengen Short-Stay Tourist Visa (Type C)", "category": "visitor", "service_type": "visitor", "description": "Short stay tourism for leisure, sightseeing, and family visits for up to 90 days.", "official_url": "https://www.exteriores.gob.es", "vfs_url": "https://visa.vfsglobal.com/ind/en/esp/", "estimated_fees": "EUR 90"},
        ],
    },
    "switzerland": {
        "country_name": "Switzerland",
        "country_code": "CH",
        "authority_name": "State Secretariat for Migration (SEM) / Cantonal Migration Offices",
        "official_portal_url": "https://www.sem.admin.ch",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/che/",
        "official_forms": [
            {"form_id": "sem_visa_d", "name": "Application for Long-Stay National Visa (Type D Form)", "description": "Official statutory SEM application form for study, employment, and residence in Switzerland exceeding 90 days", "url": "https://www.sem.admin.ch/dam/sem/en/data/einreise/visumantragsformulare/visumantrag-visumd-en-de.pdf.download.pdf/visumantrag-visumd-en-de.pdf", "applies_to": ["work", "student", "partner", "pr"], "category": "application", "mandatory": True},
            {"form_id": "sem_verpflichtungserklaerung", "name": "Declaration of Sponsorship (Verpflichtungserklärung / Déclaration de prise en charge)", "description": "Official financial guarantee form authenticated by the Swiss communal authorities guaranteeing up to CHF 30,000", "url": "https://www.sem.admin.ch/sem/en/home/themen/einreise/faq.html", "applies_to": ["visitor", "student"], "category": "financial", "mandatory": False},
            {"form_id": "kanton_arbeitsmarkt", "name": "Cantonal Labour Market Pre-Approval Decision (Vorbescheid / Décision Préalable)", "description": "Binding authorization issued by cantonal migration and employment authorities confirming national economic interest", "url": "https://www.sem.admin.ch/sem/en/home/themen/arbeit/nicht-eu_efta-angehoerige.html", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "sem_studienplan", "name": "Student Commitment Letter & Study Plan Protocol", "description": "Declaration of academic purpose, course curriculum, and signed undertaking to leave Switzerland upon study completion", "url": "https://www.eda.admin.ch/countries/india/en/home/visa/entry-ch/study-in-switzerland.html", "applies_to": ["student"], "category": "academic", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "ch_work_b_permit", "name": "Residence and Work Permit (Permit B / L - Non-EU Specialists)", "category": "work", "service_type": "work", "description": "Quota-regulated permit for highly qualified managers, specialists, and university graduates with employment contract.", "official_url": "https://www.sem.admin.ch/sem/en/home/themen/arbeit/nicht-eu_efta-angehoerige.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/che/", "estimated_fees": "CHF 88 (Visa) + CHF 142 (Cantonal issuance)"},
            {"id": "ch_student_visa", "name": "National Visa for Studies (Type D Student)", "category": "student", "service_type": "student", "description": "Long-stay visa for accredited Swiss universities (ETH Zurich, EPFL, University of Geneva, etc.).", "official_url": "https://www.sem.admin.ch/sem/en/home/themen/einreise/faq.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/che/", "estimated_fees": "CHF 88"},
            {"id": "ch_tourist_schengen", "name": "Short-Stay Schengen Tourist Visa (Type C)", "category": "visitor", "service_type": "visitor", "description": "Tourism and visiting relatives in Switzerland and Schengen area for up to 90 days.", "official_url": "https://www.swiss-visa.ch", "vfs_url": "https://visa.vfsglobal.com/ind/en/che/", "estimated_fees": "EUR 90 / CHF 88"},
            {"id": "ch_family_reunion", "name": "Family Reunification Visa (Regroupement Familial)", "category": "partner", "service_type": "partner", "description": "Residence visa for spouses and minor children of Swiss citizens or B/C permit holders.", "official_url": "https://www.sem.admin.ch/sem/en/home/themen/aufenthalt/familiennachzug.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/che/", "estimated_fees": "CHF 88"},
        ],
    },
    "netherlands": {
        "country_name": "Netherlands",
        "country_code": "NL",
        "authority_name": "Immigration and Naturalisation Service (IND) / Ministry of Justice and Security",
        "official_portal_url": "https://ind.nl",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nld/",
        "official_forms": [
            {"form_id": "ind_form_7001", "name": "IND Form 7001 - Application for Highly Skilled Migrant (Kennismigrant)", "description": "Official statutory IND form filed by recognized sponsor employer for fast-track residence permit", "url": "https://ind.nl/en/forms/7001.pdf", "applies_to": ["work", "kennismigrant"], "category": "employer", "mandatory": True},
            {"form_id": "ind_form_7018", "name": "IND Form 7018 - Application for Provisional Residence Permit (MVV Entry Visa)", "description": "Statutory application form for Authorization for Temporary Stay (Machtiging tot Voorlopig Verblijf - MVV)", "url": "https://ind.nl/en/forms/7018.pdf", "applies_to": ["work", "student", "partner", "pr"], "category": "application", "mandatory": True},
            {"form_id": "ind_form_7521", "name": "IND Form 7521 - Application for Residence with Partner / Spouse", "description": "Official family reunification application form including civil civic integration exam abroad (inburgeringseamen)", "url": "https://ind.nl/en/forms/7521.pdf", "applies_to": ["partner", "family"], "category": "application", "mandatory": True},
            {"form_id": "ind_form_garantstelling", "name": "Proof of Sponsorship and Private Accommodation Form (Garantstelling)", "description": "Municipal certified declaration of financial sponsorship and private accommodation", "url": "https://ind.nl/en/forms/1310.pdf", "applies_to": ["visitor"], "category": "financial", "mandatory": False},
            {"form_id": "ind_tb_declaration", "name": "IND Tuberculosis Examination Declaration Referral Form", "description": "Statutory undertaking to undergo TB screening at GGD Public Health Service upon arrival", "url": "https://ind.nl/en/forms/7604.pdf", "applies_to": ["work", "student", "partner"], "category": "medical", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "nl_highly_skilled", "name": "Highly Skilled Migrant Permit (Kennismigrant)", "category": "work", "service_type": "work", "description": "Fast-track residence permit sponsored by IND-recognized employer meeting age-based statutory salary criteria.", "official_url": "https://ind.nl/en/residence-permits/work/highly-skilled-migrant", "vfs_url": "https://visa.vfsglobal.com/ind/en/nld/", "estimated_fees": "EUR 380"},
            {"id": "nl_orientation_year", "name": "Orientation Year for Highly Educated Persons (Zoekjaar)", "category": "work", "service_type": "work", "description": "1-year open work permit for graduates of top 200 global universities (THE, QS, Shanghai rankings) or Dutch universities.", "official_url": "https://ind.nl/en/residence-permits/work/orientation-year-highly-educated-persons", "vfs_url": "https://visa.vfsglobal.com/ind/en/nld/", "estimated_fees": "EUR 228"},
            {"id": "nl_student", "name": "Student Residence Permit (Study in the Netherlands)", "category": "student", "service_type": "student", "description": "Higher education study permit processed via educational institution recognized sponsor.", "official_url": "https://ind.nl/en/residence-permits/study/student-residence-permit-for-university-or-higher-professional-education", "vfs_url": "https://visa.vfsglobal.com/ind/en/nld/", "estimated_fees": "EUR 228"},
            {"id": "nl_tourist_schengen", "name": "Schengen Short-Stay Tourist Visa (Type C)", "category": "visitor", "service_type": "visitor", "description": "Short visit for holidays and tourism for up to 90 days in the Netherlands.", "official_url": "https://www.netherlandsworldwide.nl/visa-the-netherlands/schengen-visa", "vfs_url": "https://visa.vfsglobal.com/ind/en/nld/", "estimated_fees": "EUR 90"},
            {"id": "nl_partner", "name": "Residence Permit for Living with a Partner in the Netherlands", "category": "partner", "service_type": "partner", "description": "Permit for married, registered, or unmarried partners of Dutch or legal residents.", "official_url": "https://ind.nl/en/residence-permits/family-and-partner/stay-with-your-partner-in-the-netherlands", "vfs_url": "https://visa.vfsglobal.com/ind/en/nld/", "estimated_fees": "EUR 228"},
        ],
    },
    "sweden": {
        "country_name": "Sweden",
        "country_code": "SE",
        "authority_name": "Swedish Migration Agency (Migrationsverket)",
        "official_portal_url": "https://migrationsverket.se",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/swe/",
        "official_forms": [
            {"form_id": "form_149011", "name": "Migrationsverket Form 149011 - Application for Swedish Work Permit", "description": "Official statutory Swedish application form for employment and residence permit", "url": "https://www.migrationsverket.se/download/18.5e83388f141c12901a52b61/1684307525287/149011_Ansokan_arbetstillstand_en.pdf", "applies_to": ["work"], "category": "application", "mandatory": True},
            {"form_id": "form_anstallning", "name": "Offer of Employment Document (Anställningserbjudande)", "description": "Employer statutory document initiated online by Swedish employer detailing collective agreement terms and insurance coverage", "url": "https://www.migrationsverket.se/English/Employers/Employing-people-from-non-EU-countries-/Work-permit-requirements.html", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "form_105031", "name": "Migrationsverket Form 105031 - First-Time Residence Permit for Studies", "description": "Statutory application form for full-time higher education programs in Sweden", "url": "https://www.migrationsverket.se/download/18.5e83388f141c12901a52b57/1684307438318/105031_Ansokan_studier_hogre_en.pdf", "applies_to": ["student"], "category": "academic", "mandatory": True},
            {"form_id": "form_161011", "name": "Migrationsverket Form 161011 - Application for Residence Permit for Family Members", "description": "Family reunification application form for spouses, cohabiting partners, and children", "url": "https://www.migrationsverket.se/download/18.5e83388f141c12901a52b6d/1684307593259/161011_Ansokan_medfoljande_arbetstagare_en.pdf", "applies_to": ["partner", "family"], "category": "application", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "se_work_permit", "name": "Swedish Work Permit (Arbetstillstånd)", "category": "work", "service_type": "work", "description": "Employer-sponsored work permit meeting Swedish union standards and salary minimum (80% of median wage = SEK 28,480/mo).", "official_url": "https://www.migrationsverket.se/English/Private-individuals/Working-in-Sweden.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/swe/", "estimated_fees": "SEK 2,200"},
            {"id": "se_blue_card", "name": "Sweden EU Blue Card", "category": "work", "service_type": "work", "description": "Residence and work permit for highly skilled personnel with 180 university credits and salary exceeding 1.5x average gross salary.", "official_url": "https://www.migrationsverket.se/English/Private-individuals/Working-in-Sweden/EU-Blue-Card.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/swe/", "estimated_fees": "SEK 2,200"},
            {"id": "se_student", "name": "Residence Permit for Higher Education Studies", "category": "student", "service_type": "student", "description": "Higher education permit requiring tuition payment and maintenance proof (SEK 10,314/mo for 2026).", "official_url": "https://www.migrationsverket.se/English/Private-individuals/Studying-in-Sweden.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/swe/", "estimated_fees": "SEK 1,500"},
            {"id": "se_tourist", "name": "Schengen Short-Stay Tourist Visa (Type C)", "category": "visitor", "service_type": "visitor", "description": "Visitor visa for leisure travel, vacation, or visiting relatives for up to 90 days.", "official_url": "https://www.migrationsverket.se/English/Private-individuals/Visiting-Sweden.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/swe/", "estimated_fees": "EUR 90"},
        ],
    },
    "japan": {
        "country_name": "Japan",
        "country_code": "JP",
        "authority_name": "Ministry of Foreign Affairs (MOFA) / Immigration Services Agency of Japan (ISA)",
        "official_portal_url": "https://www.mofa.go.jp",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/jpn/",
        "official_forms": [
            {"form_id": "mofa_visa_app", "name": "Visa Application Form to Enter Japan", "description": "Official statutory MOFA application form submitted with passport and photo to Japanese diplomatic mission", "url": "https://www.mofa.go.jp/j_info/visit/visa/pdfs/application1.pdf", "applies_to": ["work", "student", "visitor", "partner", "pr"], "category": "application", "mandatory": True},
            {"form_id": "coe_work_app", "name": "Application for Certificate of Eligibility (COE) - Working Status", "description": "Statutory application form filed with Immigration Services Agency in Japan by Japanese sponsor organization", "url": "https://www.moj.go.jp/isa/applications/procedures/16-1-1.html", "applies_to": ["work", "hsp"], "category": "employer", "mandatory": True},
            {"form_id": "mimoto_hoshosho", "name": "Letter of Guarantee Form (身元保証書 - Mimoto Hoshosho)", "description": "Official guarantee document signed by sponsor in Japan guaranteeing stay expenses and return travel", "url": "https://www.mofa.go.jp/files/000121327.pdf", "applies_to": ["visitor", "partner", "work"], "category": "financial", "mandatory": True},
            {"form_id": "reason_invitation", "name": "Reason for Invitation Letter (招へい理由書 - Shohei Riyusho)", "description": "Official explanatory document submitted by inviting Japanese organization or relative", "url": "https://www.mofa.go.jp/files/000121328.pdf", "applies_to": ["visitor", "business"], "category": "invitation", "mandatory": True},
            {"form_id": "hsp_points_calculation", "name": "Highly Skilled Professional (HSP) Points Calculation Sheet", "description": "Official statutory points evaluation form under Ministry of Justice Ordinance scoring degrees, salary, and career", "url": "https://www.moj.go.jp/isa/publications/materials/nyuukokukanri07_00016.html", "applies_to": ["hsp", "work"], "category": "application", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "jp_engineer_specialist", "name": "Work Visa: Engineer / Specialist in Humanities / International Services", "category": "work", "service_type": "work", "description": "Standard professional employment visa requiring Certificate of Eligibility (COE) and Japanese job contract.", "official_url": "https://www.mofa.go.jp/j_info/visit/visa/long/visa6.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/jpn/", "estimated_fees": "JPY 3,000 (Single entry visa fee) / INR 500 (VFS nominal)"},
            {"id": "jp_highly_skilled", "name": "Highly Skilled Professional Visa (HSP 1(a), 1(b), 1(c))", "category": "work", "service_type": "work", "description": "Preferential immigration treatment with 70+ points granting 5-year stay and fast-track PR in 1-3 years.", "official_url": "https://www.mofa.go.jp/j_info/visit/visa/long/visa13.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/jpn/", "estimated_fees": "JPY 3,000"},
            {"id": "jp_student", "name": "Student Visa (College Student)", "category": "student", "service_type": "student", "description": "Study visa for universities, junior colleges, or certified Japanese language institutes.", "official_url": "https://www.mofa.go.jp/j_info/visit/visa/long/visa4.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/jpn/", "estimated_fees": "JPY 3,000"},
            {"id": "jp_tourist_single", "name": "Temporary Visitor Visa (Tourism / Sightseeing)", "category": "visitor", "service_type": "visitor", "description": "Short-stay tourist visa for sightseeing, recreation, or visiting acquaintances for 15, 30, or 90 days.", "official_url": "https://www.mofa.go.jp/j_info/visit/visa/short/novisa.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/jpn/", "estimated_fees": "JPY 3,000 (Single) / JPY 6,000 (Multiple)"},
        ],
    },
    "argentina": {
        "country_name": "Argentina",
        "country_code": "AR",
        "authority_name": "National Directorate of Migration (Dirección Nacional de Migraciones - DNM) / Ministry of Foreign Affairs (Cancillería)",
        "official_portal_url": "https://www.migraciones.gov.ar",
        "vfs_url": "https://cindi.cancilleria.gob.ar",
        "official_forms": [
            {"form_id": "radex_solicitud", "name": "RaDEX Electronic Residence Application Protocol (Trámite de Radicación a Distancia)", "description": "Official statutory online residence filing confirmation and protocol generated by DNM RaDEX system", "url": "https://www.migraciones.gov.ar/radex/", "applies_to": ["work", "nomad", "student", "partner", "pr"], "category": "application", "mandatory": True},
            {"form_id": "form_fsv", "name": "Form FSV - Consular Visa Application Form (Solicitud de Visa)", "description": "Official Ministry of Foreign Affairs (Cancillería) application form for entry visas", "url": "https://cindi.cancilleria.gob.ar", "applies_to": ["work", "visitor", "student"], "category": "application", "mandatory": True},
            {"form_id": "renure_inscription", "name": "RENURE Employer Registration Certificate (Constancia de Inscripción en RENURE)", "description": "Official corporate registration certificate proving Argentine employer is authorized to hire foreign workers", "url": "https://www.migraciones.gov.ar/accesible/indexA.php?renure", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "declaracion_jurada_dnm", "name": "Statutory Affidavit of Good Character and No Criminal Record (Declaración Jurada DNM)", "description": "Sworn declaration submitted to DNM confirming absence of international criminal convictions", "url": "https://www.migraciones.gov.ar", "applies_to": ["work", "nomad", "student", "partner"], "category": "legal", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "ar_work_residence", "name": "Temporary Residence for Work / Employment (Artículo 23 Inciso A Ley 25.871)", "category": "work", "service_type": "work", "description": "Work authorization and residence based on an employment contract with an Argentine company registered in RENURE.", "official_url": "https://www.migraciones.gov.ar/accesible/indexA.php?radicacion_temporaria", "vfs_url": "https://cindi.cancilleria.gob.ar", "estimated_fees": "USD 250 (DNM immigration rate) + Consular visa fee"},
            {"id": "ar_digital_nomad", "name": "Digital Nomad Visa (Resolución 207/2022)", "category": "nomad", "service_type": "work", "description": "Temporary residence for remote workers providing services to natural or legal persons domiciled outside Argentina.", "official_url": "https://www.migraciones.gov.ar/nomadas_digitales/", "vfs_url": "https://cindi.cancilleria.gob.ar", "estimated_fees": "USD 200"},
            {"id": "ar_student", "name": "Student Temporary Residence (Artículo 23 Inciso J Ley 25.871)", "category": "student", "service_type": "student", "description": "Residence for formal university or tertiary studies in an educational institution registered with DNM.", "official_url": "https://www.migraciones.gov.ar/accesible/indexA.php?estudiantes", "vfs_url": "https://cindi.cancilleria.gob.ar", "estimated_fees": "USD 150"},
            {"id": "ar_tourist", "name": "Tourist Visa (Visa Transitoria de Turismo)", "category": "visitor", "service_type": "visitor", "description": "Entry visa for leisure, travel, and tourism up to 90 days issued by Argentine Consulates.", "official_url": "https://cindi.cancilleria.gob.ar", "vfs_url": "https://cindi.cancilleria.gob.ar", "estimated_fees": "USD 150"},
        ],
    },
    "portugal": {
        "country_name": "Portugal",
        "country_code": "PT",
        "authority_name": "Agency for Integration, Migration and Asylum (AIMA) / Ministry of Foreign Affairs (MNE)",
        "official_portal_url": "https://vistos.mne.gov.pt",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/prt/",
        "official_forms": [
            {"form_id": "mne_national_visa", "name": "National Visa Application Form (Pedido de Visto Nacional Tipo D)", "description": "Official statutory Ministry of Foreign Affairs application form for Portuguese residence visas", "url": "https://vistos.mne.gov.pt/en/national-visas/general-information/forms", "applies_to": ["work", "d7", "d8", "student", "golden", "pr"], "category": "application", "mandatory": True},
            {"form_id": "d8_remote_declaration", "name": "Digital Nomad Remote Work Declaration Form (D8 Teletrabalho)", "description": "Statutory declaration and employment verification for remote workers proving income at 4x Portuguese minimum wage", "url": "https://vistos.mne.gov.pt/en/national-visas/necessary-documentation/residence-visas#digital-nomads", "applies_to": ["d8", "work"], "category": "application", "mandatory": True},
            {"form_id": "termo_responsabilidade", "name": "Statement of Responsibility Form (Termo de Responsabilidade)", "description": "Official declaration by a Portuguese resident or company guaranteeing accommodation and food expenses", "url": "https://vistos.mne.gov.pt", "applies_to": ["work", "visitor", "student"], "category": "accommodation", "mandatory": False},
            {"form_id": "registo_criminal_consent", "name": "Criminal Record Verification Consent Form (AIMA)", "description": "Mandatory written authorization allowing Portuguese authorities to query applicant's criminal records", "url": "https://vistos.mne.gov.pt", "applies_to": ["work", "d7", "d8", "student", "partner"], "category": "legal", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "pt_d8_digital_nomad", "name": "Digital Nomad Visa (D8 Visa - Remote Work)", "category": "work", "service_type": "work", "description": "Residence visa for remote employees and freelancers earning at least 4 times Portuguese national minimum wage (EUR 3,280/month).", "official_url": "https://vistos.mne.gov.pt/en/national-visas/necessary-documentation/residence-visas#digital-nomads", "vfs_url": "https://visa.vfsglobal.com/ind/en/prt/", "estimated_fees": "EUR 90 (Visa) + EUR 170 (AIMA Permit)"},
            {"id": "pt_d7_passive_income", "name": "D7 Passive Income / Retirement Visa", "category": "pr", "service_type": "pr", "description": "Residence visa for foreign nationals living off passive income (pensions, rentals, dividends, intellectual property).", "official_url": "https://vistos.mne.gov.pt/en/national-visas/necessary-documentation/residence-visas#own-income", "vfs_url": "https://visa.vfsglobal.com/ind/en/prt/", "estimated_fees": "EUR 90"},
            {"id": "pt_d1_work", "name": "Subordinate Work Visa (D1 Visa)", "category": "work", "service_type": "work", "description": "Employment visa backed by a formal employment contract or binding promise of employment with a Portuguese entity.", "official_url": "https://vistos.mne.gov.pt/en/national-visas/necessary-documentation/residence-visas#subordinate-work", "vfs_url": "https://visa.vfsglobal.com/ind/en/prt/", "estimated_fees": "EUR 90"},
            {"id": "pt_student", "name": "Student Residence Visa (D4 / D5 Visa)", "category": "student", "service_type": "student", "description": "Long-term visa for higher education undergraduate, master's, doctoral programs, and research.", "official_url": "https://vistos.mne.gov.pt/en/national-visas/necessary-documentation/residence-visas#study", "vfs_url": "https://visa.vfsglobal.com/ind/en/prt/", "estimated_fees": "EUR 90"},
        ],
    },
    "ireland": {
        "country_name": "Ireland",
        "country_code": "IE",
        "authority_name": "Immigration Service Delivery (ISD) / Department of Enterprise, Trade and Employment (DETE)",
        "official_portal_url": "https://www.irishimmigration.ie",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/irl/",
        "official_forms": [
            {"form_id": "avats_online_summary", "name": "AVATS Online Visa Application Summary Sheet", "description": "Official signed summary sheet generated from AVATS (Automated Visa Application Tracking System)", "url": "https://www.visas.inis.gov.ie/avats/", "applies_to": ["work", "student", "visitor", "partner"], "category": "application", "mandatory": True},
            {"form_id": "dete_csep_permit", "name": "Critical Skills Employment Permit (CSEP) Application via EPOS", "description": "Official statutory employment permit granted by DETE for occupations on the Critical Skills Occupations List", "url": "https://epos.enterprise.gov.ie", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "dete_gep_permit", "name": "General Employment Permit (GEP) via EPOS", "description": "Standard employment permit granted by DETE subject to Labour Market Needs Test", "url": "https://epos.enterprise.gov.ie", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "isd_study_finances", "name": "Student Financial Evidence and Educational History Summary Form", "description": "Official declaration detailing educational history and minimum maintenance funds (EUR 10,000/yr)", "url": "https://www.irishimmigration.ie/coming-to-study-in-ireland/", "applies_to": ["student"], "category": "financial", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "ie_critical_skills", "name": "Critical Skills Employment Permit (CSEP) & Long-Stay D Visa", "category": "work", "service_type": "work", "description": "Fast-track permit for skilled professionals leading to Stamp 4 permanent residence after 2 years. Minimum salary EUR 38,000 / EUR 64,000.", "official_url": "https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/permit-types/critical-skills-employment-permit/", "vfs_url": "https://visa.vfsglobal.com/ind/en/irl/", "estimated_fees": "EUR 1,000 (DETE Permit) + EUR 60/100 (Visa) + EUR 300 (IRP registration)"},
            {"id": "ie_student_stamp2", "name": "Study Visa (Stamp 2 Higher Education)", "category": "student", "service_type": "student", "description": "Full-time study visa for courses listed on the Interim List of Eligible Programmes (ILEP).", "official_url": "https://www.irishimmigration.ie/coming-to-study-in-ireland/", "vfs_url": "https://visa.vfsglobal.com/ind/en/irl/", "estimated_fees": "EUR 60 (Single) / EUR 100 (Multiple) + EUR 300 (IRP)"},
            {"id": "ie_short_stay_tourist", "name": "Short-Stay Tourist Visa (Type C Visit)", "category": "visitor", "service_type": "visitor", "description": "Visit Ireland for holiday or leisure for up to 90 days. Not part of Schengen area.", "official_url": "https://www.irishimmigration.ie/coming-to-visit-ireland/", "vfs_url": "https://visa.vfsglobal.com/ind/en/irl/", "estimated_fees": "EUR 60 (Single) / EUR 100 (Multi-entry)"},
        ],
    },
    "austria": {
        "country_name": "Austria",
        "country_code": "AT",
        "authority_name": "Federal Ministry of the Interior (BMI) / Public Employment Service Austria (AMS)",
        "official_portal_url": "https://www.migration.gv.at",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/aut/",
        "official_forms": [
            {"form_id": "rwr_card_application", "name": "Red-White-Red Card Application Form (Rot-Weiß-Rot-Karte Antrag)", "description": "Official statutory Austrian application form for points-tested residence and work authorization", "url": "https://www.bmi.gv.at/312/Formulare/files/Erstantrag_RWR_Karte_2023.pdf", "applies_to": ["work", "pr"], "category": "application", "mandatory": True},
            {"form_id": "arbeitgebererklaerung", "name": "Employer Declaration Form (Arbeitgebererklärung für RWR-Karte)", "description": "Binding statutory form completed by Austrian employer confirming working conditions and collective agreement wages", "url": "https://www.ams.at/content/dam/download/formulare/arbeitgebererklaerung-rwr.pdf", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "visum_d_austria", "name": "National Visa Type D Application Form (Visum D)", "description": "Statutory application form for stay in Austria between 91 and 180 days or collecting RWR-card", "url": "https://www.bmeia.gv.at/fileadmin/user_upload/Vertretungen/New_Delhi/Dokumente/Visum_D_Antragsformular.pdf", "applies_to": ["work", "student"], "category": "application", "mandatory": True},
            {"form_id": "haftungserklaerung", "name": "Declaration of Liability (Haftungserklärung)", "description": "Notarized financial declaration of liability for living costs and accommodation in Austria", "url": "https://www.bmi.gv.at/312/Formulare/", "applies_to": ["visitor", "student"], "category": "financial", "mandatory": False},
        ],
        "visa_streams": [
            {"id": "at_rwr_card", "name": "Red-White-Red Card (Rot-Weiß-Rot-Karte)", "category": "work", "service_type": "work", "description": "Points-based work and residence permit for Very Highly Qualified Workers, Shortage Occupations, and Key Workers.", "official_url": "https://www.migration.gv.at/en/types-of-immigration/permanent-immigration/", "vfs_url": "https://visa.vfsglobal.com/ind/en/aut/", "estimated_fees": "EUR 160 (BMI permit) + EUR 150 (Visa D)"},
            {"id": "at_blue_card", "name": "Austria EU Blue Card (Blaue Karte EU)", "category": "work", "service_type": "work", "description": "Residence permit for university graduates with gross annual income matching statutory benchmark.", "official_url": "https://www.migration.gv.at/en/types-of-immigration/permanent-immigration/eu-blue-card/", "vfs_url": "https://visa.vfsglobal.com/ind/en/aut/", "estimated_fees": "EUR 160"},
            {"id": "at_student", "name": "Residence Permit - Student (Aufenthaltsbewilligung Student)", "category": "student", "service_type": "student", "description": "Residence permit for full degree studies at recognized Austrian universities and Fachhochschulen.", "official_url": "https://oead.at/en/to-austria/entry-and-residence/residence-permit-student", "vfs_url": "https://visa.vfsglobal.com/ind/en/aut/", "estimated_fees": "EUR 160"},
            {"id": "at_tourist", "name": "Schengen Short-Stay Tourist Visa (Type C)", "category": "visitor", "service_type": "visitor", "description": "Short-stay tourist and leisure travel for up to 90 days in Austria.", "official_url": "https://www.bmeia.gv.at", "vfs_url": "https://visa.vfsglobal.com/ind/en/aut/", "estimated_fees": "EUR 90"},
        ],
    },
    "belgium": {
        "country_name": "Belgium",
        "country_code": "BE",
        "authority_name": "Immigration Office (Office des Étrangers / Dienst Vreemdelingenzaken)",
        "official_portal_url": "https://dofi.ibz.be",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/bel/",
        "official_forms": [
            {"form_id": "single_permit_form", "name": "Single Permit Application (Permis Unique / Gecombineerde Vergunning)", "description": "Official regional joint work and residence authorization filed by Belgian employer", "url": "https://dofi.ibz.be/en/themes/third-country-nationals/work/single-permit", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "belgium_visa_d", "name": "Long-Stay Visa Application Form (Demande de Visa D / Aanvraag Visum D)", "description": "Statutory application form for entry with an authorized single permit or study authorization", "url": "https://visaonweb.diplomatie.be", "applies_to": ["work", "student", "partner", "pr"], "category": "application", "mandatory": True},
            {"form_id": "annexe_32", "name": "Pledge of Financial Support Form (Annexe 32 / Bijlage 32)", "description": "Official financial guarantee document legalised by Belgian authorities for student sponsorship", "url": "https://dofi.ibz.be/en/themes/third-country-nationals/study/pledge-financial-support-annex-32", "applies_to": ["student"], "category": "financial", "mandatory": True},
            {"form_id": "certificat_medical_be", "name": "Standard Medical Certificate Form for Belgium", "description": "Statutory medical clearance form signed by embassy-designated physician", "url": "https://dofi.ibz.be/en/themes/third-country-nationals/general-information/medical-certificate", "applies_to": ["work", "student", "partner"], "category": "medical", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "be_single_permit", "name": "Single Permit for Work (Permis Unique)", "category": "work", "service_type": "work", "description": "Single authorization permitting work and residence for highly qualified or shortage occupations.", "official_url": "https://dofi.ibz.be/en/themes/third-country-nationals/work/single-permit", "vfs_url": "https://visa.vfsglobal.com/ind/en/bel/", "estimated_fees": "EUR 231 (Visa D) + EUR 144 (Regional fee)"},
            {"id": "be_student", "name": "Higher Education Student Visa (Visa D Études)", "category": "student", "service_type": "student", "description": "Long-stay student visa for accredited universities in Flanders, Wallonia, or Brussels.", "official_url": "https://dofi.ibz.be/en/themes/third-country-nationals/study", "vfs_url": "https://visa.vfsglobal.com/ind/en/bel/", "estimated_fees": "EUR 231"},
            {"id": "be_tourist", "name": "Schengen Short-Stay Tourist Visa (Type C)", "category": "visitor", "service_type": "visitor", "description": "Short stay tourist travel for leisure and sightseeing for up to 90 days in Belgium.", "official_url": "https://dofi.ibz.be", "vfs_url": "https://visa.vfsglobal.com/ind/en/bel/", "estimated_fees": "EUR 90"},
        ],
    },
    "denmark": {
        "country_name": "Denmark",
        "country_code": "DK",
        "authority_name": "Danish Agency for International Recruitment and Integration (SIRI)",
        "official_portal_url": "https://www.nyidanmark.dk",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/dnk/",
        "official_forms": [
            {"form_id": "siri_ar1", "name": "SIRI Online Application Form AR1 / AR6 (Pay Limit & Positive List Scheme)", "description": "Official online statutory application completed jointly by employee and employer via Ny i Danmark", "url": "https://www.nyidanmark.dk/en-GB/You-want-to-apply/Work/Pay-limit-scheme", "applies_to": ["work"], "category": "application", "mandatory": True},
            {"form_id": "siri_st1", "name": "SIRI Form ST1 - Application for Residence Permit for Higher Education Studies", "description": "Joint online application form for students enrolled in Danish higher education programs", "url": "https://www.nyidanmark.dk/en-GB/You-want-to-apply/Study/Higher-education", "applies_to": ["student"], "category": "academic", "mandatory": True},
            {"form_id": "siri_fa1", "name": "SIRI Form FA1 - Application for Family Reunification", "description": "Official application form for spouses and cohabiting partners of Danish or foreign residents", "url": "https://www.nyidanmark.dk/en-GB/You-want-to-apply/Family", "applies_to": ["partner", "family"], "category": "application", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "dk_pay_limit", "name": "Pay Limit Scheme (Beløbsordningen)", "category": "work", "service_type": "work", "description": "Fast-track residence and work permit based on job offer meeting statutory annual salary minimum (DKK 393,000 / DKK 514,000).", "official_url": "https://www.nyidanmark.dk/en-GB/You-want-to-apply/Work/Pay-limit-scheme", "vfs_url": "https://visa.vfsglobal.com/ind/en/dnk/", "estimated_fees": "DKK 3,595 (SIRI fee) + EUR 90 (Danish Embassy visa)"},
            {"id": "dk_positive_list", "name": "Positive List Scheme (Higher Education & Skilled Work)", "category": "work", "service_type": "work", "description": "Work permit for professionals with job offers in occupations facing a designated shortage in Denmark.", "official_url": "https://www.nyidanmark.dk/en-GB/You-want-to-apply/Work/The-Positive-Lists", "vfs_url": "https://visa.vfsglobal.com/ind/en/dnk/", "estimated_fees": "DKK 3,595"},
            {"id": "dk_student", "name": "Residence Permit for Higher Education Studies", "category": "student", "service_type": "student", "description": "Full-time higher education study permit at Danish university or business academy.", "official_url": "https://www.nyidanmark.dk/en-GB/You-want-to-apply/Study", "vfs_url": "https://visa.vfsglobal.com/ind/en/dnk/", "estimated_fees": "DKK 2,750"},
            {"id": "dk_tourist", "name": "Schengen Short-Stay Tourist Visa (Type C)", "category": "visitor", "service_type": "visitor", "description": "Tourism and visiting family or friends for up to 90 days in Denmark.", "official_url": "https://www.nyidanmark.dk", "vfs_url": "https://visa.vfsglobal.com/ind/en/dnk/", "estimated_fees": "EUR 90"},
        ],
    },
    "norway": {
        "country_name": "Norway",
        "country_code": "NO",
        "authority_name": "Norwegian Directorate of Immigration (Utlendingsdirektoratet - UDI)",
        "official_portal_url": "https://www.udi.no",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nor/",
        "official_forms": [
            {"form_id": "udi_employment_offer", "name": "UDI Offer of Employment Form (Tilbud om ansettelse)", "description": "Official statutory UDI form filled and signed by Norwegian employer detailing position, salary, and union standards", "url": "https://www.udi.no/globalassets/global/skjemaer-engelsk/arbeid/offer-of-employment.pdf", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "udi_cover_letter", "name": "UDI Application Portal Cover Letter & Document Checklist", "description": "Mandatory summary document generated from the UDI Application Portal upon electronic fee payment", "url": "https://selfservice.udi.no/", "applies_to": ["work", "student", "family", "visitor"], "category": "application", "mandatory": True},
            {"form_id": "udi_power_attorney", "name": "UDI Power of Attorney Form (Fullmakt)", "description": "Authorisation for an employer or legal representative to act on applicant's behalf with UDI", "url": "https://www.udi.no/globalassets/global/skjemaer-engelsk/fullmakt-generell-engelsk.pdf", "applies_to": ["work", "student", "family"], "category": "agent", "mandatory": False},
        ],
        "visa_streams": [
            {"id": "no_skilled_worker", "name": "Skilled Worker Residence Permit (Faglært arbeidstaker)", "category": "work", "service_type": "work", "description": "Work and residence permit for professionals with completed higher education or vocational qualification.", "official_url": "https://www.udi.no/en/want-to-apply/work-immigration/skilled-workers/", "vfs_url": "https://visa.vfsglobal.com/ind/en/nor/", "estimated_fees": "NOK 6,300"},
            {"id": "no_student", "name": "Study Permit for Higher Education (Studietillatelse)", "category": "student", "service_type": "student", "description": "Residence permit for university studies requiring proof of subsistence funds (NOK 151,690/yr deposited in Norwegian student account).", "official_url": "https://www.udi.no/en/want-to-apply/studies/", "vfs_url": "https://visa.vfsglobal.com/ind/en/nor/", "estimated_fees": "NOK 5,900"},
            {"id": "no_tourist", "name": "Schengen Short-Stay Tourist Visa (Type C)", "category": "visitor", "service_type": "visitor", "description": "Short visit for holidays and tourism for up to 90 days in Norway.", "official_url": "https://www.udi.no/en/want-to-apply/visit-and-holiday/", "vfs_url": "https://visa.vfsglobal.com/ind/en/nor/", "estimated_fees": "EUR 90"},
        ],
    },
    "finland": {
        "country_name": "Finland",
        "country_code": "FI",
        "authority_name": "Finnish Immigration Service (Maahanmuuttovirasto - Migri)",
        "official_portal_url": "https://migri.fi",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/fin/",
        "official_forms": [
            {"form_id": "enter_finland_ty1", "name": "Enter Finland Form OLE_TY1 - First Residence Permit for an Employed Person (TTOL)", "description": "Official online statutory application under the Aliens Act processed by TE Office and Migri", "url": "https://enterfinland.fi", "applies_to": ["work"], "category": "application", "mandatory": True},
            {"form_id": "enter_finland_specialist", "name": "Enter Finland Form OLE_ERIK - Residence Permit for Specialist (Fast Track)", "description": "Fast-track 14-day residence permit for highly qualified specialists, tech professionals, and startup founders", "url": "https://enterfinland.fi", "applies_to": ["work", "specialist"], "category": "application", "mandatory": True},
            {"form_id": "form_tem_054", "name": "Form TEM 054 - Terms of Employment (Työehdot)", "description": "Mandatory employer statutory form verifying collective agreement compliance and salary levels", "url": "https://www.suomi.fi/services/form/supplementary-form-for-residence-permit-application-terms-of-employment-tem054-employment-and-economic-development-offices/d69e469d-27b0-4663-9fc8-508933b91fa0", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "enter_finland_student", "name": "Enter Finland Form OLE_OPI - First Residence Permit for Studies", "description": "Official application form for degree students enrolled at Finnish universities and UAS", "url": "https://enterfinland.fi", "applies_to": ["student"], "category": "academic", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "fi_specialist_fast_track", "name": "Specialist Residence Permit & D-Visa (Fast Track 14 Days)", "category": "work", "service_type": "work", "description": "Accelerated permit for university-educated specialists earning at least EUR 3,638/month.", "official_url": "https://migri.fi/en/specialist", "vfs_url": "https://visa.vfsglobal.com/ind/en/fin/", "estimated_fees": "EUR 380 (Electronic application fee)"},
            {"id": "fi_employed_person", "name": "Residence Permit for an Employed Person (TTOL)", "category": "work", "service_type": "work", "description": "Standard work permit subject to TE Services labour market review and Migri residence evaluation.", "official_url": "https://migri.fi/en/employed-person", "vfs_url": "https://visa.vfsglobal.com/ind/en/fin/", "estimated_fees": "EUR 490 (Paper) / EUR 380 (Online)"},
            {"id": "fi_student", "name": "Residence Permit for Studies (Higher Education)", "category": "student", "service_type": "student", "description": "Study permit for full Bachelor's or Master's degrees, granting right to work 30 hrs/week.", "official_url": "https://migri.fi/en/studying-in-finland", "vfs_url": "https://visa.vfsglobal.com/ind/en/fin/", "estimated_fees": "EUR 350"},
            {"id": "fi_tourist", "name": "Schengen Short-Stay Tourist Visa (Type C)", "category": "visitor", "service_type": "visitor", "description": "Tourist and leisure visa for travel up to 90 days in Finland and the Schengen zone.", "official_url": "https://finlandabroad.fi", "vfs_url": "https://visa.vfsglobal.com/ind/en/fin/", "estimated_fees": "EUR 90"},
        ],
    },
    "singapore": {
        "country_name": "Singapore",
        "country_code": "SG",
        "authority_name": "Ministry of Manpower (MOM) / Immigration & Checkpoints Authority (ICA)",
        "official_portal_url": "https://www.mom.gov.sg",
        "vfs_url": "https://save.ica.gov.sg",
        "official_forms": [
            {"form_id": "sg_ep_online", "name": "Employment Pass (EP) Online Application Form", "description": "Official statutory MOM application filed via EP eService assessed under the COMPASS points framework", "url": "https://www.mom.gov.sg/passes-and-permits/employment-pass/apply-for-a-pass", "applies_to": ["work", "ep"], "category": "employer", "mandatory": True},
            {"form_id": "sg_s_pass", "name": "S Pass Online Application Form", "description": "Statutory application for mid-level skilled technical staff earning at least SGD 3,150/month subject to quota", "url": "https://www.mom.gov.sg/passes-and-permits/s-pass/apply-for-a-pass", "applies_to": ["work", "spass"], "category": "employer", "mandatory": True},
            {"form_id": "ica_form_8", "name": "ICA Form 8 - Application for Permanent Residence (PTS Scheme)", "description": "Official application for Singapore Permanent Residence under the Professionals / Technical Personnel and Skilled Workers scheme", "url": "https://www.ica.gov.sg/reside/PR/apply", "applies_to": ["pr"], "category": "application", "mandatory": True},
            {"form_id": "ica_form_14a", "name": "ICA Form 14A - Application for an Entry Visa", "description": "Official visa application form submitted through authorized visa agents or local sponsors via SAVE portal", "url": "https://www.ica.gov.sg/enter-transit-depart/entering-singapore/visa_requirements", "applies_to": ["visitor"], "category": "application", "mandatory": True},
            {"form_id": "ica_solar_form", "name": "ICA SOLAR Student's Pass Application Protocol (eForm 16)", "description": "Official Student's Pass registration protocol via Student's Pass Online Application & Registration system", "url": "https://www.ica.gov.sg/reside/student-pass/apply", "applies_to": ["student"], "category": "academic", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "sg_employment_pass", "name": "Employment Pass (EP - COMPASS Framework)", "category": "work", "service_type": "work", "description": "Work pass for foreign managers, executives, and professionals earning at least SGD 5,000/month (SGD 5,500 in financial services).", "official_url": "https://www.mom.gov.sg/passes-and-permits/employment-pass", "vfs_url": "https://save.ica.gov.sg", "estimated_fees": "SGD 105 (Application) + SGD 225 (Issuance)"},
            {"id": "sg_one_pass", "name": "Overseas Networks & Expertise Pass (ONE Pass)", "category": "work", "service_type": "work", "description": "Personalized 5-year work pass for top talent in business, tech, arts, and sports earning at least SGD 30,000/month.", "official_url": "https://www.mom.gov.sg/passes-and-permits/overseas-networks-and-expertise-pass", "vfs_url": "https://save.ica.gov.sg", "estimated_fees": "SGD 105 (Application) + SGD 225 (Issuance)"},
            {"id": "sg_student_pass", "name": "Student's Pass (SOLAR System)", "category": "student", "service_type": "student", "description": "Pass for full-time studies at approved Institute of Higher Learning (NUS, NTU, SMU) or private education institutions.", "official_url": "https://www.ica.gov.sg/reside/student-pass", "vfs_url": "https://save.ica.gov.sg", "estimated_fees": "SGD 45 (Processing) + SGD 60 (Issuance)"},
            {"id": "sg_entry_visa", "name": "Singapore Tourist / Social Visit Entry Visa", "category": "visitor", "service_type": "visitor", "description": "Pre-entry visa for Indian passport holders issued via SAVE system for stays up to 30 days.", "official_url": "https://www.ica.gov.sg/enter-transit-depart/entering-singapore/visa_requirements", "vfs_url": "https://save.ica.gov.sg", "estimated_fees": "SGD 30 (Statutory visa fee)"},
        ],
    },
    "uae": {
        "country_name": "United Arab Emirates",
        "country_code": "AE",
        "authority_name": "Federal Authority for Identity, Citizenship, Customs and Port Security (ICP) / GDRFA Dubai",
        "official_portal_url": "https://smartservices.icp.gov.ae",
        "vfs_url": "https://www.vfsglobal.com/dubaivisaonline/",
        "official_forms": [
            {"form_id": "uae_entry_permit", "name": "Official Electronic Entry Permit Application Form (e-Channels)", "description": "Statutory online entry permit application filed through ICP Smart Services or GDRFA Dubai portal", "url": "https://smartservices.icp.gov.ae/echannels/web/client/default.html", "applies_to": ["work", "golden", "visitor", "student"], "category": "application", "mandatory": True},
            {"form_id": "uae_eid_application", "name": "Emirates ID Card Registration Form", "description": "Mandatory national biometric identity card application required for all UAE residents", "url": "https://smartservices.icp.gov.ae", "applies_to": ["work", "golden", "student", "partner"], "category": "identity", "mandatory": True},
            {"form_id": "uae_medical_fitness", "name": "Preventive Medical Examination Referral & Fitness Test", "description": "Mandatory statutory health screening (HIV, Hepatitis B, TB) completed at DHA / EHS approved medical fitness centre", "url": "https://www.dha.gov.ae", "applies_to": ["work", "golden", "student"], "category": "medical", "mandatory": True},
            {"form_id": "mohre_work_contract", "name": "MOHRE Standard Labour Contract & Offer Letter", "description": "Official Ministry of Human Resources and Emiratisation unified employment contract and electronic work permit", "url": "https://www.mohre.gov.ae", "applies_to": ["work"], "category": "employer", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "uae_golden_visa", "name": "UAE Golden Visa (10-Year Long-Term Residence)", "category": "work", "service_type": "work", "description": "Self-sponsored 10-year residency for investors, real estate owners (AED 2M+), entrepreneurs, and skilled professionals (salary AED 30,000+).", "official_url": "https://u.ae/en/information-and-services/visa-and-emirates-id/residence-visas/golden-visa", "vfs_url": "https://smartservices.icp.gov.ae", "estimated_fees": "AED 2,800 - AED 4,800"},
            {"id": "uae_green_visa", "name": "UAE Green Visa (5-Year Self-Sponsored Residency)", "category": "work", "service_type": "work", "description": "5-year residency for freelancers, self-employed persons, and skilled employees without a local employer sponsor.", "official_url": "https://u.ae/en/information-and-services/visa-and-emirates-id/residence-visas/green-visa", "vfs_url": "https://smartservices.icp.gov.ae", "estimated_fees": "AED 2,280"},
            {"id": "uae_employment_visa", "name": "Standard Company Employment Residence Visa (2 Years)", "category": "work", "service_type": "work", "description": "Employer-sponsored work residency backed by MOHRE electronic work permit and mainland / free zone sponsorship.", "official_url": "https://u.ae/en/information-and-services/visa-and-emirates-id/residence-visas/work-residence-visas", "vfs_url": "https://www.vfsglobal.com/dubaivisaonline/", "estimated_fees": "AED 3,000 - AED 5,000 (Statutorily borne by employer)"},
            {"id": "uae_tourist_visa", "name": "UAE Tourist Visa (30 Days / 60 Days / 5-Year Multi-Entry)", "category": "visitor", "service_type": "visitor", "description": "Tourist entry permit for tourism and visiting family issued electronically via GDRFA/ICP.", "official_url": "https://u.ae/en/information-and-services/visa-and-emirates-id/visit-visas/tourist-visa", "vfs_url": "https://www.vfsglobal.com/dubaivisaonline/", "estimated_fees": "AED 350 (30 days) / AED 500 (60 days) / AED 750 (5-year multi-entry)"},
        ],
    },
    "canada": {
        "country_name": "Canada",
        "country_code": "CA",
        "authority_name": "Immigration, Refugees and Citizenship Canada (IRCC)",
        "official_portal_url": "https://www.canada.ca/en/immigration-refugees-citizenship",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/can/",
        "official_forms": [
            {"form_id": "imm_0008", "name": "IMM 0008 - Generic Application Form for Canada", "description": "Main statutory application form for permanent residence applications", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm0008enu_2d.pdf", "applies_to": ["express_entry", "pr", "pnp", "family"], "category": "application", "mandatory": True},
            {"form_id": "imm_5645", "name": "IMM 5645 - Family Information Form", "description": "Detailed family member particulars for all temporary and permanent visa categories", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5645e.pdf", "applies_to": ["express_entry", "pr", "student", "work", "visitor"], "category": "application", "mandatory": True},
            {"form_id": "imm_5669", "name": "IMM 5669 - Schedule A - Background Declaration", "description": "Statutory personal history declaration covering employment, education, addresses, and military service", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5669e.pdf", "applies_to": ["express_entry", "pr"], "category": "application", "mandatory": True},
            {"form_id": "imm_1294", "name": "IMM 1294 - Application for Study Permit Made Outside of Canada", "description": "Statutory application form for international students studying at Designated Learning Institutions (DLI)", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm1294e.pdf", "applies_to": ["student"], "category": "application", "mandatory": True},
            {"form_id": "imm_1295", "name": "IMM 1295 - Application for Work Permit Made Outside of Canada", "description": "Main statutory application form for LMIA-backed and open work permits", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm1295e.pdf", "applies_to": ["work"], "category": "application", "mandatory": True},
            {"form_id": "imm_5257", "name": "IMM 5257 - Application for Temporary Resident Visa (Visitor Visa)", "description": "Official application form for tourist, business visit, or family visit visas", "url": "https://www.canada.ca/content/dam/ircc/migration/ircc/english/pdf/kits/forms/imm5257e.pdf", "applies_to": ["visitor"], "category": "application", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "ca_express_entry_fswp", "name": "Express Entry: Federal Skilled Worker Program (FSWP)", "category": "pr", "service_type": "pr", "description": "Points-based economic immigration system based on Comprehensive Ranking System (CRS) score.", "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/federal-skilled-workers.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/can/", "estimated_fees": "CAD 1,365 (CAD 850 processing + CAD 515 RPRF) + CAD 85 biometrics"},
            {"id": "ca_study_permit", "name": "Study Permit (Post-Secondary DLI)", "category": "student", "service_type": "student", "description": "Authorization to study at a Designated Learning Institution, requiring provincial attestation letter (PAL) and GIC proof.", "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/can/", "estimated_fees": "CAD 150 + CAD 85 biometrics"},
            {"id": "ca_work_permit", "name": "Employer-Specific Work Permit (LMIA)", "category": "work", "service_type": "work", "description": "Work permit for foreign nationals with a positive Labour Market Impact Assessment from Employment and Social Development Canada.", "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/can/", "estimated_fees": "CAD 155 + CAD 85 biometrics"},
            {"id": "ca_visitor_visa", "name": "Temporary Resident Visa (Visitor Visa / TRV)", "category": "visitor", "service_type": "visitor", "description": "Tourism, visiting family members, or business trips for up to 6 months per entry.", "official_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada.html", "vfs_url": "https://visa.vfsglobal.com/ind/en/can/", "estimated_fees": "CAD 100 + CAD 85 biometrics"},
        ],
    },
    "uk": {
        "country_name": "United Kingdom",
        "country_code": "GB",
        "authority_name": "UK Visas and Immigration (UKVI) / Home Office",
        "official_portal_url": "https://www.gov.uk/government/organisations/uk-visas-and-immigration",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/",
        "official_forms": [
            {"form_id": "uk_online_application", "name": "UKVI Online Visa Application Form", "description": "Official statutory application completed on gov.uk following Home Office immigration rules", "url": "https://www.gov.uk/apply-to-come-to-the-uk", "applies_to": ["work", "student", "visitor", "partner", "pr"], "category": "application", "mandatory": True},
            {"form_id": "uk_cos_document", "name": "Certificate of Sponsorship (CoS) Document", "description": "Official electronic reference number assigned by licensed sponsor employer via Sponsor Management System", "url": "https://www.gov.uk/uk-visa-sponsorship-employers/certificates-of-sponsorship", "applies_to": ["work", "skilled_worker"], "category": "employer", "mandatory": True},
            {"form_id": "uk_cas_statement", "name": "Confirmation of Acceptance for Studies (CAS) Statement", "description": "Official unique electronic reference number generated by licensed Student sponsor university", "url": "https://www.gov.uk/student-visa", "applies_to": ["student"], "category": "academic", "mandatory": True},
            {"form_id": "uk_tb_certificate", "name": "Tuberculosis (TB) Screening Medical Certificate", "description": "Statutory IOM/approved clinic chest X-ray certificate required for visa applications over 6 months", "url": "https://www.gov.uk/tb-test-visa", "applies_to": ["work", "student", "partner"], "category": "medical", "mandatory": True},
            {"form_id": "uk_atas_certificate", "name": "Academic Technology Approval Scheme (ATAS) Clearance Certificate", "description": "Mandatory security clearance certificate for postgraduate research in sensitive STEM subjects", "url": "https://www.gov.uk/guidance/academic-technology-approval-scheme", "applies_to": ["student", "work"], "category": "academic", "mandatory": False},
        ],
        "visa_streams": [
            {"id": "uk_skilled_worker", "name": "Skilled Worker Visa (Points-Based System)", "category": "work", "service_type": "work", "description": "Sponsored employment with an approved UK employer meeting eligible occupation code and general salary threshold (GBP 38,700).", "official_url": "https://www.gov.uk/skilled-worker-visa", "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/", "estimated_fees": "GBP 719 - GBP 1,420 + Immigration Health Surcharge GBP 1,035/year"},
            {"id": "uk_global_talent", "name": "Global Talent Visa (Prestigious Endorsement)", "category": "work", "service_type": "work", "description": "Permit for leaders or potential leaders in academia, research, arts, or digital technology endorsed by designated bodies.", "official_url": "https://www.gov.uk/global-talent", "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/", "estimated_fees": "GBP 716 + IHS GBP 1,035/year"},
            {"id": "uk_student", "name": "Student Visa (Higher Education)", "category": "student", "service_type": "student", "description": "Study visa for degree programs at UK licensed universities, granting 2-year Graduate Route post-study work rights.", "official_url": "https://www.gov.uk/student-visa", "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/", "estimated_fees": "GBP 490 + IHS GBP 776/year"},
            {"id": "uk_standard_visitor", "name": "Standard Visitor Visa (Tourism / Business)", "category": "visitor", "service_type": "visitor", "description": "Leisure travel, vacation, and authorized business activities for up to 6 months.", "official_url": "https://www.gov.uk/standard-visitor", "vfs_url": "https://visa.vfsglobal.com/ind/en/gbr/", "estimated_fees": "GBP 115 (6 months) / GBP 400 (2 years)"},
        ],
    },
    "usa": {
        "country_name": "United States",
        "country_code": "US",
        "authority_name": "U.S. Citizenship and Immigration Services (USCIS) / Department of State",
        "official_portal_url": "https://www.uscis.gov",
        "vfs_url": "https://travel.state.gov",
        "official_forms": [
            {"form_id": "form_ds_160", "name": "Form DS-160 - Online Nonimmigrant Visa Application Confirmation", "description": "Official statutory Department of State electronic visa application confirmation barcode page", "url": "https://ceac.state.gov/genniv/", "applies_to": ["h1b", "visitor", "student", "work", "b1b2", "f1"], "category": "application", "mandatory": True},
            {"form_id": "form_i_129", "name": "Form I-129 - Petition for a Nonimmigrant Worker", "description": "Statutory USCIS petition filed by U.S. employer for H-1B, L-1, and O-1 temporary workers", "url": "https://www.uscis.gov/i-129", "applies_to": ["h1b", "work", "l1"], "category": "employer", "mandatory": True},
            {"form_id": "form_i_20", "name": "Form I-20 - Certificate of Eligibility for Nonimmigrant Student Status", "description": "Statutory SEVIS document issued by certified academic institution for F-1 visa applicants", "url": "https://studyinthestates.dhs.gov/students/prepare/students-and-the-form-i-20", "applies_to": ["student", "f1"], "category": "academic", "mandatory": True},
            {"form_id": "form_i_140", "name": "Form I-140 - Immigrant Petition for Alien Workers", "description": "USCIS petition for employment-based permanent residence (EB-1, EB-2, EB-3)", "url": "https://www.uscis.gov/i-140", "applies_to": ["eb1", "eb2", "eb3", "pr", "green_card"], "category": "application", "mandatory": True},
            {"form_id": "form_i_485", "name": "Form I-485 - Application to Register Permanent Residence or Adjust Status", "description": "Main adjustment of status application for lawful permanent residence (Green Card)", "url": "https://www.uscis.gov/i-485", "applies_to": ["pr", "green_card"], "category": "application", "mandatory": True},
            {"form_id": "form_eta_9035", "name": "Form ETA-9035 - Labor Condition Application (LCA)", "description": "Department of Labor certified wage and working conditions determination for H-1B specialty workers", "url": "https://flag.dol.gov/", "applies_to": ["h1b", "work"], "category": "employer", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "us_h1b", "name": "H-1B Specialty Occupation Visa", "category": "work", "service_type": "work", "description": "Employer-sponsored specialty occupation work visa requiring bachelor's degree or higher.", "official_url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations", "vfs_url": "https://travel.state.gov", "estimated_fees": "USD 205 (MRV fee) + Employer USCIS petition fees"},
            {"id": "us_b1_b2", "name": "B-1 / B-2 Visitor Visa (Business & Tourism)", "category": "visitor", "service_type": "visitor", "description": "Nonimmigrant visa for temporary business travel (B-1) or tourism and medical treatment (B-2).", "official_url": "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html", "vfs_url": "https://travel.state.gov", "estimated_fees": "USD 185 (MRV fee)"},
            {"id": "us_f1_student", "name": "F-1 Academic Student Visa", "category": "student", "service_type": "student", "description": "Study visa for full-time academic degree programs at SEVP-certified schools, granting OPT post-study rights.", "official_url": "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html", "vfs_url": "https://travel.state.gov", "estimated_fees": "USD 185 (MRV fee) + USD 350 (SEVIS I-901 fee)"},
            {"id": "us_eb2_niw", "name": "EB-2 National Interest Waiver (NIW / Green Card)", "category": "pr", "service_type": "pr", "description": "Employment-based permanent residence pathway allowing self-petition without employer sponsorship for work of substantial merit.", "official_url": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-second-preference-eb-2", "vfs_url": "https://travel.state.gov", "estimated_fees": "USD 715 (I-140) + USD 1,440 (I-485)"},
        ],
    },
    "new_zealand": {
        "country_name": "New Zealand",
        "country_code": "NZ",
        "authority_name": "Immigration New Zealand (INZ) / Ministry of Business, Innovation and Employment",
        "official_portal_url": "https://www.immigration.govt.nz",
        "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/",
        "official_forms": [
            {"form_id": "inz_1015", "name": "INZ 1015 - Skilled Migrant Category Expression of Interest", "description": "EOI points submission for Skilled Migrant Category residence pathway", "url": "https://www.immigration.govt.nz/documents/forms-and-guides/inz1015.pdf", "applies_to": ["skilled_migrant", "pr"], "category": "application", "mandatory": True},
            {"form_id": "inz_aewv", "name": "Accredited Employer Work Visa (AEWV) Job Check & Application Protocol", "description": "Employer-initiated job check followed by applicant temporary work visa submission", "url": "https://www.immigration.govt.nz/new-zealand-visas/visas/visa/accredited-employer-work-visa", "applies_to": ["work"], "category": "employer", "mandatory": True},
            {"form_id": "inz_1007", "name": "INZ 1007 - General Medical Certificate Form", "description": "Mandatory statutory health examination completed by INZ panel physician", "url": "https://www.immigration.govt.nz/documents/forms-and-guides/inz1007.pdf", "applies_to": ["pr", "work", "student"], "category": "medical", "mandatory": True},
            {"form_id": "inz_1096", "name": "INZ 1096 - Chest X-Ray Certificate Form", "description": "Radiological chest X-ray screening form for tuberculosis detection", "url": "https://www.immigration.govt.nz/documents/forms-and-guides/inz1096.pdf", "applies_to": ["pr", "work", "student"], "category": "medical", "mandatory": True},
            {"form_id": "inz_1012", "name": "INZ 1012 - Fee Paying Student Visa Application Form", "description": "Statutory application form for international students at New Zealand educational providers", "url": "https://www.immigration.govt.nz/documents/forms-and-guides/inz1012.pdf", "applies_to": ["student"], "category": "application", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "nz_smc", "name": "Skilled Migrant Category Resident Visa (6-Point System)", "category": "pr", "service_type": "pr", "description": "Points-based permanent residency based on NZ occupational registration, degree level, or skilled job offer.", "official_url": "https://www.immigration.govt.nz/new-zealand-visas/visas/visa/skilled-migrant-category-resident-visa", "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/", "estimated_fees": "NZD 4,290"},
            {"id": "nz_aewv", "name": "Accredited Employer Work Visa (AEWV)", "category": "work", "service_type": "work", "description": "Temporary work visa for skilled individuals with a full-time job offer from an INZ-accredited employer.", "official_url": "https://www.immigration.govt.nz/new-zealand-visas/visas/visa/accredited-employer-work-visa", "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/", "estimated_fees": "NZD 750"},
            {"id": "nz_student", "name": "Fee Paying Student Visa", "category": "student", "service_type": "student", "description": "Study full-time at recognized New Zealand universities, polytechnics, or schools.", "official_url": "https://www.immigration.govt.nz/new-zealand-visas/visas/visa/fee-paying-student-visa", "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/", "estimated_fees": "NZD 375"},
            {"id": "nz_visitor", "name": "Visitor Visa (General Visitor)", "category": "visitor", "service_type": "visitor", "description": "Holiday, tourism, or visiting family and friends for up to 9 months.", "official_url": "https://www.immigration.govt.nz/new-zealand-visas/visas/visa/visitor-visa", "vfs_url": "https://visa.vfsglobal.com/ind/en/nzl/", "estimated_fees": "NZD 211"},
        ],
    },
    "china": {
        "country_name": "China",
        "country_code": "CN",
        "authority_name": "National Immigration Administration (NIA) / Visa For China",
        "official_portal_url": "https://en.nia.gov.cn",
        "vfs_url": "https://www.visaforchina.cn",
        "official_forms": [
            {"form_id": "china_visa_form", "name": "Form V.2013 - Visa Application Form of the People's Republic of China", "description": "Official statutory application form for entry visa and residence processing", "url": "https://www.visaforchina.cn", "applies_to": ["work", "student", "pr", "visitor", "business"], "category": "application", "mandatory": True},
            {"form_id": "china_pr_form", "name": "Foreigner Permanent Residence Identity Card Application Form", "description": "Statutory application form for Chinese Permanent Residence (Five-Star Card)", "url": "https://en.nia.gov.cn", "applies_to": ["pr", "permanent_residence"], "category": "application", "mandatory": True},
            {"form_id": "china_health_form", "name": "Foreigner Physical Examination Record", "description": "Mandatory statutory physical check-up form for Chinese work permits and long-term residence", "url": "https://www.visaforchina.cn", "applies_to": ["work", "student", "pr"], "category": "medical", "mandatory": True},
        ],
        "visa_streams": [
            {"id": "china_pr", "name": "Permanent Residence (Foreign Permanent Resident Identity Card)", "category": "pr", "service_type": "pr", "description": "Chinese Permanent Residence (Five-Star Card) for high-level experts, major investors, and long-term direct contributors.", "official_url": "https://en.nia.gov.cn", "vfs_url": "https://www.visaforchina.cn", "estimated_fees": "CNY 1,800"},
            {"id": "china_z_visa", "name": "Z Visa - Employment / Work Permit", "category": "work", "service_type": "work", "description": "Work visa for foreign nationals taking up statutory employment in mainland China.", "official_url": "https://www.visaforchina.cn", "vfs_url": "https://www.visaforchina.cn", "estimated_fees": "CNY 140 - CNY 900"},
            {"id": "china_x1_visa", "name": "X1 Student Visa (Long Term > 180 Days)", "category": "student", "service_type": "student", "description": "Long-term student visa for foreign students studying at accredited Chinese universities.", "official_url": "https://www.visaforchina.cn", "vfs_url": "https://www.visaforchina.cn", "estimated_fees": "CNY 140 - CNY 900"},
            {"id": "china_m_visa", "name": "M Visa - Commercial / Business Trade", "category": "business", "service_type": "business", "description": "Commercial and business visa for attending trade fairs, client meetings, or commerce.", "official_url": "https://www.visaforchina.cn", "vfs_url": "https://www.visaforchina.cn", "estimated_fees": "CNY 140 - CNY 900"},
        ],
    },
}

# Country alias mapping for seamless query matching
COUNTRY_ALIASES: Dict[str, str] = {
    "china": "china",
    "cn": "china",
    "prc": "china",
    "people's republic of china": "china",
    "australia": "australia",
    "aus": "australia",
    "au": "australia",
    "germany": "germany",
    "de": "germany",
    "deutschland": "germany",
    "france": "france",
    "fr": "france",
    "italy": "italy",
    "it": "italy",
    "spain": "spain",
    "es": "spain",
    "switzerland": "switzerland",
    "ch": "switzerland",
    "netherlands": "netherlands",
    "nl": "netherlands",
    "holland": "netherlands",
    "sweden": "sweden",
    "se": "sweden",
    "japan": "japan",
    "jp": "japan",
    "argentina": "argentina",
    "ar": "argentina",
    "portugal": "portugal",
    "pt": "portugal",
    "ireland": "ireland",
    "ie": "ireland",
    "austria": "austria",
    "at": "austria",
    "belgium": "belgium",
    "be": "belgium",
    "denmark": "denmark",
    "dk": "denmark",
    "norway": "norway",
    "no": "norway",
    "finland": "finland",
    "fi": "finland",
    "singapore": "singapore",
    "sg": "singapore",
    "uae": "uae",
    "united_arab_emirates": "uae",
    "dubai": "uae",
    "ae": "uae",
    "canada": "canada",
    "can": "canada",
    "ca": "canada",
    "uk": "uk",
    "united_kingdom": "uk",
    "great_britain": "uk",
    "gb": "uk",
    "usa": "usa",
    "united_states": "usa",
    "us": "usa",
    "america": "usa",
    "new_zealand": "new_zealand",
    "nz": "new_zealand",
    "nzl": "new_zealand",
}


def resolve_country_key(country_input: str) -> str:
    """Normalize user input to canonical country key."""
    if not country_input:
        return ""
    clean = country_input.lower().strip().replace("-", "_").replace(" ", "_")
    return COUNTRY_ALIASES.get(clean, clean)


def get_country_authority_info(country_input: str) -> Optional[Dict[str, Any]]:
    """Retrieve full regulatory authority, portal, forms, and streams for a country."""
    canonical_key = resolve_country_key(country_input)
    if canonical_key in COUNTRY_REGULATORY_AUTHORITIES:
        return COUNTRY_REGULATORY_AUTHORITIES[canonical_key]
    
    # Fuzzy search across keys and country names
    for key, data in COUNTRY_REGULATORY_AUTHORITIES.items():
        if key in canonical_key or canonical_key in key or data["country_name"].lower() == country_input.lower().strip():
            return data
    return None


def get_country_official_forms(country_input: str, visa_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get official statutory forms strictly in English for a country, optionally filtered by visa type."""
    data = get_country_authority_info(country_input)
    if not data or "official_forms" not in data:
        return []
    
    forms = data["official_forms"]
    if not visa_type:
        return forms
    
    clean_visa = visa_type.lower().replace("-", "_").replace(" ", "_")
    filtered = [f for f in forms if any(clean_visa in a or a in clean_visa for a in f.get("applies_to", []))]
    return filtered if filtered else [f for f in forms if f.get("mandatory")]


def get_country_vfs_url(country_input: str) -> Optional[str]:
    """Get the official VFS Global reference portal for a country."""
    data = get_country_authority_info(country_input)
    if data and data.get("vfs_url"):
        return data["vfs_url"]
    return None


def get_country_official_portal_url(country_input: str) -> Optional[str]:
    """Get the official government portal URL for a country."""
    data = get_country_authority_info(country_input)
    if data and data.get("official_portal_url"):
        return data["official_portal_url"]
    return None


def get_country_visa_categories(country_input: str) -> List[Dict[str, Any]]:
    """Get verified visa streams with official government URLs and VFS references."""
    data = get_country_authority_info(country_input)
    if data and data.get("visa_streams"):
        return data["visa_streams"]
    return []


def get_all_country_authorities_list() -> List[Dict[str, Any]]:
    """List all supported countries with authority details and form counts."""
    out = []
    for key, data in COUNTRY_REGULATORY_AUTHORITIES.items():
        out.append({
            "id": key,
            "country": data["country_name"],
            "country_code": data["country_code"],
            "authority": data["authority_name"],
            "official_portal_url": data["official_portal_url"],
            "vfs_url": data["vfs_url"],
            "total_forms": len(data.get("official_forms", [])),
            "total_streams": len(data.get("visa_streams", [])),
        })
    out.sort(key=lambda x: x["country"])
    return out


def iso_to_flag(code: str) -> str:
    """Convert a 2-letter ISO country code into Unicode flag emoji."""
    if not code or len(code) != 2:
        return "🌐"
    try:
        return "".join(chr(127397 + ord(c)) for c in code.upper())
    except Exception:
        return "🌐"


ALL_COUNTRY_CODES: Dict[str, tuple[str, str, str]] = {
    "australia": ("Australia", "AU", "🇦🇺"),
    "aus": ("Australia", "AU", "🇦🇺"),
    "au": ("Australia", "AU", "🇦🇺"),
    "canada": ("Canada", "CA", "🇨🇦"),
    "can": ("Canada", "CA", "🇨🇦"),
    "ca": ("Canada", "CA", "🇨🇦"),
    "united kingdom": ("United Kingdom", "GB", "🇬🇧"),
    "uk": ("United Kingdom", "GB", "🇬🇧"),
    "great britain": ("United Kingdom", "GB", "🇬🇧"),
    "gb": ("United Kingdom", "GB", "🇬🇧"),
    "germany": ("Germany", "DE", "🇩🇪"),
    "de": ("Germany", "DE", "🇩🇪"),
    "deutschland": ("Germany", "DE", "🇩🇪"),
    "united states": ("United States", "US", "🇺🇸"),
    "usa": ("United States", "US", "🇺🇸"),
    "us": ("United States", "US", "🇺🇸"),
    "america": ("United States", "US", "🇺🇸"),
    "new zealand": ("New Zealand", "NZ", "🇳🇿"),
    "nz": ("New Zealand", "NZ", "🇳🇿"),
    "nzl": ("New Zealand", "NZ", "🇳🇿"),
    "china": ("China", "CN", "🇨🇳"),
    "cn": ("China", "CN", "🇨🇳"),
    "prc": ("China", "CN", "🇨🇳"),
    "people's republic of china": ("China", "CN", "🇨🇳"),
    "japan": ("Japan", "JP", "🇯🇵"),
    "jp": ("Japan", "JP", "🇯🇵"),
    "singapore": ("Singapore", "SG", "🇸🇬"),
    "sg": ("Singapore", "SG", "🇸🇬"),
    "france": ("France", "FR", "🇫🇷"),
    "fr": ("France", "FR", "🇫🇷"),
    "italy": ("Italy", "IT", "🇮🇹"),
    "it": ("Italy", "IT", "🇮🇹"),
    "spain": ("Spain", "ES", "🇪🇸"),
    "es": ("Spain", "ES", "🇪🇸"),
    "switzerland": ("Switzerland", "CH", "🇨🇭"),
    "ch": ("Switzerland", "CH", "🇨🇭"),
    "netherlands": ("Netherlands", "NL", "🇳🇱"),
    "nl": ("Netherlands", "NL", "🇳🇱"),
    "holland": ("Netherlands", "NL", "🇳🇱"),
    "ireland": ("Ireland", "IE", "🇮🇪"),
    "ie": ("Ireland", "IE", "🇮🇪"),
    "uae": ("United Arab Emirates", "AE", "🇦🇪"),
    "united arab emirates": ("United Arab Emirates", "AE", "🇦🇪"),
    "dubai": ("United Arab Emirates", "AE", "🇦🇪"),
    "ae": ("United Arab Emirates", "AE", "🇦🇪"),
    "south korea": ("South Korea", "KR", "🇰🇷"),
    "korea": ("South Korea", "KR", "🇰🇷"),
    "kr": ("South Korea", "KR", "🇰🇷"),
    "india": ("India", "IN", "🇮🇳"),
    "in": ("India", "IN", "🇮🇳"),
    "brazil": ("Brazil", "BR", "🇧🇷"),
    "br": ("Brazil", "BR", "🇧🇷"),
    "mexico": ("Mexico", "MX", "🇲🇽"),
    "mx": ("Mexico", "MX", "🇲🇽"),
    "portugal": ("Portugal", "PT", "🇵🇹"),
    "pt": ("Portugal", "PT", "🇵🇹"),
    "poland": ("Poland", "PL", "🇵🇱"),
    "pl": ("Poland", "PL", "🇵🇱"),
    "sweden": ("Sweden", "SE", "🇸🇪"),
    "se": ("Sweden", "SE", "🇸🇪"),
    "norway": ("Norway", "NO", "🇳🇴"),
    "no": ("Norway", "NO", "🇳🇴"),
    "denmark": ("Denmark", "DK", "🇩🇰"),
    "dk": ("Denmark", "DK", "🇩🇰"),
    "finland": ("Finland", "FI", "🇫🇮"),
    "fi": ("Finland", "FI", "🇫🇮"),
    "austria": ("Austria", "AT", "🇦🇹"),
    "at": ("Austria", "AT", "🇦🇹"),
    "belgium": ("Belgium", "BE", "🇧🇪"),
    "be": ("Belgium", "BE", "🇧🇪"),
    "greece": ("Greece", "GR", "🇬🇷"),
    "gr": ("Greece", "GR", "🇬🇷"),
    "turkey": ("Turkey", "TR", "🇹🇷"),
    "tr": ("Turkey", "TR", "🇹🇷"),
    "thailand": ("Thailand", "TH", "🇹🇭"),
    "th": ("Thailand", "TH", "🇹🇭"),
    "malaysia": ("Malaysia", "MY", "🇲🇾"),
    "my": ("Malaysia", "MY", "🇲🇾"),
    "indonesia": ("Indonesia", "ID", "🇮🇩"),
    "id": ("Indonesia", "ID", "🇮🇩"),
    "philippines": ("Philippines", "PH", "🇵🇭"),
    "ph": ("Philippines", "PH", "🇵🇭"),
    "vietnam": ("Vietnam", "VN", "🇻🇳"),
    "vn": ("Vietnam", "VN", "🇻🇳"),
    "south africa": ("South Africa", "ZA", "🇿🇦"),
    "za": ("South Africa", "ZA", "🇿🇦"),
    "egypt": ("Egypt", "EG", "🇪🇬"),
    "eg": ("Egypt", "EG", "🇪🇬"),
    "saudi arabia": ("Saudi Arabia", "SA", "🇸🇦"),
    "sa": ("Saudi Arabia", "SA", "🇸🇦"),
    "qatar": ("Qatar", "QA", "🇶🇦"),
    "qa": ("Qatar", "QA", "🇶🇦"),
    "bahrain": ("Bahrain", "BH", "🇧🇭"),
    "bh": ("Bahrain", "BH", "🇧🇭"),
    "oman": ("Oman", "OM", "🇴🇲"),
    "om": ("Oman", "OM", "🇴🇲"),
    "kuwait": ("Kuwait", "KW", "🇰🇼"),
    "kw": ("Kuwait", "KW", "🇰🇼"),
    "czech republic": ("Czech Republic", "CZ", "🇨🇿"),
    "czechia": ("Czech Republic", "CZ", "🇨🇿"),
    "cz": ("Czech Republic", "CZ", "🇨🇿"),
    "hungary": ("Hungary", "HU", "🇭🇺"),
    "hu": ("Hungary", "HU", "🇭🇺"),
    "hong kong": ("Hong Kong", "HK", "🇭🇰"),
    "hk": ("Hong Kong", "HK", "🇭🇰"),
    "taiwan": ("Taiwan", "TW", "🇹🇼"),
    "tw": ("Taiwan", "TW", "🇹🇼"),
    "russia": ("Russia", "RU", "🇷🇺"),
    "ru": ("Russia", "RU", "🇷🇺"),
    "argentina": ("Argentina", "AR", "🇦🇷"),
    "ar": ("Argentina", "AR", "🇦🇷"),
    "chile": ("Chile", "CL", "🇨🇱"),
    "cl": ("Chile", "CL", "🇨🇱"),
    "colombia": ("Colombia", "CO", "🇨🇴"),
    "co": ("Colombia", "CO", "🇨🇴"),
    "costa rica": ("Costa Rica", "CR", "🇨🇷"),
    "cr": ("Costa Rica", "CR", "🇨🇷"),
    "kenya": ("Kenya", "KE", "🇰🇪"),
    "ke": ("Kenya", "KE", "🇰🇪"),
    "mauritius": ("Mauritius", "MU", "🇲🇺"),
    "mu": ("Mauritius", "MU", "🇲🇺"),
    "nigeria": ("Nigeria", "NG", "🇳🇬"),
    "ng": ("Nigeria", "NG", "🇳🇬"),
    "panama": ("Panama", "PA", "🇵🇦"),
    "pa": ("Panama", "PA", "🇵🇦"),
}


def resolve_country_meta(country_name_or_raw: str, fallback_text: str = "") -> tuple[str, str, str]:
    """Resolve country canonical name, ISO 2-letter code, and flag emoji from country or product name."""
    raw = (country_name_or_raw or "").strip().lower()
    if raw and raw in ALL_COUNTRY_CODES:
        return ALL_COUNTRY_CODES[raw]

    # Check fallback text (e.g. product name prefix "China - ...")
    clean_fallback = (fallback_text or "").strip()
    if " - " in clean_fallback:
        prefix = clean_fallback.split(" - ")[0].strip().lower()
        if prefix in ALL_COUNTRY_CODES:
            return ALL_COUNTRY_CODES[prefix]

    # Check if any country name is contained as a distinct keyword
    haystack = f" {raw} {clean_fallback.lower()} "
    for k, v in ALL_COUNTRY_CODES.items():
        if len(k) > 2 and f" {k} " in haystack:
            return v

    # Fallback to title-cased name
    clean_name = (country_name_or_raw or clean_fallback.split(" - ")[0] if " - " in clean_fallback else clean_fallback or "Other").strip().title()
    code = clean_name[:2].upper() if len(clean_name) >= 2 else "UN"
    flag = iso_to_flag(code) if len(code) == 2 and code.isalpha() else "🌐"
    return (clean_name, code, flag)

