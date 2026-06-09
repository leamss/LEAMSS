"""Phase 12.1 — New Zealand ANZSCO 1.3 Base Seed (~200 most-common occupations).

NZ uses ANZSCO v1.3 (not v2022 like AU). This seed covers the most-frequently
migrated occupations as published by Immigration NZ across:
  • Green List Tier 1 (Straight to Residence) — ~85 occs
  • Green List Tier 2 (Work to Residence) — ~22 occs
  • AEWV (Accredited Employer Work Visa) National Occupation List — many more

Idempotent: re-running preserves admin verification + edits.

Sources:
  • https://www.immigration.govt.nz/work/requirements-for-work-visas/green-list-occupations-qualifications-and-skills/green-list-roles-jobs-we-need-people-for-in-new-zealand/
  • https://www.immigration.govt.nz/work/requirements-for-work-visas/green-list-occupations-qualifications-and-skills/national-occupation-list-occupations-used-for-an-aewv/
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

SOURCE_NAME = "nz_anzsco_seed_2026"
SOURCE_URL = "https://www.immigration.govt.nz/work/requirements-for-work-visas/green-list-occupations-qualifications-and-skills/national-occupation-list-occupations-used-for-an-aewv/"

# ─── NZ ANZSCO 1.3 — Core Seed Set ──────────────────────────────────────────
# Format: (code, title, skill_level 1-5, unit_group_name)
# Curated from Immigration NZ's published Green List + AEWV National Occupation List.

NZ_OCCUPATIONS: List[Tuple[str, str, int, str]] = [
    # ─── 1. Managers (Construction, Engineering, Education, Health) ───
    ("121111", "Aquaculture Farmer", 1, "Farmers and Farm Managers"),
    ("121211", "Cotton Grower", 1, "Farmers and Farm Managers"),
    ("121311", "Apiarist", 2, "Farmers and Farm Managers"),
    ("121316", "Vegetable Grower", 2, "Farmers and Farm Managers"),
    ("121317", "Dairy Cattle Farmer", 1, "Farmers and Farm Managers"),
    ("121318", "Deer Farmer", 1, "Farmers and Farm Managers"),
    ("121321", "Pig Farmer", 1, "Farmers and Farm Managers"),
    ("121322", "Poultry Farmer", 1, "Farmers and Farm Managers"),
    ("121399", "Crop Farmers nec", 1, "Farmers and Farm Managers"),
    ("131112", "Sales and Marketing Manager", 1, "Advertising, Public Relations and Sales Managers"),
    ("132111", "Corporate Services Manager", 1, "Business Administration Managers"),
    ("132211", "Finance Manager", 1, "Business Administration Managers"),
    ("132311", "Human Resource Manager", 1, "Business Administration Managers"),
    ("132411", "Policy and Planning Manager", 1, "Business Administration Managers"),
    ("132511", "Research and Development Manager", 1, "Business Administration Managers"),
    ("133111", "Construction Project Manager", 1, "Construction Managers"),
    ("133112", "Project Builder", 2, "Construction Managers"),
    ("133211", "Engineering Manager", 1, "Engineering Managers"),
    ("133411", "Manufacturer", 1, "Manufacturers"),
    ("133511", "Production Manager (Forestry)", 1, "Production Managers"),
    ("133512", "Production Manager (Manufacturing)", 1, "Production Managers"),
    ("133513", "Production Manager (Mining)", 1, "Production Managers"),
    ("133611", "Supply and Distribution Manager", 1, "Supply, Distribution and Procurement Managers"),
    ("133612", "Procurement Manager", 1, "Supply, Distribution and Procurement Managers"),
    ("134111", "Child Care Centre Manager", 1, "Child Care Centre Managers"),
    ("134211", "Medical Administrator", 1, "Health and Welfare Services Managers"),
    ("134212", "Nursing Clinical Director", 1, "Health and Welfare Services Managers"),
    ("134213", "Primary Health Organisation Manager", 1, "Health and Welfare Services Managers"),
    ("134214", "Welfare Centre Manager", 1, "Health and Welfare Services Managers"),
    ("134299", "Health and Welfare Services Managers nec", 1, "Health and Welfare Services Managers"),
    ("134311", "School Principal", 1, "School Principals"),
    ("134411", "Faculty Head", 1, "Other Education Managers"),
    ("134499", "Other Education Managers nec", 1, "Other Education Managers"),
    ("141111", "Cafe or Restaurant Manager", 2, "Cafe and Restaurant Managers"),
    ("141311", "Hotel or Motel Manager", 2, "Hotel and Motel Managers"),
    ("142111", "Retail Manager (General)", 2, "Retail Managers"),
    ("149311", "Conference and Event Organiser", 2, "Other Hospitality, Retail and Service Managers"),

    # ─── 2. Professionals ───
    # Accountants / Auditors
    ("221111", "Accountant (General)", 1, "Accountants"),
    ("221112", "Management Accountant", 1, "Accountants"),
    ("221113", "Taxation Accountant", 1, "Accountants"),
    ("221213", "External Auditor", 1, "Auditors, Company Secretaries and Corporate Treasurers"),
    ("221214", "Internal Auditor", 1, "Auditors, Company Secretaries and Corporate Treasurers"),

    # Finance / Economics
    ("222311", "Financial Investment Adviser", 1, "Financial Brokers"),
    ("222312", "Financial Investment Manager", 1, "Financial Dealers"),
    ("224711", "Management Consultant", 1, "Management and Organisation Analysts"),
    ("224712", "Organisation and Methods Analyst", 1, "Management and Organisation Analysts"),

    # Engineers (lots of Green List Tier 1!)
    ("233111", "Chemical Engineer", 1, "Chemical and Materials Engineers"),
    ("233112", "Materials Engineer", 1, "Chemical and Materials Engineers"),
    ("233211", "Civil Engineer", 1, "Civil Engineering Professionals"),
    ("233212", "Geotechnical Engineer", 1, "Civil Engineering Professionals"),
    ("233213", "Quantity Surveyor", 1, "Civil Engineering Professionals"),
    ("233214", "Structural Engineer", 1, "Civil Engineering Professionals"),
    ("233215", "Transport Engineer", 1, "Civil Engineering Professionals"),
    ("233311", "Electrical Engineer", 1, "Electrical Engineering Professionals"),
    ("233411", "Electronics Engineer", 1, "Electronics Engineers"),
    ("233511", "Industrial Engineer", 1, "Industrial, Mechanical and Production Engineers"),
    ("233512", "Mechanical Engineer", 1, "Industrial, Mechanical and Production Engineers"),
    ("233513", "Production or Plant Engineer", 1, "Industrial, Mechanical and Production Engineers"),
    ("233611", "Mining Engineer (excl Petroleum)", 1, "Mining Engineers"),
    ("233612", "Petroleum Engineer", 1, "Mining Engineers"),
    ("233911", "Aeronautical Engineer", 1, "Other Engineering Professionals"),
    ("233912", "Agricultural Engineer", 1, "Other Engineering Professionals"),
    ("233913", "Biomedical Engineer", 1, "Other Engineering Professionals"),
    ("233914", "Engineering Technologist", 1, "Other Engineering Professionals"),
    ("233915", "Environmental Engineer", 1, "Other Engineering Professionals"),
    ("233916", "Naval Architect", 1, "Other Engineering Professionals"),
    ("233999", "Engineering Professionals nec", 1, "Other Engineering Professionals"),

    # ICT
    ("261111", "ICT Business Analyst", 1, "Business and Systems Analysts"),
    ("261112", "Systems Analyst", 1, "Business and Systems Analysts"),
    ("261211", "Multimedia Specialist", 2, "Multimedia Specialists and Web Developers"),
    ("261212", "Web Developer", 2, "Multimedia Specialists and Web Developers"),
    ("261311", "Analyst Programmer", 1, "Software and Applications Programmers"),
    ("261312", "Developer Programmer", 1, "Software and Applications Programmers"),
    ("261313", "Software Engineer", 1, "Software and Applications Programmers"),
    ("261314", "Software Tester", 1, "Software and Applications Programmers"),
    ("261399", "Software and Applications Programmers nec", 1, "Software and Applications Programmers"),
    ("262111", "Database Administrator", 1, "Database and Systems Administrators"),
    ("262112", "ICT Security Specialist", 1, "Database and Systems Administrators"),
    ("262113", "Systems Administrator", 1, "Database and Systems Administrators"),
    ("263111", "Computer Network and Systems Engineer", 1, "Computer Network Professionals"),
    ("263112", "Network Administrator", 1, "Computer Network Professionals"),
    ("263113", "Network Analyst", 1, "Computer Network Professionals"),
    ("263211", "ICT Quality Assurance Engineer", 1, "ICT Support and Test Engineers"),
    ("263212", "ICT Support Engineer", 1, "ICT Support and Test Engineers"),
    ("263213", "ICT Systems Test Engineer", 1, "ICT Support and Test Engineers"),

    # Health
    ("251211", "Medical Diagnostic Radiographer", 1, "Medical Imaging Professionals"),
    ("251212", "Medical Radiation Therapist", 1, "Medical Imaging Professionals"),
    ("251213", "Nuclear Medicine Technologist", 1, "Medical Imaging Professionals"),
    ("251214", "Sonographer", 1, "Medical Imaging Professionals"),
    ("251311", "Environmental Health Officer", 1, "Occupational and Environmental Health Professionals"),
    ("251312", "Occupational Health and Safety Adviser", 1, "Occupational and Environmental Health Professionals"),
    ("251411", "Optometrist", 1, "Optometrists and Orthoptists"),
    ("251511", "Hospital Pharmacist", 1, "Pharmacists"),
    ("251512", "Industrial Pharmacist", 1, "Pharmacists"),
    ("251513", "Retail Pharmacist", 1, "Pharmacists"),
    ("251911", "Health Promotion Officer", 1, "Other Health Diagnostic and Promotion Professionals"),
    ("251912", "Orthotist or Prosthetist", 1, "Other Health Diagnostic and Promotion Professionals"),
    ("252111", "Chiropractor", 1, "Chiropractors and Osteopaths"),
    ("252112", "Osteopath", 1, "Chiropractors and Osteopaths"),
    ("252213", "Occupational Therapist", 1, "Occupational Therapists"),
    ("252411", "Occupational Therapist", 1, "Occupational Therapists"),
    ("252511", "Physiotherapist", 1, "Physiotherapists"),
    ("252611", "Podiatrist", 1, "Podiatrists"),
    ("252711", "Audiologist", 1, "Audiologists and Speech Pathologists / Therapists"),
    ("252712", "Speech Pathologist / Therapist", 1, "Audiologists and Speech Pathologists / Therapists"),
    ("253111", "General Practitioner", 1, "Generalist Medical Practitioners"),
    ("253112", "Resident Medical Officer", 1, "Generalist Medical Practitioners"),
    ("253211", "Anaesthetist", 1, "Anaesthetists"),
    ("253311", "Specialist Physician (General Medicine)", 1, "Specialist Physicians"),
    ("253312", "Cardiologist", 1, "Specialist Physicians"),
    ("253313", "Clinical Haematologist", 1, "Specialist Physicians"),
    ("253314", "Medical Oncologist", 1, "Specialist Physicians"),
    ("253315", "Endocrinologist", 1, "Specialist Physicians"),
    ("253316", "Gastroenterologist", 1, "Specialist Physicians"),
    ("253317", "Intensive Care Specialist", 1, "Specialist Physicians"),
    ("253318", "Neurologist", 1, "Specialist Physicians"),
    ("253321", "Paediatrician", 1, "Specialist Physicians"),
    ("253322", "Renal Medicine Specialist", 1, "Specialist Physicians"),
    ("253323", "Rheumatologist", 1, "Specialist Physicians"),
    ("253324", "Thoracic Medicine Specialist", 1, "Specialist Physicians"),
    ("253399", "Specialist Physicians nec", 1, "Specialist Physicians"),
    ("253411", "Psychiatrist", 1, "Psychiatrists"),
    ("253511", "Surgeon (General)", 1, "Specialist Surgeons"),
    ("253512", "Cardiothoracic Surgeon", 1, "Specialist Surgeons"),
    ("253513", "Neurosurgeon", 1, "Specialist Surgeons"),
    ("253514", "Orthopaedic Surgeon", 1, "Specialist Surgeons"),
    ("253515", "Otorhinolaryngologist", 1, "Specialist Surgeons"),
    ("253516", "Paediatric Surgeon", 1, "Specialist Surgeons"),
    ("253517", "Plastic and Reconstructive Surgeon", 1, "Specialist Surgeons"),
    ("253518", "Urologist", 1, "Specialist Surgeons"),
    ("253521", "Vascular Surgeon", 1, "Specialist Surgeons"),
    ("253911", "Dermatologist", 1, "Other Medical Practitioners"),
    ("253912", "Emergency Medicine Specialist", 1, "Other Medical Practitioners"),
    ("253913", "Obstetrician and Gynaecologist", 1, "Other Medical Practitioners"),
    ("253914", "Ophthalmologist", 1, "Other Medical Practitioners"),
    ("253915", "Pathologist", 1, "Other Medical Practitioners"),
    ("253916", "Diagnostic and Interventional Radiologist", 1, "Other Medical Practitioners"),
    ("253917", "Radiation Oncologist", 1, "Other Medical Practitioners"),
    ("253999", "Medical Practitioners nec", 1, "Other Medical Practitioners"),
    ("254111", "Midwife", 1, "Midwives"),
    ("254411", "Nurse Practitioner", 1, "Nurse Practitioners"),
    ("254412", "Registered Nurse (Aged Care)", 1, "Registered Nurses"),
    ("254413", "Registered Nurse (Child and Family Health)", 1, "Registered Nurses"),
    ("254414", "Registered Nurse (Community Health)", 1, "Registered Nurses"),
    ("254415", "Registered Nurse (Critical Care and Emergency)", 1, "Registered Nurses"),
    ("254416", "Registered Nurse (Developmental Disability)", 1, "Registered Nurses"),
    ("254417", "Registered Nurse (Disability and Rehabilitation)", 1, "Registered Nurses"),
    ("254418", "Registered Nurse (Medical)", 1, "Registered Nurses"),
    ("254421", "Registered Nurse (Medical Practice)", 1, "Registered Nurses"),
    ("254422", "Registered Nurse (Mental Health)", 1, "Registered Nurses"),
    ("254423", "Registered Nurse (Perioperative)", 1, "Registered Nurses"),
    ("254424", "Registered Nurse (Surgical)", 1, "Registered Nurses"),
    ("254499", "Registered Nurses nec", 1, "Registered Nurses"),

    # Education
    ("241111", "Early Childhood (Pre-primary) Teacher", 1, "Early Childhood Teachers"),
    ("241213", "Primary School Teacher", 1, "Primary School Teachers"),
    ("241311", "Middle School Teacher", 1, "Middle School Teachers"),
    ("241411", "Secondary School Teacher", 1, "Secondary School Teachers"),
    ("241511", "Special Needs Teacher", 1, "Special Education Teachers"),
    ("241512", "Teacher of the Hearing Impaired", 1, "Special Education Teachers"),
    ("241513", "Teacher of the Sight Impaired", 1, "Special Education Teachers"),
    ("242111", "University Lecturer", 1, "University Lecturers and Tutors"),
    ("242112", "University Tutor", 1, "University Lecturers and Tutors"),

    # Architects, Surveyors, Town Planners
    ("232111", "Architect", 1, "Architects, Designers, Planners and Surveyors"),
    ("232112", "Landscape Architect", 1, "Architects, Designers, Planners and Surveyors"),
    ("232212", "Surveyor", 1, "Architects, Designers, Planners and Surveyors"),
    ("232213", "Cartographer", 1, "Architects, Designers, Planners and Surveyors"),
    ("232611", "Urban and Regional Planner", 1, "Urban and Regional Planners"),

    # Legal
    ("271111", "Barrister", 1, "Barristers"),
    ("271311", "Solicitor", 1, "Solicitors"),

    # ─── 3. Technicians and Trades ───
    ("311211", "Anaesthetic Technician", 2, "Medical Technicians"),
    ("311213", "Medical Laboratory Technician", 2, "Medical Technicians"),
    ("312211", "Civil Engineering Technician", 2, "Civil Engineering Draftspersons and Technicians"),
    ("312311", "Electrical Engineering Draftsperson", 2, "Electrical Engineering Draftspersons and Technicians"),
    ("312312", "Electrical Engineering Technician", 2, "Electrical Engineering Draftspersons and Technicians"),
    ("321111", "Automotive Electrician", 3, "Automotive Electricians and Mechanics"),
    ("321211", "Motor Mechanic (General)", 3, "Motor Mechanics"),
    ("321212", "Diesel Motor Mechanic", 3, "Motor Mechanics"),
    ("321213", "Motorcycle Mechanic", 3, "Motor Mechanics"),
    ("321214", "Small Engine Mechanic", 3, "Motor Mechanics"),
    ("322311", "Metal Fabricator", 3, "Structural Steel and Welding Trades Workers"),
    ("322312", "Pressure Welder", 3, "Structural Steel and Welding Trades Workers"),
    ("322313", "Welder (First Class)", 3, "Structural Steel and Welding Trades Workers"),
    ("323111", "Aircraft Maintenance Engineer (Avionics)", 2, "Aircraft Maintenance Engineers"),
    ("323112", "Aircraft Maintenance Engineer (Mechanical)", 2, "Aircraft Maintenance Engineers"),
    ("323113", "Aircraft Maintenance Engineer (Structures)", 2, "Aircraft Maintenance Engineers"),
    ("323211", "Fitter (General)", 3, "Metal Fitters and Machinists"),
    ("323212", "Fitter and Turner", 3, "Metal Fitters and Machinists"),
    ("323213", "Fitter-Welder", 3, "Metal Fitters and Machinists"),
    ("331111", "Bricklayer", 3, "Bricklayers, and Carpenters and Joiners"),
    ("331112", "Stonemason", 3, "Bricklayers, and Carpenters and Joiners"),
    ("331211", "Carpenter and Joiner", 3, "Bricklayers, and Carpenters and Joiners"),
    ("331212", "Carpenter", 3, "Bricklayers, and Carpenters and Joiners"),
    ("331213", "Joiner", 3, "Bricklayers, and Carpenters and Joiners"),
    ("332211", "Painting Trades Worker", 3, "Painting Trades Workers"),
    ("333111", "Glazier", 3, "Glaziers, Plasterers and Tilers"),
    ("333211", "Fibrous Plasterer", 3, "Glaziers, Plasterers and Tilers"),
    ("333212", "Solid Plasterer", 3, "Glaziers, Plasterers and Tilers"),
    ("333411", "Wall and Floor Tiler", 3, "Glaziers, Plasterers and Tilers"),
    ("334111", "Plumber (General)", 3, "Plumbers"),
    ("334112", "Airconditioning and Mechanical Services Plumber", 3, "Plumbers"),
    ("334113", "Drainer", 3, "Plumbers"),
    ("334114", "Gasfitter", 3, "Plumbers"),
    ("334115", "Roof Plumber", 3, "Plumbers"),
    ("341111", "Electrician (General)", 3, "Electricians"),
    ("341112", "Electrician (Special Class)", 3, "Electricians"),
    ("341113", "Lift Mechanic", 3, "Electricians"),
    ("342111", "Airconditioning and Refrigeration Mechanic", 3, "Air-conditioning and Refrigeration Mechanics"),
    ("342211", "Electrical Linesworker", 3, "Electrical Distribution Trades Workers"),
    ("342212", "Technical Cable Jointer", 3, "Electrical Distribution Trades Workers"),
    ("342311", "Business Machine Mechanic", 3, "Electronics and Telecommunications Trades Workers"),
    ("342313", "Electronic Equipment Trades Worker", 3, "Electronics and Telecommunications Trades Workers"),
    ("342314", "Electronic Instrument Trades Worker (General)", 3, "Electronics and Telecommunications Trades Workers"),
    ("342315", "Electronic Instrument Trades Worker (Special Class)", 3, "Electronics and Telecommunications Trades Workers"),
    ("342411", "Cabler (Data and Telecommunications)", 3, "Telecommunications Trades Workers"),
    ("342412", "Telecommunications Cable Jointer", 3, "Telecommunications Trades Workers"),
    ("342413", "Telecommunications Linesworker", 3, "Telecommunications Trades Workers"),
    ("342414", "Telecommunications Technician", 3, "Telecommunications Trades Workers"),
    ("351111", "Baker", 3, "Bakers and Pastrycooks"),
    ("351112", "Pastrycook", 3, "Bakers and Pastrycooks"),
    ("351211", "Butcher or Smallgoods Maker", 3, "Butchers and Smallgoods Makers"),
    ("351311", "Chef", 2, "Chefs"),
    ("351411", "Cook", 4, "Cooks"),

    # ─── 4. Community / Personal Service Workers ───
    ("411111", "Ambulance Officer", 2, "Ambulance Officers and Paramedics"),
    ("411112", "Intensive Care Ambulance Paramedic", 2, "Ambulance Officers and Paramedics"),
    ("411211", "Dental Hygienist", 2, "Dental Hygienists, Technicians and Therapists"),
    ("411212", "Dental Prosthetist", 2, "Dental Hygienists, Technicians and Therapists"),
    ("411213", "Dental Technician", 2, "Dental Hygienists, Technicians and Therapists"),
    ("411214", "Dental Therapist", 2, "Dental Hygienists, Technicians and Therapists"),

    # ─── 5. Plant and Machinery Operators ───
    ("712111", "Crane, Hoist or Lift Operator", 4, "Mobile Construction Plant Operators"),
    ("721111", "Agricultural and Horticultural Mobile Plant Operator", 4, "Mobile Plant Operators"),
    ("721211", "Excavator Operator", 4, "Mobile Plant Operators"),
    ("721212", "Loader Operator", 4, "Mobile Plant Operators"),
    ("721213", "Grader Operator", 4, "Mobile Plant Operators"),
    ("721214", "Bulldozer Operator", 4, "Mobile Plant Operators"),
    ("721215", "Backhoe Operator", 4, "Mobile Plant Operators"),
    ("721216", "Earthmoving Plant Operator (General)", 4, "Mobile Plant Operators"),

    # ─── 6. Aged / Disability Care Workers (Care Workforce Sector Agreement) ───
    ("423111", "Aged or Disabled Carer", 4, "Personal Carers and Assistants"),
    ("423211", "Dental Assistant", 4, "Personal Carers and Assistants"),
    ("423311", "Nursing Support Worker", 4, "Personal Carers and Assistants"),
    ("423312", "Personal Care Assistant", 4, "Personal Carers and Assistants"),
    ("423313", "Therapy Aide", 4, "Personal Carers and Assistants"),
    ("411411", "Diversional Therapist", 2, "Welfare Support Workers"),
    ("411412", "Recreation Officer", 2, "Welfare Support Workers"),
]


def _build_doc(code: str, title: str, skill_level: int, unit_group_name: str, now) -> Dict[str, Any]:
    """Build an occupation_master document seeded for NZ."""
    unit_group_code = code[:3]
    return {
        "occupation_id": str(uuid.uuid4()),
        "code": code,
        "classification_type": "ANZSCO",
        "classification_version": "ANZSCO 1.3 (NZ)",
        "country_code": "NZ",
        "title": title,
        "alternative_titles": [],
        "specialisations": [],
        "hierarchy": {
            "major_group": code[0],
            "sub_major_group": code[:2],
            "minor_group": code[:3],
            "unit_group": unit_group_code,
            "unit_group_name": unit_group_name,
        },
        "description": "",
        "typical_tasks": [],
        "skill_level": skill_level,
        "assessing_authority": {
            "body_id": "nzqa",
            "name": "NZQA",
            "full_name": "New Zealand Qualifications Authority",
            "website": "https://nzqa.govt.nz",
        },
        "skill_assessment_details": {
            "requirements": "",
            "criteria_notes": "",
            "qualification_rules": "",
            "documents_required": [],
            "fee_native": None,
            "fee_currency": None,
            "processing_time": "6 weeks",
        },
        "visa_pathways": {
            "pathway_lists": ["Federal"],
            "visa_eligibility": [
                {"visa_subclass": "SMC",      "eligible": skill_level in (1, 2, 3), "list": "Federal", "notes": ""},
                {"visa_subclass": "Green-T1", "eligible": False, "list": "Federal", "notes": ""},
                {"visa_subclass": "Green-T2", "eligible": False, "list": "Federal", "notes": ""},
                {"visa_subclass": "AEWV",     "eligible": skill_level in (1, 2, 3, 4), "list": "Federal", "notes": ""},
            ],
        },
        "state_territory_eligibility": [],
        "specialisations": [],
        "similar_codes": [],
        "ai_draft": {},
        "custom_qa": {},
        "verification": {"is_verified": False, "verified_at": None, "verified_by": None, "notes": ""},
        "_migration_version": "phase12_nz_seed_2026",
        "status": "draft",
        "created_at": now,
        "created_by": "nz_anzsco_seed",
        "updated_at": now,
        "last_reviewed_at": None,
        "linked_product_id": None,
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
    }


async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Idempotently upsert NZ ANZSCO records. Preserves admin-verified edits.

    Strategy:
      • For new codes (not in DB) — insert full doc.
      • For existing codes — DO NOT overwrite (preserve admin verification).
    """
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc)
    inserted = 0
    skipped_existing = 0

    for code, title, skill_level, unit_group_name in NZ_OCCUPATIONS:
        existing = await coll.find_one(
            {"country_code": "NZ", "code": code},
            {"_id": 1, "verification": 1, "status": 1},
        )
        if existing:
            skipped_existing += 1
            continue
        if not dry_run:
            doc = _build_doc(code, title, skill_level, unit_group_name, now)
            await coll.insert_one(doc)
        inserted += 1

    # Sanity total
    total_nz = await coll.count_documents({"country_code": "NZ"})

    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "dry_run": dry_run,
        "version": "ANZSCO 1.3 NZ · 2026",
        "totals": {
            "seed_set_size": len(NZ_OCCUPATIONS),
            "nz_records_in_db": total_nz + (0 if dry_run else inserted) if not dry_run else total_nz + inserted,
        },
        "counts": {
            "inserted": inserted,
            "skipped_existing": skipped_existing,
        },
        "ran_at": now.isoformat(),
        "actor": actor,
    }
