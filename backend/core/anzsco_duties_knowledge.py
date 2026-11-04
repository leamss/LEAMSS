"""Official ABS ANZSCO Unit Group Tasks & Technical Duties Knowledge Base.

Used to accurately match candidate resume work experience explanations,
daily roles and responsibilities against official Australian Bureau of Statistics (ABS)
and Assessing Authorities (ACS, VETASSESS, TRA, Engineers Australia) duty definitions.
"""
from typing import Dict, List, Set

IRREGULAR_VERBS_MAP: Dict[str, str] = {
    "wrote": "writ", "written": "writ", "writing": "writ", "writes": "writ",
    "built": "build", "building": "build", "builds": "build",
    "led": "lead", "leading": "lead", "leads": "lead",
    "taught": "teach", "teaching": "teach", "teaches": "teach",
    "sold": "sell", "selling": "sell", "sells": "sell",
    "bought": "buy", "buying": "buy", "buys": "buy",
    "ran": "run", "running": "run", "runs": "run",
    "spoke": "speak", "spoken": "speak",
    "drew": "draw", "drawn": "draw", "drawing": "draw",
    "chose": "choos", "chosen": "choos",
    "held": "hold", "holding": "hold",
    "paid": "pay", "paying": "pay",
    "sent": "send", "sending": "send",
    "met": "meet", "meeting": "meet",
    "sat": "sit", "sitting": "sit",
    "set": "set", "setting": "set",
    "kept": "keep", "keeping": "keep",
    "understood": "understand", "understanding": "understand",
    "dev": "develop", "devops": "devops",
    "admin": "administr", "mgr": "manag",
    "eng": "engin", "db": "databas",
    "qa": "test", "mgmt": "manag",
    "ui": "frontend", "ux": "frontend",
}

STOP_WORDS: Set[str] = {
    "with", "and", "the", "for", "years", "year", "experience", "holds", "held",
    "master", "masters", "bachelor", "bachelors", "degree", "client", "current",
    "role", "roles", "work", "worked", "working", "job", "candidate", "profile",
    "overall", "total", "skills", "assessment", "level", "post", "have", "has",
    "from", "also", "been", "their", "this", "that", "these", "those", "under",
    "over", "into", "onto", "education", "qualified", "qualifications", "completed",
    "history", "details", "applicant", "primary", "full", "time", "general", "responsible",
    "duties", "including", "across", "various", "multiple", "using", "well"
}


def lemmatize_token(word: str) -> str:
    """Lemmatize token handling irregular past tense verbs and common technical abbreviations."""
    w = word.lower()
    if w in IRREGULAR_VERBS_MAP:
        return IRREGULAR_VERBS_MAP[w]
    for sfx in ["ing", "tion", "sions", "sion", "ed", "es", "ies", "ers", "er", "ly", "ment", "ments", "s"]:
        if len(w) > len(sfx) + 3 and w.endswith(sfx):
            return w[:-len(sfx)]
    return w


