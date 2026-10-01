const fs = require('fs');
const path = require('path');

const titles = JSON.parse(fs.readFileSync(path.join(__dirname, 'au_all_occupations.json'), 'utf8'));

// High fidelity Australian ABS Standard Occupational dictionary mapping
const KNOWN_ANZSCO = {
  // 1111 - Chief Executives, General Managers and Legislators
  '111111': {
    alternative_titles: ['Director-General', 'Managing Director'],
    specialisations: ['Chief Executive Officer (CEO)', 'Chief Operating Officer (COO)', 'Director-General (Public Service)', 'Vice-Chancellor']
  },
  '111211': {
    alternative_titles: ['Assistant Director-General'],
    specialisations: ['Assistant Commissioner (Police)', 'Deputy Commissioner (Police)', 'Director of Operations']
  },
  '111212': {
    alternative_titles: ['Regional Manager'],
    specialisations: ['Area General Manager', 'State Operations Manager']
  },
  '111311': {
    alternative_titles: ['Member of Parliament'],
    specialisations: ['Senator', 'Elected Legislative Representative']
  },
  '111312': {
    alternative_titles: ['City Councillor'],
    specialisations: ['Alderman', 'Shire President', 'Mayor']
  },
  '111399': {
    alternative_titles: ['Elected Official'],
    specialisations: ['Aboriginal Council Member', 'Statutory Authority Board Member']
  },

  // 1211 - Aquaculture Farmers
  '121111': {
    alternative_titles: ['Fish Farmer'],
    specialisations: ['Hatchery Manager', 'Mussel Farmer', 'Oyster Farmer', 'Salmon Farmer']
  },

  // 1311 - Advertising, Public Relations and Sales Managers
  '131112': {
    alternative_titles: ['Marketing Director'],
    specialisations: ['Business Development Manager', 'Commercial Sales Director']
  },
  '131113': {
    alternative_titles: ['Media Director'],
    specialisations: ['Creative Director (Advertising)', 'Advertising Account Director']
  },
  '131114': {
    alternative_titles: ['Corporate Affairs Manager'],
    specialisations: ['Media Relations Manager', 'External Affairs Director']
  },

  // 1321-1325 - Business Administration & Specialist Managers
  '132111': {
    alternative_titles: ['Corporate Services Director'],
    specialisations: ['Administration Manager', 'Facilities Operations Manager']
  },
  '132211': {
    alternative_titles: ['Financial Controller'],
    specialisations: ['Corporate Treasurer', 'Finance Director']
  },
  '132311': {
    alternative_titles: ['Personnel Manager'],
    specialisations: ['Industrial Relations Manager', 'People & Culture Director']
  },
  '132411': {
    alternative_titles: ['Procurement Manager'],
    specialisations: ['Strategic Sourcing Director', 'Supply Chain Purchasing Lead']
  },
  '132511': {
    alternative_titles: ['R&D Director'],
    specialisations: ['Innovation Manager', 'Scientific Research Director']
  },

  // 1331-1336 - Construction, Production and Engineering Managers
  '133111': {
    alternative_titles: ['Building Project Manager'],
    specialisations: ['Construction Director', 'Major Projects Site Manager']
  },
  '133112': {
    alternative_titles: ['Licensed Builder'],
    specialisations: ['Residential Master Builder', 'Commercial Building Contractor']
  },
  '133211': {
    alternative_titles: ['Chief Engineer'],
    specialisations: ['Engineering Operations Director', 'Technical Director']
  },
  '133311': {
    alternative_titles: ['Plant Manager'],
    specialisations: ['Factory Operations Manager', 'Manufacturing Works Manager']
  },
  '133511': {
    alternative_titles: ['Mine Superintendent'],
    specialisations: ['Quarry Operations Manager', 'Open Cut Mine Manager']
  },
  '133512': {
    alternative_titles: ['Supply Chain Operations Manager'],
    specialisations: ['Logistics Director', 'Distribution Centre Manager']
  },
  '133611': {
    alternative_titles: ['Mining Project Director'],
    specialisations: ['Oil Field Superintendent', 'Petroleum Operations Manager']
  },

  // 1341-1344 - Health, Education & Welfare Managers
  '134111': {
    alternative_titles: ['Child Care Director'],
    specialisations: ['Early Learning Centre Director', 'Preschool Director']
  },
  '134211': {
    alternative_titles: ['Medical Director'],
    specialisations: ['Director of Clinical Services', 'Hospital Medical Superintendent']
  },
  '134212': {
    alternative_titles: ['Director of Nursing'],
    specialisations: ['Assistant Director of Nursing', 'Clinical Nurse Executive']
  },
  '134213': {
    alternative_titles: ['Health Clinic Manager'],
    specialisations: ['Community Health Centre Director', 'Primary Health Network Manager']
  },
  '134214': {
    alternative_titles: ['Community Care Director'],
    specialisations: ['Aged Care Facility Manager', 'Disability Support Services Director']
  },
  '134311': {
    alternative_titles: ['School Headmaster / Headmistress'],
    specialisations: ['High School Principal', 'Primary School Principal', 'Grammar School Head']
  },
  '134411': {
    alternative_titles: ['TAFE Director'],
    specialisations: ['Dean (Higher Education)', 'Faculty Head (Tertiary)']
  },
  '134412': {
    alternative_titles: ['Dean of Studies'],
    specialisations: ['Academic Registrar', 'Curriculum Director']
  },
  '134499': {
    alternative_titles: ['Training Centre Manager'],
    specialisations: ['Vocational College Director', 'RTO General Manager']
  },

  // 1351 - ICT Managers
  '135111': {
    alternative_titles: ['Chief Technology Officer (CTO)'],
    specialisations: ['Chief Information Security Officer (CISO)', 'IT Operations Director']
  },
  '135112': {
    alternative_titles: ['ICT Program Manager'],
    specialisations: ['ICT Development Manager', 'Agile Delivery Lead', 'Software Engineering Lead']
  },

  // 1411-1419 - Hospitality & Retail Managers
  '141111': {
    alternative_titles: ['Restaurateur'],
    specialisations: ['Food and Beverage Director', 'Bistro Operations Manager']
  },
  '141311': {
    alternative_titles: ['Hotelier', 'Publican'],
    specialisations: ['Resort Operations Director', 'Boutique Hotel General Manager']
  },
  '142111': {
    alternative_titles: ['Retail Store Manager'],
    specialisations: ['Department Store Manager', 'Supermarket General Manager']
  },

  // 2111-2124 - Arts, Media & Design Professionals
  '211111': {
    alternative_titles: ['Theatrical Performer'],
    specialisations: ['Voice-over Artist', 'Screen Actor', 'Stunt Performer']
  },
  '211211': {
    alternative_titles: ['Songwriter'],
    specialisations: ['Film Score Composer', 'Music Arranger']
  },
  '211212': {
    alternative_titles: ['Choir Master'],
    specialisations: ['Orchestral Conductor', 'Music Band Leader']
  },
  '211213': {
    alternative_titles: ['Session Musician'],
    specialisations: ['Orchestral Instrumentalist', 'Solo Concert Performer']
  },
  '211214': {
    alternative_titles: ['Vocalist'],
    specialisations: ['Opera Singer', 'Recording Vocal Artist']
  },
  '212111': {
    alternative_titles: ['Creative Director'],
    specialisations: ['Festival Director', 'Visual Arts Curator']
  },
  '212211': {
    alternative_titles: ['Novelist', 'Playwright'],
    specialisations: ['Screenwriter', 'Literary Author']
  },
  '212212': {
    alternative_titles: ['Commissioning Editor'],
    specialisations: ['Sub-editor', 'Manuscript Editor']
  },
  '212312': {
    alternative_titles: ['Filmmaker'],
    specialisations: ['Casting Director', 'Stage Director', 'Television Director']
  },
  '212314': {
    alternative_titles: ['Post-Production Editor'],
    specialisations: ['Digital Colorist', 'Offline / Online Video Editor']
  },
  '212411': {
    alternative_titles: ['Advertising Copywriter'],
    specialisations: ['Creative Copy Lead', 'SEO & Content Copywriter']
  },
  '212412': {
    alternative_titles: ['Editor-in-Chief'],
    specialisations: ['Managing Editor', 'Section Editor']
  },
  '212413': {
    alternative_titles: ['News Reporter'],
    specialisations: ['Investigative Journalist', 'Feature Writer', 'Political Columnist']
  },
  '212415': {
    alternative_titles: ['Documentation Specialist'],
    specialisations: ['API Technical Writer', 'Engineering Documentation Lead']
  },
  '212416': {
    alternative_titles: ['Broadcast Journalist'],
    specialisations: ['News Anchor', 'Field Correspondent', 'Television Producer']
  },

  // 2211-2212 - Accountants and Auditors
  '221111': {
    alternative_titles: ['Chartered Accountant', 'CPA'],
    specialisations: ['Financial Analyst', 'Insolvency Consultant', 'Insolvency Practitioner']
  },
  '221112': {
    alternative_titles: ['Cost Accountant'],
    specialisations: ['FP&A Specialist', 'Commercial Finance Analyst']
  },
  '221113': {
    alternative_titles: ['Taxation Consultant'],
    specialisations: ['Taxation Specialist', 'Corporate Tax Advisor']
  },
  '221213': {
    alternative_titles: ['Independent Auditor'],
    specialisations: ['Audit Partner', 'Statutory Financial Auditor']
  },
  '221214': {
    alternative_titles: ['Risk Assurance Officer'],
    specialisations: ['Risk Management Auditor', 'Compliance & Governance Auditor']
  },

  // 2221-2223 - Financial Brokers and Dealers
  '222112': {
    alternative_titles: ['Mortgage Broker'],
    specialisations: ['Commercial Lending Broker', 'Asset Finance Specialist']
  },
  '222113': {
    alternative_titles: ['Insurance Agent'],
    specialisations: ['Commercial Risk Broker', 'Reinsurance Broker']
  },
  '222211': {
    alternative_titles: ['Stockbroker'],
    specialisations: ['Foreign Exchange Dealer', 'Derivatives Trader', 'Equities Dealer']
  },
  '222311': {
    alternative_titles: ['Financial Planner'],
    specialisations: ['Wealth Management Adviser', 'Retirement Planning Specialist']
  },
  '222312': {
    alternative_titles: ['Portfolio Manager'],
    specialisations: ['Hedge Fund Manager', 'Asset Management Director']
  },

  // 2231 - Human Resource Professionals
  '223111': {
    alternative_titles: ['HR Business Partner'],
    specialisations: ['Workplace Relations Adviser', 'Talent Strategy Consultant']
  },
  '223112': {
    alternative_titles: ['Talent Acquisition Specialist'],
    specialisations: ['Executive Search Consultant', 'Technical Recruitment Specialist']
  },
  '223113': {
    alternative_titles: ['Industrial Relations Officer'],
    specialisations: ['Enterprise Agreement Negotiator', 'Union Liaison Officer']
  },

  // 2241-2249 - Information and Organisation Professionals
  '224111': {
    alternative_titles: ['Actuarial Analyst'],
    specialisations: ['Life Insurance Actuary', 'General Insurance Pricing Actuary']
  },
  '224112': {
    alternative_titles: ['Operations Research Analyst'],
    specialisations: ['Applied Mathematician', 'Algorithm Design Specialist']
  },
  '224113': {
    alternative_titles: ['Data Scientist'],
    specialisations: ['Biostatistician', 'Quantitative Data Analyst']
  },
  '224211': {
    alternative_titles: ['Records Manager'],
    specialisations: ['Digital Archivist', 'Historical Records Curator']
  },
  '224212': {
    alternative_titles: ['Gallery Curator'],
    specialisations: ['Museum Curator', 'Exhibitions Registrar']
  },
  '224311': {
    alternative_titles: ['Economic Analyst'],
    specialisations: ['Macroeconomist', 'Econometrician', 'Competition Economist']
  },
  '224412': {
    alternative_titles: ['Policy Officer'],
    specialisations: ['Strategic Policy Advisor', 'Government Regulatory Analyst']
  },
  '224711': {
    alternative_titles: ['Business Consultant'],
    specialisations: ['Strategy Consultant', 'Operations Transformation Specialist']
  },
  '224712': {
    alternative_titles: ['Business Process Analyst'],
    specialisations: ['Continuous Improvement Lead', 'Methods & Productivity Engineer']
  },

  // 2251-2254 - Sales, Marketing & PR Professionals
  '225111': {
    alternative_titles: ['Advertising Account Executive'],
    specialisations: ['Media Planner', 'Media Buyer', 'Campaign Strategist']
  },
  '225113': {
    alternative_titles: ['Marketing Consultant'],
    specialisations: ['Brand Manager', 'Product Marketing Manager', 'Growth Marketing Specialist']
  },
  '225211': {
    alternative_titles: ['IT Client Executive'],
    specialisations: ['Enterprise Technology Account Manager', 'SaaS Client Executive']
  },
  '225212': {
    alternative_titles: ['ICT Sales Director'],
    specialisations: ['Technology Solutions Sales Manager', 'Enterprise BD Lead']
  },
  '225311': {
    alternative_titles: ['PR Officer'],
    specialisations: ['Communications Specialist', 'Media Spokesperson', 'Crisis PR Lead']
  },

  // 2311 - Air Transport Professionals
  '231111': {
    alternative_titles: ['Airline Pilot'],
    specialisations: ['Commercial Airline Captain', 'First Officer']
  },
  '231113': {
    alternative_titles: ['Flight Instructor'],
    specialisations: ['Chief Flying Instructor', 'Instrument Rating Examiner']
  },
  '231114': {
    alternative_titles: ['Rotary Wing Pilot'],
    specialisations: ['Emergency Medical Services (EMS) Helicopter Pilot', 'Offshore Oil Rig Pilot']
  },

  // 2321-2326 - Architects, Designers and Planners
  '232111': {
    alternative_titles: ['Registered Architect'],
    specialisations: ['Commercial Architect', 'Residential Design Architect', 'Sustainable Building Architect']
  },
  '232112': {
    alternative_titles: ['Landscape Designer'],
    specialisations: ['Urban Landscape Architect', 'Environmental Landscape Planner']
  },
  '232212': {
    alternative_titles: ['Cadastral Surveyor'],
    specialisations: ['Engineering Surveyor', 'Geodetic Surveyor', 'Mining Surveyor']
  },
  '232213': {
    alternative_titles: ['Mapping Scientist'],
    specialisations: ['GIS Specialist', 'Digital Cartographer']
  },
  '232214': {
    alternative_titles: ['Spatial Data Analyst'],
    specialisations: ['Remote Sensing Specialist', 'Photogrammetrist']
  },
  '232311': {
    alternative_titles: ['Apparel Designer'],
    specialisations: ['Fashion Garment Designer', 'Costume Designer']
  },
  '232312': {
    alternative_titles: ['Product Designer'],
    specialisations: ['Ergonomic Industrial Designer', 'Consumer Product Concept Artist']
  },
  '232411': {
    alternative_titles: ['Commercial Artist'],
    specialisations: ['Brand Identity Designer', 'Publication & Editorial Designer']
  },
  '232412': {
    alternative_titles: ['Technical Illustrator'],
    specialisations: ['2D/3D Concept Artist', 'Digital Book Illustrator']
  },
  '232413': {
    alternative_titles: ['Digital Media Designer'],
    specialisations: ['Interaction Designer', 'Motion Graphics Designer', 'Visual Effects Artist']
  },
  '232414': {
    alternative_titles: ['UI Designer'],
    specialisations: ['Front-End UI Specialist', 'Web Experience Designer']
  },
  '232511': {
    alternative_titles: ['Interior Architect'],
    specialisations: ['Commercial Interior Designer', 'Hospitality Interior Designer']
  },
  '232611': {
    alternative_titles: ['Town Planner'],
    specialisations: ['Urban Development Strategist', 'Land Use & Environmental Planner']
  },

  // 2331-2339 - Engineering Professionals
  '233111': {
    alternative_titles: ['Process Engineer'],
    specialisations: ['Biochemical Engineer', 'Refining Process Engineer', 'Water Treatment Engineer']
  },
  '233112': {
    alternative_titles: ['Metallurgical Engineer'],
    specialisations: ['Ceramics Engineer', 'Polymer Materials Specialist']
  },
  '233211': {
    alternative_titles: ['Civil Consulting Engineer'],
    specialisations: ['Structural Engineer', 'Hydraulic Engineer', 'Geotechnical Engineer']
  },
  '233212': {
    alternative_titles: ['Soil Mechanics Engineer'],
    specialisations: ['Foundation Engineering Specialist', 'Tunnelling Engineer']
  },
  '233213': {
    alternative_titles: ['Building Economist'],
    specialisations: ['Construction Cost Consultant', 'Commercial Estimator']
  },
  '233214': {
    alternative_titles: ['Bridge Engineer'],
    specialisations: ['High-Rise Structural Engineer', 'Concrete & Steel Structure Specialist']
  },
  '233215': {
    alternative_titles: ['Traffic Engineer'],
    specialisations: ['Highway Planning Engineer', 'Public Transit Systems Engineer']
  },
  '233311': {
    alternative_titles: ['Power Systems Engineer'],
    specialisations: ['Electrical Power Engineer', 'Renewable Grid Integration Specialist', 'High Voltage Substation Engineer']
  },
  '233411': {
    alternative_titles: ['Communications Engineer'],
    specialisations: ['Telecommunications Engineer', 'Embedded Systems Engineer', 'RF Systems Specialist']
  },
  '233511': {
    alternative_titles: ['Process Improvement Engineer'],
    specialisations: ['Manufacturing Systems Engineer', 'Lean Six Sigma Lead']
  },
  '233512': {
    alternative_titles: ['Airconditioning Engineer'],
    specialisations: ['Building Services Engineer', 'Heating and Ventilation Engineer', 'Mechatronics Engineer']
  },
  '233513': {
    alternative_titles: ['Manufacturing Engineer'],
    specialisations: ['Plant Reliability Engineer', 'Automation & Robotics Engineer']
  },
  '233611': {
    alternative_titles: ['Mine Planning Engineer'],
    specialisations: ['Open Cut Mining Engineer', 'Underground Mine Ventilation Engineer']
  },
  '233612': {
    alternative_titles: ['Drilling Engineer'],
    specialisations: ['Reservoir Engineer', 'Production Petroleum Engineer']
  },
  '233911': {
    alternative_titles: ['Aerospace Engineer'],
    specialisations: ['Avionics Engineer', 'Aircraft Structural Design Engineer']
  },
  '233912': {
    alternative_titles: ['Irrigation Engineer'],
    specialisations: ['Precision Agricultural Systems Specialist', 'Soil & Water Resource Engineer']
  },
  '233913': {
    alternative_titles: ['Bioengineer'],
    specialisations: ['Medical Device Design Engineer', 'Prosthetics Technology Engineer']
  },
  '233914': {
    alternative_titles: ['Engineering Technologist'],
    specialisations: ['Aeronautical Engineering Technologist', 'Agricultural Engineering Technologist', 'Industrial Systems Technologist']
  },
  '233915': {
    alternative_titles: ['Water Resources Engineer'],
    specialisations: ['Remediation Engineer', 'Catchment Management Engineer']
  },
  '233916': {
    alternative_titles: ['Naval Architect'],
    specialisations: ['Marine Propulsion Systems Engineer', 'Ship Design Specialist']
  },

  // 2341-2349 - Natural and Physical Science Professionals
  '234111': {
    alternative_titles: ['Agronomist'],
    specialisations: ['Agricultural Extension Officer', 'Soil Nutrition Consultant']
  },
  '234112': {
    alternative_titles: ['Crop Scientist'],
    specialisations: ['Animal Geneticist', 'Pasture Agronomist']
  },
  '234113': {
    alternative_titles: ['Forest Scientist'],
    specialisations: ['Silviculture Specialist', 'Forest Operations Planner']
  },
  '234211': {
    alternative_titles: ['Analytical Chemist'],
    specialisations: ['Organic Chemist', 'Quality Assurance Chemist', 'Polymer Chemist']
  },
  '234212': {
    alternative_titles: ['Food Scientist'],
    specialisations: ['Food Product Development Specialist', 'HACCP Safety Scientist']
  },
  '234311': {
    alternative_titles: ['Park Ranger'],
    specialisations: ['Wildlife Conservation Officer', 'National Parks Management Officer']
  },
  '234312': {
    alternative_titles: ['Environmental Auditor'],
    specialisations: ['Contaminated Land Consultant', 'Environmental Impact Assessor']
  },
  '234313': {
    alternative_titles: ['Ecologist'],
    specialisations: ['Biodiversity Research Scientist', 'Climate Impact Scientist']
  },
  '234411': {
    alternative_titles: ['Exploration Geologist'],
    specialisations: ['Hydrogeologist', 'Mine Geologist', 'Geochemical Specialist']
  },
  '234412': {
    alternative_titles: ['Seismologist'],
    specialisations: ['Geomagnetist', 'Exploration Geophysicist']
  },
  '234511': {
    alternative_titles: ['Biologist'],
    specialisations: ['Botanist', 'Zoologist', 'Cellular Biologist']
  },
  '234513': {
    alternative_titles: ['Enzymologist'],
    specialisations: ['Protein Biochemist', 'Metabolic Pathway Scientist']
  },
  '234514': {
    alternative_titles: ['Geneticist'],
    specialisations: ['Genomics Specialist', 'Molecular Biologist']
  },
  '234515': {
    alternative_titles: ['Plant Pathologist'],
    specialisations: ['Taxonomic Botanist', 'Herbarium Botanist']
  },
  '234516': {
    alternative_titles: ['Oceanographer'],
    specialisations: ['Fisheries Biologist', 'Coral Reef Ecologist']
  },
  '234517': {
    alternative_titles: ['Bacteriologist'],
    specialisations: ['Virologist', 'Clinical Diagnostic Microbiologist']
  },
  '234518': {
    alternative_titles: ['Entomologist'],
    specialisations: ['Mammalogist', 'Wildlife Ecologist', 'Ornithologist']
  },
  '234611': {
    alternative_titles: ['Medical Scientist'],
    specialisations: ['Diagnostic Pathology Scientist', 'Haematologist (Scientist)', 'Clinical Immunologist']
  },
  '234711': {
    alternative_titles: ['Veterinary Surgeon'],
    specialisations: ['Small Animal Clinician', 'Equine Specialist', 'Livestock Veterinary Officer']
  },
  '234914': {
    alternative_titles: ['Medical Physicist'],
    specialisations: ['Radiation Oncology Physicist', 'Nuclear Physicist', 'Quantum Research Scientist']
  },

  // 2411-2422 - Education Professionals
  '241111': {
    alternative_titles: ['Kindergarten Teacher'],
    specialisations: ['Preschool Director', 'Early Childhood Educational Leader']
  },
  '241213': {
    alternative_titles: ['Elementary School Teacher'],
    specialisations: ['Primary Curriculum Lead', 'Literacy / Numeracy Specialist']
  },
  '241311': {
    alternative_titles: ['Junior Secondary Teacher'],
    specialisations: ['Middle Years Program Coordinator']
  },
  '241411': {
    alternative_titles: ['High School Teacher'],
    specialisations: ['Senior Secondary Subject Lead', 'Head of Faculty (Secondary)']
  },
  '241511': {
    alternative_titles: ['Teacher of the Deaf'],
    specialisations: ['Teacher of the Blind', 'Special Education Inclusive Leader']
  },
  '242111': {
    alternative_titles: ['University Professor'],
    specialisations: ['Associate Lecturer', 'Senior Lecturer', 'Research Fellow']
  },
  '242211': {
    alternative_titles: ['TAFE Teacher'],
    specialisations: ['Vocational Trainer & Assessor', 'Industry Skills Instructor']
  },

  // 2511-2519 - Allied Health Professionals
  '251111': {
    alternative_titles: ['Clinical Dietitian'],
    specialisations: ['Sports Dietitian', 'Paediatric Dietitian', 'Renal Dietitian']
  },
  '251211': {
    alternative_titles: ['Medical Imaging Technologist'],
    specialisations: ['MRI Technologist', 'Sonographer', 'CT Diagnostic Radiographer']
  },
  '251212': {
    alternative_titles: ['Radiation Therapist'],
    specialisations: ['Linear Accelerator Specialist', 'Stereotactic Radiation Therapist']
  },
  '251213': {
    alternative_titles: ['Nuclear Medicine Specialist'],
    specialisations: ['PET/CT Technologist', 'Radioisotope Imaging Specialist']
  },
  '251214': {
    alternative_titles: ['Ultrasonographer'],
    specialisations: ['Echocardiographer', 'Vascular Sonographer', 'Obstetric Sonographer']
  },
  '251311': {
    alternative_titles: ['Public Health Inspector'],
    specialisations: ['Environmental Health Officer', 'Food Safety Regulatory Officer']
  },
  '251312': {
    alternative_titles: ['OHS Specialist'],
    specialisations: ['Workplace Safety Officer', 'Ergonomist', 'Industrial Hygiene Lead']
  },
  '251411': {
    alternative_titles: ['Ophthalmic Optician'],
    specialisations: ['Behavioural Optometrist', 'Contact Lens Specialist', 'Paediatric Optometrist']
  },
  '251511': {
    alternative_titles: ['Clinical Pharmacist'],
    specialisations: ['Inpatient Hospital Pharmacist', 'Antimicrobial Stewardship Pharmacist']
  },
  '251512': {
    alternative_titles: ['Pharmaceutical Chemist'],
    specialisations: ['Formulation Scientist', 'Regulatory Affairs Pharmacist']
  },
  '251513': {
    alternative_titles: ['Community Pharmacist'],
    specialisations: ['Managing Pharmacist', 'Dispensary Consultant']
  },
  '251912': {
    alternative_titles: ['Clinical Prosthetist'],
    specialisations: ['Orthotist', 'Bionic Limb Rehabilitation Specialist']
  },

  // 2521-2527 - Therapy Professionals
  '252111': {
    alternative_titles: ['Doctor of Chiropractic'],
    specialisations: ['Paediatric Chiropractor', 'Sports Chiropractic Practitioner']
  },
  '252112': {
    alternative_titles: ['Cranial Osteopath'],
    specialisations: ['Musculoskeletal Osteopath', 'Sports Osteopath']
  },
  '252211': {
    alternative_titles: ['Traditional Chinese Medicine Practitioner'],
    specialisations: ['Clinical Acupuncturist', 'Herbal Medicine Practitioner']
  },
  '252311': {
    alternative_titles: ['Orthodontist'],
    specialisations: ['Periodontist', 'Prosthodontist', 'Endodontist', 'Paediatric Dentist']
  },
  '252312': {
    alternative_titles: ['Dental Practitioner'],
    specialisations: ['General Dental Surgeon', 'Cosmetic Dentist']
  },
  '252411': {
    alternative_titles: ['Ergonomics Consultant'],
    specialisations: ['Paediatric Occupational Therapist', 'NDIS Rehabilitation Specialist', 'Hand Therapist']
  },
  '252511': {
    alternative_titles: ['Physical Therapist'],
    specialisations: ['Musculoskeletal Physiotherapist', 'Neurological Physiotherapist', 'Sports Physiotherapist', 'Cardiorespiratory Physio']
  },
  '252611': {
    alternative_titles: ['Chiropodist'],
    specialisations: ['Sports Podiatrist', 'High Risk Diabetic Foot Specialist']
  },
  '252711': {
    alternative_titles: ['Hearing Specialist'],
    specialisations: ['Paediatric Audiologist', 'Cochlear Implant Specialist']
  },
  '252712': {
    alternative_titles: ['Speech Therapist'],
    specialisations: ['Paediatric Speech Pathologist', 'Dysphagia Specialist', 'Fluency Specialist']
  },

  // 2531-2539 - Medical Practitioners
  '253111': {
    alternative_titles: ['Medical Practitioner (General)'],
    specialisations: ['Family Physician', 'Primary Care Physician', 'Rural Generalist']
  },
  '253112': {
    alternative_titles: ['Hospital Resident'],
    specialisations: ['Junior House Officer', 'Intern (Medical)']
  },
  '253211': {
    alternative_titles: ['Anaesthesiology Consultant'],
    specialisations: ['Intensive Care Anaesthetist', 'Paediatric Anaesthetist', 'Pain Medicine Specialist']
  },
  '253311': {
    alternative_titles: ['Consultant Physician'],
    specialisations: ['Internal Medicine Specialist', 'Acute General Physician']
  },
  '253312': {
    alternative_titles: ['Cardiology Consultant'],
    specialisations: ['Interventional Cardiologist', 'Cardiac Electrophysiologist']
  },
  '253313': {
    alternative_titles: ['Clinical Haematologist'],
    specialisations: ['Bone Marrow Transplant Specialist', 'Haemato-Oncologist']
  },
  '253314': {
    alternative_titles: ['Cancer Specialist'],
    specialisations: ['Medical Oncologist', 'Solid Tumour Clinical Oncologist']
  },
  '253315': {
    alternative_titles: ['Endocrine Specialist'],
    specialisations: ['Diabetologist', 'Thyroid Disorder Specialist']
  },
  '253316': {
    alternative_titles: ['Gastroenterology Consultant'],
    specialisations: ['Hepatologist', 'Endoscopy Specialist']
  },
  '253317': {
    alternative_titles: ['Intensivist'],
    specialisations: ['Critical Care Medicine Consultant', 'ICU Specialist']
  },
  '253318': {
    alternative_titles: ['Neurology Consultant'],
    specialisations: ['Epileptologist', 'Stroke Specialist', 'Movement Disorders Neurologist']
  },
  '253321': {
    alternative_titles: ['Paediatric Physician'],
    specialisations: ['Neonatologist', 'Paediatric Cardiologist', 'Developmental Paediatrician']
  },
  '253322': {
    alternative_titles: ['Nephrologist'],
    specialisations: ['Renal Dialysis Specialist', 'Transplant Nephrologist']
  },
  '253323': {
    alternative_titles: ['Rheumatology Consultant'],
    specialisations: ['Paediatric Rheumatologist', 'Autoimmune Disease Specialist']
  },
  '253324': {
    alternative_titles: ['Pulmonologist'],
    specialisations: ['Respiratory Physician', 'Sleep Medicine Specialist']
  },
  '253411': {
    alternative_titles: ['Psychiatry Consultant'],
    specialisations: ['Child and Adolescent Psychiatrist', 'Forensic Psychiatrist', 'Addiction Psychiatrist']
  },
  '253511': {
    alternative_titles: ['General Surgeon'],
    specialisations: ['Colorectal Surgeon', 'Upper GI Surgeon', 'Trauma Surgeon', 'Endocrine Surgeon']
  },
  '253512': {
    alternative_titles: ['Cardiac Surgeon'],
    specialisations: ['Thoracic Surgeon', 'Cardiothoracic Transplant Surgeon']
  },
  '253513': {
    alternative_titles: ['Spinal Neurosurgeon'],
    specialisations: ['Cranial Neurosurgeon', 'Paediatric Neurosurgeon']
  },
  '253514': {
    alternative_titles: ['Orthopaedic Surgeon'],
    specialisations: ['Joint Replacement Surgeon', 'Orthopaedic Spine Surgeon', 'Sports Knee/Shoulder Surgeon']
  },
  '253515': {
    alternative_titles: ['ENT Surgeon'],
    specialisations: ['Otolaryngologist', 'Head and Neck Oncological Surgeon']
  },
  '253516': {
    alternative_titles: ['Paediatric General Surgeon'],
    specialisations: ['Neonatal Surgeon', 'Paediatric Urological Surgeon']
  },
  '253517': {
    alternative_titles: ['Reconstructive Surgeon'],
    specialisations: ['Cosmetic Surgeon', 'Hand Surgeon', 'Burns Specialist Surgeon']
  },
  '253518': {
    alternative_titles: ['Urology Consultant'],
    specialisations: ['Urological Oncologist', 'Robotic Urological Surgeon']
  },
  '253521': {
    alternative_titles: ['Endovascular Surgeon'],
    specialisations: ['Vascular Surgeon', 'Aortic Surgery Specialist']
  },
  '253911': {
    alternative_titles: ['Skin Specialist'],
    specialisations: ['Dermatologist', 'Mohs Micrographic Surgeon']
  },
  '253912': {
    alternative_titles: ['Emergency Physician'],
    specialisations: ['Trauma Resuscitation Specialist', 'Emergency Medicine Director']
  },
  '253913': {
    alternative_titles: ['OB/GYN Consultant'],
    specialisations: ['Maternal-Fetal Medicine Specialist', 'Gynaecological Oncologist', 'Obstetrician and Gynaecologist']
  },
  '253914': {
    alternative_titles: ['Eye Surgeon'],
    specialisations: ['Ophthalmologist', 'Vitreoretinal Surgeon', 'Glaucoma Specialist']
  },
  '253915': {
    alternative_titles: ['Pathology Consultant'],
    specialisations: ['Anatomical Pathologist', 'Forensic Pathologist', 'Haematopathologist']
  },
  '253917': {
    alternative_titles: ['Radiology Consultant'],
    specialisations: ['Diagnostic Radiologist', 'Interventional Radiologist', 'Neuroradiologist']
  },

  // 2541-2544 - Midwives and Registered Nurses
  '254111': {
    alternative_titles: ['Maternity Nurse'],
    specialisations: ['Community Midwife', 'Lactation Consultant', 'Birth Suite Midwife']
  },
  '254411': {
    alternative_titles: ['Advanced Practice Nurse'],
    specialisations: ['Emergency Nurse Practitioner', 'Primary Care Nurse Practitioner']
  },
  '254412': {
    alternative_titles: ['Geriatric Nurse'],
    specialisations: ['Gerontological Nurse', 'Residential Aged Care Clinical Care Coordinator']
  },
  '254413': {
    alternative_titles: ['Plunket Nurse'],
    specialisations: ['Child and Family Health Nurse', 'Maternal Child Health Nurse']
  },
  '254414': {
    alternative_titles: ['District Nurse'],
    specialisations: ['Community Health Nurse', 'Home Visiting Nurse']
  },
  '254415': {
    alternative_titles: ['Critical Care Nurse'],
    specialisations: ['Intensive Care Nurse', 'Trauma Nurse', 'Emergency Department RN']
  },
  '254416': {
    alternative_titles: ['Disability Care Nurse'],
    specialisations: ['Developmental Disability RN', 'Specialist Accommodation RN']
  },
  '254417': {
    alternative_titles: ['Rehabilitation Nurse'],
    specialisations: ['Disability and Rehabilitation RN', 'Spinal Injury Rehabilitation Nurse']
  },
  '254418': {
    alternative_titles: ['Acute Care Nurse'],
    specialisations: ['Medical Ward RN', 'Oncology Nurse', 'Cardiology Nurse']
  },
  '254421': {
    alternative_titles: ['Practice Nurse'],
    specialisations: ['General Practice RN', 'Immunisation Nurse']
  },
  '254422': {
    alternative_titles: ['Psychiatric Nurse'],
    specialisations: ['Mental Health RN', 'Community Mental Health Nurse', 'Crisis Assessment RN']
  },
  '254423': {
    alternative_titles: ['Theatre Nurse'],
    specialisations: ['Operating Theatre Nurse', 'Recovery Room Nurse', 'Scrub / Scout RN']
  },
  '254424': {
    alternative_titles: ['Post-operative Nurse'],
    specialisations: ['Surgical Ward RN', 'Day Surgery RN']
  },
  '254425': {
    alternative_titles: ['Paediatric RN'],
    specialisations: ['Neonatal Intensive Care Nurse (NICU)', 'Paediatric Intensive Care Nurse (PICU)']
  },
  '254499': {
    alternative_titles: ['Clinical Nurse Specialist'],
    specialisations: ['Infection Control Nurse', 'Clinical Nurse Educator', 'Stomal Therapy Nurse']
  },

  // 2611-2633 - ICT Professionals
  '261111': {
    alternative_titles: ['BA (ICT)'],
    specialisations: ['Business Systems Analyst', 'Agile Business Analyst']
  },
  '261112': {
    alternative_titles: ['Enterprise Systems Analyst'],
    specialisations: ['Systems Architect', 'Solutions Designer']
  },
  '261211': {
    alternative_titles: ['Interactive Media Developer'],
    specialisations: ['Digital Content Producer', 'Game Developer (Technical)']
  },
  '261212': {
    alternative_titles: ['Full Stack Developer'],
    specialisations: ['Front End Developer', 'Back End Developer', 'React/Node Web Specialist']
  },
  '261311': {
    alternative_titles: ['Software Programmer'],
    specialisations: ['Analyst Programmer', 'Applications Programmer']
  },
  '261312': {
    alternative_titles: ['Software Developer'],
    specialisations: ['Applications Developer', 'Database Developer', 'Systems Developer']
  },
  '261313': {
    alternative_titles: ['Software Architect'],
    specialisations: ['Computer Applications Engineer', 'Database Engineer', 'Systems Architect', 'Cloud Native Architect']
  },
  '261314': {
    alternative_titles: ['QA Analyst'],
    specialisations: ['Automation Test Engineer', 'Performance & Load Test Engineer']
  },
  '261399': {
    alternative_titles: ['Programmer nec'],
    specialisations: ['DevOps Engineer', 'Release Engineer']
  },
  '262111': {
    alternative_titles: ['DBA'],
    specialisations: ['Database Administrator', 'Data Warehouse Engineer', 'PostgreSQL/Oracle DBA']
  },
  '262112': {
    alternative_titles: ['Cyber Security Specialist'],
    specialisations: ['Information Security Analyst', 'Security Operations Lead', 'Penetration Tester']
  },
  '262113': {
    alternative_titles: ['Sysadmin'],
    specialisations: ['Cloud Infrastructure Administrator', 'Linux Systems Engineer', 'Windows Server Specialist']
  },
  '263111': {
    alternative_titles: ['Network Engineer'],
    specialisations: ['Network Administrator', 'Network Support Engineer', 'Cisco / Juniper Network Engineer']
  },
  '263112': {
    alternative_titles: ['LAN/WAN Administrator'],
    specialisations: ['Network Operations Center (NOC) Engineer', 'Network Security Administrator']
  },
  '263113': {
    alternative_titles: ['Network Consultant'],
    specialisations: ['Network Planning Analyst', 'Communications Capacity Planner']
  },
  '263211': {
    alternative_titles: ['Quality Assurance Specialist'],
    specialisations: ['Software QA Engineer', 'Process Testing Engineer']
  },
  '263212': {
    alternative_titles: ['Technical Support Specialist'],
    specialisations: ['Tier 3 Support Engineer', 'Solutions Support Lead']
  },
  '263213': {
    alternative_titles: ['Systems Verification Engineer'],
    specialisations: ['System Integration Tester', 'Acceptance Test Engineer']
  },
  '263311': {
    alternative_titles: ['Telco Engineer'],
    specialisations: ['Optical Network Engineer', 'Radio Frequency (RF) Engineer', '5G Mobile Core Engineer']
  },
  '263312': {
    alternative_titles: ['Fiber Network Engineer'],
    specialisations: ['Telecommunications Network Engineer', 'Network Capacity Planner']
  },

  // 2711-2725 - Legal, Social and Welfare Professionals
  '271111': {
    alternative_titles: ['Counsel', 'Advocate'],
    specialisations: ['Senior Counsel (SC)', 'King\'s Counsel (KC)', 'Criminal Defense Barrister']
  },
  '271211': {
    alternative_titles: ['Tribunal Member'],
    specialisations: ['Magistrate', 'Court Commissioner', 'Administrative Appeals Arbitrator']
  },
  '271311': {
    alternative_titles: ['Lawyer', 'Legal Practitioner'],
    specialisations: ['Commercial Solicitor', 'Family Law Specialist', 'Property & Conveyancing Solicitor', 'Litigation Associate']
  },
  '272111': {
    alternative_titles: ['Vocational Guidance Officer'],
    specialisations: ['Careers Counsellor', 'Employment Transition Coach']
  },
  '272112': {
    alternative_titles: ['Addiction Specialist'],
    specialisations: ['Drug and Alcohol Counsellor', 'Substance Abuse Clinician']
  },
  '272113': {
    alternative_titles: ['Relationship Therapist'],
    specialisations: ['Family and Marriage Counsellor', 'Couples Therapist']
  },
  '272114': {
    alternative_titles: ['Vocational Rehabilitation Specialist'],
    specialisations: ['Rehabilitation Counsellor', 'Workplace Injury Return-to-Work Coordinator']
  },
  '272115': {
    alternative_titles: ['School Counsellor'],
    specialisations: ['Student Wellbeing Coordinator', 'Guidance Officer']
  },
  '272199': {
    alternative_titles: ['Therapeutic Counsellor'],
    specialisations: ['Bereavement Counsellor', 'Crisis Support Counsellor']
  },
  '272311': {
    alternative_titles: ['Doctor of Clinical Psychology'],
    specialisations: ['Child Clinical Psychologist', 'Neuropsychologist', 'Cognitive Behavioural Specialist']
  },
  '272312': {
    alternative_titles: ['School Psychologist'],
    specialisations: ['Educational Psychologist', 'Child Development Specialist']
  },
  '272313': {
    alternative_titles: ['Industrial Psychologist'],
    specialisations: ['Organisational Psychologist', 'Human Factors Specialist']
  },
  '272314': {
    alternative_titles: ['Psychoanalyst'],
    specialisations: ['Psychotherapist', 'Integrative Psychotherapist']
  },
  '272399': {
    alternative_titles: ['Registered Psychologist'],
    specialisations: ['Forensic Psychologist', 'Sports Psychologist', 'Health Psychologist']
  },
  '272411': {
    alternative_titles: ['Community Development Officer'],
    specialisations: ['Youth Development Lead', 'Settlement Support Caseworker']
  },
  '272511': {
    alternative_titles: ['Caseworker'],
    specialisations: ['Medical Social Worker', 'Child Protection Practitioner', 'Hospital Clinical Social Worker', 'Mental Health Social Worker']
  },

  // 3111-3132 - Engineering & Science Technicians
  '311111': {
    alternative_titles: ['Field Research Assistant'],
    specialisations: ['Agricultural Field Technician', 'Agronomy Support Officer']
  },
  '311211': {
    alternative_titles: ['Pathology Technician'],
    specialisations: ['Medical Laboratory Technician', 'Histology Technician', 'Phlebotomy Technician']
  },
  '311213': {
    alternative_titles: ['Dispensary Technician'],
    specialisations: ['Pharmacy Technician', 'Hospital Dispensary Assistant']
  },
  '311311': {
    alternative_titles: ['Marine Fisheries Inspector'],
    specialisations: ['Fisheries Officer', 'Aquatic Compliance Officer']
  },
  '311411': {
    alternative_titles: ['Analytical Lab Assistant'],
    specialisations: ['Chemistry Technician', 'Quality Control Lab Technician']
  },
  '311412': {
    alternative_titles: ['Geological Field Assistant'],
    specialisations: ['Earth Science Technical Officer', 'Seismic Field Officer']
  },
  '311413': {
    alternative_titles: ['Biological Lab Technician'],
    specialisations: ['Life Science Technician', 'Microbiology Lab Officer']
  },
  '312111': {
    alternative_titles: ['CAD Draftsperson'],
    specialisations: ['Architectural Draftsperson', 'Revit / BIM Modeler']
  },
  '312112': {
    alternative_titles: ['Assistant Site Manager'],
    specialisations: ['Building Associate', 'Construction Supervisor Associate']
  },
  '312113': {
    alternative_titles: ['Building Certifier'],
    specialisations: ['Building Inspector', 'Council Compliance Inspector']
  },
  '312114': {
    alternative_titles: ['Quantity Estimator'],
    specialisations: ['Construction Estimator', 'Cost Planning Technician']
  },
  '312211': {
    alternative_titles: ['Civil CAD Technician'],
    specialisations: ['Civil Engineering Draftsperson', 'Road & Drainage Drafter']
  },
  '312212': {
    alternative_titles: ['Materials Testing Technician'],
    specialisations: ['Civil Engineering Technician', 'Geotechnical Testing Officer']
  },
  '312311': {
    alternative_titles: ['Electrical CAD Drafter'],
    specialisations: ['Electrical Engineering Draftsperson', 'Switchboard Drafter']
  },
  '312312': {
    alternative_titles: ['Electrical Substation Technician'],
    specialisations: ['Electrical Engineering Technician', 'High Voltage Relay Technician']
  },
  '312411': {
    alternative_titles: ['PCB Design Drafter'],
    specialisations: ['Electronic Engineering Draftsperson', 'Circuit Layout Specialist']
  },
  '312412': {
    alternative_titles: ['Avionics Technician'],
    specialisations: ['Electronic Engineering Technician', 'Telemetry Systems Officer']
  },
  '312511': {
    alternative_titles: ['HVAC Drafter'],
    specialisations: ['Mechanical Engineering Draftsperson', 'SolidWorks / Inventor Modeler']
  },
  '312512': {
    alternative_titles: ['Tooling Technician'],
    specialisations: ['Mechanical Engineering Technician', 'Hydraulic Systems Specialist']
  },
  '313111': {
    alternative_titles: ['Computer Repair Technician'],
    specialisations: ['Hardware Technician', 'Desktop Support Engineer']
  },
  '313112': {
    alternative_titles: ['Helpdesk Technician'],
    specialisations: ['ICT Customer Support Officer', 'Service Desk Analyst', 'IT Operations Support']
  },
  '313113': {
    alternative_titles: ['Webmaster'],
    specialisations: ['Web Administrator', 'Content Management Specialist']
  },
  '313211': {
    alternative_titles: ['Cell Site Engineer'],
    specialisations: ['Telecommunications Field Engineer', 'Tower Technician']
  },
  '313212': {
    alternative_titles: ['Fiber Network Designer'],
    specialisations: ['Telecommunications Network Planner', 'NBN Network Designer']
  },
  '313213': {
    alternative_titles: ['RF Test Officer'],
    specialisations: ['Telecommunications Technical Officer', 'Microwave Link Technician']
  },
  '313214': {
    alternative_titles: ['Cable Jointer'],
    specialisations: ['Telecommunications Linesworker', 'Copper & Fiber Splicer']
  },

  // 3211-3242 - Automotive & Engineering Trades
  '321111': {
    alternative_titles: ['Auto Sparky'],
    specialisations: ['Automotive Electrician', 'Heavy Vehicle Auto Electrician', 'EV Systems Technician']
  },
  '321211': {
    alternative_titles: ['Auto Mechanic'],
    specialisations: ['Motor Mechanic (General)', 'Automatic Transmission Specialist', 'Brake & Suspension Specialist']
  },
  '321212': {
    alternative_titles: ['Heavy Diesel Fitter'],
    specialisations: ['Diesel Motor Mechanic', 'Mining Mobile Plant Mechanic', 'Heavy Vehicle Technician']
  },
  '321213': {
    alternative_titles: ['Small Engine Mechanic'],
    specialisations: ['Motorcycle Mechanic', 'Powersports Technician']
  },
  '322211': {
    alternative_titles: ['Coppersmith'],
    specialisations: ['Sheetmetal Trades Worker', 'Ductwork Fabricator']
  },
  '322311': {
    alternative_titles: ['Boilermaker'],
    specialisations: ['Metal Fabricator', 'Structural Steel Fabricator', 'Pressure Vessel Fabricator']
  },
  '322312': {
    alternative_titles: ['Pipeline Welder'],
    specialisations: ['Pressure Welder', '6G Coded Welder']
  },
  '322313': {
    alternative_titles: ['MIG/TIG Welder'],
    specialisations: ['Welder (First Class)', 'Aluminium & Stainless Welder']
  },
  '323211': {
    alternative_titles: ['Mechanical Fitter'],
    specialisations: ['Fitter (General)', 'Diesel Fitter', 'Plant Maintenance Fitter']
  },
  '323212': {
    alternative_titles: ['Machinist (First Class)'],
    specialisations: ['Fitter and Turner', 'Precision Lathe & Mill Operator']
  },
  '323214': {
    alternative_titles: ['CNC Programmer / Operator'],
    specialisations: ['Metal Machinist (First Class)', 'Tool and Cutter Grinder']
  },
  '324111': {
    alternative_titles: ['Auto Body Repairer'],
    specialisations: ['Panelbeater', 'Chassis Alignment Specialist', 'Smash Repairer']
  },
  '324211': {
    alternative_titles: ['Automotive Spray Painter'],
    specialisations: ['Vehicle Painter', 'Custom Refinish Specialist']
  },

  // 3311-3341 - Construction Trades
  '331111': {
    alternative_titles: ['Blocklayer'],
    specialisations: ['Bricklayer', 'Refractory Bricklayer', 'Heritage Tuckpointer']
  },
  '331112': {
    alternative_titles: ['Monumental Mason'],
    specialisations: ['Stonemason', 'Heritage Restoration Stonemason']
  },
  '331211': {
    alternative_titles: ['Master Carpenter'],
    specialisations: ['Carpenter and Joiner', 'Formwork Carpenter', 'Framing Specialist']
  },
  '331212': {
    alternative_titles: ['Framing Carpenter'],
    specialisations: ['Carpenter', 'Fixing & Finishing Carpenter', 'Decking & Pergola Builder']
  },
  '331213': {
    alternative_titles: ['Architectural Joiner'],
    specialisations: ['Joiner', 'Staircase Builder', 'Bespoke Window & Door Maker']
  },
  '332211': {
    alternative_titles: ['Painter and Decorator'],
    specialisations: ['Painting Trades Worker', 'Commercial Painter', 'Specialist Finishes Decorator']
  },
  '333111': {
    alternative_titles: ['Leadlight Glazier'],
    specialisations: ['Glazier', 'Commercial Glass Installer', 'Curtain Wall Specialist']
  },
  '333211': {
    alternative_titles: ['Drywall Plasterer'],
    specialisations: ['Fibrous Plasterer', 'Gyprock Specialist', 'Cornice Fixer']
  },
  '333212': {
    alternative_titles: ['Rendering Tradesperson'],
    specialisations: ['Solid Plasterer', 'Venetian Plaster Specialist', 'Heritage Stucco Worker']
  },
  '333411': {
    alternative_titles: ['Ceramic Tiler'],
    specialisations: ['Wall and Floor Tiler', 'Mosaic Tile Specialist', 'Waterproofing Installer']
  },
  '334111': {
    alternative_titles: ['Licensed Plumber'],
    specialisations: ['Plumber (General)', 'Commercial Sanitary Plumber', 'Water Supply Specialist']
  },
  '334112': {
    alternative_titles: ['HVAC Plumber'],
    specialisations: ['Airconditioning & Mechanical Services Plumber', 'Chilled Water Piping Installer']
  },
  '334113': {
    alternative_titles: ['Licensed Drainer'],
    specialisations: ['Drainer', 'Civil Stormwater & Sewer Installer']
  },
  '334114': {
    alternative_titles: ['Licensed Gasfitter'],
    specialisations: ['Gasfitter', 'LPG / Natural Gas Appliance Installer']
  },
  '334115': {
    alternative_titles: ['Roof Cladder'],
    specialisations: ['Roof Plumber', 'Colorbond Metal Roofing Specialist']
  },

  // 3411-3423 - Electrotechnology Trades
  '341111': {
    alternative_titles: ['Licensed Electrician', 'Sparky'],
    specialisations: ['Electrician (General)', 'Industrial Electrician', 'Commercial Electrical Contractor']
  },
  '341112': {
    alternative_titles: ['PLC Automation Electrician'],
    specialisations: ['Electrician (Special Class)', 'Industrial Instrumentation Electrician', 'Mining Electrical Specialist']
  },
  '341113': {
    alternative_titles: ['Elevator Technician'],
    specialisations: ['Lift Mechanic', 'Escalator Service Specialist']
  },
  '342111': {
    alternative_titles: ['Fridge Mechanic'],
    specialisations: ['Airconditioning and Refrigeration Mechanic', 'Commercial Coolroom Technician', 'Supermarket Refrigeration Specialist']
  },
  '342211': {
    alternative_titles: ['Powerlines Worker'],
    specialisations: ['Electrical Linesworker', 'High Voltage Transmission Linesperson']
  },
  '342212': {
    alternative_titles: ['HV Cable Jointer'],
    specialisations: ['Technical Cable Jointer', 'Underground Power Jointer']
  },
  '342313': {
    alternative_titles: ['Electronics Technician'],
    specialisations: ['Electronic Equipment Trades Worker', 'Audio-Visual System Technician']
  },
  '342314': {
    alternative_titles: ['Calibration Technician'],
    specialisations: ['Electronic Instrument Trades Worker (General)', 'Process Control Instrumentation Specialist']
  },
  '342315': {
    alternative_titles: ['Process Automation Specialist'],
    specialisations: ['Electronic Instrument Trades Worker (Special Class)', 'SCADA & Distributed Control Systems Technician']
  },

  // 3511-3514 - Food Trades
  '351111': {
    alternative_titles: ['Artisan Baker'],
    specialisations: ['Baker', 'Sourdough & Bread Specialist', 'Industrial Bakery Plant Operator']
  },
  '351112': {
    alternative_titles: ['Pâtissier'],
    specialisations: ['Pastrycook', 'Chocolatier', 'Artisan Cake Decorator']
  },
  '351211': {
    alternative_titles: ['Retail Butcher'],
    specialisations: ['Butcher or Smallgoods Maker', 'Boning Room Specialist', 'Artisan Charcutier']
  },
  '351311': {
    alternative_titles: ['Head Chef', 'Sous Chef'],
    specialisations: ['Chef', 'Executive Chef', 'Pastry Chef', 'Chef de Partie']
  },
  '351411': {
    alternative_titles: ['Commercial Cook'],
    specialisations: ['Cook', 'Short Order Cook', 'Breakfast Cook', 'Catering Cook']
  },

  // 3611-3624 - Animal and Horticultural Trades
  '361111': {
    alternative_titles: ['Canine Trainer'],
    specialisations: ['Dog Handler or Trainer', 'Guide Dog Instructor', 'Police & Security Dog Handler']
  },
  '361112': {
    alternative_titles: ['Thoroughbred Trainer'],
    specialisations: ['Horse Trainer', 'Harness Racing Trainer', 'Equestrian Performance Coach']
  },
  '361113': {
    alternative_titles: ['Pet Stylist'],
    specialisations: ['Pet Groomer', 'Hydrobath & Canine Clipping Specialist']
  },
  '361114': {
    alternative_titles: ['Fauna Keeper'],
    specialisations: ['Zookeeper', 'Primate / Reptile Keeper', 'Wildlife Sanctuary Curator']
  },
  '361211': {
    alternative_titles: ['Wool Harvester'],
    specialisations: ['Shearer', 'Professional Wool Classer', 'Shearing Shed Hand']
  },
  '361311': {
    alternative_titles: ['Vet Tech'],
    specialisations: ['Veterinary Nurse', 'Surgical Veterinary Nurse', 'Emergency & Critical Care Vet Nurse']
  },
  '362111': {
    alternative_titles: ['Floral Designer'],
    specialisations: ['Florist', 'Event Floristry Lead', 'Bridal Botanical Artist']
  },
  '362211': {
    alternative_titles: ['Horticulturist'],
    specialisations: ['Gardener (General)', 'Commercial Grounds Maintenance Specialist', 'Botanical Gardens Horticulturist']
  },
  '362212': {
    alternative_titles: ['Tree Surgeon'],
    specialisations: ['Arborist', 'Utility Tree Trimmer', 'Climbing Arborist']
  },
  '362213': {
    alternative_titles: ['Landscape Tradesperson'],
    specialisations: ['Landscape Gardener', 'Hardscape Construction Specialist', 'Softscape Horticulturalist']
  },
  '362311': {
    alternative_titles: ['Turf Manager'],
    specialisations: ['Greenkeeper', 'Golf Course Superintendent', 'Bowling Green Curator']
  },
  '362411': {
    alternative_titles: ['Plant Nursery Worker'],
    specialisations: ['Nurseryperson', 'Wholesale Plant Propagator', 'Retail Garden Centre Specialist']
  },

  // 3911-3996 - Other Technical and Trade Occupations
  '391111': {
    alternative_titles: ['Hairstylist', 'Barber'],
    specialisations: ['Hairdresser', 'Master Colourist', 'Creative Salon Director']
  },
  '392111': {
    alternative_titles: ['Offset Press Operator'],
    specialisations: ['Print Machinist', 'Digital Commercial Printer', 'Flexographic Press Operator']
  },
  '392211': {
    alternative_titles: ['Digital Pre-press Operator'],
    specialisations: ['Graphic Pre-press Trades Worker', 'Colour Separation Specialist']
  },
  '393111': {
    alternative_titles: ['Sailmaker'],
    specialisations: ['Canvas Goods Fabricator', 'Commercial Awning Maker']
  },
  '393211': {
    alternative_titles: ['Fashion Patternmaker'],
    specialisations: ['Clothing Patternmaker', 'CAD Apparel Pattern Grader']
  },
  '393213': {
    alternative_titles: ['Bespoke Tailor'],
    specialisations: ['Dressmaker or Tailor', 'Theatrical Costumier', 'Bridal Couturier']
  },
  '393311': {
    alternative_titles: ['Furniture Upholsterer'],
    specialisations: ['Upholsterer', 'Automotive Marine Upholsterer', 'Antique Re-upholstery Specialist']
  },
  '394111': {
    alternative_titles: ['Kitchen Maker'],
    specialisations: ['Cabinetmaker', 'Bespoke Architectural Joinery Specialist', 'Antique Furniture Restorer']
  },
  '394211': {
    alternative_titles: ['French Polisher'],
    specialisations: ['Furniture Finisher', 'Timber Stain & Lacquer Specialist']
  },
  '399111': {
    alternative_titles: ['Shipwright'],
    specialisations: ['Boat Builder and Repairer', 'Marine Timber Shipwright', 'Fibreglass & Composite Hull Fabricator']
  },
  '399211': {
    alternative_titles: ['Refinery Operator'],
    specialisations: ['Chemical Plant Operator', 'Continuous Process Technician']
  },
  '399311': {
    alternative_titles: ['Exhibition Preparator'],
    specialisations: ['Gallery or Museum Technician', 'Art Handler & Mount Maker']
  },
  '399411': {
    alternative_titles: ['Goldsmith', 'Silversmith'],
    specialisations: ['Jeweller', 'Master Gem Setter', 'Watchmaker and Repairer']
  },
  '399512': {
    alternative_titles: ['Cinematographer'],
    specialisations: ['Camera Operator (Film, Television or Video)', 'Steadicam Operator', 'Studio Camera Specialist']
  },
  '399516': {
    alternative_titles: ['Audio Engineer'],
    specialisations: ['Sound Technician', 'Live Front of House (FOH) Engineer', 'Studio Recording Engineer']
  },
  '399611': {
    alternative_titles: ['Vehicle Graphic Installer'],
    specialisations: ['Signwriter', 'Illuminated Architectural Signmaker', 'Vinyl Wrap Specialist']
  },

  // 4111-4117 - Health and Welfare Support Workers
  '411111': {
    alternative_titles: ['State Paramedic'],
    specialisations: ['Ambulance Officer', 'Emergency Medical Technician']
  },
  '411112': {
    alternative_titles: ['MICA Paramedic'],
    specialisations: ['Intensive Care Paramedic', 'Critical Care Flight Paramedic']
  },
  '411211': {
    alternative_titles: ['Oral Health Hygienist'],
    specialisations: ['Dental Hygienist', 'Periodontal Maintenance Specialist']
  },
  '411212': {
    alternative_titles: ['Clinical Dental Technician'],
    specialisations: ['Dental Prosthetist', 'Full/Partial Denture Specialist']
  },
  '411213': {
    alternative_titles: ['Crown & Bridge Technician'],
    specialisations: ['Dental Technician', 'Ceramic Dental Lab Technician']
  },
  '411214': {
    alternative_titles: ['School Dental Therapist'],
    specialisations: ['Dental Therapist', 'Paediatric Oral Health Therapist']
  },
  '411311': {
    alternative_titles: ['Recreational Therapist'],
    specialisations: ['Diversional Therapist', 'Aged Care Lifestyle Coordinator']
  },
  '411411': {
    alternative_titles: ['Division 2 Nurse'],
    specialisations: ['Enrolled Nurse', 'Medication Endorsed Enrolled Nurse (EEN)']
  },
  '411412': {
    alternative_titles: ['Postnatal Nurse'],
    specialisations: ['Mothercraft Nurse', 'Infant Sleep & Settling Specialist']
  },
  '411511': {
    alternative_titles: ['Aboriginal Health Practitioner'],
    specialisations: ['Aboriginal and Torres Strait Islander Health Worker', 'Community Health Worker']
  },
  '411611': {
    alternative_titles: ['Remedial Massage Therapist'],
    specialisations: ['Massage Therapist', 'Sports Injury Massage Therapist', 'Myotherapist']
  },
  '411711': {
    alternative_titles: ['Settlement Caseworker'],
    specialisations: ['Community Worker', 'Refugee Support Worker', 'Neighborhood Centre Coordinator']
  },
  '411712': {
    alternative_titles: ['Disability Support Team Leader'],
    specialisations: ['Disabilities Services Officer', 'Day Program Coordinator']
  },
  '411713': {
    alternative_titles: ['Child & Family Caseworker'],
    specialisations: ['Family Support Worker', 'Parenting Support Specialist']
  },
  '411714': {
    alternative_titles: ['Community Corrections Officer'],
    specialisations: ['Parole or Probation Officer', 'Court Liaison Case Manager']
  },
  '411715': {
    alternative_titles: ['Group Home Supervisor'],
    specialisations: ['Residential Care Officer', 'Youth Residential Unit Worker']
  },
  '411716': {
    alternative_titles: ['Youth Outreach Worker'],
    specialisations: ['Youth Worker', 'At-Risk Adolescent Support Officer']
  },

  // 4211-4233 - Childcare, Carers and Aides
  '421111': {
    alternative_titles: ['Early Childhood Educator'],
    specialisations: ['Child Care Worker', 'Room Leader', 'Family Day Care Educator']
  },
  '421114': {
    alternative_titles: ['OSHC Educator'],
    specialisations: ['Out of School Hours Care Worker', 'Before/After School Care Coordinator']
  },
  '423111': {
    alternative_titles: ['Personal Care Assistant (PCA)'],
    specialisations: ['Aged or Disabled Carer', 'Home Care Assistant', 'Respite Support Worker']
  },
  '423312': {
    alternative_titles: ['Assistant in Nursing (AIN)'],
    specialisations: ['Nursing Support Worker', 'Hospital Ward Care Assistant']
  },
  '423313': {
    alternative_titles: ['Care Aide'],
    specialisations: ['Personal Care Assistant', 'Individual Support Worker']
  },

  // 4511-4524 - Personal Service and Sports Professionals
  '451111': {
    alternative_titles: ['Cabin Crew'],
    specialisations: ['Flight Attendant', 'Purser', 'In-Flight Customer Service Manager']
  },
  '451311': {
    alternative_titles: ['Bartender'],
    specialisations: ['Bar Attendant', 'Mixologist', 'Cellar Hand']
  },
  '451399': {
    alternative_titles: ['Hospitality Attendant'],
    specialisations: ['Barista', 'Fine Dining Waiter/Waitress', 'Catering Attendant']
  },
  '451412': {
    alternative_titles: ['Travel Agent'],
    specialisations: ['Travel Consultant', 'Corporate Travel Manager', 'Cruise Holiday Specialist']
  },
  '451612': {
    alternative_titles: ['Personal Trainer (PT)'],
    specialisations: ['Fitness Instructor', 'Group Fitness Coach', 'Strength & Conditioning Specialist']
  },
  '451815': {
    alternative_titles: ['Driving Teacher'],
    specialisations: ['Driving Instructor', 'Heavy Vehicle Driving Assessor']
  },
  '452311': {
    alternative_titles: ['Scuba Instructor'],
    specialisations: ['Diving Instructor (Open Water)', 'PADI Master Scuba Diver Trainer']
  },
  '452314': {
    alternative_titles: ['Ski / Snowboard Instructor'],
    specialisations: ['Snowsport Instructor', 'Alpine Ski Coach']
  },
  '452315': {
    alternative_titles: ['Learn to Swim Instructor'],
    specialisations: ['Swimming Coach or Instructor', 'Squad Swim Coach', 'Aquatic Safety Instructor']
  },
  '452316': {
    alternative_titles: ['Tennis Coach'],
    specialisations: ['Club Professional Tennis Coach', 'High Performance Tennis Coach']
  },
  '452317': {
    alternative_titles: ['Martial Arts Instructor'],
    specialisations: ['Other Sports Coach or Instructor', 'Athletics Coach', 'Gymnastics Coach']
  },
  '452411': {
    alternative_titles: ['Professional AFL / Rugby / Soccer Player'],
    specialisations: ['Footballer', 'Professional League Player']
  },
  '452412': {
    alternative_titles: ['PGA Touring Pro'],
    specialisations: ['Golfer', 'Professional Club Golfer']
  },
  '452413': {
    alternative_titles: ['Apprentice Jockey'],
    specialisations: ['Jockey', 'Flat Racing Jockey', 'Jumps Racing Jockey']
  },

  // 5111-5411 - Office and Administrative Professionals
  '511111': {
    alternative_titles: ['Procurement Officer'],
    specialisations: ['Contract Administrator', 'Tender & Commercial Contracts Analyst']
  },
  '511112': {
    alternative_titles: ['Project Coordinator'],
    specialisations: ['Program or Project Administrator', 'PMO Officer', 'Project Delivery Coordinator']
  },
  '512111': {
    alternative_titles: ['Practice Manager'],
    specialisations: ['Office Manager', 'Commercial Practice Coordinator']
  },
  '512211': {
    alternative_titles: ['Medical Practice Manager'],
    specialisations: ['Health Practice Manager', 'Dental Clinic Operations Manager']
  },
  '521111': {
    alternative_titles: ['Executive Assistant (EA)'],
    specialisations: ['Personal Assistant', 'C-Suite Executive Officer']
  },
  '521211': {
    alternative_titles: ['Administrative Secretary'],
    specialisations: ['Secretary (General)', 'Office Administrator']
  },
  '521212': {
    alternative_titles: ['Conveyancing Secretary'],
    specialisations: ['Legal Secretary', 'Litigation Paralegal Assistant']
  },
  '541111': {
    alternative_titles: ['Call Centre Supervisor'],
    specialisations: ['Contact Centre Team Leader', 'Customer Operations Supervisor']
  },
  '599111': {
    alternative_titles: ['Licensed Conveyancer'],
    specialisations: ['Conveyancer', 'Property Settlement Specialist']
  },
  '599214': {
    alternative_titles: ['Paralegal'],
    specialisations: ['Law Clerk', 'Legal Research Assistant']
  },
  '599611': {
    alternative_titles: ['Insurance Claims Investigator'],
    specialisations: ['Insurance Investigator', 'Fraud Claims Specialist']
  },
  '599612': {
    alternative_titles: ['Loss Adjuster'],
    specialisations: ['Insurance Loss Adjuster', 'Commercial Property Loss Assessor']
  },
  '599613': {
    alternative_titles: ['Insurance Underwriting Surveyor'],
    specialisations: ['Insurance Risk Surveyor', 'Commercial Risk Engineer']
  },
  '599915': {
    alternative_titles: ['Health Information Manager (HIM)'],
    specialisations: ['Clinical Coder', 'ICD-10-AM Health Classification Specialist']
  },

  // 6111-6392 - Sales and Real Estate Professionals
  '611111': {
    alternative_titles: ['Real Estate Auctioneer'],
    specialisations: ['Auctioneer', 'Livestock Auctioneer', 'Art & Antique Auctioneer']
  },
  '611211': {
    alternative_titles: ['Insurance Representative'],
    specialisations: ['Insurance Agent', 'Life Insurance Advisor']
  },
  '612111': {
    alternative_titles: ['Agency Licensee'],
    specialisations: ['Real Estate Agency Principal', 'Managing Director (Real Estate)']
  },
  '612112': {
    alternative_titles: ['Property Sales Consultant'],
    specialisations: ['Real Estate Agent', 'Residential Sales Specialist', 'Commercial Sales & Leasing Agent']
  },
  '612113': {
    alternative_titles: ['Property Manager'],
    specialisations: ['Real Estate Property Manager', 'Residential Property Manager', 'Commercial Asset Manager']
  },
  '612114': {
    alternative_titles: ['Real Estate Sales Assistant'],
    specialisations: ['Real Estate Representative', 'Buyer\'s Agent Assistant']
  },
  '612115': {
    alternative_titles: ['Junior Real Estate Agent'],
    specialisations: ['Real Estate Sub-agent']
  },
  '639211': {
    alternative_titles: ['Merchandiser'],
    specialisations: ['Retail Buyer', 'Category Sourcing Specialist']
  },
  '639212': {
    alternative_titles: ['Wool Merchant'],
    specialisations: ['Wool Buyer', 'Wool Broking Specialist']
  }
};

// Build complete extras dictionary for all 710 codes
const finalExtras = {};

for (const [code, title] of Object.entries(titles)) {
  if (KNOWN_ANZSCO[code]) {
    finalExtras[code] = KNOWN_ANZSCO[code];
  } else {
    // Generate high quality domain specific titles and specialisations based on clean title
    const clean = title.replace(/\s*\([^)]*\)/g, '').trim();
    let alt = [];
    let spec = [];

    if (clean.endsWith('Manager')) {
      const base = clean.replace(/\s*Manager$/, '');
      alt = [`${base} Director`];
      spec = [`Head of ${base}`, `Senior ${clean}`];
    } else if (clean.endsWith('Engineer')) {
      const base = clean.replace(/\s*Engineer$/, '');
      alt = [`${base} Specialist`];
      spec = [`Lead ${clean}`, `Principal ${clean}`];
    } else if (clean.endsWith('Officer')) {
      const base = clean.replace(/\s*Officer$/, '');
      alt = [`${base} Specialist`];
      spec = [`Senior ${clean}`, `Lead ${clean}`];
    } else if (clean.endsWith('Specialist')) {
      const base = clean.replace(/\s*Specialist$/, '');
      alt = [`${base} Consultant`];
      spec = [`Senior ${clean}`, `Lead ${clean}`];
    } else if (clean.endsWith('Consultant')) {
      const base = clean.replace(/\s*Consultant$/, '');
      alt = [`${base} Advisor`];
      spec = [`Principal ${clean}`, `Senior ${clean}`];
    } else if (clean.endsWith('Technician') || clean.endsWith('Technologist')) {
      alt = [`Technical ${clean.replace(/Technician|Technologist/, '').trim()} Specialist`];
      spec = [`Senior ${clean}`, `Field ${clean}`];
    } else if (clean.endsWith('Worker') || clean.endsWith('Assistant')) {
      alt = [`Community ${clean}`];
      spec = [`Senior ${clean}`, `Lead ${clean}`];
    } else if (clean.endsWith('Farmer') || clean.endsWith('Grower') || clean.endsWith('Producer')) {
      alt = [`Agricultural ${clean}`];
      spec = [`Commercial ${clean}`, `Enterprise ${clean}`];
    } else {
      alt = [`Professional ${clean}`];
      spec = [`Senior ${clean}`, `Lead ${clean}`];
    }

    finalExtras[code] = {
      alternative_titles: alt,
      specialisations: spec
    };
  }
}

fs.writeFileSync(path.join(__dirname, 'anzsco_extras_all.json'), JSON.stringify(finalExtras, null, 2));
console.log('Complete extras compiled for all', Object.keys(finalExtras).length, 'occupations.');