# Official ABS ANZSCO 4-digit Unit Group Tasks & Duties Dictionary
ANZSCO_UNIT_GROUP_DUTIES: Dict[str, List[str]] = {
    # ── ICT & SOFTWARE ──
    "2613": [
        "Researching, consulting, analysing and evaluating system program needs and software architecture",
        "Writing, designing, debugging and maintaining program code to meet system requirements and technical specifications",
        "Developing, configuring and integrating RESTful APIs, microservices, backend services, and web applications",
        "Testing, diagnosing and correcting errors and faults in applications using automated test suites and unit testing",
        "Writing, updating and maintaining technical program, end user and operational documentation",
        "Deploying and managing containerised applications using CI/CD pipelines, Docker, cloud services and version control",
        "Collaborating in agile scrum sprints, participating in code reviews, and optimizing database queries and system performance",
    ],
    "2611": [
        "Working with users to formulate and document detailed business requirements, user stories and functional specifications",
        "Identifying, investigating and analysing business processes, workflows, and operational procedures",
        "Deploying system techniques and business modelling to identify inefficiencies and recommend software solutions",
        "Preparing Business Requirements Documents (BRD), Functional Specifications (FRD) and acceptance criteria",
        "Coordinating user acceptance testing (UAT) and facilitating agile sprint planning and stakeholder workshops",
    ],
    "2612": [
        "Designing and developing website architecture, user interfaces, frontend components and multimedia applications",
        "Writing and integrating frontend code using HTML, CSS, JavaScript frameworks, React, Angular, or Vue",
        "Optimizing web performance, responsive layouts, accessibility standards, and search engine parameters",
        "Collaborating with backend developers to integrate APIs, databases and digital content management systems",
    ],
    "2621": [
        "Designing and maintaining database architecture, data models, tables, indexing and query performance",
        "Designing, configuring and monitoring cybersecurity infrastructure, firewalls, threat detection and security policies",
        "Managing database backup, disaster recovery, replication, and data integrity audits",
        "Investigating cybersecurity incidents, vulnerabilities, malware analysis, and risk assessments",
    ],
    "2631": [
        "Analysing, developing, interpreting and evaluating complex network designs and network architecture",
        "Configuring, testing and maintaining network routers, switches, subnets, firewalls, VPNs and WAN/LAN infrastructure",
        "Troubleshooting network faults, performance bottlenecks, telecommunication links, and hardware configurations",
        "Managing cloud network environments, server operating systems, DNS, DHCP, and enterprise directory services",
    ],
    "2632": [
        "Developing, executing and maintaining automated and manual test plans, test cases and test scripts",
        "Performing regression testing, system integration testing, performance benchmarking and load testing",
        "Logging, diagnosing, and reporting software defects using issue tracking systems like Jira",
        "Providing technical troubleshooting and tier-3 support for enterprise hardware and software systems",
    ],
    "2633": [
        "Designing, planning and optimising telecommunications transmission networks, radio systems, and fibre networks",
        "Configuring telecommunication switching systems, cellular towers, microwave links, and optical transport",
        "Conducting radio frequency (RF) propagation analysis and telecommunications hardware commissioning",
    ],
    "1351": [
        "Directing the development, implementation and operation of ICT strategies, technology roadmaps and budgets",
        "Managing software engineering teams, IT infrastructure departments, vendor contracts and service level agreements",
        "Overseeing resource allocation, project delivery timelines, governance standards and IT risk compliance",
    ],
    "1322": [
        "Planning, directing, and coordinating the overall financial operations, accounting systems, and treasury of an enterprise",
        "Developing corporate financial budgets, long-range financial forecasts, cash flow models, and commercial pricing strategies",
        "Overseeing P&L management, margin targets, cost reduction programs, and capital allocation across business units",
        "Evaluating investment opportunities, commercial contracts, mergers, financial due diligence, and risk governance",
        "Presenting executive financial reviews, board reports, and key operational KPIs to C-suite leadership",
        "Ensuring compliance with statutory financial reporting, corporate governance, auditing, and tax legislation",
    ],
    "1112": [
        "Directing and coordinating the overall operational activities, strategy, and business units of an enterprise",
        "Formulating organizational policies, corporate governance frameworks, and strategic business roadmaps",
        "Managing operational budgets, resource allocation, executive talent, and cross-functional performance targets",
        "Representing the organization in major negotiations, board meetings, joint ventures, and official industry forums",
    ],
    "1323": [
        "Planning, directing and coordinating the human resource management policies and workplace relations of an enterprise",
        "Overseeing talent acquisition, recruitment funnels, compensation benchmarks, and employee retention strategies",
        "Managing organizational development, employee performance reviews, learning and training programs, and HR compliance",
        "Directing dispute resolution, enterprise bargaining negotiations, and workplace health and safety compliance",
    ],
    "1324": [
        "Developing, directing and implementing strategic corporate planning, operational policies, and organizational objectives",
        "Analyzing government legislation, market trends, and industry changes to formulate strategic responses and policy briefs",
        "Overseeing program management, corporate project delivery, strategic risk management, and regulatory compliance",
    ],

    # ── ACCOUNTING, FINANCE & BUSINESS ──
    "2211": [
        "Assisting in formulating budgetary, financial and accounting policies and internal controls",
        "Preparing financial statements, balance sheets, profit and loss statements, and management accounts",
        "Conducting financial investigations, variance analyses, and cash flow forecasting",
        "Preparing and lodging statutory tax returns (GST, BAS, Corporate Income Tax) and advising on tax planning",
        "Reconciling bank accounts, general ledgers, accounts payable, accounts receivable, and payroll records",
    ],
    "2212": [
        "Planning, executing and evaluating internal and external audits to ensure compliance with financial accounting standards",
        "Examining accounting records, transaction logs, internal operational controls, and statutory compliance",
        "Preparing formal audit reports detailing findings, control deficiencies, and risk remediation recommendations",
        "Managing corporate treasury, debt financing, foreign exchange risk, and liquidity management",
    ],
    "2221": [
        "Arranging finance, loans and insurance products for corporate and individual clients",
        "Analyzing financial and credit documents, evaluating creditworthiness and borrowing risk",
        "Negotiating terms with lenders, banks, and underwriters on behalf of clients",
    ],
    "2223": [
        "Interviewing clients and corporate stakeholders to determine financial status, investment goals, risk appetite and financial horizons",
        "Developing corporate investment portfolios, capital management strategies, wealth creation plans, and asset allocation models",
        "Analysing financial market trends, equity stocks, fixed income bonds, venture capital, and commercial investment opportunities",
        "Building complex financial models, discounted cash flow (DCF) models, scenario analyses, and company valuation assessments",
        "Conducting buy-side and sell-side financial due diligence, quality of earnings assessments, and investment risk reviews",
    ],
    "2247": [
        "Reviewing organizational operating models, business processes, workflows, and governance frameworks",
        "Advising executive leadership on strategic business transformation, cost reduction, and performance optimization",
        "Developing change management strategies, stakeholder communication plans, and KPI measurement models",
        "Conducting industry benchmarking, operational gap analysis, and operating model restructuring",
    ],
    "2251": [
        "Formulating and directing advertising campaigns, digital marketing strategies, and brand positioning",
        "Analysing consumer demographics, market research surveys, competitor offerings, and customer retention metrics",
        "Managing digital paid acquisition channels (Google Ads, Meta, SEO, SEM, content marketing)",
        "Tracking marketing ROI, lead generation funnels, conversion rates, and campaign analytics",
    ],
    "2254": [
        "Promoting and selling specialized industrial, medical, technical or IT products and software services",
        "Developing technical proposals, preparing product demonstrations, and negotiating commercial enterprise contracts",
        "Building client relationships, assessing engineering specifications, and managing post-sales support",
    ],

    # ── ENGINEERING ──
    "2332": [
        "Determining construction methods, materials, structural specifications, and drafting structural blueprints",
        "Designing and calculating structural loads, stresses, foundations, steel/concrete framing, and drainage networks",
        "Supervising construction sites, testing soil compaction and concrete strength, ensuring building code compliance",
        "Managing civil infrastructure projects, roadworks, bridges, water supply, and stormwater management",
    ],
    "2333": [
        "Designing electrical power generation, transmission, distribution switchyards, and substations",
        "Specifying electrical instrumentation, control circuits, transformers, switchgear, and backup generators",
        "Performing electrical load flow studies, short-circuit calculations, protection coordination, and schematics in AutoCAD",
    ],
    "2334": [
        "Designing electronic circuits, printed circuit boards (PCBs), microcontrollers, and embedded firmware",
        "Testing and calibrating electronic instrumentation, sensor arrays, signal processors, and communications equipment",
    ],
    "2335": [
        "Designing mechanical machinery, thermodynamic systems, manufacturing equipment, piping, and HVAC ventilation",
        "Developing mechanical 3D CAD models, finite element analysis (FEA), stress calculations, and manufacturing drawings",
        "Optimizing manufacturing production lines, plant layouts, process automation, and equipment maintenance schedules",
    ],
    "2339": [
        "Designing environmental remediation, water treatment, biomedical instrumentation, or agricultural systems",
        "Conducting engineering risk assessments, environmental impact studies, and quality assurance auditing",
    ],
    "3122": [
        "Preparing civil engineering drawings, site plans, contour surveys, and construction details using AutoCAD and Civil 3D",
        "Assisting civil engineers with field measurements, soil sampling, concrete batch testing, and quantity takeoff",
    ],
    "3123": [
        "Preparing electrical engineering wiring diagrams, control panel layouts, and conduit routes using CAD",
        "Assisting electrical engineers in testing switchboards, motor control centres, and circuit continuity",
    ],
    "3125": [
        "Preparing mechanical engineering component drawings, fabrication assemblies, and piping isometrics",
        "Assisting mechanical engineers with equipment commissioning, vibration analysis, and maintenance testing",
    ],

    # ── HEALTHCARE & MEDICAL ──
    "2544": [
        "Assessing, planning, implementing and evaluating nursing and clinical healthcare for acute and chronically ill patients",
        "Administering prescribed medications, IV infusions, wound dressing, and monitoring vital medical parameters",
        "Assisting surgical procedures, triaging emergencies, maintaining sterile clinical environments, and patient charting",
        "Collaborating with doctors, specialists, and multidisciplinary healthcare teams to coordinate care plans",
    ],
    "2515": [
        "Dispensing prescription medicines, checking dosages, reviewing drug interactions and contraindications",
        "Advising patients on medication regimens, side effects, over-the-counter products, and chronic disease management",
    ],
    "2531": [
        "Examining patients, obtaining medical histories, diagnosing physical and psychological illnesses",
        "Ordering diagnostic tests (bloods, pathology, imaging) and prescribing pharmaceutical therapies and treatment regimens",
    ],
    "4115": [
        "Delivering clinical primary healthcare, preventive medicine, and chronic disease management in community health clinics",
        "Conducting community outreach, health education workshops, immunizations, and clinical patient screenings",
    ],

    # ── HOSPITALITY & FOOD TRADES ──
    "3513": [
        "Planning menus, estimating food and labour costs, ordering ingredients, and controlling kitchen stock levels",
        "Cooking, preparing and finishing high-standard culinary dishes, sauces, meat, seafood, and appetizers",
        "Supervising kitchen staff, commis chefs, apprentices, and enforcing HACCP food safety and sanitation hygiene",
        "Monitoring food preparation temperatures, kitchen equipment, plate presentation, and culinary consistency",
    ],
    "3514": [
        "Cooking and preparing meals, food items, seasonings, and basic sauces according to recipes and kitchen orders",
        "Operating grills, fryers, ovens, and food processing equipment under senior chef supervision",
        "Cleaning food preparation surfaces, washing equipment, and monitoring food storage refrigeration temperatures",
    ],
    "3511": [
        "Mixing and kneading dough, preparing bread loaves, pastries, cakes, pies, and confectionery items",
        "Operating commercial bakery ovens, dough dividers, mixers, and decorating baked goods to quality recipes",
    ],
    "1411": [
        "Directing and coordinating cafe or restaurant front-of-house, reservations, table service, and customer hospitality",
        "Managing food and beverage operations, revenue budgets, supplier contracts, staff rosters, and compliance",
    ],
    "1413": [
        "Directing hotel and motel front desk operations, reservations, room service, concierge, and housekeeping",
        "Overseeing hotel operating budgets, revenue management, guest relations, and hospitality facility maintenance",
    ],
    "1419": [
        "Directing accommodation, resort, or hospitality facilities, managing guest relations, property management, and events",
        "Overseeing hospitality staff, guest satisfaction surveys, statutory liquor licensing, and health and safety standards",
    ],

    # ── TRADES & CONSTRUCTION ──
    "3212": [
        "Diagnosing mechanical and electrical vehicle faults, servicing engines, transmissions, brake systems, and steering",
        "Performing computerized automotive diagnostic scans, engine tuning, wheel alignments, and replacing worn parts",
    ],
    "3223": [
        "Fabricating and welding steel structures, pressure vessels, and pipes using MIG, TIG, and manual arc welding",
        "Reading and interpreting engineering drawings, welding symbols, cutting steel beams, and grinding weld seams",
    ],
    "3232": [
        "Machining metal components using precision lathes, milling machines, surface grinders, and CNC tooling",
        "Assembling and fitting manufactured metal components, bearing assemblies, shafts, and hydraulic rams",
    ],
    "3312": [
        "Constructing, erecting, installing and repairing timber frameworks, roof trusses, formwork, and timber flooring",
        "Reading architectural drawings, measuring materials, cutting joints, fitting doors, windows, and architectural mouldings",
    ],
    "3341": [
        "Installing, testing and maintaining water supply pipes, sanitary drainage, sewerage systems, and gas lines",
        "Installing hot water services, pumps, fixtures, backflow prevention devices, and clearing blockages",
    ],
    "3411": [
        "Installing, wiring, testing and commissioning electrical power, lighting circuits, switchboards, and domestic/commercial cabling",
        "Testing electrical continuity, insulation resistance, circuit breakers, and fault finding on electrical installations",
    ],

    # ── LEGAL & EDUCATION ──
    "2713": [
        "Providing legal advice, researching case law precedents, statutory legislation, and regulatory compliance",
        "Drafting legal contracts, conveyancing documentation, wills, commercial agreements, and court pleadings",
        "Representing clients in negotiations, disputes, tribunals, and instructing barristers on litigation cases",
    ],
    "2411": [
        "Planning and implementing early childhood educational programs, learning activities, and developmental play",
        "Assessing and recording child developmental milestones, literacy, numeracy, and emotional progress",
    ],
    "2412": [
        "Teaching primary school children literacy, numeracy, science, arts, and physical education",
        "Preparing lesson plans, teaching aids, evaluating student work, and consulting with parents on progress",
    ],
    "2414": [
        "Teaching secondary school students specific subjects (mathematics, science, humanities, languages, arts)",
        "Preparing curriculum lesson plans, laboratory experiments, marking examinations, and mentoring students",
    ],
    "2421": [
        "Delivering academic university lectures, tutorial workshops, and supervising postgraduate research students",
        "Conducting scholarly academic research, publishing peer-reviewed journal papers, and grading university exams",
    ],

    # ── HUMAN RESOURCES & WORKPLACE RELATIONS ──
    "2231": [
        "Advising on human resource policies, recruitment strategies, talent acquisition, and employee retention",
        "Managing employee onboarding, exit procedures, performance appraisal cycles, and career progression frameworks",
        "Interpreting employment law, national workplace awards, industrial agreements, and handling employee grievances",
        "Coordinating employee remuneration benchmarks, benefits packages, and staff wellness programs",
        "Sourcing and screening candidates, conducting competency interviews, reference checking, and placing job seekers",
    ],

    # ── CONSTRUCTION & SUPPLY CHAIN MANAGEMENT ──
    "1331": [
        "Directing and coordinating construction projects, commercial developments, and residential building sites",
        "Interpreting architectural blueprints, structural engineering specifications, building codes, and safety standards",
        "Managing building project budgets, procurement schedules, subcontractor contracts, and tender bids",
        "Supervising site supervisors, managing project milestones, progress claims, quality inspections, and handover",
    ],
    "1336": [
        "Planning, organizing and directing supply chain operations, inventory management, warehousing, and logistics distribution",
        "Negotiating procurement agreements with shipping carriers, freight forwarders, suppliers, and customs brokers",
        "Monitoring warehouse inventory turnover, storage capacities, demand forecasting, and logistics routing efficiency",
        "Ensuring compliance with international shipping regulations, import/export customs clearance, and transport safety",
    ],

    # ── SALES, MARKETING & ACCOUNT MANAGEMENT ──
    "1311": [
        "Directing and managing organizational sales strategies, marketing campaigns, customer acquisition, and brand expansion",
        "Leading corporate sales teams, setting sales quotas, revenue targets, territory management, and commission structures",
        "Analyzing customer market research, competitor pricing, distribution channels, and public relations strategies",
        "Managing key corporate accounts, high-value client relationships, enterprise contracts, and stakeholder partnerships",
    ],
    "2254": [
        "Promoting and selling specialized industrial, chemical, medical, pharmaceutical, and technical equipment to businesses",
        "Consulting with technical specialists, engineers, and healthcare professionals to demonstrate product technical capabilities",
        "Preparing commercial quotations, pricing tenders, service level agreements, and client proposal presentations",
        "Managing enterprise client accounts, handling sales negotiations, pipeline tracking, and after-sales technical support",
    ],

    # ── DATA SCIENCE, ACTUARIAL & POLICY ──
    "2241": [
        "Developing mathematical and actuarial models to evaluate insurance risk, investment returns, and financial liabilities",
        "Analyzing complex statistical datasets, designing econometric models, mortality tables, and risk probability distributions",
        "Applying predictive analytics, regression analysis, machine learning algorithms, and data modeling to solve commercial problems",
    ],
    "2244": [
        "Researching, analyzing, and evaluating public policy, government legislation, program outcomes, and strategic initiatives",
        "Gathering and assessing national security, criminal, or geopolitical intelligence, preparing briefing notes, and risk reports",
        "Consulting with government stakeholders, industry bodies, and community organizations to formulate policy submissions",
    ],

    # ── ARCHITECTURE & DESIGN ──
    "2321": [
        "Developing conceptual architectural designs, site master plans, and functional layout schemes for buildings",
        "Preparing detailed working drawings, specifications, material schedules, and submit development applications (DA)",
        "Administering construction contracts, inspecting building progress on site, and ensuring compliance with BCA/NCC standards",
    ],
    "2324": [
        "Designing visual brand identities, graphic layouts, typography, logos, packaging, and marketing collateral",
        "Creating digital UI/UX user interfaces, wireframes, prototypes, user journeys, and design systems for web and mobile",
        "Illustrating creative artwork, animations, motion graphics, and preparing digital prepress print-ready assets",
    ],

    # ── LIFE SCIENCES & ALLIED HEALTH ──
    "2345": [
        "Conducting scientific research in biochemistry, microbiology, genetics, biotechnology, and molecular biology",
        "Designing laboratory experiments, cell culture assays, genomic sequencing, and analyzing biological samples",
        "Developing biotechnological products, vaccines, pharmaceuticals, and documenting regulatory trials (GCP/GLP)",
    ],
    "2346": [
        "Performing diagnostic laboratory testing on clinical specimens (blood, tissue, biopsies, fluids) in pathology laboratories",
        "Operating complex pathology diagnostic instruments, flow cytometers, automated analyzers, and validating test results",
        "Maintaining laboratory quality assurance, NATA accreditation standards, calibration logs, and clinical safety controls",
    ],
    "2512": [
        "Operating diagnostic radiographic equipment (X-ray, CT, MRI, fluoroscopy) to produce diagnostic medical images",
        "Performing ultrasound scans (obstetric, abdominal, vascular, musculoskeletal) and reporting diagnostic findings to radiologists",
        "Ensuring patient radiation safety, positioning patients accurately, and adhering to clinical radiation protection protocols",
    ],
    "2524": [
        "Assessing physical, cognitive, and psychosocial limitations of patients, formulating occupational rehabilitation plans",
        "Designing assistive technology adaptations, home modifications, ergonomic assessments, and functional capacity reviews",
    ],
    "2525": [
        "Assessing and diagnosing musculoskeletal, neurological, and cardiopulmonary physical disorders and injuries",
        "Prescribing targeted therapeutic exercise programs, manual joint therapy, electrotherapy, and rehabilitation plans",
        "Monitoring patient functional mobility, recovery milestones, and developing post-injury return-to-work programs",
    ],

    # ── SOCIAL WORK & COMMUNITY WELFARE ──
    "2725": [
        "Assessing the social, economic, and emotional needs of individuals, families, children, and vulnerable community members",
        "Providing clinical casework counselling, crisis intervention, child protection assessments, and welfare advocacy",
        "Connecting clients to community support services, housing assistance, family court representation, and healthcare programs",
    ],
    "2726": [
        "Developing and implementing community support programs, recreation initiatives, and arts projects for target groups",
        "Providing welfare case coordination, emergency relief, community development, and referral services",
    ],
    "4117": [
        "Delivering frontline community support services, disability care assistance, and youth outreach programs",
        "Monitoring client wellbeing, facilitating daily living skills, managing crisis accommodation, and preparing case reports",
    ],

    # ── BUILDING TECHNICIANS & TRADES ──
    "3121": [
        "Inspecting building construction works to verify compliance with National Construction Code (NCC) and approved plans",
        "Preparing architectural draft drawings, CAD building plans, and surveying site levels and boundaries",
    ],
    "3131": [
        "Installing, maintaining and troubleshooting computer hardware, peripheral equipment, operating systems, and local networks",
        "Providing technical helpdesk support to users, logging IT incidents, and configuring user accounts and hardware",
    ],
    "3311": [
        "Laying bricks, concrete masonry blocks, and stonework to construct residential walls, commercial foundations, and facades",
        "Spreading mortar, cutting bricks with masonry saws, checking vertical alignment with plumb lines, and jointing seams",
    ],
    "3322": [
        "Preparing interior and exterior surfaces by sanding, filling holes, stripping old paint, and applying primer undercoats",
        "Applying paint, varnish, and protective coatings using brushes, rollers, and airless spray equipment to architectural standards",
    ],
    "3331": [
        "Measuring, cutting, and installing commercial and residential glass windows, shopfronts, mirrors, and shower screens",
        "Fitting glass panels using mastic, putty, and glazing rubber gaskets, repairing broken glass, and installing balustrades",
    ],
    "3334": [
        "Laying ceramic, porcelain, slate, and marble tiles on walls, floors, swimming pools, and outdoor patios",
        "Applying tile adhesives, cutting tiles around fixtures, grouting joints, and installing waterproof membranes",
    ],
    "3211": [
        "Diagnosing and repairing automotive electrical wiring faults, alternator/starter motors, and electronic ignition systems",
        "Installing vehicle accessories, alarm systems, GPS navigation, dual-battery systems, and electric vehicle powertrain wiring",
    ],
    "3241": [
        "Repairing accident-damaged vehicle chassis and body panels using hydraulic pulling equipment and dollies",
        "Replacing damaged automotive panels, cutting and welding replacement sheet metal, and filling body contours",
    ],
    "1341": [
        "Managing early childhood education and care centres, preschools, and long day care facilities",
        "Ensuring compliance with the National Quality Framework (NQF), child safety standards, and licensing regulations",
        "Supervising early childhood educators, managing enrolments, parent communications, and centre budgets",
    ],
    "1342": [
        "Directing and managing healthcare facilities, medical clinics, community health centres, and aged care services",
        "Monitoring healthcare clinical compliance, patient care standards, operational budgets, and medical staffing",
    ],
}
